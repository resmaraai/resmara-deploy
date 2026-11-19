#!/bin/bash
# Resmara's clock. Runs on the Mac Mini, not inside Render: a free Render web service has no cron
# jobs and sleeps when nobody is looking, so the thing that publishes on time has to live
# somewhere that is always awake. This Mac is.
#
# Every 5 minutes:
#   - publish every approved post that is due (and let the retry ladder in post_retry run)
#   - every 15 minutes, read the comments on live campaigns and email new Social leads
#   - every 6th hour, re-read the listing on each running campaign (sold / pending / offline)
#   - once a day around 14:00 UTC, check every Meta connection's token health
#
# The token is read from a 0600 file and never appears in the log or in `ps`.
set -uo pipefail

TOKEN_FILE="/Users/dan/.hermes/profiles/dev/secrets/resmara-publish-token"
BASE="https://www.resmara.com"
LOG="/Users/dan/.hermes/logs/resmara-scheduler.log"

TOKEN="$(cat "$TOKEN_FILE" 2>/dev/null || true)"
if [ -z "$TOKEN" ]; then
  echo "$(date -u +%FT%TZ) no publish token at $TOKEN_FILE - nothing sent" >> "$LOG"
  exit 0
fi

say() { echo "$(date -u +%FT%TZ) $*" >> "$LOG"; }

post() { # path, timeout
  curl -sS -m "${2:-90}" -X POST -H "X-Resmara-Token: $TOKEN" \
       -H "Content-Type: application/json" -o /tmp/resmara-sched-body.$$ -w "%{http_code}" \
       "$BASE$1"
}

code=$(post "/api/content/publish/run" 120)
body=$(head -c 300 /tmp/resmara-sched-body.$$ 2>/dev/null)
rm -f /tmp/resmara-sched-body.$$
if [ "$code" = "200" ]; then
  case "$body" in
    *'"published": 0'*|*'"published":0'*) ;;   # nothing due - keep the log quiet
    *) say "published: $body" ;;
  esac
else
  say "publish/run returned $code: $body"
fi

hour=$(date -u +%H)
if [ $((10#$hour % 6)) -eq 0 ]; then
  code=$(post "/api/admin/listings/sweep" 180)
  body=$(head -c 300 /tmp/resmara-sched-body.$$ 2>/dev/null)
  rm -f /tmp/resmara-sched-body.$$
  say "listings sweep: $code $body"
fi

# Every third tick (so every 15 minutes) the console's System page runs its checks for real.
# The page reads that freshness, which is why it can say "runs every 15 minutes" and mean it.
if [ $((10#$(date -u +%M) % 15)) -lt 5 ]; then
  code=$(curl -sS -m 120 -H "X-Resmara-Token: $TOKEN" -o /tmp/resmara-sched-check.$$ \
              -w "%{http_code}" "$BASE/api/admin/system-check?refresh=1")
  body=$(head -c 200 /tmp/resmara-sched-check.$$ 2>/dev/null)
  rm -f /tmp/resmara-sched-check.$$
  case "$code" in
    200) case "$body" in *'"fail"'*) say "system check found a failure: $body" ;; esac ;;
    *) say "system-check returned $code: $body" ;;
  esac
fi

# Social leads (Post Engine §10.4), every 15 minutes on the same dial: read the comments on the
# posts and ad that are live, keep the ones that read like buying interest and email the agent.
# Quiet when nothing new came in, so a silent log means "nobody commented", not "the scan died".
if [ $((10#$(date -u +%M) % 15)) -lt 5 ]; then
  code=$(post "/api/admin/leads/scan" 240)
  body=$(head -c 400 /tmp/resmara-sched-body.$$ 2>/dev/null)
  rm -f /tmp/resmara-sched-body.$$
  case "$code" in
    200) case "$body" in *'"leads": 0'*|*'"leads":0'*) ;; *) say "leads: $body" ;; esac ;;
    *) say "leads/scan returned $code: $body" ;;
  esac
fi

# Releases reach the build room on the same 15-minute dial: an open pull request shows up as a
# review task, a merged one as a release task, and the release closes itself only when GitHub
# says its commit is inside the build Render is serving. Quiet when nothing changed.
if [ $((10#$(date -u +%M) % 15)) -lt 5 ]; then
  code=$(curl -sS -m 180 -X POST -H "X-Resmara-Token: $TOKEN" -o /tmp/resmara-sched-br.$$ \
              -w "%{http_code}" "$BASE/api/admin/buildroom/sync")
  body=$(head -c 400 /tmp/resmara-sched-br.$$ 2>/dev/null)
  rm -f /tmp/resmara-sched-br.$$
  case "$code" in
    200) case "$body" in
           *'"created": []'*'"status": []'*'"tested": []'*) ;;   # nothing to write: stay quiet
           *) say "build room sync: $body" ;;
         esac ;;
    *) say "buildroom/sync returned $code: $body" ;;
  esac
fi

if [ "$(date -u +%H%M)" -ge 1400 ] && [ "$(date -u +%H%M)" -lt 1410 ]; then
  code=$(post "/api/oauth/meta/check-all" 180)
  body=$(head -c 300 /tmp/resmara-sched-body.$$ 2>/dev/null)
  rm -f /tmp/resmara-sched-body.$$
  say "meta token health: $code $body"
fi

exit 0
