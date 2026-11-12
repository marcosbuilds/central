import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord

from bot.operations.legacy_scan_logs import (
    LEGACY_LOG_MARKER_PREFIX,
    destination_has_equivalent_log,
    destination_markers,
    legacy_log_embed,
    legacy_scan_log_kind,
    migrate_legacy_scan_logs,
)


def _message(content: str, *, message_id: int = 10, author_id: int = 99):
    return SimpleNamespace(
        id=message_id,
        content=content,
        author=SimpleNamespace(id=author_id),
        jump_url=f"https://discord.com/channels/1/2/{message_id}",
        delete=AsyncMock(),
        embeds=[],
    )


def _history(messages):
    async def iterator(*, limit=None, oldest_first=False):
        for message in messages:
            yield message

    return iterator


def test_legacy_scan_log_kind_accepts_only_terminal_set_messages():
    assert legacy_scan_log_kind(
        _message("✅ Set aprovado por <@107>. Membro: <@137>. ID Peace: `17`.")
    ) == "Set aprovado"
    assert legacy_scan_log_kind(
        _message("× Pedido de set recusado por <@107>.")
    ) == "Set recusado"
    assert legacy_scan_log_kind(
        _message("Retorno recusado por <@107>. O ID `24` continua reservado.")
    ) == "Retorno Peace recusado"
    assert legacy_scan_log_kind(
        _message("ID liberado por <@107>. Antigo: `24` · novo: `2`.")
    ) == "Retorno Peace aprovado"

    pending = SimpleNamespace(
        content="",
        embeds=[SimpleNamespace(title="Set pendente de aprovação")],
    )
    unrelated = _message("✅ Set aprovado por <@107>. Membro: <@137>. ID Peace: `0`.")
    assert legacy_scan_log_kind(pending) is None
    assert legacy_scan_log_kind(unrelated) is None


def test_destination_markers_are_stable_and_not_truncated():
    marker = f"{LEGACY_LOG_MARKER_PREFIX}123"
    message = SimpleNamespace(
        content="",
        embeds=[SimpleNamespace(footer=SimpleNamespace(text=marker))],
    )

    assert destination_markers(message) == {marker}


def test_migration_copies_and_removes_only_bot_legacy_messages():
    approved = _message("✅ Set aprovado por <@107>. Membro: <@137>. ID Peace: `17`.", message_id=10)
    human_copy = _message(approved.content, message_id=11, author_id=1234)
    pending = SimpleNamespace(
        id=12,
        content="",
        author=SimpleNamespace(id=99),
        embeds=[SimpleNamespace(title="Set pendente de aprovação")],
        delete=AsyncMock(),
    )

    scan = MagicMock(spec=discord.TextChannel)
    logs = MagicMock(spec=discord.TextChannel)
    scan.history = _history([approved, human_copy, pending])
    logs.history = _history([])
    logs.send = AsyncMock(return_value=SimpleNamespace())
    guild = SimpleNamespace(get_channel=lambda channel_id: {2: scan, 3: logs}[channel_id])

    result = asyncio.run(
        migrate_legacy_scan_logs(
            guild,
            scan_channel_id=2,
            log_channel_id=3,
            bot_user_id=99,
            apply=True,
        )
    )

    assert result == {"matched": 1, "copied": 1, "removed": 1, "failed": 0}
    logs.send.assert_awaited_once()
    assert logs.send.call_args.kwargs["embed"].footer.text.endswith(":10")
    approved.delete.assert_awaited_once()
    human_copy.delete.assert_not_awaited()
    pending.delete.assert_not_awaited()


