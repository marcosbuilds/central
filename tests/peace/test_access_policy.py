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
