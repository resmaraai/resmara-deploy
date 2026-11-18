"""Billing endpoints: buy one campaign for $49 (Stripe Checkout), and the webhook that turns a
completed payment into a buildable campaign.

One product, one price. A campaign is recorded in `orders` and mirrored on the boost as
`paid_at`; everything that costs us model calls or Meta spend asks `require_paid()` first.

A prepaid four-campaign pack used to be sold here. It was not wanted: a second campaign on the
same listing is simply another $49 campaign, started with POST /boosts/{id}/again. The
`credit_purchases` table and `users.campaign_credits` stay readable so a balance already paid
for is still spendable, but no pack is offered and no pack checkout can be created.
"""
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import get_current_user
from app.db.session import get_db, User, Boost, Order, CreditPurchase, Event
from app.services import billing

router = APIRouter()


def boost_is_paid(boost: Boost, db: Session) -> bool:
    """True when this campaign has been paid for.

    Admins and owners are exempt: the operator has to be able to build a campaign to test
    the product they are selling, and refusing them is how a paid product becomes unusable
    the moment the card on file expires.
    """
    if boost.paid_at:
        return True
    return db.query(Order).filter(Order.boost_id == boost.id, Order.status == "paid").first() is not None


def consume_credit(boost: Boost, user: User, db: Session) -> bool:
    """Spend one prepaid campaign from the account's balance, once per campaign.

    A pack is how a repeat customer buys the second, third and fourth campaign, so the build
    gate has to spend a credit rather than ask for a card again. Idempotent by stamping the
    boost: a retried build must not cost a second credit, and a build after a pack purchase
    must never charge the card.

    The conditional UPDATE is the race guard — two builds fired at once can only take the
    credit if it is still there.
    """
    if boost.paid_at:
        return True
    spent = (db.query(User)
               .filter(User.id == user.id, User.campaign_credits > 0)
               .update({User.campaign_credits: User.campaign_credits - 1},
                       synchronize_session=False))
    if not spent:
        return False
    boost.paid_at = datetime.utcnow()
    boost.paid_amount_cents = 0   # paid from a prepaid balance, not by this build
    db.add(Event(user_id=user.id, boost_id=boost.id, event_type="credit_consumed",
                 payload={"campaigns": 1}))
    db.commit()
    db.refresh(user)
    return True


def require_paid(boost: Boost, user: User, db: Session) -> None:
    """Raise the one error the UI knows how to act on when a campaign is unpaid."""
    if getattr(user, "is_admin", False):
        return
    if boost_is_paid(boost, db):
        return
    if consume_credit(boost, user, db):
        return
    raise HTTPException(status_code=402, detail={
        "error": "payment_required",
        "message": "This campaign is %s. Buy it to build the posts." % billing.price_label(),
        "price_cents": billing.price_cents(),
        "checkout": "/api/billing/checkout",
        # A credit left over from a pack bought before packs were withdrawn still builds this
        # campaign; the number is reported so the paywall can say so instead of asking for a card.
        "campaigns_left": int(getattr(user, "campaign_credits", 0) or 0),
        "boost_id": boost.id,
    })


async def customer_for(user: User, db: Session) -> str:
    """The Stripe Customer for this account, created on first use.

    One Customer per account is what makes a saved card appear at the next Checkout instead of
    an empty card form; the id is ours to remember, the card stays at Stripe.
    """
    customer_id = user.stripe_customer_id
    if customer_id:
        return customer_id
    try:
        customer_id = await billing.ensure_customer(
            user_id=user.id, email=user.email, name=user.name or "")
    except httpx.HTTPStatusError as e:
        detail = "Stripe refused to create the customer"
        try:
            detail = (e.response.json().get("error") or {}).get("message") or detail
        except Exception:  # noqa: BLE001
            pass
        raise HTTPException(status_code=502, detail=detail)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    user.stripe_customer_id = customer_id
    db.add(Event(user_id=user.id, event_type="stripe_customer_created",
                 payload={"customer_id": customer_id}))
    db.commit()
    return customer_id


