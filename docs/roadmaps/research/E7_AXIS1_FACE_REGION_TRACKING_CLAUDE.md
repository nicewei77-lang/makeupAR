# Face Region Tracking Quality for AR Makeup — Unity + AR Foundation + ARKit (iPhone)

## 1. Executive Summary

- **ARKit's ARFace mesh is the correct primary path for lip, cheek, and eye makeup regions on iPhone**, and it is sufficient as the geometric backbone for all three. It exposes a fixed-topology 1,220-vertex mesh, stable UVs, 52 blend shapes, eye poses, and a tracking state, all updated at 60 Hz. The single most important finding: because the mesh topology and UV coordinates are constant across all faces and sessions, you can author region masks **once** (as a UV texture atlas and/or fixed vertex-index sets) and reuse them on every user.
- **Where ARKit is sufficient:** overall region placement and stability under head movement/rotation (full 6DoF pose), and expression-driven deformation (mouth open, smile, blink) because the mesh deforms with blend shapes. The eye and mouth openings are **holes** in the ARKit mesh, which conveniently separates eyelid-skin from eyeball and lip from teeth.
- **Where ARKit is likely insufficient:** crisp sub-pixel lip vermilion borders and clean blush feathering. Apple's own documentation describes the data as "**a coarse triangle mesh representing the topology of the detected face**"; cheeks are sparsely tessellated, and Apple publishes neither a vertex→landmark table nor a UV template image. Lip edges from the raw mesh are widely reported by developers as "not very precise."
- **Fallback (MediaPipe Face Landmarker / 2D face parsing) should be a contingency, not the default.** Consider it only if real-device validation shows lip-border or blush-edge quality failing, and weigh the cost: running MediaPipe in Unity on iOS requires a native plugin, adds CPU/GPU load, conflicts with ARKit's exclusive front-camera use, and introduces its own jitter that needs filtering.
- **Temporal smoothing is mandatory for product quality.** Apply a One Euro filter to derived region parameters and add mask hysteresis plus explicit lost/recovered-face handling driven by `trackingState`. This is the highest-leverage, lowest-cost work in the E7 spike.

## 2. Source Matrix

| Source | Type | Reliability | Contributes | Implementation vs Reference |
|---|---|---|---|---|
| Apple ARFaceAnchor / ARFaceGeometry / BlendShapeLocation docs | Official platform docs | Highest | Mesh ("coarse triangle mesh"), blend shapes, eye pose, texture coords definitions | Implementation guidance |
| Apple "Face Tracking with ARKit" Tech Talk (601) | Official talk | Highest | 60 Hz update, geometry+blendshape model, lighting | Implementation guidance |
| Unity AR Foundation Face Tracking manual (ARFace, platform support) | Official runtime docs | Highest | ARFace.vertices/normals/indices/uvs, trackingState lifecycle | Implementation guidance |
| Unity Apple ARKit XR Plug-in face-tracking docs | Official runtime docs | Highest | ARKit-specific blendshape API, front-camera exclusivity | Implementation guidance |
| AR Foundation Samples (GitHub) | Official samples | High | Blendshape visualizer, face prefabs, ConfigurationChooser | Implementation guidance |
| facelandmarks.com (vertex tool + blog) | Community tool | Medium | Vertex 0 = upper lip center; interactive index picker; 1,220 verts / 6,912 triangle indices | Reference / dev tooling |
| Oxford Echoes "ARKit Face Tracking Vertices" | Community blog | Medium | Annotated vertex-index image maps | Reference |
| MediaPipe Face Landmarker / Face Mesh docs | Official (Google) | High | 478 landmarks (468 + 10 iris), attention mesh for lips/eyes, 52 blendshapes | Reference + fallback guidance |
| homuler/MediaPipeUnityPlugin | Community plugin | Medium | Path to run MediaPipe in Unity incl. iOS | Reference / fallback feasibility |
| One Euro filter (Casiez, Roussel & Vogel, CHI 2012) | Academic | High | Adaptive low-pass smoothing for landmark jitter | Implementation guidance |
| CelebAMask-HQ / LaPa / BiSeNet / SegFace | Academic datasets/models | High | Region taxonomy (u_lip, l_lip, l_eye, r_eye), parsing accuracy | Reference only |
| TikTok Effect House / Snapchat Lens Studio docs | Vendor docs | Medium-High | Benchmark region model (Lips/Eyes/Eyelashes masks, face UV, lip segmentation) | Reference / benchmark only |
| Banuba / DeepAR / Perfect Corp capability pages | Vendor marketing | Low-Medium | Competitive capability context | Reference only |

