"""Engine 10 (Billing): prices from config, the card form in the pop-up, Remove card, Coming up,
purchases with tax and receipts, chargebacks, team refunds, card-expiring emails and closing an
account that stops everything. Stripe is never called: every network function is replaced."""
import asyncio
import os
import tempfile
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-e10-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["STRIPE_SECRET_KEY"] = "sk_test_x"
os.environ["STRIPE_PUBLISHABLE_KEY"] = "pk_test_x"
os.environ.pop("RESMARA_STRIPE_TAX", None)
os.environ["ADMIN_EMAILS"] = "team@resmara.com"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.db.session import (Ad, AdAccount, Base, Boost, Event, ListingSite, MetaConnection, Order,  # noqa: E402
                            Post, SessionLocal, User, engine)
from app.main import app  # noqa: E402
from app.services import account_close, billing, campaign_daily, mail  # noqa: E402

Base.metadata.create_all(bind=engine)
SENT = []
mail.send_email = lambda to, subject, body: SENT.append((to, subject, body)) or True
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


def run(coro):
    return asyncio.run(coro)


# ---- Stripe stand-ins ---------------------------------------------------------------------
CARDS = {"cus_1": [{"id": "pm_old", "brand": "visa", "last4": "4417", "exp_month": 12, "exp_year": 2026,
                    "label": "Visa ending 4417, expires 12/26"}]}
DETACHED, REFUNDS = [], []


async def fake_list_cards(customer_id, client=None):
    return list(CARDS.get(customer_id, []))


async def fake_detach(pm, client=None):
    DETACHED.append(pm)
    for cards in CARDS.values():
        cards[:] = [c for c in cards if c["id"] != pm]
    return True


async def fake_setup_card(session_id, client=None):
    if session_id != "cs_good":
        return None
    CARDS["cus_1"].append({"id": "pm_new", "brand": "visa", "last4": "1111", "exp_month": 1, "exp_year": 2030,
                           "label": "Visa ending 1111, expires 01/30"})
    return "pm_new" if session_id == "cs_good" else None


async def fake_keep_only(customer_id, keep_id, client=None):
    gone = [c["id"] for c in CARDS.get(customer_id, []) if c["id"] != keep_id]
    for pm in gone:
        await fake_detach(pm)
    return len(gone)


async def fake_receipt(pi, client=None):
    return {"receipt_url": f"https://pay.stripe.com/receipts/{pi}", "tax_cents": 0}


async def fake_refund(pi, cents=None, reason="", client=None):
    REFUNDS.append((pi, cents, reason))
    return {"id": "re_1"}


REAL_REFUND = billing.refund
billing.list_cards = fake_list_cards
billing.detach_card = fake_detach
billing.setup_session_card = fake_setup_card
billing.keep_only_card = fake_keep_only
billing.receipt = fake_receipt
billing.refund = fake_refund

db = SessionLocal()
now = datetime.now(timezone.utc)
agent = User(email="morgan@example.com", hashed_password="x", name="Morgan Ellis", stripe_customer_id="cus_1",
             facebook_id="fb-9")
db.add(agent)
db.commit()
token = create_access_token({"sub": agent.email})
H = {"Authorization": f"Bearer {token}"}
client = TestClient(app)

live = Boost(user_id=agent.id, address="1248 Oakridge Drive, Redding, CA", paid_at=now - timedelta(days=5),
             launched_at=now - timedelta(days=5), go_live_date=(now - timedelta(days=4)).strftime("%Y-%m-%d"),
             campaign_days=14, until_sold=True)
db.add(live)
db.commit()
paid = Order(user_id=agent.id, boost_id=live.id, amount_cents=4900, currency="usd", status="paid", paid_at=now,
             stripe_payment_intent="pi_1", kind="campaign")
db.add(paid)
db.commit()

print("[prices from config]")
cfg = client.get("/api/billing/config").json()
ok("the campaign price comes from the server", cfg.get("price_cents") == billing.price_cents(), cfg)
ok("so does the repeat price", cfg.get("repeat_price_cents") == billing.repeat_price_cents(), cfg)
ok("and whether tax is on (off until Adam switches Stripe Tax on)", cfg.get("tax") is False, cfg)

print("[sales tax]")
import httpx  # noqa: E402
CALLS = []


def stripe_handler(request):
    CALLS.append((request.url.path, request.content.decode()))
    if request.url.path.endswith("/tax/calculations"):
        return httpx.Response(200, json={"id": "taxcalc_1", "tax_amount_exclusive": 412, "amount_total": 4312})
    if request.url.path.endswith("/payment_intents"):
        return httpx.Response(200, json={"id": "pi_tax", "status": "succeeded"})
    if request.url.path.endswith("/payment_intents/pi_tax"):
        return httpx.Response(200, json={"id": "pi_tax", "metadata": {"tax_transaction": "tax_tx_1"}})
    if request.url.path.endswith("/refunds"):
        return httpx.Response(200, json={"id": "re_tax"})
    return httpx.Response(200, json={"id": "tx_1"})


