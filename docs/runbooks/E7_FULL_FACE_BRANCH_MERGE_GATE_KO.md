# E7 Full-Face Branch Merge Gate

작성일: 2026-06-30 KST

## 1. 목적

이 문서는 `병합용브랜치`를 기준으로 `blush-mask`, `feature/brow-0626` 브랜치의 에셋, 파라미터, 스키마, 렌더링 계약을 선별 이식하기 위한 통합 병합 계획이다.

최종 목표는 기존 사용자 맞춤형 `generate -> adjust -> save package -> AR handoff` 흐름을 유지하면서 `lip`, `blush`, `brow`, `eyeliner` 네 부위가 모두 pre-Xcode 단계에서 작동 확인 가능한 상태가 되는 것이다.

이번 병합 완료 기준은 Xcode/iPhone 실기기 검증이 아니다. 이번 완료 기준은 buildless 검증, package/schema 검증, RN/Unity 정적 검증, Unity batchmode smoke, pre-Xcode gate 통과다. iPhone visual acceptance는 다음 phone-connected gate로 남긴다.

## 2. 확정된 제품 결정

### 2.1 Canonical region

최종 canonical region 이름은 다음 네 개로 고정한다.

| Region | 의미 | Primary source |
| --- | --- | --- |
| `lip` | 입술 사용자 맞춤형 마스크 | MediaPipe |
| `blush` | 블러셔가 올라갈 cheek 영역 | 팀원 cheek UV mask + 사용자 조정 |
| `brow` | 눈썹 asset 부착 영역 | MediaPipe brow anchor + 팀원 brow asset |
| `eyeliner` | 아이라인 asset fit 기준선 | MediaPipe upper eyelid boundary |

`cheek`, `eye`, `eyeline`, `eyebrow`는 신규 package의 canonical 이름으로 쓰지 않는다. 기존 코드 호환이 필요한 경우에만 legacy alias로 유지한다.

### 2.2 Provider policy

| Region | Runtime/generate policy |
| --- | --- |
| `lip` | MediaPipe 고정. Apple Vision은 UI에 노출하지 않는다. |
| `blush` | 팀원 cheek UV mask를 기본으로 쓰고, ARFace/UV 기반 스케일과 사용자 조정으로 맞춘다. |
| `brow` | MediaPipe는 위치/회전/스케일 anchor만 담당하고, 실제 모양/색/질감은 팀원 brow asset이 담당한다. |
| `eyeliner` | 이번 병합에서는 MediaPipe upper eyelid boundary만 저장한다. 최종 eyeliner asset은 전문가 팀원 산출물을 추후 fit한다. |

Apple Vision은 삭제하지 않는다. 다만 제품 UI에 provider 선택지로 노출하지 않고, 내부 fallback/debug 비교용으로만 유지한다.

## 3. 병합 원칙

1. `병합용브랜치`의 사용자 맞춤형 package flow를 중심축으로 둔다.
2. `blush-mask`, `feature/brow-0626`는 전체 merge하지 않고 선별 이식한다.
3. 가져올 대상은 에셋, texture id, palette, shader/material parameter, schema/validator, renderer contract다.
4. 가져오지 않을 대상은 오래된 RN validation flow, 현재 App flow를 덮는 구조, branch-specific roadmap churn, 현재 package contract와 충돌하는 임시 UI다.
5. `lip`의 기존 generate/adjust/save/apply 흐름은 regression 보호 대상으로 둔다.
6. 병합 중 한 region이 막히더라도 전체 흐름을 멈추지 않도록 region별 fallback과 warning을 명확히 남긴다.
7. 각 gate가 끝날 때 checkpoint commit을 남긴다.

## 4. 우선순위 구현 마일스톤

우선순위는 `P0`이 가장 높다. `P0`은 다음 단계 진행 전 반드시 닫아야 하는 보호선이고, `P1`은 실제 기능 병합의 핵심, `P2`는 pre-Xcode 완료도를 높이는 안정화, `P3`는 실기기 전 품질 보강이다.

이 섹션이 실행 spine이다. 병합 에이전트는 M0부터 M12까지 순서대로 진행한다. 뒤의 region별 섹션은 필드명, fallback, source-of-truth를 확인하기 위한 contract reference이며, 실행 순서를 새로 정의하지 않는다. 두 섹션이 충돌하면 이 섹션의 마일스톤, 11장 Risk Register, 12장 Gate matrix를 우선한다.

