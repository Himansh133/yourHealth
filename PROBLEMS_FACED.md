# Problems faced while building YourHealth

Every problem we hit, what it broke, and what we did about it (or propose to do). Grouped by area, roughly in the
order we met them. **Status** is one of: *Fixed*, *Worked around*, or *Open*.

Commit hashes point to where the fix landed.

---

## 1. Infrastructure and setup

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 1.1 | MinIO stopped publishing public Docker images. | The plan's local file store could not be pulled. | Worked around | Use SeaweedFS, which speaks the same S3 API. The code only talks S3, so real S3 works in deployment (`707ce44`). |
| 1.2 | Disk space was tight (about 6 GB free) at the start. | The plan's heavy ML (bge-m3, reranker, PaddleOCR with torch) would not fit. | Worked around | RapidOCR (PaddleOCR models on ONNX Runtime) instead of PaddleOCR; embeddings postponed (see 6.1). Disk now shows 29 GB free, so this can be revisited. |
| 1.3 | Editable install picked up folders outside the app package. | `pip install -e .` failed. | Fixed | Limit setuptools package discovery to `app*` (`01551c7`). |
| 1.4 | A short JWT secret silently weakens HS256 session tokens. | Insecure sessions if someone used a short secret. | Fixed | Require 32+ bytes; the README generates one (`53b7c2c`). |
| 1.5 | The Vite dev proxy assumed the backend was on port 8000. | Frontend could not reach a backend on another port. | Fixed | `API_URL` env var for the proxy target (`4075d0a`). |
| 1.6 | Backend tests failed in bulk (108 errors) at the start of a session. | Looked like broken code; was only Postgres, Redis and S3 not running. | Fixed | Start `docker compose up -d` before tests; the README says tests need the containers. Proposed: a pytest check that fails early with one clear message when the services are down. |
| 1.7 | No `backend/.env` existed when wiring the LLM. | Nowhere to put the GMI key. | Fixed | Created it from `.env.example` with a generated JWT secret; checked that inline `# comments` don't leak into values. |
| 1.8 | `npm run build` leaves `frontend/tsconfig.tsbuildinfo` behind. | Untracked build file shows up in `git status`. | Worked around | Deleted after builds. Proposed: add `*.tsbuildinfo` to `.gitignore`. |
| 1.9 | `pkill -f <pattern>` killed the shell running it, because the shell's own command line contained the pattern. | Restarting dev servers failed twice. | Worked around | Stop and start processes in separate commands and use a bracket pattern (`[u]vicorn`) that cannot match itself. |
| 1.10 | Vite warns that the main JS chunk is over 500 kB (mostly Recharts). | Slower first load; warning on every build. | Open | Lazy-load the Trends tab (`React.lazy`) so Recharts loads only when charts are opened. |
| 1.11 | Starlette warns that `httpx` in its TestClient is deprecated. | Noise in every test run. | Open | Move to the replacement client when FastAPI/Starlette documents it; pin versions until then. |

## 2. Reading reports (extraction and OCR)

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 2.1 | OCR boxes come in image pixels, text-layer boxes in PDF points. | Review highlights landed in the wrong place on scanned pages. | Fixed | Scale OCR boxes by 72/DPI to PDF points (`72bfa95`). |
| 2.2 | OCR returns words, not table rows. | Values lost their test names. | Fixed | Group boxes on the same line into rows so column gaps survive (`72bfa95`). |
| 2.3 | OCR reads `µIU/mL` as `ulU/mL` (capital I as l). | TSH units not recognised, value not plotted. | Fixed | Unit alias table maps the misread to `µIU/mL` (`72bfa95`). |
| 2.4 | Test names that start with a number ("25 OH Vitamin D"). | Parser took the number as the value. | Fixed | Row parser accepts a leading number as part of the name (`8874d62`). |
| 2.5 | Ranges written as "up to 200" or "< 200". | No reference range, so no high/low flag. | Fixed | Parser supports one-sided ranges (`182f8a5`). |
| 2.6 | Photos need OCR but no engine was wired at first. | Image uploads could not be read. | Fixed | Pluggable OCR; images fail with `ocr_unavailable` and a helpful message if no engine (`c237c2c`, `72bfa95`). |
| 2.7 | A document counts as a lab report only with 3+ result rows and a range keyword. | Our first two-row test PDF was filed as "other" and nothing was extracted. | Fixed (test data) | Real reports have many rows; the sample PDFs now have four. Kept the rule, since it stops prescriptions being read as lab reports. |
| 2.8 | Discharge summaries were never detected; they were filed as "other". | No section chunks; the frontend's "Discharge summary" label never showed. | Fixed | Detect "discharge summary", or "discharge" plus "diagnosis", before the prescription rule, since discharge summaries list medicines too (`a8c4860`). |
| 2.9 | The report date on a discharge summary ("Date of Discharge: 02/03/2026") is not found. | The document has no date in search results and answers. | Open | Add "discharge" and "admission" to the date labels in `classify.py`, preferring the discharge date. |

## 3. Lab tests and units

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 3.1 | The plan's `token_set_ratio` fuzzy match scores 100 whenever one name's words are a subset of another's. | MCH matched Haemoglobin, VLDL matched LDL, Non-HDL matched HDL: wrong values on charts. | Fixed | Fuzzy matching only forgives typos inside words, never extra or missing words. An unmapped row is safe; a wrong mapping is not (`81871da`). |
| 3.2 | A row printed as "Sugar" could be blood or urine sugar. | Mapping it in the parser would put wrong values on charts. | Fixed | Everyday words like "sugar", "thyroid" and "kidneys" map to tests only in chat, never in parsing (`99e8f70`). |
| 3.3 | Showing ranges with `Decimal.normalize()` turned "4.0" into "4". | Evidence did not match what the report printed. | Fixed | Keep the scale the value was stored with (`81e7d0c`). |

