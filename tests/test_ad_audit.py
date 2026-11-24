"""Engine 6, sections 3 and 5: the hook versions and the live ad audit, against a fake Meta.

1. At launch each hook version becomes its own ad in the ad set, tagged ad-hook-N for the website.
2. A hook far behind on clicks after a fair showing is paused and replaced; at most one swap a day,
   never in the last 2 days; frequency over 4 rotates one in.
3. Rejected by Meta: fixed and resubmitted once; rejected again, the team hears.
4. Not shown at all a day after go-live: the team hears once.
5. The budget, targeting and dates are never touched. Everything lands in the audit log.
"""
import asyncio
import io
import os
import tempfile
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-audit-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["RESMARA_ADMIN_EMAILS"] = "team@example.com"

from PIL import Image  # noqa: E402

from app.db.session import Ad, Asset, Base, Boost, Event, SessionLocal, User, engine  # noqa: E402
from app.services import ad_audit, mail  # noqa: E402

Base.metadata.create_all(bind=engine)
SENT = []
mail.send_email = lambda to, subject, body: SENT.append((to, subject, body)) or True
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


def png():
    buf = io.BytesIO()
    Image.new("RGB", (40, 50), "#336699").save(buf, "PNG")
    return buf.getvalue()


class FakeMeta:
    simulated = False

    def __init__(self):
        self.n = 0
        self.updates = []
        self.ads = {}          # ad id -> {"status", "insights", "feedback"}
        self.created = []

    async def upload_ad_image(self, data, filename):
        return {"hash": "h_" + filename}

    async def add_ad(self, adset_id, creative, ad):
        self.n += 1
        aid = f"ad_{self.n}"
        self.ads[aid] = {"status": "ACTIVE", "insights": {}, "feedback": {}}
        self.created.append((aid, creative))
        return {"creative": {"id": f"cr_{self.n}"}, "ad": {"id": aid}}

    async def get_object(self, object_id, fields):
        a = self.ads.get(object_id, {"status": "ACTIVE"})
        return {"effective_status": a["status"], "ad_review_feedback": a.get("feedback") or {}}

    async def get_ad_insights(self, ad_id, date_preset="lifetime"):
        return {"data": [self.ads.get(ad_id, {}).get("insights") or {}]}

    async def update_object(self, object_id, data):
        self.updates.append((object_id, data))
        if data.get("status") == "PAUSED" and object_id in self.ads:
            self.ads[object_id]["status"] = "PAUSED"
        return {"success": True}


db = SessionLocal()
u = User(email="morgan@example.com", hashed_password="x", name="Morgan Ellis")
db.add(u)
db.commit()
now = datetime.now(timezone.utc)
for i in range(1, 6):
    db.add(Asset(user_id=u.id, filename=f"hook{i}.png", url=f"/uploads/hook{i}.png", kind="design", data=png()))
db.commit()
hooks = [{"hook": f"Hook {i}", "primaryText": f"Text {i}", "headline": f"Head {i}",
          "images": {"4:5": f"/uploads/hook{i}.png"}} for i in (1, 2, 3)]
boost = Boost(user_id=u.id, address="1248 Oakridge Drive, Austin, TX", plan={"ad": {"hooks": hooks}},
              launched_at=now - timedelta(days=4), go_live_date=(now - timedelta(days=4)).strftime("%Y-%m-%d"),
              campaign_days=14, ad_budget_usd=100, destination_url="https://homes.resmara.com/1248-oakridge-drive",
              paid_at=now)
db.add(boost)
db.commit()
ad = Ad(boost_id=boost.id, kind="video", format="video", meta_ad_id="ad_main", meta_adset_id="adset_1",
        meta_creative_id="cr_main", status="scheduled")
db.add(ad)
db.commit()
meta = FakeMeta()
meta.ads["ad_main"] = {"status": "ACTIVE", "insights": {"impressions": 3000, "inline_link_clicks": 60}}

print("Hook versions at launch")
made = asyncio.run(ad_audit.add_hook_versions(db, boost, ad, meta, page_id="pg1", ig_id="ig1"))
ok("each hook is its own ad in the same ad set", len(made) == 3 and len(ad.versions) == 4)
ok("tagged so the website knows which hook sent a visitor",
   "utm_content=ad-hook-2" in meta.created[1][1]["object_story_spec"]["link_data"]["link"])
ok("runs as the agent's Page and Instagram", meta.created[0][1]["object_story_spec"]["page_id"] == "pg1"
   and meta.created[0][1]["object_story_spec"]["instagram_user_id"] == "ig1")

print("A weak hook is replaced")
meta.ads["ad_1"]["insights"] = {"impressions": 2000, "inline_link_clicks": 40, "frequency": 1.5, "spend": 10}
meta.ads["ad_2"]["insights"] = {"impressions": 2000, "inline_link_clicks": 30, "frequency": 1.5, "spend": 10}
meta.ads["ad_3"]["insights"] = {"impressions": 2000, "inline_link_clicks": 5, "frequency": 1.5, "spend": 10}


async def new_hook(b, avoid):
    return {"hook": "A new angle", "primaryText": "New text", "headline": "New head",
            "images": {"4:5": "/uploads/hook4.png"}}

