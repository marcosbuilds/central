from __future__ import annotations

import argparse
import re
import sys

from integrations.discord_api import DiscordAPI, DiscordAPIError
from config.settings import Settings
from persistence.database import PeaceDatabase


OLD_NAME = re.compile(r"^\s*[A-Za-z]\s*⎰\s*(.+?)\s+\d+\s*$")
PREFIX_NAME = re.compile(r"^\s*[A-Za-z]\s*⎰\s*(.+?)\s*$")


def alias_from_member(member: dict, fallback: str) -> str:
    nickname = str(member.get("nick") or "").strip()
    match = OLD_NAME.match(nickname)
    if match:
        return match.group(1).strip()
    match = PREFIX_NAME.match(nickname)
    if match:
        return match.group(1).strip()
    return nickname or fallback


def build_name(prefix: str, alias: str, peace_id: int) -> str:
    suffix = f" {peace_id}"
    room = max(1, 32 - len(prefix) - len(" ⎰ ") - len(suffix))
    return f"{prefix} ⎰ {alias[:room].strip()}" + suffix


def run() -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Atualiza IDs Peace nos apelidos sem alterar cargos.")
    parser.add_argument("--apply", action="store_true", help="aplica os apelidos permitidos no Discord")
    args = parser.parse_args()

    settings = Settings.from_env()
    api = DiscordAPI(settings.token)
    database = PeaceDatabase(settings.database_path)
    database.initialize()
    roles = api.guild_roles(settings.guild_id)
    role_positions = {str(role["id"]): int(role.get("position", 0)) for role in roles}
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
        prefix = str(row["name_prefix"] or "N")
        fallback = str(user.get("global_name") or user.get("username") or user_id)
        alias = alias_from_member(member, fallback)
        proposed = build_name(prefix, alias, int(row["peace_id"]))
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

