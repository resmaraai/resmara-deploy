"""The design step calls OpenAI directly (Post Engine §7.7 / Appendix C).

No Make, no BSP scenario: the listing photo and the brief go to /v1/images/edits with the exact
parameters from Appendix C (gpt-image-2.5-sunburst, 1024x1280, high, opaque, PNG, n=1), and the
finished post is read back by a checker before it is kept.

These tests run against a local stand-in for the API - a real HTTP server that records exactly
what Resmara sent - so the request shape is proven without spending money. A paid call is the only
thing not covered here, and that is stated in the report rather than implied.
"""
import base64
import io
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_DIR = tempfile.mkdtemp(prefix="design-")
os.environ["RESMARA_DB"] = os.path.join(DB_DIR, "app.db")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(DB_DIR, 'app.db')}"
os.environ["RESMARA_UPLOAD_DIR"] = os.path.join(DB_DIR, "uploads")

from PIL import Image  # noqa: E402

CALLS = []          # every request, in order
MODE = {"checker": "ok", "edit": "ok", "checker_seen": 0}


def png_bytes(color=(200, 180, 160), size=(300, 400)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG", quality=80)
    return buf.getvalue()


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format, *args):  # noqa: A002 - matches the base class signature
        pass

    def _body(self):
        length = int(self.headers.get("content-length") or 0)
        return self.rfile.read(length)

    def _json(self, payload, code=200):
        raw = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        body = self._body()
        if self.path.endswith("/images/edits"):
            CALLS.append({"path": self.path, "body": body, "auth": self.headers.get("authorization")})
            if MODE["edit"] == "fail":
                return self._json({"error": {"message": "content policy said no"}}, 400)
            made = png_bytes((90, 120, 160), (1024, 1280))
            return self._json({"data": [{"b64_json": base64.b64encode(made).decode()}]})
        if self.path.endswith("/chat/completions"):
            CALLS.append({"path": self.path, "body": body,
                          "auth": self.headers.get("authorization")})
            MODE["checker_seen"] += 1
            if MODE["checker"] == "bad_once" and MODE["checker_seen"] == 1:
                answer = {"text_ok": False, "text_seen": "JUST LSTED",
                          "photo_intact": True, "problem": 'the word "JUST LISTED" is misspelled'}
            else:
                answer = {"text_ok": True, "text_seen": "JUST LISTED", "photo_intact": True,
                          "problem": ""}
            return self._json({"choices": [{"message": {"content": json.dumps(answer)}}],
                               "usage": {"prompt_tokens": 10, "completion_tokens": 5}})
        return self._json({"error": {"message": f"unexpected path {self.path}"}}, 404)


server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
PORT = server.server_address[1]
threading.Thread(target=server.serve_forever, daemon=True).start()

os.environ["OPENAI_API_KEY"] = "sk-test-not-a-real-key"
os.environ["OPENAI_BASE_URL"] = f"http://127.0.0.1:{PORT}/v1"
# The repo's own .env points RESMARA_ENGINE_BASE_URL at a local model for dev; the engine vars win
# over OPENAI_BASE_URL, so a test that only set the OpenAI one would talk to the wrong server.
os.environ["RESMARA_ENGINE_BASE_URL"] = f"http://127.0.0.1:{PORT}/v1"
os.environ["RESMARA_ENGINE_API_KEY"] = "sk-test-not-a-real-key"  # beats the dev key in .env
os.environ["RESMARA_ALLOW_LOCAL_IMAGE_EDITS"] = "1"
os.environ["RESMARA_MODEL_DESIGN"] = "gpt-image-2.5-sunburst"
os.environ["RESMARA_MODEL_CHECK"] = "gpt-5.4-mini"

from app.services import design  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


class Boost:
    address = "123 Elm St, Austin TX"


def run(coro):
    import asyncio
    return asyncio.run(coro)


print("=== the brief says what the image may and may not do ===")
post = {"overlay": "JUST LISTED", "caption": "Three beds, a porch, and a backyard that faces west.",
        "room": "Front exterior"}
brief = design.brief_for(post, Boost(), {"name": "Dana Realty", "voice": "confident",
                                         "colors": ["#14342B", "#F2E8DC"], "font": "Inter"})
check("the overlay text is quoted exactly", '"JUST LISTED"' in brief, brief[:200])
check("  ...the address is named", "123 Elm St, Austin TX" in brief)
check("  ...the photo is not to be altered", "Do not add" in brief and "same room" in brief)
check("  ...the caption is kept off the image", "do not print it on the image" in brief)
check("  ...the brand colours are named", "#14342B" in brief)
check("  ...and the output shape is stated", "1024x1280" in brief)

