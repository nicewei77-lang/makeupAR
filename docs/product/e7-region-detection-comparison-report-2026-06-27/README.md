# E7 눈·피부·눈썹 자동 인식 후보 비교 보고서

작성일: 2026-06-27 KST  
대상 캡처: `pair_face_20260627T091334Z_06`  
범위: 눈, 피부, 눈썹 마스크 후보 비교  
상태: buildless 비교 실험. 제품 품질 승인이나 iPhone runtime 검증 아님.

## 1. 한 줄 결론

이번 캡처는 정상적으로 들어왔고 ARFace 기반 비교 이미지는 생성됐다. 다만 이번 Mac 로컬 실험에서 직접 자동 인식까지 성공한 후보는 아직 없고, 실제로 볼 수 있는 결과는 `ARFace 기반 추론`과 `색 기반 추론`이다. Apple Vision, face parsing, MediaPipe는 각각 현재 실행 환경 문제로 막혔기 때문에, iPhone 앱 안의 native provider 결과를 다시 저장해서 비교해야 한다.

2026-06-27 추가 체크포인트: iOS native provider가 `vision_face_landmarks.json` / `mediapipe_face_landmarks.json`을 capture pair 폴더에 저장하는 경로는 구현됐고, `xcodebuild` generic iPhoneOS build는 통과했다. 아직 실제 iPhone에서 provider를 실행해 JSON을 가져오지는 않았으므로 Vision/MediaPipe 샘플은 계속 `blocked`로 표시한다.

## 2. 왜 이 실험을 했나

입술은 이미 MediaPipe 또는 Apple Vision에 사용자 조정을 더하는 방향이 거의 잡혔다. 문제는 눈, 피부, 눈썹, 나중에는 볼/아이라인까지 같은 방식으로 갈 수 있느냐다.

그래서 이번에는 사용자가 앱에서 직접 찍은 capture pair 하나를 기준으로, 후보들을 같은 사진 위에 올려 비교했다.

비교 후보는 아래 5개다.

| 후보 | 이번 실험에서 하려던 역할 | 이번 결과 |
| --- | --- | --- |
| ARFace / ARKit | 얼굴 mesh와 UV 좌표를 이용한 안정적인 위치 기준 | 실행됨. 단, 직접 인식이 아니라 geometry 기반 추론 |
| Apple Vision | 눈, 눈썹 landmark 직접 추출 | Mac Swift/Vision request 실패로 blocked |
| Face parsing | 피부, 눈, 눈썹 semantic label 추출 | 현재 Python 환경에 `torch`가 없어 blocked |
| 색 / 밝기 / gradient | 피부색, 눈 흰자/어두운 눈, 눈썹 털 보조 추출 | 실행됨. 단, 보조 신호 수준 |
| MediaPipe | face landmark로 눈/눈썹/face oval 추출 | macOS GL/Metal helper native abort로 blocked |

## 3. 입력 사진

아래 사진은 앱의 `CAPTURE PAIR` 흐름으로 저장된 clean frame이다. HUD가 없는 상태로 저장되어 마스크 비교 기준으로 쓰기 적합하다.

<img src="../../../evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/frame.png" width="260" alt="capture pair clean frame">

기본 메타데이터:

| 항목 | 값 |
| --- | --- |
| capture pair id | `pair_face_20260627T091334Z_06` |
| frame size | `1179 x 2556` |
| ARFace vertex count | `1220` |
| ARFace index count | `6912` |
| ARFace UV count | `1220` |
| tracking state | `Tracking` |
| local-only | `true` |
| off-device upload | `false` |

## 4. 전체 비교 시트

아래 이미지는 모든 후보를 같은 행렬로 본 것이다. 행은 후보, 열은 눈 / 피부 / 눈썹이다.

<img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/contact_sheet_eye_skin_brow.png" width="780" alt="eye skin brow detector contact sheet">

표기 의미:

| 표기 | 뜻 |
| --- | --- |
| `available` | 해당 후보가 직접 landmark 또는 semantic label을 생성함 |
| `approximate` | 직접 인식이 아니라 geometry, UV prior, 색 등의 추론 결과 |
| `blocked` | 현재 로컬 실행 환경에서 실행 실패 또는 필수 dependency 없음 |

이번 결과는 `available`이 없다. 즉, 현재 보고서에서 볼 수 있는 마스크는 모두 제품용 자동 인식 결과가 아니라 실험용 추론 결과다.

## 5. 후보별 상세 결과

### 5.1 ARFace 기반 추론

ARFace는 얼굴 mesh와 UV 좌표를 안정적으로 준다. 하지만 "눈", "피부", "눈썹"을 semantic mask로 직접 알려주지는 않는다. 이번 결과는 기존 smooth region UV prior 또는 현재 ARFace mesh를 화면에 투영해 만든 추론이다.

