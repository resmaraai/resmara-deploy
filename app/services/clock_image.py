"""Keep the clock's image on the same commit as the web service.

The clock is a Render **cron job**: its own service, its own Docker build, its own image. It is
built from the same repository, but Render only auto-deploys the *web* service — the mirror's
workflow calls one deploy hook, and a cron job has no deploy hook at all. So a change to
``scripts/render_clock.py`` ships to the web service and never reaches the clock: the clock keeps
running yesterday's script against today's endpoints, and the only symptom is a log line that
never changes shape.

That is not a hypothetical. On 23 Nov the cron was still building 7450df4 (07:02) while the web
service served a91292e (16:07) — both "green", four commits apart.

So the web service, which knows its own commit (Render sets ``RENDER_GIT_COMMIT``) and holds the
Render key, checks the clock once at startup and starts its deploy when they differ. One GET per
startup, no secrets in git, and the two services cannot drift by more than one build.

Never raises: a web service must not fail to boot because Render's API was slow.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import settings

# Render's own vocabulary. Anything in here means "a deploy is already on its way", and starting a
# second one would queue a duplicate build of the same commit.
_IN_FLIGHT = {
    "created", "queued", "build_in_progress", "update_in_progress",
    "pre_deploy_in_progress", "canceled",
}


def _short(sha: str) -> str:
    return (sha or "")[:7]


def decide(latest_commit: str, latest_status: str, current_commit: str) -> Tuple[bool, str]:
    """Should the clock be redeployed? Returns (deploy, the sentence that says why)."""
    current = (current_commit or "").strip()
    latest = (latest_commit or "").strip()
    status = (latest_status or "").strip()
    if not current:
        return False, "no commit on this build (RENDER_GIT_COMMIT unset), so there is nothing to compare"
    if latest and latest.startswith(current[:7]):
        return False, f"clock already builds {_short(current)}"
    if status in _IN_FLIGHT:
        return False, f"clock is already deploying {_short(latest) or 'an unknown commit'} ({status})"
    if status in ("build_failed", "update_failed", "pre_deploy_failed"):
        # The failing deploy is the newest one: it may well be this very commit, and retrying it on
        # every restart turns one broken build into a loop. A person reads the failure.
        if latest and latest.startswith(current[:7]):
            return False, (f"clock's deploy of {_short(current)} failed ({status}); not retrying it "
                           f"on every restart")
    return True, (f"clock builds {_short(latest) or 'nothing yet'} and this service builds "
                  f"{_short(current)}, so the clock is being redeployed")


def _latest_deploy(client: httpx.Client, service_id: str) -> Dict[str, Any]:
    resp = client.get(f"{settings.RENDER_API_BASE}/services/{service_id}/deploys", params={"limit": 1})
    resp.raise_for_status()
    rows = resp.json() or []
    row = rows[0] if rows else {}
    return row.get("deploy", row) or {}


def keep_in_step() -> None:
    """Check the clock's image once, and start its deploy when it is behind this build."""
    clock = settings.RENDER_CRON_SERVICE_ID.strip()
    key = settings.RENDER_API_KEY.strip()
    if not clock or not key:
        print("[resmara] clock image: not checked (no RESMARA_RENDER_CRON_SERVICE_ID or Render key)")
        return
    try:
        with httpx.Client(timeout=12.0,
                          headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}) as client:
            deploy = _latest_deploy(client, clock)
            commit = (deploy.get("commit") or {}).get("id") or ""
            status = deploy.get("status") or ""
            should, why = decide(commit, status, settings.RENDER_GIT_COMMIT)
            if not should:
                print(f"[resmara] clock image: {why}")
                return
            resp = client.post(f"{settings.RENDER_API_BASE}/services/{clock}/deploys",
                               json={"clearCache": "do_not_clear"})
            resp.raise_for_status()
            started = resp.json() or {}
            started = started.get("deploy", started)
            print(f"[resmara] clock image: {why} — deploy {started.get('id')} {started.get('status')}")
    except Exception as exc:  # noqa: BLE001 - a slow Render API must not stop the service booting
        print(f"[resmara] clock image: not checked ({type(exc).__name__}: {exc})")


def latest_clock_build() -> Optional[str]:
    """What the clock is building right now, for the System page. ``None`` when it cannot be read."""
    clock = settings.RENDER_CRON_SERVICE_ID.strip()
    key = settings.RENDER_API_KEY.strip()
    if not clock or not key:
        return None
    try:
        with httpx.Client(timeout=12.0,
                          headers={"Authorization": f"Bearer {key}", "Accept": "application/json"}) as client:
            deploy = _latest_deploy(client, clock)
            return ((deploy.get("commit") or {}).get("id") or "") or None
    except Exception:  # noqa: BLE001
        return None
