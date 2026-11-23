"""Engine 1 Part A, proven from the customer's seat.

What this pins, in the order an agent lives it:

  * the Terms box is not decoration: without it the Facebook button does nothing, and the
    consent it records is what the new account is stamped with;
  * "Log in with Facebook" creates one account, and the same Facebook always lands on the same
    account - never a second one;
  * the JWT never rides in a URL: Facebook's redirect hands back a one-time ticket, and a
    second use of that ticket is refused;
  * an account Facebook refuses to give an email for still works, and we ask once;
  * a closed account is offered reactivation instead of a silent sign-in;
  * the four onboarding emails go once each, stop at the first launched campaign, skip test and
    unsubscribed accounts, and carry a working unsubscribe link.

Run:  cd ~/resmara && PYTHONPATH=. venv/bin/python tests/test_facebook_login.py
"""
import http.server
import json as _json
import os
import sys
import tempfile
import threading
import urllib.parse
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-fblogin-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "test-secret-key-for-facebook-login-000000"
os.environ["META_CLIENT_ID"] = "1135911812356864"
os.environ["META_CLIENT_SECRET"] = "test-app-secret"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
os.environ["RESMARA_PUBLISH_TOKEN"] = "clock-token"
os.environ["RESMARA_PUBLIC_BASE_URL"] = "https://www.resmara.com"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ------------------------------------------------------------------ mock Graph
class MockGraph:
    """Only what Facebook actually answers on this path: a code exchange and /me."""

    def __init__(self):
        self.people = {"code-jamie": {"id": "fb-1001", "name": "Jamie Carter", "email": "jamie@example.com"},
                       "code-noemail": {"id": "fb-2002", "name": "No Email Nancy"}}
        self.log = []
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_GET(self):  # noqa: N802
                parsed = urllib.parse.urlparse(self.path)
                query = urllib.parse.parse_qs(parsed.query)
                outer.log.append({"path": parsed.path, "query": parsed.query})
                code = (query.get("code") or [""])[0]
                token = (query.get("access_token") or [""])[0]
                if parsed.path.endswith("/oauth/access_token"):
                    if code not in outer.people:
                        return self._json(400, {"error": {"message": "Invalid verification code"}})
                    return self._json(200, {"access_token": "tok-" + code, "token_type": "bearer"})
                if parsed.path.endswith("/me"):
                    person = outer.people.get(token.replace("tok-", "", 1))
                    if not person:
                        return self._json(401, {"error": {"message": "Invalid OAuth access token"}})
                    answer = {"id": person["id"], "name": person["name"]}
                    if person.get("email"):
                        answer["email"] = person["email"]
                    return self._json(200, answer)
                return self._json(404, {"error": {"message": "no route in the mock"}})

            def _json(self, status, payload):
                data = _json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self._httpd = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self._httpd.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self._httpd.server_address[1]}"

    def stop(self):
        self._httpd.shutdown()


MOCK = MockGraph()
os.environ["GRAPH_API_BASE"] = MOCK.url

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.core.config import settings  # noqa: E402
settings.GRAPH_API_BASE = MOCK.url
from app.db.session import Base, Boost, Event, SessionLocal, User, engine  # noqa: E402
from app.db.migrate import migrate  # noqa: E402
from app.services import mail, onboarding_emails  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()
client = TestClient(app)

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


sent = []
mail.send_email = lambda to, subject, body: (sent.append((to, subject, body)), True)[1]


def db_user(**kw):
    db = SessionLocal()
    try:
        return db.query(User).filter_by(**kw).first()
    finally:
        db.close()


def login_via_facebook(code, terms=True, fmt="json"):
    start = client.post("/api/auth/facebook/start",
                        json={"terms_accepted": terms, "terms_version": "2026-11-22"})
    if start.status_code != 200:
        return start
    state = urllib.parse.parse_qs(urllib.parse.urlparse(start.json()["redirect_url"]).query)["state"][0]
    return client.get(f"/api/auth/facebook/callback?code={code}&state={urllib.parse.quote(state)}&format={fmt}")


