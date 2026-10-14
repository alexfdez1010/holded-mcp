"""Exercise MCP discovery, execution, and CLI behavior through the real SDK."""

from __future__ import annotations

import os
import subprocess
import sys

import httpx
import pytest
from mcp import Client, StdioServerParameters

from holded_mcp.server import create_server

API_KEY = "holded_server_test_key"
INVOICE_ID = "507f1f77bcf86cd799439011"


@pytest.fixture
def requests():
    return []


@pytest.fixture
def transport(requests):
    def handle(request):
        requests.append(request)
        return httpx.Response(200, json={"data": [{"id": INVOICE_ID}], "has_more": False})

    return httpx.MockTransport(handle)


async def test_mcp_discovery_and_read(transport, requests):
    async with Client(create_server(API_KEY, transport=transport)) as client:
        tools = {tool.name: tool for tool in (await client.list_tools()).tools}
        assert set(tools) == {
            "holded_search_operations",
            "holded_get_operation",
            "holded_read",
            "holded_write",
        }
        assert tools["holded_read"].annotations.read_only_hint is True
        assert tools["holded_write"].annotations.destructive_hint is True
        assert tools["holded_write"].annotations.idempotent_hint is False
        search_schema = tools["holded_search_operations"].input_schema["properties"]
        assert {"search", "version", "api", "tag", "offset", "limit"} <= set(search_schema)
        found = await client.call_tool("holded_search_operations", {"search": "list invoices"})
        assert not found.is_error
        operations = found.structured_content["operations"]
        assert "v2_list_invoices" in {op["operation_id"] for op in operations}
        assert operations[0]["version"] == "v2"  # Current operations are listed first.
        assert set(operations[0]) == {
            "operation_id",
            "version",
            "api",
            "method",
            "path",
            "summary",
            "tags",
        }
        schema = await client.call_tool(
            "holded_get_operation", {"operation_id": "v2_create_invoice"}
        )
        assert schema.structured_content["version"] == "v2"
        assert schema.structured_content["body_schema"]["required"] == ["contact_id", "items"]
        assert not requests  # Discovery stays offline.
        result = await client.call_tool(
            "holded_read", {"operation_id": "v2_list_invoices", "query": {"limit": 5}}
        )
        assert result.structured_content == {
            "status": 200,
            "data": {"data": [{"id": INVOICE_ID}], "has_more": False},
        }
        assert requests[0].url == "https://api.holded.com/api/v2/invoices?limit=5"
        assert requests[0].headers["Authorization"] == f"Bearer {API_KEY}"
        assert "key" not in requests[0].headers
        result = await client.call_tool(
            "holded_read", {"operation_id": "v1_invoicing_ListContacts"}
        )
        assert not result.is_error
        assert requests[1].url == "https://api.holded.com/api/invoicing/v1/contacts"
        assert requests[1].headers["key"] == API_KEY
        assert "authorization" not in requests[1].headers


async def test_search_filters_by_version_api_and_tag(transport, requests):
    async with Client(create_server(API_KEY, transport=transport)) as client:

        async def search(**args):
            result = await client.call_tool("holded_search_operations", {"limit": 100, **args})
            assert not result.is_error
            return result.structured_content

        assert (await search())["total"] == 496
        assert (await search(version="v2"))["total"] == 360
        assert (await search(version="v1"))["total"] == 136
        sales = await search(version="v2", api="sales")
        assert sales["total"] == 104
        assert all(op["api"] == "sales" for op in sales["operations"])
        crm = await search(api="crm")
        assert {op["version"] for op in crm["operations"]} == {"v1", "v2"}
        assert crm["total"] == 17 + 29
        assert (await search(version="v1", api="sales"))["total"] == 0
        invoices = await search(tag="invoices", version="v2")
        assert invoices["total"] > 0
        assert all(op["tags"] == ["Invoices"] for op in invoices["operations"])
        by_path = await search(search="/api/v2/invoices/find-by-number")
        assert [op["operation_id"] for op in by_path["operations"]] == [
            "v2_find_invoices_by_document_number"
        ]
        assert not requests


async def test_read_only_cannot_discover_or_execute_writes(transport, requests):
    server = create_server(API_KEY, read_only=True, transport=transport)
    async with Client(server) as client:
        assert "holded_write" not in {tool.name for tool in (await client.list_tools()).tools}
        for version in ("v1", "v2"):
            offset = 0
            while offset is not None:
                found = (
                    await client.call_tool(
                        "holded_search_operations",
                        {"version": version, "limit": 100, "offset": offset},
                    )
                ).structured_content
                assert all(op["method"] == "GET" for op in found["operations"])
                offset = found["next_offset"]
        for operation_id in ("v2_delete_invoice", "v1_invoicing_DeleteContact"):
            for tool in ("holded_read", "holded_get_operation"):
                result = await client.call_tool(tool, {"operation_id": operation_id})
                assert result.is_error
            result = await client.call_tool("holded_write", {"operation_id": operation_id})
            assert result.is_error
        assert not requests


