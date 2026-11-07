"""Aplicação única da reorganização do servidor Peace.

Uso recomendado:
    python -m bot.maintenance --apply
    python -m bot.maintenance --apply --clean

Sem --apply, o módulo apenas lista o que seria alterado. A limpeza destrutiva
de tickets e da categoria de ação só ocorre com --clean explícito.
"""

from __future__ import annotations

import argparse
import asyncio
import logging

import discord

from .cfg import Settings
from .db import PeaceDatabase


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
    "recruiter": 1466837291686297600,
    "visitor": 1474515602625269936,
    "elite": 1486981235719934082,
    "florenza_legacy": 1506409509667606569,
    "founder": 1428158506887938231,
}

DEPRECATED_ROLE_IDS = (
    1495091523245838506,  # Advertência I
    1495091691743481876,  # Advertência II
    1495091763189387395,  # Advertência III
    1466835667928744068,  # Sublider
)


def perms(**kwargs: bool) -> discord.PermissionOverwrite:
    return discord.PermissionOverwrite(**kwargs)


async def set_role_access(
    channel: discord.abc.GuildChannel,
    role: discord.Role | None,
    *,
    view: bool,
    send: bool = False,
    connect: bool | None = None,
    speak: bool | None = None,
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
    """Remove permissões de cargos antigos para evitar acesso herdado indevido."""
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
    visitor_denied: bool = False,
) -> None:
    preserved = list(allowed)
    if visitor_denied:
        preserved.append(guild.get_role(ROLE_IDS["visitor"]))
    await clear_role_overwrites(channel, guild, preserved)
    await set_default_access(channel, guild, view=public, send=send if public else False)
    for role in allowed:
        await set_role_access(channel, role, view=True, send=send)
    if visitor_denied:
        visitor = guild.get_role(ROLE_IDS["visitor"])
        await set_role_access(channel, visitor, view=False, send=False)


async def configure_voice(
    channel: discord.VoiceChannel,
    guild: discord.Guild,
    *,
    allowed: list[discord.Role | None],
    public: bool = False,
    connect: bool = True,
    speak: bool = True,
) -> None:
    await clear_role_overwrites(channel, guild, list(allowed))
    await set_default_access(channel, guild, view=public, connect=connect if public else False, speak=speak if public else False)
    for role in allowed:
        await set_role_access(channel, role, view=True, connect=connect, speak=speak)


def role_by_id_or_name(guild: discord.Guild, role_id: int | None, name: str | None = None) -> discord.Role | None:
    if role_id is None:
        return None
    role = guild.get_role(role_id)
    if role is not None:
        return role
    if name:
        return discord.utils.find(lambda item: item.name.casefold() == name.casefold(), guild.roles)
    return None


async def ensure_visual_role(
    guild: discord.Guild,
    name: str,
    colour: discord.Colour,
    aliases: tuple[str, ...] = (),
) -> discord.Role:
    names = {name.casefold(), *(alias.casefold() for alias in aliases)}
    existing = discord.utils.find(lambda item: item.name.casefold() in names, guild.roles)
    if existing is not None:
        if existing.name != name or existing.permissions != discord.Permissions.none():
            await existing.edit(
                name=name,
                permissions=discord.Permissions.none(),
                colour=colour,
                reason="Padronização dos cargos visuais Developers",
            )
        return existing
    return await guild.create_role(
        name=name,
        colour=colour,
        permissions=discord.Permissions.none(),
        hoist=False,
        mentionable=False,
        reason="Cargos visuais do time Developers",
    )


async def clean_tickets(guild: discord.Guild, database: PeaceDatabase) -> None:
    categories = [
        guild.get_channel(OPEN_TICKET_CATEGORY_ID),
        guild.get_channel(CLOSED_TICKET_CATEGORY_ID),
        guild.get_channel(ATENDIMENTO_CATEGORY_ID),
    ]
    channels: list[discord.TextChannel] = []
    for category in categories:
        if isinstance(category, discord.CategoryChannel):
            channels.extend(
                channel for channel in category.text_channels
                if channel.name.startswith("sup-")
            )
    for channel in channels:
        log.info("Apagando ticket %s (%s)", channel.name, channel.id)
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
    log.info("Histórico limpo do canal %s (%s mensagens)", channel.name, len(messages))