async def taxed_charge():
    async with httpx.AsyncClient(transport=httpx.MockTransport(stripe_handler)) as c:
        return await billing.charge_saved_card("cus_1", "pm_old", 4900, live.id, agent.id, "1248 Oakridge Drive", 0, client=c)

os.environ["RESMARA_STRIPE_TAX"] = "1"
res = asyncio.run(taxed_charge())
os.environ.pop("RESMARA_STRIPE_TAX", None)
pi_body = next((b for p_, b in CALLS if p_.endswith("/payment_intents")), "")
ok("with Stripe Tax on, tax is added on top of the price", res.get("tax_cents") == 412 and "amount=4312" in pi_body,
   (res, pi_body[:200]))
ok("  ...and the tax is recorded with Stripe for filing", any(p_.endswith("create_from_calculation") for p_, _ in CALLS), CALLS)
ok("  ...with the tax transaction kept on the payment", any(p_.endswith("/payment_intents/pi_tax") and "tax_transaction" in b for p_, b in CALLS), CALLS)
CALLS.clear()


async def taxed_refund(cents):
    async with httpx.AsyncClient(transport=httpx.MockTransport(stripe_handler)) as c:
        return await _real_refund("pi_tax", cents, "test", client=c)

_real_refund = REAL_REFUND
os.environ["RESMARA_STRIPE_TAX"] = "1"
asyncio.run(taxed_refund(1000))
os.environ.pop("RESMARA_STRIPE_TAX", None)
rev = next((b for p_, b in CALLS if p_.endswith("create_reversal")), "")
ok("a refund reverses its share of the tax", "original_transaction=tax_tx_1" in rev and "mode=partial" in rev
   and "flat_amount=-1000" in rev, rev)
CALLS.clear()

print("[purchases]")
rows = client.get("/api/billing/orders", headers=H).json()
row = rows[0] if rows else {}
ok("each purchase says what it was", row.get("what") == "Campaign", row)
ok("its status in words", row.get("status_label") == "Paid", row)
ok("with Stripe's receipt", row.get("receipt_url", "").endswith("pi_1"), row)

print("[coming up]")
up = client.get("/api/billing/upcoming", headers=H).json().get("upcoming") or []
ok("Run it until it sells listings show in Coming up", len(up) == 1 and up[0]["boost_id"] == live.id, up)
ok("  ...with the round and the repeat price", up and up[0]["round"] == 2 and up[0]["amount_cents"] == billing.repeat_price_cents(), up)

print("[remove card]")
r = client.delete("/api/billing/card", headers=H)
ok("Remove is refused while Run it until it sells is on", r.status_code == 409 and "Oakridge" in r.text, r.text[:200])
ok("  ...and nothing was detached", not DETACHED)

print("[change card in the pop-up]")
r = client.post("/api/billing/card/saved", json={"session_id": "cs_bad"}, headers=H)
ok("an unfinished form saves nothing", r.status_code == 409, r.text[:200])
r = client.post("/api/billing/card/saved", json={"session_id": "cs_good"}, headers=H)
ok("the new card is saved", r.status_code == 200 and r.json().get("status") == "saved", r.text[:200])
ok("  ...and the old one is removed, so only one card pays", DETACHED == ["pm_old"] and
   [c["id"] for c in CARDS["cus_1"]] == ["pm_new"], (DETACHED, CARDS))

print("[chargebacks]")
event = {"type": "charge.dispute.created", "data": {"object": {"id": "dp_1", "payment_intent": "pi_1",
                                                               "status": "needs_response", "amount": 4900,
                                                               "reason": "fraudulent"}}}
out = billing.dispute_outcome(event)
ok("Stripe's dispute event is read", out and out["payment_intent"] == "pi_1" and out["event"] == "charge.dispute.created", out)
SENT.clear()
res = account_close.dispute(db, out)
db.refresh(agent)
ok("a chargeback pauses charges on the account", res["status"] == "dispute_opened" and agent.billing_hold == "dispute", res)
ok("  ...and the team is alerted with what Stripe needs", any(s[0] == "team@resmara.com" and "Chargeback" in s[1]
                                                              and "Renewal consent" in s[2] for s in SENT), SENT)
fresh = Boost(user_id=agent.id, address="77 New Listing Way, Redding, CA")
db.add(fresh)
db.commit()
r = client.post("/api/billing/charge", json={"boost_id": fresh.id}, headers=H)
db.delete(fresh)
db.commit()
ok("  ...new charges are refused while it's open", r.status_code == 402 and "billing_hold" in r.text, r.text[:200])
won = dict(out, event="charge.dispute.closed", status="won")
account_close.dispute(db, won)
db.refresh(agent)
ok("won: everything resumes", agent.billing_hold is None)
lost_evt = dict(out, event="charge.dispute.created")
account_close.dispute(db, lost_evt)
account_close.dispute(db, dict(out, event="charge.dispute.closed", status="lost"))
db.refresh(agent)
ok("lost: it stays paused until the agent contacts support", agent.billing_hold == "dispute")
agent.billing_hold = None
db.commit()

