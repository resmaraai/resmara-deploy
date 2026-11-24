"""The once-a-day campaign emails (Engines 6 and 8): reports on day 7 and 14, Run it again on day 12
and at the end, never twice, never for set-and-forget, pending or sold, and never old ones on a deploy."""
import os
import tempfile
from datetime import datetime, timedelta, timezone

_tmp = tempfile.NamedTemporaryFile(prefix="resmara-daily-", suffix=".db", delete=False)
_tmp.close()
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp.name}"
os.environ.pop("RESMARA_SIMULATE", None)

from app.db.session import Base, Boost, SessionLocal, User, engine  # noqa: E402
from app.services import campaign_daily, mail  # noqa: E402

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


db = SessionLocal()
u = User(email="morgan@example.com", hashed_password="x", name="Morgan Ellis")
db.add(u)
db.commit()
now = datetime.now(timezone.utc)


def camp(address, day, **kw):
    b = Boost(user_id=u.id, address=address, launched_at=now - timedelta(days=day), paid_at=now - timedelta(days=day),
              go_live_date=(now - timedelta(days=day - 1)).strftime("%Y-%m-%d"), campaign_days=14)
    for k, v in kw.items():
        setattr(b, k, v)
    db.add(b)
    db.commit()
    return b

d7 = camp("1 Seven St, Austin", 7)
d12 = camp("2 Twelve St, Austin", 12)
d12_auto = camp("3 Auto St, Austin", 12, until_sold=True)
d12_pend = camp("4 Pending St, Austin", 12, listing_status="pending")
d15 = camp("5 Done St, Austin", 15)
old = camp("6 Old St, Austin", 40)

campaign_daily.run(db)
subjects = [s[1] for s in SENT]
ok("day 7: the report email", "Your day 7 report for 1 Seven St" in subjects, subjects)
ok("day 12: Keep the momentum going", any("2 Twelve St" in s and "momentum" in s for s in subjects))
ok("not when Run it until it sells is on", not any("3 Auto St" in s and "momentum" in s for s in subjects))
ok("not when it's pending", not any("4 Pending St" in s and "momentum" in s for s in subjects))
ok("at the end, once more if they haven't acted", any("5 Done St" in s and "momentum" in s for s in subjects))
ok("day 14 report too", "Your day 14 report for 5 Done St" in subjects)
ok("never a stack of old ones on a deploy", not any("6 Old St" in s for s in subjects))
ok("the report email has its button", any("See your report:" in s[2] for s in SENT))
n = len(SENT)
campaign_daily.run(db)
ok("never twice", len(SENT) == n)
ok("day N skips paused days", campaign_daily.day_of(camp("7 Paused St, Austin", 10, paused_days=3)) == 7)

print(f"\n{checks} checks, {failures} failed.")
if failures:
    raise SystemExit(1)
print("ALL CAMPAIGN DAILY TESTS PASSED")
