# De-identified Longitudinal Demo Import

User authorized pushing the completed features and creating a demo account with roughly 100 reports from one internet-sourced patient. Never import identifiable private patient histories or combine subjects.

Source: MIMIC-IV Clinical Database Demo 2.2, PhysioNet, https://doi.org/10.13026/dp1f-ex47 (ODbL 1.0). Public demo excludes free-text clinical notes and has no allergy table. Reconstructed PDFs must state this, and must not be called original hospital scans or original doctor notes.

- [x] Push previously verified viva features after staged secret inspection; exclude credentials, raw data and pre-existing brag-output.
- [x] Download official public tables to ignored eval/data/internet-demo and record URLs/hashes.
- [x] Test single-subject selection, unchanged measurement values, specimen-safe lab mapping, consistent date rebasing and absent allergy information.
- [x] Build a reproducible importer rendering all available lab groups and prescription history for one subject. Rendered date shifts are explicitly documented; original source timestamps remain in every PDF and a manifest.
- [ ] Create a dedicated patient account/profile locally, import files through validation, storage and the real extraction/indexing worker, retaining prescription order dates and unconfirmed historical medication status.
- [x] Enable patient-only allergy endpoints with ownership/doctor-denial tests so the missing status can be viewed without enabling doctor access routes.
- [ ] Validate login, counts, source file access, trends, medicine history, allergy unknown status, doctor-sheet generation and unauthorized access. Append credentials/profile IDs to ignored passwords.md with restricted permissions; never print or commit the password.
- [ ] Review importer, run targeted tests, stage/inspect/push code only. Raw downloads, derived clinical data, passwords and runtime logs stay ignored and local.

Constraints: preserve source values and units; never assign a serum test identity to urine/CSF/body-fluid results; never invent allergy records, diagnoses, ranges or current medicines. The generated doctor sheet is an application summary of released historical data, not a treating doctor's note. New account only; no mutation of existing patient records.

Execution evidence:
- Prior features pushed as 3c3432e on feat/viva-demo-evidence after staged secret inspection. PDF assets marked binary with .gitattributes.
- User confirmed genuine de-identified records preferred over synthetic fallback. Selected public subject10035631 only; 378 lab timestamp groups, 10,263 source lab rows, 786 prescription orders, 8 admissions; exported393 documents.
- Independent review found mutable date/manifest resume identity, a medication crash duplication window, and misleading summary classification. Regressions reproduced before fixes. Dates/source hashes are frozen, state writes are atomic, source-order medication UUIDs are stable, and the source summary remains other.
- Import uses private S3 storage and normal validation/extraction/indexing. Initial full-precision indexing was replaced by the installed quantized bge-m3 export for bulk throughput; existing full-precision chunks remain valid in the same embedding space and the actual model name is retained. App configuration is unchanged.
- Added patient-only allergy route registration; access/doctor clinical routers remain disabled. Authorization tests include foreign users, viewers and doctor-account denial.
- Targeted backend/evaluation verification:41 passed. Frontend:96 passed with bounded worker concurrency; production build passed. An earlier unbounded frontend run hit an existing one-second async-test timeout under concurrent indexing load; bounded rerun passed without changing application behavior or test assertions.
- Real API login, private PDF access, foreign-profile denial and unknown allergy status verified while loading. Final full-count and doctor-sheet checks pending completion.
