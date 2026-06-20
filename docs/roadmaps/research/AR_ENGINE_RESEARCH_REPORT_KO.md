# AR Makeup Engine Research Report - 한국어 버전

Date: 2026-06-20

Status: 리서치 보고서 / 구현 없음

Decision: Yellow - RN-hosted Unity + AR Foundation + ARKit iPhone 경로를 primary path로 유지한다. 다만 현재 repo evidence상 face tracking과 RN -> Unity recipe 전달은 Green이지만, visual alignment와 region mask는 아직 Green이 아니다. M6/M7/M8을 대체하지 않으며, 이 보고서는 이후 AR Alignment / Trackable Lifecycle / Region Mask 세션의 근거 문서다.

Current note: this report was written before the M8 closeout. For current milestone status and next boundary, use `../../../TECH_VALIDATION_RESULT.md` first. As of M8, M0-M6 are Green, M7 is Yellow / skipped by decision / risk accepted, and the next primary gate is E1 AR Alignment unless additional M7 verification is chosen.

## 1. Executive Summary

결론은 "스택을 바꾸지 말고, 검증 순서를 더 엄격히 하자"이다.

현재 repo는 React Native 앱 안에서 Unity AR 화면을 열고, iPhone 실기기에서 ARKit face tracking이 활성화되며, RN color/opacity 값이 Unity `RNBridge.ApplyRecipeJson(string)`까지 도달해 diagnostic face overlay material에 반영되는 것을 증명했다. 따라서 RN-hosted Unity + AR Foundation + ARKit iPhone 구조는 계속 primary path로 유지할 가치가 있다.

하지만 현재 화면 상태는 product makeup readiness가 아니다. `TECH_VALIDATION_RESULT.md`는 overlay가 얼굴보다 위/왼쪽으로 밀리고, eye/mouth/jaw/face contour에 맞지 않으며, `Camera "AR Camera" does not use a Tracked Pose Driver (Input System)` warning이 남아 있다고 기록한다. 또 현재 Unity 구현은 RN payload의 `layer: "lip"`을 실제 lip region으로 route하지 않고, whole-face diagnostic material만 칠한다.

따라서 v1 engine의 추천 구조는 다음 순서다.

1. M6 Unity -> RN communication을 먼저 닫는다.
2. M7 re-entry stability를 닫는다.
3. M8에서 "integration Green"과 "visual makeup Yellow/Fail"을 분리해 결과를 정리한다.
4. AR Alignment 세션에서 AR Camera pose / XR Origin hierarchy / Tracked Pose Driver warning / background render matrix / face prefab transform / screen orientation 후보를 검증한다.
5. Trackable Lifecycle 세션에서 `ARFaceManager.trackablesChanged`, `ARFace.updated`, `trackingState`, trackable ID, vertex count, transform을 기록한다.
6. Region Mask 세션에서 `lip`, `cheek`, `eye`만 최소 slice로 잡고 ARFace mesh/UV 기반 region separation을 증명한다.
7. 그 다음에만 mask texture atlas, shader pass, feather, blendMode, texture, intensity를 다룬다.

MediaPipe Face Landmarker와 ARCore Augmented Faces는 지금 primary replacement가 아니다. ARKit alignment가 해결되지 않거나, ARKit mesh/UV 기반 region mask가 부족하거나, Android / non-TrueDepth / shared landmark topology 요구가 active scope가 될 때 fallback 또는 비교 실험 후보가 된다.

## 2. Current Repo Baseline

### 2.1 Validation Boundary

현재 `TECH_VALIDATION_RESULT.md` 기준 다음 milestone은 M6 Unity -> RN communication이다. 이 리서치는 M6/M7/M8 완료를 대체하지 않는다.

현재까지의 핵심 상태:

| Area | Current status | Evidence |
| --- | --- | --- |
| RN host app | Green | `rn/MakeupARValidation/App.tsx`가 Home에서 `Start AR`를 누르면 full-screen `UnityView`를 연다. |
| RN -> Unity message | Green | `App.tsx`가 `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)`을 호출한다. |
| Unity receiver | Green | `RNBridge.cs`가 `layer`, `color`, `opacity`를 parse하고 material color/alpha에 적용한다. |
| AR Foundation / ARKit packages | Green | `unity/MakeupARUnityValidation/Packages/manifest.json`에 `com.unity.xr.arfoundation` 6.3.5, `com.unity.xr.arkit` 6.3.5가 있다. |
| Face tracking | Green | 결과 문서가 iPhone runtime `SessionTracking`, face count 1, `Face detected: true`를 기록한다. |
| Face-fitted rendering | Yellow/Fail | 결과 문서가 overlay offset과 face contour/eyes/mouth mismatch를 기록한다. |
| Region renderer | Not started | 현재 `layer: "lip"`은 전체 diagnostic overlay material에 적용될 뿐 lip region으로 분리되지 않는다. |
| Unity -> RN status | Not complete | native message path 후보는 있으나 RN 화면의 `onUnityMessage` 수신/표시는 아직 없다. |

### 2.2 Current Source Shape

`rn/MakeupARValidation/App.tsx`

- Home screen은 M5 문구를 보여주고 `Start AR` 버튼으로 Unity screen을 연다.
- Unity screen은 `UnityView`, `Close`, debug panel, `rose/coral/nude` color controls, opacity slider를 가진다.
- RN payload는 단일 object이며 `layer: "lip"`, `color`, `opacity`만 보낸다.
- `onUnityMessage` handler가 아직 없어 M6 status event 수신 UX는 구현되지 않았다.

`unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`

- `ApplyRecipeJson(string json)`은 JSON을 parse하고 opacity를 clamp한다.
- `ColorUtility.TryParseHtmlString`으로 color를 검증한다.
- `currentLayer`는 보관/logging하지만 region dispatch에는 쓰지 않는다.
- `overlayMaterial`과 현재 `ARFace` trackables의 `MeshRenderer.sharedMaterial`에 같은 color/alpha를 적용한다.
- transparent material setting은 diagnostic overlay에는 충분하지만, lip/cheek/eye layer stack은 아니다.

`unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs`

- `ARSession.stateChanged`를 기록한다.
- `ARCameraManager.requestedFacingDirection/currentFacingDirection`, `XRFaceSubsystem` optional support, face count를 기록한다.
- 현재는 `ARFaceManager.trackablesChanged`의 added/updated/removed 목록, trackable ID, `trackingState`, mesh vertex/uv/index count를 기록하지 않는다.

`unity/MakeupARUnityValidation/Assets/Editor/MakeupARValidationSetup.cs`

