from __future__ import annotations

import logging
import json
import re
import asyncio
import io
import secrets
import sqlite3
import struct
import time
import zlib
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import discord
from aiohttp import web
from discord import app_commands
from discord.ext import commands

if __package__ == "bot":
    from .config.settings import Settings, is_valid_central_bridge_key, parse_central_bridge_url
    from .persistence.database import PeaceDatabase
    from .core.identity import prefix_for_roles
    from .integrations.iris import Iris, IrisError, IRIS_SYSTEM, prompt_for_ticket
    from .core.context import bounded_context, concise_assistant_output, message_lines, redact, sanitize_assistant_output
    from .core.error_handling import configure_logging, exception_details
else:
    from config.settings import Settings, is_valid_central_bridge_key, parse_central_bridge_url
    from persistence.database import PeaceDatabase
    from core.identity import prefix_for_roles
    from integrations.iris import Iris, IrisError, IRIS_SYSTEM, prompt_for_ticket
    from core.context import bounded_context, concise_assistant_output, message_lines, redact, sanitize_assistant_output
    from core.error_handling import configure_logging, exception_details


log = logging.getLogger("peace")
ROOT = Path(__file__).resolve().parent.parent if __package__ == "bot" else Path(__file__).resolve().parent
CENTRAL_AUTH_DENIAL = "Não foi possível autenticar o acesso à Central."
CENTRAL_AUTH_THROTTLED = "Muitas tentativas de acesso. Aguarde alguns minutos e tente novamente."
PUBLIC_API_ORIGINS = frozenset(
    {
        "https://peacegg.com.br",
        "https://www.peacegg.com.br",
    }
)
TICKET_IDS = {
    "peace_support_poke_ticket",
    "peace_support_poke_staff",
    "peace_support_close_ticket",
    "peace_support_rename_ticket",
    "peace_support_claim_ticket",
    "peace_support_create_call",
}
TICKET_CONTROL_PREFIXES = (
    "peace_staff_ticket_",
    "peace_ticket_owner_",
)
AUTOMOD_ASSET = "automod.png"
WELCOME_ASSET = "welcome.png"
WELCOME_LEGACY_ASSET = "welcome-halloween.png"
SET_PANEL_ASSET = "set.png"
TICKET_PANEL_ASSET = "support.png"
OPERATIONS_PANEL_ASSET = "ops.png"
VERIFICATION_CATEGORY_NAME = "[🔐] VERIFICATION"
VERIFICATION_CHANNEL_NAME = "verify"
VERIFICATION_PANEL_MARKER = "verification:panel"
VERIFICATION_ASSET = "verification.png"
VERIFICATION_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
NOT_VERIFIED_ROLE_NAME = "Not Verified"
INTERN_ROLE_NAME = "Intern"
FOUNDER_ROLE_NAMES = ("Founder Peace", "Founder")
MANAGEMENT_ROLE_NAMES = ("Management", "Gerência", "Gerencia")
ANNOUNCEMENT_CHANNEL_NAMES = ("announcements", "avisos")
MAX_ANNOUNCEMENT_ATTACHMENTS = 10
MAX_ANNOUNCEMENT_ATTACHMENT_BYTES = 25 * 1024 * 1024
CAPTCHA_FONT = {
    "A": ("01110", "10001", "10001", "11111", "10001", "10001", "10001"),
    "B": ("11110", "10001", "10001", "11110", "10001", "10001", "11110"),
    "C": ("01111", "10000", "10000", "10000", "10000", "10000", "01111"),
    "D": ("11110", "10001", "10001", "10001", "10001", "10001", "11110"),
    "E": ("11111", "10000", "10000", "11110", "10000", "10000", "11111"),
    "F": ("11111", "10000", "10000", "11110", "10000", "10000", "10000"),
    "G": ("01111", "10000", "10000", "10111", "10001", "10001", "01111"),
    "H": ("10001", "10001", "10001", "11111", "10001", "10001", "10001"),
    "J": ("00111", "00010", "00010", "00010", "10010", "10010", "01100"),
    "K": ("10001", "10010", "10100", "11000", "10100", "10010", "10001"),
    "L": ("10000", "10000", "10000", "10000", "10000", "10000", "11111"),
    "M": ("10001", "11011", "10101", "10101", "10001", "10001", "10001"),
    "N": ("10001", "11001", "10101", "10011", "10001", "10001", "10001"),
    "P": ("11110", "10001", "10001", "11110", "10000", "10000", "10000"),
    "Q": ("01110", "10001", "10001", "10001", "10101", "10010", "01101"),
    "R": ("11110", "10001", "10001", "11110", "10100", "10010", "10001"),
    "S": ("01111", "10000", "10000", "01110", "00001", "00001", "11110"),
    "T": ("11111", "00100", "00100", "00100", "00100", "00100", "00100"),
    "U": ("10001", "10001", "10001", "10001", "10001", "10001", "01110"),
    "V": ("10001", "10001", "10001", "10001", "01010", "01010", "00100"),
    "W": ("10001", "10001", "10001", "10101", "10101", "11011", "10001"),
    "X": ("10001", "10001", "01010", "00100", "01010", "10001", "10001"),
    "Y": ("10001", "10001", "01010", "00100", "00100", "00100", "00100"),
    "Z": ("11111", "00001", "00010", "00100", "01000", "10000", "11111"),
    "2": ("01110", "10001", "00001", "00010", "00100", "01000", "11111"),
    "3": ("11110", "00001", "00001", "01110", "00001", "00001", "11110"),
    "4": ("00010", "00110", "01010", "10010", "11111", "00010", "00010"),
    "5": ("11111", "10000", "10000", "11110", "00001", "00001", "11110"),
    "6": ("01110", "10000", "10000", "11110", "10001", "10001", "01110"),
    "7": ("11111", "00001", "00010", "00100", "01000", "01000", "01000"),
    "8": ("01110", "10001", "10001", "01110", "10001", "10001", "01110"),
    "9": ("01110", "10001", "10001", "01111", "00001", "00001", "01110"),
}


def asset(name: str) -> discord.File:
    return discord.File(ROOT / "assets" / "bot" / name, filename=name)


def _png_chunk(chunk_type: bytes, payload: bytes) -> bytes:
    body = chunk_type + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)


