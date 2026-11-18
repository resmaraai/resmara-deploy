#!/usr/bin/env python3
"""Put the known Resmara filing obligations on the board, once.

These are the four real ones a California general partnership has, with the dates taken from
the IRS CP575B (issued 2026-11-12) and the Shasta County fee schedule checked 2026-11-18:

  * Fictitious Business Name statement  — 40 days from starting business
  * the newspaper run for it            — first week inside 45 days of that filing
  * Form 1065 (IRS)                     — 03/15, annually
  * Form 565 (CA FTB)                   — 03/15, annually

Idempotent by title: running it twice adds nothing. Prices are either a real number or NULL
("nobody has quoted it yet") — the publication cost is genuinely unknown until a paper is
chosen, and this script refuses to pretend otherwise.

    DATABASE_URL=... python scripts/seed_filings.py [--dry-run]
"""
from __future__ import annotations

import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROWS = [
    {
        "title": "Shasta County Fictitious Business Name statement",
        "kind": "filing",
        "jurisdiction": "Shasta County Clerk",
        "due_on": "2026-12-22",          # 40 days after the 2026-11-12 start of business
        "window_opens_on": "2026-11-12",
        "recurrence": "every_5_years",
        "cost_cents": 9300,              # $84 + $9 for the second registrant
        "cost_note": "$84 + $9 per additional registrant",
        "link": "https://www.shastacounty.gov/county-clerk/page/fictitious-business-name",
        "notes": ("Due within 40 days of starting business (B&P 17910). Filing late means filing "
                  "again and paying the fee twice. The brand is not a partner's surname, which is "
                  "why it is required at all. Valid five years."),
    },
    {
        "title": "FBN publication — four weekly runs",
        "kind": "publication",
        "jurisdiction": "Record Searchlight or Intermountain News",
        "due_on": None,                  # 45 days from the filing date, not known until it is filed
        "recurrence": "one_off",
        "cost_cents": None,              # a paper quotes this; do not invent it
        "cost_note": "quoted by the paper",
        "blocked_on": "the FBN statement has to be filed first",
        "notes": ("Publish once a week for four consecutive weeks. The first run must land within "
                  "45 days of the county filing or the whole statement is filed again. Proof of "
                  "publication goes back to the clerk within 30 days of the last run."),
    },
    {
        "title": "Federal partnership return — Form 1065",
        "kind": "tax",
        "jurisdiction": "IRS",
        "due_on": "2027-03-15",
        "recurrence": "annual",
        "cost_cents": 0,
        "cost_note": "free to file with the IRS; software or a preparer costs extra",
        "notes": ("Partnership return with a Schedule K-1 for each partner. The due date on the "
                  "CP575B is 03/15/2027. Extendable with Form 7004, which extends the filing only, "
                  "not the payment."),
    },
    {
        "title": "California partnership return — Form 565",
        "kind": "tax",
        "jurisdiction": "CA FTB",
        "due_on": "2027-03-15",
        "recurrence": "annual",
        "cost_cents": 0,
        "cost_note": "$0 — a general partnership pays no $800 minimum franchise tax",
        "notes": ("Form 565 plus K-1s. A general partnership is outside the $800 minimum franchise "
                  "tax that LLCs and corporations pay; the return itself carries no filing fee."),
    },
]


def _dates(row: dict) -> dict:
    """SQLite's Date type takes date objects, not the strings this file is written with."""
    out = dict(row)
    for key in ("due_on", "window_opens_on"):
        if out.get(key):
            out[key] = date.fromisoformat(out[key])
    return out


def main() -> int:
    dry = "--dry-run" in sys.argv
    from app.db.session import Base, engine, SessionLocal, Filing
    from app.db.migrate import migrate

    Base.metadata.create_all(bind=engine)
    migrate()

    added, skipped = [], []
    with SessionLocal() as db:
        for row in ROWS:
            if db.query(Filing).filter(Filing.title == row["title"]).first():
                skipped.append(row["title"])
                continue
            if not dry:
                db.add(Filing(status="open", owner="dan", **_dates(row)))
            added.append(row["title"])
        if not dry:
            db.commit()

    for t in added:
        print(("would add" if dry else "added") + ": " + t)
    for t in skipped:
        print("already there: " + t)
    print(f"{len(added)} added, {len(skipped)} already present, as of {date.today().isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
