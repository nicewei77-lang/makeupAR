# iPhone AR 메이크업 엔진의 얼굴 부위 트래킹 품질 리서치

## Executive summary

현재 당신의 엔진 상태를 기준으로 보면, **주 경로는 계속 Unity + AR Foundation + ARKit iPhone 경로로 유지하는 것이 맞다**는 결론입니다. 이미 저장된 검증 결과에서 RN host 앱, Unity embedded 화면, ARKit face tracking, RN↔Unity JSON 교환, `lip`·`cheek`·`eye` 독립 제어, texture sample dispatch, `FaceFeatureSnapshot` handoff까지는 실기기 기준으로 확인되었고, 다만 E3/E4의 마스크는 여전히 “넓은 debug mask”이며 제품 품질의 정밀 경계는 아직 입증되지 않았습니다. M0~M6은 Green, M7은 Yellow로 남아 있으며, E6 전체 판정도 “방향성은 유효하지만 제품 준비 완료는 아님”으로 정리되어 있습니다. fileciteturn0file1

공식 문서 기준으로 AR Foundation의 face tracking은 **face pose**, **mesh vertices/indices**, **UVs**, **eye tracking**, **blend shapes**를 ARKit에서 지원하며, `ARFaceManager.trackablesChanged`와 `ARFace.updated`, `trackingState`를 통해 얼굴 추가·업데이트·제거와 “보였다/잠시 잃었다/다시 찾았다” 상태를 추적할 수 있습니다. 즉, **“얼굴에 붙어서 따라다니는 3D 기반 부위 마스크”를 만드는 데 필요한 핵심 토대는 이미 ARKit/ARFace 쪽에 존재**합니다. citeturn2view0turn2view1turn2view2turn19view1

다만 실무적으로 보면, **ARFace mesh/UV만으로 곧바로 제품급 메이크업 경계를 얻을 수 있다고 보는 것은 과도한 기대**입니다. 가장 현실적인 해법은 **ARFace mesh + UV 기반의 정적 region atlas를 주축으로 쓰고**, 표현 변화는 blend shape·tracking state·간단한 시간 필터로 보정하는 방식입니다. 이 접근은 **cheek 블러시**에는 특히 잘 맞고, **lip**도 충분히 현실적이지만, **eye/eyeshadow는 가장 높은 리스크**를 가집니다. 눈 부위는 경계가 얇고, 깜빡임·속눈썹·상안검 주름·eyeliner에 가까운 미세 경계 때문에 mesh/UV만으로는 제품급 선명도를 얻기 어렵기 때문입니다. 이 평가는 현재 당신의 repo에서 “부위 분리는 됐지만 범위가 넓고 정확하지 않다”는 실기기 관찰과도 맞아떨어집니다. fileciteturn0file1 citeturn2view1turn19view1turn25academia0turn25academia1turn25academia2

실무 추론으로 정리하면, 이번 E7 “Visual Product-Readiness Spike”에서 가장 실용적인 목표는 다음입니다. **Runtime primary는 ARFace 유지**, **region 표현은 UV mask atlas 기반**, **lip/eye는 blendshape-aware edge correction**, **cheek는 feather-heavy soft zone**, **lost/recovered는 state machine + hysteresis**, **smoothing은 저차원 신호 위주로 최소 적용**입니다. MediaPipe Face Landmarker나 2D face parsing은 지금 당장 runtime primary로 갈아탈 대상이 아니라, **오프라인 레퍼런스·mask authoring helper·fallback 비교군**으로 두는 편이 비용 대비 이득이 큽니다. MediaPipe는 3D landmarks, blendshape scores, facial transformation matrices를 내놓고, smoothing도 single-face 설정에서 적용하도록 설계돼 있어 비교 기준으로는 매우 유용하지만, 현재 스택에 또 하나의 실시간 추적 체인을 추가하는 비용이 작지 않습니다. citeturn8view0turn9view0turn9view1

확인된 사실과 실무 추론을 분리해 한 줄로 요약하면 이렇습니다. **확인된 사실**: ARKit/ARFace는 region mask를 만들 수 있을 정도의 3D face data를 Unity에 제공합니다. **실무 추론**: 제품급 정밀 lip/eye/cheek을 얻으려면 “ARFace mesh/UV만 사용”이 아니라, “ARFace mesh/UV를 중심으로 한 authored mask + expression-aware stabilization”이 필요합니다. citeturn2view0turn2view1turn2view2turn19view1

