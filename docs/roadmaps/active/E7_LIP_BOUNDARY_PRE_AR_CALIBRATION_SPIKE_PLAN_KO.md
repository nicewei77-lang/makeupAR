# E7 Lip-First Pre-AR Boundary Calibration Spike Plan

Last updated: 2026-06-26 KST

Status: Phase 0-3 prep bundle complete / Next implementation milestones are M1 buildless personalized lip package, M2 in-app pre-filter calibration slice, M3 runtime candidate sweep / M3A buildless candidate source-stage implemented but runtime untested / E7.3 remains Yellow

## 0. One-line Decision

이번 스파이크는 **AR 화면이 뜬 뒤 매 프레임 무거운 모델을 돌리는 방식이 아니라, AR 진입 전에 가능한 신호를 모두 모아 사용자별 lip boundary map을 만들고, runtime에서는 ARFace mesh/UV 위에서 가볍게 추적하는 구조**를 검증한다.

핵심 문장:

```txt
AR 전에 무겁게 분석한다.
AR 중에는 가볍게 붙인다.
고정 대상은 화면 픽셀이 아니라 ARFace UV/vertex 좌표다.
```

이번 문서는 이제 구현 지시서다. 바로 E7.3 Green, E7.4 cosmetic rendering, 제품 품질, AI/backend/upload, commercial SDK, Android, live face parsing runtime을 승인하지 않는다.

Completed prep bundle:

- Phase 0-3 documentation, schemas, signal priority, candidate ids, privacy rules, stop rules, and buildless stubs are complete enough to stop expanding preparation work.
- Existing stubs remain useful: `scripts/e7_lip_boundary_fusion/prepare_fusion_summary.py` and `scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py`.
- No real M1/M2-ready personalized lip package, Unity/iPhone build evidence, runtime visual evidence, Lip G/Y/R, or E7.3 Green decision exists yet. M3A may source-stage validation-only runtime candidate assets under the repo, but those remain `runtimeReady=false` until M3B.
- The next work is implementation, starting with M1 Buildless Personalized Lip Package v0.

Implementation map note:

- Phase 0-3 are now treated as one completed prep bundle, not as future work to keep extending.
- Future work uses only three implementation milestones:
  - M1 Buildless Personalized Lip Package v0.
  - M2 In-App Pre-Filter Calibration Slice.
  - M3 Runtime Candidate Sweep and Lip G/Y/R.
- M3 is split by execution environment: phone-disconnected overnight agents may only do M3A buildless prep; M3B runtime sweep / Lip G/Y/R requires build approval and a connected iPhone.
- Mesh-derived structural draft and `LipPresetProfile` move into M1 as implementation work, not as a separate research-only phase.
- Runtime tracking, RN validation UI, user adjustment, edge cases, evidence, and G/Y/R are absorbed into M2/M3. Do not create separate Phase 4-6 milestones unless a later result explicitly requires them.

## 1. 왜 이 문서가 필요한가

`E7 Lip Sample Pack v0` runtime review에서 확인된 문제는 tracking failure가 아니다.

확인된 좋은 점:

- iPhone camera feed가 뜬다.
- AR tracking과 ARFace mesh/UV가 살아 있다.
- lip overlay는 얼굴에 붙어 움직인다.
- RN -> Unity payload wiring과 material parameter 전달은 동작한다.
- 실기기 FPS는 대체로 60 근처로 보인다.

확인된 실패:

- 현재 `lip-smooth-mask-v1.png`는 실제 입술 contour보다 넓고 둥글다.
- `coverage`와 `feather`는 경계를 찾는 값이 아니라 이미 틀어진 mask를 자르거나 흐리는 값이다.
- 입술 산, 입꼬리, upper/lower lip 두께, open-mouth inner hole, smile/pucker 변형을 제대로 따라가지 못한다.
- gloss/texture 품질을 올려도 경계가 틀리면 "화장"이 아니라 "입 주변 반투명 색"으로 보인다.

따라서 다음 우선순위는 sample 값을 더 늘리는 것이 아니라:

```txt
lip boundary model
-> pre-AR calibration
-> ARFace UV/vertex fixed runtime map
-> lightweight expression correction
-> 그 다음 lip renderer / sample 재평가
```

## 2. Current Repo State

현재 작업은 기존 E7.03 / E7.3 boundary contract 아래에 있다.

현재 유지해야 할 것:

- E7.3 Region Precision은 Yellow overall이며 E7.4로 자동 진입하지 않는다.
- `lip`, `cheek`, `eye`는 전체 E7.03의 in-scope region이지만, 이 문서는 `lip-first`로 깊게 다룬다.
- `cheek` / `eye`는 같은 calibration architecture가 확장될 수 있게 slot만 남긴다.
- 기존 `rendererMode="smooth-region-mask"` 경로는 보존한다.
- 기존 3-layer payload shape는 보존한다.
- `lip_daily`, `lip_gloss`, `lip_texture`는 wiring evidence로 유지한다.
- 기존 `lip-smooth-mask-v1.png`는 broad baseline으로 남긴다.
- 기존 E3/E4 baseline, RN -> Unity recipe dispatch, Unity -> RN evidence fields는 보존한다.

현재 조심해야 할 것:

- `lip-smooth-mask-v1.png`를 product-quality lip mask처럼 부르지 않는다.
- current smooth mask cleanup acceptance를 E7.3 Green으로 승격하지 않는다.
- face parsing output을 runtime product asset 또는 release asset source로 취급하지 않는다.
- Apple Vision, MediaPipe, Core ML, face parsing을 live runtime dependency로 바로 넣지 않는다.

## 3. Scope

### In scope

- `lip` boundary만 깊게 설계한다.
- Pre-AR calibration UX와 data contract.
- ARFace screen mask -> UV/vertex projection flow.
- Apple Vision lip contour의 required pre-filter calibration 역할.
- Face parsing lip/skin/mouth labels의 required pre-filter silver 역할.
- Color/gradient confidence required pre-filter signal.
- User adjustment confirmation required for M1 ready.
- Failure-mode taxonomy는 boundary 품질이 1차 목표에 도달한 뒤 future eval/held-out 기록으로 deferred.
- Runtime lightweight tracking model.
- Evidence, scoring, G/Y/R criteria.
- 다음 구현 세션 prompt.

### Extension slots only

- `cheek`: future soft-zone calibration extension.
- `eye`: future broad eyeshadow/eye tint calibration extension.

이 문서에서는 cheek/eye의 detailed algorithm을 구현하지 않는다.

### Out of scope

- E7.4 cosmetic renderer implementation.
- E7.5 demo look implementation.
- E7.6 performance final decision.
- Product-v1 readiness.
- AI recommendation, backend upload, user profile sync, raw frame storage.
- Commercial beauty SDK integration.
- Android/ARCore.
- Live per-frame face parsing or Core ML inference.
- Demographic classification.
- Free-draw product onboarding UI.

## 4. Architecture Summary

### Beginner mental model

```txt
처음에 사용자의 입술 스티커를 맞춤 제작한다.
그 스티커를 화면 픽셀에 붙이는 것이 아니라 얼굴 3D mesh의 UV/vertex에 붙인다.
그 다음부터는 ARFace mesh가 움직일 때 스티커도 같이 따라간다.
입을 벌리거나 웃을 때는 가벼운 표정 신호로 조금 보정한다.
```

### Engineering model

```txt
Pre-AR calibration
  clean frame
  ARFace projection export
  Apple Vision contour
  required face parsing mask
  color/gradient confidence
  user adjustment
  deferred failure-mode notes
        |
        v
Boundary fusion
        |
        v
screen-space lip reference mask
        |
        v
ARFace UV/vertex back-projection
        |
        v
lip calibration package
  uvProbabilityMap
  vertexWeightSet
  upper/lower maps
  inner-mouth exclusion
  corner falloff
  blendshape correction rules
        |
        v
Runtime
  ARFace mesh/UV
  smooth-region-mask shader
  lightweight correction
  no heavy per-frame parsing
```

## 5. Signal Roles

| Signal | 역할 | 사용 시점 | Runtime primary 여부 |
| --- | --- | --- | --- |
| ARFace mesh/UV | 얼굴에 붙는 좌표계 | calibration + runtime | Yes |
| ARFace screen projection | 2D mask를 UV/vertex로 옮기는 bridge | calibration/offline | No |
| Apple Vision lip landmarks | required iOS-native 2D contour hint | calibration/offline | No by default |
| Face parsing | required pixel-level semantic lip/skin/mouth silver signal | offline/calibration | No |
| Color/gradient | required boundary confidence signal | calibration/offline | No |
| User adjustment | required final personalization confirmation | calibration | Values only |
| Failure-mode type | deferred failure taxonomy / held-out eval grouping after boundary quality improves | evaluation/future | Values only |
| Blendshape / face state | required expression correction signal for M1 ready | runtime | Yes, lightweight |

## 6. Apple Vision Role

Apple Vision은 Vision Pro가 아니라 iOS/macOS의 computer vision framework다. 이 계획에서는 `VNDetectFaceLandmarksRequest` 같은 face landmarks 계열을 **M1 pre-filter 필수 lip contour signal**로 본다.

좋은 점:

- iOS-native라 dependency risk가 낮다.
- 외부 모델 다운로드 없이 시작할 수 있다.
- pre-AR calibration에서 얼굴/입술 contour sanity check에 좋다.

한계:

- 결과는 2D image coordinate 기준이다.
- ARFace mesh/UV와 직접 같은 좌표계가 아니다.
- makeup-grade lip edge를 단독으로 보장하지 않는다.
- 조명, occlusion, pose에 따라 contour 안정성이 달라질 수 있다.

이 문서에서의 결정:

```txt
Apple Vision = required calibration/pre-filter contour signal
Apple Vision != runtime primary tracker
```

사용 방식:

- neutral/smile/open/pucker capture frame에서 lip contour를 얻는다.
- face parsing이나 user-reviewed mask와 비교해 confidence를 만든다.
- ARFace screen projection 위에 overlay해서 좌표계가 맞는지 확인한다.
- contour가 잘 맞는 경우 boundary fusion에 positive hint로 사용한다.
- contour가 낮은 confidence인 경우 color/gradient나 user review 없이 자동 승격하지 않는다.

## 7. Face Parsing Role

Face parsing은 얼굴 이미지를 semantic label로 나누는 segmentation 계열이다.

예상 label:

- `upper_lip`
- `lower_lip`
- `mouth` / `inner mouth`
- `skin`
- `eye`
- `brow`
- `hair`

좋은 점:

- "정확히 어디까지가 입술인가"라는 질문에 가장 직접적이다.
- 피부/입술 색 대비가 낮은 케이스를 분석하는 데 좋다.
- Apple Vision contour보다 면적 reference를 만들기 쉽다.
- ARFace mask가 어디서 새는지 scoring하기 좋다.

한계:

- model/dataset/weights license를 별도로 확인해야 한다.
- live iPhone runtime으로 돌리면 성능, 발열, 지연, binary size risk가 커진다.
- 2D output이므로 ARFace UV/vertex에 다시 옮겨야 한다.
- pretrained model bias와 edge-case failure가 있다.

이 문서에서의 결정:

```txt
Face parsing = required M1 pre-filter silver semantic signal
Human-reviewed face parsing = gold 후보
Face parsing != E7.03 live runtime dependency
Face parsing != product/release asset source
```

Silver-to-gold rule:

- Model output만으로는 official gold mask가 아니다.
- 사람이 같은 synchronized frame에서 확인하거나 수정해야 gold가 된다.
- Gold mask가 되려면 `frame.png`와 `arface_export.json`이 같은 runtime moment에서 나온 capture pair여야 한다.

## 8. Color / Gradient Role

색은 보조 신호다.

쓸 수 있는 정보:

- lip/skin color contrast.
- local gradient around vermilion border.
- shadow confidence.
- specular/gloss highlight distraction.
- low-contrast warning.

금지:

- "빨간 영역 = 입술" 단독 판단.
- "피부보다 어두운/밝은 영역 = 입술" 단독 판단.
- 특정 피부색/인종을 class로 두고 분기.

권장:

```txt
색/gradient는 boundary confidence와 warning만 만든다.
실제 runtime placement는 ARFace UV/vertex map을 따른다.
```

Edge-case examples:

- low skin/lip contrast.
- dark lip with dark surrounding skin.
- strong lower-face shadow.
- facial hair shadow.
- lipstick already applied before calibration.
- glossy lips causing specular edge confusion.

### Color / Gradient Downstream Uses

Color/gradient 추출이 가능해졌다는 것은 boundary 생성기가 생겼다는 뜻이 아니라, **프레임 선택과 렌더링 검증에 쓸 수 있는 경량 센서가 생겼다는 뜻**이다.

우선순위가 높은 downstream use:

1. Calibration quality check.
   - 현재 M1에서 이미 구현된 기본 용도다.
   - `lowContrastWarning`, `shadowWarning`, `specularWarning`으로 현재 capture가 boundary fusion 입력으로 안전한지 판단한다.
   - 이 판단은 `ready` 승격이 아니라 `partial` / retake / review 사유를 명확히 하는 데 쓴다.

2. Best-of-N calibration selector.
   - neutral 또는 expression capture를 여러 장 찍은 뒤, 각 frame의 ARFace tracking, Apple Vision availability, face parsing coverage, color/gradient confidence를 함께 점수화한다.
   - 가장 좋은 capture pair만 M1 reference / fusion 기준으로 사용한다.
   - 모든 후보가 낮으면 자동 승격하지 않고 retake 또는 user review로 보낸다.

