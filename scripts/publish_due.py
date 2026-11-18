#!/usr/bin/env python3
"""Publish every approved post whose time has come, then read the comments on what is live.

This is the scheduler's body, not a web endpoint: a Render cron job runs it every 15
minutes, so a campaign publishes because its clock says so, not because someone happened
to have the dashboard open or because a laptop on Dan's desk was awake.

It talks to the database directly (DATABASE_URL), which means one thing matters that a
web request never had to care about: ``RESMARA_PUBLIC_BASE_URL``. Instagram fetches post
images by URL, and in a cron container there is no request host to borrow - RENDER_EXTERNAL_URL
would name the cron service itself, so the image URL must be the public site, explicitly.

The second half is the social-leads scan (Post Engine §10.4). It runs here rather than in a
second cron service: same 15-minute rhythm, and a second Render cron service is another $1/mo
floor. The two steps are isolated - a failing scan can never stop a post from going out, and a
failed publish does not stop the scan of the campaigns that are already live.

Contract: one JSON line on stdout, exit 0 when the run completed, exit 1 when it raised or
when a due post failed to publish. A cron job that cannot post must not look like a job
that had nothing to do.
"""
from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.session import SessionLocal  # noqa: E402
from app.services.publisher import publish_due  # noqa: E402
from app.services.leads import scan_all  # noqa: E402


async def _run(db) -> tuple[dict, dict, str]:
    """Publish, then scan. Each step's failure is reported, never thrown."""
    try:
        published, publish_error = await publish_due(db), ""
    except Exception as exc:  # noqa: BLE001 - the failure is the report
        published, publish_error = {}, f"publish: {type(exc).__name__}: {exc}"
    try:
        scanned, scan_error = await scan_all(db), ""
    except Exception as exc:  # noqa: BLE001 - a scan must never take the publisher down
        scanned, scan_error = {}, f"leads: {type(exc).__name__}: {exc}"
    return published, scanned, publish_error or scan_error


def main() -> int:
    db = SessionLocal()
    try:
        published, scanned, error = asyncio.run(_run(db))
    finally:
        db.close()

    if error and not published and not scanned:
        print(json.dumps({"ok": False, "error": error}))
        return 1

    line = {
        "ok": not published.get("failed") and not error,
        "checked": published.get("checked", 0),
        "posted": published.get("posted", 0),
        "failed": published.get("failed", 0),
        "skipped": published.get("skipped", 0),
        # What the lead scan saw, so a run that found nobody is still a measured zero.
        "leads": {
            "campaigns": scanned.get("campaigns", 0),
            "new": scanned.get("leads", 0),
            "emailed": scanned.get("emailed", 0),
        },
    }
    if error:
        line["error"] = error
    print(json.dumps(line))
    return 0 if line["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
