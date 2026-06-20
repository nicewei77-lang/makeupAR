# React Native + Unity AR Foundation iPhone Tech Validation Test Plan

## 1. 목적

이 문서는 AI AR Makeup Guide의 전체 서비스를 개발하기 전에, AR 메이크업 기능의 핵심 엔진을 만들 수 있는지 검증하기 위한 기술 검증 계획이다.

이번 validation의 범위는 하나로 제한한다.

> React Native 앱과 Unity + AR Foundation 기반 iOS AR 화면을 연동하고, 실제 iPhone에서 얼굴 추적과 RN-Unity 양방향 통신이 가능한지 확인한다.

서비스 기획서 기준으로 AR 메이크업 가이드는 사용자의 얼굴 위에 추천 메이크업을 실시간 적용하고, 사용자가 색상, 범위, 질감, 강도, opacity, feather, blend mode, 위치, 크기를 조정할 수 있어야 한다. 다만 이번 검증에서는 메이크업 품질 전체가 아니라, 그 기능을 만들기 위한 기술 기반이 성립하는지만 확인한다.

## 2. 검증 범위

### 포함

- React Native iOS 앱 생성
- Unity AR Foundation 프로젝트 생성
- Unity ARKit face tracking 설정
- Unity iOS build 및 `UnityFramework.framework` 생성
- React Native 앱에 Unity 화면 embed
- iPhone 실기기에서 Unity AR 화면 실행
- 얼굴 추적 여부 확인
- React Native에서 Unity로 recipe-like JSON 전달
- Unity에서 전달받은 값으로 AR overlay 색상 또는 opacity 변경
- Unity에서 React Native로 상태 이벤트 전달
- AR 화면 진입, 종료, 재진입 안정성 확인

### 제외

- 로그인
- AI 추천
- 백엔드/API
- Admin Web
- 결제
- 커뮤니티
- 실제 립/블러셔/아이섀도우 품질 구현
- 정교한 face part segmentation
- 제품별 발색 재현
- Android 검증
- App Store 제출

## 3. 기준 버전

최신 안정 조합을 우선한다.

| 영역 | 기준 |
| --- | --- |
| Mobile App | React Native 0.86 |
| Node | Node 22 LTS 계열 |
| AR Engine | Unity 6.3 LTS |
| Unity AR | AR Foundation 6.3.x |
| iOS AR Provider | Apple ARKit XR Plug-in 6.3.x |
| iOS Build Tool | Xcode 26.0+ |
| Test Device | iPhone 11 이상 |
| Target | iOS 실기기 |
| Simulator | 사용하지 않음 |

선택 이유:

- React Native 0.86은 현재 stable/active release 라인이다.
- Unity 6.3 LTS는 Unity 6 계열의 장기 지원 버전이다.
- AR Foundation 6.3은 Unity 6 계열과 호환되고, iOS provider로 ARKit XR Plug-in 6.3을 사용한다.
- ARKit XR Plug-in 6.3은 Xcode 26.0 이상을 요구한다.
- Unity embed 및 ARKit face tracking은 iOS simulator가 아니라 실제 iPhone에서 검증해야 의미가 있다.

참고:

- React Native versions: https://reactnative.dev/versions
- React Native environment setup: https://reactnative.dev/docs/set-up-your-environment
- Unity 6 releases: https://unity.com/releases/unity-6
- AR Foundation 6.3 install: https://docs.unity3d.com/Packages/com.unity.xr.arfoundation@6.3/manual/project-setup/install-arfoundation.html
- Apple ARKit XR Plug-in 6.3: https://docs.unity3d.com/Packages/com.unity.xr.arkit@6.3/manual/index.html
- Unity as a Library iOS: https://docs.unity3d.com/Manual/UnityasaLibrary-iOS.html
- React Native Unity bridge candidate: https://github.com/azesmway/react-native-unity

## 4. 초기 로컬 상태 기록

아래 표는 2026-06-19 M0 시작 시점의 기록이다. 최신 진행 상태와 현재 툴체인 판정은 `TECH_VALIDATION_RESULT.md`를 기준으로 본다.

