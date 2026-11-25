"""Transactional email: password resets, invitations, receipts, support notices.

Two providers, tried in this order:

1. **Resend** (``RESEND_API_KEY``, optional ``MAIL_FROM``) — an HTTP API, so it works on hosts
   that block outbound SMTP (Render's free tier silently drops port 587, which is how "email is
   broken" looks from the outside). Its free tier is 100 messages/day, which is why it is first
   and not the only one.
2. **SMTP** (``SMTP_HOST``/``SMTP_USER``/``SMTP_PASSWORD``) — Gmail with an app password once the
   resmara.com Workspace mailbox exists, or any relay.

SMTP is a real fallback, not just a second config option: an unverified sending domain (403) or
an exhausted daily quota (429) must not swallow a password reset while a working mailbox sits
right there. Each provider gets exactly one attempt — no retry loop — so a request that is going
to fail fails fast instead of holding the caller for a minute.

Nothing is faked: with no provider, ``send_email`` returns ``False`` and ``last_attempt()`` says
why, and the caller tells the person. A reset link that was never sent must never be reported as
sent. The API key is read from the environment and written only into the request header; it is
never logged, echoed in a response, or pasted into a reason string.
"""
import os
import re
import smtplib
from email.message import EmailMessage

import httpx

RESEND_ENDPOINT = "https://api.resend.com/emails"

# support@ is the address customers are told to write to. A password reset arriving from an
# address they have never seen reads as phishing, and Gmail files it as such.
DEFAULT_FROM = "Resmara <support@resmara.com>"

# Where a customer's reply should land. support@resmara.com is a live Google Workspace mailbox
# (Nov 2026), so a reply to a reset, receipt or support notice reaches a person instead of the
# sending account. MAIL_REPLY_TO overrides it; the header is set on both providers so switching
# transport cannot quietly drop it.
DEFAULT_REPLY_TO = "support@resmara.com"

# What the last send attempt actually did. This is what the operator console and the event log
# report, so "email is configured" and "the message went" stop looking identical. Holds no
# credential: provider names, a boolean and human-readable reasons only.
_LAST = {"provider": "", "ok": False, "reason": "", "errors": [], "fell_back": False}


def _env(name: str) -> str:
    return (os.getenv(name) or "").strip()


def resend_key() -> str:
    return _env("RESEND_API_KEY")


def smtp_configured() -> bool:
    return bool(_env("SMTP_HOST") and _env("SMTP_USER") and _env("SMTP_PASSWORD"))


def try_order() -> list:
    """Who a send will try, in order: Resend, then SMTP, then nobody."""
    order = []
    if resend_key():
        order.append("resend")
    if smtp_configured():
        order.append("smtp")
    return order


def provider() -> str:
    """Which provider a send would try first: 'resend', 'smtp' or '' (nothing configured)."""
    order = try_order()
    return order[0] if order else ""


def mail_configured() -> bool:
    return bool(try_order())


def default_sender() -> str:
    """Who the mail comes from. Resend needs a verified domain or its onboarding address; a
    Gmail/Workspace account sends as itself and rewrites anything else."""
    return _env("MAIL_FROM") or _env("SMTP_FROM") or DEFAULT_FROM


def default_reply_to() -> str:
    """Who a reply goes to. Always an address on the domain customers already know."""
    return _env("MAIL_REPLY_TO") or DEFAULT_REPLY_TO


# Resend's own test sender. It delivers to the account owner and to nobody else, so a send that
# "works" with it in place still leaves every customer without their reset or confirmation.
TEST_SENDER_DOMAINS = ("resend.dev",)


def _address_of(sender: str) -> str:
    """'Resmara <support@resmara.com>' -> 'support@resmara.com'."""
    sender = (sender or "").strip()
    if "<" in sender and ">" in sender:
        return sender[sender.index("<") + 1:sender.index(">")].strip()
    return sender


def _domain_of(sender: str) -> str:
    address = _address_of(sender)
    return address.rsplit("@", 1)[-1].lower() if "@" in address else ""


def verified_domains() -> list:
    """Domains Resend has confirmed, from MAIL_VERIFIED_DOMAINS (comma separated).

    A sending-only API key cannot read /domains, so the app cannot ask Resend whether resmara.com
    is verified. Until somebody records the confirmation - or a real send succeeds - the console
    says the domain is unconfirmed rather than reporting a healthy provider whose every message
    Resend refuses.
    """
    return [d.strip().lower() for d in _env("MAIL_VERIFIED_DOMAINS").split(",") if d.strip()]


