# E7 개인 맞춤 립 Generate 완전 구현 계획

작성일: 2026-06-27 KST

## 0. 결정

이번 작업의 목표는 단순 후보 비교가 아니라 **완성품에 가까운 개인 맞춤 립 마스크 생성 흐름**을 만든 뒤, 웹앱 베타 검증, 실제 iPhone 앱 빌드, 최종 런타임 테스트까지 닫는 것이다.

핵심 결론:

```txt
사용자가 Generate를 누른다
-> 현재 얼굴 기준으로 로컬에서 입술 2D boundary를 만든다
-> 같은 순간의 ARFace mesh/screen/UV snapshot으로 개인 맞춤 UV mask를 만든다
-> runtime에서는 이 UV mask를 계속 샘플링한다
-> Vision 방식과 MediaPipe 방식을 비교한다
-> Blendshape Assist Off/On을 비교한다
-> 얼굴을 가리는 로그/HUD 없이 실제 AR 화면에서 판단한다
```

이번 계획은 archived `E7_LIP_CANDIDATE_GENERATOR_FAST_SPIKE_PLAN_KO.md` 이후의 실행 계약이다. 이전 후보 생성 실험은 evidence와 archive로 남기고, 현재 active 목표는 **local personalized lip generate**이다.

## 1. 제품 사용자 시나리오

### 1.1 기본 사용자 흐름

사용자는 기술 후보를 이해하지 않아도 된다. 앱 안에서 경험해야 하는 흐름은 아래와 같다.

```txt
1. 앱 진입
2. AR 카메라 화면 진입
3. "입술 맞춤 생성" 시작
4. 안내: 입을 편하게 다물고 정면을 본다
5. Generate 누름
6. 앱이 현재 얼굴에서 입술 마스크를 만든다
7. 즉시 AR 화면에 립 메이크업이 적용된다
8. Vision / MediaPipe 결과를 비교한다
9. 기본 / 표정 보정 결과를 비교한다
10. 필요하면 corner / upper / lower / y를 조정한다
11. 마음에 드는 결과를 선택한다
12. smile / open-close / pucker / yaw에서 최종 확인한다
```

### 1.2 검증 앱 노출 용어

검증 단계에서는 내부 엔진 상태를 볼 수 있어야 한다.

```txt
Provider:
- Vision
- MediaPipe

Expression:
- UV Only
- Blendshape Assist

Adjustment:
- cornerReach
- upperLipTightness
- lowerLipTightness
- verticalOffset
```

제품 표현으로 바꿀 때는 아래처럼 숨긴다.

```txt
Vision / MediaPipe -> 기본 생성 / 정밀 생성 후보
UV Only -> 기본 적용
Blendshape Assist -> 표정 보정
corner / upper / lower / y -> 입꼬리 / 윗입술 / 아랫입술 / 위치
```

### 1.3 사용자가 보아야 하는 화면

사용자에게 얼굴 중앙을 가리는 큰 로그를 보여주면 안 된다.

```txt
Clean:
- 얼굴과 메이크업만 보인다
- 최종 시각 판단용

Compare HUD:
- 화면 하단에 Provider, Assist, Generate, Apply, 조정값만 보인다
- 얼굴 중앙을 가리지 않는다

Debug:
- 전체 로그, payload, FPS, latency, mesh, blendshape 값을 본다
- 기본 화면이 아니며 최종 screenshot/recording 판단에는 쓰지 않는다
```

## 2. 범위

### 2.1 포함

- React 웹앱 베타 테스트 환경.
- 웹앱에서 마스크 생성 로직 검증.
- 웹앱에서 2D mask -> UV texture -> screen round-trip 검증.
- 로컬 서버 HTTP 경유 생성 실험.
- RN과 호환되는 TypeScript 상태/계약 정의.
- 앱 내 Generate 흐름.
- on-device Vision provider.
- MediaPipe provider 비교 경로.
- Vision 방식과 MediaPipe 방식 비교.
- Blendshape Assist Off/On 비교.
- Runtime dynamic UV mask 적용.
- 얼굴을 가리지 않는 HUD/로그 구조.
- iPhone 빌드와 최종 실기기 evidence loop.

