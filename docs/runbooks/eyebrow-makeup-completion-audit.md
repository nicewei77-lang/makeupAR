# Eyebrow Makeup Completion Audit

Status: Flat-fill/soft-brow local retune verified; iPhone rebuild pending
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
  PNG-derived `brow-png-dailyflat-hair-v1.png`,
  `brow-png-dailyflat-sharp-v1.png`, and
  `brow-png-dailyflat-multiply-v1.png`, plus legacy `brow-drawn-mask-v1.png`

## Current Verification Snapshot

Fresh local checks recorded on 2026-06-27:

| Check | Status |
| --- | --- |
| `python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py` | Passed |
| `python3 scripts/e7_reference_atlas/verify_brow_png_hair_textures.py` | Passed for filled daily-flat and existing PNG hair candidates |
| `python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py` | Passed for compatibility procedural mask `brow-back-arch-soft-mix-v1` |
| `python3 scripts/e7_reference_atlas/verify_region_renderer_routes.py` | Passed |
| `python3 scripts/e7_reference_atlas/verify_unityframework_build_contract.py` | Passed |
| `npm test -- --runInBand` | Passed, 30 tests |
| `npm run lint` | Passed |
| `npx tsc --noEmit` | Passed |
| Unity `6000.3.18f1` batchmode import/compile | Passed for the flat-fill/soft-brow local retune with `Tundra build success`, `evidence/logs/eyebrow-flat-fill-softbrow-unity6000-batchmode-20260627.log` |
| `scripts/build_m3_unityframework.sh` | Passed for daily-flat with `TIMESTAMP=eyebrow-dailyflat-20260627-ufw-r1`, artifact log `evidence/logs/m3-repro-artifact-verification-eyebrow-dailyflat-20260627-ufw-r1.log` |
| RN/Xcode real-device Debug build | Passed, `evidence/logs/eyebrow-rn-xcodebuild-device-dailyflat-20260627-r1.log` |
| `devicectl` install | Passed for `com.celeste.makeupar.validation`, `evidence/logs/eyebrow-rn-devicectl-install-dailyflat-20260627-r1.log` |
| `devicectl` launch | Passed, `evidence/logs/eyebrow-rn-devicectl-launch-dailyflat-20260627-r1.log` |
| Flat-fill/soft-brow iPhone rebuild/install | Not run yet; requires explicit user build approval |

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
  tuning is included in the latest installed iPhone build.
- Local bright-brow tuning now emits `blendMode="normal"` for `light_brown`
  with PNG-derived brow hair masks while keeping `detailAmount` active; darker
  PNG brow colors remain on `multiply`. This is included in the latest
  installed iPhone build.
- Local daily-flat tuning now uses user-authored `brow_dailyflat.png` to create
  `Daily flat`, `Flat sharp`, and `Flat multiply`. `Flat sharp` is the local
  default, `Texture Detail` starts at `0.68`, the shader strengthens thin
  extracted hair detail, and `Flat multiply` forces multiply composition as an
  A/B probe. This daily-flat loop has now been rebuilt into UnityFramework,
  installed, and launched on `CloudsiPhone (26.5)`.
- User QA on the installed daily-flat build found the flat candidates hollow in
  the center, the visible hair candidates still paint-like, the preset switch
  resetting the selected mask, a too-narrow brow gap, and `soft_brow` not
  visibly appearing. The local follow-up fills the flat alpha silhouette,
  widens the flat targets and default `maskSpreadX` to `0.24`, preserves mask
  selection while switching `natural_brow`/`soft_brow`, and raises `soft_brow`
  visibility. This follow-up has passed local verification but is not installed
  on the iPhone yet.

Build notes:

- First UnityFramework export attempt failed from disk exhaustion; generated
  caches were cleaned after user approval.
- Second UnityFramework attempt failed at link with missing Swift compatibility
  libraries from Unity ARKit static libs.
- The Unity iOS postprocess now adds the Xcode iPhoneOS Swift library path and
  Swift compatibility link flags. The build script now detects Unity export
  failure strings even when Unity exits `0`.
- The latest UnityFramework artifact verification recorded a `126M`
  `UnityFramework.framework` and `30M` `Data` folder in both RN and
  package-local framework paths for
  `TIMESTAMP=eyebrow-dailyflat-20260627-ufw-r1`.
- The first latest PNG/bright RN/Xcode build failed with a stale absolute
  CocoaPods Hermes path:
  `/Users/hi/Library/CloudStorage/Dropbox/Mac/Desktop 2/Jungle/makeupAR/.../node_modules/hermes-compiler/.../hermesc`.
  Correcting only generated/ignored local Pod support paths under the current
  checkout allowed the RN/Xcode rebuild to pass.
- The successful rebuilt RN app bundle is signed with TeamIdentifier
  `X5C5U3T6B4`, is `205M`, includes `126M` `UnityFramework.framework` with
  `30M` `Data`, and was installed and launched as
  `com.celeste.makeupar.validation`.

## Requirement Audit

