"""Regression checks for the packaged official Holded API catalog and its generator."""

from __future__ import annotations

import importlib.util
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from jsonschema import Draft202012Validator

from holded_mcp.catalog import load_operations

GENERATOR_PATH = Path(__file__).resolve().parents[1] / "scripts" / "update_catalog.py"
SPEC = importlib.util.spec_from_file_location("update_catalog", GENERATOR_PATH)
assert SPEC is not None and SPEC.loader is not None
GENERATOR = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(GENERATOR)

APIS = {
    "accounting",
    "treasury",
    "sales",
    "inventory",
    "contacts",
    "crm",
    "projects",
    "team",
    "calendar",
    "inbox",
    "developers",
}
PATH_RE = re.compile(r"/api/v2/[A-Za-z0-9_{}./-]+")
ID_RE = re.compile(r"[a-z][a-z0-9_]*")
OPERATION_KEYS = {
    "operation_id",
    "api",
    "method",
    "path",
    "summary",
    "description",
    "tags",
    "parameters",
    "body_schema",
    "body_required",
    "content_type",
    "deprecated",
    "doc_url",
}


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def test_snapshot_covers_all_documented_operations():
    operations = load_operations()
    assert len(operations) == 360
    assert Counter(op["api"] for op in operations.values()) == {
        "accounting": 32,
        "treasury": 24,
        "sales": 104,
        "inventory": 78,
        "contacts": 20,
        "crm": 17,
        "projects": 17,
        "team": 37,
        "calendar": 12,
        "inbox": 9,
        "developers": 10,
    }
    for operation_id in (
        "list_invoices",
        "create_invoice",
        "find_invoices_by_document_number",
        "list_contacts",
        "upload_inbox",
        "list_leads",
        "list_employees",
    ):
        assert operation_id in operations
    assert len({(op["method"], op["path"]) for op in operations.values()}) == 360
    assert len({op["doc_url"] for op in operations.values()}) == 360


def test_committed_spec_rebuilds_the_packaged_catalog():
    rebuilt = GENERATOR.build_catalog(GENERATOR.read_spec(GENERATOR.SPEC_PATH))
    assert rebuilt == load_operations()
    assert GENERATOR.SPEC_PATH.stat().st_size < 5 * 1024 * 1024


def test_operation_structure_invariants():
    operations = load_operations()
    for operation_id, operation in operations.items():
        assert set(operation) == OPERATION_KEYS
        assert operation["operation_id"] == operation_id
        assert ID_RE.fullmatch(operation_id), operation_id
        assert operation["api"] in APIS
        assert operation["method"] in {"GET", "POST", "PUT", "DELETE", "PATCH"}
        assert PATH_RE.fullmatch(operation["path"]), operation["path"]
        assert len(operation["tags"]) == 1
        assert operation["doc_url"].startswith("https://www.holded.com/developers/api-reference/")
        assert "Required permission" in operation["description"]
        assert isinstance(operation["summary"], str) and operation["summary"]
        assert all(isinstance(tag, str) for tag in operation["tags"])
        assert isinstance(operation["body_required"], bool)
        assert isinstance(operation["deprecated"], bool)
        assert all("$ref" not in item for item in walk(operation))
        assert not any(
            key.startswith("x-ai") for item in walk(operation["parameters"]) for key in item
        )
        assert not any(
            key.startswith("x-ai") for item in walk(operation["body_schema"]) for key in item
        )
        if operation["body_schema"] is None:
            assert operation["content_type"] is None
            assert operation["body_required"] is False
        else:
            assert operation["content_type"] in {"application/json", "multipart/form-data"}
            Draft202012Validator.check_schema(operation["body_schema"])


def test_parameters_match_path_placeholders():
    for operation_id, operation in load_operations().items():
        names = [(p["name"], p["in"]) for p in operation["parameters"]]
        assert len(names) == len(set(names)), operation_id
        placeholders = re.findall(r"\{([^}]+)\}", operation["path"])
        path_params = [p for p in operation["parameters"] if p["in"] == "path"]
        assert [p["name"] for p in path_params] == placeholders, operation_id
        for parameter in operation["parameters"]:
            assert parameter["in"] in {"path", "query"}
            assert parameter["name"].casefold() != "authorization"
            assert isinstance(parameter["description"], str)
            assert set(parameter) <= {
                "name",
                "in",
                "description",
                "required",
                "schema",
                "style",
                "explode",
            }
            Draft202012Validator.check_schema(parameter["schema"])
            if parameter["in"] == "path":
                assert parameter["required"] is True


