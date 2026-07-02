# makeupAR → 302 통합 계획 (cross-repo 인벤토리 diff 기반)

작성일: 2026-06-30 KST

## 0. 목적 · 절대 제약

- **목적:** makeupAR(lab)의 사용자 맞춤형 마스크 엔진을 제품 앱 `302-group5-final-project`의 **사용자 얼굴분석 흐름**에 통합한다.
- **진입점(확정):** 302 `FaceAnalysisReportDetail` 화면의 `onCreateARFilter` → 여기서 맞춤 마스크 생성/조정/AR 흐름으로 이어진다.
- **절대 제약:** makeupAR의 **모든 기능을 보존**한다. **되던 것이 안 되면 안 된다(회귀 금지).** UI/UX만 302 디자인으로 통일(별도 문서 `USER_FLOW_REDESIGN_KO.md`).

경로:
- lab: `~/Desktop/makeupAR` (remote `nicewei77-lang/makeupAR`)
- 제품: `~/Desktop/MAKEUPAPP/302-group5-final-project` (remote `devhyun05/302-group5-final-project`, 브랜치 `codex/auradin-loaderdots-fix`)

### 0.1 작업 디렉토리 · 브랜치 원칙

- 이 문서는 `~/Desktop/makeupAR`에 둔다. 단, **302 제품 통합 구현은 이 repo에서 하지 않는다.**
- `~/Desktop/makeupAR`는 lab 정본/참조 소스/계획 문서 위치다. 현재 E7 full-face `병합용브랜치` 작업과 302 제품 구현을 섞지 않는다.
- 실제 구현 작업 위치는 `~/Desktop/MAKEUPAPP/302-group5-final-project`다.
- 302 통합 구현은 제품 repo에서 별도 브랜치(권장: `codex/302-full-face-makeupar-integration`)를 만든 뒤 시작한다.
- 구현 시작 전 302 repo의 기존 변경사항을 확인한다. 기존 WIP가 통합 기반이면 새 브랜치로 함께 가져가고, 무관한 변경이면 별도 정리/분리 후 진행한다.
- makeupAR 쪽 파일은 통합 중에도 수정 대상이 아니라 **참조 source-of-truth**다. 필요한 코드/asset/contract만 302 repo로 선별 이식한다.

## 1. 두 repo의 정체 (확인된 사실)

| | makeupAR (lab) | 302 (제품) |
|---|---|---|
| 성격 | **실제 동작 엔진 + 검증 하니스** | **제품 UI/UX 셸 + 백엔드 + 디자인 시스템** |
| RN | bare RN 0.86, `@azesmway/react-native-unity`로 **embedded Unity 실동작** | **Expo ~56**, RN 0.85.3, **embedded Unity dep 없음** |
| 촬영 | Unity/native 경로(E7 synchronized capture) | **expo-camera**(FaceCaptureScreen) |
| 얼굴분석 | 없음(로컬 전용) | **백엔드 분석 job**(createFaceAnalysisReportFromCapture, BackendApiError) |
| AR 렌더 | **실제 face-tracked Unity** smooth-region-mask | **카메라 오버레이 + 프리셋 필터**(LiveCameraLayer). Unity 브리지 *계약/프리셋*만 있고 native 미연결(추정) |
| 디자인 | 검증 UI(plain RN) | **Tamagui + `shared/theme`(colors/spacing/typography) + `shared/ui` 컴포넌트** |
| 데이터 모델 | `FullFaceMakeupRecipe`(4-region), lip은 region payload로 담김 | `MakeupFilter`(프리셋 카탈로그) |

> 두 repo는 **같은 혈통**이다: 동일 Unity 브리지 계약(`RNBridge`/`ApplyRecipeJson`/`smooth-region-mask`, region lip/cheek/brow/eye), 동일 E3/E7 Unity 스크립트 계열(302 8개 vs lab 5개).

## 2. 인벤토리 diff (feature/화면/계약/native/Unity)

판정: **정본=302** = 302 것을 기준 삼고 lab을 맞춤 / **정본=lab** = lab 엔진을 가져와야 함 / **신규배선** = 둘을 잇는 코드 필요.

