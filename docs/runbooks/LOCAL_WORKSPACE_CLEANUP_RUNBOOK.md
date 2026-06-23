# Local Workspace Cleanup Runbook

## Purpose

Use this runbook when the local `makeupAR` workspace is low on disk space or before sharing the repo with teammates.

Default working policy: use the `balanced` cleanup profile. It removes large reproducible generated artifacts and preserves durable evidence plus speed-critical dependency caches.

Sharing policy: use the `share` cleanup profile after verification. It preserves curated evidence and removes raw/generated evidence, generated build products, dependency installs, and editor caches so the directory is source-first and small.

Video policy: do not save screen recordings by default. Record only when motion, elapsed time, or a continuous scenario is core evidence. If a raw recording is captured, extract metadata, representative frames, or a contact sheet and delete the raw recording when it is no longer needed.

## When To Run

Run balanced cleanup when:

- `du -h -d 1 .` shows the workspace is dominated by generated artifacts.
- `evidence/derived-data/` contains old Xcode derived-data snapshots from previous UnityFramework builds.
- `unity-builds/` or `rn/MakeupARValidation/unity/` exists from a previous build and the next session can regenerate UnityFramework.

Do not run cleanup in the middle of an active Unity/RN build.

## Command

Preview first:

```bash
bash scripts/cleanup_local_generated.sh --profile balanced --dry-run
```

Apply only after reviewing the dry-run output:

```bash
bash scripts/cleanup_local_generated.sh --profile balanced --apply
```

Before sharing the directory:

```bash
bash scripts/cleanup_local_generated.sh --profile share --dry-run
bash scripts/cleanup_local_generated.sh --profile share --apply
```

## Balanced Cleanup Removes

- `evidence/derived-data/`
- `unity-builds/`
- `rn/MakeupARValidation/unity/`
- `rn/MakeupARValidation/ios/build/`
- repository-local `.DS_Store` files

The script refuses to remove a target if Git reports it as tracked or not ignored.

## Balanced Cleanup Preserves

- `evidence/logs/`
- `evidence/screenshots/`
- `evidence/screen-recordings/`
- `rn/MakeupARValidation/node_modules/`
- `rn/MakeupARValidation/ios/Pods/`
- `unity/MakeupARUnityValidation/Library/`

Keep these by default because they either contain milestone evidence or avoid expensive reinstall/reimport work. `balanced` cleanup does not delete screen recordings automatically; review raw recordings manually after durable metadata/contact sheets/representative frames exist.

## Share Cleanup Removes

- `evidence/derived-data/`
- `evidence/logs/`
- `evidence/recovered/`
- `evidence/screen-recordings/`
- `unity-builds/`
- `rn/MakeupARValidation/unity/`
- `rn/MakeupARValidation/ios/build/`
- `rn/MakeupARValidation/ios/Pods/`
- `rn/MakeupARValidation/ios/MakeupARValidation.xcworkspace/`
- `rn/MakeupARValidation/ios/.xcode.env.local`
- `rn/MakeupARValidation/node_modules/`
- `rn/MakeupARValidation/vendor/`
- `rn/MakeupARValidation/android/`
- `unity/MakeupARUnityValidation/Library/`
- `unity/MakeupARUnityValidation/Logs/`
- `unity/MakeupARUnityValidation/UserSettings/`
- repository-local `.DS_Store` files

Use `share` only after raw evidence has been absorbed into `TECH_VALIDATION_RESULT.md`, curated `evidence/evolution/`, or another team-readable doc. It intentionally makes the next run slower because teammates must reinstall dependencies, reimport Unity packages, and regenerate UnityFramework.

## Share Cleanup Preserves

- `evidence/README.md`
- `evidence/evolution/`
- selected canonical `evidence/screenshots/`
- `evidence/references/`
- `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/`

Curated evidence should remain small and representative. Do not keep raw frame batches, duplicate recovered attachment folders, or raw recordings in the shareable set.

## Optional Manual Video Pruning

Before deleting a raw recording, confirm that `TECH_VALIDATION_RESULT.md` points to durable replacement evidence such as:

- runtime log or summary metadata under `evidence/logs/`
- representative frame under `evidence/screenshots/`
- contact sheet under `evidence/screenshots/`

Do not delete a raw recording if a current milestone explicitly requires the original video to remain as decision evidence.

## After Cleanup

The next real-device Unity/RN validation session must regenerate UnityFramework before building the RN iOS app:

```bash
bash scripts/build_m3_unityframework.sh
```

Then run the RN iOS app from `rn/MakeupARValidation` according to `AGENTS.md`.

## Reinstall Cost After Share Cleanup

After `share`, the next session must afford:

- npm install time
- CocoaPods install time
- Unity asset/package reimport time
- reapplying or making durable any package-local bridge caveat such as `RNUnityView.mm`
