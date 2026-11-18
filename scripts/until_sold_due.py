#!/usr/bin/env python3
"""The renewal clock, and the switch that spends.

Without a flag it only reports: which campaigns are due a new round, which are held because the
campaign is paused, which have gone pending or sold. With ``--apply`` it does the whole thing -
charges the $39 to the card on file, copies the campaign forward as round n+1, builds it, emails
the agent - and clears the flag on any listing that has gone pending or sold.

Why two modes matter here: the same script runs from a Mac cron while this is being proven and, on
Render, from a cron service with nothing watching. The default has to be the safe one, so a
mistyped schedule cannot start charging cards.

Exit codes: 0 the run completed (whether or not anything was due), 1 it raised.

    python scripts/until_sold_due.py            # what tonight would do
    python scripts/until_sold_due.py --apply    # charge + build + email, for what is due
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal                      # noqa: E402
from app.services import renewals                            # noqa: E402


def _plan_line(result) -> dict:
    return {
        "ok": True,
        "mode": "plan",
        "checked_at": result["checked_at"],
        "counts": result["counts"],
        "due": [{"boost_id": r["boost_id"], "address": r["address"], "round": r["round"],
                 "ends": r["round_ends_at"], "days_left": r["days_left"],
                 "would_charge_cents": r["charge_cents"]} for r in result["due"]],
        "held": [{"boost_id": r["boost_id"], "address": r["address"], "why": r["why"]}
                 for r in result["held"]],
        "ending": [{"boost_id": r["boost_id"], "address": r["address"], "why": r["why"]}
                   for r in result["ending"]],
        "actions": "none - pass --apply to charge and build",
    }


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    apply_now = "--apply" in argv
    db = SessionLocal()
    try:
        if apply_now:
            result = asyncio.run(renewals.apply(db))
            payload = {"ok": True, "mode": "apply", **result}
        else:
            payload = _plan_line(renewals.review(db))
    except Exception as exc:                                     # noqa: BLE001 - the failure is the report
        print(json.dumps({"ok": False, "mode": "apply" if apply_now else "plan",
                          "error": "%s: %s" % (type(exc).__name__, exc)}))
        return 1
    finally:
        db.close()

    print(json.dumps(payload))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