## Source matrix

| Source | Type | Reliability | What it contributes | Implementation guidance or reference |
|---|---|---:|---|---|
| Unity AR Face Manager 6.3.5 citeturn2view0 | Official Unity doc | Very high | `ARFaceManager`, `trackablesChanged`, face prefab, max face count | Implementation guidance |
| Unity AR Face 6.3.5 citeturn2view1 | Official Unity doc | Very high | `ARFace.updated`, `trackingState`, face mesh representation, custom visualizers | Implementation guidance |
| Unity Face Tracking Platform Support 6.3.5 citeturn2view2 | Official Unity doc | Very high | Which optional face features ARKit exposes at runtime | Implementation guidance |
| Unity Face Tracking Samples 6.3.5 citeturn2view3 | Official Unity sample doc | Very high | Face pose, face mesh, ARKit blend shapes, eye poses, rear-camera config sample | Implementation guidance |
| Unity Scene Setup 6.3.4 citeturn3view0 | Official Unity doc | Very high | AR Session + XR Origin hierarchy requirement | Implementation guidance |
| Unity XR Origin reference 2.5.3 citeturn3view1 | Official Unity doc | Very high | Recommended hierarchy including `TrackedPoseDriver`, `ARCameraManager`, `ARCameraBackground` | Implementation guidance |
| Unity Camera Components 6.3.5 citeturn3view2 | Official Unity doc | Very high | Front-camera selection, background rendering, render mode | Implementation guidance |
| Unity as a Library iOS manual citeturn3view3 | Official Unity doc | Very high | `UnityFramework`, `runEmbeddedWithArgc`, `pause`, `unloadApplication`, full-screen limitation | Implementation guidance |
| Apple ARKit XR Plug-in 6.3.4 / Face tracking supplement citeturn19view0turn19view1 | Official Unity provider doc | Very high | ARKit-specific face feature support, front-camera requirement, blend shape semantics | Implementation guidance |
| Apple Developer ARKit face pages citeturn5view0turn5view1turn5view2turn5view3 | Official Apple doc | Very high, but low extractability here | Primary Apple references for face tracking/geometry/blend shapes; current browser snapshot exposed only JS gate | Reference |
| MediaPipe Face Landmarker guide citeturn8view0 | Official Google doc | High | 478 landmarks, 52 blendshapes, transformation matrices, live stream modes, smoothing when `num_faces=1` | Reference and possible fallback guidance |
| ARCore Augmented Faces intro citeturn9view0turn9view1 | Official Google doc | High | Conceptual comparison: center pose, region poses, dense face mesh for texture following | Reference |
| CelebAMask-HQ repo citeturn13view0 | Dataset repo | High for dataset/license facts | 19 classes including eyes, mouth, lip, skin; non-commercial license constraints | Reference only |
| LaPa repo + paper abstract citeturn13view1turn14view3turn15academia0 | Dataset repo + paper | High | 22k-scale face parsing, 11 labels, 106 landmarks, non-commercial terms | Reference only |
| BiSeNet face parsing repo citeturn14view4turn14view5 | Open-source repo | Medium-high | Practical CelebAMask-HQ face parsing baseline; MIT code, dataset-dependent weights | Reference only |
| SegFace repo citeturn14view6turn14view7turn14view8 | Open-source repo | Medium-high | More recent face segmentation benchmark results on CelebAMask-HQ/LaPa; MIT code | Reference only |
| PSGAN / SARA / AvatarMakeup / BeautyBank abstracts citeturn25academia0turn25academia1turn25academia2turn25academia3 | Research papers | Medium-high | Why spatial alignment, part-specific control, shade control, and UV/view consistency matter for makeup | Reference only |
| Your validation result document fileciteturn0file1 | Internal repo evidence | Very high for current state | What is already proven, why E6 stays Yellow, mesh counts observed on device, broad-mask limitation | Implementation reality check |
| Your validation test plan fileciteturn0file0 | Internal planning doc | High | Scope boundaries, iPhone-first assumptions, full-screen Unity usage | Scope and acceptance guidance |
| Prior internal research docs fileciteturn0file2 fileciteturn0file3 | Internal research context | Medium-high | Historical reasoning: keep ARKit primary, alignment/lifecycle before renderer work | Supporting context |

