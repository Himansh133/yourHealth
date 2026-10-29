import uuid
from datetime import date, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.permissions import require_profile_access
from app.db.models import User
from app.db.session import get_db
from app.services.sheet import Sheet, build_sheet

router = APIRouter()

DEFAULT_PERIOD = timedelta(days=182)  # plan 13.1: last 6 months


@router.get("/profiles/{pid}/sheet", response_model=Sheet)
def preview_sheet(
    pid: uuid.UUID,
    from_: date | None = Query(default=None, alias="from"),
    to: date | None = None,
    include_medicines: bool = True,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    require_profile_access(db, user.id, pid, "view")
    to = to or date.today()
    return build_sheet(db, pid, from_ or to - DEFAULT_PERIOD, to, include_medicines)
