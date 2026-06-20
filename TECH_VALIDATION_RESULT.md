# Tech Validation Result

Date: 2026-06-20

Latest re-check: 2026-06-20 22:08 KST

## Scope

Session 6 / M5 only: React Native controls send recipe-like JSON to Unity and Unity applies the received color/opacity to the diagnostic AR face overlay.

Unity-to-RN messaging, re-entry stability stress testing, makeup quality, AI/backend/admin/payment/community, and Android work were not attempted.

Authoritative inputs:

- `AGENTS.md`
- `TECH_VALIDATION_TEST_PLAN.md` section 12, M5 RN -> Unity communication
- `TECH_VALIDATION_RESULT.md` previous `Next Milestone Boundary`

## Workspace Document State

Active root documents:

- `AGENTS.md`: repository working rules, milestone scope boundaries, document policy, and evidence/cleanup requirements.
- `TECH_VALIDATION_TEST_PLAN.md`: stable validation contract, milestone order, and document policy.
- `TECH_VALIDATION_RESULT.md`: latest milestone decisions, current status, evidence, and next boundary.

Completed session-specific plan/status documents have been absorbed into this result document and removed from the active root. New `M*_..._PLAN.md` files should be temporary: create them only when a session needs one, then absorb the outcome here and delete the plan after completion.

## Final Decision

Status: Green

M5 is Green because the React Native app now sends recipe-like JSON values into the RN-hosted Unity scene on the real iPhone, and Unity applies those values through the `RNBridge.ApplyRecipeJson(string)` receiver:

- RN Unity screen includes three color controls: `rose #D94B74`, `coral #E67B5F`, and `nude #B9826B`.
- RN Unity screen includes an opacity slider with `0` to `1` range and `0.05` step display/rounding.
- Value changes call `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)`.
- Unity scene contains an active `RNBridge` GameObject with `RNBridge` and `FaceTrackingStatusReporter` components.
- Unity `RNBridge.ApplyRecipeJson(string)` parses `layer`, `color`, and `opacity`, clamps opacity, and applies the resulting color to the overlay material and current face trackables.
- The regenerated UnityFramework contains `RNBridge` in `Data/level0`.
- The installed iPhone app bundle also contains `RNBridge` in `Frameworks/UnityFramework.framework/Data/level0`.
- Real-device runtime logs show ARKit reaching `SessionTracking`, `Current tracked face count: 1`, and `Face detected: true`.
- Real-device runtime logs show repeated `[M5] recipe_applied` entries for initial values, opacity changes, and color changes, including `#D94B74`, `#B9826B`, and `#E67B5F`.

Known limitations:

- Initial M5 attempts showed the exact user symptom: the AR screen and RN controls were visible, but button/slider changes had no effect. The runtime logs showed `SendMessage: object RNBridge not found!`.
- Root cause: the reproducible UnityFramework script updated `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework`, but the iOS app embedded the framework from `rn/MakeupARValidation/node_modules/@azesmway/react-native-unity/ios/UnityFramework.framework`. That package framework was stale and did not contain the M5 scene object.
- `scripts/build_m3_unityframework.sh` now also copies the generated framework to the `react-native-unity` package framework path when `node_modules` is present. This package copy is generated/local state and should not be source-controlled.
- The M4 local `RNUnityView.mm` timing patch under `node_modules` is still required for this local run so Unity initializes from `didMoveToWindow` after the RN view has a real window/bounds. Make this durable before clean reinstall/reclone workflows.
- Unity logs still include `Failed to initialize subsystem ARKit-Meshing [error: 1]` and `Can't add component because class 'SphereCollider' doesn't exist!` from earlier diagnostic paths. ARKit face tracking, overlay display, and M5 recipe application still work; these are outside M5.
- The existing M1 observation about first-face-only behavior remains a follow-up risk and is not part of M5.

These do not block M5 because M5 validates one-way RN -> Unity value transfer and Unity-side application/logging only. Unity -> RN messaging and re-entry stability remain M6+ scope.

## Current Screen State Review

Review time: 2026-06-20 22:08 KST

Scope: user-provided M5 app execution recording only. No code changes were made during this review. This section records the current visible app state after M5, and separates the M5 communication result from the visual AR makeup readiness result.

Source recording:

- Original user attachment: `/Users/wiseungcheol/Downloads/ScreenRecording_06-20-2026 21-48-38_1.MP4`
- Workspace copy: `/Users/wiseungcheol/Desktop/makeupAR/evidence/screen-recordings/m5-current-screen-state-2026-06-20-214838.mp4`
- Metadata log: `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-current-screen-recording-ffprobe-2026-06-20-214838.log`
- Metadata summary: 44.35 seconds, 1180x2556 portrait video, HEVC, about 59.75 fps, creation time `2026-06-20T12:48:38Z` / `2026-06-20 21:48:38 KST`.

Representative frame evidence:

| Artifact | Path | Observation purpose |
| --- | --- | --- |
| Contact sheet | `evidence/screenshots/m5-current-screen-state-contact-sheet-2026-06-20-214838.jpg` | Full 44.35 second flow at about 2 second intervals |
| 12s frame | `evidence/screenshots/m5-current-screen-state-12s-face-tracking-offset-2026-06-20.jpg` | AR tracking debug panel is true, but mask is visibly offset from the face |
| 20s frame | `evidence/screenshots/m5-current-screen-state-20s-opacity-offset-2026-06-20.jpg` | Opacity value is high and overlay is visible, but still not face-aligned |
| 28s frame | `evidence/screenshots/m5-current-screen-state-28s-color-offset-2026-06-20.jpg` | Coral color selection is reflected in the overlay, but overlay remains offset |
| 36s frame | `evidence/screenshots/m5-current-screen-state-36s-second-face-no-overlay-2026-06-20.jpg` | Another person's face is visible, but no new mask is attached to that visible face |
| 40s frame | `evidence/screenshots/m5-current-screen-state-40s-return-offset-2026-06-20.jpg` | Returning to the first face still shows the overlay displaced to the upper-left |

Screen observations:

| Area | Current visible state | Interpretation |
| --- | --- | --- |
| RN launch/home | The recording starts from the iPhone Home screen, opens the RN validation app, and shows `RN to Unity Recipe Validation` with `Start AR`. | M2/M4 host app launch and navigation entry remain usable. |
| Unity startup | After `Start AR`, the Unity splash appears and then the front-camera AR feed appears inside the RN-hosted Unity screen. | M4 Unity embed remains functional in the installed app. |
| RN overlay controls | The Unity screen shows `Close`, a debug text panel, `rose`, `coral`, `nude` controls, an opacity slider, and the RN warning banner `Open debugger to view warnings.` | The M5 test UI is visible. The warning banner is not an AR failure by itself, but it obscures part of the bottom UI and should be cleared or investigated before polished UX testing. |
| AR tracking status | The Unity debug panel shows `AR support state: SessionTracking`, `Camera requested/current: User/User`, `Tracked face count: 1`, and `Face detected: true` in the captured frames. | ARKit face tracking is active according to runtime debug state. This does not prove visual alignment. |
| Color changes | The overlay changes color when color controls are used, including rose/coral-like visible states. Runtime logs also record `recipe_applied` for `#D94B74`, `#B9826B`, and `#E67B5F`. | RN -> Unity message delivery and Unity-side material color application are working for the M5 contract. |
| Opacity changes | The opacity label and slider change, and the overlay visibly changes opacity in some parts of the recording. Runtime logs record opacity values across the expected range. | RN -> Unity opacity delivery is working, but small step changes can be hard to perceive visually, especially when the overlay is off-face or partly off-screen. |
| Face overlay alignment | The large colored mask is consistently displaced from the visible face, usually above and/or to the upper-left. At 12s the mouth cutout appears over the forehead/hair region rather than the mouth. At 20s and 28s the overlay is still not fitted to the eyes, mouth, jaw, or face contour. | Current visual state is not face-fitted makeup. It is diagnostic overlay rendering with a serious alignment problem. |
| Head/face movement response | The overlay appears to move or deform with tracked face changes, and the user-observed eye/mouth openings can change the mask shape. | The app is receiving AR face pose/mesh-related updates, but the rendered camera/face coordinate alignment is wrong. |
| Second face / face switching | Around the second-person segment, the debug overlay still reports one tracked face, but the visible second face does not receive a new aligned mask. | The earlier first-face-only / reacquisition risk remains real. Current logs count trackables but do not identify added/updated/removed trackable IDs, so the exact failure mode is not yet isolated. |
| Controls with no visible effect | Some control movements can appear to do nothing. In current source, Unity only receives `layer`, `color`, and `opacity`, and only color/opacity are applied to the whole diagnostic face overlay material. | Any UI state that is not represented in the recipe JSON, or any change that targets a visual object outside the overlay material, will not produce a visible Unity change. This is a current implementation limitation, not user error. |

