"""One property campaign costs $49. Stripe Checkout takes the card; this module is the only
place that talks to Stripe.

The credit system this replaces priced a build in invented "campaign credits" that nobody
could buy, so the dashboard advertised a balance it could never fund. A campaign is now a
one-off purchase: POST /api/billing/checkout asks Stripe for a hosted checkout page, and the
webhook marks the order paid. Card data never reaches this app.

No STRIPE_SECRET_KEY means billing is disabled, not silently free: the endpoints answer 503
with a readable reason, and build/launch keep refusing an unpaid campaign.
"""
import hashlib
import hmac
import json
import os
import time

import httpx

STRIPE_API = "https://api.stripe.com/v1"

# $49 per campaign, in the smallest currency unit. Overridable so a promo does not need a
# deploy, but the default is the published price and the tests pin it.
DEFAULT_PRICE_CENTS = 4900
# A second campaign on a listing that did not sell is cheaper: the photos, the plan's brand
# work and the connection are already done (Ad Engine v1.3 §4.6).
DEFAULT_REPEAT_PRICE_CENTS = 3900
CURRENCY = "usd"


def price_cents() -> int:
    """The price of one campaign in cents. Bad configuration falls back to $49."""
    raw = (os.getenv("STRIPE_PRICE_CENTS") or "").strip()
    if not raw:
        return DEFAULT_PRICE_CENTS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_PRICE_CENTS
    return value if value > 0 else DEFAULT_PRICE_CENTS


def repeat_price_cents() -> int:
    """What a second campaign on the same listing costs. Overridable, defaults to $39."""
    raw = (os.getenv("STRIPE_REPEAT_PRICE_CENTS") or "").strip()
    if not raw:
        return DEFAULT_REPEAT_PRICE_CENTS
    try:
        value = int(raw)
    except ValueError:
        return DEFAULT_REPEAT_PRICE_CENTS
    return value if value > 0 else DEFAULT_REPEAT_PRICE_CENTS


def price_for(boost) -> int:
    """The price of *this* campaign: $49 the first time, $39 for a repeat (§4.6)."""
    try:
        round_no = int(getattr(boost, "repeat_round", 0) or 0)
    except (TypeError, ValueError):
        round_no = 0
    return repeat_price_cents() if round_no >= 1 else price_cents()


def price_label(cents: int | None = None) -> str:
    cents = price_cents() if cents is None else cents
    return "$%d" % (cents // 100) if cents % 100 == 0 else "$%.2f" % (cents / 100.0)


# ── prepaid campaigns (legacy, no longer sold) ─────────────────────────────
# A $196 four-campaign pack used to be offered here. It is not part of the product: a campaign is
# bought on its own for $49, and a second campaign on the same listing is just another campaign.
# The credit balance and CreditPurchase rows stay readable so any pack already paid for is still
# honoured, but nothing in the UI sells one and no new pack session is created.

def secret_key() -> str:
    return (os.getenv("STRIPE_SECRET_KEY") or "").strip()


def publishable_key() -> str:
    return (os.getenv("STRIPE_PUBLISHABLE_KEY") or "").strip()


def webhook_secret() -> str:
    return (os.getenv("STRIPE_WEBHOOK_SECRET") or "").strip()


def billing_enabled() -> bool:
    """True only when there is a key to charge with — never guess at a live secret."""
    key = secret_key()
    return bool(key) and key.startswith(("sk_", "rk_"))


def _success_url(base: str, boost_id: int) -> str:
    return "%s/?checkout=success&boost=%d" % (base.rstrip("/"), boost_id)


def _cancel_url(base: str, boost_id: int) -> str:
    return "%s/?checkout=cancelled&boost=%d" % (base.rstrip("/"), boost_id)


def checkout_payload(boost_id: int, user_id: int, address: str, base_url: str,
                     cents: int | None = None, customer_id: str | None = None,
                     save_card: bool = True) -> list:
    """The form-encoded body for POST /v1/checkout/sessions, as a list of pairs.

    A list (not a dict) because Stripe's bracket notation repeats keys; httpx preserves the
    order and repeats, a dict would collapse them.

    With a Customer attached, Checkout prefills that customer's saved cards, so a returning
    client does not retype the number. `setup_future_usage=off_session` is what tells Stripe to
    keep the card on the Customer after this one-off payment - without it the card is used once
    and forgotten.
    """
    cents = price_cents() if cents is None else cents
    name = "Resmara campaign — %s" % (address or "your listing")
    pairs = [
        ("mode", "payment"),
        ("success_url", _success_url(base_url, boost_id)),
        ("cancel_url", _cancel_url(base_url, boost_id)),
        ("client_reference_id", str(boost_id)),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][currency]", CURRENCY),
        ("line_items[0][price_data][unit_amount]", str(cents)),
        ("line_items[0][price_data][product_data][name]", name[:250]),
        ("metadata[boost_id]", str(boost_id)),
        ("metadata[user_id]", str(user_id)),
        # One campaign, one purchase: the webhook is idempotent on the session id, and this
        # key keeps a double-clicked button from opening two checkout pages for one boost.
        ("payment_intent_data[metadata][boost_id]", str(boost_id)),
    ]
    if customer_id:
        pairs.append(("customer", customer_id))
        # A customer moving house should not leave checkout with a stale billing address.
        pairs.append(("customer_update[address]", "auto"))
        if save_card:
            pairs.append(("payment_intent_data[setup_future_usage]", "off_session"))
    return pairs