| Milestone | Priority | 목표 | 산출물 | Checkpoint |
| --- | --- | --- | --- | --- |
| M0 | P0 | 현재 브랜치 baseline 고정 | clean/dirty 분류, 보호 대상 목록 | `chore: prepare full-face merge baseline` |
| M1 | P0 | 중간 정리 | cache/generated 정리, 문서 링크 정리 | M0 commit에 포함 |
| M2 | P0 | contract inventory 작성 | region/id/schema/resource mapping 표 | runbook 업데이트 |
| M3 | P0 | source branch inventory | blush/brow에서 가져올 것/버릴 것 확정 | inventory notes |
| M4 | P1 | blush asset/contract 이식 | mask assets, gains, transforms, manifest | `feat: import blush assets and runtime contract` |
| M5 | P1 | brow asset/contract 이식 | 최신 brow asset, palette, blend params | `feat: import brow assets and mediapipe anchor contract` |
| M6 | P1 | MediaPipe full-face anchor 확장 | lip/brow/eyeliner anchor provider contract | M5 또는 M7 commit에 포함 |
| M7 | P1 | package schema/save/load 통합 | 네 region 저장/로드, fallback/warning | `feat: wire full-face personalized package flow` |
| M8 | P1 | Unity runtime 연결 | region parser, resource route, material params | M7 commit에 포함 또는 별도 commit |
| M9 | P2 | RN editor/UI 연결 | provider 미노출, 자동/직접 조정 flow | M7 commit에 포함 또는 별도 commit |
| M10 | P2 | pre-Xcode gate 검증 | RN/Unity/buildless/prebuild 결과 | `test: verify full-face pre-xcode merge gates` |
| M11 | P2 | 결과 문서 반영 | TECH_VALIDATION_RESULT, active roadmap | `docs: record full-face merge gate results` |
| M12 | P3 | phone-connected 준비 | 실기기 체크리스트, Slack stop rule | M11 commit에 포함 |

### M0. Baseline 고정

목표: 현재 `병합용브랜치`가 무엇을 보존해야 하는지 확정한다.

작업:

- `git status --short`로 dirty 상태를 확인한다.
- 변경 파일이 있으면 `핵심 기능`, `문서`, `실험 산출물`, `cache/generated`, `판단 필요`로 분류한다.
- `lip` generate/adjust/save/apply 관련 파일을 보호 대상으로 표시한다.
- baseline commit 전에는 branch merge, cherry-pick, asset copy를 하지 않는다.

완료 조건:

- 현재 branch가 병합 기준점으로 설명 가능하다.
- unrelated 변경이 병합 commit에 섞이지 않는다.
- `lip` baseline이 "건드리면 안 되는 흐름"으로 문서화된다.

중단 조건:

- dirty 파일 중 누가 만든 변경인지 불명확한 핵심 기능 변경이 있다.
- `lip` 관련 변경이 이미 깨진 상태로 보인다.

### M1. 중간 정리

목표: 병합 충돌과 리뷰 소음을 줄이되 기능 구조는 건드리지 않는다.

작업:

- repo-tracked/generated/cache 여부를 먼저 확인한 뒤 정리한다.
- 끊긴 preview/report 링크는 최종 보고서가 참조하지 않는 경우에만 정리한다.
- raw frame, 임시 mask, 대용량 build output은 curated evidence 여부를 확인한 뒤 제외한다.
- `.gitignore`가 이미 막고 있는 생성물은 commit 대상에 올리지 않는다.

완료 조건:

- 병합 대상 diff에서 cache/generated 파일이 빠진다.
- 현재 보고서와 evidence 링크가 끊기지 않는다.

중단 조건:

- 삭제 후보가 curated evidence인지 판단이 애매하다.
- 정리 작업이 RN/Unity 코드 리팩터링으로 번지기 시작한다.

### M2. Contract inventory 작성

목표: 병합 전에 "어떤 id를 어디로 연결할지"를 결정한다.

작업:

- 현재 branch의 RN package schema, saved package shape, Unity accepted regions, resource ids를 표로 적는다.
- `lip`, `blush`, `brow`, `eyeliner` canonical name을 기준으로 mapping한다.
- legacy alias는 `cheek -> blush`만 허용한다.
- `eye`는 `eyeliner` alias로 쓰지 않는다. 기존 `eye-smooth-mask-v1` 같은 resource는 명시적 임시 texture fallback으로만 남길 수 있다.
- Apple Vision은 provider registry에 남길 수 있지만 UI 선택지와 primary route에서는 제외한다.

