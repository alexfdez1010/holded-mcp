"""Validated, credential-safe transport for the published Holded API (v1 and v2)."""

from __future__ import annotations

import base64
import binascii
import json
import math
import re
from typing import Any
from urllib.parse import quote

import httpx
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError, UnknownType

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
MAX_DOWNLOAD_BYTES = 10 * 1024 * 1024
APIS = ("invoicing", "crm", "projects", "team", "accounting")
_ORIGIN = "https://api.holded.com"
_V1_PATH = re.compile(r"/api/(?:" + "|".join(APIS) + r")/v1/[A-Za-z0-9_{}./-]+")
_V2_PATH = re.compile(r"/api/v2/[A-Za-z0-9_{}./-]+")
_PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")
_CONTROL = re.compile(r"[\x00-\x1f\x7f]")
_FIELD = re.compile(r"[A-Za-z0-9_.-]+(?:\[(?:[0-9]*)\])?\Z")
_MIME = re.compile(r"[A-Za-z0-9!#$&^_.+-]+/[A-Za-z0-9!#$&^_.+-]+\Z")


class HoldedError(ValueError):
    """A safe error with optional HTTP and rate-limit metadata."""

    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        retry_after: str | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.retry_after = retry_after


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return "null"
    if isinstance(value, (dict, list)):
        return json.dumps(value, separators=(",", ":"), allow_nan=False)
    return str(value)


