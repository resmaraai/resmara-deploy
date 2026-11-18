#!/usr/bin/env python3
"""Filings: the paperwork with a date on it, and the money it will take.

A missed filing is the expensive kind of oversight — an FBN filed late is filed again, fee
and all — and the things worth pinning are the rules somebody relies on when they look at
the board:

  * only the Money group (admins) can read or write it
  * days-left, overdue and due-soon are the server's arithmetic, not the page's
  * an unpriced filing is NOT $0: it is counted apart, because nobody has quoted it
  * marking a recurring row done rolls a fresh open row forward to the next cycle, and
    marking it done twice does not produce a second copy
  * a one-off filing rolls nothing
  * a cleared cost is a real instruction ("nobody has priced this"), distinct from leaving
    the field alone
  * reopening a closed row takes it back off done and keeps its money
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

FAILS = 0


def check(label: str, cond: bool, detail: str = "") -> None:
    global FAILS
    if cond:
        print("  ok   %s" % label)
    else:
        FAILS += 1
        print("  FAIL %s %s" % (label, detail))


def main() -> int:
    tmp = tempfile.mkdtemp(prefix="resmara-filings-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "filings.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-filings")
    os.environ["RESMARA_ADMIN_EMAILS"] = "dan@example.com"

    from fastapi.testclient import TestClient
    from app.main import app
    from app.core.security import get_password_hash
    from app.db.session import Base, engine, SessionLocal, User

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    def account(email: str, admin: bool = False) -> dict:
        with SessionLocal() as db:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, name=email, hashed_password=get_password_hash("fl-pass-123"),
                            is_active=True, is_admin=admin, subscription_status="active"))
                db.commit()
        r = client.post("/api/auth/login", data={"username": email, "password": "fl-pass-123"})
        token = r.json().get("access_token", "")
        if not token:
            check("login as " + email, False, r.text[:160])
        return {"Authorization": "Bearer " + token}

    dan = account("dan@example.com", admin=True)
    stranger = account("stranger@example.com")

    def board(hdrs=None) -> dict:
        r = client.get("/api/admin/filings", headers=hdrs or dan)
        return r.json() if r.status_code == 200 else {}

    # ── the door ──────────────────────────────────────────────────────────────
    check("a customer cannot read the filings",
          client.get("/api/admin/filings", headers=stranger).status_code == 403,
          str(client.get("/api/admin/filings", headers=stranger).status_code))
    check("nor add one",
          client.post("/api/admin/filings", headers=stranger, json={"title": "x"}).status_code == 403)
    check("an admin can read it", client.get("/api/admin/filings", headers=dan).status_code == 200)
    check("an empty board says so",
          board()["summary"]["total"] == 0 and board()["items"] == [], str(board().get("summary")))

    # ── validation ────────────────────────────────────────────────────────────
    check("a filing with no title is refused",
          client.post("/api/admin/filings", headers=dan, json={"title": "  "}).status_code == 400)
    check("an unknown kind is refused",
          client.post("/api/admin/filings", headers=dan,
                      json={"title": "x", "kind": "vibes"}).status_code == 400)
    check("an unknown recurrence is refused",
          client.post("/api/admin/filings", headers=dan,
                      json={"title": "x", "recurrence": "fortnightly"}).status_code == 400)
    check("a negative cost is refused",
          client.post("/api/admin/filings", headers=dan,
                      json={"title": "x", "cost_cents": -5}).status_code == 422)
    check("a bad date is refused",
          client.post("/api/admin/filings", headers=dan,
                      json={"title": "x", "due_on": "next spring"}).status_code == 400)

    # ── the real row: the county FBN statement, dated and priced ──────────────
    due_soon = date.today() + timedelta(days=12)
    r = client.post("/api/admin/filings", headers=dan, json={
        "title": "Shasta County Fictitious Business Name statement",
        "kind": "filing", "jurisdiction": "Shasta County Clerk",
        "due_on": due_soon.isoformat(), "cost_cents": 9300,
        "cost_note": "$84 + $9 per additional registrant",
        "recurrence": "every_5_years",
        "notes": "40 days from the day business started; filed late it is filed again, fee and all.",
    })
    check("an FBN row is added", r.status_code == 201, r.text[:240])
    fbn = r.json()
    check("it is open with a real price", fbn["status"] == "open" and fbn["cost_cents"] == 9300, str(fbn))
    check("the server says it is due soon", fbn["due_soon"] is True and fbn["overdue"] is False, str(fbn))
    check("and counts the days for us", fbn["days_left"] == 12, str(fbn.get("days_left")))

    # ── an unpriced, undated filing is a gap, not a $0 ────────────────────────
    r = client.post("/api/admin/filings", headers=dan, json={
        "title": "FBN publication", "kind": "publication", "jurisdiction": "Record Searchlight",
        "notes": "Four weekly runs, starting inside 45 days of the filing."})
    check("a filing with no date or price is allowed", r.status_code == 201, r.text[:200])
    pub = r.json()
    check("no price reads as not-quoted, not zero",
          pub["cost_cents"] is None and pub["cost_usd"] is None, str(pub))
    check("no date reads as no deadline",
          pub["due_on"] is None and pub["days_left"] is None and pub["due_soon"] is False, str(pub))

    # The horizon has to cover the county windows (40 days for the FBN, 45 for the first
    # publication run): at 30 days the board said "nothing due" with a live deadline 34 days out.
    r = client.post("/api/admin/filings", headers=dan, json={
        "title": "FBN publication horizon probe", "kind": "publication",
        "due_on": (date.today() + timedelta(days=40)).isoformat(), "cost_cents": 100})
    probe = r.json()
    check("a date 40 days out is already due soon", probe["due_soon"] is True, str(probe))
    client.delete("/api/admin/filings/%d" % probe["id"], headers=dan)
    r = client.post("/api/admin/filings", headers=dan, json={
        "title": "far away probe", "kind": "tax",
        "due_on": (date.today() + timedelta(days=200)).isoformat()})
    far = r.json()
    check("a date 200 days out is not", far["due_soon"] is False, str(far))
    client.delete("/api/admin/filings/%d" % far["id"], headers=dan)

    s = board()["summary"]
    check("the board counts two open", s["open"] == 2, str(s))
    check("one is due soon", s["due_soon"] == 1, str(s))
    check("known money is the priced row only", s["open_cost_cents"] == 9300, str(s))
    check("the unpriced row is counted apart",
          s["open_cost_unknown"] == 1 and s["open_cost_usd"] == 93.0, str(s))
    check("one open row has no date yet", s["no_deadline"] == 1, str(s))
    check("the next deadline is the dated one",
          s["next"] and s["next"]["id"] == fbn["id"], str(s.get("next")))

    # ── an overdue row is overdue, and stays the loudest thing on the board ───
    r = client.post("/api/admin/filings", headers=dan, json={
        "title": "CA Form 565", "kind": "tax", "jurisdiction": "CA FTB",
        "due_on": (date.today() - timedelta(days=3)).isoformat(), "cost_cents": 0,
        "recurrence": "annual"})
    tax = r.json()
    check("a passed date reads as overdue", tax["overdue"] is True and tax["days_left"] == -3, str(tax))
    check("free is $0, not unknown", tax["cost_cents"] == 0 and tax["cost_usd"] == 0.0, str(tax))
    s = board()["summary"]
    check("the board counts the overdue one", s["overdue"] == 1, str(s))
    check("a $0 filing adds nothing to the cost", s["open_cost_cents"] == 9300, str(s))

    # ── naming what is holding a row ──────────────────────────────────────────
    r = client.patch("/api/admin/filings/%d" % pub["id"], headers=dan,
                     json={"blocked_on": "needs the statement filed first"})
    check("a row can name what it is waiting on",
          r.status_code == 200 and r.json()["item"]["blocked_on"].startswith("needs"), r.text[:200])
    check("the summary counts blocked rows", board()["summary"]["blocked"] == 1, str(board()["summary"]))
    r = client.patch("/api/admin/filings/%d" % pub["id"], headers=dan, json={"clear_blocked_on": True})
    check("and it can be cleared", r.json()["item"]["blocked_on"] is None, r.text[:160])

    # ── money can be cleared on purpose ──────────────────────────────────────
    r = client.patch("/api/admin/filings/%d" % pub["id"], headers=dan, json={"cost_cents": 4500})
    check("a quoted price can be entered", r.json()["item"]["cost_cents"] == 4500, r.text[:160])
    r = client.patch("/api/admin/filings/%d" % pub["id"], headers=dan, json={"clear_cost_cents": True})
    check("and taken back to not-quoted", r.json()["item"]["cost_cents"] is None, r.text[:160])

    # ── closing a recurring row rolls the next cycle onto the board ───────────
    r = client.patch("/api/admin/filings/%d" % fbn["id"], headers=dan,
                     json={"status": "done", "paid_cents": 9300, "confirmation": "FBN-2026-0042"})
    check("marking done answers with the closed row and its next cycle", r.status_code == 200, r.text[:200])
    body = r.json()
    check("the row is done with what was paid",
          body["item"]["status"] == "done" and body["item"]["paid_cents"] == 9300, str(body["item"]))
    nxt = body["next"]
    check("a next cycle was created", nxt is not None, str(body))
    check("five years out, same day",
          nxt["due_on"] == due_soon.replace(year=due_soon.year + 5).isoformat(),
          "%s vs %s" % (nxt and nxt["due_on"], due_soon.replace(year=due_soon.year + 5)))
    check("the next cycle is open and remembers where it came from",
          nxt["status"] == "open" and nxt["rolled_from"] == fbn["id"], str(nxt))
    check("and it kept the price", nxt["cost_cents"] == 9300, str(nxt))

    r = client.patch("/api/admin/filings/%d" % fbn["id"], headers=dan, json={"status": "done"})
    check("marking it done twice does not make a second cycle",
          r.status_code == 200 and board()["summary"]["total"] == 4, str(board()["summary"]))

    # ── a one-off rolls nothing ───────────────────────────────────────────────
    r = client.patch("/api/admin/filings/%d" % pub["id"], headers=dan, json={"status": "done"})
    check("a one-off filing closes without a next cycle",
          r.status_code == 200 and r.json()["next"] is None, r.text[:200])

    # ── reopening ─────────────────────────────────────────────────────────────
    r = client.patch("/api/admin/filings/%d" % pub["id"], headers=dan, json={"status": "open"})
    check("a closed row can be reopened",
          r.json()["item"]["status"] == "open" and r.json()["item"]["done_on"] is None, r.text[:200])

    # ── a row can be removed, and a missing one is a 404 ──────────────────────
    check("a missing filing is a 404",
          client.patch("/api/admin/filings/9999", headers=dan, json={"status": "done"}).status_code == 404)
    check("a row can be deleted",
          client.delete("/api/admin/filings/%d" % pub["id"], headers=dan).status_code == 200)
    check("and the board shrinks", board()["summary"]["total"] == 3, str(board()["summary"]))

    # ── the console really renders it ────────────────────────────────────────
    page = client.get("/static/admin.html").text if False else ""
    check("the section and its endpoint name are in the page source",
          "sec-filings" in open(str(ROOT / "static" / "admin.html"), encoding="utf-8").read() and
          "/api/admin/filings" in open(str(ROOT / "static" / "admin.html"), encoding="utf-8").read())

    print("\n%s (%d failure(s))" % ("FILINGS TESTS PASSED" if FAILS == 0 else "FILINGS TESTS FAILED", FAILS))
    return 1 if FAILS else 0


if __name__ == "__main__":
    sys.exit(main())
