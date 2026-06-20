# Beauty AR Engine Benchmark Report - 한국어

Date: 2026-06-20 KST

Status: 공개 자료 기반 리서치 / 구현 전 단계

Scope: Meitu, Instagram/Meta, TikTok, Snapchat, Perfect Corp, Banuba, DeepAR, MediaPipe, Apple ARKit, Google ARCore의 공개 AR effect engine, face tracking, makeup rendering 구조를 비교한다. RN + Unity + AR Foundation 기반 v1 AR makeup engine 설계에 참고할 교훈만 정리한다. 이 문서는 제품 구현, 유료 SDK 통합, AI/backend/admin/payment/community 구현을 시작하지 않는다.

## 1. Executive Summary

상용/소셜 뷰티 AR 엔진의 공통 패턴은 분명하다.

- 얼굴 추적은 단순 bounding box가 아니라 face landmarks, dense face mesh, blendshape/expression, face/skin/lip/eye segmentation 중 여러 신호를 조합한다.
- 메이크업 렌더링은 "얼굴 전체에 색상 material 하나"가 아니라 lip, cheek, eye, brow, skin/foundation, lashes, teeth 등 region layer로 나뉜다.
- region layer는 color, opacity/intensity/coverage, finish, texture, mask, blend mode, feather/softness 같은 parameter contract를 가진다.
- creator ecosystem은 face anchors, face mesh/face mask reference texture, material/shader editor, segmentation object, visual scripting, performance QA를 제공한다.
- 모바일 실시간 성능은 feature 수, segmentation 수, texture resolution, package size, shader sampling, PBR/lighting, mesh complexity를 강하게 제한한다.

우리 프로젝트에 바로 도입 가능한 경로는 현재 검증 중인 Apple ARKit + Unity AR Foundation 경로다. MediaPipe는 fallback/reference로 직접 도입 가능성이 있지만, RN + Unity + iPhone validation의 현재 primary path를 대체할 이유는 아직 없다. TikTok Effect House, Instagram/Meta Spark, Snapchat Lens Studio는 플랫폼 effect ecosystem이다. TikTok과 Snapchat은 참고 가치가 크지만, TikTok/Instagram 내부 런타임은 우리 앱에 직접 넣을 수 없다. Snap Camera Kit은 별도 SDK로 가능성이 있지만 Snap branding/app review/SDK 조건을 받아들여야 하므로 현재 validation scope 밖이다. Perfect Corp, Banuba, DeepAR는 상용 SDK 후보지만, 부트캠프 research prototype의 직접 구현 대상으로 보지 않고 benchmark로만 둔다.

현재 우리 v1에서 따라야 할 핵심은 `ARFace` 기반 tracking을 먼저 정확히 맞추고, 그 위에 region layer renderer를 얹는 것이다. 따라하지 말아야 할 것은 상용 SDK의 전체 beauty suite, AI makeup transfer, 피부/조명/색상 matching을 v1부터 복제하려는 접근이다. 먼저 `lip`, `cheek`, `eye`의 작고 검증 가능한 region layer를 만든 뒤, texture/shader/segmentation은 단계적으로 붙여야 한다.

## 2. 조사 대상과 출처 신뢰도

| Source tier | Meaning | Used for |
| --- | --- | --- |
| A. 공식 개발자 문서/API 문서 | engine/runtime 기능, SDK capability, performance limit을 가장 신뢰한다. | TikTok Effect House, Snap Lens Studio/Camera Kit, Banuba, DeepAR, MediaPipe, Unity AR Foundation/ARKit XR Plug-in, ARCore |
| B. 공식 회사/제품/기술 페이지 | 제품 기능과 상용 제공 범위는 신뢰하되, 내부 구현 상세는 단정하지 않는다. | Meitu MTLab, Perfect Corp Makeup AR/Face Analyzer |
| C. 공식 공지 URL + 현재 접근 상태 | 현재 정책 상태 확인에 사용한다. 본문 추출이 어려운 경우 접근 가능한 URL, redirect/404 상태, 보조 출처를 함께 기록한다. | Meta Spark / Instagram AR ecosystem |
| D. 보조 매체/2차 출처 | 공식 문서가 사라졌거나 동적 페이지라 검증이 어려운 정책 이력 보강에만 사용한다. | Meta Spark 2025 shutdown details |

중요한 제한:

- Meitu, Instagram/TikTok 내부 production app runtime은 closed/proprietary다. 공개 문서로 확인되지 않는 내부 mesh topology, shader, model architecture는 쓰지 않는다.
- "내부 자체 엔진"이라고 표현하는 경우는 Meitu MTLab처럼 공식 페이지가 자체 연구/SDK를 설명하는 경우로 제한한다.
- "추측"은 추측이라고 표시한다. 이 문서에서는 제품 구현 판단에 필요한 항목은 대부분 "미공개" 또는 "참고만 가능"으로 처리한다.
- Instagram/Meta Spark 상태는 2026-06-20 기준으로 재확인했다. 구 Meta Spark docs는 `developers.facebook.com/docs/ar-studio/`가 Spark 도메인으로 redirect되고, 일부 세부 경로는 404 또는 domain resolution failure 상태였다.

## 3. Engine / SDK / Tooling 비교표

| Service | Public Engine/Tool | Own Engine or SDK | Face Tracking Basis | Makeup Regions | Texture/Shader Support | Mobile Runtime Notes | Can We Use It? | Lessons for Our Engine |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Meitu / Meitu Xiuxiu / BeautyPlus 계열 | MTLab 기술군: `MTface`, `MT3D`, `MTAR`, `MTsegment`, `MTbeauty`, `MTmakeup` | Meitu 자체 기술/closed engine. `MTAR`는 Meitu AI 기술과 결합한 cross-platform rendering SDK라고 공식 페이지가 설명 | `MTface`: face detection, face landmarks, face attributes. `MT3D`: 3D face reconstruction, expression/features analysis. `MTsegment`: skin/hair/facial feature segmentation. 구체 topology는 미공개 | `MTmakeup`은 face points, semantic segmentation, 3D reconstruction, image fusion 기반으로 makeup/face swap 등 portrait editing을 한다고 공개됨. 상세 region schema는 미공개 | 공개 페이지는 image fusion/AR rendering SDK/segmentation을 말하지만 shader/material editor는 공개하지 않음 | 제품 검증 규모와 일 호출량은 공개되지만 low-level mobile budget은 미공개 | 불가능 / closed. 벤치마크만 가능 | 자체 face landmark + segmentation + 3D reconstruction + image fusion 조합이 핵심. 우리도 region mask 전에 face basis를 확정해야 함 |
| Instagram / Meta AR effects | Meta Spark / Spark AR Studio, Meta Spark Hub. 2025-01-14 이후 third-party Spark effects/tooling 지원 종료로 분류 | 과거 플랫폼 effect tool. 현재 Instagram third-party AR effect ecosystem은 신규 도입 불가로 봄. Meta in-house effects는 closed | 과거 Spark는 face filter/effect authoring platform이었지만 현재 공식 세부 docs 접근이 불안정하다. 이 보고서에서는 face topology count를 단정하지 않음 | 과거 face filter/makeup-style effects 가능. 현재 third-party Instagram effect 배포 경로는 closed | 과거 Spark Studio는 authoring tool 성격. 현재 신규 우리 앱 engine으로 사용 불가 | 공식 AR Studio root는 redirect, 세부 경로는 404/접근 실패가 섞임. 최신 정책상 direct dependency로 삼으면 안 됨 | 불가능 / closed. 참고만 가능 | 플랫폼 의존 creator ecosystem은 shutdown risk가 크다. 우리 v1은 자체 recipe/render contract를 가져야 함 |
| TikTok / ByteDance Effect House | TikTok Effect House | 플랫폼 effect creator tool. TikTok runtime은 closed, Effect House authoring docs는 공개 | Face Binding anchors, Face Mask, 3D Face Binding, Face Detection/Face Info visual scripting, face effects, segmentation objects. 상세 internal tracker는 closed | Lip Effect, Eye Effect, Eyelash Effect, Eye Color, Face Retouch, Teeth Whitening, Lip/Eye/Skin/Teeth segmentation 등 region/object 단위 | Material Editor, GLSL-based shader concepts, Face Paint material, texture/opacity/UV/blend/render-state, visual scripting | Effect package <= 8 MB, image <= 1025 KB, image resolution <= 1024x1024, max supported FPS 30, segmentation high performance impact, face effects max 5 권장 | 참고만 가능. TikTok effect로 배포는 가능하지만 우리 RN app runtime에 직접 도입하는 SDK는 아님 | region object + material/shader + performance QA를 v1 설계의 좋은 기준으로 삼는다 |
| Snapchat Lens Studio / Snap Camera Kit | Lens Studio, Snap Camera Kit | Lens Studio는 platform authoring tool. Camera Kit은 iOS/Android/Web SDK로 Snap AR engine을 app에 넣는 commercial/platform SDK | Face Effects, Face Mesh, 93 Face Landmarks, Face Expressions, Eye Tracking, Face Texture, multi-face support | Face Retouch, Eye Color, Face Mask, Face Liquify, Face Stretch, Face Inset. Face Mask는 realistic makeup에도 사용 가능 | Face Mask texture, opacity texture, blend modes, material editor, mesh optimization, Draco compression | 3D/texture optimization docs. Camera Kit은 Snap branding required and app review workflow 있음 | 가능성 있음. 하지만 현재 validation scope 밖이고 Snap dependency/branding/review를 받아야 함 | face mask texture + opacity texture + blend mode + alpha controls가 v1 makeup layer contract의 좋은 reference |
| YouCam / Perfect Corp | Makeup AR, Virtual Makeup Try-On, Live 3D Face AR, Face AI, AI Face Analyzer | Proprietary commercial beauty SDK/SaaS | 공식 제품 페이지는 360 face tracking, AR facial detection, 70+ facial structure points/traits, landmarks/structure analysis를 공개. 상세 mesh는 미공개 | lip color, eye makeup, colored contacts, foundation/shade matching, skin tone analysis, virtual makeover | Realistic textures/finishes: matte, metallic, satin, sheer, gloss, shimmer, holographic 등. 내부 shader는 미공개 | web/app compatibility, real-time try-on, device-agnostic marketing claims. Low-level budget은 미공개 | 가능하지만 상용/유료. 현재는 benchmark only | commercial makeup renderer는 region + finish + shade/texture matching을 제품 단위로 모델링한다. v1도 finish enum을 미리 열어둔다 |
| Banuba | Banuba Face AR SDK, Banuba Studio, EffectPlayer | Commercial Face AR SDK. EffectPlayer는 C++ low-level effect player with platform bindings | SDK runs recognition operations on input frames. API has face_data landmarks, camera position, face rect, lips detected, face presence. Public docs expose makeup masks/prefabs | Makeup prefabs: foundation, concealer, contour, highlighter, blush, lipstick, lip liner, eyeshadow, eyelashes, eyeliner, eyebrows, lip shine/gloss 등 | JSON-like makeup prefab parameters: color, finish, coverage, alpha, liner width/softness, gloss masks. Studio/Asset Store available | EffectPlayer is async/multithreaded when available. Makeup base has `speed` vs `quality` mode | 가능하지만 commercial SDK. 현재는 benchmark only | region prefab + typed parameters가 우리 `MakeupRecipe` 설계에 가장 직접적이다 |
| DeepAR | DeepAR SDK, DeepAR Studio, DeepAR Beauty API | Commercial SDK/effect player + Studio/Beauty API | ML/deep learning tracks face position and facial expressions frame-by-frame, then renders 2D/3D graphics over camera feed | Beauty API: skin smoothing, face morphing, face makeup, eye makeup, lip makeup, eye coloring, background blur/removal | Parameter namespaces include foundation/blush/highlighter/contour applicationArea textures, colors/intensity, eyeliner/eyeshadow/eyelashes textures, lipstick shade/gloss textures | Official performance table says users must test in own apps; iPhone 13 Pro iOS face tracking/beautification measured at 30 FPS capped | 가능하지만 commercial SDK. 현재는 benchmark only | parameter namespace separation is useful: `faceMakeup`, `eyeMakeup`, `lipMakeup`, `skinSmoothing`, `colorFilters` |
| Google MediaPipe | MediaPipe Face Landmarker | Open/research/developer framework, not makeup engine | 478 3D landmarks, blendshape scores, facial transformation matrices, face detection + face mesh + blendshape model bundle | No built-in makeup regions. Regions must be built from landmarks/mesh/masks by us | No built-in beauty shader. Can drive custom renderer | Live stream mode, mobile GPU optimized BlazeFace detector, smoothing only when `num_faces=1` | 가능. But requires own renderer and integration complexity | fallback/reference topology. Good for non-AR static analysis or cross-platform landmark experiments |
| Apple ARKit via Unity AR Foundation | ARKit Face Tracking through Unity AR Foundation + Apple ARKit XR Plug-in | Platform SDK/provider already selected in this repo | ARKit provider supports face pose, face mesh vertices/indices, UVs, normals, eye tracking, blend shapes. Requires user-facing camera. Device requirements depend on iOS/hardware | No makeup renderer by itself. We must map regions to ARFace mesh/UV/blendshape state | Unity material/shader stack can render our region masks/layers | ARKit face tracking requires user-facing camera. ARKit XR Plug-in exposes blend shapes 0..1. Unity as Library has full-screen/single-runtime caveats | 가능. Current primary path | Use current validation path. Fix AR camera alignment before region rendering |
| Google ARCore Augmented Faces | ARCore Augmented Faces, including Unity AR Foundation guides | Platform SDK/provider, Android/iOS docs available | Center pose, three region poses, 468-point dense 3D face mesh, feature points, no specialized hardware | No makeup renderer by itself. It supports textures/models over face regions | Supports custom textures and 3D models; renderer is app-owned | Useful for beauty/accessory try-ons; Android path mostly. Not current iPhone target | 참고만 가능 now. Android future candidate | Confirms industry pattern: center/region poses + dense mesh + texture overlay |

