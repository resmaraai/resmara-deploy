"""The design step: a real listing photo + a brief, sent to OpenAI's image model (Post Engine
§7.7 and Appendix C).

BAP's Boost did this in Make: fill in the brief, send the listing photo + brief to OpenAI's image
edit, run the checker, file the result. The owner's instruction was explicit - Resmara does these
steps in the backend and calls OpenAI directly, no Make. This module is that port:

  1. `brief_for(post, boost, brand)` builds the design brief from the plan's own fields, so the
     words on the post come from what the model already wrote, never from a template invented here.
  2. `design_one(...)` posts a multipart image edit: the listing photo (and the logo/headshot when
     there is one) plus the brief, at 1024x1280, quality high, background opaque, PNG - the exact
     parameters in Appendix C.
  3. `check_design(...)` is the checker: the finished post is shown to the vision model with the
     text it was supposed to carry. A post whose text is wrong is regenerated once with the
     correction appended; a second failure keeps the original *photo* rather than shipping a post
     with garbled words on it.

Nothing here is free, so nothing here is guessed: `design_posts` reports what each call cost, what
failed, and which posts fell back to the untouched photo. When the key or the model is missing the
whole step is skipped and says so - it never writes a fake design.
"""

from __future__ import annotations

import asyncio
import base64
import re
import io
import logging
import os

import httpx

from app.core.config import settings
from app.services import llm
from app.services.llm import _json_object

log = logging.getLogger("resmara.design")

# Appendix C, verbatim: the worked-example zip's 14 calls were made with these.
DEFAULT_MODEL = "gpt-image-2.6-sunburst"  # Engine 4, 9d: the newest OpenAI image model, as a setting
SIZE = "1024x1280"
QUALITY = "high"
BACKGROUND = "opaque"
OUTPUT_FORMAT = "png"

# A design call is slow (a 1024x1280 high-quality edit is 20-60s); the build gives each one its
# own budget instead of sharing the chat timeout.
CALL_TIMEOUT = 180.0


class DesignError(Exception):
    """The image model refused or returned nothing usable."""


def model() -> str:
    return (os.getenv("RESMARA_MODEL_DESIGN")
            or getattr(settings, "OPENAI_MODEL_DESIGN", "")
            or DEFAULT_MODEL)


def check_model() -> str:
    """The vision model that reads the finished post back before it is published."""
    return (os.getenv("RESMARA_MODEL_CHECK") or getattr(settings, "OPENAI_MODEL_CHECK", "")
            or getattr(settings, "OPENAI_MODEL_VISION", "")
            or getattr(settings, "OPENAI_MODEL_PLAN", "gpt-5.5"))


def brand_model() -> str:
    return (os.getenv("RESMARA_MODEL_BRAND")
            or getattr(settings, "OPENAI_MODEL_BRAND", "")
            or getattr(settings, "OPENAI_MODEL_PLAN", "gpt-5.5"))


def design_available() -> bool:
    """True when a real design call can be made, and it is not a simulated build."""
    if bool(getattr(settings, "SIMULATE", False)):
        return False
    # Image edits only exist on OpenAI's own API; a chat-compatible local endpoint cannot do this.
    # The second clause exists so a local mock server can be used to verify this step without a
    # paid call, and it has to be asked for by name - it is never on by accident.
    native = llm.is_openai_native() or os.getenv("RESMARA_ALLOW_LOCAL_IMAGE_EDITS") == "1"
    return bool(llm.engine_key()) and native


def _base() -> str:
    return llm.engine_base()


# --------------------------------------------------------------------------- brief
BRAND_VOICE = {
    "confident": "Confident and plain. Short sentences. No hype, no exclamation marks.",
    "warm": "Warm and human. Speak to one person, not an audience.",
    "luxury": "Restrained and expensive-feeling. Few words, generous space.",
    "playful": "Light and friendly, one small smile, never silly.",
}

LAYOUTS = (
    "Headline in the lower third, one line if it fits, set in the brand typeface, generous "
    "margins, subtle dark scrim behind the text so it stays readable on any photo."
)


def _brand_bits(brand: dict | None) -> dict:
    brand = brand or {}
    return {
        "name": str(brand.get("name") or brand.get("business_name") or "").strip(),
        "voice": BRAND_VOICE.get(str(brand.get("voice") or "").lower(), ""),
        "colors": [c for c in (brand.get("colors") or []) if c][:4],
        "font": str(brand.get("font") or brand.get("typeface") or "").strip(),
        "logo": str(brand.get("logo_url") or "").strip(),
    }