## ARKit and ARFace capability summary

### Capability summary

| Data or signal | Available through Unity + AR Foundation + ARKit | Confidence | Why it matters for makeup regions | Notes |
|---|---|---:|---|---|
| Face transform / pose | Yes (`supportsFacePose`) citeturn2view2turn19view1 | High | Whole-face attachment under head translation/rotation | Foundational for keeping masks attached |
| Mesh vertices and indices | Yes (`supportsFaceMeshVerticesAndIndices`) citeturn2view2turn19view1 | High | Region geometry, barycentric lookup, UV atlas sampling | Core signal for all three regions |
| Mesh UVs | Yes (`supportsFaceMeshUVs`) citeturn2view2turn19view1 | High | Stable authored mask atlas in texture space | Most important path for authored masks |
| Mesh normals | Optional; do not assume without runtime check citeturn2view1turn2view2turn19view1 | Medium | Useful for shading, rim decisions, but not essential for region identity | Treat as bonus, not dependency |
| Blend shapes | Yes (`supportsBlendShapes`) citeturn2view2turn19view1 | High | Mouth-open/eye-closure style deformation hints; local correction | Best used as deformation hints, not primary mask basis |
| Eye tracking / eye pose | Yes if supported on device; ARKit samples include eye pose / fixation demos citeturn2view2turn2view3turn19view1 | High | Eye-region orientation, gaze-linked effects, blink-aware stabilization | Helpful for eye region, not a full eyelid boundary solver |
| `trackablesChanged` | Yes citeturn2view0turn2view1 | High | Lost/recovered/reenter state machine | Mandatory for robust lifecycle handling |
| `ARFace.updated` | Yes citeturn2view1 | High | Per-face mesh update timing | Best place to update local region state |
| `trackingState` | Yes; face may become Limited instead of removed citeturn2view1 | High | Hysteresis and graceful loss handling | Critical for temporary camera loss |
| Front-camera session requirement | Yes, unless specific ARKit configuration chooser cases are used citeturn19view1turn2view3 | High | Practical session design for selfie makeup flow | Matches your iPhone-first use case |
| Unity embedded lifecycle controls | Yes: run, pause, unload, show window citeturn3view3turn20view0 | High | Re-entry and RN-hosted lifecycle hardening | Matters because M7 is still Yellow in repo evidence fileciteturn0file1 |

### Confirmed facts from your repo

현재 repo 실기기 증거는 “데이터 파이프라인은 이미 충분히 살아 있다”는 점을 뒷받침합니다. E5 스냅샷에는 `vertexCount=1220`, `indexCount=6912`, `uvCount=1220`, `stableUv=true`, `regions=lip,cheek,eye`, texture sample summaries가 실려 있고, 동시에 E3/E4는 이 마스크들이 아직 broad debug 수준이라고 분명히 적고 있습니다. 즉, **‘정밀도’가 아직 문제이지, ‘부착용 3D 얼굴 데이터가 없다’가 문제는 아닙니다.** fileciteturn0file1

### What the data is realistically good at

ARFace mesh/UV는 **부위가 얼굴에 붙어 다니는 것**에는 강합니다. 머리 회전, 전후 이동, 표정 변화와 함께 부위를 공면적으로 움직이게 하고, UV 공간에서 mask를 안정적으로 샘플링하는 데 적합합니다. Unity 공식 문서가 mesh vertices/indices/UVs 지원을 명시하고, ARFace가 face mesh visualizer나 custom mesh renderer 기반의 face visualization을 직접 지원하는 것도 그 이유입니다. citeturn2view1turn2view2turn2view3

반대로 ARFace mesh/UV는 **의미론적 경계 그 자체**를 알려주지는 않습니다. “여기가 정확한 vermilion border, 여기가 정확한 upper lid crease, 여기가 blush should stop 되는 cheekbone line” 같은 정보는 mesh/UV에 자동으로 딸려오지 않습니다. 그래서 실제 제품급 결과는 **authored region definition**이 필요하고, 표정 변화가 큰 영역은 blendshape-aware local correction이 추가되어야 합니다. 이 점은 최신 makeup transfer 연구들이 반복해서 강조하는 “spatial alignment”, “region-adaptive control”, “shade-controllable / part-specific control”, “view/expression consistency”와도 일치합니다. citeturn25academia0turn25academia1turn25academia2turn25academia3

