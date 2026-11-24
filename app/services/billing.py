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
    return repeat_price_cents() if round_of(boost) >= 1 else price_cents()


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


def round_of(boost) -> int:
    """Which round on the same listing this campaign is: 0 the first time, 1+ for a repeat.

    The round is what decides $49 or $39, so it is also what has to ride on the payment: without
    it a Stripe report can total the money but cannot say how much of it was renewals.
    """
    try:
        return max(0, int(getattr(boost, "repeat_round", 0) or 0))
    except (TypeError, ValueError):
        return 0


def checkout_payload(boost_id: int, user_id: int, address: str, base_url: str,
                     cents: int | None = None, customer_id: str | None = None,
                     save_card: bool = True, round_no: int = 0, embedded: bool = False) -> list:
    """The form-encoded body for POST /v1/checkout/sessions, as a list of pairs.

    A list (not a dict) because Stripe's bracket notation repeats keys; httpx preserves the
    order and repeats, a dict would collapse them.

    With a Customer attached, Checkout prefills that customer's saved cards, so a returning
    client does not retype the number. `setup_future_usage=off_session` is what tells Stripe to
    keep the card on the Customer after this one-off payment - without it the card is used once
    and forgotten.

    `round_no` is stamped on both the session and the payment intent. A repeat round is $39, and
    this is what lets Stripe (and the Team room) tell the two prices apart later without guessing
    from the amount.
    """
    cents = price_cents() if cents is None else cents
    round_no = max(0, int(round_no or 0))
    price_type = "repeat" if round_no >= 1 else "first"
    name = "Resmara campaign — %s" % (address or "your listing")
    if round_no:
        name += " · round %d" % (round_no + 1)
    if embedded:
        # Stripe's form inside our pop-up (the sign-up tour engine, section 9): no jump to a
        # hosted page. Stripe comes back to return_url only for redirect-based methods.
        urls = [("ui_mode", "embedded"),
                ("return_url", "%s/?checkout=done&boost=%d&session_id={CHECKOUT_SESSION_ID}"
                 % (base_url.rstrip("/"), boost_id)),
                ("redirect_on_completion", "if_required")]
    else:
        urls = [("success_url", _success_url(base_url, boost_id)),
                ("cancel_url", _cancel_url(base_url, boost_id))]
    pairs = [
        ("mode", "payment"),
        *urls,
        ("client_reference_id", str(boost_id)),
        ("line_items[0][quantity]", "1"),
        ("line_items[0][price_data][currency]", CURRENCY),
        ("line_items[0][price_data][unit_amount]", str(cents)),
        ("line_items[0][price_data][product_data][name]", name[:250]),
        ("metadata[boost_id]", str(boost_id)),
        ("metadata[user_id]", str(user_id)),
        ("metadata[round]", str(round_no)),
        ("metadata[price_type]", price_type),
        ("metadata[price_cents]", str(cents)),
        # One campaign, one purchase: the webhook is idempotent on the session id, and this
        # key keeps a double-clicked button from opening two checkout pages for one boost.
        ("payment_intent_data[metadata][boost_id]", str(boost_id)),
        # The same three facts on the PaymentIntent, which is the object Stripe's own revenue
        # reports and Sigma queries read.
        ("payment_intent_data[metadata][round]", str(round_no)),
        ("payment_intent_data[metadata][price_type]", price_type),
        ("payment_intent_data[metadata][price_cents]", str(cents)),
    ]
    if tax_enabled():
        # Engine 10, section 6: Stripe Tax adds tax where a state requires it, from the card's ZIP.
        pairs.append(("automatic_tax[enabled]", "true"))
        pairs.append(("line_items[0][price_data][tax_behavior]", "exclusive"))
        pairs.append(("line_items[0][price_data][product_data][tax_code]", TAX_CODE))
        pairs.append(("billing_address_collection", "auto"))
    if customer_id:
        pairs.append(("customer", customer_id))
        # A customer moving house should not leave checkout with a stale billing address.
        pairs.append(("customer_update[address]", "auto"))
        if save_card:
            pairs.append(("payment_intent_data[setup_future_usage]", "off_session"))
    return pairs


