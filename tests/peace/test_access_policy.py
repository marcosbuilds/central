from types import SimpleNamespace

from main import needs_visitor, role_member, staff_member


def member(member_id, roles=(), *, bot=False):
    return SimpleNamespace(
        id=member_id,
        roles=[SimpleNamespace(id=role_id) for role_id in roles],
        bot=bot,
    )


def test_member_without_peace_needs_visitor():
    assert needs_visitor(member(10), 200)
    assert needs_visitor(member(10, [300]), 200)


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
