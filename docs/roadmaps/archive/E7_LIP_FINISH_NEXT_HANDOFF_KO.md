# E7 립 피니시 다음 작업 핸드오프

Date: 2026-06-26 KST

Status: E7.3 validation-only 립 피니시 핸드오프 / 매트 freeze / `gradient_lip` user accepted + freeze / `gloss_lip` user-drawn lower-lip specular cluster no-build tweak, UnityFramework rebuild/runtime acceptance pending

## 1. 현재 결정

이 문서는 다음 세션 또는 멀티에이전트 작업자가 바로 이어받기 위한 핸드오프다.

- `matte_lip`: 완료/freeze. 사용자가 명시적으로 다시 열지 않는 한 더 건드리지 않는다.
- `gradient_lip`: 완료/freeze. 사용자 실기기 HUD screenshot `IMG_5268.PNG`에서 RED 100% gradient 결과를 승인했다. 사용자가 명시적으로 다시 열지 않는 한 더 건드리지 않는다.
- `gloss_lip`: 이전 clustered gloss 후보는 사용자 실기기 사진에서 작은 흰 조각처럼 보여 reject. 더 넓은 matte-base wet-sheen 후보와 단일 1px streak 후보도 superseded. 최신 active 후보는 matte와 같은 tint base를 유지하고, 별도 atlas A-channel로 사용자가 고른 lower-lip specular cluster를 만든다. 위쪽 조각은 제거했고 아래쪽 조각은 1px 올린 상태다. 이 final tweak은 buildless AR expected preview와 soft-SDF verifier까지 통과했지만 UnityFramework rebuild/RN install/runtime 사진 승인은 아직 없다.
- E7.3은 계속 Yellow다. 이 작업은 validation-only 렌더러 하드닝이며 제품급 립 메이크업 claim은 금지한다.

이번 이어서 작업한 체크포인트:

- 멀티에이전트 분석 결과:
  - Gradient: shader-first로 continuous ramp를 구현하고, old `max(gradientMask, centerDensity) * fullCore` 패턴은 guard에서 금지한다.
  - Gloss: A-channel mask만으로는 부족하고 red base가 먼저 유지되어야 한다. normal/view-direction highlight는 이번 E7.3 validation pass에서는 보류한다.
