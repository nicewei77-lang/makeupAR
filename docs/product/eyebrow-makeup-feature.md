# Eyebrow Makeup Feature

Status: MediaPipe canonical asset standard linked; live landmark bridge implemented
Date: 2026-06-30
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
- Backend upload, recommendation, raw-frame storage, or face data persistence.
- AI/model inference except the explicitly approved on-device MediaPipe brow
  landmark runtime described below.
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
  intensity `0.76`, feather `0.42`, coverage `0.66`, roughness `1`,
  specular `0`, gloss boost `0`. This is the fuller everyday brow preset.
- `soft_brow`: lighter powder brow, opacity `0.75`, intensity `0.62`,
  feather `0.48`, coverage `0.54`, roughness `1`, specular `0`, gloss boost
  `0`. This is intentionally softer and should be labeled `Soft Powder` in UI
  rather than shown as a raw texture id.
- Brow color choices are separate from lip colors: `ash_brown`,
  `neutral_brown`, `dark_brown`, `soft_black`, and `light_brown`.
- Brow color is also parameterized in the RN HUD with user-facing
  `Temperature` and `Depth` sliders. Internally these remain
  `colorWarmth` and `colorDepth`; RN sends the computed final hex through the
  existing Unity `color` field.
- PNG-derived hair candidates are selectable as mask/detail textures:
  `Daily flat`, `Flat sharp`, `Flat multiply`, `Daily hair`, `Natural hair`,
  `Narrow hair`, and `Light brown`. The source art is user-authored. The
  generated Unity textures remove the grey/black background and glow, store
  soft alpha in red/alpha, and store hair detail in blue so the shader can apply
  color separately.
- PSD-derived MediaPipe/ARCore canonical-face candidates are now the authored
  asset standard for lip, cheek, and brow:
  `psd-arcore-lip-style-v1`, `psd-arcore-lip-mask-v1`,
  seven cheek masks (`psd-arcore-cheek-undereye-v1`,
  `psd-arcore-cheek-asia-z-v1`, `psd-arcore-cheek-sunkissed-v1`,
  `psd-arcore-cheek-daily-oval-v1`, `psd-arcore-cheek-undereye2-v1`,
  `psd-arcore-cheek-lovely-round-v1`,
  `psd-arcore-cheek-lifted-diagonal-v1`), and
  `psd-arcore-brow-semi-arch-v1`.
  RN defaults to these PSD/canonical masks for lip, cheek, and brow. Eye remains
  on `eye-drawn-mask-v1` until a canonical eye asset is authored.
  `archive`/`archieve` layers are excluded. White or gray PSD pixels are
  interpreted as coverage/density masks, not white makeup color; the actual
  lip, cheek, or brow color still comes from the RN/Unity recipe parameters.
  The current local conversion preserves the PSD full-canvas canonical layout
  instead of bbox-fitting the layers into existing ARKit/Unity mask positions.
  PSD intake now selects runtime source layers by canonical layer path instead
  of trusting Photoshop visibility alone, so hidden-but-named source layers can
  still be force-composited. Recommended PSD delivery is to keep makeup source
  layers visible and named consistently, while keeping guide layers such as
  `preview`, `UVs`, `lines`, `background`, `archive`, and `mask` hidden or
  outside the runtime source set.
  The 2026-06-30 updated PSD keeps the same semantic source layers but changes
  some path details: eyebrow group `Semi-arch` may be capitalized and cheek can
  arrive as `Root/blush/Undereye/all`. The extractor now matches runtime
  layer paths case-insensitively and treats `Undereye/all` as the cheek runtime
  source.
- Next brow asset intake should use three left/right pairs, delivered as six
  transparent PNGs named from the wearer's perspective, for example
  `daily_wearer_left.png` and `daily_wearer_right.png`. Recommended master
  canvas is `2048x1024` per single brow side, sRGB straight-alpha PNG, with the
  brow occupying roughly `1500..1700px` width and `220..360px` height plus
  consistent transparent padding. Individual hair strokes should remain visible
  at `6..12px` source thickness with varied opacity; avoid filled silhouettes,
  baked skin, grey backgrounds, glow, drop shadow, or premultiplied-alpha edge
  halos. The current Unity-ready brow masks are `512x512`, which is tight for
  photo-like hair grain; the next asset-generation pass should downsample the
  2048 masters into a `1024x1024` Unity brow atlas, then fall back to `512x512`
  only for performance comparison.