| 영역 | 302 (제품) | makeupAR (lab) | 실제/목업 | 정본 / 처리 |
|---|---|---|---|---|
| 촬영(생성용) | expo-camera 사진(face-analysis) | Unity synchronized capture(frame+arFaceExport) | 둘 다 실제 | **정본=makeupAR Unity capture**(AR 충돌=makeupAR). expo-camera 사진은 **진입 컨텍스트일 뿐**, 마스크 생성 source of truth는 Unity synchronized capture bundle |
| 얼굴분석 | 백엔드 분석 리포트 — 실제 | 없음 | 302 실제 | **정본=302**. 분석 리포트 화면에서 마스크 흐름 진입 |
| 진입 seam | `FaceAnalysisReportDetail.onCreateARFilter`→`MakeupFilterEdit` | — | 302 실제 | **신규배선**: onCreateARFilter를 맞춤 마스크 생성 진입으로 |
| AR 화면군 | ARFilter / ARFilterShapeAdjust / MakeupFilterEdit / MakeupFilterSave / UnityMakeupCapture (Tamagui, LiveCameraLayer) | App.tsx 마법사(plain RN) | 302 화면 실제(UI) / AR엔진은 카메라오버레이 | **정본=302 화면 + lab 엔진**: 302 화면 유지, 뒤에 lab 생성/렌더 엔진 연결 |
| **마스크 생성 엔진** | 없음(프리셋만) | `lip-generate-core`(순수 TS) + `e7PersonalizedGeneratePipeline`(buildGeneratedLipPackage/CandidateSet, smoothLipBoundary, buildUvMaskRawRgba…) | lab 실제 | **정본=lab**. 통째로 이식(전 기능 보존 핵심). 핵심 스키마는 region payload/4-region로 확장 |
| 모양/표현 조정 | ARFilterShapeAdjust (프리셋 기반 PanResponder) | lip 조정 5필드 + finish/tuning + candidate | lab 실제 | **정본=lab 파라미터**를 기준으로 하되 region별 조정은 data-driven schema로 라우팅하여, 302 화면 셸에 얹는다 |
| 데이터 계약 | `shared/types/makeupGuide`(MakeupFilter) + `packages/shared-contracts`(빈 .gitkeep) | `FullFaceMakeupRecipe`(4-region) + `LipGeneratePackage`(region payload) | — | **신규배선**: shared-contracts 1차 산출물 = `FullFaceMakeupRecipe`(4-region), lip package는 region payload. MakeupFilter↔recipe 매핑 |
| Unity 브리지 | `ar/services/unityMakeupBridge.ts`(계약/프리셋, NativeModules 참조하나 dep 없음→stub 추정) | App.tsx `postMessage('RNBridge','ApplyRecipeJson')` + UnityEventPayload(실동작) | lab 실제 | **정본=lab 동작**, 302 브리지 파일과 계약 통일 |
| embedded Unity | dep 없음(Expo) | `@azesmway/react-native-unity` 실동작 | lab 실제 | **정본=lab**. 302 Expo에 native 통합 필요(최대 리스크) |
| iOS native | — | `E7NativeLipBoundaryProviders`(Swift: extractLipBoundary/saveGeneratedPackage/renderLipMaskPreview) | lab 실제 | **정본=lab**. 302 iOS에 native module 추가. 풀페이스 anchor는 현재 302/Unity 경로에서 제공 가능한지 선검증 후 lips 기반 추출 책임을 lab 방식으로 확장 |
| Unity 프로젝트 | `apps/unity/MakeupAR`(8 .cs, E3/E7) | `unity/MakeupARUnityValidation`(5 .cs) | 둘 다 실제 | **정본=makeupAR**(사용자 지침: AR 충돌은 makeupAR 기준). 302 비충돌 추가분만 선택 이식 |

## 3. 보존 대상 전수 목록 (= 옮겨야 할 makeupAR 엔진 표면)

회귀 금지 대상. 각 항목은 "착지점 + 위험"과 함께.

