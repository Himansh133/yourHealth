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
