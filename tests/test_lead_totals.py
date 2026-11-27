"""Lead totals and lead notes (PR #17, 21 Nov 2026).

What this proves, in the customer's terms:

  * a campaign's lead count is a record: removing a lead from the list, or ticking it off,
    does not lower how many leads the campaign generated;
  * leads are counted by where they came from: the ad, the posts, the listing page;
  * the agent can save a note on a lead, change it, and clear it, without touching its status;
  * the Team room's campaign row carries the same totals and the campaign's last day.

Run:
    cd /Users/dan/resmara && PYTHONPATH=. venv/bin/python tests/test_lead_totals.py
"""
import os
import sys
import tempfile

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-lead-totals-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ["RESMARA_ADMIN_EMAILS"] = "owner@example.com"
os.environ["RESMARA_SIGNUP_CODE"] = "beta-code-123"
os.environ["RESMARA_SIGNUP_EMAILS"] = ""
for _key in ("RESEND_API_KEY", "SMTP_HOST", "OPENAI_API_KEY", "RESMARA_ENGINE_BASE_URL"):
    os.environ.pop(_key, None)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402
from app.db.session import Base, engine, SessionLocal, Boost, Lead, User  # noqa: E402
from app.db.migrate import migrate  # noqa: E402
from app.services.lead_counts import bucket_of, lead_totals  # noqa: E402
from app.api.console import _ends_on  # noqa: E402

Base.metadata.create_all(bind=engine)
migrate()
client = TestClient(app)
FAILS = []


def check(name, ok):
    print(("PASS " if ok else "FAIL ") + name)
    if not ok:
        FAILS.append(name)


client.post("/api/auth/register", json={"terms_accepted": True, "email": "agent@example.com", "password": "long enough",
                                       "name": "Dana Agent", "invite_code": "beta-code-123"})
token = client.post("/api/auth/login", data={"username": "agent@example.com",
                                            "password": "long enough"}).json()["access_token"]
agent = {"Authorization": f"Bearer {token}"}

db = SessionLocal()
user = db.query(User).filter(User.email == "agent@example.com").first()
boost = Boost(user_id=user.id, address="1248 Oakridge Drive", go_live_date="2026-11-16",
              campaign_days=14, ad_budget_usd=50.0)
db.add(boost)
db.commit()
BID = boost.id
rows = [
    ("instagram", "Instagram", "comment", "new"),
    ("facebook", "Facebook", "comment", "removed"),
    ("facebook", "Facebook ad", "ad_comment", "handled"),
    ("facebook", "Facebook ad", "ad_comment", "removed"),
    ("web", "Listing page form", "form", "new"),
    ("web", "Listing page call button", "call", "new"),
]
for i, (platform, channel, source, status) in enumerate(rows):
    db.add(Lead(boost_id=BID, user_id=user.id, platform=platform, channel=channel, source=source,
                status=status, platform_comment_id=f"c{i}", author_name=f"Person {i}", text="Is it available?"))
db.commit()
first_id = db.query(Lead).filter(Lead.boost_id == BID).order_by(Lead.id).first().id
db.close()

# buckets
check("ad comment counts as the ad", bucket_of("ad_comment", "Facebook ad") == "ad")
check("manual lead from the ad counts as the ad", bucket_of("manual", "Facebook ad") == "ad")
check("form counts as the website", bucket_of("form", None) == "website")
check("a post comment counts as the posts", bucket_of("comment", "Instagram") == "posts")

# totals keep removed and handled leads
db = SessionLocal()
t = lead_totals(db, [BID])[BID]
db.close()
check("totals by source", (t["ad"], t["posts"], t["website"]) == (2, 2, 2))
check("total includes removed and handled", t["total"] == 6 and t["removed"] == 2)

listing = client.get(f"/api/boosts/{BID}/leads", headers=agent).json()
check("list hides removed rows", len(listing["leads"]) == 4)
check("list still reports the full totals", listing["totals"]["total"] == 6)

# removing another lead does not lower the total
client.delete(f"/api/leads/{first_id}", headers=agent)
after = client.get(f"/api/boosts/{BID}/leads", headers=agent).json()["totals"]
check("removing a lead keeps the total", after["total"] == 6 and after["removed"] == 3)

# notes
r = client.patch(f"/api/leads/{first_id}", headers=agent, json={"note": "  Called back, showing Saturday  "})
check("note saves (trimmed)", r.status_code == 200 and r.json()["note"] == "Called back, showing Saturday")
check("saving a note leaves the status alone", r.json()["status"] == "removed")
r = client.patch(f"/api/leads/{first_id}", headers=agent, json={"note": ""})
check("an empty note clears it", r.json()["note"] is None)
r = client.patch(f"/api/leads/{first_id}", headers=agent, json={})
check("an empty update is refused", r.status_code == 422)
r = client.patch(f"/api/leads/{first_id}", headers=agent, json={"status": "handled"})
check("status alone still works", r.status_code == 200 and r.json()["status"] == "handled")

# Team room row
db = SessionLocal()
b = db.query(Boost).filter(Boost.id == BID).first()
check("last day = go-live + 13", _ends_on(b) == "2026-11-29")
db.close()

print()
print("ALL PASSED" if not FAILS else f"{len(FAILS)} FAILED: {FAILS}")
sys.exit(1 if FAILS else 0)
