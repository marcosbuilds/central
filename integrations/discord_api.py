from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any


class DiscordAPIError(RuntimeError):
    pass


class DiscordAPI:
    def __init__(self, token: str, api_base: str = "https://discord.com/api/v10"):
        self.api_base = api_base.rstrip("/")
        self.headers = {
            "Authorization": f"Bot {token}",
            "User-Agent": "DiscordBot (https://localhost, 0.1)",
            "Accept": "application/json",
        }

    def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        query = urllib.parse.urlencode({key: value for key, value in (params or {}).items() if value is not None})
        url = f"{self.api_base}{path}"
        if query:
            url = f"{url}?{query}"
        for attempt in range(5):
            request = urllib.request.Request(url, headers=self.headers, method="GET")
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as error:
                body = error.read().decode("utf-8", errors="replace")
                if error.code == 429:
                    try:
                        retry_after = float(json.loads(body).get("retry_after", 1.0))
                    except (ValueError, TypeError, json.JSONDecodeError):
                        retry_after = 1.0
                    time.sleep(min(retry_after, 30.0))
                    continue
                raise DiscordAPIError(f"Discord API {error.code} em {path}: {body[:500]}") from error
            except urllib.error.URLError as error:
                if attempt == 4:
                    raise DiscordAPIError(f"Falha de rede em {path}: {error}") from error
                time.sleep(1.0 + attempt)
        raise DiscordAPIError(f"Falha ao consultar {path}")

    def patch(self, path: str, payload: dict[str, Any]) -> Any:
        url = f"{self.api_base}{path}"
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(5):
            headers = {**self.headers, "Content-Type": "application/json"}
            request = urllib.request.Request(url, data=body, headers=headers, method="PATCH")
            try:
                with urllib.request.urlopen(request, timeout=30) as response:
                    raw = response.read().decode("utf-8")
                    return json.loads(raw) if raw else None
            except urllib.error.HTTPError as error:
                response_body = error.read().decode("utf-8", errors="replace")
                if error.code == 429:
                    try:
                        retry_after = float(json.loads(response_body).get("retry_after", 1.0))
                    except (ValueError, TypeError, json.JSONDecodeError):
                        retry_after = 1.0
                    time.sleep(min(retry_after, 30.0))
                    continue
                raise DiscordAPIError(f"Discord API {error.code} em {path}: {response_body[:500]}") from error
            except urllib.error.URLError as error:
                if attempt == 4:
                    raise DiscordAPIError(f"Falha de rede em {path}: {error}") from error
                time.sleep(1.0 + attempt)
        raise DiscordAPIError(f"Falha ao atualizar {path}")

    def current_bot(self) -> dict[str, Any]:
        return self.get("/users/@me")

    def guild_roles(self, guild_id: int) -> list[dict[str, Any]]:
        return self.get(f"/guilds/{guild_id}/roles")

    def guild_channels(self, guild_id: int) -> list[dict[str, Any]]:
        return self.get(f"/guilds/{guild_id}/channels")

    def guild_members(self, guild_id: int) -> list[dict[str, Any]]:
        members: list[dict[str, Any]] = []
        after = "0"
        while True:
            page = self.get(
                f"/guilds/{guild_id}/members",
                {"limit": 1000, "after": after},
            )
            if not page:
                break
            members.extend(page)
            if len(page) < 1000:
                break
            after = str(page[-1]["user"]["id"])
        return members

    def bot_messages(self, guild_id: int, bot_user_id: int) -> list[dict[str, Any]]:
        messages: list[dict[str, Any]] = []
        offset = 0
        while True:
            page = self.get(
                f"/guilds/{guild_id}/messages/search",
                {"author_id": bot_user_id, "limit": 25, "offset": offset},
            )
            batch = page.get("messages", [])
            if not batch:
                break
            # O endpoint de busca retorna cada mensagem dentro de uma lista
            # (mesmo quando há apenas uma mensagem naquele agrupamento).
            for item in batch:
                if isinstance(item, list):
                    messages.extend(item)
                else:
                    messages.append(item)
            total = int(page.get("total_results", len(messages)))
            offset += len(batch)
            if offset >= total:
                break
        return messages

    def snapshot(self, guild_id: int, founder_id: int, peace_role_id: int) -> dict[str, Any]:
        bot = self.current_bot()
        roles = self.guild_roles(guild_id)
        channels = self.guild_channels(guild_id)
        members = self.guild_members(guild_id)
        peace_role = str(peace_role_id)
        target_members = [
            member
            for member in members
            if peace_role in {str(role_id) for role_id in member.get("roles", [])}
            or int(member["user"]["id"]) == founder_id
        ]
        messages = self.bot_messages(guild_id, int(bot["id"]))
        return {
            "collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "guild_id": str(guild_id),
            "bot": bot,
            "roles": roles,
            "channels": channels,
            "members_total": len(members),
            "members": target_members,
            "bot_messages": messages,
        }

