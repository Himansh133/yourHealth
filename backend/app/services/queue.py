"""Background job queue (Redis + RQ). Upload enqueues; the worker processes (plan 7.1)."""
import uuid
from functools import lru_cache
from typing import Protocol

from redis import Redis
from rq import Queue

from app.core.config import settings

DOCUMENT_TIMEOUT_SECONDS = 180  # plan 7.2: 3-minute limit per document


class DocumentQueue(Protocol):
    def enqueue_document(self, document_id: uuid.UUID) -> None: ...


class RQDocumentQueue:
    def __init__(self, queue: Queue):
        self._queue = queue

    def enqueue_document(self, document_id: uuid.UUID) -> None:
        # By import path, so the API process never imports the heavy extraction code.
        self._queue.enqueue(
            "app.workers.process_document.process_document",
            str(document_id),
            job_timeout=DOCUMENT_TIMEOUT_SECONDS,
        )


@lru_cache
def get_queue() -> DocumentQueue:
    return RQDocumentQueue(Queue("documents", connection=Redis.from_url(settings.redis_url)))
