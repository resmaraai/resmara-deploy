#!/usr/bin/env python3
"""Resmara's clock, as the Render cron job `resmara-publisher` runs it.

This is the same work the Mac's LaunchAgent used to do from ``scripts/resmara_clock.sh``, moved
into the service so publishing no longer depends on a computer in Dan's office being awake:

  * every run (Render fires at :00/:15/:30/:45 UTC) publish every approved post whose time has come,
    read the comments on the live campaigns and email new Social leads, and sync the build room;
  * every hour, read each running campaign's listing status across its sources (Engine 6);
  * once a day around 14:00 UTC, check every Meta connection's token health.

Two deliberate choices:

  * It talks to the public HTTP API, not the database, exactly as the Mac script did. Publishing
    through ``/api/content/publish/run`` keeps one publisher: the retry ladder, the channel
    metadata and the "already sent" ledger all live in the web process. A second code path here
    is how two schedulers end up posting the same draft twice.
  * It exits 0 when the run completed, even if a step failed, because the failure is already in
    the log line for that step. Exit 1 is reserved for "no token" — a clock that cannot
    authenticate must look broken, not idle.

Usage:  RESMARA_PUBLISH_TOKEN=... python scripts/render_clock.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone

import httpx

BASE = (os.getenv("RESMARA_PUBLIC_BASE_URL") or "https://www.resmara.com").rstrip("/")
TOKEN = (os.getenv("RESMARA_PUBLISH_TOKEN") or "").strip()


def say(message: str) -> None:
    print(f"{datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')} {message}", flush=True)


def post(path: str, timeout: float) -> tuple[int, str]:
    """POST with the machine token. Returns (status, short body); never raises."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(BASE + path, headers={"X-Resmara-Token": TOKEN})
        return resp.status_code, resp.text[:400]
    except Exception as exc:  # noqa: BLE001 - the failure is the report
        return 0, f"{type(exc).__name__}: {exc}"


def get(path: str, timeout: float) -> tuple[int, str]:
    """GET with the machine token. Returns (status, short body); never raises."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.get(BASE + path, headers={"X-Resmara-Token": TOKEN})
        return resp.status_code, resp.text[:400]
    except Exception as exc:  # noqa: BLE001
        return 0, f"{type(exc).__name__}: {exc}"


def run_step(name: str, path: str, timeout: float, quiet_when: str = "") -> None:
    status, body = post(path, timeout)
    if status == 200 and quiet_when and quiet_when in body.replace(" ", ""):
        return                       # measured zero: stay quiet, like the old script did
    say(f"{name}: {status or 'ERR'} {body}")


def post_body(path: str, timeout: float) -> tuple[int, str]:
    """POST with the machine token, returning the whole body. Never raises."""
    try:
        with httpx.Client(timeout=timeout) as client:
            resp = client.post(BASE + path, headers={"X-Resmara-Token": TOKEN})
        return resp.status_code, resp.text
    except Exception as exc:  # noqa: BLE001 - the failure is the report
        return 0, f"{type(exc).__name__}: {exc}"


def buildroom() -> None:
    """Every fire prints one line, because a step that only speaks when it changes something
    cannot be told apart from a step that stopped firing. The counts are the heartbeat."""
    status, body = post_body("/api/admin/buildroom/sync", 180)
    if status != 200:
        say(f"buildroom: {status or 'ERR'} {body[:300]}")
        return
    try:
        answer = json.loads(body)
        rec = answer.get("reconciled") or {}
        say("buildroom: checked %d PRs, created %d, moved %d, tested %d, reconciled %d closed / "
            "%d deleted / %d held"
            % (len(answer.get("checked_prs") or []), len(answer.get("created") or []),
               len(answer.get("status") or []), len(answer.get("tested") or []),
               len(rec.get("closed") or []), len(rec.get("deleted") or []),
               len(rec.get("skipped") or [])))
    except (ValueError, TypeError):
        say(f"buildroom: {status} {body[:300]}")


def main() -> int:
    if not TOKEN:
        say("no RESMARA_PUBLISH_TOKEN - nothing sent")
        return 1

    # Publishing first: a failed scan must never delay a due post.
    run_step("published", "/api/content/publish/run", 120, quiet_when='"published":0')
    run_step("leads", "/api/admin/leads/scan", 240, quiet_when='"leads":0')
    buildroom()   # always one line: the build room's heartbeat, not just its changes

    # The console's System page claims it runs every 15 minutes; this is the call that makes it
    # true. Quiet unless a check actually fails.
    status, body = get("/api/admin/system-check?refresh=1", 120)
    if status != 200:
        say(f"system-check: {status or 'ERR'} {body}")
    elif '"fail"' in body:
        say(f"system-check found a failure: {body}")

    now = datetime.now(timezone.utc)
    # Engine 6, section 5: the live ad audit, every 4 hours.
    if now.hour % 4 == 1 and now.minute < 15:
        run_step("ad audit", "/api/admin/ads/audit", 300, quiet_when='"changed":0')
    # Engine 6, section 7: every hour, so a pending home stops within the hour.
    if now.minute < 15:
        run_step("listings sweep", "/api/admin/listings/sweep", 240, quiet_when='"pending":0,"sold":0,"back":0')
    if now.hour == 14 and now.minute < 10:
        run_step("meta token health", "/api/oauth/meta/check-all", 180)
        # Engine 8: Run it until it sells (report only until RESMARA_RENEWALS_APPLY is on), then the
        # once-a-day emails: day 7 and 14 reports, Run it again on day 12 and at the end.
        run_step("renewals", "/api/admin/renewals/run", 600)
        run_step("campaign emails", "/api/admin/campaigns/daily", 180, quiet_when='"reports":0,"run_again":0')
        # Engine 6: the agent's own Page and Instagram, for pending, sold and price posts.
        run_step("own posts", "/api/admin/listings/own-posts", 240, quiet_when='"found":0')
        # Engine 5: every live listing website renders and has its photos.
        run_step("listing websites", "/api/admin/sites/check", 180, quiet_when='"flagged":[]')
        # Engine 1 §6: welcome / day 3 / day 7 / day 14, once each, stopping at the first
        # launched campaign. Idempotent server-side, so a doubled tick sends nothing twice.
        status, body = post_body("/api/admin/onboarding/emails/run", 180)
        if status != 200:
            say(f"onboarding emails: {status or 'ERR'} {body[:300]}")
        else:
            try:
                answer = json.loads(body)
                say("onboarding emails: sent %d, skipped %d, stopped after launch %d"
                    % (len(answer.get("sent") or []), answer.get("skipped") or 0,
                       answer.get("stopped_after_launch") or 0))
            except (ValueError, TypeError):
                say(f"onboarding emails: {status} {body[:200]}")
        # Engine 10 §8: the yearly reminder while Run it until it sells stays on. It prints a line
        # every time it runs — once a day — because a job whose only proof is an email nobody
        # happened to receive cannot be told apart from a job that stopped firing.
        status, body = post_body("/api/admin/consent/reminders", 180)
        if status != 200:
            say(f"renewal reminders: {status or 'ERR'} {body[:300]}")
        else:
            try:
                answer = json.loads(body)
                say("renewal reminders: due %d, sent %d"
                    % (answer.get("due") or 0, len(answer.get("sent") or [])))
            except (ValueError, TypeError):
                say(f"renewal reminders: {status} {body[:200]}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
