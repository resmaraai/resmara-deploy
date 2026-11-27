"""The Day 7 / Day 14 report downloads as a real PDF (owner item 12).

"Day 7 and Day 14 inline with Download PDF." The download used to return the JSON payload, which
is not a file an agent can send to their seller. These tests open the bytes and check that it is
a PDF a viewer will accept - header, xref, trailer, one page - and that the numbers in the file are
the numbers on the page, including the honest "Not measured" when Meta has said nothing.
"""
import os
import re
import sys
import tempfile
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_DIR = tempfile.mkdtemp(prefix="pdf-")
os.environ["RESMARA_DB"] = os.path.join(DB_DIR, "app.db")
os.environ["DATABASE_URL"] = f"sqlite:///{os.path.join(DB_DIR, 'app.db')}"
os.environ["RESMARA_UPLOAD_DIR"] = os.path.join(DB_DIR, "uploads")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from app.services.report_pdf import campaign_report_pdf  # noqa: E402

FAILS = []


def check(name, ok, detail=""):
    print(("ok   " if ok else "FAIL ") + name + (f"  [{detail}]" if detail and not ok else ""))
    if not ok:
        FAILS.append(name)


def text_of(pdf: bytes) -> str:
    """Pull the strings out of the content streams - enough to prove the words are in the file."""
    out = []
    for m in re.finditer(rb"\((.*?)\)\s*Tj", pdf, re.S):
        out.append(m.group(1).replace(b"\\(", b"(").replace(b"\\)", b")").decode("latin-1"))
    return "\n".join(out)


print("=== the payload the page shows becomes a PDF ===")
payload = {
    "address": "123 Elm St, Austin TX",
    "report_day": 7,
    "period": {"from": "2026-11-15", "to": "2026-11-21", "label": "Day 1 to Day 7"},
    "posts": {"total": 14, "published": 7, "approved": 14},
    "ads": {"total": 1, "live": 1},
    "organic": {"ok": True, "summary": {"measured": 7, "posts": 7, "reach": 1840,
                                        "interactions": 96}},
    "paid": {"ok": True, "impressions": 9120, "clicks": 141, "link_clicks": 118, "spend": "31.40"},
}
pdf = campaign_report_pdf(payload)
check("the bytes start with a PDF header", pdf.startswith(b"%PDF-1.4"), pdf[:12])
check("  ...and end with the EOF marker", pdf.rstrip().endswith(b"%%EOF"))
check("  ...and carry an xref table", b"\nxref\n" in pdf)
check("  ...and a trailer pointing at the catalog", b"/Type /Catalog" in pdf and b"trailer" in pdf)
check("  ...and exactly one page", pdf.count(b"/Type /Page ") == 1, str(pdf.count(b"/Type /Page ")))

words = text_of(pdf)
check("the address is in the file", "123 Elm St, Austin TX" in words, words[:200])
check("  ...and the day", "Day 7 report" in words, words[:200])
check("  ...and the period", "Day 1 to Day 7" in words)
check("  ...and the real numbers", "Reach: 1,840" in words and "Engagement: 96" in words, words[:400])
check("  ...and the spend, labelled as Meta's", "Ad spend: $31.40" in words, words[-400:])

print("\n=== nothing measured says so, and never says zero ===")
quiet = dict(payload)
quiet["organic"] = {"ok": False, "reason": "Meta not connected yet (no usable access token)"}
quiet["paid"] = {"ok": False, "reason": "No Meta ad account connected"}
pdf2 = campaign_report_pdf(quiet)
words2 = text_of(pdf2)
check("reach not shared by Meta shows as a dash, never a guess (Engine 6, section 9)", "Reach: -" in words2, words2[:400])
check("  ...with Meta's own reason", "no usable access token" in words2, words2[:400])
check("  ...and no invented zero reaches the page",
      "Reach: 0" not in words2 and "Interactions: 0" not in words2, words2[:400])

print("\n=== text that would break the file is escaped ===")
nasty = dict(payload, address="42 O'Neil (Back)\\Lot, Austin TX")
pdf3 = campaign_report_pdf(nasty)
check("a bracket and a backslash do not unbalance the file",
      pdf3.count(b"(") == pdf3.count(b")"), f"{pdf3.count(b'(')} vs {pdf3.count(b')')}")
check("  ...and the address survives", "O'Neil (Back)" in text_of(pdf3), text_of(pdf3)[:200])

print("\n=== the route serves it as a download ===")
with TestClient(app) as client:
    client.post("/api/auth/register", json={"terms_accepted": True, "email": "rep@example.com", "password": "long enough",
                                            "name": "Reporter"})
    token = client.post("/api/auth/login",
                        data={"username": "rep@example.com", "password": "long enough"}
                        ).json()["access_token"]
    h = {"Authorization": f"Bearer {token}"}
    from app.db.session import Boost, SessionLocal, User
    db = SessionLocal()
    user = db.query(User).filter(User.email == "rep@example.com").first()
    user.meta_connected_at = datetime.now(timezone.utc)
    db.commit()
    boost = Boost(user_id=user.id, address="7 Report Row, Austin TX", campaign_days=14,
                  go_live_date=datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    db.add(boost)
    db.commit()
    bid = boost.id
    db.close()

    r = client.get(f"/api/content/reports/{bid}/download?day=7", headers=h)
    check("the download returns 200", r.status_code == 200, r.text[:200])
    check("  ...as application/pdf", r.headers.get("content-type", "").startswith("application/pdf"),
          r.headers.get("content-type"))
    check("  ...as an attachment with a name that says the day",
          "attachment" in (r.headers.get("content-disposition") or "")
          and "Day 7" in (r.headers.get("content-disposition") or ""),
          r.headers.get("content-disposition"))
    check("  ...and the body is a PDF", r.content.startswith(b"%PDF-1.4"), r.content[:12])

    r14 = client.get(f"/api/content/reports/{bid}/download?day=14", headers=h)
    check("day 14 downloads too", r14.status_code == 200 and r14.content.startswith(b"%PDF-1.4"),
          r14.text[:120] if r14.status_code != 200 else "")
    check("  ...and it says day 14", "Day 14 report" in text_of(r14.content))

    seller = client.get(f"/api/content/reports/{bid}/download?day=7&version=seller", headers=h)
    st = text_of(seller.content).lower()
    check("the seller version downloads", seller.status_code == 200 and "marketing report" in st, st[:200])
    check("  ...with no cost, spend or cost per click anywhere", "spend" not in st and "cost" not in st and "$" not in st, st[:400])

    js = client.get(f"/api/content/reports/{bid}/download?day=7&fmt=json", headers=h)
    check("fmt=json still gives the old payload", js.status_code == 200 and "report_day" in js.text,
          js.text[:120])

    other = client.get(f"/api/reports/{bid + 999}/download", headers=h)
    check("someone else's report is not downloadable", other.status_code in (403, 404),
          str(other.status_code))

print()
if FAILS:
    print(f"{len(FAILS)} FAILED: " + "; ".join(FAILS))
    raise SystemExit(1)
print("ALL REPORT PDF TESTS PASSED")