1. **`packages/lip-generate-core`** (순수 TS: contracts/reducer/payloadBuilder/validationGates/fixtureInventory) → 302 `packages/shared-contracts` 또는 `apps/mobile/src`로. **위험 낮음**(프레임워크 무관).
2. **`e7PersonalizedGeneratePipeline.ts`** (생성 엔진: buildGeneratedLipPackage, buildGeneratedLipCandidateSet, smoothLipBoundaryCurveDensified, buildUvMaskRawRgba, buildCaptureSetBlendUvMask, encodeBase64) → 302 face-analysis/ar feature. **위험 중**(Uint8Array/base64 동작 확인).
3. **iOS native `E7NativeLipBoundaryProviders`** (extractLipBoundary/saveGeneratedPackage/renderLipMaskPreview, MediaPipe) → 302 iOS. **위험 높음**: lip 전용 provider 스택에서 4-region anchor/asset 경로 확장과 `extractLipBoundary` 사용 경계가 누락되지 않도록 선검증.
4. **embedded Unity (`@azesmway`) + RNBridge/ApplyRecipeJson/UnityEventPayload** → 302 Expo. **위험 최상**: 302가 Unity를 앱에 박는 native 통합이 없음.
5. **Unity 프로젝트(smooth-region-mask, E3RegionMaskOverlay 등)** → 302 `apps/unity/MakeupAR`와 수렴. **위험 중**: 정본/리소스 id 충돌.
6. **App.tsx 흐름 로직**(마법사 상태머신, apply/ack 재시도, validation 컨트롤의 *제품용 부분*) → 302 화면에 이식. **위험 중**: 상태머신 누락 시 적용 흐름 깨짐.
7. **Full-face 4-region 작업(F1 — lip만 이식하고 "완료" 오인 금지)** — `lip/blush/brow/eyeliner` canonical id, `E7_FULL_FACE_REGION_RUNTIME_LAYERS`, `postFullFaceRegionPackage`, region별 조정 필드(brow detail/spread/offset/arch, blush, eyeliner 포함) → 302. (대부분 코드에 이미 존재하므로 *명시* 차원) **위험 중**.
8. **Region 에셋** — brow PSD(`psd-arcore-brow-semi-arch-v1`), blush cheek UV(`e7-blush-balanced-uv-v0`), eyeliner provisional(`e7-eyeliner-minimal-safe-uv-v0`), lip 마스크 + `Resources/SmoothRegionMasks` → makeupAR 정본. **위험 중**: 302 `SourceMasks`엔 Lip만 존재.
9. **Recipe/조정 계약** — `ApplyRecipeJson` recipe layer(region별 `enabled`/`color`/`opacity`/`intensity`/`maskTextureId`/`candidateId`/`params`) + finish/tuning + **AR 인라인 재조정** + Unity ack 계약 → 302. **위험 중**: region 파라미터 스키마 누락 시 표현력 손실.

## 4. 핵심 기술 리스크 (회귀 직결)

1. **Expo + embedded Unity (최우선)** — 302는 Expo, lab은 bare RN의 `@azesmway`. Unity를 302 앱에 박으려면 **Expo prebuild + dev-client + config plugin**(또는 bare 전환) + `UnityFramework` 동기화 필요. 잘못되면 **AR 렌더 전체가 죽음**.
2. **iOS native module 유지** — extractLipBoundary/saveGeneratedPackage가 Expo prebuild 후에도 살아야 함.
3. **촬영 소스(확정)** — 마스크 생성 source of truth = **Unity synchronized capture(frame+arFaceExport)**. expo-camera 사진은 face-analysis 진입 컨텍스트일 뿐. 즉 진입 후 **AR capture가 한 번 더 필요** → `USER_FLOW_REDESIGN_KO.md`의 ① 촬영(셔터)과 정합.
4. **카메라 1소비자 규칙** — 한 시점에 expo-camera / RealtimeFaceCaptureNativeView / Unity ARKit 중 **하나만** 카메라 점유(iOS 세션 경합 = "되던 게 안 됨" 단골).
5. **계약 이중화** — MakeupFilter(프리셋) ↔ FullFaceMakeupRecipe(생성). 둘을 잇되 프리셋 흐름도 안 깨지게.
6. **RN 버전차(0.86 vs 0.85.3) / TS(5 vs 6)** — 의존성 정렬.