## 4. Face Tracking Capability 비교

| Service | 공개 확인된 tracking primitives | 미공개/주의 | 우리 설계 의미 |
| --- | --- | --- | --- |
| Meitu | `MTface`는 face detection, landmarks, attributes. `MT3D`는 3D face reconstruction. `MTsegment`는 skin, hair, facial features segmentation. `MTmakeup`은 face points, semantic segmentation, 3D reconstruction, image fusion 사용 | Landmark count, mesh topology, blendshape schema, realtime renderer API는 공개되지 않음 | "landmark만"으로는 부족하다. v1도 mesh/UV/region/segmentation 중 최소 2개 축을 함께 봐야 함 |
| Instagram / Meta | 과거 Spark AR effect platform. 현재 세부 공식 docs 접근 불안정 | 현재 third-party Instagram AR effect ecosystem을 dependency로 잡으면 안 됨 | 플랫폼 AR authoring tools are not durable product architecture |
| TikTok Effect House | Face Binding anchors: face center, eyes, forehead, mouth center, chin, ears. Face Detection/Face Info/Facial Movement/Expression visual scripting. 3D face/mask/effects/segmentation objects | TikTok internal tracker and model topology are closed | v1 debug UI는 face anchor/region state를 보여줘야 함 |
| Snapchat | Face Mesh resource mimics facial expression in realtime. Face Landmarks are 93 points in screen space. Face Expressions and Eye Tracking are first-class effects | Snap internal ML model not exposed | landmark IDs, face found/lost events, face index are useful v1 diagnostics |
| Perfect Corp | 360 face tracking, AR facial detection, 70+ facial structure points/traits, facial landmarks/structure analysis | Mesh/shader internals 미공개 | commercial engines expose higher-level face traits, not raw mesh. 우리는 raw mesh 기반에 recipe를 얹어야 함 |
| Banuba | EffectPlayer runs recognition; API exposes face landmarks, ears landmarks, camera position, face rect, has face, has lips detected | Full model internals closed | API contract에 `hasFace`, `hasLips`, `faceRect`, `cameraPosition` 같은 debug fields를 두는 것이 좋음 |
| DeepAR | ML/deep learning tracks face position and facial expressions frame-by-frame | Landmark count/mesh topology not exposed in public Beauty docs | expression/position tracking과 rendering을 frame-by-frame pipeline으로 분리해야 함 |
| MediaPipe | Complete face mesh, 478 3D landmarks, 52 blendshape scores, facial transformation matrix | Makeup regions are not provided | ARKit alignment이 실패하면 fallback comparison 기준으로 좋음 |
| Apple ARKit / Unity | Face pose, mesh vertices/indices/UVs/normals, eye tracking, blend shapes | Device support and camera selection caveats | v1 primary: `ARFace` mesh/UV + blendshape + face state |
| ARCore Augmented Faces | Center pose, 3 region poses, 468-point dense 3D mesh | Current project is iPhone-first; Android out of scope | region pose + dense mesh pattern is a useful abstraction |

