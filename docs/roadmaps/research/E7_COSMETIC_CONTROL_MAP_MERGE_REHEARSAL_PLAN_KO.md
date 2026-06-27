# E7 Cosmetic Control Map Merge Rehearsal Plan

Status: review / rehearsal plan only  
Do not treat this as the active implementation plan.  
Do not switch the current working tree onto an integration branch while the tracking app flow is still in progress.

## 1. 목적

이 문서는 현재 추적 앱 흐름 개발을 멈추지 않으면서, 별도 Codex thread / 별도 worktree에서 `blush-mask` 브랜치와의 통합 가능성을 반복 실험하기 위한 모의병합 계획이다.

목표는 본류에 바로 합치는 것이 아니라 아래를 미리 확인하는 것이다.

- 화장품팀의 RN recipe / Unity bridge / renderer / shader / mask asset 계약이 우리 런타임 생성 마스크와 어떻게 만나는지 확인한다.
- 실제 merge conflict가 나는 파일과 개념 충돌을 분리한다.
- `alpha-only mask`가 아니라 `RGBA cosmetic control map`을 생성해야 하는 지점을 명확히 한다.
- 현재 추적 앱 흐름 브랜치를 보호하면서, 나중에 가져올 수 있는 작고 검증 가능한 통합 단위를 만든다.

## 2. 기준 입력

### 2.1 현재 로컬 작업공간

현재 로컬 브랜치는 추적 앱 흐름과 region generate 작업이 진행 중인 작업공간이다. 이 작업공간에서는 브랜치 전환, 정면 merge, scene/project 대량 변경을 하지 않는다.

현재 작업공간의 역할:

- 사용자 맞춤 capture / generate / adjust / save / AR apply 흐름을 계속 개발한다.
- 필요한 경우 통합 실험 결과에서 검증된 작은 adapter 또는 schema만 선별 반영한다.

### 2.2 화장품팀 기준 브랜치

기준 브랜치:

```txt
repository: nicewei77-lang/makeupAR
branch: blush-mask
latest checked SHA: 605e00adb07bb1e10155b743a5a47df6da6e5902
checked at: 2026-06-27
```

실제 integration thread를 시작할 때는 반드시 최신 SHA를 다시 확인하고, 그 세션의 기준 SHA를 문서/로그에 기록한다.

## 3. 핵심 판단

화장품팀 브랜치는 단순히 미리 만든 PNG 몇 개를 쓰는 구조가 아니다.

```txt
RN recipe
-> maskTextureId
-> RGBA control map
-> RNBridge parser
-> E3RegionMaskOverlay material binding
-> SmoothRegionMask shader
```

따라서 통합의 중심은 `pre-made mask asset을 runtime mask로 교체`가 아니라 아래 계약을 맞추는 것이다.

```txt
runtime-generated RGBA control map
-> same _MaskTex contract
-> existing cosmetic shader expression
```

우리 런타임 생성기는 단순 흑백/알파 마스크가 아니라 화장품 shader가 기대하는 채널 의미를 생성해야 한다.

### 3.1 cheek / blush control map

```txt
R = soft blush alpha
G = reserved / 0
B = center or density map
A = soft blush alpha
```

### 3.2 lip control map

```txt
R = full lip alpha
G = overline alpha
B = gradient density
A = gloss highlight
```

## 4. Region 계약

제품/생성 관점과 화장품 renderer 관점을 분리한다.

### 4.1 Product / generate region

```txt
lip
cheek
brow
eyeliner
```

`blush`는 제품/스타일 이름으로는 유지할 수 있지만, Unity payload와 화장품 renderer 계약에서는 `cheek`로 alias한다.

### 4.2 Cosmetic renderer v1 layer

`blush-mask` 브랜치 기준 runtime layer는 아래 3개로 묶여 있다.

```txt
lip
cheek
eye
```

따라서 1차 통합에서는 `lip + cheek`만 실제 cosmetic renderer에 연결한다.

```txt
included in merge rehearsal:
  lip
  cheek

extension only:
  brow
  eyeliner
```

`brow`와 `eyeliner`는 generated package / future UI / contract에는 남길 수 있지만, 이번 모의병합의 Green 조건에는 넣지 않는다. 이 둘을 처음부터 화장품 renderer에 강제로 연결하면 3-layer parser, eye layer, shader mode, QA 범위가 동시에 흔들린다.

