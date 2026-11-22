"""Lead totals per campaign, by where the lead came from.

Counts every lead Resmara ever flagged on a campaign, including ones the agent later removed
as "not a lead" or ticked off: the list is the agent's to tidy, but how many leads a campaign
generated is a record (the card, the campaign page and the Team room all read it), and
removing a row from the list must not make that number go down.

Buckets:
  ad       comments on the ad (source ad_comment, or a manual lead marked as from the ad)
  posts    comments on the 14 posts
  website  the listing page: form fills and Call taps (source form / call)
"""
from __future__ import annotations

from typing import Dict, Iterable

from sqlalchemy.orm import Session

from app.db.session import Lead

BUCKETS = ("ad", "posts", "website")


def bucket_of(source: str | None, channel: str | None) -> str:
    src = (source or "").lower()
    ch = (channel or "").lower()
    if src in ("form", "call", "web") or "listing page" in ch or "website" in ch:
        return "website"
    if src == "ad_comment" or ch.endswith(" ad") or " ad " in ch:
        return "ad"
    return "posts"


def empty() -> Dict[str, int]:
    return {"ad": 0, "posts": 0, "website": 0, "total": 0, "removed": 0}


def lead_totals(db: Session, boost_ids: Iterable[int]) -> Dict[int, Dict[str, int]]:
    ids = [int(b) for b in boost_ids if b is not None]
    out: Dict[int, Dict[str, int]] = {b: empty() for b in ids}
    if not ids:
        return out
    rows = (db.query(Lead.boost_id, Lead.source, Lead.channel, Lead.status)
            .filter(Lead.boost_id.in_(ids)).all())
    for boost_id, source, channel, status in rows:
        t = out.setdefault(boost_id, empty())
        t[bucket_of(source, channel)] += 1
        t["total"] += 1
        if status == "removed":
            t["removed"] += 1
    return out
