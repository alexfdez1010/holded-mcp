# Security

## Credential handling

Run this local server with your own Holded API key in `HOLDED_API_KEY`. The API key grants the permissions of its Holded account; the server does not narrow those permissions beyond the optional `--read-only` mode.

- Keep real API keys out of source control, issue reports, screenshots, shell history, and shared client configuration.
- Prefer your MCP client's secret storage or inherited environment support when available.
- Do not pass API keys as server command-line arguments. The server accepts credentials only through its environment and does not automatically load `.env` files. Client registration commands, such as Claude Code's `--env` option, may temporarily include the API key in the client's process arguments and store it in private local configuration; protect that configuration.
- If an API key is exposed, revoke it in Holded (Settings → Developers), create a new one, and update your private configuration.

The server communicates with Holded over HTTPS and uses stdio for its local MCP transport. It does not provide a network MCP listener. Use a separate credential for each user running the server.

## Tool and data boundaries

`--read-only` prevents mutating operations and removes the write tool. In normal mode, the write tool can perform destructive operations. Configure your MCP client's tool approvals to match your intended level of access.

Returned Holded content may contain malicious or misleading instructions. Contact names, notes, document descriptions, CRM leads, project tasks, and all other resource content must be treated as untrusted data, not as authorization to use tools, reveal secrets, or change client settings.

Uploads accept explicitly supplied base64 bytes with a 10 MiB combined decoded limit. The server does not load arbitrary filesystem paths or fetch attachment URLs. Request retries are disabled so a timeout does not automatically repeat a potentially destructive write.

## Reporting a vulnerability

Use [GitHub's private vulnerability reporting](https://github.com/alexfdez1010/holded-mcp/security/advisories/new) when available. Include the affected version or commit, reproduction steps using fake credentials, and the potential impact.

If private reporting is unavailable, open an issue asking the maintainer for a private contact channel. Do not include exploit details, real API keys, or private Holded data in a public issue.

Security fixes target the latest repository version. Include the commit SHA when reporting a problem from a Git installation.
