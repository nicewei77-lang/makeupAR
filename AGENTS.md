# AGENTS.md

## Scope
- This repo is for React Native + Unity + AR Foundation based AR makeup product development on a real iPhone; prior validation docs remain decision history.
- Follow the user's current product task or explicitly named roadmap/review scope; validation milestones are historical context, not implementation gates.
- Do not derive active scope from `TECH_VALIDATION_RESULT.md` unless the user asks for validation status/audit; use it as technical history and known-risk context.
- Use `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` only when the user asks about AR engine validation planning or prior validation decisions.
- AR product implementation and product-quality makeup rendering are allowed; get user approval before implementing non-AR product areas such as AI/backend/admin/payment/community, commercial SDK integration, or Android work.
- AI/model inference, recommendation, backend upload, or raw-frame storage require explicit user approval and privacy review before implementation.

## Required Reading
- Start each session with `AGENTS.md`; consult `TECH_VALIDATION_RESULT.md` only when prior validation state, build/device status, or known limitations matter.
- Treat validation snapshots as historical decision/evidence records, not active stop rules, milestone gates, or next boundaries unless the user explicitly asks for validation work.
- Read `TECH_VALIDATION_TEST_PLAN.md` only when changing or auditing the old validation contract.
- For validation/research tasks, lazy-load only the relevant roadmap or research file instead of whole folders.

## Build Loop
- Before Unity/RN real-device builds, stop and report the build question, primary path, target device/signing assumptions, expected risk, and out-of-scope items; build only after user approval.
- Before builds, run relevant practical checks first: static tests, Unity batchmode import/compile, local previews, or asset checks when useful.
- Every approved Unity/RN device build should regenerate and sync `UnityFramework.framework` with `bash scripts/build_m3_unityframework.sh` from the repo root.
- The script exports Unity iOS, verifies ARKit links, builds `UnityFramework` with signing disabled, copies Unity `Data`, and syncs RN/package framework paths.
- After sync, run RN/Xcode with the user-approved target device and signing team for the current build; do not hard-code a specific UDID or `DEVELOPMENT_TEAM` as the repo default.
- Before Unity builds, close Unity/Hub and ensure no Unity/Licensing processes remain; stale Licensing Client IPC can block export (`Unsupported protocol version '1.18.1'`).
- Keep the package-local `RNUnityView.mm` timing patch caveat in mind until it is made durable; stale package frameworks previously caused missing Unity objects/events.

## Document Rules
- Keep this file at 50 lines or fewer.
- Keep root docs minimal; put product docs under `docs/product/`, architecture under `docs/architecture/`, runbooks under `docs/runbooks/`, and roadmap/research under `docs/roadmaps/`.
- Keep `TECH_VALIDATION_TEST_PLAN.md` stable unless correcting the old validation contract.
- Treat `TECH_VALIDATION_RESULT.md` as validation history; do not force product progress into it unless the user asks or the work directly updates validation history.
- Put durable product decisions in product/architecture/roadmap docs, not temporary milestone notes.

## Product Boundaries
- Historical M/E validation milestones are not gates for product work.
- Product work can proceed from the user's chosen scope; record known risks and mitigations instead of blocking on Green/Yellow validation status.
- Keep `lip`, `cheek`, `eye`, camera modes, photo/video, and realtime AR decisions separate when that helps product planning or QA.
- Do not claim App Store, commercial, privacy, license, or production readiness without matching review/check evidence.

## Records and Cleanup
- Keep concise records of important decisions, builds, known limitations, user acceptance, and release/QA checks in the appropriate docs or evidence folders.
- Store supporting artifacts under `evidence/logs/`, `evidence/screenshots/`, or `evidence/screen-recordings/`, but do not record video by default.
- Save recordings only when motion, elapsed time, or a continuous scenario is core evidence; then keep metadata/contact sheets/representative frames and delete the raw recording when no longer needed.
- For local video inspection, prefer Homebrew `/opt/homebrew/bin/ffmpeg` and `/opt/homebrew/bin/ffprobe` when available.
- When runtime console output is decision evidence, capture the full stream to `evidence/logs/` with `tee` or an equivalent method; summary-only logs must be labeled as summaries.
- Store feature snapshot examples as logs or runbook-linked text artifacts; do not store raw camera frames by default.
- Do not commit generated/cache state: `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode derived data, raw evidence, or `.DS_Store`; curated evidence follows `evidence/README.md`.
