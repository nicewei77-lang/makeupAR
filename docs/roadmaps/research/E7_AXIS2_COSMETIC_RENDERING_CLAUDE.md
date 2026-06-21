# Cosmetic Rendering Research Report: Unity AR Makeup Engine

## Executive Summary

For a Unity + AR Foundation + ARKit iPhone AR makeup engine, convincing real-time makeup is achievable at "enterprise-demo quality" with a **single-pass, mostly-unlit transparent face-mesh shader** that (1) reads makeup color/finish parameters from your existing JSON layer schema, (2) composites makeup over the live ARKit camera background using a **channel-packed region mask painted in the canonical ARKit face-mesh UV space**, (3) blends pigment onto skin with **multiply/soft-light** rather than alpha-over, and (4) layers a cheap **Blinn-Phong half-vector specular** for gloss plus a **texture-based shimmer** for sparkle. The jump from "color overlay" to "looks like makeup" is driven less by raw color accuracy and more by four things: **multiplicative pigment blending (preserves skin luminance/texture), feathered mask edges (smoothstep falloff), finish-correct specular behavior, and motion stability**. AR Foundation exposes a stable canonical UV layout (`ARFace.uvs`, 1220 vertices), so a single hand-painted mask works for all faces.

The recommended architecture is **URP (Forward), single transparent material, unlit base + minimal specular term, one RGBA mask texture (R=lips, G=cheeks, B=eyes), Blend SrcAlpha OneMinusSrcAlpha with a multiply path for pigment, Linear color space**. This is well within a 30fps (ideally 60fps) iPhone budget. The three demo looks (natural_daily, gloss_lip_focus, soft_blush_shimmer_eye) are expressible in your existing JSON schema with a few refinements (drop redundant `intensity`, add `specularPower`/`shimmer` controls, and a global `skinAwareness` blend weight).

**TL;DR**
- The single biggest realism lever is **abandoning straight alpha-over compositing for multiply/soft-light pigment blending** so the makeup darkens/tints skin while preserving the user's natural luminance and pores — combined with **smoothstep-feathered region masks** to kill the hard "sticker" edge.
- Use **URP Forward + one transparent, mostly-unlit face-mesh material** sampling a **channel-packed mask in ARKit's stable canonical face UV space** (`ARFace.uvs`, 1220 verts); add a cheap Blinn-Phong half-vector specular for gloss and a scrolling/triplanar sparkle texture (not procedural Voronoi) for shimmer.
- All three demo looks are achievable in your current JSON schema with minor refinements; the schema is essentially correct but `intensity` is redundant with `opacity`×`coverage`, and you should add explicit `specularPower` and a global skin-tone blend weight.

## Section 1: What Makes AR Makeup Look Like Makeup (Not a Color Overlay)

A debug overlay reads as fake for specific, fixable reasons. Real cosmetics are **semi-transparent pigment layers that interact with the underlying skin**, not opaque decals. The visual factors, in rough order of impact:

**1. Skin-tone interaction (pigment-over-skin, not paint-over-skin).** Real makeup modulates the light reflecting off skin. A multiply blend (result = base × blend) darkens and tints while preserving the relative luminance variation of the skin underneath (pores, shadows, highlights). Straight alpha compositing replaces those values with flat color and instantly reads as plastic. This is why commercial pipelines and makeup-transfer research both emphasize preserving the source identity/luminance. BeautyGAN (Li et al., ACM MM 2018) introduced a **pixel-level histogram loss on local regions**, computing histogram matching separately on three regions — eye shadows, lips, and facial skin — and the transferred result "is supposed to preserve the personal identity of x and synthesize the makeup style of y" (Sun et al., "Disentangled Makeup Transfer," arXiv:1907.01144). PSGAN builds on the same region-histogram principle. The takeaway: keep the face's structure while shifting only the per-region color distribution.

**2. Edge softness / feathering.** Cosmetics have no hard boundary; they fade out. In shader terms this is a falloff applied to the mask: `smoothstep(edge0, edge1, maskValue)`. The feather width is the single most noticeable "tell." Blush especially must fade to nothing over a wide radius.

**3. Opacity vs. coverage (they are different).** *Opacity* is per-pixel transparency (how much you can see through the layer at its densest). *Coverage* is how completely the product fills/hides the region it occupies (a sheer tint has high opacity locally but low coverage; full lipstick has high coverage). In practice opacity scales the blend weight, while coverage scales how far the pigment density extends before the feather takes over. DeepAR and Banuba expose these as separate `amount`/`coverage` controls (Banuba uses `coverage: "low"/"mid"/"high"`).

**4. Pigment density.** The "how much product" axis — drives both saturation and how strongly the blend overrides skin. Maps to the alpha you feed into the blend, modulated by the mask.

**5. Finish types** (matte / cream / gloss / shimmer) — covered in Section 4. The short version: finish is almost entirely about **specular behavior and micro-texture**, not base color.

**6. Gloss/specular highlight rendering.** A moving specular hotspot that tracks head/light motion is what sells "wet" lips. Even a single cheap Blinn-Phong lobe is dramatically more convincing than a static bright texture.

**7. Powder softness approximation.** Powder = low/no specular + slightly diffused (blurred) edges + a faint matte lift in brightness. Achieved by suppressing specular and widening the feather.

**8. Shimmer/sparkle approximation.** Discrete sparkle points that twinkle with motion. On mobile, **texture-based** (a sparkle/noise texture sampled with a view- or time-dependent term) is far cheaper and more stable than procedural Voronoi glint shaders, which are explicitly flagged as not mobile-suitable by their authors.

