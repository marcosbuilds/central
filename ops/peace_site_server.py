"""Serve the public Peace site locally with its Netlify-compatible routes.

This development server is intentionally localhost-only. It serves the static
site, redirects public entry aliases, and proxies only the read-only status
endpoint to the configured ACLClouds origin. It must not be used as a public
edge or as an authenticated API gateway.
"""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


SITE_DIRECTORY = Path(__file__).resolve().parents[1] / "bot" / "site"
ACL_STATUS_URL = "http://api.peacegg.com.br:25072/api/status"
DISCORD_INVITE = "https://discord.gg/qUkQH8XmcN"


class PeaceSiteHandler(SimpleHTTPRequestHandler):
    """Handle static files and the small local route contract."""

    server_version = "PeaceSiteLocal/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(SITE_DIRECTORY), **kwargs)

    def end_headers(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_GET(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        route = self.path.split("?", 1)[0]

        if route in {"/discord", "/discord/", "/entrar", "/entrar/"}:
            self._redirect(DISCORD_INVITE, 302)
            return

        if route in {"/area", "/acessar", "/acessar/"}:
            self._redirect("/area/", 301)
            return

        if route == "/api/status":
            self._proxy_status()
            return

        if route == "/_redirects":
            self.send_error(404, "Route manifest is not served by the local preview")
            return

        super().do_GET()

    def do_OPTIONS(self) -> None:  # noqa: N802 - required by BaseHTTPRequestHandler
        if self.path.split("?", 1)[0] != "/api/status":
            self.send_error(404)
            return

        self.send_response(204)
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Accept")
        self.end_headers()

    def _redirect(self, location: str, status: int) -> None:
        self.send_response(status)
        self.send_header("Location", location)
        self.end_headers()

    def _proxy_status(self) -> None:
        request = Request(
            ACL_STATUS_URL,
            headers={"Accept": "application/json", "User-Agent": "PeaceSiteLocal/1.0"},
        )

        try:
            with urlopen(request, timeout=8) as response:  # noqa: S310 - fixed public URL
                payload = response.read()
                status = response.status
                content_type = response.headers.get("Content-Type", "application/json")
        except HTTPError as error:
            payload = error.read()
            status = error.code
            content_type = error.headers.get("Content-Type", "application/json")
        except (TimeoutError, URLError, OSError):
            payload = json.dumps(
                {
                    "status": "unavailable",
                    "source": "aclclouds",
                    "message": "ACLClouds não respondeu ao proxy local.",
                },
                ensure_ascii=False,
            ).encode("utf-8")
            status = 503
            content_type = "application/json; charset=utf-8"

        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the local Peace site preview.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (localhost by default).")
    parser.add_argument("--port", type=int, default=4173, help="Bind port (4173 by default).")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), PeaceSiteHandler)
    print(f"Peace site: http://{args.host}:{args.port}/")
    print(f"ACL status proxy: {ACL_STATUS_URL}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
