# Eyebrow AR Rendering Design

Status: PNG brow hair texture loop implemented locally; rebuild pending
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
3. Add brow mask texture ids for the local candidates.
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
| Mask texture id | Default `brow-back-arch-soft-mix-v1`; user-facing options include `brow-slim-tail-fine-hair-v1` plus PNG-derived `brow-png-daily-hair-v1`, `brow-png-natural-hair-v1`, `brow-png-narrow-hair-v1`, and `brow-png-lightbrown-hair-v1`; compatibility resources `brow-soft-arch-fine-hair-v1` and `brow-drawn-mask-v1` |
| RN presets | `natural_brow`, `soft_brow` |
| Unity resource | `SmoothRegionMasks/brow-soft-arch-fine-hair-v1`, `brow-back-arch-soft-mix-v1`, `brow-slim-tail-fine-hair-v1`, four `brow-png-*` hair textures, plus legacy `brow-drawn-mask-v1` |
| Unity material path | `E3RegionMaskOverlay.BuildMaterialColor` brow cases |
| Route table | `MakeupRegionRendererRoutes` |
| Brow renderer id | `brow-smooth-region-mask-renderer` |
| Brow mask threshold | `0.035` |
| Brow mask feather | `0.42`, clamped from recipe to `0.34..0.48` |

## Renderer Routing Contract

The stable contract should be the recipe region, not a specific renderer class.

Implemented route table:

| Region | Current renderer id | Backend | Future renderer option |
| --- | --- | --- | --- |
| `lip` | `lip-smooth-region-mask-renderer` | `E3RegionMaskOverlay` | `LipMakeupRenderer` |
| `cheek` | `cheek-smooth-region-mask-renderer` | `E3RegionMaskOverlay` | `CheekMakeupRenderer` |
| `eye` | `eye-smooth-region-mask-renderer` | `E3RegionMaskOverlay` | `EyeMakeupRenderer` |
| `brow` | `brow-smooth-region-mask-renderer` | `E3RegionMaskOverlay` | `BrowMakeupRenderer` |

The first loop now has code-level routes and diagnostic `rendererId` output,
while all rows still use the existing smooth-mask backend. A full class split
should wait until the brow path is working on device or until an implementation
change requires it.

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

Initial installed mask QA showed the shape followed the face correctly but
looked like `^ ^`: each brow's center was too high, the mask was far too thick,
and the effect read as sticker-like. The tuned mask keeps the same resource id
and renderer contract, but flattens the arch and reduces the stroke footprint.

The user chose to skip rebuilding the intermediate flatter mask and continue
into the next local loop. A local variation catalog was generated, and three
options were selected for the app: soft arch with fine hair, back-shifted arch
with soft mix texture, and slim tail with fine hair. The first is the RN/Unity
default for the next QA build; the old `brow-drawn-mask-v1` remains available
for comparison.

The first three-option device QA confirmed tracking and expression attachment,
but the brows were too faint, too centered, and slightly below the real brow
line. The current local post-QA candidate masks are shifted `10px` outward per
side and `7px` upward without increasing thickness. This post-QA tuning has now
been rebuilt into `UnityFramework.framework`, installed, and launched on
`CloudsiPhone (26.5)`; visual acceptance on the rebuilt app is still pending.

Follow-up QA on that rebuilt app confirmed `spread=` and `y=` are visible and
adjustable, but the renderer id was too buried in the long recipe summary, the
brow remained too centered, too faint, and the visible angle still read as an
angry/upward brow. The next local candidate therefore switches the default to
the flatter `brow-back-arch-soft-mix-v1`, removes the higher-arch and legacy
masks from the user-facing picker, starts brow spread at `0.20`, expands the
spread clamp to `±0.34`, raises default opacity/intensity to `0.75`, and
increases Unity brow alpha scaling so `75%` should be readable and `100%`
should be intentionally strong.

Current local verifier result for `brow-drawn-mask-v1.png`:

- Size: `512x512`
- Active red-channel pixels (`> 8`): `5123`
- Coverage: `0.019543`
- Bbox: `left=113, top=101, right=398, bottom=129, width=286, height=29`
- Components: two thinner brow components with bbox height `25`.
- Center arch guard: left `4.29px` center rise, right `4.34px` center rise.
- Density texture guard: center peak range `51px` left and `43px` right, with
  mean peak step `2.09` left and `1.66` right.
- Region separation guard: `eye-drawn=0/1200`, `eye-smooth=0/4200`,
  `cheek-drawn=0/50`, `lip-drawn=0/0`.

Selected local candidate verifier results:

| Mask | Active pixels | Bbox height | Center rise summary | Texture summary |
| --- | ---: | ---: | --- | --- |
| `brow-back-arch-soft-mix-v1` | `3384` | `26` | bbox `left=105,top=94,right=406,bottom=119`; centers `171/340` | peak range `13/16`, mean step `1.25/1.17` |
| `brow-slim-tail-fine-hair-v1` | `2569` | `20` | bbox `left=105,top=97,right=406,bottom=116`; centers `173/337` | peak range `68/61`, mean step `4.29/4.72` |

