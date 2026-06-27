# Eyebrow Makeup QA Runbook

Status: Flat-fill/soft-brow local retune verified; iPhone rebuild pending
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

Latest pre-build refresh on 2026-06-27 passed with `73Gi` free on
`/System/Volumes/Data`. Unity `6000.3.18f1` batchmode import/compile exited `0`
and logged `Tundra build success` in
`evidence/logs/eyebrow-prebuild-refresh-unity-batchmode-20260627.log`.

Observed generated cleanup candidates, if the user approves cleanup:

- `unity-builds`: about `3.1G`
- `unity/MakeupARUnityValidation/Library`: about `793M`; deleting it will force
  Unity to reimport the project.

```bash
"/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity" \
  -batchmode \
  -quit \
  -projectPath "/Users/hi/dev/Jungle/makeupAR/unity/MakeupARUnityValidation" \
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

## 2026-06-27 Rebuild Evidence

Latest approved post-QA tuning rebuild:

- Device: `CloudsiPhone (26.5)`.
- Bundle id: `com.celeste.makeupar.validation`.
- Signing team: `X5C5U3T6B4`.
- UnityFramework regenerated and synced:
  `TIMESTAMP=eyebrow-rebuild-20260627-ufw-r1`.
- Unity export log:
  `evidence/logs/m3-repro-unity-export-eyebrow-rebuild-20260627-ufw-r1.log`.
- UnityFramework build log:
  `evidence/logs/m3-repro-xcodebuild-unityframework-eyebrow-rebuild-20260627-ufw-r1.log`,
  `** BUILD SUCCEEDED **`.
- UnityFramework artifact verification:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-rebuild-20260627-ufw-r1.log`;
  RN/package frameworks were `119M`, with `23M` `Data` folders.
- RN/Xcode device build attempt 1:
  `evidence/logs/eyebrow-rn-xcodebuild-device-rebuild-20260627.log`,
  failed because ignored CocoaPods files referenced the old Dropbox
  `React-VFS.yaml` path.
- Local Pod support refresh:
  `pod install --no-repo-update` from `rn/MakeupARValidation/ios`.
- RN/Xcode device build attempt 2:
  `evidence/logs/eyebrow-rn-xcodebuild-device-rebuild-20260627-r2.log`,
  `** BUILD SUCCEEDED **`.
- Built app bundle:
  `unity-builds/xcode-derived-data/RNDevice-eyebrow-rebuild-20260627/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
  `198M`, including `119M` `UnityFramework.framework` and `23M`
  `UnityFramework.framework/Data`.
- `devicectl` install by device name first failed with a transient CoreDevice
  connection invalidation; retry by the approved device identifier passed:
  `evidence/logs/eyebrow-rn-devicectl-install-rebuild-20260627-r2.log`.
- `devicectl` launch passed:
  `evidence/logs/eyebrow-rn-devicectl-launch-rebuild-20260627.log`.

No face screenshots, recordings, or raw frames were captured by default.

## 2026-06-27 PNG/Bright Brow Build Evidence

Latest approved build before the next visual QA loop:

- Branch/commit: `feature/brow-0626` / `b875be0`.
- Device: `CloudsiPhone (26.5)`.
- Bundle id: `com.celeste.makeupar.validation`.
- Signing team: `X5C5U3T6B4`.
- UnityFramework regenerated and synced:
  `TIMESTAMP=eyebrow-png-bright-20260627-ufw-r1`.
- UnityFramework artifact verification:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-png-bright-20260627-ufw-r1.log`;
  RN/package frameworks were `123M`, with `27M` `Data` folders.
- Pre-build checks passed: full RN Jest (`28` tests), TypeScript, RN lint,
  brow Unity contract verifier, PNG brow hair verifier, and brow mask verifier.