res = asyncio.run(ad_audit.audit(db, boost, client=meta, now=now, new_hook=new_hook))
ok("the weak hook is paused", ("ad_3", {"status": "PAUSED"}) in meta.updates, meta.updates)
ok("and a fresh hook added", any(c[1]["name"].startswith("Hook 4") for c in meta.created))
lines = [e.payload["line"] for e in db.query(Event).filter(Event.event_type == "ad_audit").all()]
ok("the audit log says so, day by day", any(l.startswith("Day 5: hook 3 had few clicks, replaced with a new hook")
                                           for l in lines), lines)
ok("the agent isn't emailed about it", not [s for s in SENT if s[0] == "morgan@example.com"])
meta.ads["ad_2"]["insights"]["inline_link_clicks"] = 2
before = len(meta.created)
asyncio.run(ad_audit.audit(db, boost, client=meta, now=now + timedelta(hours=4), new_hook=new_hook))
ok("never more than one swap a day", len(meta.created) == before)
ok("the budget, targeting and dates are never touched",
   not any(k in d for _, d in meta.updates for k in ("lifetime_budget", "daily_budget", "targeting", "end_time")))

print("Frequency, and the last 2 days")
ad.audit = {}
db.commit()
meta.ads["ad_2"]["insights"] = {"impressions": 2000, "inline_link_clicks": 40, "frequency": 5.2}
for k in ("ad_1", "ad_4"):
    if k in meta.ads:
        meta.ads[k]["insights"] = {"impressions": 2000, "inline_link_clicks": 40, "frequency": 2}
late = Boost(user_id=u.id, address="9 Late Lane, Austin", go_live_date=(now - timedelta(days=13)).strftime("%Y-%m-%d"),
             campaign_days=14, launched_at=now - timedelta(days=13), plan={})
db.add(late)
db.commit()
late_ad = Ad(boost_id=late.id, kind="photo", meta_ad_id="ad_late", meta_adset_id="adset_2", audit={},
             versions=[{"kind": "hook", "n": 1, "meta_ad_id": "ad_x", "status": "active"},
                       {"kind": "hook", "n": 2, "meta_ad_id": "ad_y", "status": "active"}])
db.add(late_ad)
db.commit()
meta.ads["ad_x"] = {"status": "ACTIVE", "insights": {"impressions": 3000, "inline_link_clicks": 90}}
meta.ads["ad_y"] = {"status": "ACTIVE", "insights": {"impressions": 3000, "inline_link_clicks": 3}}
n_before = len(meta.created)
asyncio.run(ad_audit.audit(db, late, client=meta, now=now, new_hook=new_hook))
ok("never a swap in the last 2 days", len(meta.created) == n_before)
res = asyncio.run(ad_audit.audit(db, boost, client=meta, now=now + timedelta(days=1, hours=1), new_hook=new_hook))
ok("people seeing a hook too often rotates a new one in", any("too often" in c for c in res["changed"]), res)

print("Rejected by Meta")
SENT.clear()
target = next(v for v in ad.versions if v.get("kind") == "hook" and v.get("status") == "active")
meta.ads[target["meta_ad_id"]]["status"] = "DISAPPROVED"
meta.ads[target["meta_ad_id"]]["feedback"] = {"global": {"Housing": "Ad text mentions a protected group"}}
ad.audit = {"last_swap_at": now.isoformat()}
db.commit()
res = asyncio.run(ad_audit.audit(db, boost, client=meta, now=now + timedelta(days=1, hours=2), new_hook=new_hook))
ok("fixed and resubmitted once", any("fixed the wording and resubmitted" in c for c in res["changed"]), res)
ok("the lesson is kept for the rulebook", db.query(Event).filter(Event.event_type == "rulebook_lesson").count() == 1)
db.refresh(ad)
again = next(v for v in ad.versions if v.get("resubmitted") and v.get("status") == "active")
meta.ads[again["meta_ad_id"]]["status"] = "DISAPPROVED"
res = asyncio.run(ad_audit.audit(db, boost, client=meta, now=now + timedelta(days=1, hours=3), new_hook=new_hook))
ok("rejected again: the team hears, no endless loop", any(s[0] == "team@example.com" for s in SENT)
   and any("team is looking" in c for c in res["changed"]))

print("Not shown at all")
SENT.clear()
quiet = Boost(user_id=u.id, address="5 Quiet Court, Austin", go_live_date=(now - timedelta(days=2)).strftime("%Y-%m-%d"),
              campaign_days=14, launched_at=now - timedelta(days=3), plan={})
db.add(quiet)
db.commit()
db.add(Ad(boost_id=quiet.id, kind="photo", meta_ad_id="ad_q", meta_adset_id="adset_3", audit={}, versions=[]))
db.commit()
meta.ads["ad_q"] = {"status": "ACTIVE", "insights": {"impressions": 0}}
asyncio.run(ad_audit.audit(db, quiet, client=meta, now=now))
asyncio.run(ad_audit.audit(db, quiet, client=meta, now=now + timedelta(hours=4)))
ok("no impressions a day after go-live: the team hears once", len([s for s in SENT if "no impressions" in s[2]]) == 1)

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL AD AUDIT TESTS PASSED")
