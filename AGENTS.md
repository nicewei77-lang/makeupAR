# AGENTS.md

## Scope
- This repo is for pre-product technical validation of React Native + Unity + AR Foundation on a real iPhone, then validation-only AR makeup engine feasibility.
- Stay inside the current named milestone or explicitly named roadmap review/edit. If asked for 10 items, complete/verify all 10 or explicitly mark unfinished items as blocked, skipped by user decision, or out of scope; never call a partial subset success. In generated plans, do not create nice-to-have sections/items; all plan items are required unless the user removes them from scope.
- Derive the current milestone from `TECH_VALIDATION_RESULT.md` > `Next Milestone Boundary` unless the user explicitly names a different milestone.
- Use `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` only after the M6/M7/M8 foundation path is in scope, or when the user explicitly asks about AR engine validation planning.
- Do not start product implementation, AI/backend/admin/payment/community work, commercial SDK integration, Android work, or product-quality makeup rendering unless the milestone or user explicitly asks.
- AI readiness in this repo means schema/evidence handoff only, such as `FaceFeatureSnapshot`; it does not mean AI model inference, recommendation, backend upload, or raw-frame storage.

## Required Reading
- Start each session with `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`; read `TECH_VALIDATION_TEST_PLAN.md` only when changing the validation contract or checking milestone/evidence rules.
- Treat the result snapshot as latest status, active docs, evidence summary, stop rules, and next boundary.
- For AR engine validation, read only the current milestone section of `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md`; if it conflicts with the result snapshot, the snapshot wins.
- For E7, lazy-load research by milestone: E7.3 uses `E7_AXIS1_*`, E7.4/E7.5 uses `E7_AXIS2_*`, E7.6 uses `docs/roadmaps/active/E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`, and fallback/SDK decisions use base/benchmark reports.

## Build Loop
- Before Unity/RN real-device builds, stop and report the build question, primary path, compare-only paths, validation contract, evidence matrix, and out-of-scope items; build only after user approval.
- Before builds, exhaust buildless checks first: static tests, Unity batchmode import/compile, existing recording/capture-pair frame analysis, and ARFace export projection/contact-sheet previews.
- Every approved Unity/RN validation session should regenerate and sync `UnityFramework.framework` with `bash scripts/build_m3_unityframework.sh` from the repo root.
- The script exports Unity iOS, verifies ARKit links, builds `UnityFramework` with signing disabled, copies Unity `Data`, and syncs RN/package framework paths.
- After sync, run from `rn/MakeupARValidation`: `npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK`.
- Before Unity builds, close Unity/Hub and ensure no Unity/Licensing processes remain; stale Licensing Client IPC can block export (`Unsupported protocol version '1.18.1'`).
- Keep the durable `RNUnityView.mm` timing patch hooks in RN `postinstall` and the iOS Podfile; stale package frameworks previously caused missing Unity objects/events.

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
- Store evidence under `evidence/logs/`, `evidence/screenshots/`, or `evidence/screen-recordings/`, but do not record video by default.
- Save recordings only when motion, elapsed time, or a continuous scenario is core evidence; keep metadata/contact sheets/representative frames, delete raw recordings when no longer needed, and prefer Homebrew `ffmpeg`/`ffprobe` for inspection.
- In user-facing Korean, avoid impressive-sounding internal jargon; when the user says the issue is important or asks to think deeply, inspect relevant context/code/evidence first, separate facts/inferences/hypotheses, and answer objectively rather than giving a simple agreement.
- When runtime console output is decision evidence, capture the full stream to `evidence/logs/` with `tee` or an equivalent method; summary-only logs must be labeled as summaries.
- Store feature snapshot examples as logs or runbook-linked text artifacts; do not store raw camera frames by default.
- Do not commit generated/cache state: `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode derived data, raw evidence, or `.DS_Store`; curated evidence follows `evidence/README.md`.
