# E7 Lip-First Pre-AR Boundary Calibration Spike Plan

Last updated: 2026-06-25 KST

Status: Phase 0 document contract complete / Active E7.03 / E7.3 lip-first boundary calibration planning contract

## 0. One-line Decision

이번 스파이크는 **AR 화면이 뜬 뒤 매 프레임 무거운 모델을 돌리는 방식이 아니라, AR 진입 전에 가능한 신호를 모두 모아 사용자별 lip boundary map을 만들고, runtime에서는 ARFace mesh/UV 위에서 가볍게 추적하는 구조**를 검증한다.

핵심 문장:

```txt
AR 전에 무겁게 분석한다.
AR 중에는 가볍게 붙인다.
고정 대상은 화면 픽셀이 아니라 ARFace UV/vertex 좌표다.
```

이번 문서는 구현 계약이다. 바로 E7.3 Green, E7.4 cosmetic rendering, 제품 품질, AI/backend/upload, commercial SDK, Android, live face parsing runtime을 승인하지 않는다.

Phase 0 completion note:

- This planning contract exists and is routed from `TECH_VALIDATION_RESULT.md` and `docs/roadmaps/README.md`.
- Phase 0 is documentation-only; it does not include code, build, runtime, or device evidence.
- The next actionable boundary is the first buildless implementation slice: data contract / synchronized lip capture or reuse / one-frame round-trip preparation.

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
- Apple Vision lip contour의 reference/calibration 역할.
- Face parsing lip/skin/mouth labels의 silver reference 역할.
- Color/gradient confidence helper.
- User adjustment controls.
- Failure-mode based lip type classification.
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
  optional face parsing mask
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
| Apple Vision lip landmarks | iOS-native 2D contour hint | calibration/offline | No by default |
| Face parsing | pixel-level semantic lip/skin/mouth reference | offline/calibration | No |
| Color/gradient | boundary confidence helper | calibration/offline | No |
| User adjustment | 마지막 개인화 보정 | calibration | Values only |
| Failure-mode type | preset / stress-case 선택 | calibration/evaluation | Values only |
| Blendshape / face state | 가벼운 expression correction | runtime | Yes, lightweight |

## 6. Apple Vision Role

Apple Vision은 Vision Pro가 아니라 iOS/macOS의 computer vision framework다. 이 계획에서는 `VNDetectFaceLandmarksRequest` 같은 face landmarks 계열을 **lip contour hint**로 본다.

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
Apple Vision = calibration/reference 신호
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
Face parsing = silver semantic reference
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

Pucker는 가능하면 포함하지만, 시간 제한이 있으면 deferred로 표시한다.

## 12. Calibration Data Package

Calibration output은 화면 픽셀 좌표가 아니라 runtime에서 재사용 가능한 face-space data다.

Required shape:

```json
{
  "schemaVersion": "e7-lip-boundary-calibration-v0",
  "calibrationId": "lip-calib-YYYYMMDD-HHMMSS",
  "region": "lip",
  "sourceCapturePairIds": ["pair_lip_neutral_0001"],
  "lipBoundaryVersion": "lip-calibrated-uv-v0",
  "runtimeCandidateIds": [
    "lip-tight-auto-v0",
    "lip-tight-user-v0",
    "lip-safe-v0"
  ],
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
    "userAdjustmentParams": {
      "tightness": 0,
      "upperLowerBalance": 0,
      "cornerShrink": 0,
      "verticalOffset": 0
    }
  },
  "confidenceSummary": {
    "visionContour": "available",
    "faceParsing": "silver_or_unavailable",
    "colorGradient": "helper_only",
    "humanReview": "pending"
  },
  "privacy": {
    "rawFrameStored": false,
    "offDeviceUpload": false
  }
}
```

Notes:

- `rawFrameStored=false`는 long-term package 기준이다. Calibration 중 local frame을 잠깐 만들 수 있지만, official evidence만 남기고 raw frame batch는 삭제한다.
- `sourceCapturePairIds`는 evidence traceability를 위해 남긴다.
- `faceParsing=silver_or_unavailable`은 face parsing이 없더라도 plan이 막히지 않게 한다.

## 13. Boundary Fusion Model

우선순위:

1. Human-reviewed gold mask.
2. Face parsing lip labels, silver until reviewed.
3. Apple Vision lip contour.
4. ARFace UV/vertex topology.
5. Color/gradient confidence helper.
6. User adjustment.
7. Failure-mode type preset.

Fusion rule:

```txt
ARFace topology defines where runtime can attach.
Gold/silver/reference signals define what should count as lip.
User adjustment corrects the final practical boundary.
Color/gradient only changes confidence, never wins alone.
```

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
- Reject or down-weight back-facing, occluded, tiny projected-area, and grazing-angle triangles.
- Count votes only from front-most visible triangles.
- Treat low-vote UV regions as unknown, not negative.
- Run one-frame round-trip before batch atlas generation.
- Do not treat one-frame round-trip as Q3 runtime evidence.

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

## 15. Runtime Lightweight Tracking

Runtime must stay light.

Runtime inputs:

- ARFace mesh vertices/indices/UVs.
- selected lip candidate id.
- selected mask texture.
- user adjustment params.
- lightweight expression signals if available.
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

- FPS/frame-time when available.
- recipe latency.
- mesh vertex/index/uv counts.
- candidate id.
- fallback flag.
- tracking state.

## 20. Evidence Plan

Buildless evidence:

- `git diff --check`.
- If RN changes happen later: `npm test -- --runInBand --watchman=false`, `./node_modules/.bin/tsc --noEmit`, `npm run lint`.
- If projection scripts change later: Python compile check.

Offline evidence:

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

Recommended future implementation order:

1. Create this doc and route it from the result snapshot.
2. Add data-contract stubs for `lip-calibrated-uv-v0`.
3. Create or reuse one synchronized lip capture pair.
4. Produce one human-reviewed lip gold mask on that frame.
5. Run one-frame round-trip.
6. Generate `lip-tight-auto-v0`, `lip-tight-user-v0`, and `lip-safe-v0` candidate config.
7. Add runtime candidate selection without changing broad baseline.
8. Add minimal user adjustment controls.
9. Run one-build / many-candidate runtime sweep.
10. Record lip G/Y/R and next boundary.

Do not skip steps 3-5 and jump straight to runtime candidate claims.

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
Implement the first buildless slice of the E7.03 lip-first pre-AR boundary calibration spike.

Scope:
- lip only
- preserve E3/E4 baseline, smooth-region-mask, 3-layer RN payload, and existing bridge behavior
- do not start E7.4/E7.5/E7.6
- do not add live face parsing/Core ML runtime
- do not upload or persist raw camera frames by default

Preferred first slice:
1. Add a local candidate/config contract for lip-calibrated-uv-v0.
2. Add or verify a one-frame lip round-trip input path from a synchronized capture pair.
3. Produce offline artifacts only: lip_probability, lip_variants, summary.
4. If code changes are needed, run buildless checks first.
5. Stop before UnityFramework/Xcode/iPhone build unless the user approves the build gate.

Decision:
Do not mark E7.3 Green. Record only whether the lip-first calibration path is continue / revise / stop.
```

## 25. Relationship to Other Docs

- `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`: parent E7.03 / E7.3 Q3 boundary contract.
- `E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md`: projection and UV atlas implementation detail source.
- `E7_LIP_SAMPLE_PACK_V0_RUNTIME_REVIEW_CONTEXT_KO.md`: v0 failure context and why lip boundary comes before sample expansion.
- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`: full E7 routing and E7.4 entry gate.

This document narrows the next actionable path to `lip-first pre-AR boundary calibration`.
