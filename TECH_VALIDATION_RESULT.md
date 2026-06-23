# Tech Validation Result

Date: 2026-06-21

Latest re-check: 2026-06-22 11:18 KST

Latest document cleanup: 2026-06-22 KST

Latest E7.03 contract reset: 2026-06-22 KST

Latest E7.03 Phase 1 UI/evidence hygiene implementation: 2026-06-22 KST

Latest E7.03 Phase 1 real-device build/log/capture-tooling check: 2026-06-22 14:25 KST

Latest E7.03 Phase 1 screenshot/LogBox cleanup: 2026-06-22 14:27 KST

Latest E7.03 phase-wide time-saving plan update: 2026-06-22 KST

Latest E7.03 Phase 2 ARFace authored atlas MVP implementation/build/install check: 2026-06-22 15:24 KST

Latest E7 reference-driven UV atlas pre-gold setup: 2026-06-22 KST

Latest E7.03 P2 synchronized reference capture: 2026-06-22 23:34 KST

Latest E7.03 A/B UV atlas fast gate: 2026-06-23 KST

Latest E7.03 P8 runtime sweep implementation prep: 2026-06-23 KST

Latest E7.03 P8 runtime sweep build/log/visual review: 2026-06-23 KST

Latest E7.03 smooth-mask validation app cleanup/user acceptance: 2026-06-23 KST

Latest workspace share cleanup/document structure pass: 2026-06-23 KST

## Current Session Snapshot

This snapshot is the default entry point for future Codex sessions. Read this section first, then lazy-load only the milestone-specific plan or research document needed for the current task.

Current boundary:

- Primary path: E7.03 v2.1 Boundary Engine Quality Experiment. Phase 0 Contract Reset is complete. Phase 1 Validation UI/Evidence Hygiene is implemented, JS-verified, real-device build/log smoke-verified, and user-provided iPhone screenshots confirm Clean / Compact HUD / Full Debug mode visibility. Phase 2 ARFace authored atlas MVP is implemented with manual vertex labels, topology/UV audit metadata, RN-selectable atlas variants, and preserved E3/E4/procedural baselines. Phase 2 is JS/lint verified, UnityFramework build/sync verified, and RN real-device build/install verified; runtime launch/visual evidence is still pending because the iPhone was locked during launch.
- Reference-driven UV atlas P2 synchronized capture is complete for input collection only. The validation app now exports clean frames plus same-moment ARFace mesh/UV/screen projection data, suppresses Unity face renderers/candidate masks/debug panels during capture, uses unique timestamped `pair_face_*` capture IDs for repeated attempts, and places the capture button away from the front camera. Three copied P2 capture folders are available under `evidence/e7-reference-atlas/capture_pairs/`; `pair_face_20260622T143334Z_03` is the recommended clean reference frame for user gold-mask drawing. No gold mask, UV back-projection, round-trip render, P3/P4 acceptance, MediaPipe runtime, or E7.4 work has started.
- A no-build A/B UV atlas fast gate was run from the two user-authored mask sets on `pair_face_20260622T143300Z_01` and `pair_face_20260622T143334Z_03`. After fixing the fast-gate back-projection sampling density, `lip`, `cheek`, and `eye` all produce continuation signals, so the offline decision is `continue`. This justifies preparing a small P8 runtime sweep candidate set, but it does not mark E7.03 Green.
- P8 runtime sweep build/log/visual evidence is collected for the default reference UV runtime path. The frozen runtime candidate set lives under `unity/MakeupARUnityValidation/Assets/Resources/E7ReferenceAtlas/e7ref-fastgate-20260622T160307Z-v0/` with exactly 9 reference UV variants (`core`, `balanced`, `soft-wide` for `lip`, `cheek`, and `eye`), and RN/Unity support `rendererMode="e7-reference-uv-atlas"` / `candidateId="arface-reference-uv-atlas"`. The latest iPhone runtime stream confirms `lip`, `cheek`, and `eye` all sample ARFace UV probability atlases with `tracking_render`, mesh/UV counts `1220/6912/1220`, and `usedFallback=false`. User-provided Compact HUD photos confirm the masks appear face-attached, but all three regions remain Yellow because the silhouettes are still jagged/rough and the full white debug face surface is not Q3 overlay-ready makeup rendering.
- E7.03 smooth-mask validation app cleanup is accepted for the current optimization goal. Candidate/variant selection UI, old capture/reference controls, and stale visual debug paths were removed from the active app surface. The current runtime defaults to one `smooth-region-mask` path with three batched layers (`lip`, `cheek`, `eye`) and per-layer `enabled` flags. HUD status is inside the bottom `Regions` panel instead of floating over the face. User-provided acceptance screenshots are stored at `evidence/screenshots/e7-smooth-mask-accepted-2026-06-23/` and show visible, natural, subtle makeup on the face with Compact HUD reporting `active=lip,cheek,eye`, mesh `v=1220/i=6912/uv=1220`, FPS `52.2-60.2`, and recipe latency `36.0ms`. User visual feedback: the overall makeup is still hard to see, the eye boundary is somewhat lacking, and this validation stage ideally should make the covered region more unmistakable; however, the current result is accepted and the remaining visibility/boundary issue should be handled together with the next cosmetic expression/modeling work. This closes the current app cleanup/optimization goal by user acceptance, but it does not mark E7.03 Green or prove product-quality cosmetic rendering.
- Phase 2 adds the runtime-selectable `e7-arface-authored-atlas` candidate for `lip`, `cheek`, and `eye`. This is validation-only manual labeling plus evidence metadata, not face parsing, product segmentation, product-quality makeup, or AI/backend work.
- E7.03 v2.1 now has phase-wide time-saving rules, not only a P2 shortcut: prefer no-build data/registry/offline changes first, JS-only validation second, one real-device install for many candidate/variant/region sweeps third, and UnityFramework/Xcode rebuild only when renderer logic, schema, shader/material contract, package/framework sync, or native integration changes.
- E7.3 visual evidence has been reviewed from the user-provided screen recording. ARFace mesh/UV is live on-device, but the current procedural candidate is not visually acceptable for `lip` or `eye`; `cheek` lacks a clean E7 candidate sample. Overall E7.3 remains Yellow because the ARFace substrate is viable, but the current candidate masks block E7.4.
- The old E7.03 Green bar of "better than E3/E4 baseline" or "demo-plausible" is superseded. E7.03 Green now requires Q3 overlay-ready validation for `lip`, `cheek`, and `eye`, with runtime/visual evidence and region-separated scoring.
- Conservative alternative: run additional M7 re-entry verification if the team wants to replace the accepted M7 Yellow lifecycle risk with formal 3-cycle evidence.
- Renderer path: if the accepted M7 risk remains acceptable, stay in validation/hardening mode inside E7.3; do not enter E7.4/E7.5/E7.6 until E7.03 v2.1 evidence supports the next boundary, or until the team explicitly accepts the remaining E7.3 risk.
- Workspace/share state: source-first cleanup is complete for the current handoff pass. Current checked size is `24M` total (`.git` about `22M`; source/doc/script working tree about `2M`). Root active docs are limited to `AGENTS.md`, `TECH_VALIDATION_TEST_PLAN.md`, and `TECH_VALIDATION_RESULT.md`; active E7 plans now live under `docs/roadmaps/active/`; team onboarding/share requirements live in `docs/runbooks/TEAM_SHARE_REQUIREMENTS_KO.md`; ignored evidence/build/dependency/editor outputs are expected to be absent after `scripts/cleanup_local_generated.sh --profile share`.

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
- E7.3 Region Precision: Yellow overall / blocked from E7.4. Legacy procedural E7 video review remains `lip` Red, `cheek` Yellow / insufficient E7-candidate sample, and `eye` Red. P8 reference UV runtime sweep improves attachment for all three regions, but current P8 region decisions are `lip` Yellow, `cheek` Yellow, and `eye` Yellow pending silhouette/material cleanup and scenario-specific motion review.
- E7.03 P2 synchronized reference capture: captured / ready for user gold-mask authoring input; this does not change E7.3 region G/Y/R or mark E7.03 Green.
- E7.03 A/B UV atlas fast gate: Continue / P8 Build Gate already consumed for the first runtime sweep. `lip`, `cheek`, and `eye` all showed useful same-frame and cross-frame UV transfer; this remains offline viability evidence, not runtime Green evidence.
- E7.03 P8 runtime sweep: build/install/runtime-log/representative-photo evidence collected after Build Gate approval. The runtime path is viable, Compact HUD is visible, and Clean intentionally hides the mask, but no region is Green yet.
- E7.03 smooth-mask validation app cleanup: accepted for the current validation app optimization goal. The accepted screenshots show a usable, non-obstructed Compact HUD and a natural-enough visible overlay for this validation step. User feedback records that the overall makeup is still subtle/hard to see and the eye boundary needs improvement, but this is acceptable for now and should be resolved with cosmetic expression/modeling. Full E7.3 Region Precision remains Yellow because Q3 overlay-ready motion/scenario evidence is still incomplete.
- Full E7 visual product-readiness: incomplete.

