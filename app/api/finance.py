"""The business in money: what a campaign sells for, what it costs us to deliver, what we may
spend to win an agent, and what has actually been collected.

Every number here is either a real row (paid orders, packs, assets, the costs ledger) or
arithmetic on the assumptions the operator typed into the Finance tab. Nothing is a guess that
is presented as a measurement: anything modelled is labelled ``assumed`` in the payload and the
console's sentence for that square says so out loud.

Why the split matters: a $49 sale has ~93% gross margin and still cannot pay for a customer,
because customer acquisition for a one-off sale has to come out of that single $49. The repeat
model is what changes the answer — an agent who runs several campaigns a year is worth several
times one campaign — so this module reports both the per-campaign unit economics and the annual
value of a repeat agent, and the acquisition budget is derived from the second one.
"""
from __future__ import annotations

import math
import os
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.security import get_admin_user
from app.db.session import (Asset, Boost, Cost, CreditPurchase, FinanceSetting, Order, User,
                            get_db)
from app.services import billing, storage, team_access

router = APIRouter()

SETTINGS_ID = 1

# What these cost, as of the operator typing them in. Every one is overridable in the console:
# they are opinions about the world, not facts in the database, and the honest place for them is
# a row the operator owns rather than a constant that needs a deploy to change.
DEFAULT_ASSUMPTIONS: dict[str, float] = {
    # Delivery: one campaign is ~46k model tokens plus photo tagging; measured at ~$0.02 raw and
    # budgeted at $0.10 so a retry-heavy build is still covered.
    "engine_cost_per_campaign_usd": 0.10,
    # Photos are ~50 MB a campaign. R2 is $0.015/GB-month, so this is under a cent.
    "gb_per_campaign": 0.05,
    "r2_usd_per_gb_month": 0.015,
    # Paid hosting once off Render's free plan: web Starter, Postgres 256 MB, cron, domain.
    "hosting_web_usd": 7.00,
    "hosting_postgres_usd": 6.00,
    "hosting_cron_usd": 1.00,
    "hosting_domain_usd": 1.17,
    # Refunds, chargebacks and the odd redo.
    "refund_buffer_pct": 2.0,
    # The repeat model: how often an average agent buys, and how long they stay.
    "campaigns_per_agent_per_year": 8.0,
    "retention_years": 2.0,
    # The margin a price has to leave before acquisition is paid out of it.
    "target_margin_pct": 60.0,
    # Used for the hosting-per-campaign split before there is any volume to divide by.
    "planning_volume_per_month": 10.0,
    # Stripe's published rate; here so a rate change is a field, not a code edit.
    "stripe_pct": 2.9,
    "stripe_fixed_usd": 0.30,
}

# Bounds exist so a typo cannot turn the console into fiction: a hosting cost of $7000 or a
# retention of 400 years would silently produce nonsense acquisition budgets.
BOUNDS: dict[str, tuple[float, float]] = {
    "engine_cost_per_campaign_usd": (0.0, 100.0),
    "gb_per_campaign": (0.0, 5.0),
    "r2_usd_per_gb_month": (0.0, 1.0),
    "hosting_web_usd": (0.0, 1000.0),
    "hosting_postgres_usd": (0.0, 1000.0),
    "hosting_cron_usd": (0.0, 1000.0),
    "hosting_domain_usd": (0.0, 1000.0),
    "refund_buffer_pct": (0.0, 30.0),
    "campaigns_per_agent_per_year": (1.0, 100.0),
    "retention_years": (0.1, 20.0),
    "target_margin_pct": (0.0, 90.0),
    "planning_volume_per_month": (1.0, 10000.0),
    "stripe_pct": (0.0, 15.0),
    "stripe_fixed_usd": (0.0, 10.0),
}

