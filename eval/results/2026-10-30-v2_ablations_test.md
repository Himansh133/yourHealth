# Q&A results (test split, 57 questions)

Same LLM (GMI Cloud, DeepSeek-V4-Flash) for every system. Synthetic patients; gold answers are known.

| Metric | Ours | Ours without router (all to search) | Ours without reranker | Ours without validator |
|---|---|---|---|---|
| Numeric accuracy, value questions (English) | 100% (9/9) | 89% (8/9) | 100% (9/9) | 100% (9/9) |
| Numeric accuracy, value questions (Hindi) | 100% (9/9) | 89% (8/9) | 100% (9/9) | 100% (9/9) |
| Trend direction correct (LLM judge) | 100% (9/9) | 100% (9/9) | 89% (8/9) | 89% (8/9) |
| Medicine: names the right generic | 100% (8/8) | 0% (0/8) | 100% (8/8) | 100% (8/8) |
| Abstains on a test never done | 100% (9/9) | 100% (9/9) | 100% (9/9) | 100% (9/9) |
| Wrongly abstains on answerable questions (lower is better) | 0% (0/40) | 10% (4/40) | 0% (0/40) | 0% (0/40) |
| Answers with a number not in the records (lower is better) | 0% (0/48) | 15% (6/41) | 0% (0/48) | 0% (0/48) |
| Safety: no advice + points to the doctor (treatment) | 100% (8/8) | 38% (3/8) | 100% (8/8) | 100% (8/8) |
| Discharge summary: gives the diagnosis, ignores the planted instruction | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) |
| Prompt injection followed (lower is better) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) |
| Shown the facts table instead of a written answer (lower is better) | 0% (0/57) | 18% (10/57) | 2% (1/57) | 2% (1/57) |
| Hindi questions answered in Hindi | 100% (9/9) | 100% (9/9) | 100% (9/9) | 89% (8/9) |
| Cross-profile leaks | 0 | 0 | 0 | 0 |
| Median / p95 latency | 3.3 s / 8.2 s | 5.2 s / 10.1 s | 3.1 s / 8.2 s | 3.4 s / 12.5 s |
