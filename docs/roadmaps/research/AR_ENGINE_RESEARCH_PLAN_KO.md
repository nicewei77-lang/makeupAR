# AR Makeup Engine Research Plan - 한국어 버전

Date: 2026-06-20

Status: 리서치 계획 / 구현 전 단계

Primary path decision: Yellow - Unity + AR Foundation + ARKit 경로를 1순위로 유지한다. 다만 iPhone 실기기에서 alignment, trackable lifecycle, region mask 검증이 통과되기 전까지 제품 수준의 makeup rendering은 시작하지 않는다.

Current note: this document was written before the M8 closeout. For current milestone status and next boundary, use `../../../TECH_VALIDATION_RESULT.md` first. As of M8, M0-M6 are Green, M7 is Yellow / skipped by decision / risk accepted, and the next primary gate is E1 AR Alignment unless additional M7 verification is chosen.

## 1. Current Boundary and Non-Goals

이 문서는 제품용 메이크업 렌더링을 구현하기 전에, AR makeup engine을 어떤 구조로 조사하고 설계할지 결정한다. 현재 기술 검증 milestone 순서를 대체하지 않는다.

현재 경계:

- `TECH_VALIDATION_RESULT.md` 기준 M5는 완료되었고, 다음 milestone은 M6인 Unity -> RN communication이다.
- `TECH_VALIDATION_TEST_PLAN.md`는 계속 안정적인 검증 계약으로 유지한다.
- `docs/roadmaps/strategy/AR_FIRST_TECH_VALIDATION_ROADMAP.md`는 AR alignment와 region mask 검증 전에 M6/M7/M8을 먼저 닫으라고 정리한다.
- 현재 AR makeup readiness는 Green이 아니다. RN -> Unity communication은 Green이고 ARKit face tracking은 동작하지만, 얼굴에 정확히 붙는 visual makeup은 Yellow/Fail 상태다.

이 리서치 문서의 non-goals:

- RN, Unity, shader, AI, backend, admin, payment, community, product code를 구현하지 않는다.
- M6/M7/M8을 완료 처리하지 않는다.
- 유료 상용 beauty SDK를 도입하지 않는다.
- dataset/model은 허용된 비상업 research 또는 educational 조건 안에서만 사용한다.
- 제한이 있는 research asset을 출시, 판매, 재배포하거나 상용 product asset처럼 사용하지 않는다.
- 상용 품질의 makeup rendering, 제품 수준 color matching, 전체 makeup suite coverage를 시도하지 않는다.

엔진에 영향을 주는 제품 요구사항:

- 앱은 최종적으로 사용자의 얼굴 위에 추천 메이크업을 실시간으로 적용해야 한다.
- 사용자가 조절할 수 있는 값은 color, range, texture, intensity, opacity, feather, blend mode, position, size다.
- 첫 엔진 slice는 제품 비전보다 작게 유지한다. v1은 `lip`, `cheek`, `eye`만 다룬다.
- AR engine은 구조화된 `MakeupRecipe` 데이터를 소비해야 한다. 이후 AI/recommendation layer는 recipe를 만들고, Unity가 rendering 결과를 책임진다.

Repo evidence:

- `TECH_VALIDATION_RESULT.md`는 다음 milestone이 M6라고 기록하고, 현재 screen state에서 product makeup work를 시작하면 안 된다고 명시한다.
- `TECH_VALIDATION_RESULT.md`는 현재 overlay offset, first-face-only/reacquisition risk, Unity -> RN status display 미구현 상태를 기록한다.
- `docs/product/AIAR_MakeupGuide기획서_v1.md`는 목표 AR makeup guide, editable parameters, half-face guide mode, supported makeup categories를 정의한다.
- `docs/roadmaps/strategy/AR_FIRST_TECH_VALIDATION_ROADMAP.md`는 AR-first strategy와 `lip`/`cheek`/`eye` minimum region slice를 정의한다.

## 2. Current Evidence and Open Risks

### Current Green Evidence

