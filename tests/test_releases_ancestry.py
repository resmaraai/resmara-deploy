"""Two Team room readings that lied: "is this PR live?" and "is Clarity broken?".

Why this file exists:

1. The Releases page decided "live" by comparing each PR's merge commit to the live commit as a
   short-SHA prefix. That is only true for the one PR that happens to *be* the build being served.
   The moment anything lands on top - which is every following day - every earlier PR flipped to
   "waiting", so a page whose entire job is "what shipped" showed nothing shipped. The rule is now
   ancestry: ask GitHub whether the build is ahead of (or identical to) that merge commit.

2. Clarity's data-export API allows roughly ten calls per project per day and the Marketing page
   asked on every load, so the panel went blank by mid-morning with a 429 that reads like a broken
   token. The reader now caches for six hours and serves the last good answer when a refresh is
   refused, labelled stale, instead of claiming the integration is down.

Run:
    cd /Users/dan/resmara && ./venv/bin/python3 tests/test_releases_ancestry.py
"""
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_SCRATCH = "/Users/dan/.hermes/profiles/dev/cache/scratch"
if not os.path.isdir(_SCRATCH):
    _SCRATCH = tempfile.gettempdir()
TMP = tempfile.mkdtemp(prefix="resmara_releases_", dir=_SCRATCH)
os.environ.setdefault("DATABASE_URL", "sqlite:///" + os.path.join(TMP, "r.db"))
os.environ.setdefault("RESMARA_ENV", "test")
os.environ.setdefault("RESMARA_SIMULATE", "1")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-releases-ancestry-0001")
# No payload cache in the test: every assertion must see the live answer it just fed in.
os.environ["RESMARA_RELEASES_CACHE_SECONDS"] = "0"

LIVE = "72a6de758f21" + "0" * 28          # the build being served
INSIDE = "b" * 40                          # merged earlier, contained in LIVE
DIVERGED = "c" * 40                        # merged into a branch that is not in LIVE
TIP = "d" * 40                             # the deploy that is live, by prefix

checks = 0
failures = []


def check(condition, label):
    global checks
    checks += 1
    if not condition:
        failures.append(label)


# --------------------------------------------------------------------------- releases ancestry
from app.core.config import settings                                          # noqa: E402
from app.api import system as sysmod                                          # noqa: E402

settings.GITHUB_TOKEN = "test-token"
settings.RENDER_SERVICE_ID = "srv-test"
settings.GITHUB_REPO = "resmaraai/resmara-deploy"

PULLS = [
    {"number": 6, "title": "Run it until it sells", "state": "closed", "merged_at": "2026-11-18T15:47:42Z",
     "merge_commit_sha": INSIDE, "user": {"login": "bap-digital"}, "html_url": "u", "body": "",
     "created_at": "2026-11-18T15:00:00Z"},
    {"number": 7, "title": "Something on a dead branch", "state": "closed", "merged_at": "2026-11-18T16:00:00Z",
     "merge_commit_sha": DIVERGED, "user": {"login": "bap-digital"}, "html_url": "u", "body": "",
     "created_at": "2026-11-18T15:30:00Z"},
    {"number": 8, "title": "Open work", "state": "open", "merged_at": None,
     "merge_commit_sha": None, "user": {"login": "bap-digital"}, "html_url": "u", "body": "",
     "created_at": "2026-11-18T17:00:00Z"},
]
compares = []


def fake_gh(path, params=None):
    if path == "/pulls":
        return PULLS
    if path.startswith("/pulls/") and path.endswith("/files"):
        return []
    if path.startswith("/compare/"):
        compares.append(path)
        left, right = path.split("/compare/", 1)[1].split("...")
        if left == INSIDE:
            return {"status": "ahead"}          # the live build contains this commit
        return {"status": "diverged"}
    raise AssertionError("unexpected GitHub path " + path)


def fake_deploys(service_id, limit=10):
    return [{"id": "dep-1", "status": "live", "commit": LIVE, "message": "live build",
             "finished_at": "2026-11-18T17:14:43Z", "created_at": "2026-11-18T17:12:00Z"}]


sysmod._gh = fake_gh
sysmod._deploys = fake_deploys

payload = sysmod.releases(limit=8, user=object())
rows = {r["number"]: r for r in payload["releases"]}
check(payload["connected"] is True, "GitHub is reported connected when the token is present")
check(payload["live_commit"] == LIVE[:7], "the live commit is reported as a short sha")
check(rows[6]["deploy"] == "live", "a merged PR contained in the live build reads live (got %r)" % rows[6]["deploy"])
check(rows[7]["deploy"] == "waiting", "a merged PR not contained in the live build reads waiting (got %r)" % rows[7]["deploy"])
check(rows[8]["deploy"] is None, "an open PR carries no deploy verdict")
check(any(INSIDE in c for c in compares), "ancestry was asked of GitHub rather than guessed from prefixes")
check(rows[6]["commit"] == INSIDE[:7], "the PR row still carries its short merge sha for display")
check(payload["live_at"] == "2026-11-18T17:14:43Z", "the live deploy timestamp is passed through")
check(rows[6]["live_at"] is None, "a contained PR has no live timestamp of its own (the card falls back to merged_at)")

