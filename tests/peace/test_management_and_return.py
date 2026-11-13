import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import discord
import pytest

from bot.core.identity import prefix_for_roles
from bot.commands.nick import alias_from_member, build_name, peace_id_from_member
from bot.config.settings import _validate_unique_role_ids
from bot.main import (
    DeleteUserConfirmationView,
    DeleteUserSelectionView,
    DeleteUserSelect,
    EntryTypeSelect,
    PeaceBot,
    ReturnApprovalView,
    StartActionView,
    canonical_management_role_id,
    founder_role_member,
    management_role_member,
    start,
)
from bot.persistence.database import PeaceDatabase


class FakeRole:
    def __init__(self, role_id, name, position, hoist=True):
        self.id = role_id
        self.name = name
        self.position = position
        self.hoist = hoist
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
        async def edit_member(**kwargs):
            if "roles" in kwargs and kwargs["roles"] is not None:
                self.roles = list(kwargs["roles"])
            if "nick" in kwargs:
                self.nick = kwargs["nick"]
                self.display_name = self.nick or self.name

        self.edit = AsyncMock(side_effect=edit_member)
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
        role_names=("AIs",),
        founder_user_id=1,
        default="N",
    ) == "A"
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


def test_translated_visual_roles_keep_their_stable_peace_prefixes():
    expected = {
        "Delegado": "DEL",
        "Developer": "D",
        "Diretor Geral": "G",
        "Agente Especial": "E",
        "Agente": "M",
        "Aluno": "R",
        "Estagiário": "I",
        "Streamer": "S",
    }
    for role_name, prefix in expected.items():
        assert prefix_for_roles(
            user_id=10,
            role_names=("Peace", role_name),
            founder_user_id=1,
            default="N",
        ) == prefix

    for role_name in (
        "Gerência",
        "Visitante",
        "Apoiador",
        "Not Verified",
        "Investigador",
        "Investigador Chefe",
    ):
        assert prefix_for_roles(
            user_id=10,
            role_names=("Peace", role_name),
            founder_user_id=1,
            default="N",
        ) == "N"


def test_highest_live_visual_role_wins_over_prefix_precedence():
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Developer", "Streamer", "Management"),
        founder_user_id=1,
        default="N",
        role_positions={"Peace": 4, "Developer": 8, "Streamer": 22, "Management": 15},
    ) == "S"
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Developer", "Streamer", "Staff"),
        founder_user_id=1,
        default="N",
        role_positions={"Peace": 20, "Developer": 30, "Streamer": 10, "Staff": 40},
    ) == "D"


def test_live_display_separation_filters_visual_prefixes_but_not_founder():
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Developer", "Streamer", "Dev", "Staff"),
        founder_user_id=1,
        default="N",
        role_positions={"Peace": 4, "Developer": 30, "Streamer": 22, "Dev": 40, "Staff": 50},
        role_hoist={"Peace": False, "Developer": False, "Streamer": True, "Dev": True, "Staff": True},
    ) == "S"
    assert prefix_for_roles(
        user_id=10,
        role_names=("Developer", "Streamer"),
        founder_user_id=1,
        role_positions={"Developer": 30, "Streamer": 22},
        role_hoist={"Developer": True, "Streamer": True},
    ) == "D"
    assert prefix_for_roles(
        user_id=1,
        role_names=("Founder Peace",),
        founder_user_id=1,
        role_positions={"Founder Peace": 100},
        role_hoist={"Founder Peace": False},
    ) == "F"


def test_live_visual_role_uses_stable_code_and_ignores_hoisted_access_roles():
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Intern", "Rookie ⎰ Agent"),
        founder_user_id=1,
        default="N",
        role_positions={"Peace": 4, "Intern": 8, "Rookie ⎰ Agent": 12},
        role_hoist={"Peace": False, "Intern": True, "Rookie ⎰ Agent": True},
    ) == "R"
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Manager ⎰ Deputy Delegate", "Staff"),
        founder_user_id=1,
        default="N",
        role_positions={"Peace": 4, "Manager ⎰ Deputy Delegate": 30, "Staff": 40},
        role_hoist={"Peace": False, "Manager ⎰ Deputy Delegate": True, "Staff": True},
    ) == "DEL"


def test_manager_code_requires_discord_display_separation():
    assert prefix_for_roles(
        user_id=10,
        role_names=("Peace", "Manager ⎰ Deputy Delegate"),
        founder_user_id=1,
        default="N",
        role_positions={"Peace": 4, "Manager ⎰ Deputy Delegate": 30},
        role_hoist={"Peace": False, "Manager ⎰ Deputy Delegate": False},
    ) == "N"


