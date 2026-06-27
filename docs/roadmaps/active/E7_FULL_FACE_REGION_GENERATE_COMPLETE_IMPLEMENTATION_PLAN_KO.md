# E7 Full Face Region Generate 완전 구현 계획

작성일: 2026-06-27 KST

## 0. 결정

이번 작업의 목표는 립 단일 후보 실험을 넘어, **립 / 블러셔 / 눈썹 / 아이라인 region을 생성, 조정, 저장하고 Xcode 빌드 직전까지 RN/Unity 적용 준비를 끝내는 완성품 수준의 pre-Xcode 구현**이다.

핵심 제품 흐름:

```txt
사용자가 맞춤 생성 시작
-> 얼굴 정렬과 n회 촬영으로 현재 사용자 capture set 생성
-> native Vision / native MediaPipe가 현재 촬영 frame에서 boundary 후보 추출
-> 현재 얼굴 기준으로 립 / 블러셔 / 눈썹 / 아이라인 region mask 후보 생성
-> 부위별로 가장 흔한 실패를 직접 조정
-> 조정된 마스크 패키지 저장
-> 저장된 마스크를 AR 화면에서 소비할 수 있는 package/payload로 고정
-> RN/Unity는 저장된 package를 AR 진입 시 적용할 준비를 완료
-> 실제 iPhone/Xcode 빌드와 실기기 검증은 기기 연결 후 별도 gate에서 진행
```

이번 계획은 기존 `E7_LIP_PERSONALIZED_GENERATE_FULL_IMPLEMENTATION_PLAN_KO.md`를 확장한 현재 active 계약이다. 립에서 얻은 인사이트를 전체 부위에 일반화한다.

가장 중요한 원칙:

```txt
자동 생성만으로 끝내지 않는다.
자동 생성 + 가장 자주 틀리는 지점만 제품 UI에서 직접 조정하게 만든다.
저장된 mask package를 AR runtime이 안정적으로 소비할 수 있게 만든다.
이번 세션에서는 iPhone을 연결하지 않으므로 Xcode 빌드, 설치, 런타임 실기기 검증은 실행하지 않는다.
```

## 1. 완료 정의

이 계획에서 "완료"는 아래가 모두 끝난 상태다.

```txt
1. 립 / 블러셔 / 눈썹 / 아이라인 후보 생성 실험 완료
2. 외부 mask prior, MediaPipe/Vision, face parsing, color confidence, ARFace UV 신호 역할 정리
3. 부위별 selected policy와 top candidate set 기록
4. 부위별 사용자 조정축 3-7개 확정
5. 웹앱에서 실제 iPhone 앱 패널/wizard UI shell을 기능 없는 껍데기로 먼저 확인
6. 기존 웹앱 방식으로 Generate -> Review/Adjust -> Save -> Payload 실제 로직 검증
7. RN 앱 기본 진입면이 옛 validation HUD가 아니라 강제 단계형 wizard가 되도록 구현
8. Unity가 현재 얼굴 촬영 package를 만들 수 있도록 구현
9. native iOS Vision provider와 native iOS MediaPipe provider가 현재 촬영 frame에서 boundary를 추출하도록 구현
10. n회 촬영 capture set과 blendshape assist off/on 비교 흐름 구현
11. RN 앱에서 저장된 region package를 읽고 AR 화면으로 넘기는 흐름 구현
12. Unity runtime이 저장된 UV mask texture를 부위별로 적용할 수 있도록 구현
13. Xcode 빌드 직전 상태까지 정적/빌드리스 검증 완료
14. iPhone 연결 후 실행할 build/run/test checklist와 evidence matrix 준비
15. synthetic package smoke, Unity import/compile, RN test/typecheck/lint, native provider static checks, runtime log analyzer smoke 기록
16. TECH_VALIDATION_RESULT.md에 결정, evidence, limitations, next boundary 기록
```

완료가 아닌 경우:

```txt
- 웹 UI만 있고 실제 mask 생성이 없는 경우
- 외부 mask prior만 만들고 우리 app frame / ARFace UV로 투영하지 않은 경우
- 저장된 package 없이 임시 asset만 바꾼 경우
- 한두 부위만 성공했는데 전체 완료라고 말하는 경우
- 현재 얼굴 촬영 없이 fixture/synthetic payload만 앱 Generate로 보여주는 경우
- native Vision/MediaPipe provider가 placeholder인데 구현 완료라고 말하는 경우
- 앱 기본 UI가 옛 validation HUD/버튼 패널 그대로 남아 있는 경우
- 사용자가 전 단계를 밟지 않아도 임의 단계로 건너뛸 수 있는 경우
- blendshape assist가 UI 토글만 있고 payload/material/runtime 차이를 만들지 못하는 경우
- iPhone runtime evidence 없이 product-quality ready를 주장하는 경우
- Xcode 빌드 직전 검증만 해놓고 실기기 Green이라고 주장하는 경우
- 사용자 판단이 필요한 visual choice를 auto success로 처리한 경우
```

부분 실패는 숨기지 않는다. 네 부위 중 하나라도 남으면 아래처럼 기록한다.

```txt
lip: pre-xcode-ready / partial / blocked
blush: pre-xcode-ready / partial / blocked
brow: pre-xcode-ready / partial / blocked
eyeliner: pre-xcode-ready / partial / blocked
```

이번 iPhone 미연결 세션의 최대 판정은 `pre-xcode-ready`다. `Green`은 실제 iPhone evidence가 생긴 뒤에만 선언한다.

## 2. 사용자 시나리오

### 2.1 첫 사용자 흐름

사용자는 기술 provider를 이해할 필요가 없다.

```txt
1. 앱 진입
2. 맞춤 메이크업 생성 시작
3. 얼굴 정렬
   - 정면
   - 얼굴 거리
   - 밝기
   - 흔들림
4. n회 촬영
   - neutral
   - mouth open/closed
   - smile
   - pucker
   - yaw left/right
5. 앱이 현재 촬영 frame에서 native Vision / MediaPipe boundary를 추출한다
6. 앱이 현재 얼굴에서 4개 region mask 후보를 만든다
   - 립
   - 블러셔
   - 눈썹
   - 아이라인
7. 후보가 화면에 보인다
8. 사용자는 Vision/off, Vision/blend, MediaPipe/off, MediaPipe/blend를 비교한다
9. 가장 흔한 문제를 빠르게 조정한다
10. 저장
11. 저장된 mask package를 AR 화면 진입 payload로 고정
12. iPhone 연결 후 AR 화면에서 메이크업 look 적용
13. smile / open mouth / blink / yaw로 확인
14. 마음에 들면 유지
15. 마음에 안 들면 조정 화면으로 돌아가기
```

### 2.2 제품 화면 용어

제품 UI에는 내부 기술명을 노출하지 않는다.

```txt
맞춤 생성
저장
다시 생성
립
블러셔
눈썹
아이라인
위치
범위
두께
부드러움
강도
좌우 맞춤
입꼬리
눈꼬리
```

내부 debug 용어는 Debug 모드와 evidence에만 남긴다.

```txt
Provider: Vision / MediaPipe / ExternalPrior / Hybrid
Signal: ARFaceUV / faceParsing / colorConfidence / externalMaskPrior
Status: pre-xcode-ready / partial / blocked
Lineage: source, candidateId, selectedPolicy, warning
```

### 2.3 조정 화면

조정은 슬라이더와 버튼 조합으로 만든다.

버튼은 사용자가 바로 이해하는 빠른 수정이다.

```txt
조금 위로
조금 아래로
더 넓게
더 좁게
더 부드럽게
더 선명하게
왼쪽 맞춤
오른쪽 맞춤
```

슬라이더는 세밀 조정이다.

```txt
위치
범위
두께
부드러움
강도
좌우 밸런스
```

### 2.4 2026-06-27 사용자 흐름 재검토 결론

이번 재검토의 결론은 기존 "하단 탭/페이지네이션 HUD" 가정이 제품 흐름과 맞지 않는다는 것이다. 앱은 사용자가 아무 탭이나 눌러 다른 화면으로 이동하는 구조가 아니라, 반드시 이전 단계를 통과해야 다음 단계가 열리는 단계형 흐름이어야 한다.

현실성 판단:

```txt
방향은 맞다.
다만 단순 UI 교체가 아니라 capture -> native extraction -> UV projection -> save -> runtime apply까지 이어지는 제품 slice다.
따라서 다음 iPhone/Xcode 빌드 전에 웹 shell, RN wizard, Unity capture, native Vision/MediaPipe provider, save package, blend off/on 비교가 모두 build-ready 상태여야 한다.
Xcode 빌드 전에는 실기기 증거를 주장하지 않는다.
하지만 코드/계약/정적 검증 관점에서는 "이제 Xcode build만 남았다"라고 말할 수 있을 만큼 준비한다.
```

핵심 보정:

```txt
1. 웹앱에는 앱 UI shell preview와 실제 mask logic beta를 분리한다.
2. 앱은 강제 wizard다. 탭 전환형 페이지네이션이 아니다.
3. 첫 실사용 단계는 Generate가 아니라 촬영이다.
4. native Vision/MediaPipe는 fixture가 아니라 현재 촬영 frame에서 실행한다.
5. n회 촬영과 blendshape assist는 후보 비교의 1급 기능이다.
6. Debug/log는 얼굴 중앙을 가리지 않는 별도 sheet/drawer로 격리한다.
7. 옛 validation HUD는 기본 제품 흐름에서 제거하고 dev/debug 진입으로만 남긴다.
```

### 2.5 강제 단계형 App Flow

앱 기본 흐름은 아래 순서만 허용한다. 사용자는 뒤로가기/재촬영은 가능하지만, 이전 gate가 통과되지 않은 다음 단계로 직접 건너뛰면 안 된다.

```txt
Step 0. 시작 / 권한 / 로컬 처리 안내
  gate: camera permission, AR support, local-only privacy notice accepted

Step 1. 얼굴 정렬
  gate: face tracked, front camera active, face centered, distance/brightness/blur/yaw acceptable

Step 2. n회 촬영
  gate: required capture shots collected or explicitly marked blocked
  required validation shots: neutral, mouth-open, mouth-closed, smile, pucker, yaw-left, yaw-right
  optional/region shots: blink, squint, brow raise, cheek smile

Step 3. native boundary 추출
  gate: Vision result and MediaPipe result both produced or one provider has concrete blockedReason

Step 4. 후보 생성
  gate: 2D mask, UV mask, round-trip preview, package metadata produced

Step 5. 후보 비교
  gate: Vision/off, Vision/blend, MediaPipe/off, MediaPipe/blend 비교 가능

Step 6. 미세 조정
  gate: adjustment values change 2D mask, UV texture, round-trip, runtime payload

Step 7. 저장
  gate: stale result cannot save; saved package contains privacy/source/blend/adjustment metadata

Step 8. AR 적용 준비
  gate: Unity can parse saved package, register texture, apply generated mask path in smoke

Step 9. Debug/evidence
  gate: logs are available without covering the face judgment area
```