- `Natural hair` remains the comparison baseline for the PNG hair family, but
  the current canonical-asset default path uses `PSD semi arch` for brow.
  Default PNG `Texture Detail` remains `0.52`; `Soft Powder` lowers detail by
  default so the result reads as powder instead of harsh strokes.
- Brow texture detail is parameterized with a `Texture Detail` slider that maps
  to `detailAmount`. This preserves the color layer while allowing a controlled
  multiply-like darkening of only the extracted hair detail.
- Brow rendering is intentionally different from lip and cheek rendering. Lip
  and cheek can use broad smooth-region fill, but brow must be fiber-first:
  the blue detail channel drives visible opacity, the red shape channel only
  gates the brow area and adds a very weak powder veil. This avoids turning
  eyebrow masks into a filled block when a source asset has broad density.
- `PSD semi arch` uses the same tintable brow color path, but its PSD layers
  are interpreted separately: `left/right` drive the hair-detail channel,
  `gradient` adds only a very light powder layer, and `full` marks the target
  brow core that should be protected from skin restoration. In the current
  non-AI cleanup path, the app approximates "recognized original brow" with the
  canonical source-brow mask and restores sampled skin color only outside the
  PSD `full` core. The PSD semi-arch generator keeps the 4096px PSD source
  canvas as the source of truth and downscales the full canonical canvas to the
  runtime texture, without fitting the side bboxes into ARKit/source-brow target
  boxes. This preserves the authored semi-arch proportions and avoids hidden
  per-asset stretching. This is a canonical asset-space reference, not a runtime
  MediaPipe camera inference path. The mask uses controlled initial
  `Texture Detail` (`0.64`) and `Cleanup` defaults.
- 2026-06-30 device feedback showed that the above static fitting is not enough
  to "recognize" the real eyebrow. A MediaPipe canonical target only defines the
  asset coordinate system; it does not tell the Unity/ARKit runtime where the
  user's current brow is. Do not add hidden per-asset correction constants to
  make PSD semi-arch line up. Apple Vision eyebrow landmarks were considered as
  an interim iOS diagnostic path, but the accepted product placement contract is
  MediaPipe-first: runtime brow placement belongs to the MediaPipe full-face
  landmark packet. Raw camera frames must not be stored; only transient
  in-memory analysis, landmarks, and diagnostics are allowed.
- MediaPipe Face Landmarker is an approved brow-runtime exception as of
  2026-06-30. The approval is constrained to on-device eyebrow landmark
  placement with `face_landmarker.task` bundled in the app, no raw frame storage
  or upload, policy keyword `no raw frame storage or upload`, and numeric diagnostics only (`landmark`, `bbox`, `confidence`,
  timing, and status). User-triggered final photo/video capture remains allowed
  through the local Photos save flow, but detector frames are not capture media.
  The iOS dependency is installed with `MediaPipeTasksVision` `0.10.14`, the
  model is bundled, and the first live bridge is implemented. Unity captures a
  transient in-memory frame only while brow is active, UnityFramework calls an
  Objective-C++ bridge that resolves the app-owned Swift MediaPipe runtime,
  Swift runs Face Landmarker and returns eyebrow point counts, bbox,
  confidence, latency, and status, and RN surfaces this as
  `e7_mediapipe_brow_landmarks` diagnostics.
  This bridge proves live landmark packet access, but it does not yet move or
  warp the brow asset by those landmarks.
- Implementation note: brow assets should now be interpreted as MediaPipe
  canonical assets, not ARKit UV semantic-placement assets. Runtime brow
  placement belongs to the MediaPipe full-face landmark packet; the current
  live bridge is only the proof of packet access until a later renderer step
  maps, moves, or warps the brow asset from those landmarks.
- `Flat multiply` uses the same flatter/sharper extracted texture as
  `Flat sharp`, but forces multiply composition even for `light_brown` so the
  next device QA can compare normal color-layer composition against a multiply
  probe.
