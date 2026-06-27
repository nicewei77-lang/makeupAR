# E7 Eyeliner Anchor-to-Band App Handoff

Status: `pending_user_visual_pick`

Generated candidates: `144`
Accepted by automatic gates: `137`
Rejected into review sheet: `7`

Primary tracker:

- MediaPipe upper eyelid landmarks.

Shape model:

- Anchor-to-band parametric eyeliner.
- Family taxonomy: Cat, Puppy, Sexy, Winged, Colored, Doll, Balanced reference, Tail-only safe.
- Best reference image was used only as shape taxonomy. It was not copied as a repo/runtime asset.

Implementation after user pick:

1. Promote the selected candidate from `selected_policy_pending_user.json` to `selected_policy.json`.
2. Use the selected candidate axes as the default app preset.
3. Keep top nearby candidates as style alternatives.
4. Keep Tail-only safe as fallback.
5. Keep lower-lid coverage off by default.

Do not claim product-quality-ready until iPhone runtime visual evidence exists.
