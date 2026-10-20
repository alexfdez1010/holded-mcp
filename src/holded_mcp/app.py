"""Deployable FastAPI app serving the MCP server over streamable HTTP at /mcp."""

from __future__ import annotations

import html
import os
import time
from contextlib import asynccontextmanager
from urllib.parse import urlsplit

import anyio
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from mcp.server.auth.settings import AuthSettings, ClientRegistrationOptions

from holded_mcp import __version__
from holded_mcp.auth import PasswordOAuthProvider
from holded_mcp.server import create_server

MCP_PATH = "/mcp"
HEALTH_PATH = "/health"
LOGIN_PATH = "/login"

# Failed logins allowed per client address before it has to wait.
MAX_FAILED_LOGINS = 10
FAILED_LOGIN_WINDOW = 15 * 60

PAGE_HEADERS = {
    "Cache-Control": "no-store",
    # No form-action: browsers apply it to the post-login redirect to the client.
    "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; "
    "frame-ancestors 'none'",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}

LOGIN_PAGE = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Holded MCP · Sign in</title>
<style>
  :root {{ color-scheme: light dark; font-family: system-ui, sans-serif; }}
  body {{ margin: 0; min-height: 100vh; display: grid; place-items: center; padding: 16px;
         background: Canvas; color: CanvasText; }}
  form {{ width: 100%; max-width: 360px; display: grid; gap: 12px; }}
  h1 {{ font-size: 1.25rem; margin: 0; }}
  p {{ margin: 0; opacity: .75; font-size: .9rem; }}
  input, button {{ font: inherit; padding: 10px 12px; border-radius: 8px; }}
  input {{ border: 1px solid GrayText; }}
  button {{ border: 0; background: #2563eb; color: #fff; cursor: pointer; }}
  .error {{ color: #dc2626; opacity: 1; }}
</style>
</head>
<body>
<form method="post" action="{action}">
  <h1>Connect to Holded MCP</h1>
  <p><strong>{client}</strong> is asking for access to your Holded account.
     After signing in you will return to <strong>{target}</strong>.</p>
  {error}
  <input type="hidden" name="request" value="{request}">
  <input type="password" name="password" placeholder="Password" autocomplete="current-password"
         required autofocus aria-label="Password">
  <button type="submit">Sign in</button>
</form>
</body>
</html>
"""


def render_login(request: str, login: dict, error: str = "") -> HTMLResponse:
    target = urlsplit(login["redirect_uri"])
    page = LOGIN_PAGE.format(
        action=LOGIN_PATH,
        client=html.escape(login.get("client_name") or "An MCP client"),
        target=html.escape(target.netloc or target.scheme),
        error=f'<p class="error">{html.escape(error)}</p>' if error else "",
        request=html.escape(request),
    )
    return HTMLResponse(page, status_code=401 if error else 200, headers=PAGE_HEADERS)


def create_app(
    api_key: str,
    password_hash: str,
    public_url: str,
    *,
    read_only: bool = False,
    timeout: float = 30,
    transport: httpx.AsyncBaseTransport | None = None,
) -> FastAPI:
    """Build the app; clients sign in through OAuth with the password behind `password_hash`."""
    issuer_url = public_url.rstrip("/")
    resource_url = issuer_url + MCP_PATH
    provider = PasswordOAuthProvider(
        password_hash,
        secret=api_key,
        issuer_url=issuer_url,
        resource_url=resource_url,
        login_path=LOGIN_PATH,
    )
    auth = AuthSettings(
        issuer_url=issuer_url,
        resource_server_url=resource_url,
        validate_token_resource=True,
        client_registration_options=ClientRegistrationOptions(enabled=True),
    )
    server = create_server(
        api_key,
        read_only=read_only,
        timeout=timeout,
        transport=transport,
        auth=auth,
        auth_server_provider=provider,
    )
    # Stateless JSON responses let the app scale horizontally without sticky sessions.
    # Host checks are disabled because the app sits behind a public hostname and OAuth.
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
    failed_logins: dict[str, list[float]] = {}

    @app.get(HEALTH_PATH, include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get(LOGIN_PATH, include_in_schema=False)
    def login_form(request: str = "") -> Response:
        login = provider.load_login_request(request)
        if login is None:
            return expired_login()
        return render_login(request, login)

    @app.post(LOGIN_PATH, include_in_schema=False)
    async def login_submit(http_request: Request) -> Response:
        form = await http_request.form()
        request = str(form.get("request", ""))
        password = str(form.get("password", ""))
        login = provider.load_login_request(request)
        if login is None:
            return expired_login()
        address = http_request.client.host if http_request.client else ""
        now = time.time()
        recent = [t for t in failed_logins.get(address, []) if t > now - FAILED_LOGIN_WINDOW]
        if len(recent) >= MAX_FAILED_LOGINS:
            return render_login(request, login, "Too many failed attempts. Try again later.")
        if not await anyio.to_thread.run_sync(provider.check_password, password):
            failed_logins[address] = [*recent, now]
            return render_login(request, login, "Wrong password.")
        failed_logins.pop(address, None)
        return RedirectResponse(provider.approve(login), status_code=302, headers=PAGE_HEADERS)

    app.mount("/", mcp_app)
    return app


def expired_login() -> HTMLResponse:
    return HTMLResponse(
        "<!doctype html><title>Holded MCP</title><p>This sign-in link is invalid or has expired. "
        "Start the connection again from your MCP client.</p>",
        status_code=400,
        headers=PAGE_HEADERS,
    )


def public_url_from_env(port: int | str | None = None) -> str:
    """The public base URL: MCP_PUBLIC_URL, Railway's public domain, or localhost."""
    if url := os.environ.get("MCP_PUBLIC_URL", "").strip():
        return url.rstrip("/")
    if domain := os.environ.get("RAILWAY_PUBLIC_DOMAIN", "").strip():
        return f"https://{domain}"
    return f"http://localhost:{port or os.environ.get('PORT', '8000')}"


def app_from_env() -> FastAPI:
    """Factory for `uvicorn --factory holded_mcp.app:app_from_env`."""
    timeout = float(os.environ.get("HOLDED_TIMEOUT", "30"))
    read_only = os.environ.get("HOLDED_READ_ONLY", "").strip().lower() in {"1", "true", "yes"}
    return create_app(
        os.environ.get("HOLDED_API_KEY", ""),
        os.environ.get("MCP_PASSWORD_HASH", ""),
        public_url_from_env(),
        read_only=read_only,
        timeout=timeout,
    )
