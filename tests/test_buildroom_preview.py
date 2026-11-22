#!/usr/bin/env python3
"""The build room's Preview button: one GitHub question, answered honestly.

A "Preview" that opens production is worse than no button, and so is one that opens a guessed
hostname. The link only exists as a GitHub deployment on the pull request's head commit, so what
these checks pin is the reading of that record:

  * a task typed by hand has no pull request and says so instead of offering a link;
  * the number is looked up in the code repo first and the deploy mirror second, because the
    board's rows come from the mirror but previews belong to pull requests on the code repo;
  * a finished deployment status is preferred over a newer pending one;
  * "no preview yet" and "GitHub could not answer" are different sentences, both 200, and
    neither is an exception;
  * the answer is cached for a minute, so a room full of clicks is not a room full of API calls.
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
    tmp = tempfile.mkdtemp(prefix="resmara-preview-")
    os.environ["RESMARA_UPLOAD_DIR"] = tmp
    os.environ["DATABASE_URL"] = "sqlite:///" + os.path.join(tmp, "preview.db")
    os.environ.setdefault("SECRET_KEY", "test-secret-key-for-preview-links")
    os.environ["RESMARA_ADMIN_EMAILS"] = "dan@example.com"
    # A token only has to exist: the GitHub call itself is faked below.
    os.environ["RESMARA_GITHUB_TOKEN"] = "test-token-not-a-real-one"
    os.environ["RESMARA_PREVIEW_REPO"] = "resmaraai/resmara"
    os.environ["RESMARA_GITHUB_REPO"] = "resmaraai/resmara-deploy"
    os.environ["RESMARA_PREVIEW_CACHE_SECONDS"] = "60"

    from fastapi.testclient import TestClient
    from app.main import app
    from app.db.session import Base, engine, SessionLocal, User, BuildroomTask
    from app.services import previews

    Base.metadata.create_all(bind=engine)
    client = TestClient(app)

    from app.core.security import get_password_hash

    def account(email: str, admin: bool = False) -> dict:
        with SessionLocal() as db:
            if not db.query(User).filter(User.email == email).first():
                db.add(User(email=email, name=email, hashed_password=get_password_hash("pv-pass-123"),
                            is_active=True, is_admin=admin, subscription_status="active"))
                db.commit()
        r = client.post("/api/auth/login", data={"username": email, "password": "pv-pass-123"})
        return {"Authorization": "Bearer " + r.json().get("access_token", "")}

    dan = account("dan@example.com", admin=True)
    stranger = account("stranger@example.com")

    # ── the fake GitHub ───────────────────────────────────────────────────────────────
    # Two repositories, the way production has them: preview PRs live on the code repo, the
    # board's PR numbers come from the mirror, and the numbering overlaps but does not agree.
    CALLS: list = []
    PULLS = {"resmaraai/resmara": {7: "sha7", 9: "sha9", 10: "sha10", 11: "sha11"},
             "resmaraai/resmara-deploy": {}}
    DEPLOYMENTS = {
        "sha7": [{"id": 701, "environment": "resmara-pr-7"}],
        "sha9": [{"id": 901, "environment": "resmara-pr-9"}],
        "sha10": [],
        "sha11": [{"id": 1101, "environment": "resmara-pr-11"}],
    }
    STATUSES = {
        701: [{"state": "success", "environment_url": "https://resmara-pr-7.onrender.com"}],
        # Newest first, the way GitHub returns them: a pending status that already carries a URL
        # sits in front of the finished one that actually works.
        901: [{"state": "pending", "environment_url": "https://pr-9-not-yet"},
              {"state": "success", "environment_url": "https://resmara-pr-9.onrender.com"}],
    }

    def fake_gh(repo: str, path: str, params=None):
        CALLS.append((repo, path, dict(params or {})))
        if path.startswith("/pulls/"):
            pr = int(path.rsplit("/", 1)[-1])
            if repo == "resmaraai/resmara" and pr == 11:
                raise RuntimeError("GitHub answered 502: bad gateway")
            sha = PULLS.get(repo, {}).get(pr)
            if not sha:
                raise LookupError("%s%s answered 404" % (repo, path))
            return {"head": {"sha": sha}}
        if path == "/deployments":
            return DEPLOYMENTS.get((params or {}).get("sha"), [])
        if path.startswith("/deployments/") and path.endswith("/statuses"):
            return STATUSES.get(int(path.split("/")[2]), [])
        raise LookupError("unexpected path " + path)

    previews._gh = fake_gh
    previews.forget()

    def new_task(notes: str, title: str = "a task") -> int:
        with SessionLocal() as db:
            task = BuildroomTask(title=title, area="back_end", status="todo", notes=notes,
                                 created_by="test")
            db.add(task)
            db.commit()
            return task.id

    def preview_of(task_id: int, hdrs=None):
        return client.get(f"/api/admin/buildroom/{task_id}/preview", headers=hdrs or dan)

    # ── the door ──────────────────────────────────────────────────────────────────────
    hand = new_task("Typed by an operator. No pull request behind it.")
    check("a stranger cannot read a preview", preview_of(hand, stranger).status_code == 403,
          str(preview_of(hand, stranger).status_code))
    check("a missing task is a 404", preview_of(9999).status_code == 404,
          str(preview_of(9999).status_code))

    # ── a task with no pull request ───────────────────────────────────────────────────
    r = preview_of(hand)
    body = r.json() if r.status_code == 200 else {}
    check("a hand-written task answers 200, not an error", r.status_code == 200, str(r.status_code))
    check("... and says there is no pull request", body.get("ok") is False and body.get("reason") == "no_pr",
          str(body))
    check("... in a sentence, not a code",
          "pull request" in (body.get("why") or "").lower(), str(body.get("why")))
    check("no GitHub call is made for it", not CALLS, str(CALLS[:2]))

    # ── the row carries its PR number ─────────────────────────────────────────────────
    synced = new_task("https://github.com/resmaraai/resmara/pull/7\n[auto:pr #7 release]",
                      "Release #7 — a change")
    board = client.get("/api/admin/buildroom", headers=dan).json()
    row = next((t for t in board["items"] if t["id"] == synced), {})
    hand_row = next((t for t in board["items"] if t["id"] == hand), {})
    check("a synced row carries its pull request", row.get("pr") == 7, str(row.get("pr")))
    check("a hand-written row carries none", hand_row.get("pr") is None, str(hand_row.get("pr")))

    # ── a preview that exists ─────────────────────────────────────────────────────────
    r = preview_of(synced)
    body = r.json()
    check("a PR with a preview answers ok", body.get("ok") is True, str(body))
    check("... with the deployment's own address",
          body.get("url") == "https://resmara-pr-7.onrender.com", str(body.get("url")))
    check("... naming the code repo, not the mirror", body.get("repo") == "resmaraai/resmara",
          str(body.get("repo")))
    check("... and the environment Render created", body.get("environment") == "resmara-pr-7",
          str(body.get("environment")))

    # ── the finished status wins over a newer pending one ─────────────────────────────
    pending = new_task("[auto:pr #9 release]", "Release #9")
    body = preview_of(pending).json()
    check("a finished deployment is preferred over a newer pending one",
          body.get("url") == "https://resmara-pr-9.onrender.com", str(body.get("url")))
    check("... and reports that it is ready", body.get("state") == "success", str(body.get("state")))

    # ── a PR that exists without a preview ────────────────────────────────────────────
    noprev = new_task("[auto:pr #10 release]", "Release #10")
    body = preview_of(noprev).json()
    check("no deployment is 'no preview yet'", body.get("ok") is False
          and body.get("reason") == "no_preview", str(body))
    check("... and the sentence says what creates one",
          "blueprint" in (body.get("why") or "").lower(), str(body.get("why")))

    # ── nobody has that PR ────────────────────────────────────────────────────────────
    ghost = new_task("[auto:pr #8 release]", "Release #8")
    body = preview_of(ghost).json()
    check("a PR number neither repo knows says so", body.get("ok") is False
          and body.get("reason") == "no_pull_request", str(body))
    check("... naming both repositories it tried",
          "resmaraai/resmara" in (body.get("why") or "")
          and "resmara-deploy" in (body.get("why") or ""), str(body.get("why")))

    # ── GitHub falling over is an answer, not a crash ─────────────────────────────────
    broken = new_task("[auto:pr #11 release]", "Release #11")
    r = preview_of(broken)
    body = r.json() if r.status_code == 200 else {}
    check("a GitHub error is still a 200", r.status_code == 200, str(r.status_code))
    check("... reported as an error with GitHub's own words", body.get("reason") == "github_error"
          and "502" in (body.get("why") or ""), str(body))

    # ── cached for a minute ───────────────────────────────────────────────────────────
    previews.forget()
    CALLS.clear()
    preview_of(synced)
    preview_of(synced)
    pulls = [c for c in CALLS if c[1] == "/pulls/7"]
    check("two clicks inside a minute are one GitHub call", len(pulls) == 1, str(len(pulls)))
    previews.forget(7)
    preview_of(synced)
    pulls = [c for c in CALLS if c[1] == "/pulls/7"]
    check("forgetting the answer asks again", len(pulls) == 2, str(len(pulls)))

    print("\n%s" % ("ALL PREVIEW CHECKS PASSED" if not FAILS else "%d FAILED" % FAILS))
    return 0 if not FAILS else 1


if __name__ == "__main__":
    raise SystemExit(main())
