# E7 Lip Sample Pack v0 런타임 리뷰 컨텍스트

Last updated: 2026-06-25 KST

## 0. 이번 세션 대화 흐름 요약

이 문서는 최종 결과만이 아니라 이번 세션의 의사결정 흐름도 다음 세션에 넘기기 위한 컨텍스트이다.

대화 흐름은 아래 순서로 진행됐다.

1. 사용자는 E7 cosmetic rendering에서 첫 화장품 샘플 제작 방식을 물었다. 립을 예시로 들며 반복 실험 세팅을 고민했고, 슬라이드로 미리 볼지, 빌드 후 폰에서 바꿔가며 볼지 질문했다.
2. 방향은 **슬라이드 중심이 아니라 RN selector 기반 one-build / many-sample 방식**으로 정했다. 슬라이드는 결과 리뷰용이고, 실제 실험은 iPhone에서 `lookId`를 바꾸며 확인하는 방식이다.
3. 사용자는 finish도 바로 보고 싶다고 했다. daily와 texture만 나누면 나중에 gloss/finish를 또 봐야 하므로, 첫 빌드부터 `daily`, `gloss`, `texture` 3유형을 같이 비교하기로 했다.
4. texture에 대해서는 “새 제품 텍스처 asset 제작”이 아니라, 우선 `textureAmount`가 화장처럼 보이는 데 도움이 되는지 보는 최소 축으로 정의했다.
5. 사용자는 “계획 세워봐. 목표는 첫 번째 입술 샘플 만들기 - 계획에 있는 3유형”이라고 했고, 이후 `E7 Lip Sample Pack v0: daily / gloss / texture` 구현 계획을 승인했다.
6. 구현 범위는 E7.4 전체 진입이 아니라 **E7.3 Yellow risk를 알고 진행하는 lip-only 조건부 실험**으로 제한했다. `cheek`/`eye`는 payload에는 남기되 `enabled=false`로 꺼서 기존 3-layer Unity 계약을 유지했다.
7. 사용자가 “현재 파라미터는 임의값이냐”고 물었고, 이번 값들은 제품 검증값이 아니라 첫 실기기 관찰을 위한 seed/heuristic 값으로 봐야 한다는 전제로 진행했다.
8. 사용자가 “기기에서 색감과 속성 정도를 조절할 수 있나”라고 했고, RN compact HUD에서 색, finish, opacity/coverage/edge/tex/gloss를 조절할 수 있게 추가했다.
9. 사용자가 “Full Debug는 패널 때문에 얼굴이 안 보일텐데”라고 지적했고, Full Debug는 로그/메타 중심으로 두고, 실제 조정은 Compact HUD에서 하도록 했다. 다만 런타임 영상 리뷰 결과 Compact HUD도 여전히 너무 커서 다음 수정 대상이 됐다.
10. 사용자가 “현재 clean은 아무런 마스크가 적용되지 않아. 그냥 원본 얼굴이야. 그 점도 고쳐”라고 했고, Clean은 RN UI만 숨기고 makeup overlay는 유지하도록 바꿨다. 단, capture pair의 preclean reference capture는 예외적으로 overlay를 숨기는 특수 경로로 남겼다.
11. 사용자가 준비되면 빌드까지 진행하라고 승인했고, buildless checks 후 UnityFramework build/sync와 RN iPhone install/launch를 진행했다.
12. 첫 RN install은 `ios/Pods` 누락으로 실패했고, `pod install`로 CocoaPods를 복구한 뒤 RN install/launch를 통과했다.
13. 설치 후 사용자가 “카메라가 안 뜬다”고 했고, 스크린샷상 RN HUD는 보이지만 `tracking=waiting`, `recipe_applied waiting`인 상태였다. 원인은 카메라 권한 자체가 아니라 Unity view 초기화/브릿지 문제로 좁혀졌다.
14. 기기 프로세스에는 예전 standalone Unity 앱 `MakeupARUnityValidation.app`도 떠 있었으므로 종료했다. 이후 package-local `RNUnityView.mm` timing patch가 `pod install` 이후 사라진 것을 확인하고 복구했다.
15. `RNUnityView.mm`는 RN view가 실제 window와 non-zero bounds를 가진 뒤 Unity를 초기화하도록 다시 패치했고, RN 앱을 재빌드/재설치했다. 이후 카메라 feed와 tracking이 살아난 상태에서 사용자 런타임 영상이 제공됐다.
16. 사용자는 런타임 영상과 함께 4가지 문제를 제기했다: 입술 경계 이탈, HUD가 얼굴을 가림, 샘플 퀄리티 낮음, 슬라이더 조작 튐.
17. 영상과 contact sheet를 직접 확인했다. 카메라/tracking/mesh는 살아 있었지만, lip boundary는 broad mask 한계로 너무 둥글고 넓었고, HUD는 얼굴 하단을 가렸으며, gloss/texture는 실제 제품 finish가 아니라 약한 alpha/proxy 효과에 머물렀다.
18. 이후 사용자는 초보자도 이해할 수 있는 설명을 요청했고, 현재 v0가 “입술 화장 렌더러”가 아니라 “입술 근처에 반투명 색종이를 붙이는 실험판”에 가깝다는 식으로 설명했다.
19. 사용자는 “입술 모양 3D 모델을 만들어두고 상황마다 맞춰 쓰자”는 팀 의견을 물었다. 결론은 독립적인 예쁜 입술 3D 오브젝트를 얹는 방식은 위험하고, **ARFace에 종속된 lip patch / morph model**로 설계하는 방향은 타당하다는 것이다.
20. 사용자는 “입술 경계를 제대로 잡기 전까지 화장품 모델링은 의미 없냐”고 물었다. 답은 “shader 연구는 병렬로 가능하지만, 실시간 AR 품질 판단은 boundary가 먼저”로 정리했다.
21. 마지막으로 사용자는 이번 실험 결과, 문제, 문제 분석, 해결책, 세션 내용 전체를 다음 세션 컨텍스트용 문서로 만들어 달라고 했고, 이 문서를 생성했다.
22. 이후 사용자는 “블렌딩을 쓰면 안 되나, 직접 GPU를 다루면 되지 않나”라고 물었다. 결론은 블렌딩을 써야 하며, native Metal부터 갈 필요 없이 Unity shader의 fixed-function blend / multi-pass GPU renderer부터 검증하는 것이 맞다는 것이다.

