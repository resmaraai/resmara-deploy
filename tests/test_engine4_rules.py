"""Engine 4's fixed rules: hashtags, Instagram captions, posting and ad hours, post styles, the ad's
hooks and the platform rulebook, Fair Housing on edits, 👍/👎 and the fallback design."""

import asyncio
import os
import tempfile
from datetime import date, datetime, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-e4-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"

from fastapi import HTTPException  # noqa: E402
from app.db.session import Base, engine, SessionLocal, User, Boost, Post, Event  # noqa: E402
from app.services import post_rules as pr, ad_rulebook, ad_hooks, design  # noqa: E402
from app.services.ad_build import ad_hours_schedule, FACEBOOK_POSITIONS, INSTAGRAM_POSITIONS  # noqa: E402

Base.metadata.create_all(bind=engine)
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


KIT = {"agent": "Swana Lee", "market": "Redding, CA"}
ADDR = "905 Laurel Bend, Redding, CA 96001"

print("Hashtags")
sets = [pr.hashtags_for(index=i, room=r, address=ADDR, kit=KIT, suggested=["#realestate", "#FamilyFriendly", "#ShastaCountyHomes"])
        for i, r in enumerate(["kitchen", "pool", "front exterior", "living room"])]
ig0, fb0 = sets[0]
ok("Instagram: 3 to 5 tags", all(3 <= len(ig) <= 5 for ig, _ in sets), [len(ig) for ig, _ in sets])
ok("Facebook: 0 to 2 tags", all(len(fb) <= 2 for _, fb in sets))
ok("a local tag and the agent's own tag on every post", all(any("Redding" in t for t in ig) and "#HomesWithSwana" in ig for ig, _ in sets))
ok("a tag for what the post shows", "#ReddingKitchen" in sets[0][0] and "#ReddingPoolHome" in sets[1][0], sets[0][0])
ok("no giant generic tags", not any(t.lower() == "#realestate" for ig, _ in sets for t in ig))
ok("no Fair Housing tags", not any("family" in t.lower() for ig, _ in sets for t in ig))
ok("a niche tag the planner suggested is kept when there's room", any("#ShastaCountyHomes" in ig for ig, _ in sets))
ok("rotated: no two posts carry the same block", len({tuple(ig) for ig, _ in sets}) == len(sets))
ok("the agent's own tag can be set on My Brand", pr.agent_tag({"ownTag": "#SellingWithSwana"}) == "#SellingWithSwana")

print("No links on Instagram")
body = "Morning light fills this kitchen. See it at https://homes.example/905 today.\nSwana Lee | 530-555-0101 | LIC 0212 | Shasta Realty | Equal Housing Opportunity"
ig = pr.instagram_caption(body, 0)
ok("the link is gone", "http" not in ig and not pr.has_link(ig), ig)
ok("an invitation instead, before the closing line", "Comment TOUR" in ig and ig.strip().endswith("Equal Housing Opportunity"), ig)


class P:
    def __init__(self, **kw):
        self.__dict__.update({"caption": "", "hashtags": "", "hashtags_fb": None, "caption_ig": None, "day": 1})
        self.__dict__.update(kw)


fb, igt = pr.messages(P(caption="Hello\n\n#A #B #C", hashtags="#A #B #C", hashtags_fb="#A", caption_ig="Hello there. Comment TOUR"))
ok("Facebook gets its own tags, never the block twice", fb == "Hello\n\n#A" and fb.count("#A") == 1, fb)
ok("Instagram gets its caption and its tags", igt == "Hello there. Comment TOUR\n\n#A #B #C", igt)
fb, igt = pr.messages(P(caption="See www.x.com\n\n#A #B #C", hashtags="#A #B #C"))
ok("an older post: Facebook takes two of its tags, Instagram loses the link", fb.endswith("#A #B") and "www" not in igt, (fb, igt))

print("Posting times")
when = datetime.fromisoformat(pr.publish_at(date(2026, 12, 1), 1, ADDR)).replace(tzinfo=timezone.utc)
local = when.astimezone(pr.local_zone(ADDR))
ok("stored in UTC for the listing's local hour (6 PM Pacific = 02:00 UTC next day)", (when.hour, local.hour, local.day) == (2, 18, 1), (when, local))
ok("Texas listings use Central time", str(pr.local_zone("1 Main St, Austin, TX 78701")) == "America/Chicago")
ok("the audience's best hours win, inside 6 AM-11 PM", pr.best_hours({3: 900, 20: 500, 8: 400, 12: 100}) == (20, 8))
ok("never before 6 AM or after 11 PM", pr.clamp_hour(2) == 6 and pr.clamp_hour(23) == 22)

print("Post styles")
plan = pr.style_plan(14, liked={"full_photo": 5, "editorial": 2}, avoid=["framed"])
ok("never the same style twice in a row", all(a != b for a, b in zip(plan, plan[1:])), plan)
ok("styles they disliked are left out", "framed" not in plan)
fam = sum(1 for k in plan if k in ("full_photo", "editorial"))
ok("about two thirds familiar, one third new", 7 <= fam <= 11 and len(set(plan) - {"full_photo", "editorial"}) >= 2, plan)
again = pr.style_plan(14, liked={"full_photo": 5, "editorial": 2}, avoid=["framed"], last=plan)
ok("never repeats the last campaign's sequence", again != plan)

