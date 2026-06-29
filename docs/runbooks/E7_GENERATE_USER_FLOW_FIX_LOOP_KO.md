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
