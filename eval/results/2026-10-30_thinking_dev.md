# Q&A results (dev split, 135 questions)

Same LLM (GMI Cloud, DeepSeek-V4-Flash) for every system. Synthetic patients; gold answers are known.

| Metric | Ours | Ours, LLM thinking off |
|---|---|---|
| Numeric accuracy, value questions (English) | 100% (21/21) | 100% (21/21) |
| Numeric accuracy, value questions (Hindi) | 100% (21/21) | 100% (21/21) |
| Trend direction correct (LLM judge) | 95% (20/21) | 100% (21/21) |
| Medicine: names the right generic | 100% (20/20) | 100% (20/20) |
| Abstains on a test never done | 100% (21/21) | 100% (21/21) |
| Wrongly abstains on answerable questions (lower is better) | 0% (0/94) | 0% (0/94) |
| Answers with a number not in the records (lower is better) | 0% (0/114) | 0% (0/114) |
| Safety: no advice + points to the doctor (treatment) | 100% (20/20) | 100% (20/20) |
| Discharge summary: gives the diagnosis, ignores the planted instruction | 100% (11/11) | 100% (11/11) |
| Prompt injection followed (lower is better) | 0% (0/11) | 0% (0/11) |
| Shown the facts table instead of a written answer (lower is better) | 0% (0/135) | 1% (1/135) |
| Hindi questions answered in Hindi | 100% (21/21) | 100% (21/21) |
| Cross-profile leaks | 0 | 0 |
| Median / p95 latency | 3.6 s / 20.5 s | 3.4 s / 9.0 s |
