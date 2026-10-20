"""Exercise the FastAPI deployment: bearer-hash auth and MCP over streamable HTTP."""

from __future__ import annotations

import os
import subprocess
import sys

import httpx
import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from holded_mcp.app import create_app
from holded_mcp.auth import generate_key, hash_key, parse_key_hash

HOLDED_KEY = "holded_app_test_key"
ACCESS_KEY = "mcp_access_test_key"


@pytest.fixture
def holded_requests():
    return []


@pytest.fixture
def app(holded_requests):
    def handle(request):
        holded_requests.append(request)
        return httpx.Response(200, json={"data": [], "has_more": False})

    return create_app(HOLDED_KEY, hash_key(ACCESS_KEY), transport=httpx.MockTransport(handle))


def http_client(app, headers=None):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test", headers=headers
    )


async def run_lifespan(app, body):
    async with app.router.lifespan_context(app):
        return await body()


def test_hash_helpers():
    assert hash_key("abc") == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert parse_key_hash(" " + hash_key("abc").upper() + "\n") == hash_key("abc")
    assert len(generate_key()) >= 43
    for value in ("", "abc", "g" * 64, hash_key("abc") + "0"):
        with pytest.raises(ValueError):
            parse_key_hash(value)
    with pytest.raises(ValueError):
        create_app(HOLDED_KEY, "not-a-hash")


@pytest.mark.parametrize(
    "headers",
    [
        None,
        {"Authorization": f"Bearer {HOLDED_KEY}"},
        {"Authorization": f"Bearer {hash_key(ACCESS_KEY)}"},
        {"Authorization": f"Basic {ACCESS_KEY}"},
        {"Authorization": "Bearer "},
    ],
)
async def test_rejects_missing_or_wrong_credentials(app, holded_requests, headers):
    async def body():
        async with http_client(app, headers) as client:
            response = await client.post(MCP_URL, json=INITIALIZE)
            assert response.status_code == 401
            assert response.headers["www-authenticate"].startswith("Bearer")

    await run_lifespan(app, body)
    assert not holded_requests


async def test_health_is_public(app):
    async with http_client(app) as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


async def test_mcp_over_http_with_valid_key(app, holded_requests):
    async def body():
        http = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            headers={"Authorization": f"Bearer {ACCESS_KEY}"},
        )
        async with http, Client(streamable_http_client(MCP_URL, http_client=http)) as client:
            tools = {tool.name for tool in (await client.list_tools()).tools}
            assert "holded_write" in tools
            result = await client.call_tool("holded_read", {"operation_id": "list_invoices"})
            assert not result.is_error

    await run_lifespan(app, body)
    assert holded_requests[0].headers["Authorization"] == f"Bearer {HOLDED_KEY}"


def test_http_mode_requires_key_hash():
    result = subprocess.run(
        [sys.executable, "-m", "holded_mcp"],
        env={**os.environ, "HOLDED_API_KEY": "holded_test", "MCP_API_KEY_HASH": ""},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "MCP_API_KEY_HASH" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_hash_and_generate_key():
    hashed = subprocess.run(
        [sys.executable, "-m", "holded_mcp", "--hash-key"],
        input="abc\n",
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert hashed.returncode == 0
    assert hashed.stdout.strip() == hash_key("abc")
    generated = subprocess.run(
        [sys.executable, "-m", "holded_mcp", "--generate-key"],
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert generated.returncode == 0
    key_line, hash_line = generated.stdout.strip().splitlines()
    assert hash_line == f"MCP_API_KEY_HASH={hash_key(key_line.rsplit(' ', 1)[1])}"


MCP_URL = "http://test/mcp"
INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2025-06-18",
        "capabilities": {},
        "clientInfo": {"name": "test", "version": "0"},
    },
}
