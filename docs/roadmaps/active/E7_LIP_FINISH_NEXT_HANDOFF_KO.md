# E7 립 피니시 다음 작업 핸드오프

Date: 2026-06-26 KST

Status: E7.3 validation-only 립 피니시 핸드오프 / 매트 freeze / 그라데이션과 글로시는 미승인 / 다음 작업은 `gradient_lip`, `gloss_lip`만 대상으로 한다

## 1. 현재 결정

이 문서는 다음 세션 또는 멀티에이전트 작업자가 바로 이어받기 위한 핸드오프다.

- `matte_lip`: 완료/freeze. 사용자가 명시적으로 다시 열지 않는 한 더 건드리지 않는다.
- `gradient_lip`: 미완료. 중앙 내부 tint와 바깥 lip wash의 경계가 아직 너무 선명하다.
- `gloss_lip`: 미완료. 광택이 도는 느낌보다 색이 연해지는 느낌이 먼저 보인다.
- E7.3은 계속 Yellow다. 이 작업은 validation-only 렌더러 하드닝이며 제품급 립 메이크업 claim은 금지한다.

이번 판단에 사용된 사용자 실기기 스크린샷:

- 매트 완료/freeze 기준: `/Users/yeoduchi/Downloads/IMG_5262.PNG`
- 글로시 실패 기준: `/Users/yeoduchi/Downloads/IMG_5263.PNG`
- 그라데이션 실패 기준: `/Users/yeoduchi/Downloads/IMG_5264.PNG`
- 그라데이션 목표 레퍼런스: `/var/folders/bl/w00rm3lj0wsfm0l8t26rkd980000gn/T/TemporaryItems/NSIRD_screencaptureui_j4ni1T/스크린샷 2026-06-26 오후 2.50.30.png`

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
- 최신 UnityFramework build/sync는 `e7-matte-gradient-gloss-retune-20260626-1435`다. signed install은 provisioning 때문에 막혀 있지만, 사용자는 수동 경로로 최신 빌드 스크린샷을 제공했다.

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

1. Matte freeze guard 유지.
   - `matte_lip`는 수정하지 않는다.
   - matte `gloss=none`, `finish=matte_lip`, multiply path, ARFace atlas mask 관련 테스트를 유지한다.

2. Gradient를 먼저 고친다.
   - 새 시스템 없이 목표 레퍼런스에 가까워질 가능성이 가장 높다.
   - 우선 `SmoothRegionMask.shader`에서 continuous density/ramp를 구현한다.
   - RN `gradient_lip` preset은 shader ramp 이후 필요할 때만 최소 조정한다.
   - matte branch는 변경하지 않는다.

3. Gradient preview/evidence를 갱신한다.
   - offline preview를 재생성한다.
   - hard center boundary가 없어졌는지 확인할 target-oriented guard 또는 문서 기준을 추가한다.
   - 수치 metric만으로는 부족하므로 runtime screenshot acceptance가 필요하다.

4. Gloss는 base pigment와 highlight를 분리해서 고친다.
   - red base를 보존한다.
   - 그 다음 gloss mask를 다시 튜닝하거나 다시 그린다.
   - static mask만으로 계속 flat하면 normal/view direction을 고려한다.

5. no-build check와 Build Gate 승인 전에는 Unity/RN real-device build를 실행하지 않는다.

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
- Gradient: 중앙에서 바깥으로 부드럽게 퍼지고 center boundary가 보이지 않는 HUD screenshot 1장.
- Gloss: red pigment가 유지되고 작은 localized highlight가 보이는 HUD screenshot 1장.
- Compact HUD는 `active=lip`, `focus=lip`, `maskTex=lip-drawn-style-atlas-v1`, 기대 finish를 보여야 한다.
- E7.3 Green 또는 product readiness claim은 금지한다.

시각적 성공 기준:

- Matte: `IMG_5262` 수준 유지 또는 개선.
- Gradient: `IMG_5264`보다 바깥 edge가 훨씬 부드럽고, inner red가 perimeter보다 강하며, transition band가 blur처럼 보여야 한다.
- Gloss: pigment가 씻겨 나가지 않고, lower-center 또는 wet-line 영역에 localized highlight가 보여야 한다.

## 8. 다음 세션 프롬프트

다음 세션에서는 아래처럼 말하면 된다.

```txt
AGENTS.md와 TECH_VALIDATION_RESULT.md의 Current Session Snapshot을 먼저 읽어줘.
그 다음 docs/roadmaps/active/E7_LIP_FINISH_NEXT_HANDOFF_KO.md를 읽고 이어서 작업해줘.

E7.3 validation-only 립 피니시 작업을 계속한다.
matte_lip은 완료/freeze 상태라 절대 건드리지 마.

작업:
1. gradient_lip을 목표 레퍼런스처럼 자연스럽게 고쳐줘.
   - 약한 outer base,
   - 더 강한 inner/center tint,
   - 넓고 부드러운 transition,
   - center/perimeter 경계가 보이지 않는 형태.
   우선 SmoothRegionMask.shader에서 continuous gradient density/ramp를 구현해.
   RN gradient_lip preset은 필요할 때만 최소 조정해.

2. gradient 이후 gloss_lip을 분석/수정해줘.
   - red pigment를 보존하고,
   - localized wet highlight를 추가하고,
   - 전체가 하얗게 뜨는 broad whitening은 피한다.
   atlas A-channel gloss mask를 다시 그리는 것만으로 충분한지,
   아니면 additive pass에 normal/view-direction이 필요한지 판단해줘.

Apple Vision은 debug/compare 전용으로 유지해.
E7.3 validation 범위 안에서만 작업하고 product-quality claim은 하지 마.
먼저 no-build check를 돌리고, Unity/RN real-device build는 Build Gate 보고와 승인 전에는 실행하지 마.
```

