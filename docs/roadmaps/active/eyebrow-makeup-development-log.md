# Eyebrow Makeup Development Log

Status: Active
Date: 2026-06-30

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

- 2026-06-30: Updated `ARCore_canonical_face_texture_1.psd` applied to the
  PSD canonical asset pipeline.
  - Replaced the repo PSD input from the updated Dropbox source and reran PSD
    layer extraction plus runtime texture generation.
  - Root cause for missing cheek/brow layers in the first extraction pass:
    runtime layer matching was too strict. The updated PSD uses `Semi-arch`
    capitalization for brow and `Root/blush/<style>/all` sources for cheek.
    The extractor now matches runtime layer paths case-insensitively and
    includes all seven cheek styles.
  - Generated cheek masks:
    `psd-arcore-cheek-undereye-v1` bbox `(74,135,436,310)` active `43761`,
    `psd-arcore-cheek-asia-z-v1` bbox `(40,147,470,319)` active `50913`,
    `psd-arcore-cheek-sunkissed-v1` bbox `(64,158,448,304)` active `44665`,
    `psd-arcore-cheek-daily-oval-v1` bbox `(75,203,429,304)` active `25574`,
    `psd-arcore-cheek-undereye2-v1` bbox `(59,158,452,330)` active `44739`,
    `psd-arcore-cheek-lovely-round-v1` bbox `(89,161,422,333)` active `44165`,
    and `psd-arcore-cheek-lifted-diagonal-v1` bbox `(40,131,471,271)` active
    `33398`.
  - RN exposes all seven cheek masks in the cheek mask picker; Unity
    `RNBridge` accepts all seven ids for the cheek region.
  - Verification passed: PSD ARCore texture verifier, brow landmark privacy
    verifier, brow Unity contract verifier, RN TypeScript, and focused RN Jest.
- 2026-06-30: MediaPipe canonical-face brow landmark bridge implemented after
  user approval for the on-device dependency/model path.
  - iOS app target links `MediaPipeTasksVision` `0.10.14` and bundles
    `face_landmarker.task`.
  - Swift runtime in the app target exposes app-owned C symbols
    `E7MediaPipeAppDetectBrowLandmarksPng` and
    `E7MediaPipeAppReleaseCString`, runs Face Landmarker on transient
    in-memory PNG bytes, and returns eyebrow landmark/bbox/confidence/timing/
    status JSON.
  - Unity added `E7MediaPipeBrowLandmarkRuntime`, enabled only while brow is
    active, plus an iOS UnityFramework bridge plugin that exports the
    Unity-facing `E7MediaPipeDetectBrowLandmarksPng` and
    `E7MediaPipeReleaseCString` symbols. The plugin uses `dlsym` to call the
    app-owned Swift symbols so UnityFramework can link standalone while the app
    target owns the MediaPipe Swift dependency.
  - Unity forwards `e7_mediapipe_brow_landmarks` events through `RNBridge`.
  - RN HUD recognizes `e7_mediapipe_brow_landmarks` and summarizes point
    counts, bbox, confidence, latency, and privacy flags.
  - Privacy contract remains: no raw frame storage or upload; diagnostics are
    numeric landmark/bbox/confidence/timing/status only.
  - Verification passed: MediaPipe brow privacy contract verifier, brow Unity
    contract verifier, RN Jest, RN TypeScript, and generic iOS xcodebuild with
    code signing disabled. This bridge is installed and diagnosable on device,
    but it does not yet drive final brow placement/warp.
- 2026-06-30: Approved iPhone build completed for the updated PSD cheek set,
  canonical-mask defaults, and MediaPipe brow landmark bridge.
  - First UnityFramework attempt failed because Unity's `DllImport("__Internal")`
    needed `E7MediaPipeDetectBrowLandmarksPng` and
    `E7MediaPipeReleaseCString` inside `UnityFramework.framework`, while the
    MediaPipe implementation lived only in the RN app target. The fix was the
    app-symbol/Unity-bridge split described above.
  - UnityFramework regenerated and synced with
    `TIMESTAMP=psd-cheek-mediapipe-20260630-ufw-r2`; artifact verification
    recorded `137M` UnityFramework copies with `41M` Unity `Data` folders in
    both RN and package-local framework paths.
  - RN/Xcode Debug build for `CloudsiPhone` passed with development team
    `X5C5U3T6B4`, producing a signed `257M` `MakeupARValidation.app` with a
    `137M` embedded UnityFramework.
  - `devicectl` installed and launched `com.celeste.makeupar.validation` on
    `CloudsiPhone` (`FD44CD30-B236-5594-BE61-3C5D408A6851`).
  - Logs:
    `evidence/logs/m3-repro-unity-export-psd-cheek-mediapipe-20260630-ufw-r2.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-psd-cheek-mediapipe-20260630-ufw-r2.log`,
    `evidence/logs/m3-repro-artifact-verification-psd-cheek-mediapipe-20260630-ufw-r2.log`,
    `evidence/logs/rn-xcodebuild-device-debug-psd-cheek-mediapipe-20260630-r1.log`,
    `evidence/logs/devicectl-install-makeupar-psd-cheek-mediapipe-20260630-r1.log`,
    and
    `evidence/logs/devicectl-launch-makeupar-psd-cheek-mediapipe-20260630-r1.log`.
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
- 2026-06-27: Brow-specific mask threshold/feather policy added under the
  route-backed renderer path.
  - RED: `verify_brow_unity_contract.py` failed with
    `E3RegionMaskOverlay must define a brow-specific mask threshold`.
  - GREEN: `E3RegionMaskOverlay` now defines `BrowMaskThreshold = 0.035f`,
    `BrowMaskFeatherUvNormalized = 0.42f`, and recipe feather clamp
    `0.34f..0.48f` for `region == "brow"`.
  - Brow Unity contract verifier, brow mask verifier, and region renderer route
    verifier passed.
  - Unity batchmode compile was not rerun after this C# policy change because
    `/System/Volumes/Data` currently has less than `400Mi` free. No generated
    cache cleanup was performed without user approval.
- 2026-06-27: Pre-build verification refresh before asking for device QA/build
  approval.
  - Brow Unity contract verifier: passed.
  - Brow mask verifier: passed with `11205` active pixels, `0.042744`
    coverage, bbox `left=99,top=80,right=412,bottom=142,width=314,height=63`,
    and overlaps `eye-drawn=406/1200`, `eye-smooth=56/4200`,
    `cheek-drawn=0/50`, `lip-drawn=0/0`.
  - Region renderer route verifier: passed.
  - RN focused Jest: passed, 23 tests.
  - RN lint: passed.
  - RN TypeScript compile: `npx tsc --noEmit` passed.
  - Disk check: `/System/Volumes/Data` had `368Mi` free. Large generated
    cleanup candidates observed: `unity-builds` `3.1G` and Unity `Library`
    `793M`. No cleanup was performed without user approval.
- 2026-06-27: Completion audit added at
  `docs/runbooks/eyebrow-makeup-completion-audit.md`.
  - Current conclusion: the first-loop eyebrow module is locally verified, but
    the full objective is not complete until Unity compile is rerun after the
    latest C# policy change, real-device iPhone QA confirms placement/natural
    appearance/tracking recovery, and the left/right asymmetry-control gap is
    either implemented or explicitly deferred by user decision.
- 2026-06-27: Device QA observation template added to
  `docs/runbooks/eyebrow-makeup-qa-runbook.md` so the first real-device pass can
  capture scenario-specific user feedback without storing face screenshots by
  default.

## Device Build Result

2026-06-27:

- User approved generated-cache cleanup and the real-device Unity/RN build path.
- Generated cleanup removed reproducible build/cache output only:
  `unity-builds`, Unity `Library`, and stale Xcode DeviceSupport cache.
- UnityFramework attempt 1 failed because Unity export hit `No space left on
  device`; the build script previously missed this because Unity exited `0`.
- UnityFramework attempt 2 failed while linking Unity ARKit static libs because
  Swift compatibility libraries were not linked.
- Build contract fix:
  - `MakeupARValidationSetup.cs` now adds
    `$(TOOLCHAIN_DIR)/usr/lib/swift/iphoneos`.
  - It links `-lswiftCompatibility51`, `-lswiftCompatibility56`,
    `-lswiftCompatibilityConcurrency`, and `-lswiftCompatibilityPacks`.
  - `scripts/build_m3_unityframework.sh` now fails fast when the Unity export
    log contains `Build Finished, Result: Failure` or
    `Unity iOS export result: Failed`.
  - New verifier:
    `python3 scripts/e7_reference_atlas/verify_unityframework_build_contract.py`.
- UnityFramework attempt 3 passed with `TIMESTAMP=eyebrow-20260627-ufw-r3`.
  The artifact verification recorded arm64 `UnityFramework.framework` in both
  RN and package-local paths, with Unity `Data` copied into the framework.
- RN/Xcode Debug build for `CloudsiPhone (26.5)` passed:
  `evidence/logs/eyebrow-rn-xcodebuild-device-20260627.log`.
- `devicectl` installed `com.celeste.makeupar.validation`:
  `evidence/logs/eyebrow-rn-devicectl-install-20260627.log`.
- `devicectl` launched `com.celeste.makeupar.validation`:
  `evidence/logs/eyebrow-rn-devicectl-launch-20260627.log`.
- Local build product inspection confirmed:
  - App bundle size about `195M`.
  - Embedded `UnityFramework.framework` about `116M`.
  - Embedded Unity `Data` about `20M`.
  - `RNBridge` and `MakeupRegionRendererRoutes` are present.
  - Unity resource `brow-drawn-mask-v1` is present.
  - RN bundle contains `natural_brow`, `soft_brow`,
    `brow-drawn-mask-v1`, `regionMaskTriangles`, and `rendererId`.

Remaining:

- User visual QA on the launched iPhone build: brow placement, attachment under
  head turn, expression behavior, opacity/intensity/color response, tracking
  recovery, and lip/cheek/eye smoke check.
- Decide whether explicit left/right asymmetry controls are required before
  calling the eyebrow module complete.
- First user QA on the launched build confirmed the runtime path is working but
  the brow art direction needs tuning:
  - `natural_brow`, `soft_brow`, opacity, and intensity controls work.
  - Brow attachment is stable during left/right head turns and expression
    changes.
  - Brow placement is near the eyebrow line.
  - The shape reads as `^ ^`; the center of each brow is the highest point.
  - The stroke is much too thick and sticker-like.
- Tuning checkpoint before the next build:
  - `verify_brow_mask_texture.py` was tightened to fail the installed mask's
    thickness and central-arch shape.
  - RED: old mask failed with `Unexpected active pixels: 11205`.
  - RN RED: focused Jest failed because `natural_brow` still used intensity
    `0.58` instead of the new softer default.
  - Generator update flattened the cubic brow curves, reduced strokes from
    `34/24/13px` to `20/13/6px`, removed the hard upper highlight stroke, and
    increased blur from `1.7` to `2.3`.
  - GREEN: mask verifier passed with `5845` active pixels, `0.022297`
    coverage, bbox `left=112,top=100,right=399,bottom=130,width=288,height=31`,
    center rise about `4.4px`, and zero overlap with eye/cheek/lip masks.
  - GREEN: RN focused Jest passed with 23 tests after lowering `natural_brow`
    default opacity/intensity/coverage to `0.48/0.48/0.54`.
  - The tuned mask has not yet been rebuilt into `UnityFramework.framework` or
    reinstalled on the iPhone.
- 2026-06-27: User chose not to apply the intermediate flatter/thinner mask to
  the real device and asked to proceed directly into the next loop.
- 2026-06-27: Local texture loop added subtle procedural brow density.
  - Goal: reduce remaining sticker feel from a single smooth grey strip before
    the eventual device rebuild.
  - RED: `verify_brow_mask_texture.py` failed the smooth intermediate mask with
    `left brow center is too smooth or too patchy:
    {'centerPeakRange': 2.0, 'centerPeakMeanStep': 0.2}`.
  - Generator update changed the brow mask to a lower-alpha powder base plus
    deterministic short fine strokes and longitudinal density variation.
  - GREEN: mask verifier passed with `5123` active pixels, `0.019543`
    coverage, bbox `left=113,top=101,right=398,bottom=129,width=286,height=29`,
    center rise about `4.3px`, texture peak range `51/43`, and zero overlap
    with eye/cheek/lip masks.
  - This texture loop is local only; no UnityFramework/RN device build was
    started.