## 5. 통합 마일스톤 (선행조건 → 순서)

우선순위 P0=보호선, P1=핵심 통합, P2=안정화, P3=실기기.

| M | P | 목표 | 완료 기준 |
|---|---|---|---|
| N0 | P0 | 두 repo baseline + 보존 대상 동결 | 302 repo 작업 디렉토리/브랜치 분리 확인, lab 엔진 표면 4-region (lip/blush/brow/eyeliner) 목록 확정, lip baseline 및 302 preset baseline 보호 동시 고정 |
| N1 | P0 | **Unity 정본 결정(=makeupAR)** | §10 Unity 머지표를 실값으로 채움(파일/리소스/id 승자·migration) |
| N2 | P0 | **계약 정렬(full-face)** | `FullFaceMakeupRecipe`(4-region)를 shared-contracts에, lip은 region payload로, MakeupFilter↔recipe 매핑 |
| N3 | P1 | **엔진 순수 TS 이식** | full-face 계약으로 정렬한 `FullFaceMakeupRecipe` builder + region 조정 스키마(data-driven) + `mask/asset registry` + alias mapper가 302에서 typecheck/단위테스트 통과 |
| N4 | P1 | **Expo embedded Unity 스파이크 (buildless + pre-device)** | N4a UnityView 표시 / N4b RNBridge ApplyRecipeJson ack / N4c **4-region** recipe dispatch / N4d generated UV texture + Resources mask 로드 + arface_export.json 스키마 round-trip |
| N5 | P1 | **iOS native module 이식** | extractLipBoundary/saveGeneratedPackage가 302 prebuild에서 동작 |
| N6 | P1 | **얼굴분석→생성 seam 배선** | FaceAnalysisReportDetail 진입 → Unity capture → **4-region** 생성→조정→저장→AR 적용 1회 관통 |
| N7 | P2 | **302 화면에 엔진 연결 + 디자인 통일** | (a) AR 하단 시트에서 **4 region별 ON/OFF·color·intensity·schema-driven params 변경 → ApplyRecipeJson → Unity ack → 화면 반영**, (b) Tamagui 테마, (c) **제품 경로 copy/flag scan**(provisional/MediaPipe/Generate/provider/debug/hot/경계 보기/진하게 보기 미노출; 임시 표기 필요 시 제품 언어로 노출) |
| N8 | P2 | **회귀 검증** | (a) 생성-마스크 경로 1개 + 프리셋 MakeupFilter 경로 1개 각각 관통 smoke, (b) lab 기능 전수 체크리스트, (c) 302 기존 흐름 미파손 |
| N9 | P3 | phone-connected | N4e **ARFace attachment smoke**(실기기 필수) + face attachment/boundary/visual/FPS/thermal + 사용자 시각 합격 |

> **N4는 통째 통합 전 "스파이크"로 먼저** — Expo에 Unity가 박히는지부터 증명해야 나머지가 의미 있음. 여기서 막히면 즉시 보고(아래 stop rule).

## 6. Stop rules

- Expo에 embedded Unity가 dev-client/prebuild로도 안 박힘 → 보고(아키텍처 결정 필요: bare RN 전환 여부).
- 현재 cwd가 `~/Desktop/makeupAR`인 상태에서 302 제품 코드를 구현하려 함 → 중단. `~/Desktop/MAKEUPAPP/302-group5-final-project`의 통합 브랜치로 이동 후 진행.
- 302 캡처 스키마와 `extractLipBoundary` 입력 계약 불일치(포맷/좌표계) 또는 카메라 세션 전환 충돌 → 보고.
- Unity 정본 충돌(같은 마스크 id 다른 의미) → 보고.
- lab에서 되던 생성/적용이 302에서 재현 안 됨 → 즉시 중단·보고(회귀).

