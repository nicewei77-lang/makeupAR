# Docs Index

이 폴더는 루트 active 문서 밖의 제품 기획, 경쟁사/Twinit 리서치, AR validation 기록, 로드맵, 재실행 절차를 보관한다.

루트 active 문서는 계속 아래 3개다.

- `AGENTS.md`
- `TECH_VALIDATION_TEST_PLAN.md`
- `TECH_VALIDATION_RESULT.md`

## 어디를 먼저 볼지

| 목적 | 문서 |
| --- | --- |
| 현재 상태와 다음 작업 boundary 확인 | `../TECH_VALIDATION_RESULT.md` > `Current Session Snapshot` |
| 저장소 작업 규칙 확인 | `../AGENTS.md` |
| 상용 제품화/규제/출시 준비 | `product/COMMERCIAL_READINESS_REGULATORY_GUARDRAILS_KO.md` |
| 제품 기획/다음 기능 논의 | `product/AIAR_MakeupGuide기획서_v1.md` 또는 사용자 지정 문서 |
| Twinit/경쟁사 크롤링 결과 분석 | `../twinit-crawler/README.md`, `../twinit-crawler/data/csv/` |
| AR engine validation 기록/재개 | `roadmaps/README.md` > `Active` |
| 안정적인 foundation validation 계약 감사 | 필요할 때만 `../TECH_VALIDATION_TEST_PLAN.md` 관련 섹션 |
| AR/beauty engine research 근거 | `roadmaps/research/`에서 작업별 lazy-load |
| 이전/상위 전략 참고 | `roadmaps/strategy/` |
| 반복 실행 절차 | `runbooks/` |
| 로컬 생성물 정리 | `runbooks/LOCAL_WORKSPACE_CLEANUP_RUNBOOK.md` |
| 팀 온보딩/공유 전 요구사항 | `runbooks/TEAM_SHARE_REQUIREMENTS_KO.md` |

## 폴더 역할

| Folder | Role |
| --- | --- |
| `product/` | 서비스/제품 기획과 상용 출시 가드 문서. 검증 이후 제품/기능 작업의 주요 입력이 될 수 있다. |
| `roadmaps/active/` | AR validation 재개용 active 계획과 배경 지시서. 비-AR 작업을 자동으로 막지 않는다. |
| `roadmaps/strategy/` | 상위 전략/로드맵 참고 문서. 현재 작업 boundary는 사용자 요청과 `TECH_VALIDATION_RESULT.md`를 우선한다. |
| `roadmaps/research/` | 공개 자료 기반 research report/plan. 구현 지시서가 아니라 판단 근거다. |
| `roadmaps/archive/` | 중복되었거나 현재 기준으로는 보조적인 과거 문서. |
| `runbooks/` | 재사용 가능한 실행 절차. |
