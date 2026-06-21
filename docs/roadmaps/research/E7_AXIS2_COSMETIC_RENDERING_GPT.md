# 실시간 AR 메이크업을 위한 코스메틱 렌더링 모델 연구 보고서

## 연구 배경과 직접 결론

현재 프로젝트는 React Native 호스트 앱 안에서 Unity 화면을 열고, 실제 iPhone에서 Unity ARKit face tracking을 구동하며, RN↔Unity JSON 이벤트와 `lip`·`cheek`·`eye`의 독립 제어, 그리고 `matte_lip`·`soft_blush`·`shimmer_eye` 샘플 디스패치를 검증한 상태입니다. 다만 현재 결과는 팀이 이미 정리한 것처럼 “validation/debug quality”이며, E6 단계 판단도 기술 경로는 유효하지만 렌더러 품질 hardening과 성능 계측이 남아 있는 Yellow입니다. 즉, 지금 필요한 것은 “더 많은 기능”이 아니라 “적은 수의 룩을 설득력 있게 보이게 하는 최소 렌더링 모델”입니다. fileciteturn0file0

이 전제에서 가장 작은 기술적으로 신뢰할 수 있는 경로는 **ARKit의 face mesh/UV를 그대로 유지하고**, **AR camera background를 GPU 경로로 RenderTexture에 복사한 뒤**, **UV-space region mask를 쓰는 단일 마스터 셰이더**로 `lip`·`cheek`·`eye`를 각각 렌더링하는 방식입니다. 이 셰이더는 적어도 두 가지 시각 성분을 분리해야 합니다. 하나는 **pigment layer**이고, 다른 하나는 **finish layer**입니다. pigment layer는 색, coverage, feather, opacity, blend mode, texture를 다루고, finish layer는 roughness/specular/gloss/shimmer를 다룹니다. 이 둘을 분리하지 않으면 “색칠한 오버레이”를 벗어나기 어렵습니다. 반대로 이 둘만 분리해도 2–3개의 enterprise-demo-grade 샘플은 충분히 현실적으로 보일 수 있습니다. citeturn43view0turn30view0turn23view0turn23view1turn22view3turn26academia1turn38academia4

실무적으로는 **완전한 물리 기반 피부 렌더러**가 필요하지 않습니다. 대신 다음 네 가지만 확보하면 됩니다. 첫째, **실제 피부색과 상호작용하는 블렌딩**. 둘째, **경계 feather와 coverage 제어**. 셋째, **finish를 별도 파라미터로 제어하는 view-dependent highlight**. 넷째, **지역별 texture와 local detail preservation**입니다. 업로드된 검증 계획서가 처음부터 color, range, texture, intensity, opacity, feather, blend mode, position, size 같은 제어 항목을 엔진 요구로 잡았다는 점을 보면, 지금 필요한 스키마 확장은 이미 프로젝트 방향과도 일치합니다. fileciteturn0file1

핵심 권고를 한 줄로 요약하면 이렇습니다. **“디버그 broad mask 위에 색을 얹는 방식”에서 멈추지 말고, “camera-backed skin sampling + UV region mask + pigment/finish 분리 셰이더”로 한 단계만 올라가라.** 이 한 단계가 바로 `natural_daily`, `gloss_lip_focus`, `soft_blush_shimmer_eye`를 설득력 있게 만드는 최소 단위입니다. fileciteturn0file0

## 메이크업처럼 보이게 하는 시각 요인

AR 메이크업이 단순한 color overlay처럼 보이는 가장 큰 이유는 **피부 위에 얹힌 안료**로 보이지 않고, **화면 위에 떠 있는 색 레이어**처럼 보이기 때문입니다. 이를 가르는 첫 번째 요소는 **피부색과의 상호작용**입니다. 단순 source-over alpha도 어느 정도는 실제 배경과 섞이지만, 설득력 있는 결과를 내려면 backdrop 색을 기준으로 Multiply, Screen, Overlay, SoftLight 같은 혼합이 필요합니다. W3C compositing spec은 source-over의 기본 식을 `co = αs × Cs + αb × Cb × (1 − αs)`로 설명하고, Multiply는 `Cb × Cs`, Screen은 `1 - [(1 - Cb) × (1 - Cs)]`, SoftLight는 source 값에 따라 부드럽게 어둡게 하거나 밝게 하는 연산으로 정의합니다. 즉, “메이크업이 피부색 위에 어떻게 작동하는가”는 수학적으로도 alpha 하나가 아니라 blend function의 문제입니다. citeturn22view4turn22view0turn23view0turn23view1turn22view3

