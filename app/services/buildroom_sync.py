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

One exception, and it is narrow: after each sweep ``reconcile`` clears the two drifts the per-PR
blocks cannot reach. A heading-only bullet ("3. **Run it until it sells:**") is deleted once its
release is live, because it asks for nothing; and a hand-written card left in **review** whose
pull request is merged, live, and merged *after* the card was written is closed — nobody owes a
review of work that already serves traffic. It still never takes a claim, never closes a ``todo``
card, and leaves a card alone when the card's own words say it owes more.
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

# A pull request body that uses numbered bold sections ("3. **Run it until it sells:**") puts that
# heading through the bullet parser as if it were work. A title that is *only* a heading, with
# nothing under it, is a parsing artefact: it can be deleted once the release it came from is live.
_HEADING_ONLY = re.compile(r"^\s*\d+\.?\s*\*\*[^*]{1,120}\*\*:?\s*$")

# A card that says, in its own words, that it still owes something. A release going live does not
# overrule that — the phrase is reported instead, so a person looks rather than the watcher guessing.
_OWES_MORE = ("not built", "not yet", "blocked on", "to be written", "to write",
              "once the meta app review", "still to", "remain")

# Written once into a held card's notes, so the same explanation is not appended every sweep and
# the next person can see why a card with a live pull request is still in review.
_HELD = "release watcher:"



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


def _as_utc(value: Optional[Any]) -> Optional[datetime]:
    """SQLite hands back naive datetimes and Postgres aware ones; comparing them raises."""
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


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
    # Flush so the row has an id before anything reports on it: the caller's answer names the
    # rows it wrote, and an id assigned only at commit turns that answer into "#None".
    db.flush()
    return task


def _drive(task: BuildroomTask, *, status: str, deploy: str, live_commit: str,
           live_at: Optional[str], changed: Dict[str, Any]) -> None:
    """Move a release task to the status the deploy actually justifies, once."""
    # The LAST state line is the current one: a row that went waiting -> live -> waiting has
    # three of them, and reading the first would append the same line on every pass.
    states = _STATE_LINE.findall(task.notes or "")
    seen = states[-1] if states else None
    if seen != deploy:
        _append(task, f"deploy={deploy}")
    if task.claimed_by or (task.tested_by and task.tested_by != SYNC_BY):
        # Somebody is on it, or a person already signed it off: report, never overrule.
        return
    if task.status != status:
        changed["status"].append(f"#{task.id} {task.status}->{status}")
        task.status = status
    if status == "done" and task.tested_by != SYNC_BY:
        # Stamped once, on the pass that saw it live. Rewriting it on every later deploy would
        # make an old release claim the newest build's sha and read as if it shipped today.
        task.tested_by = SYNC_BY
        task.tested_at = datetime.now(timezone.utc)
        task.test_note = (f"live as {live_commit or 'the current build'} on resmara.com"
                          + (f", deployed {live_at}" if live_at else ""))
        changed["tested"].append(task.id)


def reconcile(db: Session, payload: Dict[str, Any], live_commit: str = "") -> Dict[str, List[str]]:
    """Close what the releases prove is finished, and delete rows that are not work.

    The board drifts in two directions the per-pull-request blocks above do not reach:

    * a card a person wrote for a spec ("Engine 4 · Campaign build") sits in **review** for days
      after the pull request that shipped it went live, because the sync never touches a row it
      did not create. Nobody owes a review of work that is already serving traffic.
    * a PR body's numbered bold heading ("3. **Run it until it sells:**") becomes a back-end task
      that asks for nothing, and it stays on the board forever.

    Two rules, both narrow enough to defend:

    * delete a heading-only ``be`` row once its pull request is merged **and live**;
    * close a **hand-written** row in ``review`` only when its notes name a pull request that is
      merged and live *and was merged after the row was created* — the PR is then evidence that the
      card's work shipped. A card that says it still owes something (``_OWES_MORE``), that somebody
      has claimed, or that a person has already tested is reported in ``skipped`` and left alone.
      ``todo`` rows are never closed: "not started" is not "shipped".
    """
    out: Dict[str, List[str]] = {"closed": [], "deleted": [], "skipped": []}
    live: Dict[int, Dict[str, Any]] = {}
    for rel in payload.get("releases") or []:
        try:
            number = int(rel.get("number"))
        except (TypeError, ValueError):
            continue
        if rel.get("merged_at") and (rel.get("deploy") or "") == "live":
            live[number] = rel
    if not live:
        return out

    stamp = datetime.now(timezone.utc)
    for row in db.query(BuildroomTask).all():
        marker = _MARK.search(row.notes or "")
        if marker and marker.group(2) == "be":
            if int(marker.group(1)) in live and _HEADING_ONLY.match(row.title or ""):
                out["deleted"].append(f"#{row.id} {row.title}")
                db.delete(row)
            continue
        if marker or row.status != "review":
            continue
        # The PR has to have merged after the card existed: an older card that merely mentions a
        # pull request number is not evidence that this card's work shipped.
        opened = _as_utc(row.created_at)
        named = {int(n) for n in re.findall(r"\bPR #(\d+)", row.notes or "")}
        shipped = [n for n in sorted(named)
                   if n in live and opened and (_as_utc(live[n].get("merged_at")) or stamp) > opened]
        if not shipped:
            continue
        if row.claimed_by or (row.tested_by and row.tested_by != SYNC_BY):
            continue                      # somebody is on it, or a person signed it: never overrule
        notes = (row.notes or "").lower()
        if any(phrase in notes for phrase in _OWES_MORE):
            if _HELD in (row.notes or ""):
                continue          # explained once already: repeating it every sweep is noise
            number = shipped[0]
            _append(row, f"{_HELD} PR #{number} is merged and live, but this card says it still "
                         f"owes work, so it stays in review for a person to look at")
            out["skipped"].append(f"#{row.id} {row.title}")
            continue
        number = shipped[0]
        _append(row, f"PR #{number} went live; nothing was claimed and nothing was left owed, "
                     f"so the release watcher closed this review row")
        row.status = "done"
        row.tested_by = SYNC_BY
        row.tested_at = stamp
        row.test_note = (f"PR #{number} merged and live as {live_commit or 'the current build'} "
                         f"on resmara.com")
        out["closed"].append(f"#{row.id} {row.title}")
    return out


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
        # The Releases payload says "merged" for anything not open, which includes a pull request
        # that was closed without merging. Only ``merged_at`` is evidence of a release; treating
        # a closed PR as one would put a row on the board that can never go live.
        merged = bool(rel.get("merged_at"))
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
            _append(review, f"merged as {sha}" if merged and sha else ("merged" if merged
                                                                     else "closed without merging"))
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
        if state == "open" or not merged:
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

    reconciled = reconcile(db, payload, live_commit=live_commit)
    db.commit()
    return {
        "checked_prs": seen_prs,
        "created": changed["created"],
        "status": changed["status"],
        "tested": changed["tested"],
        "blocked": changed["blocked"],
        "reconciled": reconciled,
        "live_commit": live_commit or None,
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }
