# E7.03 Boundary Engine Quality Experiment Plan

Date: 2026-06-22 KST

Status: Temporary E7.03 / E7.3 v2 planning document

## 1. One-line Decision

E7.03 is no longer an ARFace-only region precision tweak. It is a validation-only boundary engine comparison spike whose goal is to find the strongest practical path for overlay-ready `lip`, `cheek`, and `eye` boundaries before cosmetic rendering work begins.

The target is not "slightly better than E3/E4". The target is:

> Can this stack capture the makeup placement boundary and movement well enough that E7.4 cosmetic renderer work would be a reasonable next experiment?

If the answer is not supported by visual evidence, runtime logs, and region-level scoring, E7.03 must remain Yellow or Red.

## 2. Why This Plan Changed

Current evidence in `TECH_VALIDATION_RESULT.md` says:

- ARFace mesh/UV is live on the real iPhone.
- The current procedural E7 candidate is not visually acceptable for `lip` or `eye`.
- `lip` is Red because the mask spills into lower-face skin.
- `eye` is Red because the mask is not confined to an eye/eyeshadow region.
- `cheek` is Yellow because the recording did not include a clean E7 candidate sample.
- Full E7 visual product-readiness is incomplete.

The previous plan was useful for a narrow ARFace mesh/UV comparison, but its Green bar was too low for the user's current goal. It treated MediaPipe and 2D segmentation as future-only fallback. That is not enough for an "압도적인 퀄리티" boundary validation.

The revised E7.03 v2 bar is:

- preserve E3/E4 baseline;
- test a stronger ARFace authored-mask path;
- compare against additional boundary candidates;
- use research/open-source references where appropriate;
- judge lip, cheek, and eye separately;
- only then decide whether ARFace-only, reference-assisted ARFace, or hybrid is the right next boundary.

## 3. Current Boundary

In scope:

- `lip`, `cheek`, and `eye` only.
- Boundary, attachment, motion, expression, and lost/recovered behavior.
- Validation/debug visuals only.
- E3/E4 broad/centroid baseline preservation.
- ARFace mesh/UV authored candidate.
- Offline/reference experiments using MediaPipe, Apple Vision, Google ML Kit, and face parsing models or datasets.
- Runtime POC only for candidates that first show real value in offline/reference comparison.
- Full local evidence capture: logs, screenshots/contact sheets, short recordings when motion is decision evidence.

Out of scope:

- E7.4 cosmetic renderer implementation.
- E7.5 demo look implementation.
- E7.6 final performance decision.
- AI recommendation, inference product, backend upload, admin/payment/community work.
- Commercial SDK integration.
- Android/ARCore implementation.
- Product-readiness or product-quality makeup claims.
- New regions such as brow, lash, teeth, foundation, jaw, nose, or full-face makeup.
- M7 Green promotion.

Important nuance:

- MediaPipe, Apple Vision, ML Kit, and face parsing are allowed here as validation candidates or reference tools because the user explicitly raised the quality target.
- They are not automatically accepted as product runtime dependencies.
- Any candidate that needs raw frame storage, off-device upload, commercial terms, or broad product integration must stop and be re-scoped.

## 4. Research Basis

Internal research and benchmark docs point to the same pattern:

- Commercial beauty AR does not rely on a whole-face color material.
- It uses region layers such as lips, cheeks, eyes, brows, lashes, skin, and teeth.
- It combines landmarks, dense mesh, expression/blendshape signals, segmentation, UV masks, opacity/alpha, feather, and blend modes.
- ARFace/ARKit is the best current geometric backbone for this iPhone validation repo.
- ARFace mesh/UV does not automatically provide semantic boundaries such as "exact lip edge" or "eyelid crease".
- Lip and eye need stronger semantic comparison than cheek.

Primary local references:

- `TECH_VALIDATION_RESULT.md`
- `docs/roadmaps/research/AR_ENGINE_RESEARCH_REPORT_KO.md`
- `docs/roadmaps/research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md`
- `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_GPT.md`
- `docs/roadmaps/research/E7_AXIS1_FACE_REGION_TRACKING_CLAUDE.md`

External references to verify before implementation:

