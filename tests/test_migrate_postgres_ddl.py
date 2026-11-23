"""Two schema rules that only bite in production.

1. The SQLite spelling of a boolean default is not Postgres. `BOOLEAN DEFAULT 1` is a
   DatatypeMismatch on Postgres, and on 23 Nov 2026 it showed up in `/api/version`'s
   `migrations_failed` for `users.marketing_optin` on the live database - a real migration that
   silently did not run, on a column every Marketing number reads.

2. A column cannot carry a unique constraint through `ADD COLUMN`, and `facebook_id` must be
   unique: it is what makes "the same Facebook account always lands on the same Resmara account"
   true even when two sign-ins race.

Run:  PYTHONPATH=. venv/bin/python tests/test_migrate_postgres_ddl.py
"""
import os
import sys
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-ddl-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import inspect, text  # noqa: E402

from app.db.migrate import _ddl_for, ensure_unique_indexes, migrate  # noqa: E402
from app.db.session import Base, engine  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


check("the Postgres translator turns BOOLEAN DEFAULT 1 into TRUE",
      _ddl_for("BOOLEAN DEFAULT 1", "postgresql") == "BOOLEAN DEFAULT TRUE",
      _ddl_for("BOOLEAN DEFAULT 1", "postgresql"))
check("  ...and BOOLEAN DEFAULT 0 into FALSE",
      _ddl_for("BOOLEAN DEFAULT 0", "postgresql") == "BOOLEAN DEFAULT FALSE")
check("  ...and leaves SQLite alone", _ddl_for("BOOLEAN DEFAULT 1", "sqlite") == "BOOLEAN DEFAULT 1")

Base.metadata.create_all(bind=engine)
migrate()
migrate()  # idempotent: a second boot adds nothing and must not fail

indexes = {i["name"] for i in inspect(engine).get_indexes("users")}
check("facebook_id gets a unique index ADD COLUMN could not carry",
      "ix_users_facebook_id_unique" in indexes, str(sorted(indexes)))

# The guarantee itself: two rows with one Facebook id cannot exist.
from app.db.session import SessionLocal, User  # noqa: E402

db = SessionLocal()
try:
    db.add(User(email="a@example.com", hashed_password="x", facebook_id="fb-1"))
    db.commit()
    refused = False
    try:
        db.add(User(email="b@example.com", hashed_password="x", facebook_id="fb-1"))
        db.commit()
    except Exception:  # noqa: BLE001 - the refusal is the point
        refused = True
        db.rollback()
    check("  ...and the database refuses a second account on one Facebook id", refused,
          "a second row with fb-1 was accepted")
finally:
    db.close()

ensure_unique_indexes()
check("re-running the index step is harmless", True)

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL MIGRATION DDL TESTS PASSED")