<table>
  <tr>
    <th>눈</th>
    <th>피부</th>
    <th>눈썹</th>
  </tr>
  <tr>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/arface/eye_overlay.png" width="220" alt="arface eye overlay"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/arface/skin_overlay.png" width="220" alt="arface skin overlay"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/arface/brow_overlay.png" width="220" alt="arface brow overlay"></td>
  </tr>
</table>

관찰:

- 눈: 실제 눈 영역보다 넓은 타원형 prior다. eye makeup이나 아이라인 시작점으로는 쓸 수 있지만, 눈꺼풀/속눈썹 경계로는 부족하다.
- 피부: 얼굴 mesh 전체를 채우므로 안정적이지만, 입술/눈/눈썹까지 같이 포함한다. 피부 semantic mask라기보다는 얼굴 표면 mask다.
- 눈썹: 눈 위치 위에 그린 arc다. 실제 눈썹 털 모양을 인식한 것이 아니라, 위치 추정용 envelope에 가깝다.

판단:

ARFace는 runtime substrate로는 계속 유리하다. 다만 눈썹/아이라인처럼 세밀한 부위는 ARFace 단독으로는 부족하고, Vision/MediaPipe landmark나 색 기반 refine, 사용자 조정이 필요하다.

### 5.2 색 / 밝기 기반 추론

색 기반은 피부색, 눈 주변의 밝고 어두운 픽셀, 눈썹의 어두운 털을 찾는다. 사진 한 장에서는 꽤 그럴듯한 힌트를 줄 수 있지만, 조명/머리카락/그림자/기존 화장에 매우 취약하다.

<table>
  <tr>
    <th>눈</th>
    <th>피부</th>
    <th>눈썹</th>
  </tr>
  <tr>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/color/eye_overlay.png" width="220" alt="color eye overlay"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/color/skin_overlay.png" width="220" alt="color skin overlay"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/color/brow_overlay.png" width="220" alt="color brow overlay"></td>
  </tr>
</table>

관찰:

- 눈: ARFace eye prior 안에서 밝은 눈 흰자와 어두운 눈동자/속눈썹 쪽을 잡는다. 눈꺼풀 전체 경계는 아니다.
- 피부: 얼굴 중앙 피부는 잘 덮지만, 코/입 주변의 색 변화와 그림자를 같이 잡는다. 피부를 "정확히" 분리했다기보다는 피부색에 가까운 픽셀 묶음이다.
- 눈썹: 이번 사진에서는 실제 눈썹 털 위치를 꽤 따라간다. 다만 눈썹이 밝거나 조명이 바뀌면 쉽게 무너질 수 있다.

판단:

색 기반은 primary tracker가 아니라 refine 신호로 쓰는 편이 맞다. 특히 눈썹은 `landmark로 대략 위치 잡기 -> 색으로 실제 털 영역 좁히기 -> 사용자 조정` 조합이 좋아 보인다.

### 5.3 Apple Vision

Apple Vision은 이론적으로 눈과 눈썹 landmark를 직접 제공할 수 있다. 하지만 이번 Mac buildless Swift 실행에서는 `VNDetectFaceLandmarksRequest`가 모든 orientation에서 실패했다.

<table>
  <tr>
    <th>눈</th>
    <th>피부</th>
    <th>눈썹</th>
  </tr>
  <tr>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/vision/eye_overlay.png" width="220" alt="vision eye blocked panel"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/vision/skin_overlay.png" width="220" alt="vision skin blocked panel"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/vision/brow_overlay.png" width="220" alt="vision brow blocked panel"></td>
  </tr>
</table>

로컬 doctor 결과:

- `VNDetectFaceRectanglesRequest`: 모든 orientation에서 ANE model load 오류로 실패
- `VNDetectFaceLandmarksRequest`: 모든 orientation에서 `Unspecified error`
- `face rectangles -> inputFaceObservations -> landmarks`: rectangle 단계에서 먼저 실패

중요한 해석:

- 이것은 "Apple Vision이 이 얼굴을 못 찾는다"는 증거가 아니다.
- 현재 Mac Swift/Vision 실행 환경에서 request가 실패했다는 증거다.
- iPhone 앱 안의 native Vision provider는 별도로 검증해야 한다.

다음 액션:

- 앱에서 native Vision 결과를 JSON으로 저장하고, 같은 비교 스크립트가 그 결과를 읽게 만드는 것이 가장 빠르다.
- 특히 눈/눈썹은 Vision이 성공하면 ARFace/color보다 훨씬 좋은 기준점이 될 가능성이 있다.

### 5.4 Face parsing