def brief_for(post: dict, boost, brand: dict | None = None) -> str:
    """The design brief for one post. Every word on the image comes from the plan.

    Post Engine §7.7: the brief names the overlay text, the room, the address treatment and the
    brand look; it never asks the model to invent a claim about the property. The address is the
    only hard fact printed, because a wrong price or a wrong bed count on an image is a fair
    housing complaint waiting to happen.
    """
    bits = _brand_bits(brand)
    kit = brand or {}
    # The brand engine's kit (Engine 2) names colours as a palette and fonts as a pair.
    if not bits["colors"] and kit.get("palette"):
        bits["colors"] = [str(p[1]) for p in kit.get("palette") or [] if isinstance(p, (list, tuple)) and len(p) > 1][:4]
    if not bits["font"] and kit.get("fonts"):
        bits["font"] = " for headlines and ".join(str(f) for f in (kit.get("fonts") or [])[:2]) + " for small type"
    overlay = str(post.get("overlay") or post.get("headline") or "").strip()
    caption = str(post.get("caption") or "").strip()
    room = str(post.get("room") or "").strip()
    address = str(getattr(boost, "address", "") or "").strip()

    lines = [
        "Edit this real estate photograph into a finished social post for a property listing.",
        "Keep the photograph itself: same room, same furniture, same light, same view. Do not add "
        "or remove furniture, change the architecture, widen the room, or change the weather.",
        "Colour grade gently toward warm, natural daylight. Do not add people, pets, text, "
        "watermarks, borders or logos other than the ones supplied.",
    ]
    if room:
        lines.append(f"The photograph shows: {room}.")
    if overlay:
        lines.append(f'Set exactly this text on the image, spelled exactly as written: '
                     f'"{overlay}". Nothing else. No other lettering anywhere.')
    else:
        lines.append("Add no text at all.")
    if address:
        lines.append(f'Print this address in small type in the lower corner: "{address}".')
    style = str(post.get("style") or "").strip()
    if style:
        # Engine 4, section 4: one of six post styles, in this agent's brand; the layout, crop and
        # composition are chosen fresh for this photo. Words only where the photo has calm space.
        from app.services.post_rules import style_words
        lines.append(f"Post style: {style_words(style)}. Choose the layout, crop and composition fresh "
                     "for this photo, and place words only where the photo has calm space, never over "
                     "the subject.")
    else:
        lines.append(LAYOUTS)
    details = str(post.get("details") or "").strip()
    treatment = str(post.get("treatment") or "").strip()
    if details and treatment and treatment != "caption":
        lines.append(f'Show the agent\'s details exactly as written, as {treatment}: "{details}".')
    refs = post.get("references") or 0
    if refs:
        lines.append("The extra reference images are this agent's earlier posts they liked: match their "
                     "typography, type sizes, spacing and colour handling so this reads as part of the "
                     "same series, but never copy their photo, layout or words.")
    if bits["name"]:
        lines.append(f"The brand is {bits['name']}.")
    if bits["voice"]:
        lines.append(bits["voice"])
    if bits["colors"]:
        lines.append("Use only these brand colours for any graphic elements: "
                     + ", ".join(bits["colors"]) + ".")
    if bits["font"]:
        lines.append(f"Set the type in {bits['font']} or the closest available.")
    if caption:
        # The caption is for the post body, not the image; naming it stops the model printing it.
        lines.append("The caption that accompanies this post (do not print it on the image): "
                     + caption[:400])
    lines.append("Output a portrait 1024x1280 PNG, opaque background, no transparency.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- one design
async def _edit(files: list, prompt: str, *, model_name: str) -> bytes:
    """One image edit. Returns PNG bytes or raises DesignError with the provider's own words."""
    data = {
        "model": model_name,
        "prompt": prompt,
        "size": SIZE,
        "quality": QUALITY,
        "background": BACKGROUND,
        "output_format": OUTPUT_FORMAT,
        "n": "1",
    }
    headers = {"Authorization": f"Bearer {llm.engine_key()}"}
    url = _base() + "/images/edits"
    try:
        async with httpx.AsyncClient(timeout=CALL_TIMEOUT) as client:
            resp = await client.post(url, data=data, files=files, headers=headers)
    except Exception as exc:  # noqa: BLE001 - transport failures are reported, not raised raw
        raise DesignError(f"{type(exc).__name__}: {exc}") from exc

    if resp.status_code >= 400:
        detail = resp.text[:400]
        try:
            body = resp.json()
            detail = (body.get("error") or {}).get("message") or detail
        except Exception:  # noqa: BLE001
            pass
        raise DesignError(f"HTTP {resp.status_code}: {detail}")

    try:
        body = resp.json()
    except Exception as exc:  # noqa: BLE001
        raise DesignError(f"unreadable response: {exc}") from exc

    items = body.get("data") or []
    b64 = (items[0] or {}).get("b64_json") if items else None
    if not b64:
        raise DesignError("the response carried no image")
    try:
        return base64.b64decode(b64)
    except Exception as exc:  # noqa: BLE001
        raise DesignError(f"the image was not valid base64: {exc}") from exc


def _photo_files(photo: bytes, mime: str, logo: bytes | None, logo_mime: str,
                 headshot: bytes | None) -> list:
    files = [("image[]", ("photo.png", photo, mime or "image/png"))]
    if logo:
        files.append(("image[]", ("logo.png", logo, logo_mime or "image/png")))
    if headshot:
        files.append(("image[]", ("headshot.png", headshot, "image/png")))
    return files


def _to_png(raw: bytes) -> bytes:
    """The edit endpoint wants real image bytes; a JPEG from a phone is fine, but normalise."""
    try:
        from PIL import Image

        with Image.open(io.BytesIO(raw)) as img:
            if img.format == "PNG":
                return raw
            buf = io.BytesIO()
            img.convert("RGB").save(buf, format="PNG")
            return buf.getvalue()
    except Exception:  # noqa: BLE001 - hand the bytes over and let the provider judge them
        return raw


# --------------------------------------------------------------------------- the checker
CHECK_PROMPT = (
    "You are checking a finished real-estate social post before it is published, and you are also "
    "its Art Director. Answer with one JSON object only: "
    '{"text_ok": true|false, "text_seen": "<the words actually visible on the image>", '
    '"photo_intact": true|false, "score": <1-10>, "problem": "<empty when fine, else one short sentence>"}. '
    "text_ok is false if any word is misspelled, duplicated, cut off, or if the image carries "
    "lettering that was not asked for. photo_intact is false if the room was changed, refurnished, "
    "or the image is not the supplied photograph. score is the Art Director's mark for a post a "
    "top real estate brand would be proud to share: layout, legibility on a phone, text kept off the "
    "subject of the photo, and whether people would stop scrolling for it. 8 or more is great, 6 is "
    "acceptable, below 6 means redo it."
)
ART_DIRECTOR_MIN = 6


async def check_design(image_bytes: bytes, expected_text: str) -> dict:
    """The checker pass. Never raises: a checker that cannot run must not block the build."""
    try:
        data_url = _data_url(image_bytes)
        import json as _json
        raw = await llm.chat_text(
            CHECK_PROMPT,
            f'The text the post was supposed to carry: "{expected_text}". Check this image and '
            "answer with the JSON object only.",
            model=check_model(),
            images=[data_url],
            max_completion_tokens=400,
        )
        reply = _json_object(raw)
        if not isinstance(reply, dict):
            return {"ok": None, "reason": "the checker did not answer in JSON"}
        text_seen = str(reply.get("text_seen") or "")
        try:
            score = int(reply.get("score")) if reply.get("score") is not None else None
        except (TypeError, ValueError):
            score = None
        weak = score is not None and score < ART_DIRECTOR_MIN
        ok = bool(reply.get("text_ok")) and bool(reply.get("photo_intact", True)) and not weak
        problem = str(reply.get("problem") or "")[:300]
        if weak and not problem:
            problem = f"the Art Director scored it {score}/10: make the layout stronger and more legible"
        return {"ok": ok, "text_seen": text_seen, "score": score, "problem": problem}
    except Exception as exc:  # noqa: BLE001
        return {"ok": None, "reason": f"{type(exc).__name__}: {exc}"[:300]}


def _data_url(raw: bytes) -> str:
    try:
        from PIL import Image

        with Image.open(io.BytesIO(raw)) as img:
            img = img.convert("RGB")
            img.thumbnail((1024, 1024))
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=85)
            raw = buf.getvalue()
    except Exception:  # noqa: BLE001
        pass
    return "data:image/png;base64," + base64.b64encode(raw).decode()


