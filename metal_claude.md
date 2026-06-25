이건 제가 답을 다 알고 있다고 가정하기엔 한 가지 시간 민감한 변수가 있습니다 — SceneKit/RealityKit의 현재 Apple 권장 방향(특히 SceneKit deprecation 여부). 중간안 추천에 직접 영향을 주니 그것만 확인하고 답하겠습니다.SceneKit 상태에 중요한 변화가 있어서(WWDC25에서 soft-deprecated 됨) 그게 중간안 추천에 직접 영향을 줍니다. 그 부분을 반영해서 정리합니다.

---

## 결론 (5줄)

1. 지금 E7.3의 진짜 블로커(makeup이 subtle, eye boundary 약함, cosmetic 품질 미증명)는 **렌더러 문제가 아니라 mask/UV/landmark 데이터 + shader 저작 문제**입니다. Metal로 바꿔도 자동으로 안 좋아집니다. **[Confirmed]**
2. Metal/native의 확실한 이득은 **앱 용량(~100MB↓), 런타임 메모리, launch/re-entry lifecycle, RN 통합성**이고, 이건 "위생(hygiene)" 이득이지 "화장 품질" 이득이 아닙니다. **[Estimate]**
3. "피부색 sampling / feather / blend / finish"는 **Unity custom shader로도 전부 가능**합니다. Metal은 color space·camera texture 제어가 더 *직접적*일 뿐, Unity가 막고 있는 게 아닙니다. **[Confirmed]**
4. lip/eye boundary 정확도는 ARKit `ARFaceGeometry`의 고정 토폴로지(1220 vertices)에 묶여 있고, **Unity든 Metal이든 같은 mesh를 먹기 때문에 렌더러 교체로 해결되지 않습니다.** **[Confirmed]**
5. 따라서 합리적 결론은 **"바로 전환"도 "그냥 Unity 유지"도 아닌 병렬 스파이크** — 단, 스파이크 1차 타깃을 SceneKit으로 잡지 마세요(WWDC25 soft-deprecated). raw Metal 또는 RealityKit CustomMaterial로 가는 게 맞습니다. **[Confirmed/Risk]**

> 참고: 측정값 1220 vertices / 6912 indices / 1220 UVs는 ARKit `ARFaceGeometry`의 정확한 canonical 값입니다(1220 정점, 2304 삼각형 × 3 = 6912 인덱스, 1220 텍스처 좌표). 즉 현재 파이프라인은 AR Foundation을 통해 ARKit 표준 face mesh를 그대로 소비 중입니다. **[Confirmed]** 이게 6번 판단의 핵심 근거입니다.

---

## 1·4. Unity 유지 vs ARKit+Metal 전환 비교표

| 축 | Unity (현행) | ARKit + Metal (native) | 라벨 |
|---|---|---|---|
| 앱 용량 | UnityFramework ~105MB + Data ~9.2MB | renderer 코드+에셋 single-digit MB. **~100MB↓** | [Estimate] (Unity 측은 사내 측정 [Confirmed]) |
| 런타임 메모리 | Unity 런타임 heap/GC/subsystem 상주, 흔히 100–200MB+ | camera texture + face buffer + pipeline state만. 수십~100MB↓ 가능 | [Estimate] / 절대치 [Measure] |
| launch/re-entry/lifecycle | UaaL은 unload/재진입이 무겁고 fragile (Unity는 완전 release를 잘 안 함, 재초기화 비쌈) | 그냥 UIViewController push/pop + ARSession run/pause. 매우 가벼움 | [Confirmed] (Unity as a Library 공식 한계) |
| FPS / frame-time | 이미 52–60 (workload 작음) | 60 쉽게 도달, frame pacing 약간 안정적일 수 있음 | [Estimate] — **거의 parity, 전환 이유 아님** |
| recipe latency | ~36ms (RN→Unity bridge marshaling 포함) | RN→native bridge가 더 직접적 → 약간↓ 가능, but 36ms도 이미 OK | [Measure] — headline 아님 |
| 화장 표현력 | shader/material로 풀 가능, 현재는 미저작 | from-scratch라 풀 제어. but 천장은 동일 | [Risk] — 전환만으로 안 올라감 |
| 피부색 sampling/feather/blend/finish | 가능 (camera texture 접근이 약간 번거로움) | color space·YCbCr·blend state를 1급으로 직접 제어 → 더 *직접적* | [Confirmed] |
| 빌드/반복 속도 | Unity 수정→re-export→re-integrate 루프 느림 | Xcode 단일 루프, steady-state 빠름. but 초기 ramp 큼 | [Estimate] |
| RN 통합성 | UnityFramework embed + view 임베딩 + lifecycle glue, 무거움 | 표준 RN native view(Fabric/legacy). idiomatic | [Estimate]/일부 [Confirmed] |
| 유지보수성 | 엔진은 Unity가 관리, but UaaL fragility + 버전 업글 부담 | **렌더 코드 전부 우리가 소유** → Metal/ARKit 역량 필요, 소규모 학생팀엔 부담 | [Risk] |

