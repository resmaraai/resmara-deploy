"""Who may read which part of the Team room.

The console draws a sidebar and hides what a person cannot see, but hiding is a courtesy:
every console endpoint asks this module first, so a team member who types a URL for a group
they were not given gets a 403 rather than the data. The page's own Settings tab offers exactly
these six groups, so ``team_access`` stores these keys and nothing else.

Two things grant access:
  * ``is_admin`` on the account (the operator accounts in RESMARA_ADMIN_EMAILS, i.e. Dan and
    Adam) - full access to everything, including the Team page itself.
  * ``team_access`` - a list of the groups below, set on the Team page.

An account with neither is a customer: it has no console access at all.
"""
from __future__ import annotations

from typing import Iterable, List

from fastapi import Depends, HTTPException

from app.core.security import get_current_user

# The six groups the Team page assigns. Each covers the pages listed beside it.
GROUPS: dict[str, tuple[str, ...]] = {
    "build": ("buildroom", "releases"),
    "agents": ("users", "support", "connections", "advertising"),
    "campaigns": ("campaigns",),
    "money": ("finance", "costs", "money"),
    "business": ("growth", "marketing", "website"),
    "system": ("health", "activity", "system"),
}

# Old names, kept so a stored list that used a page name still works.
_ALIASES = {alias: group for group, aliases in GROUPS.items() for alias in aliases}
_ALIASES.update({g: g for g in GROUPS})


def is_super(user) -> bool:
    """Dan, Adam, and anyone the Team page promotes: everything, including the team itself."""
    return bool(getattr(user, "is_admin", False) or getattr(user, "team_super_admin", False))


def _granted(user) -> List[str]:
    raw = getattr(user, "team_access", None) or []
    if isinstance(raw, str):
        raw = [raw]
    out: List[str] = []
    for value in raw:
        group = _ALIASES.get(str(value).strip().lower())
        if group and group not in out:
            out.append(group)
    return out


def allowed_groups(user) -> List[str]:
    if is_super(user):
        return list(GROUPS)
    return _granted(user)


def can(user, group: str) -> bool:
    return is_super(user) or group in _granted(user)


def can_enter(user) -> bool:
    """May this account open the console at all?"""
    return is_super(user) or bool(_granted(user))


def sanitise_access(values: Iterable[str] | None) -> List[str]:
    """Keep only the group names the Team page knows, deduped, in the page's own order.

    A stored list may still hold an old page name (``finance``) from before the page was
    grouped, so each value is resolved through the alias table first; the six group keys are
    what comes back, because that is what the sidebar and the 403s both read.
    """
    chosen = {_ALIASES.get(str(v).strip().lower()) for v in (values or [])}
    return [g for g in GROUPS if g in chosen]


def require(user, group: str) -> None:
    if not can(user, group):
        raise HTTPException(status_code=403, detail="You do not have access to this part of the console")


def needs(group: str):
    """A FastAPI dependency for one group: ``Depends(needs('money'))``."""

    def _dep(current_user=Depends(get_current_user)):
        require(current_user, group)
        return current_user

    return _dep


def console_user(current_user=Depends(get_current_user)):
    """Anyone who may open the console, without asking for a particular group."""
    if not can_enter(current_user):
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user