## 7. 완료 정의 (3단계 게이트 — 과장 금지)

실기기 없이 "전 기능 재현"은 과장이므로 게이트를 분리한다.

### 7.1 `pre-device integration ready` ← 이 문서의 1차 목표
- makeupAR **4-region** 생성/조정/저장 + recipe/ack 로직이 302 코드에서 typecheck/단위/batchmode smoke 통과.
- 진입이 FaceAnalysisReportDetail에서 이어짐.
- 표현력/조정(색·finish·광택·질감·모양·candidate·**region별**)이 한 개도 안 빠짐(코드/계약 수준).
- 프리셋 흐름 회귀 0(스모크) + 제품 경로 copy/flag scan 통과.

### 7.2 `phone-installed`
- 302 dev-client가 실기기 설치 + embedded Unity 기동. 생성→AR 적용이 실기기에서 1회 관통.

### 7.3 `visual-flow-accepted`
- 실기기 시각 검증(face attachment/boundary/motion/FPS 등) + 사용자 주관 합격.
- UI/UX 302 디자인 통일 확인.

> 이 문서 범위의 "완료" = **최대 7.1(pre-device)**. 7.2/7.3은 phone-connected gate(N9). 7.1을 "전 기능 재현/제품 완료"로 표기 금지.

## 8. 미확인(다음 검증 필요)

- 302 `unityMakeupBridge`가 stub임은 **확인됨**(NativeModules.UnityMakeupBridge 부재 시 `fallback-log` 콘솔만).
- 302 `apps/unity/MakeupAR` 실제 빌드 여부 — 미확인(스크립트는 8개 존재, Unity 에디터 빌드 확인 필요).
- 302 ARFilterShapeAdjust는 `LiveCameraLayer`(expo-camera 오버레이) 기반 — **확인됨**(Unity 아님).
- 두 Unity `E3RegionMaskOverlay.cs` 실제 라인 단위 diff — 미확인(크기만 대조: 302 3357 vs lab 1886).
- 302 `E7SynchronizedCaptureExporter`의 `arface_export.json` 스키마가 lab `extractLipBoundary` 입력과 일치하는지 — 미확인(파일 존재는 확인).

## 9. 정밀 리스크 + 보완책 (전수)

심각도: 🔴 Blocker / 🟠 Major / 🟡 Minor. 각 항목 = 증상·근거 → 보완책 → 검증.

> **전역 결정 규칙(사용자 지침): AR 관련 충돌은 전부 `makeupAR`를 기준(정본)으로 둔다.** Unity 렌더, 브리지, 캡처/생성, region 처리 등 AR 동작이 갈리면 makeupAR가 이긴다. 302의 AR쪽 코드(구조 포함)는 makeupAR와 충돌하지 않는 부분만 선택적으로 얹는다.

### 🔴 P1. Expo-prebuilt iOS에 네이티브 3종 영속 이식
- **근거:** 302 `ios/Podfile.lock`에 MediaPipe/Unity/@azesmway 전무. lab은 `pod MediaPipeTasksVision 0.10.35` + `@azesmway/react-native-unity`(embedded UnityFramework) + `scripts/apply-rn-unity-timing-fix.js`(RNUnityView.mm 패치, 실패 시 Podfile raise) + `USE_FRAMEWORKS` 필요.
- **보완책:** 302는 prebuilt(bare) iOS이므로 **expo config plugin**으로 (a) MediaPipeTasksVision pod 추가, (b) @azesmway pod + UnityFramework 동기화(`scripts/build_m3_unityframework.sh` 재사용), (c) RNUnityView 타이밍 패치, (d) USE_FRAMEWORKS linkage를 prebuild에도 영속화. 서명팀(WSLFBT6QHB)·iOS 전용 설정 유지.
- **prebuild source-of-truth 결정(F9 — 먼저 확정):** 302가 이미 `ios/`를 커밋한 상태이므로 **둘 중 하나로 정함**: (1) `ios/`를 정본으로 직접 커밋 관리(네이티브 변경을 손으로) vs (2) **config plugin + `expo prebuild` 재생성을 정본**(`ios/`는 산출물). 권장 (2)+: 네이티브 설정=config plugin, **UnityFramework 대형 바이너리는 git 밖**에서 `build_m3_unityframework.sh`로 동기화. 이 결정 없으면 prebuild마다 Unity/Framework가 깨짐.
- **검증:** prebuild → pod install → 빈 UnityView 1개 띄우기 = N4a.

