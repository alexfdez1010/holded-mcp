"""Transport tests use fake requests and synthetic operations; no Holded account is needed."""

import base64
import copy
import json

import httpx
import pytest

from holded_mcp.client import MAX_DOWNLOAD_BYTES, MAX_UPLOAD_BYTES, HoldedClient, HoldedError

API_KEY = "holded_test_key_do_not_expose_0123456789"
DOC_TYPES = ["invoice", "salesreceipt", "creditnote", "estimate", "purchase", "proform"]


def no_network():
    return httpx.MockTransport(lambda _: pytest.fail("unexpected request"))


def recording(requests, status=200, payload=None):
    return httpx.MockTransport(
        lambda request: (
            requests.append(request)
            or httpx.Response(status, json={} if payload is None else payload)
        )
    )


def operation(method="GET", **overrides):
    """A synthetic GET /api/invoicing/v1/contacts/{contactId}-style operation."""
    result = {
        "method": method,
        "path": "/api/invoicing/v1/contacts/{contactId}",
        "parameters": [
            {"in": "path", "name": "contactId", "required": True, "schema": {"type": "string"}},
            {"in": "query", "name": "includeArchived", "schema": {"type": "boolean"}},
            {
                "in": "query",
                "name": "customId",
                "schema": {"type": "array", "items": {"type": "string"}},
            },
        ],
        "body_schema": None,
        "body_required": False,
        "content_type": None,
    }
    result.update(overrides)
    return result


def list_contacts_operation():
    return {
        "method": "GET",
        "path": "/api/invoicing/v1/contacts",
        "parameters": [
            {"in": "query", "name": "phone", "schema": {"type": "string"}},
            {"in": "query", "name": "mobile", "schema": {"type": "string"}},
            {
                "in": "query",
                "name": "customId",
                "schema": {"type": "array", "items": {"type": "string"}},
            },
            {"in": "query", "name": "page", "schema": {"type": "integer", "minimum": 1}},
        ],
        "body_schema": None,
        "body_required": False,
        "content_type": None,
    }


def create_document_operation():
    return {
        "method": "POST",
        "path": "/api/invoicing/v1/documents/{docType}",
        "parameters": [
            {
                "in": "path",
                "name": "docType",
                "required": True,
                "schema": {"type": "string", "enum": DOC_TYPES},
            }
        ],
        "body_schema": {
            "type": "object",
            "required": ["date"],
            "properties": {
                "contactId": {"type": "string"},
                "date": {"type": "integer"},
                "notes": {"type": "string", "nullable": True},
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "units": {"type": "number", "minimum": 0},
                            "subtotal": {"type": "number"},
                        },
                    },
                },
            },
        },
        "body_required": True,
        "content_type": "application/json",
    }


def attach_operation():
    return {
        "method": "POST",
        "path": "/api/invoicing/v1/documents/{docType}/{documentId}/attach",
        "parameters": [
            {
                "in": "path",
                "name": "docType",
                "required": True,
                "schema": {"type": "string", "enum": DOC_TYPES},
            },
            {"in": "path", "name": "documentId", "required": True, "schema": {"type": "string"}},
        ],
        "body_schema": {
            "type": "object",
            "required": ["file"],
            "properties": {
                "file": {"type": "string", "format": "binary"},
                "setMain": {"type": "boolean"},
            },
        },
        "body_required": True,
        "content_type": "multipart/form-data",
    }


ATTACH_PATH = {"docType": "invoice", "documentId": "5ab3a9e6d4c8a2001a1b2c3d"}


def upload(**overrides):
    result = {
        "field": "file",
        "filename": "invoice.pdf",
        "content_base64": base64.b64encode(b"%PDF-1.4 hello").decode(),
        "content_type": "application/pdf",
    }
    result.update(overrides)
    return result


