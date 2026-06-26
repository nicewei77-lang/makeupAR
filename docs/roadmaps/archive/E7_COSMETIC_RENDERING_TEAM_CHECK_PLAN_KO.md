# E7 코스메틱 렌더링 팀 계획 확인서

Last updated: 2026-06-23 KST

## 1. 한 줄 결론

E7.4/E7.5는 “얼굴 위에 색을 칠하는 기능”이 아니라, 현재 RN + Unity + ARKit 경로가 **메이크업처럼 보이는 검증용 렌더러**로 발전할 수 있는지 확인하는 실험이다.

핵심 구조는 다음 하나로 고정한다.

```txt
ARFace UV region mask
-> coverage / feather
-> pigment blend
-> finish / texture
-> iPhone 실기기 증거
```

짧게 말하면 아래 뜻이다.

| 용어 | 뜻 |
| --- | --- |
| ARFace UV region mask | iPhone ARFace 얼굴 지도 위에 `lip`, `cheek`, `eye` 위치를 표시한 영역 |
| coverage | 화장이 얼마나 넓게 덮이는지 |
| feather | 화장 경계가 얼마나 부드럽게 사라지는지 |
| pigment blend | 색이 피부색과 어떻게 섞이는지 |
| finish | matte, cream, gloss, shimmer처럼 표면이 어떻게 보이는지 |

## 2. 현재 진입 조건

현재 E7.3 Region Precision은 아직 Yellow다. P8 runtime sweep으로 `lip`, `cheek`, `eye` 모두 얼굴에 붙는 가능성은 좋아졌지만, 실루엣과 디버그 표면이 아직 Q3 overlay-ready 수준은 아니다.

여기서 Q3 overlay-ready는 “예쁘다”가 아니다. 실제 메이크업 렌더러를 얹어 실험해도 될 만큼 위치, 경계, 움직임이 안정적이라는 뜻이다.

따라서 E7.4는 아래 중 하나가 기록된 뒤에만 시작한다.

| 조건 | 의미 |
| --- | --- |
| Q3 통과 | `lip`, `cheek`, `eye`가 실제 메이크업 레이어를 올려볼 만큼 경계와 움직임이 안정적이다. |
| Yellow risk 수용 | 팀이 남은 region 리스크를 알고도 E7.4를 실험한다. 이 경우 전체 E7 Green은 불가하고 최대 Yellow다. |

E7.2 로그, E7.3 빌드 성공, offline atlas 점수만으로는 E7.4에 들어가지 않는다.

## 3. 우리가 검증할 렌더러

E7.4의 본질은 `color + opacity`가 아니다. 아래 세 그룹을 독립적으로 조절할 수 있어야 한다.

| 그룹 | 파라미터 | 쉬운 의미 |
| --- | --- | --- |
| Placement | `region`, `coverage`, `feather` | 어디까지 바르고, 가장자리가 얼마나 자연스럽게 사라지는가 |
| Pigment | `color`, `opacity`, `blendMode`, `textureAmount`, `skinAdaptive`, `preserveDetail` | 색이 피부와 섞이며 피부결을 살리는가 |
| Finish | `finish`, `roughness`, `specular`, `specularPower`, `glossBoost`, `shimmer`, `shimmerColor` | 매트, 크림, 글로스, 쉬머가 실제로 다르게 보이는가 |

기본 방향은 이렇다.

| 부위 | 기본 화장품 | 핵심 값 |
| --- | --- | --- |
| `lip` | tint / cream lipstick / gloss | `multiply`, tight feather, gloss는 별도 highlight |
| `cheek` | powder / cream blush | `softLight`, 낮은 opacity, 넓은 coverage, 큰 feather |
| `eye` | matte shadow / shimmer | `multiply` 또는 `softLight`, texture 기반 shimmer |

## 4. 팀 병렬 실험 방식

최종 데모는 3개만 남기지만, 탐색은 9개 샘플로 병렬 진행한다. 9개는 최종물이 아니라 인사이트 채굴용이다.

각 샘플은 완성작이 아니라 `recipe` 후보이다. 팀원은 색, 강도, feather, finish 값을 제안하고, 실기기 결과에서 무엇이 좋아졌고 무엇이 실패했는지 기록한다.

