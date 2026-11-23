"""Apply grant restrictions to ORM queries before ranking or clinical calculations."""
from contextlib import contextmanager
import uuid

from sqlalchemy import and_, event, false, or_
from sqlalchemy.orm import with_loader_criteria

from app.db.models import Allergy, Chunk, Document, LabResult, ProfileMedicine


@contextmanager
def clinical_scope(db, grant):
    pid = grant.profile_id
    excluded = [uuid.UUID(str(value)) for value in grant.scope.get('excluded_document_ids', [])]
    def allowed(model, category, document_column):
        clauses = [model.profile_id == pid]
        if not grant.scope.get(category, False):
            clauses.append(false())
        if excluded:
            clauses.append(or_(document_column.is_(None), document_column.not_in(excluded)))
        return and_(*clauses)
    document_clause = and_(Document.profile_id == pid, Document.id.not_in(excluded))
    options = [with_loader_criteria(Document, document_clause, include_aliases=True)]
    for model, category, column in [
        (Chunk, 'documents', Chunk.document_id), (LabResult, 'labs', LabResult.document_id),
        (ProfileMedicine, 'medicines', ProfileMedicine.source_document_id),
        (Allergy, 'allergies', Allergy.source_document_id),
    ]:
        options.append(with_loader_criteria(model, allowed(model, category, column), include_aliases=True))
    def restrict(execution):
        if execution.is_select:
            execution.statement = execution.statement.options(*options)
    event.listen(db, 'do_orm_execute', restrict)
    try:
        yield
    finally:
        event.remove(db, 'do_orm_execute', restrict)