| 항목 | 상태 | 판정 |
| --- | --- | --- |
| macOS | 14.3.1 | Xcode 26 설치 가능 여부 확인 필요 |
| Xcode | `/Applications/Xcode.app` 없음 | 선행 설치 필요 |
| xcodebuild | Command Line Tools만 활성화 | 전체 Xcode 전환 필요 |
| Unity Hub | 없음 | 선행 설치 필요 |
| Unity Editor | 없음 | 선행 설치 필요 |
| Node | 25.2.1 | Node 22 LTS로 고정 권장 |
| npm | 11.6.2 | Node 22 LTS에 맞춰 재확인 |
| Watchman | 없음 | 설치 필요 |
| CocoaPods | 없음 | 설치 필요 |

따라서 이 validation의 첫 번째 작업은 앱 구현이 아니라, iPhone 빌드가 가능한 개발 환경을 만드는 것이다.

## 5. 최종 판정 기준

### Green

다음 조건을 모두 만족하면 기술적으로 진행 가능으로 판정한다.

- React Native 앱이 iPhone 실기기에서 실행된다.
- RN 화면에서 버튼을 눌러 Unity AR 화면을 열 수 있다.
- Unity AR 화면에서 ARKit face tracking이 동작한다.
- 얼굴 mesh 또는 얼굴 기준 overlay가 화면에 표시된다.
- RN slider 또는 버튼 값이 Unity로 전달된다.
- Unity overlay의 색상 또는 opacity가 전달값에 따라 바뀐다.
- Unity가 `initialized`, `face_detected`, `recipe_applied` 중 최소 2개 이상의 상태 이벤트를 RN으로 전달한다.
- Unity 화면 진입, 종료, 재진입을 3회 반복해 crash가 없다.

### Yellow

다음 중 하나에 해당하면 가능성은 있으나 설계 변경 또는 추가 검증이 필요하다고 판정한다.

- Unity 단독 iOS 앱에서는 ARKit face tracking이 되지만 RN embed에서 실패한다.
- RN embed는 되지만 Unity unload/re-enter 시 crash 또는 black screen이 발생한다.
- RN -> Unity 단방향 통신은 되지만 Unity -> RN 이벤트가 불안정하다.
- iPhone 기기 또는 iOS 버전에 따라 face tracking 결과가 크게 달라진다.
- 성능이 낮아 AR 화면이 20fps 미만으로 유지된다.

### Red

다음 중 하나에 해당하면 현재 조합으로는 핵심 엔진 구현 리스크가 높다고 판정한다.

- UnityFramework를 RN iOS 앱에 통합할 수 없다.
- iPhone 실기기에서 ARKit face tracking이 동작하지 않는다.
- Unity 화면 진입 자체가 반복적으로 crash를 유발한다.
- RN과 Unity 간 값 전달이 불가능하거나 매우 불안정하다.
- Xcode/Unity/React Native 버전 충돌이 해결되지 않는다.

## 6. 마일스톤 우선순위

| 우선순위 | 마일스톤 | 목적 | 완료 기준 |
| --- | --- | --- | --- |
| P0 | M0. 환경 게이트 | 실기기 빌드 가능한 툴체인 확보 | Xcode, Unity, Node, CocoaPods, Watchman 준비 |
| P0 | M1. Unity 단독 AR 검증 | ARKit face tracking 자체가 되는지 확인 | Unity iOS 단독 앱에서 face mesh/overlay 표시 |
| P0 | M2. RN 단독 iOS 검증 | RN 앱이 iPhone에서 정상 빌드되는지 확인 | RN 기본 앱 실기기 실행 |
| P0 | M3. UnityFramework 생성 | Unity를 RN에 넣을 수 있는 산출물 확보 | `UnityFramework.framework` 생성 |
| P0 | M4. RN-Unity embed | RN 앱 안에서 Unity 화면 열기 | RN 화면에서 Unity view 표시 |
| P1 | M5. RN -> Unity 통신 | recipe 값을 Unity에 전달 | 색상/opacity 변경 반영 |
| P1 | M6. Unity -> RN 통신 | Unity 상태를 RN에서 받기 | face/status event 수신 |
| P1 | M7. 재진입 안정성 | 실제 앱 흐름에서 crash 위험 확인 | 진입/종료/재진입 3회 통과 |
| P2 | M8. 결과 정리 | 기술 선택 가능 여부 판정 | Green/Yellow/Red 리포트 작성 |

## 7. M0. 환경 게이트

### 목표

iPhone 실기기 빌드, Unity iOS export, React Native iOS build가 가능한 로컬 환경을 준비한다.

### 작업

