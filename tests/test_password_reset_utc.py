"""The reset link has to survive Postgres's timezone-aware timestamps.

Why this exists: ``password_resets.expires_at`` is ``timestamptz``, so psycopg2 hands the row
back with ``tzinfo=UTC``, and the endpoint's ``row.expires_at < datetime.utcnow()`` raised
``TypeError: can't compare offset-naive and offset-aware datetimes``. SQLite returns naive
datetimes, so the whole suite stayed green while every real link on www.resmara.com answered
500 "Internal Server Error" as soon as a customer typed a new password.

The fake row is the point: it is the only way to reproduce the production shape from sqlite.
"""
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-reset-tz-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.db.session import get_db, Base, engine  # noqa: E402
from app.db.migrate import migrate  # noqa: E402
from app.api import auth as auth_module  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + ("" if ok else f"  <- {detail}"))
    if not ok:
        FAILS.append(name)


class _FakeQuery:
    def __init__(self, row):
        self.row = row

    def filter(self, *args, **kwargs):
        return self

    def first(self):
        return self.row

    def update(self, values):
        return 1


class _FakeSession:
    """Only the parts of a Session that ``confirm_reset`` touches."""

    def __init__(self, row):
        self.row = row

    def query(self, *args, **kwargs):
        return _FakeQuery(self.row)

    def commit(self):
        self.row.committed = True

    def add(self, obj):
        pass


TOKEN = "kn_aware-timestamp-token"
NEW_PASSWORD = "third long password"


def make_row(expires_at):
    # Exactly what psycopg2 returns for a timestamptz row: aware, in UTC.
    return SimpleNamespace(id=1, user_id=1, used_at=None, expires_at=expires_at,
                           token_hash=auth_module._hash(TOKEN), email="agent@example.com")


def submit(expires_at):
    row = make_row(expires_at)
    app.dependency_overrides[get_db] = lambda: _FakeSession(row)
    try:
        client = TestClient(app)
        return client.post("/api/auth/password-reset/confirm"
                           f"?token={TOKEN}&new_password={NEW_PASSWORD}")
    finally:
        app.dependency_overrides.pop(get_db, None)


# ---- an expired link is a clean 400, not a 500 ----------------------------------------
r = submit(datetime.now(timezone.utc) - timedelta(minutes=5))
check("an expired aware link answers 400", r.status_code == 400, f"{r.status_code} {r.text}")
check("and says the link expired rather than 'Internal Server Error'",
      "invalid or has expired" in r.text, r.text[:200])

# ---- a live link with an aware timestamp actually changes the password ----------------
r = submit(datetime.now(timezone.utc) + timedelta(minutes=30))
check("a live aware link answers 200", r.status_code == 200, f"{r.status_code} {r.text}")
check("and reports the account it reset", r.json().get("email") == "agent@example.com", r.text[:200])

# ---- a naive timestamp (sqlite, the way every test wrote it before) still works -------
r = submit(datetime.utcnow() + timedelta(minutes=30))
check("a naive live timestamp still answers 200", r.status_code == 200, f"{r.status_code} {r.text}")

# ---- the normaliser itself ------------------------------------------------------------
aware = datetime(2026, 11, 15, 18, 0, tzinfo=timezone.utc)
check("an aware UTC value normalises to naive UTC",
      auth_module._naive_utc(aware) == datetime(2026, 11, 15, 18, 0), str(auth_module._naive_utc(aware)))
check("the comparison the endpoint does now survives an aware value",
      auth_module._naive_utc(aware) < datetime(2026, 11, 15, 18, 30), "still raises")

print()
if FAILS:
    print(f"FAILED: {len(FAILS)} check(s): {', '.join(FAILS)}")
    sys.exit(1)
print("PASSWORD RESET TIMEZONE TEST PASSED")