def test_structured_log_prevents_duplicate_copy_for_terminal_source():
    approved = _message(
        "✅ Set aprovado por <@107>. Membro: <@137>. ID Peace: `17`.",
        message_id=10,
    )
    existing = SimpleNamespace(
        content="",
        embeds=[
            SimpleNamespace(
                title="Set aprovado",
                fields=[
                    SimpleNamespace(name="Usuário", value="<@137>"),
                    SimpleNamespace(name="ID Peace", value="`17`"),
                    SimpleNamespace(name="Aprovado por", value="<@107>"),
                ],
            )
        ],
    )

    assert destination_has_equivalent_log([existing], approved, "Set aprovado") is True

    scan = MagicMock(spec=discord.TextChannel)
    logs = MagicMock(spec=discord.TextChannel)
    scan.history = _history([approved])
    logs.history = _history([existing])
    logs.send = AsyncMock()
    guild = SimpleNamespace(get_channel=lambda channel_id: {2: scan, 3: logs}[channel_id])

    result = asyncio.run(
        migrate_legacy_scan_logs(
            guild,
            scan_channel_id=2,
            log_channel_id=3,
            bot_user_id=99,
            apply=True,
        )
    )

    assert result == {"matched": 1, "copied": 0, "removed": 1, "failed": 0}
    logs.send.assert_not_awaited()
    approved.delete.assert_awaited_once()


def test_legacy_embed_keeps_actor_and_member_avatars_when_available():
    approved = _message(
        "✅ Set aprovado por <@107>. Membro: <@137>. ID Peace: `17`.",
        message_id=10,
    )
    actor = SimpleNamespace(
        id=107,
        mention="<@107>",
        display_name="Aprovador",
        display_avatar=SimpleNamespace(url="https://cdn.example/actor.png"),
    )
    member = SimpleNamespace(
        id=137,
        mention="<@137>",
        display_name="Membro",
        display_avatar=SimpleNamespace(url="https://cdn.example/member.png"),
    )
    guild = SimpleNamespace(get_member=lambda user_id: {107: actor, 137: member}.get(user_id))

    embed = legacy_log_embed(approved, "Set aprovado", guild=guild)

    assert embed.author.icon_url == "https://cdn.example/actor.png"
    assert embed.thumbnail.url == "https://cdn.example/member.png"


def test_legacy_approved_embed_is_terminal_but_does_not_copy_sensitive_fields():
    message = SimpleNamespace(
        id=55,
        content="",
        author=SimpleNamespace(id=99),
        embeds=[
            SimpleNamespace(
                title="Set aprovado",
                description="**Membro:** <@137>\n**ID Peace:** `17`\n**Indicado por:** <@107>",
                fields=[
                    SimpleNamespace(name="Telefone", value="`555-0100`"),
                    SimpleNamespace(name="RG", value="`12345`"),
                ],
            )
        ],
    )

    assert legacy_scan_log_kind(message) == "Set aprovado"
    embed = legacy_log_embed(message, "Set aprovado")
    assert "555-0100" not in (embed.description or "")
    assert "12345" not in (embed.description or "")


def test_legacy_set_banner_and_manual_update_embeds_are_terminal():
    banner = _message(
        "✅ SET APROVADO (pedir-set) 👤 Novo: <@137> 📕 Recrutador: <@107> 📞 Telefone: 555",
        message_id=56,
    )
    updated = SimpleNamespace(
        id=57,
        content="",
        embeds=[
            SimpleNamespace(
                title="Set atualizado",
                description="**Membro:** <@137>\n**ID Peace:** `17`\n**Atualizado por:** <@107>",
                fields=[],
            )
        ],
    )

    assert legacy_scan_log_kind(banner) == "Set aprovado"
    assert legacy_scan_log_kind(updated) == "Set atualizado"


def test_migration_retry_deletes_source_without_duplicate_copy():
    approved = _message("✅ Set aprovado por <@107>. Membro: <@137>. ID Peace: `17`.", message_id=10)
    marker = f"{LEGACY_LOG_MARKER_PREFIX}10"
    existing = SimpleNamespace(
        content="",
        embeds=[SimpleNamespace(footer=SimpleNamespace(text=marker))],
    )
    scan = MagicMock(spec=discord.TextChannel)
    logs = MagicMock(spec=discord.TextChannel)
    scan.history = _history([approved])
    logs.history = _history([existing])
    logs.send = AsyncMock()
    guild = SimpleNamespace(get_channel=lambda channel_id: {2: scan, 3: logs}[channel_id])

    result = asyncio.run(
        migrate_legacy_scan_logs(
            guild,
            scan_channel_id=2,
            log_channel_id=3,
            bot_user_id=99,
            apply=True,
        )
    )

    assert result == {"matched": 1, "copied": 0, "removed": 1, "failed": 0}
    logs.send.assert_not_awaited()
    approved.delete.assert_awaited_once()