- 2026-06-27: User clarified that brow-front direction does not need its own
  separate option and asked to apply three options from the generated variation
  sheet.
  - Selected local candidates: `0202` soft arch/fine hair,
    `0307` back arch/soft mix, and `0602` slim tail/fine hair.
  - Added Unity Resources assets: `brow-soft-arch-fine-hair-v1`,
    `brow-back-arch-soft-mix-v1`, and `brow-slim-tail-fine-hair-v1`.
  - RN/Unity default brow mask is now `brow-soft-arch-fine-hair-v1`; the other
    two candidates and legacy `brow-drawn-mask-v1` remain selectable in the HUD.
  - RED: focused Jest failed because brow payload/HUD still used
    `brow-drawn-mask-v1`; `verify_brow_unity_contract.py` failed because the
    new Unity resource was missing.
  - GREEN: focused Jest passed with 23 tests, brow Unity contract verifier
    passed, and all three selected masks passed `verify_brow_mask_texture.py`
    with zero eye/cheek/lip overlap.
  - This candidate-selection loop is local only; no UnityFramework/RN device
    build was started.
- 2026-06-27: User connected `CloudsiPhone`; after approval, the three-candidate
  build was regenerated, installed, and launched.
  - UnityFramework build: `eyebrow-options-20260627-ufw-r1`, passed.
  - RN Debug build, `devicectl` install, and launch passed for
    `com.celeste.makeupar.validation`.
  - Build product inspection confirmed the RN bundle includes
    `brow-soft-arch-fine-hair-v1`, `brow-back-arch-soft-mix-v1`, and
    `brow-slim-tail-fine-hair-v1`.
- 2026-06-27: User QA on that installed build confirmed attachment quality but
  found visual/color issues.
  - Passed: left/right head turns and expression changes stay attached.
  - Needs tuning: brow is too faint, especially `soft_brow`.
  - Needs placement tuning: brows are too centered and slightly below the real
    eyebrow line.
  - Needs UI tuning: brow color choices still use lip colors.
- 2026-06-27: Local post-QA tuning response.
  - RED: focused Jest failed because brow still used lip colors and low
    `0.48` default intensity/opacity; mask verifier failed because default
    candidate bbox top was `102`, below the new placement guard.
  - RN update adds brow-specific color options (`ash_brown`, `neutral_brown`,
    `dark_brown`, `soft_black`) and raises default `natural_brow` to opacity
    `0.68`, intensity `0.68`, and coverage `0.62`; `soft_brow` intensity is
    raised to `0.56`.
  - Mask update shifts the three selected candidates `10px` outward per side and
    `7px` upward without increasing thickness.
  - GREEN: focused Jest passed with 23 tests; all three selected masks passed
    placement/overlap verification. This post-QA local tuning is not yet
    installed on-device.
- 2026-06-27: Local brow color parameter loop.
  - RED: focused Jest failed because brow `colorWarmth`/`colorDepth` values did
    not affect the outgoing layer color and because the brow HUD had no
    `Warmth`/`Depth` controls.
  - RN update adds optional `colorWarmth` and `colorDepth` recipe parameters,
    computes the final brow hex color before sending Unity's existing `color`
    field, and shows brow-only `Warmth`/`Depth` sliders in the HUD.
  - Default values are neutral `0.50/0.50`, so the existing `neutral_brown`
    default remains `#4A342B`; one test probe verifies `Warmth 0.75` and
    `Depth 0.80` produce `#422C1E`.
  - GREEN: focused Jest passed with 24 tests; lint, TypeScript, brow Unity
    contract, renderer routes, and UnityFramework build contract passed. This
    local color-parameter tuning is not yet installed on-device.
- 2026-06-27: Local brow placement parameter loop.
  - RED: focused Jest failed because brow `maskOffsetX`/`maskOffsetY` were not
    present in the outgoing payload and the HUD had no `Brow X`/`Brow Y`
    controls; `verify_brow_unity_contract.py` failed because Unity did not
    accept or apply mask offsets.
  - RN update adds brow placement controls and sends signed mask offsets with
    each region layer. Default offset is `0/0`, with the HUD centered at `0.50`.
  - Unity update adds `maskOffsetX`/`maskOffsetY` to the bridge parser,
    `E3RegionMaskOverlay` recipe/result state, and the smooth mask shader's
    `_MaskOffset` UV sampling property.
  - GREEN: focused Jest passed with 25 tests; lint, TypeScript, brow Unity
    contract, renderer routes, and Unity batchmode import/compile passed with
    `evidence/logs/eyebrow-mask-offset-unity-batchmode-20260627.log`. This
    local placement-parameter tuning is not yet installed on-device.
- 2026-06-27: Corrected brow horizontal placement semantics before reinstall.
  - RED: focused Jest failed because `maskSpreadX` was absent from the payload
    and the HUD still showed `Brow X`; `verify_brow_unity_contract.py` failed
    because Unity did not accept or apply `maskSpreadX`.
  - RN update changes the horizontal control to `Brow Spread`, sending signed
    `maskSpreadX` for symmetric inward/outward tuning while keeping `Brow Y` as
    vertical `maskOffsetY`.
  - Unity update parses `maskSpreadX`, stores `MaskSpreadX`, sends it to the
    shader as `_MaskSpreadX`, and samples the mask around the UV centerline so
    positive spread moves the left and right brows apart instead of translating
    the whole mask sideways.
  - GREEN: focused Jest passed with 25 tests; lint, TypeScript, brow Unity
    contract, renderer routes, UnityFramework build contract, and Unity
    `6000.3.18f1` batchmode import/compile passed with
    `evidence/logs/eyebrow-mask-spread-unity-batchmode-20260627.log`. This
    local spread correction is not yet installed on-device.
- 2026-06-27: Added brow placement diagnostics before reinstall.
  - RED: focused Jest failed because the RN `recipe_applied` summary did not
    show `spread=`/`y=`, and `verify_brow_unity_contract.py` failed because
    Unity `recipe_applied` events/logs did not emit applied `maskSpreadX` and
    `maskOffsetY`.
  - Unity now emits the post-clamp applied placement values in `recipe_applied`
    JSON and Debug logs; RN summarizes them as `spread=` and `y=` so device QA
    can confirm control delivery without raw frame capture.
  - GREEN: focused Jest passed with 26 tests; lint, TypeScript, brow Unity
    contract, renderer routes, UnityFramework build contract, scoped
    `git diff --check`, and Unity `6000.3.18f1` batchmode import/compile passed
    with `evidence/logs/eyebrow-placement-diagnostics-unity-batchmode-20260627.log`.
- 2026-06-27: User approved approach 1: proceed with the current local
  post-QA tuning as the next iPhone rebuild candidate, rather than adding
  left/right asymmetry controls or splitting a dedicated brow renderer first.
  This approval confirms direction only; Unity/RN real-device build approval is
  still a separate gate.
  - Refreshed approval-safe local checks before the build gate:
    `verify_brow_unity_contract.py`, `verify_region_renderer_routes.py`,
    `verify_unityframework_build_contract.py`, focused RN Jest (`26` tests),
    RN lint, TypeScript, and all three selected brow mask verifiers passed.
  - Disk had `73Gi` free on `/System/Volumes/Data`.
  - Unity `6000.3.18f1` batchmode import/compile exited `0` and logged
    `Tundra build success` in
    `evidence/logs/eyebrow-prebuild-refresh-unity-batchmode-20260627.log`.
  - Unity rewrote whitespace-only empty YAML fields in the three brow PNG
    `.meta` files during import; those agent-created metadata churn changes
    were reverted because they did not affect importer settings.
