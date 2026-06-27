# E7 Lip v2 Boundary-First Gate Report

Date: 2026-06-26 KST

Status: active E7.3 lip-only validation report / Apple Vision gate v1 invalidated by preview-coordinate bug / Apple Vision gate v2 regenerated with corrected `raw-y` coordinates / runtime Apple Vision lip boundary implementation candidate retained for debug only / active lip path reverted to ARFace-attached `lip-drawn-style-atlas-v1` / Vision debug transform `raw-y->flip-y` added / soft-SDF logical multilayer lip rendering source-only pass added / Vision debug path now bakes stabilized boundary into ARFace UV mask source-only / soft-SDF multilayer offline preview evidence added / latest matte-gradient-gloss user-photo retune changed gloss to `tinted_soft_lower_wet_line` and gradient to weak outer base plus stronger inner tint / AR-runtime expected preview added / gradient_lip density-field atlas no-build correction added / latest retune UnityFramework build+sync Green / RN signed install blocked by provisioning / unsigned device-targeted RN/Xcode compile-link Green / iPhone runtime visual evidence pending

Latest lip finish handoff: `docs/roadmaps/active/E7_LIP_FINISH_NEXT_HANDOFF_KO.md` freezes `matte_lip` for validation, records the `gradient_lip` / `gloss_lip` continuous-ramp no-build retune, and keeps runtime acceptance open for the next Build Gate-approved pass.

## 1. Decision Summary

현재 립이 "스티커처럼 보이는" 문제는 두 축으로 나눈다.

1. Rendering/compositing: 기존 alpha overlay를 GPU pigment multiply로 바꿔 실제 입술 질감과 명암이 남는지 검증한다.
2. Boundary: Apple Vision `outerLips` / `innerLips` landmark contour를 앱 런타임 lip mask source로 사용한다. Offline gate는 좌표/윤곽 sanity check이고, 최종 판단은 런타임 UnityFramework + iPhone evidence로 한다.

2026-06-26 사용자 정정: 화장 표현을 판단하기 전에 입술 경계를 먼저 맞춰야 한다. 따라서 현재 검증 순서는 boundary-first다. Pigment multiply 코드는 구현 후보로 남겨둘 수 있지만, 입술 경계 gate가 통과되기 전에는 makeup acceptance로 취급하지 않는다.

## 2. Current Result

Implemented no-build/runtime-content changes:

- RN lip presets now send `blendMode="multiply"` for `matte_lip`, `gloss_lip`, `full_lip`, `gradient_lip`, and `overline_lip`.
- The three-layer batch contract remains fixed: `lip`, `cheek`, `eye`.
- HUD `recipe_applied` summary now exposes `blend`, `finish`, `maskTex`, and `src` so stale recipe/framework issues are visible.
- Unity maps `multiply` to GPU fixed-function `Blend DstColor Zero`.
- `SmoothRegionMask.shader` now has:
  - `PigmentMultiplyOrAlphaFallback` pass,
  - pigment filter output using `lerp(float3(1,1,1), pigmentColor, pigmentStrength)`,
  - alpha overlay fallback for non-multiply paths,
  - separate `GlossAdditiveHighlight` pass with `Blend One One`.
- Gloss is no longer part of the base pigment color; it is a separate additive highlight pass.
- Gradient keeps full lip coverage and changes pigment density toward the inner lip.
- 2026-06-26 soft-SDF logical multilayer source-only pass:
  - `SmoothRegionMask.shader` now softens lip mask alpha with `_Feather`-scaled 13-tap near/far sampling and separates soft/core/edge alpha for shader-internal logical layers.
  - Lip pigment is split into weak base stain multiply, lip-center/inner density, edge feather band, and a separate gloss highlight pass.
  - Gloss was simplified per user reference to a very thin lower-center white horizontal line. The shader now samples the atlas `A` channel for that line instead of estimating gloss position from UV.
  - The active lip style atlas `A(gloss)` channel was reduced from a broad `89x20-22px` region to a narrow line (`57x4px` for `lip-drawn-style-atlas-v1`, `58x4px` for `lip-style-atlas-v1`, measured at `A>8`).
  - RN lip presets now bias toward higher feather and lower coverage, while Unity lip atlas culling keeps more edge triangles available for feathering.
- 2026-06-26 later user-photo retune after the first soft-SDF UnityFramework build:
  - User iPhone screenshots showed the result was too light, `matte_lip` and `gradient_lip` were too similar, and the gloss line still looked like a white sticker.
  - Latest `matte_lip` restores stronger pigment while keeping the soft-SDF edge.
  - Latest `gradient_lip` follows the requested logical composition: weak full-lip base multiply, stronger inner/center tint, and soft outer feather so the color fades outward instead of sitting as a center sticker.
  - Latest `gloss_lip` changes diagnostics/highlight mode from the earlier near-white line to `tinted_soft_lower_wet_line` with lower additive boost.
  - This retune is now included in `TIMESTAMP=e7-matte-gradient-gloss-retune-20260626-1435`, which supersedes the previous `e7-soft-sdf-multilayer-20260626-1322` framework for lip visual review.

Apple Vision offline/runtime gate:

