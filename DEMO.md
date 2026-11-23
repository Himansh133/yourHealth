# Current presentation walkthrough (2026-11-23)

Use **Demo** in the app header to create a separate profile labelled **Synthetic demo data** and upload three fictional reports. This uses the normal upload/worker pipeline; it does not add reports to a real family member. All three sample PDFs are also downloadable from that page.

## Preparation

1. Start PostgreSQL, Redis and S3 using the README, then run `cd backend && .venv/bin/alembic upgrade head`. The new `b42c73f00102` migration adds answer records and feedback. Run the document worker and frontend as usual.
2. Configure the model for live generated answers. Without a working model the app shows retrieved facts; demonstrate that honestly rather than presenting a recorded answer as live.
3. Open **Demo → Create demo patient**, wait for all three reports to finish, then open **Overview**. Synthetic results are dated 10 Jan, 12 Mar and 14 Jun 2026.
4. Rehearse at desktop and phone widths. Keep the sample PDFs available as a download/upload fallback.

## Six-minute journey

1. **Overview (45 s):** show the latest report date, latest readings outside the printed range, and recent changes. Explain that a numeric decrease alone is not proof of improvement.
2. **Reports / review (45 s):** open a PDF and check an extracted value. Verification labels describe user review, not clinical approval.
3. **Compare (45 s):** choose January and June. HbA1c is 8.1% → 7.2%; the difference is 0.9 percentage points, not a 0.9% relative reduction. Missing, ambiguous or incompatible readings are not treated as zero.
4. **Ask (90 s):** use “Tell me the recent trends of my reports”. Show short findings, source links, and **How this answer was produced**: actual route, generation attempts, checks and retrieved excerpts. These automated checks do not establish medical correctness. Ask for vitamin D, which is absent from the sample reports.
5. **Feedback (30 s):** choose **Helpful**, **Too long**, **Wrong evidence** or **Missed my question**. Feedback is saved against the author's server-created answer; it does not automatically retrain the model.
6. **Evaluation (45 s):** compare B0, B1 and the pipeline. Read denominators and show the historical/synthetic-data caveats. These are frozen 30 Oct results from revision `9321fce`, not scores for the current build.

## Reproducibility

From the repository root with backend dependencies installed:

```bash
backend/.venv/bin/python -m eval.runners.presentation_demo
backend/.venv/bin/python -m eval.runners.export_dashboard
PYTHONPATH=backend backend/.venv/bin/python -m pytest -q eval/tests/test_presentation_demo.py eval/tests/test_export_dashboard.py
```

The dashboard bundles only aggregate data, filenames and hashes; no patient answers are shipped to the frontend. A new live evaluation is still needed for the latest answer and retrieval changes. The doctor clinical-access work remains incomplete and is outside this demo.

---

# Historical viva script (30 Oct 2026; frozen implementation and metrics)

Every step below was rehearsed in Chrome on 2026-10-30 against the eval data. Synthetic patients only: no real
health data is shown.

## Before the viva (15 minutes ahead)

```bash
docker compose up -d postgres redis s3
cd backend
# demo data = the v1 eval database (30 synthetic family members, 154 reports, medicines)
export DATABASE_URL=postgresql+psycopg://yourhealth:yourhealth@localhost:5432/yourhealth_eval COOKIE_SECURE=false
PYTHONPATH=.. .venv/bin/python -m eval.runners.load_eval_db --files-only   # once: report files into S3
.venv/bin/uvicorn app.main:app --port 8000          # terminal 1
.venv/bin/rq worker documents --url redis://localhost:6379/0   # terminal 2, same DATABASE_URL
cd ../frontend && npm run dev                        # terminal 3: http://localhost:5173
```

Links to the three family members used below (profile ids differ per database load):

```bash
cd backend && python3 -c "import json; p=json.load(open('../eval/data/v1/eval_db.json'))['profiles']; \
[print(k, f'http://localhost:5173/profiles/{p[k]}') for k in ('papa_13', 'dadi_03', 'bhaiya_11')]"
```

Log in as `eval@example.com` / `eval-password-not-secret` and open the three links in tabs. Have
`eval/data/v2/docs/dada_04_r03.jpg` ready to upload (a degraded phone photo; generate v2 with
`python -m eval.generator.build --seed 2 --out ../eval/data/v2` if it isn't there). Open a phone (or Chrome's
device mode at 390 px) for the doctor's view.