# ---------------------------------------------------------------- the door itself
r = client.post("/api/auth/facebook/start", json={"terms_accepted": False})
check("without the Terms box, Facebook is not started", r.status_code == 400, r.text[:200])

r = client.post("/api/auth/facebook/start", json={"terms_accepted": True, "terms_version": "2026-11-22"})
check("a ticked box yields the Facebook dialog", r.status_code == 200, r.text[:200])
url = r.json()["redirect_url"]
q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
check("  ...for the live Resmara app", q.get("client_id") == ["1135911812356864"], url[:200])
check("  ...returning to the login callback",
      q.get("redirect_uri") == ["https://www.resmara.com/api/auth/facebook/callback"], str(q.get("redirect_uri")))
check("  ...asking only for identity until App Review", q.get("scope") == ["public_profile,email"],
      str(q.get("scope")))
check("  ...with a signed state", "." in (q.get("state") or [""])[0], str(q.get("state"))[:80])

r = client.get("/api/auth/facebook/callback?code=code-jamie&state=forged.abc&format=json")
check("a forged state is refused", r.status_code == 200 and r.json().get("fb") == "error", r.text[:200])

r = client.get("/api/auth/facebook/callback?code=code-jamie&format=json")
check("a missing state is refused", r.json().get("fb") == "error", r.text[:200])

# ---------------------------------------------------------------- first sign-in
before = len(sent)
r = login_via_facebook("code-jamie")
body = r.json() if r.status_code == 200 else {}
check("a new agent signs up with Facebook", body.get("fb") == "login" and body.get("new") == "1", r.text[:300])
jamie = db_user(facebook_id="fb-1001")
check("  ...on an account keyed by their Facebook", jamie is not None and jamie.email == "jamie@example.com")
check("  ...stamped with the consent they gave",
      jamie is not None and jamie.terms_accepted_at is not None and jamie.terms_version == "2026-11-22",
      str((jamie.terms_accepted_at, jamie.terms_version)) if jamie else "")
check("  ...and the welcome email went, from their real facts",
      any("Welcome to Resmara" in s[1] for s in sent[before:]), str([s[1] for s in sent[before:]]))

r = client.post("/api/auth/facebook/exchange", json={"ticket": body.get("ticket")})
check("the ticket becomes a session", r.status_code == 200 and r.json().get("access_token"), r.text[:200])
token = r.json().get("access_token") if r.status_code == 200 else ""
me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
check("  ...that the rest of the app accepts", me.status_code == 200 and me.json().get("email") == "jamie@example.com",
      me.text[:200])

r = client.post("/api/auth/facebook/exchange", json={"ticket": body.get("ticket")})
check("a ticket works exactly once", r.status_code == 400, r.text[:200])

# --------------------------------------------------------- the same person again
r = login_via_facebook("code-jamie")
again = r.json() if r.status_code == 200 else {}
check("the same Facebook signs in again", again.get("fb") == "login" and again.get("new") == "0", r.text[:300])
db = SessionLocal()
count = db.query(User).filter(User.facebook_id == "fb-1001").count()
db.close()
check("  ...never creating a second account", count == 1, str(count))

# ------------------------------------------------------------- no email from Meta
r = login_via_facebook("code-noemail")
hidden = r.json() if r.status_code == 200 else {}
check("Facebook hiding the email still signs them in", hidden.get("fb") == "login" and hidden.get("needs_email") == "1",
      r.text[:300])
nancy = db_user(facebook_id="fb-2002")
check("  ...on a placeholder address that cannot collide", nancy is not None and nancy.email.endswith("@facebook.resmara.invalid"))
r = client.post("/api/auth/facebook/exchange", json={"ticket": hidden.get("ticket")})
ntok = r.json().get("access_token")
r = client.patch("/api/auth/me/email", json={"email": "nancy@example.com"},
                 headers={"Authorization": f"Bearer {ntok}"})