- Unity AR Foundation `ARFace`: vertices, normals, indices, UVs, `trackingState`, added/updated/removed lifecycle.
- Unity face tracking platform support: ARKit supports face pose, mesh vertices/indices, UVs, eye tracking, and blend shapes.
- MediaPipe Face Landmarker: 478 3D landmarks, blendshape scores, transformation matrices, image/video/live modes.
- Google ML Kit Face Detection / Contours: 2D facial feature contours, on-device real-time detection.
- Google ML Kit Face Mesh: 468-point mesh, real-time on-device, but beta and platform/runtime suitability must be checked.
- CelebAMask-HQ, LaPa, BiSeNet, SegFace: face parsing labels/models for offline semantic reference and mask authoring, with license constraints.

## 5. Quality Target

E7.03 v2 introduces a stricter quality ladder.

| Level | Meaning | E7.03 interpretation |
| --- | --- | --- |
| Q0 Fail | Cannot identify the intended region | Current `lip` and `eye` candidate behavior is near this level |
| Q1 Broad debug | Region roughly changes independently | E3/E4 baseline level |
| Q2 Demo-plausible | Looks acceptable in narrow neutral poses | Previous E7.03 Green bar was close to this |
| Q3 Overlay-ready validation | Boundary and movement are reliable enough to build cosmetic rendering experiments on top | New E7.03 Green bar |
| Q4 Product-grade | Handles diverse users, lighting, motion, finishes, and edge cases | Out of E7.03 scope |

E7.03 Green means Q3 for all three in-scope regions. It does not mean Q4 product readiness.

## 6. Candidate Set

### A. E3/E4 Baseline

Purpose:

- Keep a known fallback and comparison point.
- Prove E7 work does not regress existing RN -> Unity recipe dispatch or Unity -> RN event flow.

Expected result:

- Q1 only.
- Never enough for E7.03 Green.

### B. ARFace Authored UV Atlas

Purpose:

- Replace procedural broad masks with authored region definitions.
- Use ARFace mesh/UV as the primary face-attached coordinate system.

How it should work:

- Create or import a canonical face UV reference.
- Author grayscale masks for `lip`, `cheek`, and `eye`.
- Render the mask through the live ARFace mesh using its UVs.
- Add debug color output first.
- Add alpha/feather visualization after hard boundaries are confirmed.

Why it matters:

- ARFace is already available and fast.
- UV masks move with the face mesh under head rotation and expression.
- Cheek is likely to pass here first.

Main risks:

- ARFace topology/UV labels are not semantic labels.
- Lip border may still bleed during mouth open/smile.
- Eye boundary may fail during blink/squint.

### C. ARFace Fixed Vertex Sets + Blendshape Correction

Purpose:

- Add geometry-aware controls where UV mask alone is not enough.

How it should work:

- Define fixed vertex sets for lip ring, eyelid band, and cheekbone area.
- Use region vertices to compute anchors, centroids, and normals.
- Use `jawOpen`, mouth stretch/pucker/funnel signals for lip correction.
- Use `eyeBlink`, `eyeSquint`, and eye pose for eye fade/feather correction.

Expected value:

- Improves motion coherence.
- Helps stop stale or over-wide masks.
- Does not by itself solve semantic boundary precision.

### D. Apple Vision Face Landmarks

Purpose:

- Test an iOS-native 2D landmark/contour comparison path.

Why it is attractive:

- Native Apple framework.
- No third-party ML dependency.
- Likely easier to reason about on iPhone than a full external runtime.

Risks:

- 2D landmarks must be synchronized with ARKit camera frames.
- 2D coordinates must be mapped into Unity/ARFace space or used only as reference.
- Landmark density may be insufficient for makeup-grade lip/eye edges.

Best role in E7.03:

- Offline/reference comparison first.
- Possible lightweight runtime POC only if it clearly beats ARFace authored masks for lip/eye.

### E. MediaPipe Face Landmarker

Purpose:

- Compare a stronger landmark/mesh system against ARFace region candidates.

Why it is attractive:

- Provides dense 3D facial landmarks.
- Provides blendshape scores and transformation matrices.
- Has video/live-stream modes.
- Teammate evidence suggests it can nearly catch the target boundary.

Risks:

- Additional iOS/Unity integration complexity.
- Possible camera/frame synchronization conflict with ARKit.
- Latency and jitter may be visible.
- It still does not provide a finished makeup renderer.

