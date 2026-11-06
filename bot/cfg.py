from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Variável obrigatória ausente: {name}")
    return value


def _int_env(name: str, default: int | None = None) -> int:
    raw = os.getenv(name)
    if raw is None or not raw.strip():
        if default is None:
            raise RuntimeError(f"Variável obrigatória ausente: {name}")
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise RuntimeError(f"Variável {name} precisa ser um número inteiro") from exc


def _bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "sim", "on"}


def _ids_env(name: str, default: tuple[int, ...] = ()) -> tuple[int, ...]:
    raw = os.getenv(name, "")
    values: list[int] = []
    for item in raw.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            values.append(int(item))
        except ValueError as exc:
            raise RuntimeError(f"Variável {name} contém um ID inválido: {item}") from exc
    return tuple(dict.fromkeys(values)) or default


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int
    peace_role_id: int
    novato_role_id: int
    set_channel_id: int
    welcome_channel_id: int | None
    rules_channel_id: int | None
    log_channel_id: int | None
    ticket_panel_channel_id: int | None
    operations_channel_id: int | None
    absence_channel_id: int | None
    scan_channel_id: int | None
    ticket_category_id: int | None
    closed_ticket_category_id: int | None
    staff_role_id: int | None
    staff_control_channel_id: int | None
    manager_role_id: int | None
    recruiter_role_id: int | None
    visitor_role_id: int | None
    booster_role_id: int | None
    private_call_category_id: int | None
    automod_channel_id: int | None
    website_url: str
    iris_enabled: bool
    iris_model: str
    iris_url: str
    iris_escalation_seconds: int
    iris_management_channel_ids: tuple[int, ...]
    iris_general_channel_ids: tuple[int, ...]
    iris_learning_channel_ids: tuple[int, ...]
    iris_history_limit: int
    founder_user_id: int
    bot_user_id: int | None
    database_path: Path
    set_vagas_abertas: bool
    username_min_length: int
    username_max_length: int

    @classmethod
    def from_env(cls) -> "Settings":
        database_path = Path(os.getenv("DATABASE_PATH", "data/peace.sqlite3"))
        if not database_path.is_absolute():
            database_path = ROOT / database_path
        return cls(
            token=_required("DISCORD_TOKEN"),
            guild_id=_int_env("DISCORD_GUILD_ID"),
            peace_role_id=_int_env("DISCORD_PEACE_ROLE_ID"),
            novato_role_id=_int_env("DISCORD_NOVATO_ROLE_ID"),
            set_channel_id=_int_env("DISCORD_SET_CHANNEL_ID"),
            welcome_channel_id=_int_env("DISCORD_WELCOME_CHANNEL_ID", None),
            rules_channel_id=_int_env("DISCORD_RULES_CHANNEL_ID", None),
            log_channel_id=_int_env("DISCORD_LOG_CHANNEL_ID", None),
            ticket_panel_channel_id=_int_env("DISCORD_TICKET_PANEL_CHANNEL_ID", None),
            operations_channel_id=_int_env("DISCORD_OPERATIONS_CHANNEL_ID", None),
            absence_channel_id=_int_env("DISCORD_ABSENCE_CHANNEL_ID", None),
            scan_channel_id=_int_env("DISCORD_SCAN_CHANNEL_ID", None),
            ticket_category_id=_int_env("DISCORD_TICKET_CATEGORY_ID", None),
            closed_ticket_category_id=_int_env("DISCORD_CLOSED_TICKET_CATEGORY_ID", None),
            staff_role_id=_int_env("DISCORD_STAFF_ROLE_ID", None),
            staff_control_channel_id=_int_env("DISCORD_STAFF_CONTROL_CHANNEL_ID", None),
            manager_role_id=_int_env("DISCORD_MANAGER_ROLE_ID", None),
            recruiter_role_id=_int_env("DISCORD_RECRUITER_ROLE_ID", None),
            visitor_role_id=_int_env("DISCORD_VISITOR_ROLE_ID", None),
            booster_role_id=_int_env("DISCORD_BOOSTER_ROLE_ID", None),
            private_call_category_id=_int_env("DISCORD_PRIVATE_CALL_CATEGORY_ID", None),
            automod_channel_id=_int_env("DISCORD_AUTOMOD_CHANNEL_ID", None),
            website_url=os.getenv("PEACE_SITE_URL", "https://peacegg.com.br").strip(),
            iris_enabled=_bool_env("IRIS_ENABLED", False),
            iris_model=os.getenv("IRIS_MODEL", "iris-peace-micro").strip(),
            iris_url=os.getenv("IRIS_URL", "http://127.0.0.1:11435").rstrip("/"),
            iris_escalation_seconds=_int_env("IRIS_ESCALATION_SECONDS", 300),
            iris_management_channel_ids=_ids_env("IRIS_MANAGEMENT_CHANNEL_IDS"),
            iris_general_channel_ids=_ids_env("IRIS_GENERAL_CHANNEL_IDS"),
            iris_learning_channel_ids=_ids_env("IRIS_LEARNING_CHANNEL_IDS"),
            iris_history_limit=_int_env("IRIS_HISTORY_LIMIT", 10),
            founder_user_id=_int_env("DISCORD_FOUNDER_USER_ID"),
            bot_user_id=_int_env("DISCORD_BOT_USER_ID", None),
            database_path=database_path,
            set_vagas_abertas=_bool_env("SET_VAGAS_ABERTAS"),
            username_min_length=_int_env("SET_USERNAME_MIN_LENGTH", 3),
            username_max_length=_int_env("SET_USERNAME_MAX_LENGTH", 20),
        )