둘째는 **경계의 softness**입니다. 실제 립 틴트, 블러셔, 아이섀도는 대개 경계가 완전히 딱딱하지 않습니다. 특히 cheek와 eye는 feather가 없으면 스티커처럼 보입니다. 최신 controllable makeup transfer 연구도 spatial alignment와 part-specific control, region-adaptive normalization을 핵심 문제로 다룹니다. 즉, “어디에 칠하느냐”만이 아니라 “어떻게 가장자리를 사라지게 하느냐”가 품질을 좌우합니다. SARA는 spatial misalignment를 줄이기 위해 spatial alignment와 region-adaptive normalization을 분리했고, PSGAN/PSGAN++도 partial transfer와 shade-controllable transfer, detail-preserving transfer를 전면에 둡니다. 이 문헌 트렌드는 실시간 엔진에서도 `coverage`와 `feather`를 separate parameter로 둬야 한다는 강한 근거가 됩니다. citeturn28academia1turn28academia0turn28academia2

셋째는 **opacity와 coverage의 분리**입니다. 이 둘은 종종 하나처럼 취급되지만 시각적으로 다릅니다. opacity는 안료가 얼마나 강하게 보이는지를 정하고, coverage는 region 안에서 실제로 얼마나 넓고 균일하게 깔리는지를 정합니다. 예를 들어 `soft_blush`는 coverage는 넓지만 opacity는 낮아야 하고, `gloss_lip_focus`는 coverage는 비교적 높아도 pigment opacity와 gloss strength를 따로 다뤄야 자연스럽습니다. BeautyBank가 지적하듯, 기존 메이크업 연구가 저차원적인 색 분포만으로는 패턴과 디테일을 충분히 보존하지 못한다는 점은, 실시간 엔진에서도 “색의 세기”와 “패턴/분포”를 분리해야 함을 뒷받침합니다. citeturn28academia3

넷째는 **finish의 존재**입니다. 얼굴은 완전한 Lambertian 표면이 아니고, 현대 face reflectance 연구는 diffuse만으로는 실제 얼굴의 photorealism을 설명하기 어렵다고 반복해서 보여줍니다. 단일 이미지 기반 face reflectance 연구는 diffuse와 specular를 분리해 다루며, 더 최근 연구들은 specular albedo와 공간적으로 변하는 reflectance가 얼굴 realism에 중요하다고 봅니다. 따라서 lip gloss나 shimmer eye를 convincing하게 보이게 하려면, 색 레이어 위에 **view-dependent specular term**이나 **small-scale shimmer term**을 얹어야 합니다. matte는 이 term을 거의 죽이고, gloss는 살리고, shimmer는 noise-modulated highlight를 약하게 추가하는 식으로 finish를 modelled parameter로 가져가야 합니다. citeturn26academia1turn38academia4turn38academia9

다섯째는 **local skin detail preservation**입니다. 입술 결, 피부 밑의 명암, 눈두덩의 원래 shading이 어느 정도 남아 있어야 “메이크업을 바른 피부”처럼 보입니다. 색으로 완전히 덮어버리면 플라스틱처럼 보이거나 region 스티커처럼 느껴집니다. PSGAN++는 detail-preserving을 별도 문제로 다루고, AvatarMakeup은 expression과 viewpoint가 달라져도 makeup consistency를 유지하면서 fine detail control을 핵심 요구로 둡니다. 실시간 렌더러 쪽으로 옮기면 의미는 단순합니다. **색을 올리되, 원래 피부/입술 detail을 덮어 쓰지 말고 일부 남겨야 한다**는 것입니다. 이를 위해서는 blend mode 선택, opacity 제한, detail texture modulation, 그리고 필요하면 backdrop luminance를 유지하는 식의 보정이 필요합니다. citeturn28academia2turn29academia1

