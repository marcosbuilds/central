from __future__ import annotations

import json
import hashlib
import hmac
import secrets
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

if (__package__ or "").startswith("bot."):
    from ..core.identity import prefix_for_roles
else:
    from core.identity import prefix_for_roles


SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS members (
    discord_user_id TEXT PRIMARY KEY,
    username TEXT NOT NULL,
    global_name TEXT,
    display_name TEXT,
    nickname TEXT,
    peace_id INTEGER NOT NULL UNIQUE,
    name_prefix TEXT NOT NULL DEFAULT 'N',
    joined_at TEXT,
    is_founder INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS member_roles (
    discord_user_id TEXT NOT NULL REFERENCES members(discord_user_id) ON DELETE CASCADE,
    role_id TEXT NOT NULL,
    role_name TEXT NOT NULL,
    PRIMARY KEY (discord_user_id, role_id)
);

CREATE TABLE IF NOT EXISTS peace_id_pool (
    peace_id INTEGER PRIMARY KEY,
    released_from TEXT NOT NULL,
    released_at TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'available',
    release_reason TEXT NOT NULL DEFAULT 'unknown',
    release_actor_id TEXT
);

CREATE TABLE IF NOT EXISTS peace_return_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    old_peace_id INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    message_id TEXT,
    loss_reason TEXT NOT NULL DEFAULT 'unknown',
    loss_actor_id TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    new_peace_id INTEGER
);

CREATE TABLE IF NOT EXISTS set_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    in_game_username TEXT NOT NULL,
    rg_in_game TEXT NOT NULL,
    telefone_in_game TEXT NOT NULL,
    source TEXT NOT NULL,
    recruiter_user_id TEXT,
    status TEXT NOT NULL DEFAULT 'approved',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS developer_requests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    full_name TEXT NOT NULL,
    nickname TEXT NOT NULL,
    motivation TEXT NOT NULL,
    area TEXT NOT NULL,
    specialization_time TEXT NOT NULL,
    previous_experience TEXT NOT NULL,
    portfolio TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    meeting_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS builder_objects (
    object_type TEXT NOT NULL,
    object_id TEXT PRIMARY KEY,
    created_by TEXT NOT NULL,
    last_editor_user_id TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bot_messages (
    message_id TEXT PRIMARY KEY,
    channel_id TEXT NOT NULL,
    created_at TEXT,
    title TEXT,
    custom_ids TEXT NOT NULL DEFAULT '[]',
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    collected_at TEXT NOT NULL,
    guild_id TEXT NOT NULL,
    member_count INTEGER NOT NULL,
    peace_member_count INTEGER NOT NULL,
    bot_message_count INTEGER NOT NULL,
    source_file TEXT
);

CREATE TABLE IF NOT EXISTS clocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT,
    duration_seconds INTEGER,
    closed_by TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    channel_id TEXT NOT NULL UNIQUE,
    owner_user_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    details TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'open',
    claimed_by TEXT,
    voice_channel_id TEXT,
    created_at TEXT NOT NULL,
    closed_at TEXT,
    closed_by TEXT
);

