# Eyebrow Makeup Feature

Status: Local implementation complete; iPhone QA pending
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

First-loop presets are conservative:

- `natural_brow`: soft neutral brown, multiply blend, opacity `0.62`,
  intensity `0.58`, feather `0.42`, coverage `0.70`, roughness `0.96`,
  specular `0.02`, gloss boost `0`.
- `soft_brow`: lighter brown, lower intensity, wider feather, roughness `1`,
  specular `0`, gloss boost `0`.

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

## Local Verification

- RN Jest focused test: `npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand`
  passed with 23 tests.
- Brow mask verifier passed:
  `python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py`.
  The verifier now guards brow separation from eye/cheek/lip masks.
- Unity contract verifier passed:
  `python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py`.
  The verifier now guards brow renderer routing plus brow-specific
  threshold/feather policy.
- Region renderer route verifier passed:
  `python3 scripts/e7_reference_atlas/verify_region_renderer_routes.py`.
- Unity `6000.3.18f1` batchmode import/compile exited `0`; log showed
  `Tundra build success` and imported
  `Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png`.
  This compile was before the later brow-specific mask policy change; rerun is
  pending because the local disk currently has only about `252Mi` free.

## QA Status

The feature is ready for an approved real-device build/installation loop, but
it is not accepted as visually product-quality until user iPhone QA confirms
placement, attachment, color response, and tracking recovery.

## Risks

- Static UV brow masks may not match every user's natural eyebrow position.
- ARFace UV attachment should be stable, but visual quality still needs iPhone
  review under head turns and expressions.
- A first-loop mask may need several tuning passes for width, arch, and tail
  position.
- Full dedicated renderer separation is valuable but should be handled as a
  later refactor after brow is visible and testable.
