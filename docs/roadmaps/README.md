# Roadmaps Index

현재 작업 지시서는 `active/`에 둔다. 과거 계획, research, strategy 문서는 현재 milestone boundary를 대체하지 않는다.

Token-safe reading rule:

- Do not load `active/`, `research/`, or `archive/` as a whole folder.
- Treat the tables below as a menu. Open only the one file selected by `../../TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`.
- When a `_KO.md` primary plan and `_KR.md` companion both exist, agents should read `_KO.md` by default and open `_KR.md` only for user/team-facing wording.

## Active

| File | Use |
| --- | --- |
| `active/product-development-documentation-loop.md` | 제품 리서치, 개발 과정, 학습 포인트, AI 루프/멀티에이전트 운영 기록 방식. |
| `active/eyebrow-makeup-implementation-prompt.md` | 기존 AR 메이크업 앱 안의 눈썹 메이크업 기능만 구현하도록 scope를 잠근 ready-to-use 프롬프트. |
| `active/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` | M6-E6/E7 배경 지시서. 현재 boundary와 다음 세션 라우팅은 `../../TECH_VALIDATION_RESULT.md` snapshot을 우선한다. |
| `active/E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` | E7 전체 spike boundary, E7.3-E7.6 라우팅, cosmetic renderer 진입 조건. |
| `active/E7_REGION_PRECISION_SUBSPIKE_PLAN.md` | E7.03/E7.3 region precision, Q3 overlay-ready 기준, Yellow boundary risk. |
| `active/E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md` | E7.6 FPS/frame-time, thermal, memory, latency evidence 계약. |
| `active/E7_COSMETIC_RENDERING_TEAM_CHECK_PLAN_KO.md` | 팀원이 보는 E7.4/E7.5 cosmetic rendering 실험 범위와 진입 조건. |
| `active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md` | future agent용 reference-driven UV atlas 구현 계약. |
| `active/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KR.md` | UV atlas 계획의 사용자/팀원용 한국어 companion. 에이전트는 `_KO.md`를 읽은 경우 기본적으로 열지 않는다. |
| `active/E7_EXTERNAL_MASK_PRIOR_SUBSPIKE_PLAN_KO.md` | external mask prior 탐색 가드레일. 명시적으로 재개할 때만 사용한다. |

## Strategy

| File | Use |
| --- | --- |
| `strategy/AR_FIRST_TECH_VALIDATION_ROADMAP.md` | AR-first 큰 방향과 phase 구분을 볼 때 참고한다. 최신 상태는 `../../TECH_VALIDATION_RESULT.md`를 우선한다. |

## Research

| File | Use |
| --- | --- |
| `research/AR_ENGINE_RESEARCH_REPORT_KO.md` | AR alignment, lifecycle, region mask, texture sample 설계 근거. |
| `research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md` | 상용/소셜 beauty AR engine capability와 v1 설계 교훈. |
| `research/E7_AXIS1_FACE_REGION_TRACKING_*.md` | E7.3 region precision 작업 때만 lazy-load한다. |
| `research/E7_AXIS2_COSMETIC_RENDERING_*.md` | E7.4/E7.5 cosmetic rendering 작업 때만 lazy-load한다. |
| `research/AR_ENGINE_RESEARCH_PLAN_KO.md` | research 진행 계획. 현재 구현 지시서는 아니다. |

## Archive

| File | Use |
| --- | --- |
| `archive/AR_ENGINE_RESEARCH_PLAN.md` | 영어 research plan 백업. 한국어 research plan/report를 우선한다. |
| `archive/TECH_VALIDATION_HISTORY_2026-06-22.md` | 2026-06-22 snapshot 축소 전 `TECH_VALIDATION_RESULT.md` 전체 이력 백업. |
