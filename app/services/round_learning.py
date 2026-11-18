"""What the last campaign on this listing taught us, for the next one to use.

A repeat round ($39 "run it again", or the every-2-weeks "run it until it sells") used to be told
only what NOT to repeat (the earlier titles and hooks) and to open on a different photo. It never
looked at how those posts did. This module reads the previous round's real Meta numbers and turns
them into two things the next build uses:

  * a ranked list of the previous round's posts, best first (photo, room, format, words, numbers);
  * a plain-English note for the plan prompt: lead with the photos and formats that earned
    attention, keep the styles that worked, rewrite the words, drop what was ignored, and follow
    up on the posts people asked about.

Rules it keeps:
  * It never invents a number. No Meta connection, no posted posts or no measurable result means
    no learning note, and the build behaves exactly as before (new angles, rotated opening).
  * A snapshot of what it used is saved as an Event on the new campaign, so the decision can be
    shown and checked later even if Meta is disconnected by then.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

log = logging.getLogger("resmara.round_learning")

# What one interaction is worth when ranking posts. Comments and shares are people raising a hand
# or passing the house on, which is what sells a listing; a like is the cheapest signal.
WEIGHTS = {"comments": 4.0, "shares": 4.0, "saved": 3.0, "likes": 1.0, "reactions": 1.0}
TOP_N = 3


def _n(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def score(row: Dict[str, Any]) -> float:
    """One number per post. Interactions first; video views and reach only break ties."""
    s = sum(_n(row.get(k)) * w for k, w in WEIGHTS.items())
    s += _n(row.get("views")) / 100.0
    s += _n(row.get("reach")) / 1000.0
    return round(s, 3)


def previous_boost(boost, db):
    """The campaign this round follows: its parent, else the latest earlier one on the house."""
    from app.db.session import Boost  # noqa: PLC0415 - keep module import light
    parent_id = getattr(boost, "parent_boost_id", None)
    if parent_id:
        prev = db.query(Boost).filter(Boost.id == parent_id).first()
        if prev is not None:
            return prev
    return (db.query(Boost)
            .filter(Boost.user_id == getattr(boost, "user_id", None),
                    Boost.address == getattr(boost, "address", None),
                    Boost.id != getattr(boost, "id", None))
            .order_by(Boost.id.desc()).first())


def rank_posts(rows: List[Dict[str, Any]], posts_by_id: Dict[int, Any]) -> List[Dict[str, Any]]:
    """Join Meta's numbers to our posts and sort best first. Pure, so it is testable."""
    merged: Dict[int, Dict[str, Any]] = {}
    for row in rows or []:
        db_id = row.get("db_id")
        post = posts_by_id.get(db_id)
        if post is None:
            continue
        cur = merged.setdefault(db_id, {
            "post_id": db_id, "day": getattr(post, "day", None),
            "kind": getattr(post, "kind", None) or getattr(post, "post_type", None),
            "photo_file": getattr(post, "photo_file", None),
            "photo_room": getattr(post, "photo_room", None),
            "title": getattr(post, "title", None),
            "overlay": getattr(post, "overlay_text", None),
            "reach": 0, "likes": 0, "comments": 0, "shares": 0, "saved": 0, "views": 0,
            "reactions": 0, "platforms": [],
        })
        # A post that went to Facebook and Instagram is one post: add the two platforms up.
        for k in ("reach", "likes", "comments", "shares", "saved", "views", "reactions"):
            cur[k] += int(_n(row.get(k)))
        if row.get("platform"):
            cur["platforms"].append(row["platform"])
    ranked = list(merged.values())
    for r in ranked:
        r["score"] = score(r)
    ranked.sort(key=lambda r: (-r["score"], r.get("day") or 0))
    return ranked


def interactions(r: Dict[str, Any]) -> int:
    return int(r.get("likes", 0) + r.get("reactions", 0) + r.get("comments", 0)
               + r.get("shares", 0) + r.get("saved", 0))


def _describe(r: Dict[str, Any]) -> str:
    bits = []
    for k, label in (("comments", "comments"), ("shares", "shares"), ("saved", "saves"),
                     ("likes", "likes"), ("reactions", "reactions"), ("views", "video views"),
                     ("reach", "reach")):
        if r.get(k):
            bits.append("%d %s" % (r[k], label))
    what = "day %s %s" % (r.get("day"), "video" if "video" in str(r.get("kind") or "") else "photo post")
    if r.get("photo_room"):
        what += " of the %s" % r["photo_room"]
    if r.get("photo_file"):
        what += " (file %s)" % r["photo_file"]
    if r.get("title"):
        what += ', titled "%s"' % r["title"]
    return "%s: %s" % (what, ", ".join(bits) or "no interactions")