## 3. ARKit / ARFace Capability Summary

**Confirmed facts (Apple / Unity official):**

- **Mesh:** ARKit's `ARFaceGeometry` exposes a triangle mesh of **1,220 vertices** and **2,304 triangles** (6,912 triangle indices; `geometry.vertices.count = 1,220`, `geometry.triangleIndices.count = 6,912`). Apple defines `ARFaceAnchor.geometry` as "a coarse triangle mesh representing the topology of the detected face." Topology is **fixed**: a given vertex index always maps to the same point on the face, across all users and sessions. Vertices are provided in **face space** (relative to the face anchor's pose).
- **Unity exposure:** `ARFace` exposes `vertices`, `normals`, `indices`, and `uvs` (NativeArrays, parallel arrays). Availability is platform-dependent; on ARKit all are provided. The `ARFaceManager` raises added/updated/removed lifecycle events.
- **UVs / texture coordinates:** `ARFaceGeometry.textureCoordinates` is a per-vertex float2 buffer. Apple's documentation confirms the UV mapping is **constant** — the same vertex indices always map to the same texture coordinates — so a single full-face UV atlas is authorable once and reusable. **Caveat:** Apple does not publish a UV template image, and ARKit does not supply any face texture; the unwrap must be extracted from Apple's "Tracking and Visualizing Faces" sample asset. In Unity, developers report the runtime ARKit face mesh's UVs may sit outside [0,1] and need offsetting into bounds.
- **Blend shapes:** 52 coefficients (0.0–1.0), based on FACS. Names relevant to makeup regions:
  - **Lips/mouth:** `jawOpen`, `mouthClose`, `mouthFunnel`, `mouthPucker`, `mouthLeft`, `mouthRight`, `mouthSmileLeft/Right`, `mouthFrownLeft/Right`, `mouthStretchLeft/Right`, `mouthRollLower/Upper`, `mouthShrugLower/Upper`, `mouthPressLeft/Right`, `mouthLowerDownLeft/Right`, `mouthUpperUpLeft/Right`, `mouthDimpleLeft/Right`.
  - **Eyes:** `eyeBlinkLeft/Right`, `eyeSquintLeft/Right`, `eyeWideLeft/Right`, `eyeLookUp/Down/In/Out (Left/Right)`.
  - **Cheeks:** `cheekPuff`, `cheekSquintLeft/Right`. (`noseSneerLeft/Right` also affects the upper-cheek/nasolabial area.)
- **Eye pose / gaze:** ARKit provides left/right eye transforms and a fixation point; in Unity, `ARFace.leftEyePose`, `rightEyePose`, and `fixationPoint` (each `HasValue`-guarded). These describe eyeball orientation, not eyelid skin region.
- **Tracking state / transform:** Face anchor provides full 6DoF transform in world space. `ARFace.trackingState` is `None` / `Limited` / `Tracking`. When a face leaves the frame, AR Foundation may set state to `Limited` rather than removing the trackable.
- **Update rate:** Face mesh and blend shapes update in real time at **60 fps** (color image 60 fps; depth image ~15 fps).
- **Topology note (community):** The eye openings and inner mouth are **holes** in the ARKit mesh (no filled geometry), which naturally separates eyelid-skin from eyeball and lip from teeth. (ARCore's default mesh fills these; ARKit's does not.)

