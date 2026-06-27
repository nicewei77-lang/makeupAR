# E7 아이라인 Anchor-to-Band 대량 샘플 실험 계획

상태: 실행 전 계획  
작성일: 2026-06-27 KST  
범위: buildless/local-only, 앱 구현 직전 30-60분 추가 실험  
상위 계약: `docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md`  
직전 결과: `docs/product/e7-eyeliner-candidate-experiment-report-2026-06-27/README.md`

## 1. 한 줄 목표

사용자가 가장 좋은 레퍼런스로 지정한 `Cat / Puppy / Sexy / Winged / Colored / Doll` 예시를 기준으로, **MediaPipe upper eyelid anchor를 실제 아이라인 band로 확장한 후보 이미지를 대량 생성**하고 사용자가 직접 고를 수 있는 contact sheet와 한글 보고서를 만든다.

## 2. 왜 이 실험이 필요한가

직전 실험의 결론은 아래처럼 정리됐다.

```txt
tracking/reference anchor: mp-upper-balanced-v0
selected visual direction: asset-fit-wing-local-style-v0
fallback: mp-tail-only-v0
runtime substrate: ARFace UV
```

하지만 아직 남은 질문이 있다.

```txt
MediaPipe upper eyelid anchor는 잘 잡혔다.
그 anchor를 실제 예쁜 아이라인 band로 만들 때
어느 두께, 어느 inner start, 어느 tail length, 어느 tail angle이 가장 좋은가?
```

따라서 이번 실험은 새로운 tracker 탐색이 아니다. 이미 정한 anchor를 기준으로 shape만 대량 탐색한다.

```txt
anchor-to-band = upper eyelid 기준선 -> 두께가 있는 아이라인 면 -> 눈꼬리 채움 -> wing tail -> soft alpha
```

## 3. 시간 박스

목표 시간은 30-60분이다.

| 시간 | 작업 | 산출물 |
| ---: | --- | --- |
| 0-5분 | 입력/계약 freeze | input manifest |
| 5-15분 | anchor-to-band 파라미터 grid 생성 | candidate grid JSON |
| 15-30분 | 후보 100-180개 생성 | masks, overlays, eye crops |
| 30-40분 | 자동 reject/score/filter | scorecard, reject sheet |
| 40-50분 | 사용자 선택용 contact sheet 구성 | family sheets, top sheet |
| 50-60분 | 한글 보고서/아티팩트/커밋 | report, pending-user-pick policy |

60분 안에 끝나야 한다. 완벽한 자동 scoring보다, 사용자가 빠르게 고를 수 있는 넓은 샘플 공간이 우선이다.

## 4. 입력

### Primary face input

```txt
evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/frame.png
evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/mediapipe_face_landmarks.json
evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/arface_export.json
```

역할:

- `frame.png`: 후보를 실제 얼굴 위에 그려볼 기준 이미지
- `mediapipe_face_landmarks.json`: upper eyelid anchor 추출
- `arface_export.json`: UV round-trip 또는 runtime substrate sanity check

### Best visual reference

사용자가 가장 좋은 예시로 지정한 레퍼런스:

```txt
/tmp/codex-remote-attachments/019f0551-bf7f-7ee1-8fbb-e023dd51f124/017A56B8-DB3B-4D83-823A-BFE9AB4928F2/1-사진-1.jpg
```

주의:

- 이 이미지는 style taxonomy 참고용이다.
- 출처/라이선스가 확정되지 않았으므로 repo asset, runtime texture, 학습 데이터로 사용하지 않는다.
- 눈 모양을 그대로 복사하지 않고, `Cat / Puppy / Sexy / Winged / Colored / Doll`의 shape parameter만 우리 frame에 재생성한다.

## 5. 핵심 가설

### H1. 최종 제품 후보는 line이 아니라 band여야 한다

이전 `mp-upper-balanced-v0`는 깔끔하지만 line anchor에 가깝다. 제품 아이라인은 속눈썹 위를 따라가는 선에서 끝나지 않고, 바깥쪽 눈꼬리와 wing tail까지 작은 면으로 채워져야 한다.

### H2. 좋은 예시의 공통점은 outer corner fill이다

사용자 피드백의 핵심은 "눈꼬리까지 채워야 한다"이다. 따라서 이번 grid는 `outerCornerFill`을 1급 파라미터로 둔다.

