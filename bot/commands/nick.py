from __future__ import annotations

import argparse
import sys

if (__package__ or "").startswith("bot."):
    from ..integrations.discord_api import DiscordAPI, DiscordAPIError
    from ..config.settings import Settings
    from ..core.identity import (
        PEACE_NICKNAME_PATTERN,
        alias_from_nickname,
        build_peace_nickname,
        prefix_for_roles,
    )
    from ..persistence.database import PeaceDatabase
else:
    from integrations.discord_api import DiscordAPI, DiscordAPIError
    from config.settings import Settings
    from core.identity import (
        PEACE_NICKNAME_PATTERN,
        alias_from_nickname,
        build_peace_nickname,
        prefix_for_roles,
    )
    from persistence.database import PeaceDatabase


def alias_from_member(member: dict, fallback: str) -> str:
    nickname = str(member.get("nick") or "").strip()
    return alias_from_nickname(nickname, strip_legacy_id=bool(nickname)) or fallback


def build_name(prefix: str, alias: str, peace_id: int) -> str:
    return build_peace_nickname(prefix, alias, peace_id)


def peace_id_from_member(member: dict) -> int | None:
    """Return the live nickname ID when prefix-only repair is requested."""

    match = PEACE_NICKNAME_PATTERN.match(str(member.get("nick") or "").strip())
    return int(match.group("peace_id")) if match else None


def run() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Atualiza IDs Peace nos apelidos sem alterar cargos.")
    parser.add_argument("--apply", action="store_true", help="aplica os apelidos permitidos no Discord")
    parser.add_argument(
        "--prefix-only",
        action="store_true",
        help="atualiza somente o prefixo e preserva o ID Peace já exibido",
    )
    args = parser.parse_args()

    settings = Settings.from_env()
    api = DiscordAPI(settings.token)
    database = PeaceDatabase(settings.database_path)
    database.initialize()
    roles = api.guild_roles(settings.guild_id)
    roles_by_id = {str(role["id"]): role for role in roles}
    # Keep both identifiers available. The nickname backfill receives member
    # roles as IDs, while the shared prefix policy also accepts role names.
    role_positions: dict[str, int] = {}
    role_hoist: dict[str, bool] = {}
    for role in roles:
        role_id = str(role["id"])
        role_name = str(role.get("name", role_id))
        role_positions[role_id] = int(role.get("position", 0))
        role_positions[role_name] = int(role.get("position", 0))
        role_hoist[role_id] = bool(role.get("hoist", False))
        role_hoist[role_name] = bool(role.get("hoist", False))
    guild = api.get(f"/guilds/{settings.guild_id}")
    owner_id = int(guild.get("owner_id", 0))
    bot_member = api.get(f"/guilds/{settings.guild_id}/members/{settings.bot_user_id}")
    bot_top = max((role_positions.get(str(role_id), 0) for role_id in bot_member.get("roles", [])), default=0)
    members = api.guild_members(settings.guild_id)
    target = [
        member for member in members
        if str(settings.peace_role_id) in {str(role_id) for role_id in member.get("roles", [])}
        or int(member["user"]["id"]) == settings.founder_user_id
    ]

    changed = 0
    skipped = 0
    failed = 0
    for member in target:
        user = member["user"]
        user_id = int(user["id"])
        row = database.get_member(user_id)
        if row is None:
            print(f"SKIP {user_id}: membro não está no SQLite")
            skipped += 1
            continue
        member_role_names = [
            str(roles_by_id.get(str(role_id), {}).get("name", role_id))
            for role_id in member.get("roles", [])
        ]
        prefix = str(
            prefix_for_roles(
                user_id=user_id,
                role_names=member_role_names,
                founder_user_id=settings.founder_user_id,
                founder_role_names=("Founder Peace", "Founder"),
                default=str(row["name_prefix"] or "N"),
                role_positions=role_positions,
                role_hoist=role_hoist,
            )
            or "N"
        )
        fallback = str(user.get("global_name") or user.get("username") or user_id)
        alias = alias_from_member(member, fallback)
        live_peace_id = peace_id_from_member(member) if args.prefix_only else None
        peace_id = live_peace_id if live_peace_id is not None else int(row["peace_id"])
        proposed = build_name(prefix, alias, peace_id)
        current = member.get("nick") or "(sem apelido)"
        print(f"{user_id} | {current} -> {proposed}", end="")
        if user_id == owner_id:
            print(" | SKIP_OWNER")
            skipped += 1
            continue
        max_target_role = max((role_positions.get(str(role_id), 0) for role_id in member.get("roles", [])), default=0)
        if max_target_role >= bot_top:
            print(" | SKIP_HIERARCHY")
            skipped += 1
            continue
        if current == proposed:
            print(" | OK")
            continue
        if not args.apply:
            print(" | DRY_RUN")
            changed += 1
            continue
        try:
            api.patch(f"/guilds/{settings.guild_id}/members/{user_id}", {"nick": proposed})
            database.update_nickname(user_id, proposed)
            print(" | APPLIED")
            changed += 1
        except DiscordAPIError as error:
            print(f" | ERROR {error}")
            failed += 1

    mode = "aplicados" if args.apply else "previstos"
    print(f"Resumo: {changed} {mode}, {skipped} ignorados, {failed} falhas")


if __name__ == "__main__":
    run()

