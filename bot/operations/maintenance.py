"""Idempotent structural migration for the Peace Discord server.

Dry-run (read-only after login)::

    python -m bot.operations.maintenance

Apply the requested organization::

    python -m bot.operations.maintenance --apply --remove-chat-elite

Ticket/history cleanup remains separately gated by ``--clean`` and
``--clean-dev-chat``. The role migration always writes a local ignored snapshot
before deleting obsolete roles.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

import discord

if (__package__ or "").startswith("bot."):
    from ..config.settings import Settings
    from ..persistence.database import PeaceDatabase
else:
    from config.settings import Settings
    from persistence.database import PeaceDatabase


log = logging.getLogger("peace.maintenance")

ACTION_CATEGORY_ID = 1466632839339577364
OPEN_TICKET_CATEGORY_ID = 1495063893838532730
CLOSED_TICKET_CATEGORY_ID = 1495064004194861137
ATENDIMENTO_CATEGORY_ID = 1459444056064262186
REGISTROS_CATEGORY_ID = 1459443063754592297
DEVELOPMENT_CATEGORY_ID = 1506409116686614608
CALLS_CATEGORY_ID = 1459444321425035386
AFK_CHANNEL_ID = 1466629495405543515
AUTOMOD_CHANNEL_ID = 1555060813046226964
# The verification channel is intentionally kept at the server root. The old
# verification category is a retired structure and is never recreated.
VERIFICATION_CHANNEL_NAME = "verify"
NOT_VERIFIED_ROLE_NAME = "Not Verified"
INTERN_ROLE_NAME = "Estagiário"

CATEGORY_NAMES = {
    "reception": "[🎫] RECEPTION",
    "staff": "[🛡️] STAFF",
    "records": "[ℹ️] RECORDS",
    "social": "[🔔] SOCIAL LOUNGE",
    "support": "[☎️] SUPPORT",
    "calls": "[🎙️] CALLS",
    "private_calls": "[🎙️] PRIVATE CALLS",
    "closed_tickets": "[🎟️] CLOSED TICKETS",
}

LEGACY_DEVELOPMENT_CATEGORY_NAMES = frozenset({"[💻] developers"})

CHANNEL_IDS = {
    "staff_only": 1491899123547242656,
    "scan_only": 1495121743604617458,
    "rules": 1495156853817085983,
    "logs": 1495108987689893998,
    "avisos": 1459443449873830030,
    "parceiros": 1461938338612252693,
    "midias": 1459444827635712134,
    "clipes": 1459444295261093992,
    "painel": 1495087589604982785,
    "dev_chat": 1506409179005456675,
    "dev_call": 1506409269346570270,
    "waiting_voice": 1460526534527025208,
    "ticket_panel": 1459446670411567105,
    "chat_geral": 1459444803346501833,
    "chat_gerencia": 1460522012639236320,
    "chat_elite": 1481237639230263387,
    "chat_visitante": 1491909718388510901,
    "musica": 1459444851417288816,
}

ROLE_IDS = {
    "peace": 1467349800956592188,
    "staff": 1493055564010360842,
    "manager": 1471532522394615850,
    "visitor": 1474515602625269936,
    "elite": 1486981235719934082,
    "florenza_legacy": 1506409509667606569,
    "founder": 1428158506887938231,
}

ROLE_NAMES = {
    "peace": "Peace",
    "staff": "Staff",
    "manager": "Gerência",
    "general_manager": "Delegado",
    "visitor": "Visitante",
    "elite": "Agente Especial",
    "novato": "Aluno",
    "member": "Agente",
    "technical": "Developer",
    "a_is": "AIs",
    "not_verified": NOT_VERIFIED_ROLE_NAME,
    "intern": "Estagiário",
    "investigator": "Investigador",
    "lead_investigator": "Investigador Chefe",
}

ROLE_RENAMES = {
    "Management": "Gerência",
    "Gerencia": "Gerência",
    "Manager ⎰ Deputy Delegate": "Delegado",
    "Gerente geral": "Delegado",
    "Gerente Geral": "Delegado",
    "Gerente ⎰ Delegado adjunto": "Delegado",
    "Gerente ⎰ Delegado Adjunto": "Delegado",
    "Gerente / Delegado adjunto": "Delegado",
    "Gerente / Delegado Adjunto": "Delegado",
    "Gerente/delegado adjunto": "Delegado",
    "Gerente/Delegado Adjunto": "Delegado",
    "Gerente": "Gerência",
    "Visitor": "Visitante",
    "Booster": "Apoiador",
    "Elite ⎰ Special Agent": "Agente Especial",
    "Elite": "Agente Especial",
    "Elite Peace": "Agente Especial",
    "Elite ⎰ Ag. Especial": "Agente Especial",
    "Elite ⎰ Agente Especial": "Agente Especial",
    "Member ⎰ Recruit": "Agente",
    "Membro Peace": "Agente",
    "Membro ⎰ Recruta": "Agente",
    "Membro": "Agente",
    "Recruta": "Agente",
    "Rookie ⎰ Agent": "Aluno",
    "Novato Peace": "Aluno",
    "Novato ⎰ Agente": "Aluno",
    "Novato": "Aluno",
    "Aluno Peace": "Aluno",
    "Intern": "Estagiário",
    "Estagiario": "Estagiário",
    "Não Verificado": NOT_VERIFIED_ROLE_NAME,
    "Não verificado": NOT_VERIFIED_ROLE_NAME,
    "Nao verificado": NOT_VERIFIED_ROLE_NAME,
    "Investigator": "Investigador",
    "Lead Investigator": "Investigador Chefe",
    "Chief Investigator": "Investigador Chefe",
    "Investigador Líder": "Investigador Chefe",
    "Investigador-chefe": "Investigador Chefe",
    "Investigador chefe": "Investigador Chefe",
}

ROLE_COLOURS = {
    "Peace": 0x2B2D42,
    "Staff": 0x9B59B6,
    "Gerência": 0xE67E22,
    "Management": 0xE67E22,
    "Delegado": 0xF1C40F,
    "Manager ⎰ Deputy Delegate": 0xF1C40F,
    "Visitante": 0x95A5A6,
    "Visitor": 0x95A5A6,
    "Agente Especial": 0xE74C3C,
    "Elite ⎰ Special Agent": 0xE74C3C,
    "Elite ⎰ Agente Especial": 0xE74C3C,
    "Aluno": 0x2ECC71,
    "Rookie ⎰ Agent": 0x2ECC71,
    "Novato ⎰ Agente": 0x2ECC71,
    "Agente": 0x3498DB,
    "Member ⎰ Recruit": 0x3498DB,
    "Membro ⎰ Recruta": 0x3498DB,
    "Developer": 0x5865F2,
    "Dev": 0x5865F2,
    "Estagiário": 0x1ABC9C,
    "Intern": 0x1ABC9C,
    "AIs": 0x8E44AD,
    "Not Verified": 0x7F8C8D,
    "Não Verificado": 0x7F8C8D,
    "Investigador": 0x3498DB,
    "Investigator": 0x3498DB,
    "Investigador Chefe": 0x9B59B6,
    "Investigador Líder": 0x9B59B6,
    "Lead Investigator": 0x9B59B6,
    "Diretor Geral": 0xC27C0E,
    "General Director": 0xC27C0E,
    "Apoiador": 0x95A5A6,
    "Booster": 0x95A5A6,
}

OBSOLETE_ROLE_NAMES = (
    "Frontend",
    "Backend",
    "Frontend Peace",
    "Backend Peace",
    "Documentation",
    "Documentation Peace",
    "Documentação",
    "Documentação Peace",
    "Gerente de elites",
    "Gerente de recrutadores",
    "Gerente de vendas",
    "Gerente de farms",
    "Recrutador",
    "IA & Bots",
    "AI & Bots",
    "IA & Bots Peace",
    "Superintendente",
    "Superintendent",
)

DEPRECATED_ROLE_IDS = (
    1495091523245838506,  # Advertência I
    1495091691743481876,  # Advertência II
    1495091763189387395,  # Advertência III
    1466835667928744068,  # Sublider
)

BOT_ROLE_NAMES = {"PeaceBot", "Jockie Music", "DutiesBot", "TimeCord", "Medal"}


def perms(**kwargs: bool) -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(**kwargs)


def find_role(guild: discord.Guild, *names: str) -> discord.Role | None:
    normalized = {name.casefold() for name in names}
    return discord.utils.find(lambda item: item.name.casefold() in normalized, guild.roles)


def role_by_id_or_name(
    guild: discord.Guild,
    role_id: int | None,
    name: str | None = None,
    *aliases: str,
) -> discord.Role | None:
    if role_id is not None:
        role = guild.get_role(role_id)
        if role is not None:
            return role
    return find_role(guild, name, *aliases) if name else None


async def set_role_access(
    channel: discord.abc.GuildChannel,
    role: discord.Role | None,
    *,
    view: bool,
    send: bool = False,
    connect: bool | None = None,
    speak: bool | None = None,
    move_members: bool | None = None,
    manage_messages: bool | None = None,
    deny_threads: bool = False,
) -> None:
    if role is None:
        return
    values: dict[str, bool] = {
        "view_channel": view,
        "read_message_history": view,
        "send_messages": send and view,
    }
    if connect is not None:
        values["connect"] = connect and view
    if speak is not None:
        values["speak"] = speak and view
    if move_members is not None:
        values["move_members"] = move_members and view
    if manage_messages is not None:
        values["manage_messages"] = manage_messages and view
    if deny_threads:
        values.update(
            {
                "send_messages_in_threads": False,
                "create_public_threads": False,
                "create_private_threads": False,
            }
        )
    await channel.set_permissions(role, overwrite=perms(**values), reason="Reorganização Peace")


async def set_default_access(
    channel: discord.abc.GuildChannel,
    guild: discord.Guild,
    *,
    view: bool,
    send: bool = False,
    connect: bool | None = None,
    speak: bool | None = None,
    deny_threads: bool = False,
) -> None:
    values: dict[str, bool] = {
        "view_channel": view,
        "read_message_history": view,
        "send_messages": send and view,
    }
    if connect is not None:
        values["connect"] = connect and view
    if speak is not None:
        values["speak"] = speak and view
    if deny_threads:
        values.update(
            {
                "send_messages_in_threads": False,
                "create_public_threads": False,
                "create_private_threads": False,
            }
        )
    await channel.set_permissions(guild.default_role, overwrite=perms(**values), reason="Reorganização Peace")


async def clear_role_overwrites(
    channel: discord.abc.GuildChannel,
    guild: discord.Guild,
    allowed: list[discord.Role | None],
) -> None:
    """Remove role overwrites that are no longer part of the access policy."""
    allowed_ids = {role.id for role in allowed if role is not None}
    for subject in list(channel.overwrites):
        if not isinstance(subject, discord.Role):
            continue
        if subject.is_default() or subject.id in allowed_ids:
            continue
        await channel.set_permissions(subject, overwrite=None, reason="Limpeza de acesso legado Peace")


async def clear_member_overwrites(
    channel: discord.abc.GuildChannel,
) -> None:
    """Remove stale individual grants from a channel that must be role-only."""
    for subject in list(channel.overwrites):
        if isinstance(subject, discord.Member):
            await channel.set_permissions(subject, overwrite=None, reason="Limpeza de acesso individual legado Peace")


async def configure_text(
    channel: discord.TextChannel,
    guild: discord.Guild,
    *,
    allowed: list[discord.Role | None],
    public: bool = False,
    send: bool = True,
    bot_only: bool = False,
) -> None:
    await clear_role_overwrites(channel, guild, allowed)
    await set_default_access(
        channel,
        guild,
        view=public,
        send=send if public else False,
        deny_threads=bot_only,
    )
    for role in allowed:
        await set_role_access(channel, role, view=True, send=send, deny_threads=bot_only)


async def configure_voice(
    channel: discord.VoiceChannel,
    guild: discord.Guild,
    *,
    allowed: list[discord.Role | None],
    public: bool = False,
    connect: bool = True,
    speak: bool = True,
    move_members: bool | None = None,
) -> None:
    await clear_role_overwrites(channel, guild, allowed)
    await set_default_access(
        channel,
        guild,
        view=public,
        connect=connect if public else False,
        speak=speak if public else False,
    )
    for role in allowed:
        await set_role_access(
            channel,
            role,
            view=True,
            connect=connect,
            speak=speak,
            move_members=move_members,
        )


async def configure_category(
    category: discord.CategoryChannel,
    guild: discord.Guild,
    allowed: list[discord.Role | None],
) -> None:
    await clear_role_overwrites(category, guild, allowed)
    await set_default_access(category, guild, view=False, send=False)
    for role in allowed:
        await set_role_access(category, role, view=True, send=True)


async def deny_role(
    channel: discord.abc.GuildChannel,
    role: discord.Role | None,
    *,
    voice: bool = False,
) -> None:
    if role is None:
        return
    values = {
        "view_channel": False,
        "read_message_history": False,
        "send_messages": False,
    }
    if voice:
        values.update({"connect": False, "speak": False, "move_members": False})
    await channel.set_permissions(role, overwrite=perms(**values), reason="Acesso negado pela política Peace")


async def ensure_zero_permission_role(
    guild: discord.Guild,
    name: str,
    colour: discord.Colour,
    aliases: tuple[str, ...] = (),
    *,
    role_id: int | None = None,
    reason: str = "Padronização dos cargos Peace",
) -> discord.Role:
    existing = role_by_id_or_name(guild, role_id, name, *aliases)
    if existing is not None:
        if (
            existing.name != name
            or existing.permissions != discord.Permissions.none()
            or existing.colour.value != colour.value
        ):
            await existing.edit(
                name=name,
                permissions=discord.Permissions.none(),
                colour=colour,
                reason=reason,
            )
        return existing
    return await guild.create_role(
        name=name,
        colour=colour,
        permissions=discord.Permissions.none(),
        hoist=False,
        mentionable=False,
        reason=reason,
    )


async def ensure_visual_role(
    guild: discord.Guild,
    name: str,
    colour: discord.Colour,
    aliases: tuple[str, ...] = (),
) -> discord.Role:
    return await ensure_zero_permission_role(
        guild,
        name,
        colour,
        aliases,
        reason="Padronização dos cargos visuais Peace",
    )


async def style_role(
    role: discord.Role | None,
    name: str,
    colour_value: int,
) -> discord.Role | None:
    """Keep an existing role's public label and colour deterministic."""
    if role is None:
        return None
    colour = discord.Colour(colour_value)
    if role.name != name or role.colour.value != colour.value:
        await role.edit(
            name=name,
            colour=colour,
            reason="Padronização visual dos cargos Peace",
        )
    return role