Active temporary docs:

- `docs/roadmaps/active/E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`: active E7 master spike plan.
- `docs/roadmaps/active/E7_REGION_PRECISION_SUBSPIKE_PLAN.md`: active E7.03 / E7.3 v2.1 boundary engine quality plan. Phase 0 Contract Reset is complete; keep until v2.1 decisions are absorbed into this result doc or the team explicitly closes E7.3 as Yellow.
- `docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md`: active reference-driven UV atlas implementation plan for the next E7.03 region precision hardening slice; use for pre-gold capture-pair work and later one-frame round-trip gating.
- `docs/roadmaps/active/E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`: keep for E7.6 performance decision; E7.2 baseline work is complete.
- Deferred docs to create only when needed: `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` before E7.4, and `E7_DEMO_LOOK_RECIPE_SPEC.md` only if recipe values or preset behavior need a fixed contract.

Default reading route:

- Always read `AGENTS.md` and this snapshot.
- Read `TECH_VALIDATION_TEST_PLAN.md` only when changing the stable validation contract or checking milestone/evidence rules.
- For E7.3 region precision, read `docs/roadmaps/active/E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` E7.3 sections and the `docs/roadmaps/research/E7_AXIS1_*` reports.
- For E7.03 boundary work, read `docs/roadmaps/active/E7_REGION_PRECISION_SUBSPIKE_PLAN.md` first. It supersedes the old demo-plausible E7.3 Green bar with Q3 overlay-ready validation and the v2.1 experiment order.
- For reference-driven UV atlas work before gold mask authoring, read `docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md` and keep the official pair status pending until a clean frame and synchronized ARFace export are captured from the same runtime moment.
- For E7.4/E7.5 cosmetic rendering and demo looks, read `docs/roadmaps/active/E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` E7.4/E7.5 sections and the `docs/roadmaps/research/E7_AXIS2_*` reports.
- For E7.6 performance, read `docs/roadmaps/active/E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`.
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
- E7.03 Phase 2 ARFace authored atlas MVP build/install check: `evidence/logs/m3-repro-unity-export-e7-phase2-atlas-2026-06-22-151537.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-phase2-atlas-2026-06-22-151537.log`, `evidence/logs/m3-repro-artifact-verification-e7-phase2-atlas-2026-06-22-151537.log`, `evidence/logs/e7-phase2-atlas-2026-06-22-151537-rn-ios-device.log`.
- E7.03 P2 synchronized reference capture: `evidence/logs/m3-repro-unity-export-2026-06-22-230402.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-22-230402.log`, `evidence/logs/m3-repro-artifact-verification-2026-06-22-230402.log`, `evidence/logs/e7-reference-capture-rn-ios-run-2026-06-22-233049.log`, `evidence/logs/e7-reference-capture-runtime-console-2026-06-22-233202.log`, `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143300Z_01/`, `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143305Z_02/`, `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/`.
- E7.03 A/B UV atlas fast gate: `evidence/e7-reference-atlas/fast-gate-20260622T160307Z/summary.md`, `evidence/e7-reference-atlas/fast-gate-20260622T160307Z/summary.json`, plus per-region `round_trip/`, `cross_frame/`, `uv_overlap/`, `candidate_preview/`, and `atlases/` artifacts. Earlier fast-gate runs are superseded because they used sparse sampling or were debug/smoke runs.
- E7.03 P8 runtime sweep implementation prep: frozen Unity Resources under `unity/MakeupARUnityValidation/Assets/Resources/E7ReferenceAtlas/e7ref-fastgate-20260622T160307Z-v0/` include 9 probability PNGs, 9 PNG-byte Resources, and `runtime_candidates.json`. Static checks passed: `/Users/wiseungcheol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile scripts/e7_reference_atlas/fast_uv_atlas_gate.py`, `./node_modules/.bin/tsc --noEmit`, `npm run lint`, and `git diff --check`. This is implementation/static evidence only, not real-device runtime evidence.
- E7.2 build/runtime: `evidence/logs/m3-repro-unity-export-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/e7-baseline-rn-ios-run-ack-2026-06-22.log`, `evidence/logs/e7-baseline-runtime-console-ack-2026-06-22.log`, `evidence/logs/e7-baseline-summary-2026-06-22.md`, `evidence/screenshots/e7-baseline-status-panel-2026-06-22.jpg`.
- E7.0/E7.1 preflight: `evidence/logs/e7-unity-process-cleanup-2026-06-22.log`, `evidence/logs/m3-repro-unity-export-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-preflight-2026-06-22.log`, `evidence/logs/e7-build-install-run-2026-06-22.log`, `evidence/logs/e7-runtime-event-preflight-2026-06-22.log`.
- E5 no-inference snapshot: `evidence/logs/e5-ai-feature-readiness-runtime-2026-06-21.log`, `evidence/screenshots/e5-ai-feature-readiness-rn-status-2026-06-21.jpg`.
- E4 texture samples: `evidence/logs/e4-texture-samples-runtime-2026-06-21.log`, `evidence/screen-recordings/e4-texture-samples-matte-shimmer-blush-2026-06-21.mp4`, `evidence/screenshots/e4-texture-samples-comparison-2026-06-21.jpg`.
- E3 region mask: `evidence/logs/e3-region-mask-layer-dispatch-2026-06-21.log`, `evidence/screen-recordings/e3-region-mask-lip-cheek-eye-2026-06-21.mp4`, `evidence/screenshots/e3-region-mask-debug-colors-2026-06-21.jpg`.
- M6 Unity -> RN events: `evidence/logs/m6-face-state-fix-runtime-2026-06-21.log`, `evidence/screen-recordings/m6-unity-to-rn-events-2026-06-21.mp4`, `evidence/screenshots/m6-rn-face-lost-latest-event-2026-06-21.jpg`, `evidence/screenshots/m6-rn-face-tracked-recipe-event-2026-06-21.jpg`.