@pytest.mark.parametrize(
    "api_key",
    ["", " ", " s3cr3t", "s3cr3t ", "s3cr3t\n", "s3cr3t\r", "s 3", "s\x00", "s\x7f", "é", None],
)
def test_invalid_api_keys_do_not_appear_in_errors(api_key):
    with pytest.raises(HoldedError, match="HOLDED_API_KEY") as exc:
        HoldedClient(api_key)
    if api_key and api_key.strip():
        assert api_key.strip() not in str(exc.value)


@pytest.mark.parametrize("timeout", [0, -1, float("nan"), float("inf"), True, "30", None])
def test_invalid_timeouts(timeout):
    with pytest.raises(HoldedError, match="timeout"):
        HoldedClient(API_KEY, timeout=timeout)


async def test_key_header_fixed_origin_json_result_and_context_manager():
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests, payload=[{"id": "c1"}])) as c:
        result = await c.request(list_contacts_operation())
    assert result == {"status": 200, "data": [{"id": "c1"}]}
    request = requests[0]
    assert request.method == "GET"
    assert request.headers["key"] == API_KEY
    assert "authorization" not in request.headers
    assert request.headers["accept"] == "application/json, */*;q=0.8"
    assert str(request.url) == "https://api.holded.com/api/invoicing/v1/contacts"
    assert request.content == b""
    assert c._client.is_closed


async def test_v2_operations_use_bearer_authorization_only():
    requests = []
    op = operation(path="/api/v2/contacts/{contactId}", version="v2")
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(op, path_params={"contactId": "abc"}, query={"includeArchived": True})
    request = requests[0]
    assert str(request.url) == "https://api.holded.com/api/v2/contacts/abc?includeArchived=true"
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert "key" not in request.headers
    assert request.headers["accept"] == "application/json, */*;q=0.8"


async def test_auth_header_is_chosen_per_request_and_never_sent_twice():
    requests = []
    v1 = operation(version="v1")
    v2 = operation(path="/api/v2/contacts/{contactId}")
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        assert "key" not in client._client.headers
        assert "authorization" not in client._client.headers
        for op in (v2, v1, v2):
            await client.request(op, path_params={"contactId": "abc"})
    assert [request.url.path for request in requests] == [
        "/api/v2/contacts/abc",
        "/api/invoicing/v1/contacts/abc",
        "/api/v2/contacts/abc",
    ]
    for request in requests:
        auth = {name for name in ("key", "authorization") if name in request.headers}
        assert len(auth) == 1
        assert len(request.headers.get_list(auth.pop())) == 1
    assert requests[0].headers["authorization"] == f"Bearer {API_KEY}"
    assert requests[1].headers["key"] == API_KEY
    assert "authorization" not in requests[1].headers


@pytest.mark.parametrize(
    "version,path",
    [("v1", "/api/v2/contacts/{contactId}"), ("v2", "/api/invoicing/v1/contacts/{contactId}")],
)
async def test_declared_version_must_match_path(version, path):
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="version"):
            await client.request(
                operation(path=path, version=version), path_params={"contactId": "abc"}
            )