### Where ARFace is likely insufficient

가장 대표적인 부족 지점은 **눈 주변의 얇은 경계**입니다. 아이섀도우 자체는 구현 가능하지만, eyelid crease·lash line·inner/outer corner·blink 순간의 얇은 면적 변형을 제품급으로 잡으려면 ARFace mesh/UV만으로는 한계가 빨리 옵니다. 이때 필요한 것은 대개 더 많은 “semantic” 정보이지, 더 많은 “머리 전체 pose” 정보가 아닙니다. 그래서 eye가 가장 높은 리스크입니다. 이에 비해 cheek는 경계가 원래 부드러워 mesh/UV 기반 soft zone에 잘 맞고, lip은 eye보다 구조가 명확하지만 mouth open/close와 inner mouth edge 처리에서 보정이 필요합니다. 이 평가는 실무 추론입니다. citeturn2view1turn19view1turn25academia0turn25academia1

## Lip cheek eye tracking strategy

### Strategy table

| Region | Best basis | Expected under head rotation | Expected under expression | Edge / feather requirement | Main failure modes | Recommended validation scenarios | Practical verdict |
|---|---|---|---|---|---|---|---|
| Lip | **Primary:** UV mask atlas on ARFace mesh. **Secondary:** blendshape-aware lip-edge correction. citeturn2view1turn2view2turn19view1 | Strong, because lip mask rides the same tracked mesh as the face. citeturn2view1turn2view2 | Good for broad lipstick region; weaker around inner mouth and cupid’s bow during mouth opening. Blend shapes help. citeturn19view1turn25academia0 | Medium. Lipstick edges look wrong quickly if hard or bleeding. | Inner-mouth spill, cupid’s bow drift, lower-lip/teeth exposure mismatch, overpaint during smile/open mouth | neutral, smile, mouth open/close, phoneme-like lip stretches, profile turn, face lost/recovered | **Feasible with ARFace primary path** |
| Eye | **Primary:** UV mask atlas for upper-lid / under-eye zones. **Secondary:** eye pose + blink/wink-like blendshape stabilization. citeturn2view2turn2view3turn19view1 | Strong at coarse zone level, weaker at thin lash-line detail. | Weakest of the three for precise cosmetic edges because blink and eyelid deformation are aggressive. citeturn19view1turn25academia1 | High. Hard edges look obviously fake; feather must be expression-aware. | Upper-lid drift, blink collapse, eyeliner-like misregistration, eyelash/occlusion artifacts | blink, squint, wink, wide-open eye, left-right gaze, head pitch down/up, temporary occlusion by hand/hair | **Highest-risk region** |
| Cheek | **Primary:** UV or vertex-cluster soft zone on ARFace mesh. **Secondary:** optional pose-relative recentering. citeturn2view1turn2view2 | Very strong for broad blush placement. | Usually robust because cheek deformation is smoother than lips/eyes. | Very high feather, but low boundary precision requirement. | Too-low/too-high blush placement, crossing nose fold, over-spill toward under-eye or jawline | head yaw/pitch, smile, partial profile, near/far movement, face out/in | **Lowest-risk region for stable validation** |

### Region-by-region recommendation

**Lip**은 이번 스파이크에서 “제품 가능성 확인”에 가장 적합한 타깃입니다. 이유는 분명합니다. lip은 얼굴 중앙에 있고, 회전에도 비교적 잘 보이며, mask가 잘못되어도 실패 원인이 관찰되기 쉽습니다. ARKit blend shape가 0..1 스케일의 facial action 값을 제공하고 “mouth open” 같은 신호를 설명하고 있기 때문에, lip은 **UV mask를 기본으로 두고 mouth-open 계열 신호로 edge expansion/shrink를 걸어 주는 하이브리드**가 가장 실용적입니다. 다만 정확한 lip liner 수준은 이번 E7 범위를 넘어섭니다. citeturn19view1turn2view3