async def remove_deprecated_roles(guild: discord.Guild) -> None:
    for role_id in DEPRECATED_ROLE_IDS:
        role = guild.get_role(role_id)
        if role is None:
            continue
        try:
            await role.delete(reason="Remoção de cargos legados solicitada pela Peace")
            log.info("Cargo legado removido: %s (%s)", role.name, role.id)
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Não consegui remover o cargo legado %s (%s)", role.name, role.id)


async def repair_open_ticket_access(
    guild: discord.Guild,
    database: PeaceDatabase,
    staff: discord.Role | None,
    manager: discord.Role | None,
    recruiter: discord.Role | None,
) -> None:
    """Garante tickets abertos para Staff Peace, sem herança de Gerência/Recrutador."""
    channel_ids = {int(row["channel_id"]) for row in database.open_tickets()}
    for category_id in (OPEN_TICKET_CATEGORY_ID, ATENDIMENTO_CATEGORY_ID):
        category = guild.get_channel(category_id)
        if isinstance(category, discord.CategoryChannel):
            channel_ids.update(channel.id for channel in category.text_channels if channel.name.startswith("sup-"))
    for channel_id in channel_ids:
        channel = guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            continue
        for role in (manager, recruiter):
            if role is not None:
                await channel.set_permissions(
                    role,
                    overwrite=perms(view_channel=False, read_message_history=False, send_messages=False),
                    reason="Tickets abertos restritos à Staff Peace",
                )
        if staff is not None:
            await set_role_access(channel, staff, view=True, send=True, manage_messages=True)
        if guild.me is not None:
            await set_role_access(channel, guild.me, view=True, send=True, manage_messages=True)


async def remove_action_category(guild: discord.Guild) -> None:
    category = guild.get_channel(ACTION_CATEGORY_ID)
    if not isinstance(category, discord.CategoryChannel):
        return
    for channel in list(category.channels):
        await channel.delete(reason="Remoção da categoria AÇÃO solicitada pela Peace")
    await category.delete(reason="Remoção da categoria AÇÃO solicitada pela Peace")