def form_body(pairs: list) -> tuple[bytes, dict]:
    """(body, headers) for a Stripe POST that repeats keys.

    httpx's AsyncClient refuses a list of pairs passed as `data=` ("Attempted to send an sync
    request with an AsyncClient instance" - it builds a sync byte stream), so the form is encoded
    here and sent as `content=`. urlencode keeps every duplicate key, which is exactly what
    Stripe's bracket notation needs.
    """
    from urllib.parse import urlencode
    return (urlencode(pairs).encode("utf-8"),
            {"Content-Type": "application/x-www-form-urlencoded",
             "Authorization": "Bearer %s" % secret_key()})


async def create_checkout_session(boost_id: int, user_id: int, address: str, base_url: str,
                                  cents: int | None = None, client: httpx.AsyncClient | None = None,
                                  customer_id: str | None = None, save_card: bool = True) -> dict:
    """Create a Stripe Checkout session and return its JSON (id + url).

    Raises httpx.HTTPStatusError on a refusal so the caller can surface Stripe's own message
    instead of a generic failure.
    """
    if not billing_enabled():
        raise RuntimeError("Stripe is not configured: set STRIPE_SECRET_KEY on the service.")
    data = checkout_payload(boost_id, user_id, address, base_url, cents,
                            customer_id=customer_id, save_card=save_card)
    body, headers = form_body(data)
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        resp = await client.post("%s/checkout/sessions" % STRIPE_API, content=body, headers=headers)
        resp.raise_for_status()
        return resp.json()
    finally:
        if owns:
            await client.aclose()


async def ensure_customer(user_id: int, email: str, name: str = "",
                          client: httpx.AsyncClient | None = None) -> str:
    """The Stripe Customer id for this account, creating one on first use.

    One Customer per account is the whole trick behind "don't ask me for the card again": Stripe
    keeps the saved card on the Customer, not on our server, and Checkout prefills it whenever
    the session carries this id.
    """
    if not billing_enabled():
        raise RuntimeError("Stripe is not configured: set STRIPE_SECRET_KEY on the service.")
    data = [("email", email or ""), ("metadata[user_id]", str(user_id))]
    if name:
        data.append(("name", name[:200]))
    body, headers = form_body(data)
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        resp = await client.post("%s/customers" % STRIPE_API, content=body, headers=headers)
        resp.raise_for_status()
        body = resp.json()
        customer_id = body.get("id")
        if not isinstance(customer_id, str) or not customer_id.startswith("cus_"):
            raise RuntimeError("Stripe did not return a customer id: %s" % str(body)[:200])
        return customer_id
    finally:
        if owns:
            await client.aclose()