**9. Texture / local skin detail preservation.** The multiply/soft-light path inherently preserves pores and fine shading because it modulates rather than replaces. This is the cheapest realism win available.

**10. Lighting sensitivity.** Makeup should respond at least loosely to scene/ambient light so it doesn't look pasted on. ARKit provides light estimation (intensity + color temperature, and HDR directional estimate in face tracking) you can feed into the specular and overall brightness.

**11. Motion stability.** Jitter destroys the illusion. Because the mask is in face-UV space and rides the tracked mesh, it's stable by construction — but you must avoid per-frame procedural noise that "crawls" (another reason to prefer a fixed sparkle texture over screen-space procedural noise).

## Section 2: Essential Renderer Parameters — Refined Schema

Your proposed schema is close to correct. Assessment of each field:

| Field | Verdict | Notes |
|---|---|---|
| `version` | **Keep** | Schema versioning is good practice. |
| `layers[]` | **Keep** | Layer stack is the right model; mirrors DeepAR "presets/looks" and Banuba prefab stacking. |
| `id` | **Keep** | Needed for addressing/toggling layers. |
| `region` | **Keep** | lip/cheek/eye → selects mask channel. |
| `color` | **Keep** | Hex; convert to linear in-shader. |
| `opacity` | **Keep** | Per-pixel blend weight. |
| `coverage` | **Keep** | Distinct from opacity (see §1.3); controls density extent before feather. |
| `intensity` | **Drop / redundant** | Overlaps `opacity` × `coverage`. Keep ONE master strength if you want a single user slider; don't ship all three as independent. |
| `finish` | **Keep (make authoritative)** | matte/cream/gloss/shimmer should *drive defaults* for roughness/specular/shimmer rather than being decorative. |
| `blendMode` | **Keep** | multiply/soft-light/normal/screen. The realism workhorse. |
| `feather` | **Keep** | smoothstep width on mask edge. Essential. |
| `texture` | **Keep** | Optional detail/finish texture (e.g. sparkle map). |
| `roughness` | **Keep** | Inverse of specular sharpness; maps to specular exponent. |
| `specular` | **Keep, rename intent** | Specular *intensity*. Add `specularPower` (exponent/tightness) — see below. |
| `shimmer` | **Keep** | 0–1 sparkle strength; gates sampling of sparkle texture. |
| `enabled` | **Keep** | Toggle. |

**Missing fields to add:**
- `specularPower` (or `glossSharpness`): the Blinn-Phong exponent. `roughness` and `specular` (intensity) alone can't distinguish a broad soft sheen from a tight wet hotspot.
- `skinAwareness` (0–1): how strongly to bias toward multiply/soft-light vs. normal blend. Lets you dial realism vs. punchy color per layer.
- `shimmerColor` (optional): commercial SDKs (Perfect Corp) expose a separate shimmer/pearl color distinct from base color for metallic/holographic looks.
- `tintLuma` / `preserveLuma` flag (optional): explicitly keep underlying luminance for lips on deep skin tones.

**Minimal-but-complete per-region schemas:**

```json
// LIP
{ "id":"lip","region":"lip","color":"#C0455F","opacity":0.7,"coverage":0.85,
  "finish":"cream","blendMode":"multiply","feather":0.06,
  "roughness":0.5,"specular":0.25,"specularPower":24,"shimmer":0.0,
  "skinAwareness":0.7,"enabled":true }

// CHEEK (blush)
{ "id":"cheek","region":"cheek","color":"#E48C92","opacity":0.35,"coverage":0.5,
  "finish":"powder","blendMode":"softlight","feather":0.35,
  "roughness":0.9,"specular":0.0,"specularPower":1,"shimmer":0.0,
  "skinAwareness":0.85,"enabled":true }

// EYE (shadow)
{ "id":"eye","region":"eye","color":"#A6786B","opacity":0.5,"coverage":0.6,
  "finish":"shimmer","blendMode":"multiply","feather":0.18,
  "roughness":0.7,"specular":0.15,"specularPower":8,
  "shimmer":0.5,"shimmerColor":"#FFE9C8","skinAwareness":0.7,"enabled":true }
```

Note the per-region defaults: lip feather is tight (~0.06), cheek feather is wide (~0.35), eye is intermediate (~0.18). Cheek specular is zero (powder); lip specular varies by finish; eye carries the shimmer.

## Section 3: Unity Shader/Material Architecture

**URP vs Built-in.** Use **URP (Universal Render Pipeline), Forward renderer.** AR Foundation's `ARBackgroundRendererFeature` is designed for SRP, URP is the actively-developed mobile path, and URP's SRP Batcher + lightweight Lit/Unlit shaders are tuned for mobile. The community caveat is real — URP can use more memory and is not automatically faster than Built-in for trivial scenes — but for an AR makeup app the URP integration with AR Foundation, plus Shader Graph tooling, outweighs Built-in. Critically, AR Foundation's camera-background compositing has had **multiple documented URP-specific bugs on iOS** (black screen, `Unlit/ARKitBackground` Metal pipeline errors, camera background disappearing when stacking cameras), so pin to a current, known-good AR Foundation + URP combination and test on-device early (see §9).

