#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
LOG_DIR="$ROOT_DIR/evidence/logs"
TIMESTAMP="${TIMESTAMP:-$(date '+%Y-%m-%d-%H%M%S')}"
if [[ -z "${APP_PATH:-}" ]]; then
  for candidate in \
    /tmp/makeupar-rn-xcode-device-derived-mediapipe-rn-boundary-event/Build/Products/Debug-iphoneos/MakeupARValidation.app \
    /tmp/makeupar-rn-xcode-device-derived-mediapipe-exported-symbols/Build/Products/Debug-iphoneos/MakeupARValidation.app
  do
    if [[ -d "$candidate" ]]; then
      APP_PATH="$candidate"
      break
    fi
  done
fi
APP_PATH="${APP_PATH:-/tmp/makeupar-rn-xcode-device-derived-mediapipe-rn-boundary-event/Build/Products/Debug-iphoneos/MakeupARValidation.app}"
RUN_SECONDS="${RUN_SECONDS:-120}"
DEVICE_ID="${DEVICE_ID:-}"
BUNDLE_ID="${BUNDLE_ID:-}"
SCENARIO_SUMMARY="${SCENARIO_SUMMARY:-$LOG_DIR/e7-eyebrow-device-scenarios-$TIMESTAMP.md}"
RUNTIME_LOG="$LOG_DIR/e7-eyebrow-device-runtime-$TIMESTAMP.log"
DEVICES_JSON="$LOG_DIR/e7-eyebrow-devices-$TIMESTAMP.json"
INSTALL_JSON="$LOG_DIR/e7-eyebrow-install-$TIMESTAMP.json"
INSTALL_LOG="$LOG_DIR/e7-eyebrow-install-$TIMESTAMP.log"
LAUNCH_JSON="$LOG_DIR/e7-eyebrow-launch-$TIMESTAMP.json"
LAUNCH_TOOL_LOG="$LOG_DIR/e7-eyebrow-launch-tool-$TIMESTAMP.log"
VERIFY_JSON="$LOG_DIR/e7-eyebrow-runtime-verify-$TIMESTAMP.json"

mkdir -p "$LOG_DIR"

fail() {
  echo "error: $*" >&2
  exit 1
}

require_file() {
  [[ -f "$1" ]] || fail "missing required file: $1"
}

require_dir() {
  [[ -d "$1" ]] || fail "missing required directory: $1"
}

resolve_bundle_id() {
  if [[ -n "$BUNDLE_ID" ]]; then
    return
  fi

  BUNDLE_ID="$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' "$APP_PATH/Info.plist")"
  [[ -n "$BUNDLE_ID" ]] || fail "could not resolve bundle id from $APP_PATH/Info.plist"
}

resolve_available_device() {
  xcrun devicectl list devices --json-output "$DEVICES_JSON"
  if [[ -n "$DEVICE_ID" ]]; then
    return
  fi

  DEVICE_ID="$(
    python3 - "$DEVICES_JSON" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
data = json.loads(path.read_text(encoding="utf-8"))
devices = data.get("result", {}).get("devices", [])
for device in devices:
    connection = device.get("connectionProperties", {})
    if connection.get("tunnelState") in {"available", "connected"}:
        print(device.get("identifier", ""))
        break
PY
  )"

  if [[ -z "$DEVICE_ID" ]]; then
    echo "No connected iPhone device found. Current devices:" >&2
    xcrun devicectl list devices >&2 || true
    echo "Device JSON: $DEVICES_JSON" >&2
    exit 3
  fi
}

write_pending_scenario_summary() {
  if [[ -f "$SCENARIO_SUMMARY" ]]; then
    return
  fi

  cat > "$SCENARIO_SUMMARY" <<'EOF'
# E7 Eyebrow Device Scenario Summary

Set each line to visual=pass only after reviewing the device screen/video.

scenario=eyebrow_off_baseline visual=pending
scenario=eyebrow_only visual=pending
scenario=lip_cheek_eyebrow visual=pending
scenario=yaw_pitch visual=pending
scenario=expression_change visual=pending
scenario=tracking_reacquire visual=pending

Visual pass criteria:
- eyebrow attaches above the eyes, on the actual brow area
- eye exclusion holds, with no fill on eyelids/eyes
- tail tapers naturally and is not cut straight
- selected color is visible and not just opacity-only
- lip and cheek remain applied while eyebrow is active
EOF
}

run_launch_console_capture() {
  set +e
  xcrun devicectl device process launch \
    --device "$DEVICE_ID" \
    --terminate-existing \
    --console \
    --json-output "$LAUNCH_JSON" \
    --log-output "$LAUNCH_TOOL_LOG" \
    "$BUNDLE_ID" > "$RUNTIME_LOG" 2>&1 &
  local launch_pid=$!

  sleep "$RUN_SECONDS"
  if kill -0 "$launch_pid" >/dev/null 2>&1; then
    kill -INT "$launch_pid" >/dev/null 2>&1 || true
    sleep 2
  fi
  if kill -0 "$launch_pid" >/dev/null 2>&1; then
    kill "$launch_pid" >/dev/null 2>&1 || true
  fi
  wait "$launch_pid"
  local launch_status=$?
  set -e

  if [[ "$launch_status" -ne 0 && "$launch_status" -ne 130 && "$launch_status" -ne 143 ]]; then
    echo "warning: devicectl launch exited with status $launch_status" >&2
  fi
}

echo "== E7 eyebrow device validation =="
echo "App: $APP_PATH"
echo "Run seconds: $RUN_SECONDS"
echo "Timestamp: $TIMESTAMP"

require_dir "$APP_PATH"
require_file "$APP_PATH/Info.plist"
require_file "$APP_PATH/Frameworks/UnityFramework.framework/UnityFramework"
require_file "$APP_PATH/Frameworks/UnityFramework.framework/Data/Raw/face_landmarker.task"
resolve_bundle_id
resolve_available_device
write_pending_scenario_summary

echo "Bundle id: $BUNDLE_ID"
echo "Device id: $DEVICE_ID"
echo "Scenario summary: $SCENARIO_SUMMARY"
echo
echo "When the app opens, exercise these cases before the capture window ends:"
echo "  eyebrow_off_baseline, eyebrow_only, lip_cheek_eyebrow, yaw_pitch, expression_change, tracking_reacquire"
echo

xcrun devicectl device install app \
  --device "$DEVICE_ID" \
  "$APP_PATH" \
  --timeout 180 \
  --json-output "$INSTALL_JSON" \
  --log-output "$INSTALL_LOG"

run_launch_console_capture

python3 "$ROOT_DIR/scripts/e7_reference_atlas/verify_eyebrow_runtime_evidence.py" \
  "$RUNTIME_LOG" \
  --scenario-summary "$SCENARIO_SUMMARY" | tee "$VERIFY_JSON"

echo
echo "Runtime log: $RUNTIME_LOG"
echo "Verifier output: $VERIFY_JSON"
