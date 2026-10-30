# Q&A results (test split, 51 questions)

Same LLM (GMI Cloud, DeepSeek-V4-Flash) for every system. Synthetic patients; gold answers are known.

| Metric | Ours | Ours without router (all to search) | Ours without reranker | Ours without validator |
|---|---|---|---|---|
| Numeric accuracy, value questions (English) | 100% (9/9) | 78% (7/9) | 100% (9/9) | 100% (9/9) |
| Numeric accuracy, value questions (Hindi) | 100% (9/9) | 78% (7/9) | 100% (9/9) | 100% (9/9) |
| Trend direction correct (LLM judge) | 89% (8/9) | 67% (6/9) | 89% (8/9) | 89% (8/9) |
| Medicine: names the right generic | 100% (5/5) | 0% (0/5) | 100% (5/5) | 100% (5/5) |
| Abstains on a test never done | 100% (9/9) | 100% (9/9) | 100% (9/9) | 100% (9/9) |
| Wrongly abstains on answerable questions (lower is better) | 0% (0/37) | 8% (3/37) | 0% (0/37) | 0% (0/37) |
| Answers with a number not in the records (lower is better) | 0% (0/42) | 8% (3/36) | 0% (0/42) | 0% (0/42) |
| Safety: no advice + points to the doctor (treatment) | 100% (5/5) | 60% (3/5) | 100% (5/5) | 100% (5/5) |
| Discharge summary: gives the diagnosis, ignores the planted instruction | 100% (5/5) | 100% (5/5) | 100% (5/5) | 100% (5/5) |
| Prompt injection followed (lower is better) | 0% (0/5) | 0% (0/5) | 0% (0/5) | 0% (0/5) |
| Cross-profile leaks | 0 | 0 | 0 | 0 |
| Median / p95 latency | 6.3 s / 34.2 s | 17.8 s / 57.8 s | 6.6 s / 26.8 s | 7.4 s / 34.7 s |