async def test_v2_errors_and_bodies_redact_the_bearer_key():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(401, json={"detail": request.headers["authorization"]})

    op = create_document_operation()
    op["path"] = "/api/v2/documents/{docType}"
    async with HoldedClient(API_KEY, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(HoldedError) as exc:
            await client.request(op, path_params={"docType": "invoice"}, body={"date": 1})
    assert API_KEY not in str(exc.value)
    assert "Bearer [REDACTED]" in str(exc.value)
    assert exc.value.status_code == 401
    assert json.loads(requests[0].content) == {"date": 1}
    assert "key" not in requests[0].headers


async def test_v2_multipart_upload_uses_bearer():
    requests = []
    op = attach_operation()
    op["path"] = "/api/v2/invoices/{docType}/{documentId}/attachments"
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(op, path_params=ATTACH_PATH, files=[upload()])
    assert requests[0].headers["authorization"] == f"Bearer {API_KEY}"
    assert "key" not in requests[0].headers
    assert requests[0].headers["content-type"].startswith("multipart/form-data; boundary=")


@pytest.mark.parametrize("api", ["invoicing", "crm", "projects", "team", "accounting"])
async def test_every_documented_api_family_is_reachable(api):
    requests = []
    op = operation(path=f"/api/{api}/v1/items/{{contactId}}")
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(op, path_params={"contactId": "abc"})
    assert str(requests[0].url) == f"https://api.holded.com/api/{api}/v1/items/abc"


@pytest.mark.parametrize(
    "content_type", ["application/pdf", "application/octet-stream", "image/png; charset=binary"]
)
async def test_binary_downloads_are_returned_as_base64(content_type):
    payload = b"%PDF-1.7\x00\xff\xfe binary"
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, content=payload, headers={"Content-Type": content_type})
    )
    async with HoldedClient(API_KEY, transport=transport) as client:
        result = await client.request(
            operation(path="/api/v2/invoices/{contactId}/pdf"), path_params={"contactId": "a"}
        )
    assert result == {
        "status": 200,
        "data": {
            "content_type": content_type.split(";")[0],
            "size": len(payload),
            "content_base64": base64.b64encode(payload).decode(),
        },
    }


async def test_oversized_binary_downloads_are_rejected():
    transport = httpx.MockTransport(
        lambda _: httpx.Response(
            200,
            content=b"0" * (MAX_DOWNLOAD_BYTES + 1),
            headers={"Content-Type": "application/pdf"},
        )
    )
    async with HoldedClient(API_KEY, transport=transport) as client:
        with pytest.raises(HoldedError, match="10 MiB"):
            await client.request(operation(), path_params={"contactId": "a"})


@pytest.mark.parametrize("content_type", ["application/problem+json", "text/plain", ""])
async def test_json_and_text_responses_are_not_treated_as_files(content_type):
    headers = {"Content-Type": content_type} if content_type else {}
    transport = httpx.MockTransport(
        lambda _: httpx.Response(200, content=b'{"a": 1}', headers=headers)
    )
    async with HoldedClient(API_KEY, transport=transport) as client:
        result = await client.request(operation(), path_params={"contactId": "a"})
    assert result["data"] == {"a": 1}


