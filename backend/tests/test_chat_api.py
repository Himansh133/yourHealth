import json
from datetime import date
from decimal import Decimal

import pytest

from app.api.routes.chat import chat_llm
from app.db.models import Document, LabResult
from app.main import app
from app.services.chat.answer import FALLBACK_SUMMARY
from app.services.chat.llm import FakeLLM
from app.services.labs.dictionary import get_lab_dictionary
from app.services.labs.store import lab_test_ids

PAPA = {"display_name": "Papa"}


@pytest.fixture
def test_ids(db_session):
    ids = lab_test_ids(db_session, get_lab_dictionary())
    db_session.commit()
    return ids


@pytest.fixture
def use_llm():
    def _use(llm):
        app.dependency_overrides[chat_llm] = lambda: llm
        return llm
    return _use


def add_hba1c(db, pid, test_ids, value, on):
    doc = Document(profile_id=pid, source_channel="web", storage_key=f"docs/{on}", mime_type="application/pdf",
                   size_bytes=1, sha256=f"{on}{value}", doc_type="lab_report", report_date=on, status="done",
                   lab_name="Dr Lal PathLabs")
    db.add(doc)
    db.flush()
    r = LabResult(profile_id=pid, document_id=doc.id, lab_test_id=test_ids["4548-4"], raw_name="HbA1c",
                  raw_value=value, raw_unit="%", value_num=Decimal(value), value_canonical=Decimal(value),
                  range_low_canonical=Decimal("4.0"), range_high_canonical=Decimal("5.6"), flag="high",
                  observed_on=on, page_no=2, extraction_method="regex")
    db.add(r)
    db.commit()
    return r


def good_answer(evidence_id="E1"):
    return json.dumps({"answerable": True, "summary": "Papa's latest HbA1c is above the report's range.",
                       "claims": [{"text": "HbA1c was 7.2% on 14 Jun 2026", "evidence_ids": [evidence_id]}],
                       "missing_info": [], "doctor_note": "Discuss the target HbA1c with his doctor."})


def test_value_question_is_answered_from_sql_with_sources(make_user_client, db_session, test_ids, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_hba1c(db_session, pid, test_ids, "8.1", date(2026, 1, 10))
    june = add_hba1c(db_session, pid, test_ids, "7.2", date(2026, 6, 14))
    llm = use_llm(FakeLLM([good_answer()]))

    resp = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "What was papa's last HbA1c?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["answerable"] is True
    assert body["route"] == ["value"]
    assert body["claims"][0]["evidence_ids"] == ["E1"]
    assert body["sources"] == [{"id": "E1", "kind": "lab_result", "lab_result_id": str(june.id),
                                "document_id": str(june.document_id), "page_no": 2}]
    assert "8.1" not in llm.prompts[0][1]  # 'latest' sends only the last value


def test_trend_question_sends_every_value(make_user_client, db_session, test_ids, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_hba1c(db_session, pid, test_ids, "8.1", date(2026, 1, 10))
    add_hba1c(db_session, pid, test_ids, "7.2", date(2026, 6, 14))
    llm = use_llm(FakeLLM([good_answer("E2")]))

    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "Is papa's HbA1c improving?"}).json()

    assert body["route"] == ["trend"]
    assert [s["id"] for s in body["sources"]] == ["E1", "E2"]
    assert "[E1]" in llm.prompts[0][1] and "[E2]" in llm.prompts[0][1]


def test_no_values_abstains(make_user_client, test_ids, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    use_llm(FakeLLM([]))
    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "latest hba1c?"}).json()
    assert body["answerable"] is False
    assert body["summary"] == "I couldn't find this in Papa's reports."


def test_treatment_question_gets_safety_answer_without_the_llm(make_user_client, db_session, test_ids, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_hba1c(db_session, pid, test_ids, "7.2", date(2026, 6, 14))
    llm = use_llm(FakeLLM([]))

    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "Which medicine should I take for my HbA1c?"}).json()

    assert body["route"] == ["treatment"]
    assert "doctor" in body["summary"]
    assert body["claims"][0]["evidence_ids"] == ["E1"]  # their own latest value, cited
    assert "doctor visit sheet" in body["doctor_note"]
    assert llm.prompts == []


def test_document_question_searches_their_documents(make_user_client, db_session, use_llm):
    from app.services.chat.doc_search import index_document
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    doc = Document(profile_id=pid, source_channel="web", storage_key="docs/d", mime_type="application/pdf",
                   size_bytes=1, sha256="d", doc_type="discharge", status="done", lab_name="City Hospital")
    db_session.add(doc)
    db_session.flush()
    index_document(db_session, doc, [(1, "Diagnosis: diabetes"), (2, "Advice on Discharge: low sugar diet")])
    db_session.commit()
    answer = json.dumps({"answerable": True, "summary": "The discharge advice was a low sugar diet.",
                         "claims": [{"text": "Advised a low sugar diet", "evidence_ids": ["E1"]}],
                         "missing_info": [], "doctor_note": ""})
    llm = use_llm(FakeLLM([json.dumps({"labels": ["document"], "test": None}), answer]))

    body = a.post(f"/api/v1/profiles/{pid}/chat",
                  json={"question": "What did the discharge summary say about diet?"}).json()

    assert body["route"] == ["document"]
    assert "document | Discharge summary, City Hospital, p.2 | Advice on Discharge: low sugar diet" in llm.prompts[1][1]
    assert body["sources"][0] == {"id": "E1", "kind": "document", "document_id": str(doc.id), "page_no": 2}


