"""Social leads (Post Engine §10.4) against a real Graph-shaped server.

What this proves, in the customer's terms:

  * comments on a campaign's Instagram post, Facebook post and ad are actually read;
  * a comment that asks about the home becomes a lead, and "Love this!" does not;
  * the agent is emailed once per lead, and the row records whether the email really went;
  * running the scan again never duplicates a lead, and never resurrects one the agent
    removed;
  * the panel's routes work: list, add by hand, tick off, remove - and another account
    cannot see any of it;
  * with Meta not connected or a post refused, the campaign says so instead of showing an
    empty list as if nobody was interested.

Run:
    cd /Users/dan/resmara && PYTHONPATH=. venv/bin/python tests/test_social_leads.py
"""
import http.server
import json as _json
import os
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-leads-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
os.environ["RESMARA_PUBLISH_TOKEN"] = "leads-token"
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"
os.environ["RESMARA_SIGNUP_EMAILS"] = ""
for _key in ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "MAIL_FROM",
             "RESMARA_ENGINE_BASE_URL", "RESMARA_ENGINE_API_KEY", "OPENAI_API_KEY",
             "RESMARA_SIMULATE"):
    os.environ.pop(_key, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.db.session import Base, engine, SessionLocal, Ad, AdAccount, Boost, Lead, Post, User  # noqa: E402
from app.db.migrate import migrate  # noqa: E402
from app.services import leads as leads_service  # noqa: E402
from app.services import mail  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()
client = TestClient(app)


# --------------------------------------------------------------------------- mock Graph
class MockGraph:
    def __init__(self):
        self.log = []
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):  # noqa: N802
                parsed = urlparse(self.path)
                outer.log.append({"path": parsed.path, "query": parsed.query})
                status, payload = outer.answer(parsed.path)
                data = _json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        self.url = f"http://127.0.0.1:{self._httpd.server_address[1]}"

    def answer(self, path):
        if path.endswith("/media_ig1/comments"):
            return 200, {"data": [
                {"id": "c1", "text": "Is this still available? We'd love to see it this weekend.",
                 "username": "sarah.m", "timestamp": "2026-11-17T18:02:00+0000",
                 "permalink": "https://instagram.com/p/abc/c/1"},
                {"id": "c2", "text": "Love this! 🔥", "username": "james.o",
                 "timestamp": "2026-11-17T19:00:00+0000",
                 "permalink": "https://instagram.com/p/abc/c/2"},
                {"id": "c3", "text": "Not interested, thanks", "username": "meh",
                 "timestamp": "2026-11-17T19:30:00+0000"},
            ]}
        if path.endswith("/PAGE1_fbpost1/comments"):
            return 200, {"data": [
                {"id": "f1", "message": "What's the asking price and is the pool heated?",
                 "from": {"id": "77", "name": "Priya Shah"},
                 "created_time": "2026-11-18T02:10:00+0000",
                 "permalink_url": "https://facebook.com/post/1?comment=1"},
                {"id": "f2", "message": "Sending this to my husband 😍",
                 "from": {"id": "78", "name": "Megan Cole"},
                 "created_time": "2026-11-18T03:10:00+0000"},
            ]}
        if path.endswith("/adcreative1/comments"):
            return 400, {"error": {"message": "(#200) Requires pages_manage_ads permission"}}
        return 404, {"error": {"message": "no route in the mock"}}

    def stop(self):
        self._httpd.shutdown()


MOCK = MockGraph()
settings.GRAPH_API_BASE = MOCK.url

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- accounts
client.post("/api/auth/register", json={"terms_accepted": True, "email": "agent@example.com", "password": "long enough",
                                       "name": "Dana Agent", "invite_code": "beta-code-123"})
client.post("/api/auth/register", json={"terms_accepted": True, "email": "owner@example.com", "password": "long enough",
                                       "name": "Owner"})
client.post("/api/auth/register", json={"terms_accepted": True, "email": "other@example.com", "password": "long enough",
                                       "name": "Other", "invite_code": "beta-code-123"})


