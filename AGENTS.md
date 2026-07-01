# AGENTS.md

## Scope
- Finish the eyebrow filter implementation directly in this repo.
- Keep decisions practical and code changes minimal.
- Do not keep re-planning when implementation can move forward.

## Only Hard Guardrail
- Do not modify or regress existing eye and cheek/blush behavior.

## Eyebrow Work
- It is allowed to change eyebrow UI, schema, Unity bridge, Unity shader/material, masks, generated eyebrow assets, and preview/evidence scripts.
- Eyebrow assets should live in Unity Resources when runtime rendering needs them.
- Candidate images are inputs for brow texture/density; runtime placement should be driven by the brow boundary/engine logic, not by screenshots pretending to be runtime proof.

## Validation
- Run focused checks when they help confirm the current change.
- Do not block progress on broad milestone gates, excessive evidence rules, or old roadmap boundaries.
- Real-device AR validation is useful, but implementation can continue without turning every step into a formal gate.
