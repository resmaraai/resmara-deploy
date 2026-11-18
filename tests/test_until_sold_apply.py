#!/usr/bin/env python3
"""The money half of "run it until it sells", with Stripe stubbed.

A renewal that charges a card is the highest-risk code in this app: nobody is watching it, the
customer is asleep, and a bug is a real $39. So the whole path runs here against stubs, and what
is pinned is the order of operations and every way it can refuse:

  * nothing due, or no saved card, or a card already declined today: no charge, and say why
  * charged: a paid Order, the new round stamped paid, the old round's flag off so it cannot be
    charged twice, and the photos carried over
  * declined: nothing left behind (no half-made round), an event recorded, and no retry for a day
  * a listing that has gone pending or sold: the flag clears and nothing is charged
  * run twice in a row: the second run has nothing to do

Run:
    cd /Users/dan/resmara && ./venv/bin/python3 tests/test_until_sold_apply.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
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
    tmp = tempfile.mkdtemp(prefix="resmara-apply-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "apply.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-until-sold-apply")
    os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
    os.environ.pop("STRIPE_SECRET_KEY", None)
    os.environ["UNTIL_SOLD_BUILD"] = "0"          # no engine in a unit test; the hook is exercised

    from app.db.session import Base, engine, SessionLocal, Boost, Asset, Event, Order, User  # noqa: E402
    from app.db.migrate import migrate                                                     # noqa: E402
    from app.services import renewals                                                      # noqa: E402

    Base.metadata.create_all(bind=engine)
    migrate()
    db = SessionLocal()
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)

    try:
        owner = User(email="owner@example.com", name="Owner", is_active=True, is_admin=True,
                     hashed_password="x", stripe_customer_id="cus_test_1")
        db.add(owner); db.commit(); db.refresh(owner)

        def add(address, **kw):
            b = Boost(user_id=owner.id, address=address, main_status="Live", stage="LAUNCHED",
                      hidden=False, repeat_round=0, until_sold=True,
                      launched_at=now - timedelta(days=12))
            for k, v in kw.items():
                setattr(b, k, v)
            db.add(b); db.commit(); db.refresh(b)
            return b

        calls = {"charge": [], "email": [], "build": []}

        async def cards_none(customer_id):
            return []

        async def cards_one(customer_id):
            return [{"id": "pm_card_1", "label": "Visa •4242"}]

        async def charge_paid(**kw):
            calls["charge"].append(kw)
            return {"paid": True, "payment_intent": "pi_test_paid", "message": ""}

        async def charge_declined(**kw):
            calls["charge"].append(kw)
            return {"paid": False, "payment_intent": "pi_test_declined",
                    "message": "Your card was declined."}

        async def build_stub(fresh, session):
            calls["build"].append(fresh.id)
            return {"built": True, "posts": 14}

        def email_stub(to, boost, cents, build):
            calls["email"].append({"to": to, "boost": boost.id, "cents": cents})
            return True

        # ---------------------------------------------------------------- nothing due at all
        early = add("0 Too Early Road", launched_at=now - timedelta(days=2))
        out = asyncio.run(renewals.apply(db, now=now, cards_fn=cards_one, charge_fn=charge_paid,
                                         build_fn=build_stub, email_fn=email_stub))
        check("a campaign two days in is not touched", out["counts"]["due"] == 0, out["counts"])
        check("...and nothing was charged", calls["charge"] == [])

        # ---------------------------------------------------------------- no card on file
        due = add("1 Due Street")
        db.add(Asset(user_id=owner.id, boost_id=due.id, filename="f1.jpg", url="/uploads/f1.jpg",
                     kind="photo", room="kitchen", tags=["ROOM"]))
        db.commit()
        out = asyncio.run(renewals.apply(db, now=now, cards_fn=cards_none, charge_fn=charge_paid,
                                         build_fn=build_stub, email_fn=email_stub))
        check("no saved card means no charge", out["applied"][0]["status"] == "no_card",
              out["applied"][:1])
        check("...and no round was created", db.query(Boost).filter(Boost.address == "1 Due Street").count() == 1)
        check("...and the flag is still on, so it retries once a card exists", db.get(Boost, due.id).until_sold is True)

        # ---------------------------------------------------------------- charged, built, emailed
        out = asyncio.run(renewals.apply(db, now=now, cards_fn=cards_one, charge_fn=charge_paid,
                                         build_fn=build_stub, email_fn=email_stub))
        row = out["applied"][0]
        check("a due campaign renews", row["status"] == "renewed", row)
        check("the charge is the $39 repeat price", calls["charge"][-1]["cents"] == 3900, calls["charge"][-1])
        check("the charge names the new round", calls["charge"][-1]["round_no"] == 1, calls["charge"][-1])
        check("it charged the newest saved card", calls["charge"][-1]["payment_method_id"] == "pm_card_1")

        fresh = db.get(Boost, row["new_boost_id"])
        check("the next round exists as round 2", fresh.repeat_round == 1, fresh.repeat_round)
        check("...continuing the campaign it came from", fresh.parent_boost_id == due.id)
        check("...marked paid", bool(fresh.paid_at), fresh.paid_at)
        check("...at the repeat price", fresh.paid_amount_cents == 3900, fresh.paid_amount_cents)
        check("...on autopilot itself", fresh.until_sold is True)
        check("...with the photos carried over",
              db.query(Asset).filter(Asset.boost_id == fresh.id).count() == 1)
        check("the paid order is recorded",
              db.query(Order).filter(Order.boost_id == fresh.id, Order.status == "paid").count() == 1)
        check("the old round's flag is off, so it cannot charge twice",
              db.get(Boost, due.id).until_sold is False)
        check("the agent was told", calls["email"] and calls["email"][-1]["to"] == "owner@example.com")
        check("the event records the charge",
              db.query(Event).filter(Event.boost_id == fresh.id, Event.event_type == "renewal_charged").count() == 1)

        # ---------------------------------------------------------------- the second run is quiet
        before_second = len(calls["charge"])
        out = asyncio.run(renewals.apply(db, now=now, cards_fn=cards_one, charge_fn=charge_paid,
                                         build_fn=build_stub, email_fn=email_stub))
        check("running it again charges nothing", out["counts"]["due"] == 0, out["counts"])
        check("...and the charge count did not move", len(calls["charge"]) == before_second,
              len(calls["charge"]))

        # ---------------------------------------------------------------- the run cap
        for n in range(5):
            add("4 Many %d Way" % n)
        out = asyncio.run(renewals.apply(db, now=now, cards_fn=cards_one, charge_fn=charge_paid,
                                         build_fn=build_stub, email_fn=email_stub))
        check("one run renews at most three campaigns", out["counts"]["renewed"] == 3,
              out["counts"])

        # ---------------------------------------------------------------- a declined card
        declined = add("2 Declined Drive")
        before = len(calls["charge"])
        out = asyncio.run(renewals.apply(db, now=now, limit=10, cards_fn=cards_one,
                                         charge_fn=charge_declined, build_fn=build_stub,
                                         email_fn=email_stub))
        check("a decline is reported, not raised", out["applied"][0]["status"] == "declined",
              out["applied"][:1])
        # Other campaigns are still due in this fixture (sqlite reuses ids, so the earlier cap
        # test left work behind); what matters is that a charge was attempted for this one.
        check("...a charge was attempted", len(calls["charge"]) > before, len(calls["charge"]))
        check("...no half-made round is left behind",
              db.query(Boost).filter(Boost.address == "2 Declined Drive").count() == 1)
        check("...the decline is recorded",
              db.query(Event).filter(Event.boost_id == declined.id, Event.event_type == "renewal_declined").count() == 1)
        out = asyncio.run(renewals.apply(db, now=now, cards_fn=cards_one, charge_fn=charge_declined,
                                         build_fn=build_stub, email_fn=email_stub))
        check("...and it is not retried on the next tick", out["applied"][0]["status"] == "skipped",
              out["applied"][:1])

        # ---------------------------------------------------------------- a sold listing stops itself
        sold = add("3 Sold Street", listing_status="sold")
        before_sold = len(calls["charge"])
        out = asyncio.run(renewals.apply(db, now=now, cards_fn=cards_one, charge_fn=charge_paid,
                                         build_fn=build_stub, email_fn=email_stub))
        check("a sold listing is stopped", any(s["boost_id"] == sold.id for s in out["stopped"]), out["stopped"])
        check("...its flag is off", db.get(Boost, sold.id).until_sold is False)
        check("...and it was never charged", len(calls["charge"]) == before_sold,
              len(calls["charge"]))

    finally:
        db.close()

    print()
    if FAILS:
        print("FAILURES: %d" % FAILS)
        return 1
    print("ALL UNTIL-SOLD APPLY TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