**요약:** Metal이 이기는 칸은 용량·메모리·lifecycle·RN. 지는/비기는 칸은 FPS·표현력·유지보수. **표현력은 어느 쪽도 "공짜"가 아닙니다.**

---

## 2·3·5. Unity가 자동으로 해주던 것 vs Metal에서 직접 만들 것

ARKit은 **렌더링을 일절 제공하지 않습니다.** ARKit이 주는 건 face tracking, face anchor transform, `ARFaceGeometry`(vertex/index/uv/normal), blendshape 52개, camera `CVPixelBuffer` + intrinsics/projection·view matrix까지입니다. 그 위의 "그림"은 전부 개발자 몫이고, Unity는 그 "그림" 레이어를 통째로 대신 해주고 있었습니다. **[Confirmed]**

| Unity/AR Foundation이 자동으로 해주던 것 | Metal로 가면 직접 만들어야 하는 것 | 현실성 |
|---|---|---|
| Camera background 렌더 (ARCameraBackground) | YCbCr(420) 2-plane → RGB 변환 shader, full-screen quad, **orientation/displayTransform** | 가능하나 **gotcha 多** [Risk] |
| ARFace → mesh 객체화 (ARFace.vertices/indices/uvs) | `ARFaceGeometry` 버퍼를 MTLBuffer로 (stride/format/winding), **매 프레임 갱신** | 가능 [Estimate], 버그 잘 남 [Risk] |
| Material/Shader 시스템, render pipeline | MTLRenderPipelineState, blend state, depth, 색공간(sRGB/linear) 전부 직접 | 가능 [Estimate] |
| Scene graph / transform / projection 결합 | face transform × camera projection × view matrix 직접 결합 | 가능 [Estimate] |
| Player loop / 렌더 스케줄링 | CADisplayLink 혹은 ARSession delegate에 맞춘 draw loop | 가능 [Confirmed] |
| Asset/텍스처 import 파이프라인 | mask atlas 텍스처 로딩·바인딩 직접 | 쉬움 [Confirmed] |

**5번 분리 (피부색 sampling / feather / blend / finish):**

- **Unity도 충분히 가능한 것** — 네 가지 전부. skin sampling(camera texture를 fragment screen-UV로 샘플), feather(soft mask + smoothstep), pigment blend(multiply/overlay/soft-light, alpha-over), finish(specular/roughness/fresnel). 전부 fragment shader 연산이고 ShaderLab/Shader Graph로 표현됩니다. **즉 지금 화장이 subtle한 건 Unity 한계가 아니라 shader·mask 저작이 아직 안 된 것.** **[Confirmed]**
- **Metal이 더 직접적/유리한 것** — (a) **color space 정밀 제어**: 화장 blend 리얼리즘은 linear vs gamma에서 결과가 다른데 Metal은 명시적. Unity는 URP/Built-in color space 설정과 싸워야 함. (b) **live camera texture를 1급 객체로 이미 손에 쥠**(Unity는 ARCameraBackground 텍스처를 custom face material에 넘기는 게 번거로움). (c) blend state·MSAA·depth를 frame-tight하게 소유. **[Confirmed]**
- **Metal로도 자동 해결 안 되는 것** — mask/UV 품질, landmark/boundary 정밀도, 실제 artistic blend 수식 저작, finish look 튜닝. 전부 **데이터+저작 문제**라 렌더러가 안 풀어줌. **[Confirmed]**

---

## 6. Metal이 lip/eye boundary를 자동 해결하는가?

**아니요.** 경계 정확도는 (1) `ARFaceGeometry`의 고정 1220정점 토폴로지, (2) 그 위의 UV atlas 레이아웃, (3) mask edge가 UV 상에서 어디 떨어지는지, (4) blendshape 기반 deformation의 한계로 결정됩니다. ARKit face mesh의 UV는 eye/lip 윤곽 주변이 특별히 dense하지 않습니다. **Unity든 Metal이든 동일한 이 mesh를 먹기 때문에**, eye boundary가 약한 문제는 렌더러를 갈아도 그대로 남습니다. **[Confirmed]**