여섯째는 **모션 안정성**입니다. Unity AR Foundation에서 `ARFace`는 added/updated/removed lifecycle을 가지며, 시야에서 벗어날 때 완전히 removed되지 않고 `trackingState = Limited`로 남을 수 있습니다. 또한 face mesh가 지원되면 `ARFace.updated`에서 vertices, normals, indices, UVs가 갱신됩니다. 즉, convincing demo는 정지 프레임 한 장이 아니라 표정 변화와 lost/reacquired 상황에서도 region mask가 흔들리지 않아야 합니다. 따라서 렌더러는 `trackablesChanged`와 `trackingState`를 품질 요소로 간주해야 하며, face가 Limited가 되면 effect를 조금 감쇠시키거나 마지막 안정 프레임을 짧게 유지하는 식의 temporal strategy가 필요합니다. citeturn2view0turn2view1

## 권장 렌더링 모델과 셰이더 구조

가장 권장되는 구조는 **하나의 Master Makeup Shader + 지역별 material instance 또는 MaterialPropertyBlock**입니다. Shader Graph로도 시작할 수 있지만, 실제로는 블렌드 수식과 finish 항을 더 세밀하게 제어하기 위해 HLSL Custom Function 또는 hand-written shader가 더 유리합니다. Shader Graph 자체도 Blend Node에서 Multiply, Overlay, Screen, SoftLight 같은 모드를 지원하고, Sample Texture 2D 노드로 UV 기반 텍스처 샘플링을 안정적으로 사용할 수 있습니다. 따라서 “초기 설계는 Shader Graph, 성능/정밀 보정은 HLSL”이 가장 무난한 경로입니다. citeturn36view1turn41view0turn41view1turn41view2turn36view0

여기서 가장 중요한 설계 포인트는 **camera backdrop을 shader가 실제로 볼 수 있게 만드는 것**입니다. AR Foundation은 camera image 접근을 GPU와 CPU 두 경로로 나누는데, 단순 렌더링이나 셰이더 처리에는 GPU가 성능상 유리하며, AR camera background의 `_MainTex`를 RenderTexture로 blit해서 후속 처리에 쓸 수 있다고 문서가 직접 설명합니다. 반대로 CPU image는 픽셀 접근에는 유연하지만 더 resource-intensive합니다. 따라서 이 프로젝트의 “작고 그럴듯한” 데모 경로에서는 **매 프레임 GPU blit 한 번으로 camera background를 RenderTexture에 복사하고**, makeup shader가 그 텍스처를 screen-space에서 sample하도록 만드는 것이 가장 합리적입니다. 이 구조를 쓰면 blend mode가 “추상적 색 혼합”이 아니라 **실제 화면 속 피부 픽셀과의 혼합**이 됩니다. citeturn43view0

이 Master Shader는 논리적으로 두 층으로 나누는 것이 좋습니다. 첫 번째는 **Pigment Pass**입니다. 이 패스는 region mask, feather, coverage, base color, opacity, texture를 사용해 실제 메이크업 안료를 만듭니다. 두 번째는 **Finish Pass**입니다. 이 패스는 roughness/specular/gloss/shimmer를 사용해 view-dependent highlight를 얹습니다. `matte_lip`은 Pigment Pass만 강하고 Finish Pass를 약하게, `gloss_lip_focus`는 Pigment Pass 위에 좁고 밝은 finish highlight를 더 강하게, `shimmer_eye`는 미세 노이즈나 sparkle threshold를 가진 finish를 약하게 넣으면 됩니다. face reflectance literature가 diffuse와 specular를 분리해 다루는 이유도 정확히 여기에 맞닿아 있습니다. citeturn26academia1turn38academia4turn38academia9

지역 표현은 **UV-space mask atlas**를 권합니다. AR Foundation은 ARKit에서 face pose, face mesh vertices/indices, face mesh UVs, eye tracking, blend shapes까지 optional feature support를 제공합니다. 이미 현재 엔진의 snapshot에 mesh Summary와 stableUv 성격의 상태가 들어가 있고, validation 결과도 region dispatch는 확인됐습니다. 따라서 E7 spike에서는 실시간 segmentation을 새로 넣기보다, **ARFace mesh의 안정된 UV 위에 lip/cheek/eye mask를 얹는 방식**이 훨씬 작고 신뢰할 만합니다. `lip`은 하나의 mask여도 되지만, 실제 광택 표현을 조금 더 깨끗하게 하려면 upper/lower lip를 내부적으로 분리하는 편이 낫습니다. `cheek`는 좌우 대칭 mask 2개를 하나의 region으로 묶고, `eye`는 eyelid 중심의 부드러운 falloff mask로 시작하는 편이 좋습니다. citeturn30view0turn2view1turn36view0turn0file0

