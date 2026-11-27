"""Bring real listing photos into a campaign.

The content engine can write captions from the property facts alone, but it cannot
invent the gallery: posts only get an image when the plan names a photo that exists as
an Asset. This module turns either a listing page (scraped for its gallery) or a list of
direct image URLs into Asset rows, so the PHOTO INDEX the engine reads is built from the
agent's real photos.

Extraction is a pure function (``extract_image_urls``) so it is testable without the
network; only ``discover`` and ``import_from_urls`` touch HTTP.
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import urllib.parse
import uuid
from datetime import datetime
from urllib.parse import urljoin, urlparse, urlsplit

import httpx

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
CONTENT_TYPE_EXT = {
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/pjpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}
MAX_BYTES = 12 * 1024 * 1024
# A 14-day campaign wants a different photo most days, and the importer used to stop at ten,
# silently discarding the rest of the gallery. Twenty leaves room for a longer run.
DEFAULT_LIMIT = 60
# A listing's gallery is routinely 40-60 photos (this MLS's own share link for one Redding home
# carries 52). 20 was a storage guess from the first MVP and silently dropped two thirds of a
# gallery; the ceiling stays a guard against a page that lists a whole office's inventory, not a
# limit on one listing.
MAX_LIMIT = 80

_JPEG_END = b"\xff\xd9"
_PNG_END = b"IEND\xaeB`\x82"


def _strip_tail_padding(raw: bytes) -> bytes:
    """Drop the NUL padding some upload paths append after a finished image.

    37 photos in one production gallery arrived as a complete JPEG followed by up to a
    megabyte of 0x00 bytes, padded out to exactly 3 MiB. The picture is whole — the padding is
    dead weight that makes every later check (end marker, size, serving) look wrong. Trim it.
    """
    end = len(raw)
    while end > 0 and raw[end - 1] == 0:
        end -= 1
    return raw if end == len(raw) else raw[:end]


def clean_image_bytes(data) -> bytes:
    """The photo's real bytes: NUL padding removed, everything else untouched."""
    if not data:
        return b""
    try:
        raw = data if isinstance(data, (bytes, bytearray)) else bytes(data)
    except (TypeError, ValueError):
        return b""
    return _strip_tail_padding(bytes(raw))


def looks_incomplete(data, filename: str = "") -> bool:
    """True when the file has no end-of-image marker: a partial copy, not a usable photo.

    A copy that stops mid-scan is useless — the vision model cannot read it and a published
    post shows a broken picture. Padding is not damage, so NUL bytes after the end marker are
    trimmed before the check.
    """
    if not data:
        return False
    ext = (filename or "").rsplit(".", 1)[-1].lower() if "." in (filename or "") else ""
    raw = clean_image_bytes(data)
    if not raw:
        return False
    if ext in ("jpg", "jpeg"):
        if not raw.startswith(b"\xff\xd8"):
            return True
        return not raw.endswith(_JPEG_END)
    if ext == "png":
        return _PNG_END not in raw[-16:]
    return False


USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)

# Chrome on a listing page is full of furniture: logos, sprites, agent headshots and
# tracking pixels all sit next to the photos. Drop the obvious ones by name.
_SKIP_HINTS = (
    "logo", "sprite", "favicon", "avatar", "headshot", "badge", "placeholder",
    "spacer", "pixel", "icon-", "/icons/", "1x1", "transparent", "loading",
    # MLS and portal chrome that a rendered page carries next to the property photos:
    # flexmls in particular ships its own "no image available" card and an error glyph,
    # and either one would be picked as photo one if it came first.
    "no_img_available", "no-image-available", "noimage", "flexmls-ui", "/assets/error",
    "error-", "coming-soon", "default-photo", "placeholder-", "apple-touch-icon",
    "/css/", "/fonts/", "sprite-", "-logo.", "_logo.",
    # An app icon on a portal page is named with underscores, not the hyphen the older
    # hints caught: Trulia's "blue_heart_trulia_app_icon_small.png" became photo one.
    "icon_", "_icon", "app_icon", "appicon",
)

_META_RE = re.compile(r"<meta\b[^>]*>", re.I)
_ATTR_RE = re.compile(r"""([a-zA-Z_:][-a-zA-Z0-9_:.]*)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^\s"'>]+))""")
_IMG_RE = re.compile(r"<img\b[^>]*>", re.I)
_META_IMAGE_RE = re.compile(r"og:image|twitter:image", re.I)
_LD_RE = re.compile(r'<script[^>]+type\s*=\s*["\']application/ld\+json["\'][^>]*>(.*?)</script>', re.I | re.S)


def _attrs(tag: str) -> dict:
    out = {}
    for m in _ATTR_RE.finditer(tag):
        name = m.group(1).lower()
        value = next((g for g in (m.group(2), m.group(3), m.group(4)) if g is not None), "")
        out[name] = value.strip()
    return out


def _srcset_best(srcset: str) -> str:
    """Largest candidate in a srcset ("a.jpg 1x, b.jpg 2x" / "a.jpg 640w, b.jpg 1280w")."""
    best, best_score = "", -1.0
    for part in (srcset or "").split(","):
        bits = part.strip().split()
        if not bits:
            continue
        url = bits[0]
        score = 1.0
        if len(bits) > 1:
            m = re.match(r"([0-9.]+)([wx])", bits[1])
            if m:
                score = float(m.group(1))
        if score > best_score:
            best, best_score = url, score
    return best


def _looks_like_image(url: str) -> bool:
    if not url or url.startswith("data:"):
        return False
    path = urlparse(url).path.lower()
    if os.path.splitext(path)[1] in IMAGE_EXTS:
        return True
    # Many MLS/CDN galleries carry the format in the query string instead of the path.
    return bool(re.search(r"\.(jpe?g|png|webp)(?:$|[?&])", url.lower()))


def _is_furniture(url: str) -> bool:
    low = url.lower()
    return any(hint in low for hint in _SKIP_HINTS)


