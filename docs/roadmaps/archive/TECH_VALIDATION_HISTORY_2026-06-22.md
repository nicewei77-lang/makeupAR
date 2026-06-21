# Tech Validation Result

Date: 2026-06-21

Latest re-check: 2026-06-22 04:32 KST

## Scope

Current update: this document records the E7.2 Baseline Instrumentation result on top of the E7.0/E7.1 preflight. E7.2 is Green for baseline instrumentation: implementation has real-device runtime log evidence for FPS/frame-time samples, memory metric availability and values, thermal-unavailable/manual-heat fields, Unity-applied latency, RN-ack `receivedAtMs` latency, and RN-visible E7 status-panel code. A user-provided representative frame was stored as screenshot evidence. The usual at least 10 second recording requirement was explicitly waived by the user for this E7.2 decision because of file size.

M0-M6 are Green. M7 is Yellow / skipped by decision / risk accepted. M8 foundation closeout remains Yellow overall because of the accepted M7 lifecycle gap. E1 AR Alignment is Green; its 19.04 second recording satisfies the revised 10 second decision-recording minimum. E2 Trackable Lifecycle Diagnostics is Green. E3 Region Mask is Green. E4 Texture Sample is Green. E5 AI Feature Readiness Snapshot is Green with the screen-recording requirement explicitly waived by the user. E6 Engine Decision is Yellow. E7.0/E7.1 preflight is Green. E7.2 Baseline Instrumentation is Green with the E7.2-specific recording waiver noted above. Full E7 visual product-readiness remains incomplete.

Full M7 3-cycle re-entry stress testing, E7.3+ region precision, E7.4+ renderer implementation, E7.6 final performance decision, product-quality makeup rendering, AI/backend/admin/payment/community, commercial SDK integration, Android work, and raw camera frame storage were not attempted.

Authoritative inputs:

- `AGENTS.md`
- `TECH_VALIDATION_TEST_PLAN.md` sections 13-15, M6 Unity -> RN communication, M7 re-entry stability, and M8 result report
- `TECH_VALIDATION_RESULT.md` previous `Next Milestone Boundary`
- `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` section 6, M8 Foundation Closeout
- `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` section 9, E3 Region Mask
- `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` E4 Texture Sample boundary
- `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` section 12, E6 Engine Decision
- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` E7.0 Session Preflight and E7.1 Build/Runtime Preflight
- `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md` E7.2 Baseline Instrumentation measurement contract
- E1 implementation/build/runtime/screen evidence recorded in the evidence paths below
- E2 implementation/build/runtime/screen evidence recorded in the evidence paths below
- E3 implementation/build/runtime/screen evidence recorded in the evidence paths below
- E4 implementation/build/runtime/screen evidence recorded in the evidence paths below
- E5 implementation/build/runtime/screenshot evidence recorded in the evidence paths below; decision recording was explicitly waived by the user for this E5 decision
- E7.0/E7.1 preflight build/runtime evidence recorded in the evidence paths below
- E7.2 baseline instrumentation build/runtime evidence recorded in the evidence paths below

## Workspace Document State

Active root documents:

- `AGENTS.md`: repository working rules, milestone scope boundaries, document policy, and evidence/cleanup requirements.
- `TECH_VALIDATION_TEST_PLAN.md`: stable validation contract, milestone order, and document policy.
- `TECH_VALIDATION_RESULT.md`: latest milestone decisions, current status, evidence, and next boundary.

Active temporary session plans:

- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`: active E7 spike plan. This session touched only E7.2 Baseline Instrumentation after the earlier E7.0/E7.1 preflight.
- `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`: active E7 performance evidence sub-spike plan used as the measurement/logging contract for E7.2 baseline instrumentation.
- The remaining sub-spike documents are still deferred: `E7_REGION_PRECISION_SUBSPIKE_PLAN.md` before E7.3, `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` before E7.4, and `E7_DEMO_LOOK_RECIPE_SPEC.md` only if needed.

Completed session-specific plan/status documents have been absorbed into this result document and removed from the active root. New `M*_..._PLAN.md` files should be temporary: create them only when a session needs one, then absorb the outcome here and delete the plan after completion.

## E7.2 Baseline Instrumentation Decision Detail

Status: Green for E7.2 baseline instrumentation

E7.2 Baseline Instrumentation is implemented for the existing E3/E4 renderer path. The implementation adds baseline-only metric/logging surfaces without starting E7.3 region precision, E7.4 cosmetic renderer work, E7.6 final performance decision work, product-v1 readiness, AI/backend/commercial SDK/Android/raw camera frame storage, or M7 Green promotion.

Confirmed implementation:

- Unity runtime now emits `[E7] metric_sample` on an interval with FPS, frame-time, worst frame-time, sustained-sub-20 flag, tracking state, mesh counts, active region/texture baseline state, memory availability, memory values, and thermal/manual-heat fields.
- Unity runtime now emits `[E7] metric_unavailable` for unavailable thermal native API evidence and keeps `thermalMetricYellowCap=true`.
- Unity recipe apply logging now records RN `sentAtMs`, Unity `appliedAtMs`, and Unity `appliedFrame` while preserving the E3/E4 `ApplyRegionRecipe` path.
- RN sends a log-only ack back to Unity after receiving `recipe_applied`, allowing Unity console evidence to record RN `receivedAtMs`, `sendToAckLatencyMs`, `unityApplyLatencyMs`, and `unityToRnReceiveLatencyMs`.
- RN UI includes an E7 status panel that surfaces the latest baseline metric and recipe latency fields.

Confirmed build/runtime evidence:

- `npx tsc --noEmit` passed after the E7.2 implementation.
- Fresh UnityFramework export/build/sync succeeded with `TIMESTAMP=e7-baseline-instrumentation-ack-2026-06-22`.
- UnityFramework evidence paths: `evidence/logs/m3-repro-unity-export-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-baseline-instrumentation-ack-2026-06-22.log`, and `evidence/logs/m3-repro-artifact-verification-e7-baseline-instrumentation-ack-2026-06-22.log`.
- RN iOS build/install/launch succeeded on `위승철의 iPhone`: `evidence/logs/e7-baseline-rn-ios-run-ack-2026-06-22.log` records `success Successfully built the app`, `success Installed the app on the device`, and `success Successfully launched the app`.
- Runtime console evidence was captured at `evidence/logs/e7-baseline-runtime-console-ack-2026-06-22.log`.
- Baseline summary evidence was recorded at `evidence/logs/e7-baseline-summary-2026-06-22.md`.
- Representative frame evidence was provided by the user and stored at `evidence/screenshots/e7-baseline-status-panel-2026-06-22.jpg` (`590x1280` JPEG). It shows the RN-visible E7 Baseline panel with `fps=60.1`, `frame=16.6ms`, `memory=true`, `alloc=64.4MB`, `thermal=manual-device-heat`, and recipe latency around `17.0ms`.
- The usual at least 10 second baseline screen recording was explicitly waived by the user for this E7.2 decision because of file size.

Runtime summary:

- Runtime log line count: `65,428`.
- `[E7] metric_sample`: `9`.
- `[E7] metric_unavailable`: `1`.
- `[E7] recipe_latency source=unity_applied`: `14`.
- `[E7] recipe_latency source=rn_ack`: `14`.
- `memoryMetricAvailable=true`: `9`.
- `thermalEvidenceType=manual-device-heat`: `10`.
- Unity -> RN `e7_metric_sample` sends: `9`.
- Tracking-state metric samples: `7`; average FPS mean/min/max `57.6 / 51.4 / 60.1`; average frame-time mean `17.4 ms`; allocated memory range `64.3-64.9 MB`; reserved memory max `82.2 MB`.
- RN ack latency samples: `14`; RN sent -> RN received mean/min/max `137.6 / 33.0 / 1473.0 ms`; Unity applied -> RN received mean/min/max `28.4 / 7.0 / 208.0 ms`.

Known limitations:

- The first metric and first latency samples include cold-start overhead and should not be used as a final E7.6 performance decision.
- Native thermal API integration is not configured; thermal status is recorded as manual-device-heat evidence with a Yellow cap.
- The E7.2 decision relies on a user-provided representative frame instead of a screen recording; this waiver is scoped only to E7.2 and does not waive future E7.3/E7.4/E7.6 evidence expectations.

Next boundary decision:

- Next Milestone Boundary: E7.3 Region Precision sub-spike planning/validation, if the team continues under the accepted M7 Yellow lifecycle risk.
- E7.3 was not started in this E7.2 session.
- Do not proceed to E7.4 or E7.6 from this result alone.
- Do not claim product-v1 readiness or promote M7 to Green from this result.

## E7.0/E7.1 Preflight Decision Detail

Status: Green for E7.0/E7.1 preflight only

E7.0 Session Preflight and E7.1 Build/Runtime Preflight are Green. The session confirmed the current branch/worktree, kept `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` as the active temporary plan, accepted the existing M7 Yellow risk only for E7 validation, cleaned/checkpointed Unity process state, regenerated and synced UnityFramework, built/installed/launched the RN iOS app on the real iPhone, and confirmed the existing RN-hosted Unity event path still emits the required M6 events.

Preflight decisions:

- Git state at session start: branch `codex/makeupar-github-sync`, single worktree at `/Users/wiseungcheol/Desktop/makeupAR`, working tree clean, branch ahead of origin by 3 commits.
- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` is the active temporary E7 plan. It was not absorbed or deleted because full E7 is not complete.
- E7 sub-spike document timing is fixed but no sub-spike documents were created in this session: `E7_REGION_PRECISION_SUBSPIKE_PLAN.md` before E7.3, `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` before E7.4, `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md` before E7.6, and `E7_DEMO_LOOK_RECIPE_SPEC.md` only if needed.
- M7 remains Yellow / skipped by decision / risk accepted. This preflight does not promote M7 to Green.
- Unity/Hub/Licensing cleanup check found no active Unity, Unity Hub, or Unity Licensing processes and no `/tmp/Unity-LicenseClient*` stale files before the build.

Confirmed evidence:

- Fresh UnityFramework export/build/sync succeeded through `bash scripts/build_m3_unityframework.sh` with `TIMESTAMP=e7-preflight-2026-06-22`.
- Unity/Hub/Licensing cleanup evidence was recorded at `evidence/logs/e7-unity-process-cleanup-2026-06-22.log`.
- UnityFramework evidence paths: `evidence/logs/m3-repro-unity-export-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-preflight-2026-06-22.log`, and `evidence/logs/m3-repro-artifact-verification-e7-preflight-2026-06-22.log`.
- Artifact verification records both the RN reference framework and the package-local framework as arm64 Mach-O binaries, each about `105M`, each with `9.2M` `Data`, and with `NativeCallProxy.h` present.
- RN iOS build/install/launch succeeded on `위승철의 iPhone`: `evidence/logs/e7-build-install-run-2026-06-22.log` records `success Successfully built the app`, `success Installed the app on the device`, and `success Successfully launched the app`.
- Runtime console evidence was captured at `evidence/logs/e7-runtime-event-preflight-2026-06-22.log`. It records UnityFramework loading inside RN, `runEmbeddedWithArgc`, `unity_initialized`, `face_detected` with `tracked=true`, `faceCount=1`, and `recipe_applied` events.

Known limitations:

- This is not a full E7 completion. At the E7.0/E7.1 preflight point, E7.2 baseline instrumentation, E7.3 region precision, E7.4 cosmetic rendering core, E7.6 performance evidence, and any demo-look recipe work had not started. Current E7.2 implementation status is recorded in the E7.2 section above.
- This session did not collect FPS, frame-time, thermal, memory, latency, region G/Y/R, or demo-look evidence.
- The current E3/E4 visuals remain validation/debug quality. Product-quality lip, cheek, or eye makeup readiness is not claimed.
- The build temporarily caused Unity scene reserialization noise; it was restored so no source implementation change is retained from this preflight.
- No product/backend/AI inference/commercial SDK/Android/raw camera frame storage work was started.

Next boundary decision:

- At the E7.0/E7.1 preflight point, the next boundary was E7.2 Baseline Instrumentation. The current boundary is recorded in the final `Next Milestone Boundary` section.
- Continue under the accepted M7 Yellow risk only if the team still accepts that lifecycle gap; otherwise run formal M7 re-entry verification before further renderer hardening.

## E6 Decision Detail

Status: Yellow

E6 Engine Decision is Yellow. The validation evidence supports continuing on the current RN + Unity + ARKit path, but not treating the engine as product-v1-ready without focused hardening. The result is not Red because the core integration, tracking, alignment, region dispatch, texture-sample dispatch, and no-inference feature snapshot handoff all have real-device evidence. The result is not Green because M7 remains formally skipped/risk-accepted, clean rebuild durability still depends on local bridge/framework sync caveats, E3/E4 prove debug-validation visuals rather than product-quality makeup, and performance/thermal behavior has not been measured with an explicit FPS or profiling pass.

Decision matrix:

| Layer | E6 readout | Evidence basis |
| --- | --- | --- |
| Integration | Yellow / viable with accepted lifecycle caveat | M0-M6 are Green, M8 is Yellow only because M7 was skipped/risk-accepted, and RN-hosted Unity builds/install/runs on the real iPhone. |
| Tracking | Green | RN and runtime evidence show `unity_initialized`, `face_detected`, `face_lifecycle`, and `face_feature_snapshot` state with tracked/lost/recovered information. |
| Alignment | Green for validation | E1 real-device 19.04 second recording and frames show the overlay aligned to face contour/eyes/mouth at validation level. |
| Lifecycle | Yellow | E2 explains lost/recovered behavior and first-face observations, but formal M7 3-cycle re-entry evidence is still absent. |
| Region | Green for validation | E3 proves independent `lip`, `cheek`, and `eye` dispatch and nonzero mesh-region application; the masks remain broad debug masks. |
| Texture | Green for validation | E4 proves `matte_lip`, `soft_blush`, and `shimmer_eye` are distinguishable validation samples on the three allowed regions. |
| Performance | Yellow | E1-E4 recordings are about 60 fps video captures and no obvious severe degradation was recorded, but no explicit FPS/thermal profiling pass exists. |
| AI feature readiness | Green for no-inference handoff | E5 proves a real-device `FaceFeatureSnapshot` with mesh, region, texture-sample, timestamp, and privacy flags, with `rawCameraFrameStored=false` and `offDeviceUpload=false`. |

Final decision outcome:

- Yellow: continue with the current RN + Unity + ARKit direction, but schedule focused hardening before product v1 implementation.
- This is a validation success for the chosen technical direction, not a product-quality AR makeup engine sign-off.
- No fallback path is required now. MediaPipe, ARCore, commercial SDK, or alternate runtime comparison should be considered only if lifecycle, region precision, Android, or shared static/runtime landmark requirements become explicit blockers.

Required product-readiness spikes before Green product handoff:

- Lifecycle: either collect formal M7 3-cycle re-entry evidence or choose and document a Yellow workaround such as pause/resume or hide/show Unity runtime strategy.
- Clean rebuild durability: make the `RNUnityView.mm` timing patch and UnityFramework package sync reproducible outside ignored `node_modules` state.
- Renderer quality: improve beyond E3/E4 broad debug masks and procedural samples before claiming product-quality lip, cheek, or eye makeup.
- Performance: add an explicit real-device FPS/thermal/profiling pass once renderer quality work starts.

Known limitations:

- E6 does not start product implementation, AI inference, backend upload, recommendation logic, commercial SDK integration, Android work, or product-quality makeup rendering.
- E5's recording waiver remains scoped only to E5 and does not waive future decision-recording expectations.
- M7 is still Yellow and must not be silently promoted to Green.

Next boundary decision:

- Next Milestone Boundary: E6 is complete; next work should be a product-readiness hardening plan/spike, starting with lifecycle/durable integration if the team wants a Green product handoff.
- Conservative path: run formal M7 re-entry verification before any product-facing renderer investment.
- Renderer path: if the M7 Yellow risk remains accepted, proceed only to validation-quality renderer hardening and profiling, not product implementation claims.

## E5 Decision Detail

Status: Green

E5 AI Feature Readiness Snapshot is Green. The implementation stays inside the no-inference schema/evidence handoff boundary: Unity summarizes AR face state into a `face_feature_snapshot` payload without raw camera frame storage, AI inference, recommendation logic, backend upload, or product implementation. The real-device runtime log proves snapshot creation and Unity -> RN event send with face/tracking state, face count, mesh counts, active regions, applied texture samples, timestamp, and privacy flags. The RN screenshot proves visible snapshot receipt. The separate at least 10 second screen recording was explicitly waived by the user for this E5 decision.

Implementation summary:

- `FaceTrackingStatusReporter` now builds E5 snapshot JSON from AR session state, face lifecycle state, ARFace pose, mesh counts, provider capabilities, timestamp, device/camera metadata, and explicit privacy flags.
- `RNBridge` now remembers the validation feature state for `lip`, `cheek`, and `eye`, exposes active region and applied texture sample summaries, and sends `face_feature_snapshot` through the existing Unity -> RN event path.
- `rn/MakeupARValidation/App.tsx` now recognizes `face_feature_snapshot`, stores the latest payload, logs RN receipt when the JS handler receives it, and displays a compact FaceFeatureSnapshot status panel on the Unity screen.

Confirmed evidence:

- RN TypeScript check passed: `cd rn/MakeupARValidation && npx tsc --noEmit`.
- UnityFramework export/build/sync succeeded for the E5 implementation: `evidence/logs/m3-repro-unity-export-e5-ai-feature-readiness-2026-06-21.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e5-ai-feature-readiness-2026-06-21.log`, and `evidence/logs/m3-repro-artifact-verification-e5-ai-feature-readiness-2026-06-21.log`.
- RN iOS build/install/launch succeeded on `위승철의 iPhone`: `evidence/logs/e5-build-install-run-2026-06-21.log`.
- Runtime console was captured with `tee` at `evidence/logs/e5-ai-feature-readiness-runtime-2026-06-21.log`.
- Runtime log evidence includes repeated `[E5] face_feature_snapshot_created` and `[E5] unity_to_rn_send` entries. A tracked-face payload records `faceDetected=true`, `tracked=true`, `faceCount=1`, `trackingState=Tracking`, mesh counts `vertexCount=1220`, `indexCount=6912`, `uvCount=1220`, `activeRegionSummary="lip,cheek,eye"`, and `appliedTextureSampleSummary="lip:matte_lip:applied=true,cheek:soft_blush:applied=true,eye:shimmer_eye:applied=true"`.
- User-provided RN status screenshot was saved at `evidence/screenshots/e5-ai-feature-readiness-rn-status-2026-06-21.jpg`; it shows `FaceFeatureSnapshot` as `received`, `schema=1`, `tracking`, `face=1/1`, `camera=User`, `mesh v=1220 i=6912 uv=1220 stableUv=true`, `regions=lip,cheek,eye`, and `rawFrameStored=false upload=false`.
- E4 region/texture independence did not regress in the E5 runtime log: the snapshot carries all three active validation regions and the required texture samples with nonzero mesh triangle counts and `usedFallback=false`.
- Raw frame/off-device storage checks were negative for this E5 implementation path: runtime payloads include `rawCameraFrameStored=false` and `offDeviceUpload=false`; source search over the changed RN/Unity script paths found no `ReadPixels`, `EncodeTo`, `ScreenCapture`, `AVCapture`, `File.Write`, `persistentDataPath`, `fetch`, `axios`, `upload`, or HTTP URL use.

Recording waiver:

- The planned screen-recording artifact `evidence/screen-recordings/e5-ai-feature-readiness-snapshot-2026-06-21.mp4` was not collected.
- User decision at 2026-06-21 23:03 KST: "이번엔 녹화는 필요 없을 것 같아 그린 플래그 띄우자".
- This waiver applies only to E5 decision evidence and does not change future recording expectations unless explicitly repeated.

Snapshot payload interpretation:

- `type`, `schemaVersion`, `timestampMs`, and `timestamp` identify the no-inference snapshot contract and capture time.
- `faceDetected`, `tracked`, `faceCount`, `totalTrackables`, `trackingStates`, `trackingState`, and `lifecycleState` summarize the current face/tracking state.
- `activeFace.pose`, `mesh`, `meshSummary`, and `capabilities` summarize pose/mesh availability and counts without raw image data.
- `activeRegions`, `appliedTextureSamples`, `activeRegionSummary`, `appliedTextureSampleSummary`, and `regions` summarize the E3/E4 validation renderer state for `lip`, `cheek`, and `eye`.
- `rawCameraFrameStored=false`, `offDeviceUpload=false`, and the nested `privacy` object are the explicit non-storage/non-upload privacy markers.

Known limitations:

- E5 does not implement AI inference, recommendation, backend upload, persistent feature storage, raw camera frame capture, or product makeup rendering.
- RN receive is visually proven by screenshot. The missing decision recording is recorded as an explicit user-approved waiver for this E5 decision, not as hidden Green evidence.
- M7 remains Yellow / skipped by decision / risk accepted; E5 does not promote M7 to Green.

Next boundary decision:

- Next Milestone Boundary: E5 is complete; choose the next roadmap boundary before starting new implementation.
- Future milestones should continue to require decision recordings unless the user explicitly waives them again.
- Do not move into AI model inference, backend upload, recommendation logic, product-quality makeup rendering, commercial SDK integration, Android work, or product implementation.

## E4 Decision Detail

Status: Green

E4 Texture Sample is Green for validation/debug purposes. RN preserves `lip`, `cheek`, and `eye` as the only selectable regions and adds a region-specific sample selector. Unity receives texture/sample metadata in the recipe payload while `region` remains the canonical dispatch field. The real-device runtime log proves recipe parse, region dispatch, texture dispatch, applied texture, and RN-visible `recipe_applied` feedback for all three required samples. The 20.53 second decision recording satisfies the 10 second minimum and visually distinguishes `matte_lip`, `soft_blush`, and `shimmer_eye` at debug-validation level.

Implementation summary:

- `rn/MakeupARValidation/App.tsx` keeps the existing `lip`, `cheek`, and `eye` region controls, adds one texture sample option per region, stores `textureSample` per region recipe, keeps color/opacity changes scoped to the selected region, and displays current region/color/opacity/texture/applied status in RN.
- `RNBridge` parses additive `texture`, `sample`, `textureMode`, `intensity`, `feather`, and `blendMode` fields while continuing to dispatch by canonical `region`; it logs `[E4] recipe_parse`, `[E4] region_dispatch`, `[E4] texture_dispatch`, and `[E4] recipe_applied`.
- `E3RegionMaskOverlay` preserves per-region overlay state, uses runtime-generated debug textures for `matte_lip`, `soft_blush`, and `shimmer_eye`, and logs `[E4] applied_texture` for the applied region/sample.

Confirmed evidence:

- UnityFramework export/build/sync succeeded for the E4 implementation: `evidence/logs/m3-repro-unity-export-e4-texture-samples-2026-06-21.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e4-texture-samples-2026-06-21.log`, and `evidence/logs/m3-repro-artifact-verification-e4-texture-samples-2026-06-21.log`.
- RN iOS build/install/launch succeeded on `위승철의 iPhone`: `evidence/logs/e4-build-install-run-2026-06-21.log`.
- Runtime console was captured with `tee` at `evidence/logs/e4-texture-samples-runtime-2026-06-21.log`.
- Runtime log evidence includes successful non-fallback mesh application for all required sample pairs: `lip/matte_lip` applied with `meshTriangles=772-844`, `cheek/soft_blush` applied with `meshTriangles=193-200`, and `eye/shimmer_eye` applied with `meshTriangles=513-520`.
- User-provided real-device screen recording was remuxed to `evidence/screen-recordings/e4-texture-samples-matte-shimmer-blush-2026-06-21.mp4`.
- Screen recording metadata was captured at `evidence/logs/e4-screen-recording-ffprobe-2026-06-21.log`: 20.53 seconds, 1180x2556 portrait, HEVC, about 60 fps.
- Texture comparison contact-sheet screenshot was generated at `evidence/screenshots/e4-texture-samples-comparison-2026-06-21.jpg`.

Observed behavior interpretation:

- `region` remains the canonical Unity dispatch field. `texture`, `sample`, and `textureMode` are additive E4 metadata and do not replace region dispatch.
- `matte_lip` maps to `lip`, `soft_blush` maps to `cheek`, and `shimmer_eye` maps to `eye`; invalid region/sample expansion was not introduced.
- Color and opacity changes remain scoped to the selected region recipe. Runtime logs show repeated updates for cheek, eye, and lip with their own region/sample pair, and `E3RegionMaskOverlay` keeps independent per-region overlay state.
- The three samples are visually distinct enough for validation/debug: `matte_lip` is a flatter lip sample, `soft_blush` is a softer cheek sample, and `shimmer_eye` uses the brighter eye sample with screen-style blending.

Known limitations:

- The samples are procedural debug textures on broad E3 validation masks. They are not product-quality cosmetics, precise segmentation, real product color fidelity, or final blending.
- This result does not validate advanced shaders, commercial beauty SDK parity, product makeup aesthetics, FPS targets, backend upload, AI recommendation, or Android behavior.
- M7 remains Yellow / skipped by decision / risk accepted; E4 does not promote M7 to Green.

Next boundary decision:

- Next Milestone Boundary: E5 AI Readiness Snapshot.
- E5 may validate only a no-inference feature snapshot/schema/evidence handoff. Do not start AI model inference, backend upload, recommendation logic, product makeup rendering, commercial SDK integration, Android work, or product implementation.

## E3 Decision Detail

Status: Green

E3 Region Mask is Green for validation purposes. The real-device run proves independent `lip`, `cheek`, and `eye` control through RN-selected canonical `region` values, Unity recipe parsing, region dispatch, mesh-region application, and Unity-to-RN `recipe_applied` feedback.

Implementation summary:

- `rn/MakeupARValidation/App.tsx` now exposes only `lip`, `cheek`, and `eye` region selection, keeps color/opacity controls per region, sends versioned recipe JSON with canonical `region`, and keeps legacy `layer` as an alias.
- `RNBridge` now parses `version` and `layers[]`, accepts only `lip`, `cheek`, and `eye`, logs `[E3] recipe_parse`, `[E3] region_dispatch`, and `[E3] recipe_applied`, and sends RN events with `region`, `appliedRegion`, `applied`, `faceCount`, `meshTriangles`, and `usedFallback`.
- `E3RegionMaskOverlay` maintains per-region recipe/overlay state and applies validation mesh masks under each tracked `ARFace`, so applying one region does not erase other enabled region overlays.

Confirmed evidence:

- UnityFramework export/build/sync succeeded for the E3 implementation: `evidence/logs/m3-repro-unity-export-e3-region-mask-2026-06-21.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e3-region-mask-2026-06-21.log`, and `evidence/logs/m3-repro-artifact-verification-e3-region-mask-2026-06-21.log`.
- RN iOS build/install/launch succeeded on `위승철의 iPhone`: `evidence/logs/e3-build-install-run-2026-06-21.log`.
- Runtime console was captured with `tee` at `evidence/logs/e3-region-mask-layer-dispatch-2026-06-21.log`.
- Runtime log evidence includes successful mesh application for all required regions with fallback disabled: `lip` applied with `meshTriangles=737`, `cheek` applied with `meshTriangles=196`, and `eye` applied with `meshTriangles=514`; later repeated runs also show nonzero mesh triangles for the same regions.
- User-provided real-device screen recording was copied to `evidence/screen-recordings/e3-region-mask-lip-cheek-eye-2026-06-21.mp4`.
- Screen recording metadata was captured at `evidence/logs/e3-screen-recording-ffprobe-2026-06-21.log`: 38.25 seconds, 1180x2556 portrait, about 60 fps.
- Debug color contact-sheet screenshot was generated at `evidence/screenshots/e3-region-mask-debug-colors-2026-06-21.jpg`.
- User confirmed on the real iPhone that eyes, cheeks, and lips are separated, while noting that the painted ranges are broad and not precise.

Observed behavior interpretation:

- `lip`, `cheek`, and `eye` are independently selected from RN and dispatched by `region`, not only by the legacy `layer` alias.
- Color and opacity updates apply to the selected region and return RN-visible `recipe_applied` status with `applied=true`, `faceCount=1`, nonzero mesh triangle counts, and `usedFallback=false`.
- The E3 result validates region dispatch, attachment, and independent debug rendering. It does not validate product-quality makeup boundaries, texture fidelity, shimmer, commercial SDK parity, or AI readiness.

Known limitations:

- The region masks are broad validation/debug masks. The user observed that the regions are separated but not accurately bounded.
- Edge softness, precise lip/cheek/eye landmarks, upper/lower lip fit, and product-quality makeup aesthetics are not proven by E3.
- The implementation uses validation mesh heuristics, not a production segmentation model, commercial beauty SDK, or texture/shader pipeline.
- M7 remains Yellow / skipped by decision / risk accepted; E3 does not promote M7 to Green.

Next boundary decision:

- Next Milestone Boundary: E4 Texture Sample.
- E4 may validate only the planned minimum texture samples after this E3 result. Do not expand into product-quality makeup rendering, AI/backend/admin/payment/community, commercial SDK integration, Android work, or product implementation.

## E2 Decision Detail

Status: Green

E2 Trackable Lifecycle Diagnostics is Green for validation purposes. The real-device run proves that the RN-hosted Unity app records and displays face trackable lifecycle diagnostics for `trackablesChanged.added/updated/removed`, trackable ID, timestamp, tracking state, selected active face ID, `tracking/lost/reacquired` status, face count, face transform, mesh vertex/index/UV counts, and ARKit provider capability snapshot.

Implementation summary:

- `FaceTrackingStatusReporter` now emits `[E2] trackablesChanged` and `[E2] face_lifecycle` diagnostics and sends `face_lifecycle` payloads to RN.
- `RNBridge` now forwards E2 lifecycle payloads through the existing Unity-to-RN event path.
- `rn/MakeupARValidation/App.tsx` now displays the diagnostic face state, active ID, lifecycle status, changed counts, mesh summary, and provider capability snapshot.

Confirmed evidence:

- UnityFramework export/build/sync succeeded after the final E2 rebuild: `evidence/logs/m3-repro-unity-export-e2-final-2026-06-21.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e2-final-2026-06-21.log`, and `evidence/logs/m3-repro-artifact-verification-e2-final-2026-06-21.log`.
- RN iOS build/install/launch succeeded on `위승철의 iPhone`: `evidence/logs/e2-build-install-run-2026-06-21.log`.
- Runtime console was captured with `tee` at `evidence/logs/e2-trackable-lifecycle-2026-06-21.log`.
- Analysis summary was saved at `evidence/logs/e2-trackable-lifecycle-analysis-2026-06-21.log`: 1086 `face_lifecycle` events, 1086 Unity-to-RN lifecycle sends, status counts `tracking:1064`, `lost:15`, `reacquired:7`, raw `trackablesChanged` totals `added:1`, `updated:1073`, `removed:0`.
- User-provided real-device screen recording was copied to `evidence/screen-recordings/e2-trackable-lifecycle-scenarios-2026-06-21.mp4`.
- Screen recording metadata was captured at `evidence/logs/e2-screen-recording-ffprobe-2026-06-21.log`: 18.35 seconds, 1180x2556 portrait, HEVC, about 60 fps, creation time `2026-06-21T12:23:18Z` / `2026-06-21 21:23:18 KST`.
- RN face-state screenshot was generated at `evidence/screenshots/e2-rn-face-state-2026-06-21.jpg`; it shows `face_lifecycle lost`, active face ID, mesh `v=1220,i=6912,uv=1220,meshV=1220`, and provider capability text.

Observed behavior interpretation:

- First-face behavior: the run starts with no face as `status=lost`, then `trackablesChanged.added=1` creates trackable `F344E15BABC190CD-1DEF21B23315A688` with `Tracking`.
- Lost/recovered behavior: the same trackable ID repeatedly moves from `Tracking` to `trackingState=None`, `tracked=false`, `faceCount=0`, `status=lost`, then returns to `Tracking` with `status=reacquired`.
- Second-face behavior: no distinct second trackable ID was observed. The provider did not emit `removed` or a second `added`; the active face ID stayed `F344E15BABC190CD-1DEF21B23315A688` and recovered as the same ARFace trackable.
- Partial occlusion and close/far movement are diagnosable in the captured stream through `tracking/lost/reacquired`, face transform changes, and stable mesh summaries.
- Provider capability snapshot in the runtime stream reports `supportsFacePose=true`, `supportsFaceMeshVerticesAndIndices=true`, `supportsFaceMeshUVs=true`, and `supportsEyeTracking=true`.

Known limitations:

- This E2 result is Green for lifecycle diagnostics, not for person identity recognition. The second-face scenario did not produce a distinct provider trackable ID in this run.
- `trackablesChanged.removed` stayed `0`; ARKit surfaced loss as an updated persistent face trackable with `trackingState=None`, not as a removed trackable.
- `limited` did not appear in this run; observed runtime statuses were `tracking`, `lost`, and `reacquired`.
- M7 remains Yellow / skipped by decision / risk accepted; E2 does not promote M7 to Green.

Next boundary decision:

- Next Milestone Boundary: E3 Region Mask.
- E3 must validate only `lip`, `cheek`, and `eye`; do not start texture rendering, shimmer, product-quality makeup, AI/backend/admin/payment/community, commercial SDK integration, Android work, or product implementation from this E2 result.

## E2 Build Blocker Re-check

Status: Build blocker resolved

This section records the earlier E2 build blocker re-check. It resolved the Unity export blocker that prevented the E2 build loop from reaching `UnityFramework.framework` generation.

Action taken:

- Confirmed the failing export log was a Unity Licensing Client IPC/version handshake problem, not an E2 C# or RN code compile problem.
- Confirmed Unity Hub is installed at version `3.18.3` and the Editor-local `Unity.Licensing.Client` binary exists under Unity `6000.3.18f1`.
- Found stale/conflicting Unity processes: GUI Unity Editor, Hub `UnityLicensingClient_V1`, and an older Editor helper `Unity.Licensing.Client`.
- Quit Unity/Unity Hub, force-terminated the stuck Unity/Unity Licensing Client processes that survived normal quit, and removed stale `/tmp/Unity-LicenseClient*` entries.
- Re-ran `TIMESTAMP=e2-licfix-2026-06-21 bash scripts/build_m3_unityframework.sh`.

Confirmed evidence:

- Previous failure log recorded `Unsupported protocol version '1.18.1'`, missing `LicenseClient-wiseungcheol-6000.3.18`, licensing initialization timeout, and lost Licensing Client connection: `evidence/logs/m3-repro-unity-export-e2-2026-06-21.log`.
- The retry export passed Unity iOS export with `Build Finished, Result: Success` and `[M1] Unity iOS export result: Succeeded`: `evidence/logs/m3-repro-unity-export-e2-licfix-2026-06-21.log`.
- Generated Xcode project still contained required ARKit native links: `UnityARKit.m`, `libUnityARKit.a`, `libUnityARKitFaceTracking.a`, `ARKit.framework`, and `MetalPerformanceShaders.framework`.
- `UnityFramework` Xcode build completed with `** BUILD SUCCEEDED **`: `evidence/logs/m3-repro-xcodebuild-unityframework-e2-licfix-2026-06-21.log`.
- Artifact verification confirmed arm64 RN and package-local `UnityFramework.framework` copies with Data and `NativeCallProxy.h`: `evidence/logs/m3-repro-artifact-verification-e2-licfix-2026-06-21.log`.

Known limitations:

- This proved the Unity export/build blocker was cleared for the retry run; the E2 decision above supersedes that earlier unresolved runtime state.
- If the Unity Licensing Client popup returns, first repeat the process cleanup path before reinstalling Unity or resetting Hub settings.

Next boundary decision:

- Superseded by the E2 Decision Detail above.

## E1 Decision Detail

Status: Green

E1 AR Alignment is Green for validation purposes. The gross face-overlay offset recorded in the M5 screen-state review is addressed by adding AR camera pose driving and E1 diagnostics, then rebuilding UnityFramework and reinstalling/running the RN-hosted Unity app on the real iPhone.

Implementation summary:

- `MakeupARValidationSetup` now configures the AR Camera with an Input System `TrackedPoseDriver` using handheld AR device position and rotation bindings.
- `FaceTrackingStatusReporter` now logs E1 alignment diagnostics including orientation, screen size, XROrigin/camera/camera-offset transforms, face trackable state, and mesh vertex/index/UV counts.
- The Unity scene now serializes the Tracked Pose Driver and the reporter references for `XROrigin`, AR Camera, RN bridge, and E1 diagnostics.

Confirmed evidence:

- Unity project configuration completed without C# compile failure: `evidence/logs/e1-unity-configure-2026-06-21.log`.
- UnityFramework export/build/sync succeeded and produced arm64 RN and package framework artifacts with Data: `evidence/logs/m3-repro-unity-export-e1-2026-06-21.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e1-2026-06-21.log`, and `evidence/logs/m3-repro-artifact-verification-e1-2026-06-21.log`.
- RN iOS build/install/launch succeeded on `위승철의 iPhone`: `evidence/logs/e1-build-install-run-2026-06-21.log`.
- Runtime console summary records E1 alignment diagnostics, `SessionTracking`, `User/User` front camera, repeated face trackable updates, camera transform updates, mesh counts, and no observed missing Tracked Pose Driver warning in the E1 stream: `evidence/logs/e1-ar-alignment-runtime-summary-2026-06-21.log`.
- Devicectl wrapper launch log was retained at `evidence/logs/e1-ar-alignment-runtime-2026-06-21.log`.
- User-provided real-device screen recording was copied to `evidence/screen-recordings/e1-ar-alignment-front-turn-mouth-2026-06-21.mp4`.
- Screen recording metadata was captured at `evidence/logs/e1-screen-recording-ffprobe-2026-06-21.log`: 19.04 seconds, 1180x2556 portrait, HEVC, about 59.98 fps, creation time `2026-06-21T11:05:03Z` / `2026-06-21 20:05:03 KST`.
- Representative frame evidence was generated at `evidence/screenshots/e1-ar-alignment-contact-sheet-2026-06-21.jpg`, `evidence/screenshots/e1-ar-alignment-frame-05s-2026-06-21.jpg`, and `evidence/screenshots/e1-ar-alignment-frame-12s-2026-06-21.jpg`.
- The contact sheet shows the diagnostic overlay attached to the visible face rather than displaced up-left, RN event panels showing `face_detected` and `recipe_applied`, opacity/color controls affecting the diagnostic overlay, and face lost/recovered states during the short device flow.
- User confirmed on-device that all intended functions were checked. The 19.04 second recording exceeds the revised 10 second minimum for decision recordings.

Known limitations:

- The E1 recording was originally accepted under the previous 30 second expectation because the user explicitly confirmed all functions. The validation contract was later revised so decision recordings are 10 seconds minimum by default; the retained 19.04 second E1 recording satisfies that revised duration rule.
- The full raw app console stream was not persisted because `devicectl --log-output` retained only wrapper messages. The runtime evidence is therefore preserved as a summary from the observed console stream, and future captures should use shell stream capture such as `2>&1 | tee`.
- The current visual output is still a diagnostic whole-face/marker overlay. It is not E3 `lip`, `cheek`, and `eye` region rendering, and it is not product-quality makeup.
- `Failed to initialize subsystem ARKit-Meshing [error: 1]`, diagnostic `SphereCollider` warnings, and RN warning banners remain non-E1 blockers.
- M7 remains Yellow / skipped by decision / risk accepted; E1 does not promote M7 to Green.

Next boundary decision:

- Historical E1 boundary: E2 Trackable Lifecycle Diagnostics.
- Superseded by the E2 Decision Detail above; the current Next Milestone Boundary is E3 Region Mask.
- Do not start texture rendering, product-quality makeup, AI/backend/admin/payment/community, commercial SDK integration, Android work, or product implementation from this E1 result.

## M8 Final Decision

Status: Yellow

At M8 closeout, foundation integration was technically viable enough to proceed to E1 AR Alignment if the M7 lifecycle risk was accepted. The result was not Green because the formal M7 3-cycle re-entry evidence was skipped, and it was not Red because the core RN + Unity + AR Foundation path had real-device evidence for app execution, Unity embed, ARKit face tracking, and bidirectional RN-Unity communication.

Decision summary:

- RN app execution: Green.
- Unity ARKit face tracking: Green.
- UnityFramework generation and RN embed: Green.
- RN -> Unity communication: Green.
- Unity -> RN communication: Green.
- Re-entry stability: Yellow / skipped by decision / risk accepted.
- Foundation integration readiness: Yellow overall, with the core integration path Green and M7 lifecycle proof carried as an accepted risk.
- AR visual makeup readiness at M8 closeout: Not Green. The then-current face overlay was diagnostic and visibly offset; E1 was required to prove camera/feed/face mesh alignment.
- Product-quality makeup rendering: Not started. Do not treat the current overlay as lip, cheek, eye, or product-quality rendering.

M8 decision gate at that time:

- If the accepted M7 risk was still acceptable, the next milestone boundary was E1 AR Alignment.
- If lifecycle confidence was required before renderer work, the next milestone boundary was additional M7 re-entry verification.
- Do not start region masks, texture rendering, product makeup quality, AI/backend/admin/payment/community, commercial SDK integration, Android work, or product implementation from this M8 report.

## Readiness Breakdown

| Area | Status | M8 interpretation |
| --- | --- | --- |
| RN iOS host app | Green | RN 0.86 app builds, installs, launches, displays on the real iPhone, and remains usable as the host shell. |
| Unity ARKit face tracking | Green | Unity/AR Foundation/ARKit reaches `SessionTracking`, front camera, active face tracking, and diagnostic face overlay evidence. |
| UnityFramework generation/embed | Green | `UnityFramework.framework` arm64 build, Data placement, RN reference/package sync, and RN-hosted Unity screen are proven. |
| RN -> Unity recipe path | Green | RN color/opacity controls send JSON to `RNBridge.ApplyRecipeJson`; Unity logs and applies color/opacity to the diagnostic overlay. |
| Unity -> RN event path | Green | RN visibly receives and displays `unity_initialized`, `face_detected tracked=true/false`, and `recipe_applied`. |
| Re-entry lifecycle | Yellow / risk accepted | User confirmed app execution and normal Close/exit behavior, but formal 3-cycle M7 evidence was intentionally skipped. |
| Clean rebuild/reinstall durability | Yellow caveat | Local success depends on the package framework sync and the `node_modules` `RNUnityView.mm` timing patch until made durable. |
| Face-fitted AR visual alignment | M8: Not Green / E1 required | At M8 closeout, the diagnostic overlay was offset from the face. The later E1 section above records the alignment fix and evidence. |
| Region renderer | Not started | `lip`, `cheek`, and `eye` independent region control remains E3 scope. |
| Product-quality makeup rendering | Not started / Not ready | No product-quality makeup, texture, shade fidelity, feathering, or blend-mode validation has begun. |
| AI readiness | Green | E5 no-inference snapshot creation, Unity -> RN send, and RN-visible status screenshot are proven; the separate decision recording was explicitly waived by the user. This is not AI model/backend/product inference. |

## Green / Yellow / Red Basis

Green basis:

- Real iPhone evidence proves RN app execution, Unity ARKit face tracking, UnityFramework embed, RN -> Unity recipe delivery, and Unity -> RN event delivery.
- M0-M6 have concrete command/log/screenshot/screen-recording evidence recorded below.

Yellow basis:

- M7 formal 3-cycle re-entry validation was skipped by decision; this is a lifecycle confidence gap, not a Green proof.
- Clean reinstall/reclone durability still has local caveats around framework sync and the `RNUnityView.mm` timing patch.
- At M8 closeout, the visual overlay was not face-fitted, so visual makeup readiness was intentionally separated from foundation integration readiness. The later E1 section above supersedes only the diagnostic alignment gap, not region rendering or product makeup quality.

Red basis:

- No current Red foundation blocker is recorded. The known gaps are validation/visual-rendering risks rather than proof that the RN + Unity + AR Foundation path cannot work.

## M6 Decision Detail

Status: Green

M6 remains Green.

M6 implementation is present:

- Unity sends JSON events through the existing native `sendMessageToMobileApp(string message)` path.
- Unity sends `{"type":"unity_initialized"}` from `RNBridge.Start()`.
- Unity sends `{"type":"face_detected","tracked":true|false,"faceCount":...}` from `FaceTrackingStatusReporter`.
- Unity sends `{"type":"recipe_applied","layer":"lip","color":"...","opacity":...}` after `RNBridge.ApplyRecipeJson(string)`.
- RN connects `UnityView.onUnityMessage`, parses `event.nativeEvent.message` as JSON, logs receipt attempts, and displays the latest event, last event by required type, plus recent history on screen.
- Existing RN -> Unity color/opacity controls still call `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)`.

Confirmed evidence:

- M6 UnityFramework regeneration succeeded and produced a synced framework for the RN app package path.
- Real-device build/install/launch succeeded on `위승철의 iPhone`.
- Real-device runtime logs show Unity sending `unity_initialized`, `face_detected tracked=false faceCount=0`, `face_detected tracked=true faceCount=1`, and many `recipe_applied` events.
- A follow-up M6 face-state fix build also succeeded, installed, and launched on `위승철의 iPhone`.
- The follow-up runtime log confirms the Unity-side face lost/recovered state now uses active AR tracking state, not stale trackable object count: after a visible tracked face, Unity sends `face_detected tracked=false faceCount=0 totalTrackables=1 trackingStates=...:None`, then sends recovered `tracked=true faceCount=1 trackingStates=...:Tracking`.
- User-provided real iPhone screen recording shows the RN host app displaying the `Latest Unity Event` panel and receiving/displaying `recipe_applied layer=lip color=... opacity=...` after color/opacity changes.
- User-provided post-fix real iPhone screenshots show the RN host app displaying `unity_initialized`, `face_detected tracked=true faceCount=1`, `face_detected tracked=false faceCount=0 total=1 states=...:None`, and `recipe_applied layer=lip color=#E67B5F opacity=0.5` in the RN event panel.