**Inference / estimation:**

- Lip and eye regions are the **most densely tessellated** areas; cheeks and forehead are **sparser**, consistent with Apple's "coarse mesh" description. For a tight blush boundary you will likely interpolate within triangles or rely on the UV atlas rather than dense per-vertex cheek control. *(Inference from community maps + Apple "coarse" description.)*
- Because there is no official vertex→landmark table, region vertex sets must be reverse-engineered (facelandmarks.com picker, Oxford Echoes maps) or derived from blend-shape influence ("betas"). **Vertex 0 is the center of the upper lip** — community-confirmed: "a vertex with the index 0 … will always map to the middle, center of the upper lip. These vertex indices never change."

## 4. Lip / Cheek / Eye Tracking Strategy Table

| Region | Best coordinate basis | Under head rotation | Under expressions | Edge / feather needs | Failure modes | Validation scenarios |
|---|---|---|---|---|---|---|
| **Lip** | Fixed lip vertex-index ring + UV-atlas lip mask, in face space | Robust — mesh carries full 6DoF; color stays anchored | Mesh deforms with `jawOpen`/`mouthFunnel`/`mouthPucker`; holes keep color off teeth | High: vermilion border needs sub-vertex precision + soft feather; raw mesh edge is "not very precise" | Bleed beyond lip line; corner gaps on wide smile; lower-lip lag on fast `jawOpen` | Open/close mouth, big smile, pucker, talk, profile turn |
| **Eye/eyeshadow** | Eyelid-skin vertices above the eye hole + UV-atlas eye mask | Robust | Eyelid follows `eyeBlink`/`eyeWide`/`eyeSquint`; eye hole keeps shadow off eyeball | Medium-high: must hug crease/lid, feather upward; avoid brow and lash line | Shadow slips onto eyeball edge; flicker on blink; asymmetry on squint | Blink (single/repeated), wide eyes, squint, look up/down/side, glasses |
| **Cheek/blush** | Cheekbone vertex cluster + UV-atlas blush mask (soft) | Robust | Minor deformation (`cheekPuff`, `cheekSquint`, smile) | High but soft: blush is inherently diffuse, so feathering hides sparse geometry | Patch drifts with sparse cheek verts; hard edge if mask too tight; over/under-coverage across face widths | Smile, cheek puff, head tilt, varied face shapes, lighting changes |

## 5. Architecture Comparison Table

| Approach | Precision | Performance | Expression robustness | Implementation complexity | Recommended for |
|---|---|---|---|---|---|
| **ARFace mesh vertex/UV region map** | Med-High | Excellent (mesh already computed) | High (deforms w/ mesh) | Medium | All three regions — primary backbone |
| **Submesh / material separation** (split mesh by region into submeshes) | Medium | Excellent | High | Medium-High (build index buffers once) | Lip vs eye vs cheek material separation, occlusion ordering |
| **UV mask texture atlas** (painted lip/eye/cheek masks on stable face UV) | High (with good mask art) | Excellent | High | Low-Medium (author masks once) | Primary masking method for all three; best edge/feather control |
| **Separate region renderers** (independent quads/meshes per region) | Medium | Good | Medium (must re-derive anchors) | High | Special cases (e.g., decals); generally unnecessary |
| **Screen-space 2D segmentation overlay** (parse camera frame) | High (pixel-accurate edges) | Poor-Medium on iOS (heavy) | Medium (needs own smoothing) | High | Fallback only, lip-border rescue |
| **MediaPipe hybrid/reference** (478 landmarks, attention mesh) | High around lips/eyes | Medium (native plugin, extra inference) | Medium (own jitter) | High (build, camera conflict) | Reference + targeted fallback only |

## 6. Recommended Unity Implementation Path

