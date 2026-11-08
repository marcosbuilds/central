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

GUILD_ID = 1427129030427279503
ACTION_CATEGORY_ID = 1466632839339577364
OPEN_TICKET_CATEGORY_ID = 1495063893838532730
CLOSED_TICKET_CATEGORY_ID = 1495064004194861137
ATENDIMENTO_CATEGORY_ID = 1459444056064262186
REGISTROS_CATEGORY_ID = 1459443063754592297
DEVELOPMENT_CATEGORY_ID = 1506409116686614608
CALLS_CATEGORY_ID = 1459444321425035386
AFK_CHANNEL_ID = 1466629495405543515
AUTOMOD_CHANNEL_ID = 1555060813046226964
VERIFICATION_CATEGORY_NAME = "[🔐] VERIFICATION"
VERIFICATION_CHANNEL_NAME = "verificar"
NOT_VERIFIED_ROLE_NAME = "Not Verified"
INTERN_ROLE_NAME = "Intern"

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
    "manager": "Management",
    "general_manager": "Manager ⎰ Deputy Delegate",
    "visitor": "Visitor",
    "elite": "Elite ⎰ Special Agent",
    "novato": "Rookie ⎰ Agent",
    "member": "Member ⎰ Recruit",
    "technical": "Dev",
    "a_is": "AIs",
    "not_verified": NOT_VERIFIED_ROLE_NAME,
    "intern": INTERN_ROLE_NAME,
}

ROLE_RENAMES = {
    "Staff Peace": "Staff",
    "Novato Peace": "Rookie ⎰ Agent",
    "Novato ⎰ Agente": "Rookie ⎰ Agent",
    "Membro Peace": "Member ⎰ Recruit",
    "Membro ⎰ Recruta": "Member ⎰ Recruit",
    "Elite Peace": "Elite ⎰ Special Agent",
    "Elite ⎰ Ag. Especial": "Elite ⎰ Special Agent",
    "Gerência": "Management",
    "Gerencia": "Management",
    "Gerente geral": "Manager ⎰ Deputy Delegate",
    "Gerente Geral": "Manager ⎰ Deputy Delegate",
    "Gerente ⎰ Delegado adjunto": "Manager ⎰ Deputy Delegate",
    "Estagiário": "Intern",
    "Visitante": "Visitor",
}

OBSOLETE_ROLE_NAMES = (
    "Gerente de elites",
    "Gerente de recrutadores",
    "Gerente de vendas",
    "Gerente de farms",
    "Recrutador",
    "IA & Bots",
    "AI & Bots",
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
) -> discord.Role | None:
    if role_id is not None:
        role = guild.get_role(role_id)
        if role is not None:
            return role
    return find_role(guild, name) if name else None


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
    await channel.set_permissions(role, overwrite=perms(**values), reason="Reorganização Peace")


