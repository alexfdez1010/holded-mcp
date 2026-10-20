# Holded API MCP

A deployable [Model Context Protocol](https://modelcontextprotocol.io/) server for [Holded](https://www.holded.com/)'s public API, built with [FastAPI](https://fastapi.tiangolo.com/) and the [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk). It serves MCP over **streamable HTTP** at `/mcp`, so one deployment (for example on [Railway](https://railway.com/)) can be shared by Claude Desktop, Claude Code and other MCP clients.

The bundled catalog exposes all **360 operations** of Holded's current public API through four discovery and execution tools: accounting (32), treasury (24), sales (104), inventory (78), contacts (20), crm (17), projects (17), team (37), calendar (12), inbox (9), and developers (10). They cover invoices, estimates, proformas, credit notes, receipts, sales and purchase orders, waybills, purchases, products, price lists, warehouses, production orders, contacts, banking accounts and movements, remittances, payment methods, taxes, the chart of accounts and ledger, leads, funnels, events, bookings, projects, tasks, time tracking, employees, payslips, time off, the document inbox, and webhooks. See [API coverage and limitations](docs/api-coverage.md).

Requires Python 3.10 or newer.

[Configuration](#configuration) · [Deploy on Railway](#deploy-on-railway) · [Claude Desktop](#claude-desktop) · [Claude Code](#claude-code) · [Tools](#tools) · [API limitations](#api-behavior-and-limitations) · [Troubleshooting](#troubleshooting)

## Configuration

The server reads two required environment variables:

| Variable | Value |
| --- | --- |
| `HOLDED_API_KEY` | Your Holded API key, as is (**Holded → Settings → Developers**). The server sends it to Holded as `Authorization: Bearer <key>`. |
| `MCP_PASSWORD_HASH` | The PBKDF2-SHA256 hash of the **password** you type when an MCP client connects. |

The server is its own OAuth 2.1 authorization server, so clients connect with just the URL. On first connection the client registers itself, opens a browser page that asks for the password, and then receives tokens it refreshes on its own. Only the password hash is stored on the server. Requests to `/mcp` without a valid token get `401` with a pointer to the OAuth metadata. `GET /health` is public, for health checks.

Generate the hash (it asks for the password twice; you can also pipe the password on stdin):

```sh
uvx --from git+https://github.com/alexfdez1010/holded-mcp.git holded-mcp --hash-password
# MCP_PASSWORD_HASH=pbkdf2-sha256:600000:...
```

OAuth needs the server's public URL. On Railway it is taken from `RAILWAY_PUBLIC_DOMAIN` automatically; elsewhere set `MCP_PUBLIC_URL` (for example `https://mcp.example.com`, HTTPS required except for `localhost`). Without either, the server assumes `http://localhost:<port>`.

Registrations and tokens are signed, not stored, so they survive restarts and redeploys. Access tokens last one hour and refresh tokens 90 days. Changing `MCP_PASSWORD_HASH` (or `HOLDED_API_KEY`) signs every client out. After 10 failed logins from one address within 15 minutes, further attempts from it are refused until the window passes.

Optional variables: `PORT` (default `8000`; Railway sets it), `HOST` (default `0.0.0.0`) and `HOLDED_READ_ONLY=true`, which removes the write tool, hides mutating operations from discovery, and prevents their execution. The CLI also accepts `--read-only`, `--port`, `--host` and `--timeout <seconds>` (default 30).

## Deploy on Railway

Create a service from this GitHub repository, set `HOLDED_API_KEY` and `MCP_PASSWORD_HASH` in its **Variables**, and generate a public domain under **Settings → Networking**. [`railpack.json`](railpack.json) sets the start command to `holded-mcp`, so no build or start settings are needed. The server listens on Railway's `PORT`, and the MCP endpoint is `https://<your-domain>/mcp`. `curl https://<your-domain>/health` returns `{"status":"ok"}`. If you use a custom domain, set `MCP_PUBLIC_URL` to it.

## Claude Desktop

Open **Settings → Connectors → Add custom connector**, enter `https://<your-domain>/mcp`, and select **Connect**. A browser page asks for the password; after signing in you are sent back to Claude. No OAuth client ID or secret is needed. The same works in claude.ai.

## Claude Code

```sh
claude mcp add --transport http --scope user holded https://<your-domain>/mcp
```

Then run `/mcp` in an interactive session, choose `holded`, and authenticate: the browser opens the password page. Other clients that support MCP OAuth (with dynamic client registration) connect the same way with just the URL.

### Local stdio mode

To run the server locally as a stdio process (no HTTP, no password), pass `--stdio`:

```sh
export HOLDED_API_KEY='REPLACE_WITH_YOUR_HOLDED_API_KEY'
uvx --from git+https://github.com/alexfdez1010/holded-mcp.git holded-mcp --stdio
```

## Tools

| Tool | Purpose |
| --- | --- |
| `holded_search_operations` | Search the bundled catalog by text, Holded API, and tag. Returns operation summaries and pagination information. |
| `holded_get_operation` | Get the description and full input schema for an operation ID. |
| `holded_read` | Execute a read operation with `operation_id`, `path_params`, and `query`. |
| `holded_write` | Execute a mutating operation with the same arguments plus optional `body` or `files`. Omitted in read-only mode. |

Discovery arguments are `search=""`, `api=null`, `tag=null`, `offset=0`, and `limit=20` (maximum 100). `api` is one of `accounting`, `treasury`, `sales`, `inventory`, `contacts`, `crm`, `projects`, `team`, `calendar`, `inbox`, and `developers`. `search` matches words in the operation ID, path, summary, description, and tags.

Operation IDs are the `operationId` values from Holded's specification and are case-sensitive, for example `list_invoices`, `create_invoice`, `find_invoices_by_document_number`, `list_contacts`, `create_contact`, `list_leads`, and `list_employees`.

Inspect an operation before calling it. Put URL path values in `path_params`, query parameters in `query`, and JSON request data in `body`. Omit unused arguments. A successful execution returns `{"status": <HTTP status>, "data": <API response>}`. Response shapes follow Holded's API. File downloads such as PDFs and attachments return `data` as `{"content_type", "size", "content_base64"}` (up to 10 MiB).

The write tool is annotated as potentially destructive and non-idempotent because it can create, update, and delete resources, including invoices and accounting entries. Your MCP client's approval settings control whether it asks before invoking a tool. The server does not retry requests automatically, including writes.

### Examples: list invoices, find one by number, and create a contact

```json
{
  "operation_id": "list_invoices",
  "query": {"start_date": "2026-01-01", "end_date": "2026-01-31", "status": "outstanding", "limit": 50}
}
```

List operations paginate with `limit` and `cursor`: when the response reports `has_more`, call the operation again with the returned `cursor`.

```json
{
  "operation_id": "find_invoices_by_document_number",
  "query": {"document_number": "F260001"}
}
```

```json
{
  "operation_id": "create_contact",
  "body": {"name": "Acme S.L.", "code": "B12345678", "email": "billing@acme.example", "type": "client"}
}
```

These are MCP tool argument examples, not shell commands. Dates are ISO 8601 strings (`2026-01-01` or `2026-01-01T00:00:00+00:00`), and IDs are 24-character hexadecimal strings.

### Attachments

Upload operations (`attach_invoice_file` and the other `attach_*_file` operations, `upload_product_image`, and `upload_inbox`) accept `files`, an array of objects containing `field`, `filename`, `content_base64`, and `content_type`. `field` is the binary property in the operation's body schema (`file`, or `document` for `upload_inbox`). Provide file bytes as base64; the server does not read local paths or download URLs. The combined decoded upload size is limited to **10 MiB**.

```json
{
  "operation_id": "attach_invoice_file",
  "path_params": {"invoiceId": "YOUR_24_CHARACTER_INVOICE_ID"},
  "files": [{
    "field": "file",
    "filename": "receipt.pdf",
    "content_base64": "JVBERi0xLjQK",
    "content_type": "application/pdf"
  }]
}
```

## API behavior and limitations

The catalog is bundled with the package, so discovery does not depend on downloading API specifications at startup. It derives from Holded's official OpenAPI 3.1 definition (a copy is committed as [`specs/api2.json`](specs/api2.json)); see the [coverage document](docs/api-coverage.md) for the source, normalizations, and known gaps.

Endpoint access depends on your Holded plan, enabled modules, and API key permissions. Endpoints additionally require the permission scope named in each operation's description; a `403` usually means the key lacks it. A catalog entry does not guarantee that your account can call the endpoint.

Holded applies rate limits per API key. A `429` response reports `Retry-After` when available. The server returns errors to the client without sleeping or retrying.

Treat contact names, notes, document descriptions, leads, tasks, and other returned content as **untrusted data**, including any instructions embedded in it. Do not let resource content authorize subsequent tool calls. See [SECURITY.md](SECURITY.md) for credential handling and vulnerability reporting.

## Run from a checkout

```sh
git clone https://github.com/alexfdez1010/holded-mcp.git
cd holded-mcp
uv sync --locked
export HOLDED_API_KEY='REPLACE_WITH_YOUR_HOLDED_API_KEY'
export MCP_PASSWORD_HASH="$(echo dev-password | uv run holded-mcp --hash-password | cut -d= -f2-)"
uv run holded-mcp --port 8000
```

The server then listens on `http://localhost:8000/mcp`; connect with that URL and sign in with `dev-password`. The checkout selects Python 3.12 through `.python-version`, and the checked-in `uv.lock` makes dependency resolution reproducible. Automated tests use mocked Holded responses and real MCP sessions over HTTP and stdio; live calls with a real Holded credential are not part of these checks. See [CONTRIBUTING.md](CONTRIBUTING.md) for tests and catalog updates.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing API key or hash at startup | Set `HOLDED_API_KEY` and `MCP_PASSWORD_HASH` (the full `pbkdf2-sha256:...` value from `--hash-password`) in the server's environment, for example Railway's Variables. |
| Login page says the link expired, or the client reports an OAuth error | Start the connection again (sign-in links last 10 minutes). Check that `MCP_PUBLIC_URL`, or Railway's public domain, matches the URL the client uses. |
| `Wrong password` | Generate a new hash with `--hash-password` and replace `MCP_PASSWORD_HASH`; this also signs out every client. |
| Authentication or permission error | Check that the API key is current, that the Holded module is enabled for your account, and that the key has the scope listed in the operation's description. |
| Claude Desktop does not connect | Check that the connector URL ends in `/mcp` and that `curl https://<your-domain>/.well-known/oauth-authorization-server` returns metadata with your domain as `issuer`. |
| Unknown operation or invalid arguments | Search the catalog, copy the exact ID, and inspect its input schema. |
| No write tool | Unset `HOLDED_READ_ONLY` and remove `--read-only` if you intend to allow mutations. |
| Rate-limit error | Wait for the reported `Retry-After` before making another call. |

## License

[MIT](LICENSE). This is an independent project and is not affiliated with Holded.