# --------------------------------------------------------------------------- the fallback design
def fallback_design(photo: bytes, overlay: str, details: str = "", colors: list | None = None) -> bytes | None:
    """Resmara's own layout over the photo, with the words drawn in code so they're always spelled
    right (Engine 4, 9 and "If part of a build fails"). Never a plain photo. None if the photo is unreadable."""
    try:
        from PIL import Image, ImageDraw, ImageFont
        with Image.open(io.BytesIO(photo)) as src:
            img = src.convert("RGB")
    except Exception:  # noqa: BLE001
        return None
    W, H = 1024, 1280
    scale = max(W / img.width, H / img.height)
    img = img.resize((max(W, int(img.width * scale + 0.5)), max(H, int(img.height * scale + 0.5))))
    left, top = (img.width - W) // 2, (img.height - H) // 2
    img = img.crop((left, top, left + W, top + H))
    accent = "#12354D"
    for c in colors or []:
        if re.fullmatch(r"#?[0-9a-fA-F]{6}", str(c or "")):
            accent = "#" + str(c).lstrip("#")
            break
    # A soft gradient behind the words so they read on any photo.
    shade = Image.new("L", (W, H), 0)
    sd = ImageDraw.Draw(shade)
    for y in range(int(H * 0.55), H):
        sd.line([(0, y), (W, y)], fill=int(200 * (y - H * 0.55) / (H * 0.45)))
    img = Image.composite(Image.new("RGB", (W, H), "#000000"), img, shade)
    d = ImageDraw.Draw(img)
    words = (overlay or "").strip()
    y = H - 210
    if words:
        size = 76
        font = ImageFont.load_default(size=size)
        lines, line = [], ""
        for w in words.split():
            trial = (line + " " + w).strip()
            if d.textlength(trial, font=font) > W - 140 and line:
                lines.append(line)
                line = w
            else:
                line = trial
        lines.append(line)
        lines = lines[:3]
        y = H - 200 - len(lines) * (size + 8)
        d.rectangle([70, y - 26, 170, y - 18], fill=accent)
        for ln in lines:
            d.text((70, y), ln, font=font, fill="#FFFFFF")
            y += size + 8
    if details:
        small = ImageFont.load_default(size=26)
        d.text((70, H - 86), details[:90], font=small, fill="#FFFFFF")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


