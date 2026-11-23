import uuid
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import patient_user
from app.core.permissions import require_profile_access
from app.db.models import ChatRecord, User
from app.db.session import get_db
from app.services.chat.llm import LLM, get_llm_or_unavailable
from app.services.chat.service import ChatOut, answer_chat

router = APIRouter()


def chat_llm() -> LLM:
    return get_llm_or_unavailable()


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
def chat(pid: uuid.UUID, body: ChatIn, user: User = Depends(patient_user), db: Session = Depends(get_db),
         llm: LLM = Depends(chat_llm)):
    require_profile_access(db, user.id, pid, "view")
    answer = answer_chat(db, pid, body.question, body.lang, llm)
    record = ChatRecord(profile_id=pid, user_id=user.id, question=body.question, answer=answer.model_dump(mode="json"))
    db.add(record)
    db.commit()
    answer.answer_id = record.id
    return answer


class FeedbackIn(BaseModel):
    category: Literal["helpful", "too_long", "wrong_evidence", "missed_question"]


class FeedbackOut(FeedbackIn):
    answer_id: uuid.UUID


@router.put("/profiles/{pid}/chat/{aid}/feedback", response_model=FeedbackOut)
def save_feedback(pid: uuid.UUID, aid: uuid.UUID, body: FeedbackIn,
                  user: User = Depends(patient_user), db: Session = Depends(get_db)):
    require_profile_access(db, user.id, pid, "view")
    record = db.scalar(select(ChatRecord).where(ChatRecord.id == aid, ChatRecord.profile_id == pid,
                                               ChatRecord.user_id == user.id))
    if record is None:
        raise HTTPException(404, "Answer not found")
    record.feedback = body.category
    db.commit()
    return FeedbackOut(answer_id=record.id, category=record.feedback)
