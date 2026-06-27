# E7 Eyeliner Reference Review

상태: 사용자 제공 레퍼런스 6장을 제품 기준으로 증류한 리뷰. 원본 이미지는 runtime asset이나 학습 데이터로 쓰지 않는다.

## 입력 해석

사용자 판단:

가장 좋은 예시로 지정된 이미지는 `Cat / Puppy / Sexy / Winged / Colored / Doll` 6-style grid다. 이 이미지는 copy 대상이 아니라 style taxonomy 기준으로 쓴다.

| 이미지 | 분류 | 해석 |
| --- | --- | --- |
| 사진 1 | good | 다양한 wing/outer-corner fill 예시. 선은 upper lashline을 따르고 바깥쪽으로 확장된다. |
| 사진 2 | good | Cat, Puppy, Sexy, Winged 등 style preset 후보. 공통적으로 tail 방향과 outer corner fill이 핵심이다. |
| 사진 3 | good | 실사용에 가까운 얇은 선부터 중간 두께 wing까지의 좋은 예시. 과도한 면 채움은 없다. |
| 사진 4 | good | 모노리드/속쌍형 참고. 눈 위 전체보다 바깥쪽 강조와 꼬리 방향이 중요하다. |
| 사진 5 | fail | 눈두덩 전체를 검게 덮는 block fill. 앱 기본 아이라인으로는 과하고 부자연스럽다. |
| 사진 6 | fail | 위아래를 두껍게 감싼 closed ring. lower lashline/inner corner가 과해 자연형 아이라인에서 벗어난다. |

## Good Shape Rules

- Anchor는 눈동자의 윗가장자리가 아니라 upper eyelid / lashline이다.
- 기본 preset은 outer corner를 비워두지 않고 채운다.
- Tail은 outer corner에서 자연스럽게 이어져야 하며 끝이 taper되어야 한다.
- Inner corner는 얇게 시작하거나 일부 비우는 것이 안전하다.
- 모노리드/속쌍에서는 전체 선보다 바깥쪽 1/3-1/2의 방향과 채움이 더 중요하다.
- 색/텍스처는 너무 불투명한 검정 덩어리보다 makeup처럼 보이는 밀도와 edge softness가 필요하다.

## Reject Rules

- Full lid black block: 눈두덩 전체를 넓게 덮는 면 채움은 실패로 본다.
- Closed eye ring: upper/lower/inner corner가 모두 두껍게 닫힌 링 형태는 실패로 본다.
- Heavy lower line by default: lower lashline은 기본 아이라인 mask에 넣지 않는다.
- Blunt sticker tail: 눈꼬리 끝이 뭉툭하고 두꺼운 스티커처럼 보이면 실패로 본다.
- Inner corner overload: 안쪽부터 두껍게 칠하면 눈 모양이 답답해 보이므로 기본값에서 피한다.

## Candidate Decision

최종 visual preset은 `asset-fit-wing-local-style-v0`를 유지한다. 이유는 좋은 레퍼런스의 공통점인 outer corner fill과 wing direction을 가장 잘 만족하기 때문이다.

`mp-upper-balanced-v0`는 폐기하지 않는다. 이 후보는 가장 깔끔한 MediaPipe upper eyelid 기준선이므로 tracking/reference anchor이며, 앱에서 자연형/균형형 후보로 함께 비교할 가치가 있다.

`mp-tail-only-v0`는 full-line이 눈 안쪽에서 불안정하거나 사용자 눈 모양과 맞지 않을 때의 safety fallback이다.

앱 제작 직전에는 별도 30-60분 anchor-to-band 대량 샘플 실험을 한 번 더 실행한다. 이 실험은 `Cat / Puppy / Sexy / Winged / Colored / Doll` family별로 100-180개 후보를 만들고, 사용자가 contact sheet에서 직접 후보 ID를 고르게 한다.

## Implementation Guards

기본 구현에서는 아래 가드를 둔다.

| 파라미터 | 기본 방향 |
| --- | --- |
| `outerCornerFill` | 기본 preset에서 required |
| `innerStart` | 0.18-0.28 근처에서 시작, 안쪽 비우기 버튼 제공 |
| `tailLength` | 0.12-0.22 eye width 범위에서 시작 |
| `tailAngle` | lower lashline 연장선보다 살짝 upward |
| `maxLidFillHeight` | eye height의 약 18% 이하를 기본 상한으로 둔다 |
| `lowerLidCoverage` | 기본 0, 별도 style이 생기기 전까지 아이라인 mask에서 제외 |
| `edgeSoftness` | 얇은 선이 sticker처럼 보이지 않도록 소프트닝 유지 |

앱 UI에서는 `Wing 기본`, `Balanced 자연형`, `Tail-only 안전형` 세 후보를 우선 노출하고, full-lid block 또는 closed-ring preset은 제공하지 않는다.
