# Eyebrow Filter Spec

## Purpose
Build a natural eyebrow AR filter with minimal code and practical iteration.

## Hard Guardrail
- Do not modify or regress existing eye and cheek/blush behavior.

## Behavior
- Eyebrow is an optional makeup region.
- Eyebrow rendering should attach to the user's eyebrow area, not the eyelid or eye shadow area.
- Candidate buttons 1-5 should change brow texture/density/style enough to be visible.
- Color buttons should visibly change pigment: black, brown, dark brown, light brown, and wine.
- Eyebrow should be able to run together with the existing makeup layers.

## Rendering Approach
- Runtime placement is driven by eyebrow boundary/engine logic.
- Candidate PNGs are not placement anchors.
- Candidate PNGs provide strand and density texture only.
- Boundary outside cleanup, tone lift, tint fill, multiply-style color, smoothing, blur, and feathering are allowed.
- Store runtime eyebrow masks/textures in Unity Resources when Unity needs to load them.

## Practical Acceptance
- Expected renders are useful for design review only.
- Actual AR correctness must be judged from the Unity runtime behavior.
- Keep iterating until the eyebrow attaches to the brow area and looks like makeup instead of a sticker or eyelid patch.
