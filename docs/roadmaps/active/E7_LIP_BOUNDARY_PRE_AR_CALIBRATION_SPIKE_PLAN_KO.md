# E7 Lip-First Pre-AR Boundary Calibration Spike Plan

Last updated: 2026-06-25 KST

Status: Phase 0-3 prep bundle complete / Next implementation milestones are M1 buildless personalized lip package, M2 in-app pre-filter calibration slice, M3 runtime candidate sweep / Runtime candidate not created / E7.3 remains Yellow

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
- No real personalized lip package, runtime candidate, Unity/iPhone build evidence, or E7.3 Green decision exists yet.
- The next work is implementation, starting with M1 Buildless Personalized Lip Package v0.

Implementation map note:

- Phase 0-3 are now treated as one completed prep bundle, not as future work to keep extending.
- Future work uses only three implementation milestones:
  - M1 Buildless Personalized Lip Package v0.
  - M2 In-App Pre-Filter Calibration Slice.
  - M3 Runtime Candidate Sweep and Lip G/Y/R.
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
- Failure-mode based lip type classification required for M1 ready.
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
  failure-mode type tags
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
| Failure-mode type | required preset / stress-case selection | calibration/evaluation | Values only |
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

## 9. User Adjustment Role

사용자 조정은 실패를 감추는 꼼수가 아니라 개인차를 줄이는 필수 보정층이다.

초기 control은 네 개로 제한한다.

| Control | 의미 | 범위 제안 | Runtime 저장값 |
| --- | --- | --- | --- |
| `tightness` | 전체 lip mask를 좁히거나 넓힘 | `-1.0..1.0` | threshold/local scale |
| `upperLowerBalance` | upper/lower lip 비율 조정 | `-1.0..1.0` | upper/lower alpha bias |
| `cornerShrink` | 입꼬리 spill 줄임 | `0.0..1.0` | corner falloff |
| `verticalOffset` | 전체 mask 상하 이동 | `-1.0..1.0` | UV/local offset |

UX 원칙:

- calibration step 안에서만 노출한다.
- product onboarding처럼 꾸미지 않는다.
- 자유 드로잉 UI부터 만들지 않는다.
- 조정값은 local validation artifact로만 다룬다.
- 서버 업로드나 사용자 프로필 저장은 금지한다.

## 10. Failure-mode Type Classification

유형 분류는 demographic classification이 아니다. 사용자를 인종/성별/민감 특성으로 분류하지 않는다.

분류 대상은 관찰 가능한 failure mode다.

필수 lip tags:

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

이 tag는 아래 목적으로만 쓴다.

- 어떤 preset을 먼저 보여줄지 선택.
- 어떤 stress test를 꼭 볼지 결정.
- evaluation matrix에서 실패 원인을 분리.
- future held-out test set을 구성.

Initial `LipPresetProfile` selection is driven by these tags: `thin_lip -> thin`, `full_lip -> full`, `wide_smile_stretch/asymmetric_corners -> wide`, `low_skin_lip_contrast/facial_hair_or_shadow/strong_lighting_shadow/pre_applied_lip_color -> soft-edge`, and `mouth_open_teeth_visible -> inner-safe`.

## 11. Pre-AR Calibration UX

Calibration은 짧고 반복 가능해야 한다.

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
  tightness, upperLowerBalance, cornerShrink, verticalOffset

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

Phase 1에서 만들 화면은 product onboarding이 아니라 AR 진입 전 validation capture tool이다. 사용자는 짧은 단계별 prompt를 보고 정면/표정/고개 움직임을 수행하고, 앱은 각 단계마다 clean camera frame과 같은 순간의 ARFace export를 묶어 local capture record를 만든다.

