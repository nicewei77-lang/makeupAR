## 결론 5줄

1. **지금 바로 Unity를 버리는 건 비합리적**입니다. 현재 52–60 FPS가 이미 나오고 있고, iOS Unity도 내부적으로 Metal을 기본 그래픽스 API로 사용합니다. ([Unity Manual][1])
2. **Metal 전환의 확실한 이득은 렌더 품질보다 앱 용량, 메모리, launch/re-entry, RN 통합성** 쪽입니다.
3. **피부색 sampling, feather, pigment blend, finish 제어는 Unity custom shader로도 가능합니다.** Metal이 자동으로 화장을 예쁘게 만들어주지는 않습니다. ([Unity Manual][2])
4. **lip/eye boundary 정확도 문제도 Metal로 자동 해결되지 않습니다.** 같은 ARKit face mesh/UV를 쓰면 mask/UV/landmark 품질 문제는 그대로 남습니다. ([Apple Developer][3])
5. 최종 추천은 **Unity 유지 + Metal 병렬 스파이크**입니다. “전면 전환”은 스파이크가 용량·메모리·lifecycle·latency에서 명확히 이기고, visual quality가 Unity보다 나빠지지 않을 때만 결정해야 합니다.

---

## 1. Unity 유지 vs ARKit + Metal 전환 비교표

