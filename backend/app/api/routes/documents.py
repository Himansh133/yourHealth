import hashlib
import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.permissions import require_profile_access
from app.db.models import Document, User
from app.db.session import get_db
from app.services.extraction.validate import MAX_BYTES, UploadRejected, validate_upload
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
