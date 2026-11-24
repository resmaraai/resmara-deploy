"""The Meta connection engine (Engine 1 Parts B and C), tested against the spec's section 11.

1. One test per outcome key: fake Meta answers in, outcome key + capabilities + line + fix out.
2. Reconnect: the Page changes, Instagram becomes linked (the old `or` bug), held posts are released.
3. No ad account: the Page and Instagram are still saved and posts still go out.
4. One Page, one Resmara account.
5. A broken login holds due posts instead of failing them; past-due ones are never sent late.

Hermetic: temp sqlite DB and a local mock Graph server whose answers each scenario sets.
"""

import asyncio
import json
import os
import tempfile
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, urlparse

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-meta-engine-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)
os.environ["META_CLIENT_ID"] = "app_test_0000000000"
os.environ["META_CLIENT_SECRET"] = "secret_test_0000000000"

ALL_SCOPES = ["pages_show_list", "pages_manage_posts", "instagram_basic", "instagram_content_publish",
              "ads_management"]
WORLD = {}
POSTED = []


def world(**kw):
    """One agent's Meta, as the mock Graph will report it."""
    w = {"valid": True, "expires": 4102444800, "granted": list(ALL_SCOPES), "declined": [],
         "pages": [{"id": "pg1", "name": "Jamie Realty", "tasks": ["MANAGE", "CREATE_CONTENT"],
                    "is_published": True, "instagram_business_account": {"id": "ig1", "username": "jamierealty"}}],
         "ads": [{"id": "act_1", "name": "Jamie Ads", "account_status": 1, "funding_source_details": {"t": 1}}],
         "down": False}
    w.update(kw)
    WORLD.clear()
    WORLD.update(w)


class Graph(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):
        POSTED.append(urlparse(self.path).path)
        self._json({"id": "posted_1"})

    def do_GET(self):
        u = urlparse(self.path)
        q = {k: v[0] for k, v in parse_qs(u.query).items()}
        if WORLD.get("down"):
            return self._json({"error": {"message": "down"}}, 503)
        if u.path == "/oauth/access_token":
            return self._json({"access_token": "long-token", "expires_in": 5183944})
        if u.path == "/debug_token":
            return self._json({"data": {"is_valid": WORLD["valid"], "expires_at": WORLD["expires"]}})
        if not WORLD["valid"]:
            return self._json({"error": {"code": 190, "message": "Session has expired"}}, 400)
        if u.path == "/me":
            return self._json({"id": "fb_9", "name": "Jamie Agent"})
        if u.path == "/me/permissions":
            return self._json({"data": [{"permission": p, "status": "granted"} for p in WORLD["granted"]]
                               + [{"permission": p, "status": "declined"} for p in WORLD["declined"]]})
        if u.path == "/me/accounts":
            return self._json({"data": WORLD["pages"]})
        if u.path == "/me/adaccounts":
            return self._json({"data": WORLD["ads"]})
        return self._json({"error": {"message": "unexpected " + u.path}}, 404)

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


server = HTTPServer(("127.0.0.1", 0), Graph)
threading.Thread(target=server.serve_forever, daemon=True).start()
os.environ["GRAPH_API_BASE"] = f"http://127.0.0.1:{server.server_address[1]}"

from app.db.session import Base, engine, SessionLocal, User, Boost, Post, MetaConnection, AdAccount  # noqa: E402
from app.services import meta_engine, publisher  # noqa: E402
from app.api.onboarding import meta_connected, campaigns_allowed  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()
checks, failures = 0, 0


def ok(name, cond, extra=""):
    global checks, failures
    checks += 1
    print(("  PASS  " if cond else "  FAIL  ") + name + ("" if cond else f"  ({extra})"))
    if not cond:
        failures += 1


def run(coro):
    return asyncio.get_event_loop().run_until_complete(coro) if False else asyncio.run(coro)


_n = [0]


