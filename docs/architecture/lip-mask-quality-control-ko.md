# 립 마스크 품질 관리 결정 기록

작성일: 2026-06-27

## 목적

립 메이크업 렌더링에서 `Full`, `Overlip`, `Gradient`, `Glossy`가 서로 다른 의미의 축으로 조합되어야 한다. 이 문서는 마스크/셰이더/디버그 UI를 어떻게 정리했는지와, 대화 중 결정한 품질 관리 기준을 기록한다.

## 핵심 결론

- 상용 제품 기준으로는 사람이 검수하는 원본 PNG를 스타일별로 따로 관리하고, 런타임용 atlas는 스크립트로 자동 생성하는 방식이 가장 낫다.
- `Matte`, `Normal`, `Glossy`는 finish 타입이고, `Full`, `Gradient`, `Overlip`은 립 영역/밀도 스타일이다. 두 축은 독립 조합 가능해야 한다.
- `Atlas`, `Vision`, `Flat/Drawn`은 경계/마스크 소스 선택이지, `Gradient` 같은 립 스타일과 같은 층의 버튼이 아니다.
- `Glossy`는 립 전체를 빛나게 하는 효과가 아니라, 별도 highlight alpha mask에만 additive highlight를 얹는 방식이어야 한다.
- 마스크 PNG는 감마 보정이 들어간 색 이미지처럼 처리하면 경계가 생길 수 있으므로 Unity import에서 `sRGBTexture=false`로 linear/raw mask처럼 다뤄야 한다.

## 원본 마스크와 런타임 Atlas

원본 위치:

- `unity/MakeupARUnityValidation/Assets/SourceMasks/Lip/full.png`
- `unity/MakeupARUnityValidation/Assets/SourceMasks/Lip/overlip.png`
- `unity/MakeupARUnityValidation/Assets/SourceMasks/Lip/gradient-density-pronounced.png`
- `unity/MakeupARUnityValidation/Assets/SourceMasks/Lip/glossy-highlight.png`

런타임 atlas 생성 스크립트:

- `scripts/e7_reference_atlas/build_lip_source_mask_atlas.py`

생성되는 atlas:

- `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/lip-drawn-style-atlas-v1.png`
- `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/lip-drawn-gradient-density-atlas-v1.png`

RGBA 채널 의미:

| 채널 | 의미 | 품질 기준 |
| --- | --- | --- |
| R | Full mask | 립 전체 베이스. mesh culling의 기본 기준 |
| G | Overlip mask | 라인만이 아니라 안쪽 립 베이스를 포함한 오버립 영역 |
| B | Gradient density | PNG 자체가 강한 농도 차이를 갖는 gradient 밀도 |
| A | Glossy highlight | 반짝이는 부분 전용 alpha mask |

## Raw Mask와 Processed Mask

`Raw mask`는 PNG/atlas 채널에서 읽은 원래 값이다. 예를 들어 Gradient raw는 B 채널 값이고, Glossy raw는 A 채널 값이다.

`Processed mask`는 셰이더에서 raw 값에 soft sampling, `threshold`, `smoothstep`, `pow`, coverage, opacity, preserve-detail 같은 처리를 거친 뒤 실제 화면 alpha/강도로 쓰는 값이다.

이번 UI에는 `Final`, `Raw`, `Processed` 디버그 모드를 추가했다. `Raw`는 PNG 채널 자체를 회색 alpha로 보여주고, `Processed`는 셰이더 계산 뒤의 최종 마스크 강도를 보여준다.

## Gamma와 Linear 처리

경계가 생기는 흔한 이유는 마스크를 색 이미지처럼 sRGB/gamma 공간에서 샘플링한 뒤 threshold/smoothstep을 적용하기 때문이다. 이 경우 중간값이 시각 색상용 곡선으로 왜곡되어 경계가 두꺼워지거나 끊겨 보일 수 있다.

마스크는 색이 아니라 수치 데이터이므로 linear/raw 값으로 처리해야 한다. 그래서 `Assets/Resources/SmoothRegionMasks/`뿐 아니라 `Assets/SourceMasks/` 아래 PNG도 Unity import에서 `sRGBTexture=false`, readable, uncompressed로 고정했다.

## Mesh Culling 결정

이전 문제는 렌더링/mesh culling이 Full, 즉 R 채널 중심으로 묶여 있어서 `Overlip`이나 `Gradient` 차이가 실제 화면에서 죽어 보일 수 있었다는 점이다.

