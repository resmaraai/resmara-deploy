#!/usr/bin/env python3
"""Another campaign on the same listing — and the pack that is no longer for sale.

A campaign is $49 on its own. A repeat customer does not buy a bundle: they start another
campaign on the same house, which brings the listing along and delivers *new* creative. What is
pinned here:

  * no pack is offered anywhere — not in the config, not on the balance, not in the 402 the
    paywall reads, and there is no endpoint to buy one
  * a balance bought before packs were withdrawn is still honoured, once, and a replayed
    webhook still adds nothing (Stripe retries; money counted twice is how a business lies)
  * "again" copies the house, the facts, the brand and the photos into a fresh campaign that is
    still unpaid — repeating the work never hands out a free campaign
  * that campaign is tagged as round 2 for the listing, and the gallery it will build from is
    rotated, so the second campaign opens on a different photo than the first
  * the plan prompt is told which round it is and which hooks the earlier campaign already used
  * the owner can drop photos from the inherited gallery and pick exactly which ones carry over
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILS = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global FAILS
    if cond:
        print("  ok   %s" % label)
    else:
        FAILS += 1
        print("  FAIL %s %s" % (label, detail))


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="resmara-repeat-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "repeat.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-repeat")
    os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
    os.environ.pop("STRIPE_SECRET_KEY", None)   # start from "billing not configured"

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash
    from app.db.session import (Base, engine, SessionLocal, Asset, Boost, CreditPurchase,
                                Post, User)
    from app.api import billing as billing_api
    from app.services import content_engine

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    def account(email: str) -> tuple[dict, int]:
        with SessionLocal() as db:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, name=email,
                            hashed_password=get_password_hash("repeat-pass-123"),
                            is_active=True, subscription_status="active"))
                db.commit()
            uid = db.query(User).filter(User.email == email).first().id
        r = client.post("/api/auth/login", data={"username": email, "password": "repeat-pass-123"})
        return {"Authorization": "Bearer %s" % r.json().get("access_token", "")}, uid

    agent, agent_id = account("agent@example.com")
    rival, rival_id = account("rival@example.com")

    # Eight photos so the gallery has room to rotate, each with a distinct social score.
    with SessionLocal() as db:
        boost = Boost(user_id=agent_id, address="88 Repeat Ave, Austin TX",
                      property_facts='{"beds": 4}', brand_profile={"agent_name": "Dana"})
        db.add(boost)
        db.commit()
        db.refresh(boost)
        bid = boost.id
        for i in range(8):
            db.add(Asset(user_id=agent_id, boost_id=bid, filename="photo%d.jpg" % i, kind="photo",
                         url="/uploads/photo%d.jpg" % i, room="kitchen" if i % 2 else "living",
                         social_score=90 - i))
        db.commit()

    # ── the pack is not for sale ──────────────────────────────────────────────
    r = client.get("/api/billing/config")
    body = r.json() if r.status_code == 200 else {}
    check("the price config names one campaign", body.get("price_cents") == 4900, str(body))
    check("and offers no pack", "pack" not in body, str(sorted(body)))

    r = client.post("/api/billing/checkout/pack", headers=agent)
    check("there is no endpoint to buy a pack", r.status_code in (404, 405), str(r.status_code))

    # ── a balance bought before packs were withdrawn is still honoured ────────
    outcome = {"event": "checkout.session.completed", "session_id": "cs_pack_1", "paid": True,
               "kind": "pack", "campaigns": 4, "user_id": agent_id, "amount_cents": 19600,
               "payment_intent": "pi_pack_1", "customer": "cus_pack_1"}
    with SessionLocal() as db:
        res = billing_api.settle_pack(outcome, db)
    check("a legacy pack completion is recorded", res.get("status") == "paid", str(res))
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == agent_id).first()
        check("its campaigns land on the balance", user.campaign_credits == 4,
              str(user.campaign_credits))
        purchase = db.query(CreditPurchase).filter(
            CreditPurchase.stripe_session_id == "cs_pack_1").first()
        check("the purchase row is paid with an amount",
              purchase is not None and purchase.amount_cents == 19600 and purchase.paid_at is not None,
              str(purchase and purchase.status))
    with SessionLocal() as db:
        billing_api.settle_pack(outcome, db)      # Stripe retries this
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == agent_id).first()
        check("a replayed webhook does not mint a second pack", user.campaign_credits == 4,
              str(user.campaign_credits))

    with SessionLocal() as db:
        user = db.query(User).filter(User.id == agent_id).first()
        boost = db.query(Boost).filter(Boost.id == bid).first()
        billing_api.require_paid(boost, user, db)
        check("a campaign with a balance builds", boost.paid_at is not None, str(boost.paid_at))
        check("the balance went down by one", user.campaign_credits == 3, str(user.campaign_credits))
        billing_api.require_paid(boost, user, db)
        check("a retried build does not spend a second credit", user.campaign_credits == 3,
              str(user.campaign_credits))

    # ── the paywall sells a campaign and mentions no pack ─────────────────────
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == rival_id).first()
        fresh = Boost(user_id=rival_id, address="9 Unpaid Rd")
        db.add(fresh)
        db.commit()
        db.refresh(fresh)
        raised = None
        try:
            billing_api.require_paid(fresh, user, db)
        except Exception as exc:  # HTTPException
            raised = exc
        check("an unpaid campaign with no balance is refused",
              raised is not None and getattr(raised, "status_code", None) == 402, str(raised))
        detail = (raised.detail if raised is not None else {}) or {}
        check("the refusal offers one campaign at $49", detail.get("price_cents") == 4900, str(detail))
        check("and no pack", "pack" not in detail and "checkout_pack" not in detail,
              str(sorted(detail)))
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == agent_id).first()
        boost = db.query(Boost).filter(Boost.id == bid).first()
        boost.paid_at = None            # pretend this campaign is unpaid again
        db.commit()
        try:
            billing_api.require_paid(boost, user, db)
        except Exception:               # it spends a credit instead
            pass
        check("a credit is spent silently, never a paywall", user.campaign_credits == 2,
              str(user.campaign_credits))

    r = client.get("/api/billing/balance", headers=agent)
    body = r.json() if r.status_code == 200 else {}
    check("the balance is readable", r.status_code == 200 and body.get("campaigns_left") == 2,
          str(r.status_code) + " " + str(body.get("campaigns_left")))
    check("and offers no pack", "pack" not in body and "checkout_pack" not in body,
          str(sorted(body)))
    check("but the legacy purchase stays on the record",
          any(p["campaigns"] == 4 for p in body.get("purchases", [])), str(body.get("purchases")))

    # ── the first campaign's published hooks, so the repeat can avoid them ────
    with SessionLocal() as db:
        db.add(Post(boost_id=bid, day=1, title="Just listed: 4 beds in Austin",
                    overlay_text="JUST LISTED"))
        db.commit()

    # ── "again": another campaign on the same house ───────────────────────────
    r = client.post("/api/boosts/%d/again" % bid, headers=agent)
    check("an agent can start another campaign on the same house", r.status_code == 201,
          str(r.status_code))
    again = r.json() if r.status_code == 201 else {}
    check("it copies the house", again.get("address") == "88 Repeat Ave, Austin TX",
          str(again.get("address")))
    check("it is a new campaign", again.get("id") and again.get("id") != bid, str(again.get("id")))
    with SessionLocal() as db:
        new_id = again.get("id")
        new_boost = db.query(Boost).filter(Boost.id == new_id).first()
        check("the facts survive on the row",
              new_boost is not None and "beds" in str(new_boost.property_facts),
              str(new_boost and new_boost.property_facts))
        check("and the brand comes with it",
              new_boost is not None and (new_boost.brand_profile or {}).get("agent_name") == "Dana",
              str(new_boost and new_boost.brand_profile))
        check("it is tagged as the second campaign on this listing",
              new_boost.repeat_round == 1, str(new_boost.repeat_round))
        copied = db.query(Asset).filter(Asset.boost_id == new_id).count()
        check("the whole gallery comes with it", copied == 8, str(copied))
        check("and it is unpaid, so it costs a checkout like any campaign",
              new_boost.paid_at is None, str(new_boost.paid_at))
        check("no posts were invented", db.query(Post).filter(Post.boost_id == new_id).count() == 0)

    # ── the repeat builds from a different photo than the first campaign ─────
    with SessionLocal() as db:
        first_assets = db.query(Asset).filter(Asset.boost_id == bid).all()
        repeat_assets = db.query(Asset).filter(Asset.boost_id == new_id).all()
        first_order = [a.filename for a in content_engine.galleries_ranked(first_assets)]
        repeat_order = [a.filename for a in content_engine.galleries_ranked(
            repeat_assets, offset=content_engine.gallery_offset(1, len(repeat_assets)))]
        check("the first campaign opens on its strongest photo",
              first_order[0] == "photo0.jpg", str(first_order[:2]))
        check("the repeat campaign opens on a different photo",
              repeat_order[0] != first_order[0], str(repeat_order[:2]))
        check("and every photo is still used exactly once",
              sorted(repeat_order) == sorted(first_order), str(sorted(repeat_order)))
        note = content_engine.repeat_note(db.query(Boost).filter(Boost.id == new_id).first(), db)
        check("the plan is told which round it is", "campaign 2" in note, note)
        check("and which hooks the first campaign already used",
              "Just listed: 4 beds in Austin" in note, note)
        check("a first campaign gets no repeat instruction",
              "campaign 2" not in content_engine.repeat_note(
                  db.query(Boost).filter(Boost.id == bid).first(), db))

        asyncio.run(_check_rotation(db, content_engine, new_id, bid))

    r = client.get("/api/content/gallery/%d" % new_id, headers=agent)
    body = r.json() if r.status_code == 200 else {}
    strip = [p.get("file") or p.get("filename") for p in (body.get("photos") or [])]
    check("the photo strip shows the repeat's order, not the first campaign's",
          strip and strip[0] != "photo0.jpg", str(strip[:2]))

    # ── a third campaign is round 3, not round 2 again ───────────────────────
    r = client.post("/api/boosts/%d/again" % new_id, headers=agent)
    third = r.json() if r.status_code == 201 else {}
    with SessionLocal() as db:
        third_boost = db.query(Boost).filter(Boost.id == third.get("id")).first()
        check("a campaign started from the repeat is the third on the listing",
              third_boost is not None and third_boost.repeat_round == 2,
              str(third_boost and third_boost.repeat_round))

    # ── the owner chooses which photos carry over ────────────────────────────
    with SessionLocal() as db:
        keep = [a.id for a in db.query(Asset).filter(Asset.boost_id == bid).limit(3).all()]
    r = client.post("/api/boosts/%d/again" % bid, headers=agent, json={"photo_ids": keep})
    picked = r.json() if r.status_code == 201 else {}
    with SessionLocal() as db:
        n = db.query(Asset).filter(Asset.boost_id == picked.get("id")).count()
        check("only the chosen photos carry over", n == 3, str(n))

    # ── a photo can be taken out of a campaign's gallery ─────────────────────
    with SessionLocal() as db:
        drop_id = db.query(Asset).filter(Asset.boost_id == new_id).first().id
    r = client.delete("/api/content/assets/%d" % drop_id, headers=agent)
    check("the owner can drop a photo from the campaign", r.status_code == 200, str(r.status_code))
    with SessionLocal() as db:
        check("and it is gone from that campaign",
              db.query(Asset).filter(Asset.boost_id == new_id).count() == 7)
        check("while the listing's other campaign keeps its copy",
              db.query(Asset).filter(Asset.boost_id == bid).count() == 8)
    r = client.delete("/api/content/assets/%d" % drop_id, headers=rival)
    check("nobody can drop someone else's photo", r.status_code == 404, str(r.status_code))

    r = client.post("/api/boosts/%d/again" % bid, headers=rival)
    check("nobody can repeat someone else's campaign", r.status_code == 404, str(r.status_code))

    if FAILS:
        print("FAIL — %d check(s) failed" % FAILS)
        return 1
    print("PASS — no pack is sold, a legacy balance is still honoured, and 'again' runs a\n"
          "       genuinely new campaign on the same listing: rotated photos, fresh copy")
    return 0


async def _check_rotation(db, engine, new_id: int, bid: int) -> None:
    """The repeat's calendar must not open on the same photo as the first campaign."""
    from app.db.session import Asset
    first = db.query(Asset).filter(Asset.boost_id == bid).all()
    repeat = db.query(Asset).filter(Asset.boost_id == new_id).all()
    plan = [{"day": d, "photo": "photo0.jpg"} for d in range(1, 9)]
    a = engine.assign_gallery(plan, first)
    b = engine.assign_gallery(plan, repeat, offset=engine.gallery_offset(1, len(repeat)))
    check("the first campaign's day 1 is the strongest photo",
          a[0]["file"] == "photo0.jpg", str(a[0]))
    check("the repeat's day 1 is a different photo",
          b[0]["file"] != a[0]["file"], str(b[0]))
    check("and its captions are flagged for rewrite, not reused",
          all(item.get("replaced") for item in b), str(b[0]))


if __name__ == "__main__":
    sys.exit(main())
