# AR Makeup Engine Research Plan

Date: 2026-06-20

Status: Research plan / pre-implementation

Primary path decision: Yellow - keep Unity + AR Foundation + ARKit as the primary path, but do not start product makeup rendering until alignment, trackable lifecycle, and region mask validation pass on the real iPhone.

## 1. Current Boundary and Non-Goals

This document decides how to research the AR makeup engine before implementing product makeup rendering. It does not replace the current validation milestone order.

Current boundary:

- `TECH_VALIDATION_RESULT.md` says M5 is complete and the next milestone is M6, Unity -> RN communication.
- `TECH_VALIDATION_TEST_PLAN.md` remains the stable validation contract.
- `docs/roadmaps/AR_FIRST_TECH_VALIDATION_ROADMAP.md` says to close M6/M7/M8 before AR alignment and region mask validation.
- Current AR makeup readiness is not Green. RN -> Unity communication is Green, ARKit face tracking is active, but visual face-fitted makeup is Yellow/Fail.

Non-goals for this research document:

- Do not implement RN, Unity, shader, AI, backend, admin, payment, community, or product code.
- Do not mark M6/M7/M8 complete.
- Do not introduce a paid commercial beauty SDK.
- Do not use datasets/models outside their allowed non-commercial research or educational terms.
- Do not ship, sell, redistribute, or present restricted research assets as commercial product assets.
- Do not attempt commercial-quality makeup rendering, product-level color matching, or full makeup suite coverage.

Product requirements that matter for the engine:

- The app must eventually apply recommended makeup on the user's face in real time.
- User-editable parameters include color, range, texture, intensity, opacity, feather, blend mode, position, and size.
- The first engine slice should stay smaller than the product vision: `lip`, `cheek`, and `eye` only.
- The AR engine must consume structured `MakeupRecipe` data, because the later AI/recommendation layer only produces recipes; Unity owns the rendering result.

Repo evidence:

- `TECH_VALIDATION_RESULT.md` records M6 as the next milestone and explicitly says product makeup work should not start from the current screen state.
- `TECH_VALIDATION_RESULT.md` records current overlay offset, first-face-only/reacquisition risk, and missing Unity -> RN status display.
- `AIAR_MakeupGuide기획서_v1.md` defines the target AR makeup guide, editable parameters, half-face guide mode, and supported makeup categories.
- `docs/roadmaps/AR_FIRST_TECH_VALIDATION_ROADMAP.md` defines the AR-first strategy and the `lip`/`cheek`/`eye` minimum region slice.

## 2. Current Evidence and Open Risks

### Current Green Evidence

| Area | Evidence | Meaning |
| --- | --- | --- |
| RN iOS host | `rn/MakeupARValidation/App.tsx` opens a full-screen `UnityView` from the RN home screen. | The RN host can enter the AR surface. |
| RN -> Unity message path | `App.tsx` sends `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)`. | Recipe-like values can reach Unity. |
| Unity receiver | `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs` exposes `ApplyRecipeJson(string)`. | Unity can parse incoming color/opacity JSON. |
| AR Foundation stack | `TECH_VALIDATION_RESULT.md` records AR Foundation 6.3.5 and ARKit XR Plug-in 6.3.5. | The current stack is aligned with the validation baseline. |
| Real-device tracking | M5 evidence logs record `SessionTracking`, face count 1, and `Face detected: true`. | ARKit face tracking is active on the iPhone. |

### Current Yellow/Fail Evidence