해결은 별개 트랙입니다: (a) mask atlas의 region edge를 더 정밀하게 저작, (b) UV 상 boundary feather/anti-alias 개선, (c) 필요하면 blendshape 보조 신호나 별도 landmark로 eye contour 보정, (d) eye는 작은 영역이라 sub-pixel 단위 sampling/AA가 체감 큼. — 이건 **Metal의 직접 제어가 "도움은 되지만"**, 자동 해결은 아니고 **데이터·저작 작업**입니다. **[Confirmed/Estimate]**

---

## 7. Codex 같은 coding agent가 막힐 지점

| 지점 | 위험도 | 이유 |
|---|---|---|
| RN native view bridge | **높음** [Risk] | Fabric(new arch) vs legacy ViewManager. agent가 RN 버전과 안 맞는 old-arch 코드를 짜기 쉬움. Metal-backed UIView를 Fabric component로 노출하는 게 fiddly |
| Swift/ObjC/ObjC++ 선택 | 중간 [Risk] | 권장: ARKit/Metal 로직은 **Swift**, RN bridge는 **thin ObjC++**. agent가 경계를 흩뜨리거나 bridging header를 빠뜨리기 쉬움 |
| ARKit face tracking | 낮음, but [Confirmed 제약] | `ARFaceTrackingConfiguration.isSupported`(TrueDepth 기기). **Simulator에서 face tracking 안 됨** → agent 자가검증 불가 |
| ARFaceGeometry vertex/UV/index 버퍼 | **높음** [Risk] | UInt16 index, stride/format, winding/culling, **매 프레임 갱신**을 미묘하게 틀리기 쉬움(flip/mis-index) |
| Metal pipeline/shader | 중~높음 [Risk] | color space(sRGB/linear), cosmetic용 blend state, depth, YCbCr 변환을 흔히 틀림 |
| camera texture orientation/coordinate | **가장 높음** [Risk] | ARKit image orientation × device orientation × Metal tex coord × displayTransform. **전면 카메라 mirror**까지 겹쳐 거의 모두가(에이전트 포함) 한 번은 뒤집힘. **[Measure] 필수** |
| 실기기 검증 루프 | 구조적 제약 [Confirmed] | face tracking은 물리 TrueDepth 기기 전용. agent가 못 돌려봄 → **매 iteration 사람이 실기기 확인** 필요, 속도 병목 |

**핵심:** agent가 scaffold는 잘 하지만, **orientation/mirror + face buffer 갱신 + RN Fabric bridge** 세 곳이 사람 개입이 반드시 필요한 구간입니다.

---

## 8. 권장 스파이크 범위 (전면 전환 ❌, 병렬 비교 스파이크)

**최소 구현 범위 (lips만, 가장 visible·가장 쉬움):**
- 실기기에서 ARKit face tracking → camera background → `ARFaceGeometry` 렌더
- **입술 1개 region**에 skin sampling + feather + 1개 blend mode + finish(matte/gloss 1축) 적용
- 현재 Unity가 쓰는 **동일 mask/recipe**를 그대로 재현 (apples-to-apples)
- RN native view로 wiring, RN HUD를 그 위에 overlay (현 구조 동일)

**성공/실패 기준 + evidence matrix:**

| 지표 | 측정법 | 성공 기준 | 라벨 |
|---|---|---|---|
| 앱 용량 | Unity 포함 vs 제외 archive 크기 | ~100MB↓ 확인 | [Estimate→Measure] |
| 메모리 | Instruments, 동일 씬 | 유의미 감소 | [Measure] |
| lifecycle | AR 화면 20회 enter/exit, 재진입 시간, leak | crash·leak 0, 재진입 빠름 | [Measure] |
| FPS/frame-time | 실기기 동일 조건 | Unity의 52–60 이상 | [Measure] |
| recipe latency | 동일 recipe 적용 | ≤ 36ms | [Measure] |
| **입술 품질 side-by-side** | Unity vs native 동시 비교 | native가 **최소 동등 + boundary 더 선명** | 정성 [Measure] |

**결정 규칙:** native가 용량+lifecycle+RN에서 결정적이면 전환 근거. 반대로 **품질이 진짜 블로커면, 스파이크가 "같은 mesh·같은 mask면 native도 boundary 한계가 동일함"을 드러내 줌** → 즉 스파이크는 "Metal이 화장 품질을 고쳐줄 것"이라는 암묵적 기대를 *반증*하는 역할도 합니다.