def test_offline_load_returns_independent_mutable_mappings():
    first = load_operations()
    first["create_invoice"]["body_schema"]["properties"].clear()
    assert load_operations()["create_invoice"]["body_schema"]["properties"]


def test_multipart_upload_metadata():
    operations = load_operations()
    multipart = {
        op_id for op_id, op in operations.items() if op["content_type"] == "multipart/form-data"
    }
    assert {"attach_invoice_file", "upload_product_image", "upload_inbox"} <= multipart
    attach = operations["attach_invoice_file"]
    assert attach["method"] == "POST"
    assert attach["path"] == "/api/v2/invoices/{invoiceId}/attachments"
    assert attach["body_schema"]["properties"]["file"] == {"type": "string", "format": "binary"}
    inbox = operations["upload_inbox"]
    assert inbox["body_schema"]["required"] == ["document"]
    assert inbox["body_schema"]["properties"]["document"]["format"] == "binary"


def test_create_invoice_body_and_doc_url():
    operation = load_operations()["create_invoice"]
    assert operation["path"] == "/api/v2/invoices"
    assert operation["content_type"] == "application/json"
    assert operation["body_required"] is True
    assert operation["body_schema"]["required"] == ["contact_id", "items"]
    assert operation["body_schema"]["properties"]["items"]["type"] == "array"
    assert operation["doc_url"] == (
        "https://www.holded.com/developers/api-reference/invoices/create-an-invoice"
    )


def test_parameter_override_and_reference_expansion():
    spec = spec_for(
        {
            "/api/v2/invoices/{invoiceId}": {
                "parameters": [
                    {"name": "invoiceId", "in": "path", "schema": {"type": "string"}},
                    {"name": "Authorization", "in": "header", "schema": {"type": "string"}},
                ],
                "put": sample_operation(
                    operationId="update_invoice",
                    summary="Update an invoice",
                    deprecated=True,
                    parameters=[
                        {
                            "name": "invoiceId",
                            "in": "path",
                            "required": True,
                            "description": "Override",
                            "schema": {"type": "integer"},
                        }
                    ],
                    requestBody={
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Body",
                                    "description": "Local description",
                                }
                            },
                        },
                    },
                ),
            }
        },
        {
            "schemas": {
                "Body": {"properties": {"name": {"type": "string"}}, "description": "Original"}
            }
        },
    )
    operation = GENERATOR.build_catalog(spec)["update_invoice"]
    assert operation["parameters"] == [
        {
            "name": "invoiceId",
            "in": "path",
            "required": True,
            "description": "Override",
            "schema": {"type": "integer"},
        }
    ]
    assert operation["body_schema"] == {
        "type": "object",
        "description": "Local description",
        "properties": {"name": {"type": "string"}},
    }
    assert operation["body_required"] is True
    assert operation["content_type"] == "application/json"
    assert operation["deprecated"] is True


def test_recursive_refs_terminate_and_preserve_siblings():
    spec = {
        "components": {
            "schemas": {
                "Node": {
                    "type": "object",
                    "properties": {
                        "next": {"$ref": "#/components/schemas/Node", "description": "Next node"},
                    },
                }
            }
        }
    }
    expanded = GENERATOR.resolve_refs({"$ref": "#/components/schemas/Node"}, spec)
    assert expanded["properties"]["next"]["description"] == "Next node"
    assert (
        expanded["properties"]["next"]["x-holded-recursive-reference"]
        == "#/components/schemas/Node"
    )
    assert all("$ref" not in item for item in walk(expanded))


def test_pointer_escaping_and_normalization_do_not_modify_examples():
    spec = {"components": {"schemas": {"a/b~c": {"type": "string"}}}}
    assert GENERATOR.resolve_refs({"$ref": "#/components/schemas/a~1b~0c"}, spec) == {
        "type": "string"
    }
    schema = {
        "properties": {"nested": {"properties": {"field": {"type": "integer"}}}},
        "example": {"properties": {"x": "data"}},
    }
    normalized = GENERATOR.normalize_schema(schema)
    assert normalized["type"] == "object"
    assert normalized["properties"]["nested"]["type"] == "object"
    assert normalized["example"] == schema["example"]
    assert "type" not in schema