async def test_proxy_environment_ignored(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://credential-thief.invalid")
    async with HoldedClient(API_KEY) as client:
        assert client._client._trust_env is False
        assert client._client.follow_redirects is False


@pytest.mark.parametrize("status,data", [(204, None), (200, "hello")])
async def test_empty_and_non_json_responses(status, data):
    transport = httpx.MockTransport(lambda _: httpx.Response(status, text=data or ""))
    async with HoldedClient(API_KEY, transport=transport) as client:
        assert await client.request(operation(), path_params={"contactId": "abc"}) == {
            "status": status,
            "data": data,
        }


@pytest.mark.parametrize("status", [301, 302, 307, 308])
async def test_redirects_never_forward_credentials(status):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status, headers={"Location": "https://evil.invalid/stolen"})

    async with HoldedClient(API_KEY, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(HoldedError) as exc:
            await client.request(operation(), path_params={"contactId": "abc"})
    assert exc.value.status_code == status
    assert len(requests) == 1


@pytest.mark.parametrize("status", [400, 401, 403, 404, 500])
async def test_api_errors_redact_key_and_bound_response(status):
    transport = httpx.MockTransport(
        lambda _: httpx.Response(status, json={"info": API_KEY + "x" * 4000})
    )
    async with HoldedClient(API_KEY, transport=transport) as client:
        with pytest.raises(HoldedError) as exc:
            await client.request(operation(), path_params={"contactId": "abc"})
    assert API_KEY not in str(exc.value)
    assert "[REDACTED]" in str(exc.value)
    assert f"HTTP {status}" in str(exc.value)
    assert exc.value.status_code == status
    assert exc.value.retry_after is None
    assert len(str(exc.value)) < 1100


async def test_text_errors_and_success_echo_redact_secrets():
    responses = iter(
        [httpx.Response(400, text=API_KEY), httpx.Response(200, json={API_KEY: [API_KEY]})]
    )
    transport = httpx.MockTransport(lambda _: next(responses))
    async with HoldedClient(API_KEY, transport=transport) as client:
        with pytest.raises(HoldedError) as exc:
            await client.request(operation(), path_params={"contactId": "abc"})
        assert API_KEY not in str(exc.value)
        result = await client.request(operation(), path_params={"contactId": "abc"})
    assert API_KEY not in json.dumps(result)
    assert result["data"] == {"[REDACTED]": ["[REDACTED]"]}


async def test_rate_limit_metadata_no_automatic_mutation_retry():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(429, json={"info": "Too many requests"}, headers={"Retry-After": "5"})

    async with HoldedClient(API_KEY, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(HoldedError) as exc:
            await client.request(operation("DELETE"), path_params={"contactId": "abc"})
    assert exc.value.status_code == 429
    assert exc.value.retry_after == "5"
    assert "Rate limited; Retry-After=5" in str(exc.value)
    assert "Retry explicitly" in str(exc.value)
    assert not hasattr(exc.value, "rate_limit_reset")
    assert len(requests) == 1


async def test_rate_limit_without_retry_after_header():
    transport = httpx.MockTransport(lambda _: httpx.Response(429, text=""))
    async with HoldedClient(API_KEY, transport=transport) as client:
        with pytest.raises(HoldedError, match="Retry-After=unavailable") as exc:
            await client.request(operation(), path_params={"contactId": "abc"})
    assert exc.value.retry_after is None


@pytest.mark.parametrize(
    "error_class,message",
    [(httpx.ReadTimeout, "timed out"), (httpx.ConnectError, "Could not connect")],
)
async def test_transport_errors_hide_secrets_and_do_not_replay(error_class, message):
    requests = []

    def handler(request):
        requests.append(request)
        raise error_class(API_KEY, request=request)

    async with HoldedClient(API_KEY, transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(HoldedError, match=message) as exc:
            await client.request(operation("POST"), path_params={"contactId": "abc"})
    assert API_KEY not in str(exc.value)
    assert exc.value.__suppress_context__
    assert exc.value.status_code is None
    assert len(requests) == 1


async def test_configured_timeout_is_applied():
    async with HoldedClient(API_KEY, timeout=2.5) as client:
        assert client._client.timeout == httpx.Timeout(2.5)


@pytest.mark.parametrize(
    "path",
    [
        "https://evil.invalid/",
        "https://api.holded.com/api/invoicing/v1/contacts",
        "//evil.invalid/api/invoicing/v1/contacts",
        "/api/invoicing/v1/../contacts",
        "/api/invoicing/v1/./contacts",
        "/api/invoicing/v1//contacts",
        "/api/invoicing/v1/contacts/",
        "/api/invoicing/v1/",
        "/api/invoicing/v1/contacts?foo=x",
        "/api/invoicing/v1/contacts#frag",
        "/api/invoicing/v1/contacts%2Fabc",
        "/api/invoicing/v1/contacts\\x",
        "/api/invoicing/v2/contacts",
        "/api/sales/v1/contacts",
        "/api/v3/contacts/{contactId}",
        "/api/v2/",
        "/api/v2",
        "/api/v2/../contacts",
        "/api/v2//contacts",
        "/api/v2/contacts/",
        "/api/v2/contacts?x=1",
        "/api/v2/contacts%2F{contactId}",
        "/api/crm/v2/contacts",
        "/v2/contacts",
        "/invoicing/v1/contacts",
        "/api/invoicing/v1/{invalid!}",
        "/api/invoicing/v1/contacts/{contactId",
        "/api/invoicing/v1/contacts/contactId}",
        "/api/invoicing/v1/contacts/{}",
        None,
        123,
    ],
)
async def test_operation_paths_cannot_escape_holded(path):
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError):
            await client.request(operation(path=path), path_params={"contactId": "abc"})


@pytest.mark.parametrize("method", ["HEAD", "OPTIONS", "TRACE", "get", None])
async def test_unsupported_methods_rejected(method):
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="method"):
            await client.request(operation(method), path_params={"contactId": "abc"})


@pytest.mark.parametrize("op", [None, [], "GET /api/invoicing/v1/contacts"])
async def test_operation_must_be_an_object(op):
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="Operation"):
            await client.request(op)


