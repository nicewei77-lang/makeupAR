# AGENTS.md

## Scope

- This repo is for pre-product technical validation of React Native + Unity + AR Foundation on a real iPhone.
- Stay inside the current named milestone.
- Derive the current milestone from `TECH_VALIDATION_RESULT.md` > `Next Milestone Boundary` unless the user explicitly names a different milestone.
- Do not start product implementation, AI/backend/admin/payment/community work, makeup-quality rendering, UnityFramework embed, or RN-Unity messaging unless the milestone or user explicitly asks.

## Required Reading

- Read `TECH_VALIDATION_TEST_PLAN.md` first.
- Read `TECH_VALIDATION_RESULT.md` next.
- Treat `TECH_VALIDATION_TEST_PLAN.md` as the stable validation contract.
- Treat `TECH_VALIDATION_RESULT.md` as the latest status, evidence, milestone history, and next boundary.

## Document Rules

- Keep root active docs limited to `AGENTS.md`, `TECH_VALIDATION_TEST_PLAN.md`, and `TECH_VALIDATION_RESULT.md`.
- Do not update `TECH_VALIDATION_TEST_PLAN.md` for progress/status unless correcting the validation contract itself.
- Create `M*_..._PLAN.md` only as a temporary session plan.
- After a session completes, absorb the result into `TECH_VALIDATION_RESULT.md` and delete the temporary plan.
- Put reusable procedures in `docs/runbooks/`.

## Evidence and Cleanup

- Before marking a milestone complete, cite concrete evidence: command output, logs, screenshots, or real-device confirmation.
- A milestone is not complete until `TECH_VALIDATION_RESULT.md` records the decision, evidence, known limitations, and next boundary.
- Store evidence under `evidence/logs/`, `evidence/screenshots/`, or `evidence/screen-recordings/`.
- Do not keep generated/cache state in the repo: `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode `derived-data/`, or `.DS_Store`.