1. macOS 버전과 Xcode 26 설치 가능 여부를 확인한다.
2. Xcode 26.0 이상을 설치한다.
3. Xcode Command Line Tools를 전체 Xcode로 전환한다.
4. Xcode license 동의 및 first launch setup을 완료한다.
5. Unity Hub를 설치한다.
6. Unity 6.3 LTS와 iOS Build Support를 설치한다.
7. Node 22 LTS를 설치하고 현재 shell과 Xcode build phase에서 같은 Node를 보게 한다.
8. Watchman을 설치한다.
9. CocoaPods를 설치한다.
10. iPhone 11 이상 실기기를 USB로 연결하고 Developer Mode, trust, signing team을 설정한다.

### 확인 명령

```sh
sw_vers
xcodebuild -version
xcode-select -p
node -v
npm -v
watchman --version
pod --version
```

### 완료 기준

- `xcodebuild -version`이 Xcode 26.0 이상을 반환한다.
- `xcode-select -p`가 `/Applications/Xcode.app/Contents/Developer`를 가리킨다.
- Unity Hub에서 Unity 6.3 LTS와 iOS Build Support가 설치되어 있다.
- `node -v`가 22 LTS 계열이다.
- `pod --version`과 `watchman --version`이 정상 출력된다.
- Xcode에서 iPhone이 run destination으로 보인다.

### 실패 시 대응

- Xcode 26이 현재 macOS에 설치되지 않으면 macOS 업그레이드를 선행한다.
- Node 25로 인해 RN 빌드 이슈가 나면 Node 22 LTS로 고정한다.
- CocoaPods 설치가 system Ruby 권한 문제로 실패하면 Homebrew Ruby 또는 Bundler 기반 설치로 전환한다.

## 8. M1. Unity 단독 AR 검증

### 목표

RN 통합 전에 Unity + AR Foundation + ARKit face tracking 자체가 iPhone에서 동작하는지 확인한다.

### 작업

1. Unity 6.3 LTS로 새 프로젝트를 생성한다.
2. iOS build target으로 전환한다.
3. Package Manager에서 다음 패키지를 설치한다.
   - AR Foundation 6.3.x
   - Apple ARKit XR Plug-in 6.3.x
   - XR Plug-in Management
4. Project Settings > XR Plug-in Management > iOS에서 ARKit을 활성화한다.
5. ARKit face tracking subsystem을 활성화한다.
6. Scene에 다음을 구성한다.
   - `AR Session`
   - `XR Origin`
   - `AR Camera`
   - `AR Camera Manager`
   - `AR Face Manager`
7. `AR Face Manager`의 Face Prefab에 간단한 mesh visualizer 또는 semi-transparent material을 연결한다.
8. `FaceTrackingStatusReporter` 스크립트를 추가해 face count와 support 여부를 화면 또는 log로 출력한다.
9. Unity에서 iOS Xcode project를 export한다.
10. Xcode에서 iPhone 실기기로 빌드/실행한다.

### 최소 구현 내용

Unity scene에는 정교한 makeup이 아니라 아래 수준의 placeholder만 둔다.

- 얼굴이 인식되면 얼굴 mesh 위에 반투명 컬러 material 표시
- 얼굴 추적 중이면 화면 텍스트 또는 log에 `Face detected: true`
- 얼굴을 벗어나면 `Face detected: false`

### 완료 기준

- iPhone에서 Unity 단독 앱이 실행된다.
- 전면 카메라 권한 요청이 뜬다.
- 얼굴을 비추면 face mesh 또는 overlay가 표시된다.
- 얼굴을 움직이면 overlay가 따라온다.
- Unity log에서 face tracking support와 face detected 상태를 확인할 수 있다.

### 실패 시 대응

- 카메라 권한, `NSCameraUsageDescription`, ARKit provider 활성화 여부를 확인한다.
- Face tracking이 안 되면 기기 모델, iOS 버전, ARKit support를 확인한다.
- Unity scene이 검은 화면이면 AR Camera background, XR Origin, AR Session 구성을 확인한다.

## 9. M2. React Native 단독 iOS 검증

### 목표

React Native 앱이 iPhone 실기기에서 정상 빌드되는지 확인한다.

### 작업

1. Bare React Native 프로젝트를 생성한다.
2. iOS dependency를 설치한다.
3. Xcode signing team을 설정한다.
4. iPhone 실기기에서 기본 RN 앱을 실행한다.

### 권장 명령

