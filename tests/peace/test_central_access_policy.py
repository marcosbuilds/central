from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bot.db import PeaceDatabase
from bot.main import role_member


CENTRAL_ACCESS_ROLE_ID = 1486121978468372693


def member(*role_ids: int):
    return SimpleNamespace(
        roles=[SimpleNamespace(id=role_id) for role_id in role_ids],
    )


def test_only_central_access_role_can_request_a_login_code():
    allowed = member(CENTRAL_ACCESS_ROLE_ID)
    missing_role = member(1467349800956592188)
    no_roles = member()

    assert role_member(allowed, CENTRAL_ACCESS_ROLE_ID)
    assert not role_member(missing_role, CENTRAL_ACCESS_ROLE_ID)
    assert not role_member(no_roles, CENTRAL_ACCESS_ROLE_ID)


def test_central_login_code_is_single_use(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    database.create_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        code="123456",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    )

    assert not database.consume_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        code="000000",
    )
    assert database.consume_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        code="123456",
    )
    assert not database.consume_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        code="123456",
    )


def test_developer_application_keeps_second_approval_pending(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    request_id = database.save_developer_request(
        discord_user_id=10,
        full_name="Pessoa de Teste",
        nickname="tester",
        motivation="Quero contribuir com código e documentação para a equipe.",
        area="Backend",
        specialization_time="2 anos",
        previous_experience="Projetos pessoais e colaboração em comunidades.",
        portfolio="https://example.com",
    )

    database.update_developer_request(request_id, status="interview_scheduled")
    pending = database.pending_developer_requests()

    assert [int(row["id"]) for row in pending] == [request_id]
    assert database.pending_developer_request_for_user(10)["status"] == "interview_scheduled"

    database.update_developer_request(request_id, status="approved")
    assert database.pending_developer_requests() == []
