"""Social leads: buyer-interest comments on a campaign's posts and ad (Post Engine §10.4).

The campaign page has shown a Social leads panel since v1.5, but it was a browser mockup: sample
comments for the demo addresses, an empty list for a real campaign, and leads written to
``localStorage``. Nothing read Meta, nothing classified anything, and "Resmara emails you the
moment one comes in" was a promise with no code behind it. This module is the missing half.

What it does, in order, for one campaign:

1. Collect the campaign's published posts (and their ad) and ask the Graph API for the comments
   on each. Instagram and Facebook are both read, and a target Meta refuses is recorded and
   skipped - one dead post never stops the others.
2. Drop every comment Meta already gave us (``platform_comment_id`` is the identity), so a scan
   every 15 minutes cannot insert the same person twice.
3. Judge the new ones for buying interest. With the content engine configured the model answers;
   otherwise a keyword ladder answers, and the row says which one judged it. A comment the model
   did not clearly call is not a lead: a false "someone wants to buy this house" is worse than a
   missed "Beautiful!".
4. Write the leads and send the agent one plain email each, marking ``notified_at`` only when a
   provider accepted the message.

Nothing here invents data. No token, no comments, no mail provider - each is reported as a reason
on the campaign (``leads_scan_note``) and in the scan's JSON, never as an empty success.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import Ad, AdAccount, Boost, Lead, Post, User
from app.services import llm, mail

log = logging.getLogger("resmara.leads")

GRAPH_TIMEOUT = 20.0
MAX_COMMENT_PAGES = 5          # 100 comments a page: 500 is more than a 14-day campaign gets
COMMENT_PAGE_LIMIT = 100
MAX_EMAILS_PER_SCAN = 10       # Resend's free tier is 100/day; a runaway scan must not eat it
CLASSIFY_CHUNK = 20            # comments per engine call
SCAN_WINDOW_DAYS = 21          # a campaign is scanned until its last round has gone quiet

# Fields asked for. IG comments carry a username and a permalink; a Facebook comment carries
# `from{name}` and its own permalink_url. `message` vs `text` is Meta's, not ours.
IG_FIELDS = "id,text,username,timestamp,permalink"
FB_FIELDS = "id,message,from{id,name},created_time,permalink_url"


# ---------------------------------------------------------------------------
# configuration
# ---------------------------------------------------------------------------
def _graph_url(path: str) -> str:
    """Absolute Graph URL. ``graph_base`` already carries the API version (/v19.0)."""
    return settings.graph_base.rstrip("/") + "/" + path.lstrip("/")


def usable_token(ad_account: Any) -> Optional[str]:
    """A real Meta token, or None. A blank or ``sim…``/``demo…`` placeholder is not one."""
    token = (getattr(ad_account, "access_token", None) or "").strip()
    if not token:
        return None
    low = token.lower()
    if low.startswith("sim") or low.startswith("demo"):
        return None
    return token


def _parse_time(value: Any) -> Optional[datetime]:
    """Meta timestamps are ISO-8601 with a +0000 offset, or a bare date."""
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z", "%Y-%m-%d"):
        try:
            parsed = datetime.strptime(text, fmt)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    try:  # e.g. 2026-11-18T09:31:00+0000 with a colon-less offset
        return datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# is this comment a lead?
# ---------------------------------------------------------------------------
# The ladder used when no engine is configured (and as the last resort when the engine answers
# with something unusable). Ordered strongest first; the first match decides, so "Beautiful!"
# never inherits the weight of "Is it still available?".
STRONG = (
    "still available", "is this available", "is it available", "available?", "for sale",
    "asking price", "how much", "price", "what's it going for", "what is it going for",
    "schedule a showing", "book a showing", "private showing", "see the house", "see it",
    "open house", "offer", "under contract", "interested", "pre-approved", "preapproved",
    "cash offer", "virtual tour", "walk through", "walkthrough",
)
WEAK = (
    "dm me", "message me", "call me", "text me", "contact me", "more info", "more details",
    "send info", "send me", "what school", "square feet", "sq ft", "bedroom", "bathroom",
    "garage", "acre", "hoa", "taxes", "inspection", "appraisal", "financing", "mortgage",
    "where is this",
)
# A question mark alone is not interest ("Who took this photo?"), but "…?" plus one of these is.
QUESTION_HINTS = ("availab", "price", "much", "show", "visit", "tour", "offer", "bed", "bath",
                  "garage", "acre", "hoa", "tax", "school", "square", "sqft", "sq ft", "address",
                  "where", "when can")


def keyword_verdict(text: str) -> Tuple[bool, float, str]:
    """Judge one comment by its words. Returns (is_lead, confidence, why)."""
    low = (text or "").lower()
    if not low.strip():
        return False, 0.0, "empty comment"
    # "Not interested, thanks" and "no thanks" are the one place a keyword can be exactly
    # backwards: they contain the word that flags every other comment.
    if any(p in low for p in ("not interested", "no thanks", "no thank you", "already sold",
                              "sold it", "stop messaging", "unsubscribe", "spam")):
        return False, 0.7, "says they are not interested"
    for phrase in STRONG:
        if phrase in low:
            return True, 0.8, f"asks about buying: '{phrase}'"
    has_question = "?" in low
    if has_question and any(hint in low for hint in QUESTION_HINTS):
        return True, 0.6, "asks a question about the home"
    for phrase in WEAK:
        if phrase in low:
            return True, 0.5, f"signals interest: '{phrase}'"
    if len(low.split()) <= 4 and any(w in low for w in ("dm", "info", "details")):
        return True, 0.5, "asks for details"
    return False, 0.2, "no buying interest in the words"


_ENGINE_SYSTEM = (
    "You are the lead screener for a real estate agent's social campaign. You are given comments "
    "left on the agent's posts and ads about ONE home for sale. Decide, for each comment, whether "
    "the person is showing real interest in buying, seeing or asking about that home. A question "
    "about price, availability, showings, offers, the home's features, or a request to be "
    "contacted counts. A compliment ('beautiful!'), a tag of a friend with no question, spam, "
    "emoji-only, or a comment about the video/photo itself does NOT count. Be conservative: if "
    "you are not sure, answer false. Reply with JSON only, exactly this shape: "
    '{"verdicts": [{"i": 0, "lead": true, "confidence": 0.0-1.0, "why": "short reason"}]} '
    "with one entry for every comment index you were given, in order."
)


def _engine_model() -> str:
    return getattr(settings, "OPENAI_MODEL_CHECK", "") or getattr(settings, "OPENAI_MODEL_BRAND", "")


def _valid_verdicts(payload: Any, expected: int) -> Optional[List[Dict[str, Any]]]:
    """Normalise the engine's answer, or None when it is not usable.

    A model that answers with a wrong-length list, or with "lead" spelled four ways, would
    otherwise silently drop or invent leads. Anything unrecognised is a no-answer, and the
    keyword ladder takes over - never a guess.
    """
    if not isinstance(payload, dict):
        return None
    rows = payload.get("verdicts")
    if not isinstance(rows, list) or len(rows) != expected:
        return None
    out: List[Dict[str, Any]] = []
    for pos, row in enumerate(rows):
        if not isinstance(row, dict):
            return None
        lead = row.get("lead")
        if isinstance(lead, str):
            lead = lead.strip().lower() in ("true", "yes", "1")
        if not isinstance(lead, bool):
            return None
        try:
            conf = float(row.get("confidence"))
        except (TypeError, ValueError):
            conf = 0.0
        conf = max(0.0, min(1.0, conf))
        why = str(row.get("why") or "").strip()[:200]
        out.append({"lead": lead, "confidence": conf, "why": why, "by": "ai"})
    return out


async def classify(comments: Sequence[str]) -> List[Dict[str, Any]]:
    """Judge a batch of comments. Engine first, keyword ladder always as the floor."""
    texts = list(comments)
    verdicts: List[Optional[Dict[str, Any]]] = [None] * len(texts)
    if texts and llm.llm_available():
        model = _engine_model()
        for start in range(0, len(texts), CLASSIFY_CHUNK):
            chunk = texts[start:start + CLASSIFY_CHUNK]
            numbered = "\n".join(f"{i}. {t}" for i, t in enumerate(chunk))
            try:
                payload = await llm.chat_json(
                    _ENGINE_SYSTEM,
                    "Comments from this campaign:\n" + numbered,
                    model=model,
                    max_completion_tokens=900,
                    timeout=60.0,
                )
            except Exception as exc:  # noqa: BLE001 - any engine failure means "use the ladder"
                log.warning("leads: engine classification failed (%s); using keywords", exc)
                break
            parsed = _valid_verdicts(payload, len(chunk))
            if parsed is None:
                log.warning("leads: engine answered an unusable shape; using keywords")
                break
            for offset, verdict in enumerate(parsed):
                verdicts[start + offset] = verdict

    out: List[Dict[str, Any]] = []
    for text, verdict in zip(texts, verdicts):
        if verdict is None:
            is_lead, confidence, why = keyword_verdict(text)
            out.append({"lead": is_lead, "confidence": confidence, "why": why, "by": "keyword"})
        else:
            # A "lead" the model is not at least half sure of is not worth an email.
            out.append(verdict)
    return out


# ---------------------------------------------------------------------------
# Graph: comments on this campaign's posts and ad
# ---------------------------------------------------------------------------
def _fb_post_ref(post: Post, page_id: str) -> Optional[str]:
    ref = (post.fb_post_id or "").strip()
    if not ref:
        return None
    # Spec §9: the post id is ref if it contains "_", else "<page>_<ref>".
    return ref if "_" in ref else (f"{page_id}_{ref}" if page_id else ref)


def comment_targets(db: Session, boost: Boost, ad_account: Any) -> List[Dict[str, Any]]:
    """Every place a comment could land for this campaign: published posts, then the ad."""
    page_id = (getattr(ad_account, "page_id", None) or settings.META_PAGE_ID or "").strip()
    targets: List[Dict[str, Any]] = []
    posts = (db.query(Post).filter(Post.boost_id == boost.id,
                                   Post.publish_status == "posted")
             .order_by(Post.day, Post.slot).all())
    for post in posts:
        if post.ig_media_id:
            targets.append({"platform": "instagram", "id": post.ig_media_id, "post_id": post.id,
                            "source": "comment", "channel": "Instagram",
                            "label": post.title or f"Day {post.day}"})
        fb_id = _fb_post_ref(post, page_id)
        if fb_id:
            targets.append({"platform": "facebook", "id": fb_id, "post_id": post.id,
                            "source": "comment", "channel": "Facebook",
                            "label": post.title or f"Day {post.day}"})
    # The ad's own comment thread. Only when the ad has run, and a refusal here is harmless:
    # its comments are frequently the same thread as the boosted post.
    ads = db.query(Ad).filter(Ad.boost_id == boost.id).all()
    for ad in ads:
        if (ad.status or "").lower() in ("live", "submitted", "") and ad.meta_creative_id:
            targets.append({"platform": "facebook", "id": str(ad.meta_creative_id),
                            "post_id": None, "source": "ad_comment", "channel": "Facebook ad",
                            "label": "the ad"})
    return targets


def _normalise(comment: Dict[str, Any], target: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """One Graph comment -> one row-shaped dict. Empty text is not a lead and is dropped."""
    text = (comment.get("text") or comment.get("message") or "").strip()
    if not text:
        return None
    author = comment.get("from") or {}
    name = (comment.get("username") or (author.get("name") if isinstance(author, dict) else "")
            or "Someone")
    return {
        "platform": target["platform"],
        "source": target["source"],
        "channel": target["channel"],
        "post_id": target.get("post_id"),
        "post_label": target.get("label"),
        "platform_comment_id": str(comment.get("id") or "") or None,
        "author_name": str(name)[:120],
        "author_handle": (comment.get("username")
                          or (str(author.get("id")) if isinstance(author, dict) and author.get("id") else None)),
        "text": text[:4000],
        "permalink": comment.get("permalink") or comment.get("permalink_url"),
        "comment_at": _parse_time(comment.get("timestamp") or comment.get("created_time")),
    }


async def _comments_for(client: httpx.AsyncClient, token: str, target: Dict[str, Any]) -> List[Dict[str, Any]]:
    """All comments on one post/ad, paged. Raises on a refused call so the caller can record it."""
    url: Optional[str] = _graph_url(f"/{target['id']}/comments")
    params: Optional[Dict[str, Any]] = {
        "fields": IG_FIELDS if target["platform"] == "instagram" else FB_FIELDS,
        "limit": COMMENT_PAGE_LIMIT,
        "access_token": token,
    }
    found: List[Dict[str, Any]] = []
    pages = 0
    while url and pages < MAX_COMMENT_PAGES:
        resp = await client.get(url, params=params)
        if resp.status_code >= 400:
            detail = ""
            try:
                detail = ((resp.json() or {}).get("error") or {}).get("message") or ""
            except Exception:  # noqa: BLE001 - a non-JSON error body is still an error
                detail = ""
            raise RuntimeError(f"HTTP {resp.status_code}{': ' + detail[:200] if detail else ''}")
        payload = resp.json() or {}
        for comment in payload.get("data") or []:
            row = _normalise(comment, target)
            if row:
                found.append(row)
        pages += 1
        nxt = (payload.get("paging") or {}).get("next")
        if nxt:
            url = nxt          # absolute URL; already carries the token
            params = None
        else:
            url = None
    return found


async def collect_comments(ad_account: Any, targets: Iterable[Dict[str, Any]],
                           client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    """Fetch comments for every target. Returns {comments, errors}; one failure never aborts."""
    token = usable_token(ad_account)
    targets = list(targets)
    if not token:
        return {"comments": [], "errors": ["Meta is not connected (no usable access token)"],
                "targets": len(targets)}
    comments: List[Dict[str, Any]] = []
    errors: List[str] = []
    own_client = client is None
    client = client or httpx.AsyncClient(timeout=GRAPH_TIMEOUT)
    try:
        for target in targets:
            try:
                comments.extend(await _comments_for(client, token, target))
            except Exception as exc:  # noqa: BLE001 - a dead post is not a dead scan
                errors.append(f"{target['platform']} {target['id']}: {exc}")
                log.warning("leads: comments for %s %s failed: %s", target["platform"], target["id"], exc)
    finally:
        if own_client:
            await client.aclose()
    return {"comments": comments, "errors": errors, "targets": len(targets)}


# ---------------------------------------------------------------------------
# the email the agent actually receives
# ---------------------------------------------------------------------------
def lead_email(lead: Lead, boost: Boost, agent_name: str = "there") -> Tuple[str, str]:
    """(subject, body) for one new lead. Plain text: it must read well on a phone."""
    where = lead.channel or ("Instagram" if lead.platform == "instagram" else "Facebook")
    who = lead.author_name or "Someone"
    subject = f"New lead on {boost.address}: {who}"
    lines = [
        f"Hi {agent_name},",
        "",
        f"{who} looks interested in {boost.address}.",
        "",
        f"  \"{lead.text or ''}\"",
        f"  {where}" + (f" · on {lead.post_label}" if lead.post_label else ""),
        "",
        "Reply while they are still looking - Resmara flagged this comment as real interest in "
        "the home.",
    ]
    if lead.permalink:
        lines += ["", f"Open it: {lead.permalink}"]
    lines += ["", "You get these because you have a live campaign in Resmara.", "", "Resmara"]
    return subject, "\n".join(lines)


def _notify(db: Session, lead: Lead, boost: Boost, agent: Optional[User]) -> bool:
    """Send one alert. True only when a provider accepted it; the row keeps the reason."""
    if not agent or not (agent.email or "").strip():
        lead.email_error = "no address on this account"
        return False
    first = (getattr(agent, "name", "") or "").strip().split(" ")[0]
    subject, body = lead_email(lead, boost, first or "there")
    ok = mail.send_email(agent.email, subject, body)
    if ok:
        lead.notified_at = datetime.now(timezone.utc)
        lead.email_error = None
    else:
        lead.email_error = (mail.last_attempt().get("reason") or "send failed")[:300]
    return ok


def _catch_up(db: Session, boost: Boost, agent: Optional[User], budget: int) -> int:
    """Email leads an earlier scan could not send (provider down, held over the cap).

    Without this, a lead found while email was unconfigured was silent forever: it sat in the
    panel and nothing ever tried again. Sends are one at a time and budgeted, so a broken
    provider costs a failed call per lead, not a loop.
    """
    if not agent or budget <= 0:
        return 0
    rows = (db.query(Lead)
            .filter(Lead.boost_id == boost.id, Lead.notified_at.is_(None),
                    Lead.status != "removed")
            .order_by(Lead.id).limit(budget).all())
    sent = 0
    for lead in rows:
        if _notify(db, lead, boost, agent):
            sent += 1
    return sent


# ---------------------------------------------------------------------------
# one campaign, then every campaign
# ---------------------------------------------------------------------------
def add_lead(db: Session, boost: Boost, *, name: str, text: str, where: str = "Instagram",
             notify: bool = False) -> Lead:
    """A lead the agent typed in by hand (the panel's "Add a lead")."""
    where = (where or "Instagram").strip()
    platform = "instagram" if where.lower().startswith("instagram") else (
        "facebook" if where.lower().startswith("facebook") else "manual")
    lead = Lead(
        boost_id=boost.id, user_id=boost.user_id, platform=platform, channel=where,
        source="manual", author_name=(name or "").strip()[:120] or "Someone",
        text=(text or "").strip(), status="new", classified_by="manual", confidence=1.0,
        reason="added by the agent", comment_at=datetime.now(timezone.utc),
    )
    db.add(lead)
    db.flush()
    if notify:
        agent = db.query(User).filter(User.id == boost.user_id).first()
        _notify(db, lead, boost, agent)
    return lead


async def scan_boost(db: Session, boost: Boost, ad_account: Optional[AdAccount] = None,
                     *, send_mail: bool = True,
                     client: Optional[httpx.AsyncClient] = None) -> Dict[str, Any]:
    """Read this campaign's comments, keep the leads, email the agent. Never raises."""
    result: Dict[str, Any] = {"boost_id": boost.id, "address": boost.address, "ok": False,
                              "targets": 0, "comments": 0, "new": 0, "leads": 0,
                              "emailed": 0, "skipped": 0, "errors": []}
    if ad_account is None and boost.ad_account_id:
        ad_account = db.query(AdAccount).filter(AdAccount.id == boost.ad_account_id).first()
    if ad_account is None:
        ad_account = (db.query(AdAccount)
                      .filter(AdAccount.user_id == boost.user_id, AdAccount.platform == "meta",
                              AdAccount.is_active == True)  # noqa: E712 - SQLAlchemy needs it
                      .first())

    if usable_token(ad_account) is None:
        note = "Meta is not connected, so comments cannot be read yet."
        result["errors"].append(note)
        boost.leads_checked_at = datetime.now(timezone.utc)
        boost.leads_scan_note = note
        db.commit()
        return result

    targets = comment_targets(db, boost, ad_account)
    result["targets"] = len(targets)
    if not targets:
        note = "No published posts yet, so there is nothing to read comments from."
        boost.leads_checked_at = datetime.now(timezone.utc)
        boost.leads_scan_note = note
        db.commit()
        result["ok"] = True
        return result

    fetched = await collect_comments(ad_account, targets, client=client)
    result["comments"] = len(fetched["comments"])
    result["errors"].extend(fetched["errors"])

    # Dedupe: anything Meta already gave us, in any status, is not new. Removed leads stay
    # removed - the agent's "not a lead" is not re-litigated every 15 minutes.
    seen = {(row[0], row[1]) for row in db.query(Lead.platform, Lead.platform_comment_id)
            .filter(Lead.boost_id == boost.id).all() if row[1]}
    fresh: List[Dict[str, Any]] = []
    for row in fetched["comments"]:
        key = (row["platform"], row["platform_comment_id"])
        if not row["platform_comment_id"] or key in seen:
            result["skipped"] += 1
            continue
        seen.add(key)
        fresh.append(row)
    result["new"] = len(fresh)

    verdicts = await classify([row["text"] for row in fresh]) if fresh else []
    agent = db.query(User).filter(User.id == boost.user_id).first() if send_mail else None
    # Any lead an earlier scan could not email gets one more try first, inside the same budget.
    mailed = _catch_up(db, boost, agent, MAX_EMAILS_PER_SCAN)
    for row, verdict in zip(fresh, verdicts):
        if not verdict["lead"] or verdict["confidence"] < 0.5:
            result["skipped"] += 1
            continue
        lead = Lead(
            boost_id=boost.id, user_id=boost.user_id, post_id=row["post_id"],
            platform=row["platform"], channel=row["channel"], source=row["source"],
            platform_comment_id=row["platform_comment_id"], author_name=row["author_name"],
            author_handle=row["author_handle"], text=row["text"], permalink=row["permalink"],
            post_label=row["post_label"], comment_at=row["comment_at"], status="new",
            classified_by=verdict["by"], confidence=verdict["confidence"],
            reason=verdict["why"],
        )
        db.add(lead)
        db.flush()
        result["leads"] += 1
        if agent and mailed < MAX_EMAILS_PER_SCAN:
            if _notify(db, lead, boost, agent):
                mailed += 1
        elif agent:
            lead.email_error = "held: more than %d leads this scan" % MAX_EMAILS_PER_SCAN

    result["emailed"] = mailed
    note_bits = [f"{result['new']} new comment(s) read, {result['leads']} lead(s)"]
    if result["errors"]:
        note_bits.append("; ".join(result["errors"])[:400])
    boost.leads_checked_at = datetime.now(timezone.utc)
    boost.leads_scan_note = "; ".join(note_bits)
    db.commit()
    # ok means "every comment thread was read", not "somebody was interested". A refused ad
    # thread leaves ok False with the reason, even when posts yielded leads, so the campaign
    # page can say which part of the reading is incomplete.
    result["ok"] = not result["errors"]
    return result


def scan_boosts(db: Session, *, send_mail: bool = True) -> List[Boost]:
    """Campaigns whose comments are worth reading: launched, running, and recent.

    A finished campaign's posts stay up and can still attract comments, so the window runs
    SCAN_WINDOW_DAYS past launch (or forever while "until it sells" is on). Paused campaigns
    are skipped: the agent asked for quiet, and paying for reads on a paused campaign is not
    what they asked for.
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=SCAN_WINDOW_DAYS)
    # launched_at is the gate, not stage: the launch writes DEPLOYED and only metrics calls it
    # LIVE, so filtering on LIVE would have skipped every campaign that actually exists.
    rows = (db.query(Boost)
            .filter(Boost.launched_at.isnot(None), Boost.paused_at.is_(None))
            .all())
    due: List[Boost] = []
    for boost in rows:
        launched = boost.launched_at
        if launched is not None and launched.tzinfo is None:
            launched = launched.replace(tzinfo=timezone.utc)
        if boost.until_sold or (launched and launched >= cutoff):
            due.append(boost)
    return due


async def scan_all(db: Session, *, send_mail: bool = True) -> Dict[str, Any]:
    """Every due campaign, one result each. Used by the 15-minute scheduler run."""
    boosts = scan_boosts(db, send_mail=send_mail)
    results = []
    for boost in boosts:
        results.append(await scan_boost(db, boost, send_mail=send_mail))
    return {
        "ok": all(r.get("ok") for r in results) if results else True,
        "campaigns": len(results),
        "leads": sum(r.get("leads", 0) for r in results),
        "emailed": sum(r.get("emailed", 0) for r in results),
        "results": results,
    }
