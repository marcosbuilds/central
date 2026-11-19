"""Shared Peace identity rules for member labels and nicknames."""

from __future__ import annotations

import re
from collections.abc import Iterable, Mapping


# These are presentation labels only. Access/status roles must never produce a
# nickname prefix, even when Discord's ``hoist`` flag is enabled on them. The
# prefix is the stable code of the highest live visual role.
NON_VISUAL_ROLE_NAMES = frozenset(
    {
        "peace",
        "dev",
        "staff",
        "management",
        "gerência",
        "gerencia",
        "visitor",
        "visitante",
        "not verified",
        "não verificado",
        "nao verificado",
        "booster",
        "apoiador",
        "call montenegro",
    }
)

VISUAL_ROLE_PREFIXES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("DEL", ("manager ⎰ deputy delegate", "gerente ⎰ delegado adjunto", "delegado")),
    ("D", ("developer", "desenvolvedor")),
    ("B", ("bot",)),
    ("A", ("a is", "ais", "ai & bots", "ia & bots")),
    ("G", ("general director", "diretor geral")),
    ("E", ("elite", "elite ⎰ special agent", "elite ⎰ agente especial", "agente especial")),
    ("M", ("member", "member ⎰ recruit", "membro ⎰ recruta", "agente")),
    ("R", ("rookie", "rookie ⎰ agent", "novato", "novato ⎰ agente", "aluno", "recrutador")),
    ("I", ("intern", "estagiário", "estagiario")),
    ("S", ("streamer",)),
)

MAX_DISCORD_NICKNAME_LENGTH = 32
PREFIX_TOKEN_PATTERN = r"[A-Z]{1,4}"
PEACE_NICKNAME_PATTERN = re.compile(
    rf"^\s*(?P<prefix>{PREFIX_TOKEN_PATTERN})\s*⎰\s*(?P<alias>.+?)\s+(?P<peace_id>\d+)\s*$"
)
PREFIXED_NICKNAME_PATTERN = re.compile(
    rf"^\s*(?P<prefix>{PREFIX_TOKEN_PATTERN})\s*⎰\s*(?P<alias>.+?)\s*$"
)
LEGACY_ID_PATTERN = re.compile(r"^\s*(?P<alias>.+?)\s+\d+\s*$")


def alias_from_nickname(value: str | None, *, strip_legacy_id: bool = False) -> str:
    """Extract the member alias from a Peace nickname in any supported format."""

    nickname = str(value or "").strip()
    match = PEACE_NICKNAME_PATTERN.match(nickname)
    if match:
        return match.group("alias").strip()
    match = PREFIXED_NICKNAME_PATTERN.match(nickname)
    if match:
        return match.group("alias").strip()
    if strip_legacy_id:
        match = LEGACY_ID_PATTERN.match(nickname)
        if match:
            return match.group("alias").strip()
    return nickname


def build_peace_nickname(prefix: str, alias: str, peace_id: int) -> str:
    """Build a Discord-safe nickname while preserving the complete Peace ID."""

    normalized_prefix = str(prefix).strip().upper()
    if not re.fullmatch(PREFIX_TOKEN_PATTERN, normalized_prefix):
        raise ValueError("Peace nickname prefixes must be 1-4 uppercase ASCII letters")
    peace_id_text = str(int(peace_id))
    available_alias_length = (
        MAX_DISCORD_NICKNAME_LENGTH
        - len(normalized_prefix)
        - len(" ⎰ ")
        - len(peace_id_text)
        - 1
    )
    if available_alias_length < 1:
        raise ValueError("Peace ID is too long for a Discord nickname")
    normalized_alias = re.sub(r"\s+", " ", str(alias)).strip()
    base = normalized_alias[:available_alias_length].strip() or "Peace"
    return f"{normalized_prefix} ⎰ {base} {peace_id_text}"


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
    role_hoist: Mapping[str, bool] | None = None,
) -> str | None:
    """Return the deterministic presentation prefix for a member.

    Founder is an explicit product rule. Every other prefix must come from the
    allowlisted visual-role names above; when ``role_hoist`` is supplied by a
    live Discord snapshot, the matching role must also be displayed separately.
    Permission roles are explicitly excluded so names such as ``Dev`` and
    ``Management`` cannot acquire a prefix by accident.
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
    hoist_by_name: dict[str, bool] = {}
    for role_name, is_hoisted in (role_hoist or {}).items():
        for candidate in _role_name_candidates(str(role_name)):
            hoist_by_name[candidate] = bool(is_hoisted)

    for precedence, (prefix, visual_names) in enumerate(VISUAL_ROLE_PREFIXES):
        matched_names = {
            name
            for name in names.intersection(visual_names)
            if name not in NON_VISUAL_ROLE_NAMES
        }
        if role_hoist is not None:
            # Discord's ``hoist`` flag is the live source of truth for whether
            # a role is presented separately. Access/status roles remain out
            # of VISUAL_ROLE_PREFIXES, so a hoisted permission role cannot
            # acquire a prefix by accident.
            matched_names = {
                name for name in matched_names if hoist_by_name.get(name, False)
            }
        if not matched_names:
            continue
        matched_positions = [
            positions.get(name, -1)
            for name in matched_names
        ]
        # Discord's role position is the source of truth. The explicit
        # precedence keeps the name-only/database path deterministic when
        # no live role positions are available.
        matches.append((max(matched_positions), -precedence, prefix))
    if matches:
        return max(matches)[2]
    return default
