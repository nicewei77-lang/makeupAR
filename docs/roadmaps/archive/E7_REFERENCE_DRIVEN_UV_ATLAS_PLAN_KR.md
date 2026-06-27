# E7 레퍼런스 기반 UV Atlas 경계 계획

일자: 2026-06-22 KST

상태: 다음 세션 구현 계획 / E7.03 region precision hardening

의도: 현재 수동 ellipse 기반 프로토타입을 `lip`, `cheek`, `eye` 경계에 대해 레퍼런스 기반, 측정 가능, 한 번의 빌드로 여러 후보를 탐색할 수 있는 UV atlas 후보 탐색 파이프라인으로 교체한다.

문서 역할:

- 이 `_KR.md` 파일은 사용자가 읽고 검토하기 위한 한국어 companion 문서다.
- 에이전트/구현용 primary context는 `E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md`다.
- 두 문서가 어긋나면 `_KO.md` 원본을 먼저 고치고, 그 결정을 이 KR companion에 반영한다.

## 1. 핵심 결정

현재 `e7-arface-authored-atlas` 구현은 진짜 authored UV atlas가 아니라 `ARFace-only manual ellipse heuristic baseline`으로 취급한다.

다음 E7.03의 주 경로는 다음과 같다.

```txt
clean synchronized capture frame + ARFace export
-> human-reviewed gold mask on that exact frame
-> ARFace projection and UV back-projection
-> per-region UV probability atlas
-> offline scoring and candidate pruning
-> one-build real-device candidate sweep
-> region G/Y/R decision
```

이 계획은 product readiness를 선언하지 않는다. 목적은 `lip`, `cheek`, `eye` 경계가 다음 cosmetic renderer 실험으로 넘어갈 수 있을 만큼 Q3 overlay-ready인지 검증하는 것이다.

## 다음 세션 수직 슬라이스

전체 P0-P9는 E7.03 mini-project roadmap이다. 다음 구현 세션에서 전체를 시도하지 않는다.

다음 세션 현실 범위:

1. P0 naming / contract reset.
2. `evidence/e7-reference-atlas/` skeleton과 manifest schema 생성.
3. synchronized capture-pair contract 확정.
4. 같은 runtime moment에서 `lip` validation pair 1개 capture: frame image, screen-space mesh, UVs, indices, blendshapes, display metadata.
5. 그 synchronized frame 위에 official `lip` gold mask 1장 작성.
6. one-frame round-trip 실행: gold mask -> UV mask -> 같은 frame에 다시 render.
7. multi-frame atlas, scorer, silver reference, runtime candidate sweep 전에 alignment 확인.

Stop rule:

- one-frame round-trip이 gold mask와 시각적으로 맞지 않으면 multi-frame probability atlas, offline scoring, Unity/RN atlas sweep, E7.03 Green claim으로 넘어가지 않는다.

## 2. 현재 상태

이미 검증된 것:

- React Native host, Unity embedded screen, ARKit face tracking, RN -> Unity recipe dispatch, Unity -> RN events, validation HUD/log 경로가 존재한다.
- 실제 iPhone에서 ARFace mesh/UV 근거가 있다. 기존 로그에서 `1220` vertices, `6912` indices, `1220` UVs가 관측됐다.
- Phase 1 Clean / Compact HUD / Full Debug 모드가 있고, 시각 검토를 위해 LogBox suppression이 추가됐다.
- Phase 2는 region candidate metadata, `candidateId`, `variantId`, topology/UV evidence fields, one-build candidate intent를 추가했다.

현재 문제:

- 현재 "atlas" 범위는 실제 grayscale UV atlas texture로 선택되는 것이 아니라 ARFace vertex 위에 face-local manual ellipse를 얹어 선택된다.
- 이 구현은 plumbing 검증용 baseline으로는 유용하지만, 사람마다 다른 semantic boundary 적응 문제를 해결하지 못한다.
- 전체 multi-candidate evidence matrix로 검증되지 않았다.

필수 보정:

- 문서와 UI에서 현재 구현을 heuristic baseline 또는 prototype으로 명확히 부른다.
- 새로운 primary path는 generated mask asset과 측정 가능한 candidate score를 가진 `reference-driven UV atlas`로 만든다.

## 3. 범위 경계

범위 안:

- `lip`, `cheek`, `eye`만 다룬다.
- representative frames, masks, logs, contact sheets, scoring CSV/JSON을 포함한 local-only validation.
- 직접 디지털 마킹, open/reference segmentation mask, offline MediaPipe landmarks, offline face parsing references, 수학적 UV projection.
- ARFace mesh/UV runtime renderer와 RN candidate sweep.
- E3/E4 baseline과 현재 manual-ellipse heuristic은 compare-only path로 보존한다.

범위 밖:

- E7.4 cosmetic renderer, E7.5 demo look, E7.6 final performance decision.
- Product-ready makeup, product-v1 readiness, M7 Green promotion.
- AI recommendation, backend upload, admin/payment/community work.
- Commercial SDK integration.
- 현재 E7.03 boundary 안에서 runtime MediaPipe, Apple Vision, face parsing integration.
- Android/ARCore implementation.
- license review 없이 restricted dataset asset을 shipping하거나 training에 사용하는 일.
- raw camera-frame을 기본 저장하거나 off-device upload하는 일.

## 4. 이해 모델

ARKit/ARFace는 face-attached coordinate system을 제공한다.

```txt
detected human face
-> ARFace mesh vertices / indices / UVs / pose / blendshapes
-> face-attached surface
```

하지만 ARFace가 semantic makeup region을 자동으로 제공하지는 않는다.

```txt
ARFace가 자동으로 알려주지 않는 것:
- 정확한 입술 색 경계
- 눈꺼풀 crease
- blush-safe cheek zone
```

빠진 레이어는 region map이다.

```txt
semantic reference
-> UV-space region atlas
-> runtime region mask
```

목표 아키텍처:

```txt
ARFace mesh and UVs
+ region UV atlas
+ threshold / feather / morphology config
+ optional blendshape adaptation
+ tracking-state visibility rules
```

### 4.1 데이터 역할 지도

예시/참고 데이터와 official atlas input을 혼동하지 않기 위해 아래처럼 구분한다.

| 데이터 유형 | 우리 앱의 synchronized ARFace mesh/UV export가 있는가? | 마킹이 있는가? | 역할 |
| --- | --- | --- | --- |
| official app `frame.png` + `arface_export.json` + human-reviewed mask | Yes | Yes | UV atlas generation과 최종 region decision용 Gold input |
| official app `frame.png` + `arface_export.json` + model-generated mask/landmark | Yes | Yes, generated | draft labeling, diagnosis, candidate assistance용 Silver reference. 단독 Green 근거 불가 |
| external dataset image + external face parsing mask | No | 보통 Yes | taxonomy/example/reference only. official ARFace UV atlas input 아님 |
| internet image, 일반 screenshot, screen-recording-only frame | No | 있을 수도 있음 | visual reference, scenario planning, practice mask 전용 |

External dataset mask가 이미 lip, eye, skin 등을 표시하더라도 그 마킹은 해당 dataset image coordinate system 기준이다. 우리 앱의 ARFace mesh에서 어떤 triangle 또는 UV coordinate가 해당 region인지 알려주지 않는다. 따라서 official gold mask는 반드시 우리 앱의 clean synchronized capture frame 위에 그려야 한다.

## 5. 레퍼런스 소스

### 5.1 Gold Reference

Gold reference는 synchronized iPhone capture frame 위에 사람이 검토한 mask를 뜻한다.

사용 목적:

- "이 위치가 메이크업 배치로 받아들일 만한가?"의 최종 판정 기준.
- MediaPipe나 face parsing을 cosmetic truth로 맹신하지 않게 막는다.
- 특히 `cheek`에서 중요하다. 공개 parsing dataset은 보통 "blush zone"을 class로 제공하지 않는다.

생성 방법:

- 기존 screen recording은 visual failure review, scenario planning, practice mask authoring 용도로만 사용한다.
- official atlas-source frame은 같은 runtime event에서 matching ARFace mesh, UVs, indices, blendshapes, display metadata가 함께 export될 때만 capture한다.
- Figma, Photoshop, Procreate, CVAT, Label Studio 또는 동등한 local annotation tool로 `lip`, `cheek`, `eye`를 디지털 마킹한다.
- frame마다 region별 binary 또는 grayscale mask를 export한다.

중요 규칙:

- mask가 UV atlas generation용 official gold mask가 되려면 해당 frame에 valid synchronized capture pair가 있어야 한다. matching ARFace export가 없는 screen-recording-only frame은 review 또는 practice에는 쓸 수 있지만 UV back-projection input으로 쓰지 않는다.
- official annotation frame은 clean해야 한다. ARFace mesh overlay, region candidate overlay, HUD/log text, debug point/triangle, makeup/beauty texture가 보이면 안 된다. Mesh/debug view는 `projected_mesh_overlay.png` 같은 별도 derived file로 export한다.

초기 최소 세트:

- `lip`: 8 to 12 frames: neutral, smile, mouth open, mouth close, pucker, yaw left/right.
- `cheek`: 6 to 10 frames: neutral, smile, yaw, pitch, partial profile.
- `eye`: 8 to 12 frames: neutral, blink, squint, wide eye, gaze direction, pitch.

Gold mask 작성 notes:

- `lip`: visible lip surface만 포함한다. teeth, inner mouth, tongue, chin, cheek, broad skin, shadow-only area는 제외한다. mouth open frame에서는 lip surface만 칠하고 열린 입 안쪽 구멍은 outside로 둔다.
- `cheek`: anatomical dataset class가 아니라 makeup placement target을 mark한다. cheek/apple area 주변 soft blush-safe zone을 우선하고, nose fold, jaw, mouth corner, under-eye dark area, hair, ear는 피한다. blush falloff를 평가할 때는 grayscale soft mask가 더 좋다.
- `eye`: eyeliner급 정밀도가 아니라 broad eyeshadow/eye tint zone이 목표다. eyeball/iris/sclera, intended eye area보다 위의 forehead, cheek, nose bridge spill, lower-face spill은 제외한다. blink frame에서는 valid zone이 더 좁을 수 있다.

### 5.2 Silver Reference

Silver reference는 최종 truth가 아니라 draft와 보조 신호로만 쓰는 model-generated mask 또는 landmark다.

허용되는 reference:

- MediaPipe Face Landmarker: landmarks, blendshapes, facial transform matrices.
- SegFace 또는 BiSeNet face parsing: lip/eye/skin pixel-level hint.
- CelebAMask-HQ와 LaPa: taxonomy 및 offline parsing reference.
- Apple Vision Face Landmarks: 선택적 iOS-native 2D contour sanity check.

규칙:

- Silver reference는 mask 제안에만 사용하고 Green 결정에는 단독 사용하지 않는다.
- raw anatomy와 makeup placement가 다르면 human review가 silver reference를 이긴다.
- 모든 generated reference에 model/source/version/license note를 기록한다.
- Silver/reference 역할을 명확히 나눈다.
  - External dataset mask는 우리 official frame 위에 다시 생성되거나 사람이 다시 authored 되기 전까지 taxonomy/example material이다.
  - 우리 official synchronized frame 위에서 생성된 model output은 UV back-projection을 도울 수 있지만, 사람이 검토해 gold로 승격하기 전까지는 silver다.

### 5.3 Shape and Product Benchmarks

authoring inspiration으로만 사용한다.

- Snap Face Mask 및 opacity texture workflow.
- TikTok Lip Effect, Lip Segmentation, Face Paint concept.
- ARCore Augmented Faces texture/mesh overlay pattern.
- Banuba/DeepAR/Perfect Corp public parameter categories는 benchmark concept으로만 참고한다.

금지:

- platform-bound template asset을 product code로 복사하지 않는다.
- Snap/TikTok UV template이 Apple ARKit UV와 동일하다고 가정하지 않는다.
- 이 validation path에서 commercial SDK를 사용하지 않는다.

## 6. 데이터 산출물

권장 local artifact layout:

```txt
evidence/e7-reference-atlas/
  README.md
  manifest.json
  capture_pairs/
    pair_lip_0001/
      frame.png
      arface_export.json
      projected_mesh_overlay.png
      round_trip_overlay.png
  frames_practice/
    from_screen_recording/
  masks_gold/
    lip/pair_lip_0001.png
    cheek/
    eye/
  masks_silver/
    mediapipe/
    parsing/
    apple_vision/
  atlases/
    v0/
      lip_probability.png
      lip_coverage.png
      lip_unknown.png
      lip_debug_votes.png
      lip_variants.json
      cheek_probability.png
      cheek_variants.json
      eye_probability.png
      eye_variants.json
  scores/
    atlas_scores.csv
    atlas_scores.json
    offline_summary.md
  contact_sheets/
    p1_frame_pack.jpg
    p6_candidate_review.jpg
  splits/
    leave_one_frame_out.json
  forward_checks/
    uv_checkerboard_projection.jpg
```

`evidence/` 아래 파일은 generated/local evidence이며, repo policy가 명시적으로 바뀌지 않는 한 commit하지 않는다.

나중에 synchronized capture-pair, one-frame round-trip, offline scoring loop를 통과한 candidate asset만 Unity source-of-truth resource로 옮길 수 있다.

핵심 capture-pair prerequisite:

- UV atlas generation에 사용할 수 있는 frame은 같은 runtime moment와 같은 display coordinate system에서 capture된 matching ARFace export가 있을 때뿐이다.
- valid atlas source pair:
  - annotation에 실제로 사용한 clean frame image,
  - 같은 pixel coordinate space로 projection된 `screenVertices`,
  - 같은 ARFace mesh에서 나온 `uvs`와 `indices`,
  - orientation, mirroring, Unity view rect, screen/video resolution, safe-area, viewport/crop, display transform metadata,
  - 같은 frame의 blendshape values.
- matching ARFace export가 없는 기존 screen recording은 visual review, scenario selection, mask-authoring practice에만 사용하고 valid UV back-projection input으로 취급하지 않는다.
- `frame.png`는 clean annotation frame이다. mesh, candidate mask, HUD/log text, debug marker, beauty texture가 들어가면 안 된다. `projected_mesh_overlay.png` 같은 derived debug file은 같은 frame 위에 mesh를 얹어 coordinate validation에만 사용한다.

## 7. Runtime Export Contract

UV atlas를 제대로 만들려면 Unity가 screen pixel을 ARFace UV로 되돌릴 수 있는 데이터를 export해야 한다.

frame별 최소 export:

```json
{
  "schemaVersion": "e7-arface-frame-export-v1",
  "frameId": "frame_0001",
  "timestampMs": 0,
  "deviceOrientation": "portrait",
  "screenWidth": 1179,
  "screenHeight": 2556,
  "videoFrameSize": [1179, 2556],
  "unityViewRectPx": [0, 0, 1179, 2556],
  "safeAreaPx": [0, 0, 1179, 2556],
  "screenCoordinateOrigin": "top-left",
  "isMirrored": true,
  "displayScale": 3.0,
  "annotationFrameClean": true,
  "hudIncludedInFrame": false,
  "meshOverlayIncludedInFrame": false,
  "candidateOverlayIncludedInFrame": false,
  "cameraImageToScreenMatrix": [16],
  "displayTransform": [16],
  "viewportCropPx": [0, 0, 1179, 2556],
  "cameraProjection": [16],
  "cameraView": [16],
  "faceLocalToWorld": [16],
  "trackingState": "Tracking",
  "vertices": [[0.0, 0.0, 0.0]],
  "indices": [0, 1, 2],
  "uvs": [[0.0, 0.0]],
  "screenVertices": [[0.0, 0.0, 1.0, 1.0]],
  "triangleVisibility": [{"triangleIndex": 0, "frontFacing": true, "visible": true}],
  "blendshapes": {
    "jawOpen": 0.0,
    "mouthSmileLeft": 0.0,
    "mouthSmileRight": 0.0,
    "eyeBlinkLeft": 0.0,
    "eyeBlinkRight": 0.0,
    "cheekSquintLeft": 0.0,
    "cheekSquintRight": 0.0
  },
  "privacy": {
    "selectedValidationFrameStored": true,
    "rawRecordingStored": false,
    "offDeviceUpload": false
  }
}
```

