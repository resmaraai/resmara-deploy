"""Engine 3, the listing link: the link says which house; the file and the photos come from every source.

* Fewer than 14 photos: the form asks for more (the campaign needs 14).
* Photos come from whichever source gives the bigger set (the link, or the same home by address).
* The property research names every source, starting from the pasted link.
"""

import asyncio
import os
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-e3-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from app.services import listing_check, photos  # noqa: E402
from app.services.content_engine import home_file_sources  # noqa: E402

checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


async def read(url):
    return 200, "<html>3 bedrooms 2 baths for sale</html>"


def finder(n):
    async def discover(url, limit=60, address=""):
        return [f"https://img.example/{i}.jpg" for i in range(n)]
    return discover


async def no_video(url):
    return {}


URL = "https://listing.example/905-laurel-bend-redding-ca-96001"
print("14 photos")
r = asyncio.run(listing_check.check(URL, read=read, discover=finder(8), find_video=no_video))
ok("8 photos: asks for more, naming the 14 needed", r["ok"] and r["reason"] == "no_photos" and "14" in r["message"]
   and r["photos"] == 8, r)
r = asyncio.run(listing_check.check(URL, read=read, discover=finder(20), find_video=no_video))
ok("20 photos: good to build", r["ok"] and r["reason"] == "ok", r)

print("The best set of photos wins")


class FakeClient:
    async def aclose(self):
        pass


real_page, real_trulia = photos._photos_on_page, photos._trulia_by_address


async def page_with(n):
    async def f(client, url, limit, address, zipcode, trace):
        return [f"https://link.example/{i}.jpg" for i in range(n)]
    return f


async def trulia_with(n):
    async def f(client, address, zipcode, limit, trace):
        return [f"https://trulia.example/{i}.jpg" for i in range(n)]
    return f


async def run(page_n, trulia_n):
    photos._photos_on_page = await page_with(page_n)
    photos._trulia_by_address = await trulia_with(trulia_n)
    try:
        return await photos.discover(URL, limit=60, client=FakeClient(), address="905 Laurel Bend, Redding, CA 96001")
    finally:
        photos._photos_on_page, photos._trulia_by_address = real_page, real_trulia


got = asyncio.run(run(9, 30))
ok("9 on the link, 30 by address: the bigger gallery is used", len(got) == 30 and got[0].startswith("https://trulia"), len(got))
got = asyncio.run(run(20, 30))
ok("a full set on the link is kept (no lookup needed)", len(got) == 20 and got[0].startswith("https://link"), len(got))
got = asyncio.run(run(10, 5))
ok("the link's set stays when it's the bigger one", len(got) == 10 and got[0].startswith("https://link"), len(got))
got = asyncio.run(run(1, 25))
ok("a hero shot is topped up from the address", len(got) == 26, len(got))

print("The home's file comes from every source")


class B:
    listing_url = None
    property_facts = "Listing: https://aryeo.example/905-laurel"


text = home_file_sources(B())
ok("starts from the pasted link, as which house", "https://aryeo.example/905-laurel" in text and "WHICH house" in text)
ok("names the portals, the brokerage, the photographer and public records",
   all(w in text for w in ("Zillow", "Realtor.com", "Redfin", "Homes.com", "Trulia", "brokerage", "photographer", "public records")))

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL ENGINE 3 LISTING LINK TESTS PASSED")