| 항목                                    | Unity 유지                                                                                                                                                                                        | ARKit + Metal native 전환                                                                                                                                                                                        | 판단 라벨                                                                    |
| ------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 현재 검증 상태                              | 이미 RN 안에 UnityView embed, AR Foundation + ARKit face tracking, region mask 렌더링까지 검증됨. FPS 52.2–60.2, recipe latency 약 36ms는 좋은 validation baseline.                                             | 아직 미구현. 같은 수준까지 가려면 ARSession, camera background, face mesh buffer, Metal shader, RN bridge를 새로 구현해야 함.                                                                                                        | **Confirmed from known platform behavior** + **Needs local measurement** |
| 앱 용량                                  | 현재 기록상 `UnityFramework.framework ~105MB + Unity Data ~9.2MB`. Release build/stripping으로 줄일 여지는 있음. Unity는 iOS Player size 최적화로 Release Archive, stripping 등을 권장함. ([Unity Manual][4])           | Unity runtime/framework/data를 제거할 수 있으므로 가장 큰 개선 후보. ARKit/Metal은 OS framework라 앱에 Unity 같은 엔진 런타임을 싣지 않음. 단, 최종 IPA/App Store install size는 반드시 로컬 측정 필요.                                                     | **Reasonable engineering estimate** + **Needs local measurement**        |
| 런타임 메모리                               | Unity runtime, IL2CPP/engine code, AR Foundation objects, renderer, textures가 상주. Unity as a Library의 `unloadApplication`은 “most memory”를 release하지만 전부는 아니라고 문서에 명시됨. ([Unity Manual][5])      | 필요한 ARSession, MTKView, Metal buffers/textures만 유지 가능. 수십 MB 단위 개선 가능성이 큼. 다만 ARKit camera/face tracking 자체 메모리는 공통.                                                                                           | **Reasonable engineering estimate** + **Needs local measurement**        |
| launch / re-entry / lifecycle         | Unity runtime 부팅, pause/unload/showUnityWindow 관리가 필요. Unity as a Library는 runtime load/activate/unload control을 제공하지만, 하나의 Unity runtime만 가능하고 unload 후에도 일부 메모리는 남을 수 있음. ([Unity Manual][5]) | RN native view lifecycle에 맞춰 `ARSession.run/pause`, `MTKView` attach/detach를 직접 제어 가능. 화면 전환, 재진입, 메모리 회수 측면에서 유리할 가능성이 큼.                                                                                     | **Confirmed from known platform behavior** + **Needs local measurement** |
| FPS / frame-time                      | 현재 이미 60 FPS 근처. Unity도 iOS에서 Metal을 기본 사용하므로 “Metal이라서 FPS가 확 오른다”는 기대는 낮음. ([Unity Manual][1])                                                                                                | 1220 vertices 수준 face mesh는 매우 작음. Unity overhead를 줄여 frame-time tail이 좋아질 수는 있지만, ARKit tracking/camera가 병목이면 개선폭은 작음.                                                                                        | **Reasonable engineering estimate**                                      |
| recipe latency                        | RN → Unity 메시지, JSON parse, Unity main thread 반영, material update frame boundary가 들어갈 수 있음. 현재 약 36ms면 대략 2프레임권.                                                                                | RN prop/native module → native struct/uniform buffer update로 단순화 가능. 목표는 16–25ms 이하 또는 최소 1프레임 단축. 단, 현재 latency 정의가 무엇인지에 따라 다름.                                                                              | **Needs local measurement**                                              |
| 화장 표현력                                | 충분히 가능. Unity custom shader, material property, texture, HLSL/ShaderLab로 pigment, opacity, roughness/gloss, feather, blend 구현 가능. ([Unity Manual][2])                                           | 더 직접적인 GPU 제어 가능. camera YCbCr sampling, color conversion, mask blend equation, uniform layout을 직접 통제 가능. 하지만 화장 모델은 직접 설계해야 함.                                                                                | **Confirmed from known platform behavior**                               |
| 피부색 sampling                          | Unity에서도 가능하나, CPU camera image acquisition은 비용이 큼. Unity AR Foundation 문서는 `TryAcquireLatestCpuImage`가 GPU→CPU transfer라 performance impact가 있다고 설명함. ([Unity Manual][6])                      | Metal은 `ARFrame.capturedImage`의 Y/CbCr plane을 `CVMetalTextureCache`로 texture화해 shader에서 직접 sampling하는 경로가 자연스럽다. Apple의 Metal AR sample도 camera image를 GPU texture로 만들어 렌더링하는 방식을 설명한다. ([Apple Developer][7]) | **Confirmed from known platform behavior**                               |
| mask feather / pigment blend / finish | Unity shader로 가능. 현재 subtle/hard to see 문제는 Unity의 본질적 한계라기보다 shader/material/mask tuning 미완성일 가능성이 큼.                                                                                          | Metal도 가능. 더 낮은 레벨에서 blend, color space, alpha, sampling을 통제할 수 있음. 하지만 “더 예쁜 화장”은 자동이 아님.                                                                                                                     | **Confirmed from known platform behavior**                               |
| 빌드 / 반복 속도                            | Unity export → Xcode build → RN integration 흐름이 무겁다. Shader/asset iteration도 Unity build 파이프라인을 탐.                                                                                              | 순수 iOS native module이면 Xcode/RN build loop로 단순화 가능. 다만 Metal shader/debug는 난이도가 높고 실기기 반복이 필수.                                                                                                                 | **Reasonable engineering estimate**                                      |
| RN 통합성                                | UnityView 위에 RN HUD overlay는 현재 구조상 가능. 하지만 Unity as a Library는 full-screen rendering만 공식 지원하고, Unity runtime instance도 하나만 가능하다는 제한이 있음. ([Unity Manual][5])                                   | RN native view component로 `UIView/MTKView`를 직접 노출 가능. RN iOS native component는 `RCTViewManager`, `RCT_EXPORT_MODULE`, `view` 구현 방식이 공식 문서에 있음. ([React Native][8])                                             | **Confirmed from known platform behavior**                               |
| 유지보수성                                 | 팀에 Unity/Shader 숙련자가 있으면 빠름. AR Foundation이 ARSession, camera background, face trackable lifecycle을 많이 대신 해줌. ([Unity Manual][9])                                                               | iOS graphics ownership이 생김. 장기적으로 앱은 가벼워지지만, ARKit/Metal/RN bridge를 이해하는 사람이 반드시 필요.                                                                                                                           | **Risk / unknown**                                                       |
| 제품 방향 적합성                             | iOS 외 Android ARCore까지 염두에 두면 Unity/AR Foundation 유지 가치가 큼. Unity AR Foundation은 native AR SDK 위에서 멀티플랫폼 AR을 구성하는 추상화임. ([Unity Manual][9])                                                     | iPhone-only, face makeup-only, 앱 경량화가 핵심이면 native Metal 방향이 더 적합할 수 있음.                                                                                                                                        | **Reasonable engineering estimate**                                      |

---