def login(email):
    token = client.post("/api/auth/login", data={"username": email,
                                                "password": "long enough"}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


agent = login("agent@example.com")
other = login("other@example.com")


def connect_meta(email):
    """The + Campaign gate: an account has to be Meta-connected first (item 8)."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        user.meta_connected_at = datetime.now(timezone.utc)
        db.commit()
    finally:
        db.close()


connect_meta("agent@example.com")

boost = client.post("/api/boosts", headers=agent, json={
    "address": "1248 Oakridge Drive", "tier": "bap_shoot_499", "go_live_date": "2026-11-16",
    "campaign_days": 14, "ad_budget_usd": 50.0, "property_facts": "4BR/3BA"}).json()
BOOST_ID = boost["id"]


def attach_live():
    """A launched campaign: token, page, two published posts, a live ad."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == "agent@example.com").first()
        row = db.query(Boost).filter(Boost.id == BOOST_ID).first()
        account = AdAccount(user_id=user.id, platform="meta", advertiser_id="act_leads",
                            account_name="Leads test", access_token="real-token",
                            page_id="PAGE1", ig_user_id="IG1", is_active=True)
        db.add(account)
        db.flush()
        row.ad_account_id = account.id
        row.launched_at = datetime.now(timezone.utc) - timedelta(days=2)
        # DEPLOYED is what launch.py actually writes; LIVE is only ever named by metrics.
        row.stage = "DEPLOYED"
        db.add(Post(boost_id=row.id, day=1, slot=1, title="Where summer actually happens",
                    caption="x", ig_media_id="media_ig1", fb_post_id="fbpost1",
                    publish_status="posted", client_status="approved"))
        row2 = Ad(boost_id=row.id, kind="photo", status="live", meta_creative_id="adcreative1",
                  headline="Just listed")
        db.add(row2)
        db.commit()
    finally:
        db.close()


def leads_in_db(boost_id=BOOST_ID):
    db = SessionLocal()
    try:
        return db.query(Lead).filter(Lead.boost_id == boost_id).all()
    finally:
        db.close()


attach_live()

# --------------------------------------------------------------------------- the scan
sent = []


def fake_send(to, subject, body):
    sent.append((to, subject, body))
    return True


mail.send_email = fake_send

before = len(MOCK.log)
r = client.post(f"/api/boosts/{BOOST_ID}/leads/scan", headers=agent)
scan = r.json()
check("a scan answers 200", r.status_code == 200, r.text[:300])
check("  ...and asks Meta for comments", len(MOCK.log) > before,
      f"{len(MOCK.log) - before} request(s)")
check("  ...reading the IG post, the FB post and the ad", scan.get("targets") == 3, str(scan))
check("  ...getting seven comments back", scan.get("comments") == 5, str(scan))
check("  a refused ad thread is reported, not swallowed",
      any("adcreative1" in e or "pages_manage_ads" in e for e in scan.get("errors", [])),
      str(scan.get("errors")))

rows = leads_in_db()
texts = sorted((row.text or "") for row in rows)
check("two comments became leads", scan.get("leads") == 2, f"{scan.get('leads')} -> {texts}")
check("  ...the availability question", any("still available" in t for t in texts), str(texts))
check("  ...the price question", any("asking price" in t for t in texts), str(texts))
check("  'Love this!' is not a lead", not any("Love this" in t for t in texts), str(texts))
check("  'Not interested' is not a lead", not any("Not interested" in t for t in texts), str(texts))
check("  a judgement is recorded with each lead",
      all(row.classified_by in ("keyword", "ai") and row.confidence for row in rows),
      str([(r.classified_by, r.confidence) for r in rows]))
check("  the platform and the post are kept",
      {row.platform for row in rows} == {"instagram", "facebook"}, str([r.platform for r in rows]))
check("  the channel reads the way the panel prints it",
      {row.channel for row in rows} == {"Instagram", "Facebook"}, str([r.channel for r in rows]))
check("  the comment's own permalink is kept",
      any((row.permalink or "").startswith("https://instagram.com") for row in rows),
      str([r.permalink for r in rows]))
check("the agent was emailed once per lead", scan.get("emailed") == 2 and len(sent) == 2,
      f"emailed={scan.get('emailed')} sent={len(sent)}")
check("  ...to the agent's own address", all(to == "agent@example.com" for to, _, _ in sent),
      str([s[0] for s in sent]))
bodies = " ".join(b for _, _, b in sent)
check("  ...with the home and the person in the subject",
      all("1248 Oakridge Drive" in s[1] for s in sent), str([s[1] for s in sent]))
check("  ...and the exact words they wrote",
      "still available" in bodies and "asking price" in bodies, bodies[:200])
check("the send is recorded on the row",
      all(row.notified_at is not None for row in rows), str([r.notified_at for r in rows]))

db = SessionLocal()
fresh_boost = db.query(Boost).filter(Boost.id == BOOST_ID).first()
check("the campaign records when it last looked", fresh_boost.leads_checked_at is not None)
check("  ...and what happened", bool(fresh_boost.leads_scan_note), fresh_boost.leads_scan_note)
db.close()

# --------------------------------------------------------------------------- idempotent
sent.clear()
r2 = client.post(f"/api/boosts/{BOOST_ID}/leads/scan", headers=agent).json()
check("a second scan adds nothing", r2.get("leads") == 0, str(r2))
check("  ...because both comments are already known", r2.get("skipped", 0) >= 2, str(r2))
check("  ...and sends no second email", len(sent) == 0 and r2.get("emailed") == 0, str(r2))
check("the lead count in the database did not change", len(leads_in_db()) == 2,
      str(len(leads_in_db())))

# --------------------------------------------------------------------------- email honesty
sent.clear()
mail.send_email = lambda to, subject, body: False  # a provider that refuses


def add_a_lead_by_hand(name, text, where="Instagram", notify=False):
    return client.post(f"/api/boosts/{BOOST_ID}/leads", headers=agent,
                       json={"name": name, "text": text, "where": where, "notify": notify})


r3 = add_a_lead_by_hand("Test Person", "Can I book a showing?")
check("a hand-added lead is accepted", r3.status_code == 201, r3.text[:200])
check("  ...and stored on the server", r3.json()["id"] in [row.id for row in leads_in_db()])
r4 = add_a_lead_by_hand("Mail Fail", "Please call me about this house.", notify=True)
check("a failed alert is honest", r4.status_code == 201 and r4.json()["notified_at"] is None,
      r4.text[:300])
check("  ...and says why it did not go", bool(r4.json()["email_error"]), r4.text[:300])
mail.send_email = fake_send

# The catch-up: a lead that could not be emailed is tried again on the next scan, so a mail
# outage delays the alert instead of losing it.
sent.clear()
client.post(f"/api/boosts/{BOOST_ID}/leads/scan", headers=agent)
retried = [row for row in leads_in_db() if row.author_name == "Mail Fail"][0]
check("an un-emailed lead is emailed on the next scan", retried.notified_at is not None,
      str((retried.notified_at, retried.email_error)))
check("  ...and the message is the lead's own", any("Mail Fail" in s[1] for s in sent),
      str([s[1] for s in sent]))

# --------------------------------------------------------------------------- panel routes
listing = client.get(f"/api/boosts/{BOOST_ID}/leads", headers=agent).json()
check("the panel gets its leads", len(listing["leads"]) == 4, str(len(listing["leads"])))
check("  ...newest first", listing["leads"][0]["author_name"] == "Mail Fail",
      listing["leads"][0]["author_name"])
check("  ...with the open count the badge shows", listing["open"] == 4, str(listing["open"]))
check("  ...and when comments were last read", listing["scan"]["checked_at"] is not None,
      str(listing["scan"]))

first_id = listing["leads"][-1]["id"]
tick = client.patch(f"/api/leads/{first_id}", headers=agent, json={"status": "handled"})
check("a lead can be ticked off", tick.status_code == 200 and tick.json()["status"] == "handled",
      tick.text[:200])
check("  ...and stops counting as new",
      client.get(f"/api/boosts/{BOOST_ID}/leads", headers=agent).json()["open"] == 3)
bad = client.patch(f"/api/leads/{first_id}", headers=agent, json={"status": "banana"})
check("an unknown status is refused", bad.status_code == 422, str(bad.status_code))

removed = client.delete(f"/api/leads/{listing['leads'][1]['id']}", headers=agent)
check("a comment can be marked not-a-lead", removed.status_code == 200 and
      removed.json()["status"] == "removed", removed.text[:200])
check("  ...and disappears from the panel",
      len(client.get(f"/api/boosts/{BOOST_ID}/leads", headers=agent).json()["leads"]) == 3)

# The removed comment must not come back on the next scan.
client.post(f"/api/boosts/{BOOST_ID}/leads/scan", headers=agent)
statuses = [row.status for row in leads_in_db() if (row.text or "").startswith("Love this")]
check("a scan does not resurrect a removed comment", statuses == [], str(statuses))

check("another account cannot list these leads",
      client.get(f"/api/boosts/{BOOST_ID}/leads", headers=other).status_code == 404)
check("another account cannot tick one off",
      client.patch(f"/api/leads/{first_id}", headers=other,
                   json={"status": "handled"}).status_code == 404)
check("another account cannot remove one",
      client.delete(f"/api/leads/{first_id}", headers=other).status_code == 404)
check("another account cannot trigger a scan",
      client.post(f"/api/boosts/{BOOST_ID}/leads/scan", headers=other).status_code == 404)

cards = client.get("/api/boosts", headers=agent).json()
mine = [c for c in cards if c["id"] == BOOST_ID][0]
check("the campaign card carries the badge count", mine["new_leads"] == 2, str(mine["new_leads"]))

# --------------------------------------------------------------------------- honest empty
# A campaign whose account has never connected Meta must say that, not show an empty list.
connect_meta("other@example.com")
client.post("/api/boosts", headers=other, json={
    "address": "76 Willow Lane", "tier": "bap_shoot_499", "go_live_date": "2026-11-16",
    "campaign_days": 14, "ad_budget_usd": 50.0, "property_facts": "3BR/2BA"})
nodata_id = [c for c in client.get("/api/boosts", headers=other).json()
             if c["address"] == "76 Willow Lane"][0]["id"]
nodata = client.post(f"/api/boosts/{nodata_id}/leads/scan", headers=other).json()
check("a campaign with no Meta connection says so", nodata["ok"] is False and nodata["errors"],
      str(nodata))
check("  ...and writes the reason to the campaign",
      "not connected" in (client.get(f"/api/boosts/{nodata_id}/leads", headers=other)
                          .json()["scan"]["note"] or "").lower())

# --------------------------------------------------------------------------- the scheduler
db = SessionLocal()
try:
    summary = __import__("asyncio").run(leads_service.scan_all(db))
finally:
    db.close()
check("the scheduler scans live campaigns only", summary["campaigns"] == 1, str(summary))
check("  ...reports a measured zero", summary["leads"] == 0, str(summary))
check("  ...and is honest that the ad thread was refused", summary["ok"] is False, str(summary))

sched = client.post("/api/admin/leads/scan", headers={"X-Resmara-Token": "leads-token"})
check("the scheduler entrypoint answers its token", sched.status_code == 200, sched.text[:200])
check("  ...but not a wrong one",
      client.post("/api/admin/leads/scan", headers={"X-Resmara-Token": "nope"}).status_code == 403)

# --------------------------------------------------------------------------- engine path
# With the content engine configured the model judges; the keyword ladder is the floor under
# it. Both answers are exercised here so a broken engine reply cannot silently invent leads.
import asyncio  # noqa: E402
from app.services import llm  # noqa: E402

llm.llm_available = lambda: True


async def _engine_ok(system, user, **kwargs):
    return {"verdicts": [{"i": 0, "lead": True, "confidence": 0.92, "why": "asks the price"},
                         {"i": 1, "lead": False, "confidence": 0.15, "why": "a compliment"},
                         {"i": 2, "lead": True, "confidence": 0.2, "why": "maybe"}]}


llm.chat_json = _engine_ok
verdicts = asyncio.run(leads_service.classify(["What's the price?", "Love this!", "Nice sky"]))
check("the engine's own verdicts are used", [v["lead"] for v in verdicts] == [True, False, True],
      str(verdicts))
check("  ...and the judgement says it was the engine", {v["by"] for v in verdicts} == {"ai"},
      str(verdicts))


async def _engine_garbage(system, user, **kwargs):
    return {"verdicts": "not a list"}


llm.chat_json = _engine_garbage
verdicts = asyncio.run(leads_service.classify(["Is this still available?", "Love this!"]))
check("an unusable engine answer falls back to keywords",
      [v["lead"] for v in verdicts] == [True, False] and {v["by"] for v in verdicts} == {"keyword"},
      str(verdicts))

MOCK.stop()
print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL SOCIAL LEADS TESTS PASSED")