async def rename_roles(guild: discord.Guild) -> None:
    for old_name, new_name in ROLE_RENAMES.items():
        role = find_role(guild, old_name)
        if role is None or role.name == new_name:
            continue
        await role.edit(name=new_name, reason="Padronização dos nomes de cargos Peace")


def find_channel(
    guild: discord.Guild,
    channel_id: int | None,
    *aliases: str,
    category_id: int | None = None,
) -> discord.GuildChannel | None:
    if channel_id is not None:
        channel = guild.get_channel(channel_id)
        if channel is not None:
            return channel
    normalized = {alias.casefold() for alias in aliases}
    return discord.utils.find(
        lambda channel: (
            channel.name.casefold() in normalized
            and (category_id is None or channel.category_id == category_id)
        ),
        guild.channels,
    )


async def rename_channel(
    guild: discord.Guild,
    desired_name: str,
    channel_id: int | None = None,
    *aliases: str,
    category_id: int | None = None,
) -> discord.GuildChannel | None:
    channel = find_channel(guild, channel_id, *aliases, category_id=category_id)
    if channel is None:
        return None
    if channel.name != desired_name:
        await channel.edit(name=desired_name, reason="Padronização dos nomes de canais Peace")
    return channel


def obsolete_named_roles(guild: discord.Guild) -> list[discord.Role]:
    names = {name.casefold() for name in OBSOLETE_ROLE_NAMES}
    return [role for role in guild.roles if role.name.casefold() in names and not role.managed]