Source and log cross-check:

- AR Foundation and ARKit are present through `com.unity.xr.arfoundation` 6.3.5 and `com.unity.xr.arkit` 6.3.5 in `unity/MakeupARUnityValidation/Packages/manifest.json`.
- ARKit face tracking is enabled in `unity/MakeupARUnityValidation/Assets/XR/Settings/ARKitSettings.asset` with `m_FaceTracking: 1`.
- The Unity scene contains `ARFaceManager`, a face prefab, `RNBridge`, and `AR Camera Manager` in `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity`.
- The scene has `m_MaximumFaceCount: 1`, so multi-face behavior or reliable switching between people is not currently proven.
- The scene's `AR Camera` lists `Camera`, `AudioListener`, `ARCameraManager`, and `ARCameraBackground`, but no Tracked Pose Driver component is serialized in the inspected scene section.
- The final real-device log contains this warning: `Camera "AR Camera" does not use a Tracked Pose Driver (Input System), so its transform will not be updated by an XR device.` This is the strongest current clue for why ARKit tracking can be true while the rendered overlay is offset from the camera feed.
- The final real-device log also contains `UnityARKit: Updating ARSession configuration with <ARFaceTrackingConfiguration ... captureDeviceType=AVCaptureDeviceTypeBuiltInTrueDepthCamera ... framesPerSecond=(60)>`, followed by `SessionTracking`, `Current tracked face count: 1`, and `Face detected: true`.
- The face prefab contains `ARFace`, `MeshFilter`, `MeshRenderer`, `ARFaceMeshVisualizer`, and `FaceTrackingMarker`. This is an ARKit/AR Foundation face mesh diagnostic setup, not a custom per-landmark makeup renderer.
- `RNBridge.ApplyRecipeJson(string)` parses `layer`, `color`, and `opacity`; clamps opacity; and applies the resulting color to the shared overlay material and current `ARFace` trackable renderers.
- Although the RN payload sends `layer: "lip"`, the current Unity implementation does not use that layer to isolate lips. It applies color/opacity to the diagnostic face overlay as a whole.
- `FaceTrackingMarker` creates separate magenta/cyan diagnostic marker materials at runtime. Those marker materials are not driven by the RN recipe color/opacity application path.
- The native bridge has a `sendMessageToMobileApp` path, but the current M5 app does not yet implement Unity -> RN status event handling on the RN screen. M6 remains necessary for UI-visible confirmation of `unity_initialized`, `face_detected`, and `recipe_applied`.

Current screen-state decision:

- M5 communication status remains Green: RN sends recipe-like JSON, Unity receives it, and Unity logs/applies color and opacity.
- Current visual AR makeup readiness is Yellow/Fail: the displayed overlay is not aligned to the face and must not be treated as a successful face-fitted makeup implementation.
- Current tracking interpretation: ARKit/AR Foundation face tracking is active, but the current render path is a diagnostic face mesh/marker setup with a camera/pose alignment issue and no per-region makeup segmentation.
- Highest-priority follow-up before product makeup rendering: fix AR camera pose alignment, likely by adding the required Tracked Pose Driver / equivalent AR camera pose setup for the current AR Foundation + Input System stack, then re-test the same recording scenarios.
- Next diagnostic follow-up: log `ARFaceManager.trackablesChanged` added/updated/removed events with trackable IDs, current face transform, and face mesh vertex count so first-face-only and second-face reacquisition behavior can be separated from visual alignment.
- Product makeup work should not start from the current screen state. First prove a correctly aligned face mesh/landmark basis, then add region-specific rendering for lips, eyes, cheeks, brows, jaw/chin, and nose.

## Milestone History

| Milestone | Decision | Notes |
| --- | --- | --- |
| M0. Environment gate | Green as of 2026-06-20 | macOS 26.5.1, full Xcode 26.5, Node 22.23.0, npm 10.9.8, Watchman 2026.06.15.00, CocoaPods 1.16.2, Unity 6000.3.18f1, and iOS Build Support are available. |
| M1. Unity standalone AR validation | Green | Real iPhone runtime confirmed front camera, ARKit face tracking, visible diagnostic marker/mask, and face-following behavior. |
| M2. React Native standalone iOS validation | Green | RN 0.86.0 standalone iOS app builds, installs, launches, displays on the real iPhone, and relaunches once without crash. |
| M3. UnityFramework generation | Green | Unity iOS export and `UnityFramework.framework` arm64 build succeeded; framework with `Data` is available under the RN project for M4 reference. |
| M4. RN-Unity embed | Green | RN Home opens a full-screen Unity view on the real iPhone; AR camera feed, diagnostic face overlay, and face-detected logs are confirmed. |
| M5. RN -> Unity communication | Green | RN color buttons and opacity slider send JSON to Unity `RNBridge`; real-device logs show repeated `recipe_applied` for color and opacity changes. |
| M6. Unity -> RN communication | Next | Do this before re-entry stability work. |

