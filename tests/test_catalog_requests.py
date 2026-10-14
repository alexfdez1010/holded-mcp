"""Every catalog operation must fit the transport's supported input envelope.

These contract tests use minimal schema-valid inputs and mocked HTTP. They detect
catalog/transport mismatches, without claiming live account or endpoint validation.
"""

from __future__ import annotations

import json
import re
from typing import Any

import httpx
import pytest

from holded_mcp.catalog import load_operations
from holded_mcp.client import HoldedClient

API_KEY = "holded_catalog_test_key"
OBJECT_ID = "507f1f77bcf86cd799439011"
# Sample values for the string patterns used by the bundled definitions.
PATTERN_SAMPLES = (OBJECT_ID, "1")


def minimal_input(schema: dict[str, Any]) -> Any:
    """Construct minimal inputs for the JSON Schema shapes in this snapshot."""
    if "const" in schema:
        return schema["const"]
    if "enum" in schema:
        return next(value for value in schema["enum"] if value is not None)
    for keyword in ("anyOf", "oneOf"):
        if keyword in schema:
            return minimal_input(schema[keyword][0])
    if "allOf" in schema:
        result = {}
        for child in schema["allOf"]:
            result.update(minimal_input(child))
        return result
    kind = schema.get("type", "object" if "properties" in schema else "string")
    if isinstance(kind, list):
        kind = next(item for item in kind if item != "null")
    if kind == "object":
        return {
            name: minimal_input(schema.get("properties", {}).get(name, {}))
            for name in schema.get("required", [])
        }
    if kind == "array":
        return [minimal_input(schema.get("items", {})) for _ in range(schema.get("minItems", 1))]
    if kind in ("integer", "number"):
        return max(1, schema.get("minimum", 1))
    if kind == "boolean":
        return True
    if kind == "null":
        return None
    if kind == "string":
        if "pattern" in schema:
            for sample in PATTERN_SAMPLES:
                if re.search(schema["pattern"], sample):
                    return sample
            raise AssertionError(f"Add a sample value for pattern {schema['pattern']!r}.")
        return "1"
    raise AssertionError(f"Add explicit test input generation for schema type {kind!r}.")


def binary_field(schema: dict[str, Any]) -> str:
    return next(
        name
        for name, field in schema.get("properties", {}).items()
        if field.get("format") == "binary"
    )


@pytest.mark.parametrize("operation_id", sorted(load_operations()))
async def test_every_catalog_operation_can_be_sent(operation_id):
    operation = load_operations()[operation_id]
    arguments: dict[str, Any] = {}
    for location, argument in (("path", "path_params"), ("query", "query")):
        arguments[argument] = {
            parameter["name"]: minimal_input(parameter.get("schema", {}))
            for parameter in operation["parameters"]
            if parameter["in"] == location
        }
    if operation["content_type"] == "application/json":
        arguments["body"] = minimal_input(operation["body_schema"])
    if operation["content_type"] == "multipart/form-data":
        arguments["files"] = [
            {
                "field": binary_field(operation["body_schema"]),
                "filename": "sample.txt",
                "content_type": "text/plain",
                "content_base64": "aGk=",
            }
        ]
    requests = []
    async with HoldedClient(
        API_KEY,
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(200, json={"ok": True})
        ),
    ) as client:
        result = await client.request(operation, **arguments)
    assert result == {"status": 200, "data": {"ok": True}}
    assert len(requests) == 1
    request = requests[0]
    assert request.method == operation["method"]
    assert request.url.host == "api.holded.com"
    assert "{" not in request.url.path
    if operation["version"] == "v2":
        assert request.url.path.startswith("/api/v2/")
        assert request.headers["authorization"] == f"Bearer {API_KEY}"
        assert "key" not in request.headers
    else:
        assert request.headers["key"] == API_KEY
        assert "authorization" not in request.headers
    if "body" in arguments:
        assert json.loads(request.content) == arguments["body"]