## E7.3 Region Precision

Status: Yellow overall / blocked from E7.4. Implementation/build/install evidence is present and the screen recording confirms ARFace mesh/UV candidate mode runs on-device, but the legacy procedural candidate fails visual precision for `lip` and `eye`; `cheek` remains Yellow because the recording does not include a clean E7 candidate sample. P8 reference UV atlas runtime evidence is now collected for `lip`, `cheek`, and `eye`; all three remain Yellow because attachment improved but silhouette/material quality and required motion scenarios are not Q3 overlay-ready yet.

Decision:

- E7.03 Phase 0 Contract Reset is complete. `docs/roadmaps/active/E7_REGION_PRECISION_SUBSPIKE_PLAN.md` v2.1 is the active E7.03 boundary engine plan.
- E7.03 v2.1 Phase 1 Validation UI/Evidence Hygiene is implemented in the RN validation UI, JS-verified, and smoke-verified through a fresh real-device build/install/launch/runtime-log pass.
- E7.03 v2.1 Phase 2 ARFace authored atlas MVP is implemented in Unity and RN, with manual vertex label groups for `lip`, `cheek`, and `eye`, topology/UV audit evidence metadata, RN-dispatchable atlas variants, and preserved E3/E4 baseline plus current procedural candidate paths.
- E7 reference-driven UV atlas pre-gold setup was initialized locally before P2 capture: RN display/evidence wording identifies the current atlas path as a manual heuristic baseline, and `evidence/e7-reference-atlas/` contains the ignored local skeleton, manifest schema, manifest, and earlier pending `pair_lip_0001` capture-pair README. Current P2 evidence uses the newer common `pair_face_*` capture folders.
- E7.03 P2 synchronized reference capture is complete for input collection: clean `frame.png`, same-moment `arface_export.json`, `projected_mesh_overlay.png`, and `capture_summary.json` were exported and copied for three unique `pair_face_*` attempts. The best current drawing input is `pair_face_20260622T143334Z_03`.
- P2 remains an input-acquisition step only. It does not accept a gold mask, prove UV round-trip, change region G/Y/R, start MediaPipe runtime, or promote E7.03 Green.
- E7.03 A/B UV atlas fast gate is complete for offline viability only. After changing the script default to 1px back-projection sampling, `lip`, `cheek`, and `eye` all pass the fast gate; this keeps the reference-driven UV path alive and allows preparing a small P8 runtime sweep candidate set behind a Build Gate.
- E7.03 P8 runtime sweep implementation and first iPhone runtime pass are complete. It freezes 9 fast-gate-derived reference UV variants (`core`, `balanced`, `soft-wide` per region), adds `e7-reference-uv-atlas` as the primary runtime sweep renderer, keeps `e3e4-baseline`, `e7-arface-uv-candidate`, and `e7-arface-authored-atlas` as compare-only paths, and records real-device runtime compare logs plus representative Compact HUD photos.
- The previous "better than E3/E4 baseline" / "demo-plausible" Green standard is superseded by Q3 overlay-ready validation for `lip`, `cheek`, and `eye`.
- `TECH_VALIDATION_TEST_PLAN.md` was not changed for Phase 0 because no stable validation contract correction was required.
- Keep E3/E4 baseline renderer available as `e3e4-baseline`.
- Keep the previous E7 validation candidate renderer as `e7-arface-uv-candidate`; it remains a rejected/negative procedural baseline unless future evidence says otherwise.
- Add the Phase 2 authored atlas renderer as `e7-arface-authored-atlas`, default-selected for E7.3 atlas validation.
- Keep ARFace mesh/UV as a viable runtime substrate, but reject the current procedural candidate mask output for `lip` and `eye` until the candidate basis is replaced or tuned.
- Continue RN + Unity + ARKit validation only. Do not claim product-readiness, product-quality makeup, M7 Green, E7.4/E7.5/E7.6 readiness, AI/backend/upload, MediaPipe live runtime, SDK, or Android scope from this result.

