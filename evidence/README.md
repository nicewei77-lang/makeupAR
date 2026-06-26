# Evidence Curation Policy

This folder keeps a small, shareable visual history of the AR makeup validation path.

## What This Evidence Shows

- `evolution/01-face-mesh-first-proof/`: the first useful ARFace mesh/coordinate proof for the reference-driven path.
- `evolution/02-early-debug-mask/`: early broad debug masks that explain why region precision work was needed.
- `evolution/03-region-precision-yellow/`: E7 region precision Yellow evidence before the smoother path.
- `evolution/04-ref-uv-runtime-sweep/`: P8 reference-UV runtime comparison evidence.
- `evolution/05-smooth-mask-accepted/`: the currently accepted smooth-mask validation screenshots.
- `screenshots/`: canonical screenshots referenced by result docs.
- `screenshots/e7-lip-generate-web-beta-2026-06-27/`: React web beta browser proof for local-only lip mask generation, Vision/MediaPipe comparison, Blendshape Assist Off/On comparison, UV projection preview, and round-trip preview. This is buildless `partial` evidence, not RN/Unity runtime proof.
- `references/`: visual algorithm references, not runtime Green evidence.
- `e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/`: selected synchronized clean frame, ARFace export, and projected mesh overlay used as the best current gold-mask drawing input.

## Retention Rules

- Keep only representative visual samples for each stage.
- Prefer contact sheets over raw frame batches.
- Keep synchronized mesh evidence only when it includes the clean frame, ARFace export, projected mesh overlay, and capture summary from the same runtime moment.
- Do not keep `recovered/`, raw recordings, Xcode derived data, dependency installs, or editor caches in shareable evidence.
- Do not use these screenshots to claim product-quality makeup rendering. Current smooth-mask evidence is accepted for validation cleanup only; E7.3 remains Yellow.

## Local Staging

Raw recovered files and duplicate capture pairs from the recovery pass were moved out of the repo to:

`/private/tmp/makeupar-evidence-recovered-staging-20260623`
