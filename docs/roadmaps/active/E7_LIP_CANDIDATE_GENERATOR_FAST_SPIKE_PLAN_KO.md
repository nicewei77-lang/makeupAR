# E7 입술 후보 생성기 빠른 실험 계획

작성일: 2026-06-26 KST

## 0. 결정

이번 작업은 기존 후보를 더 자세히 채점하는 일이 아니라, **현재 가진 신호를 한 번에 조합해서 실제로 볼 만한 입술 경계 후보 5개를 만드는 빠른 실험**이다.

목표:

```txt
Apple Vision 점
+ face parsing 입술/피부/입 안쪽 mask
+ color/gradient edge
+ ARFace screen/UV mesh
+ 가능한 경우 blendshape 값
-> 곡선 기반 입술 후보 5개
-> 각 단계 이미지/정보 기록
-> 앱에서 후보 선택, 사용자 조정, 생성, 실제 카메라 확인
```

원칙:

- 속도를 우선한다. 완벽한 설계보다 빠르게 후보를 만들고 본다.
- 버전 분리는 최소화한다. 가능한 신호를 한 번에 붙여서 첫 결과를 만든다.
- 실패해도 멈추지 않는다. 빠진 신호는 `missing` / `blocked`로 기록하고 다음 단계로 간다.
- 새 원본 프레임 저장, 업로드, 상용 SDK, Android, 제품 기능 구현은 하지 않는다.
- iPhone build/install 또는 새 capture가 필요하면 먼저 명확히 묻고 진행한다.

참고: 사용자가 말한 "blender export"는 이 문서에서는 `blendshape export`, 즉 ARKit/ARFace 표정 값 내보내기로 해석한다.

## 1. 왜 이 실험이 필요한가

이미 확인한 문제:

- 기존 broad mask는 입술보다 크고 둥글다.
- gold 기반 변형은 사용자 기준 마스크에 너무 의존한다.
- face parsing은 면적 힌트는 좋지만 가장자리가 거칠다.
- Apple Vision은 형태는 안정적일 수 있지만 점이 적어서 잘릴 수 있다.
- color/gradient는 단독으로 boundary를 만들 수 없지만, 이미 있는 선을 실제 색 경계에 붙이는 데 쓸 수 있다.
- ARFace는 얼굴에 붙는 좌표계로 좋지만, 입술 색 경계를 직접 알지는 못한다.

따라서 이번 실험은 "정답 하나 찾기"가 아니라, 서로 다른 방식의 후보를 만들어 실제 카메라에서 비교할 수 있게 만드는 것이다.

## 2. 입력

첫 실행은 기존 local evidence만 사용한다.

| 입력 | 우선 경로 | 역할 |
| --- | --- | --- |
| clean frame | `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png` | 시각 비교 기준 |
| ARFace export | `evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/arface_export.json` | screen/UV projection |
| Apple Vision | `evidence/e7-lip-m1-packages/m1-lip-apple-vision-20260625T132216Z/apple_vision_lip_contour.json` | outer/inner lip 점 |
| face parsing | `evidence/e7-lip-m1-packages/m1-lip-face-parsing-20260625T2255Z/` | lip/upper/lower/skin/inner-mouth mask |
| color/gradient | `evidence/e7-lip-m1-packages/m1-lip-color-gradient-20260625T000000Z/color_gradient_confidence.json` | edge 신뢰도와 보정 정보 |
| gold reference | `evidence/references/e7-user-gold-raw-20260626/` | 비교용. 후보 생성의 절대 정답으로 쓰지 않음 |

## 3. 산출물

새 실행 폴더:

```txt
evidence/e7-lip-candidate-generator/experiment-YYYYMMDDTHHMMSSZ/
```

필수 산출물:

```txt
inputs/
  input_signal_report.json
  input_overview.png
  vision_points_overlay.png
  parsing_masks_overlay.png
  color_edge_band_overlay.png
  arface_mesh_overlay.png

candidates/
  parsing_curve_smooth_mask.png
  parsing_curve_smooth_alpha.png
  vision_curve_fill_mask.png
  vision_curve_fill_alpha.png
  vision_color_snap_mask.png
  vision_color_snap_alpha.png
  hybrid_curve_safe_mask.png
  hybrid_curve_safe_alpha.png
  hybrid_curve_balanced_mask.png
  hybrid_curve_balanced_alpha.png

debug/
  *_curve_points.json
  *_curve_overlay.png
  *_edge_band.png
  *_uv_round_trip_overlay.png
  *_generation_trace.json

review/
  full_size_contact_sheet.png
  compact_contact_sheet.png
  candidate_comparison_table.md
  review_notes_template.md

candidate_generation_summary.json
candidate_generation_summary.md
```

각 후보는 아래 정보를 반드시 남긴다.

| 정보 | 이유 |
| --- | --- |
| 사용한 입력 신호 | 어떤 기술이 영향을 줬는지 확인 |
| 생성 단계별 이미지 | 어느 단계에서 좋아지거나 망가졌는지 확인 |
| hard mask | Unity/UV projection 입력 |
| soft alpha | 실제 makeup edge 후보 |
| curve points | 가장자리 곡선 디버깅 |
| UV round-trip overlay | 3D 얼굴 좌표에 붙는지 확인 |
| known weakness | 다음 실험에서 바로 고칠 수 있게 기록 |

## 4. 후보 5개

### 4.1 `parsing_curve_smooth`

쉽게 말해 face parsing이 칠한 입술 덩어리를 매끈한 곡선으로 다시 그린다.

구현:

1. `face_parsing_lip_mask.png`에서 외곽 boundary를 추출한다.
2. upper/lower lip mask가 있으면 윗입술/아랫입술을 분리한다.
3. 좌우 끝점을 입꼬리 후보로 잡는다.
4. boundary 점을 줄이고, Chaikin 또는 Catmull-Rom 방식으로 곡선을 부드럽게 만든다.
5. 곡선 내부를 다시 채워 hard mask를 만든다.
6. 반복 erode/dilate로 soft alpha를 만든다.

기대:

- face parsing의 면적 판단을 살린다.
- 계단식 가장자리를 줄인다.

위험:

- face parsing이 입꼬리를 짧게 잡으면 곡선도 짧아진다.
- 원래 label이 틀린 곳은 매끈하게 틀릴 수 있다.

### 4.2 `vision_curve_fill`

쉽게 말해 Apple Vision이 찍어준 입술 점을 매끈하게 이어서 채운다.

구현:

1. `outerLips`, `innerLips` point를 읽는다.
2. 점 순서를 유지하면서 폐곡선으로 만든다.
3. 점 사이를 곡선으로 촘촘하게 보간한다.
4. outer는 채우고 inner는 뺀다.
5. hard mask와 soft alpha를 만든다.

기대:

- 형태가 안정적이고 대칭적인 후보가 나온다.
- face parsing보다 edge가 덜 거칠다.

위험:

- 점 수가 적어 실제 입술 굴곡을 놓칠 수 있다.
- 입꼬리와 얇은 윗입술이 잘릴 수 있다.

### 4.3 `vision_color_snap`

쉽게 말해 Vision 곡선을 시작점으로 두고, 실제 사진에서 입술색과 피부색이 갈라지는 지점으로 선을 조금 옮긴다.

구현:

1. `vision_curve_fill` 곡선의 각 점에서 tangent와 normal을 계산한다.
2. 각 점 주변 `-8px..+8px` 범위만 탐색한다.
3. luma/chroma gradient, lip/skin median color 차이를 함께 본다.
4. 가장 강한 boundary 후보로 점을 조금 이동한다.
5. 이동 거리는 제한한다. 색만 보고 크게 이동하지 않는다.
6. 이동 전/후 점과 edge band 이미지를 저장한다.

기대:

- Vision의 안정적인 모양을 실제 사진 경계에 더 붙인다.

위험:

- 조명/그림자/이미 바른 립 컬러 때문에 잘못 붙을 수 있다.
- color/gradient가 약하면 `vision_curve_fill`에 가깝게 유지한다.

### 4.4 `hybrid_curve_safe`

쉽게 말해 여러 신호를 다 보되, 피부나 입 안쪽으로 번지는 일을 강하게 피한다.

구현:

1. parsing curve와 vision/color curve를 모두 만든다.
2. 두 후보가 겹치거나 가까운 영역을 중심으로 삼는다.
3. face parsing skin mask와 inner-mouth mask는 exclusion으로 쓴다.
4. 입술 밖 skin band로 나가는 영역은 강하게 줄인다.
5. lower lip 아래쪽은 특히 보수적으로 처리한다.
6. UV round-trip에서 크게 어긋나는 삼각형 영역은 낮은 confidence로 표시한다.

기대:

- 실제 카메라에서 피부/입 안쪽 spill이 가장 적은 후보.

위험:

- 얇은 윗입술이나 입꼬리를 덜 칠할 수 있다.

### 4.5 `hybrid_curve_balanced`

쉽게 말해 safe보다 조금 더 넓게 잡아서 입꼬리와 얇은 윗입술을 살린다.

구현:

1. `hybrid_curve_safe`를 기반으로 한다.
2. Vision curve가 지지하는 입꼬리 방향은 조금 보존한다.
3. upper/lower split을 사용해 윗입술과 아랫입술 확장/축소를 따로 적용한다.
4. color edge가 약한 부분은 parsing/vision 중 더 안정적인 쪽을 따른다.
5. 피부 spill이 일정 수준을 넘으면 safe 쪽으로 되돌린다.

기대:

- 실제 적용감이 가장 자연스러운 후보일 수 있다.

위험:

- safe보다 피부 번짐 위험이 있다.

## 5. 후보 생성 공통 구현

새 모듈:

```txt
scripts/e7_lip_candidate_generator/
  build_lip_boundary_candidates.py
  lip_curve_utils.py
  lip_color_snap.py
  lip_candidate_review.py
```

처음에는 외부 패키지에 크게 의존하지 않는다.

- OpenCV / scipy / scikit-image가 있으면 사용 가능 여부를 기록하고 사용한다.
- 없으면 PIL + numpy로 직접 구현한다.
- MediaPipe는 설치되어 있으면 비교 후보로 바로 시도한다. 없으면 설치 필요로 기록한다.

공통 함수:

| 함수 | 역할 |
| --- | --- |
| `extract_boundary_points(mask)` | mask 외곽점 추출 |
| `split_lip_parts(mask, upper, lower)` | upper/lower/corner 구분 |
| `smooth_closed_curve(points)` | 곡선 smoothing |
| `fill_curve(points, inner_points=None)` | 곡선 내부 mask 생성 |
| `make_soft_alpha(mask)` | 부드러운 edge 생성 |
| `snap_curve_to_color_edge(points, frame, band)` | 색/gradient 기반 미세 이동 |
| `project_candidate_to_uv(mask, arface_export)` | 기존 UV projection 호출 |
| `write_step_overlay(...)` | 단계별 이미지 저장 |

## 6. blendshape export 빠른 시도

현재 export는 `blendShapes.available=false`다. 이번 작업에서는 바로 시도한다.

구현 위치 후보:

```txt
unity/MakeupARUnityValidation/Assets/Scripts/E7SynchronizedCaptureExporter.cs
unity/MakeupARUnityValidation/Assets/Scripts/FaceTrackingStatusReporter.cs
```

시도 방식:

1. `ARFaceManager.TryGetBlendShapes(face, Allocator.Temp)` 호출을 시도한다.
2. 가능한 경우 `blendShapeId`, `weight`를 JSON에 저장한다.
3. ARKit location name 변환이 가능하면 이름도 저장한다.
4. 실패하면 `blendShapes.available=false`와 실패 사유를 저장한다.

우선적으로 보고 싶은 값:

- jaw open 계열
- mouth smile left/right 계열
- mouth funnel / pucker 계열
- mouth stretch left/right 계열

이 값은 후보 생성 단계에서 곧바로 완벽한 표정 보정으로 쓰지 않아도 된다. 첫 목표는 **캡처와 실제 카메라 확인 때 표정 상태를 기록하는 것**이다.

## 7. 앱 흐름

사용자가 원하는 흐름을 그대로 따른다.

```txt
앱 진입
-> 자동으로 5개 후보 생성 또는 준비된 후보 로드
-> 후보별 boundary preview 표시
-> 사용자가 후보 선택
-> cornerReach / upperLipTightness / lowerLipTightness / verticalOffset 조정
-> 생성하기
-> 맞춤 AR mask 생성
-> 실제 카메라 화면에서 적용
```

화면에서 필요한 최소 정보:

- 현재 후보명
- 사용 신호: Vision / parsing / color / ARFace / blendshape
- 사용자 조정값 4개
- 생성된 mask id
- 실제 카메라 화면에서 active candidate id

## 8. 리뷰 방식

각 후보마다 다음을 한 화면에서 볼 수 있게 한다.

| 보기 | 목적 |
| --- | --- |
| original frame | 기준 얼굴 |
| input overlay | Vision/parsing/color/mesh가 어디에 잡혔는지 |
| curve overlay | 후보가 만든 실제 경계선 |
| hard mask overlay | 칠해지는 영역 |
| soft alpha overlay | 실제 makeup edge 느낌 |
| UV round-trip overlay | ARFace UV에 붙였을 때 돌아오는 위치 |
| notes | 잘된 점/문제점 |

리뷰 문서:

```txt
review/candidate_comparison_table.md
review/review_notes_template.md
```

## 9. 실행 순서

1. 새 후보 생성기 폴더와 스크립트 뼈대를 만든다.
2. 기존 evidence 입력을 읽고 `input_overview.png`를 만든다.
3. `parsing_curve_smooth`를 만든다.
4. `vision_curve_fill`을 만든다.
5. `vision_color_snap`을 만든다.
6. `hybrid_curve_safe`와 `hybrid_curve_balanced`를 만든다.
7. 후보별 hard/alpha/overlay/trace를 저장한다.
8. 후보별 UV round-trip preview를 만든다.
9. full-size contact sheet와 비교 문서를 만든다.
10. blendshape export를 Unity exporter에 추가 시도한다.
11. buildless compile/static check를 돌린다.
12. build가 필요해지는 순간 사용자에게 묻고, 승인되면 한 번의 build로 후보 전부를 실제 카메라에서 확인한다.

## 10. 완료 조건

이 실험은 아래가 모두 있을 때 완료다.

- 후보 5개 hard mask.
- 후보 5개 soft alpha.
- 후보 5개 full-size overlay.
- 후보 5개 UV round-trip overlay.
- 각 단계 이미지와 trace JSON.
- 후보 비교표.
- 앱에 넘길 candidate registry draft.
- blendshape export 시도 결과.
- 다음 실제 카메라 확인 checklist.

완료라고 부르지 않는 경우:

- 후보 이미지가 작아서 육안 비교가 안 되는 경우.
- 어떤 입력 신호가 후보에 영향을 줬는지 trace가 없는 경우.
- `hybrid`가 실제로 무엇을 섞었는지 설명되지 않는 경우.
- 사용자 조정/생성/카메라 적용 흐름 없이 후보 이미지만 있는 경우.

## 11. 권장 실행 방식

현재 답변 세션:

- 이 계획 문서 생성.
- 방향 확정.

다음 실행:

- 긴 구현은 Goal 모드가 적합하다.
- 새 Codex 세션은 필수는 아니다. 단, 병렬 실험을 시키고 싶으면 별도 세션/하위 에이전트를 쓸 수 있다.
- Plan 모드는 사용자가 세부 승인 단계를 원할 때만 쓴다. 이번 목표는 빠른 시도이므로 Goal 모드가 더 맞다.