### 2.6 Capture Bundle Contract

촬영 없이 맞춤 생성은 불가능하다. 앱의 Generate는 반드시 현재 얼굴에서 생성된 capture bundle을 입력으로 사용한다.

```ts
type E7CaptureShotKind =
  | "neutral"
  | "mouthOpen"
  | "mouthClosed"
  | "smile"
  | "pucker"
  | "yawLeft"
  | "yawRight"
  | "blink"
  | "squint"
  | "browRaise";

type E7CaptureShot = {
  shotId: string;
  captureSetId: string;
  shotKind: E7CaptureShotKind;
  localFramePath: string;
  frameWidth: number;
  frameHeight: number;
  orientation: "portrait" | "landscapeLeft" | "landscapeRight";
  isMirrored: boolean;
  arfaceExportPath: string;
  meshVertexCount: number;
  meshIndexCount: number;
  meshUvCount: number;
  blendshapeValues: Record<string, number>;
  quality: {
    faceTracked: boolean;
    faceCentered: boolean;
    brightnessOk: boolean;
    blurOk: boolean;
    distanceOk: boolean;
    yawOk: boolean;
    pitchOk: boolean;
    mouthStateOk: boolean;
  };
  privacy: {
    localOnly: true;
    offDeviceUpload: false;
    longTermRawFrameStored: false;
  };
};

type E7CaptureSet = {
  captureSetId: string;
  createdAtLocal: string;
  shots: E7CaptureShot[];
  requiredShotStatus: Record<string, "ready" | "blocked" | "retakeRequired">;
  selectedReferenceShotId: string;
};
```

보관 원칙:

```txt
raw camera frame은 장기 저장하지 않는다.
build/debug 중 필요한 local temp만 사용하고, 저장 package에는 필요한 파생 mask/metadata만 남긴다.
evidence로 남길 때는 representative frame/contact sheet/metadata 중심으로 남긴다.
```

## 3. 범위

### 3.1 포함

- CLI 기반 반복 실험.
- 앱 UI shell preview를 웹에서 먼저 확인하는 단계.
- Unity AR 세션에서 현재 frame + ARFace mesh/UV + blendshape를 묶어 capture bundle 생성.
- n회 촬영 flow와 shot별 품질 gate.
- native iOS Vision provider.
- native iOS MediaPipe provider.
- 외부 마스킹 데이터 기반 silver prior 확보/정규화/warping.
- 기존 evidence와 local capture pair 재사용.
- MediaPipe, Apple Vision, face parsing, color/gradient confidence, ARFace UV 신호 비교.
- 립 / 블러셔 / 눈썹 / 아이라인 후보 생성.
- 부위별 tight / balanced / safe 후보 생성.
- include / exclude / unknown map 생성.
- contact sheet, scorecard, selected policy 생성.
- 웹앱 UI/로직/payload 검증.
- 로컬 서버 또는 local-only helper.
- 저장 가능한 region mask package.
- RN 앱의 저장 package import와 AR 화면 전환 준비.
- Unity runtime UV mask 적용 준비와 synthetic smoke.
- blendshape assist off/on 비교와 runtime payload 차이 확인.
- 얼굴 중앙을 가리지 않는 debug/evidence sheet.
- Xcode 빌드 직전 checklist/evidence matrix/package readiness.
- Slack user-required alert.
- TECH_VALIDATION_RESULT.md 업데이트.

### 3.2 제외

- 서버 업로드 기반 제품 흐름.
- raw camera frame 장기 저장.
- commercial SDK 도입.
- Android.
- live face parsing/Core ML runtime.
- 화장 AR runtime 매 프레임 Vision/MediaPipe/face parsing으로 boundary 재생성.
- RN이 Unity ARKit session과 별도 camera session을 동시에 열어 충돌시키는 구조.
- fixture/replay 결과를 현재 사용자 촬영 Generate처럼 표시하는 구조.
- web shell만 만들고 실제 native provider/app capture를 생략하는 구조.
- 외부 dataset asset을 product source나 Unity Resources에 직접 복사.
- iPhone evidence 없이 product-quality ready 선언.
- 이번 세션의 Xcode/iPhone build/install/launch.
- 이번 세션의 iPhone 잠금 해제, 카메라 권한, 실기기 runtime test.

## 4. 핵심 아키텍처

### 4.1 전체 구조

```txt
Region Experiment CLI
  -> external prior build
  -> provider candidate generation
  -> face parsing / color confidence checks
  -> scorecard / contact sheet / selected policy

Region Generate Web Beta
  -> selected policy preview
  -> Generate / Adjust / Save UX
  -> package and payload verification

React Native App
  -> saved package import
  -> calibration/review screen
  -> AR screen transition
  -> Unity message contract

Unity Runtime
  -> generated UV mask registry
  -> per-region mask texture apply
  -> makeup material/shader layer
  -> runtime metrics and event logs

Pre-Xcode Build Package
  -> build checklist
  -> deferred iPhone test matrix
  -> pre-xcode-ready / partial / blocked
  -> result doc update
```

### 4.1.1 Capture-First App Architecture

제품 앱에서는 RN이 직접 별도 camera session을 열지 않는다. Unity가 이미 ARKit/AR Foundation 세션을 소유하므로, 촬영도 Unity가 현재 AR session에서 수행하고 RN은 단계 흐름과 상태를 관리한다.

```txt
RN Wizard
  -> Unity에 StartCaptureStep 요청
  -> Unity가 현재 camera frame + ARFace mesh/UV/screen projection + blendshape 저장
  -> Unity가 capture metadata event를 RN에 전달
  -> RN/native bridge가 Vision provider와 MediaPipe provider 실행
  -> provider 결과가 2D boundary contract로 정규화
  -> Unity 또는 shared local tool이 2D mask -> UV mask -> round-trip 생성
  -> RN이 후보 비교/조정/저장 UI 표시
  -> Unity runtime이 saved UV mask를 계속 샘플링
```

이 구조의 이유:

```txt
같은 순간의 camera frame과 ARFace mesh를 묶을 수 있다.
RN camera와 Unity ARKit session 충돌을 피한다.
서버/fixture가 아니라 현재 사용자 얼굴에서 생성한다.
runtime 매 프레임 AI가 아니라 calibration-time generation으로 성능과 privacy를 지킨다.
```

### 4.2 신호 역할

| Signal | 역할 | 금지 |
| --- | --- | --- |
| ARFace mesh/UV | runtime 좌표계, 2D mask -> UV projection, 얼굴 부착 | semantic boundary 자체로 과신 금지 |
| Apple Vision | native iOS current-frame 2D contour / landmark provider, sanity signal | gold mask 또는 runtime primary tracker 취급 금지 |
| MediaPipe | native iOS current-frame geometry/landmark provider, comparison signal | fixture/replay 또는 Codex shell-only 결과를 앱 구현 완료로 취급 금지 |
| Face parsing | local/offline silver semantic layer, spill/exclude 판단 | live runtime/Core ML로 승격 금지 |
| Color/gradient | confidence, contrast, hair/skin/lip edge, visibility/spill warning | boundary 생성 신호로 단독 사용 금지 |
| External mask prior | gold 없는 부위의 silver draft 생성 | 직접 gold 또는 product asset 취급 금지 |
| User adjustment | subjective boundary를 닫는 최종 correction | 조정 없이 자동 success 주장 금지 |

### 4.3 저장 package

저장되는 단위는 단순 PNG가 아니라 traceable package다.

```ts
type RegionKind = "lip" | "blush" | "brow" | "eyeliner";

type RegionGenerateStatus = "preXcodeReady" | "partial" | "blocked";

type RegionSignalSource =
  | "appleVision"
  | "mediapipe"
  | "faceParsing"
  | "colorConfidence"
  | "externalMaskPrior"
  | "arfaceUv"
  | "userAdjustment"
  | "hybrid";

type RegionMaskPackage = {
  schemaVersion: "e7-region-mask-package-v0";
  packageId: string;
  region: RegionKind;
  status: RegionGenerateStatus;
  selectedPolicy: string;
  sourceLineage: {
    sources: RegionSignalSource[];
    candidateIds: string[];
    externalPrior?: {
      sourceName: string;
      role: "silver_draft_only";
      licenseNote: string;
    };
  };
  sourceFrameMetadata: {
    capturePairId?: string;
    captureSetId?: string;
    referenceShotId?: string;
    frameWidth: number;
    frameHeight: number;
    orientation: string;
    isMirrored: boolean;
  };
  providerResults?: {
    vision?: {
      status: "ready" | "partial" | "blocked";
      boundaryPath?: string;
      confidence?: number;
      blockedReason?: string;
    };
    mediapipe?: {
      status: "ready" | "partial" | "blocked";
      boundaryPath?: string;
      confidence?: number;
      blockedReason?: string;
    };
  };
  mask2d: {
    hardMaskPath: string;
    softAlphaPath: string;
    includeMapPath?: string;
    excludeMapPath?: string;
    unknownMapPath?: string;
  };
  uvMask: {
    texturePath: string;
    resolution: number;
    roundTripOverlayPath: string;
    roundTripStatus: "ready" | "partial" | "blocked";
  };
  adjustment: Record<string, number>;
  blendshapeAssist: {
    enabled: boolean;
    captureShotIds: string[];
    assistMode: "off" | "calibrationEnvelope" | "runtimeMaterialAssist";
    runtimeBlendshapeFields: string[];
  };
  qualityWarnings: string[];
  runtimeApplyPayload: {
    region: RegionKind;
    maskTextureId: string;
    threshold: number;
    feather: number;
    opacity: number;
    runtimeReady: boolean;
  };
  privacy: {
    localOnly: true;
    offDeviceUpload: false;
    longTermRawFrameStored: false;
  };
};
```

전체 저장 bundle:

```txt
e7-saved-makeup-package-v0
  lip.package.json
  blush.package.json
  brow.package.json
  eyeliner.package.json
  composite_apply_payload.json
  review_summary.md
```

## 5. Gold 없는 상황의 평가 전략

### 5.1 기본 원칙

Gold mask가 없는 부위는 `pre-xcode-ready`를 바로 주장하지 않는다.

