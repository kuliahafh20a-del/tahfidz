"""Minimal S3-compatible signing and trusted object metadata inspection."""

from __future__ import annotations

import base64
import hashlib
import hmac
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import httpx

from app.core.config import Settings


class ObjectStorageError(RuntimeError):
    pass


class ObjectNotFoundError(ObjectStorageError):
    pass


@dataclass(frozen=True, slots=True)
class SignedObjectRequest:
    url: str
    required_headers: dict[str, str]
    expires_at: datetime


@dataclass(frozen=True, slots=True)
class ObjectMetadata:
    content_type: str
    size_bytes: int
    checksum_sha256: str | None


class S3ObjectStorage:
    """Generate SigV4 URLs without ever writing them to durable storage or logs."""

    def __init__(self, settings: Settings) -> None:
        self.internal_endpoint = settings.object_storage_endpoint
        self.public_endpoint = settings.object_storage_public_endpoint
        self.bucket = settings.object_storage_bucket
        self.region = settings.object_storage_region
        self.access_key = settings.object_storage_access_key_value
        self.secret_key = settings.object_storage_secret_key_value
        self.ttl_seconds = settings.signed_url_ttl_seconds

    def upload_request(
        self,
        storage_key: str,
        content_type: str,
        checksum_hex: str,
        *,
        now: datetime | None = None,
    ) -> SignedObjectRequest:
        checksum_base64 = base64.b64encode(bytes.fromhex(checksum_hex)).decode("ascii")
        headers = {
            "Content-Type": content_type,
            "x-amz-checksum-sha256": checksum_base64,
        }
        instant = now or datetime.now(UTC)
        return SignedObjectRequest(
            url=self._presign(
                self.public_endpoint,
                "PUT",
                storage_key,
                headers,
                instant,
            ),
            required_headers=headers,
            expires_at=instant + timedelta(seconds=self.ttl_seconds),
        )

    def playback_request(
        self, storage_key: str, *, now: datetime | None = None
    ) -> SignedObjectRequest:
        instant = now or datetime.now(UTC)
        return SignedObjectRequest(
            url=self._presign(self.public_endpoint, "GET", storage_key, {}, instant),
            required_headers={},
            expires_at=instant + timedelta(seconds=self.ttl_seconds),
        )

    async def inspect_object(self, storage_key: str) -> ObjectMetadata:
        headers = {"x-amz-checksum-mode": "ENABLED"}
        url = self._presign(
            self.internal_endpoint,
            "HEAD",
            storage_key,
            headers,
            datetime.now(UTC),
        )
        try:
            async with httpx.AsyncClient(timeout=10.0, follow_redirects=False) as client:
                response = await client.head(url, headers=headers)
        except httpx.HTTPError as error:
            raise ObjectStorageError("object storage is unavailable") from error
        if response.status_code == 404:
            raise ObjectNotFoundError("object was not found")
        if response.status_code >= 400:
            raise ObjectStorageError("object storage rejected metadata inspection")
        try:
            size_bytes = int(response.headers["content-length"])
        except (KeyError, ValueError) as error:
            raise ObjectStorageError("object metadata is incomplete") from error
        checksum = response.headers.get("x-amz-checksum-sha256")
        return ObjectMetadata(
            content_type=response.headers.get("content-type", "").partition(";")[0].strip().lower(),
            size_bytes=size_bytes,
            checksum_sha256=checksum,
        )

    def _presign(
        self,
        endpoint: str,
        method: str,
        storage_key: str,
        headers: dict[str, str],
        now: datetime,
    ) -> str:
        instant = now.astimezone(UTC)
        date_stamp = instant.strftime("%Y%m%d")
        amz_date = instant.strftime("%Y%m%dT%H%M%SZ")
        credential_scope = f"{date_stamp}/{self.region}/s3/aws4_request"
        parsed = urlsplit(endpoint)
        canonical_uri = self._object_path(parsed.path, storage_key)

        normalized_headers = {
            key.lower(): " ".join(value.strip().split()) for key, value in headers.items()
        }
        normalized_headers["host"] = parsed.netloc.lower()
        signed_headers = ";".join(sorted(normalized_headers))
        canonical_headers = "".join(
            f"{key}:{normalized_headers[key]}\n" for key in sorted(normalized_headers)
        )
        parameters = {
            "X-Amz-Algorithm": "AWS4-HMAC-SHA256",
            "X-Amz-Credential": f"{self.access_key}/{credential_scope}",
            "X-Amz-Date": amz_date,
            "X-Amz-Expires": str(self.ttl_seconds),
            "X-Amz-SignedHeaders": signed_headers,
        }
        canonical_query = urlencode(sorted(parameters.items()), quote_via=quote, safe="-_.~")
        canonical_request = "\n".join(
            (
                method,
                canonical_uri,
                canonical_query,
                canonical_headers,
                signed_headers,
                "UNSIGNED-PAYLOAD",
            )
        )
        string_to_sign = "\n".join(
            (
                "AWS4-HMAC-SHA256",
                amz_date,
                credential_scope,
                hashlib.sha256(canonical_request.encode()).hexdigest(),
            )
        )
        signature = hmac.new(
            self._signing_key(date_stamp), string_to_sign.encode(), hashlib.sha256
        ).hexdigest()
        query = f"{canonical_query}&X-Amz-Signature={signature}"
        return urlunsplit((parsed.scheme, parsed.netloc, canonical_uri, query, ""))

    def _object_path(self, endpoint_path: str, storage_key: str) -> str:
        raw_path = "/".join(
            part for part in (endpoint_path.strip("/"), self.bucket, storage_key) if part
        )
        return "/" + quote(raw_path, safe="/-_.~")

    def _signing_key(self, date_stamp: str) -> bytes:
        date_key = hmac.new(
            f"AWS4{self.secret_key}".encode(), date_stamp.encode(), hashlib.sha256
        ).digest()
        region_key = hmac.new(date_key, self.region.encode(), hashlib.sha256).digest()
        service_key = hmac.new(region_key, b"s3", hashlib.sha256).digest()
        return hmac.new(service_key, b"aws4_request", hashlib.sha256).digest()
