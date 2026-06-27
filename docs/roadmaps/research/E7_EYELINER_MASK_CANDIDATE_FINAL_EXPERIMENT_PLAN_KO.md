# E7 아이라인 마스크 후보 최종 실험 계획

상태: 실행 전 계획  
작성일: 2026-06-27 KST  
범위: buildless/local-only 아이라인 후보 생성 실험  
상위 계약: `docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md`

## 1. 한 줄 목표

앱 구현으로 넘어가기 전에, 아이라인에 대해 **MediaPipe upper eyelid landmark 기반 후보**를 빠르게 여러 개 생성하고, 기존 eye-prior 후보와 비교해서 앱에 넣을 tracking 조합, style preset, 사용자 조정축을 확정한다.

## 2. 왜 마지막 실험이 필요한가

현재 repo에는 이미 `eyeliner-minimal-safe-lashline-v0` 후보가 있고 `pre-xcode-ready` package도 존재한다.

하지만 기존 구현의 trace는 실제 MediaPipe eyelid landmark 직접 추적이라기보다 아래 방식에 가깝다.

```txt
eye_prior_dark_pixel_upper_lashline
```

즉, 넓은 eye prior 안에서 어두운 윗부분을 찾아 upper lashline처럼 추정한 후보다. 이 방식은 빠른 baseline으로는 의미가 있지만, 최종 앱의 아이라인 기능을 설계하기에는 부족하다.

이번 마지막 실험의 핵심 질문은 이것이다.

```txt
MediaPipe eye landmarks를 기준선으로 삼고,
parametric eyeliner curve와 authored style preset을 얹으면
실제 앱에서 조정 가능한 수준의 아이라인 후보를 만들 수 있는가?
```

## 3. 세션 배치

### 실험 세션

이 실험은 **현재 세션에서 진행**한다.

이유:

- 이 세션이 이미 lip, cheek, brow, eye, eyeliner 후보 비교 맥락을 가지고 있다.
- 기존 evidence와 실패 원인을 바로 재사용할 수 있다.
- 실험 결과가 앱 구현 scope를 결정하므로, 구현 전에 같은 맥락에서 결론을 내리는 편이 빠르다.

### 앱 구현 세션

실험 보고서, `selected_policy.json`, `adjustment_axes.json`, contact sheet를 남기고 checkpoint commit을 만든 뒤, 앱 구현은 **새 goal 또는 새 세션**으로 넘긴다.

구현 세션의 시작 조건:

```txt
eyeliner selected policy 존재
candidate contact sheet 존재
eye crop contact sheet 존재
reject 후보와 이유 기록
app adjustment axes 확정
Unity/RN handoff notes 존재
```

## 4. 완료 정의

이번 실험은 아래가 모두 있어야 완료다.

```txt
1. MediaPipe landmark 기반 아이라인 후보 6개 이상 생성
2. 기존 eye-prior minimal-safe 후보와 side-by-side 비교
3. full-frame contact sheet 생성
4. eye crop contact sheet 생성
5. hard mask / soft alpha / overlay 생성
6. UV projection 또는 projection 가능성 체크
7. scorecard.json 생성
8. selected_policy.json 생성
9. adjustment_axes.json 생성
10. 한국어 실험 보고서 생성
11. 앱 구현 handoff section 작성
12. checkpoint commit
```

이 실험은 buildless 실험이다. iPhone runtime Green, product-quality-ready, blink/yaw 안정성 완료를 주장하지 않는다.

## 5. Non-scope

이번 실험에서 하지 않는다.

```txt
Xcode build
iPhone install/run
실기기 AR runtime claim
live per-frame face parsing
외부 업로드
장기 raw frame 저장
상용 SDK 도입
Android 대응
```

## 6. 입력 데이터

### Primary input

```txt
evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/frame.png
evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/mediapipe_face_landmarks.json
```

이 입력은 현재 가장 중요한 기준이다.

이유:

- MediaPipe landmark가 `available` 상태다.
- `landmarkCount=478`이다.
- coordinate space가 `frame_image_pixel_top_left`로 기록되어 있다.
- 같은 pair에 Vision, parsing, ARFace, color 비교 evidence가 있다.

### Baseline candidates

```txt
evidence/e7-region-generate/session-20260626T195853Z/regions/eyeliner/
```

기존 후보는 최종 후보가 아니라 **baseline**으로 둔다.

비교 대상:

```txt
eyeliner-minimal-safe-lashline-v0
eyeliner-balanced-lashline-v0
eyeliner-safe-lashline-v0
```

### Helper references

```txt
evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/mediapipe/eye_overlay.png
evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/parsing/eye_overlay.png
evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/vision/eye_overlay.png
evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/arface/eye_overlay.png
```

역할:

- MediaPipe: primary geometry
- Vision: cross-check
- Face parsing: semantic silver reference
- ARFace: runtime surface / UV substrate reference
- Color/edge: optional snap confidence only

## 7. 핵심 가설

### H1. MediaPipe upper eyelid curve가 primary 기준선이어야 한다

아이라인은 얇은 선이라 broad eye mask만으로는 부족하다. eye opening 전체를 잡는 것보다, upper eyelid contour에서 시작해야 한다.

### H2. 예쁜 모양은 tracking이 아니라 style preset 문제다

MediaPipe는 위치를 잘 준다. 하지만 "예쁜 아이라인 모양"은 landmark에서 자동으로 나오지 않는다. 따라서 tracking과 shape를 분리한다.

```txt
tracking: MediaPipe upper eyelid landmarks
shape: parametric curve + authored style preset
runtime surface: ARFace UV
adjustment: slider + quick buttons
```

### H3. wing/full-line보다 tail-only fallback이 제품적으로 중요하다

눈 안쪽까지 선을 다 긋는 후보는 조금만 틀려도 어색하다. 반대로 바깥쪽 tail-only 또는 soft lashline은 실패해도 덜 티 나고, 사용자가 조정하기 쉽다.

### H4. 외부 asset은 texture가 아니라 shape prior로 써야 한다

외부 아이라인 asset을 그대로 붙이면 사람 눈에 맞지 않아 sticker처럼 보일 수 있다. 대신 asset에서 curve profile, taper, tail angle 같은 style 값을 추출해 MediaPipe 기준선에 재생성한다.

## 8. 후보군

최소 6개, 가능하면 8개를 생성한다.

### C1. `mp-upper-minimal`

가장 보수적인 후보.

```txt
source: MediaPipe upper eyelid arc
innerStart: 0.18
outerReach: 0.98
tailLength: 0.00-0.03 eyeWidth
lineThickness: thin
softness: medium
```

목표:

- 눈동자 침범 최소화
- 앱 기본값 후보 가능성 확인

### C2. `mp-upper-balanced`

일반 사용자를 위한 기본 후보.

```txt
source: MediaPipe upper eyelid arc
innerStart: 0.10
outerReach: 1.03
tailLength: 0.05-0.08 eyeWidth
lineThickness: medium
softness: medium
```

목표:

- 너무 약하지 않으면서 자연스러운 line
- 기존 minimal-safe보다 화장처럼 보이는지 확인

### C3. `mp-wing-soft`

눈꼬리 wing 후보.

```txt
source: MediaPipe upper eyelid arc + outer corner tangent
innerStart: 0.12
outerReach: 1.05
tailLength: 0.10-0.16 eyeWidth
tailAngle: user-adjustable
lineThickness: medium
taper: strong
```

목표:

- wing style 구현 가능성 확인
- 실패하면 default가 아니라 style preset으로 downgrade

### C4. `mp-tail-only`

바깥쪽만 그리는 안전 후보.

```txt
source: outer 35-45% of upper eyelid arc
innerStart: 0.55-0.65
outerReach: 1.08
tailLength: 0.06-0.12 eyeWidth
lineThickness: medium
softness: medium-high
```

목표:

- 눈 안쪽 spill 회피
- 홑꺼풀/눈두덩이/안쪽 경계 불안정 fallback

### C5. `mp-soft-lashline-shadow`

선이 아니라 속눈썹 라인 강조에 가까운 후보.

```txt
source: MediaPipe upper eyelid arc
lineThickness: low-medium
softness: high
opacityHint: lower
tailLength: 0.03-0.06 eyeWidth
```

목표:

- strict line이 실패할 때 제품적으로 덜 어색한 fallback
- 실제 앱에서 "자연스럽게" preset 후보

### C6. `mp-edge-snap-hybrid`

MediaPipe 곡선을 기본으로 하되 local dark edge에 미세 보정한다.

```txt
source: MediaPipe upper eyelid arc
snapSource: local dark/edge confidence
snapRadius: small
snapAllowedOnlyWhenConfidenceHigh: true
```

목표:

- 속눈썹/눈꺼풀 실제 경계에 더 붙는지 확인
- 색 기반이 primary가 되지 않도록 제한

### C7. `asset-fit-natural`

외부 또는 repo-local authored asset에서 natural eyeliner curve를 추출한 후보.

```txt
source: authored style curve
fit: inner corner, outer corner, upper eyelid curve
warp: piecewise affine or Bezier reparameterization
tailLength: short
taper: strong
```

목표:

- 예쁜 모양을 landmark만으로 만들기 어려운 경우의 돌파구
- runtime에서는 asset 이미지가 아니라 generated mask로 사용

### C8. `asset-fit-wing`

외부 또는 authored wing style 후보.

```txt
source: authored wing style
fit: outer corner tangent + eye width scale
tailLength: medium
tailAngle: adjustable
```

목표:

- wing preset 가능성 확인
- 실패하면 앱 v1에서는 숨기고 future preset으로 둠

## 9. 생성 알고리즘

### 9.1 MediaPipe eye landmark 추출

입력:

```txt
mediapipe_face_landmarks.json
```

해야 할 일:

```txt
left/right eye landmark set 분리
upper eyelid arc 추출
inner corner / outer corner 추출
eye opening polygon 추출
face yaw 추정 가능하면 기록
```

기존 `scripts/e7_region_detection_compare/`의 eye index 상수를 우선 재사용한다. index 신뢰가 애매하면 overlay를 생성해서 즉시 눈 crop에서 확인한다.

### 9.2 Curve 모델

아이라인 중심선은 polyline을 그대로 쓰지 않고 smooth curve로 만든다.

```txt
upper eyelid points
-> sort along eye horizontal axis
-> smooth
-> cubic Bezier or Catmull-Rom-like curve
-> normal direction offset
-> thickness profile 적용
-> tail endpoint 추가
```

### 9.3 Thickness profile

라인 두께는 균일하면 어색하다.

권장 profile:

```txt
inner: thin
middle: medium
outer: medium-thick
tail tip: taper to zero
```

### 9.4 Eye opening exclude zone

가장 중요한 safety gate다.

```txt
candidateMask = candidateMask - dilatedEyeOpeningMask
```

다만 너무 많이 빼면 라인이 끊기므로, 최소 2종을 비교한다.

```txt
excludeStrict
excludeSoft
```

### 9.5 UV projection

가능하면 기존 region generate pipeline의 UV projection 경로를 재사용한다.

목적:

- 앱/Unity handoff 가능성 확인
- same-frame round-trip에서 선이 완전히 깨지는지 확인

주의:

- 얇은 선은 round-trip IoU가 낮게 나올 수 있다.
- IoU만으로 reject하지 않는다.
- centerline preservation과 visual crop을 함께 본다.

## 10. Scoring

### 10.1 Hard reject

아래 하나라도 심하면 reject다.

```txt
empty mask
wrong side / mirrored
eye opening 또는 eyeball 침범 심함
눈썹 방향으로 올라감
눈 아래로 내려감
outer corner와 tail 시작점이 떨어짐
좌우 중 한쪽만 생성됨
source lineage 없음
privacy flag 없음
```

### 10.2 Quant metrics

`scorecard.json`에 반드시 남긴다.

```txt
candidateId
sourceSignals
maskPixels
bbox
leftRightAreaRatio
eyeOpeningOverlapPixels
eyeOpeningOverlapRatio
upperLidMeanDistancePx
upperLidP95DistancePx
tailStartDistanceFromOuterCornerPx
lineContinuityScore
smoothnessScore
uvRoundTripIoU
uvRoundTripCenterlineDistancePx
warnings
```

### 10.3 Visual review

숫자보다 crop이 중요하다.

필수 contact sheet:

```txt
full_frame_contact_sheet.png
eye_crop_contact_sheet.png
left_eye_crop_contact_sheet.png
right_eye_crop_contact_sheet.png
uv_round_trip_contact_sheet.png
```

눈 crop은 최소 아래 정보를 같이 보여준다.

```txt
original
candidate overlay
eye opening exclude zone
upper eyelid centerline
tail endpoint
```

## 11. 사용자 조정 설계

아이라인은 길고 tricky하므로 slider만으로는 부족하다. v1은 **slider + quick buttons**로 간다.

### 11.1 Slider axes

```txt
lineHeight
lineThickness
innerStart
outerReach
tailLength
tailAngle
tailLift
taper
softness
leftRightBalance
```