완료 조건:

- 각 region의 package id, maskTextureId, Unity resource, renderer/material route가 표에 기록된다.
- 같은 id가 서로 다른 의미로 쓰이지 않는다.

중단 조건:

- Unity resource id 충돌이 발견된다.
- RN/package/Unity 중 하나가 canonical region 이름을 받을 수 없는 구조다.

### M3. Source branch inventory

목표: `blush-mask`, `feature/brow-0626`에서 가져올 것과 버릴 것을 파일/역할 단위로 고정한다.

작업:

- `blush-mask`에서 mask assets, density/center gain, uv transforms, validator, shader/material parameter를 찾는다.
- `feature/brow-0626`에서 최신 brow asset, palette, blend mode, detail/spread/offset parameter를 찾는다.
- 두 branch의 오래된 RN flow와 현재 App 구조를 덮는 변경은 제외 대상으로 표시한다.
- brow 최신 asset이 branch에 없으면 사용자에게 경로를 요청한다.

완료 조건:

- 각 source branch별 "copy/import 대상"과 "제외 대상"이 명확하다.
- brow asset의 최신 source of truth가 확정된다.

중단 조건:

- brow 최신 asset 위치가 불명확하다.
- source branch의 renderer contract가 현재 Unity runtime과 직접 충돌한다.

### M4. Blush asset/contract 이식

목표: 팀원 cheek UV mask의 색감/밀도/느낌을 현재 `blush` package flow에 연결한다.

작업:

- blush mask texture를 Unity resource 위치에 추가한다.
- mask id, density gain, center gain, `uvTransform`, `partUvTransform`을 manifest/schema에 연결한다.
- RN/package에서는 `region=blush`만 저장한다.
- Unity에는 legacy 호환이 필요한 경우 `cheek` alias를 유지한다.
- 사용자 조정값은 위치, 스케일, 회전, 부드러움, 밀도 중심으로 둔다.

완료 조건:

- package에서 blush layer가 생성된다.
- Unity resource id로 blush texture를 참조할 수 있다.
- asset 누락 시 legacy cheek fallback + warning이 나온다.

중단 조건:

- PNG만 복사되고 gain/transform/material parameter가 누락된다.
- `cheek`이 다시 canonical처럼 퍼진다.

### M5. Brow asset/contract 이식

목표: 팀원 brow asset의 모양/색/질감을 현재 사용자 맞춤 anchor flow에 연결한다.

작업:

- 최신 brow PNG/hair texture와 mask resource를 추가한다.
- palette, blend mode, `detailAmount`, `maskSpreadX`, `maskOffsetY`를 look parameter로 보존한다.
- MediaPipe brow landmarks는 anchor, scale, rotation, 좌우 비대칭, confidence만 담당하게 분리한다.
- 실제 brow shape/thickness/color/hair detail은 teammate asset을 source of truth로 둔다.

완료 조건:

- brow package entry에 `tracking`과 `look`이 분리되어 저장된다.
- asset id와 renderer parameter가 누락 없이 Unity route까지 전달된다.
- asset이 없으면 brow는 skip + warning으로 처리된다.

중단 조건:

- MediaPipe polygon이 최종 brow mask처럼 쓰이기 시작한다.
- 팀원 asset 색감/파라미터가 package save/load에서 사라진다.

### M6. MediaPipe full-face anchor 확장

목표: lip, brow, eyeliner가 같은 MediaPipe 기반 anchor 체계에서 나오게 한다.

작업:

- `lip`은 기존 MediaPipe 경로를 유지한다.
- `brow`는 좌/우 brow landmark group을 anchor로 변환한다.
- `eyeliner`는 upper eyelid curve, inner/outer canthus, eye width, eye open ratio를 추출한다.
- eyeliner boundary schema는 `e7-eyeliner-upper-boundary-provisional-v0`로 저장한다. 전문가 asset fit 전까지 stable v1 contract로 간주하지 않는다.
- Vision result는 저장해도 되지만 primary 후보나 UI 선택지로 승격하지 않는다.
- MediaPipe 실패 시 region별 blockedReason/warning을 남긴다.

완료 조건:

- same-frame provider result에서 lip/brow/eyeliner가 각각 분리된 contract로 표현된다.
- eyeliner는 asset 없이도 boundary 저장이 가능하다.

중단 조건:

- MediaPipe native model/dependency path가 깨진다.
- Codex shell GL/Metal 문제를 제품 실패로 오해하고 구현을 중단한다.