### 2.2 제외

- 서버 업로드 기반 제품 흐름.
- raw camera frame 장기 저장.
- 상용 SDK 도입.
- Android.
- E7.4/E7.5/E7.6 일반 cosmetic renderer 확장.
- live face parsing/Core ML runtime.
- 매 프레임 Vision/MediaPipe boundary 재생성.
- product-ready 또는 E7.3 Green 자동 선언.

## 3. 핵심 아키텍처

### 3.1 전체 구조

```txt
React Web Beta
  -> shared TypeScript contract/core
  -> fixture replay
  -> local HTTP generation server
  -> browser MediaPipe preview
  -> 2D->UV->round-trip validation

RN App
  -> same provider/assist/adjustment state model
  -> Generate button
  -> user-facing Compare HUD
  -> Unity message contract

Unity Runtime
  -> current ARFace snapshot
  -> dynamic UV Texture2D generation/application
  -> smooth-region-mask shader sampling
  -> blendshape assist material parameters
  -> runtime metrics/events

iOS Native Providers
  -> Apple Vision on-device lip contour
  -> MediaPipe on-device provider if feasible
```

### 3.2 공통 계약

웹앱, RN, Unity가 같은 개념을 써야 한다.

```ts
type LipMaskProvider = "vision" | "mediapipe";

type ExpressionAssistMode = "uvOnly" | "blendshapeAssist";

type LipGenerateStatus = "ready" | "partial" | "blocked";

type LipAdjustment = {
  cornerReach: number;
  upperLipTightness: number;
  lowerLipTightness: number;
  verticalOffset: number;
};

type LipGenerateRequest = {
  requestId: string;
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  adjustment: LipAdjustment;
  frameSource: "fixture" | "webcam" | "ios-current-frame";
  privacy: {
    localOnly: true;
    offDeviceUpload: false;
    longTermRawFrameStored: false;
  };
};

type LipGenerateResult = {
  status: LipGenerateStatus;
  generatedMaskId: string;
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  uvMaskReady: boolean;
  roundTripReady: boolean;
  runtimeApplyReady: boolean;
  warnings: string[];
  blockedReason?: string;
};
```

### 3.3 로컬 개인화 모델 산출물

이 계획에서 말하는 "로컬 모델 생성"은 서버에서 학습한 ML 모델을 내려받는 뜻이 아니다. 사용자의 현재 얼굴과 같은 순간의 ARFace 데이터를 이용해, 기기 안에서 재사용 가능한 **개인화 립 적용 패키지**를 만드는 뜻이다.

최소 산출물:

```txt
generatedMaskId
provider
expressionMode
adjustment
sourceFrameMetadata
sourceFaceState
lipBoundary2D
uvMaskTexture
uvCoverageMetadata
roundTripPreview
runtimeApplyPayload
qualityWarnings
createdAt
privacyFlags
```

앱 runtime은 이 패키지를 계속 샘플링한다. 매 프레임 Vision/MediaPipe를 다시 돌리거나, 서버에 얼굴 이미지를 보내거나, raw frame을 장기 저장하지 않는다.

## 4. 웹앱 베타 테스트 설계

웹앱은 Unity/ARKit 대체물이 아니다. 웹앱의 목적은 **서비스 흐름과 마스크 생성 핵심 로직을 빌드 전에 고정하는 것**이다.

### 4.1 웹앱에서 반드시 검증할 것

