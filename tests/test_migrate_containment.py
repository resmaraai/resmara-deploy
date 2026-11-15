"""A bad ALTER must never take the site down, and Postgres must understand the DDL.

Production went down on a deploy because a failed-post column was declared `DATETIME` - valid in
SQLite, not a type Postgres has - and the exception escaped startup, so the new instance died and
Render kept the old one. Both halves are tested here: the translation, and the containment.
"""
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_DIR = tempfile.mkdtemp(prefix="migrate-")
os.environ["RESMARA_DB"] = os.path.join(DB_DIR, "app.db")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(DB_DIR, 'app.db')}"

import app.db.migrate as m  # noqa: E402  (the module, not the function re-exported by app.db)

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


print("=== the DDL Postgres gets is not SQLite's dialect ===")
check("DATETIME becomes TIMESTAMP on Postgres",
      m._ddl_for("DATETIME", "postgresql") == "TIMESTAMP", m._ddl_for("DATETIME", "postgresql"))
check("  ...inside a longer definition too",
      m._ddl_for("TIMESTAMP", "postgresql") == "TIMESTAMP")
check("  ...and TEXT/INTEGER/VARCHAR are untouched",
      all(m._ddl_for(d, "postgresql") == d for d in ("TEXT", "INTEGER DEFAULT 0", "VARCHAR(160)")))
check("SQLite keeps what it understands", m._ddl_for("DATETIME", "sqlite") == "DATETIME")

print("\n=== every declared column can actually be added on this database ===")
added = m.migrate()
print("     added:", added or "nothing (already current)")
check("the migration ran", isinstance(added, list))
check("  ...with nothing failed", m.failed_additions() == [], str(m.failed_additions()))

print("\n=== a column that cannot be added is reported, not fatal ===")
m.ADDITIONS.setdefault("users", [])
m.ADDITIONS["users"].append(("this type is not real", "NOTATYPE(9)"))
try:
    added = m.migrate()
    check("startup survived the bad DDL", True)
except Exception as exc:  # noqa: BLE001
    check("startup survived the bad DDL", False, f"{type(exc).__name__}: {exc}")
    added = []
finally:
    m.ADDITIONS["users"] = [c for c in m.ADDITIONS["users"] if c[0] != "this type is not real"]

fails = m.failed_additions()
check("  ...and the bad column is named", any("this type is not real" in f for f in fails), str(fails))
check("  ...with the reason", any("users.this type is not real" in f for f in fails), str(fails))
check("  ...and the good columns still went in or were already there",
      not any("good" in f for f in fails), str(fails))

print("\n=== a clean run clears the list ===")
m.migrate()
check("nothing failed after the bad entry is gone", m.failed_additions() == [], str(m.failed_additions()))

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL MIGRATION CONTAINMENT TESTS PASSED")