## 2. Unity가 해주던 것 vs Metal에서 직접 만들 것

| Unity / AR Foundation이 해주던 것                                                         | Metal native에서 직접 만들어야 하는 것                                                                                                                                                                 | 난이도 |
| ------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --- |
| Unity runtime view lifecycle, render loop, frame scheduling                          | `MTKView` 생성, `CADisplayLink`/draw loop, render pass 구성, lifecycle pause/resume                                                                                                             | 중   |
| AR Foundation `AR Session`, `XR Origin`, `AR Camera Manager`, `AR Camera Background` | `ARSession` 직접 생성, `ARFaceTrackingConfiguration` 실행, session interruption/error 처리                                                                                                          | 중   |
| camera background 렌더링                                                                | `ARFrame.capturedImage`의 Y/CbCr plane을 Metal texture로 만들고 RGB 변환 shader 작성. captured image는 orientation/aspect가 view에 맞춰진 상태가 아니므로 transform 처리 필요. ([Apple Developer][7])                  | 상   |
| `ARFaceManager`가 face GameObject 생성/업데이트/제거                                          | `ARSessionDelegate`에서 `ARFaceAnchor` 수신, tracking state 관리, face lost/reacquired 처리                                                                                                         | 중   |
| `ARFaceMeshVisualizer`, `MeshFilter`, `MeshRenderer`                                 | `ARFaceGeometry.vertices`, `textureCoordinates`, `triangleIndices`를 `MTLBuffer`로 업로드하고 indexed draw 호출. Apple 문서는 triangle indices가 GPU index buffer로 쓰기 적합하다고 설명함. ([Apple Developer][10]) | 상   |
| Unity material / shader property / texture binding                                   | `MTLRenderPipelineState`, `MTLSamplerState`, uniform buffer, texture binding 직접 관리. Metal pipeline state는 매 frame 만들지 말고 한 번 만들고 재사용해야 함. ([Apple Developer][11])                           | 상   |
| ShaderLab/HLSL, material inspector, texture import                                   | `.metal` shader, color space, alpha premultiplication, blend state, texture format, asset loading 직접 관리                                                                                     | 상   |
| Unity coordinate conversion / camera projection                                      | ARKit camera projection, viewport, front-camera mirroring, face anchor transform, clip-space 변환 직접 관리                                                                                       | 상   |
| RN → Unity message bridge                                                            | RN → native view props / events / native module 설계. RN 공식 문서는 native와 RN 사이 통신에 props, events, native modules를 설명함. ([React Native][12])                                                    | 중   |
| Unity profiler / frame debugger 일부                                                   | Xcode Instruments, Metal frame capture, os_signpost, custom metrics 직접 구성                                                                                                                   | 중   |
| Asset import/compression pipeline                                                    | mask texture, LUT, recipe JSON, shader constants를 iOS asset bundle 또는 app bundle로 직접 관리                                                                                                     | 중   |
| Cross-platform abstraction                                                           | iOS 전용 구현. Android를 하려면 별도 ARCore/OpenGL/Vulkan/Filament/Unity 대안 필요                                                                                                                        | 상   |

핵심은 이겁니다. **Metal로 가면 “렌더러를 직접 소유”하게 됩니다.** 그 대신 Unity가 자동으로 해주던 카메라 배경, face mesh 업데이트, shader/material binding, lifecycle, profiler, asset pipeline을 전부 직접 책임져야 합니다.

---

## 3. 직접 만드는 것이 현실적인가?

**최소 비교 스파이크 수준은 현실적입니다.**
`ARFaceGeometry`는 이미 vertices, texture coordinates, triangle indices를 제공하고, Apple 문서도 이 mesh가 여러 렌더링 기술에 쓸 수 있는 3D face topology라고 설명합니다. ([Apple Developer][13])

하지만 **제품급 cosmetic renderer 전체를 Metal로 새로 만드는 것은 별도 프로젝트급**입니다. 특히 어려운 건 Metal draw call 자체보다 아래입니다.

