#!/usr/bin/env python3
"""Rebuild the bundled operation catalog from Holded's official v1 OpenAPI definitions.

Holded's v1 reference was published with ReadMe at developers.holded.com; each of the
five v1 APIs (Invoicing, CRM, Projects, Team, Accounting) is an OpenAPI 3.0 document in
ReadMe's API registry, addressed by the ``@holded/v1.0#<id>`` identifiers referenced by
the original ReadMe reference pages. The definitions are fetched from the registry (or read
from local snapshots) and normalized into ``src/holded_mcp/data/operations.json``.

The official archive of the v1 reference (https://www.holded.com/developers/v1) is the
documentation target for every ``doc_url``; ``--verify-docs`` checks those links and the
documented method/path of each page against the generated catalog.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

APIS = ("invoicing", "crm", "projects", "team", "accounting")
REGISTRY_IDS = {
    "invoicing": "delc6k4mltcvjvk",
    "crm": "3avojom3x2i4gl",
    "projects": "osa1dlwrwhirf",
    "team": "apza3e5ummfnu54er",
    "accounting": "168v3gl2suxrvj",
}
SOURCES = {
    api: f"https://dash.readme.com/api/v1/api-registry/{registry_id}"
    for api, registry_id in REGISTRY_IDS.items()
}
DOC_BASE = "https://www.holded.com/developers/v1"
DOC_SECTIONS = {
    "invoicing": "invoice-api",
    "crm": "crm-api",
    "projects": "projects-api",
    "team": "team-api",
    "accounting": "accounting-api",
}
METHODS = frozenset({"get", "put", "post", "delete", "patch"})
ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "src/holded_mcp/data/operations.json"
COVERAGE_PATH = ROOT / "docs/api-coverage.md"
USER_AGENT = "holded-mcp-catalog/1.0"

# Every document type listed by the official docType parameter description. The generator
# fails if the source description drifts from this list.
DOC_TYPES = (
    "invoice",
    "salesreceipt",
    "creditnote",
    "salesorder",
    "proform",
    "waybill",
    "estimate",
    "purchase",
    "purchaseorder",
    "purchaserefund",
)
DOC_TYPE_DESCRIPTION = "Document type. One of: " + ", ".join(DOC_TYPES) + "."

# Operation names that cannot be derived cleanly from the source operationId/summary:
# missing identifiers, collisions after PascalCasing, or all-lowercase source names.
# Keys are (api, METHOD, path as written in the source document).
NAME_OVERRIDES = {
    ("accounting", "GET", "/chartofaccounts"): "ListAccounts",
    ("projects", "GET", "/projects/{projectId}/summary"): "GetProjectSummary",
    ("projects", "GET", "/projects/{projectId}/times/{timeTrackingId}"): "GetProjectTime",
    ("team", "GET", "/employees/{employeeId}"): "GetEmployee",
    ("team", "DELETE", "/employees/{employeeId}"): "DeleteEmployee",
    ("team", "GET", "/employees/{employeeId}/times"): "ListEmployeeTimes",
}


def read_spec(source: str | Path) -> dict[str, Any]:
    """Read an OpenAPI JSON (or YAML) document from a local path or a fixed HTTPS URL."""
    if isinstance(source, str) and source.startswith("https://"):
        request = Request(source, headers={"User-Agent": USER_AGENT})
        with urlopen(request, timeout=60) as response:
            raw = response.read().decode("utf-8")
    else:
        raw = Path(source).read_text(encoding="utf-8")
    try:
        spec = json.loads(raw)
    except json.JSONDecodeError:
        import yaml  # Development-only dependency; runtime needs only bundled JSON.

        spec = yaml.safe_load(raw)
    if not isinstance(spec, dict) or not isinstance(spec.get("paths"), dict):
        raise ValueError(f"Invalid OpenAPI document: {source}")
    return spec


def resolve_refs(value: Any, spec: dict[str, Any], stack: tuple[str, ...] = ()) -> Any:
    """Inline local references, preserving siblings and terminating recursive schemas.

    A recursive position becomes an unconstrained schema annotated with the original
    reference. External references deliberately fail so updates cannot silently omit inputs.
    """
    if isinstance(value, list):
        return [resolve_refs(item, spec, stack) for item in value]
    if not isinstance(value, dict):
        return copy.deepcopy(value)
    if "$ref" not in value:
        return {key: resolve_refs(item, spec, stack) for key, item in value.items()}
    reference = value["$ref"]
    if not isinstance(reference, str) or not reference.startswith("#/"):
        raise ValueError(f"Only local OpenAPI references are supported: {reference!r}")
    siblings = {key: item for key, item in value.items() if key != "$ref"}
    if reference in stack:
        resolved = {
            "description": "Recursive schema; nested values follow the same structure.",
            "x-holded-recursive-reference": reference,
        }
    else:
        target: Any = spec
        try:
            for part in reference[2:].split("/"):
                key = part.replace("~1", "/").replace("~0", "~")
                target = target[int(key)] if isinstance(target, list) else target[key]
        except (KeyError, IndexError, ValueError, TypeError) as exc:
            raise ValueError(f"Unresolvable OpenAPI reference: {reference}") from exc
        resolved = resolve_refs(target, spec, (*stack, reference))
        if not isinstance(resolved, dict):
            raise ValueError(f"OpenAPI reference must resolve to an object: {reference}")
    return {**resolved, **resolve_refs(siblings, spec, stack)}


def normalize_schema(schema: Any) -> Any:
    """Add an implied object type without modifying examples or arbitrary payloads."""
    if not isinstance(schema, dict):
        return schema
    result = copy.deepcopy(schema)
    if "properties" in result and "type" not in result:
        result["type"] = "object"
    for keyword in ("properties", "$defs", "definitions", "patternProperties", "dependentSchemas"):
        if isinstance(result.get(keyword), dict):
            result[keyword] = {
                name: normalize_schema(child) for name, child in result[keyword].items()
            }
    for keyword in (
        "items",
        "additionalProperties",
        "not",
        "contains",
        "if",
        "then",
        "else",
        "propertyNames",
    ):
        if isinstance(result.get(keyword), dict):
            result[keyword] = normalize_schema(result[keyword])
        elif isinstance(result.get(keyword), list):
            result[keyword] = [normalize_schema(child) for child in result[keyword]]
    for keyword in ("allOf", "anyOf", "oneOf", "prefixItems"):
        if isinstance(result.get(keyword), list):
            result[keyword] = [normalize_schema(child) for child in result[keyword]]
    return result


def pascal_case(name: str) -> str:
    """``"List Contacts"`` -> ``ListContacts``; ``"getDocument"`` -> ``GetDocument``."""
    words = [word for word in re.split(r"[^A-Za-z0-9]+", name) if word]
    return "".join(word[0].upper() + word[1:] for word in words)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def doc_url(api: str, method: str, path: str, operation: dict[str, Any]) -> str:
    """Archive URL: /developers/v1/<api>-api/<first tag>/<operationId|summary|method path>."""
    tags = operation.get("tags") or []
    if not tags:
        raise ValueError(f"Missing tag for {api} {method} {path}")
    name = operation.get("operationId") or operation.get("summary") or f"{method} {path}"
    return f"{DOC_BASE}/{DOC_SECTIONS[api]}/{slugify(tags[0])}/{slugify(name)}"


def documented_choices(description: str) -> list[str] | None:
    """Parse ``"... should be one of: {a, b,c or d}"`` into ``[a, b, c, d]``."""
    match = re.search(r"should be one of:\s*\{([^}]*)\}", description)
    if not match:
        return None
    values = [v.strip() for v in re.split(r",|\bor\b", match.group(1)) if v.strip()]
    if not all(re.fullmatch(r"[a-z]+", value) for value in values):
        return None
    return values


def normalize_parameter(parameter: dict[str, Any], operation_id: str) -> dict[str, Any]:
    result = copy.deepcopy(parameter)
    result.setdefault("description", "")
    if "schema" in result:
        result["schema"] = normalize_schema(result["schema"])
    else:
        result["schema"] = {"type": "string"}
    if result["in"] == "path":
        result["required"] = True
    description = result.get("description") or ""
    if result["name"] == "docType" and result["in"] == "path":
        choices = documented_choices(description)
        if choices is None:
            if description:
                raise ValueError(f"Unrecognized docType description for {operation_id}")
            choices = list(DOC_TYPES)
            result["description"] = DOC_TYPE_DESCRIPTION
        result["schema"] = {**result["schema"], "enum": choices}
    elif result["in"] == "query" and "Options:" in description:
        choices = re.findall(r"`([^`]+)`", description.split("Options:", 1)[1])
        if choices and result["schema"].get("type") == "string":
            result["schema"] = {**result["schema"], "enum": choices}
    return result


def build_catalog(specs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Produce deterministic, reference-free input metadata for every v1 operation."""
    operations: dict[str, dict[str, Any]] = {}
    endpoints: set[tuple[str, str]] = set()
    for api in sorted(specs):
        if api not in APIS:
            raise ValueError(f"Unknown Holded API: {api}")
        spec = specs[api]
        servers = spec.get("servers") or []
        if not servers:
            raise ValueError(f"OpenAPI servers missing for {api}")
        server = urlsplit(servers[0]["url"])
        base = server.path.rstrip("/")
        if server.scheme != "https" or server.hostname != "api.holded.com":
            raise ValueError(f"Unexpected Holded API server: {servers[0]['url']}")
        if base != f"/api/{api}/v1":
            raise ValueError(f"Unexpected base path for {api}: {base}")
        for path, raw_path_item in spec["paths"].items():
            path_item = (
                resolve_refs(raw_path_item, spec) if "$ref" in raw_path_item else raw_path_item
            )
            for method, operation in path_item.items():
                if method not in METHODS:
                    continue
                method_upper = method.upper()
                source_name = operation.get("operationId") or operation.get("summary")
                name = NAME_OVERRIDES.get((api, method_upper, path)) or pascal_case(
                    source_name or ""
                )
                if not name:
                    raise ValueError(f"Missing operation name for {api} {method_upper} {path}")
                operation_id = f"{api}_{name}"
                endpoint_path = base + "/" + path.lstrip("/")
                endpoint = (method_upper, endpoint_path)
                if operation_id in operations:
                    raise ValueError(f"Duplicate operation ID: {operation_id}")
                if endpoint in endpoints:
                    raise ValueError(f"Duplicate endpoint: {endpoint}")
                endpoints.add(endpoint)
                parameters: dict[tuple[str, str], dict[str, Any]] = {}
                for parameter in [
                    *path_item.get("parameters", []),
                    *operation.get("parameters", []),
                ]:
                    parameter = resolve_refs(parameter, spec)
                    if parameter["in"] not in {"path", "query"}:
                        continue  # The API key header is supplied by the client.
                    parameters[(parameter["name"], parameter["in"])] = normalize_parameter(
                        parameter, operation_id
                    )
                placeholders = set(re.findall(r"\{([^}]+)\}", endpoint_path))
                declared = {name for name, location in parameters if location == "path"}
                if placeholders - declared:
                    raise ValueError(
                        f"Missing path parameters for {operation_id}: "
                        f"{sorted(placeholders - declared)}"
                    )
                if declared - placeholders:
                    raise ValueError(
                        f"Undeclared path placeholders for {operation_id}: "
                        f"{sorted(declared - placeholders)}"
                    )
                # Path parameters first, in placeholder order; query parameters keep the
                # source order.
                order = re.findall(r"\{([^}]+)\}", endpoint_path)
                path_params = sorted(
                    (p for p in parameters.values() if p["in"] == "path"),
                    key=lambda p: order.index(p["name"]),
                )
                query_params = [p for p in parameters.values() if p["in"] == "query"]
                request_body = resolve_refs(operation.get("requestBody", {}), spec)
                content = request_body.get("content", {})
                preferred = ("application/json", "multipart/form-data")
                content_type = next((kind for kind in preferred if kind in content), None)
                if content and content_type is None:
                    raise ValueError(f"Unsupported request content for {operation_id}")
                body_schema = (
                    normalize_schema(content[content_type].get("schema", {}))
                    if content_type
                    else None
                )
                operations[operation_id] = {
                    "operation_id": operation_id,
                    "api": api,
                    "method": method_upper,
                    "path": endpoint_path,
                    "summary": operation.get("summary") or source_name or name,
                    "description": operation.get("description", ""),
                    "tags": operation.get("tags", []),
                    "parameters": [*path_params, *query_params],
                    "body_schema": body_schema,
                    "body_required": bool(request_body.get("required", False)),
                    "content_type": content_type,
                    "deprecated": bool(operation.get("deprecated", False)),
                    "doc_url": doc_url(api, method_upper, path, operation),
                }
    return dict(sorted(operations.items()))


