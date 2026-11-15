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
             "SMTP_SSL", "SMTP_STARTTLS", "SMTP_FROM", "MAIL_FROM")


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


class StubResend:
    """Stands in for httpx.post against api.resend.com and records what was sent."""

    def __init__(self, status=200, raise_error=None):
        self.status = status
        self.raise_error = raise_error
        self.calls = []

    def __call__(self, url, **kwargs):
        self.calls.append({"url": url, "kwargs": kwargs})
        if self.raise_error is not None:
            raise self.raise_error
        return httpx.Response(self.status, json={"id": "re_123"},
                              request=httpx.Request("POST", url))

    @property
    def body(self):
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
          stub.body.get("from") == "Resmara <support@resmara.com>"
          and stub.body.get("to") == ["owner@resmara.test"]
          and stub.body.get("subject") == "Your receipt"
          and stub.body.get("text") == "$49 paid", stub.body)

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
