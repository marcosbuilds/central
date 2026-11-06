from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from bot.db import PeaceDatabase
from bot.cfg import is_valid_central_bridge_key, parse_central_bridge_url
from bot.main import PeaceBot, CENTRAL_AUTH_DENIAL, role_member


CENTRAL_ACCESS_ROLE_ID = 9001


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
        client_id="client-test-1",
        code="123456",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    )
    with database.connect() as connection:
        stored = connection.execute("SELECT * FROM central_login_challenges").fetchone()
    assert "123456" not in stored["code_hash"]
    assert "123456" not in stored["code_salt"]

    assert not database.consume_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        code="000000",
    )
    assert database.consume_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        code="123456",
    )
    assert not database.consume_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        code="123456",
    )


def test_login_code_is_expired_and_attempt_limited(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    database.create_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        code="123456",
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    )
    assert not database.consume_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        code="123456",
    )

    database.create_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        code="654321",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    )
    for _ in range(5):
        assert not database.consume_central_login_challenge(
            discord_user_id=10,
            peace_id=42,
            client_id="client-test-1",
            code="000000",
        )
    assert not database.consume_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        code="654321",
    )


def test_request_throttling_is_per_user_and_per_client(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    for index in range(3):
        database.create_central_login_challenge(
            discord_user_id=10,
            peace_id=42,
            client_id="client-test-1",
            code=f"{index:06d}",
            expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
        )
    assert not database.central_login_request_allowed(
        discord_user_id=10,
        client_id="client-test-1",
    )
    assert database.central_login_request_allowed(
        discord_user_id=11,
        client_id="client-test-2",
    )


def test_session_is_scoped_and_revocable(tmp_path):
    database = PeaceDatabase(tmp_path / "peace.sqlite3")
    token = database.create_central_login_session(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        project_id="00000000-0000-4000-8000-000000000001",
        scope="central:access central:sync",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
    )
    session = database.validate_central_login_session(
        token=token,
        client_id="client-test-1",
        project_id="00000000-0000-4000-8000-000000000001",
    )
    assert session is not None
    assert database.validate_central_login_session(
        token=token,
        client_id="client-test-1",
        project_id="00000000-0000-4000-8000-000000000002",
    ) is None
    assert database.revoke_central_login_session(token=token, client_id="client-test-1")
    assert database.validate_central_login_session(token=token, client_id="client-test-1") is None

    expired = database.create_central_login_session(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        project_id=None,
        scope="central:access",
        expires_at=(datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
    )
    assert database.validate_central_login_session(token=expired, client_id="client-test-1") is None


def test_bridge_configuration_rejects_remote_urls_and_placeholders():
    assert is_valid_central_bridge_key("a" * 32)
    assert not is_valid_central_bridge_key("generate-a-local-secret")
    assert parse_central_bridge_url("http://127.0.0.1:8765/")[0] == "127.0.0.1"
    try:
        parse_central_bridge_url("https://example.com:8765/")
    except RuntimeError:
        pass
    else:
        raise AssertionError("remote bridge URL should be rejected")


def test_central_auth_helpers_use_opaque_client_and_project_formats():
    assert PeaceBot.central_client_id("client-test-1") == "client-test-1"
    assert PeaceBot.central_client_id("short") is None
    assert PeaceBot.central_project_id("00000000-0000-4000-8000-000000000001") is not None
    assert PeaceBot.central_project_id("not-a-project") is None
    assert '"ok": false' in PeaceBot.central_denied().text
    assert '"message"' in PeaceBot.central_denied().text


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
