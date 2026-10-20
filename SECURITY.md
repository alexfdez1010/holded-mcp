# Security

## Credential handling

The server uses two secrets, both supplied only through its environment:

- `HOLDED_API_KEY`, the Holded API key. It grants the permissions of its Holded account; the server does not narrow them beyond the optional read-only mode. Endpoints also check the key's permission scopes, so grant only the scopes you need. The server sends the key only to `https://api.holded.com`, as `Authorization: Bearer <key>`.
- `MCP_API_KEY_HASH`, the SHA-256 digest of the access key that MCP clients present as `Authorization: Bearer <access key>`. The server stores only the hash and compares digests in constant time. Use a long random access key (`holded-mcp --generate-key` produces 256 bits); an unsalted hash is only safe for high-entropy keys, not for passwords.

Anyone holding the access key can use the Holded API key's permissions through this server, so treat the access key like the Holded key itself.

- Serve the HTTP endpoint over HTTPS only (Railway's public domains terminate TLS).
- Keep real keys out of source control, issue reports, screenshots, shell history, and shared client configuration. Prefer your host's secret variables and your client's secret storage.
- The server does not automatically load `.env` files and has no key command-line option.
- If the access key is exposed, generate a new one and replace `MCP_API_KEY_HASH`. If the Holded key is exposed, revoke it in Holded (Settings → Developers), create a new one, and update `HOLDED_API_KEY`.

## Tool and data boundaries

`--read-only` prevents mutating operations and removes the write tool. In normal mode, the write tool can perform destructive operations. Configure your MCP client's tool approvals to match your intended level of access.

Returned Holded content may contain malicious or misleading instructions. Contact names, notes, document descriptions, CRM leads, project tasks, and all other resource content must be treated as untrusted data, not as authorization to use tools, reveal secrets, or change client settings.

Uploads accept explicitly supplied base64 bytes with a 10 MiB combined decoded limit. File downloads are returned as base64 and limited to 10 MiB. The server does not load arbitrary filesystem paths or fetch attachment URLs. Request retries are disabled so a timeout does not automatically repeat a potentially destructive write.

## Reporting a vulnerability

Use [GitHub's private vulnerability reporting](https://github.com/alexfdez1010/holded-mcp/security/advisories/new) when available. Include the affected version or commit, reproduction steps using fake credentials, and the potential impact.

If private reporting is unavailable, open an issue asking the maintainer for a private contact channel. Do not include exploit details, real API keys, or private Holded data in a public issue.

Security fixes target the latest repository version. Include the commit SHA when reporting a problem from a Git installation.
