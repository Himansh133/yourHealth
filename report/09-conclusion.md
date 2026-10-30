# 9. Conclusion and future work

## 9.1 What was built

YourHealth takes the lab reports a family already has, as PDFs or WhatsApp photos, and turns them into per-test
trends, links them to each person's medicines through label-sourced facts, answers questions about them in English and
Hindi with a source for every claim, and lets the family share a one-page summary with a doctor by QR code and PIN.

## 9.2 What the evaluation shows

On the expanded 90-question synthetic v2 test split at `9321fce` (Chapter 8), against the same language model used as a plain chatbot and as vector RAG:

- **Values:** 100% correct in English and Hindi (baselines 56–78%), with no made-up numbers (baselines 3–5%).
- **Medicines:** 100% name the right generic (baselines 0%).
- **Safety:** treatment questions answered safely 100% of the time (baselines 0–12%).
- **Answerable questions:** none wrongly declined (baselines 11%).
- **Document questions:** all three systems answered 24/24 correctly; this set does not separate their retrieval.
- **Extraction:** F1 95.1% on v2 reports; values were correct for matched rows, with missing rows and unit errors remaining.
- **Q&A latency:** median 5.3 s and p95 10.1 s on the expanded set. The earlier 57-question run had p95 8.2 s.

The ablation explains why. Sending every question to document search, as a typical RAG system does, loses the
medicine answers and reduces safe treatment replies to 75%. Made-up numbers were 0% in this run versus 15% in
the earlier 57-question run, so that outcome is variable. **The contribution is the routing to
structured data and fixed safe replies, not a better retriever.**

## 9.3 Limitations

- **Synthetic data.** Four clean layouts don't capture the variety of real Indian reports; extraction on clean and
  degraded photos is 83–90%, and real reports will be harder.
- **Small test groups** (9 patients, many categories with 5–9 questions) and **one language model**. The expanded test
  reused 57 previously evaluated questions; it is not a wholly untouched new holdout.
- **The reranker** showed no document-answer gain on these short, simple documents. **The validator** caught two
  computed follow-up dates, although dates are excluded from the aggregate made-up-number metric.
- **Unequal evidence access:** Ours has medicine reference facts unavailable to the report-only baselines. Medicine
  accuracy supports the system design, not a claim that its retriever is better.
- **Reference data** (LOINC codes, brand compositions, Hindi glosses, the 32 effect rows) still needs review by a
  pharmacist, a clinician and a native Hindi speaker.
- **WhatsApp** has been tested end to end only against a local stand-in for Meta's API, not with a real number.
- **The router's LLM classifier** can label the same question differently between runs.

Subsequent development work (Chapter 8.8) recovers damaged-unit values for review and bounds long section chunks.
A separate six-question retrieval probe improves top-one evidence retrieval from 3/6 to 6/6 with reranking at all
three tested sizes. These development diagnostics do not replace the published 90-question results.

## 9.4 Future work

1. **Real reports:** a small set of consented, de-identified reports to measure the real extraction gap; harder layouts
   (multi-page, two-column, repeated headers).
2. **A real WhatsApp deployment** with a Meta business number, message templates for replies outside the 24-hour window,
   and Hinglish questions translated before search.
3. **ABHA / ABDM integration** so reports can arrive from health lockers, not only as photos.
4. **Data protection:** a DPDP Act 2023 review, consent records, export and deletion on request.
5. **A local language model** behind the existing interface, so no patient text leaves the deployment.
6. **More languages** through the same answer-in-English, translate-and-check design.
7. **Doctor-facing summary:** a short generated paragraph on the doctor sheet, passed through the same validator.