Best role in E7.03:

- First: offline/reference comparison on the same clips.
- Second: targeted runtime POC only for failing regions, especially `lip` and `eye`.
- Third: hybrid candidate if ARFace-only cannot reach Q3.

### F. Face Parsing Models and Label Datasets

Candidate references:

- CelebAMask-HQ
- LaPa
- BiSeNet face parsing implementations
- SegFace
- Similar open-source face parsing/lip segmentation models after license review

Purpose:

- Provide pixel-level semantic reference for lip, eye, and skin/face regions.
- Help author better UV masks.
- Create an objective-ish reference for "does this mask actually match the feature?"

Why it is attractive:

- Strongest candidate for semantic boundary knowledge.
- Useful for lip and eye, where ARFace mesh/UV alone is weak.
- Helps avoid hand-wavy "looks better" scoring.

Risks:

- Dataset/model licenses may be research-only or non-commercial.
- Pretrained weights may have separate terms.
- Inference may be too heavy for live iPhone + Unity + ARKit.
- Cheek/blush is not always a direct dataset class; cheek may need a derived region from skin, nose, eye, and landmark geometry.

Best role in E7.03:

- Offline reference and mask-authoring helper.
- Not first-choice live runtime.
- Keep outputs local; do not upload raw frames.

### G. Google ML Kit Face Detection / Contours / Face Mesh

Purpose:

- Test a lighter Google on-device contour path.

Why it is attractive:

- Face Detection exposes facial feature contours.
- Face Mesh exposes 468 3D points and triangle info in real-time selfie-like settings.
- It may be lighter than a custom face parsing model.

Risks:

- Face Mesh docs mark the API as beta.
- iOS suitability and Unity/RN integration must be verified.
- It may duplicate MediaPipe-like functionality with less control.
- It may not be better than MediaPipe for the same engineering cost.

Best role in E7.03:

- Feasibility comparison.
- Do not prioritize above Apple Vision and MediaPipe unless integration looks clearly cheaper.

### H. KLT / Optical Flow + Periodic Segmentation

Purpose:

- Reduce latency by running a heavy semantic detector periodically, then tracking edges between detector frames.

Why it is attractive:

- It addresses the expected latency problem of segmentation.
- It matches research patterns where deep segmentation is combined with lightweight point tracking.

Risks:

- More custom computer-vision implementation.
- Harder to maintain.
- More likely to become a separate engine project.

Best role in E7.03:

- Research fallback only.
- Consider only if segmentation is accurate but too slow.

### I. Hybrid Candidate

Purpose:

- Combine the best properties:
  - ARFace for 3D attachment, pose, UV, lifecycle, and fast rendering.
  - MediaPipe / Apple Vision / face parsing for semantic contour reference or correction.
  - Unity shader/material path for region visualization.

Expected result:

- Highest chance of reaching Q3 across all three regions.
- Most engineering work.
- Most important candidate if "압도적인 퀄리티" is the priority.

## 7. Recommended Experiment Order

Do not start by integrating every candidate live. That makes the first failure "build complexity" instead of "boundary quality".

Use this order:

1. Build a clean validation view.
2. Create a shared test clip/frame set.
3. Run offline/reference comparisons.
4. Improve ARFace authored masks.
5. Pick top candidates for runtime POC.
6. Make region-level decisions.

## 8. Phase Plan

### Phase 0: Contract Reset

Outputs:

- Confirm this E7.03 v2 plan is the active plan.
- Record that the old Green bar is superseded.
- Keep `TECH_VALIDATION_TEST_PLAN.md` unchanged unless the stable validation contract itself needs correction.

Pass condition:

- Future implementation sessions can point to this document and know that E7.03 is a boundary engine comparison spike.

### Phase 1: Validation UI and Evidence Hygiene

Goal:

- Make the face visible during testing.
- Make repeated experiments fast.

Required UI modes:

- `Clean View`: no large logs over the face, only minimal controls.
- `Compact HUD`: small fps/tracking/candidate/region/status display.
- `Full Debug`: expandable evidence panel for logs and fields.
- Candidate selector: baseline, ARFace atlas, ARFace vertex/blendshape, Apple Vision ref, MediaPipe ref, parsing ref, hybrid candidate.
- Region selector: `lip`, `cheek`, `eye`.

