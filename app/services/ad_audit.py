"""Engine 6, sections 3 and 5: the hook versions in the ad set, and the live ad audit.

At launch, next to the main ad (the listing video, or the photo carousel), each hook version Engine 4
built becomes its own ad in the same ad set, tagged so the website knows which one sent a visitor.

Several times a day the audit checks the ad and fixes what it can on its own. It NEVER changes the
budget, the targeting or the dates the agent approved:
  * approved and delivering (impressions rising in ad hours)
  * rejected or limited by Meta: read the reason, fix the text against the rulebook, resubmit once,
    keep the lesson; still rejected -> the team is alerted
  * spending on pace (not stuck at zero, not burning out early): logged, the team hears if stuck
  * the hooks: after ~1,000 impressions each, a hook far behind on clicks is paused and replaced
    with a fresh hook; frequency over ~4 rotates one in. At most one swap a day, never in the last 2
  * the website is up and the ad's link points at it

Everything goes in the audit log (the agent's report shows it); the agent only hears when they need
to do something.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional

from app.db.session import Ad, Asset, Boost, Event, User

log = logging.getLogger(__name__)
FAIR_SHOWING = 1000
WEAK_SHARE = 0.5          # a hook under half the best hook's click rate is weak
MAX_FREQUENCY = 4.0
NO_SWAP_LAST_DAYS = 2
INSIGHT_FIELDS = "impressions,clicks,inline_link_clicks,ctr,frequency,spend,reach"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _aware(value):
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def log_line(db, boost: Boost, line: str, **extra) -> None:
    """One line in the ad audit log ("Day 3: hook 3 had few clicks, replaced with a new hook")."""
    from app.services.campaign_daily import day_of
    day = day_of(boost) or 0
    text = f"Day {day}: {line}" if day > 0 else line[:1].upper() + line[1:]
    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="ad_audit", payload={"line": text, **extra}))
    db.commit()


# ------------------------------------------------------------------ the hook versions at launch
def _image_bytes(db, url: str) -> Optional[bytes]:
    from app.services.listing_site import _asset_bytes
    name = (url or "").rsplit("/", 1)[-1]
    asset = db.query(Asset).filter(Asset.filename == name).first() if name else None
    return _asset_bytes(asset) if asset is not None else None


def hook_creative(hook: Dict[str, Any], image_hash: str, page_id: str, ig_id: str, link: str, n: int) -> dict:
    from app.services.ad_build import with_utm
    story = {"page_id": page_id, "link_data": {
        "image_hash": image_hash, "link": link, "message": hook.get("primaryText") or "",
        "name": hook.get("headline") or "", "description": hook.get("description") or "",
        "call_to_action": {"type": "LEARN_MORE", "value": {"link": link}}}}
    if ig_id:
        story["instagram_user_id"] = ig_id
    return {"name": f"Hook {n}: {(hook.get('hook') or '')[:40]}", "object_story_spec": story}


def _hook_link(base: str, address: str, n: int) -> str:
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
    from app.services.ad_build import with_utm
    url = with_utm(base, address)
    parts = urlsplit(url)
    q = dict(parse_qsl(parts.query))
    q["utm_content"] = f"ad-hook-{n}"
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(q), parts.fragment))


async def add_hook_versions(db, boost: Boost, ad_row: Ad, client, *, page_id: str, ig_id: str = "",
                            hooks: Optional[List[Dict[str, Any]]] = None, start: int = 1) -> List[Dict[str, Any]]:
    """Each hook version becomes its own ad in the campaign's ad set (Engine 6, section 3)."""
    plan_ad = (boost.plan or {}).get("ad") if isinstance(boost.plan, dict) else {}
    hooks = hooks if hooks is not None else [h for h in ((plan_ad or {}).get("hooks") or []) if isinstance(h, dict)]
    versions = [dict(v) for v in (ad_row.versions or [])]
    if not versions and ad_row.meta_ad_id:
        versions.append({"kind": ad_row.format or "main", "meta_ad_id": ad_row.meta_ad_id,
                         "meta_creative_id": ad_row.meta_creative_id, "status": "active",
                         "started_at": _now().isoformat()})
    base = boost.destination_url or ad_row.destination_url or boost.listing_url or ""
    made = []
    for i, hook in enumerate(hooks, start=start):
        img_url = ((hook.get("images") or {}).get("4:5") or "")
        raw = _image_bytes(db, img_url) if img_url else None
        if not raw or not ad_row.meta_adset_id or not base:
            versions.append({"kind": "hook", "n": i, "hook": hook.get("hook"), "status": "skipped",
                             "why": "no graphic" if not raw else "no ad set or link"})
            continue
        try:
            up = await client.upload_ad_image(raw, f"hook-{i}.png")
            image_hash = up.get("hash") or (up.get("images") or {}).get(f"hook-{i}.png", {}).get("hash") or f"sim_hook_{i}"
            got = await client.add_ad(ad_row.meta_adset_id, hook_creative(hook, image_hash, page_id, ig_id,
                                                                          _hook_link(base, boost.address, i), i),
                                      {"name": f"{boost.address[:40]} · hook {i}", "status": "ACTIVE"})
            row = {"kind": "hook", "n": i, "hook": hook.get("hook"), "primaryText": hook.get("primaryText"),
                   "headline": hook.get("headline"), "image": img_url, "image_hash": image_hash,
                   "meta_ad_id": (got.get("ad") or {}).get("id"), "meta_creative_id": (got.get("creative") or {}).get("id"),
                   "status": "active", "started_at": _now().isoformat(), "resubmitted": False}
            versions.append(row)
            made.append(row)
        except Exception as exc:  # noqa: BLE001 - the main ad still runs
            versions.append({"kind": "hook", "n": i, "hook": hook.get("hook"), "status": "failed", "why": str(exc)[:200]})
    ad_row.versions = versions
    db.commit()
    return made