@router.get("/billing/config")
def billing_config():
    """What the UI needs to show a price and a button — no secrets."""
    return {
        "price_cents": billing.price_cents(),
        "price_label": billing.price_label(),
        "currency": billing.CURRENCY,
        "enabled": billing.billing_enabled(),
        "publishable_key": billing.publishable_key(),
        "product": "One property campaign",
    }


class CheckoutRequest(BaseModel):
    boost_id: int


@router.post("/billing/checkout")
async def create_checkout(body: CheckoutRequest, current_user: User = Depends(get_current_user),
                          db: Session = Depends(get_db)):
    """Start a Stripe Checkout for one campaign and return the hosted URL.

    Reuses a still-open session for the same boost so a double-click cannot create two
    payable pages for one campaign.
    """
    q = db.query(Boost).filter(Boost.id == body.boost_id)
    if not current_user.is_admin:
        q = q.filter(Boost.user_id == current_user.id)
    boost = q.first()
    if not boost:
        raise HTTPException(status_code=404, detail="Boost not found")
    if not billing.billing_enabled():
        raise HTTPException(status_code=503, detail=(
            "Billing is not configured yet: set STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY "
            "on the service."))
    if boost_is_paid(boost, db) and not current_user.is_admin:
        return {"status": "already_paid", "boost_id": boost.id}

    existing = (db.query(Order)
                .filter(Order.boost_id == boost.id, Order.status == "pending",
                        Order.checkout_url.isnot(None))
                .order_by(Order.id.desc()).first())
    if existing:
        return {"status": "pending", "boost_id": boost.id, "url": existing.checkout_url,
                "session_id": existing.stripe_session_id, "price_cents": existing.amount_cents}

    # One Customer per account. This is what makes the saved card appear at Checkout next time
    # instead of an empty card form; the id is ours to remember, the card stays at Stripe.
    customer_id = await customer_for(current_user, db)

    try:
        session = await billing.create_checkout_session(
            boost_id=boost.id, user_id=current_user.id, address=boost.address,
            base_url=settings.PUBLIC_BASE_URL, customer_id=customer_id, save_card=True,
            cents=billing.price_for(boost), round_no=billing.round_of(boost))
    except httpx.HTTPStatusError as e:
        detail = "Stripe refused the checkout"
        try:
            detail = (e.response.json().get("error") or {}).get("message") or detail
        except Exception:  # noqa: BLE001 - a non-JSON error body still has to surface
            pass
        raise HTTPException(status_code=502, detail=detail)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    order = Order(user_id=current_user.id, boost_id=boost.id,
                  amount_cents=billing.price_for(boost), currency=billing.CURRENCY,
                  status="pending", stripe_session_id=session.get("id"),
                  checkout_url=session.get("url"))
    db.add(order)
    db.add(Event(user_id=current_user.id, boost_id=boost.id, event_type="checkout_started",
                 payload={"session_id": session.get("id"), "amount_cents": order.amount_cents}))
    db.commit()
    return {"status": "pending", "boost_id": boost.id, "url": session.get("url"),
            "session_id": session.get("id"), "price_cents": order.amount_cents}


