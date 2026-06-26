# E7 Reference-Driven UV Atlas Boundary Plan

Date: 2026-06-22 KST

Status: Next-session implementation plan / E7.03 region precision hardening

Owner intent: Replace the current manual-ellipse prototype with a reference-driven, measurable, one-build candidate sweep pipeline for `lip`, `cheek`, and `eye` region boundaries.

Document role:

- This `_KO.md` file is the primary implementation context for future agents.
- `E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KR.md` is a user-readable Korean companion document.
- If the two documents diverge, update this primary plan first, then mirror the decision into the KR companion.

## 1. Executive Decision

Current `e7-arface-authored-atlas` implementation should be treated as an `ARFace-only manual ellipse heuristic baseline`, not as a true authored UV atlas.

The next E7.03 path is:

```txt
clean synchronized capture frame + ARFace export
-> human-reviewed gold mask on that exact frame
-> ARFace projection and UV back-projection
-> per-region UV probability atlas
-> offline scoring and candidate pruning
-> one-build real-device candidate sweep
-> region G/Y/R decision
```

This plan does not promote product readiness. It only tries to answer whether `lip`, `cheek`, and `eye` boundaries are good enough for the next cosmetic-renderer experiment.

## Next Session Slice

The full P0-P9 plan is an E7.03 mini-project roadmap. The next implementation session should not attempt the whole roadmap.

Next session realistic scope:

1. P0 naming / contract reset.
2. Create `evidence/e7-reference-atlas/` skeleton and manifest schema.
3. Finalize the synchronized capture-pair contract.
4. Capture one `lip` validation pair from the same runtime moment: frame image, screen-space mesh, UVs, indices, blendshapes, and display metadata.
5. Draw one official `lip` gold mask on that synchronized frame.
6. Run one-frame round-trip: gold mask -> UV mask -> render back to the same frame.
7. Verify alignment before any multi-frame atlas, scorer, silver reference, or runtime candidate sweep work.

Stop rule:

- If the one-frame round-trip does not visually align with the gold mask, do not continue to multi-frame probability atlases, offline scoring, Unity/RN atlas sweep, or E7.03 Green claims.

## 2. Current State

Already proven:

- React Native host, Unity embedded screen, ARKit face tracking, RN -> Unity recipe dispatch, Unity -> RN events, and validation HUD/log paths exist.
- Real-device ARFace mesh/UV evidence exists. Prior logs observed mesh counts such as `1220` vertices, `6912` indices, and `1220` UVs.
- Phase 1 Clean / Compact HUD / Full Debug modes exist, and LogBox suppression was added for visual review.
- Phase 2 added region candidate metadata, `candidateId`, `variantId`, topology/UV evidence fields, and one-build candidate intent.

Known problem:

- The current "atlas" range is selected by face-local manual ellipses over ARFace vertices, not by a real grayscale UV atlas texture.
- It is a useful baseline for proving plumbing, but it does not solve per-person semantic boundary adaptation.
- It was not validated through a full multi-candidate evidence matrix.

Required correction:

- Rename the current implementation in docs and UI language as a heuristic baseline or prototype.
- Build the real primary path as `reference-driven UV atlas`, with generated mask assets and measurable candidate scores.

## 3. Scope Boundaries

In scope:

- `lip`, `cheek`, and `eye` only.
- Local-only validation, including representative frames, masks, logs, contact sheets, and scoring CSV/JSON.
- Direct digital annotation, open/reference segmentation masks, offline MediaPipe landmarks, offline face parsing references, and mathematical UV projection.
- ARFace mesh/UV runtime renderer and RN candidate sweep.
- E3/E4 baseline and current manual-ellipse heuristic preserved as compare-only paths.

Out of scope:

- E7.4 cosmetic renderer, E7.5 demo look, E7.6 final performance decision.
- Product-ready makeup, product-v1 readiness, M7 Green promotion.
- AI recommendation, backend upload, admin/payment/community work.
- Commercial SDK integration.
- Runtime MediaPipe, Apple Vision, or face parsing integration under the current E7.03 boundary.
- Android/ARCore implementation.
- Shipping or training on restricted dataset assets without license review.
- Raw camera-frame storage by default or off-device upload.

## 4. Mental Model

ARKit/ARFace gives a face-attached coordinate system:

```txt
detected human face
-> ARFace mesh vertices / indices / UVs / pose / blendshapes
-> face-attached surface
```

It does not give semantic makeup regions:

```txt
ARFace does not automatically say:
- exact lip color border
- eyelid crease
- blush-safe cheek zone
```

The missing layer is a region map:

```txt
semantic reference
-> UV-space region atlas
-> runtime region mask
```

The target architecture is:

```txt
ARFace mesh and UVs
+ region UV atlas
+ threshold / feather / morphology config
+ optional blendshape adaptation
+ tracking-state visibility rules
```

### 4.1 Data Role Map

Use this table to prevent confusing example/reference data with official atlas input.

| Data type | Has this app's synchronized ARFace mesh/UV export? | Has marking? | Role |
| --- | --- | --- | --- |
| Official app `frame.png` + `arface_export.json` + human-reviewed mask | Yes | Yes | Gold input for UV atlas generation and final region decisions |
| Official app `frame.png` + `arface_export.json` + model-generated mask or landmarks | Yes | Yes, generated | Silver reference for draft labeling, diagnosis, and candidate assistance; never Green by itself |
| External dataset image + external face parsing mask | No | Often yes | Taxonomy/example/reference only; not an official ARFace UV atlas input |
| Internet image, generic screenshot, or screen-recording-only frame | No | Maybe | Visual reference, scenario planning, or practice mask only |

External dataset masks may already mark lips, eyes, skin, or similar classes, but their markings belong to that dataset image coordinate system. They do not identify which triangles or UV coordinates in this app's ARFace mesh correspond to the region. Official gold masks must therefore be drawn on this app's clean synchronized capture frames.

## 5. Reference Sources

### 5.1 Gold Reference

Gold reference means human-reviewed masks on synchronized iPhone capture frames.

Use cases:

- Final judge for "is this acceptable makeup placement?"
- Prevents blindly treating MediaPipe or face parsing as cosmetic truth.
- Especially important for `cheek`, because public parsing datasets usually do not define "blush zone".

How to create:

- Use the existing screen recording only for visual failure review, scenario planning, and practice mask authoring.
- Capture official atlas-source frames from the app only when the same runtime event also exports the matching ARFace mesh, UVs, indices, blendshapes, and display metadata.
- Digitally mark `lip`, `cheek`, and `eye` using a local annotation tool, Figma, Photoshop, Procreate, CVAT, Label Studio, or equivalent.
- Export one binary or grayscale mask per region per frame.

Critical rule:

- A mask can become an official gold mask for UV atlas generation only if its frame has a valid synchronized capture pair. A screen-recording-only frame without matching ARFace export may be used for review or practice, but not for UV back-projection input.
- The official annotation frame must be clean: no ARFace mesh overlay, no region candidate overlay, no HUD/log text, no debug points/triangles, and no makeup/beauty texture. Mesh and debug views must be exported as separate derived files such as `projected_mesh_overlay.png`.

