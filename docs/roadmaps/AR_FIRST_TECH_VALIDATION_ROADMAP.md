# AR-First Technical Validation Roadmap

Date: 2026-06-20

Status: Draft / top-level planning document

Decision: A안, AR 엔진 리스크 먼저 제거

## 1. Purpose

이 문서는 AI AR Makeup Guide의 전체 기술 validation을 큰 단위로 정리한 상위 기획서다.

현재 repo의 기존 `TECH_VALIDATION_TEST_PLAN.md`는 `React Native + Unity + AR Foundation`을 iPhone 실기기에서 연동할 수 있는지 확인하는 1차 validation 계약이다. 이 문서는 그 다음 방향을 잡는다. 즉, RN-Unity 연결 가능성 확인 이후 실제 제품의 핵심 위험인 "사용자 얼굴 위에 부위별 메이크업을 실시간으로 안정적으로 적용할 수 있는가"를 검증하기 위한 상위 로드맵이다.

이 문서는 구현 세부 계획이 아니다. 이후 각 단계는 별도의 세션 계획으로 분리한다.

## 2. Current Baseline

### 2.1 Completed

현재까지 완료된 기술 validation:

| 항목 | 판정 | 근거 |
| --- | --- | --- |
| Unity와 모바일 연결 | 완료 | RN 앱이 iPhone에서 Unity 화면을 열고 Unity AR 화면이 표시됨 |
| Unity 단독 ARKit face tracking | 완료 | ARKit face tracking, front camera, diagnostic overlay 확인 |
| RN 단독 iOS 앱 실행 | 완료 | RN 앱이 iPhone 실기기에서 build/install/launch 됨 |
| UnityFramework 생성 | 완료 | Unity iOS export 및 `UnityFramework.framework` 생성 확인 |
| RN-Unity embed | 완료 | RN 안에서 full-screen Unity view 표시 |
| RN -> Unity 통신 | 완료 | RN color/opacity 변경이 Unity `RNBridge.ApplyRecipeJson`으로 전달되고 runtime log에 `recipe_applied` 출력 |

### 2.2 Not Yet Complete

현재 #2 "AR로 얼굴에 간단한 메이크업을 적용한다"는 가능성은 확인했지만 완료로 보지 않는다.

이유:

- 현재 overlay는 얼굴에 맞지 않고 위쪽/좌측으로 어긋난다.
- 현재 Unity 구현은 `layer: "lip"`을 받지만 lip만 칠하지 않는다.
- 현재 color/opacity는 진단용 face overlay material 전체에 적용된다.
- 현재 face tracking 상태는 true지만, visual alignment는 성공하지 않았다.
- 현재 second face / face reacquisition 동작은 검증되지 않았다.
- 현재 Unity -> RN 상태 이벤트는 아직 RN 화면에서 수신/표시되지 않는다.

따라서 지금 상태는 다음처럼 분리해서 판정한다.

| 영역 | 현재 판정 |
| --- | --- |
| RN-Unity 연결 | Green |
| RN -> Unity recipe 전달 | Green |
| ARKit/AR Foundation face tracking 활성화 | Green |
| 얼굴에 맞는 메이크업 overlay | Yellow/Fail |
| 부위별 메이크업 renderer | Not started |
| 실제 질감 표현 | Not started |
| AI 얼굴 분석 | Not started |
| AI 맞춤 추천 | Not started |

## 3. Strategy

선택한 전략은 A안이다.

> AR 엔진 리스크를 먼저 제거한 뒤, 메이크업 표현력과 AI 추천을 순서대로 검증한다.

이 전략을 선택하는 이유:

- 제품의 핵심 경험은 "추천" 자체가 아니라 추천된 메이크업이 실제 얼굴 위에 자연스럽게 올라가는 것이다.
- 현재 가장 큰 기술 리스크는 AI가 아니라 AR overlay 정렬과 부위별 rendering이다.
- AI 추천을 먼저 만들어도 AR renderer가 불안정하면 end-to-end demo의 실패 원인을 분리하기 어렵다.
- ARKit face mesh 기반 접근이 이미 동작 중이므로 MediaPipe 비교 실험보다 현재 Unity/AR Foundation 경로를 먼저 밀어붙이는 편이 빠르다.

## 4. Validation Principles

### 4.1 Real Device First

