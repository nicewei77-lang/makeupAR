# AGENTS.md

## Scope
- This repo is now for product-quality AR makeup engine iteration on a real iPhone using React Native + Unity + ARKit/AR Foundation; the feasibility foundation is proven, but evidence discipline still applies.
- Current scope comes from `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot` plus the single active roadmap doc. If sources conflict, follow the newest user instruction, then the result snapshot, then the active roadmap, then archive docs.
- Stay inside the named product-quality slice or explicitly named roadmap/doc edit. If asked for 10 items, complete/verify all 10 or mark each unfinished item as blocked, skipped by user decision, or out of scope; never call a partial subset success.
- Current default lane is lip candidate/boundary quality. Product-quality cosmetic rendering is allowed only inside the active or explicitly named plan; AI/backend/commercial SDK/Android remain out of scope unless explicitly named.

## Required Reading
- Start each session with `AGENTS.md` and `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`.
- Open `docs/roadmaps/README.md` as the menu, then open exactly one selected roadmap file; do not load whole `active/`, `archive/`, or `research/` folders.
- For the current lane, read `docs/roadmaps/active/E7_LIP_CANDIDATE_GENERATOR_FAST_SPIKE_PLAN_KO.md`.
- Read archive roadmap docs only when the user names them, the snapshot routes there, or an old boundary must be checked.

## Product Quality Gates
- A product-quality slice is done only when `TECH_VALIDATION_RESULT.md` records the decision, concrete evidence, known limitations, and next boundary.
- For runtime/user-visible changes, require real-device visual/runtime evidence where applicable: face attachment, boundary accuracy, motion/expression stability, makeup visibility, FPS/frame-time, latency, memory/thermal, and representative screenshots or frames.
- Do not treat buildless projection sanity, available signals such as Apple Vision/face parsing/color confidence, or same-frame round-trip output as product-quality proof by itself.
- For lip candidate work, move fast: generate visible candidates, record every input signal and missing signal, keep known weaknesses explicit, and require user/human review for subjective boundary acceptance.
- Preserve local-only privacy: no upload, no long-term raw camera-frame storage, and no live face parsing/Core ML runtime unless a plan explicitly authorizes it.

## Build Loop
- Before Unity/RN iPhone builds or new device capture, stop and report the build question, primary path, compare-only paths, quality gate, evidence matrix, and out-of-scope items; build only after user approval.
- Before builds, exhaust buildless checks first: static tests, Unity batchmode import/compile, existing capture-pair analysis, ARFace projection previews, contact sheets, and JSON/schema checks.
- Every approved Unity/RN device pass should regenerate and sync `UnityFramework.framework` with `bash scripts/build_m3_unityframework.sh` from the repo root.
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
