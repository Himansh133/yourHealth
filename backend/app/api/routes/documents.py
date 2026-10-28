import hashlib
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.permissions import require_profile_access
from app.db.models import Document, DocumentPage, LabResult, User
from app.db.session import get_db
from app.services.extraction.validate import MAX_BYTES, UploadRejected, validate_upload
from app.services.labs.store import refresh_review_status
from app.services.queue import DocumentQueue, get_queue
from app.services.storage import Storage, get_storage

router = APIRouter()

_EXT = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png"}


class DocumentOut(BaseModel):
    model_config = {"from_attributes": True}

    id: uuid.UUID
    profile_id: uuid.UUID
    source_channel: str
    original_filename: str | None
    mime_type: str
    size_bytes: int
    doc_type: str
    lab_name: str | None
    report_date: date | None
    status: str
    error_code: str | None
    created_at: datetime


def _load(db: Session, user: User, did: uuid.UUID, need) -> Document:
    doc = db.get(Document, did)
    if doc is None:
        raise HTTPException(404, "Document not found")
    require_profile_access(db, user.id, doc.profile_id, need)
    return doc


@router.post("/profiles/{pid}/documents", status_code=201, response_model=DocumentOut)
def upload_document(
    pid: uuid.UUID,
    file: UploadFile,
    response: Response,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
    queue: DocumentQueue = Depends(get_queue),
):
    require_profile_access(db, user.id, pid, "edit")
    data = file.file.read(MAX_BYTES + 1)  # one extra byte is enough to detect "too large"
    try:
        mime, _pages = validate_upload(data)
    except UploadRejected as e:
        raise HTTPException(422, {"code": e.code, "message": e.message})

    sha = hashlib.sha256(data).hexdigest()
    existing = db.scalar(select(Document).where(Document.profile_id == pid, Document.sha256 == sha))
    if existing:
        response.status_code = 200
        return existing

    doc_id = uuid.uuid4()
    key = f"docs/{doc_id}.{_EXT[mime]}"
    storage.put(key, data, mime)
    doc = Document(
        id=doc_id,
        profile_id=pid,
        uploaded_by=user.id,
        source_channel="web",
        storage_key=key,
        original_filename=(file.filename or "")[:255] or None,
        mime_type=mime,
        size_bytes=len(data),
        sha256=sha,
    )
    db.add(doc)
    db.commit()
    queue.enqueue_document(doc.id)  # after commit, so the worker can see the row
    return doc


@router.get("/profiles/{pid}/documents", response_model=list[DocumentOut])
def list_documents(pid: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "view")
    return db.scalars(
        select(Document).where(Document.profile_id == pid).order_by(Document.created_at.desc())
    ).all()


@router.get("/documents/{did}", response_model=DocumentOut)
def get_document(did: uuid.UUID, user: User = Depends(current_user), db: Session = Depends(get_db)):
    return _load(db, user, did, "view")


class DocumentPatch(BaseModel):
    report_date: date


@router.patch("/documents/{did}", response_model=DocumentOut)
def update_document(
    did: uuid.UUID, body: DocumentPatch, user: User = Depends(current_user), db: Session = Depends(get_db)
):
    """Set the report date when the report didn't print one (or it was read wrong)."""
    if body.report_date > date.today():
        raise HTTPException(422, {"code": "future_date", "message": "Report date can't be in the future."})
    doc = _load(db, user, did, "edit")
    doc.report_date = body.report_date
    db.execute(update(LabResult).where(LabResult.document_id == doc.id).values(observed_on=body.report_date))
    refresh_review_status(db, doc)
    db.commit()
    return doc


@router.get("/documents/{did}/file")
def download_document(
    did: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    doc = _load(db, user, did, "view")
    # No filename in the header: user-supplied names would need escaping, and the browser doesn't need it.
    return Response(storage.get(doc.storage_key), media_type=doc.mime_type, headers={"Content-Disposition": "inline"})


class PageOut(BaseModel):
    page_no: int
    method: str
    text: str
    ocr_confidence: float | None
    words: list[dict]


@router.get("/documents/{did}/pages/{n}", response_model=PageOut)
def get_page(did: uuid.UUID, n: int, user: User = Depends(current_user), db: Session = Depends(get_db)):
    """Page text and word boxes, so the review screen can highlight where a value was read."""
    _load(db, user, did, "view")
    page = db.scalar(select(DocumentPage).where(DocumentPage.document_id == did, DocumentPage.page_no == n))
    if page is None:
        raise HTTPException(404, "Page not found")
    return PageOut(page_no=page.page_no, method=page.method, text=page.text,
                   ocr_confidence=page.ocr_confidence, words=page.words_json or [])


@router.delete("/documents/{did}", status_code=204)
def delete_document(
    did: uuid.UUID,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
    storage: Storage = Depends(get_storage),
):
    doc = _load(db, user, did, "edit")
    db.delete(doc)
    db.commit()
    storage.delete(doc.storage_key)