우리 v1 face basis recommendation:

1. 먼저 AR camera pose alignment를 고친다.
2. `ARFaceManager.trackablesChanged`에서 added/updated/removed trackable id, tracking state, vertex count, transform을 log한다.
3. 한 얼굴만 지원하는 v1이면 `maxFaceCount = 1`을 명시적으로 UX/engine decision으로 둔다.
4. `lip`, `cheek`, `eye` region을 ARFace mesh/UV basis로 분리한다.
5. face lost/recovered 상태를 RN으로 보내기 전에는 product makeup work를 시작하지 않는다.

## 5. Makeup Renderer Capability 비교

| Service | Public makeup renderer model | Parameter clues | Lesson |
| --- | --- | --- | --- |
| Meitu | face points + semantic segmentation + 3D reconstruction + image fusion로 portrait makeup/editing | Makeup, accessories, hairstyle recommendation are mentioned. Exact parameters closed | v1 renderer는 "image fusion" 수준을 바로 목표로 하지 말고 alignment + region mask + blend를 먼저 검증 |
| TikTok | Face Effects objects and Segmentation objects. Lip Effect is a Face Mask with Face Region = Lips. Lip segmentation isolates lips for custom textures/effects | texture, material, opacity, UV, blend/render state, segmentation material | object-level region layer가 좋다. `layer=lip`는 실제 lips mask/renderer에 연결되어야 함 |
| Snapchat | Face Mask maps 2D texture to face and can create realistic makeup. It has texture, opacity texture, blend mode, alpha, draw mouth, face index | Anchor points and automatic face detection for mask mapping | opacity texture + blend mode + alpha are v1 essentials |
| Perfect Corp | commercial AR makeup with color blending, realistic texture/finish matching, lighting-aware "smart 3D AR engine", skin tone analysis | matte, metallic, satin, sheer, gloss, shimmer, holographic finish list | finish should be modeled separately from color/opacity, but not fully simulated in v1 |
| Banuba | Makeup prefabs per region. `color`, `finish`, `coverage`; lip liner softness/width; gloss mask parameters; makeup base speed/quality | foundation, concealer, contour, highlighter, blush, lipstick, lip liner, eyeshadow, eyelashes, eyeliner, eyebrows, lip shine/gloss | Strongest direct recipe inspiration. Use typed region params, not ad hoc UI state |
| DeepAR | Beauty API namespaces: `faceMakeup`, `eyeMakeup`, `lipMakeup`, `skinSmoothing`, `colorFilters`, `background` | applicationArea textures, RGBA colors, intensity/amount, shade/gloss textures | Namespaces and textures separate cleanly. Our recipe should mirror this separation |
| MediaPipe / ARKit / ARCore | Tracking primitives only. No makeup renderer | Need app-owned region masks/materials/shaders | Our engine must own renderer and recipe contract |