**Shader Graph vs hand-written HLSL.** For a spike at this scope, **Shader Graph is the right default**: it auto-manages render queue/blend state for transparent surfaces, integrates with URP, and is fast to iterate. Drop to hand-written HLSL only if you need a custom blend equation Shader Graph can't express directly (e.g., true Photoshop "soft light"), which you can do via a Custom Function node rather than a full HLSL shader. Recommendation: Shader Graph with one or two Custom Function nodes for the soft-light/overlay math.

**Compositing makeup over the AR camera background.** The ARKit camera feed is drawn by `ARCameraBackground` / `ARBackgroundRendererFeature` as the opaque background. Your makeup material must be in the **Transparent** queue so it draws after the background and blends with it. The face mesh (via `ARFaceMeshVisualizer`) is rendered with your transparent material on top. Because the makeup is transparent and blends with whatever is already in the framebuffer (the camera image), **the blend is happening against the live skin pixels** — which is exactly what you want for multiply/soft-light pigment blending. You do not need to sample the camera texture manually for a basic multiply; `Blend DstColor Zero` (multiplicative) blends your makeup color directly against the camera pixels already in the buffer. For more control (e.g. soft-light, or to read skin tone), sample the camera background texture explicitly.

**Blend mode HLSL formulas** (a = base/destination = skin, b = blend/source = makeup, all in 0–1):
- **Normal (alpha over):** `result = a*(1-α) + b*α`
- **Multiply:** `result = a*b` (darkens; the pigment workhorse)
- **Screen:** `result = 1-(1-a)*(1-b)` (lightens; for highlighter/glow)
- **Overlay:** `result = a<0.5 ? 2ab : 1-2(1-a)(1-b)` (contrast; per-channel)
- **Hard Light:** overlay with a,b swapped: `b<0.5 ? 2ab : 1-2(1-a)(1-b)`
- **Soft Light (Photoshop):** `f(a,b) = (b<0.5) ? 2ab + a²(1-2b) : 2a(1-b) + sqrt(a)(2b-1)` — interpolates between gamma 2 (b=0), gamma 1 (b=0.5), gamma 0.5 (b=1). Pegtop's smoother variant `(1-2b)a² + 2ab` avoids the discontinuity at b=0.5 and is cheaper (no sqrt/branch) — preferred on mobile.

Each is then masked and feathered: `final = lerp(skin, blendResult, maskFeathered * opacity)`.

**Alpha blending / render queue for transparent AR overlays.** Standard transparent setup: `Tags { "Queue"="Transparent" "RenderType"="Transparent" "IgnoreProjector"="True" }`, `ZWrite Off`, `Blend SrcAlpha OneMinusSrcAlpha`. In URP Shader Graph, set **Surface Type = Transparent** (this adds the Alpha block and manages queue/ZWrite automatically). For a pure multiply pigment layer you can instead use `Blend DstColor Zero`. Keep `Cull Back` (the face mesh is single-sided toward camera).

**Color space (critical for perceptual accuracy).** Set Player Settings → **Color Space = Linear**. Blending in gamma space is "not the mathematically correct way to blend colors and can give unexpected results"; linear gives perceptually correct pigment blends and specular falloff. Note iOS supports Linear (Metal); some very old GLES2 Android devices don't, but that's irrelevant for an iPhone target. Convert your hex `color` inputs from sRGB→linear in the shader (or mark color properties as sRGB so Unity does it). Watch the classic gotcha: a value authored to look right in gamma will look different in linear, so author/tune the looks *in* linear.

**Mask textures for ARKit face-mesh UV regions.** AR Foundation exposes the face-mesh texture coordinates via **`ARFace.uvs`** (a `NativeArray<Vector2>`, "parallel to vertices and normals"), backed by the ARKit provider's `ARKitFaceSubsystem.TryGetFaceMeshUVs`. **The ARKit face mesh has 1220 vertices (and 2304 triangles) with a fixed canonical UV layout.** Apple's `ARFaceAnchor`/`ARFaceGeometry` documentation states verbatim: *"Face mesh topology is constant across ARFaceGeometry instances. That is, the values of the vertexCount, textureCoordinateCount, and triangleCount properties never change... and the textureCoordinates buffer always maps the same vertex indices to the same texture coordinates. Only the vertices buffer changes between face meshes."* This means **you paint ONE mask once and it works for every face and frame.** Recommended approach: a single **channel-packed RGBA mask** authored in the canonical face UV space — **R = lips, G = cheeks, B = eyes** (alpha optionally = global blend strength) — sampled in the shader via UV0 and used to gate each region's color/blend. This is the standard Unity idiom (echo3D's AR Foundation face-makeup demo, Unity Learn's "Add a face texture" tutorial). 

**Two important ARKit-specific gotchas the deep-dive surfaced:**
1. **Unity flips the V coordinate** relative to Apple's raw `textureCoordinates` (`uvsOut[i] = (uv.x, 1.0 - uv.y)` in `ARKitFaceSubsystem`'s `TransformUVsJob`). Author/test your mask inside Unity, not against Apple's raw coordinates.
2. **Do NOT reuse ARCore's canonical face PSD** (the widely-circulated `canonical_face_texture.psd` with Mask/Lines/UVs layers) — that is the **468-vertex ARCore** mesh, whose UV layout does NOT match ARKit's 1220-vertex mesh. Get the ARKit unwrap from Apple's "Tracking and Visualizing Faces" sample download, or use a vertex-index tool, then paint your mask against that.