### M7. Package schema/save/load 통합

목표: 네 region이 하나의 full-face package 안에서 저장되고 다시 로드된다.

작업:

- package structure를 `tracking`, `adjustment`, `look`, `runtime` 역할로 분리한다.
- `lip`은 기존 saved package compatibility를 유지한다.
- `blush`는 UV mask id와 adjustment/look parameter를 저장한다.
- `brow`는 MediaPipe anchor와 teammate asset parameter를 저장한다.
- `eyeliner`는 upper eyelid boundary와 future asset slot을 저장한다.
- unknown field를 버리지 않도록 save/load 경로를 점검한다.

완료 조건:

- 저장 후 재로드해도 네 region entry가 유지된다.
- 사용자 조정값과 팀원 look parameter가 사라지지 않는다.
- `lip` 기존 package가 깨지지 않는다.

중단 조건:

- save/load가 region별 unknown parameter를 삭제한다.
- lip package migration 없이 기존 fixture가 실패한다.

### M8. Unity runtime 연결

목표: 저장 package가 Unity renderer에서 region별로 올바르게 dispatch된다.

작업:

- Unity parser가 `lip`, `blush`, `brow`, `eyeliner`를 받도록 한다.
- `blush` texture/gain/transform이 material parameter로 전달되는지 확인한다.
- `brow` asset id/palette/blend/detail/spread/offset이 renderer route까지 전달되는지 확인한다.
- `eyeliner`는 asset이 없으면 boundary/future slot 상태로 처리한다.
- 기존 `lip/cheek/eye-smooth-mask-v1` fallback은 필요한 범위에서만 유지한다.

완료 조건:

- Unity smoke에서 네 region dispatch log가 나온다.
- resource missing은 fail 또는 warning으로 명확히 구분된다.

중단 조건:

- Unity가 unknown region을 조용히 무시한다.
- material parameter가 전달되지 않아 색감/밀도가 branch와 달라질 가능성이 크다.

### M9. RN editor/UI 연결

목표: 사용자에게 provider 복잡도를 숨기고 region별 조정을 가능하게 한다.

작업:

- UI에 Vision/MediaPipe/ARKit 선택지를 노출하지 않는다.
- 사용자 흐름은 `자동 생성 -> 직접 조정 -> 저장 -> AR handoff`로 유지한다.
- region별 조정은 lip에서 검증된 slider + quick button 패턴을 재사용한다.
- `blush`는 위치/크기/회전/밀도/부드러움 중심으로 노출한다.
- `brow`는 위치 Y, spread X, 회전, detail/thickness, color preset 중심으로 노출한다.
- `eyeliner`는 이번 병합에서는 boundary debug/asset pending 상태를 명확히 보여준다.

완료 조건:

- 사용자가 기술 provider를 선택하지 않아도 네 region package를 만들 수 있다.
- region 하나가 warning이어도 전체 flow가 설명 가능하게 진행된다.

중단 조건:

- UI가 다시 실험실 provider 선택 화면처럼 보인다.
- Save 전에 어떤 region이 ready/partial/blocked인지 알 수 없다.

### M10. Pre-Xcode gate 검증

목표: 실기기 없이 병합 사고를 최대한 잡는다.

작업:

- schema/static check를 먼저 실행한다.
- package JSON 생성과 save/load round trip을 확인한다.
- RN TypeScript, focused Jest, native generate checker를 실행한다.
- Unity resource/import smoke와 `E7FullFaceRegionPackageSmoke` batchmode를 실행한다.
- `npm run e7:prebuild:full -- --no-report` 또는 동등한 full-face prebuild gate를 실행한다.
- fallback/negative path를 확인한다: legacy cheek fallback warning, brow asset missing skip warning, eyeliner asset missing warning, MediaPipe blockedReason, unknown Unity resource fail.

완료 조건:

- pass/warn/fail이 gate별로 기록된다.
- blocking fail은 0개여야 한다.
- 남은 fail은 phone-only deferred 또는 명확한 non-blocking warning으로 분류되어야 한다.
- fail은 region, layer, 원인, 다음 action으로 분해된다.

중단 조건:

- Unity licensing/project lock처럼 환경 blocker가 반복된다.
- pre-Xcode fail 원인을 특정하지 못한다.

### M11. 결과 문서 반영

목표: 다음 세션이나 다른 에이전트가 상태를 오해하지 않게 한다.

작업:

- `TECH_VALIDATION_RESULT.md` Current Session Snapshot에 병합 결과를 기록한다.
- active roadmap에는 현재 완료 위치와 다음 phone-connected gate만 반영한다.
- 이 runbook의 inventory 표를 실제 값으로 갱신한다.
- product-quality ready 표현은 쓰지 않는다.

완료 조건:

- 각 region 상태가 `pre-xcode-ready`, `partial`, `blocked` 중 하나로 기록된다.
- iPhone 실기기 검증 미수행 항목이 deferred로 명확히 남는다.

중단 조건:

- build/install/launch 없이 product-quality ready처럼 표현된다.
- evidence 위치와 문서 내용이 서로 맞지 않는다.

### M12. Phone-connected 준비

목표: 다음 iPhone 세션이 바로 실행 가능한 상태가 되게 한다.

작업:

- Xcode build/install/run 전 필요한 질문과 사용자 action을 정리한다.
- 실기기 확인 항목은 face attachment, visual boundary, motion/expression/blink/yaw, FPS, latency, memory, thermal로 둔다.
- 사용자 판단이 필요한 시점에는 Slack 알림 stop rule을 사용한다.

완료 조건:

- 다음 세션 goal prompt가 바로 작성 가능하다.
- phone-connected gate가 pre-Xcode gate와 혼동되지 않는다.

중단 조건:

- iPhone 없이 visual acceptance를 통과 처리하려 한다.

## 5. 사전 정리 reference

이번 정리는 "중간 정리"로 제한한다.

이 섹션은 M1 실행 시 확인할 정리 기준 reference다. 실행 순서는 4장의 M1을 따른다.

### 5.1 정리 대상

- 끊긴 preview/report 링크
- 더 이상 참조되지 않는 임시 실험 산출물
- repo에 남으면 안 되는 cache/generated state
- `.DS_Store`
- Unity `Library`, `Logs`, `UserSettings`
- Xcode derived data
- raw frame, 임시 mask, 장기 보관이 불필요한 local-only 진단 산출물

### 5.2 보존 대상

- curated evidence
- 현재 보고서가 참조하는 이미지
- active roadmap 근거 자료
- `TECH_VALIDATION_RESULT.md`의 Current Session Snapshot 근거
- `lip` 사용자 맞춤형 생성/저장/AR handoff 관련 코드
- RN/Unity 현재 package contract

### 5.3 금지 대상

- 병합 전 대규모 폴더 구조 개편
- region 이름 전체 치환
- 오래된 코드를 감으로 삭제
- AGENTS.md에 병합 상세 계획을 길게 추가
- RN/Unity runtime 리팩터링을 정리 작업에 포함

## 6. Contract inventory reference

이 섹션은 M2 실행 시 실제 값을 채우는 reference다. 실행 순서는 4장의 M2를 따른다.

병합 전 현재 브랜치 기준으로 다음 표를 채운다.

| Region | Package id | Mask texture id | Unity resource | Renderer/material route | Source |
| --- | --- | --- | --- | --- | --- |
| `lip` | `lip-balanced-gold-v0` | `e7-lip-balanced-uv-v0` | `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/e7-lip-balanced-uv-v0.png` | `smooth-region-mask` + `e7-full-face-lip-material-v0` | `current branch` |
| `blush` | `blush-balanced-soft-oval-v0` | `e7-blush-balanced-uv-v0` | `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/e7-blush-balanced-uv-v0.png` | `smooth-region-mask` + `e7-full-face-blush-material-v0` | `blush-mask`(legacy cheek v1) `source candidate` |
| `brow` | `brow-balanced-stroke-envelope-v0` | `e7-brow-balanced-uv-v0` | `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/e7-brow-balanced-uv-v0.png` | `smooth-region-mask` + `e7-full-face-brow-material-v0` | `current branch` (requires source-of-truth reconfirm) |
| `eyeliner` | `eyeliner-minimal-safe-lashline-v0` | `e7-eyeliner-minimal-safe-uv-v0` | `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/e7-eyeliner-minimal-safe-uv-v0.png` | `smooth-region-mask` + `e7-full-face-eyeliner-material-v0` | `current branch` / provisional boundary-only route |

### 6.1 병합 run 체크 (2026-06-30)

