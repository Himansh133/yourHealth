# 4. Reading reports

## 4.1 Getting files in

**Web upload.** PDF, JPEG or PNG, up to 15 MB and 20 pages. The file's type is checked from its bytes, not its name.
It is stored privately in S3 under a random key and a job is queued. The page shows the status (*Queued →
Processing → Done / Needs review / Failed*) and updates itself.

**WhatsApp.** A user links their phone once: the app shows a 6-digit code, and the user sends `LINK <code>` to the bot.
Codes expire in 10 minutes and are single use, and five wrong codes lock that phone for an hour. After that, any report
the user sends gets reply buttons asking whose report it is ("Papa", "Dadi"); the file is downloaded from Meta into
the same storage and the same job runs. When processing finishes the bot replies, for example: "Done. Papa's report:
7 tests found. Outside the report's range: Triglycerides 1.80 mmol/L (high)", with a link to check the values. A question typed in the chat is answered by the same pipeline as the web chat (Chapter 6).

The webhook checks Meta's signature on every request, records each message ID with `ON CONFLICT DO NOTHING` so a
retried delivery is processed once, queues the work and returns immediately. Meta retries a slow webhook, so all slow
work runs in the worker.

## 4.2 From file to text

| Input | Method |
|---|---|
| PDF with a text layer | PyMuPDF: text and each word's position |
| Scanned PDF or photo | Rendered at 200 DPI, then RapidOCR (PaddleOCR detection and recognition models on ONNX Runtime) |

OCR returns words with boxes in image pixels; they are scaled to PDF points so positions mean the same on scanned and
digital pages. The text, the words and their boxes, and the OCR confidence are stored per page.

## 4.3 Finding result rows

Lab reports are tables, but neither a text layer nor OCR returns a table. They return words with positions.

1. **Group words into lines.** Words whose vertical centres line up form a row. Phone photos are often slightly
   tilted, which made values pair with the test name one row up. The tilt is estimated from the top edges of the OCR
   boxes and rows are grouped on tilt-corrected heights. On degraded photos this raised F1 from 62.8% to 95.1%.
2. **Split each line into name and tail.** Split points are tried from the left until the right side reads as
   `value [flag] [unit] [range] [unit]`. This survives both lost column gaps and cells that OCR glued together
   ("7.2%").
3. **Read the parts.** Values may carry `<` or `>`; flags are H, L, High or Low; ranges may be `a - b`, `< b`, `> a` or
   `up to b`. A unit must start with a letter, µ or %. Without that rule, OCR junk such as "22 7/n" was read as the
   value 7 under the name "… 22".

A subsequent recovery path (Chapter 8.8) retains readable values with damaged slash-containing units only when
there is an exact dictionary name and a separate numeric value. For example, `SGOT (AST) 22 7/n 10 - 40` can be
shown for review as value 22 with raw unit `7/n`; it is not converted or treated as a trusted chart value. Missing or
unconvertible units lower confidence below the review threshold. The planned LLM extraction fallback remains unbuilt.

## 4.4 Classifying the document

Rules decide the document type from its text:

- **Discharge summary:** the words "discharge summary", or "discharge" together with "diagnosis".
- **Prescription:** checked after discharge summaries, which also list medicines.
- **Lab report:** a lab keyword (reference range, units, NABL…) and either one recognised test or three result rows.
  An earlier rule needed three rows, and the evaluation found it threw away 16 of 97 short reports.

Only lab reports produce lab values. The report date is the collection date if printed, then the report date, then the
registration date; for a discharge summary it is the discharge date, then the admission date. Dates are read in the
formats Indian labs use (`08/07/2025`, `08.07.2025`, `08-Jul-2025`, `2025-07-08`).

## 4.5 Normalising a row

**Which test is it?** The printed name is normalised (case, punctuation, spacing) and looked up among 68 aliases of 18
tests ("SGPT", "ALT (SGPT)", "Alanine Aminotransferase" → ALT). Fuzzy matching forgives typos *inside* words
only. The library's usual "token set" score matched MCH to Haemoglobin, VLDL to LDL and Non-HDL to HDL, which would
put wrong values on charts. An unmapped row is safe; a wrongly mapped one is not.

**Units.** OCR misreads are mapped back (`ulU/mL` → µIU/mL; m9/dL, m/dl, mdl → mg/dL). Values in another unit are
converted to the test's canonical unit with fixed factors: glucose mmol/L × 18.016, creatinine µmol/L ÷ 88.4, and
HbA1c mmol/mol → % with the IFCC↔NGSP formula (53 mmol/mol → 7.00%). Both the printed and the converted value are
stored.

**Flags** come from the report's own printed range, not from a textbook range, because labs differ.

**Confidence.** Each row starts at 0.85, multiplied by the page's OCR confidence, and loses points if:

| Condition | Penalty |
|---|---|
| test not recognised | 0.2 |
| fuzzy (not exact) name match | proportional to the mismatch |
| value outside a wide plausibility range for the test | 0.3 |
| printed H/L disagrees with the computed flag | 0.3 |

Either of the last two alone pushes a row below the review threshold (0.6). This is deliberate: a misread "72" for
"7.2" on a clean PDF must not skip review.

## 4.6 Review

A report with low-confidence rows is marked *Needs review*. The review screen shows the original report next to the
extracted rows and lets the user correct a value, unit or test. Unconfirmed
low-confidence points are marked on charts. Corrections are stored as verified.

## 4.7 Search chunks

Every processed document is also split into passages for document search (Chapter 6): pages in windows of 300 words
(about 400 tokens) with a 45-word overlap, plus recognised discharge sections (Diagnosis, Course in Hospital,
Advice on Discharge, Follow up…). Since `chunk-v2`, sections longer than the window are split with the same overlap,
and each chunk cites only the pages contributing its words. Existing documents require reindexing; the published
90-question test predates this change. Lab values themselves are not searched as text: value
and trend questions go to SQL. Each passage is embedded with bge-m3 when the worker processes the document.