```sh
npx @react-native-community/cli@latest init MakeupARValidation --version 0.86.0
cd MakeupARValidation
cd ios
pod install
cd ..
npm start
```

별도 터미널 또는 Xcode에서 iPhone 대상으로 실행한다.

```sh
npx react-native run-ios --device
```

### 완료 기준

- iPhone에서 RN 기본 앱이 열린다.
- Metro bundle이 정상 로드된다.
- Xcode signing/provisioning 오류가 없다.
- 앱 재실행 시 crash가 없다.

### 실패 시 대응

- Node 22 LTS가 Xcode build phase에서도 인식되는지 확인한다.
- `.xcode.env`의 `NODE_BINARY`를 실제 Node 22 경로로 고정한다.
- Pods 오류가 나면 `pod repo update`, `pod install` 로그를 확인한다.

## 10. M3. UnityFramework 생성

### 목표

Unity 프로젝트를 React Native 앱에 embed할 수 있는 iOS framework 산출물로 만든다.

### 작업

1. Unity 프로젝트에 `@azesmway/react-native-unity`에서 요구하는 Unity-side bridge 파일을 복사한다.
2. Unity iOS build를 RN 프로젝트 밖의 별도 폴더로 export한다.
3. export된 Xcode project를 연다.
4. `Data` folder의 target membership을 `UnityFramework`에 포함한다.
5. iOS native bridge header의 visibility 또는 target membership을 라이브러리 문서 기준으로 설정한다.
6. `UnityFramework` target을 build한다.
7. 생성된 `UnityFramework.framework`를 RN 프로젝트의 `unity/builds/ios` 위치에 복사한다.

### 완료 기준

- `UnityFramework.framework`가 생성된다.
- framework 내부에 Unity Data가 포함된다.
- RN 프로젝트에서 참조 가능한 경로에 배치된다.

### 실패 시 대응

- Unity iOS Build Support 설치 여부를 확인한다.
- Xcode version이 ARKit XR Plug-in 요구사항인 26.0 이상인지 확인한다.
- framework build 중 signing 오류가 나면 `UnityFramework` target signing 설정을 확인한다.

## 11. M4. React Native 앱 안에서 Unity 화면 열기

### 목표

RN 앱에서 Unity 화면을 full-screen view로 띄운다.

### 작업

1. RN 프로젝트에 Unity bridge package를 설치한다.

```sh
npm install @azesmway/react-native-unity
```

2. iOS pods를 재설치한다.

```sh
cd ios
pod install
cd ..
```

3. `UnityScreen`을 만든다.
4. `UnityView`를 full-screen으로 렌더링한다.
5. Home screen에 `Start AR` 버튼을 둔다.
6. 버튼 클릭 시 Unity screen으로 이동한다.
7. iPhone에서 실행한다.

### RN 화면 요구사항

- Home:
  - `Start AR` 버튼
  - validation status text
- UnityScreen:
  - full-screen `UnityView`
  - `Close` 버튼
  - debug log text

### 완료 기준

- RN Home 화면이 표시된다.
- `Start AR` 버튼을 누르면 Unity 화면이 표시된다.
- Unity 화면에서 AR camera feed 또는 Unity scene이 보인다.
- `Close` 버튼으로 RN 화면으로 돌아올 수 있다.

### 실패 시 대응

- iOS simulator에서 테스트하지 않는다.
- UnityView 부모 view에 명확한 크기(`flex: 1`)가 있는지 확인한다.
- `MTLTextureDescriptor has width of zero`류 오류가 나면 UnityView layout size를 먼저 고정한다.
- 화면이 검게 나오면 Unity runtime load timing과 framework path를 확인한다.

## 12. M5. RN -> Unity 통신

### 목표

React Native UI에서 조작한 recipe-like 값을 Unity AR overlay에 반영한다.

### 최소 contract

RN에서 Unity로 전달하는 메시지:

```json
{
  "layer": "lip",
  "color": "#D94B74",
  "opacity": 0.65
}
```

Unity 수신 대상:

| 항목 | 값 |
| --- | --- |
| GameObject | `RNBridge` |
| Method | `ApplyRecipeJson` |
| Parameter | JSON string |

### Unity 구현 요구사항

- `RNBridge` GameObject를 scene에 둔다.
- `ApplyRecipeJson(string json)` 메서드를 만든다.
- JSON을 parsing한다.
- `color`와 `opacity`를 face overlay material에 반영한다.
- 반영 후 Unity log에 `recipe_applied`를 출력한다.

