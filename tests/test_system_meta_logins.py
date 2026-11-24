"""The system check's Meta-login row has to report tokens, not a Python TypeError.

Why this file exists: the row read "can't compare offset-naive and offset-aware datetimes"
for weeks. Nothing was wrong with any Meta connection; the check compared Postgres's aware
`timestamptz` value against a naive `datetime.utcnow()` and the comparison raised, so the
operator tile said "fail" and named the crash instead of the state of the logins. A check
that cannot compute its own answer is worse than no check: it trains everyone to ignore red.

The row is now a pure function of the account list, so this file can put every shape of
account through it - aware, naive, none at all - without a database or a running server.

Run:  cd /Users/dan/resmara && venv/bin/python tests/test_system_meta_logins.py
"""

import os
import sys
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

os.environ.setdefault("RESMARA_ENV", "test")

from app.api.system import _meta_login_row, _utc  # noqa: E402

checks = 0
failures = 0


def ok(label, condition, detail=""):
    global checks, failures
    checks += 1
    if condition:
        print(f"  ok   {label}")
    else:
        failures += 1
        print(f"  FAIL {label}   {detail}")


def account(user_id=1, expires=None, status=None):
    return SimpleNamespace(user_id=user_id, token_expires_at=expires, token_status=status)


NOW = datetime.now(timezone.utc)

print("=== 1. an aware expiry (what Postgres actually returns) does not crash the row ===")
row = _meta_login_row([account(1, NOW + timedelta(days=30))], "2026-11-25T00:00:00")
ok("a live aware token reads ok", row["status"] == "ok", str(row))
ok("  ...and the detail counts the accounts", "1" in row["detail"], str(row))

print("\n=== 2. a naive expiry (SQLite, or a hand-built object) does not crash it either ===")
naive = datetime.utcnow() + timedelta(days=30)
row = _meta_login_row([account(1, naive)], "2026-11-25T00:00:00")
ok("a naive live token reads ok", row["status"] == "ok", str(row))

print("\n=== 3. an expired token is a failure, whoever wrote it ===")
row = _meta_login_row([account(1, NOW - timedelta(hours=1))], "2026-11-25T00:00:00")
ok("expired reads fail", row["status"] == "fail", str(row))
ok("  ...and says how many need reconnecting", "need reconnecting" in row["detail"], str(row))
row = _meta_login_row([account(1, datetime.utcnow() - timedelta(days=2))], "2026-11-25T00:00:00")
ok("a naive expired token also reads fail", row["status"] == "fail", str(row))

print("\n=== 4. the status token_health wrote still wins ===")
row = _meta_login_row([account(1, NOW + timedelta(days=30), "needs_reconnect")], "2026-11-25T00:00:00")
ok("needs_reconnect reads fail even with time left", row["status"] == "fail", str(row))
row = _meta_login_row([account(1, NOW + timedelta(days=30), "healthy")], "2026-11-25T00:00:00")
ok("healthy reads ok", row["status"] == "ok", str(row))

print("\n=== 5. expiring soon is a warning, not a failure ===")
row = _meta_login_row([account(1, NOW + timedelta(days=3))], "2026-11-25T00:00:00")
ok("three days left reads warn", row["status"] == "warn", str(row))
ok("  ...and names the week", "within a week" in row["detail"], str(row))

print("\n=== 6. no accounts and no expiry are honest states, not crashes ===")
row = _meta_login_row([], "2026-11-25T00:00:00")
ok("no accounts reads warn, not fail", row["status"] == "warn", str(row))
row = _meta_login_row([account(1, None)], "2026-11-25T00:00:00")
ok("an account with no expiry and no status reads ok", row["status"] == "ok", str(row))

print("\n=== 7. mixed shapes in one sweep (the real table) ===")
row = _meta_login_row(
    [account(1, NOW + timedelta(days=30)), account(2, datetime.utcnow() + timedelta(days=20)),
     account(3, None, "healthy"), account(4, NOW + timedelta(days=2))],
    "2026-11-25T00:00:00")
ok("one expiring among three live reads warn", row["status"] == "warn", str(row))
ok("  ...and names the one token", row["detail"].startswith("1 token"), str(row))

print("\n=== 8. the helper itself ===")
ok("_utc leaves an aware value alone", _utc(NOW) is NOW)
ok("_utc stamps UTC on a naive value", getattr(_utc(datetime(2026, 1, 1)), "tzinfo", None) == timezone.utc)
ok("_utc returns None for a non-datetime", _utc("2026-01-01") is None)
ok("_utc returns None for None", _utc(None) is None)

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL SYSTEM META LOGIN TESTS PASSED")
