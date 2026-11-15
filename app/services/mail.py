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
import smtplib
from email.message import EmailMessage

import httpx

RESEND_ENDPOINT = "https://api.resend.com/emails"

# support@ is the address customers are told to write to. A password reset arriving from an
# address they have never seen reads as phishing, and Gmail files it as such.
DEFAULT_FROM = "Resmara <support@resmara.com>"

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
            json={"from": default_sender(), "to": [to], "subject": subject, "text": body},
        )
    except httpx.HTTPError as exc:
        return False, "resend unreachable (%s)" % exc.__class__.__name__

    if resp.status_code in (200, 201, 202):
        return True, ""
    if resp.status_code in (401, 403):
        return False, "resend rejected the key or the sending domain is not verified (HTTP %d)" % resp.status_code
    if resp.status_code == 429:
        return False, "resend daily limit reached (HTTP 429)"
    return False, "resend answered HTTP %d" % resp.status_code


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
    _LAST.update({"provider": "", "ok": False, "reason": "", "errors": errors, "fell_back": False})

    for kind in order:
        ok, reason = _SENDERS[kind](to, subject, body)
        if ok:
            _LAST.update({"provider": kind, "ok": True, "reason": "",
                          "fell_back": errors != []})
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
    if not order:
        note = ("no email provider: set RESEND_API_KEY (recommended: HTTP, works on hosts that "
                "block SMTP) or SMTP_HOST/SMTP_USER/SMTP_PASSWORD (Gmail app password)")
    elif len(order) > 1:
        note = "email works via %s, falling back to %s" % (kind, order[1])
    else:
        note = "email works via %s" % kind
    return {
        "configured": bool(order),
        "provider": kind or None,
        "fallback": order[1] if len(order) > 1 else None,
        "from": default_sender() if order else None,
        "note": note,
    }
