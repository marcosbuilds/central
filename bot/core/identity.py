"""Shared Peace identity rules for member labels and nicknames."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


# These are presentation labels only. Access roles such as Peace, Dev, Staff,
# Management and Visitor must never produce a nickname prefix.
VISUAL_ROLE_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "D",
        (
            "developer",
            "desenvolvedor",
            "frontend",
            "backend",
            "documentation",
            "documentação",
            "documentacao",
            "a is",
            "ais",
            "ai & bots",
            "ia & bots",
            "general director",
            "diretor geral",
        ),
    ),
    ("S", ("streamer",)),
    ("R", ("recrutador",)),
)


def _normalise_role_name(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().strip())


def _role_name_candidates(value: str) -> set[str]:
    normalised = _normalise_role_name(value)
    candidates = {normalised}
    if normalised.endswith(" peace"):
        candidates.add(normalised[: -len(" peace")].rstrip())
    return candidates


def prefix_for_roles(
    *,
    user_id: int,
    role_names: Iterable[str],
    founder_user_id: int,
    founder_role_names: Iterable[str] = (),
    default: str | None = None,
    role_positions: Mapping[str, int] | None = None,
) -> str | None:
    """Return the deterministic presentation prefix for a member.

    Founder is an explicit product rule. Every other prefix must come from the
    allowlisted visual-role names above; permission roles are intentionally not
    matched by substring so names such as ``Dev`` and ``Management`` cannot
    acquire a prefix by accident.
    """

    names: set[str] = set()
    for role_name in role_names:
        names.update(_role_name_candidates(str(role_name)))
    founder_names: set[str] = set()
    for role_name in founder_role_names:
        founder_names.update(_role_name_candidates(str(role_name)))
    if int(user_id) == int(founder_user_id) or names.intersection(founder_names):
        return "F"
    positions: dict[str, int] = {}
    for role_name, position in (role_positions or {}).items():
        try:
            numeric_position = int(position)
        except (TypeError, ValueError):
            continue
        for candidate in _role_name_candidates(str(role_name)):
            positions[candidate] = max(positions.get(candidate, -1), numeric_position)

    matches: list[tuple[int, int, str]] = []
    for precedence, (prefix, visual_names) in enumerate(VISUAL_ROLE_PREFIXES):
        matched_positions = [
            positions.get(name, -1)
            for name in names.intersection(visual_names)
        ]
        if matched_positions:
            # Discord's role position is the source of truth. The explicit
            # precedence keeps the name-only/database path deterministic when
            # no live role positions are available.
            matches.append((max(matched_positions), -precedence, prefix))
    if matches:
        return max(matches)[2]
    return default