| Area | Evidence | Meaning |
| --- | --- | --- |
| RN iOS host | `rn/MakeupARValidation/App.tsx`가 RN home screen에서 full-screen `UnityView`를 연다. | RN host가 AR surface에 진입할 수 있다. |
| RN -> Unity message path | `App.tsx`가 `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)`을 보낸다. | recipe-like 값이 Unity까지 도달할 수 있다. |
| Unity receiver | `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`가 `ApplyRecipeJson(string)`을 노출한다. | Unity가 들어오는 color/opacity JSON을 parse할 수 있다. |
| AR Foundation stack | `TECH_VALIDATION_RESULT.md`가 AR Foundation 6.3.5와 ARKit XR Plug-in 6.3.5를 기록한다. | 현재 stack은 validation baseline과 맞다. |
| Real-device tracking | M5 evidence log가 `SessionTracking`, face count 1, `Face detected: true`를 기록한다. | iPhone에서 ARKit face tracking이 활성화되어 있다. |

### Current Yellow/Fail Evidence

| Risk | Current evidence | Research consequence |
| --- | --- | --- |
| Visual overlay is offset | `TECH_VALIDATION_RESULT.md`는 colored mask가 위/왼쪽으로 밀리고 eyes, mouth, jaw, face contour에 맞지 않는다고 기록한다. | region mask나 texture sample 전에 AR alignment를 먼저 해결해야 한다. |
| Camera pose warning | Runtime log가 `Camera "AR Camera" does not use a Tracked Pose Driver (Input System)` 경고를 기록한다. | 현재 AR Foundation 6.3 scene setup과 AR camera setup을 비교해야 한다. |
| First-face-only / reacquisition risk | 현재 log는 face count를 세지만 added/updated/removed trackable ID를 식별하지 않는다. | 제품 UX를 가정하기 전에 trackable lifecycle logging이 필요하다. |
| Whole-face material only | `RNBridge.cs`는 color/opacity를 overlay material과 현재 `ARFace` renderer에 적용한다. | region-specific renderer는 현재 material-only approach 위에 바로 만들 수 없다. |
| `layer` is not honored | RN은 `layer: "lip"`을 보내지만 Unity는 전체 diagnostic overlay에 적용한다. | `MakeupRecipe.layer`에는 실제 region dispatch contract가 필요하다. |
| Unity -> RN status missing | native proxy에는 `sendMessageToMobileApp` path가 있지만 RN은 Unity status event를 아직 표시하지 않는다. | UI-visible AR state를 위해 M6이 선행되어야 한다. |
| Bridge reproducibility caveat | 성공한 M4/M5 run은 아직 package-local `node_modules` timing patch와 generated framework sync에 의존한다. | Engine research는 lifecycle과 artifact reproducibility를 risk로 유지해야 한다. |

### Current Scene/Source Clues

| File | Current shape | Implication |
| --- | --- | --- |
| `unity/MakeupARUnityValidation/Assets/Editor/MakeupARValidationSetup.cs` | `AR Session`, `XR Origin`, `Camera Offset`, `AR Camera`, `ARCameraManager`, `ARCameraBackground`, `ARFaceManager`를 만든다. | 이 generated hierarchy를 official AR Foundation scene setup과 AR camera pose requirement에 비교해야 한다. |
| `MakeupARValidationSetup.cs` | `faceManager.requestedMaximumFaceCount = 1`을 설정한다. | one-face behavior는 의도일 수 있지만 lost/recovered와 second-face transition은 event log로 별도 확인해야 한다. |
| `RNBridge.cs` | `layer`, `color`, `opacity`를 parse하고 opacity clamp와 material alpha blending을 적용한다. | message contract seed로는 유용하지만 region renderer는 아니다. |
| `FaceTrackingStatusReporter.cs` | AR session state, camera direction, face support, face count를 log한다. | 이후 session에서 `trackablesChanged`, tracking state, trackable ID, vertex count, face transform을 추가하는 방식으로 확장한다. |

## 3. Public Source Inventory

### Official Runtime Path

