"""Single-password OAuth 2.1 authorization server for the deployed MCP endpoint.

MCP clients (Claude Desktop, Claude Code, ...) discover this server through the standard
metadata endpoints, register dynamically, and send the user to a login page that asks for
one password. Only a PBKDF2 hash of that password lives on the server.

All OAuth artifacts (client registrations, authorization codes, access and refresh tokens)
are HMAC-signed payloads, so nothing has to be stored: tokens survive restarts and work
across replicas. The signing key is derived from the password hash and the Holded API key,
so changing the password signs every client out.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import time
from typing import Any

from mcp.server.auth.provider import (
    AccessToken,
    AuthorizationCode,
    AuthorizationParams,
    AuthorizeError,
    RefreshToken,
    construct_redirect_uri,
)
from mcp.shared.auth import OAuthClientInformationFull, OAuthToken
from pydantic import AnyUrl

PASSWORD_SCHEME = "pbkdf2-sha256"
PASSWORD_ITERATIONS = 600_000

LOGIN_TTL = 10 * 60
CODE_TTL = 5 * 60
ACCESS_TTL = 60 * 60
REFRESH_TTL = 90 * 24 * 60 * 60

# Client metadata kept inside the signed client_id; enough to validate later requests.
CLIENT_FIELDS = (
    "redirect_uris",
    "token_endpoint_auth_method",
    "grant_types",
    "response_types",
    "scope",
    "client_name",
)


def _b64encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _b64decode(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def hash_password(password: str, *, iterations: int = PASSWORD_ITERATIONS) -> str:
    """Return the `pbkdf2-sha256:<iterations>:<salt>:<hash>` value stored in MCP_PASSWORD_HASH."""
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"{PASSWORD_SCHEME}:{iterations}:{_b64encode(salt)}:{_b64encode(digest)}"


def parse_password_hash(value: str) -> str:
    """Validate a configured password hash; raise ValueError if it is malformed."""
    encoded = value.strip()
    try:
        scheme, iterations, salt, digest = encoded.split(":")
        valid = (
            scheme == PASSWORD_SCHEME
            and int(iterations) > 0
            and len(_b64decode(salt)) >= 16
            and len(_b64decode(digest)) == 32
        )
    except ValueError:
        valid = False
    if not valid:
        raise ValueError(
            "MCP_PASSWORD_HASH must be a value printed by `holded-mcp --hash-password`."
        )
    return encoded


def verify_password(password: str, encoded: str) -> bool:
    """Check a password against a hash from `hash_password`, in constant time."""
    _, iterations, salt, digest = parse_password_hash(encoded).split(":")
    candidate = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), _b64decode(salt), int(iterations)
    )
    return hmac.compare_digest(candidate, _b64decode(digest))


class Signer:
    """Sign and verify `<kind>.<payload>.<mac>` tokens carrying JSON payloads."""

    def __init__(self, key: bytes) -> None:
        self.key = key

    def mac(self, message: str) -> str:
        return _b64encode(hmac.new(self.key, message.encode("ascii"), hashlib.sha256).digest())

    def sign(self, kind: str, payload: dict[str, Any], ttl: int | None = None) -> str:
        if ttl is not None:
            payload = {**payload, "exp": int(time.time()) + ttl}
        body = _b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
        return f"{kind}.{body}.{self.mac(f'{kind}.{body}')}"

    def load(self, kind: str, token: str) -> dict[str, Any] | None:
        """Return the payload of a valid, unexpired token of this kind, else None."""
        prefix, _, rest = token.partition(".")
        body, _, mac = rest.partition(".")
        if prefix != kind or not hmac.compare_digest(mac, self.mac(f"{kind}.{body}")):
            return None
        try:
            payload = json.loads(_b64decode(body))
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        if "exp" in payload and payload["exp"] < time.time():
            return None
        return payload


class PasswordOAuthProvider:
    """OAuthAuthorizationServerProvider whose authorization step is a password login page."""

    def __init__(
        self,
        password_hash: str,
        *,
        secret: str,
        issuer_url: str,
        resource_url: str,
        login_path: str,
    ) -> None:
        self.password_hash = parse_password_hash(password_hash)
        key = hmac.new(
            secret.encode("utf-8"), b"holded-mcp-oauth:" + self.password_hash.encode(), "sha256"
        ).digest()
        self.signer = Signer(key)
        self.resource_url = resource_url
        self.login_url = issuer_url.rstrip("/") + login_path
        self.used_codes: dict[str, float] = {}

    def check_password(self, password: str) -> bool:
        return verify_password(password, self.password_hash)

    def client_secret(self, client_id: str) -> str:
        return self.signer.mac(f"secret.{client_id}")

    # Dynamic client registration: the client_id is the signed registration itself.

    async def register_client(self, client_info: OAuthClientInformationFull) -> None:
        metadata = client_info.model_dump(mode="json", include=set(CLIENT_FIELDS))
        client_info.client_id = self.signer.sign("client", metadata)
        if client_info.client_secret is not None:
            client_info.client_secret = self.client_secret(client_info.client_id)

    async def get_client(self, client_id: str) -> OAuthClientInformationFull | None:
        metadata = self.signer.load("client", client_id)
        if metadata is None:
            return None
        confidential = metadata.get("token_endpoint_auth_method") != "none"
        return OAuthClientInformationFull.model_validate(
            {
                **metadata,
                "client_id": client_id,
                "client_secret": self.client_secret(client_id) if confidential else None,
                "client_secret_expires_at": 0 if confidential else None,
            }
        )

    # Authorization: park the validated request in a signed token and send the user to log in.

    async def authorize(
        self, client: OAuthClientInformationFull, params: AuthorizationParams
    ) -> str:
        if params.resource is not None and params.resource.rstrip("/") != self.resource_url:
            raise AuthorizeError("invalid_target", "Unknown resource for this server.")
        request = self.signer.sign(
            "login",
            {
                "client_id": client.client_id,
                "client_name": client.client_name,
                "redirect_uri": str(params.redirect_uri),
                "explicit": params.redirect_uri_provided_explicitly,
                "code_challenge": params.code_challenge,
                "state": params.state,
                "scopes": params.scopes or [],
            },
            LOGIN_TTL,
        )
        return construct_redirect_uri(self.login_url, request=request)

    def load_login_request(self, request: str) -> dict[str, Any] | None:
        return self.signer.load("login", request)

    def approve(self, login: dict[str, Any]) -> str:
        """Issue an authorization code for a login request; return the client redirect URL."""
        code = self.signer.sign(
            "code", {**login, "state": None, "nonce": secrets.token_urlsafe(16)}, CODE_TTL
        )
        return construct_redirect_uri(login["redirect_uri"], code=code, state=login["state"])

    async def load_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: str
    ) -> AuthorizationCode | None:
        data = self.signer.load("code", authorization_code)
        if data is None or data["client_id"] != client.client_id:
            return None
        if data["nonce"] in self.used_codes:
            return None
        return AuthorizationCode(
            code=authorization_code,
            scopes=data["scopes"],
            expires_at=data["exp"],
            client_id=data["client_id"],
            code_challenge=data["code_challenge"],
            redirect_uri=AnyUrl(data["redirect_uri"]),
            redirect_uri_provided_explicitly=data["explicit"],
            resource=self.resource_url,
        )

    async def exchange_authorization_code(
        self, client: OAuthClientInformationFull, authorization_code: AuthorizationCode
    ) -> OAuthToken:
        # Codes are single use within this process; PKCE protects them across replicas.
        now = time.time()
        self.used_codes = {nonce: exp for nonce, exp in self.used_codes.items() if exp > now}
        data = self.signer.load("code", authorization_code.code) or {}
        self.used_codes[data.get("nonce", "")] = authorization_code.expires_at
        return self.issue_tokens(client.client_id, authorization_code.scopes)

    # Tokens.

    def issue_tokens(self, client_id: str, scopes: list[str]) -> OAuthToken:
        claims = {"client_id": client_id, "scopes": scopes}
        return OAuthToken(
            access_token=self.signer.sign("access", claims, ACCESS_TTL),
            token_type="Bearer",
            expires_in=ACCESS_TTL,
            refresh_token=self.signer.sign("refresh", claims, REFRESH_TTL),
            scope=" ".join(scopes) or None,
        )

    async def load_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: str
    ) -> RefreshToken | None:
        data = self.signer.load("refresh", refresh_token)
        if data is None or data["client_id"] != client.client_id:
            return None
        return RefreshToken(
            token=refresh_token,
            client_id=data["client_id"],
            scopes=data["scopes"],
            expires_at=data["exp"],
            resource=self.resource_url,
        )

    async def exchange_refresh_token(
        self, client: OAuthClientInformationFull, refresh_token: RefreshToken, scopes: list[str]
    ) -> OAuthToken:
        return self.issue_tokens(client.client_id, scopes or refresh_token.scopes)

    async def load_access_token(self, token: str) -> AccessToken | None:
        data = self.signer.load("access", token)
        if data is None:
            return None
        return AccessToken(
            token=token,
            client_id=data["client_id"],
            scopes=data["scopes"],
            expires_at=data["exp"],
            resource=self.resource_url,
        )

    async def revoke_token(self, token: AccessToken | RefreshToken) -> None:
        # Stateless tokens cannot be revoked individually; change the password instead.
        return None