### RN 구현 요구사항

- 색상 선택 버튼 3개를 둔다.
  - rose: `#D94B74`
  - coral: `#E67B5F`
  - nude: `#B9826B`
- opacity slider를 둔다.
  - min: `0`
  - max: `1`
  - step: `0.05`
- 값 변경 시 `UnityView.postMessage("RNBridge", "ApplyRecipeJson", json)` 호출한다.

### 완료 기준

- RN에서 색상 버튼을 누르면 Unity overlay 색상이 바뀐다.
- RN에서 opacity slider를 움직이면 Unity overlay 투명도가 바뀐다.
- 값 변경 후 1초 이내 화면에 반영된다.
- Unity console 또는 Xcode log에서 적용 로그가 보인다.

### 실패 시 대응

- GameObject 이름과 method 이름이 정확히 일치하는지 확인한다.
- Unity method가 public이고 string parameter 하나를 받는지 확인한다.
- JSON parsing 실패 시 raw string을 log로 남긴다.

## 13. M6. Unity -> RN 통신

### 목표

Unity가 AR 상태를 RN에 전달하고, RN에서 이를 화면과 log로 확인한다.

### 최소 event contract

Unity에서 RN으로 보내는 메시지:

```json
{
  "type": "face_detected",
  "tracked": true,
  "faceCount": 1
}
```

추가 상태:

```json
{"type":"unity_initialized"}
{"type":"recipe_applied","layer":"lip"}
{"type":"face_detected","tracked":false,"faceCount":0}
```

### 작업

1. Unity bridge에서 native app으로 message를 보내는 API를 연결한다.
2. `ARFaceManager.trackablesChanged` 이벤트에서 face count를 계산한다.
3. face count 변경 시 RN으로 event를 보낸다.
4. RN `onUnityMessage`에서 event를 parsing한다.
5. RN 화면에 현재 상태를 표시한다.

### 완료 기준

- Unity load 완료 시 RN이 `unity_initialized`를 받는다.
- 얼굴 인식 시 RN이 `face_detected: true`를 받는다.
- 얼굴이 사라지면 RN이 `face_detected: false`를 받는다.
- RN 화면에 마지막 event가 표시된다.

### 실패 시 대응

- RN -> Unity가 먼저 되는지 확인한다.
- Unity native bridge 파일이 iOS build에 포함되어 있는지 확인한다.
- JSON event 대신 plain string event로 낮춰서 bridge 자체 문제와 parsing 문제를 분리한다.

## 14. M7. 재진입 안정성 검증

### 목표

실제 앱 흐름에서 사용자가 AR 화면을 여러 번 열고 닫아도 crash가 없는지 확인한다.

### 테스트 시나리오

1. RN Home 실행
2. `Start AR` 클릭
3. 얼굴 인식 확인
4. 색상 변경
5. opacity 변경
6. `Close` 클릭
7. Home으로 복귀
8. 위 과정을 3회 반복
9. 앱을 background로 보낸 뒤 다시 foreground로 복귀
10. AR 화면이 정상 재개되는지 확인

### 관찰 항목

- crash 여부
- black screen 여부
- camera permission 재요청 여부
- Unity unload 이후 재진입 가능 여부
- RN memory warning 여부
- iPhone 발열과 프레임 저하

### 완료 기준

- 3회 반복 진입/종료 중 crash가 없다.
- 재진입 후에도 얼굴 tracking이 동작한다.
- RN UI가 멈추지 않는다.
- Unity 화면 종료 후 iPhone camera indicator가 계속 남아있지 않는다.

### 실패 시 대응

- Unity unload 대신 pause/resume 전략으로 바꿔 테스트한다.
- full-screen modal을 유지하고 화면만 hide하는 전략을 비교한다.
- Unity as a Library의 single runtime 제한을 문서화한다.

## 15. M8. 결과 리포트

### 목표

검증 결과를 다음 개발 판단에 바로 쓸 수 있게 정리한다.

### 산출물

`TECH_VALIDATION_RESULT.md`를 작성한다.

포함 내용:

- 실행 날짜
- Mac 환경
- iPhone 모델/iOS 버전
- Xcode 버전
- Unity 버전
- AR Foundation 버전
- React Native 버전
- 검증 결과 요약
- Green/Yellow/Red 판정
- 성공한 항목
- 실패한 항목
- 주요 로그
- 화면 녹화 또는 스크린샷 경로
- 다음 액션

