# E7 Generate User Flow Fix Loop

이 문서는 E7 립 Generate를 더 이상 "코드는 바뀌었는데 앱은 그대로" 상태로 만들지 않기 위한 빠른 작업 방식이다.

## 원칙

1. 사용자 경로를 먼저 고정한다.

   - 이번 1차 성공 경로는 `시작 -> 정렬 -> 정면 사진 1장 촬영 -> 추출 -> fixed-photo 조정 -> 저장하고 AR 실행 -> AR 확인 -> 다시 조정`이다.
   - `blendshapeAssist`, 6장/다중 표정 촬영, 후보 비교 화면은 품질 이득이 증명되기 전까지 기본 flow에 넣지 않는다.

2. 화면에 보이는 것만 성공으로 친다.

   - build/test 통과는 준비 상태일 뿐이다.
   - iPhone runtime 성공은 설치 앱 build id, generated package, Unity ack, 화면/영상 증거가 함께 있어야 주장한다.

3. 기존 path를 남겨두지 않는다.

   - 숨긴 path도 테스트와 prebuild gate로 막는다.
   - 사용자 UI에 `블렌딩 선택`, raw `blendshapeAssist`, `현재 사진으로 다시 생성`이 다시 나오면 실패다.

4. 조정은 editor-only다.
   - AR 화면에서는 색/농도/보기만 즉시 바꾼다.
   - shape 조정은 `다시 조정 -> fixed-photo editor -> 저장하고 AR 실행 -> ack` 루프로 처리한다.

## 2026-06-30 잔존 문제 잠금 목록

사용자가 다시 지적한 항목은 아래 목록으로 고정한다. 여기서 `source`는 코드/테스트 반영 상태이고, `device`는 다음 iPhone 빌드에서 반드시 확인할 상태다.

| ID | 문제 | source 대응 | device 확인 |
| --- | --- | --- | --- |
| R1 | 고개 움직임 때 AR 마스크가 안 따라오거나 사라지는 느낌 | Unity `E3RegionMaskOverlay`가 짧은 `Limited/None` tracking gap에서 마지막 valid mesh를 grace hold한다. | slow/fast yaw에서 `lost_grace_hold`/`limited_grace_hold`와 화면 움직임을 같이 확인한다. |
| R2 | 밑입술이 과하게 두껍고 아래로 spill됨 | generated mask 기본값에 lower-lip spill guard를 적용하고 `밑입술 -` 도움말을 노출한다. | 기본값, `밑입술 -`, `밑입술 +`를 각각 AR 화면에서 비교한다. |
| R3 | 윗입술 안쪽이 비어 보임 | `안쪽채움` 축을 app-facing 조정축으로 유지한다. | `안쪽채움 +`가 윗입술 안쪽 hole을 줄이는지 AR 저장 후 확인한다. |
| R4 | 캡처 후 배경 사진이 왼쪽으로 치우치고 화면이 둘로 나뉘어 보임 | Extract 이후 full-screen captured photo 배경을 제거하고, 사진은 editor preview 안에서만 보이게 한다. | 추출/조정 화면에서 live/captured background bleed가 없는지 확인한다. |
| R5 | 버튼이 화면 밖으로 밀림 | adjustment card 높이와 scroll 영역을 줄이고 Save/AR를 sticky footer로 유지한다. | iPhone에서 `저장하고 AR 실행`이 항상 보이는지 확인한다. |
| R6 | 블렌딩/6장 촬영이 계속 보이는 것처럼 느껴짐 | 기본 flow는 1장 neutral capture + `기본 마스크` 하나다. `블렌딩 선택` 문구가 보이면 stale build/path 실패로 본다. | 설치 앱에서 촬영 수가 `1/1`이고 `블렌딩 선택`이 없는지 확인한다. |
| R7 | 조정해도 화면 변화가 이해되지 않음 | 조정축 라벨을 `입꼬리/윗입술/밑입술/안쪽채움/위치`로 바꾸고 fake boundary rectangle을 제거한다. | 숫자 변경, preview 갱신, saved package adjustment가 같은 값인지 pull evidence로 확인한다. |
| R8 | 저장하고 AR 실행 진행 상태가 불명확함 | 기존 save/post/waitingAck gate를 유지한다. | 저장, 전송, AR 확인 단계가 실제 ack와 맞는지 확인한다. |
| R9 | AR 화면에서 shape 재조정이 불가능함 | live AR shape edit 대신 `조정 화면으로` 버튼으로 fixed-photo editor에 복귀한다. | AR -> 조정 화면 복귀 시 촬영 사진과 후보가 유지되는지 확인한다. |
| R10 | canonical UV PSD 사용 여부가 불명확함 | 현재 PSD는 reference manifest만 등록되어 있고 runtime mask에는 직접 사용하지 않는다. ARCore PSD라 ARKit UV 변환/검증 없이 runtime에 직접 쓰면 안 된다. | runtime 사용 전 ARKit 1220 UV derivative/contact sheet/round-trip 검증이 필요하다. |

