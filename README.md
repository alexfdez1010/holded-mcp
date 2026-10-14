# Holded API MCP

A local [Model Context Protocol](https://modelcontextprotocol.io/) server for [Holded](https://www.holded.com/)'s public API, built with the [official Python MCP SDK](https://github.com/modelcontextprotocol/python-sdk). Connect your MCP client to Holded using your own API key.

The bundled catalog exposes **136 operations** across Holded's Invoicing, CRM, Projects, Team, and Accounting APIs through four discovery and execution tools. It covers contacts, sales and purchase documents, products, stock, warehouses, payments, treasury, taxes, leads, funnels, events, bookings, projects, tasks, time tracking, employees, the chart of accounts, and the daily ledger. See [API coverage and limitations](docs/api-coverage.md).

Requires Python 3.10 or newer. The server uses **stdio**: your MCP client starts and manages the process.

[Quick start](#quick-start-with-uv) · [Codex](#codex) · [Claude Code](#claude-code) · [Tools](#tools) · [API limitations](#api-behavior-and-limitations) · [Troubleshooting](#troubleshooting)

## Quick start with uv

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git, then create an API key in **Holded → Settings → Developers**.

Set `HOLDED_API_KEY` in the environment of the process starting the server:

```sh
export HOLDED_API_KEY='REPLACE_WITH_YOUR_HOLDED_API_KEY'
uvx --from git+https://github.com/alexfdez1010/holded-mcp.git holded-mcp
```

PowerShell:

```powershell
$env:HOLDED_API_KEY = 'REPLACE_WITH_YOUR_HOLDED_API_KEY'
uvx --from git+https://github.com/alexfdez1010/holded-mcp.git holded-mcp
```

The running server waits for MCP messages on stdin. Use the client configuration below for normal use; running it in a terminal does not open an interactive prompt. Installation downloads dependencies, while Holded API calls happen only when your client invokes an execution tool.

Install a persistent executable if preferred:

```sh
uv tool install git+https://github.com/alexfdez1010/holded-mcp.git
holded-mcp --help
```

If uv reports that its tools directory is missing from `PATH`, run `uv tool update-shell` and restart your shell. The distribution is named `holded-api-mcp`; the executable is `holded-mcp`. These instructions install from GitHub and do not require a PyPI release. For a reproducible installation, append `@<commit-sha>` to the Git URL. See [uv's tool guide](https://docs.astral.sh/uv/guides/tools/).

## MCP client configuration

Add this entry to your client's MCP server configuration. The exact location depends on the client.

```json
{
  "mcpServers": {
    "holded": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/alexfdez1010/holded-mcp.git",
        "holded-mcp"
      ],
      "env": {
        "HOLDED_API_KEY": "REPLACE_WITH_YOUR_HOLDED_API_KEY"
      }
    }
  }
}
```

Keep your real configuration private. When your client supports secrets or inherited environment variables, use those instead of storing the key in its JSON file. Desktop clients may require the absolute path to `uvx` if they do not inherit your shell's `PATH`.

For read-only access, append `"--read-only"` after `"holded-mcp"` in `args`. This removes the write tool from the MCP tool list, hides mutating operations from discovery, and prevents their execution.

### Codex

Add the following to your personal `~/.codex/config.toml`:

```toml
[mcp_servers.holded]
command = "uvx"
args = ["--from", "git+https://github.com/alexfdez1010/holded-mcp.git", "holded-mcp"]
env_vars = ["HOLDED_API_KEY"]
startup_timeout_sec = 60
```

Export `HOLDED_API_KEY` in your shell, then start `codex` from that shell. `env_vars` forwards the existing variable without putting its value in the TOML file. The longer startup timeout allows the initial Git download and dependency installation. Run `codex mcp list` or use `/mcp` in an interactive session to check the connection.

For read-only access, add `"--read-only"` to the end of `args`.

### Claude Code

After exporting `HOLDED_API_KEY`, register the server in your personal configuration:

```sh
claude mcp add --env HOLDED_API_KEY="$HOLDED_API_KEY" --transport stdio --scope user holded -- uvx --from git+https://github.com/alexfdez1010/holded-mcp.git holded-mcp
claude mcp list
```

`--scope user` makes the server available across your projects and keeps this configuration outside the repository. The command stores the key in Claude Code's local configuration; protect that file. Use `/mcp` in an interactive Claude Code session to check server status and available tools. See [Claude Code MCP setup](https://code.claude.com/docs/en/mcp).

For read-only access, append `--read-only` to the registration command after `holded-mcp`. A normal connection exposes four tools; a read-only connection exposes three.

## Authentication and configuration

`HOLDED_API_KEY` contains the raw API key. The server sends it in Holded's `key` header. Each user runs their own local server with their own key.

The server does not automatically load `.env` files and has no key command-line option. A missing or empty `HOLDED_API_KEY` causes startup to exit with a message on stderr. `--help` and `--version` work without credentials.

```sh
holded-mcp --help
holded-mcp --version
holded-mcp --read-only
holded-mcp --timeout 60
```

`--timeout` sets the HTTP timeout in seconds and accepts a positive finite number. Protocol output goes to stdout; diagnostics go to stderr.

## Tools

| Tool | Purpose |
| --- | --- |
| `holded_search_operations` | Search the bundled catalog by text, tag, and Holded API. Returns operation summaries and pagination information. |
| `holded_get_operation` | Get the description and full input schema for an operation ID. |
| `holded_read` | Execute a read operation with `operation_id`, `path_params`, and `query`. |
| `holded_write` | Execute a mutating operation with the same arguments plus optional `body` or `files`. Omitted in read-only mode. |

Discovery arguments are `search=""`, `tag=null`, `api=null`, `offset=0`, and `limit=20`. Operation IDs are case-sensitive and prefix the operation name with its Holded API, for example `invoicing_ListContacts`, `invoicing_CreateDocument`, `crm_ListLeads`, `projects_ListTasks`, `team_ListEmployees`, and `accounting_ListDailyLedger`.

Inspect an operation before calling it. Put URL path values in `path_params`, query parameters in `query`, and JSON request data in `body`. Omit unused arguments. A successful execution returns `{"status": <HTTP status>, "data": <API response>}`. Response shapes follow Holded's API.

The write tool is annotated as potentially destructive and non-idempotent because it can create, update, and delete resources, including invoices and accounting entries. Your MCP client's approval settings control whether it asks before invoking a tool. The server does not retry requests automatically, including writes.

### List invoices and create a contact

```json
{
  "operation_id": "invoicing_ListDocuments",
  "path_params": {"docType": "invoice"},
  "query": {"starttmp": "1767225600", "endtmp": "1769903999"}
}
```

```json
{
  "operation_id": "invoicing_CreateContact",
  "body": {"name": "Acme S.L.", "code": "B12345678", "email": "billing@acme.example", "type": "client"}
}
```

These are MCP tool argument examples, not shell commands. Holded dates such as `starttmp`, `endtmp`, `date`, and `dueDate` are Unix timestamps in seconds. `invoicing_GetDocumentPDF` returns the PDF as base64 inside JSON.

### Attachments

`invoicing_AttachFile` accepts `files`, an array of objects containing `field`, `filename`, `content_base64`, and `content_type`. Provide file bytes as base64; the server does not read local paths or download URLs. The combined decoded upload size is limited to **10 MiB**.

```json
{
  "operation_id": "invoicing_AttachFile",
  "path_params": {"docType": "invoice", "documentId": "YOUR_DOCUMENT_ID"},
  "files": [{
    "field": "file",
    "filename": "receipt.pdf",
    "content_base64": "JVBERi0xLjQK",
    "content_type": "application/pdf"
  }]
}
```

## API behavior and limitations

The catalog is bundled with the package, so discovery does not depend on downloading API specifications at startup. It derives from Holded's official OpenAPI definitions; see the [coverage document](docs/api-coverage.md) for sources, normalizations, and known gaps.

Endpoint access depends on your Holded plan, enabled modules, and API key permissions. A catalog entry does not guarantee that your account can call the endpoint.

Holded applies rate limits per API key. A `429` response reports `Retry-After` when available. The server returns errors to the client without sleeping or retrying.

Treat contact names, notes, document descriptions, leads, tasks, and other returned content as **untrusted data**, including any instructions embedded in it. Do not let resource content authorize subsequent tool calls. See [SECURITY.md](SECURITY.md) for credential handling and vulnerability reporting.

## Run from a checkout

```sh
git clone https://github.com/alexfdez1010/holded-mcp.git
cd holded-mcp
uv sync --locked
export HOLDED_API_KEY='REPLACE_WITH_YOUR_HOLDED_API_KEY'
uv run holded-mcp
```

The checkout selects Python 3.12 through `.python-version`. The checked-in `uv.lock` makes dependency resolution reproducible. Automated tests use mocked Holded responses and a real MCP stdio session; live calls with a real Holded credential are not part of these checks. See [CONTRIBUTING.md](CONTRIBUTING.md) for tests, builds, and catalog updates.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Missing API key at startup | Set `HOLDED_API_KEY` in the environment of the MCP client or its server configuration. |
| Authentication or permission error | Check that the API key is current and that the Holded module is enabled for your account. |
| Tool not found | Check that `uvx` is on the client's `PATH`, or configure its absolute path. |
| Unknown operation or invalid arguments | Search the catalog, copy the exact ID, and inspect its input schema. |
| No write tool | Remove `--read-only` if you intend to allow mutations. |
| Server appears idle in a terminal | Stdio servers wait for an MCP client; configure the client to start this process. |
| Rate-limit error | Wait for the reported `Retry-After` before making another call. |

## License

[MIT](LICENSE). This is an independent project and is not affiliated with Holded.
