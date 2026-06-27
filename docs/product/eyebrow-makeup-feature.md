# Eyebrow Makeup Feature

Status: PNG/bright brow build installed on iPhone; user visual QA pending
Date: 2026-06-27
Related strategy: `docs/product/two-stage-ar-makeup-product-strategy.md`
Related architecture: `docs/architecture/eyebrow-ar-rendering-design.md`

## Goal

Add an eyebrow makeup module inside the existing React Native + Unity + AR
Foundation makeup app. This is not a full app expansion. The feature should
render natural eyebrow color and density on a tracked face, expose minimal
React Native controls, and preserve a path for future region-specific
renderers.

## User Experience Scope

The first implementation loop should add eyebrow as a selectable makeup region
beside the existing lip, cheek, and eye controls.

The user should be able to:

- Enable or disable eyebrow makeup independently.
- Select a brow color preset suitable for natural makeup.
- Adjust opacity and intensity.
- Tune soft edge coverage through the existing region tuning controls.
- Keep existing lip, cheek, and eye behavior unchanged.

Out of scope for the first loop:

- Full camera/photo/video product workflow.
- Backend upload, recommendation, AI inference, raw-frame storage, or face data
  persistence.
- Android.
- Payment, ads, brand partnership, product sale links, or commercial SDKs.
- App Store submission automation.

## Product Behavior

Eyebrow makeup should appear face-attached during normal head motion and should
avoid a sticker-like hard edge. The first loop uses an in-house UV mask and the
existing face mesh renderer. The feature is accepted only after local checks and
user iPhone visual review.

Important quality questions for device QA:

- Does eyebrow placement stay stable when the user turns left and right?
- Does the brow effect look attached rather than floating above the face?
- Do color and intensity changes update immediately?
- Does the effect fade or hide gracefully during tracking loss?
- Are the left and right brows close enough for a first product slice, while
  leaving room for later asymmetry controls?

## Presets

First-loop presets use natural brow colors rather than lip colors:

- `natural_brow`: neutral brown, multiply blend, opacity `0.75`,
  intensity `0.75`, feather `0.48`, coverage `0.62`, roughness `1`,
  specular `0`, gloss boost `0`.
- `soft_brow`: lighter brown, lower intensity `0.66`, feather `0.48`,
  coverage `0.58`, roughness `1`, specular `0`, gloss boost `0`.
- Brow color choices are separate from lip colors: `ash_brown`,
  `neutral_brown`, `dark_brown`, `soft_black`, and `light_brown`.
- Brow color is also parameterized in the RN HUD with user-facing
  `Temperature` and `Depth` sliders. Internally these remain
  `colorWarmth` and `colorDepth`; RN sends the computed final hex through the
  existing Unity `color` field.
- PNG-derived hair candidates are selectable as mask/detail textures:
  `Daily hair`, `Natural hair`, `Narrow hair`, and `Light brown`. The source
  art is user-authored. The generated Unity textures remove the grey
  background/glow, store soft alpha in red/alpha, and store hair detail in blue
  so the shader can apply color separately.
- Brow texture detail is parameterized with a `Texture Detail` slider that maps
  to `detailAmount`. This preserves the color layer while allowing a controlled
  multiply-like darkening of only the extracted hair detail.
- `light_brown` with PNG-derived brow hair uses normal alpha composition while
  keeping `detailAmount` active. Darker PNG brow colors keep multiply
  composition. This prevents the light brow option from being darkened by a
  full multiply pass while preserving hair texture contrast.
- Brow placement is parameterized with `Brow Spread` and `Brow Y` controls.
  `Brow Spread` symmetrically expands/contracts the two brow masks around the
  UV centerline, while `Brow Y` shifts vertical mask sampling. The next iPhone
  QA can correct small centered/low placement errors live without regenerating
  PNG masks.
- Unity `recipe_applied` diagnostics emit the applied `maskSpreadX` and
  `maskOffsetY` values, and the RN HUD summarizes them as `spread=` and `y=` so
  device QA can confirm placement control delivery without collecting raw
  camera frames.

No third-party assets, commercial SDKs, research-only datasets, or unclear
license materials should enter the shipping path. Current brow assets are
either procedural in-house masks or user-authored PNGs transformed into
Unity-ready alpha/detail textures.

## Renderer Direction

The approved direction is to add brow through the existing smooth region mask
path first, while documenting a renderer-routing contract that allows future
replacement.

Initial mapping:

- `lip` -> `smooth-region-mask`
- `cheek` -> `smooth-region-mask`
- `eye` -> `smooth-region-mask`
- `brow` -> `smooth-region-mask`

Future mapping may split into:

- `lip` -> dedicated lip renderer
- `cheek` -> dedicated cheek renderer
- `eye` -> dedicated eye renderer
- `brow` -> dedicated eyebrow renderer