- `matte_lip` RN preset, Unity material scale, shader matte branch는 수정하지 않았다.
- `gradient_lip`는 같은 선택 색상 `_RegionColor`를 유지한 채 B-channel `singleGradientDensity` / pigment strength만 바꿔 약한 outer density, 넓은 mid transition, 강한 inner density를 만든다.
- Rejected gloss runtime screenshots are retained under `evidence/screenshots/e7-gloss-lip-rejected-2026-06-26/`. They show the clustered gloss candidate reading as separate small pieces, not lip gloss.
- `gloss_lip` active correction: RN preset now keeps matte-like tint/coverage/feather with stronger but localized specular (`specular=0.78`, `specularPower=36`, `glossBoost=0.68`); Unity diagnostics still report `glossHighlightMode=matte_base_wet_sheen`; Unity gloss brightness matches matte (`0.9`); shader gloss branch uses matte-derived pigment base, narrow gloss-mask specular, softened specular edges, and constrained tint-colored halo. The goal is not to whiten the lip color: inner-mouth/center whitening is failure.
- Latest gloss user-drawn cluster checks: AR expected preview regeneration and soft-SDF verifier passed after replacing the active atlas A-channel. RN Jest/TypeScript/lint, Python compile, `git diff --check`, Unity batchmode, UnityFramework rebuild, RN install, and runtime photo acceptance have not been rerun for this final 1px piece-position tweak.
- Previous Unity batchmode log for the broader matte-base sheen candidate: `evidence/logs/e7-gloss-matte-base-sheen-unity-batchmode-20260626.log`. It is superseded by the latest edge-blended 1px compile evidence above.
- Latest gloss preview metrics: style-atlas A-channel `A>8=57`, bbox `x=239..267/y=335..339`, max alpha `188`; direct atlas guard has `softComponentCountGt48=4`, `coreComponentCountGt96=3`, `upperSoftPixelsGt48=0`, `lowerCorePixelsGt96=21`; soft-SDF verifier keeps `wetLineActivePixels=237`, `wetLineHeightToLipHeight=0.0238`, `wetLineMeanLumaBoost=0.0679`, `wetLineComponentCount=1`, `glossRedBasePreservationRatio=0.9986`; AR expected preview gloss has `componentCount=3`, bbox `left=516 top=1249 right=598 bottom=1272`, `heightToLipHeight=0.1935`, `widthToLipWidth=0.3593`, `meanAdditiveLuma=0.1097`, max `0.1453`, red base ratio `1.0`, still `expected_ar_preview_review` pending real-device visual acceptance.
- Previous clustered Build Gate history remains evidence only: `evidence/logs/e7-gloss-cluster-runtime-buildgate-20260626.md` records the superseded UnityFramework build/sync and the RN signing/provisioning blocker. Do not treat that build as active gloss acceptance.
- Debug preview outputs: `debug_show_lip_base_only.png`, `debug_show_gloss_mask_only.png`, `debug_show_gloss_halo_only.png`, and `debug_show_final_gloss.png` under `evidence/e7-reference-atlas/lip-style-atlas-v1/soft_sdf_multilayer_preview_20260626/`; the verifier now requires all four.
- Previous runtime Build Gate packet: `evidence/logs/e7-gloss-cluster-runtime-buildgate-20260626.md` records the required approval question, primary path, compare-only paths, validation contract, evidence matrix, commands, and out-of-scope items for the rejected clustered candidate.
- Previous runtime Build Gate result: buildless checks re-ran and passed, Unity batchmode import/compile passed in `evidence/logs/e7-gloss-cluster-buildgate-unity-batchmode-20260626.log` with `CompileScripts: 990.195ms`, and `scripts/build_m3_unityframework.sh` succeeded with `TIMESTAMP=e7-gloss-cluster-20260626` in `real 136.04s`. Evidence logs: `evidence/logs/m3-repro-unity-export-e7-gloss-cluster-20260626.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-gloss-cluster-20260626.log`, and `evidence/logs/m3-repro-artifact-verification-e7-gloss-cluster-20260626.log`.
- Previous RN signed install result: `evidence/logs/e7-gloss-cluster-rn-ios-device-20260626.log` records `202268054(???)` / `00008110-0001794E0CD9801E` unavailable/not found by RN CLI, then Xcode failure at the known provisioning gate: no iOS App Development profile for `com.yeoseojin.makeupar.validation202268054`, automatic signing disabled, error code `65`. No install, launch, runtime diagnostics, or gloss acceptance screenshot was collected.
- AR-runtime expected preview: `scripts/e7_reference_atlas/make_lip_runtime_ar_expected_preview.py` mirrors RN default lip recipe, Unity material scaling, ARFace UV/triangle culling, the shader pigment multiply pass, and the gloss additive pass. Generated sheet: `evidence/e7-reference-atlas/lip-style-atlas-v1/ar_runtime_expected_20260626/ar_runtime_expected_sheet.png`.
- AR expected verdict: `expected_ar_preview_review`, not Green, because conservative footprint/gradient guards still require runtime review. Mesh culling is tight enough (`279/2304` triangles accepted, cull ratio `0.8789`). The latest `gradient_lip` same-color density guard remains the frozen acceptance context, and active `gloss_lip` preserves the red base (`redBasePreservationRatio=1.0`) with a localized user-drawn lower-lip specular cluster (`componentCount=3`, `heightToLipHeight=0.1935`, `meanAdditiveLuma=0.1097`, max `0.1453`). Treat this as buildless review evidence only.
- Gradient density-field correction: `gradient_lip` now uses a dedicated `lip-drawn-gradient-density-atlas-v1` resource instead of sharing the default matte/gloss atlas. The new atlas copies R/G/A from `lip-drawn-style-atlas-v1` but replaces B with a distance-transform continuous density seed. RN sends this mask id only for `gradient_lip`; default matte/gloss continue using `lip-drawn-style-atlas-v1`.
- Shader correction: the gradient branch no longer adds `outerSoftWash + midGradientLayer + innerGradientTint`. It uses one `singleGradientDensity` curve from the B channel, derives one pigment-strength curve from it, and keeps `outerMlbbColor` / `innerRedColor` equal to the same selected `_RegionColor`; the gradient effect is density/strength, not a second hue.
- Follow-up gradient internal-boundary correction: user clarified the visible issue was between the inner red density and outer tint, not the outer lip edge. The B-channel seed is now wider (`seedPixels=327`, `densityMeanActive=0.2433`), and the shader now uses `GradientDensityBlur` plus gradient-only feather to soften the density field before pigment strength is applied.
- Latest gradient AR expected metrics after same-color correction on RED 100%: `pigmentColorRangeMax=0.0`, `pigmentStrengthP95=0.5156`, `gradientTransitionWidthToLipWidth=0.7965`, `gradientInnerOuterStrengthRatio=2.2810`, `edgeInnerPigmentRatio=0.0303`, `gradientRampMaxAdjacentDeltaP95=0.0351`, and `gradientCenterBoundaryJump=0.0279`. The soft-SDF verifier also passes. Gradient-specific guards pass; overall preview remains `review` only because gloss footprint is intentionally deferred.
- Bright lighting user reference is saved at `evidence/e7-reference-atlas/lip-style-atlas-v1/lighting_references/bright_lighting_reference_20260626.png`, but it is not AR expected-render evidence because that photo has no same-frame ARFace `screenVertices` / `uvs` / `indices`. A photo-only automatic lip-mask render was visually invalidated as misaligned and removed from the preview script/outputs.
- 앞으로 예상 렌더를 공유할 때는 두 출력을 같이 보여준다: 1) ARFace capture-pair 기반 expected render는 AR 정렬/마스크 검증용, 2) bright lighting photo-aligned preview는 밝은 조명에서 색감/농도/그라데이션 확인용이다. `make_lip_runtime_ar_expected_preview.py` 기본 실행은 둘을 함께 생성하고 `gradient_two_reference_preview.png` 비교 시트를 만든다. 단, bright preview는 `notArfaceEvidence=true`로 유지한다.
- Bright lighting photo-aligned preview는 사용자 스크린샷 피드백 후 더 보수적인 안쪽 mask로 바꿨다. 실제 표시 alpha는 polygon 그대로가 아니라 density가 낮은 upper/outer edge에서 줄어들도록 한다. 경계가 의심되면 이 preview를 색 검증 근거로 쓰지 말고, 같은 프레임 ARFace capture 또는 명시적 lip mask를 받아야 한다. 이 조정은 밝은 사진 preview 전용이며 ARFace capture-pair 렌더나 Unity/RN runtime mask에는 영향이 없다.
- New evidence: `evidence/e7-reference-atlas/lip-style-atlas-v1/gradient_density_atlas_20260626/summary.json`, `lip_gradient_density_channels.png`, and regenerated `ar_runtime_expected_20260626/ar_runtime_expected_sheet.png`.
- Buildless checks after the gradient internal-boundary correction: bundled Python compile, gradient atlas generation, AR runtime expected preview, soft-SDF preview regeneration, atlas guard, soft-SDF verifier, RN Jest (`13` tests), TypeScript, RN lint, and `git diff --check` pass. Unity batchmode import/compile was not rerun for this last follow-up; the prior density-field attempt in `evidence/logs/e7-gradient-density-atlas-unity-batchmode-20260626.log` stopped at Unity Licensing IPC timeout before compile. No UnityFramework/RN real-device build/install was run.
- UnityFramework build/sync after Build Gate approval: `speed-up-unity-builds` audit confirmed stable Unity `Library/` and Xcode DerivedData reuse. A stale Unity Licensing Client was stopped, then `TIMESTAMP=e7-gradient-internal-boundary-20260626 BUILD_LOG_MODE=full ... bash scripts/build_m3_unityframework.sh` succeeded in `real 165.15s`. Evidence logs: `evidence/logs/m3-repro-unity-export-e7-gradient-internal-boundary-20260626.log`, `evidence/logs/m3-repro-xcodebuild-unityframework-e7-gradient-internal-boundary-20260626.log`, and `evidence/logs/m3-repro-artifact-verification-e7-gradient-internal-boundary-20260626.log`. Unity export records `CompileScripts: 4391.813ms` and `Exiting batchmode successfully now!`; Xcode records `** BUILD SUCCEEDED **`; RN/package-local `UnityFramework.framework` are arm64 Mach-O frameworks (`114M`, Unity `Data` `19M`).
- 이 빌드는 gradient internal-boundary fix의 compile/link/package correctness 승인이다. RN real-device install, iPhone photo/log review, E7.3 runtime visual acceptance는 아직 실행/수집하지 않았다.
- Final gradient acceptance: user-provided iPhone HUD screenshot `IMG_5268.PNG` is retained at `evidence/screenshots/e7-gradient-lip-accepted-2026-06-26/IMG_5268.PNG` (`1170x2532`). It shows `active=lip`, `focus=lip`, RED `#C21F3A`, intensity `100%`, `finish gradient_lip`, Tracking, mesh `v=1220/i=6912/uv=1220`, FPS `59.9`, frame `16.7ms`, and latency `21.0ms`. User decision: "이거야 그라데이션 픽스하자. 이제 수정 안할거야". Treat `gradient_lip` as frozen for validation only; this does not accept `gloss_lip`, cheek, eye, full E7.3 Green, or product-quality makeup.

