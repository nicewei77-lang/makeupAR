# E7 Full Face Region Generate 완전 구현 계획

작성일: 2026-06-27 KST

## 0. 결정

이번 작업의 목표는 립 단일 후보 실험을 넘어, **립 / 블러셔 / 눈썹 / 아이라인 region을 생성, 조정, 저장하고 Xcode 빌드 직전까지 RN/Unity 적용 준비를 끝내는 완성품 수준의 pre-Xcode 구현**이다.

핵심 제품 흐름:

```txt
사용자가 맞춤 생성 시작
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
5. 웹앱에서 Generate -> Review/Adjust -> Save -> Payload 흐름 완주
6. RN 앱에서 저장된 region package를 읽고 AR 화면으로 넘기는 흐름 구현
7. Unity runtime이 저장된 UV mask texture를 부위별로 적용할 수 있도록 구현
8. Xcode 빌드 직전 상태까지 정적/빌드리스 검증 완료
9. iPhone 연결 후 실행할 build/run/test checklist와 evidence matrix 준비
10. synthetic package smoke, Unity import/compile, RN test/typecheck/lint, runtime log analyzer smoke 기록
11. TECH_VALIDATION_RESULT.md에 결정, evidence, limitations, next boundary 기록
```

완료가 아닌 경우:

```txt
- 웹 UI만 있고 실제 mask 생성이 없는 경우
- 외부 mask prior만 만들고 우리 app frame / ARFace UV로 투영하지 않은 경우
- 저장된 package 없이 임시 asset만 바꾼 경우
- 한두 부위만 성공했는데 전체 완료라고 말하는 경우
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
3. 얼굴 체크
   - 정면
   - 얼굴 거리
   - 밝기
   - 흔들림
4. Generate 누름
5. 앱이 현재 얼굴에서 4개 region mask 후보를 만든다
   - 립
   - 블러셔
   - 눈썹
   - 아이라인
6. 후보가 화면에 보인다
7. 사용자는 부위별로 켜고 끄며 확인한다
8. 가장 흔한 문제를 빠르게 조정한다
9. 저장
10. 저장된 mask package를 AR 화면 진입 payload로 고정
11. iPhone 연결 후 AR 화면에서 메이크업 look 적용
12. smile / open mouth / blink / yaw로 확인
13. 마음에 들면 유지
14. 마음에 안 들면 조정 화면으로 돌아가기
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

## 3. 범위

### 3.1 포함

- CLI 기반 반복 실험.
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
- Xcode 빌드 직전 checklist/evidence matrix/package readiness.
- Slack user-required alert.
- TECH_VALIDATION_RESULT.md 업데이트.

### 3.2 제외

- 서버 업로드 기반 제품 흐름.
- raw camera frame 장기 저장.
- commercial SDK 도입.
- Android.
- live face parsing/Core ML runtime.
- 매 프레임 Vision/MediaPipe/face parsing으로 boundary 재생성.
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

### 4.2 신호 역할

| Signal | 역할 | 금지 |
| --- | --- | --- |
| ARFace mesh/UV | runtime 좌표계, 2D mask -> UV projection, 얼굴 부착 | semantic boundary 자체로 과신 금지 |
| Apple Vision | 2D contour / landmark sanity signal | gold mask 또는 runtime primary tracker 취급 금지 |
| MediaPipe | geometry prior, lip/eye/brow landmark helper, comparison signal | Codex shell 자동 필수 gate로 고정 금지 |
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
    frameWidth: number;
    frameHeight: number;
    orientation: string;
    isMirrored: boolean;
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

### Phase 2. 1시간 웹앱 완성

목표:

- 웹앱은 실험장이 아니라 pre-build UI/logic verification shell이다.
- selected candidate policy를 불러와 Generate / Adjust / Save 흐름을 확인한다.

필수 화면:

```txt
Generate
  - 얼굴/fixture 선택
  - 4개 부위 Generate
  - status pre-xcode-ready/partial/blocked

Review
  - lip / blush / brow / eyeliner tabs
  - candidate toggle
  - overlay preview
  - warning list

Adjust
  - button presets
  - sliders
  - before/after preview

Save
  - saved package summary
  - privacy flags
  - runtime payload preview
```

완료 조건:

```txt
웹앱에서 4개 부위 package load/generate/review/adjust/save 가능
payload JSON preview 가능
얼굴 중앙을 가리는 debug UI 없음
```

### Phase 3. RN App Integration

목표:

- 웹앱에서 검증한 흐름을 RN 앱에 옮긴다.
- 저장 package를 AR 화면으로 넘긴다.

필수 UI:

```txt
Calibration screen
  - Generate
  - Review/Edit each region
  - Save package
  - Enter AR

AR screen
  - Clean
  - Compare HUD
  - Debug
  - Return to Adjust
```

필수 contract:

```txt
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

