# Eyebrow Makeup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a selectable eyebrow makeup region to the existing React Native + Unity AR makeup app, using the current smooth-region-mask renderer while preserving a future region-specific renderer route.

**Architecture:** React Native keeps a stable region recipe contract and adds `brow` as the fourth region. Unity accepts `brow` through `RNBridge`, routes it to `E3RegionMaskOverlay`, and renders an in-house procedural brow UV mask from `Assets/Resources/SmoothRegionMasks/`. Future dedicated renderers can replace the implementation behind the same `region="brow"` recipe contract.

**Tech Stack:** React Native 0.86, Jest, TypeScript, Unity 6000.x, AR Foundation 6.3.5, ARKit 6.3.5, Unity C#, Unity Resources textures, Python 3 for local asset/static verifiers.

---

## File Structure

Create:

- `docs/roadmaps/active/eyebrow-makeup-implementation-plan.md` - this plan.
- `docs/runbooks/eyebrow-makeup-qa-runbook.md` - loop-end iPhone QA checklist.
- `scripts/e7_reference_atlas/generate_brow_mask_texture.py` - procedural in-house brow mask generator.
- `scripts/e7_reference_atlas/verify_brow_mask_texture.py` - local brow mask asset verifier.
- `scripts/e7_reference_atlas/verify_brow_unity_contract.py` - static Unity/RN brow contract guard.
- `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png` - generated brow UV mask.

Modify:

- `rn/MakeupARValidation/App.tsx` - add `brow` region, brow presets, brow defaults, brow mask option, and UI/payload support.
- `rn/MakeupARValidation/__tests__/App.test.tsx` - add failing tests for the fourth brow layer and HUD controls.
- `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs` - accept and report the brow layer.
- `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs` - accept the brow mask/presets and tune brow material defaults.
- `docs/product/eyebrow-makeup-feature.md` - update after implementation with actual presets and local verification result.
- `docs/architecture/eyebrow-ar-rendering-design.md` - update after implementation with actual route table and mask id.
- `docs/roadmaps/active/eyebrow-makeup-development-log.md` - record implementation, verification, failures, commit hashes, and build gate state.

Do not modify:

- `TECH_VALIDATION_RESULT.md` unless the user explicitly asks for validation-history updates.
- Real-device signing/team/device defaults.
- Android, backend, AI/model, upload, payment, advertising, or commercial SDK code.

## Task 1: React Native Brow Recipe Contract

**Files:**
- Modify: `rn/MakeupARValidation/__tests__/App.test.tsx`
- Modify: `rn/MakeupARValidation/App.tsx`

- [ ] **Step 1: Write the failing Jest test for brow recipe payloads**

Add this import to the existing import list in `rn/MakeupARValidation/__tests__/App.test.tsx`:

```typescript
  BROW_TEXTURE_STYLE_OPTIONS,
```

Add this test after the existing recipe payload tests:

```typescript
test('posts eyebrow as a fourth independent region layer', () => {
  const browSample = BROW_TEXTURE_STYLE_OPTIONS.find(
    textureSample => textureSample.name === 'natural_brow',
  );

  expect(browSample).toBeTruthy();

  const payload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      brow: {
        color: RECIPE_COLOR_OPTIONS[2],
        opacity: 0.62,
        intensity: 0.58,
        textureSample: browSample!,
      },
    },
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24680,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        feather: 0.42,
        coverage: 0.7,
        roughness: 0.96,
        specular: 0.02,
        glossBoost: 0,
        gradientAmount: 0,
        maskTextureId: 'brow-drawn-mask-v1',
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

  expect(payload.region).toBe('brow');
  expect(payload.layerCount).toBe(4);
  expect(payload.enabledLayerCount).toBe(2);
  expect(payload.activeRegions).toBe('lip,brow');
  expect(browLayer).toBeTruthy();
  expect(browLayer.enabled).toBe(true);
  expect(browLayer.texture).toBe('natural_brow');
  expect(browLayer.sample).toBe('natural_brow');
  expect(browLayer.maskTextureId).toBe('brow-drawn-mask-v1');
  expect(browLayer.opacity).toBe(0.62);
  expect(browLayer.intensity).toBe(0.58);
  expect(browLayer.feather).toBe(0.42);
  expect(browLayer.coverage).toBe(0.7);
  expect(browLayer.specular).toBe(0.02);
  expect(browLayer.materialId).toBe('natural_brow-validation-material');
  expect(browLayer.shaderMode).toBe('unlit-alpha-validation');
});
```