print("The ad set")
sched = ad_hours_schedule()[0]
ok("ads run 6 AM to 11 PM only, viewer's time zone", (sched["start_minute"], sched["end_minute"], sched["timezone_type"]) == (360, 1380, "USER") and len(sched["days"]) == 7)
ok("every placement Meta allows for housing", "marketplace" in FACEBOOK_POSITIONS and "facebook_reels" in FACEBOOK_POSITIONS and "reels" in INSTAGRAM_POSITIONS)

print("The rulebook")
ok("Have you seen a pool like this? passes", ad_rulebook.check({"hook": "Have you seen a pool like this?", "primaryText": "A pool in the oaks.", "headline": "905 Laurel Bend", "backedBy": "pool"}) == [])
bad = ad_rulebook.check({"hook": "Are you a first-time buyer?", "primaryText": "The best home for your growing family", "headline": "x", "backedBy": "x"})
ok("personal attributes, Fair Housing and unverifiable claims are caught", len(bad) >= 3 and any("Personal" in b for b in bad)
   and any("Fair Housing" in b for b in bad) and any("backed" in b for b in bad), bad)
ok("a hook with nothing behind it is caught", any("backed" in i for i in ad_rulebook.check({"hook": "Look at this"})))
fit = ad_rulebook.fit({"primaryText": "word " * 40, "headline": "x" * 60})
ok("text is trimmed to Meta's limits", len(fit["primaryText"]) <= 125 and len(fit["headline"]) <= 40)

print("The hooks")
from app.services import llm  # noqa: E402
real = llm.llm_available
llm.llm_available = lambda: False
out = asyncio.run(ad_hooks.build_hooks(address=ADDR, research="", differentiators=["Saltwater pool under the oaks", "Shop with 12-foot doors", "Mount Shasta view"], photo_index=""))
llm.llm_available = real
ok("up to 3 hook versions, each backed by the home's file", 1 <= len(out["hooks"]) <= 3 and all(h["backedBy"] for h in out["hooks"]), out["hooks"])
ok("every kept hook passes the rulebook", all(not ad_rulebook.check(h) for h in out["hooks"]))

print("The fallback design")
from PIL import Image  # noqa: E402
import io  # noqa: E402
buf = io.BytesIO()
Image.new("RGB", (1600, 1000), "#88aacc").save(buf, format="JPEG")
png = design.fallback_design(buf.getvalue(), "Where summer actually happens", "Swana Lee · 530-555-0101", ["#2F4F3E"])
img = Image.open(io.BytesIO(png))
ok("a finished 4:5 design with the words drawn in code, never a plain photo", img.size == (1024, 1280) and png[:4] == b"\x89PNG")
ok("an unreadable photo gives no design (the next photo is used)", design.fallback_design(b"nope", "x") is None)

print("Edits, thumbs and the style profile")
from app.api.engine import edit_post, rate_post, PostEdit, PostRating  # noqa: E402
from app.services.content_engine import style_profile, learned_summary  # noqa: E402
db = SessionLocal()
u = User(email="a@example.com", hashed_password="x", name="Swana", is_admin=True)
db.add(u); db.commit()
b = Boost(user_id=u.id, address=ADDR)
db.add(b); db.commit()
p = Post(boost_id=b.id, day=1, slot=1, caption="Morning light.\n\n#ReddingHomes", hashtags="#ReddingHomes",
         design_style="full_photo", details_treatment="a corner mark")
db.add(p); db.commit()
try:
    edit_post(b.id, p.id, PostEdit(caption="Perfect for your growing family."), current_user=u, db=db)
    refused = False
except HTTPException as exc:
    refused = exc.status_code == 422 and exc.detail["error"] == "fair_housing"
ok("a non-compliant edit can't be saved", refused)
r = edit_post(b.id, p.id, PostEdit(caption="Coffee by the big window. See it at https://x.example"), current_user=u, db=db)
db.refresh(p)
ok("an edit is saved server-side, tags kept, Instagram caption rewritten without the link",
   p.caption.startswith("Coffee by the big window") and p.caption.endswith("#ReddingHomes") and "http" not in (p.caption_ig or ""), (p.caption, p.caption_ig))
ok("  ...and recorded for the learner", "caption" in (p.features or {}).get("edited", []))
rate_post(b.id, p.id, PostRating(value=1), current_user=u, db=db)
db.refresh(p)
ok("👍 is stored", p.rating == 1)
b2 = Boost(user_id=u.id, address=ADDR); db.add(b2); db.commit()
for i, (st, rt) in enumerate([("framed", -1), ("framed", -1), ("editorial", None)]):
    db.add(Post(boost_id=b2.id, day=i + 1, slot=1, design_style=st, rating=rt, client_status="approved" if rt is None else "pending"))
db.commit()
prof = style_profile(db, u.id)
ok("the profile likes what got 👍 and approvals, avoids what got 👎", "full_photo" in prof["liked"] and "framed" in prof["avoid"] and "editorial" in prof["liked"], prof)
lines = learned_summary(prof)
ok("What Resmara learned about you, in plain words", any(l.startswith("You like") for l in lines) and any("don't like" in l for l in lines), lines)

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL ENGINE 4 RULE TESTS PASSED")