- `light_brown` with PNG-derived brow hair uses normal alpha composition while
  keeping `detailAmount` active. Darker PNG brow colors keep multiply
  composition. This prevents the light brow option from being darkened by a
  full multiply pass while preserving hair texture contrast.
- Brow placement is parameterized with `Gap`, `Brow Y`, `Angle`, `Arch`, and
  `Arch Position`
  controls. `Gap` is the user-facing name for the brow midline spacing control;
  internally RN keeps compatibility by sending the same value through
  `maskSpreadX` and `browGap`. `Brow Y` shifts vertical sampling, `Angle`
  applies a conservative brow-tail tilt correction, and `Arch` warps the brow
  mountain area without changing the whole brow pose. `Arch Position` shifts
  only the brow mountain forward/back along the inner-to-tail axis. User-facing
  placement sliders now start at neutral `0`; RN sends these values as literal
  deltas and no longer applies hidden default `browGap` or `maskOffsetY`
  baselines for canonical PSD placement.
- Brow reshape now uses a middle-path correction rather than full original-brow
  removal. `Cleanup` controls a weak concealer layer over a canonical source
  brow mask plus the target brow halo, so original hairs can still be reduced
  when the selected brow asset is shifted above or below the user's original
  brow. `Reshape` strengthens the target brow edge/shape inside the brow ROI.
  Defaults are conservative, `Cleanup=0.24` and `Reshape=0.16`, because
  the current renderer does not run AI face parsing or true inpainting. The
  current local build candidate uses a `GrabPass`-backed cleanup pass that
  samples the current AR camera image in the shader and blends nearby skin color
  back over the weak cleanup halo; it does not save or upload source frames.
  The cleanup shader must not use a fixed beige "skin" tint. It now samples
  farther surrounding pixels and downweights dark brow-hair samples before
  blending, so the restoration color is driven by the live camera frame. Unity
  binds internal `SmoothRegionMasks/brow-cleanup-source-v1` as
  `_BrowCleanupSourceTex`; that source mask is sampled from unshifted face UVs,
  while the user-selected brow asset still uses placement controls such as
  `Brow Y`, `Gap`, `Angle`, `Arch`, and `Arch Position`. An `AR BG` QA source
  switch is also prepared for brow cleanup. It keeps
  `GrabPass` as the default, and only when selected asks Unity to blit
  `ARCameraBackground.material` into a transient GPU texture for the cleanup
  shader. A brow-only `Skin Restore On/Off` toggle lets QA compare the asset
  without skin restoration; when off, RN preserves the stored `Cleanup` slider
  value but sends effective `browCleanupEnabled=false`,
  `browCleanupStrength=0`, and `browCleanupSourceMode=none`.
- Clean mode now separates user product capture from developer reference
  capture. `Save Photo` captures the current final app view and writes it to
  the local Photos library. `Record Video`/`Stop Video` uses ReplayKit screen
  capture and `AVAssetWriter` to save a local movie to Photos. These actions
  are explicit user-triggered local saves and are separate from validation
  evidence capture.
- Unity `recipe_applied` diagnostics emit the applied `browGap`, `maskOffsetY`,
  `browAngle`, `browArch`, `browArchPosition`, `browCleanupStrength`, and
  `browReshapeStrength` values. They also emit `browCleanupSource`,
  `browCleanupFallback`, `browCleanupStatus`, and `browCleanupSourceMode` so
  device QA can see whether the active candidate is the GrabPass live-frame
  path or the prepared ARCameraBackground fallback. They also emit
  `browCleanupEnabled`, `browCleanupFallbackAvailable`,
  `browCleanupCameraTextureWidth`, and `browCleanupCameraTextureHeight` so QA can
  tell whether cleanup is active and whether the AR BG transient texture was
  actually ready. The RN HUD summarizes these values as `gap=`, `y=`, `angle=`,
  `arch=`, `archPos=`, `cleanupEnabled=`, `cleanup=`, `reshape=`,
  `cleanupSource=`, `cleanupFallback=`, `cleanupStatus=`, `cleanupMode=`,
  `cleanupFallbackAvailable=`, and `cleanupCameraTex=` without collecting raw
  camera frames.