| Step | Capture id prefix | User action | UI state | Required capture rule | Pass/fail gate |
| --- | --- | --- | --- | --- | --- |
| 1. Face ready | `lip_ready` | 얼굴을 화면 중앙에 둠 | tracking/face/mesh 상태만 표시 | 저장하지 않아도 됨 | `tracking=Tracking`, `faceCount=1`, mesh counts available |
| 2. Neutral | `lip_neutral` | 입을 자연스럽게 닫고 정면 응시 | clean preview + tiny status | clean frame + same-moment ARFace export | baseline lip boundary seed |
| 3. Open-close | `lip_open_close` | 입을 살짝 열고 닫음 | 1-2 short captures or mini-burst | closed/open representative frames 중 최소 1개 저장 | inner-mouth/teeth exclusion seed |
| 4. Smile | `lip_smile` | 자연스럽게 웃음 | corner status visible | smile-stretched frame + ARFace export | corner stretch/corner spill check |
| 5. Pucker | `lip_pucker` | 입술을 오므림 | required capture state | pucker frame + ARFace export | central contraction check; missing이면 M1 partial |
| 6. Yaw | `lip_yaw_left` / `lip_yaw_right` | 좌/우 중 하나 이상 고개 회전 | pose direction visible | one yaw frame + ARFace export | side/corner projection stability check |
| 7. Auto preview | `lip_preview` | 후보 경계 확인 | `lip-tight-auto-v0` / `lip-safe-v0` 비교 | raw frame 저장 없이 derived preview만 생성 | severe spill 여부 확인 |
| 8. User adjustment | `lip_adjusted` | 4개 slider로 미세 보정 | Full Debug에서 값 표시 | params only; no free-draw mask | `lip-tight-user-v0` params 확정 |
| 9. Save package | `lip_calib` | local package 저장 | package id/path 표시 | derived package + summary only | `rawFrameStored=false`, `offDeviceUpload=false` |

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
| User adjustment params | adjusted/save steps | `userAdjustment` | M1 ready에는 `user_confirmed` 필요. `tightness`, `upperLowerBalance`, `cornerShrink`, `verticalOffset`, plus status showing whether zero values are user-confirmed or only assumed. |
| Extension slots | package-level only | `extensions.cheek`, `extensions.eye` | 현재는 `reserved_only`; cheek/eye 알고리즘을 시작하지 않는다. |

## 12. Calibration Data Package

Calibration output은 화면 픽셀 좌표가 아니라 runtime에서 재사용 가능한 face-space data다.

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
        "tightness": 0,
        "upperLowerBalance": 0,
        "cornerShrink": 0,
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
      "failureModeType",
      "blendshapeSnapshot"
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
    "failureModeType": "required_classified_for_m1_ready",
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
- `timestamp`, `frame`, `viewport`, and `coordinateSpaces` are projection safety fields, not cosmetic metadata. If these are absent, same-moment capture may exist but coordinate-space trust is still partial.
- `faceParsing=unavailable|required_not_run` 또는 `visionLipContour!=available`이면 M1은 `partial` 또는 `blocked`이며 ready가 아니다.
- `colorGradientConfidence!=computed`, `userAdjustment.status!=user_confirmed`, `failureModeType!=classified`, `blendshapeSnapshot!=available`, or missing `pucker`이면 M1은 `partial` 또는 `blocked`이며 ready가 아니다.
- `status=ready_for_boundary_fusion`은 Phase 2가 reference signal fusion을 시작할 수 있다는 뜻이지 E7.3 Green이 아니다.
- `status=ready_for_uv_projection`은 Phase 3 one-frame round-trip / UV atlas 준비가 가능하다는 뜻이지 runtime quality evidence가 아니다.
- `offlineCandidateConfigs` are Phase 3 projection artifacts only. They are not Unity-installed runtime candidates. A later runtime slice must record a separate `runtimeCandidateStatus` such as `installed_in_unity|tested_on_device|rejected`.
- `userAdjustment.status=default_zero_assumed` or `not_implemented` must not be described as a user-confirmed adjustment. This distinction matters most for `lip-tight-user-v0`.

## 13. Boundary Fusion Model

Phase 2의 목적은 완성된 lip mask를 만드는 것이 아니라, Phase 1 package를 읽어 어떤 신호를 채택/거절하고 어떤 candidate를 Phase 3로 넘길지 결정 가능하게 만드는 것이다.

Local contract stub:

