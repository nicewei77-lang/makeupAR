# Roadmaps Index

현재 작업 지시서는 `active/`에 하나만 둔다. 과거 계획, research, strategy 문서는 현재 milestone boundary를 대체하지 않는다.

Token-safe reading rule:

- Do not load `active/`, `research/`, or `archive/` as a whole folder.
- Treat the tables below as a menu. Open only the one file selected by `../../TECH_VALIDATION_RESULT.md` > `Current Session Snapshot`.
- When a `_KO.md` primary plan and `_KR.md` companion both exist, agents should read `_KO.md` by default and open `_KR.md` only for user/team-facing wording.

## Active

| File | Use |
| --- | --- |
| `active/E7_FULL_FACE_REGION_GENERATE_COMPLETE_IMPLEMENTATION_PLAN_KO.md` | E7 립 / 블러셔 / 눈썹 / 아이라인 region Generate 완전 구현 계획. CLI 실험, 웹앱 검증, RN/Unity 적용 준비, pre-Xcode build gate package까지의 현재 작업 계약. iPhone/Xcode 빌드와 실기기 테스트는 다음 phone-connected 세션으로 deferred. |

## Strategy

| File | Use |
| --- | --- |
| `strategy/AR_FIRST_TECH_VALIDATION_ROADMAP.md` | AR-first 큰 방향과 phase 구분을 볼 때 참고한다. 최신 상태는 `../../TECH_VALIDATION_RESULT.md`를 우선한다. |

## Research

| File | Use |
| --- | --- |
| `research/AR_ENGINE_RESEARCH_REPORT_KO.md` | AR alignment, lifecycle, region mask, texture sample 설계 근거. |
| `research/BEAUTY_AR_ENGINE_BENCHMARK_REPORT_KO.md` | 상용/소셜 beauty AR engine capability와 v1 설계 교훈. |
| `research/E7_COSMETIC_CONTROL_MAP_MERGE_REHEARSAL_PLAN_KO.md` | `blush-mask` 화장품 renderer와 런타임 생성 RGBA control map을 별도 thread/worktree에서 모의병합하기 위한 충돌 지도, 멀티 에이전트 역할, buildless 검증 계획. 현재 active 구현 계약은 아니다. |
| `research/E7_EYELINER_MASK_CANDIDATE_FINAL_EXPERIMENT_PLAN_KO.md` | 앱 구현 직전 아이라인 후보를 MediaPipe upper eyelid landmark, parametric curve, style preset, 사용자 조정축 기준으로 빠르게 확정하기 위한 buildless 최종 실험 계획. |
| `research/E7_AXIS1_FACE_REGION_TRACKING_*.md` | E7.3 region precision 작업 때만 lazy-load한다. |
| `research/E7_AXIS2_COSMETIC_RENDERING_*.md` | E7.4/E7.5 cosmetic rendering 작업 때만 lazy-load한다. |
| `research/AR_ENGINE_RESEARCH_PLAN_KO.md` | research 진행 계획. 현재 구현 지시서는 아니다. |

## Archive

| File | Use |
| --- | --- |
| `archive/AR_ENGINE_VALIDATION_IMPLEMENTATION_PLAN_KO.md` | M6-E6/E7 배경 지시서. 현재 boundary와 다음 세션 라우팅은 `../../TECH_VALIDATION_RESULT.md` snapshot을 우선한다. |
| `archive/AR_ENGINE_RESEARCH_PLAN.md` | 영어 research plan 백업. 한국어 research plan/report를 우선한다. |
| `archive/E7_VISUAL_PRODUCT_READINESS_SPIKE_PLAN.md` | E7 전체 spike boundary, E7.3-E7.6 라우팅, cosmetic renderer 진입 조건. |
| `archive/E7_REGION_PRECISION_SUBSPIKE_PLAN.md` | E7.03/E7.3 region precision, Q3 overlay-ready 기준, Yellow boundary risk. |
| `archive/E7_LIP_BOUNDARY_PRE_AR_CALIBRATION_SPIKE_PLAN_KO.md` | E7.03 lip-first pre-AR boundary calibration 계약. lip boundary lane을 다시 열 때만 사용한다. |
| `archive/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KO.md` | reference-driven UV atlas 구현 계약. 다시 필요할 때만 연다. |
| `archive/E7_REFERENCE_DRIVEN_UV_ATLAS_PLAN_KR.md` | UV atlas 계획의 사용자/팀원용 한국어 companion. `_KO.md`를 우선한다. |
| `archive/E7_LIP_SAMPLE_PACK_V0_RUNTIME_REVIEW_CONTEXT_KO.md` | lip sample v0 runtime review 컨텍스트. lip sample 튜닝을 재개할 때만 연다. |
| `archive/E7_LIP_CANDIDATE_GENERATOR_FAST_SPIKE_PLAN_KO.md` | E7 lip candidate generator fast spike 완료 계획. 후보 생성 결과/설계 맥락을 다시 확인할 때만 연다. |
| `archive/E7_LIP_PERSONALIZED_GENERATE_FULL_IMPLEMENTATION_PLAN_KO.md` | E7 개인 맞춤 립 Generate 완전 구현 계획. 현재 전체 부위 Generate 계획으로 superseded 되었으며, lip-only 웹앱/로컬서버/RN-Unity 설계를 다시 확인할 때만 연다. |
| `archive/E7_PERFORMANCE_EVIDENCE_SUBSPIKE_PLAN.md` | E7.6 FPS/frame-time, thermal, memory, latency evidence 계약. |
| `archive/E7_COSMETIC_RENDERING_TEAM_CHECK_PLAN_KO.md` | 팀원이 보는 E7.4/E7.5 cosmetic rendering 실험 범위와 진입 조건. |
| `archive/E7_EXTERNAL_MASK_PRIOR_SUBSPIKE_PLAN_KO.md` | external mask prior 탐색 가드레일. 명시적으로 재개할 때만 사용한다. |
| `archive/TECH_VALIDATION_HISTORY_2026-06-22.md` | 2026-06-22 snapshot 축소 전 `TECH_VALIDATION_RESULT.md` 전체 이력 백업. |
