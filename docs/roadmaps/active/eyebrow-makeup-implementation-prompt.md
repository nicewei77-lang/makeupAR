# Eyebrow Makeup Feature Implementation Prompt

Status: Ready-to-use prompt  
Date: 2026-06-27  
Related product strategy: `docs/product/two-stage-ar-makeup-product-strategy.md`  
Related operating note: `docs/roadmaps/active/product-development-documentation-loop.md`

## Purpose

Use this prompt when asking an agent to implement the eyebrow makeup feature inside the existing AR makeup/filter and face correction app.

The prompt intentionally locks scope to the eyebrow makeup feature. The broader camera, photo, video, realtime AR, correction, and App Store product direction is background context, not permission to build the whole app.

## Prompt

```text
기존에 따로 개발 중인 메이크업 AR 필터/얼굴 보정 앱 안에 들어갈 "눈썹 메이크업 기능"만 구현해줘. 전체 앱 개발이 아니라 기능 모듈 구현이다.

제품 배경:
- 앱은 전면카메라/후면카메라를 모두 사용할 가능성이 있다.
- 앱은 사진, 동영상, 실시간 AR, 촬영 후 보정을 모두 포함할 가능성이 있다.
- 1단계는 "빠른 출시용 비상업 App Store 제품"이다. 실제 사용자가 받을 수 있는 앱이어야 하므로 UX, 안정성, 개인정보 고지, 권한 처리, App Store 심사는 상용 앱처럼 맞춘다. 다만 수익화, 유료 기능, 브랜드 제휴, 광고, 상업 캠페인, 제품 판매 연결은 끈다.
- 1단계부터 App Store 릴리즈 빌드에는 상업 사용 가능하고 무료이며, 재배포/App Store/모바일/카메라/얼굴 사용 제한이 명확히 없는 구성요소만 사용한다.
- 1단계부터 라이선스, 출처, 소유권, 장기 유지보수 가능성을 2단계와 같은 기준점으로 검토한다. 나중에 상업화 때 정리할 임시 재료가 아니라, 처음부터 장기 제품으로 이어질 수 있는 재료만 shipping path에 넣는다.
- 비상업, 연구용, 데모용, 평가판, 출처 불명 에셋/모델/LUT/SDK는 출시 경로에 넣지 않는다.
- 내부 리서치나 스파이크에서는 실험용 자료를 볼 수 있지만, shipping path, 즉 실제 App Store 빌드에 포함되는 코드/에셋/SDK/모델에는 절대 섞지 않는다.
- 2단계는 "상업용 자체개발 제품"이다. 1단계에서 이미 라이선스/소유권/장기 유지보수 기준을 적용하되, 2단계에서는 그 기준을 다시 확인하고 더 높은 상업 제품 품질로 끌어올린다.
- 2단계는 1단계에서 라이선스/소유권 문제를 처음 정리하는 단계가 아니라, 동일한 기준 위에서 품질 기준을 1단계보다 더 높이는 단계다. 1단계는 실제 사용자가 받을 수 있는 App Store 품질의 최소 기준이고, 2단계는 완전한 상업 제품으로서 시각적 자연스러움, 보정 품질, 카메라 모드 대응, 성능 안정성, 편집성, QA 깊이, 장기 유지보수성을 더 끌어올리는 단계다.

이번 작업 범위:
- Unity / AR Foundation / ARKit 기반 눈썹 메이크업 렌더링, 머티리얼, 좌표/앵커링, 프리셋 구조를 구현한다.
- React Native 쪽은 필요한 UI, 이벤트 연결, 프리셋 제어만 최소 수정한다.
- 앱 전체 카메라 시스템, 사진/동영상 저장, 전체 얼굴 보정 플로우, 온보딩, 결제, 광고, 백엔드, Android, App Store 제출 자동화는 구현하지 않는다.

기능 목표:
- 실시간 얼굴 추적 위에 자연스러운 눈썹 메이크업을 적용한다.
- 좌우 눈썹 위치, 각도, 크기, 색상, 투명도, 블렌딩이 얼굴 움직임에 안정적으로 따라가야 한다.
- 스티커처럼 붙은 느낌이 아니라 피부, 조명, 표정 변화에서 최대한 자연스럽게 보여야 한다.
- 컬러 프리셋 변경, 강도/투명도 조절, 좌우 비대칭 보정이 가능해야 한다.
- 얼굴 회전, 표정 변화, 추적 손실, 낮은 FPS 상황에서 튀는 위치나 잔상을 최소화한다.
- 추후 립, 치크, 아이, 카메라 모드, 사진/동영상/실시간 AR/보정 기능과 충돌하지 않는 구조로 만든다.

진행 방식:
- AGENTS.md를 먼저 읽어줘.
- 관련 문서도 읽어줘:
  - docs/product/two-stage-ar-makeup-product-strategy.md
  - docs/roadmaps/active/product-development-documentation-loop.md
- repo 리서치 -> 설계 -> 구현 -> 검증 -> 실패 분석 -> 수정 -> 재검증 루프로 진행해줘.
- 바로 구현하지 말고 현재 repo 구조와 기존 AR makeup 구현을 먼저 조사해줘.
- 구현 전에 접근 방식 2-3개, 장단점, 추천안을 설명하고 내 승인을 받아줘.
- 승인 후에는 Goal mode가 가능하면 "기존 AR 메이크업 앱 안의 눈썹 메이크업 기능을 상용 제품 퀄리티 목표로 구현"하는 목표를 설정해줘.
- 새 구현 루프를 시작할 때는 작업 모드/관련 스킬을 명시적으로 켜고, 어떤 모드로 진행하는지 먼저 알려줘.
- 내 승인이 필요한 지점으로 명시한 항목 외에는 네가 합리적으로 판단해서 계속 진행해줘.

멀티에이전트/서브에이전트:
- 필요하면 멀티에이전트와 서브에이전트를 사용해줘.
- 메인 에이전트는 전체 설계, 작업 분해, 최종 통합, 문서 일관성, 최종 검증을 책임져줘.
- 서브에이전트는 독립적인 작업에만 사용해줘.
- 같은 파일을 여러 에이전트가 동시에 수정하지 않도록 파일/모듈 소유 범위를 명확히 나눠줘.
- 가능한 역할 분담:
  - Unity 렌더링 에이전트: AR Foundation, face mesh, region mask, material, shader, blending
  - RN/iOS 에이전트: React Native UI, Unity bridge, iOS permission, App Store 관련 설정
  - 디버그 에이전트: 실패 로그 분석, 재현 조건 정리, 원인 후보 좁히기, 수정 후보 제안 또는 제한된 패치
  - 문서/QA 에이전트: 리서치, 개발 과정, 학습 노트, QA 체크리스트 정리
- 디버그 에이전트는 상시로 무작정 투입하지 말고, 테스트 실패, Unity compile 실패, RN bridge 이벤트 실패, iOS build 실패, AR tracking/렌더링 이상 현상 등 실패가 발생했을 때 투입해줘.
- 실패가 발생하면 멈추지 말고 디버그 담당 서브에이전트를 투입해서 재현 조건, 원인 분석, 수정 후보, 검증 결과를 정리하고, 메인 에이전트가 통합 판단 후 루프를 계속 돌려줘.

문서화:
- 리서치 내용, 개발 과정, 사용 기술, 선택 이유, 실패한 접근, 디버그 과정, 검증 결과를 문서로 계속 정리해줘.
- 문서는 단순 작업 일지가 아니라 내가 학습할 수 있게 작성해줘.
- "무엇을 했다"뿐 아니라 "왜 그렇게 했는지", "무엇을 배웠는지", "다음에 같은 문제를 보면 어떻게 판단해야 하는지"를 설명해줘.
- 사소한 코드 수정 하나하나는 문서화하지 말고, 중요한 결정/실패/검증/학습 포인트 중심으로 남겨줘.
- 나와 대화하면서 정한 중요한 결정, 승인/보류/거절, 방향 변경, 품질 피드백도 문서에 남겨줘.
- 전체 대화 원문을 그대로 저장하기보다는 날짜, 맥락/질문, 내 결정/피드백, 근거 자료, 다음 액션이 보이도록 간결한 decision log 형태로 남겨줘.
- 제품 요구사항과 UX 결정은 docs/product/에 정리해줘.
- 렌더링/AR/Unity/RN 구조와 기술 결정은 docs/architecture/에 정리해줘.
- 개발 순서와 진행 로그는 docs/roadmaps/active/에 정리해줘.
- 리서치 결과는 docs/roadmaps/research/ 또는 관련 feature 문서에 정리해줘.
- 반복 가능한 QA, 빌드, 디버그 절차는 docs/runbooks/에 정리해줘.
- 로그/스크린샷 같은 증거는 evidence/logs/ 또는 evidence/screenshots/에 저장해줘.
- TECH_VALIDATION_RESULT.md는 내가 명시적으로 검증 히스토리 업데이트를 요청하지 않는 한 건드리지 말고, 제품 결정은 product/architecture/roadmap 문서에 남겨줘.

Git 체크포인트:
- 커밋과 push는 에이전트가 의미 있는 체크포인트라고 판단할 때 진행하되, 사소한 수정마다 남발하지 마.
- 사용자 승인/방향 합의가 필요한 변경, 공개 대상이 불명확한 push, 범위가 애매한 변경이 섞였으면 먼저 상의해줘.
- 체크포인트 예시는 리서치/설계 문서 작성 완료, 독립 구현 slice 완료, 실패 수정 후 재검증 완료, QA/runbook 업데이트 완료다.
- 커밋 전에는 working tree를 확인하고, 이번 작업과 관련 있는 파일만 stage해줘.
- 사용자나 다른 에이전트가 만든 무관한 변경은 커밋에 섞지 마.
- generated/cache state, raw evidence, Xcode derived data, Unity Library/Logs, .DS_Store는 커밋하지 마.
- 커밋 메시지는 어떤 기능/문서/검증 체크포인트인지 알 수 있게 간결하게 작성해줘.
- push 전에는 현재 branch와 remote가 명확한지 확인해줘.
- branch, remote, credentials, 공개 대상이 불명확하면 push하지 말고 먼저 물어봐.
- 커밋 hash와 push 여부는 개발 로그에 남겨줘.

루프별 실기기 품질 확인:
- 한 루프는 의미 있는 구현 slice가 끝나고 가능한 로컬 검증까지 마친 시점으로 본다.
- 사용자가 실기기 품질 피드백을 주면 그 자체를 "다음 루프 합의 요청"으로 간주해줘.
- 실기기 품질 피드백을 받은 뒤에는 바로 코드 수정에 들어가지 말고, 먼저 아래 형식으로 다음 루프 제안을 작성하고 사용자 동의를 받아줘:
  - 이번 루프에서 고칠 항목
  - 건드리지 않을 항목
  - 개선 방식
  - 기대 효과와 트레이드오프
  - 검증 방법
  - iPhone 빌드 필요 여부
- 한 루프가 끝났다고 판단되면 다음 구현으로 바로 넘어가지 말고 나에게 품질 확인을 받아줘.
- 루프 종료 시 변경 내용, 로컬 검증 결과, 실기기에서 확인해야 할 품질 포인트를 요약해줘.
- 그 다음 Unity/RN 실기기 iPhone 빌드/설치 승인을 요청해줘. 이때 빌드 질문, primary path, target device/signing assumptions, expected risk, out-of-scope 항목을 같이 보고해줘.
- 내가 승인하면 repo 규칙에 따라 빌드하고 iPhone에 설치해서 내가 직접 품질을 확인할 수 있게 해줘.
- 내가 직접 확인한 뒤 피드백을 주면, 그 피드백을 바탕으로 다음 루프 방향을 함께 정해줘.
- 동의 전에는 새 구현 루프를 시작하지 말고, 동의 후에만 코드/에셋/검증 스크립트 수정을 시작해줘.
- 얼굴/카메라가 포함된 시각 품질 검증은 AI가 직접 스크린샷을 찍는 것이 아니라, 내가 iPhone에서 직접 확인하는 방식으로 진행해줘.
- 시각 품질 판단이 필요한 경우 나에게 관찰 피드백을 요청하고, 내가 원할 때만 품질 확인용 스크린샷 제공을 요청해줘.
- 요청할 스크린샷 예시는 정면 neutral, 좌/우 고개 회전, 표정 변화, 다른 강도/컬러 프리셋, 어색한 경계/오프셋/깜빡임/비대칭이 보이는 장면이다.
- 필요한 경우 네가 자율적으로 추가 QA 항목을 제안해줘. 예를 들어 손/머리카락/안경/그림자가 눈썹이나 얼굴 일부를 가리는 상황, 빠른 고개 움직임, 가까이/멀리 이동, 위/아래 고개 기울임, 조명 변화, 추적이 잠깐 끊겼다가 돌아오는 상황 등을 테스트해달라고 요청해줘.
- 단순히 "괜찮나요?"라고 묻지 말고, 현재 구현 리스크에 맞춰 구체적으로 질문해줘. 예: "빠르게 움직여도 눈썹 위치가 밀리지 않나요?", "손이 눈썹 일부를 가릴 때 깜빡임이나 튐이 있나요?", "좌우 회전에서 한쪽 눈썹이 떠 보이나요?", "강도/색상 변경 시 값이 즉시 반영되나요?"
- 매 루프마다 모든 항목을 요구하지 말고, 이번 변경에서 판단해야 할 리스크에 맞는 최소 QA 증거만 요청해줘.
- 스크린샷은 AI가 직접 촬영/수집하지 말고, 내가 제공하고 저장을 승인한 것만 evidence/screenshots/에 보관해줘.
- 문서에는 스크린샷 파일 경로, 촬영 조건, 관찰된 품질 문제/개선점, 다음 액션을 남겨줘.
- 민감하거나 내가 저장을 원하지 않으면 이미지를 저장하지 말고, 내가 말한 관찰 내용만 개발 로그에 요약해줘.
- 사용자 품질 확인과 다음 방향 합의가 끝나기 전에는 다음 구현 루프로 넘어가지 마.

학습용 문서에 포함할 내용:
- 사용한 Unity 컴포넌트와 역할
- 사용한 AR Foundation/ARKit 개념
- 얼굴 랜드마크, face mesh, region mask, 앵커링을 어떻게 해석했는지
- 머티리얼, 셰이더, 블렌딩, 투명도 처리 방식
- 좌우 눈썹 비대칭 보정 방식
- 추적 손실이나 낮은 FPS에서의 처리 방식
- React Native와 Unity 사이 이벤트 흐름
- iOS 카메라/사진/동영상/권한/App Store 관련 고려사항
- 사용한 라이브러리/에셋/모델/LUT/SDK의 라이선스와 상업 사용 가능 여부
- 실패한 접근과 버린 이유
- 검증 명령과 결과
- 남은 리스크와 실기기 QA 체크리스트

승인이 필요한 지점:
- 최초 설계안과 추천 접근 방식 확정
- 각 구현 루프 종료 후 사용자 실기기 품질 확인과 다음 루프 방향 확정
- Unity/RN 실기기 iPhone 빌드
- signing/team/device 대상이 필요한 Xcode 빌드
- AI/model inference, recommendation, backend upload, raw-frame storage 추가
- Android 작업
- 결제, 광고, 브랜드 제휴, 제품 판매 연결
- 상용 SDK 연동
- 라이선스가 불명확하거나 제한이 있을 수 있는 라이브러리/에셋/모델/LUT/SDK 사용
- 개인정보, App Store 심사, 카메라 데이터 처리 범위가 넓어지는 변경

빌드 규칙:
- Unity/RN real-device build가 필요하면 바로 진행하지 말고 먼저 빌드 질문, primary path, target device/signing assumptions, expected risk, out-of-scope 항목을 보고하고 내 승인을 받아줘.
- 승인된 Unity/RN device build 전에는 가능한 정적 검사, Unity batchmode import/compile, 로컬 preview, asset check 같은 실용 검증을 먼저 해줘.
- 승인된 Unity/RN device build는 repo 규칙에 따라 scripts/build_m3_unityframework.sh를 사용해 UnityFramework.framework를 재생성/동기화하는 절차를 따라줘.
- 특정 UDID나 DEVELOPMENT_TEAM을 repo 기본값으로 하드코딩하지 마.

완료 기준:
- 기존 앱 안에 통합 가능한 눈썹 AR 메이크업 기능 구현 완료
- 변경 파일과 변경 이유 요약
- 제품/기술/개발 로그/QA 문서 업데이트 완료
- 가능한 정적 검사/컴파일/로컬 검증 완료
- 실패가 있었다면 원인, 수정, 재검증 결과 문서화
- 의미 있는 체크포인트 커밋과 가능한 push 완료, 또는 push 불가 사유 보고
- 루프별 실기기 품질 확인 결과와 사용자 피드백 반영 내역 정리
- 사용자와의 주요 대화 결정, 승인 기록, 스크린샷 참조/관찰 내용 정리
- 실기기 빌드가 필요한 경우 승인 대기 지점 명확히 보고
- 남은 리스크와 다음 QA 항목 정리
```
