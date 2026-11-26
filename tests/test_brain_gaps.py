"""The gaps the 25 Nov line-by-line check of every brain found, each proven closed.

Engine 1: the Facebook door keeps the visit's tags and honours the invite code; the day-3 email names
the open setup item; the Team room counts where agents are stuck; unknown Meta errors are filed and
the Weekly Meta review saves, and Approve puts a task on Dan's list.
Engine 2: facts carry confirmed / found once / not found.
Engine 3: the home's file, with "please check" decided in code and handed to the post writer.
Engine 4: the hook library, the rulebook's lessons and banned hashtags.
Engine 6: the agent report's hooks, numbers, summary and recommendations.
Engine 8: a validated price change leads the next round, never with a number.
Engine 11: Ask Resmara reads the guide and the agent's account; visitors get product answers; limits.
"""
import asyncio
import os
import tempfile
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-gaps-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
os.environ["SECRET_KEY"] = "test-secret-key-for-brain-gaps-0000000000"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.db.session import (Ad, Base, Boost, BuildroomTask, Event, ListingSite, MetaConnection,  # noqa: E402
                            SessionLocal, User, engine)
from app.main import app  # noqa: E402
from app.services import (attribution, brand_investigator, content_engine, learning_library, listing_site,  # noqa: E402
                          llm, mail, meta_engine, onboarding_emails, post_rules)
from app.api import content as content_api, help as help_api  # noqa: E402

Base.metadata.create_all(bind=engine)
mail.send_email = lambda *a, **k: True
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({str(extra)[:300]})"))
    if not cond:
        failures += 1


db = SessionLocal()
agent = User(email="morgan@example.com", hashed_password="x", name="Morgan Ellis")
admin = User(email="owner@example.com", hashed_password="x", name="Adam French", is_admin=True)
db.add_all([agent, admin])
db.commit()
H = {"Authorization": "Bearer " + create_access_token({"sub": agent.email})}
A = {"Authorization": "Bearer " + create_access_token({"sub": admin.email})}
client = TestClient(app)

print("[Engine 9 via Engine 1: the Facebook door keeps where the visit came from]")
channel, detail = attribution.classify({"utm_source": "facebook", "utm_medium": "paid", "fbclid": "abc"})
ok("a visit from a Meta ad is credited to Digital ads", channel == "ad", channel)
nonce_ev = Event(event_type="facebook_signup_context", payload={"n": "nonce-1", "source": {"utm_medium": "email",
                                                                                          "utm_source": "mailchimp"},
                                                              "invite": "BETA"})
db.add(nonce_ev)
db.commit()
from app.api.facebook_login import _signup_context  # noqa: E402
ctx = _signup_context(db, "nonce-1")
ok("the tags saved at the start are found again at Facebook's return", ctx.get("source", {}).get("utm_source") == "mailchimp"
   and ctx.get("invite") == "BETA", ctx)
ok("  ...and that email visit is credited to Email campaigns", attribution.classify(ctx["source"])[0] == "email")

print("[Engine 1: the day-3 email names the open setup item]")
conn = MetaConnection(user_id=agent.id, fb_user_id="fb-1", page_id="p1", page_name="Morgan Ellis Homes",
                      issues=["ad_no_payment"], issue_log=[{"key": "ad_no_payment", "found_at": datetime.now(timezone.utc).isoformat(),
                                                         "fixed_at": None}],
                      capabilities={"fb_post": True, "ig_post": True, "ad": False, "campaigns_allowed": True})
agent.meta_connected_at = datetime.now(timezone.utc)
agent.created_at = datetime.now(timezone.utc) - timedelta(days=4)
agent.last_login = datetime.now(timezone.utc)
db.add(conn)
db.commit()
facts = onboarding_emails.account_facts(db, agent)
ok("the account facts carry the first open setup item", (facts.get("meta_todo") or {}).get("key") == "ad_no_payment", facts.get("meta_todo"))
ok("the day-3 email picks 'something's missing on Facebook'", onboarding_emails.situation(facts) == "meta_gap")
subject, body = onboarding_emails.compose("day3", agent, facts)
line = meta_engine.OUTCOMES["ad_no_payment"]["line"]
ok("  ...and names the exact thing, with where to fix it", line in body and "#accounts" in body, body[:400])

print("[Engine 1: the Team room counts where agents are stuck]")
r = client.get("/api/admin/connections/setup", headers=A)
items = r.json().get("items") if r.status_code == 200 else []
ok("each setup item with how many agents are stuck on it", any(i["key"] == "ad_no_payment" and i["agents"] == 1 for i in items), r.text[:300])

