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
| `MCP_API_KEY_HASH` | The SHA-256 hex digest of the **access key** that MCP clients use to call this server. |

Clients authenticate with `Authorization: Bearer <access key>`. The server hashes the presented key and compares it in constant time with `MCP_API_KEY_HASH`, so the access key itself is never stored on the server. Requests without a valid key get `401`. `GET /health` is public, for health checks.

Generate a random access key and its hash:

```sh
uvx --from git+https://github.com/alexfdez1010/holded-mcp.git holded-mcp --generate-key
# MCP access key (give to clients): 3q2-...
# MCP_API_KEY_HASH=9f86d0...
```

To hash an existing key instead, pipe it in: `printf %s "$KEY" | holded-mcp --hash-key` (equivalent to `printf %s "$KEY" | shasum -a 256`).

Optional variables: `PORT` (default `8000`; Railway sets it), `HOST` (default `0.0.0.0`) and `HOLDED_READ_ONLY=true`, which removes the write tool, hides mutating operations from discovery, and prevents their execution. The CLI also accepts `--read-only`, `--port`, `--host` and `--timeout <seconds>` (default 30).

## Deploy on Railway

1. Create a Railway project from this GitHub repository. [`railway.json`](railway.json) builds it with Railpack (it detects `uv.lock`), starts `holded-mcp`, and health-checks `/health`.
2. In the service's **Variables**, set `HOLDED_API_KEY` and `MCP_API_KEY_HASH` (and optionally `HOLDED_READ_ONLY=true`).
3. Under **Settings → Networking**, generate a public domain. The MCP endpoint is `https://<your-domain>/mcp`.

Check the deployment:

```sh
curl https://<your-domain>/health   # {"status":"ok"}
```

Any other host that runs a Python process works the same way: install the package and run `holded-mcp` with the two variables set.

## Claude Desktop

Claude Desktop's custom connectors only support OAuth, so connect through [`mcp-remote`](https://www.npmjs.com/package/mcp-remote), which adds the bearer header. Requires Node.js. Open **Settings → Developer → Edit Config** and add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "holded": {
      "command": "npx",
      "args": [
        "-y",
        "mcp-remote",
        "https://<your-domain>/mcp",
        "--header",
        "Authorization:${AUTH_HEADER}"
      ],
      "env": {
        "AUTH_HEADER": "Bearer REPLACE_WITH_YOUR_ACCESS_KEY"
      }
    }
  }
}
```

Restart Claude Desktop. Keep the header in `env` with no space after `Authorization:`; some platforms split arguments that contain spaces.

## Claude Code

```sh
claude mcp add --transport http --scope user holded https://<your-domain>/mcp \
  --header "Authorization: Bearer $HOLDED_MCP_ACCESS_KEY"
claude mcp list
```

Use `/mcp` in an interactive session to check the connection. Other clients that support streamable HTTP with custom headers connect the same way: URL `https://<your-domain>/mcp`, header `Authorization: Bearer <access key>`.

### Local stdio mode

To run the server locally as a stdio process (no HTTP, no access key), pass `--stdio`:

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
export MCP_API_KEY_HASH="$(printf %s dev-access-key | uv run holded-mcp --hash-key)"
uv run holded-mcp --port 8000
```

The server then listens on `http://localhost:8000/mcp`; connect with `Authorization: Bearer dev-access-key`. The checkout selects Python 3.12 through `.python-version`, and the checked-in `uv.lock` makes dependency resolution reproducible. Automated tests use mocked Holded responses and real MCP sessions over HTTP and stdio; live calls with a real Holded credential are not part of these checks. See [CONTRIBUTING.md](CONTRIBUTING.md) for tests and catalog updates.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing API key or hash at startup | Set `HOLDED_API_KEY` and `MCP_API_KEY_HASH` (64 hex characters) in the server's environment, for example Railway's Variables. |
| `401 Unauthorized` from `/mcp` | Send `Authorization: Bearer <access key>` with the raw access key, not its hash, and check that `MCP_API_KEY_HASH` is the hash of that exact key (no trailing newline: use `printf %s`). |
| Authentication or permission error | Check that the API key is current, that the Holded module is enabled for your account, and that the key has the scope listed in the operation's description. |
| Claude Desktop does not connect | Check that `npx` is on Claude Desktop's `PATH` (or use its absolute path) and that the URL ends in `/mcp`. |
| Unknown operation or invalid arguments | Search the catalog, copy the exact ID, and inspect its input schema. |
| No write tool | Unset `HOLDED_READ_ONLY` and remove `--read-only` if you intend to allow mutations. |
| Rate-limit error | Wait for the reported `Retry-After` before making another call. |

## License

[MIT](LICENSE). This is an independent project and is not affiliated with Holded.