def _walk_json_images(node, out: list) -> None:
    if isinstance(node, str):
        return
    if isinstance(node, list):
        for item in node:
            _walk_json_images(item, out)
        return
    if not isinstance(node, dict):
        return
    for key, value in node.items():
        if key.lower() in ("image", "images", "thumbnailurl", "contenturl") and value:
            if isinstance(value, str):
                out.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        out.append(item)
                    elif isinstance(item, dict):
                        for k in ("url", "contentUrl", "@id"):
                            if isinstance(item.get(k), str):
                                out.append(item[k])
            elif isinstance(value, dict):
                for k in ("url", "contentUrl", "@id"):
                    if isinstance(value.get(k), str):
                        out.append(value[k])
        else:
            _walk_json_images(value, out)


_SCRIPT_BLOCK_RE = re.compile(r"<script\b[^>]*>(.*?)</script>", re.I | re.S)
_SCRIPT_LD_RE = re.compile(r"type\s*=\s*[\"']application/ld\+json", re.I)
_SCRIPT_URL_RE = re.compile(
    r"https?://[^\s\"'<>\\]+?\.(?:jpe?g|png|webp)(?:\?[^\s\"'<>\\]*)?", re.I)


def _script_image_urls(html: str) -> list[str]:
    """Image URLs sitting in the page's own inline JSON, which is where MLS galleries live.

    An MLS / IDX detail page renders its photo viewer from a data blob: the address, the
    price and ``"photos": [...]`` are all in one <script>. Nothing in <img> tags exposes
    more than the hero, so a login-walled MLS link used to import exactly one photo. The
    blob is JSON with escaped slashes (``https:\\/\\/cdn...\\/1-o.jpg``), so both spellings
    are normalised before the URLs are read out.
    """
    out: list[str] = []
    for match in _SCRIPT_BLOCK_RE.finditer(html or ""):
        block = match.group(0)
        if _SCRIPT_LD_RE.search(block[:600]):
            continue                      # structured data is already read, in order
        text = match.group(1)
        low = text.lower()
        if not any(token in low for token in (".jpg", ".jpeg", ".png", ".webp")):
            continue
        text = text.replace("\\/", "/").replace("\\u002F", "/").replace("\\u002f", "/")
        out.extend(_SCRIPT_URL_RE.findall(text))
    return out


def _gallery_group(urls: list[str]) -> list[str]:
    """Keep the URLs that belong to one gallery: same host, same folder, two or more.

    A portal page carries other listings' thumbnails and ad images in the same JSON. The
    house's own photos share a folder (``.../bigphoto/848/26-2848_7_K.jpg``), so keeping
    the largest such group is the difference between the gallery and a stranger's house.
    """
    groups: dict[tuple[str, str], list[str]] = {}
    for url in urls:
        parsed = urlparse(url)
        groups.setdefault((parsed.netloc.lower(), os.path.dirname(parsed.path)), []).append(url)
    if not groups:
        return []
    best = max(groups.values(), key=len)
    return best if len(best) >= 2 else urls


# ---------------------------------------------------------------------------
# The second URL behind a public listing link.
#
# An MLS "public link" is a shop window: one hero photo, a few facts, and a "view" control
# that goes somewhere else — an iframe, a viewer app on another host, or a JSON blob holding
# the listing's own URL. The gallery is on that second page, not on the shop window, so a
# single fetch of the public link can only ever return one image. These helpers read the
# pointers out of the page and hand them to the caller, which then fetches them properly.
# ---------------------------------------------------------------------------

_IFRAME_RE = re.compile(r"<iframe\b[^>]*>", re.I)
_META_REFRESH_RE = re.compile(
    r"<meta[^>]+http-equiv=[\"']?refresh[\"']?[^>]*content=[\"'][^\"']*?url=([^\"'>\s]+)", re.I)
_JS_REDIRECT_RE = re.compile(
    r"(?:window\.)?location(?:\.href)?\s*(?:=|\.replace\(|\.assign\()\s*[\"'](https?://[^\"']+|/[^\"']+)[\"']", re.I)
_LINK_TAG_RE = re.compile(r"<link\b[^>]*>", re.I)
# Keys a viewer/IDX page uses to name the real listing page. The value may sit in an inline
# JSON blob, in a data-* attribute, or in a JS object — the pattern does not care which.
_SECOND_URL_KEY_RE = re.compile(
    r"[\"'](?:(?:listing|detail|public|share|viewer|embed|gallery|media|photos?|virtualTour|tour)?"
    r"(?:url|link|href))[\"']\s*:\s*[\"'](https?://[^\"'\\]{10,600}|/[^\"'\\]{3,600})[\"']", re.I)
_GALLERY_ANCHOR_RE = re.compile(r"<a\b[^>]*>", re.I)
_MD_LINK_RE = re.compile(r"\[([^\]\n]{1,80})\]\((https?://[^)\s]{8,500})\)")


def _page_key(url: str) -> str:
    """A URL reduced to host+path+query so tracking variants of one page collapse together."""
    parts = urlsplit(url)
    return f"{parts.netloc.lower()}{parts.path.rstrip('/')}{('?' + parts.query) if parts.query else ''}"