- The RN tuning panel is scoped by focused region: lip-focused editing shows
  lip finish/area controls, while brow-focused editing shows brow texture,
  mask, color, detail, coverage, feather, and placement controls. Brow keeps
  `Coverage` and `Feather` because they control useful brow density/edge
  softness; brow hides lip/material finish controls such as roughness,
  specular, glossy, gradient, normal, and overlip.
- Sliders now expose small `-` and `+` nudge buttons in addition to dragging.
  Dragging remains coarse and quick, while nudge buttons adjust by `0.01` UI
  value steps for brow placement and color/detail fine tuning.

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
- 2026-06-27: User supplied a flatter self-authored `brow_dailyflat.png` and
  approved the texture-fidelity A/B loop. The local branch now adds
  `Daily flat`, `Flat sharp`, and `Flat multiply`; defaults brow mask selection
  to `Flat sharp`; raises default `Texture Detail` to `0.68`; strengthens the
  shader's thin-hair detail response; and keeps `Flat multiply` as an explicit
  multiply comparison path.
- 2026-06-27: User approved the daily-flat iPhone build/install. Regenerated
  and synced `UnityFramework.framework` with
  `TIMESTAMP=eyebrow-dailyflat-20260627-ufw-r1`, rebuilt the RN Debug app,
  installed it on `CloudsiPhone (26.5)`, and launched
  `com.celeste.makeupar.validation`. User visual QA on this daily-flat build is
  pending.
- 2026-06-27: User QA on the daily-flat build found the flat candidates showed
  mostly outlines with hollow centers, the visible hair candidates still looked
  paint-like, switching between `natural_brow` and `soft_brow` reset the brow
  mask to `Flat sharp`, the brow gap was too narrow, and `soft_brow` appeared
  invisible. Local follow-up now fills the flat PNG alpha interior while keeping
  hair detail separate, widens the daily-flat masks and default spread, preserves
  the selected mask when switching brow presets, and raises `soft_brow`
  visibility. This follow-up has now been rebuilt, installed, and launched on
  `CloudsiPhone (26.5)`.
- 2026-06-27: User approved the flat-fill/soft-brow iPhone build/install.
  Regenerated and synced `UnityFramework.framework` with
  `TIMESTAMP=eyebrow-flatfill-softbrow-20260627-ufw-r1`, rebuilt the RN Debug
  app from commit `1e55c4e`, installed it on `CloudsiPhone (26.5)`, and launched
  `com.celeste.makeupar.validation`. User visual QA on this flat-fill/soft-brow
  build is pending.
- 2026-06-27: User QA on the flat-fill/soft-brow build found the FLAT candidates
  still hollow, while non-flat PNG hair candidates render. Local follow-up now
  removes the FLAT-only vertical-fill pipeline and regenerates the three FLAT
  textures through the same non-filled PNG hair extraction path as the visible
  candidates. It also widens the FLAT targets and raises default `maskSpreadX`
  to `0.28`. This follow-up was rebuilt from commit `9f35cbc`, installed, and
  launched on `CloudsiPhone (26.5)`, but user QA still found the FLAT candidates
  rendered as hollow outlines.
- 2026-06-28: User supplied `brow_dailyflat_2.png`, a flatter daily-flat source
  on a light background. Local follow-up now regenerates `Daily flat`,
  `Flat sharp`, and `Flat multiply` from that source. The PNG verifier now
  rejects hollow FLAT interiors; `Flat sharp` records inner fill `0.822/0.932`
  with detailStd `57.63`. This fix was locally verified in commit `cd2c0fd` and
  is included in the later `72648a9` Gap/Angle/Arch iPhone install.
- 2026-06-28: User QA feedback after the Gap/Angle/Arch install found
  `Soft flat` and `Slim tail fine` too faint, flat candidates too long and still
  visually hollow, PNG hair candidates too paint-like, `natural_brow` and
  `soft_brow` visually unclear, and asked for brow-only arch-position control
  plus region-scoped parameters. Local follow-up now defaults to `Natural hair`,
  distinguishes `Natural` vs `Soft Powder`, adds `Arch Position`, keeps brow
  `Coverage`/`Feather`, hides lip/gloss controls while editing brow, shortens
  and fills flat candidates, boosts faint procedural candidates, and softens PNG
  hair detail in both textures and shader response.
