# AGENTS.md

## Scope
- This repo is for pre-product technical validation of React Native + Unity + AR Foundation on a real iPhone, then validation-only AR makeup engine feasibility.
- Stay inside the current named milestone or explicitly named roadmap review/edit.
- Derive the current milestone from `TECH_VALIDATION_RESULT.md` > `Next Milestone Boundary` unless the user explicitly names a different milestone.
- Use `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` only after the M6/M7/M8 foundation path is in scope, or when the user explicitly asks about AR engine validation planning.
- Do not start product implementation, AI/backend/admin/payment/community work, commercial SDK integration, Android work, or product-quality makeup rendering unless the milestone or user explicitly asks.
- AI readiness in this repo means schema/evidence handoff only, such as `FaceFeatureSnapshot`; it does not mean AI model inference, recommendation, backend upload, or raw-frame storage.

## Required Reading
- Read `TECH_VALIDATION_TEST_PLAN.md` first, then `TECH_VALIDATION_RESULT.md`.
- Treat the test plan as the stable validation contract and the result doc as latest status, evidence, milestone history, and next boundary.
- For AR engine validation planning or implementation, also read `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` and relevant research files.
- For E7 visual product-readiness work, read `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` and the four `docs/roadmaps/research/E7_AXIS*.md` reports.

## Build Loop
- Every Unity/RN real-device validation session should regenerate and sync `UnityFramework.framework` before the RN iOS build.
- Use `bash scripts/build_m3_unityframework.sh` from the repo root; do not hand-run raw Unity batchmode commands unless debugging the script itself.
- The script exports Unity iOS, verifies ARKit links, builds `UnityFramework` with signing disabled, copies Unity `Data`, and syncs RN/package framework paths.
- After sync, run from `rn/MakeupARValidation`: `npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK`.
- The 2026-06-21 Unity export blocker was stale/conflicting Unity Hub/Editor Licensing Client IPC, not E2 code (`Unsupported protocol version '1.18.1'`, lost client connection).
- Before Unity builds, close Unity/Hub and ensure no Unity/Licensing processes remain; if licensing blocks, remove `/tmp/Unity-LicenseClient*`, reopen Hub/Editor to confirm Personal license, then rerun the script.
- Keep the package-local `RNUnityView.mm` timing patch caveat in mind until it is made durable; stale package frameworks previously caused missing Unity objects/events.

## Document Rules
- Keep this file at 50 lines or fewer.
- Keep root active docs limited to `AGENTS.md`, `TECH_VALIDATION_TEST_PLAN.md`, and `TECH_VALIDATION_RESULT.md`.
- Do not update `TECH_VALIDATION_TEST_PLAN.md` for progress/status unless correcting the validation contract itself.
- Create `M*_..._PLAN.md` or `E*_..._PLAN.md` only as temporary session plans.
- After a session completes, absorb the result into `TECH_VALIDATION_RESULT.md` and delete the temporary plan.
- Put reusable procedures in `docs/runbooks/`; keep roadmap/research docs under `docs/roadmaps/`.

## Milestone Boundaries
- M6 must prove Unity -> RN events before M7, AR alignment, region masks, texture work, or AI readiness.
- M7 must prove re-entry stability or document a clear Yellow workaround before AR engine renderer work.
- M8 must separate integration Green from visual makeup readiness; do not mark face-fitted rendering Green before E1/E3 evidence.
- E1 must prove camera/feed/face mesh alignment before region/texture work; E3 validates only `lip`, `cheek`, and `eye`, with other regions future scope unless explicitly added.
- E5 AI readiness is a no-inference feature snapshot handoff, not AI product work.
- E7 is validation/hardening only: keep `lip`/`cheek`/`eye` decisions separate, require visual/performance evidence, and never promote M7 or product readiness without matching evidence.

## Evidence and Cleanup
- Before marking a milestone complete, cite concrete evidence: command output, logs, screenshots, or real-device confirmation; E7 also needs FPS/frame-time, thermal, memory, latency, region G/Y/R, and demo-look evidence.
- A milestone is not complete until `TECH_VALIDATION_RESULT.md` records the decision, evidence, known limitations, and next boundary.
- Store evidence under `evidence/logs/`, `evidence/screenshots/`, or `evidence/screen-recordings/`.
- Decision screen recordings must be at least 10 seconds unless the user explicitly accepts a shorter artifact; scenario- or cycle-based milestones still need enough footage to show the required scenario.
- When runtime console output is decision evidence, capture the full stream to `evidence/logs/` with `tee` or an equivalent method; summary-only logs must be labeled as summaries.
- Store feature snapshot examples as logs or runbook-linked text artifacts; do not store raw camera frames by default.
- Do not commit generated/cache state: `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode derived data, `evidence/`, or `.DS_Store`.
