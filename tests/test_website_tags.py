"""The Website page's tag rows: an id on the service, not a string in the HTML.

Why this file exists: ``static/tags.js`` installs the GA4, Meta pixel and Clarity snippets from
``/api/public/tags`` at run time. The Website page used to grep the homepage HTML for
``googletagmanager.com/gtag/js`` and friends, so a site with tracking fully on reported
"Not found on the homepage HTML" for every tag - a false alarm on the one page whose job is to say
whether measurement works. The rows are decided from the ids now, and the HTML only has to load the
injector.

Run:  cd /Users/dan/resmara && venv/bin/python tests/test_website_tags.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# A throwaway database, never the real one.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.pop("RESMARA_SIMULATE", None)

from app.api.marketing import _tag_rows                                    # noqa: E402

FAILED = []


def check(label, ok, detail=None):
    shown = "" if ok or detail is None else f"  <- {detail}"
    print(("ok   " if ok else "FAIL ") + label + shown)
    if not ok:
        FAILED.append(label)


def by_name(rows):
    return {r["name"]: r for r in rows}


def set_ids(ga4="", clarity="", pixel=""):
    for env, value in (("GA4_MEASUREMENT_ID", ga4), ("CLARITY_PROJECT_ID", clarity),
                       ("META_PIXEL_ID", pixel),
                       ("RESMARA_GA4_MEASUREMENT_ID", ""), ("RESMARA_CLARITY_PROJECT_ID", ""),
                       ("RESMARA_META_PIXEL_ID", "")):
        if value:
            os.environ[env] = value
        else:
            os.environ.pop(env, None)


PAGE_WITH_LOADER = '<html><head><script src="tags.js"></script></head><body></body></html>'
PAGE_WITHOUT_LOADER = "<html><head></head><body>no tags here</body></html>"

# 1. Everything wired: the ids are the truth even though no vendor snippet is in the HTML.
set_ids(ga4="G-TEST12345", clarity="abcdefghij", pixel="123456789012345")
rows = by_name(_tag_rows(PAGE_WITH_LOADER))
check("Google tag ok when the id is set", rows["Google tag"]["status"] == "ok", rows["Google tag"])
check("Google tag names the id it found", "G-TEST12345" in rows["Google tag"]["detail"],
      rows["Google tag"])
check("Meta pixel ok when the id is set", rows["Meta pixel"]["status"] == "ok", rows["Meta pixel"])
check("Clarity ok when the id is set", rows["Clarity"]["status"] == "ok", rows["Clarity"])
check("no row claims the snippet is missing",
      all("Not found on the homepage HTML" not in r["detail"] for r in rows.values()))

# 2. Nothing configured: the row has to name the env var that fixes it.
set_ids()
rows = by_name(_tag_rows(PAGE_WITH_LOADER))
check("GA4 row warns with its env var", rows["Google tag"]["status"] == "warn"
      and "GA4_MEASUREMENT_ID" in rows["Google tag"]["detail"], rows["Google tag"])
check("Clarity row warns with its env var", rows["Clarity"]["status"] == "warn"
      and "CLARITY_PROJECT_ID" in rows["Clarity"]["detail"], rows["Clarity"])
check("Meta row warns with its env var", rows["Meta pixel"]["status"] == "warn"
      and "META_PIXEL_ID" in rows["Meta pixel"]["detail"], rows["Meta pixel"])

# 3. An id with no injector on the page is a warn that says so - the tag cannot run.
set_ids(ga4="G-TEST12345")
rows = by_name(_tag_rows(PAGE_WITHOUT_LOADER))
check("id without tags.js warns about the loader", rows["Google tag"]["status"] == "warn"
      and "tags.js" in rows["Google tag"]["detail"], rows["Google tag"])

# 4. An empty page still produces one row per tag, so the page never shows a blank.
rows = _tag_rows("")
check("four tag rows on an empty page", len(rows) == 4, rows)
check("Site answers is added by the caller, not here", all(r["name"] != "Site answers" for r in rows))

# 5. The Ads tag is the one still pasted into the HTML.
rows = by_name(_tag_rows('<script src="https://googleads.g.doubleclick.net/x"></script>'))
check("Ads tag ok when pasted", rows["Google Ads tag"]["status"] == "ok", rows["Google Ads tag"])
rows = by_name(_tag_rows(PAGE_WITH_LOADER))
check("Ads tag absent is a warn, not a failure", rows["Google Ads tag"]["status"] == "warn",
      rows["Google Ads tag"])

if FAILED:
    print(f"\n{len(FAILED)} FAILED: " + ", ".join(FAILED))
    sys.exit(1)
print("ALL WEBSITE TAG CHECKS PASSED")
