import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from bot.core.identity import prefix_for_roles
from bot.config.settings import _validate_unique_role_ids
from bot.main import (
    DeleteUserConfirmationView,
    EntryTypeSelect,
    PeaceBot,
    StartActionView,
    founder_role_member,
    management_role_member,
    start,
)
from bot.persistence.database import PeaceDatabase


class FakeRole:
    def __init__(self, role_id, name, position):
        self.id = role_id
        self.name = name
        self.position = position
        self.managed = False

    def is_default(self):
        return self.id == 0

    def __lt__(self, other):
        return self.position < other.position


class FakeMember:
    def __init__(self, member_id, roles, guild):
        self.id = member_id
        self.name = f"member-{member_id}"
        self.display_name = self.name
        self.nick = None
        self.mention = f"<@{member_id}>"
        self.bot = False
        self.roles = list(roles)
        self.guild = guild
        self.add_roles = AsyncMock()
        self.remove_roles = AsyncMock()
        self.edit = AsyncMock()
        self.send = AsyncMock()


def settings(tmp_path, **overrides):
    values = {
        "database_path": tmp_path / "peace.sqlite3",
        "guild_id": 1,
        "peace_role_id": 200,
        "not_verified_role_id": 500,
        "visitor_role_id": 400,
        "founder_role_id": 100,
        "manager_role_id": 700,
        "founder_user_id": 1,
        "log_channel_id": 900,
        "set_vagas_abertas": True,
        "developer_vagas_abertas": False,
        "staff_vagas_abertas": False,
        "iris_enabled": False,
        "iris_url": "http://127.0.0.1:11435",
        "iris_model": "iris-test",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_access_roles_do_not_create_prefixes_but_visual_roles_do(tmp_path):
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Dev", "Staff", "Management", "Visitor"),
        founder_user_id=1,
        default="N",
    ) == "N"
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Developer"),
        founder_user_id=1,
        default="N",
    ) == "D"
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Streamer"),
        founder_user_id=1,
        default="N",
    ) == "S"
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Founder Peace"),
        founder_user_id=1,
        founder_role_names=("Founder Peace", "Founder"),
        default="N",
    ) == "F"


def test_start_menu_reuses_real_management_role_and_separates_actions(tmp_path):
    founder_role = FakeRole(100, "Founder Peace", 20)
    manager_role = FakeRole(700, "Management", 10)
    guild = SimpleNamespace(
        roles=[founder_role, manager_role],
        get_role=lambda role_id: {100: founder_role, 700: manager_role}.get(role_id),
    )
    founder = SimpleNamespace(id=10, roles=[founder_role], guild=guild)
    management = SimpleNamespace(id=11, roles=[manager_role], guild=guild)
    config = settings(tmp_path)

    assert founder_role_member(founder, config)
    assert not management_role_member(founder, config)
    assert management_role_member(management, config)
    assert not founder_role_member(management, config)

    bot = PeaceBot(config)
    founder_view = StartActionView(bot, founder.id, ("delete_user",))
    management_view = StartActionView(bot, management.id, ("announcement",))
    assert [option.value for option in founder_view.children[0].options] == ["delete_user"]
    assert [option.value for option in management_view.children[0].options] == ["announcement"]


def test_duplicate_role_ids_are_rejected_before_startup():
    with pytest.raises(RuntimeError, match="IDs de cargos duplicados"):
        _validate_unique_role_ids(
            {
                "DISCORD_PEACE_ROLE_ID": 200,
                "DISCORD_MANAGER_ROLE_ID": 200,
            }
        )