필수 조건:

- `vertices`, `indices`, `uvs` count가 함께 기록되어야 한다.
- `screenVertices`는 source frame과 같은 coordinate system이어야 한다.
- `videoFrameSize`, `unityViewRectPx`, `safeAreaPx`, `screenCoordinateOrigin`, `isMirrored`, `displayScale`, `displayTransform` 또는 `cameraImageToScreenMatrix`, `viewportCropPx`를 capture해야 한다.
- `annotationFrameClean`, `hudIncludedInFrame`, `meshOverlayIncludedInFrame`, `candidateOverlayIncludedInFrame`로 official annotation frame이 clean한지 명시해야 한다.
- screen-space interpolation을 쓸 경우 `screenVertices`는 perspective-correct interpolation에 필요한 depth 또는 clip-space 정보를 포함해야 한다. 가능하면 단순 depth 보정보다 `clipW` 또는 GPU-rendered triangle-id/UV buffer를 우선한다.
- export는 validation mode에서만 활성화한다.
- selected validation frame은 저장할 수 있지만 raw recording이나 continuous raw feed는 기본 저장하지 않는다.
- official atlas-source frame image는 ARFace export와 같은 runtime event에서 capture한다. matching export가 없는 screen-recording frame은 review/practice material일 뿐이다.

## 8. UV Back-Projection Algorithm

목표는 screen-space mask를 ARFace UV atlas로 누적하는 것이다.

기본 mapping:

```txt
screen pixel p
-> ARFace triangle in screen space
-> barycentric coordinate inside triangle
-> interpolated ARFace UV coordinate
-> vote into UV atlas
```

절차:

1. gold mask image와 source frame을 load한다.
2. matching ARFace export의 `screenVertices`, `indices`, `uvs`를 load한다.
3. 각 triangle에 대해 screen-space bounding box를 계산한다.
4. back-facing, occluded, active Unity view rect 밖, grazing-angle confidence threshold 미만 triangle을 reject한다.
5. bounding box 안의 pixel을 sampling한다.
6. triangle이 겹치면 depth test, triangle-id buffer 또는 동등한 visibility pass로 front-most visible triangle만 vote한다.
7. pixel이 triangle 안에 있으면 barycentric weights `(w0, w1, w2)`를 계산한다.
8. screen-space barycentric을 쓸 때는 perspective-correct interpolation을 사용한다. `clipW`가 없으면 임의 depth 보정보다 Unity-rendered UV buffer를 우선한다.
9. gold mask pixel이 region inside이면 positive vote, outside이면 negative vote를 누적한다.
10. 모든 frame을 region별로 누적해 probability atlas를 만든다.

출력:

```txt
probability(u, v) = positiveVotes(u, v) / totalVotes(u, v)
```

후처리:

- threshold로 binary mask 후보 생성.
- feather로 edge softening.
- morphology로 small hole 또는 accidental island 정리.
- unknown UV 영역은 negative로 간주하지 말고 별도 표시.
- supersampling 또는 triangle rasterization은 sparse vote 완화용이며 grazing-angle geometry 자체의 해결책으로 취급하지 않는다.
- projected triangle area 또는 `abs(normal dot viewDir)`로 sample을 weight/reject한다. silhouette와 side-facing triangle이 cheek/yaw vote를 지배하면 안 된다.
- back-facing 또는 occluded triangle은 positive/negative 모두 기여하지 않는다.
- batch atlas generation 전에 one-frame round-trip을 실행한다.
  1. synchronized `lip` frame 하나에 accepted gold mask를 작성한다.
  2. UV space로 back-project한다.
  3. 같은 mesh를 사용해 generated UV mask를 같은 frame에 다시 render한다.
  4. gold mask와 visual alignment를 비교한다.
- UV checkerboard 또는 single-triangle mask 같은 known pattern을 screen space로 forward-project해 inverse projection bug를 잡는다.

## 9. Candidate Config Contract

candidate는 코드 상수만으로 결정하지 않는다. offline output에서 runtime config로 전달한다.

예시:

```json
{
  "atlasVersion": "e7ref-v0",
  "candidates": [
    {
      "candidateId": "lip_uvatlas_v0_precision",
      "variantId": "lip-refuv-v0-p65-f02px",
      "region": "lip",
      "source": "gold-reference-uv-probability",
      "probabilityAtlas": "lip_probability_v0.png",
      "threshold": 0.65,
      "featherUvPixels": 2,
      "uvResolution": [512, 512],
      "featherUvNormalized": 0.00390625,
      "regionUvFootprint": {
        "widthPixels": 64,
        "heightPixels": 28
      },
      "morphology": "erode-one",
      "calibrationScore": {
        "precision": 0.84,
        "recall": 0.62,
        "iou": 0.56,
        "leakage": 0.11
      },
      "evalScore": null,
      "sourceFrameCount": 9,
      "goldMaskCount": 9,
      "silverReferenceCount": 0,
      "notes": "precision-biased lip candidate for first device sweep"
    }
  ]
}
```

runtime에서 반드시 log해야 하는 값:

- `candidateId`
- `variantId`
- `atlasVersion`
- `region`
- `threshold`
- `featherUvPixels`
- `featherUvNormalized`
- `uvResolution`
- `regionUvFootprint`
- `morphology`
- `sourceFrameCount`
- `goldMaskCount`
- `silverReferenceCount`
- `calibrationScore` 또는 `evalScore`
- `fallback`
- `fallbackReason`

## 10. Scoring Metrics

offline score는 region별로 다르게 해석한다.

공통 pixel metrics:

```txt
TP = candidate inside and reference inside
FP = candidate inside and reference outside
FN = candidate outside and reference inside

precision = TP / (TP + FP)
recall = TP / (TP + FN)
IoU = TP / (TP + FP + FN)
leakage = FP / candidatePositive
```

Evaluation split:

- atlas 생성에 사용한 gold mask만으로 scoring하지 않는다.
- frame 수가 적으면 leave-one-frame-out을 사용한다.
- atlas-generation frame에서 측정한 점수는 `calibrationScore`로 표시하고, held-out frame에서 측정한 점수만 `evalScore`로 표시한다.
- one-frame round-trip은 projection sanity check이지 region precision performance evidence가 아니다.

Jitter 해석:

- temporal jitter metric은 smoothing pass가 명시적으로 켜지지 않는 한 pre-smoothing metric이다.
- One Euro filtering은 future stabilization candidate이며 E7.03 atlas generation 필수 dependency가 아니다.

`lip` 우선순위:

- 가장 높은 가중치: precision과 leakage.
- skin/teeth/inner-mouth spill은 Red blocker.
- recall은 완벽하지 않아도 된다. cosmetic plausibility가 우선이다.

`cheek` 우선순위:

- hard boundary accuracy보다 soft placement.
- IoU는 낮아도 괜찮다. blush는 의도적으로 soft zone이다.
- face-attached stability와 no-hard-edge가 더 중요하다.
- soft grayscale metric을 우선한다.
  - `cheekWeightedError = mean(abs(candidateAlpha - goldSoftMask))`.
  - `cheekCenterDistance = normalized distance(candidateCentroid, goldCentroid)`.
  - `cheekHardEdgePenalty = boundaryGradientTooSharpArea`.

`eye` 우선순위:

- lower-face spill 방지.
- broad eyeshadow/eye tint가 목표이며 eyeliner-grade precision이 아니다.
- blink/squint에서는 fade/hold behavior가 mask shape만큼 중요하다.