| Risk | Current evidence | Research consequence |
| --- | --- | --- |
| Visual overlay is offset | `TECH_VALIDATION_RESULT.md` says the colored mask is displaced above/left and not fitted to eyes, mouth, jaw, or face contour. | AR alignment must be solved before region masks or texture samples. |
| Camera pose warning | Runtime log records `Camera "AR Camera" does not use a Tracked Pose Driver (Input System)`. | AR camera setup must be compared against current AR Foundation 6.3 scene setup. |
| First-face-only / reacquisition risk | Current logs count faces but do not identify added/updated/removed trackable IDs. | Trackable lifecycle logging is required before product UX assumptions. |
| Whole-face material only | `RNBridge.cs` applies color/opacity to the overlay material and current `ARFace` renderers. | Region-specific renderer cannot build on the current material-only approach. |
| `layer` is not honored | RN sends `layer: "lip"`, but Unity applies the value to the whole diagnostic overlay. | `MakeupRecipe.layer` needs a real region dispatch contract. |
| Unity -> RN status missing | The native proxy has a `sendMessageToMobileApp` path, but RN does not display Unity status events yet. | M6 remains a prerequisite for UI-visible AR state. |
| Bridge reproducibility caveat | The successful M4/M5 run still depends on a package-local `node_modules` timing patch and generated framework sync. | Engine research must preserve lifecycle and artifact reproducibility as risks. |

### Current Scene/Source Clues

| File | Current shape | Implication |
| --- | --- | --- |
| `unity/MakeupARUnityValidation/Assets/Editor/MakeupARValidationSetup.cs` | Creates `AR Session`, `XR Origin`, `Camera Offset`, `AR Camera`, `ARCameraManager`, `ARCameraBackground`, and `ARFaceManager`. | Compare this generated hierarchy against official AR Foundation scene setup and AR camera pose requirements. |
| `MakeupARValidationSetup.cs` | Sets `faceManager.requestedMaximumFaceCount = 1`. | One-face behavior may be expected, but lost/recovered and second-face transitions still need explicit event logs. |
| `RNBridge.cs` | Parses `layer`, `color`, `opacity`; clamps opacity; applies material alpha blending. | This is a useful message contract seed, not a region renderer. |
| `FaceTrackingStatusReporter.cs` | Logs AR session state, camera direction, face support, and face count. | Extend this style in a future session with `trackablesChanged`, tracking state, trackable ID, vertex count, and face transform. |

## 3. Public Source Inventory

### Official Runtime Path

