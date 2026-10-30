# Problems faced while building YourHealth

Every problem we hit, what it broke, and what we did about it (or propose to do). Grouped by area, roughly in the
order we met them. **Status** is one of: *Fixed*, *Worked around*, or *Open*.

Commit hashes point to where the fix landed.

---

## 1. Infrastructure and setup

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 1.1 | MinIO stopped publishing public Docker images. | The plan's local file store could not be pulled. | Worked around | Use SeaweedFS, which speaks the same S3 API. The code only talks S3, so real S3 works in deployment (`707ce44`). |
| 1.2 | Disk space was tight (about 6 GB free) at the start. | The plan's heavy ML (bge-m3, reranker, PaddleOCR with torch) would not fit. | Fixed | RapidOCR (PaddleOCR models on ONNX Runtime) instead of PaddleOCR. Once 29 GB was free, the search models were added as ONNX (5.8 GB with the 8-bit fallbacks), still without PyTorch (see 6.1). |
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
| 2.9 | The report date on a discharge summary ("Date of Discharge: 02/03/2026") was not found. | No date in search results, and the discharge summary was left off the doctor sheet's report list. | Fixed | "Discharge", then "admission", added to the date labels after the lab-report labels. |

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
| 5.4 | The chat and doctor sheet screens have not been checked visually in a real browser. | Layout problems could go unnoticed (tests check behaviour, not looks). | Open | Check the Ask and Doctor sheet tabs in a browser at phone and desktop widths, and the printed sheet. |

| 5.5 | The API sends Decimal values as JSON strings ("7.2"). | Treating them as numbers would silently mis-type. | Fixed | Frontend types say `string`; the sparkline converts with `Number()` only for drawing. |
| 5.6 | The test fake backend dropped query strings. | Could not test which period the sheet asked for. | Fixed | The fake records the full URL too. |
| 5.7 | Five profile tabs don't fit on a phone. | Tab bar overflowed the screen. | Fixed | The tab bar scrolls sideways. |

