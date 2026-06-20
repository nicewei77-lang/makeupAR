# M1 Front Camera Overlay Implementation Plan

Date: 2026-06-20

## Purpose

Finish Session 2 / M1 Unity Standalone AR Validation for `/Users/wiseungcheol/Desktop/makeupAR`.

This is still a technical validation milestone, not product implementation. The only goal is to prove that Unity + AR Foundation + ARKit face tracking can run on a real iPhone with a visible face-following overlay.

## Current State

Authoritative plan:

- `TECH_VALIDATION_TEST_PLAN.md` section 8 defines M1.
- M1 completion requires:
  - Unity standalone iOS app runs on a real iPhone.
  - Front camera permission/camera feed works.
  - Face mesh or overlay appears when a face is visible.
  - Overlay follows the face as the face moves.
  - Unity/Xcode log confirms face tracking support and detected state.

Current implementation:

- Unity project: `unity/MakeupARUnityValidation`
- Generated scene: `Assets/Scenes/MakeupARFaceValidation.unity`
- Face prefab: `Assets/Prefabs/ValidationFaceOverlay.prefab`
- Setup script: `Assets/Editor/MakeupARValidationSetup.cs`
- Runtime reporter: `Assets/Scripts/FaceTrackingStatusReporter.cs`

Latest user-reported runtime evidence:

- Unity standalone iOS app has built and launched on the iPhone.
- Camera feed appears.
- User reports no visible face change/overlay.
- Xcode logs repeatedly show:

```txt
[M1] AR support state: SessionTracking; Face tracking support state: XRFaceSubsystem loaded; running=True; supportsFacePose=true; supportsFaceMeshVerticesAndIndices=true; supportsFaceMeshUVs=true; supportsEyeTracking=true; Current tracked face count: 1; Face detected: true
```

Current interpretation:

- ARKit face tracking is working.
- The remaining M1 gap is visible validation: camera direction is not explicit enough, and the current overlay is too weak or not visibly rendered.
- `TECH_VALIDATION_RESULT.md` is stale and still records an earlier signing blocker. Update it after the next run with current runtime evidence.

## Scope Rules

Do:

- Stay inside M1 Unity standalone AR validation.
- Make the camera direction explicit.
- Make face-following visual evidence obvious.
- Preserve the existing minimal validation app shape.
- Update evidence/result docs after real-device verification.

Do not:

- Start React Native app creation.
- Start UnityFramework export/embed into React Native.
- Implement real makeup quality.
- Add AI/backend/admin/community/payment work.
- Hardcode a personal Apple Development Team ID into Unity or Xcode project files.

## Milestones

### M1.1 Inspect Current Unity State

Confirm before editing:

- `ARCameraManager` exists on `AR Camera`.
- `ARFaceManager` exists on `XR Origin`.
- `ARFaceManager.facePrefab` points to `ValidationFaceOverlay.prefab`.
- `ValidationFaceOverlay.prefab` contains `ARFace`, `MeshFilter`, `MeshRenderer`, and `ARFaceMeshVisualizer`.
- `FaceTrackingStatusReporter` is present in the scene and receives `ARSession` and `ARFaceManager`.

Expected known issue:

- `MakeupARValidationSetup.cs` currently creates `ARCameraManager` without explicitly setting `requestedFacingDirection`.
- Scene YAML may contain a serialized facing direction value, but the generator should be explicit so future exports are deterministic.

### M1.2 Force Front Camera

In `MakeupARValidationSetup.cs`:

- Store the created `ARCameraManager` in a variable.
- Set:

```csharp
cameraManager.requestedFacingDirection = CameraFacingDirection.User;
```

Import requirement:

- `CameraFacingDirection` is in `UnityEngine.XR.ARFoundation`, already imported by the setup script.

Acceptance:

- Regenerated scene serializes the AR camera facing direction as user-facing.
- Runtime logs/debug overlay can prove requested/current direction.

### M1.3 Add Camera Direction Runtime Reporting

In `FaceTrackingStatusReporter.cs`:

- Add serialized field:

```csharp
[SerializeField] private ARCameraManager cameraManager;
```

- Resolve it in `Awake()` with `FindFirstObjectByType<ARCameraManager>()` if missing.
- Include camera direction in both `OnGUI()` and `[M1]` logs:

```txt
Camera requested/current: User/User
```

Use exact AR Foundation properties:

- `cameraManager.requestedFacingDirection`
- `cameraManager.currentFacingDirection`

Null fallback:

- If no camera manager exists, display/log `Camera direction: ARCameraManager not found`.

Acceptance:

- Xcode console includes camera direction in every periodic `[M1]` status log.
- On-screen debug panel includes camera direction.

### M1.4 Add Strong Diagnostic Face-Following Marker

