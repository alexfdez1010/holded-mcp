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

APIS = {"invoicing", "crm", "projects", "team", "accounting"}
PATH_RE = re.compile(r"/api/(invoicing|crm|projects|team|accounting)/v1/[A-Za-z0-9_{}./-]+")
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
DOC_TYPES = [
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
]


def walk(value: Any):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def minimal_spec(
    paths: dict[str, Any], components: dict[str, Any] | None = None, api: str = "invoicing"
):
    return {
        "servers": [{"url": f"https://api.holded.com/api/{api}/v1"}],
        "paths": paths,
        "components": components or {},
    }


def test_snapshot_covers_all_documented_operations():
    operations = load_operations()
    assert len(operations) == 136
    assert Counter(operation["api"] for operation in operations.values()) == {
        "invoicing": 72,
        "crm": 29,
        "projects": 16,
        "team": 15,
        "accounting": 4,
    }
    for operation_id in (
        "invoicing_ListContacts",
        "invoicing_CreateDocument",
        "invoicing_AttachFile",
        "invoicing_GetDocumentPDF",
        "crm_ListFunnels",
        "projects_ListProjects",
        "team_ListEmployees",
        "accounting_ListDailyLedger",
    ):
        assert operation_id in operations
    assert len({(op["method"], op["path"]) for op in operations.values()}) == 136


def test_operation_structure_invariants():
    operations = load_operations()
    for operation_id, operation in operations.items():
        assert set(operation) == OPERATION_KEYS
        assert operation["operation_id"] == operation_id
        assert operation["api"] in APIS
        assert operation_id.startswith(operation["api"] + "_")
        assert re.fullmatch(r"[a-z]+_[A-Z][A-Za-z0-9]*", operation_id)
        assert operation["method"] in {"GET", "POST", "PUT", "DELETE", "PATCH"}
        assert PATH_RE.fullmatch(operation["path"]), operation["path"]
        assert operation["path"].startswith(f"/api/{operation['api']}/v1/")
        assert isinstance(operation["summary"], str) and operation["summary"]
        assert isinstance(operation["description"], str)
        assert all(isinstance(tag, str) for tag in operation["tags"])
        assert isinstance(operation["body_required"], bool)
        assert isinstance(operation["deprecated"], bool)
        assert operation["doc_url"].startswith("https://www.holded.com/developers/v1/")
        assert all("$ref" not in item for item in walk(operation))
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
            assert parameter["name"] != "key"
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
    first["invoicing_CreateDocument"]["body_schema"]["properties"].clear()
    assert load_operations()["invoicing_CreateDocument"]["body_schema"]["properties"]


def test_document_type_enums():
    operations = load_operations()
    doc_type_operations = [
        op for op in operations.values() if any(p["name"] == "docType" for p in op["parameters"])
    ]
    assert len(doc_type_operations) == 12
    enums = {
        op["operation_id"]: next(p for p in op["parameters"] if p["name"] == "docType")["schema"][
            "enum"
        ]
        for op in doc_type_operations
    }
    assert enums["invoicing_CreateDocument"] == DOC_TYPES
    assert enums["invoicing_ListDocuments"] == DOC_TYPES
    assert enums["invoicing_GetDocument"] == DOC_TYPES
    assert enums["invoicing_UpdateTrackingInfo"] == ["salesorder", "waybill"]
    assert enums["invoicing_UpdateDocumentPipeline"] == ["salesorder", "waybill"]
    assert enums["invoicing_ShippedUnitsByItem"] == ["salesorder", "order"]
    sort = next(
        p for p in operations["invoicing_ListDocuments"]["parameters"] if p["name"] == "sort"
    )
    assert sort["schema"]["enum"] == ["created-asc", "created-desc"]


def test_multipart_upload_metadata():
    operations = load_operations()
    multipart = [
        op_id for op_id, op in operations.items() if op["content_type"] == "multipart/form-data"
    ]
    assert multipart == ["invoicing_AttachFile"]
    attach = operations["invoicing_AttachFile"]
    assert attach["method"] == "POST"
    assert attach["path"] == "/api/invoicing/v1/documents/{docType}/{documentId}/attach"
    assert attach["body_schema"]["type"] == "object"
    assert attach["body_schema"]["properties"]["file"]["type"] == "string"
    assert attach["body_schema"]["properties"]["file"]["format"] == "binary"
    assert attach["body_schema"]["properties"]["setMain"] == {"type": "boolean"}


def test_create_document_body_and_doc_url():
    operation = load_operations()["invoicing_CreateDocument"]
    assert operation["path"] == "/api/invoicing/v1/documents/{docType}"
    assert operation["content_type"] == "application/json"
    properties = operation["body_schema"]["properties"]
    assert properties["date"]["type"] == "integer"
    assert properties["items"]["type"] == "array"
    assert operation["doc_url"] == (
        "https://www.holded.com/developers/v1/invoice-api/documents/create-document"
    )


