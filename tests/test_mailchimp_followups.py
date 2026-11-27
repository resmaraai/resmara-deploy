"""Every follow-up email goes through Mailchimp so each one is tracked (Adam, 25 Nov).

The tips box at Facebook sign-up is saved; unticked means never on the marketing list. Tags switch
(new / has run a campaign / past client / Run it until it sells) so the right series runs. Open,
click and bounce rates are read per email. The app's own follow-ups stop once Mailchimp is connected.
"""
import asyncio
import os
import tempfile
from datetime import datetime, timedelta

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-mc-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["SECRET_KEY"] = "test-secret-key-for-mailchimp-followups-00"
for k in ("MAILCHIMP_API_KEY", "MAILCHIMP_AUDIENCE_ID"):
    os.environ.pop(k, None)

from app.db.session import Base, Boost, Event, SessionLocal, User, engine  # noqa: E402
from app.services import mailchimp, mail, onboarding_emails  # noqa: E402

Base.metadata.create_all(bind=engine)
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({str(extra)[:300]})"))
    if not cond:
        failures += 1


db = SessionLocal()
sent_mail = []
mail.send_email = lambda *a, **k: sent_mail.append(a) or True


def user(email, **kw):
    u = User(email=email, hashed_password="x", name="Jamie Agent", **kw)
    db.add(u)
    db.commit()
    return u


print("[Tags]")
new = user("new@realty.com", created_at=datetime.utcnow())
client_ = user("client@realty.com")
db.add(Boost(user_id=client_.id, address="1 A St", paid_at=datetime.utcnow() - timedelta(days=5)))
past = user("past@realty.com")
db.add(Boost(user_id=past.id, address="2 B St", paid_at=datetime.utcnow() - timedelta(days=90)))
until = user("until@realty.com")
db.add(Boost(user_id=until.id, address="3 C St", paid_at=datetime.utcnow() - timedelta(days=90), until_sold=True))
db.commit()
ok("no campaign yet", mailchimp.tags_for(db, new) == ["signed up, no campaign yet"], mailchimp.tags_for(db, new))
ok("ran one recently", mailchimp.tags_for(db, client_) == ["has run a campaign"])
ok("nothing for 60 days is a past client", mailchimp.tags_for(db, past) == ["past client"], mailchimp.tags_for(db, past))
ok("Run it until it sells is never a past client",
   mailchimp.tags_for(db, until) == ["has run a campaign", "Run it until it sells"], mailchimp.tags_for(db, until))

print("[The list]")
os.environ["MAILCHIMP_API_KEY"] = "abc-us16"
os.environ["MAILCHIMP_AUDIENCE_ID"] = "028606916a"
calls = []


def fake_request(path, params=None, method="GET", json=None):
    calls.append((method, path, json))
    if path.endswith("/members") and method == "GET":
        return {"members": [{"email_address": "client@realty.com", "status": "subscribed", "tags": []},
                            {"email_address": "optout@realty.com", "status": "subscribed", "tags": []}],
                "total_items": 2}, ""
    if path == "/reports":
        return {"reports": [
            {"id": "r1", "campaign_title": "Welcome — day 0", "emails_sent": 100, "send_time": datetime.utcnow().isoformat(),
             "unsubscribed": 1, "opens": {"unique_opens": 49}, "clicks": {"unique_clicks": 14},
             "bounces": {"hard_bounces": 1, "soft_bounces": 1, "syntax_errors": 0}}]}, ""
    if "/activity" in path:
        return {"activity": []}, ""
    return {}, ""


mailchimp._request = fake_request
optout = user("optout@realty.com", marketing_optin=False)
result = mailchimp.sync(db)
ok("the sync runs", result["synced"], result)
tag_calls = [c for c in calls if c[1].endswith("/tags")]
client_tags = [c for c in tag_calls if c[1].split("/")[-2] == mailchimp.member_hash("client@realty.com")][0][2]["tags"]
ok("tags are switched: the one that fits on, the rest off",
   {t["name"]: t["status"] for t in client_tags}["has run a campaign"] == "active"
   and {t["name"]: t["status"] for t in client_tags}["signed up, no campaign yet"] == "inactive", client_tags)
ok("someone who unticked the box is marked unsubscribed, never subscribed",
   any(c[0] == "PATCH" and mailchimp.member_hash("optout@realty.com") in c[1] and c[2] == {"status": "unsubscribed"} for c in calls)
   and not any(c[0] == "PUT" and mailchimp.member_hash("optout@realty.com") in c[1] for c in calls))
ok("  ...and counted", result["unsubscribed"] == 1, result)

print("[Open, click and bounce rates]")
rows, _ = mailchimp.reports()
r = mailchimp.rates(rows)
ok("bounces are read", r["bounced"] == 2, r)
ok("open rate is of emails delivered", r["open_rate"] == 50.0, r)
ok("click rate", r["click_rate"] == round(100 * 14 / 98, 1), r)
ok("bounce rate is of emails sent", r["bounce_rate"] == 2.0, r)
ok("nothing sent means no rate, not 0%", mailchimp.rates([])["open_rate"] is None)
ok("no click is no click (credit is never given by mistake)",
   mailchimp.clicked_since("client@realty.com", datetime.utcnow() - timedelta(days=7)) is False)

print("[Follow-ups move to Mailchimp]")
calls.clear()
answer = onboarding_emails.send_welcome(new, db)
ok("a new sign-up goes on the list instead of getting the app's welcome",
   answer.get("reason") == "mailchimp" and answer.get("list") == "added" and not sent_mail, answer)
ok("  ...tagged 'signed up, no campaign yet'",
   any(c[1].endswith("/tags") and {"name": "signed up, no campaign yet", "status": "active"} in c[2]["tags"] for c in calls))
ok("the app sends no check-ins once Mailchimp is connected",
   onboarding_emails.run_due(db).get("owner") == "mailchimp" and not sent_mail)
for k in ("MAILCHIMP_API_KEY", "MAILCHIMP_AUDIENCE_ID"):
    os.environ.pop(k, None)
ok("until it is connected, the app's emails keep going", onboarding_emails.run_due(db).get("owner") is None)

print("[The tips box at Facebook sign-up]")
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.services import facebook_login as fb  # noqa: E402
fb.login_configured = lambda: True
fb.dialog_url = lambda state: "https://facebook.example/dialog"
c = TestClient(app)
r = c.post("/api/auth/facebook/start", json={"terms_accepted": True, "marketing_optin": False})
ev = db.query(Event).filter(Event.event_type == "facebook_signup_context").order_by(Event.id.desc()).first()
ok("unticked is saved with the sign-up", r.status_code == 200 and ev and ev.payload.get("marketing") is False,
   (r.status_code, r.text[:200], ev and ev.payload))
r = c.post("/api/auth/facebook/start", json={"terms_accepted": True})
ev = db.query(Event).filter(Event.event_type == "facebook_signup_context").order_by(Event.id.desc()).first()
ok("left ticked is a yes", ev.payload.get("marketing") is True, ev.payload)

print(f"\n{checks - failures}/{checks} passed")
print("MAILCHIMP FOLLOW-UPS PASSED" if not failures else "MAILCHIMP FOLLOW-UPS FAILED")
raise SystemExit(1 if failures else 0)
