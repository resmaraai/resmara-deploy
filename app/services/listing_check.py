"""Check a listing link before a campaign is paid for and built.

The New campaign form used to "check" a link without opening it: any address with a dot in it
got a green light, so a link to a page with no home on it sailed through to Build my campaign.
This opens the link, looks for a home and its photos, and says plainly what it found.

Never raises: every outcome is an answer the form can show.
"""
import asyncio
import re

from app.services import listing_video, listing_watch, photos

# Words a page about a home for sale carries somewhere, even when the portal hides the rest.
LISTING_WORDS = re.compile(r"\b(bed(room)?s?|bath(room)?s?|sq\.?\s?ft|square feet|mls|listing|for sale)\b", re.I)
SIGN_IN = re.compile(r"login|signin|sign-in|my\.flexmls", re.I)
MIN_PHOTOS = 4  # one or two images is a logo and a hero shot, not a gallery
NEED_PHOTOS = 14  # a campaign needs 14; fewer and the form asks for more (Engine 3, section 9)


def _answer(ok, reason, message, **extra):
    out = {"ok": ok, "reason": reason, "message": message, "opened": False, "details": False,
           "address": "", "photos": 0, "video": False, "status": listing_watch.UNKNOWN}
    out.update(extra)
    return out


async def check(url: str, *, read=None, discover=None, find_video=None,
                photo_timeout: float = 45, video_timeout: float = 20) -> dict:
    read = read or listing_watch.read_listing
    discover = discover or photos.discover
    find_video = find_video or listing_video.find
    url = (url or "").strip()
    if not re.match(r"^https?://[^/\s]+\.[^/\s]+", url):
        return _answer(False, "not_a_link", "That doesn’t look like a complete web link.")
    if SIGN_IN.search(url):
        return _answer(False, "sign_in", "This link needs an MLS sign-in to open.")

    status, html = await read(url)
    opened = 0 < status < 400
    if status in (404, 410):
        return _answer(False, "no_listing", "There’s no page at this link. It may have been taken down or typed wrong.",
                       status=listing_watch.OFFLINE)
    state = listing_watch.classify(status, html)
    address = photos.address_from_url(url)
    words = bool(LISTING_WORDS.search(html or ""))

    try:
        found = await asyncio.wait_for(discover(url, limit=60, address=address), timeout=photo_timeout)
    except Exception:  # noqa: BLE001 - a slow or walled gallery is "no photos", not an error
        found = []
    count = len(found or [])

    # A home is there when the link spells out an address, or the page reads like a listing.
    # A page that opened but has neither, and no gallery, is not a listing.
    details = bool(address) or (opened and words)
    if not details and count < MIN_PHOTOS:
        return _answer(False, "no_listing", "We couldn’t find a home for sale at this link.",
                       opened=opened, status=state)
    if state in (listing_watch.SOLD, listing_watch.PENDING):
        return _answer(False, state, "This listing shows as " + ("sold" if state == listing_watch.SOLD else "pending")
                       + ", so it can’t be advertised.", opened=opened, details=details, address=address,
                       photos=count, status=state)

    try:
        video = await asyncio.wait_for(find_video(url), timeout=video_timeout)
    except Exception:  # noqa: BLE001
        video = {}
    has_video = bool(video and video.get("found"))
    if count < MIN_PHOTOS:
        return _answer(True, "no_photos", "We have the home’s details, but we can’t get the photos from this link.",
                       opened=opened, details=True, address=address, photos=count, video=has_video, status=state)
    if count < NEED_PHOTOS:
        return _answer(True, "no_photos",
                       f"We have the home’s details and {count} photos, but a campaign needs at least "
                       f"{NEED_PHOTOS}. Add your photographer’s link or upload the rest.",
                       opened=opened, details=True, address=address, photos=count, video=has_video, status=state)
    return _answer(True, "ok", f"We have the home’s details and {count} photos.",
                   opened=opened, details=True, address=address, photos=count, video=has_video, status=state)
