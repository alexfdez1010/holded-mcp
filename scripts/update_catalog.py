#!/usr/bin/env python3
"""Rebuild the bundled operation catalog from Holded's official OpenAPI definition.

Holded publishes its API as one OpenAPI 3.1 document at
https://api.holded.com/openapi/api2.json. Paths are ``/api/v2/...`` and authentication uses
``Authorization: Bearer <key>``. Every operation has an ``operationId`` and exactly one tag;
``x-tagGroups`` groups the tags into product areas, which become the catalog's ``api``
value. Reference pages live at https://www.holded.com/developers/api-reference.

By default the definition is fetched from that official URL and saved (minified) as
``specs/api2.json`` so that the input of the committed catalog is versioned with it. Pass
``--from-specs`` to rebuild offline from the committed copy, or ``--spec PATH`` to use
another local snapshot. The result is normalized into ``src/holded_mcp/data/operations.json``
and ``docs/api-coverage.md``. ``--verify-docs`` fetches every ``doc_url`` and checks that
the page documents the same method/path.
"""

from __future__ import annotations

import argparse
import copy
import json
import re
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

SOURCE = "https://api.holded.com/openapi/api2.json"
DOC_BASE = "https://www.holded.com/developers/api-reference"
# x-tagGroups name -> catalog api slug. Unknown or missing groups fail the build.
TAG_GROUPS = {
    "Accounting": "accounting",
    "Treasury": "treasury",
    "Sales": "sales",
    "Inventory": "inventory",
    "Contacts": "contacts",
    "CRM": "crm",
    "Projects": "projects",
    "Team & HR": "team",
    "Calendar": "calendar",
    "Inbox": "inbox",
    "Developers": "developers",
}
APIS = tuple(TAG_GROUPS.values())
METHODS = frozenset({"get", "put", "post", "delete", "patch"})
PARAMETER_KEYS = ("name", "in", "description", "required", "schema", "style", "explode")
ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "src/holded_mcp/data/operations.json"
COVERAGE_PATH = ROOT / "docs/api-coverage.md"
SPEC_PATH = ROOT / "specs/api2.json"
USER_AGENT = "holded-mcp-catalog/3.0"


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


