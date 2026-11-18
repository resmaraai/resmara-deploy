"""Small previews of stored photos.

A listing photo is an original: 2-7 MB, 2500 px wide. A campaign page that draws the whole
library at once (6495 Mojave Court has 122 of them) then costs hundreds of megabytes and a
minute of blank boxes on a free-tier instance. `preview()` makes a browser-sized copy on the
spot, and the full-size file stays one click away through its own URL.

Nothing is lost when Pillow cannot read the bytes: the caller falls back to the original.
"""
from __future__ import annotations

import io
import threading
from typing import Optional

from PIL import Image

QUALITY = 72
MIN_SIZE, MAX_SIZE = 48, 1280

# A free instance has 512 MB. Decoding several 2500 px JPEGs at once is what takes it down: a
# campaign page asks for 100+ previews in one burst, so at most two are decoded at a time and
# the rest queue for a moment instead of the process being killed.
_DECODING = threading.BoundedSemaphore(2)


def _clamp(size: int) -> int:
    return max(MIN_SIZE, min(int(size or 0), MAX_SIZE))


def preview(raw: Optional[bytes], size: int = 360) -> Optional[bytes]:
    """`raw` as a JPEG whose long edge is at most `size` px, or None if it cannot be read."""
    if not raw:
        return None
    size = _clamp(size)
    try:
        with _DECODING:
            return _encode(raw, size)
    except Exception:  # noqa: BLE001 - a broken photo is the caller's fallback, not a 500
        return None


def _encode(raw: bytes, size: int) -> Optional[bytes]:
    try:
        image = Image.open(io.BytesIO(raw))
        # draft() makes the decoder stop early for JPEGs (1/2, 1/4, 1/8 scale) instead of
        # decoding 2500 px to throw the pixels away in thumbnail().
        image.draft("RGB", (size, size))
        image = image.convert("RGB")
        image.thumbnail((size, size))
        out = io.BytesIO()
        image.save(out, "JPEG", quality=QUALITY, optimize=True)
        return out.getvalue()
    except Exception:  # noqa: BLE001 - a broken photo is the caller's fallback, not a 500
        return None
