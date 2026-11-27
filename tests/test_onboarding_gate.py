"""The Meta connection is required, and a booking is not a substitute (owner item 8).

The rule the owner wrote: "Step 1 Meta connect is REQUIRED and can't be skipped. If they close
the Meta window, take them to Accounts with a message. Every sign-in should land there until
it's connected. Booking a setup session stops the prompts, but + Campaign stays blocked until
Meta is connected. And store 'Meta connected' and 'setup session booked' on the server."

So the tests are: a new account cannot create a campaign, the refusal says how to fix it,
booking a session does not open the gate, the tour is remembered, and once Meta is connected
the same call succeeds — read back from the server, not from a browser.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault("RESMARA_SIGNUP_CODE", "beta-code-123")

DB_DIR = tempfile.mkdtemp(prefix="onboarding-")
os.environ["RESMARA_DB"] = os.path.join(DB_DIR, "app.db")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(DB_DIR, 'app.db')}"
os.environ["RESMARA_UPLOAD_DIR"] = os.path.join(DB_DIR, "uploads")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


with TestClient(app) as client:
    client.post("/api/auth/register", json={"terms_accepted": True, "email": "new@example.com", "password": "long enough",
                                            "name": "New Agent", "invite_code": "beta-code-123"})
    token = client.post("/api/auth/login",
                        data={"username": "new@example.com", "password": "long enough"}
                        ).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}

    print("=== a new account cannot create a campaign ===")
    resp = client.post("/api/boosts", headers=h, json={"address": "1 First St, Austin TX"})
    check("+ Campaign is refused before Meta is connected", resp.status_code == 409, resp.text[:200])
    detail = resp.json().get("detail") or {}
    check("  ...with a reason the agent can act on",
          detail.get("error") == "meta_required" and "connect" in detail, str(detail)[:200])
    check("  ...that names the Meta connect route",
          detail.get("connect") == "/api/oauth/meta/connect", str(detail.get("connect")))

    print("\n=== the state is read from the server ===")
    st = client.get("/api/onboarding/state", headers=h).json()
    check("the state says Meta is not connected", st["meta_connected"] is False, str(st))
    check("  ...and campaigns are closed", st["campaign_allowed"] is False)
    check("  ...and it says so in words", "Meta" in (st.get("message") or ""), str(st.get("message")))

    print("\n=== the readiness audit does not tick what it cannot see ===")
    audit = client.get("/api/onboarding/meta-audit", headers=h).json()
    check("no connection means nothing is ticked",
          audit["connected"] is False and all(c["ok"] is False for c in audit["checks"]),
          str(audit)[:300])
    check("  ...and there are four things to check",
          [c["key"] for c in audit["checks"]] ==
          ["page", "page_admin", "instagram", "ad_account"], str(audit["checks"])[:200])

    print("\n=== booking a setup session stops the prompts, not the gate ===")
    booked = client.post("/api/onboarding/setup-session", headers=h,
                         json={"booked": True, "when": "2026-11-20T16:00:00Z"}).json()
    check("the booking is stored", booked["setup_booked"] is True and booked["setup_booked_at"],
          str(booked)[:200])
    check("  ...and + Campaign is still closed", booked["campaign_allowed"] is False, str(booked))
    again = client.post("/api/boosts", headers=h, json={"address": "1 First St, Austin TX"})
    check("  ...and the refusal still applies", again.status_code == 409, again.text[:150])
    check("booking twice does not move the timestamp",
          client.post("/api/onboarding/setup-session", headers=h, json={"booked": True}
                      ).json()["setup_booked_at"] == booked["setup_booked_at"])

    print("\n=== the tour is shown once per account ===")
    check("the tour starts unseen", client.get("/api/onboarding/state", headers=h).json()["tour_seen"] is False)
    client.post("/api/onboarding/tour-seen", headers=h)
    check("  ...and is remembered after it is shown",
          client.get("/api/onboarding/state", headers=h).json()["tour_seen"] is True)

    print("\n=== a second browser sees the same answers ===")
    token2 = client.post("/api/auth/login",
                         data={"username": "new@example.com", "password": "long enough"}
                         ).json()["access_token"]
    h2 = {"Authorization": f"Bearer {token2}"}
    st2 = client.get("/api/onboarding/state", headers=h2).json()
    check("the booking and the tour survive a new sign-in",
          st2["setup_booked"] is True and st2["tour_seen"] is True, str(st2)[:200])

    print("\n=== once Meta is connected the gate opens ===")
    from datetime import datetime, timezone

    from app.db.session import AdAccount, SessionLocal, User
    db = SessionLocal()
    user = db.query(User).filter(User.email == "new@example.com").first()
    user.meta_connected_at = datetime.now(timezone.utc)
    check("a real token on the account counts as connected",
          __import__("app.api.onboarding", fromlist=["meta_connected"]).meta_connected(db, user) is True)
    db.commit()
    db.close()
    made = client.post("/api/boosts", headers=h, json={"address": "1 First St, Austin TX",
                                                       "campaign_days": 14})
    check("the campaign can now be created", made.status_code in (200, 201), made.text[:200])
    check("  ...and the state agrees",
          client.get("/api/onboarding/state", headers=h).json()["campaign_allowed"] is True)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL ONBOARDING GATE TESTS PASSED")
