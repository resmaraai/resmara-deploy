"""The scheduler has a body: scripts/publish_due.py publishes a due post on its own.

Why this test exists: publishing used to happen only when something outside the app called
``POST /api/content/publish/run``. On Render there was no such caller, so a campaign could be
approved and scheduled and then simply never post. The cron job runs this script, so this test
runs the script the way Render does - as a separate process against the database - and checks a
due post actually changes state.

Run:
    cd /Users/dan/resmara && ./venv/bin/python3 tests/test_publish_cron.py
"""
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

_SCRATCH = "/Users/dan/.hermes/profiles/dev/cache/scratch"
if not os.path.isdir(_SCRATCH):
    _SCRATCH = tempfile.gettempdir()
TMP = tempfile.mkdtemp(prefix="resmara_cron_", dir=_SCRATCH)
DB_PATH = os.path.join(TMP, "cron.db")
os.environ["DATABASE_URL"] = "sqlite:///" + DB_PATH
os.environ["RESMARA_ENV"] = "test"
os.environ["RESMARA_SIMULATE"] = "1"
os.environ["RESMARA_PUBLIC_BASE_URL"] = "https://www.resmara.com"

from app.db.session import Base, engine, SessionLocal, User, AdAccount, Boost, Post  # noqa: E402

Base.metadata.create_all(bind=engine)
db = SessionLocal()

checks = []


def check(name, ok, detail=""):
    checks.append(bool(ok))
    print(f"{'ok  ' if ok else 'FAIL'} - {name}" + (f"  [{detail}]" if detail else ""))


PAST = (datetime.utcnow() - timedelta(minutes=5)).isoformat()
FUTURE = (datetime.utcnow() + timedelta(days=3)).isoformat()

user = User(email="cron@example.com", hashed_password="x", name="Cron")
db.add(user)
db.commit()
acct = AdAccount(user_id=user.id, platform="meta", advertiser_id="act_cron",
                 account_name="Cron", budget=100.0, is_active=True)
db.add(acct)
db.commit()
boost = Boost(user_id=user.id, ad_account_id=acct.id, address="1 Main St",
              stage="LIVE", main_status="Live")
db.add(boost)
db.commit()

due = Post(boost_id=boost.id, day=1, slot=1, kind="static", caption="due now",
           image_url="/uploads/due.jpg", client_status="approved",
           publish_status="scheduled", publish_at=PAST, publish_target="facebook")
later = Post(boost_id=boost.id, day=9, slot=1, kind="static", caption="not yet",
             image_url="/uploads/later.jpg", client_status="approved",
             publish_status="scheduled", publish_at=FUTURE, publish_target="facebook")
unapproved = Post(boost_id=boost.id, day=2, slot=1, kind="static", caption="unapproved",
                  image_url="/uploads/no.jpg", client_status="pending",
                  publish_status="scheduled", publish_at=PAST, publish_target="facebook")
db.add_all([due, later, unapproved])
db.commit()
due_id, later_id, unapproved_id = due.id, later.id, unapproved.id
db.close()

env = dict(os.environ)
env["PYTHONPATH"] = ROOT
env["DATABASE_URL"] = "sqlite:///" + DB_PATH

proc = subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "publish_due.py")],
                      capture_output=True, text=True, env=env, timeout=180, cwd=ROOT)
out = (proc.stdout or "").strip().splitlines()
payload = {}
for line in reversed(out):
    try:
        payload = json.loads(line)
        break
    except json.JSONDecodeError:
        continue

check("the script exits 0", proc.returncode == 0, f"rc={proc.returncode} err={(proc.stderr or '')[-200:]}")
check("it prints a JSON line", bool(payload), (proc.stdout or "")[:200])
check("it saw the due post", payload.get("checked") == 1, f"checked={payload.get('checked')}")
check("it posted it", payload.get("posted") == 1, f"posted={payload.get('posted')}")
check("nothing failed", payload.get("failed") == 0, f"failed={payload.get('failed')}")

db = SessionLocal()
due_row = db.query(Post).filter(Post.id == due_id).first()
later_row = db.query(Post).filter(Post.id == later_id).first()
unapproved_row = db.query(Post).filter(Post.id == unapproved_id).first()
check("the due post is no longer 'scheduled'", due_row.publish_status != "scheduled",
      f"status={due_row.publish_status}")
check("the future post is untouched", later_row.publish_status == "scheduled",
      f"status={later_row.publish_status}")
check("the unapproved post is untouched", unapproved_row.publish_status == "scheduled",
      f"status={unapproved_row.publish_status}")
db.close()

failed = checks.count(False)
print(f"\n{'FAILED ' + str(failed) if failed else 'ALL OK'} - {len(checks)} checks")
raise SystemExit(1 if failed else 0)