def write_spec(spec: dict[str, Any], path: Path) -> None:
    """Store a source definition as minified, key-order-preserving JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(spec, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")


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


def _is_vendor_key(key: str) -> bool:
    # Holded's schemas carry presentation hints for its own assistant (x-ai-*). They are
    # not input constraints; only this generator's own annotations are kept.
    return key.startswith("x-") and not key.startswith("x-holded-")


def normalize_schema(schema: Any) -> Any:
    """Add an implied object type and drop vendor extensions, without modifying examples
    or arbitrary payloads."""
    if not isinstance(schema, dict):
        return schema
    result = {key: copy.deepcopy(value) for key, value in schema.items() if not _is_vendor_key(key)}
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


def _binary_field(schema: Any) -> Any:
    """OpenAPI 3.1 describes raw file parts with ``contentMediaType``; add
    ``format: binary`` so one upload convention applies to every file field."""
    if (
        isinstance(schema, dict)
        and schema.get("type") == "string"
        and "contentMediaType" in schema
        and "contentEncoding" not in schema
        and "format" not in schema
    ):
        return {**schema, "format": "binary"}
    return schema


def normalize_multipart_schema(schema: dict[str, Any]) -> dict[str, Any]:
    properties = schema.get("properties")
    if not isinstance(properties, dict):
        return schema
    normalized = {}
    for name, field in properties.items():
        field = _binary_field(field)
        if isinstance(field, dict) and isinstance(field.get("items"), dict):
            field = {**field, "items": _binary_field(field["items"])}
        normalized[name] = field
    return {**schema, "properties": normalized}


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def doc_url(tag: str, summary: str) -> str:
    """Reference URL: /developers/api-reference/<tag slug>/<summary slug>."""
    return f"{DOC_BASE}/{slugify(tag)}/{slugify(summary)}"


def normalize_parameter(parameter: dict[str, Any]) -> dict[str, Any]:
    result = {key: copy.deepcopy(parameter[key]) for key in PARAMETER_KEYS if key in parameter}
    result.setdefault("description", "")
    if "schema" in result:
        result["schema"] = normalize_schema(result["schema"])
    else:
        result["schema"] = {"type": "string"}
    if "example" in parameter and "example" not in result["schema"]:
        result["schema"]["example"] = copy.deepcopy(parameter["example"])
    if result["in"] == "path":
        result["required"] = True
    return result


def _parameters(
    spec: dict[str, Any],
    path_item: dict[str, Any],
    operation: dict[str, Any],
    endpoint_path: str,
    operation_id: str,
) -> list[dict[str, Any]]:
    """Path then query parameters; operation-level entries override path-level ones."""
    parameters: dict[tuple[str, str], dict[str, Any]] = {}
    for parameter in [*path_item.get("parameters", []), *operation.get("parameters", [])]:
        parameter = resolve_refs(parameter, spec)
        if parameter["in"] == "header" and parameter["name"].casefold() == "authorization":
            continue  # The bearer token is supplied by the client.
        if parameter["in"] not in {"path", "query"}:
            raise ValueError(
                f"Unsupported {parameter['in']} parameter {parameter['name']!r} for "
                f"{operation_id}; the transport only sends path and query parameters."
            )
        parameters[(parameter["name"], parameter["in"])] = normalize_parameter(parameter)
    placeholders = re.findall(r"\{([^}]+)\}", endpoint_path)
    declared = {name for name, location in parameters if location == "path"}
    if set(placeholders) - declared:
        raise ValueError(
            f"Missing path parameters for {operation_id}: {sorted(set(placeholders) - declared)}"
        )
    if declared - set(placeholders):
        raise ValueError(
            f"Undeclared path placeholders for {operation_id}: "
            f"{sorted(declared - set(placeholders))}"
        )
    path_params = sorted(
        (p for p in parameters.values() if p["in"] == "path"),
        key=lambda p: placeholders.index(p["name"]),
    )
    return [*path_params, *(p for p in parameters.values() if p["in"] == "query")]


def _request_body(
    spec: dict[str, Any], operation: dict[str, Any], operation_id: str
) -> tuple[dict[str, Any] | None, bool, str | None]:
    request_body = resolve_refs(operation.get("requestBody", {}), spec)
    content = request_body.get("content", {})
    preferred = ("application/json", "multipart/form-data")
    content_type = next((kind for kind in preferred if kind in content), None)
    if content and content_type is None:
        raise ValueError(f"Unsupported request content for {operation_id}")
    if content_type is None:
        return None, False, None
    body_schema = normalize_schema(content[content_type].get("schema", {}))
    if content_type == "multipart/form-data":
        body_schema = normalize_multipart_schema(body_schema)
    return body_schema, bool(request_body.get("required", False)), content_type


def tag_apis(spec: dict[str, Any]) -> dict[str, str]:
    """Map each tag to the catalog api slug of its ``x-tagGroups`` entry."""
    groups = spec.get("x-tagGroups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("The definition has no x-tagGroups")
    result: dict[str, str] = {}
    for group in groups:
        name = group.get("name")
        if name not in TAG_GROUPS:
            raise ValueError(f"Unknown tag group: {name!r}; update TAG_GROUPS")
        for tag in group.get("tags", []):
            if tag in result:
                raise ValueError(f"Tag {tag!r} belongs to more than one group")
            result[tag] = TAG_GROUPS[name]
    return result


def _scopes(operation: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    security = operation.get("security", spec.get("security")) or []
    scopes: list[str] = []
    for requirement in security:
        for values in requirement.values():
            scopes.extend(value for value in values if value not in scopes)
    return scopes


def build_catalog(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Produce deterministic, reference-free input metadata for every operation."""
    servers = spec.get("servers") or []
    if not servers:
        raise ValueError("OpenAPI servers missing")
    server = urlsplit(servers[0]["url"])
    if server.scheme != "https" or server.hostname != "api.holded.com":
        raise ValueError(f"Unexpected Holded API server: {servers[0]['url']}")
    if server.path.rstrip("/"):
        raise ValueError(f"Unexpected server base path: {server.path}")
    apis = tag_apis(spec)
    operations: dict[str, dict[str, Any]] = {}
    endpoints: set[tuple[str, str]] = set()
    doc_urls: set[str] = set()
    for path, raw_path_item in spec["paths"].items():
        if not path.startswith("/api/v2/"):
            raise ValueError(f"Unexpected API path: {path}")
        path_item = resolve_refs(raw_path_item, spec) if "$ref" in raw_path_item else raw_path_item
        for method, operation in path_item.items():
            if method not in METHODS:
                continue
            method_upper = method.upper()
            operation_id = operation.get("operationId")
            if not isinstance(operation_id, str) or not re.fullmatch(
                r"[a-z][a-z0-9_]*", operation_id
            ):
                raise ValueError(f"Missing or unexpected operationId for {method_upper} {path}")
            tags = operation.get("tags") or []
            if len(tags) != 1:
                raise ValueError(f"{operation_id} must have exactly one tag")
            if tags[0] not in apis:
                raise ValueError(f"{operation_id} tag {tags[0]!r} is not in any x-tagGroups")
            summary = operation.get("summary") or ""
            if not summary:
                raise ValueError(f"Missing summary for {operation_id}")
            endpoint = (method_upper, path)
            if operation_id in operations:
                raise ValueError(f"Duplicate operation ID: {operation_id}")
            if endpoint in endpoints:
                raise ValueError(f"Duplicate endpoint: {endpoint}")
            endpoints.add(endpoint)
            url = doc_url(tags[0], summary)
            if url in doc_urls:
                raise ValueError(f"Duplicate reference URL: {url}")
            doc_urls.add(url)
            parameters = _parameters(spec, path_item, operation, path, operation_id)
            body_schema, body_required, content_type = _request_body(spec, operation, operation_id)
            description = (operation.get("description") or "").strip()
            scopes = _scopes(operation, spec)
            if scopes and not all(f"`{scope}`" in description for scope in scopes):
                note = "Required permission scopes: " + ", ".join(f"`{s}`" for s in scopes) + "."
                description = f"{description}\n\n{note}" if description else note
            operations[operation_id] = {
                "operation_id": operation_id,
                "api": apis[tags[0]],
                "method": method_upper,
                "path": path,
                "summary": summary,
                "description": description,
                "tags": list(tags),
                "parameters": parameters,
                "body_schema": body_schema,
                "body_required": body_required,
                "content_type": content_type,
                "deprecated": bool(operation.get("deprecated", False)),
                "doc_url": url,
            }
    return dict(sorted(operations.items()))