print("[team refunds]")
SENT.clear()
res = run(account_close.team_refund(db, paid, 1000, "Photos came late"))
ok("a partial refund", res["refunded_cents"] == 1000 and paid.status == "partially_refunded", res)
ok("  ...through Stripe with the reason", REFUNDS[-1] == ("pi_1", 1000, "Photos came late"), REFUNDS)
ok("  ...and the agent gets the refund email", any(s[0] == "morgan@example.com" and "We refunded $10" in s[1]
                                                   and "5 to 10 days" in s[2] for s in SENT), SENT)
res = run(account_close.team_refund(db, paid, None, "Make it right"))
ok("the rest refunds in full", res["refunded_cents"] == 3900 and paid.status == "refunded", res)
try:
    run(account_close.team_refund(db, paid, None, "again"))
    ok("nothing left can't be refunded twice", False)
except ValueError:
    ok("nothing left can't be refunded twice", True)

print("[card expiring]")
SENT.clear()
CARDS["cus_1"] = [{"id": "pm_new", "exp_month": now.month, "exp_year": now.year, "label": "Visa ending 1111"}]
n = run(campaign_daily.cards_expiring(db, now=now, list_cards=fake_list_cards))
ok("a card ending this month gets one email while Run it until it sells is on", n == 1 and
   any("expires soon" in s[1] for s in SENT), SENT)
SENT.clear()
run(campaign_daily.cards_expiring(db, now=now, list_cards=fake_list_cards))
ok("  ...never twice for the same card", not SENT, SENT)

print("[close my account]")
site = ListingSite(user_id=agent.id, boost_id=live.id, slug="1248-oakridge-drive", content={})
db.add(site)
db.add(Post(boost_id=live.id, day=9, publish_status="scheduled"))
db.add(MetaConnection(user_id=agent.id, fb_user_id="fb-9"))
db.add(AdAccount(user_id=agent.id, platform="meta", advertiser_id="act_1"))
ad = Ad(boost_id=live.id, kind="listing", meta_ad_id="ad_1", status="active")
db.add(ad)
unpaid = Boost(user_id=agent.id, address=live.address, parent_boost_id=live.id)
db.add(unpaid)
db.commit()
r = client.post("/api/auth/me/close", json={"email": "wrong@example.com"}, headers=H)
ok("closing needs the account email typed", r.status_code == 400, r.text[:200])
PAUSED = []


async def fake_pause(a):
    PAUSED.append(a.meta_ad_id)


SENT.clear()
res = run(account_close.close(db, agent, pause_ad=fake_pause))
db.expire_all()
agent = db.query(User).filter(User.id == agent.id).first()
ok("the account is closed", res["status"] == "closed" and agent.is_active is False and agent.closed_at, res)
ok("scheduled posts are cancelled", db.query(Post).filter(Post.boost_id == live.id, Post.publish_status == "scheduled").count() == 0)
ok("the ads Resmara runs are paused in Meta", PAUSED == ["ad_1"], PAUSED)
ok("Run it until it sells is off", db.get(Boost, live.id).until_sold is False)
ok("the built-but-unpaid round is discarded", db.get(Boost, unpaid.id) is None or res["rounds_discarded"] == 1, res)
ok("the saved card is removed from Stripe", "pm_new" in DETACHED and res["cards_removed"] == 1, res)
ok("Meta is disconnected", db.query(MetaConnection).filter(MetaConnection.user_id == agent.id).count() == 0)
acct = db.query(AdAccount).filter(AdAccount.user_id == agent.id).first()
ok("  ...and the ad account tokens are gone", acct._access_token is None and acct.token_status == "needs_reconnect")
page = client.get("/l/1248-oakridge-drive")
ok("the listing website says it's no longer available", page.status_code == 410 and "no longer available" in page.text,
   (page.status_code, page.text[:200]))
ok("the agent gets the account-closed email", any(s[0] == "morgan@example.com" and "account is closed" in s[1]
                                                  and "30 days" in s[2] for s in SENT), SENT)
ok("purchases are kept", db.query(Order).filter(Order.user_id == agent.id).count() == 1)
ok("their details stay for 30 days so logging in can reopen it", agent.email == "morgan@example.com")
account_close.wipe_due(db, now=now + timedelta(days=31))
db.expire_all()
agent = db.query(User).filter(User.id == agent.id).first()
ok("after 30 days their details are deleted", agent.email.startswith("deleted-") and agent.name == "Deleted account"
   and agent.facebook_id is None, agent.email)
ok("  ...purchases still kept", db.query(Order).filter(Order.user_id == agent.id).count() == 1)

print(f"\n{checks - failures}/{checks} passed")
print("ENGINE 10 PASSED" if not failures else "ENGINE 10 FAILED")
raise SystemExit(1 if failures else 0)
