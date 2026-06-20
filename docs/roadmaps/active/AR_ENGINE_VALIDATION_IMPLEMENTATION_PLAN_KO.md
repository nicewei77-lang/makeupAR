# AR Engine Validation Implementation Plan - 한국어

Date: 2026-06-21 KST

Status: Active validation implementation plan / M8 foundation closeout complete / next gate is E1 or optional M7 re-check

## 0. 현재 사용법

이 문서는 `TECH_VALIDATION_TEST_PLAN.md`와 `TECH_VALIDATION_RESULT.md` 다음에 읽는 AR engine validation 작업 지시서다. 현재 루트 active 문서는 계속 아래 3개만 유지한다.

- `AGENTS.md`
- `TECH_VALIDATION_TEST_PLAN.md`
- `TECH_VALIDATION_RESULT.md`

현재 진행 기준:

- M0-M6는 Green이다.
- M7은 `Yellow / skipped by decision / risk accepted`이며 Green이 아니다.
- M8 결과 리포트는 완료되었다.
- M7 lifecycle risk를 수용하면 다음 작업은 E1 AR Alignment다.
- lifecycle confidence를 먼저 확보해야 한다면 추가 M7 re-entry verification을 먼저 수행한다.
- E1 전에는 region mask, texture rendering, product-quality makeup rendering, AI/backend/admin/payment/community, commercial SDK, Android 작업을 시작하지 않는다.

## 1. 목적

이 문서는 `TECH_VALIDATION_TEST_PLAN.md`, `TECH_VALIDATION_RESULT.md`, AR 엔진 리서치 보고서, 상용 뷰티 AR 벤치마크 보고서를 바탕으로, validation용 AR makeup engine을 실제로 구현하기 위한 마일스톤 계획을 정의한다.

현재 목표는 제품 개발이 아니라 다음 질문에 답하는 것이다.

> RN-hosted Unity + AR Foundation + ARKit 기반에서 얼굴 위에 `lip`, `cheek`, `eye` 메이크업 layer를 안정적으로 얹을 수 있는가?

현재 foundation 상태:

- M0-M6는 Green이다.
- M7은 Yellow / skipped by decision / risk accepted다.
- M8 foundation closeout은 완료되었다.
- RN app은 iPhone에서 Unity AR 화면을 연다.
- ARKit face tracking은 `SessionTracking`, `Face detected: true`까지 확인되었다.
- RN은 Unity `RNBridge.ApplyRecipeJson(string)`으로 `layer/color/opacity`를 보낸다.
- Unity는 color/opacity를 diagnostic whole-face overlay material에 적용한다.
- Unity는 RN으로 `unity_initialized`, `face_detected`, `recipe_applied` event를 보내고 RN 화면은 이를 표시한다.
- 하지만 현재 overlay는 얼굴에 맞지 않고 offset되어 있다.
- 현재 `layer: "lip"`은 실제 lip region으로 route되지 않는다.
- product-quality makeup rendering은 아직 시작하지 않았다.

## 2. 절대 범위

### 포함

- M6 Unity -> RN communication
- M7 AR screen re-entry stability
- M8 foundation closeout
- AR camera / face mesh alignment
- `ARFaceManager.trackablesChanged` 기반 lifecycle diagnostics
- `ARFace` mesh/UV 기반 `lip`, `cheek`, `eye` region mask validation
- 최소 texture sample validation: `matte_lip`, `soft_blush`, `shimmer_eye`
- AI feature extraction readiness handoff contract
- 실기기 evidence 기록

### 제외

- 로그인, backend, DB, admin, payment, community
- AI 추천, AI model inference, AI face analysis product implementation, makeup transfer
- 상용 SDK 통합: Perfect Corp, Banuba, DeepAR, Snap Camera Kit
- TikTok/Instagram/Snap platform effect runtime 의존
- Android/ARCore 구현
- foundation shade matching, skin smoothing, relighting
- 제품별 완전 발색 재현
- multi-face social effect