초기 promotion threshold:

```txt
lip: precision >= 0.80, leakage <= 0.15, visual review no severe skin/teeth spill
cheek: visual soft-zone pass, leakage outside cheek envelope <= 0.25
eye: lower-face spill absent, visual broad-eye-zone pass, blink handling not severe
```

## 11. Adaptive Correction

UV atlas만으로 끝내지 않는다. 다만 adaptation은 ARFace에서 얻을 수 있는 신호부터 사용한다.

가능한 ARFace-only adaptation:

### Lip

Inputs:

- `jawOpen`
- `mouthClose`
- `mouthFunnel`
- `mouthPucker`
- `mouthSmileLeft`
- `mouthSmileRight`

동작:

- mouth open이 크면 inner-mouth/teeth spill을 피하기 위해 lower-confidence inner lip 영역을 줄인다.
- smile이 크면 mouth corner 주변 feather를 보수적으로 줄인다.
- pucker가 크면 lip center coverage를 유지하고 corner coverage를 줄인다.

### Eye

Inputs:

- `eyeBlinkLeft`
- `eyeBlinkRight`
- `eyeSquintLeft`
- `eyeSquintRight`
- gaze direction if available.

동작:

- blink가 크면 eye mask를 fade 또는 hold-last-stable로 처리한다.
- squint가 크면 upper eyelid band를 줄인다.
- lash-line precision 목표를 피한다.

### Cheek

Inputs:

- face yaw/pitch,
- face width 또는 ARFace bounding scale,
- cheek anchor/centroid,
- smile/cheek squint if reliable.

동작:

- soft broad zone을 유지한다.
- semantic segmentation보다 feather/centroid tuning을 우선한다.
- hard cheek border를 만들지 않는다.

## 12. Candidate Ladder

runtime ML로 성급하게 뛰어넘지 않기 위한 후보 ladder다.

| Level | Candidate | 역할 | Promotion rule |
| --- | --- | --- | --- |
| H0 | E3/E4 broad baseline | Compare-only | E7.03 Green 불가 |
| H1 | Current manual ellipse prototype | Heuristic baseline | 이 계획 시작 후 compare-only |
| H2 | Static reference-driven UV atlas | Primary next candidate | offline score가 H1보다 좋으면 승격 |
| H3 | UV atlas + threshold/feather variants | Primary tuning set | top variants만 runtime sweep |
| H4 | UV atlas + blendshape correction | Best ARFace-only candidate | H3가 expression에서 실패할 때 사용 |
| H5 | Offline third-party reference-assisted atlas | Offline correction path | `lip`/`eye` 실패 시 MediaPipe 또는 parsing reference 사용, Apple Vision은 E7.03에서 research-only |
| H6 | Runtime semantic hybrid POC | Future milestone only | 이 E7.03 계획 범위 밖, 사용자 승인 경계 변경 필요 |

## 13. 우선순위 구현 마일스톤

아래 순서대로 실행한다. prerequisite evidence가 없으면 낮은 우선순위 milestone을 시작하지 않는다.

| Priority | Milestone | 목표 | 빌드 필요 여부 | Stop / promote rule |
| --- | --- | --- | --- | --- |
| P0 | Contract and naming reset | 현재 atlas 상태를 명확히 만든다 | No | 현재 atlas가 heuristic baseline으로 문서/UI에 표시됨 |
| P1 | Capture-pair contract and artifact skeleton | valid atlas input을 mask 작성 전에 정의 | No | manifest가 practice frame과 official synchronized pair를 구분 |
| P2 | Synchronized `lip` capture export | official frame + ARFace export pair 1개 capture | Yes, Build Gate 후에만 | frame, mesh, UV, indices, blendshapes, display metadata가 같은 runtime moment |
| P3 | Official `lip` gold mask | synchronized frame 위에 mask 1장 작성 | No | mask dimension과 coordinate space가 captured frame과 일치 |
| P4 | One-frame round-trip | batch 작업 전 projection math 검증 | P2/P3 이후 No | gold mask -> UV -> same-frame render가 시각적으로 정렬 |
| P5 | UV atlas generator | 검증된 round-trip path 일반화 | No | probability/coverage/unknown/debug output 존재 |
| P6 | Offline scorer and optimizer | train-on-test 혼동 없이 후보 ranking | No | leave-one-frame-out 또는 split-labeled score 존재 |
| P7 | Offline silver/reference pass | runtime scope creep 없이 draft reference 추가 | No | silver reference가 non-authoritative 및 license-noted |
| P8 | Unity/RN atlas sweep implementation | frozen candidates를 한 번의 build로 실행 | Yes, candidate freeze 후에만 | 한 build에서 variants sweep과 evidence log 가능 |
| P9 | Real-device decision and escalation | region G/Y/R과 next boundary 기록 | P8 구조 실패 외 extra build 없음 | `TECH_VALIDATION_RESULT.md`에 result/limits/boundary 기록 |

### P0: Contract and naming reset

목적:

- 현재 manual ellipse 구현을 true authored atlas로 부르지 않게 한다.
- 이후 개선을 추측이 아니라 측정으로 비교하기 위해 baseline으로 보존한다.

수정 대상:

- `TECH_VALIDATION_RESULT.md`: 이 계획 실행 후 next-session result language.
- `docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md`: 에이전트용 primary implementation contract.
- `docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KR.md`: 사용자 검토용 한국어 companion.
- `rn/MakeupARValidation/App.tsx`: UI label이 true atlas처럼 보일 때만 label 수정.
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`: 필요할 경우 runtime metadata string만 수정.

필수 구현 디테일:

- precision 판단이 필요한 곳에서는 `authored atlas` 대신 `manual ellipse heuristic` 또는 `ARFace-only heuristic baseline`으로 표현한다.
- renderer identifier를 바꾸면 recipe dispatch/log가 깨질 수 있으므로 schema churn보다 display-label 변경을 우선한다.
- `e3e4-baseline`, `e7-arface-uv-candidate`, RN -> Unity recipe dispatch, Unity -> RN events, Phase 1 HUD/LogBox behavior, current evidence fields를 보존한다.

검증:

- `rg -n "authored atlas|manual ellipse|heuristic baseline|e7-arface-authored-atlas" TECH_VALIDATION_RESULT.md docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KR.md docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md rn/MakeupARValidation/App.tsx unity/MakeupARUnityValidation/Assets/Scripts`
- `rn/MakeupARValidation`에서 `./node_modules/.bin/tsc --noEmit`
- `rn/MakeupARValidation`에서 `npm run lint`

Exit criteria:

- reviewer가 baseline, 새 reference-driven atlas, future-only path를 혼동 없이 구분할 수 있다.

### P1: Capture-pair contract and artifact skeleton

목적:

- screen-recording-only frame을 UV atlas input으로 잘못 쓰지 못하게 한다.
- official mask authoring 전에 local artifact shape를 정의한다.

목표 artifact layout:

```txt
evidence/e7-reference-atlas/
  README.md
  manifest.json
  capture_pairs/
    pair_lip_0001/
      frame.png
      arface_export.json
      projected_mesh_overlay.png
      round_trip_overlay.png
  frames_practice/
    from_screen_recording/
  masks_gold/
    lip/pair_lip_0001.png
  masks_silver/
    mediapipe/
    parsing/
    apple_vision/
  atlases/
    v0/
      lip_probability.png
      lip_variants.json
      cheek_probability.png
      cheek_variants.json
      eye_probability.png
      eye_variants.json
  scores/
    atlas_scores.csv
    atlas_scores.json
  contact_sheets/
    p1_frame_pack.jpg
    p6_candidate_review.jpg