**Eye**는 “아이섀도우의 broad zone”까지는 가능하지만, 정교한 cosmetic edge는 위험합니다. Unity 문서상 ARKit는 eye tracking과 eye pose 샘플을 제공하고, blend shapes도 지원하므로, 눈의 방향과 깜빡임 상태를 부가 신호로 쓰는 것은 가능합니다. 하지만 이것은 어디까지나 “stabilization clue”이지, 상안검 주름의 정확한 semantic contour를 제공하는 것은 아닙니다. 그래서 eye는 **broad eyeshadow / under-eye tint / soft halo** 쪽으로 validation 목표를 좁히는 편이 맞습니다. citeturn2view2turn2view3turn19view1

**Cheek**는 가장 실용적입니다. blush는 애초에 feathered zone으로 보이는 경우가 많아서, perfect semantic boundary보다 **안정적인 위치와 부드러운 falloff**가 더 중요합니다. 즉 cheek는 2D parsing이나 dense landmark 없이도 ARFace mesh/UV 기반으로 충분히 Yellow→Green validation이 가능합니다. 다만 제품 단계에서 “광대 중심 / 콧방울 거리 / 눈 아래 간격” 같은 미세 배치까지 요구하면, 그때는 오프라인 semantic reference가 도움이 될 수 있습니다. citeturn2view1turn25academia1turn25academia3

## Architecture comparison and recommended Unity path

### Architecture comparison table

| Approach | Strengths | Weaknesses | Best use in this spike | Verdict |
|---|---|---|---|---|
| ARFace mesh vertex/UV region map | Native to current stack, face-attached in 3D, follows pose/expression, no extra ML runtime citeturn2view1turn2view2turn19view1 | Requires authored region map; semantics are not automatic | Core validation path | **Primary** |
| Submesh / material separation | Clear debugging per region; easy to see layer independence | Runtime mesh splitting is more complex; edge seams more likely | Debug stage, not final production path | **Useful for debug only** |
| UV mask texture atlas on one face mesh | Best balance for stability, feather, layered shading, texture samples | Requires one-time authoring and shader work | Best medium-term implementation path | **Best practical target** |
| Separate region renderers | Easy debugging and per-layer enable/disable | More draw calls, ordering/alpha problems, overlap artifacts | Validation-only instrumentation | **Secondary** |
| Screen-space 2D segmentation overlay | Easy to prototype semantic masks offline | Poor 3D attachment under rotation; duplicates ARFace tracking path | Reference comparison only | **Not primary runtime** |
| MediaPipe hybrid runtime | Rich landmarks, blendshapes, transform matrices; cross-platform topology citeturn8view0 | More integration complexity, another tracker to reconcile, more device/runtime cost | Only if ARFace path fails on precision or future shared topology need emerges | **Fallback / comparison** |

### Recommended Unity implementation path

가장 실용적인 경로는 **“하나의 ARFace mesh + 하나의 UV mask atlas + region-aware shader”**입니다. 먼저 canonical face topology 위에 `lip`, `cheek`, `eye` 각각의 grayscale mask를 authoring하고, runtime에는 ARFace mesh의 UV를 사용해 같은 atlas를 샘플링하면 됩니다. 이 방식은 현재 AR Foundation이 보장하는 vertices/indices/UV support를 그대로 활용하고, head rotation과 face pose를 별도 2D warping 없이 해결할 수 있습니다. citeturn2view1turn2view2turn19view1

이번 E7 스파이크에서는 production shader를 완성할 필요가 없습니다. 대신 아래 순서가 가장 안전합니다. **첫째**, 현재 broad debug mask 대신 UV atlas 기반의 hard-color region mask로 교체합니다. **둘째**, region별 alpha/feather 채널을 붙입니다. **셋째**, `matte_lip`, `soft_blush`, `shimmer_eye` 같은 validation texture sample을 atlas/shader 위에서 재적용합니다. 이렇게 하면 E3/E4에서 이미 증명된 region/texture dispatch를 같은 face-attached 좌표계 위로 끌어올릴 수 있습니다. fileciteturn0file1

`blend shapes`는 주 표현 좌표계가 아니라 **보정 신호**로 쓰는 편이 좋습니다. lip에서는 mouth-open 정도에 따라 상·하순 mask를 소폭 축소/팽창시키고, eye에서는 blink/wink 계열 값에 따라 eyelid 근처 feather 영역을 살짝 조정하는 식입니다. Unity의 ARKit face tracking 문서가 blend shapes를 0..1 facial action 값으로 설명하고, 샘플도 այդ 값을 눈·표정 표현에 사용하는 만큼, 이 용도는 문서와 잘 맞습니다. citeturn19view1turn2view3

