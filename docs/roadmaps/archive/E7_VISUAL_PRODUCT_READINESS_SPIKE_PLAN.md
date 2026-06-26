# E7 Visual Product-Readiness Spike Plan

Date: 2026-06-22 KST
Last updated: 2026-06-23 KST

Status: Temporary E7 master plan / E7.0-E7.2 complete / E7.03 smooth-mask validation app cleanup accepted / E7.3 remains Yellow / E7.4 requires a new cosmetic-rendering sub-spike plan or explicit Yellow-risk acceptance

## 0. Purpose

E7 is a validation and hardening spike, not product implementation.

This plan answers:

> Can the current RN + embedded Unity + AR Foundation + ARKit path produce a visually credible `lip`, `cheek`, and `eye` AR makeup demo if we harden region precision, cosmetic rendering, and performance evidence?

E7 must not claim product-v1 readiness. A Green E7 means the renderer path is strong enough to continue product-readiness hardening. It does not close the accepted M7 lifecycle risk, does not prove commercial color fidelity, and does not start AI/backend/product work.

Latest 2026-06-23 note: the current validation app optimization goal is closed by user acceptance with three retained screenshots at `evidence/screenshots/e7-smooth-mask-accepted-2026-06-23/`. User feedback says the makeup is still generally hard to see and the eye boundary is somewhat lacking, while accepting this level for the current step and deferring the remaining visibility/boundary polish to cosmetic expression/modeling. This accepts the simplified smooth-mask validation app state for the next working baseline; it does not make E7.3 Green or start E7.4 cosmetic rendering.

## 1. Required Reading

Default E7 session reading is intentionally narrow:

1. `AGENTS.md`
2. `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`
3. The current E7 section in this plan

Lazy-load only when the current task needs it:

- Contract or evidence rule check: relevant section of `TECH_VALIDATION_TEST_PLAN.md`
- E7.3 region precision: `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_GPT.md` and `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_CLAUDE.md`
- E7.4/E7.5 cosmetic rendering: `docs/roadmaps/research/E7_AXIS2_COSMETIC_RENDERING_GPT.md` and `docs/roadmaps/research/E7_AXIS2_COSMETIC_RENDERING_CLAUDE.md`
- E7.6 performance decision: `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`
- Fallback, SDK, licensing, or architecture comparison: `docs/roadmaps/research/AR_ENGINE_RESEARCH_REPORT_KO.md` and `docs/roadmaps/research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md`

## 2. AGENTS.md Operating Guardrails

This plan is subordinate to `AGENTS.md`, `TECH_VALIDATION_TEST_PLAN.md`, and `TECH_VALIDATION_RESULT.md`. If this plan conflicts with those documents, stop and resolve the mismatch before implementing.

### Scope guardrails

- Treat E7 as pre-product technical validation and hardening, not product implementation.
- Stay inside E7 unless the user explicitly names a different milestone or roadmap edit.
- Keep `TECH_VALIDATION_RESULT.md` > `Next Milestone Boundary` as the source of truth for current milestone state.
- Do not start product implementation, commercial SDK integration, Android work, backend upload, admin/payment/community features, AI inference, AI recommendation, or product-quality makeup rendering.
- AI readiness means schema/evidence handoff only, such as `FaceFeatureSnapshot`. It does not mean model inference, recommendation, raw-frame storage, or server upload.
- Keep E7 limited to `lip`, `cheek`, and `eye` unless the user explicitly expands scope.
- Keep M7 Yellow unless a separate formal 3-cycle re-entry pass is collected and recorded.

### Real-device build loop

Every Unity/RN real-device validation pass for E7 must start from a fresh UnityFramework export/build/sync.

1. Before Unity builds, close Unity and Unity Hub.
2. Ensure no stale Unity or Unity Licensing processes remain.
3. If licensing blocks the export, remove `/tmp/Unity-LicenseClient*`, reopen Hub/Editor to confirm the Personal license, then rerun the build script.
4. From the repo root, run:

```bash
bash scripts/build_m3_unityframework.sh
```

5. Do not hand-run raw Unity batchmode commands unless debugging the script itself.
6. Confirm the script exported Unity iOS, verified ARKit links, built `UnityFramework` with signing disabled, copied Unity `Data`, and synced RN/package framework paths.
7. Then run the RN iOS app from `rn/MakeupARValidation`:

```bash
npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK
```

Known build caveats:

- The 2026-06-21 Unity export blocker was stale/conflicting Unity Hub/Editor Licensing Client IPC, not E2 code.
- The blocker signature included `Unsupported protocol version '1.18.1'` and lost client connection.
- Keep the durable `RNUnityView.mm` timing patch hooks in RN `postinstall` and the iOS Podfile.
- Stale package frameworks previously caused missing Unity objects/events, so framework sync evidence matters.

### Document and evidence rules

- Keep `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` and any `E7_*_SUBSPIKE_PLAN.md` files temporary.
- After an E7 session completes, absorb the final result into `TECH_VALIDATION_RESULT.md` and delete temporary E7 plan files unless the user asks to keep them.
- Do not update `TECH_VALIDATION_TEST_PLAN.md` for progress/status unless correcting the stable validation contract itself.
- Put reusable procedures in `docs/runbooks/`.
- Keep roadmap/research docs under `docs/roadmaps/`.
- Store evidence under:
  - `evidence/logs/`
  - `evidence/screenshots/`
  - `evidence/screen-recordings/`
- Do not save screen recordings by default.
- Save recordings only when motion, elapsed time, or a continuous scenario is core evidence.
- When a recording is captured, keep metadata/contact sheets/representative frames for long-term evidence and delete the raw recording when it is no longer needed.
- When runtime console output is decision evidence, capture the full stream to `evidence/logs/` with `tee` or an equivalent method.
- Summary-only logs must be labeled as summaries.
- Store feature snapshot examples as logs or runbook-linked text artifacts.
- Do not store raw camera frames by default.
- Do not commit generated/cache state:
  - `unity-builds/`
  - Unity `Library/`
  - Unity `Logs/`
  - Unity `UserSettings/`
  - Xcode derived data
  - `evidence/`
  - `.DS_Store`

