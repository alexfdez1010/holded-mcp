"""Exercise the FastAPI deployment: password OAuth and MCP over streamable HTTP."""

from __future__ import annotations

import base64
import hashlib
import os
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import httpx
import httpx2
import pytest
from mcp import Client
from mcp.client.streamable_http import streamable_http_client

from holded_mcp.app import create_app, public_url_from_env
from holded_mcp.auth import hash_password, parse_password_hash, verify_password

HOLDED_KEY = "holded_app_test_key"
PASSWORD = "correct horse battery staple"
# Few iterations keep the tests fast; production hashes use PASSWORD_ITERATIONS.
PASSWORD_HASH = hash_password(PASSWORD, iterations=1000)
BASE_URL = "http://localhost"
MCP_URL = f"{BASE_URL}/mcp"
REDIRECT_URI = "http://localhost:9999/callback"
VERIFIER = "test-verifier-" + "x" * 40
CHALLENGE = (
    base64.urlsafe_b64encode(hashlib.sha256(VERIFIER.encode()).digest()).decode().rstrip("=")
)


@pytest.fixture
def holded_requests():
    return []


@pytest.fixture
def app(holded_requests):
    def handle(request):
        holded_requests.append(request)
        return httpx.Response(200, json={"data": [], "has_more": False})

    return create_app(HOLDED_KEY, PASSWORD_HASH, BASE_URL, transport=httpx.MockTransport(handle))


def http_client(app, headers=None):
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url=BASE_URL, headers=headers
    )


async def run_lifespan(app, body):
    async with app.router.lifespan_context(app):
        return await body()


async def register(client, **metadata):
    response = await client.post(
        "/register",
        json={
            "redirect_uris": [REDIRECT_URI],
            "token_endpoint_auth_method": "none",
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "client_name": "Test client",
            **metadata,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


async def start_login(client, client_id):
    response = await client.get(
        "/authorize",
        params={
            "response_type": "code",
            "client_id": client_id,
            "redirect_uri": REDIRECT_URI,
            "code_challenge": CHALLENGE,
            "code_challenge_method": "S256",
            "state": "state-123",
            "resource": MCP_URL,
        },
    )
    assert response.status_code == 302, response.text
    location = urlsplit(response.headers["location"])
    assert location.path == "/login"
    return parse_qs(location.query)["request"][0]


async def log_in(client, request, password=PASSWORD):
    return await client.post("/login", data={"request": request, "password": password})


async def authorize(client, registration):
    request = await start_login(client, registration["client_id"])
    response = await log_in(client, request)
    assert response.status_code == 302, response.text
    location = urlsplit(response.headers["location"])
    assert f"{location.scheme}://{location.netloc}{location.path}" == REDIRECT_URI
    query = parse_qs(location.query)
    assert query["state"] == ["state-123"]
    return query["code"][0]


async def exchange_code(client, registration, code, **extra):
    return await client.post(
        "/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": registration["client_id"],
            "code_verifier": VERIFIER,
            "resource": MCP_URL,
            **extra,
        },
    )


def test_password_hash_helpers():
    assert verify_password(PASSWORD, PASSWORD_HASH)
    assert not verify_password("wrong", PASSWORD_HASH)
    assert hash_password(PASSWORD) != hash_password(PASSWORD)
    assert parse_password_hash(f" {PASSWORD_HASH}\n") == PASSWORD_HASH
    for value in ("", "abc", PASSWORD_HASH.replace("pbkdf2", "md5"), PASSWORD_HASH + ":x"):
        with pytest.raises(ValueError):
            parse_password_hash(value)
    with pytest.raises(ValueError):
        create_app(HOLDED_KEY, "not-a-hash", BASE_URL)
    with pytest.raises(ValueError):
        create_app(HOLDED_KEY, PASSWORD_HASH, "http://example.com")


def test_public_url_from_env(monkeypatch):
    monkeypatch.delenv("MCP_PUBLIC_URL", raising=False)
    monkeypatch.delenv("RAILWAY_PUBLIC_DOMAIN", raising=False)
    assert public_url_from_env(1234) == "http://localhost:1234"
    monkeypatch.setenv("RAILWAY_PUBLIC_DOMAIN", "holded.up.railway.app")
    assert public_url_from_env() == "https://holded.up.railway.app"
    monkeypatch.setenv("MCP_PUBLIC_URL", "https://mcp.example.com/")
    assert public_url_from_env() == "https://mcp.example.com"


@pytest.mark.parametrize(
    "headers",
    [
        None,
        {"Authorization": f"Bearer {HOLDED_KEY}"},
        {"Authorization": f"Bearer {PASSWORD}"},
        {"Authorization": "Bearer access.e30.forged"},
        {"Authorization": "Bearer "},
    ],
)
async def test_rejects_missing_or_wrong_credentials(app, holded_requests, headers):
    async def body():
        async with http_client(app, headers) as client:
            response = await client.post("/mcp", json=INITIALIZE)
            assert response.status_code == 401
            challenge = response.headers["www-authenticate"]
            assert challenge.startswith("Bearer")
            assert "/.well-known/oauth-protected-resource/mcp" in challenge

    await run_lifespan(app, body)
    assert not holded_requests


async def test_health_and_metadata_are_public(app):
    async with http_client(app) as client:
        assert (await client.get("/health")).json() == {"status": "ok"}
        resource = (await client.get("/.well-known/oauth-protected-resource/mcp")).json()
        assert resource["resource"] == MCP_URL
        assert resource["authorization_servers"] == [BASE_URL]
        metadata = (await client.get("/.well-known/oauth-authorization-server")).json()
        assert metadata["issuer"] == BASE_URL
        assert metadata["registration_endpoint"] == f"{BASE_URL}/register"
        assert "S256" in metadata["code_challenge_methods_supported"]


async def test_login_page_and_wrong_password(app):
    async with http_client(app) as client:
        registration = await register(client)
        request = await start_login(client, registration["client_id"])
        page = await client.get("/login", params={"request": request})
        assert page.status_code == 200
        assert "Test client" in page.text
        assert 'type="password"' in page.text
        assert page.headers["x-frame-options"] == "DENY"
        wrong = await log_in(client, request, "wrong")
        assert wrong.status_code == 401
        assert "Wrong password" in wrong.text
        tampered = await log_in(client, request[:-2] + "xx")
        assert tampered.status_code == 400
        assert (await client.get("/login", params={"request": "nope"})).status_code == 400


async def test_failed_logins_are_rate_limited(app):
    async with http_client(app) as client:
        registration = await register(client)
        request = await start_login(client, registration["client_id"])
        for _ in range(10):
            assert (await log_in(client, request, "wrong")).status_code == 401
        blocked = await log_in(client, request)
        assert blocked.status_code == 401
        assert "Too many failed attempts" in blocked.text


async def test_rejects_unknown_client_and_resource(app):
    async with http_client(app) as client:
        response = await client.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": "client.forged.mac",
                "redirect_uri": REDIRECT_URI,
                "code_challenge": CHALLENGE,
                "code_challenge_method": "S256",
            },
        )
        assert response.status_code == 400
        registration = await register(client)
        response = await client.get(
            "/authorize",
            params={
                "response_type": "code",
                "client_id": registration["client_id"],
                "redirect_uri": REDIRECT_URI,
                "code_challenge": CHALLENGE,
                "code_challenge_method": "S256",
                "resource": "https://other.example.com/mcp",
            },
        )
        assert response.status_code == 302
        assert "error=invalid_target" in response.headers["location"]


