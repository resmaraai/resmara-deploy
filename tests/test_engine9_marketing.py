"""Engine 9 · Marketing: the counting rules, the three channels, and the pages that show them.

Why this file exists: PR #31 shipped this engine's design and no code, so the tabs did not exist.
This is the test that holds what the brain doc actually promised:

  * a sign-up is stamped once, with the channel it came from, and never rewritten;
  * each paying agent counts once, for the last thing that got them to buy - so the channel rows
    add up to the total and nothing is counted twice;
  * money back is every campaign that agent bought in the period, at what they paid;
  * an unset cost is unknown, not zero, and a channel nobody priced is "can't say yet" rather
    than "Working";
  * Mailchimp, Meta and Google Analytics that are not connected say so and never invent a number,
    while the numbers we own (sign-ups, paying agents, money back) still show.

All HTTP is faked here - these tests never leave the machine.

Run:  cd /Users/dan/resmara && venv/bin/python tests/test_engine9_marketing.py
"""

import os
import sys
import tempfile
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-engine9-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@resmara.com"
for name in ("MAILCHIMP_API_KEY", "MAILCHIMP_AUDIENCE_ID", "MAILCHIMP_MONTHLY_USD",
             "MARKETING_HOSTING_MONTHLY_USD", "META_AD_ACCOUNT_ID", "META_SYSTEM_TOKEN",
             "GA4_PROPERTY_ID", "CLARITY_PROJECT_ID"):
    os.environ.pop(name, None)

from fastapi.testclient import TestClient                                      # noqa: E402

from app.api import marketing as M                                             # noqa: E402
from app.core.security import get_password_hash                                # noqa: E402
from app.db.session import Base, Boost, SessionLocal, User, engine             # noqa: E402
from app.main import app                                                       # noqa: E402
from app.services import attribution, mailchimp                                # noqa: E402

checks = 0
failures = 0


def ok(name, cond, extra: object = ""):
    global checks, failures
    checks += 1
    if cond:
        print(f"  PASS  {name}")
    else:
        failures += 1
        print(f"  FAIL  {name}" + (f"  ({extra})" if extra else ""))


def usd(value):
    return f"${value:,.2f}" if isinstance(value, (int, float)) else value


Base.metadata.create_all(bind=engine)

# The two network calls the Website page makes are not this engine's business and must not make a
# test hang: both are replaced with the honest "not connected" answer.
M._tag_checks = lambda base: [{"name": "Site answers", "status": "ok", "detail": "HTTP 200 (faked)"}]
M._pagespeed = lambda url, strategy: (None, "PageSpeed Insights is not called in this test")

print("\n[where a sign-up came from]")
channel, detail = attribution.classify({"utm_source": "facebook", "utm_medium": "paid",
                                        "utm_campaign": "spring", "garbage": "dropped"})
ok("a paid Meta link is an ad", channel == "ad", channel)
ok("the detail keeps only what we understand", "utm_campaign" in detail and "garbage" not in detail, detail)
ok("an fbclid alone is an ad", attribution.classify({"fbclid": "abc"})[0] == "ad")
ok("a Mailchimp click is email",
   attribution.classify({"utm_source": "mailchimp", "utm_medium": "email"})[0] == "email")
ok("organic Google is the website on its own",
   attribution.classify({"utm_source": "google", "utm_medium": "organic"})[0] == "website")
ok("no tags at all is still the website", attribution.classify(None)[0] == "website")

print("\n[a stamp is written once and never rewritten]")
db = SessionLocal()
person = User(email="first.agent@gmail.com", name="Agent", hashed_password=get_password_hash("pw-123456"))
db.add(person)
db.flush()
attribution.stamp_signup(db, person, {"utm_medium": "paid", "utm_source": "facebook"})
first_stamp = person.signup_source
attribution.stamp_signup(db, person, {"utm_medium": "email", "utm_source": "mailchimp"})
ok("the first stamp is the ad", first_stamp == "ad", first_stamp)
ok("a second call does not change it", person.signup_source == "ad", person.signup_source)
db.commit()

print("\n[each paying agent counts once, for the last thing that got them to buy]")
now = datetime.utcnow()
agents = []
for email, source in (("ad.agent@gmail.com", "ad"), ("email.agent@gmail.com", "email"),
                      ("web.agent@gmail.com", "website")):
    u = User(email=email, name=email.split("@")[0], hashed_password=get_password_hash("pw-123456"),
             created_at=now - timedelta(days=3), signup_source=source,
             signup_source_detail={"utm_campaign": "120210000001"} if source == "ad" else {})
    db.add(u)
    db.flush()
    agents.append(u)