이번 validation에서 "얼굴의 각 부위"는 `lip`, `cheek`, `eye` 3개만 의미한다. `brow`, `nose`, `jaw`, `skin/foundation`, `lash`, `teeth`는 상용 엔진 벤치마크상 중요한 region이지만, 이 문서에서는 후속 product scope로 남긴다.

## 3. 구현 순서 요약

순서를 바꾸지 않는다. 앞 gate가 Red이면 다음 gate를 시작하지 않는다.

| Order | Milestone | Goal | Green output |
| --- | --- | --- | --- |
| 1 | M6 Unity -> RN Events | Unity 상태를 RN 화면에서 확인 | RN receives `unity_initialized`, `face_detected`, `recipe_applied` |
| 2 | M7 Re-entry Stability | AR 화면 lifecycle 안정성 확인 | Start/Close 3회 + background/foreground 통과 |
| 3 | M8 Foundation Closeout | 기존 RN-Unity 검증 닫기 | `TECH_VALIDATION_RESULT.md`가 integration과 visual readiness를 분리 |
| 4 | E1 AR Alignment | camera feed와 `ARFace` mesh 정렬 | 30초 recording에서 overlay가 face contour/eyes/mouth에 정렬 |
| 5 | E2 Trackable Lifecycle | face lost/recovered/second-face 상태 분리 | added/updated/removed, ID, trackingState, mesh count log |
| 6 | E3 Region Mask | `lip`, `cheek`, `eye` 독립 제어 | region별 color/opacity가 독립 적용 |
| 7 | E4 Texture Sample | 최소 질감 표현 검증 | matte lip / soft blush / shimmer eye 구분 |
| 8 | E5 AI Feature Readiness | AI가 소비할 얼굴 feature snapshot 준비 | no-inference `FaceFeatureSnapshot` schema and sample logs |
| 9 | E6 Engine Decision | AR engine v1 가능성 판정 | Green/Yellow/Red decision and next product boundary |

## 4. Milestone M6 - Unity -> RN Events

### 목적

Unity AR 상태가 RN host app에 보이게 만든다. 이후 AR engine work는 RN이 Unity 상태를 관찰할 수 있어야 진행한다.

### 구현 파일

| Area | File |
| --- | --- |
| RN event receiver | `rn/MakeupARValidation/App.tsx` |
| RN Unity type support | `rn/MakeupARValidation/react-native-unity.d.ts` |
| Unity event bridge | `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs` 또는 새 `UnityEventBridge.cs` |
| Unity face state source | `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs` |
| iOS native send path | `unity/MakeupARUnityValidation/Assets/Plugins/iOS/NativeCallProxy.mm` |

### Event contract

Unity -> RN message는 JSON string이다.

```json
{"type":"unity_initialized"}
{"type":"face_detected","tracked":true,"faceCount":1}
{"type":"face_detected","tracked":false,"faceCount":0}
{"type":"recipe_applied","layer":"lip","color":"#D94B74","opacity":0.65}
```

### Unity implementation detail

- Unity C#에서 iOS native function을 호출하는 얇은 sender를 만든다.
- iOS device에서는 `sendMessageToMobileApp(string message)`를 호출한다.
- Unity Editor 또는 non-iOS에서는 native 호출 대신 `Debug.Log`만 남긴다.
- `Awake` 또는 `Start` 시점에 `unity_initialized`를 한 번 보낸다.
- recipe 적용 성공 시 `recipe_applied`를 보낸다.
- face count가 변할 때만 `face_detected`를 보낸다.
- face count만 보낼 때도 `tracked` boolean을 포함한다.
- JSON 생성 실패나 native send 실패는 Unity log에 남긴다.

### RN implementation detail