### 🔴 P2. 촬영 입력 계약(framePath + arFaceExportPath)
- **근거:** lab `extractLipBoundary`는 `framePath`(frame.png) + `arFaceExportPath`(arface_export.json) 쌍을 요구(App.tsx 2273~2274). 이 쌍은 Unity `E7SynchronizedCaptureExporter`가 capture 디렉터리에 씀.
- **완화 사실:** **302 Unity에 `E7SynchronizedCaptureExporter.cs`가 이미 존재** → ARFace export 생성 능력은 결손이 아니라 배선 문제.
- **보완책:** 마스크 생성은 expo-camera 사진이 아니라 **embedded Unity의 synchronized capture 경로를 사용**(lab과 동일). expo-camera 촬영은 face-analysis 리포트용으로 분리 유지. 두 capture 공존.
- **검증:** 302 Unity가 만든 `arface_export.json` 스키마를 lab `parseRequest`가 그대로 먹는지 1회 round-trip(N4에 포함).

### 🔴 P3. Unity 프로젝트 분기 (정본 결정 + full-face 이식)
- **근거:** 302 Unity가 구조적으로 더 진화(8 스크립트: MakeupRegionRendererRoutes/MakeupRegionDebugControls/E7VisionLipBoundaryRuntime 추가; E3RegionMaskOverlay 3357줄). **그러나 region 네이밍이 cheek/eye이고 blush/eyeliner full-face 작업이 없음.** lab은 full-face(blush/eyeliner) 작업 보유하나 스크립트 5개·구조 단순.
- **보완책(사용자 지침 반영 — AR 정본=makeupAR):** **makeupAR Unity를 AR 정본으로 채택**하여 302로 가져간다. 302 Unity의 추가 스크립트(MakeupRegionRendererRoutes/MakeupRegionDebugControls/E7VisionLipBoundaryRuntime)와 더 큰 E3RegionMaskOverlay는 **makeupAR 동작과 충돌하지 않는 범위에서만** 선택 이식(충돌 시 makeupAR가 이김). full-face(blush/brow/eyeliner) 마스크·SourceMasks는 makeupAR 것이 정본. 302 `apps/unity/MakeupAR`는 makeupAR Unity로 대체/정렬.
- **주의:** 이 결정으로 302 Unity의 구조적 개선(렌더러 라우트 등)을 일부 포기할 수 있음 — 필요한 것만 makeupAR 위에 재적용.
- **검증:** 네 region 모두 makeupAR 기준 Unity에서 dispatch 로그 + 마스크 렌더(batchmode smoke).

### 🟠 P4. region 네이밍 충돌
- **근거:** lab canonical `lip/blush/brow/eyeliner` vs 302 `lip/cheek/brow/eye`(+base/contour). 302 Unity·브리지 전부 cheek/eye 사용.
- **보완책:** canonical = `lip/blush/brow/eyeliner`(full-face 런북 결정)로 통일하고 **`cheek→blush`, `eye→eyeliner` 단방향 legacy alias**를 한 곳(계약 layer)에만 둠. base/contour는 당장 미사용으로 표시.
- **검증:** 같은 id가 두 의미로 안 쓰이는지 계약 게이트.

### 🟠 P5. recipe 생성 경로 이중성
- **근거:** 302 = 프리셋(MakeupFilter) 선택→recipe(`createUnityMakeupRecipeBatchFromARFilterSelection`). lab = 생성 마스크→recipe.
- **보완책:** **생성-마스크 경로를 1차 경로로 추가**하고 프리셋 경로는 보조로 유지(둘 다 같은 `ApplyRecipeJson` 계약으로 수렴). 프리셋 흐름 회귀 없게.
- **검증:** 생성/프리셋 둘 다 AR 적용되는지.

