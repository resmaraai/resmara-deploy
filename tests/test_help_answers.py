"""Ask Resmara learns: an unanswered question is logged, answered, and served next time.

The chat (`static/help-kb.js`) matches locally against about fifty answers and never calls a
model, so it has exactly two failure modes worth a test: the question it has never seen gets
a shrug (fixed by logging the miss), and the answer the team already wrote lives in a support
reply nobody reads again (fixed by approving a reply as an answer).

The second half of this file is the orange number on the agent's Support button: a team reply
is unread until the agent opens Support, and that state has to be the server's, because the
reply happens while their browser is closed.
"""
import os
import sys
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-help-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"
os.environ["RESMARA_SIGNUP_EMAILS"] = ""
for _key in ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "MAIL_FROM"):
    os.environ.pop(_key, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import mail  # noqa: E402
from app.api import resmara as api  # noqa: E402
from app.db.session import Base, engine, SessionLocal, Event  # noqa: E402
from app.db.migrate import migrate  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


client = TestClient(app)


def login(email, password):
    token = client.post("/api/auth/login", data={"username": email, "password": password}).json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


r = client.post("/api/auth/register", json={"terms_accepted": True, "email": "agent@example.com", "password": "long enough",
                                            "name": "Agent", "invite_code": "beta-code-123"})
check("an agent can register", r.status_code == 201, r.text)
agent = login("agent@example.com", "long enough")

r = client.post("/api/auth/register", json={"terms_accepted": True, "email": "owner@example.com", "password": "long enough",
                                            "name": "Owner"})
check("the operator can register without an invite", r.status_code == 201, r.text)
operator = login("owner@example.com", "long enough")

mail.mail_configured = lambda: False
api.mail.mail_configured = mail.mail_configured

# ---- a question the chat cannot answer is logged, not lost ---------------------------
r = client.post("/api/help/misses", json={"question": "Can I post to TikTok too?"})
check("a miss needs a signed-in agent", r.status_code in (401, 403), r.text)

r = client.post("/api/help/misses", json={"question": "Can I post to TikTok too?"}, headers=agent)
check("the agent's question is logged", r.status_code == 201, r.text)
first_id = r.json().get("id")

r = client.post("/api/help/misses", json={"question": "can i post to tiktok too"},
                headers=agent)
check("the same question twice is one row", r.status_code == 201 and r.json().get("id") == first_id, r.text)
check("and the count goes up", r.json().get("asked_count") == 2, r.text)

r = client.post("/api/help/misses", json={"question": ""}, headers=agent)
check("an empty question is refused", r.status_code == 400, r.text)

r = client.get("/api/help/answers")
check("approved answers are readable without a token", r.status_code == 200, r.text)
check("and start empty", r.json() == [], str(r.json()))

r = client.get("/api/admin/help/misses", headers=agent)
check("an agent cannot read the operator's miss list", r.status_code in (401, 403), r.text)

r = client.get("/api/admin/help/misses", headers=operator)
picked = (r.json().get("items") or [{}])[0]
check("the operator sees the miss", r.status_code == 200 and picked.get("question"), r.text)
check("with who asked", picked.get("asked_by") == "agent@example.com", str(picked))
check("most-asked first is the order the list is in", r.json().get("open") == 1, r.text)

r = client.post("/api/admin/help/answers", headers=agent,
                json={"question": "Can I post to TikTok too?", "answer": "Not yet."})
check("an agent cannot approve an answer", r.status_code in (401, 403), r.text)

r = client.post("/api/admin/help/answers", headers=operator,
                json={"question": "Can I post to TikTok too?",
                      "answer": "Not yet: a campaign publishes to Facebook and Instagram only.",
                      "topic": "Publishing", "keys": "tiktok, other platform",
                      "miss_ids": [first_id]})
check("the operator can approve an answer", r.status_code == 201, r.text)
check("and it closes the miss it answers", r.json().get("miss_ids_closed") == 1, r.text)
answer_id = r.json().get("id")

r = client.get("/api/help/answers")
rows = r.json()
check("the approved answer is served to the chat", len(rows) == 1, str(rows))
row = rows[0] if rows else {}
# The field names are the contract static/help-kb.js reads: {id, q, a, topic, keys[]}.
check("in the shape the chat reads", all(k in row for k in ("id", "q", "a", "topic", "keys")), str(row))
check("with the answer text", "Facebook and Instagram only" in str(row.get("a")), str(row))
check("and its match words split into a list", row.get("keys") == ["tiktok", "other platform"], str(row))

r = client.get("/api/admin/help/misses", headers=operator)
check("the answered miss leaves the waiting list", r.json().get("open") == 0, r.text)

r = client.patch(f"/api/admin/help/answers/{answer_id}", headers=operator, json={"active": False})
check("an answer can be withdrawn", r.status_code == 200 and r.json().get("active") is False, r.text)
check("a withdrawn answer is not served", client.get("/api/help/answers").json() == [], "still served")

# ---- a team reply is unread until the agent opens Support ---------------------------
r = client.post("/api/support", json={"subject": "Day 1 post failed",
                                      "message": "Instagram rejected it."}, headers=agent)
check("the agent raises a request", r.status_code == 201, r.text)
ticket_id = r.json().get("id")

r = client.get("/api/support", headers=agent)
check("a new ticket has nothing unread", r.status_code == 200 and r.json()[0].get("unread_replies") == 0, r.text)

r = client.patch(f"/api/admin/support/{ticket_id}?reply=Try it again now, the token was stale.",
                 headers=operator)
check("the operator replies", r.status_code == 200, r.text)

r = client.get("/api/support", headers=agent)
row = (r.json() or [{}])[0]
check("the reply counts as unread", row.get("unread_replies") == 1, str(row))
msgs = row.get("messages") or []
check("and the reply itself is flagged", any(m.get("unread") for m in msgs), str(msgs))
check("the reply is the last thing said", (msgs[-1] or {}).get("from") == "admin" if msgs else False, str(msgs))
# Engine 11, section 4: a team reply makes the request Answered (the Team room's dropdown can
# say Waiting on you instead, when the team asked the agent something).
check("a reply makes the request Answered", row.get("status") == "answered", str(row.get("status")))

db = SessionLocal()
ev = (db.query(Event).filter(Event.event_type == "ticket_reply_notified")
      .order_by(Event.id.desc()).first())
check("the reply notification is recorded", ev is not None, "no event")
check("and names why no mail went out",
      ev is not None and "mail provider" in str((ev.payload or {}).get("reason")), ev and ev.payload)
db.close()

# Another agent's ticket is not theirs to read, let alone clear.
client.post("/api/auth/register", json={"terms_accepted": True, "email": "other@example.com", "password": "long enough",
                                        "name": "Other", "invite_code": "beta-code-123"})
other = login("other@example.com", "long enough")
r = client.get("/api/support", headers=other)
check("another agent sees no tickets of ours", r.status_code == 200 and r.json() == [], r.text)
check("and clearing read state touches nothing of ours",
      client.post("/api/support/read", headers=other).json().get("marked") == 0,
      "marked rows for a stranger")

r = client.post("/api/support/read", headers=agent)
check("opening Support clears the reply", r.status_code == 200 and r.json().get("marked") == 1, r.text)
r = client.get("/api/support", headers=agent)
check("and the count is zero afterwards", (r.json() or [{}])[0].get("unread_replies") == 0, r.text)

print()
if FAILS:
    print(f"{len(FAILS)} check(s) failed: {FAILS}")
    sys.exit(1)
print("ALL HELP/UNREAD TESTS PASSED")
