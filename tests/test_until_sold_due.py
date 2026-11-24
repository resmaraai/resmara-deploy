#!/usr/bin/env python3
"""The renewal clock: due, held, ending, too early - and the flags that decide which is which.

The point of this test is the boundaries, because they are the ones that cost money: a campaign
that renews a day early charges the agent $39 for a round they have not finished, and one that
never becomes due is a promise the product made and did not keep.

Run:
    cd /Users/dan/resmara && ./venv/bin/python3 tests/test_until_sold_due.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILS = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global FAILS
    if cond:
        print("  ok   %s" % label)
    else:
        FAILS += 1
        print("  FAIL %s %s" % (label, detail))


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="resmara-due-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "due.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-due")
    os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
    os.environ.pop("STRIPE_SECRET_KEY", None)

    from app.db.session import Base, engine, SessionLocal, Boost, User   # noqa: E402
    from app.db.migrate import migrate                                    # noqa: E402
    from app.services.renewals import review, round_ends_on, ROUND_DAYS   # noqa: E402

    Base.metadata.create_all(bind=engine)
    migrate()
    db = SessionLocal()
    now = datetime(2026, 11, 18, 12, 0, tzinfo=timezone.utc)
    try:
        owner = User(email="owner@example.com", name="Owner", is_active=True, is_admin=True,
                     hashed_password="x")
        db.add(owner); db.commit(); db.refresh(owner)

        def ids_of(result, key):
            return [r["boost_id"] for r in result[key]]

        def add(address, **kw):
            b = Boost(user_id=owner.id, address=address, main_status="Live", stage="LAUNCHED",
                      hidden=False, repeat_round=0, until_sold=True)
            for k, v in kw.items():
                setattr(b, k, v)
            db.add(b); db.commit(); db.refresh(b)
            return b

        # 12 days in: three days left, so this one is due tonight.
        due = add("1 Due Street", launched_at=now - timedelta(days=12))
        # 2 days in: not close to the end yet.
        early = add("2 Early Street", launched_at=now - timedelta(days=2))
        # Autopilot off is off, whatever the clock says.
        off = add("3 Off Street", launched_at=now - timedelta(days=13), until_sold=False)
        # Paused: held, and nothing is charged while it is paused.
        paused = add("4 Paused Street", launched_at=now - timedelta(days=13), paused_at=now - timedelta(days=1))
        # The listing went pending: Engine 8 pauses it and it stays on (held, never charged).
        pending = add("5 Pending Street", launched_at=now - timedelta(days=13), listing_status="pending")
        sold = add("6 Sold Street", launched_at=now - timedelta(days=13), listing_status="sold")
        # A repeat campaign: round 1 means the next one is round 2.
        second = add("7 Round Two Road", launched_at=now - timedelta(days=13), repeat_round=1)

        check("the round is 14 days long", ROUND_DAYS == 14)
        check("a round ends 14 days after launch",
              round_ends_on(due) == (now - timedelta(days=12)) + timedelta(days=14))

        result = review(db, now=now)
        ids = lambda key: sorted(r["boost_id"] for r in result[key])

        check("three days out is due", due.id in ids("due"))
        check("two days in is not", early.id in ids("too_early"))
        check("autopilot off is not due", off.id in ids("too_early") or off.id not in ids("due"))
        check("a paused campaign is held, not due", paused.id in ids("held") and paused.id not in ids("due"))
        check("held says why", "paused" in (next(r for r in result["held"] if r["boost_id"] == paused.id)["why"] or ""))
        check("pending doesn't end the series (it waits, paused)", pending.id not in ids("ending"))
        check("sold stops itself", sold.id in ids("ending"))
        check("a pending listing is never due", pending.id not in ids("due"))
        check("round one's next is round two", next(r for r in result["due"] if r["boost_id"] == second.id)["next_round"] == 2)
        check("the charge is the $39 the explainer quotes",
              all(r["charge_cents"] == 3900 for r in result["due"]))
        check("counts agree with the lists",
              result["counts"]["due"] == len(result["due"]) and result["counts"]["held"] == len(result["held"]))
        check("only autopilot campaigns are looked at", result["counts"]["on_autopilot"] == 6,
              result["counts"])

        print("\n[the boundary, to the hour]")
        edge = add("8 Edge Close", launched_at=now - timedelta(days=11, hours=0))
        check("exactly three days left is due", edge.id in ids_of(review(db, now=now), "due"))
        edge2 = add("9 Just Past", launched_at=now - timedelta(days=10, hours=23))
        check("three days and an hour is not yet", edge2.id in ids_of(review(db, now=now), "too_early"))

        print("\n[the script]")
        import subprocess
        script = ROOT / "scripts" / "until_sold_due.py"
        # The child is given a minimal environment on purpose. It re-reads the checkout's .env
        # (app/core/config.py) and python-dotenv writes those values into os.environ, so copying
        # this process's environment hands the child the live Stripe key, Render's private
        # Postgres URL and the Render/GitHub tokens: `--apply` then reaches for production and
        # hangs on a database the internet cannot reach. Name what the script needs instead.
        child = {k: v for k, v in os.environ.items()
                 if k in ("PATH", "HOME", "LANG", "TMPDIR", "VIRTUAL_ENV", "PYTHONPATH")}
        child.update({"DATABASE_URL": os.environ["DATABASE_URL"],
                      "RESMARA_UPLOAD_DIR": os.environ["RESMARA_UPLOAD_DIR"],
                      "RESMARA_ADMIN_EMAILS": os.environ["RESMARA_ADMIN_EMAILS"],
                      "SECRET_KEY": os.environ["SECRET_KEY"],
                      "RESMARA_ENV": "test", "RESMARA_SIMULATE": "1",
                      "STRIPE_SECRET_KEY": "", "STRIPE_WEBHOOK_SECRET": "",
                      "META_SYSTEM_TOKEN": "", "META_CLIENT_SECRET": "", "META_CLIENT_ID": "",
                      "OPENAI_API_KEY": "", "RESEND_API_KEY": "", "RESMARA_PUBLISH_TOKEN": "",
                      "RESMARA_GITHUB_TOKEN": "", "RESMARA_RENDER_API_KEY": ""})
        run = subprocess.run([sys.executable, str(script)], capture_output=True, text=True,
                             env=child, timeout=120)
        line = (run.stdout or "").strip().splitlines()[-1] if run.stdout.strip() else ""
        check("the script exits 0", run.returncode == 0, (run.stderr or "")[-200:])
        check("it prints one JSON line", line.startswith("{") and line.endswith("}"), line[:120])
        import json
        payload = json.loads(line) if line.startswith("{") else {}
        check("it reports ok", payload.get("ok") is True, str(payload)[:160])
        check("it lists what is due", isinstance(payload.get("due"), list))
        check("it says no action was taken", "none" in (payload.get("actions") or ""), str(payload.get("actions")))
        # --apply now does the work. With no Stripe key in this environment it must charge
        # nothing and say so, which is the behaviour a misconfigured cron has to have.
        applied = subprocess.run([sys.executable, str(script), "--apply"], capture_output=True,
                                 text=True, env=child, timeout=120)
        check("--apply runs and exits 0", applied.returncode == 0, (applied.stderr or "")[-200:])
        line2 = (applied.stdout or "").strip().splitlines()[-1] if applied.stdout.strip() else ""
        payload2 = json.loads(line2) if line2.startswith("{") else {}
        check("--apply reports mode=apply", payload2.get("mode") == "apply", str(payload2)[:160])
        check("...and charges nothing without a card",
              all(r.get("status") != "renewed" for r in payload2.get("applied") or []),
              str(payload2.get("applied"))[:200])
    finally:
        db.close()

    print()
    if FAILS:
        print("FAILURES: %d" % FAILS)
        return 1
    print("ALL UNTIL-SOLD CLOCK TESTS PASSED")
    return 0


def ids_of(result, key):
    return [r["boost_id"] for r in result[key]]


if __name__ == "__main__":
    raise SystemExit(main())