## 3. Current Boundary

Authoritative current state comes from `TECH_VALIDATION_RESULT.md`.

- M0-M6: Green.
- M7: Yellow / skipped by decision / risk accepted.
- E1 AR Alignment: Green for validation.
- E2 Trackable Lifecycle Diagnostics: Green.
- E3 Region Mask: Green for validation only; masks are broad debug masks.
- E4 Texture Sample: Green for validation only; samples are procedural/debug quality.
- E5 FaceFeatureSnapshot: Green for no-inference handoff.
- E6 Engine Decision: Yellow.
- E7.0/E7.1 Preflight: Green for preflight only.
- E7.2 Baseline Instrumentation: Green.
- E7.3 Region Precision: Yellow overall / blocked from E7.4. Legacy procedural E7 video review remains `lip` Red, `cheek` Yellow / insufficient E7-candidate sample, and `eye` Red. P8 reference UV runtime sweep improves attachment for all three regions, but current P8 region decisions are `lip` Yellow, `cheek` Yellow, and `eye` Yellow pending silhouette/material cleanup and scenario-specific motion review.
- Full E7 visual product-readiness: incomplete.

E7 continues from this position:

- The current stack is viable enough to continue.
- The problem is not missing face data.
- The problem is product-readiness uncertainty in region precision, cosmetic visual quality, performance, lifecycle caveat, and clean rebuild durability.
- The current primary boundary remains E7.3 Region Precision validation. Do not enter E7.4/E7.5/E7.6 until E7.03 evidence supports Q3 overlay-ready validation for `lip`, `cheek`, and `eye`, or until the team explicitly accepts E7.3 Yellow risk and records that E7.4/E7.5 can be at most Yellow.

## 4. E7 Decision Summary

### Primary decision

Proceed with ARKit `ARFace` mesh/UV as the primary runtime basis.

### E7 thesis

E7 should prove whether the current broad E3/E4 validation renderer can be hardened into a limited but credible visual demo by:

1. Keeping `lip`, `cheek`, and `eye` as the only regions.
2. Replacing or comparing the current broad face-space centroid mask with an authored UV-space mask path.
3. Adding cosmetic-rendering fields beyond `color` and `opacity`.
4. Validating exactly three demo looks.
5. Capturing explicit FPS/frame-time, thermal, memory, and latency evidence.

### Non-decision

E7 does not decide commercial SDK adoption, Android support, AI recommendation, backend upload, product catalog fidelity, or product-v1 readiness.

## 5. Scope

### Must

- Validate only `lip`, `cheek`, and `eye`.
- Keep ARKit / AR Foundation / ARFace as the primary runtime path.
- Preserve E3/E4 baseline behavior for comparison until E7 proves improvement.
- Add or compare an authored UV-space mask approach for region precision.
- Define Green / Yellow / Red separately for `lip`, `cheek`, and `eye`.
- Validate `natural_daily`, `gloss_lip_focus`, and `soft_blush_shimmer_eye`.
- Validate at least these rendering controls:
  - `region`
  - `color`
  - `opacity`
  - `coverage`
  - `feather`
  - `blendMode`
  - `texture`
  - `finish`
- Capture explicit performance evidence:
  - FPS or frame-time
  - thermal/device heat observation
  - memory observation
  - recipe-to-visual latency
- Keep `rawCameraFrameStored=false` / `offDeviceUpload=false` discipline.
- Keep M7 Yellow unless a separate formal 3-cycle M7 pass is collected.

### Should

- Add tracking-state fade/hold/hysteresis for `Tracking`, `Limited`, and temporary lost states.
- Add lightweight smoothing only for derived low-dimensional controls such as face pose, region anchors, and blendshape-driven parameters.
- Add mouth-open scoring for lip.
- Add blink/squint scoring for eye.
- Add wide-feather placement scoring for cheek.
- Prefer one face, three regions, and at most three active makeup layers during E7.
- Keep shader/material work simple and measurable.

### Nice to have

- Side-by-side baseline broad mask vs E7 visual output.
- Simple skin-tone robustness check across 2-3 different skin tones or lighting conditions.
- Gloss highlight movement check for `gloss_lip_focus`.
- Separate `shimmer` and `shimmerColor` controls for the eye demo.
- Contact sheet from representative frames or from a short decision recording when motion/time evidence is required.

### Defer

- MediaPipe live runtime integration.
- Live 2D face parsing / segmentation runtime.
- Commercial SDK integration: Perfect Corp, Banuba, DeepAR, Snap Camera Kit.
- Android / ARCore.
- AI inference, recommendation, makeup transfer, backend upload.
- Raw camera frame storage.
- Foundation shade matching.
- Skin smoothing.
- Relighting.
- True BRDF fitting.
- Lab color matching.
- Product catalog / SKU fidelity.
- Full product-quality makeup claim.

## 6. Sub Spike Planning Strategy

E7 is broad enough that the implementation session should not start every complex area directly from this master plan. Create sub spike markdown documents only for areas with high uncertainty, high implementation branching, or evidence risk. Do not create sub spike docs for simple checklists.

### Strongly recommended sub spike docs

1. `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`
   - Covers `E7.3 - Region Precision Spike`.
   - Create this before implementing region precision work.
   - Reason: region precision is the central dependency for the rest of E7. If `lip`, `cheek`, and `eye` do not stay attached and plausible, cosmetic rendering polish is not meaningful.
   - Must decide:
     - how to keep the current centroid/broad mask as baseline;
     - how to introduce or compare UV-space mask atlas behavior;
     - per-region motion/expression test matrix;
     - mouth-open, blink/squint, smile, and lost/recovered scoring;
     - `lip` / `cheek` / `eye` Green / Yellow / Red thresholds;
     - when MediaPipe or segmentation remains only a future fallback/reference note.