def snapshot_path() -> Path:
    root = Path(__file__).resolve().parents[2]
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return root / "data" / "snapshots" / f"peace-role-members-{timestamp}.json"


async def snapshot_obsolete_role_members(
    guild: discord.Guild,
    roles: list[discord.Role],
) -> Path:
    """Persist affected membership before a requested role deletion."""
    try:
        members = [member async for member in guild.fetch_members(limit=None)]
    except (discord.Forbidden, discord.HTTPException):
        members = list(guild.members)
    output = snapshot_path()
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "guild_id": guild.id,
        "purpose": "Peace role migration before obsolete role removal",
        "roles": {
            role.name: [
                {
                    "user_id": member.id,
                    "username": member.name,
                    "display_name": member.display_name,
                    "bot": member.bot,
                }
                for member in members
                if role in member.roles
            ]
            for role in roles
        },
    }
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Snapshot local dos cargos obsoletos salvo em %s", output.name)
    return output


async def remove_obsolete_named_roles(guild: discord.Guild, *, snapshot: bool = True) -> None:
    roles = obsolete_named_roles(guild)
    if not roles:
        return
    if snapshot:
        await snapshot_obsolete_role_members(guild, roles)
    for role in roles:
        try:
            await role.delete(reason="Remoção de cargos obsoletos solicitada pela Peace")
            log.info("Cargo obsoleto removido: %s", role.name)
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Não consegui remover o cargo obsoleto %s", role.name)


