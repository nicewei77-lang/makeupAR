#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITY_PROJECT="$ROOT_DIR/unity/MakeupARUnityValidation"
UNITY_BIN="${UNITY_BIN:-/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity}"
EXPORT_PATH="$ROOT_DIR/unity-builds/ios-export"
LOG_DIR="$ROOT_DIR/evidence/logs"
TIMESTAMP="${TIMESTAMP:-$(date '+%Y-%m-%d-%H%M%S')}"
BUILD_LOG_MODE="${BUILD_LOG_MODE:-summary}"
KEEP_DERIVED_DATA="${KEEP_DERIVED_DATA:-0}"
CUSTOM_DERIVED_DATA=0
BUILD_TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/makeupar-unityframework-$TIMESTAMP.XXXXXX")"
BUILD_TMP_CLEANED=0
if [[ -n "${DERIVED_DATA:-}" ]]; then
  CUSTOM_DERIVED_DATA=1
else
  DERIVED_DATA="$BUILD_TMP_ROOT/DerivedData"
fi

cleanup_build_tmp_root() {
  if [[ "$BUILD_TMP_CLEANED" == "1" || ! -d "$BUILD_TMP_ROOT" ]]; then
    return
  fi

  if [[ "$KEEP_DERIVED_DATA" == "1" && "$CUSTOM_DERIVED_DATA" != "1" ]]; then
    echo "Keeping temporary build workspace: $BUILD_TMP_ROOT"
    BUILD_TMP_CLEANED=1
    return
  fi

  rm -rf "$BUILD_TMP_ROOT"
  BUILD_TMP_CLEANED=1
  echo "Removed temporary build workspace: $BUILD_TMP_ROOT"
}

trap cleanup_build_tmp_root EXIT

PROJECT_FILE="$EXPORT_PATH/Unity-iPhone.xcodeproj/project.pbxproj"
NATIVE_PROXY_HEADER="$UNITY_PROJECT/Assets/Plugins/iOS/NativeCallProxy.h"

if [[ "$BUILD_LOG_MODE" == "full" ]]; then
  BUILD_LOG_DIR="$LOG_DIR"
elif [[ "$BUILD_LOG_MODE" == "summary" ]]; then
  BUILD_LOG_DIR="$BUILD_TMP_ROOT"
else
  echo "Unsupported BUILD_LOG_MODE: $BUILD_LOG_MODE (expected summary or full)" >&2
  exit 2
fi

UNITY_EXPORT_LOG="$BUILD_LOG_DIR/m3-repro-unity-export-$TIMESTAMP.log"
XCODE_BUILD_LOG="$BUILD_LOG_DIR/m3-repro-xcodebuild-unityframework-$TIMESTAMP.log"
VERIFY_LOG="$LOG_DIR/m3-repro-artifact-verification-$TIMESTAMP.log"

RN_FRAMEWORK_DIR="$ROOT_DIR/rn/MakeupARValidation/unity/builds/ios"
RN_FRAMEWORK="$RN_FRAMEWORK_DIR/UnityFramework.framework"
PACKAGE_FRAMEWORK="$ROOT_DIR/rn/MakeupARValidation/node_modules/@azesmway/react-native-unity/ios/UnityFramework.framework"
PRODUCT_FRAMEWORK="$DERIVED_DATA/Build/Products/Release-iphoneos/UnityFramework.framework"

require_file() {
  if [[ ! -f "$1" ]]; then
    echo "Missing required file: $1" >&2
    exit 1
  fi
}

VERIFY_MISSING_REQUIRED_RUNTIME_STRING=0

framework_contains_string() {
  local framework="$1"
  local needle="$2"
  grep -R -a -q -- "$needle" "$framework"
}

verify_framework_string() {
  local label="$1"
  local framework="$2"
  local needle="$3"

  if framework_contains_string "$framework" "$needle"; then
    echo "present [$label]: $needle"
    return
  fi

  echo "MISSING [$label]: $needle"
  VERIFY_MISSING_REQUIRED_RUNTIME_STRING=1
}

verify_framework_any_string() {
  local label="$1"
  local framework="$2"
  local description="$3"
  shift 3

  local needle
  for needle in "$@"; do
    if framework_contains_string "$framework" "$needle"; then
      echo "present [$label]: $description via $needle"
      return
    fi
  done

  echo "MISSING [$label]: $description (expected one of: $*)"
  VERIFY_MISSING_REQUIRED_RUNTIME_STRING=1
}