- M0 기준 고정: 완료. dirty 파일 분류(`lip` 보호 대상 + `runbook` 변경 예정 + `앱/Unity` 변경), merge 이전 점검 완료.
- M1 정리: 완료. cache/generated 정리 후보는 별도 runbook 반영 후 다음 게이트에서 문서 증빙 반영 예정.
- M2 계약 인벤토리: 완료. 위 테이블로 채움.
- M3 source branch inventory: 부분 완료. `origin/blush-mask`는 cheek v1 기반 에셋만 존재하고, `feature/brow-0626`는 `e7-brow-*` 공식 식별자 자산이 없어 **최신 brow asset 경로가 불명확**.
- M4~M12: `feature/brow-0626` 최신 자산 모호성 때문에 중단 상태(아래 M12 Stop rules 기준).

### 6.2 고정된 stop rule 기록

- `feature/brow-0626` 최신 `e7` brow 공식 식별자 자산 미확정.
- 최신 brow asset를 `feature/brow-0626`에서 확정하지 못하면 `M5` 이식을 강행하지 않음.
- `M10`~`M12`는 본 이식 가드 조건 충족 전까지 대기 상태로 둠.

Inventory 작성 시 확인할 항목:

- RN에서 보내는 region 이름
- saved package에 저장되는 region 이름
- Unity가 받는 region 이름
- Unity `Resources/SmoothRegionMasks` texture 이름
- renderer/material route 이름
- adjustment field 이름과 단위
- look parameter 이름과 범위
- legacy alias 필요 여부

## 7. Blush contract reference

이 섹션은 M4 실행 시 확인할 contract reference다. 실행 순서는 4장의 M4를 따른다.

### 7.1 가져올 것

- cheek/blush mask assets
- `cheek-session-mask-*` 계열 texture id
- density gain
- center gain
- `uvTransform`
- `partUvTransform`
- shader/material 관련 값
- asset/contract 검증 스크립트

### 7.2 가져오지 않을 것

- 오래된 `cheek` 중심 RN validation flow
- 현재 package flow를 덮는 App 구조
- 현재 full-face flow와 충돌하는 임시 UI

### 7.3 최종 연결 방식

- 신규 package에는 `region=blush`로 저장한다.
- Unity 내부에서 필요하면 `cheek -> blush` alias를 허용한다.
- 사용자 조정값은 `offsetX`, `offsetY`, `scale`, `rotation`, `softness`, `density` 중심으로 둔다.
- asset 누락 시 legacy cheek mask fallback을 허용하되 warning을 남긴다.

## 8. Brow contract reference

이 섹션은 M5 실행 시 확인할 contract reference다. 실행 순서는 4장의 M5를 따른다.

### 8.1 가져올 것

- 최신 팀원 brow asset
- brow PNG/hair textures
- brow mask ids
- palette
- blend mode
- `detailAmount`
- `maskSpreadX`
- `maskOffsetY`
- renderer parameter
- brow asset 검증 스크립트 또는 문서

### 8.2 가져오지 않을 것

- 현재 package flow를 덮는 오래된 RN App 구조
- MediaPipe anchor와 충돌하는 자체 tracking 임시 로직
- 현재 runtime layer를 대체하는 branch-specific route

### 8.3 최종 연결 방식

- MediaPipe brow landmarks는 위치, 회전, 스케일, 좌우 비대칭, confidence만 담당한다.
- 실제 눈썹 모양, 두께, 컬러, 털 질감, blend 느낌은 팀원 brow asset이 담당한다.
- 최신 brow asset이 `feature/brow-0626`에 없으면 병합을 멈추고 사용자에게 asset 위치를 요청한다.
- asset 누락 시 brow region은 skip + warning으로 처리한다.

## 9. Eyeliner contract reference

이번 병합에서는 전문가 eyeliner asset을 만들지 않는다. 우리 책임은 asset fit 기준이 되는 upper eyelid boundary를 저장하는 것이다.

이 섹션은 M6/M7 실행 시 확인할 contract reference다. 실행 순서는 4장의 M6/M7을 따른다.

### 9.1 저장할 값

- upper eyelid curve
- inner canthus
- outer canthus
- eye width
- eye open ratio
- confidence
- warning
- schemaVersion: `e7-eyeliner-upper-boundary-provisional-v0`

### 9.2 최종 연결 방식

- MediaPipe upper eyelid boundary를 source of truth로 둔다.
- boundary schema는 provisional이다. 전문가 asset fit이 들어오면 stable v1 schema 또는 migration adapter를 새로 둔다.
- runtime slot은 열어두되, asset이 없으면 boundary saved + asset missing warning 상태로 둔다.
- 임시 eyeliner shape를 제품 asset처럼 넣지 않는다.

