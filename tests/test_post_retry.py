"""Failed posts: three retries over 30 minutes, then the right verdict and the right action.

Why this test exists: a failed post used to be one line - ``publish_status='failed'`` plus
``last_error`` - and every kind of incident looked the same on the calendar. The owner's rule
(Resmara update 11/15, item 11) is that three very different things must happen:

  * our fault (engine, upload, design, template) - retry about 3 times over 30 minutes, then
    fix and repost;
  * the agent's Meta connection (dead token, missing scope, 401/403/OAuth) - no blind retries:
    email the agent once, show the red banner, and repost automatically when the token checks
    healthy again;
  * Meta rejected the post (policy, copy, media) - NEVER auto-retry: show Meta's own reason and
    let them edit, because the same post earns the same refusal.

It drives the real sweep (``publisher.publish_due``) against a mock Graph, a temp sqlite
database and a real FastAPI client, and pins the schedule, the three classifications, the
one-email rule, the reconnect repost and the API the calendar reads.

Run:
    cd /Users/dan/resmara && ./venv/bin/python3 tests/test_post_retry.py
"""
import asyncio
import json
import os
import sys
import tempfile
import threading
import time
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_SCRATCH = "/Users/dan/.hermes/profiles/dev/cache/scratch"
if not os.path.isdir(_SCRATCH):
    _SCRATCH = tempfile.gettempdir()
TMP = tempfile.mkdtemp(prefix="resmara_retry_", dir=_SCRATCH)

os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(TMP, "retry.db")
os.environ["UPLOAD_DIR"] = os.path.join(TMP, "uploads")
os.environ["RESMARA_SIMULATE"] = "0"
# The suite brings what it needs rather than inheriting a developer's .env: the system-token
# sweep and the token check both refuse to run without these.
os.environ["RESMARA_PUBLISH_TOKEN"] = "retry-sweep-token"
os.environ["META_CLIENT_ID"] = "app_retry_000000"
os.environ["META_CLIENT_SECRET"] = "secret_retry_000000"
os.makedirs(os.environ["UPLOAD_DIR"], exist_ok=True)

# What the mock Graph does next. One server covers every scenario.
STATE = {
    "post": "ok",        # ok | our_fault | policy | token
    "valid": True,       # does /debug_token report a usable token?
}
calls = []