```txt
single signal winner 금지
multi-signal agreement 사용
불확실한 경계는 unknown으로 남김
external mask는 silver only
human/user review 전에는 provisional
```

### 5.2 Include / Exclude / Unknown

각 부위 후보는 세 개의 map을 만든다.

```txt
include: 여러 신호가 "이 부위가 맞다"고 합의한 영역
exclude: 절대 칠하면 안 되는 영역
unknown: 신호가 갈리거나 판단이 부족한 영역
```

예:

```txt
립 include: Vision/MediaPipe lip contour + face parsing upper/lower lip 합의
립 exclude: inner mouth, teeth, skin spill

블러셔 include: cheekbone/apple soft oval
블러셔 exclude: eye, nose, lip, jaw, hair

눈썹 include: brow parsing/landmark/color contrast 합의
눈썹 exclude: eye opening, eyelid makeup area, forehead overreach

아이라인 include: upper/lower eyelid curve 근처 stroke
아이라인 exclude: eyeball, broad eyeshadow area, brow
```

### 5.3 외부 마스크 우회법

외부 마스크는 mesh가 달라서 직접 사용하지 않는다. 대신 normalized prior로 변환한다.

```txt
외부 image + external mask
-> landmark 기준 정규화
-> canonical face space에 region probability 누적
-> 우리 app frame에 warp
-> silver draft 생성
-> face parsing / color confidence / MediaPipe / Vision으로 보정
-> ARFace UV projection
```

외부 source 기대값:

| Source | 용도 |
| --- | --- |
| CelebAMask-HQ | lip, eye, eyebrow, skin label prior |
| LaPa | lip, eye, landmark-normalized prior |
| BiSeNet/SegFace | local/offline face parsing helper |
| MediaPipe | face normalization, landmarks, geometry comparison |

주의:

```txt
외부 mask = gold 아님
외부 mask로 만든 draft = silver
우리 clean frame 위에서 human/user review 또는 강한 다중 신호 합의 필요
```

### 5.4 Scoring

Gold가 없는 부위는 absolute score가 아니라 risk score로 평가한다.

```txt
signalAgreement
negativeSpill
unknownBoundaryRatio
symmetry
roundTripQuality
faceLocalPlausibility
adjustability
runtimeRisk
```

Candidate decision:

```txt
tight: conservative, spill 최소화
balanced: coverage와 spill 균형
safe: makeup visibility를 위해 조금 넓지만 exclude 존 보호
```

## 6. 부위별 계획

### 6.1 Lip

현재 상태:

- 립은 가장 앞서 있다.
- Apple Vision, face parsing, color confidence, user adjustment, MediaPipe evaluation 경험이 있다.
- 사용자 조정 인사이트가 이미 있다.

Primary hypothesis:

```txt
Vision/MediaPipe/face parsing/color confidence hybrid
-> user adjustment
-> ARFace UV projection
-> runtime UV mask sampling
```

사용자 조정축:

```txt
cornerReach
upperLipTightness
lowerLipTightness
verticalOffset
innerMouthGuard
edgeFeather
coverage
```

주요 실패:

```txt
입꼬리 비어 있음
아랫입술 아래 피부 spill
윗입술 산 부정확
높낮이 불만족
inner mouth/teeth 침범
pucker/smile/open-mouth에서 어색함
```

완료 조건:

```txt
selected lip package 저장
UV round-trip 통과
AR runtime에서 saved mask를 적용할 parser/payload 준비
neutral/smile/open/pucker/yaw deferred test checklist 준비
사용자 조정값이 payload와 visual에 반영
```

### 6.2 Blush

Primary hypothesis:

```txt
ARFace cheek UV/vertex soft zone
+ external/landmark cheek prior
+ face parsing exclude zones
+ color/skin-tone visibility confidence
-> soft UV mask
```

블러셔는 anatomical boundary가 아니라 cosmetic placement다. dataset에 `blush` class가 없으므로 landmark soft oval이 primary다.

사용자 조정축:

```txt
centerX
centerY
size
angle
noseGuard
underEyeGuard
mouthCornerGuard
feather
intensity
```

주요 실패:

```txt
너무 낮음
너무 높음
코 쪽 침범
눈 밑 침범
입꼬리 근처 침범
범위가 너무 넓거나 너무 약함
좌우 비대칭
```

완료 조건:

```txt
soft oval prior 생성
exclude zone 적용
UV projection
smile/yaw/pitch deferred test checklist와 round-trip preview 준비
natural blush visibility 확인
```

### 6.3 Brow

Primary hypothesis:

```txt
external eyebrow parsing prior
+ MediaPipe/Vision brow landmarks
+ color/hair-skin contrast
+ symmetry model
-> brow mask / brow stroke envelope
-> ARFace UV projection
```

눈썹은 사람마다 형태가 다르므로 자동 생성 후 직접 조정이 중요하다.

사용자 조정축:

```txt
headPosition
archHeight
tailLength
tailAngle
thickness
verticalOffset
leftRightBalance
softness
```

주요 실패:

```txt
앞머리 위치 틀림
눈썹산 위치 틀림
꼬리 짧음/김
두께 과함
좌우 비대칭
피부/머리카락과 혼동
```

완료 조건:

```txt
brow prior/draft 생성
hair/skin color confidence 기록
좌우 symmetry score 기록
사용자 조정 UI와 payload 연결
AR runtime에서 눈썹 region을 적용할 package/apply path 준비
```

### 6.4 Eyeliner

Primary hypothesis:

```txt
MediaPipe/Vision eye contour
+ eyelid landmark curve
+ color/edge confidence
+ blink/eye blendshape assist
-> parametric stroke mask
-> ARFace UV projection
```

아이라인은 가장 높은 리스크다. 면 마스크가 아니라 얇은 선이므로 작은 오차가 크게 보인다.
하지만 어렵다는 이유로 제외하지 않는다. 일반 경로가 실패하면 외부 reference 사진, 눈매 landmark, parametric lash-line curve, soft lashline emphasis, conservative tail-only candidate를 반복해서라도 최소 1개 이상의 사용 가능한 후보를 만든다.

사용자 조정축:

```txt
upperLineOffset
lineThickness
tailLength
tailAngle
outerCornerReach
innerCornerStart
softness
blinkFade
```

주요 실패:

```txt
눈꼬리 위치 틀림
라인이 두꺼움
eyeball/eye opening 침범
눈두덩이로 올라감
blink에서 튐
좌우 비대칭
```

완료 조건:

```txt
parametric eyeliner curve 생성
eye opening exclude zone 적용
blink/squint risk warning 기록
UV projection
blink/yaw deferred test checklist 준비
최소 tight / balanced / safe 또는 minimal-safe candidate 1개 이상 생성
```

## 7. 구현 단계

### Phase 0. Session Boot and Contract Lock

목표:

- 새 active plan을 기준 계약으로 고정.
- 이전 lip-only 계획은 archive로 유지.
- 실험 output root와 시간표 생성.

산출물:

```txt
docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md
evidence/e7-region-generate/session-YYYYMMDDTHHMMSSZ/session_manifest.json
evidence/e7-region-generate/session-YYYYMMDDTHHMMSSZ/timeline.md
```

### Phase 1. 2시간 실험 루프

목표:

- 웹앱이 아니라 CLI/local script에서 후보 생성과 비교를 반복.
- 네 부위 모두 top candidate set과 조정축을 만든다.

작업:

```txt
1. 기존 app clean frame과 arface_export inventory 확인
2. 외부 prior source review
3. small external sample 또는 existing parsing output 확보
4. 부위별 signal candidates 생성
5. include/exclude/unknown maps 생성
6. 2D -> UV -> round-trip
7. contact sheet 생성
8. scorecard 생성
9. selected policy provisional 기록
10. adjustment axes 확정
```

반복 규칙:

```txt
candidate generate
-> score
-> visual contact sheet
-> reject or refine
-> package
-> next region
```

2시간 종료 기준:

```txt
네 부위 모두 최소 tight/balanced/safe 후보 존재
각 후보의 missing signal과 limitation 기록
각 부위의 사용자 조정축 존재
```

### Phase 2. 웹 UI Shell + 기능 Beta 분리

목표:

- 웹앱에서 먼저 실제 iPhone 앱 패널/wizard 껍데기를 본다.
- 이 shell은 기능 없는 화면 계약이며, 사용자가 UI 흐름을 승인하는 기준이다.
- 실제 mask 생성/조정/저장 로직은 기존 web beta/local server 방식을 참고해 별도 functional beta로 검증한다.
- shell approval 없이 RN 앱 UI 구현을 진행하지 않는다.

필수 shell 화면:

```txt
App Shell / Step 0
  - 시작 / 권한 / 로컬 처리 안내

App Shell / Step 1
  - 얼굴 정렬 guide
  - 품질 gate status

App Shell / Step 2
  - n회 촬영 progress
  - neutral/open/closed/smile/pucker/yaw shot checklist
  - retake state

App Shell / Step 3
  - native Vision / native MediaPipe 추출 진행 상태

App Shell / Step 4
  - 후보 생성 결과
  - Vision/off, Vision/blend, MediaPipe/off, MediaPipe/blend

App Shell / Step 5
  - 후보 크게 보기
  - next/previous 후보 전환
  - region enable/disable

App Shell / Step 6
  - 미세 조정
  - stale result warning
  - regenerate required state

App Shell / Step 7
  - 저장
  - saved package summary
  - privacy flags

App Shell / Step 8
  - AR 적용 준비
  - debug/evidence sheet는 얼굴 중앙 밖
```

완료 조건:

```txt
web shell에서 강제 단계 흐름을 시각적으로 확인 가능
shell은 기능 없는 UI 계약임을 명시
functional beta에서 package load/generate/review/adjust/save 가능
functional beta가 fixture/prebuilt copy가 아니라 생성 path를 호출함을 smoke로 확인
payload JSON preview 가능
얼굴 중앙을 가리는 debug UI 없음
사용자가 승인하기 전 RN UI 이식 금지
```

### Phase 3. RN App Integration

목표:

- 웹 shell에서 승인된 화면 구조를 RN 앱에 옮긴다.
- functional web beta에서 검증한 생성/조정/저장 contract를 RN 앱에 연결한다.
- RN 기본 진입면에서 옛 validation HUD를 제거하고, debug/dev mode로만 격리한다.
- 저장 package를 AR 화면으로 넘긴다.

필수 UI:

```txt
Forced Wizard
  - Step 0 Start / Permission / Privacy
  - Step 1 Face Alignment
  - Step 2 Capture Shots
  - Step 3 Native Extraction
  - Step 4 Generate Candidates
  - Step 5 Compare Candidates
  - Step 6 Adjust
  - Step 7 Save Package
  - Step 8 Enter AR / Runtime Check

Navigation
  - Next is disabled until current gate passes
  - Back and Retake are allowed
  - arbitrary tab jump is not allowed
  - debug drawer does not cover face center

AR screen
  - Clean visual mode
  - compact compare controls
  - debug sheet/drawer
  - Return to Adjust
```

필수 contract:

```txt
StartCaptureStep
CaptureShotCompleted
CaptureSetReady
RunNativeVisionBoundary
RunNativeMediaPipeBoundary
GenerateCandidatePackage
ApplySavedRegionPackage
ApplyCompositeMakeupPackage
RegionPackageSaved
RegionPackageApplied
RegionPackageRejected
```

검증:

```txt
npm test -- --runInBand --watchman=false
./node_modules/.bin/tsc --noEmit
npm run lint
payload snapshot tests
```

### Phase 3A. Unity Capture + Native Provider Integration

목표:

- 앱 Generate의 입력을 fixture가 아니라 현재 촬영 capture set으로 바꾼다.
- native Vision과 native MediaPipe를 둘 다 구현한다.
- Xcode build 전에는 실기기 증거를 주장하지 않지만, iOS native module 파일/bridge/model/resource/contract가 build-ready 상태여야 한다.

Unity capture 필수 구현:

```txt
StartCaptureStep(stepKind)
current camera frame local temp write
same-moment ARFace mesh/indices/uv/screen projection export
ARKit blendshape values export
quality metrics export
CaptureShotCompleted RN event
CaptureSetReady RN event
raw frame cleanup policy
```

native Vision provider:

```txt
입력: localFramePath, orientation, isMirrored, face bounding metadata
처리: VNDetectFaceLandmarksRequest 또는 동등한 iOS Vision face landmark request
출력: lip/eye/brow contour points, confidence, coordinate transform metadata, warnings
금지: precomputed fixture contour를 현재 촬영 결과처럼 반환
```

native MediaPipe provider:

```txt
입력: localFramePath, orientation, isMirrored
처리: bundled local MediaPipe Tasks FaceLandmarker model 또는 iOS native MediaPipe equivalent
출력: face landmarks, lip/eye/brow point groups, confidence, coordinate transform metadata, warnings
금지: 서버 호출, 외부 업로드, fixture points replay
```

Provider 비교:

```txt
Vision/off
Vision/blend
MediaPipe/off
MediaPipe/blend
```

완료 조건:

```txt
native module bridge가 RN에서 호출 가능한 contract로 연결
provider 결과가 shared boundary schema로 정규화
blockedReason 없이 build-ready로 남기려면 local model/resource path와 initialization contract가 문서화
static checks와 snapshot/smoke가 provider placeholder를 감지
Xcode build만 남은 상태인지 Strict QA가 확인
```

### Phase 4. Unity Runtime Integration

목표:

- 저장된 UV mask texture를 Unity runtime에서 부위별로 적용.
- 기존 smooth-region-mask 구조를 generated package로 대체 또는 확장.

필수 구현:

```txt
GeneratedRegionMaskRegistry
CaptureBundleExporter
ApplySavedRegionPackage parser
CompositeMakeupPackage parser
DynamicRegionMaskTexture loader
2D boundary -> 2D mask -> UV mask projection entrypoint
Region material/shader parameter binding
Blendshape assist hooks
Runtime event logging
```

필수 runtime fields:

```txt
packageId
region
maskTextureId
providerPolicy
adjustment
trackingState
meshVertexCount
meshIndexCount
meshUvCount
fps
frameTimeMs
recipeLatencyMs
generateLatencyMs
runtimeApplyReady
warning
```

Blendshape assist contract:

```txt
Assist off:
  saved neutral/reference UV mask를 그대로 샘플링

Assist on:
  runtime ARKit blendshape 값을 이용해 material/feather/visibility/inner-mouth guard를 보조
  mask boundary를 매 프레임 AI로 재생성하지 않음
  generate-time n-shot capture set으로 expression envelope를 만든 뒤 runtime에서는 가볍게 보정
```

검증:

```txt
Unity batchmode import/compile
synthetic package smoke
texture load smoke
capture bundle export smoke
generated UV projection smoke
blendshape assist off/on payload smoke
runtime log analyzer smoke
```

### Phase 5. Pre-Xcode Build Gate Package

이번 세션은 iPhone을 연결하지 않으므로 여기서 멈추지 않고 build gate package를 완성한다. Xcode/실기기 빌드는 실행하지 않는다.

보고 항목:

```txt
Build question:
  iPhone이 연결된 다음 세션에서 UnityFramework/RN iPhone build를 진행할까요?

Primary path:
  approved web app shell -> RN forced wizard -> Unity capture bundle -> native Vision/MediaPipe -> generated UV mask package -> Unity runtime apply path

Compare paths:
  Vision/off
  Vision/blend
  MediaPipe/off
  MediaPipe/blend
  selected / safe fallback where available

Quality gate:
  user flow matches forced wizard
  capture set completeness
  native provider readiness
  boundary accuracy
  face attachment
  expression stability
  makeup visibility
  FPS/frame-time
  latency
  memory/thermal if available

Evidence matrix:
  web shell screenshots
  functional web beta generation proof
  logs
  buildless screenshots/frames
  contact sheets
  package summary
  runtime events
  native provider contract/static checks
  RN wizard snapshot/state gate tests

Out of scope:
  upload
  Android
  commercial SDK
  live face parsing/Core ML runtime
  AR runtime per-frame AI boundary generation
  이번 세션의 Xcode/iPhone build/install/launch
  이번 세션의 iPhone unlock/camera permission/runtime capture
```

Slack alert:

```bash
python3 scripts/notify_slack_user_required.py --message "E7 pre-Xcode 세팅이 완료되었습니다. iPhone 연결 후 빌드 진행 여부 확인이 필요합니다."
```

Webhook URL은 출력하거나 커밋하지 않는다.

### Phase 6. Deferred Xcode/iPhone Build Checklist

이번 세션에서는 실행하지 않는다. iPhone이 연결된 다음 세션에서 승인 후 실행할 명령만 문서화한다.

```bash
bash scripts/build_m3_unityframework.sh
```

그 다음:

```bash
cd rn/MakeupARValidation
npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK
```

RN CLI가 simulator 문제로 실패하면 direct Xcode fallback을 기록하고 사용한다. 단, 모든 fallback은 evidence log에 남긴다.

### Phase 7. Deferred iPhone Test Plan

iPhone이 연결된 다음 세션의 필수 scenario:

```txt
neutral
smile
open mouth
pucker if lip remains in scope
blink
squint
yaw left/right
pitch up/down
face leave/re-enter
return to adjust -> save -> re-enter AR
```

부위별 판단 질문:

```txt
lip:
  입꼬리가 비지 않는가?
  아랫입술 아래로 번지지 않는가?
  inner mouth/teeth를 칠하지 않는가?

blush:
  위치가 너무 낮거나 높지 않은가?
  코/눈밑/입가로 침범하지 않는가?
  부드럽고 자연스럽게 보이는가?

brow:
  앞머리/산/꼬리가 자연스러운가?
  좌우가 어색하지 않은가?
  피부/머리카락과 혼동되지 않는가?

eyeliner:
  눈꼬리 위치가 맞는가?
  blink에서 튀지 않는가?
  eyeball/눈동자 영역을 침범하지 않는가?
```

Evidence:

```txt
evidence/logs/
evidence/screenshots/
evidence/e7-region-generate/
```

Video는 motion이 핵심일 때만 저장한다. 저장하면 대표 frame/contact sheet/metadata를 만들고 raw recording 보관 여부를 판단한다.

### Phase 8. Result Sync

마지막에 반드시 `TECH_VALIDATION_RESULT.md`에 반영한다.

기록:

```txt
decision per region
what was built
what was verified buildless/pre-Xcode
known limitations
evidence paths
next boundary: Xcode/iPhone build and real-device runtime evidence
blocked/skipped/out-of-scope items
```

## 8. 멀티 에이전트 운영

### Manager

역할:

- 전체 목표와 boundary 관리.
- agent 소환과 handoff.
- active plan / TECH_VALIDATION_RESULT 업데이트.
- pre-Xcode gate package와 Slack alert.
- 최종 완료 판정.

Manager는 부분 완료를 성공으로 부르지 않는다.

### Debugger

역할:

- Manager를 보조하며 자잘한 frontend/backend/local-tool 버그를 계속 찾고 고친다.
- 타입 오류, lint, JSON schema, path 오류, missing artifact를 빠르게 처리한다.
- RN/Unity bridge payload mismatch를 추적한다.

산출물:

```txt
debug_log.md
fixed_issue_list.json
verification_commands.md
```

### Designer

역할:

- 웹앱과 RN 앱 UI를 설계한다.
- 얼굴 중앙을 가리지 않는 layout을 만든다.
- 제품 용어와 debug 용어를 분리한다.
- 슬라이더 + 버튼 조정 UX를 부위별로 설계한다.

산출물:

```txt
ui_flow.md
region_adjustment_controls.md
web_app_screen_contract.md
rn_screen_contract.md
```

### UX Shell Agent

역할:

- 기능 없는 web app shell을 만든다.
- iPhone 앱의 강제 단계형 화면을 웹에서 먼저 볼 수 있게 한다.
- shell과 functional beta를 섞지 않는다.
- 사용자가 승인할 수 있는 screenshot/state list를 만든다.

산출물:

```txt
web_app_shell_route.md
app_shell_screenshots/
wizard_step_contract.json
shell_to_rn_mapping.md
```

### Native Provider Agent

역할:

- iOS native Vision provider와 iOS native MediaPipe provider를 build-ready 상태로 구현한다.
- fixture replay, server upload, precomputed contour copy를 막는다.
- orientation/mirror/coordinate transform contract를 고정한다.
- RN bridge 호출 contract와 error/blockedReason shape를 만든다.

산출물:

```txt
native_provider_contract.md
vision_provider_static_check.md
mediapipe_provider_static_check.md
provider_boundary_schema.json
provider_blocker_report.md
```

### Unity Capture/Projection Agent

역할:

- Unity AR session에서 현재 frame과 ARFace mesh/UV/blendshape를 같은 순간에 export한다.
- capture bundle schema를 구현한다.
- provider 2D boundary를 UV mask로 투영하는 entrypoint를 준비한다.
- runtime debug/log가 얼굴 중앙을 가리지 않게 만든다.