| 영역                              | 현실성 판단                                                                                                               |
| ------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| RN native view bridge           | 현실적. 기존 RN 앱에 native `UIView/MTKView` 붙이는 패턴은 공식적으로 가능.                                                              |
| ARKit face tracking             | 현실적. ARKit이 face tracking 시 `ARFaceAnchor`와 geometry를 제공. ([Apple Developer][14])                                    |
| face mesh 렌더링                   | 현실적이지만 실수 많음. buffer stride, index type, UV, transform, front-camera mirroring 주의.                                   |
| camera background + orientation | 가장 잘 막히는 지점. captured image는 view orientation/aspect에 맞춰져 있지 않아서 `displayTransform`류 처리가 필요. ([Apple Developer][15]) |
| cosmetic shader                 | 가능하지만 제품 품질은 별도. pigment model, skin tone normalization, finish response, feather tuning이 필요.                        |
| eye/lip boundary 개선             | Metal만으로 자동 해결 안 됨. mask authoring, UV atlas, landmark/region definition 품질 문제.                                      |
| 팀 유지보수                          | iOS graphics 담당자가 없으면 위험. Codex가 scaffold는 해도 실기기 디버깅과 시각 QA는 사람이 해야 함.                                              |

---

## 4. “피부색 sampling, feather, blend, finish” 검증

### Unity도 가능한 것

| 기능               | Unity 가능 여부 | 설명                                                                                                                                                                                                            |
| ---------------- | ----------: | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 피부색 sampling     |          가능 | `ARCameraManager.TryAcquireLatestCpuImage`로 CPU sampling 가능하지만 성능 비용이 큼. GPU 경로로 camera texture/render texture를 활용하는 설계가 더 적합. Unity 문서는 CPU image acquisition이 resource-intensive라고 명시함. ([Unity Manual][6]) |
| mask feather     |          가능 | UV mask texture + distance/blur/gradient feather를 fragment shader에서 처리 가능.                                                                                                                                    |
| pigment blend    |          가능 | base skin color와 product color를 multiply/screen/overlay/custom blend로 섞는 shader 작성 가능.                                                                                                                        |
| finish 제어        |          가능 | matte, gloss, shimmer, pearl, roughness/specular response를 shader property와 texture로 제어 가능. Unity는 HLSL/ShaderLab custom shader와 material property를 지원함. ([Unity Manual][2])                                  |
| region별 material |          가능 | lip/cheek/eye mesh pass 또는 mask channel별 shader branch/uniform으로 가능.                                                                                                                                          |

### Metal이 더 직접적/유리한 것

| 기능                               | Metal 이점                                                                                                                         |
| -------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| camera texture sampling          | `ARFrame.capturedImage`를 Y/CbCr Metal texture로 직접 만들고 shader에서 sampling 가능. Unity/AR Foundation 추상화를 덜 탐. ([Apple Developer][7]) |
| color space / exposure / YUV→RGB | 변환 행렬, gamma/linear, alpha premultiply, blend equation을 직접 통제 가능.                                                                |
| recipe latency                   | RN native payload를 바로 uniform buffer에 반영 가능. UnitySendMessage/string/Unity main-thread 반영보다 단순화 가능.                              |
| lifecycle                        | RN 화면 생명주기와 ARSession/MTKView 생명주기를 1:1로 맞추기 쉬움.                                                                                 |
| profiling                        | Xcode Metal frame capture/Instruments 기준으로 iOS-native 병목을 직접 추적 가능.                                                              |

### Metal로도 자동 해결되지 않는 것

| 문제                        | 이유                                                                                                 |
| ------------------------- | -------------------------------------------------------------------------------------------------- |
| lip/eye boundary 정확도      | 같은 ARKit face mesh/UV를 쓰면 source geometry는 같음. mask/UV/region definition이 약하면 Metal에서도 약함.         |
| subtle/hard-to-see makeup | shader opacity, color response, finish model, lighting adaptation 문제. Metal 전환 자체가 색을 예쁘게 만들지는 않음. |
| product-quality cosmetics | 실제 화장품 질감 모델, skin-tone-aware color response, edge behavior, shimmer/gloss 모델링이 필요.                |
| 피부색 안정화                   | camera exposure/white balance/lighting 변화에 대한 normalization 로직이 필요.                                |
| QA / visual acceptance    | 기기별, 조명별, 피부톤별 캡처 비교가 필요. 렌더 API 선택으로 대체 불가.                                                       |