3. Retake reason generator.
   - `lowContrastWarning=true`: 입술-피부 색/경계 신호가 약하므로 균일한 조명 또는 더 선명한 capture가 필요하다.
   - `shadowWarning=true`: 얼굴 하단 그림자/역광 가능성이 높으므로 조명 방향을 바꾸고 다시 캡처한다.
   - `specularWarning=true`: 광택/반사가 edge 판단을 방해할 수 있으므로 gloss/립밤/반사 조건을 줄이고 다시 캡처한다.
   - 이 안내는 product onboarding 문구가 아니라 validation-only capture guide다.

4. Makeup visibility detector for later E7.4/E7.5 validation.
   - 원본 lip/skin 색과 makeup 적용 후 lip/skin 색 변화를 비교해 "화장이 실제로 보였는지"를 숫자로 확인한다.
   - 이는 cosmetic renderer 구현 승인이 아니라, 나중에 E7.4/E7.5가 명시적으로 열렸을 때 pigment/finish visibility evidence로만 쓴다.

5. Spill detector for later overlay checks.
   - Makeup 적용 후 outside skin band의 색 변화가 커지면 skin spill 가능성으로 기록한다.
   - inner-mouth/teeth 주변 색 변화가 커지면 inner-mouth spill 가능성으로 기록한다.
   - 이 판단은 mask를 자동 확장하지 않고, `lip-safe-v0`, user adjustment, 또는 retake/review 사유를 고르는 보조 신호로만 쓴다.

금지:

- Color/gradient만으로 lip boundary를 만들거나 확장하지 않는다.
- Color/gradient를 인종, 피부색 class, 민감 특성 분류에 쓰지 않는다.
- Color/gradient downstream use를 근거로 E7.3 Green, E7.4/E7.5/E7.6, product readiness, live runtime inference를 승인하지 않는다.

## 9. User Adjustment Role

사용자 조정은 실패를 감추는 꼼수가 아니라 개인차를 줄이는 필수 보정층이다.

초기 control은 네 개로 제한하되, 실제 관찰된 실패 유형에 직접 대응시킨다.

| Control | 의미 | 범위 제안 | Runtime 저장값 |
| --- | --- | --- | --- |
| `cornerReach` | 가로 폭 / 입꼬리 도달 보정. `+`는 입꼬리 쪽으로 확장, `-`는 입꼬리 spill 축소 | `-1.0..1.0` | corner reach / horizontal local scale |
| `upperLipTightness` | 윗입술 위쪽 번짐 또는 부족 보정. `+`는 더 타이트하게, `-`는 더 덮게 | `-1.0..1.0` | upper-lip threshold / local vertical scale |
| `lowerLipTightness` | 아랫입술 아래쪽 번짐 또는 부족 보정. `+`는 더 타이트하게, `-`는 더 덮게 | `-1.0..1.0` | lower-lip threshold / local vertical scale |
| `verticalOffset` | 전체 mask 상하 이동. image-space 기준 `+`는 아래, `-`는 위 | `-1.0..1.0` | UV/local offset |

실증 반영:

- 가로 크기가 작은 경우가 많고 입꼬리까지 잡지 못하므로 `cornerShrink` 단방향 control은 폐기한다. 다음 contract에서는 `cornerReach`가 입꼬리 확장과 축소를 모두 담당한다.
- 아랫입술 번짐이 많고 윗입술도 번질 수 있으므로 전체 `tightness` 하나로 처리하지 않는다. `upperLipTightness`와 `lowerLipTightness`를 분리한다.
- 높낮이 불만은 boundary 품질 문제와 UX 문제를 헷갈리게 만들 수 있으므로 `verticalOffset`은 유지하되, 이 값으로도 해결되지 않으면 reference mask / projection coordinate issue로 되돌린다.
- Legacy aliases인 `tightness`, `upperLowerBalance`, `cornerShrink`는 기존 artifacts 읽기용으로만 남긴다. 새 M1 ready 또는 `lip-tight-user-v0` user-confirmed claim은 `cornerReach`, `upperLipTightness`, `lowerLipTightness`, `verticalOffset` 네 값이 명시될 때만 허용한다.

UX 원칙:

- calibration step 안에서만 노출한다.
- product onboarding처럼 꾸미지 않는다.
- 자유 드로잉 UI부터 만들지 않는다.
- 조정값은 local validation artifact로만 다룬다.
- 서버 업로드나 사용자 프로필 저장은 금지한다.

## 10. Failure-mode Type Classification

유형 분류는 demographic classification이 아니다. 사용자를 인종/성별/민감 특성으로 분류하지 않는다.

분류 대상은 관찰 가능한 failure mode다. 다만 M1에서는 Apple Vision, face parsing, color/gradient confidence, user adjustment, pucker/blendshape evidence로 기본 boundary 품질을 먼저 검증한다. Failure-mode type은 이번 M1 ready gate에서 제외하고, 엔진 boundary가 1차 목표 수준에 도달한 뒤 future eval / held-out 기록 단계에서 도입한다.

Deferred lip tags:

- `thin_lip`
- `full_lip`
- `strong_cupid_bow`
- `flat_cupid_bow`
- `low_skin_lip_contrast`
- `wide_smile_stretch`
- `mouth_open_teeth_visible`
- `pucker_heavy`
- `asymmetric_corners`
- `facial_hair_or_shadow`
- `strong_lighting_shadow`
- `pre_applied_lip_color`

이 tag는 나중에 아래 목적으로만 쓴다.

- 어떤 preset을 먼저 보여줄지 선택.
- 어떤 stress test를 꼭 볼지 결정.
- evaluation matrix에서 실패 원인을 분리.
- future held-out test set을 구성.

Initial `LipPresetProfile` selection may later be driven by these tags: `thin_lip -> thin`, `full_lip -> full`, `wide_smile_stretch/asymmetric_corners -> wide`, `low_skin_lip_contrast/facial_hair_or_shadow/strong_lighting_shadow/pre_applied_lip_color -> soft-edge`, and `mouth_open_teeth_visible -> inner-safe`. Do not build an automatic type classifier without labeled data. For current M1, only clear input-quality retake reasons such as strong lighting shadow, pre-applied lip color, obvious occlusion/shadow, or neutral-capture mouth-open/teeth visibility should affect capture retry decisions.

## 11. Pre-AR Calibration UX

Calibration은 짧고 반복 가능해야 한다.

이 단계의 목적은 사진을 많이 모으는 것이 아니라, AR 진입 전에 한 사람의 lip boundary package를 만드는 것이다. 각 capture는 pass/fail 판정용으로만 쓰지 않고, 아래 맞춤형 mask 구성 요소 중 하나를 만든다.

- `neutral`: 기본 screen-space lip reference mask와 ARFace UV/vertex anchor를 만든다.
- `open_close`: teeth / inner-mouth exclusion을 만든다.
- `smile`: 입꼬리 stretch와 corner falloff를 만든다.
- `pucker`: 중앙 수축과 pucker/funnel 보정 규칙을 만든다.
- `yaw`: 좌우 회전에서 corner/side projection 안정성을 확인하고 projection confidence를 낮출지 결정한다.
- `user adjustment`: 자동 후보를 사용자가 확정한 `lip-tight-user-v0` 보정값으로 만든다.

Pass/fail은 최종 목표가 아니라 품질 필터다. Tracking, faceCount, coordinate metadata, privacy flag가 깨지면 해당 input은 버리거나 M1을 `partial|blocked`로 남기지만, 통과한 input은 personalized boundary generation에 들어간다.

Recommended flow:

```txt
Step 1. Face ready
  tracking stable 확인

Step 2. Neutral
  정면, 입 자연스럽게

Step 3. Open/close
  입 살짝 열고 닫기

Step 4. Smile
  입꼬리 늘어남 확인

Step 5. Pucker
  오므림 확인

Step 6. Yaw
  좌/우 중 최소 하나

Step 7. Auto boundary preview
  lip-tight-auto-v0 / lip-safe-v0 비교

Step 8. User adjustment
  cornerReach, upperLipTightness, lowerLipTightness, verticalOffset

Step 9. Save calibration package
  local validation artifact
```

Minimum viable calibration:

- neutral
- open/close
- smile
- one yaw
- user adjustment

Pucker는 M1 ready에 필요한 표정 캡처다. 시간 제한으로 빠지면 `deferred`가 아니라 M1 `partial` 사유로 기록한다.

### Phase 1 capture flow contract

Phase 1에서 만들 화면은 product onboarding이 아니라 AR 진입 전 validation capture tool이다. 사용자는 짧은 단계별 prompt를 보고 정면/표정/고개 움직임을 수행하고, 앱은 각 단계마다 clean camera frame과 같은 순간의 ARFace export를 묶어 local capture record를 만든다. 각 record는 이후 `screenLipReferenceMask`, `innerMouthExclusion`, `cornerFalloff`, `upperLowerSplit`, `blendshapeCorrection`, `userAdjustment` 중 하나 이상을 만드는 입력이다.

| Step | Capture id prefix | User action | UI state | Required capture rule | Used to produce |
| --- | --- | --- | --- | --- | --- |
| 1. Face ready | `lip_ready` | 얼굴을 화면 중앙에 둠 | tracking/face/mesh 상태만 표시 | 저장하지 않아도 됨 | capture quality gate only: `tracking=Tracking`, `faceCount=1`, mesh counts available |
| 2. Neutral | `lip_neutral` | 입을 자연스럽게 닫고 정면 응시 | clean preview + tiny status | clean frame + same-moment ARFace export | base lip reference mask, ARFace UV anchor, Vision/parsing/color comparison |
| 3. Open-close | `lip_open_close` | 입을 살짝 열고 닫음 | 1-2 short captures or mini-burst | closed/open representative frames 중 최소 1개 저장 | inner-mouth / teeth exclusion and safe lower boundary |
| 4. Smile | `lip_smile` | 자연스럽게 웃음 | corner status visible | smile-stretched frame + ARFace export | corner reach, corner falloff, smile stretch confidence |
| 5. Pucker | `lip_pucker` | 입술을 오므림 | required capture state | pucker frame + ARFace export | central contraction and pucker/funnel correction; missing이면 M1 partial |
| 6. Yaw | `lip_yaw_left` / `lip_yaw_right` | 좌/우 중 하나 이상 고개 회전 | pose direction visible | one yaw frame + ARFace export | side/corner projection confidence and UV stability |
| 7. Auto preview | `lip_preview` | 후보 경계 확인 | `lip-tight-auto-v0` / `lip-safe-v0` 비교 | raw frame 저장 없이 derived preview만 생성 | generated mask preview, spill/under-cover review, candidate selection |
| 8. User adjustment | `lip_adjusted` | 4개 slider로 미세 보정 | Full Debug에서 값 표시 | params only; no free-draw mask | user-confirmed `lip-tight-user-v0` adjustment params |
| 9. Save package | `lip_calib` | local package 저장 | package id/path 표시 | derived package + summary only | personalized boundary package with privacy flags |

### Phase 1 input signal matrix

모든 capture record는 같은 순간의 frame/export 일치를 최우선으로 기록한다. 없는 신호는 자동 생성하지 않고 `unavailable`, `deferred`, 또는 `not_run`으로 남긴다.

| Signal | Required for which steps | Contract field | Notes |
| --- | --- | --- | --- |
| Clean frame image | neutral, open-close, smile, yaw, pucker | `cleanFrame` | Temporary local processing input. Long-term calibration package에는 raw image를 넣지 않는다. |
| ARFace screen vertices | all saved captures | `arFace.screenVertices` | 2D reference mask를 ARFace UV/vertex로 옮기는 bridge. |
| ARFace UVs | all saved captures | `arFace.uvs` | Phase 3 projection의 primary coordinate target. |
| ARFace indices | all saved captures | `arFace.indices` | triangle projection/back-projection에 필요. |
| ARFace clipW | all saved captures | `arFace.clipW` | perspective-correct interpolation에 필요. 없으면 projection confidence를 낮춘다. |
| Tracking state | all steps | `tracking.state` | `Tracking`, `Limited`, `Lost` 등. |
| Face count | all steps | `tracking.faceCount` | Phase 1에서는 `1`만 pass. |
| Mesh counts | all saved captures | `tracking.meshCounts` | expected `vertices`, `indices`, `uvs` counts 기록. |
| Blendshape snapshot | saved captures | `blendshapeSnapshot` | `jawOpen`, smile/stretch, pucker/funnel 후보. 없으면 M1 ready 불가. |
| Apple Vision lip contour result | saved captures | `visionLipContour` | M1 ready에는 `available` contour가 필요하다. 구현 전 `not_run`은 partial이다. |
| Required face parsing result | neutral/open/smile preferred | `faceParsing` | M1 ready에는 local/offline `silver` 이상이 필요하다. live runtime/Core ML 구현 금지. |
| Color/gradient confidence summary | saved captures | `colorGradientConfidence` | M1 ready에는 `computed` 필요. 단독 boundary 결정 금지. |
| User adjustment params | adjusted/save steps | `userAdjustment` | M1 ready에는 `user_confirmed` 필요. `cornerReach`, `upperLipTightness`, `lowerLipTightness`, `verticalOffset`, plus status showing whether zero values are user-confirmed or only assumed. |
| Extension slots | package-level only | `extensions.cheek`, `extensions.eye` | 현재는 `reserved_only`; cheek/eye 알고리즘을 시작하지 않는다. |

## 12. Calibration Data Package

Calibration output은 화면 픽셀 좌표가 아니라 runtime에서 재사용 가능한 face-space data다.

Package는 단순 pass/fail report가 아니다. 구조는 두 층이다.

