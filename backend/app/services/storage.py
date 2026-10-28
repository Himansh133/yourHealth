"""Private file storage for original uploads. The original file is the source of truth (plan 5.3)."""
from functools import lru_cache
from typing import Protocol

import boto3
from botocore.exceptions import ClientError

from app.core.config import settings


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...
    def get(self, key: str) -> bytes: ...
    def delete(self, key: str) -> None: ...


class MemoryStorage:
    """In-process store for tests."""

    def __init__(self):
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.objects[key] = data

    def get(self, key: str) -> bytes:
        return self.objects[key]

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


class S3Storage:
    """Any S3-compatible store (SeaweedFS locally). Buckets are private: no public policy is ever set."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str, bucket: str):
        self.bucket = bucket
        self._s3 = boto3.client(
            "s3",
            endpoint_url=endpoint,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name="us-east-1",
        )
        try:
            self._s3.head_bucket(Bucket=bucket)
        except ClientError:
            self._s3.create_bucket(Bucket=bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._s3.put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        try:
            return self._s3.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except ClientError as e:
            if e.response["Error"]["Code"] in ("NoSuchKey", "404"):
                raise KeyError(key) from e
            raise

    def delete(self, key: str) -> None:
        self._s3.delete_object(Bucket=self.bucket, Key=key)  # S3 delete is already a no-op if missing


@lru_cache
def get_storage() -> Storage:
    return S3Storage(settings.s3_endpoint, settings.s3_access_key, settings.s3_secret_key, settings.s3_bucket)
