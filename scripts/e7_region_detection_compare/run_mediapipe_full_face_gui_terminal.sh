#!/usr/bin/env bash
set -u

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
PAIR_ID="${1:-pair_face_20260627T091334Z_06}"
STATUS_PATH="${2:-/private/tmp/makeupar-mediapipe-full-face.status}"
STDOUT_PATH="${3:-/private/tmp/makeupar-mediapipe-full-face.stdout}"
STDERR_PATH="${4:-/private/tmp/makeupar-mediapipe-full-face.stderr}"

cd "$REPO_ROOT" || exit 2
rm -f "$STATUS_PATH" "$STDOUT_PATH" "$STDERR_PATH"

"$REPO_ROOT/.venv/bin/python" \
  "$REPO_ROOT/scripts/e7_region_detection_compare/run_mediapipe_full_face_landmarker.py" \
  --frame "$REPO_ROOT/evidence/e7-reference-atlas/capture_pairs/$PAIR_ID/frame.png" \
  --mediapipe-model "$REPO_ROOT/.cache/mediapipe/face_landmarker.task" \
  --output-json "$REPO_ROOT/evidence/e7-reference-atlas/capture_pairs/$PAIR_ID/mediapipe_face_landmarks.json" \
  --capture-pair-id "$PAIR_ID" \
  --image-source numpy_rgb \
  --delegate cpu \
  --threshold 0.3 \
  >"$STDOUT_PATH" \
  2>"$STDERR_PATH"

exit_code=$?
printf "%s\n" "$exit_code" > "$STATUS_PATH"
exit "$exit_code"