### 판정 예시

```md
## Final Decision

Status: Green

React Native 앱 안에서 Unity AR Foundation 기반 iOS AR 화면을 열고, iPhone 실기기에서 face tracking 및 RN-Unity 양방향 통신을 확인했다. 따라서 AR 메이크업 엔진은 React Native host + Unity embedded module 구조로 진행 가능하다.
```

## 16. 구현 순서

실제 작업은 아래 순서로 진행한다.

1. M0 환경 게이트 통과
2. M1 Unity 단독 AR 검증
3. M2 RN 단독 iOS 검증
4. M3 UnityFramework 생성
5. M4 RN-Unity embed
6. M5 RN -> Unity 통신
7. M6 Unity -> RN 통신
8. M7 재진입 안정성 검증
9. M8 결과 리포트 작성

순서를 바꾸지 않는다. 특히 Unity 단독 AR 검증과 RN 단독 iOS 검증이 실패한 상태에서 embed 작업으로 넘어가면 문제 원인을 분리하기 어렵다.

## 17. 최소 파일 구조 제안

검증 repo는 아래처럼 단순하게 유지한다.

```txt
makeupAR/
  TECH_VALIDATION_TEST_PLAN.md
  TECH_VALIDATION_RESULT.md
  docs/
    runbooks/
  rn/
    MakeupARValidation/
  unity/
    MakeupARUnityValidation/
  unity-builds/
    ios-export/
  evidence/
    logs/
    screenshots/
    screen-recordings/
```

원칙:

- `rn/`에는 React Native host app만 둔다.
- `unity/`에는 Unity source project만 둔다.
- `unity-builds/`에는 Unity export 결과를 둔다.
- `evidence/`에는 검증 증거를 둔다.
- Unity export 결과와 build artifact는 필요 시 `.gitignore`로 제외한다.

문서 운영 원칙:

- 루트 active 문서는 `TECH_VALIDATION_TEST_PLAN.md`와 `TECH_VALIDATION_RESULT.md` 두 개만 둔다.
- `TECH_VALIDATION_TEST_PLAN.md`는 검증 계약과 milestone 순서를 담는 정본 계획서다. 진행 로그를 누적하지 않는다.
- `TECH_VALIDATION_RESULT.md`는 최신 판정, milestone 이력, 현재 상태, 다음 경계를 담는 상태 문서다.
- 세션별 계획서(`M*_..._PLAN.md`)는 필요한 세션에서만 임시로 만들고, 세션 완료 후 핵심 결과를 `TECH_VALIDATION_RESULT.md`에 흡수한 뒤 삭제한다.
- 반복 실행 절차만 남길 필요가 있으면 `docs/runbooks/`에 둔다.
- 증거 파일은 `evidence/logs/`, `evidence/screenshots/`, `evidence/screen-recordings/` 아래에 보관하고, 결과 문서에는 workspace 밖의 임시 경로를 남기지 않는다.

## 18. 핵심 리스크

| 리스크 | 영향 | 우선 대응 |
| --- | --- | --- |
| Xcode 26 설치 불가 | iOS build 불가 | macOS 업그레이드 또는 ARKit package version downgrade 검토 |
| UnityFramework embed 실패 | RN + Unity 구조 불가 | Unity as a Library 수동 통합 fallback 검토 |
| iOS simulator 미지원 | 빠른 테스트 어려움 | 반드시 iPhone 실기기 기준으로만 판정 |
| Unity 재진입 crash | 앱 UX 리스크 | unload/pause/resume 전략 비교 |
| RN Node 버전 충돌 | iOS build 실패 | Node 22 LTS 고정 |
| ARKit face tracking 기기 차이 | 기능 지원 범위 불명확 | iPhone 모델/iOS 버전 기록 |
| Unity full-screen 제한 | RN UI overlay 설계 제약 | AR 화면은 full-screen modal로 검증 |

## 19. 이번 validation에서 만들 최소 기능

최소 기능은 아래 4개뿐이다.

1. RN Home에서 Unity AR 화면 열기
2. Unity에서 face tracking 확인
3. RN에서 color/opacity 값을 Unity로 보내기
4. Unity에서 face/status event를 RN으로 보내기

이 4개가 되면 AR 메이크업 엔진의 핵심 기술 축은 성립한다. 이 4개가 안 되면 메이크업 렌더링 품질 구현으로 넘어가지 않는다.
