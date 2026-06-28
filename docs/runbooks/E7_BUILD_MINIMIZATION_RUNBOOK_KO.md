# E7 Build Minimization Runbook

## 목적

E7 Generate 앱의 다음 iPhone 빌드 전에, UnityFramework를 매번 재생성하지 않도록
파일 단위로 제품 런타임 필수 파일과 legacy/debug 리소스를 구분한다.

이 문서는 파일 삭제 지시서가 아니다. 현재 목표는 빌드 전에 판단 가능한 근거를 만들고,
참조가 남아 있는 리소스를 감으로 빼서 앱 흐름을 깨뜨리지 않는 것이다.

## 기본 명령

```bash
cd rn/MakeupARValidation
npm run e7:build-plan -- --no-report
```

상세 JSON/Markdown report를 남기려면 `--no-report`를 빼고 실행한다.

```bash
cd rn/MakeupARValidation
npm run e7:build-plan
```

산출물:

```text
evidence/logs/e7-build-plan/latest/minimum-build-decision.json
evidence/logs/e7-build-plan/latest/minimum-build-decision.md
```

## 빌드 판단 원칙

| 변경 종류 | 판단 | 의미 |
| --- | --- | --- |
| RN JS/Swift만 변경 | `skip-unityframework-run-rn-xcode-only` | UnityFramework 재생성 없이 RN/Xcode만 진행 |
| Unity runtime script/scene/shader/material/plugin/product resource 변경 | `run-unityframework-build` | UnityFramework 재생성 필요 |
| Unity editor smoke/tooling만 변경 | `skip-unityframework-run-unity-import-if-needed` | player framework 재생성 불필요 |
| legacy/debug mask resource만 변경 | `skip-product-phone-build-legacy-debug-resource-only` | 제품 Generate 빌드는 보통 불필요 |
| framework hash/string 불일치 | `sync-or-rebuild-unityframework-before-xcode` | sync 또는 rebuild 전 Xcode 금지 |
| 미분류 경로 변경 | `manual-review-before-build` | 사람이 영향 범위를 먼저 판정 |

## 현재 제품 런타임 필수

아래는 현재 앱 Generate, capture, saved package, Unity apply ack, AR 검증 화면을 위해 보존한다.

```text
unity/MakeupARUnityValidation/Assets/Scenes/MakeupARFaceValidation.unity
unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs
unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs
unity/MakeupARUnityValidation/Assets/Scripts/E7SynchronizedCaptureExporter.cs
unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs
unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingMarker.cs
unity/MakeupARUnityValidation/Assets/Plugins/iOS/NativeCallProxy.h
unity/MakeupARUnityValidation/Assets/Plugins/iOS/NativeCallProxy.mm
unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader
unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMaskMaterial.mat
unity/MakeupARUnityValidation/Assets/Prefabs/ValidationFaceOverlay.prefab
unity/MakeupARUnityValidation/Assets/Materials/ValidationFaceOverlay.mat
unity/MakeupARUnityValidation/Assets/XR/Loaders/ARKitLoader.asset
unity/MakeupARUnityValidation/Assets/XR/Settings/ARKitSettings.asset
unity/MakeupARUnityValidation/Assets/XR/XRGeneralSettingsPerBuildTarget.asset
unity/MakeupARUnityValidation/Packages/manifest.json
unity/MakeupARUnityValidation/Packages/packages-lock.json
unity/MakeupARUnityValidation/ProjectSettings/
```

## 현재 Resources 분류

`Assets/Resources/**`는 Unity player에 포함될 수 있다. 따라서 여기에 있는 파일은
참조가 남아 있는 동안 삭제하거나 이동하지 않는다.

제품 fallback/reference로 유지:

```text
lip-smooth-mask-v1.png
cheek-smooth-mask-v1.png
eye-smooth-mask-v1.png
e7-lip-balanced-uv-v0.png
e7-blush-balanced-uv-v0.png
e7-brow-balanced-uv-v0.png
e7-eyeliner-minimal-safe-uv-v0.png
e7-full-face-region-runtime-assets.json
```

legacy/debug 후보지만 아직 제외 금지:

```text
e7-lip-validation-tight-auto-v0.png
e7-lip-validation-tight-user-v0.png
e7-lip-validation-safe-v0.png
e7-lip-validation-cv-parsing-smooth-v1.png
e7-lip-validation-cv-vision-fill-v1.png
e7-lip-validation-cv-vision-color-v1.png
e7-lip-validation-cv-hybrid-safe-v1.png
e7-lip-validation-cv-hybrid-balanced-v1.png
e7-lip-validation-runtime-candidates.json
```

보류 이유:

- RN `LIP_RUNTIME_CANDIDATE_OPTIONS`와 old Compact HUD/recipe path가 아직 일부 legacy id를 참조한다.
- Unity `E3RegionMaskOverlay.cs` / `RNBridge.cs`는 legacy `e7-lip-validation-*` id prefix를 아직 허용한다.
- registry/scripts 참조가 남아 있어 audit상 `exclude-ready`가 아니다.

현재 실제 이동/삭제:

```text
없음
```

현재 audit 기준:

```text
SmoothRegionMasks resources: 17
legacyValidationResources: 9
excludeReadyResources: 0
```

## 이미 제품 빌드에서 제외되는 항목

`Assets/Editor/**`는 Unity player build에 들어가지 않는 editor-only 영역이다.

```text
Assets/Editor/E7FullFaceRegionPackageSmoke.cs
Assets/Editor/E7GeneratedLipMaskSmoke.cs
Assets/Editor/MakeupARValidationSetup.cs
Assets/Editor/SmoothRegionMaskTextureImporter.cs
```

XR Simulation 관련 파일은 iPhone 제품 runtime의 ARKit 경로가 아니므로 제외 후보지만,
실제로 옮기기 전 Unity import/compile을 통과해야 한다.

```text
Assets/XR/Loaders/SimulationLoader.asset
Assets/XR/Resources/XRSimulationRuntimeSettings.asset
Assets/XR/Settings/XRSimulationSettings.asset
Assets/XR/UserSimulationSettings/**
```

## 가상 변경 검증

legacy/debug resource만 변경된 상황:

```bash
node scripts/e7_build/decide_minimum_build.mjs --no-report \
  --changed-file=unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/e7-lip-validation-cv-vision-fill-v1.png
```

예상:

```text
decision=skip-product-phone-build-legacy-debug-resource-only
```

제품 fallback resource가 변경된 상황:

```bash
node scripts/e7_build/decide_minimum_build.mjs --no-report \
  --changed-file=unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/lip-smooth-mask-v1.png
```

예상:

```text
decision=run-unityframework-build
```

Unity runtime script가 변경된 상황:

```bash
node scripts/e7_build/decide_minimum_build.mjs --no-report \
  --changed-file=unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs
```

예상:

```text
decision=run-unityframework-build
```

RN만 변경된 상황:

```bash
node scripts/e7_build/decide_minimum_build.mjs --no-report \
  --changed-file=rn/MakeupARValidation/App.tsx
```

예상:

```text
decision=skip-unityframework-run-rn-xcode-only
```

## 다음 정리 단계

legacy/debug Resources를 실제로 빼려면 아래 순서로 진행한다.

1. RN old Compact HUD 후보 선택지에서 legacy mask id를 제거하거나 debug-only 진입으로 격리한다.
2. Unity runtime에서 legacy `e7-lip-validation-*` prefix 허용이 제품 path에 필요한지 확인한다.
3. registry와 generation scripts가 제품 빌드에 필요한지 분리한다.
4. `npm run e7:build-plan`에서 해당 resource가 `exclude-ready-after-move`가 되는지 확인한다.
5. 그때만 `Assets/Resources` 밖으로 이동한다.
6. Unity import/compile, RN TypeScript/Jest/lint, `npm run e7:prebuild:full`을 통과한다.
7. UnityFramework 재생성은 실제 player 산출물에서 빠졌는지 확인할 때만 실행한다.

## 기대 효과

가장 큰 속도 이득은 PNG 몇 개 삭제가 아니라, RN/UI/JS 변경 때 Unity export와
UnityFramework build를 건너뛰는 것이다. 현재 `Assets` 자체는 작지만
UnityFramework 재생성은 오래 걸린다. 따라서 이 runbook의 핵심은 파일 삭제보다
변경 영향 판단을 반복 가능하게 만드는 것이다.
