"""A customer's support request has to reach a person.

The ticket always lands in the operator console, which is enough when somebody is watching
the console. It is not enough when the customer writes at 9pm expecting an answer, so the
ticket is also mailed to the operators — and this is the check that the mail path is actually
wired, without needing a mail provider in the test.

The shape that matters: configured mail => one message to every operator address, carrying
the ticket id and what was written; unconfigured mail => no exception, no send, ticket still
saved (so the console keeps working and the customer is not punished for our config).
"""
import os
import sys
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-support-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com,second@example.com"
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"
os.environ["RESMARA_SIGNUP_EMAILS"] = ""
for _key in ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "MAIL_FROM"):
    os.environ.pop(_key, None)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services import mail  # noqa: E402
from app.api import resmara as api  # noqa: E402
from app.db.session import Base, engine  # noqa: E402
from app.db.migrate import migrate  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


client = TestClient(app)

r = client.post("/api/auth/register", json={"email": "client@example.com", "password": "long enough",
                                            "name": "Client", "invite_code": "beta-code-123"})
check("a client can register", r.status_code == 201, r.text)
token = client.post("/api/auth/login", data={"username": "client@example.com",
                                             "password": "long enough"}).json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

sent: list[dict] = []


def fake_send(to, subject, body, **kwargs):
    sent.append({"to": to, "subject": subject, "body": body, **kwargs})
    return {"sent": True}


real_configured = mail.mail_configured
real_send = mail.send_email

# ---- with no provider: the ticket is still saved, nothing raises -----------------------
mail.mail_configured = lambda: False
mail.send_email = fake_send
api.mail.mail_configured = mail.mail_configured
api.mail.send_email = mail.send_email
try:
    r = client.post("/api/support", json={"subject": "Cannot upload photos",
                                          "message": "The upload button does nothing on my phone."},
                    headers=headers)
    check("a ticket is accepted with no mail provider", r.status_code == 201, r.text)
    check("and nothing is mailed", sent == [], str(sent))
    ticket_id = r.json().get("id")

    # ---- with a provider: every operator address gets it ------------------------------
    mail.mail_configured = lambda: True
    api.mail.mail_configured = mail.mail_configured
    r = client.post("/api/support", json={"subject": "Still stuck",
                                          "message": "Second try: the gallery link shows one photo."},
                    headers=headers)
    check("a ticket is accepted with mail configured", r.status_code == 201, r.text)
    check("one message per operator", len(sent) == 2, str(len(sent)))
    tos = sorted(str(m.get("to")) for m in sent)
    check("both operator addresses were used", tos == ["owner@example.com", "second@example.com"], str(tos))
    blob = " ".join(str(m.get("body", "")) for m in sent)
    check("the ticket id is in the mail", str(r.json().get("id")) in blob, blob[:200])
    check("what the customer wrote is in the mail", "gallery link shows one photo" in blob, blob[:200])
    check("the customer's address is in the mail", "client@example.com" in blob, blob[:200])
    check("the console link is in the mail", "admin.html" in blob, blob[:200])
finally:
    mail.mail_configured = real_configured
    mail.send_email = real_send
    api.mail.mail_configured = real_configured
    api.mail.send_email = real_send

print()
if FAILS:
    print(f"{len(FAILS)} check(s) failed: {FAILS}")
    sys.exit(1)
print("all checks passed")