FIELDS = [
    {"key": "engine_cost_per_campaign_usd", "label": "Model cost per campaign",
     "hint": "Tokens and photo tagging for one 14-day build.", "unit": "$", "step": "0.01"},
    {"key": "gb_per_campaign", "label": "Photo storage per campaign",
     "hint": "Roughly 20 listing photos.", "unit": "GB", "step": "0.01"},
    {"key": "hosting_web_usd", "label": "Web service", "hint": "Render Starter.",
     "unit": "$/mo", "step": "0.01"},
    {"key": "hosting_postgres_usd", "label": "Postgres", "hint": "The real database.",
     "unit": "$/mo", "step": "0.01"},
    {"key": "hosting_cron_usd", "label": "Publisher cron", "hint": "Posts go out on time.",
     "unit": "$/mo", "step": "0.01"},
    {"key": "hosting_domain_usd", "label": "Domain", "hint": "$14 a year.",
     "unit": "$/mo", "step": "0.01"},
    {"key": "refund_buffer_pct", "label": "Refund buffer",
     "hint": "Share of revenue set aside for refunds.", "unit": "%", "step": "0.1"},
    {"key": "campaigns_per_agent_per_year", "label": "Campaigns per agent / year",
     "hint": "Listings a year times campaigns per listing.", "unit": "#", "step": "0.5"},
    {"key": "retention_years", "label": "Years an agent stays",
     "hint": "How long a repeat customer keeps buying.", "unit": "yrs", "step": "0.5"},
    {"key": "target_margin_pct", "label": "Target margin",
     "hint": "Margin a price must leave after delivery.", "unit": "%", "step": "1"},
    {"key": "planning_volume_per_month", "label": "Planning volume",
     "hint": "Campaigns a month, until real volume exists.", "unit": "#/mo", "step": "1"},
]


def _row(db: Session) -> FinanceSetting:
    row = db.query(FinanceSetting).filter(FinanceSetting.id == SETTINGS_ID).first()
    if row is None:
        row = FinanceSetting(id=SETTINGS_ID, payload=dict(DEFAULT_ASSUMPTIONS))
        db.add(row)
        db.commit()
        db.refresh(row)
    return row


def assumptions(db: Session) -> dict[str, float]:
    """The operator's numbers, with any key they have never touched filled from the defaults."""
    merged = dict(DEFAULT_ASSUMPTIONS)
    stored = _row(db).payload or {}
    for key in DEFAULT_ASSUMPTIONS:
        if key in stored:
            try:
                merged[key] = float(stored[key])
            except (TypeError, ValueError):
                pass
    return merged


class AssumptionsIn(BaseModel):
    values: dict[str, Any]


