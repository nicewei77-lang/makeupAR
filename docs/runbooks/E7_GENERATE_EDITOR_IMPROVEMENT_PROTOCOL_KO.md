# E7 Generate Editor Improvement Protocol

## Purpose

이 문서는 2026-06-29 iPhone 실기기 리뷰 이후 나온 E7 립 Generate 잔존 문제를 다음 구현에서 흔들리지 않게 다루기 위한 개선 프로토콜이다.

대상 문제는 단일 버그가 아니다. UI/UX, 비동기 상태, 마스크 조정축, 블렌딩 후보, AR 재적용 흐름이 섞여 있다. 따라서 다음 구현은 "한 번에 예쁘게 고치기"가 아니라 아래 순서대로 원인과 증거를 나눠 닫는다.

## Current Decision

```txt
Primary direction:
  Capture 이후에는 live Unity camera 위에 반투명 wizard를 계속 얹지 않는다.
  Extract 이후부터는 고정된 촬영 사진 기반 editor로 전환한다.

Shared UV reference:
  Team canonical source is evidence/references/arcore-canonical-face-texture-v1/.
  Source PSD is ARCore_canonical_face_texture_1.psd, 4096x4096, SHA-256 d7d3b87caa4929f561fc45a4b2313990542fedefeeadd6b5e8801d18bef1b8a7.
  Use it as the common UV discussion/reference mask basis, not as runtime proof by itself.
  It is not currently the runtime lip mask source.
  Because this PSD is an ARCore canonical reference, ARKit 1220-vertex UV runtime use requires a converted derivative plus round-trip/device validation.

Default lip mask direction:
  blendshapeAssist는 기본 flow에서 내린다.
  neutral 기반 마스크 + 정밀 editor + upper inner fill 조정축을 먼저 완성한다.

Before app integration:
  inner fill / upper inner fill 샘플 이미지는 축의 안전성을 확인하는 데 쓴다.
  최종 수치는 사용자가 앱에서 직접 조정하고, 그 값을 saved package/runtime payload/evidence에 저장한다.

Fast execution order:
  0. inner fill / upper inner fill 샘플을 먼저 만든다.
  1. lip-only fixed editor MVP를 먼저 닫는다.
  2. AR "수정 -> editor 복귀 -> 다시 적용" loop를 같은 1차 구현에 포함한다.
  3. blush/brow/eyeliner 확장은 패턴만 보존하고 이번 구현 범위에서는 제외한다.
```

## Non-Negotiable UX Principles

1. 촬영 단계와 편집 단계는 시각적으로 분리한다.
2. 사용자가 어떤 화면을 기준으로 판단해야 하는지 한 번에 보여야 한다.
3. 입술, 블러셔, 눈썹, 아이라인은 같은 region editor 패턴으로 확장 가능해야 한다.
4. 편집 화면에서는 마스크 판단을 방해하는 live camera 배경을 숨긴다.
5. 버튼은 safe area 안에 항상 보여야 한다.
6. 주요 액션은 화면 밖으로 밀리면 실패로 본다.
7. 조정값 숫자 변화와 시각 변화는 분리하지 않는다.
8. 오래 걸리는 작업은 반드시 loading/progress 상태를 보여준다.
9. 블렌딩처럼 비용이 큰 기능은 품질 이득이 증명될 때만 기본 flow에 둔다.
10. 첫 구현은 lip-only로 자르고, 다른 region은 API/상태 구조가 막히지 않게만 설계한다.

## Screen Model

### Stage A. Live Capture

사용 목적:

```txt
- 얼굴 정렬
- 표정/부위 촬영
- AR runtime 확인
```

UI:

```txt
- live camera full screen
- 작은 top chrome
- 현재 필요한 capture action만 하단에 표시
- 완료된 shot은 compact status로만 표시
```

주의:

```txt
촬영 중에는 editor처럼 보이게 만들지 않는다.
```

### Stage B. Extract / Generate Loading

사용 목적:

```txt
- native provider 실행
- 후보 package 생성
- preview PNG/render 준비
```

