# E7 Eyeliner App Handoff UI Notes

Selected candidate: `mp-upper-balanced-v0`
Fallback candidate: `mp-tail-only-v0`

Implementation recommendation:

- Use MediaPipe upper eyelid landmarks as the primary tracker.
- Generate a parametric natural/minimal line by default.
- Keep wing as a user-expanded style preset, not as the first default.
- Keep tail-only as the fallback when inner-eye spill or full-line instability appears.
- Color/edge may only be a small snap helper. It must not become the primary tracker.
- Face parsing remains an offline/evaluation helper, not runtime primary.

Controls:

- Sliders: `lineHeight`, `lineThickness`, `innerStart`, `outerReach`, `tailLength`, `tailAngle`, `tailLift`, `taper`, `softness`, `leftRightBalance`.
- Quick buttons: thin, move up/down, clear inner corner, shorten tail, lift tail, outer-only, mirror left/right, adjust one side only.

Deferred phone checks:

- Blink, squint, yaw, smile/open-mouth non-interference.
- Runtime UV texture sharpness for thin lines.
- Human visual acceptance on iPhone AR view.