**세션 추정 (수요코딩회 단위 가정, 분산 큼):** **[Estimate]**
- 실기기 camera+face 렌더 baseline: 2–3
- ARFaceGeometry→Metal buffer + orientation 정합: 2 (gotcha 구간)
- 입술 1 region(sample/feather/blend/finish): 2
- RN native bridge + HUD overlay: 1–2
- side-by-side 측정 + matrix: 1
→ **합 ~8–10 세션, orientation/buffer/RN bridge 때문에 variance 높음.** **[Risk]**

> 동시에, **E7 품질 작업(mask/UV/feather/blend 저작)은 Unity에서 병행**하세요. 품질 블로커가 사는 곳이 거기고 Unity로 다 표현 가능하기 때문입니다.

---

## 9·10. SceneKit/RealityKit 중간안에 대한 중요한 단서

원래는 **ARSCNView + `ARSCNFaceGeometry` + SCNProgram/shader modifier**가 "얼굴 mesh에 텍스처·shader 입히기"에 가장 딱 맞는 sweet spot(Unity 무게 제거 + Apple 유지 + 목적특화 face mesh helper, custom Metal shader도 SCNProgram으로 가능)이었습니다. 그러나:

- WWDC25(iOS 26)에서 Apple은 SceneKit을 "critical-bug only" 유지보수 모드로 전환하고 공식 문서에 deprecated로 표시했으며 RealityKit으로의 이전을 권고했습니다. Apple 공식 SceneKit 문서도 SceneKit은 deprecated이며 대신 RealityKit을 쓰라고 명시합니다.
- 다만 현재로서는 SceneKit을 hard deprecate할 계획은 없고, 만약 그렇게 된다면 충분히 사전 고지하겠다고 했습니다. 즉 기존 앱은 당분간 동작하지만 **신규/중대한 작업을 SceneKit 위에 새로 쌓는 건 권장되지 않습니다.** 새 프로젝트나 큰 업데이트에는 SceneKit을 피하라는 게 Apple의 가이드입니다.

→ **결론적으로 SceneKit은 이 작업에 기술적으로 가장 이상적이지만, 지금 새 native 트랙을 거기 얹는 건 platform-direction risk** [Risk]입니다.

대안인 **RealityKit**은 권장 방향이고 ARView가 camera background를 자동 제공하지만, **live face mesh에 fine cosmetic shader를 입히는 경로가 `ARSCNFaceGeometry`만큼 깔끔하지 않습니다.** `ARFaceGeometry`로 `MeshResource`를 직접 만들어 매 프레임 갱신 + `CustomMaterial`(Metal surface shader)로 가야 하고, CustomMaterial의 표현 자유도는 SCNProgram보다 제약이 큽니다. **[Estimate/Risk]** 즉 RealityKit은 "SceneKit의 face-mesh 장점"을 깔끔히 상속하지 못합니다.

(공식 근거: Apple Developer — `ARFaceGeometry`, "Tracking and Visualizing Faces", "Displaying an AR Experience with Metal", SceneKit 문서의 deprecation 노트 및 WWDC25 session 288 "Bring your SceneKit projects to RealityKit"; Unity — "Unity as a Library", AR Foundation Face tracking 문서. URL을 확신하지 못하는 항목은 문서명으로만 표기했습니다.)

---

## 최종 추천

**→ 「Metal 병렬 스파이크」 (전면 전환·순수 Unity 유지 둘 다 ❌)**

근거:
- E7.3의 실제 블로커는 데이터·shader 저작 문제 → **Metal이 자동으로 못 고침**. 따라서 *지금* 전면 전환할 근거가 없음. **[Confirmed]**
- 그러나 용량(~100MB)·lifecycle·RN 통합은 **진짜 이득**이라 "그냥 Unity 유지"로 무시하면 안 됨. **[Estimate]**
- 스파이크 native 1차 타깃은 **raw Metal** (또는 엔진 도움을 원하고 제약을 감수하면 RealityKit CustomMaterial). **SceneKit은 기술적 적합성에도 불구하고 WWDC25 soft-deprecation 때문에 새 트랙으로는 비권장.** **[Confirmed/Risk]**
- 스파이크 진행과 **병행해서 E7 품질 작업은 Unity에서 계속** — 품질 블로커가 사는 곳이고 Unity로 전부 표현 가능하므로. **[Confirmed]**

판단 게이트: 스파이크가 (a) 용량·lifecycle·RN 이득을 정량 증명하고 **동시에** (b) 입술 품질이 native에서 최소 동등 이상이면 → 단계적 전환 검토. (b)가 동등에 그치고 boundary가 여전히 mesh/mask에 묶이면 → **전환은 품질 해결책이 아님이 증명된 것**이므로 Unity 유지 + 데이터/저작 트랙에 집중.