## M5 Requirement Matrix

| M5 requirement | Current evidence | Status |
| --- | --- | --- |
| RN has three color controls | `rn/MakeupARValidation/App.tsx` defines `rose #D94B74`, `coral #E67B5F`, and `nude #B9826B` controls on the Unity screen | Green |
| RN has opacity slider | `rn/MakeupARValidation/App.tsx` implements an opacity slider with `0` to `1` values rounded to `0.05` steps | Green |
| RN calls Unity postMessage contract | `rn/MakeupARValidation/App.tsx` calls `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)` on initial mount and value changes | Green |
| Unity scene has `RNBridge` receiver | `unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity` contains an active `RNBridge` GameObject; `RNBridge.cs` exposes public `ApplyRecipeJson(string json)` | Green |
| Unity parses recipe JSON | `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs` parses `layer`, `color`, and `opacity`, validates HTML colors, clamps opacity, and logs parse failures with the raw string | Green |
| Unity applies color/opacity to overlay | `RNBridge.cs` applies the resulting color to the overlay material and current AR face trackable renderers, including transparent material settings | Green |
| Generated UnityFramework contains M5 scene object | `evidence/logs/m3-repro-artifact-verification-m5-rnbridge-status-object-2026-06-20-213631.log` records a successful arm64 UnityFramework build; `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework/Data/level0` contains `RNBridge` | Green |
| Installed iPhone app embeds M5 framework | `evidence/logs/m5-installed-app-framework-verification-2026-06-20-214651.log` records the installed app's `UnityFramework.framework/Data/level0` containing `RNBridge` | Green |
| Real iPhone build/install/launch succeeds | `evidence/logs/m5-run-ios-device-rnbridge-package-sync-2026-06-20-214557.log` records successful build, install, and launch for `com.makeupar.rnvalidation` on `위승철의 iPhone` | Green |
| Runtime receives and applies recipe changes | `evidence/logs/m5-devicectl-launch-console-rnbridge-package-sync-2026-06-20-214651.log` records repeated `[M5] recipe_applied` entries for `#D94B74`, `#B9826B`, `#E67B5F`, and opacity values from `0.65` down to `0.05` while AR face tracking is active | Green |
| Earlier failure mode identified | `evidence/logs/m5-devicectl-launch-console-rnbridge-status-object-2026-06-20-214338.log` records `SendMessage: object RNBridge not found!`; the final installed-app verification shows this was caused by a stale embedded package framework | Green |

## M4 Requirement Matrix

| M4 requirement | Current evidence | Status |
| --- | --- | --- |
| M3 artifact exists for RN | `evidence/logs/m3-repro-artifact-verification-2026-06-20-203023.log` records arm64 `UnityFramework.framework`, `Data`, `UnitySubsystems/UnityARKit`, and `Headers/NativeCallProxy.h` under the RN project | Green |
| Unity bridge package installed | `rn/MakeupARValidation/package.json` uses `@azesmway/react-native-unity` `^1.0.11`; `evidence/logs/m4-npm-install-react-native-unity-2026-06-20-202741.log` records successful npm install | Green |
| iOS pods reinstalled | `evidence/logs/m4-pod-install-2026-06-20-203559.log` records autolinking `react-native-unity`, generated codegen artifacts, and `Pod installation complete! There are 78 dependencies from the Podfile and 77 total pods installed.` | Green |
| RN Home has `Start AR` and validation status text | `evidence/screenshots/m4-home-start-ar-visible-2026-06-20.jpg` shows the M4 Home screen with status copy and `Start AR` | Green |
| `Start AR` opens Unity screen | `evidence/screenshots/m4-unity-ar-camera-feed-face-detected-2026-06-20.jpg` shows the RN-hosted Unity AR view after tapping `Start AR` | Green |
| Unity screen is full-screen with `Close` and debug text | The same screenshot shows camera feed filling the screen, a `Close` control, and the Unity debug overlay | Green |
| Unity camera feed or scene is visible | The same screenshot shows the front-camera feed and bright magenta diagnostic face overlay | Green |
| Close returns to RN Home | User-provided screenshots for this validation include both the Unity screen and the RN Home screen; no crash was observed during the screen transition flow | Green |
| Real iPhone build/install/launch succeeds | `evidence/logs/m4-run-ios-device-instrumented-didmove-2026-06-20.log` records successful build, install, and launch for `com.makeupar.rnvalidation` on `위승철의 iPhone` | Green |
| RN-hosted Unity runtime reaches AR tracking | `evidence/logs/m4-devicectl-launch-console-instrumented-didmove-2026-06-20.log` records UnityFramework loading, `runEmbeddedWithArgc`, `UnityARKit: Updating ARSession configuration`, `Camera requested/current: User/User`, `SessionTracking`, `Current tracked face count: 1`, and `Face detected: true` | Green |