def test_multi_letter_prefix_parser_and_formatter_preserve_alias_and_id():
    assert alias_from_member({"nick": "DEL ⎰ Kamikaze 21"}, "fallback") == "Kamikaze"
    assert alias_from_member({"nick": "R ⎰ Kamikaze 21"}, "fallback") == "Kamikaze"
    assert alias_from_member({"nick": "Kamikaze 21"}, "fallback") == "Kamikaze"
    proposed = build_name("DEL", "Kamikaze", 21)
    assert proposed == "DEL ⎰ Kamikaze 21"
    assert len(proposed) <= 32


def test_multi_letter_prefix_formatter_keeps_long_peace_id_intact():
    proposed = build_name("DEL", "a" * 40, 12345678)
    assert proposed.endswith(" 12345678")
    assert len(proposed) <= 32


def test_prefix_repair_can_preserve_the_live_peace_id():
    assert peace_id_from_member({"nick": "R ⎰ Peaceiro 42"}) == 42
    assert peace_id_from_member({"nick": "Peaceiro 42"}) is None


def test_nickname_backfill_role_maps_support_member_role_ids():
    # The live Discord member payload contains role IDs, while prefix policy
    # also needs names for visual-role matching. Keep both lookup forms alive.
    roles = [
        {"id": "10", "name": "Peace", "position": 4, "hoist": False},
        {"id": "11", "name": "Streamer", "position": 22, "hoist": True},
    ]
    role_positions = {}
    role_hoist = {}
    for role in roles:
        role_id = str(role["id"])
        role_name = str(role["name"])
        role_positions[role_id] = role_positions[role_name] = int(role["position"])
        role_hoist[role_id] = role_hoist[role_name] = bool(role["hoist"])

    assert role_positions["11"] == role_positions["Streamer"] == 22
    assert role_hoist["11"] is role_hoist["Streamer"] is True


def test_peace_nickname_repairs_manager_prefix_without_duplicating_alias(tmp_path):
    config = settings(tmp_path, booster_role_id=None, private_call_category_id=None)
    peace = FakeRole(200, "Peace", 4, hoist=False)
    manager = FakeRole(700, "Manager ⎰ Deputy Delegate", 30, hoist=True)
    guild = SimpleNamespace(roles=[peace, manager])
    member = FakeMember(21, [peace, manager], guild)
    member.nick = "R ⎰ Kamikaze 21"
    member.display_name = member.nick

    assert PeaceBot.peace_nickname(
        member,
        role_names=[role.name for role in member.roles],
        peace_id=21,
        settings=config,
        role_positions={role.name: role.position for role in member.roles},
        role_hoist={role.name: role.hoist for role in member.roles},
    ) == "DEL ⎰ Kamikaze 21"


def test_member_role_update_rebuilds_nickname_from_live_visual_priority(tmp_path):
    bot = PeaceBot(
        settings(
            tmp_path,
            booster_role_id=None,
            private_call_category_id=None,
        )
    )
    peace = FakeRole(200, "Peace", 4)
    developer = FakeRole(201, "Developer", 8)
    streamer = FakeRole(202, "Streamer", 22)
    bot_role = FakeRole(900, "PeaceBot", 100)
    guild = SimpleNamespace(
        me=SimpleNamespace(top_role=bot_role),
        roles=[peace, developer, streamer, bot_role],
        get_role=lambda role_id: {200: peace, 201: developer, 202: streamer}.get(role_id),
    )
    before = FakeMember(10, [peace, developer], guild)
    before.nick = "N ⎰ member-10 1"
    before.display_name = before.nick
    after = FakeMember(10, [peace, developer, streamer], guild)
    after.nick = before.nick
    after.display_name = after.nick
    bot.guild = guild
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=after.id,
        username=after.name,
        nickname=before.nick,
        role_ids=[role.id for role in before.roles],
        role_names=[role.name for role in before.roles],
        founder_id=1,
        role_positions={role.name: role.position for role in before.roles},
    )

    asyncio.run(bot.on_member_update(before, after))

    assert after.nick.startswith("S ⎰")
    assert bot.database.get_member(after.id)["name_prefix"] == "S"