이번 판단에 사용된 사용자 실기기 스크린샷:

- 매트 완료/freeze 기준: `/Users/yeoduchi/Downloads/IMG_5262.PNG`
- 글로시 실패 기준: `/Users/yeoduchi/Downloads/IMG_5263.PNG`
- 그라데이션 실패 기준: `/Users/yeoduchi/Downloads/IMG_5264.PNG`
- 그라데이션 완료/freeze 기준: `evidence/screenshots/e7-gradient-lip-accepted-2026-06-26/IMG_5268.PNG`
- 그라데이션 목표 레퍼런스: `/var/folders/bl/w00rm3lj0wsfm0l8t26rkd980000gn/T/TemporaryItems/NSIRD_screencaptureui_j4ni1T/스크린샷 2026-06-26 오후 2.50.30.png`
- 밝은 조명 참고 사진: `evidence/e7-reference-atlas/lip-style-atlas-v1/lighting_references/bright_lighting_reference_20260626.png` (조명/색감 참고 전용, ARFace 정렬 evidence 아님)

## 2. 구현 기준점

현재 활성 렌더링 경로:

```txt
RN preset
-> E3RegionMaskOverlay material setup
-> SmoothRegionMask.shader
-> ARFace-attached lip-drawn-style-atlas-v1
```