---

## 5. Metal이 boundary 문제를 자동 해결하는가?

아니요. **자동 해결하지 않습니다.**

현재 Unity가 AR Foundation + ARKit을 쓰고 있다면, face mesh의 근본 source는 ARKit입니다. Apple 문서 기준 `ARFaceAnchor.geometry`는 detected face에 맞춘 `ARFaceGeometry`를 제공하고, 이 geometry는 vertices, texture coordinates, triangle indices로 구성됩니다. ([Apple Developer][16])
또한 Apple 문서는 face mesh topology가 ARFaceGeometry 인스턴스 간 일정하고, texture coordinates가 같은 vertex index에 매핑된다고 설명합니다. ([Apple Developer][3])

따라서 eye boundary가 약한 원인은 보통 아래 중 하나입니다.

| 가능 원인                                                    | Metal 전환 효과                                               |
| -------------------------------------------------------- | --------------------------------------------------------- |
| UV atlas / mask 자체가 eye 영역을 부정확하게 덮음                     | 해결 안 됨. mask 재작성 필요.                                      |
| eye 주변 ARKit mesh topology가 makeup boundary에 충분히 촘촘하지 않음 | 해결 안 됨. 추가 landmark/segmentation/보정 필요.                   |
| shader feather가 너무 넓거나 opacity가 낮음                       | Unity에서도 수정 가능.                                           |
| front camera coordinate/mirroring/UV transform 오류        | Metal에서 더 명확히 잡을 수는 있음. 하지만 직접 구현해야 함.                    |
| material이 너무 subtle해서 boundary가 안 보임                     | Unity shader tuning으로도 해결 가능.                             |
| Unity layer/render order/blend state 문제                  | Metal에서 개선 가능성 있음. 하지만 Unity에서도 blend/render queue 수정 가능. |

즉, **Metal은 boundary를 “더 정확히 디버깅하고 통제할 수 있는 환경”은 주지만, 더 좋은 boundary data를 만들어주지는 않습니다.**

---

## 6. Codex 같은 coding agent가 막힐 가능성이 큰 지점

| 지점                                                | 난이도 | 막힐 가능성 | 평가                                                                                                                                                                                     |
| ------------------------------------------------- | --: | -----: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| RN native view bridge                             |   중 |      중 | Legacy RN이면 `RCTViewManager`로 비교적 가능. New Architecture/Fabric이면 codegen, view manager 구조 때문에 난이도 상승.                                                                                   |
| Swift / ObjC / ObjC++ 선택                          |   중 |     중상 | RN iOS bridge는 ObjC 패턴이 많고, Swift만으로 가면 bridging header/export 이슈가 생김. Metal/ARKit은 Swift가 편하지만 RN export는 ObjC/ObjC++가 편할 수 있음.                                                       |
| ARKit face tracking                               |   중 |      중 | `ARFaceTrackingConfiguration`, camera permission, unsupported device, session interruption 처리 필요.                                                                                      |
| ARFaceGeometry buffer 처리                          |   상 |      상 | `vector_float3`, `vector_float2`, `Int16` index, stride, buffer lifetime, per-frame update, triple buffering에서 실수 가능.                                                                  |
| Metal pipeline/shader                             |   상 |      상 | pipeline state, vertex descriptor, blend state, depth state, texture/sampler binding, shader compile 에러가 agent에게 어렵게 느껴질 수 있음.                                                         |
| camera texture orientation / coordinate transform |   상 |  매우 높음 | front camera, aspect fill, mirroring, `capturedImage` orientation, display transform이 가장 흔한 함정. Apple 문서도 captured image가 orientation/aspect 조정된 상태가 아니라고 설명함. ([Apple Developer][15]) |
| 실기기 검증 루프                                         |   상 |  매우 높음 | Face tracking은 실기기 검증이 핵심. agent는 실제 화면/미세한 시각 artifact를 판단하지 못하므로 로그, screenshot, screen recording, Xcode capture가 필요.                                                                |
| product-quality cosmetic tuning                   |   상 |  매우 높음 | 코드는 만들 수 있어도 “예쁜 화장”은 색/질감/피부톤 QA가 필요.                                                                                                                                                 |