async def retrieve_session(session_id: str, client: httpx.AsyncClient | None = None) -> dict:
    """Read one Checkout session back from Stripe (the embedded form's completion check)."""
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        resp = await client.get("%s/checkout/sessions/%s" % (STRIPE_API, session_id),
                                headers={"Authorization": "Bearer %s" % secret_key()})
        resp.raise_for_status()
        return resp.json()
    finally:
        if owns:
            await client.aclose()


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
                                  customer_id: str | None = None, save_card: bool = True,
                                  round_no: int = 0, embedded: bool = False) -> dict:
    """Create a Stripe Checkout session and return its JSON (id + url).

    Raises httpx.HTTPStatusError on a refusal so the caller can surface Stripe's own message
    instead of a generic failure.
    """
    if not billing_enabled():
        raise RuntimeError("Stripe is not configured: set STRIPE_SECRET_KEY on the service.")
    data = checkout_payload(boost_id, user_id, address, base_url, cents,
                            customer_id=customer_id, save_card=save_card, round_no=round_no,
                            embedded=embedded)
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


# ── saved card: add one without buying, then charge it on Build ───────────────
# The agent adds a card once (Stripe Checkout in setup mode: nothing is charged). From then on,
# clicking Build on a campaign IS the approval: the server charges that card off-session for the
# campaign's price, with no second page. A card the bank will not charge without the agent present
# (3-D Secure, a decline) falls back to the normal Checkout page, which can ask them.


def card_setup_payload(customer_id: str, user_id: int, base_url: str, embedded: bool = False) -> list:
    """The body for a Checkout session that only saves a card (mode=setup): no charge.

    embedded=True is Stripe's form inside the Resmara pop-up (Engine 10, section 4), never a
    separate Stripe page."""
    base = (base_url or "").rstrip("/")
    urls = ([("ui_mode", "embedded"), ("return_url", "%s/?card=saved&session_id={CHECKOUT_SESSION_ID}" % base),
             ("redirect_on_completion", "if_required")] if embedded else
            [("success_url", "%s/?card=saved" % base), ("cancel_url", "%s/?card=cancelled" % base)])
    return [
        ("mode", "setup"),
        ("customer", customer_id),
        ("currency", CURRENCY),
        ("payment_method_types[0]", "card"),
        *urls,
        # kind=card_setup tells the webhook this session has no campaign and no order behind it.
        ("metadata[kind]", "card_setup"),
        ("metadata[user_id]", str(user_id)),
        ("setup_intent_data[metadata][user_id]", str(user_id)),
    ]


async def create_card_setup_session(customer_id: str, user_id: int, base_url: str,
                                    client: httpx.AsyncClient | None = None, embedded: bool = False) -> dict:
    """Create the 'add a card' Checkout session and return its JSON (id + url)."""
    if not billing_enabled():
        raise RuntimeError("Stripe is not configured: set STRIPE_SECRET_KEY on the service.")
    body, headers = form_body(card_setup_payload(customer_id, user_id, base_url, embedded=embedded))
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        resp = await client.post("%s/checkout/sessions" % STRIPE_API, content=body, headers=headers)
        resp.raise_for_status()
        return resp.json()
    finally:
        if owns:
            await client.aclose()


def saved_card_charge_payload(customer_id: str, payment_method_id: str, cents: int, boost_id: int,
                              user_id: int, address: str = "", round_no: int = 0) -> list:
    """The body for an off-session PaymentIntent on the agent's saved card, confirmed at once.

    Same metadata as a Checkout payment (boost, round, price type, price), so Finance and Stripe's
    own reports cannot tell a one-click charge from a Checkout one.
    """
    round_no = max(0, int(round_no or 0))
    price_type = "repeat" if round_no >= 1 else "first"
    desc = "Resmara campaign — %s" % (address or "your listing")
    if round_no:
        desc += " · round %d" % (round_no + 1)
    return [
        ("amount", str(int(cents))),
        ("currency", CURRENCY),
        ("customer", customer_id),
        ("payment_method", payment_method_id),
        ("off_session", "true"),
        ("confirm", "true"),
        ("description", desc[:250]),
        ("metadata[boost_id]", str(boost_id)),
        ("metadata[user_id]", str(user_id)),
        ("metadata[round]", str(round_no)),
        ("metadata[price_type]", price_type),
        ("metadata[price_cents]", str(int(cents))),
        ("metadata[kind]", "saved_card"),
    ]