print("[Engine 1: unknown Meta errors and the Weekly Meta review]")
real_avail = llm.llm_available
llm.llm_available = lambda: False
filed = asyncio.run(meta_engine.file_unknown_error({"code": 999, "message": "Something new"}))
ok("an error the list doesn't know, with no AI to file it, is 'couldn't check right now'", filed == "meta_unreachable", filed)
meta_engine._log_unknown_error(db, agent, {"code": 999, "error_subcode": 7, "message": "Something new"}, "test", filed)
review = asyncio.run(meta_engine.weekly_review(db, send=False))
ok("the review saves last week's unknown errors", review.get("status") == "saved" and review["unknown_errors"]
   and review["unknown_errors"][0]["agents"] == 1, review)
again = asyncio.run(meta_engine.weekly_review(db, send=False))
ok("  ...once a week", again.get("status") == "already_done", again)
ev = db.query(Event).filter(Event.event_type == "meta_weekly_review").first()
payload = dict(ev.payload)
payload["suggestions"] = [{"kind": "better_wording", "key": "token_dead", "line": "Your Facebook login stopped.",
                           "why": "clearer", "example": "x", "agents": 3, "state": "waiting"}]
ev.payload = payload
db.commit()
r = client.post(f"/api/admin/meta/weekly-review/{ev.id}/decide", json={"index": 0, "approve": True}, headers=A)
ok("Approve marks it approved", r.status_code == 200 and r.json()["suggestions"][0]["state"] == "approved", r.text[:300])
ok("  ...and puts it on Dan's list in the Build room",
   db.query(BuildroomTask).filter(BuildroomTask.title.like("Meta situation%")).count() == 1)
llm.llm_available = real_avail

print("[Engine 2: how sure each fact is]")
kit = {"phone": "530-555-0100", "license": "02012345", "company": "", "factSources": {
    "phone": "https://morganellis.com", "license": "https://www2.dre.ca.gov/lookup"}}
conf = brand_investigator.fact_confidence(kit, {}, {"about": "Call 530-555-0100", "phone": "", "website": "", "address": ""})
ok("a license from the state lookup is confirmed", conf["license"] == "confirmed", conf)
ok("a phone on their website and their Page is confirmed", conf["phone"] == "confirmed", conf)
ok("a missing fact is 'not found'", conf["company"] == "not found", conf)

print("[Engine 3: the home's file]")
research = ("Bedrooms: 4 [Zillow]\nBathrooms: 3 [Zillow]\nLiving area: 2,980 sq ft [Realtor.com]\n"
            "Year built: 1998 [Public records]\nLot size: NOT FOUND")
hf = content_engine.home_file(research, "Beautiful 4 bed 3 bath home with 2,980 sq ft on a quiet street.", "https://x")
keys = {f["key"]: f for f in hf["facts"]}
ok("each fact keeps its source", keys["beds"]["source"] == "Zillow" and keys["sqft"]["source"] == "Realtor.com", hf)
ok("a fact on the pasted listing page needs no check", "beds" not in hf["please_check"] and "sqft" not in hf["please_check"], hf)
ok("a fact found only online is 'please check'", hf["please_check"] == ["year_built"], hf["please_check"])
note = content_engine.please_check_note(hf)
ok("  ...and the post writer is told never to state it as fact", "1998" in note and "Never state" in note, note)

print("[Engine 4: the hook library, the rulebook's lessons, banned hashtags]")
b1 = Boost(user_id=agent.id, address="1 Pool Way, Redding, CA")
db.add(b1)
db.commit()
db.add(Ad(boost_id=b1.id, kind="listing", versions=[
    {"kind": "hook", "n": 1, "hook": "Have you seen a pool like this?", "backedBy": "pool",
     "insights": {"impressions": 2000, "inline_link_clicks": 60}},
    {"kind": "hook", "n": 2, "hook": "Room for everything", "backedBy": "shop",
     "insights": {"impressions": 100, "inline_link_clicks": 9}}]))
db.add(Event(event_type="rulebook_lesson", payload={"reason": "Implies personal attributes", "before": "Are you ready?"}))
db.commit()
lib = learning_library.hook_library(db, city="redding")
ok("winning hooks are kept by what they're about and the market", lib and lib[0]["feature"] == "pool" and lib[0]["city"] == "redding", lib)
ok("  ...hooks with too few views don't count", all(r["hook"] != "Room for everything" for r in lib), lib)
ok("the next hooks are written with the library and Meta's past rejections",
   "pool like this" in learning_library.hook_library_note(db, "9 Lake Dr, Redding, CA")
   and "personal attributes" in learning_library.lessons_note(db).lower())
db.add(Event(event_type="platform_rules", payload={"banned_hashtags": ["sunbathing"], "checked": "2026-11-25"}))
db.commit()
learning_library._CACHE.clear()
ok("a banned hashtag from the monthly refresh is never used", not post_rules.allowed("#Sunbathing") and post_rules.allowed("#ReddingHomes"))

