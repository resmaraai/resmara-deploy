"""Engine 5: the listing website (docs/engines/engine-5-brain.md).

1. The address: slug from the street, -city then -2 on a clash, never changes, new rounds keep it.
2. The build: chapters checked (Fair Housing, prices, real photos), "please check" facts held back,
   the ad's destination becomes the website.
3. The page: finished HTML with the share card, facts band, chapters, legal footer; not public until
   unlocked; preview link; homes.resmara.com routing; unknown slug is a friendly page.
4. States: pending and sold banners, "Ask about similar homes", the agent card 30 days after the end.
5. Visitors: visits once a day, the form (emailed, trap, limit), call and text taps (once a day).
6. The price: shown when sources agree, off on a disagreement with one email, the two buttons.
7. Photos through the app; Facebook carries the tagged link, Instagram never; the ad is tagged.
"""
import asyncio
import io
import os
import tempfile
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-site-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["UPLOAD_DIR"] = tempfile.mkdtemp(prefix="resmara-site-up-")
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["RESMARA_PUBLISH_TOKEN"] = "clock-token"

from fastapi.testclient import TestClient  # noqa: E402
from PIL import Image  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.db.session import Asset, Boost, Event, Lead, ListingSite, Post, SessionLocal, User  # noqa: E402
from app.main import app  # noqa: E402
from app.services import listing_site as ls  # noqa: E402
from app.services import mail  # noqa: E402

SENT = []
mail.send_email = lambda to, subject, body: SENT.append((to, subject, body)) or True

checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


def jpeg(colour="#557799"):
    buf = io.BytesIO()
    Image.new("RGB", (1600, 1100), colour).save(buf, "JPEG")
    return buf.getvalue()


db = SessionLocal()
agent = User(email="morgan@example.com", hashed_password="x", name="Morgan Ellis",
             brand={"agent": "Morgan Ellis", "company": "Morgan & Co.", "license": "0123456", "phone": "(512) 555-0148",
                    "palette": [["Primary", "#203040"], ["Accent", "#c0392b"]], "fonts": ["Lora", "Inter"],
                    "legal": ["Morgan Ellis · (512) 555-0148", "License #0123456", "Morgan & Co.", "Equal Housing Opportunity"],
                    "voiceOfClient": "warm and plain"})
db.add(agent)
db.commit()
H = {"Authorization": "Bearer " + create_access_token({"sub": agent.email})}

plan = {"propertyStory": {"thesis": "A Hill Country home built around the view",
                          "differentiators": ["A long pool facing the lake", "A limestone kitchen", "A covered outdoor room",
                                              "A quiet primary suite"]},
        "posts": [{"photoFile": "p2.jpg"}]}
