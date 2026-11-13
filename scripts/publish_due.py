#!/usr/bin/env python3
"""Publish every approved post whose time has come.

This is the scheduler's body, not a web endpoint: a Render cron job runs it every 15
minutes, so a campaign publishes because its clock says so, not because someone happened
to have the dashboard open or because a laptop on Dan's desk was awake.

It talks to the database directly (DATABASE_URL), which means one thing matters that a
web request never had to care about: ``RESMARA_PUBLIC_BASE_URL``. Instagram fetches post
images by URL, and in a cron container there is no request host to borrow - RENDER_EXTERNAL_URL
would name the cron service itself, so the image URL must be the public site, explicitly.

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


def main() -> int:
    db = SessionLocal()
    try:
        try:
            result = asyncio.run(publish_due(db))
        except Exception as exc:  # noqa: BLE001 - the failure is the report
            print(json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}))
            return 1
    finally:
        db.close()

    line = {
        "ok": not result.get("failed"),
        "checked": result.get("checked", 0),
        "posted": result.get("posted", 0),
        "failed": result.get("failed", 0),
        "skipped": result.get("skipped", 0),
    }
    print(json.dumps(line))
    return 0 if line["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