def hidden_second_urls(html: str, page_url: str, limit: int = 3) -> list[str]:
    """The URLs a public listing page points at for the real listing view, best first.

    Reads, in order of trust: the page's own structured pointer (canonical / og:url when it
    names a different page), an inline JSON "…Url" field, a meta refresh, a JS
    ``location`` assignment, an iframe, then an anchor that says photos/gallery/view.

    Everything comes back absolute, de-duplicated, and never the page itself. Image URLs are
    excluded — they are not a second page. This is deliberately generic: MLS vendors ship a
    new skin every few years, and a pointer is a pointer whichever attribute carries it.
    """
    html = html or ""
    page_key = _page_key(page_url)
    out: list[str] = []
    seen = {page_key}

    def offer(raw: str) -> None:
        if not raw:
            return
        raw = raw.strip().replace("&amp;", "&")
        url = urljoin(page_url, raw)
        if not url.startswith(("http://", "https://")):
            return
        if _looks_like_image(url) or url.lower().endswith((".jpg", ".jpeg", ".png", ".webp")):
            return
        key = _page_key(url)
        if key in seen:
            return
        seen.add(key)
        out.append(url)

    for tag in _LINK_TAG_RE.findall(html):
        a = _attrs(tag)
        if (a.get("rel") or "").lower() in ("canonical", "alternate") and a.get("href"):
            offer(a["href"])

    for tag in _META_RE.findall(html):
        a = _attrs(tag)
        key = (a.get("property") or a.get("name") or "").lower()
        if key in ("og:url", "twitter:url") and a.get("content"):
            offer(a["content"])

    for match in _META_REFRESH_RE.findall(html):
        offer(match)

    for raw in _SECOND_URL_KEY_RE.findall(html):
        offer(raw)

    for raw in _JS_REDIRECT_RE.findall(html):
        offer(raw)

    for tag in _IFRAME_RE.findall(html):
        a = _attrs(tag)
        for key in ("src", "data-src"):
            if a.get(key):
                offer(a[key])

    for tag in _GALLERY_ANCHOR_RE.findall(html):
        a = _attrs(tag)
        href = a.get("href") or ""
        label = (a.get("title") or a.get("aria-label") or "").lower()
        if not href:
            continue
        if re.search(r"(photo|gallery|media|picture|tour|view)", href, re.I) or \
           re.search(r"(photo|gallery|media|picture|tour)", label):
            offer(href)

    # A page pulled through a reader (r.jina.ai and friends) comes back as markdown, so its
    # pointer arrives as [View all 52 photos](https://...) and the tag scan above never sees
    # it. Same intent, different skin - read the label the way the anchor scan reads title.
    for label, href in _MD_LINK_RE.findall(html):
        if re.search(r"(photo|gallery|media|picture|tour|slideshow|permalink|\bview all\b)", label, re.I) or \
           re.search(r"(photos?|gallery|media|slideshow)(/|$|\?|=)", href, re.I):
            offer(href)

    return out[:limit]


_SPARK_URL_RE = re.compile(
    r"https?://cdn\d*(?:\.resize|\.photos)?\.sparkplatform\.com/[^\s\"'<>\\]+?(\d{20,})(?:-o)?\.jpg", re.I)
_SPARK_SIZE_RE = re.compile(r"/(\d{3,5})x(\d{3,5})/")


def _spark_id(url: str) -> tuple[str, int]:
    """(media id, pixel width) for a Spark Platform photo URL, or ('', 0)."""
    m = _SPARK_URL_RE.search(url or "")
    if not m:
        return "", 0
    size = _SPARK_SIZE_RE.search(url)
    return m.group(1), int(size.group(1)) if size else 0


def spark_photo_urls(html: str, limit: int = DEFAULT_LIMIT) -> list[str]:
    """One Flexmls listing's gallery out of a Spark Platform page.

    A flexmls detail page is not one gallery. It carries the listing's own photos, the same
    photos again at 640x480, and a carousel of *other* active listings - so a naive read of
    every sparkplatform URL imports somebody else's house next to yours. Two facts sort it
    out: Spark media ids are timestamped (``20260730022520745558000000`` is 30 Jul 2026
    02:25:20 + a counter), and the photos of one listing are uploaded in one sitting, so they
    land minutes apart. Keep the largest copy of each id, then keep the biggest cluster of
    ids that sit within half an hour of each other - that cluster is the gallery.
    """
    best: dict[str, tuple[int, str]] = {}
    order: list[str] = []
    for m in _SPARK_URL_RE.finditer(html or ""):
        media_id, width = _spark_id(m.group(0))
        if not media_id:
            continue
        if media_id not in best:
            order.append(media_id)
            best[media_id] = (width, m.group(0))
        elif width > best[media_id][0]:
            best[media_id] = (width, m.group(0))
    if not best:
        return []

    def stamp(media_id: str) -> float:
        try:
            return datetime.strptime(media_id[:14], "%Y%m%d%H%M%S").timestamp()
        except ValueError:
            return 0.0

    clusters: list[list[str]] = []
    for media_id in sorted(order, key=stamp):
        when = stamp(media_id)
        if clusters and when - stamp(clusters[-1][-1]) <= 1800:
            clusters[-1].append(media_id)
        else:
            clusters.append([media_id])
    gallery = max(clusters, key=len)
    return [best[i][1] for i in gallery][:limit]


def extract_image_urls(html: str, base_url: str, limit: int = DEFAULT_LIMIT) -> list[str]:
    """Gallery URLs from a listing page, best first, absolute and de-duplicated.

    Order of trust: og:image (the page's own hero and the most reliable single image),
    the MLS gallery in structured data, then <img>/<picture> tags in document order. Logos,
    icons and tracking pixels are dropped by name, and anything that is not a raster image
    is skipped.

    This is the generic path. Movoto and Trulia bury nothing useful in meta tags — on a
    52-photo Movoto listing every meta/tag heuristic together found 3 URLs — so
    ``discover`` prefers the site adapters below and only lands here for other hosts.
    """
    html = html or ""
    found: list[str] = []

    for tag in _META_RE.findall(html):
        a = _attrs(tag)
        key = (a.get("property") or a.get("name") or "").lower()
        if key in ("og:image", "og:image:secure_url", "twitter:image", "twitter:image:src"):
            if a.get("content"):
                found.append(a["content"])

    for block in _LD_RE.findall(html):
        try:
            data = json.loads(block.strip())
        except (ValueError, TypeError):
            continue
        _walk_json_images(data, found)

    # A gallery rendered from an inline data blob (MLS / IDX pages) is invisible to the tags.
    found.extend(_gallery_group(_script_image_urls(html)))

    for tag in _IMG_RE.findall(html):
        a = _attrs(tag)
        for key in ("src", "data-src", "data-lazy-src", "data-original", "data-image"):
            if a.get(key):
                found.append(a[key])
                break
        if a.get("srcset"):
            best = _srcset_best(a["srcset"])
            if best:
                found.append(best)

    out: list[str] = []
    seen: set[str] = set()
    for raw in found:
        url = urljoin(base_url, raw.strip())
        if not url.startswith(("http://", "https://")):
            continue
        if not _looks_like_image(url) or _is_furniture(url):
            continue
        if url in seen:
            continue
        seen.add(url)
        out.append(url)
        if len(out) >= max(1, int(limit)):
            break
    return out


