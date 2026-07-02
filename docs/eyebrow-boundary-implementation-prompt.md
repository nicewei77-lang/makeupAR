# Eyebrow Boundary Goal Prompt

## 역할
너는 React Native + Unity 기반 AR 메이크업 앱에서 눈썹 필터를 구현하고 디버깅하는 담당자다.

앱 구조는 다음과 같다.

- React Native: UI, 상태, 색상/강도/투명도/스타일 선택, Unity로 recipe 전달
- Unity: ARKit/ARFoundation Face Mesh 기반 립, 볼터치, 눈썹 렌더링
- MediaPipe: 눈/눈썹 주변 기준점과 ROI를 잡는 보조 엔진
- Unity Shader: 최종 UV mask 안에 색상, feather, strand texture를 합성

## 현재 가장 큰 문제
지금 가장 큰 문제는 **눈썹 위에 마스크를 눈썹 모양대로 올리지 못하는 것**이다.

현재 눈썹 렌더링은 다음 문제가 반복된다.

- 눈썹 머리 부분이 미간/중앙 이마 쪽으로 침범한다.
- 전체 경계가 눈썹 모양이 아니라 울퉁불퉁한 덩어리처럼 보인다.
- 실제 사용자 눈썹의 몸통과 꼬리를 안정적으로 따라가지 못한다.
- 마스크가 눈썹 위가 아니라 눈/눈꺼풀 근처에 붙거나 위치가 흔들린다.
- 후보 PNG 또는 검출된 털 픽셀을 최종 눈썹 모양처럼 써서 스티커처럼 보인다.
- 색상/투명도/결 texture를 조정해도 boundary가 틀려서 자연스럽지 않다.

따라서 이번 목표는 색상이나 texture 튜닝이 아니라 **정돈된 eyebrow makeup boundary engine을 먼저 완성하는 것**이다.

## 이미 된 것
다음은 이미 어느 정도 구현되어 있으므로 처음부터 다시 만들지 않는다.

- React Native에서 eyebrow UI/recipe 경로가 존재한다.
- Unity 쪽 eyebrow runtime/rendering 경로가 존재한다.
- eyebrow 색상 선택이 동작한다.
  - black
  - dark brown
  - brown
  - light brown
  - wine