- RN/Xcode device build attempt 1:
  `evidence/logs/eyebrow-rn-xcodebuild-device-png-bright-20260627.log`,
  failed because ignored CocoaPods support files still pointed
  `HERMES_CLI_PATH` at an old Dropbox checkout.
- Local Pod support patch:
  refreshed only generated/ignored Pod support paths to the current checkout.
- RN/Xcode device build attempt 2:
  `evidence/logs/eyebrow-rn-xcodebuild-device-png-bright-20260627-r2.log`,
  `** BUILD SUCCEEDED **`.
- Built app bundle:
  `unity-builds/xcode-derived-data/RNDevice-eyebrow-png-bright-20260627-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
  `202M`, including `123M` `UnityFramework.framework` and `27M`
  `UnityFramework.framework/Data`.
- Install:
  `evidence/logs/eyebrow-rn-devicectl-install-png-bright-20260627.log`,
  installed `com.celeste.makeupar.validation`.
- Launch:
  `evidence/logs/eyebrow-rn-devicectl-launch-png-bright-20260627.log`,
  launched `com.celeste.makeupar.validation`.

No face screenshots, recordings, or raw frames were captured by default.

## 2026-06-27 Daily Flat PNG A/B Build Evidence

Latest approved build for the next visual QA loop:

- Branch/commit before build: `feature/brow-0626` / `9751510`.
- Device: `CloudsiPhone (26.5)`.
- Bundle id: `com.celeste.makeupar.validation`.
- Signing team: `X5C5U3T6B4`.
- Pre-build checks passed: full RN Jest (`29` tests), TypeScript, RN lint,
  daily-flat PNG brow hair verifier, brow Unity contract verifier, compatibility
  brow mask verifier, region renderer route verifier, and UnityFramework build
  contract verifier.
- UnityFramework regenerated and synced:
  `TIMESTAMP=eyebrow-dailyflat-20260627-ufw-r1`.
- UnityFramework artifact verification:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-dailyflat-20260627-ufw-r1.log`;
  RN/package frameworks were `126M`, with `30M` `Data` folders.
- RN/Xcode device build:
  `evidence/logs/eyebrow-rn-xcodebuild-device-dailyflat-20260627-r1.log`,
  `** BUILD SUCCEEDED **`.
- Built app bundle:
  `unity-builds/xcode-derived-data/RNDevice-eyebrow-dailyflat-20260627-r1/Build/Products/Debug-iphoneos/MakeupARValidation.app`,
  `205M`, including `126M` `UnityFramework.framework` and `30M`
  `UnityFramework.framework/Data`.
- Install:
  `evidence/logs/eyebrow-rn-devicectl-install-dailyflat-20260627-r1.log`,
  installed `com.celeste.makeupar.validation`.
- Launch:
  `evidence/logs/eyebrow-rn-devicectl-launch-dailyflat-20260627-r1.log`,
  launched `com.celeste.makeupar.validation`.

No face screenshots, recordings, or raw frames were captured by default.

## 2026-06-27 Flat-Fill/Soft-Brow Local Retune

This follow-up is not installed on the iPhone yet.

- Triggering QA feedback on the installed daily-flat build:
  - `Daily flat`, `Flat sharp`, and `Flat multiply` showed mostly outlines with
    hollow centers.
  - `Daily hair`, `Natural hair`, and `Narrow hair` were visible but still
    looked paint-like.
  - Switching `natural_brow`/`soft_brow` reset the selected mask to
    `Flat sharp`.
  - The brow gap was too narrow, making the midline look crowded.
  - `soft_brow` appeared invisible.
- Local retune:
  - Filled daily-flat alpha silhouettes while preserving extracted hair detail.
  - Widened the daily-flat targets and raised default `maskSpreadX` to `0.24`.
  - Preserved brow mask/spread/Y/detail settings while switching presets.
  - Raised `soft_brow` intensity/coverage to `0.75/0.62` and Unity
    `soft_brow` alpha response.