```txt
1. Generate UX가 자연스럽다
2. Vision / MediaPipe 선택이 명확하다
3. UV Only / Blendshape Assist 비교가 가능하다
4. 조정값이 화면과 payload에 일관되게 반영된다
5. 실제 mask가 생성된다
6. UV texture가 생성된다
7. UV -> screen round-trip이 입술 위치로 돌아온다
8. 좌표, mirror, orientation 문제가 warning으로 드러난다
9. RN/Unity로 넘길 payload가 고정된다
```

마스크 생성 없이 UI만 통과하면 실패다.

### 4.2 웹앱 구현 위치

권장 위치:

```txt
web/lip-generate-beta/
packages/lip-generate-core/
local-tools/lip-generate-server/
```

`packages/lip-generate-core/`는 DOM에 의존하지 않는 순수 TypeScript로 둔다.

포함할 핵심:

```txt
contracts.ts
lipBoundaryProvider.ts
uvProjector.ts
roundTripPreview.ts
adjustmentModel.ts
blendshapeAssistModel.ts
payloadBuilder.ts
validationGates.ts
```

### 4.3 화면 구성

#### Generate

- sample fixture 선택.
- webcam 선택.
- Provider: Vision / MediaPipe.
- Expression: UV Only / Blendshape Assist.
- Generate 버튼.
- status: ready / partial / blocked.
- warnings.
- Vision은 단순 polygon 직선 fill이 아니라 `vision_curve_fill` 방식으로 Apple Vision 점을 부드러운 closed curve로 이어 채운다.
- adjustment를 바꾸면 기존 preview를 그대로 valid로 두지 않고 "다시 생성 필요" 상태를 표시한다.

#### Inspect

- 원본 frame.
- 2D boundary overlay.
- hard mask.
- soft alpha.
- UV texture preview.
- UV round-trip overlay.
- coordinate diagnostics.

#### Compare

4개 조합을 한 화면에서 본다.

```txt
Vision + UV Only
Vision + Blendshape Assist
MediaPipe + UV Only
MediaPipe + Blendshape Assist
```

#### Payload

- RN request preview.
- Unity ApplyGeneratedLipMask payload preview.
- evidence metadata.
- JSON export.

#### Save

- 조정이 반영된 최신 결과만 저장할 수 있다.
- 저장 대상은 local-only `generated_lip_package.json`이다.
- 저장 후 목록에는 provider, assist, adjustment, package path, runtimeReady 상태가 보여야 한다.
- raw camera frame은 저장하지 않는다.

### 4.4 웹앱에서 마스크를 만드는 방법

웹앱은 렌더링 최종 품질을 못 보더라도 mask 생성은 해야 한다. 가능한 경로는 세 가지다.

#### A. Fixture replay

기존 evidence를 읽는다.

```txt
frame.png
arface_export.json
apple_vision_lip_contour.json
mediapipe_lip_curve_points.json
mediapipe_lip_curve_mask.png
```

장점:

- 가장 빠르다.
- 재현성이 좋다.
- 2D->UV->round-trip 검증에 충분하다.

한계:

- live webcam이나 iPhone current frame 검증은 아니다.

#### B. Browser MediaPipe

브라우저에서 webcam + MediaPipe Web Face Landmarker를 돌린다.

장점:

- 서비스 흐름을 사용자가 직접 느낄 수 있다.
- MediaPipe 후보는 실제로 브라우저에서 생성 가능하다.
- Blendshape-like 값도 비교 실험에 쓸 수 있다.

한계:

- ARKit mesh가 아니다.
- 최종 iPhone ARFace UV 증거가 아니다.

#### C. Local HTTP server

웹앱이 `localhost` 로컬 서버에 요청한다.

```txt
POST /api/lip-mask/generate
POST /api/lip-mask/project-uv
POST /api/lip-mask/round-trip
GET  /api/lip-mask/runs/:runId
GET  /api/lip-mask/saved
POST /api/lip-mask/save
```

서버는 repo의 기존 script나 새 helper를 호출한다.