Suggested v1 `MakeupRecipe` direction:

```json
{
  "version": 1,
  "layers": [
    {
      "id": "lip-primary",
      "region": "lip",
      "color": "#D94B74",
      "opacity": 0.65,
      "intensity": 0.7,
      "finish": "cream",
      "blendMode": "multiply",
      "feather": 0.12,
      "texture": null
    }
  ]
}
```

V1 region scope:

- `lip`: highest priority because Effect House, Snap, Banuba, DeepAR, Perfect Corp all expose lip/lipstick/lip segmentation/lip makeup as first-class.
- `cheek`: blush/highlighter/contour are common and useful, but edges must be soft.
- `eye`: eyeshadow/eyeliner/eye color/eyelash are common but more expensive and alignment-sensitive. Keep first v1 eye layer simple.

Explicit non-goals for v1:

- foundation shade matching
- skin smoothing/acne/texture correction
- relighting
- full product finish simulation
- generative makeup transfer
- multi-face social effects
- AI recommendation

## 6. Creator Tool / Shader / Material Workflow 비교

| Service | Creator/tool workflow | Shader/material signals | What to copy |
| --- | --- | --- | --- |
| TikTok Effect House | Add object from hierarchy: Face Effects, Segmentation, AR Capability. Material Editor and Visual Scripting exist. | Material Editor is GLSL-based; Face Paint has texture, tint color, opacity texture, UV tiling/offset/rotation, depth test/write, blend mode | Build our Unity inspector/debug surface around region objects and material params |
| Snapchat Lens Studio | Add Face Mask/Face Effects; adjust face mask anchor points; use helper reference files; Camera Kit deploys lenses into apps | Face Mask texture + opacity texture + blend mode + alpha. Material Editor and mesh optimization docs | Maintain face mask reference texture/UV atlas for each region |
| Banuba | Effect prefabs and JSON-like settings; Banuba Studio and Asset Store | Region prefabs with typed color/finish/coverage | Use declarative layer schema and named presets |
| DeepAR | SDK plays DeepAR effects; Beauty API changes parameters; Studio exports effects | Parameter namespaces and textures | Separate API params from renderer implementation |
| Perfect Corp | Commercial web/app modules and SDK/API integrations | Product-facing textures/finish/lighting claims, internals closed | Avoid copying internals; copy UX parameter categories only |
| Meitu | MTLab internal technologies and AI open platform link | Rendering SDK mentioned but details closed | Benchmark architecture pattern, not implementation |
| MediaPipe / ARKit / ARCore | Developer SDKs, no makeup creator tool | App-owned shaders/materials | Our Unity project must create the creator/debug tooling itself |

Unity v1 authoring implication:

- Use one debug prefab/renderer per region before collapsing into a single optimized shader.
- Keep `region`, `mask`, `material`, `blendMode`, `opacity`, `feather`, `texture` visible in Unity inspector or debug overlay.
- Store mask/UV references as assets with clear names instead of hard-coded magic vertex lists.
- Add a source-of-truth region map document after alignment is fixed.