Confirmed implementation:

- Unity `E3RegionMaskOverlay` now supports baseline-vs-E7 candidate modes plus `e7-arface-authored-atlas` while preserving the E3/E4 centroid baseline path.
- E7 candidate mode uses ARFace mesh availability plus UV-aware candidate evidence fields and face-local mesh regions for `lip`, `cheek`, and `eye`.
- Phase 2 authored atlas mode uses manual face-local vertex label groups (`lip_ring`, `cheekbone_soft_cheek`, `eyelid_band`) and RN-selectable variants for tight/balanced/wide or high/extended atlas sweeps.
- P8 reference UV atlas mode uses frozen probability atlas assets generated from `fast-gate-20260622T160307Z`. Unity samples the selected atlas through ARFace UV centroids using runtime-loaded Resources textures, while RN can sweep `core`, `balanced`, and `soft-wide` variants per `lip`, `cheek`, and `eye` in Compact HUD or Full Debug.
- Runtime comparison/evidence metadata now includes candidate id, variant id, atlas version, label map, label group, topology audit status, vertex/UV/index counts, labeled vertex counts, config hash, fallback flag, and fallback reason.
- P8 reference UV atlas metadata also logs source frame count, gold mask count, silver reference count, UV resolution, threshold, feather UV pixels/normalized value, combine mode, morphology, and calibration score summary in the Unity runtime comparison stream.
- Unity emits E7 comparison/state fields for renderer mode, mask source, tracking state, state action, mesh/UV counts, baseline triangle count, candidate triangle count, and applied triangle count.
- Tracking, Limited, lost, and recovered states now map to explicit actions such as render, short hold, fade, extended hide, and recovered restore.
- RN sends `rendererMode`, `candidateId`, and `variantId`, exposes a Baseline/E7 UV/Atlas segmented control, defaults E7.3 to `Atlas`, and surfaces phase/mask/UV/triangle/state/atlas fields in the E7 status panel and event summaries.
- RN recipe dispatch preserves the existing `ApplyRecipeJson` path and `recipe_applied` event while adding atlas metadata at the recipe/layer/ack/evidence levels.
- RN validation UI now supports `Clean`, `Compact HUD`, and `Full Debug` modes so large logs can be hidden during visual region review.
- RN P2 capture UI now starts in `Clean`, hides Unity face renderers/candidate masks/debug overlays for clean-frame capture, uses unique timestamped `pair_face_*` IDs for repeated attempts, disables the capture button while an export is pending, and places the capture button near the bottom of the screen so tapping does not cover the iPhone front camera.
- `Compact HUD` shows candidate id, selected region, tracking/face count, mesh counts, FPS/frame-time, state action, and recipe latency without covering the full AR view.
- `Full Debug` exposes evidence metadata lines for plan/version, evidence mode, candidate id, region, tracking state, face count, mesh counts, blendshape field status, FPS/frame-time, latency, state action, privacy flags, orientation/device fields where available, and latest Unity event.
- Candidate catalog is visible in Full Debug for planning hygiene. Dispatchable validation candidates are `e3e4-baseline`, current procedural `e7-arface-uv-candidate`, and Phase 2 `e7-arface-authored-atlas`; vertex/blendshape, Apple Vision, MediaPipe, parsing, and hybrid candidates remain pending metadata only.
- RN validation app suppresses the React Native dev LogBox warning overlay so the bottom warning bar does not cover AR evidence or recipe controls. Console/runtime evidence logging remains available through captured device logs.
- Current validation cleanup path fixes the renderer to `smooth-region-mask`, removes candidate/variant UI from the user-facing app, keeps `lip`/`cheek`/`eye` enabled by default, supports independent ON/OFF region toggles, and sends exactly three recipe layers in one RN -> Unity batch.
- Unity rejects legacy/non-batch recipe payloads, unsupported renderer modes, missing/mismatched texture samples, missing/mismatched smooth mask texture ids, and invalid region names instead of silently falling back to an old or wrong region. If parsing fails, Unity clears current recipes and hides overlays to avoid stale masks.
- Compact HUD status now lives inside the bottom `Regions` panel, so it no longer covers the center of the face during validation.