Codex에게 맡길 때는 “전체 전환”을 한 번에 주면 실패 확률이 높습니다. **1세션 1증거** 방식으로 쪼개야 합니다.

---

## 7. 현실적인 Metal 비교 스파이크 범위

### 최소 구현 범위

| 범위                      | 포함                                                                            | 제외                                           |
| ----------------------- | ----------------------------------------------------------------------------- | -------------------------------------------- |
| RN native view          | `NativeMetalARView`를 RN 화면에 추가. 기존 UnityView와 동일 위치/동일 HUD overlay로 비교.       | 전체 앱 구조 개편                                   |
| ARKit                   | `ARFaceTrackingConfiguration` 실행, 1개 face anchor 수신, tracking state 표시        | world tracking, multi-face, recording/replay |
| Metal camera background | `ARFrame.capturedImage`를 배경으로 렌더링                                             | 고급 tone mapping                              |
| Face mesh overlay       | ARFaceGeometry vertices/UV/indices를 indexed draw                              | mesh smoothing 고급화                           |
| Region mask             | 현재 Unity validation에서 쓰는 lip/cheek/eye UV mask 또는 동등 asset 사용                 | 새 atlas authoring                            |
| Shader                  | 단순 cosmetic shader: region mask, opacity, color, feather 1차 구현                | 제품급 finish 전체                                |
| Recipe bridge           | RN에서 lip/cheek/eye recipe를 native로 전달하고 다음 frame uniform에 반영                  | AI 추천/분석 pipeline                            |
| Metrics                 | size, memory, launch/re-entry, FPS/frame-time, recipe latency, screenshot A/B | 장기 battery/thermal 정밀 분석                     |

### 성공 기준

| 기준                | 성공선                                                                                                                               |
| ----------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 앱 용량              | Unity 제거 시 raw app bundle 또는 archive 기준 명확한 감소. 현재 local raw 기준으로는 UnityFramework/Data 약 114MB가 비교 기준. 최종 IPA/install size 별도 측정. |
| 런타임 메모리           | AR 화면 진입 후 resident memory가 Unity 대비 **최소 50MB 이상** 또는 **30% 이상** 감소하면 의미 있음.                                                     |
| launch / re-entry | AR view open → first tracked face/rendered frame 시간이 Unity 대비 **30% 이상 개선**되면 의미 있음.                                              |
| FPS / frame-time  | median 60 FPS 유지, p95 frame-time이 Unity보다 나빠지지 않을 것.                                                                              |
| recipe latency    | RN recipe 변경 → 첫 visible frame 반영이 **25ms 이하** 또는 Unity 36ms 대비 **30% 이상 개선**.                                                    |
| visual quality    | lip/cheek/eye가 Unity validation과 같거나 더 잘 보여야 함. eye boundary regression 있으면 실패.                                                   |
| 구현 비용             | 6–8 focused sessions 안에 최소 A/B 데모가 안 나오면 전면 전환 보류.                                                                                |

### 실패 기준

| 실패 유형                                        | 판단                                     |
| -------------------------------------------- | -------------------------------------- |
| Metal이 FPS만 비슷하고 용량/메모리/lifecycle 이득이 작음     | Unity 유지                               |
| Metal visual이 Unity보다 나쁨                     | Unity 유지 + Unity shader 개선             |
| eye boundary가 그대로 약함                         | 렌더러 문제가 아니라 mask/UV/landmark 문제로 분류    |
| camera orientation/mirroring artifact가 계속 남음 | Metal 전환 리스크 높음                        |
| 팀원이 유지보수 불가능                                 | Unity 유지 또는 SceneKit/RealityKit 중간안 검토 |

---

## 8. Evidence matrix