따라서 다음 세션은 이 흐름을 이어 받아야 한다. 지금은 “샘플 값을 조금 더 만져보자”가 아니라, **실험 UX, lip boundary, renderer 구조를 고치는 단계**이다.

## 1. 한 줄 결론

이번 실험은 `lip_daily`, `lip_gloss`, `lip_texture` 3개 샘플을 실기기에서 바꿔보는 데는 성공했지만, 결과 품질은 기대보다 낮다.

핵심 원인은 추적이 죽은 것이 아니라, 현재 lip sample v0가 아직 **입술 화장 렌더러**가 아니라 **ARFace 위에 반투명 색을 얹는 검증용 레이어**에 가깝기 때문이다.

따라서 다음 세션은 파라미터 튜닝을 계속하기보다 아래 순서로 가야 한다.

```txt
HUD/slider 실험 UX 안정화
-> lip boundary model / mask 정교화
-> pigment/detail/gloss 3-layer lip renderer
-> 그 뒤에 sample recipe 재평가
```

이번 결과는 `continue`가 아니라 더 정확히는 **continue with revise**이다. 즉, RN + Unity + ARKit 경로는 유지하되, 현재 v0 방식 그대로 샘플을 늘리는 것은 중단해야 한다.

## 2. 이번 세션에서 만든 것

### RN sample pack

RN 쪽에서 lip-only v2 sample pack을 추가했다.

| lookId | 의도 | 주요 값 |
| --- | --- | --- |
| `lip_daily` | 자연스러운 daily cream | `#C76B74`, opacity `0.42`, coverage `0.72`, feather `0.10`, finish `cream` |
| `lip_gloss` | 진한 gloss | `#B83A55`, opacity `0.62`, coverage `0.86`, feather `0.06`, finish `gloss`, glossBoost `0.55` |
| `lip_texture` | matte texture | `#A94E5F`, opacity `0.54`, coverage `0.78`, feather `0.09`, finish `matte`, textureAmount `0.34` |

payload는 항상 3 layers를 유지한다. `lip`만 `enabled=true`이고 `cheek`, `eye`는 `enabled=false`로 유지한다.

관련 코드:

- `rn/MakeupARValidation/App.tsx`
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
- `unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader`

### HUD tuning

기기에서 직접 바꿀 수 있게 아래 컨트롤을 추가했다.

- sample 선택: `daily`, `gloss`, `texture`
- color 선택: `rose`, `berry`, `muted`, `coral`, `nude`
- finish 선택: `matte`, `cream`, `gloss`
- tuning field: `opacity`, `coverage`, `edge`, `tex`, `gloss`
- Clean은 이제 UI만 숨기고 makeup overlay는 유지하도록 변경했다.

### Build / install

빌드는 통과했고 iPhone 설치/launch까지 됐다.

| 항목 | 결과 | 증거 |
| --- | --- | --- |
| RN test | pass | `npm test -- --runInBand --watchman=false` |
| TypeScript | pass | `./node_modules/.bin/tsc --noEmit` |
| Lint | pass | `npm run lint` |
| UnityFramework build/sync | pass | `evidence/logs/e7-lip-sample-pack-v0-unityframework-20260625-150509.log` |
| RN iPhone install/launch | pass | `evidence/logs/e7-lip-sample-pack-v0-rn-ios-run-20260625-151236.log` |
| RNUnityView timing fix 후 reinstall | pass | `evidence/logs/e7-lip-sample-pack-v0-rn-ios-run-unityviewfix-20260625-152046.log` |

주의: `pod install` 이후 `node_modules/@azesmway/react-native-unity/ios/RNUnityView.mm` timing patch가 사라져 Unity view가 검은 화면으로 뜨는 문제가 재발했다. 후속 cleanup에서 `rn/MakeupARValidation/scripts/apply-rn-unity-timing-fix.js`, RN `postinstall`, iOS Podfile hook으로 이 패치를 durable하게 재적용하도록 고정했다.

## 3. 런타임 영상 증거

사용자 제공 영상:

```txt
/Users/wiseungcheol/Downloads/ScreenRecording_06-25-2026 15-25-02_1.mov
```

영상 메타데이터:

| 항목 | 값 |
| --- | --- |
| 길이 | 72.81초 |
| 해상도 | 1180x2556 |
| FPS | 약 60fps |
| 촬영 방식 | iPhone ReplayKit screen recording |

대표 contact sheet:

```txt
evidence/screenshots/e7-lip-sample-pack-v0-runtime-review-2026-06-25/contact-5s.jpg
evidence/screenshots/e7-lip-sample-pack-v0-runtime-review-2026-06-25/mouth-contact-5s.jpg
evidence/screenshots/e7-lip-sample-pack-v0-runtime-review-2026-06-25/slider-24-32-mouth.jpg
evidence/screenshots/e7-lip-sample-pack-v0-runtime-review-2026-06-25/slider-34-42-mouth.jpg
evidence/screenshots/e7-lip-sample-pack-v0-runtime-review-2026-06-25/slider-55-63-mouth.jpg
```

영상에서 확인된 좋은 점:

- 카메라 feed는 정상적으로 뜬다.
- AR tracking은 살아 있다.
- HUD에 `tracking=Tracking`, `faces=1`, `mesh=v=1220/i=6912/uv=1220`가 보인다.
- `lip` overlay는 얼굴에 붙어 움직인다.
- FPS는 대체로 60 근처로 보인다.

영상에서 확인된 실패:

- 입술 경계가 실제 입술 contour보다 넓고 둥글다.
- HUD 패널이 얼굴 하단 대부분을 가린다.
- `daily`, `gloss`, `texture` 차이가 제품 finish처럼 느껴지지 않는다.
- `TEX`는 입술결이라기보다 거의 색 변화에 가깝다.
- `gloss`는 젖은 광택이라기보다 색이 조금 진해지거나 밝아지는 정도다.
- 슬라이더를 직접 드래그할 때 값과 화면 변화가 튀는 느낌이 있다.

## 4. 문제 1: 입술 경계가 벗어난다

### 쉬운 설명

현재 앱은 매 프레임 실제 입술 윤곽선을 찾는 것이 아니다.

지금 방식은 아래에 가깝다.

```txt
iPhone ARKit이 제공하는 얼굴 mesh
-> 그 mesh의 UV 좌표 위에 미리 만든 입술 그림(mask)을 얹음
-> mask 안쪽에 색을 칠함
```

