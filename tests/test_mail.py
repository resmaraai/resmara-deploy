"""Email delivery tests: Resend first, SMTP as a real fallback, nothing faked.

A tiny in-process SMTP server accepts the connection, so the SMTP checks prove the client
actually speaks the protocol, logs in and hands over a message — not just that a function
returned True. Resend (the HTTP provider) is checked with a stubbed httpx.post.

The case that matters for the free-plan deployment: Resend configured but refusing (unverified
domain 403, daily quota 429) must fall through to Gmail SMTP and still deliver. And when nothing
works, the answer has to be False with a reason — never a cheerful "sent".

Run:  cd /Users/dan/resmara && PYTHONPATH=/Users/dan/resmara venv/bin/python tests/test_mail.py
"""
import base64
import os
import socket
import sys
import threading

import httpx

from app.services import mail

PASSED = 0
FAILED = 0

MAIL_KEYS = ("RESEND_API_KEY", "SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_PORT",
             "SMTP_SSL", "SMTP_STARTTLS", "SMTP_FROM", "MAIL_FROM", "MAIL_REPLY_TO",
             "MAIL_VERIFIED_DOMAINS")


def check(label, condition, detail=None):
    global PASSED, FAILED
    if condition:
        PASSED += 1
        print("  [PASS] %s" % label)
    else:
        FAILED += 1
        print("  [FAIL] %s  %s" % (label, detail))


def reset_env(**values):
    """Every scenario starts from nothing configured, then sets exactly what it tests."""
    for key in MAIL_KEYS:
        os.environ.pop(key, None)
    os.environ.update({k: v for k, v in values.items() if v is not None})


class FakeSMTPServer(threading.Thread):
    """Accepts one session, records the message, answers just enough of RFC 5321."""

    def __init__(self):
        super().__init__(daemon=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen(1)
        self.port = self.sock.getsockname()[1]
        self.credentials = None
        self.message = ""
        self.mail_from = ""

    def run(self):
        conn, _ = self.sock.accept()
        conn.settimeout(10)
        f = conn.makefile("rwb", buffering=0)

        def say(line):
            f.write((line + "\r\n").encode())

        say("220 test.local SMTP")
        in_data = False
        try:
            while True:
                raw = f.readline()
                if not raw:
                    break
                line = raw.decode(errors="replace").rstrip("\r\n")
                if in_data:
                    if line == ".":
                        in_data = False
                        say("250 2.0.0 queued")
                    else:
                        self.message += line + "\n"
                    continue
                upper = line.upper()
                if upper.startswith("EHLO") or upper.startswith("HELO"):
                    say("250-test.local")
                    say("250 AUTH PLAIN LOGIN")
                elif upper.startswith("AUTH"):
                    self.credentials = line
                    say("235 2.7.0 authenticated")
                elif upper.startswith("MAIL FROM"):
                    self.mail_from = line
                    say("250 2.1.0 ok")
                elif upper.startswith("RCPT TO"):
                    say("250 2.1.0 ok")
                elif upper == "DATA":
                    in_data = True
                    say("354 send it")
                elif upper == "QUIT":
                    say("221 bye")
                    break
                else:
                    say("250 ok")
        except Exception:
            pass
        finally:
            try:
                conn.close()
            except Exception:
                pass


# Resend's real bodies, quoted so the reason parser is tested against what the API actually says
# rather than against a generic {"error": "..."} that no client ever sees.
RESEND_BODIES = {
    403: {"message": "The resmara.com domain is not verified. Please, add and verify your domain "
                     "on https://resend.com/domains",
          "name": "validation_error", "statusCode": 403},
    401: {"message": "API key is invalid", "name": "validation_error", "statusCode": 401},
    429: {"message": "Too many requests. You can only send 100 emails per day", "name":
          "rate_limit_exceeded", "statusCode": 429},
}


class StubResend:
    """Stands in for httpx.post against api.resend.com and records what was sent."""

    def __init__(self, status=200, raise_error=None, body=None, text=None):
        self.status = status
        self.raise_error = raise_error
        self.body = body if body is not None else RESEND_BODIES.get(status, {"id": "re_123"})
        self.text = text
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs})
        if self.raise_error is not None:
            raise self.raise_error
        if self.text is not None:
            return httpx.Response(self.status, text=self.text,
                                  request=httpx.Request("POST", url))
        return httpx.Response(self.status, json=self.body, request=httpx.Request("POST", url))

    @property
    def sent(self):
        return (self.calls[-1]["kwargs"].get("json") if self.calls else {}) or {}

    @property
    def auth(self):
        return (self.calls[-1]["kwargs"].get("headers") or {}).get("Authorization", "") if self.calls else ""