Unity 측 구현에서는 render queue와 transparency를 신중히 다뤄야 합니다. Unity 문서는 Transparent queue가 alpha-blended 물체를 위한 queue라고 설명하고, transparent 물체는 깊이 버퍼를 쓰지 않는 경우가 많다고 명시합니다. 또 ShaderLab의 Blend command 문서는 blending을 켜면 Early-Z 같은 GPU 최적화 일부가 꺼져 GPU frame time이 늘 수 있다고 설명합니다. 따라서 이 프로젝트에서는 **활성 region 수를 3개 이하로 고정하고**, **region당 pass 수를 1–2개로 제한**하며, **full-face 전체를 여러 번 무겁게 그리는 셰이더**를 피해야 합니다. E7용 데모라면 `lip`·`cheek`·`eye` 3개 region, 그리고 finish pass는 필요할 때만 켜는 방식이면 iPhone에서 충분히 현실적인 비용 범위에 들어갈 가능성이 높습니다. citeturn32view0turn32view1turn3view2turn34view0

색공간은 **반드시 Linear**를 권합니다. Unity는 texture가 대개 gamma color space로 저장되고 shader는 linear color space를 기대하므로, gamma 값으로 직접 샘플하면 결과가 부정확해질 수 있다고 설명합니다. AR 메이크업은 피부색 위에서 얇은 안료가 겹쳐지는 문제라서 gamma-space에서의 단순 연산은 특히 발색이 탁해지거나 예상보다 뜨는 문제를 만들기 쉽습니다. 즉 `#D94B74` 같은 recipe 색은 UI 전달값으로는 충분하지만, 실제 셰이더 연산 시에는 linear-space 변환 후 blend해야 “같은 opacity인데 피부 톤마다 예상과 다르게 튀는” 현상을 줄일 수 있습니다. citeturn3view3turn23view0turn23view1

정리하면, E7 spike에 맞는 최소 구조는 이렇습니다. **AR background GPU copy → UV region mask sampling → pigment blend → optional finish highlight → transparent composite**. 이것이 현재 broad debug mask에서 demo-quality cosmetic rendering으로 넘어가는 가장 작은 계단입니다. citeturn43view0turn30view0turn36view0turn3view2turn32view0

## 필수 파라미터 스키마

현재 rough schema는 이미 좋은 출발점입니다. 다만 `color`, `opacity`, `coverage`, `intensity`, `finish`, `blendMode`, `feather`, `texture`, `roughness`, `specular`, `shimmer`만으로는 “왜 이렇게 보여야 하는지”가 셰이더 입장에서 아직 약간 모호합니다. 그래서 E7 spike용으로는 **recipe에 넣을 값**과 **엔진이 내부적으로 계산할 값**을 구분하는 것이 좋습니다. 이 구분은 업로드된 검증 계획서가 요구한 조절 항목과도 잘 맞습니다. fileciteturn0file1

권장 recipe schema는 다음과 같습니다.

```json
{
  "version": 2,
  "lookId": "natural_daily",
  "layers": [
    {
      "id": "lip-primary",
      "region": "lip",
      "enabled": true,
      "order": 10,

      "color": "#D94B74",
      "opacity": 0.58,
      "coverage": 0.82,
      "intensity": 0.72,
      "feather": 0.10,

      "blendMode": "softLight",
      "finish": "cream",
      "texture": "lip_tint_soft",
      "textureAmount": 0.22,
      "detailScale": 1.0,

      "skinAdaptive": 0.55,
      "preserveDetail": 0.65,

      "roughness": 0.52,
      "specular": 0.18,
      "glossBoost": 0.00,
      "fresnel": 0.08,

      "shimmer": 0.00,
      "sparkleScale": 0.00,
      "sparkleThreshold": 1.00
    }
  ]
}
```

