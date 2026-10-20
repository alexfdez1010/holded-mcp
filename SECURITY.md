# Security

## Credential handling

The server uses two secrets, both supplied only through its environment:

- `HOLDED_API_KEY`, the Holded API key. It grants the permissions of its Holded account; the server does not narrow them beyond the optional read-only mode. Endpoints also check the key's permission scopes, so grant only the scopes you need. The server sends the key only to `https://api.holded.com`, as `Authorization: Bearer <key>`.
- `MCP_PASSWORD_HASH`, a salted PBKDF2-SHA256 hash (600,000 iterations) of the password typed on the OAuth login page. The server never stores the password and compares hashes in constant time. Use a long, unique password.

The server acts as its own OAuth 2.1 authorization server (dynamic client registration, authorization code with PKCE S256, refresh tokens). Client registrations, authorization codes and tokens are HMAC-SHA256-signed payloads whose key is derived from both secrets above; nothing is stored. Access tokens expire after one hour, refresh tokens after 90 days, and tokens are bound to this server's `/mcp` resource. Individual tokens cannot be revoked: changing the password invalidates all of them. Failed logins are limited to 10 per client address per 15 minutes.

Anyone who knows the password, or holds a token, can use the Holded API key's permissions through this server, so treat both like the Holded key itself.

- Serve the HTTP endpoint over HTTPS only (Railway's public domains terminate TLS).
- Keep real keys out of source control, issue reports, screenshots, shell history, and shared client configuration. Prefer your host's secret variables and your client's secret storage.
- The server does not automatically load `.env` files and has no key or password command-line option.
- If the password or a token is exposed, choose a new password and replace `MCP_PASSWORD_HASH`. If the Holded key is exposed, revoke it in Holded (Settings → Developers), create a new one, and update `HOLDED_API_KEY`.

## Tool and data boundaries

`--read-only` prevents mutating operations and removes the write tool. In normal mode, the write tool can perform destructive operations. Configure your MCP client's tool approvals to match your intended level of access.

Returned Holded content may contain malicious or misleading instructions. Contact names, notes, document descriptions, CRM leads, project tasks, and all other resource content must be treated as untrusted data, not as authorization to use tools, reveal secrets, or change client settings.

Uploads accept explicitly supplied base64 bytes with a 10 MiB combined decoded limit. File downloads are returned as base64 and limited to 10 MiB. The server does not load arbitrary filesystem paths or fetch attachment URLs. Request retries are disabled so a timeout does not automatically repeat a potentially destructive write.

## Reporting a vulnerability

Use [GitHub's private vulnerability reporting](https://github.com/alexfdez1010/holded-mcp/security/advisories/new) when available. Include the affected version or commit, reproduction steps using fake credentials, and the potential impact.

If private reporting is unavailable, open an issue asking the maintainer for a private contact channel. Do not include exploit details, real API keys, or private Holded data in a public issue.

Security fixes target the latest repository version. Include the commit SHA when reporting a problem from a Git installation.
