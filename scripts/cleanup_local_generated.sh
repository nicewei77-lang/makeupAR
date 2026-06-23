#!/usr/bin/env bash
set -euo pipefail

PROFILE="balanced"
MODE="dry-run"

usage() {
  cat <<'USAGE'
Usage:
  bash scripts/cleanup_local_generated.sh --profile balanced --dry-run
  bash scripts/cleanup_local_generated.sh --profile balanced --apply
  bash scripts/cleanup_local_generated.sh --profile share --dry-run
  bash scripts/cleanup_local_generated.sh --profile share --apply

Profiles:
  balanced  Remove large reproducible local artifacts while preserving speed-critical dependencies.
  share     Remove ignored evidence, build outputs, dependency installs, and editor caches before sharing.

Modes:
  --dry-run  Print targets and sizes only. This is the default.
  --apply    Remove the selected profile targets after safety checks.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --profile)
      PROFILE="${2:-}"
      shift 2
      ;;
    --dry-run)
      MODE="dry-run"
      shift
      ;;
    --apply)
      MODE="apply"
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "[cleanup] Unknown argument: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

if [[ "$PROFILE" != "balanced" && "$PROFILE" != "share" ]]; then
  echo "[cleanup] Unsupported profile: $PROFILE" >&2
  exit 2
fi

repo_root="$(git rev-parse --show-toplevel)"
cd "$repo_root"

balanced_targets=(
  "evidence/derived-data"
  "unity-builds"
  "rn/MakeupARValidation/unity"
  "rn/MakeupARValidation/ios/build"
)

share_targets=(
  "evidence"
  "unity-builds"
  "rn/MakeupARValidation/unity"
  "rn/MakeupARValidation/ios/build"
  "rn/MakeupARValidation/ios/Pods"
  "rn/MakeupARValidation/ios/MakeupARValidation.xcworkspace"
  "rn/MakeupARValidation/ios/.xcode.env.local"
  "rn/MakeupARValidation/node_modules"
  "rn/MakeupARValidation/vendor"
  "rn/MakeupARValidation/android"
  "unity/MakeupARUnityValidation/Library"
  "unity/MakeupARUnityValidation/Logs"
  "unity/MakeupARUnityValidation/UserSettings"
)

if [[ "$PROFILE" == "share" ]]; then
  targets=("${share_targets[@]}")
  preserved=(
    "AGENTS.md"
    "TECH_VALIDATION_TEST_PLAN.md"
    "TECH_VALIDATION_RESULT.md"
    "rn/MakeupARValidation/package-lock.json"
    "rn/MakeupARValidation/ios/Podfile.lock"
    "unity/MakeupARUnityValidation/Packages"
    "unity/MakeupARUnityValidation/ProjectSettings"
  )
else
  targets=("${balanced_targets[@]}")
  preserved=(
    "evidence/logs"
    "evidence/screenshots"
    "evidence/screen-recordings"
    "rn/MakeupARValidation/node_modules"
    "rn/MakeupARValidation/ios/Pods"
    "unity/MakeupARUnityValidation/Library"
  )
fi

echo "[cleanup] repo: $repo_root"
echo "[cleanup] profile: $PROFILE"
echo "[cleanup] mode: $MODE"
echo

echo "[cleanup] preserved paths:"
for path in "${preserved[@]}"; do
  if [[ -e "$path" ]]; then
    du -sh "$path" 2>/dev/null | sed 's/^/[keep] /'
  else
    echo "[keep] missing $path"
  fi
done
echo

assert_safe_target() {
  local path="$1"

  if git ls-files --error-unmatch "$path" >/dev/null 2>&1; then
    echo "[cleanup] Refusing to remove tracked path: $path" >&2
    return 1
  fi

  local tracked_children
  tracked_children="$(git ls-files "$path" | head -n 1)"
  if [[ -n "$tracked_children" ]]; then
    echo "[cleanup] Refusing to remove path with tracked children: $path" >&2
    git ls-files "$path" >&2
    return 1
  fi

  if ! git check-ignore -q "$path" && ! git check-ignore -q "$path/"; then
    echo "[cleanup] Refusing to remove non-ignored path: $path" >&2
    echo "[cleanup] Add it to .gitignore or remove it manually after review." >&2
    return 1
  fi
}

echo "[cleanup] removable targets:"
for path in "${targets[@]}"; do
  assert_safe_target "$path"
  if [[ -e "$path" ]]; then
    du -sh "$path" 2>/dev/null | sed 's/^/[remove] /'
  else
    echo "[remove] missing $path"
  fi
done

echo "[cleanup] repo .DS_Store files:"
ds_store_files=()
while IFS= read -r path; do
  ds_store_files+=("$path")
done < <(find . -name .DS_Store -type f -print | sort)
if [[ "${#ds_store_files[@]}" -eq 0 ]]; then
  echo "[remove] none"
else
  for path in "${ds_store_files[@]}"; do
    path="${path#./}"
    if git ls-files --error-unmatch "$path" >/dev/null 2>&1; then
      echo "[cleanup] Refusing to remove tracked .DS_Store: $path" >&2
      exit 1
    fi
    if ! git check-ignore -q "$path"; then
      echo "[cleanup] Refusing to remove non-ignored .DS_Store: $path" >&2
      exit 1
    fi
    du -sh "$path" 2>/dev/null | sed 's/^/[remove] /'
  done
fi

if [[ "$MODE" == "dry-run" ]]; then
  echo
  echo "[cleanup] dry-run complete. Re-run with --apply to remove listed targets."
  exit 0
fi

echo
echo "[cleanup] applying cleanup..."
for path in "${targets[@]}"; do
  if [[ -e "$path" ]]; then
    rm -rf "$path"
    echo "[cleanup] removed $path"
  fi
done

for path in "${ds_store_files[@]}"; do
  path="${path#./}"
  if [[ -e "$path" ]]; then
    rm -f "$path"
    echo "[cleanup] removed $path"
  fi
done

echo
echo "[cleanup] remaining top-level size:"
du -h -d 1 .
echo "[cleanup] done."