The mask remains a single-channel soft alpha texture, but no longer uses a
fully uniform central ridge. If later device QA still shows poor fit, later
loops can add:

The current PNG hair loop adds user-authored brow art as generated mask/detail
resources rather than applying the original PNGs directly. The generator removes
the grey background and glow, maps the left/right brow art into the same 512 UV
space, stores soft shape alpha in red/alpha, and stores extracted hair strokes
in blue. The shader keeps the existing color layer and uses `_DetailAmount` to
darken/detail only the hair signal inside the mask. This gives a controlled
multiply-like effect without multiplying the full grey source image over the
face.

- Separate left/right channels.
- Asymmetry parameters.
- Dedicated brow mesh culling.
- Dedicated brow shader for hair-density or powder-fill behavior.
- Optional landmark or Apple Vision anchor provider after explicit privacy
  review and user approval.

## Material Strategy

First-loop brow should avoid glossy or glitter behavior. Use low specular,
moderate feather, and multiply or normal alpha behavior depending on which looks
more natural on device. Brow now has its own mask policy inside the shared
smooth-mask backend: threshold `0.035`, default feather `0.42`, and recipe
feather clamped to `0.34..0.48`. The RN defaults now send `natural_brow` with
`brow-back-arch-soft-mix-v1` at opacity `0.75`, intensity `0.75`, coverage
`0.62`, and default `maskSpreadX=0.20` with `neutral_brown` (`#4A342B`). Unity
brow alpha scaling is stronger than the previous installed build so `75%`
should be visibly usable and `100%` can become deliberately heavy. The brow
color palette is now separate from lip colors: `ash_brown`, `neutral_brown`,
`dark_brown`, `soft_black`, and `light_brown`. RN exposes brow-only `Temperature` and
`Depth` sliders. These compute a final HTML hex color on the RN side and
keep sending it through the existing Unity `color` field, so no Unity recipe
schema change is required for color QA.
PNG hair detail is separate from color: RN sends `detailAmount`, Unity stores
it in `RegionRecipeState.DetailAmount`, and `SmoothRegionMask.shader` exposes
`_DetailAmount` to strengthen extracted hair strokes after the chosen brow
color is applied.
RN also exposes brow-only `Brow Spread` and `Brow Y` placement sliders. `Brow
Spread` becomes signed `maskSpreadX` and expands/contracts the two brow masks
symmetrically around the UV centerline; `Brow Y` becomes signed `maskOffsetY`.
Both are clamped in `RNBridge` and `E3RegionMaskOverlay`, now to `±0.34` for
horizontal spread and `±0.08` for vertical offset, then applied in
`SmoothRegionMask.shader` through `_MaskSpreadX` and `_MaskOffset.y`.
For QA, raise opacity first, intensity second, and coverage last to improve
visibility without immediately making the brow sticker-like; use `Temperature`
and `Depth` to fine-tune color after visibility is readable, then use `Brow Spread`
for brows that are too centered or too wide and `Brow Y` for vertical placement
before generating another mask texture.

The QA panel now treats `RAW`, `PROCESSED`, and `FINAL` as debug view stages
instead of product mask candidates. `LEGACY DRAWN` remains a compatibility
resource only and must not be surfaced in the user-facing QA controls.

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
- Static guard that Unity parser accepts `brow` and applies brow-specific mask
  threshold/feather policy: passed.
- Offline mask inspection for active pixel coverage and bbox: passed.
- PNG-derived brow hair texture inspection:
  `python3 scripts/e7_reference_atlas/verify_brow_png_hair_textures.py`
  passed for `Daily hair`, `Natural hair`, `Narrow hair`, and `Light brown`.
- Unity batchmode import/compile passed with Unity `6000.3.18f1` for the PNG
  hair loop. Log
  `evidence/logs/eyebrow-png-hair-texture-unity6000-batchmode-20260627.log`
  shows `Tundra build success`, `CompileScripts: 4786.690ms`, all four
  `brow-png-*` texture imports, and `Exiting batchmode successfully now!`.
- Two earlier PNG hair attempts used Unity `2022.3.62f1`, which is not the
  project editor version and failed during package resolution because AR
  Foundation `6.3.5` requires Unity 6-era package dependencies. No iPhone build
  was attempted.
- UnityFramework build contract verifier passed and now guards Swift
  compatibility link flags plus Unity export failure detection.
- UnityFramework regeneration/sync passed for the prior installed tuning with
  `TIMESTAMP=eyebrow-rebuild-20260627-ufw-r1`.
- RN/Xcode Debug build initially failed from stale ignored CocoaPods VFS paths
  that referenced an old Dropbox checkout; `pod install --no-repo-update`
  refreshed local Pod support files, then the RN/Xcode Debug build passed.
- `devicectl` install and launch passed on `CloudsiPhone (26.5)` for
  `com.celeste.makeupar.validation`.
- TypeScript compile with `npx tsc --noEmit`: passed.
- RN lint with `npm run lint`: passed.
- Region renderer route verifier: passed.

Remaining real-device visual QA on the rebuilt app:

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
