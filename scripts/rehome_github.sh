#!/usr/bin/env bash
# Move the resmara code off the old GitHub account onto the target owner.
#
#   ./scripts/rehome_github.sh resmaraai            # execute
#   ./scripts/rehome_github.sh resmaraai --dry-run  # print only
#
# Creates <owner>/resmara (private) and <owner>/resmara-deploy (public, the
# Render mirror), pushes every branch and tag, repoints the two local remotes,
# and keeps the old repositories reachable as `old-github` / `old-deploy`.
# Nothing is deleted on GitHub.
set -euo pipefail

OWNER="${1:-}"
DRY=0
[[ "${2:-}" == "--dry-run" ]] && DRY=1
[[ -n "$OWNER" ]] || { echo "usage: $0 <github-owner> [--dry-run]"; exit 2; }

cd "$(dirname "$0")/.."

ACTIVE="$(gh api user --jq .login)"
echo "gh account        : $ACTIVE"
echo "target owner      : $OWNER"
echo "code repo         : $OWNER/resmara"
echo "render mirror repo: $OWNER/resmara-deploy"
if [[ "$OWNER" != "$ACTIVE" ]]; then
  echo "ERROR: gh is authenticated as $ACTIVE, not $OWNER. Repos would be created under the wrong account."
  exit 1
fi

git diff --quiet && git diff --cached --quiet || { echo "ERROR: working tree dirty — commit first."; exit 1; }
if git ls-files | grep -qE '(^|/)\.env$|\.db$|\.pem$'; then
  echo "ERROR: secrets or a local db are tracked. Refusing to push."; exit 1
fi

run() { if [[ $DRY -eq 1 ]]; then echo "  [dry-run] $*"; else "$@"; fi; }

# 1. Park an old remote under a backup name so the new one can take the name.
park_remote() { # $1 = live name, $2 = backup name, $3 = new url
  local live="$1" backup="$2" newurl="$3" cur
  if git remote | grep -qx "$live"; then
    cur="$(git remote get-url "$live")"
    if [[ "$cur" == "$newurl" ]]; then echo "remote $live already points at $newurl"; return 0; fi
    if git remote | grep -qx "$backup"; then
      run git remote remove "$live"
    else
      run git remote rename "$live" "$backup"
    fi
  fi
}

park_remote origin old-github "https://github.com/$OWNER/resmara.git"
park_remote deploy old-deploy "https://github.com/$OWNER/resmara-deploy.git"

# 2. Code repository (private).
if gh repo view "$OWNER/resmara" >/dev/null 2>&1; then
  echo "repo $OWNER/resmara exists — wiring remote only"
  git remote | grep -qx origin || run git remote add origin "https://github.com/$OWNER/resmara.git"
else
  run gh repo create "$OWNER/resmara" --private --source=. --remote=origin
fi
# gh adds the remote itself, but not if it already exists under another name —
# make the wiring explicit so a create that skips it cannot break the push.
git remote | grep -qx origin || run git remote add origin "https://github.com/$OWNER/resmara.git"
run git push origin --all
run git push origin --tags

# 3. Render mirror (public: Render builds it without an account integration).
if gh repo view "$OWNER/resmara-deploy" >/dev/null 2>&1; then
  echo "repo $OWNER/resmara-deploy exists — wiring remote only"
  git remote | grep -qx deploy || run git remote add deploy "https://github.com/$OWNER/resmara-deploy.git"
else
  run gh repo create "$OWNER/resmara-deploy" --public --description "Deploy mirror for Render (temporary)"
fi
git remote | grep -qx deploy || run git remote add deploy "https://github.com/$OWNER/resmara-deploy.git"
run git push deploy HEAD:main

echo
echo "remotes now:"
git remote -v
