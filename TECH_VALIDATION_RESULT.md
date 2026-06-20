# Tech Validation Result

Date: 2026-06-20

Latest re-check: 2026-06-20 18:29:59 KST

## Scope

Session 2 / M1 only: Unity standalone AR Foundation iOS validation.

React Native project creation, UnityFramework embedding, RN-Unity messaging, real makeup rendering quality, backend/API, AI, admin, community, payment, and Android work were not attempted.

Authoritative inputs:

- `TECH_VALIDATION_TEST_PLAN.md` section 8, M1 Unity standalone AR validation
- `docs/runbooks/M1_STANDALONE_AR_RUNBOOK.md`

## Workspace Document State

Active root documents:

- `TECH_VALIDATION_TEST_PLAN.md`: stable validation contract, milestone order, and document policy.
- `TECH_VALIDATION_RESULT.md`: latest milestone decisions, current status, evidence, and next boundary.

Completed session-specific plan/status documents have been absorbed into this result document and removed from the active root. New `M*_..._PLAN.md` files should be temporary: create them only when a session needs one, then absorb the outcome here and delete the plan after completion.

## Final Decision

Status: Green

M1 is Green because the Unity standalone iOS app now proves the required technical chain on a real iPhone:

- Front/user-facing camera is confirmed.
- ARKit face tracking runs with `XRFaceSubsystem loaded`.
- Runtime log reports `Camera requested/current: User/User`.
- Runtime log reports `Current tracked face count: 1` and `Face detected: true`.
- A visible magenta/cyan diagnostic mask/marker appears on a detected face.
- The mask follows head movement.
- The mask disappears when the face leaves the camera view.

Known limitations:

- The diagnostic mask is visibly offset from the real face and does not fit the face precisely.
- User observed that the app appears to recognize only the first face seen after launch. When a different person's face is shown later, the mask does not newly track that second face.

These do not block M1 because M1 only validates that Unity + AR Foundation + ARKit face tracking can run on iPhone with a visible face-following overlay for a detected face. Precise face fitting, makeup quality, segmentation, product-like rendering, robust face switching, and track reacquisition behavior remain out of M1 scope.

## Milestone History

| Milestone | Decision | Notes |
| --- | --- | --- |
| M0. Environment gate | Green as of 2026-06-20 | macOS 26.5.1, full Xcode 26.5, Node 22.23.0, npm 10.9.8, Watchman 2026.06.15.00, CocoaPods 1.16.2, Unity 6000.3.18f1, and iOS Build Support are available. |
| M1. Unity standalone AR validation | Green | Real iPhone runtime confirmed front camera, ARKit face tracking, visible diagnostic marker/mask, and face-following behavior. |
| M2. React Native standalone iOS validation | Next | Do this before UnityFramework export/embed or RN-Unity messaging work. |

## Requirement Matrix

