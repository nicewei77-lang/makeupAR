# Eyebrow Makeup Completion Audit

Status: Follow-up brow QA tuning implemented locally; rebuild pending
Date: 2026-06-27

This audit checks the current eyebrow makeup feature against the original module
request. It is intentionally stricter than the local test suite: a requirement
is marked complete only when current evidence proves it, not when the code looks
plausible.

## Evidence Sources

- Product spec: `docs/product/eyebrow-makeup-feature.md`
- Architecture design: `docs/architecture/eyebrow-ar-rendering-design.md`
- Development log: `docs/roadmaps/active/eyebrow-makeup-development-log.md`
- QA runbook: `docs/runbooks/eyebrow-makeup-qa-runbook.md`
- RN app contract: `rn/MakeupARValidation/App.tsx`
- RN focused tests: `rn/MakeupARValidation/__tests__/App.test.tsx`
- Unity bridge: `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- Unity renderer: `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
- Renderer routes:
  `unity/MakeupARUnityValidation/Assets/Scripts/MakeupRegionRendererRoutes.cs`
- Brow mask assets:
  `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/brow-soft-arch-fine-hair-v1.png`,
  `brow-back-arch-soft-mix-v1.png`, `brow-slim-tail-fine-hair-v1.png`, and
  legacy `brow-drawn-mask-v1.png`

## Current Verification Snapshot

Fresh local checks recorded on 2026-06-27:

| Check | Status |
| --- | --- |
| `python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py` | Passed |
| `python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py` | Passed for the new default `brow-back-arch-soft-mix-v1` |
| `python3 scripts/e7_reference_atlas/verify_region_renderer_routes.py` | Passed |
| `python3 scripts/e7_reference_atlas/verify_unityframework_build_contract.py` | Passed |
| `npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand` | Passed, 26 tests |
| `npm run lint` | Passed |
| `npx tsc --noEmit` | Passed |
| Unity `6000.3.18f1` batchmode import/compile | Latest follow-up attempts failed before compile from Licensing Client IPC timeout; prior successful compile remains `evidence/logs/eyebrow-prebuild-refresh-unity-batchmode-20260627.log` |
| `scripts/build_m3_unityframework.sh` | Passed for latest tuning, `TIMESTAMP=eyebrow-rebuild-20260627-ufw-r1` |
| RN/Xcode real-device Debug build | First attempt failed from stale ignored CocoaPods VFS paths; passed on retry after `pod install --no-repo-update`, `evidence/logs/eyebrow-rn-xcodebuild-device-rebuild-20260627-r2.log` |
| `devicectl` install | Passed for `com.celeste.makeupar.validation` on retry, `evidence/logs/eyebrow-rn-devicectl-install-rebuild-20260627-r2.log` |
| `devicectl` launch | Passed, `evidence/logs/eyebrow-rn-devicectl-launch-rebuild-20260627.log` |

Post-QA tuning notes:

- User visual QA confirmed brow tracking, head-turn attachment, expression
  attachment, `natural_brow`, `soft_brow`, opacity, and intensity controls.
- User visual QA rejected the installed mask shape as `^ ^`, with each brow's
  center too high, the stroke far too thick, and the effect sticker-like.
- The local mask has since been tuned to `5845` active pixels,
  `0.022297` coverage, bbox height `31`, and center rise about `4.4px`.
- User chose to skip applying that intermediate tuning build and proceed into
  the next local loop.
- The current local mask now adds procedural hair/powder density variation with
  `5123` active pixels, `0.019543` coverage, bbox height `29`, center rise
  about `4.3px`, and texture peak range `51/43`.
- The prior local option build defaulted to `brow-soft-arch-fine-hair-v1` and
  exposed `brow-back-arch-soft-mix-v1` and `brow-slim-tail-fine-hair-v1` for QA
  comparison.
- The three-option iPhone build was installed and launched. User QA confirmed
  attachment under head turns and expression changes, but the brow was too
  faint, especially `soft_brow`; the selected masks were too centered and
  slightly below the real brow line; brow color controls still showed lip
  colors.
