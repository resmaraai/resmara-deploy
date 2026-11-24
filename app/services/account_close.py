"""Engine 10, sections 9 and 10: closing an account (everything stops at once), chargebacks and
team refunds.

Close my account:
  * scheduled posts cancelled; the ads Resmara runs paused in Meta
  * Run it until it sells off everywhere; built-but-unpaid rounds discarded
  * listing websites show "This page is no longer available"
  * the saved card detached from the Stripe customer; the Meta connection removed
  * "Your account is closed"; logging in within 30 days offers to reopen it (Engine 1, section 5),
    after that the personal details are deleted (purchases kept for tax and accounting)
Posts and ads already published stay on the agent's own Page and ad account: they own them.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any, Dict

from app.db.session import Ad, Boost, Event, ListingSite, Order, Post, User

log = logging.getLogger(__name__)
KEEP_DAYS = 30   # closed accounts can be reopened by logging in until their details are deleted


def _now() -> datetime:
    return datetime.now(timezone.utc)


async def close(db, user: User, *, detach=None, pause_ad=None, send: bool = True) -> Dict[str, Any]:
    from app.services import billing, listing_site, mail, renewals
    done: Dict[str, Any] = {"posts_cancelled": 0, "ads_paused": 0, "renewals_off": 0,
                            "rounds_discarded": 0, "websites_down": 0, "cards_removed": 0}
    boosts = db.query(Boost).filter(Boost.user_id == user.id).all()
    for b in boosts:
        if not b.paid_at and b.parent_boost_id:
            renewals._drop(db, b)
            done["rounds_discarded"] += 1
            continue
        n = (db.query(Post).filter(Post.boost_id == b.id, Post.publish_status.in_(("scheduled", "held")))
             .update({"publish_status": "skipped", "failure_note": "Account closed"}, synchronize_session=False))
        done["posts_cancelled"] += n
        if b.until_sold:
            b.until_sold, b.until_sold_at = False, None
            done["renewals_off"] += 1
        ad = db.query(Ad).filter(Ad.boost_id == b.id).first()
        if ad is not None and ad.meta_ad_id and (ad.status or "") not in ("paused", "ended"):
            try:
                if pause_ad is not None:
                    await pause_ad(ad)
                else:
                    from app.api.boost_control import _set_objects
                    await _set_objects(ad, "PAUSED")
                ad.status = "paused"
                done["ads_paused"] += 1
            except Exception as exc:  # noqa: BLE001 - keep closing; the team can pause it by hand
                log.info("closing %s: ad %s not paused: %s", user.id, ad.id, exc)
        if b.paused_at is None:
            b.paused_at = _now()
            b.paused_reason = "closed"
    db.commit()
    for site in db.query(ListingSite).filter(ListingSite.user_id == user.id).all():
        content = dict(site.content or {})
        content["closed"] = True
        site.content = content
        site.ended_at = _now()
        listing_site.touch(db, site)
        done["websites_down"] += 1
    if user.stripe_customer_id and billing.billing_enabled():
        for card in await billing.list_cards(user.stripe_customer_id):
            ok = await (detach or billing.detach_card)(card["id"])
            done["cards_removed"] += int(bool(ok))
    from app.db.session import AdAccount, MetaConnection
    db.query(MetaConnection).filter(MetaConnection.user_id == user.id).delete(synchronize_session=False)
    for acct in db.query(AdAccount).filter(AdAccount.user_id == user.id).all():
        # The rows stay (past ads point at them); the tokens that let Resmara act on Meta go.
        acct._access_token = None
        acct._refresh_token = None
        acct.token_status = "needs_reconnect"
        acct.token_note = "Account closed"
    db.commit()
    email, first = user.email, (user.name or "").split(" ")[0] or "there"
    if send and email and not str(email).endswith(".invalid"):
        try:
            mail.send_email(email, "Your Resmara account is closed",
                            f"Hi {first},\n\nYour Resmara account is closed. Here's what stopped:\n\n"
                            "- Your scheduled posts and the ads Resmara was running\n"
                            "- Run it until it sells, for every listing\n"
                            "- Your listing websites\n"
                            "- Your saved card (removed from our payment provider)\n"
                            "- Resmara's connection to your Facebook and Instagram\n\n"
                            "Posts and ads that already went out stay on your Page and ad account. Nothing "
                            f"was refunded. Changed your mind? Log in with Facebook in the next {KEEP_DAYS} days "
                            "to reopen it; after that your details are deleted (purchase records are kept "
                            "for tax and accounting).\n\n- Resmara")
        except Exception:  # noqa: BLE001
            pass
    user.is_active = False
    user.closed_at = user.closed_at or _now()
    db.add(Event(user_id=user.id, event_type="account_closed", payload=done))
    db.commit()
    return {"status": "closed", **done}


def wipe_due(db, *, now: datetime | None = None) -> Dict[str, Any]:
    """Daily: accounts closed more than KEEP_DAYS ago lose their personal details for good
    (Engine 1 section 5 / Engine 10 section 10). Purchases stay for tax and accounting."""
    from datetime import timedelta
    from app.core.security import get_password_hash
    cutoff = (now or _now()) - timedelta(days=KEEP_DAYS)
    wiped = []
    for user in db.query(User).filter(User.closed_at.isnot(None), User.is_active.is_(False)).all():
        closed = user.closed_at if user.closed_at.tzinfo else user.closed_at.replace(tzinfo=timezone.utc)
        if closed > cutoff or str(user.email or "").startswith("deleted-"):
            continue
        user.email = f"deleted-{user.id}@resmara.invalid"
        user.name = "Deleted account"
        user.brand = {}
        user.facebook_id = None          # a later Facebook login signs up fresh
        user.hashed_password = get_password_hash(secrets.token_urlsafe(32))
        db.add(Event(user_id=user.id, event_type="account_wiped", payload={}))
        wiped.append(user.id)
    db.commit()
    return {"wiped": wiped}


def dispute(db, outcome: Dict[str, Any]) -> Dict[str, Any]:
    """A chargeback: new charges and Run it until it sells pause on that account, the team is alerted
    with what Stripe needs; won -> everything resumes; lost -> stays paused until support hears."""
    order = db.query(Order).filter(Order.stripe_payment_intent == outcome.get("payment_intent")).first()
    if order is None:
        return {"received": True, "status": "dispute_unmatched"}
    user = db.query(User).filter(User.id == order.user_id).first()
    kind = outcome.get("event")
    if kind == "charge.dispute.created" and user is not None:
        user.billing_hold = "dispute"
        db.add(Event(user_id=user.id, boost_id=order.boost_id, event_type="dispute_opened", payload=outcome))
        db.commit()
        _alert(db, user, order, outcome)
        return {"received": True, "status": "dispute_opened"}
    if kind == "charge.dispute.closed" and user is not None:
        won = outcome.get("status") == "won"
        if won:
            user.billing_hold = None
        db.add(Event(user_id=user.id, boost_id=order.boost_id, event_type="dispute_closed",
                     payload={**outcome, "won": won}))
        db.commit()
        return {"received": True, "status": "dispute_won" if won else "dispute_lost"}
    return {"received": True, "status": "dispute_" + (kind or "").rsplit(".", 1)[-1]}


def _alert(db, user: User, order: Order, outcome: Dict[str, Any]) -> None:
    from app.services import listing_site, mail
    to = listing_site.team_email()
    if not to:
        return
    terms = db.query(Event).filter(Event.user_id == user.id, Event.event_type.in_(("terms_accepted", "signup"))) \
        .order_by(Event.id.asc()).first()
    consent = db.query(Event).filter(Event.user_id == user.id, Event.event_type.like("until_sold%")) \
        .order_by(Event.id.desc()).first()
    boost = db.query(Boost).filter(Boost.id == order.boost_id).first()
    lines = [f"A chargeback was opened on {user.email} ({outcome.get('reason') or 'no reason given'}), "
             f"${(outcome.get('amount') or 0) / 100:.2f}.",
             "New charges and Run it until it sells are paused on the account.",
             "", "What Stripe will want:",
             f"- Terms accepted: {getattr(user, 'terms_version', None) or '-'} at "
             f"{getattr(user, 'terms_accepted_at', None) or (terms.created_at if terms else '-')} "
             f"from {getattr(user, 'terms_ip', None) or '-'}",
             f"- Renewal consent: {consent.event_type + ' ' + str(consent.created_at) if consent else 'none (not on Run it until it sells)'}",
             f"- The receipt: {order.receipt_url or order.stripe_payment_intent}",
             f"- The campaign: {boost.address if boost else order.boost_id} (built and delivered)",
             "", "Answer it in Stripe."]
    try:
        mail.send_email(to, f"Chargeback opened: {user.email}", "\n".join(lines))
    except Exception:  # noqa: BLE001
        pass


async def team_refund(db, order: Order, cents: int | None, reason: str, *, refund_fn=None,
                      send: bool = True) -> Dict[str, Any]:
    """Team room → Finance → Refund (full or partial, with a reason). The agent gets the email."""
    from app.services import billing, mail
    if order.status not in ("paid", "partially_refunded") or not order.stripe_payment_intent:
        raise ValueError("Only a paid purchase can be refunded.")
    left = int(order.amount_cents or 0) + int(order.tax_cents or 0) - int(order.refunded_cents or 0)
    amount = min(int(cents), left) if cents else left
    if amount <= 0:
        raise ValueError("Nothing left to refund on this purchase.")
    result = await (refund_fn or billing.refund)(order.stripe_payment_intent, amount, reason)
    order.refunded_cents = int(order.refunded_cents or 0) + amount
    order.refund_reason = (reason or "")[:500]
    order.status = "refunded" if order.refunded_cents >= int(order.amount_cents or 0) + int(order.tax_cents or 0) \
        else "partially_refunded"
    db.add(Event(user_id=order.user_id, boost_id=order.boost_id, event_type="order_refunded",
                 payload={"order_id": order.id, "cents": amount, "reason": reason[:300],
                          "refund": (result or {}).get("id")}))
    db.commit()
    user = db.query(User).filter(User.id == order.user_id).first()
    boost = db.query(Boost).filter(Boost.id == order.boost_id).first()
    if send and user is not None and user.email and not user.email.endswith(".invalid"):
        street = (boost.address if boost else "your listing").split(",")[0]
        try:
            mail.send_email(user.email, f"We refunded {billing.price_label(amount)} for {street}",
                            f"We refunded {billing.price_label(amount)} for {street}. "
                            "It reaches your card in 5 to 10 days.\n\n- Resmara")
        except Exception:  # noqa: BLE001
            pass
    return {"status": order.status, "refunded_cents": amount}