### H3. 실패를 막는 가드는 full-lid block / closed ring 금지다

실패 레퍼런스는 두 가지다.

```txt
1. 눈두덩 전체를 검게 덮는 block fill
2. 위아래를 두껍게 닫는 closed ring
```

이번 실험의 후보 생성기는 아래를 기본 reject로 둔다.

```txt
maxLidFillHeight 초과
lowerLidCoverage 기본값 초과
inner corner 과다 채움
tail bluntness 과다
```

### H4. 최종 선택은 사람이 한다

자동 score는 정렬과 reject에만 사용한다. 아이라인은 취향과 눈 모양 의존성이 크므로 최종 선택은 contact sheet를 보고 사람이 한다.

## 6. 멀티 에이전트 역할

### Manager

- 전체 시간 박스 관리
- 입력/출력 위치 고정
- 중간 checkpoint와 최종 commit 관리
- 결과를 `pending_user_visual_pick` 상태로 정리

### Geometry Agent

- MediaPipe left/right upper eyelid anchor 추출
- inner corner, outer corner, eye width, eye height 계산
- forbidden eye-opening zone 생성
- 좌우 눈 crop 정규화
- `mp-upper-balanced-v0`를 reference anchor로 재사용

### Style Grid Agent

- best reference의 6개 style family를 parameter preset으로 변환
- 각 family에서 12-30개 후보를 생성
- 총 100-180개 후보를 목표로 한다
- 후보 ID를 사람이 고르기 쉽게 만든다

예시 ID:

```txt
cat-i18-t06-o14-a12-s30-v003
winged-i22-t07-o20-a21-s25-v014
doll-i28-t05-o10-a08-s45-v006
```

### Renderer Agent

- hard mask 생성
- soft alpha 생성
- full-frame overlay 생성
- left/right eye crop 생성
- family별 contact sheet 생성
- top 후보 contact sheet 생성
- rejected 후보 sheet 생성

### Scoring Agent

자동 지표를 계산한다.

```txt
eyeOpeningOverlap
upperLidMeanDistance
outerCornerGap
outerCornerFillScore
tailTaperScore
tailAngleScore
lidFillHeightRatio
lowerLidCoverageRatio
leftRightBalance
componentCount
uvRoundTripIoU
```

score는 최종 판단이 아니라 review order를 정하는 데만 쓴다.

### Strict QA Agent

- 외부 레퍼런스 이미지를 repo asset으로 커밋하지 않았는지 확인
- raw/cache/generated 대량 파일이 잘못 stage되지 않았는지 확인
- report 이미지가 너무 크거나 깨지지 않는지 확인
- JSON이 parse 가능한지 확인
- iPhone runtime Green을 주장하지 않았는지 확인

### Product Handoff Agent

사용자가 고른 후보가 바로 앱 구현으로 넘어가도록 아래를 만든다.

```txt
selected_policy_pending_user.json
candidate_grid.json
adjustment_axes_candidates.json
app_handoff_notes.md
```

사용자 선택 후에는 `selected_policy.json`으로 승격한다.

### Wildcard Agent

아래 상황에서만 소환한다.

```txt
MediaPipe anchor가 깨짐
band가 계속 눈 안쪽으로 침범
tail이 좌우 대칭으로 생성되지 않음
contact sheet가 판단하기 어렵게 나옴
```

역할은 기존 report/evidence/디렉토리/외부 공개 자료를 뒤져서 우회 파라미터나 더 좋은 shape prior를 제안하는 것이다.

## 7. 후보 family

사용자가 지정한 최고 레퍼런스의 6개 family를 그대로 실험 family로 둔다.

### F1. Cat

느낌:

```txt
sharp, lifted, outer-focused
```

기본 방향:

```txt
innerStart: 0.18-0.28
lineThickness: medium
tailLength: medium-long
tailAngle: upward
outerCornerFill: strong
softness: low-medium
```

### F2. Puppy

느낌:

```txt
soft, slightly lowered, rounded
```

기본 방향:

```txt
innerStart: 0.18-0.32
lineThickness: thin-medium
tailLength: short-medium
tailAngle: flat or slightly downward
outerCornerFill: medium
softness: medium-high
```

### F3. Sexy

느낌:

```txt
longer, smoky, outer third emphasized
```

기본 방향:

```txt
innerStart: 0.10-0.22
lineThickness: medium-thick outer third
tailLength: long
tailAngle: flat-upward
outerCornerFill: strong
softness: medium-high
```

