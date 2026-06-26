# Codex-Claude 로컬 오케스트레이션 Runbook

## 목적

Codex 앱/CLI를 기본 구현 에이전트로 두고, Claude Code를 계획/비평/두 번째 시선으로 붙이는 로컬 워크플로우다. 이 repo에서는 제품 품질 AR evidence 규칙과 local-only privacy가 우선이다.

## 기본 구조

```txt
Claude Code
  -> 계획 / 리스크 / 대안 / Codex handoff brief

Codex
  -> repo 읽기 / 구현 / buildless 검증 / 결과 정리

scripts/agent_orchestration/codex_claude_orchestrator.py
  -> 안전 context bundle 생성
  -> Claude prompt 생성
  -> Claude brief를 Codex prompt로 연결
  -> 기본은 dry-run
```

루트 `CLAUDE.md`는 Claude Code가 이 repo에서 따라야 할 privacy/역할 경계다. Claude Code를 직접 열 때도 이 파일이 먼저 읽히도록 유지한다.

## 최초 설치

현재 `codex` CLI는 설치되어 있어야 한다. `claude` CLI가 없으면 공식 Claude Code 설치를 먼저 한다.

```bash
curl -fsSL https://claude.ai/install.sh -o /private/tmp/claude-install.sh
bash /private/tmp/claude-install.sh
```

설치 후 새 터미널을 열거나 shell PATH를 갱신한 뒤:

```bash
claude
```

로 로그인/초기 설정을 끝낸다.

## 진단

```bash
python3 scripts/agent_orchestration/codex_claude_orchestrator.py doctor
```

`claude`가 `missing`이면 설치 또는 PATH 설정이 끝나지 않은 상태다.

## 안전 context bundle만 만들기

```bash
python3 scripts/agent_orchestration/codex_claude_orchestrator.py context
```

출력은 기본적으로 `/private/tmp/makeupar-agent-orchestration/` 아래에 생긴다. 이 bundle은 `.env`, raw evidence, screen recording, generated mask, cache, build output을 제외한다. Snapshot은 기본 24,000자까지만 포함하며, 필요하면 `--max-snapshot-chars`로 조정한다.

## Claude -> Codex handoff 준비

기본은 dry-run이라 실제 Claude/Codex를 실행하지 않고 prompt 파일만 만든다.

```bash
python3 scripts/agent_orchestration/codex_claude_orchestrator.py run \
  --task "현재 active plan 기준으로 다음 buildless 검증 작업을 설계해줘"
```

Claude용 안전 context prompt를 만들 때:

```bash
python3 scripts/agent_orchestration/codex_claude_orchestrator.py run \
  --task-file /private/tmp/task.md \
  --send-safe-context-to-claude \
  --include-active-roadmap \
  --max-snapshot-chars 24000
```

Codex 앱 안에서 `--execute-claude --send-safe-context-to-claude` 조합은 외부 Claude 서비스로 repo-derived safe context를 보내는 작업이라 보안 정책에 의해 차단될 수 있다. 이 래퍼는 해당 조합을 실행하지 않고 `external_claude_execution_skipped.md`를 남긴다. 우회하지 말고 dry-run으로 생성된 `claude_prompt.md` / `safe_context_sent_to_claude.md`를 사용자가 직접 검토한 뒤, 외부 전송이 허용되는 별도 환경에서만 실행한다.

Claude brief를 확인한 뒤 Codex까지 실행할 때:

```bash
python3 scripts/agent_orchestration/codex_claude_orchestrator.py run \
  --task-file /private/tmp/task.md \
  --send-safe-context-to-claude \
  --include-active-roadmap \
  --execute-codex
```

위 명령은 Claude를 직접 호출하지 않는다. Claude brief를 이미 받은 경우에는 그 내용을 task 파일이나 별도 brief 파일에 붙여 Codex에게 전달한다.

## 금지선

- `.env`, `.env.*`, signing material, access token을 Claude 또는 Codex prompt에 넣지 않는다.
- raw camera frame, raw screen recording, generated mask package, Xcode/Unity build cache를 Claude에 보내지 않는다.
- iPhone build/install, 새 capture, camera permission, visual judgment는 사용자 승인 없이 진행하지 않는다.
- Claude brief는 참고 의견이다. Codex는 항상 `AGENTS.md`, `TECH_VALIDATION_RESULT.md`, active roadmap을 우선한다.
- 네 부위 중 일부만 완료하고 전체 성공이라고 기록하지 않는다.

## 추천 사용 패턴

큰 설계나 경계 판단:

```txt
Claude critique only -> 사용자가 brief 확인 -> Codex 구현
```

작은 코드 수정:

```txt
Codex 단독
```

민감 evidence가 필요한 시각 판단:

```txt
Codex가 evidence 위치와 판단 질문 정리 -> 사용자 직접 확인 -> Codex 기록
```

## 보안리뷰 차단 시 대체 패턴

보안리뷰를 우회하거나 속이지 않는다. 대신 Claude에 repo-derived context를 보내지 않는 방식으로 역할을 바꾼다.

### Blind Claude

Claude는 repo 파일, evidence, 경로, 현재 스냅샷을 보지 않는다. 사용자가 직접 적은 일반 문제 설명이나 템플릿만 보고 비평한다.

적합한 질문:

```txt
AR makeup 앱에서 lip/blush/brow/eyeliner 후보를 만들 때 흔한 실패 모드와 조정축을 제안해줘.
얇은 eyeliner mask를 만들 때 conservative fallback 후보를 어떻게 설계할지 비평해줘.
실기기 없이 pre-Xcode 단계에서 검증할 수 있는 체크리스트를 일반론으로 제안해줘.
```

부적합한 질문:

```txt
현재 repo 계획서를 읽고 누락을 찾아줘.
이 evidence 폴더를 보고 가장 좋은 후보를 골라줘.
TECH_VALIDATION_RESULT.md 기준으로 상태를 판정해줘.
```

흐름:

```txt
1. Codex가 repo를 보고 내부 판단/요약을 만든다.
2. Claude에는 repo 요약을 보내지 않는다.
3. Claude에는 일반화된 질문 또는 사용자가 직접 작성한 비민감 설명만 보낸다.
4. Codex가 Claude의 일반론을 repo 상태에 다시 매핑한다.
5. 최종 결정과 구현은 Codex가 evidence gate에 맞춰 한다.
```

### Template-Only Handoff

Codex는 Claude에게 보낼 내용을 채워주지 않고 빈 템플릿만 만든다. 사용자가 외부 전송 가능한 범위를 직접 채운다.

```txt
Objective:
Non-sensitive context written by user:
Constraints:
What to critique:
Do not request:
Expected output:
```

### Codex Internal Substitute

외부 전송이 전혀 불가능하면 Claude 역할을 Codex 내부 멀티에이전트로 대체한다.

```txt
Claude 역할 대체:
- Strict Critic Agent: 계획 누락/과장 claim 탐지
- Wildcard Agent: eyeliner/reference/fallback 아이디어 생성
- QA Agent: pre-xcode-ready/partial/blocked 판정 검증
- Designer Agent: 조정 UI와 사용자 흐름 비평
```