## 7. License / Commercial / Closed Platform 제약

| Service | Use classification | Constraint |
| --- | --- | --- |
| Meitu | 불가능 / closed | Official pages show proprietary MT Lab technology. No public engine integration path found for our app. |
| Instagram / Meta Spark | 불가능 / closed | Third-party Spark ecosystem is no longer a safe dependency. Existing docs/routes are unstable; in-house Meta effects are closed. |
| TikTok Effect House | 참고만 가능 | Useful for learning authoring patterns, but effects run in TikTok platform, not our RN app. |
| Snapchat Camera Kit | 가능성 있음 | Cross-platform SDK exists, but requires Snap account/app review/branding/SDK terms and changes architecture. Out of current milestone. |
| Perfect Corp | 가능하지만 commercial | Enterprise/eCommerce product. Direct integration would be vendor dependency and paid/commercial scope. |
| Banuba | 가능하지만 commercial | Face AR SDK can be integrated technically, including Unity paths, but license/commercial scope required. |
| DeepAR | 가능하지만 commercial | SDK/Beauty API available, but paid/commercial dependency. |
| MediaPipe | 가능 | Open developer stack, but not a full makeup renderer. Integration complexity is ours. |
| Apple ARKit / Unity AR Foundation | 가능 / current path | Platform SDK path already being validated. Must handle device requirements and Unity as Library lifecycle caveats. |
| ARCore Augmented Faces | 참고만 가능 now | Android/cross-platform future candidate, not iPhone v1 scope. |

Decision:

- Do not integrate commercial SDKs in this repo now.
- Do not switch to TikTok/Instagram/Snap platform authoring as the product engine.
- Keep ARKit/AR Foundation primary.
- Keep MediaPipe/ARCore as fallback/comparison references only.

## 8. 우리 프로젝트에 반영할 설계 교훈

1. Tracking and rendering must be separate.
   - Face tracking state, face mesh/UV/blendshape, region mask, material rendering, and RN recipe updates should be separate layers.
   - Current M5 implementation mixes recipe color with whole-face diagnostic material. That is fine for M5 but not for product v1.

2. Region layer is the core abstraction.
   - Commercial engines do not expose a single "makeup color" knob. They expose lip/foundation/blush/eyeshadow/eyeliner/brow/lash/skin layers.
   - Our v1 should start with `lip`, `cheek`, `eye`, not a full face mask.

3. A recipe needs typed parameters.
   - Minimum: `region`, `color`, `opacity`, `intensity`, `blendMode`, `feather`, `texture`, `finish`.
   - Optional later: `coverage`, `applicationArea`, `roughness`, `metallic`, `normal`, `gloss`, `linerWidth`, `softness`.

4. Alignment is a gate, not a cosmetic bug.
   - Current M5 screen recording shows overlay offset. Industry tools assume a stable face basis before makeup layers.
   - Product makeup work must wait until AR camera pose/face mesh alignment is Green.

5. Segmentation is powerful but expensive.
   - Effect House explicitly marks segmentation as high performance impact and warns against combining it with many other algorithms.
   - V1 should prefer mesh/UV region masks first. Use live segmentation only if a region cannot be represented acceptably.

6. Performance constraints must be designed into the recipe.
   - Limit initial face effects/layers.
   - Avoid PBR and heavy shader sampling.
   - Use small textures and merged masks.
   - Provide a quality/speed mode later, inspired by Banuba's makeup base mode.

7. Platform ecosystems are not product architecture.
   - Meta Spark shutdown is the strongest warning. A creator ecosystem can disappear even if effects were popular.
   - Our engine contract should survive vendor/platform policy changes.

## 9. RN + Unity + AR Foundation 경로와의 차이

| Benchmark ecosystem | Their path | Our path | Gap to close |
| --- | --- | --- | --- |
| TikTok / Snapchat creator tools | Built-in face effects, masks, anchors, materials, QA and publishing pipeline | Unity project must build its own face region renderer and debug tools | Need region map assets, material presets, performance checks |
| Meitu / Perfect Corp | Full proprietary beauty AI stack with face tech, segmentation, 3D reconstruction, image fusion, skin tone/shade matching | ARKit face tracking + custom Unity renderer, no commercial beauty AI | Do not attempt full stack. Only copy architecture categories |
| Banuba / DeepAR | SDK effect player + beauty/makeup API parameters | Unity renderer plus RN recipe contract must act as our effect player | Need typed recipe and Unity-side layer dispatcher |
| MediaPipe | ML face landmarks/blendshapes/matrices, no ARKit-specific runtime | ARKit/AR Foundation provides iOS native face mesh/blendshape | Use MediaPipe only if ARKit route fails or for offline analysis |
| ARCore | 468 mesh/region poses for Android | Current target is iPhone ARKit | Future Android design can reuse the region layer abstraction |

