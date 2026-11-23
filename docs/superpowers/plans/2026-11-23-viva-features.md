# Viva Features Implementation Plan

> Implement inline, chunk by chunk, using executing-plans, test-driven-development and verification-before-completion. The user explicitly authorized implementation; do not add approval rounds. No commits or pushes without approval.

**Goal:** Make YourHealth easier to understand, demonstrate and evaluate with five useful, evidence-based additions.
**Architecture:** Extend the existing patient-only chat endpoint with actual evidence/validation metadata; use a generated aggregate-only evaluation artifact; reuse documents, lab results and trends for overview/comparison. Persist feedback against server-created chat records with profile and author checks.
**Tech Stack:** FastAPI, SQLAlchemy/PostgreSQL, React/TypeScript/Tailwind, pytest and Vitest. No new dependencies.
**Spec:** User-approved five-feature recommendation in this conversation, including suggested questions, clear demo data and consistent states.

## Global Constraints
- Preserve all pre-existing uncommitted changes, including the recent chat readability work and brag-output.
- Do not commit or push without explicit approval; keep .local-credentials.md ignored and untracked.
- Do not enable the incomplete doctor clinical-access module.
- Show real execution metadata, never model reasoning or invented confidence.
- Label historical synthetic evaluation honestly; no clinical validation claims or patient excerpts in evaluation assets.
- Keep the current teal/slate visual language, accessible labels, mobile layouts and source links.

## Review Focus
- Cross-profile/other-user feedback access must fail without exposing a chat record.
- Missing or incompatible units and qualified values must never produce a numeric comparison.
- Duplicate test rows must be identified rather than silently paired.
- Empty, loading, error and profile-switch states must not show stale data.
- Historical metrics must preserve denominators and limitations; demo fixtures must be isolated from real records.

## Chunk 1: Answer inspection
Files: backend/app/services/chat/{answer,service}.py; frontend/src/api/types.ts; frontend/src/pages/{ChatPanel,AnswerInspection}.tsx and tests.
- [x] Write and run failing API/UI tests for evidence excerpts, honest validation status and fallback.
- [x] Return retrieved evidence and generation attempt/check metadata from the actual pipeline, preserving translation metadata.
- [x] Add an expandable panel showing route, outcome and source-linked excerpts, with no hidden reasoning.
- [x] Run answer pipeline, chat API and ChatPanel tests.

## Chunk 2: Evaluation dashboard
Files: eval/runners/export_dashboard.py and tests; frontend/src/data/evaluation.json; frontend/src/pages/EvaluationPage.tsx; App.tsx; Layout.tsx.
- [x] Test aggregate extraction against frozen v2q2 result files; artifact contains metrics, denominators and provenance only.
- [x] Build a reproducible aggregate exporter and a dashboard comparing B0/B1/Ours, with historical/synthetic caveats and limitations.
- [x] Register an authenticated evaluation route and navigation link.
- [x] Run exporter tests, dashboard tests and typecheck.

## Chunk 3: Patient overview
Files: frontend/src/pages/{OverviewPanel,ProfilePage}.tsx; App.tsx; frontend tests.
- [x] Test empty/error states, latest dated report, latest flags, pending review and recent changes using existing API fixtures.
- [x] Add overview as the profile landing page and keep reports at /profiles/:pid/reports.
- [x] Show sourced latest values and recent comparisons, with verification labels and explicit clinical limits.
- [x] Run overview/navigation/profile tests and typecheck.

## Chunk 4: Report comparison
Files: frontend/src/pages/ReportComparisonPanel.tsx and tests; ProfilePage.tsx; App.tsx.
- [x] Test shared tests, missing tests, nonnumeric/qualified/incompatible units and duplicate rows.
- [x] Add two report selectors and a responsive comparison table using existing per-document lab APIs.
- [x] Show printed values, comparable changes only, report dates, verification status and source links.
- [x] Run comparison and navigation tests.

