# E7 Eyeliner App Handoff UI Notes

Selected visual candidate: `asset-fit-wing-local-style-v0`
Tracking/reference anchor: `mp-upper-balanced-v0`
Secondary visual candidate: `mp-upper-balanced-v0`
Fallback candidate: `mp-tail-only-v0`

Implementation recommendation:

- Use MediaPipe upper eyelid landmarks as the primary tracker.
- Use `mp-upper-balanced-v0` as the clean tracking/reference anchor.
- Generate `asset-fit-wing-local-style-v0` style by default because human review preferred the outer-corner-filled look.
- Keep `mp-upper-balanced-v0` visible as a natural/balanced comparison option, not only as an internal anchor.
- Keep tail-only as the fallback when inner-eye spill or full-line instability appears.
- Color/edge may only be a small snap helper. It must not become the primary tracker.
- Face parsing remains an offline/evaluation helper, not runtime primary.

Reference-derived product rules:

- Good references favor upper-lashline anchored, outer-corner-filled wing eyeliner with a tapered tail.
- Default eyeliner must not become a full-lid black block.
- Default eyeliner must not close the whole eye with a heavy lower lashline ring.
- Keep lower-lid coverage off by default until a separate lower-line style is deliberately designed.
- Use `mp-upper-balanced-v0` as the natural comparison candidate, not as the only final look.

Controls:

- Sliders: `lineHeight`, `lineThickness`, `innerStart`, `outerReach`, `tailLength`, `tailAngle`, `tailLift`, `taper`, `softness`, `leftRightBalance`.
- Quick buttons: thin, move up/down, clear inner corner, shorten tail, lift tail, outer-only, mirror left/right, adjust one side only.

Deferred phone checks:

- Blink, squint, yaw, smile/open-mouth non-interference.
- Runtime UV texture sharpness for thin lines.
- Human visual acceptance on iPhone AR view.
