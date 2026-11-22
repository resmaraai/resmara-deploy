"""Team-marked test accounts (PR #17, 21 Nov 2026).

What this proves, in the customer's terms:

  * the team can mark any account as a test account from Accounts, and unmark it;
  * a marked account stays in the Accounts list, tagged is_test, so nothing disappears;
  * every number the Team room shows leaves it out: Overview/Campaigns (live, by stage,
    real), revenue, Finance customers and paid campaigns, and Marketing sign-ups and paying;
  * its campaigns are tagged is_test on the Campaigns list, so Growth can skip them;
  * accounts on test emails are still caught without being marked.

Run:
    cd /Users/dan/resmara && PYTHONPATH=. venv/bin/python tests/test_test_accounts.py
"""
import os
import sys
import tempfile
from datetime import datetime, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-test-accounts-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@resmara-real.com"
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"
os.environ["RESMARA_SIGNUP_EMAILS"] = ""
for _key in ("RESEND_API_KEY", "SMTP_HOST", "OPENAI_API_KEY", "STRIPE_SECRET_KEY"):
    os.environ.pop(_key, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db.session import Base, engine, SessionLocal, Boost, Order, User  # noqa: E402
from app.db.migrate import migrate  # noqa: E402
from app.core.testdata import is_test_user, test_user_ids  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()
client = TestClient(app)
FAILS = []


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


def register(email, name):
    client.post("/api/auth/register", json={"email": email, "password": "long enough",
                                           "name": name, "invite_code": "beta-code-123"})


register("owner@resmara-real.com", "Owner")
register("mari@truenorth-realty.com", "Mari McCurdy")
register("coggins@bapdigital-demo.com", "Coggins Demo")     # a real-looking email: only marking catches it
register("smoke123@example.com", "Smoke")                     # caught by the email rule

db = SessionLocal()
users = {u.email: u for u in db.query(User).all()}
owner = users["owner@resmara-real.com"]
owner.is_admin = True
now = datetime.now(timezone.utc)
for email, address in (("mari@truenorth-realty.com", "1248 Oakridge Drive"),
                       ("coggins@bapdigital-demo.com", "893 Coggins")):
    b = Boost(user_id=users[email].id, address=address, go_live_date="2026-11-16", campaign_days=14,
              ad_budget_usd=50.0, stage="LIVE", paid_at=now, launched_at=now)
    db.add(b)
    db.flush()
    db.add(Order(user_id=users[email].id, boost_id=b.id, status="paid", amount_cents=4900,
                 currency="usd", paid_at=now))
db.commit()
COGGINS = users["coggins@bapdigital-demo.com"].id
db.close()

token = client.post("/api/auth/login", data={"username": "owner@resmara-real.com",
                                            "password": "long enough"}).json()["access_token"]
admin = {"Authorization": f"Bearer {token}"}


def snapshot():
    m = client.get("/api/admin/metrics", headers=admin).json()
    f = client.get("/api/admin/finance", headers=admin).json()
    return m, f


m, f = snapshot()
check("before marking: 2 live campaigns", m["campaigns"]["live"] == 2)
check("before marking: 2 paid customers in Finance", f["actuals"]["customers"] == 2)
check("before marking: revenue counts both", m["revenue"]["paid_orders"] == 2)

r = client.patch(f"/api/admin/users/{COGGINS}/test", headers=admin, json={"is_test": True})
check("mark as test account", r.status_code == 200 and r.json()["is_test"] is True)

users_list = client.get("/api/admin/users", headers=admin).json()
row = next(u for u in users_list if u["id"] == COGGINS)
check("still listed in Accounts, tagged", row["is_test"] is True)
smoke = next(u for u in users_list if u["email"].startswith("smoke"))
check("test email still caught without marking", smoke["is_test"] is True)

m, f = snapshot()
check("after: live campaigns leave it out", m["campaigns"]["live"] == 1)
check("after: stage counts leave it out", m["campaigns"]["by_stage"].get("LIVE") == 1)
check("after: real campaigns leave it out", m["campaigns"]["real"] == 1)
check("after: revenue leaves it out", m["revenue"]["paid_orders"] == 1 and m["revenue"]["paid_cents"] == 4900)
check("after: Finance customers leave it out", f["actuals"]["customers"] == 1)
check("after: Finance paid campaigns leave it out", f["actuals"]["paid_campaigns"] == 1)

camps = client.get("/api/admin/campaigns", headers=admin).json()
check("its campaign is tagged is_test", next(c for c in camps if c["address"] == "893 Coggins")["is_test"] is True)
check("a real campaign is not", next(c for c in camps if c["address"] == "1248 Oakridge Drive")["is_test"] is False)

mk = client.get("/api/admin/marketing", headers=admin)
if mk.status_code == 200:
    body = mk.json()
    found = []
    def walk(x):
        if isinstance(x, dict):
            if "paying" in x: found.append(x["paying"])
            for v in x.values(): walk(v)
        elif isinstance(x, list):
            for v in x: walk(v)
    walk(body)
    check("Marketing paying agents leave it out", found and found[0] == 1)
else:
    check("Marketing answers", False)

r = client.patch(f"/api/admin/users/{COGGINS}/test", headers=admin, json={"is_test": False})
check("unmark makes it real again", r.status_code == 200 and r.json()["is_test"] is False)
m, f = snapshot()
check("after unmarking: counted again", m["campaigns"]["live"] == 2 and f["actuals"]["customers"] == 2)

r = client.patch("/api/admin/users/99999/test", headers=admin, json={"is_test": True})
check("unknown account is a 404", r.status_code == 404)

agent_token = client.post("/api/auth/login", data={"username": "mari@truenorth-realty.com",
                                                  "password": "long enough"}).json()["access_token"]
r = client.patch(f"/api/admin/users/{COGGINS}/test", headers={"Authorization": f"Bearer {agent_token}"},
                 json={"is_test": True})
check("an agent can't mark accounts", r.status_code in (401, 403))

print()
print("ALL PASSED" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