## 6. Q&A assistant (RAG)

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 6.1 | No embedding model at first (disk, see 1.2). | Document search was keyword only: "food" did not find "diet". | Fixed | bge-m3 and bge-reranker-v2-m3 as full-precision ONNX on CPU (no PyTorch), a pgvector column, keyword + meaning results fused with RRF, then reranked (`afe4a3f`, `950cf6a`). "What food should papa avoid?" now finds the diet advice. |
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
| 6.13 | Answers take 4–7 s; document questions 12–14 s; Hindi up to 77 s (test p95 34 s). | Feels slow. | Fixed | Measured per step: the model spends most of its output on hidden reasoning (818 of 935 tokens on one translation). Turning it off (`LLM_THINKING=false`, DeepSeek's `thinking: disabled`) gave the same dev accuracy and p95 9 s instead of 20.5 s; Hindi 6–12 s instead of 21–59 s. Embedding is 0.04 s and reranking ~1 s, so they were never the problem (`27b2e4e`, `4250383`). |
| 6.14 | Section chunks of a discharge summary are not split by size. | A very long section becomes one big chunk, diluting search. | Open | Window long sections the same way as page text. |
| 6.15 | The LLM checks had only been tried on a handful of questions. | Model choice and prompt quality were not measured. | Fixed | Eval harness (plan 14): synthetic patients, 170 questions with gold answers, three systems compared. See section 8. |

| 6.16 | Hugging Face downloads hung at 406 MB, then failed with a Xet transfer error. | Models would not download. | Worked around | Restart (it resumes); the last file came over plain HTTP with `HF_HUB_DISABLE_XET=1`. |
| 6.17 | Both full-precision models need RAM: 3.2 GB in the API (both models), 1.6 GB in the worker (embedder). About 5 GB was free. | The machine may swap when other apps are open. | Worked around | Models load only when first used; 8-bit versions (0.57 GB each) are downloaded and one `.env` line away. |
| 6.18 | `tokenizers` pads with id 0, but XLM-RoBERTa models pad with id 1 and use it to compute positions. | Subtly wrong vectors for padded texts. | Fixed | Pad id read from the tokenizer (`<pad>`). |
| 6.19 | The reranker's scores can't separate relevant from unrelated passages on our text: right answers scored -6 to -7, "knee x-ray" also -6. A cut-off of 0.1 would have dropped every answer. | No safe relevance threshold. | Fixed | The reranker only reorders; whether passages answer the question stays with the LLM (it answered "not in the reports" for the knee x-ray) (`5331a1e`). |
| 6.20 | The reranker gives Hinglish questions the same floor score for every passage. Keyword search misses Hinglish too. | Hinglish document questions rely on the embedder alone. | Worked around | Equal scores keep the fused order, and "khane mein kya parhez" was answered correctly live. Proposed: translate Hinglish questions to English before searching (plan 11.4). |
| 6.21 | The full-precision reranker is slow on CPU: 4.5 s for 5 passages, 7 s for 10 with long ones. | Adds seconds to every document question. | Fixed | Batches sorted by length, only the top 10 reranked, and the 8-bit reranker by default: 10 long passages now take 3.3 s, and the API uses 2.7 GB instead of 3.2 GB. It picked the same top passage as full precision in 6 of 7 test questions. The embedder stays full precision. |
| 6.22 | The test suite must never load multi-GB models. | Slow or failing tests on machines without the models. | Fixed | Tests set `EMBEDDINGS_ENABLED=false` and use stand-in models; missing model files also mean keyword-only search. |

## 7. Doctor sheet and sharing

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 7.1 | PDF export with WeasyPrint needs system libraries (Pango, Cairo). | Heavy install for one feature that the plan lists as cuttable. | Worked around | Print from the browser (Save as PDF works too); app header and tabs are hidden when printing. Add WeasyPrint later if a server-made PDF is needed. |
| 7.2 | The medicine insights needed by the sheet were computed inside an API route. | Could not reuse them without copying. | Fixed | Moved into `medicines/store.py` as `profile_insights` (`098a1d7`). |
| 7.3 | A forwarded QR photo would give anyone the sheet. | Privacy risk. | Fixed | Link plus 4-digit PIN; only hashes stored; lock after 5 wrong PINs; links expire (1 h / 24 h / 7 days) and can be turned off; every open is logged (`d5ead08`). |
| 7.4 | A doctor's session cookie for one link could be tried on another. | Could open a different patient's sheet. | Fixed | The cookie is scoped to the link's path and names the link it unlocked; tested. |
| 7.5 | The share link points at the frontend's address, which differs by environment. | QR codes from a deployed server would point at localhost. | Worked around | `PUBLIC_BASE_URL` setting; must be set in deployment. |
| 7.6 | The sheet has no LLM-written summary yet (plan 13.1 item 7, optional). | Doctors read the tables only. | Open | Generate 3-4 sentences through the same answer validator, labelled "Auto-generated summary, check against reports". |
| 7.7 | The medicine card compared the value before starting with the first value after the onset window (plan 9.5). | On a real sheet, sodium was flagged low at 131 in the table while the card below said "142 to 140" from a value 9 months older. | Fixed | Compare with the latest value while on the medicine; found in the browser check. |

## 8. Found by the evaluation harness

The first extraction run on the dev split scored F1 87.0% (PDFs 97.0%, clean photos 65.1%, degraded photos 62.8%).
After the fixes below: dev 97.6%, and test 98.1% (run once, after tuning on dev).

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 8.1 | Reports with only two tests (e.g. creatinine and uric acid) were classified as "other", because the rule needed 3 rows. | The worker throws away the rows of non-lab documents: 16 of 97 dev reports lost every value. | Fixed | A lab keyword plus one recognised test is enough; unrecognised rows still need three (`37028a4`). |
| 8.2 | On tilted photos, rows were grouped by raw height, so values on the right paired with the test name one row up. | Wrong values stored against the wrong test: the most dangerous kind of error. | Fixed | The tilt is estimated from the OCR boxes' top edges, and rows are grouped on tilt-corrected heights. Degraded-photo F1 went from 62.8% to 95.1%. |
| 8.3 | OCR read "22 U/L" as "22 7/n", and the parser took 7 as the value (with "22" glued to the name). | A false LOW value would be stored. | Fixed | A unit must start with a letter, µ or % (or be `/cumm`); the row is now lost instead of wrong. |
| 8.4 | OCR garbles "mg/dL" as m9/dL, m/dl, mdl or m9/dlL. | Values had no unit, so they could not be converted or plotted. | Fixed | One pattern maps these to mg/dL (nothing else looks like them). |
| 8.5 | "Vitamin D Total" and "CK - Total" were not recognised. | Rows dropped even from clean PDFs. | Fixed | Aliases added. |
| 8.6 | OCR sometimes glues name and value into one box with a stray character ("7m9/dlL"), or merges "163 H". | Some photo rows are still lost (value accuracy stays 100%: no wrong values). | Open | Character-level cleanup of OCR boxes, or a second OCR pass on low-confidence rows. |
| 8.7 | The synthetic layouts are cleaner than real Indian lab reports. | The extraction numbers are an upper bound. | Open | Add harder layouts (multi-page, two-column tables, headers repeated mid-page), and if possible a small set of real, consented, de-identified reports. |
| 8.8 | Upscaling photos before OCR was tried as a fix. | It fixed some units, broke others and doubled OCR time. | Rejected | Not used. |
| 8.9 | Values converted from SI units were shown with false precision ("uric acid 5.598396 mg/dL, range 3.496896-7.195536"). | Odd answers, and numbers the user can't find on their report. | Fixed | Converted values are rounded to 3 significant figures and show what was printed: "5.6 mg/dL (printed as 333 µmol/L)" (`ddccfb2`). |
| 8.10 | Hindi "पिछला" can mean "last" or "the one before"; the model twice read it as the one before the latest and declined to answer. | Hindi value accuracy 78% on the first test run. | Fixed | The prompt now says what the evidence is ("the most recent value"; "last", "latest" and "पिछला" mean this one). Hindi value accuracy 100% on dev and test after. |
| 8.11 | The first Q&A scorer counted date parts ("07" in 2025-07-04) as made-up numbers and judged trends by keywords. | Ours looked worse than it was (31% "made-up" numbers, 44% trends). | Fixed | Dates are set aside, the records include the app's stored values, and an LLM judge reads the trend direction. |
| 8.12 | The test split was looked at before the two fixes above. | Strictly, test is no longer untouched. | Fixed | Kept both v1 runs, and built a fresh dataset with seed 2 (`eval/data/v2`, own database `yourhealth_eval_v2`), run once for every system with the final settings. Extraction F1 on it is 95.1% against 98.1% on v1 test: rows lost from phone photos, no wrong values. |
| 8.13 | The injection scorer counted "that instruction was not followed" and a rejection in the next sentence as following the instruction. | Ablations showed 2/5 injections followed when none were. | Fixed | More rejection wordings, and the rejection may come in the next sentence; every injection answer from every system was re-read. |
| 8.14 | The validator rejected warnings such as "do not stop or change the dose without your doctor" as medical advice. | With thinking off, 4 of 135 dev answers fell back to the facts table. | Fixed | A banned phrase right after "do not / don't / never / should not" is a warning; the translation check and the scorer use the same function (`f8b47e7`). |
| 8.15 | The scorer didn't count answers that fell back to the facts table or Hindi answers that came back in English. | A worse configuration could look equal. | Fixed | Both are rows in the results table now. |
| 8.16 | Ablations: the reranker and the validator changed no outcome on the v1 test set. | They can't be justified from these numbers alone. | Open | Only 5 test questions use document search; a larger document-question set is needed to measure the reranker and chunk size. The validator acts when evidence is noisy (4 rejections without the router). |

## 9. WhatsApp bot

| # | Problem | Impact | Status | Solution |
|---|---|---|---|---|
| 9.1 | No Meta developer account or public HTTPS URL during development. | The bot couldn't be tried against real WhatsApp. | Worked around | Tests use a fake client; a local stand-in for the Graph API (`WA_API_BASE`) plus signed webhook posts ran the whole flow live: link, report, buttons, processing, "Done" message, Hindi answer. Needs one real test once a Meta app exists. |
| 9.2 | Meta's current Graph API version couldn't be confirmed from public search. | Calls could target an old version. | Open | `WA_GRAPH_VERSION` setting (default v23.0); check Meta's docs when setting up. |
| 9.3 | Two family profiles with the same name ("Papa") gave two identical buttons, and questions went to the first one. Found in the live run. | Report saved or question answered for the wrong person. | Fixed | Buttons are numbered ("Papa", "Papa (2)"); a name matching several profiles picks the one used last; sending a report makes that profile the default for questions. |
| 9.4 | Meta retries webhooks and may deliver a message twice. | Duplicate documents or replies. | Fixed | Each message id is inserted with `ON CONFLICT DO NOTHING`; only a new row is queued. |
| 9.5 | Webhook must answer within seconds, but downloading, OCR and answering take longer. | Meta would retry and flood the bot. | Fixed | The webhook only verifies, records and queues; the worker does the work. |
| 9.6 | A 6-digit link code could in theory be guessed by sending many LINK messages. | Someone could link their phone to another account. | Fixed | Codes expire in 10 minutes and are single use; five wrong codes lock the phone for an hour, and failures are audited by a hash of the phone number (`a411667`). |
| 9.7 | The "Done" message is a proactive message; outside WhatsApp's 24-hour window it needs an approved template. | Late replies could be refused by Meta. | Open | Processing takes seconds, so replies stay inside the window; add a template for retries. |