- 2026-06-28: Follow-up device QA found the FLAT candidates still did not read
  like the visible PNG hair candidates. Local follow-up now aligns
  `Daily flat`, `Flat sharp`, and `Flat multiply` to the same detail-driven PNG
  hair response: FLAT alpha/detail are driven primarily by the extracted hair
  detail channel, and the verifier rejects FLAT textures whose alpha is too
  solid or whose detail-to-alpha ratio is too weak. User approved the minimal
  required-file rebuild; this follow-up has now been rebuilt and installed on
  `CloudsiPhone` without an automated launch.
- 2026-06-28: User QA on the installed FLAT hair-response build found the FLAT
  candidates still rendered with a dark outline and no visible brow hair grain.
  Local diagnosis showed the FLAT blue detail signal and alpha were still
  dominated by a continuous lower-edge outline, and the verifier only checked
  aggregate detail variance. Local fix now rebuilds `Daily flat` from the
  visible `Daily hair` resource, and `Flat sharp`/`Flat multiply` from the
  visible `Narrow hair` resource, packed into the shorter FLAT target boxes.
  It also trims the lower edge band and adds a verifier guard that rejects long
  bright bottom-edge detail runs. User approved the minimal required-file
  rebuild; this follow-up has now been rebuilt and installed on `CloudsiPhone`
  without an automated launch.
- 2026-06-28: User asked whether new left/right transparent eyebrow photo
  assets should be created as three pairs, and noted that the same source art
  looked natural when multiplied over a face in Photoshop while the app still
  clumped the brow grain. Local decision: separate left/right assets are
  recommended for future asset intake, but this pass first fixes rendering so
  PNG brow masks use a photo-detail branch. That branch keeps the broad red
  shape channel as a very light veil and drives the visible effect mainly from
  blue-channel hair peaks, closer to a Photoshop-style multiply result. RN also
  now separates hidden per-mask placement baselines from user-facing placement
  deltas, so sliders start neutral while Unity receives the mask-specific
  baseline plus any user adjustment. User approved the minimal required-file
  rebuild; this follow-up has now been rebuilt and installed on `CloudsiPhone`
  without an automated launch.

## Local Verification

- RN Jest: `npm test -- --runInBand __tests__/App.test.tsx` passed with
  `33/33` tests, including Natural hair defaults, mask-specific brow placement
  baselines, placement-delta reset on mask changes, `Natural`/`Soft Powder`
  labels, preset-switch preservation, `Arch Position`, and region-scoped
  lip/brow parameter panels.
- Brow mask verifier passed for `brow-back-arch-soft-mix-v1` and
  `brow-slim-tail-fine-hair-v1` after the visibility/top-edge retune.
- Unity contract verifier passed:
  `python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py`.
  The verifier now guards brow renderer routing, brow-specific
  threshold/feather policy, PNG hair `detailAmount`, `browArchPosition`, and
  PNG brow photo-detail rendering.
- PNG brow hair texture verifier passed:
  `python3 scripts/e7_reference_atlas/verify_brow_png_hair_textures.py`.
  It checks all seven generated PNG-derived textures for active coverage, two
  brow components, transparent corners, non-flat detail, daily-flat thinness,
  daily-flat fill, shorter flat candidate width, FLAT detail-to-alpha response,
  softer detail variance, bottom-edge outline rejection, and stray low-alpha
  artifact rejection.
- Region renderer route verifier passed:
  `python3 scripts/e7_reference_atlas/verify_region_renderer_routes.py`.
- UnityFramework build contract verifier passed:
  `python3 scripts/e7_reference_atlas/verify_unityframework_build_contract.py`.
- Unity `6000.3.18f1` batchmode import/compile for the 2026-06-28 feedback
  retune was attempted, but did not reach compile because Unity Licensing IPC
  timed out waiting for `LicenseClient-hi`. The hung batchmode process was
  interrupted and the spawned Licensing Client process was terminated. Log:
  `evidence/logs/eyebrow-feedback-retune-unity6000-batchmode-20260628.log`.
