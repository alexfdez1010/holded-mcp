"""Bearer authentication against a SHA-256 hash of the MCP access key."""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from typing import Any

_HEX_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def hash_key(key: str) -> str:
    """Return the lowercase hex SHA-256 digest stored in MCP_API_KEY_HASH."""
    return hashlib.sha256(key.encode("utf-8")).hexdigest()


def generate_key() -> str:
    """Return a new random access key with 256 bits of entropy."""
    return secrets.token_urlsafe(32)


def parse_key_hash(value: str) -> str:
    """Validate a configured hash; raise ValueError for anything but 64 hex characters."""
    digest = value.strip().lower()
    if not _HEX_SHA256.match(digest):
        raise ValueError("MCP_API_KEY_HASH must be a hex SHA-256 digest (64 characters).")
    return digest


class BearerHashAuth:
    """ASGI middleware accepting `Authorization: Bearer <key>` when sha256(key) matches.

    The raw key never lives on the server; only its hash does. Paths in `public_paths`
    (for example health checks) skip authentication.
    """

    def __init__(self, app: Any, *, key_hash: str, public_paths: frozenset[str]) -> None:
        self.app = app
        self.key_hash = parse_key_hash(key_hash)
        self.public_paths = public_paths

    def authorized(self, headers: list[tuple[bytes, bytes]]) -> bool:
        for name, value in headers:
            if name.lower() != b"authorization":
                continue
            scheme, _, token = value.decode("latin-1").partition(" ")
            if scheme.lower() != "bearer" or not token.strip():
                return False
            return hmac.compare_digest(hash_key(token.strip()), self.key_hash)
        return False

    async def __call__(self, scope: Any, receive: Any, send: Any) -> None:
        if scope["type"] != "http" or scope["path"] in self.public_paths:
            await self.app(scope, receive, send)
            return
        if self.authorized(scope["headers"]):
            await self.app(scope, receive, send)
            return
        body = b'{"error":"unauthorized"}'
        await send(
            {
                "type": "http.response.start",
                "status": 401,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                    (b"www-authenticate", b'Bearer realm="holded-mcp"'),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})
