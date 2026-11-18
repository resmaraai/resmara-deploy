#!/usr/bin/env python3
"""The renewal clock: which campaigns are due a new round, and what is being held.

Run it hourly (or nightly) and it prints one JSON line. It builds nothing and charges nothing
yet - the money half (off-session $39, the round builder, the email) is not written, and a job
that reports honestly about that is worth more than one that pretends. ``--apply`` is accepted and
refused loudly so a cron entry written too early cannot silently start spending.

Exit codes: 0 the run completed (whether or not anything was due), 1 it raised.

    python scripts/until_sold_due.py            # what tonight would do
    python scripts/until_sold_due.py --apply    # refuses: the builder is not built yet
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal                 # noqa: E402
from app.services.renewals import review               # noqa: E402


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--apply" in argv:
        print(json.dumps({
            "ok": False,
            "error": "the round builder and the $39 charge are not written yet; "
                     "this job is the clock only, so --apply has nothing to apply",
        }))
        return 1
    db = SessionLocal()
    try:
        result = review(db)
    except Exception as exc:                                        # noqa: BLE001
        print(json.dumps({"ok": False, "error": "%s: %s" % (type(exc).__name__, exc)}))
        return 1
    finally:
        db.close()

    due = result["due"]
    print(json.dumps({
        "ok": True,
        "checked_at": result["checked_at"],
        "counts": result["counts"],
        "due": [{"boost_id": r["boost_id"], "address": r["address"], "round": r["round"],
                 "ends": r["round_ends_at"], "days_left": r["days_left"],
                 "would_charge_cents": r["charge_cents"]} for r in due],
        "held": [{"boost_id": r["boost_id"], "address": r["address"], "why": r["why"]}
                 for r in result["held"]],
        "ending": [{"boost_id": r["boost_id"], "address": r["address"], "why": r["why"]}
                   for r in result["ending"]],
        "actions": "none - the builder and the charge are not implemented yet",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