- `UnityView`에 `onUnityMessage` prop을 연결한다.
- `event.nativeEvent.message`를 JSON parse한다.
- parse 성공 시 `lastUnityEvent` state에 저장하고 debug panel에 표시한다.
- parse 실패 시 raw message와 parse error를 표시한다.
- 최근 5개 event history를 debug panel에 표시한다.
- 기존 color/opacity controls는 유지한다.

### Green criteria

- RN 화면에 `unity_initialized`가 표시된다.
- 얼굴을 비추면 `face_detected tracked=true faceCount=1`이 표시된다.
- 얼굴을 화면 밖으로 빼면 `face_detected tracked=false faceCount=0` 또는 equivalent lost state가 표시된다.
- color/opacity 변경 후 `recipe_applied`가 RN 화면에 표시된다.
- runtime log에 Unity send와 RN receipt가 모두 남는다.

### Evidence

- `evidence/screen-recordings/m6-unity-to-rn-events-YYYY-MM-DD.mp4`
- `evidence/screenshots/m6-rn-latest-event-YYYY-MM-DD.jpg`
- `evidence/logs/m6-unity-to-rn-runtime-YYYY-MM-DD.log`
- `evidence/logs/m6-build-install-run-YYYY-MM-DD.log`

### Stop rule

M6가 Green이 되기 전에는 M7, AR alignment, region mask를 시작하지 않는다.

## 5. Milestone M7 - Re-entry Stability

### 목적

Unity AR 화면을 실제 앱 flow에서 여러 번 열고 닫아도 crash, black screen, camera leak이 없는지 확인한다.

### 구현/검증 정책

- 1차 전략은 현재 구조를 유지한다: RN state로 `UnityScreen` mount/unmount.
- 문제가 있으면 비교 전략을 추가한다:
  - `pauseUnity(true/false)`
  - `unloadUnity()`
  - UnityView를 unmount하지 않고 full-screen view hide/show
- 어떤 전략을 사용했는지 `TECH_VALIDATION_RESULT.md`에 명확히 기록한다.

### Test scenario

1. RN Home 실행
2. `Start AR`
3. `unity_initialized` event 확인
4. 얼굴 인식 event 확인
5. color 변경
6. opacity 변경
7. `recipe_applied` event 확인
8. `Close`
9. Home 복귀
10. 위 과정을 3회 반복
11. background/foreground 1회 수행
12. Close 후 camera indicator가 남는지 확인

### Green criteria

- 3회 반복 중 crash가 없다.
- black screen이 없다.
- 재진입 후에도 Unity event가 RN에 표시된다.
- 재진입 후에도 ARKit face tracking이 동작한다.
- Close 후 camera indicator가 비정상적으로 유지되지 않는다.

### Evidence

- `evidence/screen-recordings/m7-reentry-3x-YYYY-MM-DD.mp4`
- `evidence/logs/m7-reentry-runtime-YYYY-MM-DD.log`
- `evidence/screenshots/m7-camera-indicator-after-close-YYYY-MM-DD.jpg`

### Stop rule

M7이 Green 또는 명확한 Yellow workaround로 정리되기 전에는 AR engine renderer work를 시작하지 않는다.

## 6. Milestone M8 - Foundation Closeout

### 목적

첫 번째 RN + Unity + AR Foundation validation을 닫고, AR engine validation으로 넘어갈 수 있는지 판정한다.

### 문서 업데이트

`TECH_VALIDATION_RESULT.md`에 아래 항목을 분리 기록한다.

| Area | Expected status |
| --- | --- |
| RN iOS host | Green |
| UnityFramework embed | Green |
| RN -> Unity recipe path | Green |
| Unity -> RN event path | M6 result |
| Re-entry lifecycle | M7 result |
| ARKit face tracking | Green |
| Face-fitted rendering | Yellow/Fail until E1 |
| Region renderer | Not started until E3 |
| Product makeup readiness | Not ready |
| Clean rebuild/reinstall reproducibility | M6/M7 result plus any remaining local caveat |