- The later minimal required-file device build passed. UnityFramework
  regeneration/sync used `TIMESTAMP=eyebrow-feedback-retune-20260628-ufw-r1`;
  artifact verification recorded `126M` UnityFramework copies and `30M` `Data`
  folders in both RN and package-local paths. RN/Xcode Debug build produced a
  `205M` app bundle and `devicectl` installed
  `com.celeste.makeupar.validation` on `CloudsiPhone`. Logs:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-feedback-retune-20260628-ufw-r1.log`,
  `evidence/logs/eyebrow-rn-xcodebuild-device-feedback-retune-20260628-r1.log`,
  and
  `evidence/logs/eyebrow-rn-devicectl-install-feedback-retune-20260628-r1.log`.
- The FLAT hair-response minimal device build passed after the follow-up QA
  retune. UnityFramework regeneration/sync used
  `TIMESTAMP=eyebrow-flat-hair-response-20260628-ufw-r1`; artifact
  verification recorded `126M` UnityFramework copies and `30M` `Data` folders
  in both RN and package-local paths. RN/Xcode Debug build produced a `205M`
  app bundle and `devicectl` installed `com.celeste.makeupar.validation` on
  `CloudsiPhone`. Logs:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-flat-hair-response-20260628-ufw-r1.log`,
  `evidence/logs/eyebrow-rn-xcodebuild-device-flat-hair-response-20260628-r1.log`,
  and
  `evidence/logs/eyebrow-rn-devicectl-install-flat-hair-response-20260628-r1.log`.
  App launch, screenshots, recordings, and raw camera frame capture were not
  run in this minimal build loop.
- The FLAT edge-outline fix minimal device build passed. UnityFramework
  regeneration/sync used
  `TIMESTAMP=eyebrow-flat-outline-fix-20260628-ufw-r1`; artifact verification
  recorded `126M` UnityFramework copies and `30M` `Data` folders in both RN and
  package-local paths. RN/Xcode Debug build produced a `205M` app bundle and
  `devicectl` installed `com.celeste.makeupar.validation` on `CloudsiPhone`.
  Logs:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-flat-outline-fix-20260628-ufw-r1.log`,
  `evidence/logs/eyebrow-rn-xcodebuild-device-flat-outline-fix-20260628-r1.log`,
  and
  `evidence/logs/eyebrow-rn-devicectl-install-flat-outline-fix-20260628-r1.log`.
  App launch, screenshots, recordings, and raw camera frame capture were not
  run in this minimal build loop.
- The PNG photo-detail brow minimal device build passed. UnityFramework
  regeneration/sync used
  `TIMESTAMP=eyebrow-photodetail-20260628-ufw-r1`; artifact verification
  recorded `126M` UnityFramework copies and `30M` `Data` folders in both RN and
  package-local paths. RN/Xcode Debug build produced a `205M` app bundle and
  `devicectl` installed `com.celeste.makeupar.validation` on `CloudsiPhone`.
  Logs:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-photodetail-20260628-ufw-r1.log`,
  `evidence/logs/eyebrow-rn-xcodebuild-device-photodetail-20260628-r1.log`,
  and
  `evidence/logs/eyebrow-rn-devicectl-install-photodetail-20260628-r1.log`.
  App launch, screenshots, recordings, and raw camera frame capture were not
  run in this minimal build loop.
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
- Latest flat non-filled local checks passed: full RN Jest (`30` tests), TypeScript,
  RN lint, `verify_brow_png_hair_textures.py`, `verify_brow_unity_contract.py`,
  `verify_brow_mask_texture.py`, `verify_region_renderer_routes.py`, and
  `verify_unityframework_build_contract.py`.
- The latest PNG verifier records the source-2 daily-flat resources with a
  minimum center gap of `56px` and rejects hollow FLAT interiors. The current
  `brow-png-dailyflat-sharp-v1` verifier pass recorded `5635` active pixels,
  bbox `left=85,right=423,height=34`, inner fill `0.822/0.932`, and detailStd
  `57.63`.