def count_summary(operations: dict[str, dict[str, Any]]) -> str:
    counts = Counter(op["api"] for op in operations.values())
    return ", ".join(f"{counts[api]} {api}" for api in APIS if counts[api])


def coverage_markdown(operations: dict[str, dict[str, Any]], snapshot_date: str) -> str:
    counts = Counter(op["api"] for op in operations.values())
    multipart = sorted(
        op_id for op_id, op in operations.items() if op["content_type"] == "multipart/form-data"
    )
    lines = [
        "# API coverage",
        "",
        f"Official API snapshot: **{snapshot_date}**.",
        "",
        f"The bundled catalog exposes **{len(operations)} operations** from Holded's current "
        "public API (`/api/v2/...`). Holded's legacy v1 API is intentionally not supported.",
        "",
        "| API | Operations |",
        "| --- | ---: |",
    ]
    for api in APIS:
        if counts[api]:
            lines.append(f"| {api} | {counts[api]} |")
    lines += [
        f"| **total** | **{len(operations)}** |",
        "",
        "## Source",
        "",
        f"Holded publishes its API as one OpenAPI 3.1 document: [{SOURCE}]({SOURCE}). A copy "
        "is committed as [`specs/api2.json`](../specs/api2.json) (minified JSON, otherwise "
        "unchanged) so the catalog can be rebuilt offline. Paths are `/api/v2/...` and "
        "requests authenticate with `Authorization: Bearer <api key>`. Each operation "
        "declares the permission scope it needs (for example `sales:invoices.read`); the API "
        f"key must have that scope. The reference is at [{DOC_BASE}]({DOC_BASE}).",
        "",
        "Coverage means every HTTP operation in this definition is callable. Holded plan "
        "limits, permissions, scopes and account features still apply. Response schemas are "
        "not bundled; responses are returned as received. Undocumented endpoints are not "
        "claimed as supported.",
        "",
        "## Normalizations and limitations",
        "",
        "- Operation IDs are the source `operationId` unchanged (for example `list_invoices`).",
        "- `api` is the slug of the operation's `x-tagGroups` group: "
        + ", ".join(
            f"`{slug}` ({name})" if slug != name.lower() else f"`{slug}`"
            for name, slug in TAG_GROUPS.items()
        )
        + ". `tags` keep the single source tag (for example `Invoices`). Paths are full "
        "paths (`/api/v2/...`).",
        "- `doc_url` is `https://www.holded.com/developers/api-reference/<tag>/<summary>` "
        "(both slugified), the URL pattern of Holded's reference pages.",
        "- Local `$ref`s are expanded (siblings retained). Recursive positions, if any "
        "appear in future definitions, are left unconstrained and marked with "
        "`x-holded-recursive-reference`.",
        "- A schema declaring `properties` without `type` is normalized to `type: object`.",
        '- OpenAPI 3.1 type arrays (`["string", "null"]`) and `null` enum members are '
        "kept; validation uses JSON Schema 2020-12.",
        "- Holded's `x-ai-*` extensions (presentation and assistant hints such as "
        "`x-ai-presentation`, `x-ai-hidden`, `x-ai-grounded`, `x-ai-format`) are removed "
        "from parameter and body schemas. They are not input constraints.",
        "- Operation-level parameters override path-level parameters with the same "
        "name and location. Path parameters are always `required: true`. Parameters "
        "without a schema default to `type: string`; parameters without a description "
        "get an empty one. A parameter-level `example` moves into its schema.",
        "- The `Authorization` header is excluded: the client adds it to every request. No "
        "operation declares any other header, cookie or path-level parameter; the generator "
        "fails if one appears, because the transport only sends path and query parameters.",
        "- `body_required` and `required` flags are kept from the source.",
        "- Source descriptions already start with `**Required permission:** <scope>`. "
        "Where they omit any scope from the operation's `security` requirement, the "
        "full list is appended as `Required permission scopes: ...` (for example, "
        "`export_inbox` also needs `accounting:purchases.write`).",
        "- Pagination follows each endpoint's declared parameters; none are added. At "
        "snapshot time, paginated list operations take `limit` and an opaque `cursor` "
        "returned by the previous response (with `has_more`). The document's general "
        "introduction also mentions `page`/`limit`, but no operation declares `page`.",
        "- File uploads use `multipart/form-data` with binary fields as "
        '`{"type": "string", "format": "binary"}`; OpenAPI 3.1 `contentMediaType` file '
        "fields (none at snapshot time) are normalized to the same form. Multipart uploads ("
        + ", ".join(f"`{op_id}`" for op_id in multipart)
        + ") take one binary field (`file`, or `document` for `upload_inbox`).",
        "",
        "## Regenerate",
        "",
        "Fetch the official definition, refresh `specs/api2.json`, and rebuild:",
        "",
        "```sh",
        "uv sync --group dev",
        "uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD",
        "```",
        "",
        "Rebuild offline from the committed copy:",
        "",
        "```sh",
        "uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD --from-specs",
        "```",
        "",
        "Another local snapshot can be passed with `--spec PATH`; it is copied to "
        "`specs/api2.json`. Add `--verify-docs` to fetch every reference page and check that "
        "it documents the same method and path. If Holded adds a tag group, add it to "
        "`TAG_GROUPS` in `scripts/update_catalog.py`. The generator rejects duplicate "
        "operation IDs, duplicate method/path pairs, unresolved references, missing or "
        "extra path parameters, unsupported parameter locations, unexpected servers and "
        "unsupported body content types before writing anything.",
        "",
        "## Operations",
        "",
        "| Operation ID | API | Method | Path | API reference |",
        "| --- | --- | --- | --- | --- |",
    ]
    for operation_id, operation in operations.items():
        summary = operation["summary"].replace("|", "\\|").replace("\n", " ")
        lines.append(
            f"| `{operation_id}` | {operation['api']} | {operation['method']} | "
            f"`{operation['path']}` | [{summary}]({operation['doc_url']}) |"
        )
    lines.append("")
    return "\n".join(lines)


