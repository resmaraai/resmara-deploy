#!/usr/bin/env python3
"""Releases -> build room: the row appears, the row closes only when the release is really live.

The failure this stops is the board drifting from GitHub and Render: a merged pull request that
nobody wrote down, or a "done" row for a deploy that failed. So the rules worth pinning are:

  * an open pull request becomes a review task, assigned to the person who merges
  * the pull request's "Back end needed" bullets become their own back-end tasks, and the sync
    never closes them by itself — only whoever did the work can
  * a merged pull request becomes a release task
  * that release task is closed only when the PR's commit is inside the live build; a deploy that
    failed blocks it, a deploy in flight shows as doing, and a deploy nobody started is todo
  * a second run changes nothing (idempotent: no duplicate rows, no duplicate notes)
  * a task the sync did not create is never touched
  * the endpoint is machine-only: no token is 403, and with the token it runs the sync
"""
from __future__ import annotations

import os
import sys
import tempfile
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
    tmp = tempfile.mkdtemp(prefix="resmara-buildroom-sync-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "sync.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-buildroom-sync")
    os.environ["RESMARA_ADMIN_EMAILS"] = "dan@example.com,adam@example.com"
    os.environ["RESMARA_PUBLISH_TOKEN"] = "test-publish-token"

    from app.db.session import Base, engine, SessionLocal, BuildroomTask
    from app.services.buildroom_sync import sync

    Base.metadata.create_all(bind=engine)

    def payload(live: str, releases):
        return {"connected": True, "live_commit": live, "problems": [], "releases": releases}

    def row(db, title_start: str):
        return db.query(BuildroomTask).filter(BuildroomTask.title.startswith(title_start)).first()

    pr_open = {"number": 12, "title": "Homepage hero on phones", "state": "open",
               "side": "front end", "commit": "", "url": "https://github.com/x/pull/12",
               "deploy": None, "backend_tasks": []}
    pr_live = {"number": 11, "title": "Card on file", "state": "merged",
               "merged_at": "2026-11-18T15:47:42Z",
               "side": "front end + back end", "commit": "aaaa111", "url": "https://github.com/x/pull/11",
               "deploy": "live", "live_at": "2026-11-19T01:11:31Z",
               "backend_tasks": ["POST /api/billing/card: setup-mode checkout",
                                 "app/services/billing.py: charge the saved card"]}
    pr_waiting = {"number": 13, "title": "Dark mode fixes", "state": "merged",
                  "merged_at": "2026-11-18T19:18:12Z",
                  "side": "front end", "commit": "bbbb222", "url": "https://github.com/x/pull/13",
                  "deploy": "waiting",
                  "backend_tasks": ["POST /api/billing/card: setup-mode checkout",
                                    "app/services/billing.py: charge the saved card"]}

    # A task a person wrote by hand: the sync must not so much as rename it.
    with SessionLocal() as db:
        human = BuildroomTask(title="Articles of Organization", area="front_end", status="todo",
                              notes="hand-written, not the sync's business", created_by="dan@example.com")
        db.add(human)
        db.commit()

    # ── first run ───────────────────────────────────────────────────────────────────
    print("first run")
    with SessionLocal() as db:
        first = sync(db, payload("cccc333", [pr_open, pr_live, pr_waiting]))
        db.commit()

    with SessionLocal() as db:
        review = row(db, "Review PR #12")
        live = row(db, "Release #11")
        waiting = row(db, "Release #13")
        be1 = row(db, "POST /api/billing/card")
        be2 = row(db, "app/services/billing.py")
        stale = db.query(BuildroomTask).filter(
            BuildroomTask.notes.contains("[auto:pr #11 be")).count()
        human = row(db, "Articles of Organization")
        count = db.query(BuildroomTask).count()

    check("open PR makes a review task", review is not None)
    check("review task is assigned to the merger", review.assigned_to == "dan@example.com")
    check("review task is open", review.status == "todo")
    check("merged PR makes a release task", live is not None)
    check("live release is done", live.status == "done", live.status if live else "missing")
    check("live release is tested by the sync", live.tested_by == "release-sync")
    check("live release names the live commit", "cccc333" in (live.test_note or ""), live.test_note or "")
    check("merged-but-waiting release is still open", waiting.status == "todo", waiting.status if waiting else "missing")
    check("release area follows the PR's files", live.area == "both", live.area)
    check("release is assigned to the operator", live.assigned_to == "dan@example.com")
    check("backend bullet 1 becomes a task", be1 is not None)
    check("backend bullet 2 becomes a task", be2 is not None)
    check("backend bullet tasks are not auto-closed", be1.status == "todo", be1.status if be1 else "missing")
    check("no bullets invented for an already-live release", stale == 0, str(stale))
    check("hand-written task untouched", human.status == "todo" and human.created_by == "dan@example.com")
    check("notes carry the machine marker", "[auto:pr #11 release]" in (live.notes or ""))
    check("first run reports what it created", len(first["created"]) == 5, str(first["created"]))
    check("the report names real rows, not #None",
          bool(first["status"]) and all(s.startswith("#") and s[1:2].isdigit() for s in first["status"]),
          str(first["status"]))
    check("six rows on the board", count == 6, str(count))

    # ── second run: nothing to do ───────────────────────────────────────────────────
    print("second run (same releases)")
    with SessionLocal() as db:
        before = db.query(BuildroomTask).count()
        notes_before = row(db, "Release #13").notes
        second = sync(db, payload("cccc333", [pr_open, pr_live, pr_waiting]))
        db.commit()
        after = db.query(BuildroomTask).count()
        notes_after = row(db, "Release #13").notes

    check("no duplicate rows", before == after == 6, f"{before}->{after}")
    check("no duplicate notes", notes_before == notes_after)
    check("second run creates nothing", second["created"] == [], str(second["created"]))
    check("second run changes no status", second["status"] == [], str(second["status"]))

    # ── the deploy lands ────────────────────────────────────────────────────────────
    print("PR #13 becomes live")
    with SessionLocal() as db:
        third = sync(db, payload("dddd444", [pr_live, {**pr_waiting, "deploy": "live",
                                                      "live_at": "2026-11-19T09:00:00Z"}]))
        db.commit()
        waiting = row(db, "Release #13")
        review = row(db, "Review PR #12")

    check("#13 closed once live", waiting.status == "done", waiting.status)
    check("#13 names the new live commit", "dddd444" in (waiting.test_note or ""), waiting.test_note or "")
    check("closing it is reported", any("done" in s for s in third["status"]), str(third["status"]))

    # ── a later deploy does not rewrite history ─────────────────────────────────────
    print("a new build goes live")
    with SessionLocal() as db:
        note_before = row(db, "Release #13").test_note
        lines_before = (row(db, "Release #13").notes or "").count("\n")
        sync(db, payload("eeee555", [pr_live, {**pr_waiting, "deploy": "live",
                                               "live_at": "2026-11-20T09:00:00Z"}]))
        db.commit()
        after = row(db, "Release #13")
    check("an old release keeps the sha it shipped as", after.test_note == note_before, after.test_note or "")
    check("and gains no note for a deploy it was not part of",
          (after.notes or "").count("\n") == lines_before, str((after.notes or "").count("\n")))
    check("the still-open PR's review stays open", review.status == "todo", review.status)

    # ── the deploy fails ────────────────────────────────────────────────────────────
    print("a deploy fails")
    with SessionLocal() as db:
        db.add(BuildroomTask(title="Release #14 — broken build", area="back_end", status="todo",
                             notes="[auto:pr #14 release]", created_by="release-sync"))
        db.commit()
        fourth = sync(db, payload("cccc333", [{
            "number": 14, "title": "Broken build", "state": "merged", "side": "back end",
            "merged_at": "2026-11-19T08:00:00Z",
            "commit": "eeee555", "url": "https://github.com/x/pull/14", "deploy": "failed",
            "backend_tasks": []}]))
        db.commit()
        broken = row(db, "Release #14")

    check("a failed deploy blocks the release row", broken.status == "blocked", broken.status)
    check("the block is reported", any("#14" in b for b in fourth["blocked"]), str(fourth["blocked"]))

    # ── the pull request merges: its review row closes ─────────────────────────────
    print("PR #12 merges")
    with SessionLocal() as db:
        sync(db, payload("eeee555", [{**pr_open, "state": "merged", "commit": "ffff666",
                                      "merged_at": "2026-11-19T09:30:00Z",
                                      "deploy": "deploying"}]))
        db.commit()
        review = row(db, "Review PR #12")
        release = row(db, "Release #12")
    check("merged PR closes its review task", review.status == "done", review.status)
    check("and opens a release task", release is not None and release.status == "doing",
          release.status if release else "missing")

    # ── closed without merging: no release row, and the review row says why ─────────
    print("a pull request is closed without merging")
    pr15 = {"number": 15, "title": "Abandoned idea", "state": "open", "side": "front end",
            "commit": "", "url": "https://github.com/x/pull/15", "deploy": None,
            "backend_tasks": []}
    with SessionLocal() as db:
        sync(db, payload("ffff666", [pr15]))
        db.commit()
    with SessionLocal() as db:
        sync(db, payload("ffff666", [{**pr15, "state": "merged", "merged_at": None, "deploy": None}]))
        db.commit()
        r15 = row(db, "Review PR #15")
        rel15 = row(db, "Release #15")
    check("the review row closes", r15.status == "done", r15.status)
    check("and says it was closed, not merged", "closed without merging" in (r15.notes or ""),
          (r15.notes or "")[-60:])
    check("a closed pull request makes no release row", rel15 is None)

    # ── the endpoint is machine-only ────────────────────────────────────────────────
    print("the endpoint")
    from fastapi.testclient import TestClient
    from app.main import app
    import app.api.system as system_module

    system_module.releases = lambda limit=8, user=None: payload("ffff666", [pr_live])
    client = TestClient(app)
    refused = client.post("/api/admin/buildroom/sync")
    check("no token is refused", refused.status_code == 403, str(refused.status_code))
    allowed = client.post("/api/admin/buildroom/sync",
                          headers={"X-Resmara-Token": "test-publish-token"})
    body = allowed.json() if allowed.status_code == 200 else {}
    check("with the token it runs", allowed.status_code == 200, f"{allowed.status_code} {allowed.text[:200]}")
    check("the answer says what it looked at", body.get("checked_prs") == [11], str(body.get("checked_prs")))
    check("the answer carries the live commit", body.get("live_commit") == "ffff666", str(body.get("live_commit")))

    print()
    if FAILS:
        print(f"{FAILS} FAILED")
        return 1
    print("ALL BUILD ROOM SYNC CHECKS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