- Helper added: `scripts/e7_reference_atlas/run_vision_lip_boundary_gate.swift`.
- Initial v1 evidence under `evidence/e7-reference-atlas/vision-lip-boundary-v1/` is invalid for boundary decision because the preview/mask path double-flipped the CGContext coordinate space and the Vision Y conversion default was wrong for this image pipeline.
- The helper now defaults to `coordinateMode="raw-y"` and writes new evidence under `evidence/e7-reference-atlas/vision-lip-boundary-v2/`.
- Four existing user/reference images produced corrected Vision landmark outputs.
- A same-frame boundary-only compare sheet now places the current atlas and corrected Vision v2 mask side by side on `pair_face_20260622T143334Z_03/frame.png`.
- A buildless blend preview now compares current alpha overlay, pigment multiply with the current atlas, and pigment multiply with Vision v2 on the same clean frame.
- A runtime-expected preview sheet now uses the Vision v2 boundary with the current pigment-multiply approximation to compare `natural_satin`, `rose_visible`, `soft_gradient`, and `gloss_hint` without waiting for UnityFramework build.
- Runtime Vision implementation candidate is now wired:
  - RN sends `maskTextureId="lip-vision-boundary-v1"` for the default lip layer.
  - Unity iOS plugin `Assets/Plugins/iOS/E7VisionLipBoundary.mm` runs `VNDetectFaceLandmarksRequest` and returns `outerLips` / `innerLips` as `raw-y` image points.
  - `E7VisionLipBoundaryRuntime.cs` captures the current Unity frame transiently, calls the native Vision plugin, emits `e7_vision_lip_boundary`, and records `rawCameraFrameStored=false` / `offDeviceUpload=false`.
  - `E3RegionMaskOverlay.cs` uses the latest Vision polygon as a screen-space gate over ARFace mesh triangles: inside `outerLips` and outside `innerLips` renders; otherwise culled.
  - Screenshot feedback correction: runtime Vision now generates a screen-space `outerLips - innerLips` mask texture and `SmoothRegionMask.shader` can sample that mask with `_UseScreenSpaceMask`, so GPU multiply is clipped per pixel instead of relying on coarse ARFace triangle inclusion plus a 1x1 white placeholder.
  - Final no-build stabilization after inverted/delayed Vision motion: the active/default lip path is no longer the live Apple Vision screen-space mask. RN and Unity now default lip to the ARFace-attached `lip-drawn-style-atlas-v1` mask so the overlay follows ARFace mesh/UV. The Apple Vision path remains available as an explicit debug/compare candidate only.
  - When the Vision candidate is explicitly used, Unity transforms runtime landmarks `raw-y->flip-y` before screen-space culling/mask creation, expires stale Vision boundaries after `300ms`, captures at `0.20s` cadence, and logs `raw`, `flip-y`, `flip-x`, and `flip-xy` candidate bboxes with `selected=flip-y`.
  - The Vision debug path now smooths new boundary snapshots through a short transition, stores ARFace screen bounds at capture time, and can warp retained Vision points from the capture face bbox to the current ARFace bbox to reduce delayed screen-space drift.
  - Latest source-only stabilization: the explicit Vision debug/compare path now bakes the stabilized `outerLips - innerLips` boundary into a transient `512x512` ARFace UV mask using current ARFace screen projection plus barycentric back-projection, then samples that mask in face UV space with `_UseScreenSpaceMask=0`. Runtime diagnostics identify this path as `apple_vision_lip_landmark_arface_uv_baked` / `vision_arface_uv_baked_outer_minus_inner_soft_falloff` and append `->arface-uv-bake` to `visionBoundaryCoordinateMode`.
  - Vision capture temporarily suppresses Unity region overlays and the Unity debug GUI before `ReadPixels`, reducing self-feedback from the currently rendered makeup.
  - There is no second camera session and no raw frame persistence in this implementation.
  - `RNBridge` / RN HUD now surface `maskSource=apple_vision_runtime_lip_landmarks`, `boundaryRenderer=apple_vision_lip_landmark_screen_space`, Vision point counts, image size, and age.
  - Unity iOS export post-process adds `Vision.framework`; `scripts/build_m3_unityframework.sh` now verifies `Vision.framework in Frameworks`.

## 3. Apple Vision Gate Decision

Decision: `pending_manual_review`

Evidence:

- Invalidated previous gate: `evidence/e7-reference-atlas/vision-lip-boundary-v1/contact_sheet.png`
- Corrected gate: `evidence/e7-reference-atlas/vision-lip-boundary-v2/contact_sheet.png`
- Corrected gate summary: `evidence/e7-reference-atlas/vision-lip-boundary-v2/summary.md`
- Corrected gate JSON: `evidence/e7-reference-atlas/vision-lip-boundary-v2/summary.json`
- Same-frame compare crop: `evidence/e7-reference-atlas/vision-lip-boundary-v2/boundary_compare/atlas_vs_vision_boundary_mouth_crop.png`
- Same-frame compare full sheet: `evidence/e7-reference-atlas/vision-lip-boundary-v2/boundary_compare/atlas_vs_vision_boundary_full.png`
- Same-frame compare metrics: `evidence/e7-reference-atlas/vision-lip-boundary-v2/boundary_compare/summary.json`
- Blend preview sheet: `evidence/e7-reference-atlas/vision-lip-boundary-v2/blend_preview/alpha_vs_pigment_multiply_sheet.png`
- Blend preview metrics: `evidence/e7-reference-atlas/vision-lip-boundary-v2/blend_preview/summary.json`
- Runtime expected preview without boundary line: `evidence/e7-reference-atlas/vision-lip-boundary-v2/expected_runtime_preview/expected_runtime_vision_lip_sheet_no_boundary.png`
- Runtime expected preview with Vision edge line: `evidence/e7-reference-atlas/vision-lip-boundary-v2/expected_runtime_preview/expected_runtime_vision_lip_sheet.png`
- Runtime expected preview summary: `evidence/e7-reference-atlas/vision-lip-boundary-v2/expected_runtime_preview/summary.json`

Reason:

- v1 cannot be used because the preview was upside-down / oppositely placed by our coordinate handling, not by the source photo.
- v2 uses `VNFaceLandmarkRegion2D.pointsInImage(imageSize:)` with `raw-y` drawing coordinates and no extra CGContext flip.
- On the clean reference frame, corrected Vision v2 is close to the current atlas: IoU `0.878726`, Vision outside-atlas ratio `0.045300`, atlas-missing-in-Vision ratio `0.083041`.
- Buildless blend preview on the same frame supports the pigment-multiply direction for texture/detail preservation: alpha overlay luma std ratio `0.440485`, pigment multiply atlas ratio `0.991671`, pigment multiply Vision ratio `0.998322`.
- v2 now needs user/manual review against the actual visible lip boundary, especially mouth corners, cupid bow, inner-mouth exclusion, and lower-lip coverage.

Consequence:

- Runtime Apple Vision is now the lip boundary implementation candidate, but not accepted evidence yet.
- Do not introduce a second camera session.
- Keep `vision-lip-boundary-v1` as invalidated evidence only.
- Use `vision-lip-boundary-v2` as the coordinate sanity reference for the runtime path.
- Treat the clean-frame result as "boundary candidate roughly aligned"; UnityFramework build/sync is complete, but real acceptance still requires signed RN install plus iPhone runtime logs/photos showing the Vision boundary fits the lips.
- 2026-06-26 build update: UnityFramework build/sync is now complete; the remaining acceptance gap is signed RN install plus iPhone runtime visual/log evidence on `202268054(여서진)`.
- 2026-06-26 screenshot feedback update: screen-space mask correction is implementation/static evidence only. It still needs a fresh UnityFramework/RN install and iPhone runtime photos/logs before any boundary acceptance claim.
- 2026-06-26 screenshot feedback build update: the screen-space mask UnityFramework build/sync is Green and unsigned device-targeted RN/Xcode compile/link is Green, but signed install is still blocked by missing provisioning for `com.yeoseojin.makeupar.validation202268054`. This is not runtime acceptance.
- 2026-06-26 final stabilization build update: because real-device feedback showed inverted and delayed Vision motion, the active/default lip renderer is now the ARFace-attached atlas path again. Vision screen-space is retained only for explicit compare/debug, with `raw-y->flip-y`, stricter freshness, and transform candidate logging. UnityFramework build/sync and unsigned device-targeted RN/Xcode compile/link are Green for this latest fallback. Signed install remains blocked by missing provisioning for `com.yeoseojin.makeupar.validation202268054`, so this is not runtime acceptance.
- 2026-06-26 soft-SDF logical multilayer update: user screenshots showed hard lip edges and sticker-like gloss/gradient, and the follow-up reference asked for one very thin white horizontal line. The latest source-only pass softens mask sampling, lowers lip atlas culling threshold, keeps minimum effective feather, adds shader-internal base/inner/edge/gloss layers, changes gloss to an atlas `A` channel line mask, and adds Vision transition/face-bbox stabilization plus render-time face motion diagnostics. This has no UnityFramework/RN install or iPhone runtime photo/log acceptance yet, so E7.3 remains Yellow.
- 2026-06-26 Vision ARFace UV-bake update: the retained Vision candidate is no longer only a screen-space shader mask. It now back-projects the stabilized Vision lip polygon through current ARFace triangles into a transient UV mask and renders that mask as a face-attached UV texture. This better matches the validation goal of using Vision as a boundary seed/gate rather than as live screen tracking, but it is source-only evidence until a fresh UnityFramework/RN install and iPhone photo/log review are collected.
- 2026-06-26 soft-SDF offline preview update: a buildless preview sheet now compares original, hard alpha sticker-risk baseline, soft-SDF matte, soft-SDF gradient, thin wet-line gloss, and layer diagnostic from the same clean reference frame and lip atlas round-trip mask. This supports the rendering direction but does not replace Unity runtime/iPhone visual acceptance.
- 2026-06-26 matte/gradient/gloss user-photo retune: after real-device photos from the soft-SDF build, the shader/RN presets were retuned to make matte stronger, make gradient visibly different from matte by emphasizing inner tint over a weak outer wash, and make gloss a tinted narrow lower wet-line rather than a pure white additive line. A fresh UnityFramework build/sync now exists for this retune, but signed RN install and iPhone visual acceptance are still blocked by provisioning.
- 2026-06-26 lip finish multi-agent handoff: user screenshots from the latest build freeze `matte_lip` as the E7.3 validation baseline. The follow-up no-build pass replaced `gradient_lip` thresholded mask/core composition with a continuous soft ramp and retuned `gloss_lip` to preserve red base before localized tinted wet-line shine. Runtime acceptance remains open until a Build Gate-approved iPhone screenshot/log pass. Full handoff and next-session prompt: `docs/roadmaps/active/E7_LIP_FINISH_NEXT_HANDOFF_KO.md`.
- 2026-06-26 AR-runtime expected preview update: `scripts/e7_reference_atlas/make_lip_runtime_ar_expected_preview.py` now renders expected `matte_lip`, `gradient_lip`, and `gloss_lip` through the actual RN recipe, Unity material, ARFace UV mesh culling, shader multiply pass, and gloss additive pass. The generated sheet is `evidence/e7-reference-atlas/lip-style-atlas-v1/ar_runtime_expected_20260626/ar_runtime_expected_sheet.png`. Verdict is `expected_ar_preview_review`: gradient/gloss look directionally usable on the reference ARFace projection, but conservative guards still flag gradient ramp roughness and gloss full-pigment footprint expansion, so this does not replace iPhone runtime visual acceptance.
- 2026-06-26 gradient density-field atlas update: `gradient_lip` no longer relies on the default lip atlas B channel as a painted/banded center region. It now uses a dedicated `lip-drawn-gradient-density-atlas-v1` resource generated by distance transform, while matte/gloss remain on `lip-drawn-style-atlas-v1`. The shader gradient branch now uses one density curve and one color ramp (`outerMlbbColor -> innerRedColor`) instead of additive outer/mid/inner layers. AR expected gradient guards pass after this correction (`outsideSourceDilatedRatio=0.0589`, `adjacentDensityDeltaP95=0.0456`, `centerLineMaxJump=0.0505`), but overall preview is still review because gloss is deferred.