CREATE TABLE IF NOT EXISTS booster_spaces (
    owner_user_id TEXT PRIMARY KEY,
    role_id TEXT NOT NULL UNIQUE,
    voice_channel_id TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS absences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    start_date TEXT NOT NULL,
    end_date TEXT NOT NULL,
    reason TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS farms (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    delivered_by TEXT NOT NULL,
    received_by TEXT NOT NULL,
    delivered_value INTEGER NOT NULL,
    counted_value INTEGER NOT NULL,
    goals_paid INTEGER NOT NULL,
    paid_days TEXT NOT NULL,
    proof_url TEXT,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS iris_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    scope TEXT NOT NULL,
    channel_id TEXT,
    ticket_id INTEGER,
    actor_user_id TEXT,
    metadata_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS central_login_challenges (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    peace_id INTEGER NOT NULL,
    client_id TEXT NOT NULL DEFAULT '',
    code_hash TEXT NOT NULL,
    code_salt TEXT NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    consumed_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_central_login_challenges_user
    ON central_login_challenges(discord_user_id, id DESC);

CREATE TABLE IF NOT EXISTS central_login_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    discord_user_id TEXT NOT NULL,
    peace_id INTEGER NOT NULL,
    client_id TEXT NOT NULL,
    project_id TEXT,
    scope TEXT NOT NULL,
    token_hash TEXT NOT NULL,
    token_salt TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    revoked_at TEXT
);

CREATE INDEX IF NOT EXISTS idx_central_login_sessions_client
    ON central_login_sessions(client_id, id DESC);
"""


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _central_code_hash(code: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        code.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()


def _central_token_hash(token: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac(
        "sha256",
        token.encode("utf-8"),
        salt.encode("utf-8"),
        120_000,
    ).hex()


def _role_prefix(
    member: dict[str, Any],
    role_names: Iterable[str],
    founder_id: int,
    role_positions: Mapping[str, int] | None = None,
    role_hoist: Mapping[str, bool] | None = None,
) -> str:
    return str(
        prefix_for_roles(
            user_id=int(member["user"]["id"]),
            role_names=role_names,
            founder_user_id=founder_id,
            founder_role_names=("Founder Peace", "Founder"),
            default="N",
            role_positions=role_positions,
            role_hoist=role_hoist,
        )
    )


class PeaceDatabase:
    def __init__(self, path: Path):
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA)
            columns = {row["name"] for row in connection.execute("PRAGMA table_info(tickets)")}
            if "voice_channel_id" not in columns:
                connection.execute("ALTER TABLE tickets ADD COLUMN voice_channel_id TEXT")
            if "closed_by" not in columns:
                connection.execute("ALTER TABLE tickets ADD COLUMN closed_by TEXT")
            pool_columns = {row["name"] for row in connection.execute("PRAGMA table_info(peace_id_pool)")}
            if "status" not in pool_columns:
                connection.execute(
                    "ALTER TABLE peace_id_pool ADD COLUMN status TEXT NOT NULL DEFAULT 'available'"
                )
            if "release_reason" not in pool_columns:
                connection.execute(
                    "ALTER TABLE peace_id_pool ADD COLUMN release_reason TEXT NOT NULL DEFAULT 'unknown'"
                )
            if "release_actor_id" not in pool_columns:
                connection.execute(
                    "ALTER TABLE peace_id_pool ADD COLUMN release_actor_id TEXT"
                )
            return_columns = {row["name"] for row in connection.execute("PRAGMA table_info(peace_return_requests)")}
            if "loss_reason" not in return_columns:
                connection.execute(
                    "ALTER TABLE peace_return_requests ADD COLUMN loss_reason TEXT NOT NULL DEFAULT 'unknown'"
                )
            if "loss_actor_id" not in return_columns:
                connection.execute(
                    "ALTER TABLE peace_return_requests ADD COLUMN loss_actor_id TEXT"
                )
            developer_columns = {row["name"] for row in connection.execute("PRAGMA table_info(developer_requests)")}
            if developer_columns and "motivation" not in developer_columns:
                connection.execute("ALTER TABLE developer_requests ADD COLUMN motivation TEXT NOT NULL DEFAULT ''")
            challenge_columns = {row["name"] for row in connection.execute("PRAGMA table_info(central_login_challenges)")}
            if challenge_columns and "client_id" not in challenge_columns:
                connection.execute("ALTER TABLE central_login_challenges ADD COLUMN client_id TEXT NOT NULL DEFAULT ''")
            connection.commit()

    def _next_peace_id(self, connection: sqlite3.Connection) -> int:
        reusable = connection.execute(
            "SELECT peace_id FROM peace_id_pool WHERE peace_id > 0 AND status = 'available' ORDER BY peace_id LIMIT 1"
        ).fetchone()
        if reusable is not None:
            peace_id = int(reusable["peace_id"])
            connection.execute("DELETE FROM peace_id_pool WHERE peace_id = ?", (peace_id,))
            return peace_id
        row = connection.execute(
            "SELECT COALESCE(MAX(CASE WHEN peace_id > 0 THEN peace_id END), 0) + 1 AS next_id FROM members"
        ).fetchone()
        return int(row["next_id"])

    def import_snapshot(
        self,
        *,
        members: list[dict[str, Any]],
        roles_by_id: dict[str, dict[str, Any]],
        bot_messages: list[dict[str, Any]],
        founder_id: int,
        guild_id: int,
        source_file: str | None = None,
        randomize_new_ids: bool = True,
    ) -> dict[str, int]:
        self.initialize()
        current_time = now_iso()
        with self.connect() as connection:
            existing = {
                row["discord_user_id"]: row
                for row in connection.execute("SELECT * FROM members").fetchall()
            }
            ordered = list(members)
            if randomize_new_ids:
                secrets.SystemRandom().shuffle(ordered)
            next_id = self._next_peace_id(connection)
            imported = 0
            new_ids = 0
            for member in ordered:
                user = member["user"]
                user_id = str(user["id"])
                role_ids = [str(role_id) for role_id in member.get("roles", [])]
                role_names = [str(roles_by_id.get(role_id, {}).get("name", role_id)) for role_id in role_ids]
                role_positions = {
                    str(role.get("name", role_id)): int(role.get("position", 0))
                    for role_id, role in roles_by_id.items()
                    if isinstance(role, dict)
                }
                role_hoist = {
                    str(role.get("name", role_id)): bool(role.get("hoist", False))
                    for role_id, role in roles_by_id.items()
                    if isinstance(role, dict)
                }
                previous = existing.get(user_id)
                if previous is not None:
                    peace_id = int(previous["peace_id"])
                elif int(user_id) == founder_id:
                    peace_id = 0
                else:
                    while next_id == 0:
                        next_id += 1
                    peace_id = next_id
                    next_id += 1
                    new_ids += 1
                prefix = _role_prefix(member, role_names, founder_id, role_positions, role_hoist)
                connection.execute(
                    """
                    INSERT INTO members (
                        discord_user_id, username, global_name, display_name, nickname,
                        peace_id, name_prefix, joined_at, is_founder, created_at, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(discord_user_id) DO UPDATE SET
                        username=excluded.username,
                        global_name=excluded.global_name,
                        display_name=excluded.display_name,
                        nickname=excluded.nickname,
                        name_prefix=excluded.name_prefix,
                        joined_at=excluded.joined_at,
                        is_founder=excluded.is_founder,
                        updated_at=excluded.updated_at
                    """,
                    (
                        user_id,
                        str(user.get("username", "")),
                        user.get("global_name"),
                        member.get("display_name") or user.get("global_name") or user.get("username"),
                        member.get("nick"),
                        peace_id,
                        prefix,
                        member.get("joined_at"),
                        int(int(user_id) == founder_id),
                        current_time,
                        current_time,
                    ),
                )
                connection.execute("DELETE FROM member_roles WHERE discord_user_id = ?", (user_id,))
                connection.executemany(
                    "INSERT INTO member_roles (discord_user_id, role_id, role_name) VALUES (?, ?, ?)",
                    [(user_id, role_id, roles_by_id.get(role_id, {}).get("name", role_id)) for role_id in role_ids],
                )
                imported += 1

            connection.executemany(
                """
                INSERT INTO bot_messages (message_id, channel_id, created_at, title, custom_ids, payload_json)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(message_id) DO UPDATE SET
                    channel_id=excluded.channel_id,
                    created_at=excluded.created_at,
                    title=excluded.title,
                    custom_ids=excluded.custom_ids,
                    payload_json=excluded.payload_json
                """,
                [
                    (
                        str(message["id"]),
                        str(message.get("channel_id", "")),
                        message.get("timestamp"),
                        (message.get("embeds") or [{}])[0].get("title"),
                        json.dumps(_custom_ids(message), ensure_ascii=False),
                        json.dumps(message, ensure_ascii=False),
                    )
                    for message in bot_messages
                ],
            )
            connection.execute(
                """
                INSERT INTO snapshots
                    (collected_at, guild_id, member_count, peace_member_count, bot_message_count, source_file)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (current_time, str(guild_id), len(members), len(members), len(bot_messages), source_file),
            )
            connection.commit()
        return {"members": imported, "new_ids": new_ids, "bot_messages": len(bot_messages)}

    def get_member(self, discord_user_id: int | str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM members WHERE discord_user_id = ?", (str(discord_user_id),)
            ).fetchone()

    def member_by_peace_id(self, peace_id: int | str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM members WHERE peace_id = ?", (int(peace_id),)
            ).fetchone()

    def create_central_login_challenge(
        self,
        *,
        discord_user_id: int,
        peace_id: int,
        code: str,
        expires_at: str,
        client_id: str = "",
    ) -> int:
        self.initialize()
        timestamp = now_iso()
        salt = secrets.token_hex(16)
        code_hash = _central_code_hash(code, salt)
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE central_login_challenges
                SET consumed_at = ?
                WHERE discord_user_id = ? AND consumed_at IS NULL
                """,
                (timestamp, str(discord_user_id)),
            )
            cursor = connection.execute(
                """
                INSERT INTO central_login_challenges (
                    discord_user_id, peace_id, client_id, code_hash, code_salt,
                    attempts, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    str(discord_user_id),
                    int(peace_id),
                    client_id,
                    code_hash,
                    salt,
                    timestamp,
                    expires_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def try_create_central_login_challenge(
        self,
        *,
        discord_user_id: int,
        peace_id: int,
        client_id: str,
        code: str,
        expires_at: str,
        window_seconds: int = 600,
        max_user_requests: int = 3,
        max_client_requests: int = 6,
    ) -> int | None:
        """Atomically enforce request throttles before storing a challenge."""
        self.initialize()
        timestamp = now_iso()
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()
        salt = secrets.token_hex(16)
        code_hash = _central_code_hash(code, salt)
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            user_count = connection.execute(
                """
                SELECT COUNT(*) AS total FROM central_login_challenges
                WHERE discord_user_id = ? AND created_at >= ?
                """,
                (str(discord_user_id), cutoff),
            ).fetchone()["total"]
            client_count = connection.execute(
                """
                SELECT COUNT(*) AS total FROM central_login_challenges
                WHERE client_id = ? AND created_at >= ?
                """,
                (client_id, cutoff),
            ).fetchone()["total"]
            if int(user_count) >= max_user_requests or int(client_count) >= max_client_requests:
                connection.rollback()
                return None
            connection.execute(
                """
                UPDATE central_login_challenges
                SET consumed_at = ?
                WHERE discord_user_id = ? AND consumed_at IS NULL
                """,
                (timestamp, str(discord_user_id)),
            )
            cursor = connection.execute(
                """
                INSERT INTO central_login_challenges (
                    discord_user_id, peace_id, client_id, code_hash, code_salt,
                    attempts, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, 0, ?, ?)
                """,
                (
                    str(discord_user_id),
                    int(peace_id),
                    client_id,
                    code_hash,
                    salt,
                    timestamp,
                    expires_at,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def central_login_request_allowed(
        self,
        *,
        discord_user_id: int,
        client_id: str,
        window_seconds: int = 600,
        max_user_requests: int = 3,
        max_client_requests: int = 6,
    ) -> bool:
        self.initialize()
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=window_seconds)).isoformat()
        with self.connect() as connection:
            user_count = connection.execute(
                """
                SELECT COUNT(*) AS total FROM central_login_challenges
                WHERE discord_user_id = ? AND created_at >= ?
                """,
                (str(discord_user_id), cutoff),
            ).fetchone()["total"]
            client_count = connection.execute(
                """
                SELECT COUNT(*) AS total FROM central_login_challenges
                WHERE client_id = ? AND created_at >= ?
                """,
                (client_id, cutoff),
            ).fetchone()["total"]
        return int(user_count) < max_user_requests and int(client_count) < max_client_requests

    def revoke_central_login_challenges(
        self,
        discord_user_id: int | str,
        client_id: str | None = None,
    ) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE central_login_challenges
                SET consumed_at = COALESCE(consumed_at, ?)
                WHERE discord_user_id = ?
                  AND consumed_at IS NULL
                  AND (? IS NULL OR client_id = ?)
                """,
                (now_iso(), str(discord_user_id), client_id, client_id),
            )
            connection.commit()

    def consume_central_login_challenge(
        self,
        *,
        discord_user_id: int,
        peace_id: int,
        code: str,
        client_id: str = "",
        max_attempts: int = 5,
    ) -> bool:
        self.initialize()
        timestamp = now_iso()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM central_login_challenges
                WHERE discord_user_id = ? AND peace_id = ?
                  AND client_id = ?
                  AND consumed_at IS NULL
                ORDER BY id DESC LIMIT 1
                """,
                (str(discord_user_id), int(peace_id), client_id),
            ).fetchone()
            if row is None or row["expires_at"] <= timestamp or int(row["attempts"]) >= max_attempts:
                return False
            connection.execute(
                "UPDATE central_login_challenges SET attempts = attempts + 1 WHERE id = ?",
                (int(row["id"]),),
            )
            valid = hmac.compare_digest(
                str(row["code_hash"]),
                _central_code_hash(code, str(row["code_salt"])),
            )
            if valid:
                connection.execute(
                    "UPDATE central_login_challenges SET consumed_at = ? WHERE id = ?",
                    (timestamp, int(row["id"])),
                )
            connection.commit()
            return valid

    def create_central_login_session(
        self,
        *,
        discord_user_id: int,
        peace_id: int,
        client_id: str,
        project_id: str | None,
        scope: str,
        expires_at: str,
    ) -> str:
        self.initialize()
        token = secrets.token_urlsafe(32)
        salt = secrets.token_hex(16)
        token_hash = _central_token_hash(token, salt)
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO central_login_sessions (
                    discord_user_id, peace_id, client_id, project_id, scope,
                    token_hash, token_salt, created_at, expires_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(discord_user_id),
                    int(peace_id),
                    client_id,
                    project_id,
                    scope,
                    token_hash,
                    salt,
                    now_iso(),
                    expires_at,
                ),
            )
            connection.commit()
        return token

    def validate_central_login_session(
        self,
        *,
        token: str,
        client_id: str,
        project_id: str | None = None,
    ) -> sqlite3.Row | None:
        self.initialize()
        timestamp = now_iso()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM central_login_sessions
                WHERE client_id = ? AND revoked_at IS NULL AND expires_at > ?
                ORDER BY id DESC
                """,
                (client_id, timestamp),
            ).fetchall()
        for row in rows:
            if project_id is not None and row["project_id"] != project_id:
                continue
            if hmac.compare_digest(
                str(row["token_hash"]),
                _central_token_hash(token, str(row["token_salt"])),
            ):
                return row
        return None

    def revoke_central_login_session(self, *, token: str, client_id: str) -> bool:
        row = self.validate_central_login_session(token=token, client_id=client_id)
        if row is None:
            return False
        with self.connect() as connection:
            connection.execute(
                "UPDATE central_login_sessions SET revoked_at = ? WHERE id = ?",
                (now_iso(), int(row["id"])),
            )
            connection.commit()
        return True

    def update_nickname(self, discord_user_id: int | str, nickname: str) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                "UPDATE members SET nickname = ?, updated_at = ? WHERE discord_user_id = ?",
                (nickname, now_iso(), str(discord_user_id)),
            )
            connection.commit()

    def release_peace_member(
        self,
        discord_user_id: int | str,
        *,
        reason: str = "vínculo Peace removido manualmente",
        actor_user_id: int | str | None = None,
    ) -> sqlite3.Row | None:
        """Remove o vínculo Peace e libera o ID para o próximo set."""
        self.initialize()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            row = connection.execute(
                "SELECT * FROM members WHERE discord_user_id = ?", (str(discord_user_id),)
            ).fetchone()
            if row is None or int(row["is_founder"]):
                return None
            connection.execute(
                """
                INSERT OR REPLACE INTO peace_id_pool (
                    peace_id, released_from, released_at, status, release_reason, release_actor_id
                ) VALUES (?, ?, ?, 'available', ?, ?)
                """,
                (
                    int(row["peace_id"]),
                    str(discord_user_id),
                    now_iso(),
                    reason,
                    str(actor_user_id) if actor_user_id is not None else None,
                ),
            )
            connection.execute("DELETE FROM members WHERE discord_user_id = ?", (str(discord_user_id),))
            connection.commit()
            return row

    def available_peace_id_for_user(self, discord_user_id: int | str) -> sqlite3.Row | None:
        """Return a previously released ID for an already-completed operation."""
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM peace_id_pool
                WHERE released_from = ? AND status = 'available'
                ORDER BY released_at DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()

    def manual_peace_releases_for_cleanup(self) -> list[sqlite3.Row]:
        """Return legacy manual releases that still need Discord cleanup.

        The reason filter excludes the old ID release that happens during an
        approved return. A current ``members`` row also wins over a stale pool
        row, so a later set can never be removed by this repair pass.
        """
        self.initialize()
        with self.connect() as connection:
            return list(
                connection.execute(
                    """
                    SELECT pool.*
                    FROM peace_id_pool AS pool
                    LEFT JOIN members
                      ON members.discord_user_id = pool.released_from
                    WHERE pool.status = 'available'
                      AND pool.release_reason LIKE 'vínculo Peace removido manualmente por Founder%'
                      AND members.discord_user_id IS NULL
                    ORDER BY pool.released_at, pool.peace_id
                    """
                ).fetchall()
            )

    def reserve_peace_member(
        self,
        discord_user_id: int | str,
        *,
        reason: str = "cargo Peace perdido",
        actor_user_id: int | str | None = None,
    ) -> sqlite3.Row | None:
        """Reserva o ID de quem saiu com Peace, sem permitir reutilização automática."""
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT * FROM members WHERE discord_user_id = ?",
                (str(discord_user_id),),
            ).fetchone()
            if row is None or int(row["is_founder"]):
                return None
            connection.execute(
                """
                INSERT OR REPLACE INTO peace_id_pool (
                    peace_id, released_from, released_at, status, release_reason, release_actor_id
                ) VALUES (?, ?, ?, 'reserved', ?, ?)
                """,
                (
                    int(row["peace_id"]),
                    str(discord_user_id),
                    now_iso(),
                    reason,
                    str(actor_user_id) if actor_user_id is not None else None,
                ),
            )
            connection.execute("DELETE FROM members WHERE discord_user_id = ?", (str(discord_user_id),))
            connection.commit()
            return row

    def recorded_peace_member(self, discord_user_id: int | str, peace_role_id: int) -> bool:
        """Return whether the local record still proves that the member had Peace."""
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT 1
                FROM members
                JOIN member_roles ON member_roles.discord_user_id = members.discord_user_id
                WHERE members.discord_user_id = ?
                  AND members.is_founder = 0
                  AND members.peace_id > 0
                  AND member_roles.role_id = ?
                LIMIT 1
                """,
                (str(discord_user_id), str(peace_role_id)),
            ).fetchone()
        return row is not None

    def annotate_peace_reservation(
        self,
        discord_user_id: int | str,
        *,
        reason: str,
        actor_user_id: int | str | None = None,
    ) -> bool:
        """Append a lifecycle event to an existing reservation without releasing it."""
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                """
                SELECT release_reason, release_actor_id
                FROM peace_id_pool
                WHERE released_from = ? AND status = 'reserved'
                ORDER BY released_at DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()
            if row is None:
                return False
            previous = str(row["release_reason"] or "unknown")
            combined = reason if previous in {"", "unknown"} else f"{previous}; {reason}"
            connection.execute(
                """
                UPDATE peace_id_pool
                SET release_reason = ?,
                    release_actor_id = COALESCE(release_actor_id, ?),
                    released_at = ?
                WHERE released_from = ? AND status = 'reserved'
                """,
                (
                    combined,
                    str(actor_user_id) if actor_user_id is not None else None,
                    now_iso(),
                    str(discord_user_id),
                ),
            )
            connection.execute(
                """
                UPDATE peace_return_requests
                SET loss_reason = ?,
                    loss_actor_id = COALESCE(loss_actor_id, ?)
                WHERE discord_user_id = ? AND status = 'pending'
                """,
                (
                    combined,
                    str(actor_user_id) if actor_user_id is not None else None,
                    str(discord_user_id),
                ),
            )
            connection.commit()
        return True

    def reserve_missing_peace_members(
        self,
        *,
        current_user_ids: set[int],
        peace_role_id: int,
        current_peace_user_ids: set[int] | None = None,
    ) -> list[sqlite3.Row]:
        """Reserve active Peace records missing from the current member/role snapshot.

        ``members`` is populated only for Peace members (or the Founder), so
        checking the active table directly is intentional. A stale
        ``member_roles`` snapshot must not hide a record whose live Discord
        member no longer has the Peace role.
        """
        self.initialize()
        reserved: list[sqlite3.Row] = []
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT members.*
                FROM members
                WHERE members.peace_id > 0 AND members.is_founder = 0
                """,
            ).fetchall()
            for row in rows:
                user_id = int(row["discord_user_id"])
                if user_id in current_user_ids and (
                    current_peace_user_ids is None or user_id in current_peace_user_ids
                ):
                    continue
                reason = (
                    "registro Peace sem membro após auditoria de inicialização"
                    if user_id not in current_user_ids
                    else "cargo Peace ausente após auditoria de inicialização"
                )
                connection.execute(
                    """
                    INSERT OR REPLACE INTO peace_id_pool (
                        peace_id, released_from, released_at, status, release_reason, release_actor_id
                    ) VALUES (?, ?, ?, 'reserved', ?, NULL)
                    """,
                    (int(row["peace_id"]), str(user_id), now_iso(), reason),
                )
                connection.execute(
                    "DELETE FROM members WHERE discord_user_id = ?",
                    (str(user_id),),
                )
                reserved.append(row)
            connection.commit()
        return reserved

    def reserved_peace_id_for_user(self, discord_user_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM peace_id_pool
                WHERE released_from = ? AND status = 'reserved'
                ORDER BY released_at DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()

    def latest_return_request_for_user(self, discord_user_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM peace_return_requests
                WHERE discord_user_id = ?
                ORDER BY id DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()

    def save_return_request(
        self,
        *,
        discord_user_id: int,
        old_peace_id: int,
        loss_reason: str = "retorno Peace pendente",
        loss_actor_id: int | str | None = None,
    ) -> int:
        self.initialize()
        timestamp = now_iso()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO peace_return_requests (
                    discord_user_id, old_peace_id, status, loss_reason, loss_actor_id, created_at
                ) VALUES (?, ?, 'pending', ?, ?, ?)
                """,
                (
                    str(discord_user_id),
                    int(old_peace_id),
                    loss_reason,
                    str(loss_actor_id) if loss_actor_id is not None else None,
                    timestamp,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def get_or_create_return_request(
        self,
        *,
        discord_user_id: int,
        old_peace_id: int,
        loss_reason: str,
        loss_actor_id: int | str | None = None,
    ) -> tuple[sqlite3.Row, bool]:
        """Atomically deduplicate pending return requests for one member."""
        self.initialize()
        timestamp = now_iso()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                """
                SELECT * FROM peace_return_requests
                WHERE discord_user_id = ? AND status = 'pending'
                ORDER BY id DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()
            if existing is not None:
                connection.commit()
                return existing, False
            cursor = connection.execute(
                """
                INSERT INTO peace_return_requests (
                    discord_user_id, old_peace_id, status, loss_reason, loss_actor_id, created_at
                ) VALUES (?, ?, 'pending', ?, ?, ?)
                """,
                (
                    str(discord_user_id),
                    int(old_peace_id),
                    loss_reason,
                    str(loss_actor_id) if loss_actor_id is not None else None,
                    timestamp,
                ),
            )
            created = connection.execute(
                "SELECT * FROM peace_return_requests WHERE id = ?",
                (int(cursor.lastrowid),),
            ).fetchone()
            connection.commit()
        assert created is not None
        return created, True

    def reject_return_request(self, request_id: int | str) -> sqlite3.Row | None:
        """Reject a pending return while keeping its Peace ID reserved."""
        self.initialize()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            request = connection.execute(
                "SELECT * FROM peace_return_requests WHERE id = ? AND status = 'pending'",
                (str(request_id),),
            ).fetchone()
            if request is None:
                connection.rollback()
                return None
            reservation = connection.execute(
                """
                SELECT 1 FROM peace_id_pool
                WHERE peace_id = ? AND released_from = ? AND status = 'reserved'
                """,
                (int(request["old_peace_id"]), str(request["discord_user_id"])),
            ).fetchone()
            if reservation is None:
                connection.rollback()
                return None
            cursor = connection.execute(
                """
                UPDATE peace_return_requests
                SET status = 'rejected', resolved_at = ?, new_peace_id = NULL
                WHERE id = ? AND status = 'pending'
                """,
                (now_iso(), str(request_id)),
            )
            if cursor.rowcount != 1:
                connection.rollback()
                return None
            row = connection.execute(
                "SELECT * FROM peace_return_requests WHERE id = ?",
                (str(request_id),),
            ).fetchone()
            connection.commit()
            return row

    def return_request(self, request_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM peace_return_requests WHERE id = ?",
                (str(request_id),),
            ).fetchone()

    def pending_return_request_for_user(self, discord_user_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM peace_return_requests
                WHERE discord_user_id = ? AND status = 'pending'
                ORDER BY id DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()

    def pending_return_requests(self) -> list[sqlite3.Row]:
        self.initialize()
        with self.connect() as connection:
            return list(connection.execute(
                "SELECT * FROM peace_return_requests WHERE status = 'pending' ORDER BY id"
            ).fetchall())

    def approved_return_requests(self) -> list[sqlite3.Row]:
        self.initialize()
        with self.connect() as connection:
            return list(connection.execute(
                """
                SELECT * FROM peace_return_requests
                WHERE status = 'approved' AND new_peace_id IS NOT NULL
                ORDER BY id
                """
            ).fetchall())

    def approved_return_user_ids(self) -> set[int]:
        self.initialize()
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT DISTINCT discord_user_id
                FROM peace_return_requests
                WHERE status = 'approved' AND new_peace_id IS NOT NULL
                """
            ).fetchall()
        return {int(row["discord_user_id"]) for row in rows}

    def set_return_request_message(self, request_id: int | str, message_id: int | str) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                "UPDATE peace_return_requests SET message_id = ? WHERE id = ?",
                (str(message_id), str(request_id)),
            )
            connection.commit()

    def approve_return_request(
        self,
        request_id: int | str,
        *,
        username: str,
        nickname: str | None,
        role_ids: list[int],
        role_names: list[str],
        founder_id: int,
        role_positions: Mapping[str, int] | None = None,
        role_hoist: Mapping[str, bool] | None = None,
    ) -> tuple[sqlite3.Row, int, int] | None:
        """Libera o ID reservado e registra um novo ID para o retorno aprovado."""
        self.initialize()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            request = connection.execute(
                "SELECT * FROM peace_return_requests WHERE id = ? AND status = 'pending'",
                (str(request_id),),
            ).fetchone()
            if request is None:
                return None
            reservation = connection.execute(
                """
                SELECT * FROM peace_id_pool
                WHERE peace_id = ? AND released_from = ? AND status = 'reserved'
                """,
                (int(request["old_peace_id"]), str(request["discord_user_id"])),
            ).fetchone()
            if reservation is None:
                return None
            max_row = connection.execute(
                """
                SELECT MAX(peace_id) AS max_id FROM (
                    SELECT peace_id FROM members
                    UNION ALL
                    SELECT peace_id FROM peace_id_pool
                )
                """
            ).fetchone()
            new_peace_id = max(int(max_row["max_id"] or 0) + 1, 1)
            timestamp = now_iso()
            connection.execute(
                "UPDATE peace_id_pool SET status = 'available' WHERE peace_id = ?",
                (int(request["old_peace_id"]),),
            )
            connection.execute(
                "DELETE FROM members WHERE discord_user_id = ?",
                (str(request["discord_user_id"]),),
            )
            prefix = _role_prefix(
                {"user": {"id": str(request["discord_user_id"])}},
                role_names,
                founder_id,
                role_positions,
                role_hoist,
            )
            connection.execute(
                """
                INSERT INTO members (
                    discord_user_id, username, global_name, display_name, nickname,
                    peace_id, name_prefix, is_founder, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(request["discord_user_id"]),
                    username,
                    None,
                    username,
                    nickname,
                    new_peace_id,
                    prefix,
                    int(int(request["discord_user_id"]) == founder_id),
                    timestamp,
                    timestamp,
                ),
            )
            connection.executemany(
                "INSERT INTO member_roles (discord_user_id, role_id, role_name) VALUES (?, ?, ?)",
                [
                    (str(request["discord_user_id"]), str(role_id), name)
                    for role_id, name in zip(role_ids, role_names)
                ],
            )
            connection.execute(
                """
                UPDATE peace_return_requests
                SET status = 'approved', resolved_at = ?, new_peace_id = ?
                WHERE id = ?
                """,
                (timestamp, new_peace_id, str(request_id)),
            )
            connection.commit()
            return request, int(request["old_peace_id"]), new_peace_id

    def rollback_return_approval(self, request_id: int | str) -> bool:
        """Restore a pending return when Discord role/nickname mutation failed."""
        self.initialize()
        with self.connect() as connection:
            connection.execute("BEGIN IMMEDIATE")
            request = connection.execute(
                """
                SELECT * FROM peace_return_requests
                WHERE id = ? AND status = 'approved' AND new_peace_id IS NOT NULL
                """,
                (str(request_id),),
            ).fetchone()
            if request is None:
                connection.rollback()
                return False
            current_member = connection.execute(
                "SELECT peace_id FROM members WHERE discord_user_id = ?",
                (str(request["discord_user_id"]),),
            ).fetchone()
            if current_member is not None and int(current_member["peace_id"]) != int(request["new_peace_id"]):
                connection.rollback()
                return False
            connection.execute(
                "DELETE FROM members WHERE discord_user_id = ?",
                (str(request["discord_user_id"]),),
            )
            connection.execute(
                """
                INSERT OR REPLACE INTO peace_id_pool (
                    peace_id, released_from, released_at, status, release_reason, release_actor_id
                ) VALUES (?, ?, ?, 'reserved', ?, ?)
                """,
                (
                    int(request["old_peace_id"]),
                    str(request["discord_user_id"]),
                    now_iso(),
                    str(request["loss_reason"] or "retorno pendente"),
                    request["loss_actor_id"],
                ),
            )
            connection.execute(
                """
                UPDATE peace_return_requests
                SET status = 'pending', resolved_at = NULL, new_peace_id = NULL
                WHERE id = ?
                """,
                (str(request_id),),
            )
            connection.commit()
        return True

    def ensure_runtime_member(
        self,
        *,
        discord_user_id: int,
        username: str,
        nickname: str | None,
        role_ids: list[int],
        role_names: list[str],
        founder_id: int,
        role_positions: Mapping[str, int] | None = None,
        role_hoist: Mapping[str, bool] | None = None,
    ) -> int:
        self.initialize()
        existing = self.get_member(discord_user_id)
        if existing:
            with self.connect() as connection:
                timestamp = now_iso()
                prefix = _role_prefix(
                    {"user": {"id": str(discord_user_id)}},
                    role_names,
                    founder_id,
                    role_positions,
                    role_hoist,
                )
                connection.execute(
                    """
                    UPDATE members
                    SET username = ?, nickname = ?, name_prefix = ?, updated_at = ?
                    WHERE discord_user_id = ?
                    """,
                    (username, nickname, prefix, timestamp, str(discord_user_id)),
                )
                connection.execute("DELETE FROM member_roles WHERE discord_user_id = ?", (str(discord_user_id),))
                connection.executemany(
                    "INSERT INTO member_roles (discord_user_id, role_id, role_name) VALUES (?, ?, ?)",
                    [(str(discord_user_id), str(role_id), name) for role_id, name in zip(role_ids, role_names)],
                )
                connection.commit()
            return int(existing["peace_id"])
        with self.connect() as connection:
            peace_id = 0 if discord_user_id == founder_id else self._next_peace_id(connection)
            prefix = _role_prefix(
                {"user": {"id": str(discord_user_id)}},
                role_names,
                founder_id,
                role_positions,
                role_hoist,
            )
            timestamp = now_iso()
            connection.execute(
                """
                INSERT INTO members (
                    discord_user_id, username, global_name, display_name, nickname,
                    peace_id, name_prefix, is_founder, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(discord_user_id), username, None, username, nickname, peace_id,
                    prefix, int(discord_user_id == founder_id), timestamp, timestamp,
                ),
            )
            connection.executemany(
                "INSERT INTO member_roles (discord_user_id, role_id, role_name) VALUES (?, ?, ?)",
                [(str(discord_user_id), str(role_id), name) for role_id, name in zip(role_ids, role_names)],
            )
            connection.commit()
            return peace_id

    def save_set_request(
        self,
        *,
        discord_user_id: int,
        in_game_username: str,
        rg_in_game: str,
        telefone_in_game: str,
        source: str,
        recruiter_user_id: int | None,
        status: str = "approved",
    ) -> int:
        self.initialize()
        timestamp = now_iso()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO set_requests (
                    discord_user_id, in_game_username, rg_in_game, telefone_in_game,
                    source, recruiter_user_id, status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(discord_user_id), in_game_username, rg_in_game, telefone_in_game,
                    source, str(recruiter_user_id) if recruiter_user_id else None,
                    status, timestamp, timestamp,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def set_request(self, request_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM set_requests WHERE id = ?",
                (str(request_id),),
            ).fetchone()

    def pending_set_request_for_user(self, discord_user_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM set_requests
                WHERE discord_user_id = ? AND status = 'pending'
                ORDER BY id DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()

    def pending_set_requests(self) -> list[sqlite3.Row]:
        self.initialize()
        with self.connect() as connection:
            return list(connection.execute(
                "SELECT * FROM set_requests WHERE status = 'pending' ORDER BY id"
            ).fetchall())

    def update_set_request_status(self, request_id: int | str, status: str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                "UPDATE set_requests SET status = ?, updated_at = ? WHERE id = ?",
                (status, now_iso(), str(request_id)),
            )
            connection.commit()
        return self.set_request(request_id)

    def save_developer_request(
        self,
        *,
        discord_user_id: int,
        full_name: str,
        nickname: str,
        motivation: str,
        area: str,
        specialization_time: str,
        previous_experience: str,
        portfolio: str,
        status: str = "pending",
    ) -> int:
        self.initialize()
        timestamp = now_iso()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO developer_requests (
                    discord_user_id, full_name, nickname, motivation, area,
                    specialization_time, previous_experience, portfolio,
                    status, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(discord_user_id), full_name, nickname, motivation, area,
                    specialization_time, previous_experience, portfolio,
                    status, timestamp, timestamp,
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def developer_request(self, request_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM developer_requests WHERE id = ?",
                (str(request_id),),
            ).fetchone()

    def pending_developer_request_for_user(self, discord_user_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM developer_requests
                WHERE discord_user_id = ? AND status IN ('pending', 'interview_scheduled', 'approved', 'meeting_scheduled')
                ORDER BY id DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()

    def pending_developer_requests(self) -> list[sqlite3.Row]:
        self.initialize()
        with self.connect() as connection:
            return list(connection.execute(
                "SELECT * FROM developer_requests WHERE status IN ('pending', 'interview_scheduled') ORDER BY id"
            ).fetchall())

    def update_developer_request(
        self,
        request_id: int | str,
        *,
        status: str | None = None,
        meeting_at: str | None = None,
    ) -> sqlite3.Row | None:
        self.initialize()
        changes: list[str] = []
        values: list[str | None] = []
        if status is not None:
            changes.append("status = ?")
            values.append(status)
        if meeting_at is not None:
            changes.append("meeting_at = ?")
            values.append(meeting_at)
        if not changes:
            return self.developer_request(request_id)
        changes.append("updated_at = ?")
        values.append(now_iso())
        values.append(str(request_id))
        with self.connect() as connection:
            connection.execute(
                f"UPDATE developer_requests SET {', '.join(changes)} WHERE id = ?",
                values,
            )
            connection.commit()
        return self.developer_request(request_id)

    def save_builder_object(self, object_type: str, object_id: int | str, actor_user_id: int | str) -> None:
        self.initialize()
        timestamp = now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO builder_objects (
                    object_type, object_id, created_by, last_editor_user_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(object_id) DO UPDATE SET
                    last_editor_user_id = excluded.last_editor_user_id,
                    updated_at = excluded.updated_at
                """,
                (object_type, str(object_id), str(actor_user_id), str(actor_user_id), timestamp, timestamp),
            )
            connection.commit()

    def builder_object(self, object_type: str, object_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM builder_objects WHERE object_type = ? AND object_id = ?",
                (object_type, str(object_id)),
            ).fetchone()

    def touch_builder_object(self, object_type: str, object_id: int | str, actor_user_id: int | str) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE builder_objects
                SET last_editor_user_id = ?, updated_at = ?
                WHERE object_type = ? AND object_id = ?
                """,
                (str(actor_user_id), now_iso(), object_type, str(object_id)),
            )
            connection.commit()

    def active_clock(self, discord_user_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM clocks
                WHERE discord_user_id = ? AND ended_at IS NULL
                ORDER BY id DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()

    def start_clock(self, discord_user_id: int | str) -> sqlite3.Row:
        active = self.active_clock(discord_user_id)
        if active is not None:
            return active
        with self.connect() as connection:
            timestamp = now_iso()
            cursor = connection.execute(
                "INSERT INTO clocks (discord_user_id, started_at) VALUES (?, ?)",
                (str(discord_user_id), timestamp),
            )
            connection.commit()
            row = connection.execute("SELECT * FROM clocks WHERE id = ?", (cursor.lastrowid,)).fetchone()
            if row is None:
                raise RuntimeError("Registro de ponto não encontrado após a criação")
            return row

    def stop_clock(self, discord_user_id: int | str, closed_by: int | str | None = None) -> sqlite3.Row | None:
        active = self.active_clock(discord_user_id)
        if active is None:
            return None
        ended_at = datetime.now(timezone.utc)
        started_at = datetime.fromisoformat(str(active["started_at"]))
        duration = max(0, int((ended_at - started_at).total_seconds()))
        with self.connect() as connection:
            connection.execute(
                """
                UPDATE clocks
                SET ended_at = ?, duration_seconds = ?, closed_by = ?
                WHERE id = ?
                """,
                (ended_at.isoformat(), duration, str(closed_by) if closed_by else None, active["id"]),
            )
            connection.commit()
            return connection.execute("SELECT * FROM clocks WHERE id = ?", (active["id"],)).fetchone()

    def create_ticket(
        self,
        *,
        channel_id: int,
        owner_user_id: int,
        reason: str,
        details: str,
    ) -> int:
        self.initialize()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO tickets
                    (channel_id, owner_user_id, reason, details, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(channel_id), str(owner_user_id), reason, details, now_iso()),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def ticket_by_channel(self, channel_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM tickets WHERE channel_id = ?", (str(channel_id),)
            ).fetchone()

    def ticket_for_owner(self, discord_user_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT * FROM tickets
                WHERE owner_user_id = ? AND status = 'open'
                ORDER BY id DESC LIMIT 1
                """,
                (str(discord_user_id),),
            ).fetchone()

    def open_tickets(self) -> list[sqlite3.Row]:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM tickets WHERE status = 'open' ORDER BY id"
            ).fetchall()

    def claim_ticket(self, channel_id: int | str, staff_user_id: int | str) -> sqlite3.Row | None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE tickets SET claimed_by = ? WHERE channel_id = ? AND status = 'open'",
                (str(staff_user_id), str(channel_id)),
            )
            connection.commit()
        return self.ticket_by_channel(channel_id)

    def set_ticket_voice(self, channel_id: int | str, voice_channel_id: int | str) -> sqlite3.Row | None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE tickets SET voice_channel_id = ? WHERE channel_id = ?",
                (str(voice_channel_id), str(channel_id)),
            )
            connection.commit()
        return self.ticket_by_channel(channel_id)

    def close_ticket(self, channel_id: int | str, closed_by: int | str | None = None) -> sqlite3.Row | None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE tickets SET status = 'closed', closed_at = ?, closed_by = ? WHERE channel_id = ?",
                (now_iso(), str(closed_by) if closed_by is not None else None, str(channel_id)),
            )
            connection.commit()
        return self.ticket_by_channel(channel_id)

    def all_tickets(self) -> list[sqlite3.Row]:
        self.initialize()
        with self.connect() as connection:
            return list(connection.execute("SELECT * FROM tickets ORDER BY id").fetchall())

    def purge_tickets(self) -> None:
        self.initialize()
        with self.connect() as connection:
            connection.execute("DELETE FROM iris_events WHERE ticket_id IS NOT NULL")
            connection.execute("DELETE FROM tickets")
            connection.commit()

    def closed_tickets(self) -> list[sqlite3.Row]:
        self.initialize()
        with self.connect() as connection:
            return list(connection.execute("SELECT * FROM tickets WHERE status = 'closed' ORDER BY id DESC").fetchall())

    def save_booster_space(self, owner_user_id: int, role_id: int, voice_channel_id: int) -> None:
        self.initialize()
        timestamp = now_iso()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO booster_spaces (owner_user_id, role_id, voice_channel_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(owner_user_id) DO UPDATE SET
                    role_id = excluded.role_id,
                    voice_channel_id = excluded.voice_channel_id,
                    updated_at = excluded.updated_at
                """,
                (str(owner_user_id), str(role_id), str(voice_channel_id), timestamp, timestamp),
            )
            connection.commit()

    def booster_space_for_owner(self, owner_user_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM booster_spaces WHERE owner_user_id = ?",
                (str(owner_user_id),),
            ).fetchone()

    def booster_space_by_channel(self, channel_id: int | str) -> sqlite3.Row | None:
        self.initialize()
        with self.connect() as connection:
            return connection.execute(
                "SELECT * FROM booster_spaces WHERE voice_channel_id = ?",
                (str(channel_id),),
            ).fetchone()

    def record_iris_event(
        self,
        *,
        event_type: str,
        scope: str,
        channel_id: int | str | None = None,
        ticket_id: int | None = None,
        actor_user_id: int | str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        self.initialize()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO iris_events
                    (event_type, scope, channel_id, ticket_id, actor_user_id, metadata_json, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event_type,
                    scope,
                    str(channel_id) if channel_id is not None else None,
                    ticket_id,
                    str(actor_user_id) if actor_user_id is not None else None,
                    json.dumps(metadata or {}, ensure_ascii=False),
                    now_iso(),
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def has_iris_event(self, *, event_type: str, ticket_id: int) -> bool:
        self.initialize()
        with self.connect() as connection:
            row = connection.execute(
                "SELECT 1 FROM iris_events WHERE event_type = ? AND ticket_id = ? LIMIT 1",
                (event_type, ticket_id),
            ).fetchone()
        return row is not None

    def save_absence(
        self,
        *,
        discord_user_id: int,
        start_date: str,
        end_date: str,
        reason: str,
    ) -> int:
        self.initialize()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO absences (discord_user_id, start_date, end_date, reason, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (str(discord_user_id), start_date, end_date, reason, now_iso()),
            )
            connection.commit()
            return int(cursor.lastrowid)

    def save_farm(
        self,
        *,
        delivered_by: int,
        received_by: int,
        delivered_value: int,
        counted_value: int,
        goals_paid: int,
        paid_days: str,
        proof_url: str | None,
        created_by: int,
    ) -> int:
        self.initialize()
        with self.connect() as connection:
            cursor = connection.execute(
                """
                INSERT INTO farms
                    (delivered_by, received_by, delivered_value, counted_value, goals_paid,
                     paid_days, proof_url, created_by, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    str(delivered_by), str(received_by), delivered_value, counted_value,
                    goals_paid, paid_days, proof_url, str(created_by), now_iso(),
                ),
            )
            connection.commit()
            return int(cursor.lastrowid)


def _custom_ids(message: dict[str, Any]) -> list[str]:
    custom_ids: list[str] = []
    for row in message.get("components", []) or []:
        for component in row.get("components", []) or []:
            if component.get("custom_id"):
                custom_ids.append(str(component["custom_id"]))
    return custom_ids

