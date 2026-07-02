# E7 Full-Face 병합용 브랜치 문제 진단 보고서

- 작성일: 2026-07-01 KST
- 대상 브랜치: `병합용브랜치`
- 목적: 이번 세션에서는 수정하지 않고, 현재 브랜치가 왜 병합/제품 품질 기준에서 막히는지 문제를 빠짐없이 진단한다.
- 진단 기준: `AGENTS.md`, `TECH_VALIDATION_RESULT.md`의 Current Session Snapshot, `docs/roadmaps/README.md`, `docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md`, `docs/runbooks/E7_FULL_FACE_BRANCH_MERGE_GATE_KO.md`, 현재 워킹트리, 관련 원격 브랜치 자산/검증 스크립트 비교.

## 1. 결론

현재 `병합용브랜치`는 "4개 영역이 RN UI에서 조정되고 Unity로 전달된다"는 형태의 계약은 상당 부분 이식되어 있지만, 실제 제품 품질 기준에서는 아직 통과 상태가 아니다.

핵심 문제는 단일 버그가 아니라 다음 6가지가 겹친 것이다.

1. 팀원이 만든 자산 또는 소스 브랜치 자산이 현재 런타임 기본 경로에 충분히 들어와 있지 않으며, 일부는 현재 parser/whitelist로는 바로 다시 넣을 수도 없다.
2. RN UI와 JSON 계약에는 조정값이 있지만, Unity 셰이더가 그 조정값을 실제 렌더링에 반영하지 못하는 항목이 많다.
3. 사전 게이트가 문자열/로그 기반으로 통과할 수 있어, 실제 셰이더/자산/시각 결과 불일치를 잡지 못한다.
4. RN 테스트/문서/사전 게이트 일부가 현재 UI와 동기화되어 있지 않아, "통과" 기록이 최신 워킹트리를 직접 증명하지 못한다.
5. 저장/재적용 경로가 아직 generated lip package 중심으로 보이며, 네 region의 full-face 저장 계약이 구조적으로 확보되었다고 보기 어렵다.
6. iPhone 실기기 시각 증거가 없기 때문에, 현재 상태는 최대 `pre-xcode-ready` 또는 `partial`이지 `Green`이나 제품 품질 완료가 아니다.

따라서 사용자가 말한 "조정도 잘 안되고 팀원들 에셋도 안쓰고"라는 문제 제기는 현재 코드/자산/문서 상태와 일치한다.

## 2. 진단 범위

이번 보고서는 문제 진단만 수행했다. 다음은 하지 않았다.

- Unity/RN 코드 수정
- 에셋 교체
- 셰이더 수정
- iPhone 빌드 또는 실기기 확인
- 문서 상태값을 완료로 갱신
- 브랜치 병합 또는 커밋

확인한 주요 파일/영역은 다음과 같다.

- `AGENTS.md`
- `TECH_VALIDATION_RESULT.md`
- `docs/roadmaps/README.md`
- `docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md`
- `docs/runbooks/E7_FULL_FACE_BRANCH_MERGE_GATE_KO.md`
- `rn/MakeupARValidation/App.tsx`
- `rn/MakeupARValidation/__tests__/App.test.tsx`
- `rn/MakeupARValidation/ios/MakeupARValidation/E7NativeLipBoundaryProviders.swift`
- `scripts/e7_prebuild_gate/check_e7_prebuild_gate.mjs`
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
- `unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader`
- `unity/MakeupARUnityValidation/Assets/Textures/RegionMasks/**`
- `evidence/e7-region-generate/session-20260626T195853Z/pre_xcode_gate.md`
- `evidence/e7-region-generate/session-20260626T195853Z/pre_xcode_gate.json`
- `origin/blush-mask`의 cheek/blush 관련 자산과 검증 스크립트
- `origin/feature/brow-0626`의 brow/cheek 자산과 렌더링 관련 파일

## 3. 전체 문제 목록

### P0. 현재 상태가 제품 품질 완료로 볼 수 없는 문제

#### 3.1. 실기기 시각 검증이 아직 없다

현재 문서 자체도 iPhone 빌드/시각 검증이 보류되었다고 적고 있다. 런타임 매니페스트의 `runtimeReady`도 `false`이다.

문제:

- 네 영역 `lip`, `blush`, `brow`, `eyeliner`가 실제 iPhone 화면에서 모두 보이는지 검증되지 않았다.
- 각 영역 조정값이 실제 화면에서 변화하는지 검증되지 않았다.
- 얼굴 부착, 표정/움직임 안정성, 경계 정확도, 메이크업 가시성, FPS, 지연, 메모리/발열 증거가 없다.
- 빌드/설치/실행 가능성만으로는 제품 품질 완료를 주장할 수 없다.

영향:

- 현재 브랜치는 최대 `pre-xcode-ready` 또는 `partial`이다.
- 병합 후에도 사용자가 보는 화면에서는 "켜진 것처럼 보이지만 실제 메이크업 품질이 안 맞는" 상태가 될 수 있다.

#### 3.2. 사전 게이트 통과와 실제 제품 품질 사이에 큰 간격이 있다

현재 E7 사전 게이트는 RN/Unity 계약 문자열, 로그 토큰, 매니페스트 존재 여부 중심이다. 실제 렌더링 결과를 보지 않는다.

문제:

- Unity 셰이더가 특정 조정값을 실제로 사용하는지 확인하지 않는다.
- 에셋의 채널 구조가 셰이더 샘플링 방식과 맞는지 확인하지 않는다.
- 팀원이 만든 blush 자산이 실제 기본 경로에 들어왔는지 강하게 검증하지 않는다.
- smoke 로그가 `ApplyRecipeJson` 파싱/분기 성공을 보여도, 화면 변화까지 증명하지 않는다.

영향:

- 게이트가 통과해도 실제 화면에서 조정이 안 되거나 잘못 보일 수 있다.
- "통과"라는 말이 팀/사용자에게 완료처럼 전달될 위험이 크다.

#### 3.2A. RN gate와 실제 Jest 상태가 어긋날 수 있다

문서에는 RN Jest 통과 기록이 남아 있지만, 현재 `App.test.tsx`는 최신 full-face UI와 맞지 않는 예전 기대값을 포함하고 있다.

문제:

- 테스트는 아직 `e7-wizard-generate-candidates`, `generated-mask-toggle`, `AR 립 적용됨` 같은 예전 lip validation 중심 흐름을 찾는다.
- 현재 앱 UI는 `AR 메이크업 적용됨`, region panel, full-face inline control 중심으로 바뀌었다.
- 사전 게이트는 실제 테스트 실행보다 문자열 패턴 존재 여부를 더 강하게 본다.

영향:

- RN gate 통과 또는 문서상 Jest 통과 기록을 현재 워킹트리 품질 근거로 그대로 믿기 어렵다.
- UI 회귀나 테스트 노후화가 있어도 문서와 gate가 한동안 완료처럼 보일 수 있다.

#### 3.2B. 과거 pre-Xcode brow 증거가 현재 brow 런타임 경로를 검증하지 못한다

과거 `pre-xcode-ready` evidence는 brow runtime texture를 `e7-brow-balanced-uv-v0`로 기록한다. 하지만 현재 runtime registry와 RN 기본값, whitelist는 `psd-arcore-brow-semi-arch-v1`를 사용한다.

문제:

- 과거 증거가 현재 PSD brow 경로를 직접 검증한 것이 아니다.
- 현재 브랜치에 파일로 남아 있는 `e7-brow-balanced-uv-v0`는 최신 runtime 기본 경로에서 사실상 orphan 상태일 수 있다.

영향:

- brow의 `pre-xcode-ready` 기록을 현재 구현의 검증 근거로 재사용하면 잘못된 확신을 만들 수 있다.
- brow는 문서상 진척보다 실제 검증 최신성이 더 낮다.

### P0. 조정값이 실제 렌더링에 반영되지 않는 문제

#### 3.3. RN과 Unity C#은 brow 조정값을 전달하지만, 현재 셰이더가 대부분 받지 않는다

`rn/MakeupARValidation/App.tsx`와 `RNBridge.cs`, `E3RegionMaskOverlay.cs`에는 brow 조정값이 존재한다.

확인된 조정값 예:

- `detailAmount`
- `maskSpreadX`
- `maskOffsetY`
- `browGap`
- `browAngle`
- `browArch`
- `browArchPosition`
- `browReshapeStrength`
- `browCleanupStrength`
- `browPhotoDetailMode`
- `browPowderFill`

하지만 현재 `SmoothRegionMask.shader`는 이 중 대부분을 선언하거나 사용하지 않는다.

셰이더에 없는 주요 속성:

- `_MaskSpreadX`
- `_MaskOffset`
- `_BrowAngle`
- `_BrowArch`
- `_BrowArchPosition`
- `_DetailAmount`
- `_BrowPhotoDetailMode`
- `_BrowPowderFill`
- `_BrowCleanupStrength`
- `_BrowReshapeStrength`
- `_BrowCleanupSourceTex`

문제:

- RN UI에서 값을 움직여도 Unity C#까지만 전달되고, 최종 렌더링에서는 무시될 수 있다.
- 사용자는 "조정했는데 별 변화가 없다"고 느낄 수 있다.
- 사전 게이트는 `E3RegionMaskOverlay.cs`의 문자열 존재만 보고 통과할 수 있어 이 문제를 놓친다.

영향:

- brow 조정 기능은 계약상 존재하지만 제품 기능으로 완료되었다고 볼 수 없다.
- "조정도 잘 안된다"는 현상이 구조적으로 발생한다.

#### 3.4. non-lip 영역은 실제 패키지 재생성보다 정적 마스크 + 일부 파라미터 전달에 가깝다

현재 `App.tsx`의 recipe 생성 흐름에서 lip 외 영역은 기본적으로 고정된 `maskTextureId`를 사용한다.

문제:

- `blush`, `brow`, `eyeliner`는 사용자의 세밀한 조정에 따라 새로운 런타임 마스크가 만들어지는 구조가 아니다.
- 일부 값은 JSON에는 들어가지만, 셰이더가 사용하지 않으면 화면 결과는 변하지 않는다.
- lip은 별도 조정/패키지 경로가 상대적으로 더 강하지만, non-lip은 아직 정적 자산 의존도가 크다.

영향:

- RN 조정 UI가 실제 제품 조정 기능처럼 보이지만, 런타임 품질은 정적 프리셋 수준에 머물 수 있다.

