import asyncio
import http.client
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from types import SimpleNamespace
from urllib.error import HTTPError
from urllib.request import Request
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
        staff_role_id=501,
        manager_role_id=502,
        central_access_role_id=503,
        investigator_role_id=101,
        lead_investigator_role_id=102,
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


def run_configured_api(bot, request_path, *, method="GET", payload=None, headers=None, cookies=None):
    async def scenario():
        app = bot.public_api_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            response = await client.request(method, request_path, json=payload, headers=headers, cookies=cookies)
            return response.status, await response.json()
        finally:
            await client.close()

    return asyncio.run(scenario())


def run_configured_api_with_headers(bot, request_path, *, method="GET", payload=None, headers=None, cookies=None):
    async def scenario():
        app = bot.public_api_app()
        server = TestServer(app)
        client = TestClient(server)
        await client.start_server()
        try:
            response = await client.request(method, request_path, json=payload, headers=headers, cookies=cookies)
            return response.status, response.headers, await response.json()
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


def test_public_api_rate_limit_has_retry_contract(tmp_path):
    bot = make_bot(tmp_path)
    request = SimpleNamespace(path="/api/entry/start", remote="198.51.100.20")

    for _ in range(12):
        assert bot.public_api_rate_limit(request) is None

    response = bot.public_api_rate_limit(request)

    assert response is not None
    assert response.status == 429
    assert int(response.headers["Retry-After"]) > 0


def test_public_media_feed_reports_unavailable_sources_without_faking_empty_data(tmp_path):
    bot = make_bot(tmp_path)

    status, payload = run_configured_api(bot, "/api/media?seed=7", method="GET")

    assert status == 200
    assert payload["moments"] == []
    assert payload["clips"] == []
    assert payload["sources"]["moments"]["state"] == "unavailable"
    assert payload["sources"]["moments"]["stale"] is True
    assert payload["sources"]["clips"]["state"] == "unavailable"


def test_public_media_feed_reads_discord_attachments_and_keeps_external_urls_out(tmp_path):
    created_at = datetime.now(timezone.utc)
    messages = []
    for index in range(8):
        messages.append(
            SimpleNamespace(
                id=100 + index,
                created_at=created_at - timedelta(days=index),
                content=f"Momento {index}",
                jump_url=f"https://discord.com/channels/1/2/{100 + index}",
                reactions=[SimpleNamespace(count=index)],
                attachments=[
                    SimpleNamespace(
                        url=f"https://cdn.discordapp.com/attachments/1/2/{index}.png",
                        content_type="image/png",
                        size=1024,
                    ),
                    SimpleNamespace(
                        url="https://example.com/private.png",
                        content_type="image/png",
                        size=1024,
                    ),
                ],
            )
        )

    async def history(limit):
        for message in messages:
            yield message

    channel = SimpleNamespace(history=history)
    bot = make_bot(tmp_path)
    bot.settings.website_media_channel_id = 1459444827635712134
    bot.settings.website_clips_channel_id = None
    bot.guild = SimpleNamespace(get_channel=lambda channel_id: channel if channel_id == bot.settings.website_media_channel_id else None)
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    status, payload = run_configured_api(bot, "/api/media?seed=7", method="GET")

    assert status == 200
    assert payload["ok"] is True
    assert payload["moments"]
    assert len(payload["moments"]) <= 12
    assert all(item["url"].startswith("https://cdn.discordapp.com/") for item in payload["moments"])
    assert any(item["engagement"] > 0 for item in payload["moments"])
    assert payload["clips"] == []


def test_public_media_feed_extracts_clip_links_message_text_and_public_author(tmp_path):
    message = SimpleNamespace(
        id=909,
        created_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
        content="A curva ficou limpa https://medal.tv/games/gta-v/clips/no9WMOwfZ4Q-LXEC4?invite=public",
        jump_url="https://discord.com/channels/1/2/909",
        reactions=[SimpleNamespace(count=4)],
        attachments=[],
        author=SimpleNamespace(
            display_name="Marcos Peace",
            name="marcos",
            display_avatar=SimpleNamespace(url="https://cdn.discordapp.com/avatars/1/avatar.png"),
        ),
        embeds=[
            SimpleNamespace(
                title="GTA V Trimmed Clip",
                description="Preview from the clip provider",
                provider=SimpleNamespace(name="Medal"),
                author=SimpleNamespace(name="clip-author"),
            )
        ],
    )

    items = PeaceBot.public_media_items_from_message(message, "clips")

    assert len(items) == 1
    clip = items[0]
    assert clip["provider"] == "Medal"
    assert clip["type"] == "video"
    assert clip["kind"] == "link"
    assert clip["canonical_id"] == "no9WMOwfZ4Q-LXEC4"
    assert clip["embed_url"] == ""
    assert clip["caption"] == "A curva ficou limpa"
    assert clip["message_text"] == "A curva ficou limpa"
    assert clip["provider_title"] == "GTA V Trimmed Clip"
    assert clip["provider_description"] == "Preview from the clip provider"
    assert clip["author"]["display_name"] == "Marcos Peace"
    assert clip["author"]["avatar_url"].startswith("https://cdn.discordapp.com/")


def test_public_media_feed_keeps_link_only_messages_and_direct_video_attachments(tmp_path):
    link_only = SimpleNamespace(
        id=912,
        created_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
        content="https://medal.tv/games/gta-v/clips/clip-only?invite=public",
        jump_url="https://discord.com/channels/1/2/912",
        reactions=[],
        attachments=[],
        author=SimpleNamespace(
            display_name="Example Nick",
            name="example-user",
            display_avatar=SimpleNamespace(url="https://cdn.discordapp.com/avatars/2/avatar.png"),
        ),
        embeds=[
            SimpleNamespace(
                title="Untitled - Clipped GTA V with Medal.tv",
                description="",
                provider=SimpleNamespace(name="Medal"),
                author=SimpleNamespace(name="clip-author"),
            )
        ],
    )
    direct_video = SimpleNamespace(
        id=913,
        created_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
        content="",
        jump_url="https://discord.com/channels/1/2/913",
        reactions=[],
        attachments=[
            SimpleNamespace(
                url="https://cdn.discordapp.com/attachments/1/2/clip.mov",
                content_type="video/quicktime",
                size=1024,
            )
        ],
        author=None,
        embeds=[],
    )

    link_items = PeaceBot.public_media_items_from_message(link_only, "clips")
    direct_items = PeaceBot.public_media_items_from_message(direct_video, "clips")

    assert len(link_items) == 1
    assert link_items[0]["caption"] == ""
    assert link_items[0]["message_text"] == ""
    assert link_items[0]["provider_title"] == "Untitled - Clipped GTA V with Medal.tv"
    assert link_items[0]["provider_author"] == "clip-author"
    assert link_items[0]["author"]["display_name"] == "Example Nick"
    assert len(direct_items) == 1
    assert direct_items[0]["kind"] == "direct"
    assert direct_items[0]["type"] == "video"
    assert direct_items[0]["url"].endswith("clip.mov")


