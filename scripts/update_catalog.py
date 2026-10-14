#!/usr/bin/env python3
"""Rebuild the bundled operation catalog from Holded's official OpenAPI definitions.

The catalog combines both Holded API generations:

* **v2** (current): one OpenAPI 3.1 document published by Holded at
  https://api.holded.com/openapi/api2.json. Paths are ``/api/v2/...`` and authentication
  uses ``Authorization: Bearer <key>``. Every operation has an ``operationId`` and exactly
  one tag; ``x-tagGroups`` groups the tags into product areas, which become the catalog's
  ``api`` value. Reference pages live at https://www.holded.com/developers/api-reference.
* **v1** (deprecated, maintenance mode): Holded published the v1 reference with ReadMe at
  developers.holded.com; each of the five v1 APIs (Invoicing, CRM, Projects, Team,
  Accounting) is an OpenAPI 3.0 document in ReadMe's API registry, addressed by the
  ``@holded/v1.0#<id>`` identifiers referenced by the original ReadMe reference pages.
  Authentication uses the ``key`` header. The official archive of the v1 reference
  (https://www.holded.com/developers/v1) is the documentation target for every v1
  ``doc_url``.

By default the definitions are fetched from those official URLs and saved (minified) under
``specs/`` so that the inputs of the committed catalog are versioned with it. Pass
``--from-specs`` to rebuild offline from the committed copies, or individual ``--v2`` /
``--<v1 api>`` paths to use other local snapshots. The result is normalized into
``src/holded_mcp/data/operations.json`` and ``docs/api-coverage.md``. ``--verify-docs``
fetches every ``doc_url`` and checks that the page documents the same method/path.
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

VERSIONS = ("v1", "v2")
V1_APIS = ("invoicing", "crm", "projects", "team", "accounting")
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
V2_SOURCE = "https://api.holded.com/openapi/api2.json"
V2_DOC_BASE = "https://www.holded.com/developers/api-reference"
# x-tagGroups name -> catalog api slug. Unknown or missing groups fail the build.
V2_TAG_GROUPS = {
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
V2_APIS = tuple(V2_TAG_GROUPS.values())
APIS = {"v1": V1_APIS, "v2": V2_APIS}
METHODS = frozenset({"get", "put", "post", "delete", "patch"})
PARAMETER_KEYS = ("name", "in", "description", "required", "schema", "style", "explode")
ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "src/holded_mcp/data/operations.json"
COVERAGE_PATH = ROOT / "docs/api-coverage.md"
SPECS_DIR = ROOT / "specs"
USER_AGENT = "holded-mcp-catalog/2.0"

# Every document type listed by the official v1 docType parameter description. The
# generator fails if the source description drifts from this list.
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

# v1 operation names that cannot be derived cleanly from the source operationId/summary:
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


def spec_paths() -> dict[str, Path]:
    """Committed source copies: ``specs/v1/<api>.json`` and ``specs/v2/api2.json``."""
    paths = {api: SPECS_DIR / "v1" / f"{api}.json" for api in V1_APIS}
    paths["v2"] = SPECS_DIR / "v2" / "api2.json"
    return paths


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
    # Holded's v2 schemas carry presentation hints for its own assistant (x-ai-*). They
    # are not input constraints; only this generator's own annotations are kept.
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
    """OpenAPI 3.1 describes raw file parts with ``contentMediaType``; use 3.0's
    ``format: binary`` so one upload convention applies to both versions."""
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


def pascal_case(name: str) -> str:
    """``"List Contacts"`` -> ``ListContacts``; ``"getDocument"`` -> ``GetDocument``."""
    words = [word for word in re.split(r"[^A-Za-z0-9]+", name) if word]
    return "".join(word[0].upper() + word[1:] for word in words)


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def doc_url(api: str, method: str, path: str, operation: dict[str, Any]) -> str:
    """v1 archive URL: /developers/v1/<api>-api/<first tag>/<operationId|summary|method path>."""
    tags = operation.get("tags") or []
    if not tags:
        raise ValueError(f"Missing tag for {api} {method} {path}")
    name = operation.get("operationId") or operation.get("summary") or f"{method} {path}"
    return f"{DOC_BASE}/{DOC_SECTIONS[api]}/{slugify(tags[0])}/{slugify(name)}"


def v2_doc_url(tag: str, summary: str) -> str:
    """v2 reference URL: /developers/api-reference/<tag slug>/<summary slug>."""
    return f"{V2_DOC_BASE}/{slugify(tag)}/{slugify(summary)}"


def documented_choices(description: str) -> list[str] | None:
    """Parse ``"... should be one of: {a, b,c or d}"`` into ``[a, b, c, d]``."""
    match = re.search(r"should be one of:\s*\{([^}]*)\}", description)
    if not match:
        return None
    values = [v.strip() for v in re.split(r",|\bor\b", match.group(1)) if v.strip()]
    if not all(re.fullmatch(r"[a-z]+", value) for value in values):
        return None
    return values


def normalize_parameter(
    parameter: dict[str, Any], operation_id: str, *, v1_enums: bool = True
) -> dict[str, Any]:
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
    if not v1_enums:
        return result
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


def _parameters(
    spec: dict[str, Any],
    path_item: dict[str, Any],
    operation: dict[str, Any],
    endpoint_path: str,
    operation_id: str,
    *,
    v1_enums: bool,
) -> list[dict[str, Any]]:
    """Path then query parameters; operation-level entries override path-level ones."""
    parameters: dict[tuple[str, str], dict[str, Any]] = {}
    for parameter in [*path_item.get("parameters", []), *operation.get("parameters", [])]:
        parameter = resolve_refs(parameter, spec)
        if parameter["in"] == "header" and v1_enums:
            continue  # v1: the `key` header is supplied by the client.
        if parameter["in"] == "header" and parameter["name"].casefold() == "authorization":
            continue  # v2: the bearer token is supplied by the client.
        if parameter["in"] not in {"path", "query"}:
            raise ValueError(
                f"Unsupported {parameter['in']} parameter {parameter['name']!r} for "
                f"{operation_id}; the transport only sends path and query parameters."
            )
        parameters[(parameter["name"], parameter["in"])] = normalize_parameter(
            parameter, operation_id, v1_enums=v1_enums
        )
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


def build_v1_catalog(specs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Produce deterministic, reference-free input metadata for every v1 operation."""
    operations: dict[str, dict[str, Any]] = {}
    endpoints: set[tuple[str, str]] = set()
    for api in sorted(specs):
        if api not in V1_APIS:
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
                operation_id = f"v1_{api}_{name}"
                endpoint_path = base + "/" + path.lstrip("/")
                endpoint = (method_upper, endpoint_path)
                if operation_id in operations:
                    raise ValueError(f"Duplicate operation ID: {operation_id}")
                if endpoint in endpoints:
                    raise ValueError(f"Duplicate endpoint: {endpoint}")
                endpoints.add(endpoint)
                parameters = _parameters(
                    spec, path_item, operation, endpoint_path, operation_id, v1_enums=True
                )
                body_schema, body_required, content_type = _request_body(
                    spec, operation, operation_id
                )
                operations[operation_id] = {
                    "operation_id": operation_id,
                    "version": "v1",
                    "api": api,
                    "method": method_upper,
                    "path": endpoint_path,
                    "summary": operation.get("summary") or source_name or name,
                    "description": operation.get("description", ""),
                    "tags": operation.get("tags", []),
                    "parameters": parameters,
                    "body_schema": body_schema,
                    "body_required": body_required,
                    "content_type": content_type,
                    "deprecated": bool(operation.get("deprecated", False)),
                    "doc_url": doc_url(api, method_upper, path, operation),
                }
    return dict(sorted(operations.items()))


