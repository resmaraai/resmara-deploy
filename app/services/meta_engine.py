"""The Meta connection engine (Engine 1, Parts B and C).

CONNECT -> SAVE -> CHECK -> DECIDE -> TELL, then WATCH and RE-CHECK.
Spec: docs/engines/meta-integration-engine.md. Brain: docs/engines/engine-1-brain.md.

Rules this file keeps:

* Every fact comes straight from Meta (checks C1-C7). No model decides whether a Page or a token
  is OK, and nothing Meta didn't say is ever shown.
* One connection per agent (``MetaConnection``), saved on every Facebook login even with no Page
  and no ad account, and overwritten - never ``or``-ed - on every reconnect and Check again.
* The answers become outcome keys from one fixed table (``OUTCOMES``): each key has its line,
  what the campaign can still do, and what Fix it now opens. At most three lines are shown,
  most important first.
* One Page, one Resmara account.
* Meta being down changes nothing for the agent: the last good result stands and only the Team
  room hears about it, after 6 hours.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx

from app.core.config import settings
from app.db.session import AdAccount, Boost, Event, MetaConnection, Post, User

log = logging.getLogger("resmara.meta_engine")

GRAPH_TIMEOUT = 20
SIGN_IN_CACHE_MINUTES = 10
EXPIRING_DAYS = 7
UNREACHABLE_ALERT_HOURS = 6
HELD_RELEASE_HOURS = 24

PAGE_SCOPES = {"pages_show_list", "pages_manage_posts"}
IG_SCOPES = {"instagram_basic", "instagram_content_publish"}
AD_SCOPES = {"ads_management"}

# Meta error codes that mean "try later", never "broken": rate limits and service trouble.
RETRY_CODES = {1, 2, 4, 17, 32, 341, 613, 80001, 80004}
# Meta error codes that mean the login itself no longer works.
DEAD_TOKEN_CODES = {190, 102, 463, 467}

# --------------------------------------------------------------------------- the outcome table
# rank: lower is more important. fix.kind tells the front end what Fix it now opens:
#   dialog (the Facebook dialog, re-asking for what was turned off), setup (a Setup guide step),
#   page_picker, ig_switch, reconnect, book (a call), meta_billing (Meta's billing page, new tab).
OUTCOMES: Dict[str, Dict[str, Any]] = {
    "token_dead": {
        "rank": 0, "line": "Your Meta connection needs refreshing. Your posts are on hold until you reconnect.",
        "means": "Nothing posts until you reconnect. Your posts are held, not lost.",
        "fix": {"kind": "reconnect"}, "email": True},
    "token_expiring": {
        "rank": 1, "line": "Your Meta connection needs a quick refresh.",
        "means": "Everything still works for now. Reconnect takes two clicks.",
        "fix": {"kind": "reconnect"}},
    "page_taken": {
        "rank": 2, "line": ("This Page is already connected to another Resmara account. If that account is "
                            "yours, log in with the Facebook you used for it. If not, contact us and we'll sort it out."),
        "means": "Until it's sorted, you download each post and share it yourself.",
        "fix": {"kind": "page_picker"}},
    "scope_declined_page": {
        "rank": 3, "line": "Resmara can't post to your Page because a permission was turned off.",
        "means": "Until it's fixed, you download each post and share it yourself.",
        "fix": {"kind": "dialog", "rerequest": True}},
    "no_page": {
        "rank": 4, "line": "No Facebook business Page is connected.",
        "means": "Until a Page is connected, you download each post and share it yourself.",
        "fix": {"kind": "setup", "step": "page"}},
    "page_no_control": {
        "rank": 5, "line": "You don't have full control of your Facebook Page.",
        "means": "Until it's fixed, you download each post and share it yourself.",
        "fix": {"kind": "setup", "step": "admin"}, "email": True},
    "page_unpublished": {
        "rank": 6, "line": "Your Facebook Page is unpublished, so no one can see it.",
        "means": "Until it's published, you download each post and share it yourself.",
        "fix": {"kind": "setup", "step": "page"}},
    "several_pages": {
        "rank": 7, "line": "Which Page is your business?",
        "means": "Pick your business Page and Resmara posts there.",
        "fix": {"kind": "page_picker"}},
    "scope_declined_ig": {
        "rank": 8, "line": "Instagram posting was turned off when you connected.",
        "means": "Your posts go to your Facebook Page only.",
        "fix": {"kind": "dialog", "rerequest": True}},
    "ig_not_linked": {
        "rank": 9, "line": "Your Instagram isn't connected as a business account.",
        "means": "Your posts go to your Facebook Page only, not Instagram, until it's fixed.",
        "fix": {"kind": "ig_switch"}},
    "scope_declined_ads": {
        "rank": 10, "line": "Ads were turned off when you connected.",
        "means": "Your posts go out, but your listing ad is off.",
        "fix": {"kind": "dialog", "rerequest": True}},
    "no_ad_account": {
        "rank": 11, "line": "You don't have a Meta ad account yet, so your listing ad is off.",
        "means": "Your posts go out, but your listing ad is off until it's fixed.",
        "fix": {"kind": "setup", "step": "ads"}},
    "ad_no_payment": {
        "rank": 12, "line": "Your ad account can't run ads yet. It needs a payment method.",
        "means": "Your posts go out, but your listing ad is off until it's fixed.",
        "fix": {"kind": "setup", "step": "ads"}},
    "ad_disabled": {
        "rank": 13, "line": "Meta has disabled your ad account.",
        "means": "Your posts go out, but your listing ad is off.",
        "fix": {"kind": "book"}, "email": True},
    "ad_unpaid": {
        "rank": 14, "line": "Your ad account has an unpaid balance with Meta.",
        "means": "Your posts go out, but your listing ad is off until it's paid.",
        "fix": {"kind": "meta_billing", "url": "https://business.facebook.com/billing_hub/payment_settings"},
        "email": True},
    "ad_in_review": {
        "rank": 15, "line": "Meta is reviewing your ad account. Your ad will start when it's cleared.",
        "means": "Your posts go out. Your ad starts when Meta clears the account.",
        "fix": {"kind": None}},
}
# Shown on screens that need it but never as a notice line.
SILENT = {"ok", "meta_unreachable"}

# Never-asked (not declined) Page permissions: same key, the honest line for it.
PAGE_SCOPES_NOT_ASKED_LINE = "Resmara needs your permission to post to your Facebook Page."


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value: Any) -> Optional[datetime]:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value


# --------------------------------------------------------------------------- DECIDE (pure)
def ad_status_issue(account_status: Optional[int], has_funding: Optional[bool]) -> Optional[str]:
    """Meta's account_status (and the funding source) as one outcome key, or None when it can spend.

    Returns "unknown" for statuses the spec says never to alarm on.
    """
    if account_status is None:
        return "unknown"
    s = int(account_status)
    if s == 1:
        return None if has_funding else "ad_no_payment"
    if s in (2, 101):
        return "ad_disabled"
    if s in (3, 8):
        return "ad_unpaid"
    if s in (7, 9):
        return "ad_in_review"
    return "unknown"


def can_post(tasks: Optional[List[str]]) -> bool:
    tasks = {str(t).upper() for t in (tasks or [])}
    return bool(tasks & {"CREATE_CONTENT", "MANAGE"})


def pick_ad_account(accounts: List[Dict[str, Any]], preferred_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """The ad account in use: the one already chosen if Meta still lists it, else the best one."""
    if not accounts:
        return None
    if preferred_id:
        for a in accounts:
            if a.get("id") == preferred_id:
                return a
    def score(a):
        return (ad_status_issue(a.get("account_status"), a.get("has_funding")) is None,
                a.get("account_status") == 1)
    return sorted(accounts, key=score, reverse=True)[0]


def decide(facts: Dict[str, Any], *, chosen_page_id: Optional[str] = None,
           page_taken: bool = False, preferred_ad_account: Optional[str] = None) -> Dict[str, Any]:
    """Meta's answers -> outcome keys (ranked), capabilities and the page/ad account in use.

    ``facts``: {token_valid: bool|None, expires_at: datetime|None, granted: [..], declined: [..],
    pages: [{id, name, tasks, published, ig_id, ...}] | None, ad_accounts: [...] | None}.
    ``None`` means Meta didn't answer that question; it never becomes a false alarm.
    """
    issues: List[str] = []
    granted = set(facts.get("granted") or [])
    declined = set(facts.get("declined") or [])
    out: Dict[str, Any] = {"page": None, "ad_account": None, "page_scopes_asked": True}

    if facts.get("token_valid") is False:
        out.update(issues=["token_dead"], capabilities={
            "fb_post": False, "ig_post": False, "ad": False,
            "download_mode": True, "campaigns_allowed": True, "held": True})
        return out

    exp = _aware(facts.get("expires_at"))
    if exp is not None and exp - _now() < timedelta(days=EXPIRING_DAYS):
        issues.append("token_expiring")

    pages = facts.get("pages")
    page = None
    page_ok = False
    if PAGE_SCOPES & declined:
        issues.append("scope_declined_page")
    elif facts.get("perms_known") and not PAGE_SCOPES <= granted:
        issues.append("scope_declined_page")
        out["page_scopes_asked"] = False
    elif pages is not None:
        if not pages:
            issues.append("no_page")
        else:
            if chosen_page_id:
                page = next((p for p in pages if p.get("id") == chosen_page_id), None)
            if page is None and len(pages) == 1:
                page = pages[0]
            if page is None:
                issues.append("several_pages")
            elif page_taken:
                issues.append("page_taken")
            else:
                if not can_post(page.get("tasks")):
                    issues.append("page_no_control")
                if page.get("published") is False:
                    issues.append("page_unpublished")
                page_ok = not ({"page_no_control", "page_unpublished"} & set(issues))
    out["page"] = page

    ig_ok = False
    if page_ok:
        if IG_SCOPES & declined:
            issues.append("scope_declined_ig")
        elif not page.get("ig_id"):
            issues.append("ig_not_linked")
        else:
            ig_ok = True

    ad_ok = False
    accounts = facts.get("ad_accounts")
    if AD_SCOPES & declined:
        issues.append("scope_declined_ads")
    elif accounts is not None:
        if not accounts:
            issues.append("no_ad_account")
        else:
            acct = pick_ad_account(accounts, preferred_ad_account)
            out["ad_account"] = acct
            problem = ad_status_issue(acct.get("account_status"), acct.get("has_funding"))
            if problem is None:
                ad_ok = True
            elif problem != "unknown":
                issues.append(problem)

    issues = sorted(dict.fromkeys(issues), key=lambda k: OUTCOMES[k]["rank"])
    if "no_page" in issues and "page_no_control" in issues:
        issues.remove("page_no_control")
    fb_post = page_ok
    out["issues"] = issues
    out["capabilities"] = {
        "fb_post": fb_post,
        "ig_post": fb_post and ig_ok,
        "ad": fb_post and ad_ok,
        "download_mode": not fb_post,
        "campaigns_allowed": True,
        "held": False,
    }
    return out


def lines(issues: List[str], *, page_scopes_asked: bool = True, limit: int = 3) -> List[Dict[str, Any]]:
    """What the agent reads: at most three lines, most important first, each with its fix."""
    shown = [k for k in issues if k in OUTCOMES][:limit]
    out = []
    for k in shown:
        o = OUTCOMES[k]
        line = o["line"]
        if k == "scope_declined_page" and not page_scopes_asked:
            line = PAGE_SCOPES_NOT_ASKED_LINE
        out.append({"key": k, "line": line, "means": o["means"], "fix": dict(o["fix"])})
    return out


def headline(issues: List[str], capabilities: Dict[str, Any]) -> str:
    """The result headline from Part C, section 4."""
    if not issues:
        return "You're all set. Resmara can post and run your ads."
    if issues[0] == "several_pages":
        return "Which Page is your business?"
    if issues[0] == "page_taken":
        return "This Page is already connected to another Resmara account."
    if capabilities.get("fb_post"):
        return "You're ready to go. A couple of things will make it better."
    return "Resmara can build everything, but can't post for you yet."


# --------------------------------------------------------------------------- CHECK (Meta calls)
class MetaUnreachable(Exception):
    """Meta didn't answer, or asked us to wait. Never shown to the agent as a problem."""


