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
reference masks
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

초기 최소 세트:

- `lip`: 8 to 12 frames: neutral, smile, mouth open, mouth close, pucker, yaw left/right.
- `cheek`: 6 to 10 frames: neutral, smile, yaw, pitch, partial profile.
- `eye`: 8 to 12 frames: neutral, blink, squint, wide eye, gaze direction, pitch.

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
  frames/
    practice_from_recording/
    synced/
  masks/
    gold/
      lip/
      cheek/
      eye/
    silver/
      mediapipe/
      face-parsing/
  arface-export/
    frame_0001.arface.json
    frame_0001.preview.png
  atlas/
    lip_probability_v0.png
    cheek_probability_v0.png
    eye_probability_v0.png
    lip_mask_v0.png
    cheek_mask_v0.png
    eye_mask_v0.png
  candidates/
    e7_atlas_candidates_v0.json
  scores/
    offline_scores.csv
    offline_summary.md
    contact_sheet_lip.jpg
    contact_sheet_cheek.jpg
    contact_sheet_eye.jpg
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
  - annotation에 실제로 사용한 frame image,
  - 같은 pixel coordinate space로 projection된 `screenVertices`,
  - 같은 ARFace mesh에서 나온 `uvs`와 `indices`,
  - orientation, mirroring, Unity view rect, screen/video resolution, safe-area, viewport/crop, display transform metadata,
  - 같은 frame의 blendshape values.