| 팀원 슬롯 | 샘플 1 | 샘플 2 | 샘플 3 |
| --- | --- | --- | --- |
| A | `daily_subtle` | `gloss_balanced` | `texture_bold` |
| B | `daily_balanced` | `gloss_bold` | `texture_subtle` |
| C | `daily_bold` | `gloss_subtle` | `texture_balanced` |

`subtle`, `balanced`, `bold`는 난이도가 아니라 표현 강도다.

| 강도 | 목적 |
| --- | --- |
| `subtle` | 최소로 자연스럽게 보이는 값 찾기 |
| `balanced` | 데모에서 차이가 보이지만 과하지 않은 값 찾기 |
| `bold` | 스티커, 흰 페인트, 과한 shimmer가 되는 한계 찾기 |

각 컨셉의 질문은 다르다.

| 컨셉 | 질문 | 주로 볼 값 |
| --- | --- | --- |
| `daily` | 피부에 얇게 섞이는가 | `opacity`, `blendMode`, `skinAdaptive`, `preserveDetail` |
| `gloss` | 립 색과 광택이 분리되어 보이는가 | `roughness`, `specular`, `specularPower`, `glossBoost`, `screen` |
| `texture` | 블러셔 feather와 eye shimmer가 설득력 있는가 | `coverage`, `feather`, `textureAmount`, `shimmer`, `shimmerColor` |

## 5. 최종 룩 합성

9개 샘플을 모두 살리지 않는다. 팀 리뷰 후 좋은 조각만 뽑아 최종 3개 룩으로 압축한다.

좋은 조각은 팀 리뷰에서 선택한다. 예를 들어 A의 `daily_subtle`에서 skin blend를 가져오고, C의 `texture_balanced`에서 cheek feather 값을 가져오는 식이다.

| 최종 룩 | 가져올 인사이트 |
| --- | --- |
| `natural_daily` | 가장 좋은 skin blend + 가장 자연스러운 lip/cheek/eye 균형 |
| `gloss_lip_focus` | 가장 좋은 lip pigment + 과하지 않은 움직이는 gloss highlight |
| `soft_blush_shimmer_eye` | 가장 좋은 cheek feather + 안정적인 eye shimmer |

최종 3개 룩은 각각 다른 기술 질문을 증명해야 한다. 단순히 “색이 다른 세 가지”면 실패다.

## 6. 판정 기준

E7.4 Green은 예쁜 취향이 아니라 구조적 증거다.

Green 조건:
- old alpha/debug overlay보다 명확히 메이크업처럼 보인다.
- `coverage`, `feather`, `blendMode`, `texture`, `finish`가 눈으로 구분된다.
- `lip`, `cheek`, `eye`가 E7.3에서 인정한 수준보다 더 나빠지지 않는다.
- raw frame 저장, 업로드, AI, backend, SDK, Android가 없다.
- 성능이 즉시 무너지는 징후가 없다.

Yellow 조건:
- 방향은 좋아졌지만 한 부위나 한 finish가 아직 약하다.
- 실기기에서 보이긴 하지만 특정 표정이나 각도에서만 설득력 있다.
- 계속 실험할 가치는 있지만 Green으로 말하기에는 증거가 부족하다.

Red 조건:
- 여전히 색 스티커처럼 보인다.
- gloss가 흰 페인트처럼 보인다.
- shimmer가 노이즈처럼 보인다.
- finish를 넣자 region 안정성이 깨진다.
- 실기기에서 렌더링이나 성능이 버티지 못한다.

## 7. 하지 않는 것

이번 단계에서는 하지 않는다.

쉽게 말하면, 이번 단계에서는 무거운 상용 뷰티 앱 전체를 만들지 않고 현재 경로가 계속 투자할 가치가 있는지만 검증한다.

- 제품급 makeup renderer 주장
- full PBR / true BRDF / relighting
- foundation shade matching
- CPU image 기반 무거운 per-pixel 처리
- raw camera frame 저장 또는 업로드
- MediaPipe live runtime, face parsing product path
- commercial SDK 통합
- Android / ARCore
- M7 Green 승격

## 8. 공유 문서

- [E7 master plan](E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md)
- [현재 결과 스냅샷](../../../TECH_VALIDATION_RESULT.md)
- [Cosmetic rendering research - GPT](../research/E7_AXIS2_COSMETIC_RENDERING_GPT.md)
- [Cosmetic rendering research - Claude](../research/E7_AXIS2_COSMETIC_RENDERING_CLAUDE.md)
- [Performance evidence plan](E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md)
