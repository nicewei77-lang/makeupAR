# MediaPipe-First Real Device QA Runbook

Status: Ready for the first approved MediaPipe-first product renderer device loop
Date: 2026-06-30

## Scope

Use this runbook when validating the MediaPipe-first lip, cheek, and brow
renderer on the real iPhone. This QA loop checks product coordinate correctness,
runtime stability, and privacy diagnostics only.

Out of scope:

- Android.
- Backend upload, cloud inference, recommendation, face analysis storage, or raw
  frame persistence.
- Commercial SDK changes.
- App Store, production, privacy, or license readiness claims.

## Build Gate

Before a real-device build, stop and ask for approval. The approved path is:

1. Close Unity/Hub and stale Unity/Licensing processes.
2. Run `bash scripts/build_m3_unityframework.sh` from the repo root.
3. Build/install/run the RN iOS app with the user-approved connected iPhone and
   signing team.
4. Do not add a default UDID or `DEVELOPMENT_TEAM` to the repo.

## Current Gate

As of 2026-06-30, local static/RN/Unity compile checks pass for the
MediaPipe-first product route, including the generated MediaPipe canonical
468-vertex / 898-triangle full-face mesh topology. The remaining required
evidence is a user-approved real-device build/install/run with a face-positive
camera session. The first device loop should confirm nonzero MediaPipe full-face
landmarks, `fullFaceVertices=468`, `fullFaceTriangles=898`, and visible
lip/cheek/brow placement on the live face. Region diagnostics should also show
canonical full-face triangle gating instead of legacy ARFace UV or standalone
polygon fan rendering.

Latest local verification on 2026-06-30:

- `npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand`: 46 passed.
- `npx tsc --noEmit`: passed.
- `npm run lint -- --quiet`: passed.
- `verify_mediapipe_first_runtime_contract.py`: passed.
  This verifier now confirms the full-face product Swift section uses
  `MPImage(pixelBuffer:)` and does not decode PNG bytes, while legacy brow PNG
  detection remains explicitly diagnostic-only. It also guards Unity's reused
  pinned BGRA conversion buffer, `IntPtr` bridge path, and fixed transformation
  fallback buffers, plus the non-alloc lip/cheek/brow region solve path.
- `verify_mediapipe_canonical_assets.py`: passed.
- `verify_psd_arcore_makeup_textures.py`: passed.
- `verify_brow_landmark_privacy_contract.py`: passed.
- `verify_unityframework_build_contract.py`: passed and confirms no repo-default
  `DEVELOPMENT_TEAM`, provisioning profile, or device id is hard-coded.
- `verify_ios_local_media_capture_contract.py`: passed.
- `xcodebuild -list -project rn/MakeupARValidation/ios/MakeupARValidation.xcodeproj`:
  passed; the project exposes the `MakeupARValidation` target and scheme.
- Unity batch import/compile:
  `evidence/logs/unity_batch_compile_arkit_assist_guard_20260630.log` exited 0
  with `Tundra build success`.

## Pre-Build Checks

Run from the repo root unless a command says otherwise:

```bash
python3 scripts/e7_reference_atlas/verify_mediapipe_first_runtime_contract.py
python3 scripts/e7_reference_atlas/verify_mediapipe_canonical_assets.py
python3 scripts/e7_reference_atlas/verify_unityframework_build_contract.py
python3 scripts/e7_reference_atlas/verify_ios_local_media_capture_contract.py
```

```bash
cd rn/MakeupARValidation
npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand
npm run lint -- --quiet
npx tsc --noEmit
```

Unity import/compile check:

```bash
"/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity" \
  -batchmode \
  -quit \
  -projectPath "/Users/hi/dev/Jungle/makeupAR/unity/MakeupARUnityValidation" \
  -logFile "/Users/hi/dev/Jungle/makeupAR/evidence/logs/unity_batch_compile_mediapipe_region_overlay_20260630.log"
```

Expected:

- MediaPipe-first verifier passes.
- MediaPipe canonical asset verifier passes.
- RN tests, lint, and TypeScript pass.
- Unity exits successfully and the log has no C# compile errors.

## Face-Positive Setup

For the first coordinate-quality loop, the tester should:

- Hold the iPhone in portrait with the front camera pointed at a single face.
- Keep the full face in frame for at least 10 seconds before judging placement.
- Avoid heavy occlusion from hair, hands, glasses glare, or extreme side pose in
  the first pass.