1. `captureSet`: 어떤 same-moment frame / ARFace export / Vision / parsing / color / expression signal을 썼는지 남기는 입력 ledger.
2. `personalizedBoundary`: 그 입력을 합쳐 만든 screen-space lip mask, exclusion/falloff/split, user adjustment, UV/vertex handoff 산출물.

Readiness status는 이 산출물이 다음 단계로 넘어갈 수 있는지 설명하는 보조 메타데이터다. M1의 목표는 `pass`라는 말이 아니라 `lip-tight-auto-v0`, `lip-tight-user-v0`, `lip-safe-v0` 후보를 만들 수 있는 개인화 boundary package를 남기는 것이다.

Required shape:

```json
{
  "schemaVersion": "e7-lip-boundary-calibration-v0",
  "calibrationId": "lip-calib-YYYYMMDD-HHMMSS-v0",
  "region": "lip",
  "status": "draft|ready_for_boundary_fusion|ready_for_uv_projection|rejected",
  "createdAt": "YYYY-MM-DDTHH:mm:ss+09:00",
  "sourceCapturePairIds": [
    "pair_lip_neutral_0001",
    "pair_lip_open_close_0001",
    "pair_lip_smile_0001",
    "pair_lip_yaw_left_0001"
  ],
  "captureSet": [
    {
      "capturePairId": "pair_lip_neutral_0001",
      "step": "neutral",
      "required": true,
      "captureStatus": "captured|deferred|rejected",
      "timestamp": {
        "arFrameTimestamp": 12345.678,
        "frameImageTimestamp": 12345.678,
        "maxDeltaMs": 0
      },
      "frame": {
        "path": "frame.png",
        "width": 1920,
        "height": 1440,
        "orientation": "portrait",
        "mirrored": true,
        "colorSpace": "sRGB"
      },
      "viewport": {
        "width": 390,
        "height": 844,
        "contentMode": "aspectFill",
        "safeAreaApplied": true
      },
      "coordinateSpaces": {
        "frameImage": "image_pixel_top_left",
        "visionLandmarks": "face_bbox_normalized_bottom_left",
        "screenVertices": "frame_image_pixel_top_left",
        "referenceMask": "frame_image_pixel_top_left"
      },
      "cleanFrame": {
        "localProcessingInput": true,
        "longTermStored": false,
        "derivedEvidenceOnly": true,
        "frameDigest": "sha256-or-null"
      },
      "arFace": {
        "screenVertices": "available",
        "uvs": "available",
        "indices": "available",
        "clipW": "available",
        "screenVerticesPath": "arface_export.json#screenVertices",
        "uvsPath": "arface_export.json#uvs",
        "indicesPath": "arface_export.json#indices",
        "clipWPath": "arface_export.json#clipW",
        "meshCounts": {
          "vertices": 1220,
          "indices": 6912,
          "uvs": 1220
        }
      },
      "tracking": {
        "state": "Tracking",
        "faceCount": 1,
        "meshCountStatus": "valid"
      },
      "blendshapeSnapshot": {
        "status": "available|unavailable",
        "jawOpen": 0,
        "mouthSmileLeft": 0,
        "mouthSmileRight": 0,
        "mouthFunnel": 0,
        "mouthPucker": 0
      },
      "visionLipContour": {
        "status": "available|required_not_run|low_confidence|unavailable",
        "coordinateSpace": "image_normalized",
        "confidence": null
      },
      "faceParsing": {
        "status": "required_not_run|silver|human_reviewed_gold|unavailable",
        "labels": ["upper_lip", "lower_lip", "inner_mouth"],
        "localOnly": true
      },
      "colorGradientConfidence": {
        "status": "computed|not_run",
        "summary": "required_for_m1_ready",
        "lowContrastWarning": false,
        "shadowWarning": false,
        "specularWarning": false
      }
    }
  ],
  "personalizedBoundary": {
    "status": "draft|partial|ready_for_uv_projection|blocked",
    "generationGoal": "screen_space_lip_mask_to_arface_uv_package",
    "sourceSignals": {
      "arFaceTopology": "required_anchor",
      "meshStructuralDraft": "review_artifact_only",
      "appleVisionLipContour": "outer_contour_hint",
      "faceParsing": "lip_skin_inner_mouth_silver_signal",
      "colorGradientConfidence": "confidence_only_never_boundary_source_alone",
      "userAdjustment": "final_personalization_params"
    },
    "screenSpaceReferenceMask": {
      "status": "missing|generated|accepted_reference|human_reviewed_gold",
      "maskPath": "lip_reference_mask.png",
      "capturePairId": "pair_lip_neutral_0001",
      "coordinateSpace": "frame_image_pixel_top_left",
      "sourceBlend": [
        "faceParsingLipLabels",
        "appleVisionLipContour",
        "arFaceLipRing",
        "manualOrUserReviewedReference"
      ],
      "acceptedAsGold": false
    },
    "derivedComponents": {
      "innerMouthExclusion": {
        "status": "missing|contract_only|available",
        "source": "open_close + faceParsing inner_mouth + Vision inner contour + user review"
      },
      "cornerFalloff": {
        "status": "missing|contract_only|available",
        "source": "smile + yaw + corner reach review"
      },
      "upperLowerSplit": {
        "status": "missing|contract_only|available",
        "source": "faceParsing upper/lower labels + Vision contour + geometric fallback"
      }
    },
    "userAdjustedBoundary": {
      "status": "not_implemented|partial|user_confirmed",
      "candidateId": "lip-tight-user-v0",
      "params": {
        "cornerReach": 0,
        "upperLipTightness": 0,
        "lowerLipTightness": 0,
        "verticalOffset": 0
      }
    }
  },
  "lipBoundaryVersion": "lip-calibrated-uv-v0",
  "offlineCandidateConfigs": {
    "lip-tight-auto-v0": {
      "status": "uv_projection_artifact_only",
      "runtimeReady": false
    },
    "lip-tight-user-v0": {
      "status": "uv_projection_artifact_only",
      "runtimeReady": false
    },
    "lip-safe-v0": {
      "status": "uv_projection_artifact_only",
      "runtimeReady": false
    }
  },
  "assets": {
    "uvProbabilityMap": "lip_probability.png",
    "vertexWeightSet": "lip_vertex_weights.json",
    "upperLipMap": "lip_upper_probability.png",
    "lowerLipMap": "lip_lower_probability.png",
    "innerMouthExclusionMap": "lip_inner_mouth_exclusion.png",
    "cornerFalloffMap": "lip_corner_falloff.png"
  },
  "correction": {
    "blendshapeCorrectionRuleId": "lip-jaw-smile-pucker-v0",
    "userAdjustment": {
      "status": "user_confirmed|default_zero_assumed|not_implemented|partial",
      "confirmedByUser": false,
      "uiImplemented": false,
      "params": {
        "cornerReach": 0,
        "upperLipTightness": 0,
        "lowerLipTightness": 0,
        "verticalOffset": 0
      }
    }
  },
  "phase2BoundaryFusionInput": {
    "requiredSteps": ["neutral", "open_close", "smile", "yaw", "pucker"],
    "requiredReferenceSignals": [
      "visionLipContour",
      "faceParsing",
      "screenLipReferenceMask"
    ],
    "requiredCalibrationSignals": [
      "colorGradientConfidence",
      "userAdjustment",
      "blendshapeSnapshot"
    ],
    "deferredFollowups": [
      "failure_mode_type_classification_after_boundary_quality"
    ],
    "fusionCandidatesToProduce": [
      "lip-tight-auto-v0",
      "lip-tight-user-v0",
      "lip-safe-v0"
    ],
    "doNotPromoteToGreen": true
  },
  "phase3UvProjectionInput": {
    "requiresSameMomentFrameAndArFaceExport": true,
    "requiredArFaceFields": ["screenVertices", "uvs", "indices", "clipW"],
    "projectionRules": [
      "perspective_correct_uv",
      "visibility_confidence_ready_partial_blocked",
      "grazing_angle_downweight_when_supported",
      "unknown_not_negative"
    ],
    "visibilityPolicy": {
      "ready": "front-most visible triangle voting when reliable depth/visibility support is exported",
      "partial": "perspective-correct UV interpolation with clipW only; no occlusion-safe atlas claim",
      "blocked": "no clipW or equivalent perspective-correction support"
    },
    "expectedArtifacts": [
      "lip_probability.png",
      "lip_coverage.png",
      "lip_unknown.png",
      "lip_debug_votes.png",
      "lip_variants.json",
      "round_trip_overlay.png",
      "summary.json",
      "summary.md"
    ]
  },
  "extensions": {
    "cheek": {
      "status": "reserved_only"
    },
    "eye": {
      "status": "reserved_only"
    }
  },
  "confidenceSummary": {
    "visionContour": "required_available_for_m1_ready",
    "faceParsing": "required_silver_or_gold_for_m1_ready",
    "colorGradient": "required_computed_for_m1_ready",
    "humanReview": "required_accepted_gold_for_m1_ready",
    "userAdjustment": "required_user_confirmed_for_m1_ready",
    "failureModeType": "deferred_future_eval_not_m1_gate",
    "blendshapeSnapshot": "required_available_for_m1_ready",
    "calibrationFlow": "phase1_contract_complete"
  },
  "privacy": {
    "localOnly": true,
    "rawFrameStored": false,
    "longTermRawFrameStored": false,
    "offDeviceUpload": false,
    "backendUpload": false,
    "userProfileSync": false
  }
}
```

Notes:

- `cleanFrame.localProcessingInput=true`는 calibration 중 로컬 메모리/임시 파일로만 쓰는 입력 신호를 뜻한다.
- `rawFrameStored=false`와 `longTermRawFrameStored=false`는 long-term package 기준이다. Calibration 중 local frame을 잠깐 만들 수 있지만, derived evidence만 남기고 raw frame batch는 삭제한다.
- `sourceCapturePairIds`는 evidence traceability를 위해 남긴다.
- `captureSet`은 입력 ledger이고, `personalizedBoundary`가 실제 맞춤형 mask/package 산출물이다.
- `timestamp`, `frame`, `viewport`, and `coordinateSpaces` are projection safety fields, not cosmetic metadata. If these are absent, same-moment capture may exist but coordinate-space trust is still partial.
- `faceParsing=unavailable|required_not_run` 또는 `visionLipContour!=available`이면 M1은 `partial` 또는 `blocked`이며 ready가 아니다.
- `colorGradientConfidence!=computed`, `userAdjustment.status!=user_confirmed`, `blendshapeSnapshot!=available`, or missing `pucker`이면 M1은 `partial` 또는 `blocked`이며 ready가 아니다.
- `failureModeType`은 M1 ready gate가 아니다. 값이 없으면 future eval follow-up으로 기록하고, 현재 M1에서는 기본 boundary 품질을 먼저 검증한다.
- `status=ready_for_boundary_fusion`은 Phase 2가 reference signal fusion을 시작할 수 있다는 뜻이지 E7.3 Green이 아니다.
- `status=ready_for_uv_projection`은 Phase 3 one-frame round-trip / UV atlas 준비가 가능하다는 뜻이지 runtime quality evidence가 아니다.
- `personalizedBoundary.status=ready_for_uv_projection`이 되려면 screen-space reference mask, inner-mouth exclusion, corner falloff, upper/lower split, user adjustment, and required coordinate metadata가 어떤 source로 만들어졌는지 추적 가능해야 한다.
- `offlineCandidateConfigs` are Phase 3 projection artifacts only. They are not Unity-installed runtime candidates. A later runtime slice must record a separate `runtimeCandidateStatus` such as `installed_in_unity|tested_on_device|rejected`.
- `userAdjustment.status=default_zero_assumed` or `not_implemented` must not be described as a user-confirmed adjustment. This distinction matters most for `lip-tight-user-v0`.

## 13. Boundary Fusion Model

Phase 2의 목적은 product-quality 최종 렌더 mask를 확정하는 것이 아니라, Phase 1 package를 읽어 개인화 lip boundary handoff를 만드는 것이다. 즉 Apple Vision, face parsing, ARFace topology, color/gradient confidence, user adjustment, expression captures를 합쳐 `screenLipReferenceMask`, `innerMouthExclusion`, `cornerFalloff`, `upperLowerSplit`, and candidate handoff 상태를 만든다. Pass/fail은 이 산출물의 신뢰도를 설명하는 부가 상태다.

Local contract stub:

```txt
python3 scripts/e7_lip_boundary_fusion/prepare_fusion_summary.py \
  path/to/lip-calib-YYYYMMDD-HHMMSS-v0.json \
  --output-dir /tmp/e7-lip-fusion
```

이 stub은 `fusionSummary.json` / `fusionSummary.md` contract를 만든다. 실제 image-processing mask 생성은 M1 package builder 또는 수동/오프라인 reference artifact가 담당하고, fusion summary는 어떤 신호가 personalized boundary에 채택/거절됐는지와 Phase 3 UV projection으로 넘길 수 있는지를 기록한다. Core ML output, runtime texture, Unity-installed candidate는 만들지 않는다.

### Phase 2 input readiness

`lip-calib-*` package는 아래 조건을 만족해야 Phase 2 입력으로 받을 수 있다.

