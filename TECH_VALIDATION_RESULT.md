# Tech Validation Result

Date: 2026-06-21

Latest re-check: 2026-06-22 11:18 KST

Latest document cleanup: 2026-06-22 KST

Latest E7.03 contract reset: 2026-06-22 KST

Latest E7.03 Phase 1 UI/evidence hygiene implementation: 2026-06-22 KST

Latest E7.03 Phase 1 real-device build/log/capture-tooling check: 2026-06-22 14:25 KST

Latest E7.03 Phase 1 screenshot/LogBox cleanup: 2026-06-22 14:27 KST

Latest E7.03 phase-wide time-saving plan update: 2026-06-22 KST

## Current Session Snapshot

This snapshot is the default entry point for future Codex sessions. Read this section first, then lazy-load only the milestone-specific plan or research document needed for the current task.

Current boundary:

- Primary path: E7.03 v2.1 Boundary Engine Quality Experiment. Phase 0 Contract Reset is complete and Phase 1 Validation UI/Evidence Hygiene is implemented, JS-verified, real-device build/log smoke-verified, and user-provided iPhone screenshots confirm Clean / Compact HUD / Full Debug mode visibility. CLI screenshot capture remains tool-limited. A small RN LogBox suppression was added after screenshot review and JS-verified; reinstall was intentionally skipped by user decision. Next work stays in E7.3 with Phase 2 ARFace authored atlas MVP with manual vertex labeling, topology/UV audit, and a one-build / many-candidate loop so atlas variants can be swept from RN without UnityFramework regeneration for every candidate tweak.
- E7.03 v2.1 now has phase-wide time-saving rules, not only a P2 shortcut: prefer no-build data/registry/offline changes first, JS-only validation second, one real-device install for many candidate/variant/region sweeps third, and UnityFramework/Xcode rebuild only when renderer logic, schema, shader/material contract, package/framework sync, or native integration changes.
- E7.3 visual evidence has been reviewed from the user-provided screen recording. ARFace mesh/UV is live on-device, but the current procedural candidate is not visually acceptable for `lip` or `eye`; `cheek` lacks a clean E7 candidate sample. Overall E7.3 remains Yellow because the ARFace substrate is viable, but the current candidate masks block E7.4.
- The old E7.03 Green bar of "better than E3/E4 baseline" or "demo-plausible" is superseded. E7.03 Green now requires Q3 overlay-ready validation for `lip`, `cheek`, and `eye`, with runtime/visual evidence and region-separated scoring.
- Conservative alternative: run additional M7 re-entry verification if the team wants to replace the accepted M7 Yellow lifecycle risk with formal 3-cycle evidence.
- Renderer path: if the accepted M7 risk remains acceptable, stay in validation/hardening mode inside E7.3; do not enter E7.4/E7.5/E7.6 until E7.03 v2.1 evidence supports the next boundary, or until the team explicitly accepts the remaining E7.3 risk.

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
- E7.3 Region Precision: Yellow overall / blocked from E7.4. Region decisions from video review are `lip` Red, `cheek` Yellow / insufficient E7-candidate sample, and `eye` Red.
- Full E7 visual product-readiness: incomplete.

Active temporary docs:

- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`: active E7 master spike plan.
- `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`: active E7.03 / E7.3 v2.1 boundary engine quality plan. Phase 0 Contract Reset is complete; keep until v2.1 decisions are absorbed into this result doc or the team explicitly closes E7.3 as Yellow.
- `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`: keep for E7.6 performance decision; E7.2 baseline work is complete.
- Deferred docs to create only when needed: `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` before E7.4, and `E7_DEMO_LOOK_RECIPE_SPEC.md` only if recipe values or preset behavior need a fixed contract.

Default reading route:

- Always read `AGENTS.md` and this snapshot.
- Read `TECH_VALIDATION_TEST_PLAN.md` only when changing the stable validation contract or checking milestone/evidence rules.
- For E7.3 region precision, read `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` E7.3 sections and the `docs/roadmaps/research/E7_AXIS1_*` reports.
- For E7.03 boundary work, read `E7_REGION_PRECISION_SUBSPIKE_PLAN.md` first. It supersedes the old demo-plausible E7.3 Green bar with Q3 overlay-ready validation and the v2.1 experiment order.
- For E7.4/E7.5 cosmetic rendering and demo looks, read `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` E7.4/E7.5 sections and the `docs/roadmaps/research/E7_AXIS2_*` reports.
- For E7.6 performance, read `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`.
- Read base research or benchmark reports only for fallback, SDK comparison, licensing, or architecture decisions.

Stop rules:

- Do not mark M7 Green unless formal 3-cycle re-entry evidence is collected.
- Do not proceed to E7.4 or E7.6 from E7.2 logs or E7.3 build/install logs alone.
- Do not mark any E7.3 region Green without real-device runtime compare logs and representative visual evidence for that region.
- Do not mark E7.03 Green under the old "baseline-better" or "demo-plausible" standard. Green now requires Q3 overlay-ready validation for all three in-scope regions.
- Do not treat face parsing as E7.03 live runtime or product/release asset source, do not treat ML Kit Face Mesh as an iPhone runtime candidate, and do not introduce a separate camera session that conflicts with ARKit.
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

- E7.3 region precision implementation/build/video review: `evidence/logs/m3-repro-unity-export-e7-region-precision-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-region-precision-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-region-precision-2026-06-22.log`, `evidence/logs/e7-region-precision-rn-ios-run-default-candidate-2026-06-22.log`, `evidence/logs/e7-region-precision-summary-2026-06-22.md`, `evidence/logs/e7-region-precision-video-analysis-2026-06-22.md`, `evidence/screenshots/e7-region-precision-video-analysis-2026-06-22/contact-sheet-1fps.jpg`.
- E7.03 Phase 1 UI/evidence hygiene real-device check: `evidence/logs/m3-repro-unity-export-e7-phase1-ui-2026-06-22-141533.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-phase1-ui-2026-06-22-141533.log`, `evidence/logs/m3-repro-artifact-verification-e7-phase1-ui-2026-06-22-141533.log`, `evidence/logs/e7-phase1-ui-rn-ios-run-2026-06-22-141533.log`, `evidence/logs/e7-phase1-ui-runtime-console-2026-06-22-141533.log`, `evidence/logs/e7-phase1-ui-capture-tooling-2026-06-22-141533.log`, `evidence/logs/e7-phase1-ui-display-info-2026-06-22-141533.log`, `evidence/screenshots/e7-phase1-ui-display-info-2026-06-22-141533.json`, `evidence/screenshots/e7-phase1-ui-2026-06-22-141533/clean-view.jpg`, `evidence/screenshots/e7-phase1-ui-2026-06-22-141533/compact-hud.jpg`, `evidence/screenshots/e7-phase1-ui-2026-06-22-141533/full-debug.jpg`.
- E7.2 build/runtime: `evidence/logs/m3-repro-unity-export-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/e7-baseline-rn-ios-run-ack-2026-06-22.log`, `evidence/logs/e7-baseline-runtime-console-ack-2026-06-22.log`, `evidence/logs/e7-baseline-summary-2026-06-22.md`, `evidence/screenshots/e7-baseline-status-panel-2026-06-22.jpg`.
- E7.0/E7.1 preflight: `evidence/logs/e7-unity-process-cleanup-2026-06-22.log`, `evidence/logs/m3-repro-unity-export-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-preflight-2026-06-22.log`, `evidence/logs/e7-build-install-run-2026-06-22.log`, `evidence/logs/e7-runtime-event-preflight-2026-06-22.log`.
- E5 no-inference snapshot: `evidence/logs/e5-ai-feature-readiness-runtime-2026-06-21.log`, `evidence/screenshots/e5-ai-feature-readiness-rn-status-2026-06-21.jpg`.
- E4 texture samples: `evidence/logs/e4-texture-samples-runtime-2026-06-21.log`, `evidence/screen-recordings/e4-texture-samples-matte-shimmer-blush-2026-06-21.mp4`, `evidence/screenshots/e4-texture-samples-comparison-2026-06-21.jpg`.
- E3 region mask: `evidence/logs/e3-region-mask-layer-dispatch-2026-06-21.log`, `evidence/screen-recordings/e3-region-mask-lip-cheek-eye-2026-06-21.mp4`, `evidence/screenshots/e3-region-mask-debug-colors-2026-06-21.jpg`.
- M6 Unity -> RN events: `evidence/logs/m6-face-state-fix-runtime-2026-06-21.log`, `evidence/screen-recordings/m6-unity-to-rn-events-2026-06-21.mp4`, `evidence/screenshots/m6-rn-face-lost-latest-event-2026-06-21.jpg`, `evidence/screenshots/m6-rn-face-tracked-recipe-event-2026-06-21.jpg`.

## E7.3 Region Precision

Status: Yellow overall / blocked from E7.4. Implementation/build/install evidence is present and the screen recording confirms ARFace mesh/UV candidate mode runs on-device, but the current procedural candidate fails visual precision for `lip` and `eye`; `cheek` remains Yellow because the recording does not include a clean E7 candidate sample.

Decision:

- E7.03 Phase 0 Contract Reset is complete. `E7_REGION_PRECISION_SUBSPIKE_PLAN.md` v2.1 is the active E7.03 boundary engine plan.
- E7.03 v2.1 Phase 1 Validation UI/Evidence Hygiene is implemented in the RN validation UI, JS-verified, and smoke-verified through a fresh real-device build/install/launch/runtime-log pass.
- The previous "better than E3/E4 baseline" / "demo-plausible" Green standard is superseded by Q3 overlay-ready validation for `lip`, `cheek`, and `eye`.
- `TECH_VALIDATION_TEST_PLAN.md` was not changed for Phase 0 because no stable validation contract correction was required.
- Keep E3/E4 baseline renderer available as `e3e4-baseline`.
- Add the E7 validation candidate renderer as `e7-arface-uv-candidate`, default-selected for E7.3 validation.
- Keep ARFace mesh/UV as a viable runtime substrate, but reject the current procedural candidate mask output for `lip` and `eye` until the candidate basis is replaced or tuned.
- Continue RN + Unity + ARKit validation only. Do not claim product-readiness, product-quality makeup, M7 Green, E7.4/E7.5/E7.6 readiness, AI/backend/upload, MediaPipe live runtime, SDK, or Android scope from this result.

Confirmed implementation:

- Unity `E3RegionMaskOverlay` now supports baseline-vs-E7 candidate modes while preserving the E3/E4 centroid baseline path.
- E7 candidate mode uses ARFace mesh availability plus UV-aware candidate evidence fields and face-local mesh regions for `lip`, `cheek`, and `eye`.
- Unity emits E7 comparison/state fields for renderer mode, mask source, tracking state, state action, mesh/UV counts, baseline triangle count, candidate triangle count, and applied triangle count.
- Tracking, Limited, lost, and recovered states now map to explicit actions such as render, short hold, fade, extended hide, and recovered restore.
- RN sends `rendererMode`, exposes a Baseline/E7 UV segmented control, defaults E7.3 to `E7 UV`, and surfaces phase/mask/UV/triangle/state fields in the E7 status panel and event summaries.
- RN validation UI now supports `Clean`, `Compact HUD`, and `Full Debug` modes so large logs can be hidden during visual region review.
- `Compact HUD` shows candidate id, selected region, tracking/face count, mesh counts, FPS/frame-time, state action, and recipe latency without covering the full AR view.
- `Full Debug` exposes evidence metadata lines for plan/version, evidence mode, candidate id, region, tracking state, face count, mesh counts, blendshape field status, FPS/frame-time, latency, state action, privacy flags, orientation/device fields where available, and latest Unity event.
- Candidate catalog is visible in Full Debug for Phase 1 planning hygiene. Only existing dispatchable candidates (`e3e4-baseline` and current procedural `e7-arface-uv-candidate`) send recipe messages; ARFace atlas, vertex/blendshape, Apple Vision, MediaPipe, parsing, and hybrid candidates remain pending metadata only.
- RN validation app suppresses the React Native dev LogBox warning overlay so the bottom warning bar does not cover AR evidence or recipe controls. Console/runtime evidence logging remains available through captured device logs.

Evidence:

- Phase 1 JS verification: `./node_modules/.bin/tsc --noEmit` passed from `rn/MakeupARValidation`.
- Phase 1 lint verification: `npm run lint` passed from `rn/MakeupARValidation`.
- Phase 1 LogBox cleanup JS verification after screenshot review: `./node_modules/.bin/tsc --noEmit` and `npm run lint` passed from `rn/MakeupARValidation`.
- Phase 1 JS-only pass intentionally did not run `bash scripts/build_m3_unityframework.sh`, `xcodebuild`, `npm run ios`, or a real-device build.
- Phase 1 real-device follow-up regenerated UnityFramework with `bash scripts/build_m3_unityframework.sh`: `evidence/logs/m3-repro-xcodebuild-unityframework-e7-phase1-ui-2026-06-22-141533.log` records `** BUILD SUCCEEDED **`, and `evidence/logs/m3-repro-artifact-verification-e7-phase1-ui-2026-06-22-141533.log` records arm64 Mach-O RN/package frameworks, both `105M`, with `9.2M` Unity Data.
- Phase 1 RN iOS build/install/launch: `evidence/logs/e7-phase1-ui-rn-ios-run-2026-06-22-141533.log` records the Debug build using device id `00008140-000924DE21BB801C`, successful build, install, bundle id `com.makeupar.rnvalidation`, and successful launch on `위승철의 iPhone`.
- Phase 1 runtime console: `evidence/logs/e7-phase1-ui-runtime-console-2026-06-22-141533.log` has `93,186` lines captured through `devicectl --console`; the capture was manually stopped after sufficient evidence, so exit code `130` is capture termination, not an observed app crash.
- Runtime evidence includes UnityFramework load success, Unity root view attachment, M6 Unity -> RN events, E1/E2 tracked face lifecycle, E5 snapshots with `rawCameraFrameStored=false` and `offDeviceUpload=false`, and E7 metric samples.
- Runtime counts from the Phase 1 console stream: `[E7] metric_sample` `15`, `e7_metric_sample` RN events `15`, `[M6] unity_to_rn_send` `1189`, `face_feature_snapshot_created` `1193`, `SessionTracking` `3179`.
- Representative Phase 1 metric sample: tracking face count `1`, mesh `1220` vertices / `6912` indices / `1220` UVs, `hasStableUv=true`, average FPS samples observed at `57.1`, `60.0`, and `60.2` after cold start, memory metric available, thermal still manual-device-heat capped Yellow.
- Capture tooling check: `idevicescreenshot`, `ios-deploy`, `cfgutil`, `tidevice`, `pymobiledevice3`, and `idb` were not installed; `devicectl device` and `xcdevice` exposed no screenshot command. Display metadata was captured instead: active portrait LCD, `1179x2556`, point scale `3`.
- User-provided iPhone screenshots were saved under `evidence/screenshots/e7-phase1-ui-2026-06-22-141533/` and verify the Phase 1 modes at `590x1280`: `clean-view.jpg` shows Clean mode with the large debug panels hidden, `compact-hud.jpg` shows Compact HUD with candidate/region controls, and `full-debug.jpg` shows Full Debug evidence metadata, latest Unity event, face state, snapshot, and candidate catalog.
- The screenshot review exposed the React Native dev warning bar (`Open debugger to view warnings`) covering bottom controls. `LogBox.ignoreAllLogs(true)` was added in `rn/MakeupARValidation/App.tsx` to suppress that UI overlay in the validation app. Per user decision, the follow-up reinstall was stopped/skipped because this was a small JS-only cleanup.
- UnityFramework build/sync: `evidence/logs/m3-repro-xcodebuild-unityframework-e7-region-precision-2026-06-22.log` line `2264` records `** BUILD SUCCEEDED **`.
- Artifact verification: `evidence/logs/m3-repro-artifact-verification-e7-region-precision-2026-06-22.log` records arm64 Mach-O RN/package frameworks and copied Unity Data.
- Real-device RN build/install/launch after E7 default renderer change: `evidence/logs/e7-region-precision-rn-ios-run-default-candidate-2026-06-22.log` records successful build, install, and launch on `위승철의 iPhone`.
- Summary: `evidence/logs/e7-region-precision-summary-2026-06-22.md`.
- User-provided recording analysis: `evidence/logs/e7-region-precision-video-analysis-2026-06-22.md` records 28.46s / 59.45 FPS / 1180x2556 metadata and region verdicts.
- Contact sheet: `evidence/screenshots/e7-region-precision-video-analysis-2026-06-22/contact-sheet-1fps.jpg`.
- Representative visual evidence:
  - `eye`: `evidence/screenshots/e7-region-precision-video-analysis-2026-06-22/frame_001_01.35s.jpg` shows `E7 UV` + `eye` + `phase=region_precision`, but the mask is broad face/lower-face coverage instead of an eye zone.
  - `cheek`: `evidence/screenshots/e7-region-precision-video-analysis-2026-06-22/frame_015_15.35s.jpg` shows cheek selection, but the metric is `phase=baseline`, `mask=centroid_broad`, so this is not a clean E7 candidate sample.
  - `lip`: `evidence/screenshots/e7-region-precision-video-analysis-2026-06-22/frame_020_20.35s.jpg` and `frame_028_28.35s.jpg` show `E7 UV` + `lip` + `phase=region_precision`, but the mask spills across lower-face/cheek/chin-side skin.

Region G/Y/R:

- `lip`: Red. E7 candidate mode is live, but the selected `lip` candidate repeatedly paints surrounding lower-face skin in normal tracking frames.
- `cheek`: Yellow / insufficient E7-candidate sample. Cheek selection is present, but the visible metric is baseline or transition-stale, so no region Green/Red is justified yet.
- `eye`: Red. E7 candidate mode is live, but the selected `eye` candidate is not confined to an eyeshadow/eye region and covers broad non-eye areas.

Known limitations:

- The earlier E7.3 screen-recording review still lacks a full runtime console stream; the fresh Phase 1 follow-up has a runtime console stream, but no fresh visual screenshot/recording.
- No `[E7] region_precision_compare` runtime stream was captured during this pass.
- Cheek still needs a clean `phase=region_precision` sample before final region scoring.
- Lost, Limited, and recovered behavior were not exercised in this recording.
- On-screen FPS/frame-time values are visible, but this is not E7.6 performance evidence.
- The candidate is a validation candidate, not product-quality region segmentation or cosmetic rendering.
- E7.3 evidence does not resolve the accepted M7 Yellow lifecycle risk.
- Phase 1 UI modes are visually screenshot-verified from user-provided iPhone captures, but the post-LogBox-suppression UI was not reinstalled or re-screenshot by user decision. The local toolchain still has no automated iPhone screenshot CLI, and installed `devicectl`/`xcdevice` exposes no screenshot command.
- Future candidates shown in the candidate catalog are not runtime implementations; they are pending labels for later E7.03 phases.
- `Full Debug` can still cover part of the AR view by design; use `Clean` or `Compact HUD` for visual evidence capture.
- Phase 1 does not change region G/Y/R: `lip` remains Red, `cheek` remains Yellow / insufficient E7 candidate sample, and `eye` remains Red.
- Phase 1 runtime evidence is dominated by the default `lip` candidate path; it does not provide clean `cheek` or `eye` visual region evidence.

Next boundary:

- Stay inside E7.3 and execute E7.03 v2.1 Phase 2 ARFace authored atlas MVP with manual vertex labeling, topology/UV audit, and one-build / many-candidate atlas sweeping. On the next device install, confirm the React Native LogBox warning bar is gone before collecting new visual region evidence.
- Keep the current procedural ARFace mesh/UV candidate only as a rejected/negative baseline unless future evidence says otherwise.
- Re-record `lip`, `cheek`, and `eye` with `E7 UV`, full runtime console capture, representative visual evidence, and explicit tracking/Limited/lost/recovered notes.
- Do not enter E7.4/E7.5/E7.6 until `lip` and `eye` are no longer Red and `cheek` has a clean E7 candidate sample, or until the team explicitly accepts E7.3 as Yellow and records the risk.

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

E1 AR Alignment, E2 Trackable Lifecycle Diagnostics, E3 Region Mask, E4 Texture Sample, E5 AI Feature Readiness Snapshot, E6 Engine Decision, E7.0/E7.1 preflight, and E7.2 Baseline Instrumentation are complete. E7.3 Region Precision implementation/build/install is present, and video review confirms ARFace mesh/UV candidate mode on-device, but the current procedural candidate has `lip` Red, `eye` Red, and `cheek` Yellow / insufficient E7-candidate sample. E7.03 Phase 0 Contract Reset is complete, and Phase 1 Validation UI/Evidence Hygiene is implemented, JS-verified, real-device build/log smoke-verified, and visually confirmed with user-provided iPhone screenshots. CLI screenshot capture was blocked by local tooling limitations. A small RN LogBox suppression was added and JS-verified after screenshot review; follow-up reinstall was intentionally stopped/skipped by user decision. `E7_REGION_PRECISION_SUBSPIKE_PLAN.md` v2.1 is the active boundary engine quality plan, and the old "baseline-better" / "demo-plausible" Green bar is superseded by Q3 overlay-ready validation for `lip`, `cheek`, and `eye`. The plan now requires phase-wide experiment acceleration: one install/many variants, one recording set/many analyses, offline batch comparison before runtime POC, and rebuilds only for renderer/schema/native changes. Full E7 visual product-readiness is not complete. M0-M6 remain Green. M7 remains Yellow / skipped by decision / risk accepted.

Next boundary decision:

- Primary path: stay in E7.3 and execute E7.03 v2.1 Phase 2 ARFace authored atlas MVP with manual vertex labeling, topology/UV audit, and one-build / many-candidate atlas sweeping from RN. Across later phases, reuse the same candidate registry, shared recordings/contact sheets, cached offline comparisons, and full runtime log streams before starting new builds or new recordings.
- Conservative path: run additional M7 re-entry verification if the team wants to replace the accepted M7 Yellow risk with formal 3-cycle lifecycle evidence.
- Renderer path: do not enter E7.4/E7.5/E7.6 until E7.03 v2.1 evidence supports Q3 overlay-ready validation for the required regions, or until the team explicitly accepts the remaining E7.3 risk and records the boundary.