Evidence:

- Phase 1 JS verification: `./node_modules/.bin/tsc --noEmit` passed from `rn/MakeupARValidation`.
- Phase 1 lint verification: `npm run lint` passed from `rn/MakeupARValidation`.
- Phase 1 LogBox cleanup JS verification after screenshot review: `./node_modules/.bin/tsc --noEmit` and `npm run lint` passed from `rn/MakeupARValidation`.
- Phase 1 JS-only pass intentionally did not run `bash scripts/build_m3_unityframework.sh`, `xcodebuild`, `npm run ios`, or a real-device build.
- Phase 2 JS verification after atlas implementation: `./node_modules/.bin/tsc --noEmit` and `npm run lint` passed from `rn/MakeupARValidation`.
- P2 synchronized capture JS verification after capture UI fixes: `./node_modules/.bin/tsc --noEmit` and `npm run lint` passed from `rn/MakeupARValidation`.
- Reference-driven UV atlas pre-gold setup verification: `python3 -m json.tool evidence/e7-reference-atlas/manifest.json` passed; `python3 -m json.tool evidence/e7-reference-atlas/manifest.schema.json` passed; `find evidence/e7-reference-atlas -maxdepth 3 -type f` lists `README.md`, `manifest.json`, `manifest.schema.json`, and `capture_pairs/pair_lip_0001/README.md`; `./node_modules/.bin/tsc --noEmit`, `npm run lint`, and `git diff --check` passed. This verification is no-build/no-device only.
- Phase 2 diff hygiene: `git diff --check` passed after reverting the Unity scene reserialization produced by the build.
- Phase 1 real-device follow-up regenerated UnityFramework with `bash scripts/build_m3_unityframework.sh`: `evidence/logs/m3-repro-xcodebuild-unityframework-e7-phase1-ui-2026-06-22-141533.log` records `** BUILD SUCCEEDED **`, and `evidence/logs/m3-repro-artifact-verification-e7-phase1-ui-2026-06-22-141533.log` records arm64 Mach-O RN/package frameworks, both `105M`, with `9.2M` Unity Data.
- Phase 2 UnityFramework regeneration/sync used `bash scripts/build_m3_unityframework.sh`: `evidence/logs/m3-repro-xcodebuild-unityframework-e7-phase2-atlas-2026-06-22-151537.log` records `** BUILD SUCCEEDED **`, and `evidence/logs/m3-repro-artifact-verification-e7-phase2-atlas-2026-06-22-151537.log` records arm64 Mach-O RN/package frameworks, both `105M`, with `9.2M` Unity Data and copied Unity Data.
- P2 UnityFramework regeneration/sync used `bash scripts/build_m3_unityframework.sh`: `evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-22-230402.log` records `** BUILD SUCCEEDED **`, and `evidence/logs/m3-repro-artifact-verification-2026-06-22-230402.log` records arm64 Mach-O RN/package frameworks, both `105M`, with `9.2M` Unity Data and copied Unity Data.
- Phase 1 RN iOS build/install/launch: `evidence/logs/e7-phase1-ui-rn-ios-run-2026-06-22-141533.log` records the Debug build using device id `00008140-000924DE21BB801C`, successful build, install, bundle id `com.makeupar.rnvalidation`, and successful launch on `위승철의 iPhone`.
- Phase 2 RN iOS build/install: `evidence/logs/e7-phase2-atlas-2026-06-22-151537-rn-ios-device.log` records successful Debug build and install on `위승철의 iPhone`; launch was denied because the device was locked, so this is build/install evidence only.
- P2 RN iOS build/install/launch after unique capture-id and bottom-button fix: `evidence/logs/e7-reference-capture-rn-ios-run-2026-06-22-233049.log` records successful Debug build, install, and launch on `위승철의 iPhone`.
- P2 runtime console: `evidence/logs/e7-reference-capture-runtime-console-2026-06-22-233202.log` records three `reference_capture_requested` / `reference_capture_exported` pairs with exported capture IDs `pair_face_20260622T143300Z_01`, `pair_face_20260622T143305Z_02`, and `pair_face_20260622T143334Z_03`.
- P2 copied capture artifacts: each of `pair_face_20260622T143300Z_01`, `pair_face_20260622T143305Z_02`, and `pair_face_20260622T143334Z_03` contains `frame.png`, `arface_export.json`, `projected_mesh_overlay.png`, and `capture_summary.json` under `evidence/e7-reference-atlas/capture_pairs/`.
- P2 artifact verification: all three captures have `frame.png` and `projected_mesh_overlay.png` at `1179x2556`, `trackingState=Tracking`, mesh counts `1220` vertices / `6912` indices / `1220` UVs, `screenVertices=1220`, `annotationFrameClean=true`, `hudIncludedInFrame=false`, `meshOverlayIncludedInFrame=false`, `candidateOverlayIncludedInFrame=false`, and `blendShapes.available=false`.
- P2 visual review: `pair_face_20260622T143300Z_01/frame.png`, `pair_face_20260622T143305Z_02/frame.png`, and `pair_face_20260622T143334Z_03/frame.png` are clean frames with no white face model, colored candidate mask, Unity debug panel, or RN capture controls visible. `pair_face_20260622T143300Z_01/projected_mesh_overlay.png` and `pair_face_20260622T143334Z_03/projected_mesh_overlay.png` visually align to the same frame; `_03` is the best current gold-mask drawing candidate because the face is frontal and calm.
- Fast gate script verification: `/Users/wiseungcheol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile scripts/e7_reference_atlas/fast_uv_atlas_gate.py` passed.
- Fast gate run: `/Users/wiseungcheol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 scripts/e7_reference_atlas/fast_uv_atlas_gate.py` completed with overall decision `continue` and output root `evidence/e7-reference-atlas/fast-gate-20260622T160307Z/`.
- Fast gate region metrics: `lip` same-frame IoU `0.9720` / `0.9693`, cross-frame IoU `0.8193` / `0.8325`, UV core/union `0.7046`; `cheek` same-frame IoU `0.9912` / `0.9906`, cross-frame IoU `0.8363` / `0.8302`, UV core/union `0.7106`; `eye` same-frame IoU `0.8604` / `0.8457`, cross-frame IoU `0.6948` / `0.7129`, UV core/union `0.8060`.
- Fast gate visual review: `lip_candidate_preview.png`, `cheek_candidate_preview.png`, and `eye_candidate_preview.png` show plausible face-attached transfer between A/B for offline viability. This supports candidate preparation for runtime sweep, but still needs real-device visual/runtime evidence before any E7.03 Green claim.
- P8 runtime sweep static implementation verification: frozen Resources were generated from `fast-gate-20260622T160307Z` into `unity/MakeupARUnityValidation/Assets/Resources/E7ReferenceAtlas/e7ref-fastgate-20260622T160307Z-v0/`; `runtime_candidates.json` lists `rendererMode="e7-reference-uv-atlas"`, `candidateId="arface-reference-uv-atlas"`, 2 source frames, 2 gold masks, UV resolution `512x512`, and 9 promoted variants. Static checks passed with no Unity/RN device build: `/Users/wiseungcheol/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m py_compile scripts/e7_reference_atlas/fast_uv_atlas_gate.py`, `./node_modules/.bin/tsc --noEmit`, `npm run lint`, and `git diff --check`.
- P8 UnityFramework regeneration/sync after Build Gate approval used `TIMESTAMP=e7-p8-runtime-sweep-2026-06-23-013524 bash scripts/build_m3_unityframework.sh`: `evidence/logs/m3-repro-xcodebuild-unityframework-e7-p8-runtime-sweep-2026-06-23-013524.log` records `** BUILD SUCCEEDED **`, and `evidence/logs/m3-repro-artifact-verification-e7-p8-runtime-sweep-2026-06-23-013524.log` records synced RN/package UnityFramework artifacts and Unity Data.
- P8 RN iOS build/install/launch used `npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK` from `rn/MakeupARValidation`: `evidence/logs/e7-p8-runtime-sweep-rn-ios-run-2026-06-23-013524.log` records successful install/launch on device id `00008140-000924DE21BB801C`.
- P8 runtime console stream: `evidence/logs/e7-03-p8-runtime-console-2026-06-23-013524.log` captures the full `devicectl --console` stream until manual stop. Compact HUD overlay visibility is logged as `validationViewMode=compact`, `visible=true`, and `faceRenderersSuppressed=false`; later Clean segments intentionally log `visible=false` / `suppressed_for_clean_reference_capture`.
- P8 runtime region compare evidence: the console stream records `lip-uvref-v0-balanced`, `cheek-uvref-v0-balanced`, and `eye-uvref-v0-balanced` with `rendererMode=e7-reference-uv-atlas`, `candidateId=arface-reference-uv-atlas`, `trackingState=Tracking`, `stateAction=tracking_render`, mesh/UV counts `1220/6912/1220`, `uvResolution=512`, `threshold=0.45`, `featherUvPixels=2`, `atlasVersion=e7ref-fastgate-20260622T160307Z-v0`, `topologyAuditStatus=pass_uv_topology_ready`, and `usedFallback=false`.
- P8 representative visual evidence: user-provided Compact HUD photos are stored under `evidence/screenshots/e7-03-p8-runtime-sweep-2026-06-23-013524/`. They show `Ref UV` selected, `candidate=arface-reference-uv-atlas`, Compact HUD visible, and face-attached masks for `lip`, `cheek`, and `eye` across `eye core`, `eye balanced`, and `eye soft-wide` variant checks. Visual preference for `eye` is `balanced` as the current default; `core` is safer but too broken/under-covered for the main candidate, and `soft-wide` is too broad.
- E7.03 smooth-mask cleanup acceptance screenshots: `evidence/screenshots/e7-smooth-mask-accepted-2026-06-23/01-frontal-hud.jpg`, `02-left-angle-hud.jpg`, and `03-right-angle-hud.jpg`. These are the only retained media for this acceptance pass per user request. They show Compact HUD moved to the bottom controls, visible subtle eye/cheek/lip color, `active=lip,cheek,eye`, `focus=eye`, `opacity=0.48`, `intensity=0.58`, `applied=true`, tracking face count `1`, mesh counts `1220/6912/1220`, FPS range `52.2-60.2`, and recipe latency `36.0ms`. User evaluation: acceptable for closing this step, but visually still too subtle overall; the eye boundary remains a little weak; future validation should make region coverage easier to judge, and the remaining issue is deferred into cosmetic expression/modeling.
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