def test_public_media_feed_resolves_signed_medal_media_for_the_matching_clip():
    canonical_id = "kyMSdFd6TYMR2WrkJ"
    video_url = (
        "https://cdn.medal.tv/mediac/kyMSdFd6TYMR2WrkJ.mp4?auth=synthetic"
    )
    thumbnail_url = (
        "https://cdn.medal.tv/ugcc/content-thumbnail/kyMSdFd6TYMR2WrkJ.jpg?auth=synthetic"
    )

    assets = PeaceBot.public_media_medal_assets_from_html(
        f'<video src="{video_url}"></video><meta content="{thumbnail_url}">',
        canonical_id,
    )

    assert assets["media_url"] == video_url
    assert assets["thumbnail_url"] == thumbnail_url


def test_public_media_feed_promotes_active_medal_item_to_direct_video():
    video_url = (
        "https://cdn.medal.tv/mediac/active-clip.mp4?auth=synthetic"
    )
    thumbnail_url = (
        "https://cdn.medal.tv/ugcc/content-thumbnail/active-clip.jpg?auth=synthetic"
    )

    class FakeResponse:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def text(self, *, errors="ignore"):
            del errors
            return f'<video src="{video_url}"></video><meta content="{thumbnail_url}">'

    class FakeSession:
        def get(self, *_args, **_kwargs):
            return FakeResponse()

    item = {
        "provider": "Medal",
        "type": "video",
        "kind": "link",
        "canonical_id": "active-clip",
        "url": "https://medal.tv/games/gta-v/clips/active-clip",
        "source_url": "https://medal.tv/games/gta-v/clips/active-clip",
        "thumbnail_url": "",
    }

    resolved = asyncio.run(PeaceBot.public_media_resolve_medal_item(item, FakeSession()))

    assert resolved["kind"] == "direct"
    assert resolved["type"] == "video"
    assert resolved["url"] == video_url
    assert resolved["media_url"] == video_url
    assert resolved["thumbnail_url"] == thumbnail_url


def test_public_media_feed_reads_all_chunks_of_medal_html_before_extracting_media():
    video_url = "https://cdn.medal.tv/mediac/chunked-clip.mp4?auth=synthetic"
    thumbnail_url = "https://cdn.medal.tv/ugcc/content-thumbnail/chunked-clip.jpg?auth=synthetic"
    markup = f'<html><head><meta content="{thumbnail_url}"></head><body><video src="{video_url}"></video></body></html>'.encode()

    class ChunkedContent:
        def __init__(self, chunks):
            self.chunks = list(chunks)

        async def read(self, _size=-1):
            return self.chunks.pop(0) if self.chunks else b""

    class ChunkedResponse:
        status = 200
        headers = {"Content-Type": "text/html; charset=utf-8"}

        def __init__(self):
            split = len(markup) // 2
            self.content = ChunkedContent((markup[:split], markup[split:]))

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    class ChunkedSession:
        def get(self, *_args, **_kwargs):
            return ChunkedResponse()

    item = {
        "provider": "Medal",
        "type": "video",
        "kind": "link",
        "canonical_id": "chunked-clip",
        "source_url": "https://medal.tv/games/gta-v/clips/chunked-clip",
        "url": "https://medal.tv/games/gta-v/clips/chunked-clip",
        "thumbnail_url": "",
    }

    resolved = asyncio.run(PeaceBot.public_media_resolve_medal_item(item, ChunkedSession()))

    assert resolved["kind"] == "direct"
    assert resolved["url"] == video_url
    assert resolved["thumbnail_url"] == thumbnail_url


def test_public_media_feed_accepts_provider_video_already_supplied_by_discord():
    video_url = "https://cdn.medal.tv/mediac/clip.mp4?auth=public"
    message = SimpleNamespace(
        id=914,
        created_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
        content="https://medal.tv/games/gta-v/clips/embed-ready",
        jump_url="https://discord.com/channels/1/2/914",
        reactions=[],
        attachments=[],
        author=None,
        embeds=[
            SimpleNamespace(
                title="Medal clip",
                description="",
                provider=SimpleNamespace(name="Medal"),
                author=None,
                thumbnail=None,
                image=None,
                video=SimpleNamespace(url=video_url, proxy_url=""),
            )
        ],
    )

    items = PeaceBot.public_media_items_from_message(message, "clips")

    assert len(items) == 1
    assert items[0]["kind"] == "direct"
    assert items[0]["url"] == video_url


def test_public_media_feed_extracts_medal_link_from_embed_without_message_text():
    video_url = "https://cdn.medal.tv/mediac/embed-only.mp4?auth=synthetic"
    message = SimpleNamespace(
        id=915,
        created_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
        content="",
        jump_url="https://discord.com/channels/1/2/915",
        reactions=[],
        attachments=[],
        author=None,
        embeds=[
            SimpleNamespace(
                url="https://medal.tv/games/gta-v/clips/embed-only",
                title="Embed-only Medal clip",
                description="",
                provider=SimpleNamespace(name="Medal"),
                author=None,
                thumbnail=None,
                image=None,
                video=SimpleNamespace(url=video_url, proxy_url=""),
            )
        ],
    )

    items = PeaceBot.public_media_items_from_message(message, "clips")

    assert len(items) == 1
    assert items[0]["provider"] == "Medal"
    assert items[0]["kind"] == "direct"
    assert items[0]["url"] == video_url
    assert items[0]["source_url"] == "https://medal.tv/games/gta-v/clips/embed-only"


def test_public_media_medal_resolver_rejects_external_redirects():
    class RedirectResponse:
        status = 302
        headers = {"Location": "https://example.invalid/redirected"}

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

    class RedirectSession:
        def __init__(self):
            self.calls = []

        def get(self, url, **kwargs):
            self.calls.append((url, kwargs))
            return RedirectResponse()

    item = {
        "provider": "Medal",
        "type": "video",
        "kind": "link",
        "canonical_id": "redirected-clip",
        "source_url": "https://medal.tv/games/gta-v/clips/redirected-clip",
        "url": "https://medal.tv/games/gta-v/clips/redirected-clip",
    }
    session = RedirectSession()

    resolved = asyncio.run(PeaceBot.public_media_resolve_medal_item(item, session))

    assert resolved == item
    assert len(session.calls) == 1
    assert session.calls[0][1]["allow_redirects"] is False