### Green criteria

- M6/M7 evidence path가 결과 문서에 들어간다.
- M0-M7 history가 한 표로 정리된다.
- Next Milestone Boundary가 E1 AR Alignment로 갱신된다.
- visual makeup readiness가 integration Green과 분리되어 기록된다.
- `node_modules` package framework sync와 `RNUnityView.mm` timing patch가 durable path로 정리되었거나, 남은 local caveat와 clean rebuild 영향이 Yellow workaround로 명시된다.

### Stop rule

M8에서 visual makeup을 Green으로 적지 않는다. E1/E3 evidence가 생기기 전까지 product makeup readiness는 Yellow/Fail 또는 Not Ready다.

## 7. Milestone E1 - AR Alignment

### 목적

현재 offset된 diagnostic overlay를 live front-camera feed의 얼굴 contour, eyes, mouth에 맞춘다.

### 구현 파일

| Area | File |
| --- | --- |
| Scene generator | `unity/MakeupARUnityValidation/Assets/Editor/MakeupARValidationSetup.cs` |
| Scene asset | `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity` |
| Face prefab | `unity/MakeupARUnityValidation/Assets/Prefabs/ValidationFaceOverlay.prefab` |
| Diagnostic marker | `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingMarker.cs` |
| Status/logging | `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs` |

### Main hypotheses

| Hypothesis | Why |
| --- | --- |
| Missing camera pose driver | Runtime log says AR Camera does not use Tracked Pose Driver |
| XR Origin hierarchy mismatch | Current scene is generated manually |
| ARCameraBackground/projection mismatch | Camera feed and overlay may use different pose/projection assumptions |
| Face prefab marker offset | `FaceTrackingMarker` creates extra runtime geometry |
| RN-hosted view sizing/orientation issue | M4 required a local UnityView timing patch |

### Implementation detail

- Compare current generated hierarchy with Unity official AR Foundation scene setup.
- Add or configure the correct AR camera pose update component for Unity 6.3 / AR Foundation 6.3 / Input System.
- Ensure AR Camera keeps `ARCameraManager` and `ARCameraBackground`.
- Create diagnostic modes:
  - mesh-only: `ARFaceMeshVisualizer` on, `FaceTrackingMarker` off
  - marker-only: marker on, mesh transparent/off
  - combined: current view
- Log camera transform, XR Origin transform, face transform, active screen orientation, active `trackableId`, `trackingState`, and mesh vertex/index/UV counts.
- Do not wait until E2 to collect the minimum lifecycle telemetry needed to explain an E1 alignment failure.
- Compare RN-hosted Unity and Unity standalone using same scene and iPhone orientation.

### Green criteria

- 30초 이상 iPhone recording에서 overlay가 face contour, eyes, mouth에 맞는다.
- 정면, 좌/우 회전, 위/아래 움직임, 입 벌림, face lost/recovered를 포함한다.
- runtime log는 `SessionTracking`, active face, mesh/UV availability를 보여준다.
- runtime log는 같은 recording 구간의 active `trackableId`, `trackingState`, face transform, camera transform을 함께 보여준다.
- Tracked Pose Driver warning은 제거되거나 harmless임이 evidence로 설명된다.

### Evidence

- `evidence/screen-recordings/e1-ar-alignment-front-turn-mouth-YYYY-MM-DD.mp4`
- `evidence/screenshots/e1-ar-alignment-frame-YYYY-MM-DD.jpg`
- `evidence/logs/e1-ar-alignment-runtime-YYYY-MM-DD.log`
- `evidence/logs/e1-scene-camera-config-YYYY-MM-DD.log`

### Stop rule

E1이 Yellow/Fail이면 region mask와 texture sample을 시작하지 않는다.

## 8. Milestone E2 - Trackable Lifecycle Diagnostics

### 목적

first-face-only, lost/recovered, second-face behavior를 명확히 분리한다.