문제는 현재 입술 그림이 정교한 입술 모양이 아니라, 대략적인 입술 위치를 표시한 둥근 blob이라는 점이다.

그래서 사람마다 다른 아래 요소를 정확히 따라가지 못한다.

- 윗입술 산
- 입꼬리
- 윗입술 얇은 두께
- 아랫입술 중앙 볼륨
- 입을 벌릴 때 생기는 안쪽 빈 공간
- 웃거나 오므릴 때 바뀌는 contour

### 전문가용 원인

현재 `lip-smooth-mask-v1.png`는 512x512 fixed UV probability mask다. 실제 영상에서 보이는 경계 문제는 tracking failure가 아니라 mask prior의 표현력 부족이다.

Unity 렌더링은 전체 ARFace mesh를 그리고, shader에서 `_MaskTex`의 확률값으로 alpha를 자른다. 즉 geometry 자체가 입술 전용 mesh가 아니다.

관련 코드:

- `E3RegionMaskOverlay.ResolveMask()`는 `lip-smooth-mask-v1`을 고정으로 사용한다.
- `SmoothRegionMask.shader`는 `probability = tex2D(_MaskTex, input.uv).r`로 mask alpha를 만든다.
- `coverage`는 threshold를 조금 움직일 뿐이다.
- `feather`는 smoothstep의 폭을 조절할 뿐이다.

### 왜 edge를 늘려도 완전히 맞지 않나

`edge`는 실제 경계를 찾는 값이 아니다. 현재 구현에서 `edge`는 `feather`이고, 의미는 아래에 가깝다.

```txt
정확한 경계 보정 X
경계 흐림 정도 O
```

그래서 edge를 늘리면 틀어진 경계가 흐려져 덜 거슬릴 수는 있지만, 입술 산이나 입꼬리에 맞게 모양이 바뀌지는 않는다.

### 해결책

단기:

- `lip-tight-mask-v1`을 새로 만든다.
- 기존 `lip-smooth-mask-v1`은 broad/debug mask로 남긴다.
- sample pack의 기본 mask는 tight로 바꾼다.
- `coverage`와 `feather`의 실제 범위를 좁힌다.

중기:

- 전체 얼굴 mesh를 칠하는 대신 `lip patch mesh`를 만든다.
- ARFace vertex/UV 중 lip 주변만 골라서 전용 patch처럼 다룬다.
- 위/아래 입술, 입술 안쪽 line, 입꼬리 영역을 분리한다.

장기:

- ARKit blendshape 또는 face state를 이용해 `neutral`, `mouth_open`, `smile`, `pucker` 상태별 mask/patch 보정을 한다.
- 그래도 부족하면 MediaPipe/face parsing 같은 외부 contour prior를 fallback으로 검토한다. 단, iOS front camera 충돌과 성능 리스크 때문에 기본 경로로 바로 넣으면 안 된다.

## 5. 문제 2: HUD가 얼굴을 가린다

### 쉬운 설명

현재 HUD는 조정 도구라기보다 큰 디버그 패널이다. 얼굴을 보면서 값을 바꿔야 하는데, 정작 얼굴 하단과 입술 주변을 가린다.

Clean으로 가면 얼굴은 보이지만 조정이 어렵다. HUD로 가면 조정은 되지만 얼굴이 가린다. 실험 UX가 둘로 찢어진 상태다.

### 영상 관찰

contact sheet에서 HUD는 화면의 절반 가까이를 차지한다. 특히 입술을 가까이 가져가면 패널이 입술 하단, 턱, 목까지 크게 덮는다.

### 해결책

HUD를 bottom sheet 구조로 바꾼다.

권장 구조:

```txt
Collapsed HUD
- 높이 80-120px
- lookId / finish / FPS / latency
- sample chips 3개 정도만 표시

Expanded HUD
- 아래에서 올라오는 sheet
- 내부 ScrollView
- 색/finish/slider는 스크롤 안에 배치
- 얼굴 영역을 최소 65-70% 이상 남김
```

추가 권장:

- Compact HUD 기본은 collapsed.
- sample 버튼과 opacity 정도만 1차 노출.
- texture/gloss/coverage/edge는 expanded sheet로 이동.
- Clean은 시각 캡처용이지 조정용 escape hatch가 아니어야 한다.