## 사용자 플로우 추적표

| 단계        | 사용자가 보는 화면                     | 필수 상태 변화                                              | 실패하면 안 되는 것               |
| ----------- | -------------------------------------- | ----------------------------------------------------------- | --------------------------------- |
| 시작        | 맞춤 Generate 시작                     | wizard=start                                                | legacy sample/old lip 자동 활성화 |
| 정렬        | 얼굴/카메라/프레임 준비                | alignment ready                                             | 촬영 전 추출 가능                 |
| 촬영        | 정면 사진 1장                          | captureShot neutral captured, framePreviewUri               | 6장 촬영 요구                     |
| 추출        | 마스크 생성 중 loading                 | isGeneratingCandidates=true                                 | 아무 반응 없는 버튼               |
| 조정        | captured frame 기반 fixed-photo editor | selected package exists, upperInnerFill visible             | live camera bleed, blend step     |
| preview     | 마스크/경계/비교 mode                  | preview mode text/image changes                             | 작은 썸네일만 제공                |
| 조정값 변경 | 숫자와 package 즉시 변경               | generatedMaskId/adjustment changed before preview completes | 저장 비활성, 재생성 요구          |
| 저장/AR     | visible progress                       | save -> post -> waitingAck                                  | 눌렀는지 모름                     |
| AR 확인     | 색/농도/보기 controls                  | matching control ack                                        | shape live edit처럼 오해          |
| 다시 조정   | editor 복귀                            | pending apply reset, capture preserved                      | 1장 사진 재촬영 강제              |

## 해야 할 일 체크리스트

- [ ] RN flow에서 `E7_CAPTURE_SHOT_OPTIONS`가 기본 1장인지 확인한다.
- [ ] `E7_WIZARD_STEPS`에 blend/review 단계가 기본으로 없는지 확인한다.
- [ ] 사용자 문구에서 `블렌딩 선택`, `기본 블렌딩`, raw `blendshapeAssist`가 제거됐는지 확인한다.
- [ ] 추출 중 loading/progress panel이 보이는지 테스트한다.
- [ ] Extract 이후 captured frame shield/fixed-photo editor만 보이는지 확인한다.
- [ ] 조정 preview에 `마스크`, `경계`, `비교` mode를 둔다.
- [ ] lip preview는 기본 zoom이고 tap으로 full face 전환된다.
- [ ] `upperInnerFill`만 app-facing inner axis로 노출하고 `innerFill`은 저장 payload에서 기본 0을 유지한다.
- [ ] 조정 클릭 즉시 package/runtime payload가 바뀌고 저장 가능해야 한다.
- [ ] separate regenerate CTA를 제거한다.
- [ ] sticky Save/AR CTA를 scroll 영역 밖 footer로 둔다.
- [ ] Close/back은 captured work를 보존하되 pending save/apply/ack를 취소한다.
- [ ] stale generation / adjustment / save / apply / control ack guard를 테스트한다.
- [ ] RN Jest가 위 사용자 경로를 실제로 누르며 검증한다.
- [ ] prebuild gate가 새 계약을 강제한다.
- [ ] `npm run e7:build-plan -- --no-report`로 UnityFramework 필요 여부를 판단한다.
- [ ] iPhone/device proof 없이는 runtime 성공을 주장하지 않는다.

## 빠른 검증 명령

```bash
npm test -- --runInBand --watchman=false
npm run lint
npm run e7:build-plan -- --no-report
npm run e7:prebuild:full -- --no-report
git diff --check
```

Codex shell에 `node` / `npm` PATH가 없으면 repo에서 쓰던 bundled Node 경로를 PATH 앞에 붙인다.