iOS host 구조 측면에서는 **AR 화면을 계속 full-screen screen/modal로 유지**하는 것이 맞습니다. Unity as a Library는 iOS에서 full-screen rendering limitation을 명시하고 있고, `@azesmway/react-native-unity`도 iOS에서 built `UnityFramework`를 사용하며 view dimensions가 0이면 crash risk가 있다고 경고합니다. 당신의 test plan도 full-screen Unity screen을 기준으로 짜여 있습니다. 그러므로 “부분 화면에 예쁘게 삽입하는” 방향보다, **전체 AR 화면 하나를 안정적으로 유지하면서 RN control overlay를 얹는 방향**이 더 안전합니다. citeturn3view3turn20view0 fileciteturn0file0

현재 repo evidence를 보면 lifecycle과 framework sync가 아직 완전히 닫히지 않았습니다. 이 점 때문에 추천 구현 경로는 “새 추적기 추가”가 아니라 “현재 추적기 위의 region 표현을 정교화”입니다. 다시 말해, **문제의 중심은 tracking substrate 부재가 아니라 mask representation과 stabilization 품질**입니다. fileciteturn0file1

## Fallbacks and temporal smoothing

### Fallback trigger table

| Trigger | What it means | Recommended response | Why |
|---|---|---|---|
| Lip mask가 mouth open/close에서 반복적으로 inner-mouth로 새어 들어감 | ARFace UV alone is not enough for local lip correction | Keep ARFace primary, add offline lip contour reference or MediaPipe comparison for lip control points | Cheapest escalation path citeturn8view0turn19view1 |
| Eye shadow가 blink/squint에서 계속 붕괴 | Eye region needs stronger semantic or landmark guidance | Test MediaPipe offline/reference against the same iPhone clips; do not replace runtime immediately | Eye is the highest-risk region citeturn8view0turn19view1turn25academia1 |
| Cheek zone is stable but badly placed across face shapes | Semantic placement, not tracking, is the issue | Use offline face parsing references such as LaPa/CelebAMask-HQ for authoring heuristics | Parsing is better as authoring/reference than runtime primary citeturn13view0turn15academia0 |
| Lost/recovered produces visible pop or stale mask | Lifecycle handling is weak | Improve `trackablesChanged` + `trackingState` hysteresis before considering new tracker | Platform already exposes correct lifecycle primitives citeturn2view0turn2view1 |
| Need future shared topology across iOS and Android | Platform-specific mesh becomes organizational bottleneck | Introduce MediaPipe as shared reference topology, not necessarily primary iOS runtime | MediaPipe outputs canonical landmarks + transform matrices citeturn8view0turn9view0 |
| Need pixel-semantic explanation for offline QA or authoring | Runtime geometry lacks semantic labels | Use face parsing datasets/models offline only | That is what face parsing is naturally good at citeturn13view0turn15academia0turn14view5 |

### Temporal smoothing recommendations

가장 먼저 추천하는 것은 **“모든 vertex를 세게 필터링”이 아니라, 저차원 제어 신호만 가볍게 안정화하는 것**입니다. `trackingState`, active face ID, face pose, selected local anchors, blendshape coefficients 같은 신호는 비용이 낮고 튜닝이 쉽습니다. 반대로 매 프레임 1000+ vertices 전체를 공격적으로 평활하면 lag가 빠르게 눈에 띄고, 입이나 눈처럼 빠르게 변하는 부위에서 “늦게 따라오는 마스크”가 생깁니다. ARFace가 per-face updates를 제공하고, lifecycle도 added/updated/removed와 Limited 상태를 명시하므로, 안정화는 이들 저차원 신호 위에 얹는 것이 맞습니다. 이 부분은 실무 추론입니다. citeturn2view0turn2view1

권장 순서는 간단합니다. **face pose에는 아주 약한 EMA**, **blendshape 계수에는 약한 EMA 또는 비대칭 attack/release**, **tracked/lost visibility에는 hysteresis**입니다. 특히 Unity 문서가 face가 removed 대신 `Limited`가 될 수 있다고 명시하므로, lost 순간 즉시 mask를 끄기보다 **짧은 grace window**를 두는 편이 더 자연스럽습니다. 예를 들면 2~3 프레임 또는 100~200ms 정도의 “hold”를 두고, 그 안에 tracking이 회복되면 기존 region을 유지합니다. citeturn2view1