### 구현 파일

- `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs`
- 필요 시 새 `FaceTrackableDiagnostics.cs`
- M6 이후 RN event display in `rn/MakeupARValidation/App.tsx`

### Required diagnostics

| Signal | Required fields |
| --- | --- |
| `trackablesChanged.added` | count, trackable ID, timestamp |
| `trackablesChanged.updated` | count, active ID, trackingState |
| `trackablesChanged.removed` | count, removed ID |
| `ARFace.updated` | ID, vertex count, index count, UV count |
| face transform | position, rotation |
| active face summary | selected ID, count, tracked boolean |
| provider capability snapshot | mesh vertices/indices/UVs, blendshape or eye-pose availability if exposed |

### Test scenarios

- Same face appears.
- Same face leaves.
- Same face returns.
- First face leaves, second face appears.
- Face is partially covered.
- Face moves near/far.

### Green criteria

- Logs explain whether a face is Tracking, Limited, removed, or reacquired.
- First-face-only behavior is either accepted as v1 policy or documented as a blocker.
- RN can show simplified status:
  - `tracking`
  - `limited`
  - `lost`
  - `reacquired`

### Evidence

- `evidence/logs/e2-trackable-lifecycle-YYYY-MM-DD.log`
- `evidence/screen-recordings/e2-trackable-lifecycle-scenarios-YYYY-MM-DD.mp4`
- `evidence/screenshots/e2-rn-face-state-YYYY-MM-DD.jpg`

### Stop rule

Do not design multi-face UX. v1 remains one-face only unless a later milestone explicitly changes the target.

## 9. Milestone E3 - Region Mask Validation

### 목적

`lip`, `cheek`, `eye`가 독립적으로 제어되는 최소 AR makeup renderer를 만든다.

### Implementation policy

- Current whole-face diagnostic material remains only as a baseline.
- Region mask starts with visible debug colors, not beauty-quality makeup.
- Primary coordinate basis is `ARFace` mesh/UV.
- Screen-space 2D segmentation is fallback only.
- Region renderer should be easy to debug before shader optimization.

### Recipe contract

RN -> Unity payload evolves to versioned multi-layer JSON.

```json
{
  "version": 1,
  "layers": [
    {
      "id": "lip-primary",
      "region": "lip",
      "color": "#D94B74",
      "opacity": 0.65,
      "enabled": true
    }
  ]
}
```

`region` is the canonical E3 field. Existing `layer` may remain as a legacy alias during migration from M5, but E3 is not Green until Unity dispatches by actual region.

### RN UI changes

- Add region selector:
  - `lip`
  - `cheek`
  - `eye`
- Keep color controls:
  - rose `#D94B74`
  - coral `#E67B5F`
  - nude `#B9826B`
- Keep opacity slider.
- Display latest Unity event.
- Post full recipe JSON on region/color/opacity changes.

### Unity modules

| Module | Responsibility |
| --- | --- |
| `MakeupRecipeReceiver` | Parse `version` and `layers[]` |
| `FaceRegionMaskProvider` | Provide `lip`, `cheek`, `eye` mask source from ARFace mesh/UV |
| `MakeupLayerRenderer` | Apply layer color/opacity to selected region |
| `RegionDebugOverlay` | Show selected region with hard debug color |

### Minimum behavior

- `region=lip` changes only lip.
- `region=cheek` changes only cheek.
- `region=eye` changes only eye.
- Changing opacity affects only selected region.
- Applying one layer does not erase other enabled layers.
- Whole-face diagnostic overlay can be toggled off or visually separated.

### Region QA focus

| Region | Validation focus |
| --- | --- |
| `lip` | upper/lower lip fit, mouth opening behavior, no forehead/jaw bleed |
| `cheek` | soft bounded cheek area, no lip/eye contamination, acceptable edge softness direction |
| `eye` | left/right eye area stability, head rotation drift, simple eyeshadow-like placement only |

