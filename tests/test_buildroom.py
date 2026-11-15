#!/usr/bin/env python3
"""Build room: who is working on what, and whether the claim lock actually holds.

Two people work this product — one on ``static/``, one on ``app/`` — and the failure this
board exists to stop is two of them editing the same thing on the same evening. So the things
worth pinning are the rules a person relies on when they look at the board:

  * only an admin can read or write it — this is the operators' board
  * claiming is a lock: while a fresh claim is on a task, the other person's edit is refused
    with 409 that names the holder and the age of the claim, and their claim attempt is refused
  * claiming starts the work (todo becomes doing), releasing stops it (doing back to todo)
  * a claim older than the stale window can be taken over, and the takeover is written down
  * marking a task done releases the lock — a finished task is nobody's to hold
  * a claim nobody has is counted as "nobody has it": that is the number that stops work going
    quiet, and it must equal open minus claimed
  * an overdue task is one whose due date has passed and which is not done
  * a task is only "tested" when a person is recorded, and done-but-untested is counted apart
"""
from __future__ import annotations

import os
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
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
    tmp = tempfile.mkdtemp(prefix="resmara-buildroom-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "buildroom.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-buildroom")
    os.environ["RESMARA_ADMIN_EMAILS"] = "dan@example.com"

    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import Base, engine, SessionLocal, User, BuildroomTask

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    from app.core.security import get_password_hash

    def account(email: str, admin: bool = False) -> dict:
        with SessionLocal() as db:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, name=email, hashed_password=get_password_hash("br-pass-123"),
                            is_active=True, is_admin=admin, subscription_status="active"))
                db.commit()
        r = client.post("/api/auth/login", data={"username": email, "password": "br-pass-123"})
        token = r.json().get("access_token", "")
        if not token:
            check("login as " + email, False, r.text[:160])
        return {"Authorization": "Bearer " + token}

    dan = account("dan@example.com", admin=True)
    adam = account("adam@example.com", admin=True)
    stranger = account("stranger@example.com")

    def board(hdrs=None) -> dict:
        r = client.get("/api/admin/buildroom", headers=hdrs or dan)
        return r.json() if r.status_code == 200 else {}

    # ── the door ──────────────────────────────────────────────────────────────
    check("a stranger cannot read the board",
          client.get("/api/admin/buildroom", headers=stranger).status_code == 403,
          str(client.get("/api/admin/buildroom", headers=stranger).status_code))
    check("nor add to it",
          client.post("/api/admin/buildroom", headers=stranger,
                      json={"title": "sneak in"}).status_code == 403)
    check("an admin can read it", client.get("/api/admin/buildroom", headers=dan).status_code == 200)
    check("an empty board says so",
          board()["summary"]["tasks"] == 0 and board()["items"] == [], str(board().get("summary")))

    # ── adding ────────────────────────────────────────────────────────────────
    check("a task with no title is refused",
          client.post("/api/admin/buildroom", headers=dan, json={"title": "   "}).status_code == 400)
    check("an unknown half is refused",
          client.post("/api/admin/buildroom", headers=dan,
                      json={"title": "x", "area": "middleware"}).status_code == 400)
    check("a bad date is refused",
          client.post("/api/admin/buildroom", headers=dan,
                      json={"title": "x", "due_on": "next tuesday"}).status_code == 400)

    r = client.post("/api/admin/buildroom", headers=dan, json={
        "title": "Homepage hero: new headline and a wider photo",
        "area": "front_end", "due_on": (date.today() + timedelta(days=2)).isoformat(),
        "created_by": "dan@example.com"})
    check("a front-end task is added", r.status_code == 201, r.text[:200])
    hero = r.json()
    check("it starts as todo with nobody on it",
          hero["status"] == "todo" and hero["claimed_by"] is None, str(hero))
    check("and it is not overdue", hero["overdue"] is False)

    s = board()["summary"]
    check("the board counts it as open", s["open"] == 1, str(s))
    check("with nobody claiming it", s["unclaimed"] == 1 and s["claimed"] == 0, str(s))
    check("the total equals the rows",
          s["tasks"] == len(board()["items"]) == 1, str(s))

    # ── the lock ──────────────────────────────────────────────────────────────
    check("Adam claims the front-end task",
          client.post("/api/admin/buildroom/%d/claim" % hero["id"], headers=adam,
                      json={"by": "adam@example.com"}).json()["claimed_by"] == "adam@example.com")
    row = board()["items"][0]
    check("claiming starts the work", row["status"] == "doing", row["status"])
    check("the claim is fresh", row["claim_fresh"] is True and row["claim_age_hours"] is not None,
          str(row["claim_age_hours"]))
    s = board()["summary"]
    check("the board now says somebody has it",
          s["claimed"] == 1 and s["unclaimed"] == 0, str(s))
    check("and names who", s["by_owner"].get("adam@example.com") == 1, str(s["by_owner"]))

    r = client.patch("/api/admin/buildroom/%d" % hero["id"], headers=dan,
                     json={"title": "Dan renaming Adam's task", "who": "dan@example.com"})
    check("the other person's edit is refused", r.status_code == 409, r.text[:200])
    detail = r.json().get("detail") or {}
    check("and the refusal names the holder", detail.get("held_by") == "adam@example.com", str(detail))
    check("with the age of the claim", isinstance(detail.get("age_hours"), (int, float)), str(detail))
    check("the title was not changed anyway",
          board()["items"][0]["title"].startswith("Homepage hero"), board()["items"][0]["title"])

    r = client.post("/api/admin/buildroom/%d/claim" % hero["id"], headers=dan,
                    json={"by": "dan@example.com"})
    check("nor can the other person just claim it", r.status_code == 409, r.text[:200])

    check("but the holder can edit it",
          client.patch("/api/admin/buildroom/%d" % hero["id"], headers=adam,
                       json={"status": "review", "who": "adam@example.com"}).json()["status"] == "review")

    # ── releasing ─────────────────────────────────────────────────────────────
    check("only the holder may release it",
          client.post("/api/admin/buildroom/%d/release" % hero["id"], headers=dan,
                      json={"by": "dan@example.com"}).status_code == 409)
    row = client.post("/api/admin/buildroom/%d/release" % hero["id"], headers=adam,
                      json={"by": "adam@example.com"}).json()
    check("releasing clears the claim", row["claimed_by"] is None and row["claim_age_hours"] is None,
          str(row["claimed_by"]))
    check("a released task is nobody's and counts as such",
          board()["summary"]["unclaimed"] == 1, str(board()["summary"]))

    # ── a stale claim can be taken over, and it is written down ───────────────
    client.post("/api/admin/buildroom/%d/claim" % hero["id"], headers=adam,
                json={"by": "adam@example.com"})
    with SessionLocal() as db:
        t = db.get(BuildroomTask, hero["id"])
        t.claimed_at = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=30)
        db.commit()
    stale = board()["items"][0]
    check("a claim older than the window is stale",
          stale["claim_fresh"] is False and stale["claim_age_hours"] > 24, str(stale["claim_age_hours"]))
    check("the board counts it as stale", board()["summary"]["stale_claims"] == 1,
          str(board()["summary"]["stale_claims"]))
    check("a stale claim does not block anybody",
          client.patch("/api/admin/buildroom/%d" % hero["id"], headers=dan,
                       json={"status": "review", "who": "dan@example.com"}).status_code == 200)
    row = client.post("/api/admin/buildroom/%d/claim" % hero["id"], headers=dan,
                      json={"by": "dan@example.com"}).json()
    check("Dan can take a stale claim over", row["claimed_by"] == "dan@example.com", str(row["claimed_by"]))
    check("and the takeover is written into the notes",
          "took this over from adam@example.com" in (row["notes"] or ""), repr(row["notes"]))

    # ── done releases the lock ────────────────────────────────────────────────
    row = client.patch("/api/admin/buildroom/%d" % hero["id"], headers=dan,
                       json={"status": "done", "who": "dan@example.com"}).json()
    check("marking it done releases the claim",
          row["status"] == "done" and row["claimed_by"] is None, str(row["claimed_by"]))
    s = board()["summary"]
    check("a done task is not open", s["open"] == 0 and s["claimed"] == 0, str(s))
    check("done-but-untested is counted apart", s["untested_and_done"] == 1, str(s))
    check("and done sorts to the bottom",
          board()["items"][-1]["id"] == hero["id"], str([i["id"] for i in board()["items"]]))

    # ── tested ────────────────────────────────────────────────────────────────
    row = client.post("/api/admin/buildroom/%d/tested" % hero["id"], headers=adam,
                      json={"by": "adam@example.com", "note": "clicked it on an iPhone"}).json()
    check("a test records who did it", row["tested_by"] == "adam@example.com" and row["tested_at"],
          str(row))
    check("and the note", row["test_note"] == "clicked it on an iPhone", repr(row["test_note"]))
    s = board()["summary"]
    check("the board counts tested tasks", s["tested"] == 1 and s["untested_and_done"] == 0, str(s))
    check("testing is not editing somebody else's work — the lock does not apply",
          client.post("/api/admin/buildroom/%d/tested" % hero["id"], headers=adam,
                      json={"by": "dan@example.com"}).status_code == 200)

    # ── overdue, and what it means ────────────────────────────────────────────
    r = client.post("/api/admin/buildroom", headers=dan, json={
        "title": "Stripe receipts email", "area": "back_end",
        "due_on": (date.today() - timedelta(days=3)).isoformat(), "created_by": "dan@example.com"})
    late = r.json()
    check("a task due in the past is overdue", late["overdue"] is True, str(late["due_on"]))
    check("and the board counts it", board()["summary"]["overdue"] == 1, str(board()["summary"]))
    check("a done task is never overdue",
          client.patch("/api/admin/buildroom/%d" % late["id"], headers=dan,
                       json={"status": "done", "who": "dan@example.com"}).json()["overdue"] is False)

    # ── blocked ───────────────────────────────────────────────────────────────
    r = client.post("/api/admin/buildroom", headers=dan, json={
        "title": "Meta app review", "area": "both", "status": "blocked",
        "notes": "waiting on Facebook", "created_by": "dan@example.com"})
    check("a blocked task is marked blocked", r.json()["status"] == "blocked", str(r.json()["status"]))
    s = board()["summary"]
    check("and only blocked work counts as blocked", s["blocked"] == 1, str(s))
    check("every row is in the total", s["tasks"] == 3, str(s))

    # ── delete ────────────────────────────────────────────────────────────────
    check("a task can be removed",
          client.delete("/api/admin/buildroom/%d" % late["id"], headers=dan).json()["deleted"] == late["id"])
    check("and it is gone", board()["summary"]["tasks"] == 2, str(board()["summary"]["tasks"]))
    check("deleting something that is not there is a 404",
          client.delete("/api/admin/buildroom/%d" % late["id"], headers=dan).status_code == 404)

    print()
    if FAILS:
        print("BUILD ROOM: %d FAILED" % FAILS)
        return 1
    print("BUILD ROOM: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
