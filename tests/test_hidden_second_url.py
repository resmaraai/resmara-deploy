#!/usr/bin/env python3
"""A public MLS link has to give up the gallery it is hiding.

Agents paste the MLS/IDX "public link" — a shop window with one hero photo and a control
that opens the real listing in an iframe or a viewer on another host. Fetching that one page
returns one image, which is not a gallery. These checks pin the pointer reader (pure) and
the hop that follows it (mock transport, no internet).
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILS = 0


def check(label: str, ok: bool, detail: str = "") -> None:
    global FAILS
    print(("ok   " if ok else "FAIL ") + label + (f" — {detail}" if detail and not ok else ""))
    if not ok:
        FAILS += 1


def main() -> int:
    import asyncio

    import httpx

    from app.services import photos

    # --- the pointer reader: every shape an MLS page uses to hide the real listing --------
    PAGE = """<html><head>
      <link rel="canonical" href="https://viewer.mls.example.test/listing/8844221">
      <meta property="og:image" content="https://cdn.mls.example.test/hero.jpg">
    </head><body>
      <img src="https://cdn.mls.example.test/hero.jpg">
      <a href="/photos/8844221/all" title="See all photos">32 photos</a>
    </body></html>"""
    got = photos.hidden_second_urls(PAGE, "https://share.mls.example.test/s/abc123")
    check("a canonical pointer on another host is followed",
          got[:1] == ["https://viewer.mls.example.test/listing/8844221"], str(got))
    check("a 'see all photos' link is picked up as a fallback pointer",
          "https://share.mls.example.test/photos/8844221/all" in got, str(got))
    check("the hero image is never mistaken for a page", not any("hero.jpg" in u for u in got), str(got))
    check("the page itself is never offered as the second url",
          "https://share.mls.example.test/s/abc123" not in got, str(got))

    IFRAME = """<html><head><meta name="twitter:url" content="https://v2.mls.example.test/p/9">
      </head><body><iframe src="https://player.mls.example.test/tour/9" allowfullscreen></iframe>
      <script>window.location.href = "/viewer/9";</script></body></html>"""
    got = photos.hidden_second_urls(IFRAME, "https://share.mls.example.test/9")
    check("an iframe viewer is followed", "https://player.mls.example.test/tour/9" in got, str(got))
    check("a JS redirect is followed", "https://share.mls.example.test/viewer/9" in got, str(got))
    check("og/twitter url is followed", "https://v2.mls.example.test/p/9" in got, str(got))

    JSON_POINTER = """<html><body><script>var cfg = {"listingUrl":"https://idx.mls.example.test/listings/7788",
      "photoUrl":"https://cdn.mls.example.test/gallery/1.jpg"};</script>
      <meta http-equiv="refresh" content="0;url=https://idx.mls.example.test/redir/7788"></body></html>"""
    got = photos.hidden_second_urls(JSON_POINTER, "https://share.mls.example.test/x")
    check("a listing URL inside an inline config is followed",
          "https://idx.mls.example.test/listings/7788" in got, str(got))
    check("a meta refresh is followed",
          "https://idx.mls.example.test/redir/7788" in got, str(got))
    check("an image URL inside the config is dropped",
          not any("gallery/1.jpg" in u for u in got), str(got))
    check("pointers are capped so one bad page cannot become a crawl",
          len(photos.hidden_second_urls(JSON_POINTER, "https://share.mls.example.test/x")) <= 3)

    # --- the hop: a one-photo public page still yields the gallery ----------------------
    PUBLIC = """<html><head><meta property="og:image" content="https://cdn.mls.example.test/hero.jpg">
      </head><body><p>Public listing</p>
      <iframe src="https://viewer.mls.example.test/listing/8844221"></iframe></body></html>""" + \
        "<!-- " + "p" * 2100 + " -->"
    GALLERY = """<html><body>
      <img src="https://cdn.mls.example.test/gallery/front.jpg">
      <img src="https://cdn.mls.example.test/gallery/kitchen.jpg">
      <img src="https://cdn.mls.example.test/gallery/living.jpg">
      <img src="https://cdn.mls.example.test/gallery/bath.jpg">
      <img src="https://cdn.mls.example.test/gallery/yard.jpg">
      </body></html>""" + "<!-- " + "g" * 2100 + " -->"
    hits: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        hits.append(url)
        if url.endswith("/s/abc123"):
            return httpx.Response(200, text=PUBLIC)
        if url == "https://viewer.mls.example.test/listing/8844221":
            return httpx.Response(200, text=GALLERY)
        return httpx.Response(404, text="nope")

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as mock:
            trace: list = []
            got = await photos.discover("https://share.mls.example.test/s/abc123",
                                        limit=6, client=mock, address="", trace=trace)
            return got, trace

    found, trace = asyncio.run(run())
    check("the gallery behind the public link is what comes back",
          len([u for u in found if "/gallery/" in u]) == 5, str(found))
    check("the viewer page was fetched", "https://viewer.mls.example.test/listing/8844221" in hits, str(hits))
    check("the hero image is kept, not thrown away",
          "https://cdn.mls.example.test/hero.jpg" in found, str(found))
    check("the viewer fetch is in the trace", len(trace) >= 2, str(trace))

    print()
    if FAILS:
        print(f"{FAILS} check(s) failed")
        return 1
    print("all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
