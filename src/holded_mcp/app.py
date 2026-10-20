"""Deployable FastAPI app serving the MCP server over streamable HTTP at /mcp."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI

from holded_mcp import __version__
from holded_mcp.auth import BearerHashAuth, parse_key_hash
from holded_mcp.server import create_server

MCP_PATH = "/mcp"
HEALTH_PATH = "/health"


def create_app(
    api_key: str,
    key_hash: str,
    *,
    read_only: bool = False,
    timeout: float = 30,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Build the app; clients authenticate with `Authorization: Bearer <access key>`."""
    key_hash = parse_key_hash(key_hash)
    server = create_server(api_key, read_only=read_only, timeout=timeout, transport=transport)
    # Stateless JSON responses let the app scale horizontally without sticky sessions.
    # Host checks are disabled because the app sits behind a public hostname and bearer auth.
    mcp_app = server.streamable_http_app(
        streamable_http_path=MCP_PATH, stateless_http=True, json_response=True, host="0.0.0.0"
    )

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        async with server.session_manager.run():
            yield

    app = FastAPI(
        title="Holded API MCP",
        version=__version__,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    @app.get(HEALTH_PATH, include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    app.mount("/", mcp_app)
    app.add_middleware(BearerHashAuth, key_hash=key_hash, public_paths=frozenset({HEALTH_PATH}))
    return app


def app_from_env() -> FastAPI:
    """Factory for `uvicorn --factory holded_mcp.app:app_from_env`."""
    timeout = float(os.environ.get("HOLDED_TIMEOUT", "30"))
    read_only = os.environ.get("HOLDED_READ_ONLY", "").strip().lower() in {"1", "true", "yes"}
    return create_app(
        os.environ.get("HOLDED_API_KEY", ""),
        os.environ.get("MCP_API_KEY_HASH", ""),
        read_only=read_only,
        timeout=timeout,
    )