AR 관련 판정은 iPhone 실기기 화면, runtime log, screen recording을 기준으로 한다. Unity Editor, Simulator, 정적 screenshot만으로 Green 판정을 내리지 않는다.

### 4.2 Separate Tracking From Rendering

`Face detected: true`는 얼굴 위에 메이크업이 맞게 올라간다는 뜻이 아니다.

앞으로 모든 AR 판정은 아래 두 층을 분리한다.

| 층 | 의미 | 예시 evidence |
| --- | --- | --- |
| Tracking | ARKit/AR Foundation이 얼굴 pose/mesh를 추적하는가 | `SessionTracking`, face count, trackable ID, vertex count |
| Rendering | 추적된 얼굴 mesh 위에 시각 요소가 정확히 정렬되는가 | screen recording, frame capture, region overlay 확인 |

### 4.3 Do Not Hide AR Risk Behind AI

AI 분석/추천은 AR 메이크업 core가 최소한 안정화된 후 진행한다. AI 단계는 AR 문제를 해결하지 않는다. AI는 recipe를 만들 뿐이고, 얼굴 위에 올리는 책임은 Unity renderer에 있다.

### 4.4 Validate The Smallest Real Slice

각 단계는 제품 전체가 아니라 가장 작은 실제 slice로 검증한다.

예:

- 전체 메이크업 suite가 아니라 `lip`, `cheek`, `eye` 3개 region만 먼저 검증한다.
- 모든 질감이 아니라 matte lip, shimmer eye, soft blush 3개만 먼저 검증한다.
- 완성형 추천 엔진이 아니라 고정 catalog에서 구조화된 recipe를 생성하는지만 먼저 검증한다.

### 4.5 Evidence Before Milestone Claims

각 단계의 완료 판정은 문서 문장만으로 하지 않는다. 최소 evidence는 다음 중 2개 이상을 요구한다.

- iPhone 실기기 screen recording
- 대표 screenshot/frame capture
- runtime/device log
- source/config cross-check
- test/check command output
- 수동 관찰 메모와 재현 조건

## 5. Top-Level Roadmap

### Phase 0. Foundation Closeout

기존 RN-Unity validation을 마무리하는 단계다.

목표:

- M6 Unity -> RN 통신 완료
- M7 재진입 안정성 검증 완료
- M8 1차 기술 validation 결과 정리

필요한 이유:

- 현재 M5까지는 RN -> Unity만 검증했다.
- AR 화면 상태를 RN 앱이 알 수 있어야 이후 product UX와 debug UX를 설계할 수 있다.
- 재진입 안정성을 확인하지 않으면 실제 앱 흐름에서 Unity runtime이 위험할 수 있다.

완료 기준:

| Gate | Green 조건 |
| --- | --- |
| M6 Unity -> RN event | RN 화면에서 `unity_initialized`, `face_detected`, `recipe_applied` 수신/표시 |
| Tracking lost/recovered | 얼굴 이탈/재진입 시 RN이 상태 변화를 확인 |
| M7 re-entry | Start AR -> Close -> Start AR 3회 이상 반복 중 crash/black screen 없음 |
| Camera lifecycle | Close 후 camera indicator가 비정상적으로 유지되지 않음 |
| M8 result | 통신/연동 Green과 메이크업 visual Yellow/Fail을 분리해 기록 |

산출물:

- `TECH_VALIDATION_RESULT.md` 업데이트
- M6/M7 evidence logs
- M6/M7 screen recording 또는 screenshot
- 필요 시 runbook 보강

다음 단계 진입 조건:

- RN-Unity bidirectional messaging이 안정적으로 작동한다.
- 최소 3회 재진입에서 앱이 crash 없이 동작한다.
- 현재 face overlay 정렬 문제와 first-face-only 의심 문제를 별도 follow-up risk로 명시한다.

### Phase 1. AR Makeup Core Alignment

얼굴 추적과 visual overlay 정렬을 제품 메이크업의 기반 수준까지 끌어올리는 단계다.

목표:

- ARKit/AR Foundation face mesh가 실제 카메라 feed와 맞는 좌표계에서 렌더링되도록 수정한다.
- 진단용 full-face overlay가 얼굴 contour, 눈, 입 위치에 맞게 따라붙는지 확인한다.
- first-face-only, face reacquisition, trackable lifecycle 문제를 로그로 분리한다.

