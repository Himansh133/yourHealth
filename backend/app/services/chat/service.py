"""The chat pipeline (plan 10.2): route the question, gather evidence from the right tools, answer, validate.
Used by the web chat endpoint and by WhatsApp questions."""
import uuid
from typing import Literal

from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.models import Profile
from app.services.chat.answer import ChatAnswer, answer_question
from app.services.chat.doc_search import search_chunks
from app.services.chat.embeddings import get_embedder, get_reranker
from app.services.chat.lab_tool import LabFact, lab_lookup
from app.services.chat.llm import LLM
from app.services.chat.medicine_tool import MedicineFact, medicine_facts, medicine_vocabulary
from app.services.chat.router import classify, find_tests, route
from app.services.chat.validator import Claim, Evidence
from app.services.labs.dictionary import get_lab_dictionary
from app.services.medicines.store import effects_for, medicine_ingredients

EVIDENCE_NOTES = {
    "value": "The lab results below are the most recent value of each test asked about, from all of the reports. "
             "\"Last\", \"latest\" and \"पिछला\" mean this value.",
    "trend": "The lab results below are every value of the test, oldest first.",
}

SAFETY_SUMMARY = ("Choosing or changing a medicine depends on things this app can't see, like other conditions, "
                  "allergies, kidney function or pregnancy, so it is your doctor's call.")
OUT_OF_SCOPE = ("I can only answer from the reports and medicines saved here, and I can't diagnose. "
                "Please ask a doctor about this.")
SAFETY_NOTE = "Want me to make a doctor visit sheet with this value flagged?"


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


def answer_chat(db: Session, pid: uuid.UUID, question: str, lang: str, llm: LLM) -> ChatOut:
    """The caller has already checked that the asker may view this profile."""
    name = db.get(Profile, pid).display_name
    vocab = medicine_vocabulary(db)
    r = route(question, get_lab_dictionary(), set(vocab))
    labels, tests = r.labels, r.tests
    if not labels:
        c = classify(llm, question)
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
                  for h in search_chunks(db, pid, question, embedder=get_embedder(), reranker=get_reranker())]

    evidence = [Evidence(id=f"E{i}", text=text) for i, (text, _) in enumerate(found, 1)]
    sources = [Source(id=e.id, **fields) for e, (_, fields) in zip(evidence, found)]

    if label == "out_of_scope":
        answer = ChatAnswer(answerable=False, summary=OUT_OF_SCOPE, claims=[], missing_info=[], doctor_note="")
    elif label == "treatment":
        answer = ChatAnswer(answerable=True, summary=SAFETY_SUMMARY, missing_info=[], doctor_note=SAFETY_NOTE,
                            claims=[Claim(text=e.text, evidence_ids=[e.id]) for e in evidence])
    else:
        answer = answer_question(llm, question, name, evidence, lang, note=EVIDENCE_NOTES.get(label))
    return ChatOut(**answer.model_dump(), route=labels, sources=sources)