기존 `upperLineOffset`, `lineThickness`, `tailLength`, `tailAngle`, `outerCornerReach`, `innerCornerStart`, `softness`, `blinkFade`는 유지하되 앱 용어를 더 사용자 친화적으로 mapping한다.

권장 mapping:

```txt
lineHeight -> upperLineOffset
lineThickness -> lineThickness
innerStart -> innerCornerStart
outerReach -> outerCornerReach
tailLength -> tailLength
tailAngle + tailLift -> tailAngle
softness -> softness
blinkFade -> runtime/deferred safety assist
```

### 11.2 Quick buttons

```txt
얇게
조금 위로
조금 아래로
안쪽 비우기
꼬리 짧게
꼬리 올리기
바깥쪽만
좌우 맞추기
왼쪽만 조정
오른쪽만 조정
```

### 11.3 기본 UX 원칙

```txt
처음부터 화려한 wing을 보여주지 않는다.
기본값은 natural/minimal이어야 한다.
사용자가 직접 wing을 늘리게 한다.
눈동자나 눈 안쪽을 침범하면 warning을 띄운다.
좌우가 다르면 mirror-copy 버튼을 제공한다.
```

## 12. 멀티 에이전트 운영

이번 실험은 빠르게 끝내야 하므로 목적별로 에이전트를 나눈다.

### 12.1 Manager

책임:

```txt
목표 고정
timebox 관리
agent handoff
candidate 누락 방지
final selected policy 판정
checkpoint commit 지시
```

Manager는 아래 질문을 계속 확인한다.

```txt
이 후보가 앱 구현으로 이어질 수 있는가?
이 후보가 사람 눈 crop에서 납득 가능한가?
이 결과가 기존 eye-prior baseline보다 나은가?
실기기 검증 전 claim을 과장하고 있지 않은가?
```

### 12.2 Data Inventory Agent

책임:

```txt
input frame/landmark/overlay 경로 확인
기존 eyeliner baseline 수집
MediaPipe JSON schema 확인
external style asset 후보가 필요하면 source/license 기록
```

산출물:

```txt
input_inventory.json
source_review.md
external_asset_manifest.json
```

### 12.3 Geometry Agent

책임:

```txt
MediaPipe eye landmark index 검증
upper eyelid arc 추출
eye opening exclude zone 생성
inner/outer corner 확인
left/right orientation 오류 탐지
```

산출물:

```txt
eyelid_geometry_debug.json
eyelid_landmark_overlay.png
eye_opening_exclude_overlay.png
```

### 12.4 Candidate Generator Agent

책임:

```txt
6-8개 후보 생성
hard mask / soft alpha / overlay 저장
candidate trace 기록
style preset parameter 저장
```

산출물:

```txt
candidates/*.mask.png
candidates/*.alpha.png
candidates/*.overlay.png
candidates/*.trace.json
candidate_registry.json
```

### 12.5 Scoring Agent

책임:

```txt
eye opening overlap 측정
upper lid distance 측정
tail start distance 측정
좌우 면적/길이 비교
continuity/smoothness 평가
UV projection metric 기록
```

산출물:

```txt
scorecard.json
scorecard.md
metric_notes.md
```

### 12.6 Designer / UX Agent

책임:

```txt
사용자 조정축 확정
slider + quick button 설계
natural / tail-only / wing preset naming
앱에서 처음 보여줄 default 후보 선택 비평
```

산출물:

```txt
adjustment_axes.json
eyeliner_adjustment_controls.md
app_handoff_ui_notes.md
```

### 12.7 Strict QA Agent

책임:

```txt
과장 claim 차단
missing artifact 체크
privacy/local-only 체크
baseline 대비 개선 여부 확인
reject rule 적용
```

Stop authority:

```txt
MediaPipe 기반이라고 쓰였지만 실제 landmark를 안 쓰면 중단
eye opening overlap이 심한 후보를 selected로 올리면 중단
contact sheet 없이 완료 선언하면 중단
iPhone Green/product-quality-ready 주장하면 중단
외부 asset license/source 없이 사용하면 중단
```

산출물:

```txt
qa_gate_matrix.json
qa_review.md
missing_evidence_list.md
```

### 12.8 Wildcard Agent

소환 조건:

```txt
MediaPipe landmark 추출이 2회 이상 실패
upper eyelid index가 불확실
모든 generated 후보가 눈 crop에서 어색함
asset prior 없이는 wing이 해결되지 않음
```