def _error(body: Dict[str, Any]) -> Dict[str, Any]:
    err = body.get("error") if isinstance(body, dict) else None
    return err if isinstance(err, dict) else {}


async def _get(client: httpx.AsyncClient, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    try:
        resp = await client.get(f"{settings.graph_base}{path}", params=params)
    except (httpx.TimeoutException, httpx.TransportError) as exc:
        raise MetaUnreachable(type(exc).__name__) from exc
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001
        body = {}
    if resp.status_code >= 500:
        raise MetaUnreachable(f"HTTP {resp.status_code}")
    err = _error(body)
    if err and int(err.get("code") or 0) in RETRY_CODES:
        raise MetaUnreachable(f"Meta code {err.get('code')}")
    return body if isinstance(body, dict) else {}


async def fetch_facts(user_token: str) -> Dict[str, Any]:
    """Ask Meta C1-C7. Raises MetaUnreachable when Meta can't answer right now."""
    facts: Dict[str, Any] = {"token_valid": None, "expires_at": None, "granted": [], "declined": [],
                             "perms_known": False, "pages": None, "ad_accounts": None, "me": {},
                             "error": None}
    if not user_token:
        facts["token_valid"] = False
        return facts
    async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
        # C1: the login itself.
        if settings.META_CLIENT_ID and settings.META_CLIENT_SECRET:
            dbg = await _get(client, "/debug_token", {
                "input_token": user_token,
                "access_token": f"{settings.META_CLIENT_ID}|{settings.META_CLIENT_SECRET}"})
            data = dbg.get("data") or {}
            if data:
                facts["token_valid"] = bool(data.get("is_valid"))
                if data.get("expires_at"):
                    facts["expires_at"] = datetime.fromtimestamp(int(data["expires_at"]), tz=timezone.utc)
        me = await _get(client, "/me", {"fields": "id,name,picture{url}", "access_token": user_token})
        err = _error(me)
        if err:
            if int(err.get("code") or 0) in DEAD_TOKEN_CODES:
                facts["token_valid"] = False
                facts["error"] = err
                return facts
            facts["error"] = err
        else:
            facts["me"] = me
            if facts["token_valid"] is None:
                facts["token_valid"] = True
        if facts["token_valid"] is False:
            return facts

        # C2: permissions ticked and unticked.
        perms = await _get(client, "/me/permissions", {"access_token": user_token})
        if perms.get("data") is not None:
            facts["perms_known"] = True
            for p in perms.get("data") or []:
                (facts["granted"] if p.get("status") == "granted" else facts["declined"]).append(p.get("permission"))

        # C3-C6: Pages, posting rights, published, linked Instagram (always re-queried).
        pages = await _get(client, "/me/accounts", {
            "access_token": user_token, "limit": 100,
            "fields": ("id,name,tasks,is_published,access_token,picture{url},website,phone,"
                       "single_line_address,category,about,"
                       "instagram_business_account{id,username,profile_picture_url}")})
        if pages.get("data") is not None:
            facts["pages"] = [{
                "id": p.get("id"), "name": p.get("name"), "tasks": p.get("tasks") or [],
                "published": p.get("is_published"),
                "picture": ((p.get("picture") or {}).get("data") or {}).get("url"),
                "access_token": p.get("access_token"),
                "ig_id": (p.get("instagram_business_account") or {}).get("id"),
                "ig_username": (p.get("instagram_business_account") or {}).get("username"),
                "ig_picture": (p.get("instagram_business_account") or {}).get("profile_picture_url"),
                "info": {k: p.get(k) for k in ("website", "phone", "single_line_address", "category", "about") if p.get(k)},
            } for p in pages.get("data") or [] if p.get("id")]

        # C7: ad accounts, their status and a payment method (brokerage-owned ones too, if listed).
        ads = await _get(client, "/me/adaccounts", {
            "access_token": user_token, "limit": 100,
            "fields": "id,name,account_status,currency,funding_source_details,business{name}"})
        if ads.get("data") is not None:
            facts["ad_accounts"] = [{
                "id": a.get("id"), "name": a.get("name"), "currency": a.get("currency") or "USD",
                "account_status": a.get("account_status"),
                "has_funding": bool(a.get("funding_source_details")),
                "owner": (a.get("business") or {}).get("name"),
            } for a in ads.get("data") or [] if a.get("id")]
    return facts


# --------------------------------------------------------------------------- SAVE
async def long_lived(token: str):
    """Swap a fresh 1-2 hour login token for the ~60-day one. Keeps the original if Meta says no."""
    if not (token and settings.META_CLIENT_ID and settings.META_CLIENT_SECRET):
        return token, None
    try:
        async with httpx.AsyncClient(timeout=GRAPH_TIMEOUT) as client:
            r = await client.get(f"{settings.graph_base}/oauth/access_token", params={
                "grant_type": "fb_exchange_token", "client_id": settings.META_CLIENT_ID,
                "client_secret": settings.META_CLIENT_SECRET, "fb_exchange_token": token})
        data = r.json() if r.content else {}
    except Exception:  # noqa: BLE001
        return token, None
    if not data.get("access_token"):
        return token, None
    exp = _now() + timedelta(seconds=int(data["expires_in"])) if data.get("expires_in") else None
    return data["access_token"], exp


def connection_for(db, user_id: int) -> Optional[MetaConnection]:
    return db.query(MetaConnection).filter(MetaConnection.user_id == user_id).first()


def save_login(db, user: User, token: str, *, expires_at: Optional[datetime] = None,
               fb_user_id: Optional[str] = None, fb_user_name: Optional[str] = None) -> MetaConnection:
    """Every successful Facebook login lands here: Part A's sign-in and Connect/Reconnect alike.

    The token is overwritten. The Page choice survives (it's re-validated by the check that
    follows), everything else Meta knows is re-read by that check.
    """
    conn = connection_for(db, user.id)
    if conn is None:
        conn = MetaConnection(user_id=user.id, issues=[], issue_log=[], capabilities={},
                              pages_available=[], scopes_granted=[], scopes_declined=[],
                              breakage_emails={}, page_info={})
        db.add(conn)
    if token:
        conn.access_token = token
    conn.token_expires_at = expires_at
    conn.token_status = "healthy"
    if fb_user_id:
        conn.fb_user_id = str(fb_user_id)
    if fb_user_name:
        conn.fb_user_name = fb_user_name
    db.flush()
    return conn


def _page_taken(db, user_id: int, page_id: Optional[str]) -> bool:
    if not page_id:
        return False
    other = (db.query(MetaConnection)
             .filter(MetaConnection.page_id == page_id, MetaConnection.user_id != user_id)
             .first())
    return other is not None


def _update_issue_log(conn: MetaConnection, issues: List[str], now: datetime) -> None:
    """The setup to-do list: items appear when found and tick off on the next check that passes."""
    log_rows = [dict(r) for r in (conn.issue_log or [])]
    open_keys = {r["key"] for r in log_rows if not r.get("fixed_at")}
    for row in log_rows:
        if not row.get("fixed_at") and row["key"] not in issues:
            row["fixed_at"] = now.isoformat()
    for key in issues:
        if key not in open_keys:
            log_rows.append({"key": key, "found_at": now.isoformat(), "fixed_at": None})
    conn.issue_log = log_rows[-60:]


def _sync_ad_account(db, user: User, conn: MetaConnection, acct: Optional[Dict[str, Any]], token: str) -> None:
    """Keep ``ad_accounts`` true for the ad engine and billing, and point the connection at it."""
    rows = (db.query(AdAccount)
            .filter(AdAccount.user_id == user.id, AdAccount.platform == "meta").all())
    for row in rows:
        # The Page and Instagram follow the agent's choice everywhere; never an old value.
        row.page_id = conn.page_id
        row.ig_user_id = conn.ig_user_id
    if acct is None:
        conn.ad_account_id = None
        conn.ad_account_name = None
        conn.ad_account_owner = None
        return
    row = next((r for r in rows if r.advertiser_id == acct["id"]), None)
    if row is None:
        row = AdAccount(user_id=user.id, platform="meta", advertiser_id=acct["id"],
                        currency=acct.get("currency") or "USD", budget=5000.0)
        db.add(row)
    row.account_name = acct.get("name") or row.account_name
    row.access_token = token
    row.token_expires_at = conn.token_expires_at
    row.token_status = "healthy"
    row.token_checked_at = _now()
    row.account_status = acct.get("account_status")
    row.account_checked_at = _now()
    row.funding_status = "has_funding" if acct.get("has_funding") else "no_funding"
    row.page_id = conn.page_id
    row.ig_user_id = conn.ig_user_id
    row.is_active = True
    db.flush()
    conn.ad_account_id = row.id
    conn.ad_account_name = row.account_name
    conn.ad_account_owner = acct.get("owner")


def apply(db, user: User, conn: MetaConnection, facts: Dict[str, Any], source: str) -> Dict[str, Any]:
    """Write a check's answers onto the connection. Returns the decision."""
    now = _now()
    pages = facts.get("pages")
    if pages is not None:
        conn.pages_available = [{k: p.get(k) for k in ("id", "name", "picture", "tasks", "published",
                                                         "ig_id", "ig_username")} for p in pages]
    chosen = conn.page_id if conn.page_chosen else None
    candidate = chosen
    if pages is not None and not candidate and len(pages) == 1:
        candidate = pages[0]["id"]
    preferred_ad = None
    if conn.ad_account_id:
        row = db.query(AdAccount).filter(AdAccount.id == conn.ad_account_id).first()
        preferred_ad = row.advertiser_id if row else None
    decision = decide(facts, chosen_page_id=chosen,
                      page_taken=_page_taken(db, user.id, candidate),
                      preferred_ad_account=preferred_ad)

    me = facts.get("me") or {}
    if me.get("id"):
        conn.fb_user_id = str(me["id"])
        conn.fb_user_name = me.get("name") or conn.fb_user_name
        conn.fb_user_picture = ((me.get("picture") or {}).get("data") or {}).get("url") or conn.fb_user_picture
    if facts.get("perms_known"):
        conn.scopes_granted = list(facts.get("granted") or [])
        conn.scopes_declined = list(facts.get("declined") or [])
    if facts.get("expires_at"):
        conn.token_expires_at = facts["expires_at"]

    page = decision.get("page")
    if "page_taken" in decision["issues"]:
        page = None
    if pages is not None:
        # Overwrite, never `or`: what Meta says now is the truth.
        conn.page_id = page.get("id") if page else None
        conn.page_name = page.get("name") if page else None
        conn.page_picture = page.get("picture") if page else None
        conn.page_tasks = page.get("tasks") if page else []
        conn.page_published = page.get("published") if page else None
        conn.page_info = page.get("info") if page else {}
        conn.page_access_token = (page.get("access_token") if page else None) or None
        conn.ig_user_id = page.get("ig_id") if page else None
        conn.ig_username = page.get("ig_username") if page else None
        conn.ig_picture = page.get("ig_picture") if page else None
        if page and len(pages) == 1:
            conn.page_chosen = True
        if not page and not ({"several_pages"} & set(decision["issues"])):
            conn.page_chosen = False
    if facts.get("ad_accounts") is not None:
        _sync_ad_account(db, user, conn, decision.get("ad_account"), conn.access_token or "")

    caps = decision["capabilities"]
    issues = decision["issues"]
    if "token_dead" in issues:
        conn.token_status = "needs_reconnect"
    elif "token_expiring" in issues:
        conn.token_status = "expiring"
    else:
        conn.token_status = "healthy"

    before = (list(conn.issues or []), dict(conn.capabilities or {}))
    was_dead = "token_dead" in before[0]
    conn.issues = issues
    conn.capabilities = caps
    conn.last_checked_at = now
    conn.last_check_source = source
    conn.unreachable_since = None
    _update_issue_log(conn, issues, now)
    if caps.get("fb_post") and not user.meta_connected_at:
        user.meta_connected_at = now
    if (before[0], before[1]) != (issues, caps):
        db.add(Event(user_id=user.id, event_type="meta_outcome_changed",
                     payload={"from": before[0], "to": issues, "capabilities": caps, "source": source}))
    db.commit()
    if was_dead and "token_dead" not in issues:
        release_held(db, user)
    if caps.get("held"):
        hold_due(db, user)
    return {**decision, "page_scopes_asked": decision.get("page_scopes_asked", True)}


async def check(db, user: User, source: str = "check_again", *, force: bool = True) -> Dict[str, Any]:
    """Run C1-C7 for one agent and save the result. Always returns the agent's current status."""
    conn = connection_for(db, user.id) or _adopt_legacy(db, user)
    if conn is None:
        return status(db, user)
    if not force and conn.last_checked_at and _now() - _aware(conn.last_checked_at) < timedelta(minutes=SIGN_IN_CACHE_MINUTES):
        return status(db, user)
    try:
        facts = await fetch_facts(conn.access_token or "")
    except MetaUnreachable as exc:
        conn.unreachable_since = conn.unreachable_since or _now()
        db.add(Event(user_id=user.id, event_type="meta_unreachable", payload={"source": source, "why": str(exc)[:160]}))
        db.commit()
        return status(db, user, unreachable=True)
    except Exception as exc:  # noqa: BLE001 - a broken check never breaks the page
        log.warning("meta check failed for user %s: %s", user.id, exc)
        return status(db, user, unreachable=True)
    if facts.get("error") and not facts.get("me"):
        _log_unknown_error(db, user, facts["error"], source)
    apply(db, user, conn, facts, source)
    return status(db, user)


def _adopt_legacy(db, user: User) -> Optional[MetaConnection]:
    """An agent connected before this table existed: build their connection from the ad account row."""
    acct = (db.query(AdAccount)
            .filter(AdAccount.user_id == user.id, AdAccount.platform == "meta", AdAccount.is_active.is_(True))
            .order_by(AdAccount.id.desc()).first())
    if acct is None or not (acct.access_token or "") or (acct.access_token or "").startswith("demo"):
        return None
    conn = save_login(db, user, acct.access_token, expires_at=acct.token_expires_at)
    if acct.page_id:
        conn.page_id = acct.page_id
        conn.page_chosen = True
    conn.ad_account_id = acct.id
    db.commit()
    return conn


def _log_unknown_error(db, user: User, err: Dict[str, Any], source: str) -> None:
    """Errors the table doesn't know are kept for the Weekly Meta review (Part B, section 7)."""
    db.add(Event(user_id=user.id, event_type="meta_unknown_error",
                 payload={"code": err.get("code"), "subcode": err.get("error_subcode"),
                          "message": str(err.get("message") or "")[:300], "source": source}))
    db.commit()


# --------------------------------------------------------------------------- the Page picker
def set_page(db, user: User, page_id: str) -> Dict[str, Any]:
    """Change Page / Which Page is your business? Saves the pick; the caller re-runs the check."""
    conn = connection_for(db, user.id)
    if conn is None:
        return {"ok": False, "error": "not_connected"}
    known = {p.get("id") for p in (conn.pages_available or [])}
    if page_id not in known:
        return {"ok": False, "error": "unknown_page"}
    if _page_taken(db, user.id, page_id):
        return {"ok": False, "error": "page_taken", "message": OUTCOMES["page_taken"]["line"]}
    conn.page_id = page_id
    conn.page_chosen = True
    db.commit()
    return {"ok": True}


# --------------------------------------------------------------------------- TELL
def status(db, user: User, *, unreachable: bool = False) -> Dict[str, Any]:
    """Everything a screen needs: names and photos, the lines, the to-do list, last checked."""
    conn = connection_for(db, user.id)
    if conn is None:
        return {"connected": False, "facebook": False, "issues": [], "lines": [],
                "capabilities": {"fb_post": False, "ig_post": False, "ad": False,
                                 "download_mode": True, "campaigns_allowed": False},
                "headline": "Log in with Facebook to get started.", "todo": [], "done": []}
    caps = dict(conn.capabilities or {"campaigns_allowed": True, "download_mode": True})
    issues = list(conn.issues or [])
    asked = PAGE_SCOPES <= set(conn.scopes_granted or []) or bool(PAGE_SCOPES & set(conn.scopes_declined or []))
    shown = lines(issues, page_scopes_asked=asked or not conn.last_checked_at)
    log_rows = conn.issue_log or []
    todo = [dict(r, **{"line": OUTCOMES[r["key"]]["line"], "means": OUTCOMES[r["key"]]["means"],
                       "fix": OUTCOMES[r["key"]]["fix"]})
            for r in sorted([r for r in log_rows if not r.get("fixed_at") and r["key"] in issues],
                            key=lambda r: OUTCOMES.get(r["key"], {"rank": 99})["rank"])]
    done = [dict(r, line=OUTCOMES.get(r["key"], {}).get("line", r["key"]))
            for r in log_rows if r.get("fixed_at")][-10:]
    return {
        "connected": bool(caps.get("fb_post")),
        "facebook": True,
        "facebook_name": conn.fb_user_name,
        "facebook_picture": conn.fb_user_picture,
        "page": {"id": conn.page_id, "name": conn.page_name, "picture": conn.page_picture,
                 "published": conn.page_published} if conn.page_id else None,
        "instagram": {"username": conn.ig_username, "picture": conn.ig_picture} if conn.ig_user_id else None,
        "ad_account": {"name": conn.ad_account_name, "owner": conn.ad_account_owner}
                      if conn.ad_account_id else None,
        "pages": [{k: p.get(k) for k in ("id", "name", "picture", "ig_username")} | {"has_instagram": bool(p.get("ig_id"))}
                  for p in (conn.pages_available or [])],
        "issues": issues,
        "lines": shown,
        "fix": shown[0]["fix"] if shown else None,
        "headline": headline(issues, caps),
        "capabilities": caps,
        "todo": todo,
        "done": done,
        "last_checked_at": conn.last_checked_at.isoformat() if conn.last_checked_at else None,
        "checking_unavailable": bool(unreachable),
        "brand_hints": dict(conn.page_info or {}),
    }


def legacy_checks(st: Dict[str, Any]) -> List[Dict[str, Any]]:
    """The four-line shape the existing screens read, now from the real answers and with names."""
    issues = set(st.get("issues") or [])
    page = st.get("page") or {}
    ig = st.get("instagram") or {}
    ad = st.get("ad_account") or {}
    no_page = bool(issues & {"no_page", "scope_declined_page", "several_pages", "page_taken", "token_dead"}) or not page
    unreach = st.get("checking_unavailable")
    def detail(ok, good, bad):
        if unreach and not ok:
            return "We couldn't check this right now"
        return good if ok else bad
    page_ok = not no_page and "page_unpublished" not in issues
    admin_ok = page_ok and "page_no_control" not in issues
    ig_ok = page_ok and not (issues & {"ig_not_linked", "scope_declined_ig"}) and bool(ig)
    ad_ok = bool(st.get("capabilities", {}).get("ad"))
    first = {l["key"]: l for l in st.get("lines") or []}
    def fix_for(*keys):
        for k in keys:
            if k in first:
                return first[k]["line"]
        return None
    return [
        {"key": "page", "label": "Facebook Page found", "ok": page_ok,
         "detail": detail(page_ok, f"Your Page {page.get('name')}", "No Facebook Page Resmara can post to"),
         "picture": page.get("picture"),
         "fix": None if page_ok else fix_for("token_dead", "scope_declined_page", "no_page", "several_pages",
                                             "page_taken", "page_unpublished")},
        {"key": "page_admin", "label": "You have full control of that Page", "ok": admin_ok,
         "detail": detail(admin_ok, "Meta says you can post to it", "Not confirmed"),
         "fix": None if admin_ok else fix_for("page_no_control")},
        {"key": "instagram", "label": "Instagram business account linked", "ok": ig_ok,
         "detail": detail(ig_ok, f"@{ig.get('username')}" if ig else "", "No business Instagram on this Page"),
         "picture": ig.get("picture"),
         "fix": None if ig_ok else fix_for("ig_not_linked", "scope_declined_ig")},
        {"key": "ad_account", "label": "Ad account with a payment method", "ok": ad_ok,
         "detail": detail(ad_ok, ad.get("name") or "Ready", (ad.get("name") or "No ad account")),
         "fix": None if ad_ok else fix_for("no_ad_account", "ad_no_payment", "ad_disabled", "ad_unpaid",
                                           "ad_in_review", "scope_declined_ads")},
    ]


# --------------------------------------------------------------------------- what other engines read
def capabilities(db, user_id: int) -> Optional[Dict[str, Any]]:
    conn = connection_for(db, user_id)
    return dict(conn.capabilities or {}) if conn is not None and conn.last_checked_at else None


class PublishTarget:
    """What the publisher posts with: the agent's token, the Page (and its token) and Instagram."""

    def __init__(self, conn: MetaConnection):
        self.id = None
        self.access_token = conn.access_token
        self.page_access_token = conn.page_access_token
        self.page_id = conn.page_id
        self.ig_user_id = conn.ig_user_id
        caps = conn.capabilities or {}
        self.fb_post = bool(caps.get("fb_post"))
        self.ig_post = bool(caps.get("ig_post"))
        self.held = bool(caps.get("held")) or "token_dead" in (conn.issues or [])
        self.connection = conn


def publish_target(db, boost: Boost):
    """The connection to post through, or None to fall back to the legacy ad-account row."""
    if boost is None:
        return None
    conn = connection_for(db, boost.user_id)
    if conn is None or not conn.last_checked_at:
        return None
    return PublishTarget(conn)


def hold_due(db, user: User) -> int:
    """A broken login: due posts are held, not failed, and not lost."""
    now = datetime.utcnow().isoformat()
    rows = (db.query(Post).join(Boost, Post.boost_id == Boost.id)
            .filter(Boost.user_id == user.id, Post.publish_status == "scheduled",
                    Post.client_status == "approved", Post.publish_at.isnot(None), Post.publish_at <= now)
            .all())
    for p in rows:
        p.publish_status = "held"
        p.failure_note = "Held until you reconnect Meta."
    if rows:
        db.add(Event(user_id=user.id, event_type="posts_held", payload={"post_ids": [p.id for p in rows]}))
        db.commit()
    return len(rows)


def release_held(db, user: User) -> Dict[str, Any]:
    """Reconnected: held posts go back in the queue. Ones held over a day are missed, never sent late."""
    cutoff = (datetime.utcnow() - timedelta(hours=HELD_RELEASE_HOURS)).isoformat()
    rows = (db.query(Post).join(Boost, Post.boost_id == Boost.id)
            .filter(Boost.user_id == user.id, Post.publish_status == "held").all())
    released, missed = [], []
    for p in rows:
        if (p.publish_at or "") >= cutoff:
            p.publish_status = "scheduled"
            p.publish_attempts = 0
            p.next_attempt_at = None
            p.failure_note = None
            released.append(p.id)
        else:
            from app.services.post_retry import KIND_CONNECTION
            p.publish_status = "failed"
            p.failure_kind = KIND_CONNECTION
            p.failure_note = "Missed while your Meta connection was off. Post it now or skip it."
            missed.append(p.id)
    # The posts that ran out of tries on the broken connection come back too.
    from app.services import post_retry
    for acct in db.query(AdAccount).filter(AdAccount.user_id == user.id).all():
        post_retry.requeue_connection_failures(db, acct)
    if rows:
        db.add(Event(user_id=user.id, event_type="posts_released",
                     payload={"released": released, "missed": missed}))
        db.commit()
    return {"released": released, "missed": missed}


# --------------------------------------------------------------------------- WATCH
def _live_campaign(db, user_id: int) -> bool:
    return db.query(Boost).filter(Boost.user_id == user_id, Boost.stage == "LIVE").first() is not None


def breakage_emails_due(conn: MetaConnection, live: bool, now: datetime) -> List[str]:
    """After-onboarding breakages: once when it happens, then days 3 and 7 if still open."""
    if not live:
        return []
    due = []
    sent = dict(conn.breakage_emails or {})
    log_rows = {r["key"]: r for r in (conn.issue_log or []) if not r.get("fixed_at")}
    for key in conn.issues or []:
        if not OUTCOMES.get(key, {}).get("email"):
            continue
        found = _aware((log_rows.get(key) or {}).get("found_at"))
        if found is None:
            continue
        times = [_aware(t) for t in sent.get(key, []) if _aware(t) and _aware(t) >= found]
        age = now - found
        if len(times) == 0 or (len(times) == 1 and age >= timedelta(days=3)) or (len(times) == 2 and age >= timedelta(days=7)):
            due.append(key)
    return due


def send_breakage_emails(db, user: User, conn: MetaConnection) -> List[str]:
    from app.services import mail
    now = _now()
    due = breakage_emails_due(conn, _live_campaign(db, user.id), now)
    if not due or user.needs_email:
        return []
    key = due[0]
    o = OUTCOMES[key]
    base = (settings.PUBLIC_BASE_URL or "https://www.resmara.com").rstrip("/")
    body = (f"Hi {(user.name or '').split(' ')[0] or 'there'},\n\n{o['line']}\n\n{o['means']}\n\n"
            f"Fix it here: {base}/#accounts\n\nOr book a free call and we'll fix it with you.\n\n- Resmara")
    ok = mail.send_email(user.email, "Your Resmara campaign needs a quick fix", body)
    sent = dict(conn.breakage_emails or {})
    for k in due:
        sent.setdefault(k, []).append(now.isoformat())
    conn.breakage_emails = sent
    db.add(Event(user_id=user.id, event_type="meta_breakage_email", payload={"keys": due, "sent": bool(ok)}))
    db.commit()
    return due


async def daily_sweep(db) -> Dict[str, Any]:
    """Overnight: full check for every agent with a live campaign, breakage emails, and the 5% alarm."""
    users = (db.query(User).join(Boost, Boost.user_id == User.id)
             .filter(Boost.stage == "LIVE").distinct().all())
    result = {"checked": 0, "dead": 0, "emails": 0, "unreachable": 0, "alert": False}
    for u in users:
        st = await check(db, u, "daily", force=True)
        result["checked"] += 1
        if st.get("checking_unavailable"):
            result["unreachable"] += 1
        if "token_dead" in (st.get("issues") or []):
            result["dead"] += 1
        conn = connection_for(db, u.id)
        if conn is not None and send_breakage_emails(db, u, conn):
            result["emails"] += 1
    recent_alert = (db.query(Event).filter(Event.event_type == "meta_alert",
                                           Event.created_at >= datetime.utcnow() - timedelta(hours=24)).first())
    if result["checked"] and result["dead"] / result["checked"] > 0.05 and recent_alert is None:
        result["alert"] = _alert_owner(db, f"{result['dead']} of {result['checked']} live agents lost their Meta connection",
                                       "More than 5% of agents with live campaigns can't post. That's usually the Meta app, not the agents.")
    stale = (db.query(MetaConnection)
             .filter(MetaConnection.unreachable_since.isnot(None),
                     MetaConnection.unreachable_since <= _now() - timedelta(hours=UNREACHABLE_ALERT_HOURS)).count())
    if stale:
        db.add(Event(event_type="meta_unreachable_6h", payload={"connections": stale}))
        db.commit()
    return result


def _alert_owner(db, subject: str, body: str) -> bool:
    from app.services import mail
    owners = [a.strip() for a in (settings.ADMIN_EMAILS or "").split(",") if a.strip()]
    db.add(Event(event_type="meta_alert", payload={"subject": subject}))
    db.commit()
    if not owners:
        return False
    return bool(mail.send_email(owners[0], subject, body + "\n\n- Resmara"))


def team_counts(db) -> Dict[str, int]:
    """Team room: how many agents are on each outcome key."""
    counts: Dict[str, int] = {}
    for conn in db.query(MetaConnection).all():
        for key in conn.issues or ["ok"]:
            counts[key] = counts.get(key, 0) + 1
    return counts