관련 파일:

- `rn/MakeupARValidation/App.tsx`: `matte_lip`, `gloss_lip`, `gradient_lip` preset 값.
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`: material scaling, texture selection, mesh culling, runtime diagnostics.
- `unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader`: pigment multiply pass와 additive gloss pass.
- `scripts/e7_reference_atlas/make_lip_soft_sdf_multilayer_preview.py`: offline preview approximation.
- `scripts/e7_reference_atlas/verify_lip_soft_sdf_multilayer.py`: multilayer contract guard.

현재 확정된 사실:

- 기본 lip mask는 `lip-drawn-style-atlas-v1`이다.
- Apple Vision은 debug/compare 전용이며 활성 lip renderer가 아니다.
- 매트는 multiply pigment + soft mask + no gloss pass 구조라 validation baseline으로 적합하다.
- 최신 gradient UnityFramework build/sync는 `e7-gradient-matte-derived-20260626-1805`다. signed install은 해당 시점에 device unavailable로 막혔지만, 사용자가 최신 gradient build 결과 스크린샷을 제공해 `gradient_lip` visual acceptance를 완료했다. `gloss_lip`는 아직 별도 runtime acceptance가 필요하다.

## 3. 멀티에이전트 분석 요약

시각 분석:

- 매트는 입술 위치에 붙어 있고, 색이 충분히 보이며, 과하게 번들거리지 않는다. E7.3 validation 기준으로 freeze한다.
- 그라데이션은 목표 레퍼런스보다 full matte red + darker center에 가깝다. 목표는 안쪽에서 물든 색이 바깥으로 부드럽게 사라지는 한국식 inner stain이다.
- 글로시는 red lip 위에 controlled wet highlight가 얹힌 느낌이 아니라, 전체 pigment가 옅어진 느낌이 강하다.

코드 구조 분석:

- 매트가 안정적인 이유는 RN preset이 multiply, `roughness=1`, `specular=0`, `glossBoost=0`이고 shader gloss pass가 matte에서는 early return하기 때문이다.
- 그라데이션이 선명하게 갈라지는 이유는 shader가 사실상 thresholded zone들을 합성하기 때문이다. 현재 핵심 식은 `innerDensity = max(gradientMask, centerDensity) * fullCore`이고, `gradientMask`는 atlas `B`, `fullCore`는 raw atlas `R`에서 온다. 결과적으로 continuous ramp가 아니라 center zone + outer zone처럼 보인다.
- 글로시가 색 빠짐처럼 보이는 이유는 gloss base branch가 pigment strength를 낮추고, additive pass는 static tinted line에 가깝기 때문이다. 현재 highlight shape는 normal, view direction, light estimate, camera feed luminance, `_SpecularPower` 기반으로 형성되지 않는다.

## 4. 원인 분석

### Matte

완료로 보는 이유:

- 가장 단순한 경로다: multiply pigment + soft mask.
- 최신 실기기 screenshot에서 입술 질감이 어느 정도 살아 있고 매트 립스틱처럼 읽힌다.
- 그라데이션/글로시와 비교할 안정적인 기준점이 된다.

건드리지 말 것:

- RN `matte_lip` preset.
- Unity `matte_lip` material alpha/brightness scaling.
- shader의 matte branch.
- matte `gloss=none`을 보장하는 테스트.

### Gradient

관찰된 문제:

- `IMG_5264`에서 중앙의 진한 빨강과 바깥 lip wash가 별도 레이어처럼 보인다.
- inner tint 경계가 너무 명확하다.
- 바깥 perimeter가 목표 레퍼런스보다 아직 진하고 matte-like하다.

가능성 높은 원인:

- `gradientAmount=1`이 density field가 충분히 부드럽기 전에 inner/outer contrast를 최대로 밀고 있다.
- `innerDensity`가 `max(gradientMask, centerDensity)`와 `fullCore`에 의해 만들어져서 pigment diffusion field가 아니라 mask selection처럼 동작한다.
- 현재 gradient style은 `outerSoftWash + softEdgeFeather + innerGradientTint`를 더하지만, 각 항이 비교적 선명한 mask/core band에서 나온다.
- lip mesh culling이 너무 타이트하면 shader feather가 퍼질 geometry 자체가 부족할 수 있다.

목표 동작:

- 바깥 perimeter에서는 거의 사라지는 약한 full-lip base.
- 입 안쪽/중앙 근처의 강한 inner tint.
- inner tint와 outer wash 사이의 넓은 transition band.
- 중앙과 바깥 사이에 보이는 경계선이 없어야 한다.

가장 유력한 해결 방향:

- `gradient_lip`에 전용 continuous gradient density를 만든다. 현재의 hard `gradientMask/fullCore` 조합을 그대로 쓰지 않는다.
- multi-band ramp로 계산한다.
  - `outerWash`: 넓은 soft mask 기반의 낮은 pigment.
  - `midRamp`: lip center에서 perimeter로 넓게 퍼지는 중간 pigment.
  - `innerStain`: 현재보다 feather가 넓은 강한 inner pigment.
- shader ramp가 부드러워진 뒤 필요하면 RN `gradientAmount`를 `1`에서 낮춘다.
- 바깥 edge가 계속 잘리면 `E3RegionMaskOverlay.cs`의 lip mesh culling margin을 넓힌다.

## 5. Gloss 분석

관찰된 문제:

- `IMG_5263`에서 gloss는 빨간 립 위에 광택이 얹힌 것이 아니라, 빨간 pigment가 옅어진 것처럼 보인다.
- localized wet ridge나 specular highlight가 거의 보이지 않는다.
- 현재 highlight는 실제 카메라 노출에서 너무 약하거나 static해서 shine으로 읽히지 않는다.

가능성 높은 원인:

- gloss base branch가 shine을 더하기 전에 pigment를 먼저 약하게 만들어서, 첫 인상이 desaturation/lightening으로 보인다.
- additive highlight는 atlas `A` channel 기반 static line이고 multiplier가 낮아 실기기에서는 존재감이 부족할 수 있다.
- additive pass가 face normal, view direction, light direction, camera luminance를 고려하지 않는다.
- 별도 gloss mask를 그리는 것은 "어디를 반짝이게 할지"를 정하는 데 도움이 되지만, 그 자체만으로 물리적으로 설득력 있는 shine이 되지는 않는다.

목표 동작:

- red pigment는 matte와 비슷하게 유지한다.
- 그 위에 작은 localized wet highlight만 얹는다.
- highlight는 좁고, soft edge가 있고, 약간 립 컬러에 물들어 있어야 한다.
- 전체 입술을 넓게 하얗게 만들지 않는다.

가장 유력한 해결 방향:

- 먼저 gloss에서 pigment strength와 shine strength를 분리한다. gloss base는 현재보다 더 빨간 pigment를 보존해야 한다.
- 그 다음 highlight mask를 개선한다.
  - atlas `A` channel에 lower-lip center ridge와 아주 작은 upper-lip glint를 그리거나 생성한다.
  - highlight active area는 full lip 대비 아주 작게 유지한다.
  - 밝은 core와 부드러운 halo를 분리한다.
- 더 설득력 있는 validation 결과가 필요하면 additive gloss pass에 mesh normal과 view direction을 전달해 view/normal-responsive highlight를 만든다. 이 방법은 더 효과적일 가능성이 높지만 risk도 더 높다.

판단:

- 현재 shader 구조에서도 validation-level gloss는 가능하다. 조건은 stronger base pigment + better localized highlight mask다.
- 제품처럼 자연스러운 물광은 static additive line만으로 보장하기 어렵다. 그 수준은 normal/view/light-aware shading 또는 더 진화된 renderer가 필요할 수 있다.

## 6. 다음 작업 우선순위

1. Matte/Gradient freeze guard 유지.
   - `matte_lip`는 수정하지 않는다.
   - `gradient_lip`도 수정하지 않는다. accepted 기준은 `evidence/screenshots/e7-gradient-lip-accepted-2026-06-26/IMG_5268.PNG`이다.
   - matte `gloss=none`, `finish=matte_lip`, gradient same-pigment density path, multiply path, ARFace atlas mask 관련 테스트를 유지한다.

2. 남은 작업은 `gloss_lip`만 다룬다.
   - primary path: active lower-lip 1px specular-mask `gloss_lip`.
   - compare-only path: frozen `matte_lip` and frozen `gradient_lip`.
   - out-of-scope: matte changes, gradient changes, Apple Vision active renderer, product-quality claim.

3. Build Gate 승인 후에만 UnityFramework/RN 경로를 실행한다.
   - `bash scripts/build_m3_unityframework.sh`로 framework sync.
   - 이후 RN install/signing path는 기존 provisioning blocker를 전제로 기록한다.
   - 런타임 acceptance는 사용자 iPhone screenshot/log로 판단한다.

4. 런타임에서 실패하면 다음 순서로만 연다.
   - Gloss 실패: atlas A-channel을 약간 더 localized하게 다시 그린다.
   - static wet-line이 계속 flat하면 그때 normal/view-direction additive pass를 별도 risk로 연다.

## 7. Evidence Bar

빌드 전 no-build check:

- RN Jest.
- TypeScript.
- RN lint.
- scoped `git diff --check`.
- `verify_lip_style_atlas.py`.
- `verify_lip_soft_sdf_multilayer.py`.
- shader/preset/mask 변경 시 offline preview regeneration.
- Unity shader/script 변경 시 Unity batchmode import/compile.

런타임 acceptance evidence:

- Matte: freeze baseline이 유지된 HUD screenshot 1장.
- Gradient: accepted/frozen HUD screenshot은 `evidence/screenshots/e7-gradient-lip-accepted-2026-06-26/IMG_5268.PNG`.
- Gloss: red pigment가 유지되고 작은 localized highlight가 보이는 HUD screenshot 1장.
- Compact HUD는 `active=lip`, `focus=lip`, `maskTex=lip-drawn-style-atlas-v1`, 기대 finish를 보여야 한다.
- E7.3 Green 또는 product readiness claim은 금지한다.

시각적 성공 기준:

- Matte: `IMG_5262` 수준 유지 또는 개선.
- Gradient: `IMG_5268` 기준으로 완료/freeze. 사용자가 명시적으로 다시 열기 전까지 더 조정하지 않는다.
- Gloss: pigment가 씻겨 나가지 않고, 입술 안쪽 중앙이 허옇게 비지 않아야 하며, lower-lip surface에 짧고 얇은 localized specular streak가 주변 tint로 뭉개진 약한 halo와 함께 보여야 한다.

최근 no-build 보정:

- `gradient_lip`는 추가 레이어를 쌓지 않고, shader에서 B-channel density를 `GradientDensityBlur`로 넓게 샘플링한 뒤 raw density와 섞는다.
- gradient-only feather는 `0.38`까지 허용한다. `matte_lip` freeze path는 건드리지 않는다.
- `outerMlbbColor`와 `innerRedColor`는 둘 다 같은 `_RegionColor`에서 나온다. 즉 다른 보조색 레이어가 아니라 같은 선택 색상의 density/strength gradient다.
- RED 100% buildless expected preview 기준 pigment p95는 `0.3961 -> 0.5156`으로 올라갔고, center-line max jump는 `0.0495 -> 0.0279`로 내려갔다. 같은 색상 증거는 `pigmentColorRangeMax=0.0`.
- 최신 preview: `evidence/e7-reference-atlas/lip-style-atlas-v1/ar_runtime_expected_20260626/ar_runtime_expected_sheet.png`.

## 8. 다음 세션 프롬프트

다음 세션에서는 아래처럼 말하면 된다.

```txt
AGENTS.md와 TECH_VALIDATION_RESULT.md의 Current Session Snapshot을 먼저 읽어줘.
그 다음 docs/roadmaps/active/E7_LIP_FINISH_NEXT_HANDOFF_KO.md를 읽고 이어서 작업해줘.

E7.3 validation-only 립 피니시 작업을 계속한다.
matte_lip은 완료/freeze 상태라 절대 건드리지 마.
gradient_lip도 IMG_5268 기준으로 완료/freeze 상태라 절대 건드리지 마.

작업:
1. gloss_lip을 분석/수정해줘.
   - red pigment를 보존하고,
   - localized wet highlight를 추가하고,
   - 전체가 하얗게 뜨는 broad whitening은 피한다.
   atlas A-channel gloss mask를 다시 그리는 것만으로 충분한지,
   아니면 additive pass에 normal/view-direction이 필요한지 판단해줘.

Apple Vision은 debug/compare 전용으로 유지해.
E7.3 validation 범위 안에서만 작업하고 product-quality claim은 하지 마.
현재 matte/gradient freeze evidence는 수집됐다.
다음에는 Build Gate 보고를 먼저 하고, 승인 전에는 Unity/RN real-device build를 실행하지 마.
```