def test_start_is_silent_for_members_without_internal_roles(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    bot.authorized_dm_member = AsyncMock(return_value=None)
    response = SimpleNamespace(
        is_done=lambda: False,
        send_message=AsyncMock(),
        defer=AsyncMock(),
    )
    interaction = SimpleNamespace(
        client=bot,
        user=SimpleNamespace(id=99),
        guild=None,
        response=response,
        delete_original_response=AsyncMock(),
    )

    asyncio.run(start.callback(interaction))

    response.send_message.assert_not_awaited()
    response.defer.assert_awaited_once_with(ephemeral=True)
    interaction.delete_original_response.assert_awaited_once()


def test_request_set_selector_has_only_player_path(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    selector = EntryTypeSelect(bot)

    assert [option.value for option in selector.options] == ["player"]
    assert "developer" not in {option.value for option in selector.options}
    assert "staff" not in {option.value for option in selector.options}


def test_database_records_reservation_reason_actor_and_return_context(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    database.initialize()
    database.ensure_runtime_member(
        discord_user_id=10,
        username="member",
        nickname=None,
        role_ids=[200],
        role_names=["Peace", "Management"],
        founder_id=1,
    )

    row = database.reserve_peace_member(
        10,
        reason="cargo Peace retirado enquanto o membro permaneceu no servidor",
        actor_user_id=99,
    )
    assert row is not None
    reservation = database.reserved_peace_id_for_user(10)
    assert reservation is not None
    assert reservation["status"] == "reserved"
    assert reservation["release_reason"].startswith("cargo Peace retirado")
    assert reservation["release_actor_id"] == "99"

    request_id = database.save_return_request(
        discord_user_id=10,
        old_peace_id=int(reservation["peace_id"]),
        loss_reason=reservation["release_reason"],
        loss_actor_id=reservation["release_actor_id"],
    )
    request = database.return_request(request_id)
    assert request is not None
    assert request["loss_actor_id"] == "99"
    assert "retirado" in request["loss_reason"]

    same_request, created = database.get_or_create_return_request(
        discord_user_id=10,
        old_peace_id=int(reservation["peace_id"]),
        loss_reason="duplicated event",
    )
    assert not created
    assert same_request["id"] == request_id


def test_delete_peace_user_keeps_member_and_releases_only_valid_record(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    not_verified = FakeRole(500, "Not Verified", 5)
    founder_role = FakeRole(100, "Founder Peace", 20)
    bot_role = FakeRole(900, "PeaceBot", 100)
    guild = SimpleNamespace(
        me=SimpleNamespace(top_role=bot_role),
        roles=[peace, not_verified, founder_role, bot_role],
        text_channels=[],
        get_role=lambda role_id: {100: founder_role, 200: peace, 500: not_verified}.get(role_id),
    )
    target = FakeMember(10, [peace], guild)
    actor = FakeMember(1, [founder_role], guild)
    bot.guild = guild
    bot.member = AsyncMock(side_effect=lambda _guild, user_id: {actor.id: actor, target.id: target}.get(user_id))
    bot.send_log = AsyncMock()
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=10,
        username="member",
        nickname=None,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )

    result = asyncio.run(bot.delete_peace_users((10,), actor))

    assert "liberado" in result[0]
    target.add_roles.assert_awaited_once_with(
        not_verified,
        reason="Vínculo Peace removido por Founder 1",
    )
    target.remove_roles.assert_awaited_once_with(
        peace,
        reason="Vínculo Peace removido por Founder 1",
    )
    assert bot.database.get_member(10) is None
    with bot.database.connect() as connection:
        pool = connection.execute(
            "SELECT status, release_reason, release_actor_id FROM peace_id_pool WHERE released_from = '10'"
        ).fetchone()
    assert pool["status"] == "available"
    assert "Founder" in pool["release_reason"]
    assert pool["release_actor_id"] == "1"
    assert bot.send_log.await_count == 1


def test_delete_peace_users_rejects_management_actor_at_mutation_boundary(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    not_verified = FakeRole(500, "Not Verified", 5)
    management_role = FakeRole(700, "Management", 15)
    founder_role = FakeRole(100, "Founder Peace", 20)
    bot_role = FakeRole(900, "PeaceBot", 100)
    guild = SimpleNamespace(
        me=SimpleNamespace(top_role=bot_role),
        roles=[peace, not_verified, management_role, founder_role, bot_role],
        text_channels=[],
        get_role=lambda role_id: {
            100: founder_role,
            200: peace,
            500: not_verified,
            700: management_role,
        }.get(role_id),
    )
    target = FakeMember(10, [peace], guild)
    actor = FakeMember(11, [management_role], guild)
    bot.guild = guild
    bot.member = AsyncMock(side_effect=lambda _guild, user_id: {actor.id: actor, target.id: target}.get(user_id))
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=target.id,
        username="member",
        nickname=None,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )

    result = asyncio.run(bot.delete_peace_users((target.id,), actor))

    assert "Apenas o cargo Founder" in result[0]
    target.add_roles.assert_not_awaited()
    target.remove_roles.assert_not_awaited()
    assert bot.database.get_member(target.id) is not None


def test_loss_of_peace_creates_direct_scan_request_with_reason(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    guild = SimpleNamespace(
        me=SimpleNamespace(guild_permissions=SimpleNamespace(view_audit_log=False)),
        roles=[peace],
        get_role=lambda role_id: {200: peace}.get(role_id),
    )
    before = FakeMember(10, [peace], guild)
    after = FakeMember(10, [], guild)
    bot.guild = guild
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=10,
        username="member",
        nickname=None,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )
    bot.reconcile_visitor_role = AsyncMock()
    bot.ensure_booster_space = AsyncMock()
    bot.publish_return_request = AsyncMock()
    bot.send_log = AsyncMock()

    asyncio.run(bot.on_member_update(before, after))

    reservation = bot.database.reserved_peace_id_for_user(10)
    request = bot.database.pending_return_request_for_user(10)
    assert reservation is not None
    assert request is not None
    assert "cargo Peace retirado" in reservation["release_reason"]
    assert "cargo Peace retirado" in request["loss_reason"]
    assert request["old_peace_id"] == reservation["peace_id"]
    bot.publish_return_request.assert_awaited_once()
    assert bot.send_log.await_count == 1


def test_return_card_explains_reason_and_actor():
    request = {
        "id": 4,
        "discord_user_id": "10",
        "old_peace_id": 7,
        "loss_reason": "cargo Peace retirado enquanto o membro permaneceu no servidor",
        "loss_actor_id": "99",
        "created_at": "2026-11-10T12:00:00+00:00",
    }

    embed = PeaceBot.return_request_embed(request)
    rendered = " ".join([embed.description or "", *(field.value for field in embed.fields)])
    assert "Motivo registrado" in rendered
    assert "cargo Peace retirado" in rendered
    assert "<@99>" in rendered
    assert "Não refaça a entrevista" in rendered


def test_confirmation_view_is_a_real_second_step(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    view = DeleteUserConfirmationView(bot, 1, (10, 11))

    assert len(view.children) == 2
    assert all(getattr(button, "style", None).name == "secondary" for button in view.children)
