"""The launch gate + Meta campaign creation, shared by every launch entrypoint.

Both POST /api/boosts/{id}/launch and the legacy POST /api/resmara/launch call this, so
there is exactly one place that decides whether a campaign may spend money.

Mirrors the Creatify ad flow the dashboard was reverse-engineered from:
  layer 1 - budget precheck (subscription active + ad-account budget covers the spend)
  layer 2 - copy approval (every post approved, or an explicit auto-approve)
then campaign -> adset -> creative -> ad, all created PAUSED, and the
PENDING -> PENDING_APPROVAL -> APPROVED -> DEPLOYED -> LIVE state machine is advanced.
"""
from datetime import datetime

from sqlalchemy.orm import Session

from app.db.session import Boost, Post, Ad, AdAccount, User, Event
from app.services.credits import (
    check_launch_budget, check_approval, CampaignStage, CampaignAction,
)


def _as_datetime(value):
    """Boost.go_live_date is stored as 'YYYY-MM-DD'; accept either form."""
    if isinstance(value, datetime):
        return value
    if not value:
        return None
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d")
    except ValueError:
        return None


def resolve_ad_account(boost: Boost, current_user: User, db: Session):
    if boost.ad_account_id:
        acct = db.query(AdAccount).filter(AdAccount.id == boost.ad_account_id).first()
        if acct:
            return acct
    return (db.query(AdAccount)
            .filter(AdAccount.user_id == boost.user_id, AdAccount.platform == "meta",
                    AdAccount.is_active == True)
            .first())



def _post_image_bytes(db, post) -> tuple:
    """Bytes of a post's designed image, from disk, the database row or its public URL.

    The ad can only be built from a real picture, so this returns (bytes, filename) or
    (None, None) — never a placeholder.
    """
    import httpx
    from app.services.publisher import local_media_path, public_media_url

    name = (post.image_url or "").rsplit("/", 1)[-1].split("?")[0] or f"post-{post.id}.jpg"
    path = local_media_path(post.image_url) if post.image_url else None
    if path:
        try:
            with open(path, "rb") as fh:
                return fh.read(), name
        except OSError:
            pass
    if post.design_asset_id and db is not None:
        from app.db.session import Asset
        asset = db.query(Asset).filter(Asset.id == post.design_asset_id).first()
        data = getattr(asset, "data", None) if asset else None
        if data:
            return data, name
    url = public_media_url(post.image_url) if post.image_url else None
    if url:
        try:
            resp = httpx.get(url, timeout=30, follow_redirects=True)
            if resp.status_code < 400 and resp.content:
                return resp.content, name
        except Exception:  # noqa: BLE001 - a fetch failure falls through to "no media"
            pass
    return None, None


def _carousel_cards(posts, plan_ad: dict, limit: int = 5) -> list:
    """The strongest approved designed posts, day 1 leading (Ad Engine §4.2).

    The plan names ``creativeDays``; anything it names that has no designed image is
    skipped, and the list is topped up in day order so a carousel never ships short.
    """
    by_day = {}
    for post in posts:
        day = post.day or 0
        if day not in by_day or (post.slot or 1) < (by_day[day].slot or 1):
            by_day[day] = post
    chosen, seen = [], set()

    def take(day):
        post = by_day.get(day)
        if post is not None and post.id not in seen and post.image_url:
            seen.add(post.id)
            chosen.append(post)

    for raw in plan_ad.get("creativeDays") or []:
        try:
            take(int(raw))
        except (TypeError, ValueError):
            continue
    if 1 not in seen:
        take(1)
    for day in sorted(by_day):
        if len(chosen) >= limit:
            break
        take(day)
    return chosen[:limit]

def _merge_custom(configs: dict, custom: dict) -> list:
    """Overlay the operator's hand-edited campaign/adset/adcreative fields from the launch
    UI on top of the built configs. Returns the overridden paths so the caller can report
    exactly what the human changed (nothing is silently dropped)."""
    overridden = []
    for section, values in (custom or {}).items():
        if section not in configs or not isinstance(values, dict):
            continue
        for k, v in values.items():
            if configs[section].get(k) != v:
                configs[section][k] = v
                overridden.append(f"{section}.{k}")
    return overridden


