# Two-Stage AR Makeup Product Strategy

Status: Draft product direction  
Date: 2026-06-27  
Owner: Product/engineering working document

## Purpose

This document records the current product direction for the AR makeup app so future implementation loops, research notes, and multi-agent work stay aligned.

The product may include:

- Front camera and rear camera usage.
- Photo capture, video capture, realtime AR, and post-capture correction.
- Product-quality makeup rendering across face regions such as lip, cheek, eye, and eyebrow.
- App Store distribution to real users.

The product should be developed in two stages. Both stages target commercial-grade product quality, but the allowed business and technical ingredients differ.

## Stage 1: Fast-Release Non-Commercial App Store Product

Stage 1 is a fast-release App Store product that real users can download and use.

Even though Stage 1 is non-commercial, user-facing quality must be treated like a commercial app:

- UX should feel complete enough for real users.
- Runtime stability should be taken seriously.
- Privacy notice, permissions, camera behavior, and App Store review readiness should be handled with commercial-app discipline.
- Product claims must match the actual review and QA evidence.

Stage 1 intentionally disables commercial surfaces:

- No monetization.
- No paid features.
- No brand partnerships.
- No advertising.
- No commercial campaigns.
- No product purchase or sales connection.

Stage 1 should use commercially compatible free components by default, even though the app itself is non-commercial.

Stage 1 should apply the same baseline review standard as Stage 2 for license, ownership, and long-term maintainability. A component should not ship in Stage 1 unless its license, provenance, ownership, and maintenance outlook are acceptable for the intended mobile app distribution, commercial use, and future product continuation.

For the App Store release build, avoid temporary, research-only, demo, or non-commercial components.

Internal prototypes may temporarily use research-oriented or demo materials only when they are kept out of App Store builds and clearly marked as non-shipping experiments.

Stage 1 dependency and asset selection should prefer:

- Apple platform frameworks and APIs that are suitable for App Store apps.
- In-house code, shaders, masks, LUTs, templates, and assets.
- Free open-source libraries with permissive commercial-use licenses and acceptable notice obligations.
- Free assets or models with clear commercial-use rights and no practical product restrictions.
- Components with clear provenance, ownership, update path, replacement path, and long-term maintainability.

Avoid by default:

- Non-commercial, research-only, evaluation-only, or demo-only licenses.
- Components with unclear redistribution, App Store, mobile, face/camera, or commercial-use terms.
- SDKs with hidden usage limits, watermarking, required branding, required data sharing, or future paywalls.
- Strong copyleft dependencies that could create product or distribution obligations unless explicitly reviewed and approved.
- Assets, LUTs, templates, fonts, or models whose provenance cannot be documented.

## Stage 2: Commercial Self-Developed Product

Stage 2 is the commercial product line.

Stage 2 should raise the quality bar beyond Stage 1. Stage 1 already uses the same baseline review standard for license, ownership, and long-term maintainability, so Stage 2 is not a first-time cleanup phase. Stage 2 should improve visual realism, correction quality, camera-mode coverage, performance stability, editability, QA depth, and long-term maintainability for a fully commercial product.

Before Stage 2 release, any remaining Stage 1 component that is not clearly owned by us or suitable for the commercial product must be removed or replaced.

Replacement targets include:

- Non-commercial or research-only libraries.
- Demo SDKs.
- Temporary models.
- Trial assets.
- LUTs with unclear commercial rights.
- Templates or sample assets that are not ours or not clearly licensed for commercial use.

Stage 2 should use only components that are:

- Developed by us.
- Commercially licensed for the intended use.
- Open-source with licenses reviewed and accepted for the product.
- Documented with clear ownership, provenance, and usage limits.

## Shared Quality Bar

Both stages should aim for commercial product quality in the user experience.

Stage 1 defines the minimum real-user App Store quality bar. Stage 2 should exceed that bar rather than only replacing licenses or dependencies.

That means:

- Makeup rendering should look intentional and natural, not like a debug overlay.
- Camera permission and privacy behavior should be understandable.
- Front and rear camera behavior should be documented separately when their UX or technical constraints differ.
- Photo, video, realtime AR, and correction workflows should be treated as distinct product modes.
- Stability and performance should be verified with evidence before readiness claims are made.
- Known limitations should be recorded rather than hidden.

## Privacy and Data Boundaries

AI/model inference, backend upload, recommendation, raw camera frame storage, or any persistent face/camera data handling requires explicit approval and privacy review before implementation.

By default:

- Do not store raw camera frames.
- Do not upload face or camera data.
- Do not add AI/model inference unless the scope is explicitly approved.
- Do not claim privacy, App Store, commercial, or production readiness without matching review evidence.

## Documentation Expectations

Research, development process, and technical decisions should be documented as the product evolves.

The goal is not to create heavy paperwork. The goal is to preserve memory and make the work teachable.

Each substantial feature or phase should record:

- What was researched.
- What was decided.
- Which technologies, libraries, Unity components, AR Foundation concepts, assets, shaders, or platform APIs were used.
- Why those choices were made.
- Which alternatives were considered and rejected.
- Which files changed and what role each file has.
- Which validation commands or manual QA checks were run.
- What failed, what was learned, and how the plan changed.
- What remains risky or unverified.

Learning notes should explain the concepts behind the work, not only the final result. For AR makeup, this may include face tracking, face mesh usage, region masks, anchors, materials, shaders, blending, camera modes, RN-to-Unity messaging, iOS permissions, and App Store review constraints.

## Document Locations

Use repo document locations consistently:

- Product requirements and user behavior: `docs/product/`
- Rendering architecture, AR anchoring, and technology decisions: `docs/architecture/`
- Execution, build, release, and QA procedures: `docs/runbooks/`
- Development order, active plans, and progress logs: `docs/roadmaps/active/`
- Research reports and supporting analysis: `docs/roadmaps/research/`
- Logs and screenshots used as evidence: `evidence/logs/` and `evidence/screenshots/`

Historical validation snapshots should remain decision history. Product progress should not be forced into `TECH_VALIDATION_RESULT.md` unless the work explicitly updates validation history.

## Recommended Operating Model

For major product work, use this sequence:

1. Read `AGENTS.md` and the relevant product or architecture docs.
2. Do a small repo research pass to find the current implementation structure.
3. Write or update a short product/design note before implementation.
4. Decide the implementation path and record the tradeoffs.
5. Set the active goal when goal mode is useful.
6. Use multi-agent work only for independent areas such as Unity rendering, React Native integration, QA, and documentation.
7. Implement in small loops.
8. Verify with practical checks before any real-device build.
9. Update the development log with decisions, failures, validation, and next steps.
10. Ask for approval before Unity/RN real-device builds or any scope expansion into AI, backend, upload, payments, Android, or commercial SDK integration.

Documents should act as memory and coordination aids, not as blockers. Keep them concise enough to maintain during active development.