현재 가장 중요한 가설:

- runtime log에 `Camera "AR Camera" does not use a Tracked Pose Driver (Input System)` 경고가 있다.
- scene의 `AR Camera`에 pose 업데이트 구성이 부족할 가능성이 높다.
- 이 때문에 ARKit tracking은 true인데 overlay rendering이 카메라 feed와 어긋날 수 있다.

검증 항목:

| 항목 | 확인 방법 |
| --- | --- |
| Camera pose update | AR Camera pose 관련 component/config 확인 및 runtime warning 제거 |
| Face mesh alignment | 정면에서 eyes/mouth/jaw contour가 overlay와 맞는지 screen recording 확인 |
| Head rotation | 좌우/상하 회전 시 overlay가 얼굴에서 밀리지 않는지 확인 |
| Expression deformation | 입 벌림, 눈 변화 시 mesh deformation이 얼굴 위에서 일어나는지 확인 |
| Face lost/recovered | 얼굴이 화면 밖으로 나간 뒤 돌아왔을 때 같은 사람에게 다시 붙는지 확인 |
| Second face behavior | 다른 사람 얼굴을 보여줬을 때 trackable remove/add/update가 어떻게 일어나는지 로그 확인 |

완료 기준:

- `SessionTracking`과 `Face detected: true`가 runtime log에 남는다.
- AR Camera pose 관련 critical warning이 사라지거나, 남아도 visual alignment에 영향이 없음을 evidence로 설명한다.
- 30초 이상 screen recording에서 overlay가 얼굴 contour, eyes, mouth 기준으로 명확히 맞는다.
- 정면/좌회전/우회전/입 벌림/얼굴 이탈 후 재진입 시 overlay가 얼굴에 붙어 있다.
- `ARFaceManager.trackablesChanged` 기반으로 added/updated/removed event, trackable ID, vertex count, face transform을 확인할 수 있다.

Yellow 조건:

- 얼굴 정면에서는 맞지만 회전 시 밀린다.
- 최초 얼굴에는 맞지만 얼굴 이탈/재진입 또는 다른 사람 전환에서 실패한다.
- alignment는 맞지만 20fps 미만으로 떨어진다.

Red 조건:

- ARKit tracking은 true인데 Unity overlay를 카메라 feed에 맞출 수 없다.
- RN embed에서만 alignment가 깨지고 Unity 단독 앱과 결과가 크게 다르다.
- pose/camera lifecycle 문제로 재진입 후 tracking이 회복되지 않는다.

### Phase 2. Region Mask Validation

얼굴 전체 overlay가 아니라 부위별 메이크업을 적용할 수 있는지 확인하는 단계다.

목표:

- ARKit `ARFace` mesh를 기준으로 semantic region을 만든다.
- 최소 region은 `lip`, `cheek`, `eye`다.
- RN recipe의 `layer` 값이 실제 Unity rendering에서 부위별로 독립 적용되어야 한다.

권장 접근:

- 현재처럼 전체 face mesh material 하나를 칠하는 방식은 Phase 2 목표에 맞지 않는다.
- ARKit/AR Foundation `ARFace` mesh vertices/indices/UV를 기준으로 region mask를 만든다.
- 각 region은 별도 material, submesh, mask texture, shader pass 중 하나로 분리한다.
- 처음에는 정교한 화장 품질보다 "부위 분리 가능성"을 우선한다.

최소 region:

| Region | Validation 목적 |
| --- | --- |
| `lip` | 입술만 색상/opacity 적용 가능해야 함 |
| `cheek` | 양 볼에 blush 영역을 독립 적용 가능해야 함 |
| `eye` | 눈 주변/아이섀도우 영역을 독립 적용 가능해야 함 |

확장 region:

| Region | 나중에 필요한 이유 |
| --- | --- |
| `brow` | 눈썹 색/두께/가이드 |
| `nose` | 코 쉐딩/하이라이트 |
| `jaw_chin` | 턱/얼굴형 보정 가이드 |
| `full_face` | 전체 톤/가이드 overlay |

Recipe 확장 방향:

```json
{
  "layer": "lip",
  "color": "#D94B74",
  "opacity": 0.65,
  "feather": 0.2,
  "blendMode": "multiply",
  "intensity": 0.8
}
```