## 5. 브랜치 운영

### 5.1 현재 브랜치에서는 하지 않을 것

- `git switch`로 작업 브랜치를 바꾸지 않는다.
- `blush-mask`를 현재 작업공간에 직접 merge하지 않는다.
- 현재 dirty changes를 stash/revert/reset하지 않는다.
- Unity scene, ProjectSettings, evidence 전체를 현재 작업공간에 들여오지 않는다.

### 5.2 별도 thread / worktree

새 Codex thread는 별도 worktree에서 실행한다.

권장 이름:

```txt
thread purpose: E7 cosmetic control map merge rehearsal
branch/worktree: codex/blush-mask-merge-rehearsal
```

이 thread의 역할은 본류 반영이 아니라 통합 실험이다.

```txt
1. blush-mask latest SHA 확인
2. 별도 worktree에서 merge rehearsal
3. conflict map 작성
4. lip + cheek only integration candidate 작성
5. buildless tests 실행
6. 본류에 가져올 최소 단위 제안
```

### 5.3 worktree의 실제 영향

`git worktree`는 현재 checkout의 파일과 브랜치를 바꾸지는 않지만, 같은 git repository 안에 별도 worktree metadata와 새 branch ref를 만든다. 따라서 현재 앱 작업 흐름에는 거의 영향을 주지 않지만, "원본 repo metadata도 건드리지 않는" 수준의 격리가 필요하면 별도 clone을 써야 한다.

권장 판단:

```txt
일반 모의병합: 별도 worktree
원본 .git metadata까지 완전 격리: 별도 clone
현재 작업 파일/브랜치 보호: 둘 다 가능
속도와 저장공간: worktree가 유리
```

### 5.4 현재 WIP 포함 정책

모의병합 기준은 먼저 현재 브랜치의 committed HEAD로 고정한다. 현재 worktree의 미커밋 WIP까지 포함하면 실제 작업 흐름과 통합 실험이 섞여서 원인 분석이 어려워진다.

필요한 경우에만 2차 실험으로 현재 WIP diff를 별도 patch로 복사해 적용한다.

```txt
pass 1: committed HEAD vs blush-mask
pass 2 optional: committed HEAD + selected WIP patch vs blush-mask
never: original worktree에서 stash/reset/switch로 WIP 정리
```

## 6. 멀티 에이전트 역할 분리

각 agent는 같은 repo를 보더라도 서로 다른 질문에 답한다. 한 agent가 전체 병합을 다 떠안지 않게 한다.

### Agent A. Contract Mapper

질문:

- `blush-mask`의 RN recipe schema는 무엇인가?
- `maskTextureId`, `textureSample`, `styleId`, shader mode는 어떻게 매핑되는가?
- 우리 `RegionMaskPackage`와 어떤 필드가 맞고 어떤 필드가 빠져 있는가?

산출물:

```txt
contract_map.md
cosmetic_control_map_schema.json
field_gap_table.md
```

중점 파일:

```txt
rn/MakeupARValidation/App.tsx
unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs
docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md
```

### Agent B. Renderer / Shader Diff Reviewer

질문:

- `SmoothRegionMask.shader`에서 RGBA 각 채널은 실제로 어떻게 쓰이는가?
- `_SecondaryColor`, `_GradientAmount`, `_LipStyleMode`, `_CheekBlushMode`, `_PigmentMultiply`가 어떤 표현을 만든다?
- 우리 로컬 shader와 충돌 없이 가져올 수 있는가?

산출물:

```txt
shader_diff_notes.md
required_shader_properties.md
do_not_guess_shader_changes.md
```

중점 파일:

```txt
unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader
unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMaskMaterial.mat
unity/MakeupARUnityValidation/Assets/Editor/SmoothRegionMaskTextureImporter.cs
```

### Agent C. Runtime Mask Provider Designer

질문:

- runtime-generated texture를 기존 `_MaskTex`에 넣으려면 어떤 registration path가 필요한가?
- `raw_rgba_base64`, Resources asset, saved package, Unity-side Texture2D 생성 중 어떤 경로가 1차 통합에 안전한가?
- static fallback과 dynamic runtime mask를 같은 interface로 다룰 수 있는가?

산출물:

```txt
runtime_mask_provider_design.md
fallback_policy.md
dynamic_texture_id_policy.md
```

중점 파일:

```txt
unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs
unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs
rn/MakeupARValidation/src/e7PersonalizedGeneratePipeline.ts
packages/lip-generate-core/src/contracts.ts
```

### Agent D. Merge Conflict Scout

질문:

- 실제 merge를 하면 어떤 파일에서 textual conflict가 나는가?
- textual conflict가 없더라도 semantic conflict가 나는 곳은 어디인가?
- scene/project/evidence 변경 중 버려야 할 것은 무엇인가?

산출물:

```txt
merge_conflict_map.md
files_to_accept_from_blush_mask.md
files_to_keep_from_current.md
manual_resolution_notes.md
```

중점 파일:

```txt
rn/MakeupARValidation/App.tsx
unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs
unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs
unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader
unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/
```

### Agent E. Buildless Verification Owner

질문:

- iPhone build 없이 어떤 검증을 먼저 통과해야 하는가?
- fixture로 static mask와 generated control map을 비교할 수 있는가?
- 어떤 실패를 runtime test 전 Red/blocked로 봐야 하는가?

산출물:

```txt
buildless_test_matrix.md
fixture_comparison_plan.md
runtime_gate_checklist.md
```

중점 검증:

```txt
TypeScript typecheck
RN lint
Unity batchmode compile/import
shader/material property presence
mask asset import settings
RGBA channel diagnostics
fixture contact sheet comparison
```

## 7. 예상 충돌 파일

### 7.1 High risk

```txt
rn/MakeupARValidation/App.tsx
unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs
unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs
unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader
unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMaskMaterial.mat
unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/*.png
```

이 파일들은 textual conflict와 semantic conflict가 모두 예상된다.

### 7.2 Medium risk

```txt
unity/MakeupARUnityValidation/Assets/Editor/SmoothRegionMaskTextureImporter.cs
rn/MakeupARValidation/__tests__/App.test.tsx
unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs
```

### 7.3 Avoid by default

```txt
unity/MakeupARUnityValidation/Assets/Scenes/*.unity
unity/MakeupARUnityValidation/ProjectSettings/*.asset
evidence/**
unity-builds/**
rn/MakeupARValidation/ios/Pods/**
```

이 파일들은 명시적 이유 없이 통합 산출물에 포함하지 않는다.

## 8. 사전 정렬 원칙

현재 작업 브랜치에 미리 반영해도 되는 것은 기능 선반영이 아니라 통합면 정리다.

허용:

```txt
blush -> cheek alias 정책 문서화
controlMapSchema / channelSchema 필드 설계
runtime-generated maskTextureId naming policy
static fallback 정책
lip + cheek first scope
brow / eyeliner extension only 정책
```

비허용:

```txt
화장품 shader 예측 구현
RNBridge 대수술
E3RegionMaskOverlay 대수술
Unity scene 변경
ProjectSettings 변경
brow/eyeliner cosmetic renderer 완전 연결
실기기 evidence 없는 Green/product-quality 주장
```

## 9. Integration branch에서의 실제 merge 절차

### Step 1. 기준 고정

```txt
record current local branch SHA
record blush-mask HEAD SHA
record dirty status of original workspace
```

### Step 2. 별도 worktree 생성

현재 작업공간을 건드리지 않는 별도 worktree에서 실행한다.

### Step 3. merge rehearsal

`blush-mask`를 실제 merge하거나 필요한 경우 cherry-pick / file-level apply를 비교한다.

기록할 것:

```txt
conflicted files
auto-merged files
semantic conflicts
discarded files
manual choices
```

### Step 4. 1차 통합 범위 제한

최초 성공 조건은 아래로 제한한다.

```txt
lip static cosmetic atlas works
cheek static cosmetic atlas works
runtime-generated cheek/lip RGBA control map can be accepted by the same path
static fallback remains available
3-layer cosmetic renderer still works
```

### Step 5. buildless verification

실기기 build 전 아래를 통과해야 한다.

```txt
RN TypeScript check
RN lint
Unity compile/import
shader property smoke
maskTextureId whitelist / dynamic registry smoke
RGBA channel diagnostic smoke
fixture contact sheet or expected render comparison
```

### Step 6. report back

