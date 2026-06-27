# Docs Index

이 폴더는 루트 active 문서 밖의 제품 기획, AR validation 계획, 리서치, 재실행 절차를 보관한다.

루트 active 문서는 계속 아래 3개다.

- `AGENTS.md`
- `TECH_VALIDATION_TEST_PLAN.md`
- `TECH_VALIDATION_RESULT.md`

## 어디를 먼저 볼지

| 목적 | 문서 |
| --- | --- |
| 제품 단계 전략과 상용/비상업 경계 | `product/two-stage-ar-makeup-product-strategy.md` |
| AI 루프/멀티에이전트 개발 문서화 방식 | `roadmaps/active/product-development-documentation-loop.md` |
| 눈썹 메이크업 기능 구현용 프롬프트 | `roadmaps/active/eyebrow-makeup-implementation-prompt.md` |
| 현재 상태와 다음 boundary 확인 | `../TECH_VALIDATION_RESULT.md` > `Current Session Snapshot` |
| 안정적인 foundation validation 계약 확인 | 필요할 때만 `../TECH_VALIDATION_TEST_PLAN.md` 관련 섹션 |
| AR engine validation 과거/배경 지시서 | `roadmaps/active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` |
| E7 active 세부 계획 찾기 | `roadmaps/README.md` > `Active` |
| 제품 기획 참고 | `product/AIAR_MakeupGuide기획서_v1.md` |
| AR/beauty engine research 근거 | `roadmaps/research/`에서 milestone별 lazy-load |
| 이전/상위 전략 참고 | `roadmaps/strategy/` |
| 반복 실행 절차 | `runbooks/` |
| 로컬 생성물 정리 | `runbooks/LOCAL_WORKSPACE_CLEANUP_RUNBOOK.md` |
| 팀 온보딩/공유 전 요구사항 | `runbooks/TEAM_SHARE_REQUIREMENTS_KO.md` |

## 폴더 역할

| Folder | Role |
| --- | --- |
| `product/` | 서비스/제품 기획과 durable product decision 문서. Validation milestone의 현재 상태를 대체하지 않는다. |
| `roadmaps/active/` | 현재 제품 개발 계획, 진행 로그, AI 루프/멀티에이전트 운영 노트. |
| `roadmaps/strategy/` | 상위 전략/로드맵 참고 문서. 현재 boundary는 `TECH_VALIDATION_RESULT.md`를 우선한다. |
| `roadmaps/research/` | 공개 자료 기반 research report/plan. 구현 지시서가 아니라 판단 근거다. |
| `roadmaps/archive/` | 중복되었거나 현재 기준으로는 보조적인 과거 문서. |
| `runbooks/` | 재사용 가능한 실행 절차. |