| Input | Required | Accept rule | Reject / down-weight rule |
| --- | --- | --- | --- |
| Package metadata | Yes | `schemaVersion=e7-lip-boundary-calibration-v0`, `region=lip`, `calibrationId` starts with `lip-calib-` | non-lip region, unsupported schema, missing id |
| Privacy flags | Yes | `localOnly=true`, `rawFrameStored=false`, `longTermRawFrameStored=false`, `offDeviceUpload=false`, `backendUpload=false` | any off-device/upload/raw long-term flag |
| `neutral` | Yes | captured, Tracking, faceCount 1, ARFace fields available | missing, Limited/Lost, faceCount not 1, missing ARFace bridge |
| `open_close` | Yes | captured or representative closed/open record, ARFace fields available | missing means inner-mouth exclusion cannot be trusted |
| `smile` | Yes | captured, corner stretch visible enough for review | missing means corner falloff is partial |
| `yaw` | Yes | at least one `yaw`, `yaw_left`, or `yaw_right` capture | missing means side/corner projection stability is partial |
| `pucker` | Yes | captured, central contraction visible enough for review | missing means contraction/pucker stability is partial |
| Apple Vision contour | Yes | `available` with coordinate metadata and confidence; required for M1 ready | `not_run`, low confidence, or unavailable keeps M1 partial/blocked |
| Face parsing lip labels | Yes | local/offline `silver` or `human_reviewed_gold`; required for M1 ready | `not_run` or unavailable keeps M1 partial/blocked; `silver` stays silver until human review |
| Color/gradient | Yes | `computed` confidence summary for every accepted capture | color-only boundary is rejected; missing keeps M1 partial/blocked |
| User adjustment | Yes | `status=user_confirmed` with four params; user-confirmed zero is allowed | never replaces reference evidence; absent/default-assumed values keep M1 partial/blocked |
| Failure-mode type | No / deferred | optional future eval type/preset with source reason | missing does not block M1; record as deferred follow-up |
| Blendshape snapshot | Yes | available jaw/smile/pucker/funnel values or explicit exporter support | missing keeps M1 partial/blocked |

우선순위:

1. Human-reviewed gold mask.
2. Face parsing lip labels, silver until reviewed.
3. Apple Vision lip contour.
4. ARFace UV/vertex topology.
5. Color/gradient confidence.
6. User adjustment.
7. Blendshape / face-state correction.
8. Deferred failure-mode taxonomy for later eval only.

Fusion rule:

```txt
ARFace topology defines where runtime can attach.
Gold/silver/reference signals define what should count as lip.
User adjustment corrects the final practical boundary.
Color/gradient is required confidence evidence, but never wins alone.
```

### Signal fusion policy

- ARFace topology is the attachment domain. A reference signal outside plausible projected ARFace lip/corner topology is rejected or clipped before Phase 3.
- Human-reviewed gold wins when it comes from the same runtime moment as the ARFace export.
- Face parsing `silver` is required before M1 ready and can seed `upper/lower/inner-mouth` labels, but it is never called product gold until human-reviewed.
- Apple Vision contour is required before M1 ready and can tighten the outer contour when it agrees with gold/silver or when no better reference exists and confidence is acceptable.
- Mesh-derived structural draft can seed or constrain a reference-mask candidate through the M1 implementation path in Section 14A. It is required as a review artifact for M1 audit, not gold, and must still become an accepted screen-space mask before UV projection.
- Color/gradient is required for M1 ready and can only change `confidenceSummary` and `rejectedSignalReasons`; it cannot expand or create a boundary alone.
- User adjustment is required for M1 ready and is applied last as scalar parameters: `cornerReach`, `upperLipTightness`, `lowerLipTightness`, `verticalOffset`.
- Blendshape/face-state signals are required before M1 ready; if unavailable, the result remains partial with exact missing reasons.
- Failure-mode type classification is deferred until boundary quality is good enough for meaningful failure taxonomy; missing failure-mode tags do not keep M1 partial.
- If Apple Vision or face parsing is absent, Phase 2 is `partial` or `blocked`, not `ready`, even when a manual/reference mask exists.

Candidate outputs:

| Candidate | Meaning | Default use |
| --- | --- | --- |
| `lip-tight-auto-v0` | automatic reference-assisted tight mask | first comparison |
| `lip-tight-user-v0` | automatic mask + user adjustment | expected best practical candidate |
| `lip-safe-v0` | spill prevention first, smaller coverage | fallback for teeth/skin spill |
| `lip-smooth-mask-v1` | existing broad baseline | compare-only |

Promotion rule:

- `lip-tight-auto-v0` can be promoted only if it beats broad baseline in neutral and at least one expression scenario.
- `lip-tight-user-v0` is the expected main candidate if automatic contour is close but not exact.
- `lip-safe-v0` wins if broad/tight candidates repeatedly paint skin, teeth, or inner mouth.

Candidate generation rules:

| Candidate | Required source | Boundary behavior | Confidence / rejection rule |
| --- | --- | --- | --- |
| `lip-tight-auto-v0` | neutral + smile/yaw + accepted gold/silver/reference mask + required Vision/parsing/color/blendshape signals | tight outer contour, conservative color confidence, no user bias | reject color-only edges; partial if any required M1 signal is missing |
| `lip-tight-user-v0` | `lip-tight-auto-v0` + user-confirmed adjustment params | applies corner reach, independent upper/lower tightness, and vertical offset | partial if adjustment is not explicitly user-confirmed; does not override inner-mouth exclusion |
| `lip-safe-v0` | open_close + accepted pucker + inner-mouth exclusion + corner falloff + required Vision/parsing reference signals | smaller spill-prevention mask; accepts under-coverage before teeth/skin spill | partial if any required M1 signal is missing; future failure taxonomy may explain later edge-case behavior |

### `fusionSummary.json` contract

```json
{
  "schemaVersion": "e7-lip-boundary-fusion-summary-v0",
  "fusionId": "fusion-lip-calib-YYYYMMDD-HHMMSS-v0",
  "calibrationId": "lip-calib-YYYYMMDD-HHMMSS-v0",
  "region": "lip",
  "phase2Status": "ready|partial|blocked",
  "inputs": {
    "captureSet": {
      "neutral": [{"capturePairId": "pair_lip_neutral_0001", "acceptedForFusion": true}],
      "open_close": [{"capturePairId": "pair_lip_open_close_0001", "acceptedForFusion": true}],
      "smile": [{"capturePairId": "pair_lip_smile_0001", "acceptedForFusion": true}],
      "yaw": [{"capturePairId": "pair_lip_yaw_left_0001", "acceptedForFusion": true}],
      "pucker": []
    },
    "referenceSignals": {
      "humanReviewedGold": 0,
      "faceParsingSilver": 0,
      "visionContourAvailable": 0,
      "visionContourLowConfidence": 0,
      "colorGradientComputed": 0,
      "colorGradientWarnings": []
    },
    "userAdjustment": {
      "status": "user_confirmed|default_zero_assumed|not_implemented|partial",
      "confirmedByUser": false,
      "uiImplemented": false,
      "params": {
        "cornerReach": 0,
        "upperLipTightness": 0,
        "lowerLipTightness": 0,
        "verticalOffset": 0
      }
    }
  },
  "fusionPolicy": {
    "priority": [
      "human_reviewed_gold_mask",
      "face_parsing_lip_labels_silver_until_reviewed",
      "apple_vision_lip_contour",
      "arface_topology_projection",
      "color_gradient_confidence_required_confidence_only",
      "user_adjustment_params",
      "blendshape_face_state_correction"
    ],
    "deferredFollowups": [
      "failure_mode_type_classification_after_boundary_quality"
    ],
    "runtimeRule": "no_live_face_parsing_or_core_ml_runtime"
  },
  "candidateOutputs": {
    "lip-tight-auto-v0": {
      "status": "ready_for_mask_derivation|partial_contract_only|blocked",
      "rejectedSignalReasons": []
    },
    "lip-tight-user-v0": {
      "status": "ready_for_mask_derivation|partial_contract_only|blocked",
      "rejectedSignalReasons": []
    },
    "lip-safe-v0": {
      "status": "ready_for_mask_derivation|partial_contract_only|blocked",
      "rejectedSignalReasons": []
    }
  },
  "phase3OutputContract": {
    "screenSpaceLipReferenceMask": {
      "requiredFields": ["maskPath", "capturePairId", "coordinateSpace", "acceptedSignalIds"]
    },
    "innerMouthExclusion": {
      "source": "open_close plus required faceParsing/Vision plus user review; missing source keeps M1 partial/blocked"
    },
    "cornerFalloff": {
      "source": "smile and yaw corner stretch/spill review"
    },
    "upperLowerSplit": {
      "source": "required faceParsing labels plus required Vision contour; geometric split alone is partial fallback, not M1 ready"
    },
    "confidenceSummary": {
      "source": "per-capture signal confidence plus global phase2Status"
    },
    "rejectedSignalReasons": []
  }
}
```

`fusionSummary.md`는 같은 내용을 사람이 빠르게 읽는 요약으로 남긴다. 실제 raw frame 경로나 장기 보관 위치를 적지 않고, `capturePairId`, signal status, candidate status, rejected reasons만 적는다.

## 14. Screen Mask to ARFace UV/Vertex Projection

Projection pipeline:

```txt
2D reference mask on clean iPhone frame
-> ARFace triangle projected to screen
-> pixel inside triangle
-> barycentric weights
-> perspective-correct UV
-> UV probability vote
-> candidate atlas
```

Mandatory rules:

- `frame.png` and `arface_export.json` must come from the same runtime moment.
- Use `screenVertices`, `uvs`, `indices`, and `clipW` or equivalent perspective-correction field.
- The capture pair must record frame size, orientation, mirroring, viewport/content mode, and coordinate-space mapping for `frame.png`, Vision landmarks, `screenVertices`, and `referenceMask`.
- A mesh-derived structural draft is not a projection input by itself. It can enter Phase 3 only after it is accepted as a screen-space lip reference mask with traceable source signals.
- Visibility handling is graded:
  - If reliable clip-space depth, front-most marking, or per-triangle visibility is exported, use front-most visible triangle voting and record `visibilityConfidence=ready`.
  - If only `clipW` is available, use perspective-correct UV interpolation, record `visibilityConfidence=partial`, and do not claim an occlusion-safe atlas.
  - If neither `clipW` nor equivalent perspective-correction support exists, block Phase 3 projection.
- Reject or down-weight back-facing, occluded, tiny projected-area, and grazing-angle triangles only when the required geometry/visibility signal exists. Otherwise record the limitation instead of silently pretending the vote is occlusion-safe.
- Treat low-vote UV regions as unknown, not negative.
- Run one-frame round-trip before batch atlas generation.
- Do not treat one-frame round-trip as Q3 runtime evidence.

### Capture pair metadata contract

The minimum same-moment pair is not only `frame.png` plus `arface_export.json`. It must also make the projection coordinate system auditable:

```json
{
  "capturePairId": "pair_lip_neutral_0001",
  "timestamp": {
    "arFrameTimestamp": 12345.678,
    "frameImageTimestamp": 12345.678,
    "maxDeltaMs": 0
  },
  "frame": {
    "path": "frame.png",
    "width": 1920,
    "height": 1440,
    "orientation": "portrait",
    "mirrored": true,
    "colorSpace": "sRGB"
  },
  "viewport": {
    "width": 390,
    "height": 844,
    "contentMode": "aspectFill",
    "safeAreaApplied": true
  },
  "coordinateSpaces": {
    "frameImage": "image_pixel_top_left",
    "visionLandmarks": "face_bbox_normalized_bottom_left",
    "screenVertices": "frame_image_pixel_top_left",
    "referenceMask": "frame_image_pixel_top_left"
  },
  "arFace": {
    "screenVerticesPath": "arface_export.json#screenVertices",
    "uvsPath": "arface_export.json#uvs",
    "indicesPath": "arface_export.json#indices",
    "clipWPath": "arface_export.json#clipW"
  }
}
```

If this metadata is missing, Phase 3 can still report what is present, but `coordinateSpaceValidated` must remain false or partial until `round_trip_overlay.png` proves there is no y-flip, mirror, scale, or aspect-fill crop mismatch.

### Minimum reference mask creation path

The first Phase 3 projection sanity proof may run with a selected user-painted gold raw reference or newly reviewed manual mask, but M1 ready must wait for every required M1 signal: Apple Vision, local/offline face parsing, color/gradient, user-confirmed adjustment, pucker, blendshape/face-state, accepted/gold reference, coordinate/visibility, held-out/eval, and split/exclusion/falloff evidence. Failure-mode type is deferred until boundary quality is good enough for meaningful taxonomy. Projection-only proof without the required M1 signals is partial.

Minimum path:

1. Use one neutral same-moment capture pair.
2. Generate required comparison masks/signals: selected user-painted gold raw reference, newly reviewed manual or accepted screen-space mask, local face parsing silver mask, Apple Vision outer/inner lips contour rasterization, and existing `lip_ring` mesh draft for review only.
3. Human-review the overlay.
4. Save `lip_reference_mask.png` and `lip_reference_mask.meta.json`.
5. The metadata must include `maskSource`, `reviewedBy`, `capturePairId`, `coordinateSpace`, `imageWidth`, `imageHeight`, `acceptedSignalIds`, and `knownWeaknesses`.

Manual polygon gold/reference is allowed for the first coordinate-space proof only when it is newly reviewed or explicitly accepted. The user-painted gold raw references under `evidence/references/e7-user-gold-raw-20260626/` may be used as gold reference assets, but each selected asset must still pass coordinate pairing before M1 UV projection readiness. The rejected `manual_polygon_codex_visual_reference_v0` lineage is not allowed because the goal is `screen mask -> ARFace UV -> round-trip`, and a wrong screen mask would make that proof meaningless.

Required artifacts:

```txt
lip_probability.png
lip_coverage.png
lip_unknown.png
lip_debug_votes.png
lip_variants.json
round_trip_overlay.png
summary.json
summary.md
```

`lip_variants.json` must store offline candidate configs with `runtimeReady=false`. Runtime install/test status belongs to a later runtime slice, not Phase 3 projection.

Local preparation / execution stub:

```txt
python3 scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py \
  path/to/fusionSummary.json \
  --capture-pair path/to/pair_lip_neutral_0001 \
  --mask path/to/lip_reference_mask.png \
  --mask-source human_reviewed_gold \
  --accepted-signal-id human_reviewed_lip_mask \
  --inner-mouth-status available \
  --corner-falloff-status available \
  --upper-lower-status available \
  --output-dir /tmp/e7-lip-uv-projection
```

Preparation behavior:

- If `fusionSummary.json` is missing or Phase 2 is `blocked`, Phase 3 execution is `blocked`.
- If the same-moment capture pair is missing `frame.png` or `arface_export.json`, Phase 3 execution is `blocked`.
- If the capture pair lacks frame/orientation/mirroring/viewport/coordinate-space metadata, Phase 3 records `coordinateSpaceValidated=false` or partial until overlay review resolves it.
- If the accepted screen-space lip reference mask is missing, Phase 3 execution is `blocked` rather than generating fake PNGs.
- If inner-mouth exclusion, corner falloff, or upper/lower split are still `contract_only`, Phase 3 execution is `partial` even if the basic round-trip can run.
- If `coordinateSpaceValidated=false`, the script records a warning; the next review must inspect `round_trip_overlay.png` before trusting the projection.
- The script may read a local frame/mask/export to produce derived evidence, but it does not store raw frames long-term, upload data, run live face parsing/Core ML, build UnityFramework, or modify runtime shaders/materials.

### Phase 2 / Phase 3 output contract

Phase 1이 다음 단계에 넘기는 것은 UI 화면 시안이 아니라 local calibration package와 capture record contract다.

Phase 2 Boundary Fusion receives:

- `lip-calib-*` package metadata.
- `captureSet` entries for `neutral`, `open_close`, `smile`, and at least one `yaw`.
- required `pucker` entry with accepted capture evidence.
- capture-pair coordinate metadata: frame dimensions, orientation, mirroring, viewport/content mode, timestamp delta, and coordinate-space mapping.
- Apple Vision lip contour result per saved capture; `not_run`, low confidence, or unavailable prevents M1 ready.
- local/offline face parsing result per useful capture; `silver` or `human_reviewed_gold` is required for M1 ready, while `not_run` or unavailable prevents M1 ready.
- color/gradient confidence summary per capture.
- user adjustment params plus status; zero values must distinguish `user_confirmed` from `default_zero_assumed` or `not_implemented`.
- privacy flags proving `localOnly=true`, `rawFrameStored=false`, and `offDeviceUpload=false`.

Phase 2 Boundary Fusion produces:

- `screenLipReferenceMask` or equivalent derived local mask for each accepted capture.
- `innerMouthExclusion` decision.
- `cornerFalloff` decision.
- `upperLowerSplit` decision.
- candidate decisions for `lip-tight-auto-v0`, `lip-tight-user-v0`, and `lip-safe-v0`.
- `fusionSummary.json` / `fusionSummary.md` with confidence and rejected-signal reasons.

Phase 3 UV Projection receives:

- Phase 2 accepted screen-space lip reference mask: `maskPath`, `capturePairId`, `coordinateSpace=frame_image_pixel_top_left` or an explicitly convertible equivalent, `acceptedSignalIds`, `derivedEvidenceOnly=true`.
- same-moment capture-pair metadata for frame size, orientation, mirroring, viewport/content mode, timestamp delta, and coordinate-space mapping.
- `innerMouthExclusion`: open/close evidence, face parsing/Vision/user-review source, and rejection reason if unavailable.
- `cornerFalloff`: left/right corner confidence, smile/yaw source ids, and spill-prevention bias.
- `upperLowerSplit`: upper/lower confidence and fallback label if only geometric split exists.
- `confidenceSummary`: overall `phase2Status`, per-signal confidence, and whether the mask has required gold/silver/reference acceptance metadata.
- `rejectedSignalReasons`: missing/low-confidence Vision, unavailable face parsing, missing color/gradient, unconfirmed user adjustment, missing blendshape/face-state, color-only edge, missing ARFace field, privacy flag violation, or missing pucker.
- `deferredFollowups`: include `failure_mode_type_classification_after_boundary_quality` when failure taxonomy is intentionally postponed.
- same-moment ARFace `screenVertices`, `uvs`, `indices`, and `clipW`.
- `capturePairId` traceability for every projection input.
- rejection/down-weight rules for occluded, tiny, back-facing, or grazing triangles.

Phase 3 UV Projection produces:

- `uvProbabilityMap`, `upperLipMap`, `lowerLipMap`, `innerMouthExclusionMap`, and `cornerFalloffMap`.
- `vertexWeightSet`.
- `round_trip_overlay.png` and `roundTripScore`.
- `lip_variants.json` with `offlineCandidateConfigs`, each marked `runtimeReady=false`.
- `summary.json` / `summary.md` that separates `roundTripScore`, `calibrationScore`, and future `evalScore`.

Runtime install state is not part of Phase 3. A later runtime slice may add a separate `runtimeCandidateStatus` field such as `installed_in_unity|tested_on_device|rejected`.

Completion rule:

```txt
Phase 2 Boundary Fusion contract_ready = input/fusion/candidate/output contract and buildless summary stub complete.
Phase 2 Boundary Fusion contract_ready != Boundary Fusion execution complete.
Phase 2 Boundary Fusion contract_ready != UV back-projection complete.
Phase 2 Boundary Fusion contract_ready != runtime mask implemented.
Phase 2 Boundary Fusion contract_ready != E7.3 Green.
```

## 14A. Mesh-Derived Structural Draft and Preset Profile Extension

This section is part of M1 Buildless Personalized Lip Package v0. It is no longer a standalone planning-only phase. It still does not supersede Boundary Fusion or UV Projection, but its first useful implementation is to generate a reviewable user-specific lip draft from existing ARFace mesh evidence before the app runtime slice.

### Current evidence reality

- Current reusable capture evidence includes clean frontal-ish capture pairs and projected mesh overlays, especially `pair_face_20260622T143334Z_03`.
- Current evidence is not a complete `lip-calib-*` package: neutral/open-close/smile/pucker/yaw calibration captures are not all collected.
- User-approved human-painted gold assets exist, but no coordinate-paired M1-ready lip gold mask has been selected yet.
- The existing `manual_polygon_codex_visual_reference_v0` marking from `m1-lip-package-20260625T112757Z` and every mask derived from it are explicitly rejected by user decision as wrong marking. They must not be used as gold, reference, candidate seed, UV projection input, or M1 readiness evidence.
- User-painted gold raw references are available at `evidence/references/e7-user-gold-raw-20260626/`. Every file in that folder is accepted as human-painted gold for offline reference, candidate generation, candidate scoring, and mask derivation experiments. A specific file still needs coordinate-space and same-moment ARFace export pairing before it can satisfy M1 UV projection readiness.
- No real `fusionSummary.json` has been generated from a complete calibration package.
- Therefore mesh-derived draft work can be designed and visually inspected, but it cannot claim a complete personalized tracking package yet.

### Package naming rule

`PersonalizedRegionTrackingPackage` is a conceptual umbrella only. It is not a new on-disk schema, file name, or source of truth.

The actual package contract remains:

```txt
schemaVersion=e7-lip-boundary-calibration-v0
calibrationId=lip-calib-*
extensions.cheek.status=reserved_only
extensions.eye.status=reserved_only
```

### Existing label group reuse

Mesh-derived draft must reuse existing Phase 2 manual vertex label groups where available:

- `lip_ring`
- `cheekbone_soft_cheek`
- `eyelid_band`

Do not define this extension as a fresh topology-discovery project. The first draft path is existing label groups plus current export fields, then required Vision/parsing comparison and user review.

### Derivable signal table

| Signal / feature | Current status | Use in mesh draft | Rule |
| --- | --- | --- | --- |
| `screenVertices` | available in current capture exports | project existing lip-ring structure into the clean frame | usable now |
| `uvs` | available | keep draft tied to ARFace UV space | usable now |
| `indices` | available | follow triangle edge continuity around the existing label group | usable now |
| `clipW` | available as projection support | perspective-correct interpolation / projection sanity only | usable now |
| mesh counts | available, expected `1220/6912/1220` | reject incompatible export shape | usable now |
| mouth/lip topology seed | available through existing label groups and mesh topology | rough lip-area structural seed | derivable now |
| lip ring projection | available through label group + screen vertices | first screen-space draft envelope | derivable now |
| edge continuity | available through indices | avoid disconnected draft islands | derivable now |
| mouth width / height ratio | derivable from projected structural points | select simple lip preset profile | derivable now |
| corner distance | derivable from projected structural points when label group is sufficient | detect wide-corner tendency | derivable now |
| simple area / position ratio | derivable from projected envelope | thin/full/wide rough classification | derivable now |
| per-vertex normals | not exposed in current accepted export contract | curvature or surface-angle reasoning | exporter extension required |
| curvature | not exposed and not safely derivable from current fields alone | do not use for current draft scoring | exporter extension required |
| reliable per-triangle visibility | not exposed | front-most / occlusion rejection | exporter extension required |
| front-most triangle marking | not exposed | robust UV vote filtering | exporter extension required |
| blendshape values | current capture export records unavailable | expression-conditioned draft refinement | exporter extension required |

`screenVertices` depth-like values are projection-support metadata only. Do not treat them as normals, curvature, or reliable visibility evidence.

### LipPresetProfile rule

`LipPresetProfile` selects an initial shape policy. It is not a runtime candidate id.

Allowed candidate ids remain:

- `lip-tight-auto-v0`
- `lip-tight-user-v0`
- `lip-safe-v0`
- `lip-smooth-mask-v1` as broad baseline only

Do not create `lip-thin-v0`, `lip-full-v0`, `lip-wide-v0`, `lip-soft-edge-v0`, or `lip-inner-safe-v0` as runtime candidates.

Preset profiles use two separate namespaces:

| Field | Meaning | Namespace rule |
| --- | --- | --- |
| `userAdjustmentBias` | initial bias for the four Section 9 scalars: `cornerReach`, `upperLipTightness`, `lowerLipTightness`, `verticalOffset` | user-adjustment namespace |
| `maskDerivationNote` | candidate-generation notes such as feather tendency, coverage tendency, confidence warning, or inner-mouth exclusion strength | candidate-generation namespace |

`featherTendency` and `coverageTendency` here are draft-stage notes, not the Section 15 runtime `coverage` / `feather` tuning controls.

| Preset profile | `userAdjustmentBias` | `maskDerivationNote` | Candidate preference |
| --- | --- | --- | --- |
| `thin` | `upperLipTightness` / `lowerLipTightness` positive | conservative coverage tendency | start with `lip-tight-auto-v0` |
| `full` | `upperLipTightness` / `lowerLipTightness` negative | coverage-friendly draft tendency, still bounded by accepted reference mask | start with `lip-tight-auto-v0` |
| `wide` | `cornerReach` positive | preserve or extend wider corner range if no spill is observed | start with `lip-tight-auto-v0`; review corners |
| `soft-edge` | no required scalar bias | lower confidence warning; feather tendency only | require review before promotion |
| `inner-safe` | `lowerLipTightness` positive, `cornerReach` neutral or negative | stronger inner-mouth / lower-face spill prevention | prefer `lip-safe-v0` |

### Flow placement

```txt
existing label groups + current export fields
-> mesh-derived structural draft
-> required Vision/parsing comparison plus color/user review comparison
-> accepted screen-space lip reference mask
-> Phase 2 Boundary Fusion candidate decision
-> Phase 3 UV Projection
```

The draft is useful only if it helps produce a better accepted reference mask. It is not a substitute for gold review or one-frame round-trip.

## 14B. Gold-Reference Mask Derivation Experiment

This section is the overnight-agent contract for deciding how to make the first useful personalized lip mask. It is still M1 buildless work. It does not authorize UnityFramework/Xcode/iPhone builds, live face parsing/Core ML runtime, upload, product UI, or E7.4/E7.5 renderer work.

Goal:

```txt
user-painted gold raw references
-> extracted gold masks
-> multiple mask derivation candidates
-> automatic scoring and contact sheets
-> selected derivation policy or explicit partial/blocked reason
```

The output is a mask derivation policy, not a product-quality makeup claim. A selected policy can be used for the next coordinate-paired M1 package attempt only after the selected gold/reference asset is matched to a same-moment `frame.png` and `arface_export.json`.

### Required Inputs

Primary gold reference manifest:

```txt
evidence/references/e7-user-gold-raw-20260626/manifest.json
```

All files in that manifest have `acceptedAsGold=true` by user decision. Agents must treat them as human-painted gold reference assets for offline mask derivation and scoring.

Gold sets:

| Set | Files | Use |
| --- | --- | --- |
| `soft_alpha_set` | `contact-sheet.png`, `combined-soft-alpha-projection.png` | visual reference and multi-region context; `combined-soft-alpha-projection.png` may seed color-label extraction when dimensions match |
| `lip_gold_set_20260625` | `user-gold-lip-mask-gray-20260625-163204.png`, `user-gold-lip-render-20260625-163240.png` | primary lip-only gold mask plus rendered visual context |
| `A_set` | `A_1.png`, `A_0.png` | second lip gold mask plus full-face visual context |

Optional comparison signals:

- same-moment capture pair, preferably `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/`;
- Apple Vision lip contour artifacts when available;
- local/offline face parsing artifacts when available;
- ARFace `screenVertices`, `uvs`, `indices`, and `clipW`;
- color/gradient confidence artifacts;
- user adjustment review artifacts.

Hard input rules:

- Use only the user-painted gold raw manifest above for gold source unless the user explicitly adds another gold set.
- Never use `manual_polygon_codex_visual_reference_v0` or any derived mask from that rejected lineage.
- Never promote a generated candidate to M1 ready without coordinate-space compatibility with a same-moment ARFace export.
- If a listed gold file is missing, hash-mismatched, unreadable, or dimension-mismatched without an explicit conversion rule, mark the experiment `partial` or `blocked`.
- Do not overwrite raw gold files. All derived masks go under the experiment output folder.

### Output Folder Contract

Create one run folder:

```txt
evidence/e7-lip-mask-derivation/experiment-YYYYMMDDTHHMMSSZ/
```

Required artifacts:

| Artifact | Purpose |
| --- | --- |
| `input_manifest.json` | resolved gold files, source manifest hash, optional Vision/parsing/ARFace inputs, privacy flags |
| `gold_extracted_masks/*.png` | binary or alpha masks extracted from each gold source |
| `gold_extraction_report.json` | extraction method, positive pixels, bounding box, dimensions, warnings per gold file |
| `candidates/<candidateId>/*.png` | candidate masks at the same dimensions as the evaluated gold mask |
| `overlays/<candidateId>_overlay.png` | candidate over visual context when context exists |
| `contact_sheet.png` | compact visual comparison for all candidates and gold masks |
| `mask_derivation_scores.json` | numeric metrics, hard rejects, per-set scores, weighted totals |
| `selected_policy.json` | selected policy, decision, confidence, tie/margin details, required next action |
| `mask_derivation_summary.md` | human-readable result and next boundary |

The run must not store new camera frames unless they are already accepted evidence or explicitly supplied by the user. If a script needs visual context, reference existing paths in `input_manifest.json`.

### Candidate Families

Generate every candidate that has enough input. If a candidate cannot be generated, record it as `skipped` with the exact missing input; do not silently omit it.

| Candidate id | Input | Rule |
| --- | --- | --- |
| `gold_exact_binary` | user-painted gold mask | threshold non-background/non-transparent pixels into a binary mask |
| `gold_alpha_soft` | user-painted gold mask | keep anti-aliased alpha/edge softness where present |
| `gold_clean_morphology` | extracted gold mask | close tiny holes, remove specks, keep one main lip component |
| `gold_conservative_erode` | extracted gold mask | shrink slightly to reduce skin/inner-mouth spill risk |
| `gold_coverage_dilate` | extracted gold mask | expand slightly to reduce under-coverage; reject if spill grows too much |
| `face_parsing_raw` | face parsing silver | direct lip labels only |
| `face_parsing_clean` | face parsing silver | cleaned upper/lower lip labels, inner-mouth removed when available |
| `vision_contour_fill` | Apple Vision contour | rasterized outer lip contour, inner contour removed when available |
| `vision_expanded` | Apple Vision contour | slightly expanded contour for low-coverage comparison |
| `arface_lip_ring_envelope` | ARFace lip ring | projected mesh envelope; structural baseline only |
| `parsing_clamped_by_vision` | parsing + Vision | parsing lip mask clipped or expanded only where Vision agrees |
| `parsing_clamped_by_arface` | parsing + ARFace | parsing lip mask clipped to plausible ARFace lip envelope |
| `hybrid_conservative` | gold + parsing/Vision/ARFace | prioritize precision and spill avoidance |
| `hybrid_balanced` | gold + parsing/Vision/ARFace | balance coverage and spill |
| `hybrid_coverage` | gold + parsing/Vision/ARFace | prioritize lip coverage; reject if spill is excessive |
| `lip_smooth_mask_v1_baseline` | existing broad baseline if available | compare-only negative/broad baseline |

Minimum useful run:

- at least `gold_exact_binary`, `gold_alpha_soft`, `gold_clean_morphology`, `gold_conservative_erode`, and `gold_coverage_dilate`;
- at least one gold set must produce a non-empty extracted lip mask;
- if Vision, parsing, or ARFace inputs are missing, the run can still be `partial` but not `blocked` if gold-derived candidates and scoring are produced.

### Evaluation Metrics

Plain-language meaning:

```txt
Good mask = covers the painted lip gold area and avoids everything else.
```

Per candidate, compute these metrics for every compatible gold set:

| Metric | Meaning | Direction |
| --- | --- | --- |
| `goldIoU` | overlap between candidate and gold mask | higher is better |
| `lipCoverageRecall` | how much of gold lip is covered | higher is better |
| `lipPrecision` | how much candidate area is actually gold lip | higher is better |
| `outsideGoldSpill` | candidate area outside gold | lower is better |
| `innerMouthSpill` | overlap with inner-mouth/teeth signal when available | lower is better |
| `skinBandSpill` | spill into nearby skin band around gold mask | lower is better |
| `componentCount` | disconnected islands | 1 main component preferred |
| `holeCount` | holes inside lip mask | lower is better unless inner-mouth is intentionally excluded |
| `edgeRoughness` | jagged boundary / perimeter-to-area anomaly | lower is better |
| `bboxPlausibility` | width/height/position within plausible lip range for the frame | pass/fail or score |
| `visionAgreement` | agreement with Apple Vision contour when available | higher is better |
| `faceParsingAgreement` | agreement with face parsing lip labels when available | higher is better |
| `arfaceEnvelopeAgreement` | overlap with plausible ARFace lip-ring envelope when coordinate-paired | higher is better |

Initial scoring formula:

```txt
baseScore =
  0.35 * goldIoU
  + 0.25 * lipPrecision
  + 0.20 * lipCoverageRecall
  + 0.10 * boundaryCleanliness
  + 0.05 * auxiliarySignalAgreement
  + 0.05 * robustnessAcrossGoldSets

penalties =
  outsideGoldSpillPenalty
  + innerMouthSpillPenalty
  + skinBandSpillPenalty
  + disconnectedIslandPenalty
  + coordinateMismatchPenalty

finalScore = clamp(baseScore - penalties, 0.0, 1.0)
```

If a metric cannot be computed, set it to `null`, record `metricUnavailableReasons`, and reduce confidence. Do not invent a score.

### Hard Rejects

Reject a candidate before weighted scoring when any of these are true:

- candidate source uses `manual_polygon_codex_visual_reference_v0` or a derived rejected mask;
- candidate is empty;
- candidate dimensions do not match the evaluated gold mask and no explicit conversion was performed;
- lip candidate covers more than `0.06` of the full frame area unless the run is explicitly marked as full-face/combined-region context;
- lip candidate has more than `3` disconnected components after cleanup;
- `outsideGoldSpill > 0.45` for gold-only scoring;
- `lipCoverageRecall < 0.55` for gold-only scoring;
- `lipPrecision < 0.55` for gold-only scoring;
- inner-mouth/teeth spill is available and exceeds `0.08`;
- coordinate-paired mode is requested but required `frame.png`, `arface_export.json`, orientation, mirroring, viewport, or dimensions are missing.

These thresholds are starting bars for automation. If they reject every candidate, the correct result is `partial_needs_review`, not a fake ready result.

### Decision Rule

Write exactly one `experimentDecision`:

| Decision | Required condition |
| --- | --- |
| `ready_for_coordinate_pairing` | top candidate passes hard rejects, `finalScore >= 0.75`, margin over second candidate is `>= 0.05`, and at least two compatible gold references do not contradict the chosen policy family |
| `partial_needs_review` | candidates and scores exist, but score is below threshold, margin is too small, gold sets disagree, optional signals are missing, or overlays look risky |
| `blocked` | no valid gold mask can be extracted, manifest is invalid, every candidate hard-rejects, or required coordinate-paired inputs are requested but absent |

`ready_for_coordinate_pairing` is not M1 ready. It means the mask derivation policy is good enough to try with a same-moment capture/export pair.

`selected_policy.json` must include:

```json
{
  "schemaVersion": "e7-lip-mask-derivation-selected-policy-v0",
  "experimentDecision": "ready_for_coordinate_pairing|partial_needs_review|blocked",
  "selectedCandidateId": "hybrid_balanced",
  "selectedPolicyFamily": "gold_clean|vision|parsing|arface|hybrid|baseline",
  "finalScore": 0.0,
  "scoreMargin": 0.0,
  "acceptedGoldSourceIds": [],
  "hardRejects": [],
  "metricUnavailableReasons": [],
  "requiresHumanReview": true,
  "nextAction": "coordinate_pair_selected_gold|human_review_candidates|fix_inputs"
}
```

### Agent Work Order

Run agents in this order:

1. Manager agent validates scope:
   - lip-first M1 only;
   - local-only;
   - no upload;
   - no live runtime inference;
   - no UnityFramework/Xcode/iPhone build;
   - rejected polygon lineage is unavailable.
2. Data/evidence agent validates `manifest.json`, hashes, dimensions, roles, and gold extraction feasibility.
3. Development agent implements or runs the buildless derivation script.
4. Scoring agent computes all metrics, hard rejects, and selected policy.
5. Tester agent re-runs manifest validation, confirms output schema, checks `git diff --check`, and verifies no rejected lineage appears in inputs.
6. Manager agent writes the final `mask_derivation_summary.md` with `ready|partial|blocked` language and syncs `TECH_VALIDATION_RESULT.md` if the boundary changes.

The agents must continue without user input by choosing `partial_needs_review` whenever a judgment call is too close. They must not force `ready_for_coordinate_pairing`.

### Completion Criteria

This experiment is complete when:

- all raw gold inputs from `evidence/references/e7-user-gold-raw-20260626/manifest.json` are accounted for;
- at least the minimum gold-derived candidates are generated;
- every generated candidate has metrics or explicit unavailable reasons;
- a contact sheet exists;
- `mask_derivation_scores.json`, `selected_policy.json`, and `mask_derivation_summary.md` exist;
- the summary names the selected policy or exact blocker;
- no artifact claims E7.3 Green, runtime readiness, product readiness, or M1 ready unless coordinate-paired M1 gates also pass.

## 15. Runtime Lightweight Tracking

Runtime must stay light.

Runtime inputs:

- ARFace mesh vertices/indices/UVs.
- selected lip candidate id.
- selected mask texture.
- user adjustment params.
- lightweight expression signals; if unavailable, the candidate remains partial/fallback-only and cannot be treated as M1-approved runtime input.
- tracking state.

Runtime must not:

- run face parsing every frame;
- run Core ML every frame;
- acquire a second camera session;
- upload frames;
- store raw camera frames by default.

Unity behavior:

- Existing `smooth-region-mask` remains the active renderer mode unless a later implementation explicitly introduces a new isolated candidate mode.
- `E3RegionMaskOverlay` or a dedicated E7 component samples `_MaskTex` through ARFace UVs.
- `MaskTextureId` must support a calibrated lip candidate without replacing `lip-smooth-mask-v1`.
- `coverage` and `feather` remain tuning controls, not semantic boundary finders.
- On `Tracking`, render normally.
- On short `Limited`, hold or fade.
- On extended lost, hide and re-prime after recovery.

Blendshape correction:

These rules require blendshape values to be exposed by a later exporter/runtime slice; Section 14A records current capture-export blendshape values as unavailable.

| Signal | Intended correction |
| --- | --- |
| `jawOpen` | increase inner-mouth caution, reduce lower-lip overpaint if needed |
| smile/stretch | adjust corner falloff or horizontal tolerance |
| pucker/funnel | reduce broad corner assumptions, tighten central region |
| tracking limited | hold/fade/hide, not new boundary inference |

Blendshape rule:

```txt
Blendshapes modulate an already-good boundary.
They do not create semantic boundaries from scratch.
```

## 16. RN Validation UI

RN UI is validation tooling, not product UI.

Required behavior:

- Compact HUD defaults to collapsed bottom sheet.
- Face/lip remains visible during tuning.
- Clean mode hides RN UI but keeps makeup overlay visible.
- Candidate selector is debug/validation only.
- Slider changes should be throttle or release-commit based.
- User adjustment values are visible in Full Debug.
- Runtime logs include active candidate id and adjustment params.

Suggested controls:

```txt
Candidate:
  broad baseline
  lip-tight-auto-v0
  lip-tight-user-v0
  lip-safe-v0

Adjustment:
  cornerReach
  upperLipTightness
  lowerLipTightness
  verticalOffset

Evidence:
  tracking
  mesh v/i/uv
  FPS
  recipe latency
  candidate id
  maskTextureId
  fallback flag
```

## 17. Edge Case Matrix

The first acceptance matrix is lip-only.

| Case | Why it matters | Must observe |
| --- | --- | --- |
| thin lip | easy to overpaint skin | upper/lower miss and spill |
| full lip | easy to under-cover | coverage and corner behavior |
| strong cupid bow | upper lip shape sensitivity | cupid bow miss |
| low skin/lip contrast | color cannot be trusted | non-color boundary stability |
| wide smile | corner stretch | corner detachment/spill |
| mouth open with teeth visible | inner-mouth risk | teeth/inner-mouth spill |
| pucker/funnel | shape contraction | central mask stability |
| facial hair/shadow | false edge risk | color/gradient confidence |
| asymmetric corners | one-side failure | per-side adjustment need |

Metrics per case:

- skin spill;
- teeth / inner-mouth spill;
- corner detachment;
- upper lip miss;
- lower lip overfill;
- jitter;
- lag;
- recovery after tracking loss.

## 18. Scoring

Use both human visual review and approximate metrics.

When a reference mask exists:

```txt
precision = TP / (TP + FP)
recall = TP / (TP + FN)
IoU = TP / (TP + FP + FN)
leakage = FP / candidatePositive
miss = FN / referencePositive
```

Lip weighting:

- highest weight: precision and leakage;
- strong penalty: teeth / inner-mouth spill;
- strong penalty: lower-face skin spill;
- moderate penalty: small cupid bow miss;
- moderate penalty: corner gap if not visually severe;
- visual review overrides unreliable numbers.

Score labels:

- `calibrationScore`: measured on frames used to generate the atlas.
- `evalScore`: measured on held-out frames.
- `roundTripScore`: projection sanity only, not runtime quality.

Minimum `roundTripScore` shape:

```json
{
  "maskToRoundTripIoU": 0.0,
  "contourMeanErrorPx": null,
  "contourP95ErrorPx": null,
  "validTriangleVoteRatio": 0.0,
  "unknownUvRatio": 0.0,
  "coverageRatio": 0.0,
  "coordinateSpaceValidated": false,
  "visibilityConfidence": "ready|partial|blocked",
  "requiresHumanOverlayReview": true
}
```

Phase 3 one-frame pass means:

- `coordinateSpaceValidated=true`.
- `round_trip_overlay.png` visually aligns with the source mask.
- no obvious y-flip, mirror, scale, or aspect-fill crop mismatch.
- `unknownUvRatio` is recorded and not treated as negative lip evidence.
- summary separates projection sanity from runtime quality.

Suggested first bars:

```txt
lip precision >= 0.80
lip leakage <= 0.15
visual review: no severe repeated skin/teeth/inner-mouth spill
```

These are starting bars. Revise only after actual gold reference quality is reviewed.

## 19. Performance Budget

Principle:

```txt
Heavy before AR.
Light during AR.
No surprise runtime inference.
```

Allowed in calibration/offline:

- Apple Vision face landmarks.
- Face parsing reference.
- Color/gradient analysis.
- Multiple captured frames.
- UV back-projection.
- Candidate scoring.

Allowed in runtime:

- ARFace mesh/UV sampling.
- Mask texture lookup.
- A small number of material parameters.
- Low-dimensional blendshape correction.
- Smoothing/hysteresis on scalar params.

Not allowed by default:

- Per-frame face parsing.
- Per-frame Core ML segmentation.
- Second camera session.
- Raw frame upload.
- Product profile sync.

Runtime evidence must record:

- FPS/frame-time; if capture fails, the runtime sweep remains partial and the failure reason must be recorded.
- recipe latency.
- mesh vertex/index/uv counts.
- candidate id.
- fallback flag.
- tracking state.

## 20. Evidence Plan

Buildless evidence:

- `git diff --check`.
- If Boundary Fusion contract stub changes: `python3 -m py_compile scripts/e7_lip_boundary_fusion/prepare_fusion_summary.py`.
- If Phase 3 projection preparation stub changes: `python3 -m py_compile scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py`.
- If RN changes happen later: `npm test -- --runInBand --watchman=false`, `./node_modules/.bin/tsc --noEmit`, `npm run lint`.
- If projection scripts change from contract stub to real math, add/run focused tests under `tests/e7_lip_uv_projection/`:
  - `test_barycentric_inside_triangle.py`
  - `test_perspective_correct_uv.py`
  - `test_mask_dimension_mismatch_blocks.py`
  - `test_missing_clipw_partial_or_blocked.py`
  - `test_coordinate_space_mismatch_warns.py`
  - `test_unknown_not_negative.py`
  - `test_no_fake_artifacts_when_mask_missing.py`

Offline evidence:

- `fusionSummary.json` and `fusionSummary.md`.
- one-frame round-trip overlay.
- original frame + reference mask + projected mesh overlay.
- candidate preview contact sheet.
- `summary.json` and `summary.md`.
- clear `calibrationScore` vs `evalScore` labels.

Real-device evidence, only after build approval:

- one install sweeps all lip candidates.
- 10-20 second lip motion clip if motion is decision evidence.
- representative frames/contact sheets retained.
- raw recordings can be deleted after extraction unless a specific decision needs retention.
- full runtime console stream captured when logs are decision evidence.

## 21. G/Y/R Criteria

### Green

- Lip boundary reaches Q3 overlay-ready validation candidate.
- Neutral, smile, open/close, pucker, and yaw evidence exist or skipped scenarios are explicitly documented.
- No severe repeated skin, teeth, or inner-mouth spill.
- Runtime evidence shows face-attached behavior with acceptable FPS/latency.
- Candidate, mask, calibration package, and evidence paths are recorded.

Green does not mean product-v1 readiness.

### Yellow

- Neutral and light motion are credible.
- Smile/open/corner scenarios still show visible issues.
- Candidate is useful for more boundary tuning.
- E7.4 cosmetic rendering remains blocked or explicitly capped as Yellow-risk if the team chooses to proceed.

### Red

- Repeated broad skin spill remains after calibrated UV + user adjustment.
- Teeth or inner mouth are repeatedly painted in normal motion.
- Boundary cannot stay attached under normal head/lip movement.
- Projection math cannot be trusted.
- Runtime cost or tracking instability invalidates the path.

## 22. Stop Rules

Stop and re-scope if:

- synchronized frame/export pair is unavailable;
- projection round-trip fails due to coordinate mismatch;
- Apple Vision or face parsing requires a second camera session for runtime;
- any path requires off-device upload;
- a candidate needs commercial SDK terms;
- user adjustment becomes product onboarding instead of validation tool;
- E7.4/E7.5/E7.6 starts before E7.3 risk is explicitly accepted;
- the team tries to classify demographic identity rather than failure mode.

## 23. Implementation Sequence

The contract/prep phases are done. The remaining work is intentionally compressed into three implementation milestones so the team does not keep adding contract-only subphases.

### M1. Buildless Personalized Lip Package v0

Goal:

```txt
existing capture pair
-> mesh-derived lip draft
-> accepted/reference lip mask
-> required Vision/parsing/color/user/failure/blendshape signals
-> fusion summary
-> UV round-trip
-> offline personalized lip package artifacts
```

Work:

- Use the best existing same-moment capture pair first, preferably `pair_face_20260622T143334Z_03`.
- Implement mesh-derived draft v0 from existing `lip_ring` label group plus available `screenVertices`, `uvs`, `indices`, and `clipW`.
- Produce review artifacts such as `lip_mesh_draft.png`, `lip_mesh_draft_overlay.png`, and `lip_mesh_draft_meta.json`.
- Create or accept one new valid `lip_reference_mask.png`; selected user-painted gold raw references are allowed, and manual polygon annotation is allowed for the first proof only when it is newly reviewed or explicitly accepted. The rejected `manual_polygon_codex_visual_reference_v0` lineage is locked out and cannot satisfy this item.
- Produce Apple Vision lip contour artifacts and metadata for the same frame. If Vision is unavailable or low confidence, M1 remains partial/blocked with the exact reason.
- Produce local/offline face parsing lip/skin/mouth artifacts and metadata for the same frame. If parsing is unavailable, M1 remains partial/blocked with the exact reason.
- Produce color/gradient confidence artifacts, user-confirmed adjustment params, pucker capture, and blendshape/face-state evidence. If any required signal is unavailable, M1 remains partial/blocked with the exact reason. Failure-mode classification remains a deferred follow-up, not a current M1 blocker.
- Generate a real `fusionSummary.json` / `fusionSummary.md` for this capture.
- Run the buildless UV round-trip stub and produce `lip_probability.png`, `lip_coverage.png`, `lip_unknown.png`, `lip_debug_votes.png`, `lip_variants.json`, `round_trip_overlay.png`, `summary.json`, and `summary.md`.
- Keep `lip_variants.json` as offline configs with `runtimeReady=false`.

Acceptance:

- The overlay shows whether the personalized mask lands in the correct coordinate space.
- User-painted gold raw references are valid gold assets, but M1 UV projection readiness still requires coordinate-space compatibility with the chosen same-moment ARFace export.
- Any reference mask with `rejectedByUser=true`, `doNotUseAsReference=true`, or `reviewStatus` starting with `rejected` keeps M1 blocked/partial and must not be used for candidate selection.
- Apple Vision contour status is `available`; otherwise M1 is not ready.
- Face parsing status is `silver` or `human_reviewed_gold`; otherwise M1 is not ready.
- Color/gradient is `computed`, user adjustment is `user_confirmed`, pucker capture is accepted, and blendshape/face-state values are available; otherwise M1 is not ready.
- Failure-mode type classification is not required for M1 ready; record it later when the engine boundary is strong enough for useful edge-case taxonomy.
- Missing normals, curvature, reliable triangle visibility, or front-most triangle support are recorded as limitations and keep M1 partial unless their replacement evidence is explicitly accepted.
- Result is `ready|partial|blocked` with exact reasons.
- No UnityFramework/Xcode/iPhone build and no runtime candidate claim.

### M2. In-App Pre-Filter Calibration Slice

Goal:

```txt
app entry
-> face/check capture
-> local personalized mask/package creation or selection
-> filter starts with that package
```

Work:

- Add the smallest validation UI path for pre-filter face check and capture, reusing existing capture/export mechanics where possible.
- Make the app either generate the M1-style package locally or select a precomputed local package for the current validation run.
- Keep the broad baseline available as fallback and comparison.
- Do not add live face parsing/Core ML runtime, backend upload, product onboarding, or commercial SDK.
- Run this milestone only after the normal build gate approval.

Acceptance:

- On device, the user-visible flow is clear: 검사 -> 맞춤형 lip package 준비 -> 필터 진입.
- Runtime does not pretend a package exists when calibration is blocked.
- Logs show active package/candidate id, mesh counts, fallback flag, and whether the package was generated or selected.

### M3. Runtime Candidate Sweep and Lip G/Y/R

M3 is split into two parts so unattended agents do not overrun into build/device work:

- M3A Buildless Runtime Sweep Prep: phone-disconnected / overnight-agent work only.
- M3B Build-Gated Runtime Candidate Sweep: real-device build, motion evidence, and Lip G/Y/R decision.

M3A can prepare the runtime sweep and source-stage validation-only candidate assets/registries inside the repo, but it cannot build/install the app, run ARFace sampling, collect FPS/latency, record runtime visual evidence, or decide Lip G/Y/R.

#### M3A. Buildless Runtime Sweep Prep

Goal:

```txt
M1/M2-approved or explicitly draft lip package inputs
-> runtime candidate asset/registry drafts
-> RN/Unity candidate/package/adjustment wiring
-> sweep logging and review contract
-> static verification bundle
```

Work:

- Confirm whether M1/M2 outputs are actually ready. If not ready, keep every M3A artifact marked `draft` or `blocked_by_m1_m2` and do not claim runtime readiness.
- Prepare runtime candidate asset/registry drafts only for `lip-tight-auto-v0`, `lip-tight-user-v0`, and `lip-safe-v0`; if assets are source-staged under Unity Resources, record `runtimeReady=false` and `runtimeCandidateStatus=validation_only_installed_buildless|source_staged_buildless_unproven` until a build-gated run proves otherwise.
- Wire or prepare RN/Unity candidate IDs, local package selection, and the four adjustment controls only: `cornerReach`, `upperLipTightness`, `lowerLipTightness`, and `verticalOffset`. A lightweight Unity shader sampling/threshold probe may use these values during M3B runtime validation, but the baked candidate mask texture is not regenerated live and this must not be described as `user_confirmed`.
- Prepare sweep log fields, evidence schema, contact-sheet/review checklist, and prior runtime evidence summary.
- Run static/buildless checks only: `git diff --check`, RN `npm test -- --runInBand --watchman=false`, `./node_modules/.bin/tsc --noEmit`, `npm run lint`, and Unity compile/import checks if touched and available without device.
- Summarize existing logs/recordings only as historical context; do not use them as the new M3 runtime evidence.

Expected M3A output folder:

```txt
evidence/e7-lip-runtime-sweep-prep/prep-YYYYMMDDTHHMMSSZ/
  input_readiness.json
  runtime_candidate_registry_draft.json
  runtime_candidate_registry.json (only if source-staged for buildless compile validation)
  adjustment_controls_contract.json
  sweep_evidence_schema.json
  runtime_sweep_checklist.md
  prior_evidence_summary.md
  static_verification.md
  summary.md
```

M3A acceptance:

- Result is `prep_ready|partial|blocked`, not Lip Green/Yellow/Red.
- No UnityFramework/Xcode/iPhone build, no app install, no device runtime claim, and no E7.3 Green claim.
- Source-staged Unity Resources are allowed only as buildless validation assets with `runtimeReady=false`; they are not proof that the candidate works on-device.
- Candidate registry must record `userAdjustmentParams`, `userAdjustmentStatus`, and whether those params were actually applied to the mask; auto-provisional values must not be presented as `user_confirmed`.
- Every candidate traces to an M1/M2-approved package or is explicitly marked `blocked_by_m1_m2`.
- Static checks pass, or failures are recorded with exact command/status.
- The next action is either return to M1/M2, request the M2/M3 build gate, or wait for phone-connected runtime testing.

#### M3B. Build-Gated Runtime Sweep

Goal:

```txt
personalized lip package
-> runtime ARFace UV sampling
-> minimal user adjustment
-> motion validation
-> lip G/Y/R decision
```

Work:

- Install only the M1/M2-approved candidates: `lip-tight-auto-v0`, `lip-tight-user-v0`, and `lip-safe-v0`.
- Add the four minimal adjustment controls only: `cornerReach`, `upperLipTightness`, `lowerLipTightness`, `verticalOffset`.
- Start only after user-approved build gate, with the build question, primary path, compare-only paths, validation contract, evidence matrix, and out-of-scope items stated first.
- Run one-build / many-candidate sweep across neutral, open/close, smile, pucker, and yaw; any skipped state requires an explicit waiver and keeps the result capped at partial/Yellow-risk.
- Record FPS/frame-time, recipe latency, mesh counts, fallback flag, active candidate, and representative visual evidence; missing runtime evidence keeps the sweep partial.

