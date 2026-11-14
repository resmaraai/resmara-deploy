#!/usr/bin/env python3
"""Finance tab: the model has to be arithmetic, honest about what is assumed, and locked to admins.

The tab exists so the operator can answer three questions without a spreadsheet: what a campaign
leaves us, how many pay the hosting bill, and what we may spend to win an agent. Those answers are
only worth anything if they agree with each other, so what is pinned here is the arithmetic:

  * a sale's cost is exactly the parts added up, and contribution is price minus cost
  * break-even is fixed cost divided by what a sale leaves, rounded up (not down)
  * the price floor is the price that leaves the target margin at today's volume
  * a repeat agent is worth their annual contribution times the years they stay, and the
    acquisition budget is that divided by the multiple
  * saving an assumption changes the model, and an unknown key or an out-of-range number is
    refused rather than silently ignored
  * real money — a paid order and a paid pack — shows up in collected revenue, and a buyer who
    paid twice is a repeat customer
  * a non-admin gets 403
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
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
    tmp = tempfile.mkdtemp(prefix="resmara-finance-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "finance.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-finance")
    os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash
    from app.db.session import Base, engine, SessionLocal, Boost, CreditPurchase, Order, User

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    def account(email: str, admin: bool = False) -> dict:
        with SessionLocal() as db:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, name=email,
                            hashed_password=get_password_hash("finance-pass-123"),
                            is_active=True, is_admin=admin, subscription_status="active"))
                db.commit()
        r = client.post("/api/auth/login",
                        data={"username": email, "password": "finance-pass-123"})
        return {"Authorization": "Bearer %s" % r.json().get("access_token", "")}

    admin = account("owner@example.com", admin=True)
    client_h = account("agent@example.com")

    # ── who may look ───────────────────────────────────────────────────────────
    check("a customer is refused", client.get("/api/admin/finance", headers=client_h).status_code == 403,
          str(client.get("/api/admin/finance", headers=client_h).status_code))
    r = client.get("/api/admin/finance", headers=admin)
    check("the operator gets the model", r.status_code == 200, str(r.status_code))
    body = r.json()
    for key in ("price", "fixed", "volume", "unit", "breakeven", "price_floor", "repeat",
                "acquisition", "actuals", "capacity", "customers", "assumptions", "fields"):
        check("it carries %s" % key, key in body)

    # ── the arithmetic agrees with itself ──────────────────────────────────────
    u, f, b = body["unit"], body["fixed"], body["breakeven"]
    parts = round(u["stripe_fee_usd"] + u["delivery_usd"] + u["hosting_usd"] + u["refunds_usd"], 2)
    check("a sale costs exactly its parts", abs(parts - u["costs_usd"]) <= 0.02,
          "%s vs %s" % (parts, u["costs_usd"]))
    check("contribution is price minus cost",
          abs(round(u["price_usd"] - u["costs_usd"], 2) - u["contribution_usd"]) <= 0.02,
          "%s" % u["contribution_usd"])
    check("margin is contribution over price",
          abs(u["margin_pct"] - round(u["contribution_usd"] / u["price_usd"] * 100, 1)) <= 0.15,
          str(u["margin_pct"]))
    expected_be = -(-f["total_monthly_usd"] // b["per_sale_after_delivery_usd"])  # ceil
    check("break-even rounds up, never down", b["campaigns_per_month"] == int(expected_be),
          "%s vs %s" % (b["campaigns_per_month"], expected_be))
    check("hosting is the four line items added up",
          abs(round(f["web_usd"] + f["postgres_usd"] + f["cron_usd"] + f["domain_usd"], 2)
              - f["total_monthly_usd"]) <= 0.01, str(f["total_monthly_usd"]))
    check("fixed cost is annualised correctly",
          abs(f["annual_usd"] - f["total_monthly_usd"] * 12) <= 0.05, str(f["annual_usd"]))

    rep, acq = body["repeat"], body["acquisition"]
    check("an agent a year is per-campaign contribution times volume",
          abs(rep["annual_contribution_usd"]
              - rep["contribution_per_campaign_usd"] * rep["campaigns_per_agent_per_year"]) <= 0.05,
          str(rep["annual_contribution_usd"]))
    check("lifetime is annual times years",
          abs(rep["lifetime_contribution_usd"]
              - rep["annual_contribution_usd"] * rep["retention_years"]) <= 0.10,
          str(rep["lifetime_contribution_usd"]))
    check("the acquisition budget is lifetime divided by its multiple",
          abs(acq["max_cac_usd"]["3"] - rep["lifetime_contribution_usd"] / 3) <= 0.02,
          str(acq["max_cac_usd"]))
    check("a stricter multiple allows less acquisition",
          acq["max_cac_usd"]["4"] < acq["max_cac_usd"]["3"] < acq["max_cac_usd"]["2"],
          str(acq["max_cac_usd"]))

    # ── assumptions: refused when wrong, effective when right ─────────────────
    before = body["unit"]["contribution_usd"]
    check("an unknown assumption is refused",
          client.put("/api/admin/finance/assumptions", headers=admin,
                     json={"values": {"nonsense": 1}}).status_code == 400)
    check("an out-of-range number is refused",
          client.put("/api/admin/finance/assumptions", headers=admin,
                     json={"values": {"hosting_web_usd": 7001}}).status_code == 400)
    check("a non-number is refused",
          client.put("/api/admin/finance/assumptions", headers=admin,
                     json={"values": {"engine_cost_per_campaign_usd": "cheap"}}).status_code == 400)
    r = client.put("/api/admin/finance/assumptions", headers=admin,
                   json={"values": {"engine_cost_per_campaign_usd": 5.10}})
    check("a real change saves", r.status_code == 200, str(r.status_code))
    after = client.get("/api/admin/finance", headers=admin).json()
    check("and it moves the model", abs(after["unit"]["contribution_usd"] - (before - 5.0)) <= 0.02,
          "%s -> %s" % (before, after["unit"]["contribution_usd"]))
    check("and it is remembered",
          abs(after["assumptions"]["engine_cost_per_campaign_usd"] - 5.10) <= 0.001,
          str(after["assumptions"]["engine_cost_per_campaign_usd"]))
    client.put("/api/admin/finance/assumptions", headers=admin,
               json={"values": {"engine_cost_per_campaign_usd": 0.10}})

    # ── real money shows up ───────────────────────────────────────────────────
    with SessionLocal() as db:
        agent = db.query(User).filter(User.email == "agent@example.com").first()
        boost = Boost(user_id=agent.id, address="12 Repeat St, Austin TX")
        db.add(boost)
        db.commit()
        db.refresh(boost)
        db.add(Order(user_id=agent.id, boost_id=boost.id, amount_cents=4900, status="paid",
                     paid_at=datetime.utcnow(), stripe_session_id="cs_test_fin_1"))
        db.add(CreditPurchase(user_id=agent.id, campaigns=4, amount_cents=19600, status="paid",
                              paid_at=datetime.utcnow(), stripe_session_id="cs_test_fin_2"))
        agent.campaign_credits = 3
        db.commit()

    body = client.get("/api/admin/finance", headers=admin).json()
    a = body["actuals"]
    check("a paid campaign and a paid pack are both collected",
          abs(a["gross_usd"] - 245.0) <= 0.01, str(a["gross_usd"]))
    check("counts them separately", a["paid_campaigns"] == 1 and a["paid_packs"] == 1,
          str(a))
    check("a buyer who paid twice is a repeat customer", a["repeat_customers"] == 1, str(a["repeat_customers"]))
    check("repeat rate is a share of buyers", abs(a["repeat_rate_pct"] - 100.0) <= 0.1,
          str(a["repeat_rate_pct"]))
    check("unspent prepaid campaigns are reported", a["credits_outstanding"] == 3,
          str(a["credits_outstanding"]))
    check("volume basis becomes actual once there is a sale", body["volume"]["basis"] == "actual",
          body["volume"]["basis"])
    row = body["customers"][0]
    check("the customer row shows the pack and the campaign",
          row["campaigns"] == 1 and row["packs"] == 1 and abs(row["paid_usd"] - 245.0) <= 0.01,
          str(row))

    if FAILS:
        print("FAIL — %d check(s) failed" % FAILS)
        return 1
    print("PASS — the model adds up, break-even rounds up, assumptions are validated and\n"
          "       effective, real payments appear, and only an admin can read it")
    return 0


if __name__ == "__main__":
    sys.exit(main())