2. `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md`
   - Covers `E7.4 - Cosmetic Rendering Core`.
   - Create this before shader/material/schema implementation.
   - Reason: rendering scope can quickly drift from validation shader to product renderer. The sub spike must lock the minimum pigment/finish model before implementation.
   - Must decide:
     - E7 recipe v2 minimum fields;
     - backward compatibility with E3/E4 payloads;
     - meanings of `coverage`, `feather`, `blendMode`, `finish`, and `texture`;
     - supported E7 blend modes;
     - supported E7 finish presets;
     - whether to isolate E7 renderer in a new component or extend the existing validation overlay;
     - the 3x3 Look Pack sample matrix and final three-look synthesis process;
     - the E7.4 entry gate: Q3 region evidence, or explicit E7.3 Yellow-risk acceptance with result cap;
     - what remains validation-only and what is deferred product rendering.

3. `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`
   - Covers `E7.2 - Baseline Instrumentation` and `E7.6 - Performance and Device Evidence Pass`.
   - Create this before final demo validation or whenever metrics implementation is non-trivial.
   - Reason: performance evidence is easy to make ambiguous if the measurement plan is invented after the visual work.
   - Must decide:
     - FPS/frame-time capture method;
     - thermal evidence method;
     - memory evidence method;
     - recipe send-to-visual-applied latency measurement;
     - whether missing metrics are Yellow or Red;
     - exact evidence file names and summary format.

### Conditional sub spike doc

4. `E7_DEMO_LOOK_RECIPE_SPEC.md`
   - Covers `E7.5 - Demo Look Implementation`.
   - Create only if look JSON values, RN preset selector behavior, or look-by-look QA criteria need to be fixed before implementation.
   - Useful when:
     - RN will expose preset selection;
     - Unity parser will expand to recipe v2;
     - each look's colors, opacity, coverage, finish, blend, shimmer, and gloss values must be stable across sessions;
     - another agent needs to understand why each recipe value was chosen.

### No separate sub spike needed by default

- `E7.0`: checklist only.
- `E7.1`: existing build loop and artifact-sync rules are sufficient.
- `E7.7`: decide after E7.3-E7.6 evidence exists.
- `E7.8`: `TECH_VALIDATION_RESULT.md` handoff rules are sufficient.

Recommended order:

1. `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`
2. `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md`
3. `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`
4. `E7_DEMO_LOOK_RECIPE_SPEC.md` only if needed

## 7. Implementation Milestones

Milestones are ordered by priority. Do not start a later milestone if an earlier P0 milestone is Red.

### E7.0 - Session Preflight and Baseline Contract

Priority: P0

Goal:

- Start the E7 implementation session from a known repo and artifact state.
- Prevent accidental product implementation scope drift.

Implementation actions:

1. Read the required docs from section 1.
2. Confirm current branch and worktree status.
3. Confirm `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` is the active temporary session plan.
4. Confirm no product/backend/AI/commercial SDK/Android work is being started.
5. Confirm whether the implementation session is accepting M7 Yellow risk or first running formal M7.
6. Decide the E7 sub spike document path before complex implementation:
   - create `E7_REGION_PRECISION_SUBSPIKE_PLAN.md` before E7.3 unless the implementation is intentionally limited to a trivial baseline check;
   - create `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` before E7.4 unless no shader/material/schema branching is being attempted;
   - create `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md` before E7.6 unless the measurement method is fully specified in this plan or the result handoff;
   - create `E7_DEMO_LOOK_RECIPE_SPEC.md` only if recipe values or preset behavior need to be fixed before implementation;
   - if a recommended sub spike is skipped, record the reason and the resulting decision-risk cap.

Default:

- Accept current M7 Yellow risk for E7 renderer validation only.
- Do not mark M7 Green.
- Skipping a recommended sub spike is allowed only when the implementation path is simple and the skip reason is explicit.
- Skipping the performance measurement plan does not remove the E7 performance evidence requirement.

Evidence:

- No runtime evidence required for E7.0.
- Note implementation-session start state in the final `TECH_VALIDATION_RESULT.md` update after the E7 run.
- Record which E7 sub spike docs were created, skipped, or deferred.

Stop rule:

- Stop if the implementation request tries to claim product-v1 readiness or starts AI/backend/commercial SDK/Android work.
- Do not start E7.3, E7.4, or E7.6 if the needed sub spike decision is still unclear.

### E7.1 - Build and Runtime Preflight

Priority: P0

Goal:

- Ensure the app used for E7 is built from fresh UnityFramework output and the package-local framework is synced.

Implementation actions:

1. Close Unity/Hub and stale Unity licensing processes before Unity build.
2. Run `bash scripts/build_m3_unityframework.sh` from repo root.
3. Verify the script syncs:
   - `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework`
   - `rn/MakeupARValidation/node_modules/@azesmway/react-native-unity/ios/UnityFramework.framework`
4. Run from `rn/MakeupARValidation`:
   - `npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK`
5. Confirm RN screen can open Unity and receive existing Unity events.

Evidence:

- `evidence/logs/e7-unityframework-export-YYYY-MM-DD.log`
- `evidence/logs/e7-unityframework-build-YYYY-MM-DD.log`
- `evidence/logs/e7-artifact-verification-YYYY-MM-DD.log`
- `evidence/logs/e7-build-install-run-YYYY-MM-DD.log`

Green:

- Fresh UnityFramework export/build/sync succeeds.
- RN iOS build/install/launch succeeds on the real iPhone.
- RN-hosted Unity opens and existing `unity_initialized` / `face_detected` / `recipe_applied` events still work.

Yellow:

- App runs only after a documented manual sync or local workaround.
- E7 may continue only if the workaround is recorded as a caveat.

Red:

- Fresh build cannot launch RN-hosted Unity.
- Unity events or RN -> Unity recipe path regress.

Stop rule:

- Do not start E7 visual work until the app being tested is confirmed to contain the current Unity code and RN bridge.

