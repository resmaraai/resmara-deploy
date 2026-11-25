"""System check and Releases.

Both pages answer one question the operator asks out loud: "is the thing I am looking at the
thing that is running, and is it healthy?" So neither of them guesses:

  * System check runs the checks it claims to run, right now, and reports what came back.
  * Releases reads the pull requests on the deploy mirror and the deploy records on the host,
    then compares the commit that is live with the commit each pull request merged.

When a credential is missing the row says so ("not connected") instead of reporting a pass.
"""
from __future__ import annotations

import logging
import os
import time
from datetime import datetime, timezone
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import httpx
from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.boost_control import get_current_user_optional
from app.core import config as settings_module
from app.core.config import settings
from app.db.session import AdAccount, Boost, Event, Post, User, get_db
from app.services import llm, mail, team_access

log = logging.getLogger("resmara.system")

router = APIRouter()

CHECK_TTL_SECONDS = 60
_cache: Dict[str, Any] = {"at": 0.0, "rows": None}


# --------------------------------------------------------------------------- system check
def _now_iso() -> str:
    return datetime.utcnow().isoformat()


def _row(name: str, status: str, detail: str, checked_at: str) -> Dict[str, Any]:
    return {"name": name, "status": status, "detail": detail, "checked_at": checked_at}


def _utc(value: Any) -> Optional[datetime]:
    """A stored datetime as aware UTC.

    Postgres hands back an aware value for a `timestamptz` column while `datetime.utcnow()`
    is naive, and comparing the two raises TypeError. That is why this check once read
    "can't compare offset-naive and offset-aware datetimes" instead of the state of the
    logins: the row was reporting the crash in its own comparison, not a broken token.
    """
    if not isinstance(value, datetime):
        return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _meta_login_row(accounts: List[Any], checked_at: str) -> Dict[str, Any]:
    """One row for every agent's Meta login.

    `token_status` is what token_health wrote on its last check; the expiry is the second
    opinion, because a status nobody has refreshed for weeks is a claim, not a fact.
    """
    now = datetime.now(timezone.utc)
    dead: List[Any] = []
    expiring: List[Any] = []
    for account in accounts:
        expires = _utc(getattr(account, "token_expires_at", None))
        status = (getattr(account, "token_status", "") or "").lower()
        if status in ("needs_reconnect", "broken", "expired") or (expires and expires < now):
            dead.append(account.user_id)
        elif expires and (expires - now).days <= 7:
            expiring.append(account.user_id)
    if not accounts:
        return _row("Meta logins", "warn", "No Meta account connected yet", checked_at)
    if dead:
        return _row("Meta logins", "fail", f"{len(dead)} of {len(accounts)} need reconnecting", checked_at)
    if expiring:
        return _row("Meta logins", "warn", f"{len(expiring)} token(s) expire within a week", checked_at)
    return _row("Meta logins", "ok", f"All {len(accounts)} working", checked_at)


def _http_get(url: str, timeout: float = 8.0) -> tuple[Optional[int], float, str]:
    started = time.monotonic()
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            response = client.get(url)
        return response.status_code, (time.monotonic() - started) * 1000.0, response.text[:4000]
    except Exception as exc:                                     # noqa: BLE001 - reported
        return None, (time.monotonic() - started) * 1000.0, str(exc)[:300]