- eyebrow 스타일 버튼이 존재한다.
- Unity 쪽 주요 파일이 연결되어 있다.
  - `unity/MakeupARUnityValidation/Assets/Scripts/E7MediaPipeEyebrowBoundaryRuntime.cs`
  - `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
  - `unity/MakeupARUnityValidation/Assets/Shaders/EyebrowRegionMask.shader`
- MediaPipe/FaceLandmarker 기반 경로는 추가되어 있다.
- ARFace mesh/UV 기반 렌더링 경로는 존재한다.
- 눈썹이 완전히 지연 없이 따라오는 방향은 일부 개선되었다.
- 립/볼터치 기능은 기존 기능으로 유지되어야 한다.

## 아직 안 된 것
다음 항목은 아직 완료로 보지 않는다.

- 사용자 실제 눈썹 위에 최종 mask가 정확히 올라가지 않는다.
- 눈썹 모양이 매끄럽지 않고 화장용 눈썹 경계처럼 보이지 않는다.
- 눈썹 머리, 몸통, 산, 꼬리가 자연스럽게 연결되지 않는다.
- 미간 침범이 완전히 해결되지 않았다.
- 꼬리가 얇고 흐리게 빠지지 않고 잘리거나 뭉친다.
- 3개 스타일이 명확히 구분되지 않는다.
  - semi arch
  - straight
  - arch
- 후보 PNG가 strand/density source로만 쓰이고 있다고 검증되지 않았다.
- boundary가 ARFace UV mask로 안정적으로 bake되어 다양한 얼굴 각도에서 유지되는지 검증되지 않았다.
- 실제 기기에서 립/볼터치와 눈썹이 동시에 문제 없이 유지되는지 최종 검증되지 않았다.

## 잘못된 접근
다음 방식으로 계속 진행하면 안 된다.

- 후보 눈썹 PNG를 얼굴 위에 그대로 스티커처럼 붙이기
- 검출된 어두운 털 픽셀 외곽선을 그대로 최종 mask로 쓰기
- MediaPipe landmark를 완성된 눈썹 경계라고 가정하기
- 색상, opacity, intensity만 올려서 경계 문제를 가리기
- 예상 렌더만 보고 실제 AR runtime에서 된 것처럼 말하기
- 립/볼터치 경로를 건드려 눈썹 문제를 해결하려 하기

## 올바른 방향
상용 필터에 가까운 구조는 다음 하이브리드 방식이다.

1. MediaPipe landmark로 눈/눈썹 주변 ROI를 잡는다.
2. 눈 landmark를 exclusion zone으로 사용해서 mask가 눈으로 내려오지 못하게 한다.
3. 실제 어두운 눈썹 털 픽셀은 위치/높이 참고값으로만 사용한다.
4. 최종 경계는 head/body/arch/tail control point로 만든다.
5. 이 control point를 부드러운 곡선으로 연결해 makeup eyebrow envelope를 만든다.
6. 생성된 envelope를 ARFace UV mask에 bake한다.
7. Unity shader는 그 mask 안에서만 렌더링한다.
   - 기존 눈썹 tone을 살짝 낮추는 neutralizer
   - 색을 입히는 tint/multiply layer
   - 후보 PNG를 모양이 아니라 strand/density texture source로 섞는 layer
   - blur/feather/smoothing

핵심은 **위치와 형태는 boundary engine이 만들고, PNG는 결 표현에만 쓰는 것**이다.

## 목표 눈썹 모양

### 1. Semi Arch
- 일자 눈썹과 아치 눈썹의 중간 형태
- 앞머리는 낮고 둥글게 시작
- 앞부분부터 중간까지는 거의 일자처럼 자연스럽게 이어짐
- 길이의 60-70% 지점에서 아주 완만한 낮은 산 생성
- 산은 뾰족하지 않고 부드러운 곡선
- 꼬리는 눈꼬리 방향으로 살짝 내려가며 얇고 흐리게 끝남

마스크 표현:

- 앞머리는 연하게
- 몸통은 중간 농도
- 산 부분은 살짝 진하게
- 꼬리는 얇고 흐리게
- 가장자리는 부드러운 회갈색 feather gradient

### 2. Straight
- 전체적으로 수평에 가까운 직선형
- 앞머리는 둥글고 부드럽게 시작
- 몸통은 거의 같은 높이로 길게 이어짐
- 눈썹산은 없거나 아주 약함
- 꼬리는 갑자기 꺾이지 않고 살짝 낮아지며 자연스럽게 얇아짐

마스크 표현:

- 윗선/아랫선이 칼같은 직선이면 안 됨
- 앞머리는 가장 연하게
- 몸통 중앙은 중간 농도
- 꼬리는 끝으로 갈수록 투명하게 사라짐

### 3. Arch
- 세미 아치보다 곡선이 뚜렷한 아치형
- 앞머리는 낮고 부드럽게 시작
- 몸통은 중앙 이후 점점 위로 올라감
- 길이의 65-75% 지점에서 가장 높은 산 생성
- 산은 둥글게 처리하되 세미 아치보다 높이가 분명해야 함
- 꼬리는 산 이후 아래쪽으로 자연스럽게 내려가며 길고 얇게 빠짐

마스크 표현:

- 산 부분이 가장 선명함
- 앞머리와 꼬리는 흐림
- 꼬리는 두껍지 않고 길고 얇게 빠짐
- 끝부분은 투명하게 사라짐

## 구현 우선순위

1. boundary-only overlay부터 고친다.
2. 머리, 몸통, 산, 꼬리 control point를 deterministic curve로 만든다.
3. 미간 침범을 막기 위해 brow head inset/min nose gap을 적용한다.
4. eye exclusion zone을 적용해 mask가 눈으로 내려가지 않게 한다.
5. 실제 털 픽셀은 중심선/높이 보정에만 약하게 사용한다.
6. 좌우 눈썹은 각각 생성하되 기본 비율과 스타일 규칙은 대칭성을 유지한다.
7. boundary가 통과된 뒤에만 색상/feather/strand texture를 조정한다.
8. 마지막에 Unity device runtime에서 UV mask가 얼굴 움직임을 따라가는지 확인한다.

## 구현 시 유의사항

- 기존 립/볼터치 동작을 수정하거나 회귀시키면 안 된다.
- eyebrow 관련 코드와 shader/material/asset/schema만 좁게 수정한다.
- broad rebuild나 반복 Unity export를 먼저 하지 않는다.
- 예상 렌더와 runtime 증거를 구분해서 보고한다.
- route/debug 문제는 route가 실제로 깨졌을 때만 본다. 지금 주 문제는 route가 아니라 boundary shape/placement다.
- 후보 PNG는 texture/density source로만 사용한다.
- static preview가 맞아도 실제 AR runtime 검증 전에는 완료라고 말하지 않는다.

## 필요한 디버그 출력
다음 디버그는 boundary가 어디에 생성되는지 확인하기 위해 필요하다.

- MediaPipe eye/brow 기준점
- brow ROI
- eye exclusion zone
- final control points
- final smooth envelope polygon
- UV-baked mask preview
- exaggerated fill preview
- left/right orientation check

단, 디버그는 진행을 돕기 위한 수단일 뿐이고 최종 목표는 자연스러운 눈썹 boundary다.

## 통과 기준
다음 조건을 만족해야 한다.

1. 마스크가 실제 사용자 눈썹 몸통 위에 올라간다.
2. 눈썹 머리가 미간/중앙 이마를 침범하지 않는다.
3. 경계가 울퉁불퉁하지 않고 매끄러운 눈썹 모양이다.
4. semi arch, straight, arch 세 가지가 눈으로 구분된다.
5. 꼬리가 잘리지 않고 얇고 흐리게 빠진다.
6. 눈 영역과 겹치지 않는다.
7. 색상/결 texture는 boundary 안에서만 보인다.
8. 얼굴 각도가 바뀌어도 ARFace UV mask가 눈썹 위치를 따라간다.
9. 립과 볼터치가 눈썹과 동시에 정상 동작한다.
10. 실제 기기 runtime evidence로 검증된다.

## 보고 형식
작업 보고는 다음 형식으로 한다.

- Done
- Not Done
- Current blocker
- Files changed
- Preview/evidence path
- Device verification status
- Next action

완료라고 말하려면 정적 예상 이미지가 아니라 실제 기기에서 눈썹 위에 boundary/mask가 안정적으로 붙는 증거가 있어야 한다.