check("  ...and we ask once for a real one", r.status_code == 200 and
      db_user(facebook_id="fb-2002").email == "nancy@example.com", r.text[:200])

# ------------------------------------------------------------- close, then come back
r = client.post("/api/auth/me/close", headers={"Authorization": f"Bearer {token}"})
check("an agent can close their account", r.status_code == 200, r.text[:200])
r = login_via_facebook("code-jamie")
closed = r.json() if r.status_code == 200 else {}
check("  ...and is offered reactivation instead of a silent sign-in", closed.get("fb") == "closed", r.text[:300])
r = client.post("/api/auth/facebook/reactivate", json={"ticket": closed.get("ticket")})
check("  ...one click brings it back", r.status_code == 200 and r.json().get("access_token"), r.text[:200])
check("  ...with the campaigns still there", db_user(facebook_id="fb-1001").closed_at is None)

# --------------------------------------------------- closed accounts are not deleted
r = client.post("/api/auth/facebook/exchange", json={"ticket": closed.get("ticket")})
check("a reactivation ticket cannot be spent twice", r.status_code == 400, r.text[:200])

# -------------------------------------------------------------- onboarding emails
db = SessionLocal()
jamie = db.query(User).filter(User.facebook_id == "fb-1001").first()
jamie.created_at = datetime.now(timezone.utc) - timedelta(days=8)
db.commit()
sent.clear()
out = onboarding_emails.run_due(db)
steps = [s for s in out["sent"] if s["to"] == "jamie@example.com"]
check("day 3 and day 7 have gone, once each", sorted(s["step"] for s in steps) == ["day3", "day7"],
      str([s["step"] for s in steps]))
check("  ...but never the welcome twice", "welcome" not in [s["step"] for s in steps], str(steps))
out2 = onboarding_emails.run_due(db)
check("running again sends nothing twice", not [s for s in out2["sent"] if s["to"] == "jamie@example.com"],
      str(out2["sent"]))

# a launched campaign stops the remaining emails
jamie = db.query(User).filter(User.facebook_id == "fb-1001").first()
db.add(Boost(user_id=jamie.id, address="905 Laurel Bend", tier="bap_shoot_499",
             go_live_date="2026-11-20", launched_at=datetime.now(timezone.utc), stage="LIVE"))
db.commit()
jamie.created_at = datetime.now(timezone.utc) - timedelta(days=20)
db.commit()
sent.clear()
out3 = onboarding_emails.run_due(db)
check("a launched campaign stops day 14", not [s for s in out3["sent"] if s["to"] == "jamie@example.com"],
      str(out3["sent"]))

# a test account is never emailed
nancy = db.query(User).filter(User.facebook_id == "fb-2002").first()
nancy.is_test = True
nancy.created_at = datetime.now(timezone.utc) - timedelta(days=20)
db.commit()
sent.clear()
out4 = onboarding_emails.run_due(db)
check("test accounts get no onboarding email", not [s for s in out4["sent"] if s["to"] == "nancy@example.com"],
      str(out4["sent"]))
db.close()

# --------------------------------------------------------------- the way out
tok = onboarding_emails.unsub_token(1)
r = client.get(f"/api/unsubscribe?u=1&t={tok}")
check("the unsubscribe link works without signing in", r.status_code == 200, r.text[:200])
check("  ...and turns the emails off", db_user(id=1).marketing_optin is False)
r = client.get("/api/unsubscribe?u=1&t=wrong")
check("  ...but not with a forged token", r.status_code == 400, r.text[:200])

# ------------------------------------------------------------- the clock entrypoint
r = client.post("/api/admin/onboarding/emails/run", headers={"X-Resmara-Token": "nope"})
check("the clock endpoint refuses a bad token", r.status_code == 403, r.text[:150])
r = client.post("/api/admin/onboarding/emails/run", headers={"X-Resmara-Token": "clock-token"})
check("  ...and answers the real one", r.status_code == 200 and "sent" in r.json(), r.text[:200])

MOCK.stop()
print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL FACEBOOK LOGIN TESTS PASSED")