```txt
scripts/e7_lip_boundary_fusion/extract_apple_vision_lip_contour.swift
scripts/e7_lip_candidate_generator/retry_mediapipe_lip_landmarker.py
scripts/e7_lip_uv_projection/prepare_one_frame_round_trip.py
```

장점:

- Apple Vision fixture 또는 Swift extractor를 웹앱에서 간접 호출할 수 있다.
- Python/MediaPipe helper를 브라우저 제약 없이 쓸 수 있다.
- mask 생성과 UV projection을 build 전 자동화할 수 있다.

한계:

- 제품 runtime path가 아니다.
- local-only 개발 서버임을 UI와 로그에 명확히 표시해야 한다.
- raw frame은 장기 저장하지 않는다.

### 4.5 웹앱 통과 기준

웹앱에서 아래가 모두 통과해야 앱 구현으로 넘어간다.

```txt
- Vision fixture 또는 local server 경로로 mask 생성 성공.
- MediaPipe fixture/browser/local server 중 최소 하나로 mask 생성 성공.
- 두 provider 모두 UV texture 생성 성공.
- 두 provider 모두 round-trip overlay가 입술 위치로 돌아옴.
- adjustment 값이 preview와 payload에 반영됨.
- adjustment 값이 실제 2D mask / UV / round-trip 생성에 반영됨.
- 조정 후 재생성 전 stale 상태가 UI에 표시되고 저장이 막힘.
- Blendshape Assist Off/On payload 차이가 명확함.
- 조정 완료 후 local-only 패키지 저장 가능.
- 얼굴 중앙을 가리는 debug UI가 기본 화면에 없음.
- generatedMaskId, provider, expressionMode, privacy flags가 기록됨.
```

## 5. 실제 앱 구현 설계

### 5.0 iPhone 앱 페이지 구조

RN 앱은 웹 베타의 좌측 control panel / 우측 preview grid를 복사하지 않는다. 실제 앱은 AR 카메라가 주 화면이고, 조작은 하단 페이징 HUD로 잠깐 올라오는 구조여야 한다.

원칙:

```txt
- UnityView는 full-bleed로 둔다.
- 얼굴 중앙과 입술 주변에는 로그, 큰 카드, payload를 올리지 않는다.
- 한 페이지에서는 한 가지 판단만 시킨다.
- Debug는 별도 sheet/page로 격리한다.
- 웹의 4-card 동시 비교는 모바일에서 쓰지 않고, 한 후보씩 live AR에 적용해 비교한다.
```

페이지:

```txt
Ready:
  - 정면 준비 안내
  - Provider segmented control: Vision / MediaPipe
  - Assist segmented control: Off / On
  - CTA: 입술 맞춤 생성

Generating:
  - 하단 4-step progress: 현재 얼굴 캡처 / 입술 경계 / UV 변환 / AR 적용
  - 얼굴 위 로그 금지
  - 실패 시 하단 한 줄 blockedReason

Result:
  - 한 후보만 AR 얼굴에 적용
  - 하단 버튼: 비교 / 조정 / 저장 / 다시 생성
  - 상단 tiny status: provider, assist, partial/blocked

Compare:
  - 하단 candidate strip: Vision Off / Vision On / MediaPipe Off / MediaPipe On
  - 탭 또는 스와이프할 때 같은 얼굴 위에 한 후보씩 적용
  - IoU와 payload는 Debug에서만 표시

Adjust:
  - 한 번에 한 조정 축만 보여준다: 입꼬리 / 윗입술 / 아랫입술 / 위치
  - 기본 조작은 `- / +` stepper, slider는 보조
  - 조정값 변경 후에는 mask 재생성이 필요한지, shader preview만 바뀐 것인지 명확히 표시

Save:
  - generatedMaskId, provider, expressionMode, adjustment, runtimeApplyPayload, qualityWarnings, privacyFlags 저장
  - 저장 후 neutral / smile / open-close / pucker / yaw evidence 체크로 이동

Debug:
  - payload JSON, warnings, mesh counts, blendshape values, latency, FPS
  - 최종 시각 판단 screenshot/recording 화면으로 쓰지 않는다
```