def agent(name="agent", unique=True):
    _n[0] += 1
    if unique:
        # Every test agent gets its own Pages: one Page can only belong to one Resmara account.
        for pg in WORLD.get("pages") or []:
            pg["id"] = pg["id"].split("~")[0] + f"~{_n[0]}"
    u = User(email=f"{name}{_n[0]}@example.com", hashed_password="x", name="Jamie Agent", facebook_id=f"fb{_n[0]}")
    db.add(u)
    db.commit()
    meta_engine.save_login(db, u, "user-token")
    db.commit()
    return u


def scenario(**kw):
    world(**kw)
    u = agent()
    return u, run(meta_engine.check(db, u, "connect"))


# ---------------------------------------------------------------- 1. one test per outcome key
print("Outcome keys")
u, st = scenario()
ok("ok: everything passes, no lines", st["issues"] == [] and st["lines"] == [], st["issues"])
ok("ok: posts to Facebook and Instagram and runs the ad",
   st["capabilities"]["fb_post"] and st["capabilities"]["ig_post"] and st["capabilities"]["ad"])
ok("ok: shows the Page and Instagram by name", st["page"]["name"] == "Jamie Realty"
   and st["instagram"]["username"] == "jamierealty" and st["ad_account"]["name"] == "Jamie Ads", st)
ok("ok: headline", st["headline"] == "You're all set. Resmara can post and run your ads.")
ok("ok: connected means a Page", meta_connected(db, u))

u, st = scenario(valid=False)
ok("token_dead: nothing posts, posts held", st["issues"] == ["token_dead"]
   and not st["capabilities"]["fb_post"] and st["capabilities"]["held"], st)
ok("token_dead: Fix it now is Reconnect", st["fix"]["kind"] == "reconnect")

u, st = scenario(expires=int((datetime.now(timezone.utc) + timedelta(days=3)).timestamp()))
ok("token_expiring: still works, asks for a refresh", st["issues"] == ["token_expiring"]
   and st["capabilities"]["fb_post"], st["issues"])

u, st = scenario(declined=["pages_manage_posts"], granted=[s for s in ALL_SCOPES if s != "pages_manage_posts"])
ok("scope_declined_page: download mode, re-ask in the dialog", st["issues"][0] == "scope_declined_page"
   and st["capabilities"]["download_mode"] and st["fix"] == {"kind": "dialog", "rerequest": True}, st["issues"])
ok("scope_declined_page: the 'turned off' line", "permission was turned off" in st["lines"][0]["line"])

u, st = scenario(granted=["public_profile", "email"])
ok("Page permissions never asked: honest line, same fix",
   st["issues"][0] == "scope_declined_page" and "needs your permission" in st["lines"][0]["line"], st["lines"])

u, st = scenario(pages=[])
ok("no_page: download mode, setup guide", st["issues"][0] == "no_page"
   and st["capabilities"]["download_mode"] and st["fix"]["kind"] == "setup", st["issues"])
ok("no_page: headline", st["headline"] == "Resmara can build everything, but can't post for you yet.")
ok("no_page: campaigns are still allowed", campaigns_allowed(db, u) and not meta_connected(db, u))

u, st = scenario(pages=[{"id": "pgx", "name": "Shared Page", "tasks": ["ANALYZE"], "is_published": True}])
ok("page_no_control", st["issues"][0] == "page_no_control" and not st["capabilities"]["fb_post"], st["issues"])

u, st = scenario(pages=[{"id": "pgu", "name": "Draft Page", "tasks": ["MANAGE"], "is_published": False}])
ok("page_unpublished", "page_unpublished" in st["issues"] and not st["capabilities"]["fb_post"], st["issues"])

two = [{"id": "pa", "name": "Jamie Personal Brand", "tasks": ["MANAGE"], "is_published": True},
       {"id": "pb", "name": "Jamie Team", "tasks": ["MANAGE"], "is_published": True,
        "instagram_business_account": {"id": "igb", "username": "jamieteam"}}]