MediaPipe 문서가 `num_faces=1`일 때 smoothing을 적용한다고 밝히는 점도 참고할 만합니다. 이것은 face AR에서 **single-face 환경에서는 filtering이 일반적으로 이득**이라는 간접 근거입니다. 다만 MediaPipe 수준의 smoothing 체계를 그대로 이식할 필요는 없고, 이번 스파이크에서는 **EMA + hysteresis만으로도 충분**할 가능성이 큽니다. citeturn8view0

One Euro filter나 Kalman filter는 “없으면 안 되는 필수 요소”는 아닙니다. 이번 축에서는 이 둘을 **후순위 실험 옵션**으로 두는 편이 낫습니다. 만약 EMA만으로는 jitter가 남고, 더 강하게 평활하면 lag가 거슬린다면, 그때 **face pose 또는 소수의 region anchor**에만 적용하는 방식으로 시험하는 것이 맞습니다. 전체 mesh에 먼저 들이대는 접근은 추천하지 않습니다. 이 부분은 실무 추론입니다. AR tracking lifecycle 자체는 이미 플랫폼에서 제공하므로, 먼저 상태기계와 경량 smoothing으로 얻을 수 있는 이득을 다 쓰는 편이 효율적입니다. citeturn2view0turn2view1turn8view0

## Validation criteria, risks, and spike plan

### Real-device validation checklist

| Validation item | What to test on a real iPhone | Pass condition |
|---|---|---|
| Lip boundary | neutral, smile, mouth open/close, speech-like motion | Upper/lower lip region stays attached and does not spill clearly into teeth/inner mouth most of the time |
| Eye region | blink, squint, look left/right/up/down, head pitch | Eye zone remains plausible and does not jump on blink; small soft drift acceptable in E7 |
| Cheek region | smile, yaw, pitch, partial profile | Blush zone remains face-attached and feathered without sharp seams |
| Head rotation | yaw left/right, pitch up/down, slight roll | Region masks stay glued to face under motion |
| Lost/recovered | face leaves frame, returns after short and medium gap | Mask fades/holds gracefully; no stale mask floating in space |
| Re-entry | AR enter → close → re-enter repeated | No crash, no black screen, region state resets correctly |
| Tracking state telemetry | log `trackablesChanged`, `trackingState`, active face ID | Face lifecycle is explainable from logs, not guessed |
| Performance | runtime observation and at least coarse FPS/thermal note | No obvious collapse in interactive use; enough headroom for validation |
| Privacy guardrail | snapshot path only, no raw frame persistence | Continue `rawCameraFrameStored=false`, `offDeviceUpload=false` style discipline from current evidence fileciteturn0file1 |

### Green yellow red decision criteria

| Axis | Green | Yellow | Red |
|---|---|---|---|
| Lip | Stable, attached, believable under open/close and turns | Works in neutral/light motion but breaks on larger expression | Cannot remain attached or repeatedly spills badly |
| Eye | Broad eyeshadow zone remains stable through normal blink/motion | Works only in narrow poses or drifts at blink | Cannot maintain believable eye-area placement |
| Cheek | Soft zone stays attached with good feather | Attached but placement tuning still weak | Fails to remain face-attached |
| Lifecycle | Lost/recovered and re-entry are visually controlled and logged | Recoverable but with visible pop or unresolved caveat | Stale masks, unexplained state, or repeated breakage |
| Overall E7 | ARFace primary path is good enough to continue hardening toward product renderer work | Path remains viable but eye/lip still need fallback/reference work | ARFace path fails to support stable region preservation in practice |

### Open risks and unknowns

가장 큰 미지수는 여전히 **eye region의 제품급 정밀도**입니다. Unity/ARKit는 eye tracking과 blend shapes를 제공하지만, 그것만으로 thin cosmetic boundary가 충분한지는 공식 문서만으로 확정할 수 없습니다. 이 부분은 실기기 validation이 필요합니다. citeturn2view2turn2view3turn19view1