산출물:

```txt
capture_bundle_schema.json
capture_export_smoke.md
uv_projection_smoke.md
runtime_debug_layout_check.md
```

### Blend/Capture Agent

역할:

- n회 촬영 sequence와 shot별 gate를 구현한다.
- blendshape assist off/on 비교 payload를 만든다.
- assist가 mask 재생성이 아니라 material/feather/visibility 보조임을 검증한다.

산출물:

```txt
capture_sequence_contract.md
blendshape_assist_contract.md
assist_off_on_payload_diff.json
expression_gate_matrix.md
```

### Data Agent

역할:

- 필요 데이터 확보, license/size/source 기록.
- 외부 mask prior small sample 준비.
- existing evidence inventory 정리.
- face parsing/color confidence/MediaPipe/Vision input 준비.

산출물:

```txt
source_review.md
data_manifest.json
external_prior_manifest.json
input_inventory.json
```

### Experiment and Reasoning Agent

역할:

- 실험 설계, scoring, 판단 논리 담당.
- 부위별 가설과 reject rule 작성.
- gold 없는 상황의 provisional 판단 관리.
- top candidate set과 selected policy 추천.

산출물:

```txt
experiment_matrix.json
scorecard.md
selected_policy.json
reasoning_report.md
```

### Strict QA Agent

역할:

- 가장 엄격하게 Manager를 보조한다.
- pre-xcode-ready/partial/blocked gate를 관리한다.
- evidence 누락, 과장된 claim, silent failure를 차단한다.
- Xcode/iPhone test를 실행하지 않는 현재 세션의 품질검증과 deferred test checklist를 담당한다.

Stop authority:

```txt
gold 없는 후보를 pre-xcode-ready라고 부르면 중단
iPhone evidence 없는 Green/product-quality claim이면 중단
4개 부위 중 하나라도 누락되면 완료 선언 차단
raw frame/upload/privacy 위반이면 중단
web shell approval 없이 RN UI 이식이면 중단
current capture 없이 fixture 결과를 앱 Generate로 표시하면 중단
native Vision/MediaPipe placeholder를 build-ready라고 부르면 중단
강제 단계 gate 없이 자유 탭 이동이면 중단
```

산출물:

```txt
qa_gate_matrix.json
qa_review.md
missing_evidence_list.md
final_acceptance_checklist.md
```

### Wildcard Agent

필요할 때만 소환한다.

역할:

- 큰 장애물에서 창의적 우회로를 찾는다.
- 외부 검색, repo/directory deep search, alternative library/path 탐색.
- MediaPipe GL/Metal context 문제, external dataset blocker, pre-Xcode integration blocker 같은 큰 이슈를 담당한다.

소환 조건:

```txt
2회 이상 같은 blocker 반복
primary path가 막혔지만 scope를 유지해야 함
외부 source/license/size 확인 필요
기존 repo 안에 숨은 evidence/tool을 찾아야 함
```

### Claude External Critic Agent

Claude는 구현자가 아니라 외부 비평가로 쓴다. Codex/Manager가 repo를 읽고 필요한 맥락을 선별한 뒤, Claude에는 구체적인 문제 설명과 판단 질문을 함께 넘긴다. Claude의 출력은 참고 의견이며 최종 구현, evidence 판정, 문서 반영은 Codex가 책임진다.

역할:

- 계획 누락, 과장된 완료 주장, weak gate를 비판한다.
- 아이라인처럼 막힌 부위의 fallback 후보를 창의적으로 제안한다.
- lip / blush / brow / eyeliner별 실패 모드와 사용자 조정축을 재검토한다.
- pre-Xcode 완료 조건과 deferred iPhone test checklist의 빈틈을 찾는다.
- 제품 사용자 흐름이 기술자용 flow처럼 보이는 지점을 비판한다.

적합한 호출 시점:

```txt
2시간 실험 루프 초반: 후보 생성 가설과 scorecard 비평
아이라인 2회 이상 실패: reference/photo/parametric fallback 비평
웹앱 flow freeze 전: Generate -> Review -> Adjust -> Save UX 비평
pre-Xcode gate 전: 누락된 buildless 검증과 과장 claim 점검
최종 보고 전: partial/blocked 기록의 정직성 점검
```

Claude에 넘기는 context packet:

```txt
Objective:
  이번 세션 목표와 완료 정의

Current boundary:
  iPhone 미연결, Xcode build/install/launch 금지, pre-xcode-ready가 최대 상태

Region status:
  lip / blush / brow / eyeliner 각각의 현재 후보, 약점, missing signal

Relevant constraints:
  local-only, no upload, no raw frame long-term storage, no live face parsing/Core ML runtime

Available signals:
  ARFace UV, Vision/MediaPipe, face parsing silver, color/gradient confidence, external prior

Decision questions:
  무엇이 빠졌는가?
  어떤 실패 모드가 과소평가되었는가?
  아이라인 최소 후보를 어떻게 보장할 것인가?
  pre-Xcode 완료 조건이 충분한가?

Output format:
  Critical risks
  Missing checks
  Region-by-region critique
  Concrete Codex handoff
```

금지:

```txt
Claude에게 .env, signing material, raw camera frame, screen recording, generated mask package, build cache를 보내지 않음
Claude가 repo 파일을 직접 수정하거나 build/test를 실행하지 않음
Claude 의견만으로 Green/product-quality-ready/runtime-ready 선언하지 않음
Claude 의견이 AGENTS.md / TECH_VALIDATION_RESULT.md / active roadmap과 충돌하면 local repo contract를 우선함
```

산출물:

```txt
claude_context_packet.md
claude_critique.md 또는 claude_stdout.json
claude_to_codex_handoff.md
manager_decision_on_claude_feedback.md
```

### 추가 에이전트

필요하면 아래를 추가한다.

```txt
RN Integration Agent
Unity Runtime Agent
Build Evidence Agent
Runtime Log Analyzer Agent
Documentation/Handoff Agent
```

## 9. 시간표와 알림

기본 timebox:

```txt
T+00:00 - T+00:15  Session boot, manifest, active contract 확인
T+00:15 - T+01:15  Web app shell 화면 계약 작성/검증
T+01:15 - T+03:15  Capture/native provider/experiment loop 병렬 구현
T+03:15 - T+04:30  RN forced wizard + Unity capture/projection integration
T+04:30 - T+05:15  Functional web beta parity, save package, blend off/on 검증
T+05:15 - T+05:45  Pre-Xcode build gate package and deferred test checklist
T+05:45 - T+06:15  Result sync and final report
```

알림/heartbeat:

```txt
30분마다 timeline.md 업데이트
2시간 실험 종료 시 Slack/user-required alert if review needed
웹 shell screenshot 준비 시 Slack/user-required alert if visual/user choice needed
pre-Xcode package 완료 시 Slack/user-required alert if next-session build decision needed
이번 세션에서는 iPhone 잠금/권한/빌드 승인을 요청하지 않음
시각 판단, 외부 full download, scope 확대가 필요할 때만 Slack/user-required alert
```

알림 명령:

```bash
python3 scripts/notify_slack_user_required.py --message "<짧은 한국어 요청>"
```

알림 실패 시:

```txt
SLACK_WEBHOOK_URL 미설정이면 timeline에 "slack_skipped_not_configured" 기록
알림 실패를 이유로 사용자-only gate를 자동 통과하지 않음
사용자-only action은 사용자 응답 전 진행하지 않음
```

## 10. 실험 루프 상세

### 10.1 Loop Contract

각 region마다 아래를 반복한다.

```txt
generate candidates
-> build include/exclude/unknown maps
-> score
-> contact sheet
-> inspect failure modes
-> refine
-> select top candidates
-> define adjustment axes
-> package
```

### 10.2 Required Artifacts

```txt
evidence/e7-region-generate/session-*/regions/lip/
evidence/e7-region-generate/session-*/regions/blush/
evidence/e7-region-generate/session-*/regions/brow/
evidence/e7-region-generate/session-*/regions/eyeliner/
```

각 region 폴더:

```txt
input_manifest.json
signal_report.json
candidates/
maps/
uv_projection/
contact_sheet.png
scorecard.json
selected_policy.json
adjustment_axes.json
package.json
summary.md
```

### 10.3 Reject Rules

공통 reject:

```txt
wrong coordinate / mirrored / upside-down
round-trip clearly off face region
negative spill severe
empty mask
full-face mask
unknown boundary too large
no source lineage
privacy flags missing
```

부위별 reject:

```txt
lip: teeth/inner-mouth/skin spill severe
blush: eye/nose/mouth/jaw spill severe
brow: eye opening or hairline confusion severe
eyeliner: eyeball/eye opening spill severe or line too unstable
```

## 11. 웹앱 상세

웹앱은 두 갈래다.

```txt
1. App Shell Preview
   - 기능 없는 UI 껍데기
   - iPhone 앱의 강제 단계형 flow를 웹에서 먼저 확인
   - RN 이식 전 사용자 승인 기준

2. Functional Generate Beta
   - 기존 lip-generate-beta/local server 방식을 참고
   - 실제 mask generation, UV projection, round-trip, adjust, save 검증
   - app shell과 UI가 다를 수 있지만 contract는 RN 이식 기준으로 맞춘다
```

권장 위치:

```txt
web/region-generate-beta/
web/region-generate-beta/src/routes/app-shell/
packages/region-generate-core/
local-tools/region-generate-server/
```

기존 lip 구조를 재사용한다.

```txt
web/lip-generate-beta/
packages/lip-generate-core/
local-tools/lip-generate-server/
```

필수 UX:

```txt
App Shell Preview:
  Start
  Face Alignment
  Capture Shots
  Native Extraction
  Candidate Compare
  Adjust
  Save
  Runtime Ready
  Debug Sheet

Functional Generate Beta:
  Generate all
  Review by region
  Adjust by region
  Save package
  Payload preview
  Evidence export
```

디자인 원칙:

```txt
첫 화면은 실제 사용 흐름
얼굴/preview 영역을 가리지 않음
debug JSON은 별도 panel
버튼은 빠른 조정
슬라이더는 세밀 조정
```

## 12. RN/Unity 상세

### 12.1 RN

필수 state:

```txt
wizardStep
wizardGateStatus
captureSet
captureShotProgress
nativeProviderStatus
savedPackage
selectedRegion
regionStatus
adjustmentValues
blendshapeAssistEnabled
arApplyStatus
latestUnityEvent
viewMode: clean | compareHud | debugSheet
```

필수 buttons:

```txt
촬영 시작
재촬영
후보 생성
4가지 후보 비교
저장
AR에서 보기
조정으로 돌아가기
부위 ON/OFF
```