- Local verification:
  - Full RN Jest passed with `30` tests.
  - TypeScript, RN lint, PNG hair verifier, brow mask verifier, Unity contract
    verifier, renderer route verifier, and UnityFramework build contract
    verifier passed.
  - Unity `6000.3.18f1` batchmode import/compile passed:
    `evidence/logs/eyebrow-flat-fill-softbrow-unity6000-batchmode-20260627.log`.

An approved UnityFramework/RN iPhone build is required before accepting or
rejecting the visual result.

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
  into the next local loop. At that checkpoint the mask also included subtle
  procedural hair/powder density variation and was still local only.
- A following local loop added three selectable mask candidates from the generated
  variation sheet: `brow-soft-arch-fine-hair-v1` as default,
  `brow-back-arch-soft-mix-v1`, and `brow-slim-tail-fine-hair-v1`.
- The `eyebrow-options-20260627-ufw-r1` iPhone build installed and launched with
  the three options. User QA confirmed head-turn and expression attachment, but
  the brow was too faint, especially `soft_brow`; the masks were too centered
  and slightly below the real brow line; color choices were still lip colors.
- Local post-QA tuning now raises brow visibility, adds brow-specific colors,
  and shifts the three selected masks outward/upward.
- The latest approved rebuild installed and launched this post-QA tuning on
  `CloudsiPhone (26.5)`.
- User QA on that rebuilt app confirmed `spread=` and `y=` are visible and
  adjustable, but `renderer=...` was hard to find because it only appeared in
  the long `recipe_applied` summary. The brow still looked too faint, too
  centered, and too sharply upward/angry.
- Local follow-up tuning now exposes `Renderer ...` as its own compact HUD row,
  defaults to the flatter `Soft flat` mask (`brow-back-arch-soft-mix-v1`),
  removes high-arch/legacy masks from the user-facing picker, starts opacity and
  intensity at `0.75`, starts `Brow Spread` at `0.20`, widens horizontal spread
  to `±0.34`, and strengthens Unity brow alpha response. This follow-up tuning
  is now included in the latest installed PNG/bright brow build.
- The latest installed PNG/bright brow build also includes user-authored PNG
  brow hair candidates (`Daily hair`, `Natural hair`, `Narrow hair`,
  `Light brown`), `Texture Detail`, and the `light_brown` normal-composition
  split for PNG-derived brow hair. User visual QA is pending.
- Local daily-flat follow-up now adds `Daily flat`, `Flat sharp`, and
  `Flat multiply` from the flatter user-authored `brow_dailyflat.png`. `Flat
  sharp` is the new local default, `Texture Detail` starts at `0.68`, and
  `Flat multiply` is an explicit multiply comparison path. This daily-flat loop
  is now installed and launched on `CloudsiPhone (26.5)` for visual QA.
- User QA on the daily-flat install found the flat candidates hollow, the
  visible hair candidates still paint-like, `soft_brow` not visibly appearing,
  preset switching resetting the selected mask, and the two brows too close
  together. Local retune for those issues has passed checks but is not installed
  yet.

## Brow Parameter Tuning Guide

Use `neutral_brown` as the first color for natural dark brows. Start with
opacity `0.75`, intensity `0.75`, coverage `0.62`, feather `0.48`.

For color, keep `neutral_brown` first and use `Temperature` and `Depth` before
switching to a darker swatch. `Temperature` below `0.50` moves the result toward
ash; above `0.50` makes it warmer. `Depth` below `0.50` lightens; above `0.50`
darkens. Good first QA probes are `Temperature 0.40..0.60` and
`Depth 0.55..0.75`.

For placement, the current local retune starts `Brow Spread` outward at `0.24`
internally, which appears around `0.85` on the slider. If the brows still look
too centered, move `Brow Spread` farther right; the new Unity clamp allows up to
`0.34`. If the brows are too wide, move it left. If the brows still sit low,
move `Brow Y` slightly above `0.50`. The compact AR Status HUD should show a
separate `Renderer brow-smooth-region-mask-renderer` line plus `mask=...`,
`spread=`, and `y=` after Unity acknowledges the recipe.

