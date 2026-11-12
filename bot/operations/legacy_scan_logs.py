"""Move legacy set and return outcome messages out of ``scan-only``.

The current set workflow publishes pending review cards in ``scan-only`` and
writes outcome records to the configured log channel. Older versions edited a
review card into a plain-text approval/rejection message in ``scan-only``. The
current flow can also leave a terminal card when Discord rejects a delete;
existing structured logs are reconciled before a source message is removed so
a cleanup never duplicates an outcome.

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

# These patterns intentionally describe only terminal messages produced by old
# approval views. Pending cards have an embed footer such as ``set_request:123``
# and do not match any expression below.
LEGACY_APPROVED_PATTERN = re.compile(
    r"^\s*(?:✅\s*)?Set aprovado por\s+<@!?(?P<actor>\d+)>\.\s+"
    r"Membro:\s+<@!?(?P<member>\d+)>\.\s+ID Peace:\s+`(?P<peace_id>[1-9]\d*)`\."
    r"(?:\s+DM de boas-vindas está fechada\.)?\s*$",
    re.IGNORECASE,
)
LEGACY_REJECTED_PATTERN = re.compile(
    r"^\s*[×✕x]\s+Pedido de set recusado por\s+<@!?(?P<actor>\d+)>\.\s*$",
    re.IGNORECASE,
)
LEGACY_RETURN_REJECTED_PATTERN = re.compile(
    r"^\s*Retorno recusado por\s+<@!?(?P<actor>\d+)>\.\s+"
    r"O ID\s+`(?P<peace_id>[1-9]\d*)`\s+continua reservado\.\s*$",
    re.IGNORECASE,
)
LEGACY_RETURN_APPROVED_PATTERN = re.compile(
    r"^\s*ID liberado por\s+<@!?(?P<actor>\d+)>\.\s+"
    r"Antigo:\s+`(?P<old_id>[1-9]\d*)`\s+·\s+novo:\s+`(?P<new_id>[1-9]\d*)`\.\s*$",
    re.IGNORECASE,
)

LEGACY_SET_APPROVED_BANNER_PATTERN = re.compile(
    r"^\s*(?:✅\s*)?SET APROVADO\s*\(pedir-set\).*?"
    r"Novo:\s*<@!?(?P<member>\d+)>.*?"
    r"(?:Recrutador|Aprovado por):\s*<@!?(?P<actor>\d+)>.*$",
    re.IGNORECASE | re.DOTALL,
)

LEGACY_EMBED_APPROVED_PATTERN = re.compile(
    r"(?:\*{0,2}\s*)?Membro(?:\*{0,2})?\s*:\s*<@!?(?P<member>\d+)>.*?"
    r"(?:\*{0,2}\s*)?ID\s+Peace(?:\*{0,2})?\s*:\s*`?(?P<peace_id>[1-9]\d*)`?.*?"
    r"(?:(?:\*{0,2}\s*)?Aprovado por|(?:\*{0,2}\s*)?Indicado por)(?:\*{0,2})?\s*:\s*<@!?(?P<actor>\d+)>"
    r".*$",
    re.IGNORECASE | re.DOTALL,
)

LEGACY_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("Set aprovado", LEGACY_SET_APPROVED_BANNER_PATTERN),
    ("Set aprovado", LEGACY_APPROVED_PATTERN),
    ("Set recusado", LEGACY_REJECTED_PATTERN),
    ("Retorno Peace recusado", LEGACY_RETURN_REJECTED_PATTERN),
    ("Retorno Peace aprovado", LEGACY_RETURN_APPROVED_PATTERN),
)


def legacy_scan_log_signature(message: Any) -> dict[str, str] | None:
    """Return the terminal outcome and stable IDs encoded in a source message."""

    content = str(getattr(message, "content", "") or "")
    for kind, pattern in LEGACY_PATTERNS:
        match = pattern.fullmatch(content)
        if match:
            return {"kind": kind, **match.groupdict()}
    for embed in getattr(message, "embeds", ()) or ():
        title = str(getattr(embed, "title", "") or "").strip()
        if title.casefold() not in {"set aprovado", "set atualizado"}:
            continue
        values = [str(getattr(embed, "description", "") or "")]
        values.extend(
            f"{getattr(field, 'name', '')}: {getattr(field, 'value', '')}"
            for field in getattr(embed, "fields", ()) or ()
        )
        normalized = "\n".join(values).replace("*", "")
        if title.casefold() == "set aprovado":
            match = LEGACY_EMBED_APPROVED_PATTERN.search(normalized)
            kind = "Set aprovado"
            actor_labels = r"(?:Aprovado por|Indicado por|Recrutador)"
        else:
            match = None
            kind = "Set atualizado"
            actor_labels = r"Atualizado por"
        signature: dict[str, str] = {"kind": kind}
        member_match = re.search(r"(?:Membro|Novo)\s*:\s*<@!?(\d+)>", normalized, re.IGNORECASE)
        peace_match = re.search(r"ID\s+Peace\s*:\s*`?(\d+)`?", normalized, re.IGNORECASE)
        actor_match = re.search(rf"{actor_labels}\s*:\s*<@!?(\d+)>", normalized, re.IGNORECASE)
        if match:
            signature.update({key: value for key, value in match.groupdict().items() if value is not None})
        if member_match:
            signature["member"] = member_match.group(1)
        if peace_match:
            signature["peace_id"] = peace_match.group(1)
        if actor_match:
            signature["actor"] = actor_match.group(1)
        return signature
    return None


def legacy_scan_log_kind(message: Any) -> str | None:
    """Return the legacy outcome kind, or ``None`` for every other message."""

    signature = legacy_scan_log_signature(message)
    return signature["kind"] if signature is not None else None


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


def _member_for_id(guild: Any | None, user_id: str | None) -> Any | None:
    if guild is None or not user_id:
        return None
    getter = getattr(guild, "get_member", None)
    return getter(int(user_id)) if callable(getter) else None


def _avatar_url(user: Any | None) -> str:
    return str(getattr(getattr(user, "display_avatar", None), "url", "") or "").strip()


def _display_name(user: Any | None, fallback: str) -> str:
    return str(
        getattr(user, "display_name", None)
        or getattr(user, "name", None)
        or fallback
    ).strip()


def _mention(user: Any | None, user_id: str | None) -> str:
    mention = str(getattr(user, "mention", "") or "").strip()
    if mention:
        return mention
    return f"<@{user_id}>" if user_id else "membro não identificado"


def legacy_log_embed(message: Any, kind: str, *, guild: Any | None = None) -> discord.Embed:
    """Render one old plain-text outcome as a normal log card."""

    content = str(getattr(message, "content", "") or "").strip()
    signature = legacy_scan_log_signature(message) or {"kind": kind}
    if not content:
        if signature.get("member") and signature.get("peace_id"):
            content = (
                f"{kind} legado identificado para <@{signature['member']}>. "
                f"ID Peace: `{signature['peace_id']}`."
            )
        else:
            content = f"{kind} legado identificado no scan-only."
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
    actor = _member_for_id(guild, signature.get("actor"))
    subject = _member_for_id(guild, signature.get("member"))
    actor_avatar = _avatar_url(actor)
    subject_avatar = _avatar_url(subject)
    if actor is not None:
        author_name = f"Ação por {_display_name(actor, 'membro Peace')}"
        if actor_avatar:
            embed.set_author(name=author_name, icon_url=actor_avatar)
        else:
            embed.set_author(name=author_name)
    if subject_avatar:
        embed.set_thumbnail(url=subject_avatar)
    elif actor_avatar:
        embed.set_thumbnail(url=actor_avatar)
    if actor is not None:
        if "aprovado" in kind.casefold():
            actor_label = "Aprovador"
        elif "atualizado" in kind.casefold():
            actor_label = "Atualizado por"
        else:
            actor_label = "Recusador"
        embed.add_field(name=actor_label, value=_mention(actor, signature.get("actor")), inline=False)
    if subject is not None:
        embed.add_field(name="Membro afetado", value=_mention(subject, signature.get("member")), inline=False)
    embed.set_footer(text=legacy_scan_log_marker(message))
    return embed


def _embed_fields(embed: Any) -> dict[str, str]:
    return {
        str(getattr(field, "name", "") or "").strip().casefold(): str(getattr(field, "value", "") or "")
        for field in getattr(embed, "fields", ()) or ()
    }


def _contains_mention(value: str, user_id: str | None) -> bool:
    if not user_id:
        return False
    return bool(re.search(rf"<@!?{re.escape(user_id)}>", value))


def destination_has_equivalent_log(destinations: list[Any], source: Any, kind: str) -> bool:
    """Detect a structured log emitted by the current flow before migrating."""

    signature = legacy_scan_log_signature(source)
    if signature is None:
        return False
    for destination in destinations:
        for embed in getattr(destination, "embeds", ()) or ():
            title = str(getattr(embed, "title", "") or "").strip().casefold()
            if title != kind.casefold():
                continue
            fields = _embed_fields(embed)
            if kind == "Set aprovado":
                if (
                    signature.get("peace_id") in fields.get("id peace", "")
                    and _contains_mention(fields.get("usuário", ""), signature.get("member"))
                    and _contains_mention(fields.get("aprovado por", ""), signature.get("actor"))
                ):
                    return True
            elif kind == "Retorno Peace recusado":
                if (
                    signature.get("peace_id") in fields.get("id reservado", "")
                    and _contains_mention(fields.get("quem recusou", ""), signature.get("actor"))
                ):
                    return True
            elif kind == "Retorno Peace aprovado":
                if (
                    signature.get("old_id") in fields.get("id anterior", "")
                    and signature.get("new_id") in fields.get("novo id", "")
                    and _contains_mention(fields.get("aprovado por", ""), signature.get("actor"))
                ):
                    return True
            elif kind == "Set atualizado":
                if (
                    signature.get("peace_id") in fields.get("id peace", "")
                    and _contains_mention(fields.get("membro", ""), signature.get("member"))
                    and _contains_mention(fields.get("atualizado por", ""), signature.get("actor"))
                ):
                    return True
    return False


async def _history(channel: discord.TextChannel) -> AsyncIterator[discord.Message]:
    async for message in channel.history(limit=None, oldest_first=True):
        yield message


async def _delete_message(message: Any, *, reason: str) -> None:
    """Delete full and partial Discord messages across discord.py versions."""

    delete = getattr(message, "delete")
    try:
        await delete(reason=reason)
    except TypeError as error:
        if "reason" not in str(error):
            raise
        await delete()


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
    destination_messages: list[Any] = []
    try:
        async for message in _history(log_channel):
            destination_messages.append(message)
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
        author = getattr(message, "author", None)
        author_id = getattr(author, "id", None)
        author_is_bot = bool(getattr(author, "bot", False))
        if bot_user_id is not None:
            if author_id != bot_user_id and not author_is_bot:
                continue
        elif not author_is_bot:
            continue
        kind = legacy_scan_log_kind(message)
        if kind is None:
            continue
        result["matched"] += 1
        marker = legacy_scan_log_marker(message)
        if not apply:
            continue
        if marker not in existing_markers and not destination_has_equivalent_log(destination_messages, message, kind):
            try:
                await log_channel.send(
                    embed=legacy_log_embed(message, kind, guild=guild),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                existing_markers.add(marker)
                result["copied"] += 1
            except (discord.Forbidden, discord.HTTPException):
                log.exception("Não consegui copiar o registro legado %s", getattr(message, "id", "?"))
                result["failed"] += 1
                continue
        try:
            await _delete_message(message, reason="Migrar log legado para o canal logs")
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