**Feathering / falloff on UV masks.** Don't rely on a hard-edged painted mask alone. Paint the mask with a soft gradient at region boundaries, then in-shader apply `smoothstep(0.5 - feather, 0.5 + feather, maskChannel)` to control edge softness at runtime from your `feather` parameter. This lets one painted mask produce tight lips and soft blush via parameters.

**Texture sampling for finish variation.** Use the optional `texture` field to sample a finish/detail map (e.g., a sparkle texture for shimmer, or a subtle micro-normal for cream sheen). Sample via the same face UV0 or a tiled/triplanar coordinate for sparkle.

## Section 4: Finish Simulation — Practical Mobile Approaches

Finish is defined almost entirely by **specular response + micro-texture**, with base color held constant. TikTok Effect House's "Makeup Palette" template tutorial confirms the mental model verbatim: *"Increasing the Metallic value will create a more glossy look, while increasing the Roughness value will provide a more matte look!"* Mapping for each finish:

**Matte.** Visual: no specular, flat, slightly "absorbs" light. Shader: specular intensity = 0, base color via multiply, no sparkle. Optionally a tiny brightness lift. Cheapest finish.

**Cream / Satin.** Visual: soft, broad sheen — a wide, low-intensity specular lobe. Shader: Blinn-Phong with **low exponent (~8–24)** and moderate intensity (~0.2–0.35). Reads as "natural lipstick/skin-like."

**Gloss.** Visual: tight, bright, mobile hotspot that tracks light/head motion — the "wet" look. Shader: Blinn-Phong with **high exponent (~48–128)** and higher intensity (~0.5–0.9). The half-vector model is the right choice: it's "computationally cheap," "more true-to-life than Phong," and avoids Phong's negative-dot artifact. Formula: `spec = pow(saturate(dot(N, normalize(L+V))), specularPower) * specularIntensity`. Drive light direction `L` from ARKit light estimation (or a fixed key light if estimation is noisy). Because lips are nearly flat in the mesh normal field, you may add a subtle normal map or use the screen-space gradient to localize the hotspot to the lower lip.

**Shimmer / Metallic.** Visual: discrete glints + a base sheen, often a pearl color distinct from base. Shader: sample a **sparkle texture** (small bright dots / high-frequency noise) modulated by `shimmer` strength and a view/half-vector term so glints pop with motion; tint by `shimmerColor`. **Avoid procedural Voronoi-noise glint shaders** — the popular ones explicitly state "Mobile platforms are NOT supported due to the use of procedural noise," and real-time glint research notes these shaders remain "costly compared to smooth PBR ones." A scrolling/static sparkle texture sampled once is the mobile-feasible choice and is also more temporally stable (no crawling).

**Specular model choice.** Use **Blinn-Phong half-vector**, not full microfacet PBR. Mobile PBR-on-skin work (Space Ape's "Physically Based Shading on Mobile") shows teams bake specular into a lookup texture keyed on `[N·H, smoothness]` precisely because per-light GGX is expensive; for 1–2 demo lights, an analytic Blinn-Phong term is cheaper than texture fetches and entirely sufficient for demo quality.

**Roughness/smoothness mapping.** Map `roughness`→exponent inversely: `specularPower = lerp(128, 4, roughness)` (rough = broad/dim; smooth = tight/bright). This single mapping lets the `finish` enum set sensible `roughness` defaults.

**Powder softness.** Suppress specular to ~0, widen feather, and optionally add a faint high-roughness diffuse lift. This is the cheek/blush default.

## Section 5: Skin-Tone-Aware Color Blending

**How pigment interacts with skin tone.** The same lipstick reads differently on different skin because the result is (roughly) pigment × skin reflectance. A multiply blend reproduces this automatically: on deep skin the multiplied result is naturally darker/richer; on fair skin it's lighter — without per-tone tuning. Independent testing repeatedly finds that try-on tools **fail most on deeper skin tones** when they don't respect this. The Algorithmic Justice League's 2023 controlled evaluation of eight try-on platforms (including Ulta GLAMLab, Estée Lauder Try On, and Amazon StyleSnap) across Fitzpatrick I–VI found average color-matching accuracy for foundation/concealer of **89% for Type I skin but only 54% for Type V–VI**, and shade blending was rated "unrealistic or distorting" in a majority of medium-to-deep trials under non-studio lighting. A 2024 ACM *Transactions on Management Information Systems* benchmark similarly found that "over half of users with deep skin tones received foundation recommendations off by ΔE ≥ 8" and that "no app achieved >60% accuracy for Type VI users without manual override." The fix at demo scope is to lean on physically-plausible blending (multiply/soft-light) rather than alpha-over, which is exactly where overlays fail.

**Which blend mode is most realistic for pigment-on-skin?**
- **Multiply** — best default for lips and most pigments. Darkens/tints, preserves luminance and pores. Can over-darken very saturated colors on deep skin (mitigate with `skinAwareness` < 1, mixing in some normal blend).
- **Soft light** — best for sheer/diffuse products like powder blush and subtle eyeshadow; gently darkens or lightens around mid-gray, "very soft compositions," less harsh than overlay. Great for "barely there" looks.
- **Overlay** — punchier contrast; usable but can look harsh/artificial on skin; use sparingly.
- **Screen** — for highlighter/inner-corner glow (lightening only).

So: **lips → multiply; blush → soft light; eyeshadow → multiply (matte) or soft light (sheer); highlighter → screen.** This mirrors what makeup-transfer GANs do implicitly via region histogram matching.

**Consistency across Fitzpatrick types.** A simple, effective correction at demo scope: blend with `skinAwareness` so very dark results retain a floor of chroma, and optionally apply a mild luminance-preserving step (compute makeup result, then restore a fraction of the original skin luma). Avoid the documented "overcorrection" failure mode where uniform brightening destroys undertone — don't normalize brightness globally.

**CIE Lab — worth it?** For a demo/spike: **not worth the cost.** Perceptual Lab blending would improve cross-tone consistency, but it requires sRGB→linear→XYZ→Lab conversions per pixel (and back), which is heavy for a mobile fragment shader and overkill for three demo looks. Linear-space multiply/soft-light captures most of the perceptual benefit at a fraction of the cost. Revisit Lab only if you later build a commercial shade-matching feature.

**Real-time skin-tone sampling from live camera.** Practical approach: sample the AR camera background texture at a few stable face landmarks (e.g., forehead/cheek vertices from the face mesh, which have known UV positions), average over a small neighborhood, and use it to (a) set the `skinAwareness` floor and (b) optionally auto-tune blend weight so saturated pigments don't crush on deep skin. Keep it cheap (a handful of samples, temporally smoothed) to avoid flicker. For the spike, even a single averaged cheek sample is enough to demonstrate tone-awareness.

## Section 6: Region-Specific Rendering (Lip / Cheek / Eye)

**LIP.**
- *UV mask:* lips occupy a clearly identifiable island in the canonical ARKit face UV; paint the red channel of your mask there, with a tight (~0.04–0.08) feather so the lip line stays crisp but not hard.
- *Gloss specular placement:* the wet hotspot should sit on the fuller, lower lip and the cupid's-bow peaks. Because the flat mesh gives weak normals, bias the specular toward the lower-lip region (via a painted gloss-weight in the mask's alpha or a second small texture) and drive it with a half-vector term so it slides with head motion.
- *Matte vs cream vs gloss:* matte = multiply + zero specular; cream = multiply + broad low specular (exp ~16–24); gloss = multiply base + tight bright specular (exp ~64–128). DeepAR's architecture mirrors this — a base "lipstick" material (≈matte) combined with a separate "lip gloss" material layered on top.

