import asyncio, os, sys, time
sys.path.insert(0, "/Users/dan/resmara")
os.environ.setdefault("DATABASE_URL", "sqlite:////tmp/x.db")
from app.services import photos

ADDRS = [
    ("sycamore", "2163 Sycamore Dr, Redding, CA 96001"),
    ("harpole", "1354 Harpole Rd, Redding, CA 96002"),
    ("mojave", "6495 Mojave Ct, Anderson, CA 96007"),
    ("coggins", "892 Coggins St, Redding, CA 96003"),
]


async def one(label, addr):
    t = time.time()
    try:
        urls = await asyncio.wait_for(
            photos.discover("https://www.trulia.com/sitemaps/", limit=20, address=addr), 240)
        print(f"{label}: {len(urls)} photos in {round(time.time()-t)}s", flush=True)
        for u in urls[:2]:
            print("   ", u, flush=True)
    except Exception as e:
        print(f"{label}: ERR {type(e).__name__} {str(e)[:120]} after {round(time.time()-t)}s", flush=True)


async def main():
    await asyncio.gather(*(one(l, a) for l, a in ADDRS))

asyncio.run(main())
