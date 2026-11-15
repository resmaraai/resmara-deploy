"""The Team room's back end: who may read what, and that the console's data is real.

Why this file exists: the console draws its sidebar from the account, but the sidebar is a
courtesy. These checks hold the two rules that make the room safe to give to a colleague:

  * **The server refuses, not the page.** A granted account reaches exactly its groups and gets
    a 403 for the rest, and an account with no grant reaches nothing. Removing someone from the
    team takes the access away and leaves their own customers' campaigns alone.
  * **The figures come from our rows.** The finance chart is built from paid orders, the fail log
    from real failed posts, and a page whose third party is not connected says so instead of
    printing a zero.

Runs hermetically: temp sqlite DB, no network (the model and PageSpeed calls are refused before
they leave), no real install touched.

Run:  cd /Users/dan/resmara && venv/bin/python tests/test_team_room.py
"""

import os
import tempfile
from datetime import datetime, timedelta

# --- environment BEFORE the app is imported (config reads env at import time) ---
_tmp = tempfile.NamedTemporaryFile(prefix="resmara-team-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@resmara.com"
os.environ["RESMARA_PUBLISH_TOKEN"] = "machine-token-for-the-clock"

import sys                                                             # noqa: E402

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient                              # noqa: E402

from app.core.config import settings                                   # noqa: E402
from app.core.security import get_password_hash                        # noqa: E402
from app.db.session import (Base, Boost, Order, Post, SessionLocal,     # noqa: E402
                            User, engine)
from app.main import app                                               # noqa: E402
from app.services import llm, team_access                              # noqa: E402

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


Base.metadata.create_all(bind=engine)

PW = "Hunter2Hunter2"
db = SessionLocal()

owner = User(email="owner@resmara.com", name="Dan", hashed_password=get_password_hash(PW),
             is_active=True, is_admin=True, subscription_status="active",
             last_login=datetime.utcnow())
campaigns_only = User(email="campaigns@resmara.com", name="Camp", hashed_password=get_password_hash(PW),
                      is_active=True, team_access=["campaigns"], last_login=datetime.utcnow())
super_only = User(email="super@resmara.com", name="Super", hashed_password=get_password_hash(PW),
                  is_active=True, team_super_admin=True, team_access=[], last_login=datetime.utcnow())
customer = User(email="customer@example.com", name="Client", hashed_password=get_password_hash(PW),
                is_active=True, subscription_status="active")
for person in (owner, campaigns_only, super_only, customer):
    db.add(person)
db.commit()

# A customer with a campaign of their own: removing them from the team must not touch it.
client_boost = Boost(user_id=customer.id, address="12 Test St", stage="LIVE")
db.add(client_boost)
db.commit()
db.refresh(client_boost)
CUSTOMER_ID = customer.id
OWNER_ID = owner.id
MEMBER_ID = None

# One paid order and one abandoned checkout, so the finance chart has something real to show.
db.add(Order(user_id=customer.id, boost_id=client_boost.id, amount_cents=299,
             status="paid", paid_at=datetime.utcnow() - timedelta(days=1)))
db.add(Order(user_id=customer.id, boost_id=client_boost.id, amount_cents=299,
             status="pending", created_at=datetime.utcnow() - timedelta(days=1)))
db.add(Post(boost_id=client_boost.id, day=1, slot=1, publish_status="failed",
            failure_kind="connection", last_error="token expired",
            failure_note="Meta rejected the photo",
            fail_log=[{"at": datetime.utcnow().isoformat(), "error": "token expired",
                       "attempt": 4, "kind": "connection"}]))
db.commit()
db.close()


def headers(email):
    client = TestClient(app)
    response = client.post("/api/auth/login", data={"username": email, "password": PW})
    assert response.status_code == 200, response.text[:200]
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


# ---------------------------------------------------------------- who may read what
print("\n[the server refuses, the sidebar is only a courtesy]")
cust = TestClient(app, headers=headers("customer@example.com"))
for path in ("/api/admin/campaigns", "/api/admin/connections", "/api/admin/activity",
             "/api/admin/team", "/api/admin/finance", "/api/admin/finance/daily"):
    r = cust.get(path)
    ok(f"an account with no grant is refused {path}", r.status_code == 403, r.status_code)

camp = TestClient(app, headers=headers("campaigns@resmara.com"))
ok("a granted group is served", camp.get("/api/admin/campaigns").status_code == 200)
ok("another group is refused", camp.get("/api/admin/finance").status_code == 403)
ok("the team page is refused to a non-super", camp.get("/api/admin/team").status_code == 403)
ok("the overview is still there for anyone in the room", camp.get("/api/admin/metrics").status_code == 200)

sup = TestClient(app, headers=headers("super@resmara.com"))
ok("a super admin without groups still reaches them", sup.get("/api/admin/finance").status_code == 200)

own = TestClient(app, headers=headers("owner@resmara.com"))
ok("an owner reaches everything", own.get("/api/admin/finance").status_code == 200)

# ---------------------------------------------------------------- the team page
print("\n[the team page: who is in, and what they may read]")
rows = own.get("/api/admin/team")
ok("the team lists only accounts with access", rows.status_code == 200, rows.text[:150])
emails = [r["email"] for r in rows.json()] if rows.status_code == 200 else []
ok("an owner is in it", "owner@resmara.com" in emails, emails)
ok("a granted member is in it", "campaigns@resmara.com" in emails, emails)
ok("a plain customer is not", "customer@example.com" not in emails, emails)
ok("a super admin is marked as one",
   any(r["email"] == "super@resmara.com" and r["super_admin"] for r in (rows.json() if rows.status_code == 200 else [])))

created = own.post("/api/admin/team", json={"name": "New Person", "email": "new@resmara.com",
                                            "access": ["money"], "super_admin": False})
ok("a new member is created", created.status_code == 200, created.text[:200])
body = created.json() if created.status_code == 200 else {}
ok("with a link to choose their own password", bool(body.get("invite_link")), body)
ok("and says plainly that no email went out", body.get("emailed") is False, body)
ok("no password is ever set by the operator", "password" not in created.text.lower())

promoted = own.post("/api/admin/team", json={"email": "customer@example.com", "access": ["campaigns"]})
ok("an existing customer is promoted, not duplicated", promoted.status_code == 200 and promoted.json().get("created") is False,
   promoted.text[:200])

patched = own.patch(f"/api/admin/team/{body.get('id')}", json={"access": ["money", "system"]})
ok("the groups are saved", patched.status_code == 200 and sorted(patched.json()["access"]) == ["money", "system"],
   patched.text[:200])
ok("an unknown group is dropped, not stored",
   own.patch(f"/api/admin/team/{body.get('id')}", json={"access": ["money", "space-travel"]}).json()["access"] == ["money"])

removed = own.delete(f"/api/admin/team/{CUSTOMER_ID}")
ok("a customer can be removed from the team", removed.status_code == 200, removed.text[:200])
db = SessionLocal()
kept = db.query(User).filter(User.id == CUSTOMER_ID).first()
ok("their account survives", kept is not None)
ok("their campaign survives", db.query(Boost).filter(Boost.user_id == CUSTOMER_ID).count() == 1)
ok("only the access is gone", not kept.team_access and not kept.is_active or kept.team_access == [])
db.close()
ok("an owner cannot be removed", own.delete(f"/api/admin/team/{OWNER_ID}").status_code == 400)
ok("nobody can remove themselves", own.delete(f"/api/admin/team/{OWNER_ID}").status_code != 200)
ok("an operator cannot be made a plain member",
   own.patch(f"/api/admin/team/{OWNER_ID}", json={"super_admin": False}).status_code == 400)

# ---------------------------------------------------------------- the figures
print("\n[the console's figures come from our own rows]")
campaigns = own.get("/api/admin/campaigns").json()
ok("campaigns is the list the table draws", isinstance(campaigns, list) and len(campaigns) == 1, str(campaigns)[:200])
ok("with the agent's name on the row", campaigns and campaigns[0].get("agent_name") == "Client", str(campaigns)[:200])
detail = own.get(f"/api/admin/campaigns/{campaigns[0]['id']}").json()
ok("a campaign opens with its posts", len(detail.get("posts") or []) == 1, str(detail)[:200])
ok("and the reason it failed is on the post",
   (detail.get("posts") or [{}])[0].get("reason") == "Meta rejected the photo", str(detail.get("posts"))[:200])
failed = own.get("/api/admin/posts/failed").json()
ok("the fail log lists the post", len(failed) == 1, str(failed)[:200])
ok("with every attempt kept",
   bool((failed or [{}])[0].get("fail_log")), str(failed)[:200])

daily = own.get("/api/admin/finance/daily?days=7").json()
ok("the finance chart has one row per day", len(daily.get("days") or []) == 7, len(daily.get("days") or []))
ok("the paid order is in it", round(daily.get("total_usd") or 0, 2) == 2.99, daily.get("total_usd"))
ok("the abandoned checkout is counted, not dropped",
   sum(d.get("unfinished", 0) for d in daily.get("days") or []) == 1)

releases = own.get("/api/admin/releases")
ok("releases answers even with no GitHub token", releases.status_code == 200, releases.text[:150])
ok("and says it is not connected rather than empty",
   releases.json().get("connected") is False, str(releases.json())[:200])

check = own.get("/api/admin/system-check").json()
names = [c["name"] for c in check.get("checks") or []]
ok("the system check runs its checks", len(names) >= 4, names)
ok("a check that cannot run says so",
   any(c["status"] in ("warn", "fail") for c in check["checks"]), check["checks"][:3])

machine = TestClient(app).get("/api/admin/system-check",
                              headers={"X-Resmara-Token": "machine-token-for-the-clock"})
ok("the clock can call the check without a login", machine.status_code == 200, machine.status_code)
ok("a wrong machine token is refused",
   TestClient(app).get("/api/admin/system-check", headers={"X-Resmara-Token": "nope"}).status_code == 403)

# ---------------------------------------------------------------- the chat
print("\n[the chat answers from the approved library, or admits it cannot]")
no_library = cust.post("/api/help/ask", json={"question": "How do I connect my Facebook page?"})
ok("a question with an empty library falls back", no_library.status_code in (200, 401, 403), no_library.status_code)
if no_library.status_code == 200:
    ok("and never invents an answer", no_library.json().get("sure") is False, no_library.json())

original = llm.chat_json
async def broken(*args, **kwargs):
    raise RuntimeError("no model")
llm.chat_json = broken
try:
    with_library = own.post("/api/help/ask", json={"question": "How do I connect my Facebook page?"})
    ok("a model failure is a fallback, not a 500", with_library.status_code == 200, with_library.status_code)
finally:
    llm.chat_json = original

# ---------------------------------------------------------------- the mapping itself
print("\n[the six groups the Team page offers]")
ok("the page's six groups are the module's six", list(team_access.GROUPS) ==
   ["build", "agents", "campaigns", "money", "business", "system"], list(team_access.GROUPS))
ok("a page name still maps to its group", team_access.sanitise_access(["finance"]) == ["money"])
ok("junk is dropped", team_access.sanitise_access(["money", "admin"]) == ["money"])

print()
if failures:
    print(f"{failures} of {checks} FAILED")
    sys.exit(1)
print(f"{checks} checks, 0 failed.\nALL TEAM ROOM TESTS PASSED")
