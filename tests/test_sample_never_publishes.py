"""A sample campaign is never published.

The demo book on the sample account (resmaraai@gmail.com) is an illustration: real photos, real
looking posts, nothing that should ever reach a customer's Facebook Page. The scheduler sweeps
every approved, due post, so without this guard a demo campaign would be handed to Meta (or fail
loudly on the calendar) the moment its schedule came due.

Run:
    cd /Users/dan/resmara && PYTHONPATH=/Users/dan/resmara venv/bin/python tests/test_sample_never_publishes.py
"""
import asyncio
import os
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_SCRATCH = "/Users/dan/.hermes/profiles/dev/cache/scratch"
if not os.path.isdir(_SCRATCH):
    _SCRATCH = tempfile.gettempdir()
TMP = tempfile.mkdtemp(prefix="resmara_sample_", dir=_SCRATCH)
os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(TMP, "sample.db")
os.environ["RESMARA_ENV"] = "test"

from app.services import publisher  # noqa: E402
from app.db.session import Base, engine, SessionLocal, AdAccount, Boost, Post, User  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()
NOW = "2030-01-01T00:00:00"
LATER = "2030-06-01T00:00:00"
checks = []


def check(name, ok, detail=""):
    checks.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'} - {name}" + (f"  [{detail}]" if detail else ""))


user = User(email="sample@example.com", hashed_password="x", name="Sample")
db.add(user)
db.commit()
# A publishable account: the scheduler only looks at posts whose owner has a connection or an
# active ad account. That is what makes the demo post *due* - the guard is what stops it.
acct = AdAccount(user_id=user.id, platform="meta", advertiser_id="act_sample",
                 account_name="Sample", budget=100.0, is_active=True)
db.add(acct)
db.commit()


def mk_boost(addr, sample):
    b = Boost(user_id=user.id, ad_account_id=acct.id, address=addr, stage="LIVE", main_status="Active",
              plan={"_sample": True} if sample else {"summary": "real"})
    db.add(b)
    db.commit()
    return b


def mk_post(b, day, at=NOW):
    p = Post(boost_id=b.id, day=day, slot=1, kind="static", caption="c",
             client_status="approved", publish_status="scheduled", publish_at=at,
             publish_target="both")
    db.add(p)
    db.commit()
    return p


demo = mk_boost("1 Demo St", True)
real = mk_boost("2 Real St", False)
demo_post = mk_post(demo, 1)
# The real campaign's post is not due yet, so this run only ever has the demo post to consider -
# a unit test must not try to reach Meta.
mk_post(real, 1, at=LATER)

check("only the demo post is due for this run", len(publisher._due_posts(db, NOW, 50)) == 1)

result = asyncio.run(publisher.publish_due(db, now=NOW))
db.refresh(demo_post)

check("the demo post was skipped, not published", result["skipped"] == 1 and result["posted"] == 0,
      str(result["details"]))
check("the demo post keeps its schedule (nothing red on its calendar)",
      demo_post.publish_status == "scheduled", demo_post.publish_status)
check("the demo post was never attempted", demo_post.failure_kind is None,
      str(demo_post.failure_kind))
check("the sample skip is named in the run's details",
      any(d.get("status") == "sample" for d in result["details"]))

print(f"\n{sum(checks)} passed, {len(checks) - sum(checks)} failed")
print("ALL SAMPLE-PUBLISH CHECKS PASSED" if all(checks) else "SAMPLE-PUBLISH CHECKS FAILED")
sys.exit(0 if all(checks) else 1)