async def clear_non_bot_role_permissions(
    guild: discord.Guild,
    members: list[discord.Member],
) -> None:
    """Leave global permissions only on managed/bot-only roles and the founder."""
    founder_name = "Founder Peace".casefold()
    for role in guild.roles:
        if role.is_default() or role.managed or role.name.casefold() == founder_name:
            continue
        human_holder = any(role in member.roles and not member.bot for member in members)
        bot_holder = any(role in member.roles and member.bot for member in members)
        if bot_holder and not human_holder and role.name in BOT_ROLE_NAMES:
            continue
        if role.permissions != discord.Permissions.none():
            await role.edit(
                permissions=discord.Permissions.none(),
                reason="Cargos Peace visuais/acesso não usam permissões globais",
            )


async def ensure_verification_surface(
    guild: discord.Guild,
    not_verified: discord.Role | None = None,
) -> tuple[discord.CategoryChannel | None, discord.TextChannel | None]:
    # `verify` is intentionally a root channel at position zero. Do not move
    # it into Reception or recreate the retired Verification category.
    category = None
    channel = discord.utils.find(
        lambda item: isinstance(item, discord.TextChannel)
        and item.name.casefold() in {VERIFICATION_CHANNEL_NAME, "verificar"},
        guild.text_channels,
    )
    if channel is None:
        channel = await guild.create_text_channel(
            VERIFICATION_CHANNEL_NAME,
            category=category,
            topic="Eu uso este canal somente para verificar membros.",
            reason="Criar canal de verificação no topo da Peace",
        )
    else:
        await channel.edit(
            name=VERIFICATION_CHANNEL_NAME,
            category=category,
            topic="Eu uso este canal somente para verificar membros.",
            position=0,
            reason="Manter o canal de verificação no topo sem categoria",
        )
    if channel.category is None and channel.position != 0:
        await channel.edit(position=0, reason="Manter o canal de verificação no topo sem categoria")
    await channel.set_permissions(
        guild.default_role,
        overwrite=perms(view_channel=False, read_message_history=False, send_messages=False),
        reason="Somente membros Not Verified visualizam a verificação",
    )
    allowed_subjects: set[discord.Role | discord.Member] = {guild.default_role}
    if not_verified is not None:
        access = perms(view_channel=True, read_message_history=True, send_messages=False)
        await channel.set_permissions(
            not_verified,
            overwrite=access,
            reason="Not Verified precisa acessar a verificação",
        )
        allowed_subjects.add(not_verified)
    if guild.me is not None:
        await channel.set_permissions(
            guild.me,
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            manage_messages=True,
            reason="Peace Tools precisa manter o painel de verificação",
        )
        allowed_subjects.add(guild.me)
    for subject in list(channel.overwrites):
        if subject not in allowed_subjects:
            await channel.set_permissions(
                subject,
                overwrite=None,
                reason="Remover acesso legado do canal de verificação",
            )
    return category, channel


async def clean_tickets(guild: discord.Guild, database: PeaceDatabase) -> None:
    categories = [
        guild.get_channel(OPEN_TICKET_CATEGORY_ID),
        guild.get_channel(CLOSED_TICKET_CATEGORY_ID),
        guild.get_channel(ATENDIMENTO_CATEGORY_ID),
    ]
    channels: list[discord.TextChannel] = []
    for category in categories:
        if isinstance(category, discord.CategoryChannel):
            channels.extend(channel for channel in category.text_channels if channel.name.startswith("sup-"))
    for channel in channels:
        log.info("Apagando ticket %s", channel.name)
        await channel.delete(reason="Limpeza solicitada dos tickets antigos da Peace")
    database.purge_tickets()
    old_open = guild.get_channel(OPEN_TICKET_CATEGORY_ID)
    if isinstance(old_open, discord.CategoryChannel) and not old_open.channels:
        await old_open.delete(reason="Categoria antiga de tickets substituída pelo atendimento")


async def clean_dev_chat(guild: discord.Guild) -> None:
    channel = guild.get_channel(CHANNEL_IDS["dev_chat"])
    if not isinstance(channel, discord.TextChannel):
        return
    messages = [message async for message in channel.history(limit=None, oldest_first=True)]
    for message in messages:
        await message.delete()
    log.info("Histórico limpo do canal dev")


async def remove_deprecated_roles(guild: discord.Guild) -> None:
    roles = [role for role_id in DEPRECATED_ROLE_IDS if (role := guild.get_role(role_id)) is not None]
    if roles:
        await snapshot_obsolete_role_members(guild, roles)
    for role in roles:
        try:
            await role.delete(reason="Remoção de cargos legados solicitada pela Peace")
            log.info("Cargo legado removido: %s", role.name)
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Não consegui remover cargo legado %s", role_id)


async def repair_open_ticket_access(
    guild: discord.Guild,
    database: PeaceDatabase,
    staff: discord.Role | None,
    manager: discord.Role | None,
) -> None:
    """Keep open tickets with Staff/Management and without deleted-role access."""
    channel_ids = {int(row["channel_id"]) for row in database.open_tickets()}
    for category_id in (OPEN_TICKET_CATEGORY_ID, ATENDIMENTO_CATEGORY_ID):
        category = guild.get_channel(category_id)
        if isinstance(category, discord.CategoryChannel):
            channel_ids.update(channel.id for channel in category.text_channels if channel.name.startswith("sup-"))
    for channel_id in channel_ids:
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            continue
        await clear_role_overwrites(channel, guild, [staff, manager])
        if staff is not None:
            await set_role_access(channel, staff, view=True, send=True, manage_messages=True)
        if manager is not None:
            await set_role_access(channel, manager, view=True, send=True, manage_messages=True)
        if guild.me is not None:
            await set_role_access(channel, guild.me.top_role, view=True, send=True, manage_messages=True)


