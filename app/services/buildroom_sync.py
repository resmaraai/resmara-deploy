"""Releases become build room rows, and a row closes itself when the release is live.

The build room and the Releases page answer two halves of one question — *what is left,*
and *did it ship* — and until now a person was the glue: merge a pull request, remember to
write a row, remember to tick it off when Render finished. That is three chances to forget on
every release, and the board quietly stops being true.

This module is the glue, in one direction only:

* an **open** pull request becomes a *review* task, so a change waiting on a person is visible
  on the board that people actually look at;
* the "Back end needed" bullets in a pull request's body become one task each, so what the front
  end is waiting on is on the board before the merge, not after;
* a **merged** pull request becomes a *release* task, and that task is closed only when GitHub
  says its commit is inside the build Render is serving — not when the PR is merged, and not
  when a deploy merely started;
* a deploy that *failed* blocks the release task instead of leaving it looking idle.

What it deliberately will not do: touch a task it did not create, take a claim off anyone, or
close a "Back end needed" bullet by itself. Those bullets describe work in code, and only a
person or an agent who did the work can say it is done. A machine that guesses there would turn
the one board that tells the truth into another dashboard.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import BuildroomTask

SYNC_BY = "release-sync"
# Every row this module owns carries this in its notes. The number is the pull request, the
# word says which question the row answers, and the optional number is a bullet index.
_MARK = re.compile(r"\[auto:pr #(\d+) (review|release|be)(?: (\d+))?\]")
# Notes lines are written as "[YYYY-MM-DD] deploy=live", so the state has to be read from the
# last such line, not from a bare marker.
_STATE_LINE = re.compile(r"^\[[0-9-]+\] deploy=(\w+)", re.MULTILINE)


def _operator() -> str:
    """The account that does deploys and back-end work: the first admin email, i.e. Dan."""
    first = (settings.ADMIN_EMAILS or "").split(",")[0].strip()
    return first or "resmaraai@gmail.com"


def _area(side: str) -> str:
    side = (side or "").lower()
    if "front end + back end" in side or ("front" in side and "back" in side):
        return "both"
    if "back" in side:
        return "back_end"
    if "front" in side:
        return "front_end"
    return "both"


def _stamp() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _append(task: BuildroomTask, line: str) -> None:
    task.notes = ((task.notes + "\n") if task.notes else "") + f"[{_stamp()}] {line}"


def _index(rows: List[BuildroomTask]) -> Dict[Tuple[int, str, int], BuildroomTask]:
    out: Dict[Tuple[int, str, int], BuildroomTask] = {}
    for row in rows:
        match = _MARK.search(row.notes or "")
        if match:
            out[(int(match.group(1)), match.group(2), int(match.group(3) or 0))] = row
    return out


def _new_task(db: Session, *, pr: int, kind: str, bullet: int, title: str, area: str,
              notes: str, assignee: str) -> BuildroomTask:
    task = BuildroomTask(
        title=title[:240],
        area=area,
        status="todo",
        notes=f"{notes}\n[auto:pr #{pr} {kind}" + (f" {bullet}" if bullet else "") + "]",
        assigned_to=assignee,
        created_by=SYNC_BY,
    )
    db.add(task)
    return task


def _drive(task: BuildroomTask, *, status: str, deploy: str, live_commit: str,
           live_at: Optional[str], changed: Dict[str, Any]) -> None:
    """Move a release task to the status the deploy actually justifies, once."""
    state_line = _STATE_LINE.search(task.notes or "")
    seen = state_line.group(1) if state_line else None
    if seen != deploy:
        _append(task, f"deploy={deploy}" + (f" ({live_commit})" if deploy == "live" and live_commit else ""))
    if task.claimed_by or (task.tested_by and task.tested_by != SYNC_BY):
        # Somebody is on it, or a person already signed it off: report, never overrule.
        return
    if task.status != status:
        changed["status"].append(f"#{task.id} {task.status}->{status}")
        task.status = status
    if status == "done":
        if task.tested_by != SYNC_BY:
            task.tested_by = SYNC_BY
            task.tested_at = datetime.now(timezone.utc)
            changed["tested"].append(task.id)
        note = f"live as {live_commit or 'the current build'} on resmara.com" + (
            f", deployed {live_at}" if live_at else "")
        if task.test_note != note:
            task.test_note = note


def sync(db: Session, payload: Dict[str, Any]) -> Dict[str, Any]:
    """Reconcile the Releases payload into the build room. Idempotent; safe to run every tick."""
    live_commit = (payload.get("live_commit") or "").strip()
    rows = db.query(BuildroomTask).all()
    existing = _index(rows)
    changed: Dict[str, List[Any]] = {"created": [], "status": [], "tested": [], "blocked": []}
    assignee = _operator()
    seen_prs: List[int] = []

    for rel in payload.get("releases") or []:
        try:
            pr = int(rel.get("number"))
        except (TypeError, ValueError):
            continue
        seen_prs.append(pr)
        state = rel.get("state") or "open"
        deploy = rel.get("deploy") or ("waiting" if state != "open" else "open")
        area = _area(rel.get("side") or "")
        title = (rel.get("title") or "").strip()
        url = rel.get("url") or ""
        sha = rel.get("commit") or ""

        # --- an open pull request: somebody owes a review --------------------------------
        key = (pr, "review", 0)
        review = existing.get(key)
        if state == "open":
            if review is None:
                existing[key] = _new_task(
                    db, pr=pr, kind="review", bullet=0,
                    title=f"Review PR #{pr} — {title}",
                    area=area,
                    notes=(f"{url}\n{rel.get('side') or 'unknown'} change, waiting on a review "
                           f"before it can be merged and deployed."),
                    assignee=assignee)
                changed["created"].append(existing[key].title)
            else:
                if review.claimed_by or (review.tested_by and review.tested_by != SYNC_BY):
                    pass
                elif review.status != "todo":
                    changed["status"].append(f"#{review.id} {review.status}->todo")
                    review.status = "todo"
        elif review is not None and review.status != "done":
            _append(review, f"merged as {sha}" if sha else "merged")
            if not review.claimed_by and not (review.tested_by and review.tested_by != SYNC_BY):
                changed["status"].append(f"#{review.id} {review.status}->done")
                review.status = "done"

        # --- the pull request's "Back end needed" bullets --------------------------------
        # Only while the change is still not live. A bullet is a pre-merge promise; once the
        # release is served, only a person can say whether it was kept or shipped around, and a
        # board full of guessed rows is worse than one that stays quiet. Backfilling every
        # bullet from every old pull request would bury today's work in last week's.
        if state == "open" or deploy != "live":
            for i, bullet in enumerate(rel.get("backend_tasks") or [], start=1):
                text = (bullet or "").strip().lstrip("-* ").strip()
                if not text:
                    continue
                key = (pr, "be", i)
                if key in existing:
                    continue
                existing[key] = _new_task(
                    db, pr=pr, kind="be", bullet=i,
                    title=text[:240], area="back_end",
                    notes=(f"Needed by PR #{pr} — {title}\n{url}\n"
                           "Closed by whoever does the work, not by the release landing."),
                    assignee=assignee)
                changed["created"].append(existing[key].title)

        # --- a merged pull request: a release row that closes when it is really live ----
        if state == "open":
            continue
        key = (pr, "release", 0)
        release = existing.get(key)
        if release is None:
            release = _new_task(
                db, pr=pr, kind="release", bullet=0,
                title=f"Release #{pr} — {title}", area=area,
                notes=(f"{url}\nMerged as {sha or 'an unknown commit'}"
                       + (f", {rel.get('merged_at')}" if rel.get("merged_at") else "")
                       + ".\nClosed when that commit is inside the build Render is serving."),
                assignee=assignee)
            existing[key] = release
            changed["created"].append(release.title)

        if deploy == "live":
            _drive(release, status="done", deploy="live", live_commit=live_commit,
                   live_at=rel.get("live_at"), changed=changed)
        elif deploy == "failed":
            _drive(release, status="blocked", deploy="failed", live_commit=live_commit,
                   live_at=None, changed=changed)
            changed["blocked"].append(f"#{release.id} {release.title}")
        elif deploy == "deploying":
            _drive(release, status="doing", deploy="deploying", live_commit=live_commit,
                   live_at=None, changed=changed)
        else:
            _drive(release, status="todo", deploy=deploy, live_commit=live_commit,
                   live_at=None, changed=changed)

    db.commit()
    return {
        "checked_prs": seen_prs,
        "created": changed["created"],
        "status": changed["status"],
        "tested": changed["tested"],
        "blocked": changed["blocked"],
        "live_commit": live_commit or None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
