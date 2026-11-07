import asyncio
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from bot.persistence.database import PeaceDatabase
from bot.config.settings import (
    _central_bridge_key_env,
    is_valid_central_bridge_key,
    parse_central_bridge_url,
)
from bot.main import CENTRAL_AUTH_DENIAL, CENTRAL_AUTH_THROTTLED, PeaceBot, role_member


CENTRAL_ACCESS_ROLE_ID = 9001


def member(*role_ids: int):
    return SimpleNamespace(
        roles=[SimpleNamespace(id=role_id) for role_id in role_ids],
    )


def make_bot(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        central_bridge_key="a" * 32,
        central_auth_code_ttl_seconds=600,
        central_auth_session_ttl_seconds=1800,
    )
    return PeaceBot(settings)


def run_endpoint(handler, *, payload, headers=None):
    async def scenario():
        app = web.Application()
        app.router.add_post("/", handler)
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            response = await client.post(
                "/",
                json=payload,
                headers=headers or {"X-Central-Bridge-Key": "a" * 32},
            )
            return response.status, await response.json()
        finally:
            await client.close()

    return asyncio.run(scenario())


def test_only_central_access_role_can_request_a_login_code():
    allowed = member(CENTRAL_ACCESS_ROLE_ID)
    missing_role = member(1467349800956592188)
    no_roles = member()

    assert role_member(allowed, CENTRAL_ACCESS_ROLE_ID)
    assert not role_member(missing_role, CENTRAL_ACCESS_ROLE_ID)
    assert not role_member(no_roles, CENTRAL_ACCESS_ROLE_ID)


def test_central_endpoints_require_the_bridge_key_and_hide_identity_state(tmp_path):
    bot = make_bot(tmp_path)
    bot.central_auth_member = AsyncMock(return_value=None)
    payload = {"peace_id": 42, "client_id": "client-test-1"}

    unauthorized_status, unauthorized = run_endpoint(
        bot.central_auth_request,
        payload=payload,
        headers={"X-Central-Bridge-Key": "wrong"},
    )
    unknown_status, unknown = run_endpoint(bot.central_auth_request, payload=payload)
    mismatched_status, mismatched = run_endpoint(
        bot.central_auth_request,
        payload={"peace_id": 43, "client_id": "client-test-1"},
    )

    assert unauthorized_status == 401
    assert unknown_status == mismatched_status == 403
    assert unknown == mismatched == {"ok": False, "message": CENTRAL_AUTH_DENIAL}
    assert unauthorized["ok"] is False


def test_central_request_endpoint_throttles_and_does_not_log_codes(tmp_path, caplog):
    bot = make_bot(tmp_path)
    requester = SimpleNamespace(id=10, send=AsyncMock())
    bot.central_auth_member = AsyncMock(return_value=requester)
    payload = {"peace_id": 42, "client_id": "client-test-1"}

    responses = [run_endpoint(bot.central_auth_request, payload=payload) for _ in range(4)]

    assert [status for status, _ in responses[:3]] == [200, 200, 200]
    assert responses[3] == (429, {"ok": False, "message": CENTRAL_AUTH_THROTTLED})
    assert requester.send.await_count == 3
    for call in requester.send.call_args_list:
        message = call.args[0]
        code = re.search(r"Código: `(?P<code>\d{6})`", message).group("code")
        assert code not in caplog.text


def test_central_endpoints_issue_validate_revoke_and_recheck_role(tmp_path):
    bot = make_bot(tmp_path)
    requester = SimpleNamespace(id=10)
    bot.central_auth_member = AsyncMock(return_value=requester)
    project_id = "00000000-0000-4000-8000-000000000001"
    bot.database.create_central_login_challenge(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        code="123456",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat(),
    )

    async def scenario():
        app = web.Application()
        app.router.add_post("/verify", bot.central_auth_verify)
        app.router.add_post("/session", bot.central_auth_session)
        app.router.add_post("/revoke", bot.central_auth_revoke)
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        headers = {"X-Central-Bridge-Key": "a" * 32}
        try:
            verified = await client.post(
                "/verify",
                json={"peace_id": 42, "code": "123456", "client_id": "client-test-1", "project_id": project_id},
                headers=headers,
            )
            verified_body = await verified.json()
            token = verified_body["session"]["token"]
            session_headers = {**headers, "Authorization": f"Bearer {token}"}
            valid = await client.post(
                "/session",
                json={"client_id": "client-test-1", "project_id": project_id},
                headers=session_headers,
            )
            valid_body = await valid.json()
            revoked = await client.post(
                "/revoke",
                json={"client_id": "client-test-1"},
                headers=session_headers,
            )
            revoked_body = await revoked.json()
            after_revoke = await client.post(
                "/session",
                json={"client_id": "client-test-1", "project_id": project_id},
                headers=session_headers,
            )
            after_revoke_body = await after_revoke.json()
            return (
                verified.status,
                verified_body,
                valid.status,
                valid_body,
                revoked.status,
                revoked_body,
                after_revoke.status,
                after_revoke_body,
            )
        finally:
            await client.close()

    result = asyncio.run(scenario())
    assert result[0] == result[2] == 200
    assert result[1]["session"]["scope"] == ["central:access", "central:sync"]
    assert result[3]["session"]["project_id"] == project_id
    assert result[4:6] == (200, {"ok": True, "message": "Sessão encerrada."})
    assert result[6] == 403
    assert result[7] == {"ok": False, "message": CENTRAL_AUTH_DENIAL}

    role_revoked_token = bot.database.create_central_login_session(
        discord_user_id=10,
        peace_id=42,
        client_id="client-test-1",
        project_id=None,
        scope="central:access",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
    )
    bot.central_auth_member = AsyncMock(return_value=None)
    status, body = run_endpoint(
        bot.central_auth_session,
        payload={"client_id": "client-test-1"},
        headers={
            "X-Central-Bridge-Key": "a" * 32,
            "Authorization": f"Bearer {role_revoked_token}",
        },
    )
    assert status == 403
    assert body == {"ok": False, "message": CENTRAL_AUTH_DENIAL}


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


def test_missing_central_bridge_key_disables_the_optional_bridge(monkeypatch):
    monkeypatch.delenv("CENTRAL_BRIDGE_KEY", raising=False)

    assert _central_bridge_key_env() == ""


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
