"""Audit log (plan 6.7). Ids and outcomes only, never medical text."""
import uuid

from sqlalchemy.orm import Session

from app.db.models import AuditEvent


def record(db: Session, action: str, outcome: str, *, actor_kind: str, profile_id: uuid.UUID | None = None,
           actor_user_id: uuid.UUID | None = None, resource_id: uuid.UUID | None = None,
           meta: dict | None = None) -> None:
    db.add(AuditEvent(action=action, outcome=outcome, actor_kind=actor_kind, profile_id=profile_id,
                      actor_user_id=actor_user_id, resource_id=resource_id, meta=meta))