### 5.1 Generate는 진짜 생성이다

Generate는 미리 baked된 asset을 고르는 버튼이 아니다.

```txt
Generate 누름
-> current frame snapshot
-> current ARFace snapshot
-> provider 실행
-> 2D lip boundary 생성
-> UV mask 생성
-> dynamic Texture2D 생성
-> material에 적용
-> runtime event/log 기록
```

### 5.2 Provider

#### Vision

1차 제품 경로로 둔다.

```txt
current frame
-> Apple Vision face landmarks
-> outer/inner lip points
-> no-CV curve fill
-> hard mask + soft alpha
```

주의:

- OpenCV/scikit-image 보정은 이번 경로에서 제외한다.
- color snap도 boundary source로 쓰지 않는다.
- Vision 결과가 없으면 `blocked`로 기록한다.

#### MediaPipe

비교 provider로 둔다.

```txt
current frame
-> MediaPipe Face Landmarker
-> lip landmarks
-> no-CV lip curve fill
-> hard mask + soft alpha
```

주의:

- on-device 통합이 막히면 `blocked`로 기록한다.
- 서버 우회는 제품 경로가 아니라 개발/비교 경로다.
- 최종 앱에서 MediaPipe live integration을 넣을지는 성능/빌드/라이선스 확인 후 결정한다.

### 5.3 2D -> UV projection

필수 입력:

```txt
frame size
screenVertices
uvs
indices
orientation
isMirrored
viewport/safeArea
clipW 또는 perspective semantics
depth/front-most visibility 가능 여부
```

기본 알고리즘:

```txt
1. 2D lip mask를 screen space에 둔다.
2. ARFace triangle을 screen space로 rasterize한다.
3. mask pixel이 들어온 triangle을 찾는다.
4. barycentric interpolation으로 UV 좌표를 계산한다.
5. UV texture에 alpha/probability를 누적한다.
6. visibility/front-most 정보가 없으면 warning을 남긴다.
7. UV texture를 다시 screen으로 round-trip해서 위치를 확인한다.
```

완료 조건:

- UV mask가 생성된다.
- round-trip이 입술 위치로 돌아온다.
- 좌우/상하 뒤집힘이 없다.
- 턱/피부로 크게 밀리지 않는다.
- coordinate warning이 있으면 `partial`로 남긴다.

### 5.4 Blendshape Assist

Blendshape는 mask를 다시 만드는 기능이 아니다. 같은 UV mask를 쓰고 material/shader parameter만 작게 보정한다.

비교 모드:

```txt
UV Only
Blendshape Assist
```

초기 역할:

```txt
Generate 품질 판정:
- jawOpen이 높으면 neutral capture 경고
- mouthPucker가 높으면 pucker 상태 경고
- smile/stretch가 높으면 비대칭 상태 경고

Runtime Assist:
- jawOpen 높음: inner-mouth alpha/falloff 강화
- smileLeft/Right 높음: corner feather 또는 corner falloff 완화
- pucker/funnel 높음: coverage를 약간 줄임
```

금지:

- 매 프레임 2D boundary 재생성.
- 매 프레임 UV texture 재생성.
- 과한 geometry deformation.
- assist 때문에 FPS/frame-time이 눈에 띄게 악화되는 것.

### 5.5 Runtime HUD

기본 화면은 얼굴을 가리지 않는다.

```txt
Bottom Compare HUD:
- Provider
- Assist Off/On
- Generate
- Apply
- corner/upper/lower/y
- status

Tiny top status:
- generated/applied
- FPS or warning icon only

Full Debug:
- payload
- blendshape values
- mesh counts
- latency
- provider logs
```

얼굴 중앙 overlay/log는 최종 시각 판단 화면에서 금지한다.