**CHEEK / BLUSH.**
- *Feathered mask + gradient math:* blush is the most feather-dependent region. Paint a soft radial gradient in the green channel centered on the apple/cheekbone; apply wide `smoothstep` falloff (`feather` ~0.3–0.4). A radial gradient mask `1 - smoothstep(r0, r1, dist)` gives the natural fade.
- *Powder vs cream blush:* powder = soft light blend, zero specular, widest feather; cream = multiply blend, slight broad sheen (low specular), slightly tighter feather.
- *Placement:* center on the cheekbone/apple. Standard makeup guidance places blush along a cheekbone-to-temple sweep; in mesh terms, anchor the gradient on stable cheek vertices and sweep upward/outward toward the temple. (DeepAR ships ~5–10 blush *shape* masks for exactly this placement variation.)

**EYE / EYESHADOW.**
- *UV islands:* eyes have their own UV islands; paint the blue channel over the lid region. Eye makeup is more forgiving of skin-tone matching than lips/foundation because it "relies less on precise skin-tone matching and more on surface geometry and lighting-independent chroma."
- *Shimmer:* sample the sparkle texture within the lid mask, gated by `shimmer`, tinted by `shimmerColor`. Keep glints subtle and motion-linked.
- *Layering (lid / crease / highlight zones):* for a richer look, split eyeshadow into up to three sub-layers (Banuba and Perfect Corp both support up to 3–5 stacked eyeshadow shades): a base lid color (multiply), a deeper crease shade (multiply, smaller mask), and an inner-corner/brow-bone highlight (screen, often shimmer). For the demo, two layers (lid + subtle shimmer highlight) are enough.

## Section 7: Commercial SDK Parameter Schema Insights

Reference only — do not integrate. The convergent design across vendors strongly validates your schema:

**Banuba (Face AR SDK).** Per-product objects with `color` (RGBA 0–1), `finish` (enum), `coverage` (`low`/`mid`/`high`). Finish enums are product-specific and rich: lipstick `shimmer/matte/cream_shine`; eyeshadow `matte/matte_powder/glitter_metallic/glitter/metallic/glitter_sheer/cream`; eyeliner `matte_liquid/matte_cream/metallic/...`. Lips have presets Matte/Shiny/Glitter plus extended params (color, brightness). Eyeshadow can be an **array up to 3** stacked shades. Confirms: color + finish + coverage as the core triple, finish as an enum that drives a shader, and stacked eye layers.

**DeepAR (Beauty API).** Namespaced params: `lipMakeup.lipstick.{enable, shade(template), amount}`, `faceMakeup.blush.{intensity, color(RGBA 0–255)}`, plus separate `lipGloss`. Lip = base lipstick material (matte-like) + optional gloss layer. Masks are **alpha textures** that exclude eyes/mouth from foundation/smoothing. Confirms: enable/intensity/color per product, template-based presets ("looks" vs "presets"), and gloss as a separate additive layer.

**Perfect Corp (YouCam) — richest finish schema.** Lip-color JSON exposes `texture` enum `[matte, gloss, holographic, metallic, satin, sheer, shimmer]`, `colorIntensity` (0–100), and conditionally-required `gloss` (0–100, when texture is gloss/holographic/metallic/sheer/shimmer), plus `shimmerColor` and `shimmerIntensity` (when holographic/metallic/shimmer). Also `vto_type` Solid/Ombre/Two-Tone and lip morphology. The engine "processes specific vto_type and finish_type (e.g., Matte, Shimmer) to simulate light reflection and texture." Confirms: **separate shimmer color + intensity** (justifying your `shimmerColor` addition) and gloss as a 0–100 scalar.