### Green criteria

- iPhone recording proves lip, cheek, eye are independently controlled.
- Region changes apply within 1 second.
- Region stays attached through head rotation, expression, and lost/recovered.
- Runtime log records recipe parse, region dispatch, and applied region.

### Evidence

- `evidence/screen-recordings/e3-region-mask-lip-cheek-eye-YYYY-MM-DD.mp4`
- `evidence/screenshots/e3-region-mask-debug-colors-YYYY-MM-DD.jpg`
- `evidence/logs/e3-region-mask-layer-dispatch-YYYY-MM-DD.log`
- `docs/runbooks/E3_REGION_MASK_VALIDATION_RUNBOOK.md` if the procedure becomes reusable

### Stop rule

Do not add texture, shimmer, product catalog, AI recommendation, or product color fidelity before E3 is at least Yellow and preferably Green.

## 10. Milestone E4 - Texture Sample Validation

### 목적

Region mask 위에서 기본 makeup texture 차이가 표현되는지 검증한다.

### Required samples

| Sample | Region | Required controls |
| --- | --- | --- |
| `matte_lip` | `lip` | `color`, `opacity`, `blendMode` |
| `soft_blush` | `cheek` | `color`, `opacity`, `feather`, `intensity` |
| `shimmer_eye` | `eye` | `color`, `opacity`, `texture`, `intensity` |

### Recipe extension

```json
{
  "version": 1,
  "layers": [
    {
      "id": "eye-shimmer",
      "region": "eye",
      "color": "#E6A0A8",
      "opacity": 0.55,
      "feather": 0.2,
      "blendMode": "normal",
      "texture": "shimmer_eye",
      "intensity": 0.8,
      "enabled": true
    }
  ]
}
```

### Unity implementation detail

- Add shader/material path only after E3 region stability.
- Start with simple unlit transparent materials.
- Add feather by mask edge softness or alpha gradient.
- Add `blendMode` with limited enum:
  - `normal`
  - `multiply`
  - `screen`
- Add named texture/pattern samples:
  - `matte_lip`
  - `soft_blush`
  - `shimmer_eye`
- Keep layer count to 3 or fewer in E4.
- Keep live segmentation out of E4 unless E3 explicitly shows mesh/UV masks cannot represent a target region.

### Performance budget

- One active face.
- Three active makeup layers or fewer.
- Simple/unlit transparent materials first; avoid PBR and heavy shader sampling.
- Small sample textures, preferably 1024 px or smaller per edge during validation.
- Record visible FPS/stutter, thermal warning, and device heat observations in the runtime log or result note.

### Green criteria

- iPhone recording shows three samples are visually distinct.
- Opacity and intensity have different visible effects.
- Samples stay inside their regions.
- No obvious frame drop, thermal issue, or tracking instability appears during the test; if FPS is measurable, no sustained sub-20fps segment is accepted as Green.

### Evidence

- `evidence/screen-recordings/e4-texture-samples-matte-shimmer-blush-YYYY-MM-DD.mp4`
- `evidence/screenshots/e4-texture-samples-comparison-YYYY-MM-DD.jpg`
- `evidence/logs/e4-texture-samples-runtime-YYYY-MM-DD.log`
- recipe examples stored as text in the log or linked from the result doc

### Stop rule

Do not start product-by-product color fidelity, foundation, skin smoothing, relighting, or commercial-quality rendering until E4 is at least Yellow.

## 11. Milestone E5 - AI Feature Extraction Readiness Handoff

### 목적

AI 추천이나 AI face analysis를 구현하지 않고, 이후 AI가 얼굴 특징을 소비할 수 있는 최소 feature snapshot 계약이 준비되었는지 검증한다.

### Scope boundary