### E7.2 - Baseline Instrumentation

Priority: P0

Goal:

- Capture the current E3/E4 renderer behavior and add enough metrics to judge whether E7 improves visual quality without unacceptable performance cost.

Implementation touchpoints:

- `rn/MakeupARValidation/App.tsx`
- `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs`
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`

Implementation actions:

1. Add E7 runtime metric logging with at least:
   - approximate FPS
   - approximate frame time in ms
   - memory summary if available
   - recipe send timestamp and recipe applied timestamp
   - active region and active demo look
   - `trackingState`
   - face count and active trackable state
2. Add RN-visible E7 status panel or extend existing debug panel with:
   - current demo look
   - current region
   - latest FPS/frame-time summary if received
   - latest recipe latency if available
3. Capture baseline visual evidence before E7 renderer changes:
   - existing `matte_lip`
   - existing `soft_blush`
   - existing `shimmer_eye`
   - prefer representative frame/contact sheet plus metadata unless motion/time is the decision point
4. Keep runtime console output as a full stream with `tee`.

Evidence:

- `evidence/logs/e7-baseline-runtime-YYYY-MM-DD.log`
- Optional short raw recording only if motion/time is the decision point: `evidence/screen-recordings/e7-baseline-debug-mask-YYYY-MM-DD.mp4`
- `evidence/screenshots/e7-baseline-representative-frame-YYYY-MM-DD.jpg`

Green:

- Baseline runtime log includes face state, region state, sample state, FPS/frame-time or explicit metric-unavailable note, and recipe apply timing.
- Baseline visual evidence shows the current debug-quality renderer through representative frame/contact sheet, or through a short recording when motion/time is core evidence.

Yellow:

- Visual baseline exists, but one metric is missing and explicitly labeled unavailable.

Red:

- No baseline visual evidence or runtime stream exists.
- Existing E3/E4 behavior regresses before E7 changes.

Stop rule:

- Do not judge E7 improvement without baseline evidence.

### E7.3 - Region Precision Spike

Priority: P0

Goal:

- Determine whether `lip`, `cheek`, and `eye` can become more precise than the current broad debug masks while staying attached to the ARFace mesh.

Implementation touchpoints:

- Prefer adding a new validation component such as `E7RegionMaskOverlay` or clearly isolated E7 mode inside `E3RegionMaskOverlay.cs`.
- Preserve E3/E4 behavior as a fallback/baseline.

Implementation actions:

1. Confirm runtime `ARFace.uvs` availability and log:
   - vertex count
   - index count
   - uv count
   - active tracking state
2. Add an E7 mask mode that can render:
   - baseline centroid mask
   - E7 UV-space mask or authored mask candidate
3. Use `lip`, `cheek`, and `eye` as the only mask channels.
4. Start with hard debug colors before cosmetic finish work.
5. Add region-specific scoring scenarios:
   - Lip: neutral, smile, mouth open/close, pucker/talk-like motion, left/right head turn, lost/recovered.
   - Cheek: smile, yaw, pitch, near/far movement, partial profile, lost/recovered.
   - Eye: blink, repeated blink, squint, gaze left/right/up/down, head pitch, lost/recovered.
6. Add lightweight state handling:
   - on `Tracking`: render normally.
   - on short `Limited` / temporary lost: hold or fade for a short grace window.
   - on extended lost: fade out or disable region rendering.
7. Avoid adding MediaPipe or live segmentation in this milestone.

Evidence:

- `evidence/logs/e7-region-precision-runtime-YYYY-MM-DD.log`
- Optional short raw recording only if motion/expression/lost-recovered continuity is core evidence: `evidence/screen-recordings/e7-region-precision-lip-cheek-eye-YYYY-MM-DD.mp4`
- `evidence/screenshots/e7-region-precision-contact-sheet-YYYY-MM-DD.jpg`

Region G/Y/R:

| Region | Green | Yellow | Red |
| --- | --- | --- | --- |
| `lip` | Lip region stays attached through mouth open/close and turns; no obvious repeated spill into teeth/inner mouth in normal demo motion. | Good in neutral/light motion but visible spill, corner gaps, or mouth-open weakness remains. | Region cannot stay attached or repeatedly paints teeth/inner mouth/skin in normal motion. |
| `cheek` | Soft cheek zone stays attached and naturally feathered through smile/yaw/pitch; no sharp sticker edge. | Zone follows the face but placement or feather is weak across some poses. | Cheek patch drifts, crosses wrong facial areas, or cannot remain face-attached. |
| `eye` | Broad eyeshadow zone remains plausible through blink/squint/gaze/head pitch with no severe flicker. | Works only in narrow poses, with mild blink drift or shimmer instability. | Eye region jumps, paints eyeball/lash-line badly, or collapses on blink/squint. |

Overall:

- Green only if all three regions are at least demo-plausible and the result is better than baseline.
- Yellow if one region remains weak but the ARFace primary path remains viable.
- Red if ARFace mesh/UV cannot produce stable region masks for the required regions.

Stop rule:

- If region precision is Red, do not start cosmetic finish work. Record fallback analysis instead.

### E7.4 - Cosmetic Rendering Core

Priority: P0

Goal:

- Move beyond `color` + `opacity` debug rendering and prove a minimal pigment/finish model can look more like makeup.
- Prove renderer capability, not product-v1 makeup quality.
- Keep the implementation small enough to measure on the real iPhone.

Entry gate:

- Preferred gate: E7.3 reaches Q3 overlay-ready validation for `lip`, `cheek`, and `eye` with real-device visual/runtime evidence.
- Allowed but capped gate: the team explicitly accepts remaining E7.3 Yellow risk and records that E7.4/E7.5 evidence is conditional; full E7 visual product-readiness remains at most Yellow until the region gaps close.
- Do not start E7.4 from E7.2 metrics, E7.3 build/install logs, or offline atlas scores alone.

Implementation touchpoints:

- `rn/MakeupARValidation/App.tsx`
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- E7 renderer component from E7.3
- Unity material/shader assets created for E7 validation

Research-backed renderer model:

```txt
ARFace UV region mask
-> coverage / feather soft mask
-> pigment blend against live skin appearance
-> optional finish highlight or shimmer
-> transparent face-mesh composite
```

Implementation default:

- Use one isolated E7 validation renderer path, not the E3/E4 debug renderer as the permanent renderer.
- Keep E3/E4 baseline selectable for before/after comparison.
- Use the accepted E7.3 ARFace/UV region candidate as the placement source; do not add MediaPipe, face parsing, commercial SDK, Android, or product segmentation here.
- Prefer one mostly-unlit transparent makeup material or a very small material set.
- Do not migrate render pipelines inside E7.4 just because research recommends URP. If the current Unity project pipeline cannot support the needed transparent face-mesh overlay, write a separate render-pipeline gate before doing a migration.
- Keep active regions to `lip`, `cheek`, and `eye`; keep active makeup layers small enough for E7.6 performance evidence.

Minimum E7 recipe fields:

```json
{
  "version": 2,
  "lookId": "natural_daily",
  "layers": [
    {
      "id": "lip-primary",
      "region": "lip",
      "enabled": true,
      "color": "#C76B74",
      "opacity": 0.45,
      "coverage": 0.70,
      "feather": 0.10,
      "blendMode": "multiply",
      "finish": "cream",
      "texture": "lip_tint_soft"
    }
  ]
}
```

Allowed E7 experimental fields:

- `roughness`
- `specular`
- `specularPower`
- `glossBoost`
- `shimmer`
- `shimmerColor`
- `textureAmount`
- `skinAdaptive`
- `preserveDetail`

Parameter model:

| Group | Fields | Purpose |
| --- | --- | --- |
| Placement | `region`, `coverage`, `feather` | Decides where the product appears and how the edge disappears. |
| Pigment | `color`, `opacity`, `blendMode`, `texture`, `textureAmount`, `skinAdaptive`, `preserveDetail` | Decides how product color mixes with skin and whether skin detail survives. |
| Finish | `finish`, `roughness`, `specular`, `specularPower`, `glossBoost`, `shimmer`, `shimmerColor` | Decides whether the result reads as matte, cream, gloss, powder, or shimmer. |

Default values when fields are missing:

| Field | Default |
| --- | --- |
| `coverage` | `0.70` |
| `feather` | `0.10` |
| `blendMode` | `multiply` |
| `finish` | `cream` |
| `textureAmount` | `0.0` |
| `roughness` | `0.60` |
| `specular` | `0.15` |
| `specularPower` | `16` |
| `glossBoost` | `0.0` |
| `shimmer` | `0.0` |
| `skinAdaptive` | `0.70` |
| `preserveDetail` | `0.65` |

Region defaults:

| Region | Default product | Blend | Finish | Edge / strength guidance |
| --- | --- | --- | --- | --- |
| `lip` | tint / cream lipstick | `multiply` | `cream` | tighter feather `0.04-0.12`, medium/high coverage, preserve lip detail. |
| `cheek` | powder / cream blush | `softLight` | `powder` | wide feather `0.30-0.45`, low opacity, broad coverage. |
| `eye` | matte shadow / shimmer | `multiply` or `softLight` | `matte` or `shimmer` | medium feather `0.16-0.26`, shimmer only through texture-based sparkle. |

Finish mapping:

| Finish | Renderer behavior |
| --- | --- |
| `matte` | Pigment only; specular near `0`; no shimmer. |
| `cream` | Pigment plus broad weak sheen; low/moderate `specular`, low/moderate `specularPower`. |
| `gloss` | Pigment base plus tight moving highlight; high `specular`, high `specularPower`, low `roughness`. |
| `shimmer` | Pigment plus sparkle texture gated by `shimmer` and tinted by `shimmerColor`; avoid procedural noise. |
| `powder` | Low opacity, wide feather, no specular; best default for cheek. |

Implementation actions:

1. Create `E7_COSMETIC_RENDERING_CORE_SUBSPIKE_PLAN.md` before implementation unless the user explicitly asks for a one-session minimal renderer proof. The sub-spike must copy the entry gate and stop rules from this section.
2. Keep existing E4 fields backward compatible:
   - `region`
   - `layer`
   - `color`
   - `opacity`
   - `texture`
   - `sample`
   - `textureMode`
   - `intensity`
   - `feather`
   - `blendMode`
3. Treat E4 `intensity` as legacy/master strength only. Do not make `intensity`, `opacity`, and `coverage` three independent E7 controls unless a later spec explicitly needs that.
4. Add E7 v2 parsing without breaking E3/E4 validation payloads.
5. Log at least `lookId`, layer ids, active regions, renderer mode, blend mode, finish, recipe latency, and whether E7 defaults were applied.
6. Implement limited blend modes:
   - `normal`
   - `multiply`
   - `softLight` if feasible
   - `screen`
7. Implement limited finish presets:
   - `matte`: low/no specular, texture optional.
   - `cream`: low broad specular.
   - `gloss`: stronger specular / gloss highlight.
   - `shimmer`: texture-based shimmer, no procedural heavy noise.
   - `powder`: low opacity, high feather, low/no specular.
8. Implement `coverage` and `feather` as first-class mask controls. The first visual gate is not gloss; it is whether blend + feather visibly beats the old alpha/debug overlay.
9. Implement `skinAdaptive` and `preserveDetail` as lightweight validation controls. If live camera/backdrop sampling is used, keep it GPU-oriented or very low sample count; do not store raw frames and do not upload frames.
10. Keep shader complexity low: no full PBR/GGX, no multi-light setup, no reflection probes, no procedural sparkle, no broad per-pixel branching over many layers, and no high-resolution mask stack unless E7.6 evidence says it is safe.
11. If a basic transparent cosmetic material cannot render on the live AR background on the real iPhone, stop and resolve that foundation issue before implementing blend/finish complexity.

Evidence:

- `evidence/logs/e7-renderer-core-runtime-YYYY-MM-DD.log`
- Optional short raw recording only if temporal visual behavior is core evidence: `evidence/screen-recordings/e7-renderer-core-comparison-YYYY-MM-DD.mp4`
- `evidence/screenshots/e7-renderer-core-before-after-YYYY-MM-DD.jpg`
- The before/after evidence must include the old E3/E4 alpha/debug behavior and the E7 cosmetic renderer under the same region/scenario where practical.

Green:

- E7 renderer visibly improves over alpha/normal debug overlay.
- `coverage`, `feather`, `blendMode`, `texture`, and `finish` produce distinguishable effects.
- `lip`, `cheek`, and `eye` all remain attached at least as well as the accepted E7.3 candidate used for entry.
- No raw frame is stored or uploaded.
- No obvious severe performance regression appears before full demo validation.

Yellow:

- Renderer improves visual quality but one finish type is weak or only convincing in narrow conditions.

Red:

- Renderer still looks like simple color overlay.
- Finish effects break region stability or cause severe performance problems.
- A basic transparent cosmetic overlay cannot render over the live AR camera path on the real iPhone.

Stop rule:

- Do not create more demo looks until the core renderer can show a visible improvement over baseline.
- Do not use gloss, shimmer, or strong color to hide weak region precision.

### E7.5 - Demo Look Implementation

Priority: P1

Goal:

- Validate three focused demo looks, each answering a different E7 question.
- Use a temporary 3x3 Look Pack to extract parameter insight, then compress the result back to exactly three final E7 demo looks.

Implementation actions:

1. Add RN demo look selector for the temporary `E7 Look Pack` samples while E7.5 tuning is active.
2. Add final demo look selector for exactly:
   - `natural_daily`
   - `gloss_lip_focus`
   - `soft_blush_shimmer_eye`
3. Send each look as full recipe JSON through the existing `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)` path.
4. Keep manual region/color/opacity controls available only if they do not obscure demo validation.
5. Log `lookId`, active layers, active region list, render mode, changed parameter focus, and recipe latency.

Temporary 3x3 Look Pack:

| Owner slot | Sample 1 | Sample 2 | Sample 3 |
| --- | --- | --- | --- |
| A | `daily_subtle` | `gloss_balanced` | `texture_bold` |
| B | `daily_balanced` | `gloss_bold` | `texture_subtle` |
| C | `daily_bold` | `gloss_subtle` | `texture_balanced` |

Strength meaning:

| Strength | Meaning | Use |
| --- | --- | --- |
| `subtle` | Safe and natural | Find the minimum visible makeup effect. |
| `balanced` | Demo-visible but still plausible | Candidate for final recipe defaults. |
| `bold` | Limit-finding stress sample | Find where sticker, paint, glare, or noisy shimmer failure begins. |

Concept focus:

| Concept | Primary question | Required regions | Main parameters to vary |
| --- | --- | --- | --- |
| `daily` | Does product blend into skin while keeping detail? | `lip`, `cheek`, `eye` | `opacity`, `blendMode`, `skinAdaptive`, `preserveDetail` |
| `gloss` | Can pigment and finish read as separate layers? | `lip`, optional weak `cheek` | `roughness`, `specular`, `specularPower`, `glossBoost`, `screen` |
| `texture` | Do feather, texture, and shimmer improve realism without noise? | `cheek`, `eye`, optional nude `lip` | `coverage`, `feather`, `textureAmount`, `shimmer`, `shimmerColor` |

Sample metadata contract:

```json
{
  "lookId": "gloss_balanced",
  "ownerSlot": "A",
  "concept": "gloss",
  "strength": "balanced",
  "intent": "prove lip pigment and gloss finish separation",
  "changedParams": ["specular", "specularPower", "glossBoost"],
  "expectedEffect": "moving lip highlight without white-paint glare",
  "risk": "static white paint or lip-boundary spill",
  "layers": []
}
```

Look Pack rules:

- Each sample may vary only its declared main parameters plus color choices needed for the concept.
- Non-target parameters must use E7.4 defaults so the team can identify what changed the visual result.
- The 9 samples are exploration artifacts, not final product looks.
- After team review, extract useful parameter decisions and discard weak samples.

Final synthesis:

- `natural_daily` = best skin blend + best subtle lip/cheek/eye balance.
- `gloss_lip_focus` = best lip pigment base + best non-static gloss highlight.
- `soft_blush_shimmer_eye` = best cheek feather + best stable eye shimmer.
- Do not carry all 9 Look Pack samples forward as final E7 demos.

Demo criteria:

| Look | Purpose | Required regions | Required properties | Green condition |
| --- | --- | --- | --- | --- |
| `natural_daily` | Baseline natural makeup credibility | `lip`, `cheek`, `eye` | lip tint, low/medium opacity, soft cheek feather, subtle eye shadow, `multiply`/`softLight`, `cream`/`powder`/`matte` finishes | Looks less like a sticker than baseline; skin detail remains visible; cheek edge does not pop during smile/turn. |
| `gloss_lip_focus` | Prove pigment and finish are separate | `lip`, optional weak `cheek` | lip base pigment, gloss/highlight layer, `screen` or gloss path, `specular`, `specularPower`, low `roughness`, tight feather | Lip color blends with the face and gloss/highlight reads as finish, not static white paint; mouth-open spill is not severe. |
| `soft_blush_shimmer_eye` | Prove feather and texture/shimmer control | `cheek`, `eye`, optional nude `lip` | wide cheek feather, powder finish, eye shimmer texture, `shimmer`, `shimmerColor`, moderate eye feather | Cheek fades naturally; eye shimmer stays in eye region; blink/squint flicker is no worse than Yellow. |

Evidence:

- `evidence/logs/e7-demo-looks-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-look-pack-review-YYYY-MM-DD.md`
- Optional short raw recording only if transitions/motion are core evidence: `evidence/screen-recordings/e7-demo-looks-natural-gloss-shimmer-YYYY-MM-DD.mp4`
- `evidence/screenshots/e7-look-pack-contact-sheet-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-demo-looks-contact-sheet-YYYY-MM-DD.jpg`

Green:

- All three looks are visibly distinct.
- Each look demonstrates its intended technical point.
- The final three looks are synthesized from Look Pack evidence, not hand-waved from subjective preference alone.
- No look requires product catalog, AI, backend, commercial SDK, or raw-frame storage.

Yellow:

- Two looks are credible and one remains weak.
- Any required look is intentionally reduced or skipped without replacing the whole E7 decision target.
- Continue with explicit blocker notes.

Red:

- Looks are not visually distinct from debug overlays.
- More than one look breaks region stability or performance.

Stop rule:

- Do not expand beyond the three final demo looks in E7. Temporary Look Pack samples are allowed only as evidence-generating exploration and must be collapsed before E7.8 handoff.
- Do not keep tuning the Look Pack once the team can identify the best parameter decisions and the worst failure boundaries.

### E7.6 - Performance and Device Evidence Pass

Priority: P1

Goal:

- Decide whether E7 visual improvements are feasible on the real iPhone without unacceptable frame, thermal, memory, or latency cost.

Default measurement methods:

- FPS/frame-time:
  - Add a lightweight Unity runtime sampler in `FaceTrackingStatusReporter`, the E7 renderer component, or a small `E7PerformanceReporter`.
  - Use `Time.unscaledDeltaTime` or equivalent Unity frame timing.
  - Emit a summary every 2 seconds while the E7 screen is active.
  - Include at least average FPS, average frame time, worst observed frame time in the sample window, active `lookId`, active regions, and active renderer mode.
- Memory:
  - Prefer Unity `UnityEngine.Profiling.Profiler` counters if available in the build, such as allocated/reserved memory.
  - Also record RN/iOS memory warnings if they occur.
  - If reliable memory counters are not available, write `memoryMetricAvailable=false` and keep the memory decision at Yellow unless the run is otherwise stable and the limitation is explicitly accepted.
- Thermal:
  - Record any iOS/Unity thermal warning, app instability, or device heat concern.
  - If a thermal API/native bridge is not already available, use manual device heat observation and label it as manual.
  - Manual-only thermal evidence can support continuing the spike, but should not be used to overclaim product readiness.
- Latency:
  - RN should attach a `sentAtMs` timestamp and `lookId` to each E7 recipe payload.
  - Unity should echo the `lookId`, active recipe id, and applied timestamp or frame count in `recipe_applied`.
  - RN should log the observed send-to-ack latency.
  - Visual latency still needs human confirmation from representative evidence; capture a short recording only when still frames cannot show lag/motion continuity.
- Summary:
  - Create `evidence/logs/e7-performance-summary-YYYY-MM-DD.log`.
  - The summary must state which metrics are measured, which are unavailable, and whether each unavailable metric caps the E7 result at Yellow.

Implementation actions:

1. Run the final E7 demo on the real iPhone.
2. Capture a full runtime stream with `tee`.
3. Capture visual decision evidence. Record a short clip only when motion/time/continuous scenario evidence is required; if one clip covers all looks and scenarios, it must be long enough to show:
   - baseline or transition from baseline
   - all three demo looks
   - at least one head movement sequence
   - at least one expression sequence
   - lost/recovered if used for the decision
4. Capture metrics:
   - approximate FPS or frame-time
   - thermal warning or manual device heat observation
   - memory observation or explicit unavailable note
   - recipe send to visual-applied latency
5. Save representative screenshots, metadata, or a contact sheet. Capture a short recording only if visual latency/motion continuity cannot be judged from still evidence.

Evidence:

- `evidence/logs/e7-performance-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-performance-summary-YYYY-MM-DD.log`
- Optional short raw recording only if visual latency/motion continuity is core evidence: `evidence/screen-recordings/e7-performance-demo-YYYY-MM-DD.mp4`
- `evidence/screenshots/e7-performance-contact-sheet-YYYY-MM-DD.jpg`

Performance G/Y/R:

| Layer | Green | Yellow | Red |
| --- | --- | --- | --- |
| FPS/frame-time | Average remains at or above 30 fps equivalent, no obvious sustained collapse, and no sustained sub-20 fps segment. | Metrics are partial or mild stutter appears, but interaction remains usable. | Sustained severe stutter, sustained sub-20 fps, or frame-time spikes make demo unreliable. |
| Thermal | No iOS/Unity thermal warning when available; manual heat observation is recorded and not concerning during the decision run. | Device becomes warm, thermal API is unavailable, or thermal evidence is manual-only and too short to be confident, but no warning/crash occurs. | Thermal warning, severe heat, or app instability. |
| Memory | No RN memory warning, crash, or obvious memory growth during demo. | Memory evidence is incomplete but no instability observed. | Memory warning, crash, black screen, or reload. |
| Latency | Recipe change is visually reflected within 1 second. | Reflected within 2 seconds or latency logging is incomplete. | More than 2 seconds, inconsistent application, or stale visual state. |

Stop rule:

- E7 cannot be Green without explicit performance evidence.

### E7.7 - Fallback and Scope Decision

Priority: P2

Goal:

- Decide whether ARFace-only remains viable or whether a future fallback comparison is needed.

Implementation actions:

1. Review E7.3-E7.6 results by region.
2. Do not add MediaPipe live runtime during E7 unless the user explicitly starts a separate fallback milestone.
3. If a region is Red or stubborn Yellow, record one of:
   - keep ARFace-only and tune mask/feather later
   - run future offline MediaPipe/reference comparison on the same recorded clips
   - create a future fallback spike
4. Keep commercial SDKs as benchmark/reference only.

Fallback triggers:

- Lip repeatedly spills into teeth/inner mouth after mask tuning.
- Eye repeatedly flickers or paints wrong areas during blink/squint.
- Cheek cannot achieve soft stable placement.
- Performance cannot support E7 renderer at demo quality.
- Lifecycle/re-entry behavior blocks target UX.

Evidence:

- `evidence/logs/e7-fallback-decision-YYYY-MM-DD.log` if a fallback review is performed.

Decision:

- Green: no fallback needed now.
- Yellow: fallback/reference comparison may be useful later for one region.
- Red: current ARFace-only visual path is blocked for the failing region.

Stop rule:

- Do not implement fallback inside E7 unless E7 is explicitly re-scoped.

### E7.8 - Result Handoff

Priority: P2

Goal:

- Close E7 honestly and prepare the next boundary.

Implementation actions:

1. Update `TECH_VALIDATION_RESULT.md` only after real E7 evidence exists.
2. Record:
   - decision date/time
   - implementation summary
   - evidence paths
   - region G/Y/R
   - renderer G/Y/R
   - performance G/Y/R
   - known limitations
   - next boundary
3. Delete `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` after its result is absorbed, unless the user asks to keep it temporarily.
4. Keep `TECH_VALIDATION_TEST_PLAN.md` unchanged unless correcting the validation contract.

Possible E7 final decisions:

- Green for visual product-readiness spike: limited demo visuals are credible enough to continue hardening, but still not product-v1-ready.
- Yellow: direction remains viable, but one or more layers need another focused spike.
- Red: visual product-readiness is blocked; do not continue renderer/product work until blocker is solved.

Stop rule:

- Do not close E7 without evidence paths in `TECH_VALIDATION_RESULT.md`.

## 8. File Touchpoints for Implementation Session

Expected implementation files:

- `rn/MakeupARValidation/App.tsx`
  - Add E7 look selection.
  - Send v2 recipe payloads.
  - Display E7 status/metrics if available.
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
  - Parse additive v2 fields while preserving E3/E4 payload compatibility.
  - Emit `recipe_applied` with `lookId`, region, finish, blend, texture, latency fields if available.
- `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs`
  - Provide tracking, mesh/UV, and metric status for E7 evidence.
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs` or new E7 renderer component
  - Preserve baseline.
  - Add E7 region precision and cosmetic rendering mode.

