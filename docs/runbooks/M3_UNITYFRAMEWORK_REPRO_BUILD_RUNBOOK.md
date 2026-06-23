# M3 UnityFramework Repro Build Runbook

Use this to regenerate the M3 `UnityFramework.framework` artifact for the next RN embed milestone.

This runbook does not require an iPhone connection because it only exports and builds the Unity iOS framework for generic `iphoneos` arm64. A real iPhone is only needed when running the standalone Unity app or the later RN-hosted Unity runtime.

## Scope

Allowed:

- Unity iOS export.
- `UnityFramework` target build with signing disabled.
- Verification that the generated Xcode project includes ARKit native provider sources and libraries.
- Copying Unity `Data` into `UnityFramework.framework/Data`.
- Copying the final framework to the RN reference path.

Not allowed here:

- RN app embed.
- RN-Unity bridge package installation.
- RN-to-Unity or Unity-to-RN messaging.
- Makeup-quality rendering work.

## Command

From the repo root:

```sh
bash scripts/build_m3_unityframework.sh
```

By default, the script uses temporary Unity/Xcode full logs and temporary Xcode DerivedData, then deletes them after the RN/package frameworks are synced. It keeps only a small artifact verification summary under `evidence/logs/`.

Retain full build logs only for a specific evidence pass:

```sh
BUILD_LOG_MODE=full bash scripts/build_m3_unityframework.sh
```

Retain DerivedData only for local debugging:

```sh
KEEP_DERIVED_DATA=1 bash scripts/build_m3_unityframework.sh
```

## Expected Output

Final RN reference artifact:

```txt
rn/MakeupARValidation/unity/builds/ios/UnityFramework.framework
```

Required verification shape:

```txt
** BUILD SUCCEEDED **
UnityFramework: Mach-O 64-bit dynamically linked shared library arm64
UnityFramework.framework/Data/boot.config
```

## Why This Exists

The Unity export generated during M3 did not make the `UnityFramework` product fully self-contained by itself:

- The generated Xcode project must include `UnityARKit.m`, `libUnityARKit.a`, `libUnityARKitFaceTracking.a`, `ARKit.framework`, and `MetalPerformanceShaders.framework` in the `UnityFramework` build.
- Unity `Data` was generated for the app target and needed to be copied into `UnityFramework.framework/Data`.

The script verifies the generated native ARKit link entries, builds with the Xcode project's own settings, then copies Unity `Data` into the framework. It does this without storing an Apple Development Team ID or changing RN integration code.