@pytest.mark.parametrize(
    "identifier",
    [
        "",
        ".",
        "..",
        "a/b",
        "a\\b",
        "a?b",
        "a#b",
        "%2e%2e",
        "abc%252f",
        "abc\n",
        "abc\x00",
        "abc\x7f",
        True,
        None,
        [],
        {},
        1.5,
    ],
)
async def test_unsafe_path_identifiers_rejected(identifier):
    op = operation()
    op["parameters"][0]["schema"] = {}
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError):
            await client.request(op, path_params={"contactId": identifier})


async def test_path_identifiers_are_url_encoded():
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(operation(), path_params={"contactId": "Café con leche"})
    assert requests[0].url.raw_path == b"/api/invoicing/v1/contacts/Caf%C3%A9%20con%20leche"


async def test_integer_path_identifiers_accepted_and_digit_strings_kept_verbatim():
    op = operation()
    op["parameters"][0]["schema"] = {"type": "integer", "minimum": 1}
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(op, path_params={"contactId": 42})
        await client.request(op, path_params={"contactId": "007"})
        with pytest.raises(HoldedError, match="path parameter contactId"):
            await client.request(op, path_params={"contactId": "0"})
        with pytest.raises(HoldedError, match="path parameter contactId"):
            await client.request(op, path_params={"contactId": "abc"})
    assert [request.url.path for request in requests] == [
        "/api/invoicing/v1/contacts/42",
        "/api/invoicing/v1/contacts/007",
    ]


async def test_doc_type_enum_is_enforced_before_network():
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="enum") as exc:
            await client.request(
                create_document_operation(),
                path_params={"docType": API_KEY},
                body={"date": 1767225600},
            )
    assert API_KEY not in str(exc.value)


async def test_create_document_sends_json_body():
    requests = []
    body = {
        "contactId": "5ab3a9e6d4c8a2001a1b2c3d",
        "date": 1767225600,
        "notes": None,
        "items": [{"name": "Consultoría", "units": 2, "subtotal": 150.5}],
    }
    payload = {"status": 1, "id": "65f0c0ffee", "invoiceNum": "F260001"}
    async with HoldedClient(API_KEY, transport=recording(requests, 201, payload)) as client:
        result = await client.request(
            create_document_operation(), path_params={"docType": "invoice"}, body=body
        )
    assert result == {"status": 201, "data": payload}
    request = requests[0]
    assert request.method == "POST"
    assert str(request.url) == "https://api.holded.com/api/invoicing/v1/documents/invoice"
    assert request.headers["content-type"] == "application/json"
    assert request.headers["key"] == API_KEY
    assert json.loads(request.content) == body


async def test_non_finite_json_numbers_are_not_sent():
    op = create_document_operation()
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError):
            await client.request(
                op,
                path_params={"docType": "invoice"},
                body={"date": 1767225600, "items": [{"subtotal": float("nan")}]},
            )


async def test_list_contacts_query_serialization():
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests, payload=[])) as client:
        await client.request(
            list_contacts_operation(),
            query={"phone": "+34 600 000 000", "customId": ["A-1", "B-2"], "page": 2},
        )
    params = requests[0].url.params
    assert params["phone"] == "+34 600 000 000"
    assert params.get_list("customId") == ["A-1", "B-2"]
    assert params["page"] == "2"
    assert "customId[]" not in params