def learning_note(ranked: List[Dict[str, Any]], ad: Optional[Dict[str, Any]] = None) -> str:
    """The plan prompt's paragraph about the last round. '' when there is nothing real to learn."""
    if not ranked or not any(interactions(r) or r.get("views") for r in ranked):
        return ""
    top = [r for r in ranked if r["score"] > 0][:TOP_N]
    if not top:
        return ""
    bottom = [r for r in ranked if r not in top and not interactions(r) and not r.get("views")][:3]
    asked = [r for r in ranked if r.get("comments")]
    videos = [r for r in ranked if "video" in str(r.get("kind") or "")]
    photos = [r for r in ranked if r not in videos]

    lines = ["WHAT WORKED LAST ROUND (real Meta numbers from the previous campaign on this listing; "
             "use them to make this round perform better):"]
    for i, r in enumerate(top, 1):
        lines.append("  %d. %s" % (i, _describe(r)))
    files = [r["photo_file"] for r in top if r.get("photo_file")]
    if files:
        lines.append("- Lead with what worked: use these photos again on day 1 and in the strongest "
                     "slots, and name their days in the ad's creativeDays: " + ", ".join(files) +
                     ". Same photo is fine; the words must be new.")
    rooms = []
    for r in top:
        if r.get("photo_room") and r["photo_room"] not in rooms:
            rooms.append(r["photo_room"])
    if rooms:
        lines.append("- Give more of the calendar to the rooms people engaged with: " +
                     ", ".join(rooms) + ".")
    if videos and photos:
        v = sum(r["score"] for r in videos) / len(videos)
        p = sum(r["score"] for r in photos) / len(photos)
        if v > p * 1.25:
            lines.append("- Video out-performed photo posts last round: keep every video slot "
                         "and lean on motion where the library allows.")
        elif p > v * 1.25:
            lines.append("- Photo posts out-performed video last round: favour strong single "
                         "photos over video where there is a choice.")
    if top and any(r.get("overlay") for r in top):
        lines.append("- Keep the on-photo style (length and tone) of the top posts, with new wording.")
    if asked:
        lines.append("- People commented on: " + "; ".join(
            '"%s"' % (r.get("title") or "day %s" % r.get("day")) for r in asked[:3]) +
            ". Follow those topics up with a clear invitation to message or book a showing.")
    if bottom:
        lines.append("- These got no interaction; do not repeat their angle or lead with their "
                     "photos: " + "; ".join(
                         '"%s"' % (r.get("title") or "day %s" % r.get("day")) for r in bottom) + ".")
    if ad and ad.get("source") == "meta" and ad.get("clicks") is not None:
        ctr = ad.get("ctr")
        lines.append("- Last round's ad: %s clicks%s. %s" % (
            int(_n(ad.get("clicks"))),
            (" at %.2f%% click-through" % _n(ctr)) if ctr is not None else "",
            "Build this round's ad around the top photos above."))
    return "\n".join(lines)


async def previous_round_results(boost, db) -> Dict[str, Any]:
    """Fetch, rank and explain the previous round. Never raises: a failure means 'no learning'."""
    out: Dict[str, Any] = {"ok": False, "ranked": [], "note": "", "reason": ""}
    try:
        if int(getattr(boost, "repeat_round", 0) or 0) <= 0 or db is None:
            out["reason"] = "first campaign on this listing"
            return out
        prev = previous_boost(boost, db)
        if prev is None:
            out["reason"] = "no earlier campaign found"
            return out
        out["previous_boost_id"] = prev.id
        from app.db.session import Post  # noqa: PLC0415
        from app.services import insights  # noqa: PLC0415
        posts = db.query(Post).filter(Post.boost_id == prev.id).all()
        organic = await insights.organic_results(db, prev, None, "0000", "9999")
        if organic.get("source") != "meta":
            out["reason"] = organic.get("reason") or "Meta numbers unavailable"
            return out
        ranked = rank_posts(organic.get("posts") or [], {p.id: p for p in posts})
        ad = None
        try:
            from datetime import datetime, timedelta  # noqa: PLC0415
            start = getattr(prev, "created_at", None) or (datetime.utcnow() - timedelta(days=90))
            ad = await insights.ad_numbers(db, prev, start.strftime("%Y-%m-%d"),
                                           datetime.utcnow().strftime("%Y-%m-%d"))
        except Exception:  # noqa: BLE001 - the ad numbers are a bonus, never a blocker
            ad = None
        note = learning_note(ranked, ad)
        out.update({"ok": bool(note), "ranked": ranked, "note": note,
                    "reason": "" if note else "no post earned any interaction last round"})
        return out
    except Exception as exc:  # noqa: BLE001 - learning is guidance, never a build blocker
        log.warning("round learning skipped: %s", exc)
        out["reason"] = "could not read last round's numbers (%s)" % type(exc).__name__
        return out