**TikTok Effect House.** A single `Makeup_Mat` material with properties for Lip, Lip Highlight, Eyeshadow, Eyeshadow Highlight, Eyeliner, Undereye, Cheek, each with **Color + Metallic + Roughness** (PBR-style: metallic↑ = glossy, roughness↑ = matte). Confirms a metallic/roughness mapping is industry-standard and that "highlight" sub-layers for lip and eye are worth modeling.

**Snapchat Lens Studio.** Makeup template exposes lip tint + gloss, blush, eyeliner, eyeshadow, mascara, brow, each with enable/color/intensity; uses Face Mask (2D texture mapped to a face region) and PBR materials with Blend Mode = Normal for transparency. Confirms region-mapped 2D textures + simple per-effect enable/color/intensity is sufficient for convincing looks.

**Net takeaways for your schema:** (1) color + finish(enum) + coverage/intensity is the universal core — you have it; (2) finish should *drive* shader params (metallic/roughness/specular), not be cosmetic — fix this; (3) add separate shimmer color+intensity (Perfect Corp); (4) support stacked layers per region (you already have a layer array); (5) gloss/highlight as its own layer (DeepAR/TikTok).

## Section 8: Demo Look Parameter Recipes

All in your refined JSON schema. Colors are starting points; tune in linear space on-device.

**1. natural_daily** — soft lip tint, light blush, subtle eye shadow.
```json
{ "version":1, "skinSampling":true, "layers":[
  { "id":"lip-tint","region":"lip","color":"#C76B74","opacity":0.45,"coverage":0.7,
    "finish":"cream","blendMode":"multiply","feather":0.10,
    "roughness":0.6,"specular":0.15,"specularPower":16,"shimmer":0.0,
    "skinAwareness":0.8,"enabled":true },
  { "id":"blush-soft","region":"cheek","color":"#E59A98","opacity":0.25,"coverage":0.45,
    "finish":"powder","blendMode":"softlight","feather":0.38,
    "roughness":0.95,"specular":0.0,"specularPower":1,"shimmer":0.0,
    "skinAwareness":0.9,"enabled":true },
  { "id":"eye-subtle","region":"eye","color":"#B08F7E","opacity":0.35,"coverage":0.5,
    "finish":"matte","blendMode":"multiply","feather":0.22,
    "roughness":0.85,"specular":0.05,"specularPower":6,"shimmer":0.0,
    "skinAwareness":0.75,"enabled":true } ] }
```

**2. gloss_lip_focus** — skin-tone-aware lip pigment, visible gloss/specular highlight, controlled opacity/shine.
```json
{ "version":1, "skinSampling":true, "layers":[
  { "id":"lip-base","region":"lip","color":"#B83A55","opacity":0.75,"coverage":0.9,
    "finish":"cream","blendMode":"multiply","feather":0.05,
    "roughness":0.5,"specular":0.25,"specularPower":24,"shimmer":0.0,
    "skinAwareness":0.7,"enabled":true },
  { "id":"lip-gloss","region":"lip","color":"#FFFFFF","opacity":0.6,"coverage":0.7,
    "finish":"gloss","blendMode":"screen","feather":0.06,
    "roughness":0.1,"specular":0.85,"specularPower":96,"shimmer":0.0,
    "skinAwareness":0.0,"enabled":true },
  { "id":"blush-min","region":"cheek","color":"#E0918C","opacity":0.18,"coverage":0.4,
    "finish":"powder","blendMode":"softlight","feather":0.4,
    "roughness":0.95,"specular":0.0,"specularPower":1,"shimmer":0.0,
    "skinAwareness":0.9,"enabled":true } ] }
```
The gloss is modeled as a **second lip layer**: a near-white, high-exponent specular layer (screen blend) over the pigment base — directly mirroring DeepAR's lipstick+gloss split.

**3. soft_blush_shimmer_eye** — feathered blush, powder-like cheek texture, subtle shimmer eye.
```json
{ "version":1, "skinSampling":true, "layers":[
  { "id":"blush-feathered","region":"cheek","color":"#E78B95","opacity":0.4,"coverage":0.55,
    "finish":"powder","blendMode":"softlight","feather":0.42,
    "roughness":0.95,"specular":0.0,"specularPower":1,"shimmer":0.0,
    "skinAwareness":0.85,"enabled":true },
  { "id":"eye-lid","region":"eye","color":"#A77C6A","opacity":0.5,"coverage":0.6,
    "finish":"shimmer","blendMode":"multiply","feather":0.18,
    "roughness":0.7,"specular":0.2,"specularPower":10,
    "shimmer":0.55,"shimmerColor":"#FFE9C8","texture":"sparkle_fine",
    "skinAwareness":0.7,"enabled":true },
  { "id":"eye-highlight","region":"eye","color":"#FFF3E0","opacity":0.35,"coverage":0.3,
    "finish":"shimmer","blendMode":"screen","feather":0.2,
    "roughness":0.4,"specular":0.4,"specularPower":40,
    "shimmer":0.7,"shimmerColor":"#FFFFFF","texture":"sparkle_fine",
    "skinAwareness":0.0,"enabled":true },
  { "id":"lip-nude","region":"lip","color":"#C98A82","opacity":0.4,"coverage":0.7,
    "finish":"cream","blendMode":"multiply","feather":0.08,
    "roughness":0.65,"specular":0.15,"specularPower":18,"shimmer":0.0,
    "skinAwareness":0.8,"enabled":true } ] }
```

