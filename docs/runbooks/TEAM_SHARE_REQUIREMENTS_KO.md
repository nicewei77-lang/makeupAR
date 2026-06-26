# Team Onboarding and Share Requirements

이 문서는 `makeupAR` 디렉토리를 처음 클론한 팀원과 Codex 에이전트가 함께 보는 온보딩 문서다.

목표는 두 가지다.

- 팀원이 자기 Mac/iPhone/Apple Team 환경에 맞게 바로 세팅할 수 있게 한다.
- 에이전트가 현재 repo 구조, 공유 정책, 로컬 전용값, 생성물 정리 규칙을 오해하지 않게 한다.

이 repo는 React Native + embedded Unity + AR Foundation + ARKit 기반 iPhone 실기기 검증용 공동 베이스다. 현재는 화장품 모델링/렌더링 연구 전 단계의 validation workspace이며, 제품 구현 repo가 아니다.

## 먼저 읽을 순서

팀원:

1. 이 문서
2. `AGENTS.md`
3. `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`
4. 필요한 경우에만 `TECH_VALIDATION_TEST_PLAN.md`

Codex 에이전트:

1. `AGENTS.md`
2. `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`
3. 이 문서, 클론/공유/호환성/세팅을 다룰 때
4. milestone별 필요한 roadmap/research 문서만 lazy-load

## 공유 전 정리

공유 직전에는 repo root에서 아래를 실행한다.

```bash
bash scripts/cleanup_local_generated.sh --profile share --dry-run
bash scripts/cleanup_local_generated.sh --profile share --apply
```

`share` 프로필은 raw/generated evidence, build output, dependency install, Unity editor cache를 제거한다. curated evidence, 소스, lockfile, Unity `Packages/`, Unity `ProjectSettings/`, RN iOS 프로젝트 설정은 보존한다.

## 디렉토리 구조

| Path | Role |
| --- | --- |
| `AGENTS.md` | 에이전트/작업자 공통 규칙. scope, 빌드 루프, 증거/정리 정책 |
| `TECH_VALIDATION_RESULT.md` | 현재 상태, milestone 판정, 다음 boundary source of truth |
| `TECH_VALIDATION_TEST_PLAN.md` | 안정적인 validation 계약. 진행 상황 기록용 문서가 아님 |
| `rn/MakeupARValidation/` | React Native iOS host app |
| `unity/MakeupARUnityValidation/` | Unity + AR Foundation validation scene/source |
| `scripts/` | 재현 빌드와 로컬 생성물 정리 스크립트 |
| `docs/runbooks/` | 반복 실행 절차와 온보딩 문서 |
| `docs/roadmaps/active/` | 현재 또는 다음 validation 계획 |
| `docs/roadmaps/research/` | AR/beauty engine research 근거 |
| `docs/roadmaps/archive/` | 과거 evidence index/history. 최신 상태를 대체하지 않음 |
| `evidence/` | 공유 가능한 curated visual evidence와 선택된 mesh/capture 근거. raw evidence는 포함하지 않음 |
| `unity-builds/` | Unity iOS export 생성물. 공유본에는 포함하지 않음 |

처음 클론한 팀원은 `rn/MakeupARValidation/README.md`보다 이 문서를 우선한다. RN README는 일반 React Native 템플릿 문서라 이 repo의 Unity/iPhone validation 흐름을 충분히 설명하지 않는다.

## 필수 도구

| Tool | Required version / note |
| --- | --- |
| macOS | iPhone real-device validation 가능한 Mac |
| Xcode | iOS device build 가능한 Xcode. `xcodebuild -version`으로 확인 |
| Unity | `6000.3.18f1` with iOS Build Support |
| Node.js | `>= 22.11.0` |
| npm | `package-lock.json` 기준 `npm ci` |
| Ruby/Bundler/CocoaPods | `Gemfile.lock` 기준 `bundle install`, `bundle exec pod install` 가능 상태 |
| iPhone | ARKit Face Tracking 지원 기기 |