def _send_via_resend(to: str, subject: str, body: str):
    """One POST to Resend. Returns (accepted, reason).

    The key exists only in this Authorization header for the length of the call. The response
    body is deliberately not put into the reason: an error payload can echo the request, and a
    credential in a log line or an HTTP response is a leaked credential.
    """
    try:
        resp = httpx.post(
            RESEND_ENDPOINT,
            timeout=10,  # short: a dead primary must not stall the fallback behind it
            headers={"Authorization": "Bearer %s" % resend_key()},
            json={"from": default_sender(), "to": [to], "subject": subject, "text": body,
                  "reply_to": default_reply_to()},
        )
    except httpx.HTTPError as exc:
        return False, "resend unreachable (%s)" % exc.__class__.__name__

    if resp.status_code in (200, 201, 202):
        return True, ""
    return False, _resend_reason(resp)


def _resend_message(resp) -> str:
    """Resend's own sentence from an error body, shortened and stripped of anything key-shaped.

    The reason is stored on events and shown in the operator console, so it carries the
    actionable text ("the domain is not verified") and never the request that produced it.
    """
    body = None
    try:
        body = resp.json()
    except Exception:  # noqa: BLE001 - a non-JSON body (a Cloudflare page) is still evidence
        body = None
    message = ""
    if isinstance(body, dict):
        message = str(body.get("message") or body.get("name") or "")
    if not message:
        message = (resp.text or "").strip()
    message = " ".join(message.split())
    message = re.sub(r"\b(?:re|sk|rk)_[A-Za-z0-9_\-]{6,}", "[redacted]", message)
    return message[:160]


def _resend_reason(resp) -> str:
    """What a refused send actually means. One guess ("key or domain") hides both diagnoses.

    A 403 is three different problems - an unverified domain, the test sender addressing a
    stranger, or Cloudflare answering before Resend ever sees the request - and the fix differs
    for each. The console and the customer-facing notice quote this string.
    """
    status = resp.status_code
    message = _resend_message(resp)
    low = message.lower()
    if "error code: 1010" in low or "cloudflare" in low:
        return "blocked before Resend answered (Cloudflare 1010)"
    if status == 401:
        return "resend rejected the API key (HTTP 401)"
    if status == 429:
        return "resend daily limit reached (HTTP 429)"
    if status == 403:
        if "own email address" in low:
            return "Resend's test sender only delivers to the account owner (HTTP 403)"
        if "not verified" in low or "verify your domain" in low:
            return ("the sending domain is not verified in Resend (HTTP 403)%s"
                    % (": " + message if message else ""))
        return "resend refused the message (HTTP 403)%s" % (": " + message if message else "")
    return ("resend answered HTTP %d: %s" % (status, message)) if message else (
        "resend answered HTTP %d" % status)


def _smtp_password() -> str:
    """Google shows an app password as four groups ('abcd efgh ijkl mnop'). The spaces are
    presentation; pasting them into SMTP_PASSWORD is what a 535 login failure looks like."""
    return _env("SMTP_PASSWORD").replace(" ", "")


def _send_via_smtp(to: str, subject: str, body: str):
    """One SMTP conversation. Returns (accepted, reason)."""
    host = _env("SMTP_HOST")
    user = _env("SMTP_USER")
    try:
        port = int(os.getenv("SMTP_PORT") or 587)
    except ValueError:
        port = 587
    # The authenticated account is the honest default sender: Gmail sends as it and rewrites any
    # other From, so naming a domain that may not exist yet just produces mail that looks forged.
    sender = _env("SMTP_FROM") or _env("MAIL_FROM") or user
    use_ssl = (os.getenv("SMTP_SSL", "").lower() in ("1", "true", "yes")) or port == 465
    # A relay on the same host may speak plain SMTP; public providers require TLS.
    use_tls = (os.getenv("SMTP_STARTTLS", "1").lower() not in ("0", "false", "no"))

    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = to
    msg["Subject"] = subject
    msg["Reply-To"] = default_reply_to()
    msg.set_content(body)

    try:
        if use_ssl:
            with smtplib.SMTP_SSL(host, port, timeout=20) as s:
                s.login(user, _smtp_password())
                s.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=20) as s:
                if use_tls:
                    s.starttls()
                s.login(user, _smtp_password())
                s.send_message(msg)
        return True, ""
    except Exception as exc:  # noqa: BLE001 - any transport failure means "not sent"
        # Class name only: smtplib's message can carry the relay's own text, and nothing from a
        # failed login belongs in a stored event.
        return False, "smtp failed (%s)" % exc.__class__.__name__


_SENDERS = {"resend": _send_via_resend, "smtp": _send_via_smtp}


