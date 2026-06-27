# E7 아이라인 마스크 후보 최종 실험 보고서

상태: buildless/local-only 실험 완료. iPhone runtime Green 또는 product-quality-ready 판정 아님.

## 1. 한 줄 결론

이번 실험의 추천 조합은 **`mp-upper-balanced-v0`** 이다. 추적 기준은 MediaPipe upper eyelid landmark이고, 모양은 parametric eyeliner curve로 만든다. fallback은 **`mp-tail-only-v0`** 로 둔다.

## 2. 왜 다시 실험했나

기존 `eyeliner-minimal-safe-lashline-v0`는 앱 구현 전 baseline으로는 유용했지만, 실제 trace가 direct MediaPipe eyelid landmark라기보다 broad eye prior 안의 dark upper-lashline 추정에 가까웠다. 아이라인은 얇은 선이라 작은 오차가 바로 보이므로, 이번에는 MediaPipe landmark에서 upper eyelid curve를 직접 뽑아 후보를 만들었다.

## 3. 입력

| 항목 | 값 |
| --- | --- |
| Capture pair | `pair_face_20260627T091334Z_06` |
| Primary frame | `evidence/e7-reference-atlas/capture_pairs/pair_face_20260627T091334Z_06/frame.png` |
| Primary landmark | `mediapipe_face_landmarks.json` |
| Landmark count | `478` |
| 후보 수 | MediaPipe/parametric `8`개 + same-frame legacy baseline `3`개 |

용어를 짧게 정리하면 이렇다.

| 용어 | 의미 |
| --- | --- |
| MediaPipe upper eyelid | 눈 위쪽 경계 landmark. 이번 실험의 주 추적 기준 |
| Parametric curve | landmark를 그대로 칠하지 않고, 두께/꼬리/부드러움을 가진 곡선으로 다시 만든 마스크 |
| Eye opening overlap | 눈동자/눈 안쪽으로 침범했는지 보는 안전 지표. 이번 표에서는 boundary가 아니라 안쪽 safety zone 기준 |
| Legacy baseline | 기존 eye prior + dark pixel 방식. 같은 frame에서 다시 생성해 비교 |

## 4. Geometry 확인

<figure>
  <img src="assets/01-eyelid-landmark-eye-crop.png" width="760" alt="MediaPipe eyelid geometry overlay">
  <figcaption>그림 1. 초록색 선이 MediaPipe upper eyelid curve, 노란 점이 inner corner, 파란 점이 outer corner다. 이번 후보들은 이 선을 기준으로 생성했다.</figcaption>
</figure>

## 5. 전체 후보 비교

<figure>
  <img src="assets/02-full-frame-contact-sheet.png" width="860" alt="Full frame eyeliner candidate contact sheet">
  <figcaption>그림 2. full-frame overlay 비교. 얼굴 전체에서는 선이 작게 보이므로 위치가 크게 틀어졌는지와 좌우 균형을 먼저 본다.</figcaption>
</figure>

<figure>
  <img src="assets/03-eye-crop-contact-sheet.png" width="900" alt="Eye crop eyeliner candidate contact sheet">
  <figcaption>그림 3. 실제 판단은 eye crop이 중요하다. 아이라인은 얇기 때문에 full-frame보다 crop에서 eye opening 침범, 눈꼬리 시작점, 꼬리 각도를 봐야 한다.</figcaption>
</figure>

## 6. UV round-trip 확인

<figure>
  <img src="assets/04-uv-round-trip-contact-sheet.png" width="900" alt="UV round trip eyeliner contact sheet">
  <figcaption>그림 4. ARFace UV로 보냈다가 같은 frame으로 되돌린 preview다. 얇은 선이라 IoU만으로 품질을 단정하면 안 되고, 선이 완전히 깨지거나 엉뚱한 곳으로 가지 않는지를 본다.</figcaption>
</figure>

## 7. 선택 후보

<figure>
  <img src="assets/05-selected-candidate-eye-crop.png" width="760" alt="Selected eyeliner crop">
  <figcaption>그림 5. 선택 후보 `mp-upper-balanced-v0`. MediaPipe upper eyelid를 직접 따라가며, 앱 기본값으로 쓰기 좋은 균형형 형태다.</figcaption>
</figure>

선택 이유:

- eye opening overlap이 낮다.
- inner corner를 약간 비워 실제 앱에서 어색한 번짐을 줄인다.
- wing을 기본값으로 강제하지 않아 사용자 조정으로 확장하기 쉽다.
- legacy eye-prior baseline보다 추적 기준 설명이 명확하다.
- UV round-trip에서 thin-line 특유의 손실은 있지만, 앱 구현용 source policy로는 충분히 명확하다.

## 8. Fallback

