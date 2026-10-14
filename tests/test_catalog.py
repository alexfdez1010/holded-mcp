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
    "v1": {"invoicing", "crm", "projects", "team", "accounting"},
    "v2": {
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
    },
}
PATH_RE = {
    "v1": re.compile(r"/api/(invoicing|crm|projects|team|accounting)/v1/[A-Za-z0-9_{}./-]+"),
    "v2": re.compile(r"/api/v2/[A-Za-z0-9_{}./-]+"),
}
ID_RE = {
    "v1": re.compile(r"v1_[a-z]+_[A-Z][A-Za-z0-9]*"),
    "v2": re.compile(r"v2_[a-z][a-z0-9_]*"),
}
OPERATION_KEYS = {
    "operation_id",
    "version",
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
    assert len(operations) == 496
    assert Counter(op["version"] for op in operations.values()) == {"v1": 136, "v2": 360}
    assert Counter(op["api"] for op in operations.values() if op["version"] == "v1") == {
        "invoicing": 72,
        "crm": 29,
        "projects": 16,
        "team": 15,
        "accounting": 4,
    }
    assert Counter(op["api"] for op in operations.values() if op["version"] == "v2") == {
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
        "v1_invoicing_ListContacts",
        "v1_invoicing_CreateDocument",
        "v1_invoicing_AttachFile",
        "v1_invoicing_GetDocumentPDF",
        "v1_crm_ListFunnels",
        "v1_projects_ListProjects",
        "v1_team_ListEmployees",
        "v1_accounting_ListDailyLedger",
        "v2_list_invoices",
        "v2_create_invoice",
        "v2_find_invoices_by_document_number",
        "v2_list_contacts",
        "v2_upload_inbox",
        "v2_list_leads",
        "v2_list_employees",
    ):
        assert operation_id in operations
    assert len({(op["method"], op["path"]) for op in operations.values()}) == 496
    assert len({op["doc_url"] for op in operations.values()}) == 496


def test_committed_specs_rebuild_the_packaged_catalog():
    paths = GENERATOR.spec_paths()
    specs = {key: GENERATOR.read_spec(path) for key, path in paths.items()}
    v1 = {api: specs[api] for api in GENERATOR.V1_APIS}
    rebuilt = GENERATOR.build_catalog(v1, specs["v2"])
    assert rebuilt == load_operations()
    assert sum(path.stat().st_size for path in paths.values()) < 5 * 1024 * 1024


def test_operation_structure_invariants():
    operations = load_operations()
    for operation_id, operation in operations.items():
        version = operation["version"]
        assert set(operation) == OPERATION_KEYS
        assert operation["operation_id"] == operation_id
        assert version in APIS
        assert operation["api"] in APIS[version]
        assert ID_RE[version].fullmatch(operation_id), operation_id
        assert operation["method"] in {"GET", "POST", "PUT", "DELETE", "PATCH"}
        assert PATH_RE[version].fullmatch(operation["path"]), operation["path"]
        if version == "v1":
            assert operation_id.startswith(f"v1_{operation['api']}_")
            assert operation["path"].startswith(f"/api/{operation['api']}/v1/")
            assert operation["doc_url"].startswith("https://www.holded.com/developers/v1/")
        else:
            assert len(operation["tags"]) == 1
            assert operation["doc_url"].startswith(
                "https://www.holded.com/developers/api-reference/"
            )
            assert "Required permission" in operation["description"]
        assert isinstance(operation["summary"], str) and operation["summary"]
        assert isinstance(operation["description"], str)
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
            assert parameter["name"].casefold() not in {"key", "authorization"}
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
    first["v1_invoicing_CreateDocument"]["body_schema"]["properties"].clear()
    assert load_operations()["v1_invoicing_CreateDocument"]["body_schema"]["properties"]


def test_document_type_enums():
    operations = load_operations()
    doc_type_operations = [
        op
        for op in operations.values()
        if op["version"] == "v1" and any(p["name"] == "docType" for p in op["parameters"])
    ]
    assert len(doc_type_operations) == 12
    enums = {
        op["operation_id"]: next(p for p in op["parameters"] if p["name"] == "docType")["schema"][
            "enum"
        ]
        for op in doc_type_operations
    }
    assert enums["v1_invoicing_CreateDocument"] == DOC_TYPES
    assert enums["v1_invoicing_ListDocuments"] == DOC_TYPES
    assert enums["v1_invoicing_GetDocument"] == DOC_TYPES
    assert enums["v1_invoicing_UpdateTrackingInfo"] == ["salesorder", "waybill"]
    assert enums["v1_invoicing_UpdateDocumentPipeline"] == ["salesorder", "waybill"]
    assert enums["v1_invoicing_ShippedUnitsByItem"] == ["salesorder", "order"]
    sort = next(
        p for p in operations["v1_invoicing_ListDocuments"]["parameters"] if p["name"] == "sort"
    )
    assert sort["schema"]["enum"] == ["created-asc", "created-desc"]


def test_multipart_upload_metadata():
    operations = load_operations()
    multipart = [
        op_id for op_id, op in operations.items() if op["content_type"] == "multipart/form-data"
    ]
    assert [op for op in multipart if op.startswith("v1_")] == ["v1_invoicing_AttachFile"]
    attach = operations["v1_invoicing_AttachFile"]
    assert attach["method"] == "POST"
    assert attach["path"] == "/api/invoicing/v1/documents/{docType}/{documentId}/attach"
    assert attach["body_schema"]["type"] == "object"
    assert attach["body_schema"]["properties"]["file"]["type"] == "string"
    assert attach["body_schema"]["properties"]["file"]["format"] == "binary"
    assert attach["body_schema"]["properties"]["setMain"] == {"type": "boolean"}


def test_create_document_body_and_doc_url():
    operation = load_operations()["v1_invoicing_CreateDocument"]
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
    assert operations["v1_projects_GetProjectTimes"]["path"].endswith("/projects/{projectId}/times")
    assert operations["v1_projects_GetProjectTime"]["path"].endswith(
        "/projects/{projectId}/times/{timeTrackingId}"
    )
    assert operations["v1_projects_GetProjectSummary"]["doc_url"].endswith(
        "/projects-api/projects/get-projects-projectid-summary"
    )
    assert "v1_accounting_ListAccounts" in operations
    assert "v1_team_ListEmployeeTimes" in operations


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
    operation = GENERATOR.build_v1_catalog({"invoicing": spec})["v1_invoicing_UpdateContact"]
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
        GENERATOR.build_v1_catalog(
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
        GENERATOR.build_v1_catalog(
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
        GENERATOR.build_v1_catalog({"crm": spec})
    spec["servers"] = [{"url": "https://example.com/api/invoicing/v1"}]
    with pytest.raises(ValueError, match="Unexpected Holded API server"):
        GENERATOR.build_v1_catalog({"invoicing": spec})


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
    catalog = GENERATOR.build_v1_catalog({"invoicing": document})
    assert list(catalog) == ["v1_invoicing_A", "v1_invoicing_Z"]
    reversed_document = {**document, "paths": dict(reversed(list(document["paths"].items())))}
    rebuilt = GENERATOR.build_v1_catalog({"invoicing": reversed_document})
    assert json.dumps(rebuilt) == json.dumps(catalog)
    coverage = GENERATOR.coverage_markdown(catalog, "2026-10-14")
    assert coverage.index("`v1_invoicing_A`") < coverage.index("`v1_invoicing_Z`")


def v2_spec(paths: dict[str, Any], components: dict[str, Any] | None = None):
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


def test_v2_operations_use_source_ids_tag_groups_scopes_and_reference_urls():
    spec = v2_spec(
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
    catalog = GENERATOR.build_v2_catalog(spec)
    assert list(catalog) == ["v2_update_invoice", "v2_upload_employee_document"]
    update = catalog["v2_update_invoice"]
    assert update["version"] == "v2"
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
    upload = catalog["v2_upload_employee_document"]
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


def _v2_operation(**overrides):
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
            {"/api/v2/invoices": {"get": _v2_operation(tags=["Invoices", "Employees"])}},
            "exactly one tag",
        ),
        ({"/api/v2/invoices": {"get": _v2_operation(tags=["Unknown"])}}, "x-tagGroups"),
        ({"/api/v2/invoices": {"get": _v2_operation(operationId=None)}}, "operationId"),
        ({"/api/v2/invoices": {"get": _v2_operation(operationId="ListInvoices")}}, "operationId"),
        ({"/api/v1/invoices": {"get": _v2_operation()}}, "Unexpected v2 path"),
        (
            {
                "/api/v2/invoices": {
                    "get": _v2_operation(
                        parameters=[{"name": "X-Company", "in": "header", "schema": {}}]
                    )
                }
            },
            "Unsupported header parameter",
        ),
        (
            {
                "/api/v2/a": {"get": _v2_operation()},
                "/api/v2/b": {"get": _v2_operation()},
            },
            "Duplicate operation ID",
        ),
    ],
)
def test_invalid_v2_definitions_fail(paths, message):
    with pytest.raises(ValueError, match=message):
        GENERATOR.build_v2_catalog(v2_spec(paths))


def test_v2_unknown_tag_group_and_server_fail():
    spec = v2_spec({"/api/v2/invoices": {"get": _v2_operation()}})
    spec["x-tagGroups"].append({"name": "Mystery", "tags": ["Other"]})
    with pytest.raises(ValueError, match="Unknown v2 tag group"):
        GENERATOR.build_v2_catalog(spec)
    spec = v2_spec({"/api/v2/invoices": {"get": _v2_operation()}})
    spec["servers"] = [{"url": "https://api.holded.com/api"}]
    with pytest.raises(ValueError, match="base path"):
        GENERATOR.build_v2_catalog(spec)


def test_merged_catalog_and_coverage_report_both_versions():
    v1 = minimal_spec({"/contacts": {"get": {"operationId": "List Contacts", "tags": ["A"]}}})
    v2 = v2_spec({"/api/v2/invoices": {"get": _v2_operation()}})
    catalog = GENERATOR.build_catalog({"invoicing": v1}, v2)
    assert list(catalog) == ["v1_invoicing_ListContacts", "v2_list_invoices"]
    assert GENERATOR.count_summary(catalog) == "1 v1 (1 invoicing); 1 v2 (1 sales)"
    coverage = GENERATOR.coverage_markdown(catalog, "2026-10-14")
    assert "| v2 | sales | 1 |" in coverage
    assert "| v1 | invoicing | 1 |" in coverage
    assert coverage.index("### v2\n\n| Operation ID") < coverage.index("### v1\n\n| Operation ID")


def test_write_spec_round_trips_minified(tmp_path):
    spec = v2_spec({"/api/v2/invoices": {"get": _v2_operation(summary="Café")}})
    path = tmp_path / "nested" / "api2.json"
    GENERATOR.write_spec(spec, path)
    assert GENERATOR.read_spec(path) == spec
    assert "\n" not in path.read_text(encoding="utf-8").rstrip("\n")
    assert "Café" in path.read_text(encoding="utf-8")