- Use neutral expression first, then smile, open mouth, raise eyebrows, and make
  small head turns.

The first evidence we need is a face-positive run where MediaPipe reports a
stable packet. A no-face log is useful for diagnostics, but it cannot prove
makeup placement quality.

## Acceptance Checks

- HUD or diagnostics reports `rendererMode=mediapipe-region-overlay` for lip,
  cheek, and brow product layers.
- Compact HUD reports product ownership as `Renderer MediaPipe` instead of raw
  renderer ids such as `lip-mediapipe-region-overlay-renderer`.
- Product lip source labels are `MediaPipe lip` and `MediaPipe flat`; alternate
  sources are explicitly labeled as `Vision diagnostic`, `Legacy atlas
  diagnostic`, or `Legacy mask`.
- Product UI does not present `ATLAS`, `PSD ARCORE`, `VISION`, `FLAT`, or
  `PSD FLAT` as equal unexplained product choices.
- HUD reports `mediapipe=full-face`, `stable=true`, nonzero landmark count, and
  `rawFrameStored=false offDeviceUpload=false`.
- HUD or heartbeat reports `inputFormat=bgra-cvpixelbuffer`,
  `mediapipeSource=direct-frame`, and MediaPipe capture counters. The first
  product pass is expected to use throttled ARCameraManager CPU-image BGRA
  input through the reused pinned buffer, not `ReadPixels` or PNG detector input.
- HUD or `face_feature_snapshot` reports
  `productCoordinateSystem=mediapipe_canonical_face_space`,
  `placementOwner=mediapipe_full_face_landmarks`, and
  `arkitAssistRole=arkit_session_camera_optional_depth`.
- Diagnostics reports
  `coordinates=mediapipe assist=arkit-session,arkit-camera,optional-depth`,
  `fullFaceMesh=mediapipe_canonical_face_model_v1`, `fullFaceVertices=468`,
  and `fullFaceTriangles=898` once a face-positive MediaPipe packet is
  available.
- Lip, cheek, and brow region diagnostics report
  `meshCullingMode=mediapipe_canonical_full_face_triangle_gate`,
  `maskSoftSampleMode=mediapipe_canonical_triangle_gate`, and
  `topologyAuditStatus=mediapipe_canonical_face_model_v1` after makeup is
  applied.
- Performance diagnostics report `activeRegionCount`,
  `averageFrameTimeMs`, `worstFrameTimeMs`, `mediapipePacketAgeMs`,
  `mediapipeInferenceLatencyMs`, `mediapipeDroppedPacketCount`,
  `mediapipeStalePacketCount`, and MediaPipe capture skip counters. Use these
  together to separate slow inference, Unity render slowness, stale packets, and
  camera-frame cadence issues.
- Lip stays on the lips in neutral, smile, and open-mouth states.
- Brow follows eyebrow area and does not hide lip or cheek.
- Cheek remains visible when lip and brow are also active.
- Fast but normal small head motion does not create severe jitter.
- Temporary packet stale/drop state fades or holds briefly instead of clearing
  all makeup instantly.
- During temporary frame loss, `mediapipePacketAgeMs` should continue increasing
  from the last accepted MediaPipe frame, then the region state should move from
  `mediapipe_region_stale_hold` to
  `mediapipe_stale_expired_waiting_for_face` if the loss continues.
- Long face loss eventually hides product makeup and recovers when the face
  returns.

## Failure Signs To Record

- Lip is vertically attached to the nose, chin, or teeth instead of the lip
  boundary.
- Cheek disappears when brow is enabled.
- Brow activation hides lip or cheek.
- Makeup appears screen-locked instead of face-locked.
- Makeup is mirrored left/right in a way that breaks asymmetric assets.
- Overlay shakes faster than the underlying face under normal head motion.
- Diagnostics show `stale_expired` continuously while the face is in frame.
- Diagnostics show lip, cheek, or brow as `legacy_arface_uv_compat` during a
  MediaPipe product route test.
- Privacy flags are missing or not `false`.

## Evidence Policy

Do not save raw camera frames by default. Store summary logs under
`evidence/logs/` when they are decision evidence. Save screenshots or recordings
only when visual alignment, motion, or jitter must be reviewed; keep them
minimal and do not treat them as raw-frame storage pipelines.
