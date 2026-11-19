import asyncio
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import AsyncMock

import discord

from bot.main import PeaceBot


@dataclass(frozen=True)
class FrozenRoleSettings:
    database_path: object
    iris_enabled: bool = False
    iris_url: str = "http://127.0.0.1:11435"
    iris_model: str = "iris-test"
    guild_id: int = 1
    not_verified_role_id: int | None = None
    intern_role_id: int | None = None
    investigator_role_id: int | None = None
    lead_investigator_role_id: int | None = None


class FakeRole:
    def __init__(self, role_id: int, name: str, colour: int):
        self.id = role_id
        self.name = name
        self.permissions = discord.Permissions.none()
        self.colour = discord.Colour(colour)
        self.edit = AsyncMock()


def fake_guild(roles):
    guild = SimpleNamespace(roles=roles, create_role=AsyncMock())
    guild.get_role = lambda role_id: next(
        (role for role in guild.roles if role.id == role_id),
        None,
    )
    return guild


def test_flow_roles_bind_to_a_frozen_settings_snapshot(tmp_path):
    roles = [
        FakeRole(300, "Not Verified", 0x7F8C8D),
        FakeRole(301, "Intern", 0x1ABC9C),
        FakeRole(401, "Investigator", 0x3498DB),
        FakeRole(402, "Lead Investigator", 0x9B59B6),
    ]
    settings = FrozenRoleSettings(
        database_path=tmp_path / "peace.sqlite3",
        not_verified_role_id=300,
        intern_role_id=301,
    )
    bot = PeaceBot(settings)
    bot.guild = fake_guild(roles)

    asyncio.run(bot.ensure_flow_roles())

    assert bot.settings.investigator_role_id == 401
    assert bot.settings.lead_investigator_role_id == 402
    assert bot.settings is not settings
    assert bot.settings.__dataclass_params__.frozen is True


def test_new_flow_roles_bind_on_first_startup(tmp_path):
    next_id = 500
    created = []

    async def create_role(**kwargs):
        nonlocal next_id
        role = FakeRole(next_id, kwargs["name"], kwargs["colour"].value)
        next_id += 1
        created.append(role)
        guild.roles.append(role)
        return role

    guild = fake_guild([])
    guild.create_role = create_role
    bot = PeaceBot(FrozenRoleSettings(database_path=tmp_path / "peace.sqlite3"))
    bot.guild = guild

    asyncio.run(bot.ensure_flow_roles())

    assert [role.name for role in created] == [
        "Not Verified",
        "Estagiário",
        "Investigador",
        "Investigador Chefe",
    ]
    assert bot.settings.investigator_role_id == 502
    assert bot.settings.lead_investigator_role_id == 503