Required evidence fields:

- candidate id;
- region;
- tracking state;
- face count;
- mesh vertex/index/uv counts;
- blendshape fields used;
- FPS/frame-time;
- candidate latency if applicable;
- state action: render, hold, fade, hide, recover;
- visual decision notes.

Why this comes first:

- Without a clean view, every quality decision is contaminated.
- If logs cover the face, we are not validating region precision.

### Phase 2: Shared Test Set

Goal:

- Compare candidates on the same motion, lighting, and face frames.

Minimum recordings:

- `lip`: 15-20 seconds, neutral, smile, mouth open/close, talking-like movement, pucker, yaw left/right.
- `cheek`: 15-20 seconds, smile, yaw, pitch, near/far, partial profile.
- `eye`: 15-20 seconds, blink, repeated blink, squint, gaze left/right/up/down, head pitch.
- `lost/recovered`: 10-15 seconds, face exits frame, returns, recovers.

Evidence rules:

- Keep recordings local.
- Store under `evidence/screen-recordings/` only when needed.
- Generate contact sheets and representative frames.
- Delete raw extracted frame batches after derived evidence is created unless a specific frame is selected as evidence.
- Do not upload frames.

### Phase 3: Offline / Reference Candidate Comparison

Goal:

- Determine which candidate is worth live runtime work.

Inputs:

- Shared recordings from Phase 2.
- Representative frames per region and motion state.

Candidates:

- Current E3/E4 baseline.
- Current procedural E7 candidate.
- ARFace authored UV atlas candidate, if implemented.
- Apple Vision landmarks/contours.
- MediaPipe Face Landmarker.
- Face parsing model/reference labels.
- Google ML Kit contours/mesh if feasible.

Outputs:

- Per-frame overlay contact sheet.
- Region scoring table.
- Candidate ranking per region.
- Decision: no runtime POC, ARFace-only POC, MediaPipe POC, Apple Vision POC, parsing-assisted authoring, or hybrid POC.

Do not count a candidate as better just because it is more complex. It must visibly improve boundary placement or motion stability.

### Phase 4: ARFace Authored Boundary Candidate

Goal:

- Replace broad procedural masks with an authored face-attached candidate.

Required implementation traits:

- Use ARFace mesh/UV data.
- Use authored `lip`, `cheek`, and `eye` masks.
- Keep E3/E4 baseline selectable.
- Add hard-color debug output first.
- Add feather/alpha debug after hard placement is correct.
- Log UV availability and mesh counts every summary interval.
- Keep state handling Unity-side.

Expected region outcomes:

- `cheek`: likely strongest ARFace-only Green candidate.
- `lip`: possible Q3 with mask tuning and blendshape correction; risk remains around inner mouth and smile.
- `eye`: likely Q2/Q3 only for broad eyeshadow, not eyeliner-grade edge.

### Phase 5: Semantic Boundary Reference

Goal:

- Use trained labels/models to define what "correct boundary" means.

Tasks:

- Review license for each dataset/model/weight.
- Run face parsing or label-derived reference on selected frames.
- Extract `upper lip`, `lower lip`, `eye`, `skin`, and surrounding face labels where available.
- For cheek, derive a soft reference zone from skin/landmark geometry rather than expecting a perfect dataset class.
- Use parsing output to adjust ARFace UV masks.

Expected output:

- `lip` reference mask.
- `eye` reference mask or contour.
- `cheek` derived soft-zone reference.
- Notes on whether the reference is suitable only for authoring or could become runtime fallback.

### Phase 6: Runtime POC for Winners Only

Goal:

- Test only the candidates that offline comparison says are worth the integration cost.

Candidate gates:

- Apple Vision runtime POC only if 2D contours clearly beat ARFace atlas on lip/eye in offline frames.
- MediaPipe runtime POC only if MediaPipe reference clearly improves failing regions and expected latency is acceptable enough to measure.
- Face parsing runtime POC only if offline parsing is dramatically better and a lightweight/mobile path is plausible.
- Hybrid runtime POC only if ARFace atlas is stable but semantic edge correction is needed.

Runtime POC must measure:

- FPS/frame-time.
- Candidate inference latency.
- Visual lag.
- Jitter.
- Recovery after `Limited`/lost state.
- Memory and thermal notes if available.

### Phase 7: Final Region Decision

For each region, record:

- Best candidate.
- Backup candidate.
- Green/Yellow/Red.
- Q-level.
- Visual evidence.
- Runtime evidence.
- Known failure cases.
- Whether E7.4 may start for that region.

Do not collapse regions into one overall score. `cheek` may be Green while `eye` remains Yellow or Red.

## 9. Scoring Method

### Region Metrics

Use both visual scoring and simple derived measurements.

| Metric | Beginner meaning | Expert meaning |
| --- | --- | --- |
| Boundary fit | Does the colored area sit where makeup should go? | Mask/reference overlap, miss, spill, edge plausibility |
| Motion attachment | Does it stick to the face when moving? | Pose/expression coherence, per-frame centroid/area stability |
| Expression robustness | Does it survive blinking, smiling, mouth opening? | Blendshape-conditioned boundary behavior |
| Jitter | Does it shake while the face is still? | Frame-to-frame anchor/mask delta |
| Lag | Does it follow late? | Candidate inference/control delay |
| Recovery | Does it recover cleanly after losing the face? | `Tracking` -> `Limited` -> recovered state machine behavior |
| Privacy/evidence hygiene | Are we keeping only needed local evidence? | No off-device upload, no unnecessary raw frame retention |

### Suggested Quantitative Fields

When a reference mask or contour exists:

- reference coverage: percent of reference region covered by candidate;
- spill ratio: percent of candidate outside reference or acceptable feather area;
- center drift: normalized movement of candidate center relative to face landmarks;
- area instability: frame-to-frame area change after accounting for face scale;
- recovery time: frames or milliseconds from `Tracking` restored to stable render;
- latency: frame delay or milliseconds from input frame to candidate result.

If the numbers are not reliable, label them as approximate and let visual evidence dominate.

## 10. Region-specific Green / Yellow / Red

### Lip

Green:

- Q3 or better.
- Stays on upper/lower lip through neutral, smile, mouth open/close, pucker, and talking-like movement.
- Does not repeatedly paint teeth, inner mouth, chin, or surrounding cheek/lower-face skin.
- Corners do not obviously detach during a normal smile.
- Recovery does not leave stale lip paint floating.

Yellow:

- Strong neutral and light-motion fit, but mouth-open or smile edge still has occasional visible error.
- Usable for further boundary tuning, not cosmetic finish work.

Red:

- Repeated spill into lower-face skin, teeth, or mouth interior.
- Cannot maintain recognizable lip placement under normal motion.

### Cheek

Green:

- Q3 or better.
- Soft blush zone stays attached through smile, yaw, pitch, and near/far movement.
- Does not drift into the nose fold, under-eye, jaw, or wrong side of the face.
- Feather looks intentional, not like a hard sticker.

Yellow:

- Face attachment is stable, but placement/size/feather needs tuning.

Red:

- Region crosses obviously wrong facial areas or cannot stay face-attached.

### Eye

Green:

- Q3 for broad eyeshadow/eye tint, not eyeliner-grade precision.
- Holds through blink, repeated blink, squint, gaze movement, and head pitch.
- Does not paint eyeball, collapse into lash line, jump to brow, or flicker severely.

Yellow:

- Works for neutral/light blink but fails in strong squint, fast blink, or extreme gaze.
- Needs semantic correction or blink-aware fade.

Red:

- Region is not an eye region, paints broad face/lower face, or collapses on blink/squint.

## 11. Candidate Ranking Prediction

Current best prediction before running the experiments:

| Candidate | Lip | Cheek | Eye | Overall prediction |
| --- | --- | --- | --- | --- |
| E3/E4 baseline | Red/Q1 | Yellow/Q1 | Red/Q1 | Keep only as baseline |
| Current procedural E7 | Red/Q0-Q1 | Unknown/Yellow | Red/Q0-Q1 | Reject as final basis |
| ARFace authored UV atlas | Yellow-Green/Q2-Q3 | Green/Q3 | Yellow/Q2-Q3 | Best primary path |
| ARFace atlas + blendshape correction | Green possible/Q3 | Green/Q3 | Yellow-Green possible/Q2-Q3 | Best ARFace-only path |
| Apple Vision contours | Yellow-Green possible | Weak for cheek | Yellow possible | Good iOS-native comparison |
| MediaPipe Face Landmarker | Green possible | Yellow-Green | Green possible | Strongest landmark comparison |
| Face parsing reference | Green reference | Useful derived reference | Green reference | Best offline semantic source |
| ML Kit contours/mesh | Yellow-Green possible | Weak for cheek | Yellow possible | Worth feasibility check |
| Hybrid ARFace + semantic correction | Green most likely | Green | Green most likely | Highest quality path, highest work |

The most likely final answer is not one engine for every region. It may be:

- `cheek`: ARFace authored UV atlas.
- `lip`: ARFace authored UV atlas + blendshape correction, with MediaPipe or parsing reference for authoring.
- `eye`: ARFace authored UV atlas + blink/eye-pose handling, with MediaPipe or parsing reference; runtime hybrid if ARFace-only remains Yellow.

## 12. Evidence Contract

Required logs:

- `evidence/logs/e7-03-boundary-runtime-YYYY-MM-DD.log`
- `evidence/logs/e7-03-boundary-offline-compare-YYYY-MM-DD.md`
- `evidence/logs/e7-03-boundary-decision-YYYY-MM-DD.md`

Required visuals:

- `evidence/screenshots/e7-03-boundary-contact-sheet-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-03-boundary-region-lip-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-03-boundary-region-cheek-YYYY-MM-DD.jpg`
- `evidence/screenshots/e7-03-boundary-region-eye-YYYY-MM-DD.jpg`

Optional recordings:

- `evidence/screen-recordings/e7-03-boundary-lip-YYYY-MM-DD.mp4`
- `evidence/screen-recordings/e7-03-boundary-cheek-YYYY-MM-DD.mp4`
- `evidence/screen-recordings/e7-03-boundary-eye-YYYY-MM-DD.mp4`
- `evidence/screen-recordings/e7-03-boundary-lost-recovered-YYYY-MM-DD.mp4`

Recording rule:

- Use recordings when motion is decision evidence.
- Keep at least 10 seconds per decision clip.
- Prefer 15-20 seconds for lip/cheek/eye motion clips.
- Keep metadata, contact sheets, and representative frames.
- Do not commit evidence.

Runtime full stream:

- Capture full runtime console output with `tee` or equivalent.
- Summary-only logs cannot replace full logs.

## 13. Stop Rules

Stop and re-scope if:

- A candidate requires off-device upload of face frames.
- A candidate requires commercial SDK terms or branding.
- A candidate requires Android work.
- A candidate changes RN/Unity product UI beyond validation controls.
- A candidate requires new makeup regions outside `lip`, `cheek`, `eye`.
- E3/E4 baseline behavior regresses.
- RN -> Unity recipe dispatch regresses.
- Unity -> RN event receipt regresses.
- M7 lifecycle risk is silently treated as Green.

Do not stop merely because the scope is larger than the old E7.03 plan. The user has explicitly raised the quality target.

## 14. Implementation Touchpoints

Likely files for implementation sessions:

- `rn/MakeupARValidation/App.tsx`
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
- `unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs`
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- optional new Unity scripts for E7.03 candidate isolation;
- optional local scripts under `scripts/` for offline frame extraction, candidate comparison, and contact sheet generation.

Implementation principles:

- Keep E3/E4 baseline selectable.
- Keep candidate modes explicit.
- Keep region scoring separate.
- Keep debug visuals hard and readable before cosmetic rendering.
- Keep smoothing in Unity or candidate-runtime layer, not RN per-frame bridge.
- Keep local-only evidence.

## 15. Final Handoff Required

E7.03 is complete only when `TECH_VALIDATION_RESULT.md` records:

- decision date/time;
- implemented candidates;
- rejected candidates and why;
- evidence paths;
- `lip`, `cheek`, and `eye` Q-level plus Green/Yellow/Red;
- best candidate per region;
- performance/latency notes;
- lost/recovered notes;
- privacy/license limitations;
- whether E7.4 is allowed, blocked, or allowed only for specific regions;
- next boundary.

Until that handoff exists, full E7 visual product-readiness remains incomplete.
