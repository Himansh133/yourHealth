

def test_csv_evidence_does_not_invent_a_pdf_page():
    import uuid
    from app.services.chat.doc_search import ChunkHit
    hit = ChunkHit(uuid.uuid4(), 1, 1, 'Source value 2.10 mg/dL', 'lab_report', 'original.csv', None, mime_type='text/csv')
    assert 'p.1' not in hit.evidence_text()
    assert 'CSV source' in hit.evidence_text()