#### 3.5. brow cleanup 경로가 사실상 꺼져 있다

현재 RN 기본값에서 brow cleanup은 꺼져 있다.

확인된 상태:

- `browCleanupEnabled`가 `false`
- cleanup strength가 `0`
- cleanup frame source가 `none`

문제:

- 눈썹 주변 정리/보정이 필요한 제품 품질 경로가 실제로 작동하지 않는다.
- 관련 필드가 문서/계약에 있어도 런타임 기본 경로에서는 꺼져 있다.

영향:

- brow는 특히 원본 눈썹, 피부색, 조명에 영향을 많이 받는데 cleanup 없이 제품 품질을 기대하기 어렵다.

### P0. 팀원 에셋/소스 브랜치 자산이 현재 경로에서 충분히 사용되지 않는 문제

#### 3.6. `origin/blush-mask`의 cheek session mask들이 현재 브랜치 기본 자산으로 들어와 있지 않다

`origin/blush-mask`에는 다음 계열의 자산이 있다.

- `cheek-session-mask-1-v1`
- `cheek-session-mask-2-v1`
- `cheek-session-mask-3-v1`
- `cheek-session-mask-4-v1`
- `cheek-session-mask-5-v1`

현재 `병합용브랜치`의 기본 런타임 자산은 이 계열이 아니라 다음 쪽이다.

- `e7-blush-balanced-uv-v0`
- `blush-balanced-soft-oval-v0`
- `cheek-smooth-mask-v1`

문제:

- 팀원이 만든 cheek/blush session mask가 현재 기본 제품 경로에 직접 쓰이지 않는다.
- `origin/blush-mask`의 검증 스크립트가 요구하는 "5개 session mask 복사/보존" 계약이 현재 브랜치에는 반영되어 있지 않다.
- 현재 브랜치의 gate도 이 5개 자산 존재를 강제하지 않는다.

영향:

- 사용자가 보기에는 "팀원들이 준 blush 에셋을 안 쓰고 자체 생성 에셋으로 대체한" 상태다.
- 팀 작업물 기준으로 병합 품질을 판단하면 현재 브랜치는 불충분하다.

#### 3.7. `origin/blush-mask`의 자산 형식과 현재 셰이더 해석 방식이 다르다

`origin/blush-mask`의 검증 계약은 source RGB luminance 기반의 밀도/커버리지 해석을 전제로 한다. 반면 현재 `SmoothRegionMask.shader`는 기본적으로 마스크 텍스처의 red 채널을 샘플링한다.

문제:

- source RGB luminance를 이용해 cheek session mask의 회색 밀도와 흰 배경을 해석하는 경로가 현재 셰이더에 없다.
- 현재 셰이더는 `tex2D(_MaskTex, maskUv).r` 방식으로 단순 red 채널을 본다.
- 현재 RNBridge/E3 whitelist는 blush mask id를 `e7-blush-*` 계열로 제한하고, renderer mode도 `smooth-region-mask`만 허용한다.
- 따라서 `origin/blush-mask` 자산을 단순 복사해도 의도한 blush 밀도/경계가 나오지 않을 가능성이 높다.

영향:

- 자산 미사용 문제뿐 아니라, 가져와도 현재 렌더러와 해석 계약이 맞지 않는 문제가 있다.
- 따라서 `origin/blush-mask` 자산은 단순 복사만으로 복원되지 않는다.

#### 3.8. `origin/feature/brow-0626`의 brow PNG 계열 자산이 현재 브랜치에서 의도적으로 제외되어 있다

`origin/feature/brow-0626`에는 여러 brow PNG 자산과 관련 렌더링 코드가 있다.

예:

- `brow-png-dailyflat-hair-v1`
- `brow-png-dailyflat-sharp-v1`
- `brow-png-dailyflat-multiply-v1`
- `brow-png-daily-hair-v1`
- `brow-png-natural-hair-v1`
- `brow-png-narrow-hair-v1`
- `brow-png-lightbrown-hair-v1`
- `brow-soft-arch-fine-hair-v1`
- `brow-slim-tail-fine-hair-v1`

현재 runbook은 `feature/brow-0626`을 제외하고 PSD-only brow를 사용한다고 명시한다.

문제:

- 팀/사용자가 `feature/brow-0626`의 brow 에셋을 기대했다면, 현재 브랜치 정책과 기대가 충돌한다.
- 현재 브랜치에는 위 brow PNG 계열이 기본 런타임 후보로 들어와 있지 않다.
- 브랜치 전략상 의도된 제외였더라도, 사용자가 보기에는 "팀원 에셋을 안 쓴다"가 맞다.

영향:

- 병합용 브랜치가 팀 작업물을 통합했다는 인상을 주기 어렵다.
- PSD-only brow가 제품 결과로 충분한지 별도 시각 검증이 필요하다.

#### 3.9. `origin/feature/brow-0626`의 richer shader/renderer 경로가 현재 브랜치에 없다

`origin/feature/brow-0626` 쪽에는 brow 관련 셰이더 속성, MediaPipe renderer, 자산 변형 경로가 더 풍부하다. 현재 브랜치는 계약 일부와 PSD 자산만 가져오고, 그 렌더링 구현은 충분히 이식되지 않았다.

문제:

- 소스 브랜치에는 있는 조정 기능을 현재 브랜치에서는 UI/JSON 계약만 일부 흉내 내는 상태가 될 수 있다.
- 실제 렌더링 능력은 현재 단순 `SmoothRegionMask.shader` 수준에 묶인다.

영향:

- 병합이 기능 이식이 아니라 계약/문자열 이식에 가까워질 위험이 있다.

#### 3.10. brow 소스 정책이 사용자 기대와 충돌할 수 있다

현재 문서 정책은 brow를 `/Users/wiseungcheol/Documents/ARCore_canonical_face_texture_1.psd` 기반 PSD-only로 둔다. 동시에 사용자는 팀원 에셋 미사용을 문제로 보고 있다.

문제:

- 문서상 정책은 "PSD-only brow"지만, 사용자의 병합 기대는 "팀원 에셋 사용"일 수 있다.
- 이 정책 충돌이 명시적으로 정리되지 않았다.

영향:

- 구현을 아무리 정리해도 무엇이 정답 자산인지 합의되지 않으면 같은 문제가 반복된다.

### P0. 자산 채널/셰이더 해석 불일치 문제

#### 3.11. PSD brow 자산은 alpha에 shape가 있는데 현재 셰이더는 red 채널을 읽는다

현재 brow 기본 자산 `psd-arcore-brow-semi-arch-v1.png`는 shape 정보가 alpha 채널에 있는 것으로 보인다. 하지만 현재 `SmoothRegionMask.shader`는 red 채널을 마스크 값으로 사용한다.

확인된 특징:

- `psd-arcore-brow-semi-arch-v1.png`는 alpha가 있는 픽셀 수가 매우 제한적이다.
- 반면 RGB는 투명 영역에도 흰색 또는 값이 남아 있을 수 있다.
- 현재 셰이더는 `tex2D(_MaskTex, maskUv).r`로 red 채널을 사용한다.

문제:

- 투명해야 할 영역도 red 값 때문에 마스크로 인식될 수 있다.
- 현재 셰이더 기준으로는 brow가 눈썹 shape가 아니라 얼굴 넓은 영역 mask처럼 해석될 위험이 있다.
- alpha 기반 PNG를 쓰려면 셰이더가 alpha를 해석해야 하는데 현재 경로와 맞지 않는다.

영향:

- brow는 자산이 존재해도 실제 화면에서 잘못 보일 위험이 크다.
- 이 문제는 사전 게이트가 잡지 못한다.

#### 3.12. blush current asset과 team cheek session asset의 채널 계약이 다르다

현재 `e7-blush-balanced-uv-v0`는 red 채널 확률 마스크처럼 쓰일 수 있는 형태다. 반면 `origin/blush-mask`의 cheek session mask는 회색/흰 배경 기반의 source RGB luminance 계약에 가깝다.

문제:

- 현재 기본 자산은 현재 셰이더와 맞추기 위해 만들어진 generated/projection 자산에 가깝다.
- 팀 session mask는 별도 해석 로직 없이 넣으면 경계/밀도/배경 해석이 틀어질 수 있다.

영향:

- 팀 asset을 쓰려면 단순 파일 교체만으로는 안 된다.
- 현재 병합용 브랜치가 팀 asset을 회피한 것이 아니라, 렌더링 계약부터 다르게 되어 있는 상태다.

### P1. 영역별 문제

#### 3.13. lip: 상대적으로 가장 진행되어 있지만 실기기 acceptance가 없다

lip은 MediaPipe 기반 흐름, 조정 필드, 패키지 갱신 경로가 상대적으로 가장 많이 구현되어 있다.

문제:

- 실제 iPhone에서 boundary, inner fill, corner reach, opacity, finish가 제품 기준으로 통과했는지 증거가 없다.
- 다른 영역과 함께 켰을 때 레이어 순서/색/가림 문제가 없는지 확인되지 않았다.
- lip의 일부 UI 액션은 과거 상태에서 active region을 lip-only로 되돌리는 흔적이 있어 full-face 흐름에서 회귀 가능성이 있다.

영향:

- lip 단독 readiness와 full-face readiness를 혼동하면 안 된다.

#### 3.14. blush: 팀 source-of-truth와 현재 런타임 source-of-truth가 다르다

문제:

- runbook은 blush를 "team cheek UV mask + user adjustment"로 정의하지만, 현재 런타임 기본은 `e7-blush-balanced-uv-v0` 계열이다.
- `origin/blush-mask`의 `cheek-session-mask-*` 자산이 기본 후보로 들어와 있지 않다.
- `blush` UI 조정 필드는 `coverage`, `feather`, `maskThreshold` 정도로 제한적이다.
- team branch에 있던 coverage/intensity/densityGain/threshold 계열 정교한 계약과 다르다.

영향:

- blush는 "팀 에셋을 쓴 제품 기능"이라고 보기 어렵다.
- 사용자가 원하는 cheek look과 실제 default look이 다를 가능성이 높다.

#### 3.15. brow: 가장 심각한 불일치 영역이다

문제:

- 현재 기본 자산은 PSD-derived `psd-arcore-brow-semi-arch-v1`이다.
- 팀/브랜치 brow PNG 후보는 제외되어 있다.
- RN/UI/C#에는 많은 brow 조정값이 있으나 셰이더가 대부분 사용하지 않는다.
- PSD 자산은 alpha shape 기반인데 셰이더는 red 채널을 본다.
- cleanup이 꺼져 있다.
- MediaPipe anchor + PSD asset이 실제 얼굴 위에서 맞는지 시각 증거가 없다.