### Phase 4. Unity Runtime Integration

목표:

- 저장된 UV mask texture를 Unity runtime에서 부위별로 적용.
- 기존 smooth-region-mask 구조를 generated package로 대체 또는 확장.

필수 구현:

```txt
GeneratedRegionMaskRegistry
ApplySavedRegionPackage parser
CompositeMakeupPackage parser
DynamicRegionMaskTexture loader
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

검증:

```txt
Unity batchmode import/compile
synthetic package smoke
texture load smoke
runtime log analyzer smoke
```

### Phase 5. Pre-Xcode Build Gate Package

이번 세션은 iPhone을 연결하지 않으므로 여기서 멈추지 않고 build gate package를 완성한다. Xcode/실기기 빌드는 실행하지 않는다.

보고 항목:

```txt
Build question:
  iPhone이 연결된 다음 세션에서 UnityFramework/RN iPhone build를 진행할까요?

Primary path:
  saved composite package -> Unity generated region masks -> AR runtime apply path

Compare paths:
  base / selected / safe
  assist off / assist on where available

Quality gate:
  boundary accuracy
  face attachment
  expression stability
  makeup visibility
  FPS/frame-time
  latency
  memory/thermal if available

Evidence matrix:
  logs
  buildless screenshots/frames
  contact sheets
  package summary
  runtime events

Out of scope:
  upload
  Android
  commercial SDK
  live face parsing/Core ML runtime
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
T+00:15 - T+02:15  Experiment loop
T+02:15 - T+03:15  Web app UI/logic completion
T+03:15 - T+04:15  RN/Unity buildless integration and checks
T+04:15 - T+04:45  Pre-Xcode build gate package and deferred test checklist
T+04:45 - T+05:15  Result sync and final report
```

알림/heartbeat:

```txt
30분마다 timeline.md 업데이트
2시간 실험 종료 시 Slack/user-required alert if review needed
1시간 웹앱 종료 시 Slack/user-required alert if visual/user choice needed
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

웹앱은 실험 시간이 아니라 검증 시간이다.

권장 위치:

```txt
web/region-generate-beta/
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
savedPackage
selectedRegion
regionStatus
adjustmentValues
arApplyStatus
latestUnityEvent
viewMode: clean | compareHud | debug
```

필수 buttons:

```txt
맞춤 생성
저장
AR에서 보기
조정으로 돌아가기
부위 ON/OFF
```

### 12.2 Unity

필수:

```txt
package parser
mask texture loader
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
E7 Full Face Region Generate 완전 구현 계획을 실행한다. 립 / 블러셔 / 눈썹 / 아이라인 region mask를 생성, 조정, 저장하고, 저장된 mask package를 RN/Unity AR runtime에서 적용할 수 있도록 Xcode 빌드 직전까지 세팅을 완료한다.

필수 읽기:
1. AGENTS.md
2. TECH_VALIDATION_RESULT.md > Current Session Snapshot
3. docs/roadmaps/README.md
4. docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md

작업 원칙:
- 실험은 웹앱이 아니라 CLI/local script로 2시간 반복한다.
- 웹앱은 1시간 pre-build UI/logic verification shell로 완성한다.
- 외부 mask prior는 silver only로 사용한다.
- face parsing과 color confidence는 버리지 말고 후보 생성/검증/경고 신호로 사용한다.
- ARFace UV는 runtime 좌표계다.
- iPhone evidence 없이 Green/product-quality ready를 주장하지 않는다.
- 이번 세션에서는 Xcode/iPhone build/install/launch, 기기 잠금 해제, 카메라 권한 요청, 실기기 runtime test를 실행하지 않는다.
- 4개 부위를 모두 처리한다. 못 끝낸 부위는 blocked/partial로 명시한다.
- 아이라인은 어렵다는 이유로 제외하지 않는다. 사진/reference/외부 prior/parametric curve/soft lashline 우회로를 반복해서라도 최소 candidate를 만든다.
- Claude는 구현자가 아니라 외부 비평가로 사용한다. Codex가 구체적인 관련 맥락을 context packet으로 정리해 넘기고, Claude의 비평을 Codex가 repo/evidence gate에 맞춰 다시 판단한다.

에이전트:
- Manager
- Debugger
- Designer
- Data Agent
- Experiment and Reasoning Agent
- Strict QA Agent
- Wildcard Agent when blocked
- Claude External Critic Agent for critique/fallback/risk review

완료 조건:
- 4개 region 후보 생성과 selected policy
- 사용자 조정축
- Claude critique 또는 Codex 내부 대체 비평 반영 여부 기록
- web generate/review/adjust/save
- RN saved package -> AR screen
- Unity generated mask apply
- pre-Xcode build gate package
- deferred Xcode/iPhone build/run/test checklist
- TECH_VALIDATION_RESULT.md 업데이트
```