- This milestone creates schema, logs, and sample snapshots only.
- No AI model, recommendation, backend, upload, storage service, or makeup transfer is implemented.
- No raw camera frame is stored or exported unless a later explicit privacy-reviewed milestone adds it.

### `FaceFeatureSnapshot` draft contract

```json
{
  "schemaVersion": 1,
  "timestampMs": 0,
  "source": "arkit_arface",
  "deviceModel": "iPhone17,3",
  "arSessionState": "SessionTracking",
  "cameraFacing": "User",
  "orientation": "portrait",
  "activeFace": {
    "trackableId": "example",
    "trackingState": "Tracking",
    "lifecycleState": "tracking",
    "pose": {
      "position": [0, 0, 0],
      "rotationEuler": [0, 0, 0]
    }
  },
  "mesh": {
    "vertexCount": 0,
    "indexCount": 0,
    "uvCount": 0,
    "hasStableUv": false
  },
  "regions": {
    "lip": {"available": true, "maskSource": "arface_uv", "qaStatus": "green"},
    "cheek": {"available": true, "maskSource": "arface_uv", "qaStatus": "yellow"},
    "eye": {"available": true, "maskSource": "arface_uv", "qaStatus": "yellow"}
  },
  "capabilities": {
    "blendShapesAvailable": false,
    "eyePoseAvailable": false
  },
  "privacy": {
    "rawCameraFrameStored": false,
    "offDeviceUpload": false
  }
}
```

### Required sample scenarios

- Neutral front face.
- Left/right head turn.
- Mouth open/closed.
- Face lost/recovered.
- Region mask applied for `lip`, `cheek`, and `eye`.

### Green criteria

- Runtime logs or exported JSON examples show the snapshot contract for the required scenarios.
- `trackableId`, `trackingState`, lifecycle state, mesh counts, and region availability are filled from real-device runtime data or clearly marked unavailable.
- Snapshot separates tracking data, region mask data, rendering QA status, and privacy status.
- AI can later consume stable geometry/region state without guessing from screenshots.
- No AI inference, recommendation, raw-frame upload, or backend path is introduced.

### Evidence

- `evidence/logs/e5-face-feature-snapshot-YYYY-MM-DD.log`
- `evidence/screenshots/e5-feature-snapshot-rn-debug-YYYY-MM-DD.jpg` if RN displays the summary
- `docs/runbooks/E5_FACE_FEATURE_SNAPSHOT_RUNBOOK.md` if the export procedure becomes reusable

### Stop rule

Do not claim AI face analysis readiness if the snapshot lacks stable face identity, tracking state, mesh/UV availability, region QA status, or privacy flags.

## 12. Milestone E6 - Engine Decision

### 목적

Validation용 AR engine 제작 가능성을 Green/Yellow/Red로 닫고, 제품 개발로 넘어갈 수 있는지 판단한다.

### Decision table

| Layer | Green condition |
| --- | --- |
| Integration | M6/M7/M8 all Green or acceptable Yellow with documented workaround |
| Tracking | Face state is observable in RN and runtime logs |
| Alignment | Face overlay is aligned with camera feed |
| Lifecycle | Lost/recovered and first-face-only behavior are understood |
| Region | `lip`, `cheek`, `eye` independently controlled |
| Texture | 3 samples are visually distinct |
| Performance | No obvious real-device degradation during validation |
| AI feature readiness | `FaceFeatureSnapshot` contract has real-device samples and no hidden raw-frame/backend dependency |

### Final decision outcomes

| Decision | Meaning |
| --- | --- |
| Green | Build product v1 on current RN + Unity + ARKit path |
| Yellow | Continue, but schedule focused spikes for remaining weak layer |
| Red | Do not continue product work until blocker is solved or fallback path is selected |

### Fallback triggers

Use MediaPipe or ARCore comparison only if one of these happens:

- ARKit/AR Foundation overlay cannot be aligned to the camera feed.
- `ARFace` mesh/UV cannot produce stable `lip`, `cheek`, `eye` masks.
- lifecycle/reacquisition behavior blocks target UX.
- Android support becomes an explicit validation target.
- static AI analysis must share a landmark topology with runtime AR.

## 13. Evidence and Documentation Rules

- Store logs under `evidence/logs/`.
- Store screenshots under `evidence/screenshots/`.
- Store recordings under `evidence/screen-recordings/`.
- Store feature snapshot examples as logs or runbook-linked text artifacts; do not store raw camera frames by default.
- Put reusable procedures in `docs/runbooks/`.
- Do not keep `unity-builds/`, Unity `Library/`, `Logs/`, `UserSettings/`, Xcode `derived-data/`, `.DS_Store`, or generated framework artifacts in source control.
- Root active docs remain limited to:
  - `AGENTS.md`
  - `TECH_VALIDATION_TEST_PLAN.md`
  - `TECH_VALIDATION_RESULT.md`
- Temporary session plans may be named `M6_..._PLAN.md`, `E1_..._PLAN.md`, etc., but must be absorbed into `TECH_VALIDATION_RESULT.md` and deleted after completion.

## 14. Current Next Session Prompt

Use this as the next implementation session goal if the M7 lifecycle risk remains accepted.

```md
# Goal: E1 AR Alignment 구현 및 실기기 검증

Workspace: `/Users/wiseungcheol/Desktop/makeupAR`

Required reading order:

1. `AGENTS.md`
2. `TECH_VALIDATION_TEST_PLAN.md`
3. `TECH_VALIDATION_RESULT.md`
4. `docs/roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md`
5. `docs/roadmaps/research/AR_ENGINE_RESEARCH_REPORT_KO.md`
6. `unity/MakeupARUnityValidation/Assets/Editor/MakeupARValidationSetup.cs`
7. `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity`
8. `unity/MakeupARUnityValidation/Assets/Prefabs/ValidationFaceOverlay.prefab`
9. `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingMarker.cs`
10. `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs`
11. `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`

Current boundary:

- M0-M6 are Green.
- M7 is Yellow / skipped by decision / risk accepted.
- M8 foundation closeout is complete.
- Next primary milestone is E1 AR Alignment.
- Do not start region masks, texture rendering, product-quality makeup rendering, AI/backend/admin/payment/community, commercial SDK integration, Android work, or product implementation.

Implement only E1:

- Fix or explain the current camera/feed/ARFace mesh alignment problem.
- Compare the scene setup against Unity AR Foundation 6.3 iOS face tracking expectations.
- Address the `AR Camera` pose warning or document why it is harmless with evidence.
- Add the minimum diagnostics needed for E1: camera transform, XR Origin transform, face transform, active orientation, trackable ID, trackingState, mesh vertex/index/UV counts.
- Keep the renderer diagnostic. Do not implement lip/cheek/eye region masks yet.

Verify on real iPhone:

- Record at least 30 seconds with front face, left/right head turn, up/down movement, mouth open/closed, and face lost/recovered.
- Confirm whether the overlay is aligned to face contour, eyes, and mouth.
- Save runtime logs under `evidence/logs/`.
- Save screenshot or screen recording under `evidence/screenshots/` or `evidence/screen-recordings/`.

Update:

- Update `TECH_VALIDATION_RESULT.md` with E1 decision, evidence, limitations, and next boundary.
- If E1 is Green, next boundary is E2 Trackable Lifecycle or E3 Region Mask depending on whether lifecycle diagnostics are already sufficient.
- If E1 is Yellow/Fail, do not start E3 region mask or E4 texture sample work.

Stop rule:

- Do not mark face-fitted rendering Green unless real-device evidence shows the overlay aligned with the camera feed and face mesh.
```

If formal lifecycle confidence is required before E1, use a narrower additional M7 re-entry verification session instead. That session must keep M7 Yellow until a 3-cycle evidence pass is actually recorded.