Acceptance:

- Decide whether lip is Green, Yellow, or Red under the Q3 overlay-ready bar.
- If lip is not credible, return to M1/M2 with a specific failure reason: coordinate space, mesh draft, reference mask, fusion, package, runtime sampling, or adjustment.
- If lip is credible, decide whether to extend the same package pattern to cheek/eye or explicitly accept Yellow risk before E7.4 cosmetic rendering.

Do not create more milestones inside this lip-first path unless one of these three is blocked for a concrete technical reason.

## 24. Next Implementation Prompt

```txt
cwd=/Users/wiseungcheol/Desktop/makeupAR

Read first:
- AGENTS.md
- TECH_VALIDATION_RESULT.md > Current Session Snapshot
- docs/roadmaps/active/E7_LIP_BOUNDARY_PRE_AR_CALIBRATION_SPIKE_PLAN_KO.md
- docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md only for UV projection details
- docs/roadmaps/active/E7_LIP_SAMPLE_PACK_V0_RUNTIME_REVIEW_CONTEXT_KO.md only for the v0 runtime failure context

Goal:
Implement M1 Buildless Personalized Lip Package v0 for the E7.03 lip-first pre-AR boundary calibration path.

This is the first real implementation slice for the intended app flow:

```txt
app/pre-filter 검사
-> 사용자별 lip draft/package 생성
-> AR filter runtime 진입
```

M1 stays buildless, but it must produce real local artifacts rather than more contract text.

Scope:
- lip only
- preserve E3/E4 baseline, smooth-region-mask, 3-layer RN payload, and existing bridge behavior
- do not start E7.4/E7.5/E7.6
- do not add live face parsing/Core ML runtime
- do not upload or persist raw camera frames by default

Preferred first slice:
1. Select the best existing same-moment capture pair, preferably `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/`.
2. Implement or run a mesh-derived lip draft v0 using existing `lip_ring` label group plus current export fields (`screenVertices`, `uvs`, `indices`, `clipW`).
3. Produce review artifacts: `lip_mesh_draft.png`, `lip_mesh_draft_overlay.png`, and `lip_mesh_draft_meta.json`.
4. Provide one accepted/reference `lip_reference_mask.png` on the same frame; selected user-painted gold raw references are allowed, and manual polygon annotation is allowed for the first proof only when it is newly reviewed or explicitly accepted. The rejected `manual_polygon_codex_visual_reference_v0` lineage is locked out.
5. Produce required Apple Vision lip contour artifacts and required local/offline face parsing artifacts for the same frame; if either is unavailable, M1 remains partial/blocked with exact reasons.
6. Produce required color/gradient confidence, user-confirmed adjustment params, pucker capture, and blendshape/face-state artifacts; if any required signal is unavailable, M1 remains partial/blocked with exact reasons. Leave failure-mode classification as a deferred follow-up.
7. Generate a real `fusionSummary.json` / `fusionSummary.md` for this input.
8. Run `python3 scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py ...` in buildless mode.
9. Produce offline package artifacts only: lip_probability, lip_coverage, lip_unknown, lip_debug_votes, lip_variants with offlineCandidateConfigs/runtimeReady=false, round_trip_overlay, summary.
10. If inputs are insufficient, record `ready|partial|blocked` and the exact missing input; do not invent masks or fake artifacts.
11. Stop before UnityFramework/Xcode/iPhone build unless the user approves the M2 build gate.

Decision:
Do not mark E7.3 Green. Record whether M1 is ready / partial / blocked, and name the next concrete step: implement/run Apple Vision, implement/run local face parsing, compute color/gradient, confirm user adjustment, capture pucker/blendshape evidence, fix mesh draft, create/reference-approve mask, fix fusion summary, fix UV projection, or proceed to M2 build gate only after all current M1 gates pass. Keep failure-mode classification as future eval work after boundary quality improves.
```

## 24B. Overnight Multi-Agent Launch Contract

Use this section when the user asks Codex to run unattended multi-agent work until the deadline or until the remaining app usage is exhausted.

### Run Window

```txt
Deadline: 2026-06-26 12:00 KST
Usage budget: no internal token cap; use the remaining Codex app usage until exhausted
Concurrency: max 3 active sub-agents
Do not stop only because human review would normally be required. When human judgment is missing, continue with an explicitly labeled `auto_provisional` or `pending_review` artifact and keep readiness `partial`.
Stop only when: all buildless work queues are exhausted, usage/quota/rate limit is exhausted, deadline arrives, UnityFramework/Xcode/iPhone build is required, new phone capture is required, or an input is truly blocked.
```

The manager is the current Codex thread. Do not spawn agents until the user explicitly says to start.

### Priority Order

1. Primary goal: advance every unfinished lip-plan task that can be done buildlessly without phone capture, UnityFramework, Xcode, iPhone install, or runtime evidence. This is not limited to Section 14B.
2. Dependency order: Section 14B gold-mask derivation -> optional-signal rerun -> coordinate preview/audit -> auto-provisional policy selection -> M1 package regeneration -> provisional user-adjustment review -> M1 gate matrix/next queue -> missing-scenario capture manifest -> M3A draft prep.
3. Do not start M3B, UnityFramework, Xcode, iPhone install, real-device runtime sweep, or Lip G/Y/R. When those are required, record the exact build gate or capture queue and keep readiness partial/blocked.

### Shared Agent Contract

Every sub-agent must receive these rules:

```txt
Read first:
- AGENTS.md
- TECH_VALIDATION_RESULT.md > Current Session Snapshot
- docs/roadmaps/active/E7_LIP_BOUNDARY_PRE_AR_CALIBRATION_SPIKE_PLAN_KO.md

Hard rules:
- lip-only
- local-only
- no upload
- no live face parsing/Core ML runtime
- no UnityFramework/Xcode/iPhone build
- do not use the rejected manual polygon lineage
- do not treat raw gold existence as M1 ready
- do not claim runtime readiness, E7.3 Green, or Lip G/Y/R
- if judgment is ambiguous, continue with `auto_provisional|pending_review|partial`, not ready
- do not revert edits made by other agents

Required final format:
- Status: ready|partial|blocked or prep_ready|partial|blocked
- Changed files
- Commands run
- Evidence/artifact paths
- Blockers
- Recommended next action
```

### Launch Sequence

Run agents in this order:

1. Spawn Evidence Agent and Dev Agent in parallel.
2. While they run, the Manager reviews untouched context only and prepares integration notes.
3. When Dev produces artifacts, spawn Scoring Agent.
4. When Scoring produces `selected_policy.json`, spawn Tester Agent.
5. Manager integrates only after Tester returns.
6. If Section 14B ends `partial_needs_review`, do not stop for missing human review. Spawn follow-up agents to create `auto_provisional` selection, coordinate preview/audit, M1 package regeneration, user-adjustment provisional review, gate matrix, missing-capture manifest, review pack, and M3A draft artifacts as long as the work remains buildless.
7. Stop on build/device/new-capture requirement and record the exact build gate or capture queue instead of continuing.

### Evidence Agent Prompt

```txt
Role: Evidence Agent
Task: Validate Section 14B inputs before generation/scoring.

Scope:
- Read the shared contract.
- Validate `evidence/references/e7-user-gold-raw-20260626/manifest.json`.
- Check file existence, dimensions, hashes, acceptedAsGold, localOnly, uploadAllowed, roles, and source lineage.
- Confirm rejected `manual_polygon_codex_visual_reference_v0` lineage is not part of the gold allowlist.
- Identify which gold sets can support mask extraction and which can only support overlay/context review.

Write scope:
- Read-only unless the Manager explicitly asks for a small validation note.

Done when:
- Return a compact readiness report with valid inputs, invalid/missing inputs, and exact blockers.
```

### Dev Agent Prompt

```txt
Role: Dev Agent
Task: Implement/run Section 14B buildless mask derivation.

Scope:
- Read the shared contract.
- Build or reuse local scripts to extract gold masks, generate candidates, overlays, contact sheet, and candidate metadata.
- Use only the user-approved gold raw set under `evidence/references/e7-user-gold-raw-20260626/`.
- Generate at least the minimum useful gold-derived candidate families from Section 14B.
- Do not overwrite raw gold files.

Write scope:
- `scripts/e7_lip_mask_derivation/` if code is needed.
- `evidence/e7-lip-mask-derivation/experiment-YYYYMMDDTHHMMSSZ/`.

Required artifacts:
- `input_manifest.json`
- `gold_extracted_masks/*.png`
- `gold_extraction_report.json`
- `candidates/<candidateId>/*.png`
- `overlays/*`
- `contact_sheet.png`
- initial `mask_derivation_scores.json` if easy; otherwise leave scoring to Scoring Agent
- `mask_derivation_summary.md`

Done when:
- Artifacts exist or the exact blocker is recorded.
- No runtime/build/device claim is made.
```

### Scoring Agent Prompt

```txt
Role: Scoring Agent
Task: Score Section 14B candidates and select a policy.

Scope:
- Read the shared contract.
- Use the latest `evidence/e7-lip-mask-derivation/experiment-*/` produced by Dev.
- Compute available Section 14B metrics, hard rejects, finalScore, scoreMargin, and unavailable metric reasons.
- Write `mask_derivation_scores.json` and `selected_policy.json`.
- If candidates are too close or signals disagree, choose `partial_needs_review`.

Write scope:
- The latest Section 14B experiment folder only.

Done when:
- `selected_policy.json` has `experimentDecision`.
- The summary names `ready_for_coordinate_pairing|partial_needs_review|blocked` and the next action.
```

### Tester Agent Prompt

```txt
Role: Tester Agent
Task: Verify Section 14B output integrity.

Scope:
- Read the shared contract.
- Check required artifacts exist.
- Validate JSON files parse.
- Search outputs for rejected lineage.
- Run `git diff --check`.
- Run focused Python compile/tests only for touched scripts.
- Do not run UnityFramework, Xcode, RN iPhone install, or device tests.

Write scope:
- Read-only unless a tiny verification note is requested.

Done when:
- Return pass/fail with exact files, commands, and residual risks.
```

### M3A Prep Agent Prompt

```txt
Role: M3A Prep Agent
Task: Prepare buildless runtime sweep artifacts only if Section 14B is already complete enough.

Scope:
- Read the shared contract and M3A section.
- Confirm whether M1/M2 outputs are actually ready. If not, mark artifacts `draft` or `blocked_by_m1_m2`.
- Prepare runtime candidate registry draft, optional source-staged validation-only Unity Resource masks, adjustment control contract, sweep evidence schema, runtime sweep checklist, prior evidence summary, and static verification summary.
- Do not build/install the app, run device tests, collect runtime evidence, or decide Lip G/Y/R.

Write scope:
- `evidence/e7-lip-runtime-sweep-prep/prep-YYYYMMDDTHHMMSSZ/` or a clearly named validation candidate prep folder.
- Only touch RN/Unity source if the Manager explicitly assigns a narrow buildless wiring patch.

Done when:
- Result is `prep_ready|partial|blocked`.
- Every candidate has `runtimeReady=false` unless later real-device evidence exists.
```

### Manager Completion Rules

The Manager must finish by writing a concise final state:

```txt
Primary Section 14B: ready_for_coordinate_pairing|partial_needs_review|blocked
M1 state: ready|partial|blocked
Optional M3A state: prep_ready|partial|blocked|not_run
Artifacts:
- ...
Commands:
- ...
Stopped because:
- completed|usage_exhausted|deadline|blocked|build_gate_required
Next exact action:
- ...
```

If app usage is exhausted before all agents finish, stop without spawning more agents and preserve the last known partial state.

### No-Stop Human Review Override

For unattended runs, missing human review is not a stop condition. Agents must:

- keep the relevant readiness `partial`;
- create an `auto_provisional` or `pending_review` artifact with exact objective tie-breaker rules;
- never write `human_reviewed`, `user_confirmed`, `M1 ready`, `runtime ready`, `E7.3 Green`, or Lip G/Y/R unless that evidence really exists;
- continue to the next buildless artifact that can reduce ambiguity or prepare the next phone/build session.

Examples:

- If two mask policies tie, select a provisional policy by coordinate compatibility, spill, hard rejects, and reproducibility, then continue.
- If user adjustment is missing, create a provisional adjustment candidate/review pack but do not mark it `user_confirmed`.
- If captures are missing, create a capture manifest/queue and mark those gates `blocked_by_missing_capture`.
- If runtime evidence is needed, create M3A draft/source-stage artifacts only and mark candidates `runtimeReady=false`.

## 25. Relationship to Other Docs

- `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`: parent E7.03 / E7.3 Q3 boundary contract.
- `E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md`: projection and UV atlas implementation detail source.
- `E7_LIP_SAMPLE_PACK_V0_RUNTIME_REVIEW_CONTEXT_KO.md`: v0 failure context and why lip boundary comes before sample expansion.
- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`: full E7 routing and E7.4 entry gate.

### Non-contract reference ideas

These sources can inspire future design and review language, but they are not Phase 2/3 inputs and do not change the gold/silver/runtime contract.

| Source | Useful idea | Not allowed as |
| --- | --- | --- |
| Twinit crawl | zone taxonomy, lip finish/texture vocabulary, future renderer requirement hints | gold mask, training data, runtime evidence, product feature commitment |
| LiveBeauty / `complete_face_version` | face diversity stress corpus idea and failure-case inspiration | lip boundary label, beauty-score model input, official ARFace atlas input, shareable evidence without license review |

This document narrows the next actionable path to `lip-first pre-AR boundary calibration`.