Current repo-specific implications:

- `TECH_VALIDATION_RESULT.md` records M5 Green only for RN -> Unity communication, not makeup readiness.
- Current visual AR makeup readiness is Yellow/Fail because the overlay is offset and not region-specific.
- M6 should still be Unity -> RN communication, not makeup rendering.
- Before region rendering, the next AR-specific follow-up is camera pose alignment and `ARFaceManager.trackablesChanged` diagnostics.
- After M6/M7/M8, product v1 engine work should begin with a small ARFace mesh/UV region renderer proof, not a beauty suite.

## 10. Recommended Takeaways for v1

Recommended v1 scope:

| Decision | Recommendation |
| --- | --- |
| Runtime | Continue RN host + embedded Unity + AR Foundation + ARKit on iPhone. |
| Face basis | Use ARKit/AR Foundation `ARFace` mesh/UV/blendshape data first. |
| Regions | Start with `lip`, `cheek`, `eye` only. |
| Rendering | Use separate debug region renderers/materials first; optimize later. |
| Recipe | Move from single JSON `{layer,color,opacity}` to versioned multi-layer `MakeupRecipe`. |
| UI controls | Keep color/opacity, then add intensity/feather/blend mode only after alignment is fixed. |
| Performance | One face, small textures, <= 3 initial layers, unlit/simple transparent materials, no segmentation in first pass. |
| Fallback | MediaPipe Face Landmarker only if ARKit mesh/UV cannot support region rendering. |
| Commercial SDKs | Do not integrate in this validation repo. Keep as benchmark only. |

v1 Green criteria for makeup engine research after current validation milestones:

- AR camera feed and `ARFace` mesh overlay are aligned on iPhone.
- Unity logs face added/updated/removed trackable ids and mesh vertex counts.
- RN receives `unity_initialized`, `face_detected`, and `recipe_applied`.
- `lip` region color/opacity changes without affecting whole face.
- `cheek` region soft mask renders without hard edges.
- `eye` region renders a simple color/texture overlay without severe drift.
- Closing/reopening AR screen does not break face tracking or recipe application.

Do not call v1 makeup renderer ready if:

- the mask is offset from the visible face,
- `layer` still applies to the entire face material,
- face lost/recovered state is invisible to RN,
- second-face/reacquisition behavior is unknown,
- performance cannot stay near the target frame rate on the real iPhone.

### Final Required Conclusions

1. Meitu / Instagram / TikTok 계열이 공통적으로 의존하는 AR makeup engine 패턴

   Meitu, Instagram/Meta Spark, TikTok Effect House 계열의 공통 패턴은 face tracking primitive 위에 region-aware effect layer를 얹는 구조다. Meitu는 face landmarks, semantic segmentation, 3D reconstruction, image fusion을 공식적으로 말한다. TikTok은 Face Binding, Face Mask/Lip Effect, segmentation, material/shader workflow를 공개한다. Instagram/Meta는 현재 third-party Spark ecosystem이 닫혔지만, 과거 AR effect platform 자체는 face filter/effect authoring을 중심으로 했다. 공통점은 "얼굴 전체 material 하나"가 아니라 tracking + region + texture/material + effect parameter + mobile QA 구조다.

2. 우리 v1에서 반드시 따라야 할 패턴

   우리 v1은 ARKit/AR Foundation의 face mesh/UV/blendshape basis를 먼저 안정화하고, `lip`, `cheek`, `eye` region layer를 typed `MakeupRecipe`로 구동해야 한다. 각 layer는 `color`, `opacity`, `intensity`, `blendMode`, `feather`, `texture`, `finish`를 갖도록 설계하되, 첫 구현은 color/opacity/intensity 정도로 제한한다. Tracking state, region mask, material rendering, RN messaging은 분리해야 한다.

3. 우리 v1에서 따라하지 말아야 할 패턴

   상용 SDK의 full beauty suite, AI makeup transfer, foundation shade matching, relighting, skin smoothing, multi-face social filters, platform-specific creator publishing을 v1에 따라 하면 안 된다. Instagram/TikTok/Snap 같은 closed platform runtime에 제품 architecture를 의존해서도 안 된다. 현재 offset diagnostic overlay 위에 makeup quality work를 얹는 것도 금지다.

## 11. Source Appendix

### Meitu / Meitu Xiuxiu / BeautyPlus 계열