u, st = scenario(pages=two)
ok("several_pages: asks which Page, lists both with the Instagram tag", st["issues"][0] == "several_pages"
   and len(st["pages"]) == 2 and st["pages"][1]["has_instagram"] and st["fix"]["kind"] == "page_picker", st)
ok("several_pages: headline is the question", st["headline"] == "Which Page is your business?")
res = meta_engine.set_page(db, u, next(p["id"] for p in st["pages"] if p["name"] == "Jamie Team"))
st = run(meta_engine.check(db, u, "check_again"))
ok("picking a Page saves it and re-checks", res["ok"] and st["page"]["name"] == "Jamie Team"
   and st["instagram"]["username"] == "jamieteam" and st["issues"] == [], st["issues"])
ok("an unknown Page can't be picked", meta_engine.set_page(db, u, "nope")["error"] == "unknown_page")

u, st = scenario(declined=["instagram_content_publish"])
ok("scope_declined_ig: Facebook and ad still work", st["issues"] == ["scope_declined_ig"]
   and st["capabilities"]["fb_post"] and not st["capabilities"]["ig_post"] and st["capabilities"]["ad"], st["issues"])

u, st = scenario(pages=[{"id": "pgn", "name": "No IG Page", "tasks": ["MANAGE"], "is_published": True}])
ok("ig_not_linked: Instagram switch pop-up", st["issues"] == ["ig_not_linked"] and st["fix"]["kind"] == "ig_switch"
   and "isn't connected as a business account" in st["lines"][0]["line"], st["issues"])

u, st = scenario(declined=["ads_management"])
ok("scope_declined_ads", st["issues"] == ["scope_declined_ads"] and st["capabilities"]["ig_post"]
   and not st["capabilities"]["ad"], st["issues"])

u, st = scenario(ads=[])
ok("no_ad_account: posts still go to Facebook and Instagram", st["issues"] == ["no_ad_account"]
   and st["capabilities"]["fb_post"] and st["capabilities"]["ig_post"] and not st["capabilities"]["ad"], st)
db.expire_all()
conn = meta_engine.connection_for(db, u.id)
ok("no_ad_account: the Page and Instagram are still saved (fix-first item 1)",
   (conn.page_id or "").startswith("pg1") and conn.ig_user_id == "ig1", (conn.page_id, conn.ig_user_id))
ok("no_ad_account: connected (fix-first item 5)", meta_connected(db, u))

for status, funding, key in [(1, None, "ad_no_payment"), (2, {"t": 1}, "ad_disabled"),
                             (101, {"t": 1}, "ad_disabled"), (3, {"t": 1}, "ad_unpaid"),
                             (8, {"t": 1}, "ad_unpaid"), (7, {"t": 1}, "ad_in_review"),
                             (9, {"t": 1}, "ad_in_review")]:
    acct = {"id": "act_s", "name": "Ads", "account_status": status}
    if funding:
        acct["funding_source_details"] = funding
    u, st = scenario(ads=[acct])
    ok(f"{key} (status {status}): posts go out, ad is off", st["issues"] == [key]
       and st["capabilities"]["fb_post"] and not st["capabilities"]["ad"], st["issues"])
u, st = scenario(ads=[{"id": "act_q", "name": "Ads", "account_status": 1}])
ok("ad_no_payment opens the ad account setup step", st["fix"] == {"kind": "setup", "step": "ads"})
u, st = scenario(ads=[{"id": "act_d", "name": "Ads", "account_status": 2, "funding_source_details": {"t": 1}}])
ok("ad_disabled opens Book a call", st["fix"]["kind"] == "book")
u, st = scenario(ads=[{"id": "act_w", "name": "Ads", "account_status": 42, "funding_source_details": {"t": 1}}])
ok("an unknown ad status never alarms", st["issues"] == [] and not st["capabilities"]["ad"], st["issues"])