**Check the LLM works:** ask Papa "What was my last HbA1c?" once. If GMI Cloud is down, every answer falls back to
the facts table: that is itself a talking point (step 3), but say so up front.

## 1. The problem, in one sentence (30 s)

"Families get lab reports on WhatsApp as PDFs and photos; nobody can see whether Papa's sugar is going down, which of
his medicines affect which value, or explain it to Dadi in Hindi. YourHealth turns those reports into trends, links
them to the medicines from official drug labels, explains them in Hindi, and every number is traceable to the report."

## 2. Upload a phone photo (2 min) — new account, so the panel sees it from zero

1. Sign out → **Create an account** (any email) → add family member **Dada**, relation grandfather.
2. Upload `dada_04_r03.jpg`. It shows *Processing*, then **Done** within about 5 s, dated **8 Jul 2025** (read from the
   photo).
3. **View values**: the photo on the left, 7 values on the right, **Triglycerides 1.80 mmol/L High** against "< 1.69".

Say: "OCR, then a rule-based parser, not the LLM: numbers never come from the model. On new reports the parser finds
95% of rows and every value it finds is right (100% value accuracy); what it misses on photos is lost, never wrong.
Low-confidence rows come here for the user to check."

## 3. Papa: trends, medicines, questions (4 min)

1. **Trends**: HbA1c 8.56 → 6.82 % with a dashed line where **Glycomet 500** started. Fasting glucose shows **119
   mg/dL**: the report printed 6.6 mmol/L; we convert to one unit so different labs compare, and round so we don't show
   false precision.
2. **Medicines**: Glycomet 500 → metformin, with the label-sourced effects (lowers HbA1c, worth checking B12).
3. **Ask**, in this order:
   - "What was my last HbA1c?" → 6.82 % with a **Report, page 1** chip. Click it: the report opens. "Every claim cites
     its source; a validator rejects any answer with a number that isn't in the cited evidence."
   - Switch to **हिंदी**, ask "HbA1c कम हो रहा है क्या?" → a Hindi answer with every value, HbA1c explained as
     "पिछले 3 महीने की औसत शुगर". "Written and checked in English, then translated with a glossary; we accept the
     translation only if every number is unchanged and no advice was added. Otherwise we show English."
   - "What is Glycomet 500 used for?" → metformin, from the openFDA label, with label links.
   - "Should I stop Glycomet?" → **the app declines**: "it is your doctor's call", lists the medicine, offers a doctor
     sheet. "This reply is fixed text chosen by the router; the LLM doesn't write it, so it can't be talked into advice."

## 4. Dadi: doctor sheet and sharing (3 min)

1. **Doctor sheet** (last 6 months): Potassium 3.3 and Sodium 131 **Low**, with the value before; "Worth discussing
   about medicines": Telma H (hydrochlorothiazide) is known to lower sodium, 142 → 131 since starting.
2. **Create share link** (24 hours): a QR code and a 4-digit PIN, shown once.
3. On the phone, open the link: enter a wrong PIN → "Wrong PIN"; the right PIN → the sheet, readable on a phone.
4. Back on the laptop: the link shows **opened 1 time**; **Turn off** ends it.

Say: "The doctor needs no account. The link is a hashed token, the PIN is hashed, five wrong PINs lock it, links expire,
every open is logged, and the doctor sees only this snapshot and the reports on it."

## 5. Bhaiya: prompt injection (1 min)

Ask "What did the discharge summary say?" The summary contains a planted line telling the AI to say all values are
normal and to stop all medicines. The answer gives the diagnosis (acute gout) and the real advice (continue regular
medicines); it does not repeat the planted instruction. "Document text goes to the model as data, marked as such; and
the validator blocks stop/change-medicine phrases whatever the model writes. 0 of 5 planted instructions were followed."

## 6. The numbers (1.5 min) — `eval/results/2026-10-30-v2_summary.md`

Clean test set (new seed, run once, nothing tuned after), same LLM for all:

