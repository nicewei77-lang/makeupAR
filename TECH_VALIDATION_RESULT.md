# Tech Validation Result

Date: 2026-06-20

Latest re-check: 2026-06-20 21:03 KST

## Scope

Session 5 / M4 only: React Native app opens the Unity screen.

RN-to-Unity messaging, Unity-to-RN messaging, recipe/color/opacity transfer, re-entry stability stress testing, makeup quality, AI/backend/admin/payment/community, and Android work were not attempted.

Authoritative inputs:

- `AGENTS.md`
- `TECH_VALIDATION_TEST_PLAN.md` section 11, M4 React Native app opens the Unity screen
- `TECH_VALIDATION_RESULT.md` previous `Next Milestone Boundary`

## Workspace Document State

Active root documents:

- `AGENTS.md`: repository working rules, milestone scope boundaries, document policy, and evidence/cleanup requirements.
- `TECH_VALIDATION_TEST_PLAN.md`: stable validation contract, milestone order, and document policy.
- `TECH_VALIDATION_RESULT.md`: latest milestone decisions, current status, evidence, and next boundary.

Completed session-specific plan/status documents have been absorbed into this result document and removed from the active root. New `M*_..._PLAN.md` files should be temporary: create them only when a session needs one, then absorb the outcome here and delete the plan after completion.

## Final Decision

Status: Green

M4 is Green because the React Native app now opens the Unity AR screen on the real iPhone:

- `@azesmway/react-native-unity` 1.0.11 was installed in the RN project.
- iOS pods were reinstalled and autolinked `react-native-unity`.
- The M3 `UnityFramework.framework` artifact exists under the RN project, includes Unity `Data`, and was regenerated with `NativeCallProxy.h` for bridge compilation.
- RN Home shows the M4 validation screen, validation status text, and `Start AR`.
- `Start AR` opens a full-screen Unity view with a `Close` control and debug overlay.
- The real iPhone displays the Unity AR front-camera feed inside the RN app.
- The Unity diagnostic magenta face overlay is visible on the detected face.
- Runtime logs from the RN-hosted app show UnityFramework loading, ARKit session configuration, `Camera requested/current: User/User`, `SessionTracking`, `Current tracked face count: 1`, and `Face detected: true`.
- `Close` returns to the RN Home screen, as shown by the user-provided Home screenshot during the same validation flow.

Known limitations:

- Initial M4 attempts showed a black Unity screen and no camera permission entry in iOS Settings. The final successful run required an iOS bridge initialization timing fix in `node_modules/@azesmway/react-native-unity/ios/RNUnityView.mm`: initialize Unity from `didMoveToWindow` after the RN view has a non-zero window/bounds. This is currently a local package patch and should be made durable before clean reinstall/reclone workflows.
- The final app still shows the React Native warning toast `Open debugger to view warnings.` This did not block the Unity AR screen, camera feed, or face detection.
- Unity logs include `Failed to initialize subsystem ARKit-Meshing [error: 1]`, but ARKit face tracking still reaches `SessionTracking` and detects one face. Meshing is not part of the M4 completion criteria.
- Unity logs include `Can't add component because class 'SphereCollider' doesn't exist!` from the diagnostic marker path. The visible face overlay and face detection still work; fixing diagnostic-marker internals is outside M4.
- The existing M1 observation about first-face-only behavior remains a follow-up risk and is not part of M4.

These do not block M4 because M4 validates only that RN can open a full-screen Unity view and show an AR camera feed or Unity scene on a real iPhone. RN-Unity messaging, Unity-to-RN messaging, and re-entry stability remain M5+ scope.

## Milestone History

| Milestone | Decision | Notes |
| --- | --- | --- |
| M0. Environment gate | Green as of 2026-06-20 | macOS 26.5.1, full Xcode 26.5, Node 22.23.0, npm 10.9.8, Watchman 2026.06.15.00, CocoaPods 1.16.2, Unity 6000.3.18f1, and iOS Build Support are available. |
| M1. Unity standalone AR validation | Green | Real iPhone runtime confirmed front camera, ARKit face tracking, visible diagnostic marker/mask, and face-following behavior. |
| M2. React Native standalone iOS validation | Green | RN 0.86.0 standalone iOS app builds, installs, launches, displays on the real iPhone, and relaunches once without crash. |
| M3. UnityFramework generation | Green | Unity iOS export and `UnityFramework.framework` arm64 build succeeded; framework with `Data` is available under the RN project for M4 reference. |
| M4. RN-Unity embed | Green | RN Home opens a full-screen Unity view on the real iPhone; AR camera feed, diagnostic face overlay, and face-detected logs are confirmed. |
| M5. RN -> Unity communication | Next | Do this before Unity-to-RN messaging or re-entry stability work. |

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
| Signing storage policy | Apple Development Team ID is not stored in `MakeupARValidation.xcodeproj/project.pbxproj`; M4 CLI signing used temporary extra params and redacted logs |
| Unity integration | M4 embeds the local M3 `UnityFramework.framework` through `@azesmway/react-native-unity` |
| RN-Unity bridge package | `@azesmway/react-native-unity` 1.0.11 installed and autolinked through CocoaPods |
| M4 screens | `App.tsx` contains the minimal Home screen and full-screen Unity screen required by section 11 |
| M4 Home controls | Home shows validation status text and `Start AR` |
| M4 Unity controls | Unity screen shows full-screen `UnityView`, `Close`, and debug log text/overlay |
| Camera permission | `NSCameraUsageDescription` is present in the RN iOS app Info.plist |
| M4 reference artifact | `rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework` |
| M4 bridge initialization caveat | The successful local run includes a package-local `RNUnityView.mm` timing patch in `node_modules` so Unity initializes after `didMoveToWindow` with a real window/bounds |

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
| iOS bridge proxy | `Assets/Plugins/iOS/NativeCallProxy.h` and `Assets/Plugins/iOS/NativeCallProxy.mm` were added so the RN Unity bridge can compile against the generated UnityFramework |
| M3 exported Xcode project | `/Users/wiseungcheol/Desktop/makeupAR/unity-builds/ios-export` |
| M3 generated framework source product | `/Users/wiseungcheol/Desktop/makeupAR/evidence/derived-data/m3-unityframework-repro-2026-06-20-201720/Build/Products/Release-iphoneos/UnityFramework.framework` |

## Evidence

| Evidence | Path / content |
| --- | --- |
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
- First-face-only behavior: after launch, the app appears to keep tracking only the first recognized face and does not reliably reacquire a different person's face later.
- This should be treated as a follow-up validation risk before product AR UX work.
- Candidate follow-up checks: confirm whether the original `ARFace` trackable is actually removed when the first face leaves; log `trackablesChanged` added/updated/removed events; test `ARSession.Reset()` or disable/enable `ARFaceManager` between users; confirm whether `requestedMaximumFaceCount = 1` and ARKit provider behavior are acceptable for the target UX.

## Next Milestone Boundary

M4 is complete. Do not treat the M2 Xcode GUI stale issue record as an M4 blocker unless a fresh CLI build/install/launch fails in a later milestone.

Recommended next validation step is M5, RN -> Unity communication.

Do not start Unity-to-RN messaging, re-entry stability work, makeup-quality work, recipe/color/opacity transfer, or AI/backend/admin/payment/community work until the plan reaches those milestones.
