# E7 Full-Face Region Generate Pre-Xcode Gate

Session: `session-20260626T195853Z`
Date: 2026-06-27 KST
Status: `pre-xcode-ready`

## Region Status

| Region | Status | Selected candidate | Runtime texture |
| --- | --- | --- | --- |
| lip | `pre-xcode-ready` | `lip-balanced-gold-v0` | `e7-lip-balanced-uv-v0` |
| blush | `pre-xcode-ready` | `blush-balanced-soft-oval-v0` | `e7-blush-balanced-uv-v0` |
| brow | `pre-xcode-ready` | `brow-balanced-stroke-envelope-v0` | `e7-brow-balanced-uv-v0` |
| eyeliner | `pre-xcode-ready` | `eyeliner-minimal-safe-lashline-v0` | `e7-eyeliner-minimal-safe-uv-v0` |

## Completed

- CLI/local experiment generated candidates, scorecards, selected policies, adjustment axes, UV masks, contact sheets, and composite package for all four regions.
- Web review shell supports region review, adjustment controls, contact-sheet preview, and saved package draft payload.
- RN has a full-face package button that posts a four-layer v2 recipe for `lip,blush,brow,eyeliner`.
- Unity Resources contain the selected UV masks and a runtime asset registry.
- Unity RNBridge and `E3RegionMaskOverlay` accept the four product regions and their stable `e7-*` mask texture IDs.
- Editor smoke code exists for a future Unity batchmode parse/dispatch check.

## Verification

- `python3 -m py_compile scripts/e7_region_generate/build_region_candidates.py`
- `python3 -m py_compile scripts/e7_region_generate/install_full_face_region_runtime_assets.py`
- `python3 scripts/e7_region_generate/install_full_face_region_runtime_assets.py`
- `python3 -m json.tool unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/e7-full-face-region-runtime-assets.json`
- `npx tsc --noEmit` in `rn/MakeupARValidation`
- `npm run lint`, `npm run typecheck`, and `npm run build` in `web/lip-generate-beta`
- `git diff --check` and `git diff --cached --check`
- Unity batchmode `E7FullFaceRegionPackageSmoke.RunFromCommandLine`: passed after closing the stale project-locking Unity processes

## Blocked / Deferred

- Xcode/iPhone build, install, launch, camera permission, and runtime visual evidence were intentionally not run in this phone-disconnected session.
- No region can be promoted to Green/product-quality-ready without real-device face attachment, motion/expression, blink/yaw, FPS/frame-time, latency, memory, thermal, and human visual acceptance evidence.

## Next Phone-Connected Gate

1. Run UnityFramework export/sync only after build approval.
2. Run RN iPhone build/install/launch only after build approval.
3. Capture representative visual evidence for neutral, smile, open/close mouth, yaw, and blink/eyeliner stability.
4. Record runtime logs and update `TECH_VALIDATION_RESULT.md` with Green/Yellow/Red decisions per region.
