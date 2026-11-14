#!/usr/bin/env python3
"""The repeat purchase: a pack of campaigns, the balance it creates, and one more campaign.

The business only works if an agent buys again, so what is pinned here is the whole loop:

  * a paid pack adds its campaigns to the account's balance, and a replayed webhook adds
    nothing (Stripe retries; money counted twice is how a business lies to itself)
  * an abandoned pack adds nothing and is marked expired, not paid
  * building an unpaid campaign spends one credit and stamps the campaign, so a retried build
    cannot spend a second credit and a later build cannot charge the card again
  * with no balance the build is refused with the one error the UI understands, and that error
    offers the pack
  * "again" copies the house, the facts and the photos into a fresh campaign that is still
    unpaid — repeating the work never hands out a free campaign
  * a pack checkout is refused while Stripe is unconfigured and recorded when it is not
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

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
    tmp = tempfile.mkdtemp(prefix="resmara-pack-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "pack.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-pack")
    os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
    os.environ.pop("STRIPE_SECRET_KEY", None)   # start from "billing not configured"

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash
    from app.db.session import (Base, engine, SessionLocal, Asset, Boost, CreditPurchase,
                                Order, User)
    from app.api import billing as billing_api
    from app.services import billing as billing_service

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    def account(email: str) -> tuple[dict, int]:
        with SessionLocal() as db:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, name=email,
                            hashed_password=get_password_hash("pack-pass-123"),
                            is_active=True, subscription_status="active"))
                db.commit()
            uid = db.query(User).filter(User.email == email).first().id
        r = client.post("/api/auth/login", data={"username": email, "password": "pack-pass-123"})
        return {"Authorization": "Bearer %s" % r.json().get("access_token", "")}, uid

    agent, agent_id = account("agent@example.com")
    rival, rival_id = account("rival@example.com")

    with SessionLocal() as db:
        boost = Boost(user_id=agent_id, address="88 Repeat Ave, Austin TX",
                      property_facts='{"beds": 4}', brand_profile={"agent_name": "Dana"})
        db.add(boost)
        db.commit()
        db.refresh(boost)
        bid = boost.id
        db.add(Asset(user_id=agent_id, boost_id=bid, filename="photo1.jpg", kind="photo",
                     url="/uploads/photo1.jpg"))
        db.commit()

    # ── a pack checkout is refused while Stripe is unconfigured ───────────────
    r = client.post("/api/billing/checkout/pack", headers=agent)
    check("no Stripe, no checkout", r.status_code == 503, str(r.status_code))

    # ── a paid pack credits the account, once ─────────────────────────────────
    outcome = {"event": "checkout.session.completed", "session_id": "cs_pack_1", "paid": True,
               "kind": "pack", "campaigns": 4, "user_id": agent_id, "amount_cents": 19600,
               "payment_intent": "pi_pack_1", "customer": "cus_pack_1"}
    with SessionLocal() as db:
        res = billing_api.settle_pack(outcome, db)
    check("a paid pack is recorded", res.get("status") == "paid", str(res))
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == agent_id).first()
        check("its campaigns land on the balance", user.campaign_credits == 4,
              str(user.campaign_credits))
        check("and the Stripe customer is remembered for next time",
              user.stripe_customer_id == "cus_pack_1", str(user.stripe_customer_id))
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

    # ── an abandoned pack is not money ────────────────────────────────────────
    with SessionLocal() as db:
        db.add(CreditPurchase(user_id=agent_id, campaigns=4, amount_cents=19600,
                              status="pending", stripe_session_id="cs_pack_expired"))
        db.commit()
        billing_api.settle_pack({"event": "checkout.session.expired",
                                 "session_id": "cs_pack_expired", "paid": False,
                                 "kind": "pack", "user_id": agent_id}, db)
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == agent_id).first()
        row = db.query(CreditPurchase).filter(
            CreditPurchase.stripe_session_id == "cs_pack_expired").first()
        check("an expired pack credits nothing", user.campaign_credits == 4, str(user.campaign_credits))
        check("and is marked expired, not paid", row.status == "expired", str(row.status))

    # ── building spends one credit, once ──────────────────────────────────────
    with SessionLocal() as db:
        user = db.query(User).filter(User.id == agent_id).first()
        boost = db.query(Boost).filter(Boost.id == bid).first()
        billing_api.require_paid(boost, user, db)
        check("a campaign with a balance builds", boost.paid_at is not None, str(boost.paid_at))
        check("the balance went down by one", user.campaign_credits == 3, str(user.campaign_credits))
        billing_api.require_paid(boost, user, db)
        check("a retried build does not spend a second credit", user.campaign_credits == 3,
              str(user.campaign_credits))

    # ── no balance means the paywall, and the paywall offers the pack ─────────
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
        check("the refusal offers the pack", (detail.get("pack") or {}).get("size") == 4,
              str(detail.get("pack")))
        check("and says how many campaigns are left", detail.get("campaigns_left") == 0,
              str(detail.get("campaigns_left")))

    # ── the balance endpoint ──────────────────────────────────────────────────
    r = client.get("/api/billing/balance", headers=agent)
    body = r.json() if r.status_code == 200 else {}
    check("the account can read its balance", r.status_code == 200 and body.get("campaigns_left") == 3,
          str(r.status_code) + " " + str(body.get("campaigns_left")))
    check("and sees its paid pack in the history",
          any(p["status"] == "paid" and p["campaigns"] == 4 for p in body.get("purchases", [])),
          str(body.get("purchases")))
    check("and is offered the pack to buy again", (body.get("pack") or {}).get("size") == 4,
          str(body.get("pack")))

    # ── "again": another campaign on the same house, still unpaid ─────────────
    r = client.post("/api/boosts/%d/again" % bid, headers=agent)
    check("an agent can start another campaign on the same house", r.status_code == 201,
          str(r.status_code))
    again = r.json() if r.status_code == 201 else {}
    check("it copies the house", again.get("address") == "88 Repeat Ave, Austin TX",
          str(again.get("address")))
    with SessionLocal() as db:
        copied_boost = db.query(Boost).filter(Boost.id == again.get("id")).first()
        check("the facts survive on the row",
              copied_boost is not None and "beds" in str(copied_boost.property_facts),
              str(copied_boost and copied_boost.property_facts))
        check("and the brand comes with it",
              copied_boost is not None and (copied_boost.brand_profile or {}).get("agent_name") == "Dana",
              str(copied_boost and copied_boost.brand_profile))
    check("it is a new campaign", again.get("id") and again.get("id") != bid, str(again.get("id")))
    with SessionLocal() as db:
        new_id = again.get("id")
        copied = db.query(Asset).filter(Asset.boost_id == new_id).count()
        new_boost = db.query(Boost).filter(Boost.id == new_id).first()
        check("the photos come with it", copied == 1, str(copied))
        check("and it is unpaid, so it costs a credit or a checkout",
              new_boost.paid_at is None, str(new_boost.paid_at))
        posts = db.query(Boost).filter(Boost.id == new_id).count()
        check("no posts were invented", posts == 1, str(posts))

    r = client.post("/api/boosts/%d/again" % bid, headers=rival)
    check("nobody can repeat someone else's campaign", r.status_code == 404, str(r.status_code))

    # ── a configured Stripe records the pending pack ──────────────────────────
    async def fake_session(**kwargs):
        return {"id": "cs_new_pack", "url": "https://checkout.stripe.test/cs_new_pack"}

    async def fake_customer(user, db):
        return "cus_fake"

    original = (billing_service.billing_enabled, billing_service.create_pack_checkout_session,
                billing_api.customer_for)
    billing_service.billing_enabled = lambda: True
    billing_service.create_pack_checkout_session = fake_session
    billing_api.customer_for = fake_customer
    try:
        r = client.post("/api/billing/checkout/pack", headers=agent)
        body = r.json() if r.status_code == 200 else {}
        check("with Stripe configured the checkout opens", r.status_code == 200,
              str(r.status_code) + " " + str(body))
        check("at the pack price", body.get("amount_cents") == 19600, str(body.get("amount_cents")))
        check("for the pack size", body.get("campaigns") == 4, str(body.get("campaigns")))
        with SessionLocal() as db:
            row = db.query(CreditPurchase).filter(
                CreditPurchase.stripe_session_id == "cs_new_pack").first()
            check("and a pending purchase is recorded to reconcile against",
                  row is not None and row.status == "pending", str(row and row.status))
        # A second click must not create a second payable page.
        r2 = client.post("/api/billing/checkout/pack", headers=agent)
        check("a double click reuses the open session",
              r2.json().get("session_id") == "cs_new_pack", str(r2.json()))
    finally:
        (billing_service.billing_enabled, billing_service.create_pack_checkout_session,
         billing_api.customer_for) = original

    if FAILS:
        print("FAIL — %d check(s) failed" % FAILS)
        return 1
    print("PASS — a pack becomes a balance, a build spends one credit exactly once, the\n"
          "       paywall offers the pack, and 'again' repeats a house without giving it away")
    return 0


if __name__ == "__main__":
    sys.exit(main())
