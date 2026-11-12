"""Move legacy set outcome messages out of ``scan-only``.

The current set workflow publishes pending review cards in ``scan-only`` and
writes outcome records to the configured log channel. Older versions edited a
review card into a plain-text approval/rejection message in ``scan-only``.

This module is deliberately a one-shot operator command. The default mode is
read-only; ``--apply`` must be supplied before Discord messages are copied or
deleted.
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import re
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any

import discord

if (__package__ or "").startswith("bot."):
    from ..config.settings import Settings
else:
    from config.settings import Settings


log = logging.getLogger("peace.legacy_scan_logs")

LEGACY_LOG_MARKER_PREFIX = "Peace · logs · legacy-scan:"

# These patterns intentionally describe only the terminal messages produced by
# the old SetApprovalView. Pending cards have an embed footer such as
# ``set_request:123`` and do not match either expression.
LEGACY_APPROVED_PATTERN = re.compile(
    r"^\s*(?:✅\s*)?Set aprovado por\s+<@!?\d+>\.\s+"
    r"Membro:\s+<@!?\d+>\.\s+ID Peace:\s+`[1-9]\d*`\."
    r"(?:\s+DM de boas-vindas está fechada\.)?\s*$",
    re.IGNORECASE,
)
LEGACY_REJECTED_PATTERN = re.compile(
    r"^\s*[×✕x]\s+Pedido de set recusado por\s+<@!?\d+>\.\s*$",
    re.IGNORECASE,
)


def legacy_scan_log_kind(message: Any) -> str | None:
    """Return the legacy outcome kind, or ``None`` for every other message."""

    content = str(getattr(message, "content", "") or "")
    if LEGACY_APPROVED_PATTERN.fullmatch(content):
        return "Set aprovado"
    if LEGACY_REJECTED_PATTERN.fullmatch(content):
        return "Set recusado"
    return None


def legacy_scan_log_marker(message: Any) -> str:
    """Build the stable marker used to make copy-then-delete idempotent."""

    return f"{LEGACY_LOG_MARKER_PREFIX}{int(getattr(message, 'id'))}"


def _embed_footer_text(embed: Any) -> str:
    footer = getattr(embed, "footer", None)
    return str(getattr(footer, "text", "") or "")


def destination_markers(message: Any) -> set[str]:
    """Read migration markers from a destination message."""

    values = [str(getattr(message, "content", "") or "")]
    values.extend(_embed_footer_text(embed) for embed in getattr(message, "embeds", ()) or ())
    marker_pattern = re.compile(re.escape(LEGACY_LOG_MARKER_PREFIX) + r"\d+")
    return {
        match.group(0)
        for value in values
        for match in marker_pattern.finditer(value)
    }


def legacy_log_embed(message: Any, kind: str) -> discord.Embed:
    """Render one old plain-text outcome as a normal log card."""

    content = str(getattr(message, "content", "") or "").strip()
    embed = discord.Embed(
        title=f"{kind} · legado",
        description=content[:4096] or "Registro legado sem conteúdo textual.",
        color=0x2B2D31,
    )
    jump_url = str(getattr(message, "jump_url", "") or "").strip()
    if jump_url:
        embed.add_field(name="Origem", value=jump_url[:1024], inline=False)
    created_at = getattr(message, "created_at", None)
    if isinstance(created_at, datetime):
        embed.timestamp = created_at
    embed.set_footer(text=legacy_scan_log_marker(message))
    return embed


async def _history(channel: discord.TextChannel) -> AsyncIterator[discord.Message]:
    async for message in channel.history(limit=None, oldest_first=True):
        yield message


async def migrate_legacy_scan_logs(
    guild: discord.Guild,
    *,
    scan_channel_id: int | None,
    log_channel_id: int | None,
    bot_user_id: int | None,
    apply: bool,
) -> dict[str, int]:
    """Copy matching legacy messages to ``logs`` and then delete their source.

    A destination marker is checked before each copy. If the process is
    interrupted after sending but before deleting, a later run removes the
    source without creating a duplicate log.
    """

    result = {"matched": 0, "copied": 0, "removed": 0, "failed": 0}
    if scan_channel_id is None or log_channel_id is None:
        log.error("DISCORD_SCAN_CHANNEL_ID e DISCORD_LOG_CHANNEL_ID são necessários")
        return result

    scan_channel = guild.get_channel(int(scan_channel_id))
    log_channel = guild.get_channel(int(log_channel_id))
    if not isinstance(scan_channel, discord.TextChannel) or not isinstance(log_channel, discord.TextChannel):
        log.error("Os canais scan-only e logs precisam ser canais de texto disponíveis")
        return result

    existing_markers: set[str] = set()
    try:
        async for message in _history(log_channel):
            existing_markers.update(destination_markers(message))
    except (discord.Forbidden, discord.HTTPException):
        log.exception("Não consegui ler o histórico do canal logs")
        result["failed"] += 1
        return result

    try:
        source_messages = [message async for message in _history(scan_channel)]
    except (discord.Forbidden, discord.HTTPException):
        log.exception("Não consegui ler o histórico do canal scan-only")
        result["failed"] += 1
        return result

    for message in source_messages:
        if bot_user_id is not None and getattr(getattr(message, "author", None), "id", None) != bot_user_id:
            continue
        kind = legacy_scan_log_kind(message)
        if kind is None:
            continue
        result["matched"] += 1
        marker = legacy_scan_log_marker(message)
        if not apply:
            continue
        if marker not in existing_markers:
            try:
                await log_channel.send(
                    embed=legacy_log_embed(message, kind),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                existing_markers.add(marker)
                result["copied"] += 1
            except (discord.Forbidden, discord.HTTPException):
                log.exception("Não consegui copiar o registro legado %s", getattr(message, "id", "?"))
                result["failed"] += 1
                continue
        try:
            await message.delete(reason="Migrar log legado para o canal logs")
            result["removed"] += 1
        except discord.NotFound:
            # It was already removed by an earlier retry; the desired state is
            # still satisfied and no duplicate destination message is needed.
            result["removed"] += 1
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Não consegui remover o registro legado %s", getattr(message, "id", "?"))
            result["failed"] += 1

    return result


def run_once(*, apply: bool) -> None:
    settings = Settings.from_env()
    intents = discord.Intents.default()
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        guild = client.get_guild(settings.guild_id)
        if guild is None:
            log.error("Servidor Peace não está disponível no cache")
            await client.close()
            return
        result = await migrate_legacy_scan_logs(
            guild,
            scan_channel_id=getattr(settings, "scan_channel_id", None),
            log_channel_id=getattr(settings, "log_channel_id", None),
            bot_user_id=getattr(client.user, "id", None),
            apply=apply,
        )
        log.info(
            "Logs legados: %s encontrados, %s copiados, %s removidos, %s falhas%s",
            result["matched"],
            result["copied"],
            result["removed"],
            result["failed"],
            " (simulação)" if not apply else "",
        )
        await client.close()

    client.run(settings.token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Migra logs legados do scan-only para logs")
    parser.add_argument("--apply", action="store_true", help="copia e remove as mensagens identificadas")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_once(apply=args.apply)


if __name__ == "__main__":
    main()