이번 기준:

- Full/Normal/Matte/Glossy full: R
- Overlip: R + G
- Gradient: R + B
- Glossy highlight: culling 기준이 아니라 A 채널 highlight pass 전용

이렇게 하면 Gradient는 B 채널 밀도 영역을, Overlip은 G 채널 확장 영역을 mesh 단계에서도 살릴 수 있다.

## Glossy 구현 결정

Glossy는 "립 전체 발광"이 아니라 "반짝이는 부분만 additive highlight"가 맞다. 그래서 별도 `glossy-highlight.png`를 A 채널로 패킹하고, 셰이더의 glossy pass는 `_GlossMaskTex` alpha만 읽는다.

별도 highlight 마스크를 써도 soft sampling, threshold, smoothstep, coverage, opacity 같은 처리는 적용 가능하다. 마스크 파일을 나누는 것은 처리 기능을 포기하는 것이 아니라, 검수 가능한 원본을 명확히 나누는 일이다.

## Gradient Density

Gradient 전용 density는 "어디가 더 진하고 어디가 더 옅은지"를 나타내는 밀도 지도다. 단순히 Full mask에 shader 수식으로 gradient를 만들 수도 있지만, PNG 자체에 gradient를 가진 파일이 더 자연스럽고 디자이너 검수가 쉽다.

이번에는 `gradient-density-pronounced.png`를 기본 소스로 사용한다. 통계상 Full보다 훨씬 좁고 강한 중심 밀도를 갖도록 만들었다.

## Guide와 Mesh QA

품질 검사용 overlay 원칙:

- Guide: 초록색, 얼굴 라인/중요 landmark 확인용
- Mesh: 노란색, wire overlay 확인용
- Filled face mesh는 노란 면처럼 보일 수 있으므로 품질 검사 기본값으로 쓰지 않는다

RN UI의 `Mask`, `Guide`, `Mesh`, `Diagnostics`, `Final`, `Raw`, `Processed` 버튼으로 각각 켜고 끌 수 있게 했다.

## 이번 적용 파일

- `rn/MakeupARValidation/App.tsx`
  - `Normal/Matte/Glossy` finish 축과 `Full/Gradient/Overlip` area 축 유지
  - `Final/Raw/Processed` mask debug view 추가
  - `Overline` 사용자 표시를 `Overlip`으로 변경
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
  - `maskDebugViewMode` payload 파싱 및 렌더러 전달
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
  - style-aware mesh culling 추가
  - mask debug view mode를 material에 전달
- `unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader`
  - Raw/Processed 디버그 출력
  - Glossy pass는 디버그 모드에서 비활성화
  - Overlip을 라인 전용이 아니라 채워진 오버립 영역으로 계산
- `unity/MakeupARUnityValidation/Assets/Editor/SmoothRegionMaskTextureImporter.cs`
  - runtime mask와 source mask를 linear/readable/uncompressed로 import
- `scripts/e7_reference_atlas/build_lip_source_mask_atlas.py`
  - 개별 source mask에서 런타임 RGBA atlas 생성

## 보류한 아이디어

지금 당장 적용하지 않은 것:

- 16-bit mask: banding 증거가 생기면 도입한다.
- dithering: gradient banding이 실제 기기에서 보일 때만 검토한다.
- normal-aware glossy: 얼굴 조명/normal 안정성이 확보된 뒤 glossy 품질 개선용으로 검토한다.
- 내부 ID `overline_lip` 전체 rename: 현재 브리지/테스트/기존 recipe 호환을 위해 유지하고, 사용자-facing 용어만 `Overlip`으로 정리했다.

## QA 체크 기준

1. `Raw`에서 Full/Overlip/Gradient 모양이 서로 달라야 한다.
2. `Processed`에서 threshold/feather/coverage를 거친 뒤에도 Overlip과 Gradient 차이가 남아야 한다.
3. `Final`에서 Glossy는 립 전체가 빛나는 것이 아니라 highlight mask 부분만 반짝여야 한다.
4. `Mesh`는 노란 wire 기준으로 확인하고, 면이 통째로 노랗게 채워지면 filled face renderer가 켜졌는지 확인한다.
5. 새 립 스타일이 늘어나면 개별 source PNG를 추가하고 atlas packer에 채널/출력 규칙을 확장한다.