영향:

- brow는 "조정 가능"이라고 말하기 어렵다.
- 제품 화면에서 가장 먼저 티가 나는 실패 영역이 될 수 있다.

#### 3.16. eyeliner: provisional asset 상태에서 제품 완료로 보기 어렵다

현재 기본은 `e7-eyeliner-minimal-safe-uv-v0`이다.

문제:

- eyeliner는 문서상으로도 provisional 또는 safe/minimal 성격이 강하다.
- 상/하 eyelid, 두께, 꼬리, 눈매별 밀착 품질이 실기기에서 검증되지 않았다.
- 전용 팀 에셋 또는 최종 디자인 source-of-truth가 명확하지 않다.

영향:

- "full-face 4개 영역 완료"라고 말하기에는 eyeliner도 아직 낮은 확신 상태다.

#### 3.16A. 4개 region overlay의 transparent 합성 순서가 고정되어 있지 않다

현재 E3는 region마다 같은 face mesh topology를 복사한 child mesh를 만들고, 모두 transparent material로 렌더링한다.

문제:

- 각 overlay renderer의 `sortingOrder`가 모두 동일하다.
- 현재 shader는 `Transparent`, `ZWrite Off`, `ZTest Always`를 사용한다.
- lip/blush/brow/eyeliner 동시 활성화 시 어떤 레이어가 위에 와야 하는지 제품 계약이 코드에 명시되어 있지 않다.

영향:

- 실기기에서 색 겹침, 우선순위 뒤집힘, 깜빡임, 각도/표정에 따른 예기치 않은 시각 결과가 생길 수 있다.
- full-face 동시 활성 상태는 단일 region보다 별도 검증이 필요하다.

### P1. RN UX/상태 관리 문제

#### 3.17. UI가 모든 영역 활성화처럼 보여도 실제 readiness는 영역별로 다르다

현재 RN product flow는 full-face generation 후 네 영역을 활성화하고 inline adjustment를 제공하는 구조다.

문제:

- UI 활성화와 실제 렌더링 readiness가 분리되어 있지 않다.
- non-lip 영역은 실제 화면 변화가 약하거나 없을 수 있는데도 조정 가능한 기능처럼 노출된다.
- 사용자 입장에서는 "기능이 있는데 왜 안 먹지?"가 된다.

영향:

- 제품 품질 이전에 UX 신뢰가 깨질 수 있다.

#### 3.18. provider 이름을 숨기는 정책이 디버깅 투명성과 충돌한다

활성 roadmap은 UI에서 provider 이름을 노출하지 말라고 한다. 제품 UX로는 맞지만, 현재처럼 품질이 불안정한 단계에서는 내부 진단 정보가 부족해질 수 있다.

문제:

- 사용자는 어떤 영역이 어떤 source-of-truth를 쓰는지 앱에서 알기 어렵다.
- 팀원 에셋 미사용 같은 이슈가 뒤늦게 발견된다.

영향:

- 개발/검수 단계에서는 내부 debug 표시 또는 evidence 문서가 더 강해야 하는데 현재는 그 역할이 약하다.

#### 3.19. 상태 문구가 실제 증거보다 앞서갈 위험이 있다

RN 쪽 상태 메시지는 `ApplyRecipeJson` ack나 saved record를 근거로 applied처럼 보일 수 있다.

문제:

- Unity가 JSON을 받았다는 것과 화면에서 제대로 보인다는 것은 다르다.
- saved package가 있다는 것과 runtime visual proof가 있다는 것도 다르다.
- `generated_lip_mask_applied` ack가 성공하면 RN은 곧바로 applied 상태를 만들고, 그 직후 full-face `ApplyRecipeJson`을 다시 보낸다.
- UI 배너는 이 두 단계를 구분하지 않고 `AR 메이크업 적용됨`으로 묶어 보여준다.

영향:

- 내부 사용자/팀원이 "적용됨"을 "보이는 품질 통과"로 오해할 수 있다.
- lip dynamic mask ack 성공과 4-region full-face apply 성공이 하나의 완료처럼 읽힐 수 있다.

#### 3.19A. 제품 경로 kill-list가 아직 완전히 닫히지 않았다

active roadmap은 `Debug`, `진하게 보기`, `경계 보기` 같은 검증용 요소가 제품 사용자 경로에 남아 있으면 비완료로 본다.

문제:

- 현재 상단 chrome에 `Debug` 버튼이 남아 있다.
- 적용 완료 후 안내 문구도 `진하게 보기`, `경계` 같은 lab 검증 표현을 포함한다.
- 사용자가 보는 경로에서 product path와 validation path가 완전히 분리되지 않았다.

영향:

- 302 제품 포팅 기준으로는 아직 lab/debug 흔적이 남아 있는 상태다.
- 제품 흐름이 완료된 것처럼 보여도 실제로는 내부 검증 UI가 섞여 있다.

### P1. 저장/재적용 계약 문제

#### 3.20. save/load가 실제 look parameter를 보존하는지 충분히 증명되지 않았다

runbook risk register에도 save/load look parameter loss가 있다.

문제:

- saved record schema가 `generatedMaskId`, `packagePath`, `metadataPath`, `status` 중심이다.
- 현재 RN 저장 경로는 `selectedCandidate.package`를 `saveGeneratedPackage`로 넘기며, 저장 파일 이름도 `generated_lip_package.json`이다.
- saved package에 모든 region adjustment가 들어가는지 확인이 필요하다.
- 다시 불러온 뒤 Unity apply 결과가 동일한지 확인되지 않았다.
- non-lip의 no-op 조정값은 저장되어도 시각적으로 의미가 없을 수 있다.

영향:

- 사용자가 조정 후 저장해도 다시 열었을 때 같은 결과가 나오지 않을 수 있다.
- 현재 코드는 full-face 저장이 아니라 generated lip package 저장을 확장해 쓰는 구조에 더 가깝다.
- roadmap의 "네 region 모두 저장 package에 포함" 기준은 아직 구조적으로 미충족일 가능성이 크다.

#### 3.21. static runtime asset과 user-adjusted package가 혼동된다

현재 full-face package에는 canonical runtime layer가 있지만, 실제 사용자 조정으로 만들어진 최종 시각 결과와 동일하다고 보기 어렵다.

문제:

- asset id가 고정되어 있고 파라미터만 저장되는 영역이 있다.
- 파라미터가 셰이더에서 무시되면 저장값도 의미가 없다.

영향:

- "패키지 저장 완료"가 실제 제품 결과 보존을 의미하지 않을 수 있다.

### P1. 브랜치 병합 전략 문제

#### 3.22. 선택적 이식이 계약만 가져오고 구현을 충분히 가져오지 못했다

runbook은 selective transplant를 택했다. 이 전략은 기존 product flow를 보존하는 장점이 있지만, 현재는 asset/renderer 구현 누락을 만들었다.

문제:

- `origin/blush-mask`의 자산/검증 계약이 들어오지 않았다.
- `origin/feature/brow-0626`의 richer brow renderer/asset 경로가 들어오지 않았다.
- RN/JSON/C# 계약은 이식되었지만 shader/material 경로가 따라오지 못했다.

영향:

- 병합 브랜치가 "통합본"처럼 보이지만 실제로는 핵심 시각 구현이 빠져 있다.

#### 3.23. `feature/brow-0626` 제외 정책이 현재 문제의 한 축이다

문서상 `feature/brow-0626`은 명시적으로 제외되어 있다.

문제:

- 제외 자체는 과거 정책상 의도였지만, 지금 사용자의 요구는 팀 에셋 사용 여부를 문제 삼고 있다.
- 따라서 이전 정책을 그대로 유지할지, 팀 에셋을 다시 통합할지 결정이 필요하다.

영향:

- 정책을 바꾸지 않으면 "팀원 에셋 안 씀" 문제는 계속 남는다.

### P1. 문서/상태 보고 문제

#### 3.24. `TECH_VALIDATION_RESULT.md`가 너무 많은 히스토리를 포함해 현재 실패점을 빠르게 보기 어렵다

`TECH_VALIDATION_RESULT.md`에는 현재 snapshot과 과거 검증 로그가 함께 많이 누적되어 있다.

문제:

- "prebuild pass"와 "runtimeReady false"가 같은 문서 안에 있어 상태가 혼동된다.
- 현 상태의 가장 큰 blocker인 shader/asset mismatch가 snapshot 최상단에서 충분히 강조되지 않는다.
- RN Jest 통과 기록이 현재 UI/테스트 상태와 어긋날 가능성이 있다.
- 과거 brow pre-Xcode evidence가 현재 PSD brow runtime path를 검증하지 않았다는 점이 빠르게 드러나지 않는다.

영향:

- 팀원이 문서를 보면 통과/완료로 오해할 수 있다.

#### 3.25. runbook의 완료 표시가 실제 렌더링 완료와 섞여 보인다

runbook에는 M4/M5 등 일부 milestone 완료 기록이 있다.

문제:

- milestone 완료가 "계약/자산 준비"인지 "iPhone 제품 품질 통과"인지 문맥을 꼼꼼히 보지 않으면 헷갈린다.
- 현재 shader no-op 문제와 asset source mismatch가 runbook 완료표에 직접 드러나지 않는다.

영향:

- 다음 작업자가 "이미 끝난 영역"으로 오해하고 깊은 진단을 건너뛸 수 있다.

#### 3.26. active roadmap, runbook, snapshot의 상태 단어가 다르게 읽힌다

문제:

- active roadmap은 complete implementation을 목표로 한다.
- snapshot은 partial/pre-xcode 경계와 runtimeReady false를 말한다.
- runbook은 selective transplant milestone을 완료로 기록한다.

영향:

- "무엇이 완료이고 무엇이 미완료인지"가 사람마다 다르게 해석된다.

### P1. 검증 스크립트 문제

#### 3.27. `check_e7_prebuild_gate.mjs`가 shader source를 직접 검증하지 않는다

현재 gate는 `E3RegionMaskOverlay.cs`에 속성 문자열이 있는지 확인하지만, `SmoothRegionMask.shader`에 같은 속성이 있는지는 확인하지 않는다.

문제:

- C#에서 `SetFloat("_BrowArch", value)`를 호출해도 shader가 `_BrowArch`를 모르면 결과가 없다.
- 이 상태를 gate가 통과시킨다.
- gate는 post-applied AR UI를 실제 동작 대신 문자열 패턴과 안내 문구로 주로 확인한다.
- 따라서 최신 `App.test.tsx` 실패나 UI/문구 drift를 직접 잡아내지 못한다.

영향:

- 가장 중요한 "조정값이 실제로 먹는가"를 자동 검증하지 못한다.
- RN gate가 최신 UI 품질과 동기화되어 있다는 보장이 없다.

#### 3.28. gate가 team blush source-of-truth를 강제하지 않는다

문제:

- `origin/blush-mask`의 `cheek-session-mask-*` 자산 존재를 확인하지 않는다.
- source RGB luminance 기반 shader/contract가 있는지 확인하지 않는다.
- team asset 미사용 상태도 pass 가능하다.

영향:

- 팀원 에셋 미사용 문제가 자동 검증에서 누락된다.

#### 3.29. gate가 PNG 채널 계약을 검사하지 않는다

문제:

- PNG가 alpha 기반인지 red-channel 기반인지 확인하지 않는다.
- shader가 어떤 채널을 읽는지와 asset 채널 구조가 맞는지 확인하지 않는다.

영향:

- brow처럼 alpha shape 자산을 red-channel shader로 읽는 문제를 놓친다.

#### 3.30. smoke log가 visual proof를 대체하고 있다

문제:

- smoke log는 parser/dispatch 성공을 확인할 수 있지만 시각 결과를 확인할 수 없다.
- screenshot/contact sheet/material sampling 없이 smoke pass만으로는 제품 품질 근거가 부족하다.

영향:

- 테스트 이름은 통과처럼 보이나 실제 제품 검수에는 빈칸이 남는다.

### P2. 워킹트리/브랜치 위생 문제

#### 3.31. 현재 브랜치가 원격보다 ahead 상태이고 워킹트리가 dirty다

확인된 상태:

- `병합용브랜치`가 `origin/병합용브랜치`보다 ahead 상태다.
- 여러 파일이 수정되어 있다.
- `MAKEUPAR_TO_302_INTEGRATION_KO.md`가 untracked 상태다.

현재 수정 파일:

- `TECH_VALIDATION_RESULT.md`
- `rn/MakeupARValidation/App.tsx`
- `scripts/build_m3_unityframework.sh`
- `scripts/e7_prebuild_gate/check_e7_prebuild_gate.mjs`
- `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity`
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`

문제:

- 어떤 변경이 의도된 병합 결과이고 어떤 변경이 임시 작업인지 추적이 어렵다.
- 추가 진단/수정 시 작업자 실수 가능성이 커진다.

영향:

- 병합 리뷰와 책임 추적이 어려워진다.

#### 3.32. Unity scene 파일에 whitespace 문제가 있다

`git diff --check`에서 Unity scene trailing whitespace가 보고되었다.

확인된 위치:

- `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity` line 395
- `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity` line 641
- `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity` line 674

문제:

- 기능 실패의 핵심 원인은 아니지만, 병합 전 hygiene gate에서 걸릴 수 있다.
- 자동 포맷/패치가 Unity scene을 건드릴 경우 불필요한 diff가 커질 수 있다.

영향:

- 병합 안정성과 리뷰 품질을 떨어뜨린다.

### P2. evidence/프라이버시/운영 문제

#### 3.33. 현재 evidence는 제품 품질 판단에 부족하다

문제:

- 현재 상태를 증명하는 대표 screenshot/frame이 없다.
- 각 region별 before/after adjustment evidence가 없다.
- 실기기 motion/expression evidence가 없다.

영향:

- 어떤 영역이 실제로 실패하는지 팀이 시각적으로 빠르게 합의하기 어렵다.

#### 3.34. 로컬-only 원칙은 지켜야 하지만, 그 때문에 증거 수집 절차가 더 명확해야 한다

문제:

- camera frame/raw evidence는 privacy 때문에 장기 저장하면 안 된다.
- 하지만 현재는 대체 evidence인 curated screenshot/contact sheet도 충분하지 않다.

영향:

- 안전하게 남길 수 있는 evidence 형식이 없으면 매번 말로만 상태를 설명하게 된다.

## 4. 원격 브랜치 비교로 본 누락

### 4.1. `origin/blush-mask`에서 현재 브랜치로 들어오지 않은 핵심

누락 또는 미반영으로 보이는 항목:

- `cheek-session-mask-1-v1`부터 `cheek-session-mask-5-v1`까지의 session mask 자산
- cheek/blush contract verify script가 기대하는 strict asset copy 계약
- source RGB luminance 기반 density/coverage 해석
- session mask별 runtime selection
- calibration parameter set

현재 브랜치에 있는 것:

- `e7-blush-balanced-uv-v0`
- `blush-balanced-soft-oval-v0`
- `cheek-smooth-mask-v1`

판단:

- 현재 브랜치의 blush는 team cheek session mask 통합본이 아니다.
- 추가로, 이 자산들은 현재 parser/whitelist/shader 계약과도 맞지 않아 단순 복사로 복원되지 않는다.

### 4.2. `origin/feature/brow-0626`에서 현재 브랜치로 들어오지 않은 핵심

누락 또는 제외된 항목:

- brow PNG 후보 다수
- cheek PSD derivative 후보 다수
- richer brow shader 속성/렌더링 경로
- MediaPipe renderer 관련 구조

현재 브랜치에 있는 것:

- `psd-arcore-brow-semi-arch-v1`
- `brow-cleanup-source-v1`
- `e7-brow-balanced-uv-v0`
- RN/C# 계약 일부

판단:

- 현재 브랜치의 brow는 `feature/brow-0626` 통합본이 아니라 PSD-only 축소 경로다.
- 과거 `pre-xcode-ready` evidence가 가리킨 `e7-brow-balanced-uv-v0`와 현재 기본 runtime인 `psd-arcore-brow-semi-arch-v1` 사이에 증거 단절이 있다.

## 5. 문제 심각도 요약

| ID | 영역 | 심각도 | 요약 |
| --- | --- | --- | --- |
| D-01 | 전체 | P0 | 실기기 시각 증거가 없어 제품 품질 완료가 아니다 |
| D-02 | 전체 | P0 | prebuild gate가 shader/visual mismatch를 잡지 못한다 |
| D-03 | brow | P0 | RN/C# brow 조정값 대부분이 현재 shader에서 no-op일 수 있다 |
| D-04 | brow | P0 | PSD brow asset은 alpha shape인데 shader는 red channel을 읽는다 |
| D-05 | blush | P0 | team cheek session masks가 현재 기본 경로에 없다 |
| D-06 | blush | P0 | team mask luminance 계약과 현재 red-channel shader 계약이 다르다 |
| D-07 | non-lip | P0 | non-lip 영역은 정적 mask + 일부 param 전달에 가깝다 |
| D-08 | brow | P0 | cleanup path가 기본적으로 꺼져 있다 |
| D-09 | save/load | P0 | 저장 경로가 generated lip package 중심이며 full-face 저장 계약이 구조적으로 불충분하다 |
| D-10 | brow | P0 | 과거 brow pre-Xcode evidence가 현재 PSD brow runtime을 검증하지 못한다 |
| D-11 | eyeliner | P1 | provisional asset 상태이며 제품 품질 근거가 없다 |
| D-12 | lip | P1 | 단독 구현은 상대적으로 강하지만 full-face visual acceptance가 없다 |
| D-13 | runtime | P1 | 4개 region transparent overlay의 합성 순서가 고정되어 있지 않다 |
| D-14 | RN gate | P1 | RN Jest/문서/gate 최신성이 어긋나 현재 품질 근거로 쓰기 어렵다 |
| D-15 | UX | P1 | UI 활성화와 실제 렌더링 readiness가 분리되어 있지 않다 |
| D-16 | UX | P1 | applied 상태와 full-face apply 단계가 UI에서 섞여 보인다 |
| D-17 | branch | P1 | selective transplant가 구현보다 계약 이식에 치우쳤다 |
| D-18 | docs | P1 | snapshot/runbook/roadmap 상태 단어와 과거 증거가 혼동된다 |
| D-19 | product path | P1 | Debug/경계/진하게 보기 등 lab 검증 요소가 제품 경로에 남아 있다 |
| D-20 | hygiene | P2 | dirty worktree, ahead commits, untracked doc이 있어 리뷰가 어렵다 |
| D-21 | hygiene | P2 | Unity scene trailing whitespace가 남아 있다 |

## 6. 현재 판단

현재 `병합용브랜치`의 가장 큰 문제는 "코드가 아예 없다"가 아니다. 오히려 RN UI, JSON, Unity bridge, 일부 런타임 자산, gate 문서가 있어서 겉으로는 꽤 진행된 것처럼 보인다.

하지만 제품 품질에서 중요한 지점은 다음이다.

- 조정값이 실제 셰이더에 연결되어야 한다.
- 자산 채널과 셰이더 해석 방식이 맞아야 한다.
- 팀원이 만든 source-of-truth 자산이 명확하게 들어와야 한다.
- 저장/재적용 경로가 네 region 기준으로 닫혀 있어야 한다.
- 테스트와 과거 증거가 현재 런타임과 같은 대상을 검증해야 한다.
- iPhone에서 실제로 보이고 움직이는 증거가 있어야 한다.

이 여섯 가지가 현재 동시에 부족하다.

따라서 이 브랜치는 아직 병합 완료/제품 품질 완료가 아니라, "계약 이식 후 시각 런타임 통합이 미완료된 중간 상태"로 보는 것이 정확하다.

## 7. 이번 세션에서 새로 고치지 않은 이유

사용자 지시가 "이 세션에서 고칠 게 아니며, 해결보다 진단에 모든 리소스를 집중하라"였기 때문에 수정은 수행하지 않았다.

또한 현재 문제는 한두 줄 패치로 끝나지 않는다. 특히 다음 결정이 선행되어야 한다.

- blush source-of-truth를 현재 generated asset으로 둘지, `origin/blush-mask`의 cheek session mask로 바꿀지
- brow source-of-truth를 PSD-only로 유지할지, `origin/feature/brow-0626`의 brow PNG 계열을 쓸지
- shader를 현재 단순 마스크 방식으로 유지할지, branch별 richer renderer 계약을 이식할지
- gate를 문자열 통과 중심에서 shader/asset/visual evidence 중심으로 바꿀지

이 결정 없이 바로 고치면 또 다른 "겉보기 통과" 상태가 생길 가능성이 높다.