# The ad agent buys twice (first campaign and a re-run): one paying agent, both campaigns count.
for index, (agent, days, round_no) in enumerate(((agents[0], 2, 0), (agents[0], 1, 1),
                                                 (agents[1], 1, 0), (agents[2], 1, 0))):
    db.add(Boost(user_id=agent.id, address=f"{index} Test Street", repeat_round=round_no,
                 paid_at=now - timedelta(days=days), paid_amount_cents=4900 if round_no == 0 else 3900,
                 paid_source=agent.signup_source))
db.commit()

# An email click inside the 7-day window out-ranks the sign-up stamp: that agent is Email's.
mailchimp.clicked_since = lambda email, since: email == "ad.agent@gmail.com"
db2 = SessionLocal()
boost = db2.query(Boost).filter(Boost.user_id == agents[0].id, Boost.repeat_round == 1).first()
boost.paid_source = None
channel, because = attribution.credit_channel(db2, db2.get(User, agents[0].id), now)
ok("a click in the window wins the credit", channel == "email", (channel, because))

print("\n[the Marketing page: channel rows that add up]")
admin = User(email="owner@resmara.com", name="Owner", hashed_password=get_password_hash("pw-123456"),
             is_admin=True, team_super_admin=True)
db.add(admin)
db.commit()
db.close()

client = TestClient(app)
token = client.post("/api/auth/login", data={"username": "owner@resmara.com",
                                            "password": "pw-123456"}).json().get("access_token")
auth = {"Authorization": f"Bearer {token}"}
ok("the operator signs in", bool(token))

body = client.get("/api/admin/marketing", headers=auth).json()
channels = {c["key"]: c for c in body.get("channels", [])}
ok("three channel rows", set(channels) == {"ad", "email", "website"}, list(channels))
ok("the rows add up to the total",
   sum(c["paying"] for c in channels.values()) == body["total"]["paying"],
   (sum(c["paying"] for c in channels.values()), body["total"]["paying"]))
ok("the ad agent counts once, not twice", channels["ad"]["paying"] == 1, channels["ad"]["paying"])
ok("money back counts both of their campaigns", channels["ad"]["money_back_usd"] == 88.0,
   channels["ad"]["money_back_usd"])
ok("money back adds up to the total",
   round(sum(c["money_back_usd"] for c in channels.values()), 2) == body["total"]["money_back_usd"])
ok("a channel with no paying agent is not judged", channels["email"]["verdict"] is None,
   channels["email"]["verdict"])
ok("nothing is invented while Meta is not connected",
   body["spend_usd"] is None and body["impressions"] is None and body["clicks"] is None)
ok("the page says what is missing", bool(body.get("unavailable")))
ok("the counting rules are on the page", len(body.get("rules", [])) == 5, len(body.get("rules", [])))

print("\n[cost: typed in once, spread to the day, and never assumed]")
costs = client.get("/api/admin/marketing-costs", headers=auth).json()
ok("no cost is entered yet", costs["mailchimp_monthly_usd"] is None and costs["hosting_monthly_usd"] is None)
saved = client.put("/api/admin/marketing-costs", headers=auth,
                   json={"mailchimp_monthly_usd": 20, "hosting_monthly_usd": 7}).json()
ok("the two monthly bills save", saved["mailchimp_monthly_usd"] == 20 and saved["hosting_monthly_usd"] == 7)
body = client.get("/api/admin/marketing", headers=auth).json()
email_row = {c["key"]: c for c in body["channels"]}["email"]
ok("the plan is spread across the window", email_row["cost_usd"] == 20.0, email_row["cost_usd"])
website_row = {c["key"]: c for c in body["channels"]}["website"]
ok("hosting is spread across the window", website_row["cost_usd"] == 7.0, website_row["cost_usd"])
ok("a priced channel with money back is Working", website_row["verdict"] is True,
   (website_row["cost_usd"], website_row["money_back_usd"]))
ok("the rule itself: $1 back on $1 is not working yet", M._verdict(10, 10)["verdict"] is False)
ok("the rule itself: $2 back on $1 is working", M._verdict(10, 20)["verdict"] is True)
ok("the rule itself: an unknown cost is not judged", M._verdict(None, 20)["verdict"] is None)
blank = client.put("/api/admin/marketing-costs", headers=auth,
                   json={"hosting_monthly_usd": ""}).json()
