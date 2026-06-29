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
CLEAN_DERIVED_DATA="${CLEAN_DERIVED_DATA:-0}"
SKIP_UNITY_EXPORT="${SKIP_UNITY_EXPORT:-0}"
XCODE_DEBUG_INFORMATION_FORMAT="${XCODE_DEBUG_INFORMATION_FORMAT:-dwarf}"
XCODE_GENERATE_DEBUG_SYMBOLS="${XCODE_GENERATE_DEBUG_SYMBOLS:-NO}"
BUILD_TMP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/makeupar-unityframework-$TIMESTAMP.XXXXXX")"
BUILD_TMP_CLEANED=0
if [[ -z "${DERIVED_DATA:-}" ]]; then
  DERIVED_DATA="$ROOT_DIR/unity-builds/xcode-derived-data/UnityFramework"
fi

cleanup_build_tmp_root() {
  if [[ "$BUILD_TMP_CLEANED" == "1" || ! -d "$BUILD_TMP_ROOT" ]]; then
    return
  fi

  if [[ "$KEEP_DERIVED_DATA" == "1" && "$DERIVED_DATA" == "$BUILD_TMP_ROOT"* ]]; then
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

echo "== M3 UnityFramework reproducible build =="
echo "Root: $ROOT_DIR"
echo "Unity project: $UNITY_PROJECT"
echo "Unity binary: $UNITY_BIN"
echo "Export path: $EXPORT_PATH"
echo "Derived data: $DERIVED_DATA"
echo "Build log mode: $BUILD_LOG_MODE"
echo "Clean derived data: $CLEAN_DERIVED_DATA"
echo "Skip Unity export: $SKIP_UNITY_EXPORT"
echo "Xcode debug information format: $XCODE_DEBUG_INFORMATION_FORMAT"
echo "Xcode generate debug symbols: $XCODE_GENERATE_DEBUG_SYMBOLS"
echo "Timestamp: $TIMESTAMP"

if [[ "$SKIP_UNITY_EXPORT" != "1" ]]; then
  require_file "$UNITY_BIN"
fi
require_file "$NATIVE_PROXY_HEADER"
mkdir -p "$LOG_DIR" "$BUILD_LOG_DIR" "$DERIVED_DATA" "$RN_FRAMEWORK_DIR"

if [[ "$CLEAN_DERIVED_DATA" == "1" ]]; then
  if [[ -z "$DERIVED_DATA" || "$DERIVED_DATA" == "/" ]]; then
    echo "Refusing to clean unsafe DerivedData path: $DERIVED_DATA" >&2
    exit 2
  fi
  echo "Cleaning Xcode DerivedData cache: $DERIVED_DATA"
  rm -rf "$DERIVED_DATA"
  mkdir -p "$DERIVED_DATA"
elif [[ "$CLEAN_DERIVED_DATA" != "0" ]]; then
  echo "Unsupported CLEAN_DERIVED_DATA: $CLEAN_DERIVED_DATA (expected 0 or 1)" >&2
  exit 2
fi

if [[ "$SKIP_UNITY_EXPORT" != "0" && "$SKIP_UNITY_EXPORT" != "1" ]]; then
  echo "Unsupported SKIP_UNITY_EXPORT: $SKIP_UNITY_EXPORT (expected 0 or 1)" >&2
  exit 2
fi

echo
echo "== Unity iOS export =="
if [[ "$SKIP_UNITY_EXPORT" == "1" ]]; then
  echo "Skipping Unity export; reusing existing export at: $EXPORT_PATH"
  echo "Unity export skipped; reused existing export at: $EXPORT_PATH" > "$UNITY_EXPORT_LOG"
else
  "$UNITY_BIN" \
    -batchmode \
    -quit \
    -projectPath "$UNITY_PROJECT" \
    -executeMethod MakeupARValidationSetup.ExportIosProject \
    -logFile "$UNITY_EXPORT_LOG"
fi

require_file "$PROJECT_FILE"
require_file "$EXPORT_PATH/Data/boot.config"

echo
echo "== Verify generated ARKit native links =="
for required_entry in \
  "UnityARKit.m in Sources" \
  "libUnityARKit.a in Frameworks" \
  "libUnityARKitFaceTracking.a in Frameworks" \
  "ARKit.framework in Frameworks" \
  "Vision.framework in Frameworks" \
  "MetalPerformanceShaders.framework in Frameworks"; do
  if ! grep -q "$required_entry" "$PROJECT_FILE"; then
    echo "Generated Xcode project is missing required ARKit entry: $required_entry" >&2
    echo "Project file: $PROJECT_FILE" >&2
    exit 1
  fi
  echo "Found: $required_entry"
done

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
    DEBUG_INFORMATION_FORMAT="$XCODE_DEBUG_INFORMATION_FORMAT" \
    GCC_GENERATE_DEBUGGING_SYMBOLS="$XCODE_GENERATE_DEBUG_SYMBOLS" \
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
  echo "Build success proof:"
  grep -n "BUILD SUCCEEDED" "$XCODE_BUILD_LOG" || true
} > "$VERIFY_LOG"

cat "$VERIFY_LOG"

cleanup_build_tmp_root

echo
echo "Done."
if [[ "$BUILD_LOG_MODE" == "full" ]]; then
  echo "Unity export log: $UNITY_EXPORT_LOG"
  echo "Xcode build log: $XCODE_BUILD_LOG"
elif [[ -d "$BUILD_TMP_ROOT" ]]; then
  echo "Full Unity/Xcode logs remain with kept temporary build workspace: $BUILD_TMP_ROOT"
else
  echo "Full Unity/Xcode logs were temporary and not retained."
  echo "Set BUILD_LOG_MODE=full to retain them under evidence/logs for a specific evidence pass."
fi
echo "Xcode DerivedData cache: $DERIVED_DATA"
echo "Verification log: $VERIFY_LOG"