def render_captcha_png(code: str) -> bytes:
    """Render a short CAPTCHA as a self-contained PNG without exposing its text."""
    width, height, scale = 300, 100, 8
    background = (247, 249, 252)
    rows = [bytearray(background * width) for _ in range(height)]

    def pixel(x: int, y: int, colour: tuple[int, int, int]) -> None:
        if 0 <= x < width and 0 <= y < height:
            offset = x * 3
            rows[y][offset : offset + 3] = bytes(colour)

    def line(x1: int, y1: int, x2: int, y2: int, colour: tuple[int, int, int]) -> None:
        dx = abs(x2 - x1)
        sx = 1 if x1 < x2 else -1
        dy = -abs(y2 - y1)
        sy = 1 if y1 < y2 else -1
        error = dx + dy
        while True:
            pixel(x1, y1, colour)
            if x1 == x2 and y1 == y2:
                return
            twice = 2 * error
            if twice >= dy:
                error += dy
                x1 += sx
            if twice <= dx:
                error += dx
                y1 += sy

    for _ in range(220):
        shade = 180 + secrets.randbelow(45)
        pixel(secrets.randbelow(width), secrets.randbelow(height), (shade, shade, shade))
    for _ in range(5):
        line(
            secrets.randbelow(width // 3),
            secrets.randbelow(height),
            width - secrets.randbelow(width // 3) - 1,
            secrets.randbelow(height),
            (165, 180, 198),
        )

    colours = ((25, 73, 110), (120, 55, 104), (37, 104, 91), (135, 73, 35))
    start_x = 18
    for index, character in enumerate(code):
        glyph = CAPTCHA_FONT.get(character, CAPTCHA_FONT["A"])
        x = start_x + index * 45 + secrets.randbelow(5)
        y = 18 + secrets.randbelow(9)
        colour = colours[index % len(colours)]
        for row_index, row in enumerate(glyph):
            for column_index, filled in enumerate(row):
                if filled == "1":
                    for dy in range(scale):
                        for dx in range(scale):
                            pixel(x + column_index * scale + dx, y + row_index * scale + dy, colour)

    border = (120, 135, 150)
    for x in range(width):
        pixel(x, 0, border)
        pixel(x, height - 1, border)
    for y in range(height):
        pixel(0, y, border)
        pixel(width - 1, y, border)
    raw = b"".join(b"\x00" + bytes(row) for row in rows)
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", header)
        + _png_chunk(b"IDAT", zlib.compress(raw, level=9))
        + _png_chunk(b"IEND", b"")
    )


def now_unix() -> int:
    return int(datetime.now(timezone.utc).timestamp())


def mention(user_id: int | str) -> str:
    return f"<@{user_id}>"


def clean_name(value: str, fallback: str = "ticket") -> str:
    value = re.sub(r"[^a-zA-Z0-9-]+", "-", value.casefold()).strip("-")
    return (value or fallback)[:70]


def duration_text(seconds: int) -> str:
    hours, remainder = divmod(max(seconds, 0), 3600)
    minutes, secs = divmod(remainder, 60)
    return f"{hours}h{minutes:02d}m{secs:02d}s"


def role_member(member: discord.Member, role_id: int | None) -> bool:
    return role_id is not None and any(role.id == role_id for role in member.roles)


def role_position_map(roles) -> dict[str, int]:
    """Return live Discord role positions for the identity policy."""
    return {
        str(role.name): int(getattr(role, "position", 0))
        for role in roles
        if getattr(role, "name", None) is not None
    }


def role_hoist_map(roles) -> dict[str, bool]:
    """Return Discord's live "display separately" flag by role name."""
    return {
        str(role.name): bool(getattr(role, "hoist", False))
        for role in roles
        if getattr(role, "name", None) is not None
    }


def role_named(guild: discord.Guild, role_id: int | None, *names: str) -> discord.Role | None:
    """Resolve configured roles while keeping local development configuration optional."""
    if role_id is not None:
        role = guild.get_role(role_id)
        if role is not None:
            return role
    normalized = {name.casefold() for name in names if name}
    if not normalized:
        return None
    return discord.utils.find(
        lambda role: role.name.casefold() in normalized,
        getattr(guild, "roles", ()),
    )


def unique_role_named(guild: discord.Guild, role_id: int | None, *names: str) -> discord.Role | None:
    """Resolve an authorization role without guessing among duplicate names."""
    if role_id is not None:
        role = guild.get_role(role_id)
        if role is not None:
            return role
    normalized = {name.casefold() for name in names if name}
    matches = [
        role
        for role in getattr(guild, "roles", ())
        if role.name.casefold() in normalized
    ]
    return matches[0] if len(matches) == 1 else None


def canonical_role_id(role_key: str) -> int | None:
    """Reuse a structural role ID instead of introducing another environment key."""
    try:
        if __package__ == "bot":
            from .operations.maintenance import ROLE_IDS
        else:
            from operations.maintenance import ROLE_IDS
        return int(ROLE_IDS[role_key])
    except (ImportError, KeyError, TypeError, ValueError):
        return None


def canonical_founder_role_id() -> int | None:
    """Reuse the structural migration's Founder role ID; do not add another env key."""
    return canonical_role_id("founder")


def canonical_management_role_id() -> int | None:
    """Reuse the structural migration's Management role ID when env is absent/stale."""
    return canonical_role_id("manager")


def role_is_manageable(role: discord.Role, bot_member: discord.Member | None) -> bool:
    is_default = getattr(role, "is_default", None)
    if (is_default() if callable(is_default) else bool(is_default)) or getattr(role, "managed", False):
        return False
    if bot_member is None:
        return False
    bot_top = getattr(bot_member, "top_role", None)
    if bot_top is None:
        return False
    try:
        return role < bot_top
    except TypeError:
        return int(getattr(role, "position", 0)) < int(getattr(bot_top, "position", 0))


def needs_visitor(
    member: discord.Member,
    peace_role_id: int | None,
    visitor_role_id: int | None = None,
) -> bool:
    """Return whether a human member needs to complete Visitor verification."""
    return (
        not member.bot
        and not role_member(member, peace_role_id)
        and (visitor_role_id is None or not role_member(member, visitor_role_id))
    )


def staff_member(member: discord.Member, settings: Settings) -> bool:
    return (
        member.id == settings.founder_user_id
        or role_member(member, settings.staff_role_id)
    )


def reviewer_member(member: discord.Member, settings: Settings) -> bool:
    """Return whether a member may review an application or return request."""
    return (
        staff_member(member, settings)
        or role_member(member, settings.manager_role_id)
    )


def configured_role_member(
    member: discord.Member,
    guild: discord.Guild,
    role_id: int | None,
    *names: str,
) -> bool:
    role = unique_role_named(guild, role_id, *names)
    return role is not None and role_member(member, role.id)


def founder_role_member(member: discord.Member, settings: Settings) -> bool:
    role_id = getattr(settings, "founder_role_id", None) or canonical_founder_role_id()
    return configured_role_member(
        member,
        member.guild,
        role_id,
        *FOUNDER_ROLE_NAMES,
    )


def management_role_member(member: discord.Member, settings: Settings) -> bool:
    role_id = canonical_management_role_id() or getattr(settings, "manager_role_id", None)
    return configured_role_member(
        member,
        member.guild,
        role_id,
        *MANAGEMENT_ROLE_NAMES,
    )


def application_path_open(path: str, settings: Settings) -> bool:
    """Keep vacancy gates explicit and testable for the three entry paths."""
    return {
        "player": bool(getattr(settings, "set_vagas_abertas", False)),
        "developer": bool(getattr(settings, "developer_vagas_abertas", False)),
        "staff": bool(getattr(settings, "staff_vagas_abertas", False)),
    }.get(path, False)


def verification_eligible(
    member: discord.Member,
    peace_role_id: int | None,
    visitor_role_id: int | None,
    not_verified_role_id: int | None = None,
) -> bool:
    """Return whether this member may start the Visitor CAPTCHA."""
    return (
        needs_visitor(member, peace_role_id, visitor_role_id)
        and (
            not_verified_role_id is None
            or role_member(member, not_verified_role_id)
        )
    )


async def respond(interaction: discord.Interaction, content: str, *, ephemeral: bool = True, view: discord.ui.View | None = None) -> None:
    kwargs: dict[str, object] = {"ephemeral": ephemeral}
    if view is not None:
        kwargs["view"] = view
    if interaction.response.is_done():
        await interaction.followup.send(content, **kwargs)
    else:
        await interaction.response.send_message(content, **kwargs)


async def ignore_interaction(interaction: discord.Interaction) -> None:
    """Acknowledge an ignored slash command without exposing a denial message."""
    if interaction.response.is_done():
        return
    try:
        await interaction.response.defer(ephemeral=True)
        await interaction.delete_original_response()
    except (discord.Forbidden, discord.HTTPException, discord.NotFound):
        log.debug("Não consegui limpar a confirmação silenciosa da interação", exc_info=True)


async def dismiss_component_message(interaction: discord.Interaction) -> None:
    """Remove an ephemeral interview step after the member advances."""
    message = interaction.message
    if message is None:
        return
    try:
        await message.delete()
    except discord.HTTPException:
        try:
            await message.edit(content="", embed=None, view=None)
        except discord.HTTPException:
            log.debug("Não consegui limpar a etapa efêmera da entrevista", exc_info=True)


@dataclass
class SetDraft:
    in_game_username: str
    rg_in_game: str
    telefone_in_game: str


@dataclass
class DeveloperDraft:
    full_name: str
    nickname: str
    motivation: str
    area: str = ""


class VerificationCaptchaView(discord.ui.View):
    def __init__(self, bot: "PeaceBot", member_id: int, options: list[str]):
        super().__init__(timeout=180)
        self.bot = bot
        self.member_id = member_id
        self.add_item(VerificationCaptchaSelect(bot, member_id, options))

    async def on_timeout(self) -> None:
        self.bot.verification_challenges.pop(self.member_id, None)


class VerificationCaptchaSelect(discord.ui.Select):
    def __init__(self, bot: "PeaceBot", member_id: int, options: list[str]):
        self.bot = bot
        self.member_id = member_id
        super().__init__(
            placeholder="Selecione o CAPTCHA que eu mostrei",
            custom_id="peace_verification_captcha",
            options=[
                discord.SelectOption(label=value, value=value)
                for value in options
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        if interaction.user.id != self.member_id:
            await interaction.edit_original_response(
                content="Eu gerei este CAPTCHA para outro membro.",
                embed=None,
                attachments=[],
                view=None,
            )
            return
        challenge = self.bot.verification_challenges.get(self.member_id)
        selected = self.values[0]
        if challenge is None or challenge[1] <= time.monotonic():
            self.bot.verification_challenges.pop(self.member_id, None)
            await interaction.edit_original_response(
                content="Eu encerrei este CAPTCHA por tempo limite. Volte ao canal #verify e inicie uma nova verificação.",
                embed=None,
                attachments=[],
                view=VerificationStartView(self.bot),
            )
            return
        answer, _ = challenge
        if selected != answer:
            self.bot.verification_challenges.pop(self.member_id, None)
            await interaction.edit_original_response(
                content="Código incorreto. O cargo Visitor não foi liberado. Clique em **Iniciar verificação** para tentar novamente.",
                embed=None,
                attachments=[],
                view=VerificationStartView(self.bot),
            )
            return

        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        visitor = (
            role_named(
                interaction.guild,
                getattr(self.bot.settings, "visitor_role_id", None),
                "Visitor",
            )
            if interaction.guild
            else None
        )
        not_verified = (
            role_named(
                interaction.guild,
                getattr(self.bot.settings, "not_verified_role_id", None),
                NOT_VERIFIED_ROLE_NAME,
                "Não verificado",
                "Nao verificado",
            )
            if interaction.guild
            else None
        )
        self.bot.verification_challenges.pop(self.member_id, None)
        if member is None or member.bot or visitor is None:
            await interaction.edit_original_response(
                content="Eu não consegui liberar o cargo Visitor. Procure a staff.",
                embed=None,
                attachments=[],
                view=None,
            )
            return
        if role_member(member, self.bot.settings.peace_role_id):
            await interaction.edit_original_response(
                content="Eu confirmei sua conta, mas não apliquei Visitor porque você já possui o cargo Peace.",
                embed=None,
                attachments=[],
                view=None,
            )
            return
        if visitor in member.roles:
            if not_verified is not None and not_verified in member.roles:
                try:
                    await member.remove_roles(not_verified, reason="Visitor já verificado pelo CAPTCHA")
                except (discord.Forbidden, discord.HTTPException):
                    await interaction.edit_original_response(
                        content="Eu confirmei sua conta, mas não consegui remover o cargo Not Verified. A staff precisa corrigir isso.",
                        embed=None,
                        attachments=[],
                        view=None,
                    )
                    return
            await interaction.edit_original_response(
                content="Eu já confirmei sua conta e o cargo Visitor já está liberado.",
                embed=None,
                attachments=[],
                view=None,
            )
            return
        bot_member = getattr(interaction.guild, "me", None)
        if (
            bot_member is None
            or visitor.managed
            or visitor >= bot_member.top_role
            or (
                not_verified is not None
                and (not_verified.managed or not_verified >= bot_member.top_role)
            )
        ):
            await interaction.edit_original_response(
                content="Eu confirmei sua conta, mas minha hierarquia não permite aplicar Visitor. A staff precisa corrigir isso.",
                embed=None,
                attachments=[],
                view=None,
            )
            return
        added_visitor = False
        try:
            await member.add_roles(visitor, reason="CAPTCHA de verificação concluído")
            added_visitor = True
            if not_verified is not None and not_verified in member.roles:
                await member.remove_roles(not_verified, reason="CAPTCHA de verificação concluído")
        except (discord.Forbidden, discord.HTTPException):
            if added_visitor:
                try:
                    await member.remove_roles(visitor, reason="Rollback de verificação incompleta")
                except (discord.Forbidden, discord.HTTPException):
                    log.exception("Falha ao reverter Visitor após falha na remoção de Not Verified")
            log.exception("Falha ao aplicar Visitor após verificação para %s", member.id)
            await interaction.edit_original_response(
                content="Não consegui concluir a verificação. Nenhum acesso foi liberado; clique em **Iniciar verificação** para tentar novamente.",
                embed=None,
                attachments=[],
                view=VerificationStartView(self.bot),
            )
            return
        await interaction.edit_original_response(
            content="Eu confirmei que você não é um bot e liberei o cargo Visitor. Agora você pode acessar as áreas de visitante.",
            embed=None,
            attachments=[],
            view=None,
        )


class VerificationStartView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(
        label="Iniciar verificação",
        style=discord.ButtonStyle.secondary,
        custom_id="peace_verification_start",
    )
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.defer(ephemeral=True)
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None or member.bot:
            await interaction.edit_original_response(
                content="Eu não libero o cargo Visitor para contas de bot.",
                view=None,
            )
            return
        visitor = role_named(
            member.guild,
            getattr(self.bot.settings, "visitor_role_id", None),
            "Visitor",
        )
        if visitor is not None and visitor in member.roles:
            await interaction.edit_original_response(
                content="Eu já confirmei sua conta e o cargo Visitor já está liberado.",
                view=None,
            )
            return
        if role_member(member, self.bot.settings.peace_role_id):
            await interaction.edit_original_response(
                content="Eu não preciso verificar novamente uma conta que já possui o cargo Peace.",
                view=None,
            )
            return
        if not verification_eligible(
            member,
            self.bot.settings.peace_role_id,
            self.bot.settings.visitor_role_id,
            self.bot.settings.not_verified_role_id,
        ):
            await interaction.edit_original_response(
                content="Você precisa do cargo **Not Verified** para iniciar.",
                view=None,
            )
            return
        options = self.bot.create_verification_challenge(member.id)
        answer = self.bot.verification_challenges[member.id][0]
        image_file = discord.File(io.BytesIO(render_captcha_png(answer)), filename="captcha.png")
        embed = discord.Embed(
            title="CAPTCHA de verificação",
            description="Leia o código na imagem e selecione a opção correspondente no menu abaixo.",
            color=0x5865F2,
        )
        embed.set_image(url="attachment://captcha.png")
        embed.set_footer(text="Esta tentativa expira em 3 minutos.")
        await interaction.edit_original_response(
            content="Selecione no menu o código mostrado na imagem.",
            embed=embed,
            attachments=[image_file],
            view=VerificationCaptchaView(self.bot, member.id, options),
        )


class SetModal(discord.ui.Modal, title="Pedir set · entrevista inicial"):
    in_game_username = discord.ui.TextInput(
        label="Apelido in-game",
        placeholder="Uma palavra, de 3 a 20 caracteres",
        min_length=3,
        max_length=20,
        required=True,
    )
    rg_in_game = discord.ui.TextInput(
        label="RG in-game",
        placeholder="Informe o RG usado na cidade",
        max_length=4000,
        required=True,
    )
    telefone_in_game = discord.ui.TextInput(
        label="Telefone in-game",
        placeholder="Informe o telefone usado na cidade",
        max_length=100,
        required=True,
    )

    def __init__(self, bot: "PeaceBot"):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        username = str(self.in_game_username.value).strip()
        if not re.fullmatch(r"[^\s]+", username):
            await respond(interaction, "O apelido precisa ter uma única palavra.")
            return
        settings = self.bot.settings
        if not settings.username_min_length <= len(username) <= settings.username_max_length:
            await respond(
                interaction,
                f"O apelido precisa ter entre {settings.username_min_length} e "
                f"{settings.username_max_length} caracteres.",
            )
            return
        self.bot.drafts[interaction.user.id] = SetDraft(
            in_game_username=username,
            rg_in_game=str(self.rg_in_game.value).strip(),
            telefone_in_game=str(self.telefone_in_game.value).strip(),
        )
        await interaction.response.send_message(
            "Entrevista inicial registrada. Agora selecione onde conheceu a Peace:",
            view=SourceView(self.bot),
            ephemeral=True,
        )


class SetView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="◈ Iniciar entrevista", style=discord.ButtonStyle.secondary, custom_id="peace_pedir_set_open")
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is not None:
            reservation = self.bot.database.reserved_peace_id_for_user(member.id)
            if reservation is not None:
                await self.bot.ensure_return_request(member)
                await respond(
                    interaction,
                    "Seu ID Peace continua reservado. Eu encaminhei seu retorno diretamente ao **scan-only** para aprovação; não é necessário refazer a entrevista.",
                )
                return
            if role_member(member, self.bot.settings.peace_role_id):
                await respond(interaction, "Você já possui o cargo Peace e não precisa solicitar um novo set.")
                return
            if not application_path_open("player", self.bot.settings):
                await respond(interaction, "Eu mantive as vagas de Player fechadas no momento.")
                return
        elif not application_path_open("player", self.bot.settings):
            await respond(interaction, "Eu mantive as vagas de Player fechadas no momento.")
            return
        await interaction.response.send_modal(SetModal(self.bot))


class EntryTypeSelect(discord.ui.Select):
    def __init__(self, bot: "PeaceBot"):
        self.bot = bot
        super().__init__(
            placeholder="Escolha o caminho da entrevista",
            custom_id="peace_entry_type",
            options=[
                discord.SelectOption(
                    label="Player set · vagas abertas",
                    value="player",
                    description="Player applications are open",
                ),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is not None and role_member(member, self.bot.settings.peace_role_id):
            await respond(interaction, "Você já possui o cargo Peace e não precisa solicitar um novo set.")
            return
        if not application_path_open("player", self.bot.settings):
            await respond(interaction, "Eu mantive as vagas de Player fechadas no momento.")
            return
        await interaction.response.send_modal(SetModal(self.bot))
        await dismiss_component_message(interaction)


class EntryTypeView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=300)
        self.add_item(EntryTypeSelect(bot))


class DeveloperIdentityModal(discord.ui.Modal, title="Entrevista dev · etapa 1"):
    full_name = discord.ui.TextInput(
        label="Nome e sobrenome reais",
        placeholder="Usado apenas na análise interna da Peace",
        min_length=5,
        max_length=100,
        required=True,
    )
    nickname = discord.ui.TextInput(
        label="Apelido que você usa na Peace",
        placeholder="Seu nome de uso no servidor",
        min_length=3,
        max_length=32,
        required=True,
    )
    motivation = discord.ui.TextInput(
        label="Por que quer integrar o time?",
        placeholder="Responda com pelo menos 30 caracteres",
        min_length=30,
        max_length=1200,
        style=discord.TextStyle.paragraph,
        required=True,
    )

    def __init__(self, bot: "PeaceBot"):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        self.bot.developer_drafts[interaction.user.id] = DeveloperDraft(
            full_name=str(self.full_name.value).strip(),
            nickname=str(self.nickname.value).strip(),
            motivation=str(self.motivation.value).strip(),
        )
        await interaction.response.send_message(
            "Etapa inicial registrada. Agora escolha a área principal em que pretende atuar.",
            view=DeveloperAreaView(self.bot),
            ephemeral=True,
        )


class DeveloperAreaSelect(discord.ui.Select):
    def __init__(self, bot: "PeaceBot"):
        self.bot = bot
        super().__init__(
            placeholder="Escolha sua área principal",
            custom_id="peace_developer_area",
            options=[
                discord.SelectOption(label="Frontend", value="Frontend"),
                discord.SelectOption(label="Backend", value="Backend"),
                discord.SelectOption(label="Documentation", value="Documentation"),
                discord.SelectOption(label="AIs", value="AIs"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        draft = self.bot.developer_drafts.get(interaction.user.id)
        if draft is None:
            await respond(interaction, "Sua entrevista expirou; inicie novamente pelo painel.")
            return
        draft.area = self.values[0]
        await interaction.response.send_modal(DeveloperExperienceModal(self.bot))
        await dismiss_component_message(interaction)


class DeveloperAreaView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=300)
        self.add_item(DeveloperAreaSelect(bot))


class DeveloperExperienceModal(discord.ui.Modal, title="Entrevista dev · etapa 2"):
    specialization_time = discord.ui.TextInput(
        label="Há quanto tempo se especializa?",
        placeholder="Ex.: 2 anos com backend Python",
        min_length=3,
        max_length=160,
        required=True,
    )
    previous_experience = discord.ui.TextInput(
        label="Onde já atuou ou praticou?",
        placeholder="Projetos, empresas, estudos ou comunidades — mínimo de 30 caracteres",
        min_length=30,
        max_length=1400,
        style=discord.TextStyle.paragraph,
        required=True,
    )
    portfolio = discord.ui.TextInput(
        label="Portfólio, GitHub ou referência",
        placeholder="Opcional, mas recomendado",
        max_length=300,
        required=False,
    )

    def __init__(self, bot: "PeaceBot"):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        draft = self.bot.developer_drafts.pop(interaction.user.id, None)
        if draft is None or not draft.area:
            await respond(interaction, "Sua entrevista expirou; inicie novamente pelo painel.")
            return
        if self.bot.database.pending_developer_request_for_user(interaction.user.id) is not None:
            await respond(interaction, "Você já possui uma candidatura Dev em análise ou integração.")
            return
        request_id = self.bot.database.save_developer_request(
            discord_user_id=interaction.user.id,
            full_name=draft.full_name,
            nickname=draft.nickname,
            motivation=draft.motivation,
            area=draft.area,
            specialization_time=str(self.specialization_time.value).strip(),
            previous_experience=str(self.previous_experience.value).strip(),
            portfolio=str(self.portfolio.value).strip(),
            status="pending",
        )
        request = self.bot.database.developer_request(request_id)
        if request is None:
            await respond(interaction, "Não consegui registrar sua entrevista; tente novamente.")
            return
        await self.bot.send_to_channel(
            self.bot.settings.scan_channel_id,
            embed=self.bot.developer_request_embed(request),
            view=self.bot.developer_approval_view(request_id),
        )
        await respond(
            interaction,
            "Currículo enviado ao scan-only. A entrevista manual será feita na call de suporte; depois da avaliação, a equipe avisará se você foi aprovado para entrar no time.",
        )


class DeveloperApprovalView(discord.ui.View):
    def __init__(self, bot: "PeaceBot", request_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.request_id = request_id
        request = bot.database.developer_request(request_id)
        self.phase = "interview" if request is None or request["status"] == "pending" else "member"
        approve = discord.ui.Button(
            label=(
                "✓ Aprovar entrevista"
                if self.phase == "interview"
                else "✓ Aprovar como integrante"
            ),
            style=discord.ButtonStyle.secondary,
            custom_id=f"peace_dev_approve_{request_id}",
        )
        reject = discord.ui.Button(
            label="× Recusar candidatura",
            style=discord.ButtonStyle.secondary,
            custom_id=f"peace_dev_reject_{request_id}",
        )
        approve.callback = self.approve
        reject.callback = self.reject
        self.add_item(approve)
        self.add_item(reject)

    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True

    async def guard(self, interaction: discord.Interaction):
        request = self.bot.database.developer_request(self.request_id)
        if request is None or request["status"] not in {"pending", "interview_scheduled"}:
            await respond(interaction, "Esta candidatura já foi processada.")
            return None
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        allowed = member is not None and reviewer_member(member, self.bot.settings)
        if not allowed:
            await respond(interaction, "Somente Staff ou Management autorizado pode analisar candidaturas Dev.")
            return None
        return request

    async def approve(self, interaction: discord.Interaction) -> None:
        request = await self.guard(interaction)
        if request is None:
            return
        await interaction.response.defer()
        if request["status"] == "pending":
            self.bot.database.update_developer_request(self.request_id, status="interview_scheduled")
            sent = await self.bot.send_developer_interview_notice(request)
            updated = self.bot.database.developer_request(self.request_id) or request
            next_view = DeveloperApprovalView(self.bot, self.request_id)
            self.bot.developer_approval_views[self.request_id] = next_view
            if interaction.message is not None:
                text = (
                    "✅ Entrevista aprovada. O candidato foi avisado para fazer a entrevista manual na call de suporte. "
                    "Após a call, use **Aprovar como integrante**."
                    if sent else
                    "✅ Entrevista aprovada, mas o PV está fechado. Faça a entrevista manual na call de suporte e depois use **Aprovar como integrante**."
                )
                await interaction.message.edit(
                    content=text,
                    embed=self.bot.developer_request_embed(updated),
                    view=next_view,
                )
            return
        guild = interaction.guild or self.bot.guild
        member = await self.bot.member(guild, int(request["discord_user_id"])) if guild else None
        central_access_role_id = self.bot.settings.central_access_role_id
        developer_role = (
            guild.get_role(central_access_role_id)
            if guild is not None and central_access_role_id is not None
            else None
        )
        if member is None or developer_role is None:
            if interaction.message is not None:
                await interaction.message.edit(
                    content="⚠️ Não foi possível aprovar: o candidato ou o cargo Dev não foi encontrado. Nenhuma alteração foi aplicada.",
                    embed=self.bot.developer_request_embed(request),
                    view=self,
                )
            return
        try:
            if developer_role not in member.roles:
                await member.add_roles(
                    developer_role,
                    reason=f"Candidatura Dev aprovada por Staff ou Management {interaction.user.id}",
                )
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao aplicar o cargo Dev ao candidato %s", member.id)
            if interaction.message is not None:
                await interaction.message.edit(
                    content="⚠️ Não foi possível aplicar o cargo Dev. Verifique a hierarquia e as permissões do bot; a candidatura continua pendente.",
                    embed=self.bot.developer_request_embed(request),
                    view=self,
                )
            return
        member_roles = {role.id: role.name for role in member.roles}
        member_roles[developer_role.id] = developer_role.name
        member_role_objects = list(member.roles)
        if developer_role not in member_role_objects:
            member_role_objects.append(developer_role)
        peace_id = self.bot.database.ensure_runtime_member(
            discord_user_id=member.id,
            username=member.name,
            nickname=member.nick,
            role_ids=list(member_roles),
            role_names=list(member_roles.values()),
            founder_id=self.bot.settings.founder_user_id,
            role_positions=role_position_map(member_role_objects),
            role_hoist=role_hoist_map(member_role_objects),
        )
        self.bot.database.update_developer_request(self.request_id, status="approved")
        sent = await self.bot.send_developer_decision_notice(request, peace_id=peace_id)
        self.disable_all()
        if interaction.message is not None:
            text = (
                "✅ Candidato aprovado como integrante. Cargo Dev aplicado e DM de aceite enviada."
                if sent else
                "✅ Candidato aprovado como integrante e cargo Dev aplicado, mas o PV está fechado."
            )
            await interaction.message.edit(content=text, embed=None, view=self)

    async def reject(self, interaction: discord.Interaction) -> None:
        request = await self.guard(interaction)
        if request is None:
            return
        await interaction.response.defer()
        after_interview = request["status"] == "interview_scheduled"
        self.bot.database.update_developer_request(self.request_id, status="rejected")
        member = await self.bot.member(interaction.guild, int(request["discord_user_id"])) if interaction.guild else None
        sent = False
        if member is not None:
            sent = await self.bot.send_developer_rejection_notice(request, after_interview=after_interview)
        self.disable_all()
        if interaction.message is not None:
            text = (
                f"× {'Candidatura' if after_interview else 'Entrevista'} recusada por {interaction.user.mention}. O candidato foi avisado por DM."
                if sent else
                f"× {'Candidatura' if after_interview else 'Entrevista'} recusada por {interaction.user.mention}. O PV do candidato está fechado."
            )
            await interaction.message.edit(content=text, embed=None, view=self)


class SourceSelect(discord.ui.Select):
    def __init__(self, bot: "PeaceBot"):
        self.bot = bot
        super().__init__(
            placeholder="Selecione uma opção",
            custom_id="peace_set_source",
            options=[
                discord.SelectOption(label="Fui recrutado", value="recrutado"),
                discord.SelectOption(label="Streamer", value="streamer"),
                discord.SelectOption(label="Clipes", value="clipes"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        draft = self.bot.drafts.get(interaction.user.id)
        if draft is None:
            await respond(interaction, "Sua entrevista expirou; inicie novamente.")
            return
        if self.values[0] == "recrutado":
            recruiters = await self.bot.recruiter_members()
            await interaction.response.defer(ephemeral=True)
            await dismiss_component_message(interaction)
            await interaction.followup.send(
                "Selecione quem fez o recrutamento:",
                view=RecruiterView(self.bot, draft, recruiters),
                ephemeral=True,
            )
            return
        await interaction.response.defer(ephemeral=True)
        await dismiss_component_message(interaction)
        await self.bot.finish_set(interaction, draft, self.values[0], None)


class SourceView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=300)
        self.add_item(SourceSelect(bot))


class RecruiterSelect(discord.ui.Select):
    def __init__(self, bot: "PeaceBot", draft: SetDraft, recruiters: list[discord.Member]):
        self.bot = bot
        self.draft = draft
        options = [
            discord.SelectOption(
                label=(member.display_name or member.name)[:100],
                value=str(member.id),
                description=f"@{member.name}"[:100],
            )
            for member in recruiters[:25]
        ]
        super().__init__(placeholder="Quem fez seu recrutamento?", options=options, custom_id="peace_set_recruiter")

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await dismiss_component_message(interaction)
        await self.bot.finish_set(interaction, self.draft, "recrutado", int(self.values[0]))


class RecruiterView(discord.ui.View):
    def __init__(self, bot: "PeaceBot", draft: SetDraft, recruiters: list[discord.Member] | None = None):
        super().__init__(timeout=300)
        if recruiters:
            self.add_item(RecruiterSelect(bot, draft, recruiters))
        else:
            unavailable = discord.ui.Button(
                label="Nenhum reviewer disponível agora",
                style=discord.ButtonStyle.secondary,
                disabled=True,
            )
            self.add_item(unavailable)


class SetApprovalView(discord.ui.View):
    def __init__(self, bot: "PeaceBot", request_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.request_id = request_id
        approve = discord.ui.Button(
            label="✓ Aprovar set",
            style=discord.ButtonStyle.secondary,
            custom_id=f"peace_set_approve_{request_id}",
        )
        reject = discord.ui.Button(
            label="× Recusar",
            style=discord.ButtonStyle.secondary,
            custom_id=f"peace_set_reject_{request_id}",
        )
        approve.callback = self.approve
        reject.callback = self.reject
        self.add_item(approve)
        self.add_item(reject)

    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True

    async def guard(self, interaction: discord.Interaction):
        request = self.bot.database.set_request(self.request_id)
        if request is None or request["status"] != "pending":
            await respond(interaction, "Este pedido já foi processado.")
            return None
        if not isinstance(interaction.user, discord.Member) or not self.bot.can_approve_set_request(request, interaction.user):
            await respond(interaction, "Somente Staff ou Management autorizado pode aprovar este pedido.")
            return None
        return request

    async def approve(self, interaction: discord.Interaction) -> None:
        request = await self.guard(interaction)
        if request is None:
            return
        await interaction.response.defer()
        result = await self.bot.approve_set_request(request, interaction.user)
        self.disable_all()
        if interaction.message is not None:
            await interaction.message.edit(content=f"✅ {result}", embed=None, view=self)

    async def reject(self, interaction: discord.Interaction) -> None:
        request = await self.guard(interaction)
        if request is None:
            return
        await interaction.response.defer()
        await self.bot.reject_set_request(request, interaction.user)
        self.disable_all()
        if interaction.message is not None:
            await interaction.message.edit(
                content=f"× Pedido de set recusado por {interaction.user.mention}.",
                embed=None,
                view=self,
                allowed_mentions=discord.AllowedMentions(users=True),
            )


class ReturnApprovalView(discord.ui.View):
    def __init__(self, bot: "PeaceBot", request_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.request_id = request_id
        self.processing = False
        release = discord.ui.Button(
            label="Liberar ID",
            style=discord.ButtonStyle.secondary,
            custom_id=f"peace_return_release_{request_id}",
        )
        release.callback = self.release_id
        self.add_item(release)
        reject = discord.ui.Button(
            label="Recusar retorno",
            style=discord.ButtonStyle.secondary,
            custom_id=f"peace_return_reject_{request_id}",
        )
        reject.callback = self.reject_return
        self.add_item(reject)

    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True

    def enable_all(self) -> None:
        for item in self.children:
            item.disabled = False

    async def edit_source(self, interaction: discord.Interaction, **kwargs) -> None:
        if interaction.response.is_done():
            if interaction.message is not None:
                await interaction.message.edit(**kwargs)
            else:
                await interaction.edit_original_response(**kwargs)
            return
        await interaction.response.edit_message(**kwargs)

    async def release_id(self, interaction: discord.Interaction) -> None:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None or not reviewer_member(member, self.bot.settings):
            await respond(interaction, "Somente Staff ou Management autorizado pode liberar este retorno.")
            return
        if self.processing:
            await interaction.response.defer()
            return
        self.processing = True
        self.disable_all()
        try:
            async with self.bot.return_mutation_lock(self.request_id):
                request = self.bot.database.return_request(self.request_id)
                if request is None or request["status"] != "pending":
                    await self.edit_source(interaction, content="Este retorno já foi processado.", embed=None, view=None)
                    return
                target = await self.bot.member(interaction.guild, int(request["discord_user_id"])) if interaction.guild else None
                if target is None:
                    self.enable_all()
                    await self.edit_source(interaction, content="O membro não está disponível no servidor.", view=self)
                    return
                peace_role = target.guild.get_role(self.bot.settings.peace_role_id)
                if peace_role is None:
                    self.enable_all()
                    await self.edit_source(
                        interaction,
                        content="O cargo Peace não está configurado; o retorno continua pendente.",
                        view=self,
                    )
                    return
                await self.edit_source(
                    interaction,
                    content="**Retorno em andamento**\nAplicando Peace, removendo os cargos de entrada e atualizando o apelido.",
                    view=self,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                visitor_role = role_named(target.guild, getattr(self.bot.settings, "visitor_role_id", None), "Visitor")
                not_verified_role = role_named(
                    target.guild,
                    getattr(self.bot.settings, "not_verified_role_id", None),
                    NOT_VERIFIED_ROLE_NAME,
                    "Não verificado",
                    "Nao verificado",
                )
                return_roles = {
                    role.id: role.name
                    for role in target.roles
                    if role.id not in {
                        item.id
                        for item in (visitor_role, not_verified_role)
                        if item is not None
                    }
                }
                return_roles[peace_role.id] = peace_role.name
                try:
                    result = self.bot.database.approve_return_request(
                        self.request_id,
                        username=target.name,
                        nickname=target.nick,
                        role_ids=list(return_roles),
                        role_names=list(return_roles.values()),
                        founder_id=self.bot.settings.founder_user_id,
                        role_positions=role_position_map([*target.roles, peace_role]),
                        role_hoist=role_hoist_map([*target.roles, peace_role]),
                    )
                except sqlite3.Error:
                    log.exception("Falha ao registrar a aprovação do retorno Peace %s", self.request_id)
                    self.enable_all()
                    self.processing = False
                    pending = self.bot.database.return_request(self.request_id)
                    await self.edit_source(
                        interaction,
                        content="⚠️ Não consegui registrar a liberação do ID. O retorno continua pendente; tente novamente após conferir o banco.",
                        embed=self.bot.return_request_embed(pending) if pending is not None else None,
                        view=self,
                    )
                    return
                if result is None:
                    current = self.bot.database.return_request(self.request_id)
                    if current is not None and current["status"] == "pending":
                        self.enable_all()
                        self.processing = False
                        await self.edit_source(
                            interaction,
                            content="⚠️ Não consegui validar a reserva do ID. O retorno continua pendente; nada foi alterado.",
                            embed=self.bot.return_request_embed(current),
                            view=self,
                        )
                    else:
                        await self.edit_source(interaction, content="Este retorno já foi processado.", embed=None, view=None)
                    return
                _, old_id, new_id = result
                try:
                    await self.bot.apply_return_member_state(
                        target,
                        peace_role=peace_role,
                        peace_id=new_id,
                        reason=f"Retorno Peace aprovado por {member.id}",
                    )
                except (discord.Forbidden, discord.HTTPException, RuntimeError):
                    try:
                        self.bot.database.rollback_return_approval(self.request_id)
                    except sqlite3.Error:
                        log.exception("Falha ao reverter aprovação do retorno Peace %s", self.request_id)
                    log.info("Retorno Peace %s voltou a pendente após falha no Discord", self.request_id)
                    self.enable_all()
                    self.processing = False
                    pending = self.bot.database.return_request(self.request_id)
                    await self.edit_source(
                        interaction,
                        content="⚠️ Não consegui aplicar os cargos do retorno. A solicitação continua pendente e o ID permanece reservado.",
                        embed=self.bot.return_request_embed(pending) if pending is not None else None,
                        view=self,
                    )
                    return
                try:
                    await target.send(
                        f"Seu retorno à Peace foi aprovado. O ID antigo `{old_id}` foi liberado e seu novo ID é `{new_id}`."
                    )
                except (discord.Forbidden, discord.HTTPException):
                    log.info("Não consegui enviar a confirmação do retorno Peace %s", target.id)
                await self.bot.send_log(
                    "Retorno Peace aprovado",
                    actor=member,
                    fields=(
                        ("Usuário", target.mention),
                        ("ID anterior", f"`{old_id}`"),
                        ("Novo ID", f"`{new_id}`"),
                        ("Aprovado por", member.mention),
                        ("Horário", f"<t:{now_unix()}:F>"),
                    ),
                )
                await self.edit_source(
                    interaction,
                    content=f"ID liberado por {member.mention}. Antigo: `{old_id}` · novo: `{new_id}`.",
                    embed=None,
                    view=None,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
        finally:
            if self.processing:
                self.processing = False

    async def reject_return(self, interaction: discord.Interaction) -> None:
        member = interaction.user if isinstance(interaction.user, discord.Member) else None
        if member is None or not reviewer_member(member, self.bot.settings):
            await respond(interaction, "Somente Staff ou Management autorizado pode recusar este retorno.")
            return
        if self.processing:
            await interaction.response.defer()
            return
        self.processing = True
        self.disable_all()
        try:
            async with self.bot.return_mutation_lock(self.request_id):
                request = self.bot.database.return_request(self.request_id)
                if request is None or request["status"] != "pending":
                    await self.edit_source(interaction, content="Este retorno já foi processado.", embed=None, view=None)
                    return
                await self.edit_source(
                    interaction,
                    content="**Recusa em andamento**\nO retorno será recusado e o ID continuará reservado.",
                    view=self,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                try:
                    rejected = self.bot.database.reject_return_request(self.request_id)
                except sqlite3.Error:
                    log.exception("Falha ao registrar a recusa do retorno Peace %s", self.request_id)
                    self.enable_all()
                    self.processing = False
                    pending = self.bot.database.return_request(self.request_id)
                    await self.edit_source(
                        interaction,
                        content="⚠️ Não consegui registrar a recusa. O retorno continua pendente e o ID permanece reservado.",
                        embed=self.bot.return_request_embed(pending) if pending is not None else None,
                        view=self,
                    )
                    return
                if rejected is None:
                    current = self.bot.database.return_request(self.request_id)
                    if current is not None and current["status"] == "pending":
                        self.enable_all()
                        self.processing = False
                        await self.edit_source(
                            interaction,
                            content="⚠️ Não consegui validar a reserva do ID. O retorno continua pendente; nada foi alterado.",
                            embed=self.bot.return_request_embed(current),
                            view=self,
                        )
                    else:
                        await self.edit_source(interaction, content="Este retorno já foi processado.", embed=None, view=None)
                    return
                target = await self.bot.member(interaction.guild, int(request["discord_user_id"])) if interaction.guild else None
                if target is not None:
                    try:
                        await target.send(
                            "Seu retorno à Peace foi recusado. O ID anterior continua reservado e não foi liberado para outra pessoa."
                        )
                    except (discord.Forbidden, discord.HTTPException):
                        log.info("Não consegui enviar a recusa do retorno Peace %s", target.id)
                await self.bot.send_log(
                    "Retorno Peace recusado",
                    actor=member,
                    fields=(
                        ("Usuário", mention(request["discord_user_id"])),
                        ("ID reservado", f"`{int(request['old_peace_id'])}`"),
                        ("Ação", "Novo set de retorno recusado; o ID permanece reservado."),
                        ("Quem recusou", member.mention),
                        ("Horário", f"<t:{now_unix()}:F>"),
                    ),
                )
                await self.edit_source(
                    interaction,
                    content=f"Retorno recusado por {member.mention}. O ID `{int(request['old_peace_id'])}` continua reservado.",
                    embed=None,
                    view=None,
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
        finally:
            if self.processing:
                self.processing = False


class StartActionSelect(discord.ui.Select):
    def __init__(self, bot: "PeaceBot", owner_id: int, actions: tuple[str, ...]):
        self.bot = bot
        self.owner_id = owner_id
        options = []
        if "delete_user" in actions:
            options.append(
                discord.SelectOption(
                    label="Excluir usuário",
                    value="delete_user",
                    description="Remove o vínculo Peace e libera o ID com confirmação",
                )
            )
        if "announcement" in actions:
            options.append(
                discord.SelectOption(
                    label="Avisar",
                    value="announcement",
                    description="Publica um aviso com Markdown e anexos",
                )
            )
        super().__init__(
            placeholder="Escolha o que deseja fazer",
            custom_id="peace_start_action",
            options=options,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id or interaction.guild is not None:
            await respond(interaction, "Este menu só pode ser usado pelo responsável no PV do bot.")
            return
        action = self.values[0]
        if action == "delete_user":
            member = await self.bot.authorized_dm_member(self.owner_id, "founder")
            if member is None:
                await respond(interaction, "Apenas o cargo Founder pode excluir vínculos Peace.")
                return
            await interaction.response.defer()
            candidates = await self.bot.delete_peace_candidates()
            if not candidates:
                await interaction.edit_original_response(
                    content="Não encontrei membros com vínculo Peace disponível para revisão no servidor.",
                    view=None,
                )
                return
            view = DeleteUserSelectionView(self.bot, self.owner_id, candidates)
            await interaction.edit_original_response(
                content=view.prompt(),
                view=view,
            )
            return
        if action == "announcement":
            member = await self.bot.authorized_dm_member(self.owner_id, "management")
            if member is None:
                await respond(interaction, "Apenas o cargo Management pode publicar avisos.")
                return
            await self.bot.collect_announcement(interaction, member)
            return
        await respond(interaction, "Ação desconhecida. Abra o `/start` novamente.")


class StartActionView(discord.ui.View):
    def __init__(self, bot: "PeaceBot", owner_id: int, actions: tuple[str, ...]):
        super().__init__(timeout=300)
        self.add_item(StartActionSelect(bot, owner_id, actions))


class DeleteUserSelectionView(discord.ui.View):
    PAGE_SIZE = 25

    def __init__(self, bot: "PeaceBot", owner_id: int, candidates: list[discord.Member]):
        super().__init__(timeout=300)
        self.bot = bot
        self.owner_id = owner_id
        self.candidates = candidates
        self.page = 0
        self.select_item = self._build_select()
        self.add_item(self.select_item)
        self.previous_button: discord.ui.Button | None = None
        self.next_button: discord.ui.Button | None = None
        if self.total_pages > 1:
            self.previous_button = discord.ui.Button(
                label="← Anterior",
                style=discord.ButtonStyle.secondary,
                custom_id=f"peace_start_delete_prev_{owner_id}",
                row=1,
            )
            self.next_button = discord.ui.Button(
                label="Próxima →",
                style=discord.ButtonStyle.secondary,
                custom_id=f"peace_start_delete_next_{owner_id}",
                row=1,
            )
            self.previous_button.callback = self.previous_page
            self.next_button.callback = self.next_page
            self.add_item(self.previous_button)
            self.add_item(self.next_button)
            self._refresh_navigation()

    @property
    def total_pages(self) -> int:
        return max(1, (len(self.candidates) + self.PAGE_SIZE - 1) // self.PAGE_SIZE)

    def prompt(self) -> str:
        return (
            "Selecione um ou mais membros do servidor Peace para revisar. "
            "A remoção só acontece depois da confirmação final.\n\n"
            f"Página **{self.page + 1}/{self.total_pages}** · "
            f"{len(self.candidates)} membros com vínculo Peace encontrados."
        )

    def _page_candidates(self) -> list[discord.Member]:
        start = self.page * self.PAGE_SIZE
        return self.candidates[start : start + self.PAGE_SIZE]

    def _build_select(self) -> "DeleteUserSelect":
        return DeleteUserSelect(
            self.bot,
            self.owner_id,
            self._page_candidates(),
            page=self.page,
            total_pages=self.total_pages,
        )

    def _refresh_navigation(self) -> None:
        if self.previous_button is not None:
            self.previous_button.disabled = self.page == 0
        if self.next_button is not None:
            self.next_button.disabled = self.page >= self.total_pages - 1

    async def _change_page(self, interaction: discord.Interaction, delta: int) -> None:
        if interaction.user.id != self.owner_id or interaction.guild is not None:
            await respond(interaction, "Este seletor só pode ser usado pelo responsável no PV do bot.")
            return
        self.page = min(max(self.page + delta, 0), self.total_pages - 1)
        self.remove_item(self.select_item)
        self.select_item = self._build_select()
        self.add_item(self.select_item)
        self._refresh_navigation()
        await interaction.response.edit_message(content=self.prompt(), view=self)

    async def previous_page(self, interaction: discord.Interaction) -> None:
        await self._change_page(interaction, -1)

    async def next_page(self, interaction: discord.Interaction) -> None:
        await self._change_page(interaction, 1)


class DeleteUserSelect(discord.ui.Select):
    def __init__(
        self,
        bot: "PeaceBot",
        owner_id: int,
        candidates: list[discord.Member],
        *,
        page: int,
        total_pages: int,
    ):
        self.bot = bot
        self.owner_id = owner_id
        options = [
            discord.SelectOption(
                label=(member.display_name or member.name or str(member.id))[:100],
                value=str(member.id),
                description=f"@{member.name} · Discord {member.id}"[:100],
            )
            for member in candidates
        ]
        super().__init__(
            custom_id=f"peace_start_delete_users_{owner_id}_{page}",
            placeholder=f"Selecione membros · página {page + 1}/{total_pages}",
            min_values=1,
            max_values=len(options),
            options=options,
            row=0,
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        if interaction.user.id != self.owner_id or interaction.guild is not None:
            await respond(interaction, "Este seletor só pode ser usado pelo responsável no PV do bot.")
            return
        if await self.bot.authorized_dm_member(self.owner_id, "founder") is None:
            await respond(interaction, "Apenas o cargo Founder pode excluir vínculos Peace.")
            return
        target_ids = tuple(dict.fromkeys(int(user_id) for user_id in self.values))
        targets = "\n".join(f"• {mention(user_id)}" for user_id in target_ids)
        await interaction.response.edit_message(
            content="**Confirmação real**\n"
            "Vou remover os cargos gerenciáveis, manter ou aplicar `Not Verified`, conservar o membro no servidor e liberar o ID Peace somente para registros válidos.\n\n"
            f"Usuários selecionados:\n{targets}\n\n"
            "Confirme apenas depois de revisar a lista.",
            view=DeleteUserConfirmationView(self.bot, self.owner_id, target_ids),
            allowed_mentions=discord.AllowedMentions.none(),
        )


class DeleteUserConfirmationView(discord.ui.View):
    def __init__(self, bot: "PeaceBot", owner_id: int, target_ids: tuple[int, ...]):
        super().__init__(timeout=300)
        self.bot = bot
        self.owner_id = owner_id
        self.target_ids = target_ids
        self.processing = False

    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True

    @staticmethod
    def result_lines(results: tuple[str, ...]) -> str:
        visible = [f"• {result[:150]}" for result in results[-10:]]
        hidden = len(results) - len(visible)
        if hidden > 0:
            visible.insert(0, f"• … {hidden} resultado(s) anterior(es)")
        return "\n".join(visible) or "Aguardando o primeiro usuário…"

    @classmethod
    def progress_content(cls, processed: int, total: int, results: tuple[str, ...]) -> str:
        completed = max(0, min(processed, total)) if total else 0
        ratio = completed / total if total else 0
        filled = min(12, round(ratio * 12))
        bar = "█" * filled + "░" * (12 - filled)
        percentage = int(ratio * 100)
        listing = cls.result_lines(results)
        return (
            "**Exclusão em andamento**\n"
            f"`{bar}` **{completed}/{total}** · **{percentage}%**\n\n"
            "**Usuários já processados**\n"
            f"{listing}"
        )

    @discord.ui.button(
        label="Confirmar exclusão",
        style=discord.ButtonStyle.secondary,
        custom_id="peace_start_delete_confirm",
    )
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.owner_id or interaction.guild is not None:
            await respond(interaction, "Esta confirmação só pode ser usada pelo responsável no PV do bot.")
            return
        if self.processing:
            await interaction.response.defer()
            return
        actor = await self.bot.authorized_dm_member(self.owner_id, "founder")
        if actor is None:
            await respond(interaction, "Apenas o cargo Founder pode confirmar esta exclusão.")
            return
        self.processing = True
        self.disable_all()
        await interaction.response.edit_message(
            content=self.progress_content(0, len(self.target_ids), ()),
            view=self,
            allowed_mentions=discord.AllowedMentions.none(),
        )

        async def update_progress(processed: int, total: int, results: tuple[str, ...]) -> None:
            content = self.progress_content(processed, total, results)
            try:
                if interaction.message is not None:
                    await interaction.message.edit(
                        content=content,
                        view=self,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                else:
                    await interaction.edit_original_response(
                        content=content,
                        view=self,
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
            except (discord.Forbidden, discord.HTTPException, discord.NotFound):
                log.info("Não consegui atualizar o progresso da exclusão Peace")

        try:
            results = await self.bot.delete_peace_users(
                self.target_ids,
                actor,
                progress_callback=update_progress,
            )
            content = (
                "**Resultado da exclusão**\n"
                "**Usuários processados**\n"
                f"{self.result_lines(tuple(results)) if results else 'Nenhum usuário foi processado.'}"
            )
        except Exception:
            log.exception("Falha inesperada na confirmação de exclusão Peace")
            content = "**Exclusão não concluída**\nOcorreu uma falha inesperada. Verifique os logs antes de tentar novamente."
        if interaction.message is not None:
            await interaction.message.edit(
                content=content,
                view=self,
                allowed_mentions=discord.AllowedMentions.none(),
            )
        else:
            await interaction.edit_original_response(
                content=content,
                view=self,
                allowed_mentions=discord.AllowedMentions.none(),
            )

    @discord.ui.button(
        label="Cancelar",
        style=discord.ButtonStyle.secondary,
        custom_id="peace_start_delete_cancel",
    )
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if interaction.user.id != self.owner_id:
            await respond(interaction, "Esta confirmação pertence a outro Founder.")
            return
        self.disable_all()
        await interaction.response.edit_message(content="Operação cancelada. Nenhum vínculo foi alterado.", view=self)


class WelcomeView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=None)
        guild_id = bot.settings.guild_id
        set_id = bot.settings.set_channel_id
        rules_id = bot.settings.rules_channel_id
        ticket_id = bot.settings.ticket_panel_channel_id
        if rules_id is not None:
            self.add_item(discord.ui.Button(
                label="📕 Ler regras",
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/channels/{guild_id}/{rules_id}",
            ))
        self.add_item(discord.ui.Button(
            label="◈ Pedir set",
            style=discord.ButtonStyle.link,
            url=f"https://discord.com/channels/{guild_id}/{set_id}",
        ))
        if ticket_id is not None:
            self.add_item(discord.ui.Button(
                label="🎫 Falar com a equipe",
                style=discord.ButtonStyle.link,
                url=f"https://discord.com/channels/{guild_id}/{ticket_id}",
            ))


class TicketDetailsModal(discord.ui.Modal, title="Detalhes do ticket"):
    details = discord.ui.TextInput(
        label="Descreva o caso",
        placeholder="Explique o que aconteceu, com nomes, horários ou prints quando necessário.",
        style=discord.TextStyle.paragraph,
        max_length=2000,
        required=True,
    )

    def __init__(self, bot: "PeaceBot", category: str):
        super().__init__()
        self.bot = bot
        self.category = category

    async def on_submit(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer(ephemeral=True)
        await self.bot.open_ticket(interaction, self.category, str(self.details.value).strip())


class CategorySelect(discord.ui.Select):
    def __init__(self, bot: "PeaceBot"):
        self.bot = bot
        super().__init__(
            placeholder="Escolha o tipo de atendimento",
            custom_id="peace_support_category",
            options=[
                discord.SelectOption(label="Apresentar projeto", value="Apresentar projeto"),
                discord.SelectOption(label="Reportar comportamento", value="Reportar comportamento"),
                discord.SelectOption(label="Ideias", value="Ideias"),
                discord.SelectOption(label="Propostas", value="Propostas"),
                discord.SelectOption(label="Suporte geral", value="Suporte geral"),
                discord.SelectOption(label="Solicitar avaliação · Dev", value="Solicitar avaliação · Dev"),
                discord.SelectOption(label="Solicitar avaliação · Streamer", value="Solicitar avaliação · Streamer"),
                discord.SelectOption(label="Solicitar avaliação · Recrutador", value="Solicitar avaliação · Recrutador"),
                discord.SelectOption(label="Solicitar outra função", value="Solicitar outra função"),
            ],
        )

    async def callback(self, interaction: discord.Interaction) -> None:
        await interaction.response.send_modal(TicketDetailsModal(self.bot, self.values[0]))


class CategoryView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=300)
        self.add_item(CategorySelect(bot))


class SupportView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="◈ Abrir ticket", style=discord.ButtonStyle.secondary, custom_id="peace_support_open_ticket")
    async def open_button(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        await interaction.response.send_message(
            "Selecione uma categoria para abrir o atendimento:",
            view=CategoryView(self.bot),
            ephemeral=True,
        )


class TicketView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=None)
        self.bot = bot

    def ticket(self, interaction: discord.Interaction):
        ticket = self.bot.database.ticket_by_channel(interaction.channel_id)
        if ticket is None or ticket["status"] != "open":
            return None
        return ticket

    @discord.ui.button(label="↗ Poke usuário", style=discord.ButtonStyle.secondary, custom_id="peace_support_poke_ticket")
    async def poke(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = self.ticket(interaction)
        if ticket is None or not isinstance(interaction.channel, discord.TextChannel):
            await respond(interaction, "Este canal não está registrado como ticket.")
            return
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user, self.bot.settings):
            await respond(interaction, "Apenas a staff pode chamar o solicitante.")
            return
        owner = await self.bot.member(interaction.guild, int(ticket["owner_user_id"])) if interaction.guild else None
        if owner is not None:
            try:
                await owner.send(f"A staff enviou um lembrete sobre seu ticket em {interaction.guild.name}.")
            except discord.Forbidden:
                log.info("DM fechado para o solicitante %s", owner.id)
        await interaction.channel.send(f"{mention(ticket['owner_user_id'])}, a staff aguarda seu retorno.")
        await respond(interaction, "Solicitante notificado por mensagem e no ticket.")

    @discord.ui.button(label="≡ Poke staff", style=discord.ButtonStyle.secondary, custom_id="peace_support_poke_staff")
    async def poke_staff(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = self.ticket(interaction)
        if ticket is None or not isinstance(interaction.channel, discord.TextChannel):
            await respond(interaction, "Este canal não está registrado como ticket.")
            return
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user, self.bot.settings):
            await respond(interaction, "Apenas a staff pode notificar a equipe.")
            return
        role = f"<@&{self.bot.settings.staff_role_id}>" if self.bot.settings.staff_role_id else "staff"
        sent = await self.bot.notify_staff_pv(ticket, "O ticket precisa de atendimento e recebeu um Poke.")
        if sent:
            await interaction.channel.send(content=f"{role}, o ticket precisa de atendimento.", allowed_mentions=discord.AllowedMentions(roles=True))
            await respond(interaction, "A equipe foi notificada por PV.")
        else:
            await respond(interaction, "Não foi possível enviar PV para a equipe agora. Verifique o painel interno.")

    @discord.ui.button(label="× Encerrar", style=discord.ButtonStyle.secondary, custom_id="peace_support_close_ticket")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = self.ticket(interaction)
        if ticket is None or not isinstance(interaction.channel, discord.TextChannel):
            await respond(interaction, "Este canal não está registrado como ticket.")
            return
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user, self.bot.settings):
            await respond(interaction, "Apenas a staff pode encerrar tickets.")
            return
        await self.bot.close_ticket_channel(interaction.channel, ticket, interaction.user)
        await respond(interaction, "Ticket encerrado.")

    @discord.ui.button(label="✎ Renomear", style=discord.ButtonStyle.secondary, custom_id="peace_support_rename_ticket")
    async def rename(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if self.ticket(interaction) is None:
            await respond(interaction, "Este ticket já foi encerrado e não aceita alterações.")
            return
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user, self.bot.settings):
            await respond(interaction, "Apenas a staff pode renomear tickets.")
            return
        await interaction.response.send_modal(RenameModal(self.bot))

    @discord.ui.button(label="◉ Criar call", style=discord.ButtonStyle.secondary, custom_id="peace_support_create_call")
    async def create_call(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = self.ticket(interaction)
        if ticket is None or not isinstance(interaction.channel, discord.TextChannel):
            await respond(interaction, "Este canal não está registrado como ticket.")
            return
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user, self.bot.settings):
            await respond(interaction, "Apenas a staff pode criar uma call.")
            return
        if ticket["voice_channel_id"]:
            await respond(interaction, f"A call já existe: <#{ticket['voice_channel_id']}>")
            return
        guild = interaction.guild
        if guild is None:
            await respond(interaction, "Não consegui localizar o servidor.")
            return
        try:
            voice = await guild.create_voice_channel(
                name=f"call-{clean_name(interaction.channel.name)}"[:90],
                category=interaction.channel.category,
                reason="Call criada para ticket",
            )
            self.bot.database.set_ticket_voice(interaction.channel.id, voice.id)
            await interaction.channel.send(f"📞 Call criada: {voice.mention}")
            await respond(interaction, "Call criada para este ticket.")
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao criar call do ticket %s", interaction.channel.id)
            await respond(interaction, "Não consegui criar a call. Verifique as permissões do bot.")

    @discord.ui.button(label="✓ Assumir", style=discord.ButtonStyle.secondary, custom_id="peace_support_claim_ticket")
    async def claim(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        ticket = self.ticket(interaction)
        if ticket is None:
            await respond(interaction, "Este canal não está registrado como ticket.")
            return
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user, self.bot.settings):
            await respond(interaction, "Apenas a staff pode assumir tickets.")
            return
        self.bot.database.claim_ticket(interaction.channel_id, interaction.user.id)
        self.bot.database.record_iris_event(
            event_type="ticket_claimed",
            scope="ticket",
            channel_id=interaction.channel_id,
            ticket_id=int(ticket["id"]),
            actor_user_id=interaction.user.id,
        )
        await self.bot.notify_claim(ticket, interaction.user)
        if isinstance(interaction.channel, discord.TextChannel):
            await interaction.channel.send(
                f"**Atendimento assumido**\nStaff: {interaction.user.mention}\nData: <t:{now_unix()}:F>",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
        await respond(interaction, "Ticket assumido.")


class StaffRenameModal(discord.ui.Modal, title="Alterar nome do ticket"):
    name = discord.ui.TextInput(label="Novo nome", max_length=70, required=True)

    def __init__(self, bot: "PeaceBot", ticket_channel_id: int):
        super().__init__()
        self.bot = bot
        self.ticket_channel_id = ticket_channel_id

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user, self.bot.settings):
            await respond(interaction, "Apenas a staff pode renomear tickets.")
            return
        ticket = self.bot.database.ticket_by_channel(self.ticket_channel_id)
        channel = self.bot.guild.get_channel(self.ticket_channel_id) if self.bot.guild else None
        if ticket is None or ticket["status"] != "open" or not isinstance(channel, discord.TextChannel):
            await respond(interaction, "Este ticket já foi encerrado ou não está disponível.")
            return
        try:
            await channel.edit(name=clean_name(str(self.name.value)), reason="Ticket renomeado pela staff")
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao renomear ticket %s", self.ticket_channel_id)
            await respond(interaction, "Não consegui renomear o ticket. Verifique as permissões do bot.")
            return
        await respond(interaction, "Ticket renomeado.")


class StaffTicketView(discord.ui.View):
    """Controles privados publicados somente no canal da staff."""

    ACTIONS = (
        ("poke_user", "↗ Poke usuário"),
        ("poke_staff", "≡ Poke staff"),
        ("close", "× Encerrar"),
        ("rename", "✎ Renomear"),
        ("create_call", "◉ Criar call"),
        ("claim", "✓ Assumir"),
    )

    def __init__(self, bot: "PeaceBot", ticket_channel_id: int):
        super().__init__(timeout=None)
        self.bot = bot
        self.ticket_channel_id = ticket_channel_id
        for action, label in self.ACTIONS:
            button = discord.ui.Button(
                label=label,
                style=discord.ButtonStyle.secondary,
                custom_id=f"peace_staff_ticket_{action}_{ticket_channel_id}",
            )
            button.callback = self._callback(action)
            self.add_item(button)

    def _callback(self, action: str):
        async def callback(interaction: discord.Interaction) -> None:
            await self.handle(interaction, action)

        return callback

    def target_channel(self) -> discord.TextChannel | None:
        channel = self.bot.guild.get_channel(self.ticket_channel_id) if self.bot.guild else None
        return channel if isinstance(channel, discord.TextChannel) else None

    def disable_all(self) -> None:
        for item in self.children:
            item.disabled = True

    async def handle(self, interaction: discord.Interaction, action: str) -> None:
        if not isinstance(interaction.user, discord.Member) or not staff_member(interaction.user, self.bot.settings):
            await respond(interaction, "Apenas a staff pode usar estes controles.")
            return
        ticket = self.bot.database.ticket_by_channel(self.ticket_channel_id)
        channel = self.target_channel()
        if ticket is None or ticket["status"] != "open" or channel is None:
            await respond(interaction, "Este ticket já foi encerrado ou não está disponível.")
            return
        if action == "rename":
            await interaction.response.send_modal(StaffRenameModal(self.bot, self.ticket_channel_id))
            return
        if action == "poke_user":
            owner = await self.bot.member(interaction.guild, int(ticket["owner_user_id"])) if interaction.guild else None
            if owner is not None:
                try:
                    await owner.send("A staff enviou um lembrete sobre seu ticket na Peace.")
                except (discord.Forbidden, discord.HTTPException):
                    log.info("DM fechado para o solicitante %s", owner.id)
            await channel.send(
                content=f"{mention(ticket['owner_user_id'])}, a staff aguarda seu retorno.",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            await respond(interaction, "Solicitante notificado por PV e no ticket.")
            return
        if action == "poke_staff":
            sent = await self.bot.notify_staff_pv(ticket, "O ticket precisa de atendimento e recebeu um Poke.")
            if sent:
                role = f"<@&{self.bot.settings.staff_role_id}>" if self.bot.settings.staff_role_id else "staff"
                await channel.send(content=f"{role}, o ticket precisa de atendimento.", allowed_mentions=discord.AllowedMentions(roles=True))
                await respond(interaction, "A equipe foi notificada por PV.")
            else:
                await respond(interaction, "Não foi possível enviar PV para a equipe agora. Verifique o painel interno.")
            return
        if action == "claim":
            self.bot.database.claim_ticket(self.ticket_channel_id, interaction.user.id)
            self.bot.database.record_iris_event(
                event_type="ticket_claimed",
                scope="ticket",
                channel_id=self.ticket_channel_id,
                ticket_id=int(ticket["id"]),
                actor_user_id=interaction.user.id,
            )
            await self.bot.notify_claim(ticket, interaction.user)
            await channel.send(
                f"**Atendimento assumido**\nStaff: {interaction.user.mention}\nData: <t:{now_unix()}:F>",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            await respond(interaction, "Ticket assumido.")
            return
        if action == "create_call":
            if ticket["voice_channel_id"]:
                await respond(interaction, f"A call já existe: <#{ticket['voice_channel_id']}>")
                return
            guild = interaction.guild
            if guild is None:
                await respond(interaction, "Não consegui localizar o servidor.")
                return
            try:
                voice = await guild.create_voice_channel(
                    name=f"call-{clean_name(channel.name)}"[:90],
                    category=channel.category,
                    reason="Call criada pela staff para ticket",
                )
                self.bot.database.set_ticket_voice(self.ticket_channel_id, voice.id)
                await channel.send(f"📞 Call criada: {voice.mention}")
                await respond(interaction, "Call criada para este ticket.")
            except (discord.Forbidden, discord.HTTPException):
                log.exception("Falha ao criar call do ticket %s", self.ticket_channel_id)
                await respond(interaction, "Não consegui criar a call. Verifique as permissões do bot.")
            return
        if action == "close":
            await self.bot.close_ticket_channel(channel, ticket, interaction.user)
            self.disable_all()
            if interaction.message is not None:
                await interaction.message.edit(view=self)
            await respond(interaction, "Ticket encerrado.")


class RenameModal(discord.ui.Modal, title="Alterar nome do ticket"):
    name = discord.ui.TextInput(label="Novo nome", max_length=70, required=True)

    def __init__(self, bot: "PeaceBot"):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if not isinstance(interaction.channel, discord.TextChannel):
            await respond(interaction, "Este canal não pode ser renomeado.")
            return
        ticket = self.bot.database.ticket_by_channel(interaction.channel.id)
        if ticket is None or ticket["status"] != "open":
            await respond(interaction, "Este ticket já foi encerrado e não aceita alterações.")
            return
        try:
            await interaction.channel.edit(name=clean_name(str(self.name.value)), reason="Ticket renomeado")
        except discord.Forbidden:
            await respond(interaction, "O bot não tem permissão para renomear este canal.")
            return
        await respond(interaction, "Ticket renomeado.")


class ClockEndView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=None)
        self.bot = bot

    @discord.ui.button(label="× Encerrar ponto", style=discord.ButtonStyle.secondary, custom_id="clock_out_btn")
    async def stop(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            await respond(interaction, "Não consegui identificar seu membro no servidor.")
            return
        try:
            row = self.bot.database.stop_clock(interaction.user.id, interaction.user.id)
            if row is None:
                await respond(interaction, "Você não tem um ponto aberto.")
                return
            seconds = int(row["duration_seconds"] or 0)
            await self.bot.send_log(
                "Ponto finalizado",
                actor=interaction.user,
                fields=(
                    ("Usuário", interaction.user.mention),
                    ("Tempo registrado", duration_text(seconds)),
                    ("Horário", f"<t:{now_unix()}:F>"),
                ),
            )
            await respond(interaction, f"Ponto finalizado: `{duration_text(seconds)}`.")
        except (discord.Forbidden, discord.HTTPException, RuntimeError):
            log.exception("Falha ao encerrar ponto")
            await respond(interaction, "Não consegui encerrar seu ponto. Procure a staff.")


class OperationsView(discord.ui.View):
    def __init__(self, bot: "PeaceBot"):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(discord.ui.Button(label="↗ Site", style=discord.ButtonStyle.link, url=bot.settings.website_url))

    @discord.ui.button(label="◷ Ponto", style=discord.ButtonStyle.secondary, custom_id="clock_in_btn")
    async def clock(self, interaction: discord.Interaction, button: discord.ui.Button) -> None:
        if not isinstance(interaction.user, discord.Member):
            await respond(interaction, "Não consegui identificar seu membro no servidor.")
            return
        try:
            active = self.bot.database.active_clock(interaction.user.id)
            if active is None:
                self.bot.database.start_clock(interaction.user.id)
                await self.bot.send_log(
                    "Ponto iniciado",
                    actor=interaction.user,
                    fields=(
                        ("Usuário", interaction.user.mention),
                        ("Horário", f"<t:{now_unix()}:F>"),
                    ),
                )
                await respond(interaction, "Ponto iniciado. Use × Encerrar ponto quando sair.", view=ClockEndView(self.bot))
            else:
                await respond(interaction, "Seu ponto já está iniciado. Use × Encerrar ponto para encerrar.", view=ClockEndView(self.bot))
        except (discord.Forbidden, discord.HTTPException, RuntimeError):
            log.exception("Falha no ponto")
            await respond(interaction, "Não consegui registrar seu ponto. Tente novamente ou procure a staff.")


class AbsenceModal(discord.ui.Modal, title="Solicitar ausência"):
    start_date = discord.ui.TextInput(label="Data inicial", placeholder="DD/MM/AAAA", max_length=10, required=True)
    end_date = discord.ui.TextInput(label="Data final", placeholder="DD/MM/AAAA", max_length=10, required=True)
    reason = discord.ui.TextInput(label="Motivo", style=discord.TextStyle.paragraph, max_length=1000, required=True)

    def __init__(self, bot: "PeaceBot"):
        super().__init__()
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction) -> None:
        if interaction.guild is None:
            await respond(interaction, "Este formulário só funciona dentro do servidor.")
            return
        start = str(self.start_date.value).strip()
        end = str(self.end_date.value).strip()
        if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", start) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}", end):
            await respond(interaction, "Use as datas no formato DD/MM/AAAA.")
            return
        self.bot.database.save_absence(
            discord_user_id=interaction.user.id,
            start_date=start,
            end_date=end,
            reason=str(self.reason.value).strip(),
        )
        manager = f"<@&{self.bot.settings.manager_role_id}>" if self.bot.settings.manager_role_id else "Management"
        channel = self.bot.guild.get_channel(self.bot.settings.absence_channel_id or 0) if self.bot.guild else None
        if isinstance(channel, discord.TextChannel):
            await channel.send(
                content=(
                    f"{manager}\n**Solicitação de ausência**\n"
                    f"Membro: {interaction.user.mention}\nPeríodo: **{start}** até **{end}**\n"
                    f"Motivo: {str(self.reason.value).strip()}\n\nA gerência precisa verificar a solicitação."
                ),
                allowed_mentions=discord.AllowedMentions(roles=True, users=True),
            )
        await respond(interaction, "Solicitação enviada para a gerência.")


class PeaceBot(commands.Bot):
    def __init__(self, settings: Settings):
        intents = discord.Intents.default()
        intents.members = True
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.settings = settings
        self.database = PeaceDatabase(settings.database_path)
        self.drafts: dict[int, SetDraft] = {}
        self.developer_drafts: dict[int, DeveloperDraft] = {}
        self.verification_challenges: dict[int, tuple[str, float]] = {}
        self.guild: discord.Guild | None = None
        self.panels_synced = False
        self.iris = Iris(settings.iris_url, settings.iris_model) if settings.iris_enabled else None
        self.iris_tasks: dict[int, asyncio.Task] = {}
        self.iris_pending: set[int] = set()
        self.iris_escalation_tasks: dict[int, asyncio.Task] = {}
        self.staff_views: dict[int, StaffTicketView] = {}
        self.set_approval_views: dict[int, SetApprovalView] = {}
        self.return_approval_views: dict[int, ReturnApprovalView] = {}
        self.developer_approval_views: dict[int, DeveloperApprovalView] = {}
        self.announcement_collectors: set[int] = set()
        self.booster_tasks: set[int] = set()
        self.managed_peace_role_removals: set[int] = set()
        self.member_mutation_locks: dict[int, asyncio.Lock] = {}
        self.return_mutation_locks: dict[int, asyncio.Lock] = {}
        self.reception_visibility_synced = False
        self.iris_context_cache = ""
        self.iris_context_cache_at = 0.0
        self.iris_context_lock = asyncio.Lock()
        self.iris_context_task: asyncio.Task | None = None
        self.public_api_runner: web.AppRunner | None = None
        self.central_bridge_runner: web.AppRunner | None = None

    async def setup_hook(self) -> None:
        self.database.initialize()
        await self.start_public_api()
        await self.start_central_bridge()
        self.add_view(SetView(self))
        self.add_view(VerificationStartView(self))
        self.add_view(SupportView(self))
        self.add_view(OperationsView(self))
        self.add_view(ClockEndView(self))
        for row in self.database.open_tickets():
            self.staff_view(int(row["channel_id"]))
        for row in self.database.pending_set_requests():
            self.set_approval_view(int(row["id"]))
        for row in self.database.pending_return_requests():
            self.return_approval_view(int(row["id"]))
        for row in self.database.pending_developer_requests():
            self.developer_approval_view(int(row["id"]))
        try:
            await self.tree.sync()
            await self.tree.sync(guild=discord.Object(id=self.settings.guild_id))
        except discord.HTTPException:
            log.exception("Falha ao sincronizar comandos slash")

    def create_verification_challenge(self, member_id: int) -> list[str]:
        """Create a short-lived CAPTCHA and return its shuffled choices."""
        answer = "".join(secrets.choice(VERIFICATION_ALPHABET) for _ in range(6))
        options = {answer}
        while len(options) < 5:
            options.add("".join(secrets.choice(VERIFICATION_ALPHABET) for _ in range(6)))
        choices = list(options)
        secrets.SystemRandom().shuffle(choices)
        self.verification_challenges[member_id] = (answer, time.monotonic() + 180)
        return choices

    async def ensure_flow_roles(self) -> None:
        """Create the status and onboarding labels used by the member flow."""
        if self.guild is None:
            return
        specs = (
            (
                NOT_VERIFIED_ROLE_NAME,
                getattr(self.settings, "not_verified_role_id", None),
                ("Não verificado", "Nao verificado"),
                discord.Colour(0x7F8C8D),
            ),
            (
                INTERN_ROLE_NAME,
                getattr(self.settings, "intern_role_id", None),
                ("Estagiário", "Estagiario"),
                discord.Colour(0x1ABC9C),
            ),
        )
        for name, role_id, aliases, colour in specs:
            role = role_named(self.guild, role_id, name, *aliases)
            if role is None:
                await self.guild.create_role(
                    name=name,
                    colour=colour,
                    permissions=discord.Permissions.none(),
                    hoist=False,
                    mentionable=False,
                    reason="Criar cargo do fluxo de entrada da Peace",
                )
                continue
            if (
                role.name != name
                or role.permissions != discord.Permissions.none()
                or role.colour.value != colour.value
            ):
                await role.edit(
                    name=name,
                    colour=colour,
                    permissions=discord.Permissions.none(),
                    reason="Padronizar cargo do fluxo de entrada da Peace",
                )

    @staticmethod
    @web.middleware
    async def public_api_cors(request: web.Request, handler) -> web.StreamResponse:
        response = await handler(request)
        origin = request.headers.get("Origin")
        if origin in PUBLIC_API_ORIGINS:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Vary"] = "Origin"
        return response

    async def public_api_health(self, request: web.Request) -> web.Response:
        response = web.json_response({"ok": True, "service": "peace-backend"})
        response.headers["Cache-Control"] = "no-store"
        return response

    async def public_api_status(self, request: web.Request) -> web.Response:
        discord_connected = self.is_ready() and not self.is_closed()
        response = web.json_response(
            {
                "service": "peace-backend",
                "status": "ok" if discord_connected else "starting",
                "frontend": "netlify",
                "discord": {"connected": discord_connected},
            }
        )
        response.headers["Cache-Control"] = "no-store"
        return response

    async def public_api_options(self, request: web.Request) -> web.Response:
        response = web.Response(status=204)
        response.headers["Cache-Control"] = "no-store"
        return response

    def public_api_app(self) -> web.Application:
        """Build the intentionally small public API surface used by Netlify."""
        app = web.Application(middlewares=(self.public_api_cors,))
        app.router.add_get("/healthz", self.public_api_health)
        app.router.add_get("/api/status", self.public_api_status)
        app.router.add_route("OPTIONS", "/api/status", self.public_api_options)
        return app

    async def start_public_api(self) -> None:
        if not self.settings.api_enabled:
            log.info("API pública da Peace desativada por configuração")
            return
        app = self.public_api_app()
        runner = web.AppRunner(app)
        await runner.setup()
        try:
            site = web.TCPSite(runner, self.settings.api_host, self.settings.api_port)
            await site.start()
        except OSError:
            await runner.cleanup()
            log.exception(
                "Não consegui abrir a API pública da Peace em %s:%s",
                self.settings.api_host,
                self.settings.api_port,
            )
            return
        self.public_api_runner = runner
        log.info(
            "API pública da Peace ativa em http://%s:%s",
            self.settings.api_host,
            self.settings.api_port,
        )

    async def stop_public_api(self) -> None:
        if self.public_api_runner is not None:
            await self.public_api_runner.cleanup()
            self.public_api_runner = None

    async def start_central_bridge(self) -> None:
        if not is_valid_central_bridge_key(self.settings.central_bridge_key):
            log.warning("Ponte local da Central desativada: CENTRAL_BRIDGE_KEY inválida")
            return
        try:
            host, port, bridge_url = parse_central_bridge_url(self.settings.central_bridge_url)
        except RuntimeError:
            log.exception("Ponte local da Central desativada: CENTRAL_BRIDGE_URL inválida")
            return
        app = web.Application()
        app.router.add_post("/v1/central/auth/request", self.central_auth_request)
        app.router.add_post("/v1/central/auth/verify", self.central_auth_verify)
        app.router.add_post("/v1/central/auth/session", self.central_auth_session)
        app.router.add_post("/v1/central/auth/revoke", self.central_auth_revoke)
        runner = web.AppRunner(app)
        await runner.setup()
        try:
            site = web.TCPSite(runner, host, port)
            await site.start()
        except OSError:
            await runner.cleanup()
            log.exception(
                "Não consegui abrir a ponte local da Central em %s:%s",
                host,
                port,
            )
            return
        self.central_bridge_runner = runner
        log.info("Ponte local da Central ativa em %s", bridge_url)

    async def stop_central_bridge(self) -> None:
        if self.central_bridge_runner is not None:
            await self.central_bridge_runner.cleanup()
            self.central_bridge_runner = None

    def central_bridge_authorized(self, request: web.Request) -> bool:
        supplied = request.headers.get("X-Central-Bridge-Key", "")
        return bool(
            supplied
            and is_valid_central_bridge_key(self.settings.central_bridge_key)
            and secrets.compare_digest(supplied, self.settings.central_bridge_key)
        )

    @staticmethod
    def central_client_id(value: object) -> str | None:
        client_id = str(value or "").strip()
        return client_id if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._:-]{7,127}", client_id) else None

    @staticmethod
    def central_project_id(value: object) -> str | None:
        project_id = str(value or "").strip()
        return project_id if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}", project_id) else None

    @staticmethod
    def central_bearer_token(request: web.Request) -> str | None:
        authorization = request.headers.get("Authorization", "")
        match = re.fullmatch(r"Bearer ([A-Za-z0-9_-]{40,})", authorization)
        return match.group(1) if match else None

    async def central_auth_member(self, peace_id: int) -> discord.Member | None:
        record = self.database.member_by_peace_id(peace_id)
        if record is None:
            return None
        guild = self.guild or self.get_guild(self.settings.guild_id)
        if guild is None:
            return None
        try:
            member = await guild.fetch_member(int(record["discord_user_id"]))
        except discord.NotFound:
            member = None
        except (discord.Forbidden, discord.HTTPException):
            return None
        if member is None or not role_member(member, self.settings.central_access_role_id):
            return None
        return member

    @staticmethod
    def central_denied() -> web.Response:
        return web.json_response({"ok": False, "message": CENTRAL_AUTH_DENIAL}, status=403)

    @staticmethod
    def central_session_response(row, token: str | None = None) -> dict[str, object]:
        response: dict[str, object] = {
            "peace_id": int(row["peace_id"]),
            "subject": f"discord:{row['discord_user_id']}",
            "client_id": row["client_id"],
            "scope": str(row["scope"]).split(),
            "project_id": row["project_id"],
            "expires_at": row["expires_at"],
        }
        if token is not None:
            response["token"] = token
        return response

    async def central_auth_request(self, request: web.Request) -> web.Response:
        if not self.central_bridge_authorized(request):
            return web.json_response({"ok": False, "message": "Ponte não autorizada."}, status=401)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise TypeError
            peace_id = int(payload.get("peace_id", 0))
            client_id = self.central_client_id(payload.get("client_id"))
        except (ValueError, TypeError, json.JSONDecodeError):
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        if peace_id <= 0 or client_id is None:
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        project_id = self.central_project_id(payload.get("project_id"))
        if payload.get("project_id") and project_id is None:
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        member = await self.central_auth_member(peace_id)
        if member is None:
            return self.central_denied()
        if not self.database.central_login_request_allowed(
            discord_user_id=member.id,
            client_id=client_id,
        ):
            return web.json_response(
                {"ok": False, "message": CENTRAL_AUTH_THROTTLED},
                status=429,
                headers={"Retry-After": "600"},
            )
        issued = await self.issue_central_login_code(member, peace_id, client_id)
        if issued is None:
            return web.json_response(
                {"ok": False, "message": CENTRAL_AUTH_THROTTLED},
                status=429,
                headers={"Retry-After": "600"},
            )
        if not issued:
            return web.json_response(
                {"ok": False, "message": "Não foi possível enviar a DM. Abra suas mensagens privadas."},
                status=502,
            )
        return web.json_response({"ok": True, "message": "Código enviado no Discord."})

    async def central_auth_verify(self, request: web.Request) -> web.Response:
        if not self.central_bridge_authorized(request):
            return web.json_response({"ok": False, "message": "Ponte não autorizada."}, status=401)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise TypeError
            peace_id = int(payload.get("peace_id", 0))
            code = str(payload.get("code", "")).strip()
            client_id = self.central_client_id(payload.get("client_id"))
        except (ValueError, TypeError, json.JSONDecodeError):
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        if peace_id <= 0 or not re.fullmatch(r"\d{6}", code) or client_id is None:
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        project_id = self.central_project_id(payload.get("project_id"))
        if payload.get("project_id") and project_id is None:
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        member = await self.central_auth_member(peace_id)
        if member is None:
            return self.central_denied()
        valid = self.database.consume_central_login_challenge(
            discord_user_id=member.id,
            peace_id=peace_id,
            client_id=client_id,
            code=code,
        )
        if not valid:
            return web.json_response({"ok": False, "message": "Código inválido, expirado ou já utilizado."}, status=401)
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.settings.central_auth_session_ttl_seconds
        )
        scope = "central:access central:sync" if project_id else "central:access"
        token = self.database.create_central_login_session(
            discord_user_id=member.id,
            peace_id=peace_id,
            client_id=client_id,
            project_id=project_id,
            scope=scope,
            expires_at=expires_at.isoformat(),
        )
        row = self.database.validate_central_login_session(
            token=token,
            client_id=client_id,
            project_id=project_id,
        )
        if row is None:
            return web.json_response({"ok": False, "message": "Não foi possível criar a sessão da Central."}, status=503)
        return web.json_response({
            "ok": True,
            "message": "Acesso à Central liberado.",
            "session": self.central_session_response(row, token),
        })

    async def central_auth_session(self, request: web.Request) -> web.Response:
        if not self.central_bridge_authorized(request):
            return web.json_response({"ok": False, "message": "Ponte não autorizada."}, status=401)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise TypeError
        except (TypeError, json.JSONDecodeError):
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        client_id = self.central_client_id(payload.get("client_id"))
        token = self.central_bearer_token(request)
        project_id = self.central_project_id(payload.get("project_id"))
        if client_id is None or token is None or (payload.get("project_id") and project_id is None):
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        row = self.database.validate_central_login_session(
            token=token,
            client_id=client_id,
            project_id=project_id,
        )
        if row is None:
            return self.central_denied()
        member = await self.central_auth_member(int(row["peace_id"]))
        if member is None:
            self.database.revoke_central_login_session(token=token, client_id=client_id)
            return self.central_denied()
        return web.json_response({
            "ok": True,
            "message": "Sessão válida.",
            "session": self.central_session_response(row),
        })

    async def central_auth_revoke(self, request: web.Request) -> web.Response:
        if not self.central_bridge_authorized(request):
            return web.json_response({"ok": False, "message": "Ponte não autorizada."}, status=401)
        try:
            payload = await request.json()
            if not isinstance(payload, dict):
                raise TypeError
        except (TypeError, json.JSONDecodeError):
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        client_id = self.central_client_id(payload.get("client_id"))
        token = self.central_bearer_token(request)
        if client_id is None or token is None:
            return web.json_response({"ok": False, "message": "Dados de acesso inválidos."}, status=400)
        self.database.revoke_central_login_session(token=token, client_id=client_id)
        return web.json_response({"ok": True, "message": "Sessão encerrada."})

    async def close(self) -> None:
        await self.stop_public_api()
        await self.stop_central_bridge()
        await super().close()

    async def run_startup_step(self, label: str, operation):
        """Run one startup reconciliation without blocking the remaining steps."""

        try:
            return True, await operation()
        except asyncio.CancelledError:
            raise
        except Exception as error:
            log.exception(
                "Etapa de inicialização '%s' falhou; as próximas etapas continuarão (%s)",
                label,
                exception_details(error),
            )
            return False, None

    @staticmethod
    def report_background_task(task: asyncio.Task) -> None:
        """Consume task exceptions so asyncio never emits an unhandled warning."""

        if task.cancelled():
            return
        try:
            task.result()
        except Exception as error:
            log.error(
                "Tarefa em segundo plano '%s' terminou com erro (%s)",
                task.get_name(),
                exception_details(error),
                exc_info=(type(error), error, error.__traceback__),
            )

    async def on_ready(self) -> None:
        self.guild = self.get_guild(self.settings.guild_id)
        if self.guild is None:
            log.error("Servidor %s não está disponível no cache do bot", self.settings.guild_id)
            return
        log.info("Conectado como %s no servidor %s", self.user, self.guild.name)
        # Nickname repair is an independent startup invariant. Run it before
        # panel reconciliation so a slow or rate-limited panel history request
        # cannot prevent existing Peace members from receiving their live
        # visual-role prefix.
        await self.run_startup_step("tags Peace prioritárias", self.sync_peace_tags)
        if not self.panels_synced:
            completed, result = await self.run_startup_step("painéis", self.sync_panels)
            self.panels_synced = completed and result is True
        await self.run_startup_step("cargos do fluxo de entrada", self.ensure_flow_roles)
        await self.run_startup_step("retornos Peace aprovados", self.sync_approved_return_requests)
        await self.run_startup_step("reserva de IDs Peace", self.sync_missing_peace_ids)
        await self.run_startup_step("painel de verificação", self.sync_verification_panel)
        for label, operation in (
            ("painel de boas-vindas", self.sync_welcome_panel),
            ("painel anti-spam", self.sync_automod_channel),
            ("auditoria dos tickets fechados", self.audit_closed_tickets),
            ("auditoria dos tickets abertos", self.audit_open_ticket_controls),
        ):
            await self.run_startup_step(label, operation)
        if self.iris is not None:
            await self.run_startup_step("auditoria da Iris", self.audit_iris_messages)
        for label, operation in (
            ("mensagens fixas de tickets", self.audit_fixed_ticket_messages),
            ("limpeza de painéis internos antigos", self.cleanup_staff_ticket_panels),
            ("painéis de controle dos tickets", self.sync_ticket_control_panels),
            ("painéis de set pendentes", self.sync_pending_set_panels),
            ("painéis de retorno pendentes", self.sync_pending_return_panels),
            ("painéis de developers pendentes", self.sync_pending_developer_panels),
            ("cargos de visitante", self.sync_visitor_roles),
            ("limpeza de exclusões Peace antigas", self.sync_released_member_cleanup),
        ):
            await self.run_startup_step(label, operation)
        if self.iris is not None:
            await self.run_startup_step("retomada da Iris", self.resume_iris)
        if self.iris is not None and (self.iris_context_task is None or self.iris_context_task.done()):
            self.iris_context_task = asyncio.create_task(
                self.organization_context(),
                name="iris-context-warmup",
            )
            self.iris_context_task.add_done_callback(self.report_background_task)

    async def on_member_join(self, member: discord.Member) -> None:
        await self.reconcile_visitor_role(member)
        if not await self.ensure_return_request(member):
            await self.sync_member_tag(member)
        await self.ensure_booster_space(member)

    async def peace_role_removal_actor(
        self,
        before: discord.Member,
        after: discord.Member,
    ) -> discord.abc.User | None:
        """Best-effort audit-log lookup; never guess an actor from stale entries."""
        guild = after.guild
        bot_member = getattr(guild, "me", None)
        permissions = getattr(bot_member, "guild_permissions", None)
        if bot_member is None or not getattr(permissions, "view_audit_log", False):
            return None

        def role_ids(value) -> set[int]:
            roles = getattr(value, "roles", value)
            if roles is None:
                return set()
            return {int(getattr(role, "id", role)) for role in roles}

        try:
            async for entry in guild.audit_logs(
                limit=15,
                action=discord.AuditLogAction.member_role_update,
            ):
                target = getattr(entry, "target", None)
                if getattr(target, "id", None) != after.id:
                    continue
                created_at = getattr(entry, "created_at", None)
                if created_at is None or datetime.now(timezone.utc) - created_at > timedelta(seconds=45):
                    continue
                for change in getattr(entry, "changes", ()):
                    if getattr(change, "key", None) != "roles":
                        continue
                    before_ids = role_ids(getattr(change, "before", None))
                    after_ids = role_ids(getattr(change, "after", None))
                    if not before_ids and not after_ids:
                        continue
                    if self.settings.peace_role_id in before_ids and self.settings.peace_role_id not in after_ids:
                        actor = getattr(entry, "user", None)
                        if actor is not None:
                            return actor
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não consegui consultar o audit log para a remoção de Peace de %s", after.id)
        return None

    async def reserve_member_peace(
        self,
        member: discord.Member,
        *,
        reason: str,
        actor: discord.abc.User | None = None,
    ) -> sqlite3.Row | None:
        reserved = self.database.reserve_peace_member(
            member.id,
            reason=reason,
            actor_user_id=getattr(actor, "id", None),
        )
        if reserved is not None:
            await self.send_log(
                "ID Peace reservado",
                actor=actor or member,
                fields=(
                    ("Usuário", member.mention),
                    ("ID reservado", f"`{int(reserved['peace_id'])}`"),
                    ("Motivo", reason),
                    ("Quem", actor.mention if actor is not None else "não identificado"),
                    ("Horário", f"<t:{now_unix()}:F>"),
                ),
            )
        return reserved

    async def on_member_remove(self, member: discord.Member) -> None:
        if member.bot:
            return
        existing_reservation = self.database.reserved_peace_id_for_user(member.id)
        if existing_reservation is not None:
            self.database.annotate_peace_reservation(
                member.id,
                reason="membro também saiu do servidor",
            )
            return
        if not role_member(member, self.settings.peace_role_id) and not self.database.recorded_peace_member(
            member.id,
            self.settings.peace_role_id,
        ):
            return
        await self.reserve_member_peace(
            member,
            reason="membro saiu do servidor enquanto o vínculo Peace estava ativo",
        )

    async def on_member_update(self, before: discord.Member, after: discord.Member) -> None:
        roles_changed = before.roles != after.roles
        nickname_changed = getattr(before, "nick", None) != getattr(after, "nick", None)
        if not roles_changed and not nickname_changed:
            return
        # A removal clears the nickname before it removes the Peace role. Do
        # not let the intermediate Discord event immediately rebuild the old
        # tag while the two-step mutation is still in progress.
        if after.id in self.managed_peace_role_removals:
            return
        if roles_changed:
            before_role_ids = {role.id for role in before.roles}
            after_role_ids = {role.id for role in after.roles}
            peace_removed = (
                self.settings.peace_role_id in before_role_ids
                and self.settings.peace_role_id not in after_role_ids
            )
            if peace_removed and after.id not in self.managed_peace_role_removals:
                actor = await self.peace_role_removal_actor(before, after)
                await self.reserve_member_peace(
                    after,
                    reason="cargo Peace retirado enquanto o membro permaneceu no servidor",
                    actor=actor,
                )
            visitor = role_named(
                after.guild,
                getattr(self.settings, "visitor_role_id", None),
                "Visitor",
            )
            not_verified = role_named(
                after.guild,
                getattr(self.settings, "not_verified_role_id", None),
                NOT_VERIFIED_ROLE_NAME,
                "Não verificado",
                "Nao verificado",
            )
            prefer_reverification = (
                visitor is not None
                and not_verified is not None
                and visitor.id in before_role_ids
                and visitor.id in after_role_ids
                and not_verified.id not in before_role_ids
                and not_verified.id in after_role_ids
            )
            await self.reconcile_visitor_role(
                after,
                prefer_reverification=prefer_reverification,
            )
            if prefer_reverification:
                await self.sync_verification_panel()
        if not await self.ensure_return_request(after):
            await self.sync_member_tag(after)
        if roles_changed:
            await self.ensure_booster_space(after)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        try:
            if message.guild is None:
                dm_command = (message.content or "").strip().casefold()
                if dm_command in {"start", "/start", "!start"}:
                    log.info("Menu interno solicitado por DM (usuário %s)", message.author.id)
                    await self.send_dm_start_menu(message.author.id, message.channel)
                return
            if self.settings.automod_channel_id and message.channel.id == self.settings.automod_channel_id:
                await self.handle_automod_message(message)
                return
            if message.channel.id in self.settings.iris_learning_channel_ids:
                self.iris_context_cache_at = 0.0
            ticket = self.database.ticket_by_channel(message.channel.id)
            if ticket is not None and ticket["status"] == "open" and isinstance(message.channel, discord.TextChannel):
                is_owner = int(ticket["owner_user_id"]) == message.author.id
                is_staff = isinstance(message.author, discord.Member) and staff_member(message.author, self.settings)
                claimed = bool(ticket["claimed_by"])
                if self.iris is not None:
                    if (is_owner and (not claimed or self.iris_mentioned(message))) or (is_staff and self.iris_mentioned(message)):
                        self.schedule_iris_response(message.channel)
                    if is_owner:
                        self.start_iris_escalation(message.channel)
            await self.process_commands(message)
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao processar mensagem %s", message.id)
        except Exception:
            log.exception("Erro inesperado ao processar mensagem %s", message.id)

    async def on_error(self, event_method: str, *args, **kwargs) -> None:
        """Keep unexpected event failures visible without crashing the bot."""

        log.exception("Erro não tratado no evento '%s'", event_method)

    async def on_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError) -> None:
        original = getattr(error, "original", error)
        command_name = interaction.command.qualified_name if interaction.command else "desconhecido"
        if isinstance(original, app_commands.CommandOnCooldown):
            log.info("Comando slash em cooldown: %s", command_name)
            await respond(interaction, "Aguarde alguns segundos e tente novamente.")
            return
        if isinstance(original, app_commands.CheckFailure):
            log.warning("Comando slash recusado por permissão: %s", command_name)
            await respond(interaction, "Você não tem permissão para executar esta ação.")
            return
        log.error(
            "Erro em comando slash '%s' (%s)",
            command_name,
            exception_details(original),
            exc_info=(type(original), original, original.__traceback__),
        )
        try:
            await respond(interaction, "Ocorreu um erro ao executar a ação. A staff foi avisada.")
        except discord.HTTPException as response_error:
            log.warning(
                "Não foi possível responder ao erro da interação (%s)",
                exception_details(response_error),
            )

    async def on_command_error(self, context: commands.Context, error: commands.CommandError) -> None:
        if isinstance(error, commands.CommandNotFound):
            return
        log.error(
            "Erro em comando prefixado '%s' (%s)",
            getattr(context.command, "qualified_name", "desconhecido"),
            exception_details(error),
            exc_info=(type(error), error, error.__traceback__),
        )

    async def sync_one_panel(
        self,
        channel_id: int | None,
        custom_id: str,
        embed: discord.Embed | list[discord.Embed],
        view: discord.ui.View,
        asset_name: str | None = None,
    ) -> bool:
        if channel_id is None or self.guild is None or self.user is None:
            return False
        channel = self.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            log.warning("Canal de painel inválido ou ausente: %s", channel_id)
            return False
        embeds = embed if isinstance(embed, list) else [embed]
        try:
            matches: list[discord.Message] = []
            async for message in channel.history(limit=100):
                if message.author.id != self.user.id:
                    continue
                custom_ids = {
                    component.custom_id
                    for row in message.components
                    for component in row.children
                    if component.custom_id
                }
                if custom_id in custom_ids:
                    matches.append(message)
            if matches:
                message = matches[0]
                attachments = [asset(asset_name)] if asset_name else []
                if asset_name:
                    embeds[0].set_image(url=f"attachment://{asset_name}")
                payload = self.panel_embed_payload(embeds)
                await message.edit(content=None, **payload, view=view, attachments=attachments)
                for duplicate in matches[1:]:
                    await duplicate.delete()
                return True
            file = asset(asset_name) if asset_name else None
            if asset_name:
                embeds[0].set_image(url=f"attachment://{asset_name}")
            payload = self.panel_embed_payload(embeds)
            await channel.send(**payload, view=view, file=file)
            return True
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao sincronizar painel no canal %s", channel_id)
            return False

    @staticmethod
    def panel_embed_payload(embeds: list[discord.Embed]) -> dict[str, object]:
        """Use one or multiple embeds without changing the single-embed API."""
        if len(embeds) == 1:
            return {"embed": embeds[0]}
        return {"embeds": embeds}

    async def sync_panels(self) -> bool:
        results = await asyncio.gather(
            self.sync_one_panel(self.settings.set_channel_id, "peace_pedir_set_open", self.set_panel_embeds(), SetView(self), SET_PANEL_ASSET),
            self.sync_one_panel(self.settings.ticket_panel_channel_id, "peace_support_open_ticket", self.support_panel_embeds(), SupportView(self), TICKET_PANEL_ASSET),
            self.sync_one_panel(self.settings.operations_channel_id, "clock_in_btn", self.operations_panel_embeds(), OperationsView(self), OPERATIONS_PANEL_ASSET),
        )
        return all(results)

    @staticmethod
    def verification_panel_embed() -> discord.Embed:
        embed = discord.Embed(
            title="◈ Verificação de acesso",
            color=0x101827,
        )
        embed.add_field(
            name="1 · INICIAR",
            value="Use o botão abaixo.",
            inline=True,
        )
        embed.add_field(
            name="2 · LER",
            value="Leia o código exibido.",
            inline=True,
        )
        embed.add_field(
            name="3 · SELECIONAR",
            value="Escolha a opção correta.",
            inline=True,
        )
        embed.set_image(url=f"attachment://{VERIFICATION_ASSET}")
        embed.set_footer(text=VERIFICATION_PANEL_MARKER)
        return embed

    @staticmethod
    def verification_explanation_embed() -> discord.Embed:
        embed = discord.Embed(
            title="Como funciona",
            description=(
                "Clique em **Iniciar verificação**, leia o código da imagem e selecione a resposta. "
                "Quando a escolha estiver correta, eu libero o cargo **Visitor** para você."
            ),
            color=0x101827,
        )
        embed.add_field(
            name="O que faz",
            value="Confirma que uma pessoa está controlando a conta antes de liberar o acesso inicial.",
            inline=True,
        )
        embed.add_field(
            name="Por que existe",
            value="Reduz automações e mantém as áreas de visitante protegidas.",
            inline=True,
        )
        return embed

    @classmethod
    def verification_panel_embeds(cls) -> list[discord.Embed]:
        return [cls.verification_panel_embed(), cls.verification_explanation_embed()]

    async def sync_verification_panel(self) -> bool:
        """Publish the CAPTCHA panel without changing channel structure or permissions."""
        if self.guild is None or self.user is None:
            return False
        try:
            channel = (
                self.guild.get_channel(self.settings.verification_channel_id)
                if self.settings.verification_channel_id is not None
                else None
            )
            if not isinstance(channel, discord.TextChannel):
                channel = discord.utils.find(
                    lambda item: item.name.casefold() in {VERIFICATION_CHANNEL_NAME.casefold(), "verificar"},
                    self.guild.text_channels,
                )
            if channel is None:
                log.warning("Canal de verificação não encontrado; permissões não serão alteradas")
                return False

            embeds = self.verification_panel_embeds()
            matches: list[discord.Message] = []
            async for message in channel.history(limit=100):
                if message.author.id != self.user.id:
                    continue
                if message.embeds and (message.embeds[0].footer.text or "") == VERIFICATION_PANEL_MARKER:
                    matches.append(message)
            if matches:
                payload = self.panel_embed_payload(embeds)
                await matches[0].edit(
                    content=None,
                    **payload,
                    view=VerificationStartView(self),
                    attachments=[asset(VERIFICATION_ASSET)],
                )
                for duplicate in matches[1:]:
                    await duplicate.delete()
            else:
                payload = self.panel_embed_payload(embeds)
                await channel.send(
                    **payload,
                    view=VerificationStartView(self),
                    file=asset(VERIFICATION_ASSET),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            return True
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao sincronizar a área de verificação")
            return False

    @staticmethod
    def automod_embed() -> discord.Embed:
        embed = discord.Embed(
            color=0xE74C3C,
        )
        embed.add_field(
            name="🛡️ DETECT",
            value="Mensagem identificada",
            inline=True,
        )
        embed.add_field(
            name="🧹 REMOVE",
            value="Mensagem removida",
            inline=True,
        )
        embed.add_field(
            name="⏱️ TIMEOUT",
            value="7 dias",
            inline=True,
        )
        embed.set_image(url=f"attachment://{AUTOMOD_ASSET}")
        return embed

    @staticmethod
    def is_automod_panel_message(message: discord.Message) -> bool:
        """Identify old or current bot-owned anti-spam panels without touching user messages."""
        embed_text: list[str] = []
        image_urls: list[str] = []
        for embed in message.embeds:
            embed_text.extend(
                value
                for value in (
                    embed.title or "",
                    embed.description or "",
                    embed.footer.text or "",
                    *(field.name for field in embed.fields),
                    *(field.value for field in embed.fields),
                )
                if value
            )
            if embed.image.url:
                image_urls.append(embed.image.url)
        attachments = " ".join(attachment.filename for attachment in message.attachments)
        searchable = "\n".join((message.content, *embed_text, attachments)).casefold()
        return (
            "peace // spam control" in searchable
            or "contenção automática" in searchable
            or "<svg" in searchable
            or "automod.png" in " ".join(image_urls).casefold()
            or "automod.svg" in searchable
        )

    async def sync_automod_channel(self) -> None:
        """Refresh only the bot-owned anti-spam message; never change channel permissions."""
        if self.guild is None or self.user is None or self.settings.automod_channel_id is None:
            return
        channel = self.guild.get_channel(self.settings.automod_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            matches: list[discord.Message] = []
            async for message in channel.history(limit=100):
                if message.author.id == self.user.id and self.is_automod_panel_message(message):
                    matches.append(message)
            embed = self.automod_embed()
            if matches:
                await matches[0].edit(
                    content=None,
                    embed=embed,
                    view=None,
                    attachments=[asset(AUTOMOD_ASSET)],
                )
                for duplicate in matches[1:]:
                    await duplicate.delete()
                return
            await channel.send(
                embed=embed,
                file=asset(AUTOMOD_ASSET),
                allowed_mentions=discord.AllowedMentions.none(),
            )
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao sincronizar o painel anti-spam")

    async def handle_automod_message(self, message: discord.Message) -> None:
        """Apaga a mensagem do honeypot e aplica timeout, sem expulsar nem banir."""
        try:
            await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não consegui apagar a mensagem do honeypot %s", message.id)
        if isinstance(message.author, discord.Member):
            try:
                await message.author.timeout(
                    timedelta(days=7),
                    reason="Mensagem enviada no canal de moderação automática",
                )
            except (discord.Forbidden, discord.HTTPException):
                log.info("Não consegui aplicar timeout automático em %s", message.author.id)
            self.database.record_iris_event(
                event_type="automod_timeout",
                scope="automod",
                channel_id=message.channel.id,
                actor_user_id=message.author.id,
            )
            await self.send_log(
                "Moderação automática",
                actor=message.author,
                fields=(
                    ("Usuário", message.author.mention),
                    ("Ação", "Mensagem removida e timeout de 7 dias aplicado."),
                    ("Canal", getattr(message.channel, "mention", f"#{message.channel.id}")),
                    ("Horário", f"<t:{now_unix()}:F>"),
                ),
            )

    async def disable_ticket_controls(self, channel: discord.TextChannel) -> None:
        if self.user is None:
            return
        try:
            async for message in channel.history(limit=100):
                if message.author.id != self.user.id:
                    continue
                if self.is_ticket_control_message(message):
                    await message.edit(view=None)
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao remover controles do ticket encerrado %s", channel.id)

    async def audit_closed_tickets(self) -> None:
        if self.guild is None or self.settings.closed_ticket_category_id is None:
            return
        category = self.guild.get_channel(self.settings.closed_ticket_category_id)
        if not isinstance(category, discord.CategoryChannel):
            return
        for channel in category.text_channels:
            await self.disable_ticket_controls(channel)

    async def audit_open_ticket_controls(self) -> None:
        """Atualiza tickets antigos para o conjunto atual de botões monocromáticos."""
        if self.guild is None or self.user is None:
            return
        for row in self.database.open_tickets():
            channel = self.guild.get_channel(int(row["channel_id"]))
            if not isinstance(channel, discord.TextChannel):
                continue
            try:
                async for message in channel.history(limit=50):
                    if message.author.id != self.user.id or not message.components:
                        continue
                    custom_ids = self.message_custom_ids(message)
                    if custom_ids & TICKET_IDS or any(
                        custom_id.startswith("peace_ticket_owner_")
                        for custom_id in custom_ids
                    ):
                        await message.delete()
            except (discord.Forbidden, discord.HTTPException):
                log.info("Não foi possível atualizar os botões do ticket %s", channel.id)

    async def audit_iris_messages(self) -> None:
        """Converte respostas antigas em cards para texto simples e seguro."""
        if self.guild is None or self.user is None:
            return
        channels: list[discord.TextChannel] = []
        for channel_id in (self.settings.ticket_category_id, self.settings.closed_ticket_category_id):
            channel = self.guild.get_channel(channel_id or 0)
            if isinstance(channel, discord.CategoryChannel):
                channels.extend(channel.text_channels)
            elif isinstance(channel, discord.TextChannel):
                channels.append(channel)
        seen: set[int] = set()
        for channel in channels:
            if channel.id in seen:
                continue
            seen.add(channel.id)
            try:
                async for message in channel.history(limit=100):
                    if message.author.id != self.user.id:
                        continue
                    content = message.content or ""
                    if message.embeds and (message.embeds[0].title or "") == "Ticket aberto" and "<@&" in content:
                        await message.edit(content="")
                        continue
                    if "recebeu pv (" in content.casefold():
                        match = re.search(r"pv \((\d+) pessoa", content.casefold())
                        sent = int(match.group(1)) if match else 0
                        replacement = (
                            "A equipe foi notificada por PV e o ticket ainda aguarda atendimento."
                            if sent else
                            "O ticket ainda aguarda atendimento. A equipe deve verificar o painel interno."
                        )
                        await message.edit(content=replacement)
                        continue
                    if content and any(marker in content.casefold() for marker in ("[referência interna]", "[dado sensível removido]", "solicitante:", "se necessário, mencione a staff", "se precisar da equipe")):
                        await message.edit(content=sanitize_assistant_output(content))
                        continue
                    if not message.embeds:
                        continue
                    title = message.embeds[0].title or ""
                    if title not in {"Iris · atendimento", "Iris · plano técnico"}:
                        continue
                    text = sanitize_assistant_output(message.embeds[0].description or "")
                    await message.edit(content=text, embed=None)
            except (discord.Forbidden, discord.HTTPException):
                log.info("Não foi possível migrar mensagens da Iris no canal %s", channel.id)

    async def audit_fixed_ticket_messages(self) -> None:
        """Migra avisos fixos antigos para embeds e elimina controles públicos antigos."""
        if self.guild is None or self.user is None:
            return
        for ticket in self.database.all_tickets():
            channel = self.guild.get_channel(int(ticket["channel_id"]))
            if not isinstance(channel, discord.TextChannel):
                continue
            owner = await self.member(self.guild, int(ticket["owner_user_id"]))
            closer = await self.member(self.guild, int(ticket["closed_by"])) if ticket["closed_by"] else None
            try:
                async for message in channel.history(limit=100):
                    if message.author.id != self.user.id:
                        continue
                    ids = self.message_custom_ids(message)
                    if any(custom_id.startswith("peace_ticket_owner_") for custom_id in ids):
                        await message.delete()
                        continue
                    content = (message.content or "").casefold()
                    title = (message.embeds[0].title or "").casefold() if message.embeds else ""
                    if "ações do solicitante" in content or "controles exclusivos da staff" in content:
                        await message.delete()
                        continue
                    if title == "controles do atendimento":
                        await message.edit(
                            content=None,
                            embed=self.ticket_staff_embed(ticket),
                            view=self.staff_view(int(ticket["channel_id"])) if ticket["status"] == "open" else None,
                        )
                        continue
                    if "ticket aberto" in content or title.startswith("ticket aberto"):
                        await message.edit(
                            content=None,
                            embed=self.ticket_open_embed(int(ticket["id"]), mention(ticket["owner_user_id"]), str(ticket["reason"]), str(ticket["details"])),
                        )
                    elif "ticket encerrado" in content or title.startswith("ticket encerrado"):
                        await message.edit(content=None, embed=self.ticket_closed_embed(ticket, closer))
            except (discord.Forbidden, discord.HTTPException):
                log.info("Não foi possível migrar os avisos fixos do ticket %s", ticket["id"])

    @staticmethod
    def ticket_staff_embed(ticket) -> discord.Embed:
        embed = discord.Embed(
            title="Controles do atendimento",
            description=(
                "Controles exclusivos da staff. O solicitante não possui ações neste painel.\n\n"
                "Use assumir, chamar, criar call, renomear ou encerrar conforme o andamento do atendimento."
            ),
        )
        embed.add_field(name="Categoria", value=redact(str(ticket["reason"]), limit=100), inline=True)
        embed.add_field(name="Ticket", value=f"<#{int(ticket['channel_id'])}>", inline=True)
        embed.set_footer(text=f"ticket:{int(ticket['id'])}")
        return embed

    @staticmethod
    def ticket_open_embed(ticket_id: int, owner_mention: str, reason: str, details: str) -> discord.Embed:
        embed = discord.Embed(
            title=f"Ticket aberto · #{ticket_id:04d}",
            description=(
                f"{owner_mention}, seu atendimento foi registrado. A Íris fará a triagem inicial; "
                "a staff pode assumir quando necessário.\n\n"
                "Responda diretamente neste canal e não envie senhas, tokens ou dados pessoais desnecessários."
            ),
        )
        embed.add_field(name="Motivo", value=redact(reason, limit=100), inline=True)
        embed.add_field(name="Detalhes iniciais", value=redact(details, limit=900), inline=False)
        embed.set_footer(text=f"ticket:{ticket_id}")
        return embed

    @staticmethod
    def ticket_closed_embed(ticket, actor: discord.Member | None = None) -> discord.Embed:
        embed = discord.Embed(
            title=f"Ticket encerrado · #{int(ticket['id']):04d}",
            description="Este atendimento foi encerrado e arquivado. O histórico permanece disponível apenas para a Íris.",
        )
        embed.add_field(name="Responsável pelo encerramento", value=actor.mention if actor else "staff", inline=True)
        embed.add_field(name="Categoria", value=redact(str(ticket["reason"]), limit=100), inline=True)
        embed.set_footer(text=f"ticket:{int(ticket['id'])}")
        return embed

    def staff_view(self, ticket_channel_id: int) -> StaffTicketView:
        view = self.staff_views.get(ticket_channel_id)
        if view is None:
            view = StaffTicketView(self, ticket_channel_id)
            self.staff_views[ticket_channel_id] = view
            self.add_view(view)
        return view

    def set_approval_view(self, request_id: int) -> SetApprovalView:
        view = self.set_approval_views.get(request_id)
        if view is None:
            view = SetApprovalView(self, request_id)
            self.set_approval_views[request_id] = view
            self.add_view(view)
        return view

    def return_approval_view(self, request_id: int) -> ReturnApprovalView:
        view = self.return_approval_views.get(request_id)
        if view is None:
            view = ReturnApprovalView(self, request_id)
            self.return_approval_views[request_id] = view
            self.add_view(view)
        return view

    @staticmethod
    def message_custom_ids(message: discord.Message) -> set[str]:
        return {
            component.custom_id
            for row in message.components
            for component in row.children
            if component.custom_id
        }

    @classmethod
    def is_ticket_control_message(cls, message: discord.Message) -> bool:
        ids = cls.message_custom_ids(message)
        return bool(ids & TICKET_IDS or any(
            custom_id.startswith(prefix)
            for custom_id in ids
            for prefix in TICKET_CONTROL_PREFIXES
        ))

    async def sync_ticket_control_panels(self) -> None:
        if self.guild is None or self.user is None:
            return
        for ticket in self.database.open_tickets():
            channel = self.guild.get_channel(int(ticket["channel_id"]))
            if not isinstance(channel, discord.TextChannel):
                continue
            staff_custom_id = f"peace_staff_ticket_claim_{channel.id}"
            staff_message = None
            try:
                async for message in channel.history(limit=100):
                    if message.author.id != self.user.id:
                        continue
                    custom_ids = self.message_custom_ids(message)
                    if any(custom_id.startswith("peace_ticket_owner_") for custom_id in custom_ids):
                        await message.delete()
                        continue
                    if staff_custom_id in custom_ids:
                        staff_message = message
                if staff_message is None:
                    await channel.send(
                        embed=self.ticket_staff_embed(ticket),
                        view=self.staff_view(channel.id),
                        allowed_mentions=discord.AllowedMentions.none(),
                    )
                else:
                    await staff_message.edit(
                        content=None,
                        embed=self.ticket_staff_embed(ticket),
                        view=self.staff_view(channel.id),
                    )
            except (discord.Forbidden, discord.HTTPException):
                log.info("Não foi possível sincronizar os controles do ticket %s", channel.id)

    async def cleanup_staff_ticket_panels(self) -> None:
        if self.guild is None or self.user is None or self.settings.staff_control_channel_id is None:
            return
        channel = self.guild.get_channel(self.settings.staff_control_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            async for message in channel.history(limit=100):
                if message.author.id != self.user.id:
                    continue
                title = message.embeds[0].title if message.embeds else ""
                footer = message.embeds[0].footer.text if message.embeds else ""
                if title == "Controles privados da staff" or footer.startswith("ticket:"):
                    await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não foi possível limpar os painéis antigos do staff-only")

    def set_panel_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="◈ Request a Peace set",
            color=0x101827,
        )
        embed.add_field(
            name="1 · ESCOLHER",
            value="Selecione o caminho da entrevista.",
            inline=True,
        )
        embed.add_field(
            name="2 · PREENCHER",
            value="Informe dados corretos e completos.",
            inline=True,
        )
        embed.add_field(
            name="3 · ANALISAR",
            value="A equipe revisa o pedido.",
            inline=True,
        )
        embed.set_image(url=f"attachment://{SET_PANEL_ASSET}")
        return embed

    def set_panel_details_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title="Como funciona",
            description=(
                "Escolha uma entrevista e preencha os dados solicitados com atenção. "
                "A equipe usa essas informações para analisar a entrada correta em cada área."
            ),
            color=0x101827,
        )
        embed.add_field(
            name="Regra",
            value="Uma nova entrada de Player não é aceita para quem já possui Peace.",
            inline=False,
        )
        return embed

    def set_panel_embeds(self) -> list[discord.Embed]:
        return [self.set_panel_embed(), self.set_panel_details_embed()]

    @staticmethod
    def support_panel_embed() -> discord.Embed:
        embed = discord.Embed(
            title="◈ Atendimento Peace",
            color=0x101827,
        )
        embed.add_field(
            name="1 · ESCOLHER",
            value="Selecione o assunto do atendimento.",
            inline=True,
        )
        embed.add_field(
            name="2 · DESCREVER",
            value="Explique o caso com os dados necessários.",
            inline=True,
        )
        embed.add_field(
            name="3 · ACOMPANHAR",
            value="A equipe assume o ticket quando necessário.",
            inline=True,
        )
        embed.set_image(url=f"attachment://{TICKET_PANEL_ASSET}")
        return embed

    @staticmethod
    def support_panel_details_embed() -> discord.Embed:
        embed = discord.Embed(
            title="Como funciona",
            description=(
                "Abra um ticket, escolha a categoria correta e descreva o que precisa. "
                "A conversa fica organizada em um atendimento próprio."
            ),
            color=0x101827,
        )
        embed.add_field(
            name="O que faz",
            value="Cria um espaço privado para a equipe acompanhar e resolver seu caso.",
            inline=True,
        )
        embed.add_field(
            name="Por que existe",
            value="Evita pedidos espalhados e mantém cada atendimento com seu contexto.",
            inline=True,
        )
        return embed

    @classmethod
    def support_panel_embeds(cls) -> list[discord.Embed]:
        return [cls.support_panel_embed(), cls.support_panel_details_embed()]

    @staticmethod
    def operations_panel_embed() -> discord.Embed:
        embed = discord.Embed(
            title="◷ Operações Peace",
            color=0x101827,
        )
        embed.add_field(
            name="1 · INICIAR",
            value="Use ◷ Ponto ao começar suas atividades.",
            inline=True,
        )
        embed.add_field(
            name="2 · ACOMPANHAR",
            value="Acesse os recursos internos da Peace Tools.",
            inline=True,
        )
        embed.add_field(
            name="3 · FINALIZAR",
            value="Encerre o ponto ao terminar.",
            inline=True,
        )
        embed.set_image(url=f"attachment://{OPERATIONS_PANEL_ASSET}")
        return embed

    @staticmethod
    def operations_panel_details_embed() -> discord.Embed:
        embed = discord.Embed(
            title="Como funciona",
            description=(
                "Registre o início do trabalho com ◷ Ponto e use × Encerrar ponto "
                "quando sair. O site continua disponível pelo botão ao lado."
            ),
            color=0x101827,
        )
        embed.add_field(
            name="O que faz",
            value="Registra o período ativo e envia os marcos operacionais para os logs.",
            inline=True,
        )
        embed.add_field(
            name="Por que existe",
            value="Mantém o histórico da equipe organizado e auditável.",
            inline=True,
        )
        return embed

    @classmethod
    def operations_panel_embeds(cls) -> list[discord.Embed]:
        return [cls.operations_panel_embed(), cls.operations_panel_details_embed()]

    @staticmethod
    def welcome_embed() -> discord.Embed:
        embed = discord.Embed(
            title="◈ Bem-vindo à Peace",
            color=0x101827,
        )
        embed.add_field(
            name="1 · LER",
            value="Comece pelas regras do servidor.",
            inline=True,
        )
        embed.add_field(
            name="2 · ENTRAR",
            value="Peça seu set quando estiver pronto.",
            inline=True,
        )
        embed.add_field(
            name="3 · FALAR",
            value="Abra um atendimento se precisar de ajuda.",
            inline=True,
        )
        embed.set_image(url=f"attachment://{WELCOME_ASSET}")
        return embed

    @staticmethod
    def welcome_details_embed() -> discord.Embed:
        embed = discord.Embed(
            title="Como funciona",
            description=(
                "Use os botões para seguir o primeiro acesso na ordem certa: leia as regras, "
                "faça sua entrevista e procure a equipe quando precisar."
            ),
            color=0x101827,
        )
        embed.add_field(
            name="O que faz",
            value="Reúne em um só lugar os caminhos principais para começar na comunidade.",
            inline=True,
        )
        embed.add_field(
            name="Por que existe",
            value="Deixa o acesso inicial claro e reduz dúvidas antes da entrada.",
            inline=True,
        )
        return embed

    @classmethod
    def welcome_panel_embeds(cls) -> list[discord.Embed]:
        return [cls.welcome_embed(), cls.welcome_details_embed()]

    async def sync_welcome_panel(self) -> None:
        if self.guild is None or self.user is None or self.settings.welcome_channel_id is None:
            return
        channel = self.guild.get_channel(self.settings.welcome_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        view = WelcomeView(self)
        try:
            matches: list[discord.Message] = []
            bot_messages: list[discord.Message] = []
            async for message in channel.history(limit=50):
                if message.author.id != self.user.id:
                    continue
                bot_messages.append(message)
                if any(
                    attachment.filename in {WELCOME_ASSET, WELCOME_LEGACY_ASSET}
                    for attachment in message.attachments
                ):
                    matches.append(message)
            if not matches:
                for old_message in bot_messages:
                    await old_message.delete()
                await channel.send(
                    embeds=self.welcome_panel_embeds(),
                    view=view,
                    file=asset(WELCOME_ASSET),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            else:
                bot_message = matches[0]
                payload = self.panel_embed_payload(self.welcome_panel_embeds())
                await bot_message.edit(
                    content=None,
                    **payload,
                    view=view,
                    attachments=[asset(WELCOME_ASSET)],
                )
                for duplicate in matches[1:]:
                    await duplicate.delete()
                for old_message in bot_messages:
                    if old_message.id != bot_message.id and old_message.id not in {item.id for item in matches[1:]}:
                        await old_message.delete()
            async for message in channel.history(limit=50):
                if (
                    message.author.id == self.settings.founder_user_id
                    and len(message.attachments) == 1
                    and message.attachments[0].filename == "content.png"
                ):
                    await message.delete()
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não foi possível sincronizar o painel de boas-vindas")

    async def sync_reception_visibility(self) -> None:
        """Channel visibility is operator-managed; the bot does not rewrite it."""
        return

    async def sync_closed_ticket_visibility(self) -> None:
        """Closed-ticket visibility is operator-managed; the bot does not rewrite it."""
        return

    async def sync_ticket_names(self) -> None:
        """Corrige nomes antigos e usa o ID incremental do ticket, não o ID do usuário."""
        if self.guild is None:
            return
        for ticket in self.database.all_tickets():
            channel = self.guild.get_channel(int(ticket["channel_id"]))
            if not isinstance(channel, discord.TextChannel):
                continue
            owner = await self.member(self.guild, int(ticket["owner_user_id"]))
            desired = self.ticket_channel_name(owner, int(ticket["id"]))
            if channel.name == desired:
                continue
            try:
                await channel.edit(name=desired, reason="Padronização do ID do ticket Peace")
            except (discord.Forbidden, discord.HTTPException):
                log.info("Não foi possível renomear o ticket %s", ticket["id"])

    @staticmethod
    def tag_prefix(member: discord.Member, settings: Settings) -> str | None:
        visual_prefix = prefix_for_roles(
            user_id=member.id,
            role_names=(role.name for role in member.roles),
            founder_user_id=settings.founder_user_id,
            founder_role_names=FOUNDER_ROLE_NAMES,
            default=None,
            role_positions=role_position_map(member.roles),
            role_hoist=role_hoist_map(member.roles),
        )
        if visual_prefix is not None:
            return visual_prefix
        if role_member(member, settings.peace_role_id):
            return "N"
        return None

    @staticmethod
    def peace_nickname(
        member: discord.Member,
        *,
        role_names: list[str],
        peace_id: int,
        settings: Settings,
        role_positions: dict[str, int] | None = None,
        role_hoist: dict[str, bool] | None = None,
    ) -> str | None:
        visual_prefix = prefix_for_roles(
            user_id=member.id,
            role_names=role_names,
            founder_user_id=settings.founder_user_id,
            founder_role_names=FOUNDER_ROLE_NAMES,
            default=None,
            role_positions=role_positions,
            role_hoist=role_hoist,
        )
        has_peace = role_member(member, settings.peace_role_id) or any(
            str(name).casefold().strip() == "peace"
            for name in role_names
        )
        prefix = visual_prefix or ("N" if has_peace else None)
        if prefix is None:
            return None
        current = member.nick or member.display_name or member.name
        match = re.match(r"^[A-Z]\s*⎰\s*(.+?)\s+(\d{1,8})$", current)
        if match:
            base = match.group(1).strip()
        else:
            # Older Peace nicknames could contain the numeric ID without the
            # visual prefix. Preserve the alias when repairing those names so
            # the backfill does not produce e.g. ``S ⎰ Name 24 24``.
            legacy_match = re.match(r"^(.+?)\s+\d{1,8}$", current)
            base = (
                legacy_match.group(1).strip()
                if legacy_match and has_peace
                else current.strip()
            )
        base = re.sub(r"\s+", " ", base)[:20].strip() or member.name[:20]
        return f"{prefix} ⎰ {base} {peace_id}"[:32]

    async def sync_member_tag(
        self,
        member: discord.Member,
        *,
        role_names: list[str] | None = None,
        peace_id: int | None = None,
        strict: bool = False,
        stats: dict[str, int] | None = None,
    ) -> bool:
        if member.bot:
            if stats is not None:
                stats["ignored"] = stats.get("ignored", 0) + 1
            return True
        effective_role_names = role_names or [role.name for role in member.roles]
        effective_role_positions = role_position_map(member.roles)
        effective_role_hoist = role_hoist_map(member.roles)
        has_peace = role_member(member, self.settings.peace_role_id) or any(
            str(name).casefold().strip() == "peace"
            for name in effective_role_names
        )
        record = self.database.get_member(member.id)
        if peace_id is not None:
            resolved_peace_id = peace_id
        elif record is None and has_peace:
            resolved_peace_id = self.database.ensure_runtime_member(
                discord_user_id=member.id,
                username=member.name,
                nickname=member.nick,
                role_ids=[role.id for role in member.roles],
                role_names=effective_role_names,
                founder_id=self.settings.founder_user_id,
                role_positions=effective_role_positions,
                role_hoist=effective_role_hoist,
            )
        else:
            resolved_peace_id = int(record["peace_id"]) if record is not None else int(str(member.id)[-4:])
        if record is not None and role_names is None:
            self.database.ensure_runtime_member(
                discord_user_id=member.id,
                username=member.name,
                nickname=member.nick,
                role_ids=[role.id for role in member.roles],
                role_names=effective_role_names,
                founder_id=self.settings.founder_user_id,
                role_positions=effective_role_positions,
                role_hoist=effective_role_hoist,
            )
        desired = self.peace_nickname(
            member,
            role_names=effective_role_names,
            peace_id=resolved_peace_id,
            settings=self.settings,
            role_positions=effective_role_positions,
            role_hoist=effective_role_hoist,
        )
        if desired is None:
            if stats is not None:
                stats["not_applicable"] = stats.get("not_applicable", 0) + 1
            return True
        if member.nick == desired:
            if stats is not None:
                stats["already_correct"] = stats.get("already_correct", 0) + 1
            return True
        try:
            await member.edit(nick=desired, reason="Padronização da tag Peace")
            self.database.update_nickname(member.id, desired)
            if stats is not None:
                stats["updated"] = stats.get("updated", 0) + 1
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não foi possível atualizar a tag de %s", member.id)
            if stats is not None:
                stats["failed"] = stats.get("failed", 0) + 1
            if strict:
                raise
            return False
        return True

    async def members_for_tag_sync(self) -> tuple[list[discord.Member], bool]:
        """Return the complete member view used by the nickname backfill.

        ``Guild.members`` is a cache and can be incomplete after a restart or
        when the gateway has not delivered every member chunk yet. The REST
        member iterator is the authoritative fallback for this reconciliation;
        cached members remain useful when Discord denies the fetch.
        """
        if self.guild is None:
            return [], False
        members_by_id = {
            member.id: member
            for member in getattr(self.guild, "members", ())
            if getattr(member, "id", None) is not None
        }
        member_count = getattr(self.guild, "member_count", None)
        if getattr(self.guild, "chunked", False) or (
            isinstance(member_count, int) and len(members_by_id) >= member_count
        ):
            return list(members_by_id.values()), False
        fetch_members = getattr(self.guild, "fetch_members", None)
        if not callable(fetch_members):
            return list(members_by_id.values()), False
        try:
            async for member in fetch_members(limit=None):
                members_by_id[member.id] = member
        except (discord.Forbidden, discord.HTTPException):
            log.warning(
                "Não foi possível buscar todos os membros para a sincronização de tags; "
                "usando o cache (%s membros)",
                len(members_by_id),
            )
            return list(members_by_id.values()), False
        return list(members_by_id.values()), True

    async def sync_peace_tags(self) -> dict[str, int | bool]:
        if self.guild is None:
            return {
                "seen": 0,
                "updated": 0,
                "already_correct": 0,
                "ignored": 0,
                "not_applicable": 0,
                "returned": 0,
                "failed": 0,
                "fetched": False,
            }
        members, fetched = await self.members_for_tag_sync()
        counters: dict[str, int] = {
            "seen": len(members),
            "updated": 0,
            "already_correct": 0,
            "ignored": 0,
            "not_applicable": 0,
            "returned": 0,
            "failed": 0,
        }
        for member in members:
            if await self.ensure_return_request(member):
                counters["returned"] += 1
                reservation = self.database.reserved_peace_id_for_user(member.id)
                has_peace = role_member(member, self.settings.peace_role_id) or any(
                    str(role.name).casefold().strip() == "peace"
                    for role in getattr(member, "roles", ())
                )
                if reservation is not None and has_peace:
                    # A pending return has no active ``members`` row by design.
                    # Repair the live nickname with the reserved ID, but never
                    # recreate the active Peace record before review approval.
                    await self.sync_member_tag(
                        member,
                        peace_id=int(reservation["peace_id"]),
                        stats=counters,
                    )
                continue
            await self.sync_member_tag(member, stats=counters)
        summary: dict[str, int | bool] = {**counters, "fetched": fetched}
        log.info(
            "Sincronização de tags Peace concluída: %s vistos, %s atualizados, "
            "%s já corretos, %s sem tag, %s retornos pendentes, %s falhas "
            "(busca completa=%s)",
            counters["seen"],
            counters["updated"],
            counters["already_correct"],
            counters["not_applicable"],
            counters["returned"],
            counters["failed"],
            "sim" if fetched else "não",
        )
        return summary

    async def sync_missing_peace_ids(self) -> None:
        if self.guild is None:
            return
        current_ids = {member.id for member in self.guild.members}
        current_peace_ids = {
            member.id
            for member in self.guild.members
            if role_member(member, self.settings.peace_role_id)
        }
        current_peace_ids.update(
            user_id
            for user_id in self.database.approved_return_user_ids()
            if user_id in current_ids
        )
        reserved = self.database.reserve_missing_peace_members(
            current_user_ids=current_ids,
            peace_role_id=self.settings.peace_role_id,
            current_peace_user_ids=current_peace_ids,
        )
        if reserved:
            log.info("IDs Peace reservados após auditoria: %s", len(reserved))

    async def ensure_return_request(self, member: discord.Member) -> bool:
        if member.bot:
            return False
        reservation = self.database.reserved_peace_id_for_user(member.id)
        if reservation is None:
            return False
        latest = self.database.latest_return_request_for_user(member.id)
        if latest is not None and latest["status"] == "rejected":
            return True
        request, created = self.database.get_or_create_return_request(
            discord_user_id=member.id,
            old_peace_id=int(reservation["peace_id"]),
            loss_reason=str(reservation["release_reason"] or "motivo não registrado"),
            loss_actor_id=reservation["release_actor_id"],
        )
        if created:
            await self.publish_return_request(request)
        return True

    @staticmethod
    def return_request_embed(request) -> discord.Embed:
        actor_id = request["loss_actor_id"]
        actor = mention(actor_id) if actor_id else "não identificado"
        embed = discord.Embed(
            title="Retorno Peace pendente · scan-only",
            description=(
                f"**Membro:** {mention(request['discord_user_id'])}\n"
                f"**ID reservado:** `{int(request['old_peace_id'])}`\n\n"
                f"**Motivo registrado:** {redact(str(request['loss_reason'] or 'não informado'), limit=500)}\n"
                f"**Quem retirou:** {actor}\n"
                f"**Registrado em:** {redact(str(request['created_at']), limit=40)}\n\n"
                "Este retorno foi enviado diretamente ao scan-only. Não refaça a entrevista de Player. "
                "Use **Liberar ID** somente após conferir o histórico e a situação atual. A ação libera o ID antigo "
                "para o pool e registra um novo ID para este membro."
            ),
            color=0xF1C40F,
        )
        embed.set_footer(text=f"peace_return:{request['id']}")
        return embed

    async def stored_return_panel_message(
        self,
        channel: discord.TextChannel,
        request,
    ) -> discord.Message | None:
        message_id = request["message_id"]
        if not message_id or self.user is None:
            return None
        try:
            message = await channel.fetch_message(int(message_id))
        except discord.NotFound:
            return None
        if message.author.id != self.user.id:
            return None
        marker = f"peace_return_release_{request['id']}"
        return message if marker in self.message_custom_ids(message) else None

    async def publish_return_request(self, request) -> None:
        if self.guild is None or self.settings.scan_channel_id is None:
            return
        channel = self.guild.get_channel(self.settings.scan_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            async with self.return_mutation_lock(int(request["id"])):
                current = self.database.return_request(int(request["id"])) or request
                if current["status"] != "pending":
                    return
                existing = await self.stored_return_panel_message(channel, current)
                if existing is not None:
                    await existing.edit(
                        embed=self.return_request_embed(current),
                        view=self.return_approval_view(int(current["id"])),
                    )
                    return
                message = await channel.send(
                    embed=self.return_request_embed(current),
                    view=self.return_approval_view(int(current["id"])),
                    allowed_mentions=discord.AllowedMentions(users=True),
                )
                self.database.set_return_request_message(int(current["id"]), message.id)
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Não foi possível publicar retorno Peace no scan-only")

    async def sync_pending_return_panels(self) -> None:
        if self.guild is None or self.user is None or self.settings.scan_channel_id is None:
            return
        channel = self.guild.get_channel(self.settings.scan_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        for request in self.database.pending_return_requests():
            try:
                marker = f"peace_return_release_{request['id']}"
                matches: list[discord.Message] = []
                stored = await self.stored_return_panel_message(channel, request)
                if stored is not None:
                    matches.append(stored)
                async for message in channel.history(limit=100):
                    if (
                        message.author.id == self.user.id
                        and message.id != getattr(stored, "id", None)
                        and marker in self.message_custom_ids(message)
                    ):
                        matches.append(message)
                if matches:
                    await matches[0].edit(
                        embed=self.return_request_embed(request),
                        view=self.return_approval_view(int(request["id"])),
                    )
                    for duplicate in matches[1:]:
                        await duplicate.delete()
                else:
                    await self.publish_return_request(request)
            except (discord.Forbidden, discord.HTTPException, ValueError, TypeError):
                log.info("Não foi possível sincronizar o retorno Peace %s", request["id"])

    async def ensure_booster_space(self, member: discord.Member) -> None:
        if self.guild is None or member.bot or self.settings.booster_role_id is None or self.settings.private_call_category_id is None:
            return
        if not role_member(member, self.settings.booster_role_id):
            return
        existing = self.database.booster_space_for_owner(member.id)
        if existing is not None:
            private_role = self.guild.get_role(int(existing["role_id"]))
            voice = self.guild.get_channel(int(existing["voice_channel_id"]))
            if private_role is not None and isinstance(voice, discord.VoiceChannel):
                if private_role not in member.roles:
                    try:
                        await member.add_roles(private_role, reason="Booster recebeu sua área privada")
                    except (discord.Forbidden, discord.HTTPException):
                        log.info("Não consegui devolver o cargo privado ao booster %s", member.id)
                return
        category = self.guild.get_channel(self.settings.private_call_category_id)
        booster_role = self.guild.get_role(self.settings.booster_role_id)
        if not isinstance(category, discord.CategoryChannel) or booster_role is None:
            return
        try:
            private_role = await self.guild.create_role(
                name=f"Booster・{clean_name(member.name)}"[:100],
                hoist=False,
                mentionable=True,
                reason="Área privada criada para booster Peace",
            )
            voice = await self.guild.create_voice_channel(
                name=f"├🎧・{member.name}"[:100],
                category=category,
                reason="Call privada automática de booster Peace",
            )
            ordered = sorted(category.voice_channels, key=lambda channel: channel.position)
            siblings = [channel for channel in ordered if channel.id != voice.id]
            if len(siblings) >= 2:
                await voice.edit(position=siblings[0].position + 1, reason="Posicionar call privada entre as calls existentes")
            await member.add_roles(private_role, reason="Cargo privado automático do booster")
            self.database.save_booster_space(member.id, private_role.id, voice.id)
            await member.send(
                f"Sua área privada da Peace está pronta: cargo {private_role.mention} e call {voice.mention}. "
                "Use os comandos de booster para adicionar/remover pessoas e puxá-las para a call."
            )
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Não consegui criar a área privada do booster %s", member.id)

    async def sync_booster_spaces(self) -> None:
        if self.guild is None or self.settings.booster_role_id is None:
            return
        for member in self.guild.members:
            await self.ensure_booster_space(member)

    def booster_space(self, owner: discord.Member):
        space = self.database.booster_space_for_owner(owner.id)
        if space is None or self.guild is None:
            return None, None
        private_role = self.guild.get_role(int(space["role_id"]))
        voice = self.guild.get_channel(int(space["voice_channel_id"]))
        if not isinstance(voice, discord.VoiceChannel):
            voice = None
        return private_role, voice

    async def reconcile_visitor_role(
        self,
        member: discord.Member,
        *,
        prefer_reverification: bool = False,
    ) -> None:
        """Keep entry roles consistent and allow an explicit reverification reset."""
        visitor = role_named(
            member.guild,
            getattr(self.settings, "visitor_role_id", None),
            "Visitor",
        )
        not_verified = role_named(
            member.guild,
            getattr(self.settings, "not_verified_role_id", None),
            NOT_VERIFIED_ROLE_NAME,
            "Não verificado",
            "Nao verificado",
        )
        if visitor is None and not_verified is None:
            return
        try:
            status_roles = [
                role for role in (visitor, not_verified)
                if role is not None and role in member.roles
            ]
            if member.bot:
                if status_roles:
                    await member.remove_roles(
                        *status_roles,
                        reason="Contas de bot não usam Visitor ou Not Verified",
                    )
                return
            has_peace = role_member(member, self.settings.peace_role_id)
            if has_peace:
                if status_roles:
                    await member.remove_roles(
                        *status_roles,
                        reason="Peace member não é visitante nem Not Verified",
                    )
            elif visitor is not None and visitor in member.roles:
                if not_verified is not None and not_verified in member.roles:
                    if prefer_reverification:
                        await member.remove_roles(
                            visitor,
                            reason="Not Verified reaplicado para exigir nova verificação",
                        )
                    else:
                        await member.remove_roles(not_verified, reason="Visitor já está verificado")
            elif not_verified is not None and not_verified not in member.roles:
                await member.add_roles(
                    not_verified,
                    reason="Entrada exige verificação antes de Visitor",
                )
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não foi possível sincronizar os cargos de entrada para %s", member.id)

    async def sync_visitor_roles(self) -> None:
        if self.guild is None:
            return
        for member in self.guild.members:
            await self.reconcile_visitor_role(member)

    def set_approval_embed(self, request) -> discord.Embed:
        selected = mention(request["recruiter_user_id"]) if request["recruiter_user_id"] else "qualquer Staff ou Management"
        embed = discord.Embed(
            title="Set pendente de aprovação",
            description=(
                f"**Membro:** {mention(request['discord_user_id'])}\n"
                f"**Apelido in-game:** `{redact(str(request['in_game_username']), limit=80)}`\n"
                f"**Onde conheceu:** {redact(str(request['source']), limit=40)}\n"
                f"**Reviewer selecionado:** {selected}\n\n"
                "Confira os dados e aprove somente se o recrutamento estiver confirmado."
            ),
            color=0x5865F2,
        )
        embed.add_field(name="Telefone in-game", value=f"`{redact(str(request['telefone_in_game']), limit=100)}`", inline=True)
        embed.add_field(name="RG in-game", value=f"`{redact(str(request['rg_in_game']), limit=100)}`", inline=True)
        embed.set_footer(text=f"set_request:{request['id']}")
        return embed

    @staticmethod
    def set_approved_dm_embed(request, recruiter: discord.Member, peace_id: int) -> discord.Embed:
        """Build the private welcome card sent after a Player set is approved."""
        approver_name = getattr(recruiter, "display_name", None) or getattr(recruiter, "name", "Staff")
        avatar = getattr(getattr(recruiter, "display_avatar", None), "url", None)
        embed = discord.Embed(
            title="✓ Set aprovado · bem-vindo à Peace",
            description=(
                f"Seu acesso de **Player** foi liberado, {redact(str(request['in_game_username']), limit=80)}.\n\n"
                "O time aprovou sua entrada e seu vínculo já está ativo no servidor. "
                "Leia as regras, acompanhe os avisos e participe da comunidade."
            ),
            color=0x2B2D42,
        )
        embed.add_field(name="Seu ID Peace", value=f"`{peace_id}`", inline=True)
        embed.add_field(name="Aprovado por", value=redact(str(approver_name), limit=80), inline=True)
        embed.add_field(
            name="Próximo passo",
            value="Leia as regras e siga as orientações dos canais de entrada. Se precisar, abra um ticket de suporte.",
            inline=False,
        )
        if avatar:
            embed.set_thumbnail(url=str(avatar))
        embed.set_footer(text="Peace · Player set")
        return embed

    async def sync_pending_set_panels(self) -> None:
        if self.guild is None or self.user is None or self.settings.scan_channel_id is None:
            return
        channel = self.guild.get_channel(self.settings.scan_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            for request in self.database.pending_set_requests():
                marker = f"peace_set_approve_{request['id']}"
                found = None
                async for message in channel.history(limit=100):
                    if message.author.id == self.user.id and marker in self.message_custom_ids(message):
                        found = message
                        break
                if found is None:
                    await channel.send(
                        embed=self.set_approval_embed(request),
                        view=self.set_approval_view(int(request["id"])),
                        allowed_mentions=discord.AllowedMentions(users=True),
                    )
                else:
                    await found.edit(embed=self.set_approval_embed(request), view=self.set_approval_view(int(request["id"])))
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não foi possível sincronizar pedidos de set pendentes")

    def developer_approval_view(self, request_id: int) -> DeveloperApprovalView:
        view = self.developer_approval_views.get(request_id)
        if view is None:
            view = DeveloperApprovalView(self, request_id)
            self.developer_approval_views[request_id] = view
        return view

    @staticmethod
    def developer_request_embed(request) -> discord.Embed:
        if request["status"] == "pending":
            decision_instruction = (
                "Esta é a primeira etapa. Confira o currículo e use "
                "**Aprovar entrevista** para encaminhar o candidato à entrevista manual na call de suporte. "
                "Use **Recusar candidatura** se ele não deve seguir."
            )
        else:
            decision_instruction = (
                "A entrevista manual na call de suporte deve estar concluída. O candidato foi bem? "
                "Ele fará diferença no time? Use **Aprovar como integrante** para conceder o cargo Dev "
                "e liberar o acesso da Central. Use **Recusar candidatura** quando a decisão for negativa."
            )
        embed = discord.Embed(
            title=(
                "Candidatura Dev · aprovar entrevista"
                if request["status"] == "pending"
                else "Candidatura Dev · decisão final"
            ),
            description=(
                f"**Candidato:** {mention(request['discord_user_id'])}\n"
                f"**Nome real:** `{redact(str(request['full_name']), limit=100)}`\n"
                f"**Apelido:** `{redact(str(request['nickname']), limit=60)}`\n"
                f"**Área:** `{redact(str(request['area']), limit=60)}`\n\n"
                f"**Motivação:** {redact(str(request['motivation']), limit=900)}\n\n"
                f"**Tempo de especialização:** {redact(str(request['specialization_time']), limit=180)}\n"
                f"**Onde atuou/praticou:** {redact(str(request['previous_experience']), limit=1100)}\n"
                f"**Portfólio:** {redact(str(request['portfolio']) or 'não informado', limit=300)}\n\n"
                f"{decision_instruction}"
            ),
            color=0x5865F2,
        )
        embed.set_footer(text=f"developer_request:{request['id']}")
        return embed

    async def send_developer_interview_notice(self, request) -> bool:
        if self.guild is None:
            return False
        member = await self.member(self.guild, int(request["discord_user_id"]))
        if member is None:
            return False
        try:
            await member.send(
                "✅ Sua candidatura foi aprovada para a etapa de entrevista manual!\n\n"
                f"Área: **{redact(str(request['area']), limit=60)}**\n"
                "Procure a call de suporte para fazer a entrevista. Depois dela, a equipe decidirá se você entra como integrante do time."
            )
        except (discord.Forbidden, discord.HTTPException):
            log.info("DM fechada para convite de entrevista dev %s", request["id"])
            return False
        return True

    async def send_developer_decision_notice(self, request, *, peace_id: int) -> bool:
        if self.guild is None:
            return False
        member = await self.member(self.guild, int(request["discord_user_id"]))
        if member is None:
            return False
        try:
            await member.send(
                "✅ Você foi aprovado como integrante do time de desenvolvimento da Peace!\n\n"
                f"Área: **{redact(str(request['area']), limit=60)}**\n"
                f"Seu cargo Dev foi aplicado e seu ID Peace é `{peace_id}`.\n"
                    "Entre no painel da Central com esse ID para solicitar o código de acesso no Discord."
            )
        except (discord.Forbidden, discord.HTTPException):
            log.info("DM fechada para decisão da candidatura dev %s", request["id"])
            return False
        return True

    async def send_developer_rejection_notice(self, request, *, after_interview: bool) -> bool:
        if self.guild is None:
            return False
        member = await self.member(self.guild, int(request["discord_user_id"]))
        if member is None:
            return False
        try:
            if after_interview:
                await member.send(
                    "Sua candidatura para o time de desenvolvimento não foi aprovada após a entrevista manual.\n\n"
                    "Se quiser entender os próximos passos, procure a staff."
                )
            else:
                await member.send(
                    "Sua candidatura não foi aprovada para a etapa de entrevista manual.\n\n"
                    "Se quiser entender os próximos passos, procure a staff."
                )
        except (discord.Forbidden, discord.HTTPException):
            log.info("DM fechada para recusa da candidatura dev %s", request["id"])
            return False
        return True

    async def sync_pending_developer_panels(self) -> None:
        if self.guild is None or self.user is None or self.settings.scan_channel_id is None:
            return
        channel = self.guild.get_channel(self.settings.scan_channel_id)
        if not isinstance(channel, discord.TextChannel):
            return
        try:
            for request in self.database.pending_developer_requests():
                marker = f"peace_dev_approve_{request['id']}"
                found = None
                async for message in channel.history(limit=100):
                    if message.author.id == self.user.id and marker in self.message_custom_ids(message):
                        found = message
                        break
                if found is None:
                    await channel.send(
                        embed=self.developer_request_embed(request),
                        view=self.developer_approval_view(int(request["id"])),
                        allowed_mentions=discord.AllowedMentions(users=True),
                    )
                else:
                    await found.edit(
                        embed=self.developer_request_embed(request),
                        view=self.developer_approval_view(int(request["id"])),
                    )
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não foi possível sincronizar entrevistas dev pendentes")

    @staticmethod
    def log_card(
        title: str,
        *,
        fields: tuple[tuple[str, str], ...],
        actor: discord.abc.User | None = None,
    ) -> discord.Embed:
        embed = discord.Embed(title=title, color=0x2B2D31)
        for name, value in fields:
            embed.add_field(name=name, value=value, inline=False)
        avatar = getattr(getattr(actor, "display_avatar", None), "url", None)
        if avatar:
            embed.set_thumbnail(url=str(avatar))
        embed.set_footer(text="Peace · logs")
        return embed

    async def send_log(
        self,
        title: str,
        *,
        fields: tuple[tuple[str, str], ...],
        actor: discord.abc.User | None = None,
    ) -> None:
        await self.send_to_channel(
            getattr(self.settings, "log_channel_id", None),
            embed=self.log_card(title, fields=fields, actor=actor),
        )

    async def send_to_channel(
        self,
        channel_id: int | None,
        *,
        content: str | None = None,
        embed: discord.Embed | None = None,
        view: discord.ui.View | None = None,
    ) -> None:
        if self.guild is None or channel_id is None:
            return
        channel = self.guild.get_channel(channel_id)
        if isinstance(channel, discord.TextChannel):
            try:
                await channel.send(
                    content=content,
                    embed=embed,
                    view=view,
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.HTTPException):
                log.exception("Falha ao escrever no canal %s", channel_id)

    async def close_ticket_channel(self, channel: discord.TextChannel, ticket, actor: discord.Member) -> None:
        if ticket["status"] != "open":
            return
        closed_ticket = self.database.close_ticket(channel.id, actor.id) or ticket
        self.database.record_iris_event(
            event_type="ticket_closed",
            scope="ticket",
            channel_id=channel.id,
            ticket_id=int(ticket["id"]),
            actor_user_id=actor.id,
        )
        self.stop_iris(channel.id)
        closed = self.guild.get_channel(self.settings.closed_ticket_category_id or 0) if self.guild else None
        if isinstance(closed, discord.CategoryChannel):
            await channel.edit(category=closed, reason="Ticket encerrado")
        await self.disable_ticket_controls(channel)
        if ticket["voice_channel_id"]:
            voice = self.guild.get_channel(int(ticket["voice_channel_id"])) if self.guild else None
            if isinstance(voice, discord.VoiceChannel):
                try:
                    await voice.delete(reason="Ticket encerrado")
                except discord.HTTPException:
                    log.info("Call do ticket %s já não estava disponível", channel.id)
        await channel.send(
            embed=self.ticket_closed_embed(closed_ticket, actor),
            allowed_mentions=discord.AllowedMentions(users=True),
        )

    def ticket_channel_name(self, owner: discord.Member | None, ticket_id: int) -> str:
        base = clean_name(owner.name if owner is not None else "ticket")
        return f"sup-{base}-t{ticket_id:04d}"[:90]

    async def member(self, guild: discord.Guild, user_id: int) -> discord.Member | None:
        member = guild.get_member(user_id)
        if member is not None:
            return member
        try:
            return await guild.fetch_member(user_id)
        except discord.NotFound:
            return None

    def mutation_lock(self, user_id: int) -> asyncio.Lock:
        """Serialize Discord/database mutations for one member in this process."""
        lock = self.member_mutation_locks.get(int(user_id))
        if lock is None:
            lock = asyncio.Lock()
            self.member_mutation_locks[int(user_id)] = lock
        return lock

    def return_mutation_lock(self, request_id: int) -> asyncio.Lock:
        lock = self.return_mutation_locks.get(int(request_id))
        if lock is None:
            lock = asyncio.Lock()
            self.return_mutation_locks[int(request_id)] = lock
        return lock

    async def authorized_dm_member(
        self,
        user_id: int,
        role_kind: str,
    ) -> discord.Member | None:
        guild = self.guild or self.get_guild(self.settings.guild_id)
        if guild is None:
            return None
        member = await self.member(guild, user_id)
        if member is None:
            return None
        if role_kind == "founder":
            return member if founder_role_member(member, self.settings) else None
        if role_kind == "management":
            return member if management_role_member(member, self.settings) else None
        return None

    async def delete_peace_candidates(self) -> list[discord.Member]:
        """Return selectable Peace members from the server, not from the DM context."""
        guild = self.guild or self.get_guild(self.settings.guild_id)
        if guild is None:
            return []

        members_by_id = {
            member.id: member
            for member in getattr(guild, "members", ())
        }
        fetch_members = getattr(guild, "fetch_members", None)
        if callable(fetch_members):
            try:
                fetched = [member async for member in fetch_members(limit=None)]
                members_by_id.update({member.id: member for member in fetched})
            except (discord.Forbidden, discord.HTTPException):
                log.info("Não consegui buscar todos os membros para o menu Founder; usando o cache")

        candidates = [
            member
            for member in members_by_id.values()
            if not member.bot
            and member.id != self.settings.founder_user_id
            and not founder_role_member(member, self.settings)
            and role_member(member, self.settings.peace_role_id)
        ]
        candidates.sort(key=lambda member: (member.display_name.casefold(), member.id))
        return candidates

    async def start_actions_for(self, user_id: int) -> tuple[str, ...]:
        """Return the internal actions available to a member in the bot's DM."""
        actions: list[str] = []
        if await self.authorized_dm_member(user_id, "founder") is not None:
            actions.append("delete_user")
        if await self.authorized_dm_member(user_id, "management") is not None:
            actions.append("announcement")
        return tuple(actions)

    async def send_dm_start_menu(self, user_id: int, channel: discord.abc.Messageable) -> bool:
        """Send the persistent DM fallback used when a client sends ``start`` as text."""
        actions = await self.start_actions_for(user_id)
        if not actions:
            return False
        await channel.send(
            "Escolha uma ação. Cada opção valida novamente o cargo antes de executar qualquer alteração.",
            view=StartActionView(self, user_id, actions),
            allowed_mentions=discord.AllowedMentions.none(),
        )
        return True

    def announcement_channel(self) -> discord.TextChannel | None:
        if self.guild is None:
            return None
        configured_id = getattr(self.settings, "announcement_channel_id", None)
        if configured_id is not None:
            configured = self.guild.get_channel(configured_id)
            if isinstance(configured, discord.TextChannel):
                return configured
        names = {name.casefold() for name in ANNOUNCEMENT_CHANNEL_NAMES}
        return discord.utils.find(
            lambda channel: isinstance(channel, discord.TextChannel)
            and (
                channel.name.casefold() in names
                or channel.name.casefold().endswith("・announcements")
                or channel.name.casefold().endswith("・avisos")
            ),
            self.guild.text_channels,
        )

    @staticmethod
    def announcement_embed(
        message: discord.Message,
        actor: discord.Member,
        *,
        image_filename: str | None = None,
    ) -> discord.Embed:
        """Render Management announcements as a neutral card, not loose text."""
        embed = discord.Embed(
            description=message.content or "\u200b",
            color=0x2B2D31,
        )
        avatar = getattr(getattr(actor, "display_avatar", None), "url", None)
        if avatar:
            embed.set_author(name="Peace · Avisos", icon_url=str(avatar))
        else:
            embed.set_author(name="Peace · Avisos")
        if image_filename:
            embed.set_image(url=f"attachment://{image_filename}")
        embed.set_footer(text=f"Publicado por {getattr(actor, 'display_name', actor.name)}")
        return embed

    async def collect_announcement(
        self,
        interaction: discord.Interaction,
        actor: discord.Member,
    ) -> None:
        """Collect one real DM message so Markdown and attachments stay intact."""
        if actor.id in self.announcement_collectors:
            await respond(interaction, "Já estou aguardando um aviso seu. Envie uma única mensagem no PV atual.")
            return
        if interaction.channel_id is None:
            await respond(interaction, "Não consegui identificar seu PV com o bot.")
            return
        self.announcement_collectors.add(actor.id)
        try:
            await interaction.response.send_message(
                "Envie agora a mensagem do aviso neste PV. Markdown, links e anexos serão preservados. "
                "Aguardo uma mensagem por até 5 minutos.",
                ephemeral=False,
            )
            prompt = None
            try:
                prompt = await interaction.original_response()
            except (discord.HTTPException, discord.NotFound):
                pass

            def check(message: discord.Message) -> bool:
                return message.author.id == actor.id and message.channel.id == interaction.channel_id

            try:
                message = await self.wait_for("message", timeout=300, check=check)
            except asyncio.TimeoutError:
                if prompt is not None:
                    try:
                        await prompt.edit(content="Tempo esgotado. Nenhum aviso foi publicado.")
                    except (discord.Forbidden, discord.HTTPException):
                        pass
                return
            if len(message.attachments) > MAX_ANNOUNCEMENT_ATTACHMENTS:
                if prompt is not None:
                    await prompt.edit(content=f"Envie no máximo {MAX_ANNOUNCEMENT_ATTACHMENTS} anexos. Nenhum aviso foi publicado.")
                return
            if any(attachment.size > MAX_ANNOUNCEMENT_ATTACHMENT_BYTES for attachment in message.attachments):
                if prompt is not None:
                    await prompt.edit(content="Um dos anexos ultrapassa o limite de 25 MB. Nenhum aviso foi publicado.")
                return
            if len(message.content) > 2000:
                if prompt is not None:
                    await prompt.edit(content="A mensagem ultrapassa o limite de 2.000 caracteres do Discord. Nenhum aviso foi publicado.")
                return
            if not message.content and not message.attachments:
                if prompt is not None:
                    await prompt.edit(content="A mensagem precisa conter texto ou pelo menos um anexo. Nenhum aviso foi publicado.")
                return
            current_actor = await self.authorized_dm_member(actor.id, "management")
            published = (
                "O cargo Management não está mais presente. Nenhum aviso foi publicado."
                if current_actor is None
                else await self.publish_announcement(message, current_actor)
            )
            if prompt is not None:
                try:
                    await prompt.edit(content=published)
                except (discord.Forbidden, discord.HTTPException):
                    await interaction.followup.send(published, ephemeral=True)
            else:
                await interaction.followup.send(published, ephemeral=True)
        finally:
            self.announcement_collectors.discard(actor.id)

    async def publish_announcement(
        self,
        message: discord.Message,
        actor: discord.Member,
    ) -> str:
        current_actor = await self.authorized_dm_member(actor.id, "management")
        if current_actor is None:
            return "O cargo Management não está mais presente. Nenhum aviso foi publicado."
        actor = current_actor
        channel = self.announcement_channel()
        if channel is None:
            return "Não encontrei o canal de avisos configurado. Nenhum aviso foi publicado."
        peace_role = self.guild.get_role(self.settings.peace_role_id)
        if peace_role is None:
            return "Não encontrei o cargo Peace configurado. Nenhum aviso foi publicado."
        files: list[discord.File] = []
        try:
            for attachment in message.attachments:
                files.append(await attachment.to_file(use_cached=True))
            image_filename = next(
                (
                    attachment.filename
                    for attachment in message.attachments
                    if str(getattr(attachment, "content_type", "") or "").startswith("image/")
                    or Path(attachment.filename).suffix.casefold() in {".png", ".jpg", ".jpeg", ".gif", ".webp"}
                ),
                None,
            )
            published = await channel.send(
                content=peace_role.mention,
                embed=self.announcement_embed(message, actor, image_filename=image_filename),
                files=files or [],
                allowed_mentions=discord.AllowedMentions(
                    everyone=False,
                    users=False,
                    roles=True,
                    replied_user=False,
                ),
            )
        except (discord.Forbidden, discord.HTTPException, OSError):
            log.exception("Falha ao publicar aviso no canal %s", channel.id)
            return "Não consegui publicar o aviso. Nenhuma confirmação de publicação foi registrada."
        jump_url = getattr(published, "jump_url", None) or (
            f"https://discord.com/channels/{self.settings.guild_id}/{channel.id}/{published.id}"
        )
        await self.send_log(
            "Aviso publicado",
            actor=actor,
            fields=(
                ("Usuário", actor.mention),
                ("Canal", channel.mention),
                ("Anexos", str(len(message.attachments))),
                ("Mensagem", jump_url),
                ("Horário", f"<t:{now_unix()}:F>"),
            ),
        )
        return f"✓ Aviso publicado em {channel.mention}: {jump_url}"

    async def apply_removed_member_state(
        self,
        target: discord.Member,
        *,
        peace_role: discord.Role,
        not_verified: discord.Role,
        bot_member: discord.Member,
        reason: str,
        reset_nickname: bool = True,
    ) -> None:
        """Apply the terminal Discord state for a manually removed member."""
        current_roles = list(target.roles)
        current_role_ids = {role.id for role in current_roles}
        if peace_role.id in current_role_ids and not role_is_manageable(peace_role, bot_member):
            raise RuntimeError("o cargo Peace está acima da hierarquia do bot")
        if not_verified.id not in current_role_ids and not role_is_manageable(not_verified, bot_member):
            raise RuntimeError("o cargo Not Verified está acima da hierarquia do bot")

        roles_to_remove = [
            role
            for role in current_roles
            if role.id != not_verified.id and role_is_manageable(role, bot_member)
        ]
        desired_roles = [role for role in current_roles if role not in roles_to_remove]
        if not_verified.id not in {role.id for role in desired_roles}:
            desired_roles.append(not_verified)

        nick = None if reset_nickname else target.nick
        role_changed = {role.id for role in desired_roles} != current_role_ids
        nick_changed = reset_nickname and target.nick is not None
        if not role_changed and not nick_changed:
            return
        # Clear the server nickname first. Discord can accept both fields in
        # one PATCH, but separating them makes the reset observable and lets a
        # retry finish safely if the role mutation is rate-limited.
        if nick_changed:
            await target.edit(nick=nick, reason=reason)
        if role_changed:
            await target.edit(roles=desired_roles, reason=reason)

    async def apply_return_member_state(
        self,
        target: discord.Member,
        *,
        peace_role: discord.Role,
        peace_id: int,
        reason: str,
    ) -> str:
        """Apply the complete Discord state for an approved direct return."""
        visitor_role = role_named(
            target.guild,
            getattr(self.settings, "visitor_role_id", None),
            "Visitor",
        )
        not_verified_role = role_named(
            target.guild,
            getattr(self.settings, "not_verified_role_id", None),
            NOT_VERIFIED_ROLE_NAME,
            "Não verificado",
            "Nao verificado",
        )
        current_roles = list(target.roles)
        removable_status_ids = {
            role.id
            for role in (visitor_role, not_verified_role)
            if role is not None and role.id in {item.id for item in current_roles}
        }
        for role in (visitor_role, not_verified_role):
            if role is not None and role.id in removable_status_ids and not role_is_manageable(role, target.guild.me):
                raise RuntimeError("um cargo de entrada está acima da hierarquia do bot")
        if peace_role.id not in {role.id for role in current_roles} and not role_is_manageable(peace_role, target.guild.me):
            raise RuntimeError("o cargo Peace está acima da hierarquia do bot")

        desired_roles = [role for role in current_roles if role.id not in removable_status_ids]
        if peace_role.id not in {role.id for role in desired_roles}:
            desired_roles.append(peace_role)
        desired_role_names = [role.name for role in desired_roles]
        desired_nick = self.peace_nickname(
            target,
            role_names=desired_role_names,
            peace_id=peace_id,
            settings=self.settings,
            role_positions=role_position_map(desired_roles),
            role_hoist=role_hoist_map(desired_roles),
        )
        if desired_nick is None:
            raise RuntimeError("não foi possível calcular o apelido Peace")
        if (
            {role.id for role in desired_roles} != {role.id for role in current_roles}
            or target.nick != desired_nick
        ):
            await target.edit(roles=desired_roles, nick=desired_nick, reason=reason)
        self.database.ensure_runtime_member(
            discord_user_id=target.id,
            username=target.name,
            nickname=desired_nick,
            role_ids=[role.id for role in desired_roles],
            role_names=desired_role_names,
            founder_id=self.settings.founder_user_id,
            role_positions=role_position_map(desired_roles),
            role_hoist=role_hoist_map(desired_roles),
        )
        return desired_nick

    async def sync_released_member_cleanup(self) -> None:
        """Repair manual deletions left half-applied by an older bot version."""
        if self.guild is None:
            return
        peace_role = self.guild.get_role(self.settings.peace_role_id)
        not_verified = role_named(
            self.guild,
            getattr(self.settings, "not_verified_role_id", None),
            NOT_VERIFIED_ROLE_NAME,
            "Não verificado",
            "Nao verificado",
        )
        if peace_role is None or not_verified is None or self.guild.me is None:
            return
        for release in self.database.manual_peace_releases_for_cleanup():
            target = await self.member(self.guild, int(release["released_from"]))
            if target is None or target.bot or self.database.get_member(target.id) is not None:
                continue
            async with self.mutation_lock(target.id):
                self.managed_peace_role_removals.add(target.id)
                try:
                    await self.apply_removed_member_state(
                        target,
                        peace_role=peace_role,
                        not_verified=not_verified,
                        bot_member=self.guild.me,
                        reason="Regularização de exclusão Peace antiga",
                    )
                except (discord.Forbidden, discord.HTTPException, RuntimeError):
                    log.info("Não foi possível regularizar a exclusão Peace antiga de %s", target.id)
                finally:
                    self.managed_peace_role_removals.discard(target.id)

    async def sync_approved_return_requests(self) -> None:
        """Converge approved return records whose Discord mutation was interrupted."""
        if self.guild is None:
            return
        peace_role = self.guild.get_role(self.settings.peace_role_id)
        if peace_role is None:
            return
        for request in self.database.approved_return_requests():
            target = await self.member(self.guild, int(request["discord_user_id"]))
            record = None if target is None or target.bot else self.database.get_member(target.id)
            if target is None or target.bot or record is None:
                continue
            if int(record["peace_id"]) != int(request["new_peace_id"]):
                log.info(
                    "Ignorando a reparação do retorno Peace %s: o membro já possui outro ID ativo",
                    request["id"],
                )
                continue
            try:
                await self.apply_return_member_state(
                    target,
                    peace_role=peace_role,
                    peace_id=int(request["new_peace_id"]),
                    reason="Regularização de retorno Peace aprovado",
                )
            except (discord.Forbidden, discord.HTTPException, RuntimeError):
                log.info("Não foi possível regularizar o retorno Peace %s", request["id"])

    async def delete_peace_users(
        self,
        target_ids: tuple[int, ...],
        actor: discord.Member,
        *,
        progress_callback: Callable[[int, int, tuple[str, ...]], Awaitable[None]] | None = None,
    ) -> list[str]:
        """Remove Peace state without kicking members or releasing invalid IDs."""
        if self.guild is None:
            return ["Servidor indisponível; nenhum vínculo foi alterado."]
        authorized_actor = await self.authorized_dm_member(actor.id, "founder")
        if authorized_actor is None:
            return ["Apenas o cargo Founder pode excluir vínculos Peace; nada foi alterado."]
        actor = authorized_actor
        not_verified = role_named(
            self.guild,
            getattr(self.settings, "not_verified_role_id", None),
            NOT_VERIFIED_ROLE_NAME,
            "Não verificado",
            "Nao verificado",
        )
        bot_member = self.guild.me
        peace_role = self.guild.get_role(self.settings.peace_role_id)
        if not_verified is None or peace_role is None or bot_member is None:
            return ["Cargos de Peace incompletos ou hierarquia indisponível; nenhum vínculo foi alterado."]

        results: list[str] = []
        unique_target_ids = tuple(dict.fromkeys(target_ids))
        processed = 0

        async def record_result(result: str) -> None:
            nonlocal processed
            results.append(result)
            processed += 1
            if progress_callback is not None:
                await progress_callback(processed, len(unique_target_ids), tuple(results))

        for target_id in unique_target_ids:
            if await self.authorized_dm_member(actor.id, "founder") is None:
                results.append("O cargo Founder não está mais presente; os próximos usuários não foram processados.")
                if progress_callback is not None:
                    await progress_callback(processed, len(unique_target_ids), tuple(results))
                break
            async with self.mutation_lock(int(target_id)):
                target = await self.member(self.guild, int(target_id))
                record = self.database.get_member(target_id)
                if target is None:
                    await record_result(f"{mention(target_id)}: não está no servidor; nada foi alterado.")
                    continue
                released_already = self.database.available_peace_id_for_user(target.id)
                manual_release = (
                    released_already is not None
                    and str(released_already["release_reason"] or "").startswith(
                        "vínculo Peace removido manualmente por Founder"
                    )
                )
                if record is None or int(record["peace_id"]) <= 0 or int(record["is_founder"]):
                    if manual_release:
                        cleanup_ok = True
                        try:
                            self.managed_peace_role_removals.add(target.id)
                            await self.apply_removed_member_state(
                                target,
                                peace_role=peace_role,
                                not_verified=not_verified,
                                bot_member=bot_member,
                                reason="Regularização de exclusão Peace já concluída",
                            )
                        except (discord.Forbidden, discord.HTTPException, RuntimeError):
                            cleanup_ok = False
                            await record_result(f"{target.mention}: ID já liberado, mas a regularização Discord falhou.")
                        finally:
                            self.managed_peace_role_removals.discard(target.id)
                        if cleanup_ok:
                            await record_result(
                                f"{target.mention}: exclusão já confirmada; ID `{int(released_already['peace_id'])}` continua liberado."
                            )
                    else:
                        await record_result(f"{target.mention}: registro Peace válido não encontrado; nada foi alterado.")
                    continue
                if not role_member(target, peace_role.id):
                    reserved = await self.reserve_member_peace(
                        target,
                        reason="cargo Peace já estava ausente durante a revisão Founder",
                        actor=actor,
                    )
                    if reserved is None:
                        await record_result(f"{target.mention}: o cargo Peace já não está presente e a reserva não pôde ser criada.")
                    else:
                        await record_result(f"{target.mention}: o cargo Peace já não estava presente; ID `{int(reserved['peace_id'])}` ficou reservado para retorno.")
                    continue

                self.managed_peace_role_removals.add(target.id)
                try:
                    await self.apply_removed_member_state(
                        target,
                        peace_role=peace_role,
                        not_verified=not_verified,
                        bot_member=bot_member,
                        reason=f"Vínculo Peace removido por Founder {actor.id}",
                    )
                    released = self.database.release_peace_member(
                        target.id,
                        reason="vínculo Peace removido manualmente por Founder",
                        actor_user_id=actor.id,
                    )
                    if released is None:
                        released = self.database.available_peace_id_for_user(target.id)
                        if released is not None and str(released["release_reason"] or "").startswith(
                            "vínculo Peace removido manualmente por Founder"
                        ):
                            await record_result(
                                f"{target.mention}: exclusão já confirmada; ID `{int(released['peace_id'])}` continua liberado."
                            )
                            continue
                        raise RuntimeError("registro Peace mudou antes da liberação do ID")
                    await self.send_log(
                        "Vínculo Peace removido",
                        actor=actor,
                        fields=(
                            ("Usuário", target.mention),
                            ("ID liberado", f"`{int(released['peace_id'])}`"),
                            ("Ação", "Cargos gerenciáveis removidos; Not Verified mantido/aplicado; apelido redefinido."),
                            ("Quem", actor.mention),
                            ("Horário", f"<t:{now_unix()}:F>"),
                        ),
                    )
                    await record_result(
                        f"{target.mention}: vínculo removido, apelido redefinido e ID `{int(released['peace_id'])}` liberado."
                    )
                except (discord.Forbidden, discord.HTTPException, RuntimeError, sqlite3.Error):
                    log.exception("Falha ao remover vínculo Peace de %s", target.id)
                    await record_result(f"{target.mention}: falha no Discord; o ID não foi liberado automaticamente.")
                finally:
                    self.managed_peace_role_removals.discard(target.id)
        return results

    async def recruiter_members(self) -> list[discord.Member]:
        if self.guild is None:
            return []
        recruiters = [
            member for member in self.guild.members
            if reviewer_member(member, self.settings)
        ]
        if recruiters:
            return recruiters
        try:
            fetched = [member async for member in self.guild.fetch_members(limit=None)]
        except (discord.Forbidden, discord.HTTPException):
            return []
        return [
            member for member in fetched
            if reviewer_member(member, self.settings)
        ]

    async def notify_claim(self, ticket, staff: discord.Member) -> None:
        if self.guild is None:
            return
        owner = await self.member(self.guild, int(ticket["owner_user_id"]))
        if owner is not None:
            try:
                await owner.send(
                    f"Seu ticket foi assumido por {staff.display_name}. A equipe continuará o atendimento por lá."
                )
            except discord.Forbidden:
                log.info("DM fechado para o solicitante %s", owner.id)
        try:
            await staff.send(f"Você assumiu o ticket <#{ticket['channel_id']}>.")
        except discord.Forbidden:
            log.info("DM fechado para o staff %s", staff.id)

    async def notify_staff_pv(self, ticket, reason: str, targets: list[discord.Member] | None = None) -> int:
        if self.guild is None:
            return 0
        selected: list[discord.Member] = []
        if targets is not None:
            selected = targets
        claimed_by = ticket["claimed_by"]
        if not selected and claimed_by:
            owner = await self.member(self.guild, int(claimed_by))
            if owner is not None:
                selected = [owner]
        if not selected:
            selected = [
                member
                for member in self.guild.members
                if member.id != getattr(self.user, "id", 0)
                and staff_member(member, self.settings)
                and member.status != discord.Status.offline
            ][:5]
        sent = 0
        for staff in selected:
            try:
                await staff.send(
                    f"Iris: {reason}\nTicket: <#{ticket['channel_id']}>\n"
                    "Abra o ticket e use os controles exclusivos da staff publicados nele para iniciar o atendimento."
                )
                sent += 1
            except (discord.Forbidden, discord.HTTPException):
                log.info("Não foi possível enviar PV para staff %s", staff.id)
        return sent

    async def staff_support_scores(self, category: str) -> list[tuple[discord.Member, float]]:
        """Calcula uma pontuação explicável usando tickets fechados e ações observáveis."""
        if self.guild is None:
            return []
        scores: dict[int, float] = {}
        category_key = category.casefold().strip()
        for ticket in self.database.closed_tickets()[:40]:
            channel = self.guild.get_channel(int(ticket["channel_id"]))
            if not isinstance(channel, discord.TextChannel):
                continue
            weight = 2.0 if str(ticket["reason"]).casefold() == category_key else 0.5
            claimed = ticket["claimed_by"]
            if claimed:
                scores[int(claimed)] = scores.get(int(claimed), 0.0) + weight
            closed_by = ticket["closed_by"]
            if closed_by:
                scores[int(closed_by)] = scores.get(int(closed_by), 0.0) + 0.25
            try:
                async for message in channel.history(limit=80, oldest_first=True):
                    author = message.author
                    if isinstance(author, discord.Member) and staff_member(author, self.settings):
                        scores[author.id] = scores.get(author.id, 0.0) + weight
            except (discord.Forbidden, discord.HTTPException):
                continue
        ranked: list[tuple[discord.Member, float]] = []
        for member_id, score in scores.items():
            member = await self.member(self.guild, member_id)
            if member is not None and staff_member(member, self.settings):
                ranked.append((member, score))
        ranked.sort(key=lambda item: (-item[1], item[0].display_name.casefold()))
        return ranked

    async def escalate_ticket(self, channel: discord.TextChannel, ticket) -> None:
        if self.guild is None:
            return
        ranked = await self.staff_support_scores(str(ticket["reason"]))
        if ranked:
            staff, score = ranked[0]
            await channel.send(
                f"{staff.mention}, a Íris encaminhou este atendimento para você por histórico de suporte compatível.",
                allowed_mentions=discord.AllowedMentions(users=True),
            )
            self.database.record_iris_event(
                event_type="staff_escalation",
                scope="ticket",
                channel_id=channel.id,
                ticket_id=int(ticket["id"]),
                actor_user_id=staff.id,
                metadata={"score": round(score, 2), "category": str(ticket["reason"])},
            )
            await self.notify_staff_pv(ticket, "A Íris encaminhou um atendimento para você.", [staff])
            return
        role = f"<@&{self.settings.staff_role_id}>" if self.settings.staff_role_id else "a staff"
        await channel.send(
            f"{role}, a Íris precisa de ajuda humana neste atendimento.",
            allowed_mentions=discord.AllowedMentions(roles=True),
        )
        self.database.record_iris_event(
            event_type="staff_escalation",
            scope="ticket",
            channel_id=channel.id,
            ticket_id=int(ticket["id"]),
            metadata={"category": str(ticket["reason"]), "score": None},
        )
        await self.notify_staff_pv(ticket, "A Íris precisa de ajuda humana neste atendimento.")

    def context_author(self, message: discord.Message) -> str:
        if self.user is not None and message.author.id == self.user.id:
            return "Iris"
        if isinstance(message.author, discord.Member) and staff_member(message.author, self.settings):
            return "staff"
        return "solicitante"

    async def ticket_history(self, channel: discord.TextChannel, limit: int = 40) -> str:
        try:
            messages = [
                message
                async for message in channel.history(limit=limit, oldest_first=True)
                if not message.author.bot
            ]
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao ler histórico do ticket %s", channel.id)
            return ""
        return bounded_context(message_lines(messages, role_resolver=self.context_author), limit=12000)

    async def safe_channel_context(self, channel_id: int, *, limit: int | None = None) -> str:
        if self.guild is None:
            return ""
        channel = self.guild.get_channel(channel_id)
        if not isinstance(channel, discord.TextChannel):
            return ""
        if self.guild.me is not None:
            permissions = channel.permissions_for(self.guild.me)
            if not permissions.view_channel or not permissions.read_message_history:
                return ""
        try:
            messages = [
                message async for message in channel.history(
                    limit=limit or self.settings.iris_history_limit,
                    oldest_first=True,
                )
            ]
        except (discord.Forbidden, discord.HTTPException):
            log.info("Iris sem acesso de leitura ao canal de contexto %s", channel_id)
            return ""
        return bounded_context(message_lines(messages, role_resolver=self.context_author), limit=5000)

    async def closed_ticket_context(self) -> str:
        if self.guild is None or self.settings.closed_ticket_category_id is None:
            return ""
        category = self.guild.get_channel(self.settings.closed_ticket_category_id)
        if not isinstance(category, discord.CategoryChannel):
            return ""
        channels = sorted(category.text_channels, key=lambda item: item.created_at, reverse=True)[:12]
        histories = await asyncio.gather(
            *(self.ticket_history(channel, limit=12) for channel in channels),
            return_exceptions=True,
        )
        parts: list[str] = []
        for history in histories:
            if isinstance(history, str) and history:
                parts.append(f"[ticket anterior anonimizado]\n{history}")
        return bounded_context(parts, limit=12000)

    async def organization_context(self) -> str:
        async with self.iris_context_lock:
            now = time.monotonic()
            if self.iris_context_cache and now - self.iris_context_cache_at < 180:
                return self.iris_context_cache

            async def collect(channel_ids: tuple[int, ...], limit: int) -> list[str]:
                values = await asyncio.gather(
                    *(self.safe_channel_context(channel_id, limit=limit) for channel_id in channel_ids),
                    return_exceptions=True,
                )
                return [value for value in values if isinstance(value, str) and value]

            parts: list[str] = []
            management = await collect(self.settings.iris_management_channel_ids, self.settings.iris_history_limit)
            if management:
                parts.append("\n".join(f"[gerência — referência interna, não revelar]\n{value}" for value in management))

            culture = await collect(self.settings.iris_general_channel_ids, 6)
            configured = set(self.settings.iris_management_channel_ids) | set(self.settings.iris_general_channel_ids) | set(self.settings.iris_learning_channel_ids)
            detected_channels = []
            for channel in self.guild.text_channels if self.guild is not None else []:
                parent_name = channel.category.name.casefold() if channel.category else ""
                if channel.id in configured or "ticket" in parent_name or "registro" in parent_name:
                    continue
                if "chat" in channel.name.casefold() or "resenha" in parent_name:
                    detected_channels.append(channel.id)
            culture.extend(await collect(tuple(detected_channels), 4))
            if culture:
                parts.append("\n".join(f"[cultura pública — usar apenas como tendência]\n{value}" for value in culture))

            known = set(self.settings.iris_management_channel_ids) | set(self.settings.iris_general_channel_ids)
            learning_ids = tuple(channel_id for channel_id in self.settings.iris_learning_channel_ids if channel_id not in known)
            extra = await collect(learning_ids, 6)
            if extra:
                parts.append("\n".join(f"[padrão interno autorizado — não revelar]\n{value}" for value in extra))

            previous = await self.closed_ticket_context()
            if previous:
                parts.append("[tickets anteriores — anonimizados, usar como padrão e nunca como fato atual]\n" + previous)
            self.iris_context_cache = bounded_context(parts, limit=7000)
            self.iris_context_cache_at = now
            return self.iris_context_cache

    def iris_mentioned(self, message: discord.Message) -> bool:
        content = message.content.casefold()
        return "iris" in content or (self.user is not None and self.user in message.mentions)

    @staticmethod
    def requested_role(ticket) -> str:
        value = f"{ticket['reason']} {ticket['details']}".casefold()
        if "dev" in value or "developer" in value:
            return "Developer"
        if "streamer" in value:
            return "Streamer"
        if "recrutador" in value or "recrutamento" in value:
            return "Recrutador"
        return ""

    @staticmethod
    def iris_fast_fallback(role_request: str, history: str) -> str:
        """Mantém a conversa viva quando o modelo local está lento demais."""
        if not role_request:
            return "Pode explicar em uma frase o que aconteceu?"
        step = min(max(history.casefold().count("solicitante:") - 1, 0), 3)
        if step >= 3:
            role_label = role_request.capitalize()
            return f"Ainda não posso aprovar o pedido para {role_label}. Faltam exemplos reais e verificáveis de contribuição. A staff pode revisar o caso se você apresentar essas evidências."
        questions = {
            "developer": (
                "Você já corrigiu algum problema em teste? O que mudou?",
                "Como você conferiu que a mudança deu certo?",
                "O que faria se a mudança desse errado?",
                "Por que quer ser Developer da Peace?",
            ),
            "streamer": (
                "Que tipo de conteúdo você quer trazer para a Peace?",
                "Como você lidaria com uma crítica ao seu conteúdo?",
                "Como evitaria expor alguém sem autorização?",
                "Por que quer ser Streamer da Peace?",
            ),
            "recrutador": (
                "Como você receberia alguém novo na Peace?",
                "O que faria ao ver uma regra sendo quebrada?",
                "Como seria justo ao avaliar um pedido de set?",
                "Por que quer ser Recrutador da Peace?",
            ),
        }
        selected = questions.get(role_request.casefold(), questions["developer"])
        return selected[step]

    @staticmethod
    def extract_escalation_marker(answer: str) -> tuple[str, bool]:
        should_escalate = "[encaminhar]" in answer.casefold()
        cleaned = re.sub(r"\[encaminhar\]\s*", "", answer, flags=re.IGNORECASE).strip()
        return cleaned, should_escalate

    def schedule_iris_response(self, channel: discord.TextChannel) -> None:
        if self.iris is None:
            return
        self.iris_pending.add(channel.id)
        current = self.iris_tasks.get(channel.id)
        if current is not None and not current.done():
            return
        task = asyncio.create_task(self.iris_response_loop(channel), name=f"iris-ticket-{channel.id}")
        self.iris_tasks[channel.id] = task
        task.add_done_callback(lambda _: self.iris_tasks.pop(channel.id, None))
        task.add_done_callback(self.report_background_task)

    async def iris_response_loop(self, channel: discord.TextChannel) -> None:
        try:
            while channel.id in self.iris_pending:
                self.iris_pending.discard(channel.id)
                await asyncio.sleep(1)
                current = self.database.ticket_by_channel(channel.id)
                if current is None or current["status"] != "open" or self.iris is None:
                    return
                async with channel.typing():
                    history = await self.ticket_history(channel, limit=12)
                    try:
                        organization_context = await asyncio.wait_for(
                            self.organization_context(),
                            timeout=1,
                        )
                    except asyncio.TimeoutError:
                        organization_context = self.iris_context_cache
                        log.warning("Contexto da Iris demorou no ticket %s; usando cache disponível", channel.id)
                    owner = await self.member(self.guild, int(current["owner_user_id"])) if self.guild else None
                    user_profile = self.user_ticket_profile(int(current["owner_user_id"]))
                    user_profile = "\n".join(
                        part for part in (self.member_profile(owner), user_profile) if part
                    )
                    role_request = self.requested_role(current)
                    history = bounded_context([history], limit=2600 if role_request else 4500)
                    organization_context = bounded_context([organization_context], limit=1800 if role_request else 3500)
                    user_profile = bounded_context([user_profile], limit=600 if role_request else 900)
                    staff_mention = f"<@&{self.settings.staff_role_id}>" if self.settings.staff_role_id else "a staff"
                    try:
                        answer = await asyncio.wait_for(
                            self.iris.chat(
                                system=IRIS_SYSTEM,
                                prompt=prompt_for_ticket(
                                    category=str(current["reason"]),
                                    details=redact(str(current["details"])),
                                    history=history,
                                    staff_mention=staff_mention,
                                    organization_context=organization_context,
                                    user_profile=user_profile,
                                    role_request=role_request,
                                ),
                            ),
                            timeout=8,
                        )
                    except asyncio.TimeoutError:
                        log.warning("Resposta da Iris excedeu 8s no ticket %s; usando pergunta curta", channel.id)
                        answer = self.iris_fast_fallback(role_request, history)
                answer = sanitize_assistant_output(answer, forbidden_context=organization_context)
                answer = concise_assistant_output(answer, interview=bool(self.requested_role(current)))
                answer, should_escalate = self.extract_escalation_marker(answer)
                current = self.database.ticket_by_channel(channel.id)
                if current is None or current["status"] != "open":
                    return
                await channel.send(answer, allowed_mentions=discord.AllowedMentions.none())
                if should_escalate and not self.database.has_iris_event(
                    event_type="staff_escalation", ticket_id=int(current["id"])
                ):
                    await self.escalate_ticket(channel, current)
                self.database.record_iris_event(
                    event_type="iris_response",
                    scope="ticket",
                    channel_id=channel.id,
                    ticket_id=int(current["id"]),
                    metadata={"category": str(current["reason"])},
                )
        except IrisError as error:
            log.warning("Iris não respondeu ao ticket %s: %s", channel.id, error)
            current = self.database.ticket_by_channel(channel.id)
            if current is not None and current["status"] == "open":
                await channel.send(
                    "⚠️ A Íris está temporariamente indisponível. "
                    "Sua solicitação continua aberta e a equipe foi avisada.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
                await self.notify_staff_pv(current, "Não consegui responder automaticamente ao ticket.")
        except asyncio.CancelledError:
            raise
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao publicar resposta da Iris no ticket %s", channel.id)
        except Exception:
            log.exception("Erro inesperado no atendimento da Iris no ticket %s", channel.id)

    def start_iris_escalation(self, channel: discord.TextChannel) -> None:
        if self.iris is None:
            return
        if channel.id in self.iris_escalation_tasks:
            return
        task = asyncio.create_task(self.iris_escalation(channel), name=f"iris-escalation-{channel.id}")
        self.iris_escalation_tasks[channel.id] = task
        task.add_done_callback(lambda _: self.iris_escalation_tasks.pop(channel.id, None))
        task.add_done_callback(self.report_background_task)

    def stop_iris(self, channel_id: int) -> None:
        self.iris_pending.discard(channel_id)
        for tasks in (self.iris_tasks, self.iris_escalation_tasks):
            task = tasks.get(channel_id)
            if task is not None and not task.done():
                task.cancel()

    async def iris_escalation(self, channel: discord.TextChannel) -> None:
        try:
            await asyncio.sleep(max(60, self.settings.iris_escalation_seconds))
            current = self.database.ticket_by_channel(channel.id)
            if current is None or current["status"] != "open":
                return
            recent = await self.ticket_history(channel, limit=8)
            if current["claimed_by"] and "staff:" in recent:
                return
            sent = await self.notify_staff_pv(current, "O ticket ainda está sem retorno da equipe.")
            self.database.record_iris_event(
                event_type="staff_escalation",
                scope="ticket",
                channel_id=channel.id,
                ticket_id=int(current["id"]),
                metadata={"sent": sent, "claimed": bool(current["claimed_by"])},
            )
            if sent:
                role = f"<@&{self.settings.staff_role_id}>" if self.settings.staff_role_id else "staff"
                await channel.send(
                    content=f"{role}, o ticket ainda aguarda atendimento. A equipe foi notificada por PV.",
                    allowed_mentions=discord.AllowedMentions(roles=True),
                )
            else:
                await channel.send(
                    content="O ticket ainda aguarda atendimento. A equipe deve verificar o painel interno.",
                    allowed_mentions=discord.AllowedMentions.none(),
                )
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao escalar ticket %s", channel.id)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Erro inesperado ao escalar ticket %s", channel.id)

    async def resume_iris(self) -> None:
        if self.guild is None or self.iris is None:
            return
        for row in self.database.open_tickets():
            channel = self.guild.get_channel(int(row["channel_id"]))
            if isinstance(channel, discord.TextChannel):
                self.start_iris_escalation(channel)
                if not self.database.has_iris_event(
                    event_type="iris_response",
                    ticket_id=int(row["id"]),
                ):
                    self.schedule_iris_response(channel)

    async def channel_history(self, channel: discord.abc.Messageable, limit: int = 25) -> str:
        if not hasattr(channel, "history"):
            return ""
        try:
            messages = [message async for message in channel.history(limit=limit, oldest_first=True)]
        except (discord.Forbidden, discord.HTTPException):
            log.exception("Falha ao ler histórico do canal %s", getattr(channel, "id", "?"))
            return ""
        return bounded_context(message_lines(messages, role_resolver=self.context_author), limit=10000)

    def member_profile(self, member: discord.Member | None) -> str:
        if member is None:
            return ""
        roles = [role.name for role in member.roles if role.name != "@everyone"]
        parts = [
            f"perfil do servidor: nome={redact(member.display_name, limit=80)}",
            f"cargos={redact(', '.join(roles[:12]), limit=400) or 'nenhum'}",
        ]
        if self.settings.booster_role_id and role_member(member, self.settings.booster_role_id):
            parts.append(
                "benefícios booster: call privada automática no meio da categoria CALL・PRIVADA, "
                "cargo privado para convidados e comandos para adicionar/remover, puxar e retirar da call"
            )
        if member.joined_at is not None:
            parts.append(f"entrou no servidor em={member.joined_at.date().isoformat()}")
        return " | ".join(parts)

    def user_ticket_profile(self, user_id: int) -> str:
        try:
            with self.database.connect() as connection:
                rows = connection.execute(
                    "SELECT reason, details, status, created_at, closed_at FROM tickets WHERE owner_user_id = ? ORDER BY id DESC LIMIT 5",
                    (str(user_id),),
                ).fetchall()
        except Exception:
            log.exception("Falha ao consultar perfil operacional do usuário %s", user_id)
            return ""
        if not rows:
            return ""
        return "\n".join(
            f"atendimento anterior: categoria={redact(str(row['reason']), limit=80)}, resumo={redact(str(row['details']), limit=300)}, estado={row['status']}, criado={str(row['created_at'])[:10]}"
            for row in rows
        )

    async def finish_set(self, interaction: discord.Interaction, draft: SetDraft, source: str, recruiter_user_id: int | None) -> None:
        guild = interaction.guild or self.guild
        if guild is None:
            await respond(interaction, "Não consegui localizar o servidor.")
            return
        member = await self.member(guild, interaction.user.id)
        if member is None:
            await respond(interaction, "Não consegui localizar seu membro no servidor.")
            return
        reservation = self.database.reserved_peace_id_for_user(member.id)
        if reservation is not None:
            await self.ensure_return_request(member)
            await respond(
                interaction,
                "Seu ID Peace continua reservado. O retorno foi enviado diretamente ao scan-only para aprovação; não vou abrir uma entrevista comum.",
            )
            return
        if not application_path_open("player", self.settings):
            await respond(interaction, "Eu mantive as vagas de Player fechadas no momento.")
            return
        peace_role = guild.get_role(self.settings.peace_role_id)
        if peace_role is None:
            await respond(interaction, "A configuração de cargos Peace está incompleta; procure a staff.")
            return
        if self.database.pending_set_request_for_user(member.id) is not None:
            await respond(interaction, "Seu pedido já está aguardando aprovação de Staff ou Management.")
            return
        if len(f"N ⎰ {draft.in_game_username} 99999") > 32:
            await respond(interaction, "Esse apelido ultrapassa o limite de 32 caracteres.")
            return
        request_id = self.database.save_set_request(
            discord_user_id=member.id,
            in_game_username=draft.in_game_username,
            rg_in_game=draft.rg_in_game,
            telefone_in_game=draft.telefone_in_game,
            source=source,
            recruiter_user_id=recruiter_user_id,
            status="pending",
        )
        request = self.database.set_request(request_id)
        if request is None:
            await respond(interaction, "Não consegui registrar seu pedido para aprovação.")
            return
        await self.send_to_channel(
            self.settings.scan_channel_id,
            embed=self.set_approval_embed(request),
            view=self.set_approval_view(request_id),
        )
        self.drafts.pop(interaction.user.id, None)
        await respond(interaction, "Pedido enviado ao scan-only. Staff ou Management precisa aprovar o set manualmente antes da liberação.")

    def can_approve_set_request(self, request, member: discord.Member) -> bool:
        # Historical requests may contain a former recruiter ID, but that ID
        # never bypasses the current Staff/Management authorization boundary.
        return reviewer_member(member, self.settings)

    async def approve_set_request(self, request, recruiter: discord.Member) -> str:
        guild = recruiter.guild
        member = await self.member(guild, int(request["discord_user_id"]))
        peace_role = guild.get_role(self.settings.peace_role_id)
        intern_role = role_named(
            guild,
            getattr(self.settings, "intern_role_id", None),
            INTERN_ROLE_NAME,
            "Intern",
            "Estagiario",
        )
        visitor_role = role_named(
            guild,
            getattr(self.settings, "visitor_role_id", None),
            "Visitor",
        )
        not_verified_role = role_named(
            guild,
            getattr(self.settings, "not_verified_role_id", None),
            NOT_VERIFIED_ROLE_NAME,
            "Não verificado",
            "Nao verificado",
        )
        if member is None or peace_role is None or intern_role is None:
            return "Não consegui localizar o membro ou os cargos do set."
        requested_role_objects = list(member.roles)
        for role in (peace_role, intern_role):
            if role not in requested_role_objects:
                requested_role_objects.append(role)
        requested_role_names = [role.name for role in requested_role_objects]
        existing = self.database.get_member(member.id)
        peace_id = int(existing["peace_id"]) if existing else self.database.ensure_runtime_member(
            discord_user_id=member.id,
            username=member.name,
            nickname=member.nick,
            role_ids=[role.id for role in member.roles],
            role_names=[role.name for role in member.roles],
            founder_id=self.settings.founder_user_id,
            role_positions=role_position_map(requested_role_objects),
            role_hoist=role_hoist_map(requested_role_objects),
        )
        prefix = prefix_for_roles(
            user_id=member.id,
            role_names=requested_role_names,
            founder_user_id=self.settings.founder_user_id,
            founder_role_names=FOUNDER_ROLE_NAMES,
            default="N",
            role_positions=role_position_map(requested_role_objects),
            role_hoist=role_hoist_map(requested_role_objects),
        ) or "N"
        nickname = f"{prefix} ⎰ {request['in_game_username']} {peace_id}"
        try:
            await member.add_roles(
                peace_role,
                intern_role,
                reason=f"Set aprovado manualmente por Staff ou Management {recruiter.id}",
            )
            if visitor_role is not None:
                await member.remove_roles(visitor_role, reason="Set aprovado: visitante convertido em Peace")
            if not_verified_role is not None:
                await member.remove_roles(not_verified_role, reason="Set aprovado: membro convertido em Peace")
            await member.edit(nick=nickname, reason="Set aprovado manualmente por Staff ou Management")
            member_roles = {role.id: role.name for role in member.roles}
            member_roles[peace_role.id] = peace_role.name
            member_roles[intern_role.id] = intern_role.name
            self.database.ensure_runtime_member(
                discord_user_id=member.id,
                username=member.name,
                nickname=nickname,
                role_ids=list(member_roles),
                role_names=list(member_roles.values()),
                founder_id=self.settings.founder_user_id,
                role_positions=role_position_map(requested_role_objects),
                role_hoist=role_hoist_map(requested_role_objects),
            )
            self.database.update_set_request_status(request["id"], "approved")
            dm_sent = True
            try:
                await member.send(
                    embed=self.set_approved_dm_embed(request, recruiter, peace_id),
                    allowed_mentions=discord.AllowedMentions.none(),
                )
            except (discord.Forbidden, discord.HTTPException):
                dm_sent = False
                log.info("DM fechado para o membro aprovado %s", member.id)
        except (discord.Forbidden, discord.HTTPException, RuntimeError):
            log.exception("Falha ao aplicar set pendente em %s", member.id)
            return "Não consegui aplicar o set. Verifique permissões, hierarquia e tente novamente."
        await self.send_log(
            "Set aprovado",
            actor=recruiter,
            fields=(
                ("Usuário", member.mention),
                ("ID Peace", f"`{peace_id}`"),
                ("Aprovado por", recruiter.mention),
                ("DM de boas-vindas", "enviada" if dm_sent else "indisponível"),
                ("Horário", f"<t:{now_unix()}:F>"),
            ),
        )
        dm_note = "" if dm_sent else " A DM de boas-vindas está fechada."
        return f"Set aprovado por {recruiter.mention}. Membro: {member.mention}. ID Peace: `{peace_id}`.{dm_note}"

    async def reject_set_request(self, request, recruiter: discord.Member) -> None:
        self.database.update_set_request_status(request["id"], "rejected")
        member = await self.member(recruiter.guild, int(request["discord_user_id"]))
        if member is not None:
            try:
                await member.send("Seu pedido de set foi recusado por Staff ou Management. Se precisar, abra um ticket para revisar os dados.")
            except (discord.Forbidden, discord.HTTPException):
                log.info("DM fechado para o pedido de set %s", request["id"])

    async def issue_central_login_code(self, member: discord.Member, peace_id: int, client_id: str) -> bool | None:
        code = f"{secrets.randbelow(1_000_000):06d}"
        expires_at = datetime.now(timezone.utc) + timedelta(
            seconds=self.settings.central_auth_code_ttl_seconds
        )
        challenge_id = self.database.try_create_central_login_challenge(
            discord_user_id=member.id,
            peace_id=peace_id,
            client_id=client_id,
            code=code,
            expires_at=expires_at.isoformat(),
        )
        if challenge_id is None:
            return None
        try:
            await member.send(
                "Código de acesso da Central\n"
                f"ID Peace: `{peace_id}`\n"
                f"Código: `{code}`\n"
                f"Validade: {self.settings.central_auth_code_ttl_seconds // 60} minutos.\n"
                "Não compartilhe este código."
            )
        except (discord.Forbidden, discord.HTTPException):
            self.database.revoke_central_login_challenges(member.id, client_id)
            log.info("DM fechada para o código da Central do membro %s", member.id)
            return False
        return True

    async def open_ticket(self, interaction: discord.Interaction, reason: str, details: str) -> None:
        guild = interaction.guild or self.guild
        if guild is None or not isinstance(interaction.user, discord.Member):
            await respond(interaction, "Este formulário só funciona dentro do servidor.")
            return
        old = self.database.ticket_for_owner(interaction.user.id)
        if old is not None:
            await respond(interaction, f"Você já possui um ticket aberto: <#{old['channel_id']}>")
            return
        category = guild.get_channel(self.settings.ticket_category_id or 0)
        if not isinstance(category, discord.CategoryChannel):
            await respond(interaction, "A categoria de tickets não está configurada.")
            return
        channel: discord.TextChannel | None = None
        try:
            channel = await guild.create_text_channel(name="sup-abrindo", category=category, reason="Novo ticket Peace")
            ticket_id = self.database.create_ticket(
                channel_id=channel.id,
                owner_user_id=interaction.user.id,
                reason=reason,
                details=details,
            )
            try:
                await channel.edit(name=self.ticket_channel_name(interaction.user, ticket_id), reason="Numerar ticket Peace")
            except discord.HTTPException:
                log.exception("Não consegui renomear o ticket %s após registrá-lo", ticket_id)
            await channel.send(
                embed=self.ticket_open_embed(ticket_id, interaction.user.mention, reason, details),
                allowed_mentions=discord.AllowedMentions(users=True, roles=False),
            )
            current = self.database.ticket_by_channel(channel.id)
            if current is not None:
                await self.sync_ticket_control_panels()
                if self.iris is not None:
                    self.schedule_iris_response(channel)
                    self.start_iris_escalation(channel)
        except (discord.Forbidden, discord.HTTPException, RuntimeError):
            log.exception("Falha ao abrir ticket")
            if channel is not None:
                try:
                    await channel.delete(reason="Rollback de ticket com erro")
                except discord.HTTPException:
                    log.exception("Falha ao remover canal de ticket incompleto")
            await respond(interaction, "Não consegui abrir o ticket. Verifique as permissões e tente novamente.")
            return
        await respond(interaction, f"Ticket aberto: {channel.mention}")


@app_commands.command(name="start", description="Abre as ações internas da Peace no PV")
@app_commands.allowed_contexts(guilds=False, dms=True, private_channels=False)
async def start(interaction: discord.Interaction) -> None:
    bot = interaction.client
    if not isinstance(bot, PeaceBot):
        return
    actions = await bot.start_actions_for(interaction.user.id)
    if not actions:
        # Ordinary members must not learn that an internal menu exists.
        await ignore_interaction(interaction)
        return
    if interaction.guild is not None:
        await respond(interaction, "Use o `/start` no PV com o bot.")
        return
    await interaction.response.send_message(
        "Escolha uma ação. Cada opção valida novamente o cargo antes de executar qualquer alteração.",
        view=StartActionView(bot, interaction.user.id, actions),
        ephemeral=False,
    )


@app_commands.command(name="painel_set", description="Publica ou atualiza o painel de pedido de set")
async def panel_set(interaction: discord.Interaction) -> None:
    bot = interaction.client
    if not isinstance(bot, PeaceBot) or not isinstance(interaction.user, discord.Member):
        return
    if not staff_member(interaction.user, bot.settings):
        await respond(interaction, "Apenas a staff pode sincronizar painéis.")
        return
    if interaction.channel_id != bot.settings.set_channel_id:
        await respond(interaction, "Use este comando no canal de pedir set.")
        return
    await interaction.response.defer(ephemeral=True)
    await bot.sync_one_panel(bot.settings.set_channel_id, "peace_pedir_set_open", bot.set_panel_embeds(), SetView(bot), SET_PANEL_ASSET)
    await interaction.followup.send("Painel de set sincronizado.", ephemeral=True)


async def booster_owner_context(interaction: discord.Interaction):
    bot = interaction.client
    if not isinstance(bot, PeaceBot) or not isinstance(interaction.user, discord.Member):
        return None, None, None
    if bot.settings.booster_role_id is None or not role_member(interaction.user, bot.settings.booster_role_id):
        return bot, None, None
    private_role, voice = bot.booster_space(interaction.user)
    return bot, private_role, voice


@app_commands.command(name="booster_adicionar", description="Adiciona alguém ao cargo privado do seu booster")
async def booster_add(interaction: discord.Interaction, usuario: discord.Member) -> None:
    bot, private_role, voice = await booster_owner_context(interaction)
    if bot is None or private_role is None:
        await respond(interaction, "Você não possui uma área privada de booster ativa.")
        return
    if bot.guild is None or bot.guild.me is None or private_role.position >= bot.guild.me.top_role.position:
        await respond(interaction, "O cargo privado está acima da hierarquia do bot.")
        return
    try:
        await usuario.add_roles(private_role, reason=f"Booster {interaction.user.id} adicionou membro")
    except (discord.Forbidden, discord.HTTPException):
        await respond(interaction, "Não consegui aplicar o cargo privado.")
        return
    await respond(interaction, f"Cargo privado aplicado a {usuario.mention}.")


@app_commands.command(name="booster_remover", description="Remove alguém do cargo privado do seu booster")
async def booster_remove(interaction: discord.Interaction, usuario: discord.Member) -> None:
    bot, private_role, voice = await booster_owner_context(interaction)
    if bot is None or private_role is None:
        await respond(interaction, "Você não possui uma área privada de booster ativa.")
        return
    try:
        await usuario.remove_roles(private_role, reason=f"Booster {interaction.user.id} removeu membro")
    except (discord.Forbidden, discord.HTTPException):
        await respond(interaction, "Não consegui remover o cargo privado.")
        return
    if voice is not None and usuario.voice is not None and usuario.voice.channel and usuario.voice.channel.id == voice.id:
        try:
            await usuario.move_to(None, reason=f"Booster {interaction.user.id} removeu membro da call")
        except (discord.Forbidden, discord.HTTPException):
            log.info("Não consegui retirar %s da call privada", usuario.id)
    await respond(interaction, f"Cargo privado removido de {usuario.mention}.")


@app_commands.command(name="booster_puxar", description="Puxa para sua call privada alguém que já esteja em voz")
async def booster_pull(interaction: discord.Interaction, usuario: discord.Member) -> None:
    bot, private_role, voice = await booster_owner_context(interaction)
    if bot is None or private_role is None or voice is None:
        await respond(interaction, "Sua área privada de booster não está disponível.")
        return
    if usuario.voice is None:
        await respond(interaction, "O usuário precisa estar em uma call para ser puxado.")
        return
    if private_role not in usuario.roles:
        await respond(interaction, "Primeiro adicione o usuário ao seu cargo privado.")
        return
    try:
        await usuario.move_to(voice, reason=f"Booster {interaction.user.id} puxou membro para sua call")
    except (discord.Forbidden, discord.HTTPException):
        await respond(interaction, "Não consegui mover o usuário. Verifique as permissões da call.")
        return
    await respond(interaction, f"{usuario.mention} foi movido para sua call privada.")


@app_commands.command(name="booster_tirar_call", description="Tira alguém da sua call privada")
async def booster_remove_from_call(interaction: discord.Interaction, usuario: discord.Member) -> None:
    bot, private_role, voice = await booster_owner_context(interaction)
    if bot is None or private_role is None or voice is None:
        await respond(interaction, "Sua área privada de booster não está disponível.")
        return
    if usuario.voice is None or usuario.voice.channel is None or usuario.voice.channel.id != voice.id:
        await respond(interaction, "Esse usuário não está na sua call privada.")
        return
    try:
        await usuario.move_to(None, reason=f"Booster {interaction.user.id} retirou membro da call")
    except (discord.Forbidden, discord.HTTPException):
        await respond(interaction, "Não consegui retirar o usuário da call.")
        return
    await respond(interaction, f"{usuario.mention} foi retirado da sua call privada.")


@app_commands.command(name="sincronizar", description="Reintegra os painéis nos canais configurados")
async def sync_panels(interaction: discord.Interaction) -> None:
    bot = interaction.client
    if not isinstance(bot, PeaceBot) or not isinstance(interaction.user, discord.Member):
        return
    if not staff_member(interaction.user, bot.settings):
        await respond(interaction, "Apenas a staff pode sincronizar painéis.")
        return
    await interaction.response.defer(ephemeral=True)
    await bot.sync_panels()
    await interaction.followup.send("Painéis sincronizados.", ephemeral=True)


@app_commands.command(name="ausencia", description="Solicita uma ausência à gerência")
async def absence(interaction: discord.Interaction) -> None:
    bot = interaction.client
    if not isinstance(bot, PeaceBot):
        return
    if bot.settings.absence_channel_id and interaction.channel_id != bot.settings.absence_channel_id:
        await respond(interaction, "Use este comando no canal de gerência.")
        return
    await interaction.response.send_modal(AbsenceModal(bot))


@app_commands.command(name="farme", description="Registra uma entrega de farme no canal de logs")
@app_commands.describe(entregou="Membro que entregou", recebeu="Membro que recebeu", valor_entregue="Valor entregue", valor_contado="Valor conferido", metas="Metas pagas", dias="Dias quitados", prova="URL da prova")
async def farm(interaction: discord.Interaction, entregou: discord.Member, recebeu: discord.Member, valor_entregue: int, valor_contado: int, metas: int, dias: str, prova: str | None = None) -> None:
    bot = interaction.client
    if not isinstance(bot, PeaceBot) or not isinstance(interaction.user, discord.Member):
        return
    if not staff_member(interaction.user, bot.settings):
        await respond(interaction, "Apenas a staff pode registrar farme.")
        return
    if min(valor_entregue, valor_contado, metas) < 0:
        await respond(interaction, "Valores e metas não podem ser negativos.")
        return
    await interaction.response.defer(ephemeral=True)
    bot.database.save_farm(delivered_by=entregou.id, received_by=recebeu.id, delivered_value=valor_entregue, counted_value=valor_contado, goals_paid=metas, paid_days=dias, proof_url=prova, created_by=interaction.user.id)
    await bot.send_log(
        "Farme confirmado",
        actor=interaction.user,
        fields=(
            ("Entregou", entregou.mention),
            ("Recebeu", recebeu.mention),
            ("Valor entregue", str(valor_entregue)),
            ("Valor contado", str(valor_contado)),
            ("Metas pagas", str(metas)),
            ("Dias quitados", dias),
            ("Prova", prova or "não informada"),
            ("Horário", f"<t:{now_unix()}:F>"),
        ),
    )
    await interaction.followup.send("Farme registrado nos logs.", ephemeral=True)


def run() -> None:
    configure_logging()
    try:
        settings = Settings.from_env()
    except RuntimeError as error:
        log.error("Configuração inválida; o bot não será iniciado: %s", error)
        raise SystemExit(2) from error
    bot = PeaceBot(settings)
    guild = discord.Object(id=settings.guild_id)
    bot.tree.add_command(start)
    for command in (
        panel_set,
        sync_panels,
        absence,
        farm,
        booster_add,
        booster_remove,
        booster_pull,
        booster_remove_from_call,
    ):
        bot.tree.add_command(command, guild=guild)
    bot.run(settings.token)


if __name__ == "__main__":
    run()