이 스키마에서 꼭 필요한 값은 생각보다 많지 않습니다. `region`은 당연히 필요하고, `color`, `opacity`, `coverage`, `feather`는 pigment의 모양을 결정합니다. `blendMode`는 피부와의 상호작용 방식을 정하고, `finish`는 셰이더의 내부 브랜치 선택을 간단하게 만듭니다. `texture`와 `textureAmount`는 “립 틴트인지 파우더 블러쉬인지 쉬머 섀도인지”를 구분하게 해주고, `roughness`, `specular`, `glossBoost`, `shimmer`는 finish pass를 제어합니다. `skinAdaptive`와 `preserveDetail`는 꼭 commercial SDK처럼 복잡하게 갈 필요는 없지만, 데모 품질에서는 매우 효율적인 파라미터입니다. 전자는 피부 톤에 따라 recipe color를 얼마나 보정할지를, 후자는 backdrop luminance/detail을 얼마나 살릴지를 뜻합니다. 이런 분리는 part-specific, shade-controllable, detail-preserving makeup control을 강조하는 최근 연구 흐름과 일치합니다. citeturn28academia0turn28academia1turn28academia2turn28academia3turn29academia1

반대로 엔진 내부에서 계산해야 하는 값은 recipe에 굳이 노출하지 않아도 됩니다. 예를 들어 `screenUV`, `faceTrackingState`, `cameraBackplateTex`, `regionMaskValue`, `stabilizedMask`, `localSkinMean`, `viewDotNormal`, `lightHint`, `temporalBlendAlpha` 같은 값은 renderer state에 속합니다. 특히 `localSkinMean`은 GPU camera copy를 직접 sample해서 region 주변부 또는 region 내부 low-pass 값으로 계산할 수 있고, `lightHint`는 ARCameraManager의 light estimation이 있을 때만 optional하게 활용하면 됩니다. 문서상 light estimation은 지원 여부가 기기와 camera facing direction에 따라 달라질 수 있으므로, front-camera face AR에서는 이것을 **필수 전제**로 두면 안 됩니다. 즉, 빛 추정은 “있으면 조금 더 좋게” 쓰고, 데모 품질의 핵심은 여전히 backdrop 기반 blend와 finish fake입니다. citeturn2view2turn43view0

실제 셰이더 쪽에서는 아래와 같은 순서가 가장 실용적입니다. 첫째, UV mask를 샘플해 `coverage`와 `feather`를 반영한 soft mask를 만듭니다. 둘째, backdrop 피부색을 camera RenderTexture에서 읽습니다. 셋째, recipe color를 linear로 변환하고 `skinAdaptive`만큼 backdrop 평균과 상호작용시켜 adjusted pigment color를 만듭니다. 넷째, Multiply·SoftLight·Screen·Overlay 중 선택된 모드로 pigment 색을 backdrop과 섞습니다. 다섯째, `preserveDetail`이 높으면 backdrop luminance나 미세 texture를 일부 유지합니다. 여섯째, finish pass에서 specular/gloss/shimmer를 view-dependent로 추가합니다. 이 흐름은 alpha compositing 공식, W3C blend mode 수식, Unity Blend Node 구현 예시, 그리고 face reflectance 논문들이 강조하는 diffuse/specular 분리와 모두 맞아떨어집니다. citeturn22view4turn23view0turn23view1turn22view3turn41view0turn41view1turn41view2turn26academia1turn38academia4

실무 추천값도 정리할 수 있습니다. `lip`은 기본적으로 `Multiply` 또는 `SoftLight`가 안전하고, gloss가 강한 경우 그 위에 작은 specular pass를 더하는 편이 좋습니다. `cheek`는 `SoftLight` 또는 `Screen` 계열이 자연스러운 경우가 많고, `coverage`는 넓게, `opacity`는 낮게 두는 편이 powder/cream 느낌을 살립니다. `eye`는 `SoftLight`, `Overlay`, 약한 `Screen`이 잘 맞으며, shimmer는 별도의 `shimmer` 파라미터를 낮게 두고 `textureAmount`와 분리해 제어하는 것이 안전합니다. 이 값 배치는 W3C/Shader Graph의 기본 수식 특성과, recent makeup transfer literature가 말하는 part-specific, degree-controllable, detail-preserving 제어 목표를 실시간 엔진 쪽으로 번역한 engineering inference입니다. citeturn23view0turn23view1turn22view3turn41view0turn41view1turn41view2turn28academia0turn28academia1turn28academia2

## 데모 품질에 맞는 룩 레시피

