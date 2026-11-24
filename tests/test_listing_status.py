"""Engine 6, section 7: pending and sold, read from the status field, never guessed.

1. The layers: the known spot (and not a "similar homes" list), the standard spot, the AI only with a
   quote that's really on the page, a taken-down page is never a sale.
2. Deciding: one status field is enough, AI alone on two sources isn't, pending beats sold.
3. The campaign: pending pauses the ad and the posts and emails once; sold ends it with no email;
   back on the market with the same agent emails Turn it back on (set and forget resumes by itself);
   another agent's listing never prompts; resume gives the days back.
4. The agent's Pause pop-up (It's pending / It sold) and Turn it back on with a confirm.
5. The agent's own posts: this home only, quoted; a price post takes the price off the website.
6. Unreadable for a day alerts the team once; a site that changed its layout is noticed.
"""
import asyncio
import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-status-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["RESMARA_ADMIN_EMAILS"] = "team@example.com"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.db.session import Boost, ListingSite, Post, SessionLocal, User  # noqa: E402
from app.main import app  # noqa: E402
from app.services import campaign_state as cs  # noqa: E402
from app.services import listing_status as lst  # noqa: E402
from app.services import mail, publisher  # noqa: E402

SENT = []
mail.send_email = lambda to, subject, body: SENT.append((to, subject, body)) or True
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


def zillow(status, agent="Morgan Ellis", lic="0123456", price=845000, nearby="SOLD"):
    data = {"props": {"pageProps": {"property": {
        "streetAddress": "1248 Oakridge Drive", "homeStatus": status, "price": price,
        "attributionInfo": {"agentName": agent, "agentLicenseNumber": lic, "brokerName": "Morgan & Co."},
        "nearbyHomes": [{"streetAddress": "9 Elm Street", "homeStatus": nearby}]}}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(data)}</script></html>'


def ldjson(avail):
    return ('<html><script type="application/ld+json">' + json.dumps(
        {"@type": "RealEstateListing", "offers": {"availability": f"https://schema.org/{avail}", "price": 845000}})
        + '</script></html>')


# ---------------------------------------------------------------- 1. the layers
print("Reading one source")
r = lst.known_spot(zillow("PENDING"), "1248 Oakridge Drive")
ok("the known spot: homeStatus PENDING", r and r.status == "pending" and r.layer == "known")
ok("the listing agent is read too", r.agent.get("license") == "0123456")
ok("and the price", r.price_cents == 84500000)
r = lst.known_spot(zillow("FOR_SALE", nearby="SOLD"), "1248 Oakridge Drive")
ok("a 'similar homes' entry never decides", r.status == "active")
ok("the standard spot (schema.org)", lst.standard_spot(ldjson("SoldOut")).status == "sold")
page = "<html><body><h1>1248 Oakridge Drive</h1><p>Status: Under contract</p><h2>Recently sold nearby</h2><p>Sold 9 Elm</p></body></html>"


async def ai_good(text, address):
    return {"status": "pending", "quote": "Status: Under contract", "agent": "Morgan Ellis", "price": ""}


async def ai_made_up(text, address):
    return {"status": "sold", "quote": "This home has closed", "agent": ""}


async def ai_nearby(text, address):
    return {"status": "sold", "quote": "Sold 9 Elm"}

ok("the AI with a real quote", asyncio.run(lst.ai_read(page, "1248 Oakridge Drive", ai=ai_good)).status == "pending")
ok("the AI's quote has to be on the page", asyncio.run(lst.ai_read(page, "x", ai=ai_made_up)) is None)
ok("a quote from 'Recently sold nearby' never counts", asyncio.run(lst.ai_read(page, "x", ai=ai_nearby)) is None)

PAGES = {}


async def fetcher(url):
    return PAGES.get(url, (0, ""))

PAGES["https://aryeo.com/l/1"] = (404, "")
r = asyncio.run(lst.read_source("https://aryeo.com/l/1", "1248 Oakridge Drive", fetcher=fetcher))
ok("a taken-down photographer's page is not a sale", r.status == "offline" and not r.clear())
PAGES["https://www.zillow.com/x"] = (403, "blocked")
ok("a blocked page is unknown", asyncio.run(lst.read_source("https://www.zillow.com/x", "a", fetcher=fetcher)).status == "unknown")

# ---------------------------------------------------------------- 2. deciding
print("Deciding")
R = lambda src, st, layer="known": lst.Read(source=src, url="", status=st, layer=layer)
ok("one status field is enough", lst.decide([R("zillow", "pending"), R("link", "unknown", "unreadable")])[0] == "pending")
ok("pending beats sold", lst.decide([R("zillow", "pending"), R("redfin", "sold")])[0] == "pending")
ok("AI on one source against a status field on another: wait",
   lst.decide([R("link", "pending", "ai"), R("zillow", "active")])[0] is None)
ok("two sources agreeing (AI) is enough", lst.decide([R("link", "pending", "ai"), R("redfin", "pending", "ai")])[0] == "pending")
ok("nothing readable: don't act", lst.decide([R("link", "unknown", "unreadable")])[0] is None)
ok("listing-site links are kept from Engine 3's research",
   lst.sources_from_research("Found on Zillow (https://www.zillow.com/homedetails/1248-Oakridge/123_zpid/) and [Redfin]")
   == ["https://www.zillow.com/homedetails/1248-Oakridge/123_zpid/"])

# ---------------------------------------------------------------- 3. the campaign
print("The campaign")
db = SessionLocal()
agent = User(email="morgan@example.com", hashed_password="x", name="Morgan Ellis",
             brand={"agent": "Morgan Ellis", "license": "0123456", "company": "Morgan & Co."})
db.add(agent)
db.commit()
H = {"Authorization": "Bearer " + create_access_token({"sub": agent.email})}
now = datetime.now(timezone.utc)
boost = Boost(user_id=agent.id, address="1248 Oakridge Drive, Austin, TX", listing_url="https://agent.example/1248",
              listing_sources=["https://www.zillow.com/homedetails/1248"], launched_at=now - timedelta(days=3),
              go_live_date=(now - timedelta(days=3)).strftime("%Y-%m-%d"), campaign_days=14, paid_at=now, stage="LIVE")
db.add(boost)
db.commit()
db.add(ListingSite(boost_id=boost.id, user_id=agent.id, slug="1248-oakridge-drive", content={"photos": []}, brand={}))
for d in range(4, 8):
    db.add(Post(boost_id=boost.id, day=d, caption=f"Day {d}", client_status="approved", publish_status="scheduled",
                publish_at=(now - timedelta(minutes=5) + timedelta(days=d - 4)).isoformat(timespec="seconds")))
db.commit()

PAGES["https://agent.example/1248"] = (200, "<html>Loading…</html>")
PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("FOR_SALE"))
res = asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
ok("for sale: nothing happens", res["status"] == "active" and boost.paused_at is None and not SENT)

PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("PENDING"))
res = asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
db.refresh(boost)
ok("pending pauses right away", res["action"] == "pending" and boost.paused_at is not None and boost.paused_reason == "pending")
ok("the posts stop (the publisher skips a paused campaign)",
   not publisher._due_posts(db, now.isoformat(timespec="seconds"), 50, boost.id))
ok("one email with Turn it back on", len(SENT) == 1 and "Pending" in SENT[0][1] and "Turn it back on" in SENT[0][2])
ok("the website stops taking showings", "under contract" in __import__("app.services.listing_site", fromlist=["x"]).render(
   db.query(ListingSite).first(), boost, status="pending"))
ok("the card says Paused · Pending", cs.card_state(boost) == "Paused · Pending")
asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
ok("checked again every hour, no second email", len(SENT) == 1)

PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("FOR_SALE", agent="Pat Other", lic="999"))
res = asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
ok("back on the market with another agent: nothing", res["action"] == "back_not_same_agent" and len(SENT) == 1
   and boost.paused_at is not None)
PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("FOR_SALE"))
res = asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
ok("same agent: one email, and it doesn't restart by itself", res["action"] == "back_emailed" and len(SENT) == 2
   and "For Sale again" in SENT[1][1] and boost.paused_at is not None)

client = TestClient(app)
r = client.post(f"/api/boosts/{boost.id}/resume", headers=H)
ok("Turn it back on works when the listing is for sale", r.status_code == 200 and r.json()["status"] == "resumed", r.text)
db.refresh(boost)
ok("the banner goes and posts can go out again", boost.paused_at is None and boost.listing_status == "active")

# The agent's pop-up
r = client.post(f"/api/boosts/{boost.id}/pause", headers=H, json={"why": "pending"})
db.refresh(boost)
ok("It's pending pauses everything", r.json()["reason"] == "pending" and boost.paused_reason == "pending"
   and r.json()["card_state"] == "Paused · Pending")
boost.listing_reads = {"zillow": {"status": "pending", "layer": "known"}}
db.commit()
r = client.post(f"/api/boosts/{boost.id}/resume", headers=H, json={})
ok("still pending online: asks first", r.status_code == 409 and r.json()["detail"]["error"] == "still_pending")
r = client.post(f"/api/boosts/{boost.id}/resume", headers=H, json={"confirm": True})
ok("Turn it back on anyway", r.status_code == 200 and r.json()["status"] == "resumed")
PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("PENDING"))
db.refresh(boost)
res = asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
ok("and the hourly check doesn't pause it again for the same Pending", res["action"] == "agent_turned_it_back_on"
   and boost.paused_at is None)
PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("FOR_SALE"))
asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
ok("until the listing changes again", not (boost.listing_notes or {}).get("agent_override"))
r = client.post(f"/api/boosts/{boost.id}/pause", headers=H, json={"why": "pause"})
db.refresh(boost)
ok("Just pause it", boost.paused_reason == "agent" and cs.card_state(boost) == "Paused")
before = {p.id: p.publish_at for p in db.query(Post).filter(Post.boost_id == boost.id).all()}
boost.paused_at = datetime.now(timezone.utc) - timedelta(days=2)
db.commit()
r = client.post(f"/api/boosts/{boost.id}/resume", headers=H, json={})
db.refresh(boost)
after = {p.id: p.publish_at for p in db.query(Post).filter(Post.boost_id == boost.id).all()}
moved = [datetime.fromisoformat(after[k]) - datetime.fromisoformat(before[k]) for k in before]
ok("resume gives back the paused days (posts move forward)", r.json()["days_added"] == 2
   and all(timedelta(days=2) <= m < timedelta(days=2, minutes=5) for m in moved), moved)

# Run it until it sells: back on the market picks up by itself
SENT.clear()
boost.until_sold = True
boost.listing_status = "active"
db.commit()
PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("PENDING"))
asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
ok("set and forget: the pending email says we'll keep checking", SENT and "keep checking" in SENT[-1][2]
   and boost.until_sold is True)
PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("FOR_SALE"))
res = asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
db.refresh(boost)
ok("back with the same agent: running again by itself", res["action"] == "back_resumed" and boost.paused_at is None
   and "running again" in SENT[-1][1])

# Sold
SENT.clear()
PAGES["https://www.zillow.com/homedetails/1248"] = (200, zillow("SOLD"))
res = asyncio.run(cs.check(db, boost, fetcher=fetcher, ai=ai_made_up))
db.refresh(boost)
ok("sold pauses everything and ends Run it until it sells", res["action"] == "sold" and boost.paused_at is not None
   and boost.until_sold is False)
ok("no email when it sells", not SENT)
ok("the card says Completed · Sold", cs.card_state(boost) == "Completed · Sold")
r = client.post(f"/api/boosts/{boost.id}/resume", headers=H, json={"confirm": True})
ok("a sold campaign can't be turned back on", r.status_code == 409 and r.json()["detail"]["error"] == "sold")
ok("sold campaigns aren't checked any more", boost not in cs.due(db))

# ---------------------------------------------------------------- 5. the agent's own posts
print("The agent's own posts")
b2 = Boost(user_id=agent.id, address="76 Willow Lane, Austin, TX", listing_url="https://agent.example/76",
           launched_at=now - timedelta(days=2), go_live_date=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
           campaign_days=14, paid_at=now)
db.add(b2)
db.commit()
site2 = ListingSite(boost_id=b2.id, user_id=agent.id, slug="76-willow-lane", content={"photos": []}, brand={},
                    price_cents=62500000)
db.add(site2)
db.commit()
SENT.clear()
res = asyncio.run(cs.own_posts(db, b2, posts=[
    {"where": "Instagram", "text": "Under contract in 4 days! 9 Elm Street", "link": "x"},
    {"where": "Facebook", "text": "Golden hour at 76 Willow. See the home: homes.resmara.com/76-willow-lane", "link": "y"},
]))
ok("a post about another home never counts", not res["found"] and b2.paused_at is None)
res = asyncio.run(cs.own_posts(db, b2, posts=[{"where": "Instagram", "text": "Price improved on 76 Willow Lane!", "link": "z"}]))
db.refresh(site2)
ok("a price post about this home takes the price off", res["found"][0]["kind"] == "price" and site2.price_cents is None)
ok("and one email asks for the new price", SENT and "price change" in SENT[-1][1].lower()
   and "Your post on Instagram says the price on this home has improved" in SENT[-1][2])
res = asyncio.run(cs.own_posts(db, b2, posts=[{"where": "Facebook", "text": "76 Willow Lane is UNDER CONTRACT!", "link": "w"}]))
db.refresh(b2)
ok("'Under contract!' about this home pauses everything", res["found"][0]["kind"] == "pending" and b2.paused_reason == "pending")
ok("it keeps the post it quoted", "UNDER CONTRACT" in res["found"][0]["quote"])

# ---------------------------------------------------------------- 6. alerts
print("Alerts")
b3 = Boost(user_id=agent.id, address="5 Pine Court, Austin, TX", listing_url="https://agent.example/5",
           launched_at=now, go_live_date=now.strftime("%Y-%m-%d"), campaign_days=14, paid_at=now,
           listing_notes={"unreadable_since": (now - timedelta(hours=25)).isoformat()})
db.add(b3)
db.commit()
SENT.clear()
asyncio.run(cs.check(db, b3, fetcher=fetcher, ai=ai_made_up))
asyncio.run(cs.check(db, b3, fetcher=fetcher, ai=ai_made_up))
ok("no source readable for a day: the team hears once", len([s for s in SENT if s[0] == "team@example.com"]) == 1)
ok("a site that changed its layout is noticed", cs.layout_changes([
    {"reads": [{"source": "zillow", "http": 200, "layer": "ai"}]}] * 3) == ["zillow"])

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL LISTING STATUS TESTS PASSED")
