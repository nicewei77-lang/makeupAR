# Eyebrow Makeup QA Runbook

Status: First iPhone QA tuning in progress; rebuild pending
Date: 2026-06-27

## Scope

Use this runbook for the first eyebrow makeup device QA loop. This checks only
the local AR eyebrow feature inside the existing app.

Completion evidence is tracked separately in
`docs/runbooks/eyebrow-makeup-completion-audit.md`.

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

Confirm there is enough local disk space first. The 2026-06-27 build needed
generated-cache cleanup before it could complete.

Observed generated cleanup candidates, if the user approves cleanup:

- `unity-builds`: about `3.1G`
- `unity/MakeupARUnityValidation/Library`: about `793M`; deleting it will force
  Unity to reimport the project.

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

## 2026-06-27 Build Evidence

- Device: `CloudsiPhone (26.5)`.
- Bundle id: `com.celeste.makeupar.validation`.
- Signing team: `X5C5U3T6B4`.
- UnityFramework regenerated and synced:
  `TIMESTAMP=eyebrow-20260627-ufw-r3`.
- UnityFramework log:
  `evidence/logs/m3-repro-xcodebuild-unityframework-eyebrow-20260627-ufw-r3.log`.
- RN/Xcode device build:
  `evidence/logs/eyebrow-rn-xcodebuild-device-20260627.log`, `** BUILD SUCCEEDED **`.
- Install:
  `evidence/logs/eyebrow-rn-devicectl-install-20260627.log`, installed app
  `com.celeste.makeupar.validation`.
- Launch:
  `evidence/logs/eyebrow-rn-devicectl-launch-20260627.log`, launched
  application with the bundle identifier.
- App bundle check: local build product includes `UnityFramework.framework/Data`,
  `RNBridge`, `MakeupRegionRendererRoutes`, Unity resource
  `brow-drawn-mask-v1`, and RN bundle strings `natural_brow`, `soft_brow`,
  `brow-drawn-mask-v1`, `rendererId`.

No face screenshots, recordings, or raw frames were captured by default.

## Device QA

Start in HUD mode with `lip` active by default, then select `brow`.

First QA result on the installed `eyebrow-20260627-ufw-r3` build:

- Passed: `natural_brow`, `soft_brow`, opacity, and intensity controls respond.
- Passed: brow attachment stays stable during left/right head turns and
  expression changes.
- Needs tuning: brow placement is near the eyebrow line, but the shape reads as
  `^ ^`; the center of each brow is the highest point; the stroke is far too
  thick and sticker-like.
- Local tuning has been made, but a new UnityFramework/RN device build is
  required before the following checks can accept the visual result.
- User then chose to skip applying the intermediate tuning build and continue
  into the next local loop. The current local mask also includes subtle
  procedural hair/powder density variation; it is not installed on the iPhone
  yet.
- The latest local loop adds three selectable mask candidates from the generated
  variation sheet: `brow-soft-arch-fine-hair-v1` as default,
  `brow-back-arch-soft-mix-v1`, and `brow-slim-tail-fine-hair-v1`. These are
  not installed on the iPhone yet.

Check:

- `brow` can be enabled and disabled independently.
- `natural_brow` appears as the default brow sample.
- `soft_brow` can be selected and updates immediately.
- `brow-soft-arch-fine-hair-v1` is selected for brow by default.
- `brow-back-arch-soft-mix-v1` and `brow-slim-tail-fine-hair-v1` can be selected
  for visual comparison.
- The latest recipe HUD shows `renderer=brow-smooth-region-mask-renderer` for
  brow after Unity acknowledges the recipe.
- Opacity and intensity changes update without restarting AR.
- Brow color changes stay face-attached during small head motion.
- Left and right head turns do not cause the brow to float or detach.
- Raised-brow or mild expression changes do not create severe forehead or eyelid
  bleed.
- Temporary tracking loss fades/hides and recovers without stale brow placement.
- Existing lip, cheek, and eye controls still toggle and render.
- The tuned shape does not read as `^ ^`.
- The center of each brow is not the obvious highest point.
- The brow stroke is thin enough to read as makeup, not a sticker.
- The brow fill has subtle density variation and does not read as one uniform
  grey strip.

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

## User Observation Template

Use this template after an approved device build. Do not store screenshots or
recordings unless the user explicitly approves storing them.

Build context:

- Branch/commit: `feature/brow-0626`
- Device: `CloudsiPhone`
- iOS version: `26.5`
- Signing team used: `X5C5U3T6B4`
- UnityFramework regenerated with `scripts/build_m3_unityframework.sh`: yes,
  `TIMESTAMP=eyebrow-20260627-ufw-r3`
- Unity batchmode compile after latest brow C# change: pass,
  `evidence/logs/eyebrow-unity-batchmode-20260627.log`

Minimum observations:

| Scenario | Question | User observation | Pass / Needs tuning |
| --- | --- | --- | --- |
| Frontal neutral | Are both brows close to the natural brow line, without forehead or eyelid bleed? | Near eyebrow line, but `^ ^`; center too high; far too thick and sticker-like on the installed build | Needs tuning |
| Left head turn | Does the near/far brow stay attached, or does either side float? | Tracks well on the installed build | Pass |
| Right head turn | Does the near/far brow stay attached, or does either side float? | Tracks well on the installed build | Pass |
| Raised brow / mild expression | Does the effect avoid severe eyelid/forehead bleed? | Stays attached on the installed build | Pass for attachment; shape needs tuning |
| `natural_brow` preset | Does it read as soft makeup rather than a sticker? | Control works, but visual is too thick/sticker-like on the installed build | Needs tuning |
| `soft_brow` preset | Is the lighter preset still visible but natural? | Control works on the installed build | Recheck after tuning |
| Opacity/intensity change | Do changes apply immediately without AR restart? | Works on the installed build | Pass |
| Temporary tracking loss | Does the brow hide/fade and recover without stale placement? |  |  |
| Existing regions smoke test | Do lip, cheek, and eye still toggle/render? |  |  |

Asymmetry decision:

- Are both brows wrong in the same direction, suggesting mask tuning?
- Is only one brow wrong, suggesting left/right asymmetry controls?
- Should explicit left/right offset/scale/angle correction be implemented before
  calling the eyebrow module complete?

Screenshot policy:

- No screenshots requested:
- User approved storing screenshots:
- Screenshot paths under `evidence/screenshots/`:
- Notes if screenshots were viewed but not stored:

Do not store raw face frames by default. If screenshots or recordings are needed
as evidence, get explicit user approval first and store only curated artifacts
under `evidence/`.