M6 is Green because the current evidence proves the required Unity -> RN status events are sent by Unity and displayed on the real iPhone RN host screen:

- `unity_initialized` is visible in the RN `Last by type` panel.
- `face_detected tracked=true faceCount=1` is visible in the RN event panel/history.
- `face_detected tracked=false faceCount=0` is visible as the RN `Latest Unity Event` after the face leaves view.
- `recipe_applied layer=lip color=#E67B5F opacity=0.5` is visible in the RN event panel.
- Existing RN -> Unity color/opacity controls still work on the same screen.

Known limitations:

- RN JS `console.log('[M6] rn_unity_message_received', ...)` did not appear in the captured Metro/device console logs. RN receipt is instead proven by real-device RN screen evidence showing parsed Unity event state and history.
- The user-provided earlier recording remains valid evidence for RN receipt/display of `recipe_applied`; the later screenshots close the missing init/face acquired/face lost display gap.
- The M4 local `RNUnityView.mm` timing patch under `node_modules` is still required for this local run so Unity initializes from `didMoveToWindow` after the RN view has a real window/bounds. Make this durable before clean reinstall/reclone workflows.
- Unity logs still include `Failed to initialize subsystem ARKit-Meshing [error: 1]` and `Can't add component because class 'SphereCollider' doesn't exist!` from earlier diagnostic paths. These are outside M6 unless they block Unity -> RN event proof.
- The previous first-face-only / reacquisition observation is narrowed for M6: the ARFace trackable object can persist, but the fixed M6 state now reports active `trackingState` so face lost/recovered no longer depends on trackable removal.

