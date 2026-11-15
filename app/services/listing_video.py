"""Finding the listing video, if the listing has one (Post Engine §6.6).

A listing page sometimes carries the tour the photographer already shot. When it does, the
first day's post should be that video rather than a designed still, and the ad runs as a single
video ad instead of a carousel (§6.6, Ad Engine §4). When it does not, the campaign is photo
posts and a carousel ad — which is the normal case, and the agent is told which one they got.

Only a direct, public MP4/MOV counts: Meta pulls the file itself from the URL, so a YouTube or
Vimeo embed cannot be posted natively, and a Matterport tour is a 3D walkthrough, not a video.
Resmara never downloads or stores the footage — it stores the URL.
"""
from __future__ import annotations

import re
from urllib.parse import urljoin, urlsplit

import httpx

USER_AGENT = "Mozilla/5.0 (compatible; Resmara/1.0; listing video check; support@resmara.com)"

# Instagram Reels' own limits (§6.6): 3 s to 15 min, 300 MB.
MAX_BYTES = 300 * 1024 * 1024
MIN_SECONDS = 3
MAX_SECONDS = 15 * 60

SKIP_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "matterport.com", "my.matterport.com",
              "facebook.com", "fb.watch")
VIDEO_EXT = (".mp4", ".mov", ".m4v")
TOUR_WORDS = ("virtual tour", "video tour", "tour", "walkthrough", "video")

_OG_VIDEO = re.compile(r'<meta[^>]+property=["\']og:video(?::url|:secure_url)?["\'][^>]+'
                       r'content=["\']([^"\']+)["\']', re.I)
_OG_VIDEO_ALT = re.compile(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+'
                           r'property=["\']og:video(?::url|:secure_url)?["\']', re.I)
_VIDEO_TAG = re.compile(r'<video[^>]*src=["\']([^"\']+)["\']', re.I)
_SOURCE_TAG = re.compile(r'<source[^>]*src=["\']([^"\']+)["\'][^>]*>', re.I)
_LINK_TAG = re.compile(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]{0,80})', re.I)


def _clean(url: str) -> str:
    """A canonical absolute URL with the tracking noise removed, or "" if it is not one."""
    url = (url or "").strip()
    if not url or url.startswith("data:") or url.startswith("blob:"):
        return ""
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return ""
    if any(skip in (parts.netloc or "").lower() for skip in SKIP_HOSTS):
        return ""
    return url


def _is_direct_video(url: str) -> bool:
    path = urlsplit(url).path.lower()
    return path.endswith(VIDEO_EXT)


def candidates(html: str, base_url: str) -> list[str]:
    """Every URL on the page that could be a direct video file, in the order they appear."""
    found: list[str] = []
    for pattern in (_OG_VIDEO, _OG_VIDEO_ALT, _VIDEO_TAG, _SOURCE_TAG):
        for match in pattern.finditer(html or ""):
            url = _clean(urljoin(base_url, match.group(1)))
            if url and _is_direct_video(url) and url not in found:
                found.append(url)
    return found


def tour_links(html: str, base_url: str) -> list[str]:
    """Pages one level away that look like the photographer's tour page (§6.6)."""
    links: list[str] = []
    for match in _LINK_TAG.finditer(html or ""):
        href, text = match.group(1), (match.group(2) or "")
        label = f"{href} {text}".lower()
        if not any(word in label for word in TOUR_WORDS):
            continue
        url = _clean(urljoin(base_url, href))
        if url and url not in links and url != base_url:
            links.append(url)
    return links[:3]


async def probe(url: str, *, timeout: int = 15) -> dict:
    """What Meta would find: a reachable, public, direct video file under 300 MB."""
    out = {"url": url, "ok": False, "detail": ""}
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                     headers={"User-Agent": USER_AGENT}) as client:
            resp = await client.head(url)
            if resp.status_code >= 400 or resp.status_code == 405:
                resp = await client.get(url, headers={"Range": "bytes=0-1023"})
    except Exception as exc:  # noqa: BLE001 - the reason is the answer
        out["detail"] = f"The video link could not be opened ({type(exc).__name__})."
        return out
    if resp.status_code >= 400:
        out["detail"] = f"The video link answered {resp.status_code}."
        return out
    ctype = (resp.headers.get("content-type") or "").lower()
    if ctype.startswith("text/html"):
        out["detail"] = ("That link is a page, not a video file. Meta needs a direct MP4 or "
                         "MOV address.")
        return out
    length = resp.headers.get("content-length")
    if length and length.isdigit() and int(length) > MAX_BYTES:
        out["detail"] = (f"The video is {int(length) // (1024 * 1024)} MB - Instagram Reels "
                         "accepts up to 300 MB.")
        return out
    out.update({"ok": True, "content_type": ctype or "video/*",
                "bytes": int(length) if length and length.isdigit() else None,
                "detail": "A listing video was found."})
    return out


async def find(url: str, *, timeout: int = 20) -> dict:
    """Look on the listing page, then one level into its tour links. Never raises."""
    result = {"video_url": None, "found": False, "detail": "", "tried": []}
    if not url:
        result["detail"] = "No listing link to look at."
        return result
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=True,
                                     headers={"User-Agent": USER_AGENT}) as client:
            page = await client.get(url)
            pages = [url] if page.status_code < 400 else []
            html_by_url = {url: page.text if pages else ""}
            for link in tour_links(html_by_url.get(url, ""), url):
                try:
                    sub = await client.get(link)
                except Exception:  # noqa: BLE001 - one bad tour link is not a failure
                    continue
                pages.append(link)
                html_by_url[link] = sub.text if sub.status_code < 400 else ""
    except Exception as exc:  # noqa: BLE001
        result["detail"] = f"The listing page could not be read ({type(exc).__name__})."
        return result

    for page_url in pages:
        for candidate in candidates(html_by_url.get(page_url, ""), page_url):
            result["tried"].append(candidate)
            verdict = await probe(candidate)
            if verdict["ok"]:
                result.update({"video_url": candidate, "found": True,
                               "detail": verdict["detail"], "bytes": verdict.get("bytes")})
                return result
            result["detail"] = verdict["detail"]
    if not result["detail"]:
        result["detail"] = "No video, so your ad will be a photo carousel."
    else:
        result["detail"] = ("No usable video, so your ad will be a photo carousel. "
                           + result["detail"])
    return result
