#!/usr/bin/env python3
"""The consent dialog asks for exactly the permissions App Review is recording.

Adam's brief (24 Nov 2026): the App Review videos have to show the Facebook login asking for
pages_read_user_content, instagram_manage_comments and email. The dialog sends whatever the app's
META_SCOPES says, and that list lived in two places that had drifted apart - the code default in
app/api/oauth.py and the value in render.yaml - so a permission could be missing from one and not
the other with nothing on screen to show it.

Meta fails the WHOLE dialog with "Invalid Scopes" if any single permission is not enabled for the
app's use cases, which is why the list stays configuration and the code never adds to it on its
own. This test pins the two declarations to each other and to what Adam needs to record.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Config reads the environment at import time. A throwaway sqlite URL keeps the import from
# create_all()-ing a resmara.db into the repo root. (This repo's own .env carries a developer's
# short META_SCOPES, so the runtime list is checked through the override below, not here.)
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ.pop("RESMARA_SIMULATE", None)

CHECKS = 0
FAILS = 0


def ok(label: str, cond: bool, detail: str = "") -> None:
    global CHECKS, FAILS
    CHECKS += 1
    if cond:
        print("  ok   %s" % label)
    else:
        FAILS += 1
        print("  FAIL %s %s" % (label, detail))


from app.api.oauth import _DEFAULT_SCOPES                       # noqa: E402

# What Adam reported the live dialog asks for (11, in render.yaml's old order) plus the three he
# needs the recording to show.
REQUIRED = [
    "ads_management", "ads_read", "pages_manage_ads", "read_insights", "business_management",
    "pages_read_engagement", "pages_show_list", "pages_manage_posts", "instagram_basic",
    "instagram_content_publish", "instagram_manage_insights",
    # Submitted to Meta for App Review on 23-24 Nov, and the reason for this test.
    "instagram_manage_comments", "pages_read_user_content", "email",
]

for scope in REQUIRED:
    ok("the code default asks for %s" % scope, scope in _DEFAULT_SCOPES)
ok("no permission appears twice", len(_DEFAULT_SCOPES) == len(set(_DEFAULT_SCOPES)), str(_DEFAULT_SCOPES))
ok("the ad and Page permissions stay (the dialog cannot be trimmed for the recording)",
   {"ads_management", "pages_manage_ads", "pages_show_list"} <= set(_DEFAULT_SCOPES), str(_DEFAULT_SCOPES))

# ── render.yaml declares the same list ────────────────────────────────────────────────────────
import yaml                                                        # noqa: E402

doc = yaml.safe_load((ROOT / "render.yaml").read_text())
web = [s for s in (doc.get("services") or []) if s.get("type") == "web"][0]
env = {e.get("key"): e.get("value") for e in (web.get("envVars") or []) if e.get("key")}
declared = [s.strip() for s in str(env.get("META_SCOPES") or "").replace("\n", "").split(",") if s.strip()]
ok("render.yaml declares META_SCOPES as a literal value", bool(declared), str(env.get("META_SCOPES"))[:80])
ok("render.yaml and the code default ask for the same permissions",
   set(declared) == set(_DEFAULT_SCOPES),
   "only in render.yaml: %s  only in code: %s" % (sorted(set(declared) - set(_DEFAULT_SCOPES)),
                                                  sorted(set(_DEFAULT_SCOPES) - set(declared))))
for scope in ("instagram_manage_comments", "pages_read_user_content", "email"):
    ok("render.yaml asks for %s" % scope, scope in declared)

# ── the env var still wins, which is what a live service's value does ────────────────────────
# load_dotenv() does not override an exported variable, so a subprocess tells the truth here.
probe = subprocess.run(
    [sys.executable, "-c",
     "from app.api.oauth import META_SCOPES; print(','.join(META_SCOPES))"],
    cwd=str(ROOT), capture_output=True, text=True,
    env={**os.environ, "PYTHONPATH": str(ROOT), "DATABASE_URL": "sqlite:///:memory:",
         "META_SCOPES": "ads_management,email"},
)
asked = [ln.strip() for ln in (probe.stdout or "").splitlines() if ln.strip()]
asked = asked[-1] if asked else ""
ok("META_SCOPES on the service overrides the default list", asked == "ads_management,email",
   asked or (probe.stderr or "")[-200:])

print("\n%d/%d passed" % (CHECKS - FAILS, CHECKS))
raise SystemExit(1 if FAILS else 0)
