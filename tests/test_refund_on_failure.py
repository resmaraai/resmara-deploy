"""A build that fails after payment gives the money back (owner item 16).

The order the owner asked for is "refund or retry automatically". Both routes are tested here:
a prepaid campaign returns its credit to the balance, and a card payment with a payment intent
is refunded at Stripe — with the campaign left unpaid so the retry costs nothing. A payment we
cannot refund is recorded as pending for the operator instead of being reported as refunded.
"""
import os
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_DIR = tempfile.mkdtemp(prefix="refund-")
os.environ["RESMARA_DB"] = os.path.join(DB_DIR, "app.db")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(DB_DIR, 'app.db')}"
os.environ["RESMARA_UPLOAD_DIR"] = os.path.join(DB_DIR, "uploads")

from app.db.session import Event, Order, SessionLocal, User  # noqa: E402
from app.services import billing  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


from app.main import app  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

with TestClient(app) as client:
    client.post("/api/auth/register", json={"terms_accepted": True, "email": "pay@example.com", "password": "long enough",
                                            "name": "Payer"})
    db = SessionLocal()
    user = db.query(User).filter(User.email == "pay@example.com").first()
    token = client.post("/api/auth/login",
                        data={"username": "pay@example.com", "password": "long enough"}
                        ).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    user.meta_connected_at = datetime.now(timezone.utc)
    user.campaign_credits = 1
    db.commit()

    from app.db.session import Boost
    made = client.post("/api/boosts", headers=h, json={"address": "9 Refund Way, Austin TX",
                                                       "campaign_days": 14})
    boost_id = made.json()["id"]

    print("=== a prepaid campaign returns its credit ===")
    # Building spends the credit (require_paid -> consume_credit), then the build "fails".
    db = SessionLocal()
    boost = db.query(Boost).filter(Boost.id == boost_id).first()
    owner = db.query(User).filter(User.id == boost.user_id).first()
    owner.campaign_credits = 1
    db.commit()
    from app.api.billing import require_paid
    require_paid(boost, owner, db)
    db.refresh(owner)
    check("the build spent the credit", int(owner.campaign_credits) == 0, str(owner.campaign_credits))

    import asyncio

    outcome = asyncio.run(billing.refund_failed_build(boost, db))
    db.refresh(owner)
    check("the credit is back", int(owner.campaign_credits) == 1, str(owner.campaign_credits))
    check("  ...and it is reported as returned",
          outcome.get("refunded") is True and outcome.get("kind") == "credit", str(outcome))
    check("  ...and a retry is free because the campaign is unpaid again",
          boost.paid_at is None, str(boost.paid_at))
    ev = (db.query(Event).filter(Event.boost_id == boost.id,
                                 Event.event_type == "credit_returned").first())
    check("  ...and the reason is on the record", ev is not None)

    print("\n=== a card payment is refunded at Stripe ===")
    boost.paid_at = datetime.now(timezone.utc)
    boost.paid_amount_cents = 4900
    order = Order(user_id=owner.id, boost_id=boost.id, amount_cents=4900, status="paid",
                  stripe_session_id="cs_test_123", stripe_payment_intent="pi_test_123")
    db.add(order)
    db.commit()

    calls = {}

    class FakeResponse:
        status_code = 200
        content = b"{}"

        def json(self):
            return {"id": "re_test_1"}

    class FakeClient:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *a):
            return False

        async def post(self, url, **kwargs):
            calls.update({"url": url, **{k: v for k, v in kwargs.items()}})
            return FakeResponse()

    original_client = billing.httpx.AsyncClient
    original_key = billing.secret_key
    original_enabled = billing.billing_enabled
    billing.httpx.AsyncClient = FakeClient
    billing.secret_key = lambda: "sk_test_fake"
    billing.billing_enabled = lambda: True
    try:
        outcome = asyncio.run(billing.refund_failed_build(boost, db))
    finally:
        billing.httpx.AsyncClient = original_client
        billing.secret_key = original_key
        billing.billing_enabled = original_enabled

    check("Stripe was asked for a refund of the payment intent",
          calls.get("url", "").endswith("/v1/refunds")
          and (calls.get("data") or {}).get("payment_intent") == "pi_test_123", str(calls)[:200])
    check("  ...with an idempotency key so a retry cannot refund twice",
          (calls.get("headers") or {}).get("Idempotency-Key", "").startswith("refund-boost-"),
          str(calls.get("headers")))
    check("  ...and the refund is reported", outcome.get("refunded") is True
          and outcome.get("kind") == "card", str(outcome))
    db.refresh(order)
    check("  ...the order now says refunded", order.status == "refunded", order.status)

    print("\n=== a payment we cannot refund is not reported as refunded ===")
    boost2 = Boost(user_id=owner.id, address="10 Pending St, Austin TX", campaign_days=14,
                   paid_at=datetime.now(timezone.utc), paid_amount_cents=4900)
    db.add(boost2)
    db.commit()
    outcome = asyncio.run(billing.refund_failed_build(boost2, db))
    check("no payment intent means pending, not refunded",
          outcome.get("refunded") is False and outcome.get("pending") is True, str(outcome))
    ev = (db.query(Event).filter(Event.boost_id == boost2.id,
                                 Event.event_type == "refund_pending").first())
    check("  ...and the operator can see it in the log", ev is not None)
    db.close()

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL REFUND TESTS PASSED")