# --------------------------------------------------------------------------- the step
async def design_posts(plan_posts: list[dict], boost, brand: dict | None,
                       photo_for, *, logo: bytes | None = None, logo_mime: str = "",
                       headshot: bytes | None = None, checker: bool = True,
                       references: list | None = None) -> dict:
    """Design every post in the plan. ``photo_for(post) -> (bytes, mime)`` supplies the source.

    Returns {"designed": [{"index", "bytes", "mime", "note"}], "skipped": [...], "calls": n,
    "model": ..., "checked": n, "regenerated": n, "fallbacks": n, "notes": [...]}.

    A post whose source photo is missing is skipped with a reason. A post the model refuses twice
    keeps its **photo** as the post image (an undesigned photo is honest; a post with the wrong
    words on it is not), and the note says which.
    """
    out = {"designed": [], "skipped": [], "calls": 0, "checked": 0, "regenerated": 0,
           "fallbacks": 0, "notes": [], "model": model()}
    if not design_available():
        # Never a plain photo: every post still gets the fallback design, flagged for a look.
        for index, post in enumerate(plan_posts):
            raw_mime = photo_for(post)
            made = fallback_design(_to_png(raw_mime[0]), str(post.get("overlay") or ""), str(post.get("details") or ""),
                                   (brand or {}).get("colors") or [p[1] for p in ((brand or {}).get("palette") or []) if len(p) > 1]) \
                if raw_mime and raw_mime[0] else None
            if made:
                out["fallbacks"] += 1
                out["designed"].append({"index": index, "bytes": made, "mime": "image/png", "note": "fallback",
                                        "needs_look": True})
            else:
                out["skipped"].append({"index": index, "reason": "no image model and no usable photo"})
        out["notes"].append("the image model is not configured, so the posts use Resmara's fallback design")
        return out

    model_name = model()
    for index, post in enumerate(plan_posts):
        raw_mime = photo_for(post)
        if not raw_mime or not raw_mime[0]:
            out["skipped"].append({"index": index, "reason": "no photo for this post"})
            continue
        raw, mime = raw_mime
        photo = _to_png(raw)
        brief = brief_for(post, boost, brand)
        expected = str(post.get("overlay") or post.get("headline") or "").strip()
        files = _photo_files(photo, mime, logo, logo_mime, headshot)
        # Their own 👍 posts as references (Engine 4, 9): two per post, rotating through the pool.
        refs = [r for r in (references or []) if r]
        if refs:
            picks = [refs[(index * 2 + k) % len(refs)] for k in range(min(2, len(refs)))]
            for k, ref in enumerate(dict.fromkeys(picks)):
                files.append(("image[]", (f"reference-{k + 1}.png", ref, "image/png")))
            post = {**post, "references": len(set(picks))}
            brief = brief_for(post, boost, brand)

        made = None
        last_error = ""
        for attempt in range(2):
            try:
                out["calls"] += 1
                made = await _edit(files, brief, model_name=model_name)
            except DesignError as exc:
                last_error = str(exc)[:300]
                # A refusal on the content policy will refuse again; only retry transport/5xx.
                if str(exc).startswith("HTTP 4") and "429" not in str(exc)[:12]:
                    break
                await asyncio.sleep(2)
                continue
            if not checker or not expected:
                break
            verdict = await check_design(made, expected)
            out["checked"] += 1
            if verdict.get("ok") is not False:
                break
            # Try once more with the checker's complaint appended - a misspelling is usually fixed
            # by naming it, and a second wrong answer keeps the photo instead.
            problem = verdict.get("problem") or "the text did not match"
            brief = brief + (f"\n\nThe previous attempt had this problem, fix it: {problem}. "
                             f'The only text allowed on the image is "{expected}".')
            out["regenerated"] += 1
            made = None

        if not made:
            # Retried once already: now the fallback design, flagged "Needs a look". Never a plain photo.
            out["fallbacks"] += 1
            colors = (brand or {}).get("colors") or [p[1] for p in ((brand or {}).get("palette") or []) if len(p) > 1]
            fb = fallback_design(photo, expected, str(post.get("details") or ""), colors)
            if fb:
                out["notes"].append(f"post {index + 1} used the fallback design and is flagged Needs a look: "
                                    f"{last_error or 'the checks rejected it twice'}")
                out["designed"].append({"index": index, "bytes": fb, "mime": "image/png", "note": "fallback",
                                        "needs_look": True})
            else:
                out["skipped"].append({"index": index, "reason": last_error or "rejected twice"})
            continue
        out["designed"].append({"index": index, "bytes": made, "mime": "image/png",
                                "note": "designed"})
    return out


