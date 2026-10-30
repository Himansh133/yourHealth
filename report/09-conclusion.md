# 9. Conclusion and future work

## 9.1 What was built

YourHealth takes the lab reports a family already has, as PDFs or WhatsApp photos, and turns them into per-test
trends, links them to each person's medicines through label-sourced facts, answers questions about them in English and
Hindi with a source for every claim, and lets the family share a one-page summary with a doctor by QR code and PIN.

## 9.2 What the evaluation shows

On a clean synthetic test set (Chapter 8), against the same language model used as a plain chatbot and as vector RAG:

- **Values:** 100% correct in English and Hindi (baselines 56–78%), with no made-up numbers (baselines 3–6%).
- **Medicines:** 100% name the right generic (baselines 0%).
- **Safety:** treatment questions answered safely 100% of the time (baselines 25%).
- **Answerable questions:** none wrongly declined (baselines 20%).
- **Extraction:** F1 95.1% on new reports, every value read was correct, and p95 latency was 8.2 s.

The ablation explains why. Sending every question to document search, as a typical RAG system does, loses the
medicine answers and the safety reply and lets made-up numbers through. **The contribution is the routing to
structured data and fixed safe replies, not a better retriever.**

## 9.3 Limitations

- **Synthetic data.** Four clean layouts don't capture the variety of real Indian reports; extraction on clean and
  degraded photos is 83–90%, and real reports will be harder.
- **Small test groups** (9 patients, 5–9 questions per type) and **one language model**.
- **The reranker and the validator** showed no measurable gain on this set; they are kept as safeguards, not because the
  numbers prove them.
- **Reference data** (LOINC codes, brand compositions, Hindi glosses, the 32 effect rows) still needs review by a
  pharmacist, a clinician and a native Hindi speaker.
- **WhatsApp** has been tested end to end only against a local stand-in for Meta's API, not with a real number.
- **The router's LLM classifier** can label the same question differently between runs.

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