- Local post-QA tuning raised `natural_brow` to opacity/intensity/coverage
  `0.68/0.68/0.62`, adds brow-specific colors, and shifts the three selected
  mask PNGs 10px outward and 7px upward. That tuning has now been
  regenerated into UnityFramework, rebuilt into the RN app, installed, and
  launched on the iPhone.
- Local color-parameter tuning adds brow `Warmth` and `Depth` controls that
  compute the final RN hex color before sending Unity's existing `color` field.
  This color tuning is included in the latest installed rebuild.
- Local placement-parameter tuning adds brow `Brow Spread` and `Brow Y`
  controls that send `maskSpreadX` and `maskOffsetY` through RNBridge into the
  Unity smooth-mask shader. `Brow Spread` adjusts the two brows symmetrically
  outward/inward from center; this placement tuning is included in the latest
  installed rebuild.
- User approved using the current post-QA tuning as the next iPhone rebuild
  candidate, and that rebuild has been installed and launched. User visual QA on
  the rebuilt app found `spread=`/`y=` visible and adjustable, but the renderer
  id was hard to find, the brow remained too centered and too faint, and the
  upward angle still read as angry.
- Local follow-up tuning now defaults to `brow-back-arch-soft-mix-v1`
  (`Soft flat`), removes high-arch/legacy masks from the user-facing picker,
  raises `natural_brow` opacity/intensity to `0.75/0.75`, starts
  `maskSpreadX` at `0.20`, widens spread clamp to `±0.34`, labels the visible
  color sliders as `Temperature` and `Depth`, strengthens Unity brow alpha
  response, and shows `Renderer ...` as its own compact HUD row. This follow-up
  tuning is not rebuilt or installed yet.

Build notes:

- First UnityFramework export attempt failed from disk exhaustion; generated
  caches were cleaned after user approval.
- Second UnityFramework attempt failed at link with missing Swift compatibility
  libraries from Unity ARKit static libs.
- The Unity iOS postprocess now adds the Xcode iPhoneOS Swift library path and
  Swift compatibility link flags. The build script now detects Unity export
  failure strings even when Unity exits `0`.
- The latest UnityFramework artifact verification recorded a `119M`
  `UnityFramework.framework` and `23M` `Data` folder in both RN and
  package-local framework paths.
- The first latest-tuning RN/Xcode build failed with a stale absolute
  CocoaPods VFS path:
  `/Users/hi/Library/CloudStorage/Dropbox/Mac/Desktop 2/Jungle/makeupAR/.../React-VFS.yaml`.
  Running `pod install --no-repo-update` refreshed ignored local Pod support
  files under the current checkout, then the RN/Xcode rebuild passed.
- The successful rebuilt RN app bundle is signed with TeamIdentifier
  `X5C5U3T6B4`, is `198M`, includes `119M` `UnityFramework.framework` with
  `23M` `Data`, and was installed and launched as
  `com.celeste.makeupar.validation`.

## Requirement Audit

