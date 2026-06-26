# Eyebrow Makeup Feature

Status: Design review
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

First-loop presets should be conservative:

- `natural_brow`: soft neutral brown, low gloss, powder-like density.
- `soft_brow`: lighter brown, lower opacity, wider feather.
- Optional dark preset only if the local mask preview and device QA do not make
  the effect look stamped on.

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

## Risks

- Static UV brow masks may not match every user's natural eyebrow position.
- ARFace UV attachment should be stable, but visual quality still needs iPhone
  review under head turns and expressions.
- A first-loop mask may need several tuning passes for width, arch, and tail
  position.
- Full dedicated renderer separation is valuable but should be handled as a
  later refactor after brow is visible and testable.