def test_public_media_feed_supports_tiktok_players_and_short_link_fallbacks(tmp_path):
    message = SimpleNamespace(
        id=910,
        created_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
        content=(
            "Olha esse corte https://www.tiktok.com/@peace/video/7692212006451006740 "
            "https://vt.tiktok.com/ZSgQSLA9e/"
        ),
        jump_url="https://discord.com/channels/1/2/910",
        reactions=[],
        attachments=[],
        author=None,
        embeds=[],
    )

    items = PeaceBot.public_media_items_from_message(message, "clips")

    assert len(items) == 2
    full = items[0]
    short = items[1]
    assert full["provider"] == "TikTok"
    assert full["kind"] == "embed"
    assert full["canonical_id"] == "7692212006451006740"
    assert full["embed_url"] == (
        "https://www.tiktok.com/player/v1/7692212006451006740"
        "?controls=1&description=1&music_info=1"
    )
    assert short["provider"] == "TikTok"
    assert short["kind"] == "link"
    assert short["embed_url"] == ""
    assert short["fallback_url"] == "https://vt.tiktok.com/ZSgQSLA9e/"


def test_public_media_feed_deduplicates_equivalent_links_inside_one_message(tmp_path):
    message = SimpleNamespace(
        id=911,
        created_at=datetime(2026, 11, 11, tzinfo=timezone.utc),
        content=(
            "Mesmo clip https://medal.tv/games/gta-v/clips/abc123?invite=one "
            "e https://medal.tv/games/gta-v/clips/abc123?invite=two"
        ),
        jump_url="https://discord.com/channels/1/2/911",
        reactions=[],
        attachments=[],
        author=None,
        embeds=[],
    )

    items = PeaceBot.public_media_items_from_message(message, "clips")

    assert len(items) == 1
    assert items[0]["canonical_id"] == "abc123"


def test_public_media_selection_deduplicates_the_same_clip_across_messages():
    items = [
        {
            "id": "new-message:link:0",
            "provider": "Medal",
            "canonical_id": "same-clip",
            "source_url": "https://medal.tv/games/gta-v/clips/same-clip?invite=new",
            "created_at_unix": 20,
            "engagement": 2,
        },
        {
            "id": "old-message:link:0",
            "provider": "Medal",
            "canonical_id": "same-clip",
            "source_url": "https://medal.tv/games/gta-v/clips/same-clip?invite=old",
            "created_at_unix": 10,
            "engagement": 9,
        },
        {
            "id": "other-message:link:0",
            "provider": "Medal",
            "canonical_id": "other-clip",
            "source_url": "https://medal.tv/games/gta-v/clips/other-clip",
            "created_at_unix": 5,
            "engagement": 1,
        },
    ]

    selected = PeaceBot.select_public_media(items, "clips", seed=7)

    assert [item["id"] for item in selected].count("new-message:link:0") == 1
    assert "old-message:link:0" not in [item["id"] for item in selected]
    assert "other-message:link:0" in [item["id"] for item in selected]


def test_public_api_rejects_untrusted_origins_without_reflection(tmp_path):
    status, headers, _ = run_public_api(
        tmp_path,
        "/api/status",
        headers={"Origin": "https://evil.peacegg.com.br"},
    )

    assert status == 403
    assert "Access-Control-Allow-Origin" not in headers
    assert headers["Cache-Control"] == "no-store"


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


def test_authentication_responses_are_private_and_uncacheable(tmp_path):
    routes = (
        ("/api/member/auth/request", {"peace_id": "invalid"}),
        ("/api/member/auth/verify", {"peace_id": "invalid", "code": "invalid"}),
        ("/api/member/auth/session", {}),
        ("/api/member/auth/revoke", {}),
    )

    for route, payload in routes:
        bot = make_bot(tmp_path)
        status, headers, _ = run_configured_api_with_headers(
            bot,
            route,
            method="POST",
            payload=payload,
        )

        assert status in {400, 401}
        assert headers["Cache-Control"] == "no-store, private"
        assert headers["Pragma"] == "no-cache"
        assert {value.strip() for value in headers["Vary"].split(",")} >= {"Authorization", "Cookie"}


def test_public_api_does_not_expose_central_bridge_routes(tmp_path):
    status, _, _ = run_public_api(tmp_path, "/v1/central/auth/request")

    assert status == 404


def test_public_entry_invite_is_effectively_single_use_and_reused_until_expiry(tmp_path):
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
        max_uses=2,
        unique=True,
        reason="Convite único do fluxo público de entrada Peace",
    )


def test_public_entry_binds_join_from_the_verification_channel_invite_list(tmp_path):
    from bot.main import EntryInviteSession

    not_verified = SimpleNamespace(id=300, name="Not Verified")
    channel = SimpleNamespace(name="verify")
    channel.create_invite = AsyncMock()
    invite = SimpleNamespace(
        code="entry-code",
        url="https://discord.gg/entry-code",
        uses=1,
        delete=AsyncMock(),
    )
    channel.invites = AsyncMock(return_value=[invite])
    guild = SimpleNamespace(
        text_channels=[channel],
        roles=[not_verified],
        get_channel=lambda channel_id: channel if channel_id == 500 else None,
        get_role=lambda role_id: not_verified if role_id == 300 else None,
    )
    member = SimpleNamespace(
        id=12345678901234567,
        name="peaceiro",
        display_name="peaceiro",
        roles=[not_verified],
        guild=guild,
    )
    bot = make_bot(tmp_path)
    bot.guild = guild
    token = "B" * 43
    session = EntryInviteSession(
        session_token=token,
        invite_code="entry-code",
        invite_url="https://discord.gg/entry-code",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        initial_uses=0,
    )
    bot.entry_sessions[token] = session

    asyncio.run(bot.bind_entry_invite(member))

    assert session.discord_user_id == member.id
    assert session.discord_username == member.display_name
    assert session.status == "verification_pending"
    channel.invites.assert_awaited_once_with()
    invite.delete.assert_awaited_once_with(reason="Convite individual do fluxo público de entrada já utilizado")


def test_public_entry_invite_lookup_falls_back_to_fetch_when_list_is_empty(tmp_path):
    invite = SimpleNamespace(code="entry-code", url="https://discord.gg/entry-code", uses=0)
    channel = SimpleNamespace(
        name="verify",
        create_invite=AsyncMock(),
        invites=AsyncMock(return_value=[]),
        fetch_invites=AsyncMock(return_value=[invite]),
    )
    guild = SimpleNamespace(
        text_channels=[channel],
        get_channel=lambda channel_id: channel if channel_id == 500 else None,
    )
    bot = make_bot(tmp_path)
    bot.guild = guild

    found, inspected = asyncio.run(bot.entry_invite_for_code(guild, "entry-code"))

    assert found is invite
    assert inspected is True
    channel.invites.assert_awaited_once_with()
    channel.fetch_invites.assert_awaited_once_with()


