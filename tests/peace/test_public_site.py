import asyncio
import http.client
import threading
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

from aiohttp import web
from aiohttp.test_utils import TestClient, TestServer

from bot.main import PeaceBot


def make_bot(tmp_path):
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        discord_invite_url="https://discord.gg/example",
        guild_id=1,
        peace_role_id=100,
        visitor_role_id=200,
        not_verified_role_id=300,
        verification_channel_id=500,
    )
    return PeaceBot(settings)


def run_public_api(tmp_path, request_path, *, method="GET", headers=None):
    async def scenario():
        bot = make_bot(tmp_path)
        app = bot.public_api_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            response = await client.request(
                method,
                request_path,
                headers=headers,
                allow_redirects=False,
            )
            return response.status, response.headers, await response.text()
        finally:
            await client.close()

    return asyncio.run(scenario())


def run_configured_api(bot, request_path, *, method="GET", payload=None):
    async def scenario():
        app = bot.public_api_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            response = await client.request(method, request_path, json=payload)
            return response.status, await response.json()
        finally:
            await client.close()

    return asyncio.run(scenario())


def test_acl_does_not_serve_the_netlify_frontend(tmp_path):
    for path in ("/", "/discord", "/styles.css", "/script.js", "/assets/peace-bird.png"):
        status, _, _ = run_public_api(tmp_path, path)

        assert status == 404


def test_backend_health_is_machine_readable(tmp_path):
    status, headers, body = run_public_api(tmp_path, "/healthz")

    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    assert headers["Cache-Control"] == "no-store"
    assert body == '{"ok": true, "service": "peace-backend"}'


def test_public_api_status_is_bounded_and_tracks_discord_readiness(tmp_path):
    status, headers, body = run_public_api(
        tmp_path,
        "/api/status",
        headers={"Origin": "https://peacegg.com.br"},
    )

    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    assert headers["Cache-Control"] == "no-store"
    assert headers["Access-Control-Allow-Origin"] == "https://peacegg.com.br"
    assert headers["Vary"] == "Origin"
    assert body == (
        '{"service": "peace-backend", "status": "starting", '
        '"frontend": "netlify", "discord": {"connected": false}}'
    )


def test_public_api_rejects_untrusted_origins_without_reflection(tmp_path):
    status, headers, _ = run_public_api(
        tmp_path,
        "/api/status",
        headers={"Origin": "https://evil.peacegg.com.br"},
    )

    assert status == 200
    assert "Access-Control-Allow-Origin" not in headers
    assert "Vary" not in headers


def test_public_api_supports_only_status_preflight(tmp_path):
    status, headers, body = run_public_api(
        tmp_path,
        "/api/status",
        method="OPTIONS",
        headers={"Origin": "https://www.peacegg.com.br"},
    )

    assert status == 204
    assert body == ""
    assert headers["Access-Control-Allow-Origin"] == "https://www.peacegg.com.br"
    assert headers["Access-Control-Allow-Methods"] == "GET, POST, OPTIONS"


def test_public_api_does_not_expose_central_bridge_routes(tmp_path):
    status, _, _ = run_public_api(tmp_path, "/v1/central/auth/request")

    assert status == 404


def test_public_entry_invite_is_single_use_and_reused_until_expiry(tmp_path):
    bot = make_bot(tmp_path)
    channel = SimpleNamespace(name="verify")
    channel.create_invite = AsyncMock(
        return_value=SimpleNamespace(
            code="entry-code",
            url="https://discord.gg/entry-code",
            uses=0,
        )
    )
    bot.guild = SimpleNamespace(
        text_channels=[channel],
        roles=[],
        get_channel=lambda channel_id: channel if channel_id == 500 else None,
        get_role=lambda role_id: None,
    )
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    status, first = run_configured_api(bot, "/api/entry/start", method="POST", payload={})
    assert status == 200
    assert first["ok"] is True
    assert first["status"] == "waiting_invite"
    assert first["expires_in"] <= 1800

    status, second = run_configured_api(
        bot,
        "/api/entry/start",
        method="POST",
        payload={"session_token": first["session_token"]},
    )
    assert status == 200
    assert second["session_token"] == first["session_token"]
    assert second["invite_url"] == first["invite_url"]
    channel.create_invite.assert_awaited_once_with(
        max_age=1800,
        max_uses=1,
        unique=True,
        reason="Convite único do fluxo público de entrada Peace",
    )