def _run_checks(db: Session) -> List[Dict[str, Any]]:
    checked_at = _now_iso()
    base = settings.PUBLIC_BASE_URL.rstrip("/")
    rows: List[Dict[str, Any]] = []

    # The public site and the console, actually fetched. The agent app is the single page at "/"
    # (static/index.html), so there is no /dashboard to fetch - that check failed from the day it
    # was written and taught everyone to ignore a red row.
    for name, path in (("Website", "/"), ("Team room", "/admin.html")):
        code, ms, body = _http_get(f"{base}{path}")
        if code is None:
            rows.append(_row(name, "fail", f"No answer from {base}{path}: {body}", checked_at))
        elif code >= 400:
            rows.append(_row(name, "fail", f"HTTP {code} from {base}{path}", checked_at))
        elif path == "/" and "resmara" not in body.lower():
            rows.append(_row(name, "warn", f"Answered {code} in {ms:.0f} ms but the page does not look like Resmara", checked_at))
        else:
            rows.append(_row(name, "ok", f"Answering {code} in {ms:.0f} ms", checked_at))

    # The API itself: if this handler is running, so is the API, but the version is the point.
    try:
        version = getattr(settings_module, "VERSION", None) or os.getenv("RESMARA_VERSION", "")
        rows.append(_row("API", "ok", f"Serving {version or 'this build'}", checked_at))
    except Exception as exc:                                     # noqa: BLE001
        rows.append(_row("API", "fail", str(exc)[:200], checked_at))

    # The database: one real query, not a pool flag.
    try:
        db.execute(text("SELECT 1"))
        users = db.query(User).count()
        campaigns = db.query(Boost).count()
        rows.append(_row("Database", "ok", f"Answering; {users} accounts, {campaigns} campaigns", checked_at))
    except Exception as exc:                                     # noqa: BLE001
        rows.append(_row("Database", "fail", f"Query failed: {exc}"[:200], checked_at))

    # The publisher: the clock is the local machine, so what can be checked here is the trace
    # it leaves. A shop with no published post yet is a warning, not a failure.
    try:
        last_published = (db.query(Event).filter(Event.event_type == "post_published")
                          .order_by(Event.id.desc()).first())
        failed = db.query(Post).filter(Post.publish_status == "failed").count()
        if last_published is None:
            rows.append(_row("Publisher", "warn",
                             f"Nothing published yet; {failed} post(s) waiting in the fail log" if failed
                             else "Nothing published yet", checked_at))
        else:
            age = ""
            if last_published.created_at:
                hours = (datetime.utcnow() - last_published.created_at.replace(tzinfo=None)).total_seconds() / 3600
                age = f"{hours:.0f} h ago" if hours >= 1 else "in the last hour"
            rows.append(_row("Publisher", "ok" if not failed else "warn",
                             f"Last post published {age}; {failed} failed post(s)" , checked_at))
    except Exception as exc:                                     # noqa: BLE001
        rows.append(_row("Publisher", "fail", str(exc)[:200], checked_at))

    # Every agent's Meta login, from the accounts table.
    try:
        rows.append(_meta_login_row(db.query(AdAccount).all(), checked_at))
    except Exception as exc:                                     # noqa: BLE001
        rows.append(_row("Meta logins", "fail", str(exc)[:200], checked_at))

    # The content engine (copy, plans, photos).
    try:
        if llm.llm_available():
            info = llm.engine_info()
            rows.append(_row("Content engine", "ok",
                             f"{info.get('host') or 'engine'} via {info.get('provider')}", checked_at))
        else:
            rows.append(_row("Content engine", "fail", "No key or local endpoint: builds cannot write copy", checked_at))
    except Exception as exc:                                     # noqa: BLE001
        rows.append(_row("Content engine", "fail", str(exc)[:200], checked_at))

    # Payments.
    try:
        if (os.getenv("STRIPE_SECRET_KEY") or "").strip():
            rows.append(_row("Payments", "ok", "Stripe key present", checked_at))
        else:
            rows.append(_row("Payments", "warn", "Stripe is not configured: checkout is off", checked_at))
    except Exception as exc:                                     # noqa: BLE001
        rows.append(_row("Payments", "fail", str(exc)[:200], checked_at))

    # Email.
    try:
        state = mail.delivery_state()
        if not state["configured"]:
            rows.append(_row("Email", "warn",
                             "No mail provider: reset links are handed over by hand", checked_at))
        elif state.get("sandbox"):
            # A provider being configured is not delivery: Resend's test sender only reaches the
            # account owner, so customer resets and confirmations go nowhere.
            rows.append(_row("Email", "warn", state["note"], checked_at))
        else:
            rows.append(_row("Email", "ok",
                             "Mail sends from %s" % (state.get("from") or "the configured sender"),
                             checked_at))
    except Exception as exc:                                     # noqa: BLE001
        rows.append(_row("Email", "fail", str(exc)[:200], checked_at))

    # The tags an ad blocker or a broken pasted snippet would silently remove.
    try:
        code, _ms, body = _http_get(f"{base}/")
        if code is None:
            rows.append(_row("Tracking tags", "warn", "Homepage unreachable, tags not checked", checked_at))
        else:
            # The ids are injected by static/tags.js from /api/public/tags, so "is it installed"
            # is two questions: does the page load the injector, and does the server hold an id?
            loads = "tags.js" in body
            configured = []
            try:
                import os as _os
                if (_os.getenv("GA4_MEASUREMENT_ID") or _os.getenv("RESMARA_GA4_MEASUREMENT_ID") or "").strip():
                    configured.append("Google tag")
                if (_os.getenv("CLARITY_PROJECT_ID") or _os.getenv("RESMARA_CLARITY_PROJECT_ID") or "").strip():
                    configured.append("Clarity")
            except Exception:                                    # noqa: BLE001
                configured = []
            if loads and len(configured) == 2:
                rows.append(_row("Tracking tags", "ok", "Both loaded on every page", checked_at))
            elif loads and configured:
                missing = "Clarity" if "Google tag" in configured else "Google tag"
                rows.append(_row("Tracking tags", "warn",
                                 f"{configured[0]} is live; {missing} has no id yet "
                                 f"(GA4_MEASUREMENT_ID / CLARITY_PROJECT_ID)", checked_at))
            elif loads:
                rows.append(_row("Tracking tags", "warn",
                                 "The loader is on every page but no id is set - nothing is being "
                                 "measured (GA4_MEASUREMENT_ID / CLARITY_PROJECT_ID)", checked_at))
            else:
                rows.append(_row("Tracking tags", "warn",
                                 "The homepage does not load tags.js, so no tag can run", checked_at))
    except Exception as exc:                                     # noqa: BLE001
        rows.append(_row("Tracking tags", "warn", str(exc)[:200], checked_at))

    return rows