| Hypothesis                          | 측정 방법                                                                           | 성공 기준                                              | 라벨                                         |
| ----------------------------------- | ------------------------------------------------------------------------------- | -------------------------------------------------- | ------------------------------------------ |
| Unity가 앱 용량의 주범이다                   | Unity 포함 build vs Metal-only build의 `.app`, `.ipa`, App Store estimated size 비교 | Metal build가 유의미하게 작음                              | **Needs local measurement**                |
| Unity가 AR 화면 메모리의 주범이다              | Xcode Memory Graph / Instruments Allocations로 enter/exit 5회 측정                  | Metal이 50MB+ 또는 30%+ 낮음                            | **Needs local measurement**                |
| Metal이 re-entry를 개선한다               | cold open, warm re-entry, first face rendered timestamp                         | 30%+ 개선                                            | **Needs local measurement**                |
| Metal이 FPS를 개선한다                    | 3분 실기기 run, median/p95 frame-time                                               | Unity보다 p95 frame-time 개선 또는 동일                    | **Needs local measurement**                |
| Metal이 recipe latency를 줄인다          | RN send timestamp → shader uniform applied → first frame visible timestamp      | ≤25ms 또는 30%+ 개선                                   | **Needs local measurement**                |
| Metal이 eye boundary를 개선한다           | 동일 UV mask/recipe로 Unity vs Metal screenshot overlay 비교                         | 동일 mask에서 boundary 개선이 있으면 Unity render/blend 문제였음 | **Risk / unknown**                         |
| Unity shader로도 product-quality 가능하다 | Unity custom shader에 skin sample/feather/blend/finish 1차 구현                     | visual acceptance 개선                               | **Confirmed from known platform behavior** |
| Metal 구현을 Codex가 감당 가능하다            | session별 buildable checkpoint                                                   | 6–8 sessions 내 A/B demo                            | **Risk / unknown**                         |

---

## 9. 구현 마일스톤

| 세션        | 목표                      | 산출물                                                                                          |
| --------- | ----------------------- | -------------------------------------------------------------------------------------------- |
| Session 1 | RN native view skeleton | RN 화면에 `NativeMetalARView` 표시. lifecycle log. UnityView와 feature flag 전환.                    |
| Session 2 | ARKit face tracking     | `ARFaceTrackingConfiguration` 실행, face anchor detected/updated/lost log, tracking state HUD. |
| Session 3 | Metal camera background | `ARFrame.capturedImage`를 MTKView 배경으로 렌더. orientation/aspect/mirroring 검증.                   |
| Session 4 | Face mesh draw          | ARFaceGeometry vertices/UV/indices를 Metal buffer로 올려 wireframe/solid face mesh 렌더.           |
| Session 5 | Region mask shader      | lip/cheek/eye UV mask texture 적용, opacity/color/feather uniform 반영.                          |
| Session 6 | RN recipe bridge        | 기존 Unity recipe payload와 같은 구조로 native uniform update. latency 측정.                           |
| Session 7 | A/B evidence capture    | Unity vs Metal 동일 recipe screenshot, FPS, memory, launch, re-entry, size 표 작성.               |
| Session 8 | go/no-go                | 유지/전환/중간안 판단. Metal 계속할지 Unity shader 개선으로 돌아갈지 결정.                                          |

---

## 10. 최종 추천

### 선택지별 판단

| 선택지                         |        추천도 | 이유                                                                                                                                                                                                                                                                                                                           |
| --------------------------- | ---------: | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Unity 유지**                |         높음 | 이미 feasibility accepted, FPS도 충분함. product-quality cosmetic rendering은 Unity custom shader로도 검증 가능. 지금 버리면 검증된 baseline을 잃음.                                                                                                                                                                                                 |
| **Metal 병렬 스파이크**           | **가장 합리적** | 앱 용량, memory, lifecycle, RN 통합성에 대한 의심을 증거로 해결할 수 있음. 실패해도 Unity baseline이 남음.                                                                                                                                                                                                                                               |
| **Metal 전면 전환**             |      아직 낮음 | boundary/화장 품질 문제가 렌더 API 문제인지 아직 증명되지 않음. 직접 구현할 범위가 큼.                                                                                                                                                                                                                                                                     |
| **SceneKit/RealityKit 중간안** |     제한적 추천 | SceneKit `ARSCNFaceGeometry`는 face topology를 빠르게 시각화하는 데 좋고, Apple도 quick visualization 경로로 제시함. ([Apple Developer][17]) RealityKit `CustomMaterial`은 Metal shader를 쓰면서 RealityKit pipeline을 활용할 수 있음. ([Apple Developer][18]) 다만 product-grade makeup shader와 camera texture sampling을 정밀하게 통제하려면 결국 direct Metal 쪽이 더 명확함. |