## 10. Full-face package/runtime contract reference

이 섹션은 M7/M8 실행 시 확인할 contract reference다. 실행 순서는 4장의 M7/M8을 따른다.

최종 full-face package는 네 region을 모두 포함해야 한다.

| Region | Required status |
| --- | --- |
| `lip` | generated mask + adjustment + runtime payload |
| `blush` | UV mask id + adjustment + look parameter |
| `brow` | MediaPipe anchor + teammate asset id + look parameter + adjustment |
| `eyeliner` | MediaPipe upper eyelid boundary + future asset slot |

UI는 provider 선택지를 노출하지 않는다. 사용자에게는 `자동`과 `직접 조정` 중심 흐름만 제공한다.

Fallback 정책:

| Region | Fallback |
| --- | --- |
| `lip` | 실패 시 blocked |
| `blush` | legacy cheek mask fallback + warning |
| `brow` | skip + warning |
| `eyeliner` | boundary 저장 성공, asset missing warning |

## 11. Risk Register

이 섹션은 병합 중 자주 발생할 수 있는 실패 모드를 미리 고정한다. 각 milestone은 아래 risk를 확인하고, 해당 risk가 발생하면 `예방책`을 먼저 적용한 뒤에도 해결되지 않을 때 `Stop rule`을 따른다.

| ID | 위험 | 발생 가능 지점 | 예방책 | Stop rule |
| --- | --- | --- | --- | --- |
| R1 | 팀원 에셋의 색감/느낌이 달라짐 | PNG만 복사하고 Unity `.meta`, material, blend, gain, transform을 놓칠 때 | PNG, `.meta`, resource id, shader/material parameter, gain/transform을 한 세트로 이식 | 같은 asset이 branch와 명백히 다른 색감/밀도로 보이면 중단 |
| R2 | package save/load에서 look parameter 유실 | brow/blush의 custom field를 serializer가 버릴 때 | save/load round trip에서 `detailAmount`, `maskSpreadX`, `maskOffsetY`, palette, blend, density/center gain 보존 확인 | 저장 후 재로드에서 look/tracking/adjustment 값이 사라지면 중단 |
| R3 | legacy 이름이 새 region 의미와 섞임 | `cheek`, `eye`, `eyeline`, `eyebrow`가 canonical처럼 쓰일 때 | 신규 package는 `lip/blush/brow/eyeliner`만 사용하고 `cheek -> blush`만 legacy alias 허용 | 같은 id가 두 의미로 쓰이면 중단 |
| R4 | 최신 brow asset source of truth 불명확 | `feature/brow-0626`에 최신 asset이 없거나 여러 후보가 있을 때 | M3에서 최신 asset 위치를 확정하고, 불명확하면 사용자에게 경로 요청 | 최신 brow asset을 확정하지 못하면 brow 이식 중단 |
| R5 | fallback/skip이 성공처럼 보임 | blush fallback, brow skip, eyeliner asset missing이 warning 없이 지나갈 때 | package/debug/prebuild gate에 warning 또는 blockedReason을 남김 | warning 표면화 없이 fallback이 통과하면 중단 |
| R6 | MediaPipe 확장이 lip 회귀를 만듦 | native provider/schema를 확장하면서 기존 lip boundary shape를 바꿀 때 | lip provider contract는 보존하고 brow/eyeliner는 별도 field로 추가 | lip generate/save/apply baseline이 깨지면 중단 |
| R7 | eyeliner provisional schema가 stable처럼 굳어짐 | 전문가 asset 전 boundary schema를 v1처럼 취급할 때 | `e7-eyeliner-upper-boundary-provisional-v0`로 저장하고 future migration을 명시 | stable v1로 고정하려는 변경이 생기면 중단 |
| R8 | Unity 환경 문제와 코드 문제가 섞임 | batchmode project lock, licensing, AssetImportWorker, platform support 문제 | 환경 blocker와 code fail을 분리 기록하고 필요한 프로세스/라이선스 상태를 먼저 정리 | 원인 미분리 pre-Xcode fail이면 중단 |
| R9 | 정리 중 evidence/report 링크가 깨짐 | cleanup에서 curated evidence나 보고서 참조 이미지를 삭제할 때 | 삭제 전 보고서 참조 여부와 curated evidence 여부를 확인 | evidence 여부가 애매하면 삭제하지 않음 |
| R10 | pre-Xcode pass를 product-quality-ready로 오해 | 결과 문서나 handoff에서 실기기 미검증을 누락할 때 | `pre-xcode-ready`, `partial`, `blocked`, `deferred`를 분리 기록 | iPhone visual evidence 없이 product-quality-ready 표현이 나오면 중단 |