## M3 Requirement Matrix

| M3 requirement | Current evidence | Status |
| --- | --- | --- |
| Unity project confirmed for iOS target/export | `evidence/logs/m3-unity-export-2026-06-20.log` contains `[M1] Unity iOS export result: Succeeded at /Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export`; Unity project uses `com.unity.xr.arfoundation` 6.3.5 and `com.unity.xr.arkit` 6.3.5 | Green |
| Exported Xcode project includes UnityFramework target | `unity-builds/ios-export/Unity-iPhone.xcodeproj/project.pbxproj` contains the `UnityFramework` native target and scheme; `scripts/build_m3_unityframework.sh` verifies required ARKit entries before building | Green |
| `UnityFramework.framework` builds | `evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-20-201720.log` contains `** BUILD SUCCEEDED **` | Green |
| Framework binary is iPhone arm64 | `evidence/logs/m3-repro-artifact-verification-2026-06-20-201720.log` records `Mach-O 64-bit dynamically linked shared library arm64` for the RN copy | Green |
| Unity Data is inside framework | `evidence/logs/m3-repro-artifact-verification-2026-06-20-201720.log` records `UnityFramework.framework/Data`, size `9.2M`, including `boot.config`, `globalgamemanagers`, `level0`, and `UnitySubsystems/UnityARKit` | Green |
| RN reference path exists for M4 | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework` exists and is verified in `evidence/logs/m3-repro-artifact-verification-2026-06-20-201720.log` | Green |
| RN embed/messaging stayed out of scope | No RN screen/navigation, package install, bridge code, or messaging changes were made in M3 | Green |

## M2 Requirement Matrix

| M2 requirement | Current evidence | Status |
| --- | --- | --- |
| Bare React Native project created | `rn/MakeupARValidation/package.json` uses `react-native` `0.86.0`; init log shows `Welcome to React Native 0.86.0` | Green |
| iOS dependencies installed | `evidence/logs/m2-pod-install-retry-2026-06-20.log` contains `Pod installation complete! There are 77 dependencies from the Podfile and 76 total pods installed.` | Green |
| Xcode signing/provisioning confirmed | Xcode managed profile was created for `com.makeupar.rnvalidation`; signed build/install succeeded on the physical iPhone. Team ID is not retained in the project file. | Green |
| Real iPhone build succeeds | `evidence/logs/m2-xcodebuild-after-gui-signing-2026-06-20.log` contains `** BUILD SUCCEEDED **` | Green |
| Real iPhone install and launch succeeds | `evidence/logs/m2-run-ios-after-gui-signing-2026-06-20.log` contains `success Installed the app on the device`, `bundleID: com.makeupar.rnvalidation`, and `success Successfully launched the app` | Green |
| Metro/JS bundle loads | Physical-device build log contains Metro bundle generation and Hermes compilation; user confirmed the RN app was visible on the iPhone | Green |
| Relaunch has no crash | `evidence/logs/m2-relaunch-2026-06-20.log` contains `Launched application with com.makeupar.rnvalidation bundle identifier.` after `--terminate-existing` | Green |

## M1 Requirement Matrix

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
| React Native | `0.86.0` | Checked |
| RN app path | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation` | Checked |
| RN iOS bundle id | `com.makeupar.rnvalidation` | Checked |
| M3 UnityFramework artifact | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework` | Checked |
| M3 UnityFramework Data | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework/Data` | Checked |
| M3 reproducible build runbook | `/Users/wiseungcheol/Desktop/makeupAR/docs/runbooks/M3_UNITYFRAMEWORK_REPRO_BUILD_RUNBOOK.md` | Checked |