- 2026-06-27: User approved the real-device rebuild for approach 1, and the
  current post-QA tuning was regenerated, installed, and launched.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-rebuild-20260627-ufw-r1`.
  - Unity export/build/artifact evidence:
    `evidence/logs/m3-repro-unity-export-eyebrow-rebuild-20260627-ufw-r1.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-eyebrow-rebuild-20260627-ufw-r1.log`,
    and
    `evidence/logs/m3-repro-artifact-verification-eyebrow-rebuild-20260627-ufw-r1.log`.
    Verification recorded `119M` UnityFramework copies and `23M` `Data`
    folders in both RN and package-local locations.
  - RN/Xcode Debug build attempt 1 failed with exit `65` because ignored
    CocoaPods support files still referenced an old Dropbox checkout path for
    `Pods/React-Core-prebuilt/React-VFS.yaml`.
  - Running `pod install --no-repo-update` from `rn/MakeupARValidation/ios`
    refreshed the local Pod support files without changing tracked source.
  - RN/Xcode Debug build attempt 2 passed with
    `evidence/logs/eyebrow-rn-xcodebuild-device-rebuild-20260627-r2.log`.
    The built app bundle is `198M`, including `119M`
    `UnityFramework.framework` and `23M` `UnityFramework.framework/Data`.
  - First `devicectl` install by device name failed with a transient CoreDevice
    connection invalidation; retry by the approved device identifier passed:
    `evidence/logs/eyebrow-rn-devicectl-install-rebuild-20260627-r2.log`.
  - Launch passed:
    `evidence/logs/eyebrow-rn-devicectl-launch-rebuild-20260627.log`.
  - No face screenshots, recordings, or raw camera frames were captured.
  - Next gate: user iPhone visual QA must check brow visibility, placement,
    shape, color, `Warmth`/`Depth`, `Brow Spread`/`Brow Y`, tracking recovery,
    and lip/cheek/eye smoke behavior before calling the module complete.
- 2026-06-27: User QA feedback on `eyebrow-rebuild-20260627-ufw-r1`.
  - Confirmed: `spread=` and `y=` are visible and `Brow Spread`/`Brow Y`
    adjustments apply.
  - Clarified: `renderer=brow-smooth-region-mask-renderer` was hard to find; it
    only appeared inside the long `recipe_applied` summary.
  - Needs tuning: brow remains too faint, too centered, and angled upward enough
    to read as angry. `Warmth`/`Depth` were not useful while visibility was too
    low.
  - RED: focused Jest failed after adding expectations for a `0.75/0.75`
    default brow, `brow-back-arch-soft-mix-v1` as default, outward
    `maskSpreadX=0.20`, visible `Renderer ...` compact HUD row, clearer
    `Ash/Warm` and `Light/Dark` labels, and removal of the high-arch/legacy
    brow mask options from the user-facing picker.
  - RN update makes `Soft flat` (`brow-back-arch-soft-mix-v1`) the default,
    leaves only `Soft flat` and `Slim tail fine` in the brow mask picker,
    starts opacity/intensity at `0.75`, starts spread at `0.20`, expands
    slider-to-Unity spread range to `±0.34`, renames visible color controls to
    `Ash/Warm` and `Light/Dark`, and adds a separate compact HUD
    `Renderer ...` line plus `mask=... spread=... y=...`.
  - Unity update matches the wider `maskSpreadX` clamp in both `RNBridge` and
    `E3RegionMaskOverlay`, changes the Unity default brow mask id to
    `brow-back-arch-soft-mix-v1`, and raises brow alpha response so `75%`
    should be readable while `100%` can be deliberately strong.
  - Verifier update changes the default brow mask guard to
    `brow-back-arch-soft-mix-v1`, tightens the top-edge arch guard to reduce the
    `^ ^`/angry read, and separates user-facing mask options from compatibility
    mask resources.
  - GREEN: focused RN Jest passed with 26 tests; brow Unity contract, brow mask
    texture verifier, and region renderer route verifier passed locally. That
    checkpoint happened before the later PNG/bright brow install, which now
    includes this follow-up tuning.
  - Unity `6000.3.18f1` batchmode import/compile was attempted twice after
    confirming no Unity Editor/Hub/Licensing process was active. Both attempts
    failed before compile at Licensing Client IPC initialization:
    `evidence/logs/eyebrow-followup-unity-batchmode-20260627.log` and
    `evidence/logs/eyebrow-followup-unity-batchmode-20260627-r2.log`.
    The Unity/Licensing processes started by those attempts were terminated.
- 2026-06-27: Brow QA panel and Guide/Mesh recovery loop.
  - User clarified that the validation panel must work like an internal makeup
    SDK console, not a pile of developer-only parameters. The user also
    clarified that `Ash/Warm` and `Light/Dark` should not replace the visible
    controls; the panel should say `Temperature` and `Depth`, and debug stages
    should read `RAW`, `PROCESSED`, `FINAL` in that order.
  - RED: focused RN Jest failed until the panel exposed `Debug View`,
    `RAW/PROCESSED/FINAL` in order, `Brow QA`, `Color`, `Placement`,
    `Temperature`, `Depth`, no legacy drawn option, and Guide/Mesh toggle logs
    that no longer claim the face debug surface is suppressed while mesh is on.
    The Unity contract verifier failed until `RNBridge` actually applied
    `faceMeshVisible` instead of forcing mesh overlay off.
  - Root cause for the non-working Mesh button: RN sent
    `meshOverlayVisible=true`, but Unity `SetE7RegionOverlayVisibleJson` called
    `SetFaceMeshOverlayVisible(false)`, and that method ignored its parameter.
  - GREEN: RN focused Jest passed with 26 tests; `verify_brow_unity_contract.py`
    and `verify_region_renderer_routes.py` passed; TypeScript and RN lint
    passed. Unity `6000.3.18f1` batchmode import/compile passed with
    `evidence/logs/eyebrow-qa-panel-guide-mesh-unity-batchmode-20260627.log`
    (`CompileScripts: 2954.854ms`, `Exiting batchmode successfully now!`).
  - Hand/occlusion handling is a real SDK requirement, but it is not part of
    this loop. It needs a separate occlusion track so hand, hair, glasses, or
    other foreground objects can remove makeup only where they cover the face.
- 2026-06-27: PNG-derived brow hair texture loop.
  - User confirmed the supplied `brow_daily.png`, `brow_natural.png`,
    `brow_narrow.png`, and `brow_lightbrown.png` are self-authored.
  - Direction chosen: do not multiply the full source PNG over the face.
    Instead, preprocess the art into Unity 512x512 alpha/detail textures and
    keep the brow color as a separate recipe color layer.
  - RED: focused Jest failed because `light_brown`, PNG brow mask options, and
    `detailAmount` were absent; `verify_brow_png_hair_textures.py` failed
    because the generated PNG hair resources were missing.
  - GREEN: generated `brow-png-daily-hair-v1`,
    `brow-png-natural-hair-v1`, `brow-png-narrow-hair-v1`, and
    `brow-png-lightbrown-hair-v1` plus matching `.meta` files. RN now exposes
    `Daily hair`, `Natural hair`, `Narrow hair`, `Light brown`,
    `light_brown`, and `Texture Detail`; Unity parses `detailAmount` and
    passes it to `_DetailAmount` in `SmoothRegionMask.shader`.
  - Verification passed: full RN Jest `27/27`, `npx tsc --noEmit`,
    `npm run lint`, `verify_brow_png_hair_textures.py`,
    `verify_brow_mask_texture.py`, `verify_brow_unity_contract.py`, and
    `verify_region_renderer_routes.py`.
  - Initial Unity batchmode attempts accidentally used Unity `2022.3.62f1` and
    failed before C# compile during package resolution because the project is
    pinned to Unity `6000.3.18f1` and AR Foundation `6.3.5` expects Unity 6-era
    package dependencies. Logs:
    `evidence/logs/eyebrow-png-hair-texture-unity-batchmode-20260627.log` and
    `evidence/logs/eyebrow-png-hair-texture-unity-batchmode-20260627-rerun.log`.
    The automatic `packages-lock.json` downgrade from those failed attempts was
    restored.
  - GREEN: rerunning with the project editor, Unity `6000.3.18f1`, passed
    batchmode import/compile. Log:
    `evidence/logs/eyebrow-png-hair-texture-unity6000-batchmode-20260627.log`.
    It includes `Tundra build success`, `CompileScripts: 4786.690ms`, imports
    for all four `brow-png-*` textures, and `Exiting batchmode successfully now!`.
  - No UnityFramework/iPhone build was run in this loop.
- 2026-06-27: Bright PNG brow blend split.
  - RED: focused Jest failed because `light_brown` plus
    `brow-png-daily-hair-v1` still emitted `blendMode="multiply"`.
  - GREEN: RN now emits `blendMode="normal"` only for `light_brown` with
    PNG-derived brow hair masks, while darker PNG brow colors continue to emit
    `blendMode="multiply"`. `detailAmount` remains active in both paths.
  - Verification passed: full RN Jest `28/28`, `npx tsc --noEmit`,
    `npm run lint`, `verify_brow_unity_contract.py`, and
    `verify_brow_png_hair_textures.py`.
  - No UnityFramework/iPhone build was run in this loop.
- 2026-06-27: User chose to install the current PNG/bright brow build on the
  iPhone before starting the next auto-placement loop, then approved the
  real-device build/install.
  - Pre-build checks passed: full RN Jest (`28` tests), TypeScript, RN lint,
    `verify_brow_unity_contract.py`, `verify_brow_png_hair_textures.py`, and
    `verify_brow_mask_texture.py`.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-png-bright-20260627-ufw-r1`.
  - Artifact verification recorded `123M` UnityFramework copies and `27M`
    `Data` folders in both RN and package-local locations:
    `evidence/logs/m3-repro-artifact-verification-eyebrow-png-bright-20260627-ufw-r1.log`.
  - RN/Xcode Debug build attempt 1 failed with exit `65` because generated
    CocoaPods support files still pointed `HERMES_CLI_PATH` at an old Dropbox
    checkout.
  - The generated/ignored Pod support files were corrected locally to the
    current checkout, then RN/Xcode Debug build attempt 2 passed:
    `evidence/logs/eyebrow-rn-xcodebuild-device-png-bright-20260627-r2.log`.
  - Built app bundle:
    `unity-builds/xcode-derived-data/RNDevice-eyebrow-png-bright-20260627-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
    `202M`, including `123M` `UnityFramework.framework` and `27M`
    `UnityFramework.framework/Data`.
  - `devicectl` installed and launched `com.celeste.makeupar.validation` on
    `CloudsiPhone (26.5)`:
    `evidence/logs/eyebrow-rn-devicectl-install-png-bright-20260627.log` and
    `evidence/logs/eyebrow-rn-devicectl-launch-png-bright-20260627.log`.
  - No face screenshots, recordings, or raw camera frames were captured.
  - Next gate: user iPhone visual QA on the installed PNG/bright brow build.
    Any quality feedback starts a new agreement proposal before implementation.
- 2026-06-27: Daily-flat PNG texture fidelity A/B loop.
  - User supplied self-authored `brow_dailyflat.png` and approved the proposed
    texture-fidelity loop.
  - RED: focused RN Jest failed because the default brow mask was still
    `brow-back-arch-soft-mix-v1`, flat PNG A/B labels were absent, and
    `light_brown` with the new sharp/multiply probes did not route to the
    expected blend modes. `verify_brow_png_hair_textures.py` and
    `verify_brow_unity_contract.py` failed because the new daily-flat assets and
    Unity texture ids were missing.
  - First generated sharp texture carried a source-image vertical artifact; the
    verifier was tightened to reject stray low-alpha pixels outside the brow
    components.
  - GREEN: generator now supports `dailyflat` source extraction, `--only`
    output selection, bright-on-dark hair scoring, component-based brow crop
    selection, and three generated Unity resources:
    `brow-png-dailyflat-hair-v1`, `brow-png-dailyflat-sharp-v1`, and
    `brow-png-dailyflat-multiply-v1`.
  - RN now defaults brow mask selection to `Flat sharp`, exposes `Daily flat`,
    `Flat sharp`, and `Flat multiply`, raises default `Texture Detail` to
    `0.68`, keeps light-brown PNG hair on normal composition except for the
    explicit `Flat multiply` probe, and verifies this with focused Jest.
  - Unity `RNBridge` and `E3RegionMaskOverlay` accept the new ids and default to
    `brow-png-dailyflat-sharp-v1`. `SmoothRegionMask.shader` now preserves a
    sharper `hairNeedle` signal and strengthens extracted PNG brow detail.
  - Verification passed: full RN Jest (`29` tests), `npx tsc --noEmit`,
    `npm run lint`, `verify_brow_png_hair_textures.py`,
    `verify_brow_unity_contract.py`, `verify_brow_mask_texture.py`,
    `verify_region_renderer_routes.py`, and
    `verify_unityframework_build_contract.py`.
  - Unity `6000.3.18f1` batchmode import/compile first failed before compile
    because Unity Licensing IPC timed out in the sandboxed run. Log:
    `evidence/logs/eyebrow-dailyflat-png-unity6000-batchmode-20260627.log`.
    The Unity/Licensing processes started by that attempt were terminated.
  - Retrying Unity batchmode with elevated permissions passed with `Tundra build
    success`, imported the three `brow-png-dailyflat-*` textures, and exited
    successfully:
    `evidence/logs/eyebrow-dailyflat-png-unity6000-batchmode-20260627-r2.log`.
  - User approved the real-device daily-flat build/install.
  - Pre-build checks passed again: full RN Jest (`29` tests), TypeScript, RN
    lint, `verify_brow_png_hair_textures.py`,
    `verify_brow_unity_contract.py`, `verify_brow_mask_texture.py`,
    `verify_region_renderer_routes.py`, and
    `verify_unityframework_build_contract.py`.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-dailyflat-20260627-ufw-r1`.
  - Artifact verification recorded `126M` UnityFramework copies and `30M`
    `Data` folders in both RN and package-local locations:
    `evidence/logs/m3-repro-artifact-verification-eyebrow-dailyflat-20260627-ufw-r1.log`.
  - RN/Xcode Debug build passed:
    `evidence/logs/eyebrow-rn-xcodebuild-device-dailyflat-20260627-r1.log`.
  - Built app bundle:
    `unity-builds/xcode-derived-data/RNDevice-eyebrow-dailyflat-20260627-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
    `205M`, including `126M` `UnityFramework.framework` and `30M`
    `UnityFramework.framework/Data`.
  - `devicectl` installed and launched `com.celeste.makeupar.validation` on
    `CloudsiPhone (26.5)`:
    `evidence/logs/eyebrow-rn-devicectl-install-dailyflat-20260627-r1.log` and
    `evidence/logs/eyebrow-rn-devicectl-launch-dailyflat-20260627-r1.log`.
  - No face screenshots, recordings, or raw camera frames were captured.
  - Next gate: user iPhone visual QA on the installed daily-flat A/B build.
    Any quality feedback starts a new agreement proposal before implementation.
- 2026-06-27: Flat-fill/soft-brow local follow-up after daily-flat QA.
  - User QA found the flat daily candidates showed mostly outlines with hollow
    centers, while `Daily hair`/`Natural hair`/`Narrow hair` were visible but
    still paint-like. Switching `natural_brow`/`soft_brow` reset the selected
    mask to `Flat sharp`, the two brows looked too close together, and
    `soft_brow` appeared invisible.
  - RED: focused RN Jest failed because switching to `soft_brow` reset the
    selected brow mask. `verify_brow_png_hair_textures.py` failed the
    daily-flat assets with `center gap too narrow: 29px`.
  - Generator update moves the flat PNG targets outward and fills vertical
    alpha gaps for the flat silhouette while keeping extracted hair detail in
    the detail channel. The verifier now rejects daily-flat center gaps under
    `44px` and hollow interior fill under `0.72`.
  - RN update preserves the selected brow mask, spread, Y offset, texture
    detail, and preserve-detail settings when switching between
    `natural_brow` and `soft_brow`. The default brow spread is raised from
    `0.20` to `0.24`.
  - `soft_brow` is raised to intensity/coverage `0.75/0.62`, and Unity now
    maps `soft_brow` alpha with
    `sampleAlphaScale = Mathf.Lerp(0.58f, 0.94f, recipe.Intensity)`.
  - GREEN: focused RN Jest passed, then full RN Jest passed with `30` tests.
    TypeScript, RN lint, `verify_brow_png_hair_textures.py`,
    `verify_brow_unity_contract.py`, `verify_brow_mask_texture.py`,
    `verify_region_renderer_routes.py`, and
    `verify_unityframework_build_contract.py` passed.
  - Unity `6000.3.18f1` batchmode import/compile passed with
    `evidence/logs/eyebrow-flat-fill-softbrow-unity6000-batchmode-20260627.log`.
  - At this checkpoint the follow-up was local only. No UnityFramework
    regeneration, RN/Xcode device build, install, launch, screenshots,
    recordings, or raw camera frames were run before the separate build approval
    below.
- 2026-06-27: User approved the flat-fill/soft-brow iPhone build/install.
  - Pre-build checks passed: PNG brow hair verifier, brow Unity contract
    verifier, and UnityFramework build contract verifier.
  - Device check found `CloudsiPhone` connected as
    `FD44CD30-B236-5594-BE61-3C5D408A6851`.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-flatfill-softbrow-20260627-ufw-r1`.
  - Artifact verification recorded `126M` UnityFramework copies and `30M`
    `Data` folders in both RN and package-local locations:
    `evidence/logs/m3-repro-artifact-verification-eyebrow-flatfill-softbrow-20260627-ufw-r1.log`.
  - RN/Xcode Debug build passed:
    `evidence/logs/eyebrow-rn-xcodebuild-device-flatfill-softbrow-20260627-r1.log`.
  - Built app bundle:
    `unity-builds/xcode-derived-data/RNDevice-eyebrow-flatfill-softbrow-20260627-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
    `205M`, including `126M` `UnityFramework.framework` and `30M`
    `UnityFramework.framework/Data`.
  - `devicectl` installed and launched `com.celeste.makeupar.validation` on
    `CloudsiPhone (26.5)`:
    `evidence/logs/eyebrow-rn-devicectl-install-flatfill-softbrow-20260627-r1.log`
    and
    `evidence/logs/eyebrow-rn-devicectl-launch-flatfill-softbrow-20260627-r1.log`.
  - No face screenshots, recordings, raw camera frames, or Slack messages were
    captured/sent.
  - Next gate: user iPhone visual QA on the installed flat-fill/soft-brow
    build. Any quality feedback starts a new agreement proposal before
    implementation.
- 2026-06-27: Flat non-filled PNG retune after flat-fill iPhone QA.
  - User QA on the installed flat-fill/soft-brow build found the FLAT candidates
    still hollow inside. The important new clue is that `Daily hair`,
    `Natural hair`, and `Narrow hair` render, so the likely root cause is the
    FLAT-only generation pipeline rather than the shared shader path.
  - User also confirmed the brow gap is still too narrow.
  - RED: focused RN Jest failed because default `maskSpreadX` was still `0.24`
    instead of the wider `0.28`. `verify_brow_png_hair_textures.py` failed
    because the daily-flat generator still used `fill_vertical_gaps=True`, the
    FLAT-only solid-fill path.
  - Generator update removes the FLAT-only vertical fill and lowers FLAT
    `shape_filter_size` back to the same non-filled alpha/detail extraction
    family used by the visible non-flat PNG hair candidates. The FLAT target
    boxes were also moved outward.
  - RN update raises default brow `maskSpreadX` from `0.24` to `0.28`.
  - GREEN: focused RN Jest passed, then full RN Jest passed with `30` tests.
    TypeScript, RN lint, `verify_brow_png_hair_textures.py`,
    `verify_brow_unity_contract.py`, `verify_brow_mask_texture.py`,
    `verify_region_renderer_routes.py`, and
    `verify_unityframework_build_contract.py` passed.
  - The updated PNG verifier records `brow-png-dailyflat-sharp-v1` with
    `4187` active pixels, bbox `left=85,right=427,height=34`, and detailStd
    `72.75`.
  - Unity `6000.3.18f1` batchmode import/compile passed with
    `evidence/logs/eyebrow-flat-nonfilled-pipeline-unity6000-batchmode-20260627.log`.
  - This follow-up is local only. No UnityFramework regeneration, RN/Xcode
    device build, install, launch, screenshots, recordings, raw camera frames,
    or Slack messages were run/sent in this loop.
- 2026-06-27: User approved the flat non-filled PNG iPhone build/install.
  - Pre-build checks passed: PNG brow hair verifier, brow Unity contract
    verifier, brow mask texture verifier, region renderer route verifier, and
    UnityFramework build contract verifier.
  - Device check found `CloudsiPhone` connected as
    `FD44CD30-B236-5594-BE61-3C5D408A6851`.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-flatnonfilled-20260627-ufw-r1`.
  - Artifact verification recorded `126M` UnityFramework copies and `30M`
    `Data` folders in both RN and package-local locations:
    `evidence/logs/m3-repro-artifact-verification-eyebrow-flatnonfilled-20260627-ufw-r1.log`.
  - RN/Xcode Debug build passed:
    `evidence/logs/eyebrow-rn-xcodebuild-device-flatnonfilled-20260627-r1.log`.
  - Built app bundle:
    `unity-builds/xcode-derived-data/RNDevice-eyebrow-flatnonfilled-20260627-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
    `205M`, including `126M` `UnityFramework.framework` and `30M`
    `UnityFramework.framework/Data`.
  - `devicectl` installed and launched `com.celeste.makeupar.validation` on
    `CloudsiPhone (26.5)`:
    `evidence/logs/eyebrow-rn-devicectl-install-flatnonfilled-20260627-r1.log`
    and
    `evidence/logs/eyebrow-rn-devicectl-launch-flatnonfilled-20260627-r1.log`.
  - No face screenshots, recordings, raw camera frames, or Slack messages were
    captured/sent.
  - User QA on this installed build still found `Daily flat`, `Flat sharp`, and
    `Flat multiply` hollow inside.
- 2026-06-28: Source-2 FLAT fill fix after hollow iPhone QA.
  - User supplied `brow_dailyflat_2.png`; local diagnostics showed the previous
    FLAT source generated inner fill around `0.42..0.49`, while source-2
    generates `Flat sharp` inner fill `0.822/0.932`.
  - RED: `verify_brow_png_hair_textures.py` failed the old generated FLAT
    texture with `left brow interior is too hollow for device rendering`.
  - Regenerated `Daily flat`, `Flat sharp`, and `Flat multiply` from
    `brow_dailyflat_2.png` and updated the verifier so hollow FLAT interiors
    cannot pass again.
  - GREEN: PNG hair verifier, brow Unity contract verifier, brow mask texture
    verifier, region renderer route verifier, and UnityFramework build contract
    verifier passed.
  - Unity `6000.3.18f1` batchmode import/compile passed with
    `evidence/logs/eyebrow-flat2-filled-texture-unity6000-batchmode-20260628.log`.
  - This source-2 fix is local only. No UnityFramework regeneration, RN/Xcode
    device build, install, launch, screenshots, recordings, raw camera frames,
    or Slack messages were run/sent in this loop.
- 2026-06-28: Gap/Angle/Arch placement controls and region-scoped tuning panel.
  - User approved the loop to expose intuitive brow placement controls, preserve
    them across `natural_brow`/`soft_brow` preset switches, and show only
    region-relevant tuning controls while editing lip or brow.
  - RN adds `Gap`, `Angle`, and `Arch` sliders beside the existing `Brow Y`
    control. `Gap` is sent as both `maskSpreadX` and `browGap` for compatibility;
    `Angle` and `Arch` are sent as `browAngle` and `browArch`. The selected brow
    mask and all placement/detail values now survive brow preset switches.
  - Unity `RNBridge` parses `browGap`, `browAngle`, and `browArch`, clamps them
    conservatively, passes them into `E3RegionMaskOverlay`, and emits them back
    through `recipe_applied` diagnostics. `SmoothRegionMask.shader` applies gap
    through the existing spread path and applies a small brow-only UV sampling
    warp for angle and arch.
  - GREEN: RN Jest passed with `31/31` tests. TypeScript, RN lint,
    `verify_brow_png_hair_textures.py`, `verify_brow_unity_contract.py`,
    `verify_brow_mask_texture.py`, `verify_region_renderer_routes.py`, and
    `verify_unityframework_build_contract.py` passed.
  - Unity `6000.3.18f1` batchmode import/compile passed with
    `evidence/logs/eyebrow-gap-angle-arch-unity6000-batchmode-20260628.log`;
    the log has no C# compiler error or shader error. Non-fatal shutdown
    messages include Licensing token update, Curl callback abort, and usbmuxd
    shutdown output after successful batchmode quit.
  - This loop is local only. No UnityFramework regeneration, RN/Xcode device
    build, install, launch, screenshots, recordings, raw camera frames, or Slack
    messages were run/sent.
- 2026-06-28: Brow visual feedback retune and Arch Position control.
  - User QA feedback found `Soft flat` and `Slim tail fine` nearly invisible;
    `Daily flat`, `Flat sharp`, and `Flat multiply` too long and visually
    hollow; PNG hair candidates visible but too paint-like; `natural_brow` and
    `soft_brow` unclear; and requested a parameter that moves only the brow
    mountain forward/back. User also clarified that `coverage` and `feather`
    should remain available for brow.
  - RED: focused RN Jest failed because the default brow mask/detail, distinct
    `natural_brow`/`soft_brow` values, `browArchPosition`, and region-scoped
    brow panel expectations were not implemented. The Unity contract verifier
    failed on missing `browArchPosition`; the procedural mask verifier failed
    after visibility boosting exposed a too-pointed top edge for `Soft flat`.
  - RN now defaults brow to `Natural hair`
    (`brow-png-natural-hair-v1`), labels the presets as `Natural` and
    `Soft Powder`, keeps selected mask/placement values across preset switches,
    adds `Arch Position`, and scopes controls so brow shows texture, placement,
    `Coverage`, and `Feather` while hiding lip/material finish controls.
  - Unity `RNBridge`, `E3RegionMaskOverlay`, and `SmoothRegionMask.shader`
    parse, clamp, apply, and log `browArchPosition`. Positive values move the
    brow mountain toward the tail; negative values move it toward the inner
    brow.
  - Texture retune shortens/fills the three flat PNG candidates, boosts
    `Soft flat` and `Slim tail fine`, softens the top edge of `Soft flat`, and
    reduces PNG hair detail harshness in both the blue detail channel and shader
    response.
  - GREEN: focused RN Jest passed with `31/31`; TypeScript and RN lint passed;
    brow Unity contract verifier, PNG brow hair verifier, procedural mask
    verifiers for `brow-back-arch-soft-mix-v1` and
    `brow-slim-tail-fine-hair-v1`, region renderer route verifier, and
    UnityFramework build contract verifier passed.
  - Unity `6000.3.18f1` batchmode import/compile was attempted, but did not
    reach compile because Unity Licensing IPC failed waiting for
    `LicenseClient-hi`. The hung batchmode process was interrupted and the
    spawned `Unity.Licensing.Client` process was terminated. Log:
    `evidence/logs/eyebrow-feedback-retune-unity6000-batchmode-20260628.log`.
  - User then approved a minimal required-file build. Unity/Hub/Licensing
    processes were clear before build; `CloudsiPhone` was connected as
    `FD44CD30-B236-5594-BE61-3C5D408A6851`.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-feedback-retune-20260628-ufw-r1`. Artifact verification
    recorded `126M` UnityFramework copies and `30M` `Data` folders in both RN
    and package-local paths:
    `evidence/logs/m3-repro-artifact-verification-eyebrow-feedback-retune-20260628-ufw-r1.log`.
  - RN/Xcode Debug build passed:
    `evidence/logs/eyebrow-rn-xcodebuild-device-feedback-retune-20260628-r1.log`.
    Built app bundle:
    `unity-builds/xcode-derived-data/RNDevice-eyebrow-feedback-retune-20260628-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
    `205M`, including `126M` `UnityFramework.framework` and `30M`
    `UnityFramework.framework/Data`.
  - `devicectl` installed `com.celeste.makeupar.validation` on `CloudsiPhone`:
    `evidence/logs/eyebrow-rn-devicectl-install-feedback-retune-20260628-r1.log`.
  - App launch was not run in this minimal build loop. No screenshots,
    recordings, raw camera frames, or Slack messages were captured/sent.
- 2026-06-28: FLAT candidates aligned to PNG hair response after device QA.
  - User QA found the overall brow retune improved, but `Daily flat`,
    `Flat sharp`, and `Flat multiply` still did not read like `Daily hair`,
    `Natural hair`, and `Narrow hair`, and asked whether the FLAT candidates
    could use the same application method.
  - Root cause: Unity/RN already apply all PNG brow masks through the same
    shader path, but the FLAT textures had been routed through an extra local
    `retune_flat` image post-process. Metrics confirmed the FLAT alpha was more
    solid and the blue hair-detail signal was weaker than the visible PNG hair
    candidates.
  - RED: `verify_brow_png_hair_textures.py` was tightened to fail FLAT textures
    when alpha is too solid or detail-to-alpha ratio is too weak compared with
    the PNG hair family. The current `Daily flat` failed this new guard.
  - GREEN: FLAT textures were remapped so alpha/detail are driven primarily by
    the extracted blue hair-detail channel, while preserving the shorter FLAT
    target boxes. The generator configs for `Flat sharp` and `Flat multiply`
    now use the same extraction defaults as the other PNG hair masks; the local
    retune script keeps a reproducible `remap_flat_to_hair_response` step for
    the current Unity-ready PNGs.
  - Verification passed: `verify_brow_png_hair_textures.py`,
    `verify_brow_unity_contract.py`, and `verify_region_renderer_routes.py`.
  - User approved the minimal required-file rebuild. Unity/Hub/Licensing
    processes were clear before build; `CloudsiPhone` was connected as
    `FD44CD30-B236-5594-BE61-3C5D408A6851`.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-flat-hair-response-20260628-ufw-r1`. Artifact
    verification recorded `126M` UnityFramework copies and `30M` `Data`
    folders in both RN and package-local paths:
    `evidence/logs/m3-repro-artifact-verification-eyebrow-flat-hair-response-20260628-ufw-r1.log`.
  - RN/Xcode Debug build passed:
    `evidence/logs/eyebrow-rn-xcodebuild-device-flat-hair-response-20260628-r1.log`.
    Built app bundle:
    `unity-builds/xcode-derived-data/RNDevice-eyebrow-flat-hair-response-20260628-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
    `205M`.
  - `devicectl` installed `com.celeste.makeupar.validation` on `CloudsiPhone`:
    `evidence/logs/eyebrow-rn-devicectl-install-flat-hair-response-20260628-r1.log`.
  - App launch was not run in this minimal build loop. No screenshots,
    recordings, raw camera frames, or Slack messages were captured/sent.
- 2026-06-28: FLAT dark-outline/no-hair-grain follow-up.
  - User QA on the installed FLAT hair-response build found the FLAT candidates
    still read as a dark border with no visible brow grain.
  - Root cause: the previous FLAT remap still used the flat source's blue detail
    signal, whose strongest continuous feature was the lower outline. The shader
    then converted that same signal into soft brow alpha before the weaker hair
    detail layer could read on the face.
  - RED: `verify_brow_png_hair_textures.py` was tightened to reject long bright
    bottom-edge detail runs for FLAT textures. The current
    `brow-png-dailyflat-hair-v1` failed with a bottom-edge run of `13`.
  - GREEN: FLAT textures are now rebuilt from the already-visible hair-family
    resources: `Daily flat` from `Daily hair`, and `Flat sharp`/`Flat multiply`
    from `Narrow hair`, packed into the shorter FLAT target boxes with lower
    edge trimming. Verification passed: `verify_brow_png_hair_textures.py`,
    `verify_brow_unity_contract.py`, and `verify_region_renderer_routes.py`.
  - User approved the minimal required-file rebuild. Unity/Hub/Licensing
    processes were clear before build; `CloudsiPhone` was connected as
    `FD44CD30-B236-5594-BE61-3C5D408A6851`.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-flat-outline-fix-20260628-ufw-r1`. Artifact
    verification recorded `126M` UnityFramework copies and `30M` `Data`
    folders in both RN and package-local paths:
    `evidence/logs/m3-repro-artifact-verification-eyebrow-flat-outline-fix-20260628-ufw-r1.log`.
  - RN/Xcode Debug build passed:
    `evidence/logs/eyebrow-rn-xcodebuild-device-flat-outline-fix-20260628-r1.log`.
    Built app bundle:
    `unity-builds/xcode-derived-data/RNDevice-eyebrow-flat-outline-fix-20260628-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
    `205M`.
  - `devicectl` installed `com.celeste.makeupar.validation` on `CloudsiPhone`:
    `evidence/logs/eyebrow-rn-devicectl-install-flat-outline-fix-20260628-r1.log`.
  - App launch was not run in this minimal build loop. No screenshots,
    recordings, raw camera frames, or Slack messages were captured/sent.
- 2026-06-28: PNG brow photo-detail rendering and mask-specific baseline pass.
  - User asked whether new left/right transparent eyebrow photo assets could be
    generated as three pairs, and clarified that the same source art looked
    natural when multiplied over a photo in Photoshop but still lost individual
    hair grain in the app.
  - Direction: separate left/right assets remain recommended for future intake,
    but this local pass first fixes the app-side rendering path so existing
    PNG brow hair detail is not converted into a soft solid mask.
  - RED: focused RN Jest failed because brow tuning still started with visible
    placement values and payloads did not add mask-specific hidden placement
    baselines. The Unity contract verifier failed because PNG brow masks did
    not route to a photo-detail rendering mode.
  - GREEN: RN now keeps user-facing brow placement deltas at zero, adds
    per-mask hidden baselines in payloads, lifts PNG hair masks by
    `maskOffsetY=-0.018`, and resets placement deltas when changing brow mask
    design. `SmoothRegionMask.shader` now has `_BrowPhotoDetailMode`; Unity
    enables it only for `brow-png-*` masks. In that branch, red-channel shape is
    only a light veil and blue-channel hair peaks drive the visible
    multiply-like brow grain.
  - Verification passed: RN Jest `33/33`, TypeScript, RN lint,
    `verify_brow_unity_contract.py`, `verify_brow_png_hair_textures.py`,
    `verify_brow_mask_texture.py`, and `verify_region_renderer_routes.py`.
  - User approved the minimal required-file rebuild. Unity/Hub/Licensing
    processes were clear before build; `CloudsiPhone` was connected as
    `FD44CD30-B236-5594-BE61-3C5D408A6851`.
  - UnityFramework regeneration/sync passed with
    `TIMESTAMP=eyebrow-photodetail-20260628-ufw-r1`. Artifact verification
    recorded `126M` UnityFramework copies and `30M` `Data` folders in both RN
    and package-local paths:
    `evidence/logs/m3-repro-artifact-verification-eyebrow-photodetail-20260628-ufw-r1.log`.
  - RN/Xcode Debug build passed:
    `evidence/logs/eyebrow-rn-xcodebuild-device-photodetail-20260628-r1.log`.
    Built app bundle:
    `unity-builds/xcode-derived-data/RNDevice-eyebrow-photodetail-20260628-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
    `205M`.
  - `devicectl` installed `com.celeste.makeupar.validation` on `CloudsiPhone`:
    `evidence/logs/eyebrow-rn-devicectl-install-photodetail-20260628-r1.log`.
  - App launch was not run in this minimal build loop. No screenshots,
    recordings, raw camera frames, or Slack messages were captured/sent.
