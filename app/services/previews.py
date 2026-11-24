"""Where a pull request's preview environment lives, according to GitHub.

Render creates a preview environment for a pull request and reports it as a GitHub
**Deployment** on that pull request's head commit; the address arrives in the deployment status'
``environment_url``. That record is the only public source for the link, so this module reads it
instead of inventing a URL from the PR number — a guessed host would 404 for every change that
has not finished building, and a 404 on a "Preview" button reads as a broken product.

Three things make the answer uncertain, and each is reported rather than smoothed over:

* **No preview exists** until a Blueprint is linked to this repository and the workspace is on
  the Pro plan. The button then says so; it does not open the production site.
* **Two repositories are tried.** The build room's rows come from the Releases payload, which
  reads the deploy mirror (``RESMARA_GITHUB_REPO``), while previews belong to pull requests on
  the code repo (``RESMARA_PREVIEW_REPO``). The numbering differs between them, so a PR number
  is looked up in both and the first one carrying a preview deployment wins.
* **A preview can be mid-build.** The newest status may have a URL before the service is up, so
  a ``success`` status is preferred over a newer pending one.

Nothing here writes: no deploy, no environment variable, no comment on the pull request.
"""
from __future__ import annotations

import time
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings

_cache: Dict[str, Dict[str, Any]] = {}


def _token() -> str:
    return (getattr(settings, "GITHUB_TOKEN", "") or "").strip()


def _gh(repo: str, path: str, params: Optional[Dict[str, Any]] = None) -> Any:
    """One GitHub call. A 404 is a fact about that repo; anything else is an error."""
    token = _token()
    if not token:
        raise RuntimeError("No GitHub token on the service (RESMARA_GITHUB_TOKEN)")
    headers = {"Accept": "application/vnd.github+json",
               "X-GitHub-Api-Version": "2022-11-28",
               "Authorization": f"Bearer {token}"}
    with httpx.Client(timeout=12.0, headers=headers) as client:
        response = client.get(f"{settings.GITHUB_API_BASE}/repos/{repo}{path}",
                              params=params or {})
    if response.status_code == 404:
        raise LookupError(f"{repo}{path} answered 404")
    if response.status_code >= 400:
        raise RuntimeError(f"GitHub answered {response.status_code}: {response.text[:200]}")
    return response.json()


def repos() -> List[str]:
    """The code repo first (previews live there), then the mirror the board's PR numbers use."""
    out: List[str] = []
    for name in ((getattr(settings, "PREVIEW_REPO", "") or "").strip(),
                 (getattr(settings, "GITHUB_REPO", "") or "").strip()):
        if name and name not in out:
            out.append(name)
    return out


def _pick(dep: Dict[str, Any], statuses: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
    """The status whose URL is worth opening: a finished one before a newer unfinished one."""
    with_url = [st for st in statuses if (st.get("environment_url") or st.get("target_url"))]
    if not with_url:
        return None
    for st in with_url:
        if (st.get("state") or "") == "success":
            return st
    return with_url[0]


def preview_for_pr(pr: int) -> Dict[str, Any]:
    """``{ok, pr, url, state, environment, repo, reason, why}`` — never raises."""
    key = str(pr)
    cached = _cache.get(key)
    ttl = max(1, int(getattr(settings, "PREVIEW_CACHE_SECONDS", 60) or 60))
    if cached and (time.monotonic() - cached["at"]) < ttl:
        return dict(cached["value"])

    out: Dict[str, Any] = {"ok": False, "pr": pr, "url": None, "state": None,
                           "environment": None, "repo": None, "reason": None, "why": ""}
    if not _token():
        out.update(reason="github_not_configured",
                   why="No GitHub token on the service, so the preview link cannot be read. "
                       "RESMARA_GITHUB_TOKEN is what asks GitHub about the pull request.")
        return out

    seen_repo = False
    for repo in repos():
        try:
            pull = _gh(repo, f"/pulls/{int(pr)}")
        except LookupError:
            continue                      # no such PR there: try the other repository
        except Exception as exc:          # noqa: BLE001 - a check, not a crash
            out.update(reason="github_error", repo=repo,
                       why=f"GitHub could not answer for {repo}: {str(exc)[:200]}")
            return _remember(key, out)
        seen_repo = True
        sha = ((pull or {}).get("head") or {}).get("sha") or ""
        # The FIRST repository that knows the PR is the one worth naming: the numbers overlap
        # between the code repo and the mirror, and reporting whichever was tried last made a
        # "no preview yet" answer point at the mirror for a PR that lives on the code repo.
        out["repo"] = out["repo"] or repo
        if not sha:
            continue
        try:
            deployments = _gh(repo, "/deployments", {"sha": sha, "per_page": 20}) or []
        except Exception as exc:          # noqa: BLE001 - reported
            out.update(reason="github_error",
                       why=f"GitHub could not list deployments for {repo}: {str(exc)[:200]}")
            return _remember(key, out)
        for dep in deployments:
            try:
                statuses = _gh(repo, f"/deployments/{dep.get('id')}/statuses",
                               {"per_page": 10}) or []
            except Exception:             # noqa: BLE001 - one unreadable deployment is not fatal
                continue
            status = _pick(dep, statuses)
            if not status:
                continue
            url = (status.get("environment_url") or status.get("target_url") or "").strip()
            out.update(ok=True, url=url, state=status.get("state"),
                       environment=dep.get("environment"), reason=None, why="")
            return _remember(key, out)

    if not seen_repo:
        out.update(reason="no_pull_request",
                   why=f"No pull request #{pr} exists in "
                       + " or ".join(repos())
                       + ", so there is no preview to open.")
    elif not out.get("reason"):
        out.update(reason="no_preview",
                   why="This pull request has no preview environment yet. Render creates one when "
                       "a Blueprint is linked to this repository (Pro workspace) and the pull "
                       "request is against the Blueprint's branch; it appears within a minute or "
                       "two of a push.")
    return _remember(key, out)


def _remember(key: str, value: Dict[str, Any]) -> Dict[str, Any]:
    _cache[key] = {"at": time.monotonic(), "value": dict(value)}
    return value


def forget(pr: Optional[int] = None) -> None:
    """Drop the cached answer (tests, and after a known push)."""
    if pr is None:
        _cache.clear()
    else:
        _cache.pop(str(pr), None)
