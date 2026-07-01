# Eyebrow Implementation Plan

## Goal
Implement the eyebrow filter until it works naturally in Unity AR.

## Hard Guardrail
- Do not modify or regress existing eye and cheek/blush behavior.

## Implementation Direction
- Use a boundary-first eyebrow engine.
- Keep eyebrow placement separate from candidate PNG placement.
- Use candidate 1-5 assets as hair texture/density inputs only.
- Render color, neutralizer, feathering, and strand texture inside the eyebrow boundary.
- Keep eyebrow assets in Unity Resources when needed by runtime.

## Work Order
1. Fix the runtime eyebrow boundary and placement.
2. Make candidate 1-5 visibly different.
3. Make colors visibly different, including black, brown, dark brown, light brown, and wine.
4. Ensure eyebrow can be active together with existing makeup layers.
5. Generate expected renders for visual review when useful.
6. Build or run on device when it is actually needed to confirm AR behavior.