- 2026-06-28: Asset resolution, slider usability, and brow attachment feedback.
  - User QA found the photo-detail build improved but still looked resolution
    limited, asked for explicit asset size/resolution guidance, found slider
    dragging too hard, and noticed subtle brow drift relative to the real brow
    during head motion.
  - Asset decision: new photo-like brow inputs should be six transparent PNG
    masters, three styles times wearer-left/right, `2048x1024` per side with a
    consistent crop baseline. The brow should occupy about `1500..1700px` by
    `220..360px`, with `6..12px` source hair strokes and no baked
    background/glow/shadow. The next generation pass should produce a
    `1024x1024` Unity brow atlas for quality QA while keeping current `512x512`
    textures as a performance fallback.
  - RED: focused RN Jest failed because brow placement sliders had no fine
    nudge controls. The Unity brow contract verifier failed because brow overlay
    mesh vertices were copied from ARFace every frame without a brow-specific
    stability path.
  - GREEN: `ValueSlider` now exposes small `-` and `+` buttons that nudge by
    `0.01` UI value steps. `E3RegionMaskOverlay` now applies a conservative
    brow-only local vertex low-pass (`BrowMeshVertexSmoothing=0.58`) so the
    face transform still follows tracking directly while thin brow hair strokes
    get less ARFace surface jitter.
  - Verification passed so far: RN Jest `34/34`, RN lint, TypeScript,
    `verify_brow_unity_contract.py`, `verify_brow_png_hair_textures.py`,
    `verify_brow_mask_texture.py`, and `verify_region_renderer_routes.py`.
    This loop is local only so far. No
    UnityFramework regeneration, RN/Xcode device build, install, launch,
    screenshots, recordings, raw camera frames, or Slack messages were run/sent.