- Unity `6000.3.18f1` batchmode import/compile for the flat non-filled local
  retune exited `0`. Log
  `evidence/logs/eyebrow-flat-nonfilled-pipeline-unity6000-batchmode-20260627.log`
  shows `Tundra build success`, imports for the three
  `brow-png-dailyflat-*` textures, `CompileScripts: 1023.505ms`, and
  `Exiting batchmode successfully now!`.
- Unity `6000.3.18f1` batchmode import/compile for the source-2 FLAT fill fix
  exited `0`. Log
  `evidence/logs/eyebrow-flat2-filled-texture-unity6000-batchmode-20260628.log`
  shows `Tundra build success`, `CompileScripts: 1015.010ms`, and
  `Exiting batchmode successfully now!`.
- UnityFramework regeneration/sync passed for the `9f35cbc` flat non-filled
  build with `TIMESTAMP=eyebrow-flatnonfilled-20260627-ufw-r1`. Artifact
  verification recorded `126M` UnityFramework copies and `30M` `Data` folders
  in both RN and package-local locations:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-flatnonfilled-20260627-ufw-r1.log`.
- RN/Xcode Debug build passed for that installed `9f35cbc` build with
  `evidence/logs/eyebrow-rn-xcodebuild-device-flatnonfilled-20260627-r1.log`.
  The built app bundle was `205M`, including `126M`
  `UnityFramework.framework` and `30M` `UnityFramework.framework/Data`.
- `devicectl` install and launch passed on `CloudsiPhone (26.5)` with
  `evidence/logs/eyebrow-rn-devicectl-install-flatnonfilled-20260627-r1.log`
  and
  `evidence/logs/eyebrow-rn-devicectl-launch-flatnonfilled-20260627-r1.log`.
- Unity `6000.3.18f1` batchmode import/compile for the flat-fill/soft-brow
  local retune exited `0`. Log
  `evidence/logs/eyebrow-flat-fill-softbrow-unity6000-batchmode-20260627.log`
  shows `Tundra build success`, imports for the three
  `brow-png-dailyflat-*` textures, `CompileScripts: 3043.203ms`, and
  `Exiting batchmode successfully now!`.
- UnityFramework regeneration/sync passed for the flat-fill/soft-brow build
  with `TIMESTAMP=eyebrow-flatfill-softbrow-20260627-ufw-r1`. Artifact
  verification recorded `126M` UnityFramework copies and `30M` `Data` folders
  in both RN and package-local locations:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-flatfill-softbrow-20260627-ufw-r1.log`.
- RN/Xcode Debug build passed with
  `evidence/logs/eyebrow-rn-xcodebuild-device-flatfill-softbrow-20260627-r1.log`.
  The built app bundle is `205M`, including `126M`
  `UnityFramework.framework` and `30M` `UnityFramework.framework/Data`.
- `devicectl` install and launch passed on `CloudsiPhone (26.5)` with
  `evidence/logs/eyebrow-rn-devicectl-install-flatfill-softbrow-20260627-r1.log`
  and
  `evidence/logs/eyebrow-rn-devicectl-launch-flatfill-softbrow-20260627-r1.log`.
- Unity `6000.3.18f1` batchmode import/compile for the daily-flat loop first
  hit a Licensing IPC timeout in the sandboxed run:
  `evidence/logs/eyebrow-dailyflat-png-unity6000-batchmode-20260627.log`.
  The elevated retry passed with `Tundra build success`, imported the three
  `brow-png-dailyflat-*` textures, and exited successfully:
  `evidence/logs/eyebrow-dailyflat-png-unity6000-batchmode-20260627-r2.log`.