## Chunk 5: Answer feedback
Files: backend/app/db/models.py; backend/alembic/versions/*chat_feedback.py; backend/app/api/routes/chat.py; frontend/src/{api,pages} feedback changes and tests.
- [x] Test persistence, feedback updates, rejected invalid categories, unauthorized/other-profile/other-author access.
- [x] Store web chat records server-side; return answer_id; save one category per answer and author with profile checks.
- [x] Add accessible feedback controls with saving/success/error and retry behavior.
- [x] Run backend chat/security tests, migration upgrade/downgrade on test database and frontend feedback tests.

## Chunk 6: Demo polish and verification
Files: frontend chat/profile/demo UI; eval demo fixture tooling; DEMO.md; this plan.
- [x] Add suggested questions, isolated synthetic three-report demo fixture, and repeatable demo instructions.
- [x] Verify full backend/frontend suites, typecheck/build, aggregate regeneration, migration, secret-ignore and diff checks.
- [x] Obtain independent code review, fix material findings and verify again.
- [x] Report the completed chunks and exact limitations; ask only before any requested commit/push.

## Execution ledger
- Starting state: 10 modified tracked files from the prior chat task, plus untracked brag-output/. No existing files reset or stashed.
- Ruling: continue in the shared checkout so the already-tested uncommitted chat changes remain the implementation baseline. No commits, branch integration or pushes are authorized.

- Chunk 1 complete: 42 backend tests and 10 ChatPanel tests passed; inspection shows real pipeline metadata.
- Chunk 2 complete: exporter test, evaluation UI test and typecheck passed. Aggregate-only JSON generated reproducibly from frozen benchmark files.
- Chunks 3–4 complete: 17 overview, comparison and profile-navigation tests passed; typecheck passed.
- Chunk 5 complete: 48 backend chat/answer tests and 12 feedback/chat UI tests passed; typecheck passed.

- Independent review completed by viva_review. Feedback authorization and migration chain passed review. Two important integration issues were reproduced and fixed: qualifiers/duplicate dates in chat evidence, and queue-submit failure recovery on upload retry.
- Additional accuracy fixes: undated reports excluded from trend comparisons; small changes below display precision identified explicitly; percentage-valued tests display absolute changes in percentage points; all evidence source kinds link to their source.
- Review regression evidence: four lab/queue regressions failed before implementation; 59 combined lab/upload/chat tests passed afterward. The undated-report regression also failed before its fix and is included in the final suite.
- Demo integration: generated PDFs were uploaded and processed through the actual worker with isolated test storage; all nine rows mapped to canonical tests and all report dates were recovered.
- Migration: upgrade head → downgrade previous revision → upgrade head passed on a disposable database; additive upgrade to b42c73f00102 applied locally.
- Browser: overview, comparison, evaluation, demo and chat exercised in Chrome at 1280px and 390px using explicitly synthetic mocked API data. No document-level horizontal overflow or visible API errors.
- Frontend final verification: 95 tests passed; production build passed with the existing bundle-size warning. No live provider/model-quality evaluation was performed.
- Test execution note: an initial full database run overlapped a targeted run against the same test database, producing deadlock/table-reset errors. Database tests are being rerun sequentially before completion.

- Final verification complete: backend batch 1 (23 files) 361 passed; backend batch 2 (remaining 23 files) 239 passed; evaluation tooling 57 passed. All 600 backend and 57 evaluation tests passed in completed runs. The interrupted combined run is not counted as verification.
- Frontend final result: 95 passed across 20 files; TypeScript/production build passed. Existing chart test-layout and bundle-size warnings remain.
- Browser final smoke passed for all five screens at both 1280px and 390px. Temporary Chrome and Vite preview processes were stopped.
- Final review findings addressed with regression checks. No deferred review findings remain. No new live-model benchmark or clinical validation is claimed.
- Integration state: shared checkout retained, nothing staged, committed or pushed; .local-credentials.md remains ignored/untracked. Pre-existing brag-output/ remains untouched.