def v2_tag_apis(spec: dict[str, Any]) -> dict[str, str]:
    """Map each v2 tag to the catalog api slug of its ``x-tagGroups`` entry."""
    groups = spec.get("x-tagGroups")
    if not isinstance(groups, list) or not groups:
        raise ValueError("The v2 definition has no x-tagGroups")
    result: dict[str, str] = {}
    for group in groups:
        name = group.get("name")
        if name not in V2_TAG_GROUPS:
            raise ValueError(f"Unknown v2 tag group: {name!r}; update V2_TAG_GROUPS")
        for tag in group.get("tags", []):
            if tag in result:
                raise ValueError(f"v2 tag {tag!r} belongs to more than one group")
            result[tag] = V2_TAG_GROUPS[name]
    return result


def _scopes(operation: dict[str, Any], spec: dict[str, Any]) -> list[str]:
    security = operation.get("security", spec.get("security")) or []
    scopes: list[str] = []
    for requirement in security:
        for values in requirement.values():
            scopes.extend(value for value in values if value not in scopes)
    return scopes


def build_v2_catalog(spec: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Produce deterministic, reference-free input metadata for every v2 operation."""
    servers = spec.get("servers") or []
    if not servers:
        raise ValueError("OpenAPI servers missing for v2")
    server = urlsplit(servers[0]["url"])
    if server.scheme != "https" or server.hostname != "api.holded.com":
        raise ValueError(f"Unexpected Holded API server: {servers[0]['url']}")
    if server.path.rstrip("/"):
        raise ValueError(f"Unexpected v2 server base path: {server.path}")
    tag_apis = v2_tag_apis(spec)
    operations: dict[str, dict[str, Any]] = {}
    endpoints: set[tuple[str, str]] = set()
    doc_urls: set[str] = set()
    for path, raw_path_item in spec["paths"].items():
        if not path.startswith("/api/v2/"):
            raise ValueError(f"Unexpected v2 path: {path}")
        path_item = resolve_refs(raw_path_item, spec) if "$ref" in raw_path_item else raw_path_item
        for method, operation in path_item.items():
            if method not in METHODS:
                continue
            method_upper = method.upper()
            source_id = operation.get("operationId")
            if not isinstance(source_id, str) or not re.fullmatch(r"[a-z][a-z0-9_]*", source_id):
                raise ValueError(f"Missing or unexpected operationId for {method_upper} {path}")
            operation_id = f"v2_{source_id}"
            tags = operation.get("tags") or []
            if len(tags) != 1:
                raise ValueError(f"{operation_id} must have exactly one tag")
            if tags[0] not in tag_apis:
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
            url = v2_doc_url(tags[0], summary)
            if url in doc_urls:
                raise ValueError(f"Duplicate v2 reference URL: {url}")
            doc_urls.add(url)
            parameters = _parameters(spec, path_item, operation, path, operation_id, v1_enums=False)
            body_schema, body_required, content_type = _request_body(spec, operation, operation_id)
            description = (operation.get("description") or "").strip()
            scopes = _scopes(operation, spec)
            if scopes and not all(f"`{scope}`" in description for scope in scopes):
                note = "Required permission scopes: " + ", ".join(f"`{s}`" for s in scopes) + "."
                description = f"{description}\n\n{note}" if description else note
            operations[operation_id] = {
                "operation_id": operation_id,
                "version": "v2",
                "api": tag_apis[tags[0]],
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


def build_catalog(
    v1_specs: dict[str, dict[str, Any]], v2_spec: dict[str, Any] | None
) -> dict[str, dict[str, Any]]:
    """Merge both API generations into one catalog keyed by operation ID."""
    operations = build_v1_catalog(v1_specs)
    if v2_spec is not None:
        operations.update(build_v2_catalog(v2_spec))
    endpoints = Counter((op["method"], op["path"]) for op in operations.values())
    duplicates = [endpoint for endpoint, count in endpoints.items() if count > 1]
    if duplicates:
        raise ValueError(f"Duplicate endpoints across versions: {duplicates}")
    return dict(sorted(operations.items()))


def _counts(operations: dict[str, dict[str, Any]]) -> Counter[tuple[str, str]]:
    return Counter((op["version"], op["api"]) for op in operations.values())


def count_summary(operations: dict[str, dict[str, Any]]) -> str:
    counts = _counts(operations)
    parts = []
    for version in VERSIONS:
        total = sum(count for (v, _), count in counts.items() if v == version)
        details = ", ".join(
            f"{counts[(version, api)]} {api}" for api in APIS[version] if counts[(version, api)]
        )
        parts.append(f"{total} {version} ({details})")
    return "; ".join(parts)


def coverage_markdown(operations: dict[str, dict[str, Any]], snapshot_date: str) -> str:
    counts = _counts(operations)
    totals = Counter(op["version"] for op in operations.values())
    multipart = sorted(
        op_id
        for op_id, op in operations.items()
        if op["content_type"] == "multipart/form-data" and op["version"] == "v2"
    )
    lines = [
        "# API coverage",
        "",
        f"Official API snapshot: **{snapshot_date}**.",
        "",
        f"The bundled catalog exposes **{len(operations)} operations**: "
        f"**{totals['v2']}** from the current Holded **v2** API and **{totals['v1']}** from "
        "the deprecated **v1** API. Both use the same API key (`HOLDED_API_KEY`).",
        "",
        "| Version | API | Operations |",
        "| --- | --- | ---: |",
    ]
    for version in reversed(VERSIONS):
        for api in APIS[version]:
            if counts[(version, api)]:
                lines.append(f"| {version} | {api} | {counts[(version, api)]} |")
        lines.append(f"| **{version}** | **total** | **{totals[version]}** |")
    lines += [
        "",
        "## Sources",
        "",
        "Copies of every source definition are committed under [`specs/`](../specs) "
        "(minified JSON, otherwise unchanged) so the catalog can be rebuilt offline.",
        "",
        "### v2 (current)",
        "",
        f"Holded publishes v2 as one OpenAPI 3.1 document: [{V2_SOURCE}]({V2_SOURCE}) "
        "(`specs/v2/api2.json`). Paths are `/api/v2/...` and requests authenticate with "
        "`Authorization: Bearer <api key>`. Each operation declares the permission scope "
        "it needs (for example `sales:invoices.read`); the API key must have that scope. "
        f"The reference is at [{V2_DOC_BASE}]({V2_DOC_BASE}).",
        "",
        "### v1 (deprecated)",
        "",
        "Holded labels v1 as deprecated/maintenance mode; it still works with the same key, "
        "sent in the `key` header. Holded published the v1 reference with ReadMe "
        "(developers.holded.com). Each v1 API is an OpenAPI 3.0 document in ReadMe's API "
        "registry; the original ReadMe reference pages (Internet Archive captures up to "
        "2026) identify them as `@holded/v1.0#<id>` (`specs/v1/<api>.json`):",
        "",
    ]
    for api in V1_APIS:
        lines.append(f"- {api}: [{SOURCES[api]}]({SOURCES[api]})")
    lines += [
        "",
        f"Holded now serves the v1 reference as an archive at [{DOC_BASE}]({DOC_BASE}); "
        "every v1 `doc_url` points there. At the first snapshot (2026-10-14) the archive "
        "listed exactly the same 136 method/path pairs, parameters, body fields, types "
        "and required flags as these definitions (the archive renders only top-level body "
        "fields; nested schemas come from the definitions).",
        "",
        "Coverage means every HTTP operation in these definitions is callable. Holded "
        "plan limits, permissions, scopes and account features still apply. Response "
        "schemas are not bundled; responses are returned as received. Undocumented "
        "endpoints are not claimed as supported.",
        "",
        "## Normalizations and limitations",
        "",
        "### Both versions",
        "",
        "- Every operation records its `version` (`v1` or `v2`) and `api`. Paths are full "
        "paths (`/api/v2/...` or `/api/<api>/v1/...`).",
        "- Local `$ref`s are expanded (siblings retained). Recursive positions, if any "
        "appear in future definitions, are left unconstrained and marked with "
        "`x-holded-recursive-reference`.",
        "- A schema declaring `properties` without `type` is normalized to `type: object`.",
        "- Operation-level parameters override path-level parameters with the same "
        "name and location. Path parameters are always `required: true`. Parameters "
        "without a schema default to `type: string`; parameters without a description "
        "get an empty one. A parameter-level `example` moves into its schema.",
        "- Authentication headers are excluded: the client adds `key` (v1) or "
        "`Authorization: Bearer` (v2) per request, never both. No v2 operation declares "
        "any other header, cookie or path-level parameter; the generator fails if one "
        "appears, because the transport only sends path and query parameters.",
        "- `body_required` and `required` flags are kept from the source.",
        "- File uploads use `multipart/form-data` with binary fields as "
        '`{"type": "string", "format": "binary"}`. OpenAPI 3.1 `contentMediaType` file '
        "fields (none at snapshot time) are normalized to the same form.",
        "",
        "### v2",
        "",
        "- Operation IDs are `v2_<operationId>` with the source `operationId` unchanged "
        "(for example `v2_list_invoices`).",
        "- `api` is the slug of the operation's `x-tagGroups` group: "
        + ", ".join(
            f"`{slug}` ({name})" if slug != name.lower() else f"`{slug}`"
            for name, slug in V2_TAG_GROUPS.items()
        )
        + ". `tags` keep the single source tag (for example `Invoices`).",
        "- `doc_url` is `https://www.holded.com/developers/api-reference/<tag>/<summary>` "
        "(both slugified), the URL pattern of Holded's reference pages.",
        '- OpenAPI 3.1 type arrays (`["string", "null"]`) and `null` enum members are '
        "kept; validation uses JSON Schema 2020-12.",
        "- Holded's `x-ai-*` extensions (presentation and assistant hints such as "
        "`x-ai-presentation`, `x-ai-hidden`, `x-ai-grounded`, `x-ai-format`) are removed "
        "from parameter and body schemas. They are not input constraints.",
        "- Source descriptions already start with `**Required permission:** <scope>`. "
        "Where they omit any scope from the operation's `security` requirement, the "
        "full list is appended as `Required permission scopes: ...` (for example, "
        "`v2_export_inbox` also needs `accounting:purchases.write`).",
        "- Pagination follows each endpoint's declared parameters; none are added. At "
        "snapshot time, paginated list operations take `limit` and an opaque `cursor` "
        "returned by the previous response (with `has_more`). The document's general "
        "introduction also mentions `page`/`limit`, but no operation declares `page`.",
        "- Multipart uploads ("
        + ", ".join(f"`{op_id}`" for op_id in multipart)
        + ") take one binary field (`file`, or `document` for `v2_upload_inbox`).",
        "",
        "### v1",
        "",
        "- Operation IDs are `v1_<api>_<Name>`, where `Name` is the source `operationId` "
        "(or `summary` when absent) converted to PascalCase (`List Contacts` -> "
        "`ListContacts`, `getDocument` -> `GetDocument`). Explicit overrides: "
        + ", ".join(
            f"`v1_{api}_{name}` ({method} `{path}`)"
            for (api, method, path), name in sorted(NAME_OVERRIDES.items())
        )
        + ". They cover missing identifiers, a collision (`GetProjectTimes` is used "
        "for both the list and the single-entry operation in the source) and "
        "all-lowercase source names.",
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
        "- `v1_invoicing_AttachFile` uses `multipart/form-data` with `file` (binary) and "
        "an optional `setMain` boolean, as in the source.",
        "- The v1 source marks no request body as required, even where a body is needed "
        "in practice.",
        "- Timestamps (`starttmp`, `endtmp`, `date`, `dueDate`, ...) are Unix timestamps; "
        "the source does not state the unit, but its examples use seconds (10 digits). "
        "The source types some as strings and some as integers, and this catalog keeps "
        "the source types. Exceptions: tracking `pickUpDate`/`deliveryDate` use "
        "`DD/MM/YYYY` strings and the CRM slots `day` uses `yyyy-mm-dd`.",
        '- `v1_invoicing_GetDocumentPDF` returns JSON `{"status": 1, "data": "<base64>"}` '
        "rather than a binary PDF (per the official response example).",
        "- Pagination is only declared where the source declares it: a `page` query "
        "parameter on `v1_accounting_ListDailyLedger`, `v1_team_ListEmployees` and "
        "`v1_team_ListTimes` (pages of up to 500 items).",
        "",
        "## Regenerate",
        "",
        "Fetch the official definitions, refresh `specs/`, and rebuild:",
        "",
        "```sh",
        "uv sync --group dev",
        "uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD",
        "```",
        "",
        "Rebuild offline from the committed copies under `specs/`:",
        "",
        "```sh",
        "uv run python scripts/update_catalog.py --snapshot-date YYYY-MM-DD --from-specs",
        "```",
        "",
        "Individual local snapshots can also be passed with `--v2 api2.json` and "
        "`--invoicing`, `--crm`, `--projects`, `--team`, `--accounting`; they are copied "
        "into `specs/`. Add `--verify-docs` to fetch every reference page and check that "
        "it documents the same method and path. If Holded republishes a v1 definition "
        "under a new registry id, update `REGISTRY_IDS`; if it adds a v2 tag group, add "
        "it to `V2_TAG_GROUPS` in `scripts/update_catalog.py`. The generator rejects "
        "duplicate operation IDs, duplicate method/path pairs, unresolved references, "
        "missing or extra path parameters, unsupported parameter locations, unexpected "
        "servers and unsupported body content types before writing anything.",
        "",
        "## Operations",
        "",
    ]
    for version in reversed(VERSIONS):
        lines += [
            f"### {version}",
            "",
            "| Operation ID | API | Method | Path | API reference |",
            "| --- | --- | --- | --- | --- |",
        ]
        for operation_id, operation in operations.items():
            if operation["version"] != version:
                continue
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
    # v1 archive pages show the full URL; v2 reference pages show the templated path.
    expected = f"https://api.holded.com{path}" if operation["version"] == "v1" else path
    if expected not in page or operation["method"] not in page:
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
    for api in V1_APIS:
        parser.add_argument(f"--{api}", help=f"Local v1 {api} OpenAPI snapshot (else fetch)")
    parser.add_argument("--v2", help="Local v2 OpenAPI snapshot, api2.json (else fetch)")
    parser.add_argument(
        "--from-specs",
        action="store_true",
        help="Use the committed copies under specs/ instead of fetching",
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
    committed = spec_paths()
    sources: dict[str, str | Path] = {}
    for key in (*V1_APIS, "v2"):
        local = getattr(args, key)
        if local and args.from_specs:
            parser.error(f"--{key} cannot be combined with --from-specs")
        if args.from_specs:
            sources[key] = committed[key]
        else:
            sources[key] = local or (V2_SOURCE if key == "v2" else SOURCES[key])
    specs = {key: read_spec(source) for key, source in sources.items()}
    operations = build_catalog({api: specs[api] for api in V1_APIS}, specs["v2"])
    if args.verify_docs:
        problems = verify_docs(operations)
        if problems:
            raise SystemExit("Documentation check failed:\n" + "\n".join(problems))
    if not args.from_specs:
        for key, spec in specs.items():
            write_spec(spec, committed[key])
    catalog = json.dumps(operations, ensure_ascii=False, indent=2) + "\n"
    coverage = coverage_markdown(operations, args.snapshot_date)
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    COVERAGE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CATALOG_PATH.write_text(catalog, encoding="utf-8")
    COVERAGE_PATH.write_text(coverage, encoding="utf-8")
    print(f"Wrote {len(operations)} operations: {count_summary(operations)}.")


if __name__ == "__main__":
    main()
