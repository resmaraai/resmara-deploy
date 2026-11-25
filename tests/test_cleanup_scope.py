#!/usr/bin/env python3
"""A demo reset must never delete a person's campaign.

On 24 Nov 2026 `scripts/seed_sample_account.py --clear-tests` ran with the rule "delete every
campaign with no paid order" and removed a collaborator's real build for 892 Coggins St, Redding
(16 uploaded photos), an hour after it failed on provider credits. The backup it writes leaves
the image bytes out, so nothing could be restored. The cleanup is now scoped to test accounts.
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global FAILS
    print(("ok   " if ok else "FAIL ") + label + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS += 1


def main() -> int:
    db_dir = tempfile.mkdtemp(prefix="resmara_cleanup_")
    os.environ["DATABASE_URL"] = f"sqlite:///{db_dir}/app.db"
    os.environ["UPLOAD_DIR"] = str(Path(db_dir) / "uploads")
    for key in ("RESMARA_ENGINE_BASE_URL", "RESMARA_ENGINE_API_KEY", "OPENAI_API_KEY",
                "OPENAI_BASE_URL", "RESMARA_SIMULATE"):
        os.environ.pop(key, None)
    for mod in [m for m in list(sys.modules) if m.startswith("app.")]:
        del sys.modules[mod]
    for mod in [m for m in list(sys.modules) if m.startswith("scripts.")]:
        del sys.modules[mod]

    from app.db.session import Base, Boost, SessionLocal, User, engine  # noqa: E402

    Base.metadata.create_all(bind=engine)

    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "seed_sample_account", ROOT / "scripts" / "seed_sample_account.py")
    seeder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(seeder)

    db = SessionLocal()
    try:
        sample = User(email="resmaraai@gmail.com", name="Sample", is_test=True, is_active=True,
                      hashed_password="x")
        collaborator = User(email="alfrench777@gmail.com", name="Adam", is_test=False,
                            is_active=True, hashed_password="x")
        throwaway = User(email=f"smoke{os.getpid()}@example.com", name="Smoke", is_active=True,
                         hashed_password="x")
        db.add_all([sample, collaborator, throwaway])
        db.commit()

        kept = Boost(user_id=collaborator.id, address="892 Coggins Street, Redding, CA 96003",
                     main_status="Build failed", stage="PENDING", hidden=False, plan={})
        demo = Boost(user_id=sample.id, address="1809 Woodland Avenue, Austin, TX 78704",
                     main_status="Awaiting approval", stage="PENDING", hidden=False,
                     plan={"_sample": True})
        other_test = Boost(user_id=throwaway.id, address="1 Card Way",
                           main_status="In Progress", stage="PENDING", hidden=False, plan={})
        db.add_all([kept, demo, other_test])
        db.commit()
        ids = {"kept": kept.id, "demo": demo.id, "other_test": other_test.id}

        gone = seeder.clear_tests(db, keep_sample=True)
        remaining = {b.id for b in db.query(Boost).all()}

        check("a collaborator's unpaid campaign survives a demo reset",
              ids["kept"] in remaining, f"remaining={sorted(remaining)} gone={gone}")
        check("the sample campaign marked _sample is kept", ids["demo"] in remaining,
              f"remaining={sorted(remaining)}")
        check("a throwaway test account's campaign is still cleared",
              ids["other_test"] not in remaining, f"remaining={sorted(remaining)}")
        check("the cleared row is reported by name", any("1 Card Way" in g for g in gone), str(gone))
        check("the kept row is not reported as deleted",
              not any("Coggins" in g for g in gone), str(gone))

        # The deliberate way to clear a real account still works - it must be named.
        gone2 = seeder.clear_tests(db, keep_sample=True, include_emails={"alfrench777@gmail.com"})
        remaining2 = {b.id for b in db.query(Boost).all()}
        check("--include-email clears a named real account on purpose",
              ids["kept"] not in remaining2 and any("Coggins" in g for g in gone2),
              f"remaining={sorted(remaining2)} gone={gone2}")
    finally:
        db.close()

    print("ALL CLEANUP-SCOPE CHECKS PASSED" if not FAILS else f"{FAILS} CLEANUP-SCOPE CHECK(S) FAILED")
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
