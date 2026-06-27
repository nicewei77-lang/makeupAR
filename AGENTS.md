# AGENTS.md

## Scope
- This repo is now for product-quality AR makeup engine iteration on a real iPhone using React Native + Unity + ARKit/AR Foundation; the feasibility foundation is proven, but evidence discipline still applies.
- Current scope comes from the newest user instruction, then `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`, then the single active roadmap doc, then archive docs. `AGENTS.md` must not hard-code the current task or lane.
- Stay inside the named product-quality slice or explicitly named roadmap/doc edit. If asked for 10 items, complete/verify all 10 or mark each unfinished item as blocked, skipped by user decision, or out of scope; never call a partial subset success.
- AI/backend/upload, commercial SDK, Android, or live per-frame AI parsing remain out of scope unless the user or active roadmap explicitly names them.

## Required Reading
- Start each session with `AGENTS.md` and `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`.
- Open `docs/roadmaps/README.md` as the menu, then open exactly one selected roadmap file; do not load whole `active/`, `archive/`, or `research/` folders.
- Read archive roadmap docs only when the user names them, the snapshot routes there, or an old boundary must be checked.
- After reading the contract, decide whether the user asked for planning or implementation; do not substitute a polished plan for requested code, UI, buildless proof, or device evidence.

## Fast Development Defaults
- Prefer the fastest relevant proof first: web/prototype UI, local server smoke, static checks, focused tests, Unity batchmode, existing device artifacts, and JSON/schema inspection before full rebuilds.
- For UX/state/generation flows, verify the flow in the web shell or functional beta first when available, then port the proven behavior to RN/Unity unless the user explicitly skips that step.
- Keep edits narrow and reversible. Avoid unrelated refactors, broad doc churn, and new dependencies unless they clearly remove blocker-level complexity.

## Product Quality Gates
- A product-quality slice is done only when `TECH_VALIDATION_RESULT.md` records the decision, concrete evidence, known limitations, and next boundary.
- Generation, local save, runtime apply, and visual acceptance are separate gates. A saved package or `saved_record` is not runtime proof; Unity/apply acknowledgment and visual evidence are required for applied claims.
- For runtime/user-visible changes, require real-device visual/runtime evidence where applicable: face attachment, boundary accuracy, motion/expression stability, makeup visibility, FPS/frame-time, latency, memory/thermal, and representative screenshots or frames.
- Do not treat buildless projection sanity, available signals such as Apple Vision/face parsing/color confidence, or same-frame round-trip output as product-quality proof by itself.
- For visual boundary or makeup judgment, generate visible candidates quickly, record inputs and missing signals, keep known weaknesses explicit, and require user/human review for subjective acceptance.
- Preserve local-only privacy: no upload and no product long-term raw camera-frame storage. Temporary diagnostic frame pulls are allowed only when needed for evidence, must stay local, and must be cleanup-scoped.

## Build Loop
- Before Unity/RN iPhone builds or device actions requiring the user, stop and report the build question, primary path, compare-only paths, quality gate, evidence matrix, and out-of-scope items; proceed only after user approval.
- When stopping for user approval, visual judgment, device unlock, camera permission, or any other user-only action, also attempt a local Slack alert with `python3 scripts/notify_slack_user_required.py --message "<short Korean request>"` if `SLACK_WEBHOOK_URL` is configured. Never print or commit the webhook URL, and do not proceed past the gated action until the user replies.
- Before builds, exhaust the relevant buildless checks first: web/prototype verification, static tests, Unity batchmode import/compile, existing artifact analysis, previews/contact sheets, and JSON/schema checks.
- Regenerate and sync `UnityFramework.framework` with `bash scripts/build_m3_unityframework.sh` when Unity code/assets/plugins changed or the export may be stale. For RN-only changes, record why skipping UnityFramework regeneration is safe.
- After sync, run from `rn/MakeupARValidation`: `npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK`.

## Document Rules
- Keep `docs/roadmaps/active/` to one current plan; move superseded roadmap docs to `docs/roadmaps/archive/`.
- After a session completes, absorb decisions into `TECH_VALIDATION_RESULT.md`; keep reusable procedures in `docs/runbooks/` and roadmap/research material under `docs/roadmaps/`.

## Evidence and Cleanup
- Store evidence under `evidence/logs/`, `evidence/screenshots/`, or `evidence/screen-recordings/`, but do not record video by default.
- Save recordings only when motion, elapsed time, or a continuous scenario is core evidence; keep metadata/contact sheets/representative frames, and delete raw recordings when no longer needed.
- In user-facing Korean, avoid impressive-sounding internal jargon; when the user says the issue is important or asks to think deeply, inspect relevant context/code/evidence first, separate facts/inferences/hypotheses, and answer objectively rather than giving a simple agreement.
- When runtime console output is decision evidence, keep the full stream or a clearly labeled summary; summary-only logs must be labeled as summaries.
- Do not commit generated/cache state: `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode derived data, raw evidence, `.cache/`, or `.DS_Store`; curated evidence follows `evidence/README.md`.
