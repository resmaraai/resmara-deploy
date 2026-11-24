"""Card on file: add a card without buying, then Build charges it with no second page.

Hermetic: Stripe is never called. The two network functions are swapped for stand-ins, so the
endpoints' decisions (charge, refuse, fall back) are pinned without moving money.

Run:  PYTHONPATH=. python tests/test_saved_card.py
"""
import asyncio
import json
import os
import sys

os.environ["STRIPE_SECRET_KEY"] = "sk_test_dummy"
os.environ.pop("STRIPE_WEBHOOK_SECRET", None)

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import SessionLocal, User, Boost, Order  # noqa: E402
from app.core.security import get_password_hash  # noqa: E402
from app.services import billing  # noqa: E402
from app.db.migrate import migrate  # noqa: E402

migrate()

PASSED = 0
FAILED = 0
EMAIL = "card-test@example.com"


def check(label, condition, detail=""):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print("  [PASS] %s" % label)
    else:
        FAILED += 1
        print("  [FAIL] %s  %s" % (label, detail))


def pairs_dict(pairs):
    return {k: v for k, v in pairs}


def main():
    print("\n[payloads]")
    setup = pairs_dict(billing.card_setup_payload("cus_1", 7, "https://resmara.com/"))
    check("add-card page is setup mode (no charge)", setup["mode"] == "setup")
    check("add-card page is tied to the customer", setup["customer"] == "cus_1")
    check("add-card page returns to ?card=saved", setup["success_url"] == "https://resmara.com/?card=saved")
    check("add-card session is marked card_setup", setup["metadata[kind]"] == "card_setup")

    charge = pairs_dict(billing.saved_card_charge_payload("cus_1", "pm_1", 3900, 42, 7, "1 Main St", 1))
    check("charge is off-session and confirmed now",
          charge["off_session"] == "true" and charge["confirm"] == "true")
    check("charge uses the saved card", charge["payment_method"] == "pm_1")
    check("charge carries the campaign's price", charge["amount"] == "3900")
    check("a repeat round is labelled repeat", charge["metadata[price_type]"] == "repeat"
          and charge["metadata[round]"] == "1")
    check("the description names the round", "round 2" in charge["description"])

    print("\n[webhook]")
    outcome = billing.checkout_outcome({"type": "checkout.session.completed", "data": {"object": {
        "id": "cs_setup", "payment_status": "no_payment_required", "mode": "setup",
        "metadata": {"kind": "card_setup", "user_id": "7"}}}})
    check("a saved-card session is recognised", outcome.get("kind") == "card_setup")

    print("\n[endpoints]")
    client = TestClient(app)
    db = SessionLocal()
    try:
        db.query(User).filter(User.email == EMAIL).delete()
        db.commit()
        user = User(email=EMAIL, hashed_password=get_password_hash("Hunter2Hunter2"), name="Card",
                    is_active=True, is_admin=False, stripe_customer_id="cus_test")
        db.add(user)
        db.commit()
        b1 = Boost(user_id=user.id, address="1 Card Way")
        b2 = Boost(user_id=user.id, address="2 Card Way")
        b3 = Boost(user_id=user.id, address="3 Card Way")
        db.add_all([b1, b2, b3])
        db.commit()
        ids = (b1.id, b2.id, b3.id)
    finally:
        db.close()
    tok = client.post("/api/auth/login", data={"username": EMAIL, "password": "Hunter2Hunter2"}).json()["access_token"]
    auth = {"Authorization": "Bearer %s" % tok}

    real_list, real_charge, real_setup = billing.list_cards, billing.charge_saved_card, billing.create_card_setup_session
    calls = []

    async def no_cards(customer_id, client=None):
        return []

    async def one_card(customer_id, client=None):
        return [{"id": "pm_new", "label": "Visa •••• 4242, expires 04/2029"},
                {"id": "pm_old", "label": "Visa •••• 1111, expires 01/2027"}]

    async def charge_ok(**kw):
        calls.append(kw)
        return {"paid": True, "payment_intent": "pi_ok", "message": ""}

    async def charge_declined(**kw):
        calls.append(kw)
        return {"paid": False, "payment_intent": "pi_no", "message": "Your card was declined."}

    async def setup_ok(customer_id, user_id, base_url, client=None, embedded=False):
        return {"id": "cs_setup", "url": "https://checkout.stripe.com/c/pay/cs_setup"}

    try:
        billing.create_card_setup_session = setup_ok
        r = client.post("/api/billing/card", json={}, headers=auth)
        check("Add a card returns Stripe's page", r.status_code == 200 and "checkout.stripe.com" in r.json().get("url", ""), r.text[:200])

        billing.list_cards = no_cards
        r = client.post("/api/billing/charge", json={"boost_id": ids[0]}, headers=auth)
        check("no card on file -> 409 no_card", r.status_code == 409 and r.json()["detail"]["error"] == "no_card", r.text[:200])

        billing.list_cards = one_card
        billing.charge_saved_card = charge_ok
        r = client.post("/api/billing/charge", json={"boost_id": ids[0]}, headers=auth)
        check("card on file -> charged", r.status_code == 200 and r.json()["status"] == "paid", r.text[:200])
        check("the newest card is the one charged", calls and calls[-1]["payment_method_id"] == "pm_new")
        check("the first campaign is $49", calls and calls[-1]["cents"] == 4900)
        db = SessionLocal()
        try:
            boost = db.get(Boost, ids[0])
            order = db.query(Order).filter(Order.boost_id == ids[0]).first()
            check("the campaign is marked paid", bool(boost.paid_at) and boost.paid_amount_cents == 4900)
            check("a paid order with the payment intent is recorded",
                  order is not None and order.status == "paid" and order.stripe_payment_intent == "pi_ok")
        finally:
            db.close()

        n = len(calls)
        r = client.post("/api/billing/charge", json={"boost_id": ids[0]}, headers=auth)
        check("charging a paid campaign again does not charge twice",
              r.status_code == 200 and r.json().get("already") is True and len(calls) == n, r.text[:200])

        b = client.post("/api/boosts/%d/build" % ids[0], json={"force": True}, headers=auth)
        check("a campaign paid by card is no longer refused for payment", b.status_code != 402, b.status_code)

        billing.charge_saved_card = charge_declined
        r = client.post("/api/billing/charge", json={"boost_id": ids[1]}, headers=auth)
        det = r.json().get("detail", {}) if r.status_code == 402 else {}
        check("a decline -> 402 card_declined with a Checkout fallback",
              det.get("error") == "card_declined" and det.get("checkout") == "/api/billing/checkout", r.text[:200])
        db = SessionLocal()
        try:
            check("a decline leaves the campaign unpaid", not db.get(Boost, ids[1]).paid_at)
        finally:
            db.close()

        r = client.post("/api/billing/charge", json={"boost_id": 999999}, headers=auth)
        check("someone else's / unknown campaign -> 404", r.status_code == 404, r.status_code)
    finally:
        billing.list_cards, billing.charge_saved_card, billing.create_card_setup_session = real_list, real_charge, real_setup

    print("\n[cleanup]")
    db = SessionLocal()
    try:
        db.query(Order).filter(Order.boost_id.in_(ids)).delete(synchronize_session=False)
        db.query(Boost).filter(Boost.id.in_(ids)).delete(synchronize_session=False)
        db.query(User).filter(User.email == EMAIL).delete()
        db.commit()
        print("  cleaned test rows")
    finally:
        db.close()
    os.environ.pop("STRIPE_SECRET_KEY", None)

    print("\n" + "=" * 60)
    print("%d passed, %d failed" % (PASSED, FAILED))
    if FAILED:
        print("SAVED CARD TESTS FAILED")
        sys.exit(1)
    print("ALL SAVED CARD TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
