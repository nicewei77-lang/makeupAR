# Eyebrow Makeup QA Runbook

Status: Ready for approved device build
Date: 2026-06-27

## Scope

Use this runbook after the user approves a real-device Unity/RN build for the
first eyebrow makeup loop. This checks only the local AR eyebrow feature inside
the existing app.

Out of scope:

- Android.
- AI/model inference, recommendation, backend upload, or raw-frame storage.
- Payment, ads, commercial SDKs, App Store claims, or production readiness.

## Pre-Build Checks

Run from the repo root before requesting or starting the device build:

```bash
python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py
python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py
python3 scripts/e7_reference_atlas/verify_region_renderer_routes.py
```

RN focused check:

```bash
npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand
```

Run the RN command from `rn/MakeupARValidation`.

Unity local import/compile check:

Confirm there is enough local disk space first. The latest local check showed
less than `400Mi` free on `/System/Volumes/Data`, which is too tight for a
Unity/RN device build.

```bash
"/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity" \
  -batchmode \
  -quit \
  -projectPath "/Users/hi/Library/CloudStorage/Dropbox/Mac/Desktop/Jungle/makeupAR/unity/MakeupARUnityValidation" \
  -logFile -
```

## Approved Build Path

Only after user approval:

1. Close Unity/Hub and ensure stale Unity/Licensing processes are not blocking
   export.
2. From repo root, run `bash scripts/build_m3_unityframework.sh`.
3. Run the RN/Xcode target with the user-approved iPhone and signing team.
4. Do not add a default UDID or `DEVELOPMENT_TEAM` to the repo.

## Device QA

Start in HUD mode with `lip` active by default, then select `brow`.

Check:

- `brow` can be enabled and disabled independently.
- `natural_brow` appears as the default brow sample.
- `soft_brow` can be selected and updates immediately.
- `brow-drawn-mask-v1` is selected for brow.
- The latest recipe HUD shows `renderer=brow-smooth-region-mask-renderer` for
  brow after Unity acknowledges the recipe.
- Opacity and intensity changes update without restarting AR.
- Brow color changes stay face-attached during small head motion.
- Left and right head turns do not cause the brow to float or detach.
- Raised-brow or mild expression changes do not create severe forehead or eyelid
  bleed.
- Temporary tracking loss fades/hides and recovers without stale brow placement.
- Existing lip, cheek, and eye controls still toggle and render.

## Acceptance Notes

Mark the loop accepted only if the user confirms:

- Placement is close enough for a first product slice.
- The effect reads as soft brow makeup rather than a hard sticker.
- Existing lip/cheek/eye behavior did not regress in the smoke test.

If placement is off, record whether the problem is:

- Too high or low.
- Too close to the nose or too wide.
- Too thick or too thin.
- Tail angle wrong.
- Both brows equally wrong or asymmetric.

Do not store raw face frames by default. If screenshots or recordings are needed
as evidence, get explicit user approval first and store only curated artifacts
under `evidence/`.