verify_framework_required_runtime_strings() {
  local label="$1"
  local framework="$2"

  echo "Required runtime strings for $label:"
  verify_framework_string "$label" "$framework" "generated_lip_mask_applied.latest.json"
  verify_framework_string "$label" "$framework" "CaptureE7ReferenceFrameJson"
  verify_framework_string "$label" "$framework" "overlaySyncPhase"
  verify_framework_any_string \
    "$label" \
    "$framework" \
    "generated lip validation control request id" \
    "validationControlRequestId" \
    "controlRequestId"
}

echo "== M3 UnityFramework reproducible build =="
echo "Root: $ROOT_DIR"
echo "Unity project: $UNITY_PROJECT"
echo "Unity binary: $UNITY_BIN"
echo "Export path: $EXPORT_PATH"
echo "Derived data: $DERIVED_DATA"
echo "Build log mode: $BUILD_LOG_MODE"
echo "Timestamp: $TIMESTAMP"

require_file "$UNITY_BIN"
require_file "$NATIVE_PROXY_HEADER"
mkdir -p "$LOG_DIR" "$BUILD_LOG_DIR" "$DERIVED_DATA" "$RN_FRAMEWORK_DIR"

echo
echo "== Unity iOS export =="
"$UNITY_BIN" \
  -batchmode \
  -quit \
  -projectPath "$UNITY_PROJECT" \
  -executeMethod MakeupARValidationSetup.ExportIosProject \
  -logFile "$UNITY_EXPORT_LOG"

require_file "$PROJECT_FILE"
require_file "$EXPORT_PATH/Data/boot.config"

echo
echo "== Verify generated ARKit native links =="
LEGACY_ARKIT_LINKS_FOUND=1
for required_entry in \
  "UnityARKit.m in Sources" \
  "libUnityARKit.a in Frameworks" \
  "libUnityARKitFaceTracking.a in Frameworks" \
  "ARKit.framework in Frameworks" \
  "MetalPerformanceShaders.framework in Frameworks"; do
  if ! grep -q "$required_entry" "$PROJECT_FILE"; then
    LEGACY_ARKIT_LINKS_FOUND=0
    echo "Legacy ARKit entry not present: $required_entry"
    continue
  fi
  echo "Found legacy ARKit entry: $required_entry"
done

if [[ "$LEGACY_ARKIT_LINKS_FOUND" == "0" ]]; then
  echo "Legacy ARKit native entries were not all present; checking Unity 6000 generated ARKit sources."
  for required_entry in \
    "Unity.XR.ARKit.cpp" \
    "Unity.XR.ARKit_CodeGen.c" \
    "Unity.XR.ARKit.FaceTracking.cpp" \
    "Unity.XR.ARKit.FaceTracking_CodeGen.c"; do
    if ! grep -q "$required_entry" "$PROJECT_FILE"; then
      echo "Generated Xcode project is missing required ARKit generated source: $required_entry" >&2
      echo "Project file: $PROJECT_FILE" >&2
      exit 1
    fi
    echo "Found Unity 6000 ARKit generated source: $required_entry"
  done

  ARKIT_SUBSYSTEM_MANIFEST="$EXPORT_PATH/Data/UnitySubsystems/UnityARKit/UnitySubsystemsManifest.json"
  require_file "$ARKIT_SUBSYSTEM_MANIFEST"
  if ! grep -q '"libraryName": "UnityARKit"' "$ARKIT_SUBSYSTEM_MANIFEST"; then
    echo "UnityARKit subsystem manifest is missing libraryName=UnityARKit" >&2
    echo "Manifest file: $ARKIT_SUBSYSTEM_MANIFEST" >&2
    exit 1
  fi
  echo "Found UnityARKit subsystem manifest: $ARKIT_SUBSYSTEM_MANIFEST"
fi

echo
echo "== Build UnityFramework target =="
run_xcodebuild() {
  xcodebuild \
    -project "$EXPORT_PATH/Unity-iPhone.xcodeproj" \
    -scheme UnityFramework \
    -configuration Release \
    -sdk iphoneos \
    -destination "generic/platform=iOS" \
    -derivedDataPath "$DERIVED_DATA" \
    CODE_SIGNING_ALLOWED=NO \
    build
}

if [[ "$BUILD_LOG_MODE" == "full" ]]; then
  if ! run_xcodebuild 2>&1 | tee "$XCODE_BUILD_LOG"; then
    echo "UnityFramework build failed. Full log: $XCODE_BUILD_LOG" >&2
    exit 1
  fi