## Current React Native Project State

| Item | Result |
| --- | --- |
| RN project path | `/Users/wiseungcheol/Desktop/makeupAR/rn/MakeupARValidation` |
| React Native version | `0.86.0` |
| iOS workspace | `rn/MakeupARValidation/ios/MakeupARValidation.xcworkspace` |
| iOS bundle identifier | `com.makeupar.rnvalidation` |
| Signing storage policy | Apple Development Team ID is not stored in `MakeupARValidation.xcodeproj/project.pbxproj`; M5 CLI signing used temporary extra params and redacted logs |
| Unity integration | RN embeds Unity through `@azesmway/react-native-unity`; the iOS app copies the package framework under `node_modules/@azesmway/react-native-unity/ios/UnityFramework.framework` |
| RN-Unity bridge package | `@azesmway/react-native-unity` 1.0.11 installed and autolinked through CocoaPods |
| M5 screens | `App.tsx` contains the minimal Home screen and full-screen Unity screen required by sections 11-12 |
| M5 Home controls | Home shows validation status text and `Start AR` |
| M5 Unity controls | Unity screen shows full-screen `UnityView`, `Close`, debug text, rose/coral/nude color buttons, and an opacity slider |
| Camera permission | `NSCameraUsageDescription` is present in the RN iOS app Info.plist |
| M5 generated reference artifact | `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework` |
| M5 installed package artifact | `rn/MakeupARValidation/node_modules/@azesmway/react-native-unity/ios/UnityFramework.framework` is synced from the generated reference artifact for local iPhone builds |
| M4 bridge initialization caveat | The successful local run still includes a package-local `RNUnityView.mm` timing patch in `node_modules` so Unity initializes after `didMoveToWindow` with a real window/bounds |

## Current Unity Project State

| Item | Result |
| --- | --- |
| Unity project path | `/Users/wiseungcheol/Desktop/makeupAR/unity/MakeupARUnityValidation` |
| AR Foundation version | `com.unity.xr.arfoundation` 6.3.5 |
| Apple ARKit XR Plug-in version | `com.unity.xr.arkit` 6.3.5 |
| XR Plug-in Management version | `com.unity.xr.management` 4.5.4 |
| ARKit face tracking | `Assets/XR/Settings/ARKitSettings.asset` has face tracking enabled |
| AR scene | `Assets/Scenes/MakeupARFaceValidation.unity` |
| Required scene objects | `AR Session`, `XR Origin`, `AR Camera`, `AR Camera Manager`, `AR Face Manager`, and `RNBridge` are present |
| Face prefab | `Assets/Prefabs/ValidationFaceOverlay.prefab` contains `ARFace`, `MeshFilter`, `MeshRenderer`, `ARFaceMeshVisualizer`, and `FaceTrackingMarker` |
| Face mesh material | `Assets/Materials/ValidationFaceOverlay.mat` uses bright magenta with alpha `0.65` |
| Runtime debug script | `Assets/Scripts/FaceTrackingStatusReporter.cs` logs AR state, camera requested/current direction, face subsystem support, face count, and `Face detected: true/false` |
| M5 recipe receiver | `Assets/Scripts/RNBridge.cs` parses RN recipe JSON and applies color/opacity to the diagnostic face overlay material |
| Diagnostic marker script | `Assets/Scripts/FaceTrackingMarker.cs` creates a magenta face-center sphere and cyan crosshair bars under the tracked face prefab |
| iOS bridge proxy | `Assets/Plugins/iOS/NativeCallProxy.h` and `Assets/Plugins/iOS/NativeCallProxy.mm` were added so the RN Unity bridge can compile against the generated UnityFramework |
| M3 exported Xcode project | `/Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export` |
| M3 generated framework source product | `/Users/wiseungcheol/Desktop/makeupAR/evidence/derived-data/m3-unityframework-repro-2026-06-20-201720/Build/Products/Release-iphoneos/UnityFramework.framework` |

## Evidence