## 6. 문제 3: 샘플 퀄리티가 낮고 변화가 작다

### 쉬운 설명

현재 `daily`, `gloss`, `texture`는 이름은 화장품 finish처럼 보이지만, 실제로는 대부분 같은 방식으로 그려진다.

지금 렌더러는 대략 이렇다.

```txt
반투명 색
+ 아주 약한 랜덤 grain
+ 고정 위치 하이라이트 조금
```

그래서 사용자가 보기에는 아래처럼 느껴진다.

```txt
daily / gloss / texture
= 색이 조금 진해지거나 흐려지는 정도
```

### 전문가용 원인

현재 shader는 unlit transparent alpha pass다.

중요한 한계:

- `blendMode=multiply`를 payload로 보내지만 shader pass는 실제 multiply가 아니다.
- `Blend SrcAlpha OneMinusSrcAlpha`라 일반 alpha blending이다.
- camera background color를 sampling하지 않는다.
- 피부/입술 원본 밝기와의 pigment mixing이 없다.
- `textureAmount`는 실제 lip wrinkle texture가 아니라 procedural grain이다.
- `glossBoost`는 실제 specular reflection이 아니라 UV-local highlight proxy다.
- normal/view/light 기반 반사가 없다.
- upper/lower lip highlight가 분리되어 있지 않다.
- 입술 세로 주름을 보존하거나 강조하지 않는다.

현재 texture 구현은 매우 약하다.

```txt
grainScale = 1.0 + (grain - 0.5) * textureAmount * 0.16
```

예를 들어 `textureAmount=0.34`이면 색 변화 폭은 약 2-3% 수준이다. 입술결로 보기 어렵다.

현재 gloss 구현도 단순하다.

```txt
horizontalCenter
lowerLipBand
specularShape
specularStrength
```

즉, “젖은 립글로스”가 아니라 “UV 위치 기반 밝은 띠”에 가깝다.

### 첨부 레퍼런스 수준에 필요한 구조

첨부된 립 레퍼런스는 단순 색칠이 아니라 아래 요소가 동시에 있다.

```txt
정확한 입술 contour
입술 안쪽/바깥쪽 농도 차이
세로 주름 보존
중앙부 광택
입술 경계 feather
피부/입술 원본 밝기와 자연스러운 blend
```

따라서 다음 renderer는 최소 3-layer로 나눠야 한다.

```txt
1. base pigment pass
   - 색/opacity
   - multiply 또는 soft-light 계열
   - 원본 입술 밝기 보존

2. detail pass
   - lip wrinkle texture
   - vertical grain
   - 원본 luminance/detail preservation

3. gloss pass
   - 별도 gloss mask
   - lower/upper lip highlight 분리
   - additive 또는 screen 계열
   - intensity, width, position 조절
```

### 현재 방식은 괜찮은가

배선 검증용으로는 괜찮다.

이번 v0는 아래를 확인했다.

- RN에서 sample 선택 가능
- v2 payload 전달 가능
- Unity에서 material/shader parameter 수신 가능
- 실기기에서 60fps 근처로 렌더링 가능

하지만 화장품 샘플 품질 평가 방식으로는 부족하다.

계속 현재 파라미터만 조정하면 실패할 가능성이 높다. 값이 잘못된 것이 아니라, 값이 제어하는 대상이 너무 단순하기 때문이다.

## 7. 문제 4: 슬라이더 조작이 튄다

### 쉬운 설명

현재 슬라이더는 손가락이 움직일 때마다 즉시 값을 계산하고, 즉시 Unity로 보낸다.

그래서 손가락 위치 계산이 조금만 흔들려도 값이 튀고, Unity도 너무 자주 새 recipe를 받는다.

### 전문가용 원인

현재 `TuningSlider`는 `event.nativeEvent.locationX`를 바로 사용한다.

문제:

- `locationX`는 responder target 기준이라 드래그 중 안정성이 떨어질 수 있다.
- track의 절대 좌표를 기준으로 계산하지 않는다.
- move event마다 `onChange`가 호출된다.
- `onChange`는 곧바로 `postRecipeBatch()`로 이어진다.
- 모든 tuning field가 같은 `0-1`, `0.05` step을 공유한다.

### 해결책

UI 계산:

- slider track의 screen x 좌표를 `measureInWindow`로 잡는다.
- `pageX - trackLeft`로 값을 계산한다.
- track 밖으로 나가도 clamp한다.

전송 방식:

- 드래그 중에는 RN local preview만 갱신한다.
- Unity post는 50-100ms throttle한다.
- 또는 `onPanResponderRelease`에서 commit한다.

field별 범위:

| field | 권장 범위 | 이유 |
| --- | --- | --- |
| opacity | `0.05-0.85` | 색 강도는 넓게 봐도 됨 |
| coverage | `0.45-0.90` | mask threshold와 연결되므로 과도한 변화 방지 |
| edge/feather | `0.01-0.20` | 너무 넓으면 경계가 퍼져 보임 |
| textureAmount | `0.00-1.00` | 단, shader 개선 후 의미 있음 |
| glossBoost | `0.00-1.00` | 단, gloss pass 분리 후 의미 있음 |

## 8. GPU 블렌딩 / 직접 GPU 렌더링 논의

사용자는 “블렌딩을 쓰면 안 되나, 직접 GPU를 다루면 되지 않나”라고 질문했다.

결론:

```txt
블렌딩은 써야 한다.
지금 문제는 블렌딩을 쓰면 안 되는 것이 아니라,
현재 v0가 실제 화장품용 블렌딩을 거의 쓰지 않는다는 점이다.
```

현재 shader는 일반 alpha blending에 가깝다.

```txt
입술 mask 안에
반투명 색을
SrcAlpha OneMinusSrcAlpha로 얹음
```

payload에는 `blendMode=multiply`가 들어가지만, 현재 shader pass는 실제 multiply pigment blend가 아니다. 즉, RN recipe의 `blendMode` 값과 GPU의 실제 blend equation이 아직 일치하지 않는다.

### GPU를 쓰는 현실적인 단계

바로 native Metal/custom plugin으로 갈 필요는 없다. RN + Unity + ARKit validation 경로에서는 아래 순서가 더 안전하다.

```txt
1. Unity shader fixed-function blending
2. Unity shader multi-pass renderer
3. 필요하면 camera/background texture sampling
4. 그래도 부족하면 native Metal/custom plugin
```

### 우선 가능한 pigment multiply

립 pigment는 단순 alpha overlay보다 multiply 계열이 더 맞다.

목표:

```txt
원본 입술/피부 색 * 립 색
```

효과:

```txt
색이 얼굴 위에 떠 있는 느낌 감소
원래 입술 명암 일부 보존
반투명 색종이 느낌 완화
```

Unity fixed-function blending으로도 1차 근사는 가능하다.

```shader
Blend DstColor Zero
```

단, 그냥 pigment color를 곱하면 너무 어두워질 수 있으므로 shader 출력은 아래처럼 설계하는 편이 낫다.

```txt
sourceColor = lerp(white, lipColor, alpha)
finalColor = cameraColor * sourceColor
```

이렇게 하면 alpha가 낮을 때는 원본에 가깝고, alpha가 높을 때는 lip pigment가 더 강하게 섞인다.

### gloss는 pigment와 다른 pass가 맞다

Gloss는 pigment와 같은 방식으로 처리하면 안 된다.

```txt
pigment = multiply 계열
gloss = additive 또는 screen 계열
```

예:

```shader
Blend SrcAlpha One
```

또는 screen에 가까운 pass를 따로 만들 수 있다.

따라서 lip renderer v1은 최소 아래처럼 나누는 것이 맞다.

```txt
Pass 1: base pigment multiply
Pass 2: lip detail / wrinkle
Pass 3: gloss highlight additive or screen
```

### 블렌딩만으로는 boundary를 고칠 수 없다

중요한 점:

```txt
좋은 블렌딩은 질감을 고친다.
좋은 boundary model은 위치를 고친다.
```

만약 mask가 입술 밖으로 벗어난 상태에서 multiply/gloss를 잘 만들면, 결과는 더 자연스럽게 “입술 밖에 잘못 칠한 화장”이 될 수 있다.

정리하면 아래와 같다.

```txt
경계가 틀림 + 좋은 블렌딩
= 더 그럴듯하게 잘못 칠해짐

경계가 맞음 + 나쁜 블렌딩
= 위치는 맞지만 색종이 같음

경계가 맞음 + 좋은 블렌딩
= 화장처럼 보이기 시작
```