Previous M5 remains Green. M6 is complete. M7 is not marked Green because the formal 3-cycle re-entry evidence was skipped.

## M7 Time-box Decision

Status: Yellow / skipped by decision

M7 formal validation was stopped before the required 3-cycle `Start AR -> face tracking -> color/opacity change -> Close -> Home -> re-enter` loop. The user confirmed the app runs and that normal exit/Close behavior was not problematic, but the official M7 evidence standard was intentionally not collected because the validation session was time-boxed.

Evidence retained from the interrupted M7 pass:

- `evidence/logs/m7-metro-2026-06-21.log`: Metro dev server started for the M7 attempt.
- `evidence/logs/m7-reentry-runtime-2026-06-21.log`: real-device app launch reached Unity AR runtime and logged `unity_initialized`, `face_detected tracked=true/false`, and `recipe_applied` before the test was stopped.
- `evidence/logs/m7-build-install-run-2026-06-21.log`: attempted RN reinstall was aborted by user direction before completion.

Known limitations:

- No 3-cycle re-entry screen recording or screenshot evidence was captured.
- No post-Close camera indicator evidence was captured for the formal M7 run.
- M7 should be treated as a risk-accepted Yellow item, not a Green stability proof.

Practical decision:

- Do not spend additional time on standalone M7 re-entry stress testing in this validation pass.
- If re-entry instability appears later, use the documented fallback candidates from the test plan: avoid Unity unload when possible, compare pause/resume, or keep a full-screen Unity container and hide/show it.

## Current Screen State Review

Review time: 2026-06-20 22:08 KST

Scope: user-provided M5 app execution recording only. No code changes were made during this review. This section records the current visible app state after M5, and separates the M5 communication result from the visual AR makeup readiness result.

Source recording:

- Original user attachment: `/Users/wiseungcheol/Downloads/ScreenRecording_06-20-2026 21-48-38_1.MP4`
- Workspace copy: `/Users/wiseungcheol/Desktop/makeupAR/evidence/screen-recordings/m5-current-screen-state-2026-06-20-214838.mp4`
- Metadata log: `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-current-screen-recording-ffprobe-2026-06-20-214838.log`
- Metadata summary: 44.35 seconds, 1180x2556 portrait video, HEVC, about 59.75 fps, creation time `2026-06-20T12:48:38Z` / `2026-06-20 21:48:38 KST`.

Representative frame evidence:

| Artifact | Path | Observation purpose |
| --- | --- | --- |
| Contact sheet | `evidence/screenshots/m5-current-screen-state-contact-sheet-2026-06-20-214838.jpg` | Full 44.35 second flow at about 2 second intervals |
| 12s frame | `evidence/screenshots/m5-current-screen-state-12s-face-tracking-offset-2026-06-20.jpg` | AR tracking debug panel is true, but mask is visibly offset from the face |
| 20s frame | `evidence/screenshots/m5-current-screen-state-20s-opacity-offset-2026-06-20.jpg` | Opacity value is high and overlay is visible, but still not face-aligned |
| 28s frame | `evidence/screenshots/m5-current-screen-state-28s-color-offset-2026-06-20.jpg` | Coral color selection is reflected in the overlay, but overlay remains offset |
| 36s frame | `evidence/screenshots/m5-current-screen-state-36s-second-face-no-overlay-2026-06-20.jpg` | Another person's face is visible, but no new mask is attached to that visible face |
| 40s frame | `evidence/screenshots/m5-current-screen-state-40s-return-offset-2026-06-20.jpg` | Returning to the first face still shows the overlay displaced to the upper-left |

Screen observations:

| Area | Current visible state | Interpretation |
| --- | --- | --- |
| RN launch/home | The recording starts from the iPhone Home screen, opens the RN validation app, and shows `RN to Unity Recipe Validation` with `Start AR`. | M2/M4 host app launch and navigation entry remain usable. |
| Unity startup | After `Start AR`, the Unity splash appears and then the front-camera AR feed appears inside the RN-hosted Unity screen. | M4 Unity embed remains functional in the installed app. |
| RN overlay controls | The Unity screen shows `Close`, a debug text panel, `rose`, `coral`, `nude` controls, an opacity slider, and the RN warning banner `Open debugger to view warnings.` | The M5 test UI is visible. The warning banner is not an AR failure by itself, but it obscures part of the bottom UI and should be cleared or investigated before polished UX testing. |
| AR tracking status | The Unity debug panel shows `AR support state: SessionTracking`, `Camera requested/current: User/User`, `Tracked face count: 1`, and `Face detected: true` in the captured frames. | ARKit face tracking is active according to runtime debug state. This does not prove visual alignment. |
| Color changes | The overlay changes color when color controls are used, including rose/coral-like visible states. Runtime logs also record `recipe_applied` for `#D94B74`, `#B9826B`, and `#E67B5F`. | RN -> Unity message delivery and Unity-side material color application are working for the M5 contract. |
| Opacity changes | The opacity label and slider change, and the overlay visibly changes opacity in some parts of the recording. Runtime logs record opacity values across the expected range. | RN -> Unity opacity delivery is working, but small step changes can be hard to perceive visually, especially when the overlay is off-face or partly off-screen. |
| Face overlay alignment | The large colored mask is consistently displaced from the visible face, usually above and/or to the upper-left. At 12s the mouth cutout appears over the forehead/hair region rather than the mouth. At 20s and 28s the overlay is still not fitted to the eyes, mouth, jaw, or face contour. | Current visual state is not face-fitted makeup. It is diagnostic overlay rendering with a serious alignment problem. |
| Head/face movement response | The overlay appears to move or deform with tracked face changes, and the user-observed eye/mouth openings can change the mask shape. | The app is receiving AR face pose/mesh-related updates, but the rendered camera/face coordinate alignment is wrong. |
| Second face / face switching | Around the second-person segment, the debug overlay still reports one tracked face, but the visible second face does not receive a new aligned mask. | The earlier first-face-only / reacquisition risk remains real. Current logs count trackables but do not identify added/updated/removed trackable IDs, so the exact failure mode is not yet isolated. |
| Controls with no visible effect | Some control movements can appear to do nothing. In current source, Unity only receives `layer`, `color`, and `opacity`, and only color/opacity are applied to the whole diagnostic face overlay material. | Any UI state that is not represented in the recipe JSON, or any change that targets a visual object outside the overlay material, will not produce a visible Unity change. This is a current implementation limitation, not user error. |