- `AR Session`, `XR Origin`, `Camera Offset`, `AR Camera`, `ARCameraManager`, `ARCameraBackground`, `ARFaceManager`를 생성한다.
- `ARCameraManager.requestedFacingDirection = User`로 front camera를 요청한다.
- `ARFaceManager.facePrefab`에 `ValidationFaceOverlay` prefab을 연결한다.
- `faceManager.requestedMaximumFaceCount = 1`로 설정한다.
- generated scene cross-check상 `AR Camera`에는 `ARCameraManager`와 `ARCameraBackground`가 있으나 `TrackedPoseDriver` serialized entry는 확인되지 않았다.

## 3. Core Problem: Alignment, Lifecycle, Region Mask

### 3.1 Alignment

현재 증상은 "tracking true인데 rendering alignment fail"이다. 이 둘은 분리해서 봐야 한다.

주요 원인 후보:

| Candidate | Why plausible | How to validate |
| --- | --- | --- |
| AR Camera pose update missing | Unity XR Origin reference는 recommended Main Camera components에 `TrackedPoseDriver`, `ARCameraManager`, `ARCameraBackground`를 함께 둔다. 현재 runtime warning도 Tracked Pose Driver 부재를 가리킨다. | AR Camera에 현재 AR Foundation 6.3 + Input System stack에 맞는 pose driver 또는 equivalent setup을 추가/검증하고 warning 제거 전후 screen recording을 비교한다. |
| XR Origin / Camera Offset hierarchy mismatch | AR Foundation scene setup은 AR Session과 XR Origin이 필수이며 XR Origin이 trackables를 Unity coordinate system으로 변환한다고 설명한다. 현재 generator가 manual hierarchy를 만든다. | official XR Origin (Mobile AR) 생성 hierarchy와 current generated hierarchy를 component 단위로 diff한다. |
| ARCameraBackground render matrix / render mode issue | ARCameraBackground가 camera feed를 scene background로 렌더링한다. background와 overlay가 다른 pose/projection을 쓰면 offset처럼 보일 수 있다. | `ARCameraBackground`, `ARCameraManager`, camera projection/logging, orientation/frame capture를 함께 확인한다. |
| Face prefab transform or diagnostic marker offset | current face prefab에 `ARFace`, `MeshFilter`, `MeshRenderer`, `ARFaceMeshVisualizer`, marker script가 있고, diagnostic marker/material이 별도 runtime object를 만든다. | ARFace mesh visualizer만 켜고 marker를 끈 recording, marker만 켠 recording, mesh bounds/transform logs를 분리한다. |
| RN-hosted Unity view size/orientation | `@azesmway/react-native-unity`는 iOS Unity view가 non-zero parent dimensions를 기다린다고 문서화한다. M4도 local `didMoveToWindow` timing patch에 의존했다. | Unity standalone과 RN-hosted 결과를 같은 scene/device/orientation에서 비교한다. UnityView bounds와 safe-area/orientation logs를 남긴다. |
| Face trackable state confusion | face count는 1인데 first-face-only/reacquisition risk가 남아 있다. Limited state와 removed state가 섞이면 visual result가 오래된 face 기준으로 남을 수 있다. | `trackablesChanged`, `ARFace.updated`, `trackingState`, trackable ID, transform을 timestamp와 함께 log한다. |

AR Alignment Green 기준:

- 30초 이상 iPhone recording에서 face contour, eyes, mouth 기준 overlay가 맞는다.
- front face, left/right/up/down head movement, mouth open/closed, face lost/recovered를 포함한다.
- runtime log는 `SessionTracking`, face detected, active trackable ID, vertex/uv availability를 보여준다.
- Tracked Pose Driver warning은 사라지거나, 남아도 visual alignment에 영향이 없다는 evidence를 남긴다.

### 3.2 Lifecycle

Unity AR Foundation 공식 문서상 `ARFaceManager`는 detected face마다 GameObject를 만들고, faces가 added/updated/removed될 때 `trackablesChanged`를 발생시킨다. `ARFace`도 trackable lifecycle을 가지며, face가 camera field of view를 떠났을 때 항상 removed되는 것이 아니라 `trackingState = Limited`가 될 수 있다.

따라서 현재 `faceCount > 0`만으로는 부족하다. engine 구조에는 다음 진단이 들어가야 한다.

| Signal | Why it matters |
| --- | --- |
| `trackablesChanged.added` | 첫 얼굴 탐지, 다른 얼굴 전환, reset 이후 새 trackable 생성 확인 |
| `trackablesChanged.updated` | 매 frame 또는 상태 변화에서 active face가 계속 갱신되는지 확인 |
| `trackablesChanged.removed` | 얼굴 이탈이 실제 removal인지, Limited state 유지인지 분리 |
| `ARFace.updated` | 개별 face mesh vertices/normals/indices/uvs update timing 확인 |
| `ARFace.trackingState` | Tracking / Limited / None 상태를 face count와 분리 |
| trackable ID | first-face-only, same-face reacquisition, second-face switch를 구분 |
| mesh vertex/index/uv count | region mask를 만들 수 있는 geometry basis가 runtime에 실제로 있는지 확인 |
| face transform | visual offset이 mesh data 문제인지 coordinate transform 문제인지 확인 |

### 3.3 Region Mask

현재 구현은 whole-face material이다. v1 region mask는 최소 `lip`, `cheek`, `eye`만 다루고, 아래 원칙을 따른다.

- 첫 목표는 예쁜 makeup이 아니라 "부위가 독립적으로 분리되어 얼굴에 붙는가"다.
- ARFace mesh/UV를 primary coordinate basis로 둔다.
- static face parsing output을 realtime AR에 바로 덮는 방식은 fallback으로만 둔다.
- 처음에는 debug color와 hard mask로 시작하고, alignment가 Green이 된 뒤 feather/texture/blend를 붙인다.

가장 현실적인 v1 방식:

1. ARFace mesh visualizer가 안정적으로 camera feed에 맞는지 확인한다.
2. ARFace mesh vertices/indices/UVs availability를 runtime descriptor와 actual mesh로 확인한다.
3. ARKit/ARFace topology에서 `lip`, `cheek`, `eye` candidate vertex/UV ranges를 debug overlay로 표시한다.
4. 독립 material/renderer 또는 mask channel로 각 region을 칠한다.
5. region이 안정화되면 mask texture atlas와 shader layer stack으로 이동한다.

## 4. Public Source Findings