### 내가 테크 리드라면 이렇게 결정합니다

**지금은 “Unity 유지 + Metal 병렬 스파이크”가 정답에 가깝습니다.**

Unity 쪽에서는 먼저 **custom shader 개선**으로 subtle makeup, eye boundary, feather, pigment blend, finish를 끌어올립니다. 동시에 Metal 쪽은 “대체 가능성”을 증명하는 최소 스파이크만 합니다. Metal이 **용량/메모리/lifecycle/recipe latency에서 확실히 이기고**, visual quality가 Unity와 같거나 더 좋다는 evidence가 나오면 그때 전환을 논의합니다.

반대로 Metal 스파이크에서 eye boundary가 그대로라면, 그건 렌더러 문제가 아니라 **UV mask / region definition / ARKit face topology / landmark 보정 문제**입니다. 그 경우 Unity를 버리는 대신 E7.3의 Yellow 원인을 mask authoring과 cosmetic shader 품질 쪽으로 좁혀야 합니다.

[1]: https://docs.unity3d.com/6000.0/Documentation/Manual/Metal.html?utm_source=chatgpt.com "Metal"
[2]: https://docs.unity3d.com/6000.5/Documentation/Manual/Shaders.html "Unity - Manual: Custom shaders"
[3]: https://developer.apple.com/documentation/arkit/arfacegeometry/texturecoordinates-u42d?changes=_2%2C_2&language=objc%2Cobjc&utm_source=chatgpt.com "textureCoordinates | Apple Developer Documentation"
[4]: https://docs.unity3d.com/6000.0/Documentation/Manual/iphone-playerSizeOptimization.html?utm_source=chatgpt.com "Optimize the size of the iOS Player"
[5]: https://docs.unity3d.com/6000.4/Documentation/Manual/UnityasaLibrary-iOS.html "Unity - Manual: Integrating Unity into native iOS applications"
[6]: https://docs.unity3d.com/Packages/com.unity.xr.arfoundation%404.2/manual/cpu-camera-image.html?utm_source=chatgpt.com "Accessing the device camera image on the CPU"
[7]: https://developer.apple.com/documentation/arkit/arkit_in_ios/displaying_an_ar_experience_with_metal?changes=_1_1&utm_source=chatgpt.com "Displaying an AR Experience with Metal"
[8]: https://reactnative.dev/docs/0.83/legacy/native-components-ios "iOS Native UI Components · React Native"
[9]: https://docs.unity3d.com/6000.5/Documentation/Manual/AROverview.html "Unity - Manual: AR development in Unity"
[10]: https://developer.apple.com/documentation/arkit/arfacegeometry/triangleindices-8isy8?utm_source=chatgpt.com "triangleIndices | Apple Developer Documentation"
[11]: https://developer.apple.com/library/archive/documentation/3DDrawing/Conceptual/MTLBestPracticesGuide/PersistentObjects.html "Metal Best Practices Guide: Persistent Objects"
[12]: https://reactnative.dev/docs/communication-ios "Communication between native and React Native · React Native"
[13]: https://developer.apple.com/documentation/arkit/arfacegeometry?utm_source=chatgpt.com "ARFaceGeometry | Apple Developer Documentation"
[14]: https://developer.apple.com/documentation/ARKit/tracking-and-visualizing-faces?utm_source=chatgpt.com "Tracking and visualizing faces"
[15]: https://developer.apple.com/documentation/arkit/arframe/displaytransform%28for%3Aviewportsize%3A%29?utm_source=chatgpt.com "displayTransform(for:viewportSize:)"
[16]: https://developer.apple.com/documentation/arkit/arfaceanchor?utm_source=chatgpt.com "ARFaceAnchor | Apple Developer Documentation"
[17]: https://developer.apple.com/documentation/arkit/arscnfacegeometry?utm_source=chatgpt.com "ARSCNFaceGeometry | Apple Developer Documentation"
[18]: https://developer.apple.com/documentation/realitykit/custommaterial?utm_source=chatgpt.com "CustomMaterial | Apple Developer Documentation"