## 4. Medicines

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 4.1 | Drug knowledge comes from US sources (openFDA) but brands are Indian. | Names differ (paracetamol vs acetaminophen). | Worked around | Indian brand → ingredient → US name map (`name_map_in_us.csv`); see plan 4.3. |
| 4.2 | openFDA returns many labels per ingredient. | Risk of citing a combination or injection label. | Fixed | Pick single-ingredient, oral, prescription, newest; every curated effect row is checked against the label section it cites (`948ed4c`). |
| 4.3 | Fuzzy brand matching could snap "Telma 60" to Telma 40 or 80. | Wrong strength on a medicine. | Fixed | Names may have typos, but strengths must match exactly (`52ad3e8`). |
| 4.4 | Short brand names ("Pan" for Pan 40) are everyday words. | Chat would treat "pan" in a question as a medicine. | Worked around | Brand names under 4 letters are not matched in chat questions. Proposed: allow them only when followed by a strength ("pan 40"). |

## 5. Frontend

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 5.1 | Browser locale data writes "Sept" for en-GB. | Dates read differently across browsers and did not match the backend. | Fixed | Fixed month names in `format.ts` (`2477b44`). |
| 5.2 | Chrome drew the arrow marker on charts as an emoji. | Medicine markers looked wrong. | Fixed | Plain text glyphs (`e9710f1`). |
| 5.3 | The test fake backend treated any object with a `status` field as a reply wrapper. | Document objects (which have `status`) broke tests. | Fixed | Only `{status, body}` objects are wrappers (`d7a0895`). |
| 5.4 | The chat screen has not been checked visually in a real browser. | Layout problems could go unnoticed (tests check behaviour, not looks). | Open | Check the Ask tab in a browser at phone and desktop widths. |

## 6. Q&A assistant (RAG)

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 6.1 | No embedding model yet (disk, see 1.2). | Document search is keyword only: "food" will not find "diet". | Open | Add a multilingual embedding model (bge-m3 as planned, or a smaller one such as multilingual-e5-small) plus a pgvector column, and fuse with keyword results (plan 10.5). |
| 6.2 | GMI Cloud's model prices are not on its public site, and its blog posts disagree. | Could not pick the cheapest model from the web. | Fixed | `GET /v1/models` returns prices per model; models were ranked from that. |
| 6.3 | The cheapest GMI models did not respond (Ling-3.0 404; gpt-oss-120b and gemma-4-31b 503). | Could not use them. | Worked around | Benchmarked the next cheapest through our real prompt and validator; DeepSeek-V4-Flash passed 12/12 (`69602ae`). Re-run the benchmark later; availability changes. |
| 6.4 | GMI's free 1.5B model is too small for JSON answers that cite evidence. | Most answers would fail checks and fall back to tables. | Worked around | Not used. |
| 6.5 | "is" and "was" as value cues sent "What is HbA1c?" (a general question) to a value lookup. | Wrong kind of answer. | Fixed | Removed those cues; such questions go to the LLM classifier (`53b5f1d`). |
| 6.6 | The number check read the "1" in HbA1c (and digits in B12, T4) as numbers. | Correct answers were rejected and fell back to a table. | Fixed | Digits right after a letter are part of a name; "850mg" is still checked (`0865d78`). |
| 6.7 | "Which medicine for his sugar?" did not find his sugar values. | Safety answer without his own numbers. | Fixed | Everyday words map to tests (`99e8f70`). |
| 6.8 | The classifier read "what treatment did he get in hospital" as asking which medicine to take. | Gave the safety template instead of the hospital record. | Fixed | Label descriptions separate treatment given (document) from treatment choice, with examples (`6deab64`). |
| 6.9 | The classifier declined "When is his follow up?" as out of scope. | Refused a question the discharge summary answers. | Fixed | Follow-up, advice and diet are listed under document questions (`6deab64`). |
| 6.10 | The classifier named "kidney function", which is not a test. | "How are his kidneys?" found nothing. | Fixed | Its test name goes through the same matcher as the rules, so everyday words work; "kidneys" added (`6deab64`). |
| 6.11 | The classifier can label the same question differently on different runs, even at temperature 0. | Answers may change between asks. | Open | Measure router accuracy on a labelled question set (plan 14) and add examples for the questions it gets wrong. |
| 6.12 | The model once wrote "[E1]" inside the answer text. | Odd text in the chat. | Fixed | Prompt rule: IDs go only in `evidence_ids` (`6deab64`). Proposed: also strip `[E\d+]` from text in the validator if it recurs. |
| 6.13 | Each answer takes 4 to 10 seconds; questions the rules can't place add a classifier call. | Feels slow. | Open | Stream the answer, or show the retrieved facts first and the written answer when ready. |
| 6.14 | Section chunks of a discharge summary are not split by size. | A very long section becomes one big chunk, diluting search. | Open | Window long sections the same way as page text. |
| 6.15 | The LLM checks have only been tried on a handful of questions. | Model choice and prompt quality are not measured. | Open | Build the eval harness from plan 14 (synthetic patients, labelled questions, faithfulness and number-check metrics). |