Docker는 현재 기본 실행 환경이 아니다. iPhone 실기기, Xcode signing, Unity iOS export, Unity Hub/license 흐름 때문에 Docker 안에서 end-to-end 실행하기 어렵다. 나중에 순수 Python 오프라인 분석이나 모델링 실험만 분리되면 별도 Docker화를 검토한다.

## 처음 클론 후 세팅

```bash
cd rn/MakeupARValidation
npm ci
bundle install
bundle exec pod install --project-directory=ios
cd ../..
bash scripts/build_m3_unityframework.sh
cd rn/MakeupARValidation
npm run ios -- --device "<TEAMMATE_IPHONE_NAME>" --no-packager --extra-params DEVELOPMENT_TEAM=<TEAMMATE_TEAM_ID>
```

`scripts/build_m3_unityframework.sh` 기본값은 전체 Unity/Xcode 로그와 DerivedData를 남기지 않는다. 특정 evidence pass에서만 `BUILD_LOG_MODE=full`을 붙인다.

## 개인 환경값 체크리스트

| Current local value | Why it matters | Team action |
| --- | --- | --- |
| `/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity` | build script default Unity path | Unity 설치 위치가 다르면 `UNITY_BIN=/path/to/Unity`로 실행 |
| `위승철의 iPhone` | local RN iOS device name | 팀원 기기 이름으로 `--device` 값을 교체 |
| `9G4K6N63MK` | local Apple Development Team | 팀원 Apple Team ID로 `DEVELOPMENT_TEAM` 교체 |
| durable `RNUnityView.mm` timing patch hook | clean reinstall에서 RN `postinstall` / iOS Podfile hook이 package-local patch를 재적용해야 함 | 설치 로그에서 `[rn-unity-timing-fix]`를 확인하고 첫 real-device run에서 Unity view initialization을 재검증 |

팀원은 개인값을 source file에 직접 커밋하지 않는다. 실행할 때 명령어 인자나 환경변수로 넘긴다.

예시:

```bash
UNITY_BIN="/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity" \
  bash scripts/build_m3_unityframework.sh

cd rn/MakeupARValidation
npm run ios -- --device "<TEAMMATE_IPHONE_NAME>" --no-packager --extra-params DEVELOPMENT_TEAM=<TEAMMATE_TEAM_ID>
```

## 첫 실행 확인

첫 팀원 실행은 기능 개발이 아니라 compatibility smoke test로 본다.

확인할 것:

- `npm ci`가 lockfile 기준으로 끝난다.
- `bundle exec pod install --project-directory=ios`가 끝난다.
- `bash scripts/build_m3_unityframework.sh`가 `Verification log`를 남기고 RN/package framework sync를 완료한다.
- iPhone build/install이 성공한다.
- Unity view가 검은 화면이나 0-size view로 멈추지 않는다.
- RN 화면에서 smooth-mask validation UI가 뜬다.
- 실기기에서 Unity initialization, face tracking, RN/Unity event path가 깨지지 않는다.

첫 실행에서 문제가 나면 먼저 `[rn-unity-timing-fix]` hook 실행 여부와 package framework sync를 확인한다. Hook이 실행됐는데도 Unity view가 검은 화면이면 real-device initialization 로그를 다시 수집한다.

## 보존해야 하는 파일

- `AGENTS.md`
- `TECH_VALIDATION_TEST_PLAN.md`
- `TECH_VALIDATION_RESULT.md`
- `evidence/README.md`
- `evidence/evolution/`
- selected canonical `evidence/screenshots/`
- `evidence/references/`
- `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/`
- `rn/MakeupARValidation/package-lock.json`
- `rn/MakeupARValidation/ios/Podfile.lock`
- `unity/MakeupARUnityValidation/Packages/`
- `unity/MakeupARUnityValidation/ProjectSettings/`
- `unity/MakeupARUnityValidation/Assets/`

## 공유하지 않는 파일

- `evidence/recovered/`
- `evidence/derived-data/`
- `evidence/logs/`
- `evidence/screen-recordings/`
- `unity-builds/`
- `rn/MakeupARValidation/unity/`
- `rn/MakeupARValidation/node_modules/`
- `rn/MakeupARValidation/ios/Pods/`
- `rn/MakeupARValidation/ios/build/`
- `unity/MakeupARUnityValidation/Library/`
- `unity/MakeupARUnityValidation/Logs/`
- `unity/MakeupARUnityValidation/UserSettings/`