`natural_daily`는 가장 보수적이고 성공 확률이 높은 룩입니다. 이 룩의 목표는 “코스메틱이 존재하지만 전면적으로 튀지 않는 것”입니다. lip는 `SoftLight` 또는 약한 `Multiply`, opacity 0.45–0.60, coverage는 비교적 높게 두고 feather는 중간 정도가 적절합니다. cheek는 넓은 coverage, 낮은 opacity, 높은 feather가 핵심입니다. eye는 shimmer를 거의 끄고 low-contrast texture만 넣어야 전체 룩이 과장되지 않습니다. 이 룩은 피부 detail preservation이 잘 보이는지, 그리고 broad debug mask가 아니라 실제 메이크업처럼 “얇게 얹힌” 느낌이 나는지 확인하는 기준 룩이 됩니다. citeturn22view3turn28academia2turn28academia3

`gloss_lip_focus`는 데모 임팩트가 가장 큰 룩입니다. 이 룩에서 중요한 것은 lip pigment 자체보다 **finish layer 분리**를 보여주는 것입니다. pigment는 skin-adaptive tint처럼 유지하고, gloss는 좁은 하이라이트와 높은 specular, 낮은 roughness, 약한 fresnel boost로 표현하는 편이 좋습니다. 여기서 주의할 점은 gloss를 단지 `Screen`과 opacity로 흉내 내면 “젖은 흰색”처럼 보이기 쉽다는 것입니다. better path는 lip의 base tint를 먼저 backdrop과 섞고, 별도 finish term으로 카메라/라이트 방향에 반응하는 highlight를 얹는 것입니다. recent face reflectance 연구가 specular와 diffuse를 분리해 다루는 이유가 그대로 적용됩니다. citeturn26academia1turn38academia4turn38academia9

`soft_blush_shimmer_eye`는 feather 품질과 texture 제어를 보여주는 룩입니다. cheek는 powder-like softness가 중요하므로 mask 경계가 거의 느껴지지 않아야 하고, texture는 고대비가 아니라 약한 grain이어야 합니다. eye는 shimmer를 넣되 glitter particle처럼 보이기보다, soft highlight granularity처럼 보여야 설득력이 높습니다. AvatarMakeup이 표현·시점 consistency를 위해 global UV map을 강조하는 이유도, 이런 섬세한 eye detail이 고개 각도와 표정 변화에서 깨지지 않아야 하기 때문입니다. 그래서 이 룩은 texture가 보여야 하지만 mask 흔들림은 보여서는 안 됩니다. citeturn29academia1turn28academia3

세 룩 모두에서 recipe 파일을 완전히 따로 둘 필요는 없습니다. 하나의 마스터 스키마를 공유하고, 룩마다 `blendMode`, `texture`, `finish`, `specular`, `roughness`, `shimmer`, `skinAdaptive`, `preserveDetail`만 다르게 주는 것이 maintenance에 유리합니다. 다시 말해 이 프로젝트에서 필요한 것은 “수많은 제품 SKU”가 아니라, **같은 renderer가 finish와 texture를 다르게 보여줄 수 있다는 증거**입니다. 그것만 증명되면 E7 spike의 목적은 달성됩니다. fileciteturn0file0turn0file1

## iPhone 실시간 제약과 구현 우선순위

이 프로젝트는 Unity as a Library 제약을 피할 수 없습니다. Unity 공식 문서는 Unity as a Library가 iOS에서 full-screen rendering만 지원하고, Unity runtime의 lifecycle 제약이 있으며, quit 후 같은 process에서 다시 실행할 수 없고, unload 후에도 일부 메모리를 유지한다고 설명합니다. 따라서 renderer spike는 “기능을 계속 얹는 것”보다 **지금 있는 full-screen AR 경로에서 최소 draw와 최소 state change로 고품질을 확보하는 것**이 맞습니다. 렌더러를 정교하게 만들더라도 lifecycle 리스크를 키우면 안 됩니다. citeturn42view0turn42view1

셰이더 성능 측면에서는 Unity가 모바일에서 complex calculation을 피하고, fragment shader의 반복 계산을 줄이며, 필요할 경우 `half` 정밀도를 활용하고, `discard`와 depth-buffer writes를 피하라고 권장합니다. 또 blending 자체가 Early-Z를 약화시킬 수 있습니다. 따라서 E7 spike에서는 **pow/sin/log 남발**, **과한 procedural sparkle**, **여러 장의 고해상 mask를 겹치는 구조**, **fragment 단계의 무거운 조건 분기**를 피해야 합니다. 가장 좋은 전략은 룩을 늘리는 대신 `lip`, `cheek`, `eye` 3개 region에 대해서만 texture와 finish branch를 제한하고, 자주 바뀌지 않는 값은 C#에서 계산해 material property로 넘기는 것입니다. citeturn34view0turn33view0turn3view2

