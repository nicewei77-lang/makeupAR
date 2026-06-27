# E7 Full-Face Region Generate Experiment Summary

Session: `session-20260626T195853Z`

Region decisions:
- lip: `pre-xcode-ready`
- blush: `pre-xcode-ready`
- brow: `pre-xcode-ready`
- eyeliner: `pre-xcode-ready`

Notes:
- All artifacts are local-only buildless outputs.
- Eyeliner produced a minimal-safe candidate and remains subject to blink/yaw iPhone evidence later.
- No Green/product-quality-ready claim is made.

Runtime handoff:
- Unity Resources now contain selected UV masks for `lip`, `blush`, `brow`, and `eyeliner`.
- RN can post a four-layer `e7_full_face_region_generate_v0` package to Unity before the later approved Xcode build.
- Unity accepts the product region IDs and stable `e7-*` mask texture IDs in source.

Verification:
- Python compile passed for the region generator and Unity asset installer.
- Unity runtime asset registry JSON validation passed.
- RN TypeScript check passed.
- Web review shell lint/typecheck/build passed before the RN/Unity handoff.
- Unity batchmode smoke passed after closing the stale Unity project-locking processes.

Deferred:
- Xcode/iPhone build, install, launch, and runtime camera evidence.
- Face attachment, expression/motion stability, blink/yaw eyeliner review, FPS/frame-time, latency, memory, and thermal evidence.
- Human visual acceptance for subjective cosmetic boundary quality.