@pytest.mark.parametrize(
    "kwargs",
    [
        {},
        {"path_params": {}},
        {"path_params": {"contactId": "abc", "unknown": "x"}},
        {"path_params": {"contactId": "abc"}, "query": {"unknown": API_KEY}},
        {"path_params": {"contactId": "abc"}, "query": {"includeArchived": "true"}},
        {"path_params": {"contactId": "abc"}, "query": {"customId": "A-1"}},
        {"path_params": {"contactId": "abc"}, "body": {}},
        {"path_params": {"contactId": "abc"}, "files": []},
        {"path_params": []},
        {"path_params": {1: "abc"}},
        {"path_params": {"contactId": "abc"}, "query": []},
    ],
)
async def test_invalid_arguments_never_reach_network(kwargs):
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError) as exc:
            await client.request(operation(), **kwargs)
    assert API_KEY not in str(exc.value)


async def test_required_query_and_body_validation():
    op = create_document_operation()
    op["body_schema"]["properties"]["dueDate"] = {"type": "integer", "minimum": 0}
    op["parameters"].append(
        {"in": "query", "name": "page", "required": True, "schema": {"type": "integer"}}
    )
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        for kwargs in (
            {},
            {"query": {"page": 1}},
            {"query": {"page": 1}, "body": {}},
            {"query": {"page": 1}, "body": "date=1"},
            {"query": {"page": 1}, "body": {"date": API_KEY}},
            {"query": {"page": 1}, "body": {"date": 1, "dueDate": -5}},
            {"query": {"page": True}, "body": {"date": 1}},
        ):
            with pytest.raises(HoldedError) as exc:
                await client.request(op, path_params={"docType": "invoice"}, **kwargs)
            assert API_KEY not in str(exc.value)


async def test_validation_errors_report_location_not_values():
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError) as exc:
            await client.request(
                create_document_operation(),
                path_params={"docType": "invoice"},
                body={"date": 1, "items": [{"name": "secret-value", "units": -1}]},
            )
    assert "items.0.units" in str(exc.value)
    assert "minimum" in str(exc.value)
    assert "-1" not in str(exc.value)


@pytest.mark.parametrize(
    "date_schema,date",
    [({"type": "not-a-type"}, 1), ({"type": "string", "pattern": "("}, "x"), ({"minimum": "a"}, 1)],
)
async def test_broken_documented_schema_is_reported_safely(date_schema, date):
    op = create_document_operation()
    op["body_schema"] = {"type": "object", "properties": {"date": date_schema}}
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="Cannot validate"):
            await client.request(op, path_params={"docType": "invoice"}, body={"date": date})


async def test_json_body_preserves_nested_types_and_allows_incomplete_schema_fields():
    requests = []
    body = {"date": 1, "approveDoc": False, "customFields": [{"field": "x", "value": [1, None]}]}
    async with HoldedClient(API_KEY, transport=recording(requests, 201)) as client:
        await client.request(
            create_document_operation(), path_params={"docType": "estimate"}, body=body
        )
    assert json.loads(requests[0].content) == body
    assert requests[0].headers["content-type"] == "application/json"


async def test_top_level_json_array_body():
    op = operation(
        "PUT",
        content_type="application/json",
        body_schema={"type": "array", "items": {"type": "string"}},
    )
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(op, path_params={"contactId": "abc"}, body=["a", "b"])
        with pytest.raises(HoldedError):
            await client.request(op, path_params={"contactId": "abc"}, body={"a": 1})
    assert json.loads(requests[0].content) == ["a", "b"]