- matching ARFace export가 없는 기존 screen recording은 visual review, scenario selection, mask-authoring practice에만 사용하고 valid UV back-projection input으로 취급하지 않는다.

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
  "hudIncludedInFrame": false,
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
    "rawCameraFrameStored": false,
    "offDeviceUpload": false
  }
}
```

필수 조건:

- `vertices`, `indices`, `uvs` count가 함께 기록되어야 한다.
- `screenVertices`는 source frame과 같은 coordinate system이어야 한다.
- `videoFrameSize`, `unityViewRectPx`, `safeAreaPx`, `screenCoordinateOrigin`, `isMirrored`, `displayScale`, `displayTransform` 또는 `cameraImageToScreenMatrix`, `viewportCropPx`를 capture해야 한다.
- screen-space interpolation을 쓸 경우 `screenVertices`는 perspective-correct interpolation에 필요한 depth 또는 clip-space 정보를 포함해야 한다. 가능하면 단순 depth 보정보다 `clipW` 또는 GPU-rendered triangle-id/UV buffer를 우선한다.
- export는 validation mode에서만 활성화한다.
- raw camera frame은 기본 저장하지 않는다.
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
4. bounding box 안의 pixel을 sampling한다.
5. pixel이 triangle 안에 있으면 barycentric weights `(w0, w1, w2)`를 계산한다.
6. UV를 `uv = w0 * uv0 + w1 * uv1 + w2 * uv2`로 interpolate한다.
7. gold mask pixel이 region inside이면 positive vote, outside이면 negative vote를 누적한다.
8. 모든 frame을 region별로 누적해 probability atlas를 만든다.

출력:

```txt
probability(u, v) = positiveVotes(u, v) / totalVotes(u, v)
```

후처리:

- threshold로 binary mask 후보 생성.
- feather로 edge softening.
- morphology로 small hole 또는 accidental island 정리.
- unknown UV 영역은 negative로 간주하지 말고 별도 표시.

## 9. Candidate Config Contract

candidate는 코드 상수만으로 결정하지 않는다. offline output에서 runtime config로 전달한다.

예시:

```json
{
  "atlasVersion": "e7ref-v0",
  "candidates": [
    {
      "candidateId": "lip_uvatlas_v0_precision",
      "region": "lip",
      "source": "gold-reference-uv-probability",
      "probabilityAtlas": "lip_probability_v0.png",
      "threshold": 0.65,
      "featherUvPixels": 2,
      "morphology": "erode-one",
      "scoreSummary": {
        "precision": 0.84,
        "recall": 0.62,
        "iou": 0.56,
        "leakage": 0.11
      },
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
- `morphology`
- `sourceFrameCount`
- `goldMaskCount`
- `silverReferenceCount`
- `scoreSummary`
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

`lip` 우선순위:

- 가장 높은 가중치: precision과 leakage.
- skin/teeth/inner-mouth spill은 Red blocker.
- recall은 완벽하지 않아도 된다. cosmetic plausibility가 우선이다.

`cheek` 우선순위:

- hard boundary accuracy보다 soft placement.
- IoU는 낮아도 괜찮다. blush는 의도적으로 soft zone이다.
- face-attached stability와 no-hard-edge가 더 중요하다.

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
| P1 | Evidence pack and artifact layout | 반복 가능한 local input을 만든다 | No | frames, metadata, mask slots가 stable id를 가짐 |
| P2 | Gold mask authoring | 사람이 검토한 target mask 생성 | No | 각 region이 first scoring에 충분한 gold mask를 가짐 |
| P3 | Offline silver/reference pass | runtime scope creep 없이 draft mask/landmark 추가 | No | silver reference가 non-authoritative로 표시됨 |
| P4 | ARFace projection export | frame과 맞는 screen-space mesh/UV data capture | Yes, Build Gate 후에만 | export가 frame/mask id와 매칭됨 |
| P5 | UV atlas generator | frame mask를 UV-space probability atlas로 변환 | export 이후 No | region별 atlas PNG/JSON/debug overlay 존재 |
| P6 | Offline scorer and optimizer | threshold/feather/morphology 후보 ranking | No | top variants가 metric + visual review로 선택됨 |
| P7 | Unity/RN atlas sweep implementation | 한 번의 빌드로 selected candidates 실행 | Yes, candidate freeze 후에만 | 한 build에서 variants sweep과 evidence log 가능 |
| P8 | Real-device decision pass | region G/Y/R과 next boundary 기록 | P7 구조 실패 외 extra build 없음 | `TECH_VALIDATION_RESULT.md`에 result/limits/boundary 기록 |
| P9 | Escalation decision | ARFace-only 지속 가능성 판단 | No | runtime semantic POC는 future/user-approved only |

### P0: Contract and naming reset

목적:

- 현재 manual ellipse 구현을 true authored atlas로 부르지 않게 한다.
- 이후 개선을 추측이 아니라 측정으로 비교하기 위해 baseline으로 보존한다.

수정 대상:

- `TECH_VALIDATION_RESULT.md`: 이 계획 실행 후 next-session result language.
- `docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KR.md`: 한국어 구현 계약.
- `docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md`: 원문/병행 문서.
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

### P1: Evidence pack and artifact layout

목적:

- frame extraction, mask authoring, ARFace export matching, atlas generation, scoring을 재현 가능하게 만든다.

목표 artifact layout:

```txt
evidence/e7-reference-atlas/
  README.md
  manifest.json
  frames/
    frame_lip_0001.png
    frame_cheek_0001.png
    frame_eye_0001.png
  masks_gold/
    lip/frame_lip_0001.png
    cheek/frame_cheek_0001.png
    eye/frame_eye_0001.png
  masks_silver/
    mediapipe/
    parsing/
    apple_vision/
  arface_exports/
    frame_lip_0001.json
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
  "sourceRecording": "/Users/wiseungcheol/Downloads/ScreenRecording_06-22-2026 19-52-46_1.mov",
  "privacy": {
    "rawCameraFrameStored": false,
    "offDeviceUpload": false
  },
  "frames": [
    {
      "frameId": "frame_lip_0001",
      "region": "lip",
      "timestampSec": 20.35,
      "scenario": "neutral_or_talking",
      "framePath": "frames/frame_lip_0001.png",
      "goldMaskPath": "masks_gold/lip/frame_lip_0001.png",
      "arfaceExportPath": "arface_exports/frame_lip_0001.json",
      "status": "needs_gold_mask"
    }
  ]
}
```

필수 구현 디테일:

- 기존 사용자 제공 녹화를 먼저 사용한다. missing scenario가 `lip`, `cheek`, `eye` 판단을 막을 때만 새 녹화를 요청한다.
- stable frame id를 사용한다. timestamp만으로 artifact를 keying하지 않는다.
- milestone이 명시적으로 요구하지 않는 한 raw recording은 repo 밖에 둔다.
- representative derived frame만 `evidence/` 아래에 저장하고, scoring 후 retain/delete 여부를 문서화한다.

검증:

- `python3 -m json.tool evidence/e7-reference-atlas/manifest.json`
- `find evidence/e7-reference-atlas -maxdepth 3 -type f`
- 각 selected frame에 region, scenario, source timestamp, privacy metadata가 있는지 수동 확인.

Exit criteria:

- 다음 세션이 입력 조건을 다시 묻지 않고 manifest만으로 frame/mask/atlas/scoring 작업을 재실행할 수 있다.

### P2: Gold mask authoring

목적:

- 현재 validation footage 위에서 시각적으로 허용 가능한 makeup placement의 truth source를 만든다.

최소 frame target:

| Region | First-pass minimum | Preferred target | Required scenario spread |
| --- | --- | --- | --- |
| lip | 5 frames | 8 to 12 frames | neutral, smile/talking, mouth open/close, yaw |
| cheek | 4 frames | 6 to 10 frames | neutral, smile, yaw, pitch or near/far |
| eye | 5 frames | 8 to 12 frames | neutral, blink/squint, wide eye, pitch/gaze |

mask authoring rules:

- `lip`: visible lip surface를 포함한다. teeth, inner mouth, chin, cheek, broad skin은 제외한다. vermilion border 밖 feather는 makeup-plausible할 때만 허용한다.
- `cheek`: anatomical segmentation class가 아니라 soft blush-safe zone을 mark한다. cheekbone/apple area 주변 oval/gradient placement를 우선한다. hard dataset-style border는 필요 없다.
- `eye`: eyeliner-grade lash precision이 아니라 broad eyeshadow/eye tint zone이 목표다. lower face, cheek, nose bridge spill, forehead spill은 제외한다.

필수 구현 디테일:

- Gold mask는 Figma, Photoshop, Procreate, CVAT, Label Studio 또는 local equivalent로 그릴 수 있다.
- source frame과 같은 pixel dimension으로 mask를 export한다.
- region/frame마다 binary 또는 grayscale mask 하나를 사용한다.
- `manifest.json`에 author, tool, date, frame id, review status를 기록한다.
- review status는 `draft`, `reviewed`, `accepted`, `rejected`만 사용한다.

검증:

- 각 gold mask를 source frame 위에 overlay하고 `contact_sheets/p2_gold_masks.jpg`를 만든다.
- source frame과 dimension이 다른 mask는 reject한다.
- empty alpha/white coverage 또는 full-frame accidental coverage는 reject한다.

Exit criteria:

- 각 region에 first-pass offline scoring을 실행할 만큼 accepted gold mask가 있다.

### P3: Offline silver/reference pass

목적:

- runtime ML을 도입하지 않고 manual effort를 줄이고 failure mode를 드러낸다.

허용 reference signal:

- MediaPipe Face Landmarker output: offline landmarks/blendshapes/face transform hints.
- BiSeNet/SegFace-style face parsing output: offline lip/eye/skin hints.
- Apple Vision face landmarks: optional 2D contour sanity check only.
- CelebAMask-HQ와 LaPa: license review 전까지 taxonomy/reference dataset only.

필수 구현 디테일:

- generated output은 모두 `masks_silver/` 또는 `references/` 아래에 저장한다.
- source name과 version을 알 수 있으면 모든 silver artifact에 prefix로 남긴다.
- metadata에 `referenceAuthority: "silver"`를 추가한다.
- silver mask만으로 E7.03 Green을 결정하지 않는다.
- runtime MediaPipe, runtime Apple Vision, live face parsing, new camera session, upload, backend path를 추가하지 않는다.

검증:

- manifest에 source, version, command/tool, license note, human-reviewed 여부가 기록된다.
- visual review에서 silver output이 맹신 대상이 아니라 draft로만 유용하다는 점을 확인한다.

Exit criteria:

- silver reference는 comparison 또는 pre-labeling에 사용 가능하지만, decision authority는 gold mask로 유지된다.

### P4: ARFace projection export

목적:

- screen pixel을 ARFace UV로 되돌릴 정확한 mapping data를 capture한다.

빌드 정책:

- 이 milestone은 처음으로 Unity/RN build가 필요할 수 있다.
- 시작 전 반드시 Build Gate에서 멈춘다.
- 이미 설치된 build가 필요한 export를 지원하면 rebuild를 건너뛴다.

Unity 수정 대상:

- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- overlay class가 복잡해지는 경우에만 작은 validation-only exporter class를 추가한다.

RN 수정 대상:

- `rn/MakeupARValidation/App.tsx`: export trigger 또는 export status 표시용 toggle/button이 필요할 때만.

`arface_exports/<frameId>.json` 최소 필드:

```json
{
  "frameId": "frame_lip_0001",
  "capturedAtUnixMs": 1780000000000,
  "rendererMode": "manual-ellipse-heuristic-baseline",
  "trackingState": "Tracking",
  "region": "lip",
  "screen": {
    "width": 1179,
    "height": 2556,
    "orientation": "portrait"
  },
  "mesh": {
    "vertexCount": 1220,
    "indexCount": 6912,
    "uvCount": 1220,
    "hasStableUv": true,
    "screenVertices": [[512.1, 1204.7, 0.93]],
    "uvs": [[0.42, 0.58]],
    "indices": [0, 1, 2]
  },
  "blendshapes": {
    "mouthSmileLeft": 0.0,
    "jawOpen": 0.0,
    "eyeBlinkLeft": 0.0
  },
  "privacy": {
    "rawCameraFrameStored": false,
    "offDeviceUpload": false
  }
}
```

필수 구현 디테일:

- validation mode에서만 export한다.
- 짧은 `exportSchemaVersion`을 포함한다.
- frame 위에 mesh overlay를 그릴 수 있을 만큼 screen projection data를 포함한다.
- export success/failure는 기존 RN event path로 log한다.
- export size를 제한한다. selected frame 또는 short capture window만 사용하고, continuous raw capture는 기본 금지한다.

검증:

- export된 `screenVertices`와 `indices`를 matching frame 위에 overlay한다.
- UV vote에 사용하기 전에 mesh outline이 얼굴을 따라가는지 확인한다.
- 현재 device evidence 기준 약 `1220` vertices / `6912` indices / `1220` UVs와 count가 맞는지 확인한다.

Exit criteria:

- region별 accepted gold frame 중 최소 하나가 visually aligned ARFace export를 가진다.

### P5: UV atlas generator

목적:

- accepted screen-space region mask를 UV-space probability atlas로 변환한다.

권장 script target:

- `scripts/e7_reference_atlas/generate_uv_atlas.py`

Inputs:

- `manifest.json`
- `frames/*.png`
- `masks_gold/<region>/*.png`
- `arface_exports/*.json`
- Optional `masks_silver/**`

Outputs:

- `atlases/v0/<region>_probability.png`
- `atlases/v0/<region>_coverage.png`
- `atlases/v0/<region>_unknown.png`
- `atlases/v0/<region>_debug_votes.png`
- `atlases/v0/<region>_atlas_meta.json`

Algorithm requirements:

- visible ARFace triangle마다 projected screen-space triangle 안의 source-frame pixel을 test한다.
- sampled pixel마다 screen space에서 barycentric coordinate를 계산한다.
- triangle UV로부터 UV를 interpolate한다.
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

- batch mode 전에 frame 하나로 generator를 먼저 실행한다.
- probability atlas를 신뢰하기 전에 `debug_votes`와 `coverage` image를 inspect한다.
- unknown region이 excluded region과 시각적으로 분리되어 있는지 확인한다.

Exit criteria:

- 각 region에 accepted gold mask 기반 probability atlas와 metadata가 있다.

### P6: Offline scorer and candidate optimizer

목적:

- 가능한 atlas threshold 후보들을 빌드 전에 작은 runtime candidate set으로 줄인다.

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
      "morphology": "erode-one",
      "offlineScore": {
        "precision": 0.84,
        "recall": 0.62,
        "iou": 0.56,
        "leakage": 0.11
      },
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

Exit criteria:

- Unity/RN build 전에 runtime candidate set이 freeze된다.

### P7: Unity/RN atlas sweep implementation

목적:

- frozen UV atlas candidate를 Unity에서 load하고 RN에서 한 번의 build로 sweep한다.

빌드 정책:

- Unity/RN real-device build 전 Build Gate에서 멈춘다.
- selected runtime candidate를 모두 build에 bundle해서 rebuild 없이 여러 candidate를 탐색한다.

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
- `morphology`
- `offlineScoreSummary`
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

### P8: Real-device decision pass

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

### P9: Escalation decision

목적:

- reference-driven ARFace UV atlas가 Q3에 도달하지 못할 때 다음 선택지를 결정한다.

Decision ladder:

1. `cheek`이 실패하면 먼저 atlas feather/centroid/shape envelope를 조정한다.
2. `lip`이 skin/teeth/inner-mouth spill로 실패하면 offline MediaPipe 또는 face parsing reference assistance를 추가한다.
3. `eye`가 blink/squint에서 실패하면 blink fade를 추가하고 runtime hybrid 제안 전에 offline landmarks/parsing을 비교한다.
4. P5/P6/P8 evidence 이후에도 ARFace-only가 실패하면 targeted runtime semantic POC를 위한 별도 boundary proposal을 작성한다.

Hard limits:

- runtime MediaPipe, Apple Vision, face parsing POC는 이 계획에서 허용하지 않는다.
- E7.03이 Green이거나 팀이 남은 Yellow risk를 명시적으로 수용하기 전까지 E7.4/E7.5/E7.6은 blocked다.
- 이 계획으로 product-quality makeup, M7 Green, AI/backend readiness, SDK readiness, Android readiness, product readiness를 주장하지 않는다.

Exit criteria:

- next boundary는 아래 중 하나다.
  - ARFace UV atlas hardening 계속.
  - offline reference-assisted correction 추가.
  - separate runtime semantic POC plan 작성.
  - recorded risk와 함께 E7.3 Yellow close.

## 14. Build Gate Contract

Unity/RN real-device build는 아래 질문에 답하기 전 시작하지 않는다.

```txt
Build question:
Primary experiment path:
Compare-only paths:
Validation contract:
Candidate matrix:
Expected runtime fields:
Expected visual evidence:
Out-of-scope items:
Why one build is enough:
```

이 계획에서 유효한 build question 예시:

```txt
Can the reference-driven UV atlas candidates keep lip, cheek, and eye masks
face-attached and semantically plausible enough for Q3 region precision,
while preserving RN <-> Unity recipe/events and E3/E4 compare baselines?
```

## 15. Acceptance Criteria

### Offline acceptance

- in-scope region마다 gold reference mask pack이 최소 하나 있다.
- offline scorer가 metrics와 contact sheets를 출력한다.
- top runtime candidate는 code constant가 아니라 score와 visual review로 선택된다.
- 현재 manual ellipse candidate는 compare-only로 측정된다.

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
| Gold mask 생성이 느림 | atlas generation 지연 | region별 5 to 10 frame으로 시작하고 silver reference를 draft로 사용 |
| Silver reference가 틀림 | 잘못된 atlas 생성 | human acceptance envelope가 model output을 override |
| ARFace projection export가 부정확 | UV atlas vote가 틀어짐 | 먼저 projected mesh over frame debug checker로 검증 |
| UV coverage가 sparse | atlas hole 발생 | 더 많은 frame 누적, triangle supersampling, unknown region 보존 |
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
2. 첫 frame pack source를 결정한다. 기존 recording 먼저, missing scenario가 blocker일 때만 새 recording.
3. `evidence/e7-reference-atlas/` 아래 offline artifact layout을 만든다.
4. representative frame을 추출하고 frame id를 정의한다.
5. gold/silver mask generation workflow를 만들거나 scaffold한다.
6. reference pack shape가 명확해진 뒤에만 ARFace projected mesh export instrumentation을 추가한다.
7. Build Gate가 만족되기 전 Unity/RN build를 시작하지 않는다.

## 20. 최종 검토

이 계획은 현재 repo constraint와 대조했다.

- E7.03 / E7.3 region precision 안에 머문다.
- E3/E4 baseline, Phase 1 HUD/LogBox cleanup, RN <-> Unity events, recipe dispatch를 보존한다.
- E7.4/E7.5/E7.6, product readiness, M7 Green, AI/backend/upload, Android, commercial SDK work를 도입하지 않는다.
- MediaPipe/face parsing은 offline reference only로 다루며 runtime dependency가 아니다. Apple Vision은 future research/escalation note로만 남긴다.
- hand-tuned ellipse logic을 measurable reference-driven UV atlas path로 대체한다.
- direct digital marking, existing mask datasets, mathematical UV projection, offline scoring, runtime candidate sweep, real-device evidence를 포함한다.