Face parsing은 피부, 눈, 눈썹 같은 semantic label을 직접 줄 수 있어서 비교 기준으로 매우 좋다. 하지만 현재 Python 실행 환경에는 `torch`가 없어 local BiSeNet runner를 실행하지 못했다.

<table>
  <tr>
    <th>눈</th>
    <th>피부</th>
    <th>눈썹</th>
  </tr>
  <tr>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/parsing/eye_overlay.png" width="220" alt="parsing eye blocked panel"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/parsing/skin_overlay.png" width="220" alt="parsing skin blocked panel"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/parsing/brow_overlay.png" width="220" alt="parsing brow blocked panel"></td>
  </tr>
</table>

판단:

Face parsing은 runtime primary로 쓰기보다는 offline silver reference나 평가 기준으로 쓰는 편이 맞다. 이번 단계에서 다시 살리려면 `torch`가 있는 로컬 환경을 별도로 준비해야 한다. 단, raw frame 장기 저장/업로드 없이 derived mask만 남기는 현재 privacy 원칙은 유지해야 한다.

### 5.5 MediaPipe

MediaPipe는 얼굴 landmark를 촘촘히 주기 때문에 눈/눈썹/face oval의 geometric 기준으로 유리하다. 하지만 이번 Mac 로컬 Python 실행에서는 FaceLandmarker native graph가 macOS GL/Metal helper service를 열지 못해 abort됐다. 기존 retry script로 여러 variant를 돌렸지만 모두 실패했다.

<table>
  <tr>
    <th>눈</th>
    <th>피부</th>
    <th>눈썹</th>
  </tr>
  <tr>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/mediapipe/eye_overlay.png" width="220" alt="mediapipe eye blocked panel"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/mediapipe/skin_overlay.png" width="220" alt="mediapipe skin blocked panel"></td>
    <td><img src="../../../evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/mediapipe/brow_overlay.png" width="220" alt="mediapipe brow blocked panel"></td>
  </tr>
</table>

판단:

이 실패는 Mac 로컬 실험 환경 문제에 가깝다. iOS 앱에는 이미 native MediaPipe provider 준비가 들어가 있으므로, 다음 비교는 앱이 저장한 native MediaPipe landmark 결과를 직접 가져오는 편이 더 현실적이다.

로컬 doctor 결과:

- MediaPipe Python import: 성공
- 설치 버전: `0.10.35`
- legacy `mp.solutions.face_mesh`: 현재 wheel에서 없음
- Tasks Vision API: import 가능
- Tasks FaceLandmarker retry: exit code `1`, macOS native helper 문제로 usable landmark 생성 실패

## 6. 숫자로 본 이번 결과

| 후보 | 눈 pixel | 피부 pixel | 눈썹 pixel | 상태 요약 |
| --- | ---: | ---: | ---: | --- |
| ARFace | 31,479 | 733,128 | 9,562 | 전부 approximate |
| Apple Vision | 0 | 0 | 0 | Mac Swift/Vision 실행 blocked |
| Face parsing | 0 | 0 | 0 | `torch` 없음 |
| 색 기반 | 41,604 | 684,685 | 23,127 | 전부 approximate |
| MediaPipe | 0 | 0 | 0 | macOS native graph abort |

숫자는 품질 점수가 아니다. 어떤 후보가 어느 정도 면적을 잡았는지 보는 참고값이다.

## 7. 현재 품질 판단

이번 결과만 놓고 보면 제품 품질 마스크로 바로 쓰기는 어렵다.

이유:

- 눈은 "눈 주변 영역" 정도는 잡았지만, 아이라인이나 아이섀도우 경계에 필요한 눈꺼풀/속눈썹 라인은 아니다.
- 피부는 얼굴 표면이나 피부색 영역을 크게 잡았을 뿐, 볼/블러셔 영역처럼 의도된 cosmetic placement가 아니다.
- 눈썹은 색 기반 결과가 가장 그럴듯하지만, 조명과 털 색에 의존한다.
- Vision, MediaPipe, face parsing의 직접 신호가 이번 로컬 비교에서 살아 있지 않아 최종 조합 판단이 아직 불완전하다.

그래도 이 실험은 쓸모가 있다. ARFace는 위치 고정용, 색 기반은 실제 털/피부색 refine용이라는 역할이 분명해졌고, blocked된 후보들은 "버릴 후보"가 아니라 "다음에는 앱 native output으로 가져와야 하는 후보"로 정리됐다.

## 8. 부위별 유력 조합 가설

### 눈

현재 최선 가설:

```txt
native Vision 또는 native MediaPipe eye landmarks
+ ARFace UV/mesh로 runtime 고정
+ 색 기반 dark/white pixel 보조
+ 사용자 조정: 위아래 위치, 두께, 눈꼬리, 부드러움
```

