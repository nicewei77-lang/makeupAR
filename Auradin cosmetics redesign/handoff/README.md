# Auradin screen redesign — handoff (v2: clickless flow)

Drop-in replacements for the React Native + Tamagui app.

| File here | Destination |
|---|---|
| `AuradinSearchScreen.tsx` | `apps/mobile/src/features/recommendation/screens/AuradinSearchScreen.tsx` |
| `auradin.mock.ts` | `apps/mobile/src/features/recommendation/mocks/auradin.mock.ts` |

No changes to `types.ts`, `AppFooter.tsx`, or `FooterIcons.tsx`. No new libraries —
the gloss orb uses `react-native-svg` (already a dependency) + the `Animated` API.

## The flow (one screen, four phases)
1. **home** — a large `AURADIN` wordmark (Korean 아우라딘 removed), one prompt
   composer (camera + send only), and three suggestion chips that **auto-submit**
   on a single tap. Minimal, clickless.
2. **searching** — the prompt dissolves; a sensual swirling **gloss-color orb**
   takes over while the AI "reads the color". Breathing orb + glow, animated
   loader dots, the user's query echoed, and three thinking steps (the active one
   breathes).
3. **question** — exactly **one** follow-up, asked with two large tappable color
   **swatch tiles** (맑은 핑크 / 차분한 로즈) + a "둘 다 좋아요" skip. Tap = advance,
   no confirm button ("don't make me think").
4. **results** — candidates reveal, the header reflecting the chosen color
   (e.g. "차분한 로즈 · 2만원 이하"): one hero pick (image · brand · shade · price ·
   why-it-matches) and compact alternatives.

Restart by tapping the wordmark or "처음부터 다시".

## Implementation notes
- Phases are plain `useState` + `setTimeout` (timings `SEARCH_MS` / `PICK_MS`).
  Each phase view fades/​lifts in via the `useFadeIn` hook; breathing loops via
  `useBreathe`.
- **Searching visual (latest design): a cute, kitsch cosmetic-photo parade.**
  The web preview (`Auradin Search.dc.html`, source of truth) replaces the old
  gloss orb with background-less product cuts that **pop in and out one at a
  time** with a springy bounce + slight tilt, over twinkling ✦ sparkles, a
  rotating dashed ring, and soft pastel blobs. Copy is playful ("아우라딘이 콕콕
  찾는 중"). Only this phase is kitsch — home / question / results stay calm.
  To port to RN: cross-fade the three product `Image`s with an `Animated`
  spring (scale 0.3→1.15→1 + small rotate), staggered ~1.4s apart, each masked
  to a soft circle (use `MaskedView` or a radial PNG), plus a few twinkling
  sparkle `Text` glyphs and a slow-rotating dashed `View` ring. The
  `react-native-svg` `GlossOrb` in this file is the older look — swap it out of
  `SearchingView` for the parade once you wire it.
- Wordmark resize between phases is an instant size swap (RN doesn't auto-animate
  layout). Animate a `scale` transform if you want it to morph.
- `question` and `candidates` copy is read from `auradin.mock.ts` via
  `getAuradinDraftData()`; only the flow chrome copy (loader labels, eyebrows) is
  in the screen.
- Run `npm run typecheck` after copying — the file is written to match the
  existing tokens/types but has not been compiled in this environment.

## Reference
`Auradin Search.dc.html` (project root) is the fully interactive design of this
flow — press send / a chip to watch the search animation, answer the question,
and see results. Use it as the source of truth for motion and layout.