# ------------------------------------------------------------------ the audit
async def _insights(client, ad_id: str) -> Dict[str, float]:
    try:
        data = await client.get_ad_insights(ad_id)
    except Exception:  # noqa: BLE001
        return {}
    row = (data.get("data") or [data])[0] if isinstance(data, dict) else {}
    out = {}
    for k in ("impressions", "clicks", "inline_link_clicks", "ctr", "frequency", "spend", "reach"):
        try:
            out[k] = float(row.get(k) or 0)
        except (TypeError, ValueError):
            out[k] = 0.0
    return out


def click_rate(ins: Dict[str, float]) -> float:
    imp = ins.get("impressions") or 0
    return ((ins.get("inline_link_clicks") or ins.get("clicks") or 0) / imp) if imp else 0.0


def weak_hooks(rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Hooks with a fair showing whose click rate is far below the best hook's."""
    fair = [r for r in rows if r.get("status") == "active" and (r.get("insights") or {}).get("impressions", 0) >= FAIR_SHOWING]
    if len(fair) < 2:
        return []
    best = max(click_rate(r["insights"]) for r in fair)
    return [r for r in fair if best > 0 and click_rate(r["insights"]) < best * WEAK_SHARE]


def can_swap(ad_row: Ad, boost: Boost, now: datetime) -> bool:
    from app.services.renewals import round_ends_on
    end = round_ends_on(boost)
    if end is not None and end - now <= timedelta(days=NO_SWAP_LAST_DAYS):
        return False
    last = _aware((ad_row.audit or {}).get("last_swap_at"))
    return last is None or now - last >= timedelta(days=1)


async def fresh_hook(boost: Boost, avoid: List[str]) -> Optional[Dict[str, Any]]:
    """A new hook for this home from the hook library, true to the house and rulebook-checked."""
    from app.services import ad_hooks
    plan = boost.plan if isinstance(boost.plan, dict) else {}
    diffs = [str(d) for d in ((plan.get("propertyStory") or {}).get("differentiators") or [])]
    got = await ad_hooks.build_hooks(address=boost.address, research=boost.property_facts or "",
                                     differentiators=diffs, photo_index="")
    for h in got.get("hooks") or []:
        if (h.get("hook") or "").strip().lower() not in {a.strip().lower() for a in avoid if a}:
            return h
    return None


def fix_text(row: Dict[str, Any], reason: str) -> Dict[str, Any]:
    """Rejected: the copy is re-fitted to the rulebook (limits, no flagged words) before the one resubmit."""
    from app.services import ad_rulebook
    fixed = ad_rulebook.fit({"primaryText": row.get("primaryText") or "", "headline": row.get("headline") or "",
                             "description": "", "hook": row.get("hook") or ""})
    for key in ("primaryText", "headline", "hook"):
        text = fixed.get(key) or ""
        for issue in ad_rulebook.fair_housing_issues(text):
            text = text.replace(issue, "").strip()
        fixed[key] = " ".join(text.split())
    return fixed


async def audit(db, boost: Boost, *, client=None, now: Optional[datetime] = None,
                new_hook: Optional[Callable] = None, send: bool = True) -> Dict[str, Any]:
    """One look at one campaign's ad. Returns what was checked and what changed."""
    now = now or _now()
    ad_row = db.query(Ad).filter(Ad.boost_id == boost.id).first()
    if ad_row is None or not ad_row.meta_ad_id:
        return {"boost_id": boost.id, "skipped": "no ad"}
    if boost.paused_at is not None:
        return {"boost_id": boost.id, "skipped": "paused"}
    if client is None:
        from app.services.ad_platforms import get_platform_client
        from app.services.launch import resolve_ad_account
        owner = db.query(User).filter(User.id == boost.user_id).first()
        account = resolve_ad_account(boost, owner, db) if owner else None
        if account is None:
            log_line(db, boost, "The ad account couldn't be reached, so the ad wasn't checked.")
            return {"boost_id": boost.id, "skipped": "no ad account"}
        client = get_platform_client(account)
    state = dict(ad_row.audit or {})
    versions = [dict(v) for v in (ad_row.versions or [])]
    if not versions:
        versions = [{"kind": ad_row.format or "main", "meta_ad_id": ad_row.meta_ad_id,
                     "meta_creative_id": ad_row.meta_creative_id, "status": "active"}]
    changed: List[str] = []
    live_from = None
    try:
        live_from = datetime.strptime(str(boost.go_live_date)[:10], "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(hours=14)
    except (TypeError, ValueError):
        pass

    # 1. approved and delivering; rejected by Meta
    for row in versions:
        if row.get("status") not in ("active",) or not row.get("meta_ad_id"):
            continue
        try:
            info = await client.get_object(row["meta_ad_id"], "effective_status,ad_review_feedback")
        except Exception:  # noqa: BLE001
            info = {}
        status = str(info.get("effective_status") or "").upper()
        row["meta_status"] = status
        row["insights"] = await _insights(client, row["meta_ad_id"])
        if status in ("DISAPPROVED", "WITH_ISSUES"):
            reason = "; ".join(str(v) for v in ((info.get("ad_review_feedback") or {}).get("global") or {}).values())[:300] \
                or "Meta didn't say why"
            if row.get("kind") == "hook" and not row.get("resubmitted"):
                fixed = fix_text(row, reason)
                try:
                    creative = hook_creative({**row, **fixed}, row.get("image_hash") or "", _page_id(db, boost), "",
                                             _hook_link(boost.destination_url or "", boost.address, row.get("n") or 0),
                                             row.get("n") or 0)
                    got = await client.add_ad(ad_row.meta_adset_id, creative,
                                              {"name": f"{boost.address[:40]} · hook {row.get('n')} (fixed)", "status": "ACTIVE"})
                    await client.update_object(row["meta_ad_id"], {"status": "PAUSED"})
                    row["status"] = "replaced"
                    versions.append({**row, **fixed, "meta_ad_id": (got.get("ad") or {}).get("id"),
                                     "meta_creative_id": (got.get("creative") or {}).get("id"),
                                     "status": "active", "resubmitted": True, "started_at": now.isoformat(),
                                     "insights": {}})
                    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="rulebook_lesson",
                                 payload={"reason": reason, "before": row.get("primaryText"), "after": fixed.get("primaryText")}))
                    changed.append(f"Meta rejected hook {row.get('n')} ({reason}); fixed the wording and resubmitted it")
                except Exception as exc:  # noqa: BLE001
                    changed.append(f"Meta rejected hook {row.get('n')}; the fix couldn't be resubmitted")
                    _alert_team(boost, f"Meta rejected an ad and the resubmit failed: {reason} ({exc})")
            else:
                row["status"] = "rejected"
                changed.append(f"Meta rejected the {'hook ' + str(row.get('n')) if row.get('kind') == 'hook' else 'main ad'} "
                               f"({reason}); the team is looking at it")
                _alert_team(boost, f"Meta rejected an ad for {boost.address} again: {reason}")

    active = [r for r in versions if r.get("status") == "active"]
    total_imp = sum((r.get("insights") or {}).get("impressions", 0) for r in active)

    # 2. delivering, on pace
    last_imp = float(state.get("impressions") or 0)
    if live_from and now > live_from + timedelta(hours=24):
        if total_imp == 0 and last_imp == 0:
            if not state.get("stuck_alerted"):
                _alert_team(boost, f"The ad for {boost.address} has no impressions since going live.")
                state["stuck_alerted"] = now.isoformat()
                changed.append("The ad wasn't being shown yet; the team is checking it")
    spend = sum((r.get("insights") or {}).get("spend", 0) for r in active)
    budget = float(boost.ad_budget_usd or 0)
    if live_from and budget and now > live_from:
        elapsed = min(1.0, (now - live_from).total_seconds() / (int(boost.campaign_days or 14) * 86400))
        state["pace"] = round(spend / (budget * elapsed), 2) if elapsed > 0 else None
        if state["pace"] and state["pace"] > 1.6 and not state.get("pace_noted"):
            state["pace_noted"] = now.isoformat()
            changed.append("Spending faster than an even pace; Meta keeps it within your lifetime budget")
    state["impressions"] = total_imp

    # 3. weak hooks and frequency: at most one swap a day, never in the last 2 days
    hooks = [r for r in active if r.get("kind") == "hook"]
    weak = weak_hooks(hooks)
    freq = max([(r.get("insights") or {}).get("frequency", 0) for r in active] or [0])
    reason = None
    target = None
    if weak:
        target = min(weak, key=lambda r: click_rate(r["insights"]))
        reason = f"hook {target.get('n')} had few clicks"
    elif freq > MAX_FREQUENCY and hooks:
        target = max(hooks, key=lambda r: (r.get("insights") or {}).get("frequency", 0))
        reason = f"people were seeing hook {target.get('n')} too often"
    if target is not None and can_swap(ad_row, boost, now):
        avoid = [r.get("hook") or "" for r in versions]
        hook = await (new_hook or fresh_hook)(boost, avoid)
        if hook:
            try:
                await client.update_object(target["meta_ad_id"], {"status": "PAUSED"})
                target["status"] = "swapped_out"
                ad_row.versions = versions
                db.commit()
                n = max([r.get("n") or 0 for r in versions]) + 1
                made = await add_hook_versions(db, boost, ad_row, client, page_id=_page_id(db, boost),
                                               hooks=[hook], start=n)
                versions = [dict(v) for v in (ad_row.versions or [])]
                state["last_swap_at"] = now.isoformat()
                changed.append(f"{reason}, replaced with a new hook"
                               + ("" if made else " (the new hook's graphic is still being made)"))
            except Exception as exc:  # noqa: BLE001
                changed.append(f"{reason}; the swap didn't go through")
                log.info("hook swap failed for %s: %s", boost.id, exc)

    # 4. the website is up and the ad links there
    try:
        from app.services import listing_site
        site = listing_site.site_for(db, boost, adopt=False)
        if site is not None:
            out = listing_site.render(site, boost, status=listing_site.state(boost, site))
            if "<title>" not in out:
                changed.append("The listing website didn't load; the team is fixing it")
                _alert_team(boost, f"The listing website for {boost.address} didn't render.")
            elif ad_row.destination_url and listing_site.HOST not in (ad_row.destination_url or "") and \
                    listing_site.HOST in (boost.destination_url or ""):
                state["link_note"] = "the ad was launched before the website existed"
    except Exception:  # noqa: BLE001
        pass

    ad_row.versions = versions
    state["checked_at"] = now.isoformat()
    ad_row.audit = state
    db.commit()
    for line in changed:
        log_line(db, boost, line)
    return {"boost_id": boost.id, "changed": changed, "active": len([r for r in versions if r.get("status") == "active"]),
            "impressions": total_imp}


def _page_id(db, boost: Boost) -> str:
    try:
        from app.services import meta_engine
        target = meta_engine.publish_target(db, boost)
        return (target.page_id if target else "") or ""
    except Exception:  # noqa: BLE001
        return ""


def _alert_team(boost: Boost, message: str) -> None:
    try:
        from app.services import listing_site, mail
        to = listing_site.team_email()
        if to:
            mail.send_email(to, f"Ad audit: {boost.address}", message + f"\n\nCampaign {boost.id}.")
    except Exception:  # noqa: BLE001
        pass


async def sweep(db, **kw) -> Dict[str, Any]:
    from app.services.campaign_state import is_over
    out = []
    for boost in db.query(Boost).filter(Boost.launched_at.isnot(None), Boost.paused_at.is_(None)).all():
        if is_over(boost):
            continue
        try:
            out.append(await audit(db, boost, **kw))
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            out.append({"boost_id": boost.id, "error": str(exc)[:200]})
    return {"checked": len(out), "changed": sum(len(r.get("changed") or []) for r in out), "details": out}