@pytest.mark.parametrize(
    "reference", ["https://example.com/schema.json", "#/components/schemas/Missing"]
)
def test_invalid_refs_fail_explicitly(reference):
    with pytest.raises(ValueError):
        GENERATOR.resolve_refs({"$ref": reference}, {})


def test_local_json_and_yaml_sources(tmp_path):
    document = spec_for({"/api/v2/invoices": {"get": sample_operation()}})
    json_path = tmp_path / "api.json"
    json_path.write_text(json.dumps(document), encoding="utf-8")
    assert GENERATOR.read_spec(json_path) == document
    yaml_path = tmp_path / "api.yaml"
    yaml_path.write_text("servers:\n  - url: https://api.holded.com\npaths: {}\n", encoding="utf-8")
    assert GENERATOR.read_spec(yaml_path)["paths"] == {}


def test_catalog_generation_is_deterministic():
    document = spec_for(
        {
            "/api/v2/z": {"get": sample_operation(operationId="z_op", summary="Z")},
            "/api/v2/a": {"get": sample_operation(operationId="a_op", summary="A")},
        }
    )
    catalog = GENERATOR.build_catalog(document)
    assert list(catalog) == ["a_op", "z_op"]
    reversed_document = {**document, "paths": dict(reversed(list(document["paths"].items())))}
    rebuilt = GENERATOR.build_catalog(reversed_document)
    assert json.dumps(rebuilt) == json.dumps(catalog)
    coverage = GENERATOR.coverage_markdown(catalog, "2026-10-14")
    assert coverage.index("`a_op`") < coverage.index("`z_op`")
    assert "| sales | 2 |" in coverage
    assert GENERATOR.count_summary(catalog) == "2 sales"


def spec_for(paths: dict[str, Any], components: dict[str, Any] | None = None):
    return {
        "openapi": "3.1.0",
        "servers": [{"url": "https://api.holded.com"}],
        "paths": paths,
        "components": components or {},
        "x-tagGroups": [
            {"name": "Sales", "tags": ["Invoices"]},
            {"name": "Team & HR", "tags": ["Employees"]},
        ],
    }


def test_operations_use_source_ids_tag_groups_scopes_and_reference_urls():
    spec = spec_for(
        {
            "/api/v2/invoices/{invoiceId}": {
                "put": {
                    "operationId": "update_invoice",
                    "summary": "Update an invoice",
                    "description": "**Required permission:** `sales:invoices.write`",
                    "tags": ["Invoices"],
                    "security": [{"bearerAuth": ["sales:invoices.write", "extra:scope.read"]}],
                    "x-ai-ui-card": {"action": "update"},
                    "parameters": [
                        {
                            "name": "invoiceId",
                            "in": "path",
                            "required": True,
                            "example": "507f1f77bcf86cd799439011",
                            "schema": {"type": "string", "pattern": "^[a-f0-9]{24}$"},
                        },
                        {"name": "Authorization", "in": "header", "schema": {"type": "string"}},
                    ],
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/Body",
                                }
                            }
                        },
                    },
                }
            },
            "/api/v2/employees/{employeeId}/documents": {
                "post": {
                    "operationId": "upload_employee_document",
                    "summary": "Upload a document",
                    "tags": ["Employees"],
                    "security": [{"bearerAuth": ["team:employees.write"]}],
                    "parameters": [
                        {"name": "employeeId", "in": "path", "schema": {"type": "string"}}
                    ],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "multipart/form-data": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "file": {
                                            "type": "string",
                                            "contentMediaType": "application/octet-stream",
                                        },
                                        "note": {"type": ["string", "null"]},
                                    },
                                }
                            }
                        },
                    },
                }
            },
        },
        {
            "schemas": {
                "Body": {
                    "properties": {
                        "notes": {
                            "type": ["string", "null"],
                            "x-ai-hidden": True,
                            "enum": ["a", None],
                        },
                        "x-ai-literal-property": {"type": "string"},
                    },
                    "example": {"x-ai-hidden": "kept in examples"},
                }
            }
        },
    )
    catalog = GENERATOR.build_catalog(spec)
    assert list(catalog) == ["update_invoice", "upload_employee_document"]
    update = catalog["update_invoice"]
    assert update["api"] == "sales"
    assert update["path"] == "/api/v2/invoices/{invoiceId}"
    assert update["tags"] == ["Invoices"]
    assert update["doc_url"] == (
        "https://www.holded.com/developers/api-reference/invoices/update-an-invoice"
    )
    assert update["description"].endswith(
        "Required permission scopes: `sales:invoices.write`, `extra:scope.read`."
    )
    assert update["parameters"] == [
        {
            "name": "invoiceId",
            "in": "path",
            "required": True,
            "schema": {
                "type": "string",
                "pattern": "^[a-f0-9]{24}$",
                "example": "507f1f77bcf86cd799439011",
            },
            "description": "",
        }
    ]
    assert update["body_schema"] == {
        "type": "object",
        "properties": {
            "notes": {"type": ["string", "null"], "enum": ["a", None]},
            "x-ai-literal-property": {"type": "string"},
        },
        "example": {"x-ai-hidden": "kept in examples"},
    }
    assert update["body_required"] is False
    upload = catalog["upload_employee_document"]
    assert upload["api"] == "team"
    assert upload["description"] == "Required permission scopes: `team:employees.write`."
    assert upload["body_required"] is True
    assert upload["content_type"] == "multipart/form-data"
    assert upload["body_schema"]["properties"]["file"] == {
        "type": "string",
        "contentMediaType": "application/octet-stream",
        "format": "binary",
    }
    assert upload["body_schema"]["properties"]["note"] == {"type": ["string", "null"]}


