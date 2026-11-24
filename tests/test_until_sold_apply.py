#!/usr/bin/env python3
"""Run it until it sells, the money half (Engine 8, docs/engines/engine-8-brain.md), Stripe stubbed.

A renewal that charges a card is the highest-risk code in this app: nobody is watching, the
customer is asleep, and a bug is a real $39. What is pinned is the order and every refusal:

  * build first, charge only when the build succeeded; a build that fails twice is never charged
  * charged: a paid Order, posts approved automatically, launched for the day the round ends,
    the flag moves to the new round, the website keeps its link, one "goes live" email
  * declined: nothing charged, nothing live, the built round kept; tried once a day, 3 times,
    then one Check billing email; a saved card charges it straight away
  * pending holds it (still on); sold ends it
  * Run it again · $39: the same path, live the next morning, the series stays off
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
    print(("  ok   " if cond else "  FAIL ") + label + ("" if cond else " " + str(detail)[:300]))
    if not cond:
        FAILS += 1


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="resmara-apply-")
    os.environ["UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "apply.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-until-sold-apply")
    os.environ["RESMARA_ADMIN_EMAILS"] = "team@example.com"
    os.environ.pop("STRIPE_SECRET_KEY", None)
    os.environ.pop("RESMARA_SIMULATE", None)

    from app.db.session import Base, engine, SessionLocal, Boost, Asset, ListingSite, Order, Post, User  # noqa
    from app.db.migrate import migrate
    from app.services import mail, renewals

    sent = []
    mail.send_email = lambda to, subject, body: sent.append((to, subject, body)) or True
    Base.metadata.create_all(bind=engine)
    migrate()
    db = SessionLocal()
    now = datetime.now(timezone.utc)
    owner = User(email="morgan@example.com", name="Morgan Ellis", is_active=True, hashed_password="x",
                 stripe_customer_id="cus_test_1")
    db.add(owner)
    db.commit()

    def add(address, **kw):
        b = Boost(user_id=owner.id, address=address, main_status="Live", stage="LAUNCHED", repeat_round=0,
                  until_sold=True, campaign_days=14, launched_at=now - timedelta(days=12),
                  go_live_date=(now - timedelta(days=12)).strftime("%Y-%m-%d"), paid_at=now - timedelta(days=13))
        for k, v in kw.items():
            setattr(b, k, v)
        db.add(b)
        db.commit()
        db.add(Asset(user_id=owner.id, boost_id=b.id, filename=f"{b.id}-front.jpg", url="/uploads/x.jpg", kind="photo"))
        db.commit()
        return b

    order = []

    async def build_ok(fresh, d):
        order.append(("build", fresh.id))
        for day in (1, 2):
            d.add(Post(boost_id=fresh.id, day=day, caption=f"Round post {day}", client_status="pending",
                       publish_status="scheduled",
                       publish_at=(datetime.strptime(fresh.go_live_date, "%Y-%m-%d")
                                   + timedelta(days=day - 1, hours=18)).isoformat()))
        d.commit()

    async def build_broken(fresh, d):
        order.append(("build-fail", fresh.id))
        raise RuntimeError("the plan model timed out")

    async def cards_one(customer_id):
        return [{"id": "pm_card_1"}]

    async def cards_none(customer_id):
        return []

    async def charge_ok(**kw):
        order.append(("charge", kw["boost_id"]))
        return {"paid": True, "payment_intent": "pi_ok"}

    async def charge_declined(**kw):
        order.append(("decline", kw["boost_id"]))
        return {"paid": False, "message": "Your card was declined."}

    async def launch_ok(b, u, d):
        order.append(("launch", b.id))
        return {"status": "launched"}

    kw = dict(cards_fn=cards_one, launch_fn=launch_ok)

    print("Build first, then charge")
    due = add("1248 Oakridge Drive, Austin, TX")
    db.add(ListingSite(boost_id=due.id, user_id=owner.id, slug="1248-oakridge-drive", content={"photos": []}, brand={}))
    db.commit()
    res = asyncio.run(renewals.apply(db, now=now, build_fn=build_ok, charge_fn=charge_ok, **kw))
    row = res["applied"][0]
    fresh = db.get(Boost, row.get("new_boost_id"))
    check("renewed", row["status"] == "renewed", row)
    check("built before it was charged, launched after", [o[0] for o in order] == ["build", "charge", "launch"], order)
    check("a paid $39 order", db.query(Order).filter(Order.boost_id == fresh.id, Order.status == "paid").count() == 1
          and fresh.paid_amount_cents == 3900)
    check("approved automatically", all(p.client_status == "approved" for p in db.query(Post).filter(Post.boost_id == fresh.id)))
    check("goes live the day the current round ends", fresh.go_live_date == (now + timedelta(days=2)).strftime("%Y-%m-%d"),
          fresh.go_live_date)
    check("the series moves to the new round", fresh.until_sold is True and db.get(Boost, due.id).until_sold is False)
    check("the website keeps its link on the new round",
          db.query(ListingSite).filter(ListingSite.slug == "1248-oakridge-drive").first().boost_id == fresh.id)
    check("one email: it goes live, nothing to do", len(sent) == 1 and "goes live" in sent[0][1]
          and "Nothing to do" in sent[0][2], sent)
    check("the photos came along", db.query(Asset).filter(Asset.boost_id == fresh.id).count() == 1)
    res = asyncio.run(renewals.apply(db, now=now, build_fn=build_ok, charge_fn=charge_ok, **kw))
    check("run again straight away: nothing to do", not res["applied"], res["applied"])

    print("A build that fails is never charged")
    order.clear()
    sent.clear()
    broken = add("2 Broken Way, Austin, TX")
    res = asyncio.run(renewals.apply(db, now=now, build_fn=build_broken, charge_fn=charge_ok, **kw))
    check("failed, retried once, no charge", res["applied"][0]["status"] == "failed"
          and [o[0] for o in order] == ["build-fail", "build-fail"], order)
    check("nothing left behind", db.query(Boost).filter(Boost.parent_boost_id == broken.id).count() == 0)
    check("the team is told", any(s[0] == "team@example.com" for s in sent))
    broken.until_sold = False
    db.commit()

    print("A declined card")
    order.clear()
    sent.clear()
    dec = add("3 Decline Court, Austin, TX")
    res = asyncio.run(renewals.apply(db, now=now, build_fn=build_ok, charge_fn=charge_declined, **kw))
    waiting = renewals.waiting_round(db, dec)
    check("nothing charged, nothing live, the built round kept", res["applied"][0]["status"] == "declined"
          and waiting is not None and waiting.paid_at is None and ("launch", waiting.id) not in order)
    check("no email after the first decline", not sent)
    res = asyncio.run(renewals.apply(db, now=now + timedelta(hours=2), build_fn=build_ok, charge_fn=charge_declined, **kw))
    check("tried once a day, not every tick", res["applied"][0]["status"] == "skipped")
    for i in (1, 2):
        res = asyncio.run(renewals.apply(db, now=now + timedelta(days=i, hours=1), build_fn=build_ok,
                                         charge_fn=charge_declined, **kw))
    check("not rebuilt on a retry", [o[0] for o in order].count("build") == 1, order)
    check("after the 3rd decline: one Check billing email", len(sent) == 1 and "couldn't renew" in sent[0][1]
          and "Check billing" in sent[0][2], sent)
    check("the old round still runs to its end", db.get(Boost, dec.id).paused_at is None)
    res = asyncio.run(renewals.apply(db, now=now + timedelta(days=4), build_fn=build_ok, charge_fn=charge_declined, **kw))
    check("then it waits for a card", res["applied"][0]["status"] == "on_hold", res["applied"])
    order.clear()
    res = asyncio.run(renewals.card_saved(db, owner.id, now=now + timedelta(days=4, hours=1), build_fn=build_ok,
                                          charge_fn=charge_ok, **kw))
    row = (res.get("applied") or [{}])[0]
    check("a saved card charges the waiting round straight away", row.get("status") == "renewed"
          and [o[0] for o in order] == ["charge", "launch"], (row, order))
    if row.get("new_boost_id"):
        check("the old round had ended, so it goes live the next morning",
              db.get(Boost, row["new_boost_id"]).go_live_date == (now + timedelta(days=5)).strftime("%Y-%m-%d"),
              db.get(Boost, row["new_boost_id"]).go_live_date)

    print("No card at all")
    order.clear()
    nocard = add("4 No Card Lane, Austin, TX")
    res = asyncio.run(renewals.apply(db, now=now, build_fn=build_ok, charge_fn=charge_ok, cards_fn=cards_none,
                                     launch_fn=launch_ok))
    mine = [r for r in res["applied"] if r["boost_id"] == nocard.id]
    check("no card is a decline: nothing charged", mine and mine[0]["status"] == "declined"
          and "charge" not in [o[0] for o in order], res["applied"])
    nocard.until_sold = False
    db.commit()

    print("Pending and sold")
    order.clear()
    pend = add("5 Pending Street, Austin, TX", listing_status="pending", paused_at=now, paused_reason="pending")
    sold = add("6 Sold Street, Austin, TX", listing_status="sold")
    asyncio.run(renewals.apply(db, now=now, build_fn=build_ok, charge_fn=charge_ok, **kw))
    check("pending: nothing built or charged, and it stays on",
          not [o for o in order if o[1] in (pend.id,)] and db.get(Boost, pend.id).until_sold is True
          and renewals.waiting_round(db, pend) is None)
    check("sold: ends it", db.get(Boost, sold.id).until_sold is False)

    print("Run it again · $39")
    order.clear()
    sent.clear()
    done = add("7 Again Avenue, Austin, TX", until_sold=False,
               go_live_date=(now - timedelta(days=15)).strftime("%Y-%m-%d"))
    res = asyncio.run(renewals.run_again(db, done, owner, build_fn=build_ok, charge_fn=charge_ok, **kw))
    again = db.get(Boost, res.get("new_boost_id")) if res.get("new_boost_id") else None
    check("one click: built, charged, launched", res["status"] == "renewed"
          and [o[0] for o in order] == ["build", "charge", "launch"], (res, order))
    check("live the next morning", again is not None and again.go_live_date == (now + timedelta(days=1)).strftime("%Y-%m-%d"))
    check("and the series stays off", again is not None and again.until_sold is False)
    check("never for a pending listing",
          asyncio.run(renewals.run_again(db, pend, owner, build_fn=build_ok, charge_fn=charge_ok, **kw))["status"] == "skipped")

    db.close()
    if FAILS:
        print("FAILURES: %d" % FAILS)
        return 1
    print("ALL UNTIL-SOLD APPLY TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