1. **Lock the pipeline to the user-facing camera.** Enable face tracking in XR Plug-in Management; ensure your `ConfigurationChooser` prioritizes the front camera (face tracking and world/rear-camera subsystems are mutually exclusive on ARKit).
2. **Author region masks against the stable face UV atlas, once.** Extract the ARKit UV unwrap from Apple's "Tracking and Visualizing Faces" sample, and paint three soft-edged grayscale masks (lip, eye, cheek). Because UVs are constant, these masks transfer to every user. Use TikTok Effect House's downloadable face-mask template (Whole face / Eyes / Eyelashes / Lips / Teeth) and Snapchat's Face Mesh UV reference as authoring benchmarks for region shapes.
3. **Render via a custom face material that samples region masks.** Assign `ARFace.uvs` to the generated Unity mesh; in the shader, multiply makeup color by the region mask's alpha with adjustable feather and opacity/blend-mode (mirroring the per-region opacity + blend-mode model that Effect House/Lens Studio expose).
4. **Define fixed vertex-index sets per region** (lip ring, eyelid band, cheekbone cluster) for logic that needs geometry rather than texture — e.g., computing a per-region centroid/normal for smoothing or occlusion checks. Reverse-engineer these once with the facelandmarks.com picker / Oxford Echoes maps; store as constants.
5. **Drive expression-aware behavior from blend shapes.** Read `jawOpen`/`mouthClose`/`mouthFunnel`/`mouthPucker` to modulate lip mask/feather; read `eyeBlink*`/`eyeSquint*` to fade eyeshadow during blink to avoid the eyeball edge.
6. **Subscribe to lifecycle + tracking state.** Use `ARFaceManager` events and `ARFace.trackingState` to gate rendering (see §8). Offload any heavy per-frame work off the main thread to hold 60 fps.
7. **Insert temporal smoothing** (§8) on derived per-region parameters before rendering.
8. **Validate on real device only** (§9), iterating mask art and feather until lip/eye edges pass.

## 7. Fallback Trigger Table

| Region | Trigger condition | Recommended fallback | Cost / risk |
|---|---|---|---|
| **Lip** | Vermilion border visibly imprecise after mask tuning; bleed onto teeth/skin persists at scale | 2D lip segmentation (BiSeNet/SegFace `u_lip`+`l_lip`) OR MediaPipe attention-mesh lip contour to refine the mask edge | High CPU/GPU on iOS; segmentation has "very high performance impact" per Effect House; adds jitter to filter |
| **Eye** | Eyeshadow slips onto eyeball or flickers on blink beyond what blend-shape fade fixes | MediaPipe refined eye/iris landmarks (`refine_landmarks`) for a tighter lid contour | Native plugin + inference cost; camera-access conflict with ARKit front camera |
| **Cheek** | Blush patch drifts / can't feather smoothly due to sparse cheek vertices | Interpolate over a larger cheek vertex polygon; if still failing, 2D parsing of cheek region | Lower urgency (blush is diffuse); parsing cost high |
| **Any** | Device lacks reliable ARKit face tracking (older device) | MediaPipe Face Landmarker as cross-device path | Significant dev effort; out of iPhone-first scope |

## 8. Temporal Smoothing Recommendations

