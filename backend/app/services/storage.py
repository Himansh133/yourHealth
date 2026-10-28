"""Private file storage for original uploads. The original file is the source of truth (plan 5.3)."""
from typing import Protocol


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


_default = MemoryStorage()  # replaced by MinIO in the next slice


def get_storage() -> Storage:
    return _default
