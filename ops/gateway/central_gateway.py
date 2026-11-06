"""Small dependency-free WSGI gateway for the Central deployment smoke test.

The PythonAnywhere free tier is used as a reachable control-plane probe, not as
the source of truth for project data. The desktop application remains usable
when this gateway is unavailable. Secrets are read only from the process
environment and are never returned by an endpoint or written to logs.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Callable, Iterable


VERSION = "0.2.0"


def _json_response(start_response: Callable, status: str, payload: dict) -> list[bytes]:
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    start_response(
        status,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Cache-Control", "no-store"),
            ("Content-Length", str(len(body))),
        ],
    )
    return [body]


def _configuration() -> dict[str, object]:
    # Only expose booleans here. The values themselves may contain credentials
    # or identifying deployment details and must not leave the process.
    return {
        "supabase_url_configured": bool(os.environ.get("CENTRAL_SUPABASE_URL")),
        "supabase_publishable_key_configured": bool(
            os.environ.get("CENTRAL_SUPABASE_PUBLISHABLE_KEY")
        ),
    }


def application(environ: dict, start_response: Callable) -> Iterable[bytes]:
    """WSGI entry point expected by PythonAnywhere."""

    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = environ.get("PATH_INFO", "/") or "/"

    if method != "GET":
        return _json_response(
            start_response,
            "405 Method Not Allowed",
            {"error": "method_not_allowed", "allowed": ["GET"]},
        )

    if path in {"/", "/healthz", "/v1/health"}:
        return _json_response(
            start_response,
            "200 OK",
            {
                "service": "central-gateway",
                "status": "ok",
                "deployment": "pythonanywhere",
                "version": VERSION,
                "checked_at": datetime.now(timezone.utc).isoformat(),
                "configuration": _configuration(),
            },
        )

    if path == "/v1/capabilities":
        return _json_response(
            start_response,
            "200 OK",
            {
                "service": "central-gateway",
                "version": VERSION,
                "available": ["health"],
                "not_available": [
                    "continuous_sse",
                    "file_sync",
                    "provider_runs",
                ],
                "control_plane": {
                    "events": "supabase_realtime_websocket",
                    "files": "syncthing_p2p",
                    "gateway_role": "health_and_configuration_probe",
                },
                "reason": "Long-lived streaming and file bytes stay outside the PythonAnywhere free worker.",
            },
        )

    return _json_response(
        start_response,
        "404 Not Found",
        {"error": "not_found", "path": path},
    )


if __name__ == "__main__":  # pragma: no cover - convenience for local smoke tests
    from wsgiref.simple_server import make_server

    port = int(os.environ.get("CENTRAL_GATEWAY_PORT", "8080"))
    with make_server("127.0.0.1", port, application) as server:
        print(f"Central gateway listening on http://127.0.0.1:{port}")
        server.serve_forever()
