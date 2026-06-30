# MediaPipe-First AR Makeup Architecture

Status: Accepted for product-coordinate implementation
Decision date: 2026-06-30

## Decision

AR makeup의 product coordinate system은 MediaPipe canonical face space로
고정한다.

ARKit은 iOS camera, session, depth, fallback을 돕는 assist layer로 남지만,
ARKit UV는 더 이상 lip, cheek, brow, eye 메이크업 배치의 product source가
아니다.

## Consequences

- Makeup asset은 MediaPipe/ARCore canonical face texture space를 기준으로
  제작하고 검증한다.
- Runtime makeup placement는 MediaPipe Face Landmarker packet이 주도한다.
- Product renderer는 Unity `ReadPixels`와 PNG detector input 조합에 의존하면
  안 된다.
- ARKit face mesh/UV renderer는 MediaPipe-first renderer가 parity에 도달할
  때까지 compatibility/debug route로만 유지한다.

## Implementation Contract

MediaPipe canonical face space는 제품 asset의 의미 좌표계다. PSD-derived lip,
cheek, brow, 그리고 나중에 authored canonical eye가 준비되면 eye asset은
canonical full-face texture canvas 위에서 위치와 밀도를 해석해야 하며,
런타임에서 각 부위가 어디에 붙을지는 MediaPipe Face Landmarker가 제공하는
full-face landmark packet을 기준으로 계산한다.

ARKit/AR Foundation은 iOS에서 계속 유용하다. Camera session 유지, AR view
통합, depth/fallback, 기존 디버그 mesh 확인 같은 역할은 유지할 수 있다.
다만 ARKit `ARFace` UV는 장기 제품 좌표계가 아니므로 새 제품 placement
contract의 semantic source로 쓰지 않는다.

## Compatibility Notes

기존 ARKit UV atlas renderer, smooth-region-mask route, ARFace mesh/UV 진단은
당장 제거하지 않는다. 이 경로들은 MediaPipe-first renderer가 lip, cheek,
brow, eye에서 기존 품질과 기능을 따라잡을 때까지 비교, QA, fallback,
compatibility 목적으로 유지한다.

새 구현은 `ReadPixels`로 카메라 프레임을 PNG로 만든 뒤 detector에 넣는
흐름을 제품 경로로 만들지 않는다. Detector 입력은 승인된 on-device runtime
안에서 transient in-memory data로 처리하고, raw frame 저장이나 업로드를
하지 않는다.

## Runtime Projection And Stale Frames

Current product detector input is the direct AR camera CPU-image path, not a
screen readback path. Unity receives `ARCameraManager.frameReceived`, acquires
the latest `XRCpuImage`, downsizes the long edge to 720 px, converts it to
BGRA into a reused pinned buffer, and calls the iOS app target through
`E7MediaPipeDetectFullFaceBgra` with the pinned pointer. Swift wraps that
memory-only BGRA buffer as a `CVPixelBuffer` and runs MediaPipe with
`MPImage(pixelBuffer:)` in `.video` mode. Capture is throttled to 15 fps for the
first product pass. This is intentionally different from the old
`ReadPixels -> EncodeToPNG -> detector` path and avoids per-capture managed
pin/unpin churn on the Unity conversion step. The runtime also reuses fixed
transformation fallback buffers, so the orientation retry path does not allocate
candidate arrays every capture. Lip, cheek, and brow region solving exposes
preallocated-buffer APIs for the product overlay and heartbeat/status path, so
region coordinate extraction does not allocate new point arrays every rendered
frame.

The native-frame handle ABI is reserved through
`E7MediaPipeDetectFullFaceFromNativeFrame`, but it currently reports
`native_frame_handle_not_connected`. A future performance pass can replace the
BGRA copy with a zero-copy native `CVPixelBuffer` or GPU texture bridge after
the first face-positive product-quality loop proves coordinate correctness.

첫 MediaPipe-first 제품 renderer는 smoothed full-face packet의 normalized
landmark를 Unity camera viewport에 투영한다. 이때 detector input frame의
`selectedOrientationDegrees`, `imageWidth`, `imageHeight`를 사용해 oriented
image size를 구하고, Unity camera viewport와 `aspect-fill` 방식으로 맞춘 뒤
lip, cheek, brow polygon을 만든다. 단순 normalized 1:1 매핑은 카메라 배경의
crop/fill과 어긋날 수 있으므로 제품 경로의 장기 기본값이 아니다.

MediaPipe packet이 짧게 stale 상태가 되면 마지막 smoothed placement를 즉시
지우지 않고 hold/fade한다. 너무 오래된 packet은 `stale_expired`로 만료하고
새 face-positive packet을 기다린다. 이 동작은 순간 frame drop 때문에 모든
makeup이 깜박이거나 사라지는 것을 막기 위한 제품 품질 계약이다.
Stale age는 MediaPipe frame timestamp와 같은 runtime clock으로 증가해야
한다. XR frame timestamp를 쓴 packet에 wall-clock timestamp를 섞으면 packet이
영구히 fresh로 보이거나 즉시 stale이 되는 문제가 생기므로, 마지막 frame
timestamp와 Unity realtime delta를 결합해 현재 runtime timestamp를 계산한다.

