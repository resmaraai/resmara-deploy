#!/usr/bin/env python3
"""render.yaml has to be safe to SYNC onto the live service, not merely valid YAML.

Linking a Render Blueprint makes this file the source of truth for resources created by hand in
the dashboard. Two failure modes come from that, and neither is a YAML error:

  * a name that does not match the live resource makes Render stand up a SECOND copy of it
    (another web service, another Postgres — and the free one is deleted on its expiry date);
  * a setting omitted from the file reverts to its default, and Render's default region is
    oregon while this service runs in virginia.

The other half is the Meta pair: the app ID and the app secret are changed together or not at
all. A new ID with the old secret answers "Error validating client secret" on every token
exchange and reads like a code bug, so both are placeholders and the wanted ID lives in a
comment — which this file asserts, because "helpfully" inlining the ID is the mistake.

Finally, a cron job in this file is a purchase: cron services have no free tier and billing
starts when the service exists. The publishing clock runs from the Mac today, so an "enabled"
cron here is a charge nobody agreed to.
"""
from __future__ import annotations

import re
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


# The live resources, read from GET /v1/services and /v1/postgres: these names are the ones a
# sync must MATCH, so they are pinned here rather than left to whoever edits the file next.
LIVE_WEB_NAME = "resmara"
LIVE_WEB_REGION = "virginia"
LIVE_WEB_REPO = "https://github.com/resmaraai/resmara-deploy"
LIVE_DB_NAME = "resmara-db"
LIVE_DB_DATABASE = "resmara"
LIVE_DB_REGION = "virginia"

# Every variable the live service actually carries. The Blueprint preserves unlisted variables,
# so this is not a deploy requirement — it is the inventory that stops a reader believing the
# file is the whole service.
LIVE_KEYS = {
    "DATABASE_URL", "RESMARA_ENV", "RESMARA_PUBLIC_BASE_URL", "SECRET_KEY",
    "RESMARA_PUBLISH_TOKEN", "META_CLIENT_ID", "META_CLIENT_SECRET", "META_SCOPES",
    "META_SYSTEM_TOKEN", "META_AD_ACCOUNT_ID", "META_PAGE_ID", "META_IG_ID", "META_PIXEL_ID",
    "OPENAI_API_KEY", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_CENTS",
    "RESEND_API_KEY", "MAIL_FROM", "GA4_PROPERTY_ID", "GA4_MEASUREMENT_ID", "GA4_SA_JSON",
    "CLARITY_PROJECT_ID", "CLARITY_TOKEN", "RESMARA_PAGESPEED_KEY", "RESMARA_GITHUB_TOKEN",
    "RESMARA_RENDER_API_KEY", "RESMARA_RENDER_SERVICE_ID", "RESMARA_ADMIN_EMAILS",
    "RESMARA_SIGNUP_CODE",
}

# Keys whose value must never be a literal in git. sync:false (dashboard) or fromDatabase /
# fromService (derived) only.
SECRET_KEYS = {
    "SECRET_KEY", "RESMARA_PUBLISH_TOKEN", "META_CLIENT_SECRET", "META_SYSTEM_TOKEN",
    "OPENAI_API_KEY", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "RESEND_API_KEY",
    "GA4_SA_JSON", "CLARITY_TOKEN", "RESMARA_PAGESPEED_KEY", "RESMARA_GITHUB_TOKEN",
    "RESMARA_RENDER_API_KEY", "RESMARA_SIGNUP_CODE", "RESMARA_ADMIN_EMAILS",
}