def _schema_for_validation(schema: Any) -> Any:
    """Support OpenAPI 3.0 nullable alongside JSON Schema's native types."""
    if isinstance(schema, list):
        return [_schema_for_validation(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    result = {key: _schema_for_validation(value) for key, value in schema.items()}
    if result.get("nullable") is True:
        result.pop("nullable")
        return {"anyOf": [result, {"type": "null"}]}
    return result


def api_version(operation: dict[str, Any]) -> str:
    """Return "v1" or "v2" from the operation path, rejecting any other destination.

    The path decides how the key is sent: v1 uses Holded's `key` header and v2 uses
    `Authorization: Bearer`. A declared `version` must agree with the path.
    """
    path = operation.get("path")
    if isinstance(path, str) and _V2_PATH.fullmatch(path):
        version = "v2"
    elif isinstance(path, str) and _V1_PATH.fullmatch(path):
        version = "v1"
    else:
        raise HoldedError("Invalid Holded API path.")
    if operation.get("version", version) != version:
        raise HoldedError("Operation version does not match its API path.")
    return version


class HoldedClient:
    """Send requests only to Holded, sending the API key once per request: in the `key`
    header for v1 operations or as `Authorization: Bearer` for v2 operations."""

    def __init__(
        self,
        api_key: str,
        *,
        timeout: float = 30,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if (
            not isinstance(api_key, str)
            or not api_key
            or api_key != api_key.strip()
            or any(ord(char) < 33 or ord(char) > 126 for char in api_key)
        ):
            raise HoldedError("HOLDED_API_KEY must be a nonempty ASCII key without whitespace.")
        if (
            isinstance(timeout, bool)
            or not isinstance(timeout, (int, float))
            or not math.isfinite(timeout)
            or timeout <= 0
        ):
            raise HoldedError("Request timeout must be a positive finite number.")
        self._api_key = api_key
        self._client = httpx.AsyncClient(
            # No client-wide credential: each request carries exactly one auth header.
            headers={"Accept": "application/json, */*;q=0.8"},
            timeout=timeout,
            transport=transport,
            follow_redirects=False,
            trust_env=False,
        )

    async def __aenter__(self) -> HoldedClient:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    def _redact(self, value: Any) -> Any:
        if isinstance(value, str):
            return value.replace(self._api_key, "[REDACTED]")
        if isinstance(value, list):
            return [self._redact(item) for item in value]
        if isinstance(value, dict):
            return {self._redact(key): self._redact(item) for key, item in value.items()}
        return value

    def _validate(self, value: Any, schema: dict[str, Any] | None, label: str) -> None:
        if not schema:
            return
        try:
            validator = Draft202012Validator(_schema_for_validation(schema))
            error = next(validator.iter_errors(value), None)
        except (SchemaError, UnknownType, re.error, ValueError, TypeError, RecursionError):
            raise HoldedError(f"Cannot validate the documented schema for {label}.") from None
        if error is not None:
            location = ".".join(str(part) for part in error.absolute_path)
            suffix = f" at {location}" if location else ""
            # jsonschema messages include supplied values; report constraints only.
            raise HoldedError(
                self._redact(f"Invalid {label}{suffix}: failed {error.validator} validation.")
            )

    @staticmethod
    def _parameters(values: dict[str, Any] | None, label: str) -> dict[str, Any]:
        if values is None:
            return {}
        if not isinstance(values, dict) or any(not isinstance(key, str) for key in values):
            raise HoldedError(f"{label} must be an object with string keys.")
        return values

    def _url_and_query(
        self,
        operation: dict[str, Any],
        path_params: dict[str, Any],
        query: dict[str, Any],
    ) -> tuple[str, list[tuple[str, str]]]:
        method, path = operation.get("method"), operation.get("path")
        if method not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
            raise HoldedError("Unsupported API method.")
        api_version(operation)
        if any(part in {".", "..", ""} for part in path.split("/")[1:]):
            raise HoldedError("Invalid Holded API path.")
        names = set(_PLACEHOLDER.findall(path))
        if "{" in _PLACEHOLDER.sub("", path) or "}" in _PLACEHOLDER.sub("", path):
            raise HoldedError("Invalid API path placeholder.")
        declared: dict[str, dict[str, Any]] = {location: {} for location in ("path", "query")}
        for parameter in operation.get("parameters", []):
            location = parameter.get("in")
            if location in declared:
                declared[location][parameter["name"]] = parameter
        if set(path_params) - names or names - set(path_params):
            raise HoldedError("Path parameters must exactly match the documented API path.")
        if set(query) - set(declared["query"]):
            raise HoldedError("Unknown query parameter; use the operation's documented parameters.")
        for location, supplied in (("path", path_params), ("query", query)):
            for name, parameter in declared[location].items():
                if parameter.get("required") and name not in supplied:
                    raise HoldedError(
                        self._redact(f"Missing required {location} parameter: {name}.")
                    )
                if name in supplied:
                    value = supplied[name]
                    schema = parameter.get("schema", {})
                    # Validate digit-only path IDs numerically without changing the wire ID.
                    if (
                        location == "path"
                        and schema.get("type") in ("integer", "number")
                        and isinstance(value, str)
                        and re.fullmatch(r"[0-9]+", value)
                    ):
                        value = int(value)
                    self._validate(value, schema, f"{location} parameter {name}")
        for name in names:
            value = path_params[name]
            if not isinstance(value, (str, int)) or isinstance(value, bool):
                raise HoldedError("Path identifiers must be strings or integers.")
            value = str(value)
            if (
                not value
                or value in {".", ".."}
                or any(char in value for char in "/\\%?#")
                or _CONTROL.search(value)
            ):
                raise HoldedError("Path identifier contains unsafe URL characters.")
            path = path.replace("{" + name + "}", quote(value, safe=""))
        pairs: list[tuple[str, str]] = []
        for name, value in query.items():
            parameter = declared["query"][name]
            style = parameter.get("style", "form")
            explode = parameter.get("explode", style == "form")
            if isinstance(value, list):
                if style == "form" and explode:
                    pairs.extend((name, _scalar(item)) for item in value)
                elif style in {"form", "spaceDelimited", "pipeDelimited"}:
                    delimiter = {"form": ",", "spaceDelimited": " ", "pipeDelimited": "|"}[style]
                    pairs.append((name, delimiter.join(_scalar(item) for item in value)))
                else:
                    raise HoldedError("Unsupported query array serialization style.")
            elif isinstance(value, dict):
                if style == "deepObject":
                    pairs.extend((f"{name}[{key}]", _scalar(item)) for key, item in value.items())
                else:
                    pairs.append((name, _scalar(value)))
            else:
                pairs.append((name, _scalar(value)))
        return _ORIGIN + path, pairs

    def _uploads(
        self,
        files: list[dict[str, Any]],
        schema: dict[str, Any] | None,
    ) -> tuple[list[tuple[str, tuple[str, bytes, str]]], dict[str, Any]]:
        if not isinstance(files, list):
            raise HoldedError("Files must be a list of upload objects.")
        result = []
        synthetic: dict[str, Any] = {}
        total = 0
        properties = (schema or {}).get("properties", {})
        for file in files:
            if not isinstance(file, dict) or set(file) != {
                "field",
                "filename",
                "content_base64",
                "content_type",
            }:
                raise HoldedError(
                    "Each file needs field, filename, content_base64, and content_type."
                )
            field, filename, encoded, content_type = (
                file[key] for key in ("field", "filename", "content_base64", "content_type")
            )
            if not isinstance(field, str) or len(field) > 128 or not _FIELD.fullmatch(field):
                raise HoldedError("Invalid multipart field name.")
            base_field = field.split("[", 1)[0]
            if base_field not in properties:
                raise HoldedError("Upload field is absent from the documented multipart schema.")
            field_schema = properties[base_field]
            is_array = field_schema.get("type") == "array"
            binary_schema = field_schema.get("items", {}) if is_array else field_schema
            if binary_schema.get("format") != "binary":
                raise HoldedError("Upload field must be a documented binary property.")
            if "[" in field and not is_array:
                raise HoldedError("Indexed file fields require an array upload property.")
            if (
                not isinstance(filename, str)
                or not filename
                or len(filename) > 255
                or _CONTROL.search(filename)
                or any(char in filename for char in "/\\")
            ):
                raise HoldedError(
                    "Upload filename must be a plain filename without path or control characters."
                )
            if not isinstance(content_type, str) or not _MIME.fullmatch(content_type):
                raise HoldedError("Upload content_type must be a valid MIME type.")
            if not isinstance(encoded, str) or len(encoded) > 4 * ((MAX_UPLOAD_BYTES + 2) // 3):
                raise HoldedError("Total decoded uploads must not exceed 10 MiB.")
            try:
                decoded = base64.b64decode(encoded, validate=True)
            except (ValueError, binascii.Error):
                raise HoldedError("Upload content_base64 must contain valid base64.") from None
            total += len(decoded)
            if total > MAX_UPLOAD_BYTES:
                raise HoldedError("Total decoded uploads must not exceed 10 MiB.")
            if is_array:
                synthetic.setdefault(base_field, []).append(filename)
            elif base_field in synthetic:
                raise HoldedError("A single-file upload property cannot be repeated.")
            else:
                synthetic[base_field] = filename
            result.append((field, (filename, decoded, content_type)))
        return result, synthetic

    async def request(
        self,
        operation: dict[str, Any],
        *,
        path_params: dict[str, Any] | None = None,
        query: dict[str, Any] | None = None,
        body: dict[str, Any] | list[Any] | None = None,
        files: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        """Validate and send one request; mutations are never automatically retried."""
        if not isinstance(operation, dict):
            raise HoldedError("Operation must be a documented API operation object.")
        url, params = self._url_and_query(
            operation,
            self._parameters(path_params, "Path parameters"),
            self._parameters(query, "Query parameters"),
        )
        if body is not None and not isinstance(body, (dict, list)):
            raise HoldedError("Request body must be an object or array.")
        schema, content_type = operation.get("body_schema"), operation.get("content_type")
        if body is not None and schema is None:
            raise HoldedError("This operation does not accept a request body.")
        if files is not None and content_type != "multipart/form-data":
            raise HoldedError("Files are only accepted by multipart upload operations.")
        if api_version(operation) == "v2":
            auth = {"Authorization": f"Bearer {self._api_key}"}
        else:
            auth = {"key": self._api_key}
        kwargs: dict[str, Any] = {"params": params, "headers": auth}
        if content_type == "multipart/form-data":
            if body is not None and not isinstance(body, dict):
                raise HoldedError("Multipart request metadata must be an object.")
            uploads, synthetic = self._uploads(files if files is not None else [], schema)
            values = dict(body or {})
            binary_fields = {
                name
                for name, field_schema in (schema or {}).get("properties", {}).items()
                if field_schema.get("format") == "binary"
                or field_schema.get("items", {}).get("format") == "binary"
            }
            if set(values) & (set(synthetic) | binary_fields):
                raise HoldedError("Provide binary fields through files only.")
            values.update(synthetic)
            if operation.get("body_required") and not values and not uploads:
                raise HoldedError("This operation requires a request body or upload.")
            self._validate(values, schema, "request body")
            if uploads or body:
                # Encode metadata as multipart text parts alongside uploaded files.
                kwargs["files"] = [
                    (name, (None, _scalar(value))) for name, value in (body or {}).items()
                ] + uploads
        else:
            if operation.get("body_required") and body is None:
                raise HoldedError("This operation requires a request body.")
            if body is not None:
                self._validate(body, schema, "request body")
                if content_type in (None, "application/json"):
                    kwargs["json"] = body
                elif content_type == "application/x-www-form-urlencoded":
                    if not isinstance(body, dict):
                        raise HoldedError("Form request body must be an object.")
                    kwargs["data"] = {name: _scalar(value) for name, value in body.items()}
                else:
                    raise HoldedError("Unsupported documented request content type.")
        try:
            response = await self._client.request(operation["method"], url, **kwargs)
        except httpx.TimeoutException:
            raise HoldedError(
                "Holded request timed out; check the resource before retrying a mutation."
            ) from None
        except httpx.RequestError:
            raise HoldedError(
                "Could not connect to Holded; check connectivity before retrying."
            ) from None
        except (ValueError, TypeError, RuntimeError):
            raise HoldedError("Could not serialize or send the Holded request.") from None
        media_type = response.headers.get("content-type", "").split(";", 1)[0].strip().lower()
        if not response.content:
            data = None
        elif (
            not response.is_error
            and media_type
            and not media_type.startswith("text/")
            and media_type != "application/json"
            and not media_type.endswith("+json")
        ):
            # Binary downloads (PDFs, attachments, previews) are returned as base64 so their
            # bytes survive JSON transport intact.
            if len(response.content) > MAX_DOWNLOAD_BYTES:
                raise HoldedError(
                    f"Holded returned a {media_type} file larger than 10 MiB; "
                    "download it from Holded directly."
                )
            data = {
                "content_type": media_type,
                "size": len(response.content),
                "content_base64": base64.b64encode(response.content).decode("ascii"),
            }
        else:
            try:
                data = response.json()
            except ValueError:
                data = response.text
        data = self._redact(data)
        if response.is_error or response.is_redirect:
            retry_after = self._redact(response.headers.get("retry-after"))
            detail = (
                json.dumps(data, ensure_ascii=True)
                if isinstance(data, (dict, list))
                else str(data or "")
            )
            message = f"Holded API returned HTTP {response.status_code}: {detail[:1000]}"
            if response.status_code == 429:
                message += (
                    f". Rate limited; Retry-After={retry_after or 'unavailable'}. "
                    "Retry explicitly when allowed."
                )
            raise HoldedError(message, status_code=response.status_code, retry_after=retry_after)
        return {"status": response.status_code, "data": data}