- 2026-06-28: Middle-path original brow cleanup and reshape controls.
  - User chose the middle approach after discussing why full face/brow warp and
    inpainting are higher-risk for eyebrow hair detail.
  - Direction: no AI/model inference, no raw frame storage, and no full
    inpainting in this loop. Add weak `Cleanup` and `Reshape` controls so the
    current ARFace overlay renderer can soften original eyebrow hairs around a
    target asset and strengthen the selected target brow shape inside the brow
    ROI.
  - RED: focused RN Jest failed because default brow tuning did not carry
    `browCleanupStrength=0.24` and `browReshapeStrength=0.16`, and the HUD had
    no `Cleanup`/`Reshape` controls. The Unity contract verifier failed because
    `RNBridge`, `E3RegionMaskOverlay`, and `SmoothRegionMask.shader` did not
    expose the cleanup/reshape fields.
  - GREEN: RN now sends `browCleanupStrength` and `browReshapeStrength` in each
    brow layer and exposes `Cleanup`/`Reshape` sliders. Unity parses, clamps,
    stores, logs, and forwards those values. `SmoothRegionMask.shader` adds a
    target-mask `reshapeBoost` plus a low-alpha `BrowCleanupConcealer` pass.
  - Verification passed: RN Jest `34/34`, RN lint, TypeScript,
    `verify_brow_unity_contract.py`, `verify_brow_png_hair_textures.py`,
    `verify_brow_mask_texture.py`, and `verify_region_renderer_routes.py`.
  - Unity `6000.3.18f1` batchmode import/compile exited `0` with `Tundra build
    success`, `CompileScripts: 3271.993ms`, and
    `Exiting batchmode successfully now!` in
    `evidence/logs/eyebrow-cleanup-reshape-unity6000-batchmode-20260628.log`.
    The log also included a Licensing access-token update warning, but no C#
    or shader compile failure.
  - This loop is local only so far. No UnityFramework regeneration, RN/Xcode
    device build, install, launch, screenshots, recordings, raw camera frames,
    or Slack messages were run/sent.