Phase 2에서는 모든 필드를 구현할 필요는 없다. 단, schema가 나중에 texture/recommendation 단계로 확장될 수 있어야 한다.

완료 기준:

- RN에서 `lip`, `cheek`, `eye`를 선택할 수 있다.
- 각 region별 color/opacity 변경이 1초 이내 Unity 화면에 반영된다.
- lip 변경이 cheek/eye에 번지지 않는다.
- cheek 변경이 lip/eye에 번지지 않는다.
- eye 변경이 lip/cheek에 번지지 않는다.
- 얼굴 회전과 표정 변화 중 region이 얼굴 위에서 유지된다.
- 대표 screen recording과 runtime log가 남는다.

Yellow 조건:

- region은 분리되지만 edge가 너무 딱딱하거나 약간 번진다.
- 정면에서는 동작하지만 고개 회전 시 region이 밀린다.
- 입 벌림 등 expression에서 lip region이 부자연스럽다.

Red 조건:

- ARKit face mesh 기반으로 region 분리가 불가능하다.
- region이 얼굴 움직임을 안정적으로 따라가지 못한다.
- 성능이 제품 경험 기준으로 유지되지 않는다.

### Phase 3. Texture And Product Sample Validation

색상 overlay를 넘어 실제 메이크업 질감 표현 가능성을 검증하는 단계다.

목표:

- 제품급 전체 품질이 아니라 질감 표현 가능성을 확인한다.
- 최소 3개 샘플만 만든다.
- AR renderer가 color, opacity, feather, blend, texture intensity를 표현할 수 있는지 확인한다.

최소 샘플:

| Sample | Region | 검증 목적 |
| --- | --- | --- |
| Matte Lip | `lip` | 매트 립처럼 균일하고 부드러운 입술 색 표현 |
| Shimmer Eye | `eye` | 눈 주변에 shimmer/highlight 질감 표현 |
| Soft Blush | `cheek` | 볼 영역에 feather가 있는 부드러운 번짐 표현 |

필수 조절값:

| Parameter | 목적 |
| --- | --- |
| `color` | 제품 색상 후보 표현 |
| `opacity` | 강도 조절 |
| `feather` | 경계 부드러움 |
| `blendMode` | 피부와 섞이는 방식 |
| `texture` | 질감 asset 또는 procedural texture 선택 |
| `intensity` | texture/shine 강도 |

완료 기준:

- iPhone screen recording에서 세 샘플의 질감 차이가 눈에 보인다.
- 각 샘플은 해당 region에만 적용된다.
- opacity와 intensity 변경이 시각적으로 구분된다.
- 밝은 조명/어두운 조명 또는 서로 다른 얼굴 거리에서 최소 2조건을 비교한다.
- 제품별 정확한 발색 재현은 이 단계의 완료 기준에 포함하지 않는다.

Yellow 조건:

- 질감 차이는 보이지만 피부와 합성되는 느낌이 약하다.
- 특정 조명에서만 그럴듯하다.
- feather/blend가 region edge에서 어색하다.

Red 조건:

- 질감이 단순 색상 overlay와 구분되지 않는다.
- texture 적용 시 tracking/rendering 안정성이 크게 떨어진다.
- 실시간 성능이 유지되지 않는다.

### Phase 4. AI Face Analysis Validation

사용자 얼굴 사진을 분석해 추천에 필요한 특징을 구조화하는 단계다.

목표:

- 실시간 AR camera frame이 아니라 정적 얼굴 사진 1장을 입력으로 시작한다.
- AI는 메이크업 추천에 필요한 관찰 가능한 특징만 추출한다.
- 결과는 자유 텍스트가 아니라 schema 기반 JSON이어야 한다.

분석 대상:

| Category | 예시 |
| --- | --- |
| Image quality | 조명, blur, 얼굴 가림, 얼굴 방향 |
| Face proportions | 얼굴형 추정, 상/중/하안부 비율의 대략적 관찰 |
| Eye area | 눈매, 눈꺼풀 가시성, 눈 주변 여백 |
| Lip area | 입술 두께/윤곽/추천 가능한 컬러 강도 |
| Cheek area | blush 적용 위치 후보 |
| Brow area | 눈썹 밀도/각도/가이드 필요성 |
| Nose/jaw hints | 쉐딩/하이라이트 추천에 필요한 관찰 |
| Uncertainty | 단정하기 어려운 항목과 이유 |

