# Contributing

Contributions are welcome. Keep code, documentation, commit messages, and examples in English. For large changes, open an issue describing the problem and proposed behavior before implementation.

## Development setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) and Git, then:

```sh
git clone https://github.com/alexfdez1010/holded-mcp.git
cd holded-mcp
uv sync --locked
```

The checkout uses Python 3.12. The package supports Python 3.10 and newer; CI checks Python 3.10, 3.12, and 3.14. Commit `uv.lock` whenever an intentional dependency change requires an update.

## Checks

Run the same checks as CI:

```sh
uv run ruff check .
uv run ruff format --check .
uv run pytest
uv build
```

Use `uv run ruff format .` to apply formatting. Tests should use mocked HTTP responses and exercise observable behavior, including failures. Do not require a real Holded API key or make live API calls in automated tests. Never commit credentials, private resource content, or recordings containing them.

When manually running the server, provide `HOLDED_API_KEY` in the environment and use an MCP client. Prefer `--read-only` for exploratory validation. Stdio stdout must contain only MCP protocol traffic; send diagnostics to stderr.

## Update the API catalog

The catalog is generated from Holded's official public API specifications: the v2 OpenAPI 3.1 document (`https://api.holded.com/openapi/api2.json`) and the five v1 definitions in ReadMe's API registry. Copies of these inputs are committed under `specs/` (`specs/v2/api2.json` and `specs/v1/<api>.json`, minified JSON). Fetch the current definitions, refresh `specs/`, and regenerate the catalog and coverage document using:

```sh
uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD
uv run pytest
```

Replace `YYYY-MM-DD` with the date you fetch the source specifications. The generated coverage document records the same snapshot date. To rebuild offline from the committed copies (for example after changing the generator), add `--from-specs`. To use other local snapshots, pass `--v2 PATH` and/or `--invoicing`, `--crm`, `--projects`, `--team`, `--accounting`; they are copied into `specs/`. Add `--verify-docs` to check every `doc_url` against Holded's reference pages (network access required).

`tests/test_catalog.py` rebuilds the catalog from `specs/` and fails if it differs from the packaged `operations.json`, so commit the specs, catalog, and coverage document together.

Review the generated changes before committing. Verify operation counts per version and API, IDs, methods, paths, required parameters, request schemas, multipart handling, and exclusions. Update README counts when coverage changes. If Holded adds a v2 tag group, map it in `V2_TAG_GROUPS`; if it republishes a v1 definition under a new registry id, update `REGISTRY_IDS`. Discovery must continue to work from the bundled catalog without network access at startup.

Holded's published schemas can be incomplete. Document narrowly scoped fixes and their official sources. Do not silently invent fields or claim endpoint support beyond what the transport and schema validation can handle.

## Pull requests

Explain the problem, resulting behavior, and validation in the PR description. Keep unrelated changes separate. Add regression coverage for functional changes where it proves meaningful behavior, and update usage documentation when inputs or installation change.

Check that the wheel contains the bundled catalog and that its `holded-mcp` entry point works. Run `--help` and `--version` without credentials. Authentication must remain environment-based; never introduce API key logging or command-line API key arguments.

Report vulnerabilities through the process in [SECURITY.md](SECURITY.md), without posting secrets publicly.