React Native should continue to send a stable `region="brow"` recipe. Unity can
later route that region to a dedicated brow renderer without forcing a broad UI
or bridge rewrite.

## Decisions

- 2026-06-27: User approved starting with the existing `smooth-region-mask`
  approach for eyebrow makeup.
- 2026-06-27: User asked whether dedicated renderers can be added later. The
  answer is yes if RN keeps a stable region recipe contract and Unity owns the
  renderer routing.
- 2026-06-27: User observed that existing regions should eventually be split by
  renderer too. The chosen plan is to prepare the renderer contract now, without
  doing a full lip/cheek/eye renderer refactor in the eyebrow loop.
- 2026-06-27: Implemented first-loop eyebrow through the existing
  `smooth-region-mask` renderer with `brow-drawn-mask-v1`, `natural_brow`, and
  `soft_brow`. Dedicated renderer splitting remains a follow-up refactor.
- 2026-06-27: Added brow-specific mask threshold and feather policy under the
  route-backed renderer path: threshold `0.035`, default feather `0.42`, and
  recipe feather clamp `0.34..0.48`.
- 2026-06-27: After user build approval, regenerated/synced
  `UnityFramework.framework`, fixed the Unity ARKit Swift compatibility link
  path, built the RN Debug app, installed it on `CloudsiPhone (26.5)`, and
  launched `com.celeste.makeupar.validation`. Visual brow QA is still pending.
- 2026-06-27: First iPhone brow QA showed the runtime path is working:
  `natural_brow`, `soft_brow`, opacity, and intensity controls respond; brow
  attachment remains stable during left/right head turns and expression
  changes. Visual quality needs tuning because the brow shape appears as
  `^ ^`, with the center of each brow too high, the stroke far too thick, and
  the result sticker-like.
- 2026-06-27: Tuned `brow-drawn-mask-v1` before the next device build by
  flattening the center arch, reducing mask thickness, removing the hard upper
  highlight stroke, and lowering default brow opacity/intensity/coverage.
- 2026-06-27: User chose not to apply that intermediate tuning to the iPhone
  build and asked to move directly into the next local loop. The next loop adds
  subtle procedural hair/powder density variation inside the same
  `brow-drawn-mask-v1` resource so the brow is less like a single smooth
  sticker strip before the eventual rebuild.
- 2026-06-27: User then asked to apply three options from the generated brow
  variation sheet. The local app now exposes `brow-soft-arch-fine-hair-v1`
  as the default, plus `brow-back-arch-soft-mix-v1` and
  `brow-slim-tail-fine-hair-v1` for comparison. `brow-drawn-mask-v1` remains
  as a legacy comparison option. At that checkpoint this was local only; the
  following build record covers the iPhone install.
- 2026-06-27: The three-option build was installed and launched on
  `CloudsiPhone`. User QA confirmed tracking and expression attachment, but the
  brow was too faint, especially `soft_brow`; the masks were too centered and
  slightly below the real brow line; color choices were still lip colors.
- 2026-06-27: Local post-QA tuning raises `natural_brow` visibility, adds the
  brow-specific color palette, and shifts the three selected mask PNGs outward
  and upward. At that checkpoint this tuning was local only; the latest rebuild
  record below covers the iPhone install.
- 2026-06-27: Added brow `Warmth` and `Depth` color parameters in the RN HUD.
  This keeps Unity's recipe contract stable while allowing real-device QA to
  tune ash/warm and light/dark brow color without adding more fixed swatches.
- 2026-06-27: Added brow `Brow Spread` and `Brow Y` placement parameters
  through the RN recipe, Unity bridge, overlay material, and smooth mask shader.
  At that checkpoint this tuning was local only; the latest rebuild record below
  covers the iPhone install.
- 2026-06-27: Added applied brow placement diagnostics to Unity
  `recipe_applied` events and the RN HUD summary (`spread=`/`y=`) for the next
  iPhone QA loop.
- 2026-06-27: User approved the current post-QA tuning rebuild. Regenerated and
  synced `UnityFramework.framework` with
  `TIMESTAMP=eyebrow-rebuild-20260627-ufw-r1`, rebuilt the RN Debug app after
  refreshing stale local CocoaPods VFS paths, installed it on
  `CloudsiPhone (26.5)`, and launched `com.celeste.makeupar.validation`. The
  latest visual QA is now pending on the rebuilt app.
- 2026-06-27: User QA on that rebuilt app found `spread=`/`y=` visible and
  adjustable, but `renderer=brow-smooth-region-mask-renderer` was hard to find,
  the brows were still too centered, too faint, and angled upward enough to read
  as angry. Local follow-up tuning now makes `brow-back-arch-soft-mix-v1` the
  default `Soft flat` mask, removes high-arch/legacy masks from the user-facing
  picker, raises brow opacity/intensity to `0.75`, widens `Brow Spread` to
  `±0.34`, starts brow spread at `0.20`, strengthens Unity brow alpha response,
  and shows `Renderer ...` as its own compact HUD row. This follow-up tuning is
  included in the later PNG/bright brow install.