따라서 다음 세션에서는 boundary와 renderer를 경쟁시키지 않는다. 둘은 병렬로 가되, 실시간 AR 품질 판정은 boundary가 어느 정도 맞은 뒤에 한다.

### 다음 renderer 실험 제안

lip renderer v1의 첫 GPU 실험은 아래가 적당하다.

```txt
1. 현재 alpha overlay baseline
2. pigment multiply pass
3. pigment multiply + separate gloss pass
4. pigment multiply + lip detail texture + gloss pass
```

실험 질문:

- `alpha`보다 `multiply`가 피부/입술에 더 자연스럽게 섞이는가?
- gloss pass가 색 농도와 분리되어 보이는가?
- detail pass가 noise가 아니라 입술결로 보이는가?
- boundary가 아직 broad일 때도 renderer 차이가 눈에 보이는가?
- renderer 차이는 보이지만 boundary 때문에 최종 품질 판정이 막히는가?

이 실험은 native Metal이 아니라 Unity shader에서 먼저 한다. native Metal/custom plugin은 Unity shader와 URP/custom pass로 충분히 해결되지 않을 때만 검토한다.

## 9. 3D 입술 모델 의견에 대한 판단

팀에서 나온 “입술 모양 3D 모델을 만들어두고 상황마다 맞춰 쓰자”는 의견은 방향성이 있다. 단, 구현 형태를 정확히 잡아야 한다.

권장하지 않는 방향:

```txt
독립적인 예쁜 입술 3D 오브젝트를 만들고
카메라 얼굴 위에 따로 얹기
```

이 방식은 아래 상황에서 쉽게 어긋난다.

- 입을 벌림
- 웃음
- 오므림
- 고개 회전
- 입꼬리 움직임
- 사람마다 다른 입술 두께

권장 방향:

```txt
ARFace mesh
-> lip anchor vertices 선택
-> lip patch mesh 생성
-> lip UV/mask 정교화
-> 표정/blendshape에 따라 morph
-> 그 위에 pigment/detail/gloss 렌더링
```

즉, “입술 3D 모델”은 독립 오브젝트가 아니라 **ARFace에 종속된 lip patch / morph model**이어야 한다.

외부 3D 모델은 쓸 수 있지만, 목적은 완성 렌더링 모델이 아니라 아래에 가깝다.

```txt
lip patch/mask 설계를 위한 reference
ARFace topology/UV에 맞춘 retopology reference
```

## 10. 경계 전에는 화장품 모델링이 의미 없는가

정확히 말하면 이렇다.

```txt
경계가 안 맞는 상태에서도 shader 연구는 가능하다.
하지만 실시간 AR 화장품 품질 판단은 경계가 먼저다.
```

입술은 cheek보다 훨씬 민감하다. 경계가 몇 mm만 벗어나도 바로 티가 난다. 좋은 pigment/gloss shader를 만들어도 위치가 틀리면 “예쁜 화장”이 아니라 “잘못 칠한 색”처럼 보인다.

그래서 우선순위는 아래가 맞다.

```txt
1. 입술 경계/위치
2. 입 벌림, 웃음, 오므림에서 경계 유지
3. pigment/detail/gloss
4. sample recipe tuning
```

다만 병렬로 할 수 있는 일은 있다.

- static frame에서 3-pass lip shader prototype
- pigment/detail/gloss 파라미터 설계
- 레퍼런스 이미지 기반 quality target 분해
- HUD/slider UX 개선

하지 말아야 할 일:

- 현재 broad mask 위에서 gloss/texture 값만 계속 튜닝
- 경계가 안 맞는 상태로 sample quality를 Green/Red 판정
- `textureAmount`, `glossBoost` 수치만 늘려서 제품처럼 보이길 기대

## 11. 다음 세션 권장 작업 순서

### Phase A: 실험 UX 복구

목표: 얼굴을 보면서 조정할 수 있게 만든다.

작업:

- Compact HUD를 collapsed bottom sheet로 변경
- 상세 컨트롤은 `ScrollView` 내부로 이동
- 기본 화면에는 sample chips + 핵심 상태만 남김
- slider coordinate 계산 안정화
- slider Unity post throttle 또는 release commit 적용
- field별 range 분리

판정:

- 얼굴/입술이 HUD에 가리지 않는다.
- 조정 중 값이 튀지 않는다.
- Clean으로 가지 않아도 비교가 가능하다.

### Phase B: lip boundary v1

목표: 현재 broad mask를 대체할 tight lip boundary를 만든다.

작업:

- `lip-tight-mask-v1.png` 제작
- 기존 `lip-smooth-mask-v1.png`와 A/B 선택 가능하게 유지
- upper/lower lip 분리 가능성 검토
- mouth opening에서 inner mouth 영역 색칠 방지
- 영상 10초로 neutral/open/smile/pucker 확인

판정:

- edge를 크게 만지지 않아도 기본 경계가 입술에 맞는다.
- 입꼬리와 윗입술 산이 broad blob처럼 보이지 않는다.

### Phase C: lip renderer v1

목표: daily/gloss/texture가 실제로 다른 기술 질문을 보이게 만든다.

작업:

- base pigment multiply pass
- detail/wrinkle pass
- gloss highlight additive 또는 screen pass
- 실제 GPU blend mode 또는 유사 구현
- gloss용 별도 mask/UV band
- texture용 vertical lip grain

판정:

- `daily`는 얇은 pigment로 보인다.
- `gloss`는 색과 광택이 분리되어 보인다.
- `texture`는 단순 noise가 아니라 입술결 방향성이 보인다.

### Phase D: sample pack 재정의

목표: 현재 3개 sample 값을 폐기하거나 재보정한다.

작업:

- 새 mask/renderer 기준으로 `lip_daily`, `lip_gloss`, `lip_texture` 재설정
- 기존 v0 값은 reference only로 남김
- 기기에서 one-build / many-sample 방식으로 재검증

## 12. 다음 세션 프롬프트 초안

```txt
cwd=/Users/wiseungcheol/Desktop/makeupAR

AGENTS.md와 TECH_VALIDATION_RESULT.md Current Session Snapshot을 먼저 읽고,
docs/roadmaps/active/E7_LIP_SAMPLE_PACK_V0_RUNTIME_REVIEW_CONTEXT_KO.md를 이번 작업 컨텍스트로 사용해줘.

목표는 E7 Lip Sample Pack v0의 런타임 리뷰에서 나온 문제를 해결하는 첫 수정이다.

우선순위:
1. Compact HUD를 collapsed bottom sheet + ScrollView 구조로 바꿔 얼굴을 보면서 조정할 수 있게 한다.
2. 슬라이더를 안정화한다. locationX 직접 사용을 줄이고, drag 중 Unity post를 throttle 또는 release commit으로 바꾼다.
3. 이번 세션에서는 lip renderer product quality를 주장하지 않는다.
4. GPU blending은 native Metal이 아니라 Unity shader fixed-function blend / multi-pass부터 검증한다.
5. 가능하면 lip-tight-mask-v1 제작/연결 계획까지 세우되, 바로 E7.4 Green을 주장하지 않는다.

검증:
- npm test -- --runInBand --watchman=false
- npm run lint
- ./node_modules/.bin/tsc --noEmit
- buildless checks 후 필요하면 사용자 승인 받고 iPhone build

주의:
- RNUnityView.mm timing patch는 RN `postinstall`과 iOS Podfile hook으로 재적용된다. clean reinstall 후에는 hook 실행 로그와 Unity view initialization만 확인한다.
- 현재 v0 shader는 unlit alpha + weak grain + fixed gloss proxy라 샘플 품질 판단에는 한계가 있다.
- 다음 실기기 판정은 Green/Yellow가 아니라 continue / revise / stop으로 기록한다.
```

## 13. 현재 결정

이번 lip sample pack v0는 다음처럼 기록한다.

| 항목 | 결정 |
| --- | --- |
| RN/Unity payload wiring | continue |
| 실기기 build/install path | continue |
| 현재 HUD 실험 UX | revise |
| 현재 lip boundary | revise |
| 현재 gloss/texture 표현 | revise |
| 현재 v0 파라미터 추가 튜닝 | stop 또는 낮은 우선순위 |
| full E7 Green / product readiness | 불가 |

요약:

```txt
기술 경로는 유지한다.
하지만 현재 sample v0를 더 튜닝하는 대신,
실험 UX, lip boundary, renderer 구조를 순서대로 고친다.
```