Minimum initial set:

- `lip`: 8 to 12 frames: neutral, smile, mouth open, mouth close, pucker, yaw left/right.
- `cheek`: 6 to 10 frames: neutral, smile, yaw, pitch, partial profile.
- `eye`: 8 to 12 frames: neutral, blink, squint, wide eye, gaze direction, pitch.

Gold mask authoring notes:

- `lip`: include visible lip surface only. Exclude teeth, inner mouth, tongue, chin, cheek, broad skin, and shadow-only areas. For open-mouth frames, mark the lip surface and leave the mouth hole outside.
- `cheek`: mark a makeup placement target, not an anatomical dataset class. Prefer a soft blush-safe zone around the cheek/apple area. Avoid nose folds, jaw, mouth corners, under-eye dark area, hair, and ears. A grayscale soft mask is preferred when evaluating blush falloff.
- `eye`: target a broad eyeshadow/eye tint zone, not eyeliner-grade precision. Exclude eyeball/iris/sclera, forehead above the intended eye area, cheek, nose bridge spill, and lower-face spill. Blink frames may have a narrower valid zone.

### 5.2 Silver Reference

Silver reference means model-generated masks or landmarks that are useful but not trusted as final truth.

Allowed references:

- MediaPipe Face Landmarker for landmarks, blendshapes, and facial transform matrices.
- SegFace or BiSeNet face parsing for pixel-level lip/eye/skin hints.
- CelebAMask-HQ and LaPa as taxonomy and offline parsing references.
- Apple Vision Face Landmarks as an optional iOS-native 2D contour sanity check.
- Detailed external-mask-prior planning lives in `docs/roadmaps/active/E7_EXTERNAL_MASK_PRIOR_SUBSPIKE_PLAN_KO.md`; it treats external masks only as silver draft inputs before human gold approval.

Rules:

- Use silver reference to propose masks, not to decide Green alone.
- Human review must override silver reference when makeup placement differs from raw anatomy.
- Record model/source/version/license notes for every generated reference.
- Split silver/reference roles explicitly:
  - External dataset masks are taxonomy/example material unless they are re-run or re-authored on this app's official frames.
  - Model outputs generated on this app's official synchronized frames may assist UV back-projection, but remain silver until human-reviewed into gold.

### 5.3 Shape and Product Benchmarks

Use as authoring inspiration only:

- Snap Face Mask and opacity texture workflow.
- TikTok Lip Effect, Lip Segmentation, and Face Paint concepts.
- ARCore Augmented Faces texture/mesh overlay pattern.
- Banuba/DeepAR/Perfect Corp public parameter categories as benchmark concepts only.

Do not:

- Copy platform-bound template assets into product code.
- Assume Snap/TikTok UV templates match Apple ARKit UVs.
- Use commercial SDKs in this validation path.

## 6. Data Artifacts

Suggested local artifact layout:

```txt
evidence/e7-reference-atlas/
  README.md
  manifest.json
  capture_pairs/
    pair_lip_0001/
      frame.png
      arface_export.json
      projected_mesh_overlay.png
      round_trip_overlay.png
  frames_practice/
    from_screen_recording/
  masks_gold/
    lip/pair_lip_0001.png
    cheek/
    eye/
  masks_silver/
    mediapipe/
    parsing/
    apple_vision/
  atlases/
    v0/
      lip_probability.png
      lip_coverage.png
      lip_unknown.png
      lip_debug_votes.png
      lip_variants.json
      cheek_probability.png
      cheek_variants.json
      eye_probability.png
      eye_variants.json
  scores/
    atlas_scores.csv
    atlas_scores.json
    offline_summary.md
  contact_sheets/
    p1_frame_pack.jpg
    p6_candidate_review.jpg
  splits/
    leave_one_frame_out.json
  forward_checks/
    uv_checkerboard_projection.jpg
```

All files under `evidence/` are generated/local evidence and should not be committed unless the repo policy explicitly changes.

Candidate assets that become source-of-truth Unity resources can later move into Unity assets, but only after the synchronized capture-pair, one-frame round-trip, and offline scoring loops prove they are worth runtime validation.

Critical capture-pair prerequisite:

- A frame can be used for UV atlas generation only if it has a matching ARFace export captured from the same runtime moment and the same display coordinate system.
- Valid atlas source pair:
  - clean frame image actually used for annotation,
  - `screenVertices` projected into the exact same pixel coordinate space,
  - `uvs` and `indices` from the same ARFace mesh,
  - orientation, mirroring, Unity view rect, screen/video resolution, safe-area, viewport/crop, and display transform metadata,
  - blendshape values from the same frame.
- Existing screen recordings without matching ARFace export may be used for visual review, scenario selection, or mask-authoring practice, but must not be treated as valid UV back-projection input.
- `frame.png` is the clean annotation frame. It must not include mesh, candidate mask, HUD/log text, debug markers, or beauty texture. Derived debug files such as `projected_mesh_overlay.png` may overlay mesh on the same frame for coordinate validation.

## 7. Runtime Export Contract

To build the UV atlas correctly, Unity must export enough data to map screen pixels back to ARFace UVs.

Minimum per-frame export:

```json
{
  "schemaVersion": "e7-arface-frame-export-v1",
  "frameId": "frame_0001",
  "timestampMs": 0,
  "deviceOrientation": "portrait",
  "screenWidth": 1179,
  "screenHeight": 2556,
  "videoFrameSize": [1179, 2556],
  "unityViewRectPx": [0, 0, 1179, 2556],
  "safeAreaPx": [0, 0, 1179, 2556],
  "screenCoordinateOrigin": "top-left",
  "isMirrored": true,
  "displayScale": 3.0,
  "annotationFrameClean": true,
  "hudIncludedInFrame": false,
  "meshOverlayIncludedInFrame": false,
  "candidateOverlayIncludedInFrame": false,
  "cameraImageToScreenMatrix": [16 floats],
  "displayTransform": [16 floats],
  "viewportCropPx": [0, 0, 1179, 2556],
  "cameraProjection": [16 floats],
  "cameraView": [16 floats],
  "faceLocalToWorld": [16 floats],
  "trackingState": "Tracking",
  "vertices": [[x, y, z]],
  "indices": [0, 1, 2],
  "uvs": [[u, v]],
  "screenVertices": [[xPx, yPx, depth, clipW]],
  "triangleVisibility": [{"triangleIndex": 0, "frontFacing": true, "visible": true}],
  "blendshapes": {
    "jawOpen": 0.0,
    "mouthSmileLeft": 0.0,
    "mouthSmileRight": 0.0,
    "mouthPucker": 0.0,
    "mouthFunnel": 0.0,
    "eyeBlinkLeft": 0.0,
    "eyeBlinkRight": 0.0,
    "eyeSquintLeft": 0.0,
    "eyeSquintRight": 0.0
  }
}
```

If exact camera matrices are difficult to export in the first pass, export a projected screen-space mesh instead:

```json
{
  "screenVertices": [[xPx, yPx, depth, clipW]],
  "uvs": [[u, v]],
  "indices": [0, 1, 2],
  "videoFrameSize": [1179, 2556],
  "unityViewRectPx": [0, 0, 1179, 2556],
  "screenCoordinateOrigin": "top-left",
  "isMirrored": true,
  "displayScale": 3.0,
  "annotationFrameClean": true,
  "hudIncludedInFrame": false,
  "meshOverlayIncludedInFrame": false,
  "candidateOverlayIncludedInFrame": false,
  "displayTransform": [16 floats]
}
```

The projected mesh path is simpler, but it is valid only when the frame image and export are captured from the same runtime moment and the same display coordinate space.

Required export metadata:

- `videoFrameSize`, `unityViewRectPx`, `safeAreaPx`, `screenCoordinateOrigin`, `isMirrored`, `displayScale`, `displayTransform` or `cameraImageToScreenMatrix`, and `viewportCropPx`.
- `annotationFrameClean`, `hudIncludedInFrame`, `meshOverlayIncludedInFrame`, and `candidateOverlayIncludedInFrame` must make it explicit that the official annotation frame is clean.
- `screenVertices` must include enough depth or clip-space information for perspective-correct interpolation. Prefer `clipW` or a GPU-rendered triangle-id/UV buffer over depth-only correction.
- Official atlas-source frames must be captured in the same runtime event as the ARFace export. Screen-recording-only frames are review/practice material only.

## 8. UV Back-Projection Algorithm

Goal:

```txt
2D reference mask on iPhone frame
-> ARFace triangle in screen space
-> barycentric coordinate inside triangle
-> ARFace UV coordinate
-> UV probability atlas vote
```

Algorithm:

1. Load selected frame image and reference mask.
2. Load matching ARFace export with `screenVertices`, `indices`, and `uvs`.
3. For each triangle:
   - Get its three screen-space vertices.
   - Reject triangles that are back-facing, occluded, outside the active Unity view rect, or below the grazing-angle confidence threshold.
   - Rasterize or sample pixels inside the screen triangle.
   - For overlapping triangles, count votes only from the front-most visible triangle using depth test, triangle-id buffer, or an equivalent visibility pass.
   - For each sampled pixel, check whether the reference mask is positive.
   - Compute barycentric weights `(w0, w1, w2)`.
   - Compute UV with perspective-correct interpolation when using screen-space barycentrics. If `clipW` is unavailable, prefer a Unity-rendered UV buffer over ad hoc depth correction.
   - Accumulate positive or negative votes into UV atlas bins.
4. Repeat across all frames.
5. Normalize probability:
   - `p(region | uv) = positiveVotes / max(1, totalVotes)`.
6. Generate mask variants:
   - different thresholds,
   - different dilation/erosion,
   - different feather distances,
   - region-specific smoothing.

Implementation notes:

- Use supersampling or triangle rasterization to avoid sparse votes, but do not treat supersampling as a fix for grazing-angle geometry.
- Weight or reject samples using projected triangle area and/or `abs(normal dot viewDir)`. Silhouette and side-facing triangles should not dominate cheek/yaw votes.
- Back-facing or occluded triangles must not contribute positive or negative votes.
- Store vote count maps as debug images to reveal UV holes.
- Run a one-frame round-trip before any batch atlas generation:
  1. draw one accepted gold mask on one synchronized `lip` frame,
  2. back-project it into UV space,
  3. render the generated UV mask back onto the same frame using the same mesh,
  4. visually compare against the gold mask.
- Add a forward-projection sanity check by rendering a known UV pattern, such as a checkerboard or single-triangle mask, back to screen space.
- Treat low-vote UV regions as unknown, not negative.
- Keep left/right symmetry optional; do not force it if real evidence shows asymmetry.

## 9. Candidate Config Contract

Use a data file instead of hard-coded C# ellipse constants.

Example:

```json
{
  "schemaVersion": "e7-region-atlas-candidates-v1",
  "atlasVersion": "reference-driven-uv-atlas-v0",
  "candidates": [
    {
      "candidateId": "arface-reference-uv-atlas",
      "variantId": "lip-refuv-v0-p75-f04px",
      "region": "lip",
      "probabilityAtlas": "lip_probability_v0.png",
      "binaryMaskAsset": "lip_mask_v0.png",
      "uvResolution": [512, 512],
      "threshold": 0.75,
      "featherUvPixels": 4,
      "featherUvNormalized": 0.0078125,
      "regionUvFootprint": {
        "widthPixels": 64,
        "heightPixels": 28
      },
      "morphology": "none",
      "blendshapeRuleId": "lip-jaw-smile-v0",
      "source": {
        "goldFrames": 10,
        "silverRefs": ["mediapipe-face-landmarker", "face-parsing-review"],
        "manualReview": true
      }
    }
  ]
}
```

Runtime should support:

- `candidateId`
- `variantId`
- `region`
- `threshold`
- `uvResolution`
- `featherUvPixels`
- `featherUvNormalized`
- `regionUvFootprint`
- `probabilityAtlas`
- `binaryMaskAsset`
- `atlasVersion`
- `source/reference metadata`

## 10. Scoring Metrics

For each frame and region:

```txt
TP = candidate positive and reference positive
FP = candidate positive and reference negative
FN = candidate negative and reference positive

precision = TP / (TP + FP)
recall = TP / (TP + FN)
IoU = TP / (TP + FP + FN)
leakage = FP / candidatePositive
miss = FN / referencePositive
```

Temporal metrics:

```txt
centroidJitter = mean distance between consecutive candidate centroids
areaJitter = mean absolute area delta between consecutive frames
edgeJitter = mean boundary displacement where measurable
```

Normalize distances by a face scale such as eye distance, face width, or ARFace bounding size.

Evaluation split:

- Do not score only on the same gold masks used to generate the atlas.
- Use leave-one-frame-out when the frame count is small.
- At minimum, label offline scores as `calibrationScore` when they are measured on atlas-generation frames, and reserve `evalScore` for held-out frames.
- The one-frame round-trip test is a projection sanity check, not region precision performance evidence.

Jitter interpretation:

- Temporal jitter metrics are pre-smoothing metrics unless a smoothing pass is explicitly enabled.
- One Euro filtering is a future stabilization candidate, not a required E7.03 atlas-generation dependency.

Region-specific scoring:

- `lip`
  - Highest weight: precision and leakage.
  - Strong penalties for spill into skin, teeth, and inner mouth.
  - Moderate penalty for small misses at corners or cupid's bow.
- `cheek`
  - Highest weight: centroid placement, symmetry, soft falloff, and low hard-edge visibility.
  - IoU is less important because blush is intentionally soft.
  - Spill toward jaw, nose fold, and under-eye is penalized.
  - Prefer soft grayscale metrics:
    - `cheekWeightedError = mean(abs(candidateAlpha - goldSoftMask))`.
    - `cheekCenterDistance = normalized distance(candidateCentroid, goldCentroid)`.
    - `cheekHardEdgePenalty = boundaryGradientTooSharpArea`.
- `eye`
  - Highest weight: non-eye spill and temporal stability during blink/squint.
  - Target is broad eyeshadow/eye tint, not eyeliner-grade precision.
  - Spill into forehead, mouth, cheek, or eyeball region is Red-risk.