| Requirement | Current Evidence | Status |
| --- | --- | --- |
| Implement only the eyebrow makeup module inside the existing app | Product docs keep camera/photo/video/backend/AI/Android/payment out of scope; code changes are limited to RN recipe/UI, Unity bridge/rendering, mask asset, verifiers, and docs | Satisfied for current loop |
| Unity / AR Foundation / ARKit based eyebrow rendering | Brow is accepted by `RNBridge`, routed by `MakeupRegionRendererRoutes`, rendered by `E3RegionMaskOverlay`, packaged into `UnityFramework.framework`, installed, and launched on `CloudsiPhone (26.5)` | Build/install proven; visual QA pending |
| React Native minimal UI, events, presets | RN focused tests cover brow as fourth region, brow HUD controls, and four-layer recipe dispatch | Locally verified |
| Natural brow presets | `natural_brow`, `soft_brow`, the two user-facing brow mask options, brow-specific colors/material cases, and brow-specific mask threshold/feather are covered by static verifiers; the latest local defaults are raised to `0.75/0.75` | Locally retuned; device rebuild pending |
| Stable renderer structure that will not block later lip/cheek/eye/brow splits | `MakeupRegionRendererRoutes` exposes per-region renderer ids while preserving `region` as the RN contract | Locally verified |
| In-house, shipping-safe brow mask asset | Current selected candidates come from the locally generated procedural variation sheet; docs record no third-party asset or unclear license path | Locally verified |
| Brow placement avoids obvious eye/cheek/lip mask overlap | Mask verifier checks active pixels, bbox, two components, tightened top-edge arch height, and overlap thresholds; RN/Unity now expose a wider `Brow Spread` range and default outward spread | Locally retuned; device rebuild pending |
| Color, opacity, intensity, feather, coverage, material response | RN payload and Unity renderer parse/apply these fields; focused Jest covers brow-specific colors, `Temperature`/`Depth` color parameters, `Brow Spread`/`Brow Y` placement tuning, and the static contract verifiers cover the Unity acceptance path | Locally verified; visual quality pending |
| Face-attached motion under head turns | User reported the brow follows well during left/right head turns and expression changes on the installed build | Visually proven for attachment |
| Natural appearance under lighting and expression change | User reported earlier builds were too arched, too thick, sticker-like, too faint, too centered, slightly low, and then still too upward/angry; the local follow-up tuning switches to the flatter mask and stronger alpha response | Needs rebuild and user re-QA |
| Tracking loss and low-FPS behavior does not leave stale brow artifacts | Existing renderer has tracking fade/hide behavior, but brow-specific real-device behavior has not been observed | Not visually proven |
| Left/right asymmetry correction is possible | The current first loop supports symmetric procedural brow masks and shared tuning; explicit left/right asymmetry controls are not implemented | Incomplete |
| Existing lip/cheek/eye behavior is not regressed | RN tests, static route checks, Unity compile, UnityFramework build, RN build, install, and launch passed; no manual region smoke observation yet | Partially proven |
| Product/technical/development/QA docs updated | Product, architecture, development log, QA runbook, and this audit are present and updated for the latest rebuild evidence | Satisfied for current loop |
| Meaningful checkpoint commits and push | Branch `feature/brow-0626` has pushed implementation and pre-build verification checkpoints; the latest rebuild evidence is pending checkpoint commit | In progress |
| Real-device iPhone build and user quality feedback | Build, install, and launch passed on `CloudsiPhone (26.5)`; user feedback from that build drove a local follow-up tuning pass that has not been rebuilt yet | Feedback collected; rebuild pending |

## Remaining QA Items

The latest build approval gate has been executed for the prior build. Remaining
work is to rebuild and visually QA the follow-up local tuning:

1. On the iPhone, open the AR screen and select `brow`.
2. Confirm the compact HUD eventually reports
   `Renderer brow-smooth-region-mask-renderer` after Unity applies the recipe.
3. Confirm the tuned brow is more visible, no longer appears too centered or
   below the real brow line, no longer reads as a thick sticker, and does not
   appear too sharply upward/angry.
4. Compare `Soft flat` (`brow-back-arch-soft-mix-v1`) and `Slim tail fine`
   (`brow-slim-tail-fine-hair-v1`) on device and choose the best default.
5. Collect user visual observations for frontal neutral, left/right head turns,
   expression change, color/Ash-Warm/Light-Dark/Brow Spread/Brow Y/intensity update,
   tracking recovery, and existing
   lip/cheek/eye smoke behavior using the observation template in
   `docs/runbooks/eyebrow-makeup-qa-runbook.md`.
6. Decide whether explicit left/right asymmetry correction is required before
   calling the eyebrow module complete.

## Current Conclusion

The current codebase has a locally verified follow-up tuning pass for the
first-loop eyebrow makeup module. Earlier iPhone QA confirmed
attachment/control behavior and exposed the remaining product-quality issues:
too faint, too centered, and too upward/angry. The local branch now includes a
flatter default mask, stronger alpha response, clearer color labels, wider
spread control, and explicit compact HUD renderer display. The full objective
is not complete because this follow-up tuning still needs a real-device rebuild
and user QA. Completion still needs:

- UnityFramework/RN device rebuild with the follow-up brow tuning.
- User visual QA confirming product-quality visibility, placement, shape, and
  thickness on the rebuilt iPhone app.
- A decision on whether explicit left/right asymmetry correction must be added
  before calling the eyebrow module complete.
