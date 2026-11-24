"""Engine 11 (Support): the 1 business day promise, Which listing?, the four statuses, signed reply
emails, the agent replying, auto-close after 7 days and the Team room's reply-by order."""
import os
import tempfile
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-e11-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["RESMARA_SUPPORT_EMAIL"] = "support@resmara.com"

from fastapi.testclient import TestClient  # noqa: E402

from app.core.security import create_access_token  # noqa: E402
from app.db.session import Base, Boost, SessionLocal, SupportTicket, User, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.services import mail, support  # noqa: E402

Base.metadata.create_all(bind=engine)
SENT = []
mail.send_email = lambda to, subject, body: SENT.append((to, subject, body)) or True
mail.mail_configured = lambda: True
checks, failures = 0, 0
PT = ZoneInfo("America/Los_Angeles")


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


def pt(y, m, d, h, mi=0):
    return datetime(y, m, d, h, mi, tzinfo=PT)


def due(sent):
    return support.reply_by(sent).astimezone(PT)


print("[1 business day]")
ok("Monday 10 AM -> Tuesday 5 PM", due(pt(2026, 11, 30, 10)) == pt(2026, 12, 1, 17), due(pt(2026, 11, 30, 10)))
ok("Monday 6 PM -> Wednesday 5 PM (after the cutoff)", due(pt(2026, 11, 30, 18)) == pt(2026, 12, 2, 17))
ok("Friday 4 PM -> Monday 5 PM", due(pt(2026, 12, 4, 16)) == pt(2026, 12, 7, 17))
ok("Friday 6 PM -> Tuesday 5 PM", due(pt(2026, 12, 4, 18)) == pt(2026, 12, 8, 17))
ok("Saturday -> Tuesday 5 PM", due(pt(2026, 12, 5, 11)) == pt(2026, 12, 8, 17))
ok("Thanksgiving doesn't count (Wed 10 AM -> Fri 5 PM)", due(pt(2026, 11, 25, 10)) == pt(2026, 11, 27, 17), due(pt(2026, 11, 25, 10)))
ok("Christmas observed doesn't count (Thu Dec 24 10 AM -> Mon 5 PM)", due(pt(2026, 12, 24, 10)) == pt(2026, 12, 28, 17))
ok("the label reads like a person", support.reply_by_label(support.reply_by(pt(2026, 11, 30, 10)),
                                                         now=pt(2026, 11, 30, 10)) == "Tuesday at 5 PM",
   support.reply_by_label(support.reply_by(pt(2026, 11, 30, 10)), now=pt(2026, 11, 30, 10)))
d = support.reply_by(pt(2026, 11, 30, 10))
ok("past due is 'late'", support.due_state(d, "received", now=d + timedelta(minutes=1)) == "late")
ok("within 2 hours is 'soon'", support.due_state(d, "received", now=d - timedelta(hours=1)) == "soon")
ok("answered requests are never due", support.due_state(d, "answered", now=d + timedelta(days=1)) == "")
ok("older statuses read as the new four", support.label("open") == "Received" and support.label("resolved") == "Closed")

print("[sending a request]")
db = SessionLocal()
agent = User(email="morgan@example.com", hashed_password="x", name="Morgan Ellis")
other = User(email="sam@example.com", hashed_password="x", name="Sam")
admin = User(email="adam@resmara.com", hashed_password="x", name="Adam French", is_admin=True)
db.add_all([agent, other, admin])
db.commit()
mine = Boost(user_id=agent.id, address="1248 Oakridge Drive, Redding, CA")
theirs = Boost(user_id=other.id, address="9 Other St, Austin, TX")
db.add_all([mine, theirs])
db.commit()
H = {"Authorization": "Bearer " + create_access_token({"sub": agent.email})}
A = {"Authorization": "Bearer " + create_access_token({"sub": admin.email})}
client = TestClient(app)

SENT.clear()
r = client.post("/api/support", json={"subject": "Instagram post failed", "message": "Day 3 didn't go out",
                                      "boost_id": mine.id, "page": "campaigns"}, headers=H)