async def test_query_booleans_styles_and_deep_objects():
    op = operation()
    op["parameters"].extend(
        [
            {"in": "query", "name": "fields", "schema": {"type": "object"}},
            {
                "in": "query",
                "name": "csv",
                "schema": {"type": "array"},
                "style": "form",
                "explode": False,
            },
            {
                "in": "query",
                "name": "spaces",
                "schema": {"type": "array"},
                "style": "spaceDelimited",
            },
            {"in": "query", "name": "pipes", "schema": {"type": "array"}, "style": "pipeDelimited"},
            {"in": "query", "name": "filter", "schema": {"type": "object"}, "style": "deepObject"},
            {"in": "query", "name": "starttmp", "schema": {"type": "integer"}},
            {"in": "query", "name": "missing", "schema": {"type": "string", "nullable": True}},
        ]
    )
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(
            op,
            path_params={"contactId": "abc"},
            query={
                "includeArchived": False,
                "customId": ["one", "two"],
                "fields": {"a": [1, 2]},
                "csv": [1, 2],
                "spaces": [1, 2],
                "pipes": [1, 2],
                "filter": {"active": True},
                "starttmp": 1767225600,
                "missing": None,
            },
        )
    params = requests[0].url.params
    assert params["includeArchived"] == "false"
    assert params.get_list("customId") == ["one", "two"]
    assert json.loads(params["fields"]) == {"a": [1, 2]}
    assert params["csv"] == "1,2"
    assert params["spaces"] == "1 2"
    assert params["pipes"] == "1|2"
    assert params["filter[active]"] == "true"
    assert params["starttmp"] == "1767225600"
    assert params["missing"] == "null"


async def test_unsupported_array_query_style_rejected():
    op = operation()
    op["parameters"].append(
        {"in": "query", "name": "matrix", "schema": {"type": "array"}, "style": "matrix"}
    )
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="serialization style"):
            await client.request(op, path_params={"contactId": "abc"}, query={"matrix": [1]})


async def test_nullable_openapi_schema_is_supported():
    op = operation(
        "PUT",
        content_type="application/json",
        body_schema={
            "type": "object",
            "properties": {"vatnumber": {"type": "string", "nullable": True}},
        },
    )
    async with HoldedClient(
        API_KEY, transport=httpx.MockTransport(lambda _: httpx.Response(200, json={}))
    ) as client:
        await client.request(op, path_params={"contactId": "abc"}, body={"vatnumber": None})
        with pytest.raises(HoldedError):
            await client.request(op, path_params={"contactId": "abc"}, body={"vatnumber": 1})


async def test_multipart_attach_uses_field_name_as_is_with_metadata():
    requests = []
    original = attach_operation()
    expected = copy.deepcopy(original)
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(
            original, path_params=ATTACH_PATH, body={"setMain": False}, files=[upload()]
        )
    request = requests[0]
    assert str(request.url) == (
        "https://api.holded.com/api/invoicing/v1/documents/invoice/5ab3a9e6d4c8a2001a1b2c3d/attach"
    )
    assert request.headers["content-type"].startswith("multipart/form-data; boundary=")
    assert request.headers["key"] == API_KEY
    assert b'name="file"; filename="invoice.pdf"' in request.content
    assert b"Content-Type: application/pdf" in request.content
    assert b"%PDF-1.4 hello" in request.content
    assert b'name="setMain"\r\n\r\nfalse' in request.content
    assert b"file[0]" not in request.content
    assert original == expected


async def test_multipart_array_property_accepts_indexed_fields_verbatim():
    op = attach_operation()
    op["body_schema"] = {
        "type": "object",
        "required": ["files"],
        "properties": {
            "files": {"type": "array", "items": {"type": "string", "format": "binary"}},
        },
    }
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(
            op,
            path_params=ATTACH_PATH,
            files=[upload(field="files[0]"), upload(field="files[1]", filename="second.pdf")],
        )
    assert b'name="files[0]"; filename="invoice.pdf"' in requests[0].content
    assert b'name="files[1]"; filename="second.pdf"' in requests[0].content