def main() -> int:
    import yaml

    path = ROOT / "render.yaml"
    text = path.read_text()
    try:
        doc = yaml.safe_load(text)
    except Exception as exc:                                    # noqa: BLE001 - reported
        print("  FAIL render.yaml does not parse: %s" % exc)
        return 1
    check("render.yaml parses as YAML", isinstance(doc, dict))

    # ── previews: the declaration Adam asked for, kept in step ──────────────────────────
    prev = doc.get("previews") or {}
    check("preview generation is automatic", prev.get("generation") == "automatic", str(prev))
    check("previews expire after 3 days", prev.get("expireAfterDays") == 3, str(prev))

    # ── the web service must MATCH the live one ────────────────────────────────────────
    services = doc.get("services") or []
    web = [s for s in services if s.get("type") == "web"]
    check("exactly one web service", len(web) == 1, str([s.get("name") for s in services]))
    if not web:
        return 1
    w = web[0]
    check("web service name matches the live service", w.get("name") == LIVE_WEB_NAME,
          str(w.get("name")))
    check("web service region is spelled out and matches", w.get("region") == LIVE_WEB_REGION,
          "Render defaults omitted regions to oregon; live is %s" % LIVE_WEB_REGION)
    check("web service builds the deploy mirror", w.get("repo") == LIVE_WEB_REPO, str(w.get("repo")))
    check("web service branch is main", w.get("branch") == "main", str(w.get("branch")))
    check("web service is docker", w.get("runtime") == "docker", str(w.get("runtime")))
    check("dockerfile path is declared", (w.get("dockerfilePath") or "") == "./Dockerfile",
          str(w.get("dockerfilePath")))
    check("deploys on commit", (w.get("autoDeployTrigger") or "") == "commit",
          str(w.get("autoDeployTrigger")))

    # ── the database must MATCH too, or a sync creates a second one ────────────────────
    dbs = doc.get("databases") or []
    check("exactly one database", len(dbs) == 1, str([d.get("name") for d in dbs]))
    if dbs:
        d = dbs[0]
        check("database name matches the live one", d.get("name") == LIVE_DB_NAME, str(d.get("name")))
        check("databaseName matches the live one", d.get("databaseName") == LIVE_DB_DATABASE,
              str(d.get("databaseName")))
        check("database region is spelled out and matches", d.get("region") == LIVE_DB_REGION,
              str(d.get("region")))
        check("database plan matches", d.get("plan") == "0.1c-256mb", str(d.get("plan")))
        check("database is private-network only", d.get("ipAllowList") == [],
              str(d.get("ipAllowList")))

    # ── the Meta app pair: placeholders, never a literal ID ───────────────────────────
    env = {e.get("key"): e for e in (w.get("envVars") or []) if e.get("key")}
    check("META_CLIENT_ID is a dashboard value, not a literal", env.get("META_CLIENT_ID", {}).get("sync") is False,
          str(env.get("META_CLIENT_ID")))
    check("META_CLIENT_SECRET is a dashboard value", env.get("META_CLIENT_SECRET", {}).get("sync") is False,
          str(env.get("META_CLIENT_SECRET")))
    check("the wanted app id is recorded in the file", "1135911812356864" in text)
    check("the retired app id is not referenced as a value", "value: \"1881970083170197\"" not in text
          and "value: 1881970083170197" not in text)

    # ── inventory and references ──────────────────────────────────────────────────────
    keys = [e.get("key") for e in (w.get("envVars") or []) if e.get("key")]
    check("every live variable is declared", LIVE_KEYS <= set(keys),
          "missing: %s" % sorted(LIVE_KEYS - set(keys)))
    check("no duplicate variable keys", len(keys) == len(set(keys)),
          str([k for k in set(keys) if keys.count(k) > 1]))
    check("no environment variable is both a value and a reference",
          all(sum(1 for f in ("value", "sync", "generateValue", "fromDatabase", "fromService")
                  if f in e) == 1 for e in (w.get("envVars") or [])),
          str([e.get("key") for e in (w.get("envVars") or [])
               if sum(1 for f in ("value", "sync", "generateValue", "fromDatabase", "fromService")
                      if f in e) != 1]))
    db_names = {d.get("name") for d in dbs}
    check("every fromDatabase reference exists",
          all((e.get("fromDatabase") or {}).get("name") in db_names
              for e in (w.get("envVars") or []) if e.get("fromDatabase")),
          str([e.get("key") for e in (w.get("envVars") or [])
               if e.get("fromDatabase") and (e["fromDatabase"].get("name") not in db_names)]))
    svc_names = {s.get("name") for s in services}
    check("every fromService reference exists",
          all((e.get("fromService") or {}).get("name") in svc_names
              for e in (w.get("envVars") or []) if e.get("fromService")))

    # ── nothing secret in git ─────────────────────────────────────────────────────────
    check("no secret key carries a literal value",
          all(("value" not in env.get(k, {})) for k in SECRET_KEYS if k in env),
          str([k for k in SECRET_KEYS if k in env and "value" in env[k]]))
    patterns = [r"sk_live_[A-Za-z0-9]{6,}", r"rk_live_[A-Za-z0-9]{6,}", r"whsec_[A-Za-z0-9]{6,}",
                r"gh[pousr]_[A-Za-z0-9]{10,}", r"re_[A-Za-z0-9]{12,}", r"\b[0-9a-f]{40}\b"]
    hits = [p for p in patterns if re.search(p, text)]
    check("no key/token literal anywhere in the file", not hits, str(hits))

    # ── a cron here is a purchase, not a line of YAML ──────────────────────────────────
    crons = [s for s in services if s.get("type") == "cron"]
    check("no cron service is enabled (it costs ~$1/mo from the moment it exists)", not crons,
          str([s.get("name") for s in crons]))
    # If one is ever enabled, these two settings are not optional: a cron with its own generated
    # SECRET_KEY cannot decrypt stored Meta tokens, and it has no inbound host to infer.
    for c in crons:
        cen = {e.get("key"): e for e in (c.get("envVars") or []) if e.get("key")}
        check("cron %s takes SECRET_KEY from the web service" % c.get("name"),
              (cen.get("SECRET_KEY", {}).get("fromService") or {}).get("envVarKey") == "SECRET_KEY",
              str(cen.get("SECRET_KEY")))
        check("cron %s sets RESMARA_PUBLIC_BASE_URL" % c.get("name"),
              (cen.get("RESMARA_PUBLIC_BASE_URL") or {}).get("value") == "https://www.resmara.com",
              str(cen.get("RESMARA_PUBLIC_BASE_URL")))

    print("\n%s" % ("ALL CHECKS PASSED" if not FAILS else "%d FAILED" % FAILS))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