## 4. No-Build Verification

Latest no-build checks on 2026-06-26 KST:

- RN Jest: `11` tests passed.
- TypeScript: `./node_modules/.bin/tsc --noEmit` passed.
- RN lint: `npm run lint` passed.
- iOS native Vision plugin syntax: `xcrun --sdk iphoneos clang++ -fsyntax-only ... E7VisionLipBoundary.mm` passed.
- Runtime expected preview script compile passed: `scripts/e7_reference_atlas/make_runtime_vision_lip_expected_preview.py`.
- Shader/static guard confirms:
  - `PigmentMultiplyOrAlphaFallback`,
  - `GlossAdditiveHighlight`,
  - `Blend One One`,
  - Unity multiply maps to `BlendMode.DstColor` / `BlendMode.Zero`,
  - RN HUD summary exposes `blend`, `finish`, `maskTex`, and `maskSource`.
- Apple Vision helper Swift typecheck passed.
- Boundary compare helper Python compile passed.
- Blend preview helper Python compile passed.
- Unity batchmode import/compile previously passed before the runtime Vision plugin with log `evidence/logs/e7-lip-v2-boundary-pigment-unity-batchmode-20260626.log`.
  - Log records `CompileScripts: 1017.874ms`.
  - No `Shader error`, `error CS`, or compile failure was found.
  - Log ends with `Exiting batchmode successfully now!`.
- Unity batchmode after runtime Vision wiring was attempted at `evidence/logs/e7-vision-lip-runtime-unity-batchmode-20260626.log` but did not reach compile because Unity Licensing Client/Headless licensing hung during editor startup. This is a tooling blocker, not runtime acceptance evidence.
- `git diff --check` passed.
- Screenshot feedback screen-space mask correction checks passed: scoped `git diff --check` for the touched Unity files, RN Jest (`11` tests), TypeScript, RN lint, and a Unity DLL referenced Roslyn script compile. Full `git diff --check` still fails on pre-existing dirty Unity scene trailing whitespace outside this correction.
- Final ARFace-attached fallback / Vision transform checks passed: RN Jest (`11` tests), TypeScript, RN lint, scoped `git diff --check`, and Unity DLL-referenced Roslyn compile for the changed/runtime-dependent C# files. Roslyn emitted only existing JSON payload field warnings (`CS0649`).
- Soft-SDF logical multilayer source-only checks passed: RN Jest (`13` tests, including matte `gloss=none`, wide feather `soft=feather_scaled_13tap_near_far`, `featherPx=3.45/6.38`, Vision capture-motion diagnostics, render-stage `visionMotion=0.276/medium_face_motion`, soft bake `maskDiag=vision_arface_uv_baked_outer_minus_inner_soft_falloff`, and Vision event `motion=0.390/large_face_motion`), TypeScript, RN lint, scoped `git diff --check`, shader/static guard search for the new soft/core/multilayer/gloss paths, preview regeneration, atlas guard, Python compile, runtime log verifier contract guard (`runtimeVerifier=guarded`), and Unity batchmode import/compile in `evidence/logs/e7-soft-sdf-a-channel-line-unity-batchmode-20260626.log`. The latest guard also locks Vision freshness/transition/face-bbox warp markers (`FreshBoundaryMaxAgeMs=300`, `CaptureIntervalSeconds=0.20f`, `face_bbox_translate_scale`, `large_face_motion_smooth`, `VisionUvMaskSoftSplatRadius`, and `visionBoundaryFaceMotionRisk`) and shader feather radius markers (`FeatherTexelRadius`, near/far texel rings, near radius `3.447px`, far radius `6.377px`, plus runtime `maskSoftSampleMode` / `maskFeatherNearRadiusPx` / `maskFeatherFarRadiusPx`) so hard-edge or delayed screen-space Vision behavior is less likely to regress silently. The latest soft-white line guard records `wetLineActivePixels=493`, `wetLineMeanLumaBoost=0.1968`, `thinWetLine lumaCorrelation=0.8531`, and one-line shape metrics (`bbox=119x5px`, `aspect=23.8`, `height/lip=0.040`, `width/lip=0.509`, `componentCount=1`). The Unity batchmode log records both lip style atlas textures and `SmoothRegionMask.shader` imported, `CompileScripts: 3202.976ms`, no `Shader error` / `error CS`, and `Exiting batchmode successfully now!`.
- Vision ARFace UV-bake source-only checks passed: scoped `git diff --check`, Unity DLL-referenced Roslyn compile for all six runtime scripts, Unity batchmode import/compile, RN Jest (`11` tests), TypeScript, and RN lint. Roslyn emitted only existing JSON payload field warnings (`CS0649`). The Unity batchmode log `evidence/logs/e7-vision-arface-uv-bake-diag-unity-batchmode-20260626.log` records `CompileScripts: 2965.738ms`, no `Shader error` / `error CS`, and `Exiting batchmode successfully now!`.
- Soft-SDF offline preview checks passed: Python compile for `scripts/e7_reference_atlas/make_lip_soft_sdf_multilayer_preview.py`, preview generation under `evidence/e7-reference-atlas/lip-style-atlas-v1/soft_sdf_multilayer_preview_20260626/`, and `scripts/e7_reference_atlas/verify_lip_soft_sdf_multilayer.py` guard coverage for shader soft-SDF layers, Vision ARFace UV baking, RNBridge runtime diagnostics, edge feather band mean, detail-preservation luma correlation, and single-line gloss.
- Matte/gradient/gloss user-photo retune checks passed after updating RN presets, Unity material scaling, shader logical layer weights, preview generation, and verifier expectations: RN Jest (`13` tests), TypeScript, RN lint, atlas guard, soft-SDF verifier (`softMatteLumaStdRatio=0.7951`, `softGradientLumaStdRatio=1.2470`, `softGradientLumaCorrelation=0.9364`, `wetLineMeanLumaBoost=0.0553`, `wetLineComponentCount=1`), scoped `git diff --check`, preview regeneration, and Unity batchmode import/compile in `evidence/logs/e7-matte-gradient-gloss-retune-unity-batchmode-20260626.log` with `CompileScripts: 3287.457ms`, no `Shader error` / `error CS`, and `Exiting batchmode successfully now!`.
- Matte/gradient/gloss retune UnityFramework build/sync passed with `TIMESTAMP=e7-matte-gradient-gloss-retune-20260626-1435`: Unity export verified ARKit/Vision/MetalPerformanceShaders links, Xcode UnityFramework recorded `** BUILD SUCCEEDED **`, RN/package frameworks were synced as arm64 Mach-O (`113M`, Unity `Data` `18M`), and the measured wrapper time was `real 134.45s` while reusing Unity `Library/` and Xcode DerivedData.
- RN signed install/build to `202268054(여서진)` failed at the known provisioning gate: no iOS App Development profile for `com.yeoseojin.makeupar.validation202268054` with automatic signing disabled. The follow-up unsigned device-targeted Xcode build with `CODE_SIGNING_ALLOWED=NO` succeeded and embedded `UnityFramework.framework` into `MakeupARValidation.app`, so compile/link/package is Green but runtime visual acceptance is still missing.

