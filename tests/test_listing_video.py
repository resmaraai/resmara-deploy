"""The listing video: found when it is a real file, refused when it is an embed (§6.6).

The rule that matters is that Resmara only ever stores a direct public MP4/MOV that Meta can
pull. A YouTube embed, a Vimeo page or a Matterport walkthrough all look like "video" to a
regex and none of them can be posted as a native video, so they are tested as refusals.
"""
import http.server
import os
import sys
import tempfile
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services import listing_video  # noqa: E402
from app.services.content_engine import _apply_listing_video  # noqa: E402

PAGES = {
    "/listing": """<html><head><meta property="og:video" content="/media/tour.mp4"></head>
<body><h1>1234 Elm Street</h1><p>For sale $525,000</p><div>3 bed 2 bath 1,800 sq ft home
with a pool, updated kitchen and Hill Country views.</div></body></html>""",
    "/no-video": """<html><body><h1>1234 Elm Street</h1><p>For sale $525,000</p>
<p>3 bed 2 bath 1,800 sq ft</p></body></html>""",
    "/youtube": """<html><body><h1>1234 Elm</h1>
<iframe src="https://www.youtube.com/embed/abc123"></iframe>
<a href="https://www.youtube.com/watch?v=abc123">Watch the video walkthrough</a></body></html>""",
    "/tour-link": """<html><body><h1>1234 Elm</h1>
<a href="/tour-page">Virtual tour</a></body></html>""",
    "/tour-page": """<html><body><video src="/media/tour.mov"></video></body></html>""",
    "/dead-video": """<html><head><meta property="og:video" content="/media/missing.mp4"></head>
<body>For sale</body></html>""",
}


class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        path = self.path.split("?")[0]
        if path in PAGES:
            body = PAGES[path].encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if path in ("/media/tour.mp4", "/media/tour.mov"):
            self.send_response(200)
            self.send_header("Content-Type", "video/mp4")
            self.send_header("Content-Length", "2048")
            self.end_headers()
            self.wfile.write(b"\x00" * 2048)
            return
        self.send_response(404)
        self.send_header("Content-Type", "text/html")
        self.end_headers()
        self.wfile.write(b"<html>not found</html>")

    def log_message(self, fmt, *args):
        pass


server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
BASE = f"http://127.0.0.1:{server.server_address[1]}"
threading.Thread(target=server.serve_forever, daemon=True).start()

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def run(url):
    import asyncio
    return asyncio.run(listing_video.find(url))


print("=== a direct video file is found ===")
found = run(f"{BASE}/listing")
check("og:video with a direct MP4 is accepted", found["found"] is True, str(found)[:300])
check("  ...and the URL is the file itself", (found.get("video_url") or "").endswith("tour.mp4"),
      str(found.get("video_url")))
check("  ...and the agent is told one was found", "found" in found["detail"].lower(),
      found["detail"])

print("\n=== a page with no video says so, and says what happens instead ===")
none = run(f"{BASE}/no-video")
check("no video means no video", none["found"] is False)
check("  ...and the answer names the fallback",
      "photo carousel" in none["detail"].lower(), none["detail"])

print("\n=== embeds are not videos ===")
yt = run(f"{BASE}/youtube")
check("a YouTube embed is refused", yt["found"] is False, str(yt)[:300])
check("  ...and never stored as a video URL", not yt.get("video_url"))

print("\n=== the tour link is followed one level ===")
tour = run(f"{BASE}/tour-link")
check("a 'Virtual tour' link is followed", tour["found"] is True, str(tour)[:300])
check("  ...to the MOV behind it", (tour.get("video_url") or "").endswith("tour.mov"),
      str(tour.get("video_url")))

print("\n=== a dead video URL is not a video ===")
dead = run(f"{BASE}/dead-video")
check("a 404 video is refused", dead["found"] is False, str(dead)[:200])
check("  ...and the reason is passed on", "404" in dead["detail"], dead["detail"])

print("\n=== day 1 becomes the video and the ad becomes a video ad ===")


class FakeBoost:
    video_url = f"{BASE}/media/tour.mp4"


plan = {
    "posts": [
        {"day": 1, "slot": 1, "kind": "static", "caption": "Day one."},
        {"day": 2, "slot": 1, "kind": "static", "caption": "Day two."},
    ],
    "ad": {"creativeDays": [8, 11, 14], "primaryText": "hi"},
}
notes = []
changed = _apply_listing_video(plan, FakeBoost(), notes)
check("the video is applied", changed is True)
check("  ...to the day-1 post", plan["posts"][0]["kind"] == "main_video",
      str(plan["posts"][0]))
check("  ...with the URL on the post", plan["posts"][0]["video_url"].endswith("tour.mp4"))
check("  ...and the ad becomes one video ad",
      plan["ad"]["adType"] == "video" and plan["ad"]["creativeDays"] == [1],
      str(plan["ad"])[:200])
check("  ...and the agent's notes say which they got", any("video" in n for n in notes), str(notes))

plan2 = {"posts": [{"day": 1, "slot": 1, "kind": "static"}, {"day": 2, "slot": 1}],
         "ad": {"creativeDays": [8, 11, 14]}}
notes2 = []


class NoVideo:
    video_url = ""


check("no video leaves the calendar alone", _apply_listing_video(plan2, NoVideo(), notes2) is False)
check("  ...and the ad stays a carousel", "adType" not in plan2["ad"], str(plan2["ad"]))

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL LISTING VIDEO TESTS PASSED")