def test_public_entry_repair_only_restores_linked_not_verified_role(tmp_path):
    from bot.main import EntryInviteSession

    class Role:
        def __init__(self, role_id, name, position):
            self.id = role_id
            self.name = name
            self.position = position
            self.managed = False

        def is_default(self):
            return False

        def __lt__(self, other):
            return self.position < other.position

    class Member:
        def __init__(self, guild):
            self.id = 12345678901234567
            self.name = "peaceiro"
            self.display_name = "peaceiro"
            self.roles = []
            self.guild = guild

        async def add_roles(self, role, reason=None):
            self.roles.append(role)

    not_verified = Role(300, "Not Verified", 3)
    guild = SimpleNamespace(
        text_channels=[],
        roles=[not_verified],
        me=SimpleNamespace(top_role=Role(999, "PeaceBot", 10)),
        get_role=lambda role_id: not_verified if role_id == 300 else None,
    )
    member = Member(guild)
    guild.get_member = lambda member_id: member if member_id == member.id else None
    bot = make_bot(tmp_path)
    bot.guild = guild
    token = "A" * 43
    bot.entry_sessions[token] = EntryInviteSession(
        session_token=token,
        invite_code="entry-code",
        invite_url="https://discord.gg/entry-code",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        discord_user_id=member.id,
        discord_username=member.name,
        status="verification_pending",
    )

    status, payload = run_configured_api(
        bot,
        "/api/entry/repair",
        method="POST",
        payload={"session_token": token, "discord_username": member.name},
    )
    assert status == 200
    assert payload["code"] == "ROLE_REPAIRED"
    assert not_verified in member.roles


def test_public_site_files_are_complete():
    from pathlib import Path

    site_root = Path(__file__).parents[2] / "bot" / "site"
    member_root = site_root / "area"

    assert (site_root / "index.html").is_file()
    assert (site_root / "styles.css").is_file()
    assert (site_root / "script.js").is_file()
    assert (site_root / "assets" / "peace-bird.png").is_file()
    assert (site_root / "assets" / "discord.svg").is_file()
    assert (site_root / "assets" / "id-card.svg").is_file()
    assert (site_root / "assets" / "shield-check.svg").is_file()
    assert (member_root / "index.html").is_file()
    for route in ("entrar", "candidatura", "acessar", "avisos", "parceiros"):
        assert (site_root / route / "index.html").is_file()
    assert "/api/status" in (site_root / "script.js").read_text(encoding="utf-8")
    assert "/api/auth/code/request" not in (site_root / "script.js").read_text(encoding="utf-8")
    assert "/api/auth/code/verify" not in (site_root / "script.js").read_text(encoding="utf-8")
    assert "data-service-status" in (site_root / "index.html").read_text(encoding="utf-8")
    script = (site_root / "script.js").read_text(encoding="utf-8")
    stylesheet = (site_root / "styles.css").read_text(encoding="utf-8")
    homepage = (site_root / "index.html").read_text(encoding="utf-8")
    assert "--canvas: #050607" in stylesheet
    assert "O seu espaço." in homepage
    assert 'class="peace-icon"' in homepage
    assert 'id="avisos"' not in homepage
    assert 'id="parceiros"' not in homepage
    header_cta = homepage.split('class="button button--outline header-cta"', 1)[1].split("</a>", 1)[0]
    hero_cta = homepage.split('class="button button--light button--large"', 1)[1].split("</a>", 1)[0]
    assert "peace-icon" in header_cta and "discord-icon" not in header_cta
    assert "peace-icon" in hero_cta and "discord-icon" not in hero_cta

    entry_html = (site_root / "entrar" / "index.html").read_text(encoding="utf-8")
    candidature_html = (site_root / "candidatura" / "index.html").read_text(encoding="utf-8")
    login_html = (site_root / "acessar" / "index.html").read_text(encoding="utf-8")
    assert "Começar minha entrada" in entry_html
    assert "peace-icon" in entry_html
    assert "Conectar no Discord" in candidature_html
    assert "discord-icon" in candidature_html
    assert "data-entry-connect" in candidature_html
    assert "#verify" in candidature_html
    assert "entry-help-panel" in candidature_html
    assert "return-icon" in candidature_html
    assert 'class="login-layout login-layout--focused"' in login_html
    assert "flow-boundary" not in login_html
    assert "auth-note" not in login_html
    assert "Seu ID não é uma senha." not in login_html
    assert 'data-login-status role="status" aria-live="polite" hidden' in login_html
    assert 'maxlength="19"' in login_html
    assert 'inputmode="numeric"' in login_html
    assert 'src="/assets/id-card.svg"' in login_html
    assert ">Continuar</span>" in login_html
    assert "Login indisponível" not in login_html
    assert "Conexão indisponível" not in candidature_html
    assert "Acesso web em preparação" in script
    assert "status unavailable" not in script
    assert "fetch unavailable" not in script
    assert "request timeout" not in script
    assert 'data-button-label' in login_html and 'button-spinner' in login_html
    assert 'data-button-label' in candidature_html and 'button-spinner' in candidature_html
    assert '60000' in script
    assert 'aria-busy' in script
    assert '/api/entry/start' in script
    assert '/api/entry/status' in script
    assert '/api/entry/repair' in script
    assert 'href="/discord/"' not in candidature_html
    assert "abrindo-discord.html" in script
    assert "endpoint unavailable" not in script
    assert (site_root / "candidatura" / "abrindo-discord.html").is_file()
    assert 'data-entry-confirm' not in candidature_html
    assert 'Progresso restaurado neste navegador' not in script
    assert 'Revisão salva neste navegador' not in script
    assert 'Candidatura salva neste navegador' not in script
    assert 'button.disabled = stageNumber > currentStage' in script
    assert '--container-background' in stylesheet
    assert '.application-card' in stylesheet and '.login-card' in stylesheet
    assert 'body[data-page="candidatura"] .flow-header { display: none; }' in stylesheet
    for flow_html in (entry_html, candidature_html, login_html):
        assert "flow-header-context" not in flow_html