| Requirement | Current Evidence | Status |
| --- | --- | --- |
| Implement only the eyebrow makeup module inside the existing app | Product docs keep camera/photo/video/backend/AI/Android/payment out of scope; code changes are limited to RN recipe/UI, Unity bridge/rendering, mask asset, verifiers, and docs | Satisfied for current loop |
| Unity / AR Foundation / ARKit based eyebrow rendering | Brow is accepted by `RNBridge`, routed by `MakeupRegionRendererRoutes`, rendered by `E3RegionMaskOverlay`, packaged into `UnityFramework.framework`, installed, and launched on `CloudsiPhone (26.5)` with the daily-flat A/B build. The newer flat-fill/soft-brow retune has only local Unity batchmode verification so far | Previous build/install proven; retune rebuild pending |
| React Native minimal UI, events, presets | RN focused tests cover brow as fourth region, brow HUD controls, and four-layer recipe dispatch | Locally verified |
| Natural brow presets | `natural_brow`, `soft_brow`, the user-facing brow mask options, daily-flat PNG candidates, brow-specific colors/material cases, and brow-specific mask threshold/feather are covered by static verifiers; local tests now guard that switching presets preserves the selected brow mask | Locally verified; retune visual QA pending |
| Stable renderer structure that will not block later lip/cheek/eye/brow splits | `MakeupRegionRendererRoutes` exposes per-region renderer ids while preserving `region` as the RN contract | Locally verified |
| In-house, shipping-safe brow mask asset | Current selected candidates come from the locally generated procedural variation sheet; docs record no third-party asset or unclear license path | Locally verified |
| Brow placement avoids obvious eye/cheek/lip mask overlap | PNG verifier checks active pixels, bbox, two components, daily-flat thinness, detail channel variance, low-alpha stray artifact rejection, non-hollow daily-flat fill, and a minimum daily-flat center gap. RN/Unity still expose `Brow Spread` and `Brow Y` | Locally verified; retune visual QA pending |
| Color, opacity, intensity, feather, coverage, material response | RN payload and Unity renderer parse/apply these fields; focused Jest covers brow-specific colors, `Temperature`/`Depth`, bright PNG normal composition, darker PNG multiply composition, explicit `Flat multiply`, `Texture Detail`, `Brow Spread`/`Brow Y`, and static contract verifiers cover the Unity acceptance path | Locally verified; visual quality pending |
| Face-attached motion under head turns | User reported the brow follows well during left/right head turns and expression changes on the installed build | Visually proven for attachment |
| Natural appearance under lighting and expression change | User reported earlier builds were too arched, too thick, sticker-like, too faint, too centered, slightly low, still too upward/angry, then too thick per hair strand, and then hollow on flat candidates. The local retune fills the flat alpha silhouette and widens the brow gap, but real-device appearance is not proven | Needs user re-QA after rebuild |
| Tracking loss and low-FPS behavior does not leave stale brow artifacts | Existing renderer has tracking fade/hide behavior, but brow-specific real-device behavior has not been observed | Not visually proven |
| Left/right asymmetry correction is possible | The current first loop supports symmetric procedural brow masks and shared tuning; explicit left/right asymmetry controls are not implemented | Incomplete |
| Existing lip/cheek/eye behavior is not regressed | RN tests, TypeScript, lint, static route checks, and Unity batchmode compile passed for the flat-fill/soft-brow local retune; no manual region smoke observation has been done for the retune build | Partially proven |
| Product/technical/development/QA docs updated | Product, architecture, development log, QA runbook, and this audit are present and updated for the latest rebuild evidence | Satisfied for current loop |
| Meaningful checkpoint commits and push | Branch `feature/brow-0626` has pushed implementation checkpoints; latest install evidence is being recorded as a follow-up checkpoint | In progress |
| Real-device iPhone build and user quality feedback | Daily-flat A/B brow build installed and launched on `CloudsiPhone (26.5)`; user feedback on that build produced the current flat-fill/soft-brow local retune | Retune build pending |

## Remaining QA Items

The installed iPhone build is still the older daily-flat A/B build. The newer
flat-fill/soft-brow retune needs an approved iPhone rebuild before visual QA.
After that rebuild, visually QA this candidate:

1. On the iPhone, open the AR screen and select `brow`.
2. Confirm the compact HUD eventually reports
   `Renderer brow-smooth-region-mask-renderer` after Unity applies the recipe.
3. Confirm the tuned brow is more visible, no longer appears too centered or
   below the real brow line, no longer reads as a thick sticker, and does not
   appear too sharply upward/angry.
4. Compare `Flat sharp`, `Flat multiply`, `Daily flat`, and the previous
   `Soft flat` candidate on device and choose the best default.
5. Collect user visual observations for frontal neutral, left/right head turns,
   expression change, color/Temperature/Depth/Brow Spread/Brow Y/intensity update,
   tracking recovery, and existing
   lip/cheek/eye smoke behavior using the observation template in
   `docs/runbooks/eyebrow-makeup-qa-runbook.md`.
6. Decide whether explicit left/right asymmetry correction is required before
   calling the eyebrow module complete.

## Current Conclusion

The current codebase has an installed daily-flat PNG A/B pass plus a newer
local flat-fill/soft-brow retune for the first-loop eyebrow makeup module.
Earlier iPhone QA confirmed attachment/control behavior and exposed the
remaining product-quality issues: too faint, too centered, too upward/angry,
too thick or paint-like per hair strand, hollow flat candidates, too-narrow brow
gap, preset reset, and invisible `soft_brow`. The local retune addresses the
hollow fill, default gap, preset reset, and `soft_brow` visibility in code and
static/local Unity checks. The full objective is not complete because this
retune still needs an approved iPhone rebuild and user visual QA.
Completion still needs:

- User visual QA confirming product-quality visibility, placement, shape,
  per-hair thickness, and texture fidelity on the rebuilt iPhone app.
- A decision on whether explicit left/right asymmetry correction must be added
  before calling the eyebrow module complete.