print("[Engine 6: the agent report]")
b1_ad = db.query(Ad).filter(Ad.boost_id == b1.id).first()
hooks = content_api.report_hooks(db, b1)
ok("each hook side by side", len(hooks) == 2 and hooks[0]["click_rate"] == 3.0, hooks)
ok("  ...the winner marked only once it has enough views", sum(1 for h in hooks if h["winner"]) == 0, hooks)
b1_ad.versions = [dict(v, insights={"impressions": 1000, "inline_link_clicks": 10 * (i + 1)}) for i, v in enumerate(b1_ad.versions)]
db.commit()
ok("  ...and with enough views, the best click rate wins",
   [h["label"] for h in content_api.report_hooks(db, b1) if h["winner"]] == ["Hook 2"])
organic = {"source": "meta", "summary": {"measured": 2, "reach": 900, "interactions": 40},
           "posts": [{"db_id": None, "day": 1, "reach": 600, "likes": 20, "comments": 3, "views": 800, "saved": 1},
                     {"db_id": None, "day": 3, "reach": 300, "likes": 10, "comments": 1, "views": 400, "saved": 0}]}
content_api._fill_post_numbers(organic, [], 7)
ok("totals come from the posts Meta measured", organic["summary"]["likes"] == 30 and organic["summary"]["views"] == 1200, organic["summary"])
ok("  ...with views per day of the campaign", organic["daily"][0] == 800 and organic["daily"][2] == 400, organic["daily"])
report = {"organic": organic, "paid": {"ok": True, "link_clicks": 55}, "leads": {"ad_comments": 1, "website_form": 1},
          "website": {"visits": 12, "url": "https://homes.resmara.com/1-pool-way"},
          "open_leads": [{"name": "Dana", "source": "web"}], "hooks": content_api.report_hooks(db, b1)}
summary, recs = content_api.report_reading(report, 7)
ok("the summary is the numbers in words", "900 people" in summary and "55 clicks" in summary and "2 leads" in summary, summary)
ok("recommendations name who to follow up with and the winning hook",
   any("Dana" in r for r in recs) and any("Hook 2" in r for r in recs), recs)

print("[Engine 8: a validated price change leads the next round]")
b2 = Boost(user_id=agent.id, address="5 Oak St, Redding, CA", plan={})
db.add(b2)
db.commit()
site = ListingSite(boost_id=b2.id, user_id=agent.id, slug="5-oak-st", content={}, price_cents=50000000)
db.add(site)
db.commit()
listing_site.apply_price_readings(db, site, {"zillow": 47500000}, send=False)
db.refresh(b2)
ok("one source with a new price isn't validated", not (b2.plan or {}).get("price_update"), b2.plan)
listing_site.apply_price_readings(db, site, {"zillow": 47000000, "redfin": 47000000}, send=False)
db.refresh(b2)
ok("the listing and another source agreeing is validated", (b2.plan or {}).get("price_update", {}).get("validated"), b2.plan)
b3 = Boost(user_id=agent.id, address="5 Oak St, Redding, CA", repeat_round=1)
db.add(b3)
db.commit()
note = content_engine.round_price_note(b3, db)
ok("the next round leads with 'Improved price'", "Improved price" in note, note)
ok("  ...never a number or the old price", "$" not in note and "470" not in note and "500" not in note, note)

print("[Engine 11: Ask Resmara]")
seen = {}


async def fake_chat_json(system, user, **kw):
    seen["user"] = user
    return {"answer": "Your Page Morgan Ellis Homes is connected.", "sure": True, "go": "accounts"}

llm.llm_available = lambda: True
llm.chat_json = fake_chat_json
llm.take_usage = lambda: {"prompt_tokens": 1000, "completion_tokens": 100}
r = client.post("/api/help/ask", json={"question": "Is my Facebook connected?", "page": "accounts"}, headers=H)
ok("a signed-in agent gets an answer", r.status_code == 200 and r.json().get("sure"), r.text[:200])
ok("  ...from their own account", "Morgan Ellis Homes" in seen.get("user", "") and "Setup item open" in seen["user"], seen.get("user", "")[:400])
ok("  ...and the guide", "Guide:" in seen["user"] and len(seen["user"].split("Guide:")[1]) > 500)
r = client.post("/api/help/ask", json={"question": "How much does a campaign cost?", "page": "home"})
ok("a signed-out visitor gets product answers", r.status_code == 200 and r.json().get("sure"), r.text[:200])
ok("  ...never account answers", "signed-out visitor" in seen["user"] and "Morgan" not in seen["user"])
os.environ["RESMARA_ASK_DAILY_USD"] = "0.0001"
r = client.post("/api/help/ask", json={"question": "Another question here"}, headers=H)
ok("past the daily cost cap the chat falls back to the library", r.json().get("reason") == "daily_cap", r.text[:200])
os.environ.pop("RESMARA_ASK_DAILY_USD", None)
for _ in range(25):
    r = client.post("/api/help/ask", json={"question": "Again and again"}, headers=H)
ok("20 questions an hour, then the library", r.json().get("reason") == "rate_limited", r.text[:200])

print(f"\n{checks - failures}/{checks} passed")
print("BRAIN GAPS PASSED" if not failures else "BRAIN GAPS FAILED")
raise SystemExit(1 if failures else 0)
