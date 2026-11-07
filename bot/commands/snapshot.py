from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from ..config.settings import Settings
from ..persistence.database import PeaceDatabase
from ..integrations.discord_api import DiscordAPI


def run() -> None:
    parser = argparse.ArgumentParser(description="Captura cargos, membros Peace e mensagens do bot.")
    parser.add_argument("--no-randomize", action="store_true", help="mantém a ordem recebida pela API")
    parser.add_argument("--output", type=Path, help="arquivo JSON de snapshot")
    args = parser.parse_args()

    settings = Settings.from_env()
    api = DiscordAPI(settings.token)
    snapshot = api.snapshot(settings.guild_id, settings.founder_user_id, settings.peace_role_id)
    output = args.output or Path(__file__).resolve().parents[2] / "data" / "snapshots" / (
        f"discord_snapshot_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.json"
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")

    roles_by_id = {str(role["id"]): role for role in snapshot["roles"]}
    database = PeaceDatabase(settings.database_path)
    result = database.import_snapshot(
        members=snapshot["members"],
        roles_by_id=roles_by_id,
        bot_messages=snapshot["bot_messages"],
        founder_id=settings.founder_user_id,
        guild_id=settings.guild_id,
        source_file=str(output),
        randomize_new_ids=not args.no_randomize,
    )
    print(f"Snapshot salvo: {output}")
    print(f"Membros com Peace importados: {result['members']}")
    print(f"Novos IDs Peace gerados: {result['new_ids']}")
    print(f"Mensagens do bot recuperadas: {result['bot_messages']}")
    print(f"Banco SQL: {settings.database_path}")


if __name__ == "__main__":
    run()

