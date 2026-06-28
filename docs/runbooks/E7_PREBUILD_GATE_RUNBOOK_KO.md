# E7 Prebuild Gate Runbook

## 목적

Xcode 빌드 전에 E7 in-app Generate 실패를 로컬에서 먼저 잡는다.

이 gate는 iPhone 실기기 build를 대체하지 않는다. 대신 긴 빌드 전에 아래를 차단한다.

- 실제 generated package는 입술 shape인데 RN preview가 둥근 사각형으로 보이는 문제
- `saved_record`를 runtime apply proof로 오해하는 문제
- `UnityFramework.framework`가 최신 `RNBridge` apply ack/persist 코드를 포함하지 않는 문제
- Vision/MediaPipe native provider, local save, preview bridge 누락
- Unity `generated_lip_mask_applied` ack gate 누락

## 명령

빠른 gate:

```bash
cd rn/MakeupARValidation
npm run e7:prebuild
```

native provider static check까지 포함:

```bash
cd rn/MakeupARValidation
npm run e7:prebuild:full
```

최소 빌드 경로 판정:

```bash
cd rn/MakeupARValidation
npm run e7:build-plan
```

직접 실행:

```bash
node scripts/e7_prebuild_gate/check_e7_prebuild_gate.mjs
```

## 최소 빌드 판정

`npm run e7:build-plan`은 Xcode/Unity를 실행하지 않는다. 현재 git diff와
`UnityFramework.framework` 해시/필수 문자열을 읽어서 다음 중 하나를 고른다.

- `skip-unityframework-run-rn-xcode-only`: RN/Swift 쪽만 바뀌었고 UnityFramework가 sync됨. Unity export/build를 생략하고 RN Xcode 빌드만 간다.
- `run-unityframework-build`: Unity 런타임 script, scene, shader, material, prefab, Resources, XR, iOS plugin이 바뀜. `bash scripts/build_m3_unityframework.sh`가 필요하다.
- `sync-or-rebuild-unityframework-before-xcode`: RN reference framework와 package-local framework가 다르거나 필수 ack/capture 문자열이 빠짐. sync 또는 rebuild 후 prebuild gate를 다시 돌린다.
- `skip-product-phone-build-legacy-debug-resource-only`: legacy/debug Unity resource만 바뀜. 제품 Generate 경로의 iPhone 빌드는 보통 불필요하며, 해당 legacy 후보를 일부러 시각 검증할 때만 UnityFramework/Xcode 승인을 요청한다.
- `skip-unityframework-run-unity-import-if-needed`: Unity Editor smoke/tooling만 바뀜. player framework 재생성은 보통 불필요하다.
- `manual-review-before-build`: 분류되지 않은 경로가 바뀜. Unity 생략 여부를 사람이 먼저 확인한다.

이 판정은 "사용하지 않는 Unity 파일 삭제"를 대신하지 않는다. 도구가 함께 출력하는
Unity asset audit은 파일 단위로 `product-runtime-required`, `product-runtime-fallback`,
`product-runtime-reference`, `legacy-validation-debug`, `editor-only`, `xr-simulation-debug`를
나눠 보여준다. 삭제/이동은 RN sample selector, Unity registry, scene/prefab 참조를
제거한 뒤 Unity import/compile까지 통과할 때만 한다.

가상 변경 파일로 판단만 재현할 수도 있다.

```bash
node ../../scripts/e7_build/decide_minimum_build.mjs --no-report \
  --changed-file=unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/e7-lip-validation-cv-vision-fill-v1.png
```

현재 기준으로 legacy/debug mask만 바뀌면 `skip-product-phone-build-legacy-debug-resource-only`,
`lip-smooth-mask-v1.png` 같은 product fallback이나 `RNBridge.cs`가 바뀌면
`run-unityframework-build`가 나와야 한다.

## 입력 Fixture

기본 fixture는 실제 iPhone에서 pull한 아래 자료를 사용한다.