## 6. 구현 단계

### Phase A. 계약과 fixture 고정

목표:

- shared contract 정의.
- fixture set 고정.
- Vision/MediaPipe/no-CV 경계 정책 확정.

산출물:

```txt
packages/lip-generate-core/contracts.ts
fixtures/lip-generate/*.json
fixtures/lip-generate/*.png
docs/runbooks/E7_LIP_GENERATE_EVIDENCE_RUNBOOK_KO.md
```

검증:

```txt
npm test 또는 node smoke
json schema check
fixture inventory check
```

### Phase B. 웹앱 베타

목표:

- 서비스 흐름을 React 웹앱에서 완주한다.
- 마스크 생성 로직을 반드시 실행한다.
- 2D->UV->round-trip을 시각 검증한다.

산출물:

```txt
web/lip-generate-beta/
web/lip-generate-beta/screenshots/
evidence/e7-lip-generate-web-beta/
```

검증:

```txt
Generate -> Inspect -> Compare -> Payload 흐름 완료
Vision fixture/local server mask 생성
MediaPipe browser/local server mask 생성
UV texture 생성
round-trip overlay 생성
```

### Phase C. 로컬 생성 서버

목표:

- 웹앱이 local HTTP로 실제 repo generator를 호출한다.
- 마스크 생성, UV projection, round-trip을 서버에서 재현한다.

권장 stack:

```txt
Node/Express 또는 Python/FastAPI
```

API:

```txt
POST /api/lip-mask/generate
POST /api/lip-mask/project-uv
POST /api/lip-mask/round-trip
GET /api/lip-mask/runs/:runId
```

privacy:

```txt
localOnly=true
offDeviceUpload=false
longTermRawFrameStored=false
```

### Phase D. RN 앱 UI

목표:

- 웹앱에서 검증한 흐름을 RN에 옮긴다.
- 얼굴을 가리지 않는 Compare HUD를 만든다.

필수 UI:

```txt
Provider segmented control: Vision / MediaPipe
Assist segmented control: Off / Assist
Generate button
Apply/Compare state
Adjustment controls
Clean / Compare HUD / Debug mode
```

검증:

```txt
tsc
lint
RN tests
payload snapshot tests
```

### Phase E. Unity dynamic mask runtime

목표:

- runtime Texture2D를 생성하고 shader/material에 적용한다.
- 같은 generated mask로 Assist Off/On을 비교한다.

필수 구현:

```txt
ApplyGeneratedLipMask payload parser
GeneratedLipMaskRegistry
ScreenMaskToUvProjector
DynamicLipMaskTexture
BlendshapeAssistController
E7 generated mask event logs
```

검증:

```txt
Unity batchmode import/compile
synthetic payload smoke
generated texture smoke
```

### Phase F. iOS provider

목표:

- Vision on-device provider를 먼저 연결한다.
- MediaPipe provider는 feasible path를 구현하거나 blocked evidence를 남긴다.

Vision 완료 조건:

```txt
current frame에서 lip contour 획득
same-frame ARFace snapshot과 묶임
generated UV mask 적용 가능
```

MediaPipe 완료 조건:

```txt
on-device inference 성공
lip landmarks 획득
generated UV mask 적용 가능
```

MediaPipe가 막히면:

```txt
status=blocked
blockedReason 기록
Vision path는 계속 진행
```

### Phase G. iPhone build and final loop

Build 전 질문:

```txt
Primary path:
- Vision on-device Generate -> UV mask -> runtime apply

Compare paths:
- MediaPipe Generate if available
- Blendshape Assist Off/On

Quality gate:
- boundary accuracy
- face attachment
- inner-mouth exclusion
- corner coverage
- expression stability
- FPS/frame-time
- latency
- memory/thermal if available

Out of scope:
- upload
- server product path
- Android
- commercial SDK
- product-ready claim without evidence
```

승인 후:

```txt
bash scripts/build_m3_unityframework.sh
cd rn/MakeupARValidation
npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK
```

## 7. 최종 테스트 시나리오

### 7.1 기본 생성

```txt
1. Clean 또는 Compare HUD 진입
2. Provider=Vision
3. Assist=Off
4. 입을 편하게 다물고 Generate
5. 적용 결과 확인
6. Assist=On으로 전환
7. 같은 mask에서 변화 확인
```

### 7.2 Provider 비교

```txt
1. Provider=Vision Generate
2. Provider=MediaPipe Generate
3. 같은 color/opacity/feather로 비교
4. 입꼬리, 윗입술 산, 아랫입술 아래 spill 확인
```

### 7.3 Expression 비교

```txt
1. neutral
2. open-close
3. smile
4. pucker
5. yaw left/right
```

각 시나리오에서 기록:

```txt
provider
assist mode
generatedMaskId
tracking state
mesh counts
blendshape available/key values
FPS/frame-time
recipe/generate latency
visual verdict
known weakness
```

### 7.4 사용자가 판단할 질문

```txt
- 입술 전체가 충분히 포함되는가?
- 입꼬리가 비지 않는가?
- 윗입술 산이 자연스러운가?
- 아랫입술 아래 피부로 번지지 않는가?
- 입 안쪽/치아를 칠하지 않는가?
- 얼굴 움직임에서 붙어 보이는가?
- Assist On이 실제로 더 좋은가, 아니면 불안정한가?
- Vision과 MediaPipe 중 어느 쪽이 더 제품답나?
```

## 8. 멀티 에이전트 실행 계획

### Agent 1. Contract/Gate

- shared request/result schema 작성.
- evidence gate matrix 작성.
- ready/partial/blocked 규칙 관리.
- TECH_VALIDATION_RESULT 업데이트 후보 작성.

### Agent 2. Web Beta UI

- React 웹앱 구현.
- Generate / Inspect / Compare / Payload 화면.
- 얼굴을 가리지 않는 UI.
- RN 상태 모델과 맞는 reducer 설계.

### Agent 3. Mask Generation Server

- local HTTP server 구현.
- fixture replay.
- Vision/MediaPipe helper 호출.
- raw frame long-term 저장 방지.

### Agent 4. Projection Core

- 2D mask -> UV texture.
- UV -> screen round-trip.
- coordinate/mirror/orientation diagnostics.
- web/unit fixture 검증.

### Agent 5. RN App

- Provider/Assist/Generate UI.
- Compare HUD.
- payload builder.
- test/lint/typecheck.

### Agent 6. Unity Runtime

- dynamic Texture2D.
- generated mask registry.
- shader/material apply.
- Blendshape Assist controller.
- runtime logs/events.

### Agent 7. iOS Providers

- Vision provider.
- MediaPipe feasibility path.
- same-frame snapshot contract.
- blocked evidence if MediaPipe cannot ship in this pass.

### Agent 8. QA/Evidence

- web beta evidence.
- buildless verification.
- build logs.
- runtime console capture.
- representative screenshots/frames.
- final G/Y/R recommendation.

## 9. 반복 루프

이 계획은 한 번에 끝났다고 말하지 않는다. 아래 루프를 목표 달성까지 반복한다.

### 9.1 Web loop

```txt
Implement
-> Generate mask
-> Project UV
-> Round-trip preview
-> Compare four modes
-> Fix contract/logic/UI
-> Repeat until web gate passes
```

Web gate가 실패하면 iPhone build로 가지 않는다.

### 9.2 Buildless app loop

```txt
RN tests
-> TypeScript
-> lint
-> Unity batchmode import/compile
-> synthetic payload smoke
-> generated texture smoke
-> Fix
-> Repeat
```

### 9.3 Device loop