# ---------------------------------------------------------------------------
# Site adapters.
#
# Listing galleries are not in og:image or <img> tags — they are in inline JSON. Movoto
# keeps a `__INITIAL_STATE__` blob, Trulia publishes JSON-LD. Reading that JSON is the
# difference between 3 photos and all of them, so each site gets an explicit parser and a
# testable pure function.
# ---------------------------------------------------------------------------

_INITIAL_STATE_RE = re.compile(
    r'<script[^>]*id=["\']__INITIAL_STATE__["\'][^>]*>(.*?)</script>', re.I | re.S)
_NEXT_DATA_RE = re.compile(
    r'<script[^>]*id=["\']__NEXT_DATA__["\'][^>]*>(.*?)</script>', re.I | re.S)
_ZILLOW_HASH_RE = re.compile(r"zillowstatic/fp/([a-z0-9]+)", re.I)


def _json_blobs(html: str) -> list:
    out = []
    for block in _LD_RE.findall(html or ""):
        try:
            out.append(json.loads(block.strip()))
        except (ValueError, TypeError):
            continue
    return out


def _initial_state(html: str) -> dict:
    m = _INITIAL_STATE_RE.search(html or "")
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def _next_data(html: str) -> dict:
    """The Next.js props blob Trulia (and every other modern listing site) renders from."""
    m = _NEXT_DATA_RE.search(html or "")
    if not m:
        return {}
    try:
        data = json.loads(m.group(1))
    except (ValueError, TypeError):
        return {}
    return data if isinstance(data, dict) else {}


def movoto_photo_urls(html: str, size: str = "l") -> list[str]:
    """Every gallery photo on a Movoto detail page, in the order the listing shows them.

    Movoto's size suffixes: "" original (2048px), "_l" 1920px, "_r" 960px, "_p" 480px
    thumbnail. "l" is the bandwidth/quality sweet spot; "p" — which is what the card
    thumbnail field holds — is a tile, not a photo.
    """
    state = _initial_state(html)
    page = state.get("pageData") or {}
    out: list[str] = []
    for category in page.get("categorizedPhotos") or []:
        for photo in (category or {}).get("photos") or []:
            url = (photo or {}).get("url")
            if not isinstance(url, str):
                continue
            suffix = ((photo.get("images") or {}).get(size) or "")
            out.append(url.replace(".webp", suffix) if suffix and url.endswith(".webp") else url)
    return list(dict.fromkeys(u for u in out if _looks_like_image(u)))


def movoto_listings(html: str) -> list[dict]:
    """The listings on a Movoto city page (price, beds, baths, sqft, detail path)."""
    page = (_initial_state(html).get("pageData") or {})
    rows = []
    for item in page.get("listings") or []:
        path = (item or {}).get("path")
        if not isinstance(path, str):
            continue
        rows.append({
            "address": ((item.get("geo") or {}).get("address") or "").strip(),
            "city": (item.get("geo") or {}).get("city"),
            "zip": (item.get("geo") or {}).get("zipcode"),
            "price": item.get("listPrice"), "beds": item.get("bed"), "baths": item.get("bath"),
            "sqft": item.get("sqftTotal"), "photo_count": item.get("photoCount"),
            "url": urljoin("https://www.movoto.com/", path),
        })
    return rows


def trulia_photo_urls(html: str, full_res: bool = True) -> list[str]:
    """Trulia gallery photos, upgraded to Zillow's CDN original when possible.

    Trulia is a Next.js app: the gallery is ``props.homeDetails.media.photos[].url.large``
    inside ``__NEXT_DATA__`` (JSON-LD carries only one hero image, so it is the fallback).
    Photos are served at 1024px from ``/pictures/thumbs_5/zillowstatic/fp/<hash>-full.jpg``;
    the same hash on ``photos.zillowstatic.com`` returns the 3000×2250 original with no
    Referer required, and Trulia's robots.txt explicitly allows the thumbs path.
    """
    urls: list[str] = []

    data = _next_data(html)
    if data:
        home = ((data.get("props") or {}).get("homeDetails") or {})
        media = home.get("media") or {}
        for photo in media.get("photos") or []:
            url = (photo or {}).get("url") if isinstance(photo, dict) else None
            if isinstance(url, dict):
                urls.append(url.get("large") or url.get("thumbnail") or "")
            elif isinstance(url, str):
                urls.append(url)

    found: list[str] = []
    for blob in _json_blobs(html):
        _walk_json_images(blob, found)
    urls.extend(found)

    out: list[str] = []
    for url in urls:
        if not url or _is_furniture(url):
            continue
        m = _ZILLOW_HASH_RE.search(url)
        if m and full_res:
            out.append(f"https://photos.zillowstatic.com/fp/{m.group(1)}-full.jpg")
        elif _looks_like_image(url):
            out.append(url)
    return list(dict.fromkeys(out))


def trulia_listings(html: str) -> list[dict]:
    """Listings on a Trulia city page, taken from JSON-LD (the page has no listing links)."""
    rows: list[dict] = []

    def visit(node):
        if isinstance(node, list):
            for item in node:
                visit(item)
        elif isinstance(node, dict):
            offers = node.get("offers")
            offer = offers[0] if isinstance(offers, list) and offers else offers
            url = (offer or {}).get("url") if isinstance(offer, dict) else None
            if isinstance(url, str) and "/home/" in url:
                offered = node.get("itemOffered") if isinstance(node.get("itemOffered"), dict) else node
                rows.append({
                    "url": url,
                    "price": (offer or {}).get("price"),
                    "beds": offered.get("numberOfBedrooms"),
                    "baths": offered.get("numberOfBathroomsTotal"),
                    "sqft": ((offered.get("floorSize") or {}).get("value")
                             if isinstance(offered.get("floorSize"), dict) else None),
                    "address": ((offered.get("address") or {}).get("streetAddress")
                                if isinstance(offered.get("address"), dict) else None),
                })
            for value in node.values():
                visit(value)

    for blob in _json_blobs(html):
        visit(blob)
    seen, out = set(), []
    for row in rows:
        if row["url"] in seen:
            continue
        seen.add(row["url"])
        out.append(row)
    return out