- [ ] **Step 2: Write the failing Jest test for brow controls in HUD mode**

Add this test near the existing HUD control tests:

```typescript
test('shows eyebrow region and brow texture controls in HUD mode', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'brow');
  const text = collectText(renderer!);

  expect(text).toContain('focus brow');
  expect(text).toContain('natural_brow');
  expect(text).toContain('soft_brow');
  expect(text).toContain('brow-drawn-mask-v1');
});
```

- [ ] **Step 3: Run the focused RN tests and confirm RED**

Run:

```bash
cd rn/MakeupARValidation
npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand
```

Expected: FAIL because `BROW_TEXTURE_STYLE_OPTIONS`, `DEFAULT_REGION_RECIPES.brow`, `DEFAULT_REGION_TUNING.brow`, and `brow` UI controls do not exist yet.

- [ ] **Step 4: Implement minimal RN brow schema support**

In `rn/MakeupARValidation/App.tsx`, change the region list and mask id union:

```typescript
const RECIPE_REGION_OPTIONS = ['lip', 'cheek', 'eye', 'brow'] as const;
```

Add brow mask id to `MaskTextureId`:

```typescript
  | 'eye-smooth-mask-v1'
  | 'brow-drawn-mask-v1'
  | 'brow-smooth-mask-v1';
```

Add brow presets to `RECIPE_TEXTURE_SAMPLE_OPTIONS`:

```typescript
  {
    name: 'natural_brow',
    label: 'natural brow',
    region: 'brow',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#8A5A44',
    intensity: 0.58,
    feather: 0.42,
    coverage: 0.7,
    finish: 'powder-brow',
    roughness: 0.96,
    specular: 0.02,
    specularPower: 8,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'soft_brow',
    label: 'soft brow',
    region: 'brow',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#A7795D',
    intensity: 0.42,
    feather: 0.5,
    coverage: 0.58,
    finish: 'soft-powder-brow',
    roughness: 1,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
```

Add the exported brow texture options below `LIP_TEXTURE_STYLE_OPTIONS`:

```typescript
export const BROW_TEXTURE_STYLE_OPTIONS: RecipeTextureSample[] =
  RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureSample => textureSample.region === 'brow',
  );
```

Extend `DEFAULT_TEXTURE_SAMPLE_BY_REGION`:

```typescript
  brow: RECIPE_TEXTURE_SAMPLE_OPTIONS.find(
    textureSample => textureSample.name === 'natural_brow',
  ) as RecipeTextureSample,
```

Extend `DEFAULT_MASK_TEXTURE_ID_BY_REGION`:

```typescript
  brow: 'brow-drawn-mask-v1',
```

Extend `DEFAULT_REGION_RECIPES`:

```typescript
  brow: {
    color: RECIPE_COLOR_OPTIONS[2],
    opacity: 0.62,
    intensity: DEFAULT_TEXTURE_SAMPLE_BY_REGION.brow.intensity,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.brow,
  },
```

Extend `MASK_TEXTURE_OPTIONS_BY_REGION`:

```typescript
  brow: [{ id: 'brow-drawn-mask-v1', label: 'Drawn' }],
```

Extend `DEFAULT_ACTIVE_REGIONS`:

```typescript
  brow: false,
```

- [ ] **Step 5: Confirm RN control filtering automatically includes brow**

Verify that this existing code remains region-driven and needs no brow-specific branch:

```typescript
  const textureOptionsForFocusedRegion = RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureSample => textureSample.region === focusedRegion,
  );
```

If `formatTextureLabel` lacks brow labels, add cases:

```typescript
        case 'natural_brow':
          return 'Natural';
        case 'soft_brow':
          return 'Soft';
```

- [ ] **Step 6: Run the focused RN tests and confirm GREEN**

Run:

```bash
cd rn/MakeupARValidation
npm test -- --runTestsByPath __tests__/App.test.tsx --runInBand
```

Expected: PASS for all `App.test.tsx` tests.

- [ ] **Step 7: Commit RN contract slice**

Run:

```bash
git status --short
git add rn/MakeupARValidation/App.tsx rn/MakeupARValidation/__tests__/App.test.tsx
git commit -m "feat(rn): add eyebrow recipe controls"
```

Only stage the two RN files above.