def card_label(card: dict) -> str:
    """'Visa •••• 4242, expires 04/2029' — enough to recognise a card, never enough to use it."""
    brand = str((card or {}).get("brand") or "Card").title()
    last4 = str((card or {}).get("last4") or "••••")
    month = (card or {}).get("exp_month")
    year = (card or {}).get("exp_year")
    if month and year:
        return "%s •••• %s, expires %02d/%d" % (brand, last4, int(month), int(year))
    return "%s •••• %s" % (brand, last4)


async def list_cards(customer_id: str, client: httpx.AsyncClient | None = None) -> list[dict]:
    """The cards this customer can pay with, for the 'pay with your saved card' line in the UI.

    Read-only and deliberately never returns anything but the summary fields.
    """
    if not billing_enabled() or not customer_id:
        return []
    headers = {"Authorization": "Bearer %s" % secret_key()}
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        resp = await client.get("%s/payment_methods" % STRIPE_API,
                                params={"customer": customer_id, "type": "card", "limit": 5},
                                headers=headers)
        resp.raise_for_status()
        out = []
        for card in (resp.json().get("data") or []):
            info = card.get("card") or {}
            out.append({
                "id": card.get("id"),
                "brand": info.get("brand"),
                "last4": info.get("last4"),
                "exp_month": info.get("exp_month"),
                "exp_year": info.get("exp_year"),
                "label": card_label(info),
            })
        return out
    finally:
        if owns:
            await client.aclose()


def parse_signature_header(header: str) -> tuple[int, list[str]]:
    """Split a Stripe-Signature header into (timestamp, [v1 signatures])."""
    ts = 0
    sigs: list[str] = []
    for part in (header or "").split(","):
        if "=" not in part:
            continue
        k, v = part.split("=", 1)
        k = k.strip()
        if k == "t":
            try:
                ts = int(v.strip())
            except ValueError:
                ts = 0
        elif k == "v1":
            sigs.append(v.strip())
    return ts, sigs


def verify_webhook(payload: bytes, header: str, secret: str, tolerance: int = 300,
                   now: float | None = None) -> bool:
    """True when the payload really came from Stripe.

    Stripe signs the string "{timestamp}.{raw body}" with the endpoint secret. The timestamp
    check stops a captured request being replayed later; comparison is constant time.
    """
    if not secret:
        return False
    ts, sigs = parse_signature_header(header)
    if not ts or not sigs:
        return False
    now = time.time() if now is None else now
    if tolerance and abs(now - ts) > tolerance:
        return False
    signed = b"%d.%s" % (ts, payload)
    expected = hmac.new(secret.encode(), signed, hashlib.sha256).hexdigest()
    return any(hmac.compare_digest(expected, s) for s in sigs)


def checkout_outcome(event: dict) -> dict:
    """What a webhook event means for us: which order, paid or not.

    Kept pure so the webhook's decision is testable without a database or a network call.
    """
    kind = (event or {}).get("type") or ""
    obj = ((event or {}).get("data") or {}).get("object") or {}
    meta = obj.get("metadata") or {}
    if kind == "checkout.session.completed":
        paid = (obj.get("payment_status") or "").lower() in ("paid", "no_payment_required")
        return {"event": kind, "session_id": obj.get("id"), "paid": paid,
                # A pack session carries no boost: kind=pack is what sends the webhook to
                # credit_purchases instead of hunting for an order that cannot exist yet.
                "kind": (meta.get("kind") or "campaign"),
                "campaigns": _as_int(meta.get("campaigns")),
                "boost_id": _as_int(meta.get("boost_id")),
                "user_id": _as_int(meta.get("user_id")),
                "amount_cents": _as_int(obj.get("amount_total")),
                "payment_intent": obj.get("payment_intent"),
                "customer": obj.get("customer")}
    if kind in ("checkout.session.expired", "checkout.session.async_payment_failed"):
        return {"event": kind, "session_id": obj.get("id"), "paid": False,
                "kind": (meta.get("kind") or "campaign"),
                "campaigns": _as_int(meta.get("campaigns")),
                "boost_id": _as_int(meta.get("boost_id")),
                "user_id": _as_int(meta.get("user_id")),
                "amount_cents": _as_int(obj.get("amount_total")),
                "payment_intent": obj.get("payment_intent")}
    return {"event": kind, "session_id": obj.get("id"), "paid": False, "ignored": True}


