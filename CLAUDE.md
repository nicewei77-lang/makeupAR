# CLAUDE.md

This repository is primarily operated by Codex. Claude Code may be used as a
planning, critique, and second-opinion agent, but Codex remains the default
implementer for repo edits unless the user explicitly says otherwise.

## Required Context
- Read `AGENTS.md` first.
- Treat `TECH_VALIDATION_RESULT.md` > `Current Session Snapshot` as the current
  boundary source.
- Open `docs/roadmaps/README.md` as the roadmap menu and then only the active
  roadmap named by the snapshot.

## Privacy And Evidence Rules
- Do not read or summarize `.env`, `.env.*`, signing files, access tokens, or
  private credentials.
- Do not inspect, upload, transform, or retain raw camera frames, screen
  recordings, generated evidence folders, Xcode/Unity build outputs, or
  `.cache` artifacts unless the user explicitly asks for that exact evidence
  item.
- Prefer source files, docs, schemas, and curated summaries over raw evidence.
- If visual or device judgment is required, stop and ask the user instead of
  inferring product-quality success.

## Role In Codex-Claude Workflows
- Default role: critique, risk review, alternative plan, or prompt handoff for
  Codex.
- Produce concise, actionable briefs with file paths, assumptions, risks, and
  verification suggestions.
- Do not claim E7 product-quality readiness, runtime readiness, or Green status
  without the evidence gates recorded in `TECH_VALIDATION_RESULT.md`.
- Do not run Unity/RN iPhone builds, new capture, uploads, commercial SDK
  integration, Android work, or live face parsing/Core ML runtime unless the
  active plan and the user explicitly authorize it.

## Handoff Format
When handing work back to Codex, use this shape:

```txt
Objective:
Scope:
Files likely involved:
Do not touch:
Known constraints:
Suggested implementation steps:
Suggested verification:
Open questions:
```