async def apply_structure(
    guild: discord.Guild,
    database: PeaceDatabase,
    central_access_role_id: int | None = None,
) -> None:
    await remove_deprecated_roles(guild)
    roles = {
        key: role_by_id_or_name(guild, value)
        for key, value in ROLE_IDS.items()
    }
    peace = roles["peace"]
    staff = roles["staff"]
    manager = roles["manager"]
    recruiter = roles["recruiter"]
    visitor = roles["visitor"]
    elite = roles["elite"]
    founder = roles["founder"]
    legacy_dev = role_by_id_or_name(guild, central_access_role_id)
    legacy_florenza = roles["florenza_legacy"]

    if manager is not None and manager.permissions != discord.Permissions.none():
        await manager.edit(
            permissions=discord.Permissions.none(),
            reason="Gerência não deve possuir permissões administrativas globais",
        )

    if legacy_dev is not None and legacy_dev.name.casefold() != "dev":
        await legacy_dev.edit(
            name="Dev",
            permissions=discord.Permissions.none(),
            colour=discord.Colour.dark_blue(),
            hoist=True,
            reason="Separação entre acesso técnico e cargo visual Developer",
        )
    technical = legacy_dev
    visual_base = await ensure_visual_role(
        guild,
        "Developer",
        discord.Colour.blurple(),
        aliases=("Desenvolvedor Peace", "Developer Peace"),
    )
    await ensure_visual_role(guild, "Frontend", discord.Colour.teal(), aliases=("Frontend Peace",))
    await ensure_visual_role(guild, "Backend", discord.Colour.dark_teal(), aliases=("Backend Peace",))
    await ensure_visual_role(guild, "Documentation", discord.Colour.gold(), aliases=("Documentação Peace", "Documentation Peace"))
    ai_role = await ensure_visual_role(guild, "AI & Bots", discord.Colour.purple(), aliases=("IA & Bots Peace",))

    try:
        members = [member async for member in guild.fetch_members(limit=None)]
    except (discord.Forbidden, discord.HTTPException):
        members = list(guild.members)
    if guild.me is not None and ai_role not in guild.me.roles:
        try:
            await guild.me.add_roles(ai_role, reason="Cargo visual exclusivo do bot com IA da Peace")
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não consegui aplicar o cargo AI & Bots ao bot da Peace")
    if technical is not None and legacy_florenza is not None:
        for member in members:
            if legacy_florenza in member.roles and technical not in member.roles:
                try:
                    await member.add_roles(technical, reason="Migração do acesso Florenza para Desenvolvimento Peace")
                except (discord.Forbidden, discord.HTTPException):
                    log.info("Não consegui migrar o acesso dev de %s", member.id)

    registros = guild.get_channel(REGISTROS_CATEGORY_ID)
    if not isinstance(registros, discord.CategoryChannel):
        registros = None
    staff_category = discord.utils.find(
        lambda item: isinstance(item, discord.CategoryChannel) and item.name.casefold() == "[🛡️] staff".casefold(),
        guild.categories,
    )
    if staff_category is None:
        staff_category = await guild.create_category(
            name="[🛡️] STAFF",
            reason="Categoria interna de staff da Peace",
        )
    await staff_category.set_permissions(guild.default_role, overwrite=perms(view_channel=False), reason="Área interna da staff")
    staff_category_roles = (staff,)
    await clear_role_overwrites(staff_category, guild, list(staff_category_roles))
    for role in staff_category_roles:
        await set_role_access(staff_category, role, view=True, send=True)
    if guild.me is not None:
        await set_role_access(staff_category, guild.me, view=True, send=True, manage_messages=True)

    for key in ("staff_only", "scan_only", "logs"):
        channel = guild.get_channel(CHANNEL_IDS[key])
        if isinstance(channel, discord.TextChannel):
            desired_name = {
                "staff_only": "staff-only",
                "scan_only": "scan-only",
                "logs": "logs",
            }[key]
            await channel.edit(name=desired_name, category=staff_category, reason="Organização da área interna da staff")
            channel_roles = (recruiter,) if key == "scan_only" else (staff,)
            await configure_text(
                channel,
                guild,
                allowed=list(channel_roles),
                send=key != "logs",
            )
            if key == "scan_only":
                # The STAFF category grants Staff Peace by inheritance, but
                # scan-only is recruiter-only; keep an explicit deny here.
                await channel.set_permissions(
                    staff,
                    overwrite=perms(view_channel=False, read_message_history=False, send_messages=False),
                    reason="scan-only exclusivo para recrutadores",
                )
                for legacy_role in (manager, founder):
                    if legacy_role is not None:
                        await channel.set_permissions(
                            legacy_role,
                            overwrite=None,
                            reason="Remoção de acesso legado do scan-only",
                        )
            if guild.me is not None:
                await set_role_access(channel, guild.me, view=True, send=True, manage_messages=True)

    staff_channels = {
        key: guild.get_channel(CHANNEL_IDS[key])
        for key in ("staff_only", "scan_only", "logs")
    }
    scan_only = staff_channels.get("scan_only")
    staff_only = staff_channels.get("staff_only")
    logs_channel = staff_channels.get("logs")
    # The category assignment above keeps scan-only at the first available
    # child position. Do not issue a global position=0 edit here: Discord may
    # detach the channel from STAFF when moving it across the guild tree.
    if isinstance(staff_only, discord.TextChannel):
        await staff_only.edit(position=1, reason="Ordenação da área interna da staff")
    if isinstance(logs_channel, discord.TextChannel):
        await logs_channel.edit(position=2, reason="logs no final da área interna da staff")

    closed_category = guild.get_channel(CLOSED_TICKET_CATEGORY_ID)
    if isinstance(closed_category, discord.CategoryChannel):
        category_positions = [category.position for category in guild.categories]
        await closed_category.edit(
            position=max(category_positions, default=closed_category.position) + 1,
            reason="TICKETS-FECHADOS deve permanecer como última categoria",
        )

    development = guild.get_channel(DEVELOPMENT_CATEGORY_ID)
    if isinstance(development, discord.CategoryChannel):
        await development.edit(name="[💻] DEVELOPERS", reason="Padronização da área técnica em inglês")
        await development.set_permissions(guild.default_role, overwrite=perms(view_channel=False), reason="Área privada do desenvolvimento Peace")
        development_roles = (technical, staff)
        await clear_role_overwrites(development, guild, list(development_roles))
        for role in development_roles:
            await set_role_access(development, role, view=True, send=True, connect=True, speak=True)
        if legacy_florenza is not None:
            await development.set_permissions(legacy_florenza, overwrite=None, reason="Remoção do acesso Florenza legado")
        dev_chat = guild.get_channel(CHANNEL_IDS["dev_chat"])
        dev_call = guild.get_channel(CHANNEL_IDS["dev_call"])
        if isinstance(dev_chat, discord.TextChannel):
            await dev_chat.edit(name="╰💬・chat-dev", reason="Padronização do canal Developers")
            await configure_text(dev_chat, guild, allowed=list(development_roles), send=True)
            if legacy_florenza is not None:
                await dev_chat.set_permissions(legacy_florenza, overwrite=None, reason="Remoção do acesso Florenza legado")
            for legacy_role in (manager, founder):
                if legacy_role is not None:
                    await dev_chat.set_permissions(
                        legacy_role,
                        overwrite=None,
                        reason="Gerência e cargos legados sem acesso a Developers",
                    )
        if isinstance(dev_call, discord.VoiceChannel):
            await dev_call.edit(name="╭💻・programming", reason="Padronização da call Developers")
            await configure_voice(dev_call, guild, allowed=list(development_roles))
            for legacy_role in (manager, founder):
                if legacy_role is not None:
                    await dev_call.set_permissions(
                        legacy_role,
                        overwrite=None,
                        reason="Gerência e cargos legados sem acesso a Developers",
                    )
            if legacy_florenza is not None:
                await dev_call.set_permissions(legacy_florenza, overwrite=None, reason="Remoção do acesso Florenza legado")

    calls = guild.get_channel(CALLS_CATEGORY_ID)
    if isinstance(calls, discord.CategoryChannel):
        await calls.edit(name="[🎙️] CALLS", reason="Calls compartilhadas entre Peace e desenvolvimento")
        for role in (peace, technical, staff, manager, founder):
            await set_role_access(calls, role, view=True, connect=True, speak=True)
        for channel in calls.voice_channels:
            await configure_voice(channel, guild, allowed=[peace, technical, staff, manager, founder])

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

    rules = guild.get_channel(CHANNEL_IDS["rules"])
    if isinstance(rules, discord.TextChannel):
        await configure_text(rules, guild, allowed=[], public=True, send=False)

    afk = guild.get_channel(AFK_CHANNEL_ID)
    if isinstance(afk, discord.VoiceChannel):
        await afk.edit(category=None, position=1, name="AFK", reason="AFK público e visível da Peace")
        await set_default_access(afk, guild, view=True, connect=False, speak=False)
        for role in (peace, technical, staff, manager, recruiter, visitor, elite, founder):
            await set_role_access(afk, role, view=True, connect=False, speak=False)

    avisos = guild.get_channel(CHANNEL_IDS["avisos"])
    if isinstance(avisos, discord.TextChannel):
        await configure_text(avisos, guild, allowed=[peace, technical, staff, manager, founder], send=False)
    parceiros = guild.get_channel(CHANNEL_IDS["parceiros"])
    if isinstance(parceiros, discord.TextChannel):
        await configure_text(parceiros, guild, allowed=[peace, staff, manager, founder], send=True)
    for key in ("midias", "clipes"):
        channel = guild.get_channel(CHANNEL_IDS[key])
        if isinstance(channel, discord.TextChannel):
            await configure_text(channel, guild, allowed=[], public=True, send=True, visitor_denied=True)
    painel = guild.get_channel(CHANNEL_IDS["painel"])
    if isinstance(painel, discord.TextChannel):
        await configure_text(painel, guild, allowed=[], public=True, send=False, visitor_denied=True)

    chat_geral = guild.get_channel(CHANNEL_IDS["chat_geral"])
    if isinstance(chat_geral, discord.TextChannel):
        await configure_text(chat_geral, guild, allowed=[peace, staff, manager, founder], send=True)
    chat_gerencia = guild.get_channel(CHANNEL_IDS["chat_gerencia"])
    if isinstance(chat_gerencia, discord.TextChannel):
        await configure_text(chat_gerencia, guild, allowed=[staff, manager, founder], send=True)
    chat_elite = guild.get_channel(CHANNEL_IDS["chat_elite"])
    if isinstance(chat_elite, discord.TextChannel):
        await configure_text(chat_elite, guild, allowed=[elite, staff, manager, founder], send=True)
    chat_visitante = guild.get_channel(CHANNEL_IDS["chat_visitante"])
    if isinstance(chat_visitante, discord.TextChannel):
        await configure_text(chat_visitante, guild, allowed=[visitor, staff, manager, founder], send=True)
    musica = guild.get_channel(CHANNEL_IDS["musica"])
    if isinstance(musica, discord.TextChannel):
        await configure_text(musica, guild, allowed=[peace, technical, staff, manager, founder], send=True)

    ticket_panel = guild.get_channel(CHANNEL_IDS["ticket_panel"])
    if isinstance(ticket_panel, discord.TextChannel):
        await ticket_panel.edit(name="╰❗・ticket", reason="Padronização do último canal de atendimento")
        await configure_text(ticket_panel, guild, allowed=[visitor, peace, technical, staff, manager, founder], send=False, public=True)

    waiting_voice = guild.get_channel(CHANNEL_IDS["waiting_voice"])
    if isinstance(waiting_voice, discord.VoiceChannel):
        await waiting_voice.edit(name="╭📞・Aguardando", reason="Padronização do primeiro canal de atendimento")

    atendimento = guild.get_channel(1459444056064262186)
    old_open = guild.get_channel(OPEN_TICKET_CATEGORY_ID)
    if isinstance(atendimento, discord.CategoryChannel) and isinstance(old_open, discord.CategoryChannel):
        for channel in list(old_open.text_channels):
            if channel.name.startswith("sup-"):
                await channel.edit(category=atendimento, reason="Tickets abertos integrados ao atendimento")

    await repair_open_ticket_access(guild, database, staff, manager, recruiter)

    if database.path.exists():
        database.initialize()