## Section 9: Mobile Performance Constraints

**Target & budget.** Aim 60fps (16.6ms) but treat 30fps (33ms) as the floor. Unity's official guidance (Unity Blog, "Optimize your mobile game performance," and "Best practices for profiling game performance") is to use only ~65% of the available frame time to allow for cooldown between frames: *"A typical frame budget will be approximately 22 ms per frame at 30 fps and 11 ms per frame at 60 fps"* — i.e. `(1000/30)*0.65 = 21.66 ms` and `(1000/60)*0.65 = 10.83 ms`. AR face tracking + camera passthrough already consumes a meaningful chunk of CPU/GPU, so the makeup render must be cheap.

**Shader passes.** **One pass is the target.** The whole makeup stack (all enabled layers) should composite in a single transparent face-mesh material; loop/branch minimally over layers inside one fragment shader, or pre-composite layer parameters CPU-side and feed the shader a small fixed set. Transparency = overdraw, which is the main mobile cost; per Unity's mobile art-optimization guidance, "rendering an object with transparency always uses more GPU resources... especially when transparent objects are rendered on top of one another (overdraw)." Keep the face mesh single-layered where possible; the gloss/highlight "second layer" can be a branch inside the same shader rather than a second draw.

**Texture memory budget.** Modest. One channel-packed region mask (R/G/B = lip/cheek/eye) + one shared sparkle texture covers all three looks. Use **ASTC compression** (the iOS/ARM-preferred format) and keep masks at 1024² or 512² (the face mesh UV doesn't need 2K for demo quality). Generate mipmaps. This is a few MB total — negligible.

**Shader complexity ceiling.** Stay unlit + one analytic specular term. Avoid: multiple real-time lights, procedural Voronoi/noise, per-pixel branching over many layers, full PBR/GGX, reflection probes. Mobile PBR teams bake even a single specular lobe into a LUT to save ALU; you can stay analytic with 1 light. Prefer ALU over many texture fetches, but keep both low.

**URP mobile settings.** Enable **SRP Batcher**; disable Depth Texture and Opaque Texture unless needed (a basic multiply doesn't need them — but note soft-light/skin-sampling variants may need the camera/opaque texture, so enable only if used); disable HDR if not needed (or 32-bit if needed); disable extra shadows/MSAA you don't use; strip unused shader variants.

**Known URP + AR Foundation iOS compositing gotchas (test early):**
- **Black screen / background not rendering** on several URP + AR Foundation combos on iOS — recurring across versions; verify `ARBackgroundRendererFeature` is added to the Forward Renderer asset.
- **`Unlit/ARKitBackground` Metal pipeline error** ("depthAttachmentPixelFormat is not valid and shader writes to depth") with certain URP versions — a known issue tied to depth handling.
- **Camera background breaks when stacking cameras / enabling depth texture / URP post-processing** — historically caused black screen or geometry disappearing; several were fixed in specific AR Foundation versions, so use a current known-good combo.
- **Render Graph (URP 17 / Unity 6) glitches** with AR camera image to render texture on iOS — if on Unity 6, validate the render-graph path on-device.
Mitigation: pin a known-good Unity LTS + URP + AR Foundation + ARKit package set, add the background renderer feature, and validate camera passthrough + a trivial transparent overlay on a real iPhone before building the full shader.

## Section 10: Recommended Implementation Path (Spike Roadmap)

**Stage 0 — Foundation validation (de-risk first).** On a real iPhone, confirm URP Forward + AR Foundation + ARKit face tracking renders the camera background AND a trivial transparent material on the face mesh, with `ARFaceMeshVisualizer` feeding `ARFace.uvs` into the mesh UV0. *Gate:* camera passthrough + a flat 50%-opacity colored lip region visible and stable. This catches the URP/iOS compositing bugs before you invest in the shader.

**Stage 1 — Canonical mask + region dispatch.** Obtain the ARKit 1220-vertex UV unwrap (Apple "Tracking and Visualizing Faces" sample, NOT the ARCore PSD). Paint a channel-packed RGBA mask (R=lips, G=cheeks, B=eyes) in Unity-space UVs (remember the V-flip). Wire your existing JSON `region` → mask channel. *Gate:* each region independently tintable from JSON.

**Stage 2 — Pigment blending + feather (the realism unlock).** Implement multiply (lips/eye) and soft-light (cheek) blend paths in Shader Graph (soft light via Custom Function, Pegtop variant). Add runtime `smoothstep` feather from the `feather` param. Linear color space on; convert hex→linear. *Gate:* side-by-side vs. the old alpha overlay shows obvious realism gain — pores/luminance preserved, edges soft. This is the milestone that proves "looks like makeup."

**Stage 3 — Finish simulation.** Add the Blinn-Phong half-vector specular term driven by `specular`/`specularPower`, mapped from `finish`/`roughness`. Add texture-based shimmer (sparkle map + `shimmer`/`shimmerColor`), gated so matte/cream finishes pay nothing. Drive light dir from ARKit light estimation (fallback fixed key light). *Gate:* gloss lips show a moving hotspot; shimmer eye twinkles with motion; powder cheek has zero spec.

**Stage 4 — Skin-tone awareness.** Sample averaged cheek skin color from the camera background; feed `skinAwareness` floor / blend-weight auto-tune. *Gate:* the same gloss_lip_focus recipe looks plausible across at least 3 distinct skin tones without per-tone hand-tuning.

**Stage 5 — Demo looks + polish.** Implement the three recipes from §8 as selectable presets via your RN↔Unity JSON channel. Profile on-device (target ≤11ms at 60fps, hard floor ≤22ms at 30fps); confirm single-pass, ASTC masks, SRP Batcher on. *Gate:* enterprise stakeholders see three distinct, convincing looks switchable in real time at stable framerate.

**Benchmarks / thresholds that change the plan:**
- If on-device frame time > 22ms with the full stack → collapse layers further (pre-composite params CPU-side), drop shimmer to static (no view term), reduce mask to 512².
- If gloss hotspot looks flat/static → add a small lip normal map or screen-space gradient to localize the highlight; consider ARKit light estimation if you were using a fixed light.
- If deep-skin shades crush to black → lower `skinAwareness`, mix in normal blend, add chroma floor; only then consider a heavier perceptual (Lab) path.
- If URP camera background fails on target iOS → fall back to the known-good AR Foundation/URP version pin from Stage 0, or (last resort) Built-in RP with manual background blit.

## References

- Wikipedia, "Blend modes" — multiply/screen/overlay/hard-light/soft-light formulas (Photoshop & Pegtop soft-light variants).
- Photoblogstop, "Photoshop Blend Modes Explained" — blend-group behavior.
- Unity Manual — "ShaderLab: Blending"; "Blending Modes in URP"; "Linear or gamma workflow"; "Differences between linear and gamma color space"; "Specular" (lipstick specularity example); "Configure for better performance" (URP mobile); "Art optimization tips for mobile game developers" (overdraw/transparency).
- Unity Blog, "Optimize your mobile game performance" (June 23, 2021) and "Best practices for profiling game performance" — 65% frame-budget rule (~11ms @60fps, ~22ms @30fps).
- Daniel Ilett, "Shader Graph Basics Part 3 – Transparency & Alpha"; Wikibooks "Cg Programming/Unity/Transparency"; NedMakesGames, "Writing Unity URP Shaders... Part 3" (render queues, ZWrite Off).
- Unity Shader Graph docs — "Feature Examples" (smoothstep falloff masks); Godot Shaders "Circle Mask with Feathering" (smoothstep mask idiom).
- AR Foundation docs — `ARFace.uvs`; `ARKitFaceSubsystem.TryGetFaceMeshUVs`; ARKit face tracking; "Configuring AR Camera Background with SRP." Apple Developer — `ARFaceAnchor`/`ARFaceGeometry` (textureCoordinates, vertexCount, constant-topology quote: "Face mesh topology is constant across ARFaceGeometry instances... the textureCoordinates buffer always maps the same vertex indices to the same texture coordinates"), "Tracking and Visualizing Faces."
- GitHub — Unity-Technologies/arfoundation-samples Issue #631 (UV stability); needle-mirror `ARKitFaceSubsystem.cs` (V-flip TransformUVsJob, supportsFaceMeshUVs); echo3Dco/Unity-ARFoundation-echo3D-demo-Face-Makeup; Unity Learn "Create with AR Face Filters."
- Unity Discussions / Issue Tracker — URP+AR Foundation iOS black-screen and `Unlit/ARKitBackground` Metal errors; camera-background-with-camera-stacking bug; URP 17 render-graph iOS glitches.
- Banuba docs — "Makeup Prefabs" (finish enums, coverage), "Virtual Makeup API" (RGBA color, blush/eyeshadow/lipstick). DeepAR docs — "Ultimate Beauty," "DeepAR Beauty API" (lipMakeup/blush params, alpha masks). Perfect Corp/YouCam API — lip_color JSON (texture enum, gloss, shimmerColor/shimmerIntensity). TikTok Effect House — "Makeup Palette" (Color/Metallic/Roughness, verbatim metallic/roughness quote). Snap Lens Studio — "Makeup" template, "Materials Overview."
- Makeup transfer — BeautyGAN (Li et al., ACM MM 2018; pixel-level histogram loss on eye/lip/skin regions); Sun et al., "Disentangled Makeup Transfer" (arXiv:1907.01144, identity-preservation quote); PSGAN (arXiv:1909.06956); "Lipstick ain't enough" (arXiv:2104.01867, UV-space blending).
- Blinn-Phong references — Wikipedia "Blinn–Phong reflection model"; LearnOpenGL "Advanced Lighting"; Medium/spaceapetech "Physically Based Shading on Mobile" (LUT-baked specular keyed on N·H/smoothness). Real-time glint — arXiv:2306.05051; Nightshift "Glitter Shader" (procedural noise not mobile-supported).
- Skin-tone accuracy testing — Algorithmic Justice League 2023 evaluation of 8 try-on platforms (Fitzpatrick I–VI; 89% vs 54% color-match accuracy); 2024 ACM *Transactions on Management Information Systems* benchmark (ΔE ≥ 8 for >half of deep-skin users; <60% accuracy for Type VI without override), via Alibaba product-insights audit summaries.
- Unity mobile profiling/optimization — Medium "Profiling Mobile Games (Unity)"; DEV "Mobile Game Optimization Checklist" (fps targets, ASTC/ETC2 compression).