async def test_oauth_flow_and_mcp_over_http(app, holded_requests):
    async def body():
        async with http_client(app) as client:
            registration = await register(client)
            assert "client_secret" not in registration or registration["client_secret"] is None
            code = await authorize(client, registration)

            bad_verifier = await exchange_code(client, registration, code, code_verifier="y" * 50)
            assert bad_verifier.status_code == 400
            tokens = await exchange_code(client, registration, code)
            assert tokens.status_code == 200, tokens.text
            tokens = tokens.json()
            assert tokens["token_type"].lower() == "bearer"
            assert (await exchange_code(client, registration, code)).status_code == 400

            refreshed = await client.post(
                "/token",
                data={
                    "grant_type": "refresh_token",
                    "refresh_token": tokens["refresh_token"],
                    "client_id": registration["client_id"],
                },
            )
            assert refreshed.status_code == 200, refreshed.text
            access_token = refreshed.json()["access_token"]

        http = httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app),
            headers={"Authorization": f"Bearer {access_token}"},
        )
        async with http, Client(streamable_http_client(MCP_URL, http_client=http)) as client:
            tools = {tool.name for tool in (await client.list_tools()).tools}
            assert "holded_write" in tools
            result = await client.call_tool("holded_read", {"operation_id": "list_invoices"})
            assert not result.is_error

    await run_lifespan(app, body)
    assert holded_requests[0].headers["Authorization"] == f"Bearer {HOLDED_KEY}"


async def test_confidential_client_and_restart(app, holded_requests):
    async with http_client(app) as client:
        registration = await register(client, token_endpoint_auth_method="client_secret_post")
        assert registration["client_secret"]
        code = await authorize(client, registration)
        missing_secret = await exchange_code(client, registration, code)
        assert missing_secret.status_code == 401
        tokens = await exchange_code(
            client, registration, code, client_secret=registration["client_secret"]
        )
        assert tokens.status_code == 200, tokens.text
        access_token = tokens.json()["access_token"]

    # Registrations and tokens are signed, so they survive a restart with the same config.
    restarted = create_app(HOLDED_KEY, PASSWORD_HASH, BASE_URL)

    async def initialize():
        async with http_client(restarted, {"Authorization": f"Bearer {access_token}"}) as client:
            return await client.post(
                "/mcp", json=INITIALIZE, headers={"Accept": "application/json, text/event-stream"}
            )

    response = await run_lifespan(restarted, initialize)
    assert response.status_code == 200, response.text
    # A new password signs everyone out.
    rotated = create_app(HOLDED_KEY, hash_password("new", iterations=1000), BASE_URL)
    async with http_client(rotated, {"Authorization": f"Bearer {access_token}"}) as client:
        assert (await client.post("/mcp", json=INITIALIZE)).status_code == 401


def test_http_mode_requires_password_hash():
    result = subprocess.run(
        [sys.executable, "-m", "holded_mcp"],
        env={**os.environ, "HOLDED_API_KEY": "holded_test", "MCP_PASSWORD_HASH": ""},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert "MCP_PASSWORD_HASH" in result.stderr
    assert "Traceback" not in result.stderr


def test_cli_hash_password():
    hashed = subprocess.run(
        [sys.executable, "-m", "holded_mcp", "--hash-password"],
        input="s3cret\n",
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert hashed.returncode == 0, hashed.stderr
    name, _, value = hashed.stdout.strip().partition("=")
    assert name == "MCP_PASSWORD_HASH"
    assert verify_password("s3cret", value)


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