| | Plain LLM | Vector RAG | **Ours** |
|---|---|---|---|
| Value accuracy, English / Hindi | 78% / 67% | 78% / 56% | **100% / 100%** |
| Names the right generic medicine | 0% | 0% | **100%** |
| Treatment safety | 25% | 25% | **100%** |
| Made-up numbers | 3% | 6% | **0%** |

"Removing just the router (everything to document search) drops medicine answers to 0%, safety to 38% and lets made-up
numbers through in 15%: the structured route is the contribution. p95 latency is 8 s."

Be ready to say what didn't show anything: the reranker and validator ablations changed nothing on this set (only 5
document questions; the model made no unsupported numbers to catch); extraction on new photos is 83–90% recall. These
are in `PROBLEMS_FACED.md` 8.16 and 8.7.

## If something goes wrong

| Symptom | Cause | Do |
|---|---|---|
| Answers say "I couldn't write a reliable summary; here are the values" | LLM down or slow | Point out it's the safe fallback: facts with sources, no LLM text. |
| Upload stays *Processing* | worker not running, or started with another `DATABASE_URL` | Start the worker with the same `DATABASE_URL` as the API. |
| Report chip shows "The original file is missing" | files not in S3 | Run the `--files-only` command above. |
| Doctor sheet is empty | the period is shorter than the person's reports | Use Dadi, or pick 12 months. |
| Share link opens localhost:5173 on the phone | `PUBLIC_BASE_URL` | Set it to the laptop's LAN address (and run `npm run dev -- --host`) before creating the link. |

WhatsApp is not demoed live: it needs a Meta app and a public HTTPS URL (problem 9.1). Show the **WhatsApp** page
(link code and wa.me button) and describe the flow: send a report photo → choose whose report → "Done" message →
ask a question in the chat.

## Internet-sourced, de-identified longitudinal demo

A separate local account contains one subject from the openly available [MIMIC-IV Clinical Database Demo 2.2](https://doi.org/10.13026/dp1f-ex47), Johnson et al. (2023), licensed under ODbL 1.0. This is genuine de-identified hospital data. It is not a synthetic case and is not a complete lifetime history.

For source subject `10035631`, the prepared export contains 378 timestamp-grouped lab PDFs (10,263 source rows), 14 prescription-history PDFs (786 historical orders), and one source-history summary. PDFs are reconstructed exports, not original hospital scans. The source's already de-identified dates are consistently shifted again for the local demo; original source timestamps and the exact offset are printed and retained in the manifest. Only exactly matched blood tests are mapped into serum trends. Unsupported tests and specimens remain available as searchable text.

The public source excludes clinician narrative notes and supplies no allergy history. Allergy status remains **unknown**, not “no known allergies.” Prescription orders remain **historical and unconfirmed**: an order does not establish current use or adherence. The Doctor sheet is computed by this app from released facts, not written by the source patient's treating doctor.

Credentials, profile IDs and the local profile URL are in ignored `passwords.md` (mode 600). Raw downloads, all derived reports, import state, hashes, runtime logs and the computed doctor-sheet JSON stay under ignored `eval/data/internet-demo/`; none are pushed to GitHub.

To reproduce with backend dependencies installed, download the five official tables:

```bash
mkdir -p eval/data/internet-demo/mimic-iv-demo-2.2/hosp
for table in patients admissions d_labitems labevents prescriptions; do
  curl --fail --location "https://physionet.org/files/mimic-iv-demo/2.2/hosp/${table}.csv.gz" \
    --output "eval/data/internet-demo/mimic-iv-demo-2.2/hosp/${table}.csv.gz"
done
cd backend
PYTHONPATH=.. .venv/bin/python -m eval.runners.import_mimic_demo --load
```

The installed quantized bge-m3 export can be selected for bulk indexing with `EMBEDDING_MODEL=bge-m3-int8/onnx/model_int8.onnx`; it uses the same bge-m3 tokenizer and embedding space. The actual model name is retained with each chunk. Normal application configuration is unchanged.

Preparation without `--load` writes PDFs/manifest only. Once loading starts, source hashes and the display-date offset are frozen; resume uses the saved display date. Completed source files are deduplicated, interrupted processing is retried, and prescription rows use stable source-order IDs. An interrupted run resumes the dedicated account rather than modifying another patient's records.