| Source | What it says | Use in this repo |
| --- | --- | --- |
| [Unity AR Face Manager 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/arfacemanager.html) | `ARFaceManager` creates face GameObjects, exposes `trackablesChanged`, uses a face prefab, and has `Maximum Face Count`. | Use `trackablesChanged` as the core lifecycle event for M6+ status and reacquisition diagnosis. |
| [Unity AR Face 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/face-tracking/arface.html) | `ARFace` lifecycle is added/updated/removed; a face can become `Limited`; face mesh data can include vertices, normals, indices, and UVs. | Use `trackingState`, mesh vertices/indices/UVs, and `ARFace.updated` as the basis for alignment and region masks. |
| [Unity Face Tracking Samples 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/samples/features/face-tracking.html) | Official samples include face pose, face mesh, ARKit blend shapes, eye poses, and ARCore-only face regions. | Use samples as reference scenes before inventing custom face/lifecycle code. |
| [Unity Camera Components 6.3](https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%406.3/manual/features/camera/camera-components.html) | AR scenes use `ARCameraManager` and `ARCameraBackground`; facing direction can be user/front camera. | Check the current AR Camera hierarchy and background rendering before debugging renderer math. |
| [Unity as a Library iOS](https://docs.unity3d.com/Manual/UnityasaLibrary-iOS.html) | UnityFramework supports embedded runtime control, pause, unload, and `sendMessageToGOWithName`; known limits include full-screen-only rendering and a single Unity runtime instance. | Keep AR screen full-screen and treat unload/re-enter behavior as an M7 validation risk, not a cosmetic issue. |
| [`@azesmway/react-native-unity`](https://github.com/azesmway/react-native-unity) | iOS uses a built `UnityFramework`; supports `postMessage`, `onUnityMessage`, `unloadUnity`, and `pauseUnity`; warns that iOS view dimensions must be non-zero. | Continue using it for the validation bridge, but make current local timing/framework-sync caveats durable before relying on clean reinstall behavior. |

### Tracking Alternatives

| Source | What it says | Decision |
| --- | --- | --- |
| [MediaPipe Face Landmarker](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker) | Outputs 3D face landmarks, blendshape scores, and facial transformation matrices; supports image, video, and live stream modes; can output a complete face mesh. | Keep as a fallback/comparison candidate, not the primary implementation path yet. |
| [ARCore Augmented Faces](https://developers.google.com/ar/develop/augmented-faces) | Provides center pose, three region poses, and a 468-point 3D face mesh for face effects and try-ons without specialized hardware. | Use as Android/fallback reference. It is not a reason to switch away from the current iOS ARKit validation path. |

Fallback trigger for MediaPipe or ARCore comparison:

- ARKit/AR Foundation alignment cannot be fixed in RN-hosted Unity.
- ARKit mesh/UV is insufficient for stable `lip`, `cheek`, and `eye` region masks.
- Face lost/recovered or second-face reacquisition blocks product UX even after lifecycle fixes.
- Android validation becomes part of the active scope.
- Static AI analysis and runtime AR need a shared landmark topology that ARKit alone cannot provide.

### Makeup Texture and Region References

Project-use note:

- This project is a bootcamp research/education prototype, not a commercial release.
- Datasets and model repositories that allow non-commercial research, teaching, scientific publication, or personal experimentation may be used for research validation in this repo.
- Keep citation/attribution notes with any dataset/model used.
- Do not redistribute restricted datasets, derived dataset copies, or pretrained weights unless the upstream terms explicitly allow it.
- Re-check licenses before any public launch, App Store submission, paid demo, or commercial use.

| Source | What it contributes | License/use constraint |
| --- | --- | --- |
| [CelebAMask-HQ](https://github.com/switchablenorms/CelebAMask-HQ) | Face parsing reference with 30,000 high-resolution images and 19 mask classes including skin, nose, eyes, brows, mouth, lip, and hair. | Allowed for this bootcamp scope as non-commercial research/educational use if the dataset agreement is followed. Do not sell, redistribute, or use as a commercial product asset. |
| [LaPa Dataset](https://github.com/jd-opensource/lapa-dataset) | Face parsing reference with 22,000+ images, 11-category labels, and 106-point landmarks. | Allowed for this bootcamp scope as non-commercial research, teaching, publication, or personal experimentation if license terms are followed. Do not use for commercial release without re-review. |
| [BiSeNet face parsing](https://github.com/zllrunning/face-parsing.PyTorch) | Practical face parsing implementation commonly used with CelebAMask-HQ-style labels. | MIT-licensed code can be used for research prototyping, but datasets and pretrained weights must follow their own terms. Runtime fit still needs separate review before integration. |
| [SegFace](https://github.com/Kartik-3004/SegFace) | Newer face segmentation reference for long-tail face parsing classes. | MIT-licensed code can be used for research prototyping; datasets used with it still inherit their own non-commercial/research terms. |
| [PSGAN](https://hf.co/papers/1909.06956), [SARA](https://hf.co/papers/2311.16828), [BeautyBank](https://hf.co/papers/2411.11231), [AvatarMakeup](https://hf.co/papers/2507.02419), [FFHQ-Makeup](https://hf.co/papers/2508.03241) | Makeup transfer literature emphasizes spatial alignment, region-aware editing, identity/appearance consistency, and UV/3D consistency. | Use to shape renderer requirements (`region`, `texture`, `feather`, `blendMode`, `intensity`), not to import generative makeup pipelines into v1. |

## 4. Candidate Architecture Matrix

| Candidate | Description | Strength | Risk | Decision |
| --- | --- | --- | --- | --- |
| A. Current whole-face material | Continue applying color/opacity to the `ARFace` mesh material. | Already proven for RN -> Unity message receipt. | Cannot isolate lip/cheek/eye; current visual alignment is wrong; `layer` has no real meaning. | Reject as product engine. Keep only as diagnostic baseline. |
| B. ARFace mesh + per-region vertex/UV maps | Use ARKit/AR Foundation `ARFace` mesh data and classify stable vertex/UV areas into `lip`, `cheek`, and `eye` masks. | Best fit for current iOS stack; follows face pose/expression; keeps Unity renderer in control. | Requires mapping work and real-device validation for expression/rotation. | Primary v1 research path after alignment. |
| C. Multiple region renderers/materials | Create separate renderer objects/materials for each region, driven by shared face mesh updates. | Clear layer isolation; easier visual debugging; maps well to recipe layers. | May increase draw calls and edge artifacts; must stay aligned to the same face mesh. | Use for v1 prototype if performance remains acceptable. |
| D. Mask texture atlas + shader pass | Use UV-space masks/textures and one shader/layer stack to blend regions. | Better for feather, texture, and later matte/shimmer/blush samples. | More shader/asset complexity; requires correct UV basis first. | Research in parallel, implement after B/C proves region separation. |
| E. Screen-space 2D landmarks/segmentation | Overlay 2D masks on camera feed using face parsing or landmarks. | Can borrow face parsing literature; useful for static analysis. | Harder to keep stable with 3D head rotation and Unity camera feed; duplicates ARKit tracking. | Fallback only. |
| F. MediaPipe live landmark stack | Run MediaPipe Face Landmarker and render from its landmarks/matrices. | Strong cross-platform landmark topology and blendshape output. | Adds ML/native/runtime complexity to RN + Unity; not needed until ARKit path fails a concrete gate. | Do not implement now; define fallback triggers. |
| G. Commercial beauty AR SDK | Integrate paid/closed virtual makeup SDK. | Fastest polished demo if budget/license allow. | Conflicts with current direct-implementation learning/validation goal; vendor lock-in; outside scope. | Benchmark only; no integration in this validation plan. |

Recommended engine direction for v1:

1. Keep Unity + AR Foundation + ARKit as the primary runtime path.
2. Close M6/M7/M8 before makeup renderer work.
3. Fix camera/pose alignment before region masks.
4. Add explicit trackable lifecycle diagnostics before judging first-face-only behavior.
5. Build `lip`, `cheek`, and `eye` as independent region layers over ARFace mesh data.
6. Use shader/mask texture work only after region separation is visually stable.
7. Use MediaPipe/ARCore only if a documented fallback trigger is hit.

Primary path Green/Yellow/Red:

| Layer | Current status | Reason |
| --- | --- | --- |
| RN + Unity + iPhone integration | Green | M0-M5 are recorded Green through real-device build, embed, AR view, and RN -> Unity recipe delivery. |
| ARKit/AR Foundation tracking | Green | Logs and screenshots show `SessionTracking`, front camera, and face detected state. |
| Face-fitted rendering | Yellow/Fail | Overlay is visibly offset and AR Camera pose warning is present. |
| Region renderer | Not started | Current code applies color/opacity to the whole diagnostic overlay. |
| Overall ARKit primary path | Yellow / continue | The stack is still the best primary path, but it needs alignment and region-mask gates before product work. |

## 5. Proposed v1 Interfaces

These interfaces are research targets only. Do not implement them in this document.

### Recipe Shape

Use a multi-layer recipe so RN, AI recommendation, and Unity renderer share one contract:

```json
{
  "recipeId": "demo-natural-001",
  "version": 1,
  "layers": [
    {
      "layer": "lip",
      "color": "#D94B74",
      "opacity": 0.65,
      "feather": 0.2,
      "blendMode": "multiply",
      "texture": "matte_lip",
      "intensity": 0.8,
      "positionOffset": {"x": 0.0, "y": 0.0},
      "scale": 1.0,
      "enabled": true
    }
  ]
}
```

Minimum v1 required fields:

- `layers[]`
- `layer`: initially `lip`, `cheek`, `eye`
- `color`
- `opacity`

Optional v1+ fields:

- `feather`
- `blendMode`
- `texture`
- `intensity`
- `positionOffset`
- `scale`
- `enabled`

Renderer meanings:

| Field | Renderer meaning |
| --- | --- |
| `layer` | Selects a semantic face region. It must route to a real region mask, not a whole-face material. |
| `color` | Base pigment color for the selected region. |
| `opacity` | Alpha/strength of the layer. Must be visually distinguishable on device. |
| `feather` | Softness at mask edge. Required for blush and eye shadow quality. |
| `blendMode` | How pigment combines with camera/skin appearance. Start with `normal`, `multiply`, and `screen` candidates. |
| `texture` | Named procedural or asset texture. Start with `matte_lip`, `shimmer_eye`, and `soft_blush`. |
| `intensity` | Texture/shine/glitter strength, separate from opacity. |
| `positionOffset` | Small user adjustment in region-local space after mask alignment is stable. |
| `scale` | Small user adjustment for region size after mask alignment is stable. |

### Unity Runtime Modules

Proposed module boundaries for later implementation:

| Module | Responsibility | Depends on |
| --- | --- | --- |
| `UnityEventBridge` | Send `unity_initialized`, `face_detected`, `recipe_applied`, and diagnostics to RN. | M6 bridge work. |
| `FaceTrackableDiagnostics` | Log added/updated/removed faces, trackable ID, tracking state, vertex count, transform, and support flags. | `ARFaceManager.trackablesChanged`, `ARFace.updated`. |
| `ARCameraPoseValidator` | Confirm camera pose setup, remove/justify AR Camera pose warnings, and expose alignment diagnostics. | AR Foundation camera/XR Origin setup. |
| `MakeupRecipeReceiver` | Parse `layers[]`, validate supported layers/textures/blend modes, and queue/apply recipes. | RN -> Unity bridge. |
| `FaceRegionMaskProvider` | Build or load `lip`, `cheek`, `eye` masks from ARFace mesh/UV data. | Stable ARFace mesh alignment. |
| `MakeupLayerRenderer` | Render each recipe layer with color, opacity, feather, blend, texture, and intensity. | Region masks and material/shader path. |

## 6. Follow-Up Validation Plans

### 6.1 M6 Unity -> RN Communication

Purpose:

- Finish the current official next milestone before deeper engine work.

Minimum events:

- `unity_initialized`
- `face_detected` with `tracked` and `faceCount`
- `recipe_applied` with `layer`

Evidence:

- RN screen shows the latest Unity event.
- Runtime log records event send and RN receipt.
- Face lost/recovered produces changed RN status.

Stop rule:

- Do not start region rendering in M6.

### 6.2 M7 Re-Entry Stability

Purpose:

- Confirm Unity lifecycle is safe enough for an AR makeup screen.

Minimum scenario:

- Start AR -> detect face -> change color/opacity -> Close -> repeat 3 times.
- Background/foreground once.
- Confirm camera indicator behavior after Close.

Evidence:

- Screen recording.
- Device/runtime log.
- Note whether unload, pause/resume, or hidden full-screen modal behavior is used.

Stop rule:

- Do not treat a one-time successful entry as product-ready.

### 6.3 M8 Foundation Result

Purpose:

- Close the first RN + Unity + AR Foundation validation before AR engine work.

Required result separation:

- RN-Unity integration status.
- Bidirectional messaging status.
- Re-entry/lifecycle status.
- ARKit tracking status.
- Visual makeup readiness status.

Expected current framing:

- Integration likely Green if M6/M7 pass.
- Visual makeup readiness remains Yellow/Fail until alignment and region masks pass.

### 6.4 AR Alignment Plan

Purpose:

- Make the diagnostic face mesh/overlay line up with the camera feed before any region mask or texture work.

Research/implementation questions for that future session:

- Does the generated scene need a Tracked Pose Driver / equivalent AR camera pose component for the current AR Foundation + Input System stack?
- Does the RN-hosted Unity embed behave differently from Unity standalone for camera pose?
- Is the overlay offset caused by camera transform, XR Origin hierarchy, background render matrix, face prefab transform, material/render queue, or screen orientation?

Minimum checks:

- Compare current `XR Origin > Camera Offset > AR Camera` hierarchy with official AR Foundation sample hierarchy.
- Verify whether AR Camera pose warning is gone or documented as harmless.
- Record front-facing screen recording with neutral face, head left/right/up/down, mouth open/closed, face lost/recovered.

Green criteria:

- 30+ second real-device recording shows overlay aligned to face contour, eyes, and mouth.
- Runtime log still shows `SessionTracking` and face detected state.
- Alignment stays acceptable through head rotation and expression changes.
- Any remaining warning is explained with evidence.

Yellow criteria:

- Front-facing still pose aligns, but rotation/expression/reacquisition drifts.

Red criteria:

- Tracking stays true but Unity overlay cannot be aligned to the camera feed.

### 6.5 Trackable Lifecycle Plan

Purpose:

- Separate first-face-only behavior from normal `MaximumFaceCount = 1` provider behavior and from visual alignment bugs.

Minimum diagnostics:

- Subscribe to `ARFaceManager.trackablesChanged`.
- Log `added`, `updated`, `removed` counts.
- Log trackable ID, `trackingState`, face transform, vertex count, and timestamp.
- Log when `ARFace.updated` fires for the active face.

Test scenarios:

- One face enters/leaves.
- Same face leaves and returns.
- Different face appears after first face leaves.
- Face partially occluded.
- Face far/near.

Green criteria:

- Logs clearly explain whether faces are removed, limited, updated, or reacquired.
- RN can display simplified face tracking status after M6.

### 6.6 Region Mask Plan

Purpose:

- Prove `lip`, `cheek`, and `eye` can be independently controlled from recipe data.

Preferred v1 approach:

- Use ARFace mesh/UV as the primary coordinate basis.
- Start with simple region masks and obvious debug colors.
- Use independent materials/renderers or mask channels for `lip`, `cheek`, and `eye`.

Minimum RN controls:

- Select region: `lip`, `cheek`, `eye`.
- Select color.
- Adjust opacity.

Minimum Unity behavior:

- `layer: "lip"` changes only lip.
- `layer: "cheek"` changes only cheek.
- `layer: "eye"` changes only eye.
- Changes apply within 1 second.
- Existing whole-face diagnostic overlay can be toggled off or separated from makeup region rendering.

Green criteria:

- Real-device recording proves each region changes independently.
- Region stays attached through head rotation, expression, and face lost/recovered.
- Runtime logs show recipe layer dispatch and region application.

Yellow criteria:

- Regions are separate but edge quality or rotation stability is weak.

Red criteria:

- ARFace mesh/UV cannot support stable region masks in the current stack.

### 6.7 Texture Sample Plan

Purpose:

- Verify that the renderer can show basic makeup texture differences after region masks are stable.

Minimum samples:

- `matte_lip` on `lip`
- `shimmer_eye` on `eye`
- `soft_blush` on `cheek`

Minimum controls:

- `color`
- `opacity`
- `feather`
- `blendMode`
- `texture`
- `intensity`

Green criteria:

- iPhone recording shows visibly different matte, shimmer, and soft-blush behaviors.
- Each sample remains restricted to its region.
- Opacity and intensity changes are visually distinguishable.

Stop rule:

- Do not start product-by-product color fidelity until texture sample validation is at least Yellow.

## 7. Recommended Next Working Order

Keep this order unless `TECH_VALIDATION_RESULT.md` is explicitly updated with a different boundary:

1. M6 Unity -> RN communication.
2. M7 re-entry stability.
3. M8 foundation result.
4. AR Alignment.
5. Trackable Lifecycle diagnostics.
6. Region Mask validation.
7. Texture Sample validation.
8. AI Face Analysis.
9. AI Recommendation.

Why this order:

- Without M6, RN cannot reliably show AR engine state.
- Without M7, Unity lifecycle can break normal app use.
- Without alignment, region masks and textures can look wrong for reasons unrelated to region logic.
- Without trackable lifecycle logs, first-face-only behavior cannot be separated from render bugs.
- Without region masks, texture and makeup recipe work only decorate a whole-face diagnostic overlay.

## 8. Acceptance Checklist

This research plan is ready to use when:

- It keeps current validation boundary intact.
- It cites repo evidence and public source links for core claims.
- It gives a Green/Yellow/Red decision for the ARKit/AR Foundation primary path.
- It defines fallback triggers for MediaPipe/ARCore instead of switching stacks prematurely.
- It defines enough detail for later `AR Alignment Plan` and `Region Mask Plan` sessions.
- It keeps product implementation, AI/backend/admin/payment/community, and commercial makeup quality out of scope.
