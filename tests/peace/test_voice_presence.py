import asyncio
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

from bot.main import PeaceBot


AFK_CHANNEL_ID = 1466629495405543515


class FakeVoiceClient:
    def __init__(self, channel):
        self.channel = channel
        self.move_to = AsyncMock()
        self.disconnect = AsyncMock()
        self._connected = True

    def is_connected(self):
        return self._connected


class FakeVoiceChannel:
    def __init__(self, guild):
        self.id = AFK_CHANNEL_ID
        self.guild = guild
        self.connect_calls = []

    async def connect(self, *, self_mute=False):
        self.connect_calls.append({"self_mute": self_mute})
        self.guild.voice_client = FakeVoiceClient(self)
        return self.guild.voice_client


def make_bot(tmp_path: Path) -> PeaceBot:
    settings = SimpleNamespace(
        database_path=tmp_path / "peace.sqlite3",
        iris_enabled=False,
        iris_url="http://127.0.0.1:11435",
        iris_model="iris-test",
        guild_id=1,
        afk_channel_id=AFK_CHANNEL_ID,
    )
    return PeaceBot(settings)


def test_afk_presence_connects_muted_when_online(tmp_path):
    bot = make_bot(tmp_path)
    guild = SimpleNamespace(voice_client=None, change_voice_state=AsyncMock())
    afk = FakeVoiceChannel(guild)
    guild.get_channel = lambda channel_id: afk if channel_id == AFK_CHANNEL_ID else None
    bot.guild = guild

    assert asyncio.run(bot.ensure_afk_presence()) is True

    assert afk.connect_calls == [{"self_mute": True}]
    assert guild.voice_client.channel is afk


def test_afk_presence_moves_existing_connection_and_reapplies_mute(tmp_path):
    bot = make_bot(tmp_path)
    guild = SimpleNamespace(change_voice_state=AsyncMock())
    afk = FakeVoiceChannel(guild)
    other = SimpleNamespace(id=987)
    voice = FakeVoiceClient(other)
    guild.voice_client = voice
    guild.get_channel = lambda channel_id: afk if channel_id == AFK_CHANNEL_ID else None
    bot.guild = guild

    assert asyncio.run(bot.ensure_afk_presence()) is True

    voice.move_to.assert_awaited_once_with(afk)
    guild.change_voice_state.assert_awaited_once_with(channel=afk, self_mute=True)


def test_afk_presence_reconciles_when_discord_moves_or_unmutes_the_bot(tmp_path):
    bot = make_bot(tmp_path)
    bot._connection.user = SimpleNamespace(id=77)
    bot.ensure_afk_presence = AsyncMock(return_value=True)
    member = SimpleNamespace(id=77)
    after = SimpleNamespace(channel=SimpleNamespace(id=987), self_mute=False)

    asyncio.run(bot.on_voice_state_update(member, SimpleNamespace(), after))

    bot.ensure_afk_presence.assert_awaited_once()