```text
evidence/logs/e7-device-pull-20260627-post-user-review/
  source-pair-111840Z-12/frame.png
  source-pair-111840Z-12/arface_export.json
  generated-package/generated_lip_package.json
  generated-package/saved_record.json
```

이 fixture는 buildless replay 기준이다. 앱이 실제 capture에서 만든 package를 RN/Unity가 어떻게 소비할지 재현한다.

## 산출물

gate는 매번 아래 파일을 갱신한다.

```text
evidence/logs/e7-prebuild-gate/latest/gate-report.json
evidence/logs/e7-prebuild-gate/latest/gate-report.md
evidence/logs/e7-prebuild-gate/latest/mask-preview.html
evidence/logs/e7-prebuild-gate/latest/mask-preview.svg
```

`mask-preview.html`은 `generated_lip_package.json`의 `lipBoundary2D`를 실제 capture frame 위에 그린다. 앱 preview가 이 파일과 다르면 Xcode build를 진행하지 않는다.

## 통과 조건

다음 조건이 모두 pass여야 한다.

- package schema가 `e7-personalized-lip-generate-package-v0`
- privacy flags가 `localOnly=true`, `offDeviceUpload=false`, `longTermRawFrameStored=false`
- lip outer/inner boundary point가 존재
- boundary가 bbox proxy가 아닌 polygon shape
- runtime payload가 `raw_rgba_base64` UV mask를 포함
- UV alpha가 비어 있지 않음
- ARFace mesh/UV/index가 replay 가능
- RN preview가 bbox/rounded-rect fake overlay를 사용하지 않음
- RN preview가 generated package 기반 preview image를 표시
- iOS native bridge가 actual package preview render method를 노출
- RN apply success가 Unity `generated_lip_mask_applied` ack 조건을 요구
- Unity source가 latest/jsonl ack를 persist
- 현재 RN app에 포함될 `UnityFramework.framework`가 source와 같은 ack persistence 문자열을 포함

## 실패 해석

`rn.preview_no_fake_bbox_overlay` 실패:

RN이 `lipBoundary2D`를 실제 polygon/mask로 렌더하지 않고 bbox 기반 pill/rounded-rect로 표시한다. 이 상태로 빌드하면 사용자가 본 “입술 마스크가 막대처럼 보이는” 문제가 재발한다.

`ios.native_preview_method_exported` 실패:

RN이 보여줄 preview PNG를 native iOS에서 생성하는 bridge가 없다. `generated_lip_package.json`을 입력으로 받아 frame 위에 실제 lip boundary를 그린 `file://` preview를 반환해야 한다.

`unity.framework_contains_ack_persistence` 실패:

Unity source에는 `generated_lip_mask_applied.latest.json/jsonl` 저장 코드가 있지만 현재 RN 빌드가 사용할 `UnityFramework.framework`에는 그 코드가 없다. `bash scripts/build_m3_unityframework.sh`로 UnityFramework를 regenerate/sync하기 전에는 Xcode build를 금지한다.

`package.saved_record_is_not_apply_proof`는 pass가 정상이다. saved record가 local save임을 확인하는 check이며, runtime apply proof는 Unity ack만 인정한다.

## 운영 규칙

1. 앱/RN/Unity Generate flow를 수정한 뒤 먼저 `npm run e7:build-plan`으로 최소 빌드 경로를 정한다.
2. RN/Swift만 바뀐 경우 UnityFramework 재생성을 건너뛰고 RN 정적 체크와 prebuild gate를 먼저 돌린다.
3. `npm run e7:prebuild` 또는 `npm run e7:prebuild:full`에 빨간불이 있으면 Xcode build로 가지 않는다.
4. preview 관련 빨간불은 `mask-preview.html`과 RN preview가 같아질 때까지 수정한다.
5. UnityFramework 빨간불은 UnityFramework regenerate/sync 후 다시 확인한다.
6. 모든 gate가 pass한 뒤에만 사용자에게 Xcode build 승인을 요청한다.
