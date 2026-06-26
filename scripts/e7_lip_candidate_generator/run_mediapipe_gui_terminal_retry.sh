#!/usr/bin/env bash
set -u
set -o pipefail

ROOT="/Users/wiseungcheol/Desktop/makeupAR"
RUN_ID="mediapipe-gui-terminal-$(date -u +%Y%m%dT%H%M%SZ)"
OUT_DIR="$ROOT/evidence/e7-lip-candidate-generator/$RUN_ID"
LOG="$OUT_DIR/gui_terminal_command_output.txt"

mkdir -p "$OUT_DIR"
cd "$ROOT" || exit 2

{
  echo "MediaPipe GUI Terminal retry"
  echo "root=$ROOT"
  echo "run_id=$RUN_ID"
  echo "python=$ROOT/.venv/bin/python"
  echo "output=$OUT_DIR"
  echo

  env \
    PYTHONDONTWRITEBYTECODE=1 \
    MPLCONFIGDIR="$ROOT/.cache/matplotlib" \
    "$ROOT/.venv/bin/python" \
    "$ROOT/scripts/e7_lip_candidate_generator/retry_mediapipe_lip_landmarker.py" \
    --run-id "$RUN_ID"

  STATUS=$?
  echo
  echo "exit_status=$STATUS"
  echo "$OUT_DIR" > "$ROOT/evidence/e7-lip-candidate-generator/latest_gui_terminal_retry.txt"
  echo "latest_marker=$ROOT/evidence/e7-lip-candidate-generator/latest_gui_terminal_retry.txt"
  echo "log=$LOG"
  exit "$STATUS"
} 2>&1 | tee "$LOG"