async def charge_saved_card(customer_id: str, payment_method_id: str, cents: int, boost_id: int,
                            user_id: int, address: str = "", round_no: int = 0,
                            client: httpx.AsyncClient | None = None) -> dict:
    """Charge the saved card now. Returns {"paid": bool, "payment_intent": id, "message": str}.

    Never raises for a declined card: a decline is an answer, not an error. The idempotency key
    is per campaign and round, so a double-clicked Build cannot charge twice.
    """
    if not billing_enabled():
        raise RuntimeError("Stripe is not configured: set STRIPE_SECRET_KEY on the service.")
    # Engine 10, section 6: tax on top where the state requires it (0 when Stripe Tax is off).
    tax = await tax_for(customer_id, cents, "boost-%s-round-%s" % (boost_id, int(round_no or 0)), client=client)
    pairs = saved_card_charge_payload(customer_id, payment_method_id, cents, boost_id, user_id, address, round_no)
    if tax["tax_cents"]:
        pairs = [(k, str(tax["total_cents"]) if k == "amount" else v) for k, v in pairs]
        pairs += [("metadata[tax_cents]", str(tax["tax_cents"])), ("metadata[tax_calculation]", tax["calculation"] or "")]
    body, headers = form_body(pairs)
    # The card is in the key too: after a decline the agent can add a new card and the retry must
    # reach Stripe instead of replaying the cached decline.
    headers["Idempotency-Key"] = "resmara-boost-%s-round-%s-%s-%s" % (
        boost_id, int(round_no or 0), int(cents), payment_method_id)
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        resp = await client.post("%s/payment_intents" % STRIPE_API, content=body, headers=headers)
        data = {}
        try:
            data = resp.json()
        except Exception:  # noqa: BLE001
            data = {}
        if resp.status_code >= 400:
            err = data.get("error") or {}
            if resp.status_code == 402 or err.get("type") == "card_error":
                intent = err.get("payment_intent") or {}
                return {"paid": False, "payment_intent": intent.get("id"),
                        "message": err.get("message") or "Your card was declined."}
            resp.raise_for_status()
        status = data.get("status")
        if status == "succeeded":
            await record_tax(tax["calculation"], data.get("id"), client=client)
            return {"paid": True, "payment_intent": data.get("id"), "message": "", "tax_cents": tax["tax_cents"]}
        return {"paid": False, "payment_intent": data.get("id"),
                "message": "Your bank wants to confirm this payment."}
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


# ── Engine 10: tax, the card, receipts, refunds, disputes ──────────────────────
TAX_CODE = "txcd_10103001"   # Software as a Service (SaaS) - Business Use (agents buy it for their business)


def tax_enabled() -> bool:
    """On only once Adam has switched Stripe Tax on in Stripe (RESMARA_STRIPE_TAX=1)."""
    return os.getenv("RESMARA_STRIPE_TAX", "").strip().lower() in ("1", "true", "yes", "on")


async def stripe_call(method: str, path: str, pairs: list | None = None, params: dict | None = None,
                      idem: str | None = None, client: httpx.AsyncClient | None = None) -> dict:
    """One Stripe API call. Raises httpx.HTTPStatusError on a refusal (with Stripe's JSON kept)."""
    if not billing_enabled():
        raise RuntimeError("Stripe is not configured: set STRIPE_SECRET_KEY on the service.")
    owns = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        if method == "GET":
            resp = await client.get("%s%s" % (STRIPE_API, path), params=params or {},
                                    headers={"Authorization": "Bearer %s" % secret_key()})
        else:
            body, headers = form_body(pairs or [])
            if idem:
                headers["Idempotency-Key"] = idem
            resp = await client.request(method, "%s%s" % (STRIPE_API, path), content=body, headers=headers)
        resp.raise_for_status()
        return resp.json()
    finally:
        if owns:
            await client.aclose()


async def tax_for(customer_id: str, cents: int, reference: str, client=None) -> dict:
    """Stripe Tax for an off-session charge: {"tax_cents", "total_cents", "calculation"}.
    No tax (Stripe Tax off, or the state doesn't tax it, or no address yet) -> tax 0."""
    if not tax_enabled() or not customer_id:
        return {"tax_cents": 0, "total_cents": int(cents), "calculation": None}
    try:
        calc = await stripe_call("POST", "/tax/calculations", [
            ("currency", CURRENCY), ("customer", customer_id),
            ("line_items[0][amount]", str(int(cents))), ("line_items[0][reference]", reference[:200]),
            ("line_items[0][tax_code]", TAX_CODE), ("line_items[0][tax_behavior]", "exclusive"),
        ], client=client)
    except Exception:  # noqa: BLE001 - an address Stripe can't place: no tax, never a failed charge
        return {"tax_cents": 0, "total_cents": int(cents), "calculation": None}
    return {"tax_cents": int(calc.get("tax_amount_exclusive") or 0),
            "total_cents": int(calc.get("amount_total") or cents), "calculation": calc.get("id")}