| Source | Findings | Engine meaning | License / use note |
| --- | --- | --- | --- |
| [Unity AR Face Manager 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/arfacemanager.html) | `ARFaceManager`는 face GameObject를 생성하고 `trackablesChanged`로 added/updated/removed를 보고한다. `Face Prefab`, `Maximum Face Count`를 가진다. | M6 이후 status event와 lifecycle diagnostics의 중심은 `trackablesChanged`다. | Unity documentation. 링크/인용 기반으로 사용. |
| [Unity AR Face 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/arface.html) | `ARFace` lifecycle은 added/updated/removed이며, update 시 mesh vertices/normals/indices/uvs가 갱신될 수 있다. face가 FOV를 벗어나면 removed 대신 `Limited`가 될 수 있다. | `trackingState`, `ARFace.updated`, mesh data가 alignment와 region mask의 핵심이다. | Unity documentation. 링크/인용 기반으로 사용. |
| [Unity Face Tracking Platform Support 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/platform-support.html) | ARCore와 ARKit 모두 face pose, face mesh vertices/indices, face mesh UVs를 지원한다고 표시된다. Optional feature support는 descriptor로 확인 가능하다. | ARKit path에서 mesh/UV 기반 region mask를 검증할 근거가 있다. 런타임에서도 descriptor를 log해야 한다. | Unity documentation. 링크/인용 기반으로 사용. |
| [Unity Face Tracking Samples 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/samples/features/face-tracking.html) | sample은 face pose, face mesh, ARCore face regions, ARKit blend shapes, ARKit eye poses를 제공한다. ARKit face tracking support 조건도 정리되어 있다. | current custom scene을 official Face Mesh / Face Pose sample과 비교해야 한다. | Unity sample/license는 Unity package terms를 따른다. repo에 복사 전 license 확인. |
| [Unity Scene Setup 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/project-setup/scene-setup.html) | AR scene에는 `AR Session`과 `XR Origin`이 필요하고, XR Origin이 device tracking 및 trackable-to-Unity-coordinate 변환을 담당한다. | overlay offset은 XR Origin / Camera Offset / AR Camera hierarchy부터 검증해야 한다. | Unity documentation. |
| [Unity XR Origin reference](https://docs.unity3d.com/Packages/com.unity.xr.core-utils%402.5/manual/xr-origin-reference.html) | recommended Main Camera components에는 `TrackedPoseDriver`, `ARCameraManager`, `ARCameraBackground`가 함께 표시된다. | current warning과 정확히 맞물린다. AR Camera pose update 구성은 alignment gate의 첫 후보이다. | Unity documentation. |
| [Unity Camera Components 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/camera/camera-components.html) | `ARCameraManager`와 `ARCameraBackground`가 camera 기능과 background rendering을 담당하고, User direction은 front/selfie camera다. | face overlay는 camera feed와 같은 camera/projection/render order에서 검증해야 한다. | Unity documentation. |
| [Unity as a Library iOS](https://docs.unity3d.com/Manual/UnityasaLibrary-iOS.html) | Unity iOS export는 `UnityFramework.framework`를 만들고, `runEmbeddedWithArgc`, `unloadApplication`, `pause`, `sendMessageToGOWithName` 등을 제공한다. Known limitations로 full-screen rendering only, single runtime instance가 있다. | AR screen은 full-screen 전제를 유지하고, M7에서 unload/pause/re-enter policy를 검증해야 한다. | Unity Manual. Unity runtime/framework 사용은 Unity license/terms 범위에서 검토. |
| [`@azesmway/react-native-unity`](https://github.com/azesmway/react-native-unity) | iOS device는 지원, iOS simulator는 미지원. iOS는 built `UnityFramework`를 사용하며, `postMessage`, `onUnityMessage`, `unloadUnity`, `pauseUnity`를 제공한다. iOS view dimensions가 0이면 crash risk가 있다. | 현재 bridge는 validation에 적합하다. M6은 `onUnityMessage`를 써야 하고, M7은 unload/pause/re-enter behavior를 검증해야 한다. | MIT license. UnityFramework artifact와 Unity license는 별도. |
| [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) | image/video/live stream 입력을 받고 3D landmarks, blendshape scores, facial transformation matrices를 출력한다. model bundle은 478 landmarks와 52 blendshape scores를 포함한다. | cross-platform fallback / static AI analysis bridge 후보. 지금 ARKit primary path를 바로 대체할 이유는 아니다. | Google docs content CC BY 4.0, code samples Apache 2.0. Model/runtime terms는 실제 사용 전 별도 확인. |
| [ARCore Augmented Faces](https://developers.google.com/ar/develop/augmented-faces) | specialized hardware 없이 center pose, three region poses, 468-point 3D face mesh를 제공하며 textures/models를 face에 overlay하는 use case를 설명한다. | Android scope 또는 ARKit comparison reference. ARCore face region poses는 ARKit primary path에는 직접 적용되지 않는다. | Google docs content CC BY 4.0, code samples Apache 2.0. ARCore SDK terms 별도 확인. |

## 5. Tracking Stack Comparison

| Stack | Strength | Risk / cost | Best use in this project | Decision |
| --- | --- | --- | --- | --- |
| Unity + AR Foundation + ARKit on iPhone | 이미 repo에서 real-device tracking, Unity embed, RN -> Unity message가 Green이다. AR Foundation는 ARKit face pose/mesh/UV support를 노출한다. | 현재 alignment issue와 lifecycle/re-entry 검증이 남아 있다. iOS-first이며 device support 조건이 있다. | Primary runtime path. v1 AR makeup engine의 첫 검증 대상. | Continue as primary. |
| MediaPipe Face Landmarker | 3D landmarks, blendshapes, transformation matrices, image/video/live stream mode가 있고 cross-platform topology가 강하다. | RN + Unity + native ML runtime complexity가 늘어난다. 현재 문제는 landmark 부족보다 camera/render alignment에 가깝다. | ARKit path가 alignment/region/lifecycle에서 막힐 때 fallback 또는 static AI analysis와 AR landmark comparison. | Fallback/comparison only. |
| ARCore Augmented Faces | 468-point mesh, center pose, region poses, no specialized hardware, Android beauty/effects reference가 좋다. | 현재 repo boundary는 iPhone ARKit이다. Android 구현은 explicitly out of scope다. | Android validation이 active scope가 될 때 primary Android candidate. | Not now. |
| 2D face parsing / segmentation overlay | CelebAMask-HQ, LaPa, BiSeNet, SegFace 같은 자료가 region semantics에 강하다. | realtime 3D head rotation, camera projection, occlusion, expression deformation에는 ARFace mesh보다 불리하다. | region label inspiration, offline research, static AI feedback, mask concept validation. | Runtime primary로 쓰지 않음. |
| Commercial beauty AR SDK | 빠른 polished demo 가능성. | 유료/closed, vendor lock-in, 부트캠프 learning/validation goal과 충돌. | benchmark reference 정도. | Integrate하지 않음. |

Fallback trigger:

- ARKit/AR Foundation face mesh overlay를 camera feed에 정렬할 수 없다.
- Tracked Pose Driver / XR Origin / background rendering / orientation 수정 후에도 offset이 재현된다.
- ARFace mesh/UV 기반 `lip`, `cheek`, `eye` region이 안정적으로 분리되지 않는다.
- first-face-only 또는 reacquisition behavior가 M6/M7 이후에도 product UX를 막는다.
- Android validation이 공식 scope로 들어온다.
- AI static analysis와 AR runtime이 같은 landmark topology를 공유해야 하는 강한 요구가 생긴다.

## 6. Region Mask & Renderer Architecture Comparison

| Architecture | Description | Good for | Weakness | Verification order |
| --- | --- | --- | --- | --- |
| Whole-face material | 현재처럼 `ARFace` mesh material 전체에 color/opacity 적용 | Diagnostic, RN -> Unity message smoke test | region separation 불가. `layer` 의미 없음. 현재 alignment도 fail | Keep only as baseline |
| ARFace mesh vertex/UV region map | ARFace mesh vertices/indices/UVs를 기준으로 region을 분류 | iOS primary path, face-following geometry, expression-aware base | topology mapping과 per-device/runtime stability 검증 필요 | 1 |
| Separate region renderers/materials | lip/cheek/eye별 MeshRenderer/material 또는 child object | debug clarity, recipe layer isolation | draw calls, edge artifacts, shared mesh sync 관리 | 2 |
| Submesh/material separation | one mesh에 region submesh/material을 배정 | renderer 구조 명확, Unity material workflow 친화적 | runtime mesh reconstruction complexity | 3 |
| Mask texture atlas | UV-space mask texture로 lip/cheek/eye channel 관리 | feather, soft blush, texture blending, shader stack | UV basis가 안정화되어야 함 | 4 |
| Shader pass / layer stack | color/opacity/feather/blendMode/texture/intensity를 shader에서 합성 | product makeup renderer로 확장 가능 | complexity/performance/debug difficulty | 5 |
| Screen-space 2D segmentation | camera image에 face parsing mask를 붙임 | offline reference, static feedback, quick mask prototype | 3D AR stability 낮음, Unity camera feed와 좌표 동기화 비용 | fallback |

권장 검증 순서:

1. AR Camera / face mesh alignment Green.
2. `ARFace.updated`에서 mesh vertices/indices/UVs actual availability 확인.
3. `lip`, `cheek`, `eye` debug region을 hard color로 분리.
4. region별 renderer/material dispatch가 RN `layer`와 연결되는지 확인.
5. submesh/material 또는 mask atlas 중 더 단순한 쪽으로 v1 prototype 고정.
6. feather와 blendMode를 추가한다.
7. texture/intensity를 추가한다.
8. half-face guide mode, positionOffset, scale은 alignment와 region stability가 Green이 된 뒤에만 추가한다.

Recommended v1 renderer field meaning:

| Field | v1 meaning |
| --- | --- |
| `layer` | `lip`, `cheek`, `eye` 중 하나를 선택하는 region dispatch key |
| `color` | selected region의 base pigment color |
| `opacity` | selected region의 alpha/strength |
| `feather` | mask edge softness. 처음에는 shader/mask 단계 이후 추가 |
| `blendMode` | camera/skin과 섞는 방식. `normal`, `multiply`, `screen` 후보 |
| `texture` | `matte_lip`, `soft_blush`, `shimmer_eye` 같은 named texture/procedural sample |
| `intensity` | opacity와 분리된 texture/shine/glitter strength |
| `positionOffset` | alignment 안정화 이후 user adjustment |
| `scale` | alignment 안정화 이후 region-local size adjustment |

## 7. Makeup Texture / Face Parsing / Makeup Transfer References

이 자료들은 v1 runtime engine에 바로 넣기 위한 것이 아니다. 주된 의미는 renderer contract와 region semantics를 정교하게 잡는 것이다.

| Reference | What it contributes | Renderer implication | License / research-use note |
| --- | --- | --- | --- |
| [CelebAMask-HQ](https://github.com/switchablenorms/CelebAMask-HQ) | 30,000 high-res face images, 19 classes including skin, nose, eyes, eyebrows, mouth, lip, hair, accessories. | `lip`, `eye`, face/skin boundary semantic reference. face parsing class design 참고. | Non-commercial research purposes only. Software use restricted to non-commercial research and educational purposes. No commercial exploitation or redistribution of dataset portions/derived data. |
| [LaPa Dataset](https://github.com/jd-opensource/lapa-dataset) | 22,000+ images, 11-category pixel labels, 106-point landmarks. | face parsing + landmark relationship reference. cheek/eye/lip rough semantic mapping에 도움. | Free for academic/non-academic non-commercial purposes such as research, teaching, scientific publications, personal experimentation. License terms 동의 필요. |
| [BiSeNet face parsing PyTorch](https://github.com/zllrunning/face-parsing.PyTorch) | CelebAMask-HQ 기반 practical face parsing implementation and pretrained model link. | offline mask prototype, parsing-map based makeup concept 참고. | Code is MIT. Dataset/pretrained weight는 각각 upstream 조건을 따른다. |
| [SegFace](https://github.com/Kartik-3004/SegFace) | Long-tail face segmentation, LaPa/CelebAMask-HQ results, lightweight/mobile backbone mention. | face parsing model quality benchmark. eye/lip/accessory class robustness 참고. | Repo is MIT. Weights/datasets require their own terms; do not redistribute weights unless terms allow. |
| [PSGAN](https://arxiv.org/abs/1909.06956) | pose/expression robust, spatial-aware, partial and shade-controllable makeup transfer. | `layer`, `intensity`, `partial transfer`, pose/expression robustness가 renderer requirement임을 뒷받침. | Paper reference. Code/dataset/license not adopted here. |
| [SARA](https://arxiv.org/abs/2311.16828) | spatial alignment and region-adaptive normalization for part-specific and shade-controllable makeup transfer. | alignment와 region-adaptive control이 core problem임을 확인. | Paper reference only unless code/data terms are separately verified. |
| [BeautyBank](https://arxiv.org/abs/2411.11231) | high-dimensional makeup latent encoding and detailed pattern preservation. | `texture`, `pattern`, `intensity`를 opacity와 분리해야 하는 이유. | Paper reference only; BMS dataset/code terms must be verified before use. |
| [AvatarMakeup](https://arxiv.org/abs/2507.02419) | 3D avatar makeup consistency across views/expressions using global UV map idea. | AR runtime도 expression/view consistency를 위해 UV-space mask/texture direction이 중요하다. | Paper reference only; code/data terms must be verified before use. |
| [FFHQ-Makeup](https://arxiv.org/abs/2508.03241) | paired synthetic bare/makeup data preserving identity/expression across styles. | paired data can help future recommendation/feedback research, not v1 AR renderer. | Paper reference only. Dataset availability/license must be verified before use. |

Key design lessons:

- `color` and `opacity` alone are not enough for product makeup. Literature repeatedly separates region, shade/degree, spatial alignment, local detail, and consistency.
- `feather` is necessary for cheek and eye region edges.
- `blendMode` is necessary because pigment should mix with camera/skin appearance differently per product.
- `texture` and `intensity` must be separate fields; shimmer/shine/pattern strength is not the same as alpha.
- UV-space thinking is useful after ARFace alignment is solved, because head pose/expression consistency becomes easier to reason about than screen-space masks.

## 8. License and Research-Use Notes

This repo is a bootcamp non-commercial research/education prototype, not a commercial release. The following rules should apply until terms are re-reviewed:

- Always keep citation/attribution notes for datasets, models, papers, and code.
- Do not commit downloaded datasets, restricted derived data, or pretrained weights into this repo unless upstream terms explicitly allow redistribution.
- Keep dataset/model downloads outside source control.
- If a dataset says non-commercial only, use it only for research validation, teaching, scientific publication, or personal experimentation.
- Before public launch, paid demo, App Store/TestFlight distribution beyond internal education, or commercial product work, re-check all licenses and obtain approvals if needed.

| Source | Type | Use allowed for this prototype | Not allowed / caution |
| --- | --- | --- | --- |
| Unity AR Foundation docs/samples | Official docs/samples | Read as implementation guidance; use package samples according to Unity package terms. | Do not assume sample asset redistribution terms without checking package license. |
| Unity Runtime / UnityFramework | Runtime/framework | Validation under installed Unity license terms. | Commercial deployment requires Unity licensing compliance. |
| `@azesmway/react-native-unity` | Bridge code | MIT code can be used in prototype, with license preservation. | Generated UnityFramework and Unity runtime terms are separate. |
| Google MediaPipe docs/code samples | Docs/code samples | Docs under CC BY 4.0, code samples Apache 2.0. Good for comparison prototype. | Model/runtime/package terms must be checked before bundling. |
| Google ARCore docs/code samples | Docs/code samples | Docs under CC BY 4.0, code samples Apache 2.0. Good for Android comparison research. | ARCore SDK/API terms and platform scope must be checked before product use. |
| CelebAMask-HQ | Dataset/software | Non-commercial research/education reference. | No commercial exploitation; no further copying/publishing/distribution of dataset portions except allowed internal single-site copies. |
| LaPa | Dataset | Non-commercial research, teaching, scientific publications, personal experimentation. | License terms agreement required; commercial use requires separate review. |
| BiSeNet face parsing repo | Code/model reference | MIT code can be inspected/used for research prototype. | Pretrained model and dataset terms are separate. |
| SegFace | Code/model reference | MIT code can be inspected/used for research prototype. | Hugging Face weights and training datasets need separate license review. |
| PSGAN/SARA/BeautyBank/AvatarMakeup/FFHQ-Makeup | Papers/literature | Safe as design references and citations. | Do not use datasets/weights/code unless license is found and compatible. |

## 9. Recommended v1 Engine Architecture

### 9.1 Decision

Primary runtime path:

> React Native host + full-screen Unity view + Unity AR Foundation + Apple ARKit XR Plug-in + ARFace mesh/UV based makeup renderer.

This path remains primary because the repo has already proven:

- real iPhone RN app launch,
- Unity iOS export and UnityFramework build,
- RN-hosted Unity AR view,
- ARKit face tracking active on iPhone,
- RN -> Unity recipe-like message delivery.

It remains Yellow because the visual engine is not validated:

- current overlay is offset,
- current AR Camera pose warning is unresolved,
- current recipe layer is not honored,
- current renderer is whole-face diagnostic material,
- current lifecycle logs do not explain first-face-only/reacquisition.

### 9.2 Proposed Runtime Modules

These are architecture boundaries only. Do not implement them in this research step.

| Module | Responsibility | Required before product makeup |
| --- | --- | --- |
| `UnityEventBridge` | Send `unity_initialized`, `face_detected`, `recipe_applied`, diagnostics to RN. | M6 |
| `FaceTrackableDiagnostics` | Log `trackablesChanged`, `ARFace.updated`, ID, trackingState, transform, vertex/index/uv counts. | AR Alignment / Lifecycle |
| `ARCameraPoseValidator` | Verify XR Origin / AR Camera / Tracked Pose Driver / background rendering alignment. | AR Alignment |
| `MakeupRecipeReceiver` | Parse multi-layer recipe, validate layer/color/opacity/feather/blendMode/texture/intensity. | Region Mask |
| `FaceRegionMaskProvider` | Provide `lip`, `cheek`, `eye` masks from ARFace mesh/UV or verified fallback. | Region Mask |
| `MakeupLayerRenderer` | Render layer stack with color, opacity, feather, blend, texture, intensity. | Texture Sample |
| `HalfFaceGuideMask` | Clip recipe rendering to one side of face for guide mode. | After region stability |

### 9.3 Minimum v1 Recipe Contract

The current single payload can evolve into a multi-layer contract after M6/M7/M8.

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
      "enabled": true
    }
  ]
}
```

v1 hard requirement:

- `layers[]`
- `layer`: `lip`, `cheek`, `eye`
- `color`
- `opacity`
- `enabled`

v1+ after region stability:

- `feather`
- `blendMode`
- `texture`
- `intensity`
- `positionOffset`
- `scale`
- `halfFaceSide`

### 9.4 Green / Yellow / Red Decision

현재 결론은 overall Yellow다. 이유는 integration과 tracking은 Green이지만, face-fitted rendering과 region renderer가 아직 Green이 아니기 때문이다.

| Layer | Current decision | Why | Green condition |
| --- | --- | --- | --- |
| RN + Unity host integration | Green | RN app opens full-screen Unity view on real iPhone, and M4/M5 evidence records successful embed. | M7 re-entry repeats without crash/black screen/camera leak. |
| RN -> Unity recipe path | Green | RN sends `layer/color/opacity`; Unity `RNBridge.ApplyRecipeJson` parses and applies color/opacity. | Keep working after clean rebuild/reinstall without local `node_modules` caveats. |
| Unity -> RN event path | Not complete | Native path and package `onUnityMessage` support exist, but RN screen does not yet receive/print Unity events. | M6 receives `unity_initialized`, `face_detected`, `recipe_applied` on RN screen/log. |
| ARKit / AR Foundation tracking | Green | Runtime evidence records `SessionTracking`, front camera, face count 1, and `Face detected: true`. | Tracking remains active through lost/recovered and re-entry scenarios. |
| Face-fitted rendering | Yellow/Fail | Current overlay is visibly offset and Tracked Pose Driver warning is unresolved. | 30s+ iPhone recording shows overlay aligned to contour, eyes, mouth through movement/expression. |
| Trackable lifecycle clarity | Yellow | Current logs count faces but do not explain added/updated/removed, `trackingState`, or trackable ID behavior. | Logs separate Tracking vs Limited vs removed and explain first-face/reacquisition behavior. |
| Region renderer | Not started | `layer: "lip"` is accepted but whole-face material is colored. | `lip`, `cheek`, `eye` are independently controlled and stay attached to face. |
| Texture renderer | Not started | No feather/blend/texture/intensity path exists yet. | `matte_lip`, `soft_blush`, `shimmer_eye` are visually distinct on iPhone recording. |
| Overall primary path | Yellow / continue | Current stack has enough proof to continue, but visual makeup engine is not validated. | M6/M7/M8 closeout plus AR Alignment and Region Mask reach Green or at least defensible Yellow. |

### 9.5 M6 / M7 / M8 Acceptance

M6/M7/M8 are not AR makeup rendering milestones, but they must close before deeper engine work because they prove that the RN host can observe Unity state and survive normal AR screen lifecycle.

| Milestone | Purpose | Minimum acceptance | Evidence | Stop rule |
| --- | --- | --- | --- | --- |
| M6 Unity -> RN communication | Unity AR state becomes visible to RN. | RN receives and displays/logs `unity_initialized`, `face_detected` with `tracked` and `faceCount`, and `recipe_applied` with `layer`. Face lost/recovered changes should be visible in RN. | RN screenshot or screen recording showing latest event; device/runtime log showing Unity send and RN receipt; source/config cross-check for bridge path. | Do not start re-entry, alignment, or region rendering until event delivery is proven or blocked with evidence. |
| M7 re-entry stability | Confirm Unity runtime lifecycle is safe enough for app flow. | Start AR -> face detect -> color/opacity change -> Close -> return Home repeated 3 times without crash/black screen. Include one background/foreground check and camera indicator observation. | Screen recording of 3 cycles; device/runtime log; note whether unload, pause/resume, or hide/show strategy is used. | Do not treat one successful AR entry as stable. If unload is unstable, test pause/resume strategy before product work. |
| M8 foundation result | Close the first RN + Unity + AR Foundation validation honestly. | `TECH_VALIDATION_RESULT.md` separates RN-Unity integration, bidirectional messaging, re-entry lifecycle, ARKit tracking, and visual makeup readiness. | Updated result document plus M6/M7 evidence paths. | Do not mark visual AR makeup Green unless alignment and region renderer evidence actually exists. |

### 9.6 Next Validation Order

Do not start product makeup rendering yet.

1. M6 Unity -> RN communication.
2. M7 re-entry stability.
3. M8 foundation result with separated integration/rendering decisions.
4. AR Alignment Plan.
5. Trackable Lifecycle Plan.
6. Region Mask Plan for `lip`, `cheek`, `eye`.
7. Texture Sample Plan for `matte_lip`, `soft_blush`, `shimmer_eye`.
8. AI face analysis and recommendation only after AR core is at least Yellow/Green.

### 9.7 Follow-Up Validation Plan Details

#### 9.7.1 AR Alignment Plan

Purpose:

- Prove that ARKit/AR Foundation face mesh rendering is aligned with the live front-camera feed before any region mask or texture work.

Minimum checks:

| Check | Required observation |
| --- | --- |
| AR Camera pose setup | Confirm whether `TrackedPoseDriver` or equivalent AR Foundation 6.3 camera pose setup exists. Remove the current warning or document why it is harmless with evidence. |
| XR Origin hierarchy | Compare current `XR Origin > Camera Offset > AR Camera` hierarchy with official `XR Origin (Mobile AR)` setup. |
| ARCameraBackground/projection | Confirm camera feed and overlay share correct projection/orientation/render order. |
| Face prefab transform | Test `ARFaceMeshVisualizer` mesh without extra marker objects, then marker-only, to isolate transform/material artifacts. |
| RN-hosted vs Unity standalone | Compare same scene/device/orientation in standalone Unity app and RN-hosted Unity view. |
| Movement/expression | Test neutral, left/right/up/down head movement, mouth open/closed, face lost/recovered. |

Evidence:

- `evidence/screen-recordings/ar-alignment-front-turn-mouth-YYYY-MM-DD.mp4`
- `evidence/screenshots/ar-alignment-representative-frame-YYYY-MM-DD.jpg`
- `evidence/logs/ar-alignment-runtime-YYYY-MM-DD.log`
- source/config cross-check for camera hierarchy and warning state

Decision criteria:

| Decision | Criteria |
| --- | --- |
| Green | 30s+ iPhone recording shows overlay aligned to face contour, eyes, mouth through movement/expression; runtime remains `SessionTracking`; warning is removed or proven harmless. |
| Yellow | Front-facing neutral pose aligns, but rotation/expression/reacquisition drifts or warning remains unresolved. |
| Red | Tracking is true but Unity overlay cannot be aligned to camera feed, or RN-hosted Unity breaks alignment while standalone works. |

Stop rule:

- Do not start region mask, texture, makeup quality, or product rendering while face mesh alignment remains Yellow/Fail.

#### 9.7.2 Trackable Lifecycle Plan

Purpose:

- Separate normal `MaximumFaceCount = 1` behavior, `Limited` tracking state, removed trackables, second-face behavior, and visual rendering bugs.

Minimum checks:

| Check | Required observation |
| --- | --- |
| `ARFaceManager.trackablesChanged` | Log added/updated/removed counts every change. |
| Trackable identity | Log trackable ID, timestamp, face transform, active face selection. |
| `ARFace.trackingState` | Distinguish Tracking, Limited, and None instead of relying on face count only. |
| `ARFace.updated` | Log per-face update timing and whether mesh data is updated. |
| Mesh availability | Log vertex/index/UV counts for the active face. |
| Scenarios | Same face in/out, same face reacquired, second face after first leaves, partial occlusion, near/far movement. |

Evidence:

- `evidence/logs/ar-trackable-lifecycle-YYYY-MM-DD.log`
- optional `evidence/screen-recordings/ar-trackable-lifecycle-scenarios-YYYY-MM-DD.mp4`
- summary table mapping each scenario to added/updated/removed/trackingState behavior

Decision criteria:

| Decision | Criteria |
| --- | --- |
| Green | Logs clearly explain whether face is added, updated, Limited, removed, or reacquired; first-face-only behavior is understood and can be represented in RN status. |
| Yellow | Lifecycle is mostly clear but second-face or reacquisition behavior remains inconsistent. |
| Red | Trackables remain ambiguous enough that renderer cannot know which face to attach to, or face state cannot recover in target UX. |

Stop rule:

- Do not design multi-face or second-person UX until lifecycle evidence explains current one-face behavior. Do not treat face count alone as engine state.

#### 9.7.3 Region Mask Plan

Purpose:

- Prove that `lip`, `cheek`, and `eye` can be independently controlled from recipe data and remain attached to the tracked face.

Minimum checks:

| Check | Required observation |
| --- | --- |
| Mesh/UV basis | Runtime confirms ARFace vertices/indices/UVs are available and stable enough for masks. |
| Region map | `lip`, `cheek`, `eye` candidate vertex/UV regions are visible as debug colors. |
| Layer dispatch | RN recipe `layer` changes only the selected region, not the whole face. |
| Region independence | Lip changes do not color cheek/eye; cheek changes do not color lip/eye; eye changes do not color lip/cheek. |
| Movement/expression | Regions stay attached through head rotation, mouth open/closed, face lost/recovered. |
| Diagnostic overlay separation | Whole-face diagnostic material is disabled or visually separated from makeup regions. |

Evidence:

- `evidence/screen-recordings/region-mask-lip-cheek-eye-YYYY-MM-DD.mp4`
- `evidence/screenshots/region-mask-lip-cheek-eye-YYYY-MM-DD.jpg`
- `evidence/logs/region-mask-layer-dispatch-YYYY-MM-DD.log`
- source/config cross-check for region provider and renderer path

Decision criteria:

| Decision | Criteria |
| --- | --- |
| Green | iPhone recording proves independent `lip`, `cheek`, `eye` color/opacity changes within 1s and regions remain attached through movement/expression. |
| Yellow | Regions are separated but edges are hard, slightly bleeding, or weaker under rotation/expression. |
| Red | ARFace mesh/UV path cannot produce stable region masks, or layer changes still affect the whole face. |

Stop rule:

- Do not add feather, texture, shimmer, product color fidelity, or AI recommendation until basic region separation is at least Yellow and preferably Green.

#### 9.7.4 Texture Sample Plan

Purpose:

- After stable region masks, prove that renderer fields beyond `color` and `opacity` can express visibly different makeup textures.

Minimum checks:

| Sample | Region | Required controls |
| --- | --- | --- |
| `matte_lip` | `lip` | `color`, `opacity`, `blendMode` |
| `soft_blush` | `cheek` | `color`, `opacity`, `feather`, `intensity` |
| `shimmer_eye` | `eye` | `color`, `opacity`, `texture`, `intensity` |

Additional checks:

- Compare at least two lighting or face-distance conditions.
- Confirm texture/intensity changes are visually distinct from opacity changes.
- Confirm samples remain restricted to their region.
- Watch runtime FPS/thermal behavior enough to catch obvious performance regressions.

Evidence:

- `evidence/screen-recordings/texture-samples-matte-shimmer-blush-YYYY-MM-DD.mp4`
- `evidence/screenshots/texture-samples-comparison-YYYY-MM-DD.jpg`
- `evidence/logs/texture-samples-runtime-YYYY-MM-DD.log`
- recipe JSON examples for each sample

Decision criteria:

| Decision | Criteria |
| --- | --- |
| Green | iPhone recording shows matte lip, soft blush, and shimmer eye as visually different, region-bounded effects; opacity and intensity are distinguishable. |
| Yellow | Texture differences exist but blending/feather/lighting quality is weak or only convincing in narrow conditions. |
| Red | Texture samples look like simple color overlays, break region stability, or cause unacceptable performance. |

Stop rule:

- Do not start product-by-product color fidelity, full makeup suite, catalog matching, or commercial-quality rendering until texture sample validation is at least Yellow.

### 9.8 Final Answer to Research Questions

| Question | Answer |
| --- | --- |
| 1. Primary path 유지? | Yes, but Yellow. RN-hosted Unity + AR Foundation + ARKit is still the best primary path because M0-M5 integration/tracking/message delivery are proven. Product makeup must wait for alignment and region mask gates. |
| 2. overlay offset / TPD warning 원인과 AR Alignment 관찰점? | Most plausible first candidate is AR Camera pose setup because current scene lacks serialized TrackedPoseDriver and runtime warning names it. Also check XR Origin hierarchy, ARCameraBackground/projection/render mode, face prefab transform, RN UnityView sizing/orientation, and lifecycle state. |
| 3. `trackablesChanged`, `ARFace.updated`, mesh data, trackingState 연결? | Build a diagnostics layer first. Use `trackablesChanged` for added/updated/removed lifecycle, `ARFace.updated` for per-face mesh updates, `trackingState` for Tracking vs Limited, and vertices/indices/UVs as region mask basis. |
| 4. v1 `lip`, `cheek`, `eye` mask 현실적 방식? | ARFace mesh/UV based debug region masks first, not 2D segmentation primary. Start with hard-color debug masks, then independent renderer/material dispatch, then shader/mask atlas. |
| 5. 검증 순서? | Alignment -> lifecycle/mesh/UV availability -> vertex/UV region map -> independent region materials/renderers -> submesh/material or mask atlas -> shader pass/layer stack -> texture/intensity. |
| 6. MediaPipe / ARCore fallback timing? | Use only if ARKit alignment/region/lifecycle fails, Android enters scope, non-TrueDepth support is required, or static AI analysis needs shared landmark topology. |
| 7. face parsing / makeup transfer 의미? | They justify renderer fields beyond color/opacity: region, feather, blendMode, texture, intensity, shade/degree control, UV/pose/expression consistency. |
| 8. usable dataset/model/code? | CelebAMask-HQ and LaPa can be used for non-commercial research/education with attribution and no redistribution. BiSeNet and SegFace code are MIT but datasets/weights follow upstream terms. Makeup transfer papers are references only until code/data license is verified. |

## Appendix A. Source Appendix

| Source | Core claim used in this report | Link | Repo evidence connected | Use condition |
| --- | --- | --- | --- | --- |
| Unity AR Face Manager 6.3 | `ARFaceManager` creates face GameObjects and reports added/updated/removed via `trackablesChanged`; has Face Prefab and Maximum Face Count. | https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/arfacemanager.html | Current scene uses `ARFaceManager`, `ValidationFaceOverlay` prefab, and `m_MaximumFaceCount: 1`. | Unity documentation; use as guidance with attribution/link. |
| Unity AR Face 6.3 | `ARFace` lifecycle includes added/updated/removed; `ARFace.updated` can update vertices/normals/indices/uvs; `trackingState` can become Limited. | https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/arface.html | Current `FaceTrackingStatusReporter.cs` logs face count but not `trackingState`, trackable ID, or mesh counts. | Unity documentation; use as guidance with attribution/link. |
| Unity Face Tracking Platform Support | ARKit and ARCore support face pose, mesh vertices/indices, and mesh UVs through AR Foundation descriptors. | https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/platform-support.html | `FaceTrackingStatusReporter.cs` already reads descriptor support fields; report recommends logging actual mesh counts next. | Unity documentation. |
| Unity Face Tracking Samples | Official samples cover face pose, face mesh, ARKit blend shapes, ARKit eye poses, and ARCore face regions. | https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/samples/features/face-tracking.html | Current custom scene should be compared against official Face Pose / Face Mesh sample setup. | Unity package/sample terms must be checked before copying assets/code. |
| Unity Scene Setup | AR scenes require AR Session and XR Origin; XR Origin transforms trackables into Unity coordinates. | https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/project-setup/scene-setup.html | `MakeupARValidationSetup.cs` manually creates `AR Session`, `XR Origin`, `Camera Offset`, and `AR Camera`. | Unity documentation. |
| Unity XR Origin reference | Recommended AR Main Camera components include `TrackedPoseDriver`, `ARCameraManager`, and `ARCameraBackground`. | https://docs.unity3d.com/Packages/com.unity.xr.core-utils%402.5/manual/xr-origin-reference.html | Runtime warning says AR Camera does not use Tracked Pose Driver; scene grep did not find serialized `TrackedPoseDriver`. | Unity documentation. |
| Unity Camera Components | `ARCameraManager` controls camera features and `ARCameraBackground` renders video background; User direction means front/selfie camera. | https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/camera/camera-components.html | Current scene has `ARCameraManager`, `ARCameraBackground`, and `m_FacingDirection: 2` / User. | Unity documentation. |
| Unity as a Library iOS | UnityFramework supports embedded runtime control, pause/unload, and `sendMessageToGOWithName`; limitations include full-screen rendering and one runtime instance. | https://docs.unity3d.com/Manual/UnityasaLibrary-iOS.html | M3/M4/M5 use generated `UnityFramework.framework`; M7 must validate unload/pause/re-enter behavior. | Unity license/runtime terms apply. |
| `@azesmway/react-native-unity` | Provides `UnityView`, `postMessage`, `onUnityMessage`, `unloadUnity`, `pauseUnity`; iOS simulator unsupported; iOS view needs dimensions. | https://github.com/azesmway/react-native-unity | Current `App.tsx` uses `UnityView.postMessage`; no `onUnityMessage` yet. M4 had view timing caveat. | MIT for bridge code; UnityFramework/runtime terms separate. |
| MediaPipe Face Landmarker | Outputs 3D landmarks, blendshapes, and transformation matrices for image/video/live stream; model bundle includes dense face mesh and blendshape model. | https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker | Not used in repo. Kept as fallback/comparison if ARKit path fails or shared landmark topology is needed. | Docs CC BY 4.0, code samples Apache 2.0; model/runtime terms must be checked. |
| ARCore Augmented Faces | Provides center pose, three region poses, and 468-point 3D mesh without specialized hardware. | https://developers.google.com/ar/develop/augmented-faces | Not used in repo. Kept for Android/fallback comparison, not current iPhone scope. | Docs CC BY 4.0, code samples Apache 2.0; ARCore SDK terms apply. |
| CelebAMask-HQ | 30,000 high-res face images and 19 semantic classes including eyes, mouth, lip, skin, hair, accessories. | https://github.com/switchablenorms/CelebAMask-HQ | Not used in repo. Useful as non-commercial face parsing reference for region semantics. | Non-commercial research/educational only; no commercial exploitation or redistribution. |
| LaPa Dataset | 22,000+ images, 11-category labels, and 106-point landmarks for face parsing. | https://github.com/jd-opensource/lapa-dataset | Not used in repo. Useful as research reference for parsing/landmark relationships. | Non-commercial research, teaching, scientific publication, personal experimentation; license terms agreement required. |
| BiSeNet face parsing PyTorch | Practical CelebAMask-HQ-style face parsing implementation with pretrained model link. | https://github.com/zllrunning/face-parsing.PyTorch | Not used in repo. Useful for offline mask prototype/reference only. | Code MIT; dataset and weights follow upstream terms. |
| SegFace | Long-tail face segmentation reference with CelebAMask-HQ/LaPa results and mobile backbone discussion. | https://github.com/Kartik-3004/SegFace | Not used in repo. Useful as face parsing benchmark/reference. | Code MIT; weights/datasets need separate terms review. |
| PSGAN | Makeup transfer paper emphasizing pose/expression robustness, partial transfer, and shade control. | https://arxiv.org/abs/1909.06956 | Not used in repo. Supports renderer fields `layer` and `intensity`. | Paper reference only until code/data license is verified. |
| SARA | Makeup transfer paper emphasizing spatial alignment, region-adaptive normalization, part-specific and shade-controllable transfer. | https://arxiv.org/abs/2311.16828 | Not used in repo. Supports alignment-first and region-aware architecture. | Paper reference only until code/data license is verified. |
| BeautyBank | Makeup latent encoding paper emphasizing detailed pattern preservation. | https://arxiv.org/abs/2411.11231 | Not used in repo. Supports `texture` and `intensity` as separate renderer fields. | Paper reference only; dataset/code terms must be checked. |
| AvatarMakeup | 3D avatar makeup paper emphasizing expression/view consistency and global UV map direction. | https://arxiv.org/abs/2507.02419 | Not used in repo. Supports UV-space mask/texture direction after alignment. | Paper reference only; code/data terms must be checked. |
| FFHQ-Makeup | Paired synthetic bare/makeup dataset paper preserving identity/expression across styles. | https://arxiv.org/abs/2508.03241 | Not used in repo. Future AI/recommendation/feedback research reference, not v1 runtime renderer. | Paper reference only; dataset availability/license must be checked. |