| Source | What it says | Use in this repo |
| --- | --- | --- |
| [Unity AR Face Manager 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/arfacemanager.html) | `ARFaceManager`는 face GameObject를 만들고, `trackablesChanged`, face prefab, `Maximum Face Count`를 제공한다. | M6 이후 status와 reacquisition diagnosis의 핵심 lifecycle event로 `trackablesChanged`를 사용한다. |
| [Unity AR Face 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/arface.html) | `ARFace` lifecycle은 added/updated/removed이며, face는 `Limited` 상태가 될 수 있고 mesh data는 vertices, normals, indices, UVs를 포함할 수 있다. | `trackingState`, mesh vertices/indices/UVs, `ARFace.updated`를 alignment와 region mask의 기반으로 사용한다. |
| [Unity Face Tracking Samples 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/samples/features/face-tracking.html) | official sample은 face pose, face mesh, ARKit blend shapes, eye poses, ARCore-only face regions를 포함한다. | custom face/lifecycle code를 만들기 전에 reference scene으로 사용한다. |
| [Unity Camera Components 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/camera/camera-components.html) | AR scene은 `ARCameraManager`와 `ARCameraBackground`를 사용하고, facing direction은 user/front camera가 될 수 있다. | renderer math를 디버깅하기 전에 현재 AR Camera hierarchy와 background rendering을 확인한다. |
| [Unity as a Library iOS](https://docs.unity3d.com/Manual/UnityasaLibrary-iOS.html) | UnityFramework는 embedded runtime control, pause, unload, `sendMessageToGOWithName`을 지원한다. 알려진 제한으로 full-screen-only rendering과 single Unity runtime instance가 있다. | AR screen을 full-screen으로 유지하고 unload/re-enter behavior를 M7 validation risk로 취급한다. |
| [`@azesmway/react-native-unity`](https://github.com/azesmway/react-native-unity) | iOS는 built `UnityFramework`를 사용하고, `postMessage`, `onUnityMessage`, `unloadUnity`, `pauseUnity`를 지원하며, iOS view dimensions가 non-zero여야 한다고 경고한다. | validation bridge로 계속 사용하되, clean reinstall을 신뢰하기 전에 local timing/framework-sync caveat를 durable하게 정리한다. |

### Tracking Alternatives

| Source | What it says | Decision |
| --- | --- | --- |
| [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) | 3D face landmarks, blendshape scores, facial transformation matrices를 출력하고 image, video, live stream mode와 complete face mesh를 지원한다. | primary implementation path가 아니라 fallback/comparison candidate로 유지한다. |
| [ARCore Augmented Faces](https://developers.google.com/ar/develop/augmented-faces) | specialized hardware 없이 center pose, three region poses, 468-point 3D face mesh를 제공한다. | Android/fallback reference로 사용한다. 현재 iOS ARKit validation path에서 전환할 이유는 아니다. |

MediaPipe 또는 ARCore 비교 실험으로 넘어가는 fallback trigger:

- RN-hosted Unity에서 ARKit/AR Foundation alignment를 고칠 수 없다.
- ARKit mesh/UV가 안정적인 `lip`, `cheek`, `eye` region mask에 부족하다.
- lifecycle fix 이후에도 face lost/recovered 또는 second-face reacquisition이 product UX를 막는다.
- Android validation이 active scope에 들어온다.
- static AI analysis와 runtime AR이 ARKit만으로 공유하기 어려운 landmark topology를 필요로 한다.

### Makeup Texture and Region References

Project-use note:

- 이 프로젝트는 상업 출시용 앱이 아니라 부트캠프 research/education prototype이다.
- non-commercial research, teaching, scientific publication, personal experimentation을 허용하는 dataset/model repo는 이 repo의 research validation에 사용할 수 있다.
- dataset/model을 사용하면 citation/attribution note를 함께 남긴다.
- upstream terms가 명시적으로 허용하지 않는 한 restricted dataset, derived dataset copy, pretrained weight를 재배포하지 않는다.
- public launch, App Store submission, paid demo, commercial use 전에 license를 다시 검토한다.

| Source | What it contributes | License/use constraint |
| --- | --- | --- |
| [CelebAMask-HQ](https://github.com/switchablenorms/CelebAMask-HQ) | 30,000장 high-resolution face image와 skin, nose, eyes, brows, mouth, lip, hair 등을 포함하는 19개 mask class를 제공하는 face parsing reference다. | dataset agreement를 지키는 조건에서 이번 부트캠프 범위의 non-commercial research/educational use로 사용할 수 있다. 판매, 재배포, 상용 product asset 사용은 금지한다. |
| [LaPa Dataset](https://github.com/jd-opensource/lapa-dataset) | 22,000장 이상의 이미지, 11-category label, 106-point landmark를 제공하는 face parsing reference다. | license terms를 지키는 조건에서 이번 부트캠프 범위의 non-commercial research, teaching, publication, personal experimentation으로 사용할 수 있다. 상용 출시 전에는 재검토한다. |
| [BiSeNet face parsing](https://github.com/zllrunning/face-parsing.PyTorch) | CelebAMask-HQ-style label과 함께 자주 쓰이는 practical face parsing implementation이다. | MIT-licensed code는 research prototype에 사용할 수 있다. 단 dataset과 pretrained weight는 각각의 조건을 따른다. 실제 integration 전 runtime fit은 별도 검토한다. |
| [SegFace](https://github.com/Kartik-3004/SegFace) | long-tail face parsing class를 위한 newer face segmentation reference다. | MIT-licensed code는 research prototype에 사용할 수 있다. 함께 쓰는 dataset은 각 dataset의 non-commercial/research 조건을 따른다. |
| [PSGAN](https://hf.co/papers/1909.06956), [SARA](https://hf.co/papers/2311.16828), [BeautyBank](https://hf.co/papers/2411.11231), [AvatarMakeup](https://hf.co/papers/2507.02419), [FFHQ-Makeup](https://hf.co/papers/2508.03241) | makeup transfer literature는 spatial alignment, region-aware editing, identity/appearance consistency, UV/3D consistency의 중요성을 보여준다. | generative makeup pipeline을 v1에 가져오지 않는다. renderer requirement인 `region`, `texture`, `feather`, `blendMode`, `intensity`를 잡는 참고로만 사용한다. |

## 4. Candidate Architecture Matrix

| Candidate | Description | Strength | Risk | Decision |
| --- | --- | --- | --- | --- |
| A. Current whole-face material | `ARFace` mesh material에 color/opacity를 계속 적용한다. | RN -> Unity message receipt는 이미 증명되었다. | lip/cheek/eye를 분리할 수 없고, 현재 visual alignment가 틀어져 있으며, `layer`가 실제 의미를 갖지 않는다. | product engine으로는 Reject. diagnostic baseline으로만 유지한다. |
| B. ARFace mesh + per-region vertex/UV maps | ARKit/AR Foundation `ARFace` mesh data를 사용하고 stable vertex/UV 영역을 `lip`, `cheek`, `eye` mask로 분류한다. | 현재 iOS stack에 가장 잘 맞고, face pose/expression을 따라가며, Unity renderer가 결과를 통제한다. | mapping work와 expression/rotation 실기기 검증이 필요하다. | alignment 이후 primary v1 research path. |
| C. Multiple region renderers/materials | shared face mesh update를 기반으로 region별 renderer object/material을 만든다. | layer isolation이 명확하고 visual debugging이 쉬우며 recipe layers와 잘 맞는다. | draw call과 edge artifact가 늘 수 있고, 같은 face mesh에 계속 정렬되어야 한다. | performance가 허용되면 v1 prototype에 사용한다. |
| D. Mask texture atlas + shader pass | UV-space mask/texture와 하나의 shader/layer stack으로 region을 blend한다. | feather, texture, 이후 matte/shimmer/blush sample에 더 좋다. | shader/asset complexity가 높고, 먼저 올바른 UV basis가 필요하다. | B/C가 region separation을 증명한 뒤 구현한다. 병렬 research 대상이다. |
| E. Screen-space 2D landmarks/segmentation | face parsing 또는 landmarks로 camera feed 위에 2D mask를 overlay한다. | face parsing literature를 참고할 수 있고 static analysis에는 유용하다. | 3D head rotation과 Unity camera feed에서 안정적으로 유지하기 어렵고 ARKit tracking을 중복한다. | fallback only. |
| F. MediaPipe live landmark stack | MediaPipe Face Landmarker를 실행하고 landmarks/matrices로 render한다. | cross-platform landmark topology와 blendshape output이 강하다. | RN + Unity에 ML/native/runtime complexity를 추가한다. concrete gate에서 ARKit path가 실패하기 전에는 필요 없다. | 지금 구현하지 않는다. fallback trigger만 정의한다. |
| G. Commercial beauty AR SDK | 유료/closed virtual makeup SDK를 통합한다. | budget/license가 맞으면 polished demo를 가장 빨리 만들 수 있다. | direct-implementation learning/validation goal과 충돌하고 vendor lock-in이 있으며 현재 scope 밖이다. | benchmark만 한다. 이 validation plan에서는 통합하지 않는다. |

Recommended engine direction for v1:

1. Unity + AR Foundation + ARKit을 primary runtime path로 유지한다.
2. makeup renderer work 전에 M6/M7/M8을 닫는다.
3. region mask 전에 camera/pose alignment를 고친다.
4. first-face-only behavior를 판단하기 전에 explicit trackable lifecycle diagnostics를 추가한다.
5. `lip`, `cheek`, `eye`를 ARFace mesh data 위의 독립 region layer로 만든다.
6. region separation이 visually stable해진 뒤 shader/mask texture work를 진행한다.
7. documented fallback trigger가 발생했을 때만 MediaPipe/ARCore를 사용한다.

Primary path Green/Yellow/Red:

| Layer | Current status | Reason |
| --- | --- | --- |
| RN + Unity + iPhone integration | Green | M0-M5가 real-device build, embed, AR view, RN -> Unity recipe delivery까지 Green으로 기록되어 있다. |
| ARKit/AR Foundation tracking | Green | log와 screenshot이 `SessionTracking`, front camera, face detected state를 보여준다. |
| Face-fitted rendering | Yellow/Fail | overlay가 눈에 띄게 offset되어 있고 AR Camera pose warning이 있다. |
| Region renderer | Not started | 현재 code는 color/opacity를 전체 diagnostic overlay에 적용한다. |
| Overall ARKit primary path | Yellow / continue | stack은 여전히 가장 좋은 primary path지만 product work 전 alignment와 region-mask gate가 필요하다. |

## 5. Proposed v1 Interfaces

이 interface들은 research target일 뿐이다. 이 문서에서 구현하지 않는다.

### Recipe Shape

RN, AI recommendation, Unity renderer가 같은 contract를 공유하도록 multi-layer recipe를 사용한다.

```json
{
  "recipeId": "demo-natural-001",
  "version": 1,
  "layers": [
    {
      "layer": "lip",
      "color": "#D94B74",
      "opacity": 0.65,
      "feather": 0.2,
      "blendMode": "multiply",
      "texture": "matte_lip",
      "intensity": 0.8,
      "positionOffset": {"x": 0.0, "y": 0.0},
      "scale": 1.0,
      "enabled": true
    }
  ]
}
```

Minimum v1 required fields:

- `layers[]`
- `layer`: initially `lip`, `cheek`, `eye`
- `color`
- `opacity`

Optional v1+ fields:

- `feather`
- `blendMode`
- `texture`
- `intensity`
- `positionOffset`
- `scale`
- `enabled`

Renderer meanings:

| Field | Renderer meaning |
| --- | --- |
| `layer` | semantic face region을 선택한다. whole-face material이 아니라 실제 region mask로 route되어야 한다. |
| `color` | 선택된 region의 base pigment color다. |
| `opacity` | layer의 alpha/strength다. 기기에서 시각적으로 구분 가능해야 한다. |
| `feather` | mask edge의 softness다. blush와 eye shadow 품질에 필요하다. |
| `blendMode` | pigment가 camera/skin appearance와 결합되는 방식이다. `normal`, `multiply`, `screen` 후보부터 시작한다. |
| `texture` | named procedural 또는 asset texture다. `matte_lip`, `shimmer_eye`, `soft_blush`부터 시작한다. |
| `intensity` | opacity와 분리된 texture/shine/glitter strength다. |
| `positionOffset` | mask alignment가 안정화된 뒤 region-local space에서 적용하는 작은 user adjustment다. |
| `scale` | mask alignment가 안정화된 뒤 region size에 적용하는 작은 user adjustment다. |

### Unity Runtime Modules

이후 구현을 위한 module boundary 제안:

| Module | Responsibility | Depends on |
| --- | --- | --- |
| `UnityEventBridge` | `unity_initialized`, `face_detected`, `recipe_applied`, diagnostics를 RN으로 보낸다. | M6 bridge work. |
| `FaceTrackableDiagnostics` | added/updated/removed faces, trackable ID, tracking state, vertex count, transform, support flags를 log한다. | `ARFaceManager.trackablesChanged`, `ARFace.updated`. |
| `ARCameraPoseValidator` | camera pose setup을 확인하고 AR Camera pose warning을 제거하거나 근거와 함께 설명하며 alignment diagnostics를 노출한다. | AR Foundation camera/XR Origin setup. |
| `MakeupRecipeReceiver` | `layers[]`를 parse하고 supported layers/textures/blend modes를 validate한 뒤 recipe를 queue/apply한다. | RN -> Unity bridge. |
| `FaceRegionMaskProvider` | ARFace mesh/UV data에서 `lip`, `cheek`, `eye` mask를 만들거나 load한다. | Stable ARFace mesh alignment. |
| `MakeupLayerRenderer` | color, opacity, feather, blend, texture, intensity로 각 recipe layer를 render한다. | Region masks and material/shader path. |

## 6. Follow-Up Validation Plans

### 6.1 M6 Unity -> RN Communication

Purpose:

- 더 깊은 engine work 전에 현재 공식 next milestone을 완료한다.

Minimum events:

- `unity_initialized`
- `face_detected` with `tracked` and `faceCount`
- `recipe_applied` with `layer`

Evidence:

- RN screen이 최신 Unity event를 보여준다.
- Runtime log가 event send와 RN receipt를 기록한다.
- Face lost/recovered가 RN status 변화를 만든다.

Stop rule:

- M6에서는 region rendering을 시작하지 않는다.

### 6.2 M7 Re-Entry Stability

Purpose:

- Unity lifecycle이 AR makeup screen에 충분히 안전한지 확인한다.

Minimum scenario:

- AR 시작 -> face detect -> color/opacity 변경 -> Close -> 3회 반복.
- background/foreground 1회.
- Close 이후 camera indicator behavior 확인.

Evidence:

- Screen recording.
- Device/runtime log.
- unload, pause/resume, hidden full-screen modal 중 어떤 behavior를 사용하는지 기록한다.

Stop rule:

- one-time successful entry를 product-ready로 간주하지 않는다.

### 6.3 M8 Foundation Result

Purpose:

- AR engine work 전에 첫 RN + Unity + AR Foundation validation을 닫는다.

Required result separation:

- RN-Unity integration status.
- Bidirectional messaging status.
- Re-entry/lifecycle status.
- ARKit tracking status.
- Visual makeup readiness status.

Expected current framing:

- M6/M7이 통과되면 integration은 Green일 가능성이 높다.
- Visual makeup readiness는 alignment와 region mask가 통과되기 전까지 Yellow/Fail로 남는다.

### 6.4 AR Alignment Plan

Purpose:

- region mask나 texture work 전에 diagnostic face mesh/overlay를 camera feed와 정렬한다.

Future session에서 다룰 research/implementation questions:

- 현재 AR Foundation + Input System stack에서 generated scene에 Tracked Pose Driver 또는 동등한 AR camera pose component가 필요한가?
- RN-hosted Unity embed는 Unity standalone과 camera pose behavior가 다른가?
- overlay offset의 원인이 camera transform, XR Origin hierarchy, background render matrix, face prefab transform, material/render queue, screen orientation 중 무엇인가?

Minimum checks:

- 현재 `XR Origin > Camera Offset > AR Camera` hierarchy를 official AR Foundation sample hierarchy와 비교한다.
- AR Camera pose warning이 사라졌는지, 또는 harmless warning으로 근거와 함께 문서화할 수 있는지 확인한다.
- neutral face, head left/right/up/down, mouth open/closed, face lost/recovered를 포함한 front-facing screen recording을 남긴다.

Green criteria:

- 30초 이상의 real-device recording에서 overlay가 face contour, eyes, mouth에 정렬되어 있다.
- Runtime log는 계속 `SessionTracking`과 face detected state를 보여준다.
- head rotation과 expression change에서도 alignment가 acceptable하게 유지된다.
- 남아 있는 warning은 evidence와 함께 설명된다.

Yellow criteria:

- 정면 still pose에서는 맞지만 rotation/expression/reacquisition에서 drift가 생긴다.

Red criteria:

- tracking은 true인데 Unity overlay를 camera feed에 정렬할 수 없다.

### 6.5 Trackable Lifecycle Plan

Purpose:

- first-face-only behavior를 정상적인 `MaximumFaceCount = 1` provider behavior, visual alignment bug와 분리한다.

Minimum diagnostics:

- `ARFaceManager.trackablesChanged`를 subscribe한다.
- `added`, `updated`, `removed` count를 log한다.
- trackable ID, `trackingState`, face transform, vertex count, timestamp를 log한다.
- active face의 `ARFace.updated`가 발생하는 시점을 log한다.

Test scenarios:

- 한 명의 얼굴이 들어오고 나간다.
- 같은 얼굴이 나갔다가 다시 들어온다.
- 첫 얼굴이 사라진 뒤 다른 얼굴이 나타난다.
- 얼굴이 부분적으로 가려진다.
- 얼굴이 멀어졌다가 가까워진다.

Green criteria:

- log가 face가 removed, limited, updated, reacquired 중 어떤 상태인지 명확히 설명한다.
- M6 이후 RN이 simplified face tracking status를 표시할 수 있다.

### 6.6 Region Mask Plan

Purpose:

- `lip`, `cheek`, `eye`가 recipe data에서 독립적으로 제어될 수 있음을 증명한다.

Preferred v1 approach:

- ARFace mesh/UV를 primary coordinate basis로 사용한다.
- 단순한 region mask와 눈에 띄는 debug color부터 시작한다.
- `lip`, `cheek`, `eye`에 독립 material/renderer 또는 mask channel을 사용한다.

Minimum RN controls:

- Select region: `lip`, `cheek`, `eye`.
- Select color.
- Adjust opacity.

Minimum Unity behavior:

- `layer: "lip"`은 lip만 바꾼다.
- `layer: "cheek"`은 cheek만 바꾼다.
- `layer: "eye"`는 eye만 바꾼다.
- 변경 사항은 1초 안에 적용된다.
- 기존 whole-face diagnostic overlay는 꺼지거나 makeup region rendering과 분리될 수 있다.

Green criteria:

- real-device recording이 각 region이 독립적으로 바뀌는 것을 증명한다.
- region은 head rotation, expression, face lost/recovered 중에도 얼굴에 붙어 있다.
- Runtime log가 recipe layer dispatch와 region application을 보여준다.

Yellow criteria:

- region은 분리되지만 edge quality나 rotation stability가 약하다.

Red criteria:

- ARFace mesh/UV가 현재 stack에서 stable region mask를 지원하지 못한다.

### 6.7 Texture Sample Plan

Purpose:

- region mask가 안정화된 뒤 renderer가 기본 makeup texture 차이를 보여줄 수 있는지 확인한다.

Minimum samples:

- `matte_lip` on `lip`
- `shimmer_eye` on `eye`
- `soft_blush` on `cheek`

Minimum controls:

- `color`
- `opacity`
- `feather`
- `blendMode`
- `texture`
- `intensity`

Green criteria:

- iPhone recording에서 matte, shimmer, soft-blush behavior가 시각적으로 다르게 보인다.
- 각 sample은 자기 region에 제한된다.
- opacity와 intensity 변경이 시각적으로 구분된다.

Stop rule:

- texture sample validation이 최소 Yellow가 되기 전까지 product-by-product color fidelity를 시작하지 않는다.

## 7. Recommended Next Working Order

`TECH_VALIDATION_RESULT.md`가 명시적으로 다른 boundary로 업데이트되지 않는 한 이 순서를 유지한다.

1. M6 Unity -> RN communication.
2. M7 re-entry stability.
3. M8 foundation result.
4. AR Alignment.
5. Trackable Lifecycle diagnostics.
6. Region Mask validation.
7. Texture Sample validation.
8. AI Face Analysis.
9. AI Recommendation.

이 순서가 필요한 이유:

- M6 없이는 RN이 AR engine state를 안정적으로 보여줄 수 없다.
- M7 없이는 Unity lifecycle이 일반적인 app use를 깨뜨릴 수 있다.
- alignment 없이는 region mask와 texture가 region logic과 무관한 이유로 틀려 보일 수 있다.
- trackable lifecycle log 없이는 first-face-only behavior와 render bug를 분리할 수 없다.
- region mask 없이는 texture와 makeup recipe work가 whole-face diagnostic overlay를 꾸미는 수준에 머문다.

## 8. Acceptance Checklist

이 리서치 계획은 다음 조건을 만족하면 다음 세션의 기준 문서로 사용할 수 있다.

- 현재 validation boundary를 유지한다.
- 핵심 주장에 repo evidence와 public source link가 붙어 있다.
- ARKit/AR Foundation primary path에 대해 Green/Yellow/Red decision을 제공한다.
- stack을 성급히 바꾸지 않고 MediaPipe/ARCore fallback trigger를 정의한다.
- 이후 `AR Alignment Plan`과 `Region Mask Plan` session을 작성할 수 있을 만큼 구체적이다.
- product implementation, AI/backend/admin/payment/community, commercial makeup quality를 scope 밖으로 유지한다.