- Legacy procedural `lip`: Red. E7 procedural candidate mode is live, but the selected `lip` candidate repeatedly paints surrounding lower-face skin in normal tracking frames.
- Legacy procedural `cheek`: Yellow / insufficient E7-candidate sample. Cheek selection is present, but the visible metric is baseline or transition-stale, so no region Green/Red is justified yet.
- Legacy procedural `eye`: Red. E7 procedural candidate mode is live, but the selected `eye` candidate is not confined to an eyeshadow/eye region and covers broad non-eye areas.
- P8 reference UV `lip`: Yellow. Runtime log confirms ARFace UV sampling with fallback disabled, and photos show the lip mask stays mouth-local, but the silhouette is jagged/flat and not Q3 overlay-ready.
- P8 reference UV `cheek`: Yellow. Runtime log confirms tracking render with fallback disabled, and photos show cheek-local masks, but the region is still blocky/low on the face and needs yaw/pitch/near-far scenario review.
- P8 reference UV `eye`: Yellow. Runtime log confirms tracking render with fallback disabled, and photos show eye-local masks across core/balanced/soft-wide checks. `eye balanced` is the best current candidate among the three because it preserves eyelid coverage better than `core`; `soft-wide` is too broad. The remaining blocker is jagged/overbroad silhouette quality, not runtime attachment.