UnityFramework/RN build attempt on 2026-06-26 KST:

- UnityFramework build/sync succeeded with `TIMESTAMP=e7-vision-lip-runtime-20260626-0245`.
- Unity iOS export verified `Vision.framework in Frameworks`.
- Xcode linked UnityFramework with `-framework Vision` and recorded `** BUILD SUCCEEDED **`.
- RN/package framework paths both contain arm64 `UnityFramework.framework` artifacts (`113M`, Unity `Data` `18M`).
- RN install must target `202268054(여서진)` via `--udid 00008110-0001794E0CD9801E`; the old `위승철의 iPhone` device label is invalid for future builds.
- RN CLI build by UDID reached Xcode signing, then failed before install because no development provisioning profile exists for `com.yeoseojin.makeupar.validation202268054`.
- Evidence logs:
  - `evidence/logs/m3-repro-unity-export-e7-vision-lip-runtime-20260626-0245.log`
  - `evidence/logs/m3-repro-xcodebuild-unityframework-e7-vision-lip-runtime-20260626-0245.log`
  - `evidence/logs/m3-repro-artifact-verification-e7-vision-lip-runtime-20260626-0245.log`
  - `evidence/logs/e7-vision-lip-runtime-rn-ios-device-20260626-0245.log`
  - `evidence/logs/e7-vision-lip-runtime-rn-ios-udid-20260626-0245.log`

Screenshot feedback screen-space mask UnityFramework/RN build attempt on 2026-06-26 KST:

- Pre-build checks passed: RN Jest (`11` tests), TypeScript, RN lint, scoped `git diff --check`, and Unity DLL-referenced Roslyn compile. Full `git diff --check` still fails only on pre-existing dirty scene whitespace in `MakeupARFaceValidation.unity`.
- Unity/Hub/Licensing process cleanup found no stale Unity build blockers.
- UnityFramework build/sync succeeded with `TIMESTAMP=e7-vision-screen-mask-20260626-0315`.
- Unity iOS export verified `Vision.framework`, `ARKit.framework`, and Unity ARKit native library links.
- Xcode UnityFramework target recorded `** BUILD SUCCEEDED **`; RN/package framework paths both contain arm64 `UnityFramework.framework` artifacts (`113M`, Unity `Data` `18M`).
- `xcrun devicectl` confirmed `202268054(여서진)` is connected; RN CLI uses `--udid 00008110-0001794E0CD9801E`.
- Signed RN install by UDID reached Xcode signing, then failed before install because no development provisioning profile exists for `com.yeoseojin.makeupar.validation202268054` and automatic signing is disabled.
- A device-targeted unsigned Xcode build with `CODE_SIGNING_ALLOWED=NO` succeeded and embedded the new UnityFramework. This proves compile/link/framework packaging only.
- No iPhone runtime boundary photo/log acceptance was collected; E7.3 remains Yellow.
- Evidence logs:
  - `evidence/logs/m3-repro-unity-export-e7-vision-screen-mask-20260626-0315.log`
  - `evidence/logs/m3-repro-xcodebuild-unityframework-e7-vision-screen-mask-20260626-0315.log`
  - `evidence/logs/m3-repro-artifact-verification-e7-vision-screen-mask-20260626-0315.log`
  - `evidence/logs/e7-vision-screen-mask-rn-ios-device-20260626-0315.log`
  - `evidence/logs/e7-vision-screen-mask-xcodebuild-device-nosign-20260626-0315.log`

Final ARFace-attached fallback / Vision debug transform build checkpoint on 2026-06-26 KST:

- Active/default RN lip mask: `lip-drawn-style-atlas-v1`.
- Unity/RNBridge default lip mask: `lip-drawn-style-atlas-v1`.
- Retained explicit Vision candidate: `lip-vision-boundary-v1`.
- Vision candidate transform: `raw-y->flip-y`.
- Vision stale max age: `300ms`.
- Vision capture cadence: `0.20s`.
- Runtime debug log added: `vision_lip_boundary_transform_candidates` with `raw`, `flip-y`, `flip-x`, and `flip-xy` bbox summaries.
- Unity/Hub/Licensing process cleanup found no stale Unity build blockers.
- UnityFramework build/sync succeeded with `TIMESTAMP=e7-arface-lip-fallback-20260626-0349`.
- Unity iOS export verified `Vision.framework`, `ARKit.framework`, and Unity ARKit native library links.
- Xcode UnityFramework target recorded `** BUILD SUCCEEDED **`; RN/package framework paths both contain arm64 `UnityFramework.framework` artifacts (`113M`, Unity `Data` `18M`).
- Signed RN install by UDID reached Xcode signing, then failed before install because no development provisioning profile exists for `com.yeoseojin.makeupar.validation202268054` and automatic signing is disabled.
- A device-targeted unsigned Xcode build with `CODE_SIGNING_ALLOWED=NO` succeeded and embedded the new UnityFramework. This proves compile/link/framework packaging only.
- No iPhone runtime boundary photo/log acceptance was collected; E7.3 remains Yellow.
- Evidence logs:
  - `evidence/logs/m3-repro-unity-export-e7-arface-lip-fallback-20260626-0349.log`
  - `evidence/logs/m3-repro-xcodebuild-unityframework-e7-arface-lip-fallback-20260626-0349.log`
  - `evidence/logs/m3-repro-artifact-verification-e7-arface-lip-fallback-20260626-0349.log`
  - `evidence/logs/e7-arface-lip-fallback-rn-ios-device-20260626-0349.log`
  - `evidence/logs/e7-arface-lip-fallback-xcodebuild-device-nosign-20260626-0349.log`

Soft-SDF logical multilayer source-only checkpoint on 2026-06-26 KST:

- Active/default RN lip mask remains `lip-drawn-style-atlas-v1`.
- Lip atlas mask threshold is lower and effective feather has a higher validation floor so the shader can render a soft edge instead of a hard cut.
- Shader rendering now uses logical layers inside the existing material pass structure: weak base stain, inner/center density, soft edge band, and separate gloss highlight.
- Latest user-photo retune keeps the same logical layer structure but raises matte/gradient pigment strength after the real-device result became too faint.
- Gradient is now explicitly modeled as weak outer base multiply plus stronger inner/center tint plus a soft edge fade; this is the validation target for the Korean-style gradient lip look.
- Gloss highlight remains intentionally minimal but is no longer a pure white line. Runtime diagnostics now expose `glossHighlightMode=tinted_soft_lower_wet_line` for `gloss_lip`, and RN tests still verify matte events stay at `gloss=none`.
- Vision debug candidate now records transition progress, stabilization mode, capture-time face bounds availability, and can face-bbox warp stale screen points to the current ARFace projection. It also reports `visionBoundaryFaceMotionScore`, `visionBoundaryFaceCenterShiftPx`, `visionBoundaryFaceScaleDelta`, and `visionBoundaryFaceMotionRisk` so device logs can distinguish low/medium/large compensation while reviewing delayed motion.
- Latest soft-white A-channel line / wide-feather retune passed shader/static guard, atlas guard, RN Jest, TypeScript, RN lint, scoped `git diff --check`, preview regeneration, Python compile, runtime log verifier synthetic pass/expected-fail, and Unity batchmode import/compile. The latest batchmode log `evidence/logs/e7-soft-sdf-a-channel-line-unity-batchmode-20260626.log` records both lip style atlas textures and `SmoothRegionMask.shader` imported, `CompileScripts: 3202.976ms`, no `Shader error` / `error CS`, and `Exiting batchmode successfully now!`.
- Latest matte/gradient/gloss user-photo retune then passed RN Jest, TypeScript, RN lint, atlas guard, soft-SDF verifier, scoped `git diff --check`, preview regeneration, Unity batchmode import/compile, UnityFramework build/sync, and unsigned RN device-targeted compile/link. Signed RN install and iPhone runtime visual acceptance are still blocked by provisioning, so E7.3 remains Yellow.
- Latest gradient/gloss continuous-ramp no-build retune keeps `matte_lip` frozen, replaces the `gradient_lip` thresholded `max(gradientMask, centerDensity) * fullCore` path with continuous `atlasGradientGuide` / `continuousGradientDensity` / `midGradientRamp` / `innerGradientDensity` / `gradientTintMix`, and strengthens only `gloss_lip` red base plus localized tinted wet-line shine. Checks passed: `git diff --check`, atlas guard, soft-SDF verifier, RN Jest (`13`), TypeScript, RN lint, Python compile, preview regeneration, and Unity batchmode import/compile in `evidence/logs/e7-gradient-gloss-continuous-ramp-unity-batchmode-20260626.log` with `CompileScripts: 3074.723ms`, no `Shader error` / `error CS`, and `Exiting batchmode successfully now!`. Preview guard metrics include `gradientTransitionWidthToLipWidth=0.9744`, `gradientInnerOuterStrengthRatio=3.2299`, `gradientRampMaxAdjacentDeltaP95=0.0110`, `wetLineMeanLumaBoost=0.0767`, and `glossRedBasePreservationRatio=1.0452`. No UnityFramework/RN real-device build or runtime visual acceptance was run for this source-only checkpoint.

Vision ARFace UV-bake source-only checkpoint on 2026-06-26 KST:

- Active/default RN lip mask remains `lip-drawn-style-atlas-v1`.
- The retained explicit Vision candidate still starts from Apple Vision `outerLips` / `innerLips`, but after transform/smoothing/face-bbox stabilization it is baked into a transient ARFace UV mask rather than sampled as a live screen-space shader texture.
- The bake projects current ARFace triangles to screen, samples points inside the stabilized Vision lip polygon, back-projects those samples with barycentric weights into UV, writes a `512x512` RGBA style-compatible mask with soft falloff splats, and renders with `_UseScreenSpaceMask=0`.
- Runtime diagnostics should show `boundaryRenderer=apple_vision_lip_landmark_arface_uv_baked`, `meshCullingMode=apple_vision_lip_landmark_arface_uv_baked`, `visionBoundaryCoordinateMode` ending in `->arface-uv-bake`, `maskTextureDiagnosticStatus=vision_arface_uv_baked_outer_minus_inner_soft_falloff`, and `vision_lip_boundary_arface_uv_bake` log fields for hit triangles/samples plus `softSplatRadius=3`.
- Unity batchmode import/compile passed for this source-only checkpoint with no shader or C# compile error in `evidence/logs/e7-vision-arface-uv-bake-diag-unity-batchmode-20260626.log`.
- No UnityFramework build, RN install, or iPhone runtime visual acceptance was collected for this source-only checkpoint; E7.3 remains Yellow.

Soft-SDF logical multilayer offline preview checkpoint on 2026-06-26 KST:

- Preview script: `scripts/e7_reference_atlas/make_lip_soft_sdf_multilayer_preview.py`.
- Inputs: clean reference frame `pair_face_20260622T143334Z_03/frame.png` and `lip_atlas_roundtrip_mask.png`.
- Output sheet: `evidence/e7-reference-atlas/lip-style-atlas-v1/soft_sdf_multilayer_preview_20260626/soft_sdf_multilayer_sheet.png`.
- The latest sheet compares original, hard alpha baseline, stronger soft-SDF matte, soft outer wash plus stronger inner gradient, tinted lower wet-line gloss, and layer diagnostic.
- Summary metrics after the latest continuous-ramp retune record hard alpha `lumaStdRatio=0.4046`, soft matte `0.7951`, soft gradient `1.3368`, soft matte/gradient luma correlation `0.8712` / `0.9472`, thin tinted wet-line luma correlation `0.8984`, `edgeBandMean=0.5947`, `gradientTransitionWidthToLipWidth=0.9744`, `gradientInnerOuterStrengthRatio=3.2299`, `gradientRampMaxAdjacentDeltaP95=0.0110`, `gradientCenterBoundaryJump=0.1243`, `wetLineActivePixels=493`, `wetLineMeanLumaBoost=0.0767`, `glossRedBasePreservationRatio=1.0452`, and one-line shape `aspect=23.8` / `height/lip=0.040` / `width/lip=0.509` / `componentCount=1`.
- This is offline preview evidence only; no UnityFramework build, RN install, or iPhone runtime visual acceptance was collected, so E7.3 remains Yellow.

## 5. Multilayer Lip Rendering Handoff

Purpose for the next Codex or multi-agent worker:

- Continue E7.3 lip-only validation from the current ARFace-attached `lip-drawn-style-atlas-v1` default path.
- Treat `docs/roadmaps/active/E7_LIP_FINISH_NEXT_HANDOFF_KO.md` as the current detailed handoff for lip finish work.
- Do not modify `matte_lip`; it is frozen as the validation baseline from the latest user screenshot.
- Fix the remaining user-visible issues in `gradient_lip` and `gloss_lip` while preserving the frozen `matte_lip` baseline.
- Keep Apple Vision as explicit debug/compare only; do not restore live Vision screen-space masking as the default lip renderer.
- Stay validation-only. Do not claim E7.3 Green, product readiness, or product-quality makeup without iPhone runtime visual/log evidence.

Current implementation status:

- RN/Unity integration and UnityFramework packaging are functional.
- The active/default lip mask is `lip-drawn-style-atlas-v1`, attached to ARFace UV/mesh.
- GPU multiply is already used for pigment preservation.
- Gloss highlight is already separated from the base pigment pass.
- Offline soft-SDF logical multilayer preview exists and should be treated as the current direction of travel.
- Signed iPhone install remains blocked by local provisioning for `com.yeoseojin.makeupar.validation202268054`; unsigned device-targeted compile/link has succeeded in prior build gates.

Estimated completion by area:

- RN/Unity/ARKit integration: about `85%` for validation.
- ARFace-attached lip placement: about `65%`.
- Lip boundary naturalness: about `40%`.
- Texture-preserving multiply lip color: about `55%`.
- Gradient lip naturalness: about `25-35%`.
- Gloss lip naturalness: about `25-35%`.
- Latest runtime visual acceptance: `0%` until a fresh signed install or user-provided runtime screenshots confirm the new build.

Primary user feedback to address:

- Lip color is visible and tracks the mouth, but the outer boundary still appears too hard.
- Feather/blur looks insufficient, especially around the upper lip bow, mouth corners, and lower-lip outer edge.
- Gloss feels like a broad artificial overlay rather than a small wet highlight.
- Gradient feels like a mask color change rather than natural inner-lip staining.
- The desired direction is logical multilayer rendering: base stain, inner tint, soft edge feather, and optional gloss highlight.

Recommended implementation priority:

1. Fix lip edge softness before increasing gloss or gradient strength.
2. Keep one ARFace-attached mask path and improve shader-side soft alpha/SDF-like falloff.
3. Implement logical multilayer composition inside the shader rather than stacking many transparent Unity meshes.
4. Keep `matte_lip` frozen, and retune only `gradient_lip` / `gloss_lip` as different combinations of the same layers.
5. Add diagnostics for the soft mask/layer mode so runtime logs can prove the intended path is active.