t = r.json()
ok("the request is saved as Received", r.status_code == 201 and t["status"] == "received" and t["status_label"] == "Received", r.text[:300])
ok("  ...with the listing", t.get("boost_id") == mine.id and t.get("address", "").startswith("1248 Oakridge"), t)
ok("  ...the page they were on and the account snapshot", t.get("page") == "campaigns" and t.get("snapshot", {}).get("campaigns") == 1, t)
ok("  ...and the reply-by promise", bool(t.get("reply_by")) and " at 5 PM" in t.get("reply_by_label", ""), t.get("reply_by_label"))
ok("it lands in the shared support inbox", any(s[0] == "support@resmara.com" and f"Resmara support #{t['id']}: Instagram post failed" == s[1]
                                               and "Reply by:" in s[2] and "1 campaign(s)" in s[2] for s in SENT), SENT)
ok("the agent gets the same promise by email", any(s[0] == "morgan@example.com" and "We'll reply by" in s[2] for s in SENT), SENT)
r = client.post("/api/support", json={"subject": "x", "message": "y", "boost_id": theirs.id}, headers=H)
ok("another agent's listing is never attached", r.status_code == 201 and r.json().get("boost_id") is None, r.text[:200])

print("[the team replies]")
SENT.clear()
r = client.patch(f"/api/admin/support/{t['id']}?reply=Reconnect%20Instagram%20and%20click%20Retry.", headers=A)
row = db.get(SupportTicket, t["id"])
db.refresh(row)
ok("a reply makes it Answered", r.status_code == 200 and row.status == "answered", (r.status_code, row.status))
ok("  ...signed with the team member's first name", row.messages[-1].get("by") == "Adam", row.messages[-1])
ok("  ...and emailed to the agent with See the reply", any(s[0] == "morgan@example.com" and "See the reply:" in s[2]
                                                           and "Adam from Resmara" in s[2] for s in SENT), SENT)
r = client.patch(f"/api/admin/support/{t['id']}?status=waiting&reply=Which%20Page%20is%20it%3F", headers=A)
db.refresh(row)
ok("asking them something is Waiting on you", row.status == "waiting")
mine_list = client.get("/api/support", headers=H).json()
ok("the agent sees the plain status", mine_list and any(x["id"] == t["id"] and x["status_label"] == "Waiting on you" for x in mine_list), mine_list)

print("[the agent replies]")
SENT.clear()
r = client.post(f"/api/support/{t['id']}/reply", json={"text": "It's the Redding Homes page"}, headers=H)
db.refresh(row)
ok("their reply puts it back with us", r.status_code == 200 and row.status == "received" and r.json()["reply_by_label"], r.text[:200])
ok("  ...and the inbox hears about it", any(s[0] == "support@resmara.com" and s[1].startswith("Re: Resmara support") for s in SENT), SENT)
r = client.post(f"/api/support/{t['id']}/reply", json={"text": "hi"},
                headers={"Authorization": "Bearer " + create_access_token({"sub": other.email})})
ok("nobody else can reply on it", r.status_code == 404)

print("[Team room order]")
late = SupportTicket(user_id=agent.id, subject="Old one", status="received",
                     reply_by=datetime.now(timezone.utc) - timedelta(hours=3), messages=[])
done = SupportTicket(user_id=agent.id, subject="Done", status="closed", messages=[])
db.add_all([late, done])
db.commit()
rows = client.get("/api/admin/support", headers=A).json()
ok("requests waiting on us come first, oldest reply-by first", rows[0]["subject"] == "Old one" and rows[0]["due"] == "late",
   [(x["subject"], x["status"], x["due"]) for x in rows])
ok("closed ones go to the end", rows[-1]["status"] == "closed", [x["status"] for x in rows])

print("[closes itself after 7 days]")
quiet = SupportTicket(user_id=agent.id, subject="Quiet", status="answered",
                      messages=[{"from": "admin", "text": "Done", "at": (datetime.now(timezone.utc) - timedelta(days=8)).isoformat()}])
fresh = SupportTicket(user_id=agent.id, subject="Fresh", status="answered",
                      messages=[{"from": "admin", "text": "Done", "at": (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()}])
db.add_all([quiet, fresh])
db.commit()
n = support.auto_close(db)
db.refresh(quiet)
db.refresh(fresh)
ok("answered 8 days ago with no reply: Closed", quiet.status == "closed" and n >= 1, (quiet.status, n))
ok("answered 2 days ago: still open", fresh.status == "answered")

print(f"\n{checks - failures}/{checks} passed")
print("ENGINE 11 PASSED" if not failures else "ENGINE 11 FAILED")
raise SystemExit(1 if failures else 0)