async def set_default_access(
    channel: discord.abc.GuildChannel,
    guild: discord.Guild,
    *,
    view: bool,
    send: bool = False,
    connect: bool | None = None,
    speak: bool | None = None,
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


async def configure_text(
    channel: discord.TextChannel,
    guild: discord.Guild,
    *,
    allowed: list[discord.Role | None],
    public: bool = False,
    send: bool = True,
) -> None:
    await clear_role_overwrites(channel, guild, allowed)
    await set_default_access(channel, guild, view=public, send=send if public else False)
    for role in allowed:
        await set_role_access(channel, role, view=True, send=send)


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


async def ensure_visual_role(
    guild: discord.Guild,
    name: str,
    colour: discord.Colour,
    aliases: tuple[str, ...] = (),
) -> discord.Role:
    existing = find_role(guild, name) or find_role(guild, *aliases)
    if existing is not None:
        if existing.name != name or existing.permissions != discord.Permissions.none():
            await existing.edit(
                name=name,
                permissions=discord.Permissions.none(),
                colour=colour,
                reason="Padronização dos cargos visuais Peace",
            )
        return existing
    return await guild.create_role(
        name=name,
        colour=colour,
        permissions=discord.Permissions.none(),
        hoist=False,
        mentionable=False,
        reason="Criar cargo visual Peace",
    )


async def rename_roles(guild: discord.Guild) -> None:
    for old_name, new_name in ROLE_RENAMES.items():
        role = find_role(guild, old_name)
        if role is None or role.name == new_name:
            continue
        await role.edit(name=new_name, reason="Padronização dos nomes de cargos Peace")


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
    category = discord.utils.find(
        lambda item: item.name.casefold() == VERIFICATION_CATEGORY_NAME.casefold(),
        guild.categories,
    )
    if category is None:
        category = await guild.create_category(
            VERIFICATION_CATEGORY_NAME,
            reason="Criar área única de verificação da Peace",
        )
    await category.set_permissions(
        guild.default_role,
        overwrite=perms(view_channel=False, read_message_history=False, send_messages=False),
        reason="Somente membros Not Verified visualizam a verificação",
    )
    channel = discord.utils.find(
        lambda item: item.name.casefold() == VERIFICATION_CHANNEL_NAME.casefold()
        and item.category_id == category.id,
        guild.text_channels,
    )
    if channel is None:
        channel = discord.utils.find(
            lambda item: item.name.casefold() == VERIFICATION_CHANNEL_NAME.casefold(),
            guild.text_channels,
        )
    if channel is None:
        channel = await guild.create_text_channel(
            VERIFICATION_CHANNEL_NAME,
            category=category,
            topic="Eu uso este canal somente para verificar membros.",
            reason="Criar canal único de verificação da Peace",
        )
    else:
        await channel.edit(
            name=VERIFICATION_CHANNEL_NAME,
            category=category,
            topic="Eu uso este canal somente para verificar membros.",
            reason="Padronizar canal único de verificação da Peace",
        )
    await channel.set_permissions(
        guild.default_role,
        overwrite=perms(view_channel=False, read_message_history=False, send_messages=False),
        reason="Somente membros Not Verified visualizam a verificação",
    )
    if not_verified is not None:
        access = perms(view_channel=True, read_message_history=True, send_messages=False)
        await category.set_permissions(
            not_verified,
            overwrite=access,
            reason="Not Verified precisa acessar a verificação",
        )
        await channel.set_permissions(
            not_verified,
            overwrite=access,
            reason="Not Verified precisa acessar a verificação",
        )
    if guild.me is not None:
        await category.set_permissions(
            guild.me,
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            manage_messages=True,
            reason="Peace Tools precisa manter a categoria de verificação",
        )
        await channel.set_permissions(
            guild.me,
            view_channel=True,
            read_message_history=True,
            send_messages=True,
            manage_messages=True,
            reason="Peace Tools precisa manter o painel de verificação",
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
    for role_id in DEPRECATED_ROLE_IDS:
        role = guild.get_role(role_id)
        if role is None:
            continue
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


def validate_preflight(guild: discord.Guild) -> None:
    """Fail before mutation when the bot cannot manage this migration safely."""
    if guild.me is None:
        raise RuntimeError("O membro do bot não está disponível para validar a hierarquia")
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
    remove_chat_elite_channel: bool = False,
) -> None:
    validate_preflight(guild)
    await remove_deprecated_roles(guild)
    await rename_roles(guild)

    obsolete = obsolete_named_roles(guild)
    if obsolete:
        await snapshot_obsolete_role_members(guild, obsolete)
    # Rename the surviving legacy AI role to AIs before deleting duplicate aliases.
    ai_role = await ensure_visual_role(
        guild,
        ROLE_NAMES["a_is"],
        discord.Colour.purple(),
        aliases=("AI & Bots", "IA & Bots", "IA & Bots Peace"),
    )
    not_verified = await ensure_visual_role(
        guild,
        ROLE_NAMES["not_verified"],
        discord.Colour.dark_grey(),
        aliases=("Não verificado", "Nao verificado"),
    )
    intern = await ensure_visual_role(
        guild,
        ROLE_NAMES["intern"],
        discord.Colour.teal(),
        aliases=("Estagiário", "Estagiario"),
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

    await ensure_visual_role(
        guild,
        "Developer",
        discord.Colour.blurple(),
        aliases=("Desenvolvedor Peace", "Developer Peace"),
    )
    await ensure_visual_role(guild, "Frontend", discord.Colour.teal(), aliases=("Frontend Peace",))
    await ensure_visual_role(guild, "Backend", discord.Colour.dark_teal(), aliases=("Backend Peace",))
    await ensure_visual_role(
        guild,
        "Documentation",
        discord.Colour.gold(),
        aliases=("Documentação Peace", "Documentation Peace"),
    )
    await ensure_visual_role(
        guild,
        "General Director",
        discord.Colour.dark_gold(),
        aliases=("Diretor geral", "Diretor Geral"),
    )
    await ensure_visual_role(
        guild,
        "Superintendent",
        discord.Colour.dark_purple(),
        aliases=("Superintendente",),
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
        staff_category = await guild.create_category("[🛡️] STAFF", reason="Categoria interna de Staff Peace")
    elif staff_category.name != "[🛡️] STAFF":
        await staff_category.edit(name="[🛡️] STAFF", reason="Padronizar categoria Staff Peace")
    staff_roles = [staff, manager, founder]
    await configure_category(staff_category, guild, staff_roles)
    if guild.me is not None:
        await set_role_access(staff_category, guild.me.top_role, view=True, send=True)

    for key, desired_name in (("staff_only", "staff-only"), ("scan_only", "scan-only"), ("logs", "logs")):
        channel = guild.get_channel(CHANNEL_IDS[key])
        if not isinstance(channel, discord.TextChannel):
            continue
        await channel.edit(name=desired_name, category=staff_category, reason="Organização da área interna de Staff")
        await configure_text(channel, guild, allowed=staff_roles, send=key != "logs")
        if guild.me is not None:
            await set_role_access(channel, guild.me.top_role, view=True, send=True, manage_messages=True)

    closed_category = guild.get_channel(CLOSED_TICKET_CATEGORY_ID)
    if isinstance(closed_category, discord.CategoryChannel):
        category_positions = [category.position for category in guild.categories]
        await closed_category.edit(
            position=max(category_positions, default=closed_category.position) + 1,
            reason="TICKETS-FECHADOS deve permanecer como última categoria",
        )

    development = guild.get_channel(DEVELOPMENT_CATEGORY_ID)
    development_roles = [technical, staff, manager, founder]
    if isinstance(development, discord.CategoryChannel):
        await development.edit(name="[💻] DEVELOPERS", reason="Padronização da área técnica em inglês")
        await configure_category(development, guild, development_roles)
        dev_chat = guild.get_channel(CHANNEL_IDS["dev_chat"])
        dev_call = guild.get_channel(CHANNEL_IDS["dev_call"])
        if isinstance(dev_chat, discord.TextChannel):
            await dev_chat.edit(name="╰💬・chat-dev", reason="Padronização do canal Developers")
            await configure_text(dev_chat, guild, allowed=development_roles, send=True)
        if isinstance(dev_call, discord.VoiceChannel):
            await dev_call.edit(name="╭💻・programming", reason="Padronização da call Developers")
            await configure_voice(dev_call, guild, allowed=development_roles, move_members=False)
    if legacy_florenza is not None and isinstance(development, discord.CategoryChannel):
        await development.set_permissions(legacy_florenza, overwrite=None, reason="Remoção do acesso dev legado")

    calls = guild.get_channel(CALLS_CATEGORY_ID)
    call_roles = [peace, technical, staff, manager, founder]
    if isinstance(calls, discord.CategoryChannel):
        await calls.edit(name="[🎙️] CALLS", reason="Padronização das calls normais Peace")
        await configure_category(calls, guild, call_roles)
        for channel in calls.voice_channels:
            await configure_voice(channel, guild, allowed=call_roles, move_members=False)
            await set_role_access(channel, manager, view=True, connect=True, speak=True, move_members=True)

    atendimento = guild.get_channel(ATENDIMENTO_CATEGORY_ID)
    support_roles = [peace, visitor, staff, manager, founder]
    if isinstance(atendimento, discord.CategoryChannel):
        await configure_category(atendimento, guild, support_roles)
        for channel in atendimento.voice_channels:
            await configure_voice(channel, guild, allowed=support_roles, move_members=False)
            await set_role_access(channel, staff, view=True, connect=True, speak=True, move_members=True)
        for channel in atendimento.text_channels:
            if channel.id != CHANNEL_IDS["ticket_panel"] and not channel.name.startswith("sup-"):
                await configure_text(channel, guild, allowed=support_roles, send=True)
    waiting_voice = guild.get_channel(CHANNEL_IDS["waiting_voice"])
    if isinstance(waiting_voice, discord.VoiceChannel):
        await waiting_voice.edit(name="╭📞・Aguardando suporte", reason="Padronização da espera de suporte")
        await configure_voice(waiting_voice, guild, allowed=support_roles, move_members=False)
        await set_role_access(waiting_voice, staff, view=True, connect=True, speak=True, move_members=True)

    await ensure_verification_surface(guild, not_verified)

    registros = guild.get_channel(REGISTROS_CATEGORY_ID)
    registration_roles = [peace, technical, staff, manager, founder]
    if isinstance(registros, discord.CategoryChannel):
        await registros.edit(name="[ℹ️] REGISTROS", reason="Padronizar categoria de registros")
        await configure_category(registros, guild, registration_roles)
    for key in ("avisos", "parceiros"):
        channel = guild.get_channel(CHANNEL_IDS[key])
        if isinstance(channel, discord.TextChannel):
            await configure_text(channel, guild, allowed=registration_roles, send=False)
    for key, send in (("midias", True), ("clipes", True), ("painel", False)):
        channel = guild.get_channel(CHANNEL_IDS[key])
        if isinstance(channel, discord.TextChannel):
            await configure_text(channel, guild, allowed=[], public=True, send=send)

    rules = guild.get_channel(CHANNEL_IDS["rules"])
    if isinstance(rules, discord.TextChannel):
        await configure_text(rules, guild, allowed=[], public=True, send=False)
    automod = guild.get_channel(AUTOMOD_CHANNEL_ID)
    if isinstance(automod, discord.TextChannel):
        await automod.edit(
            name="spam-control",
            category=None,
            position=0,
            topic="Spam control only. Do not send messages in this channel.",
            reason="Honeypot público da moderação Peace",
        )
        await configure_text(automod, guild, allowed=[], public=True, send=True)

    social = discord.utils.find(
        lambda item: isinstance(item, discord.CategoryChannel)
        and ("resenha" in item.name.casefold() or "social" in item.name.casefold()),
        guild.categories,
    )
    social_roles = [peace, staff, manager, founder]
    if isinstance(social, discord.CategoryChannel):
        await social.edit(name="[🔔] RESENHA & SOCIAL", reason="Padronizar categoria social Peace")
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
        await ticket_panel.edit(name="╰❗・ticket", reason="Padronização do último canal de atendimento")
        await configure_text(ticket_panel, guild, allowed=support_roles, public=True, send=False)

    afk = guild.get_channel(AFK_CHANNEL_ID)
    if isinstance(afk, discord.VoiceChannel):
        await afk.edit(category=None, position=1, name="AFK", reason="AFK público e visível da Peace")
        await clear_role_overwrites(afk, guild, [])
        await set_default_access(afk, guild, view=True, connect=False, speak=False)

    if remove_chat_elite_channel:
        await remove_chat_elite(guild)
    old_open = guild.get_channel(OPEN_TICKET_CATEGORY_ID)
    if isinstance(atendimento, discord.CategoryChannel) and isinstance(old_open, discord.CategoryChannel):
        for channel in list(old_open.text_channels):
            if channel.name.startswith("sup-"):
                await channel.edit(category=atendimento, reason="Tickets abertos integrados ao atendimento")
    await repair_open_ticket_access(guild, database, staff, manager)
    database.initialize()


def run_once(*, apply: bool, clean: bool, clean_dev: bool, remove_chat_elite_channel: bool) -> None:
    settings = Settings.from_env()
    intents = discord.Intents.default()
    intents.members = True
    client = discord.Client(intents=intents)

    @client.event
    async def on_ready() -> None:
        guild = client.get_guild(GUILD_ID or settings.guild_id)
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
                remove_chat_elite_channel=remove_chat_elite_channel,
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
    parser.add_argument("--clean", action="store_true", help="remove tickets e a categoria AÇÃO")
    parser.add_argument("--clean-dev-chat", action="store_true", help="limpa todo o histórico do chat-dev")
    args = parser.parse_args()
    if (args.clean or args.clean_dev_chat or args.remove_chat_elite) and not args.apply:
        parser.error("ações destrutivas exigem --apply")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_once(
        apply=args.apply,
        clean=args.clean,
        clean_dev=args.clean_dev_chat,
        remove_chat_elite_channel=args.remove_chat_elite,
    )


if __name__ == "__main__":
    main()