Optional implementation files:

- New Unity script for E7 renderer/metrics if isolating from E3/E4 is cleaner.
- New Unity material/shader assets for E7 validation.
- New runbook only if the E7 procedure becomes reusable beyond one session.

## 9. Evidence Naming Contract

Use these names unless the implementation session needs a more specific suffix:

- `evidence/logs/e7-unityframework-export-YYYY-MM-DD.log`
- `evidence/logs/e7-unityframework-build-YYYY-MM-DD.log`
- `evidence/logs/e7-artifact-verification-YYYY-MM-DD.log`
- `evidence/logs/e7-build-install-run-YYYY-MM-DD.log`
- `evidence/logs/e7-baseline-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-region-precision-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-renderer-core-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-look-pack-review-YYYY-MM-DD.md`
- `evidence/logs/e7-demo-looks-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-performance-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-performance-summary-YYYY-MM-DD.log`
- `evidence/screenshots/e7-baseline-representative-frame-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-region-precision-contact-sheet-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-renderer-core-before-after-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-look-pack-contact-sheet-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-demo-looks-contact-sheet-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-performance-contact-sheet-YYYY-MM-DD.jpg`

Optional raw recordings, only when motion/time/continuous scenario evidence is required:

- `evidence/screen-recordings/e7-baseline-debug-mask-YYYY-MM-DD.mp4`
- `evidence/screen-recordings/e7-region-precision-lip-cheek-eye-YYYY-MM-DD.mp4`
- `evidence/screen-recordings/e7-demo-looks-natural-gloss-shimmer-YYYY-MM-DD.mp4`
- `evidence/screen-recordings/e7-performance-demo-YYYY-MM-DD.mp4`