Use diagnostic overlay, not natural makeup.

Implementation target:

- Create a new runtime script, for example:

```txt
Assets/Scripts/FaceTrackingMarker.cs
```

Behavior:

- Attach this script to the face prefab root or to a child under the face prefab.
- The marker must be a child of the tracked `ARFace` prefab, so it follows the tracked face transform automatically.
- Create obvious visual primitives at runtime if serialized child objects are absent:
  - A bright magenta/cyan sphere or cube near the nose/face center.
  - A short crosshair made from small colored bars.
- Keep the marker small enough not to hide the whole face but obvious enough for screenshot proof.

Recommended marker:

- One magenta sphere at local position `(0, 0, 0.08)`, scale around `0.04`.
- Two cyan bars crossing near the face center, scale around `0.12 x 0.01 x 0.01`.
- Use `Unlit/Color` or fallback material.
- Disable shadows and keep render queue high enough to be visible.

In `MakeupARValidationSetup.cs`:

- When creating or updating `ValidationFaceOverlay.prefab`, ensure the prefab includes the marker script.
- If the prefab already exists, update it rather than returning early without adding the marker.
- Make the face mesh material stronger:
  - Increase alpha from the current weak value to roughly `0.65`.
  - Use bright magenta or cyan.
  - Disable shadows for validation renderers.

Acceptance:

- When a face is detected, at least one bright marker clearly moves with the face.
- If the face leaves the camera, marker disappears with the ARFace trackable.

### M1.5 Regenerate Unity Scene And Export iOS Project

Run Unity setup/export after code changes.

Preferred command shape:

```sh
"/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity" \
  -batchmode \
  -quit \
  -projectPath /Users/wiseungcheol/Desktop/makeupAR/unity/MakeupARUnityValidation \
  -executeMethod MakeupARValidationSetup.ExportIosProject \
  -logFile /Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m1-front-camera-overlay-export-2026-06-20.log
```

Notes:

- Unity export can overwrite the Xcode project. If Xcode signing disappears after export, reselect the Personal Team in Xcode UI.
- Do not hardcode `DEVELOPMENT_TEAM` into source-controlled project generation unless the user explicitly asks.

Acceptance:

- Export succeeds.
- Export path remains:

```txt
/Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export
```

### M1.6 Rebuild And Run On iPhone

In Xcode:

- Open `unity-builds/ios-export/Unity-iPhone.xcodeproj`.
- Select target `Unity-iPhone`.
- Ensure `Signing & Capabilities` has the user's Personal Team selected.
- Select the real iPhone as the run destination.
- Press `Cmd + R`.

Runtime checks:

- App launches.
- Camera feed appears.
- Debug panel shows `Face detected: true`.
- Debug panel or logs show camera direction as `User`.
- Bright marker/overlay visibly follows the face.

Evidence to collect:

- Xcode `[M1]` logs showing:
  - `SessionTracking`
  - `XRFaceSubsystem loaded`
  - `running=True`
  - `Current tracked face count: 1`
  - `Face detected: true`
  - camera requested/current direction
- Screenshot or screen recording showing marker/overlay on the face.

### M1.7 Update Result And Decide Status

Update `TECH_VALIDATION_RESULT.md`.

Replace stale entries that say build/run was not tested or blocked by signing if the new evidence proves otherwise.

Record:

- App build/run status.
- Camera permission/feed status.
- Camera direction status.
- Face tracking log status.
- Overlay/marker follow status.
- Evidence file paths.
- Final M1 readiness: Green, Yellow, or Red.

Decision rules:

- Green:
  - Real iPhone app runs.
  - Front/user-facing camera is confirmed.
  - `Face detected: true` log is present.
  - Visible marker/overlay follows the face.
- Yellow:
  - App and face tracking work, but front camera or visible overlay follow remains unverified.
- Red:
  - Front camera change breaks AR session, face tracking repeatedly fails, or app crashes/black-screens.

## Suggested Next Session Goal Prompt

Use this short prompt in a new Codex session:

```md
/goal /Users/wiseungcheol/Desktop/makeupAR 에서 M1_FRONT_CAMERA_OVERLAY_IMPLEMENTATION_PLAN.md를 먼저 읽고, 그 계획대로 Session 2 / M1 Unity Standalone AR Validation을 마무리해줘. M1 범위 밖 작업은 하지 말고, 완료 후 TECH_VALIDATION_RESULT.md에 Green/Yellow/Red 판정을 기록해줘.
```

## Final Notes

- The current tracking logs are already strong evidence that ARKit face tracking works.
- The next implementation should optimize for unmistakable validation evidence, not visual polish.
- Keep the diagnostic marker obvious even if it looks ugly. That is intentional for M1.