## Task 2: In-House Brow Mask Asset

**Files:**
- Create: `scripts/e7_reference_atlas/verify_brow_mask_texture.py`
- Create: `scripts/e7_reference_atlas/generate_brow_mask_texture.py`
- Create: `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png`

- [ ] **Step 1: Write the brow mask verifier first**

Create `scripts/e7_reference_atlas/verify_brow_mask_texture.py`:

```python
#!/usr/bin/env python3
"""Verify the generated brow mask texture is present and product-safe."""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


DEFAULT_MASK = (
    "unity/MakeupARUnityValidation/Assets/Resources/"
    "SmoothRegionMasks/brow-drawn-mask-v1.png"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--mask", type=Path, default=Path(DEFAULT_MASK))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    mask_path = args.mask if args.mask.is_absolute() else args.repo_root / args.mask
    if not mask_path.exists():
        raise SystemExit(f"missing mask: {mask_path}")

    image = Image.open(mask_path).convert("RGBA")
    if image.size != (512, 512):
        raise SystemExit(f"expected 512x512 mask, got {image.size}")

    pixels = np.asarray(image)
    alpha = pixels[:, :, 3]
    active = alpha > 8
    active_count = int(active.sum())
    coverage = active_count / float(alpha.size)
    if active_count <= 0:
        raise SystemExit("brow mask has no active alpha pixels")
    if not (0.002 <= coverage <= 0.08):
        raise SystemExit(f"brow mask coverage out of range: {coverage:.6f}")

    rows, cols = np.nonzero(active)
    left = int(cols.min())
    right = int(cols.max())
    top = int(rows.min())
    bottom = int(rows.max())
    width = right - left + 1
    height = bottom - top + 1

    if width < 110 or width > 390:
        raise SystemExit(f"brow mask bbox width out of range: {width}")
    if height < 18 or height > 130:
        raise SystemExit(f"brow mask bbox height out of range: {height}")
    if top < 95 or bottom > 285:
        raise SystemExit(f"brow mask vertical position out of range: top={top} bottom={bottom}")

    print(
        "brow_mask_ok",
        f"path={mask_path}",
        "size=512x512",
        f"activePixels={active_count}",
        f"coverage={coverage:.6f}",
        f"bbox=left={left},top={top},right={right},bottom={bottom},width={width},height={height}",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the verifier and confirm RED**

Run:

```bash
python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py
```

Expected: FAIL with `missing mask: .../brow-drawn-mask-v1.png`.

- [ ] **Step 3: Add the procedural brow mask generator**

Create `scripts/e7_reference_atlas/generate_brow_mask_texture.py`:

```python
#!/usr/bin/env python3
"""Generate an in-house procedural ARFace-UV eyebrow mask."""

from __future__ import annotations

import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter


DEFAULT_OUTPUT = (
    "unity/MakeupARUnityValidation/Assets/Resources/"
    "SmoothRegionMasks/brow-drawn-mask-v1.png"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path(DEFAULT_OUTPUT))
    parser.add_argument("--resolution", type=int, default=512)
    return parser.parse_args()


def draw_brow(draw: ImageDraw.ImageDraw, center_x: int, center_y: int, mirror: int) -> None:
    points = [
        (center_x - mirror * 112, center_y + 24),
        (center_x - mirror * 78, center_y - 6),
        (center_x - mirror * 32, center_y - 22),
        (center_x + mirror * 30, center_y - 18),
        (center_x + mirror * 82, center_y + 2),
        (center_x + mirror * 118, center_y + 24),
        (center_x + mirror * 72, center_y + 36),
        (center_x + mirror * 8, center_y + 30),
        (center_x - mirror * 54, center_y + 38),
        (center_x - mirror * 104, center_y + 42),
    ]
    draw.polygon(points, fill=(92, 58, 42, 205))


