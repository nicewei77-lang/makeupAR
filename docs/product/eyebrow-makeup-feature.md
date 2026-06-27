# Eyebrow Makeup Feature

Status: First iPhone QA tuning in progress; rebuild pending
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

- `natural_brow`: neutral brown, multiply blend, opacity `0.68`,
  intensity `0.68`, feather `0.48`, coverage `0.62`, roughness `1`,
  specular `0`, gloss boost `0`.
- `soft_brow`: lighter brown, lower intensity `0.56`, feather `0.48`,
  coverage `0.58`, roughness `1`, specular `0`, gloss boost `0`.
- Brow color choices are separate from lip colors: `ash_brown`,
  `neutral_brown`, `dark_brown`, and `soft_black`.
- Brow color is also parameterized in the RN HUD with `Warmth` and `Depth`.
  The selected swatch remains the base color, and RN sends the computed final
  hex through the existing Unity `color` field.

No third-party assets, commercial SDKs, research-only datasets, or unclear
license materials should enter the shipping path. The first brow mask should be
generated in-house from simple procedural geometry.

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
  as a legacy comparison option. This is local only and has not been rebuilt
  to the iPhone.
- 2026-06-27: The three-option build was installed and launched on
  `CloudsiPhone`. User QA confirmed tracking and expression attachment, but the
  brow was too faint, especially `soft_brow`; the masks were too centered and
  slightly below the real brow line; color choices were still lip colors.
- 2026-06-27: Local post-QA tuning raises `natural_brow` visibility, adds the
  brow-specific color palette, and shifts the three selected mask PNGs outward
  and upward. This post-QA tuning has not yet been installed on-device.
- 2026-06-27: Added brow `Warmth` and `Depth` color parameters in the RN HUD.
  This keeps Unity's recipe contract stable while allowing real-device QA to
  tune ash/warm and light/dark brow color without adding more fixed swatches.

## Local Verification

- RN Jest focused test: `npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand`
  passed with 23 tests.
- Brow mask verifier passed for the three selected local candidates:
  `brow-soft-arch-fine-hair-v1`, `brow-back-arch-soft-mix-v1`, and
  `brow-slim-tail-fine-hair-v1`. The verifier now accepts the thinner
  fine-hair candidates while still guarding arch height and separation from
  eye/cheek/lip masks.
- Unity contract verifier passed:
  `python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py`.
  The verifier now guards brow renderer routing plus brow-specific
  threshold/feather policy.
- Region renderer route verifier passed:
  `python3 scripts/e7_reference_atlas/verify_region_renderer_routes.py`.
- UnityFramework build contract verifier passed:
  `python3 scripts/e7_reference_atlas/verify_unityframework_build_contract.py`.
- Unity `6000.3.18f1` batchmode import/compile exited `0`; log showed
  `Tundra build success` and imported
  `Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png`.
- UnityFramework regeneration/sync passed with
  `TIMESTAMP=eyebrow-20260627-ufw-r3`.
- RN/Xcode Debug build, `devicectl` install, and `devicectl` launch passed on
  `CloudsiPhone (26.5)`.

## QA Status

The feature is installed and launchable on the approved iPhone builds. Device QA
has confirmed attachment, expression stability, and control response. Visual
product quality is not accepted yet because the latest installed build is too
faint, too centered, and slightly low, with lip-color choices still showing in
the brow HUD. The current local branch fixes those issues by increasing brow
visibility, adding brow-specific colors, and shifting the selected masks outward
and upward. This post-QA tuning requires a fresh UnityFramework/RN device build
before the next iPhone QA pass.

## Risks

- Static UV brow masks may not match every user's natural eyebrow position.
- ARFace UV attachment should be stable, but visual quality still needs iPhone
  review under head turns and expressions.
- A first-loop mask may need several tuning passes for width, arch, and tail
  position.
- Full dedicated renderer separation is valuable but should be handled as a
  later refactor after brow is visible and testable.