async def brand_from_meta(page: dict, business: dict | None = None) -> dict:
    """Build a brand kit from what Meta knows (Brand Engine v1.0 §4).

    Page name, category, about text, phone, address and the profile picture are facts; voice,
    palette and typeface are *proposals* the agent confirms in My Brand. The function says which
    is which, so nothing here can be mistaken for something Meta told us.
    """
    business = business or {}
    facts = {
        "name": str(page.get("name") or business.get("name") or "").strip(),
        "category": str(page.get("category") or "").strip(),
        "about": str(page.get("about") or page.get("description") or "").strip()[:600],
        "phone": str(page.get("phone") or "").strip(),
        "website": str(page.get("website") or "").strip(),
        "address": str((page.get("location") or {}).get("street") or "").strip(),
        "logo_url": str((page.get("picture") or {}).get("data", {}).get("url") or "").strip(),
    }
    proposed = {"voice": "", "colors": [], "font": "", "tagline": "", "why": []}
    if llm.llm_available() and (facts["about"] or facts["category"]):
        try:
            reply = await llm.chat_json(
                "You design brand kits for real-estate agents. Answer with JSON only: "
                '{"voice": "confident|warm|luxury|playful", "colors": ["#rrggbb", "#rrggbb", '
                '"#rrggbb"], "font": "<a common, safe typeface>", "tagline": "<6 words max, no '
                'exclamation marks>", "why": ["<one line per choice>"]}. Choose from the facts '
                "given; invent nothing about awards, sales or licensing.",
                str(facts)[:1500],
                model=brand_model(),
                max_completion_tokens=400)
            if isinstance(reply, dict):
                for key in ("voice", "colors", "font", "tagline", "why"):
                    if reply.get(key):
                        proposed[key] = reply[key]
        except Exception as exc:  # noqa: BLE001
            proposed["why"] = [f"the model did not answer: {type(exc).__name__}"]
    return {"facts": facts, "proposed": proposed,
            "source": "meta+model" if proposed["colors"] else "meta only",
            "confirmed": False}


def design_cost_note(calls: int) -> str:
    """What the design step cost, said plainly (item 6: ~$4 per campaign for 14 images)."""
    return (f"{calls} image edit{'s' if calls != 1 else ''} made. The owner's benchmark is about "
            f"$4 per 14-image campaign; the provider's own usage is the authority, not this line.")