## 12. Gate matrix

| Gate | 확인 내용 | 완료 기준 |
| --- | --- | --- |
| Contract gate | region 이름, package schema, legacy alias, id mapping | 누락/충돌 없음 |
| Asset gate | blush/brow texture, manifest, resource 참조 | Unity resource 참조 가능 |
| Generate gate | 네 region entry 생성 | lip 회귀 없음, 나머지 region entry 생성 |
| Save/load gate | 저장 package 재로드 | adjustment/look/tracking 값 보존 |
| RN gate | TS/Jest/native generate checker | 통과 또는 명확한 blockedReason |
| Unity gate | resource/import/static smoke | Unity batchmode smoke 통과 |
| Pre-Xcode gate | full-face prebuild gate | blocking fail 0개, warning/deferred 명시 |

## 13. Test plan

실행 순서:

1. schema/static check
2. package JSON 생성 확인
3. id mapping/manifest 참조 확인
4. RN TypeScript
5. focused Jest
6. native generate checker
7. Unity resource/import smoke
8. `E7FullFaceRegionPackageSmoke` batchmode
9. `npm run e7:prebuild:full -- --no-report` 또는 동등한 full-face prebuild gate

Fallback/negative path:

1. blush asset 누락 시 legacy cheek fallback warning이 표면화된다.
2. brow asset 누락 시 brow skip + warning이 표면화된다.
3. eyeliner asset 누락 시 boundary saved + asset missing warning이 표면화된다.
4. MediaPipe 실패 시 provider blockedReason이 package와 UI/debug surface에 남는다.
5. Unity unknown resource는 조용히 무시되지 않고 fail 또는 명확한 warning으로 기록된다.

이번 범위에서 제외:

- Xcode build
- iPhone install/launch
- real-device face attachment
- motion/expression/blink/yaw 확인
- FPS/frame-time
- latency
- memory/thermal
- 사용자 visual acceptance

위 항목은 다음 phone-connected gate에서 수행한다.

## 14. 결과 문서 반영

병합 완료 후 다음을 반영한다.

1. `TECH_VALIDATION_RESULT.md` Current Session Snapshot
   - 병합된 region
   - 통과한 gate
   - partial/blocked 항목
   - iPhone deferred 항목

2. Active roadmap
   - 현재 완료 위치
   - 다음 phone-connected gate
   - 남은 visual/product-quality 증거

3. 이 runbook
   - 최종 id mapping
   - 실제 가져온 asset 목록
   - 실제 fallback/warning 정책

## 15. Stop rules

다음 상황에서는 병합을 계속 진행하지 않고 사용자에게 보고한다.

- 최신 brow asset 위치가 불명확함
- `lip` generate/save/apply baseline이 깨짐
- Unity resource id가 같은 이름으로 다른 의미를 가짐
- 팀원 branch의 shader/material contract가 현재 runtime과 충돌함
- MediaPipe native dependency/model 경로가 깨짐
- pre-Xcode gate에서 fail이 발생했지만 원인 분리가 되지 않음
- Xcode/iPhone 실기기 action이 필요해짐

사용자 도움이 필요한 경우 Slack webhook이 설정되어 있으면 다음 형식으로 알린다.

```bash
python3 scripts/notify_slack_user_required.py --message "<짧은 한국어 요청>"
```

## 16. 완료 정의

이번 병합은 다음 조건을 모두 만족하면 완료로 본다.

- `lip`, `blush`, `brow`, `eyeliner` package contract가 존재한다.
- `lip` 기존 기능이 회귀하지 않는다.
- `blush`는 팀원 cheek UV mask와 사용자 조정값을 package/runtime에 연결한다.
- `brow`는 MediaPipe anchor와 팀원 brow asset contract를 연결한다.
- `eyeliner`는 MediaPipe upper eyelid boundary를 저장한다.
- buildless/schema/RN/Unity/pre-Xcode gate 결과가 문서화된다.
- blocking pre-Xcode fail은 남아 있지 않다.
- 남은 warning/fail은 phone-only deferred 또는 non-blocking warning으로 분류되어 있다.
- 실기기 검증이 필요한 항목은 product-quality ready로 과장하지 않고 deferred로 기록한다.