```txt
python3 scripts/e7_lip_boundary_fusion/prepare_fusion_summary.py \
  path/to/lip-calib-YYYYMMDD-HHMMSS-v0.json \
  --output-dir /tmp/e7-lip-fusion
```

이 stub은 `fusionSummary.json` / `fusionSummary.md` contract를 만든다. 실제 `screenLipReferenceMask` image, face parsing mask, Core ML output, UV atlas, runtime texture는 만들지 않는다.

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
| Failure-mode type | Yes | classified validation type/preset with source reason | missing keeps M1 partial/blocked |
| Blendshape snapshot | Yes | available jaw/smile/pucker/funnel values or explicit exporter support | missing keeps M1 partial/blocked |

우선순위:

1. Human-reviewed gold mask.
2. Face parsing lip labels, silver until reviewed.
3. Apple Vision lip contour.
4. ARFace UV/vertex topology.
5. Color/gradient confidence.
6. User adjustment.
7. Failure-mode type preset.
8. Blendshape / face-state correction.

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
- User adjustment is required for M1 ready and is applied last as scalar parameters: `tightness`, `upperLowerBalance`, `cornerShrink`, `verticalOffset`.
- Failure-mode type classification and blendshape/face-state signals are required before M1 ready; if unavailable, the result remains partial with exact missing reasons.
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
| `lip-tight-auto-v0` | neutral + smile/yaw + accepted gold/silver/reference mask + required Vision/parsing/color/failure/blendshape signals | tight outer contour, conservative color confidence, no user bias | reject color-only edges; partial if any required M1 signal is missing |
| `lip-tight-user-v0` | `lip-tight-auto-v0` + user-confirmed adjustment params | applies tightness, upper/lower balance, corner shrink, vertical offset | partial if adjustment is not explicitly user-confirmed; does not override inner-mouth exclusion |
| `lip-safe-v0` | open_close + accepted pucker + inner-mouth exclusion + corner falloff + required Vision/parsing reference signals | smaller spill-prevention mask; accepts under-coverage before teeth/skin spill | partial if any required M1 signal is missing; wins only after failure-mode evidence supports it |

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
        "tightness": 0,
        "upperLowerBalance": 0,
        "cornerShrink": 0,
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
      "failure_mode_type_preset"
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

The first Phase 3 projection sanity proof may run with a manual mask, but M1 ready must wait for every required M1 signal: Apple Vision, local/offline face parsing, color/gradient, user-confirmed adjustment, failure-mode type, pucker, blendshape/face-state, accepted/gold reference, coordinate/visibility, held-out/eval, and split/exclusion/falloff evidence. Projection-only proof without those signals is partial.

Minimum path:

1. Use one neutral same-moment capture pair.
2. Generate required comparison masks/signals: manual or accepted screen-space mask, local face parsing silver mask, Apple Vision outer/inner lips contour rasterization, and existing `lip_ring` mesh draft for review only.
3. Human-review the overlay.
4. Save `lip_reference_mask.png` and `lip_reference_mask.meta.json`.
5. The metadata must include `maskSource`, `reviewedBy`, `capturePairId`, `coordinateSpace`, `imageWidth`, `imageHeight`, `acceptedSignalIds`, and `knownWeaknesses`.

Manual polygon gold/reference is allowed for the first coordinate-space proof because the goal is `screen mask -> ARFace UV -> round-trip`, not face-parsing model validation.

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
- `rejectedSignalReasons`: missing/low-confidence Vision, unavailable face parsing, missing color/gradient, unconfirmed user adjustment, missing failure-mode type, missing blendshape/face-state, color-only edge, missing ARFace field, privacy flag violation, or missing pucker.
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
- No accepted human-reviewed lip gold mask exists yet.
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
| `userAdjustmentBias` | initial bias for the four Section 9 scalars: `tightness`, `upperLowerBalance`, `cornerShrink`, `verticalOffset` | user-adjustment namespace |
| `maskDerivationNote` | candidate-generation notes such as feather tendency, coverage tendency, confidence warning, or inner-mouth exclusion strength | candidate-generation namespace |