Suggested first-pass pass bars:

```txt
lip: precision >= 0.80, leakage <= 0.15, visual review no severe skin/teeth spill
cheek: visual soft-zone pass, centroid stable, no jaw/nose/under-eye overrun
eye: broad zone plausible, no large forehead/lower-face spill, blink drift acceptable
```

These bars are starting points and must be revised from actual gold reference quality.

## 11. Adaptive Correction

Do not try to filter or morph the entire ARFace mesh.

Apply correction only to low-dimensional region parameters:

- mask threshold,
- alpha,
- feather,
- local scale,
- local offset,
- visibility state,
- small region anchor positions.

### Lip rules

Inputs:

- `jawOpen`
- `mouthSmileLeft/Right`
- `mouthPucker`
- `mouthFunnel`
- `mouthStretchLeft/Right` if available

First-pass behavior:

- Increase inner-mouth caution when `jawOpen` rises.
- Slightly reduce lower lip coverage when mouth is open if teeth/inner-mouth spill is observed.
- Slightly expand horizontal tolerance during smile only if corner gaps appear.
- Do not use blendshapes to create new semantic boundaries; only modulate an already-good atlas.

### Eye rules

Inputs:

- `eyeBlinkLeft/Right`
- `eyeSquintLeft/Right`
- `eyeWideLeft/Right`
- eye pose if available

First-pass behavior:

- Fade or narrow eyeshadow alpha during blink to avoid visible collapse.
- Avoid hard lash-line precision goals.
- Keep target as broad upper-lid/soft halo validation.

### Cheek rules

Inputs:

- face width or ARFace bounding scale,
- cheek anchor/centroid,
- smile/cheek squint if reliable.

First-pass behavior:

- Keep a soft broad zone.
- Prefer feather and centroid tuning over semantic segmentation.
- Avoid hard cheek borders.

## 12. Candidate Ladder

Use this ladder to prevent jumping to expensive runtime ML too early.

| Level | Candidate | Role | Promotion rule |
| --- | --- | --- | --- |
| H0 | E3/E4 broad baseline | Compare-only | Never E7.03 Green |
| H1 | Current manual ellipse prototype | Heuristic baseline | Compare-only after this plan starts |
| H2 | Static reference-driven UV atlas | Primary next candidate | Promote if offline scores beat H1 |
| H3 | UV atlas + threshold/feather variants | Primary tuning set | Promote top variants to runtime sweep |
| H4 | UV atlas + blendshape correction | Best ARFace-only candidate | Use where H3 fails under expression |
| H5 | Offline third-party reference-assisted atlas | Offline correction path | Use MediaPipe or face parsing references for failing `lip` or `eye`; Apple Vision remains research-only under E7.03 |
| H6 | Runtime semantic hybrid POC | Future milestone only | Not part of this E7.03 plan; open only if the user explicitly changes the boundary |

## 13. Prioritized Implementation Milestones

Execute these milestones in priority order. Do not start a lower-priority milestone when its prerequisite evidence is missing.

| Priority | Milestone | Goal | Build needed? | Stop / promote rule |
| --- | --- | --- | --- | --- |
| P0 | Contract and naming reset | Make the current atlas status unambiguous | No | Current atlas is documented/UI-labeled as heuristic baseline |
| P1 | Capture-pair contract and artifact skeleton | Define valid atlas inputs before masking | No | Manifest distinguishes practice frames from official synchronized pairs |
| P2 | Synchronized `lip` capture export | Capture one official frame + ARFace export pair | Yes, only after Build Gate | Frame, mesh, UV, indices, blendshapes, and display metadata share one runtime moment |
| P3 | Official `lip` gold mask | Draw one mask on the synchronized frame | No | Mask dimensions and coordinate space match the captured frame |
| P4 | One-frame round-trip | Prove projection math before batch work | No after P2/P3 | Gold mask -> UV -> same-frame render visually aligns |
| P5 | UV atlas generator | Generalize the validated round-trip path | No | Probability/coverage/unknown/debug outputs exist |
| P6 | Offline scorer and optimizer | Rank candidates without train-on-test confusion | No | Leave-one-frame-out or split-labeled scores exist |
| P7 | Offline silver/reference pass | Add optional draft references without runtime scope creep | No | Silver references are non-authoritative and license-noted |
| P8 | Unity/RN atlas sweep implementation | Run frozen candidates in one build | Yes, only after candidate list freezes | One build can sweep variants and log evidence |
| P9 | Real-device decision and escalation | Record region G/Y/R and next boundary | No extra build unless P8 fails structurally | `TECH_VALIDATION_RESULT.md` records result/limits/boundary |

### P0: Contract and naming reset

Purpose:

- Stop calling the current manual ellipse implementation a true authored atlas.
- Preserve it as a comparison baseline so future improvements are measured, not guessed.

Edit targets:

- `TECH_VALIDATION_RESULT.md`: next-session result language when this plan is executed.
- `docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md`: primary agent implementation contract.
- `docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KR.md`: user-readable companion document.
- `rn/MakeupARValidation/App.tsx`: UI labels only if current labels imply a true atlas.
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`: runtime metadata strings only if needed.

Required implementation details:

- Rename user-facing / evidence language from `authored atlas` to `manual ellipse heuristic` or `ARFace-only heuristic baseline` where precision matters.
- Keep renderer identifiers stable if changing them would break existing recipe dispatch or logs; prefer display-label changes over schema churn.
- Preserve `e3e4-baseline`, `e7-arface-uv-candidate`, RN -> Unity recipe dispatch, Unity -> RN events, Phase 1 HUD/LogBox behavior, and current evidence fields.

Verification:

- `rg -n "authored atlas|manual ellipse|heuristic baseline|e7-arface-authored-atlas" TECH_VALIDATION_RESULT.md docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md docs/roadmaps/active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KR.md rn/MakeupARValidation/App.tsx unity/MakeupARUnityValidation/Assets/Scripts`
- From `rn/MakeupARValidation`: `./node_modules/.bin/tsc --noEmit`
- From `rn/MakeupARValidation`: `npm run lint`

Exit criteria:

- A reviewer can tell which path is baseline, which path is the new reference-driven atlas, and which paths are future-only.

### P1: Capture-pair contract and artifact skeleton

Purpose:

- Make it impossible to accidentally treat a screen-recording-only frame as UV atlas input.
- Define the local artifact shape before official mask authoring begins.

Target artifact layout:

```txt
evidence/e7-reference-atlas/
  README.md
  manifest.json
  capture_pairs/
    pair_lip_0001/
      frame.png
      arface_export.json
      projected_mesh_overlay.png
      round_trip_overlay.png
  frames_practice/
    from_screen_recording/
  masks_gold/
    lip/pair_lip_0001.png
  masks_silver/
    mediapipe/
    parsing/
    apple_vision/
  atlases/
    v0/
      lip_probability.png
      lip_variants.json
      cheek_probability.png
      cheek_variants.json
      eye_probability.png
      eye_variants.json
  scores/
    atlas_scores.csv
    atlas_scores.json
  contact_sheets/
    p1_frame_pack.jpg
    p6_candidate_review.jpg