구현 우선순위는 명확합니다. 첫째, **Linear color space 전환**. 둘째, **AR background GPU copy RenderTexture 확보**. 셋째, **UV region mask atlas 도입**. 넷째, **Master Makeup Shader 작성**. 다섯째, **lip/cheek/eye 각 region에 material instance 연결**. 여섯째, **세 개의 룩 preset 작성**. 이 순서가 중요한 이유는, 현재 팀의 검증 문서에서도 이미 broad debug mask와 sample distinction은 확보됐고 product-quality renderer가 아직 비어 있기 때문입니다. 즉, next delta는 region dispatch가 아니라 **blend 질감과 finish 질감**입니다. fileciteturn0file0turn0file2turn0file3

또 하나 중요한 점은 **CPU image path를 기본 경로로 쓰지 말아야 한다**는 것입니다. AR Foundation 문서는 GPU가 단순 렌더/셰이더 처리에 가장 적합하고, CPU path는 pixel data 접근이 가능하지만 더 resource-intensive하다고 분명히 설명합니다. 그러므로 skin-tone-aware blending을 위해 매 프레임 CPU에서 얼굴 픽셀을 읽는 구조는 E7 spike 기준으로 과합니다. CPU path는 필요하다면 아주 드물게 region 주변 평균 색을 calibration 용도로 샘플링하는 정도로만 쓰고, per-pixel compositing은 GPU로 끝내는 편이 맞습니다. citeturn43view0

## 최종 권고안

이 프로젝트의 메인 질문에 대한 직접 답은 다음과 같습니다. **Unity + AR Foundation + ARKit iPhone AR makeup engine이 enterprise-demo-quality에 가까운 2–3개 샘플을 보여주려면, “face mesh 위에 색을 입히는 구조”가 아니라 “camera-backed skin compositing + UV region mask + pigment/finish 분리 셰이더” 구조가 필요합니다.** 이것이 최소 기술적으로 신뢰할 수 있는 렌더링 모델입니다. citeturn43view0turn30view0turn23view0turn22view3turn26academia1

권장 아키텍처를 더 압축하면 이렇습니다. **하나의 face mesh, 하나의 mask atlas, 하나의 master shader, region별 property set, camera backdrop RenderTexture, 그리고 룩별 preset JSON**. 이 구성은 현재 팀이 이미 검증한 RN↔Unity JSON bridge, ARFace 기반 region dispatch, validation texture sample handoff와 잘 맞고, 필요 이상으로 시스템을 확장하지 않습니다. 즉, commercial beauty SDK를 다시 만들지 않고도 “이 경로는 제품 품질로 hardening할 가치가 있다”는 데모를 보여주기에 충분합니다. fileciteturn0file0turn0file1

필수 파라미터는 최종적으로 다음 묶음이면 됩니다. **형상 파라미터**로 `region`, `coverage`, `feather`. **안료 파라미터**로 `color`, `opacity`, `blendMode`, `texture`, `textureAmount`, `skinAdaptive`, `preserveDetail`. **마감 파라미터**로 `finish`, `roughness`, `specular`, `glossBoost`, `fresnel`, `shimmer`. 이 정도면 matte, cream, gloss, shimmer를 모두 데모 수준에서 설명할 수 있습니다. 반대로 full relighting, true BRDF fitting, foundation shade matching, generative transfer runtime, multi-face social effect는 E7 spike 범위에서 빼는 것이 맞습니다. citeturn2view2turn34view0turn28academia1turn28academia3turn29academia1

가장 실용적인 engineering 판단은 이것입니다. **`natural_daily`는 SoftLight 중심, `gloss_lip_focus`는 pigment+finish 분리 증명, `soft_blush_shimmer_eye`는 feather+texture 증명**으로 나누어 구현하십시오. 세 룩이 각기 다른 기술 포인트를 대표하게 만들면, “이 엔진이 단순히 색을 칠하는가”가 아니라 “안료, 질감, 마감, 피부 상호작용을 구조적으로 제어할 수 있는가”를 팀에 명확하게 보여줄 수 있습니다. 그게 바로 지금 단계에서 필요한 시연 가치입니다. citeturn22view3turn23view0turn23view1turn26academia1turn28academia2turn29academia1