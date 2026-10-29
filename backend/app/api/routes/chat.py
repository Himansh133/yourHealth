import uuid
from typing import Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.permissions import require_profile_access
from app.db.models import Profile, User
from app.db.session import get_db
from app.services.chat.answer import ChatAnswer, answer_question
from app.services.chat.lab_tool import LabFact, lab_lookup
from app.services.chat.llm import LLM, LLMError, get_llm
from app.services.chat.router import route
from app.services.chat.validator import Claim, Evidence
from app.services.labs.dictionary import get_lab_dictionary
from app.services.medicines.store import medicine_ingredients

router = APIRouter()

SAFETY_SUMMARY = ("Choosing or changing a medicine depends on things this app can't see, like other conditions, "
                  "allergies, kidney function or pregnancy, so it is your doctor's call.")
SAFETY_NOTE = "Want me to make a doctor visit sheet with this value flagged?"
NOT_YET = "I can answer questions about test values and trends for now. Other questions are coming soon."


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


class Source(BaseModel):
    id: str
    kind: Literal["lab_result"]
    lab_result_id: uuid.UUID
    document_id: uuid.UUID
    page_no: int | None


class ChatOut(ChatAnswer):
    route: list[str]
    sources: list[Source]


@router.post("/profiles/{pid}/chat", response_model=ChatOut)
def chat(pid: uuid.UUID, body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db),
         llm: LLM = Depends(chat_llm)):
    require_profile_access(db, user.id, pid, "view")
    name = db.get(Profile, pid).display_name
    meds = {n.lower() for mi in medicine_ingredients(db, pid) for n in (mi.name, mi.ingredient.name)}
    r = route(body.question, get_lab_dictionary(), meds)
    label = r.labels[0] if r.labels else None

    facts: list[LabFact] = []
    if label in ("value", "trend", "treatment"):
        for t in r.tests:
            facts += lab_lookup(db, pid, t.loinc_code, "trend" if label == "trend" else "latest")
    evidence = [Evidence(id=f"E{i}", text=f.evidence_text()) for i, f in enumerate(facts, 1)]
    sources = [Source(id=e.id, kind="lab_result", lab_result_id=f.lab_result_id, document_id=f.document_id,
                      page_no=f.page_no) for e, f in zip(evidence, facts)]

    if label == "treatment":
        answer = ChatAnswer(answerable=True, summary=SAFETY_SUMMARY, missing_info=[], doctor_note=SAFETY_NOTE,
                            claims=[Claim(text=e.text, evidence_ids=[e.id]) for e in evidence])
    elif label in ("value", "trend"):
        answer = answer_question(llm, body.question, name, evidence, body.lang)
    else:
        answer = ChatAnswer(answerable=False, summary=NOT_YET, claims=[], missing_info=[], doctor_note="")
    return ChatOut(**answer.model_dump(), route=r.labels, sources=sources)