Source and log cross-check:

- AR Foundation and ARKit are present through `com.unity.xr.arfoundation` 6.3.5 and `com.unity.xr.arkit` 6.3.5 in `unity/MakeupARUnityValidation/Packages/manifest.json`.
- ARKit face tracking is enabled in `unity/MakeupARUnityValidation/Assets/XR/Settings/ARKitSettings.asset` with `m_FaceTracking: 1`.
- The Unity scene contains `ARFaceManager`, a face prefab, `RNBridge`, and `AR Camera Manager` in `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity`.
- The scene has `m_MaximumFaceCount: 1`, so multi-face behavior or reliable switching between people is not currently proven.
- The scene's `AR Camera` lists `Camera`, `AudioListener`, `ARCameraManager`, and `ARCameraBackground`, but no Tracked Pose Driver component is serialized in the inspected scene section.
- The final real-device log contains this warning: `Camera "AR Camera" does not use a Tracked Pose Driver (Input System), so its transform will not be updated by an XR device.` This is the strongest current clue for why ARKit tracking can be true while the rendered overlay is offset from the camera feed.
- The final real-device log also contains `UnityARKit: Updating ARSession configuration with <ARFaceTrackingConfiguration ... captureDeviceType=AVCaptureDeviceTypeBuiltInTrueDepthCamera ... framesPerSecond=(60)>`, followed by `SessionTracking`, `Current tracked face count: 1`, and `Face detected: true`.
- The face prefab contains `ARFace`, `MeshFilter`, `MeshRenderer`, `ARFaceMeshVisualizer`, and `FaceTrackingMarker`. This is an ARKit/AR Foundation face mesh diagnostic setup, not a custom per-landmark makeup renderer.
- `RNBridge.ApplyRecipeJson(string)` parses `layer`, `color`, and `opacity`; clamps opacity; and applies the resulting color to the shared overlay material and current `ARFace` trackable renderers.
- Although the RN payload sends `layer: "lip"`, the current Unity implementation does not use that layer to isolate lips. It applies color/opacity to the diagnostic face overlay as a whole.
- `FaceTrackingMarker` creates separate magenta/cyan diagnostic marker materials at runtime. Those marker materials are not driven by the RN recipe color/opacity application path.
- At the 2026-06-20 M5 screen-state review point, the native bridge had a `sendMessageToMobileApp` path but the M5 app did not yet implement Unity -> RN status event handling on the RN screen. The later M6 section above records the completed Unity -> RN result.

Current screen-state decision:

- M5 communication status remains Green: RN sends recipe-like JSON, Unity receives it, and Unity logs/applies color and opacity.
- Current visual AR makeup readiness is Yellow/Fail: the displayed overlay is not aligned to the face and must not be treated as a successful face-fitted makeup implementation.
- Current tracking interpretation: ARKit/AR Foundation face tracking is active, but the current render path is a diagnostic face mesh/marker setup with a camera/pose alignment issue and no per-region makeup segmentation.
- Highest-priority follow-up before product makeup rendering: fix AR camera pose alignment, likely by adding the required Tracked Pose Driver / equivalent AR camera pose setup for the current AR Foundation + Input System stack, then re-test the same recording scenarios.
- M8 diagnostic follow-up, now completed by E2 above: log `ARFaceManager.trackablesChanged` added/updated/removed events with trackable IDs, current face transform, and face mesh vertex count so first-face-only and second-face reacquisition behavior can be separated from visual alignment.
- Product makeup work should not start from the current screen state. First prove a correctly aligned face mesh/landmark basis, then validate E3 region-specific rendering only for `lip`, `cheek`, and `eye`; other face regions remain future product scope.

## M0-M7 Foundation Summary

This table is the M8 single-glance foundation validation summary. M7 remains Yellow and is not promoted to Green.

| Milestone | Decision | Notes |
| --- | --- | --- |
| M0. Environment gate | Green as of 2026-06-20 | macOS 26.5.1, full Xcode 26.5, Node 22.23.0, npm 10.9.8, Watchman 2026.06.15.00, CocoaPods 1.16.2, Unity 6000.3.18f1, and iOS Build Support are available. |
| M1. Unity standalone AR validation | Green | Real iPhone runtime confirmed front camera, ARKit face tracking, visible diagnostic marker/mask, and face-following behavior. |
| M2. React Native standalone iOS validation | Green | RN 0.86.0 standalone iOS app builds, installs, launches, displays on the real iPhone, and relaunches once without crash. |
| M3. UnityFramework generation | Green | Unity iOS export and `UnityFramework.framework` arm64 build succeeded; framework with `Data` is available under the RN project for M4 reference. |
| M4. RN-Unity embed | Green | RN Home opens a full-screen Unity view on the real iPhone; AR camera feed, diagnostic face overlay, and face-detected logs are confirmed. |
| M5. RN -> Unity communication | Green | RN color buttons and opacity slider send JSON to Unity `RNBridge`; real-device logs show repeated `recipe_applied` for color and opacity changes. |
| M6. Unity -> RN communication | Green as of 2026-06-21 | Unity sends required JSON events, including fixed face lost/recovered events based on active `trackingState`; RN visibly displays `unity_initialized`, `face_detected tracked=true/false`, and `recipe_applied` on the real iPhone. |
| M7. Re-entry stability | Yellow / skipped as of 2026-06-21 | Formal 3-cycle re-entry evidence was intentionally skipped due validation time constraints. User confirmed app execution and normal exit behavior were acceptable, but M7 is not a Green stability proof. |

## M8 Known Limitations

- M7 has no formal 3-cycle `Start AR -> Close -> Home -> re-enter` recording, screenshot set, or camera-indicator-after-close evidence.
- The current foundation result proves a viable RN-hosted Unity AR path, but it does not prove product lifecycle robustness under repeated open/close/background/foreground stress.
- The successful local RN-hosted Unity run still depends on the package-local `RNUnityView.mm` timing patch under `node_modules`; this must be made durable before clean reinstall/reclone workflows.
- Generated UnityFramework artifacts must be synced into the package framework path used by `@azesmway/react-native-unity`; stale embedded frameworks previously caused RN -> Unity messages to miss `RNBridge`.
- RN-side JS console receipt logs were not captured for M6, although RN receipt is proven by the real-device RN event panel and screenshots.
- The previous M5 gross visual offset is addressed by E1. Current AR visual output is still a diagnostic whole-face/marker overlay and must not be used as evidence for lip, cheek, eye, texture, or product-quality rendering.
- The current Unity recipe path accepts `layer: "lip"` but does not route to a lip region; it applies color/opacity to the whole diagnostic overlay.
- First-face/reacquisition behavior remains a follow-up diagnostic topic; M6 fixed active tracking state reporting but did not fully validate second-person switching.
- Multi-face UX, product makeup quality, texture samples, AI inference, backend upload, commercial SDK integration, and Android remain outside the completed foundation validation.

## Risk Accepted

- M8 closes with an overall Yellow decision instead of spending more time on standalone M7 re-entry stress testing.
- Proceeding past E1 is acceptable only if the team accepts that M7 lifecycle risk remains open and that E1's 19.04 second recording is evaluated under the revised 10 second decision-recording rule.
- If lifecycle stability becomes a release-critical question before renderer work, run additional M7 verification before continuing renderer validation.
- The current visual evidence is accepted only as E1 diagnostic alignment evidence, not as region-renderer, texture, or product makeup visual readiness.

## M6 Requirement Matrix

| M6 requirement | Current evidence | Status |
| --- | --- | --- |
| Unity uses native send path | `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs` imports and calls `sendMessageToMobileApp(string message)` on iOS | Green |
| Unity sends `unity_initialized` | `evidence/logs/m6-face-state-fix-runtime-2026-06-21.log` line 145 contains `[M6] unity_to_rn_send {"type":"unity_initialized"}`; `evidence/screenshots/m6-rn-face-lost-latest-event-2026-06-21.jpg` shows `unity_initialized: seen 1:07:39 AM` in RN `Last by type` | Green |
| Unity sends face acquired event | `evidence/logs/m6-face-state-fix-runtime-2026-06-21.log` lines 160-165 and later lines such as 611-616 show active tracking and `[M6] unity_to_rn_send {"type":"face_detected","tracked":true,"faceCount":1,"totalTrackables":1,"trackingStates":"...:Tracking"}`; `evidence/screenshots/m6-rn-face-tracked-recipe-event-2026-06-21.jpg` shows RN `face_detected: tracked=true faceCount=1 total=1 states=...:Tracking` | Green |
| Unity sends face lost event | `evidence/logs/m6-face-state-fix-runtime-2026-06-21.log` lines 200-205, 299-304, 400-405, and later transitions show `[M6] unity_to_rn_send {"type":"face_detected","tracked":false,"faceCount":0,"totalTrackables":1,"trackingStates":"...:None"}` after a visible tracked face; `evidence/screenshots/m6-rn-face-lost-latest-event-2026-06-21.jpg` shows RN `Latest Unity Event` as `face_detected tracked=false faceCount=0 total=1 states=...:None` | Green |
| Unity sends recipe applied event | `evidence/logs/m6-face-state-fix-runtime-2026-06-21.log` lines 256-260 and 285-289 contain `[M6] unity_to_rn_send {"type":"recipe_applied","layer":"lip",...}` for color changes | Green |
| RN connects `onUnityMessage` | `rn/MakeupARValidation/App.tsx` connects `UnityView` `onUnityMessage={handleUnityMessage}` and parses `event.nativeEvent.message` as JSON | Green |
| RN displays latest event, type status, and history | User-provided screen recording copied to `evidence/screen-recordings/m6-unity-to-rn-events-2026-06-21.mp4`; post-fix screenshots `evidence/screenshots/m6-rn-face-lost-latest-event-2026-06-21.jpg` and `evidence/screenshots/m6-rn-face-tracked-recipe-event-2026-06-21.jpg` show `Latest Unity Event`, `Last by type`, and history displaying init, face acquired, face lost, and recipe events | Green |
| Existing RN -> Unity controls still work | Real-device screen recording shows color buttons and opacity slider active while Unity logs continue `[M5] recipe_applied` and `[M6] unity_to_rn_send recipe_applied` | Green |
| Runtime log contains Unity send and RN receipt | Runtime logs contain Unity send entries. RN JS console receipt line was not captured in Metro/device logs, but RN receipt is proven by real-device RN screen state/history populated from parsed `onUnityMessage` payloads. | Green with logging caveat |

## M5 Requirement Matrix

| M5 requirement | Current evidence | Status |
| --- | --- | --- |
| RN has three color controls | `rn/MakeupARValidation/App.tsx` defines `rose #D94B74`, `coral #E67B5F`, and `nude #B9826B` controls on the Unity screen | Green |
| RN has opacity slider | `rn/MakeupARValidation/App.tsx` implements an opacity slider with `0` to `1` values rounded to `0.05` steps | Green |
| RN calls Unity postMessage contract | `rn/MakeupARValidation/App.tsx` calls `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)` on initial mount and value changes | Green |
| Unity scene has `RNBridge` receiver | `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity` contains an active `RNBridge` GameObject; `RNBridge.cs` exposes public `ApplyRecipeJson(string json)` | Green |
| Unity parses recipe JSON | `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs` parses `layer`, `color`, and `opacity`, validates HTML colors, clamps opacity, and logs parse failures with the raw string | Green |
| Unity applies color/opacity to overlay | `RNBridge.cs` applies the resulting color to the overlay material and current AR face trackable renderers, including transparent material settings | Green |
| Generated UnityFramework contains M5 scene object | `evidence/logs/m3-repro-artifact-verification-m5-rnbridge-status-object-2026-06-20-213631.log` records a successful arm64 UnityFramework build; `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework/Data/level0` contains `RNBridge` | Green |
| Installed iPhone app embeds M5 framework | `evidence/logs/m5-installed-app-framework-verification-2026-06-20-214651.log` records the installed app's `UnityFramework.framework/Data/level0` containing `RNBridge` | Green |
| Real iPhone build/install/launch succeeds | `evidence/logs/m5-run-ios-device-rnbridge-package-sync-2026-06-20-214557.log` records successful build, install, and launch for `com.makeupar.rnvalidation` on `위승철의 iPhone` | Green |
| Runtime receives and applies recipe changes | `evidence/logs/m5-devicectl-launch-console-rnbridge-package-sync-2026-06-20-214651.log` records repeated `[M5] recipe_applied` entries for `#D94B74`, `#B9826B`, `#E67B5F`, and opacity values from `0.65` down to `0.05` while AR face tracking is active | Green |
| Earlier failure mode identified | `evidence/logs/m5-devicectl-launch-console-rnbridge-status-object-2026-06-20-214338.log` records `SendMessage: object RNBridge not found!`; the final installed-app verification shows this was caused by a stale embedded package framework | Green |