async def record_tax(calculation: str | None, payment_intent: str | None, client=None) -> None:
    """Record the tax for filing, and keep the transaction id on the payment so a refund can reverse it."""
    if not calculation or not payment_intent:
        return
    try:
        tx = await stripe_call("POST", "/tax/transactions/create_from_calculation",
                               [("calculation", calculation), ("reference", payment_intent)], client=client)
        if tx.get("id"):
            await stripe_call("POST", "/payment_intents/%s" % payment_intent,
                              [("metadata[tax_transaction]", tx["id"])], client=client)
    except Exception:  # noqa: BLE001 - logged in Stripe; the charge stands
        pass


async def reverse_tax(payment_intent: str, cents: int | None, refund_id: str | None, client=None) -> None:
    """A refund on a taxed charge reverses that tax too, so it isn't filed as collected."""
    if not tax_enabled() or not payment_intent:
        return
    try:
        pi = await stripe_call("GET", "/payment_intents/%s" % payment_intent, client=client)
        tx = ((pi or {}).get("metadata") or {}).get("tax_transaction")
        if not tx:
            return
        pairs = [("original_transaction", tx), ("reference", refund_id or "refund-%s" % payment_intent)]
        pairs += [("mode", "partial"), ("flat_amount", str(-int(cents)))] if cents else [("mode", "full")]
        await stripe_call("POST", "/tax/transactions/create_reversal", pairs, client=client)
    except Exception:  # noqa: BLE001 - the refund stands; the team can reverse it in Stripe
        pass


async def detach_card(payment_method_id: str, client=None) -> bool:
    try:
        await stripe_call("POST", "/payment_methods/%s/detach" % payment_method_id, [], client=client)
        return True
    except Exception:  # noqa: BLE001
        return False


async def keep_only_card(customer_id: str, keep_id: str, client=None) -> int:
    """Change card: the new card replaces the old one for everything (Engine 10, section 4)."""
    removed = 0
    for card in await list_cards(customer_id, client=client):
        if card.get("id") and card["id"] != keep_id and await detach_card(card["id"], client=client):
            removed += 1
    try:
        await stripe_call("POST", "/customers/%s" % customer_id,
                          [("invoice_settings[default_payment_method]", keep_id)], client=client)
    except Exception:  # noqa: BLE001
        pass
    return removed


async def setup_session_card(session_id: str, client=None) -> str | None:
    """The card a finished card-setup session saved."""
    session = await stripe_call("GET", "/checkout/sessions/%s" % session_id,
                                params={"expand[]": "setup_intent"}, client=client)
    intent = session.get("setup_intent") or {}
    if isinstance(intent, str):
        intent = await stripe_call("GET", "/setup_intents/%s" % intent, client=client)
    return intent.get("payment_method") if intent.get("status") == "succeeded" else None


async def receipt(payment_intent: str, client=None) -> dict:
    """{"receipt_url", "tax_cents"} for a payment, read back from Stripe."""
    try:
        pi = await stripe_call("GET", "/payment_intents/%s" % payment_intent,
                               params={"expand[]": "latest_charge"}, client=client)
    except Exception:  # noqa: BLE001
        return {}
    charge = pi.get("latest_charge") or {}
    return {"receipt_url": charge.get("receipt_url") if isinstance(charge, dict) else None,
            "tax_cents": int((pi.get("metadata") or {}).get("tax_cents") or 0)}


async def refund(payment_intent: str, cents: int | None = None, reason: str = "", client=None) -> dict:
    pairs = [("payment_intent", payment_intent), ("metadata[reason]", (reason or "")[:300])]
    if cents:
        pairs.append(("amount", str(int(cents))))
    result = await stripe_call("POST", "/refunds", pairs, idem="resmara-refund-%s-%s" % (payment_intent, cents or "full"),
                               client=client)
    await reverse_tax(payment_intent, cents, (result or {}).get("id"), client=client)
    return result


def dispute_outcome(event: dict) -> dict | None:
    """charge.dispute.created / closed -> {"event", "payment_intent", "status", "amount"}."""
    kind = (event or {}).get("type") or ""
    if not kind.startswith("charge.dispute."):
        return None
    obj = ((event or {}).get("data") or {}).get("object") or {}
    return {"event": kind, "dispute": obj.get("id"), "payment_intent": obj.get("payment_intent"),
            "status": obj.get("status"), "amount": _as_int(obj.get("amount")), "reason": obj.get("reason")}