역할:

```txt
repo 안 숨은 eye/eyeliner asset 탐색
외부 open/license-safe eyeliner vector 탐색
논문/오픈소스 예시 조사
Bezier/style preset 대안 제시
```

### 12.9 Claude External Critic

Claude는 구현자가 아니라 외부 비평가다.

호출 시점:

```txt
1차 후보 contact sheet 생성 직후
selected policy 확정 직전
```

넘길 context:

```txt
목표: MediaPipe 기반 아이라인 후보 최종 선택
입력: frame, landmarks, baseline 후보, candidate contact sheet
제약: local-only, buildless, no iPhone runtime claim
질문:
  - 어떤 후보가 앱 default로 가장 안전한가?
  - wing/tail-only 중 어떤 fallback이 제품적으로 낫나?
  - 사용자 조정축에서 빠진 것은 무엇인가?
  - 과장 claim 또는 missing evidence는 무엇인가?
```

## 13. 시간표

총 90-150분으로 끝낸다.

### T+00 - T+10: Contract lock

```txt
읽기: AGENTS.md, TECH_VALIDATION_RESULT.md snapshot, active roadmap eyeliner section
입력 경로 확정
output root 생성
baseline 후보 inventory 작성
```

### T+10 - T+30: Geometry extraction

```txt
MediaPipe JSON parse
upper eyelid arc 생성
eye opening exclude mask 생성
landmark overlay 생성
left/right orientation 확인
```

### T+30 - T+65: Candidate generation

```txt
mp-upper-minimal
mp-upper-balanced
mp-wing-soft
mp-tail-only
mp-soft-lashline-shadow
mp-edge-snap-hybrid
asset-fit-natural if asset/source ready
asset-fit-wing if asset/source ready
```

### T+65 - T+95: Score and contact sheets

```txt
metric scorecard 생성
full-frame contact sheet
eye crop contact sheet
UV round-trip sheet
baseline vs new candidate 비교
```

### T+95 - T+120: Refine loop

```txt
상위 2개 후보만 refine
eye opening spill 감소
tail 시작점 보정
innerStart/outerReach/taper 조정
```

### T+120 - T+140: Decision

```txt
selected policy 결정
fallback policy 결정
adjustment axes 확정
app implementation handoff 작성
```

### T+140 - T+150: QA and checkpoint

```txt
Strict QA gate 통과
report 링크 확인
TECH_VALIDATION_RESULT.md 반영 여부 판단
checkpoint commit
```

## 14. Output root

권장 output root:

```txt
evidence/e7-eyeliner-candidate-experiment/experiment-YYYYMMDDTHHMMSSZ/
```

필수 구조:

```txt
input_inventory.json
source_review.md
geometry/
  eyelid_landmark_overlay.png
  eye_opening_exclude_overlay.png
  eyelid_geometry_debug.json
candidates/
  *.mask.png
  *.alpha.png
  *.overlay.png
  *.trace.json
uv_projection/
  *.uv_probability.png
  *.round_trip_overlay.png
contact_sheets/
  full_frame_contact_sheet.png
  eye_crop_contact_sheet.png
  left_eye_crop_contact_sheet.png
  right_eye_crop_contact_sheet.png
scorecard.json
scorecard.md
selected_policy.json
adjustment_axes.json
qa_review.md
summary.md
```

보고서 위치:

```txt
docs/product/e7-eyeliner-candidate-experiment-report-YYYY-MM-DD/README.md
```

## 15. Decision ladder

### A. Best path

```txt
selected: mp-upper-balanced or mp-upper-minimal
fallback: mp-tail-only
stylePreset: natural
app default: selected candidate
```

조건:

```txt
eye opening overlap 낮음
crop에서 자연스러움
tail이 outer corner에 붙음
UV projection에서 선이 유지됨
사용자 조정축으로 문제 해결 가능
```

### B. Hybrid path

```txt
selected: mp-edge-snap-hybrid
fallback: mp-upper-minimal
```

조건:

```txt
순수 MediaPipe line이 실제 lashline보다 떠 보임
edge snap이 안정적으로 경계에 붙음
색/edge가 primary가 아니라 small correction으로만 동작
```

### C. Safe fallback path

```txt
selected: mp-tail-only or mp-soft-lashline-shadow
fallback: no-wing minimal line
```

조건:

```txt
full-line이 눈 안쪽에서 자주 깨짐
wing 후보가 어색함
tail-only는 자연스럽고 조정 가능함
```

### D. Asset prior path

```txt
selected: asset-fit-natural
fallback: mp-upper-minimal
```

조건:

```txt
MediaPipe 기준선은 맞지만 모양이 계속 어색함
authored style curve가 crop에서 확실히 낫다
asset source/license/lineage가 기록됨
runtime에는 generated mask로만 들어간다
```

### E. Blocked

blocked는 마지막 선택지다.

조건:

```txt
MediaPipe landmark가 없거나 좌표가 틀림
모든 후보가 eye opening을 심하게 침범
contact sheet에서 사용자에게 보여줄 수 있는 후보가 없음
external asset도 source/license 문제로 사용 불가
```

blocked가 되면 반드시 아래를 남긴다.

```txt
blocked reason
repro command
failed candidate images
next unblock action
```

## 16. 앱 구현 handoff

실험이 성공하면 구현 세션은 아래 결론으로 시작한다.

```txt
lip: 기존 성공 흐름 유지
cheek: 팀원 UV mask + 사용자 위치/크기 조정
brow: MediaPipe landmark
eyeliner: MediaPipe upper eyelid + parametric style preset + 사용자 조정
runtime substrate: ARFace UV
face parsing/color: helper/evaluation only
```

앱 구현에 넘길 파일:

```txt
selected_policy.json
adjustment_axes.json
candidate_registry.json
scorecard.json
eye_crop_contact_sheet.png
app_handoff_ui_notes.md
```

RN/Unity 구현 주의:

```txt
아이라인은 line texture가 얇으므로 UV 해상도/feather 문제를 별도 체크한다.
기본값은 natural/minimal로 둔다.
wing은 preset 또는 사용자 확장으로 둔다.
blink/yaw 안정성은 phone-connected session에서 따로 본다.
saved package가 runtime proof는 아니다.
```

## 17. 즉시 실행 프롬프트

아래 프롬프트로 goal을 시작하면 된다.

```txt
목표: E7 아이라인 마스크 후보 최종 실험을 buildless/local-only로 완료한다.

계약:
- AGENTS.md, TECH_VALIDATION_RESULT.md Current Session Snapshot, docs/roadmaps/README.md, active E7 full-face plan을 먼저 읽는다.
- 이번 실험 문서 docs/roadmaps/research/E7_EYELINER_MASK_CANDIDATE_FINAL_EXPERIMENT_PLAN_KO.md를 실행 계약으로 사용한다.
- Xcode/iPhone build/install/run은 하지 않는다.
- raw frame/upload/장기 저장 금지. 기존 local evidence만 사용하고 새 산출물은 evidence 아래에 정리한다.

해야 할 일:
1. pair_face_20260627T091334Z_06의 frame과 mediapipe_face_landmarks.json을 primary input으로 사용한다.
2. 기존 eyeliner-minimal-safe/balanced/safe 후보는 baseline으로만 둔다.
3. MediaPipe upper eyelid landmark 기반 후보를 최소 6개 생성한다.
4. full-frame, eye crop, left/right crop, UV round-trip contact sheet를 만든다.
5. eye opening overlap, upper lid distance, tail start distance, continuity, left/right balance, UV round-trip metric을 scorecard에 기록한다.
6. selected_policy.json, adjustment_axes.json, app_handoff_ui_notes.md를 만든다.
7. Strict QA가 과장 claim, missing artifact, source lineage, privacy flag, eye opening spill을 검사한다.
8. 한국어 보고서를 작성하고 링크를 남긴다.
9. 주요 체크포인트마다 자동 커밋한다.

완료 조건:
- 앱 구현 세션이 바로 시작할 수 있을 만큼 아이라인 selected policy와 조정축이 확정되어야 한다.
- 성공하지 못하면 blocked reason, 실패 이미지, 다음 unblock action을 남긴다.
```

## 18. 최종 원칙

이번 실험의 목적은 멋진 demo 한 장을 만드는 것이 아니다.

목적은 앱 구현에 필요한 결정을 닫는 것이다.

```txt
어떤 신호로 잡을지
어떤 후보를 기본값으로 할지
어떤 후보를 fallback으로 둘지
사용자가 어떤 축으로 조정할지
어떤 한계를 phone-connected session으로 넘길지
```

이 다섯 가지가 닫히면, 아이라인 실험은 성공이다.