def test_public_entry_reports_an_invite_that_disappeared(tmp_path):
    from bot.main import EntryInviteSession

    channel = SimpleNamespace(name="verify", create_invite=AsyncMock(), invites=AsyncMock(return_value=[]))
    guild = SimpleNamespace(
        text_channels=[channel],
        roles=[],
        get_channel=lambda channel_id: channel if channel_id == 500 else None,
        get_role=lambda role_id: None,
        get_member=lambda member_id: None,
    )
    bot = make_bot(tmp_path)
    bot.guild = guild
    token = "C" * 43
    bot.entry_sessions[token] = EntryInviteSession(
        session_token=token,
        invite_code="entry-code",
        invite_url="https://discord.gg/entry-code",
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
        created_at=datetime.now(timezone.utc) - timedelta(seconds=45),
    )

    status, payload = run_configured_api(
        bot,
        "/api/entry/status",
        method="POST",
        payload={"session_token": token},
    )

    assert status == 200
    assert payload["status"] == "invite_unavailable"
    assert payload["invite_url"] == ""


def test_public_member_auth_sends_and_consumes_one_dm_code(tmp_path):
    member = SimpleNamespace(
        id=12345678901234567,
        name="peaceiro",
        display_name="Peaceiro",
        global_name="Peaceiro",
        nick="M ⎰ Peaceiro 42",
        roles=[SimpleNamespace(id=100, name="Peace")],
        bot=False,
        send=AsyncMock(),
    )
    bot = make_bot(tmp_path)
    bot.database.ensure_runtime_member(
        discord_user_id=member.id,
        username=member.name,
        nickname=member.nick,
        role_ids=[100],
        role_names=["Peace"],
        founder_id=999,
    )
    with bot.database.connect() as connection:
        connection.execute("UPDATE members SET peace_id = 42 WHERE discord_user_id = ?", (str(member.id),))
        connection.commit()
    bot.guild = SimpleNamespace(
        members=[member],
        get_member=lambda user_id: member if user_id == member.id else None,
    )
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    status, requested_headers, requested = run_configured_api_with_headers(
        bot,
        "/api/member/auth/request",
        method="POST",
        payload={"peace_id": "42"},
    )
    assert status == 200
    assert requested["ok"] is True
    assert "member_name" not in requested
    message = member.send.await_args.kwargs["embed"]
    code = message.fields[0].value.strip("`")
    assert message.description == f"Bom dia, <@{member.id}>." or message.description == f"Boa tarde, <@{member.id}>." or message.description == f"Boa noite, <@{member.id}>."
    allowed_mentions = member.send.await_args.kwargs["allowed_mentions"]
    assert allowed_mentions.users is True
    assert allowed_mentions.roles is False
    assert code not in requested
    challenge_cookie = next(
        value.split(";", 1)[0]
        for value in requested_headers.getall("Set-Cookie", [])
        if value.startswith("peace_member_challenge=")
    )
    challenge_name, challenge_value = challenge_cookie.split("=", 1)
    assert challenge_name == "peace_member_challenge"
    assert challenge_value

    status, verified_headers, verified = run_configured_api_with_headers(
        bot,
        "/api/member/auth/verify",
        method="POST",
        headers={"Origin": "https://peacegg.com.br"},
        cookies={challenge_name: challenge_value},
        payload={"code": code},
    )
    assert status == 200
    assert verified["ok"] is True
    assert verified["session"]["peace_id"] == 42
    assert verified["session"]["member_name"] == "Peaceiro"
    assert "token" not in verified["session"]
    assert any(value.startswith("peace_member_session=") for value in verified_headers.getall("Set-Cookie", []))

    status, invalid = run_configured_api(
        bot,
        "/api/member/auth/verify",
        method="POST",
        headers={"Origin": "https://peacegg.com.br"},
        cookies={challenge_name: challenge_value},
        payload={"code": code},
    )
    assert status == 401
    assert invalid["code"] == "INVALID_CODE"


def test_public_entry_identifies_existing_visitor_without_granting_access(tmp_path):
    member = SimpleNamespace(
        id=12345678901234567,
        name="peaceiro",
        display_name="Peaceiro",
        global_name="Peaceiro",
        nick=None,
        roles=[SimpleNamespace(id=200, name="Visitor")],
        bot=False,
    )
    bot = make_bot(tmp_path)
    bot.guild = SimpleNamespace(members=[member], get_member=lambda user_id: member if user_id == member.id else None)
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    status, payload = run_configured_api(
        bot,
        "/api/entry/identify",
        method="POST",
        payload={"discord_username": "peaceiro"},
    )
    assert status == 200
    assert payload["status"] == "visitor_member"
    assert payload["next_stage"] == 3
    assert payload["discord_user"]["mention"] == "@Peaceiro"


def test_public_member_auth_rejects_ids_outside_numeric_limit(tmp_path):
    bot = make_bot(tmp_path)
    bot.guild = SimpleNamespace()
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    status, payload = run_configured_api(
        bot,
        "/api/member/auth/request",
        method="POST",
        payload={"peace_id": "1" * 20},
    )
    assert status == 400
    assert payload["code"] == "INVALID_PEACE_ID"


def test_public_member_auth_rejects_ids_that_overflow_sqlite(tmp_path):
    bot = make_bot(tmp_path)
    bot.guild = SimpleNamespace()
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    for value in ("9223372036854775808", "9999999999999999999"):
        status, payload = run_configured_api(
            bot,
            "/api/member/auth/request",
            method="POST",
            payload={"peace_id": value},
        )
        assert status == 400
        assert payload["code"] == "INVALID_PEACE_ID"


def test_public_member_cookie_wins_over_legacy_bearer(tmp_path):
    bot = make_bot(tmp_path)
    cookie = "C" * 43
    bearer = "B" * 43
    request = SimpleNamespace(
        cookies={"peace_member_session": cookie},
        headers={"Authorization": f"Bearer {bearer}"},
    )

    assert bot.public_member_token(request) == cookie


