"""The New campaign link check opens the link and only green-lights a real listing.

Hermetic: no network. The page reader, photo finder and video finder are stand-ins.

Run:  PYTHONPATH=. python tests/test_listing_check.py
"""
import asyncio
import sys

from app.services import listing_check as lc

PASSED = 0
FAILED = 0


def check(label, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print("  [PASS] %s" % label)
    else:
        FAILED += 1
        print("  [FAIL] %s  %s" % (label, detail))


def run(url, status=200, html="", photos=0, video=False, slow_photos=False):
    async def read(u):
        return status, html

    async def discover(u, limit=60, address=""):
        if slow_photos:
            await asyncio.sleep(5)
        return ["https://img/%d.jpg" % i for i in range(photos)]

    async def find_video(u):
        return {"found": video}

    return asyncio.run(lc.check(url, read=read, discover=discover, find_video=find_video,
                                photo_timeout=0.2, video_timeout=0.2))


print("Link check")
r = run("not a link")
check("a non-link is refused", not r["ok"] and r["reason"] == "not_a_link", r)

r = run("https://my.flexmls.com/listing/123")
check("a sign-in link is refused", not r["ok"] and r["reason"] == "sign_in", r)

r = run("https://www.c21.com/property/9999-nowhere-rd", status=404)
check("a dead page is refused", not r["ok"] and r["reason"] == "no_listing", r)

r = run("https://www.example.com/about-us", html="<h1>About our team</h1>")
check("a page with no home on it is refused (the bug)", not r["ok"] and r["reason"] == "no_listing", r)

r = run("https://www.zillow.com/homedetails/4422-Clay-St-Redding-CA-96003/15238205_zpid/", status=403)
check("a walled portal with an address gives details, asks for photos",
      r["ok"] and r["reason"] == "no_photos" and r["address"].startswith("4422 Clay St"), r)

r = run("https://share.mls.com/abc", html="4 beds 3 baths 2,400 sq ft for sale", photos=31, video=True)
check("a real listing page is a green light with its photo count", r["ok"] and r["reason"] == "ok" and r["photos"] == 31, r)
check("its video is reported", r["video"] is True, r)

r = run("https://share.mls.com/abc", html="Pending · 4 beds 3 baths", photos=20)
check("a pending listing is refused", not r["ok"] and r["reason"] == "pending", r)

r = run("https://share.mls.com/abc", html="4 beds 3 baths for sale", slow_photos=True)
check("a slow gallery is 'no photos', not an error", r["ok"] and r["reason"] == "no_photos", r)

print("\n%d passed, %d failed" % (PASSED, FAILED))
sys.exit(1 if FAILED else 0)