@router.get("/admin/system-check")
def system_check(refresh: bool = False, x_resmara_token: Optional[str] = Header(None),
                 db: Session = Depends(get_db), current_user=Depends(get_current_user_optional)):
    """Every check below is run when this is called (a 60s cache stops a stuck tab hammering).

    The publishing clock on the always-awake machine calls this every fifteen minutes with
    ``X-Resmara-Token``, which is why the console can say "runs every 15 minutes" and mean it.
    """
    expected = (getattr(settings, "PUBLISH_TOKEN", "") or "").strip()
    machine = bool(expected) and (x_resmara_token or "").strip() == expected
    if not machine:
        if current_user is None or not team_access.can(current_user, "system"):
            raise HTTPException(status_code=403, detail="You do not have access to this part of the console")

    fresh_enough = (time.time() - _cache["at"]) < CHECK_TTL_SECONDS and _cache["rows"]
    if fresh_enough and not refresh:
        return {"checked_at": _cache["checked_at"], "cached": True, "checks": _cache["rows"]}
    rows = _run_checks(db)
    _cache.update({"at": time.time(), "rows": rows, "checked_at": _now_iso()})
    return {"checked_at": _cache["checked_at"], "cached": False, "checks": rows}


# --------------------------------------------------------------------------- releases
def _gh(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    token = settings.GITHUB_TOKEN.strip()
    if not token:
        raise RuntimeError("No GitHub token on the service (RESMARA_GITHUB_TOKEN)")
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               "Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=12.0, headers=headers) as client:
        response = client.get(f"{settings.GITHUB_API_BASE}/repos/{settings.GITHUB_REPO}{path}",
                              params=params or {})
    if response.status_code == 404:
        raise RuntimeError(f"GitHub says {settings.GITHUB_REPO} does not exist for this token")
    if response.status_code >= 400:
        raise RuntimeError(f"GitHub answered {response.status_code}: {response.text[:200]}")
    return response.json()


def _render(path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    key = settings.RENDER_API_KEY.strip()
    if not key:
        raise RuntimeError("No Render key on the service (RESMARA_RENDER_API_KEY)")
    headers = {"Authorization": f"Bearer {key}", "Accept": "application/json"}
    with httpx.Client(timeout=12.0, headers=headers) as client:
        response = client.get(f"{settings.RENDER_API_BASE}{path}", params=params or {})
    if response.status_code >= 400:
        raise RuntimeError(f"Render answered {response.status_code}: {response.text[:200]}")
    return response.json()


def _contains(commit: str, live: str) -> bool:
    """True when ``commit`` is already inside ``live`` (the same commit or an ancestor).

    The Releases page used to compare the two short SHAs by prefix, which only answers "live" for
    the one PR whose merge commit *is* the build being served. The moment anything else lands on
    top, every earlier PR reads "waiting" and the page looks like nothing ever shipped. GitHub's
    compare endpoint answers the real question: is the build ahead of this commit (or identical to
    it)? One call per merged PR, and a failure is a "not proven" rather than an exception.
    """
    a, b = (commit or "").strip(), (live or "").strip()
    if not a or not b:
        return False
    if b.startswith(a[:7]) or b.startswith(a):
        return True
    try:
        data = _gh(f"/compare/{a}...{b}")
    except Exception as exc:                                     # noqa: BLE001 - a check, not a crash
        log.info("compare %s...%s unavailable: %s", a[:7], b[:7], exc)
        return False
    return (data.get("status") or "") in ("ahead", "identical")


def _deploys(service_id: str, limit: int = 10) -> List[Dict[str, Any]]:
    data = _render(f"/services/{service_id}/deploys", {"limit": limit})
    out = []
    for item in data or []:
        deploy = item.get("deploy", item)
        commit = deploy.get("commit") or {}
        out.append({
            "id": deploy.get("id"),
            "status": deploy.get("status"),
            "commit": commit.get("id") or "",
            "message": (commit.get("message") or "").split("\n")[0][:200],
            "finished_at": deploy.get("finishedAt"),
            "created_at": deploy.get("createdAt"),
        })
    return out


def _side(files: List[str]) -> str:
    front = any(f.startswith("static/") for f in files)
    back = any(not f.startswith("static/") for f in files)
    if front and back:
        return "front end + back end"
    if back:
        return "back end"
    return "front end"


def _bullets(body: str) -> List[str]:
    out = []
    for line in (body or "").splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")) and len(stripped) > 3:
            out.append(stripped[2:].strip())
    return out


def _body_section(body: str) -> List[str]:
    """The PR's "Back end needed" list, if it has one."""
    lines = (body or "").splitlines()
    start = None
    for i, line in enumerate(lines):
        low = line.lower()
        if "back end" in low and (low.startswith("#") or low.startswith("**")):
            start = i + 1
            break
    if start is None:
        return []
    out = []
    for line in lines[start:]:
        stripped = line.strip()
        if stripped.startswith("#"):
            break
        if stripped[:2] in ("- ", "* ") or (stripped[:2].rstrip(".").isdigit() and stripped[:3].endswith(". ")):
            out.append(stripped.lstrip("-* ").strip())
    return out[:20]


_RELEASES_CACHE: Dict[str, Any] = {"at": 0.0, "payload": None}


@router.get("/admin/releases")
def releases(limit: int = 8, user=Depends(team_access.needs("build"))):
    """Open and recently merged pull requests, each with whether its commit is what is live.

    Cached briefly: answering it costs one GitHub compare call per merged PR (that is what makes
    "live" mean *contained in the build* rather than "happens to be the build"), which is several
    seconds of third-party latency. The console asks on every open, and a page that times out
    shows the previous answer - which is exactly how a freshly merged PR reads as still waiting.
    """
    fresh_for = float(os.getenv("RESMARA_RELEASES_CACHE_SECONDS", "60") or 60)
    # What is stored under "payload" is the answer itself (with the limit it was built for), so a
    # hit copies that: reading cached["payload"] is a KeyError on the very answer it just stored,
    # which is a 500 on the second open of the page rather than the cached one.
    cached = _RELEASES_CACHE.get("payload")
    same = cached and cached.get("limit") == limit
    if same and (time.time() - float(_RELEASES_CACHE.get("at") or 0)) < fresh_for:
        payload = dict(cached)
        payload.pop("limit", None)
        payload["cached"] = True
        return payload

    problems: List[str] = []
    pulls: List[Dict[str, Any]] = []
    deploys: List[Dict[str, Any]] = []
    service = settings.RENDER_SERVICE_ID.strip()

    try:
        pulls = _gh("/pulls", {"state": "all", "per_page": max(1, min(limit, 20)),
                               "sort": "updated", "direction": "desc"})
    except Exception as exc:                                     # noqa: BLE001
        problems.append(str(exc)[:300])
    if service:
        try:
            deploys = _deploys(service)
        except Exception as exc:                                 # noqa: BLE001
            problems.append(str(exc)[:300])
    else:
        problems.append("No Render service id on the service (RESMARA_RENDER_SERVICE_ID)")

    live = next((d for d in deploys if d["status"] in ("live", "deployed")), None)
    newest = deploys[0] if deploys else None
    live_commit = (live or {}).get("commit") or ""

    # One GitHub call per PR for its files, plus one compare call each to know whether its merge
    # commit is inside the live build. Sequentially that is ten round trips and a page that reads
    # as stuck; concurrently it is one round trip's worth of waiting.
    def _files_for(pull):
        try:
            return pull.get("number"), [f.get("filename", "") for f in
                                        _gh(f"/pulls/{pull['number']}/files", {"per_page": 100})]
        except Exception as exc:                                 # noqa: BLE001
            log.info("files for PR %s unavailable: %s", pull.get("number"), exc)
            return pull.get("number"), []

    files_by_pr = {}
    if pulls:
        with ThreadPoolExecutor(max_workers=8) as pool:
            for number, files in pool.map(_files_for, pulls):
                files_by_pr[number] = files

    # Same for the ancestry question: one compare call per merged PR, asked at the same time.
    merged_shas = [p.get("merge_commit_sha") or "" for p in pulls if p.get("state") != "open"]
    contained = {}
    if merged_shas and live_commit:
        def _ask(sha):
            return sha, _contains(sha, live_commit)

        with ThreadPoolExecutor(max_workers=8) as pool:
            for sha, inside in pool.map(_ask, [s for s in merged_shas if s]):
                contained[sha] = inside

    rows = []
    for pull in pulls:
        files = files_by_pr.get(pull.get("number")) or []

        sha = (pull.get("merge_commit_sha") or "")[:7]
        full_sha = pull.get("merge_commit_sha") or ""
        state = "open" if pull.get("state") == "open" else "merged"
        deploy = None
        live_at = None
        if state == "merged" and sha:
            if live_commit.startswith(sha):
                deploy, live_at = "live", (live or {}).get("finished_at")
            elif contained.get(full_sha):
                # This PR is already in the build being served; it just isn't the tip any more.
                # No timestamp of its own, so the card falls back to its merge date.
                deploy = "live"
            elif newest and newest["commit"].startswith(sha):
                deploy = "deploying"
            elif newest and newest["status"] in ("build_failed", "update_failed", "canceled", "pre_deploy_failed"):
                deploy = "failed"
            else:
                deploy = "waiting"
        rows.append({
            "number": pull.get("number"),
            "title": pull.get("title"),
            "author": (pull.get("user") or {}).get("login"),
            "state": state,
            "side": _side(files) if files else "unknown",
            "opened_at": pull.get("created_at"),
            "merged_at": pull.get("merged_at"),
            "commit": sha,
            "url": pull.get("html_url"),
            "summary": _bullets(pull.get("body") or "")[:8],
            "backend_tasks": _body_section(pull.get("body") or ""),
            "deploy": deploy,
            "live_at": live_at,
            "checks": None,
        })
    open_rows = [r for r in rows if r["state"] == "open"]
    merged_rows = [r for r in rows if r["state"] != "open"]
    # "connected" is what the page reads before it says anything: with no GitHub token the list
    # above is empty for a boring reason, and "Everything is live" would be a lie.
    connected = bool(getattr(settings, "GITHUB_TOKEN", "") or "") and not any(
        "GitHub" in p or "token" in p.lower() for p in problems)
    payload = {
        "repo": settings.GITHUB_REPO,
        "connected": connected,
        "live_commit": live_commit[:7] or None,
        "live_at": (live or {}).get("finished_at"),
        "latest_deploy": newest,
        "open": open_rows,
        "recent": merged_rows,
        "releases": rows,
        "problems": problems,
        "cached": False,
    }
    _RELEASES_CACHE.update({"at": time.time(), "payload": dict(payload, limit=limit)})
    return payload