def test_public_member_session_is_revoked_when_a_peace_id_is_reassigned(tmp_path):
    bot = make_bot(tmp_path)
    first_user_id = 111111111111111
    second_user_id = 222222222222222
    bot.database.ensure_runtime_member(
        discord_user_id=first_user_id,
        username="first",
        nickname="First",
        role_ids=[100],
        role_names=["Peace"],
        founder_id=999,
    )
    first = bot.database.get_member(first_user_id)
    assert first is not None
    token = bot.database.create_central_login_session(
        discord_user_id=first_user_id,
        peace_id=int(first["peace_id"]),
        client_id="peacegg-web",
        project_id=None,
        scope="peace:member",
        expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    )
    with bot.database.connect() as connection:
        connection.execute("DELETE FROM member_roles WHERE discord_user_id = ?", (str(first_user_id),))
        connection.execute("DELETE FROM members WHERE discord_user_id = ?", (str(first_user_id),))
        timestamp = datetime.now(timezone.utc).isoformat()
        connection.execute(
            """
            INSERT INTO members (
                discord_user_id, username, global_name, display_name, nickname,
                peace_id, name_prefix, is_founder, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (str(second_user_id), "second", None, "Second", "Second", int(first["peace_id"]), "N", timestamp, timestamp),
        )
        connection.execute(
            "INSERT INTO member_roles (discord_user_id, role_id, role_name) VALUES (?, ?, ?)",
            (str(second_user_id), "100", "Peace"),
        )
        connection.commit()
    member = SimpleNamespace(
        id=second_user_id,
        name="second",
        display_name="Second",
        global_name="Second",
        nick="Second",
        roles=[SimpleNamespace(id=100, name="Peace")],
        bot=False,
    )
    bot.guild = SimpleNamespace(
        get_member=lambda user_id: member if user_id == second_user_id else None,
        fetch_member=AsyncMock(return_value=member),
    )
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    status, payload = run_configured_api(
        bot,
        "/api/member/auth/session",
        method="POST",
        cookies={"peace_member_session": token},
        payload={},
    )

    assert status == 401
    assert payload["code"] == "AUTH_SESSION_INVALID"
    assert bot.database.validate_central_login_session(token=token, client_id="peacegg-web") is None


def test_public_member_logout_revokes_cookie_only_session(tmp_path):
    bot = make_bot(tmp_path)
    token = bot.database.create_central_login_session(
        discord_user_id=123,
        peace_id=42,
        client_id="peacegg-web",
        project_id=None,
        scope="peace:member",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
    )

    status, payload = run_configured_api(
        bot,
        "/api/member/auth/revoke",
        method="POST",
        payload={},
        headers={"Origin": "https://peacegg.com.br"},
        cookies={"peace_member_session": token},
    )

    assert status == 200
    assert payload == {"ok": True, "message": "Sessão encerrada."}
    assert bot.database.validate_central_login_session(token=token, client_id="peacegg-web") is None


def test_public_member_logout_rejects_cookie_without_allowed_origin(tmp_path):
    bot = make_bot(tmp_path)
    token = bot.database.create_central_login_session(
        discord_user_id=123,
        peace_id=42,
        client_id="peacegg-web",
        project_id=None,
        scope="peace:member",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
    )

    status, payload = run_configured_api(
        bot,
        "/api/member/auth/revoke",
        method="POST",
        payload={},
        cookies={"peace_member_session": token},
    )

    assert status == 403
    assert payload["code"] == "ORIGIN_REQUIRED"
    assert bot.database.validate_central_login_session(token=token, client_id="peacegg-web") is not None


def test_public_auth_member_uses_fresh_discord_role_state(tmp_path):
    cached_member = SimpleNamespace(
        id=12345678901234567,
        roles=[SimpleNamespace(id=100, name="Peace")],
        bot=False,
    )
    fetched_member = SimpleNamespace(
        id=cached_member.id,
        roles=[],
        bot=False,
    )
    bot = make_bot(tmp_path)
    bot.database.ensure_runtime_member(
        discord_user_id=cached_member.id,
        username="peaceiro",
        nickname="M ⎰ Peaceiro 42",
        role_ids=[100],
        role_names=["Peace"],
        founder_id=999,
    )
    with bot.database.connect() as connection:
        connection.execute("UPDATE members SET peace_id = 42 WHERE discord_user_id = ?", (str(cached_member.id),))
        connection.commit()

    async def fetch_member(_member_id):
        return fetched_member

    bot.guild = SimpleNamespace(
        get_member=lambda user_id: cached_member if user_id == cached_member.id else None,
        fetch_member=fetch_member,
    )
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    status, payload = run_configured_api(
        bot,
        "/api/member/auth/request",
        method="POST",
        payload={"peace_id": "42"},
    )

    assert status == 403
    assert payload["code"] == "AUTH_DENIED"


def test_investigation_overview_is_site_owned(tmp_path):
    member = SimpleNamespace(
        id=12345678901234567,
        name="investigador",
        display_name="Investigator",
        global_name="Investigator",
        nick="I ⎰ Investigator 42",
        roles=[SimpleNamespace(id=100, name="Peace"), SimpleNamespace(id=101, name="Investigator")],
        bot=False,
    )

    bot = make_bot(tmp_path)
    bot.database.ensure_runtime_member(
        discord_user_id=member.id,
        username=member.name,
        nickname=member.nick,
        role_ids=[100, 101],
        role_names=["Peace", "Investigator"],
        founder_id=999,
    )
    with bot.database.connect() as connection:
        connection.execute("UPDATE members SET peace_id = 42 WHERE discord_user_id = ?", (str(member.id),))
        connection.commit()
    bot.guild = SimpleNamespace(
        members=[member],
        text_channels=[],
        get_member=lambda user_id: member if user_id == member.id else None,
    )
    token = bot.database.create_central_login_session(
        discord_user_id=member.id,
        peace_id=42,
        client_id="peacegg-web",
        project_id=None,
        scope="peace:member",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
    )

    status, payload = run_configured_api(
        bot,
        "/api/member/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert status == 200
    investigation = payload["overview"]["investigation"]
    assert investigation["state"] == "empty"
    assert investigation["source"] == "site:investigations"
    assert investigation["stale"] is False
    assert payload["overview"]["updated_at"]
    assert isinstance(payload["overview"]["stale"], bool)


def test_member_overview_marks_sqlite_presence_as_unavailable(tmp_path):
    member = SimpleNamespace(
        id=12345678901234567,
        name="peaceiro",
        display_name="Peaceiro",
        global_name="Peaceiro",
        nick="M ⎰ Peaceiro 42",
        roles=[SimpleNamespace(id=100, name="Peace")],
        bot=False,
    )
    bot = make_bot(tmp_path)
    bot.database.ensure_runtime_member(
        discord_user_id=member.id,
        username=member.name,
        nickname=member.nick,
        role_ids=[100],
        role_names=["Peace"],
        founder_id=999,
    )
    with bot.database.connect() as connection:
        connection.execute("UPDATE members SET peace_id = 42 WHERE discord_user_id = ?", (str(member.id),))
        connection.commit()
    bot.guild = SimpleNamespace(
        members=[member],
        text_channels=[],
        get_member=lambda user_id: member if user_id == member.id else None,
    )
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False
    bot.database.active_clocks = lambda limit=24: (_ for _ in ()).throw(sqlite3.OperationalError("database is locked"))
    token = bot.database.create_central_login_session(
        discord_user_id=member.id,
        peace_id=42,
        client_id="peacegg-web",
        project_id=None,
        scope="peace:member",
        expires_at=(datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat(),
    )

    status, payload = run_configured_api(
        bot,
        "/api/member/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert status == 200
    assert payload["overview"]["active_members"]["state"] == "unavailable"
    assert payload["overview"]["active_members"]["stale"] is True
    assert payload["overview"]["stale"] is True


def test_public_member_auth_accepts_founder_zero_id(tmp_path):
    member = SimpleNamespace(
        id=12345678901234567,
        name="founder",
        display_name="Founder",
        global_name="Founder",
        nick="F ⎰ Founder 0",
        roles=[SimpleNamespace(id=100, name="Peace")],
        bot=False,
        send=AsyncMock(),
    )
    bot = make_bot(tmp_path)
    bot.database.ensure_runtime_member(
        discord_user_id=member.id,
        username=member.name,
        nickname=member.nick,
        role_ids=[100],
        role_names=["Peace"],
        founder_id=member.id,
    )
    bot.guild = SimpleNamespace(
        members=[member],
        get_member=lambda user_id: member if user_id == member.id else None,
    )
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    for raw_peace_id in (0, "0"):
        status, payload = run_configured_api(
            bot,
            "/api/member/auth/request",
            method="POST",
            payload={"peace_id": raw_peace_id},
        )

        assert status == 200
        assert payload["ok"] is True
        assert "member_name" not in payload


def test_public_member_auth_reports_discord_timeout_as_unavailable(tmp_path):
    member_id = 12345678901234567
    bot = make_bot(tmp_path)
    bot.database.ensure_runtime_member(
        discord_user_id=member_id,
        username="founder",
        nickname="F ⎰ Founder 0",
        role_ids=[100],
        role_names=["Peace"],
        founder_id=member_id,
    )
    bot.guild = SimpleNamespace(
        get_member=lambda user_id: None,
        fetch_member=AsyncMock(side_effect=asyncio.TimeoutError()),
    )
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False

    status, payload = run_configured_api(
        bot,
        "/api/member/auth/request",
        method="POST",
        payload={"peace_id": 0},
    )

    assert status == 503
    assert payload["code"] == "AUTH_UNAVAILABLE"


def test_public_member_session_uses_bounded_cookie_and_overview_is_role_scoped(tmp_path):
    member = SimpleNamespace(
        id=12345678901234567,
        name="peaceiro",
        display_name="Peaceiro",
        global_name="Peaceiro",
        nick="M ⎰ Peaceiro 42",
        roles=[SimpleNamespace(id=100, name="Peace")],
        bot=False,
        send=AsyncMock(),
    )
    bot = make_bot(tmp_path)
    bot.database.ensure_runtime_member(
        discord_user_id=member.id,
        username=member.name,
        nickname=member.nick,
        role_ids=[100],
        role_names=["Peace"],
        founder_id=999,
    )
    with bot.database.connect() as connection:
        connection.execute("UPDATE members SET peace_id = 42 WHERE discord_user_id = ?", (str(member.id),))
        connection.commit()
    bot.guild = SimpleNamespace(
        members=[member],
        text_channels=[],
        get_member=lambda user_id: member if user_id == member.id else None,
    )
    bot.is_ready = lambda: True
    bot.is_closed = lambda: False
    token = bot.database.create_central_login_session(
        discord_user_id=member.id,
        peace_id=42,
        client_id="peacegg-web",
        project_id=None,
        scope="peace:member",
        expires_at=(datetime.now(timezone.utc) + timedelta(days=7)).isoformat(),
    )

    status, overview = run_configured_api(
        bot,
        "/api/member/overview",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert status == 200
    assert overview["overview"]["capabilities"]["investigator"] is False
    assert "investigation" not in overview["overview"]
    assert overview["overview"]["active_members"]["state"] == "empty"

    status, denied = run_configured_api(bot, "/api/member/overview")
    assert status == 401
    assert denied["code"] == "AUTH_SESSION_INVALID"


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
    headers = (site_root / "_headers").read_text(encoding="utf-8")
    assert headers.startswith("/*\n  Content-Security-Policy:")
    assert "*/" not in headers
    assert (member_root / "index.html").is_file()
    for route in ("entrar", "candidatura", "acessar", "avisos", "parceiros"):
        assert (site_root / route / "index.html").is_file()
    for route in ("estudos", "estudos/civil", "estudos/peace", "meu-processo"):
        assert (site_root / route / "index.html").is_file()
    assert not list(site_root.rglob("*.pdf")), "PDFs must stay out of the public shell until published"
    assert "/api/status" not in (site_root / "script.js").read_text(encoding="utf-8")
    assert "/api/auth/code/request" not in (site_root / "script.js").read_text(encoding="utf-8")
    assert "/api/auth/code/verify" not in (site_root / "script.js").read_text(encoding="utf-8")
    homepage = (site_root / "index.html").read_text(encoding="utf-8")
    assert "data-service-status" not in homepage
    assert "Peace Tools conectado" not in homepage
    script = "\n".join(
        [
            (site_root / "script.js").read_text(encoding="utf-8"),
            *[
                path.read_text(encoding="utf-8")
                for path in (
                    site_root / "js" / "site-core.js",
                    site_root / "js" / "public-media.js",
                    site_root / "js" / "candidature.js",
                    site_root / "js" / "login.js",
                    site_root / "js" / "member-area.js",
                )
            ],
        ]
    )
    stylesheet = "\n".join(
        [
            (site_root / "styles.css").read_text(encoding="utf-8"),
            *[
                path.read_text(encoding="utf-8")
                for path in (
                    site_root / "css" / "base.css",
                    site_root / "css" / "member.css",
                    site_root / "css" / "flows.css",
                    site_root / "css" / "media.css",
                    site_root / "css" / "responsive.css",
                    site_root / "css" / "studies.css",
                )
            ],
        ]
    )
    homepage = (site_root / "index.html").read_text(encoding="utf-8")
    assert "--canvas: #050607" in stylesheet
    assert "O seu espaço." in homepage
    assert 'href="/estudos/"' in homepage
    assert 'href="/meu-processo/"' in homepage
    assert "Estudar para entrar" in homepage
    assert "learning-hub" in homepage
    assert 'class="peace-icon"' in homepage
    assert 'id="avisos"' not in homepage
    assert 'id="parceiros"' not in homepage
    menu_control = homepage.split('class="menu-toggle"', 1)[1].split('</button>', 1)[0]
    assert '<span class="menu-toggle-label">menu</span>' in menu_control
    assert 'class="menu-toggle-arrow"' in menu_control
    assert menu_control.count('<i></i>') == 2
    assert 'menu-toggle-lines' not in homepage
    header_cta = homepage.split('class="button button--outline header-cta"', 1)[1].split("</a>", 1)[0]
    hero_cta = homepage.split('class="button button--light button--large"', 1)[1].split("</a>", 1)[0]
    assert "peace-icon" in header_cta and "discord-icon" not in header_cta
    assert "peace-icon" in hero_cta and "discord-icon" not in hero_cta

    entry_html = (site_root / "entrar" / "index.html").read_text(encoding="utf-8")
    candidature_html = (site_root / "candidatura" / "index.html").read_text(encoding="utf-8")
    login_html = (site_root / "acessar" / "index.html").read_text(encoding="utf-8")
    assert "Começar entrada" in entry_html
    assert "flow-secondary-action" in entry_html
    assert "peace-icon" in entry_html
    assert "Conectar no Discord" in candidature_html
    assert "discord-icon" in candidature_html
    assert "data-entry-connect" in candidature_html
    assert "#verify" in candidature_html
    assert "entry-help-panel" in candidature_html
    assert "application-context" in candidature_html
    assert 'class="login-layout login-layout--focused"' in login_html
    assert "flow-boundary" not in login_html
    assert "auth-note" not in login_html
    assert "Seu ID não é uma senha." not in login_html
    assert 'data-login-status role="status" aria-live="polite" hidden' in login_html
    assert 'maxlength="19"' in login_html
    assert 'inputmode="numeric"' in login_html
    assert 'src="/assets/id-card.svg"' in login_html
    assert 'name="keep-connected"' in login_html
    assert "Manter conectado neste dispositivo" in login_html
    assert "Enviar código no Discord" in login_html
    code_form = login_html.split('data-login-verify', 1)[1].split('</form>', 1)[0]
    assert 'name="peace-id"' not in code_form
    assert 'Enviar código no Discord' not in code_form
    assert 'name="access-code"' in code_form
    assert "Login indisponível" not in login_html
    assert "Conexão indisponível" not in candidature_html
    assert "/api/member/auth/request" in script
    assert "/api/member/auth/verify" in script
    assert "/api/media?seed=" in script
    assert 'data-media-list="moments"' in homepage
    assert 'data-media-list="clips"' in homepage
    assert "media-skeleton" in homepage
    assert "/api/media" in (site_root / "_redirects").read_text(encoding="utf-8")
    assert "Acesso web em preparação" not in script
    assert "status unavailable" not in script
    assert "fetch unavailable" not in script
    assert "request timeout" not in script
    assert 'data-button-label' in login_html and 'button-spinner' in login_html
    assert 'data-button-label' in candidature_html and 'button-spinner' in candidature_html
    assert 'data-candidature-toast' in candidature_html
    assert 'Candidatura pronta para revisão.' not in script
    assert 'showCandidatureToast' in script
    assert 'firstLink.focus()' in script
    assert 'copyAllowedFrom' not in script
    assert 'user-select: none' not in stylesheet
    assert '60000' in script
    assert 'aria-busy' in script
    assert 'window.sessionStorage' in script
    assert 'storeMemberSessionToken' not in script
    assert 'payload.session.token' not in script
    assert '/api/entry/start' in script
    assert '/api/entry/status' in script
    assert '/api/entry/repair' in script
    assert '/api/entry/identify' in script
    assert 'data-entry-invite-panel' in candidature_html
    assert 'data-entry-invite-open' in candidature_html
    assert candidature_html.count('data-entry-invite-open') == 1
    assert '<a class="entry-invite-url" data-entry-invite-link' in candidature_html
    assert 'data-entry-invite-link target="_blank"' not in candidature_html
    assert 'data-entry-invite-waiting' in candidature_html
    assert 'invite_unavailable' in script
    assert 'recoverEntrySession' in script
    assert 'data-entry-existing' in candidature_html
    assert 'Já sou membro' in login_html or 'Já sou membro' in entry_html
    assert 'href="/discord/"' not in candidature_html
    assert 'window.open("/candidatura/abrindo-discord.html"' not in script
    assert 'entryInviteWindowName = "peace-discord-invite"' in script
    assert "reserveEntryInviteWindow" in script
    assert "endpoint unavailable" not in script
    assert (site_root / "candidatura" / "abrindo-discord.html").is_file()
    opening_html = (site_root / "candidatura" / "abrindo-discord.html").read_text(encoding="utf-8")
    assert 'data-page="entry-loading"' in opening_html
    assert 'width="1254" height="1254"' in opening_html
    assert 'href="/styles.css?v=20261113-01"' in opening_html
    assert 'src="/script.js?v=20261113-01"' in opening_html
    assert '<style>' not in opening_html
    assert 'src="/candidatura/abrindo-discord.js?v=20261113-01"' in opening_html
    assert 'entry-loading-card' in stylesheet
    assert 'data-entry-confirm' not in candidature_html
    assert 'Progresso restaurado neste navegador' not in script
    assert 'Revisão salva neste navegador' not in script
    assert 'Candidatura salva neste navegador' not in script
    assert 'button.disabled = stageNumber > currentStage' in script
    assert '--container-background' in stylesheet
    assert '.application-card' in stylesheet and '.login-card' in stylesheet
    assert 'scrollbar-gutter: stable' in stylesheet
    assert '--scrollbar-thumb' in stylesheet and '::-webkit-scrollbar-corner' in stylesheet
    assert 'grid-template-columns: repeat(auto-fit, minmax(min(100%, 19rem), 1fr))' in stylesheet
    assert '.media-card, .media-skeleton {' in stylesheet and 'flex-direction: column;' in stylesheet
    assert '.media-card-copy {\n  flex: 1 1 auto;\n  overflow: visible;' in stylesheet
    assert '.site-nav::before' in stylesheet and '.menu-open .site-nav' in stylesheet
    assert 'grid-template-columns: repeat(2, minmax(0, 1fr))' in stylesheet
    assert 'border-radius: var(--container-radius)' in stylesheet
    assert 'backdrop-filter: var(--container-blur)' in stylesheet
    assert '-webkit-backdrop-filter: var(--container-blur)' in stylesheet
    assert '.menu-toggle-arrow i:first-child' in stylesheet
    assert '.menu-toggle-arrow i:last-child' in stylesheet
    assert '.site-header { display: grid;' in stylesheet
    assert '.flow-copy,' in stylesheet and '.application-stage,' in stylesheet
    assert 'body[data-page="candidatura"] .flow-header { display: grid; }' in stylesheet
    studies_html = (site_root / "estudos" / "index.html").read_text(encoding="utf-8")
    civil_html = (site_root / "estudos" / "civil" / "index.html").read_text(encoding="utf-8")
    peace_html = (site_root / "estudos" / "peace" / "index.html").read_text(encoding="utf-8")
    process_html = (site_root / "meu-processo" / "index.html").read_text(encoding="utf-8")
    for html in (studies_html, civil_html, peace_html, process_html):
        assert 'href="/styles.css?v=20261113-02"' in html
        assert 'src="/script.js?v=20261113-01"' in html
        assert 'aria-label="Páginas públicas"' in html
    assert "Apostila Civil" in studies_html and "Manual da Peace" in studies_html
    assert "PDF em preparação" in civil_html
    assert "Download ainda indisponível" in civil_html and "Download ainda indisponível" in peace_html
    assert "Manual de convivência em PDF" in peace_html
    assert "Como a conexão funcionará" in process_html
    assert 'aria-current="location">Estudos</a>' in civil_html
    assert 'aria-current="location">Estudos</a>' in peace_html
    assert '<nav class="study-outline"' in civil_html and '<nav class="study-outline"' in peace_html
    assert 'class="study-reader" id="capitulos" tabindex="-1"' in civil_html
    assert 'class="study-reader" id="manual" tabindex="-1"' in peace_html
    assert '<section id="avaliacao" tabindex="-1"' in civil_html
    assert '<section id="pdf" tabindex="-1"' in peace_html
    assert 'class="process-empty" id="conexao" tabindex="-1"' in process_html
    assert "Somente a Gerência poderá gerar, atribuir, revogar e corrigir provas." in process_html
    assert "Mesmo banco de questões" in civil_html
    assert "Sequência individual" in civil_html
    assert "class=\"process-identity-list\"" in process_html
    assert "Discord ID" in process_html and "Membro Peace" in process_html
    assert "A ordem será individual" in process_html
    assert "Começar pela Apostila Civil" in process_html
    assert "synthetic" not in process_html.lower()
    assert ".study-reader" in stylesheet and ".process-empty" in stylesheet
    assert ".status-tag {" in stylesheet and ".study-rule-grid" in stylesheet
    assert ".process-identity-list" in stylesheet
    assert ".flow-header-nav a[aria-current=\"page\"]::after" in stylesheet
    assert "flows.css?v=20261113-02" in (site_root / "styles.css").read_text(encoding="utf-8")
    assert "studies.css?v=20261113-02" in (site_root / "styles.css").read_text(encoding="utf-8")
    assert 'html.js-ready body { animation: none !important; }' in stylesheet
    for flow_html in (entry_html, candidature_html, login_html):
        assert "flow-header-context" not in flow_html
    for page_html in (homepage, entry_html, candidature_html, login_html):
        assert '<script>' not in page_html


def test_member_area_is_gated_and_has_no_unauthenticated_preview():
    from pathlib import Path

    site_root = Path(__file__).parents[2] / "bot" / "site"
    member_html = (site_root / "area" / "index.html").read_text(encoding="utf-8")
    script = (site_root / "script.js").read_text(encoding="utf-8")
    member_script = (site_root / "js" / "member-area.js").read_text(encoding="utf-8")

    assert 'data-page="member"' in member_html
    assert "data-member-gate" in member_html
    assert "data-member-preview" not in member_html
    assert "data-preview-toggle" not in member_html
    assert "data-preview-screen" not in member_html
    assert "prévia" not in member_html.lower()
    assert "member-header" in member_html
    assert "site-header site-header--area" not in member_html
    assert 'data-workspace-menu' not in member_html
    assert "workspace-shell" not in member_html
    assert "registros abaixo são sintéticos" not in member_html
    assert 'data-preview-toggle' not in script
    assert 'data-member-preview' not in script
    assert 'get("preview")' not in script
    assert "openPreview" not in script
    assert "investigativa" not in script
    assert "grant" not in script.lower()
    assert "gsap" not in script.lower()
    assert member_html.count("<h1") == 1
    assert 'data-member-block="announcements" aria-live' not in member_html
    assert 'data-member-block="media" aria-live' not in member_html
    assert "Intl.DateTimeFormat" in member_script
    assert "data.updated_at" in member_script
    public_media_script = (site_root / "js" / "public-media.js").read_text(encoding="utf-8")
    assert "thumbnail.width = 320" in public_media_script
    assert "avatarImage.width = 32" in public_media_script
    assert "Última leitura · uma fonte está desatualizada" in public_media_script


def test_netlify_redirects_keep_the_short_discord_route():
    from pathlib import Path

    redirects = (Path(__file__).parents[2] / "bot" / "site" / "_redirects").read_text(encoding="utf-8")

    assert "/discord https://discord.gg/qUkQH8XmcN 302!" in redirects
    assert "/discord/ https://discord.gg/qUkQH8XmcN 302!" in redirects
    assert "/estudos /estudos/ 301!" in redirects
    assert "/meu-processo /meu-processo/ 301!" in redirects
    assert "/estudos/civil /estudos/civil/ 301!" in redirects
    assert "/estudos/peace /estudos/peace/ 301!" in redirects
    assert "/estudos/a-peace /estudos/peace/ 301!" in redirects
    assert "/estudos/a-peace/ /estudos/peace/ 301!" in redirects
    assert "/api/status http://141.11.237.97:25072/api/status 200!" in redirects
    assert "/api/media http://141.11.237.97:25072/api/media 200!" in redirects
    assert "/api/member/overview http://141.11.237.97:25072/api/member/overview 200!" in redirects
    assert sum(line.startswith("/api/member/overview ") for line in redirects.splitlines()) == 1
    for route in ("/entrar", "/candidatura", "/area", "/acessar", "/avisos", "/parceiros"):
        assert f"{route} {route}/ 301!" not in redirects


def test_local_proxy_forwards_only_the_member_session_and_bearer():
    from ops.peace_site_server import filtered_member_proxy_headers

    session = "A" * 43
    challenge = "C" * 43
    bearer = "B" * 43
    headers = filtered_member_proxy_headers(
        f"unrelated=secret; peace_member_session={session}; peace_member_challenge={challenge}; legacy=ignored",
        f"Bearer {bearer}",
    )

    assert headers == {
        "Cookie": f"peace_member_session={session}; peace_member_challenge={challenge}",
        "Authorization": f"Bearer {bearer}",
    }


def test_local_proxy_rejects_redirects_before_they_can_carry_credentials():
    from ops.peace_site_server import ACL_OPENER

    class RedirectHandler(BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802 - test server hook
            self.send_response(302)
            self.send_header("Location", "https://attacker.invalid/collect")
            self.end_headers()

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), RedirectHandler)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        try:
            ACL_OPENER.open(Request(f"http://127.0.0.1:{server.server_port}/api/member/auth/session"), timeout=2)
        except HTTPError as error:
            assert error.code == 302
        else:
            raise AssertionError("the authenticated proxy opener followed a redirect")
    finally:
        server.shutdown()
        worker.join(timeout=2)


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
            ("/estudos", 301, "/estudos/"),
            ("/estudos/civil", 301, "/estudos/civil/"),
            ("/estudos/peace", 301, "/estudos/peace/"),
            ("/meu-processo", 301, "/meu-processo/"),
            ("/estudos/a-peace", 301, "/estudos/peace/"),
            ("/estudos/a-peace/", 301, "/estudos/peace/"),
            ("/entrar/", 200, None),
            ("/candidatura/", 200, None),
            ("/acessar/", 200, None),
            ("/avisos/", 200, None),
            ("/parceiros/", 200, None),
            ("/estudos/", 200, None),
            ("/estudos/civil/", 200, None),
            ("/estudos/peace/", 200, None),
            ("/meu-processo/", 200, None),
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
