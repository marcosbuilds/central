import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.main import PeaceBot, needs_visitor, reviewer_member, role_member, staff_member, verification_eligible


def member(member_id, roles=(), *, bot=False):
    return SimpleNamespace(
        id=member_id,
        roles=[SimpleNamespace(id=role_id) for role_id in roles],
        bot=bot,
    )


def test_only_human_without_peace_or_visitor_needs_verification():
    assert needs_visitor(member(10), 200, 400)
    assert needs_visitor(member(10, [300]), 200, 400)
    assert not needs_visitor(member(10, [400]), 200, 400)


def test_peace_members_and_bots_do_not_need_visitor():
    assert not needs_visitor(member(10, [200]), 200)
    assert not needs_visitor(member(11, bot=True), 200)


def test_role_member_and_staff_guard_are_access_based():
    staff = member(20, [500])
    founder = member(1)
    ordinary = member(30, [600])
    settings = SimpleNamespace(founder_user_id=1, staff_role_id=500)

    assert role_member(staff, 500)
    assert staff_member(staff, settings)
    assert staff_member(founder, settings)
    assert not staff_member(ordinary, settings)


def test_reviewers_are_staff_or_management_not_recruiter_labels():
    settings = SimpleNamespace(founder_user_id=1, staff_role_id=500, manager_role_id=700)

    assert reviewer_member(member(20, [500]), settings)
    assert reviewer_member(member(21, [700]), settings)
    assert not reviewer_member(member(22, [800]), settings)


def test_verification_eligibility_excludes_bots_peace_and_existing_visitor():
    assert verification_eligible(member(10), 200, 400)
    assert not verification_eligible(member(11, [200]), 200, 400)
    assert not verification_eligible(member(12, [400]), 200, 400)
    assert not verification_eligible(member(13, bot=True), 200, 400)


def test_verification_challenge_contains_one_answer_and_expires(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
    )
    bot = PeaceBot(settings)

    choices = bot.create_verification_challenge(10)
    answer, expires_at = bot.verification_challenges[10]

    assert len(choices) == 5
    assert len(set(choices)) == 5
    assert answer in choices
    assert expires_at > 0


def test_reconcile_never_grants_visitor_without_captcha(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
    )
    bot = PeaceBot(settings)
    visitor = SimpleNamespace(id=400)
    guild = SimpleNamespace(get_role=lambda role_id: visitor)
    human = SimpleNamespace(
        id=10,
        bot=False,
        roles=[],
        guild=guild,
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )

    asyncio.run(bot.reconcile_visitor_role(human))

    human.add_roles.assert_not_awaited()
    human.remove_roles.assert_not_awaited()


def test_reconcile_assigns_not_verified_to_a_new_human(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
        not_verified_role_id=500,
    )
    bot = PeaceBot(settings)
    visitor = SimpleNamespace(id=400)
    not_verified = SimpleNamespace(id=500)
    guild = SimpleNamespace(
        get_role=lambda role_id: {400: visitor, 500: not_verified}.get(role_id),
        roles=[visitor, not_verified],
    )
    human = SimpleNamespace(
        id=10,
        bot=False,
        roles=[],
        guild=guild,
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )

    asyncio.run(bot.reconcile_visitor_role(human))

    human.add_roles.assert_awaited_once_with(
        not_verified,
        reason="Entrada exige verificação antes de Visitor",
    )
    human.remove_roles.assert_not_awaited()


def test_reconcile_removes_not_verified_after_visitor_or_peace(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        visitor_role_id=400,
        not_verified_role_id=500,
    )
    bot = PeaceBot(settings)
    visitor = SimpleNamespace(id=400)
    not_verified = SimpleNamespace(id=500)
    peace = SimpleNamespace(id=200)
    guild = SimpleNamespace(
        get_role=lambda role_id: {200: peace, 400: visitor, 500: not_verified}.get(role_id),
        roles=[peace, visitor, not_verified],
    )
    verified = SimpleNamespace(
        id=10,
        bot=False,
        roles=[visitor, not_verified],
        guild=guild,
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )
    peace_member = SimpleNamespace(
        id=11,
        bot=False,
        roles=[peace, not_verified],
        guild=guild,
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
    )

    asyncio.run(bot.reconcile_visitor_role(verified))
    asyncio.run(bot.reconcile_visitor_role(peace_member))

    verified.remove_roles.assert_awaited_once_with(
        not_verified,
        reason="Visitor já está verificado",
    )
    peace_member.remove_roles.assert_awaited_once_with(
        not_verified,
        reason="Membro Peace não é visitante nem Not Verified",
    )


def test_approved_set_assigns_peace_and_intern_without_requiring_novato(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        peace_role_id=200,
        novato_role_id=300,
        visitor_role_id=400,
        not_verified_role_id=500,
        intern_role_id=600,
        founder_user_id=1,
    )
    bot = PeaceBot(settings)
    bot.database.initialize()
    peace = SimpleNamespace(id=200, name="Peace")
    visitor = SimpleNamespace(id=400, name="Visitor")
    not_verified = SimpleNamespace(id=500, name="Not Verified")
    intern = SimpleNamespace(id=600, name="Estagiário")
    guild = SimpleNamespace(
        get_role=lambda role_id: {
            200: peace,
            400: visitor,
            500: not_verified,
            600: intern,
        }.get(role_id),
        roles=[peace, visitor, not_verified, intern],
    )
    target = SimpleNamespace(
        id=10,
        name="candidate",
        nick=None,
        mention="<@10>",
        roles=[],
        add_roles=AsyncMock(),
        remove_roles=AsyncMock(),
        edit=AsyncMock(),
        send=AsyncMock(),
    )
    reviewer = SimpleNamespace(
        id=20,
        guild=guild,
        mention="<@20>",
        display_name="Staff",
    )
    bot.member = AsyncMock(return_value=target)

    result = asyncio.run(
        bot.approve_set_request(
            {
                "id": 1,
                "discord_user_id": 10,
                "in_game_username": "candidate",
            },
            reviewer,
        )
    )

    assert "Set aprovado" in result
    target.add_roles.assert_awaited_once_with(
        peace,
        intern,
        reason="Set aprovado manualmente por Staff ou Management 20",
    )
    target.remove_roles.assert_any_await(visitor, reason="Set aprovado: visitante convertido em Peace")
    target.remove_roles.assert_any_await(not_verified, reason="Set aprovado: membro convertido em Peace")