def _check_doc(item: tuple[str, dict[str, Any]]) -> str | None:
    operation_id, operation = item
    request = Request(operation["doc_url"], headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=60) as response:
            page = response.read().decode("utf-8", "replace")
    except OSError as exc:
        return f"{operation_id}: {exc}"
    path = operation["path"]
    if path not in page or operation["method"] not in page:
        return f"{operation_id}: page does not document {operation['method']} {path}"
    return None


def verify_docs(operations: dict[str, dict[str, Any]]) -> list[str]:
    """Return problems found by fetching each reference page (network access required)."""
    with ThreadPoolExecutor(max_workers=8) as pool:
        return [problem for problem in pool.map(_check_doc, operations.items()) if problem]


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--spec", help="Local OpenAPI snapshot, api2.json (else fetch)")
    source.add_argument(
        "--from-specs",
        action="store_true",
        help="Use the committed copy, specs/api2.json, instead of fetching",
    )
    parser.add_argument(
        "--snapshot-date", required=True, help="Source snapshot date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--verify-docs", action="store_true", help="Check every doc_url against its page"
    )
    args = parser.parse_args()
    from datetime import date

    date.fromisoformat(args.snapshot_date)
    spec = read_spec(SPEC_PATH if args.from_specs else args.spec or SOURCE)
    operations = build_catalog(spec)
    if args.verify_docs:
        problems = verify_docs(operations)
        if problems:
            raise SystemExit("Documentation check failed:\n" + "\n".join(problems))
    if not args.from_specs:
        write_spec(spec, SPEC_PATH)
    catalog = json.dumps(operations, ensure_ascii=False, indent=2) + "\n"
    coverage = coverage_markdown(operations, args.snapshot_date)
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(catalog, encoding="utf-8")
    COVERAGE_PATH.write_text(coverage, encoding="utf-8")
    print(f"Wrote {len(operations)} operations: {count_summary(operations)}.")


if __name__ == "__main__":
    main()