Recommended layer model:

```txt
finalLip =
  base stain multiply
+ soft outer edge wash
+ inner gradient tint
+ optional tinted gloss highlight
```

Layer guidance:

- `base stain`: weak multiply tint across the lip, preserving skin/lip luminance and texture.
- `soft outer edge wash`: weaker color near the outer boundary using SDF-like or blurred alpha falloff.
- `inner gradient tint`: stronger pigment near the inner lip or lip center; avoid a simple mechanical vertical UV gradient if possible.
- `gloss highlight`: narrow tinted wet-line or lower-lip center/streak highlight only; avoid broad pure-white screen/additive over the whole lip.

Shader-side direction:

- Inspect `SmoothRegionMask.shader` first.
- Avoid treating mask alpha as a hard 0/1 threshold.
- If the atlas alpha is binary-like, approximate soft alpha with a cheap 5-tap or 9-tap neighborhood sample before `smoothstep`.
- Split fill and edge values conceptually:

```hlsl
float blurredMask = ...; // 5-tap or 9-tap local alpha average
float edgeMask = smoothstep(edgeLow, edgeHigh, blurredMask);
float fillMask = smoothstep(fillLow, fillHigh, blurredMask);
float edgeBand = saturate(edgeMask - fillMask);
```

- Use `fillMask` for stronger inner/base color.
- Use `edgeBand` or `edgeMask` for weak outer wash only.
- Keep gloss masked by fill/inner areas so it does not brighten surrounding skin.

Finish-specific expectations:

- `matte_lip`: base multiply plus soft edge only; minimal/no specular; should preserve lip creases.
- `gradient_lip`: weak outer base plus stronger inner/center tint; edge should fade softly.
- `gloss_lip`: base multiply plus a thin tinted wet-line/lower-lip highlight; no broad white shine.

Suggested diagnostics:

```txt
maskSoft=on
softSample=5tap or 9tap
edgeLow=...
edgeHigh=...
fillLow=...
fillHigh=...
layerModel=base_edge_inner_gloss
glossHighlightMode=tinted_soft_lower_wet_line
gradientMode=soft_inner_tint
```

Minimum no-build verification before any build gate:

- RN Jest.
- TypeScript.
- RN lint.
- Scoped `git diff --check`.
- Shader/static guard if available.
- Atlas/soft-SDF preview regeneration if the mask or layer math changes.
- Unity batchmode import/compile or Roslyn/static Unity C# check when Unity scripts changed.

Build gate reminder:

- Before UnityFramework or RN real-device build, report the build question, primary path, compare-only paths, validation contract, evidence matrix, and out-of-scope items.
- The primary path should remain ARFace-attached `lip-drawn-style-atlas-v1` with shader-side logical multilayer soft rendering.
- Compare-only paths may include Apple Vision debug, hard-alpha baseline, and offline soft-SDF preview.

Do not do in this handoff:

- Do not make Apple Vision live screen-space mask the default again.
- Do not add a second camera session.
- Do not introduce Core ML, MediaPipe runtime, backend upload, raw-frame storage, or product implementation.
- Do not solve this by stacking many real transparent meshes without a measured reason.
- Do not mark E7.3 Green without real-device runtime evidence.

## 6. Face Parsing Note

The user review correctly points toward face parsing / lip segmentation as the more appropriate boundary class.

That is not part of the current v2 implementation scope. If the team expands scope, the next boundary experiment should be a separate offline face parsing / lip segmentation gate:

- same 3+ user photos,
- current `lip-drawn-style-atlas-v1` baseline,
- invalidated v1 Vision candidate and corrected v2 Vision candidate for comparison,
- face parsing or lip segmentation mask candidate,
- contact sheet comparing boundary fit, inner-mouth exclusion, and full lip coverage.

No runtime face parsing, Core ML model integration, MediaPipe runtime, native Metal path, backend upload, or product-readiness claim is authorized by this v2 report.

## 7. Build Gate

Before any UnityFramework or RN real-device build, stop and report:

- build question,
- primary path: runtime Apple Vision lip boundary using `outerLips` / `innerLips` as the lip gate first; pigment multiply remains a rendering candidate after boundary fit is accepted,
- boundary gate result: Vision v2 is roughly aligned on the clean frame; runtime Vision integration candidate is implemented but not accepted until UnityFramework + iPhone evidence,
- compare-only paths: current alpha overlay / current user-drawn atlas / v1 invalid Vision candidate / v2 corrected Vision candidate / buildless blend preview,
- validation contract: three batched layers only (`lip`, `cheek`, `eye`),
- evidence matrix,
- out-of-scope items: Core ML, MediaPipe runtime, native Metal, second camera session, product readiness.

Approved build command remains:

```bash
bash scripts/build_m3_unityframework.sh
```

Approved RN/Xcode device target after sync:

```bash
cd rn/MakeupARValidation
npm run ios -- --udid 00008110-0001794E0CD9801E --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK
```

## 8. Acceptance Bar

This v2 pass must answer boundary first:

```txt
Does the corrected Apple Vision lip contour fit the visible lip boundary well enough to become the makeup mask source?
```

It cannot mark E7.3 Green, product readiness, or product-quality lip rendering.

Boundary acceptance needs:

- mouth corners included,
- upper lip cupid bow not inverted or displaced,
- lower lip coverage not shifted onto chin skin,
- inner mouth / teeth excluded,
- stable enough on frontal and yaw screenshots to justify a runtime Vision plugin spike.
