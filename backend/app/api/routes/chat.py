import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.permissions import require_profile_access
from app.db.models import User
from app.db.session import get_db
from app.services.chat.llm import LLM, LLMError, get_llm
from app.services.chat.service import ChatOut, answer_chat

router = APIRouter()


class _Unconfigured:
    def complete_json(self, system: str, user: str) -> str:
        raise LLMError("LLM is not configured")


def chat_llm() -> LLM:
    """Without a configured LLM, answers fall back to the table of retrieved facts."""
    try:
        return get_llm()
    except LLMError:
        return _Unconfigured()


class ChatIn(BaseModel):
    question: str = Field(max_length=500)
    lang: Literal["en", "hi"] = "en"

    @field_validator("question")
    @classmethod
    def not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must not be blank")
        return v.strip()


@router.post("/profiles/{pid}/chat", response_model=ChatOut, response_model_exclude_none=True)
def chat(pid: uuid.UUID, body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db),
         llm: LLM = Depends(chat_llm)):
    require_profile_access(db, user.id, pid, "view")
    return answer_chat(db, pid, body.question, body.lang, llm)