`featherTendency` and `coverageTendency` here are draft-stage notes, not the Section 15 runtime `coverage` / `feather` tuning controls.

| Preset profile | `userAdjustmentBias` | `maskDerivationNote` | Candidate preference |
| --- | --- | --- | --- |
| `thin` | `tightness` positive | conservative coverage tendency | start with `lip-tight-auto-v0` |
| `full` | `tightness` negative | coverage-friendly draft tendency, still bounded by accepted reference mask | start with `lip-tight-auto-v0` |
| `wide` | `cornerShrink` lower | preserve wider corner range if no spill is observed | start with `lip-tight-auto-v0`; review corners |
| `soft-edge` | no required scalar bias | lower confidence warning; feather tendency only | require review before promotion |
| `inner-safe` | `cornerShrink` higher | stronger inner-mouth exclusion | prefer `lip-safe-v0` |

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
  tightness
  upperLowerBalance
  cornerShrink
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
- Create or accept one `lip_reference_mask.png`; manual polygon annotation is allowed for the first proof.
- Produce Apple Vision lip contour artifacts and metadata for the same frame. If Vision is unavailable or low confidence, M1 remains partial/blocked with the exact reason.
- Produce local/offline face parsing lip/skin/mouth artifacts and metadata for the same frame. If parsing is unavailable, M1 remains partial/blocked with the exact reason.
- Produce color/gradient confidence artifacts, user-confirmed adjustment params, failure-mode classification, pucker capture, and blendshape/face-state evidence. If any are unavailable, M1 remains partial/blocked with the exact reason.
- Generate a real `fusionSummary.json` / `fusionSummary.md` for this capture.
- Run the buildless UV round-trip stub and produce `lip_probability.png`, `lip_coverage.png`, `lip_unknown.png`, `lip_debug_votes.png`, `lip_variants.json`, `round_trip_overlay.png`, `summary.json`, and `summary.md`.
- Keep `lip_variants.json` as offline configs with `runtimeReady=false`.

Acceptance:

- The overlay shows whether the personalized mask lands in the correct coordinate space.
- Apple Vision contour status is `available`; otherwise M1 is not ready.
- Face parsing status is `silver` or `human_reviewed_gold`; otherwise M1 is not ready.
- Color/gradient is `computed`, user adjustment is `user_confirmed`, failure-mode type is classified, pucker capture is accepted, and blendshape/face-state values are available; otherwise M1 is not ready.
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
- Add the four minimal adjustment controls only: `tightness`, `upperLowerBalance`, `cornerShrink`, `verticalOffset`.
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
4. Provide one accepted/reference `lip_reference_mask.png` on the same frame; manual polygon annotation is allowed for the first proof.
5. Produce required Apple Vision lip contour artifacts and required local/offline face parsing artifacts for the same frame; if either is unavailable, M1 remains partial/blocked with exact reasons.
6. Produce required color/gradient confidence, user-confirmed adjustment params, failure-mode classification, pucker capture, and blendshape/face-state artifacts; if any are unavailable, M1 remains partial/blocked with exact reasons.
7. Generate a real `fusionSummary.json` / `fusionSummary.md` for this input.
8. Run `python3 scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py ...` in buildless mode.
9. Produce offline package artifacts only: lip_probability, lip_coverage, lip_unknown, lip_debug_votes, lip_variants with offlineCandidateConfigs/runtimeReady=false, round_trip_overlay, summary.
10. If inputs are insufficient, record `ready|partial|blocked` and the exact missing input; do not invent masks or fake artifacts.
11. Stop before UnityFramework/Xcode/iPhone build unless the user approves the M2 build gate.

Decision:
Do not mark E7.3 Green. Record whether M1 is ready / partial / blocked, and name the next concrete step: implement/run Apple Vision, implement/run local face parsing, compute color/gradient, confirm user adjustment, classify failure mode, capture pucker/blendshape evidence, fix mesh draft, create/reference-approve mask, fix fusion summary, fix UV projection, or proceed to M2 build gate only after all M1 gates pass.
```

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
