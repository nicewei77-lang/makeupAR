# Eyebrow AR Rendering Design

Status: Local implementation complete; device QA pending
Date: 2026-06-27
Related product doc: `docs/product/eyebrow-makeup-feature.md`

## Current System

The current app sends React Native recipe batches to Unity through `RNBridge`.
Unity parses region layers and applies them through `E3RegionMaskOverlay`, which
renders a smooth UV mask over the AR Foundation `ARFace` mesh. Existing runtime
regions are now `lip`, `cheek`, `eye`, and `brow`.

The renderer already supports:

- Per-region enabled state.
- Color, opacity, intensity, feather, coverage, roughness, specular, gloss, and
  gradient fields.
- Mask textures in `Assets/Resources/SmoothRegionMasks/`.
- ARFace mesh/UV attachment.
- Visibility suppression for clean/capture/debug modes.
- Tracking-state fade/hide behavior.

## Implemented First Loop

Eyebrow support was added by extending the existing region recipe pipeline:

1. Extend region constants from `lip | cheek | eye` to include `brow`.
2. Add brow texture sample presets such as `natural_brow` and `soft_brow`.
3. Add a brow mask texture id such as `brow-drawn-mask-v1`.
4. Generate an in-house 512x512 brow UV mask under
   `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/`.
5. Teach Unity parsing and mask normalization to accept `brow`.
6. Route `brow` to the current `smooth-region-mask` renderer for this loop.
7. Record the renderer routing contract so future dedicated renderers can
   replace the implementation per region.

Implemented contract values:

| Field | Value |
| --- | --- |
| Region | `brow` |
| Renderer mode | `smooth-region-mask` |
| Mask texture id | `brow-drawn-mask-v1` |
| RN presets | `natural_brow`, `soft_brow` |
| Unity resource | `SmoothRegionMasks/brow-drawn-mask-v1` |
| Unity material path | `E3RegionMaskOverlay.BuildMaterialColor` brow cases |

## Renderer Routing Contract

The stable contract should be the recipe region, not a specific renderer class.

Conceptual route table:

| Region | Initial renderer | Future renderer option |
| --- | --- | --- |
| `lip` | `smooth-region-mask` | `LipMakeupRenderer` |
| `cheek` | `smooth-region-mask` | `CheekMakeupRenderer` |
| `eye` | `smooth-region-mask` | `EyeMakeupRenderer` |
| `brow` | `smooth-region-mask` | `BrowMakeupRenderer` |

In the first loop this may remain a documented routing decision plus small
normalization helpers. A full class split should wait until the brow path is
working on device or until an implementation change requires it.

## Why Not Split All Renderers Now

`E3RegionMaskOverlay` currently holds region application, mask loading,
diagnostics, material configuration, tracking visibility, and lip-specific
features. Splitting all renderers is a good future direction, but doing it in
the same loop as the first eyebrow feature would increase regression risk for
already tuned lip matte/gradient/gloss behavior.

The safer path is:

1. Add brow through the existing renderer.
2. Keep tests around region parsing and recipe payload shape.
3. Verify brow on device.
4. Split renderers in a separate refactor when there is a working visual target
   to preserve.

## Brow Mask Strategy

The first brow mask is generated in-house and procedural. It is a
soft, symmetric eyebrow shape in ARFace UV space, stored as a readable,
uncompressed Unity resource. It favors conservative coverage so it does not
paint the forehead or eyelids.

Local verifier result for `brow-drawn-mask-v1.png`:

- Size: `512x512`
- Active red-channel pixels (`> 8`): `11275`
- Coverage: `0.043011`
- Bbox: `left=99, top=132, right=412, bottom=196, width=314, height=65`
- Components: two large brow components, center gap empty at the verifier
  threshold.

The mask can start as a single-channel soft alpha shape. If the first device QA
shows poor fit, later loops can add:

- Separate left/right channels.
- Asymmetry parameters.
- Dedicated brow mesh culling.
- Dedicated brow shader for hair-density or powder-fill behavior.
- Optional landmark or Apple Vision anchor provider after explicit privacy
  review and user approval.

## Material Strategy

First-loop brow should avoid glossy or glitter behavior. Use low specular,
moderate feather, and multiply or normal alpha behavior depending on which looks
more natural on device.

The shader does not need a new third-party dependency. If the generic shader
cannot create a convincing brow result, a dedicated brow shader can be added in
a later renderer split.

## React Native Data Flow

React Native should add `brow` to the same payload builder that currently
emits region layers. The Unity bridge should continue to receive a batch with
one layer per known region. The important compatibility point is that future
Unity code can decide renderer selection internally from `region` and
`textureSample`.

No raw camera frame storage, upload, AI inference, recommendation, commercial
SDK, or Android work is part of this flow.

## Verification Plan

Local checks before any real-device build:

- Jest test for eyebrow recipe payload shape: passed.
- Static guard that Unity parser accepts `brow`: passed.
- Offline mask inspection for active pixel coverage and bbox: passed.
- Unity batchmode import/compile when Unity code or assets change: passed with
  Unity `6000.3.18f1`.
- TypeScript compile with `npx tsc --noEmit`: passed.
- RN lint with `npm run lint`: passed.

Real-device QA after build approval:

- Frontal neutral brow placement.
- Left and right head turn stability.
- Raised-brow or expression change.
- Color/intensity immediate update.
- Temporary tracking loss recovery.

The agent should not capture face screenshots directly. User-provided
observations or screenshots may be recorded only with user approval.

## Future Renderer Split

When the feature is stable enough to preserve, split by responsibility:

- Common recipe schema and validation.
- Common face tracking visibility state.
- Per-region renderer classes.
- Per-region material/shader policy.
- Per-region mask and diagnostic policy.

This split should be tested as a refactor, not mixed into the first visible brow
implementation unless the existing renderer blocks progress.
