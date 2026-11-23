#!/usr/bin/env python3
"""The clock is a second Render service, and Render never rebuilds a cron job on a commit.

The failure this stops: a change to ``scripts/render_clock.py`` reaching the web service and never
reaching the clock, so the clock keeps running yesterday's script against today's endpoints and
every dashboard reads green. The rules worth pinning:

  * same commit → nothing happens
  * a different commit → the clock's deploy is started
  * a deploy already in flight → nothing happens (no duplicate build of the same commit)
  * this commit's deploy already failed → nothing happens (one broken build must not become a
    loop on every restart)
  * no key or no cron id → nothing happens, and it says so instead of guessing
  * it never raises: a slow Render API must not stop the web service booting
"""
from __future__ import annotations

import os
import sys
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
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-clock-image")
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join("/tmp", "clock-image.db")
    os.environ.setdefault("RESMARA_UPLOAD_DIR", "/tmp/clock-image-uploads")

    from app.services import clock_image
    from app.core import config

    decide = clock_image.decide

    print("decide()")
    should, why = decide("a91292e" + "0" * 33, "live", "cc2ab03" + "0" * 33)
    check("a clock on another commit is redeployed", should is True, why)
    check("and the reason names both shorts", "a91292e" in why and "cc2ab03" in why, why)

    check("a clock on this commit is left alone",
          decide("cc2ab03" + "0" * 33, "live", "cc2ab03" + "0" * 33)[0] is False)
    check("a build in flight is not duplicated",
          decide("a91292e", "build_in_progress", "cc2ab03")[0] is False)
    check("a queued build is not duplicated",
          decide("a91292e", "queued", "cc2ab03")[0] is False)
    check("a failed build of THIS commit is not retried on every restart",
          decide("cc2ab03", "build_failed", "cc2ab03")[0] is False)
    check("a failed build of an older commit is retried",
          decide("a91292e", "build_failed", "cc2ab03")[0] is True)
    check("no commit on this build means no guessing",
          decide("a91292e", "live", "")[0] is False)

    print("keep_in_step() without wiring")
    config.settings.RENDER_API_KEY = ""
    config.settings.RENDER_CRON_SERVICE_ID = ""
    try:
        clock_image.keep_in_step()
        check("it says it skipped instead of raising", True)
    except Exception as exc:  # noqa: BLE001
        check("it says it skipped instead of raising", False, repr(exc))

    print("keep_in_step() with an unreachable API")
    config.settings.RENDER_API_KEY = "test-key"
    config.settings.RENDER_CRON_SERVICE_ID = "crn-test"
    config.settings.RENDER_API_BASE = "http://127.0.0.1:9"   # closed port: connection refused
    config.settings.RENDER_GIT_COMMIT = "cc2ab03" + "0" * 33
    try:
        clock_image.keep_in_step()
        check("a dead Render API does not stop the boot", True)
    except Exception as exc:  # noqa: BLE001
        check("a dead Render API does not stop the boot", False, repr(exc))
    check("latest_clock_build() reports unknown rather than raising",
          clock_image.latest_clock_build() is None)

    print()
    if FAILS:
        print(f"{FAILS} FAILED")
        return 1
    print("ALL CLOCK IMAGE CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