```txt
Ask build approval
-> UnityFramework build/sync
-> RN iPhone install/launch
-> runtime console capture
-> user visual scenario
-> evidence summary
-> ready/partial/blocked decision
-> fix exact failing layer
-> repeat
```

### 9.4 Stop rules

Stop and report instead of guessing if:

```txt
- Provider returns no lip boundary.
- 2D->UV round-trip is visibly wrong.
- generated texture applies to wrong face area.
- runtime logs cover the face in Clean/Compare mode.
- MediaPipe requires large unplanned native/plugin integration.
- FPS/frame-time drops materially.
- raw frame would need long-term storage.
- upload/server product path becomes required.
```

### 9.5 사용자 도움 요청 규칙

Goal 실행 중 아래 상황이 나오면 계속 추측하지 말고 즉시 사용자에게 짧게 요청한다.

```txt
- 얼굴/입술 시각 판단이 필요한 contact sheet 또는 screenshot 선택.
- iPhone 잠금 해제, 카메라 권한, 기기 연결, 빌드 승인.
- Vision과 MediaPipe 중 주관적 경계 품질 선택.
- Blendshape Assist Off/On 중 제품 기본값 선택.
- pucker/smile/open-close/yaw 같은 추가 표정 캡처가 필요한 경우.
- evidence가 Yellow라서 계속 구현할지, 우회할지, scope를 줄일지 결정해야 하는 경우.
```

## 10. 완료 조건

완료는 아래가 모두 만족될 때만 말한다.

```txt
- 웹앱에서 Vision/MediaPipe mask 생성 검증.
- 웹앱에서 2D->UV->round-trip 검증.
- 웹앱에서 Provider x Assist 4조합 비교 가능.
- 로컬 개인화 모델 산출물 패키지가 생성/저장/재적용 가능.
- RN 앱에 같은 사용자 흐름 구현.
- Unity runtime에서 generated UV mask dynamic apply.
- Vision on-device Generate 성공.
- MediaPipe는 성공 또는 명확한 blocked evidence.
- Blendshape Assist Off/On 비교 가능.
- 얼굴을 가리지 않는 runtime HUD.
- iPhone에서 neutral/open-close/smile/pucker/yaw evidence.
- FPS/frame-time/latency/log evidence.
- TECH_VALIDATION_RESULT에 결정, evidence, limitations, next boundary 기록.
```

완료가 아닌 경우:

```txt
- 웹앱 UI만 있고 mask 생성이 없는 경우.
- 정적 baked mask 선택만 하는 경우.
- round-trip 없이 UV 생성만 주장하는 경우.
- Vision만 성공했는데 MediaPipe 상태를 기록하지 않는 경우.
- Assist가 켜져 있지만 실제 payload/runtime 차이가 없는 경우.
- 얼굴 중앙을 로그/HUD가 가려서 시각 판단이 어려운 경우.
- 실기기 visual/runtime evidence 없이 ready를 주장하는 경우.
```

## 11. 최종 판단 기준

최종 보고는 아래 형식으로 한다.

```txt
Vision + UV Only: Green / Yellow / Red
Vision + Blendshape Assist: Green / Yellow / Red
MediaPipe + UV Only: Green / Yellow / Red / Blocked
MediaPipe + Blendshape Assist: Green / Yellow / Red / Blocked
```

그리고 제품 판단은 별도로 적는다.

```txt
Recommended default provider:
Recommended assist default:
Required retake guidance:
Known failure modes:
Next required work:
```

## 12. 현재 보수적 추천

초기 제품 기본값은 아래가 가장 현실적이다.

```txt
Default provider: Vision
Default assist: Off
Advanced compare: MediaPipe, Blendshape Assist
Default capture: neutral one-shot
Precision capture: open-close / smile / pucker / yaw only when needed
Runtime: generated UV mask reuse, no per-frame AI
```

이 추천은 구현 전 가정이다. 최종 default는 웹앱 gate와 iPhone runtime evidence로 다시 결정한다.
