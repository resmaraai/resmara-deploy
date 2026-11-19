#!/usr/bin/env bash
# The project's test suite: every isolated check, in one command.
#
#   ./scripts/run_tests.sh              # the project's venv, else `python3`
#   PYTHON=/path/to/.venv/bin/python ./scripts/run_tests.sh
#
# Exits non-zero on the first failure. Deliberately excludes tests/smoke_live.py,
# tests/real_build_once.py and tests/probe_report.py: those talk to a running server (and the
# last two spend nothing but do build real campaigns), so they belong to a deployment check —
# `scripts/selfcheck.py --base <url>` is that check.
set -uo pipefail
cd "$(dirname "$0")/.."

# The app's own dependencies live in the project venv; the system interpreter has no fastapi, so
# a bare `python3` fails at import and says nothing about the code. Prefer the venv that is here.
if [ -n "${PYTHON:-}" ]; then
  PY="$PYTHON"
elif [ -x ./venv/bin/python3 ]; then
  PY=./venv/bin/python3
else
  PY=python3
fi
export PYTHONPATH="$PWD"

fail=0
run() {
  local label="$1"; shift
  local out
  if out=$("$@" 2>&1); then
    printf 'ok   %-26s %s\n' "$label" "$(printf '%s' "$out" | tail -1)"
  else
    printf 'FAIL %-26s\n' "$label"
    printf '%s\n' "$out" | tail -15
    fail=1
  fi
}

for t in tests/test_*.py; do
  run "$(basename "$t" .py)" "$PY" "$t"
done

if ! command -v node >/dev/null 2>&1; then
  echo "skip node suites (node not installed)"
else
  run test_frontend_api node tests/test_frontend_api.js
  run test_client_workspace node tests/test_client_workspace.js
  run test_new_campaign_flow node tests/test_new_campaign_flow.js
  run test_review_scope node tests/test_review_scope.js
  if [ -n "${CI_SKIP_DEPLOYED_UI:-}" ]; then
    echo "skip test_deployed_ui (CI_SKIP_DEPLOYED_UI set: it reads a deployment's public URL)"
  else
    run test_deployed_ui node tests/test_deployed_ui.js
  fi
fi

[ "$fail" = 0 ] && echo "ALL SUITES PASSED" || echo "SUITE FAILURES"
exit "$fail"