integration branch는 아래 보고서만 본류에 제안한다.

```txt
what merged cleanly
what conflicted
what was intentionally deferred
which files are safe to port back
which files must wait for tracking app flow completion
next build gate question
```

## 10. 성공 기준

모의병합 성공은 product-quality 성공이 아니다.

성공:

```txt
conflict map complete
lip + cheek cosmetic renderer path compiles
RGBA control map contract documented
static fallback preserved
runtime-generated texture insertion path identified or smoke-tested
current tracking app branch remains untouched
```

부분 성공:

```txt
merge conflict map complete
but shader/RNBridge/E3 integration does not compile yet
or runtime-generated texture insertion path is design-only
```

실패:

```txt
current working tree was disrupted
scene/project/evidence churn dominates the integration
lip/cheek renderer requires abandoning current tracking app flow
RGBA channel contract remains unclear
```

## 11. 실기기 gate

이 문서의 범위는 buildless merge rehearsal이다. iPhone build/install/runtime evidence는 별도 승인 gate에서만 진행한다.

실기기 gate 질문은 아래 형식으로 별도 보고한다.

```txt
Build question:
  별도 integration branch에서 UnityFramework/RN iPhone build를 진행할까요?

Primary path:
  runtime-generated RGBA control map -> cosmetic _MaskTex -> ARFace UV renderer

Compare paths:
  static blush-mask asset
  runtime-generated lip/cheek control map
  fallback static asset

Quality gate:
  face attachment
  boundary accuracy
  density/gradient/gloss preservation
  makeup visibility
  FPS/frame-time
  latency
  memory/thermal
```

## 12. 마지막 누락 방지 체크

모의병합 thread가 시작되기 전에 아래가 빠지면 안 된다.

```txt
source branch SHA
target/local branch SHA
original worktree dirty status
worktree or clone isolation choice
exact file allowlist / blocklist
copied asset allowlist
runtime RGBA channel contract
static fallback contract
buildless test command list
abort criteria
report-back template
```

중단 조건:

```txt
original worktree branch switch가 필요함
original dirty changes stash/reset/revert가 필요함
Unity scene / ProjectSettings / build cache 대량 반입이 필요함
raw camera frame, signing material, secret, build cache 공유가 필요함
iPhone build/install/launch가 필요함
brow/eyeliner를 lip/cheek와 같은 완성도로 연결해야만 성공이라고 주장함
```

이 중단 조건 중 하나라도 걸리면 병합 실험을 멈추고 `blocked` 또는 `partial`로 보고한다.

## 13. 별도 Codex thread 시작 프롬프트

아래 프롬프트를 새 Codex thread에 그대로 줄 수 있다.

```txt
여기는 makeupAR E7 cosmetic control map merge rehearsal 전용 thread다.

목표:
- 현재 추적 앱 흐름 작업공간을 건드리지 않는다.
- 별도 worktree/branch에서 nicewei77-lang/makeupAR blush-mask 최신 브랜치와의 모의병합을 수행한다.
- 제품 반영이 아니라 conflict map, adapter strategy, buildless verification 결과를 만든다.

필수 읽기:
1. AGENTS.md
2. TECH_VALIDATION_RESULT.md > Current Session Snapshot / Next Milestone Boundary
3. docs/roadmaps/README.md
4. docs/roadmaps/research/E7_COSMETIC_CONTROL_MAP_MERGE_REHEARSAL_PLAN_KO.md
5. docs/roadmaps/active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md

기준:
- blush-mask 최신 SHA를 먼저 다시 확인하고 기록한다.
- 1차 integration scope는 lip + cheek only다.
- product/generate region은 lip / cheek / brow / eyeliner로 보되, cosmetic renderer v1은 lip / cheek / eye 3-layer를 유지한다.
- brow / eyeliner는 extension only다.
- alpha-only가 아니라 RGBA control map contract를 맞춘다.

금지:
- 현재 원본 worktree 브랜치 전환
- raw camera frame upload
- live face parsing/Core ML runtime 도입
- Unity scene / ProjectSettings / evidence 전체 수용
- iPhone build/install/launch
- product-quality Green 주장

산출물:
- merge_conflict_map.md
- contract_map.md
- runtime_mask_provider_design.md
- buildless_test_matrix.md
- final_rehearsal_summary.md
```