print("\n=== a design call uses the Appendix C parameters ===")
CALLS.clear()
plan = [{"overlay": "JUST LISTED", "caption": "Front of the house", "room": "Front exterior"}]
photo = png_bytes()
result = run(design.design_posts(plan, Boost(), {"name": "Dana Realty"}, lambda p: (photo, "image/jpeg")))
edits = [c for c in CALLS if c["path"].endswith("/images/edits")]
check("one image edit was made", len(edits) == 1, str(len(CALLS)))
body = edits[0]["body"] if edits else b""
for name, needle in (("gpt-image-2.5-sunburst", b"gpt-image-2.5-sunburst"),
                     ("1024x1280", b"1024x1280"), ("quality high", b"\r\n\r\nhigh\r\n"),
                     ("background opaque", b"\r\n\r\nopaque\r\n"),
                     ("format png", b"\r\n\r\npng\r\n")):
    check(f"  ...{name} is set", needle in body, str(body[:400]))
check("  ...n is one image", b'name="n"\r\n\r\n1\r\n' in body, str(body[:600]))
check("  ...the photo itself is attached", b"image[]" in body and b"filename=\"photo.png\"" in body)
check("  ...and the key is sent as a bearer token", edits and edits[0]["auth"] == "Bearer sk-test-not-a-real-key",
      str(edits[0]["auth"])[:40] if edits else "")
check("the checker read it back", any(c["path"].endswith("/chat/completions") for c in CALLS))
check("  ...and the design was kept", result["designed"] and len(result["designed"]) == 1,
      str(result)[:300])
check("  ...as a PNG", result["designed"][0]["mime"] == "image/png")
check("  ...with one call counted", result["calls"] == 1, str(result["calls"]))

print("\n=== a misspelling is regenerated once, then accepted ===")
CALLS.clear()
MODE["checker"] = "bad_once"
MODE["checker_seen"] = 0
result = run(design.design_posts(plan, Boost(), {"name": "Dana Realty"}, lambda p: (photo, "image/jpeg")))
edits = [c for c in CALLS if c["path"].endswith("/images/edits")]
check("it tried again", len(edits) == 2, str(len(edits)))
check("  ...and said why in the second brief", b"misspelled" in edits[-1]["body"], "")
check("  ...the second design was kept", len(result["designed"]) == 1 and result["regenerated"] == 1,
      str(result)[:300])

print("\n=== a refusal is not retried forever, and the photo is kept ===")
CALLS.clear()
MODE["checker"] = "ok"
MODE["checker_seen"] = 0
MODE["edit"] = "fail"
result = run(design.design_posts(plan, Boost(), {"name": "Dana Realty"}, lambda p: (photo, "image/jpeg")))
edits = [c for c in CALLS if c["path"].endswith("/images/edits")]
check("a content-policy refusal is tried once", len(edits) == 1, str(len(edits)))
check("  ...nothing was designed", result["designed"] == [], str(result["designed"])[:120])
check("  ...the post is counted as a fallback", result["fallbacks"] == 1, str(result["fallbacks"]))
check("  ...and the reason names the provider's words",
      any("content policy" in n for n in result["notes"]), str(result["notes"])[:200])
MODE["edit"] = "ok"

print("\n=== a post with no photo is skipped, not invented ===")
result = run(design.design_posts([{"overlay": "A", "caption": ""}], Boost(), {},
                                lambda p: None))
check("nothing was sent", result["calls"] == 0, str(result["calls"]))
check("  ...and it says there was no photo",
      result["skipped"] and "no photo" in result["skipped"][0]["reason"], str(result["skipped"]))

print("\n=== without the model, the step declines to pretend ===")
os.environ.pop("RESMARA_ALLOW_LOCAL_IMAGE_EDITS", None)
check("design is unavailable off OpenAI's API", design.design_available() is False)
skipped = run(design.design_posts(plan, Boost(), {}, lambda p: (photo, "image/png")))
check("  ...and every post is reported skipped, not designed",
      skipped["designed"] == [] and "not configured" in " ".join(skipped["notes"]),
      str(skipped["notes"])[:160])
os.environ["RESMARA_ALLOW_LOCAL_IMAGE_EDITS"] = "1"

print("\n=== the brand kit separates what Meta told us from what the model proposed ===")
CALLS.clear()
page = {"name": "Dana Realty", "category": "Real Estate Agent",
        "about": "Selling homes in south Austin since 2009.", "phone": "512-555-0100",
        "website": "https://danarealty.example", "picture": {"data": {"url": "https://x/logo.png"}}}
CALLS.clear()
# the fake checker answers the brand call with its checker JSON, so only the facts are asserted
kit = run(design.brand_from_meta(page))
check("the page's own facts are carried through", kit["facts"]["name"] == "Dana Realty"
      and kit["facts"]["phone"] == "512-555-0100", str(kit["facts"])[:200])
check("  ...the logo comes from Meta", kit["facts"]["logo_url"] == "https://x/logo.png")
check("  ...and nothing is marked confirmed", kit["confirmed"] is False)

print("\n=== the cost line does not invent a price ===")
note = design.design_cost_note(14)
check("it names the call count", "14 image edits" in note, note)
check("  ...and points at the provider for the real cost", "provider" in note, note)

server.shutdown()
print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL DESIGN STEP TESTS PASSED")
