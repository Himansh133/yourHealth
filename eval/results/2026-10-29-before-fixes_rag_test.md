# Q&A results (test split, 46 questions)

Same LLM (GMI Cloud, DeepSeek-V4-Flash) for every system. Synthetic patients; gold answers are known.

| Metric | B0: plain LLM, all report text | B1: vector RAG, top 6 | Ours |
|---|---|---|---|
| Numeric accuracy, value questions (English) | 89% (8/9) | 78% (7/9) | 100% (9/9) |
| Numeric accuracy, value questions (Hindi) | 67% (6/9) | 56% (5/9) | 78% (7/9) |
| Trend direction correct (LLM judge) | 89% (8/9) | 78% (7/9) | 89% (8/9) |
| Medicine: names the right generic | 80% (4/5) | 0% (0/5) | 100% (5/5) |
| Abstains on a test never done | 100% (9/9) | 100% (9/9) | 100% (9/9) |
| Wrongly abstains on answerable questions (lower is better) | 0% (0/32) | 16% (5/32) | 6% (2/32) |
| Answers with a number not in the records (lower is better) | 9% (3/33) | 4% (1/27) | 23% (8/35) |
| Safety: no advice + points to the doctor (treatment) | 40% (2/5) | 40% (2/5) | 100% (5/5) |
| Cross-profile leaks | 0 by design (one profile's text only) | 0 by design (one profile's text only) | 0 |
| Median / p95 latency | 3.2 s / 14.5 s | 3.0 s / 9.7 s | 4.9 s / 17.9 s |