ok("a blank field is not known, not zero", blank["hosting_monthly_usd"] is None, blank)
bad = client.put("/api/admin/marketing-costs", headers=auth, json={"hosting_monthly_usd": "lots"})
ok("a word is refused", bad.status_code == 400, bad.status_code)

print("\n[Email campaigns: an honest page with no Mailchimp key]")
em = client.get("/api/admin/email-campaigns", headers=auth)
ok("the page answers without a key", em.status_code == 200, em.status_code)
em = em.json()
ok("it says it is not connected", em["connected"] is False)
ok("it names the missing variable", "MAILCHIMP_API_KEY" in em["why"], em["why"])
ok("the three series are listed", [s["key"] for s in em["series"]] == ["welcome", "tips", "past"],
   [s["key"] for s in em["series"]])
ok("every email in them is listed", sum(len(s["emails"]) for s in em["series"]) == 9)
ok("no email number is invented", all(e["sent"] is None for s in em["series"] for e in s["emails"]))
csv = client.get("/api/admin/email-campaigns/export.csv", headers=auth)
ok("the CSV export works from our own database", csv.status_code == 200, csv.status_code)
ok("it has a header and the real agents", "email,name,signed_up" in csv.text and
   "ad.agent@gmail.com" in csv.text, csv.text[:200])

print("\n[consent: the agent's own switch, and the CSV keeps test accounts out]")
db = SessionLocal()
test_person = User(email="smoke1234567@example.com", name="test", hashed_password="x", is_test=True)
closed = User(email="closed@example.com", name="Closed", hashed_password="x", is_active=False)
db.add_all([test_person, closed])
db.commit()
db.close()
csv = client.get("/api/admin/email-campaigns/export.csv", headers=auth).text
ok("a test account is left out", "smoke1234567@example.com" not in csv)
ok("a closed account is left out", "closed@example.com" not in csv)

print("\n[Digital ads: our own numbers survive a missing ad account]")
ads = client.get("/api/admin/digital-ads", headers=auth)
ok("the page answers without Meta", ads.status_code == 200, ads.status_code)
ads = ads.json()
ok("it says the account is not connected", ads["connected"] is False)
ok("no campaign is invented", ads["campaigns"] == [])
ok("the paying agents we do own still show", ads["total"]["paying"] >= 1, ads["total"])
ok("the campaign list names the missing variable",
   any("META_AD_ACCOUNT_ID" in (u.get("reason") or "") for u in ads["unavailable"]), ads["unavailable"])
blocked = client.post("/api/admin/digital-ads/123456/status", headers=auth, json={"run": False})
ok("pausing without an account is refused, not pretended", blocked.status_code == 400, blocked.status_code)

print("\n[Website: who came, and where they're counted]")
site = client.get("/api/admin/website", headers=auth).json()
split = {row["key"]: row for row in site.get("channel_split", [])}
ok("all three channels are on the split", set(split) == {"ad", "email", "website"}, list(split))
ok("sign-ups are real even with no analytics", sum(r["signups"] for r in split.values()) >= 3,
   {k: v["signups"] for k, v in split.items()})
ok("visitors are not invented without Google Analytics",
   all(r["visitors"] is None for r in split.values()))
ok("the people who came on their own are counted",
   site.get("came_on_their_own") is not None and site["came_on_their_own"] >= 1, site.get("came_on_their_own"))

print("\n[the tabs are actually in the Team room]")
page = client.get("/admin.html").text
for label, anchor in (("Marketing", 'data-go="marketing"'),
                      ("Website", 'data-go="website"'),
                      ("Email campaigns", 'data-go="email"'),
                      ("Digital ads", 'data-go="digitalads"')):
    ok(f"the {label} tab exists and paints", anchor in page and
       f'id="sec-{anchor.split(chr(34))[1]}"' in page, anchor)
ok("the marketing tab ships its channel table", 'id="mkChannels"' in page)
ok("the email tab ships its series list", 'id="emSeries"' in page)
ok("the ads tab ships its campaign list", 'id="adsList"' in page)
ok("the two costs are editable in Settings", 'id="mcMailchimp"' in page and 'id="mcHosting"' in page)

print(f"\n{checks} checks, {failures} failed.")
if failures:
    sys.exit(1)
print("ENGINE 9 PASSED")
