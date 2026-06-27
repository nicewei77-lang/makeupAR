# E7 립 구현 통합 리포트

Date: 2026-06-27 KST

Status: E7.3 validation-only 립 구현 리포트 / `matte_lip` freeze / `gradient_lip` user accepted + freeze / `gloss_lip` 구현 후보 존재, 최종 런타임 승인 미수집 / E7.3 전체 Yellow 유지

## 1. 결론

이번 립 작업은 E7.3 validation-only 범위에서 `matte_lip`, `gradient_lip`, `gloss_lip`의 렌더링 경로를 구현하고 하드닝한 작업이다.

- `matte_lip`: 완료/freeze. 현재 validation 기준의 안정 baseline으로 유지한다.
- `gradient_lip`: 완료/freeze. 사용자 실기기 HUD screenshot `IMG_5268.PNG`에서 RED `#C21F3A`, intensity `100%`, `finish gradient_lip` 결과를 승인했다.
- `gloss_lip`: 구현 후보는 있다. 다만 최신 후보는 buildless preview/guard 기준이며, UnityFramework rebuild, RN install, 실기기 runtime 사진 승인은 아직 최종 수집되지 않았다.
- E7.3 전체는 계속 Yellow다. 이 리포트는 validation renderer 구현/증거 정리이며, 제품급 립 메이크업 완성이나 E7 전체 Green을 의미하지 않는다.

## 2. 구현 범위

활성 립 렌더링 경로:

```txt
RN preset
-> RNBridge recipe payload
-> E3RegionMaskOverlay material setup / texture selection
-> SmoothRegionMask.shader
-> ARFace-attached lip-drawn-style-atlas-v1
```

주요 파일:

- `rn/MakeupARValidation/App.tsx`: 립 finish preset, UI/HUD 상태, RN -> Unity payload.
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`: RN payload 파싱과 Unity recipe 전달.
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`: mask texture 선택, material scaling, mesh culling, runtime diagnostics.
- `unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader`: pigment multiply, soft mask sampling, gradient density, gloss additive pass.
- `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/lip-drawn-style-atlas-v1.png`: matte/gloss 기본 lip atlas.
- `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/lip-drawn-gradient-density-atlas-v1.png`: gradient 전용 continuous density atlas.
- `scripts/e7_reference_atlas/make_lip_runtime_ar_expected_preview.py`: ARFace 기반 expected render와 bright lighting photo-aligned preview 생성.
- `scripts/e7_reference_atlas/verify_lip_soft_sdf_multilayer.py`: soft-SDF/gradient/gloss guard.

## 3. Finish별 상태

### Matte

상태: 완료/freeze.

결정 근거:

- multiply pigment + soft mask + no gloss pass 구조가 가장 안정적이다.
- 사용자 실기기 확인에서 입술 위치와 질감이 validation baseline으로 적절하다고 판단했다.
- 이후 작업에서 `matte_lip` RN preset, Unity material scale, shader matte branch는 건드리지 않는 것을 원칙으로 둔다.

### Gradient

상태: 완료/freeze.

핵심 문제:

- 초기 방식은 atlas B channel과 shader layer 조합이 사실상 inner/outer 두 레이어처럼 보여 중앙 blob과 경계가 생겼다.
- 색을 진하게 하면 레이어 경계가 강해지고, 경계를 줄이면 전체 색이 약해지는 문제가 반복됐다.

최종 방향:

- `gradient_lip` 전용 `lip-drawn-gradient-density-atlas-v1`를 생성했다.
- B channel을 painted band가 아니라 distance-transform 기반 continuous density field로 바꿨다.
- shader는 inner/outer layer를 더하는 방식 대신 하나의 density/pigment curve를 사용한다.
- `outerMlbbColor`와 `innerRedColor`를 같은 `_RegionColor`에서 가져오게 해, 같은 색상이 농도/밀도만 다르게 보이도록 했다.

사용자 승인:

- 승인 스크린샷: `evidence/screenshots/e7-gradient-lip-accepted-2026-06-26/IMG_5268.PNG`
- 조건: RED `#C21F3A`, intensity `100%`, `finish gradient_lip`, Tracking, FPS `59.9`, frame `16.7ms`, latency `21.0ms`
- 사용자 결정: "이거야 그라데이션 픽스하자. 이제 수정 안할거야"

따라서 `gradient_lip`은 E7.3 validation 기준에서 freeze한다.

### Gloss

상태: 구현 후보 있음 / 최종 runtime acceptance pending.

실패한 후보:

- clustered gloss 후보는 실기기 사진에서 작은 흰 조각처럼 보여 rejected.
- 더 넓은 matte-base wet-sheen 후보와 단일 1px streak 후보도 superseded.

현재 후보:

- matte와 같은 tint base를 유지한다.
- pigment가 씻겨 나가지 않도록 red base preservation을 우선한다.
- 별도 atlas A-channel로 lower-lip specular cluster를 만들고, 위쪽 조각은 제거했다.
- additive highlight는 좁고 localized해야 하며, 입술 중앙이 허옇게 비는 것은 실패로 본다.