```

`manifest.json` minimum fields:

```json
{
  "planId": "e7-reference-driven-uv-atlas",
  "atlasVersion": "e7ref-v0",
  "privacy": {
    "selectedValidationFrameStored": true,
    "rawRecordingStored": false,
    "offDeviceUpload": false
  },
  "capturePairs": [
    {
      "capturePairId": "pair_lip_0001",
      "region": "lip",
      "source": "synchronized_runtime_capture",
      "scenario": "neutral_or_talking",
      "framePath": "capture_pairs/pair_lip_0001/frame.png",
      "arfaceExportPath": "capture_pairs/pair_lip_0001/arface_export.json",
      "goldMaskPath": "masks_gold/lip/pair_lip_0001.png",
      "projectedMeshOverlayPath": "capture_pairs/pair_lip_0001/projected_mesh_overlay.png",
      "annotationFrameClean": true,
      "hudIncludedInFrame": false,
      "meshOverlayIncludedInFrame": false,
      "candidateOverlayIncludedInFrame": false,
      "status": "synced_capture_pending",
      "coordinateSpaceValidated": false,
      "roundTripStatus": "not_run"
    }
  ]
}
```

Required implementation details:

- Use the existing user-provided recording only for failure review, scenario planning, and practice masks.
- Use stable `capturePairId` values for official atlas inputs. Never key artifacts only by timestamp.
- Add frame statuses: `practice_from_recording`, `synced_capture_pending`, `synced_capture_valid`, `gold_mask_accepted`, `round_trip_passed`, `rejected`.
- Store official annotation frames only as clean selected validation frames. Do not store mesh/HUD/candidate/debug overlays inside `frame.png`; store those as derived files.
- Keep raw recording outside repo unless a milestone explicitly requires storing it.
- Store representative derived frames only under `evidence/`, and document whether they should be retained or deleted after scoring.

Verification:

- `python3 -m json.tool evidence/e7-reference-atlas/manifest.json`
- `find evidence/e7-reference-atlas -maxdepth 3 -type f`
- Manual check that no `.mov`-only frame is marked `synced_capture_valid`.
- Manual check that each official pair has region, scenario, coordinate metadata, and privacy metadata.
- Manual check that every official `frame.png` is clean enough for human masking and every mesh/debug overlay is stored separately.

Exit criteria:

- A future session can tell which frames are practice/review material and which synchronized pairs are valid atlas inputs.

### P2: Synchronized `lip` capture export

Purpose:

- Capture one official `lip` source pair before any official gold mask or atlas generation.

Build policy:

- This milestone may require Unity/RN changes and a real-device build.
- Stop at Build Gate and state that the build purpose is `synchronized capture / one-frame round-trip`, not runtime candidate sweep.
- If an installed build already exports the required pair, reuse it and skip rebuild.

Required implementation details:

- Export validation-only data from the same runtime moment:
  - clean frame image used for annotation, with no mesh, HUD, candidate overlay, debug points, or makeup texture,
  - `screenVertices`, `uvs`, `indices`,
  - vertex/index/UV counts,
  - blendshapes,
  - `videoFrameSize`, `unityViewRectPx`, `safeAreaPx`, `screenCoordinateOrigin`, `isMirrored`, `displayScale`, `displayTransform` or `cameraImageToScreenMatrix`, `viewportCropPx`,
  - `clipW` or equivalent perspective-correction value when using screen-space interpolation,
  - visibility data or enough depth/triangle-id information to recover front-most triangles.
- Also export derived debug files separately, especially `projected_mesh_overlay.png`, so coordinate alignment can be checked without polluting the annotation frame.
- Keep raw capture bounded to the selected validation event.
- Emit export success/failure through existing RN event paths.

Verification:

- Overlay exported mesh over the exact captured frame.
- Verify face outline, lips, eyes, and key contours align in the same pixel coordinate space.
- Confirm `frame.png` itself remains clean enough to see real lip, eye, and cheek boundaries.
- Confirm current device shape is plausible, for example around `1220` vertices / `6912` indices / `1220` UVs where supported.

Exit criteria:

- One `lip` pair is marked `synced_capture_valid` and `coordinateSpaceValidated=true`.

### P3: Official `lip` gold mask

Purpose:

- Draw the first official gold mask only after P2 proves the frame/export pair is valid.

Required implementation details:

- Draw on `capture_pairs/pair_lip_0001/frame.png`, not on a `.mov`-only practice frame.
- Do not draw on `projected_mesh_overlay.png` or any screenshot that already contains mesh/debug/HUD overlays.
- Export the mask at the exact same pixel dimensions as the captured frame.
- Mark teeth, inner mouth, chin, cheek, and broad skin as outside.
- Record author, tool, date, frame id, and review status in `manifest.json`.
- Use `draft`, `reviewed`, `accepted`, `rejected`.

Verification:

- Overlay the mask on the synchronized frame.
- Reject masks with dimension mismatch, empty coverage, full-frame coverage, or obvious coordinate offset.
- Reject masks authored from mesh-covered frames when the real boundary is not visible enough to judge.

Exit criteria:

- One `lip` gold mask is `accepted` for one synchronized capture pair.

### P4: One-frame round-trip

Purpose:

- Prove projection math before multi-frame atlas generation or scoring.

Required implementation details:

- Back-project the accepted `lip` gold mask into UV space.
- Render the generated UV mask back onto the same frame using the same mesh/export.
- Compare against the original gold mask.
- Run a forward-projection sanity check with a known UV checkerboard or single-triangle pattern.

Verification:

- Create `capture_pairs/pair_lip_0001/round_trip_overlay.png`.
- Record whether mismatch is caused by coordinate transform, mirroring, perspective interpolation, visibility/depth, grazing-angle rejection, or mask authoring.

Exit criteria:

- Round-trip visually aligns well enough to justify batch atlas generation.

### P5: UV atlas generator

Purpose:

- Generalize the validated one-frame round-trip path into UV-space probability atlases.

Suggested script target:

- `scripts/e7_reference_atlas/generate_uv_atlas.py`

Inputs:

- `manifest.json`
- `capture_pairs/*/frame.png`
- `masks_gold/<region>/*.png`
- `capture_pairs/*/arface_export.json`
- Optional `masks_silver/**`

Outputs:

- `atlases/v0/<region>_probability.png`
- `atlases/v0/<region>_coverage.png`
- `atlases/v0/<region>_unknown.png`
- `atlases/v0/<region>_debug_votes.png`
- `atlases/v0/<region>_atlas_meta.json`

Algorithm requirements:

- Use only `synced_capture_valid` pairs.
- For each visible ARFace triangle, test source-frame pixels inside its projected screen-space triangle.
- For each sampled pixel, compute barycentric coordinates in screen space.
- Interpolate UV using perspective-correct interpolation or a Unity-rendered UV/triangle-id buffer.
- Count votes only from the front-most visible triangle.
- Reject or down-weight back-facing, occluded, tiny projected-area, and grazing-angle triangles.
- Accumulate positive votes where the gold mask is inside the region and negative votes where it is outside.
- Write probability as `positiveVotes / totalVotes`.
- Track unknown UV texels separately; do not silently treat unknown as negative.
- Supersample or rasterize triangles densely enough that thin lip/eye regions are not lost.

`<region>_atlas_meta.json` minimum fields:

```json
{
  "atlasVersion": "e7ref-v0",
  "region": "lip",
  "sourceFrameIds": ["frame_lip_0001"],
  "goldMaskCount": 5,
  "silverReferenceCount": 0,
  "uvResolution": [512, 512],
  "positiveVoteCount": 12345,
  "negativeVoteCount": 67890,
  "unknownTexelRatio": 0.42,
  "generator": "scripts/e7_reference_atlas/generate_uv_atlas.py"
}
```

Verification:

- Run the one-frame round-trip before batch mode.
- Inspect `debug_votes` and `coverage` images before trusting the probability atlas.
- Confirm unknown regions are visibly separate from excluded regions.

Exit criteria:

- `lip` has probability, coverage, unknown, and debug vote images generated from valid synchronized pairs.

### P6: Offline scorer and candidate optimizer

Purpose:

- Narrow many possible atlas thresholds into a small runtime candidate set while separating calibration scores from evaluation scores.

Suggested script target:

- `scripts/e7_reference_atlas/score_atlas_candidates.py`

Candidate sweep dimensions:

- Threshold: region-specific, for example `0.35`, `0.45`, `0.55`, `0.65`, `0.75`.
- Feather radius: `0`, `2`, `4`, `8`, `12` UV pixels.
- Morphology: none, close-small-holes, erode-one, dilate-one.
- Region-specific clamp:
  - `lip`: prefer high precision and low leakage.
  - `cheek`: prefer soft coverage and low hard-edge penalty.
  - `eye`: prefer no lower-face spill and blink-safe behavior.
- Evaluation split:
  - Use leave-one-frame-out when the frame count is small.
  - Label scores as `calibrationScore` when measured on atlas-generation frames.
  - Label scores as `evalScore` only when measured on held-out frames.

Outputs:

- `scores/atlas_scores.csv`
- `scores/atlas_scores.json`
- `contact_sheets/p6_candidate_review.jpg`
- `atlases/v0/runtime_candidates.json`

`runtime_candidates.json` minimum fields:

```json
{
  "atlasVersion": "e7ref-v0",
  "candidates": [
    {
      "candidateId": "lip_uvatlas_v0_precision",
      "region": "lip",
      "probabilityAtlas": "lip_probability.png",
      "threshold": 0.65,
      "featherUvPixels": 2,
      "uvResolution": [512, 512],
      "featherUvNormalized": 0.00390625,
      "regionUvFootprint": {
        "widthPixels": 64,
        "heightPixels": 28
      },
      "morphology": "erode-one",
      "calibrationScore": {
        "precision": 0.84,
        "recall": 0.62,
        "iou": 0.56,
        "leakage": 0.11
      },
      "evalScore": null,
      "promotionReason": "best leakage-controlled lip candidate"
    }
  ]
}
```

Promotion limits:

- Promote no more than 2 to 4 variants per region into the runtime build.
- Include one conservative, one balanced, and optionally one wide candidate per region.
- Keep H0/H1 baselines as compare-only paths.

Verification:

- Scores must be reproducible from checked manifest/artifacts.
- Contact sheet must show source frame, gold mask, candidate overlay, false positives, and false negatives.
- Manual visual review may veto a high metric candidate if it looks cosmetically implausible.
- Cheek candidates must include soft-target metrics before promotion: `cheekWeightedError`, `cheekCenterDistance`, and `cheekHardEdgePenalty`.
- Temporal jitter scores are pre-smoothing metrics unless a smoothing pass is explicitly enabled.

Exit criteria:

- Runtime candidates are promoted by reproducible scores and visual review, not by constants or train-on-test numbers alone.

### P7: Offline silver/reference pass

Purpose:

- Add optional draft references without introducing runtime ML.

Required implementation details:

- MediaPipe, face parsing, and Apple Vision outputs remain offline reference material only.
- LaPa, BiSeNet, SegFace, CelebAMask-HQ, and any pretrained outputs remain reference-only until license review.
- Every silver artifact records source, version, command/tool, license note, and human review status.
- Do not use silver masks to mark E7.03 Green.
- Do not add runtime MediaPipe, runtime Apple Vision, live face parsing, new camera sessions, upload, or backend paths.

Exit criteria:

- Silver references can assist labeling or diagnosis, but gold masks remain the decision authority.

### P8: Unity/RN atlas sweep implementation

Purpose:

- Load frozen, evidence-backed atlas candidates in Unity and sweep them from RN in one build.

Build policy:

- Stop at Build Gate and state that the build purpose is `runtime candidate sweep`.
- Bundle all selected runtime candidates in one build.
- Do not begin P8 until P4 passes and P6 freezes a small candidate list.

Unity asset targets:

- Prefer `unity/MakeupARUnityValidation/Assets/Resources/E7ReferenceAtlas/<atlasVersion>/` for build-bundled validation assets.
- Include probability PNGs and `runtime_candidates.json`.
- Do not copy public dataset assets or third-party templates into Unity assets.

Unity code targets:

- `E3RegionMaskOverlay.cs`: add true UV atlas texture sampling path.
- `RNBridge.cs`: accept candidate/variant dispatch and emit atlas evidence metadata.
- `FaceTrackingStatusReporter.cs`: preserve E7 metric/event behavior.

RN code target:

- `rn/MakeupARValidation/App.tsx`: expose selected atlas candidate, variant, and region in Compact HUD without covering the face.

Runtime metadata requirements:

- `rendererMode`
- `candidateId`
- `variantId`
- `atlasVersion`
- `region`
- `atlasSourceFrameCount`
- `goldMaskCount`
- `silverReferenceCount`
- `uvResolution`
- `threshold`
- `featherUvPixels`
- `featherUvNormalized`
- `morphology`
- `calibrationScore` or `evalScore`
- `fallback`
- `fallbackReason`
- `trackingState`
- `stateAction`
- `vertexCount`
- `indexCount`
- `uvCount`

Verification before device run:

- From `rn/MakeupARValidation`: `./node_modules/.bin/tsc --noEmit`
- From `rn/MakeupARValidation`: `npm run lint`
- `git diff --check`
- Confirm Unity asset paths are included in the Unity project and not under ignored build/cache folders.

Exit criteria:

- One installed app can switch `lip`, `cheek`, and `eye` atlas variants from RN and emit full evidence metadata.

### P9: Real-device decision and escalation

Purpose:

- Produce the evidence needed to decide whether E7.03 can go Green, stays Yellow, or needs a different boundary.

Run sequence:

1. Stop and present Build Gate.
2. After approval, run `bash scripts/build_m3_unityframework.sh` from repo root if Unity assets/code changed.
3. From `rn/MakeupARValidation`, run `npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK`.
4. Capture full runtime console stream to `evidence/logs/`.
5. Capture representative screenshots/recording only as needed for region/motion evidence.
6. Produce contact sheets and region G/Y/R notes.

Evidence requirements:

- Runtime log has `region_precision_atlas` or equivalent atlas evidence events.
- Each region has representative visual evidence for at least one promoted candidate.
- Compare-only H0/H1 evidence remains available but is not used as Green proof.
- FPS/frame-time can be logged, but do not promote E7.6 performance from this pass.

Region decision rules:

- `lip` Green only if no severe skin/teeth/inner-mouth spill in required scenarios.
- `cheek` Green only if the soft blush zone is face-attached and does not look like a hard segmentation error.
- `eye` Green only if broad eye/eyeshadow placement remains plausible and does not spill to lower face.
- Overall E7.03 Green requires all three regions to be Q3 overlay-ready.

Exit criteria:

- `TECH_VALIDATION_RESULT.md` records command evidence, visual evidence, region G/Y/R, limitations, and next boundary.

Escalation ladder:

1. If `cheek` fails, tune atlas feather/centroid/shape envelope first.
2. If `lip` fails due to skin/teeth/inner-mouth spill, add offline MediaPipe or face parsing reference assistance.
3. If `eye` fails under blink/squint, add blink fade and compare offline landmarks/parsing before proposing runtime hybrid.
4. If ARFace-only fails after P5/P6/P8 evidence, write a new boundary proposal for a targeted runtime semantic POC.

Hard limits:

- Runtime MediaPipe, Apple Vision, or face parsing POC is not allowed in this plan.
- E7.4/E7.5/E7.6 remain blocked unless E7.03 is Green or the team explicitly accepts the remaining E7.3 Yellow risk, records the boundary in `TECH_VALIDATION_RESULT.md`, and treats later renderer/demo evidence as conditional with full E7 visual product-readiness capped at Yellow.
- Do not claim product-quality makeup, M7 Green, AI/backend readiness, SDK readiness, Android readiness, or product readiness from this plan.

Escalation exit criteria:

- The next boundary is one of:
  - continue ARFace UV atlas hardening,
  - add offline reference-assisted correction,
  - write a separate runtime semantic POC plan,
  - close E7.3 Yellow with recorded risk.

## 14. Build Gate Contract

No Unity/RN real-device build starts until this checklist is answered:

```txt
Build question:
Build purpose: synchronized capture / one-frame round-trip / runtime candidate sweep
Primary experiment path:
Compare-only paths:
Validation contract:
Synchronized capture-pair contract:
Clean annotation frame contract:
Candidate matrix:
Expected runtime fields:
Expected visual evidence:
Out-of-scope items:
Why one build is enough:
```

For this plan, a valid build question should look like:

```txt
Can this build capture one synchronized lip source pair and prove the
one-frame round-trip before any multi-frame atlas or runtime candidate sweep,
while preserving RN <-> Unity recipe/events and E3/E4 compare baselines?
```

Later, after P4 and P6 pass, a runtime sweep build question may change to:

```txt
Can the frozen reference-driven UV atlas candidates keep lip, cheek, and eye
masks face-attached and semantically plausible enough for Q3 region precision
in one install, while preserving RN <-> Unity recipe/events and E3/E4 baselines?
```

## 15. Acceptance Criteria

### Offline acceptance

- For the next session, one synchronized `lip` capture pair exists before any official gold mask.
- The official annotation `frame.png` is clean, while mesh/HUD/candidate/debug overlays are stored as separate derived files.
- The one-frame `lip` round-trip passes before batch atlas generation.
- Later full E7.03 offline acceptance requires gold reference mask packs for each in-scope region.
- Offline scorer outputs metrics and contact sheets.
- Top runtime candidates are selected by score and visual review, not by code constants alone.
- Current manual ellipse candidate is measured as compare-only.
- Calibration scores and held-out evaluation scores are labeled separately.

### Runtime acceptance

- Real-device app can switch selected atlas variants without rebuilding.
- Compact HUD exposes region and atlas variant clearly enough for recording.
- Unity logs include candidate, variant, atlas version, topology/UV status, region, tracking state, and fallback reason.
- Representative visual evidence exists for all three regions.

### E7.03 decision acceptance

- Region decisions are separate: `lip`, `cheek`, `eye`.
- Green requires Q3 for all three regions.
- Yellow must name exact blockers and next boundary.
- Red must name whether the failure is tracking, mask representation, semantic reference, expression handling, or lifecycle.

## 16. Test Matrix

| Region | Required scenarios | Must observe |
| --- | --- | --- |
| lip | neutral, smile, open/close, pucker, yaw | no severe skin/teeth/inner-mouth spill |
| cheek | neutral, smile, yaw, pitch, near/far | soft face-attached blush zone, no hard edge |
| eye | neutral, blink, squint, wide eye, gaze, pitch | broad eye zone remains plausible, no lower-face spill |
| lifecycle | tracking, Limited/lost, recovered | fade/hold/recover behavior is logged and visually controlled |
| integration | recipe dispatch, event ack, HUD | no regression to Phase 1, M6, E3/E4 paths |

## 17. Risks and Mitigations

| Risk | Impact | Mitigation |
| --- | --- | --- |
| Screen recording frame lacks matching ARFace export | Invalid UV votes | Use `.mov` only for review/practice; official atlas input requires synchronized capture pair |
| External dataset mask is treated as official atlas input | Invalid ARFace UV mapping | Use external masks only as taxonomy/examples unless generated or re-authored on this app's synchronized frame |
| Mesh/HUD/debug overlay hides the real lip, eye, or cheek boundary | Noisy or biased gold masks | Keep official `frame.png` clean and export mesh/debug overlays only as separate derived files |
| Coordinate transform, mirroring, viewport, or safe-area mismatch | Round-trip fails even with good masks | Capture display metadata and require mesh overlay plus one-frame round-trip |
| Train-on-test offline scoring | Over-optimistic candidate scores | Use leave-one-frame-out or clearly label calibration vs eval scores |
| Perspective-incorrect UV interpolation | Boundary drift on close/selfie geometry | Use `clipW` perspective-correct interpolation or Unity-rendered UV/triangle-id buffer |
| Occluded/back-facing triangles vote | Atlas polluted under yaw/profile | Vote only front-most visible triangles; reject back-facing/occluded triangles |
| Grazing-angle triangles are unstable | Cheek/yaw coverage becomes noisy | Weight/reject by projected area or `abs(normal dot viewDir)` |
| Gold masks are slow to create | Delays atlas generation | Start with 5 to 10 frames per region and use silver references as drafts |
| Silver reference is wrong | Bad atlas if trusted blindly | Human acceptance envelope overrides model output |
| ARFace projection export is inaccurate | UV atlas votes become wrong | First validate with a debug checker: projected mesh over frame |
| UV coverage is sparse | Holes in atlas | Accumulate valid synchronized frames, preserve unknown regions, and inspect coverage maps |
| Lip still spills | Blocks Q3 | Add blendshape correction, then MediaPipe/face parsing reference |
| Eye remains unstable | Blocks Q3 | Narrow to broad eyeshadow target, add blink fade, then semantic reference |
| Cheek has no dataset class | Ambiguous target | Define gold makeup placement manually, use soft-zone criteria |
| Runtime ML seems tempting | Scope creep | Keep ML as offline reference until evidence justifies a targeted POC |
| Evidence exposes face images | Privacy concern | Keep local, minimize frames, delete raw recordings after extraction if no longer needed |

## 18. Source and License Notes

Local governance and boundary sources:

- `AGENTS.md`: repo scope, evidence policy, document rules, build loop, E7 boundary constraints, and out-of-scope guardrails.
- `TECH_VALIDATION_RESULT.md`: Current Session Snapshot, E7.3 Yellow status, region G/Y/R decisions, evidence paths, stop rules, and next boundary.
- `TECH_VALIDATION_TEST_PLAN.md`: stable validation/evidence contract reference only; do not edit unless the validation contract itself changes.
- `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`: active E7.03 / E7.3 v2.1 boundary engine plan and Q3 overlay-ready acceptance standard.
- `E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md`: E7 master spike boundary; used only to keep E7.4/E7.5/E7.6 out of this plan.
- `E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md`: E7.6 performance boundary; used only to prevent performance Green claims from E7.03 evidence.

Local research and benchmark sources:

- `docs/roadmaps/research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md`: beauty AR platform patterns, face mask / face paint / segmentation benchmark context, and SDK boundary context.
- `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_GPT.md`: region tracking research synthesis for E7 axis 1.
- `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_CLAUDE.md`: second-pass region tracking synthesis for E7 axis 1.

Local session/evidence source material:

- `evidence/logs/e7-region-precision-video-analysis-2026-06-22.md`: prior screen-recording analysis and current `lip` Red / `eye` Red / `cheek` Yellow basis.
- `evidence/screenshots/e7-region-precision-video-analysis-2026-06-22/contact-sheet-1fps.jpg`: representative visual review contact sheet.
- `/Users/wiseungcheol/Downloads/ScreenRecording_06-22-2026 19-52-46_1.mov`: user-provided raw recording referenced as local source material only; do not copy into repo or retain derived frames beyond evidence policy without need.

External AR/runtime references:

- Unity AR Foundation `ARFace`: https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.3/manual/features/face-tracking/arface.html
- Unity face tracking platform support: https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.3/manual/features/face-tracking/platform-support.html
- MediaPipe Face Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- ARCore Augmented Faces: https://developers.google.com/ar/develop/augmented-faces
- Apple Vision `VNDetectFaceLandmarksRequest`: https://developer.apple.com/documentation/vision/vndetectfacelandmarksrequest
- Apple Vision `VNFaceLandmarkRegion2D`: https://developer.apple.com/documentation/vision/vnfacelandmarkregion2d

External beauty AR / mask workflow references:

- Snap Face Mask: https://developers.snap.com/lens-studio/4.55.1/references/guides/lens-features/tracking/face/face-effects/face-mask
- TikTok Lip Effect: https://effecthouse.tiktok.com/learn/guides/workspace/objects/face-effects/lip-effect
- TikTok Lip Segmentation: https://effecthouse.tiktok.com/learn/guides/workspace/objects/segmentation/lip-segmentation
- TikTok Face Paint: https://effecthouse.tiktok.com/learn/guides/workspace/assets/material/face-paint

External dataset / parsing references:

- CelebAMask-HQ: https://github.com/switchablenorms/CelebAMask-HQ
- LaPa dataset: https://github.com/jd-opensource/lapa-dataset
- BiSeNet face parsing: https://github.com/zllrunning/face-parsing.PyTorch
- SegFace: https://github.com/Kartik-3004/SegFace

External annotation/tooling references:

- Figma Help Center: https://help.figma.com/hc/en-us
- Adobe Photoshop Desktop Help: https://helpx.adobe.com/photoshop/desktop.html
- Procreate Handbook: https://help.procreate.com/procreate/handbook
- CVAT documentation: https://docs.cvat.ai/docs/
- Label Studio documentation: https://labelstud.io/guide/

External smoothing/math reference:

- One Euro Filter paper: https://cristal.univ-lille.fr/~casiez/1euro/

Implementation provenance:

- The barycentric screen-to-UV projection, vote accumulation, scoring thresholds, candidate ladder, and build-gate workflow in this plan are authored implementation proposals for this repo. No third-party code, model weights, dataset assets, SDKs, or UV templates are copied into the repo by this document.

License policy:

- Public datasets and pretrained weights are reference-only until license review.
- CelebAMask-HQ is non-commercial/research restricted.
- LaPa, BiSeNet, SegFace, and any generated silver outputs remain reference-only until their source licenses and derivative-output constraints are reviewed.
- Every silver artifact stored under `masks_silver/` or `references/` must include source, version, command/tool, license note, and human review status.
- Commercial SDK materials are benchmark references only.
- Do not move third-party template assets into source code without explicit license clearance.

## 19. Next Session Checklist

Start the next session by reading:

1. `AGENTS.md`
2. `TECH_VALIDATION_RESULT.md` Current Session Snapshot
3. `E7_REGION_PRECISION_SUBSPIKE_PLAN.md`
4. This plan
5. `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_GPT.md`
6. `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_CLAUDE.md`
7. `docs/roadmaps/research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md`

Then do:

1. Inspect current git diff and label current atlas implementation as heuristic baseline.
2. Build the offline artifact skeleton under `evidence/e7-reference-atlas/`.
3. Treat the existing recording as scenario review/practice material only.
4. Finalize the synchronized capture-pair contract and manifest fields.
5. Stop at Build Gate before any Unity/RN build and state whether the build is for synchronized capture or runtime sweep.
6. Capture one official `lip` pair from a single runtime moment.
7. Confirm the official annotation `frame.png` is clean and mesh/debug overlays are separate derived files.
8. Draw one official `lip` gold mask on that synchronized frame.
9. Run one-frame round-trip and inspect `round_trip_overlay.png`.
10. Do not start multi-frame atlas generation, scorer work, silver references, or runtime candidate sweep until the round-trip gate passes.

## 20. Final Review

This plan was checked against the current repo constraints:

- It stays inside E7.03 / E7.3 region precision.
- It preserves E3/E4 baseline, Phase 1 HUD/LogBox cleanup, RN <-> Unity events, and recipe dispatch.
- It does not introduce E7.4/E7.5/E7.6, product readiness, M7 Green, AI/backend/upload, Android, or commercial SDK work.
- It treats MediaPipe/face parsing as offline reference only, not as runtime dependency, and leaves Apple Vision as a future research/escalation note.
- It replaces hand-tuned ellipse logic with a measurable reference-driven UV atlas path.
- It treats external dataset masks as taxonomy/examples unless they are generated or re-authored on this app's synchronized frames.
- It requires official annotation frames to be clean and keeps mesh/HUD/candidate/debug overlays as separate derived files.
- It requires synchronized capture pairs before official gold masks or UV back-projection.
- It gates all batch atlas/scoring/runtime sweep work behind a one-frame `lip` round-trip.
- It includes direct digital marking, existing mask datasets, mathematical UV projection, offline scoring, runtime candidate sweep, and real-device evidence.
