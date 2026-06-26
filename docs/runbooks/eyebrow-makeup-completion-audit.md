# Eyebrow Makeup Completion Audit

Status: Not complete; implementation loop is waiting for cleanup/build approval
Date: 2026-06-27

This audit checks the current eyebrow makeup feature against the original module
request. It is intentionally stricter than the local test suite: a requirement
is marked complete only when current evidence proves it, not when the code looks
plausible.

## Evidence Sources

- Product spec: `docs/product/eyebrow-makeup-feature.md`
- Architecture design: `docs/architecture/eyebrow-ar-rendering-design.md`
- Development log: `docs/roadmaps/active/eyebrow-makeup-development-log.md`
- QA runbook: `docs/runbooks/eyebrow-makeup-qa-runbook.md`
- RN app contract: `rn/MakeupARValidation/App.tsx`
- RN focused tests: `rn/MakeupARValidation/__tests__/App.test.tsx`
- Unity bridge: `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- Unity renderer: `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
- Renderer routes:
  `unity/MakeupARUnityValidation/Assets/Scripts/MakeupRegionRendererRoutes.cs`
- Brow mask asset:
  `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png`

## Current Verification Snapshot

Fresh local checks recorded on 2026-06-27:

| Check | Status |
| --- | --- |
| `python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py` | Passed |
| `python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py` | Passed |
| `python3 scripts/e7_reference_atlas/verify_region_renderer_routes.py` | Passed |
| `npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand` | Passed, 23 tests |
| `npm run lint` | Passed |
| `npx tsc --noEmit` | Passed |

Unity batchmode import/compile passed earlier with Unity `6000.3.18f1`, but it
has not been rerun after the later brow-specific C# mask policy change because
the machine has less than `400Mi` free on `/System/Volumes/Data`.

## Requirement Audit

| Requirement | Current Evidence | Status |
| --- | --- | --- |
| Implement only the eyebrow makeup module inside the existing app | Product docs keep camera/photo/video/backend/AI/Android/payment out of scope; code changes are limited to RN recipe/UI, Unity bridge/rendering, mask asset, verifiers, and docs | Satisfied for current loop |
| Unity / AR Foundation / ARKit based eyebrow rendering | Brow is accepted by `RNBridge`, routed by `MakeupRegionRendererRoutes`, and rendered by `E3RegionMaskOverlay` through the existing ARFace smooth UV mask path | Locally implemented; device proof pending |
| React Native minimal UI, events, presets | RN focused tests cover brow as fourth region, brow HUD controls, and four-layer recipe dispatch | Locally verified |
| Natural brow presets | `natural_brow`, `soft_brow`, `brow-drawn-mask-v1`, brow color/material cases, and brow-specific mask threshold/feather are covered by static verifiers | Locally verified |
| Stable renderer structure that will not block later lip/cheek/eye/brow splits | `MakeupRegionRendererRoutes` exposes per-region renderer ids while preserving `region` as the RN contract | Locally verified |
| In-house, shipping-safe brow mask asset | `brow-drawn-mask-v1.png` is generated procedurally by repo script; docs record no third-party asset or unclear license path | Locally verified |
| Brow placement avoids obvious eye/cheek/lip mask overlap | Mask verifier checks active pixels, bbox, two components, and overlap thresholds | Locally verified |
| Color, opacity, intensity, feather, coverage, material response | RN payload and Unity renderer parse/apply these fields; focused Jest and static contract verifiers cover the payload and acceptance path | Locally verified; visual quality pending |
| Face-attached motion under head turns | ARFace UV mesh attachment is implemented, but no current real-device visual evidence exists after brow integration | Not proven |
| Natural appearance under lighting and expression change | Material policy is conservative, but no current real-device visual evidence exists | Not proven |
| Tracking loss and low-FPS behavior does not leave stale brow artifacts | Existing renderer has tracking fade/hide behavior, but brow-specific real-device behavior has not been observed | Not proven |
| Left/right asymmetry correction is possible | The current first loop supports symmetric procedural brow masks and shared tuning; explicit left/right asymmetry controls are not implemented | Incomplete |
| Existing lip/cheek/eye behavior is not regressed | RN tests and static route checks pass; Unity compile passed before the latest C# policy change; no device smoke test yet | Partially proven |
| Product/technical/development/QA docs updated | Product, architecture, development log, QA runbook, and this audit are present | Satisfied for current loop |
| Meaningful checkpoint commits and push | Branch `feature/brow-0626` has pushed implementation and pre-build verification checkpoints; this audit is a separate checkpoint | Satisfied for current loop |
| Real-device iPhone build and user quality feedback | Not approved or run yet | Missing approval/evidence |

## Blocking Approval Items

The next progress step requires explicit user approval because it touches
generated cleanup and device build workflow:

1. Clean enough generated/cache output to allow Unity/RN build work. Candidate:
   `unity-builds` at about `3.1G`. Optional candidate:
   `unity/MakeupARUnityValidation/Library` at about `793M`, with Unity reimport
   cost.
2. Rerun Unity batchmode import/compile after the brow C# mask-policy change.
3. Run the approved real-device path:
   `bash scripts/build_m3_unityframework.sh`, then RN/Xcode on the
   user-approved iPhone and signing team.
4. Collect user visual QA observations for frontal neutral, left/right head
   turns, expression change, color/intensity update, tracking recovery, and
   existing lip/cheek/eye smoke behavior using the observation template in
   `docs/runbooks/eyebrow-makeup-qa-runbook.md`.

## Current Conclusion

The current codebase has a locally verified first-loop eyebrow makeup module,
but the full objective is not complete. Completion still needs at least:

- Unity compile after the latest brow C# policy change.
- Real-device iPhone build/install.
- User visual QA confirming product-quality placement and attachment.
- A decision on whether explicit left/right asymmetry correction must be added
  before calling the eyebrow module complete.