def test_startup_tag_sync_fetches_existing_members_outside_gateway_cache(tmp_path):
    config = settings(tmp_path, booster_role_id=None, private_call_category_id=None)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 4)
    streamer = FakeRole(202, "Streamer", 22, hoist=True)
    guild = SimpleNamespace(
        members=[],
        roles=[peace, streamer],
        get_role=lambda role_id: {200: peace, 202: streamer}.get(role_id),
    )
    existing = FakeMember(24, [peace, streamer], guild)
    existing.nick = "member-24 1"
    existing.display_name = existing.nick

    async def fetch_members(*, limit=None):
        assert limit is None
        yield existing

    guild.fetch_members = fetch_members
    bot.guild = guild
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=existing.id,
        username=existing.name,
        nickname=existing.nick,
        role_ids=[role.id for role in existing.roles],
        role_names=[role.name for role in existing.roles],
        founder_id=1,
        role_positions={role.name: role.position for role in existing.roles},
        role_hoist={role.name: role.hoist for role in existing.roles},
    )

    summary = asyncio.run(bot.sync_peace_tags())

    assert existing.nick == "S ⎰ member-24 1"
    assert summary["fetched"] is True
    assert summary["seen"] == 1
    assert summary["updated"] == 1
    assert summary["failed"] == 0


def test_pending_return_with_peace_role_repairs_nickname_without_recreating_record(tmp_path):
    config = settings(tmp_path, booster_role_id=None, private_call_category_id=None)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 4, hoist=False)
    streamer = FakeRole(202, "Streamer", 22, hoist=True)
    guild = SimpleNamespace(
        members=[],
        chunked=True,
        roles=[peace, streamer],
        get_role=lambda role_id: {200: peace, 202: streamer}.get(role_id),
    )
    member = FakeMember(24, [peace, streamer], guild)
    member.nick = "N ⎰ member-24 1"
    member.display_name = member.nick
    guild.members = [member]
    bot.guild = guild
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=member.id,
        username=member.name,
        nickname=member.nick,
        role_ids=[role.id for role in member.roles],
        role_names=[role.name for role in member.roles],
        founder_id=1,
        role_positions={role.name: role.position for role in member.roles},
        role_hoist={role.name: role.hoist for role in member.roles},
    )
    reservation = bot.database.reserve_peace_member(member.id, reason="cargo Peace perdido")
    assert reservation is not None
    request, _ = bot.database.get_or_create_return_request(
        discord_user_id=member.id,
        old_peace_id=int(reservation["peace_id"]),
        loss_reason="cargo Peace perdido",
    )

    summary = asyncio.run(bot.sync_peace_tags())

    assert member.nick == f"S ⎰ member-24 {int(reservation['peace_id'])}"
    assert bot.database.get_member(member.id) is None
    assert bot.database.return_request(request["id"])["status"] == "pending"
    assert summary["returned"] == 1
    assert summary["updated"] == 1


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


def test_management_role_uses_structural_id_when_env_is_not_set(tmp_path):
    role = FakeRole(1471532522394615850, "Management", 10)
    guild = SimpleNamespace(
        roles=[role],
        get_role=lambda role_id: role if role_id == role.id else None,
    )
    member = SimpleNamespace(id=11, roles=[role], guild=guild)
    config = settings(tmp_path, manager_role_id=None)

    assert canonical_management_role_id() == role.id
    assert management_role_member(member, config)


def test_start_actions_resolve_canonical_management_role_from_real_member(tmp_path):
    role = FakeRole(1471532522394615850, "Management", 10)
    guild = SimpleNamespace(
        roles=[role],
        get_role=lambda role_id: role if role_id == role.id else None,
    )
    member = SimpleNamespace(id=11, roles=[role], guild=guild)
    bot = PeaceBot(settings(tmp_path, manager_role_id=None))
    bot.guild = guild
    bot.member = AsyncMock(return_value=member)

    assert asyncio.run(bot.start_actions_for(member.id)) == ("announcement",)


def test_founder_delete_candidates_are_loaded_from_the_peace_server(tmp_path):
    peace_role = FakeRole(200, "Peace", 10)
    founder_role = FakeRole(100, "Founder Peace", 30)
    members = []

    async def fetch_members(limit=None):
        for member in members:
            yield member

    guild = SimpleNamespace(
        roles=[peace_role, founder_role],
        members=members,
        get_role=lambda role_id: {
            peace_role.id: peace_role,
            founder_role.id: founder_role,
        }.get(role_id),
        fetch_members=fetch_members,
    )
    members.extend(
        [
            FakeMember(1, [peace_role, founder_role], guild),
            FakeMember(10, [peace_role], guild),
            FakeMember(11, [peace_role], guild),
            FakeMember(12, [], guild),
        ]
    )
    bot = PeaceBot(settings(tmp_path))
    bot.guild = guild

    candidates = asyncio.run(bot.delete_peace_candidates())

    assert [member.id for member in candidates] == [10, 11]


