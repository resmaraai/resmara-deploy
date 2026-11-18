"""A repeat round learns from the last one: rank its posts by real Meta numbers, lead with what
worked, drop what was ignored, and never invent a number.

Hermetic: Meta is never called; the insights functions are swapped for stand-ins.

Run:  PYTHONPATH=. python tests/test_round_learning.py
"""
import asyncio
import sys
from types import SimpleNamespace as NS

from app.services import round_learning as rl

PASSED = 0
FAILED = 0


def check(label, cond, detail=""):
    global PASSED, FAILED
    if cond:
        PASSED += 1
        print("  [PASS] %s" % label)
    else:
        FAILED += 1
        print("  [FAIL] %s  %s" % (label, detail))


POSTS = {
    1: NS(id=1, day=1, kind="static", post_type="photo", photo_file="pool.jpg", photo_room="pool",
          title="Where summer actually happens", overlay_text="Your backyard resort"),
    2: NS(id=2, day=2, kind="short_video", post_type="video", photo_file="tour.mp4", photo_room="tour",
          title="Walk the house in 30 seconds", overlay_text="Take the tour"),
    3: NS(id=3, day=3, kind="static", post_type="photo", photo_file="laundry.jpg", photo_room="laundry",
          title="The details", overlay_text="Space for everything"),
    4: NS(id=4, day=4, kind="static", post_type="photo", photo_file="kitchen.jpg", photo_room="kitchen",
          title="How much room is enough?", overlay_text="Room to cook"),
}
ROWS = [
    {"db_id": 1, "platform": "instagram", "reach": 900, "likes": 40, "comments": 6, "shares": 3, "saved": 5},
    {"db_id": 1, "platform": "facebook", "reactions": 20, "comments": 2, "shares": 1},
    {"db_id": 2, "platform": "instagram", "reach": 700, "likes": 10, "views": 1500},
    {"db_id": 3, "platform": "instagram", "reach": 300},
    {"db_id": 4, "platform": "instagram", "reach": 500, "likes": 12, "comments": 3},
]


def main():
    print("\n[ranking]")
    ranked = rl.rank_posts(ROWS, POSTS)
    check("posts are ranked best first", [r["post_id"] for r in ranked][0] == 1 and [r["post_id"] for r in ranked][-1] == 3, [r["post_id"] for r in ranked])
    check("Facebook and Instagram numbers for one post are added up",
          ranked[0]["comments"] == 8 and ranked[0]["shares"] == 4, ranked[0])
    check("a post nobody touched scores zero", [r for r in ranked if r["post_id"] == 3][0]["score"] < 1)

    print("\n[the note]")
    note = rl.learning_note(ranked, {"source": "meta", "clicks": 42, "ctr": 1.8})
    check("names the winning photos to reuse", "pool.jpg" in note and "kitchen.jpg" in note, note)
    check("asks for the winners in the ad", "creativeDays" in note)
    check("says the words must be new", "words must be new" in note)
    check("follows up the posts people commented on", "Where summer actually happens" in note and "message" in note)
    check("drops the angle nobody engaged with", "The details" in note.split("no interaction")[-1])
    check("reports the last ad's real clicks", "42 clicks" in note and "1.80%" in note)

    print("\n[never invents]")
    check("no numbers -> no note", rl.learning_note([], None) == "")
    zero = rl.rank_posts([{"db_id": 3, "platform": "instagram", "reach": 0}], POSTS)
    check("only zero-interaction posts -> no note", rl.learning_note(zero, None) == "")

    print("\n[previous_round_results]")
    first = asyncio.run(rl.previous_round_results(NS(repeat_round=0), object()))
    check("a first campaign learns nothing", not first["ok"] and "first campaign" in first["reason"])

    from app.services import insights
    real_o, real_a, real_prev = insights.organic_results, insights.ad_numbers, rl.previous_boost

    class FakeQuery:
        def __init__(self, rows): self.rows = rows
        def filter(self, *a, **k): return self
        def all(self): return self.rows

    class FakeDB:
        def query(self, model): return FakeQuery(list(POSTS.values()))

    async def unavailable(*a, **k):
        return {"source": "unavailable", "reason": "Meta is not connected"}

    async def meta(*a, **k):
        return {"source": "meta", "posts": ROWS}

    async def ad(*a, **k):
        return {"source": "meta", "clicks": 10, "ctr": 1.2}

    try:
        rl.previous_boost = lambda boost, db: NS(id=99, created_at=None)
        insights.organic_results, insights.ad_numbers = unavailable, ad
        res = asyncio.run(rl.previous_round_results(NS(repeat_round=1, id=100, user_id=1, address="x"), FakeDB()))
        check("Meta not connected -> builds as before, with the reason", not res["ok"] and "not connected" in res["reason"], res)

        insights.organic_results = meta
        res = asyncio.run(rl.previous_round_results(NS(repeat_round=1, id=100, user_id=1, address="x"), FakeDB()))
        check("real numbers -> a note for the plan", res["ok"] and "pool.jpg" in res["note"], res.get("reason"))
        check("and it remembers which campaign it learned from", res.get("previous_boost_id") == 99)

        async def boom(*a, **k):
            raise RuntimeError("graph down")
        insights.organic_results = boom
        res = asyncio.run(rl.previous_round_results(NS(repeat_round=1, id=100, user_id=1, address="x"), FakeDB()))
        check("a Meta failure never blocks the build", not res["ok"] and "RuntimeError" in res["reason"])
    finally:
        insights.organic_results, insights.ad_numbers, rl.previous_boost = real_o, real_a, real_prev

    print("\n" + "=" * 60)
    print("%d passed, %d failed" % (PASSED, FAILED))
    if FAILED:
        print("ROUND LEARNING TESTS FAILED")
        sys.exit(1)
    print("ALL ROUND LEARNING TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
