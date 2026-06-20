#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UNITY_PROJECT="$ROOT_DIR/unity/MakeupARUnityValidation"
UNITY_BIN="${UNITY_BIN:-/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity}"
EXPORT_PATH="$ROOT_DIR/unity-builds/ios-export"
LOG_DIR="$ROOT_DIR/evidence/logs"
TIMESTAMP="${TIMESTAMP:-$(date '+%Y-%m-%d-%H%M%S')}"
DERIVED_DATA="${DERIVED_DATA:-$ROOT_DIR/evidence/derived-data/m3-unityframework-repro-$TIMESTAMP}"
PROJECT_FILE="$EXPORT_PATH/Unity-iPhone.xcodeproj/project.pbxproj"
NATIVE_PROXY_HEADER="$UNITY_PROJECT/Assets/Plugins/iOS/NativeCallProxy.h"

UNITY_EXPORT_LOG="$LOG_DIR/m3-repro-unity-export-$TIMESTAMP.log"
XCODE_BUILD_LOG="$LOG_DIR/m3-repro-xcodebuild-unityframework-$TIMESTAMP.log"
VERIFY_LOG="$LOG_DIR/m3-repro-artifact-verification-$TIMESTAMP.log"

RN_FRAMEWORK_DIR="$ROOT_DIR/rn/MakeupARValidation/unity/builds/ios"
RN_FRAMEWORK="$RN_FRAMEWORK_DIR/UnityFramework.framework"
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
echo "Timestamp: $TIMESTAMP"

require_file "$UNITY_BIN"
require_file "$NATIVE_PROXY_HEADER"
mkdir -p "$LOG_DIR" "$DERIVED_DATA" "$RN_FRAMEWORK_DIR"

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
for required_entry in \
  "UnityARKit.m in Sources" \
  "libUnityARKit.a in Frameworks" \
  "libUnityARKitFaceTracking.a in Frameworks" \
  "ARKit.framework in Frameworks" \
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
xcodebuild \
  -project "$EXPORT_PATH/Unity-iPhone.xcodeproj" \
  -scheme UnityFramework \
  -configuration Release \
  -sdk iphoneos \
  -destination "generic/platform=iOS" \
  -derivedDataPath "$DERIVED_DATA" \
  CODE_SIGNING_ALLOWED=NO \
  build 2>&1 | tee "$XCODE_BUILD_LOG"

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

echo
echo "Done."
echo "Unity export log: $UNITY_EXPORT_LOG"
echo "Xcode build log: $XCODE_BUILD_LOG"
echo "Verification log: $VERIFY_LOG"
