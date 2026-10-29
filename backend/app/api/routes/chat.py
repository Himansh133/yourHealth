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
from app.services.chat.doc_search import search_chunks
from app.services.chat.lab_tool import LabFact, lab_lookup
from app.services.chat.llm import LLM, LLMError, get_llm
from app.services.chat.medicine_tool import MedicineFact, medicine_facts, medicine_vocabulary
from app.services.chat.router import classify, find_tests, route
from app.services.chat.validator import Claim, Evidence
from app.services.labs.dictionary import get_lab_dictionary
from app.services.medicines.store import effects_for, medicine_ingredients

router = APIRouter()

SAFETY_SUMMARY = ("Choosing or changing a medicine depends on things this app can't see, like other conditions, "
                  "allergies, kidney function or pregnancy, so it is your doctor's call.")
OUT_OF_SCOPE = ("I can only answer from the reports and medicines saved here, and I can't diagnose. "
                "Please ask a doctor about this.")
SAFETY_NOTE = "Want me to make a doctor visit sheet with this value flagged?"


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
    kind: Literal["lab_result", "medicine", "drug_label", "document"]
    lab_result_id: uuid.UUID | None = None
    document_id: uuid.UUID | None = None
    page_no: int | None = None
    medicine_id: uuid.UUID | None = None
    url: str | None = None


class ChatOut(ChatAnswer):
    route: list[str]
    sources: list[Source]


def _lab_source(f: LabFact) -> dict:
    return {"kind": "lab_result", "lab_result_id": f.lab_result_id, "document_id": f.document_id, "page_no": f.page_no}


def _medicine_source(f: MedicineFact) -> dict:
    if f.kind == "medicine":
        return {"kind": "medicine", "medicine_id": f.medicine_id}
    return {"kind": "drug_label", "url": f.url}


@router.post("/profiles/{pid}/chat", response_model=ChatOut, response_model_exclude_none=True)
def chat(pid: uuid.UUID, body: ChatIn, user: User = Depends(current_user), db: Session = Depends(get_db),
         llm: LLM = Depends(chat_llm)):
    require_profile_access(db, user.id, pid, "view")
    name = db.get(Profile, pid).display_name
    vocab = medicine_vocabulary(db)
    r = route(body.question, get_lab_dictionary(), set(vocab))
    labels, tests = r.labels, r.tests
    if not labels:
        c = classify(llm, body.question)
        labels = c.labels
        tests = find_tests(c.test, get_lab_dictionary()) if c.test else tests
    label = labels[0]
    if (label in ("value", "trend") and not tests) or (label == "medicine" and not r.medicines):
        label, labels = "document", ["document"]  # nothing specific to look up: their documents may mention it
    asked_ingredients = {i for m in r.medicines for i in vocab[m]}
    loinc_codes = {t.loinc_code for t in tests}

    found: list[tuple[str, dict]] = []  # (evidence text, source fields)
    if label in ("value", "trend", "treatment", "medicine_lab"):
        mode = "latest" if label in ("value", "treatment") else "trend"
        for t in tests:
            found += [(f.evidence_text(), _lab_source(f)) for f in lab_lookup(db, pid, t.loinc_code, mode)]
    if label in ("medicine", "medicine_lab"):
        facts = medicine_facts(db, pid, asked_ingredients, loinc_codes if label == "medicine_lab" else None)
        found += [(f.text, _medicine_source(f)) for f in facts]
    if label == "treatment":
        # Plan 9.6: mention medicines they already take for this test, from their own list.
        taken = {mi.ingredient.id for mi in medicine_ingredients(db, pid)}
        linked = {e.ingredient_id for e, t in effects_for(db, taken) if t.loinc_code in loinc_codes}
        facts = medicine_facts(db, pid, linked | asked_ingredients)
        found += [(f.text, _medicine_source(f)) for f in facts if f.kind == "medicine"]
    if label == "document":
        found += [(h.evidence_text(), {"kind": "document", "document_id": h.document_id, "page_no": h.page_start})
                  for h in search_chunks(db, pid, body.question)]

    evidence = [Evidence(id=f"E{i}", text=text) for i, (text, _) in enumerate(found, 1)]
    sources = [Source(id=e.id, **fields) for e, (_, fields) in zip(evidence, found)]

    if label == "out_of_scope":
        answer = ChatAnswer(answerable=False, summary=OUT_OF_SCOPE, claims=[], missing_info=[], doctor_note="")
    elif label == "treatment":
        answer = ChatAnswer(answerable=True, summary=SAFETY_SUMMARY, missing_info=[], doctor_note=SAFETY_NOTE,
                            claims=[Claim(text=e.text, evidence_ids=[e.id]) for e in evidence])
    else:
        answer = answer_question(llm, body.question, name, evidence, body.lang)
    return ChatOut(**answer.model_dump(), route=labels, sources=sources)