금지:

```txt
기본 화면에 옛 validation HUD 노출
Vision/MediaPipe/UV/Assist 같은 기술 버튼을 사용자 flow의 primary action으로 노출
gate가 실패했는데 다음 단계 활성화
얼굴 중앙을 가리는 로그 panel
```

### 12.2 Unity

필수:

```txt
current frame capture
ARFace export
blendshape export
package parser
mask texture loader
native provider result receiver
2D boundary/UV projection bridge
region material binding
per-region enable/disable
runtime warning event
tracking state event
performance event
```

Blendshape assist:

```txt
lip: jawOpen / pucker / smile
blush: smile / cheek squint where available
brow: browInnerUp / browDown if available
eyeliner: eyeBlink / eyeSquint / eyeWide
```

Assist는 mask를 새로 생성하지 않는다. 같은 saved UV mask의 material/feather/visibility를 보조한다.

## 13. 품질 기준

### 13.1 Enterprise Quality Gates

```txt
Traceability:
  모든 package에 sourceLineage와 warnings 존재

Reproducibility:
  실험 command, input manifest, output paths 기록

Privacy:
  localOnly=true, offDeviceUpload=false, longTermRawFrameStored=false

UX:
  사용자 flow가 기술 후보 선택처럼 느껴지지 않음

Runtime:
  얼굴에 붙어 보임
  큰 HUD가 얼굴 중앙을 가리지 않음

Performance:
  FPS/frame-time/latency evidence 기록

Fallback:
  실패한 provider는 blockedReason 기록
```

### 13.2 Region Acceptance

```txt
Green:
  저장된 mask가 runtime에서 안정적으로 보이고, 주요 scenario에서 제품 검증을 계속할 수 있음

Yellow:
  기본 방향은 맞지만 조정/edge/expression/scenario caveat가 남음

Red:
  해당 region이 사용자를 오도하거나, AR runtime 적용 전 재설계 필요
```

Green은 iPhone evidence 없이는 선언하지 않는다.
이번 iPhone 미연결 세션의 최종 표기는 `pre-xcode-ready`, `partial`, `blocked` 중 하나다.

### 13.3 Build-Ready Reality Checklist

아래가 모두 참이어야 "이제 Xcode build만 남았다"고 말할 수 있다.

```txt
UI:
  web app shell에서 강제 wizard 전체 화면을 확인했다
  RN 기본 진입 화면이 shell과 같은 단계 구조다
  옛 validation HUD는 default path에서 제거되거나 dev/debug 뒤에 숨었다

Capture:
  Unity current-frame capture contract가 구현됐다
  capture set에 frame, ARFace mesh/UV, blendshape, quality metrics가 묶인다
  n회 촬영 shot 상태가 ready/retakeRequired/blocked로 기록된다

Providers:
  native Vision provider가 현재 frame 입력을 받는 bridge를 갖는다
  native MediaPipe provider가 현재 frame 입력을 받는 bridge를 갖는다
  두 provider 모두 fixture/precomputed replay를 앱 Generate로 반환하지 않는다

Generation:
  provider boundary -> 2D mask -> UV mask -> round-trip path가 연결됐다
  조정값 변경이 mask/UV/runtime payload에 실제 delta를 만든다
  stale result는 저장할 수 없다

Blend:
  assist off/on 비교 payload가 존재한다
  assist on은 runtime 매 프레임 AI 재생성이 아니라 blendshape 기반 lightweight 보정이다

Save/Runtime:
  saved package에 captureSetId, providerResults, adjustment, blendshapeAssist, privacy flags가 있다
  Unity가 saved package를 parse/register/apply하는 smoke를 통과했다
  debug/log UI는 얼굴 중앙을 가리지 않는다

QA:
  RN test/typecheck/lint 통과
  web build/typecheck/lint 통과
  Unity batchmode import/compile 통과
  provider static/snapshot checks 통과
  Strict QA가 빠진 단계와 과장 claim이 없다고 확인했다
```

### 13.4 2026-06-27 구현 현실 점검

이번 구현 루프의 결론은 `partial`이다. 핵심 제품 흐름은 앱 코드에 들어갔지만, native MediaPipe iOS dependency/model이 아직 로컬 프로젝트에 없으므로 "이제 Xcode build만 남았다"라고 말하면 안 된다.

완료된 것:

```txt
web app shell:
  Start -> Face Alignment -> Capture -> Native Extraction -> Compare -> Adjust -> Save -> Runtime Ready를 보여주는 기능 없는 iPhone 앱 UI shell 추가
  functional beta는 기존 local server Generate/adjust/save 검증 경로 유지

RN app:
  기본 진입을 옛 validation HUD가 아니라 맞춤 Generate forced wizard로 변경
  임의 단계 점프 방지
  n-shot capture state 추가
  neutral capture 없이는 native extraction 불가
  adjustment 변경 시 generated candidates stale 처리
  stale 상태에서는 save 차단
  debug는 face-center HUD가 아니라 별도 drawer로 이동

Unity capture:
  기존 E7SynchronizedCaptureExporter 재사용
  CaptureReferenceFrameJson으로 frame.png, arface_export.json, projected mesh overlay, blendShapes를 app Documents에 저장 가능

native iOS:
  E7NativeLipBoundaryProviders Swift bridge 추가
  Vision provider는 현재 capture frame과 arface_export.json을 읽어 lip landmark boundary와 ARFace export/blendshape payload를 RN에 반환
  saveGeneratedPackage는 local-only package record를 Documents/e7-generated-lip-packages에 저장
  MediaPipe provider는 fixture/replay를 반환하지 않으며, 현재는 blockedReason=mediapipe_ios_dependency_or_task_model_not_bundled 반환

RN generation:
  native boundary + ARFace screen/UV export -> raw RGBA UV mask package 생성 helper 추가
  Vision/off, Vision/blend, MediaPipe/off, MediaPipe/blend 후보 shape 생성
  Unity ApplyGeneratedLipMaskJson payload 전송 경로 유지
```

검증:

```txt
RN:
  ./node_modules/.bin/tsc --noEmit
  npm test -- --runInBand --watchman=false
  npm run lint

web:
  npm run lint
  npm run typecheck
  npm run build

shared:
  packages/lip-generate-core npm run typecheck
  packages/lip-generate-core npm test

local server:
  python3 local-tools/lip-generate-server/server.py --smoke
  result: partial
  Vision adjusted delta: 6763
  MediaPipe adjusted delta: 8275
  both uvMaskReady=true, roundTripReady=true, saveStatus=saved

iOS project static:
  plutil -lint rn/MakeupARValidation/ios/MakeupARValidation.xcodeproj/project.pbxproj
  ruby -c rn/MakeupARValidation/ios/Podfile

Unity:
  E7GeneratedLipMaskSmoke.RunFromCommandLine exit 0
  evidence/logs/e7-generated-lip-mask-rn-wizard-unity-smoke-20260627.log
```

현재 상태:

| 항목 | 상태 | 이유 |
| --- | --- | --- |
| Web shell | ready | 앱 wizard 껍데기 확인 가능 |
| Functional web beta | partial | 실제 fixture 기반 mask/UV/save 검증 가능, 앱 runtime 증거는 아님 |
| RN forced wizard | partial | buildless tests 통과, iPhone visual/runtime 미검증 |
| Unity capture/export | partial | 기존 exporter 재사용 가능, 이번 wizard에서 실기기 capture evidence 미수집 |
| native Vision | partial | Swift bridge/source 구현, Xcode/iPhone runtime 미검증 |
| native MediaPipe | blocked | iOS MediaPipe dependency/model 미번들; blockedReason 명시 |
| RN boundary->UV package | partial | JS helper/typecheck 통과, 실제 native Vision 결과와 on-device performance 미검증 |
| Save/runtime apply | partial | native save bridge/source 구현, Unity editor smoke 통과, iPhone runtime 미검증 |
| Build-ready claim | blocked | MediaPipe native blocker와 Xcode/iPhone evidence 부재 |

다음 결정을 해야 한다:

```txt
1. MediaPipe iOS dependency/model을 로컬 프로젝트에 번들해서 native MediaPipe를 완성한다.
2. 또는 첫 Xcode gate를 Vision-only로 좁힌다고 명시적으로 scope 조정한다.

사용자 원래 목표는 Vision과 MediaPipe 실제 비교이므로 기본 추천은 1번이다.
단, dependency/license/model size를 확인하기 전에는 build-ready로 올리지 않는다.
```

### 13.5 2026-06-27 MediaPipe iOS unblock / pre-Xcode ready 점검

13.4에서 남았던 native MediaPipe blocker는 제거됐다. 현재 상태는 `pre-xcode-ready`다. 의미는 "이제 Xcode build/install/run gate로 넘어갈 수 있다"이지, iPhone runtime 품질이나 product-ready를 뜻하지 않는다.

구현된 것:

```txt
iOS dependency:
  Podfile에 MediaPipeTasksVision 0.10.35 추가
  pod install 통과
  Podfile.lock에 MediaPipeTasksVision / MediaPipeTasksCommon 0.10.35 기록

iOS model resource:
  rn/MakeupARValidation/ios/MakeupARValidation/E7Models/face_landmarker.task 추가
  Xcode project Resources phase에 face_landmarker.task 등록
  모델 크기: 약 3.6MB

native MediaPipe provider:
  E7NativeLipBoundaryProviders.swift가 MediaPipeTasksVision을 conditional import
  module/resource가 있으면 current capture framePath + arFaceExportPath로 FaceLandmarker image mode 실행
  MediaPipe outer/inner lip landmark index를 frame_image_pixel_top_left boundary로 변환
  fixture/replay 반환 금지 유지
  module/resource가 없을 때만 blockedReason=mediapipe_tasks_vision_module_not_installed 또는 model missing 계열 반환

package contract:
  saved package에 captureSetId, providerResults, blendshapeAssist, adjustment, privacyFlags 명시
  Unity runtime payload에도 captureSetId 포함

Unity capture contract:
  E7SynchronizedCaptureExporter가 RN 요청의 captureSetId / captureShotKind / purpose를 파싱
  arface_export.json, capture_summary.json, RN capture event에 captureSetId / captureShotKind 보존
  quality summary에 trackingState, frame size, mesh vertex/index/uv count, projectedVertexCount, stable UV 여부, HUD 미포함 여부 기록
  blendshape 원본 값은 arface_export.json의 blendShapes에 유지하고 quality는 그 위치를 가리킴
```

검증:

```txt
iOS dependency/static:
  pod trunk info MediaPipeTasksVision
  pod install
  plutil -lint rn/MakeupARValidation/ios/MakeupARValidation.xcodeproj/project.pbxproj
  ruby -c rn/MakeupARValidation/ios/Podfile
  xcodebuild -workspace MakeupARValidation.xcworkspace -scheme MakeupARValidation -showBuildSettings

RN:
  ./node_modules/.bin/tsc --noEmit
  npm test -- --runInBand --watchman=false
  npm run lint

web:
  npm run lint
  npm run typecheck
  npm run build

shared:
  packages/lip-generate-core npm run typecheck
  packages/lip-generate-core npm test

local server:
  python3 local-tools/lip-generate-server/server.py --smoke
  result: partial
  Vision adjusted delta: 6763
  MediaPipe adjusted delta: 8275
  both uvMaskReady=true, roundTripReady=true, saveStatus=saved

Unity:
  E7GeneratedLipMaskSmoke.RunFromCommandLine exit 0
  evidence/logs/e7-generated-lip-mask-rn-wizard-mediapipe-prexcode-20260627.log
  evidence/logs/e7-generated-lip-mask-rn-wizard-capture-contract-prexcode-20260627.log

Strict QA:
  old validation HUD default path 없음
  capture 전 Generate 비활성
  stale 상태 save 차단
  debug/log face-center HUD 제거, drawer 뒤로 이동
  offDeviceUpload=false, longTermRawFrameStored=false 유지
```

현재 상태:

| 항목 | 상태 | 이유 |
| --- | --- | --- |
| Web shell | ready | 앱 wizard 껍데기 확인 가능 |
| Functional web beta | partial | fixture/local server 기반 생성/조정/저장 검증 가능, 앱 runtime 증거는 아님 |
| RN forced wizard | pre-xcode-ready | buildless tests 통과, Xcode/iPhone runtime 미검증 |
| Unity capture/export | pre-xcode-ready | captureSetId/shotKind/purpose/quality export 계약 보강 및 Unity compile/smoke 통과, 실기기 capture evidence는 다음 gate |
| native Vision | pre-xcode-ready | Swift current-frame provider 구현, Xcode/iPhone runtime 미검증 |
| native MediaPipe | pre-xcode-ready | Pod/model/resource/Swift current-frame provider 준비, Xcode/iPhone runtime 미검증 |
| RN boundary->UV package | pre-xcode-ready | JS helper/typecheck 통과, 실제 native 결과 runtime 성능 미검증 |
| Save/runtime apply | pre-xcode-ready | local save bridge/source 구현, Unity editor smoke 통과, iPhone runtime 미검증 |
| Build-ready claim | pre-xcode-ready | 이제 의도적으로 남긴 gate는 Xcode build/install/run과 실기기 evidence |

명시적 한계:

```txt
Xcode build/install/run은 실행하지 않았다.
iPhone에서 native Vision/MediaPipe가 실제 frame으로 성공하는지는 아직 증명되지 않았다.
FPS/frame-time/latency/memory/thermal/visual acceptance는 아직 없다.
Green/product-quality-ready, Lip G/Y/R, E7.3 Green은 아니다.
```

다음 gate:

```txt
사용자 승인 후 Xcode build/install/run.
빌드 전 Slack/user-required alert sent:
"이제 Xcode build만 하면 됩니다. 빌드 진행 승인이 필요합니다."
```

### 13.6 2026-06-27 UX correction after shell review

사용자 리뷰에서 다음 문제를 확인했다.

```txt
추출은 Vision 또는 MediaPipe 둘 중 하나를 선택하는 단계인데,
비교 화면이 provider 선택과 후보 비교를 섞어 보이게 했다.

조정 화면에서 마스크가 올라간 얼굴이 너무 작았다.
촬영 이후에도 live camera처럼 보여서 실제 촬영/저장 프레임인지 헷갈렸다.
뒤로가기가 없었다.
실제 촬영인지, 보이기만 하는 shell인지 구분이 부족했다.
```

반영한 것:

```txt
web shell:
  Start -> Align -> Capture -> Extract -> Compare -> Adjust -> Save -> Runtime 강제 흐름 유지
  Extract에서 Vision / MediaPipe 중 하나만 선택
  Compare는 선택 provider에서 나온 여러 후보를 비교하는 화면으로 변경
  모든 post-start step에 이전 버튼 추가
  Capture 이후 화면은 live camera가 아니라 캡처 프레임 검토 상태로 표시
  Adjust 화면은 작은 썸네일 대신 큰 mask-on-face preview 중심으로 변경

RN:
  generateWizardCandidates가 선택 provider 하나만 native current-frame provider로 실행
  provider 변경 시 기존 후보/save state 초기화
  wizard back button 추가
  Extract 이후 Unity live camera view 위에 captured-frame review shield 표시
  native provider 결과의 framePreviewUri를 큰 조정 preview slot에 연결

iOS native provider:
  Vision / MediaPipe 결과에 framePreviewUri=file://.../frame.png 반환
```

정직한 해석:

```txt
web shell은 실제 촬영이 아니다. UI/흐름 확인용이다.
RN/Unity 앱 경로는 단순 표시가 아니라 CaptureE7ReferenceFrameJson을 Unity로 보내고,
Unity exporter가 WaitForEndOfFrame 이후 ReadPixels로 frame.png를 쓰고 ARFace export를 저장하는 구조다.
다만 iPhone에서 실제로 캡처 파일이 생성되고 framePreviewUri 이미지가 RN에 표시되는지는 아직 Xcode/iPhone runtime gate 전이므로 증명되지 않았다.
```

검증:

```txt
web npm run typecheck
web npm run lint
web npm run build
RN ./node_modules/.bin/tsc --noEmit
RN npm test -- --runInBand --watchman=false
RN npm run lint
git diff --check
```

### 13.7 2026-06-27 Immediate adjustment sync correction

사용자 리뷰에서 조정 UX 기준을 다시 고정했다.

```txt
슬라이더 조정 후 "다시 생성"을 기다리는 UX는 목표와 맞지 않는다.
조정 화면의 사진 preview는 딜레이 없이 바로 바뀌어야 한다.
무거운 Vision/MediaPipe 추출은 다시 돌리지 않는다.
이미 추출된 lip boundary를 같은 조정식으로 변형하고, 그 결과를 preview/package에 반영한다.
```

반영한 것:

```txt
web functional beta:
  현재 slider state로 lip boundary를 즉시 변형
  원본 사진 위 SVG mask-on-face preview를 즉시 갱신
  stale 상태에서도 저장 버튼을 막지 않음
  저장을 누르면 최신 조정값으로 local server package를 다시 생성한 뒤 저장

RN app:
  adjustment 변경 시 native provider 재호출/timeout debounce 제거
  이미 추출한 native boundary + ARFace export에서 후보 package를 즉시 재계산
  UV raw RGBA 생성 전에 lip boundary adjustment를 적용
  stale state를 해제하고 현재 package를 저장 가능 상태로 유지
```

검증:

```txt
web npm run typecheck
web npm run lint
web npm run build
browser check:
  Generate 후 cornerReach slider 0 -> 0.35 변경
  live preview SVG path 즉시 변경 확인
  stale save 클릭 후 saved record에 cornerReach 0.35 저장 확인
local server smoke:
  Vision adjusted delta 6763
  MediaPipe adjusted delta 8275
RN npm test -- --runInBand --watchman=false
RN ./node_modules/.bin/tsc --noEmit
RN npm run lint
shared-core npm run typecheck
shared-core npm run test
git diff --check
```

## 14. User-Required Gates

반드시 사용자 도움을 요청해야 하는 경우:

```txt
시각적으로 가장 나은 후보 선택
최종 subjective acceptance
외부 dataset full download/checkpoint download 승인
runtime video 저장 여부
scope 확대 승인
```

`빌드 승인`, `iPhone 잠금 해제`, `카메라 권한`은 이번 세션에서는 요청하지 않고 다음 phone-connected build session의 deferred gate로 남긴다.

요청 방식:

```txt
짧은 한국어 메시지
Slack alert 시도
timeline에 기록
사용자 응답 전 gated action 진행 금지
```

## 15. Risk Register

| Risk | 대응 |
| --- | --- |
| Gold mask 없음 | external prior + multi-signal provisional + unknown map |
| 외부 데이터 license/size 불명확 | source review 먼저, small sample만, full download approval 필요 |
| MediaPipe Codex shell GL/Metal 실패 | GUI Terminal/manual helper 또는 helper signal로 downgrade |
| Face parsing이 부정확 | silver only, single source winner 금지 |
| Color edge가 shadow/hair와 혼동 | confidence/warning으로만 사용 |
| Eyeliner가 불안정 | reference 사진/외부 prior/parametric stroke/minimal-safe curve 반복으로 최소 후보 생성 |
| Xcode build 실패 | 이번 세션에서는 실행하지 않고 다음 세션 checklist/fallback으로 보존 |
| 기기 잠금/권한 | 이번 세션에서는 요청하지 않고 deferred gate로 기록 |
| 성능 저하 | runtime metrics로 region/source별 분리 |
| 사용자 기대와 다른 결과 | 제품 시나리오와 조정축을 먼저 고정 |

## 16. 최종 보고 형식

최종 보고는 짧고 결정 중심으로 쓴다.

```txt
What was built
- ...

What was verified buildless/pre-Xcode
- ...

Region decisions
- lip: pre-xcode-ready/partial/blocked, reason
- blush: pre-xcode-ready/partial/blocked, reason
- brow: pre-xcode-ready/partial/blocked, reason
- eyeliner: pre-xcode-ready/partial/blocked, reason

Known limitations
- ...

Evidence
- logs
- screenshots/frames
- packages
- contact sheets

Next boundary
- ...
```

## 17. Ready-To-Run Goal Prompt

다음 구현 세션에 줄 목표:

```txt
cwd=/Users/wiseungcheol/Desktop/makeupAR

목표:
E7 in-app personalized Generate flow를 Xcode 빌드 직전까지 완성한다. 사용자가 앱에서 단계별로 얼굴을 정렬하고, n회 촬영하고, 현재 촬영 frame에서 native Vision/MediaPipe 후보를 생성하고, blendshape assist off/on을 비교하고, 조정 후 저장하며, 저장된 UV mask package를 Unity AR runtime이 적용할 수 있는 상태까지 준비한다. 최종 상태는 "이제 Xcode build/install/run만 하면 된다"여야 한다.

필수 읽기:
1. AGENTS.md
2. TECH_VALIDATION_RESULT.md > Current Session Snapshot
3. docs/roadmaps/README.md
4. docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md

작업 원칙:
- 구현 전에 web app shell을 만든다. shell은 기능 없는 iPhone 앱 UI 껍데기이며 강제 단계형 flow를 보여준다.
- 실제 기능은 기존 web beta/local server의 생성/조정/저장 방식을 RN/Unity/native 구조로 이식한다.
- 앱은 탭/하단 페이지네이션이 아니라 강제 wizard다. 이전 gate가 통과되지 않으면 다음 단계로 넘어갈 수 없다.
- 첫 핵심 단계는 Generate가 아니라 촬영이다. 현재 frame + ARFace mesh/UV + blendshape + quality metrics를 capture bundle로 만든다.
- native Vision과 native MediaPipe를 둘 다 current-frame provider로 구현한다. fixture/precomputed replay를 앱 Generate처럼 보이면 실패다.
- blendshape assist off/on 비교를 구현한다. assist on은 매 프레임 AI 재생성이 아니라 saved UV mask의 material/feather/visibility 보조다.
- 조정값은 2D mask, UV texture, round-trip, runtime payload에 실제 delta를 만들어야 한다.
- 저장 버튼과 stale-result 차단을 구현한다.
- 옛 validation HUD는 기본 제품 흐름에서 제거하고 dev/debug 뒤로 숨긴다.
- debug/log는 얼굴 중앙을 가리지 않는 sheet/drawer로만 보여준다.
- raw camera frame 장기 저장, 서버 업로드, Android, commercial SDK, live face parsing/Core ML runtime은 하지 않는다.
- Xcode/iPhone build/install/launch는 실행하지 않는다. 목표는 build 직전 준비 완료다.
- iPhone evidence 없이 Green/product-quality ready를 주장하지 않는다.

에이전트:
- Manager
- UX Shell Agent
- RN Wizard Agent
- Unity Capture/Projection Agent
- Native Provider Agent
- Blend/Capture Agent
- Web Logic Agent
- Debugger
- Strict QA Agent
- Documentation/Handoff Agent
- Wildcard Agent only when blocked
- Claude External Critic Agent only for critique/fallback/risk review

완료 조건:
- web app shell에서 Start -> Face Alignment -> Capture -> Native Extraction -> Compare -> Adjust -> Save -> Runtime Ready 화면 확인 가능
- functional web beta가 실제 mask generation/adjust/save를 계속 검증
- RN 기본 화면이 forced wizard이고 old validation HUD가 default path에 없음
- Unity capture bundle exporter 구현
- native Vision provider 구현
- native MediaPipe provider 구현
- capture set n회 촬영 상태와 quality gate 구현
- Vision/off, Vision/blend, MediaPipe/off, MediaPipe/blend 후보 비교 가능
- adjustment delta와 stale save block 검증
- saved package에 captureSetId, providerResults, adjustment, blendshapeAssist, privacy flags 포함
- Unity saved package parse/register/apply smoke 통과
- web/RN/shared/native/Unity buildless checks 통과
- Strict QA가 Build-Ready Reality Checklist를 통과 또는 partial/blocked 항목을 명시
- TECH_VALIDATION_RESULT.md 업데이트
- Slack/user-required alert 준비: "이제 Xcode build만 하면 됩니다. 빌드 진행 승인이 필요합니다."

중단/질문 조건:
- web shell 시각 승인이 필요하면 사용자에게 바로 요청
- iPhone unlock, camera permission, Xcode build가 필요해지는 순간 멈추고 사용자에게 요청
- native MediaPipe dependency/license/model 문제가 막히면 blockedReason과 우회안을 정리하고 사용자에게 보고
- 목표 일부만 끝났으면 완료라고 하지 말고 partial/blocked를 명시
```

### 17.1 Superseded: partial 상태에서 이어가던 Goal Prompt

```txt
상태: superseded by 13.5 / 17.2.
남아 있던 native MediaPipe iOS dependency/model blocker는 2026-06-27 pre-Xcode pass에서 해소됐다.
현재 이어갈 때는 아래 17.2 Xcode Gate Prompt를 사용한다.

cwd=/Users/wiseungcheol/Desktop/makeupAR

목표:
E7 in-app personalized Generate flow를 "Xcode build/install/run만 남은 상태"까지 마저 닫는다. 현재 web shell, functional web beta, RN forced wizard, Unity capture exporter 연동, native Vision bridge, JS boundary->UV raw RGBA package helper, local save bridge, Unity generated-mask editor smoke는 buildless/source-stage 통과했다. 남은 핵심 blocker는 native MediaPipe iOS dependency/model 미번들이다. 절대 Vision-only를 완성으로 포장하지 말고, MediaPipe를 실제 current-frame provider로 완성하거나 사용자의 명시 승인 아래 scope를 Vision-only build gate로 좁혀라.

필수 읽기:
1. AGENTS.md
2. TECH_VALIDATION_RESULT.md > Current Session Snapshot
3. docs/roadmaps/README.md
4. docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md > 13.4

현재 완료된 기반:
- web/lip-generate-beta/src/AppWizardShell.tsx: 기능 없는 앱 UI shell
- web/lip-generate-beta functional beta/local server: 실제 fixture Generate/adjust/save 검증
- rn/MakeupARValidation/App.tsx: forced wizard default path
- rn/MakeupARValidation/src/e7PersonalizedGeneratePipeline.ts: native boundary + ARFace export -> raw RGBA UV package helper
- rn/MakeupARValidation/ios/MakeupARValidation/E7NativeLipBoundaryProviders.swift: native Vision + local save bridge, MediaPipe blocked adapter
- Unity RNBridge/E3RegionMaskOverlay: generated raw RGBA mask register/apply path
- evidence/logs/e7-generated-lip-mask-rn-wizard-unity-smoke-20260627.log

필수 작업:
1. MediaPipe iOS dependency/model 현실성 확인
   - repo-local asset/dependency 우선 탐색
   - 없으면 공식/primary source만 확인
   - license/model size/offline bundling 가능성 기록
2. native MediaPipe current-frame provider 구현
   - fixture/precomputed replay 금지
   - current capture framePath + arFaceExportPath 입력
   - lip outer/inner boundary 반환
   - blockedReason 없이 ready가 되려면 model/resource path와 initialization contract가 실제로 존재해야 함
3. RN wizard와 native provider 통합 보강
   - Vision/off, Vision/blend, MediaPipe/off, MediaPipe/blend 중 blocked/ready가 UI에 명확히 보이게 유지
   - MediaPipe ready 시 generated candidate package 생성 확인
   - adjustment 변경 -> stale -> regenerate -> save 경로 유지
4. buildless 검증 재실행
   - RN tsc/test/lint
   - web lint/typecheck/build
   - lip-generate-core typecheck/test
   - local server smoke
   - iOS project static checks
   - Unity generated-mask editor smoke
5. Strict QA
   - old validation HUD가 default path에 보이지 않는지 확인
   - capture 없이 Generate가 되지 않는지 확인
   - 저장 버튼/stale 차단 확인
   - debug/log가 얼굴 중앙을 가리지 않는지 확인
   - raw frame upload/long-term storage 금지 유지
6. 문서 업데이트
   - TECH_VALIDATION_RESULT.md에 결정/evidence/limitations/next boundary 기록
   - active roadmap 13.4 상태 갱신

완료 조건:
- MediaPipe native blocker가 제거되어 Vision과 MediaPipe 모두 current-frame provider로 build-ready이거나, 사용자가 Vision-only build gate 축소를 명시 승인했다.
- RN/web/shared/iOS static/Unity buildless checks가 통과했다.
- Strict QA가 "Xcode build만 남음" 또는 남은 partial/blocked를 명확히 선언했다.
- Xcode/iPhone build/install/launch는 실행하지 않았다.

멈춤 조건:
- MediaPipe dependency/model 다운로드, license, 큰 binary 추가, Xcode build, iPhone unlock/camera permission, 또는 사용자 visual 선택이 필요하면 즉시 멈추고 한국어로 요청한다.
- Xcode build가 필요해지는 순간 scripts/notify_slack_user_required.py로 Slack 알림을 시도하고 사용자 승인을 기다린다.
```

### 17.2 현재 pre-Xcode-ready 상태에서 이어갈 Xcode Gate Prompt

```txt
cwd=/Users/wiseungcheol/Desktop/makeupAR

목표:
E7 in-app personalized Generate flow는 pre-Xcode-ready 상태다. 이제 사용자 승인 후 Xcode build/install/run을 수행하고, iPhone에서 실제 capture-first wizard가 native Vision/MediaPipe current-frame 후보를 생성, blendshape assist off/on 비교, 조정, 저장, Unity runtime apply까지 이어지는지 검증한다.

필수 읽기:
1. AGENTS.md
2. TECH_VALIDATION_RESULT.md > Current Session Snapshot
3. docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md > 13.5

빌드 전 확인:
- 사용자에게 Xcode build/install/run 승인 요청
- Slack alert 시도: "이제 Xcode build만 하면 됩니다. 빌드 진행 승인이 필요합니다."
- 기기 unlock/camera permission이 필요하면 즉시 멈춤

실행:
- bash scripts/build_m3_unityframework.sh
- cd rn/MakeupARValidation
- npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK

실기기 검증:
- wizard 기본 진입: old validation HUD가 기본 화면에 없음
- Start -> Align -> Capture -> Extract -> Compare -> Adjust -> Save -> Runtime Ready 강제 흐름
- neutral capture가 frame.png / arface_export.json / blendShapes를 남기는지
- n-shot capture의 captureSetId / captureShotKind / purpose가 arface_export.json, capture_summary.json, RN capture event에 유지되는지
- capture quality summary가 trackingState, frame size, mesh vertex/index/uv count, projectedVertexCount, stable UV 여부를 남기는지
- native Vision ready 여부와 boundary preview
- native MediaPipe ready 여부와 boundary preview
- Vision/off, Vision/blend, MediaPipe/off, MediaPipe/blend 비교 카드
- adjustment 변경 후 stale, regenerate 후 save 가능
- saved package에 captureSetId/providerResults/adjustment/blendshapeAssist/privacyFlags 포함
- Unity runtime apply 로그와 얼굴 중앙을 가리지 않는 debug drawer
- FPS/frame-time/latency/memory/thermal 기본 기록

완료 조건:
- 빌드/install/launch 결과와 실패 로그를 TECH_VALIDATION_RESULT.md에 기록
- 성공하더라도 Green/product-ready로 올리지 말고 runtime evidence와 visual acceptance를 분리 기록
- 실패 시 blocker와 fallback을 기록
```
