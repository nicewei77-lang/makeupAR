# Eyebrow Makeup Development Log

Status: Active
Date: 2026-06-27

## Context

The user requested implementation of only the eyebrow makeup feature inside the
existing React Native + Unity + AR Foundation makeup app. The broader camera,
photo/video, backend, AI, Android, monetization, and App Store submission
surfaces remain out of scope.

Relevant starting docs read:

- `AGENTS.md`
- `docs/product/two-stage-ar-makeup-product-strategy.md`
- `docs/roadmaps/active/product-development-documentation-loop.md`
- `docs/roadmaps/active/eyebrow-makeup-implementation-prompt.md`

## Repo Research Summary

Current runtime makeup path:

- React Native app: `rn/MakeupARValidation/App.tsx`
- RN tests: `rn/MakeupARValidation/__tests__/App.test.tsx`
- Unity bridge: `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- Unity region renderer:
  `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
- Shader: `unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader`
- Mask resources:
  `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/`

Findings:

- The current bridge and Unity renderer accept only `lip`, `cheek`, and `eye`.
- No eyebrow runtime implementation exists yet.
- Existing rendering is ARFace UV mesh based through `smooth-region-mask`.
- Lip has extra atlas/culling/gloss behavior. Cheek and eye mostly use the same
  smooth mask renderer with different masks and material parameters.
- The worktree already contains unrelated uncommitted and untracked changes.
  Future staging must include only eyebrow-related files.

## Approved Direction

2026-06-27:

- User approved starting with approach 1: add eyebrow through the existing
  `smooth-region-mask` renderer.
- User asked if approaches 2 and 3 can be added later. Decision: yes, if RN
  keeps a stable `region="brow"` recipe contract and Unity owns renderer
  routing.
- User noted that existing regions should also eventually have separate
  renderers. Decision: prepare a region-to-renderer routing contract now, but do
  not split lip/cheek/eye renderers in the first eyebrow loop.

Initial route table:

- `lip` -> `smooth-region-mask`
- `cheek` -> `smooth-region-mask`
- `eye` -> `smooth-region-mask`
- `brow` -> `smooth-region-mask`

Future route table can replace any row with a dedicated renderer such as
`BrowMakeupRenderer`.

## Implementation Loop 1 Plan Summary

This is a summary only. A detailed implementation plan will be written after
the user reviews the design docs.

Expected first slice:

- Add `brow` to RN region types and recipe payloads.
- Add brow presets and minimal controls.
- Add tests that first fail for missing brow payload support.
- Add Unity parser and smooth-mask normalization support for `brow`.
- Generate an in-house procedural brow mask texture.
- Run RN tests, TypeScript, static checks, and Unity batchmode compile.
- Stop for real-device build approval before iPhone build/install.

## Approval Gates

Approval is still required before:

- Starting implementation after written spec review.
- Unity/RN real-device iPhone build or signing/device-targeted Xcode build.
- Any AI/model inference, recommendation, backend upload, or raw-frame storage.
- Android work.
- Payment, ads, brand partnership, product sales, or commercial SDK use.
- Any dependency, asset, model, LUT, or SDK with unclear license terms.

## Current Risks

- Brow UV mask fit is unknown until device QA.
- A generic smooth mask may not produce enough hair-like texture.
- Full renderer split is likely useful later but would increase first-loop
  regression risk if done before brow has a working visual baseline.
- Existing dirty worktree must be handled carefully to avoid committing
  unrelated user or generated changes.

## Checkpoints

- 2026-06-27: Goal created: "기존 AR 메이크업 앱 안의 눈썹 메이크업 기능을 상용 제품 퀄리티 목표로 구현".
- 2026-06-27: Design docs created for product behavior, AR rendering design,
  and development log. Implementation not started.
- 2026-06-27: Implementation plan created and pushed on `feature/brow-0626`.
- 2026-06-27: RN recipe contract implemented in commit `323d0ce`.
  - RED: focused Jest failed because `BROW_TEXTURE_STYLE_OPTIONS` and `brow`
    controls were missing.
  - GREEN: focused Jest passed, 23 tests.
  - Added `brow` as fourth recipe region, `natural_brow`, `soft_brow`, and
    `brow-drawn-mask-v1` to the RN payload/HUD contract.