UI:

```txt
- 마지막 촬영 사진을 고정 배경으로 표시
- 중앙 loading panel 또는 full-screen overlay
- 진행 문구:
  "입술 경계를 찾는 중"
  "마스크 후보를 만드는 중"
  "미리보기를 준비하는 중"
- 취소/다시 촬영은 작게 제공
```

Progress source:

```txt
- requestId
- current stage
- elapsedMs
- cancel/ignore-late-result state
- native save/apply ack state when relevant
```

금지:

```txt
- 버튼만 disable하고 기다리게 하기
- live camera와 loading card를 겹쳐서 보여주기
- 처리 중인지 사용자가 추측하게 만들기
```

### Stage C. Fixed Photo Region Editor

사용 목적:

```txt
- 생성된 mask 후보 확인
- 부위 선택
- 확대/축소/이동
- 조정축 적용
- 저장 후보 확정
```

기본 화면:

```txt
- 고정 촬영 사진
- 얼굴 전체가 처음에 보임
- 편집 가능한 region을 은은한 overlay로 표시
- 사용자가 region을 탭하면 자동 zoom
```

First implementation scope:

```txt
Ship lip-only first.
Keep blush/brow/eyeliner as future region contracts, not first-build UI.
```

Region tap behavior:

```txt
lip tap:
  입술 bbox 중심으로 animated zoom
  하단 toolbar가 lip 전용 조정축으로 변경

blush tap:
  양볼 영역으로 zoom 또는 좌/우 선택
  blush 전용 크기/농도/위치 조정 표시

brow tap:
  눈썹 영역으로 zoom
  brow 두께/길이/위치 조정 표시

eyeliner tap:
  눈 영역으로 zoom
  wing/두께/꼬리/라인 위치 조정 표시
```

Navigation:

```txt
- "전체 얼굴" 버튼: zoom out
- pinch zoom: 더 확대/축소
- pan: 확대 상태에서 이동
- double tap region: region zoom toggle
```

Editor overlay modes:

```txt
원본:
  촬영 사진만 표시

마스크:
  마스크 alpha만 강하게 표시

겹쳐보기:
  촬영 사진 + 색상 overlay + boundary

비교:
  누르고 있는 동안 before, 떼면 after
```

### Stage D. AR Validation

사용 목적:

```txt
- 실제 ARFace runtime에서 face attachment 확인
- 색/농도/진하게/경계 보기 확인
- motion/expression check
```

UI:

```txt
- live AR camera
- bottom controls는 작고 접을 수 있어야 함
- "수정" 액션은 명확하게 노출
```

AR correction policy:

```txt
Immediate in AR:
  color
  opacity
  strong validation mode
  boundary visibility
  feather/threshold if shader-only

Return to editor:
  mask shape
  upper/lower geometry
  inner fill
  corner reach
  generated UV texture rebuild
```

Reason:

```txt
이미 Unity에 올라간 generated mask는 raw UV texture다.
색/농도는 shader parameter로 즉시 바꿀 수 있지만,
shape 수정은 texture/package 재생성이 필요하다.
따라서 AR 위에서 모든 shape을 live-edit하려고 하지 말고,
"AR에서 문제 발견 -> editor로 복귀 -> 재적용"을 제품 flow로 둔다.
```

## Close / Back Protocol

Close must not mean "throw away all work" after capture.

State-specific behavior:

```txt
capture before any saved shot:
  Close exits Generate.

after at least one captured shot:
  Close asks:
    "편집을 닫을까요?"
    choices:
      "추출로 돌아가기"
      "촬영부터 다시"
      "나가기"

extract/generate loading:
  Close cancels or waits for current request guard to settle.
  Late async result must be ignored.

fixed photo editor:
  Close returns to Extract or candidate overview.
  It must not force six-shot recapture.

AR validation:
  Close exits AR validation.
  generated package and capture set stay available unless user explicitly resets.
```

## Button Density Rules

Mobile vertical space is a product constraint, not a styling detail.

Rules:

```txt
- Primary CTA is sticky at bottom safe area.
- Secondary actions go into compact row or overflow menu.
- Debug is not visible by default.
- Step chips collapse after capture/extract.
- Candidate cards must not push the primary CTA below screen.
- Text cannot be the only progress indicator.
```

For the lip editor:

```txt
Top:
  Back / 전체 얼굴 / mode toggle

Center:
  image editor canvas

Bottom:
  selected axis label
  slider
  small - / + stepper
  Apply to AR
```

## Lip Adjustment Axis Protocol

### Existing axes

Current axes:

```txt
cornerReach:
  입꼬리/가로 방향 외곽 보정

upperLipTightness:
  윗입술 바깥 경계 상하 보정

lowerLipTightness:
  아랫입술 바깥 경계 상하 보정

verticalOffset:
  전체 입술 위치 이동
```

Current limitation:

```txt
이 축들은 대부분 outer boundary를 넓히거나 움직인다.
사용자가 본 "윗입술 안쪽이 빈다" 문제는 outer boundary가 아니라 inner mouth hole 문제다.
```

### New candidate axes

Do not expose all of these in the app before visual sample review. The first
app-facing promotion candidate is `upperInnerFill`, because the initial
buildless sample keeps lower-lip growth bounded while reducing the upper inner
mouth gap.

Candidate axes:

```txt
innerFill:
  inner mouth hole 전체를 줄이거나 늘림

upperInnerFill:
  윗입술 안쪽 경계만 입 안쪽 방향으로 채움

lowerInnerProtect:
  아랫입술/입 안쪽으로 과도하게 채워지는 것을 방지

mouthGapProtect:
  치아/입 안쪽 공간을 반드시 남기는 보호 강도
```

Recommended first app-facing labels:

```txt
입 안쪽
윗입술 안쪽
입 안 보호
```

## Pre-App Sample Experiment Protocol

Goal:

```txt
앱에 조정축을 넣기 전에 같은 촬영 사진에서 후보 이미지를 만들고,
사용자가 고를 수 있는지 확인한다.
```

Inputs:

```txt
- fixed frame.png
- current generated package
- lipBoundary2D outer/inner points
- ARFace export
- current raw UV mask
- team canonical UV reference manifest:
  evidence/references/arcore-canonical-face-texture-v1/manifest.json
```

Generate sample variants:

```txt
baseline_current
inner_fill_weak
inner_fill_medium
inner_fill_strong
upper_inner_fill_weak
upper_inner_fill_medium
upper_inner_fill_strong
upper_inner_fill_with_mouth_gap_protect
upper_inner_fill_with_lower_protect
```

Each sample must output:

```txt
- full-face overlay
- lip crop overlay
- mask-only crop
- before/after contact sheet
- metrics JSON
```

Metrics:

```txt
uvResolution
positiveTexels
alphaBoundingBoxTexels
edgeBandRatio
innerHolePositiveRatio
upperInnerFilledTexels
mouthGapRemainingTexels
lowerLipGrowthRatio
alphaChecksum
previewVsUvRoundTripDelta
```

Human review questions:

```txt
1. 윗입술 안쪽 빈 느낌이 줄었는가?
2. 치아/입 안까지 칠하지 않는가?
3. 아랫입술이 더 두꺼워지지 않았는가?
4. 입꼬리/중앙 경계가 어색하지 않은가?
5. 원본 사진 위에서 사용자가 조정 차이를 즉시 볼 수 있는가?
```

Promotion rule:

```txt
Only promote an axis to RN app when:
  - samples show the axis is directionally safe enough for in-app tuning
  - mouth gap is not destroyed
  - lower lip growth is bounded
  - metrics and contact sheet are saved
```

Initial sample run:

```txt
script:
  .venv/bin/python scripts/e7_lip_candidate_generator/generate_inner_fill_samples.py

output:
  evidence/e7-lip-inner-fill-samples/inner-fill-20260629T152646Z/
  evidence/e7-lip-inner-fill-samples/mesh-roundtrip-review/

observed:
  upper_inner_fill_040:
    upperInnerFilledPixels=23
    mouthGapRemainingRatio=0.914
    lowerLipGrowthRatio=1.000

  upper_inner_fill_060:
    upperInnerFilledPixels=25
    mouthGapRemainingRatio=0.906
    lowerLipGrowthRatio=1.000

decision:
  Expose upperInnerFill as the first guarded lip inner-fill adjustment axis.
  Keep innerFill hidden until it shows a clear benefit over upperInnerFill.
  Do not hard-code the final value from static samples. Let the user tune it
  on-device in the fixed-photo editor and persist the chosen value in the
  generated package plus runtime apply payload.
```

## BlendshapeAssist Explanation and Decision Protocol

### Beginner explanation

기본 후보는 정면 사진 한 장에서 입술을 찾는다.

블렌딩 후보는 정면, 입 벌림, 미소, 오므림, 좌/우 각도 사진을 보고 "여러 사진에서 입술로 보이는 영역"을 합쳐보는 방식이다.

의도는 좋다:

```txt
- 한 장에서 놓친 입꼬리를 다른 표정 사진이 보완
- 표정 변화에도 덜 깨지는 평균 입술 영역 확보
- AR에서 움직일 때 더 안정적인 mask 기대
```

하지만 현재 결과는 비용 대비 이득이 증명되지 않았다.

### Expert explanation

Current implementation:

```txt
1. 각 shot에서 screen-space lip boundary를 얻는다.
2. 각 boundary를 ARFace UV space로 projection한다.
3. neutral shot의 UV mask를 anchor로 둔다.
4. mouthOpen/smile/pucker/yaw shot의 alpha mask를 낮은 weight로 더한다.
5. weighted score가 threshold 이상이고 neutral-expanded bbox 안이면 expression envelope를 허용한다.
6. 어떤 shot이든 inner mouth로 본 texel은 강하게 suppress한다.
```

Critical assumption:

```txt
각 shot에서 같은 UV texel이 같은 의미의 입술 부위를 가리킨다.
```

Why this can fail:

```txt
- 표정 변화에서 입술 soft tissue가 움직인다.
- 입을 벌리면 inner mouth visibility가 크게 바뀐다.
- mouthOpen shot은 윗입술 안쪽과 입 안쪽 hole의 경계가 불안정하다.
- expression shot의 mask가 neutral과 완전히 정렬되지 않으면 consensus가 좋은 영역을 깎을 수 있다.
- uvOnlyVsBlendAlphaDelta > 0은 "다르다"는 뜻이지 "더 좋다"는 뜻이 아니다.
```

Observed product decision:

```txt
blendshapeAssist is real but not product-proven.
It should not be the default path until it beats neutral in visible quality.
```

Blend default rule:

```txt
Default:
  neutral / non-blend

Hidden or experimental:
  blendshapeAssist

Show blend only when:
  - preview visibly improves lip coverage or stability
  - upper inner lip is not suppressed
  - edge quality is not worse
  - human review prefers it
```

If blend remains:

```txt
Do not require six photos by default.
Use optional "표정 보조 실험" mode.
Explain that it may help when neutral result is weak.
Provide side-by-side lip crop and mask-only diff.
```

## Implementation Phases

### Phase 0. Inner fill sample generator

Why first:

```txt
윗입술 안쪽 비어 보임은 핵심 품질 리스크다.
UI를 크게 고치기 전에, 어떤 mask axis가 실제로 좋아 보이는지 먼저 증명한다.
```

Changes:

```txt
- local script generates sample variants
- contact sheet and metrics
- no RN app change yet
```

Proof:

```txt
- generated sample folder
- contact sheet
- metrics JSON
- user/human decision note
```

### Phase 1. Product flow restructure

Changes:

```txt
- Extract 이후 live Unity background 숨김
- fixed photo editor screen 추가
- loading/progress overlay 추가
- Close/back state machine 수정
- primary CTA sticky safe-area 보장
- requestId/stage/elapsed/ack state를 loading UI와 log에 연결
```

Buildless proof:

```txt
- RN Jest: Close after capture does not reset six shots.
- RN Jest: Extract/generate shows loading state.
- RN Jest: primary CTA remains present in editor.
- screenshot/playback: fixed photo editor has no live camera bleed.
```

### Phase 2. Lip-only region editor MVP

Changes:

```txt
- face overview editor
- lip tap to auto zoom
- overlay mode toggles
- lip crop comparison
- whole-face return
```

Buildless proof:

```txt
- RN Jest for region selection state.
- visual screenshot for overview, lip zoom, full-face return.
```

Deferred from MVP:

```txt
- blush/brow/eyeliner UI
- full pinch/pan polish
- double-tap zoom toggle
```

### Phase 3. App integration of accepted axis

Changes:

```txt
- add only the accepted inner-fill axis
- immediate 2D preview transform
- async package rebuild guarded by request id
- save/apply disabled while package is stale
- save/apply reuses existing ack gate
```

Buildless proof:

```txt
- test axis changes preview path/mask metrics
- test stale rebuild ignored
- test save disabled while package stale
```

### Phase 4. AR correction loop

```txt
- AR "수정" button opens fixed photo editor with current package
- "AR에 다시 적용" saves/reposts generated package
- progress visible until ack
```

Buildless proof:

```txt
- test AR correction route preserves capture/package state.
- test re-apply enters progress state and waits for ack.
```

Device proof:

```txt
- AR에서 문제 확인
- 수정으로 이동
- 조정
- 다시 AR 적용
- matching generated-mask ack
- screenshot/video evidence
```

### Phase 5. Region expansion and blend re-evaluation

Changes:

```txt
- blush/brow/eyeliner region editor 확장
- pinch/pan polish
- blendshapeAssist side-by-side quality re-check
```

Entry condition:

```txt
- lip-only flow has passed buildless checks and next iPhone review.
```

## Implementation Checkpoint 2026-06-30

Status:

```txt
source/buildless passed
device/user visual proof pending
```

Implemented first:

```txt
- upperInnerFill is the first app-facing inner lip fill axis.
- innerFill stays hidden/default 0.
- The user-tuned value is stored in saved package/runtime apply payload/evidence metadata.
- Adjustment preview starts zoomed to the lip and can be tapped back to full-face view.
- Extract/generate has an explicit loading panel.
- Close after capture/apply preserves work and returns to extract/adjust.
- Preview-size gate records actual values and accepts values above the minimum.
```

Verified:

```txt
RN TypeScript: pass
RN Jest: 35 passed
RN ESLint: pass
packages/lip-generate-core typecheck/test: pass
e7:build-plan: skip-unityframework-run-rn-xcode-only
e7:prebuild:full: 38 pass / 0 fail / 0 warn
git diff --check: pass
```

Still needs iPhone review:

```txt
- user-selected upperInnerFill value
- saved package pull with the selected value
- matching generated-mask apply ack
- visual acceptance for upper inner lip cover
- motion/expression attachment after the tuned mask is applied
```

## Acceptance Gates

Ready for next iPhone build only when:

```txt
- Extract 이후 live camera bleed가 없다.
- loading/progress가 모든 long-running step에 있다.
- Close/back does not force unnecessary recapture.
- lip tap auto zoom works.
- editor supports whole-face return.
- primary action is never below screen.
- selected adjustment visibly changes preview before save.
- inner fill sample has accepted visual candidate or remains out of app.
- blend is default-off unless quality is proven.
- build-plan says UnityFramework status is understood.
```

Not product-quality until:

```txt
- real-device visual review accepts lip coverage.
- upper inner lip is not visibly empty.
- mouth gap is not overfilled.
- AR apply ack is pulled or observed.
- slow/fast yaw and mouth open/close are recorded.
- FPS/frame-time/memory/thermal are recorded when runtime changes matter.
```

## Out Of Scope For This Protocol

```txt
- live per-frame AI parsing
- cloud upload
- commercial SDK switch
- Android
- claiming blendshapeAssist is better from metadata alone
- adding more capture steps before the neutral editor is good
```