```

`manifest.json` 최소 필드:

```json
{
  "planId": "e7-reference-driven-uv-atlas",
  "atlasVersion": "e7ref-v0",
  "privacy": {
    "selectedValidationFrameStored": true,
    "rawRecordingStored": false,
    "offDeviceUpload": false
  },
  "capturePairs": [
    {
      "capturePairId": "pair_lip_0001",
      "region": "lip",
      "source": "synchronized_runtime_capture",
      "scenario": "neutral_or_talking",
      "framePath": "capture_pairs/pair_lip_0001/frame.png",
      "arfaceExportPath": "capture_pairs/pair_lip_0001/arface_export.json",
      "goldMaskPath": "masks_gold/lip/pair_lip_0001.png",
      "projectedMeshOverlayPath": "capture_pairs/pair_lip_0001/projected_mesh_overlay.png",
      "annotationFrameClean": true,
      "hudIncludedInFrame": false,
      "meshOverlayIncludedInFrame": false,
      "candidateOverlayIncludedInFrame": false,
      "status": "synced_capture_pending",
      "coordinateSpaceValidated": false,
      "roundTripStatus": "not_run"
    }
  ]
}
```

필수 구현 디테일:

- 기존 사용자 제공 녹화는 failure review, scenario planning, practice mask 용도로만 사용한다.
- official atlas input에는 stable `capturePairId`를 사용한다. timestamp만으로 artifact를 keying하지 않는다.
- frame status는 `practice_from_recording`, `synced_capture_pending`, `synced_capture_valid`, `gold_mask_accepted`, `round_trip_passed`, `rejected`를 사용한다.
- official annotation frame은 clean selected validation frame으로만 저장한다. `frame.png` 안에 mesh/HUD/candidate/debug overlay를 넣지 말고, 이런 이미지는 derived file로 분리한다.
- milestone이 명시적으로 요구하지 않는 한 raw recording은 repo 밖에 둔다.
- representative derived frame만 `evidence/` 아래에 저장하고, scoring 후 retain/delete 여부를 문서화한다.

검증:

- `python3 -m json.tool evidence/e7-reference-atlas/manifest.json`
- `find evidence/e7-reference-atlas -maxdepth 3 -type f`
- `.mov`-only frame이 `synced_capture_valid`로 표시되지 않았는지 수동 확인.
- official pair마다 region, scenario, coordinate metadata, privacy metadata가 있는지 수동 확인.
- 모든 official `frame.png`가 사람이 실제 경계를 볼 수 있을 만큼 clean하고, mesh/debug overlay가 별도 파일로 분리됐는지 수동 확인.

Exit criteria:

- 다음 세션이 어떤 frame이 practice/review material이고 어떤 synchronized pair가 valid atlas input인지 구분할 수 있다.

### P2: Synchronized `lip` capture export

목적:

- official gold mask나 atlas generation 전에 official `lip` source pair 1개를 capture한다.

빌드 정책:

- 이 milestone은 Unity/RN 변경과 real-device build가 필요할 수 있다.
- Build Gate에서 멈추고 build purpose가 `synchronized capture / one-frame round-trip`인지, runtime candidate sweep이 아닌지 명시한다.
- 이미 설치된 build가 필요한 pair를 export할 수 있으면 rebuild를 건너뛴다.

필수 구현 디테일:

- 같은 runtime moment에서 validation-only data를 export한다.
  - annotation에 사용할 clean frame image. mesh, HUD, candidate overlay, debug point, makeup texture가 없어야 한다.
  - `screenVertices`, `uvs`, `indices`,
  - vertex/index/UV counts,
  - blendshapes,
  - `videoFrameSize`, `unityViewRectPx`, `safeAreaPx`, `screenCoordinateOrigin`, `isMirrored`, `displayScale`, `displayTransform` 또는 `cameraImageToScreenMatrix`, `viewportCropPx`,
  - screen-space interpolation을 쓸 때 필요한 `clipW` 또는 equivalent perspective-correction value,
  - front-most triangle 복원을 위한 visibility data 또는 depth/triangle-id 정보.
- coordinate alignment를 확인하되 annotation frame을 오염시키지 않도록 `projected_mesh_overlay.png` 같은 derived debug file도 별도로 export한다.
- raw capture는 selected validation event로 제한한다.
- export success/failure는 기존 RN event path로 emit한다.

검증:

- export mesh를 정확히 같은 captured frame 위에 overlay한다.
- face outline, lips, eyes, key contours가 같은 pixel coordinate space에서 맞는지 확인한다.
- `frame.png` 자체는 실제 lip, eye, cheek boundary가 보일 만큼 clean한지 확인한다.
- 현재 device evidence 기준 약 `1220` vertices / `6912` indices / `1220` UVs와 count가 plausible한지 확인한다.

Exit criteria:

- `lip` pair 1개가 `synced_capture_valid` 및 `coordinateSpaceValidated=true`로 표시된다.

### P3: Official `lip` gold mask

목적:

- P2가 frame/export pair 유효성을 증명한 뒤 첫 official gold mask를 작성한다.

필수 구현 디테일:

- `.mov`-only practice frame이 아니라 `capture_pairs/pair_lip_0001/frame.png` 위에 그린다.
- `projected_mesh_overlay.png`나 mesh/debug/HUD overlay가 이미 들어간 screenshot 위에 그리지 않는다.
- captured frame과 정확히 같은 pixel dimension으로 mask를 export한다.
- teeth, inner mouth, chin, cheek, broad skin은 outside로 mark한다.
- `manifest.json`에 author, tool, date, frame id, review status를 기록한다.
- review status는 `draft`, `reviewed`, `accepted`, `rejected`만 사용한다.

검증:

- mask를 synchronized frame 위에 overlay한다.
- dimension mismatch, empty coverage, full-frame coverage, obvious coordinate offset이 있으면 reject한다.
- 실제 경계를 판단하기 어려울 정도로 mesh가 덮인 frame에서 작성한 mask는 reject한다.

Exit criteria:

- `lip` gold mask 1개가 synchronized capture pair에 대해 `accepted` 상태가 된다.

### P4: One-frame round-trip

목적:

- multi-frame atlas generation이나 scoring 전에 projection math를 증명한다.

필수 구현 디테일:

- accepted `lip` gold mask를 UV space로 back-project한다.
- 같은 mesh/export를 사용해 generated UV mask를 같은 frame 위에 다시 render한다.
- original gold mask와 비교한다.
- known UV checkerboard 또는 single-triangle pattern으로 forward-projection sanity check를 실행한다.

검증:

- `capture_pairs/pair_lip_0001/round_trip_overlay.png`를 만든다.
- mismatch 원인이 coordinate transform, mirroring, perspective interpolation, visibility/depth, grazing-angle rejection, mask authoring 중 무엇인지 기록한다.

Exit criteria:

- round-trip이 batch atlas generation을 진행할 만큼 시각적으로 정렬된다.

### P5: UV atlas generator

목적:

- 검증된 one-frame round-trip path를 UV-space probability atlas generation으로 일반화한다.

권장 script target:

- `scripts/e7_reference_atlas/generate_uv_atlas.py`

Inputs:

- `manifest.json`
- `capture_pairs/*/frame.png`
- `masks_gold/<region>/*.png`
- `capture_pairs/*/arface_export.json`
- Optional `masks_silver/**`

Outputs:

- `atlases/v0/<region>_probability.png`
- `atlases/v0/<region>_coverage.png`
- `atlases/v0/<region>_unknown.png`
- `atlases/v0/<region>_debug_votes.png`
- `atlases/v0/<region>_atlas_meta.json`

Algorithm requirements:

- `synced_capture_valid` pair만 사용한다.
- visible ARFace triangle마다 projected screen-space triangle 안의 source-frame pixel을 test한다.
- sampled pixel마다 screen space에서 barycentric coordinate를 계산한다.
- perspective-correct interpolation 또는 Unity-rendered UV/triangle-id buffer로 UV를 interpolate한다.
- front-most visible triangle에서만 vote를 누적한다.
- back-facing, occluded, tiny projected-area, grazing-angle triangle은 reject 또는 down-weight한다.
- gold mask inside이면 positive vote, outside이면 negative vote를 누적한다.
- probability는 `positiveVotes / totalVotes`로 기록한다.
- unknown UV texel은 별도 tracking한다. unknown을 조용히 negative로 처리하지 않는다.
- thin lip/eye region이 사라지지 않도록 triangle을 충분히 dense하게 supersample 또는 rasterize한다.

`<region>_atlas_meta.json` 최소 필드:

```json
{
  "atlasVersion": "e7ref-v0",
  "region": "lip",
  "sourceFrameIds": ["frame_lip_0001"],
  "goldMaskCount": 5,
  "silverReferenceCount": 0,
  "uvResolution": [512, 512],
  "positiveVoteCount": 12345,
  "negativeVoteCount": 67890,
  "unknownTexelRatio": 0.42,
  "generator": "scripts/e7_reference_atlas/generate_uv_atlas.py"
}
```

검증:

- batch mode 전에 one-frame round-trip을 실행한다.
- probability atlas를 신뢰하기 전에 `debug_votes`와 `coverage` image를 inspect한다.
- unknown region이 excluded region과 시각적으로 분리되어 있는지 확인한다.

Exit criteria:

- `lip`에 대해 valid synchronized pair 기반 probability, coverage, unknown, debug vote image가 있다.

### P6: Offline scorer and candidate optimizer

목적:

- 가능한 atlas threshold 후보를 빌드 전에 작은 runtime candidate set으로 줄이되, calibration score와 eval score를 분리한다.

권장 script target:

- `scripts/e7_reference_atlas/score_atlas_candidates.py`

Candidate sweep dimensions:

- Threshold: region-specific, 예: `0.35`, `0.45`, `0.55`, `0.65`, `0.75`.
- Feather radius: `0`, `2`, `4`, `8`, `12` UV pixels.
- Morphology: none, close-small-holes, erode-one, dilate-one.
- Region-specific clamp:
  - `lip`: high precision과 low leakage 우선.
  - `cheek`: soft coverage와 low hard-edge penalty 우선.
  - `eye`: lower-face spill 없음과 blink-safe behavior 우선.
- Evaluation split:
  - frame 수가 적으면 leave-one-frame-out을 사용한다.
  - atlas-generation frame에서 측정한 값은 `calibrationScore`로 표시한다.
  - held-out frame에서 측정한 값만 `evalScore`로 표시한다.

Outputs:

- `scores/atlas_scores.csv`
- `scores/atlas_scores.json`
- `contact_sheets/p6_candidate_review.jpg`
- `atlases/v0/runtime_candidates.json`

`runtime_candidates.json` 최소 필드:

```json
{
  "atlasVersion": "e7ref-v0",
  "candidates": [
    {
      "candidateId": "lip_uvatlas_v0_precision",
      "region": "lip",
      "probabilityAtlas": "lip_probability.png",
      "threshold": 0.65,
      "featherUvPixels": 2,
      "uvResolution": [512, 512],
      "featherUvNormalized": 0.00390625,
      "regionUvFootprint": {
        "widthPixels": 64,
        "heightPixels": 28
      },
      "morphology": "erode-one",
      "calibrationScore": {
        "precision": 0.84,
        "recall": 0.62,
        "iou": 0.56,
        "leakage": 0.11
      },
      "evalScore": null,
      "promotionReason": "best leakage-controlled lip candidate"
    }
  ]
}
```

Promotion limits:

- region별 runtime build에 올리는 variant는 2 to 4개 이하.
- region마다 conservative, balanced, 선택적으로 wide candidate를 포함한다.
- H0/H1 baseline은 compare-only path로 유지한다.

검증:

- score는 manifest/artifact에서 재현 가능해야 한다.
- contact sheet에는 source frame, gold mask, candidate overlay, false positives, false negatives가 보여야 한다.
- metric이 좋아도 cosmetically implausible하면 manual visual review가 veto할 수 있다.
- cheek candidate는 promotion 전에 `cheekWeightedError`, `cheekCenterDistance`, `cheekHardEdgePenalty`를 포함해야 한다.
- temporal jitter score는 smoothing pass가 명시적으로 켜지지 않는 한 pre-smoothing metric이다.

Exit criteria:

- runtime candidate는 constant나 train-on-test number가 아니라 재현 가능한 score와 visual review로 승격된다.

### P7: Offline silver/reference pass

목적:

- runtime ML을 도입하지 않고 optional draft reference를 추가한다.

필수 구현 디테일:

- MediaPipe, face parsing, Apple Vision output은 offline reference material로만 유지한다.
- LaPa, BiSeNet, SegFace, CelebAMask-HQ, pretrained output은 license review 전까지 reference-only다.
- 모든 silver artifact는 source, version, command/tool, license note, human review status를 기록한다.
- silver mask만으로 E7.03 Green을 결정하지 않는다.
- runtime MediaPipe, runtime Apple Vision, live face parsing, new camera session, upload, backend path를 추가하지 않는다.

Exit criteria:

- silver reference는 labeling 또는 diagnosis를 도울 수 있지만 decision authority는 gold mask로 유지된다.

### P8: Unity/RN atlas sweep implementation

목적:

- frozen, evidence-backed atlas candidate를 Unity에서 load하고 RN에서 한 번의 build로 sweep한다.

빌드 정책:

- Build Gate에서 멈추고 build purpose가 `runtime candidate sweep`임을 명시한다.
- selected runtime candidate를 모두 하나의 build에 bundle한다.
- P4가 통과하고 P6가 작은 candidate list를 freeze하기 전에는 P8을 시작하지 않는다.

Unity asset target:

- build-bundled validation asset은 `unity/MakeupARUnityValidation/Assets/Resources/E7ReferenceAtlas/<atlasVersion>/`를 우선 사용한다.
- probability PNG와 `runtime_candidates.json`을 포함한다.
- public dataset asset 또는 third-party template을 Unity asset에 복사하지 않는다.

Unity code target:

- `E3RegionMaskOverlay.cs`: true UV atlas texture sampling path 추가.
- `RNBridge.cs`: candidate/variant dispatch 수신 및 atlas evidence metadata emit.
- `FaceTrackingStatusReporter.cs`: E7 metric/event behavior 보존.

RN code target:

- `rn/MakeupARValidation/App.tsx`: face를 가리지 않도록 Compact HUD에 selected atlas candidate, variant, region 표시.

runtime metadata requirements:

- `rendererMode`
- `candidateId`
- `variantId`
- `atlasVersion`
- `region`
- `atlasSourceFrameCount`
- `goldMaskCount`
- `silverReferenceCount`
- `uvResolution`
- `threshold`
- `featherUvPixels`
- `featherUvNormalized`
- `morphology`
- `calibrationScore` 또는 `evalScore`
- `fallback`
- `fallbackReason`
- `trackingState`
- `stateAction`
- `vertexCount`
- `indexCount`
- `uvCount`

device run 전 검증:

- `rn/MakeupARValidation`에서 `./node_modules/.bin/tsc --noEmit`
- `rn/MakeupARValidation`에서 `npm run lint`
- `git diff --check`
- Unity asset path가 Unity project에 포함되어 있고 ignored build/cache folder 아래가 아닌지 확인한다.

Exit criteria:

- 설치된 앱 하나로 RN에서 `lip`, `cheek`, `eye` atlas variant를 switch하고 full evidence metadata를 emit할 수 있다.

### P9: Real-device decision and escalation

목적:

- E7.03이 Green인지, Yellow 유지인지, 다른 boundary가 필요한지 결정할 evidence를 만든다.

실행 순서:

1. 멈추고 Build Gate를 제시한다.
2. 승인 후 Unity asset/code가 바뀌었으면 repo root에서 `bash scripts/build_m3_unityframework.sh` 실행.
3. `rn/MakeupARValidation`에서 `npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK` 실행.
4. full runtime console stream을 `evidence/logs/`에 capture.
5. region/motion evidence에 필요할 때만 representative screenshot/recording capture.
6. contact sheet와 region G/Y/R note 생성.

Evidence requirements:

- runtime log에 `region_precision_atlas` 또는 동등한 atlas evidence event가 있어야 한다.
- 각 region이 promoted candidate 하나 이상에 대해 representative visual evidence를 가져야 한다.
- compare-only H0/H1 evidence는 유지하되 Green proof로 쓰지 않는다.
- FPS/frame-time은 log할 수 있지만, 이 pass에서 E7.6 performance를 promote하지 않는다.

Region decision rules:

- `lip` Green: 필수 scenario에서 severe skin/teeth/inner-mouth spill이 없어야 한다.
- `cheek` Green: soft blush zone이 face-attached이고 hard segmentation error처럼 보이지 않아야 한다.
- `eye` Green: broad eye/eyeshadow placement가 plausible하고 lower face로 spill되지 않아야 한다.
- Overall E7.03 Green은 세 region 모두 Q3 overlay-ready일 때만 가능하다.

Exit criteria:

- `TECH_VALIDATION_RESULT.md`에 command evidence, visual evidence, region G/Y/R, limitations, next boundary를 기록한다.

Escalation ladder:

1. `cheek`이 실패하면 먼저 atlas feather/centroid/shape envelope를 조정한다.
2. `lip`이 skin/teeth/inner-mouth spill로 실패하면 offline MediaPipe 또는 face parsing reference assistance를 추가한다.
3. `eye`가 blink/squint에서 실패하면 blink fade를 추가하고 runtime hybrid 제안 전에 offline landmarks/parsing을 비교한다.
4. P5/P6/P8 evidence 이후에도 ARFace-only가 실패하면 targeted runtime semantic POC를 위한 별도 boundary proposal을 작성한다.

Hard limits:

- runtime MediaPipe, Apple Vision, face parsing POC는 이 계획에서 허용하지 않는다.
- E7.03이 Green이거나 팀이 남은 E7.3 Yellow risk를 명시적으로 수용하고 `TECH_VALIDATION_RESULT.md`에 boundary를 기록하기 전까지 E7.4/E7.5/E7.6은 blocked다. Yellow risk를 수용해 넘어가더라도 이후 renderer/demo evidence는 conditional이며 full E7 visual product-readiness는 Yellow cap을 가진다.
- 이 계획으로 product-quality makeup, M7 Green, AI/backend readiness, SDK readiness, Android readiness, product readiness를 주장하지 않는다.

Escalation exit criteria:

- next boundary는 아래 중 하나다.
  - ARFace UV atlas hardening 계속.
  - offline reference-assisted correction 추가.
  - separate runtime semantic POC plan 작성.
  - recorded risk와 함께 E7.3 Yellow close.

## 14. Build Gate Contract

Unity/RN real-device build는 아래 질문에 답하기 전 시작하지 않는다.

```txt
Build question:
Build purpose: synchronized capture / one-frame round-trip / runtime candidate sweep
Primary experiment path:
Compare-only paths:
Validation contract:
Synchronized capture-pair contract:
Clean annotation frame contract:
Candidate matrix:
Expected runtime fields:
Expected visual evidence:
Out-of-scope items:
Why one build is enough:
```

이 계획에서 유효한 build question 예시:

```txt
Can this build capture one synchronized lip source pair and prove the
one-frame round-trip before any multi-frame atlas or runtime candidate sweep,
while preserving RN <-> Unity recipe/events and E3/E4 compare baselines?
```

나중에 P4와 P6가 통과한 뒤 runtime sweep build question은 다음처럼 바뀔 수 있다.

```txt
Can the frozen reference-driven UV atlas candidates keep lip, cheek, and eye
masks face-attached and semantically plausible enough for Q3 region precision
in one install, while preserving RN <-> Unity recipe/events and E3/E4 baselines?
```

## 15. Acceptance Criteria

### Offline acceptance

- 다음 세션 기준으로는 official gold mask 전에 synchronized `lip` capture pair 1개가 있어야 한다.
- official annotation `frame.png`는 clean해야 하며, mesh/HUD/candidate/debug overlay는 별도 derived file로 저장한다.
- batch atlas generation 전에 one-frame `lip` round-trip이 통과해야 한다.
- 이후 전체 E7.03 offline acceptance에는 in-scope region마다 gold reference mask pack이 필요하다.
- offline scorer가 metrics와 contact sheets를 출력한다.
- top runtime candidate는 code constant가 아니라 score와 visual review로 선택된다.
- 현재 manual ellipse candidate는 compare-only로 측정된다.
- calibration score와 held-out eval score는 분리해서 표시한다.

### Runtime acceptance

- real-device app이 rebuild 없이 selected atlas variants를 switch할 수 있다.
- Compact HUD가 recording에 충분히 명확하게 region과 atlas variant를 보여준다.
- Unity logs에 candidate, variant, atlas version, topology/UV status, region, tracking state, fallback reason이 포함된다.
- 세 region 모두 representative visual evidence가 있다.

### E7.03 decision acceptance

- region decision은 `lip`, `cheek`, `eye`로 분리한다.
- Green은 세 region 모두 Q3일 때만 가능하다.
- Yellow는 정확한 blocker와 next boundary를 이름으로 적어야 한다.
- Red는 failure가 tracking, mask representation, semantic reference, expression handling, lifecycle 중 어디에 속하는지 적어야 한다.

## 16. Test Matrix

| Region | Required scenarios | Must observe |
| --- | --- | --- |
| lip | neutral, smile, open/close, pucker, yaw | severe skin/teeth/inner-mouth spill 없음 |
| cheek | neutral, smile, yaw, pitch, near/far | soft face-attached blush zone, hard edge 없음 |
| eye | neutral, blink, squint, wide eye, gaze, pitch | broad eye zone plausible, lower-face spill 없음 |
| lifecycle | tracking, Limited/lost, recovered | fade/hold/recover behavior가 log되고 visually controlled |
| integration | recipe dispatch, event ack, HUD | Phase 1, M6, E3/E4 path regression 없음 |

## 17. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Screen recording frame에 matching ARFace export 없음 | invalid UV vote | `.mov`는 review/practice로만 사용하고 official atlas input은 synchronized capture pair만 허용 |
| External dataset mask를 official atlas input으로 오해 | invalid ARFace UV mapping | 외부 mask는 taxonomy/example로만 쓰고, 우리 synchronized frame 위에서 생성/재작성된 경우에만 후보 input으로 다룸 |
| Mesh/HUD/debug overlay가 실제 lip, eye, cheek boundary를 가림 | noisy 또는 biased gold mask | official `frame.png`는 clean하게 유지하고 mesh/debug overlay는 별도 derived file로만 export |
| Coordinate transform, mirroring, viewport, safe-area mismatch | 좋은 mask여도 round-trip 실패 | display metadata capture와 mesh overlay + one-frame round-trip을 필수화 |
| Train-on-test offline scoring | 후보 점수가 과도하게 낙관적 | leave-one-frame-out 또는 calibration/eval score 분리 |
| Perspective-incorrect UV interpolation | close/selfie geometry에서 boundary drift | `clipW` perspective-correct interpolation 또는 Unity-rendered UV/triangle-id buffer 사용 |
| Occluded/back-facing triangle vote | yaw/profile에서 atlas 오염 | front-most visible triangle만 vote하고 back-facing/occluded triangle reject |
| Grazing-angle triangle 불안정 | cheek/yaw coverage noise | projected area 또는 `abs(normal dot viewDir)` 기준 weight/reject |
| Gold mask 생성이 느림 | atlas generation 지연 | region별 5 to 10 frame으로 시작하고 silver reference를 draft로 사용 |
| Silver reference가 틀림 | 잘못된 atlas 생성 | human acceptance envelope가 model output을 override |
| ARFace projection export가 부정확 | UV atlas vote가 틀어짐 | 먼저 projected mesh over frame debug checker로 검증 |
| UV coverage가 sparse | atlas hole 발생 | valid synchronized frame을 더 누적하고 unknown region과 coverage map을 보존 |
| Lip spill 지속 | Q3 blocker | blendshape correction 후 MediaPipe/face parsing reference 추가 |
| Eye 불안정 | Q3 blocker | broad eyeshadow target으로 좁히고 blink fade 후 semantic reference 비교 |
| Cheek dataset class 부재 | target ambiguity | gold makeup placement를 수동 정의하고 soft-zone criteria 사용 |
| Runtime ML 유혹 | scope creep | ML은 targeted POC 근거가 생길 때까지 offline reference로 유지 |
| face image evidence 노출 | privacy concern | local 유지, frame 최소화, 필요 없어지면 raw recording 삭제 |

## 18. Source and License Notes

Local governance and boundary sources:

- `AGENTS.md`: repo scope, evidence policy, document rules, build loop, E7 boundary constraints, out-of-scope guardrails.
- `TECH_VALIDATION_RESULT.md`: Current Session Snapshot, E7.3 Yellow status, region G/Y/R decisions, evidence paths, stop rules, next boundary.
- `TECH_VALIDATION_TEST_PLAN.md`: stable validation/evidence contract reference only. validation contract 자체 변경이 아니면 수정하지 않는다.
- `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`: active E7.03 / E7.3 v2.1 boundary engine plan and Q3 overlay-ready acceptance standard.
- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`: E7 master spike boundary. E7.4/E7.5/E7.6을 이 계획 밖에 두기 위해서만 사용.
- `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`: E7.6 performance boundary. E7.03 evidence로 performance Green을 주장하지 않기 위해 사용.

Local research and benchmark sources:

- `docs/roadmaps/research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md`: beauty AR platform patterns, face mask / face paint / segmentation benchmark context, SDK boundary context.
- `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_GPT.md`: E7 axis 1 region tracking research synthesis.
- `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_CLAUDE.md`: E7 axis 1 second-pass region tracking synthesis.

Local session/evidence source material:

- `evidence/logs/e7-region-precision-video-analysis-2026-06-22.md`: prior screen-recording analysis와 현재 `lip` Red / `eye` Red / `cheek` Yellow 근거.
- `evidence/screenshots/e7-region-precision-video-analysis-2026-06-22/contact-sheet-1fps.jpg`: representative visual review contact sheet.
- `/Users/wiseungcheol/Downloads/ScreenRecording_06-22-2026 19-52-46_1.mov`: 사용자 제공 raw recording. local source material로만 참조하고, 필요 없이 repo에 복사하거나 파생 frame을 장기 보존하지 않는다.

External AR/runtime references:

- Unity AR Foundation `ARFace`: https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.3/manual/features/face-tracking/arface.html
- Unity face tracking platform support: https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.3/manual/features/face-tracking/platform-support.html
- MediaPipe Face Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- ARCore Augmented Faces: https://developers.google.com/ar/develop/augmented-faces
- Apple Vision `VNDetectFaceLandmarksRequest`: https://developer.apple.com/documentation/vision/vndetectfacelandmarksrequest
- Apple Vision `VNFaceLandmarkRegion2D`: https://developer.apple.com/documentation/vision/vnfacelandmarkregion2d

External beauty AR / mask workflow references:

- Snap Face Mask: https://developers.snap.com/lens-studio/4.55.1/references/guides/lens-features/tracking/face/face-effects/face-mask
- TikTok Lip Effect: https://effecthouse.tiktok.com/learn/guides/workspace/objects/face-effects/lip-effect
- TikTok Lip Segmentation: https://effecthouse.tiktok.com/learn/guides/workspace/objects/segmentation/lip-segmentation
- TikTok Face Paint: https://effecthouse.tiktok.com/learn/guides/workspace/assets/material/face-paint

External dataset / parsing references:

- CelebAMask-HQ: https://github.com/switchablenorms/CelebAMask-HQ
- LaPa dataset: https://github.com/jd-opensource/lapa-dataset
- BiSeNet face parsing: https://github.com/zllrunning/face-parsing.PyTorch
- SegFace: https://github.com/Kartik-3004/SegFace

External annotation/tooling references:

- Figma Help Center: https://help.figma.com/hc/en-us
- Adobe Photoshop Desktop Help: https://helpx.adobe.com/photoshop/desktop.html
- Procreate Handbook: https://help.procreate.com/procreate/handbook
- CVAT documentation: https://docs.cvat.ai/docs/
- Label Studio documentation: https://labelstud.io/guide/

External smoothing/math reference:

- One Euro Filter paper: https://cristal.univ-lille.fr/~casiez/1euro/

Implementation provenance:

- barycentric screen-to-UV projection, vote accumulation, scoring thresholds, candidate ladder, build-gate workflow는 이 repo를 위한 authored implementation proposal이다. 이 문서는 third-party code, model weights, dataset assets, SDKs, UV templates를 repo로 복사하지 않는다.

License policy:

- public dataset과 pretrained weights는 license review 전까지 reference-only다.
- CelebAMask-HQ는 non-commercial/research restricted로 취급한다.
- LaPa, BiSeNet, SegFace 및 generated silver output은 source license와 derivative-output constraint를 확인하기 전까지 reference-only다.
- `masks_silver/` 또는 `references/` 아래 저장되는 모든 silver artifact는 source, version, command/tool, license note, human review status를 포함해야 한다.
- commercial SDK material은 benchmark reference only다.
- explicit license clearance 없이 third-party template asset을 source code로 옮기지 않는다.

## 19. 다음 세션 체크리스트

다음 세션 시작 시 읽을 것:

1. `AGENTS.md`
2. `TECH_VALIDATION_RESULT.md` Current Session Snapshot
3. `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`
4. 이 한국어 계획서
5. `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_GPT.md`
6. `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_CLAUDE.md`
7. `docs/roadmaps/research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md`

그 다음 할 일:

1. 현재 git diff를 확인하고 current atlas implementation을 heuristic baseline으로 label한다.
2. `evidence/e7-reference-atlas/` 아래 offline artifact skeleton을 만든다.
3. 기존 recording은 scenario review/practice material로만 취급한다.
4. synchronized capture-pair contract와 manifest fields를 확정한다.
5. Unity/RN build 전 Build Gate에서 멈추고 build purpose가 synchronized capture인지 runtime sweep인지 명시한다.
6. 같은 runtime moment에서 official `lip` pair 1개를 capture한다.
7. official annotation `frame.png`가 clean하고 mesh/debug overlay가 별도 derived file인지 확인한다.
8. 그 synchronized frame 위에 official `lip` gold mask 1장을 작성한다.
9. one-frame round-trip을 실행하고 `round_trip_overlay.png`를 inspect한다.
10. round-trip gate가 통과하기 전 multi-frame atlas generation, scorer work, silver reference, runtime candidate sweep을 시작하지 않는다.

## 20. 최종 검토

이 계획은 현재 repo constraint와 대조했다.

- E7.03 / E7.3 region precision 안에 머문다.
- E3/E4 baseline, Phase 1 HUD/LogBox cleanup, RN <-> Unity events, recipe dispatch를 보존한다.
- E7.4/E7.5/E7.6, product readiness, M7 Green, AI/backend/upload, Android, commercial SDK work를 도입하지 않는다.
- MediaPipe/face parsing은 offline reference only로 다루며 runtime dependency가 아니다. Apple Vision은 future research/escalation note로만 남긴다.
- hand-tuned ellipse logic을 measurable reference-driven UV atlas path로 대체한다.
- external dataset mask는 우리 synchronized frame 위에서 생성/재작성되기 전까지 taxonomy/example로만 취급한다.
- official annotation frame은 clean해야 하며 mesh/HUD/candidate/debug overlay는 별도 derived file로 분리한다.
- official gold mask나 UV back-projection 전에 synchronized capture pair를 요구한다.
- 모든 batch atlas/scoring/runtime sweep work를 one-frame `lip` round-trip gate 뒤로 둔다.
- direct digital marking, existing mask datasets, mathematical UV projection, offline scoring, runtime candidate sweep, real-device evidence를 포함한다.
