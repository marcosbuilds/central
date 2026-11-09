import asyncio
from types import SimpleNamespace

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
    )
    return PeaceBot(settings)


def run_public_site(tmp_path, request_path):
    async def scenario():
        bot = make_bot(tmp_path)
        app = web.Application()
        app.router.add_get("/", bot.public_site_index)
        app.router.add_get("/discord", bot.public_site_redirect)
        app.router.add_get("/healthz", bot.public_site_health)
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            response = await client.get(request_path, allow_redirects=False)
            return response.status, response.headers, await response.text()
        finally:
            await client.close()

    return asyncio.run(scenario())


def test_home_serves_the_public_site_and_logo(tmp_path):
    status, headers, body = run_public_site(tmp_path, "/")

    assert status == 200
    assert headers["Content-Type"].startswith("text/html")
    assert "Um lugar para" in body
    assert "/assets/peace-bird.png" in body


def test_discord_short_link_redirects_without_caching(tmp_path):
    status, headers, _ = run_public_site(tmp_path, "/discord")

    assert status == 302
    assert headers["Location"] == "https://discord.gg/example"
    assert headers["Cache-Control"] == "no-store"


def test_public_site_health_is_machine_readable(tmp_path):
    status, headers, body = run_public_site(tmp_path, "/healthz")

    assert status == 200
    assert headers["Content-Type"].startswith("application/json")
    assert body == '{"ok": true, "service": "peace-site"}'


def test_public_site_files_are_complete():
    from pathlib import Path

    site_root = Path(__file__).parents[2] / "bot" / "site"

    assert (site_root / "index.html").is_file()
    assert (site_root / "styles.css").is_file()
    assert (site_root / "script.js").is_file()
    assert (site_root / "assets" / "peace-bird.png").is_file()