- **Frame-to-frame jitter:** Even at 60 Hz, derived region parameters (centroids, mask transforms, blend-shape-driven feather) exhibit micro-jitter. Apply a **One Euro filter** per scalar/vector signal — the standard adaptive low-pass used by MediaPipe FaceMesh and defined by Casiez, Roussel & Vogel (CHI 2012, "1€ Filter," doi:10.1145/2207676.2208639): "at low speeds, a low cutoff reduces jitter at the expense of lag, but at high speeds, the cutoff is increased to reduce lag rather than jitter." Two tunable params: **`mincutoff`** (minimum cutoff frequency — lower values remove more jitter) and **`beta`** (raise to reduce latency/lag at speed).
- **Low-pass vs Kalman:** A simple EMA/low-pass is cheapest but fixed-lag; Kalman/EKF is heavier and rarely needed here since ARKit already fuses sensor + TrueDepth data. **One Euro is the recommended default** for makeup region params.
- **Mask hysteresis:** For any binary on/off decisions (e.g., "mouth open → switch lip mask variant"), use dual thresholds so the state doesn't chatter near the boundary; require N consecutive frames before flipping.
- **Lost/recovered face handling:** Gate on `trackingState`. On `Limited`, **freeze** the last good region transforms and **fade out** makeup over a few frames rather than snapping. On return to `Tracking`, **fade back in** and re-prime the One Euro filters with the first valid frame to avoid a recovery jump. Note the documented risk that ARKit face tracking can take seconds (reportedly up to ~1 minute in some multi-camera/session configs) to re-acquire — design the fade and a visible "reposition face" hint accordingly.
- **Lag vs smoothness:** Tune One Euro so static makeup is rock-steady while fast head turns keep makeup glued. Validate subjectively on device; over-smoothing produces visible "swim."

## 9. Real-Device Validation Checklist (iPhone, per region)

**Global (all regions):**
- Static hold at arm's length, 60 fps confirmed, no swim/jitter.
- Slow then fast yaw/pitch/roll; makeup stays glued; check profile-angle dropout (ARKit front-mesh degrades near profile).
- Move toward/away from camera (scale changes).
- Bright, dim, and side-lit conditions.
- Face exit and re-entry: confirm fade-out on `Limited`, clean fade-in on re-acquire, re-acquire latency acceptable.
- Multiple face shapes / skin tones (mask coverage and inclusivity).

**Lip:** open/close mouth (`jawOpen`), wide smile, pucker (`mouthPucker`)/funnel (`mouthFunnel`), talking, biting lip — check border bleed onto teeth/skin and corner gaps.

**Eye:** single + repeated blink, wide eyes, squint, gaze up/down/left/right, eyeglasses on — check shadow staying on lid, blink flicker, lash-line/brow spill.

**Cheek:** smile, cheek puff (`cheekPuff`), head tilt — check blush drift, feather smoothness, symmetry, over/under coverage across face widths.

## 10. Green / Yellow / Red Decision Criteria

- **GREEN (product-ready):** All three regions stay anchored under full movement and expressions at 60 fps; lip border has no objectionable bleed; eyeshadow holds through blinks; blush feathers naturally; recovery after face loss is graceful. → ARKit-only path validated; proceed to renderer polish.
- **YELLOW (needs work, not blocked):** Region placement solid but edges soft/imprecise (lip border, blush feather), or minor blink flicker. → Iterate mask art + One Euro tuning + blend-shape fades before considering fallback.
- **RED (blocker):** Persistent lip bleed at scale that mask/segmentation can't fix; severe jitter that smoothing can't tame without unacceptable lag; unrecoverable tracking loss; or required regions unattainable on target devices. → Escalate to MediaPipe/2D-parsing hybrid for the failing region only, or revisit scope.

## 11. Open Risks and Unknowns