ARFace 단독은 눈 영역이 너무 넓다. 색 단독은 눈동자/흰자/그림자에 흔들린다. 눈은 landmark가 먼저 필요하다.

### 피부 / 볼

현재 최선 가설:

```txt
ARFace face surface
+ cheek UV prior 또는 parametric cheek placement
+ 피부색 guard로 머리카락/옷/그림자 제외
+ smile/yaw capture로 볼 위치 안정성 확인
+ 사용자 조정: 높낮이, 안쪽/바깥쪽, 크기, 강도, 부드러움
```

피부 전체 mask와 블러셔 mask는 다르다. 제품에 필요한 것은 "피부 전체 인식"이 아니라 "볼에 자연스럽게 올라갈 placement"다.

### 눈썹

현재 최선 가설:

```txt
native Vision 또는 MediaPipe eyebrow landmarks
+ 색 기반 dark-hair refine
+ ARFace로 얼굴 움직임에 고정
+ 사용자 조정: 높이, arch, tail 길이, 두께, 좌우 밸런스
```

이번 사진에서는 색 기반 눈썹이 꽤 유용했다. 하지만 landmark 없이 색만 쓰면 머리카락, 그림자, 안경, 조명에 취약하다.

## 9. 다음 작업 제안

가장 중요한 다음 단계는 Mac 로컬 provider 실패를 붙잡는 것보다, 앱이 이미 찍은 capture pair 흐름 안에서 native provider 결과를 저장하게 만드는 것이다.

우선순위:

1. iPhone 앱에서 native Vision 결과를 capture pair 폴더에 저장한다.
2. iPhone 앱에서 native MediaPipe 결과를 capture pair 폴더에 저장한다.
3. `devicectl copy from`으로 앱 Documents의 capture pair 폴더를 가져온다.
4. 이 보고서의 비교 스크립트가 그 JSON을 읽어 같은 contact sheet를 다시 만든다.
5. face parsing은 local research 기준으로 필요할 때만 `torch` 환경을 복구한다.
6. 다음 비교는 `neutral` 한 장이 아니라 `neutral / smile / blink / yaw`까지 포함해 안정성을 본다.

## 10. 남은 한계

- 이 보고서는 buildless 실험이다.
- iPhone runtime에서 Vision/MediaPipe가 실제로 같은 결과를 내는지는 아직 검증하지 않았다.
- 마스크가 얼굴 움직임, 표정, blink, yaw에서 안정적인지는 아직 모른다.
- 사람의 시각 판단으로 "메이크업 boundary로 괜찮다"는 승인을 받은 상태가 아니다.
- 이 결과만으로 Green 또는 product-quality-ready를 주장하면 안 된다.

## 11. 산출물 위치

| 산출물 | 경로 |
| --- | --- |
| 한국어 요약 | `evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/summary.md` |
| 전체 contact sheet | `evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/contact_sheet_eye_skin_brow.png` |
| 구조화 요약 JSON | `evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/summary.json` |
| 비교 생성 스크립트 | `scripts/e7_region_detection_compare/build_capture_pair_region_masks.py` |
| iPhone capture pair pull helper | `scripts/e7_region_detection_compare/pull_ios_capture_pair_and_rebuild.py` |
| Apple Vision helper | `scripts/e7_region_detection_compare/extract_apple_vision_face_landmarks.swift` |
| Apple Vision local doctor | `evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/vision/local_doctor/vision_local_doctor.json` |
| MediaPipe local doctor | `evidence/e7-region-detection-comparison/pair_face_20260627T091334Z_06/mediapipe/local_doctor/mediapipe_local_doctor.md` |
| iOS native provider source | `rn/MakeupARValidation/ios/MakeupARValidation/E7NativeLipBoundaryProviders.swift` |

## 12. 최종 판단

이번 실험은 "마스크 품질이 좋다"는 결론이 아니라, 눈/피부/눈썹에서 어떤 후보가 어떤 역할을 해야 하는지 분리한 실험이다.

현재 바로 쓸 수 있는 인사이트는 다음이다.

- ARFace는 얼굴에 붙이는 기준으로 계속 필요하다.
- 색 기반은 눈썹과 피부 refine에 도움이 되지만 단독 primary는 아니다.
- Vision과 MediaPipe는 버릴 후보가 아니라, Mac 로컬이 아니라 iPhone native output으로 다시 비교해야 하는 후보이다.
- Face parsing은 runtime 후보보다 offline silver reference/평가 기준으로 살리는 편이 좋다.
- 제품 흐름에서는 자동 인식 후 사용자 조정축이 반드시 필요하다.