- Meitu MTLab official homepage: https://mtlab.meitu.com/
  - Used for `MTface`, `MT3D`, `MTAR`, `MTsegment`, `MTbeauty`, `MTmakeup`.
  - Key facts used: MTLab is Meitu's algorithm research center; `MTface` includes face detection, landmarks, attributes; `MT3D` includes 3D reconstruction/depth estimation; `MTAR` combines Meitu AI with a cross-platform rendering SDK for AR/virtual try-on/ARKit/ARCore businesses; `MTsegment` segments body/skin/hair/facial features; `MTmakeup` uses face points, semantic segmentation, 3D reconstruction, image fusion for portrait makeup/editing.

### Instagram / Meta

- Meta official update URL checked: https://developers.facebook.com/blog/post/2024/08/27/meta-spark-update/
- Old AR Studio root checked: https://developers.facebook.com/docs/ar-studio/
  - Observed during this run: official AR Studio root redirects to `https://sparkar.facebook.com/ar-studio/learn`; some detailed routes returned 404 or could not resolve.
- Secondary corroboration for shutdown details: The Verge, "Meta is ending support for custom face filters in its apps", 2024-08-27: https://www.theverge.com/2024/8/27/24229643/meta-spark-ar-effects-face-filters-shutdown-tiktok-snapchat
  - Used only because the official dynamic content was not reliably extractable in CLI. Core decision: do not depend on Meta Spark/Instagram third-party effects.

### TikTok / ByteDance Effect House

- Effect House introduction: https://effecthouse.tiktok.com/learn/
- Lip Effect: https://effecthouse.tiktok.com/learn/guides/workspace/objects/face-effects/lip-effect
- Face Binding: https://effecthouse.tiktok.com/learn/guides/workspace/components/ar-capability/face-binding
- Lip Segmentation: https://effecthouse.tiktok.com/learn/guides/workspace/objects/segmentation/lip-segmentation
- Face Paint material: https://effecthouse.tiktok.com/learn/guides/workspace/assets/material/face-paint
- Material and Shader Concepts: https://effecthouse.tiktok.com/learn/guides/editor-panels/material-editor/material-and-shader
- Technical Optimization: https://effecthouse.tiktok.com/learn/guides/getting-started/technical-guidelines/technical-optimization

### Snapchat / Snap

- Lens Studio Face Effects Overview: https://developers.snap.com/lens-studio/references/guides/lens-features/tracking/face/face-effects-overview
- Face Mask: https://developers.snap.com/lens-studio/references/guides/lens-features/tracking/face/face-effects/face-mask
- Face Landmarks: https://developers.snap.com/lens-studio/4.55.1/references/guides/lens-features/tracking/face/face-effects/face-landmark
- 3D Optimization: https://developers.snap.com/lens-studio/4.55.1/references/guides/lens-features/optimization/3d-meshes
- Camera Kit overview: https://developers.snap.com/camera-kit/getting-started/what-is-camera-kit

### Perfect Corp / YouCam

- Makeup AR: https://www.perfectcorp.com/business/products/makeup-ar
- Virtual Makeup Try-On: https://www.perfectcorp.com/business/products/virtual-makeup
- AI Face Analyzer: https://www.perfectcorp.com/business/products/ai-face-analyzer
- AI Skin Analysis: https://www.perfectcorp.com/business/products/ai-skin-analysis

### Banuba

- Banuba Face AR SDK: https://docs.banuba.com/far-sdk/
- Makeup Prefabs: https://docs.banuba.com/far-sdk/effects/prefabs/makeup/
- Effects overview: https://docs.banuba.com/far-sdk/effects/overview/
- Face data API reference: https://docs.banuba.com/far-sdk/generated/doxygen/html/classbnb_1_1interfaces_1_1face__data.html

### DeepAR

- DeepAR SDK introduction: https://docs.deepar.ai/deepar-sdk/introduction/
- DeepAR Beauty features: https://docs.deepar.ai/deepar-beauty/features/
- DeepAR Beauty parameters: https://docs.deepar.ai/deepar-beauty/parameters/
- DeepAR performance: https://docs.deepar.ai/deepar-sdk/specification/performance/

### Google / MediaPipe / ARCore

- MediaPipe Face Landmarker: https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker
- ARCore Augmented Faces: https://developers.google.com/ar/develop/augmented-faces

### Apple / Unity ARKit path

- Unity AR Foundation Face Tracking: https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.3/manual/features/face-tracking.html
- Unity Apple ARKit XR Plug-in Face Tracking: https://docs.unity3d.com/Packages/com.unity.xr.arkit@6.3/manual/arkit-face-tracking.html
- Apple ARKit Tracking and Visualizing Faces: https://developer.apple.com/documentation/arkit/tracking-and-visualizing-faces
