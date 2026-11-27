#!/usr/bin/env python3
"""A build that stops because the AI account is out of credit says so, in words a customer can use.

The live failure on 24 Nov 2026 was a raw `Client error '429 Too Many Requests' ... "You have no
credits remaining." (insufficient_quota)` in the build status, which reads like a Resmara bug and
hides the fact that the campaign, its photos and its approved scope are all still there.
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILS = 0

ADAM_ERROR = ("Client error '429 Too Many Requests' for url 'https://api.openai.com/v1/responses': "
              "{\"error\": {\"message\": \"You have no credits remaining.\", "
              "\"type\": \"insufficient_quota\", \"code\": \"credit_balance_exhausted\"}}")


def check(label: str, ok: bool, detail: str = "") -> None:
    global FAILS
    print(("ok   " if ok else "FAIL ") + label + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS += 1


def main() -> int:
    db_dir = tempfile.mkdtemp(prefix="resmara_quota_")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_dir}/app.db"
    os.environ["UPLOAD_DIR"] = str(Path(db_dir) / "uploads")
    for key in ("RESMARA_ENGINE_BASE_URL", "RESMARA_ENGINE_API_KEY", "OPENAI_API_KEY",
                "OPENAI_BASE_URL"):
        os.environ.pop(key, None)
    for mod in [m for m in list(sys.modules) if m.startswith("app.")]:
        del sys.modules[mod]

    from app.api.engine import provider_error_text

    text = provider_error_text(ADAM_ERROR)
    check("the quota refusal is not passed through raw", "429" not in text, text)
    check("it says the provider is out of credit", "out of credit" in text.lower(), text)
    check("it says the campaign itself is intact", "saved" in text.lower(), text)
    check("an unrelated failure keeps its own words",
          provider_error_text("ValueError: gallery is empty") == "ValueError: gallery is empty")

    from fastapi.testclient import TestClient
    from app.core.config import settings
    from app.main import app

    settings.SIMULATE = True
    settings.OPENAI_API_KEY = ""

    with TestClient(app) as client:
        reg = client.post("/api/auth/register", json={"terms_accepted": True,
            "email": f"quota{int(time.time())}@example.com", "password": "quota-pass-12345",
            "name": "Quota"})
        check("register", reg.status_code in (200, 201), str(reg.status_code))
        login = client.post("/api/auth/login", data={
            "username": reg.json()["email"], "password": "quota-pass-12345"})
        check("login", login.status_code == 200, str(login.status_code))
        h = {"Authorization": f"Bearer {login.json()['access_token']}"}

        from app.db.session import Boost, Event, SessionLocal, User
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == reg.json()["email"]).first()
            user.meta_connected_at = datetime.utcnow()
            db.commit()
        finally:
            db.close()

        made = client.post("/api/boosts", headers=h, json={
            "address": "892 Coggins Street, Redding, CA 96003", "tier": "standard",
            "campaign_days": 14, "ad_budget_usd": 250})
        check("create a boost", made.status_code in (200, 201), made.text[:200])
        boost_id = made.json()["id"]

        db = SessionLocal()
        try:
            row = db.query(Boost).filter(Boost.id == boost_id).first()
            row.paid_at = datetime.utcnow()
            row.paid_amount_cents = 4900
            db.commit()
        finally:
            db.close()

        # The engine is replaced, not reached: this asserts the shape of the failure the customer
        # reads, and spends nothing.
        from app.services import content_engine

        async def refuses(boost, db, **kwargs):
            raise RuntimeError(ADAM_ERROR)

        original = content_engine.build_campaign
        content_engine.build_campaign = refuses
        try:
            started = client.post(f"/api/boosts/{boost_id}/build", headers=h,
                                  json={"force": True, "photo_permission": True})
            check("POST /build accepts the run", started.status_code == 202, started.text[:200])
            status = {}
            deadline = time.time() + 60
            while time.time() < deadline:
                status = client.get(f"/api/boosts/{boost_id}/build-status", headers=h).json()
                if status.get("status") in ("done", "error"):
                    break
                time.sleep(0.3)
        finally:
            content_engine.build_campaign = original

        err = (status.get("error") or "")
        check("the run ends in error", status.get("status") == "error", str(status))
        check("/build-status names the out-of-credit cause", "out of credit" in err.lower(), err)
        check("/build-status does not leak the raw 429", "429" not in err, err)

        db = SessionLocal()
        try:
            row = db.query(Boost).filter(Boost.id == boost_id).first()
            check("the campaign is marked Build failed, not left In Progress",
                  row.main_status == "Build failed", str(row.main_status))
            ev = (db.query(Event).filter(Event.boost_id == boost_id, Event.event_type == "error")
                  .order_by(Event.id.desc()).first())
            logged = (ev.payload or {}).get("error", "") if ev else ""
            check("the recorded error is the readable one", "out of credit" in logged.lower(), logged)
        finally:
            db.close()

    print("ALL PROVIDER-QUOTA CHECKS PASSED" if not FAILS else f"{FAILS} PROVIDER-QUOTA CHECK(S) FAILED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
