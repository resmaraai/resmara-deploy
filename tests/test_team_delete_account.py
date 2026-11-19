"""Deleting an account from the Team room, through the real endpoints.

Why this exists: "Remove from team" is reversible on purpose (their campaigns are their
business), which left the operator with no way to clear out a test signup, a duplicate or a
spam account. Delete is the other half, and it is the half that can destroy a customer, so
these checks pin all of it: the emailed confirmation, the owner/self refusals, and that the
campaigns, posts, photos and rows actually go - children before parents, files off disk.
"""
import os
import sys
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-teamdelete-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
os.environ["RESMARA_SIGNUP_EMAILS"] = ""
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"
for _key in ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "MAIL_FROM"):
    os.environ.pop(_key, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from datetime import datetime, timedelta  # noqa: E402

from app.db.session import (Asset, Base, Boost, PasswordReset, Post, SessionLocal, User,  # noqa: E402
                            engine)
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


def login(email):
    r = client.post("/api/auth/login", data={"username": email, "password": PASSWORD})
    check(f"{email} can sign in", r.status_code == 200, r.text[:200])
    return {"Authorization": "Bearer " + r.json()["access_token"]}


r = client.post("/api/auth/register", json={"email": "owner@example.com", "password": PASSWORD,
                                            "name": "Owner"})
check("the operator can register", r.status_code == 201, r.text[:200])
operator = login("owner@example.com")

r = client.post("/api/auth/register", json={"email": "temp@example.com", "password": PASSWORD,
                                            "name": "Temp Agent", "invite_code": "beta-code-123"})
check("a member can register", r.status_code == 201, r.text[:200])
member_id = r.json().get("id")
member = login("temp@example.com")

# The member gets console access, so they appear in the Team room at all.
r = client.post("/api/admin/team", headers=operator,
                json={"name": "Temp Agent", "email": "temp@example.com", "access": ["campaigns"]})
check("the operator adds them to the team", r.status_code in (200, 201), r.text[:200])

# ...and they own a campaign with a post and a photo, so delete has something real to remove.
# The rows go in directly: creating a campaign through the API needs a connected Meta account,
# and this test is about what delete removes, not about the launch gate.
db = SessionLocal()
boost = Boost(user_id=member_id, address="742 Evergreen Terrace, Springfield, OR 97403",
              campaign_days=14, ad_budget_usd=50)
db.add(boost)
db.commit()
db.refresh(boost)
boost_id = boost.id
db.add(Post(boost_id=boost_id, day=1, kind="Post", caption="Hello"))
photo_file = "teamdelete-probe.jpg"
db.add(Asset(user_id=member_id, boost_id=boost_id, filename=photo_file,
             url=f"/uploads/{photo_file}", original_name="probe.jpg", kind="photo", data=b"\xff\xd8"))
db.add(PasswordReset(user_id=member_id, token_hash="x" * 64,
                     expires_at=datetime.utcnow() + timedelta(minutes=30)))
db.commit()
db.close()

upload_path = os.path.join(os.environ.get("UPLOAD_DIR", "uploads"), photo_file)
with open(upload_path, "wb") as fh:
    fh.write(b"\xff\xd8")

r = client.get("/api/admin/team", headers=operator)
check("they are listed on the team", any(x.get("id") == member_id for x in r.json()), r.text[:200])
check("the list says how many campaigns they own",
      any(x.get("id") == member_id and x.get("campaigns") == 1 for x in r.json()), r.text[:300])

# A non-super member cannot delete anyone.
r = client.request("DELETE", f"/api/admin/team/{member_id}/account", headers=member,
                  json={"confirm": "temp@example.com"})
check("a team member cannot delete an account", r.status_code == 403, r.text[:200])

# No confirmation, and a wrong one, both refuse - and change nothing.
r = client.request("DELETE", f"/api/admin/team/{member_id}/account", headers=operator)
check("no confirmation is refused", r.status_code == 422, r.text[:200])
r = client.request("DELETE", f"/api/admin/team/{member_id}/account", headers=operator,
                  json={"confirm": "someone-else@example.com"})
check("the wrong email is refused", r.status_code == 422, r.text[:200])
db = SessionLocal()
check("the account still exists after a refused delete",
      db.query(User).filter(User.id == member_id).first() is not None)
db.close()

# The operator cannot delete themselves or another owner.
me = client.get("/api/admin/me", headers=operator)
my_id = (me.json() or {}).get("id") if me.status_code == 200 else None
if my_id is not None:
    r = client.request("DELETE", f"/api/admin/team/{my_id}/account", headers=operator,
                      json={"confirm": "owner@example.com"})
    check("an operator cannot delete their own account", r.status_code == 400, r.text[:200])

# The real delete.
r = client.request("DELETE", f"/api/admin/team/{member_id}/account", headers=operator,
                  json={"confirm": "TEMP@example.com"})
check("the account is deleted", r.status_code == 200, r.text[:300])
body = r.json() if r.status_code == 200 else {}
check("the delete reports what it removed",
      body.get("removed", {}).get("campaigns") == 1 and body.get("removed", {}).get("posts") == 1,
      str(body))

db = SessionLocal()
check("the user row is gone", db.query(User).filter(User.id == member_id).first() is None)
check("their campaign is gone", db.query(Boost).filter(Boost.user_id == member_id).count() == 0)
check("their posts are gone", db.query(Post).filter(Post.boost_id == boost_id).count() == 0)
check("their photos are gone", db.query(Asset).filter(Asset.user_id == member_id).count() == 0)
check("their reset tokens are gone",
      db.query(PasswordReset).filter(PasswordReset.user_id == member_id).count() == 0)
db.close()
check("the photo file is off disk", not os.path.exists(upload_path), upload_path)

r = client.get("/api/admin/team", headers=operator)
check("they are gone from the Team room",
      not any(x.get("id") == member_id for x in r.json()), r.text[:300])

r = client.post("/api/auth/login", data={"username": "temp@example.com", "password": PASSWORD})
check("the deleted account can no longer sign in", r.status_code in (400, 401, 403), r.text[:200])

try:
    os.unlink(upload_path)
except OSError:
    pass

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: {FAILS}")
    sys.exit(1)
print("ALL TEAM DELETE-ACCOUNT CHECKS PASSED")
