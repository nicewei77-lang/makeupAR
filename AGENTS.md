# AGENTS.md

## Scope
- This repo has moved from pre-product AR technical validation into post-validation product/research/prototype work.
- The user's named task is the active boundary. If the task is unclear, use `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot` / `Next Work Boundary`.
- Validation docs and evidence are historical grounding; unresolved Yellow items do not block unrelated product, research, crawler, docs, or prototype tasks.
- Commercial completion and product readiness are valid work targets; implementation, AI/backend/admin/payment/community, SDK, Android, and product-quality makeup work may start when requested, with readiness gated by `docs/product/COMMERCIAL_READINESS_REGULATORY_GUARDRAILS_KO.md`.
- Do not claim product-v1 readiness, product-quality makeup, or AR engine Green status from old validation evidence.
- Raw camera frames, biometric-like face data, uploads, and model inference require an explicit privacy-safe plan.

## Required Reading
- Start each session with `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`; read `TECH_VALIDATION_TEST_PLAN.md` only when changing the validation contract or checking milestone/evidence rules.
- For commercial/product work, read `docs/product/COMMERCIAL_READINESS_REGULATORY_GUARDRAILS_KO.md` plus the target docs/code; do not reopen E7 research by default.
- For Twinit/competitor research, start with `twinit-crawler/README.md` and generated CSV/JSONL only as needed.
- For AR validation continuation, read the matching roadmap section only: E7.3 `E7_AXIS1_*`, E7.4/E7.5 `E7_AXIS2_*`, E7.6 performance subspike.

## Build Loop
- Ordinary docs/crawler/product/frontend tasks do not need the Unity/RN validation build loop.
- Before Unity/RN real-device builds, stop and report the build question, target path, evidence needed, and out-of-scope items; build only after user approval.
- Before builds, exhaust buildless checks first: static tests, Unity batchmode import/compile, existing recording/capture-pair frame analysis, and ARFace export projection/contact-sheet previews.
- Every approved Unity/RN device session should regenerate and sync `UnityFramework.framework` with `bash scripts/build_m3_unityframework.sh` from the repo root.
- The script exports Unity iOS, verifies ARKit links, builds `UnityFramework` with signing disabled, copies Unity `Data`, and syncs RN/package framework paths.
- After sync, run from `rn/MakeupARValidation` with the current connected iPhone/team values recorded in the result snapshot or supplied by the user.
- Before Unity builds, close Unity/Hub and ensure no Unity/Licensing processes remain; stale Licensing Client IPC can block export (`Unsupported protocol version '1.18.1'`).
- Keep the package-local `RNUnityView.mm` timing patch caveat in mind until it is made durable; stale package frameworks previously caused missing Unity objects/events.

## Document Rules
- Keep this file at 50 lines or fewer.
- Keep root active docs limited to `AGENTS.md`, `TECH_VALIDATION_TEST_PLAN.md`, and `TECH_VALIDATION_RESULT.md`.
- Do not update `TECH_VALIDATION_TEST_PLAN.md` for progress/status unless correcting the validation contract itself.
- Create new plan docs only when they will guide real work; validation `M*_..._PLAN.md` / `E*_..._PLAN.md` files remain temporary unless promoted.
- After a session completes, absorb the result into `TECH_VALIDATION_RESULT.md` and delete the temporary plan.
- Put reusable procedures in `docs/runbooks/`; keep roadmap/research docs under `docs/roadmaps/`.

## Milestone Boundaries
- Completed validation foundation: M0-M6 Green; M7 Yellow/risk accepted; M8 Yellow because of M7.
- E1-E5 are validation Green, E6 is Yellow, and E7.3 remains Yellow for visual product-readiness unless new evidence changes it.
- If resuming AR engine work, keep `lip`/`cheek`/`eye` evidence separate and record whether later work accepts the E7.3 Yellow cap.
- AI readiness from the validation phase means no-inference feature snapshot handoff only; future AI product work needs a new explicit plan.

## Evidence and Cleanup
- Before marking AR/device/product-readiness or commercial-ready complete, cite evidence and satisfy the commercial regulatory gate where relevant.
- For resumed validation milestones, `TECH_VALIDATION_RESULT.md` must record the decision, evidence, known limitations, and next boundary.
- Store evidence under `evidence/logs/`, `evidence/screenshots/`, or `evidence/screen-recordings/`, but do not record video by default.
- Save recordings only when motion, elapsed time, or a continuous scenario is core evidence; then keep metadata/contact sheets/representative frames and delete the raw recording when no longer needed.
- For local video inspection, prefer Homebrew `/opt/homebrew/bin/ffmpeg` and `/opt/homebrew/bin/ffprobe` when available.
- When runtime console output is decision evidence, capture the full stream to `evidence/logs/` with `tee` or an equivalent method; summary-only logs must be labeled as summaries.
- Store feature snapshot examples as logs or runbook-linked text artifacts; do not store raw camera frames by default.
- Do not commit generated/cache state: `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode derived data, raw evidence, or `.DS_Store`; curated evidence follows `evidence/README.md`.
