# Complete module 20

Spec: `yourhealth-implementation-plan.md` section 20. User explicitly authorized all remaining work on 2026-11-02.

## Work and ownership

- [x] Finish admin bootstrap and correct account UI test selector.
- [ ] Consent: patient public codes, lookup limits, approve/deny, grants, revocation, clinic QR/codes, audit history.
- [ ] Allergies: patient CRUD, explicit unknown/none-confirmed state, document proposals and confirmation.
- [ ] Clinical views: SQL snapshot, scoped file access, doctor chat with citations and Redis TTL, three medicine checks.
- [ ] UI: patient consent/allergies and doctor home/snapshot/chat/check, with role navigation.
- [ ] WhatsApp: request notifications, consent buttons checked against current linked patient membership.
- [ ] Evaluation: access boundaries, allergy extraction, snapshot truth, medicine checks, doctor chat safety and citations.
- [ ] Stretch: report comparison and patient-approved doctor notes where implemented and verified.
- [ ] Integration: migrations, test suites, production build and independent review.

## Constraints and decisions

- Every clinical read requires a current verified doctor and an active patient grant; exclusions filter data before retrieval.
- Patient codes never authorize access. Invalid/unknown lookups have the same response.
- No clinical review is fabricated. Unreviewed allergy-class rows remain inactive; a reviewer has been requested.
- Existing patient data and unrelated local changes must be preserved.
- Root integrates routers and owns admin/WhatsApp/docs. Consent owns models and migration; clinical owns scoped clinical services; frontend owns UI. Shared database test runs are serialized.
- Prior frontend failure was an ambiguous heading selector (two headings matched `family`), corrected to the level-one `Family` heading; all six doctor portal tests now pass.
- Local administrator created successfully. Credentials are delivered privately in the conversation, never committed.