## 정리 감사 결과

공유 전 볼륨 폭증 원인은 소스가 아니라 모두 재생성 가능한 로컬 산출물이었다.

| Category | Pre-cleanup size | Decision |
| --- | ---: | --- |
| `evidence/derived-data/` | 23GB | 삭제. Xcode DerivedData와 CompilationCache는 재생성 산출물 |
| `evidence/logs/` | 450MB | 삭제. 현재 결과는 `TECH_VALIDATION_RESULT.md`와 curated evidence에 흡수됨 |
| `evidence/screen-recordings/` | 102MB | 삭제. raw recording은 기본 보존 대상 아님 |
| `unity-builds/` | 821MB | 삭제. Unity iOS export는 script로 재생성 |
| `rn/MakeupARValidation/ios/Pods/` | 1.0GB | 삭제. `pod install`로 재생성 |
| `rn/MakeupARValidation/node_modules/` | 410MB | 삭제. `npm ci`로 재생성 |
| `unity/MakeupARUnityValidation/Library/` | 759MB | 삭제. Unity가 재생성 |
| `rn/MakeupARValidation/unity/` | 107MB | 삭제. `build_m3_unityframework.sh`가 재생성 |

검토했지만 보존한 항목:

| Path | Reason |
| --- | --- |
| `docs/roadmaps/archive/E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` | E7 전체 boundary와 cosmetic rendering 진입 조건을 설명하는 보관 문서 |
| `docs/roadmaps/archive/E7_REGION_PRECISION_SUBSPIKE_PLAN.md` | E7.3 Yellow boundary risk와 cosmetic rendering 전제 조건을 설명하는 보관 문서 |
| `docs/roadmaps/archive/E7_COSMETIC_RENDERING_TEAM_CHECK_PLAN_KO.md` | 팀원이 cosmetic rendering 실험 범위와 진입 조건을 확인할 때 쓰는 보관 문서 |
| `docs/roadmaps/archive/E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md` | E7.6 성능 비교 계약으로 재사용 가능한 보관 문서 |
| `scripts/e7_reference_atlas/fast_uv_atlas_gate.py` | 작고 추적된 재현 도구. 현재 cosmetic modeling 기본 문맥에서는 읽지 않아도 되지만 과거 face-boundary 판단 재검토에 필요 |
| `evidence/evolution/` | 처음 mesh 가능성, broad mask 한계, region precision Yellow, Ref UV sweep, smooth-mask accepted 흐름을 설명하는 대표 시각 근거 |
| `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/` | best current clean frame + ARFace export + projected mesh overlay. gold-mask drawing input과 face mesh 가능성 근거 |

## 현재 호환성 판단

- Source/lockfile 기반으로 팀원이 다시 설치하고 UnityFramework를 재생성하는 구조다.
- 현재 repo는 iPhone validation 전용이다. Android, backend, AI inference, admin, payment, production makeup rendering은 공유 실행 범위가 아니다.
- Clean reinstall의 `RNUnityView.mm` timing risk는 RN `postinstall`과 iOS Podfile hook으로 완화했다. 첫 팀원 실행에서는 hook 로그와 Unity view initialization을 검증 항목으로 남긴다.

## 에이전트 작업 규칙

- 클론/공유/정리/세팅 질문은 이 문서를 먼저 확인한다.
- 현재 milestone 판단은 항상 `TECH_VALIDATION_RESULT.md` snapshot을 우선한다.
- 공유본에는 curated `evidence/`가 있어야 한다. 단, raw logs, raw recordings, recovered cache, duplicate frame batches는 없어야 한다.
- `node_modules`, `Pods`, Unity `Library`, `unity-builds`, `rn/MakeupARValidation/unity`는 생성물이다. 필요하면 재설치/재생성하고, 커밋하지 않는다.
- Docker를 전제로 작업을 설계하지 않는다. 단, 순수 오프라인 분석만 별도 분리될 때는 새 계획에서 검토한다.