| Evidence | Path / content |
| --- | --- |
| M5 Unity configure log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-unity-configure-rnbridge-on-status-object-2026-06-20-213545.log` |
| M5 regenerated UnityFramework export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-m5-rnbridge-status-object-2026-06-20-213631.log` |
| M5 regenerated UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-m5-rnbridge-status-object-2026-06-20-213631.log` contains `** BUILD SUCCEEDED **` |
| M5 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-m5-rnbridge-status-object-2026-06-20-213631.log` records the RN framework path, arm64 binary, `104M` framework size, `9.2M` Data folder, and `NativeCallProxy.h` |
| M5 TypeScript check log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-typescript-check-2026-06-20-214651.log` |
| M5 diff whitespace check log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-git-diff-check-2026-06-20-214651.log` |
| M5 initial stale-framework failure log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-devicectl-launch-console-rnbridge-status-object-2026-06-20-214338.log` records `SendMessage: object RNBridge not found!` while the AR screen and RN controls were visible |
| M5 package-sync RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-run-ios-device-rnbridge-package-sync-2026-06-20-214557.log` records successful build, install, and launch on `위승철의 iPhone` |
| M5 installed app framework verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-installed-app-framework-verification-2026-06-20-214651.log` records the installed app bundle's `UnityFramework.framework/Data/level0` containing `RNBridge` |
| M5 real-device recipe application console log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-devicectl-launch-console-rnbridge-package-sync-2026-06-20-214651.log` records AR `SessionTracking`, `Face detected: true`, and repeated `[M5] recipe_applied` entries for color and opacity changes |
| M5 recipe application summary log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m5-runtime-recipe-applied-summary-2026-06-20-214651.log` |
| M4 RN Unity bridge npm install log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-npm-install-react-native-unity-2026-06-20-202741.log` |
| M4 regenerated UnityFramework log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-regenerate-unityframework-2026-06-20-203023.log` |
| M4 regenerated artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-2026-06-20-203023.log` |
| M4 pod install log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-pod-install-2026-06-20-203559.log` |
| M4 TypeScript check retry log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-typescript-check-retry-2026-06-20-203559.log` |
| M4 Jest check log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-jest-2026-06-20-203559.log`; blocked before tests because `@react-native/jest-preset` is missing from the RN template dependency tree |
| M4 successful RN build/install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-run-ios-device-instrumented-didmove-2026-06-20.log` |
| M4 RN-hosted Unity console log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m4-devicectl-launch-console-instrumented-didmove-2026-06-20.log` |
| M4 initial black-screen screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m4-unityview-black-screen-2026-06-20.jpg` |
| M4 initial missing camera-permission screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m4-ios-settings-no-camera-permission-2026-06-20.jpg` |
| M4 Home screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m4-home-start-ar-visible-2026-06-20.jpg` |
| M4 successful AR camera screenshot | `/Users/wiseungcheol/Desktop/makeupAR/evidence/screenshots/m4-unity-ar-camera-feed-face-detected-2026-06-20.jpg` |
| M2 RN init log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-rn-init-2026-06-20.log` |
| M2 bundle install log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-bundle-install-2026-06-20.log` |
| M2 pod install retry log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-pod-install-retry-2026-06-20.log` |
| M2 device list log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-device-list-2026-06-20.log` |
| M2 Xcode build success log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-xcodebuild-after-gui-signing-2026-06-20.log` |
| M2 install/launch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-run-ios-after-gui-signing-2026-06-20.log` |
| M2 relaunch log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m2-relaunch-2026-06-20.log` |
| M2 app visible confirmation | User confirmed the RN app was visible on the iPhone after install/launch |
| M3 Unity export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-unity-export-2026-06-20.log` |
| M3 initial target build failure log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-xcodebuild-unityframework-2026-06-20.log` |
| M3 scheme build failure log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-xcodebuild-unityframework-scheme-2026-06-20.log` |
| M3 ARKit static-lib retry log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-xcodebuild-unityframework-with-arkit-libs-2026-06-20.log` |
| M3 UnityARKit object compile logs | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-compile-unityarkit-object-2026-06-20.log`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-compile-unityarkit-object-retry-2026-06-20.log`, `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-compile-unityarkit-object-with-interface-2026-06-20.log` |
| M3 successful UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-xcodebuild-unityframework-with-arkit-object-2026-06-20.log` contains `** BUILD SUCCEEDED **` |
| M3 artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-artifact-verification-2026-06-20.log` records the RN framework path, arm64 binary, `104M` framework size, and `9.2M` Data folder |
| M3 reproducible build script | `/Users/wiseungcheol/Desktop/makeupAR/scripts/build_m3_unityframework.sh` verifies generated ARKit native link entries, builds `UnityFramework` with signing disabled, copies Unity `Data`, and places the RN reference artifact |
| M3 reproducible Unity export log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-unity-export-2026-06-20-201720.log` |
| M3 reproducible UnityFramework build log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-xcodebuild-unityframework-2026-06-20-201720.log` contains `** BUILD SUCCEEDED **` |
| M3 reproducible artifact verification log | `/Users/wiseungcheol/Desktop/makeupAR/evidence/logs/m3-repro-artifact-verification-2026-06-20-201720.log` records the RN framework path, arm64 binary, `104M` framework size, `9.2M` Data folder, and `UnitySubsystems/UnityARKit` |
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

- M2 Xcode GUI stale issue record: Xcode's Issue Navigator continued to show the earlier `No such module 'React'` GUI failure after CLI build/install/launch succeeded. This does not block M2 because the same workspace/scheme/device built successfully via `xcodebuild`, and the app installed, launched, displayed, and relaunched on the real iPhone.
- M3 UnityFramework ARKit link check: the reproducible build script now verifies the generated Xcode project includes `UnityARKit.m`, `libUnityARKit.a`, `libUnityARKitFaceTracking.a`, `ARKit.framework`, and `MetalPerformanceShaders.framework` before building. The successful 2026-06-20 20:17 KST run used the generated Xcode project settings without extra PackageCache link overrides.
- M3 Data placement adjustment: generated `Data` is attached to the app target resources by default. `scripts/build_m3_unityframework.sh` copies it into `UnityFramework.framework/Data` after the framework build so M4 has a single referenceable framework artifact.
- M3 generated artifact storage: the RN reference artifact is available locally under `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework`, and `.gitignore` excludes `rn/MakeupARValidation/unity/builds/` so the generated framework is not accidentally source-controlled.
- M4 Unity bridge compile requirement: `@azesmway/react-native-unity` imports `UnityFramework/NativeCallProxy.h`, so the M3 reproducible build script now copies that generated Unity plugin header into `UnityFramework.framework/Headers`. No app-level RN-to-Unity or Unity-to-RN message calls were added or exercised in M4; the native proxy is present only as the package-required compile/link shim.
- M4 initial black screen: the RN view transitioned to the Unity screen but the bridge did not start Unity before a valid window/bounds were available, so iOS Settings initially showed no Camera permission entry and the Unity area stayed black.
- M4 local bridge timing fix: the final successful run used a package-local `RNUnityView.mm` patch that initializes Unity from `didMoveToWindow` once the view has non-zero bounds and a window. This patch is documented as a reproducibility caveat because it lives under ignored `node_modules`.
- M4 real-device result: after the timing fix and fresh install/launch, the RN-hosted Unity screen requested camera access, displayed the front-camera AR feed, showed the magenta diagnostic face overlay, and logged `Face detected: true`.
- M5 stale embedded framework failure: the user-observed symptom was visible AR screen plus visible RN controls, but no color/opacity effect. Logs showed `SendMessage: object RNBridge not found!`.
- M5 framework path correction: the generated reference framework under `rn/MakeupARValidation/unity/builds/ios` contained `RNBridge`, but Xcode embedded the package framework under `node_modules/@azesmway/react-native-unity/ios`. Syncing that package framework fixed message delivery; the build script now performs this sync when `node_modules` is present.
- M5 real-device result: after package framework sync and reinstall, the installed app bundle's `UnityFramework.framework/Data/level0` contained `RNBridge`, and live device logs showed repeated `[M5] recipe_applied` for color and opacity changes while AR face tracking was active.
- First-face-only behavior: after launch, the app appears to keep tracking only the first recognized face and does not reliably reacquire a different person's face later.
- This should be treated as a follow-up validation risk before product AR UX work.
- Candidate follow-up checks: confirm whether the original `ARFace` trackable is actually removed when the first face leaves; log `trackablesChanged` added/updated/removed events; test `ARSession.Reset()` or disable/enable `ARFaceManager` between users; confirm whether `requestedMaximumFaceCount = 1` and ARKit provider behavior are acceptable for the target UX.

## Next Milestone Boundary

M5 is complete. Do not treat the M2 Xcode GUI stale issue record as an M5 blocker unless a fresh CLI build/install/launch fails in a later milestone.

Recommended next validation step is M6, Unity -> RN communication.

Do not start re-entry stability work, makeup-quality work, AI/backend/admin/payment/community work, or product implementation until the plan reaches those milestones.