def test_member_area_is_gated_and_preview_is_explicitly_synthetic():
    from pathlib import Path

    site_root = Path(__file__).parents[2] / "bot" / "site"
    member_html = (site_root / "area" / "index.html").read_text(encoding="utf-8")
    script = (site_root / "script.js").read_text(encoding="utf-8")

    assert 'data-page="member"' in member_html
    assert "data-member-gate" in member_html
    assert "data-member-preview" in member_html
    assert 'data-preview-screen="investigativa"' in member_html
    assert "member-header" in member_html
    assert "site-header site-header--area" not in member_html
    assert "registros abaixo são sintéticos" in member_html
    assert 'get("preview") === "member"' in script
    assert "grant" not in script.lower()
    assert "gsap" not in script.lower()


def test_netlify_redirects_keep_the_short_discord_route():
    from pathlib import Path

    redirects = (Path(__file__).parents[2] / "bot" / "site" / "_redirects").read_text(encoding="utf-8")

    assert "/discord https://discord.gg/qUkQH8XmcN 302!" in redirects
    assert "/discord/ https://discord.gg/qUkQH8XmcN 302!" in redirects
    assert "/api/status http://141.11.237.97:25072/api/status 200!" in redirects
    for route in ("/entrar", "/candidatura", "/area", "/acessar", "/avisos", "/parceiros"):
        assert f"{route} {route}/ 301!" not in redirects


def test_local_site_server_handles_static_and_entry_routes():
    from ops.peace_site_server import PeaceSiteHandler

    from http.server import ThreadingHTTPServer

    server = ThreadingHTTPServer(("127.0.0.1", 0), PeaceSiteHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
        for path, expected_status, expected_location in (
            ("/", 200, None),
            ("/discord", 302, "https://discord.gg/qUkQH8XmcN"),
            ("/entrar", 301, "/entrar/"),
            ("/candidatura", 301, "/candidatura/"),
            ("/acessar", 301, "/acessar/"),
            ("/avisos", 301, "/avisos/"),
            ("/parceiros", 301, "/parceiros/"),
            ("/entrar/", 200, None),
            ("/candidatura/", 200, None),
            ("/acessar/", 200, None),
            ("/avisos/", 200, None),
            ("/parceiros/", 200, None),
        ):
            connection.request("GET", path)
            response = connection.getresponse()
            response.read()
            assert response.status == expected_status
            if expected_location:
                assert response.getheader("Location") == expected_location
        connection.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
