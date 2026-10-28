"""Medium test: needs the `s3` service from docker-compose running."""
import uuid

import pytest

from app.core.config import settings
from app.services.storage import S3Storage


@pytest.fixture
def s3():
    store = S3Storage(
        endpoint=settings.s3_endpoint,
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        bucket=f"test-{uuid.uuid4().hex[:12]}",
    )
    yield store
    client = store._s3
    for obj in client.list_objects_v2(Bucket=store.bucket).get("Contents", []):
        client.delete_object(Bucket=store.bucket, Key=obj["Key"])
    client.delete_bucket(Bucket=store.bucket)


def test_put_get_roundtrip(s3):
    s3.put("docs/a.pdf", b"%PDF-1.7 hello", "application/pdf")
    assert s3.get("docs/a.pdf") == b"%PDF-1.7 hello"


def test_delete_removes_object(s3):
    s3.put("docs/a.pdf", b"x", "application/pdf")
    s3.delete("docs/a.pdf")
    with pytest.raises(KeyError):
        s3.get("docs/a.pdf")


def test_delete_missing_key_is_noop(s3):
    s3.delete("docs/never-existed.pdf")


def test_bucket_is_private(s3):
    import urllib.error
    import urllib.request

    s3.put("docs/secret.pdf", b"private", "application/pdf")
    url = f"{settings.s3_endpoint}/{s3.bucket}/docs/secret.pdf"
    with pytest.raises(urllib.error.HTTPError) as exc:
        urllib.request.urlopen(url)
    assert exc.value.code in (401, 403)