Fallback은 `mp-tail-only-v0` 이다.

이 후보는 전체 라인을 그리지 않고 바깥쪽을 중심으로 잡는다. 눈 안쪽이 불안정하거나 full-line이 어색한 사람에게 안전한 대안이다.

## 9. Score 요약

| 후보 | Score | Eye opening overlap | Upper lid mean distance | Continuity | UV IoU |
| --- | ---: | ---: | ---: | ---: | ---: |
| `mp-upper-balanced-v0` | 0.572 | 0.0 | 4.382px | 1.0 | 0.081067 |
| `mp-tail-only-v0` | 0.547 | 0.0 | 3.828px | 1.0 | 0.16472 |
| `asset-fit-natural-local-style-v0` | 0.545 | 0.0 | 3.605px | 1.0 | 0.083118 |
| `mp-upper-minimal-v0` | 0.521 | 0.0 | 5.566px | 1.0 | 0.048193 |
| `mp-soft-lashline-shadow-v0` | 0.517 | 0.0 | 2.954px | 1.0 | 0.090354 |
| `asset-fit-wing-local-style-v0` | 0.514 | 0.0 | 3.684px | 1.0 | 0.151548 |
| `mp-wing-soft-v0` | 0.486 | 0.0 | 4.108px | 1.0 | 0.103335 |
| `mp-edge-snap-hybrid-v0` | 0.466 | 0.0 | 4.532px | 1.0 | 0.08885 |
| `baseline-legacy-safe-eye-prior-current-frame-v0` | 0.347 | 0.195494 | 16.965px | 0.833333 | 0.393224 |
| `baseline-legacy-balanced-eye-prior-current-frame-v0` | 0.346 | 0.192697 | 15.383px | 0.833333 | 0.352056 |
| `baseline-legacy-minimal-safe-eye-prior-current-frame-v0` | 0.318 | 0.184866 | 14.928px | 0.666667 | 0.300251 |


Legacy baseline 해석:

- same-frame legacy 후보는 이미지에서 주황색으로 보인다.
- UV IoU만 보면 높아 보이는 후보가 있지만, eye opening overlap과 upper lid distance가 훨씬 나쁘다.
- 따라서 기존 방식은 앱 기본 tracking으로 쓰지 않고, 비교용 baseline 또는 보조 참고로만 둔다.

## 10. 앱 구현으로 넘길 결정

```txt
primary tracker: MediaPipe upper eyelid landmark
shape model: parametric eyeliner curve
style preset: natural/minimal first, wing as user preset
runtime substrate: ARFace UV
fallback: tail-only or soft lashline
color/edge: optional snap helper only
face parsing: offline/evaluation helper only
```

사용자 조정축:

```txt
lineHeight
lineThickness
innerStart
outerReach
tailLength
tailAngle
tailLift
taper
softness
leftRightBalance
blinkFade
```

빠른 버튼:

```txt
얇게
조금 위로
조금 아래로
안쪽 비우기
꼬리 짧게
꼬리 올리기
바깥쪽만
좌우 맞추기
왼쪽만 조정
오른쪽만 조정
```

## 11. 남은 한계

- 이 결과는 static buildless frame 기준이다.
- blink/yaw/squint 안정성은 iPhone AR 화면에서 따로 봐야 한다.
- UV round-trip은 얇은 선 특성상 IoU가 낮을 수 있으므로, runtime에서는 실제 렌더링 crop으로 판단해야 한다.
- authored wing preset은 제품적으로 가능성이 있지만 기본값으로는 보수적으로 숨기는 편이 맞다.

## 12. 산출물 위치

| 항목 | 위치 |
| --- | --- |
| 실험 root | `evidence/e7-eyeliner-candidate-experiment/experiment-20260627T140808Z` |
| Scorecard | `evidence/e7-eyeliner-candidate-experiment/experiment-20260627T140808Z/scorecard.json` |
| Selected policy | `evidence/e7-eyeliner-candidate-experiment/experiment-20260627T140808Z/selected_policy.json` |
| Adjustment axes | `evidence/e7-eyeliner-candidate-experiment/experiment-20260627T140808Z/adjustment_axes.json` |
| App handoff | `evidence/e7-eyeliner-candidate-experiment/experiment-20260627T140808Z/app_handoff_ui_notes.md` |
| Report artifact mirror | `docs/product/e7-eyeliner-candidate-experiment-report-2026-06-27/artifacts` |

## 13. 최종 판정

아이라인 앱 구현은 진행 가능하다. 단, 최종 구현 전략은 **MediaPipe upper eyelid + parametric natural preset + tail-only fallback + 사용자 조정**으로 제한한다. 기존 eye-prior/dark-pixel 방식은 baseline 또는 보조 참고로만 둔다.
