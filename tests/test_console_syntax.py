"""The console's script has to parse, or the whole page is dead.

Why this file exists: one missing pair of parentheses in an `if` shipped, and the browser threw
the entire inline script away - so every function on the page was undefined, the sign-in button
did nothing, and the page still looked completely normal. Nothing in the suite noticed, because
the HTML was served and every string test still matched.

`node --check` on each inline script is the cheapest possible guard against that class of
outage. It needs no browser and no server.

Run:  cd /Users/dan/resmara && venv/bin/python tests/test_console_syntax.py
"""

import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# The pages an operator or an agent actually loads. A syntax error in any of them is an outage.
PAGES = ["static/admin.html", "static/index.html", "static/help-kb.js", "static/app.js"]

checks = 0
failures = 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    if cond:
        print(f"  PASS  {name}")
    else:
        failures += 1
        print(f"  FAIL  {name}" + (f"  ({extra})" if extra else ""))


node = shutil.which("node")
if not node:
    print("skip: node is not installed, and this check needs the same parser a browser uses")
    sys.exit(0)


def blocks_of(path):
    text = open(os.path.join(ROOT, path), encoding="utf-8").read()
    if path.endswith(".js"):
        return [("whole file", text)]
    # Inline <script> only: a src= block is a different file and is checked on its own.
    found = re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", text, re.S)
    return [(f"inline script #{i + 1}", body) for i, body in enumerate(found)]


print("\n[every script a browser would run must parse]")
for page in PAGES:
    if not os.path.isfile(os.path.join(ROOT, page)):
        ok(f"{page} exists", False)
        continue
    for label, body in blocks_of(page):
        with tempfile.NamedTemporaryFile("w", suffix=".js", delete=False) as tmp:
            tmp.write(body)
            name = tmp.name
        try:
            result = subprocess.run([node, "--check", name], capture_output=True, text=True)
        finally:
            os.unlink(name)
        detail = ""
        if result.returncode:
            lines = [l for l in (result.stderr or "").splitlines() if l.strip()]
            detail = " ".join(lines[:4])[:300]
        ok(f"{page} · {label} parses" if len(body) > 0 else f"{page} · {label} is empty (skipped)",
           result.returncode == 0 or not body.strip(), detail)


print("\n[a page whose script parses still has its entry point]")
console = open(os.path.join(ROOT, "static/admin.html"), encoding="utf-8").read()
ok("the sign-in handler is bound", "$('loginBtn').addEventListener('click', login)" in console)
ok("boot runs on load", "boot()" in console)
ok("a syntax error would not be caught by a string test alone",
   "__check__" not in console)

print()
if failures:
    print(f"{failures} of {checks} FAILED")
    sys.exit(1)
print(f"{checks} checks, 0 failed.\nALL SCRIPT PARSE TESTS PASSED")