async def test_write_and_wrong_tool_rejection(transport, requests):
    async with Client(create_server(API_KEY, transport=transport)) as client:
        result = await client.call_tool(
            "holded_write",
            {"operation_id": "v2_create_contact", "body": {"name": "Example"}},
        )
        assert not result.is_error
        assert requests[0].method == "POST"
        assert requests[0].url == "https://api.holded.com/api/v2/contacts"
        assert requests[0].content == b'{"name":"Example"}'
        assert requests[0].headers["Authorization"] == f"Bearer {API_KEY}"
        for tool, operation in (
            ("holded_write", "v2_list_invoices"),
            ("holded_write", "v1_invoicing_ListContacts"),
            ("holded_read", "v2_create_contact"),
            ("holded_read", "v1_invoicing_CreateContact"),
            ("holded_read", "v2_unknown_operation"),
            ("holded_write", "invoicing_CreateContact"),
        ):
            result = await client.call_tool(tool, {"operation_id": operation})
            assert result.is_error
        assert len(requests) == 1


async def test_invalid_arguments_never_reach_holded(transport, requests):
    async with Client(create_server(API_KEY, transport=transport)) as client:
        result = await client.call_tool(
            "holded_write",
            {"operation_id": "v2_delete_invoice", "path_params": {"invoiceId": "not-an-id"}},
        )
        assert result.is_error
        assert "pattern" in str(result)
        assert not requests


async def test_catalog_pagination_and_input_validation(transport, requests):
    async with Client(create_server(API_KEY, transport=transport)) as client:
        first = (
            await client.call_tool("holded_search_operations", {"limit": 1})
        ).structured_content
        second = (
            await client.call_tool(
                "holded_search_operations", {"limit": 1, "offset": first["next_offset"]}
            )
        ).structured_content
        assert first["total"] == 496
        assert first["operations"] != second["operations"]
        for args in ({"limit": 101}, {"offset": -1}, {"version": "v3"}, {"api": "billing"}):
            assert (await client.call_tool("holded_search_operations", args)).is_error
        assert (
            await client.call_tool("holded_get_operation", {"operation_id": "https://example.org"})
        ).is_error
        assert not requests


async def test_http_error_is_a_safe_mcp_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(403, json={"detail": request.headers["authorization"]})
    )
    async with Client(create_server("holded_secret", transport=transport)) as client:
        result = await client.call_tool("holded_read", {"operation_id": "v2_list_invoices"})
        assert result.is_error
        assert "holded_secret" not in str(result)
        assert "403" in str(result)


def test_instructions_prefer_v2():
    server = create_server(API_KEY)
    assert "prefer v2" in server.instructions
    assert "deprecated" in server.instructions
    assert "scope" in server.instructions
    assert "Write tools are enabled." in server.instructions
    assert "only permits reads" in create_server(API_KEY, read_only=True).instructions


async def test_actual_stdio_handshake():
    # A fake key suffices: initializing and browsing the catalog never calls Holded.
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "holded_mcp", "--read-only"],
        env={**os.environ, "HOLDED_API_KEY": "holded_stdio_test"},
    )
    async with Client(params) as client:
        assert len((await client.list_tools()).tools) == 3
        result = await client.call_tool(
            "holded_get_operation", {"operation_id": "v2_list_invoices"}
        )
        assert not result.is_error
        assert result.structured_content["path"] == "/api/v2/invoices"


@pytest.mark.parametrize("args", [["--help"], ["--version"]])
def test_cli_metadata_without_key(args):
    result = subprocess.run(
        [sys.executable, "-m", "holded_mcp", *args],
        env={**os.environ, "HOLDED_API_KEY": ""},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert result.stdout


def test_missing_key_fails_cleanly():
    result = subprocess.run(
        [sys.executable, "-m", "holded_mcp"],
        env={**os.environ, "HOLDED_API_KEY": ""},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == ""
    assert "HOLDED_API_KEY" in result.stderr
    assert "Traceback" not in result.stderr


@pytest.mark.parametrize("value", ["0", "-1", "nan", "inf", "invalid"])
def test_invalid_timeout_fails(value):
    result = subprocess.run(
        [sys.executable, "-m", "holded_mcp", "--timeout", value],
        env={**os.environ, "HOLDED_API_KEY": "holded_test"},
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 2
    assert result.stdout == ""
