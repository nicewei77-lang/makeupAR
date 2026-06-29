# ARCore Canonical Face Texture v1

This folder records the team-shared canonical UV face texture source for E7 AR makeup region work.

## Source

```txt
Local source: /Users/wiseungcheol/Documents/ARCore_canonical_face_texture_1.psd
Format: Adobe Photoshop PSD
Size: 4096 x 4096
Bytes: 109374370
SHA-256: d7d3b87caa4929f561fc45a4b2313990542fedefeeadd6b5e8801d18bef1b8a7
```

## Team Use

Use this asset as the canonical UV reference for shared mask/region discussion:

```txt
- lip
- blush
- brow
- eyeliner
- future face-region UV alignment reviews
```

For implementation, prefer committed lightweight derivatives:

```txt
- flattened PNG reference
- region-specific mask PNGs
- contact sheets
- metrics JSON
```

Do not commit the 104MB PSD directly unless the team explicitly decides to use Git LFS or another binary asset policy.

## Boundary

This is a reference asset, not runtime evidence. It does not prove iPhone visual quality, AR attachment, motion stability, shader quality, or product readiness.