- **No official vertex/UV map:** Region vertex sets and UV layout are reverse-engineered; Apple could change details across iOS versions (topology stability is guaranteed by Apple's "constant topology" statement, but specific landmark labels are community-derived, not Apple-guaranteed). Mitigate by centralizing index/mask constants.
- **Cheek tessellation:** Sparse cheek geometry may limit blush precision; degree of impact unverified until on-device testing.
- **MediaPipe-on-iOS-in-Unity cost:** Real fps impact of a hybrid path is unquantified here and must be measured; front-camera exclusivity means MediaPipe would consume the camera frame separately from ARKit.
- **Re-acquisition latency:** Reported multi-second (occasionally up to ~1 minute) re-acquire in certain multi-camera/session configs; needs measurement in this specific RN+Unity embedding.
- **RN↔Unity bridge:** Smoothing/state must live Unity-side; JSON event latency makes RN unsuitable for per-frame region control (architecture assumption, to confirm).

## 12. License / Dataset / SDK Caution Notes

- **CelebAMask-HQ:** Licensed **CC BY-NC-SA 4.0** (NVIDIA Corp.); repo states "the use of this software is RESTRICTED to non-commercial research and educational purposes." 30,000 images at 512×512 with 19 classes (incl. `u_lip`, `l_lip`, `l_eye`, `r_eye`). Usable to understand region taxonomy, **not** for shipping a model trained on it without checking terms.
- **LaPa:** Research dataset; verify license before any model use.
- **BiSeNet / SegFace / face-parsing repos:** Check each repo's license (and any pretrained-weight license) before bundling; some weights are research-only. (For context, SegFace reports a mean F1 of 88.96 on CelebAMask-HQ and 93.03 on LaPa — high accuracy, but offline/server-grade compute.)
- **MediaPipe:** **Apache 2.0** (permissive); models downloadable; runs on-device with no server needed — fits "no server-side processing." Outputs **478 landmarks** (468 surface + 10 iris, 5 per eye) plus 52 blendshape scores. Still adds binary size and maintenance.
- **TikTok Effect House / Snapchat Lens Studio / Banuba / DeepAR / Perfect Corp:** Cited as **benchmark/reference only**. Their templates/UVs are platform-bound and not to be repackaged; commercial SDKs carry licensing/cost and are explicitly out of scope as a main solution.
- **Privacy:** Keep all processing on-device; do not store raw camera frames by default. ARKit processes face data locally — preserve that property in the RN+Unity wrapper.

## 13. Concrete Next-Step Plan — 1–2 Week Validation Spike

**Phase A (Days 1–2): Instrumentation & baseline.** Add an on-device HUD: fps, `trackingState`, key blend shapes (`jawOpen`, `eyeBlinkL/R`, `cheekPuff`). Confirm `ARFace.uvs` populate; render the raw face mesh + UV checker to verify the atlas (and check whether UVs need offsetting into [0,1]). Capture baseline jitter.

**Phase B (Days 3–5): Region masks.** Author lip/eye/cheek masks on the stable UV atlas (extract from Apple sample; benchmark shapes against Effect House/Lens Studio templates). Implement the region-mask shader with per-region opacity, feather, and blend mode. Define fixed vertex-index sets for lip ring / eyelid band / cheekbone cluster.

**Phase C (Days 6–8): Expression + smoothing.** Wire blend shapes to lip feather and eyeshadow blink-fade. Add One Euro filters (`mincutoff`/`beta`) to derived params; add mask hysteresis; implement `trackingState`-gated fade-out/in with filter re-priming.

**Phase D (Days 9–10): Real-device validation.** Run the full §9 checklist across ≥2 iPhones, multiple faces/skin tones, varied lighting. Record clips; score each region Green/Yellow/Red.

**Phase E (Days 11–12, buffer): Triage.** For any RED/stubborn-YELLOW region, prototype the targeted fallback (lip: 2D segmentation/MediaPipe attention-mesh edge; eye: refined landmarks) and measure fps cost. Produce a go/no-go recommendation on ARKit-only vs hybrid per region.

**Exit criteria:** A documented Green/Yellow/Red verdict per region, tuned One Euro params, a reusable mask atlas, and a clear decision on whether any fallback is needed for product readiness.

---

### Bottom line
For lip, cheek, and eye makeup on iPhone, **build on ARKit's ARFace mesh + a stable UV mask atlas as the primary path**, separate regions by painted masks (not separate renderers), drive expression behavior from named blend shapes, and invest early in One Euro smoothing plus `trackingState`-gated fade logic. Treat MediaPipe / 2D face parsing as a **per-region rescue** for lip-edge or blush precision only if real-device validation flags it — never as the default architecture.