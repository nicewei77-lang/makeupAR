# Tech Validation Result

Date: 2026-06-21

Latest re-check: 2026-06-22 04:32 KST

Latest document cleanup: 2026-06-22 KST

## Current Session Snapshot

This snapshot is the default entry point for future Codex sessions. Read this section first, then lazy-load only the milestone-specific plan or research document needed for the current task.

Current boundary:

- Primary path: E7.3 Region Precision sub-spike planning/validation.
- E7.3 has not started.
- Conservative alternative: run additional M7 re-entry verification if the team wants to replace the accepted M7 Yellow lifecycle risk with formal 3-cycle evidence.
- Renderer path: if the accepted M7 risk remains acceptable, stay in validation/hardening mode and create the required E7 sub-spike documents before E7.3, E7.4, and E7.6.

Current status:

- M0-M6: Green.
- M7: Yellow / skipped by decision / risk accepted. Do not promote M7 without formal 3-cycle re-entry evidence.
- M8 foundation closeout: Yellow overall because M7 remains risk-accepted.
- E1 AR Alignment: Green for validation.
- E2 Trackable Lifecycle Diagnostics: Green.
- E3 Region Mask: Green for validation only; masks are broad debug masks.
- E4 Texture Sample: Green for validation only; texture samples are procedural/debug quality.
- E5 AI Feature Readiness Snapshot: Green for no-inference handoff; decision recording was explicitly waived only for E5.
- E6 Engine Decision: Yellow; continue the RN + Unity + ARKit direction, but do not claim product-v1 readiness.
- E7.0/E7.1 Preflight: Green for preflight only.
- E7.2 Baseline Instrumentation: Green for baseline instrumentation; decision recording was explicitly waived only for E7.2.
- Full E7 visual product-readiness: incomplete.

Active temporary docs:

- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`: active E7 master spike plan.
- `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`: keep for E7.6 performance decision; E7.2 baseline work is complete.
- Deferred docs to create only when needed: `E7_REGION_PRECISION_SUBSPIKE_PLAN.md` before E7.3, `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` before E7.4, and `E7_DEMO_LOOK_RECIPE_SPEC.md` only if recipe values or preset behavior need a fixed contract.

Default reading route:

- Always read `AGENTS.md` and this snapshot.
- Read `TECH_VALIDATION_TEST_PLAN.md` only when changing the stable validation contract or checking milestone/evidence rules.
- For E7.3 region precision, read `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` E7.3 sections and the `docs/roadmaps/research/E7_AXIS1_*` reports.
- For E7.4/E7.5 cosmetic rendering and demo looks, read `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` E7.4/E7.5 sections and the `docs/roadmaps/research/E7_AXIS2_*` reports.
- For E7.6 performance, read `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`.
- Read base research or benchmark reports only for fallback, SDK comparison, licensing, or architecture decisions.

Stop rules:

- Do not mark M7 Green unless formal 3-cycle re-entry evidence is collected.
- Do not proceed to E7.4 or E7.6 from E7.2 logs alone.
- Do not claim full E7, visual product readiness, product-v1 readiness, or product-quality makeup from E7.0/E7.1 preflight or E7.2 instrumentation logs.
- Do not treat E3 as product-quality makeup accuracy; it proves validation-level region independence only.
- Do not treat E4 as product-quality makeup fidelity; it proves validation/debug texture sample dispatch and visual distinction only.
- Do not treat E5 or E7.2 recording waivers as general waivers for future milestones.
- Do not start AI model inference, backend upload, recommendation logic, commercial SDK integration, Android work, raw camera frame storage, or product implementation until a plan explicitly reaches that scope.

Evidence media policy:

- Do not save screen recordings by default.
- Save a recording only when motion, elapsed time, or a continuous scenario is the core evidence.
- When a recording is captured, prefer long-term retention of metadata, contact sheets, and representative frames. The raw recording may be deleted after decision review or extraction unless a milestone explicitly requires keeping it.

Key evidence:

- E7.2 build/runtime: `evidence/logs/m3-repro-unity-export-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/e7-baseline-rn-ios-run-ack-2026-06-22.log`, `evidence/logs/e7-baseline-runtime-console-ack-2026-06-22.log`, `evidence/logs/e7-baseline-summary-2026-06-22.md`, `evidence/screenshots/e7-baseline-status-panel-2026-06-22.jpg`.
- E7.0/E7.1 preflight: `evidence/logs/e7-unity-process-cleanup-2026-06-22.log`, `evidence/logs/m3-repro-unity-export-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-preflight-2026-06-22.log`, `evidence/logs/e7-build-install-run-2026-06-22.log`, `evidence/logs/e7-runtime-event-preflight-2026-06-22.log`.
- E5 no-inference snapshot: `evidence/logs/e5-ai-feature-readiness-runtime-2026-06-21.log`, `evidence/screenshots/e5-ai-feature-readiness-rn-status-2026-06-21.jpg`.
- E4 texture samples: `evidence/logs/e4-texture-samples-runtime-2026-06-21.log`, `evidence/screen-recordings/e4-texture-samples-matte-shimmer-blush-2026-06-21.mp4`, `evidence/screenshots/e4-texture-samples-comparison-2026-06-21.jpg`.
- E3 region mask: `evidence/logs/e3-region-mask-layer-dispatch-2026-06-21.log`, `evidence/screen-recordings/e3-region-mask-lip-cheek-eye-2026-06-21.mp4`, `evidence/screenshots/e3-region-mask-debug-colors-2026-06-21.jpg`.
- M6 Unity -> RN events: `evidence/logs/m6-face-state-fix-runtime-2026-06-21.log`, `evidence/screen-recordings/m6-unity-to-rn-events-2026-06-21.mp4`, `evidence/screenshots/m6-rn-face-lost-latest-event-2026-06-21.jpg`, `evidence/screenshots/m6-rn-face-tracked-recipe-event-2026-06-21.jpg`.

## E7.2 Baseline Instrumentation

Status: Green for E7.2 baseline instrumentation.

Confirmed implementation:

- Unity emits `[E7] metric_sample` with FPS, frame-time, worst frame-time, sustained-sub-20 flag, tracking state, mesh counts, active region/texture baseline state, memory availability/values, and thermal/manual-heat fields.
- Unity emits `[E7] metric_unavailable` for unavailable thermal native API evidence and keeps `thermalMetricYellowCap=true`.
- Unity recipe apply logging records RN `sentAtMs`, Unity `appliedAtMs`, and Unity `appliedFrame` while preserving the E3/E4 `ApplyRegionRecipe` path.
- RN sends a log-only ack after receiving `recipe_applied`, so Unity console evidence records RN `receivedAtMs`, `sendToAckLatencyMs`, `unityApplyLatencyMs`, and `unityToRnReceiveLatencyMs`.
- RN UI includes an E7 status panel with latest baseline metric and recipe latency fields.

Runtime summary:

- Runtime log line count: `65,428`.
- `[E7] metric_sample`: `9`.
- `[E7] metric_unavailable`: `1`.
- `[E7] recipe_latency source=unity_applied`: `14`.
- `[E7] recipe_latency source=rn_ack`: `14`.
- Tracking-state metric samples: `7`; average FPS mean/min/max `57.6 / 51.4 / 60.1`; average frame-time mean `17.4 ms`; allocated memory range `64.3-64.9 MB`; reserved memory max `82.2 MB`.
- RN ack latency samples: `14`; RN sent -> RN received mean/min/max `137.6 / 33.0 / 1473.0 ms`; Unity applied -> RN received mean/min/max `28.4 / 7.0 / 208.0 ms`.

Known limitations:

- First metric and latency samples include cold-start overhead and must not be used as final E7.6 performance evidence.
- Native thermal API integration is not configured; thermal is manual-device-heat evidence with a Yellow cap.
- E7.2 relies on a user-provided representative frame instead of a screen recording. This waiver is scoped only to E7.2.

## Workspace Document State

Active root documents:

- `AGENTS.md`: repository working rules, milestone scope boundaries, document policy, and evidence/cleanup requirements.
- `TECH_VALIDATION_TEST_PLAN.md`: stable validation contract. Do not update for progress/status unless correcting the contract.
- `TECH_VALIDATION_RESULT.md`: current snapshot, latest milestone decisions, and next boundary.

History archive:

- Full historical details, requirement matrices, special observations, environment/device snapshots, and the full evidence index were moved to `docs/roadmaps/archive/TECH_VALIDATION_HISTORY_2026-06-22.md`.
- Use the archive only when auditing old milestone evidence or reconstructing past decisions.

Document policy:

- New `M*_..._PLAN.md` or `E*_..._PLAN.md` files are temporary session plans.
- After a session completes, absorb the result into this file and delete temporary plans unless the user asks to keep them.
- Put reusable procedures in `docs/runbooks/`.
- Keep roadmap/research docs under `docs/roadmaps/`.

## Cleanup And Token Management

Local cleanup policy:

- Use `bash scripts/cleanup_local_generated.sh --profile balanced --dry-run` before applying cleanup.
- The balanced profile removes large reproducible generated artifacts while preserving `node_modules`, iOS `Pods`, Unity `Library`, logs, screenshots, and existing evidence directories. Future raw recordings should not be created or kept by default.
- After cleanup, the next real-device Unity/RN session must regenerate UnityFramework with `bash scripts/build_m3_unityframework.sh`.
- Detailed cleanup procedure lives in `docs/runbooks/LOCAL_WORKSPACE_CLEANUP_RUNBOOK.md`.

Token policy:

- Future sessions should start from `AGENTS.md` plus `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`.
- Do not load all research reports by default.
- Load only the research axis that matches the current E7 milestone.

## Next Milestone Boundary

E1 AR Alignment, E2 Trackable Lifecycle Diagnostics, E3 Region Mask, E4 Texture Sample, E5 AI Feature Readiness Snapshot, E6 Engine Decision, E7.0/E7.1 preflight, and E7.2 Baseline Instrumentation are complete. Full E7 visual product-readiness is not complete. M0-M6 remain Green. M7 remains Yellow / skipped by decision / risk accepted.

Next boundary decision:

- Primary path: E7.3 Region Precision sub-spike planning/validation.
- Conservative path: run additional M7 re-entry verification if the team wants to replace the accepted M7 Yellow risk with formal 3-cycle lifecycle evidence.
- Renderer path: if the team continues with accepted M7 risk, stay in validation/hardening mode and create the required E7 sub-spike documents before E7.3, E7.4, and E7.6 instead of jumping directly into product renderer claims.
