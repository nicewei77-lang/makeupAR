# E7 Lip v2 Boundary-First Gate Report

Date: 2026-06-26 KST

Status: active E7.3 lip-only validation report / Apple Vision gate v1 invalidated by preview-coordinate bug / Apple Vision gate v2 regenerated with corrected `raw-y` coordinates / runtime Apple Vision lip boundary implementation candidate retained for debug only / active lip path reverted to ARFace-attached `lip-drawn-style-atlas-v1` / Vision debug transform `raw-y->flip-y` added / UnityFramework build+sync Green for latest fallback / unsigned RN device-targeted compile Green / signed install blocked by provisioning / iPhone runtime visual evidence pending

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

## 5. Face Parsing Note

The user review correctly points toward face parsing / lip segmentation as the more appropriate boundary class.

That is not part of the current v2 implementation scope. If the team expands scope, the next boundary experiment should be a separate offline face parsing / lip segmentation gate:

- same 3+ user photos,
- current `lip-drawn-style-atlas-v1` baseline,
- invalidated v1 Vision candidate and corrected v2 Vision candidate for comparison,
- face parsing or lip segmentation mask candidate,
- contact sheet comparing boundary fit, inner-mouth exclusion, and full lip coverage.

No runtime face parsing, Core ML model integration, MediaPipe runtime, native Metal path, backend upload, or product-readiness claim is authorized by this v2 report.

## 6. Build Gate

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

## 7. Acceptance Bar

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