출력 방향:

```json
{
  "imageQuality": {
    "usable": true,
    "lighting": "soft_front",
    "issues": []
  },
  "faceFeatures": {
    "faceShapeHint": "oval",
    "eyeArea": "visible_lid_space",
    "lipArea": "medium_fullness",
    "cheekArea": "clear_application_area"
  },
  "confidence": {
    "overall": 0.78,
    "notes": ["single photo only"]
  },
  "limitations": []
}
```

주의:

- AI가 확신하지 못하는 항목은 `unknown` 또는 `low_confidence`로 남긴다.
- 민감하거나 불필요한 속성 추정은 하지 않는다.
- 피부과/의료 판단처럼 보이는 분석은 하지 않는다.
- 이 단계에서는 backend 전체 구현 없이 local prototype 또는 좁은 API prototype으로 충분하다.

완료 기준:

- 10~20장 고정 테스트 이미지에서 같은 schema의 JSON이 생성된다.
- 사람이 봤을 때 명백히 틀린 단정이 반복되지 않는다.
- image quality가 낮은 입력은 추천 불가 또는 low confidence로 처리된다.
- recommendation 단계가 사용할 수 있는 feature field가 안정적으로 나온다.

Yellow 조건:

- schema는 안정적이지만 feature 품질 편차가 크다.
- 조명/각도에 따라 결과가 크게 흔들린다.
- 일부 항목이 추천에는 아직 충분하지 않다.

Red 조건:

- 구조화 출력이 자주 깨진다.
- 얼굴 특징을 과도하게 단정한다.
- 추천에 사용할 수 없을 정도로 품질이 불안정하다.

### Phase 5. AI Recommendation Validation

AI 분석 결과를 바탕으로 메이크업 recipe를 추천하고 Unity renderer에 연결하는 단계다.

목표:

- AI가 얼굴 feature와 제한된 제품/스타일 catalog를 받아 메이크업 recipe를 만든다.
- 추천은 설명 가능해야 한다.
- 결과는 RN -> Unity -> AR renderer로 전달 가능한 구조여야 한다.

입력:

| Input | 설명 |
| --- | --- |
| `faceFeatures` | Phase 4에서 나온 얼굴 특징 JSON |
| `styleGoal` | natural, daily, bold 등 사용자가 원하는 방향 |
| `catalog` | 검증용 제품/색상/texture 후보 |
| `constraints` | 과한 색상 제외, 특정 region 제외 등 |

출력 방향:

```json
{
  "recommendationId": "demo-natural-001",
  "summary": "soft rose daily makeup",
  "layers": [
    {
      "layer": "lip",
      "color": "#D94B74",
      "opacity": 0.62,
      "texture": "matte_lip",
      "reason": "balances visible lip fullness with natural tone"
    },
    {
      "layer": "cheek",
      "color": "#E6A0A8",
      "opacity": 0.35,
      "texture": "soft_blush",
      "reason": "adds soft color without overpowering the face"
    }
  ],
  "limitations": ["single input photo"]
}
```

완료 기준:

- 추천 결과가 정해진 schema를 지킨다.
- 추천 layer가 Unity renderer에서 적용 가능한 값으로 생성된다.
- 추천 이유가 얼굴 feature와 연결된다.
- 없는 제품이나 지원하지 않는 texture를 hallucination하지 않는다.
- 최소 5개 고정 시나리오에서 recipe가 생성되고 Unity에 적용된다.

Yellow 조건:

- schema는 안정적이지만 추천 품질이 평범하다.
- 일부 추천 이유가 추상적이다.
- Unity에는 적용되지만 visual result가 아직 충분히 예쁘지 않다.

Red 조건:

- 지원하지 않는 layer/texture/color를 자주 생성한다.
- 얼굴 feature와 무관한 추천을 반복한다.
- Unity renderer가 소비할 수 없는 결과가 나온다.

## 6. MediaPipe Decision

현재 당장 MediaPipe 테스트는 하지 않는다.

이유:

- 현재 ARKit/AR Foundation face tracking 자체는 동작한다.
- 현재 문제는 landmark 수 부족보다 camera/pose alignment와 region rendering 구조에 가깝다.
- ARKit face mesh는 iOS/TrueDepth 기반 제품 경험에 충분히 강한 후보이다.
- 새 tracking stack을 추가하면 RN, Unity, native dependency, performance, debugging 복잡도가 증가한다.

MediaPipe를 다시 검토할 조건:

| Trigger | 의미 |
| --- | --- |
| ARKit mesh로 region mask 품질이 부족함 | lips/eyes/cheeks 경계가 계속 부정확한 경우 |
| Android 지원이 validation 범위에 들어옴 | ARKit-only 전략으로는 부족 |
| TrueDepth 없는 기기 지원이 필요함 | ARKit face tracking 기기 제약이 문제가 되는 경우 |
| ARKit reacquisition 문제가 해결되지 않음 | first-face-only 또는 trackable lifecycle 문제가 product UX를 막는 경우 |
| AI/vision landmark 통합이 필요함 | static analysis와 runtime AR alignment를 같은 landmark 체계로 묶어야 하는 경우 |

MediaPipe를 검토하게 되면 목표는 "교체"가 아니라 "비교 실험"이다.

비교 항목:

- landmark stability
- lip/eye/cheek region quality
- runtime FPS
- Unity integration complexity
- iOS build complexity
- RN bridge complexity
- face lost/recovered behavior

## 7. Detailed Stage Boundaries

### 7.1 What Counts As #2 Complete

기술 validation 리스트의 #2 "AR로 얼굴에 간단한 메이크업을 적용한다"는 다음 조건을 만족할 때 완료로 본다.

- RN-hosted Unity AR 화면에서 실행된다.
- ARKit/AR Foundation face tracking이 active다.
- face overlay가 실제 얼굴에 정렬된다.
- 최소 `lip`, `cheek`, `eye` 3개 region이 분리된다.
- 각 region의 color/opacity가 독립 조작된다.
- 얼굴 회전/표정/이탈 후 재진입에서 크게 깨지지 않는다.
- Unity -> RN status event가 들어온다.
- Start/Close/re-enter 3회 이상 crash가 없다.

단순히 얼굴 전체 mask 색이 바뀌는 것은 #2 완료가 아니다.

### 7.2 What Counts As #3 Complete

#3 "실제 질감을 살린 메이크업 제품 샘플 만들고 테스트"는 다음 조건을 만족할 때 완료로 본다.

- matte lip, shimmer eye, soft blush 샘플이 있다.
- 각 샘플은 region mask 위에서 동작한다.
- 색상, opacity, feather, blend, intensity 중 최소 3개 이상이 조절 가능하다.
- iPhone 화면에서 질감 차이가 확인된다.
- 제품별 완벽한 발색 재현은 요구하지 않는다.

### 7.3 What Counts As #4 Complete

#4 "AI가 사용자의 얼굴 사진을 분석해 특징을 포착한다"는 다음 조건을 만족할 때 완료로 본다.

- 정적 얼굴 사진 입력을 받는다.
- 정해진 schema의 feature JSON을 출력한다.
- image quality와 uncertainty를 함께 출력한다.
- 추천에 필요한 feature가 충분히 안정적으로 나온다.
- 낮은 품질의 입력에 대해 억지 분석을 하지 않는다.

### 7.4 What Counts As #5 Complete

#5 "포착한 특징을 바탕으로 AI가 맞춤 메이크업을 추천한다"는 다음 조건을 만족할 때 완료로 본다.

- feature JSON과 catalog를 입력으로 받는다.
- 지원 가능한 layer/texture/color만 추천한다.
- 추천 이유가 feature와 연결된다.
- 결과가 Unity recipe schema로 변환된다.
- 추천 recipe가 실제 AR renderer에서 적용된다.

## 8. Evidence Plan

모든 단계는 evidence를 남긴다.

권장 저장 위치:

| Evidence | 위치 |
| --- | --- |
| runtime/device logs | `evidence/logs/` |
| screenshots/frame captures | `evidence/screenshots/` |
| screen recordings | `evidence/screen-recordings/` |
| runbooks | `docs/runbooks/` |
| top-level roadmap | `docs/roadmaps/` |

각 세부 계획은 시작 전에 success criteria와 evidence 이름을 먼저 정한다.

예:

- `m6-unity-to-rn-events-YYYY-MM-DD.log`
- `m7-reentry-3x-YYYY-MM-DD.mp4`
- `ar-alignment-front-turn-mouth-YYYY-MM-DD.mp4`
- `region-mask-lip-cheek-eye-YYYY-MM-DD.mp4`
- `texture-samples-matte-shimmer-blush-YYYY-MM-DD.mp4`
- `ai-face-analysis-fixed-set-YYYY-MM-DD.jsonl`
- `ai-recommendation-recipe-fixed-set-YYYY-MM-DD.jsonl`

## 9. Future Planning Units

이 문서를 기준으로 이후 생성할 세부 계획 단위는 다음과 같다.

| Plan Unit | 목적 |
| --- | --- |
| M6 Unity -> RN Communication Plan | Unity 상태 이벤트를 RN에서 수신/표시 |
| M7 Re-entry Stability Plan | Unity 화면 lifecycle 안정성 검증 |
| M8 Foundation Result Plan | 1차 RN-Unity validation 결과 정리 |
| AR Alignment Plan | camera/pose/mesh 정렬 문제 해결 |
| AR Trackable Lifecycle Plan | first-face-only, lost/recovered, second face 진단 |
| Region Mask Plan | lip/cheek/eye 부위별 rendering 검증 |
| Texture Sample Plan | matte/shimmer/blush 질감 샘플 검증 |
| AI Face Analysis Plan | 정적 사진 feature extraction schema 검증 |
| AI Recommendation Plan | feature 기반 recipe 추천 및 Unity 적용 검증 |

세부 계획은 해당 세션이 시작될 때만 만든다. 완료 후 결과는 `TECH_VALIDATION_RESULT.md`에 흡수한다.

## 10. Final Decision Logic

전체 validation의 최종 의사결정은 다음 기준으로 한다.

### Green

- RN + Unity + AR Foundation 통합이 실기기에서 안정적이다.
- 얼굴 tracking과 visual alignment가 모두 성공한다.
- 최소 3개 region에 독립 메이크업 적용이 가능하다.
- 최소 3개 질감 샘플이 실시간 AR에서 구분된다.
- AI 분석/추천이 구조화된 recipe를 생성하고 Unity renderer에 연결된다.
- 핵심 flow가 재진입/얼굴 이탈/상태 이벤트까지 포함해 재현 가능하다.

### Yellow

- 핵심 flow는 가능하지만 일부 품질/안정성 문제가 남는다.
- ARKit-only 전략은 가능하나 region 품질이나 기기 제약 검토가 필요하다.
- AI 추천은 가능하지만 추천 품질이나 catalog 설계가 추가로 필요하다.
- 제품 개발은 가능하되, 다음 단계에서 추가 technical spike가 필요하다.

### Red

- RN-hosted Unity AR에서 얼굴 정렬이 해결되지 않는다.
- 부위별 region mask가 안정적으로 동작하지 않는다.
- 질감 표현이 실시간 AR에서 구분되지 않는다.
- AI 추천 결과가 renderer와 연결 가능한 구조로 나오지 않는다.
- 핵심 flow가 실기기에서 반복 재현되지 않는다.

## 11. Non-Goals

이 로드맵의 범위에 포함하지 않는 것:

- 로그인
- 결제
- 커뮤니티
- 관리자 페이지
- 제품 DB 전체 구축
- App Store 제출
- Android validation
- 완성형 추천 알고리즘
- 브랜드별 완전한 제품 발색 재현
- 실제 production backend architecture

이 항목들은 AR core와 AI recommendation validation이 Green 또는 최소 Yellow로 정리된 뒤 별도 제품 개발 계획에서 다룬다.

## 12. Immediate Next Step

현재 `TECH_VALIDATION_RESULT.md` 기준 다음 작업은 M6이다.

즉, 이 상위 로드맵을 기준으로 바로 product makeup 작업을 시작하지 않는다. 먼저 다음 순서를 따른다.

1. M6 Unity -> RN communication
2. M7 re-entry stability
3. M8 foundation validation result
4. AR alignment
5. Region mask
6. Texture sample
7. AI face analysis
8. AI recommendation

이 순서를 바꾸려면 명시적으로 milestone boundary를 바꾸고, 왜 바꾸는지 `TECH_VALIDATION_RESULT.md`에 남긴다.