def _street_tokens(text: str) -> list[str]:
    return [t for t in re.split(r"[^a-z0-9]+", (text or "").lower()) if t]


def match_listing(rows: list[dict], address: str = "", zipcode: str = "") -> dict | None:
    """Find the listing for the same property as ``address`` ('1234 Elm St, Redding, CA').

    Matches on the house number plus at least two street words, in either the row's own
    address or its URL slug — that is what lets a Zillow link be re-resolved on Trulia,
    where 'St' and 'Street' must still be the same house.
    """
    tokens = _street_tokens(address)
    if not tokens:
        return None
    number = tokens[0] if tokens[0].isdigit() else ""
    street = tokens[1:4]
    if not number and len(street) < 2:
        return None
    want_zip = (zipcode or "").strip()

    for row in rows:
        address_tokens = set(_street_tokens(row.get("address") or ""))
        slug = re.sub(r"[^a-z0-9]+", "-", (row.get("url") or "").lower())
        has_number = (number and (number in address_tokens or number in slug)) if number else True
        hits = sum(1 for t in street if t in address_tokens or t in slug)
        if has_number and hits >= min(2, len(street) or 2):
            if want_zip and want_zip not in slug and want_zip not in (row.get("address") or ""):
                continue
            return row
    return None


def address_from_listing_url(url: str) -> tuple[str, str, str]:
    """(address, state, zip) guessed from a listing URL, for the Trulia fallback."""
    path = urlparse(url).path
    slug = path.strip("/").split("/")[-2] if path.strip("/").count("/") >= 1 else path.strip("/")
    slug = slug.replace("_zpid", "")
    parts = [p for p in slug.split("-") if p]
    address = " ".join(parts[:4])
    state = next((p for p in parts if re.fullmatch(r"[A-Z]{2}", p)), "")
    zipcode = next((p for p in parts if re.fullmatch(r"\d{5}", p)), "")
    return address, state, zipcode


def guess_ext(url: str, content_type: str = "") -> str:
    ctype = (content_type or "").split(";")[0].strip().lower()
    if ctype in CONTENT_TYPE_EXT:
        return CONTENT_TYPE_EXT[ctype]
    ext = os.path.splitext(urlparse(url).path)[1].lower()
    if ext in IMAGE_EXTS:
        return ".jpg" if ext == ".jpeg" else ext
    return ""


def source_name(url: str, ext: str) -> str:
    """A name a human would recognise in the photo index ('front-of-house.jpg')."""
    stem = os.path.splitext(os.path.basename(urlparse(url).path))[0]
    stem = re.sub(r"[^A-Za-z0-9._-]+", "-", stem).strip("-")
    return (stem or "listing-photo") + ext


def _client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        follow_redirects=True,
        timeout=httpx.Timeout(30.0, connect=15.0),
        headers={"User-Agent": USER_AGENT, "Accept": "text/html,image/*,*/*"},
    )


_CHROME_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}


