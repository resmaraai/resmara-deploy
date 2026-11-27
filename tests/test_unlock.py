"""Build first, then pay to unlock (sign-up tour engine, section 5).

* The first campaign builds with no card.
* Built and unpaid = locked: nothing to read, approve, post or launch; three blurred pictures only.
* One locked campaign at a time.
* A saved card unlocks the next campaign as soon as it's built; a decline leaves it locked.
* Stripe's form is embedded (ui_mode=embedded) and "Save this card" sets setup_future_usage.
"""

import asyncio
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-unlock-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi import HTTPException  # noqa: E402
from app.db.session import Base, engine, SessionLocal, User, Boost, Post, Event  # noqa: E402
from app.api import billing as api  # noqa: E402
from app.services import billing  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


def raises(fn, status, error):
    try:
        fn()
    except HTTPException as exc:
        return exc.status_code == status and (exc.detail or {}).get("error") == error
    return False


u = User(email="agent@example.com", hashed_password="x", name="Jamie", facebook_id="fb1")
db.add(u)
db.commit()


def campaign(address):
    b = Boost(user_id=u.id, address=address)
    db.add(b)
    db.commit()
    return b


def build(b):
    for d in range(1, 15):
        db.add(Post(boost_id=b.id, day=d, slot=1, caption=f"Day {d}", image_url=f"/uploads/{d}.jpg"))
    db.add(Event(user_id=u.id, boost_id=b.id, event_type="campaign_built", payload={}))
    db.commit()


print("The first campaign")
first = campaign("905 Laurel Bend")
try:
    api.allow_build(first, u, db)
    built_ok = True
except HTTPException:
    built_ok = False
ok("builds with no card", built_ok)
ok("not locked before it's built", not api.is_locked(first, u, db))
build(first)
ok("built and unpaid is locked", api.is_locked(first, u, db))
ok("review and approval wait for payment", raises(lambda: api.require_unlocked(first, u, db), 402, "locked"))
try:
    api.require_unlocked(first, u, db)
except HTTPException as exc:
    msg = exc.detail["message"]
ok("  ...with the unlock message", "905 Laurel Bend is built. Pay $" in msg and "to unlock it" in msg, msg)
ok("rebuilding a locked campaign needs paying first", raises(lambda: api.allow_build(first, u, db), 402, "payment_required"))

print("One locked campaign at a time")
second = campaign("12 Oak Way")
ok("a second campaign can't build while one is locked", raises(lambda: api.allow_build(second, u, db), 409, "unlock_first"))
try:
    api.allow_build(second, u, db)
except HTTPException as exc:
    d = exc.detail
ok("  ...names the waiting one", d["boost_id"] == first.id and "Unlock 905 Laurel Bend first" in d["message"], d)

hand = campaign("1 Hand Made Ln")
db.add(Post(boost_id=hand.id, day=1, slot=1, caption="typed in"))
db.commit()
ok("posts added by hand (no Resmara build) never lock", not api.is_locked(hand, u, db))
hand.hidden = True
db.commit()

print("Locked preview")
from app.api.engine import list_posts, get_plan  # noqa: E402
rows = list_posts(first.id, current_user=u, db=db)
ok("three pictures, nothing to read", sum(1 for r in rows if r["image_url"]) == 3
   and all(r["caption"] is None and r["locked"] for r in rows), rows[:2])
ok("the plan is hidden while locked", get_plan(first.id, current_user=u, db=db).get("locked") is True)

print("Paying unlocks it")
api.record_paid(db, first, u, 4900, via="checkout")
ok("paid: unlocked", not api.is_locked(first, u, db))
ok("the second campaign can now build", (lambda: (api.allow_build(second, u, db), True))()[1])
full = list_posts(first.id, current_user=u, db=db)
ok("the posts can be read once paid", full[0]["caption"] == "Day 1")

print("A saved card unlocks the next one as soon as it's built")
build(second)
u.stripe_customer_id = "cus_test"
db.commit()
real = (billing.billing_enabled, billing.list_cards, billing.charge_saved_card)
billing.billing_enabled = lambda: True


async def cards(_):
    return [{"id": "pm_1", "label": "Visa ending 4242"}]


async def charge_ok(**kw):
    return {"paid": True, "payment_intent": "pi_1"}


async def charge_no(**kw):
    return {"paid": False, "message": "Your card was declined."}


billing.list_cards = cards
billing.charge_saved_card = charge_no
res = asyncio.run(api.charge_saved(db, second, u))
ok("a declined saved card leaves it locked", res["status"] == "declined" and api.is_locked(second, u, db), res)
billing.charge_saved_card = charge_ok
res = asyncio.run(api.charge_saved(db, second, u))
ok("a saved card unlocks it", res["status"] == "paid" and not api.is_locked(second, u, db), res)
billing.billing_enabled, billing.list_cards, billing.charge_saved_card = real

print("Stripe's form, embedded")
pairs = billing.checkout_payload(7, 1, "905 Laurel Bend", "https://www.resmara.com", 4900,
                                 customer_id="cus_x", save_card=True, embedded=True)
keys = dict(pairs)
ok("ui_mode=embedded_page with a return_url, no success page", keys.get("ui_mode") == "embedded_page"
   and "return_url" in keys and "success_url" not in keys, keys)
ok("Save this card sets setup_future_usage", keys.get("payment_intent_data[setup_future_usage]") == "off_session")
no_save = dict(billing.checkout_payload(7, 1, "x", "https://x", 4900, customer_id="cus_x", save_card=False, embedded=True))
ok("unticked: the card isn't saved", "payment_intent_data[setup_future_usage]" not in no_save)
hosted = dict(billing.checkout_payload(7, 1, "x", "https://x", 4900))
ok("the hosted page still works for old links", "success_url" in hosted and "ui_mode" not in hosted)

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL UNLOCK TESTS PASSED")