### 🟠 P6. 브리지 추상화 차이
- **근거:** 302 `NativeModules.UnityMakeupBridge`(미구현 stub) vs lab `@azesmway` UnityView + `postMessage('RNBridge','ApplyRecipeJson')`. RNBridge GameObject는 양쪽 Unity 공통.
- **보완책:** **@azesmway UnityView를 정본 브리지로** 채택(검증됨). 302 `unityMakeupBridge.ts`의 recipe 빌드 로직(계약/프리셋)은 살리되, 전송부는 @azesmway postMessage로 교체.
- **검증:** ApplyRecipeJson 왕복 + UnityEvent ack 수신.

### 🟡 P7. 버전/설정 차이
- **근거:** RN 0.86 vs 0.85.3, TS 5 vs 6, 서명팀 9G4K6N63MK vs WSLFBT6QHB, 302 iOS 전용.
- **보완책:** 302 기준(0.85.3/TS6/WSLFBT6QHB/iOS)에 lab 코드를 맞춤. @azesmway·MediaPipe의 RN 0.85 호환 확인.
- **검증:** typecheck/pod install 통과.

### 🟡 P8. 중복 네이티브 얼굴캡처
- **근거:** 302 `RealtimeFaceCaptureNativeView`(landmark) vs lab Unity ARKit capture. 같은 목적 다른 구현.
- **보완책:** 역할 분리 + **카메라 1소비자 규칙** — 한 시점에 expo-camera(face-analysis) / RealtimeFaceCaptureNativeView / Unity ARKit 중 **하나만** 카메라 점유. 마스크 생성·AR 구간은 Unity가 점유, 진입/해제 시 명시적으로 release. 중복 기능은 하나로 정리(우선 공존, 후속 통합).
- **검증:** face-analysis → 마스크 생성(Unity) 전환 시 카메라 세션 충돌/검은 화면/freeze 없는지 1회 전환 smoke.

### 통합 우선순위 (보완책 반영)
P1·P2·P3가 N4 스파이크(N4a~d, buildless)의 3대 증명 대상. ARFace **실기기 attachment**(N4e)는 N9 phone gate로 분리(buildless 증명 불가). 이 셋이 통과해야 나머지(P4~P8)는 코드 정합 수준으로 처리 가능.

## 10. 부록 — Unity 머지 결정표 (N1 산출물 템플릿)

AR 정본=makeupAR. 아래를 N1에서 실값으로 채운다(단순 한쪽 덮어쓰기 금지, 라인 단위 diff 후).

| file/resource | 302 의미 | makeupAR 의미 | 결정 | id migration | smoke 증거 |
|---|---|---|---|---|---|
| `E3RegionMaskOverlay.cs` | 3357줄 | 1886줄, full-face | **makeupAR 기준** + 302 비충돌분 선택 | — | region dispatch 로그 |
| `MakeupRegionRendererRoutes.cs` | 렌더러 라우트 | 없음 | 비충돌 시 선택 이식 | — | 렌더 경로 |
| `MakeupRegionDebugControls.cs` | 디버그 | 없음 | **제품 미노출**(dev only) | — | — |
| `E7VisionLipBoundaryRuntime.cs` | vision boundary | App native 경로로 처리 | 충돌 검토 후 결정 | — | boundary 산출 |
| `E7SynchronizedCaptureExporter.cs` | 존재 | 존재(생성 입력 생산) | **makeupAR 기준** | — | arface_export round-trip |
| `RNBridge.cs` | 공통 | 공통 | 계약 통일 | — | ApplyRecipeJson ack |
| `Resources/SmoothRegionMasks` | lip 위주 | 4-region | **makeupAR** | `cheek→blush`,`eye→eyeliner` | 마스크 로드 |
| `SourceMasks` | Lip만 | 4-region(blush/brow/eyeliner 포함) | **makeupAR** | — | — |