def test_name_overrides_resolve_collisions():
    operations = load_operations()
    assert operations["projects_GetProjectTimes"]["path"].endswith("/projects/{projectId}/times")
    assert operations["projects_GetProjectTime"]["path"].endswith(
        "/projects/{projectId}/times/{timeTrackingId}"
    )
    assert operations["projects_GetProjectSummary"]["doc_url"].endswith(
        "/projects-api/projects/get-projects-projectid-summary"
    )
    assert "accounting_ListAccounts" in operations
    assert "team_ListEmployeeTimes" in operations


def test_parameter_override_and_reference_expansion():
    spec = minimal_spec(
        {
            "/contacts/{contactId}": {
                "parameters": [
                    {
                        "name": "contactId",
                        "in": "path",
                        "schema": {"type": "string"},
                    },
                    {"name": "key", "in": "header", "schema": {"type": "string"}},
                ],
                "put": {
                    "operationId": "Update Contact",
                    "tags": ["CONTACTS"],
                    "deprecated": True,
                    "parameters": [
                        {
                            "name": "contactId",
                            "in": "path",
                            "required": True,
                            "description": "Override",
                            "schema": {"type": "integer"},
                        }
                    ],
                    "requestBody": {
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
                },
            }
        },
        {
            "schemas": {
                "Body": {"properties": {"name": {"type": "string"}}, "description": "Original"}
            }
        },
    )
    operation = GENERATOR.build_catalog({"invoicing": spec})["invoicing_UpdateContact"]
    assert operation["path"] == "/api/invoicing/v1/contacts/{contactId}"
    assert operation["parameters"] == [
        {
            "name": "contactId",
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
    assert operation["doc_url"].endswith("/invoice-api/contacts/update-contact")


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


def test_duplicate_ids_and_missing_path_parameters_fail():
    with pytest.raises(ValueError, match="Duplicate operation ID"):
        GENERATOR.build_catalog(
            {
                "crm": minimal_spec(
                    {
                        "/first": {"get": {"operationId": "Same Name", "tags": ["A"]}},
                        "/second": {"get": {"operationId": "SameName", "tags": ["A"]}},
                    },
                    api="crm",
                )
            }
        )
    with pytest.raises(ValueError, match="Missing path parameters"):
        GENERATOR.build_catalog(
            {
                "crm": minimal_spec(
                    {"/leads/{leadId}": {"get": {"operationId": "Missing", "tags": ["A"]}}},
                    api="crm",
                )
            }
        )


def test_unexpected_server_fails():
    spec = minimal_spec({"/x": {"get": {"operationId": "X", "tags": ["A"]}}})
    with pytest.raises(ValueError, match="Unexpected base path"):
        GENERATOR.build_catalog({"crm": spec})
    spec["servers"] = [{"url": "https://example.com/api/invoicing/v1"}]
    with pytest.raises(ValueError, match="Unexpected Holded API server"):
        GENERATOR.build_catalog({"invoicing": spec})


def test_documented_choices_parser():
    description = (
        "docType should be one of: {invoice, salesreceipt, creditnote, salesorder, "
        "proform, waybill,estimate, purchase, purchaseorder or purchaserefund}"
    )
    assert GENERATOR.documented_choices(description) == DOC_TYPES
    assert GENERATOR.documented_choices("no list here") is None


def test_pascal_case():
    assert GENERATOR.pascal_case("List Contacts") == "ListContacts"
    assert GENERATOR.pascal_case("getDocument") == "GetDocument"
    assert GENERATOR.pascal_case("GetDocumentPDF") == "GetDocumentPDF"
    assert GENERATOR.pascal_case("Delete Expenses account") == "DeleteExpensesAccount"


def test_local_json_and_yaml_sources(tmp_path):
    document = minimal_spec({"/contacts": {"get": {"operationId": "List", "tags": ["A"]}}})
    json_path = tmp_path / "api.json"
    json_path.write_text(json.dumps(document), encoding="utf-8")
    assert GENERATOR.read_spec(json_path) == document
    yaml_path = tmp_path / "api.yaml"
    yaml_path.write_text(
        "servers:\n  - url: https://api.holded.com/api/crm/v1\npaths: {}\n", encoding="utf-8"
    )
    assert GENERATOR.read_spec(yaml_path)["paths"] == {}


def test_catalog_generation_is_deterministic():
    document = minimal_spec(
        {
            "/z": {"get": {"operationId": "Z", "tags": ["A"]}},
            "/a": {"get": {"operationId": "A", "tags": ["A"]}},
        }
    )
    catalog = GENERATOR.build_catalog({"invoicing": document})
    assert list(catalog) == ["invoicing_A", "invoicing_Z"]
    reversed_document = {**document, "paths": dict(reversed(list(document["paths"].items())))}
    rebuilt = GENERATOR.build_catalog({"invoicing": reversed_document})
    assert json.dumps(rebuilt) == json.dumps(catalog)
    coverage = GENERATOR.coverage_markdown(catalog, "2026-10-14")
    assert coverage.index("`invoicing_A`") < coverage.index("`invoicing_Z`")
