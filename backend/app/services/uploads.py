"""Accepting a report file, from the web or WhatsApp: validate, de-duplicate per profile, store, queue (plan 7.1)."""
import hashlib
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Document
from app.services.extraction.validate import validate_upload
from app.services.queue import DocumentQueue
from app.services.storage import Storage

_EXT = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}


def store_upload(db: Session, storage: Storage, queue: DocumentQueue, profile_id: uuid.UUID, user_id: uuid.UUID,
                 data: bytes, filename: str | None, channel: str) -> tuple[Document, bool]:
    """Returns (document, created). The same file already on this profile returns the existing one.
    Raises UploadRejected for files we can't take."""
    mime, _pages = validate_upload(data)
    sha = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.profile_id == profile_id, Document.sha256 == sha))
    if existing:
        return existing, False

    doc_id = uuid.uuid4()
    key = f"docs/{doc_id}.{_EXT[mime]}"
    storage.put(key, data, mime)
    doc = Document(id=doc_id, profile_id=profile_id, uploaded_by=user_id, source_channel=channel, storage_key=key,
                   original_filename=(filename or "")[:255] or None, mime_type=mime, size_bytes=len(data), sha256=sha)
    db.add(doc)
    db.commit()
    queue.enqueue_document(doc.id)  # after commit, so the worker can see the row
    return doc, True
