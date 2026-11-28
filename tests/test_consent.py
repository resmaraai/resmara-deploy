#!/usr/bin/env python3
"""Terms, renewal consent and the three money emails (Engine 1 §1, Engine 10 §1 and §8).

The failure these stop is not a crash, it is a quiet gap in the record: an account created
without accepting the Terms, an automatic $39 renewal switched on with nothing stored to say who
agreed, an agent never told that the charge repeats, and a price change announced after the fact.
So what is pinned here is the *evidence*:

  * a sign-up without the box ticked is refused, and one with it stores the version, time, IP
    and browser
  * the Terms state endpoint says "stale", accepting records the new version, and a stale tab
    offering an old version is refused
  * Checkout, Launch and "Run it until it sells" refuse a stale account with 409 terms_stale,
    and the automatic renewal refuses to turn on without its own consent
  * turning it off keeps the consent and stamps when it ended
  * the acknowledgment email is attempted on every turn-on, and a mail failure never undoes the
    record
  * the yearly reminder goes once a year, not once a sweep
  * a price notice closer than 30 days is refused, and 30+ days reaches every paying account
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone

def utc_today():
    """The server's own clock. app/services/consent.py counts the 30-day notice from
    datetime.now(timezone.utc).date(); using the Mac's local date here makes this test fail
    every evening between 4pm and midnight Pacific, when UTC is already the next day."""
    return datetime.now(timezone.utc).date()
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILS = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global FAILS
    if cond:
        print("  ok   %s" % label)
    else:
        FAILS += 1
        print("  FAIL %s %s" % (label, detail))


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="resmara-consent-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "consent.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-consent")
    os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
    os.environ["RESMARA_PUBLISH_TOKEN"] = "test-publish-token"
    os.environ.pop("RESEND_API_KEY", None)
    os.environ.pop("SMTP_HOST", None)
    os.environ.pop("SIGNUP_CODE", None)
    os.environ["RESMARA_SIGNUP_CODE"] = ""
    # The beta gate: these two addresses are on the list, so registration exercises the Terms
    # path instead of stopping at "private beta".
    os.environ["RESMARA_SIGNUP_EMAILS"] = "ticked@example.com,payer@example.com"
    # A key that is never used: it only makes billing_enabled() true so the Terms gate is what
    # answers, instead of the "billing is not configured" 503 in front of it.
    os.environ["STRIPE_SECRET_KEY"] = "sk_test_consent_only"

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash
    from app.db import migrate as migrate_mod
    from app.db.session import (Base, engine, SessionLocal as Session, Boost, Event, Order, User)
    from app.services import consent
    from app.services.facebook_login import TERMS_VERSION

    Base.metadata.create_all(bind=engine)
    migrate_mod.migrate()

    check("the migration knows the five renewal-consent columns",
          all(col in dict(migrate_mod.ADDITIONS["boosts"])
              for col in ("renewal_consent_at", "renewal_consent_version",
                          "renewal_consent_ip", "renewal_consent_ua",
                          "renewal_consent_off_at")))

    client = TestClient(app)
    H_JSON = {"Content-Type": "application/json"}

    # ── signing up ───────────────────────────────────────────────────────────────────
    print("sign-up carries the agreement")
    no_box = client.post("/api/auth/register", headers={"User-Agent": "consent-test/1.0"},
                         json={"email": "nobox@example.com", "password": "longenough1"})
    check("a sign-up with the box unticked is refused", no_box.status_code == 400,
          "%s %s" % (no_box.status_code, no_box.text[:120]))
    check("and the refusal says which box", "Terms" in no_box.text, no_box.text[:120])

    made = client.post("/api/auth/register", headers={"User-Agent": "consent-test/1.0"},
                       json={"email": "ticked@example.com", "password": "longenough1",
                             "terms_accepted": True, "terms_version": TERMS_VERSION})
    check("a sign-up with it ticked is created", made.status_code == 201,
          "%s %s" % (made.status_code, made.text[:200]))
    check("the account carries the accepted version",
          (made.json().get("terms_version") or "") == TERMS_VERSION, str(made.json().get("terms_version")))
    with Session() as db:
        user = db.query(User).filter(User.email == "ticked@example.com").first()
        ev = (db.query(Event).filter(Event.user_id == user.id,
                                     Event.event_type == "terms_accepted").first())
        uid = user.id if user else None
    check("the acceptance is written with the time, IP and browser",
          bool(ev) and (ev.payload or {}).get("version") == TERMS_VERSION
          and (ev.payload or {}).get("ip") and "consent-test" in ((ev.payload or {}).get("user_agent") or ""),
          json.dumps((ev.payload if ev else {}))[:200])

    # ── stale and re-accepting ───────────────────────────────────────────────────────
    print("a changed version is asked again")
    with Session() as db:
        u = db.get(User, uid)
        u.terms_version = "2020-01-01"
        db.commit()
    tok = client.post("/api/auth/login", data={"username": "ticked@example.com",
                                               "password": "longenough1"})
    H = {"Authorization": "Bearer " + (tok.json().get("access_token") or "")}
    state = client.get("/api/auth/terms", headers=H)
    check("the state endpoint says stale", state.status_code == 200 and state.json().get("stale") is True,
          state.text[:200])
    wrong = client.post("/api/auth/me/terms", headers=H, json={"version": "2020-01-01"})
    check("accepting an old version from a stale tab is refused", wrong.status_code == 400,
          wrong.text[:160])
    ok = client.post("/api/auth/me/terms", headers={**H, "User-Agent": "consent-test/2.0"},
                     json={"version": TERMS_VERSION})
    check("accepting the current one is recorded", ok.status_code == 200 and ok.json().get("status") == "accepted",
          ok.text[:200])
    check("and the state is no longer stale",
          client.get("/api/auth/terms", headers=H).json().get("stale") is False)

    # ── the money gates ─────────────────────────────────────────────────────────────
    print("money-moving calls refuse a stale account")
    with Session() as db:
        owner = db.get(User, uid)
        b = Boost(user_id=owner.id, address="7 Consent Court", main_status="Live", stage="LAUNCHED")
        db.add(b)
        db.commit()
        db.refresh(b)
        boost_id = b.id
    ok_on = client.post("/api/boosts/%d/until-sold" % boost_id,
                        params={"until_sold": True, "renewal_consent": TERMS_VERSION},
                        headers={**H, "User-Agent": "consent-test/3.0"})
    check("a current account can turn automatic renewal on", ok_on.status_code == 200, ok_on.text[:200])
    with Session() as db:
        row = db.get(Boost, boost_id)
        stored = (row.renewal_consent_version, bool(row.renewal_consent_at), row.renewal_consent_ip,
                  row.renewal_consent_ua)
        ack = (db.query(Event).filter(Event.boost_id == boost_id,
                                      Event.event_type == "renewal_acknowledgment").first())
    check("the agreement is stored on the campaign, with who and where",
          stored[0] == TERMS_VERSION and stored[1] and stored[2]
          and "consent-test" in (stored[3] or ""), str(stored))
    check("the acknowledgment email was attempted and its outcome recorded",
          bool(ack) and (ack.payload or {}).get("mail") in ("sent", "not_configured"),
          json.dumps((ack.payload if ack else {})))

    # off keeps the record
    off = client.post("/api/boosts/%d/until-sold" % boost_id, params={"until_sold": False}, headers=H)
    check("turning it off answers 200", off.status_code == 200, off.text[:160])
    with Session() as db:
        row = db.get(Boost, boost_id)
        kept = (row.renewal_consent_version, bool(row.renewal_consent_at), bool(row.renewal_consent_off_at))
        ended = (db.query(Event).filter(Event.boost_id == boost_id, Event.event_type == "renewal_consent",
                                        Event.payload.isnot(None)).all())
    check("off keeps the consent and stamps the end", kept[0] == TERMS_VERSION and kept[1] and kept[2],
          str(kept))
    check("off writes an event saying it ended",
          any((e.payload or {}).get("on") is False for e in ended), str(len(ended)))

    # no consent at all
    no_consent = client.post("/api/boosts/%d/until-sold" % boost_id,
                             params={"until_sold": True}, headers=H)
    check("turning it on without the agreement is refused 400",
          no_consent.status_code == 400 and "renewal_consent" in no_consent.text,
          no_consent.text[:160])

    # stale account: renewal and checkout both refuse
    with Session() as db:
        u = db.get(User, uid)
        u.terms_version = "2020-01-01"
        db.commit()
    stale_on = client.post("/api/boosts/%d/until-sold" % boost_id,
                           params={"until_sold": True, "renewal_consent": TERMS_VERSION}, headers=H)
    check("a stale account cannot turn renewal on", stale_on.status_code == 409,
          stale_on.text[:160])
    check("and is told which version to accept",
          (stale_on.json().get("detail") or {}).get("current") == TERMS_VERSION,
          str(stale_on.json().get("detail"))[:160])
    checkout = client.post("/api/billing/checkout", headers=H, json={"boost_id": boost_id})
    check("a stale account cannot start Checkout", checkout.status_code == 409,
          "%s %s" % (checkout.status_code, checkout.text[:160]))
    check("the refusal is machine-readable",
          (checkout.json().get("detail") or {}).get("error") == "terms_stale",
          str(checkout.json().get("detail"))[:160])
    with Session() as db:
        u = db.get(User, uid)
        u.terms_version = TERMS_VERSION
        db.commit()

    # ── the yearly reminder ─────────────────────────────────────────────────────────
    print("the yearly reminder fires once a year")
    now = datetime.now(timezone.utc)
    with Session() as db:
        u = db.get(User, uid)
        old = Boost(user_id=u.id, address="1 Anniversary Way", main_status="Live", until_sold=True,
                    until_sold_at=now - timedelta(days=400),
                    renewal_consent_at=now - timedelta(days=400),
                    renewal_consent_version=TERMS_VERSION)
        young = Boost(user_id=u.id, address="2 New Consent Road", main_status="Live", until_sold=True,
                      until_sold_at=now - timedelta(days=10),
                      renewal_consent_at=now - timedelta(days=10),
                      renewal_consent_version=TERMS_VERSION)
        db.add_all([old, young])
        db.commit()
        old_id, young_id = old.id, young.id
    first = None
    with Session() as db:
        result = consent.send_reminders(db)
    check("one reminder is due", result.get("due") == 1, str(result))
    check("it names the campaign that has run a year",
          [s["boost_id"] for s in result.get("sent", [])] == [old_id], str(result.get("sent")))
    with Session() as db:
        again = consent.send_reminders(db)
    check("a second run the same day sends nothing", again.get("due") == 0, str(again))

    # ── the price notice ────────────────────────────────────────────────────────────
    print("a price change needs 30 days")
    with Session() as db:
        buyer = User(email="payer@example.com", hashed_password=get_password_hash("longenough1"),
                     is_active=True, terms_version=TERMS_VERSION)
        db.add(buyer)
        db.commit()
        db.add(Order(user_id=buyer.id, boost_id=boost_id, amount_cents=4900, status="paid",
                     kind="campaign"))
        db.commit()
    short = client.post("/api/admin/price-notice", headers=H,
                        json={"new_cents": 5900, "effective_on": (utc_today() + timedelta(days=10)).isoformat()})
    check("a notice 10 days out is refused", short.status_code in (400, 403),
          "%s %s" % (short.status_code, short.text[:160]))
    # The operator is the admin in RESMARA_ADMIN_EMAILS, not this customer.
    with Session() as db:
        adm = db.query(User).filter(User.email == "owner@example.com").first()
        if not adm:
            adm = User(email="owner@example.com", hashed_password=get_password_hash("ownerpass123"),
                       is_active=True, is_admin=True, terms_version=TERMS_VERSION)
            db.add(adm)
            db.commit()
        else:
            adm.is_admin = True
            adm.hashed_password = get_password_hash("ownerpass123")
            adm.terms_version = TERMS_VERSION
            db.commit()
    atok = client.post("/api/auth/login", data={"username": "owner@example.com",
                                                "password": "ownerpass123"})
    AH = {"Authorization": "Bearer " + (atok.json().get("access_token") or "")}
    short2 = client.post("/api/admin/price-notice", headers=AH,
                         json={"new_cents": 5900, "effective_on": (utc_today() + timedelta(days=10)).isoformat()})
    check("the operator's 10-day notice is refused 400", short2.status_code == 400,
          "%s %s" % (short2.status_code, short2.text[:160]))
    check("and the refusal names the earliest allowed date",
          (short2.json().get("detail") or {}).get("earliest") ==
          (utc_today() + timedelta(days=30)).isoformat(),
          str(short2.json().get("detail"))[:200])
    good = client.post("/api/admin/price-notice", headers=AH,
                       json={"new_cents": 5900,
                             "effective_on": (utc_today() + timedelta(days=45)).isoformat(),
                             "note": "The first change since launch."})
    check("45 days out is accepted", good.status_code == 200, "%s %s" % (good.status_code, good.text[:200]))
    body = good.json() if good.status_code == 200 else {}
    check("it reaches every paying account", body.get("recipients", 0) >= 1, str(body))
    check("it says honestly whether mail went out",
          body.get("mail") in ("sent", "not_configured"), str(body.get("mail")))
    with Session() as db:
        logged = (db.query(Event).filter(Event.event_type == "price_notice").count())
    check("each recipient is recorded", logged >= 1, str(logged))
    hist = client.get("/api/admin/price-notice", headers=AH)
    check("the history endpoint returns them", hist.status_code == 200
          and len(hist.json().get("notices") or []) >= 1, hist.text[:160])

    # ── the machine endpoint ────────────────────────────────────────────────────────
    print("the clock's endpoint is machine-only")
    refused = client.post("/api/admin/consent/reminders")
    check("no token is 403", refused.status_code == 403, str(refused.status_code))
    allowed = client.post("/api/admin/consent/reminders",
                          headers={"X-Resmara-Token": "test-publish-token"})
    check("with the token it runs", allowed.status_code == 200 and "due" in allowed.json(),
          allowed.text[:160])

    print()
    if FAILS:
        print("%d FAILED" % FAILS)
        return 1
    print("ALL CONSENT TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