u, st = scenario()
world(down=True)
st2 = run(meta_engine.check(db, u, "check_again"))
ok("meta_unreachable: nothing changes for the agent, no notice",
   st2["issues"] == st["issues"] and st2["capabilities"]["fb_post"] and st2["checking_unavailable"], st2)
db.expire_all()
ok("meta_unreachable: remembered for the 6-hour Team room alert",
   meta_engine.connection_for(db, u.id).unreachable_since is not None)

print("Several issues at once")
u, st = scenario(pages=[{"id": "pgm", "name": "No IG", "tasks": ["MANAGE"], "is_published": True}], ads=[],
                 expires=int((datetime.now(timezone.utc) + timedelta(days=2)).timestamp()))
ok("at most three lines, most important first",
   [l["key"] for l in st["lines"]] == ["token_expiring", "ig_not_linked", "no_ad_account"], st["issues"])
ok("Fix it now opens the first one", st["fix"]["kind"] == "reconnect")
d = meta_engine.decide({"token_valid": True, "pages": [], "ad_accounts": []})
ok("no Page and no ad account together", d["issues"] == ["no_page", "no_ad_account"], d["issues"])
ok("page_no_control hidden when no_page is present",
   "page_no_control" not in meta_engine.decide({"token_valid": True, "pages": []})["issues"])
ok("four problems still show three lines", len(meta_engine.lines(
    ["token_expiring", "page_unpublished", "ig_not_linked", "no_ad_account"])) == 3)

# ---------------------------------------------------------------- 2. reconnect overwrites
print("Reconnect")
u, st = scenario(pages=[{"id": "pgr", "name": "Old Page", "tasks": ["MANAGE"], "is_published": True}])
ok("starts without Instagram", st["issues"] == ["ig_not_linked"])
world(pages=[{"id": f"pgr~{_n[0]}", "name": "Old Page", "tasks": ["MANAGE"], "is_published": True,
              "instagram_business_account": {"id": "ig_new", "username": "nowbusiness"}}])
st = run(meta_engine.check(db, u, "check_again"))
ok("Check again picks up a newly linked Instagram (the `or` bug is gone)",
   st["instagram"] and st["instagram"]["username"] == "nowbusiness" and st["issues"] == [], st)
world(pages=[{"id": f"pg_moved~{_n[0]}", "name": "New Page", "tasks": ["MANAGE"], "is_published": True}])
meta_engine.save_login(db, u, "fresh-token")
st = run(meta_engine.check(db, u, "connect"))
ok("Reconnect changes the Page and drops the stale Instagram",
   st["page"]["name"] == "New Page" and st["instagram"] is None, st)
db.expire_all()
rows = db.query(AdAccount).filter(AdAccount.user_id == u.id).all()
ok("the ad account rows follow the new Page", rows and all(r.page_id == st["page"]["id"] for r in rows),
   [(r.page_id) for r in rows])

# ---------------------------------------------------------------- 3. the setup to-do list
print("Setup to-do list")
u, st = scenario(ads=[])
ok("what's missing is on the list", [t["key"] for t in st["todo"]] == ["no_ad_account"], st["todo"])
world()
st = run(meta_engine.check(db, u, "check_again"))
ok("the next check that passes ticks it off, with when", st["todo"] == []
   and st["done"] and st["done"][-1]["key"] == "no_ad_account" and st["done"][-1]["fixed_at"], st["done"])

# ---------------------------------------------------------------- 4. one Page, one account
print("One Page, one account")
world(pages=[{"id": "shared_pg", "name": "Brokerage Page", "tasks": ["MANAGE"], "is_published": True}])
first = agent(unique=False)
run(meta_engine.check(db, first, "connect"))
second = agent(unique=False)
st = run(meta_engine.check(db, second, "connect"))
ok("a second account can't connect a Page that's already connected", st["issues"][0] == "page_taken"
   and "already connected to another Resmara account" in st["lines"][0]["line"]
   and not st["capabilities"]["fb_post"], st["issues"])
