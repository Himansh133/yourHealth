# YourHealth: build checklist

Every step of the project in build order, chunk by chunk, with what each chunk delivers. Ticked items exist in
the code and are tested; plan sections are in brackets. Problem numbers (e.g. 7.1) refer to [the problems list](PROBLEMS_FACED.md).
Each chunk lists related problems, including fixed issues and workarounds; those references do not mean every issue
is still open. Items without a matching problem number keep their plan reference.

`[x]` done · `[~]` done differently from the plan, or partly · `[ ]` not done

## Chunk 1: Foundation (plan 5, 6.1, 12)

Related problems: 1.1–1.9, 1.11 (infrastructure, setup and test maintenance).

- [x] Docker Compose: Postgres with pgvector, Redis, S3-compatible storage
- [x] Database schema with Alembic migrations; CI checks migrations match the models
- [x] Register, login, logout, `GET /me`; httpOnly session cookie
- [x] Family profiles: create, rename, delete (Me, Papa, Mummy, Dadi)
- [x] One permission check used by every route (plan 12.1)
- [x] Isolation tests: one account can never read another's profiles, documents, values or shares (plan 12.3)
- [x] Audit log for sensitive actions
- [ ] Inviting a family member to share a profile (plan 12.2, stretch goal, on the cut list)
- [x] Frontend: login page, family page
- [ ] Follow up the TestClient deprecation warning (problem 1.11)
- [ ] Add a test-service preflight check and ignore build metadata (proposed in 1.6 and 1.8)

## Chunk 2: Uploading reports (plan 3.2, 7.1-7.2)

Related problems: 2.1, 2.6–2.9, 8.1 (OCR coordinates, document detection and dates).

- [x] Upload PDF or photo per profile; original stored in S3
- [x] Job queue (Redis) and a worker that processes each document
- [x] Status shown while processing (queued, processing, done, failed)
- [x] Text layer read from PDFs; OCR for photos and scanned PDFs
- [x] Document type detection (lab report, prescription, discharge summary, other)
- [x] Documents list with filters; open the original file; page text with word boxes
- [x] Delete a document together with its file, rows and chunks
- [x] Frontend: upload and status screen

## Chunk 3: Reading lab values (plan 7.3, 8)

Related problems: 2.2–2.5, 3.1–3.3, 8.2–8.6, 8.8–8.9 (row parsing, matching, units and lost rows).

- [x] Lab test dictionary (about 40 tests) with aliases and LOINC codes
- [x] Row parser for table layouts, including tilted phone photos (problem 8.2)
- [x] Regex parser for text that isn't a clean table
- [ ] Third tier: LLM parser for rows the first two miss (plan 7.3). Not built; lost rows are reported instead (8.6)
- [x] Name matching to dictionary tests
- [x] Unit conversion with exact factors; converted values rounded and shown with what was printed (8.9)
- [x] Flags from the report's own range, cross-checked with the printed H/L
- [x] Per-row confidence; low-confidence rows marked for review
- [x] Review screen: user corrects a value, row becomes "verified"
- [x] Frontend: review page

## Chunk 4: Trend graphs (plan 3.4)

Related problems: 1.10, 5.2, 5.5, 7.7, 8.9 (chart loading, markers, numeric display and medicine comparisons).

- [x] `GET /trends`: tests with 2 or more points, canonical units, ranges
- [x] Chart per test with out-of-range points marked
- [x] Medicine start/stop markers drawn on the charts (plan 9.5 overlay)
- [x] Frontend: trends tab
- [ ] Load the charts library only when the tab opens (problem 1.10, open)

## Chunk 5: Medicines and reference data (plan 4.2, 9)

Related problems: 4.1–4.4, 7.2, 7.7, 8.18 (drug names, labels, shared insights and medicine-name validation).

- [x] Indian brand dataset loaded; composition parser (brand to ingredients and strengths)
- [x] India to US name map (paracetamol / acetaminophen)
- [x] Drug knowledge from RxNorm, openFDA labels and MedlinePlus, fetched offline; sources in `refdata/SOURCES.md`
- [x] `drug_lab_effects` table, each row citing a label; checks in `refdata/EFFECTS_VERIFICATION.md`
- [ ] Faculty or doctor review of `drug_lab_effects` (plan 19)
- [x] Medicine list per profile: add by brand search, edit, stop, delete
- [x] Printed prescriptions parsed into unconfirmed medicines; user confirms or deletes each one
- [~] Confirming is a `PATCH` on the medicine, not the planned `POST /prescription/confirm` endpoint
- [x] Medicine info page: ingredient, label facts, known lab effects with sources
- [x] "Is this medicine doing its job?": value before starting against the latest value on the medicine (7.7)
- [x] Declines to recommend a medicine and offers a doctor visit sheet instead (plan 9.6)
- [x] Frontend: medicines tab
- [ ] Support short brand names when followed by an exact strength (proposed in 4.4)

## Chunk 6: Q&A assistant (plan 3.6, 10)

Related problems: 6.1–6.22, 8.10, 8.14, 8.18, 8.20, 8.22 (retrieval, routing, prompts, validation and latency).

- [x] Chunking of report text; discharge summaries chunked by section
- [ ] Long discharge-summary sections split by size (problem 6.14, open)
- [x] bge-m3 embeddings (ONNX) stored in pgvector
- [x] Hybrid document search: full-text plus vector, then the reranker (reorder only, no cut-off: 6.19)
- [x] Router: value, trend, document, medicine, medicine-lab, treatment, out of scope; rules first, LLM classifier
      for the rest