class Graph(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        calls.append(("GET", u.path, q))
        if u.path == "/debug_token":
            if not STATE["valid"]:
                return self._json({"error": {"message": "Invalid OAuth access token",
                                             "code": 190, "type": "OAuthException"}}, code=400)
            return self._json({"data": {
                "app_id": os.environ["META_CLIENT_ID"], "type": "USER",
                "is_valid": True,
                "expires_at": int(time.time()) + 50 * 86400,
                "scopes": ["ads_management", "business_management"],
            }})
        if u.path.startswith("/act_"):
            return self._json({"name": "Retry Ad Account", "account_status": 1,
                               "disable_reason": 0, "currency": "USD", "is_prepay_account": False,
                               "funding_source_details": {"type": "VISA",
                                                          "display_string": "Visa ending 4242"}})
        return self._json({"data": []})

    def do_POST(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        length = int(self.headers.get("Content-Length") or 0)
        if length:
            self.rfile.read(length)
        calls.append(("POST", u.path, q))

        if u.path == "/PAGE1/photos" or u.path == "/PAGE1/feed":
            mode = STATE["post"]
            if mode == "ok":
                return self._json({"id": "fb_post_ok"})
            if mode == "our_fault":
                # A Graph that simply broke: nothing the agent can do, retrying is right.
                return self._json({"error": {"message": "An unexpected error has occurred. "
                                                        "Please retry your request later.",
                                             "code": 2, "is_transient": True}}, code=500)
            if mode == "policy":
                return self._json({"error": {
                    "message": "This post was not published.",
                    "code": 368,
                    "error_user_title": "Your post wasn't published",
                    "error_user_msg": "Your post goes against our Community Standards on spam.",
                }}, code=400)
            if mode == "token":
                return self._json({"error": {
                    "message": "Error validating access token: Session has expired.",
                    "code": 190, "error_subcode": 463, "type": "OAuthException",
                }}, code=400)
        return self._json({"data": []})


server = HTTPServer(("127.0.0.1", 0), Graph)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ["GRAPH_API_BASE"] = f"http://127.0.0.1:{server.server_address[1]}"

from fastapi.testclient import TestClient                                  # noqa: E402
from app.main import app                                                    # noqa: E402
from app.core.config import settings                                        # noqa: E402
from app.db.session import (Base, engine, SessionLocal, User, AdAccount, Boost, Post,  # noqa: E402
                             Event)
from app.services import mail, post_retry, publisher, token_health          # noqa: E402

Base.metadata.create_all(bind=engine)

CHECKS = []
FAILS = []


def ok(name, cond, detail=""):
    CHECKS.append(name)
    if cond:
        print(f"  PASS  {name}")
    else:
        FAILS.append(name)
        print(f"  FAIL  {name}" + (f"  ({detail})" if detail else ""))


with open(os.path.join(settings.UPLOAD_DIR, "photo.jpg"), "wb") as fh:
    fh.write(b"\xff\xd8\xffJPEGBYTES")

SITE = TestClient(app)

# --------------------------------------------------------------------------- 1. classification
print("\n=== 1. every failure lands in exactly one of the three kinds ===")
C = post_retry.classify
ok("a dead token (190) is a connection problem",
   C("Error validating access token", status_code=400,
     graph_error={"code": 190, "type": "OAuthException"}) == post_retry.KIND_CONNECTION)
ok("a missing permission (200) is a connection problem",
   C("Permissions error", graph_error={"code": 200}) == post_retry.KIND_CONNECTION)
ok("a bare HTTP 403 is a connection problem",
   C("Forbidden", status_code=403) == post_retry.KIND_CONNECTION)
ok("Meta's community-standards refusal (368) is a rejection, not ours",
   C("not published", graph_error={"code": 368}) == post_retry.KIND_META_REJECTED)
ok("an unsupported aspect ratio (36003) is a rejection",
   C("aspect ratio", graph_error={"code": 36003}) == post_retry.KIND_META_REJECTED)
ok("Meta's user-facing refusal wording counts as a rejection even without a code we know",
   C("refused", graph_error={"code": 100,
                             "error_user_msg": "This photo does not meet our requirements."})
   == post_retry.KIND_META_REJECTED)
ok("a transient Graph 500 is ours to retry",
   C("unexpected error", status_code=500, graph_error={"code": 2}) == post_retry.KIND_OUR_FAULT)
ok("a missing upload file is ours",
   C("media file not found for post 4: /uploads/gone.jpg") == post_retry.KIND_OUR_FAULT)
ok("no Meta account connected is a connection problem, not a retry",
   C("No Meta account connected for this boost") == post_retry.KIND_CONNECTION)
ok("there are exactly three kinds", post_retry.KINDS == ("our_fault", "connection", "meta_rejected"))

# --------------------------------------------------------------------------- fixtures
pw = "retry-pass-12345"
SITE.post("/api/auth/register", json={"email": "retry@example.com", "password": pw, "name": "Retry"})
tok = SITE.post("/api/auth/login", data={"username": "retry@example.com", "password": pw}).json()["access_token"]
H = {"Authorization": f"Bearer {tok}"}

db = SessionLocal()
user = db.query(User).filter(User.email == "retry@example.com").first()
user.subscription_status = "active"
db.add(user)
db.commit()
acct = AdAccount(user_id=user.id, platform="meta", advertiser_id="act_123",
                 access_token="test_token", page_id="PAGE1", ig_user_id="IG1",
                 is_active=True, budget=50.0)
db.add(acct)
db.commit()
ACCT_ID = acct.id
boost = Boost(user_id=user.id, ad_account_id=acct.id, address="9 Retry Lane", stage="LIVE",
              main_status="Live", go_live_date="2026-11-01")
db.add(boost)
db.commit()
BOOST_ID = boost.id          # plain value: the ORM object detaches when this session closes
db.close()


def new_post(day, target="facebook"):
    session = SessionLocal()
    post = Post(boost_id=BOOST_ID, day=day, slot=1, kind="photo", caption="A caption",
                hashtags="#tag", image_url="/uploads/photo.jpg", client_status="approved",
                publish_status="scheduled", publish_target=target,
                publish_at="2026-11-01T10:00:00", publish_attempts=0)
    session.add(post)
    session.commit()
    pid = post.id
    session.close()
    return pid


def fresh(pid):
    session = SessionLocal()
    session.expire_all()
    row = session.query(Post).filter(Post.id == pid).first()
    session.expunge(row)
    session.close()
    return row


def run(now):
    session = SessionLocal()
    try:
        return asyncio.run(publisher.publish_due(session, now=now))
    finally:
        session.close()


def post_calls(path="/PAGE1/photos"):
    return [c for c in calls if c[0] == "POST" and c[1] == path]


# --------------------------------------------------------------------------- 2. the retry ladder
print("\n=== 2. our fault: three retries over 30 minutes, then fix-and-repost ===")
ok("the schedule is 3 retries at 2, 10 and 30 minutes",
   post_retry.RETRY_MARKS_MINUTES == (2, 10, 30) and post_retry.MAX_ATTEMPTS == 4,
   str((post_retry.RETRY_MARKS_MINUTES, post_retry.MAX_ATTEMPTS)))

# The clock the test drives, one and a half hours ago: the retries have to land inside the
# daily summary's 24-hour window, so the times cannot be far enough back to miss it.
T0 = datetime.utcnow().replace(microsecond=0) - timedelta(minutes=90)


def at(minutes):
    return (T0 + timedelta(minutes=minutes)).isoformat()


pid = new_post(day=1)
STATE["post"] = "our_fault"
before = len(post_calls())

r = run(at(0))
row = fresh(pid)
ok("the first failure does not mark the post dead", row.publish_status == "scheduled",
   f"status={row.publish_status}")
ok("  ...it counts the attempt", row.publish_attempts == 1, str(row.publish_attempts))
ok("  ...and the first retry is due 2 minutes later", row.next_attempt_at == at(2),
   str(row.next_attempt_at))
ok("  ...and the run reports it as retrying, not failed",
   r["failed"] == 1 and r["retrying"] == 1, str(r["details"]))
ok("  ...with the agent told it is ours and being retried",
   "on us" in (row.failure_note or "") and "1 of 4" in (row.failure_note or ""), row.failure_note)

r = run(at(1))
ok("a sweep before the retry is due does nothing", r["checked"] == 0, str(r))
ok("  ...and makes no network call", len(post_calls()) - before == 1, str(len(post_calls()) - before))

r = run(at(3))
row = fresh(pid)
ok("the retry runs when it is due", row.publish_attempts == 2, str(row.publish_attempts))
ok("  ...and the next wait is 8 minutes (the 10-minute mark)",
   row.next_attempt_at == at(11), str(row.next_attempt_at))

run(at(11))
row = fresh(pid)
ok("the third try lands on the 30-minute mark's last wait",
   row.publish_attempts == 3 and row.next_attempt_at == at(31),
   str((row.publish_attempts, row.next_attempt_at)))

r = run(at(31))
row = fresh(pid)
ok("the fourth try is the last one", row.publish_attempts == 4, str(row.publish_attempts))
ok("  ...and the post is now marked failed", row.publish_status == "failed", row.publish_status)
ok("  ...with no further attempt scheduled", row.next_attempt_at is None)
ok("  ...classified as our fault", row.failure_kind == post_retry.KIND_OUR_FAULT, row.failure_kind)
ok("  ...and the agent is told it is ours to fix and repost",
   "our fault" in (row.failure_note or "").lower(), row.failure_note)
ok("exactly four attempts reached Meta", len(post_calls()) - before == 4, str(len(post_calls()) - before))
ok("a sweep after the ladder is spent does not try again", run(at(90))["checked"] == 0)

# --------------------------------------------------------------------------- 3. Meta rejected it
print("\n=== 3. Meta rejected it: never auto-retried, Meta's reason shown, edit offered ===")
pid = new_post(day=2)
STATE["post"] = "policy"
before = len(post_calls())

r = run(at(0))
row = fresh(pid)
ok("the rejection marks the post failed on the first answer", row.publish_status == "failed",
   row.publish_status)
ok("  ...classified as a Meta rejection", row.failure_kind == post_retry.KIND_META_REJECTED,
   row.failure_kind)
ok("  ...with no retry scheduled", row.next_attempt_at is None and row.publish_attempts == 1,
   str((row.next_attempt_at, row.publish_attempts)))
ok("  ...and Meta's own sentence is what the agent reads",
   "Community Standards on spam" in (row.failure_note or ""), row.failure_note)
ok("  ...carried verbatim from Meta", "Community Standards on spam" in (row.last_error or ""),
   row.last_error)
ok("only one call was made", len(post_calls()) - before == 1, str(len(post_calls()) - before))

ok("a later sweep never retries a rejected post", run(at(40))["checked"] == 0)
ok("  ...no matter how much later", run(at(60 * 48))["checked"] == 0)
ok("  ...so Meta saw exactly one attempt", len(post_calls()) - before == 1,
   str(len(post_calls()) - before))

payload = post_retry.failure_payload(row)
ok("the calendar is told this is a rejection with Meta's reason",
   payload["kind"] == post_retry.KIND_META_REJECTED and payload["reason"] == row.last_error,
   str(payload)[:200])
ok("  ...that it is not retrying", payload["retrying"] is False)
ok("  ...and it offers Edit and Skip, never Try again",
   payload["actions"] == ["edit_and_post", "skip"], str(payload["actions"]))
ok("  ...under the red banner", payload["label"] == "Didn't post", payload["label"])

rejected_id = pid

# --------------------------------------------------------------------------- 4. the connection
print("\n=== 4. the agent's connection died: one email, red banner, no blind retries ===")
pid = new_post(day=3)
STATE["post"] = "token"
before = len(post_calls())

sent = []
real_send, real_configured = mail.send_email, mail.mail_configured
mail.send_email = lambda to, subject, body: (sent.append((to, subject, body)) or True)
mail.mail_configured = lambda: True
try:
    r = run(at(0))
    row = fresh(pid)
    ok("a dead token marks the post failed at once, with no retry ladder",
       row.publish_status == "failed" and row.publish_attempts == 1,
       str((row.publish_status, row.publish_attempts)))
    ok("  ...classified as a connection problem", row.failure_kind == post_retry.KIND_CONNECTION,
       row.failure_kind)
    ok("  ...the agent is emailed once", len(sent) == 1, str(sent)[:200])
    ok("  ...to the campaign's own agent", sent and sent[0][0] == "retry@example.com", str(sent)[:120])
    ok("  ...telling them to reconnect and that the post reposts itself",
       "reconnect" in sent[0][2].lower() and "by itself" in sent[0][2], sent[0][2][:200])
    ok("  ...and their own words say the same", "reconnect" in (row.failure_note or "").lower(),
       row.failure_note)

    run(at(40))
    run(at(60 * 24))
    ok("no retry of any kind happened", len(post_calls()) - before == 1,
       str(len(post_calls()) - before))
    ok("and nobody was emailed twice", len(sent) == 1, str(len(sent)))

    payload = post_retry.failure_payload(fresh(pid))
    ok("the calendar shows the red banner with reconnect offered",
       payload["actions"] == ["reconnect", "try_again", "skip"] and payload["emailed"] is True,
       str(payload)[:220])
finally:
    mail.send_email, mail.mail_configured = real_send, real_configured

connection_id = pid

# --------------------------------------------------------------------------- 5. reconnect
print("\n=== 5. the connection comes back: the post reposts by itself ===")
session = SessionLocal()
acct_row = session.query(AdAccount).filter(AdAccount.id == ACCT_ID).first()
STATE["valid"] = True
summary = asyncio.run(token_health.refresh_account(acct_row, session))
ok("the token check reports the connection healthy", summary["token_status"] == "healthy",
   str(summary.get("token_status")))
ok("  ...and it says how many posts came back", summary.get("posts_requeued") == 1,
   str(summary.get("posts_requeued")))
row = session.query(Post).filter(Post.id == connection_id).first()
ok("the post is queued again", row.publish_status == "scheduled", row.publish_status)
ok("  ...with a fresh ladder", row.publish_attempts == 0 and row.next_attempt_at is None,
   str((row.publish_attempts, row.next_attempt_at)))
ok("  ...and the banner is gone", post_retry.failure_payload(row) is None,
   str(post_retry.failure_payload(row)))
session.close()

STATE["post"] = "ok"
before = len(post_calls())
r = run(at(180))
row = fresh(connection_id)
ok("the ordinary sweep publishes it", r["posted"] == 1 and row.publish_status == "posted",
   str((r["posted"], row.publish_status)))
ok("  ...under a real network call", len(post_calls()) - before == 1,
   str(len(post_calls()) - before))
ok("  ...keeping the day's failure on the record for the summary", row.failed_at is not None)

# --------------------------------------------------------------------------- 6. the API
print("\n=== 6. what the calendar reads, and the buttons it can press ===")
status = SITE.get(f"/api/content/publish/status/{BOOST_ID}", headers=H)
body = status.json() if status.status_code == 200 else {}
posts = {p["id"]: p for p in body.get("posts", [])}
ok("the status endpoint answers", status.status_code == 200, status.text[:160])
ok("  ...and still carries every key an older client reads",
   all(k in posts.get(rejected_id, {}) for k in
       ("id", "day", "slot", "publish_status", "last_error", "publish_at", "publish_target")),
   str(list(posts.get(rejected_id, {}))[:12]))
ok("  ...plus the failure the banner needs",
   posts.get(rejected_id, {}).get("failure", {}).get("kind") == post_retry.KIND_META_REJECTED,
   str(posts.get(rejected_id, {}).get("failure"))[:200])

feed = SITE.get(f"/api/boosts/{BOOST_ID}/posts", headers=H)
entry = next((p for p in (feed.json() if feed.status_code == 200 else [])
              if p["id"] == rejected_id), {})
ok("the calendar's own post feed carries the banner too",
   feed.status_code == 200 and entry.get("failure", {}).get("kind") == post_retry.KIND_META_REJECTED,
   f"{feed.status_code} {str(entry.get('failure'))[:160]}")
ok("  ...and still every field it had before",
   {"id", "caption", "publish_status", "last_error", "publish_at"} <= set(entry),
   str(sorted(entry))[:200])

r = SITE.post(f"/api/content/publish/post/{rejected_id}/retry", headers=H)
ok("Try again on a rejected post is refused with Meta's reason",
   r.status_code == 400 and "rejected" in r.text, f"{r.status_code} {r.text[:160]}")

r = SITE.post(f"/api/content/publish/post/{rejected_id}/retry?edited=true", headers=H)
ok("Edit and post is accepted once the copy has changed", r.status_code == 200, r.text[:160])
ok("  ...and the post is queued again",
   fresh(rejected_id).publish_status == "scheduled", fresh(rejected_id).publish_status)

r = SITE.post(f"/api/content/publish/post/{rejected_id}/skip", headers=H)
row = fresh(rejected_id)
ok("Skip takes it out of the calendar", r.status_code == 200 and row.publish_status == "skipped",
   f"{r.status_code} {row.publish_status}")
ok("  ...and clears the retry clock", row.next_attempt_at is None)
ok("  ...and the banner is gone from the calendar",
   post_retry.failure_payload(row) is None, str(post_retry.failure_payload(row)))

r = SITE.post("/api/content/publish/post/999999/skip", headers=H)
ok("a post that is not the caller's is a 404", r.status_code == 404, str(r.status_code))

# --------------------------------------------------------------------------- 7. daily summary
print("\n=== 7. the daily summary rides along with the sweep that already runs ===")
STATE["post"] = "ok"
STATE["valid"] = True
summary = SITE.post("/api/oauth/meta/check-all", headers={"X-Resmara-Token": "retry-sweep-token"})
ok("the system-token sweep runs", summary.status_code == 200, summary.text[:160])
sweep = summary.json() if summary.status_code == 200 else {}
failed = sweep.get("failed_posts") or {}
ok("it carries the day's failed posts", isinstance(failed.get("by_kind"), dict), str(failed)[:200])
ok("  ...counted by kind", failed.get("by_kind", {}).get("meta_rejected") == 1
   and failed.get("by_kind", {}).get("connection") == 1
   and failed.get("by_kind", {}).get("our_fault") == 1, str(failed.get("by_kind")))
ok("  ...with a total", failed.get("total") == 3, str(failed.get("total")))
ok("  ...over a 24-hour window", failed.get("window_hours") == 24, str(failed.get("window_hours")))

session = SessionLocal()
# An incident from three days ago must not be sold as today's.
session.add(Event(boost_id=BOOST_ID, event_type="post_failed",
                  payload={"post_id": 999, "kind": "connection", "attempts": 1},
                  created_at=datetime.utcnow() - timedelta(days=3)))
session.commit()
full = post_retry.daily_summary(session, hours=24)
three_days = post_retry.daily_summary(session, hours=72 + 1)
session.close()
ok("the summary is a plain function, not a mail blast",
   set(full.keys()) >= {"total", "by_kind", "posts", "window_hours"}, str(list(full.keys())))
ok("  ...that only counts inside its window",
   three_days["total"] == full["total"] + 1 and full["total"] == 3,
   str((three_days["total"], full["total"])))
ok("  ...and lists who to look at",
   full["posts"] and full["posts"][0]["address"] == "9 Retry Lane", str(full["posts"])[:200])

# ---------------------------------------------------------------------------
print(f"\n{len(CHECKS)} checks, {len(FAILS)} failed.")
if FAILS:
    print("FAILED: " + ", ".join(FAILS))
    print("FAILED - failed post handling")
    raise SystemExit(1)
print("ALL POST RETRY TESTS PASSED")
raise SystemExit(0)