## Renderer Artifacts

현재 제품 route는 `MediaPipeRegionOverlayRenderer`가 lip, cheek, brow를
실제 화면에 그린다. Region ownership은 다음 파일로 분리한다.

- `MediaPipeLipRegionRenderer.cs`: lip outer contour와 inner cutout을
  MediaPipe full-face packet에서 계산한다.
- `MediaPipeBrowRegionRenderer.cs`: left/right brow landmark region을
  MediaPipe full-face packet에서 계산한다.
- `MediaPipeCheekRegionRenderer.cs`: left/right cheek polygon을 MediaPipe
  full-face packet에서 계산한다.
- `MediaPipeCanonicalRegionMeshBuilder.cs`: smoothed MediaPipe landmark packet과
  공식 canonical topology를 결합해 lip, cheek, brow region 안에 들어오는
  full-face triangle만 남긴다. 즉 region renderer는 독립 polygon fan을
  그리는 것이 아니라 동일한 468-vertex / 898-triangle canonical mesh를
  region mask로 cull해서 제품 makeup mesh를 만든다.
- `MediaPipeFullFaceMeshRenderer.cs`: full-face textured mesh로 이동하기
  위한 packet-to-mesh renderer다. 공식 MediaPipe
  `canonical_face_model.obj`에서 추출한 468-vertex, 898-triangle topology와
  canonical UV를 사용한다. 최종 제품 품질 판정에는 authored canonical texture
  layer를 full-face mesh material layer로 통합하는 추가 작업이 필요하다.
  평상시 status reporting은 packet count와 topology count만 읽는 lightweight
  path를 사용하고, 디버그 mesh는 명시적으로 보일 때만 실제 Mesh 데이터를 갱신한다.

이 분리는 ARKit UV renderer로 되돌아가지 않고 full-face mesh renderer로
옮겨가기 위한 중간 구조다.

## Diagnostics Contract

HUD, Unity log, `face_feature_snapshot`은 제품 좌표 ownership을 명시해야 한다.
MediaPipe-first 제품 경로에서는 다음 값이 보여야 한다.

- `productCoordinateSystem=mediapipe_canonical_face_space`
- `placementOwner=mediapipe_full_face_landmarks`
- `arkitAssistRole=arkit_session_camera_optional_depth`
- `coordinates=mediapipe assist=arkit-session,arkit-camera,optional-depth`
- `fullFaceMesh=mediapipe_canonical_face_model_v1`
- `fullFaceTriangles=898`
- `meshCullingMode=mediapipe_canonical_full_face_triangle_gate`
- `maskSoftSampleMode=mediapipe_canonical_triangle_gate`
- `mediapipePacketAgeMs`, `mediapipeInferenceLatencyMs`,
  `mediapipeDroppedPacketCount`, `mediapipeStalePacketCount`
- `mediapipeCaptureSkippedBusyCount`,
  `mediapipeCaptureSkippedThrottleCount`,
  `mediapipeCaptureFrameUnavailableCount`
- `activeRegionCount`, `averageFrameTimeMs`, `worstFrameTimeMs`

Region snapshot은 MediaPipe 제품 route와 legacy ARFace UV compatibility route를
구분한다. Lip, cheek, brow의 제품 route는 `mediapipe_region_overlay_product`
상태여야 하고, eye처럼 아직 smooth fallback인 route는 명시적으로
`legacy_arface_uv_compat`로 표시한다.

## ARKit Assist And Fallback Policy

ARKit tracking is diagnostic assist, not product placement ownership. When the
MediaPipe product renderer is active:

- If ARKit reports a face but MediaPipe has no fresh or short-stale face packet,
  lip, cheek, and brow product overlays stay hidden with
  `mediapipe_waiting_for_face` or `mediapipe_stale_expired_waiting_for_face`.
- If a short-stale MediaPipe packet is still inside the hold window, makeup may
  hold or fade from the last smoothed MediaPipe placement, never from ARKit UV.
- If ARKit session/camera data is unavailable, MediaPipe diagnostics can only
  continue when an approved on-device camera frame source is still producing
  transient in-memory frames with `rawFrameStored=false` and
  `offDeviceUpload=false`.
- If both MediaPipe packet input and ARKit/session diagnostics are unavailable,
  UI and logs should remain in `waiting for face` style states and product
  makeup must stay hidden until a MediaPipe face-positive packet returns.
- `MediaPipeRegionOverlayRenderer` rejects non-MediaPipe renderer modes so a
  product layer cannot silently mix MediaPipe landmarks with legacy ARFace UV
  masks.

## Source And License Notes

`MediaPipeCanonicalFaceMesh.cs`의 topology/UV table은 Google MediaPipe
`canonical_face_model.obj`에서 생성했다.

- Source:
  `https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model.obj`
- License: Apache License 2.0

이 데이터는 제품 renderer의 canonical mesh basis로 쓰되, 최종 배포 전에는
MediaPipe runtime/model/package license review와 third-party notice 정리를
별도로 확인해야 한다.