db.expire_all()
ok("  ...and the Page isn't saved on the second account", meta_engine.connection_for(db, second.id).page_id is None)
ok("  ...and the first account keeps it", meta_engine.connection_for(db, first.id).page_id == "shared_pg")

# ---------------------------------------------------------------- 5. held posts and the publisher
print("Posting")


def campaign(user, *, hours_ago):
    b = Boost(user_id=user.id, address="1 Test St", stage="LIVE")
    db.add(b)
    db.commit()
    p = Post(boost_id=b.id, day=1, client_status="approved", publish_status="scheduled",
             publish_target="facebook", caption="Hello",
             publish_at=(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=hours_ago)).isoformat())
    db.add(p)
    db.commit()
    return b, p


world(ads=[])
u = agent()
run(meta_engine.check(db, u, "connect"))
b, p = campaign(u, hours_ago=1)
POSTED.clear()
os.environ["RESMARA_SIMULATE"] = ""
from app.core.config import settings  # noqa: E402
settings.SIMULATE = False
res = run(publisher.publish_due(db, limit=50, boost_id=b.id))
db.refresh(p)
ok("an agent with no ad account still posts (fix-first item 4)", p.publish_status == "posted"
   and any("/feed" in x or "/photos" in x for x in POSTED), (p.publish_status, POSTED, res["details"]))

world(valid=False)
u2 = agent()
b2, p_recent = campaign(u2, hours_ago=2)
p_old = Post(boost_id=b2.id, day=2, client_status="approved", publish_status="scheduled", publish_target="facebook",
             caption="Old", publish_at=(datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=3)).isoformat())
db.add(p_old)
db.commit()
run(meta_engine.check(db, u2, "connect"))
db.refresh(p_recent)
db.refresh(p_old)
ok("a broken login holds due posts, not fails them", p_recent.publish_status == "held" and p_old.publish_status == "held",
   (p_recent.publish_status, p_old.publish_status))
world()
meta_engine.save_login(db, u2, "reconnected-token")
run(meta_engine.check(db, u2, "connect"))
db.refresh(p_recent)
db.refresh(p_old)
ok("reconnecting sends the held post", p_recent.publish_status == "scheduled", p_recent.publish_status)
ok("a post held for days is never sent late", p_old.publish_status == "failed"
   and "Missed while your Meta connection was off" in (p_old.failure_note or ""), p_old.publish_status)

world(pages=[])
u3 = agent()
run(meta_engine.check(db, u3, "connect"))
b3, p3 = campaign(u3, hours_ago=1)
run(publisher.publish_due(db, limit=50, boost_id=b3.id))
db.refresh(p3)
ok("download mode: nothing is sent, the post stays to download", p3.publish_status == "download", p3.publish_status)

# ---------------------------------------------------------------- 6. after-onboarding breakage emails
print("Breakage emails")
c = MetaConnection(user_id=u.id, issues=["token_dead"],
                   issue_log=[{"key": "token_dead", "found_at": (datetime.now(timezone.utc) - timedelta(days=4)).isoformat(),
                               "fixed_at": None}], breakage_emails={})
now = datetime.now(timezone.utc)
ok("sent once when it happens", meta_engine.breakage_emails_due(c, True, now) == ["token_dead"])
c.breakage_emails = {"token_dead": [(now - timedelta(days=4)).isoformat()]}
ok("then again on day 3", meta_engine.breakage_emails_due(c, True, now) == ["token_dead"])
c.breakage_emails = {"token_dead": [(now - timedelta(days=4)).isoformat(), (now - timedelta(days=1)).isoformat()]}
ok("not again before day 7", meta_engine.breakage_emails_due(c, True, now) == [])
ok("never without a live campaign", meta_engine.breakage_emails_due(c, False, now) == [])
c.issues = ["ig_not_linked"]
ok("never for things they saw at sign-up", meta_engine.breakage_emails_due(c, True, now) == [])

server.shutdown()
print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL META ENGINE TESTS PASSED")
