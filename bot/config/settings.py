from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2] if (__package__ or "").startswith("bot.") else Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")

LOOPBACK_HOSTS = {"localhost", "127.0.0.1", "::1"}
BRIDGE_PLACEHOLDERS = {
    "generate-a-local-secret",
    "replace-with-a-local-secret",
    "replace-with-a-32-byte-secret",
}


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


def _validate_unique_role_ids(role_ids: dict[str, int | None]) -> None:
    """Fail closed when two settings point at the same Discord role."""
    owners: dict[int, list[str]] = {}
    for setting_name, role_id in role_ids.items():
        if role_id is None:
            continue
        owners.setdefault(int(role_id), []).append(setting_name)
    duplicates = {
        role_id: names
        for role_id, names in owners.items()
        if len(names) > 1
    }
    if duplicates:
        details = "; ".join(
            f"{role_id}: {', '.join(names)}"
            for role_id, names in sorted(duplicates.items())
        )
        raise RuntimeError(f"IDs de cargos duplicados na configuração: {details}")


def is_valid_central_bridge_key(value: str) -> bool:
    normalized = value.strip()
    return (
        len(normalized) >= 32
        and normalized.casefold() not in BRIDGE_PLACEHOLDERS
        and not normalized.casefold().startswith("replace-with-")
    )


def _central_bridge_key_env() -> str:
    value = os.getenv("CENTRAL_BRIDGE_KEY", "").strip()
    if not value:
        return ""
    if not is_valid_central_bridge_key(value):
        raise RuntimeError("CENTRAL_BRIDGE_KEY precisa ser um segredo local aleatório de pelo menos 32 caracteres")
    return value


def _discord_invite_env() -> str:
    value = os.getenv("PEACE_DISCORD_INVITE_URL", "https://discord.gg/replace-with-invite").strip()
    parsed = urlsplit(value)
    if parsed.scheme != "https" or parsed.hostname not in {"discord.gg", "discord.com", "www.discord.com"}:
        raise RuntimeError("PEACE_DISCORD_INVITE_URL precisa apontar para um convite HTTPS do Discord")
    if not parsed.path.strip("/"):
        raise RuntimeError("PEACE_DISCORD_INVITE_URL precisa conter o código do convite")
    return value


def parse_central_bridge_url(value: str) -> tuple[str, int, str]:
    """Return a safe loopback binding; the bridge never binds a remote host."""
    parsed = urlsplit(value.strip())
    if parsed.scheme != "http" or parsed.hostname not in LOOPBACK_HOSTS:
        raise RuntimeError("CENTRAL_BRIDGE_URL precisa ser uma URL HTTP de loopback")
    if parsed.username or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/"):
        raise RuntimeError("CENTRAL_BRIDGE_URL contém componentes não permitidos")
    try:
        port = parsed.port or 8765
    except ValueError as exc:
        raise RuntimeError("CENTRAL_BRIDGE_URL contém uma porta inválida") from exc
    if not 1 <= port <= 65535:
        raise RuntimeError("CENTRAL_BRIDGE_URL contém uma porta inválida")
    host = parsed.hostname
    assert host is not None
    return host, port, f"http://[{host}]:{port}/" if ":" in host else f"http://{host}:{port}/"