- 2026-06-28: GrabPass skin sampling and local user media capture loop.
  - User set the next sequence: first implement GrabPass-based real-time skin
    restoration, then add local photo/video capture, then ask before iPhone
    build, and only use an ARCameraBackground texture fallback if GrabPass does
    not sample the AR background correctly on device.
  - RED: `verify_brow_unity_contract.py` failed because
    `SmoothRegionMask.shader` did not grab the live frame, did not expose
    `_BrowCleanupFrameTex`, and did not sample nearby screen pixels for cleanup
    restoration. `verify_ios_local_media_capture_contract.py` failed because
    the `MakeupARLocalMedia` native module did not exist. RN Jest failed
    because clean mode had no `Save Photo`/`Record Video` local product capture
    buttons.
  - GREEN: `SmoothRegionMask.shader` now adds a `GrabPass` named
    `_BrowCleanupFrameTex`; `BrowCleanupConcealer` computes screen-space grab
    coordinates, samples nearby grabbed-frame pixels through
    `SampleGrabbedFrameSkin`, uses a widened brow cleanup zone, and blends the
    sampled skin color over the cleanup halo.
  - GREEN: RN clean mode now exposes explicit user-triggered `Save Photo`,
    `Record Video`, and `Stop Video` actions through `NativeModules`
    `MakeupARLocalMedia`; logs record only status, not captured file/frame data.
    iOS adds `MakeupARLocalMedia.swift`, Photos add-only usage text, and Xcode
    target membership. The native module uses `UIGraphicsImageRenderer` for
    photos, ReplayKit + `AVAssetWriter` for videos, and local Photos saves. It
    does not use networking APIs.
  - Verification passed so far: RN Jest `35/35`, RN lint, TypeScript,
    `verify_brow_unity_contract.py`,
    `verify_ios_local_media_capture_contract.py`, and plist lint for
    `Info.plist`/`PrivacyInfo.xcprivacy`. Unity `6000.3.18f1` batchmode
    compile exited `0` for the GrabPass shader loop with `Tundra build
    success` and `Exiting batchmode successfully now!` in
    `evidence/logs/eyebrow-grabpass-skin-sampling-unity6000-batchmode-20260628.log`.
  - `xcodebuild -list` was attempted only as a non-build project listing check,
    but failed in the sandbox/CoreSimulator environment and did not compile the
    app. Per user instruction, no iPhone build/install/launch was run. The next
    step is to report the build question and wait for explicit approval before
    UnityFramework regeneration and RN/Xcode device build.
  - Follow-up non-build preflight removed a stale ignored local workspace
    reference to `/private/tmp/.../Pods.xcodeproj`; the repo-local
    `Pods/Pods.xcodeproj` exists and is the only intended Pods reference.
    `verify_ios_local_media_capture_contract.py` now guards against stale
    `/private/tmp/` workspace references. `xcodebuild -list -project` can read
    both the app project and Pods project, and Ruby `xcodeproj` can parse the
    workspace references. `xcodebuild -list -workspace` still reports
    sandbox/CoreSimulator service errors in this environment, so actual app
    build verification remains gated on the approved iPhone build.
  - Follow-up TDD diagnostic hardening: RED showed RN Jest missing
    `cleanupSource=grabpass_live_frame_skin_sample` and
    `verify_brow_unity_contract.py` missing `browCleanupSource` in the Unity
    event. GREEN adds `browCleanupSource`, `browCleanupFallback`, and
    `browCleanupStatus` to `E3RegionMaskOverlay.RegionApplyResult`,
    `RNBridge` `recipe_applied` logs/events, and the RN Diagnostics summary.
    Expected candidate values are `grabpass_live_frame_skin_sample`,
    `ar_camera_background_texture`, and `grabpass_candidate` when brow cleanup
    is enabled. Rechecks passed: RN Jest `35/35`, RN lint, TypeScript,
    `verify_brow_unity_contract.py`, `verify_ios_local_media_capture_contract.py`,
    scoped `git diff --check`, and Unity `6000.3.18f1` batchmode compile with
    `Tundra build success`, `CompileScripts: 3237.193ms`, and
    `Exiting batchmode successfully now!` in
    `evidence/logs/eyebrow-grabpass-diagnostics-unity6000-batchmode-20260628.log`.
  - Follow-up no-phone preflight implemented the prepared ARCameraBackground
    fallback path without changing the default. RED: RN Jest failed because
    `browCleanupSourceMode` was missing from payload/HUD diagnostics, and
    `verify_brow_unity_contract.py` failed because `RNBridge` did not parse the
    source mode. GREEN: RN now sends `browCleanupSourceMode=grabpass` by
    default and exposes a brow-only `GrabPass`/`AR BG` QA switch; `RNBridge`
    parses and emits the mode; `E3RegionMaskOverlay` can blit
    `ARCameraBackground.material` into a transient GPU `RenderTexture`, bind it
    as `_BrowCleanupCameraTex`, and set `_BrowCleanupFrameSource` only when the
    texture is available. Verification passed: RN Jest `36/36`, RN lint,
    TypeScript, `verify_brow_unity_contract.py`,
    `verify_ios_local_media_capture_contract.py`, and Unity `6000.3.18f1`
    batchmode compile with `Tundra build success`, `CompileScripts:
    3235.562ms`, and `Exiting batchmode successfully now!` in
    `evidence/logs/eyebrow-ar-camera-background-fallback-unity6000-batchmode-20260628.log`.
  - Follow-up fallback diagnostics hardening: RED showed RN HUD did not display
    `cleanupFallbackAvailable`/`cleanupCameraTex`, and
    `verify_brow_unity_contract.py` did not require those fields in the Unity
    event. GREEN adds actual RT readiness and width/height to
    `E3RegionMaskOverlay.RegionApplyResult`, `RNBridge` logs/events, and RN
    diagnostics. AR BG mode now reports `ar_camera_background_ready` only when
    the transient GPU texture was updated; otherwise it reports
    `ar_camera_background_unavailable`.
  - Approved iPhone build completed for the fallback-readiness diagnostics
    loop. UnityFramework regenerated/synced with
    `TIMESTAMP=eyebrow-cleanup-fallback-20260628-ufw-r1`; artifact verification
    recorded `126M` RN/package framework copies with `30M` `Data` folders.
    RN/Xcode attempt r1 failed because Swift could not see `RCTBridgeModule`
    for `MakeupARLocalMedia.swift`; adding
    `MakeupARValidation-Bridging-Header.h` with `<React/RCTBridgeModule.h>` and
    setting `SWIFT_OBJC_BRIDGING_HEADER` fixed the local media module compile.
    RN/Xcode r2 passed, producing a `205M` app bundle with a `126M`
    `UnityFramework.framework` and `30M` Unity `Data`. `devicectl` installed
    `com.celeste.makeupar.validation` on `CloudsiPhone`; automated launch was
    denied because the device was locked. Logs:
    `evidence/logs/m3-repro-unity-export-eyebrow-cleanup-fallback-20260628-ufw-r1.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-eyebrow-cleanup-fallback-20260628-ufw-r1.log`,
    `evidence/logs/m3-repro-artifact-verification-eyebrow-cleanup-fallback-20260628-ufw-r1.log`,
    `evidence/logs/eyebrow-rn-xcodebuild-device-cleanup-fallback-20260628-r1.log`,
    `evidence/logs/eyebrow-rn-xcodebuild-device-cleanup-fallback-20260628-r2.log`,
    `evidence/logs/eyebrow-rn-devicectl-list-cleanup-fallback-20260628-r1.log`,
    `evidence/logs/eyebrow-rn-devicectl-install-cleanup-fallback-20260628-r1.log`,
    and
    `evidence/logs/eyebrow-rn-devicectl-launch-cleanup-fallback-20260628-r1.log`.
  - Follow-up skin-restore opt-out: RED covered a missing
    `browCleanupEnabled=false` payload path and a missing brow QA switch.
    GREEN adds a brow-only `Skin Restore On/Off` switch in RN. Turning it off
    preserves the stored `Cleanup` slider value for later, but sends effective
    `browCleanupEnabled=false`, `browCleanupStrength=0`, and
    `browCleanupSourceMode=none` to Unity; `E3RegionMaskOverlay` then skips the
    cleanup pass and ARCameraBackground fallback request. Diagnostics now expose
    `cleanupEnabled=` alongside the existing cleanup source/fallback fields.
    Verification passed: RN Jest `38/38`, RN lint, TypeScript,
    `verify_brow_unity_contract.py`, `verify_ios_local_media_capture_contract.py`,
    and Unity `6000.3.18f1` batchmode compile with `Tundra build success` and
    `Exiting batchmode successfully now!` in
    `evidence/logs/eyebrow-skin-restore-toggle-unity6000-batchmode-20260628.log`.
    Per user instruction, no new iPhone build/install/launch was run for this
    toggle-only follow-up.
  - Approved iPhone build completed for the skin-restore toggle loop.
    Pre-build checks passed again: RN Jest `38/38`, RN lint, TypeScript,
    `verify_brow_unity_contract.py`, and
    `verify_ios_local_media_capture_contract.py`. UnityFramework regenerated
    and synced with `TIMESTAMP=eyebrow-skin-restore-toggle-20260628-ufw-r1`;
    artifact verification recorded `126M` RN/package framework copies with
    `30M` `Data` folders. RN/Xcode Debug build for `CloudsiPhone` passed,
    producing a `206M` app bundle with a `126M` embedded
    `UnityFramework.framework` and `30M` Unity `Data`. `devicectl` installed
    and launched `com.celeste.makeupar.validation` on the paired iPhone. Logs:
    `evidence/logs/m3-repro-unity-export-eyebrow-skin-restore-toggle-20260628-ufw-r1.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-eyebrow-skin-restore-toggle-20260628-ufw-r1.log`,
    `evidence/logs/m3-repro-artifact-verification-eyebrow-skin-restore-toggle-20260628-ufw-r1.log`,
    `evidence/logs/eyebrow-rn-xcodebuild-device-skin-restore-toggle-20260628-r1.log`,
    `evidence/logs/eyebrow-rn-devicectl-install-skin-restore-toggle-20260628-r1.log`,
    and
    `evidence/logs/eyebrow-rn-devicectl-launch-skin-restore-toggle-20260628-r1.log`.
  - Follow-up skin-color mismatch fix: device QA reported that the covered brow
    cleanup area did not look like skin. Root-cause check found that
    `SmoothRegionMask.shader` still mixed a hard-coded beige cleanup tint
    (`0.76,0.61,0.50`) into the pigment pass before the live-frame cleanup
    pass, and the frame sampler used very near samples that could include dark
    original brow hairs. RED extended `verify_brow_unity_contract.py` to reject
    fixed cleanup tint and require weighted skin sampling. GREEN removes the
    pigment-pass cleanup tint, keeps reshape separate from cleanup, and changes
    both GrabPass and ARCameraBackground cleanup paths to sample farther
    surrounding pixels while downweighting dark brow-hair samples. Verification
    passed: `verify_brow_unity_contract.py`, scoped `git diff --check`, and
    Unity `6000.3.18f1` batchmode compile with `Tundra build success`,
    `CompileScripts: 1376.105ms`, and `Exiting batchmode successfully now!` in
    `evidence/logs/eyebrow-skin-restore-sample-weight-unity6000-batchmode-20260628.log`.
    No new iPhone build/install was run for this local shader fix.
  - Follow-up source-brow cleanup mask fix: device QA correctly noted that the
    cleanup region still followed the moved target brow asset, so moving the brow
    fully above or below the original brow could leave the original eyebrow
    uncovered. RED extended `verify_brow_unity_contract.py` to require an
    internal canonical source-brow mask and shader sampling from unshifted face
    UVs, initially failing on missing
    `SmoothRegionMasks/brow-cleanup-source-v1.png`. GREEN adds
    `generate_brow_cleanup_source_mask.py`, generated
    `brow-cleanup-source-v1.png/.meta`, and
    `verify_brow_cleanup_source_mask.py`; `E3RegionMaskOverlay` binds the mask as
    `_BrowCleanupSourceTex`, while `SmoothRegionMask.shader` uses the union of
    target cleanup halo and source cleanup alpha, with target-core protection so
    the source cleanup pass does not overpaint the newly drawn brow. Verification
    passed: `verify_brow_cleanup_source_mask.py`,
    `verify_brow_unity_contract.py`, and Unity `6000.3.18f1` batchmode compile
    with `Tundra build success`, `CompileScripts: 2990.687ms`, and
    `Exiting batchmode successfully now!` in
    `evidence/logs/eyebrow-source-cleanup-unity6000-batchmode-20260628.log`.
    No new iPhone build/install was run for this local cleanup-mask fix.
  - Follow-up PSD ARCore tint-mask clarification: the supplied PSD uses white
    or gray layer pixels as tintable coverage/density masks, not fixed white
    makeup color. GREEN updates `generate_psd_arcore_makeup_textures.py` to
    combine layer alpha and luminance into mask intensity, keeps generated
    resources under new ids (`psd-arcore-lip-style-v1`,
    `psd-arcore-lip-mask-v1`, `psd-arcore-cheek-undereye-v1`, and
    `psd-arcore-brow-semi-arch-v1`), and documents that runtime pigment comes
    from RN/Unity recipe color. Verification passed:
    `verify_psd_arcore_makeup_textures.py`,
    `verify_brow_unity_contract.py`, and scoped `git diff --check`. No new
    iPhone build/install was run for this local asset-pipeline clarification.
  - Approved iPhone build completed for the PSD tint-mask loop. Pre-build
    checks passed: `verify_psd_arcore_makeup_textures.py`,
    `verify_brow_unity_contract.py`, `verify_region_renderer_routes.py`,
    `verify_brow_cleanup_source_mask.py`, `verify_brow_mask_texture.py`, RN
    Jest `38/38`, RN lint, TypeScript, `verify_ios_local_media_capture_contract.py`,
    scoped `git diff --check`, and Unity `6000.3.18f1` batchmode import/compile
    with `Tundra build success`, `CompileScripts: 986.103ms`, and
    `Exiting batchmode successfully now!` in
    `evidence/logs/psd-tint-mask-prebuild-unity6000-batchmode-20260629.log`.
    UnityFramework regenerated and synced with
    `TIMESTAMP=psd-tint-mask-20260629-ufw-r1`; artifact verification recorded
    `131M` RN/package framework copies with `35M` `Data` folders. RN/Xcode Debug
    build for `CloudsiPhone` passed, producing a `211M` app bundle with a `131M`
    embedded `UnityFramework.framework` and `35M` Unity `Data`. `devicectl`
    installed and launched `com.celeste.makeupar.validation` on the paired
    iPhone. Logs:
    `evidence/logs/m3-repro-unity-export-psd-tint-mask-20260629-ufw-r1.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-psd-tint-mask-20260629-ufw-r1.log`,
    `evidence/logs/m3-repro-artifact-verification-psd-tint-mask-20260629-ufw-r1.log`,
    `evidence/logs/eyebrow-rn-xcodebuild-device-psd-tint-mask-20260629-r1.log`,
    `evidence/logs/eyebrow-rn-devicectl-install-psd-tint-mask-20260629-r1.log`,
    and
    `evidence/logs/eyebrow-rn-devicectl-launch-psd-tint-mask-20260629-r1.log`.
  - Follow-up brow clumping fix: user noted that brow likely needs a different
    implementation from other regions because it appears clumped. Root cause:
    the brow photo-detail path still behaved like a smooth filled region with
    broad blue density, and the PSD brow generator stored broad density in the
    blue detail channel. RED extended `verify_brow_unity_contract.py` to require
    a brow-specific `BrowFiberAlpha` high-pass extractor and reject the older
    broad `hairLine` fill formula; RED also extended
    `verify_psd_arcore_makeup_textures.py` to fail when PSD brow blue detail is
    too broad (`ratio=0.763`). GREEN changes `SmoothRegionMask.shader` so brow
    photo masks are fiber-first: blue-channel detail drives opacity, red shape
    only gates the area and contributes a very weak powder veil. It also changes
    `generate_psd_arcore_makeup_textures.py` so PSD brow blue detail is sparse
    fiber data instead of broad fill. Verification passed:
    `verify_brow_unity_contract.py`, `verify_psd_arcore_makeup_textures.py`,
    `verify_brow_png_hair_textures.py`, scoped `git diff --check`, and Unity
    `6000.3.18f1` batchmode compile with `Tundra build success`,
    `CompileScripts: 932.484ms`, and `Exiting batchmode successfully now!` in
    `evidence/logs/brow-fiber-renderer-unity6000-batchmode-20260629.log`. No
    new iPhone build/install was run for this local shader/asset fix.
  - Follow-up PSD semi-arch layer-semantics fix: user clarified that
    `left/right` are the hair-detail layers, `gradient` should add only very
    light powder, and `full` is not fill makeup; it is the target brow core, so
    any recognized/source brow outside `full` should be restored toward sampled
    skin color. Root cause: the previous PSD fix still treated red/full as a
    powder shape. GREEN updates the PSD generator so the brow runtime texture is
    `R=full target/protect core`, `G=soft gradient powder`, `B=left/right hair
    detail`, and `A=diagnostic union`. The shader's PSD path now reads powder
    from green instead of red, keeps hair from blue, and lets the existing
    cleanup pass use red/full as the target-core protection mask when restoring
    the canonical source-brow region outside the new brow. Verification passed:
    `verify_brow_unity_contract.py`, `verify_psd_arcore_makeup_textures.py`,
    and scoped `git diff --check`. Unity `6000.3.18f1` batchmode compile was
    attempted but did not reach compile because Licensing IPC timed out waiting
    for `LicenseClient-hi`; log:
    `evidence/logs/psd-semiarch-layer-semantics-unity6000-batchmode-20260629.log`.
    No new iPhone build/install was run for this local shader/asset/contract/doc
    fix.
  - Approved iPhone build completed for the PSD semi-arch layer-semantics fix.
    Pre-build verification passed with `verify_psd_arcore_makeup_textures.py`
    and `verify_brow_unity_contract.py`. UnityFramework regenerated and synced
    with `scripts/build_m3_unityframework.sh`; artifact verification recorded
    `131M` UnityFramework copies and `35M` Unity `Data` folders in both RN and
    package-local framework paths. RN/Xcode Debug build for `CloudsiPhone`
    passed with development team `X5C5U3T6B4`, producing a signed `211M`
    `MakeupARValidation.app`. `devicectl` installed and launched
    `com.celeste.makeupar.validation` on the paired iPhone. Logs:
    `evidence/logs/m3-repro-unity-export-2026-06-29-155702.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-29-155702.log`,
    `evidence/logs/m3-repro-artifact-verification-2026-06-29-155702.log`,
    `evidence/logs/rn-xcodebuild-device-debug-20260629-1600.log`,
    `evidence/logs/devicectl-install-makeupar-20260629-1602.log`, and
    `evidence/logs/devicectl-launch-makeupar-20260629-1603.log`.
  - Follow-up PSD semi-arch shape/hairline fix after iPhone visual QA:
    user reported that the AR brow sat under the real brow, the shape looked
    odd, and the brow grain was not visible. Root cause: the PSD semi-arch mask
    reused the PNG hair placement baseline (`maskOffsetY=-0.018`) even though
    the PSD silhouette is different, and the generated blue hair channel kept
    broad `left/right` density (`mean=206`) so the shader saw a filled brow
    block instead of line texture. GREEN changes the PSD generator to high-pass
    local line centers from `left/right`, reduce the `gradient` powder
    amplitude, and slightly thin the `full` core. The regenerated PSD brow
    changed from bbox `(107,98,406,133)`, active `3721`, blue mean `206` to bbox
    `(110,99,400,132)`, active `2392`, blue active `1853`, blue mean `133`.
    RN now gives only `psd-arcore-brow-semi-arch-v1` a lifted placement baseline
    `maskOffsetY=-0.034` plus initial `Texture Detail=0.78` and `Cleanup=0.52`
    when selected. Verification passed:
    `verify_psd_arcore_makeup_textures.py`, `verify_brow_unity_contract.py`,
    and focused RN Jest `__tests__/App.test.tsx` (`41` tests). No new
    UnityFramework/RN iPhone build was run for this local asset/RN/doc fix yet.
  - Approved iPhone build completed for the PSD semi-arch shape/hairline fix.
    Pre-build verification passed with `verify_psd_arcore_makeup_textures.py`,
    `verify_brow_unity_contract.py`, focused RN Jest
    `__tests__/App.test.tsx` (`41/41`), and `npx tsc --noEmit`.
    UnityFramework regenerated and synced with
    `scripts/build_m3_unityframework.sh` at timestamp `2026-06-29-171730`;
    artifact verification recorded `131M` UnityFramework copies and `35M`
    Unity `Data` folders in both RN and package-local framework paths. The
    UnityFramework Xcode phase logged repeated passcode-protected device polling
    warnings, but they did not block the generic framework build. RN/Xcode Debug
    build for `CloudsiPhone` passed, producing a signed `211M`
    `MakeupARValidation.app`. `devicectl` installed and launched
    `com.celeste.makeupar.validation` on the paired iPhone. Logs:
    `evidence/logs/m3-repro-unity-export-2026-06-29-171730.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-29-171730.log`,
    `evidence/logs/m3-repro-artifact-verification-2026-06-29-171730.log`,
    `evidence/logs/rn-xcodebuild-device-debug-20260629-1720.log`,
    `evidence/logs/devicectl-install-makeupar-20260629-1721.log`, and
    `evidence/logs/devicectl-launch-makeupar-20260629-1721.log`.
  - Follow-up MESH debug overlay fill fix: user reported that turning on
    `MESH` showed a filled yellow face surface instead of triangular wire.
    Root cause: the RN `MESH` toggle correctly sent `meshOverlayVisible=true`,
    and `FaceTrackingStatusReporter` had a wireframe `OnGUI` path, but
    `RNBridge.SetFaceMeshOverlayVisible(true)` also re-enabled the ARFace prefab
    `MeshRenderer` with a yellow transparent material. That filled surface
    visually covered the wireframe. GREEN keeps the mesh overlay state routed to
    `statusReporter.SetMeshOverlayVisible(faceMeshVisible)` while always
    suppressing ARFace prefab renderers; `faceDebugSurfaceSuppressed` is now
    logged as `true` even when `meshOverlayVisible=true`. The yellow surface
    helper was removed so `MESH` means wireframe only. Verification passed:
    `verify_brow_unity_contract.py`, focused RN Jest
    `__tests__/App.test.tsx` (`41/41`), `npx tsc --noEmit`, and Unity
    `6000.3.18f1` batchmode compile with `Tundra build success`,
    `CompileScripts: 3276.346ms`, and `Exiting batchmode successfully now!` in
    `evidence/logs/mesh-wire-debug-unity6000-batchmode-20260629.log`. No new
    UnityFramework/RN iPhone build was run for this local debug-overlay fix yet.
  - Approved iPhone build attempted for the MESH wireframe-only fix. Pre-build
    verification passed with `verify_brow_unity_contract.py`, focused RN Jest
    `__tests__/App.test.tsx` (`41/41`), and `npx tsc --noEmit`.
    UnityFramework regenerated and synced with
    `scripts/build_m3_unityframework.sh` at timestamp `2026-06-29-180716`;
    artifact verification recorded `131M` UnityFramework copies and `35M`
    Unity `Data` folders in both RN and package-local framework paths. Direct
    RN/Xcode build to `CloudsiPhone` failed because Xcode could not find the
    destination id `00008130-001E08E22E30001C`; `xcrun devicectl list devices`
    showed `CloudsiPhone` as `unavailable`. A fallback generic iOS Debug build
    succeeded, producing a signed `211M` `MakeupARValidation.app`, but
    `devicectl` install did not complete because CoreDevice could not locate the
    device (`CoreDeviceError 1011`, `DeviceIdentifier = ecid_8454016831848476`).
    Logs:
    `evidence/logs/m3-repro-unity-export-2026-06-29-180716.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-29-180716.log`,
    `evidence/logs/m3-repro-artifact-verification-2026-06-29-180716.log`,
    `evidence/logs/rn-xcodebuild-device-debug-20260629-1810.log`,
    `evidence/logs/rn-xcodebuild-generic-ios-debug-20260629-1810.log`,
    `evidence/logs/devicectl-install-makeupar-20260629-1811.log`, and
    `evidence/logs/devicectl-install-makeupar-20260629-1811-coredevice.log`.
  - Follow-up PSD asset intake update: user supplied an updated
    `ARCore_canonical_face_texture_1.psd`. First inspection showed that
    hidden runtime layers such as `left-full`, `right-full`,
    `left-gradient`, `right-gradient`, and `lip/full_color_or_mask` can
    composite as alpha-empty if the extraction path trusts Photoshop
    visibility. User then resupplied a cleaned PSD where runtime source layers
    are visible and guide/template layers are hidden. GREEN adds
    `extract_arcore_psd_layers.py`, which selects runtime PSD layers by
    canonical layer path, force-composites hidden-but-named runtime sources as
    a safety net, and excludes `preview`, `UVs`, `lines`, `background`,
    `archive`/`archieve`, and `mask` guide layers. The PSD generator now accepts
    `left-gradient` directly and falls back to single cheek source layers when
    left/right cheek source names are absent. Regenerated Unity resources:
    `psd-arcore-lip-style-v1.png`, `psd-arcore-lip-mask-v1.png`,
    `psd-arcore-cheek-undereye-v1.png`, and
    `psd-arcore-brow-semi-arch-v1.png`. The latest PSD brow channels are
    R/full active `2392`, G/powder active `3040`, B/hair active `1276`;
    verification passed with `verify_psd_arcore_makeup_textures.py` and
    `verify_brow_unity_contract.py`. The learning guide now records the PSD
    delivery rule: keep makeup source layers named consistently and preferably
    visible, but keep guide/template/archive layers out of runtime sources. No
    UnityFramework/RN iPhone build was run for this asset-pipeline-only update.
  - Approved iPhone build completed for the updated PSD asset intake. Pre-build
    verification passed with `verify_psd_arcore_makeup_textures.py`,
    `verify_brow_unity_contract.py`, focused RN Jest `__tests__/App.test.tsx`
    (`41/41`), and `npx tsc --noEmit`. `xcrun devicectl list devices` showed
    `CloudsiPhone` as `available (paired)`. UnityFramework regenerated and
    synced with `scripts/build_m3_unityframework.sh` at timestamp
    `psd-asset-20260629-204246`; artifact verification recorded `131M`
    UnityFramework copies and `35M` Unity `Data` folders in both RN and
    package-local framework paths. The UnityFramework Xcode phase logged
    passcode-protected device polling warnings, but the generic framework build
    still passed. RN/Xcode Debug build for `CloudsiPhone` passed, producing a
    signed `211M` `MakeupARValidation.app`. `devicectl` installed and launched
    `com.celeste.makeupar.validation` on the paired iPhone. Logs:
    `evidence/logs/m3-repro-unity-export-psd-asset-20260629-204246.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-psd-asset-20260629-204246.log`,
    `evidence/logs/m3-repro-artifact-verification-psd-asset-20260629-204246.log`,
    `evidence/logs/rn-xcodebuild-device-debug-psd-asset-20260629-204246.log`,
    `evidence/logs/devicectl-install-makeupar-psd-asset-20260629-204246.log`,
    and
    `evidence/logs/devicectl-launch-makeupar-psd-asset-20260629-204246.log`.
  - Follow-up PSD semi-arch hair-detail visibility fix: user confirmed the
    installed `PSD semi arch` mask was the updated asset but reported that its
    hair grain looked weaker than the other brow assets despite clean white
    source strokes. Root cause: the previous PSD generator assumed
    `left/right` could contain broad density and aggressively extracted only
    line centers; for the new PSD those layers are already clean hair strokes,
    so the conversion over-thinned them. The PSD `full` channel is also much
    denser than PNG brow shape channels, which made the shader's shape-based
    broad-fill suppression hide more of the hair detail. GREEN updates the PSD
    generator to preserve direct `left/right` stroke coverage while still using
    the `full` shape gate, and updates `SmoothRegionMask.shader` to relax
    detail suppression only when the PSD brow flag is active. Regenerated
    `psd-arcore-brow-semi-arch-v1.png`: B/hair active pixels increased from
    `1276` to `2144` while R/full active remains `2392` and G/powder active
    remains `3040`. `verify_psd_arcore_makeup_textures.py` now requires enough
    PSD blue hair coverage to catch this regression. Verification passed:
    `verify_psd_arcore_makeup_textures.py`, `verify_brow_unity_contract.py`,
    focused RN Jest `__tests__/App.test.tsx` (`41/41`), and Unity
    `6000.3.18f1` batchmode compile with `Tundra build success`,
    `CompileScripts: 990.106ms`, and `Exiting batchmode successfully now!` in
    `evidence/logs/psd-brow-hair-preserve-unity6000-batchmode-20260629-210826.log`.
    No new UnityFramework/RN iPhone build was run for this local shader/asset
    fix yet.
  - Approved iPhone build completed for the PSD semi-arch hair/full semantics
    fix. User clarified that PSD `full` is only an area/protection check, not a
    visible makeup layer. GREEN updates `SmoothRegionMask.shader` so the PSD
    brow visible seed comes from hair/powder (`B`/`G`) only, while `full`
    remains a gate/protection channel and does not add fill color or brow
    reshape output. The brow Unity contract verifier now checks that the old
    `shapeRaw * powderFill * 0.32` visible path is absent and that PSD reshape
    boost is disabled by the PSD brow mask. Pre-build verification passed with
    `verify_psd_arcore_makeup_textures.py`, `verify_brow_unity_contract.py`,
    focused RN Jest `__tests__/App.test.tsx` (`41/41`), `npx tsc --noEmit`,
    and `git diff --check` over the touched shader/scripts/docs. UnityFramework
    regenerated and synced with `scripts/build_m3_unityframework.sh` at
    timestamp `psd-full-protect-20260629-212153`; artifact verification
    recorded `131M` UnityFramework copies and `35M` Unity `Data` folders in
    both RN and package-local framework paths. RN/Xcode Debug build for
    `CloudsiPhone` passed, producing a signed `211M`
    `MakeupARValidation.app`. `devicectl` installed and launched
    `com.celeste.makeupar.validation` on the paired iPhone. Logs:
    `evidence/logs/m3-repro-unity-export-psd-full-protect-20260629-212153.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-psd-full-protect-20260629-212153.log`,
    `evidence/logs/m3-repro-artifact-verification-psd-full-protect-20260629-212153.log`,
    `evidence/logs/rn-xcodebuild-device-debug-psd-full-protect-20260629-212153.log`,
    `evidence/logs/devicectl-install-makeupar-psd-full-protect-20260629-212153.log`,
    and
    `evidence/logs/devicectl-launch-makeupar-psd-full-protect-20260629-212153.log`.
  - Follow-up PSD semi-arch shape/stroke correction after device screenshot:
    user reported that the built PSD SEMI ARCH still looked wrong, with brow
    strokes appearing under the natural eyebrow and the shape reading as dotted
    lower-edge marks instead of hair texture. Root cause: the PSD generator
    resized the 4096px extracted PSD full-canvas layers to 512px before
    crop/fit, so the clean white `left/right` hair strokes were already damaged
    before Unity texture generation. It also bbox-fitted both brows together,
    including the empty inter-brow gap, which compressed each brow side and
    pushed the semi-arch into an unnaturally thin contour. GREEN keeps PSD
    source layers at original resolution until final crop/fit, fits left and
    right brow sides separately to `brow-cleanup-source-v1`, lightly preserves
    high-resolution hair strokes before downsampling, and resets the PSD brow
    hidden Y baseline to `0` so the selected mask does not start with an
    additional downward offset. Regenerated `psd-arcore-brow-semi-arch-v1.png`:
    R/full active `5470`, G/powder active `6613`, B/hair active `4888`, bbox
    `(99,83,414,143)`. Verification passed:
    `verify_psd_arcore_makeup_textures.py`, `verify_brow_unity_contract.py`,
    focused RN Jest `__tests__/App.test.tsx` (`41/41`), and
    `npx tsc --noEmit`. Approved iPhone build completed at timestamp
    `psd-brow-refit-20260629-214900`: UnityFramework regenerated and synced
    with `scripts/build_m3_unityframework.sh`, artifact verification recorded
    `131M` UnityFramework copies and `35M` Unity `Data` folders in both RN and
    package-local framework paths, RN/Xcode Debug build for `CloudsiPhone`
    passed with a signed `211M` `MakeupARValidation.app`, and `devicectl`
    installed/launched `com.celeste.makeupar.validation` on the paired iPhone.
    Logs:
    `evidence/logs/m3-repro-unity-export-psd-brow-refit-20260629-214900.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-psd-brow-refit-20260629-214900.log`,
    `evidence/logs/m3-repro-artifact-verification-psd-brow-refit-20260629-214900.log`,
    `evidence/logs/rn-xcodebuild-device-debug-psd-brow-refit-20260629-214900.log`,
    `evidence/logs/devicectl-install-makeupar-psd-brow-refit-20260629-214900.log`,
    and
    `evidence/logs/devicectl-launch-makeupar-psd-brow-refit-20260629-214900.log`.
  - Follow-up PSD semi-arch thin-stroke tuning after user feedback: user said
    the refit build was much better, but asked why individually drawn thin
    hairs looked thick. Root cause: the PSD hair preservation path widened
    high-resolution source strokes with `MaxFilter(size=3)`, then RN started
    PSD semi-arch with `Texture Detail=0.78`, and the shader's fiber emphasis
    made the widened B channel read too heavy. RED updated
    `verify_psd_arcore_makeup_textures.py` to reject PSD hair widening and
    require thinner B-channel mean, and updated the RN HUD test to expect
    `detail 64%`; both failed against the previous implementation. GREEN
    removes the brow hair MaxFilter from the PSD generator, lowers
    `PSD_BROW_DEFAULT_DETAIL_AMOUNT` to `0.64`, and regenerates
    `psd-arcore-brow-semi-arch-v1.png`. Latest metrics: R/full active `5470`,
    G/powder active `6613`, B/hair active `4182`, B mean `91.1`, bbox
    `(99,83,414,143)`. Verification passed:
    `verify_psd_arcore_makeup_textures.py`, `verify_brow_unity_contract.py`,
    focused RN Jest `__tests__/App.test.tsx` (`41/41`), and
    `npx tsc --noEmit`. Approved iPhone build completed at timestamp
    `psd-brow-thin-20260630-000700`: UnityFramework regenerated and synced
    with `scripts/build_m3_unityframework.sh`, artifact verification recorded
    `131M` UnityFramework copies and `35M` Unity `Data` folders in both RN and
    package-local framework paths, RN/Xcode Debug build for `CloudsiPhone`
    passed with a signed `211M` `MakeupARValidation.app`, and `devicectl`
    installed/launched `com.celeste.makeupar.validation` on the paired iPhone.
    Logs:
    `evidence/logs/m3-repro-unity-export-psd-brow-thin-20260630-000700.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-psd-brow-thin-20260630-000700.log`,
    `evidence/logs/m3-repro-artifact-verification-psd-brow-thin-20260630-000700.log`,
    `evidence/logs/rn-xcodebuild-device-debug-psd-brow-thin-20260630-000700.log`,
    `evidence/logs/devicectl-install-makeupar-psd-brow-thin-20260630-000700.log`,
    and
    `evidence/logs/devicectl-launch-makeupar-psd-brow-thin-20260630-000700.log`.
  - Follow-up PSD semi-arch MediaPipe canonical fitting after user feedback:
    user said the thin-stroke build was better, but the brow still felt like the
    asset itself had been stretched. Root cause: the generator was no longer
    thickening individual strokes, but it still fit each PSD brow side into the
    broad `brow-cleanup-source-v1` ARKit/source-brow bbox (`~164x64px` per
    side). Official MediaPipe FaceMesh eyebrow landmark targets mapped through
    the canonical face model are closer to `~112x30px` per side, so the old
    target made the authored `~4.9:1` semi-arch read vertically enlarged. RED
    updated `verify_psd_arcore_makeup_textures.py` to require MediaPipe
    canonical brow fitting and reject vertically stretched PSD brow output.
    GREEN updates `generate_psd_arcore_makeup_textures.py` to fit PSD brow
    sides into MediaPipe canonical eyebrow targets with source aspect preserved
    (`contain`), while keeping lip/cheek on the existing ARKit bbox path.
    Regenerated `psd-arcore-brow-semi-arch-v1.png`: R/full bbox
    `(115,131,400,159)`, R/full active `2223`, G/powder active `3114`, B/hair
    active `2034`, B/hair mean `76.863`. This is static MediaPipe
    canonical-landmark fitting only; no runtime MediaPipe inference, raw camera
    frame storage, or upload was added. Verification passed:
    `verify_psd_arcore_makeup_textures.py`, `verify_brow_unity_contract.py`,
    focused RN Jest `__tests__/App.test.tsx` (`41/41`), and
    `npx tsc --noEmit`. Approved iPhone build completed at timestamp
    `psd-mediapipe-fit-20260630-010500`: UnityFramework regenerated and synced
    with `scripts/build_m3_unityframework.sh`, artifact verification recorded
    `131M` UnityFramework copies and `35M` Unity `Data` folders in both RN and
    package-local framework paths, RN/Xcode Debug build for `CloudsiPhone`
    passed with a signed `211M` `MakeupARValidation.app`, and `devicectl`
    installed/launched `com.celeste.makeupar.validation` on the paired iPhone.
    Logs:
    `evidence/logs/m3-repro-unity-export-psd-mediapipe-fit-20260630-010500.log`,
    `evidence/logs/m3-repro-xcodebuild-unityframework-psd-mediapipe-fit-20260630-010500.log`,
    `evidence/logs/m3-repro-artifact-verification-psd-mediapipe-fit-20260630-010500.log`,
    `evidence/logs/rn-xcodebuild-device-debug-psd-mediapipe-fit-20260630-010500.log`,
    `evidence/logs/devicectl-install-makeupar-psd-mediapipe-fit-20260630-010500.log`,
    and
    `evidence/logs/devicectl-launch-makeupar-psd-mediapipe-fit-20260630-010500.log`.
  - Follow-up after device screenshot of the MediaPipe-fit build: user clarified
    that the issue now looked like the renderer was not recognizing the eyebrow
    position at all, and explicitly rejected using an ARKit-runtime-corrected
    target. Root cause recorded: a PSD brow texture authored into a MediaPipe
    canonical target is still only a static texture; sampling it directly with
    ARKit `ARFace` UVs does not mean the runtime has recognized the user's
    actual eyebrow. A short-lived ARKit-calibrated generator/test direction and
    PSD-only shader UV bridge were removed. The generator is restored to the
    MediaPipe canonical target with aspect-preserving side fitting, and
    `verify_brow_unity_contract.py` now rejects hidden PSD canonical correction
    constants such as `ApplyPsdBrowCanonicalMap`. Latest regenerated
    `psd-arcore-brow-semi-arch-v1.png`: R/full bbox `(113,132,398,159)`,
    R/full active `2166`, G/powder active `3045`, B/hair active `1992`,
    B/hair mean `75.749`. Correct next direction: keep the asset in
    canonical-face space, then drive live brow placement from runtime detector
    landmarks (Apple Vision eyebrow landmarks on the current iOS path; MediaPipe
    Face Landmarker/canonical output after explicit dependency/privacy review),
    without per-asset hidden y/gap/scale correction values. Verification passed:
    `verify_psd_arcore_makeup_textures.py` and `verify_brow_unity_contract.py`.
  - 2026-06-30 MediaPipe brow runtime privacy approval: user approved the
    recommended storage policy after clarifying that explicit product photo
    capture should still save final results. Approved scope: add MediaPipe Face
    Landmarker as an on-device eyebrow placement runtime with an app-bundled
    `face_landmarker.task`; keep detector raw camera frames memory-only; do not
    store or upload raw detector frames; log only landmark, bbox, confidence,
    timing, and status numbers; keep user-triggered `Save Photo`/`Record Video`
    as the only local media save exception. RED added
    `verify_brow_landmark_privacy_contract.py` and confirmed it failed before
    the contract was documented.
  - 2026-06-30 MediaPipe canonical app standard and dependency install:
    user chose MediaPipe Canonical Face as the app-wide makeup asset coordinate
    standard, not just the PSD brow experiment. RED/contract updates required
    PSD-derived lip, cheek, and brow masks to preserve the authored full-canvas
    MediaPipe/ARCore canonical layout instead of bbox-fitting into ARKit/Unity
    target boxes; RN defaults now use the PSD/canonical masks for lip, cheek,
    and brow, with neutral brow placement deltas (`gap=0`, `y=0`). The iOS
    dependency was installed with `MediaPipeTasksVision` `0.10.14`,
    `face_landmarker.task` was bundled, and a Swift sentinel imports the
    dependency and resolves the bundled model path. Verification passed:
    TypeScript, focused RN Jest `41/41`, `verify_psd_arcore_makeup_textures.py`,
    `verify_brow_landmark_privacy_contract.py`,
    `verify_brow_unity_contract.py`, and a generic signing-disabled iOS
    Xcode build. This step proves dependency/model linkage only; the live
    camera-frame to Face Landmarker to Unity landmark-payload bridge remains
    pending, and no UnityFramework real-device build/install was run in this
    loop.