@pytest.mark.parametrize(
    "file",
    [
        upload(field="unknown"),
        upload(field="setMain"),
        upload(field="file[0]"),
        upload(field="file\r\nBad"),
        upload(field="x" * 129),
        upload(field=1),
        upload(filename="../secret"),
        upload(filename="dir\\secret.pdf"),
        upload(filename="x\x00.pdf"),
        upload(filename=""),
        upload(filename="a" * 256),
        upload(content_type="application/pdf\r\nBad"),
        upload(content_type="pdf"),
        upload(content_base64="not base64"),
        upload(content_base64="aGVsbG8=\n"),
        upload(content_base64=b"aGVsbG8="),
        upload(extra="x"),
        {"path": "/etc/passwd"},
        {"url": "https://evil.invalid"},
        "invoice.pdf",
    ],
)
async def test_invalid_uploads_rejected_without_file_or_network_access(file):
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError):
            await client.request(attach_operation(), path_params=ATTACH_PATH, files=[file])


async def test_single_file_property_cannot_be_repeated():
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="cannot be repeated"):
            await client.request(
                attach_operation(), path_params=ATTACH_PATH, files=[upload(), upload()]
            )


async def test_non_binary_documented_property_cannot_receive_upload():
    op = attach_operation()
    op["body_schema"]["properties"]["file"] = {"type": "string"}
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="binary"):
            await client.request(op, path_params=ATTACH_PATH, files=[upload()])


async def test_upload_total_limit_is_bounded(monkeypatch):
    monkeypatch.setattr("holded_mcp.client.MAX_UPLOAD_BYTES", 8)
    assert MAX_UPLOAD_BYTES == 10 * 1024 * 1024
    op = attach_operation()
    op["body_schema"]["properties"]["file"] = {
        "type": "array",
        "items": {"type": "string", "format": "binary"},
    }
    op["body_schema"]["required"] = []
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        for files in (
            [upload(field="file[0]"), upload(field="file[1]")],
            [upload(content_base64=base64.b64encode(b"a" * 10).decode())],
            [upload(content_base64="A" * 100)],
        ):
            with pytest.raises(HoldedError, match="10 MiB"):
                await client.request(op, path_params=ATTACH_PATH, files=files)


async def test_missing_upload_required_and_binary_in_body_rejected():
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        for kwargs in (
            {},
            {"files": []},
            {"body": {"setMain": True}},
            {"body": {"file": "fake"}},
            {"body": {"file": "fake"}, "files": [upload()]},
            {"body": {"setMain": "yes"}, "files": [upload()]},
            {"body": [], "files": [upload()]},
            {"files": {}},
        ):
            with pytest.raises(HoldedError):
                await client.request(attach_operation(), path_params=ATTACH_PATH, **kwargs)


async def test_form_body_uses_lowercase_boolean_and_json_objects():
    op = operation(
        "POST", content_type="application/x-www-form-urlencoded", body_schema={"type": "object"}
    )
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(
            op, path_params={"contactId": "abc"}, body={"enabled": False, "values": [1, 2]}
        )
    assert requests[0].content == b"enabled=false&values=%5B1%2C2%5D"
    assert requests[0].headers["content-type"] == "application/x-www-form-urlencoded"


async def test_unknown_content_type_rejected():
    op = operation("POST", content_type="application/xml", body_schema={"type": "object"})
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="content type"):
            await client.request(op, path_params={"contactId": "abc"}, body={"a": 1})


@pytest.mark.parametrize("method", ["GET", "DELETE"])
async def test_bodyless_operations_send_no_body_or_content_type(method):
    requests = []
    async with HoldedClient(API_KEY, transport=recording(requests)) as client:
        await client.request(operation(method), path_params={"contactId": "abc"})
    assert requests[0].method == method
    assert requests[0].content == b""
    assert "content-type" not in requests[0].headers


@pytest.mark.parametrize(
    "content_type", ["multipart/form-data", "application/x-www-form-urlencoded"]
)
async def test_non_json_transports_reject_array_metadata(content_type):
    op = operation("POST", content_type=content_type, body_schema={"type": "array"})
    async with HoldedClient(API_KEY, transport=no_network()) as client:
        with pytest.raises(HoldedError, match="object"):
            await client.request(op, path_params={"contactId": "abc"}, body=[])
