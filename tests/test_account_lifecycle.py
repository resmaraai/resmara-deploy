"""Password recovery and account closing, through the real endpoints.

Why this exists: the public site used to hand a working reset token back in the response
whenever no mail provider was configured — which is the same as handing anyone the ability to
take over any account they know the address of. These checks pin the closed shape: the
request never returns a token, the operator can mint a link by hand instead (so a locked-out
customer is not stuck), the link really works once, and a customer can close their own
account but only with the password typed again.
"""
import os
import sys
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-lifecycle-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
# Empty, not absent: the repo's .env closes signup, and an env var wins over the dotenv file.
os.environ["RESMARA_SIGNUP_EMAILS"] = ""
# An operator address in ADMIN_EMAILS keeps the gate shut for strangers, so the test agent
# gets in the way a partner would: with the invite code.
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"
for _key in ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "MAIL_FROM"):
    os.environ.pop(_key, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import Base, engine, SessionLocal, User  # noqa: E402
from app.db.migrate import migrate  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


client = TestClient(app)

PASSWORD = "correct horse battery"
NEW_PASSWORD = "another long password"

r = client.post("/api/auth/register", json={"email": "agent@example.com", "password": PASSWORD,
                                            "name": "Agent", "invite_code": "beta-code-123"})
check("an agent can register", r.status_code == 201, r.text)
agent = r.json()

r = client.post("/api/auth/register", json={"email": "owner@example.com", "password": PASSWORD,
                                            "name": "Owner"})
check("the operator can register", r.status_code == 201, r.text)
check("an allowlisted owner is an admin", r.json().get("is_admin") is True, r.text)
admin_token = client.post("/api/auth/login",
                          data={"username": "owner@example.com", "password": PASSWORD}).json()["access_token"]
admin_headers = {"Authorization": f"Bearer {admin_token}"}

# ---- a short password is refused, not stored -----------------------------------------
r = client.post("/api/auth/register", json={"email": "short@example.com", "password": "abc",
                                            "invite_code": "beta-code-123"})
check("a 3-character password is refused", r.status_code == 400, r.text)

# ---- the reset request must not hand back a token -------------------------------------
r = client.post("/api/auth/password-reset/request?email=agent@example.com")
check("a reset request answers 200", r.status_code == 200, r.text)
body = r.json()
check("the answer carries no reset_token", "reset_token" not in body, str(body))
check("with no mail provider the answer says so", body.get("delivery") == "not_configured", str(body))
check("and tells the customer to ask support", "support" in (body.get("detail") or "").lower(), str(body))

r = client.post("/api/auth/password-reset/request?email=nobody@example.com")
check("an unknown address answers the same way", r.status_code == 200 and r.json().get("delivery") == "not_configured",
      r.text)

# ---- the operator can mint a link by hand --------------------------------------------
r = client.post(f"/api/admin/users/{agent['id']}/reset-link")
check("a reset link is refused without an operator session", r.status_code in (401, 403), r.text)

r = client.post(f"/api/admin/users/{agent['id']}/reset-link", headers=admin_headers)
check("an operator gets a reset link", r.status_code == 200, r.text)
link = r.json().get("link", "")
check("the link points at the public reset page", "/reset?token=" in link, link)
check("nothing was emailed when mail is off", r.json().get("emailed") is False, r.text)

token = link.split("token=", 1)[-1]

# ---- the link works exactly once ------------------------------------------------------
r = client.post(f"/api/auth/password-reset/confirm?token={token}&new_password={NEW_PASSWORD}")
check("the link changes the password", r.status_code == 200, r.text)
r = client.post("/api/auth/login", data={"username": "agent@example.com", "password": NEW_PASSWORD})
check("the new password signs in", r.status_code == 200, r.text)
agent_token = r.json()["access_token"]
r = client.post("/api/auth/login", data={"username": "agent@example.com", "password": PASSWORD})
check("the old password no longer signs in", r.status_code in (400, 401), r.text)
r = client.post(f"/api/auth/password-reset/confirm?token={token}&new_password={'third long password'}")
check("the same link cannot be used twice", r.status_code == 400, r.text)

# ---- closing the account -------------------------------------------------------------
agent_headers = {"Authorization": f"Bearer {agent_token}"}
r = client.delete(f"/api/auth/me?password=wrong password", headers=agent_headers)
check("closing an account needs the right password", r.status_code == 400, r.text)

r = client.delete("/api/auth/me?password=wrong", headers=agent_headers)
check("a wrong password does not close the account", r.status_code == 400, r.text)

r = client.delete(f"/api/auth/me?password={NEW_PASSWORD}", headers=agent_headers)
check("the customer can close their own account", r.status_code == 200, r.text)

r = client.post("/api/auth/login", data={"username": "agent@example.com", "password": NEW_PASSWORD})
check("a closed account cannot sign in", r.status_code in (400, 401), r.text)

db = SessionLocal()
row = db.query(User).filter(User.id == agent["id"]).first()
check("the closed account keeps its row for the payment record", row is not None)
check("the email address is not kept", row and "agent@example.com" not in (row.email or ""), row and row.email)
check("the name is not kept", row and row.name == "Deleted account", row and row.name)
check("the brand profile is not kept", row and not row.brand, row and str(row.brand))
db.close()

r = client.delete(f"/api/auth/me?password={PASSWORD}", headers=admin_headers)
check("an operator account cannot be closed from the site", r.status_code == 400, r.text)

# ---- the reset page itself is served --------------------------------------------------
r = client.get("/reset?token=whatever")
check("the reset link opens a real page", r.status_code == 200 and "<html" in r.text.lower(), r.status_code)

print()
if FAILS:
    print(f"{len(FAILS)} check(s) failed: {FAILS}")
    sys.exit(1)
print("all checks passed")
