#!/usr/bin/env python3
"""Run it until it sells: the switch is a column on the campaign, not a browser preference.

Adam's PR #6 shipped the interface with the choice held in `state.untilSoldCampaigns` in the
browser, keyed by address. That cannot work for anything that costs money: the round builder and
the $39 charge run on the server, and a closed browser must not be the reason a paid-for renewal
never happens. What is pinned here:

  * the campaign carries `until_sold` (and when it was turned on), through the API and the list
  * turning it on and off is the owner's only, someone else gets 404 rather than a hint
  * it cannot be turned on for a listing already pending or sold — that is what makes it stop
  * the migration knows the columns, so a Postgres install that already has the table gets them
"""
from __future__ import annotations

import os
import sys
import tempfile
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
    tmp = tempfile.mkdtemp(prefix="resmara-untilsold-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "until.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-until-sold")
    os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
    os.environ.pop("STRIPE_SECRET_KEY", None)

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash
    from app.db import migrate as migrate_mod
    from app.db.session import Base, engine, SessionLocal as Session, Boost, User

    Base.metadata.create_all(bind=engine)
    migrate_mod.migrate()

    db = Session()
    try:
        owner = User(email="owner@example.com", name="Owner", is_active=True, is_admin=True,
                     hashed_password=get_password_hash("ownerpass123"))
        other = User(email="other@example.com", name="Other", is_active=True, is_admin=False,
                     hashed_password=get_password_hash("otherpass123"))
        db.add_all([owner, other]); db.commit(); db.refresh(owner); db.refresh(other)
        # Engine 10 §8: turning it on carries a Terms agreement, so both accounts are seeded the
        # way sign-up seeds them (the refusal of a stale/missing agreement is pinned separately).
        from app.services.consent import current_terms
        owner.terms_version = other.terms_version = current_terms()
        db.commit()
        b = Boost(user_id=owner.id, address="12 Until Sold Lane", main_status="Live", stage="LAUNCHED",
                  hidden=False)
        db.add(b); db.commit(); db.refresh(b)
        boost_id, other_id = b.id, other.id
        check("a fresh campaign is not on autopilot", bool(b.until_sold) is False)
    finally:
        db.close()

    client = TestClient(app)
    tok = client.post("/api/auth/login", data={"username": "owner@example.com", "password": "ownerpass123"})
    check("the owner can sign in", tok.status_code == 200, tok.text[:120])
    H = {"Authorization": "Bearer " + (tok.json().get("access_token") or "")}

    # ---------------------------------------------------------------- turn it on
    on = client.post("/api/boosts/%d/until-sold" % boost_id,
                     params={"until_sold": True, "renewal_consent": current_terms()}, headers=H)
    check("turning it on answers 200", on.status_code == 200, on.text[:160])
    body = on.json()
    check("the campaign reports until_sold true", body.get("until_sold") is True, str(body.get("until_sold")))
    check("turning it on records when", bool(body.get("until_sold_at")), str(body.get("until_sold_at")))

    # ---------------------------------------------------------------- it survives a reload
    listed = client.get("/api/boosts", headers=H)
    check("the campaign list answers", listed.status_code == 200, listed.text[:120])
    rows = listed.json() if isinstance(listed.json(), list) else listed.json().get("items", [])
    row = next((r for r in rows if r.get("id") == boost_id), None)
    check("the list carries the campaign", row is not None)
    check("the list carries until_sold, so the card reads the server", bool(row and row.get("until_sold") is True))

    # ---------------------------------------------------------------- not somebody else's switch
    tok2 = client.post("/api/auth/login", data={"username": "other@example.com", "password": "otherpass123"})
    H2 = {"Authorization": "Bearer " + (tok2.json().get("access_token") or "")}
    stolen = client.post("/api/boosts/%d/until-sold" % boost_id, params={"until_sold": False}, headers=H2)
    check("another account cannot flip it (404, not a hint)", stolen.status_code == 404, stolen.text[:120])
    check("...and it is still on", client.get("/api/boosts", headers=H).json() and
          next((r for r in (client.get("/api/boosts", headers=H).json() if isinstance(client.get("/api/boosts", headers=H).json(), list) else client.get("/api/boosts", headers=H).json().get("items", [])) if r.get("id") == boost_id), {}).get("until_sold") is True)

    # ---------------------------------------------------------------- it stops for a sold listing
    db = Session()
    try:
        row = db.query(Boost).filter(Boost.id == boost_id).first()
        row.until_sold = False
        row.listing_status = "pending"
        db.commit()
    finally:
        db.close()
    refused = client.post("/api/boosts/%d/until-sold" % boost_id, params={"until_sold": True}, headers=H)
    check("a pending listing refuses autopilot with 409", refused.status_code == 409, refused.text[:160])
    check("the refusal says why", "pending" in (refused.json().get("detail") or "").lower(),
          str(refused.json().get("detail"))[:120])

    # ---------------------------------------------------------------- and off again
    db = Session()
    try:
        row = db.query(Boost).filter(Boost.id == boost_id).first()
        row.listing_status = "active"
        db.commit()
    finally:
        db.close()
    client.post("/api/boosts/%d/until-sold" % boost_id,
                params={"until_sold": True, "renewal_consent": current_terms()}, headers=H)
    off = client.post("/api/boosts/%d/until-sold" % boost_id, params={"until_sold": False}, headers=H)
    check("turning it off answers 200", off.status_code == 200, off.text[:120])
    check("off clears the flag", off.json().get("until_sold") is False)
    check("off clears the timestamp too", off.json().get("until_sold_at") is None,
          str(off.json().get("until_sold_at")))

    # ---------------------------------------------------------------- an existing install gets the column
    boosts_additions = migrate_mod.ADDITIONS.get("boosts") or []
    names = [c[0] for c in boosts_additions]
    check("the migration names until_sold", "until_sold" in names, str(names)[:200])
    check("the migration names until_sold_at", "until_sold_at" in names)
    check("every boost column lives in the one boosts block",
          list(migrate_mod.ADDITIONS.keys()).count("boosts") == 1)

    print()
    if FAILS:
        print("FAILURES: %d" % FAILS)
        return 1
    print("ALL UNTIL-SOLD TESTS PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