If the brow is too faint, raise opacity first to `0.74..0.80`. If it is still
too faint, raise intensity to `0.74..0.82`. Adjust coverage last, usually no
higher than `0.68`, because too much coverage can make the brow read as a
sticker.

If the brow looks too solid, lower intensity before lowering opacity. If the
edge looks sticker-like, lower coverage slightly (`0.56..0.60`) or raise feather
within the current clamp. Use `dark_brown` or `soft_black` only after opacity and
intensity feel right; otherwise the color change can hide shape problems.

Check:

- `brow` can be enabled and disabled independently.
- `natural_brow` appears as the default brow sample.
- `soft_brow` can be selected and updates immediately.
- Switching `natural_brow`/`soft_brow` does not reset the selected brow mask.
- `soft_brow` remains visible enough to judge color and placement.
- `Soft flat` (`brow-back-arch-soft-mix-v1`) was the previous installed default
  and remains selectable for comparison.
- `Slim tail fine` (`brow-slim-tail-fine-hair-v1`) can be selected for visual
  comparison.
- `Flat sharp` (`brow-png-dailyflat-sharp-v1`) is selected for brow by default
  in the local daily-flat build candidate.
- PNG hair candidates `Daily flat`, `Flat sharp`, `Flat multiply`, `Daily hair`,
  `Natural hair`, `Narrow hair`, and `Light brown` can be selected and compared.
- Compare `Flat sharp` against `Flat multiply` with the same color and
  `Texture Detail` value to judge whether multiply revives texture or makes the
  brow too muddy.
- `Daily flat`, `Flat sharp`, and `Flat multiply` no longer show only an outline
  with a hollow center.
- `Texture Detail` changes the visible PNG hair detail without replacing the
  selected brow color layer.
- `Brow Spread` and `Brow Y` controls can be adjusted while the brow remains
  attached.
- The compact AR Status HUD shows `Renderer brow-smooth-region-mask-renderer`
  plus applied `spread=`/`y=` values after Unity acknowledges the recipe.
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
- The two brows no longer make the midline look too narrow.

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
- Commit: fill after the next approved flat-fill/soft-brow build
- Device: `CloudsiPhone`
- iOS version: `26.5`
- Signing team used: `X5C5U3T6B4`
- UnityFramework regenerated with `scripts/build_m3_unityframework.sh`: fill
  after approved build
- Latest relevant Unity batchmode compile before this rebuild: pass,
  `evidence/logs/eyebrow-flat-fill-softbrow-unity6000-batchmode-20260627.log`
- UnityFramework rebuild/sync: fill after approved build
- RN/Xcode rebuild: fill after approved build
- Install/launch: fill after approved build

Minimum observations:

| Scenario | Question | User observation | Pass / Needs tuning |
| --- | --- | --- | --- |
| Frontal neutral | Are both brows close to the natural brow line, without forehead or eyelid bleed? |  |  |
| Left head turn | Does the near/far brow stay attached, or does either side float? |  |  |
| Right head turn | Does the near/far brow stay attached, or does either side float? |  |  |
| Raised brow / mild expression | Does the effect avoid severe eyelid/forehead bleed? |  |  |
| `natural_brow` preset | Does it read as soft makeup rather than a sticker? |  |  |
| `soft_brow` preset | Is the lighter preset still visible but natural? |  |  |
| Brow mask options | Does `Soft flat` work better than `Slim tail fine` as the default? |  |  |
| `Temperature` / `Depth` | Do color changes apply immediately and stay natural once visibility is readable? |  |  |
| `Brow Spread` / `Brow Y` | Do placement changes apply immediately and improve centering/height? |  |  |
| Opacity/intensity change | Do changes apply immediately without AR restart? |  |  |
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