def send_email(to: str, subject: str, body: str) -> bool:
    """Send one plain-text email. True only when a provider accepted it.

    Resend first, SMTP second: if the API answers with an error the message is not lost while a
    working mailbox is configured. Callers keep treating this as a boolean; the detail is in
    ``last_attempt()``.
    """
    order = try_order()
    errors = []
    _LAST.update({"provider": "", "ok": False, "reason": "", "errors": errors, "fell_back": False,
                  "from": "", "config": tuple(order)})

    for kind in order:
        ok, reason = _SENDERS[kind](to, subject, body)
        if ok:
            _LAST.update({"provider": kind, "ok": True, "reason": "",
                          "fell_back": errors != [], "from": default_sender()})
            return True
        errors.append("%s: %s" % (kind, reason) if reason else kind)
        _LAST["provider"] = kind

    if not order:
        _LAST["reason"] = ("no email provider configured: set RESEND_API_KEY (recommended - HTTP, "
                           "works where SMTP is blocked) or SMTP_HOST/SMTP_USER/SMTP_PASSWORD")
    else:
        _LAST["reason"] = "; ".join(errors)
    return False


def last_attempt() -> dict:
    """How the most recent send ended, for the console and the event log. Safe to show."""
    return {k: (list(v) if isinstance(v, list) else v) for k, v in _LAST.items()}


def delivery_state() -> dict:
    """What the operator console should say about email, without revealing a credential."""
    order = try_order()
    kind = order[0] if order else ""
    has_fallback = len(order) > 1
    sender = default_sender() if order else None
    domain = _domain_of(sender or "")
    # Resend's onboarding@resend.dev test sender delivers to the account owner only. A row that
    # says "email works" while every customer message is dropped is the same lie as an empty
    # inbox reported as delivered.
    sandbox = bool(domain and any(domain.endswith(d) or domain == d
                                  for d in TEST_SENDER_DOMAINS))
    # Two ways a domain counts as proven: somebody recorded it in MAIL_VERIFIED_DOMAINS, or a real
    # send through Resend with this same sender was accepted since this process started. A
    # sending-only key cannot read /domains, and "presence of a key" proves nothing about whether
    # Resend will accept the message.
    proven_by_send = bool(_LAST.get("ok")) and _LAST.get("provider") == "resend" and (
        _domain_of(_LAST.get("from") or "") == domain)
    confirmed = bool(domain) and (domain in verified_domains() or proven_by_send)
    unconfirmed = bool(kind == "resend" and domain and not sandbox and not confirmed)

    if not order:
        note = ("no email provider: set RESEND_API_KEY (recommended: HTTP, works on hosts that "
                "block SMTP) or SMTP_HOST/SMTP_USER/SMTP_PASSWORD (Gmail app password)")
    elif sandbox:
        note = ("Resend's test sender is in use: mail only reaches the Resend account owner until "
                "resmara.com is verified")
    elif unconfirmed:
        note = ("%s is not confirmed as verified in Resend, so it refuses every message from it: "
                "add the domain's records at resend.com/domains, then set "
                "MAIL_VERIFIED_DOMAINS=%s" % (domain, domain))
        if has_fallback:
            note += " (mail falls back to %s meanwhile)" % order[1]
    elif has_fallback:
        note = "email works via %s, falling back to %s" % (kind, order[1])
    else:
        note = "email works via %s" % kind
    return {
        "configured": bool(order),
        "provider": kind or None,
        "fallback": order[1] if has_fallback else None,
        "from": sender,
        "reply_to": default_reply_to() if order else None,
        "sandbox": sandbox,
        "domain": domain or None,
        "domain_verified": bool(confirmed),
        "unconfirmed": unconfirmed,
        "note": note,
    }


def console_row() -> dict:
    """The operator console's Email row: a status and one plain sentence.

    Kept here, not in the API, so the rules the row obeys are the rules under test: a configured
    provider is not delivery, an unverified sending domain is not delivery, and a send that just
    failed is named instead of being hidden behind a green row.
    """
    state = delivery_state()
    if not state["configured"]:
        return {"status": "warn",
                "note": "No mail provider: reset links are handed over by hand"}
    if state["sandbox"] or state["unconfirmed"]:
        return {"status": "warn", "note": state["note"]}
    last = last_attempt()
    # Only an attempt made under the transport configured now is evidence about email today: a
    # failure recorded against a provider that has since been removed (or added) says nothing
    # about whether the next message will go out.
    if (not last.get("ok") and last.get("reason")
            and tuple(last.get("config") or ()) == tuple(try_order())):
        return {"status": "warn", "note": "The last send failed: %s" % last["reason"]}
    return {"status": "ok",
            "note": "Mail sends from %s via %s"
                    % (state.get("from") or "the configured sender", state["provider"])}