Known limitations:

- The earlier E7.3 screen-recording review still lacks a full runtime console stream; the fresh Phase 1 follow-up has a runtime console stream, but no fresh visual screenshot/recording.
- No `[E7] region_precision_compare` runtime stream was captured during this pass.
- P8 runtime evidence is a first representative pass, not a complete required-scenario sweep. Neutral/front-facing photos are present, but smile/open-close/pucker/yaw for `lip`, near/far/yaw/pitch for `cheek`, and blink/repeated blink/squint/head pitch for `eye` still need structured review before any region can become Green.
- P8 Compact HUD photos still show an opaque white full-face debug surface behind the colored regions. That is useful for validation visibility, but it blocks a Q3 overlay-ready makeup claim until the material/debug-surface behavior is separated from region mask evidence.
- The accepted smooth-mask cleanup screenshots are user-accepted for the current app optimization goal, not a formal E7.03 Green decision. They do not cover the full required motion matrix, diverse lighting/users, E7.4 cosmetic material realism, or the user's noted visibility/eye-boundary weakness.
- Phase 2 atlas runtime launch limitation is superseded for P2 capture only: the app now launches and captures synchronized reference pairs, but this still is not runtime atlas visual scoring and does not change Phase 2 region G/Y/R.
- The reference-driven UV atlas path has captured synchronized P2 inputs, but `goldMaskWork.status` is still `not_started`; there is no official user-authored gold mask, UV back-projection, same-frame round-trip render, P3 acceptance, or P4 validation yet.
- The A/B fast gate used user-authored mask PNGs already present in the capture folders, but it does not normalize `manifest.json` into official multi-frame gold-mask status and does not replace the full P3/P4/P5/P6 pipeline.
- The fast gate excludes `triangleVisibility`, occlusion/depth conflict handling, and blendshape correction because the current export has no triangle visibility records and `blendShapes.available=false`.
- The canonical fast gate summary is `fast-gate-20260622T160307Z`. Earlier debug/sparse-sampling/smoke outputs were removed or superseded and should not be used for decisions.
- P2 export records `blendShapes.available=false` because blendshapes are not exposed in the current capture exporter.
- P2 export records `coordinateSpaceValidated=false` / `pending_projected_mesh_overlay_review`; visual overlay review is positive for `_01` and `_03`, but no automated pixel-level coordinate acceptance threshold has been implemented.
- Cheek still needs a clean `phase=region_precision` sample before final region scoring.
- Lost, Limited, and recovered behavior were not exercised in this recording.
- On-screen FPS/frame-time values are visible, but this is not E7.6 performance evidence.
- The candidate is a validation candidate, not product-quality region segmentation or cosmetic rendering.
- Phase 2 manual atlas labels are authored validation heuristics over ARFace mesh/UV data. They are not MediaPipe, Apple Vision, face parsing, product segmentation, or a product-ready makeup asset source.
- Timestamped P2 capture IDs intentionally differ from the original fixed `pair_face_0001` request so repeated capture attempts do not overwrite each other. This is an evidence-management adjustment, not a renderer behavior change.
- E7.3 evidence does not resolve the accepted M7 Yellow lifecycle risk.
- Phase 1 UI modes are visually screenshot-verified from user-provided iPhone captures, and Phase 2 installed the LogBox-suppressed RN build on-device, but post-LogBox visual confirmation is still pending because launch was blocked by device lock. The local toolchain still has no automated iPhone screenshot CLI, and installed `devicectl`/`xcdevice` exposes no screenshot command.
- Non-atlas future candidates shown in the candidate catalog are not runtime implementations; they are pending labels for later E7.03 phases.
- `Full Debug` can still cover part of the AR view by design; use `Clean` or `Compact HUD` for visual evidence capture.
- Phase 1 does not change region G/Y/R: `lip` remains Red, `cheek` remains Yellow / insufficient E7 candidate sample, and `eye` remains Red.
- Phase 1 runtime evidence is dominated by the default `lip` candidate path; it does not provide clean `cheek` or `eye` visual region evidence.
- Phase 2 does not claim M7 Green, E7.4/E7.5/E7.6 readiness, AI/backend/upload readiness, SDK readiness, Android readiness, product readiness, or M7 lifecycle closure.

Next boundary:

- The current smooth-mask validation app cleanup/optimization goal is closed by user acceptance, with screenshots retained as the only media artifact for that pass.
- If continuing E7.3 strictly, use the accepted smooth-mask cleanup as the current usable validation app state and run structured region scenarios before any Green decision.
- If entering the next makeup-modeling scope, first create or update `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` and explicitly record that E7.4 starts on top of an accepted-for-validation but still E7.3-Yellow boundary state.
- The next real proof must be a follow-up runtime comparison with full metadata and representative visual evidence for the missing scenarios: smile/open-close/pucker/yaw for `lip`, near/far/yaw/pitch for `cheek`, and blink/repeated blink/squint/head pitch for `eye`.
- Keep the current procedural ARFace mesh/UV candidate and current manual heuristic baseline as compare-only paths unless future evidence promotes a new reference-driven atlas candidate.
- Do not enter E7.4/E7.5/E7.6 until `lip`, `cheek`, and `eye` have Q3 overlay-ready evidence, or until the team explicitly accepts E7.3 Yellow risk and records that later E7.4/E7.5 evidence is conditional and full E7 visual product-readiness remains capped at Yellow.

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
- The balanced profile removes large reproducible generated artifacts while preserving `node_modules`, iOS `Pods`, Unity `Library`, logs, screenshots, and existing evidence directories. Use `--profile share` before handing the directory to teammates; it removes ignored evidence, dependency installs, editor caches, and build products.
- To prevent workspace growth, keep `evidence/`, `unity-builds/`, RN `node_modules`, iOS `Pods`, Xcode DerivedData/build folders, Unity `Library`/`Logs`/`UserSettings`, raw recordings, and full build logs out of source control and remove them with the cleanup profiles when they are no longer active evidence/debug state.
- `scripts/build_m3_unityframework.sh` now defaults to temporary DerivedData plus temporary Unity/Xcode full logs and keeps only the small artifact verification summary. Use `BUILD_LOG_MODE=full` or `KEEP_DERIVED_DATA=1` only for a specific evidence/debug pass.
- After cleanup, the next real-device Unity/RN session must regenerate UnityFramework with `bash scripts/build_m3_unityframework.sh`.
- Detailed cleanup procedure lives in `docs/runbooks/LOCAL_WORKSPACE_CLEANUP_RUNBOOK.md`.
- Team onboarding, share execution requirements, directory structure, and local-only values live in `docs/runbooks/TEAM_SHARE_REQUIREMENTS_KO.md`.

Token policy:

- Future sessions should start from `AGENTS.md` plus `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`.
- Do not load all research reports by default.
- Load only the research axis that matches the current E7 milestone.
- Do not load `docs/roadmaps/active/`, `docs/roadmaps/research/`, or `docs/roadmaps/archive/` as whole folders. Use `docs/roadmaps/README.md` as the menu and open only the selected file.
- For `_KO.md` / `_KR.md` companion pairs, agents should read the `_KO.md` primary implementation plan and skip `_KR.md` unless user-facing wording is specifically needed.
- For broad search, exclude lockfiles and generated project/config files unless the task is dependency or native project troubleshooting: `package-lock.json`, `Podfile.lock`, Xcode `project.pbxproj`, and Unity `ProjectSettings/*.asset`.
- For large code hotspots, use symbol search plus targeted ranges instead of opening whole files by default: `rn/MakeupARValidation/App.tsx`, `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`, `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs`, and `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`.

Result growth policy:

- Keep this file as a compact routing and decision record, not a full log dump.
- Record only the latest decision, evidence paths, known limitations, and next boundary. Do not paste full build logs, full console streams, raw JSON dumps, frame lists, or long analysis transcripts into this file.
- When a milestone accumulates old details, move historical evidence lists and superseded narrative into `docs/roadmaps/archive/TECH_VALIDATION_HISTORY_YYYY-MM-DD.md`, then keep only the current high-signal summary here.
- If `Current Session Snapshot` becomes hard to scan, compress older bullets into one status bullet plus archive references before adding new work.
- Prefer metadata, contact sheets, representative frames, and short summary logs over raw recordings or full logs. Keep raw/heavy artifacts local under ignored `evidence/` only while they are active decision evidence.

## Next Milestone Boundary

E1 AR Alignment, E2 Trackable Lifecycle Diagnostics, E3 Region Mask, E4 Texture Sample, E5 AI Feature Readiness Snapshot, E6 Engine Decision, E7.0/E7.1 preflight, and E7.2 Baseline Instrumentation are complete. The 2026-06-23 smooth-mask validation app cleanup/optimization goal is closed by user acceptance: the app now uses the simplified `smooth-region-mask` runtime surface, hides obsolete selector/capture/debug paths from the active UI, keeps HUD evidence in the bottom controls, and stores only the three accepted screenshots under `evidence/screenshots/e7-smooth-mask-accepted-2026-06-23/`. User feedback for the retained screenshots says the makeup is still generally hard to see and the eye boundary is somewhat lacking, but this is acceptable for closing this step and should be addressed with cosmetic expression/modeling. This closes the current app optimization task, not the full E7.03 quality gate. E7.3 remains Yellow overall because Q3 overlay-ready motion/scenario evidence for all three regions is incomplete, and full E7 visual product-readiness is not complete. M0-M6 remain Green. M7 remains Yellow / skipped by decision / risk accepted.

Next boundary decision:

- Primary path: current validation app optimization is closed; next work should either continue E7.3 scenario hardening from the accepted smooth-mask state, or explicitly open E7.4 cosmetic modeling with a new `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` and a recorded Yellow boundary risk.
- Conservative path: run additional M7 re-entry verification if the team wants to replace the accepted M7 Yellow risk with formal 3-cycle lifecycle evidence.
- Renderer path: do not enter E7.4/E7.5/E7.6 until E7.03 v2.1 evidence supports Q3 overlay-ready validation for all three regions, or until the team explicitly accepts the remaining E7.3 Yellow risk, records the boundary, and treats later renderer/demo evidence as conditional with a Yellow cap.