def test_founder_delete_selection_paginates_server_candidates(tmp_path):
    peace_role = FakeRole(200, "Peace", 10)
    guild = SimpleNamespace(roles=[peace_role])
    candidates = [FakeMember(100 + index, [peace_role], guild) for index in range(30)]
    bot = PeaceBot(settings(tmp_path))

    view = DeleteUserSelectionView(bot, 1, candidates)
    selector = view.children[0]

    assert view.total_pages == 2
    assert selector.__class__.__name__ == "DeleteUserSelect"
    assert len(selector.options) == 25
    assert selector.options[0].value == "100"
    assert any(getattr(item, "label", "") == "Próxima →" for item in view.children)


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


def test_start_sends_persistent_menu_to_authorized_dm_member(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    bot.authorized_dm_member = AsyncMock(
        side_effect=lambda _user_id, role_kind: (
            SimpleNamespace(id=99) if role_kind in {"founder", "management"} else None
        )
    )
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
    )

    asyncio.run(start.callback(interaction))

    kwargs = response.send_message.call_args.kwargs
    assert kwargs["ephemeral"] is False
    assert isinstance(kwargs["view"], StartActionView)
    assert [option.value for option in kwargs["view"].children[0].options] == [
        "delete_user",
        "announcement",
    ]


def test_text_start_in_dm_uses_the_same_authorized_menu(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    bot.authorized_dm_member = AsyncMock(
        side_effect=lambda _user_id, role_kind: (
            SimpleNamespace(id=99) if role_kind == "management" else None
        )
    )
    channel = SimpleNamespace(id=123, send=AsyncMock())
    message = SimpleNamespace(
        author=SimpleNamespace(id=99, bot=False),
        guild=None,
        content="/start",
        channel=channel,
        id=456,
    )

    asyncio.run(bot.on_message(message))

    channel.send.assert_awaited_once()
    assert [option.value for option in channel.send.call_args.kwargs["view"].children[0].options] == [
        "announcement",
    ]


def test_text_start_in_dm_stays_silent_without_internal_role(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    bot.authorized_dm_member = AsyncMock(return_value=None)
    channel = SimpleNamespace(id=123, send=AsyncMock())
    message = SimpleNamespace(
        author=SimpleNamespace(id=99, bot=False),
        guild=None,
        content="start",
        channel=channel,
        id=456,
    )

    asyncio.run(bot.on_message(message))

    channel.send.assert_not_awaited()


def test_management_announcement_is_published_as_card_with_markdown_and_image(tmp_path):
    config = settings(tmp_path, announcement_channel_id=600)
    bot = PeaceBot(config)
    actor = SimpleNamespace(
        id=99,
        name="manager",
        display_name="Management",
        mention="<@99>",
        display_avatar=SimpleNamespace(url="https://cdn.example/avatar.png"),
    )
    attachment = SimpleNamespace(
        filename="announcement.png",
        content_type="image/png",
        size=128,
        to_file=AsyncMock(return_value=SimpleNamespace(filename="announcement.png")),
    )
    source = SimpleNamespace(
        content="**Aviso importante**\n[Leia mais](https://example.com)",
        attachments=[attachment],
    )
    channel = MagicMock(spec=discord.TextChannel)
    channel.mention = "<#600>"
    channel.send = AsyncMock(return_value=SimpleNamespace(id=700, jump_url="https://discord.com/channels/1/600/700"))
    bot.guild = SimpleNamespace(
        get_channel=lambda channel_id: channel if channel_id == 600 else None,
        get_role=lambda role_id: SimpleNamespace(id=role_id, mention=f"<@&{role_id}>"),
        text_channels=[channel],
    )
    bot.authorized_dm_member = AsyncMock(return_value=actor)
    bot.send_log = AsyncMock()

    result = asyncio.run(bot.publish_announcement(source, actor))

    kwargs = channel.send.call_args.kwargs
    assert kwargs["content"] == "<@&200>"
    assert kwargs["allowed_mentions"].roles is True
    assert kwargs["allowed_mentions"].users is False
    assert kwargs["embed"].description == source.content
    assert kwargs["embed"].author.name == "Peace · Avisos"
    assert kwargs["embed"].image.url == "attachment://announcement.png"
    assert kwargs["files"]
    assert "Aviso publicado" in result


def test_delete_selection_edits_the_existing_interaction_message(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    candidate = FakeMember(10, [], SimpleNamespace())
    selector = DeleteUserSelect(bot, 1, [candidate], page=0, total_pages=1)
    selector._values = ["10"]
    bot.authorized_dm_member = AsyncMock(return_value=SimpleNamespace(id=1))
    response = SimpleNamespace(
        edit_message=AsyncMock(),
        send_message=AsyncMock(),
    )
    interaction = SimpleNamespace(
        user=SimpleNamespace(id=1),
        guild=None,
        response=response,
    )

    asyncio.run(selector.callback(interaction))

    response.edit_message.assert_awaited_once()
    response.send_message.assert_not_awaited()
    assert isinstance(response.edit_message.call_args.kwargs["view"], DeleteUserConfirmationView)


def test_delete_confirmation_updates_the_same_message_after_processing(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    actor = SimpleNamespace(id=1)
    bot.authorized_dm_member = AsyncMock(return_value=actor)
    bot.delete_peace_users = AsyncMock(return_value=["ok"])
    view = DeleteUserConfirmationView(bot, 1, (10,))
    response = SimpleNamespace(edit_message=AsyncMock(), defer=AsyncMock())
    message = SimpleNamespace(edit=AsyncMock(), delete=AsyncMock())
    interaction = SimpleNamespace(
        user=actor,
        guild=None,
        response=response,
        message=message,
    )

    asyncio.run(view.children[0].callback(interaction))

    response.edit_message.assert_awaited_once()
    message.edit.assert_awaited_once()
    assert "Resultado da exclusão" in message.edit.call_args.kwargs["content"]
    assert bot.delete_peace_users.await_args.args == ((10,), actor)
    assert callable(bot.delete_peace_users.await_args.kwargs["progress_callback"])


def test_delete_confirmation_renders_progress_bar_and_processed_users(tmp_path):
    bot = PeaceBot(settings(tmp_path))
    actor = SimpleNamespace(id=1)
    bot.authorized_dm_member = AsyncMock(return_value=actor)

    async def delete_with_progress(_target_ids, _actor, *, progress_callback):
        await progress_callback(1, 2, ("<@10>: vínculo removido e ID `10` liberado.",))
        await progress_callback(
            2,
            2,
            (
                "<@10>: vínculo removido e ID `10` liberado.",
                "<@11>: vínculo removido e ID `11` liberado.",
            ),
        )
        return ["<@10>: vínculo removido e ID `10` liberado.", "<@11>: vínculo removido e ID `11` liberado."]

    bot.delete_peace_users = AsyncMock(side_effect=delete_with_progress)
    view = DeleteUserConfirmationView(bot, 1, (10, 11))
    response = SimpleNamespace(edit_message=AsyncMock(), defer=AsyncMock())
    message = SimpleNamespace(edit=AsyncMock(), delete=AsyncMock())
    interaction = SimpleNamespace(
        user=actor,
        guild=None,
        response=response,
        message=message,
    )

    asyncio.run(view.children[0].callback(interaction))

    assert "0/2" in response.edit_message.call_args.kwargs["content"]
    progress_messages = [call.kwargs["content"] for call in message.edit.await_args_list]
    assert any("1/2" in content and "50%" in content for content in progress_messages)
    assert any("2/2" in content and "100%" in content for content in progress_messages)
    assert any("<@11>: vínculo removido" in content for content in progress_messages)


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


def test_database_reconciles_active_record_even_when_role_snapshot_is_stale(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    database.initialize()
    database.ensure_runtime_member(
        discord_user_id=10,
        username="member",
        nickname=None,
        role_ids=[200],
        role_names=["Peace"],
        founder_id=1,
    )
    with database.connect() as connection:
        connection.execute("DELETE FROM member_roles WHERE discord_user_id = '10'")
        connection.commit()

    reserved = database.reserve_missing_peace_members(
        current_user_ids={10},
        peace_role_id=200,
        current_peace_user_ids=set(),
    )

    assert len(reserved) == 1
    assert database.get_member(10) is None
    assert database.reserved_peace_id_for_user(10) is not None


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
    target.nick = "apelido personalizado"
    target.display_name = target.nick
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
    assert target.edit.await_count == 2
    nickname_edit, role_edit = target.edit.await_args_list
    assert nickname_edit.kwargs["nick"] is None
    assert "roles" not in nickname_edit.kwargs
    assert role_edit.kwargs["roles"] == [not_verified]
    assert "nick" not in role_edit.kwargs
    assert target.roles == [not_verified]
    assert target.nick is None
    assert bot.database.get_member(10) is None
    with bot.database.connect() as connection:
        pool = connection.execute(
            "SELECT status, release_reason, release_actor_id FROM peace_id_pool WHERE released_from = '10'"
        ).fetchone()
    assert pool["status"] == "available"
    assert "Founder" in pool["release_reason"]
    assert pool["release_actor_id"] == "1"
    assert bot.send_log.await_count == 1

    repeated = asyncio.run(bot.delete_peace_users((10,), actor))
    assert "já confirmada" in repeated[0]
    assert target.edit.await_count == 2
    assert bot.send_log.await_count == 1


def test_delete_peace_user_uses_live_role_when_role_snapshot_is_stale(tmp_path):
    config = settings(tmp_path)
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
    bot = PeaceBot(config)
    bot.guild = guild
    bot.member = AsyncMock(side_effect=lambda _guild, user_id: {actor.id: actor, target.id: target}.get(user_id))
    bot.send_log = AsyncMock()
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=target.id,
        username="member",
        nickname=None,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )
    with bot.database.connect() as connection:
        connection.execute("DELETE FROM member_roles WHERE discord_user_id = ?", (str(target.id),))
        connection.commit()

    result = asyncio.run(bot.delete_peace_users((target.id,), actor))

    assert "vínculo removido" in result[0]
    assert target.roles == [not_verified]
    assert bot.database.get_member(target.id) is None
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


def test_missing_peace_audit_accepts_approved_return_members_without_name_error(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    member = SimpleNamespace(id=10, roles=[peace])
    bot.guild = SimpleNamespace(members=[member])
    bot.database.approved_return_user_ids = MagicMock(return_value={10})
    bot.database.reserve_missing_peace_members = MagicMock(return_value=[])

    asyncio.run(bot.sync_missing_peace_ids())

    bot.database.reserve_missing_peace_members.assert_called_once_with(
        current_user_ids={10},
        peace_role_id=200,
        current_peace_user_ids={10},
    )


def test_pending_return_sync_reuses_stored_card_instead_of_sending_duplicate(tmp_path):
    config = settings(tmp_path, scan_channel_id=600)
    bot = PeaceBot(config)
    bot._connection.user = SimpleNamespace(id=99)
    peace = FakeRole(200, "Peace", 10)
    guild = SimpleNamespace(
        get_channel=lambda channel_id: channel if channel_id == 600 else None,
        get_role=lambda role_id: peace if role_id == peace.id else None,
    )
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
    reservation = bot.database.reserve_peace_member(10, reason="membro saiu do servidor")
    request, _ = bot.database.get_or_create_return_request(
        discord_user_id=10,
        old_peace_id=int(reservation["peace_id"]),
        loss_reason="membro saiu do servidor",
    )
    bot.database.set_return_request_message(request["id"], 123)
    component = SimpleNamespace(custom_id=f"peace_return_release_{request['id']}")
    message = SimpleNamespace(
        id=123,
        author=SimpleNamespace(id=99),
        components=[SimpleNamespace(children=[component])],
        edit=AsyncMock(),
        delete=AsyncMock(),
    )
    channel = MagicMock(spec=discord.TextChannel)
    channel.fetch_message = AsyncMock(return_value=message)

    async def history(**_kwargs):
        if False:
            yield message

    channel.history = history
    bot.return_approval_view = MagicMock(return_value=object())

    asyncio.run(bot.sync_pending_return_panels())

    channel.fetch_message.assert_awaited_once_with(123)
    channel.send.assert_not_called()
    message.edit.assert_awaited_once()


def test_approved_return_repair_skips_member_with_a_new_active_id(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    bot_role = FakeRole(900, "PeaceBot", 100)
    guild = SimpleNamespace(
        me=SimpleNamespace(top_role=bot_role),
        roles=[peace, bot_role],
        get_role=lambda role_id: peace if role_id == peace.id else None,
    )
    target = FakeMember(10, [peace], guild)
    target.nick = "N ⎰ member-10 99"
    target.display_name = target.nick
    bot.guild = guild
    bot.member = AsyncMock(return_value=target)
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=target.id,
        username=target.name,
        nickname=target.nick,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )
    reservation = bot.database.reserve_peace_member(target.id, reason="membro saiu do servidor")
    request, _ = bot.database.get_or_create_return_request(
        discord_user_id=target.id,
        old_peace_id=int(reservation["peace_id"]),
        loss_reason="membro saiu do servidor",
    )
    approved = bot.database.approve_return_request(
        request["id"],
        username=target.name,
        nickname=target.nick,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )
    assert approved is not None
    with bot.database.connect() as connection:
        connection.execute(
            "UPDATE members SET peace_id = ?, nickname = ? WHERE discord_user_id = ?",
            (99, "N ⎰ member-10 99", str(target.id)),
        )
        connection.commit()

    asyncio.run(bot.sync_approved_return_requests())

    target.edit.assert_not_awaited()
    assert bot.database.get_member(target.id)["peace_id"] == 99


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


def test_manual_delete_cleanup_repairs_old_state_but_skips_a_new_set(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    not_verified = FakeRole(500, "Not Verified", 5)
    bot_role = FakeRole(900, "PeaceBot", 100)
    guild = SimpleNamespace(
        me=SimpleNamespace(top_role=bot_role),
        roles=[peace, not_verified, bot_role],
        get_role=lambda role_id: {200: peace, 500: not_verified}.get(role_id),
    )
    target = FakeMember(10, [peace], guild)
    target.nick = "N ⎰ member-10 7"
    target.display_name = target.nick
    bot.guild = guild
    bot.member = AsyncMock(return_value=target)
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=10,
        username=target.name,
        nickname=target.nick,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )
    bot.database.release_peace_member(
        target.id,
        reason="vínculo Peace removido manualmente por Founder 1",
        actor_user_id=1,
    )

    original_apply = bot.apply_removed_member_state
    bot.ensure_return_request = AsyncMock(return_value=False)
    bot.sync_member_tag = AsyncMock()

    async def apply_with_intermediate_event(*args, **kwargs):
        assert target.id in bot.managed_peace_role_removals
        before = SimpleNamespace(
            id=target.id,
            bot=False,
            roles=[peace],
            nick=target.nick,
            guild=guild,
        )
        after = SimpleNamespace(
            id=target.id,
            bot=False,
            roles=[peace],
            nick=None,
            guild=guild,
        )
        await bot.on_member_update(before, after)
        bot.sync_member_tag.assert_not_awaited()
        await original_apply(*args, **kwargs)

    bot.apply_removed_member_state = apply_with_intermediate_event

    asyncio.run(bot.sync_released_member_cleanup())

    assert target.roles == [not_verified]
    assert target.nick is None
    target.edit.reset_mock()

    target.roles = [peace]
    target.nick = "N ⎰ member-10 8"
    target.display_name = target.nick
    bot.database.ensure_runtime_member(
        discord_user_id=target.id,
        username=target.name,
        nickname=target.nick,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )

    asyncio.run(bot.sync_released_member_cleanup())

    target.edit.assert_not_awaited()


def test_rejected_return_keeps_reservation_and_does_not_reopen(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    guild = SimpleNamespace(
        me=SimpleNamespace(top_role=FakeRole(900, "PeaceBot", 100)),
        roles=[peace],
        get_role=lambda role_id: peace if role_id == peace.id else None,
    )
    member = FakeMember(10, [peace], guild)
    bot.guild = guild
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=member.id,
        username=member.name,
        nickname=None,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )
    reservation = bot.database.reserve_peace_member(member.id, reason="saiu do servidor")
    request, created = bot.database.get_or_create_return_request(
        discord_user_id=member.id,
        old_peace_id=int(reservation["peace_id"]),
        loss_reason="saiu do servidor",
    )
    assert created

    rejected = bot.database.reject_return_request(request["id"])

    assert rejected["status"] == "rejected"
    assert bot.database.reserved_peace_id_for_user(member.id) is not None
    bot.member = AsyncMock(return_value=member)
    assert asyncio.run(bot.ensure_return_request(member)) is True
    assert bot.database.pending_return_request_for_user(member.id) is None


def test_reject_return_callback_edits_card_and_keeps_reserved_id(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    founder_role = FakeRole(100, "Founder Peace", 20)
    guild = SimpleNamespace(
        me=SimpleNamespace(top_role=FakeRole(900, "PeaceBot", 100)),
        roles=[peace, founder_role],
        get_role=lambda role_id: {peace.id: peace, founder_role.id: founder_role}.get(role_id),
    )
    target = FakeMember(10, [peace], guild)
    bot.guild = guild
    bot.member = AsyncMock(return_value=target)
    bot.send_log = AsyncMock()
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=target.id,
        username=target.name,
        nickname=None,
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )
    reservation = bot.database.reserve_peace_member(target.id, reason="membro saiu do servidor")
    request, _ = bot.database.get_or_create_return_request(
        discord_user_id=target.id,
        old_peace_id=int(reservation["peace_id"]),
        loss_reason="membro saiu do servidor",
    )
    reviewer = MagicMock(spec=discord.Member)
    reviewer.id = 1
    reviewer.roles = [founder_role]
    reviewer.guild = guild
    reviewer.mention = "<@1>"
    response = SimpleNamespace(is_done=lambda: response.edit_message.await_count > 0, edit_message=AsyncMock())
    followup = SimpleNamespace(send=AsyncMock())
    message = SimpleNamespace(edit=AsyncMock(), delete=AsyncMock())
    interaction = SimpleNamespace(
        user=reviewer,
        guild=guild,
        response=response,
        followup=followup,
        message=message,
    )

    view = ReturnApprovalView(bot, int(request["id"]))
    asyncio.run(view.children[1].callback(interaction))

    assert bot.database.return_request(request["id"])["status"] == "rejected"
    assert bot.database.reserved_peace_id_for_user(target.id)["peace_id"] == reservation["peace_id"]
    assert target.roles == [peace]
    assert target.nick is None
    assert target.send.await_count == 1
    assert bot.send_log.await_count == 1
    response.edit_message.assert_awaited_once()
    followup.send.assert_awaited_once()
    assert followup.send.await_args.kwargs["embed"].title == "Retorno recusado"
    message.edit.assert_not_awaited()
    message.delete.assert_awaited_once()
    assert all(button.disabled for button in view.children)


def test_return_approval_view_has_release_and_reject_actions(tmp_path):
    view = ReturnApprovalView(PeaceBot(settings(tmp_path)), 4)

    assert [button.label for button in view.children] == ["Liberar ID", "Recusar retorno"]
    assert [button.custom_id for button in view.children] == [
        "peace_return_release_4",
        "peace_return_reject_4",
    ]


def test_return_approval_assigns_peace_removes_entry_roles_and_updates_nickname(tmp_path):
    config = settings(tmp_path)
    bot = PeaceBot(config)
    peace = FakeRole(200, "Peace", 10)
    visitor = FakeRole(400, "Visitor", 4)
    not_verified = FakeRole(500, "Not Verified", 5)
    bot_role = FakeRole(900, "PeaceBot", 100)
    guild = SimpleNamespace(
        me=SimpleNamespace(top_role=bot_role),
        roles=[peace, visitor, not_verified, bot_role],
        get_role=lambda role_id: {
            peace.id: peace,
            visitor.id: visitor,
            not_verified.id: not_verified,
        }.get(role_id),
    )
    target = FakeMember(10, [not_verified], guild)
    target.nick = "N ⎰ member-10 24"
    target.display_name = target.nick
    bot.guild = guild
    bot.member = AsyncMock(return_value=target)
    bot.send_log = AsyncMock()
    bot.database.initialize()
    bot.database.ensure_runtime_member(
        discord_user_id=target.id,
        username=target.name,
        nickname="N ⎰ member-10 24",
        role_ids=[peace.id],
        role_names=[peace.name],
        founder_id=1,
    )
    reservation = bot.database.reserve_peace_member(target.id, reason="cargo Peace perdido")
    request, _ = bot.database.get_or_create_return_request(
        discord_user_id=target.id,
        old_peace_id=int(reservation["peace_id"]),
        loss_reason="cargo Peace perdido",
    )
    reviewer = MagicMock(spec=discord.Member)
    reviewer.id = 1
    reviewer.roles = []
    reviewer.guild = guild
    reviewer.mention = "<@1>"
    response = SimpleNamespace(is_done=lambda: response.edit_message.await_count > 0, edit_message=AsyncMock())
    followup = SimpleNamespace(send=AsyncMock())
    interaction = SimpleNamespace(
        user=reviewer,
        guild=guild,
        response=response,
        followup=followup,
        message=SimpleNamespace(edit=AsyncMock(), delete=AsyncMock()),
    )

    view = ReturnApprovalView(bot, int(request["id"]))
    asyncio.run(view.children[0].callback(interaction))

    assert target.roles == [peace]
    assert target.nick == "N ⎰ member-10 2"
    assert bot.database.return_request(request["id"])["status"] == "approved"
    assert bot.database.get_member(target.id)["peace_id"] == 2
    assert bot.send_log.await_count == 1
    interaction.response.edit_message.assert_awaited_once()
    followup.send.assert_awaited_once()
    assert followup.send.await_args.kwargs["embed"].title == "Retorno aprovado"
    interaction.message.edit.assert_not_awaited()
    interaction.message.delete.assert_awaited_once()
