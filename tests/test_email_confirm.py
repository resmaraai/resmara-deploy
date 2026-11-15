"""Email confirmation before the first sign-in (owner item 8).

The rule: sign-up takes first name, last name, email, password (invite code behind a link), and
"email confirmation before first sign-in". The part that has to be honest is what happens on a
deploy with no mail provider - locking a beta tester out of an inbox nothing will ever be sent to
is worse than letting them in, so those accounts are confirmed on the spot and the response says
the email did not go out. These tests cover both paths, the resend, and a used link.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_DIR = tempfile.mkdtemp(prefix="confirm-")
os.environ["RESMARA_DB"] = os.path.join(DB_DIR, "app.db")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(DB_DIR, 'app.db')}"
os.environ["RESMARA_UPLOAD_DIR"] = os.path.join(DB_DIR, "uploads")
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"

from fastapi.testclient import TestClient  # noqa: E402

from app.db.session import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.services import mail  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def register(client, email, name="Agent"):
    return client.post("/api/auth/register", json={"email": email, "password": "long enough",
                                                   "name": name, "invite_code": "beta-code-123"})


with TestClient(app) as client:
    print("=== with no mail provider, nobody is locked out ===")
    r = register(client, "nopost@example.com")
    check("registration works", r.status_code == 201, r.text[:200])
    login = client.post("/api/auth/login", data={"username": "nopost@example.com",
                                                 "password": "long enough"})
    check("  ...and they can sign in at once", login.status_code == 200, login.text[:200])
    check("  ...because nothing was sent to confirm", mail.provider() == "", mail.provider())

    print("\n=== when the email does go out, the address has to be proved first ===")
    sent = []

    def fake_send(to, subject, body, *a, **k):
        sent.append({"to": to, "subject": subject, "body": body})
        return True

    original = mail.send_email
    mail.send_email = fake_send
    try:
        r = register(client, "please@example.com")
        check("registration still works", r.status_code == 201, r.text[:150])
        check("  ...one email was sent", len(sent) == 1, str(len(sent)))
        check("  ...with a confirmation link in it",
              "/confirm?token=" in sent[0]["body"], sent[0]["body"][:200])
        token = sent[0]["body"].split("/confirm?token=")[1].split()[0]
        check("  ...and the subject says what it is", "Confirm" in sent[0]["subject"])

        blocked = client.post("/api/auth/login", data={"username": "please@example.com",
                                                       "password": "long enough"})
        check("sign-in is refused until it is confirmed", blocked.status_code == 403,
              str(blocked.status_code))
        check("  ...with a message that says to check the inbox",
              "Confirm your email" in blocked.text, blocked.text[:200])

        print("\n=== the link confirms once ===")
        ok = client.get(f"/api/auth/confirm?token={token}")
        check("the link confirms the address", ok.status_code == 200 and ok.json()["ok"], ok.text[:150])
        then = client.post("/api/auth/login", data={"username": "please@example.com",
                                                    "password": "long enough"})
        check("  ...and now they can sign in", then.status_code == 200, then.text[:150])
        again = client.get(f"/api/auth/confirm?token={token}")
        check("  ...the same link cannot be used twice", again.status_code == 400, again.text[:150])

        print("\n=== a new link is only sent when one is needed ===")
        dup = client.post("/api/auth/confirm/resend?email=please@example.com")
        check("an already-confirmed address is not spammed", dup.status_code == 200
              and len(sent) == 1, str(len(sent)))
        unknown = client.post("/api/auth/confirm/resend?email=nobody@example.com")
        check("an unknown address does not reveal that it is unknown",
              unknown.status_code == 200 and unknown.json()["delivery"] == "sent",
              unknown.text[:150])

        print("\n=== the token is stored hashed, not as a working link ===")
        r2 = register(client, "hashed@example.com")
        db = SessionLocal()
        from app.db.session import User
        row = db.query(User).filter(User.email == "hashed@example.com").first()
        token2 = sent[-1]["body"].split("/confirm?token=")[1].split()[0]
        check("the column does not hold the token itself",
              row.confirm_token_hash != token2, str(row.confirm_token_hash)[:20])
        check("  ...it holds a hash", row.confirm_token_hash and len(row.confirm_token_hash) >= 32,
              str(row.confirm_token_hash)[:20])
        db.close()

        print("\n=== an expired link is refused with a way forward ===")
        from datetime import datetime, timedelta, timezone
        db = SessionLocal()
        row = db.query(User).filter(User.email == "hashed@example.com").first()
        row.confirm_sent_at = datetime.now(timezone.utc) - timedelta(hours=49)
        db.commit()
        db.close()
        old = client.get(f"/api/auth/confirm?token={token2}")
        check("49 hours later the link is dead", old.status_code == 400, old.text[:150])
        check("  ...and it says to ask for a new one", "expired" in old.text.lower(), old.text[:150])
        fresh = client.post("/api/auth/confirm/resend?email=hashed@example.com")
        check("  ...which the resend does", fresh.status_code == 200
              and fresh.json()["delivery"] == "sent", fresh.text[:150])
        new_token = sent[-1]["body"].split("/confirm?token=")[1].split()[0]
        check("  ...and the new link works",
              client.get(f"/api/auth/confirm?token={new_token}").status_code == 200)
    finally:
        mail.send_email = original

    print("\n=== the page exists so the link is not a dead end ===")
    page = client.get("/confirm?token=abc")
    check("/confirm renders a page", page.status_code == 200 and "<html" in page.text.lower(),
          str(page.status_code))

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL EMAIL CONFIRMATION TESTS PASSED")