async def remove_action_category(guild: discord.Guild) -> None:
    category = guild.get_channel(ACTION_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        return
    for channel in list(category.channels):
        await channel.delete(reason="Remoção da categoria AÇÃO solicitada pela Peace")
    await category.delete(reason="Remoção da categoria AÇÃO solicitada pela Peace")


async def remove_chat_elite(guild: discord.Guild) -> None:
    channel = guild.get_channel(CHANNEL_IDS["chat_elite"])
    if not isinstance(channel, discord.GuildChannel):
        channel = discord.utils.find(lambda item: "chat-elite" in item.name.casefold(), guild.channels)
    if isinstance(channel, discord.GuildChannel):
        await channel.delete(reason="Remover canal chat-elite conforme reorganização Peace")
        log.info("Canal chat-elite removido")


async def remove_developers_area(guild: discord.Guild) -> None:
    """Delete the obsolete Developers category and its child channels."""

    category = guild.get_channel(DEVELOPMENT_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        category = discord.utils.find(
            lambda item: isinstance(item, discord.CategoryChannel)
            and item.name.casefold() in LEGACY_DEVELOPMENT_CATEGORY_NAMES,
            guild.categories,
        )
    if isinstance(category, discord.CategoryChannel):
        for channel in list(category.channels):
            await channel.delete(reason="Remoção da área Developers solicitada pela Peace")
        await category.delete(reason="Remoção da área Developers solicitada pela Peace")
        return

    # If the category was already removed manually, still clean up the two
    # explicitly retired child channels without touching unrelated channels.
    for channel_id in (CHANNEL_IDS["dev_chat"], CHANNEL_IDS["dev_call"]):
        channel = guild.get_channel(channel_id)
        if isinstance(channel, discord.GuildChannel):
            await channel.delete(reason="Remoção de canal Developers solicitada pela Peace")


def validate_preflight(guild: discord.Guild) -> None:
    """Fail before mutation when the bot cannot manage this migration safely."""
    if guild.me is None:
        raise RuntimeError("O membro do bot não está disponível para validar a hierarquia")
    if guild.me.top_role.is_default():
        raise RuntimeError("O bot precisa de um cargo próprio acima de @everyone para aplicar a estrutura restrita")
    permissions = guild.me.guild_permissions
    if not permissions.manage_roles or not permissions.manage_channels:
        raise RuntimeError("O bot precisa de Gerenciar cargos e Gerenciar canais para a migração")
    target_names = {
        name.casefold()
        for name in (
            *ROLE_RENAMES.keys(),
            *OBSOLETE_ROLE_NAMES,
            NOT_VERIFIED_ROLE_NAME,
            INTERN_ROLE_NAME,
            ROLE_NAMES["investigator"],
            ROLE_NAMES["lead_investigator"],
        )
    }
    target_ids = (set(ROLE_IDS.values()) - {ROLE_IDS["founder"]}) | set(DEPRECATED_ROLE_IDS)
    target_ids |= {
        role.id for role in guild.roles if role.name.casefold() in target_names
    }
    blocked = [
        role.name
        for role in guild.roles
        if not role.managed
        and role.id in target_ids
        and role >= guild.me.top_role
    ]
    if blocked:
        raise RuntimeError("A hierarquia do bot bloqueia estes cargos: " + ", ".join(blocked))


async def apply_structure(
    guild: discord.Guild,
    database: PeaceDatabase,
    central_access_role_id: int | None = None,
    *,
    investigator_role_id: int | None = None,
    lead_investigator_role_id: int | None = None,
    private_call_category_id: int | None = None,
    remove_chat_elite_channel: bool = False,
    remove_developers: bool = False,
) -> None:
    validate_preflight(guild)
    if remove_developers:
        await remove_developers_area(guild)
    await remove_deprecated_roles(guild)
    await rename_roles(guild)

    obsolete = obsolete_named_roles(guild)
    if obsolete:
        await snapshot_obsolete_role_members(guild, obsolete)
    # Rename the surviving legacy AI role to AIs before deleting duplicate aliases.
    ai_role = await ensure_visual_role(
        guild,
        ROLE_NAMES["a_is"],
        discord.Colour(ROLE_COLOURS["AIs"]),
        aliases=("AI & Bots", "IA & Bots", "IA & Bots Peace"),
    )
    not_verified = await ensure_visual_role(
        guild,
        ROLE_NAMES["not_verified"],
        discord.Colour(ROLE_COLOURS["Not Verified"]),
        aliases=("Não Verificado", "Não verificado", "Nao verificado"),
    )
    intern = await ensure_visual_role(
        guild,
        ROLE_NAMES["intern"],
        discord.Colour(ROLE_COLOURS["Intern"]),
        aliases=("Estagiário", "Estagiario"),
    )
    investigator = await ensure_zero_permission_role(
        guild,
        ROLE_NAMES["investigator"],
        discord.Colour(ROLE_COLOURS["Investigator"]),
        aliases=("Investigador",),
        role_id=investigator_role_id,
        reason="Criar cargo de acesso Investigator da Peace",
    )
    lead_investigator = await ensure_zero_permission_role(
        guild,
        ROLE_NAMES["lead_investigator"],
        discord.Colour(ROLE_COLOURS["Lead Investigator"]),
        aliases=(
            "Chief Investigator",
            "Investigador Líder",
            "Investigador-chefe",
            "Investigador chefe",
        ),
        role_id=lead_investigator_role_id,
        reason="Criar cargo de acesso Lead Investigator da Peace",
    )
    await remove_obsolete_named_roles(guild, snapshot=False)

    peace = role_by_id_or_name(guild, ROLE_IDS["peace"], ROLE_NAMES["peace"])
    staff = role_by_id_or_name(guild, ROLE_IDS["staff"], ROLE_NAMES["staff"])
    manager = role_by_id_or_name(guild, ROLE_IDS["manager"], ROLE_NAMES["manager"])
    visitor = role_by_id_or_name(guild, ROLE_IDS["visitor"], ROLE_NAMES["visitor"])
    founder = role_by_id_or_name(guild, ROLE_IDS["founder"], "Founder Peace")
    technical = role_by_id_or_name(guild, central_access_role_id, ROLE_NAMES["technical"])
    if technical is None:
        technical = find_role(guild, ROLE_NAMES["technical"])
    legacy_florenza = guild.get_role(ROLE_IDS["florenza_legacy"])

    await style_role(peace, ROLE_NAMES["peace"], ROLE_COLOURS["Peace"])
    await style_role(staff, ROLE_NAMES["staff"], ROLE_COLOURS["Staff"])
    await style_role(manager, ROLE_NAMES["manager"], ROLE_COLOURS["Gerência"])
    await style_role(visitor, ROLE_NAMES["visitor"], ROLE_COLOURS["Visitante"])
    await style_role(technical, ROLE_NAMES["technical"], ROLE_COLOURS["Developer"])
    await style_role(
        find_role(guild, ROLE_NAMES["general_manager"]),
        ROLE_NAMES["general_manager"],
        ROLE_COLOURS["Delegado"],
    )
    await style_role(
        find_role(guild, ROLE_NAMES["elite"]),
        ROLE_NAMES["elite"],
        ROLE_COLOURS["Agente Especial"],
    )
    await style_role(
        find_role(guild, ROLE_NAMES["novato"]),
        ROLE_NAMES["novato"],
        ROLE_COLOURS["Aluno"],
    )
    await style_role(
        find_role(guild, ROLE_NAMES["member"]),
        ROLE_NAMES["member"],
        ROLE_COLOURS["Agente"],
    )

    await ensure_visual_role(
        guild,
        "Developer",
        discord.Colour(ROLE_COLOURS["Developer"]),
        aliases=("Desenvolvedor Peace", "Developer Peace"),
    )
    await ensure_visual_role(
        guild,
        "Diretor Geral",
        discord.Colour(ROLE_COLOURS["Diretor Geral"]),
        aliases=("General Director", "Diretor geral"),
    )
    try:
        members = [member async for member in guild.fetch_members(limit=None)]
    except (discord.Forbidden, discord.HTTPException):
        members = list(guild.members)
    await clear_non_bot_role_permissions(guild, members)
    if guild.me is not None and ai_role not in guild.me.roles:
        try:
            await guild.me.add_roles(ai_role, reason="Cargo visual AIs exclusivo do bot da Peace")
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não consegui aplicar o cargo AIs ao bot da Peace")
    if technical is not None and legacy_florenza is not None:
        for member in members:
            if legacy_florenza in member.roles and technical not in member.roles:
                try:
                    await member.add_roles(technical, reason="Migração do acesso dev legado")
                except (discord.Forbidden, discord.HTTPException):
                    log.info("Não consegui migrar o acesso dev de %s", member.id)

    # Staff and Management are access roles; every other named role remains visual.
    staff_category = discord.utils.find(
        lambda item: isinstance(item, discord.CategoryChannel)
        and item.name.casefold() == "[🛡️] staff".casefold(),
        guild.categories,
    )
    if staff_category is None:
        staff_category = await guild.create_category(CATEGORY_NAMES["staff"], reason="Categoria interna de Staff Peace")
    elif staff_category.name != CATEGORY_NAMES["staff"]:
        await staff_category.edit(name=CATEGORY_NAMES["staff"], reason="Padronizar categoria Staff Peace")
    staff_roles = [staff, manager, founder]
    await configure_category(staff_category, guild, staff_roles)
    if guild.me is not None:
        await set_role_access(staff_category, guild.me.top_role, view=True, send=True)

    for key, desired_name in (("staff_only", "staff-only"), ("scan_only", "scan-only"), ("logs", "logs")):
        channel = guild.get_channel(CHANNEL_IDS[key])
        if not isinstance(channel, discord.TextChannel):
            continue
        await channel.edit(name=desired_name, category=staff_category, reason="Organização da área interna de Staff")
        # Both surfaces are bot-written. Staff may read and use component
        # actions, but no human role may post messages in either channel.
        log_roles = [*staff_roles, technical] if key == "logs" else staff_roles
        await configure_text(channel, guild, allowed=log_roles, send=False, bot_only=True)
        if guild.me is not None:
            await set_role_access(channel, guild.me.top_role, view=True, send=True, manage_messages=True)

    # Keep the visible structure English while preserving every existing channel ID.
    reception = discord.utils.find(
        lambda item: isinstance(item, discord.CategoryChannel)
        and item.name.casefold() in {
            CATEGORY_NAMES["reception"].casefold(),
            "[🎫] recepção",
            "[🎫] recepcao",
        },
        guild.categories,
    )
    if reception is not None and reception.name != CATEGORY_NAMES["reception"]:
        await reception.edit(
            name=CATEGORY_NAMES["reception"],
            reason="Padronizar categoria de recepção em inglês",
        )
    await rename_channel(
        guild,
        "├📕・rules",
        None,
        "├📕・regras",
    )
    await rename_channel(
        guild,
        "╭📣・announcements",
        CHANNEL_IDS["avisos"],
        "╭📣・avisos",
    )
    await rename_channel(
        guild,
        "├🤝・partners",
        CHANNEL_IDS["parceiros"],
        "├🤝・parceiros",
    )
    await rename_channel(
        guild,
        "├📸・media",
        CHANNEL_IDS["midias"],
        "├📸・midias",
    )
    await rename_channel(
        guild,
        "├📹・clips",
        CHANNEL_IDS["clipes"],
        "├📹・clipes",
    )
    await rename_channel(
        guild,
        "╰🎯・dashboard",
        CHANNEL_IDS["painel"],
        "╰🎯・painel",
    )
    await rename_channel(
        guild,
        "╭💬・general-chat",
        CHANNEL_IDS["chat_geral"],
        "╭💬・chat-geral",
    )
    await rename_channel(
        guild,
        "├💬・management-chat",
        CHANNEL_IDS["chat_gerencia"],
        "├💬・chat-gerencia",
    )
    await rename_channel(
        guild,
        "├💬・visitor-chat",
        CHANNEL_IDS["chat_visitante"],
        "├💬・chat-visitante",
    )
    await rename_channel(
        guild,
        "╰🎵・music",
        CHANNEL_IDS["musica"],
        "╰🎵・música",
        "╰🎵・musica",
    )

    closed_category = guild.get_channel(CLOSED_TICKET_CATEGORY_ID)
    if isinstance(closed_category, discord.CategoryChannel):
        category_positions = [category.position for category in guild.categories]
        await closed_category.edit(
            name=CATEGORY_NAMES["closed_tickets"],
            position=max(category_positions, default=closed_category.position) + 1,
            reason="TICKETS-FECHADOS deve permanecer como última categoria",
        )

    calls = guild.get_channel(CALLS_CATEGORY_ID)
    call_roles = [peace, technical, staff, manager, founder]
    if isinstance(calls, discord.CategoryChannel):
        await calls.edit(name=CATEGORY_NAMES["calls"], reason="Padronização das calls normais Peace")
        await configure_category(calls, guild, call_roles)
        for channel in calls.voice_channels:
            await configure_voice(channel, guild, allowed=call_roles, move_members=False)
            await set_role_access(channel, manager, view=True, connect=True, speak=True, move_members=True)

    private_calls = guild.get_channel(private_call_category_id) if private_call_category_id else None
    if isinstance(private_calls, discord.CategoryChannel) and private_calls.id != CALLS_CATEGORY_ID:
        await private_calls.edit(
            name=CATEGORY_NAMES["private_calls"],
            reason="Padronização da categoria de calls privadas Peace",
        )
        for channel in private_calls.voice_channels:
            if "gerência" in channel.name.casefold() or "gerencia" in channel.name.casefold():
                await channel.edit(
                    name="╰🎧・Management",
                    reason="Padronizar call de gerência em inglês",
                )

    atendimento = guild.get_channel(ATENDIMENTO_CATEGORY_ID)
    support_roles = [peace, visitor, staff, manager, founder]
    if isinstance(atendimento, discord.CategoryChannel):
        await atendimento.edit(name=CATEGORY_NAMES["support"], reason="Padronizar categoria de suporte Peace")
        await configure_category(atendimento, guild, support_roles)
        for channel in atendimento.voice_channels:
            if "suporte" in channel.name.casefold():
                await channel.edit(
                    name=channel.name.replace("Suporte", "Support").replace("suporte", "Support"),
                    reason="Padronizar calls de suporte em inglês",
                )
            await configure_voice(channel, guild, allowed=support_roles, move_members=False)
            await set_role_access(channel, staff, view=True, connect=True, speak=True, move_members=True)
        for channel in atendimento.text_channels:
            if channel.id != CHANNEL_IDS["ticket_panel"] and not channel.name.startswith("sup-"):
                await configure_text(channel, guild, allowed=support_roles, send=True)
    waiting_voice = guild.get_channel(CHANNEL_IDS["waiting_voice"])
    if isinstance(waiting_voice, discord.VoiceChannel):
        await waiting_voice.edit(name="╰📞・Waiting for Support", reason="Padronização da espera de suporte")
        await configure_voice(waiting_voice, guild, allowed=support_roles, move_members=False)
        await set_role_access(waiting_voice, staff, view=True, connect=True, speak=True, move_members=True)

    await ensure_verification_surface(guild, not_verified)

    # Investigation is a site-owned surface. Keep the access roles in Discord,
    # but never create, rename, or permission a Discord category/channel for it.
    # Existing legacy objects are intentionally left untouched; cleanup requires
    # a separate, explicit operator action.

    registros = guild.get_channel(REGISTROS_CATEGORY_ID)
    registration_roles = [peace, technical, staff, manager, founder]
    if isinstance(registros, discord.CategoryChannel):
        await registros.edit(name=CATEGORY_NAMES["records"], reason="Padronizar categoria de registros")
        await configure_category(registros, guild, registration_roles)
    for key in ("avisos", "parceiros"):
        channel = guild.get_channel(CHANNEL_IDS[key])
        if isinstance(channel, discord.TextChannel):
            await configure_text(channel, guild, allowed=registration_roles, send=False)
            if key == "parceiros":
                # All verified internal roles can read partner posts; only
                # Management may publish or edit them in Discord.
                await set_role_access(channel, manager, view=True, send=True, manage_messages=True)
    # These channels belong to the records area; they are not public onboarding
    # surfaces and must not leak to Not Verified or Visitor.
    for key, send in (("midias", True), ("clipes", True), ("painel", False)):
        channel = guild.get_channel(CHANNEL_IDS[key])
        if isinstance(channel, discord.TextChannel):
            await configure_text(channel, guild, allowed=registration_roles, send=send)

    rules = guild.get_channel(CHANNEL_IDS["rules"])
    if isinstance(rules, discord.TextChannel):
        # Rules are readable by verified visitors and internal access roles,
        # but the server must remain invisible to @everyone until verification.
        await configure_text(
            rules,
            guild,
            allowed=[peace, visitor, staff, manager, founder],
            send=False,
        )
    automod = guild.get_channel(AUTOMOD_CHANNEL_ID)
    if isinstance(automod, discord.TextChannel):
        await automod.edit(
            name="spam-control",
            category=None,
            position=0,
            topic="Private spam control. Do not send messages in this channel.",
            reason="Canal privado de moderação Peace",
        )
        await configure_text(automod, guild, allowed=[], send=False)
        if guild.me is not None:
            for subject in list(automod.overwrites):
                if subject in {guild.default_role, guild.me}:
                    continue
                await automod.set_permissions(
                    subject,
                    overwrite=None,
                    reason="Remover acessos individuais do canal privado de spam",
                )
            await automod.set_permissions(
                guild.me,
                overwrite=perms(
                    view_channel=True,
                    read_message_history=True,
                    send_messages=True,
                    manage_messages=True,
                ),
                reason="Peace Tools precisa manter o canal privado de spam",
            )

    social = discord.utils.find(
        lambda item: isinstance(item, discord.CategoryChannel)
        and ("resenha" in item.name.casefold() or "social" in item.name.casefold()),
        guild.categories,
    )
    social_roles = [peace, staff, manager, founder]
    if isinstance(social, discord.CategoryChannel):
        await social.edit(name=CATEGORY_NAMES["social"], reason="Padronizar categoria social Peace")
        await configure_category(social, guild, social_roles)
    chat_geral = guild.get_channel(CHANNEL_IDS["chat_geral"])
    if isinstance(chat_geral, discord.TextChannel):
        await configure_text(chat_geral, guild, allowed=[peace, staff, manager, founder], send=True)
    chat_gerencia = guild.get_channel(CHANNEL_IDS["chat_gerencia"])
    if isinstance(chat_gerencia, discord.TextChannel):
        await configure_text(chat_gerencia, guild, allowed=[staff, manager, founder], send=True)
        await deny_role(chat_gerencia, peace)
        await deny_role(chat_gerencia, visitor)
    chat_visitante = guild.get_channel(CHANNEL_IDS["chat_visitante"])
    if isinstance(chat_visitante, discord.TextChannel):
        await configure_text(chat_visitante, guild, allowed=[visitor, staff, manager, founder], send=True)
        await deny_role(chat_visitante, peace)
        await deny_role(chat_visitante, technical)
    musica = guild.get_channel(CHANNEL_IDS["musica"])
    if isinstance(musica, discord.TextChannel):
        await configure_text(musica, guild, allowed=[peace, staff, manager, founder], send=True)

    ticket_panel = guild.get_channel(CHANNEL_IDS["ticket_panel"])
    if isinstance(ticket_panel, discord.TextChannel):
        await ticket_panel.edit(name="╭❗・ticket", reason="Padronização do último canal de atendimento")
        await configure_text(ticket_panel, guild, allowed=support_roles, send=False)

    afk = guild.get_channel(AFK_CHANNEL_ID)
    if isinstance(afk, discord.VoiceChannel):
        await afk.edit(category=None, position=1, name="AFK", reason="AFK visível sem entrada da Peace")
        await configure_voice(
            afk,
            guild,
            allowed=[peace, visitor, staff, manager, founder],
            connect=False,
            speak=False,
            move_members=False,
        )

    if remove_chat_elite_channel:
        await remove_chat_elite(guild)
    old_open = guild.get_channel(OPEN_TICKET_CATEGORY_ID)
    if isinstance(atendimento, discord.CategoryChannel) and isinstance(old_open, discord.CategoryChannel):
        for channel in list(old_open.text_channels):
            if channel.name.startswith("sup-"):
                await channel.edit(category=atendimento, reason="Tickets abertos integrados ao atendimento")
    await repair_open_ticket_access(guild, database, staff, manager)
    database.initialize()


def run_once(
    *,
    apply: bool,
    clean: bool,
    clean_dev: bool,
    remove_chat_elite_channel: bool,
    remove_developers: bool,
) -> None:
    settings = Settings.from_env()
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        guild = client.get_guild(settings.guild_id)
        if guild is None:
            log.error("Servidor Peace não está disponível no cache")
            await client.close()
            return
        log.info("Servidor encontrado: %s", guild.name)
        if not apply:
            log.info("Modo simulação: nenhuma alteração foi aplicada")
            await client.close()
            return
        database = PeaceDatabase(settings.database_path)
        try:
            await apply_structure(
                guild,
                database,
                settings.central_access_role_id,
                investigator_role_id=settings.investigator_role_id,
                lead_investigator_role_id=settings.lead_investigator_role_id,
                private_call_category_id=settings.private_call_category_id,
                remove_chat_elite_channel=remove_chat_elite_channel,
                remove_developers=remove_developers,
            )
        except Exception:
            log.exception("Migração interrompida antes da conclusão; revise o estado parcial")
            await client.close()
            return
        if clean:
            await clean_tickets(guild, database)
            await remove_action_category(guild)
        if clean_dev:
            await clean_dev_chat(guild)
        log.info("Reorganização concluída")
        await client.close()

    client.run(settings.token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reorganiza a estrutura atual da Peace")
    parser.add_argument("--apply", action="store_true", help="aplica as alterações")
    parser.add_argument("--remove-chat-elite", action="store_true", help="remove o canal chat-elite")
    parser.add_argument(
        "--remove-developers",
        action="store_true",
        help="remove a categoria Developers e os canais dev-chat/programming",
    )
    parser.add_argument("--clean", action="store_true", help="remove tickets e a categoria AÇÃO")
    parser.add_argument("--clean-dev-chat", action="store_true", help="limpa todo o histórico do chat-dev")
    args = parser.parse_args()
    if (args.clean or args.clean_dev_chat or args.remove_chat_elite or args.remove_developers) and not args.apply:
        parser.error("ações destrutivas exigem --apply")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_once(
        apply=args.apply,
        clean=args.clean,
        clean_dev=args.clean_dev_chat,
        remove_chat_elite_channel=args.remove_chat_elite,
        remove_developers=args.remove_developers,
    )


if __name__ == "__main__":
    main()