- 2026-06-27: User provided self-authored brow PNGs. The local branch now adds
  four PNG-derived candidates (`Daily hair`, `Natural hair`, `Narrow hair`,
  `Light brown`) plus a brow-only `Texture Detail` slider. The implementation
  does not multiply the full source PNG over the face; it extracts alpha/detail
  channels and lets Unity apply the chosen brow color layer separately.
- 2026-06-27: Local bright-brow tuning now routes `light_brown` plus PNG brow
  hair masks through normal alpha composition, while retaining `detailAmount`
  for extracted hair strokes. Darker PNG brow colors remain on multiply.
  This was then rebuilt, installed, and launched on device for visual QA.
- 2026-06-27: User chose to install the current PNG/bright brow build before
  starting the next auto-placement loop. Regenerated and synced
  `UnityFramework.framework` with
  `TIMESTAMP=eyebrow-png-bright-20260627-ufw-r1`, rebuilt the RN Debug app
  after correcting stale generated CocoaPods Hermes paths, installed it on
  `CloudsiPhone (26.5)`, and launched `com.celeste.makeupar.validation`.
  User visual QA on this exact build is pending.

## Local Verification

- RN Jest: `npm test -- --runInBand` passed with 28 tests, including the
  bright PNG brow blend split.
- Brow mask verifier passed for the new default `brow-back-arch-soft-mix-v1`.
  The verifier now tightens the top-edge arch guard to reduce the angry
  `^ ^` read while still checking separation from eye/cheek/lip masks.
- Unity contract verifier passed:
  `python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py`.
  The verifier now guards brow renderer routing plus brow-specific
  threshold/feather policy and PNG hair `detailAmount`.
- PNG brow hair texture verifier passed:
  `python3 scripts/e7_reference_atlas/verify_brow_png_hair_textures.py`.
  It checks all four generated PNG-derived textures for active coverage, two
  brow components, transparent corners, and a non-flat detail channel.
- Region renderer route verifier passed:
  `python3 scripts/e7_reference_atlas/verify_region_renderer_routes.py`.
- UnityFramework build contract verifier passed:
  `python3 scripts/e7_reference_atlas/verify_unityframework_build_contract.py`.
- Unity `6000.3.18f1` batchmode import/compile exited `0` for the PNG hair
  loop. Log `evidence/logs/eyebrow-png-hair-texture-unity6000-batchmode-20260627.log`
  shows `Tundra build success`, `CompileScripts: 4786.690ms`, imports for all
  four `brow-png-*` textures, and `Exiting batchmode successfully now!`.
- Earlier PNG hair batchmode attempts used the wrong editor,
  Unity `2022.3.62f1`, and failed before C# compile during package resolution
  because AR Foundation `6.3.5` requires Unity 6-era package dependencies. Logs
  remain as negative evidence:
  `evidence/logs/eyebrow-png-hair-texture-unity-batchmode-20260627.log` and
  `evidence/logs/eyebrow-png-hair-texture-unity-batchmode-20260627-rerun.log`.
- After the follow-up QA tuning, Unity batchmode was retried twice but failed
  before compile during Licensing Client IPC initialization. Logs:
  `evidence/logs/eyebrow-followup-unity-batchmode-20260627.log` and
  `evidence/logs/eyebrow-followup-unity-batchmode-20260627-r2.log`.
- UnityFramework regeneration/sync passed for the latest PNG/bright brow build
  with `TIMESTAMP=eyebrow-png-bright-20260627-ufw-r1`.
- RN/Xcode Debug build first failed because ignored CocoaPods files still
  referenced an old Dropbox `HERMES_CLI_PATH`. Correcting only generated local
  Pod support paths let the RN Debug build pass with
  `evidence/logs/eyebrow-rn-xcodebuild-device-png-bright-20260627-r2.log`.
- `devicectl` install and launch passed on `CloudsiPhone (26.5)` with
  `evidence/logs/eyebrow-rn-devicectl-install-png-bright-20260627.log` and
  `evidence/logs/eyebrow-rn-devicectl-launch-png-bright-20260627.log`.

## QA Status

The latest iPhone build is launchable and includes the stronger, flatter brow
tuning, PNG hair candidates, `Texture Detail`, and the bright-brow composition
split. Product quality is still not accepted until the user visually checks this
installed build for visibility, placement, shape, color, and tracking recovery.

## Risks

- Static UV brow masks may not match every user's natural eyebrow position.
- ARFace UV attachment should be stable, but visual quality still needs iPhone
  review under head turns and expressions.
- A first-loop mask may need several tuning passes for width, arch, and tail
  position.
- Full dedicated renderer separation is valuable but should be handled as a
  later refactor after brow is visible and testable.