### F4. Winged

느낌:

```txt
clean default wing
```

기본 방향:

```txt
innerStart: 0.18-0.28
lineThickness: medium
tailLength: medium-long
tailAngle: upward
outerCornerFill: required
softness: medium
```

현재 앱 기본 후보는 이 family에서 나올 가능성이 가장 높다.

### F5. Colored

느낌:

```txt
shape is soft wing, rendering tint can vary
```

이번 실험에서는 색 자체보다 shape를 본다. contact sheet는 판단 편의를 위해 tint preview를 추가할 수 있지만, mask 선택은 geometry 기준으로 한다.

기본 방향:

```txt
innerStart: 0.18-0.30
lineThickness: thin-medium
tailLength: medium
tailAngle: soft upward
outerCornerFill: medium
softness: high
```

### F6. Doll

느낌:

```txt
rounder, shorter, cute, less sharp
```

기본 방향:

```txt
innerStart: 0.22-0.35
lineThickness: thin-medium
tailLength: short
tailAngle: flat or mildly upward
outerCornerFill: low-medium
softness: high
```

## 8. 대량 샘플 grid

목표 후보 수:

```txt
minimum: 96
target: 144
maximum: 180
```

Family별 기본 생성량:

| Family | 후보 수 |
| --- | ---: |
| Cat | 24 |
| Puppy | 18 |
| Sexy | 24 |
| Winged | 30 |
| Colored | 18 |
| Doll | 18 |
| Balanced reference | 6 |
| Tail-only safe | 6 |
| 합계 | 144 |

공통 파라미터:

```txt
innerStart: 0.10 / 0.18 / 0.22 / 0.28 / 0.35
lineThicknessPx: 4.0 / 5.5 / 7.0 / 8.5
outerCornerFill: 0.10 / 0.16 / 0.22 / 0.28
tailLengthEyeWidth: 0.08 / 0.14 / 0.20 / 0.26
tailAngleDeg: family-dependent
tailLiftPx: family-dependent
taper: 0.8 / 1.1 / 1.4
softnessPx: 2.0 / 3.2 / 4.5
opacityPreview: 0.45 / 0.65 / 0.85
```

모든 조합을 cartesian product로 폭발시키지 않는다. family별로 의미 있는 조합만 고르는 stratified grid를 쓴다.

## 9. 생성 알고리즘

### Step A. Anchor

MediaPipe upper eyelid landmark를 좌우 눈별 curve로 만든다.

```txt
inner corner -> upper eyelid samples -> outer corner
```

curve는 smoothing spline 또는 polyline resampling으로 균일 샘플링한다.

### Step B. Band

curve의 normal 방향으로 두께를 만든다.

```txt
upper edge = anchor + normal * upperOffset
lower edge = anchor + normal * lowerOffset
```

단, lower edge가 eye opening forbidden zone을 침범하면 후보를 reject 또는 shrink한다.

### Step C. Outer corner fill

outer corner 주변은 단순 stroke가 아니라 작은 wedge/triangle/curved patch를 만든다.

```txt
outer fill patch = outer corner + upper band + tail base
```

이 부분이 레퍼런스의 "눈꼬리까지 채움"을 담당한다.

### Step D. Tail

outer corner tangent와 family별 angle/lift/length로 tail control point를 만든다.

```txt
tailStart = outer corner + small overlap
tailEnd = outer corner + tangent * tailLength + liftVector
```

tail 끝은 taper polygon 또는 alpha gradient로 마감한다.

### Step E. Soft Alpha

hard mask와 soft alpha를 둘 다 만든다.

```txt
hard mask: scoring/UV projection용
soft alpha: visual review/render preview용
```

## 10. 자동 reject 기준

아래는 사람이 보기 전에 제거하거나 `reject_sheet`로 따로 모은다.

```txt
eyeOpeningOverlapRatio > 0.03
lidFillHeightRatio > 0.18
lowerLidCoverageRatio > 0.02
outerCornerGapPx > 8
tailBluntnessScore > threshold
componentCount != 2
leftRightBalanceAbsDiff > 0.25
```

다만 자동 reject가 너무 공격적이면 후보를 완전히 버리지 않고 rejected sheet에 보여준다. 사용자가 의외로 좋아할 가능성은 낮지만, 왜 실패했는지 확인할 수 있게 한다.

## 11. 산출물

