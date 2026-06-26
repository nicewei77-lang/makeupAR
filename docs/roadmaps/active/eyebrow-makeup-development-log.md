# Eyebrow Makeup Development Log

Status: Active
Date: 2026-06-27

## Context

The user requested implementation of only the eyebrow makeup feature inside the
existing React Native + Unity + AR Foundation makeup app. The broader camera,
photo/video, backend, AI, Android, monetization, and App Store submission
surfaces remain out of scope.

Relevant starting docs read:

- `AGENTS.md`
- `docs/product/two-stage-ar-makeup-product-strategy.md`
- `docs/roadmaps/active/product-development-documentation-loop.md`
- `docs/roadmaps/active/eyebrow-makeup-implementation-prompt.md`

## Repo Research Summary

Current runtime makeup path:

- React Native app: `rn/MakeupARValidation/App.tsx`
- RN tests: `rn/MakeupARValidation/__tests__/App.test.tsx`
- Unity bridge: `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- Unity region renderer:
  `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`
- Shader: `unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader`
- Mask resources:
  `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/`

Findings:

- The current bridge and Unity renderer accept only `lip`, `cheek`, and `eye`.
- No eyebrow runtime implementation exists yet.
- Existing rendering is ARFace UV mesh based through `smooth-region-mask`.
- Lip has extra atlas/culling/gloss behavior. Cheek and eye mostly use the same
  smooth mask renderer with different masks and material parameters.
- The worktree already contains unrelated uncommitted and untracked changes.
  Future staging must include only eyebrow-related files.

## Approved Direction

2026-06-27:

- User approved starting with approach 1: add eyebrow through the existing
  `smooth-region-mask` renderer.
- User asked if approaches 2 and 3 can be added later. Decision: yes, if RN
  keeps a stable `region="brow"` recipe contract and Unity owns renderer
  routing.
- User noted that existing regions should also eventually have separate
  renderers. Decision: prepare a region-to-renderer routing contract now, but do
  not split lip/cheek/eye renderers in the first eyebrow loop.

Initial route table:

- `lip` -> `smooth-region-mask`
- `cheek` -> `smooth-region-mask`
- `eye` -> `smooth-region-mask`
- `brow` -> `smooth-region-mask`

Future route table can replace any row with a dedicated renderer such as
`BrowMakeupRenderer`.

## Implementation Loop 1 Plan Summary

This is a summary only. A detailed implementation plan will be written after
the user reviews the design docs.

Expected first slice:

- Add `brow` to RN region types and recipe payloads.
- Add brow presets and minimal controls.
- Add tests that first fail for missing brow payload support.
- Add Unity parser and smooth-mask normalization support for `brow`.
- Generate an in-house procedural brow mask texture.
- Run RN tests, TypeScript, static checks, and Unity batchmode compile.
- Stop for real-device build approval before iPhone build/install.

## Approval Gates

Approval is still required before:

- Starting implementation after written spec review.
- Unity/RN real-device iPhone build or signing/device-targeted Xcode build.
- Any AI/model inference, recommendation, backend upload, or raw-frame storage.
- Android work.
- Payment, ads, brand partnership, product sales, or commercial SDK use.
- Any dependency, asset, model, LUT, or SDK with unclear license terms.

## Current Risks

- Brow UV mask fit is unknown until device QA.
- A generic smooth mask may not produce enough hair-like texture.
- Full renderer split is likely useful later but would increase first-loop
  regression risk if done before brow has a working visual baseline.
- Existing dirty worktree must be handled carefully to avoid committing
  unrelated user or generated changes.

## Checkpoints

- 2026-06-27: Goal created: "기존 AR 메이크업 앱 안의 눈썹 메이크업 기능을 상용 제품 퀄리티 목표로 구현".
- 2026-06-27: Design docs created for product behavior, AR rendering design,
  and development log. Implementation not started.