## M4 Requirement Matrix

| M4 requirement | Current evidence | Status |
| --- | --- | --- |
| M3 artifact exists for RN | `evidence/logs/m3-repro-artifact-verification-2026-06-20-203023.log` records arm64 `UnityFramework.framework`, `Data`, `UnitySubsystems/UnityARKit`, and `Headers/NativeCallProxy.h` under the RN project | Green |
| Unity bridge package installed | `rn/MakeupARValidation/package.json` uses `@azesmway/react-native-unity` `^1.0.11`; `evidence/logs/m4-npm-install-react-native-unity-2026-06-20-202741.log` records successful npm install | Green |
| iOS pods reinstalled | `evidence/logs/m4-pod-install-2026-06-20-203559.log` records autolinking `react-native-unity`, generated codegen artifacts, and `Pod installation complete! There are 78 dependencies from the Podfile and 77 total pods installed.` | Green |
| RN Home has `Start AR` and validation status text | `evidence/screenshots/m4-home-start-ar-visible-2026-06-20.jpg` shows the M4 Home screen with status copy and `Start AR` | Green |
| `Start AR` opens Unity screen | `evidence/screenshots/m4-unity-ar-camera-feed-face-detected-2026-06-20.jpg` shows the RN-hosted Unity AR view after tapping `Start AR` | Green |
| Unity screen is full-screen with `Close` and debug text | The same screenshot shows camera feed filling the screen, a `Close` control, and the Unity debug overlay | Green |
| Unity camera feed or scene is visible | The same screenshot shows the front-camera feed and bright magenta diagnostic face overlay | Green |
| Close returns to RN Home | User-provided screenshots for this validation include both the Unity screen and the RN Home screen; no crash was observed during the screen transition flow | Green |
| Real iPhone build/install/launch succeeds | `evidence/logs/m4-run-ios-device-instrumented-didmove-2026-06-20.log` records successful build, install, and launch for `com.makeupar.rnvalidation` on `위승철의 iPhone` | Green |
| RN-hosted Unity runtime reaches AR tracking | `evidence/logs/m4-devicectl-launch-console-instrumented-didmove-2026-06-20.log` records UnityFramework loading, `runEmbeddedWithArgc`, `UnityARKit: Updating ARSession configuration`, `Camera requested/current: User/User`, `SessionTracking`, `Current tracked face count: 1`, and `Face detected: true` | Green |

## M3 Requirement Matrix

| M3 requirement | Current evidence | Status |
| --- | --- | --- |
| Unity project confirmed for iOS target/export | `evidence/logs/m3-unity-export-2026-06-20.log` contains `[M1] Unity iOS export result: Succeeded at /Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export`; Unity project uses `com.unity.xr.arfoundation` 6.3.5 and `com.unity.xr.arkit` 6.3.5 | Green |
| Exported Xcode project includes UnityFramework target | `unity-builds/ios-export/Unity-iPhone.xcodeproj/project.pbxproj` contains the `UnityFramework` native target and scheme; `scripts/build_m3_unityframework.sh` verifies required ARKit entries before building | Green |
| `UnityFramework.framework` builds | `evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-20-201720.log` contains `** BUILD SUCCEEDED **` | Green |
| Framework binary is iPhone arm64 | `evidence/logs/m3-repro-artifact-verification-2026-06-20-201720.log` records `Mach-O 64-bit dynamically linked shared library arm64` for the RN copy | Green |
| Unity Data is inside framework | `evidence/logs/m3-repro-artifact-verification-2026-06-20-201720.log` records `UnityFramework.framework/Data`, size `9.2M`, including `boot.config`, `globalgamemanagers`, `level0`, and `UnitySubsystems/UnityARKit` | Green |
| RN reference path exists for M4 | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework` exists and is verified in `evidence/logs/m3-repro-artifact-verification-2026-06-20-201720.log` | Green |
| RN embed/messaging stayed out of scope | No RN screen/navigation, package install, bridge code, or messaging changes were made in M3 | Green |

## M2 Requirement Matrix

| M2 requirement | Current evidence | Status |
| --- | --- | --- |
| Bare React Native project created | `rn/MakeupARValidation/package.json` uses `react-native` `0.86.0`; init log shows `Welcome to React Native 0.86.0` | Green |
| iOS dependencies installed | `evidence/logs/m2-pod-install-retry-2026-06-20.log` contains `Pod installation complete! There are 77 dependencies from the Podfile and 76 total pods installed.` | Green |
| Xcode signing/provisioning confirmed | Xcode managed profile was created for `com.makeupar.rnvalidation`; signed build/install succeeded on the physical iPhone. Team ID is not retained in the project file. | Green |
| Real iPhone build succeeds | `evidence/logs/m2-xcodebuild-after-gui-signing-2026-06-20.log` contains `** BUILD SUCCEEDED **` | Green |
| Real iPhone install and launch succeeds | `evidence/logs/m2-run-ios-after-gui-signing-2026-06-20.log` contains `success Installed the app on the device`, `bundleID: com.makeupar.rnvalidation`, and `success Successfully launched the app` | Green |
| Metro/JS bundle loads | Physical-device build log contains Metro bundle generation and Hermes compilation; user confirmed the RN app was visible on the iPhone | Green |
| Relaunch has no crash | `evidence/logs/m2-relaunch-2026-06-20.log` contains `Launched application with com.makeupar.rnvalidation bundle identifier.` after `--terminate-existing` | Green |

## M1 Requirement Matrix

| M1 requirement | Current evidence | Status |
| --- | --- | --- |
| Unity standalone iOS app runs on real iPhone | User confirmed the app is installed/running on the iPhone and provided live screenshots | Green |
| Front/user-facing camera works | User confirmed front camera; screenshots show front-camera feed and debug panel `Camera requested/current: User/User` | Green |
| Camera direction appears in debug/logs | User-provided Xcode logs include `Camera requested/current: User/User`; screenshots show the same in the debug panel | Green |
| Face tracking support works | User-provided Xcode logs show `SessionTracking`, `XRFaceSubsystem loaded`, `running=True`, `Current tracked face count: 1`, `Face detected: true` | Green |
| Visible face-following overlay exists | Screenshots show a bright magenta diagnostic mask/marker over the camera feed | Green |
| Overlay follows the face | User confirmed the cross/marker is visible, the mask follows head movement, and disappears when the face leaves the view | Green |
| Unity iOS export succeeds | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m1-front-camera-overlay-export-2026-06-20.log` contains `[M1] Unity iOS export result: Succeeded at /Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export` | Green |

## Environment / Device Snapshot

| Item | Result | Status |
| --- | --- | --- |
| macOS | 26.5.1, build 25F80 | Checked |
| Xcode | Xcode 26.5, build 17F42 | Checked |
| Unity | 6000.3.18f1 | Checked |
| Unity iOS Build Support | `/Applications/Unity/Hub/Editor/6000.3.18f1/PlaybackEngines/iOSSupport` exists | Checked |
| Node | `v22.23.0` | Checked |
| npm | `10.9.8` | Checked |
| Watchman | `2026.06.15.00` | Checked |
| CocoaPods | `1.16.2` | Checked |
| iPhone via `devicectl` | `위승철의 iPhone`, identifier `6F504EE9-BABC-5F6F-A186-C734E04CA625`, state `connected`, model `iPhone 16 (iPhone17,3)` | Checked |
| Exported Xcode project | Generated during M1 under ignored `unity-builds/ios-export/`; generated artifact is not retained in the cleaned repo | Reproducible |
| Real-device runtime | User confirmed the regenerated app runs and produced screenshots/logs | Checked |
| React Native | `0.86.0` | Checked |
| RN app path | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation` | Checked |
| RN iOS bundle id | `com.makeupar.rnvalidation` | Checked |
| M3 UnityFramework artifact | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework` | Checked |
| M3 UnityFramework Data | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework/Data` | Checked |
| M3 reproducible build runbook | `/Users/wiseungcheol/Desktop/makeupAR/docs/runbooks/M3_UNITYFRAMEWORK_REPRO_BUILD_RUNBOOK.md` | Checked |

## Current React Native Project State

| Item | Result |
| --- | --- |
| RN project path | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation` |
| React Native version | `0.86.0` |
| iOS workspace | `rn/MakeupARValidation/ios/MakeupARValidation.xcworkspace` |
| iOS bundle identifier | `com.makeupar.rnvalidation` |
| Signing storage policy | Apple Development Team ID is not stored in `MakeupARValidation.xcodeproj/project.pbxproj`; M5 CLI signing used temporary extra params and redacted logs |
| Unity integration | RN embeds Unity through `@azesmway/react-native-unity`; the iOS app copies the package framework under `node_modules/@azesmway/react-native-unity/ios/UnityFramework.framework` |
| RN-Unity bridge package | `@azesmway/react-native-unity` 1.0.11 installed and autolinked through CocoaPods |
| M6 screens | `App.tsx` contains the minimal Home screen and full-screen Unity screen with RN -> Unity controls plus the M6 `Latest Unity Event`, `Last by type`, and recent Unity event history panels |
| M5 Home controls | Home shows validation status text and `Start AR` |
| M6 Unity controls | Unity screen shows full-screen `UnityView`, `Close`, debug text, rose/coral/nude color buttons, an opacity slider, and Unity -> RN event display |
| Camera permission | `NSCameraUsageDescription` is present in the RN iOS app Info.plist |
| M6 generated reference artifact | `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework` |
| M6 installed package artifact | `rn/MakeupARValidation/node_modules/@azesmway/react-native-unity/ios/UnityFramework.framework` is synced from the generated reference artifact for local iPhone builds |
| M4 bridge initialization caveat | The successful local run still includes a package-local `RNUnityView.mm` timing patch in `node_modules` so Unity initializes after `didMoveToWindow` with a real window/bounds |

## Current Unity Project State

| Item | Result |
| --- | --- |
| Unity project path | `/Users/wiseungcheol/Desktop/makeupAR/unity/MakeupARUnityValidation` |
| AR Foundation version | `com.unity.xr.arfoundation` 6.3.5 |
| Apple ARKit XR Plug-in version | `com.unity.xr.arkit` 6.3.5 |
| XR Plug-in Management version | `com.unity.xr.management` 4.5.4 |
| ARKit face tracking | `Assets/XR/Settings/ARKitSettings.asset` has face tracking enabled |
| AR scene | `Assets/Scenes/MakeupARFaceValidation.unity` |
| Required scene objects | `AR Session`, `XR Origin`, `AR Camera`, `AR Camera Manager`, `AR Face Manager`, and `RNBridge` are present |
| Face prefab | `Assets/Prefabs/ValidationFaceOverlay.prefab` contains `ARFace`, `MeshFilter`, `MeshRenderer`, `ARFaceMeshVisualizer`, and `FaceTrackingMarker` |
| Face mesh material | `Assets/Materials/ValidationFaceOverlay.mat` uses bright magenta with alpha `0.65` |
| Runtime debug script | `Assets/Scripts/FaceTrackingStatusReporter.cs` logs AR state, camera requested/current direction, face subsystem support, face count, `Face detected: true/false`, and sends M6 face status events to RN |
| M6 RN bridge | `Assets/Scripts/RNBridge.cs` parses RN recipe JSON, applies color/opacity to the diagnostic face overlay material, and sends M6 JSON events to RN through `sendMessageToMobileApp` |
| Diagnostic marker script | `Assets/Scripts/FaceTrackingMarker.cs` creates a magenta face-center sphere and cyan crosshair bars under the tracked face prefab |
| iOS bridge proxy | `Assets/Plugins/iOS/NativeCallProxy.h` and `Assets/Plugins/iOS/NativeCallProxy.mm` were added so the RN Unity bridge can compile against the generated UnityFramework |
| M3 exported Xcode project | `/Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export` |
| M3 generated framework source product | `/Users/wiseungcheol/Desktop/makeupAR/evidence/derived-data/m3-unityframework-repro-2026-06-20-201720/Build/Products/Release-iphoneos/UnityFramework.framework` |

## Evidence

Key evidence paths:

- E7.2 Baseline Instrumentation: `evidence/logs/m3-repro-unity-export-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-baseline-instrumentation-ack-2026-06-22.log`, `evidence/logs/e7-baseline-rn-ios-run-ack-2026-06-22.log`, `evidence/logs/e7-baseline-runtime-console-ack-2026-06-22.log`, `evidence/logs/e7-baseline-summary-2026-06-22.md`, and `evidence/screenshots/e7-baseline-status-panel-2026-06-22.jpg`. The E7.2 screen recording requirement was explicitly waived by the user for file-size reasons.
- E7.0/E7.1 preflight: `evidence/logs/e7-unity-process-cleanup-2026-06-22.log`, `evidence/logs/m3-repro-unity-export-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-preflight-2026-06-22.log`, `evidence/logs/m3-repro-artifact-verification-e7-preflight-2026-06-22.log`, `evidence/logs/e7-build-install-run-2026-06-22.log`, and `evidence/logs/e7-runtime-event-preflight-2026-06-22.log`.
- E6 Engine Decision: this document's E6 section above synthesizes the existing E1-E5 real-device evidence plus the accepted M7 lifecycle gap. No new runtime artifact was required for E6 because it is a decision milestone rather than a new implementation milestone.
- E5 AI Feature Readiness Snapshot: `evidence/logs/e5-ai-feature-readiness-runtime-2026-06-21.log`, `evidence/logs/e5-build-install-run-2026-06-21.log`, `evidence/screenshots/e5-ai-feature-readiness-rn-status-2026-06-21.jpg`, `evidence/logs/m3-repro-unity-export-e5-ai-feature-readiness-2026-06-21.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e5-ai-feature-readiness-2026-06-21.log`, and `evidence/logs/m3-repro-artifact-verification-e5-ai-feature-readiness-2026-06-21.log`. The planned decision recording was explicitly waived by the user for this E5 decision.
- E4 Texture Sample: `evidence/logs/e4-texture-samples-runtime-2026-06-21.log`, `evidence/screen-recordings/e4-texture-samples-matte-shimmer-blush-2026-06-21.mp4`, and `evidence/screenshots/e4-texture-samples-comparison-2026-06-21.jpg`.
- E3 Region Mask: `evidence/logs/e3-region-mask-layer-dispatch-2026-06-21.log`, `evidence/screen-recordings/e3-region-mask-lip-cheek-eye-2026-06-21.mp4`, and `evidence/screenshots/e3-region-mask-debug-colors-2026-06-21.jpg`.
- M5 RN -> Unity communication: `evidence/logs/m5-devicectl-launch-console-rnbridge-package-sync-2026-06-20-214651.log`, `evidence/screen-recordings/m5-current-screen-state-2026-06-20-214838.mp4`, and sampled offset/alignment screenshots under `evidence/screenshots/m5-current-screen-state-*`.
- M6 Unity -> RN communication: `evidence/logs/m6-face-state-fix-runtime-2026-06-21.log`, `evidence/screen-recordings/m6-unity-to-rn-events-2026-06-21.mp4`, `evidence/screenshots/m6-rn-face-lost-latest-event-2026-06-21.jpg`, and `evidence/screenshots/m6-rn-face-tracked-recipe-event-2026-06-21.jpg`.
- M7 interrupted/risk-accepted evidence: `evidence/logs/m7-reentry-runtime-2026-06-21.log`, `evidence/logs/m7-metro-2026-06-21.log`, and `evidence/logs/m7-build-install-run-2026-06-21.log`.
- Visual readiness limitation evidence: `evidence/screenshots/m5-current-screen-state-12s-face-tracking-offset-2026-06-20.jpg`, `evidence/screenshots/m5-current-screen-state-20s-opacity-offset-2026-06-20.jpg`, `evidence/screenshots/m5-current-screen-state-28s-color-offset-2026-06-20.jpg`, and `evidence/screenshots/m5-current-screen-state-40s-return-offset-2026-06-20.jpg`.

Full evidence index:

| Evidence | Path / content |
| --- | --- |
| E7.2 regenerated UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-e7-baseline-instrumentation-ack-2026-06-22.log` |
| E7.2 regenerated UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-e7-baseline-instrumentation-ack-2026-06-22.log` contains `** BUILD SUCCEEDED **` |
| E7.2 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-e7-baseline-instrumentation-ack-2026-06-22.log` records arm64 RN/package framework verification, `Data`, `NativeCallProxy.h`, and package framework sync |
| E7.2 RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e7-baseline-rn-ios-run-ack-2026-06-22.log` records successful build, install, and launch on `위승철의 iPhone` |
| E7.2 runtime baseline console log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e7-baseline-runtime-console-ack-2026-06-22.log` records `[E7] metric_sample`, `[E7] metric_unavailable`, `memoryMetricAvailable=true`, `thermalEvidenceType=manual-device-heat`, `recipe_latency source=unity_applied`, and `recipe_latency source=rn_ack receivedAtMs=...` |
| E7.2 baseline summary | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e7-baseline-summary-2026-06-22.md` summarizes metric counts, tracking-state FPS/frame-time/memory ranges, RN ack latency, representative-frame evidence, and the E7.2-scoped recording waiver |
| E7.2 representative frame screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/e7-baseline-status-panel-2026-06-22.jpg` is a user-provided `590x1280` JPEG showing the RN E7 Baseline panel with tracking state, FPS/frame-time, memory availability/value, thermal manual-heat field, and latency |
| E7.2 waived decision recording | No `evidence/screen-recordings/e7-*` baseline recording was stored; the user explicitly waived the E7.2 recording artifact for file-size reasons |
| E7.0/E7.1 Unity process cleanup log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e7-unity-process-cleanup-2026-06-22.log` records no active Unity/Hub/Licensing process and no `/tmp/Unity-LicenseClient*` stale file |
| E7.0/E7.1 regenerated UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-e7-preflight-2026-06-22.log` |
| E7.0/E7.1 regenerated UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-e7-preflight-2026-06-22.log` contains `** BUILD SUCCEEDED **` |
| E7.0/E7.1 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-e7-preflight-2026-06-22.log` records arm64 RN/package framework verification, `Data`, `NativeCallProxy.h`, and package framework sync |
| E7.0/E7.1 RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e7-build-install-run-2026-06-22.log` records successful build, install, and launch on `위승철의 iPhone` |
| E7.0/E7.1 runtime event preflight log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e7-runtime-event-preflight-2026-06-22.log` records RN-hosted Unity loading, `unity_initialized`, `face_detected tracked=true faceCount=1`, and `recipe_applied` events |
| E5 regenerated UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-e5-ai-feature-readiness-2026-06-21.log` |
| E5 regenerated UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-e5-ai-feature-readiness-2026-06-21.log` contains `** BUILD SUCCEEDED **` |
| E5 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-e5-ai-feature-readiness-2026-06-21.log` records framework verification and package framework sync |
| E5 RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e5-build-install-run-2026-06-21.log` records successful build, install, and launch on `위승철의 iPhone` |
| E5 runtime snapshot log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e5-ai-feature-readiness-runtime-2026-06-21.log` records `[E5] face_feature_snapshot_created` and `[E5] unity_to_rn_send` entries with `rawCameraFrameStored=false`, `offDeviceUpload=false`, face/tracking state, mesh counts, active regions, and texture samples |
| E5 RN status screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/e5-ai-feature-readiness-rn-status-2026-06-21.jpg` shows RN `FaceFeatureSnapshot` received with schema, tracking, mesh, region/sample, and raw-frame/upload flags |
| E5 waived decision recording | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screen-recordings/e5-ai-feature-readiness-snapshot-2026-06-21.mp4` was not collected; user explicitly waived the recording requirement for this E5 Green decision |
| E4 regenerated UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-e4-texture-samples-2026-06-21.log` |
| E4 regenerated UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-e4-texture-samples-2026-06-21.log` contains `** BUILD SUCCEEDED **` |
| E4 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-e4-texture-samples-2026-06-21.log` records framework verification and package framework sync |
| E4 RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e4-build-install-run-2026-06-21.log` records successful build, install, and launch on `위승철의 iPhone` |
| E4 runtime texture sample log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e4-texture-samples-runtime-2026-06-21.log` records `[E4] recipe_parse`, `[E4] region_dispatch`, `[E4] texture_dispatch`, `[E4] applied_texture`, and `[E4] recipe_applied` for `matte_lip`, `soft_blush`, and `shimmer_eye` |
| E4 screen recording metadata log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e4-screen-recording-ffprobe-2026-06-21.log` records a 20.53 second 1180x2556 portrait recording |
| E4 user screen recording | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screen-recordings/e4-texture-samples-matte-shimmer-blush-2026-06-21.mp4` shows the three texture samples on the real iPhone |
| E4 texture comparison screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/e4-texture-samples-comparison-2026-06-21.jpg` summarizes the RN debug UI and visible texture sample differences from the E4 recording |
| E3 regenerated UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-e3-region-mask-2026-06-21.log` |
| E3 regenerated UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-e3-region-mask-2026-06-21.log` contains `** BUILD SUCCEEDED **` |
| E3 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-e3-region-mask-2026-06-21.log` records framework verification and package framework sync |
| E3 RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e3-build-install-run-2026-06-21.log` records successful build, install, and launch on `위승철의 iPhone` |
| E3 runtime region dispatch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e3-region-mask-layer-dispatch-2026-06-21.log` records `[E3] recipe_parse`, `[E3] region_dispatch`, `[E3] applied_region`, and RN `recipe_applied` events for `lip`, `cheek`, and `eye` |
| E3 screen recording metadata log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/e3-screen-recording-ffprobe-2026-06-21.log` records a 38.25 second 1180x2556 portrait recording |
| E3 user screen recording | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screen-recordings/e3-region-mask-lip-cheek-eye-2026-06-21.mp4` shows lip, cheek, and eye region changes on the real iPhone |
| E3 debug color screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/e3-region-mask-debug-colors-2026-06-21.jpg` summarizes the RN debug UI and region color states from the E3 recording |
| M6 regenerated UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-m6-unity-to-rn-2026-06-21-0030.log` |
| M6 regenerated UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-m6-unity-to-rn-2026-06-21-0030.log` contains `** BUILD SUCCEEDED **` |
| M6 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-m6-unity-to-rn-2026-06-21-0030.log` records framework verification and package framework sync |
| M6 RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m6-build-install-run-2026-06-21.log` records successful build, install, and launch on `위승철의 iPhone` |
| M6 Unity -> RN runtime log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m6-unity-to-rn-runtime-2026-06-21.log` records Unity sending `unity_initialized`, `face_detected`, and `recipe_applied` JSON events |
| M6 face-state fix UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-m6-face-state-fix-2026-06-21-0100.log` |
| M6 face-state fix UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-m6-face-state-fix-2026-06-21-0100.log` contains `** BUILD SUCCEEDED **` |
| M6 face-state fix artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-m6-face-state-fix-2026-06-21-0100.log` records framework verification and package framework sync |
| M6 face-state fix RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m6-face-state-fix-build-install-run-2026-06-21.log` records a successful device build, install, and launch on `위승철의 iPhone` with destination `00008140-000924DE21BB801C` |
| M6 face-state fix Metro log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m6-face-state-fix-metro-2026-06-21.log` records Metro startup; no RN `[M6] rn_unity_message_received` entries were captured |
| M6 face-state fix runtime log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m6-face-state-fix-runtime-2026-06-21.log` records Unity sending `unity_initialized`, `face_detected tracked=true faceCount=1`, `face_detected tracked=false faceCount=0 totalTrackables=1 trackingStates=...:None`, recovered `tracked=true`, and `recipe_applied` events |
| M6 user screen recording | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screen-recordings/m6-unity-to-rn-events-2026-06-21.mp4` shows the RN host app event panel displaying `recipe_applied layer=lip ...` after color/opacity changes |
| M6 post-fix face lost RN screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m6-rn-face-lost-latest-event-2026-06-21.jpg` shows the RN `Latest Unity Event` as `face_detected tracked=false faceCount=0 total=1 states=...:None`, plus `unity_initialized`, `face_detected`, and `recipe_applied` under `Last by type` |
| M6 post-fix face tracked/recipe RN screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m6-rn-face-tracked-recipe-event-2026-06-21.jpg` shows RN displaying `face_detected tracked=true faceCount=1 total=1 states=...:Tracking` and `recipe_applied layer=lip color=#E67B5F opacity=0.5` |
| M6 contact sheet | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m6-unity-to-rn-events-contact-sheet-2026-06-21.jpg` summarizes the 48.30 second screen recording |
| M6 latest-event frame evidence | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m6-rn-latest-event-2026-06-21-04s.jpg`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m6-rn-latest-event-2026-06-21-12s.jpg`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m6-rn-latest-event-2026-06-21-24s.jpg`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m6-rn-latest-event-2026-06-21-36s.jpg`, and `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m6-rn-latest-event-2026-06-21-44s.jpg` show the RN event panel state at sampled timestamps |
| M7 interrupted runtime log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m7-reentry-runtime-2026-06-21.log` records a real-device launch reaching Unity AR runtime with init, face, and recipe events before the formal re-entry loop was skipped |
| M7 Metro log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m7-metro-2026-06-21.log` records Metro startup for the interrupted M7 pass |
| M7 aborted reinstall log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m7-build-install-run-2026-06-21.log` records the user-aborted reinstall attempt |
| M5 Unity configure log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-unity-configure-rnbridge-on-status-object-2026-06-20-213545.log` |
| M5 regenerated UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-m5-rnbridge-status-object-2026-06-20-213631.log` |
| M5 regenerated UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-m5-rnbridge-status-object-2026-06-20-213631.log` contains `** BUILD SUCCEEDED **` |
| M5 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-m5-rnbridge-status-object-2026-06-20-213631.log` records the RN framework path, arm64 binary, `104M` framework size, `9.2M` Data folder, and `NativeCallProxy.h` |
| M5 TypeScript check log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-typescript-check-2026-06-20-214651.log` |
| M5 diff whitespace check log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-git-diff-check-2026-06-20-214651.log` |
| M5 initial stale-framework failure log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-devicectl-launch-console-rnbridge-status-object-2026-06-20-214338.log` records `SendMessage: object RNBridge not found!` while the AR screen and RN controls were visible |
| M5 package-sync RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-run-ios-device-rnbridge-package-sync-2026-06-20-214557.log` records successful build, install, and launch on `위승철의 iPhone` |
| M5 installed app framework verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-installed-app-framework-verification-2026-06-20-214651.log` records the installed app bundle's `UnityFramework.framework/Data/level0` containing `RNBridge` |
| M5 real-device recipe application console log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-devicectl-launch-console-rnbridge-package-sync-2026-06-20-214651.log` records AR `SessionTracking`, `Face detected: true`, and repeated `[M5] recipe_applied` entries for color and opacity changes |
| M5 recipe application summary log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-runtime-recipe-applied-summary-2026-06-20-214651.log` |
| M4 RN Unity bridge npm install log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-npm-install-react-native-unity-2026-06-20-202741.log` |
| M4 regenerated UnityFramework log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-regenerate-unityframework-2026-06-20-203023.log` |
| M4 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-2026-06-20-203023.log` |
| M4 pod install log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-pod-install-2026-06-20-203559.log` |
| M4 TypeScript check retry log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-typescript-check-retry-2026-06-20-203559.log` |
| M4 Jest check log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-jest-2026-06-20-203559.log`; blocked before tests because `@react-native/jest-preset` is missing from the RN template dependency tree |
| M4 successful RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-run-ios-device-instrumented-didmove-2026-06-20.log` |
| M4 RN-hosted Unity console log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-devicectl-launch-console-instrumented-didmove-2026-06-20.log` |
| M4 initial black-screen screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m4-unityview-black-screen-2026-06-20.jpg` |
| M4 initial missing camera-permission screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m4-ios-settings-no-camera-permission-2026-06-20.jpg` |
| M4 Home screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m4-home-start-ar-visible-2026-06-20.jpg` |
| M4 successful AR camera screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m4-unity-ar-camera-feed-face-detected-2026-06-20.jpg` |
| M2 RN init log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-rn-init-2026-06-20.log` |
| M2 bundle install log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-bundle-install-2026-06-20.log` |
| M2 pod install retry log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-pod-install-retry-2026-06-20.log` |
| M2 device list log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-device-list-2026-06-20.log` |
| M2 Xcode build success log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-xcodebuild-after-gui-signing-2026-06-20.log` |
| M2 install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-run-ios-after-gui-signing-2026-06-20.log` |
| M2 relaunch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-relaunch-2026-06-20.log` |
| M2 app visible confirmation | User confirmed the RN app was visible on the iPhone after install/launch |
| M3 Unity export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-unity-export-2026-06-20.log` |
| M3 initial target build failure log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-xcodebuild-unityframework-2026-06-20.log` |
| M3 scheme build failure log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-xcodebuild-unityframework-scheme-2026-06-20.log` |
| M3 ARKit static-lib retry log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-xcodebuild-unityframework-with-arkit-libs-2026-06-20.log` |
| M3 UnityARKit object compile logs | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-compile-unityarkit-object-2026-06-20.log`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-compile-unityarkit-object-retry-2026-06-20.log`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-compile-unityarkit-object-with-interface-2026-06-20.log` |
| M3 successful UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-xcodebuild-unityframework-with-arkit-object-2026-06-20.log` contains `** BUILD SUCCEEDED **` |
| M3 artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-artifact-verification-2026-06-20.log` records the RN framework path, arm64 binary, `104M` framework size, and `9.2M` Data folder |
| M3 reproducible build script | `/Users/wiseungcheol/Desktop/makeupAR/scripts/build_m3_unityframework.sh` verifies generated ARKit native link entries, builds `UnityFramework` with signing disabled, copies Unity `Data`, and places the RN reference artifact |
| M3 reproducible Unity export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-2026-06-20-201720.log` |
| M3 reproducible UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-20-201720.log` contains `** BUILD SUCCEEDED **` |
| M3 reproducible artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-2026-06-20-201720.log` records the RN framework path, arm64 binary, `104M` framework size, `9.2M` Data folder, and `UnitySubsystems/UnityARKit` |
| M1 front-camera/marker export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m1-front-camera-overlay-export-2026-06-20.log` |
| Export success line | `[M1] Unity iOS export result: Succeeded at /Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export` |
| Regenerated Xcode project | Generated during M1; recreate with `docs/runbooks/M1_STANDALONE_AR_RUNBOOK.md` when needed |
| Front camera serialization | `Assets/Scenes/MakeupARFaceValidation.unity` has `ARCameraManager` `m_FacingDirection: 2` |
| Marker prefab inclusion | `Assets/Prefabs/ValidationFaceOverlay.prefab` includes `Assembly-CSharp::FaceTrackingMarker` |
| Screenshot evidence | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m1-front-camera-overlay-2026-06-20-1.png`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m1-front-camera-overlay-2026-06-20-2.png` |
| Runtime log evidence | User-provided Xcode log includes `SessionTracking`, `Camera requested/current: User/User`, `XRFaceSubsystem loaded`, `running=True`, `Current tracked face count: 1`, `Face detected: true` |
| User visual confirmation | Front camera confirmed; cross visible; mask follows head movement; marker disappears when face leaves the view |
| Face switching observation | User observed that after the first detected face, showing another person's face does not create a newly tracked mask |

## Special Observations

- M2 Xcode GUI stale issue record: Xcode's Issue Navigator continued to show the earlier `No such module 'React'` GUI failure after CLI build/install/launch succeeded. This does not block M2 because the same workspace/scheme/device built successfully via `xcodebuild`, and the app installed, launched, displayed, and relaunched on the real iPhone.
- M3 UnityFramework ARKit link check: the reproducible build script now verifies the generated Xcode project includes `UnityARKit.m`, `libUnityARKit.a`, `libUnityARKitFaceTracking.a`, `ARKit.framework`, and `MetalPerformanceShaders.framework` before building. The successful 2026-06-20 20:17 KST run used the generated Xcode project settings without extra PackageCache link overrides.
- M3 Data placement adjustment: generated `Data` is attached to the app target resources by default. `scripts/build_m3_unityframework.sh` copies it into `UnityFramework.framework/Data` after the framework build so M4 has a single referenceable framework artifact.
- M3 generated artifact storage: the RN reference artifact is available locally under `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework`, and `.gitignore` excludes `rn/MakeupARValidation/unity/builds/` so the generated framework is not accidentally source-controlled.
- M4 Unity bridge compile requirement: `@azesmway/react-native-unity` imports `UnityFramework/NativeCallProxy.h`, so the M3 reproducible build script now copies that generated Unity plugin header into `UnityFramework.framework/Headers`. No app-level RN-to-Unity or Unity-to-RN message calls were added or exercised in M4; the native proxy is present only as the package-required compile/link shim.
- M4 initial black screen: the RN view transitioned to the Unity screen but the bridge did not start Unity before a valid window/bounds were available, so iOS Settings initially showed no Camera permission entry and the Unity area stayed black.
- M4 local bridge timing fix: the final successful run used a package-local `RNUnityView.mm` patch that initializes Unity from `didMoveToWindow` once the view has non-zero bounds and a window. This patch is documented as a reproducibility caveat because it lives under ignored `node_modules`.
- M4 real-device result: after the timing fix and fresh install/launch, the RN-hosted Unity screen requested camera access, displayed the front-camera AR feed, showed the magenta diagnostic face overlay, and logged `Face detected: true`.
- M5 stale embedded framework failure: the user-observed symptom was visible AR screen plus visible RN controls, but no color/opacity effect. Logs showed `SendMessage: object RNBridge not found!`.
- M5 framework path correction: the generated reference framework under `rn/MakeupARValidation/unity/builds/ios` contained `RNBridge`, but Xcode embedded the package framework under `node_modules/@azesmway/react-native-unity/ios`. Syncing that package framework fixed message delivery; the build script now performs this sync when `node_modules` is present.
- M5 real-device result: after package framework sync and reinstall, the installed app bundle's `UnityFramework.framework/Data/level0` contained `RNBridge`, and live device logs showed repeated `[M5] recipe_applied` for color and opacity changes while AR face tracking was active.
- M6 Unity send path result: runtime logs show Unity calling the native send path for `unity_initialized`, `face_detected`, and `recipe_applied`.
- M6 face-state fix result: after changing face counting to active `ARFace.trackingState`, the real-device runtime log now shows acquired `tracked=true faceCount=1 trackingStates=...:Tracking`, lost `tracked=false faceCount=0 totalTrackables=1 trackingStates=...:None`, and recovered `tracked=true faceCount=1`.
- M6 RN visible receipt result: the user-provided real-device screen recording and post-fix screenshots show RN displaying `unity_initialized`, `face_detected tracked=true faceCount=1`, `face_detected tracked=false faceCount=0`, and `recipe_applied layer=lip ...` in `Latest Unity Event`, `Last by type`, and history.
- M6 logging caveat: the collected runtime/Metro logs do not include RN-side `[M6] rn_unity_message_received` lines, but RN receipt is proven by the real-device RN event panel populated from parsed `onUnityMessage` payloads.
- First-face/reacquisition note: the previous recording showed an apparent first-face-only risk. The M6 fix confirms a persistent ARFace trackable can move to `TrackingState.None`; M6 now counts only active tracking faces, but different-person reacquisition remains outside this M6 screen-evidence pass.
- M7 time-box decision: formal 3-cycle re-entry validation was skipped by user decision. The user confirmed app launch and normal exit behavior were acceptable, but this is recorded as Yellow/risk accepted rather than Green.
- E3 region mask result: RN now sends canonical `region` recipe layers for `lip`, `cheek`, and `eye`; Unity logs parse/dispatch/applied results and applies nonzero mesh masks for all three. The user confirmed the regions are separated, but the painted ranges are broad, so this is Green for validation dispatch/independence and not product-quality makeup accuracy.
- E4 texture sample result: RN now exposes `matte_lip`, `soft_blush`, and `shimmer_eye` as one validation sample per allowed region; Unity logs parse/region/texture/applied flow for each sample and applies them on nonzero face meshes. This is Green for debug texture-sample validation and not product-quality makeup fidelity.
- E5 snapshot result: Unity now emits a no-inference `face_feature_snapshot` payload with face/tracking state, mesh counts, active regions, applied texture samples, timestamp, and explicit `rawCameraFrameStored=false` / `offDeviceUpload=false` privacy flags. The real-device runtime log proves snapshot creation and Unity -> RN send, and the RN status screenshot proves visible receipt. The separate decision recording was explicitly waived by the user, so E5 is Green.
- E6 decision result: the AR engine direction is Yellow, not Green or Red. Continue with the RN + Unity + ARKit path, but require focused lifecycle, durable integration, renderer-quality, and performance hardening before claiming product-v1 readiness.
- E7.0/E7.1 preflight result: fresh UnityFramework export/build/sync, RN iOS build/install/launch, and the existing RN-hosted Unity `unity_initialized`, `face_detected`, and `recipe_applied` event path were confirmed on the real iPhone. This is Green for preflight only and does not complete full E7.
- E7.2 baseline instrumentation result: runtime metric/thermal/memory/latency logging is implemented and confirmed on the real iPhone. The user-provided representative frame shows the RN-visible E7 Baseline panel. The usual recording requirement was explicitly waived for this E7.2 decision, so E7.2 is Green for baseline instrumentation.

## Next Milestone Boundary

E1 AR Alignment, E2 Trackable Lifecycle Diagnostics, E3 Region Mask, E4 Texture Sample, E5 AI Feature Readiness Snapshot, E6 Engine Decision, E7.0/E7.1 preflight, and E7.2 Baseline Instrumentation are complete. Full E7 visual product-readiness is not complete. M0-M6 remain Green. M7 remains Yellow / skipped by decision / risk accepted.

Next boundary decision:

- Primary path: E7.3 Region Precision sub-spike planning/validation. E7.3 was not started in the E7.2 session.
- Conservative path: run additional M7 re-entry verification if the team wants to replace the accepted M7 Yellow risk with formal 3-cycle lifecycle evidence.
- Renderer path: if the team continues with accepted M7 risk, stay in validation/hardening mode and create the required E7 sub-spike documents before E7.3, E7.4, and E7.6 instead of jumping directly into product renderer claims.

Stop rules:

- Do not mark M7 Green unless a formal 3-cycle re-entry pass with evidence is collected.
- Do not proceed to E7.4 or E7.6 from E7.2 logs alone.
- Do not claim full E7, visual product readiness, or product-v1 readiness from E7.0/E7.1 preflight or E7.2 instrumentation logs alone.
- Do not treat E3 as product-quality makeup accuracy; it only proves validation-level region independence.
- Do not treat E4 as product-quality makeup fidelity; it only proves validation/debug texture sample dispatch and visual distinction.
- Do not treat the E5 recording waiver as a general waiver for future milestones.
- Do not treat E6 Yellow as permission to claim product-v1 readiness.
- Do not start AI model inference, backend upload, recommendation logic, commercial SDK integration, Android work, raw camera frame storage, or product implementation until the plan explicitly reaches those milestones.