@router.get("/admin/finance")
def finance(db: Session = Depends(get_db), current_user: User = Depends(team_access.needs("money"))):
    """Everything the Finance tab shows, computed once, server-side, so there is one version
    of each number instead of a different one in every panel."""
    a = assumptions(db)
    price_cents = billing.price_cents()
    price = price_cents / 100.0

    fixed_monthly = (a["hosting_web_usd"] + a["hosting_postgres_usd"] + a["hosting_cron_usd"]
                     + a["hosting_domain_usd"])
    storage_per_campaign_month = a["gb_per_campaign"] * a["r2_usd_per_gb_month"]

    now = datetime.utcnow()
    month_ago = now - timedelta(days=30)
    paid_orders = db.query(Order).filter(Order.status == "paid").all()
    paid_packs = db.query(CreditPurchase).filter(CreditPurchase.status == "paid").all()

    recent = [o for o in paid_orders if o.paid_at and o.paid_at >= month_ago]
    recent += [p for p in paid_packs if p.paid_at and p.paid_at >= month_ago]
    volume_actual = float(len(recent))
    volume = volume_actual or float(a["planning_volume_per_month"])

    hosting_per_campaign = fixed_monthly / volume
    delivery = a["engine_cost_per_campaign_usd"] + storage_per_campaign_month
    stripe_fee = price * (a["stripe_pct"] / 100.0) + a["stripe_fixed_usd"]
    refunds = price * (a["refund_buffer_pct"] / 100.0)
    contribution = price - stripe_fee - delivery - hosting_per_campaign - refunds
    margin_pct = (contribution / price * 100.0) if price else 0.0

    # Break-even is fixed cost divided by what is left of a sale once delivery is paid for. It
    # deliberately ignores acquisition: this is the floor, before a single customer is bought.
    per_sale_after_delivery = price - stripe_fee - delivery - refunds
    breakeven_volume = (math.ceil(fixed_monthly / per_sale_after_delivery)
                        if per_sale_after_delivery > 0 else None)

    # Price needed to leave the target margin at the current volume: solve
    # price = fixed/N + delivery + refunds + stripe + margin*price for price.
    denom = 1.0 - (a["stripe_pct"] / 100.0) - (a["refund_buffer_pct"] / 100.0) \
        - (a["target_margin_pct"] / 100.0)
    price_floor = ((fixed_monthly / volume + delivery) / denom) if denom > 0.01 else None

    ltv_contribution = contribution * a["campaigns_per_agent_per_year"] * a["retention_years"]
    cac = {ratio: round(ltv_contribution / ratio, 2) for ratio in (2, 3, 4)}

    # Actuals — real rows only.
    gross_cents = sum(int(o.amount_cents or 0) for o in paid_orders) \
        + sum(int(p.amount_cents or 0) for p in paid_packs)
    gross = gross_cents / 100.0
    # Renewals: a paid order on a campaign whose round is 1 or more. The $39 is never inferred
    # from the amount (a promo could change it) — the round on the campaign decides it.
    rounds = {b.id: int(getattr(b, "repeat_round", 0) or 0)
              for b in db.query(Boost).filter(Boost.id.in_(
                  [o.boost_id for o in paid_orders] or [-1])).all()}
    renewal_orders = [o for o in paid_orders if rounds.get(o.boost_id, 0) >= 1]
    renewal_cents = sum(int(o.amount_cents or 0) for o in renewal_orders)
    month_gross = (sum(int(o.amount_cents or 0) for o in paid_orders
                       if o.paid_at and o.paid_at >= month_ago)
                   + sum(int(p.amount_cents or 0) for p in paid_packs
                         if p.paid_at and p.paid_at >= month_ago)) / 100.0
    buyers: dict[int, dict[str, Any]] = {}
    for o in paid_orders:
        row = buyers.setdefault(o.user_id, {"campaigns": 0, "packs": 0, "cents": 0,
                                            "last": None})
        row["campaigns"] += 1
        row["cents"] += int(o.amount_cents or 0)
        if o.paid_at and (row["last"] is None or o.paid_at > row["last"]):
            row["last"] = o.paid_at
    for p in paid_packs:
        row = buyers.setdefault(p.user_id, {"campaigns": 0, "packs": 0, "cents": 0,
                                            "last": None})
        row["packs"] += 1
        row["cents"] += int(p.amount_cents or 0)
        if p.paid_at and (row["last"] is None or p.paid_at > row["last"]):
            row["last"] = p.paid_at

    emails = {u.id: u.email for u in db.query(User).filter(
        User.id.in_(list(buyers.keys()))).all()} if buyers else {}
    credits_out = db.query(func.coalesce(func.sum(User.campaign_credits), 0)).scalar() or 0
    customers = [{
        "user_id": uid,
        "email": emails.get(uid) or ("#%d" % uid),
        "campaigns": row["campaigns"],
        "packs": row["packs"],
        "purchases": row["campaigns"] + row["packs"],
        "paid_usd": round(row["cents"] / 100.0, 2),
        "last_paid": row["last"],
    } for uid, row in buyers.items()]
    customers.sort(key=lambda c: (-c["paid_usd"], c["email"]))
    repeat_customers = [c for c in customers if c["purchases"] >= 2]
    repeat_rate = (len(repeat_customers) / len(customers) * 100.0) if customers else 0.0

    # Costs: the ledger is what was actually paid; the assumptions above are the run-rate.
    costs = db.query(Cost).all()
    try:
        from app.api.costs import _summary as ledger_summary  # noqa: PLC0415 - shared maths
        ledger = ledger_summary(costs)
    except Exception:  # noqa: BLE001 - the Finance tab must not die with the costs module
        ledger = {"spent_to_date_usd": 0.0, "monthly_recurring_usd": 0.0, "count": len(costs)}

    # Capacity: photos are the only thing that grows without limit.
    asset_bytes = db.query(func.coalesce(func.sum(func.length(Asset.data)), 0)).scalar() or 0
    campaigns_built = db.query(func.count(Boost.id)).scalar() or 0
    db_bytes = None
    try:
        bind = db.get_bind()
        if bind.dialect.name == "postgresql":
            db_bytes = db.execute(func.pg_database_size(
                func.current_database())).scalar()
        else:
            path = str(bind.url.database or "")
            if path and os.path.exists(path):
                db_bytes = os.path.getsize(path)
    except Exception:  # noqa: BLE001 - a size probe must never break the page
        db_bytes = None

    return {
        "generated_at": now,
        "price": {
            "cents": price_cents,
            "label": billing.price_label(price_cents),
            "repeat_cents": billing.repeat_price_cents(),
            "repeat_label": billing.price_label(billing.repeat_price_cents()),
        },
        "fixed": {
            "web_usd": a["hosting_web_usd"],
            "postgres_usd": a["hosting_postgres_usd"],
            "cron_usd": a["hosting_cron_usd"],
            "domain_usd": a["hosting_domain_usd"],
            "total_monthly_usd": round(fixed_monthly, 2),
            "annual_usd": round(fixed_monthly * 12, 2),
        },
        "volume": {
            "campaigns_last_30d": int(volume_actual),
            "basis": "actual" if volume_actual else "assumed",
            "used": volume,
        },
        "unit": {
            "price_usd": round(price, 2),
            "stripe_fee_usd": round(stripe_fee, 2),
            "engine_usd": round(a["engine_cost_per_campaign_usd"], 2),
            "storage_usd": round(storage_per_campaign_month, 4),
            "hosting_usd": round(hosting_per_campaign, 2),
            "refunds_usd": round(refunds, 2),
            "delivery_usd": round(delivery, 2),
            "costs_usd": round(stripe_fee + delivery + hosting_per_campaign + refunds, 2),
            "contribution_usd": round(contribution, 2),
            "margin_pct": round(margin_pct, 1),
        },
        "breakeven": {
            "campaigns_per_month": breakeven_volume,
            "revenue_at_breakeven_usd": (None if breakeven_volume is None
                                         else round(breakeven_volume * price, 2)),
            "per_sale_after_delivery_usd": round(per_sale_after_delivery, 2),
        },
        "price_floor": {
            "target_margin_pct": a["target_margin_pct"],
            "at_current_volume_usd": None if price_floor is None else round(price_floor, 2),
        },
        "repeat": {
            "campaigns_per_agent_per_year": a["campaigns_per_agent_per_year"],
            "retention_years": a["retention_years"],
            "contribution_per_campaign_usd": round(contribution, 2),
            "annual_contribution_usd": round(contribution * a["campaigns_per_agent_per_year"], 2),
            "lifetime_contribution_usd": round(ltv_contribution, 2),
            "revenue_per_agent_per_year_usd": round(price * a["campaigns_per_agent_per_year"], 2),
        },
        "acquisition": {
            "max_cac_usd": cac,
            "note": ("Each figure keeps the stated multiple of lifetime contribution as profit: "
                     "3x means $1 of acquisition buys $3 of contribution."),
        },
        "actuals": {
            "gross_usd": round(gross, 2),
            "gross_last_30d_usd": round(month_gross, 2),
            "renewal_orders": len(renewal_orders),
            "renewal_gross_usd": round(renewal_cents / 100.0, 2),
            "paid_campaigns": len(paid_orders),
            "paid_packs": len(paid_packs),
            "customers": len(customers),
            "repeat_customers": len(repeat_customers),
            "repeat_rate_pct": round(repeat_rate, 1),
            "avg_paid_per_customer_usd": round(gross / len(customers), 2) if customers else 0.0,
            "credits_outstanding": int(credits_out),
        },
        "ledger": {
            "spent_to_date_usd": ledger.get("spent_to_date_usd", 0.0),
            "monthly_recurring_usd": ledger.get("monthly_recurring_usd", 0.0),
            "entries": ledger.get("count", len(costs)),
        },
        "capacity": {
            "campaigns_built": int(campaigns_built),
            "asset_bytes": int(asset_bytes),
            "asset_mb": round(asset_bytes / 1048576.0, 1),
            "db_bytes": int(db_bytes) if db_bytes is not None else None,
            "db_mb": round(db_bytes / 1048576.0, 1) if db_bytes is not None else None,
            "storage_mode": storage.mode(),
            "r2_configured": storage.enabled(),
            "r2_note": storage.note(),
        },
        "customers": customers,
        "assumptions": a,
        "fields": FIELDS,
    }


