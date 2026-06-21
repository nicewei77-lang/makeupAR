# AGENTS.md

## Scope

- This repo is for pre-product technical validation of React Native + Unity + AR Foundation on a real iPhone, then validation-only AR makeup engine feasibility.
- Stay inside the current named milestone or explicitly named roadmap review/edit.
- Derive the current milestone from `TECH_VALIDATION_RESULT.md` > `Next Milestone Boundary` unless the user explicitly names a different milestone.
- Use `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` only after the M6/M7/M8 foundation path is in scope, or when the user explicitly asks about AR engine validation planning.
- Do not start product implementation, AI/backend/admin/payment/community work, commercial SDK integration, Android work, or product-quality makeup rendering unless the milestone or user explicitly asks.
- AI readiness in this repo means schema/evidence handoff only, such as `FaceFeatureSnapshot`; it does not mean AI model inference, recommendation, backend upload, or raw-frame storage.

## Required Reading

- Read `TECH_VALIDATION_TEST_PLAN.md` first.
- Read `TECH_VALIDATION_RESULT.md` next.
- Treat `TECH_VALIDATION_TEST_PLAN.md` as the stable validation contract.
- Treat `TECH_VALIDATION_RESULT.md` as the latest status, evidence, milestone history, and next boundary.
- For AR engine validation planning or implementation, read `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` after the two root validation docs.
- For research-backed AR/beauty engine decisions, also read the relevant files under `docs/roadmaps/research/`, especially the AR engine research report and beauty AR benchmark report.

## Document Rules

- Keep root active docs limited to `AGENTS.md`, `TECH_VALIDATION_TEST_PLAN.md`, and `TECH_VALIDATION_RESULT.md`.
- Do not update `TECH_VALIDATION_TEST_PLAN.md` for progress/status unless correcting the validation contract itself.
- Create `M*_..._PLAN.md` only as a temporary session plan.
- Create `E*_..._PLAN.md` only as a temporary AR engine validation session plan.
- After a session completes, absorb the result into `TECH_VALIDATION_RESULT.md` and delete the temporary plan.
- Put reusable procedures in `docs/runbooks/`.
- Keep roadmap/research docs under `docs/roadmaps/`; keep the current working plan under `docs/roadmaps/active/`; do not promote them to root active docs.

## Milestone Boundaries

- M6 must prove Unity -> RN events before M7, AR alignment, region masks, texture work, or AI readiness.
- M7 must prove re-entry stability or document a clear Yellow workaround before AR engine renderer work.
- M8 must separate integration Green from visual makeup readiness; do not mark face-fitted rendering Green before E1/E3 evidence.
- E1 must prove camera/feed/face mesh alignment before region mask or texture validation.
- E3 validates only `lip`, `cheek`, and `eye`; other face regions stay future product scope unless explicitly added.
- E5 AI readiness is a no-inference feature snapshot handoff, not AI product work.

## Evidence and Cleanup

- Before marking a milestone complete, cite concrete evidence: command output, logs, screenshots, or real-device confirmation.
- A milestone is not complete until `TECH_VALIDATION_RESULT.md` records the decision, evidence, known limitations, and next boundary.
- Store evidence under `evidence/logs/`, `evidence/screenshots/`, or `evidence/screen-recordings/`.
- Decision screen recordings must be at least 10 seconds unless the user explicitly accepts a shorter artifact; scenario- or cycle-based milestones still need enough footage to show the required scenario.
- When runtime console output is decision evidence, capture the full stream to `evidence/logs/` with `tee` or an equivalent method; summary-only logs must be labeled as summaries.
- Store feature snapshot examples as logs or runbook-linked text artifacts; do not store raw camera frames by default.
- Do not keep generated/cache state in the repo: `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode `derived-data/`, or `.DS_Store`.