- UnityFramework regeneration/sync passed for the latest daily-flat brow build
  with `TIMESTAMP=eyebrow-dailyflat-20260627-ufw-r1`. Artifact verification
  recorded `126M` UnityFramework copies and `30M` `Data` folders in both RN and
  package-local locations:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-dailyflat-20260627-ufw-r1.log`.
- RN/Xcode Debug build passed with
  `evidence/logs/eyebrow-rn-xcodebuild-device-dailyflat-20260627-r1.log`.
  The built app bundle is `205M`, including `126M`
  `UnityFramework.framework` and `30M` `UnityFramework.framework/Data`.
- `devicectl` install and launch passed on `CloudsiPhone (26.5)` with
  `evidence/logs/eyebrow-rn-devicectl-install-dailyflat-20260627-r1.log` and
  `evidence/logs/eyebrow-rn-devicectl-launch-dailyflat-20260627-r1.log`.
- Gap/Angle/Arch and region-scoped parameter UI loop checks passed locally:
  RN Jest `31/31`, TypeScript, RN lint, brow Unity contract verifier, PNG hair
  verifier, and UnityFramework build contract verifier.
- UnityFramework regeneration/sync passed for the Gap/Angle/Arch build with
  `TIMESTAMP=eyebrow-gap-angle-arch-20260628-ufw-r1`. Artifact verification
  recorded `126M` UnityFramework copies and `30M` `Data` folders in both RN and
  package-local locations:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-gap-angle-arch-20260628-ufw-r1.log`.
- RN/Xcode Debug build passed with
  `evidence/logs/eyebrow-rn-xcodebuild-device-gap-angle-arch-20260628-r1.log`.
  The built app bundle is `205M`, including a `126M`
  `UnityFramework.framework`.
- `devicectl` install passed on `CloudsiPhone (26.5)` with
  `evidence/logs/eyebrow-rn-devicectl-install-gap-angle-arch-20260628-r1.log`.
  Automated launch was attempted twice but the iPhone was locked, so launch was
  denied by SpringBoard:
  `evidence/logs/eyebrow-rn-devicectl-launch-gap-angle-arch-20260628-r1.log`
  and
  `evidence/logs/eyebrow-rn-devicectl-launch-gap-angle-arch-20260628-r2.log`.
- Fallback-readiness diagnostics build passed after explicit approval.
  UnityFramework regeneration/sync used
  `TIMESTAMP=eyebrow-cleanup-fallback-20260628-ufw-r1`; artifact verification
  recorded `126M` UnityFramework copies and `30M` `Data` folders in both RN and
  package-local locations:
  `evidence/logs/m3-repro-artifact-verification-eyebrow-cleanup-fallback-20260628-ufw-r1.log`.
- RN/Xcode Debug build attempt r1 failed on `MakeupARLocalMedia.swift` because
  Swift could not see `RCTBridgeModule`; the local fix added
  `MakeupARValidation-Bridging-Header.h` and `SWIFT_OBJC_BRIDGING_HEADER`.
  Attempt r2 passed:
  `evidence/logs/eyebrow-rn-xcodebuild-device-cleanup-fallback-20260628-r2.log`.
  The built app bundle is `205M`, including `126M`
  `UnityFramework.framework` and `30M` `UnityFramework.framework/Data`.
- `devicectl` installed `com.celeste.makeupar.validation` on `CloudsiPhone`
  with
  `evidence/logs/eyebrow-rn-devicectl-install-cleanup-fallback-20260628-r1.log`.
  Automated launch was attempted but the iPhone was locked:
  `evidence/logs/eyebrow-rn-devicectl-launch-cleanup-fallback-20260628-r1.log`.

## QA Status

The latest installed iPhone build is the 2026-06-28 fallback-readiness brow
build from `RNDevice-eyebrow-cleanup-fallback-20260628-r2`. It installed on
`CloudsiPhone`, but automated launch was blocked because the iPhone was locked.
Product quality is still not accepted until the user opens the installed app or
launch is explicitly rerun, then visually checks FLAT readability versus
`Daily hair`/`Natural hair`/`Narrow hair`, hair texture fidelity, curve shape,
color, multiply-vs-normal behavior, preset switching, `soft_brow`, brow gap,
angle, arch, arch position, and tracking recovery.

## Risks

- Static UV brow masks may not match every user's natural eyebrow position.
- ARFace UV attachment should be stable, but visual quality still needs iPhone
  review under head turns and expressions.
- A first-loop mask may need several tuning passes for width, arch, and tail
  position.
- Full dedicated renderer separation is valuable but should be handled as a
  later refactor after brow is visible and testable.