두 번째 리스크는 **topology authoring effort**입니다. 공식 문서는 mesh/UV availability를 보장하지만, `lip`·`cheek`·`eye`의 “좋은 region atlas”는 결국 직접 만들어야 합니다. 현재 repo evidence가 broad masks를 보여준다는 점은, 바로 이 authoring/validation 문제가 아직 남아 있음을 뜻합니다. fileciteturn0file1

세 번째는 **iOS embedded lifecycle**입니다. Unity as a Library는 full-screen limitation과 single runtime instance limitation을 명시하고 있고, `react-native-unity`도 iOS पर UnityFramework 배치와 non-zero parent dimensions 같은 조건을 요구합니다. 현재 repo에서 M7이 formal Green이 아니라는 점도 이 리스크를 이미 보여 줍니다. 따라서 E7 결과를 “tracking quality Green”으로 올리더라도, lifecycle caveat는 별도로 닫아야 합니다. citeturn3view3turn20view0 fileciteturn0file1

### License, dataset, and SDK caution notes

| Item | Safe use in this spike | Caution |
|---|---|---|
| Unity docs / samples | Yes, primary implementation guidance citeturn2view0turn2view3turn3view0 | Sample assets/code reuse still follows Unity package terms |
| MediaPipe docs | Yes, as reference or comparison citeturn8view0 | Runtime integration adds cost and model/runtime terms should be checked if bundled |
| CelebAMask-HQ | Yes, offline semantic reference | Non-commercial research/education only; no commercial exploitation or redistribution of dataset portions/derived data citeturn13view0 |
| LaPa | Yes, offline semantic reference | Non-commercial purposes under license terms; commercial review needed later citeturn14view3turn15academia0 |
| BiSeNet / SegFace code | Yes, offline experimentation; MIT code | Dataset/weights follow separate upstream terms citeturn14view4turn14view6 |
| Commercial beauty SDKs | Benchmarking reference at most | Not recommended as the primary solution in this validation, per your scope constraints fileciteturn0file0 |

### Concrete next-step plan for a one-to-two week validation spike

| Window | Goal | Concrete output |
|---|---|---|
| Early spike | Instrumentation hardening | Runtime log of `trackablesChanged`, `trackingState`, face ID, mesh/UV support, active region state; keep current privacy stance citeturn2view0turn2view1 fileciteturn0file1 |
| Early spike | UV basis confirmation | One captured canonical ARFace topology snapshot for your target device class; confirm region atlas can map consistently to observed mesh |
| Mid spike | Region atlas authoring | Replace broad debug masks with authored `lip`, `cheek`, `eye` UV masks rendered as hard debug colors |
| Mid spike | Stabilization pass | Add light EMA on face pose / blendshape coefficients and hysteresis on lost/recovered |
| Mid spike | Region validation | Record neutral, turn, mouth open/close, blink, out/in scenarios and score each region separately |
| Late spike | Texture carry-over | Reapply `matte_lip`, `soft_blush`, `shimmer_eye` on the UV-mask path to verify no regression from E4 fileciteturn0file1 |
| Late spike | Fallback decision | Only if lip or eye is still clearly unstable, run MediaPipe offline/reference comparison on the same device clips |
| Late spike | Final decision | Mark E7 axis Green only if regions remain attached and visually plausible under the agreed test matrix; otherwise keep Yellow with explicit blocker notes |

### Final recommendation

이번 질문에 대한 가장 실용적인 답은 명확합니다. **ARKit `ARFace` mesh/UV data는 lip·cheek·eye의 “정밀하고 안정적인 실시간 부위 추적”을 시작하기에 충분하다. 하지만 그것만으로 제품급 semantic boundary를 보장하지는 않는다.** 그래서 이번 E7에서는 **ARFace를 유지하되, authored UV region atlas + light temporal stabilization + lifecycle hysteresis + limited blendshape correction**으로 가는 것이 최적 경로입니다. **Cheek는 가장 빨리 Green을 받을 후보, lip은 충분히 현실적, eye는 가장 높은 리스크**입니다. MediaPipe Face Landmarker와 2D face parsing은 **즉시 교체 수단이 아니라 offline reference / authoring helper / fallback threshold test**로 두는 편이 가장 실용적입니다. citeturn2view1turn2view2turn19view1turn8view0turn15academia0turn25academia0turn25academia1 fileciteturn0file1