# Product Development Documentation Loop

Status: Active operating note  
Date: 2026-06-27  
Related product strategy: `docs/product/two-stage-ar-makeup-product-strategy.md`

## Why This Exists

Long-running AI implementation loops can lose context if decisions live only in chat. Multi-agent work makes this more important because each agent may receive a smaller slice of context.

This document defines how to preserve research and development memory without turning documentation into the main task.

## Principle

Use documentation as a lightweight memory system.

Good documentation should answer:

- What are we trying to build?
- What did we learn before choosing this path?
- Why did we choose this implementation?
- What changed during development?
- What should the next agent or human know before continuing?

Avoid documenting every tiny edit. Record meaningful decisions, failed attempts, validation evidence, and learning points.

## Recommended Flow

For substantial product features:

1. Repo research
   - Read the relevant current code, docs, scripts, and build constraints.
   - Summarize only what affects the feature.

2. Short design note
   - Record the intended UX, technical approach, alternatives, risks, and validation plan.
   - Keep this short enough that it can be updated during the loop.

3. Goal setup
   - If goal mode is useful, set the goal after the initial design direction is clear.
   - The goal should describe the concrete feature outcome, not every internal step.

4. Multi-agent split
   - Use subagents only for independent work areas.
   - Give each subagent a clear file/module ownership boundary.
   - Do not let multiple agents edit the same files unless there is a deliberate integration step.
   - Treat debugging as a focused role: use a debug subagent when a concrete failure appears, not as a broad always-on reviewer.

5. Implementation loop
   - Implement a small slice.
   - Run the practical verification available locally.
   - Fix failures.
   - Update the log only when the result changes the plan, proves something, or reveals a risk.
   - Commit meaningful, verified checkpoints so the work can be resumed or rolled forward safely.

6. Integration and QA
   - The main agent integrates the work.
   - Run broader checks.
   - Record known limitations and next QA items.
   - Push checkpoint commits when the branch/remote is known and the checkpoint is coherent.

7. User quality gate
   - Treat a loop as complete only after a coherent implementation slice has passed practical local checks.
   - At the end of each loop, request a real-device build/install checkpoint for user quality review.
   - Ask the user to inspect the feature on the iPhone and provide quality feedback before the next implementation loop.
   - Ask the user for their on-device observations, and optionally user-provided representative QA screenshots when visual quality is central to the decision.
   - Discuss the user's feedback and update the next loop direction before continuing.

8. Real-device build gate
   - Before Unity/RN real-device builds, stop and report the build question, primary path, target device/signing assumptions, expected risk, and out-of-scope items.
   - Continue only after user approval.

## User Device QA Loop

Each implementation loop should end with a user-facing quality checkpoint when the slice affects AR makeup behavior.

Loop-end sequence:

1. Finish a coherent implementation slice.
2. Run practical local checks first.
3. Summarize what changed, what was verified locally, and what still needs device inspection.
4. Ask for approval to build/install on the user's iPhone, including target device/signing assumptions, expected risk, and out-of-scope items.
5. After approval, build and install using the repo-approved Unity/RN build path.
6. Ask the user to test the feature on-device.
7. Ask the user to provide quality feedback and, only if they choose, representative screenshots.
8. Discuss the result with the user, decide the next adjustment, and record the decision in the development log.

The agent should not capture face screenshots directly. Face/camera visual QA is performed by the user on their iPhone. The agent may request observations or optional screenshots, but the user decides what to share and whether anything should be stored.

Recommended screenshot coverage for visual QA:

- Frontal neutral face.
- Left and right head turns.
- Raised brow or expression change, when relevant.
- Different eyebrow intensity/color presets.
- Any visible defect such as offset, flicker, harsh edge, asymmetry, or unnatural blending.
- Partial occlusion, such as a hand, hair, glasses, or shadow covering part of the brow/face.
- Motion stress, such as quick head turns, leaning closer/farther, or rapid expression changes.
- Different lighting conditions, such as bright light, dim light, side light, and mixed indoor light.

Screenshots should be treated as user-provided QA evidence, not agent-captured evidence. Store them under `evidence/screenshots/` only when the user provides the file and explicitly approves storing it. If screenshots are sensitive, summarize the user's observations in the development log instead of storing the image.

The agent should actively propose user QA checks instead of waiting for generic feedback. Suggested checks should be tailored to the current implementation risk and may include:

- Does eyebrow placement remain stable during quick movement?
- Does the effect drift when the user turns left/right or tilts up/down?
- Does the makeup disappear, stretch, or flicker when part of the face is occluded?
- Does the eyebrow color/blending still look natural under different lighting?
- Does strength/color preset switching create jumps, lag, or stale values?
- Does tracking recover gracefully after temporary face loss?
- Are left/right eyebrows aligned naturally, including asymmetry controls?
- Is the result acceptable on the actual iPhone screen, not only in logs or editor previews?

For each loop, the agent should ask for only the QA evidence needed for the current risk, not an exhaustive checklist every time.

## Conversation and Approval Records

Important user conversations should be captured as concise records in the relevant product, architecture, roadmap, or runbook document.

Record:

- User approvals, rejections, or requested changes.
- Build/install approval checkpoints.
- Scope decisions and out-of-scope confirmations.
- Quality feedback from device testing.
- Screenshot requests, user-supplied screenshot filenames, and screenshot observations.
- Decisions made after discussing screenshots or on-device behavior.
- Next-loop direction agreed with the user.

Do not store a full chat transcript unless explicitly requested. Prefer a dated decision log entry with:

- Date.
- Context or question.
- User decision or feedback.
- Evidence link or screenshot path, if approved for storage.
- Resulting action or next loop direction.

If screenshots or camera-derived artifacts include sensitive face data, do not capture or store them directly. Ask the user whether they want to provide and store the image. When storage is not appropriate, record only a textual observation summary from the user's feedback.

## Git Checkpoints

Use git as a progress safety net during longer product work.

Commit after meaningful checkpoints, such as:

- Research/design document created or updated.
- A coherent implementation slice is complete.
- A compile/test failure has been fixed and re-verified.
- QA/runbook updates match the current implementation state.

Before committing:

- Inspect the working tree.
- Stage only files related to the current checkpoint.
- Do not include unrelated user changes.
- Do not commit generated/cache state, raw evidence, Xcode derived data, Unity `Library/`, Unity `Logs/`, or `.DS_Store`.
- Record the relevant verification result in the commit summary or development log.

Push after checkpoint commits when:

- The current branch and remote are clear.
- The commit is coherent enough to share.
- The push will not publish unrelated changes or private/raw evidence.

If branch, remote, credentials, or publication target are unclear, stop and ask before pushing.

## Debug Subagent Pattern

Use a debug subagent when there is a concrete failure signal, such as:

- Unity compile/import failure.
- React Native bridge or event failure.
- iOS/Xcode build failure.
- Test failure.
- AR tracking instability.
- Makeup rendering artifacts, flicker, offset, or unexpected blending.

The debug subagent should produce:

- Failure summary.
- Reproduction condition.
- Relevant logs or command output.
- Likely root causes.
- Fix candidates.
- Files it proposes to change, if any.
- Verification results after the fix.

The main agent remains responsible for integration. Debug agents should not take broad ownership of product direction or edit files outside their assigned scope.

## What To Capture

Research notes:

- Existing files and systems that matter.
- Prior validation or research documents used.
- Relevant technical constraints.
- Unknowns that need implementation or device testing.

Development notes:

- Order of implementation.
- Major files changed and why.
- Key data flow between React Native and Unity.
- Rendering or AR tracking assumptions.
- Verification commands and results.
- Failed approaches and why they were rejected.
- Debug findings, reproduction steps, root cause, fix, and re-verification when failures occur.
- Checkpoint commit hashes and push status for meaningful milestones.
- User device QA feedback, screenshot references, and next-loop direction decisions.
- User approvals, conversation decisions, and screenshot observation summaries.

Learning notes:

- Concepts needed to understand the work.
- How Unity, AR Foundation, ARKit, React Native, and iOS pieces relate.
- Why a design is product-quality rather than only technically functional.

Risk notes:

- App Store/privacy gaps.
- License or commercial-use gaps.
- Free-but-restricted dependency, asset, LUT, template, model, or SDK concerns.
- Device-only uncertainties.
- Performance, thermal, tracking, or visual quality issues.

## Suggested Feature Document Set

For a feature such as eyebrow makeup, use:

- Product behavior: `docs/product/eyebrow-makeup-feature.md`
- Rendering/AR design: `docs/architecture/eyebrow-ar-rendering-design.md`
- Active progress log: `docs/roadmaps/active/eyebrow-makeup-development-log.md`
- QA/runbook if needed: `docs/runbooks/eyebrow-makeup-qa-runbook.md`

## Efficient Amount of Documentation

Before implementation:

- Write the feature goal, recommended approach, alternatives, risks, and validation plan.

During implementation:

- Update only when a meaningful decision, failure, validation result, or scope change happens.

After a slice completes:

- Record what now works, what was verified, what remains risky, and what the next step should be.

This keeps the loop fast while preserving enough context for future continuation.