| M1 requirement | Current evidence | Status |
| --- | --- | --- |
| Unity standalone iOS app runs on real iPhone | User confirmed the app is installed/running on the iPhone and provided live screenshots | Green |
| Front/user-facing camera works | User confirmed front camera; screenshots show front-camera feed and debug panel `Camera requested/current: User/User` | Green |
| Camera direction appears in debug/logs | User-provided Xcode logs include `Camera requested/current: User/User`; screenshots show the same in the debug panel | Green |
| Face tracking support works | User-provided Xcode logs show `SessionTracking`, `XRFaceSubsystem loaded`, `running=True`, `Current tracked face count: 1`, `Face detected: true` | Green |
| Visible face-following overlay exists | Screenshots show a bright magenta diagnostic mask/marker over the camera feed | Green |
| Overlay follows the face | User confirmed the cross/marker is visible, the mask follows head movement, and disappears when the face leaves the view | Green |
| Unity iOS export succeeds | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m1-front-camera-overlay-export-2026-06-20.log` contains `[M1] Unity iOS export result: Succeeded at /Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export` | Green |

## Environment / Device Snapshot

| Item | Result | Status |
| --- | --- | --- |
| macOS | 26.5.1, build 25F80 | Checked |
| Xcode | Xcode 26.5, build 17F42 | Checked |
| Unity | 6000.3.18f1 | Checked |
| Unity iOS Build Support | `/Applications/Unity/Hub/Editor/6000.3.18f1/PlaybackEngines/iOSSupport` exists | Checked |
| Node | `v22.23.0` | Checked |
| npm | `10.9.8` | Checked |
| Watchman | `2026.06.15.00` | Checked |
| CocoaPods | `1.16.2` | Checked |
| iPhone via `devicectl` | `위승철의 iPhone`, identifier `6F504EE9-BABC-5F6F-A186-C734E04CA625`, state `connected`, model `iPhone 16 (iPhone17,3)` | Checked |
| Exported Xcode project | Generated during M1 under ignored `unity-builds/ios-export/`; generated artifact is not retained in the cleaned repo | Reproducible |
| Real-device runtime | User confirmed the regenerated app runs and produced screenshots/logs | Checked |

## Current Unity Project State

| Item | Result |
| --- | --- |
| Unity project path | `/Users/wiseungcheol/Desktop/makeupAR/unity/MakeupARUnityValidation` |
| AR Foundation version | `com.unity.xr.arfoundation` 6.3.5 |
| Apple ARKit XR Plug-in version | `com.unity.xr.arkit` 6.3.5 |
| XR Plug-in Management version | `com.unity.xr.management` 4.5.4 |
| ARKit face tracking | `Assets/XR/Settings/ARKitSettings.asset` has face tracking enabled |
| AR scene | `Assets/Scenes/MakeupARFaceValidation.unity` |
| Required scene objects | `AR Session`, `XR Origin`, `AR Camera`, `AR Camera Manager`, `AR Face Manager`, and `Face Tracking Status Reporter` are present |
| Face prefab | `Assets/Prefabs/ValidationFaceOverlay.prefab` contains `ARFace`, `MeshFilter`, `MeshRenderer`, `ARFaceMeshVisualizer`, and `FaceTrackingMarker` |
| Face mesh material | `Assets/Materials/ValidationFaceOverlay.mat` uses bright magenta with alpha `0.65` |
| Runtime debug script | `Assets/Scripts/FaceTrackingStatusReporter.cs` logs AR state, camera requested/current direction, face subsystem support, face count, and `Face detected: true/false` |
| Diagnostic marker script | `Assets/Scripts/FaceTrackingMarker.cs` creates a magenta face-center sphere and cyan crosshair bars under the tracked face prefab |

## Evidence

| Evidence | Path / content |
| --- | --- |
| M1 front-camera/marker export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m1-front-camera-overlay-export-2026-06-20.log` |
| Export success line | `[M1] Unity iOS export result: Succeeded at /Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export` |
| Regenerated Xcode project | Generated during M1; recreate with `docs/runbooks/M1_STANDALONE_AR_RUNBOOK.md` when needed |
| Front camera serialization | `Assets/Scenes/MakeupARFaceValidation.unity` has `ARCameraManager` `m_FacingDirection: 2` |
| Marker prefab inclusion | `Assets/Prefabs/ValidationFaceOverlay.prefab` includes `Assembly-CSharp::FaceTrackingMarker` |
| Screenshot evidence | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m1-front-camera-overlay-2026-06-20-1.png`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m1-front-camera-overlay-2026-06-20-2.png` |
| Runtime log evidence | User-provided Xcode log includes `SessionTracking`, `Camera requested/current: User/User`, `XRFaceSubsystem loaded`, `running=True`, `Current tracked face count: 1`, `Face detected: true` |
| User visual confirmation | Front camera confirmed; cross visible; mask follows head movement; marker disappears when face leaves the view |
| Face switching observation | User observed that after the first detected face, showing another person's face does not create a newly tracked mask |

## Special Observations

- First-face-only behavior: after launch, the app appears to keep tracking only the first recognized face and does not reliably reacquire a different person's face later.
- This should be treated as a follow-up validation risk before product AR UX work.
- Candidate follow-up checks: confirm whether the original `ARFace` trackable is actually removed when the first face leaves; log `trackablesChanged` added/updated/removed events; test `ARSession.Reset()` or disable/enable `ARFaceManager` between users; confirm whether `requestedMaximumFaceCount = 1` and ARKit provider behavior are acceptable for the target UX.

## Next Milestone Boundary

M1 is complete. Do not treat the mask offset or first-face-only behavior as part of M1.

Recommended next validation step is M2, React Native standalone iOS validation, before any RN-Unity embedding work.

Do not start UnityFramework export/embed, RN-Unity messaging, or makeup-quality work until the plan reaches those milestones.