else
  if ! run_xcodebuild > "$XCODE_BUILD_LOG" 2>&1; then
    echo "UnityFramework build failed. Last 80 log lines:" >&2
    tail -n 80 "$XCODE_BUILD_LOG" >&2
    exit 1
  fi
  grep "BUILD SUCCEEDED" "$XCODE_BUILD_LOG" || true
fi

require_file "$PRODUCT_FRAMEWORK/UnityFramework"
mkdir -p "$PRODUCT_FRAMEWORK/Headers"
cp "$NATIVE_PROXY_HEADER" "$PRODUCT_FRAMEWORK/Headers/NativeCallProxy.h"
require_file "$PRODUCT_FRAMEWORK/Headers/NativeCallProxy.h"

echo
echo "== Place Unity Data inside framework =="
rm -rf "$PRODUCT_FRAMEWORK/Data"
ditto "$EXPORT_PATH/Data" "$PRODUCT_FRAMEWORK/Data"
require_file "$PRODUCT_FRAMEWORK/Data/boot.config"

echo
echo "== Copy framework to RN reference path =="
rm -rf "$RN_FRAMEWORK"
ditto "$PRODUCT_FRAMEWORK" "$RN_FRAMEWORK"
require_file "$RN_FRAMEWORK/UnityFramework"
require_file "$RN_FRAMEWORK/Data/boot.config"
require_file "$RN_FRAMEWORK/Headers/NativeCallProxy.h"

if [[ -d "$(dirname "$PACKAGE_FRAMEWORK")" ]]; then
  echo
  echo "== Copy framework to react-native-unity package path =="
  rm -rf "$PACKAGE_FRAMEWORK"
  ditto "$PRODUCT_FRAMEWORK" "$PACKAGE_FRAMEWORK"
  require_file "$PACKAGE_FRAMEWORK/UnityFramework"
  require_file "$PACKAGE_FRAMEWORK/Data/boot.config"
  require_file "$PACKAGE_FRAMEWORK/Headers/NativeCallProxy.h"
fi

echo
echo "== Verify artifact =="
{
  echo "M3 UnityFramework reproducible artifact verification"
  echo "Timestamp: $TIMESTAMP"
  echo
  xcodebuild -version
  echo
  echo "RN framework: $RN_FRAMEWORK"
  file "$RN_FRAMEWORK/UnityFramework"
  du -sh "$RN_FRAMEWORK"
  du -sh "$RN_FRAMEWORK/Data"
  if [[ -d "$PACKAGE_FRAMEWORK" ]]; then
    echo
    echo "Package framework: $PACKAGE_FRAMEWORK"
    file "$PACKAGE_FRAMEWORK/UnityFramework"
    du -sh "$PACKAGE_FRAMEWORK"
    du -sh "$PACKAGE_FRAMEWORK/Data"
  fi
  echo "Native bridge header:"
  ls -l "$RN_FRAMEWORK/Headers/NativeCallProxy.h"
  echo
  echo "Data sample:"
  find "$RN_FRAMEWORK/Data" -maxdepth 2 -print | sort
  echo
  verify_framework_required_runtime_strings "RN reference" "$RN_FRAMEWORK"
  if [[ -d "$PACKAGE_FRAMEWORK" ]]; then
    echo
    verify_framework_required_runtime_strings "package-local" "$PACKAGE_FRAMEWORK"
  fi
  echo
  echo "Build success proof:"
  grep -n "BUILD SUCCEEDED" "$XCODE_BUILD_LOG" || true
} > "$VERIFY_LOG"

cat "$VERIFY_LOG"

if [[ "$VERIFY_MISSING_REQUIRED_RUNTIME_STRING" != "0" ]]; then
  echo "UnityFramework artifact verification failed: missing required E7 runtime strings." >&2
  echo "Verification log: $VERIFY_LOG" >&2
  exit 1
fi

cleanup_build_tmp_root

echo
echo "Done."
if [[ "$BUILD_LOG_MODE" == "full" ]]; then
  echo "Unity export log: $UNITY_EXPORT_LOG"
  echo "Xcode build log: $XCODE_BUILD_LOG"
elif [[ "$KEEP_DERIVED_DATA" == "1" && "$CUSTOM_DERIVED_DATA" != "1" ]]; then
  echo "Full Unity/Xcode logs remain with kept temporary build workspace: $BUILD_TMP_ROOT"
else
  echo "Full Unity/Xcode logs were temporary and not retained."
  echo "Set BUILD_LOG_MODE=full to retain them under evidence/logs for a specific evidence pass."
fi
echo "Verification log: $VERIFY_LOG"