@router.get("/billing/balance")
def my_balance(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """How many campaigns this account has already paid for and not yet built.

    Packs are no longer sold, so the only way this is above zero is a pack bought before they
    were withdrawn — the balance is still honoured, and reported honestly.
    """
    rows = (db.query(CreditPurchase)
            .filter(CreditPurchase.user_id == current_user.id)
            .order_by(CreditPurchase.id.desc()).limit(20).all())
    return {
        "campaigns_left": int(getattr(current_user, "campaign_credits", 0) or 0),
        "single": {"price_cents": billing.price_cents(),
                   "price_label": billing.price_label()},
        "enabled": billing.billing_enabled(),
        # Packs bought before they were withdrawn, newest first, so the record is not lost.
        "purchases": [{
            "id": p.id, "campaigns": p.campaigns, "amount_cents": p.amount_cents,
            "amount_label": billing.price_label(p.amount_cents or 0), "status": p.status,
            "checkout_url": p.checkout_url if p.status == "pending" else None,
            "created_at": p.created_at, "paid_at": p.paid_at,
        } for p in rows],
    }


# A pack session created before packs were withdrawn can still complete (a Checkout link lives
# for 24 hours). Its metadata names its own size and price; these are the last values the offer
# ever used, so a session with no metadata is still honoured rather than paid for and dropped.
LEGACY_PACK_SIZE = 4
LEGACY_PACK_CENTS = 19600


def settle_pack(outcome: dict, db: Session) -> dict:
    """Apply a legacy pack payment: add its campaigns to the account's balance, once.

    Nothing creates a pack session any more; this keeps a completion that was already in flight
    from taking money and giving nothing. Idempotent on the purchase status, so a webhook Stripe
    retries cannot mint a second pack.
    """
    session_id = outcome.get("session_id")
    purchase = (db.query(CreditPurchase)
                .filter(CreditPurchase.stripe_session_id == session_id).first())
    user = db.query(User).filter(User.id == outcome.get("user_id")).first()

    if outcome.get("paid"):
        if purchase is None:
            # The session was created before this deploy, or the row was lost. Record it now
            # rather than taking money and giving nothing.
            if user is None:
                return {"received": True, "status": "unmatched"}
            purchase = CreditPurchase(
                user_id=user.id,
                campaigns=outcome.get("campaigns") or LEGACY_PACK_SIZE,
                amount_cents=outcome.get("amount_cents") or LEGACY_PACK_CENTS,
                currency=billing.CURRENCY, status="pending", stripe_session_id=session_id)
            db.add(purchase)
            db.flush()
        if purchase.status != "paid":
            purchase.status = "paid"
            purchase.paid_at = datetime.utcnow()
            purchase.stripe_payment_intent = (outcome.get("payment_intent")
                                              or purchase.stripe_payment_intent)
            owner = user or db.query(User).filter(User.id == purchase.user_id).first()
            if owner is not None:
                owner.campaign_credits = int(owner.campaign_credits or 0) + int(purchase.campaigns or 0)
                if outcome.get("customer") and not owner.stripe_customer_id:
                    owner.stripe_customer_id = outcome["customer"]
                db.add(Event(user_id=owner.id, event_type="pack_paid",
                             payload={"session_id": session_id,
                                      "campaigns": purchase.campaigns,
                                      "amount_cents": purchase.amount_cents,
                                      "credits_left": owner.campaign_credits}))
    elif purchase and purchase.status == "pending":
        purchase.status = ("expired" if outcome.get("event") == "checkout.session.expired"
                           else "failed")

    db.commit()
    return {"received": True, "status": purchase.status if purchase else "unmatched"}


@router.post("/billing/webhook")
async def stripe_webhook(request: Request, db: Session = Depends(get_db)):
    """Stripe calls this after a payment. Signature-verified, then idempotent on the session.

    Anonymous by design: Stripe has no account here. The signature is the authentication.
    """
    payload = await request.body()
    header = request.headers.get("stripe-signature", "")
    secret = billing.webhook_secret()
    if not secret:
        raise HTTPException(status_code=503, detail="STRIPE_WEBHOOK_SECRET is not set")
    if not billing.verify_webhook(payload, header, secret):
        raise HTTPException(status_code=400, detail="Bad signature")

    event = billing.load_event(payload)
    outcome = billing.checkout_outcome(event)
    if outcome.get("ignored"):
        return {"received": True, "ignored": outcome["event"]}
    # A pack session has no boost and no order: it credits the account's balance instead.
    if outcome.get("kind") == "pack":
        return settle_pack(outcome, db)

    order = None
    if outcome.get("session_id"):
        order = db.query(Order).filter(Order.stripe_session_id == outcome["session_id"]).first()
    boost = db.query(Boost).filter(Boost.id == outcome["boost_id"]).first() if outcome.get("boost_id") else None

    if outcome.get("paid"):
        if not order and boost:
            # The session was created before this deploy, or the row was lost: record it now
            # rather than taking money and leaving the campaign locked.
            order = Order(user_id=outcome.get("user_id") or boost.user_id, boost_id=boost.id,
                          amount_cents=outcome.get("amount_cents") or billing.price_cents(),
                          currency=billing.CURRENCY, status="paid",
                          stripe_session_id=outcome.get("session_id"),
                          stripe_payment_intent=outcome.get("payment_intent"))
            db.add(order)
        if order and order.status != "paid":
            order.status = "paid"
            order.paid_at = datetime.utcnow()
            order.stripe_payment_intent = outcome.get("payment_intent") or order.stripe_payment_intent
        # Belt and braces: if the checkout that paid was created before the account had a
        # customer id, remember the one Stripe actually charged so the next purchase prefills.
        payer = db.query(User).filter(User.id == (order.user_id if order else outcome.get("user_id"))).first()
        if payer is not None and outcome.get("customer") and not payer.stripe_customer_id:
            payer.stripe_customer_id = outcome.get("customer")
        if boost:
            boost.paid_at = datetime.utcnow()
            boost.paid_amount_cents = outcome.get("amount_cents") or billing.price_cents()
        if order:
            db.add(Event(user_id=order.user_id, boost_id=order.boost_id, event_type="campaign_paid",
                         payload={"session_id": outcome.get("session_id"),
                                  "amount_cents": order.amount_cents}))
    elif order and order.status == "pending":
        order.status = "expired" if outcome.get("event") == "checkout.session.expired" else "failed"

    db.commit()
    return {"received": True, "status": order.status if order else "unmatched"}


@router.get("/billing/cards")
async def my_cards(current_user: User = Depends(get_current_user)):
    """The cards Stripe already has for this account, masked. Drives the 'saved card' note."""
    if not billing.billing_enabled():
        return {"enabled": False, "cards": [], "note": "Billing is not configured yet."}
    customer_id = current_user.stripe_customer_id
    if not customer_id:
        return {"enabled": True, "cards": [], "note": "No card saved yet."}
    try:
        cards = await billing.list_cards(customer_id)
    except Exception as exc:  # noqa: BLE001 - a Stripe outage must not break the billing page
        return {"enabled": True, "cards": [], "note": "Could not read saved cards (%s)." %
                type(exc).__name__}
    return {
        "enabled": True,
        "cards": cards,
        "note": ("Your card is saved - checkout will offer it." if cards
                 else "No card saved yet."),
    }


@router.get("/billing/orders")
def my_orders(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """This account's purchases, newest first — the receipts list behind the Billing page."""
    q = db.query(Order)
    if not current_user.is_admin:
        q = q.filter(Order.user_id == current_user.id)
    rows = q.order_by(Order.id.desc()).limit(50).all()
    addresses = {b.id: b.address for b in db.query(Boost).filter(
        Boost.id.in_([o.boost_id for o in rows if o.boost_id])).all()} if rows else {}
    return [{
        "id": o.id, "boost_id": o.boost_id,
        "address": addresses.get(o.boost_id), "status": o.status,
        "amount_cents": o.amount_cents, "amount_label": billing.price_label(o.amount_cents or 0),
        "currency": o.currency, "session_id": o.stripe_session_id,
        "created_at": o.created_at, "paid_at": o.paid_at,
    } for o in rows]


@router.get("/billing/boost/{boost_id}")
def boost_billing(boost_id: int, current_user: User = Depends(get_current_user),
                  db: Session = Depends(get_db)):
    """Whether this campaign is paid for, and its latest order — what the review screen asks."""
    q = db.query(Boost).filter(Boost.id == boost_id)
    if not current_user.is_admin:
        q = q.filter(Boost.user_id == current_user.id)
    boost = q.first()
    if not boost:
        raise HTTPException(status_code=404, detail="Boost not found")
    order = (db.query(Order).filter(Order.boost_id == boost.id)
             .order_by(Order.id.desc()).first())
    return {
        "boost_id": boost.id,
        "paid": bool(boost.paid_at) or (order is not None and order.status == "paid"),
        "exempt": bool(current_user.is_admin),
        "price_cents": billing.price_cents(),
        "price_label": billing.price_label(),
        "order": None if not order else {
            "id": order.id, "status": order.status, "amount_cents": order.amount_cents,
            "checkout_url": order.checkout_url, "paid_at": order.paid_at,
        },
    }