Do not commit `evidence/`.

## 10. Global Stop Rules

Stop the E7 implementation session immediately if any of these happens:

- Fresh UnityFramework build/sync cannot produce a runnable RN-hosted Unity app.
- RN -> Unity `ApplyRecipeJson` or Unity -> RN event receipt regresses.
- Face tracking/mesh/UV data is not available on the real iPhone.
- E7.4 starts without Q3 region evidence or recorded E7.3 Yellow-risk acceptance.
- E7 region precision is Red before cosmetic rendering starts.
- Cosmetic renderer causes severe performance collapse.
- Any step requires raw camera frame storage, off-device upload, AI inference, backend work, commercial SDK integration, or Android implementation.
- The session begins to claim product-v1 readiness.
- A formal M7 claim is needed but the 3-cycle re-entry evidence is not collected.

## 11. Final Acceptance Criteria for E7

E7 can be called Green only if all are true:

1. Fresh build/install/run evidence exists.
2. Baseline E3/E4 visual evidence exists.
3. `lip`, `cheek`, and `eye` each have region precision G/Y/R.
4. The E7 renderer visibly improves beyond simple debug overlay.
5. `natural_daily`, `gloss_lip_focus`, and `soft_blush_shimmer_eye` are all demonstrated. If any required look is reduced or skipped, the final E7 decision is at most Yellow unless the user explicitly re-scopes E7 before implementation.
6. If the 3x3 Look Pack path was used, the final three looks are synthesized from recorded Look Pack evidence and the weak samples are not promoted as final demos.
7. FPS/frame-time, thermal, memory, and latency evidence exists.
8. No product/backend/AI/commercial SDK/Android/raw-frame scope was introduced.
9. `TECH_VALIDATION_RESULT.md` records the decision, evidence, limitations, and next boundary.

If any of 1-9 is missing, E7 is not Green. If E7.4/E7.5 proceeds under explicit E7.3 Yellow-risk acceptance, full E7 visual product-readiness remains at most Yellow until the region gaps are closed with evidence.
