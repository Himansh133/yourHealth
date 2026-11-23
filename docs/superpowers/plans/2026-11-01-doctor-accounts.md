# Doctor accounts and approval Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement step 1 of module 20: doctor signup, admin verification, and separate patient, doctor, and admin account access.

**Architecture:** Extend the existing users table and session authentication; add a doctors table and separate doctor/admin routers. Reuse React form controls and the existing layout. Keep the existing patient data and public share flow working.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, PostgreSQL, React, TypeScript, Tailwind, pytest, Vitest.

**Spec:** `yourhealth-implementation-plan.md`, sections 20.3, 20.4, 20.11, 20.13, 20.14, and step 1 of 20.16.

## Global Constraints

- Signup collects full name, registration number, registration council, specialty, clinic name.
- Verification starts as `unverified`; an admin approves manually after checking credentials.
- Unverified doctors can log in but cannot request or view patient records.
- Doctor accounts cannot call patient endpoints and the reverse.
- Doctors never get a broad list of patients.
- No diagnosis suggestions, differential lists, dose recommendations, or full interaction checking.

## Design and scope decisions

The supplied module 20 is the design specification and the user's request authorizes starting its build sequence. This milestone implements its first step end to end; patient grants and all clinical features remain tracked below. Native execution reuses current infrastructure rather than creating a second login system. Account role comes from SQL on every request, never a user-submitted token claim. Registration cannot choose admin privileges or verification status. Admin bootstrap is an explicit local command requiring a new email and password; it never promotes existing patient accounts silently. No demo doctor is automatically verified.

The UI retains the existing teal/slate design, labeled forms, keyboard focus, and accessible status text. A doctor's home shows their verification status and explains that patient access is not available in this milestone. The admin page filters doctor applications and supports verify/reject, preserving review metadata.

## Review Focus

1. Blank/whitespace credentials must fail validation before any account is created.
2. Duplicate email must return 409 and leave no partial doctor record.
3. Public registration fields cannot grant admin or verified status.
4. A doctor with an accidental profile membership still cannot use patient endpoints.
5. Review state is read from SQL on the next request; existing patient sessions continue working after migration.

### Task 1: Database and account APIs

**Files:** `backend/app/db/models.py`, new Alembic migration, `backend/app/api/deps.py`, `backend/app/api/routes/auth.py`, new `doctor.py` and `admin.py`, `backend/app/main.py`, `backend/tests/test_doctor_accounts.py`.

**Interfaces:** `UserOut.account_type`; `GET /doctor/me`; `POST /doctor/register`; `GET /admin/doctors?status=unverified`; `POST /admin/doctors/{uid}/verify` and `/reject`; patient endpoints use `patient_user`, shared auth uses `current_user`.

- [ ] Write API tests for signup/login, defaults, credential validation, duplicates, approval metadata, filter, and role boundaries.
- [ ] Run `.venv/bin/pytest tests/test_doctor_accounts.py -q`; expect missing routes/fields to fail.
- [ ] Implement additive migration, models, dependencies, routes, and review audit metadata.
- [ ] Run doctor/account tests and existing auth/profile tests; expect all pass.

### Task 2: Doctor registration, status, and admin screens

**Files:** frontend account types/endpoints, auth/route wiring, Layout/LoginPage, new doctor register/home and admin pages plus tests.

**Interfaces:** `/doctor/register`, `/doctor`, `/admin/doctors`; account home determined by patient/doctor/admin role.

- [ ] Write tests for doctor registration, verification status, admin decisions, and account-specific navigation; run and observe failure.
- [ ] Implement screens using existing controls, field validation, pending states, and role guards.
- [ ] Run `npm test` and `npm run build`; expect success.

### Task 3: Bootstrap, migration, and verification

**Files:** `backend/app/admin.py`, README, this progress record.

- [ ] Add explicit local admin creation using a prompted password and test rejection of existing email.
- [ ] Apply `alembic upgrade head`, verify old patient remains patient and records unchanged.
- [ ] Run full backend/frontend suites and build, inspect diff and get an independent review.
- [ ] Record results and remaining module steps. Do not commit/publish unrelated work.

## Remaining module 20 steps

- [ ] Step 2: public patient codes, access requests, approval/denial, scoped grants, clinic codes, audit history.
- [ ] Step 3: allergies and explicit unknown/no-known-allergy states, patient UI, parser proposals.
- [ ] Step 4: grant-filtered patient snapshot and document viewing.
- [ ] Step 5: clinical chat with scoped retrieval, citations and grant-limited Redis history.
- [ ] Step 6: three proposed-medicine checks and independently reviewed allergy class references.
- [ ] Step 7: module evaluation datasets and access/safety regression suite.

## Execution ledger

- Skills installed from the four requested repositories; persistent preference recorded in `~/.codex/AGENTS.md`.
- Ruling: implement the first complete milestone from the supplied build sequence, matching "start building"; do not expose clinical routes before scoped grants exist.