def run_once(*, apply: bool, clean: bool, clean_dev: bool) -> None:
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
        log.info("Servidor encontrado: %s (%s)", guild.name, guild.id)
        if not apply:
            log.info("Modo simulação: nenhuma alteração foi aplicada")
            await client.close()
            return
        database = PeaceDatabase(settings.database_path)
        await apply_structure(guild, database, settings.central_access_role_id)
        if clean:
            await clean_tickets(guild, database)
            await remove_action_category(guild)
        if clean_dev:
            await clean_dev_chat(guild)
        log.info("Reorganização concluída%s", " com limpeza destrutiva" if clean else "")
        await client.close()

    client.run(settings.token)


def main() -> None:
    parser = argparse.ArgumentParser(description="Reorganiza a estrutura atual da Peace")
    parser.add_argument("--apply", action="store_true", help="aplica as alterações")
    parser.add_argument("--clean", action="store_true", help="remove tickets e a categoria AÇÃO")
    parser.add_argument("--clean-dev-chat", action="store_true", help="limpa todo o histórico do chat-dev")
    args = parser.parse_args()
    if (args.clean or args.clean_dev_chat) and not args.apply:
        parser.error("--clean e --clean-dev-chat exigem --apply")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    run_once(apply=args.apply, clean=args.clean, clean_dev=args.clean_dev_chat)


if __name__ == "__main__":
    main()
