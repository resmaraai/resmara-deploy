"""The page must carry the fix, not just the server.

Why this file exists: a fix landed on Render and the owner pressed the same dead button, because
the browser was still running the review.js it had fetched days earlier - script URLs never
changed and the HTML was cacheable. Every shipped .js/.css is now requested with ?v=<newest asset
mtime> and the HTML is sent no-cache, so a deploy reaches the page on the next load.

Run:  cd /Users/dan/resmara && venv/bin/python tests/test_static_cache.py
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A throwaway database, never the real one.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.pop("RESMARA_SIMULATE", None)

os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient                                    # noqa: E402

from app.main import app                                                     # noqa: E402

FAILED = []


def check(label, ok, detail=None):
    shown = "" if ok or detail is None else f"  <- {detail}"
    print(("ok   " if ok else "FAIL ") + label + shown)
    if not ok:
        FAILED.append(label)


ASSET = re.compile(r'(?:src|href)="([^"]+\.(?:js|css)(?:\?[^"]*)?)"')

client = TestClient(app)
for path in ("/", "/reset", "/confirm"):
    r = client.get(path)
    refs = ASSET.findall(r.text)
    check(f"{path} answers 200", r.status_code == 200, r.status_code)
    check(f"{path} is sent no-cache so new asset URLs are read",
          "no-cache" in (r.headers.get("cache-control") or ""), r.headers.get("cache-control"))
    check(f"{path} loads the app's own scripts and styles", len(refs) >= 10, len(refs))
    check(f"{path} stamps every shipped asset", all("?v=" in s for s in refs),
          [s for s in refs if "?v=" not in s])
    check(f"{path} leaves the external font link alone",
          "https://fonts.googleapis.com/css2" in r.text)

r = client.get("/")
stamps = {s.split("?v=")[1] for s in ASSET.findall(r.text) if "?v=" in s}
check("one stamp for the whole page", len(stamps) == 1, stamps)
assets = [s for s in ASSET.findall(r.text) if "?v=" in s]
bad = [s for s in assets if client.get(s).status_code != 200]
check("every stamped asset still serves (the query string is ignored)", not bad, bad)

print("\n" + ("FAILED: " + ", ".join(FAILED) if FAILED else "ALL STATIC-CACHE CHECKS PASSED"))
sys.exit(1 if FAILED else 0)
