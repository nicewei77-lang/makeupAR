# E7 Performance Evidence Sub Spike Plan

Date: 2026-06-22 KST

Status: Temporary E7 sub-spike plan / no implementation evidence yet

## 1. Purpose and Scope

이 문서는 E7 visual product-readiness spike 안에서 성능 증거를 애매하지 않게 만들기 위한 측정 계약서다.

이 sub spike는 두 구간을 함께 다룬다.

- `E7.2 - Baseline Instrumentation`
- `E7.6 - Performance and Device Evidence Pass`

목적은 현재 E3/E4 debug renderer baseline과 이후 E7 renderer 결과를 같은 단위로 비교할 수 있게 만드는 것이다. 이 문서는 구현 계획과 evidence 기준만 고정한다. 코드 구현, evidence 생성, `TECH_VALIDATION_RESULT.md` 업데이트, product-v1 readiness claim은 이 문서 작성 범위가 아니다.

Non-scope:

- product-v1 readiness claim
- product implementation
- AI inference, AI recommendation, backend upload, admin/payment/community work
- commercial SDK integration
- Android work
- raw camera frame storage
- product-quality makeup rendering claim
- M7 Green promotion

## 2. Current Boundary

현재 authoritative boundary는 `TECH_VALIDATION_RESULT.md`를 따른다.

- E7.0/E7.1 preflight는 Green for preflight only.
- Full E7 visual product-readiness는 incomplete.
- Next Milestone Boundary는 `E7.2 Baseline Instrumentation`.
- M7은 여전히 Yellow / skipped by decision / risk accepted.
- E7.2 이후에도 formal M7 3-cycle re-entry evidence 없이 M7을 Green으로 승격하지 않는다.

E7.2에서는 기존 E3/E4 renderer behavior를 바꾸지 않는다. 먼저 current debug-quality renderer의 face state, region state, sample state, FPS/frame-time, memory/thermal 가능 여부, recipe timing, baseline recording을 확보한다.

## 3. Required Context

E7 performance evidence 작업 전 다음 문서를 읽는다.

1. `AGENTS.md`
2. `TECH_VALIDATION_TEST_PLAN.md`
3. `TECH_VALIDATION_RESULT.md`
4. `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`
5. `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md`
6. `docs/roadmaps/research/AR_ENGINE_RESEARCH_REPORT_KO.md`
7. `docs/roadmaps/research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md`
8. `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_GPT.md`
9. `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_CLAUDE.md`
10. `docs/roadmaps/research/E7_AXIS2_COSMETIC_RENDERING_GPT.md`
11. `docs/roadmaps/research/E7_AXIS2_COSMETIC_RENDERING_CLAUDE.md`

Context interpretation:

- `TECH_VALIDATION_TEST_PLAN.md` keeps the older Yellow threshold that sustained AR performance below 20fps is unacceptable.
- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` requires explicit FPS/frame-time, thermal, memory, and latency evidence before E7 can be Green.
- The active roadmap keeps the validation budget conservative: one active face, three makeup layers or fewer, simple transparent materials first, and no obvious frame drop or thermal issue.
- E7 axis research recommends baseline instrumentation before region/rendering changes, including fps, `trackingState`, blendshape/mesh/UV observability, and jitter-related notes.
- Benchmark/research reports are evidence-design inputs only. They do not authorize commercial SDK adoption, live segmentation, Android expansion, or product implementation.

## 4. Measurement Contract

Every E7 metric log and summary should be tied to a single run identity.

Required run fields:

- `runId`
- `phase`: `baseline` or `performance`
- `timestampMs`
- `deviceName`
- `appBuildLabel`
- `unityFrameworkBuildLabel`
- `rendererMode`: `e3e4-baseline`, `e7-region`, `e7-renderer`, or explicit future value
- `lookId`: use `baseline_debug_mask` during E7.2 if no demo look exists yet
- `region`
- `activeRegions`
- `texture`
- `sample`

Required face/tracking fields:

- `trackingState`
- `faceCount`
- `totalTrackables`
- `activeTrackableState`
- `meshVertexCount`
- `meshIndexCount`
- `meshUvCount`
- `hasStableUv`
- `meshSummary`

Required FPS/frame-time fields:

- `sampleWindowMs`
- `sampleFrameCount`
- `averageFps`
- `averageFrameTimeMs`
- `worstFrameTimeMs`
- `sustainedSub20FpsObserved`

Required memory fields:

- `memoryMetricAvailable`
- `memoryMetricSource`: `UnityEngine.Profiling.Profiler`, `RN/iOS warning`, `manual-unavailable`, or another explicit source
- `allocatedMemoryMb` if available
- `reservedMemoryMb` if available
- `monoUsedMemoryMb` if available
- `memoryWarningObserved`
- `memoryMetricYellowCap`

Required thermal fields:

- `thermalEvidenceType`: `api`, `unity-ios-warning`, `manual-device-heat`, or `unavailable`
- `thermalWarningObserved`
- `manualHeatObservation`: for example `not_concerning`, `warm`, `hot`, or `not_recorded`
- `thermalMetricYellowCap`

Required latency fields:

- RN `sentAtMs`
- Unity `appliedAtMs`
- Unity `appliedFrame`
- RN `receivedAtMs`
- `sendToAckLatencyMs`
- `visualLatencyConfirmedByRecording`
- `visualLatencyObservation`

Fixed log event names:

- `[E7] metric_sample`
- `[E7] recipe_latency`
- `[E7] baseline_state`
- `[E7] metric_unavailable`
- `[E7] performance_summary`

Logging rules:

- Runtime console output used as decision evidence must be captured as a full stream with `tee` or equivalent.
- Per-frame RN bridge traffic is not allowed for metrics. FPS/frame-time sampling should run in Unity and emit a compact summary every 2 seconds while the E7 screen is active.
- Missing metrics must be logged with `[E7] metric_unavailable` and must state whether they cap the result at Yellow.
- Summary-only files are allowed only as summaries; they do not replace the full runtime stream.
- Do not store raw camera frames. Screen recordings, screenshots, and contact sheets are allowed evidence artifacts under the existing evidence rules.

## 5. E7.2 Baseline Procedure

E7.2 establishes the comparison baseline before E7 renderer changes.

Implementation intent:

1. Keep current E3/E4 debug renderer behavior unchanged.
2. Add or plan metric instrumentation around the existing runtime path.
3. Capture current `matte_lip`, `soft_blush`, and `shimmer_eye` behavior before E7.3/E7.4 work.
4. Record enough state to compare later visual improvements against performance cost.

Required baseline runtime evidence:

- Face/tracking state: `trackingState`, `faceCount`, `totalTrackables`, active trackable state.
- Region/sample state: active region, active texture/sample, active renderer mode.
- Mesh/UV state: vertex/index/uv counts and `hasStableUv`.
- FPS/frame-time: measured summary or explicit unavailable note.
- Memory: measured summary or `memoryMetricAvailable=false`.
- Thermal: warning/manual observation/unavailable state.
- Recipe timing: RN send timestamp, Unity applied timestamp or frame, RN receive timestamp.

Required baseline visual evidence:

- A baseline recording of at least 10 seconds.
- The recording must show the current debug-quality renderer before E7 renderer changes.
- The recording should include the existing `matte_lip`, `soft_blush`, and `shimmer_eye` states when practical.
- A representative frame screenshot should be saved from the baseline recording or live run.

Baseline output files:

- `evidence/logs/e7-baseline-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-baseline-summary-YYYY-MM-DD.log`
- `evidence/screen-recordings/e7-baseline-debug-mask-YYYY-MM-DD.mp4`
- `evidence/screenshots/e7-baseline-representative-frame-YYYY-MM-DD.jpg`

E7.2 Green:

- Baseline runtime log includes face state, region state, sample state, FPS/frame-time or explicit metric-unavailable note, and recipe apply timing.
- Baseline recording is at least 10 seconds and shows the current debug-quality renderer.
- Missing metric decisions are explicit and do not hide uncertainty.

E7.2 Yellow:

- Visual baseline is recorded, but one metric is missing and explicitly labeled unavailable.
- Memory or thermal evidence is manual-only or incomplete, but no instability is observed.

E7.2 Red:

- No baseline recording exists.
- No full runtime stream exists.
- Existing E3/E4 behavior regresses before E7 changes.
- Recipe path, face tracking, or RN-hosted Unity event flow fails.

## 6. E7.6 Final Performance Procedure

E7.6 decides whether E7 visual improvements are feasible on the real iPhone without unacceptable frame, thermal, memory, or latency cost.

Default final run procedure:

1. Start from a fresh UnityFramework export/build/sync according to `AGENTS.md`.
2. Build/install/launch the RN iOS app on `위승철의 iPhone`.
3. Capture a full runtime stream with `tee`.
4. Record decision footage. A single clip may cover all looks only if it is long enough to show:
   - baseline or transition from baseline
   - all three demo looks
   - at least one head movement sequence
   - at least one expression sequence
   - lost/recovered if used for the decision
5. Capture or explicitly mark availability for:
   - approximate FPS or frame-time
   - thermal warning or manual device heat observation
   - memory observation or explicit unavailable note
   - recipe send-to-visual-applied latency
6. Save representative screenshots or a contact sheet.

Final performance output files:

- `evidence/logs/e7-performance-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-performance-summary-YYYY-MM-DD.log`
- `evidence/screen-recordings/e7-performance-demo-YYYY-MM-DD.mp4`
- `evidence/screenshots/e7-performance-contact-sheet-YYYY-MM-DD.jpg`

Final summary requirements:

- State measured metrics.
- State unavailable metrics.
- State whether each unavailable metric caps the E7 result at Yellow.
- State the final performance G/Y/R decision per layer: FPS/frame-time, thermal, memory, latency.
- State whether performance evidence is strong enough to support the overall E7 decision.
- State that event latency alone is not enough if the screen recording shows visible lag.

## 7. Evidence Files and Summary Format

Runtime log format should stay grep-friendly. Example shape:

```text
[E7] metric_sample runId=e7-baseline-2026-06-22 phase=baseline timestampMs=1780000000000 rendererMode=e3e4-baseline lookId=baseline_debug_mask region=lip activeRegions=lip,cheek,eye texture=matte_lip sample=matte_lip trackingState=Tracking faceCount=1 totalTrackables=1 meshVertexCount=1220 meshIndexCount=6912 meshUvCount=1220 hasStableUv=true sampleWindowMs=2000 sampleFrameCount=120 averageFps=60.0 averageFrameTimeMs=16.7 worstFrameTimeMs=23.4 sustainedSub20FpsObserved=false memoryMetricAvailable=false memoryMetricYellowCap=true thermalEvidenceType=manual-device-heat thermalWarningObserved=false manualHeatObservation=not_concerning
[E7] recipe_latency runId=e7-baseline-2026-06-22 phase=baseline timestampMs=1780000000100 lookId=baseline_debug_mask region=lip texture=matte_lip sentAtMs=1780000000000 appliedAtMs=1780000000048 appliedFrame=12345 receivedAtMs=1780000000096 sendToAckLatencyMs=96 visualLatencyConfirmedByRecording=false visualLatencyObservation=pending_recording_review
[E7] metric_unavailable runId=e7-baseline-2026-06-22 phase=baseline metric=memory reason=Profiler counter unavailable in current build memoryMetricAvailable=false yellowCap=true
[E7] performance_summary runId=e7-performance-2026-06-22 phase=performance fpsDecision=Green thermalDecision=Yellow memoryDecision=Yellow latencyDecision=Green overallPerformanceDecision=Yellow explicitPerformanceEvidence=true
```

Summary file format:

```text
runId:
phase:
date:
device:
buildEvidence:
runtimeLog:
recording:
screenshotsOrContactSheet:
metricsMeasured:
metricsUnavailable:
yellowCaps:
fpsFrameTimeDecision:
thermalDecision:
memoryDecision:
latencyDecision:
overallPerformanceDecision:
knownLimitations:
nextBoundaryImpact:
```

## 8. Green / Yellow / Red Rules

E7 cannot be Green without explicit performance evidence.

FPS/frame-time:

- Green: average remains at or above 30fps equivalent, no obvious sustained collapse, and no sustained sub-20fps segment.
- Yellow: metrics are partial or mild stutter appears, but interaction remains usable.
- Red: sustained severe stutter, sustained sub-20fps, or frame-time spikes make the demo unreliable.

Thermal:

- Green: no iOS/Unity thermal warning when available; manual heat observation is recorded and not concerning during the decision run.
- Yellow: device becomes warm, thermal API is unavailable, or thermal evidence is manual-only and too short to be confident, but no warning/crash occurs.
- Red: thermal warning, severe heat, crash, black screen, reload, or app instability.

Memory:

- Green: no RN memory warning, crash, black screen, reload, or obvious memory growth during the run.
- Yellow: memory counters are incomplete or unavailable, but no instability is observed.
- Red: memory warning, crash, black screen, reload, or obvious memory growth that threatens the demo.

Latency:

- Green: recipe change is visually reflected within 1 second and the event path is consistent.
- Yellow: reflected within 2 seconds or latency logging is incomplete, but the visual state is not stale.
- Red: more than 2 seconds, inconsistent application, stale visual state, or event ack without visible update.

Overall performance:

- Green only if FPS/frame-time is Green, latency is Green, and thermal/memory are Green or explicitly accepted Yellow limitations for validation only.
- Yellow if one or more metrics are incomplete but the run is stable and the limitation is explicit.
- Red if any layer is Red or if runtime/recording evidence is missing.

## 9. Stop Rules

Stop rule:

- Do not judge E7 visual improvement without E7.2 baseline evidence.
- Do not mark E7 Green without explicit FPS/frame-time, thermal, memory, and latency evidence or explicit documented metric-unavailable decisions.
- Do not continue to E7.6 final performance decision if E7.3/E7.4/E7.5 renderer/look evidence does not exist.
- Do not use event latency alone as proof of visual responsiveness.
- Do not store raw camera frames by default.
- Do not start backend upload, AI inference, AI recommendation, commercial SDK integration, Android work, or product implementation.
- Do not promote M7 to Green from E7 performance evidence.
- Do not update `TECH_VALIDATION_RESULT.md` until real E7 evidence exists.

## 10. Future Implementation Touchpoints

Implementation should stay close to existing paths.

RN recipe send/receive path:

- Attach `sentAtMs`, `lookId`, and stable recipe id fields when RN posts recipe JSON to `RNBridge.ApplyRecipeJson`.
- Log `[E7] recipe_latency` on RN receipt after Unity echoes applied timing.
- Extend the RN status/debug panel with current look, current region, latest FPS/frame-time, and latest recipe latency.

Unity recipe apply/event path:

- Keep `RNBridge.ApplyRecipeJson` as the recipe parse/apply entrypoint.
- Echo `lookId`, active recipe id, Unity applied timestamp, and applied frame in `recipe_applied`.
- Keep existing E3/E4 payload compatibility until E7 recipe v2 is explicitly introduced by the renderer sub spike.

Unity face/tracking status reporter:

- Add a lightweight FPS/frame-time sampler using `Time.unscaledDeltaTime` or equivalent.
- Emit `[E7] metric_sample` every 2 seconds while the E7 screen is active.
- Prefer Unity `UnityEngine.Profiling.Profiler` counters for memory if available.
- Log explicit unavailable metrics with `[E7] metric_unavailable`.

Existing E3/E4 overlay baseline:

- Preserve current E3/E4 renderer behavior during E7.2 baseline capture.
- Use `rendererMode=e3e4-baseline` for baseline logs.
- Do not mix E7 renderer changes into baseline evidence.

## 11. Assumptions

- This file is a temporary root-level E7 sub-spike plan.
- E7.2 is allowed to add instrumentation but not alter current E3/E4 visual behavior.
- FPS/frame-time uses a 2 second Unity-side sample window by default.
- `Time.unscaledDeltaTime` is the default frame timing source.
- Memory uses Unity Profiler counters first. If unavailable, record `memoryMetricAvailable=false` and apply Yellow cap unless explicitly accepted later.
- Thermal evidence may be manual device heat observation if no native/API bridge exists, but manual-only thermal evidence must not support product-readiness overclaim.
- Latency decision separates event ack latency from screen-recording visual confirmation.
- Product quality, commercial color fidelity, raw frame persistence, backend upload, AI inference, Android support, and commercial SDK comparisons remain out of scope.