실험 output root:

```txt
evidence/e7-eyeliner-anchor-to-band-experiment/experiment-YYYYMMDDTHHMMSSZ/
```

필수 산출물:

```txt
candidate_grid.json
scorecard.json
shortlist.json
selected_policy_pending_user.json
adjustment_axes_candidates.json
app_handoff_notes.md
summary.md
```

이미지 산출물:

```txt
contact_sheet_all_small.png
contact_sheet_top_36.png
contact_sheet_family_cat.png
contact_sheet_family_puppy.png
contact_sheet_family_sexy.png
contact_sheet_family_winged.png
contact_sheet_family_colored.png
contact_sheet_family_doll.png
contact_sheet_balanced_tail_safe.png
contact_sheet_rejected.png
left_eye_contact_sheet_top_36.png
right_eye_contact_sheet_top_36.png
uv_round_trip_top_12.png
```

보고서 mirror:

```txt
docs/product/e7-eyeliner-anchor-to-band-experiment-report-2026-06-27/
```

보고서에는 사용자 선택을 위해 적당한 크기의 이미지를 넣는다.

```txt
1. 한 줄 결론
2. 왜 이 실험을 했는지
3. 가장 좋은 레퍼런스가 의미하는 형태 기준
4. family별 contact sheet
5. top 36 contact sheet
6. rejected sheet
7. 후보를 고르는 법
8. 후보 ID별 파라미터 표
9. 다음 앱 구현 handoff
10. 남은 한계
```

## 12. 사용자 선택 방식

사용자에게는 복잡한 metric이 아니라 candidate ID로 고르게 한다.

예:

```txt
1순위: winged-i22-t07-o20-a21-s32-v014
2순위: cat-i18-t06-o16-a18-s25-v009
싫은 후보: puppy 계열 전부, doll 너무 약함
수정 요청: 1순위에서 꼬리 10% 짧게, 두께 살짝 얇게
```

사용자 선택 후 후속 작업:

```txt
selected_policy_pending_user.json -> selected_policy.json
chosen candidate axes -> app default preset
nearby variants 12개 추가 생성 여부 결정
RN/Unity 구현으로 진입
```

## 13. 완료 판정

이번 실험의 완료 판정은 아래다.

```txt
status: pending_user_visual_pick
```

완료라는 뜻:

- 후보 이미지를 충분히 만들었다.
- 사용자가 고를 수 있는 보고서를 만들었다.
- 앱 구현에 필요한 후보 ID와 파라미터 구조를 고정했다.

아직 완료가 아닌 것:

- 사용자 최종 선택
- iPhone runtime visual acceptance
- blink/yaw/squint 안정성
- product-quality Green

## 14. 바로 실행할 goal 프롬프트 초안

```txt
E7 아이라인 anchor-to-band 대량 샘플 실험을 실행해줘. 목표는 앱 구현 전에 사용자가 직접 고를 수 있도록 MediaPipe upper eyelid anchor 기반 아이라인 band 후보를 100-180개 생성하는 것이다. 입력은 pair_face_20260627T091334Z_06의 frame, mediapipe_face_landmarks, arface_export를 사용하고, 사용자가 가장 좋은 예시로 지정한 Cat/Puppy/Sexy/Winged/Colored/Doll 레퍼런스는 shape taxonomy로만 참고한다. 외부 이미지는 repo asset/runtime asset으로 커밋하지 않는다.

후보 family는 Cat, Puppy, Sexy, Winged, Colored, Doll, Balanced reference, Tail-only safe로 나누고, innerStart, lineThickness, outerCornerFill, tailLength, tailAngle, taper, softness를 stratified grid로 바꿔 최소 96개, 목표 144개 후보를 생성해라. hard mask, soft alpha, full-frame overlay, left/right eye crop, family별 contact sheet, top 36 contact sheet, rejected sheet, UV round-trip top 12를 만들고, 자동 score/reject는 정렬 보조로만 사용해라.

최종 산출물은 보기 좋은 크기의 이미지가 들어간 한국어 실험 보고서와 candidate_grid.json, scorecard.json, shortlist.json, selected_policy_pending_user.json, adjustment_axes_candidates.json, app_handoff_notes.md다. 판정은 pending_user_visual_pick으로 두고, iPhone runtime Green이나 product-quality-ready를 주장하지 마라. 완료 후 필요한 파일만 checkpoint commit해라.
```