def _host(url: str) -> str:
    host = (urlparse(url).hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


_STREET_SUFFIX_RE = re.compile(
    r"\b(st|street|ave|avenue|rd|road|dr|drive|ln|lane|ct|court|way|blvd|boulevard|pl|place|"
    r"ter|terrace|hwy|highway|loop|cir|circle|pkwy|parkway|trl|trail|sq|square|pt|point)\b",
    re.I)
_STATE_ZIP_RE = re.compile(r"\b([A-Z]{2})\b\s*(\d{5}(?:-\d{4})?)?\s*$")


def parse_address(text: str) -> tuple[str, str, str, str]:
    """(street, city, state, zip) from however an owner typed the address.

    Two shapes reach this function and only one of them used to work:

        892 Coggins St, Redding, CA 96003   -> commas, the form hint
        892 Coggins Street Redding CA       -> what the campaign actually held

    The Trulia fallback needs the city and state, and it was reading them out of a
    comma pattern; an address without commas answered "no city", the fallback was
    skipped without a word, and an MLS link that exposes one hero photo imported one
    photo. So the parse no longer depends on punctuation.
    """
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return "", "", "", ""
    parts = [p.strip() for p in text.split(",") if p.strip()]
    state, zipcode = "", ""
    tail = parts[-1] if parts else text
    m = _STATE_ZIP_RE.search(tail)
    if m:
        state, zipcode = m.group(1), m.group(2) or ""
        rest = tail[:m.start()].strip(" ,")
        parts = parts[:-1] + ([rest] if rest else [])

    if len(parts) >= 2:
        street, city = parts[0], parts[-1]
    else:
        tokens = text.split()
        if zipcode and re.fullmatch(r"\d{5}(?:-\d{4})?", tokens[-1]):
            tokens = tokens[:-1]
        if state and tokens and tokens[-1].upper() == state:
            tokens = tokens[:-1]
        city_tokens: list[str] = []
        while tokens and len(city_tokens) < 3:
            word = tokens[-1]
            # A street suffix means everything left is the street, not more city.
            if _STREET_SUFFIX_RE.fullmatch(word):
                break
            city_tokens.insert(0, tokens.pop())
            if len(city_tokens) == 1:
                break
        street, city = " ".join(tokens), " ".join(city_tokens)
    return street, re.sub(r"\s+", " ", city).strip(), state, zipcode


def _city_candidates(address: str, state: str) -> list[str]:
    """City page slugs to try, most likely first ('Redding', then 'rancho-cordova')."""
    parts = [p.strip() for p in (address or "").split(",") if p.strip()]
    if len(parts) >= 2:
        spelled = re.sub(r"[^A-Za-z ]+", "", parts[-1]).strip()
        return [spelled.replace(" ", "-")] if spelled else []
    tokens = [t for t in re.split(r"[^A-Za-z0-9]+", address or "") if t]
    if state and tokens and tokens[-1].upper() == state:
        tokens = tokens[:-1]
    out: list[str] = []
    for size in (1, 2):
        if len(tokens) <= size:
            break
        words = tokens[-size:]
        if any(_STREET_SUFFIX_RE.fullmatch(w) or w.isdigit() for w in words):
            continue
        out.append(" ".join(words))
    return out


def _trulia_city_urls(address: str, zipcode: str) -> list[str]:
    """Candidate Trulia city pages for an address, whatever punctuation it arrived with."""
    _, _, state, _ = parse_address(address)
    if not state:
        m = re.search(r"\b([A-Z]{2})\b", address or "")
        state = m.group(1) if m else ""
    if not state:
        return []
    return [f"https://www.trulia.com/{state}/{slug}/" for slug in _city_candidates(address, state)]


def _trulia_city_url(address: str, zipcode: str) -> str:
    """Best guess at a Trulia city page for an address ('1234 Elm St, Redding, CA')."""
    urls = _trulia_city_urls(address, zipcode)
    return urls[0] if urls else ""


READER_BASE = "https://r.jina.ai/"          # renders the page on their infrastructure
READER_TIMEOUT = 90.0

# Words that only appear on a wall, never on a listing. MLS portals (Flexmls, Matrix) and the
# big consumer sites answer a bot with "200 OK" and a few kilobytes of JavaScript that then
# asks for a challenge — so status alone says nothing, and treating it as success meant the
# reader fallback below was never tried on exactly the pages that need it.
_WALL_MARKERS = (
    "client challenge",
    "cf_chl_opt",
    "just a moment",
    "enable javascript and cookies to continue",
    "javascript is disabled in your browser",
    "please enable javascript to proceed",
    "attention required! | cloudflare",
    "checking your browser before accessing",
    "are you a robot",
    "px-captcha",
    "captcha-delivery",
    "request unsuccessful. incapsula",
    "ddos protection by",
)


def _looks_like_a_wall(html: str) -> bool:
    """True when this is a challenge/consent shell rather than the page that was asked for."""
    if not html:
        return False
    low = html[:4000].lower()
    if any(marker in low for marker in _WALL_MARKERS):
        return True
    # A shell with no content: short, scripted, and carrying no picture of a property at all.
    # A short page that is nonetheless full of listing data — JSON-LD, a __NEXT_DATA__ blob, a
    # gallery of .jpg URLs — is a real page in a thin wrapper, not a wall, and must not be
    # thrown away.
    _DATA_HINTS = ("application/ld+json", "__next_data__", "__initial_state__", '"photos"',
                   ".jpg", ".jpeg", ".png", ".webp")
    if len(html) < 12000 and not _META_IMAGE_RE.search(html) and html.count("<img") == 0:
        if "<script" in low and not any(hint in html.lower() for hint in _DATA_HINTS):
            return True
    return False


async def _fetch_html(client: httpx.AsyncClient, url: str, trace: list | None = None,
                      force_reader: bool = False, reader_format: str = "html") -> str:
    """The page's HTML, direct if the site allows it, otherwise through a hosted reader.

    Zillow, Realtor, Redfin, Homes.com, Movoto and Trulia all answer 403 to a datacenter IP
    (Render is one) while answering 200 to a home connection — so a direct fetch works in
    local development and fails in production, which is the worst possible split. Flexmls and
    Matrix go further and answer 200 with a challenge shell, which is why a direct answer is
    checked for a wall before it is believed. The reader fetches from its own browser fleet
    and returns the rendered HTML, scripts and all, so the same parsers run on both.
    JINA_API_KEY raises the reader's rate limit when set.
    """
    def note(outcome):
        if trace is not None:
            trace.append({"url": url, "outcome": outcome})

    if not force_reader:
        try:
            resp = await client.get(url, headers=_CHROME_HEADERS)
            note(resp.status_code)
            if resp.status_code == 200 and len(resp.text) > 2000:
                if not _looks_like_a_wall(resp.text):
                    return resp.text
                note("wall")
        except httpx.HTTPError as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            note(status or exc.__class__.__name__)

    headers = dict(_CHROME_HEADERS)
    if reader_format == "html":
        headers["X-Respond-With"] = "html"
    # The reader keeps a snapshot of every page it has ever rendered, and for a listing it
    # captured while the page was still a challenge shell that snapshot is empty (247 bytes:
    # a title and nothing else). A cached empty page is worse than a miss because it looks
    # like an answer - it is how a 52-photo Flexmls share link imported one photo.
    headers["X-No-Cache"] = "true"
    # Their renderer gives up early and answers 200 with a few hundred bytes of nothing when
    # it is busy, so ask it to wait for the page instead of snapshotting the wait screen.
    headers["X-Timeout"] = "60"
    key = os.getenv("JINA_API_KEY")
    if key:
        headers["Authorization"] = f"Bearer {key}"
    try:
        reader = await client.get(READER_BASE + url, headers=headers, timeout=READER_TIMEOUT)
        note("reader:%s" % reader.status_code)
        if reader.status_code == 200:
            return reader.text
    except httpx.HTTPError as exc:
        note("reader:%s" % exc.__class__.__name__)
    return ""


async def _photos_from_second_pages(client: httpx.AsyncClient, urls: list[str], limit: int,
                                   trace: list | None) -> list[str]:
    """Photos found by following a public listing page's own pointer to the real listing.

    One extra hop is allowed, not a crawl: a shop window often points at another shop
    window (``share`` -> ``viewer`` -> gallery). Two hops covers the MLS layouts seen so far
    and keeps a wrong guess from turning into a fetch storm.
    """
    out: list[str] = []
    for target in urls:
        html = await _fetch_html(client, target, trace)
        if not html:
            continue
        host = _host(target)
        if "trulia.com" in host:
            found = trulia_photo_urls(html, full_res=False)
        elif "movoto.com" in host:
            found = movoto_photo_urls(html)
        else:
            found = extract_image_urls(html, target, limit=limit)
        if len(found) < 4:
            for deeper in hidden_second_urls(html, target, limit=1):
                page = await _fetch_html(client, deeper, trace)
                if not page:
                    continue
                more = extract_image_urls(page, deeper, limit=limit)
                for u in more:
                    if u not in found:
                        found.append(u)
                if len(found) >= 4:
                    break
        for url in found:
            if url not in out:
                out.append(url)
        if len(out) >= limit:
            break
    return out[:limit]


async def _photos_on_page(client: httpx.AsyncClient, url: str, limit: int,
                          address: str, zipcode: str, trace: list | None) -> list[str]:
    html = await _fetch_html(client, url, trace)
    if not html:
        return []
    host = _host(url)

    if "movoto.com" in host:
        photos = movoto_photo_urls(html)
        if photos:
            return photos[:limit]
        match = match_listing(movoto_listings(html), address, zipcode)   # a city page
        if match:
            detail = await _fetch_html(client, match["url"], trace)
            return movoto_photo_urls(detail)[:limit] if detail else []

    if "trulia.com" in host:
        # 1024px thumbs, not the 3000px originals: a Facebook or Instagram post is 1080px
        # wide, so the original is ~8x the bytes for detail nobody sees, and on a free
        # database every campaign's gallery is stored as bytes.
        photos = trulia_photo_urls(html, full_res=False)
        if photos:
            return photos[:limit]

    spark_page = "sparkplatform" in html or "flexmls" in host
    photos = spark_photo_urls(html, limit=limit) if spark_page else []
    # One photo out of a Flexmls page is its hero, not a gallery: a real gallery is two or
    # more, and anything less means this HTML is the app's shell rather than the listing.
    if len(photos) >= 2:
        return photos[:limit]

    for url_ in extract_image_urls(html, url, limit=limit):
        if url_ not in photos:
            photos.append(url_)

    # Render's IP is handed a thin shell where a home connection gets the listing, and the
    # hosted reader that can see the page is flaky: the same URL came back as 349 bytes, then
    # 176 KB, then 247 bytes on three consecutive asks. So a walled MLS page is asked again
    # until a render actually carries a gallery, and a render that carries nothing is not an
    # answer. Markdown, not HTML: a Flexmls share link's 52 photos are in the text render,
    # while its HTML render is a shell holding the one hero image.
    if len(photos) < 4:
        for attempt in range(3):
            text = await _fetch_html(client, url, trace, force_reader=True, reader_format="markdown")
            if text:
                gallery = spark_photo_urls(text, limit=limit) if "sparkplatform" in text else []
                if len(gallery) >= 2:
                    return gallery[:limit]
                for url_ in extract_image_urls(text, url, limit=limit):
                    if url_ not in photos:
                        photos.append(url_)
            if len(photos) >= 4 or attempt == 2:
                break
            await asyncio.sleep(2)

    # A public MLS / IDX / share link is a shop window: the gallery lives one page deeper.
    # Follow the page's own pointer before giving up on it — that is where the photos are.
    if len(photos) < 4:
        for extra in await _photos_from_second_pages(
                client, hidden_second_urls(html, url), limit, trace):
            if extra not in photos:
                photos.append(extra)
            if len(photos) >= limit:
                break
    return photos[:limit]


def address_from_url(listing_url: str) -> str:
    """The street address a portal URL already spells out.

    zillow.com/homedetails/4422-Clay-St-Redding-CA-96003/15238205_zpid/
        -> 4422 Clay St, Redding, CA 96003
    redfin.com/CA/Redding/1354-Harpole-Rd-96002/home/139453215
        -> 1354 Harpole Rd, Redding, CA 96002
    realtor.com/realestateandhomes-detail/6495-Mojave-Ct_Anderson_CA_96007_M12345
        -> 6495 Mojave Ct, Anderson, CA 96007

    Every portal puts the address in the path because that is their SEO, and it is worth
    reading for one reason: the Trulia lookup is the route that survives a datacenter IP,
    and it needs an address to search for even when the campaign has none yet.
    """
    parts = [p for p in urllib.parse.urlparse(listing_url).path.split("/") if p]
    for part in parts:  # realtor.com: underscores
        m = re.match(r"^(\d{1,6}(?:-[A-Za-z0-9]+)+)_([A-Za-z][A-Za-z .]*(?:-[A-Za-z]+)*)_([A-Z]{2})_(\d{5})", part)
        if m:
            return (f"{m.group(1).replace('-', ' ')}, "
                    f"{m.group(2).replace('-', ' ')}, {m.group(3)} {m.group(4)}")
    for part in parts:  # zillow.com: street-city-state-zip
        m = re.match(r"^(\d{1,6}(?:-[A-Za-z0-9]+)+)-([A-Za-z][A-Za-z]*(?:-[A-Za-z]+)*)-([A-Z]{2})-(\d{5})$", part)
        if m:
            return (f"{m.group(1).replace('-', ' ')}, "
                    f"{m.group(2).replace('-', ' ')}, {m.group(3)} {m.group(4)}")
    for i, part in enumerate(parts):  # redfin.com: street-zip, city and state before it
        m = re.match(r"^(\d{1,6}(?:-[A-Za-z0-9]+)+)-(\d{5})$", part)
        if not m or i < 1:
            continue
        street, zipcode = m.group(1).replace('-', ' '), m.group(2)
        # /CA/Redding/1354-Harpole-Rd-96002/... puts the state two segments back;
        # /Redding-CA/1354-Harpole-Rd-96002/... puts it one back.
        if i >= 2 and re.fullmatch(r"[A-Z]{2}", parts[i - 2]):
            return f"{street}, {parts[i - 1].replace('-', ' ')}, {parts[i - 2]} {zipcode}"
        if re.fullmatch(r"[A-Z]{2}", parts[i - 1]):
            return f"{street}, {parts[i - 1]} {zipcode}"
    return ""


async def _trulia_by_address(client: httpx.AsyncClient, address: str, zipcode: str,
                             limit: int, trace: list | None) -> list[str]:
    """The same property on Trulia, found from the campaign's own address.

    The city page is a guess, so more than one spelling is tried ('Redding', then
    'rancho-cordova'); a page that yields listings but not this house means the guess was
    right and the property simply is not on Trulia, so it stops there instead of walking
    every candidate and burning a fetch each.
    """
    for city_url in _trulia_city_urls(address, zipcode):
        html = await _fetch_html(client, city_url, trace)
        rows = trulia_listings(html) if html else []
        match = match_listing(rows, address, zipcode) if rows else None
        if match:
            return await _photos_on_page(client, match["url"], limit, address, zipcode, trace)
        if rows:
            break
    return []


async def discover(listing_url: str, limit: int = DEFAULT_LIMIT, client: httpx.AsyncClient | None = None,
                   address: str = "", zipcode: str = "", trace: list | None = None) -> list[str]:
    """Gallery photo URLs for a listing, from whichever source can still serve them.

    Order of attempts:

      1. the page itself, parsed by its own adapter (Movoto ``__INITIAL_STATE__``,
         Trulia ``__NEXT_DATA__``) with a generic og:image/JSON-LD/<img> pass for other hosts;
      2. the same page through a hosted reader, which is what makes production work at all —
         every listing portal answers 403 to a datacenter IP;
      2b. the URL that page points at. An MLS / IDX "public link" shows one hero photo and
         puts the gallery behind an iframe, a viewer app or a JSON ``…Url`` field, so the
         page's own pointer is followed (one extra hop) before falling back;
      3. the same property on Trulia, found by the campaign's own address, because Trulia is
         the same inventory and its gallery survives the reader where Movoto's does not.

    Returns [] rather than raising when nothing works, so the caller can explain the
    options instead of surfacing an httpx status code. ``trace`` collects each URL tried
    with its outcome, which is the difference between a support answer and a shrug.
    """
    own = client is None
    client = client or _client()
    try:
        urls = await _photos_on_page(client, listing_url, limit, address, zipcode, trace)
        # A listing dashboard (Fotello, an MLS, a Drive folder) renders its gallery after a
        # sign-in, so the public HTML holds one hero image at most. A handful of photos is not
        # a gallery either: top it up from the address, which is the same inventory on Trulia.
        lookup = address or address_from_url(listing_url)
        # Engine 3: photos come from whichever source gives the best set. Short of a full
        # campaign's worth (14), the same home is looked up by address too and the bigger
        # gallery wins; a near-empty page (a hero shot) is topped up as before.
        if len(urls) < 14:
            if lookup:
                _, _, _, parsed_zip = parse_address(lookup)
                extra = await _trulia_by_address(client, lookup, zipcode or parsed_zip,
                                                limit, trace)
                if len(urls) >= 4 and len(extra) > len(urls):
                    if trace is not None:
                        trace.append({"url": "", "outcome": f"the address lookup had the bigger gallery "
                                                            f"({len(extra)} vs {len(urls)}): using it"})
                    urls = list(extra)
                elif len(urls) < 4:
                    for u in extra:
                        if u not in urls:
                            urls.append(u)
                        if len(urls) >= limit:
                            break
            elif trace is not None:
                # The campaign had no address and the link carried none either, so the one
                # route that survives a walled MLS page had nothing to look up. Say it, so
                # "only one photo came in" has a cause attached to it.
                trace.append({"url": "", "outcome": "no address to look the property up by"})
        return urls[:limit]
    finally:
        if own:
            await client.aclose()


async def import_from_urls(
    db,
    *,
    user_id: int,
    boost_id: int | None,
    urls: list[str],
    upload_dir: str,
    limit: int = DEFAULT_LIMIT,
    client: httpx.AsyncClient | None = None,
) -> dict:
    """Download image URLs into uploads/ and record one Asset per stored photo.

    Returns {'imported': n, 'skipped': [...], 'assets': [{'asset_id', 'url', 'name', 'bytes'}]}.
    A URL that 404s, is not an image, or is larger than MAX_BYTES is skipped with a reason
    instead of failing the batch — a gallery with one dead link should still import.
    """
    from app.db.session import Asset  # local import keeps this module import-light

    os.makedirs(upload_dir, exist_ok=True)
    own = client is None
    client = client or _client()
    imported: list[dict] = []
    skipped: list[dict] = []
    seen_urls: set[str] = set()
    try:
        rows = db.query(Asset).filter(Asset.boost_id == boost_id).all() if boost_id is not None else []
        existing = {(a.original_name or "").lower(): a for a in rows}
        for url in urls:
            if len(imported) >= max(1, int(limit)):
                break
            if url in seen_urls:
                continue
            seen_urls.add(url)

            try:
                resp = await client.get(url, headers={"Accept": "image/*"})
                resp.raise_for_status()
                content_type = resp.headers.get("content-type", "")
                ext = guess_ext(url, content_type)
                if not ext:
                    skipped.append({"url": url, "reason": f"not an image ({content_type or 'no content-type'})"})
                    continue
                data = resp.content
                if not data:
                    skipped.append({"url": url, "reason": "empty response"})
                    continue
                if len(data) > MAX_BYTES:
                    skipped.append({"url": url, "reason": f"too large ({len(data) // 1024} KB)"})
                    continue
            except httpx.HTTPError as exc:
                skipped.append({"url": url, "reason": f"download failed: {exc.__class__.__name__}"})
                continue

            name = source_name(url, ext)
            if name.lower() in existing:
                # Same photo as before. If its bytes were lost (an asset imported before images
                # were stored with the row, or a wiped disk), this is the chance to repair it.
                old = existing[name.lower()]
                if not getattr(old, "data", None):
                    old.data = data
                    old.content_type = content_type or None
                    db.commit()
                    imported.append({"asset_id": old.id, "url": old.url, "name": name,
                                     "bytes": len(data), "restored": True})
                else:
                    skipped.append({"url": url, "reason": "already imported"})
                continue
            filename = f"{uuid.uuid4().hex}{ext}"
            with open(os.path.join(upload_dir, filename), "wb") as fh:
                fh.write(data)
            asset = Asset(
                user_id=user_id,
                boost_id=boost_id,
                filename=filename,
                url=f"/uploads/{filename}",
                original_name=name,
                kind="photo",
                data=data,
                content_type=content_type or None,
            )
            db.add(asset)
            db.commit()
            db.refresh(asset)
            existing[name.lower()] = asset
            imported.append({"asset_id": asset.id, "url": asset.url, "name": name, "bytes": len(data)})
    finally:
        if own:
            await client.aclose()
    return {"imported": len(imported), "skipped": skipped, "assets": imported}