def main() -> int:
    args = parse_args()
    output = args.output if args.output.is_absolute() else args.repo_root / args.output
    output.parent.mkdir(parents=True, exist_ok=True)

    size = int(args.resolution)
    image = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    mask = Image.new("L", (size, size), 0)
    mask_draw = ImageDraw.Draw(mask)
    draw_brow(mask_draw, 188, 181, 1)
    draw_brow(mask_draw, 324, 181, -1)
    mask = mask.filter(ImageFilter.GaussianBlur(radius=5.2))

    alpha = mask.point(lambda value: min(210, int(value * 0.9)))
    color = Image.new("RGBA", (size, size), (92, 58, 42, 0))
    color.putalpha(alpha)
    image.alpha_composite(color)
    image.save(output)
    print(f"generated brow mask: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Generate the brow mask asset**

Run:

```bash
python3 scripts/e7_reference_atlas/generate_brow_mask_texture.py
```

Expected: creates `unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png`.

- [ ] **Step 5: Run the verifier and confirm GREEN**

Run:

```bash
python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py
```

Expected: PASS with `brow_mask_ok` and active coverage between `0.002` and `0.08`.

- [ ] **Step 6: Commit mask slice**

Run:

```bash
git status --short
git add scripts/e7_reference_atlas/generate_brow_mask_texture.py scripts/e7_reference_atlas/verify_brow_mask_texture.py unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png
git commit -m "feat(unity): add procedural eyebrow mask asset"
```

Only stage the two scripts and generated brow mask PNG.

## Task 3: Unity Brow Parser and Renderer Contract

**Files:**
- Create: `scripts/e7_reference_atlas/verify_brow_unity_contract.py`
- Modify: `unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs`
- Modify: `unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs`

- [ ] **Step 1: Write the static Unity/RN brow contract verifier**

Create `scripts/e7_reference_atlas/verify_brow_unity_contract.py`:

```python
#!/usr/bin/env python3
"""Verify source files expose the brow region contract."""

from __future__ import annotations

from pathlib import Path


ROOT = Path.cwd()
RN_APP = ROOT / "rn/MakeupARValidation/App.tsx"
RN_BRIDGE = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs"
REGION_OVERLAY = ROOT / "unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs"
MASK = ROOT / "unity/MakeupARUnityValidation/Assets/Resources/SmoothRegionMasks/brow-drawn-mask-v1.png"


REQUIRED = {
    RN_APP: [
        "['lip', 'cheek', 'eye', 'brow']",
        "natural_brow",
        "soft_brow",
        "brow-drawn-mask-v1",
        "BROW_TEXTURE_STYLE_OPTIONS",
    ],
    RN_BRIDGE: [
        '"lip", "cheek", "eye", "brow"',
        'value == "brow"',
        'region == "brow" && (value == "natural_brow" || value == "soft_brow")',
        'region == "brow" && value == "brow-drawn-mask-v1"',
        'return "brow-drawn-mask-v1";',
    ],
    REGION_OVERLAY: [
        'region == "brow"',
        'textureSample == "natural_brow"',
        'textureSample == "soft_brow"',
        'case "brow":',
        'return "brow-drawn-mask-v1";',
        'case "natural_brow":',
        'case "soft_brow":',
    ],
}


def main() -> int:
    if not MASK.exists():
        raise SystemExit(f"missing brow mask asset: {MASK}")

    failures: list[str] = []
    for path, needles in REQUIRED.items():
        text = path.read_text(encoding="utf-8")
        for needle in needles:
            if needle not in text:
                failures.append(f"{path}: missing {needle!r}")

    if failures:
        raise SystemExit("\n".join(failures))

    print("brow_unity_contract_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Run the verifier and confirm RED**

Run:

```bash
python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py
```

Expected: FAIL because Unity C# files do not yet accept `brow`.

- [ ] **Step 3: Extend `RNBridge.cs` brow parsing**

In `RNBridge.cs`, change:

```csharp
private static readonly string[] FeatureSnapshotRegions = { "lip", "cheek", "eye" };
```

to:

```csharp
private static readonly string[] FeatureSnapshotRegions = { "lip", "cheek", "eye", "brow" };
```

In `NormalizeRegion`, change:

```csharp
if (value == "lip" || value == "cheek" || value == "eye")
```

to:

```csharp
if (value == "lip" || value == "cheek" || value == "eye" || value == "brow")
```

In `NormalizeTextureSample`, add this accepted case:

```csharp
            || (region == "brow" && (value == "natural_brow" || value == "soft_brow"))
```

In `NormalizeMaskTextureId`, add this accepted case:

```csharp
            || (region == "brow" && value == "brow-drawn-mask-v1")
```

In `GetDefaultMaskTextureId`, add:

```csharp
            case "brow":
                return "brow-drawn-mask-v1";
```

- [ ] **Step 4: Extend `E3RegionMaskOverlay.cs` brow rendering**

In `NormalizeRegion`, change:

```csharp
if (region == "lip" || region == "cheek" || region == "eye")
```

to:

```csharp
if (region == "lip" || region == "cheek" || region == "eye" || region == "brow")
```

In `NormalizeTextureSample`, add:

```csharp
            || (region == "brow" && (textureSample == "natural_brow" || textureSample == "soft_brow"))
```

In `NormalizeMaskTextureId`, add:

```csharp
            || (region == "brow" && maskTextureId == "brow-drawn-mask-v1")
```

In `GetDefaultMaskTextureId`, add:

```csharp
            case "brow":
                return "brow-drawn-mask-v1";
```

In `BuildMaterialColor`, add brow material response:

```csharp
            case "natural_brow":
                sampleAlphaScale = Mathf.Lerp(0.42f, 0.64f, recipe.Intensity);
                brightnessScale = 0.82f;
                break;
            case "soft_brow":
                sampleAlphaScale = Mathf.Lerp(0.30f, 0.48f, recipe.Intensity);
                brightnessScale = 0.9f;
                break;
```

In `ResolveMask`, keep brow on the generic soft mask path by not adding it to lip atlas logic.

- [ ] **Step 5: Run static contract verifier and confirm GREEN**

Run:

```bash
python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py
```

Expected: PASS with `brow_unity_contract_ok`.

- [ ] **Step 6: Run Unity batchmode import/compile**

Use the installed Unity path from the repo's prior build logs or the current Unity Hub install. First check the available executable:

```bash
ls /Applications/Unity/Hub/Editor
```

Then run batchmode import/compile from the repo root with the matching Unity executable:

```bash
"/Applications/Unity/Hub/Editor/6000.3.18f1/Unity.app/Contents/MacOS/Unity" -batchmode -quit -projectPath "unity/MakeupARUnityValidation" -logFile "evidence/logs/eyebrow-unity-batchmode-20260627.log"
```

Expected: Unity exits successfully, and the log contains no `error CS` or `Shader error`.

- [ ] **Step 7: Commit Unity contract slice**

Run:

```bash
git status --short
git add scripts/e7_reference_atlas/verify_brow_unity_contract.py unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs evidence/logs/eyebrow-unity-batchmode-20260627.log
git commit -m "feat(unity): route eyebrow makeup through smooth mask"
```

Only stage the verifier, the two Unity source files, and the batchmode log if it is accepted as evidence.

## Task 4: Local Verification and QA Documentation

**Files:**
- Create: `docs/runbooks/eyebrow-makeup-qa-runbook.md`
- Modify: `docs/product/eyebrow-makeup-feature.md`
- Modify: `docs/architecture/eyebrow-ar-rendering-design.md`
- Modify: `docs/roadmaps/active/eyebrow-makeup-development-log.md`

- [ ] **Step 1: Add the eyebrow QA runbook**

Create `docs/runbooks/eyebrow-makeup-qa-runbook.md`:

```markdown
# Eyebrow Makeup QA Runbook

Status: Draft for first iPhone loop
Date: 2026-06-27

## Purpose

Use this checklist after local checks pass and before deciding whether the
eyebrow makeup slice is ready for another implementation loop.

## Agent Rules

- Do not capture face screenshots directly.
- Ask the user for observations from the real iPhone.
- Store user-provided screenshots only when the user explicitly approves.
- Do not run Unity/RN real-device builds before reporting the build question,
  primary path, target device/signing assumptions, expected risk, and
  out-of-scope items.

## First Loop Device Checks

Ask the user to inspect:

- Frontal neutral face: brow appears on eyebrow area, not forehead or eyelid.
- Left and right head turn: brow does not float or slide.
- Raised brow or expression change: brow remains attached without harsh stretch.
- Color/intensity change: updates are immediate and do not leave stale values.
- Temporary face loss: brow hides/fades and recovers without lingering residue.

## Feedback Questions

- Does eyebrow placement remain stable when turning left and right?
- Does either brow look too high, too low, too thick, or too stamped on?
- Does the selected color look like natural brow makeup on the iPhone screen?
- Do opacity and intensity controls change the result immediately?
- Is left/right balance acceptable for the first slice, or should asymmetry
  controls move into the next loop?
```

- [ ] **Step 2: Run all local RN checks**

Run:

```bash
cd rn/MakeupARValidation
npm test -- --runInBand
npx tsc --noEmit
npm run lint
```

Expected: all pass. Record any warnings in the development log if they are not already known.

- [ ] **Step 3: Run asset and static verifiers**

Run from repo root:

```bash
python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py
python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py
git diff --check
```

Expected: all pass.

- [ ] **Step 4: Update docs with implementation results**

In `docs/roadmaps/active/eyebrow-makeup-development-log.md`, append:

```markdown
## Implementation Loop 1 Local Verification

Date: 2026-06-27

Implemented:

- React Native `brow` recipe region and HUD controls.
- `natural_brow` and `soft_brow` presets.
- In-house `brow-drawn-mask-v1` procedural mask.
- Unity `RNBridge` and `E3RegionMaskOverlay` support for `brow`.

Local checks:

- Jest: PASS, `cd rn/MakeupARValidation && npm test -- --runInBand`
- TypeScript: PASS, `cd rn/MakeupARValidation && npx tsc --noEmit`
- RN lint: PASS, `cd rn/MakeupARValidation && npm run lint`
- Brow mask verifier: PASS, `python3 scripts/e7_reference_atlas/verify_brow_mask_texture.py`
- Brow Unity contract verifier: PASS, `python3 scripts/e7_reference_atlas/verify_brow_unity_contract.py`
- Unity batchmode import/compile: PASS, `evidence/logs/eyebrow-unity-batchmode-20260627.log`

Device QA status:

- Real-device build not yet run.
- Awaiting user approval for Unity/RN iPhone build/install.
```

If a command fails, replace the matching PASS line with `FAIL`, paste the
failure summary, fix the issue, rerun the same command, and add the re-run
result directly below the failed line.

- [ ] **Step 5: Commit verification/docs slice**

Run:

```bash
git status --short
git add docs/runbooks/eyebrow-makeup-qa-runbook.md docs/product/eyebrow-makeup-feature.md docs/architecture/eyebrow-ar-rendering-design.md docs/roadmaps/active/eyebrow-makeup-development-log.md
git commit -m "docs: record eyebrow makeup QA loop"
```

Only stage the docs listed above.

## Task 5: Loop-End Build Gate Report

**Files:**
- Modify: `docs/roadmaps/active/eyebrow-makeup-development-log.md`

- [ ] **Step 1: Prepare the build gate summary**

Append this section to `docs/roadmaps/active/eyebrow-makeup-development-log.md`:

```markdown
## Build Gate Packet

Date: 2026-06-27

Build question:

- May I regenerate/sync UnityFramework and run the React Native iPhone
  build/install so the user can inspect eyebrow makeup on device?

Primary path:

- `bash scripts/build_m3_unityframework.sh` from repo root.
- Then RN/Xcode device build with the user-approved target iPhone and signing
  team for this loop.

Target device/signing assumptions:

- Do not hard-code a UDID or development team in repo defaults.
- Use the currently connected/user-approved iPhone and signing team only after
  explicit approval.

Expected risk:

- UnityFramework build may be slow or blocked by Unity licensing/process state.
- Xcode signing may fail if the selected device/team/profile is unavailable.
- Brow visual fit may need another tuning loop after user iPhone review.

Out of scope:

- Android.
- Backend, upload, recommendation, AI/model inference, raw-frame storage.
- Payment, ads, brand partnership, product sales, commercial SDKs.
- App Store submission automation.
```

- [ ] **Step 2: Commit build gate packet**

Run:

```bash
git status --short
git add docs/roadmaps/active/eyebrow-makeup-development-log.md
git commit -m "docs: add eyebrow device build gate"
```

- [ ] **Step 3: Stop and request build approval**

Do not run `scripts/build_m3_unityframework.sh`, RN CLI, Xcode, or device install until the user approves the build gate.

Report:

- Changed files.
- Local verification results.
- Build question.
- Primary path.
- Target device/signing assumptions.
- Expected risk.
- Out-of-scope items.

## Self-Review Checklist

- Spec coverage: Tasks cover RN schema/UI, Unity parser/renderer, in-house mask asset, local verification, docs, and the real-device build approval gate.
- Placeholder scan: This plan contains no `TBD`, incomplete tasks, or missing command expectations.
- Type consistency: Region name is consistently `brow`; mask id is consistently `brow-drawn-mask-v1`; presets are consistently `natural_brow` and `soft_brow`.
- Scope control: No AI/model inference, backend upload, raw-frame storage, Android, commercial SDK, payment, ads, or App Store submission work is included.