def coverage_markdown(operations: dict[str, dict[str, Any]], snapshot_date: str) -> str:
    counts = Counter(operation["api"] for operation in operations.values())
    summary = ", ".join(f"**{counts[api]} {api}**" for api in APIS)
    lines = [
        "# API coverage",
        "",
        f"Official API snapshot: **{snapshot_date}**.",
        "",
        f"The bundled catalog exposes **{len(operations)} operations** of the Holded v1 API: "
        f"{summary}.",
        "",
        "## Sources",
        "",
        "Holded published the v1 reference with ReadMe (developers.holded.com). Each v1 "
        "API is an OpenAPI 3.0 document in ReadMe's API registry; the original ReadMe "
        "reference pages (Internet Archive captures up to 2026) identify them as "
        "`@holded/v1.0#<id>`:",
        "",
    ]
    for api in APIS:
        lines.append(f"- {api}: [{SOURCES[api]}]({SOURCES[api]})")
    lines += [
        "",
        f"Holded now serves the v1 reference as an archive at [{DOC_BASE}]({DOC_BASE}); "
        "every `doc_url` points there. At snapshot time the archive lists exactly the "
        "same 136 method/path pairs, parameters, body fields, types and required flags "
        "as these definitions (the archive renders only top-level body fields; nested "
        "schemas come from the definitions).",
        "",
        "Holded labels v1 as deprecated/maintenance mode and documents a new v2 API "
        "(`https://api.holded.com/api/v2/...`, Bearer authentication, OpenAPI at "
        "`https://api.holded.com/openapi/api2.json`). v2 is **not** part of this catalog. "
        "Authentication for v1 uses the `key` header, which the client adds; header "
        "parameters are therefore excluded from the catalog.",
        "",
        "Coverage means every HTTP operation in these definitions is callable. Holded "
        "plan limits, permissions and account features still apply. Response schemas "
        "are not bundled; responses are returned as received. Undocumented endpoints "
        "are not claimed as supported.",
        "",
        "## Normalizations and limitations",
        "",
        "- Operation IDs are `<api>_<Name>`, where `Name` is the source `operationId` "
        "(or `summary` when absent) converted to PascalCase (`List Contacts` -> "
        "`ListContacts`, `getDocument` -> `GetDocument`). Explicit overrides: "
        + ", ".join(
            f"`{api}_{name}` ({method} `{path}`)"
            for (api, method, path), name in sorted(NAME_OVERRIDES.items())
        )
        + ". They cover missing identifiers, a collision (`GetProjectTimes` is used "
        "for both the list and the single-entry operation in the source) and "
        "all-lowercase source names.",
        "- Paths are full paths (`/api/<api>/v1/...`) built from each definition's server URL.",
        "- Local `$ref`s are expanded (siblings retained). Recursive positions, if any "
        "appear in future definitions, are left unconstrained and marked with "
        "`x-holded-recursive-reference`.",
        "- A schema declaring `properties` without `type` is normalized to `type: object`.",
        "- Operation-level parameters override path-level parameters with the same "
        "name and location. Path parameters are always `required: true`. "
        "Header parameters are excluded (none are declared besides the `key` "
        "security scheme). Parameters without a schema default to `type: string`; "
        "parameters without a description get an empty one.",
        "- `docType` path parameters carry an `enum`. Where the parameter's description "
        "lists its values (`should be one of: {...}`), that list is used "
        "(e.g. `{salesorder, waybill}` for tracking and pipeline updates, "
        "`{salesorder, order}` for shipped units). Where the source gives no "
        "description, the full list from the documents reference is applied: "
        + ", ".join(f"`{value}`" for value in DOC_TYPES)
        + ".",
        "- Query parameters whose description says `Options:` followed by backticked "
        "values get an `enum` (the documents `sort` parameter: `created-asc`, "
        "`created-desc`). Other value lists that the source describes only in prose "
        "(contact `type`, `taxOperation`, languages, carrier keys) are kept as "
        "descriptions, because the source does not present them as exhaustive.",
        "- File uploads (`invoicing_AttachFile`) use `multipart/form-data` with "
        '`file: {"type": "string", "format": "binary"}` and an optional `setMain` '
        "boolean, as in the source.",
        "- `body_required` and `required` flags are kept from the source. The source marks "
        "no request body as required, even where a body is needed in practice.",
        "- Timestamps (`starttmp`, `endtmp`, `date`, `dueDate`, ...) are Unix timestamps; "
        "the source does not state the unit, but its examples use seconds (10 digits). "
        "The source types some as strings and some as integers, and this catalog keeps "
        "the source types. Exceptions: tracking `pickUpDate`/`deliveryDate` use "
        "`DD/MM/YYYY` strings and the CRM slots `day` uses `yyyy-mm-dd`.",
        '- `invoicing_GetDocumentPDF` returns JSON `{"status": 1, "data": "<base64>"}` '
        "rather than a binary PDF (per the official response example).",
        "- Pagination is only declared where the source declares it: a `page` query "
        "parameter on `accounting_ListDailyLedger`, `team_ListEmployees` and "
        "`team_ListTimes` (pages of up to 500 items). Other list operations declare no "
        "pagination inputs and none are added.",
        "",
        "## Regenerate",
        "",
        "```sh",
        "uv sync --group dev",
        "uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD",
        "```",
        "",
        "For a reproducible offline rebuild, keep the five source documents and pass them:",
        "",
        "```sh",
        "uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD \\",
        "  --invoicing invoicing.json --crm crm.json --projects projects.json \\",
        "  --team team.json --accounting accounting.json",
        "```",
        "",
        "Add `--verify-docs` to fetch every archive page and check that it documents the "
        "same method and path. If Holded republishes a definition under a new registry "
        "id, update `REGISTRY_IDS` in `scripts/update_catalog.py`. The generator rejects "
        "duplicate operation IDs, duplicate method/path pairs, unresolved references, "
        "missing or extra path parameters, unexpected servers and unsupported body "
        "content types before writing anything.",
        "",
        "## Operations",
        "",
        "| Operation ID | Method | Path | API reference |",
        "| --- | --- | --- | --- |",
    ]
    for operation_id, operation in operations.items():
        summary = operation["summary"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{operation_id}` | {operation['method']} | `{operation['path']}` | "
            f"[{summary}]({operation['doc_url']}) |"
        )
    return "\n".join(lines) + "\n"


def verify_docs(operations: dict[str, dict[str, Any]]) -> list[str]:
    """Return problems found by fetching each archive page (network access required)."""
    problems = []
    for operation_id, operation in operations.items():
        request = Request(operation["doc_url"], headers={"User-Agent": USER_AGENT})
        try:
            with urlopen(request, timeout=60) as response:
                page = response.read().decode("utf-8", "replace")
        except OSError as exc:
            problems.append(f"{operation_id}: {exc}")
            continue
        expected = f"https://api.holded.com{operation['path']}"
        if expected not in page or operation["method"] not in page:
            problems.append(f"{operation_id}: page does not document {expected}")
    return problems


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for api in APIS:
        parser.add_argument(f"--{api}", help=f"Local {api} OpenAPI snapshot (else fetch)")
    parser.add_argument(
        "--snapshot-date", required=True, help="Source snapshot date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--verify-docs", action="store_true", help="Check every doc_url against the archive"
    )
    args = parser.parse_args()
    from datetime import date

    date.fromisoformat(args.snapshot_date)
    specs = {api: read_spec(getattr(args, api) or SOURCES[api]) for api in APIS}
    operations = build_catalog(specs)
    if args.verify_docs:
        problems = verify_docs(operations)
        if problems:
            raise SystemExit("Documentation check failed:\n" + "\n".join(problems))
    catalog = json.dumps(operations, ensure_ascii=False, indent=2) + "\n"
    coverage = coverage_markdown(operations, args.snapshot_date)
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(catalog, encoding="utf-8")
    COVERAGE_PATH.write_text(coverage, encoding="utf-8")
    counts = Counter(operation["api"] for operation in operations.values())
    print(
        f"Wrote {len(operations)} operations ("
        + ", ".join(f"{counts[api]} {api}" for api in APIS)
        + ")."
    )


if __name__ == "__main__":
    main()