- 2026-06-27: Procedural brow mask asset implemented in commit `a40a582`.
  - RED: `verify_brow_mask_texture.py` failed because
    `brow-drawn-mask-v1.png` was missing.
  - GREEN: verifier passed with `11275` active pixels, `0.043011` coverage,
    bbox `left=99,top=132,right=412,bottom=196,width=314,height=65`, and two
    brow components.
  - Asset is generated in-house by
    `scripts/e7_reference_atlas/generate_brow_mask_texture.py`.
- 2026-06-27: Unity brow bridge/render contract implemented in commit
  `a48dbb4`.
  - RED: `verify_brow_unity_contract.py` failed on 3-region
    `FeatureSnapshotRegions`.
  - GREEN: Unity contract verifier passed.
  - Unity `6000.3.18f1` batchmode import/compile exited `0`; log included
    `Tundra build success` and imported
    `Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png`.
  - Batchmode log also printed a Unity shutdown-time `.NET SDK` warning after
    successful compile/import; no C# compile failure was reported.
- 2026-06-27: Final local verification sweep before device build gate:
  - RN focused Jest: passed, 23 tests.
  - RN lint: passed.
  - RN TypeScript compile: `npx tsc --noEmit` passed.
  - Brow mask verifier: passed.
  - Unity brow contract verifier: passed.
- 2026-06-27: Brow mask region-separation guard added after local inspection
  showed excessive overlap with the existing eye masks.
  - RED: `verify_brow_mask_texture.py` failed with
    `Brow mask overlaps eye-drawn: 4702 > 1200`.
  - GREEN: generator moved the brow curves upward. Verifier passed with
    `11205` active pixels, `0.042744` coverage, bbox
    `left=99,top=80,right=412,bottom=142,width=314,height=63`, and overlaps
    `eye-drawn=406/1200`, `eye-smooth=56/4200`, `cheek-drawn=0/50`,
    `lip-drawn=0/0`.
  - RN focused Jest, RN lint, RN TypeScript compile, brow Unity contract
    verifier, and Unity `6000.3.18f1` batchmode import/compile all passed
    after the adjustment.
  - Unity batchmode reported only `212Mi` available disk space on
    `/System/Volumes/Data`; device build likely needs cleanup before running.
- 2026-06-27: Region renderer route table added to turn the renderer-split
  decision into code-level routing.
  - RED: `verify_region_renderer_routes.py` failed because
    `MakeupRegionRendererRoutes.cs` did not exist.
  - GREEN: route verifier passed after adding per-region renderer ids:
    `lip-smooth-region-mask-renderer`, `cheek-smooth-region-mask-renderer`,
    `eye-smooth-region-mask-renderer`, and `brow-smooth-region-mask-renderer`,
    all currently backed by `E3RegionMaskOverlay`.
  - RN HUD now displays Unity `rendererId` from `recipe_applied` events; focused
    Jest first failed on missing `renderer=lip-smooth-region-mask-renderer`,
    then passed after the formatter update.
  - RN focused Jest, RN lint, RN TypeScript compile, brow mask verifier, brow
    Unity contract verifier, region route verifier, and Unity `6000.3.18f1`
    batchmode import/compile all passed.
  - Unity compile emitted an existing obsolete API warning in
    `Assets/Editor/MakeupARValidationSetup.cs`; no route-table compile errors
    were reported.

## Build Gate Packet

Real-device build has not been run in this loop.

Before building on iPhone, report and get user approval for:

- Primary path: regenerate/sync `UnityFramework.framework` with
  `bash scripts/build_m3_unityframework.sh`, then run the RN/Xcode target with
  the user-approved device and signing team.
- Target assumptions: real iPhone with ARKit face tracking support; no hard-coded
  UDID or `DEVELOPMENT_TEAM` should be added as repo defaults.
- Expected risk: first-loop static UV brow placement may need arch/width/tail
  tuning after visual QA.
- Local machine risk: current disk free space is about `212Mi`; cleanup should
  happen before real-device export/build. Large generated candidates observed:
  `unity-builds` about `3.1G` and Unity `Library` about `796M`.
- Out of scope: Android, AI/model inference, backend upload, raw-frame storage,
  payment, ads, commercial SDKs, and App Store readiness claims.