- [ ] Measure router accuracy on a labelled question set (problem 6.11, open)
- [x] SQL tool for values and trends (latest value comes from the database, not from search)
- [x] Medicine tool for the person's medicines and label facts
- [x] Prompt with numbered evidence; JSON answer with claims, sources, missing info and a doctor note
- [x] Validator on every answer: every number must be in the cited evidence, no medical advice; one retry, then
      the facts table
- [x] Abstains when the reports don't hold the answer; declines treatment questions
- [x] Citations open the source report
- [x] LLM through GMI Cloud (DeepSeek-V4-Flash, thinking off)
- [x] Frontend: chat tab with source chips

## Chunk 7: Hindi (plan 3.7, 11)

Related problems: 6.20, 8.10, 8.17, 8.19–8.21 (Hindi/Hinglish routing, drafting and translation checks).

- [x] Answers written in English first, then translated with a Hindi glossary
- [x] Number check after translation; glossary text set aside (8.17, 8.21)
- [x] Falls back to English with a note when the Hindi fails the checks
- [x] Hindi and Hinglish questions understood, including Hindi trend words (8.19)
- [x] Language picker in the chat
- [ ] Whole interface in Hindi (planned `i18n/` folder): only the chat is bilingual
- [ ] Hindi text to speech (on the cut list)
- [ ] Translate Hinglish document queries before retrieval (proposed in 6.20; plan 11.4)

## Chunk 8: WhatsApp bot (plan 3.3, 7.4)

Related problems: 9.1–9.7 (Meta integration, profile selection, delivery handling and link security).

- [x] Link a phone with a 6-digit code; codes expire, are single use, and lock after 5 wrong tries (9.6)
- [x] Webhook verification and signed message posts
- [x] Receive a PDF or photo, choose the profile with buttons, process, reply "Done"
- [x] Ask questions over WhatsApp (English and Hindi)
- [x] Duplicate deliveries ignored (9.4); webhook only records and queues (9.5)
- [x] Frontend: WhatsApp settings page
- [~] Tested against a local stand-in for Meta's API, not real WhatsApp (9.1)
- [ ] Run the full flow against real WhatsApp and verify the configured Graph API version (9.1–9.2)
- [ ] Message template for replies outside the 24-hour window (9.7, open)

## Chunk 9: Doctor visit sheet and QR sharing (plan 3.8, 13)

Related problems: 5.6, 7.1–7.7 (sheet data, PDF export, sharing, deployment URL and summary).

- [x] Sheet: recent values with flags, trends, medicines, medicine cards, documents
- [x] Share link with QR code and 4-digit PIN; only hashes stored; lock after 5 wrong PINs
- [x] Links expire (1 h, 24 h, 7 days), can be turned off, and every open is logged
- [x] Public PIN page and sheet for the doctor; cookie scoped to one link (7.4)
- [~] PDF export: print or "Save as PDF" from the browser, no server-made PDF (7.1)
- [ ] Short LLM-written summary on the sheet (plan 13.1 item 7, optional; 7.6)
- [x] Frontend: doctor sheet tab and public share page

## Chunk 10: Evaluation (plan 14)

Related problems: 6.11, 6.15, 6.22, 8.1–8.22 (evaluation findings, test isolation and coverage gaps).

- [x] Synthetic patient generator with known answers
- [x] Report renderer (4 layouts) and photo degrader
- [x] Extraction scorer: F1 by PDF, clean photo, degraded photo; value accuracy
- [x] Question generator with gold labels (value, trend, absent, medicine, treatment, injection, Hindi, document)
- [x] Baselines: B0 plain LLM with all report text, B1 vector RAG top 6
- [x] Ablations: without router, reranker, validator; thinking on/off (dev)
- [~] Chunk-size ablation (190 / 300 / 450 words): re-chunking tool built, not run yet
- [x] LLM judge for trend direction
- [x] Clean test set v2 (seed 2) run once per system
- [x] v2 test with the added Hindi trend and document questions (90 questions), every system run once
- [~] CI: harness tests and an extraction regression check on every push; the Q&A smoke subset from plan 14.6
      is not in CI (needs the LLM)
- [ ] Harder layouts and real, consented, de-identified reports (8.7, open)
- [ ] Long documents with similar passages to measure reranker benefit (8.16, open)
- [x] Computed follow-up dates rejected by the validator; facts-table fallback retained (8.22, working as intended)

## Chunk 11: Report and viva

Related problems: 5.1–5.7, 8.7, 8.12, 8.16, 8.22, 9.1–9.2 (demo checks, evidence limits and final reporting).

- [x] Report chapters 1-9 in `report/`
- [x] Chapter 8 updated with the 90-question test numbers
- [x] Problems list (`PROBLEMS_FACED.md`)
- [x] Viva demo script (`DEMO.md`)
- [ ] Final checks from plan 19: LOINC codes on loinc.org, Meta API details (9.2), college deadline dates
- [ ] Review reference data with a pharmacist/clinician and Hindi glosses with a native speaker (report 9.3)
- [ ] Reconcile chapter 9 with the 90-question results in chapter 8: baseline safety/numbers and the validator finding (8.16, 8.22)
- [ ] Add report citations, verify product comparisons, add screenshots and complete college front matter/formatting (`report/README.md`)
