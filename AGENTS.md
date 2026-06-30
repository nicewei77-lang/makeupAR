# AGENTS.md

## Scope
- This repo is a React Native + Unity + AR Foundation AR makeup product for real iPhone testing.
- Follow the user's current task or explicitly named roadmap/review scope; validation docs are historical decision/evidence records, not active gates.
- AR product implementation and makeup rendering are allowed.
- Get user approval before non-AR product work such as AI/backend/admin/payment/community or Android.
- Do not use paid SDKs, paid APIs, trial-only SDKs, or dependencies that prohibit commercial product use.
- Free-to-use dependencies with attribution, notice, or license-text requirements are allowed only when they permit commercial product use and those obligations can be satisfied.
- AI/model inference, recommendations, backend uploads, or raw-frame storage require explicit approval and privacy review.

## Dependencies
- A dependency means an external package/SDK/API such as an npm package, CocoaPod, Unity package, native framework, or vendor service.
- Prefer the current stack, repo scripts, and existing helper code for simple work, but do not make awkward workarounds to avoid a well-justified dependency.
- If a new or updated dependency would materially improve quality, speed, maintainability, or reliability, ask the user before adding it.
- When asking, explain what it solves, why existing code is not enough, whether it is free for commercial product use, and any attribution/notice obligations.
- Add or update dependencies only after user approval.
- Avoid paid accounts, trials, telemetry-heavy SDKs, or vendor lock-in.
- Restoring existing dependencies from committed manifests/lockfiles is allowed.

## Required Reading
- Start each session with this file.
- Consult `TECH_VALIDATION_RESULT.md` only for prior validation, build/device status, or known-risk context.
- Read `TECH_VALIDATION_TEST_PLAN.md` only when changing or auditing the old validation contract.
- For validation/research tasks, lazy-load only the relevant roadmap or research file.

## Build Loop
- Before Unity/RN real-device builds, stop and report the build question, primary path, target device/signing assumptions, expected risk, and out-of-scope items; build only after user approval.
- Before approved builds, run useful practical checks first: static tests, Unity batchmode import/compile, local previews, or asset checks.
- For approved Unity/RN device builds, regenerate and sync `UnityFramework.framework` with `bash scripts/build_m3_unityframework.sh` from the repo root before RN/Xcode.
- Use the user-approved target device and signing team for each build; do not hard-code a specific UDID or `DEVELOPMENT_TEAM` as the repo default.
- Before Unity builds, close Unity/Hub and stale Unity/Licensing processes.

## Docs and Records
- Keep root docs minimal; put product docs under `docs/product/`, architecture under `docs/architecture/`, runbooks under `docs/runbooks/`, and roadmap/research under `docs/roadmaps/`.
- Put durable product decisions in the appropriate product, architecture, roadmap, or runbook doc.
- Record important decisions, builds, known limitations, user acceptance, and release/QA checks concisely.
- Store supporting artifacts under `evidence/logs/`, `evidence/screenshots/`, or `evidence/screen-recordings/`; do not store raw camera frames or video by default.
- Do not commit generated/cache state: `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode derived data, raw evidence, or `.DS_Store`.

## Product Claims
- Keep `lip`, `cheek`, `eye`, camera modes, photo/video, and realtime AR decisions separate when useful for planning or QA.
- Do not claim App Store, commercial, privacy, license, or production readiness without matching review/check evidence.