def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def load_event(payload: bytes) -> dict:
    """Parse a webhook body, tolerating the odd non-object payload."""
    try:
        data = json.loads(payload.decode("utf-8") or "{}")
    except (UnicodeDecodeError, json.JSONDecodeError):
        return {}
    return data if isinstance(data, dict) else {}


async def refund_failed_build(boost, db) -> dict:
    """A build that dies after the agent paid gives the money back (owner item 16).

    "If a build fails after charging, refund or retry automatically." Both, in the order that
    costs the agent least: a prepaid campaign returns to their balance, and a card payment is
    refunded at Stripe. The campaign is left unpaid either way, so the retry the UI offers is
    genuinely free instead of quietly charging a second time.
    """
    from app.db.session import Event, Order, User

    if not getattr(boost, "paid_at", None):
        return {"refunded": False, "reason": "this campaign was never charged"}
    amount = int(getattr(boost, "paid_amount_cents", 0) or 0)

    if amount == 0:
        # Paid from a prepaid balance: the credit goes back where it came from.
        owner = db.query(User).filter(User.id == boost.user_id).first()
        if owner:
            owner.campaign_credits = int(owner.campaign_credits or 0) + 1
        boost.paid_at = None
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="credit_returned",
                     payload={"reason": "the build failed before any posts were made"}))
        db.commit()
        return {"refunded": True, "kind": "credit", "credits": int(owner.campaign_credits or 0)
                if owner else None}

    order = (db.query(Order).filter(Order.boost_id == boost.id, Order.status == "paid")
             .order_by(Order.id.desc()).first())
    intent = (order.stripe_payment_intent if order else "") or ""
    if not intent or not billing_enabled():
        # No intent on record (an admin-built campaign, or a payment taken before we stored it)
        # is not refundable by us; record it so the operator can do it in Stripe, and do not
        # pretend the money moved.
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="refund_pending",
                     payload={"amount_cents": amount,
                              "reason": "no payment intent on this order" if order
                              else "no paid order found"}))
        db.commit()
        return {"refunded": False, "pending": True, "amount_cents": amount,
                "reason": "This one has to be refunded in Stripe."}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post("https://api.stripe.com/v1/refunds",
                                     auth=(secret_key(), ""),
                                     data={"payment_intent": intent},
                                     headers={"Idempotency-Key": f"refund-boost-{boost.id}"})
        body = resp.json() if resp.content else {}
    except Exception as exc:  # noqa: BLE001 - a failed refund is reported, never assumed
        body, resp = {"error": {"message": f"{type(exc).__name__}: {exc}"}}, None
    if resp is not None and resp.status_code < 300 and body.get("id"):
        boost.paid_at = None
        if order:
            order.status = "refunded"
        db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="refund_issued",
                     payload={"amount_cents": amount, "refund_id": body["id"],
                              "payment_intent": intent}))
        db.commit()
        return {"refunded": True, "kind": "card", "amount_cents": amount,
                "refund_id": body["id"]}

    message = ((body.get("error") or {}).get("message") or "Stripe refused the refund")[:300]
    db.add(Event(user_id=boost.user_id, boost_id=boost.id, event_type="refund_failed",
                 payload={"amount_cents": amount, "error": message}))
    db.commit()
    return {"refunded": False, "error": message, "amount_cents": amount}