boost = Boost(user_id=agent.id, address="1248 Oakridge Drive, Austin, TX 78738", plan=plan,
              property_facts="4 beds, 3.5 baths, 3,420 sq ft on 1.2 acres, built 2015.", stage="LIVE",
              go_live_date=(datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d"), campaign_days=14)
db.add(boost)
db.commit()
for i, room in enumerate(["Exterior front", "Kitchen", "Pool", "Primary bedroom", "Living room", "Patio"], start=1):
    db.add(Asset(user_id=agent.id, boost_id=boost.id, filename=f"p{i}.jpg", url=f"/uploads/p{i}.jpg", kind="photo",
                 room=room, see=room, data=jpeg(), content_type="image/jpeg"))
db.commit()


async def writer(b, kit, photos):
    return {
        "facts": {"beds": 4, "baths": 3.5, "sqft": "3,420", "lot": "1.2 acres", "year_built": 2015, "garage": None,
                  "city": "Austin, TX 78738"},
        "please_check": ["year_built"],
        "headline": "A Hill Country home built around the view",
        "chapters": [
            {"title": "The arrival", "text": "A limestone path leads to a glass front door.", "photos": ["p1.jpg", "p5.jpg"]},
            {"title": "The heart of the house", "text": "The kitchen opens to the living room.", "photos": ["p2.jpg", "p5.jpg"]},
            {"title": "Perfect for families", "text": "Great schools and a safe neighborhood for young families.", "photos": ["p3.jpg"]},
            {"title": "The evenings", "text": "Priced at $845,000, the pool faces west.", "photos": ["p3.jpg"]},
            {"title": "The mornings", "text": "The primary suite looks out on oaks.", "photos": ["nope.jpg"]},
        ],
        "note": "Come at golden hour if you can.",
        "neighborhood": [{"place": "downtown Austin", "minutes": 25}, {"place": "", "minutes": 4}],
        "open_house": None,
    }

# ---------------------------------------------------------------- 1. the address
print("The address")
ok("slug is the street", ls.make_slug(db, "1248 Oakridge Drive, Austin, TX") == "1248-oakridge-drive")
db.add(ListingSite(boost_id=999001, user_id=agent.id, slug="76-willow-lane"))
db.commit()
ok("a clash adds the city", ls.make_slug(db, "76 Willow Lane, Dallas, TX") == "76-willow-lane-dallas")
db.add(ListingSite(boost_id=999002, user_id=agent.id, slug="76-willow-lane-dallas"))
db.commit()
ok("then -2", ls.make_slug(db, "76 Willow Lane, Dallas, TX") == "76-willow-lane-dallas-2")

# ---------------------------------------------------------------- 2. the build
print("The build")
site = asyncio.run(ls.build(db, boost, writer=writer))
c = site.content
titles = [ch["title"] for ch in c["chapters"]]
ok("the slug is saved", site.slug == "1248-oakridge-drive")
ok("a Fair Housing chapter is dropped", "Perfect for families" not in titles, titles)
ok("a chapter naming a price is dropped", "The evenings" not in titles, titles)
ok("a chapter whose photos aren't real gets a real one", "The mornings" in titles and
   all(p in c["photos"] for ch in c["chapters"] for p in ch["photos"]))
ok("no photo is used twice across chapters",
   len([p for ch in c["chapters"] for p in ch["photos"]]) == len({p for ch in c["chapters"] for p in ch["photos"]}))
ok("the checks say what was dropped", any("Fair Housing" in x for x in site.checks) and any("price" in x for x in site.checks))
ok("a neighborhood line without a place is dropped", c["neighborhood"] == [{"place": "downtown Austin", "minutes": 25}])
ok("the exterior is the hero", c["photos"][0] == "p1.jpg")
ok("the ad now clicks to the website", boost.destination_url == "https://homes.resmara.com/1248-oakridge-drive")
ok("a share image was made", site.share_asset_id is not None)
ok("please-check facts are held back", "year_built" not in ls.visible_facts(c) and ls.visible_facts(c)["beds"] == 4)
ok("the brand kit is snapshotted", site.brand["primary"] == "#203040" and site.brand["fonts"] == ["Lora", "Inter"]
   and not any("Equal Housing" in l for l in site.brand["legal"]))

client = TestClient(app)
print("The page")
r = client.get("/l/1248-oakridge-drive")
ok("not public until the campaign is unlocked", r.status_code == 404 and "isn't here" in r.text)
r = client.get(f"/l/1248-oakridge-drive?preview={ls.preview_token(site)}")
ok("the agent's preview link works before unlock", r.status_code == 200 and "Preview" in r.text)
r = client.get("/l/1248-oakridge-drive?preview=wrong")
ok("a wrong preview token doesn't", r.status_code == 404)

boost.paid_at = datetime.now(timezone.utc)
db.commit()
r = client.get("/l/1248-oakridge-drive")
t = r.text
ok("public once unlocked", r.status_code == 200)
ok("the title and share card are in the HTML", "<title>1248 Oakridge Drive, Austin, TX 78738</title>" in t
   and 'property="og:image"' in t and "/l/1248-oakridge-drive/share.jpg" in t)
ok("the facts band", "Bedrooms" in t and "3,420 sq ft" in t and "1.2 acres" in t)
ok("the held fact isn't shown", "Year built" not in t)
ok("the story headline and chapters", "built around the view" in t and "The heart of the house" in t and 'class="ch-num">01' in t)
ok("Schedule a showing", "Schedule a showing" in t and "Ask about similar homes" not in t)
ok("no price found: ask the agent", "Ask Morgan about pricing" in t)
ok("the agent's note, card, Call and Text", "golden hour" in t and "License #0123456" in t and 'href="tel:5125550148"' in t
   and 'href="sms:5125550148"' in t)
ok("the footer: legal lines, Equal Housing, believed accurate", "Morgan &amp; Co." in t and "Equal Housing Opportunity" in t
   and "believed accurate but not guaranteed" in t)
ok("the brand's colours and fonts", "--p:#203040" in t and "family=Lora" in t)
ok("the phone bar", 'class="bar"' in t)
ok("Open in Maps", "google.com/maps/search" in t)
r = client.get("/1248-oakridge-drive", headers={"host": "homes.resmara.com"})
ok("homes.resmara.com/<slug> is the page", r.status_code == 200 and "The heart of the house" in r.text)
r = client.get("/nothing-here", headers={"host": "homes.resmara.com"})
ok("an unknown slug is a friendly page, not an error", r.status_code == 404 and "This home isn't here" in r.text)
r = client.get("/l/1248-oakridge-drive/share.jpg")
ok("the share image is served", r.status_code == 200 and r.headers["content-type"] == "image/jpeg")
r = client.get("/photos/p2.jpg?w=700", headers={"host": "homes.resmara.com"})
ok("photos load through the app, resized, long cache",
   r.status_code == 200 and Image.open(io.BytesIO(r.content)).size[0] <= 1200 and "max-age=2592000" in r.headers["cache-control"])
ok("only listing photos are served there", client.get("/photos/secret.txt").status_code == 404)

# ---------------------------------------------------------------- 5. visitors
print("Visitors")
B = "/api/public/listing/1248-oakridge-drive"
r1 = client.post(B + "/visit", json={"visitor": "v1", "source": "post-7"}).json()
r2 = client.post(B + "/visit", json={"visitor": "v1", "source": "post-7"}).json()
client.post(B + "/visit", json={"visitor": "v2", "source": "ad"})
ok("a visit counts once a day per visitor", r1.get("counted") is True and r2.get("counted") is False)
SENT.clear()
r = client.post(B + "/lead", json={"name": "Jo Buyer", "email": "jo@example.com", "wants": "showing", "visitor": "v1",
                                   "message": "Saturday?", "source": "post-7"})
lead = db.query(Lead).filter(Lead.boost_id == boost.id, Lead.source == "web").first()
ok("the form makes a lead", r.status_code == 200 and lead is not None and lead.email == "jo@example.com" and lead.wants == "showing")
ok("and emails the agent straight away", SENT and SENT[0][0] == "morgan@example.com" and "Jo Buyer" in SENT[0][1]
   and lead.notified_at is not None)
r = client.post(B + "/lead", json={"name": "Bot", "email": "b@x.com", "website": "spam.com"})
ok("the trap field is ignored silently", r.status_code == 200 and db.query(Lead).filter(Lead.author_name == "Bot").count() == 0)
r = client.post(B + "/lead", json={"name": "No email", "email": "nope"})
ok("a bad email is refused", r.status_code == 422)
ok("call tap counts", client.post(B + "/call", json={"visitor": "v1"}).json()["counted"] is True)
ok("a second call tap that day doesn't", client.post(B + "/call", json={"visitor": "v1"}).json()["counted"] is False)
ok("text tap is its own lead", client.post(B + "/text", json={"visitor": "v1"}).json()["counted"] is True)
calls = db.query(Lead).filter(Lead.boost_id == boost.id, Lead.source == "call").all()
ok("call leads send no email", len(SENT) == 1 and calls[0].channel == "Listing page call button")
s = client.get(f"/api/boosts/{boost.id}/site", headers=H).json()
ok("section 3 numbers: visits, form, call, text leads", s["stats"]["visits"] == 2 and s["stats"]["forms"] == 1
   and s["stats"]["calls"] == 1 and s["stats"]["texts"] == 1, s.get("stats"))
ok("and which post or ad brought them", s["stats"]["sources"].get("post-7") == 1 and s["stats"]["sources"].get("ad") == 1)
ok("section 3 gets the link and the preview", s["url"].endswith("/1248-oakridge-drive") and "preview=" in s["preview_url"])
ok("another agent can't read it", client.get(f"/api/boosts/{boost.id}/site",
   headers={"Authorization": "Bearer " + create_access_token({"sub": "nobody@example.com"})}).status_code == 401)
r = client.post(f"/api/boosts/{boost.id}/site/confirm", headers=H, json={"confirm": ["year_built"]})
ok("confirming a fact in review shows it", "Year built" in client.get("/l/1248-oakridge-drive").text)

# ---------------------------------------------------------------- 6. the price
print("The price")
SENT.clear()
ok("sources agree: shown", ls.apply_price_readings(db, site, {"zillow": 84500000, "agent": 84500000}) == "price_shown")
ok("as Listed at", "Listed at $845,000" in client.get("/l/1248-oakridge-drive").text)
res = ls.apply_price_readings(db, site, {"zillow": 82500000, "agent": 84500000})
ok("sources disagree: off at once, one email", res == "price_held_email" and site.price_cents is None and len(SENT) == 1
   and "price change" in SENT[0][1].lower())
ok("the email has both buttons", "?do=set" in SENT[0][2] and "?do=none" in SENT[0][2])
ok("not asked twice for the same change", ls.apply_price_readings(db, site, {"zillow": 82500000, "agent": 84500000}) == "price_held"
   and len(SENT) == 1)
ok("the page shows no price meanwhile", "Ask Morgan about pricing" in client.get("/l/1248-oakridge-drive").text)
token = site.price_token
db.add(Post(boost_id=boost.id, day=5, caption="The evenings here are golden. Priced to sell. Come see it.",
            publish_status="scheduled", client_status="approved"))
db.commit()
r = client.get(f"/api/public/price/{token}?do=set")
ok("Set a new price opens one page", r.status_code == 200 and "Current list price" in r.text)
r = client.post(f"/api/public/price/{token}", data={"price": "$825,000"})
db.refresh(site)
ok("saving shows it straight away", site.price_cents == 82500000 and site.price_mode == "agent"
   and "Listed at $825,000" in client.get("/l/1248-oakridge-drive").text)
post = db.query(Post).filter(Post.boost_id == boost.id).first()
ok("posts still to go out say Improved price, no number", "Improved price." in post.caption and "$" not in post.caption
   and "Priced" not in post.caption)
db.refresh(boost)
ok("the next round can lead with it", (boost.plan or {}).get("price_update", {}).get("words") == "Improved price")
r = client.get(f"/api/public/price/{token}?do=none")
db.refresh(site)
ok("Don't show a price: one tap", "No price on this listing" in r.text and site.price_mode == "none" and site.price_cents is None)
ok("then a price found online is never shown", ls.apply_price_readings(db, site, {"zillow": 82500000}) == "agent_chose_no_price")
site.price_token_at = datetime.now(timezone.utc) - timedelta(days=8)
db.commit()
ok("the links stop after 7 days", "expired" in client.get(f"/api/public/price/{token}?do=set").text)

# ---------------------------------------------------------------- 4. states
print("Pending, sold, ended")
boost.listing_status = "pending"
db.commit()
t = client.get("/l/1248-oakridge-drive").text
ok("pending: the banner, the chip, Ask about similar homes", "This home is under contract" in t and ">Pending<" in t
   and "Ask about similar homes" in t and "Schedule a showing" not in t)
ok("pending keeps the agent's contact and the form", "Send to Morgan" in t and 'href="tel:' in t)
boost.listing_status = "sold"
db.commit()
t = client.get("/l/1248-oakridge-drive").text
ok("sold: its own banner", "This home has sold" in t and "under contract" not in t)
boost.listing_status = None
boost.go_live_date = (datetime.now(timezone.utc) - timedelta(days=60)).strftime("%Y-%m-%d")
db.commit()
t = client.get("/l/1248-oakridge-drive").text
ok("30 days after the end: the agent card and form only", "This home is no longer available." in t
   and "The heart of the house" not in t and "Send to Morgan" in t)
boost.go_live_date = (datetime.now(timezone.utc) - timedelta(days=2)).strftime("%Y-%m-%d")
db.commit()

# ---------------------------------------------------------------- 1b. a new round keeps the link
print("Run it until it sells keeps the link")
nxt = Boost(user_id=agent.id, address=boost.address, parent_boost_id=boost.id, plan=plan, stage="PENDING")
db.add(nxt)
db.commit()
for i in range(1, 4):
    db.add(Asset(user_id=agent.id, boost_id=nxt.id, filename=f"p{i}.jpg", url=f"/uploads/p{i}.jpg", kind="photo",
                 room="Kitchen", data=jpeg(), content_type="image/jpeg"))
db.commit()
ok("an unpaid next round doesn't take the page", ls.site_for(db, nxt) is None)


async def writer2(b, kit, photos):
    w = await writer(b, kit, photos)
    w["headline"] = "Round two: the view, again"
    return w
held = asyncio.run(ls.build(db, nxt, writer=writer2, share=False))
ok("built ahead, the running round keeps the page", held.boost_id == boost.id
   and "Round two" not in client.get("/l/1248-oakridge-drive").text)
nxt.paid_at = datetime.now(timezone.utc)
db.commit()
again = ls.promote(db, nxt)
ok("paid: the next round takes over the same site and slug", again is not None and again.slug == "1248-oakridge-drive"
   and again.boost_id == nxt.id)
ok("with the new round's story", "Round two" in client.get("/l/1248-oakridge-drive").text)
again.boost_id = boost.id
db.commit()

# ---------------------------------------------------------------- 7. links
print("Links")
from app.services import post_rules  # noqa: E402
from app.services.ad_build import with_utm  # noqa: E402
p = Post(id=55, caption="Golden hour on the patio.", hashtags="#austinhomes #hillcountry", hashtags_fb="#austinhomes")
fb, ig = post_rules.messages(p, ls.tracked_url(site, "post-55"))
ok("Facebook carries the tagged website link", "See the home: https://homes.resmara.com/1248-oakridge-drive?" in fb
   and "utm_content=post-55" in fb)
ok("Instagram never does", "homes.resmara.com" not in ig)
ok("the ad is tagged as the ad", "utm_content=ad" in with_utm("https://homes.resmara.com/x", "1248 Oakridge Drive"))

# ---------------------------------------------------------------- daily check
print("Daily check")
db.query(Asset).filter(Asset.filename == "p2.jpg").delete()
db.commit()
r = client.post("/api/admin/sites/check", headers={"X-Resmara-Token": "clock-token"}).json()
ok("a missing photo is flagged", any(f["slug"] == "1248-oakridge-drive" for f in r["flagged"]), r)
ok("the check needs the clock's token", client.post("/api/admin/sites/check").status_code in (403, 503))

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL LISTING SITE TESTS PASSED")