현재 증거:

- buildless AR expected preview와 soft-SDF verifier는 통과했다.
- 최신 preview는 `expected_ar_preview_review`이며 Green이 아니다.
- UnityFramework rebuild, RN install, 실기기 사진/log 기반 최종 승인은 아직 없다.

## 4. Expected Render 정책

앞으로 립 예상 렌더를 보여줄 때는 두 출력을 함께 제공한다.

1. ARFace 기반 expected render
   - 같은 프레임의 ARFace `screenVertices`, `uvs`, `indices`를 사용한다.
   - AR 정렬, mesh culling, mask footprint 검증용이다.
   - 대표 출력: `evidence/e7-reference-atlas/lip-style-atlas-v1/ar_runtime_expected_20260626/ar_runtime_expected_sheet.png`

2. Bright lighting photo-aligned preview
   - 밝은 조명 참고 사진 위에 photo-aligned lip preview를 얹는다.
   - 조명/색감/농도 참고용이며 ARFace evidence가 아니다.
   - summary에는 `notArfaceEvidence=true`로 기록한다.
   - 경계가 의심되면 색 검증 근거로 쓰지 않는다. 이 경우 같은 프레임 ARFace capture 또는 명시적 lip mask가 필요하다.

RED 100% 비교 출력:

- `evidence/e7-reference-atlas/lip-style-atlas-v1/ar_runtime_expected_red100_20260626/ar_runtime_expected_sheet.png`
- `evidence/e7-reference-atlas/lip-style-atlas-v1/ar_runtime_expected_red100_20260626/bright_lighting_reference_gradient_lip_photo_aligned_sheet.png`
- `evidence/e7-reference-atlas/lip-style-atlas-v1/ar_runtime_expected_red100_20260626/gradient_two_reference_preview.png`

## 5. 주요 검증 증거

Buildless/static evidence:

- RN Jest, TypeScript, RN lint 반복 통과 기록.
- Python compile 및 preview regeneration 기록.
- soft-SDF verifier 통과 기록.
- AR runtime expected preview 생성 기록.
- gradient same-color density metrics:
  - `pigmentColorRangeMax=0.0`
  - `pigmentStrengthP95=0.5156`
  - `gradientTransitionWidthToLipWidth=0.7965`
  - `gradientInnerOuterStrengthRatio=2.2810`
  - `edgeInnerPigmentRatio=0.0303`
  - `gradientRampMaxAdjacentDeltaP95=0.0351`
  - `gradientCenterBoundaryJump=0.0279`

Build/package evidence:

- gradient 관련 UnityFramework build/sync evidence:
  - `evidence/logs/m3-repro-unity-export-e7-gradient-matte-derived-20260626-1805.log`
  - `evidence/logs/m3-repro-xcodebuild-unityframework-e7-gradient-matte-derived-20260626-1805.log`
  - `evidence/logs/m3-repro-artifact-verification-e7-gradient-matte-derived-20260626-1805.log`
- UnityFramework target `** BUILD SUCCEEDED **`, ARKit/Vision/MetalPerformanceShaders link verification, RN/package framework sync 기록이 있다.
- signed RN install은 provisioning/device availability 문제로 막힌 기록이 있다.

Runtime/user evidence:

- `matte_lip`: 사용자 실기기 사진 기준 freeze.
- `gradient_lip`: `IMG_5268.PNG` 기준 사용자 승인/freeze.
- `gloss_lip`: 최신 후보에 대한 실기기 최종 승인 증거는 아직 없다.

## 6. 제한 사항

- 이 리포트는 E7.3 validation renderer 구현 보고서다.
- 제품급 립 메이크업 품질, 상용 립 segmentation, full E7 Green을 claim하지 않는다.
- `gloss_lip`은 구현 후보가 있지만 최종 runtime acceptance가 없다.
- cheek/eye는 이 리포트의 완료 범위가 아니다.
- bright lighting photo-aligned preview는 색감 참고용이며 AR 정렬 증거가 아니다.
- iPhone signed install은 provisioning/account/device availability 이슈에 의해 여러 번 막혔다.

## 7. 다음 액션

1. `matte_lip`과 `gradient_lip`은 freeze 유지.
2. `gloss_lip`만 별도 Build Gate 후 UnityFramework rebuild/RN install/runtime 사진/log acceptance를 수집한다.
3. runtime evidence를 얻으면 `TECH_VALIDATION_RESULT.md`와 이 리포트에 gloss 승인 여부를 반영한다.
4. E7.3 전체 Green은 lip만으로 선언하지 않는다. cheek/eye와 required motion/lighting evidence가 별도로 필요하다.

## 8. 판정

립 구현은 validation-only 기준으로 상당 부분 완료되었다.

- `matte_lip`: Done / frozen
- `gradient_lip`: Done / user accepted / frozen
- `gloss_lip`: Implemented candidate / buildless validated / runtime acceptance pending
- E7.3 overall: Yellow 유지