def sample_operation(**overrides):
    operation = {
        "operationId": "list_invoices",
        "summary": "List invoices",
        "tags": ["Invoices"],
    }
    operation.update(overrides)
    return operation


@pytest.mark.parametrize(
    "paths,message",
    [
        (
            {"/api/v2/invoices": {"get": sample_operation(tags=["Invoices", "Employees"])}},
            "exactly one tag",
        ),
        ({"/api/v2/invoices": {"get": sample_operation(tags=["Unknown"])}}, "x-tagGroups"),
        ({"/api/v2/invoices": {"get": sample_operation(operationId=None)}}, "operationId"),
        (
            {"/api/v2/invoices": {"get": sample_operation(operationId="ListInvoices")}},
            "operationId",
        ),
        ({"/api/invoicing/legacy/invoices": {"get": sample_operation()}}, "Unexpected API path"),
        (
            {
                "/api/v2/invoices": {
                    "get": sample_operation(
                        parameters=[{"name": "X-Company", "in": "header", "schema": {}}]
                    )
                }
            },
            "Unsupported header parameter",
        ),
        (
            {
                "/api/v2/a": {"get": sample_operation()},
                "/api/v2/b": {"get": sample_operation()},
            },
            "Duplicate operation ID",
        ),
        (
            {"/api/v2/invoices/{invoiceId}": {"get": sample_operation()}},
            "Missing path parameters",
        ),
    ],
)
def test_invalid_definitions_fail(paths, message):
    with pytest.raises(ValueError, match=message):
        GENERATOR.build_catalog(spec_for(paths))


def test_unknown_tag_group_and_server_fail():
    spec = spec_for({"/api/v2/invoices": {"get": sample_operation()}})
    spec["x-tagGroups"].append({"name": "Mystery", "tags": ["Other"]})
    with pytest.raises(ValueError, match="Unknown tag group"):
        GENERATOR.build_catalog(spec)
    spec = spec_for({"/api/v2/invoices": {"get": sample_operation()}})
    spec["servers"] = [{"url": "https://api.holded.com/api"}]
    with pytest.raises(ValueError, match="base path"):
        GENERATOR.build_catalog(spec)


def test_write_spec_round_trips_minified(tmp_path):
    spec = spec_for({"/api/v2/invoices": {"get": sample_operation(summary="Café")}})
    path = tmp_path / "nested" / "api2.json"
    GENERATOR.write_spec(spec, path)
    assert GENERATOR.read_spec(path) == spec
    assert "\n" not in path.read_text(encoding="utf-8").rstrip("\n")
    assert "Café" in path.read_text(encoding="utf-8")