@dataclass(frozen=True)
class Settings:
    token: str
    guild_id: int
    peace_role_id: int
    novato_role_id: int
    set_channel_id: int
    welcome_channel_id: int | None
    rules_channel_id: int | None
    verification_category_id: int | None
    verification_channel_id: int | None
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
    visitor_role_id: int | None
    not_verified_role_id: int | None
    intern_role_id: int | None
    booster_role_id: int | None
    central_access_role_id: int | None
    central_auth_code_ttl_seconds: int
    central_auth_session_ttl_seconds: int
    central_bridge_url: str
    central_bridge_key: str
    private_call_category_id: int | None
    automod_channel_id: int | None
    afk_channel_id: int | None
    website_url: str
    website_media_channel_id: int | None
    website_clips_channel_id: int | None
    website_media_cache_seconds: int
    api_enabled: bool
    api_host: str
    api_port: int
    discord_invite_url: str
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
    developer_vagas_abertas: bool
    staff_vagas_abertas: bool
    username_min_length: int
    username_max_length: int

    @classmethod
    def from_env(cls) -> "Settings":
        database_path = Path(os.getenv("DATABASE_PATH", "data/peace.sqlite3"))
        if not database_path.is_absolute():
            database_path = ROOT / database_path
        central_bridge_url = os.getenv("CENTRAL_BRIDGE_URL", "").strip()
        settings = cls(
            token=_required("DISCORD_TOKEN"),
            guild_id=_int_env("DISCORD_GUILD_ID"),
            peace_role_id=_int_env("DISCORD_PEACE_ROLE_ID"),
            novato_role_id=_int_env("DISCORD_NOVATO_ROLE_ID"),
            set_channel_id=_int_env("DISCORD_SET_CHANNEL_ID"),
            welcome_channel_id=_int_env("DISCORD_WELCOME_CHANNEL_ID", None),
            rules_channel_id=_int_env("DISCORD_RULES_CHANNEL_ID", None),
            verification_category_id=_int_env("DISCORD_VERIFICATION_CATEGORY_ID", None),
            verification_channel_id=_int_env("DISCORD_VERIFICATION_CHANNEL_ID", None),
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
            visitor_role_id=_int_env("DISCORD_VISITOR_ROLE_ID", None),
            not_verified_role_id=_int_env("DISCORD_NOT_VERIFIED_ROLE_ID", None),
            intern_role_id=_int_env("DISCORD_INTERN_ROLE_ID", None),
            booster_role_id=_int_env("DISCORD_BOOSTER_ROLE_ID", None),
            central_access_role_id=_int_env("DISCORD_CENTRAL_ACCESS_ROLE_ID", None),
            central_auth_code_ttl_seconds=_int_env("CENTRAL_AUTH_CODE_TTL_SECONDS", 600),
            central_auth_session_ttl_seconds=_int_env("CENTRAL_AUTH_SESSION_TTL_SECONDS", 1800),
            central_bridge_url=(
                parse_central_bridge_url(central_bridge_url)[2]
                if central_bridge_url
                else ""
            ),
            central_bridge_key=_central_bridge_key_env(),
            private_call_category_id=_int_env("DISCORD_PRIVATE_CALL_CATEGORY_ID", None),
            automod_channel_id=_int_env("DISCORD_AUTOMOD_CHANNEL_ID", None),
            afk_channel_id=_int_env("DISCORD_AFK_CHANNEL_ID", None),
            website_url=os.getenv("PEACE_SITE_URL", "https://peacegg.com.br").strip(),
            website_media_channel_id=_int_env("PEACE_SITE_MEDIA_CHANNEL_ID", None),
            website_clips_channel_id=_int_env("PEACE_SITE_CLIPS_CHANNEL_ID", None),
            website_media_cache_seconds=max(30, _int_env("PEACE_SITE_MEDIA_CACHE_SECONDS", 300)),
            api_enabled=_bool_env("PEACE_API_ENABLED", True),
            api_host=os.getenv("PEACE_API_HOST", "0.0.0.0").strip() or "0.0.0.0",
            api_port=_int_env("PEACE_API_PORT", _int_env("PORT", 8080)),
            discord_invite_url=_discord_invite_env(),
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
            set_vagas_abertas=_bool_env("SET_VAGAS_ABERTAS", True),
            developer_vagas_abertas=_bool_env("SET_DEVELOPER_VAGAS_ABERTAS"),
            staff_vagas_abertas=_bool_env("SET_STAFF_VAGAS_ABERTAS"),
            username_min_length=_int_env("SET_USERNAME_MIN_LENGTH", 3),
            username_max_length=_int_env("SET_USERNAME_MAX_LENGTH", 20),
        )
        configured_role_ids = {
            "DISCORD_PEACE_ROLE_ID": settings.peace_role_id,
            "DISCORD_NOVATO_ROLE_ID": settings.novato_role_id,
            "DISCORD_STAFF_ROLE_ID": settings.staff_role_id,
            "DISCORD_MANAGER_ROLE_ID": settings.manager_role_id,
            "DISCORD_VISITOR_ROLE_ID": settings.visitor_role_id,
            "DISCORD_NOT_VERIFIED_ROLE_ID": settings.not_verified_role_id,
            "DISCORD_INTERN_ROLE_ID": settings.intern_role_id,
            "DISCORD_BOOSTER_ROLE_ID": settings.booster_role_id,
            "DISCORD_CENTRAL_ACCESS_ROLE_ID": settings.central_access_role_id,
        }
        try:
            if (__package__ or "").startswith("bot."):
                from ..operations.maintenance import ROLE_IDS
            else:
                from operations.maintenance import ROLE_IDS
            configured_role_ids["existing Founder role"] = int(ROLE_IDS["founder"])
        except (ImportError, KeyError, TypeError, ValueError):
            pass
        _validate_unique_role_ids(configured_role_ids)
        return settings

