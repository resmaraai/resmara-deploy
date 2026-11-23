"""Mailchimp, through its API (Engine 9, section 2).

Resmara's own Mailchimp account holds one audience, "Resmara clients", built from *our*
accounts - there are no bought lists. Every client's address is a contact, tagged with what
they are doing (signed up, no campaign yet / has run a campaign / Run it until it sells), and
the series are approved emails Adam wrote, started from those tags.

Two rules this module follows:

* **Unset is not empty.** With no API key the page says "not connected" and names the missing
  environment variables. It never reports a list of zero contacts, because that reads as a
  business fact when it is only a missing credential.
* **Mailchimp is never on the critical path of a sale.** Every call here is wrapped by the
  caller; a Mailchimp outage costs a page its numbers, not the customer their campaign.

Env: ``MAILCHIMP_API_KEY`` (key plus data-centre suffix, e.g. ``abc-us21``) and
``MAILCHIMP_AUDIENCE_ID``.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

log = logging.getLogger("resmara.mailchimp")

TIMEOUT = 20.0
# One page load asks for the audience, the tags and the reports; three calls in a second is
# rude to a free Mailchimp plan, so the answer is reused for a minute.
CACHE_SECONDS = 60
_CACHE: Dict[str, Any] = {"at": 0.0, "key": "", "members": None}

TAGS = {
    "new": "signed up, no campaign yet",
    "campaign": "has run a campaign",
    "until_sold": "Run it until it sells",
}


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def credentials() -> tuple[str, str, str]:
    """(api key, data centre, audience id). Any missing piece comes back empty."""
    key = _env("MAILCHIMP_API_KEY")
    audience = _env("MAILCHIMP_AUDIENCE_ID")
    dc = ""
    if "-" in key:
        dc = key.rsplit("-", 1)[1].strip()
    return key, dc, audience


def configured() -> bool:
    key, dc, audience = credentials()
    return bool(key and dc and audience)


def why_not() -> str:
    key, dc, audience = credentials()
    missing = [name for name, value in (("MAILCHIMP_API_KEY", key),
                                        ("MAILCHIMP_AUDIENCE_ID", audience)) if not value]
    if key and not dc:
        missing.append("MAILCHIMP_API_KEY's data-centre suffix (e.g. -us21)")
    return ("Mailchimp is not connected (needs " + " and ".join(missing) + " on the service)"
            if missing else "")


def _request(path: str, params: Optional[Dict[str, Any]] = None,
             method: str = "GET", json: Optional[Dict[str, Any]] = None
             ) -> tuple[Optional[Any], str]:
    key, dc, audience = credentials()
    if not configured():
        return None, why_not()
    url = f"https://{dc}.api.mailchimp.com/3.0{path}"
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            response = client.request(method, url, params=params or None,
                                      json=json, auth=("resmara", key))
        if response.status_code >= 400:
            detail = ""
            try:
                detail = ((response.json() or {}).get("detail")
                          or (response.json() or {}).get("title") or "")
            except Exception:                                    # noqa: BLE001
                detail = response.text[:160]
            log.info("mailchimp %s -> %s %s", path, response.status_code, str(detail)[:160])
            if response.status_code in (401, 403):
                return None, "Mailchimp refused the API key (check MAILCHIMP_API_KEY)"
            return None, f"Mailchimp answered {response.status_code}: {str(detail)[:160]}"
        if response.status_code == 204 or not response.text:
            return {}, ""
        return response.json(), ""
    except Exception as exc:                                     # noqa: BLE001 - a page, not a crash
        log.info("mailchimp request failed: %s", exc)
        return None, f"Mailchimp could not be reached ({type(exc).__name__})"


def member_hash(email: str) -> str:
    return hashlib.md5((email or "").strip().lower().encode()).hexdigest()


def _member(raw: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "email": (raw.get("email_address") or "").lower(),
        "status": raw.get("status") or "",
        "tags": [t.get("name") for t in (raw.get("tags") or []) if t.get("name")],
        "last_changed": raw.get("last_changed") or raw.get("timestamp_opt"),
    }


def members(force: bool = False) -> tuple[Optional[List[Dict[str, Any]]], str]:
    """Every contact in the audience (paged; small lists are the normal case)."""
    key, dc, audience = credentials()
    cache_key = f"{dc}:{audience}:{key[-6:]}"
    if (not force and _CACHE["members"] is not None and _CACHE["key"] == cache_key
            and time.time() - float(_CACHE["at"] or 0) < CACHE_SECONDS):
        return _CACHE["members"], ""

    out: List[Dict[str, Any]] = []
    offset = 0
    while True:
        data, why = _request(f"/lists/{audience}/members",
                             {"count": 500, "offset": offset,
                              "fields": "members.email_address,members.status,members.tags,"
                                        "members.last_changed,total_items"})
        if data is None:
            return None, why
        rows = data.get("members") or []
        out.extend(_member(row) for row in rows)
        offset += len(rows)
        total = int(data.get("total_items") or 0)
        if not rows or offset >= total:
            break
    _CACHE.update({"at": time.time(), "key": cache_key, "members": out})
    return out, ""


def audience() -> Dict[str, Any]:
    """The list's own numbers: who is on it, how many left, when it last synced."""
    if not configured():
        return {"connected": False, "why": why_not(), "name": None, "contacts": None,
                "unsubscribed": None, "last_sync": None}
    _key, _dc, audience_id = credentials()
    info, why = _request(f"/lists/{audience_id}",
                         {"fields": "name,stats.member_count,stats.unsubscribe_count,"
                                    "stats.last_sub_date"})
    if info is None:
        return {"connected": False, "why": why, "name": None, "contacts": None,
                "unsubscribed": None, "last_sync": None}
    stats = info.get("stats") or {}
    return {
        "connected": True, "why": "",
        "name": info.get("name") or "Resmara clients",
        "contacts": int(stats.get("member_count") or 0),
        "unsubscribed": int(stats.get("unsubscribe_count") or 0),
        "last_sync": stats.get("last_sub_date"),
    }