class stubbed:
    """Context manager: patch mail.httpx.post for one scenario, always restore."""

    def __init__(self, stub):
        self.stub = stub
        self.original = None

    def __enter__(self):
        self.original = mail.httpx.post
        mail.httpx.post = self.stub
        return self.stub

    def __exit__(self, *exc):
        mail.httpx.post = self.original
        return False


def smtp_env(port, password="abcd efgh ijkl mnop", sender="Resmara <support@resmara.com>"):
    return {"SMTP_HOST": "127.0.0.1", "SMTP_PORT": str(port),
            "SMTP_USER": "support@resmara.com", "SMTP_PASSWORD": password,
            "SMTP_STARTTLS": "0", "SMTP_FROM": sender}


def main():
    global PASSED, FAILED
    saved = {k: os.environ.get(k) for k in MAIL_KEYS}
    for k in MAIL_KEYS:
        os.environ.pop(k, None)

    # ---- nothing configured ------------------------------------------------------------
    print("[no provider]")
    check("nothing configured is reported as such", mail.mail_configured() is False)
    check("and a send honestly fails", mail.send_email("a@b.c", "s", "b") is False)
    state = mail.delivery_state()
    check("the state explains what to set", "RESEND_API_KEY" in state["note"], state["note"])
    check("the failure names the missing setting",
          "RESEND_API_KEY" in mail.last_attempt()["reason"], mail.last_attempt())
    check("no provider means no fake success", mail.last_attempt()["ok"] is False)

    # The support address is the one customers are told to write to; a reset from anything else
    # reads as phishing.
    check("mail comes from support@resmara.com by default",
          "support@resmara.com" in mail.default_sender(), mail.default_sender())
    check("not the old noreply@ address", "noreply" not in mail.default_sender(),
          mail.default_sender())
    os.environ["MAIL_FROM"] = "Resmara <hello@resmara.com>"
    check("but MAIL_FROM still overrides it",
          mail.default_sender() == "Resmara <hello@resmara.com>", mail.default_sender())
    os.environ.pop("MAIL_FROM")
    # A reply to a reset or a receipt has to reach a person who reads it, so the header is set on
    # every message rather than left to whatever the transport defaults to.
    check("replies go to support@resmara.com", mail.default_reply_to() == "support@resmara.com",
          mail.default_reply_to())
    os.environ["MAIL_REPLY_TO"] = "team@resmara.com"
    check("and MAIL_REPLY_TO can override it", mail.default_reply_to() == "team@resmara.com",
          mail.default_reply_to())
    os.environ.pop("MAIL_REPLY_TO")

    # ---- SMTP alone: a real conversation ----------------------------------------------
    print("\n[smtp]")
    server = FakeSMTPServer()
    server.start()
    reset_env(**smtp_env(server.port))
    check("smtp is detected", mail.provider() == "smtp", mail.provider())
    sent = mail.send_email("owner@resmara.test", "Reset your Resmara password",
                           "Use this link: https://resmara.com/reset?t=abc")
    server.join(timeout=5)
    check("the message is accepted over a real conversation", sent is True)
    check("the body reached the server", "https://resmara.com/reset?t=abc" in server.message,
          server.message[:200])
    check("the recipient was addressed", "owner@resmara.test" in server.message, server.message[:200])
    check("the subject was set", "Reset your Resmara password" in server.message, server.message[:200])
    check("the smtp message carries the reply-to header",
          "Reply-To: support@resmara.com" in server.message, server.message[:400])
    check("a login was attempted", bool(server.credentials), server.credentials)
    check("the credential never appears in the transcript",
          "abcd efgh ijkl mnop" not in (server.credentials or ""), server.credentials)

    # Google displays an app password as four groups; the copy-pasted spaces are what make the
    # login fail, so the client strips them before authenticating.
    decoded = ""
    if server.credentials and server.credentials.upper().startswith("AUTH PLAIN"):
        try:
            decoded = base64.b64decode(server.credentials.split()[2]).decode(errors="replace")
        except Exception:
            decoded = ""
    check("a space-separated app password is accepted whole",
          decoded.endswith("abcdefghijklmnop"), decoded)
    check("the success is recorded as smtp", mail.last_attempt()["provider"] == "smtp",
          mail.last_attempt())

    print("\n[failure path]")
    reset_env(SMTP_HOST="127.0.0.1", SMTP_PORT="1", SMTP_USER="support@resmara.com",
              SMTP_PASSWORD="abcd efgh ijkl mnop")
    check("a dead relay returns False, not an exception", mail.send_email("a@b.c", "s", "b") is False)
    check("and says the smtp attempt failed", "smtp" in mail.last_attempt()["reason"],
          mail.last_attempt())
    check("without leaking the password", "abcd" not in str(mail.last_attempt()), mail.last_attempt())

    # ---- Resend alone ---------------------------------------------------------------
    print("\n[resend]")
    reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <support@resmara.com>")
    check("resend is the primary when set", mail.provider() == "resend", mail.provider())
    stub = StubResend(200)
    with stubbed(stub):
        ok = mail.send_email("owner@resmara.test", "Your receipt", "$49 paid")
    check("resend send reports success", ok is True)
    check("it posts to the Resend API", stub.calls and stub.calls[0]["url"] == mail.RESEND_ENDPOINT,
          stub.calls[0]["url"] if stub.calls else None)
    check("the bearer is the key", stub.auth.endswith("re_test_123"), stub.auth)
    check("from/to/subject/body are right",
          stub.sent.get("from") == "Resmara <support@resmara.com>"
          and stub.sent.get("to") == ["owner@resmara.test"]
          and stub.sent.get("subject") == "Your receipt"
          and stub.sent.get("text") == "$49 paid", stub.sent)
    check("the resend payload carries the reply-to address",
          stub.sent.get("reply_to") == "support@resmara.com", stub.sent.get("reply_to"))

    # ---- Resend refuses, SMTP rescues -----------------------------------------------
    # The free plan has no SMTP at all and Resend's free tier stops at 100/day, so both halves of
    # "Resend first, SMTP fallback" are load-bearing. Neither refusal below may cost a reset mail.
    print("\n[resend refuses -> smtp fallback]")
    for label, status, expected in (("an unverified domain (403)", 403, "not verified"),
                                    ("the daily quota (429)", 429, "daily limit")):
        server = FakeSMTPServer()
        server.start()
        reset_env(RESEND_API_KEY="re_test_123", **smtp_env(server.port))
        check("%s: both providers are seen" % label,
              mail.try_order() == ["resend", "smtp"], mail.try_order())
        stub = StubResend(status)
        with stubbed(stub):
            ok = mail.send_email("agent@resmara.test", "Welcome to Resmara",
                                 "Your account is ready.")
        server.join(timeout=5)
        check("%s: the mail still goes out" % label, ok is True)
        check("%s: it went over smtp" % label, "agent@resmara.test" in server.message,
              server.message[:200])
        last = mail.last_attempt()
        check("%s: the record says smtp carried it" % label, last["provider"] == "smtp", last)
        check("%s: and that it fell back" % label, last["fell_back"] is True, last)
        check("%s: resend's reason is kept" % label,
              any(expected in e for e in last["errors"]), last["errors"])
        check("%s: the API key is not in the record" % label,
              "re_test_123" not in repr(last) and "re_test_123" not in repr(mail.delivery_state()),
              repr(last))

    # ---- both refuse -----------------------------------------------------------------
    print("\n[both providers fail]")
    reset_env(RESEND_API_KEY="re_test_123", SMTP_HOST="127.0.0.1", SMTP_PORT="1",
              SMTP_USER="support@resmara.com", SMTP_PASSWORD="abcd efgh ijkl mnop")
    stub = StubResend(500)
    with stubbed(stub):
        ok = mail.send_email("a@b.c", "s", "b")
    last = mail.last_attempt()
    check("nothing delivered means False", ok is False)
    check("both attempts are listed", mail.try_order() == ["resend", "smtp"], mail.try_order())
    check("the reason covers resend", "resend" in last["reason"], last["reason"])
    check("the reason covers smtp", "smtp" in last["reason"], last["reason"])
    check("and no credential is in it", "re_test_123" not in str(last), last)
    state = mail.delivery_state()
    check("the console shows the fallback", state["fallback"] == "smtp", state)
    check("and still calls email configured", state["configured"] is True, state)
    check("the reply-to is reported without the credential",
          state["reply_to"] == "support@resmara.com", state)
    check("a verified sender is not called a sandbox", state["sandbox"] is False, state)

    # ---- Resend's test sender is not delivery ---------------------------------------
    # onboarding@resend.dev only reaches the Resend account owner. Reporting "email works" while
    # every customer message is dropped is the lie this state exists to prevent.
    print("\n[resend test sender]")
    reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <onboarding@resend.dev>")
    state = mail.delivery_state()
    check("the test sender is flagged as a sandbox", state["sandbox"] is True, state)
    check("and the note says who actually receives it",
          "owner" in state["note"] and "verified" in state["note"], state["note"])
    check("the key still counts as configured", state["configured"] is True, state)
    reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <support@resmara.com>")
    check("a real sender on our own domain is not a sandbox",
          mail.delivery_state()["sandbox"] is False, mail.delivery_state())

    # ---- an unverified sending domain is not delivery ---------------------------------
    # The state of production until resmara.com's records exist: a key present, a real address in
    # MAIL_FROM, and every send refused. A green row here is what makes a launch look finished.
    # This section runs before any accepted send, because one success is itself proof.
    print("\n[unverified sender]")
    reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <support@resmara.com>")
    state = mail.delivery_state()
    check("the domain is reported", state["domain"] == "resmara.com", state)
    check("an unrecorded domain is unconfirmed", state["unconfirmed"] is True, state)
    check("and is not called verified", state["domain_verified"] is False, state)
    check("the note names the page to fix it", "resend.com/domains" in state["note"], state["note"])
    check("and the variable that records success",
          "MAIL_VERIFIED_DOMAINS=resmara.com" in state["note"], state["note"])
    row = mail.console_row()
    check("the console row reads warn", row["status"] == "warn", row)
    check("and carries the reason", "resend.com/domains" in row["note"], row)

    os.environ["MAIL_VERIFIED_DOMAINS"] = "trackmygold.net, resmara.com"
    state = mail.delivery_state()
    check("a recorded domain is confirmed", state["unconfirmed"] is False, state)
    check("and the row turns ok", mail.console_row()["status"] == "ok", mail.console_row())
    check("naming the sender", "support@resmara.com" in mail.console_row()["note"],
          mail.console_row())
    os.environ.pop("MAIL_VERIFIED_DOMAINS")

    # SMTP authenticates as a mailbox rather than claiming a domain, so it has no verification
    # gap to report; warning there would be the same lie in reverse.
    server = FakeSMTPServer()
    server.start()
    reset_env(**smtp_env(server.port))
    check("gmail smtp is not flagged unverified",
          mail.delivery_state()["unconfirmed"] is False, mail.delivery_state())
    check("a mailbox sender reads ok", mail.console_row()["status"] == "ok", mail.console_row())
    check("and says which provider carries it", "smtp" in mail.console_row()["note"],
          mail.console_row())

    # ---- what a refusal actually means -------------------------------------------------
    # Every 403 used to read "rejected the key or the sending domain is not verified". One guess
    # for three different faults sends the operator to the wrong console: an unverified domain
    # needs DNS, the test sender needs a verified domain, and Cloudflare needs nothing but a
    # different client signature. The real bodies below come from api.resend.com.
    print("\n[refusal reasons]")
    cases = (
        ("an unverified domain", 403, None, "not verified"),
        ("the test sender, stranger recipient", 403,
         {"message": "You can only send testing emails to your own email address "
                     "(resmaraai@gmail.com). To send emails to other recipients, please verify a "
                     "domain at resend.com/domains", "name": "validation_error", "statusCode": 403},
         "account owner"),
        ("a revoked key", 401, None, "API key"),
        ("the daily quota", 429, None, "daily limit"),
    )
    for label, status, body, expected in cases:
        reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <support@resmara.com>")
        with stubbed(StubResend(status, body=body)):
            check("%s: not delivered" % label,
                  mail.send_email("owner@resmara.test", "s", "b") is False)
        reason = mail.last_attempt()["reason"]
        check("%s: the reason names it" % label, expected in reason, reason)
        check("%s: without the key" % label, "re_test_123" not in reason, reason)

    # Cloudflare sits in front of api.resend.com and answers 1010 to a client it dislikes; the
    # request never reaches Resend, so blaming the key or the domain is a wrong diagnosis.
    reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <support@resmara.com>")
    with stubbed(StubResend(403, text="error code: 1010\n")):
        mail.send_email("owner@resmara.test", "s", "b")
    reason = mail.last_attempt()["reason"]
    check("a Cloudflare block is named as a block", "Cloudflare" in reason, reason)
    check("and not blamed on the domain", "not verified" not in reason, reason)

    # A real accepted send is the strongest evidence, and it outranks the env var: the row fixes
    # itself the first time a message actually leaves, without anyone editing Render.
    reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <support@resmara.com>")
    with stubbed(StubResend(200)):
        check("an accepted send succeeds", mail.send_email("owner@resmara.test", "s", "b") is True)
    state = mail.delivery_state()
    check("a proven sender is confirmed", state["unconfirmed"] is False, state)
    check("and the row reads ok", mail.console_row()["status"] == "ok", mail.console_row())

    # A failed send must not leave a green row behind it.
    reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <support@resmara.com>")
    os.environ["MAIL_VERIFIED_DOMAINS"] = "resmara.com"
    with stubbed(StubResend(403)):
        check("a refused send is honest", mail.send_email("owner@resmara.test", "s", "b") is False)
    row = mail.console_row()
    check("the row reports the last failure", row["status"] == "warn", row)
    check("with its reason", "last send failed" in row["note"].lower(), row["note"])
    os.environ.pop("MAIL_VERIFIED_DOMAINS")

    # A failure recorded against a transport that is no longer in use says nothing about the one
    # configured now: after switching to SMTP the row must not keep warning about Resend.
    reset_env(RESEND_API_KEY="re_test_123", MAIL_FROM="Resmara <support@resmara.com>")
    with stubbed(StubResend(403)):
        mail.send_email("owner@resmara.test", "s", "b")
    os.environ.pop("RESEND_API_KEY")
    check("a stale resend failure is not reported as today's",
          mail.console_row()["status"] == "warn", mail.console_row())
    check("and the row says there is no provider",
          "no mail provider" in mail.console_row()["note"].lower(), mail.console_row())

    # ---- restore env -----------------------------------------------------------------
    print("\n[restore env]")
    for k, v in saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    print("  restored")

    print("\n" + "=" * 60)
    print("%d passed, %d failed" % (PASSED, FAILED))
    if FAILED:
        print("MAIL TESTS FAILED")
        sys.exit(1)
    print("ALL MAIL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