def test_document_question_with_nothing_found_abstains(make_user_client, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    llm = use_llm(FakeLLM([json.dumps({"labels": ["document"], "test": None})]))
    body = a.post(f"/api/v1/profiles/{pid}/chat",
                  json={"question": "What did the discharge summary say about diet?"}).json()
    assert body["answerable"] is False
    assert body["summary"] == "I couldn't find this in Papa's reports."
    assert len(llm.prompts) == 1  # only the classifier


def test_unconfigured_llm_falls_back_to_facts(make_user_client, db_session, test_ids, monkeypatch):
    from app.core.config import settings
    monkeypatch.setattr(settings, "llm_api_key", "")
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_hba1c(db_session, pid, test_ids, "7.2", date(2026, 6, 14))
    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "last hba1c"}).json()
    assert body["fallback"] is True
    assert body["summary"] == FALLBACK_SUMMARY


def test_other_users_profile_is_not_found(make_user_client, use_llm):
    a = make_user_client("a@example.com")
    b = make_user_client("b@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    use_llm(FakeLLM([]))
    assert b.post(f"/api/v1/profiles/{pid}/chat", json={"question": "last hba1c"}).status_code == 404


def test_empty_question_is_rejected(make_user_client, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    assert a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "  "}).status_code == 422


def test_everyday_word_finds_the_values(make_user_client, db_session, test_ids, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_hba1c(db_session, pid, test_ids, "7.2", date(2026, 6, 14))
    use_llm(FakeLLM([]))
    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "Which medicine should papa take for his sugar?"}).json()
    assert [c["evidence_ids"] for c in body["claims"]] == [["E1"]]


# --- medicines ------------------------------------------------------------------------------------------------

@pytest.fixture
def refdata(db_session):
    from app.refdata.load import load_reference_data
    load_reference_data(db_session)


def add_glycomet(db, client, pid):
    from sqlalchemy import select
    from app.db.models import DrugBrand
    bid = str(db.scalar(select(DrugBrand.id).where(DrugBrand.brand_name == "Glycomet 500")))
    return client.post(f"/api/v1/profiles/{pid}/medicines",
                       json={"brand_id": bid, "frequency_code": "BD", "started_on": "2026-03-01"}).json()


def test_medicine_question_uses_the_label(make_user_client, refdata, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    llm = use_llm(FakeLLM([good_answer("E1").replace("HbA1c was 7.2% on 14 Jun 2026", "It treats thyroid problems")]))

    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "What is Thyronorm for?"}).json()

    assert body["route"] == ["medicine"]
    assert "drug_info | levothyroxine" in llm.prompts[0][1]
    assert body["sources"][0]["kind"] == "drug_label"
    assert body["sources"][0]["url"].startswith("https://dailymed.nlm.nih.gov/")


def test_medicine_and_test_question_sends_values_medicine_and_effect(make_user_client, db_session, test_ids, refdata,
                                                                    use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    med = add_glycomet(db_session, a, pid)
    add_hba1c(db_session, pid, test_ids, "8.1", date(2026, 1, 10))
    add_hba1c(db_session, pid, test_ids, "7.2", date(2026, 6, 14))
    llm = use_llm(FakeLLM([good_answer("E2")]))

    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "Is Glycomet bringing papa's HbA1c down?"}).json()

    prompt = llm.prompts[0][1]
    assert body["route"] == ["medicine_lab"]
    assert "HbA1c 8.1 %" in prompt and "HbA1c 7.2 %" in prompt
    assert "medicine | Glycomet 500 (metformin) | twice a day | started 2026-03-01" in prompt
    assert "drug_effect | metformin and HbA1c" in prompt
    assert "Vitamin B12" not in prompt  # only effects on the asked test
    kinds = {s["kind"] for s in body["sources"]}
    assert kinds == {"lab_result", "medicine", "drug_label"}
    assert {s.get("medicine_id") for s in body["sources"]} >= {med["id"]}


def test_treatment_answer_lists_linked_medicines_they_take(make_user_client, db_session, test_ids, refdata, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_glycomet(db_session, a, pid)
    add_hba1c(db_session, pid, test_ids, "7.2", date(2026, 6, 14))
    use_llm(FakeLLM([]))

    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "Which medicine should papa take for his HbA1c?"}).json()

    claims = [c["text"] for c in body["claims"]]
    assert any(c.startswith("lab_result | HbA1c 7.2 %") for c in claims)
    assert any(c.startswith("medicine | Glycomet 500") for c in claims)


def test_classifier_finds_the_test_the_rules_missed(make_user_client, db_session, test_ids, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    add_hba1c(db_session, pid, test_ids, "8.1", date(2026, 1, 10))
    add_hba1c(db_session, pid, test_ids, "7.2", date(2026, 6, 14))
    llm = use_llm(FakeLLM([json.dumps({"labels": ["trend"], "test": "glycated hemoglobin"}), good_answer("E2")]))

    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "How has papa's three month average been?"}).json()

    assert body["route"] == ["trend"]
    assert "[E2] lab_result | HbA1c 7.2 %" in llm.prompts[1][1]


def test_out_of_scope_question_is_declined_without_answering(make_user_client, use_llm):
    a = make_user_client("a@example.com")
    pid = a.post("/api/v1/profiles", json=PAPA).json()["id"]
    llm = use_llm(FakeLLM([json.dumps({"labels": ["out_of_scope"], "test": None})]))

    body = a.post(f"/api/v1/profiles/{pid}/chat", json={"question": "Do I have cancer?"}).json()

    assert body["route"] == ["out_of_scope"]
    assert body["answerable"] is False
    assert "doctor" in body["summary"]
    assert len(llm.prompts) == 1  # only the classifier