@router.put("/admin/finance/assumptions")
def save_assumptions(body: AssumptionsIn, db: Session = Depends(get_db),
                     current_user: User = Depends(team_access.needs("money"))):
    """Store the operator's numbers. Unknown keys and out-of-range values are refused, because
    a silently ignored typo is how a model starts lying."""
    payload = dict(_row(db).payload or {})
    saved = {}
    for key, raw in (body.values or {}).items():
        if key not in DEFAULT_ASSUMPTIONS:
            raise HTTPException(status_code=400, detail="Unknown assumption: %s" % key)
        try:
            value = float(raw)
        except (TypeError, ValueError):
            raise HTTPException(status_code=400, detail="%s must be a number" % key)
        low, high = BOUNDS.get(key, (None, None))
        if low is not None and not (low <= value <= high):
            raise HTTPException(status_code=400,
                                detail="%s must be between %s and %s" % (key, low, high))
        payload[key] = value
        saved[key] = value
    row = _row(db)
    row.payload = payload
    db.commit()
    return {"saved": saved, "assumptions": assumptions(db)}


@router.get("/admin/finance/daily")
def finance_daily(days: int = 30, db: Session = Depends(get_db),
                  current_user: User = Depends(team_access.needs("money"))):
    """One row per day, with the orders behind it - the bar chart on the Finance page.

    Days are calendar days in UTC (Stripe reports in UTC and so does the database), the window
    is contiguous so a quiet day is a zero bar rather than a missing one, and a checkout that
    was started and never finished shows up as ``unfinished`` on the day it was started.
    """
    days = max(1, min(int(days or 30), 180))
    end = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
    start = end - timedelta(days=days)

    paid = (
        db.query(Order, User, Boost)
        .outerjoin(User, Order.user_id == User.id)
        .outerjoin(Boost, Order.boost_id == Boost.id)
        .filter(Order.paid_at.isnot(None))
        .filter(Order.paid_at >= start)
        .order_by(Order.paid_at)
        .all()
    )
    started = (
        db.query(Order)
        .filter(Order.status == "pending")
        .filter(Order.created_at >= start)
        .all()
    )

    buckets: dict[str, dict] = {}
    cursor = start
    while cursor < end:
        buckets[cursor.date().isoformat()] = {"date": cursor.date().isoformat(), "orders": 0,
                                              "revenue_usd": 0.0, "unfinished": 0, "items": []}
        cursor += timedelta(days=1)

    for order, owner, boost in paid:
        paid_at = order.paid_at.replace(tzinfo=None) if isinstance(order.paid_at, datetime) else None
        if paid_at is None:
            continue
        day = buckets.get(paid_at.date().isoformat())
        if day is None:
            continue
        amount = round(float(order.amount_cents or 0) / 100.0, 2)
        day["orders"] += 1
        day["revenue_usd"] = round(day["revenue_usd"] + amount, 2)
        day["items"].append({
            "at": paid_at.isoformat(),
            "agent": (owner.name or owner.email) if owner else None,
            "agent_email": owner.email if owner else None,
            "address": boost.address if boost else None,
            "amount_usd": amount,
        })

    for order in started:
        created = order.created_at.replace(tzinfo=None) if isinstance(order.created_at, datetime) else None
        if created is None:
            continue
        day = buckets.get(created.date().isoformat())
        if day is not None:
            day["unfinished"] += 1

    return {"days": list(buckets.values()), "window_days": days,
            "total_usd": round(sum(d["revenue_usd"] for d in buckets.values()), 2)}
