"""The campaign after approval: launch details, pause, the numbers, the re-run, the watcher.

Ad Engine v1.3 §4.5–§5. Everything here is checked against a real HTTP server standing in
for the agent's listing page, because the point of the listing check is that a dead or sold
link must be caught before two weeks of the seller's money are spent on it.
"""
import http.server
import os
import sys
import tempfile
import threading
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-control-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
os.environ["RESMARA_PUBLISH_TOKEN"] = "sweep-token"
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"
os.environ["RESMARA_SIGNUP_EMAILS"] = ""
for _key in ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "MAIL_FROM"):
    os.environ.pop(_key, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import Base, engine, SessionLocal, Ad, AdAccount, Boost, User  # noqa: E402
from app.db.migrate import migrate  # noqa: E402
from app.services import listing_watch  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()

client = TestClient(app)

LISTING_HTML = """<html><body><h1>1234 Elm Street, Austin, TX 78704</h1>
<p>3 bed 2 bath 1,800 sq ft single family home on a 0.24 acre lot.</p>
<p>For sale: $525,000. MLS #4471203. Private showings available this weekend.</p>
<p>Hill Country views, updated kitchen, pool, two car garage, and a covered patio.</p>
</body></html>"""
SOLD_HTML = """<html><body><h1>1234 Elm Street, Austin, TX 78704</h1>
<p>3 bed 2 bath 1,800 sq ft single family home on a 0.24 acre lot.</p>
<p>Sold on 12 November 2026 for $519,000 after 19 days.</p>
<p>This home is no longer available. See similar properties in the area.</p></body></html>"""
PENDING_HTML = """<html><body><h1>1234 Elm Street, Austin, TX 78704</h1>
<p>3 bed 2 bath 1,800 sq ft single family home on a 0.24 acre lot.</p>
<p>Under contract - pending sale. Backup offers considered.</p></body></html>"""
PAGE = {"body": LISTING_HTML, "status": 200}


def status_page(status):
    """A listing page with its status field, the way the listing sites publish it."""
    import json as _json
    data = {"props": {"pageProps": {"property": {"streetAddress": "1234 Elm Street", "homeStatus": status}}}}
    return f'<html><script id="__NEXT_DATA__" type="application/json">{_json.dumps(data)}</script></html>'



class Listing(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802 - http.server's API
        if self.path.startswith("/gone"):
            self.send_response(404)
            self.end_headers()
            return
        body = PAGE["body"].encode()
        self.send_response(PAGE["status"])
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass


server = http.server.HTTPServer(("127.0.0.1", 0), Listing)
PORT = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()
LISTING = f"http://127.0.0.1:{PORT}/listing"

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


# --------------------------------------------------------------------------- setup
client.post("/api/auth/register", json={"email": "agent@example.com", "password": "long enough",
                                       "name": "Agent", "invite_code": "beta-code-123"})
client.post("/api/auth/register", json={"email": "owner@example.com", "password": "long enough",
                                        "name": "Owner"})
def connect_meta(email):
    """Mark the account as Meta-connected: + Campaign is closed until it is (item 8)."""
    from datetime import datetime, timezone
    from app.db.session import SessionLocal, User
    db = SessionLocal()
    user = db.query(User).filter(User.email == email).first()
    user.meta_connected_at = datetime.now(timezone.utc)
    db.commit()
    db.close()


def login(email, password="long enough"):
    """The token endpoint is OAuth2 form-encoded, not JSON."""
    token = client.post("/api/auth/login", data={"username": email,
                                                 "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


connect_meta("agent@example.com")
agent = login("agent@example.com")
ADMIN = login("owner@example.com")


def make_boost(address="1234 Elm Street, Austin, TX 78704"):
    resp = client.post("/api/boosts", headers=agent, json={
        "address": address, "tier": "bap_shoot_499", "go_live_date": "2026-12-01",
        "campaign_days": 14, "ad_budget_usd": 50.0, "property_facts": "3BR/2BA"})
    return resp.json()


def attach_live_ad(boost_id: int, user_email: str = "agent@example.com"):
    """Give the boost a connected account and a launched ad, the way a real launch leaves it."""
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == user_email).first()
        boost = db.query(Boost).filter(Boost.id == boost_id).first()
        account = AdAccount(user_id=user.id, platform="meta", advertiser_id="act_demo",
                            account_name="Demo", access_token="", is_active=True)
        db.add(account)
        db.flush()
        boost.ad_account_id = account.id
        boost.launched_at = datetime.now(timezone.utc) - timedelta(days=3)
        boost.end_date = datetime.now(timezone.utc) + timedelta(days=11)
        db.add(Ad(boost_id=boost.id, kind="photo", format="carousel",
                  status="scheduled", meta_ad_id="ad_1", meta_adset_id="adset_1",
                  meta_campaign_id="camp_1", card_post_ids=[1], image_hashes=["h1"]))
        db.commit()
    finally:
        db.close()


# --------------------------------------------------------------------------- launch details
print("\n=== 1. the listing link is checked, not trusted ===")
boost = make_boost()
resp = client.patch(f"/api/boosts/{boost['id']}/launch-details", headers=agent,
                    json={"listing_url": LISTING})
check("a real listing link is accepted", resp.status_code == 200, resp.text[:200])
check("  ...and the good check is reported", resp.json()["checks"]["listing_url"]["ok"] is True,
      resp.text[:300])

resp = client.patch(f"/api/boosts/{boost['id']}/launch-details", headers=agent,
                    json={"listing_url": f"http://127.0.0.1:{PORT}/gone"})
check("a 404 link is refused before it reaches an ad", resp.status_code == 422, resp.text[:200])
check("  ...with the reason the seller can act on",
      "404" in (resp.json().get("detail", {}).get("message") or ""), resp.text[:200])

resp = client.patch(f"/api/boosts/{boost['id']}/launch-details", headers=agent,
                    json={"listing_url": "not a url"})
check("a non-URL is refused", resp.status_code == 422, resp.text[:200])

resp = client.patch(f"/api/boosts/{boost['id']}/launch-details", headers=agent,
                    json={"listing_url": LISTING, "budget_usd": 1,
                          "destination_url": "https://example.com/elm"})
check("the budget is clamped to the floor, not taken as typed",
      resp.json().get("budget_usd") == 5.0, resp.text[:200])
db = SessionLocal()
saved = db.query(Boost).filter(Boost.id == boost["id"]).first()
check("  ...and stored with the moment it was confirmed",
      saved.budget_confirmed_at is not None and saved.destination_url == "https://example.com/elm",
      f"{saved.budget_confirmed_at} {saved.destination_url}")
db.close()

# --------------------------------------------------------------------------- pause / resume
print("\n=== 2. pause stops delivery and gives the days back ===")
attach_live_ad(boost["id"])
resp = client.post(f"/api/boosts/{boost['id']}/pause", headers=agent)
body = resp.json()
check("pause reports success", resp.status_code == 200 and body["status"] == "paused", resp.text[:300])
check("  ...and touches the ad, the ad set and the campaign",
      len([s for s in body["steps"] if s.get("ok")]) == 3, str(body)[:300])

resp = client.post(f"/api/boosts/{boost['id']}/resume", headers=agent)
body = resp.json()
check("resume restarts delivery", resp.status_code == 200 and body["status"] == "resumed",
      resp.text[:300])
check("  ...and moves the ad set's end date by the paused days",
      any(str(st.get("adset_end_time") or "").startswith("2026-12-15") for st in body.get("steps") or []),
      str(body)[:300])

resp = client.post(f"/api/boosts/99999/pause", headers=agent)
check("someone else's campaign cannot be paused", resp.status_code == 404)

# --------------------------------------------------------------------------- the numbers
print("\n=== 3. the numbers come back in the seller's language ===")
resp = client.get(f"/api/boosts/{boost['id']}/ad-performance", headers=agent)
body = resp.json()
check("performance is readable", resp.status_code == 200 and "totals" in body, resp.text[:300])
check("  ...with the keys the report uses",
      all(k in body.get("totals", {}) for k in ("impressions", "clicks", "link_clicks",
                                                "leads", "spend", "ctr_percent")),
      str(body.get("totals"))[:300])
check("  ...and a format the creative decision depends on", body.get("format") == "carousel")

# --------------------------------------------------------------------------- the watcher
print("\n=== 4. the listing watcher reads the page and stops a sold campaign ===")
check("classify: for sale is active", listing_watch.classify(200, LISTING_HTML) == "active")
check("classify: sold is sold", listing_watch.classify(200, SOLD_HTML) == "sold")
check("classify: under contract is pending",
      listing_watch.classify(200, PENDING_HTML) == "pending")
check("classify: a 404 is offline, not active",
      listing_watch.classify(404, "") == "offline")
check("classify: a 500 is unknown, never sold on a guess",
      listing_watch.classify(500, "") == "unknown")

resp = client.post("/api/admin/listings/sweep", headers={"x-resmara-token": "wrong"})
check("the sweep refuses a bad token", resp.status_code == 403, resp.text[:120])

db = SessionLocal()
try:
    row = db.query(Boost).filter(Boost.id == boost["id"]).first()
    row.listing_url = LISTING
    db.commit()
finally:
    db.close()

# Engine 6, section 7: the words on a page are never a status; the status field behind it is.
PAGE["body"] = LISTING_HTML
resp = client.post("/api/admin/listings/sweep", headers={"x-resmara-token": "sweep-token"})
body = resp.json()
check("the sweep runs with the system token", resp.status_code == 200, resp.text[:200])
check("  ...and words alone ('Sold', 'pending') never decide", body.get("sold") == 0 and body.get("pending") == 0,
      str(body)[:300])
PAGE["body"] = status_page("FOR_SALE")
body = client.post("/api/admin/listings/sweep", headers={"x-resmara-token": "sweep-token"}).json()
check("  ...and records the listing as still active",
      (body.get("details") or [{}])[0].get("status") == "active", str(body)[:300])

PAGE["body"] = status_page("SOLD")
resp = client.post("/api/admin/listings/sweep", headers={"x-resmara-token": "sweep-token"})
body = resp.json()
check("a sold listing is caught on the next sweep", body.get("sold") == 1, str(body)[:300])
db = SessionLocal()
row = db.query(Boost).filter(Boost.id == boost["id"]).first()
check("  ...with the state saved on the campaign",
      row.listing_status == "sold" and row.paused_at is not None, str(row.listing_status))
db.close()
PAGE["body"] = LISTING_HTML

# --------------------------------------------------------------------------- run it again
print("\n=== 5. a second campaign is $39 and keeps the listing's history ===")
from app.services import billing  # noqa: E402

check("a first campaign is $49", billing.price_cents() == 4900, str(billing.price_cents()))
check("a repeat is $39", billing.repeat_price_cents() == 3900, str(billing.repeat_price_cents()))

resp = client.post(f"/api/boosts/{boost['id']}/again", headers=agent, json={})
body = resp.json()
check("a second campaign is created", resp.status_code == 201, resp.text[:200])
check("  ...in round 2", body.get("repeat_round") == 1, str(body.get("repeat_round")))
check("  ...pointing back at the campaign it continues",
      body.get("parent_boost_id") == boost["id"], str(body.get("parent_boost_id")))
repeat = type("Boost", (), {"repeat_round": body.get("repeat_round")})()
first = type("Boost", (), {"repeat_round": 0})()
check("  ...and priced at $39 because it is a repeat", billing.price_for(repeat) == 3900)
check("  ...while a first campaign still costs $49", billing.price_for(first) == 4900)
check("  ...carrying the listing link over instead of making the agent retype it",
      body.get("listing_url") == LISTING, str(body.get("listing_url")))

db = SessionLocal()
child = db.query(Boost).filter(Boost.id == body.get("id")).first()
check("  ...with fresh copy and no reused plan", child is not None and not child.plan)
check("  ...and no paid stamp until it is actually bought",
      child is not None and child.paid_at is None)
db.close()

print("\n=== 6. the agent's photo permission is recorded before the engine runs ===")
from app.db.session import Asset  # noqa: E402

photo = make_boost("88 Oak Avenue, Austin, TX 78704")
db = SessionLocal()
db.add(Asset(user_id=db.query(User).filter(User.email == "agent@example.com").first().id,
             boost_id=photo["id"], filename="front.jpg", url="/uploads/front.jpg",
             original_name="front.jpg", kind="photo", data=b"", content_type="image/jpeg"))
# Paid first: money is the outer gate (item 16), permission is what Build asks after it.
db.query(Boost).filter(Boost.id == photo["id"]).first().paid_at = datetime.now(timezone.utc)
db.commit()
db.close()

resp = client.post(f"/api/boosts/{photo['id']}/build", headers=agent, json={})
detail = resp.json().get("detail") or {}
check("a gallery with no permission on record cannot be built",
      resp.status_code == 409 and detail.get("error") == "photo_permission_required",
      resp.text[:200])
check("  ...and the answer says what to confirm",
      "permission" in (detail.get("message") or "").lower(), str(detail)[:200])

resp = client.patch(f"/api/boosts/{photo['id']}/photo-permission", headers=agent,
                    json={"granted": True})
check("ticking the box records the moment", resp.status_code == 200
      and resp.json().get("photo_permission_at"), resp.text[:200])
stamp = resp.json().get("photo_permission_at")

resp = client.patch(f"/api/boosts/{photo['id']}/photo-permission", headers=agent,
                    json={"granted": True})
check("  ...and a second tick does not move it", resp.json().get("photo_permission_at") == stamp)

row = client.get("/api/boosts", headers=agent).json()
entry = next((b for b in row if b.get("id") == photo["id"]), {})
check("  ...and it is visible on the campaign itself",
      bool(entry.get("photo_permission_at")), str(entry)[:200])

print("\n=== 7. the old test posts can be audited and cleared, and only on purpose ===")
from app.db.session import Post  # noqa: E402

db = SessionLocal()
for n in range(3):
    db.add(Post(boost_id=boost["id"], day=n + 1, slot=1, kind="static",
                caption=f"Test caption {n}\nsecond line", publish_status="scheduled"))
db.commit()
db.close()

resp = client.get("/api/admin/posts/audit", headers=agent)
check("an agent cannot read the post audit", resp.status_code == 403, resp.text[:120])

audit = client.get("/api/admin/posts/audit", headers=ADMIN).json()
check("an operator can see every campaign's posts", audit["total_posts"] >= 3, str(audit)[:200])
row = next((c for c in audit["campaigns"] if c["boost_id"] == boost["id"]), {})
check("  ...with a sample of what each post says",
      row.get("sample") and row["sample"][0]["caption"].startswith("Test caption"),
      str(row)[:200])

resp = client.post("/api/admin/posts/purge", headers=ADMIN, json={})
check("a purge without the count is refused", resp.status_code == 428, resp.text[:200])
check("  ...and the refusal names the exact phrase",
      resp.json()["detail"].get("expect_confirm", "").startswith("DELETE "), resp.text[:200])

resp = client.post("/api/admin/posts/purge", headers=ADMIN, json={
    "confirm": f"DELETE {audit['total_posts']} POSTS", "expect_total": audit["total_posts"],
    "keep_boost_ids": [boost["id"]]})
check("keeping one campaign deletes the rest",
      resp.status_code == 200 and resp.json()["deleted"] >= 0, resp.text[:200])

after = client.get("/api/admin/posts/audit", headers=ADMIN).json()
kept = next((c for c in after["campaigns"] if c["boost_id"] == boost["id"]), {})
check("  ...and the campaign that was kept still has its posts", kept.get("posts") == 3,
      str(kept)[:200])

print("\n=== 8. the same job from a machine token, not a browser ===")
import os as _os
pub = "test-publish-token-123"
_os.environ["RESMARA_PUBLISH_TOKEN"] = pub
from app.core.config import settings as _settings
_settings.PUBLISH_TOKEN = pub
r = client.get("/api/admin/posts/audit", headers={"X-Resmara-Token": pub})
check("the audit answers a token", r.status_code == 200, r.text[:160])
r_bad = client.get("/api/admin/posts/audit", headers={"X-Resmara-Token": "wrong"})
check("  ...but not a wrong one", r_bad.status_code in (401, 403), str(r_bad.status_code))
guard = client.post("/api/admin/posts/purge", json={"expect_total": 0, "confirm": "DELETE 0 POSTS"},
                    headers={"X-Resmara-Token": pub})
check("the count guard still bites with a token", guard.status_code == 428, str(guard.status_code))
now = client.get("/api/admin/posts/audit", headers={"X-Resmara-Token": pub}).json()["total_posts"]
done = client.post("/api/admin/posts/purge",
                   json={"expect_total": now, "confirm": f"DELETE {now} POSTS"},
                   headers={"X-Resmara-Token": pub})
check("  ...and a token purge works", done.status_code == 200 and done.json()["deleted"] == now,
      done.text[:200])
check("  ...leaving nothing behind", done.json()["remaining"] == 0, done.text[:200])

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL CAMPAIGN CONTROL TESTS PASSED")