# The old prefix rule must not leak back in: a commit that merely shares a prefix with the live one
# is not the same commit, and ancestry is what decides.
check(sysmod._contains(INSIDE, LIVE) is True, "_contains follows GitHub saying ahead")
check(sysmod._contains(DIVERGED, LIVE) is False, "_contains refuses a commit GitHub says diverged")
check(sysmod._contains(LIVE, LIVE) is True, "_contains is true for the build itself")
check(sysmod._contains("", LIVE) is False, "_contains is false with no commit")

# The cache is what makes the page quick, and the store is the answer itself. Reading a nested
# "payload" out of it raised KeyError on the second open, which shipped as a 500 because the test
# window above disables the cache entirely: the branch only ever runs in production.
os.environ["RESMARA_RELEASES_CACHE_SECONDS"] = "60"
sysmod._RELEASES_CACHE.update({"at": 0.0, "payload": None})
sysmod.releases(limit=8, user=object())          # fills the cache
second = sysmod.releases(limit=8, user=object())  # must be served from it, not raise
check(second.get("cached") is True, "a second read inside the window is answered from the cache")
check(second.get("limit") is None, "the cache's own limit key does not leak into the answer")
check(len(second.get("releases") or []) == len(payload["releases"]),
      "the cached answer is the same shape as the fresh one")
os.environ["RESMARA_RELEASES_CACHE_SECONDS"] = "0"
sysmod._RELEASES_CACHE.update({"at": 0.0, "payload": None})


# --------------------------------------------------------------------------- Clarity cache
from app.services import analytics                                           # noqa: E402

CALLS = {"n": 0}


class FakeResponse:
    def __init__(self, code, payload=None):
        self.status_code = code
        self._payload = payload or []

    def json(self):
        return self._payload


class FakeClient:
    """Stands in for httpx.Client; CALLS counts real reads, which is the point of the cache."""

    def __init__(self, *a, **k):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def get(self, url, params=None, headers=None):
        CALLS["n"] += 1
        return NEXT.pop(0) if NEXT else FakeResponse(200, TRAFFIC)


TRAFFIC = [{"metricName": "Traffic", "information": [
    {"totalSessionCount": "7", "distantUserCount": "5"},
    {"totalSessionCount": "3", "distantUserCount": "2"},
]}]
NEXT = []

os.environ["CLARITY_PROJECT_ID"] = "zesn1v5vzg"
os.environ["CLARITY_TOKEN"] = "test-token"

# No credential at all is still an honest empty state with the variable named.
saved_token = analytics._env
analytics._env = lambda name: "" if name == "CLARITY_TOKEN" else saved_token(name)
no_token = analytics.clarity_sessions()
analytics._env = saved_token
check(no_token["connected"] is False and "CLARITY_TOKEN" in (no_token["why"] or ""),
      "without a token the reader names CLARITY_TOKEN instead of failing")

analytics._CLARITY_CACHE.update({"at": 0.0, "payload": None})
analytics.httpx = type("httpx", (), {"Client": FakeClient})

first = analytics.clarity_sessions()
check(first["connected"] is True and first["sessions"] == 10 and first["people"] == 7,
      "a good read totals the traffic rows (got %s)" % ((first.get("sessions"), first.get("people")),))
check(first.get("cached") is False, "a fresh read says it is not cached")
check(CALLS["n"] == 1, "the first read calls Clarity once")

second = analytics.clarity_sessions()
check(second["connected"] is True and second.get("cached") is True, "a second read inside the window is cached")
check(CALLS["n"] == 1, "a cached read does not call Clarity again (calls=%d)" % CALLS["n"])

# The window expires and Clarity refuses: the last good answer survives, labelled stale.
analytics._CLARITY_CACHE["at"] = 0.0
NEXT.append(FakeResponse(429))
third = analytics.clarity_sessions()
check(third["connected"] is True, "a 429 with a held answer stays connected")
check(third.get("stale") is True, "the held answer is labelled stale")
check(third["sessions"] == 10, "the held answer keeps the real numbers")
check("rate-limited" in (third.get("note") or "").lower(), "the note names Clarity's rate limit")

# With nothing held, a 429 must still say so plainly rather than showing a fake zero.
analytics._CLARITY_CACHE.update({"at": 0.0, "payload": None})
NEXT.append(FakeResponse(429))
cold = analytics.clarity_sessions()
check(cold["connected"] is False and cold["sessions"] is None, "a 429 with nothing held reports not connected")
check("rate-limited" in (cold.get("why") or "").lower(), "the cold 429 explains the daily limit")

# A hard error with a held answer is stale too, not an outage.
analytics._CLARITY_CACHE.update({"at": 0.0, "payload": {"connected": True, "sessions": 4, "people": 3,
                                                        "window_days": 3, "why": "", "url": "u"}})
NEXT.append(FakeResponse(500))
held = analytics.clarity_sessions()
check(held.get("stale") is True and held.get("sessions") == 4, "a 500 with a held answer serves the held numbers")

print()
if failures:
    print("FAILURES (%d/%d):" % (len(failures), checks))
    for f in failures:
        print("  -", f)
    sys.exit(1)
print("ALL RELEASES ANCESTRY + CLARITY CACHE TESTS PASSED (%d checks)" % checks)