def tag_counts(rows: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
    """How many contacts carry each tag, plus how many unsubscribed."""
    rows = rows if rows is not None else (members()[0] or [])
    counts: Dict[str, int] = {}
    for row in rows:
        for tag in row.get("tags") or []:
            counts[tag] = counts.get(tag, 0) + 1
    return ([{"name": k, "count": v} for k, v in sorted(counts.items(), key=lambda kv: -kv[1])]
            + [{"name": "unsubscribed", "count": sum(1 for r in rows if r.get("status") == "unsubscribed")}])


def reports(count: int = 50) -> tuple[Optional[List[Dict[str, Any]]], str]:
    """Sent campaigns and their opens/clicks, newest first (Mailchimp's own reports)."""
    data, why = _request("/reports", {"count": count, "sort_field": "send_time",
                                      "sort_dir": "DESC",
                                      "fields": "reports.id,reports.campaign_title,"
                                                "reports.emails_sent,reports.send_time,"
                                                "reports.opens.unique_opens,"
                                                "reports.clicks.unique_clicks,"
                                                "reports.clicks.click_rate"})
    if data is None:
        return None, why
    out = []
    for row in data.get("reports") or []:
        out.append({
            "id": row.get("id"),
            "name": row.get("campaign_title") or "Untitled",
            "sent": int(row.get("emails_sent") or 0),
            "opened": int(((row.get("opens") or {}).get("unique_opens")) or 0),
            "clicked": int(((row.get("clicks") or {}).get("unique_clicks")) or 0),
            "sent_at": row.get("send_time"),
        })
    return out, ""


def clicked_since(email: str, since: datetime) -> bool:
    """Did this address click a campaign email after ``since``? The one call that decides credit.

    Only asked for an address that is about to buy, so the extra round trip is rare. Any error
    answers "no", which falls back to the sign-up stamp - a real observation, not a guess.
    """
    return bool(click_events(email, since))


def click_events(email: str, since: datetime) -> tuple[List[Dict[str, Any]], str]:
    """The marketing emails this address clicked after ``since``, newest first.

    Used twice: to decide a purchase's credit, and to name the series that earned it. An empty
    list is a real answer ("no clicks"); an unreachable Mailchimp comes back with a reason.
    """
    if not configured() or not email:
        return [], why_not()
    _key, _dc, audience = credentials()
    data, why = _request(f"/lists/{audience}/members/{member_hash(email)}/activity",
                         {"count": 50, "activity_filters": "click"})
    if not data:
        return [], why
    out: List[Dict[str, Any]] = []
    for row in data.get("activity") or []:
        if (row.get("type") or "").lower() != "click":
            continue
        stamp = row.get("timestamp") or ""
        try:
            seen = datetime.fromisoformat(str(stamp).replace("Z", "+00:00")).replace(tzinfo=None)
        except Exception:                                        # noqa: BLE001
            continue
        if seen < since.replace(tzinfo=None):
            continue
        out.append({"title": row.get("title") or row.get("campaign_title") or "",
                    "at": stamp})
    out.sort(key=lambda row: row.get("at") or "", reverse=True)
    return out, ""


def sync(db) -> Dict[str, Any]:
    """Put every real client account in the audience, with the tag that describes them.

    Test accounts and closed accounts come off the list. The tags are the whole targeting
    mechanism for the three series, so they are rewritten on every sync rather than merged.
    """
    from app.core.testdata import is_test_email
    from app.db.session import Boost, User

    if not configured():
        return {"synced": False, "why": why_not(), "added": 0, "updated": 0, "removed": 0}

    _key, _dc, audience = credentials()
    have, why = members(force=True)
    if have is None:
        return {"synced": False, "why": why, "added": 0, "updated": 0, "removed": 0}
    known = {row["email"]: row for row in have}

    added = updated = removed = 0
    for user in db.query(User).all():
        email = (user.email or "").strip().lower()
        if not email:
            continue
        test = bool(getattr(user, "is_test", False)) or is_test_email(email)
        if test or not getattr(user, "is_active", True):
            if email in known:
                _request(f"/lists/{audience}/members/{member_hash(email)}", method="DELETE")
                removed += 1
            continue

        paid = (db.query(Boost).filter(Boost.user_id == user.id,
                                       Boost.paid_at.isnot(None)).count())
        until_sold = bool(db.query(Boost).filter(Boost.user_id == user.id,
                                                 Boost.until_sold.is_(True)).count())
        tags = [TAGS["campaign"] if paid else TAGS["new"]]
        if until_sold:
            tags.append(TAGS["until_sold"])

        body = {"email_address": email, "status_if_new": "subscribed",
                "merge_fields": {"FNAME": (user.name or "").split(" ")[0][:60]}}
        if email in known and (known[email].get("status") in ("unsubscribed", "cleaned", "archived")):
            # Never re-subscribe somebody who left: Mailchimp's own unsubscribe has to win.
            body.pop("status_if_new")
            body["status"] = known[email]["status"]
        _request(f"/lists/{audience}/members/{member_hash(email)}", method="PUT", json=body)
        _request(f"/lists/{audience}/members/{member_hash(email)}/tags", method="POST",
                 json={"tags": [{"name": t, "status": "active"} for t in tags]})
        if email in known:
            updated += 1
        else:
            added += 1

    _CACHE["members"] = None
    return {"synced": True, "why": "", "added": added, "updated": updated, "removed": removed}


def csv_text(db) -> str:
    """The backup export: every real client's address, tagged, never a test or closed account.

    Unsubscribes are marked in their own column, so the file can be imported somewhere else
    without mailing somebody who opted out.
    """
    import csv
    import io

    from app.core.testdata import is_test_email
    from app.db.session import Boost, User

    rows = members(force=False)[0]
    unsubscribed = {row["email"] for row in (rows or []) if row.get("status") == "unsubscribed"}

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["email", "name", "signed_up", "came_from", "tag", "marketing_optin",
                     "unsubscribed"])
    for user in db.query(User).order_by(User.id.desc()).all():
        email = (user.email or "").strip().lower()
        if not email or getattr(user, "is_test", False) or is_test_email(email):
            continue
        if not getattr(user, "is_active", True):
            continue
        paid = db.query(Boost).filter(Boost.user_id == user.id, Boost.paid_at.isnot(None)).count()
        tag = TAGS["campaign"] if paid else TAGS["new"]
        created = user.created_at
        when = created.replace(tzinfo=None).date().isoformat() if isinstance(created, datetime) else ""
        writer.writerow([email, user.name or "", when, user.signup_source or "",
                         tag, "yes" if getattr(user, "marketing_optin", True) is not False else "no",
                         "yes" if email in unsubscribed else "no"])
    return buf.getvalue()