async def launch_boost(boost: Boost, current_user: User, db: Session, *, budget_usd=None,
                       auto_approve: bool = False, action: str = None,
                       custom_configs: dict = None, no_delivery: bool = False) -> dict:
    """Run the gate and, if it passes, create the campaign. Returns a JSON-safe dict.

    ``no_delivery`` builds the whole chain PAUSED (campaign, ad set and ad) and returns a
    Meta-rendered preview instead of treating it as a launch: real objects Meta accepted,
    zero spend, and nothing to un-do. This is the free proof the ad path works.
    """
    from app.services.ad_platforms import get_platform_client, build_boost_configs

    action = action or CampaignAction.LAUNCH_NEW_CAMPAIGN
    ad_account = resolve_ad_account(boost, current_user, db)
    if not ad_account:
        return {"status": "no_ad_account",
                "detail": "No Meta ad account connected yet - connect one first",
                "boost_id": boost.id}

    posts = db.query(Post).filter(Post.boost_id == boost.id).all()
    if not posts:
        return {"status": "nothing_to_launch",
                "detail": "Build and approve the campaign content first",
                "boost_id": boost.id}

    # Layer-0 gate: is the connection itself healthy? In a client-billed setup the ad
    # account is the customer's own and their card pays Meta, so a dead token or an account
    # that cannot spend has to stop the launch HERE. Creating a PAUSED campaign that can
    # never run hides the problem until the customer notices no results.
    from app.services import token_health
    health = await token_health.ensure_ready(ad_account, db)
    if not health["ok"]:
        db.add(Event(user_id=current_user.id, boost_id=boost.id, event_type="error",
                     payload={"where": "launch_preflight", "status": health["status"],
                              "detail": (health.get("detail") or "")[:300]}))
        db.commit()
        return {"status": health["status"], "boost_id": boost.id,
                "ad_account_id": ad_account.id, "needs": health.get("needs", []),
                "detail": health.get("detail") or "the ad account is not ready to launch",
                "preflight": health.get("summary")}

    budget = float(budget_usd or boost.ad_budget_usd or 0.0)
    precheck = check_launch_budget(ad_account, budget)
    copy_approved = all(p.client_status == "approved" for p in posts)
    approval = check_approval(precheck["budget_approved"], copy_approved, auto_approve=auto_approve)

    # Layer-2 gate: the boost has to have been approved as a whole, too.
    stage_now = boost.stage or CampaignStage.PENDING
    if not approval["can_auto_publish"]:
        if CampaignStage.can_transition(stage_now, CampaignStage.PENDING_APPROVAL):
            boost.stage = CampaignStage.PENDING_APPROVAL
            db.commit()
        return {
            "status": "approval_required",
            "boost_id": boost.id,
            "budget_approved": precheck["budget_approved"],
            "copy_approved": copy_approved,
            "can_auto_publish": False,
            "reasons": approval["reasons"],
            "precheck": precheck,
        }

    # --- media first: the ad is only real once it has a picture or a video (Ad Engine §4.2)
    from app.services.publisher import public_media_url
    plan_ad = {}
    if isinstance(boost.plan, dict) and isinstance(boost.plan.get("ad"), dict):
        plan_ad = boost.plan["ad"]
    client = get_platform_client(ad_account)
    video = None
    cards = []
    media_notes = []
    video_url = getattr(boost, "video_url", None)
    if video_url:
        try:
            uploaded = await client.upload_ad_video(public_media_url(video_url) or video_url)
            video_id = uploaded.get("id")
            if video_id and await client.wait_for_video(video_id):
                video = {"video_id": video_id}
                media_notes.append(f"video {video_id} processed by Meta")
            else:
                media_notes.append("Meta could not process the listing video — falling back "
                                   "to the carousel")
        except Exception as exc:  # noqa: BLE001 - fall back, and say so
            media_notes.append(f"video upload failed ({exc}) — falling back to the carousel")
    if not video:
        for post in _carousel_cards(posts, plan_ad):
            if client.simulated:
                # A demo account never calls Meta, so there is nothing to upload and no
                # bytes to read — the tree still has to be complete for the walkthrough.
                cards.append({"image_hash": f"sim_{post.id}", "title": post.title,
                              "post_id": post.id})
                continue
            data, filename = _post_image_bytes(db, post)
            if not data:
                media_notes.append(f"post {post.id} has no image file to upload")
                continue
            try:
                uploaded = await client.upload_ad_image(data, filename)
            except Exception as exc:  # noqa: BLE001
                media_notes.append(f"post {post.id} image upload failed: {exc}")
                continue
            cards.append({"image_hash": uploaded["hash"], "title": post.title,
                          "post_id": post.id})

    from app.services import geocode as geo_service
    configs = build_boost_configs(
        boost,
        plan=boost.plan or {},
        page_id=ad_account.page_id,
        budget_usd=budget,
        cards=cards,
        video=video,
        ig_user_id=getattr(ad_account, "ig_user_id", None),
        destination=getattr(boost, "destination_url", None),
        go_live=boost.go_live_date,
        geo=geo_service.for_boost(boost, db),
        campaign_no=(boost.repeat_round or 0) + 1,
        status="PAUSED" if no_delivery else "ACTIVE",
    )
    configs.setdefault("notes", []).extend(media_notes)
    if configs.get("format") == "none":
        detail = ("the ad has no creative: " + "; ".join(configs.get("notes") or [])
                  if configs.get("notes") else "no designed post image and no usable video")
        db.add(Event(user_id=current_user.id, boost_id=boost.id, event_type="error",
                     payload={"where": "ad_media", "detail": detail[:400]}))
        db.commit()
        return {"status": "no_creative", "boost_id": boost.id, "detail": detail,
                "config_notes": configs.get("notes")}
    overridden = _merge_custom(configs, custom_configs or {})
    if overridden:
        configs.setdefault("notes", []).append("operator overrides: " + ", ".join(overridden))
    try:
        result = await client.create_campaign(configs)
    except Exception as e:
        # The client rolls back a half-created chain and reports what it removed, so a
        # failed launch leaves the customer's ad account exactly as it found it.
        partial = getattr(e, "partial", None) or {}
        db.add(Event(user_id=current_user.id, boost_id=boost.id, event_type="error",
                     payload={"where": "meta_launch", "error": str(e)[:400], "partial": partial}))
        db.commit()
        # Turn Meta's sentence into the action a human has to take, when it is one we know.
        kind = None
        if getattr(e, "graph_error", None):
            kind = (token_health.classify_graph_error(e.graph_error) or {}).get("kind")
        return {"status": "failed", "boost_id": boost.id,
                "needs": [kind] if kind else [],
                "created_ids": partial.get("created", {}),
                "rolled_back": partial.get("deleted", []),
                "detail": f"Meta launch failed: {e}"}

    campaign_id = (result.get("campaign") or {}).get("id")
    adset_id = (result.get("adset") or {}).get("id")
    creative_id = (result.get("creative") or {}).get("id")
    ad_id = (result.get("ad") or {}).get("id")

    if no_delivery:
        # Everything Meta returned is PAUSED, so this build cannot deliver or spend.
        # Hand back the ids plus Meta's own rendering of the ad as the proof.
        preview = {"skipped": True}
        if ad_id and not getattr(client, "simulated", False):
            try:
                preview = await client.get_ad_preview(ad_id)
            except Exception as exc:  # noqa: BLE001 - a missing preview must not hide the build
                preview = {"error": str(exc)[:300]}
        db.add(Event(user_id=current_user.id, boost_id=boost.id,
                     event_type="campaign_built_paused",
                     payload={"campaign_id": campaign_id, "adset_id": adset_id,
                              "creative_id": creative_id, "ad_id": ad_id,
                              "simulated": bool(result.get("simulated"))}))
        db.commit()
        return {
            "status": "built_paused",
            "boost_id": boost.id,
            "no_delivery": True,
            "simulated": bool(result.get("simulated")),
            "meta_campaign_id": campaign_id,
            "meta_adset_id": adset_id,
            "meta_creative_id": creative_id,
            "meta_ad_id": ad_id,
            "preview": preview,
            "all_paused": True,
            "budget_approved": precheck["budget_approved"],
            "copy_approved": copy_approved,
            "config_notes": configs.get("notes", []),
        }


    boost.meta_campaign_id = campaign_id
    boost.stage = CampaignStage.DEPLOYED     # campaign exists and is PAUSED
    boost.main_status = "Launched"
    boost.launched_at = datetime.utcnow()

    ad_row = db.query(Ad).filter(Ad.boost_id == boost.id).first()
    if not ad_row:
        ad_row = Ad(boost_id=boost.id, kind="video" if configs.get("format") == "video" else "photo")
        db.add(ad_row)
    ad_row.meta_ad_id = ad_id
    ad_row.meta_adset_id = adset_id
    ad_row.meta_creative_id = creative_id
    ad_row.meta_campaign_id = campaign_id
    ad_row.format = configs.get("format")
    ad_row.card_post_ids = [c.get("post_id") for c in cards if c.get("post_id")]
    ad_row.image_hashes = [c.get("image_hash") for c in cards if c.get("image_hash")]
    ad_row.video_url = video_url
    ad_row.meta_video_id = (video or {}).get("video_id")
    ad_row.destination_url = (configs.get("adcreative") or {}).get("object_story_spec", {}) \
        .get("link_data", {}).get("link") or (configs.get("adcreative") or {}) \
        .get("object_story_spec", {}).get("video_data", {}).get("call_to_action", {}) \
        .get("value", {}).get("link")
    # Approved by the agent, active in Meta, and simply not delivering before start_time (§4.4).
    ad_row.status = "scheduled"

    db.add(Event(user_id=current_user.id, boost_id=boost.id, event_type="campaign_launched",
                 payload={"action": action, "campaign_id": campaign_id, "adset_id": adset_id,
                          "creative_id": creative_id, "ad_id": ad_id,
                          "simulated": bool(result.get("simulated"))}))
    db.commit()

    return {
        "status": "launched",
        "boost_id": boost.id,
        "stage": boost.stage,
        "simulated": bool(result.get("simulated")),
        "budget_approved": precheck["budget_approved"],
        "copy_approved": copy_approved,
        "can_auto_publish": True,
        "meta_campaign_id": campaign_id,
        "meta_adset_id": adset_id,
        "meta_creative_id": creative_id,
        "meta_ad_id": ad_id,
        "config_notes": configs.get("notes", []),
        "overridden_fields": overridden,
    }
