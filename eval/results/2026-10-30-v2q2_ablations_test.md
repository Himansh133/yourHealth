# Q&A results (test split, 90 questions)

Same LLM (GMI Cloud, DeepSeek-V4-Flash) for every system. Synthetic patients; gold answers are known.

| Metric | Ours | Ours without router (all to search) | Ours without reranker | Ours without validator |
|---|---|---|---|---|
| Numeric accuracy, value questions (English) | 100% (9/9) | 78% (7/9) | 100% (9/9) | 100% (9/9) |
| Numeric accuracy, value questions (Hindi) | 100% (9/9) | 100% (9/9) | 100% (9/9) | 100% (9/9) |
| Trend direction correct, English (LLM judge) | 89% (8/9) | 89% (8/9) | 89% (8/9) | 89% (8/9) |
| Trend direction correct, Hindi (LLM judge) | 100% (9/9) | 100% (9/9) | 89% (8/9) | 89% (8/9) |
| Document questions: states the fact from the document | 100% (24/24) | 100% (24/24) | 100% (24/24) | 100% (24/24) |
| Medicine: names the right generic | 100% (8/8) | 0% (0/8) | 100% (8/8) | 100% (8/8) |
| Abstains on a test never done | 100% (9/9) | 89% (8/9) | 100% (9/9) | 100% (9/9) |
| Wrongly abstains on answerable questions (lower is better) | 0% (0/73) | 11% (8/73) | 0% (0/73) | 0% (0/73) |
| Answers with a number not in the records (lower is better) | 0% (0/81) | 0% (0/68) | 0% (0/81) | 0% (0/81) |
| Safety: no advice + points to the doctor (treatment) | 100% (8/8) | 75% (6/8) | 100% (8/8) | 100% (8/8) |
| Discharge summary: gives the diagnosis, ignores the planted instruction | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) |
| Prompt injection followed (lower is better) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) |
| Shown the facts table instead of a written answer (lower is better) | 2% (2/90) | 7% (6/90) | 2% (2/90) | 0% (0/90) |
| Hindi questions answered in Hindi | 100% (18/18) | 72% (13/18) | 100% (18/18) | 100% (18/18) |
| Cross-profile leaks | 0 | 0 | 0 | 0 |
| Median / p95 latency | 5.3 s / 10.1 s | 5.0 s / 11.3 s | 4.4 s / 9.9 s | 5.3 s / 7.9 s |
