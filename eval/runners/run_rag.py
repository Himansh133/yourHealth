"""Answer the generated questions with one system and save the answers (plan 14.4, 14.5).

  b0    plain LLM: all of the profile's report text in the prompt, no retrieval, no validator
  b1    vector RAG: the 6 nearest chunks by meaning, no router, no SQL, no validator
  ours  the app's chat endpoint: router, SQL tool, medicine tool, hybrid search, reranker, validator

All use the same LLM. Usage (from backend/, after load_eval_db):
  DATABASE_URL=postgresql+psycopg://yourhealth:yourhealth@localhost:5432/yourhealth_eval COOKIE_SECURE=false \\
    PYTHONPATH=.. .venv/bin/python -m eval.runners.run_rag --system ours --split test
"""
import argparse
import json
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.db.models import Chunk, Document, DocumentPage, LabResult, LabTestRecord, ProfileMedicine
from app.db.session import SessionLocal
from app.services.chat.doc_search import _dense_ids
from app.services.chat.embeddings import get_embedder
from app.services.chat.lab_tool import lab_lookup
from app.services.chat.llm import LLMError, get_llm
from app.services.chat.medicine_tool import medicine_facts
from app.services.medicines.store import medicine_ingredients

EVAL = Path(__file__).resolve().parents[1]
DATA = EVAL / "data" / "v1"

BASELINE_SYSTEM = """You answer questions about a person's own medical reports, using only the reports given.
If the reports don't answer the question, say so. Reply with JSON only: {{"answerable": true or false, "answer": "..."}}.
Write the answer in {lang}."""
LANG = {"en": "English", "hi": "Hindi"}


def report_text(db, pid: uuid.UUID) -> str:
    """All of the profile's report text, oldest first: what B0 gets."""
    pages = db.execute(select(DocumentPage.text).join(Document, Document.id == DocumentPage.document_id)
                       .where(Document.profile_id == pid).order_by(Document.report_date, DocumentPage.page_no))
    return "\n".join(t for (t,) in pages)


def record_text(db, pid: uuid.UUID) -> str:
    """Everything the app knows about this person, to tell made-up numbers from real ones: report text, the lab
    values it stored (including converted ones) and what it knows about their medicines."""
    codes = db.scalars(select(LabTestRecord.loinc_code).join(LabResult, LabResult.lab_test_id == LabTestRecord.id)
                       .where(LabResult.profile_id == pid).distinct())
    labs = [f.evidence_text() for code in codes for f in lab_lookup(db, pid, code, "trend")]
    ingredients = {mi.ingredient.id for mi in medicine_ingredients(db, pid)}
    return "\n".join([report_text(db, pid), *labs, *(f.text for f in medicine_facts(db, pid, ingredients))])


def baseline(system: str, q: dict, pid: uuid.UUID) -> dict:
    with SessionLocal() as db:
        if system == "b0":
            context = report_text(db, pid)
        else:
            ids = _dense_ids(db, pid, get_embedder().embed([q["question"]])[0])[:6]
            context = "\n\n".join(db.scalars(select(Chunk.text).where(Chunk.id.in_(ids))))
    start = time.time()
    try:
        raw = get_llm().complete_json(BASELINE_SYSTEM.format(lang=LANG[q["lang"]]),
                                      f"Reports:\n{context}\n\nQuestion: {q['question']}")
        out = json.loads(raw)
        answerable, text = bool(out.get("answerable", True)), str(out.get("answer", ""))
    except (LLMError, ValueError) as e:
        answerable, text = True, f"[error: {type(e).__name__}]"
    return {"answerable": answerable, "text": text, "latency": time.time() - start}


def ours(client, q: dict, pid: uuid.UUID) -> dict:
    start = time.time()
    body = client.post(f"/api/v1/profiles/{pid}/chat", json={"question": q["question"], "lang": q["lang"]}).json()
    latency = time.time() - start
    text = " ".join([body["summary"], *(c["text"] for c in body["claims"]), *body["missing_info"],
                     body["doctor_note"]])
    with SessionLocal() as db:
        leaks = sum(_owner(db, s) not in (None, pid) for s in body["sources"])
    return {"answerable": body["answerable"], "text": text, "latency": latency, "leaks": leaks,
            "route": body["route"], "fallback": body["fallback"]}


def _owner(db, source: dict) -> uuid.UUID | None:
    """Which profile a cited source belongs to (drug labels belong to nobody)."""
    if source["kind"] == "lab_result":
        return db.scalar(select(LabResult.profile_id).where(LabResult.id == uuid.UUID(source["lab_result_id"])))
    if source["kind"] == "document":
        return db.scalar(select(Document.profile_id).where(Document.id == uuid.UUID(source["document_id"])))
    if source["kind"] == "medicine":
        return db.scalar(select(ProfileMedicine.profile_id).where(ProfileMedicine.id == uuid.UUID(source["medicine_id"])))
    return None


def main(system: str, split: str) -> Path:
    if not settings.database_url.endswith("/yourhealth_eval"):
        raise SystemExit("DATABASE_URL must point at the yourhealth_eval database")
    db_info = json.loads((DATA / "eval_db.json").read_text())
    questions = [json.loads(line) for line in (DATA / f"questions_{split}.jsonl").read_text().splitlines()]
    pid = {k: uuid.UUID(v) for k, v in db_info["profiles"].items()}

    if system == "ours":
        from fastapi.testclient import TestClient

        from app.main import app
        client = TestClient(app)
        client.post("/api/v1/auth/login", json={"email": db_info["email"], "password": db_info["password"]})
        answers = [ours(client, q, pid[q["patient_key"]]) for q in questions]
    else:
        with ThreadPoolExecutor(4) as pool:
            answers = list(pool.map(lambda q: baseline(system, q, pid[q["patient_key"]]), questions))

    out = EVAL / "results" / f"{date.today().isoformat()}_rag_{system}_{split}.jsonl"
    out.write_text("".join(json.dumps({"id": q["id"], **a}, ensure_ascii=False) + "\n"
                           for q, a in zip(questions, answers)))
    print(f"{system}: {len(answers)} answers -> {out}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--system", choices=["b0", "b1", "ours"], required=True)
    ap.add_argument("--split", choices=["dev", "test"], default="test")
    args = ap.parse_args()
    main(args.system, args.split)
