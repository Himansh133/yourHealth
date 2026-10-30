# Evaluation harness (plan section 14)

Synthetic data only: patients, reports and answers are generated, so the right answer is always known.

Run from `backend/` (the harness uses the backend's own code and `.env`):

```bash
cd backend
PYTHONPATH=.. .venv/bin/python -m eval.generator.build                 # dataset v1 -> eval/data/v1 (not in git)
PYTHONPATH=.. .venv/bin/python -m eval.runners.run_extraction --split dev
PYTHONPATH=.. .venv/bin/python -m eval.runners.run_extraction --split test   # only for the final number
.venv/bin/pytest ../eval/tests                                         # harness tests
```

The dataset is deterministic for a seed (default 1), so it isn't committed; results in `results/` are.
Tune on `dev`; run `test` once per change you want to report. Synthetic layouts are cleaner than real reports,
so treat these numbers as an upper bound.

## Long-document development probe

```bash
PYTHONPATH=.. .venv/bin/python -m eval.runners.retrieval_challenge \
  --out ../eval/results/2026-10-31_retrieval_dev.json
```

Uses the locally installed embedding and reranker models, without database changes or LLM calls. Six questions
cover diet and follow-up advice in three similar discharge notes longer than 1,000 words. It compares dense search
with and without reranking the top ten candidates, at 190/300/450-word windows, reporting MRR and Recall@1/3/6/10.
Gold requires the complete answer sentence in the correct document. This is a development diagnostic, **not** the
production hybrid search (PostgreSQL full-text fusion is absent), an answer-quality ablation, or a new holdout.

Long sections now use `chunk-v2`. Existing stored documents need reindexing to receive those chunks. The probe
chunks in memory and leaves the published v2 evaluation database unchanged.

## Extraction recovery diagnostics

```bash
PYTHONPATH=.. .venv/bin/python -m eval.runners.run_extraction --split dev --data ../eval/data/v1 \
  --stamp 2026-10-31-review-recovery
```

Damaged-unit recovery retains a clearly separated value and exact dictionary name for review. It preserves the
unreadable unit, leaves canonical values empty, and lowers confidence below the review threshold. This can improve
row coverage without improving strict whole-row F1, since an unreadable unit remains an error. Compare test-found,
value accuracy and unit accuracy alongside F1; do not count a review candidate as a fully corrected row.
