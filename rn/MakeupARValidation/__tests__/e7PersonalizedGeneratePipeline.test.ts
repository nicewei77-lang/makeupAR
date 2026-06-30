import type { LipAdjustment } from '../../../packages/lip-generate-core/src';
import type { E7NativeBoundaryResult } from '../src/e7PersonalizedGeneratePipeline';
import {
  buildGeneratedLipPackage,
  buildUvMaskRawRgba,
  smoothLipBoundaryCurveDensified,
} from '../src/e7PersonalizedGeneratePipeline';

const ZERO_ADJUSTMENT: LipAdjustment = {
  cornerReach: 0,
  upperLipTightness: 0,
  lowerLipTightness: 0,
  verticalOffset: 0,
  innerFill: 0,
  upperInnerFill: 0,
};

const VISIBLE_ADJUSTMENT: LipAdjustment = {
  cornerReach: 0.8,
  upperLipTightness: 0.65,
  lowerLipTightness: 0.7,
  verticalOffset: 0.35,
  innerFill: 0.25,
  upperInnerFill: 0.4,
};

function makeNativeBoundaryResult(): E7NativeBoundaryResult {
  return {
    status: 'ready',
    provider: 'vision',
    captureSetId: 'e7-capture-set-boundary-test',
    capturePairId: 'pair_face_boundary_test_0001',
    captureShotKind: 'neutral',
    framePath: 'Documents/e7-reference-atlas/capture_pairs/pair/frame.png',
    framePreviewUri: 'file:///tmp/e7-frame-preview.png',
    arFaceExportPath:
      'Documents/e7-reference-atlas/capture_pairs/pair/arface_export.json',
    frameWidth: 240,
    frameHeight: 240,
    boundary: {
      coordinateSpace: 'frame_image_pixel_top_left',
      source: 'vision',
      generationMethod: 'vision_current_frame_test',
      outerPoints: [
        { x: 66, y: 126 },
        { x: 86, y: 105 },
        { x: 120, y: 96 },
        { x: 154, y: 105 },
        { x: 174, y: 126 },
        { x: 154, y: 149 },
        { x: 120, y: 158 },
        { x: 86, y: 149 },
      ],
      innerPoints: [
        { x: 92, y: 127 },
        { x: 108, y: 119 },
        { x: 132, y: 119 },
        { x: 148, y: 127 },
        { x: 132, y: 135 },
        { x: 108, y: 135 },
      ],
    },
    arFaceExport: {
      capturePairId: 'pair_face_boundary_test_0001',
      screenVertices: [
        [0, 0, 1],
        [240, 0, 1],
        [0, 240, 1],
        [240, 240, 1],
      ],
      uvs: [
        [0, 1],
        [1, 1],
        [0, 0],
        [1, 0],
      ],
      indices: [0, 1, 2, 1, 3, 2],
      display: {
        videoFrameSize: [240, 240],
        orientation: 'portrait',
        isMirrored: true,
      },
    },
    blendShapes: {
      available: true,
      keySignals: {
        mouthSmileLeft: 0.12,
        mouthPucker: 0.03,
      },
    },
    warnings: ['test_current_frame_native_provider'],
  };
}

function makeThinInnerMouthNativeBoundaryResult(): E7NativeBoundaryResult {
  const result = makeNativeBoundaryResult();
  return {
    ...result,
    boundary: {
      ...result.boundary!,
      innerPoints: [
        { x: 92, y: 127 },
        { x: 108, y: 126.4 },
        { x: 132, y: 126.4 },
        { x: 148, y: 127 },
        { x: 132, y: 128 },
        { x: 108, y: 128 },
      ],
      generationMethod: 'vision_current_frame_thin_inner_mouth_test',
    },
  };
}

function makeAsymmetricMediaPipeMouthNativeBoundaryResult(): E7NativeBoundaryResult {
  return {
    status: 'ready',
    provider: 'mediapipe',
    captureSetId: 'e7-capture-set-asymmetric-mediapipe-test',
    capturePairId: 'pair_face_asymmetric_mediapipe_test_0001',
    captureShotKind: 'neutral',
    framePath: 'Documents/e7-reference-atlas/capture_pairs/pair/frame.png',
    framePreviewUri: 'file:///tmp/e7-frame-preview.png',
    arFaceExportPath:
      'Documents/e7-reference-atlas/capture_pairs/pair/arface_export.json',
    frameWidth: 1179,
    frameHeight: 2556,
    boundary: {
      coordinateSpace: 'frame_image_pixel_top_left',
      source: 'mediapipe',
      generationMethod: 'native_mediapipe_asymmetric_inner_mouth_test',
      outerPoints: [
        { x: 441.64, y: 1357.3 },
        { x: 453.69, y: 1374.3 },
        { x: 470.27, y: 1391.85 },
        { x: 497.93, y: 1413.36 },
        { x: 535.41, y: 1427.43 },
        { x: 578.41, y: 1430.55 },
        { x: 621.98, y: 1424.52 },
        { x: 659.07, y: 1407.5 },
        { x: 686.87, y: 1383.9 },
        { x: 703.63, y: 1363.35 },
        { x: 713.92, y: 1345.48 },
        { x: 702.15, y: 1334.51 },
        { x: 685.04, y: 1322.48 },
        { x: 658.68, y: 1308.88 },
        { x: 617.7, y: 1296.03 },
        { x: 576.66, y: 1307.24 },
        { x: 533.78, y: 1299.95 },
        { x: 493.09, y: 1316.22 },
        { x: 468.86, y: 1331.82 },
        { x: 452.68, y: 1344.97 },
      ],
      innerPoints: [
        { x: 454.55, y: 1357 },
        { x: 475.71, y: 1357.42 },
        { x: 492.73, y: 1357.65 },
        { x: 515.97, y: 1358.43 },
        { x: 544.3, y: 1359.11 },
        { x: 577.64, y: 1360.56 },
        { x: 610.71, y: 1357.7 },
        { x: 639.93, y: 1353.27 },
        { x: 662.9, y: 1350.54 },
        { x: 680.81, y: 1348.54 },
        { x: 701.94, y: 1346.6 },
        { x: 679.11, y: 1348.14 },
        { x: 661.79, y: 1349.62 },
        { x: 638.82, y: 1351.93 },
        { x: 610.84, y: 1355.49 },
        { x: 578.44, y: 1358.73 },
        { x: 545.68, y: 1357.65 },
        { x: 517.15, y: 1356.48 },
        { x: 493.64, y: 1357.14 },
        { x: 475.97, y: 1356.77 },
      ],
    },
    arFaceExport: {
      capturePairId: 'pair_face_asymmetric_mediapipe_test_0001',
      screenVertices: [
        [0, 0, 1],
        [1179, 0, 1],
        [0, 2556, 1],
        [1179, 2556, 1],
      ],
      uvs: [
        [0, 1],
        [1, 1],
        [0, 0],
        [1, 0],
      ],
      indices: [0, 1, 2, 1, 3, 2],
      display: {
        videoFrameSize: [1179, 2556],
        orientation: 'portrait',
        isMirrored: true,
      },
    },
    blendShapes: {
      available: true,
      keySignals: {
        mouthSmileLeft: 0.04,
        mouthPucker: 0.02,
      },
    },
    warnings: ['test_asymmetric_mediapipe_inner_mouth'],
  };
}

function makeCaptureSetShot(
  shotKind: E7NativeBoundaryResult['captureShotKind'],
  delta: { x?: number; y?: number; scaleX?: number; scaleY?: number } = {},
): E7NativeBoundaryResult {
  const result = makeNativeBoundaryResult();
  const scaleX = delta.scaleX ?? 1;
  const scaleY = delta.scaleY ?? 1;
  const center = { x: 120, y: 127 };
  const transformPoint = (point: { x: number; y: number }) => ({
    x: center.x + (point.x - center.x) * scaleX + (delta.x ?? 0),
    y: center.y + (point.y - center.y) * scaleY + (delta.y ?? 0),
  });

  return {
    ...result,
    capturePairId: `pair_face_boundary_test_${shotKind}`,
    captureShotKind: shotKind,
    framePath: `Documents/e7-reference-atlas/capture_pairs/${shotKind}/frame.png`,
    arFaceExportPath: `Documents/e7-reference-atlas/capture_pairs/${shotKind}/arface_export.json`,
    boundary: {
      ...result.boundary!,
      outerPoints: result.boundary!.outerPoints.map(transformPoint),
      innerPoints: result.boundary!.innerPoints.map(transformPoint),
      generationMethod: `vision_${shotKind}_test`,
    },
    blendShapes: {
      available: true,
      keySignals: {
        mouthSmileLeft: shotKind === 'smile' ? 0.62 : 0.12,
        mouthPucker: shotKind === 'pucker' ? 0.58 : 0.03,
      },
    },
  };
}

function outerBoundaryDelta(
  previous: NonNullable<E7NativeBoundaryResult['boundary']>['outerPoints'],
  next: NonNullable<E7NativeBoundaryResult['boundary']>['outerPoints'],
) {
  const count = Math.min(previous.length, next.length);
  let total = 0;
  for (let index = 0; index < count; index++) {
    total +=
      Math.abs(previous[index].x - next[index].x) +
      Math.abs(previous[index].y - next[index].y);
  }
  return total;
}

function maxY(
  points: NonNullable<E7NativeBoundaryResult['boundary']>['outerPoints'],
) {
  return Math.max(...points.map(point => point.y));
}

function minY(
  points: NonNullable<E7NativeBoundaryResult['boundary']>['outerPoints'],
) {
  return Math.min(...points.map(point => point.y));
}

function minX(
  points: NonNullable<E7NativeBoundaryResult['boundary']>['outerPoints'],
) {
  return Math.min(...points.map(point => point.x));
}

function maxX(
  points: NonNullable<E7NativeBoundaryResult['boundary']>['outerPoints'],
) {
  return Math.max(...points.map(point => point.x));
}

function polygonSelfIntersectionCount(points: { x: number; y: number }[]) {
  const cross = (
    a: { x: number; y: number },
    b: { x: number; y: number },
    c: { x: number; y: number },
  ) => (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
  const intersects = (
    a: { x: number; y: number },
    b: { x: number; y: number },
    c: { x: number; y: number },
    d: { x: number; y: number },
  ) => {
    const abC = cross(a, b, c);
    const abD = cross(a, b, d);
    const cdA = cross(c, d, a);
    const cdB = cross(c, d, b);
    return (
      ((abC > 1e-6 && abD < -1e-6) || (abC < -1e-6 && abD > 1e-6)) &&
      ((cdA > 1e-6 && cdB < -1e-6) || (cdA < -1e-6 && cdB > 1e-6))
    );
  };
  let count = 0;
  for (let index = 0; index < points.length; index++) {
    const start = points[index];
    const end = points[(index + 1) % points.length];
    for (let otherIndex = index + 1; otherIndex < points.length; otherIndex++) {
      if (
        Math.abs(index - otherIndex) <= 1 ||
        (index === 0 && otherIndex === points.length - 1)
      ) {
        continue;
      }
      if (
        intersects(
          start,
          end,
          points[otherIndex],
          points[(otherIndex + 1) % points.length],
        )
      ) {
        count += 1;
      }
    }
  }
  return count;
}

function tinyAlphaHoleCount(
  maskRawRgbaBase64: string,
  width: number,
  height: number,
) {
  const raw = decodeBase64(maskRawRgbaBase64);
  const alpha = new Uint8Array(width * height);
  let alphaMinX = width;
  let alphaMinY = height;
  let alphaMaxX = -1;
  let alphaMaxY = -1;

  for (let index = 0; index < width * height; index++) {
    const value = raw[index * 4 + 3] ?? 0;
    alpha[index] = value;
    if (value > 127) {
      const x = index % width;
      const y = Math.floor(index / width);
      alphaMinX = Math.min(alphaMinX, x);
      alphaMinY = Math.min(alphaMinY, y);
      alphaMaxX = Math.max(alphaMaxX, x);
      alphaMaxY = Math.max(alphaMaxY, y);
    }
  }

  if (alphaMaxX < alphaMinX || alphaMaxY < alphaMinY) {
    return 0;
  }

  const seen = new Uint8Array(width * height);
  let tinyHoles = 0;
  for (let y = alphaMinY; y <= alphaMaxY; y++) {
    for (let x = alphaMinX; x <= alphaMaxX; x++) {
      const startIndex = y * width + x;
      if (seen[startIndex] || alpha[startIndex] > 127) {
        continue;
      }

      const queue: Array<[number, number]> = [[x, y]];
      seen[startIndex] = 1;
      let cursor = 0;
      let area = 0;
      let touchesBounds = false;
      let componentMinX = x;
      let componentMaxX = x;
      let componentMinY = y;
      let componentMaxY = y;

      while (cursor < queue.length) {
        const [currentX, currentY] = queue[cursor++];
        area += 1;
        componentMinX = Math.min(componentMinX, currentX);
        componentMaxX = Math.max(componentMaxX, currentX);
        componentMinY = Math.min(componentMinY, currentY);
        componentMaxY = Math.max(componentMaxY, currentY);
        if (
          currentX === alphaMinX ||
          currentX === alphaMaxX ||
          currentY === alphaMinY ||
          currentY === alphaMaxY
        ) {
          touchesBounds = true;
        }

        for (const [nextX, nextY] of [
          [currentX + 1, currentY],
          [currentX - 1, currentY],
          [currentX, currentY + 1],
          [currentX, currentY - 1],
        ] as Array<[number, number]>) {
          if (
            nextX < alphaMinX ||
            nextX > alphaMaxX ||
            nextY < alphaMinY ||
            nextY > alphaMaxY
          ) {
            continue;
          }
          const nextIndex = nextY * width + nextX;
          if (!seen[nextIndex] && alpha[nextIndex] <= 127) {
            seen[nextIndex] = 1;
            queue.push([nextX, nextY]);
          }
        }
      }

      const componentWidth = componentMaxX - componentMinX + 1;
      const componentHeight = componentMaxY - componentMinY + 1;
      if (
        !touchesBounds &&
        area <= 8 &&
        componentWidth <= 4 &&
        componentHeight <= 3
      ) {
        tinyHoles += 1;
      }
    }
  }

  return tinyHoles;
}

function decodeBase64(input: string) {
  const alphabet =
    'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
  let clean = input;
  while (clean.endsWith('=')) {
    clean = clean.slice(0, -1);
  }
  const bytes: number[] = [];
  let buffer = 0;
  let bits = 0;

  for (const char of clean) {
    const value = alphabet.indexOf(char);
    if (value < 0) {
      continue;
    }
    buffer = buffer * 64 + value;
    bits += 6;
    if (bits >= 8) {
      bits -= 8;
      bytes.push(Math.floor(buffer / 2 ** bits) % 256);
      buffer %= 2 ** bits;
    }
  }

  return Uint8Array.from(bytes);
}

test('curve_densified_v1 increases package lip boundary point count', () => {
  const nativeResult = makeNativeBoundaryResult();
  const originalPointCount =
    nativeResult.boundary!.outerPoints.length +
    nativeResult.boundary!.innerPoints.length;

  const smoothed = smoothLipBoundaryCurveDensified(nativeResult.boundary!, {
    width: nativeResult.frameWidth,
    height: nativeResult.frameHeight,
  });
  expect(smoothed.boundarySmoothing).toBe('curve_densified_v1');
  expect(smoothed.originalPointCount).toBe(originalPointCount);
  expect(smoothed.smoothedPointCount).toBeGreaterThan(originalPointCount);

  const candidate = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  });
  expect(candidate.package).toBeDefined();
  const boundary = candidate.package!.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  expect(boundary.boundarySmoothing).toBe('curve_densified_v1');
  expect(boundary.originalPointCount).toBe(originalPointCount);
  expect(boundary.smoothedPointCount).toBeGreaterThan(originalPointCount);
  expect(boundary.smoothingDiagnostics).toMatchObject({
    originalOuterPointCount: nativeResult.boundary!.outerPoints.length,
    originalInnerPointCount: nativeResult.boundary!.innerPoints.length,
    smoothedOuterPointCount: boundary.outerPoints.length,
    smoothedInnerPointCount: boundary.innerPoints.length,
  });
});

test('visible lip adjustment changes smoothed boundary and UV alpha diagnostics', () => {
  const nativeResult = makeNativeBoundaryResult();

  const basePackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const adjustedPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: VISIBLE_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;

  const baseBoundary = basePackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const adjustedBoundary = adjustedPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  expect(
    outerBoundaryDelta(baseBoundary.outerPoints, adjustedBoundary.outerPoints),
  ).toBeGreaterThan(24);

  const baseUv = basePackage.uvCoverageMetadata as Record<string, unknown>;
  const adjustedUv = adjustedPackage.uvCoverageMetadata as Record<
    string,
    unknown
  >;
  expect(baseUv.boundarySmoothing).toBe('curve_densified_v1');
  expect(adjustedUv.boundarySmoothing).toBe('curve_densified_v1');
  expect(adjustedUv.alphaChecksum).not.toBe(baseUv.alphaChecksum);
  expect(adjustedUv.alphaSum).not.toBe(baseUv.alphaSum);
  expect(adjustedPackage.runtimeApplyPayload.maskRawRgbaBase64).not.toBe(
    basePackage.runtimeApplyPayload.maskRawRgbaBase64,
  );
  expect(adjustedPackage.generatedMaskId).not.toBe(basePackage.generatedMaskId);
});

test('lower lip adjustment plus expands downward in top-left frame coordinates', () => {
  const nativeResult = makeNativeBoundaryResult();
  const basePackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const lowerPlusPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      lowerLipTightness: 0.35,
    },
    generatedAtMs: 1000,
  }).package!;
  const lowerMinusPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      lowerLipTightness: -0.35,
    },
    generatedAtMs: 1000,
  }).package!;

  const baseBoundary = basePackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const lowerPlusBoundary = lowerPlusPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const lowerMinusBoundary = lowerMinusPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;

  expect(maxY(lowerPlusBoundary.outerPoints)).toBeGreaterThan(
    maxY(baseBoundary.outerPoints),
  );
  expect(maxY(lowerMinusBoundary.outerPoints)).toBeLessThan(
    maxY(baseBoundary.outerPoints),
  );
});

test('zero-adjustment generated mask starts with an automatic lower spill guard', () => {
  const nativeResult = makeNativeBoundaryResult();
  const guardedPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const releasedPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      lowerLipTightness: 0.34,
    },
    generatedAtMs: 1000,
  }).package!;

  const guardedBoundary = guardedPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const releasedBoundary = releasedPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;

  expect(maxY(guardedBoundary.outerPoints)).toBeLessThan(
    maxY(releasedBoundary.outerPoints),
  );
  expect(guardedPackage.uvCoverageMetadata?.lowerLipGuardApplied).toBe(true);
  expect(guardedPackage.uvCoverageMetadata?.lowerLipGuardTightness).toBe(0.34);
  expect(guardedPackage.qualityWarnings).toContain(
    'lower_lip_spill_guard_tightness_0.34',
  );
  expect(guardedPackage.qualityWarnings).toContain(
    'upper_inner_fill_auto_bias_0.34',
  );
});

test('upper lip adjustment plus expands upward in top-left frame coordinates', () => {
  const nativeResult = makeNativeBoundaryResult();
  const basePackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const upperPlusPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      upperLipTightness: 0.35,
    },
    generatedAtMs: 1000,
  }).package!;
  const upperMinusPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      upperLipTightness: -0.35,
    },
    generatedAtMs: 1000,
  }).package!;

  const baseBoundary = basePackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const upperPlusBoundary = upperPlusPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const upperMinusBoundary = upperMinusPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;

  expect(minY(upperPlusBoundary.outerPoints)).toBeLessThan(
    minY(baseBoundary.outerPoints),
  );
  expect(minY(upperMinusBoundary.outerPoints)).toBeGreaterThan(
    minY(baseBoundary.outerPoints),
  );
});

test('upper inner fill plus shrinks the upper mouth hole without moving outer boundary', () => {
  const nativeResult = makeNativeBoundaryResult();
  const basePackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const upperInnerFillPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      upperInnerFill: 0.5,
    },
    generatedAtMs: 1000,
  }).package!;

  const baseBoundary = basePackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const upperInnerFillBoundary =
    upperInnerFillPackage.lipBoundary2D as NonNullable<
      E7NativeBoundaryResult['boundary']
    >;
  const baseUv = basePackage.uvCoverageMetadata as Record<string, number>;
  const upperInnerFillUv = upperInnerFillPackage.uvCoverageMetadata as Record<
    string,
    number
  >;

  expect(
    outerBoundaryDelta(
      baseBoundary.outerPoints,
      upperInnerFillBoundary.outerPoints,
    ),
  ).toBeLessThan(0.01);
  expect(minY(upperInnerFillBoundary.innerPoints)).toBeGreaterThan(
    minY(baseBoundary.innerPoints),
  );
  expect(upperInnerFillUv.alphaSum).toBeGreaterThan(baseUv.alphaSum);
  expect(upperInnerFillUv.positiveTexels).toBeGreaterThan(
    baseUv.positiveTexels,
  );
  expect(upperInnerFillPackage.generatedMaskId).not.toBe(
    basePackage.generatedMaskId,
  );
});

test('default upper inner fill adds a visible seam guard for a nearly closed mouth', () => {
  const nativeResult = makeThinInnerMouthNativeBoundaryResult();
  const seamReleasedPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      upperInnerFill: -0.34,
    },
    generatedAtMs: 1000,
  }).package!;
  const seamGuardedPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;

  const seamReleasedBoundary = seamReleasedPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const seamGuardedBoundary = seamGuardedPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const seamReleasedUv = seamReleasedPackage.uvCoverageMetadata as Record<
    string,
    number
  >;
  const seamGuardedUv = seamGuardedPackage.uvCoverageMetadata as Record<
    string,
    number
  >;

  expect(
    outerBoundaryDelta(
      seamReleasedBoundary.outerPoints,
      seamGuardedBoundary.outerPoints,
    ),
  ).toBeLessThan(0.01);
  expect(minY(seamGuardedBoundary.innerPoints)).toBeGreaterThan(
    minY(seamReleasedBoundary.innerPoints) + 1,
  );
  expect(seamGuardedUv.alphaSum).toBeGreaterThan(seamReleasedUv.alphaSum);
  expect(seamGuardedUv.positiveTexels).toBeGreaterThan(
    seamReleasedUv.positiveTexels,
  );
  expect(seamGuardedPackage.qualityWarnings).toContain(
    'upper_inner_fill_auto_bias_0.34',
  );
});

test('semantic upper inner fill avoids MediaPipe right-side pinholes', () => {
  const nativeResult = makeAsymmetricMediaPipeMouthNativeBoundaryResult();
  const packages = [0, 0.15, 0.3, 0.45].map(
    upperInnerFill =>
      buildGeneratedLipPackage({
        nativeResult,
        expressionMode: 'uvOnly',
        adjustment: {
          ...ZERO_ADJUSTMENT,
          upperLipTightness: 0.1,
          lowerLipTightness: 0.2,
          upperInnerFill,
        },
        generatedAtMs: 1000 + Math.round(upperInnerFill * 100),
      }).package!,
  );
  const baseUv = packages[0].uvCoverageMetadata as Record<string, number>;
  const strongestUv = packages[packages.length - 1]
    .uvCoverageMetadata as Record<string, number>;

  for (const generatedPackage of packages) {
    const boundary = generatedPackage.lipBoundary2D as NonNullable<
      E7NativeBoundaryResult['boundary']
    >;
    expect(polygonSelfIntersectionCount(boundary.innerPoints)).toBe(0);
    expect(
      tinyAlphaHoleCount(
        generatedPackage.runtimeApplyPayload.maskRawRgbaBase64!,
        generatedPackage.runtimeApplyPayload.maskTextureWidth!,
        generatedPackage.runtimeApplyPayload.maskTextureHeight!,
      ),
    ).toBe(0);
  }

  expect(strongestUv.alphaSum).toBeGreaterThan(baseUv.alphaSum);
  expect(strongestUv.positiveTexels).toBeGreaterThanOrEqual(
    baseUv.positiveTexels,
  );
  expect(strongestUv.lowerLipGuardClippedTexels).toBe(0);
});

test('vertical offset plus moves lip boundary upward in top-left frame coordinates', () => {
  const nativeResult = makeNativeBoundaryResult();
  const basePackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const offsetPlusPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      verticalOffset: 0.35,
    },
    generatedAtMs: 1000,
  }).package!;
  const offsetMinusPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      verticalOffset: -0.35,
    },
    generatedAtMs: 1000,
  }).package!;

  const baseBoundary = basePackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const offsetPlusBoundary = offsetPlusPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const offsetMinusBoundary = offsetMinusPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;

  expect(minY(offsetPlusBoundary.outerPoints)).toBeLessThan(
    minY(baseBoundary.outerPoints),
  );
  expect(maxY(offsetMinusBoundary.outerPoints)).toBeGreaterThan(
    maxY(baseBoundary.outerPoints),
  );
});

test('corner reach plus expands horizontal boundary width', () => {
  const nativeResult = makeNativeBoundaryResult();
  const basePackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const cornerPlusPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      cornerReach: 0.35,
    },
    generatedAtMs: 1000,
  }).package!;
  const cornerMinusPackage = buildGeneratedLipPackage({
    nativeResult,
    expressionMode: 'uvOnly',
    adjustment: {
      ...ZERO_ADJUSTMENT,
      cornerReach: -0.35,
    },
    generatedAtMs: 1000,
  }).package!;

  const baseBoundary = basePackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const cornerPlusBoundary = cornerPlusPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;
  const cornerMinusBoundary = cornerMinusPackage.lipBoundary2D as NonNullable<
    E7NativeBoundaryResult['boundary']
  >;

  expect(minX(cornerPlusBoundary.outerPoints)).toBeLessThan(
    minX(baseBoundary.outerPoints),
  );
  expect(maxX(cornerPlusBoundary.outerPoints)).toBeGreaterThan(
    maxX(baseBoundary.outerPoints),
  );
  expect(minX(cornerMinusBoundary.outerPoints)).toBeGreaterThan(
    minX(baseBoundary.outerPoints),
  );
  expect(maxX(cornerMinusBoundary.outerPoints)).toBeLessThan(
    maxX(baseBoundary.outerPoints),
  );
});

test('generated UV mask defaults to 512 with antialias and hole metrics', () => {
  const generatedPackage = buildGeneratedLipPackage({
    nativeResult: makeNativeBoundaryResult(),
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const metadata = generatedPackage.uvCoverageMetadata!;

  expect(generatedPackage.runtimeApplyPayload.maskTextureWidth).toBe(512);
  expect(generatedPackage.runtimeApplyPayload.maskTextureHeight).toBe(512);
  expect(metadata.uvResolution).toBe(512);
  expect(metadata.alphaBoundingBoxTexels).toBeTruthy();
  expect(metadata.edgeBandTexels).toBeGreaterThan(0);
  expect(metadata.edgeBandRatio).toBeGreaterThan(0);
  expect(metadata.innerHoleSampleCount).toBeGreaterThan(0);
  expect(metadata.innerHolePositiveRatio).toBeLessThanOrEqual(0.01);
  expect(metadata.previewVsUvRoundTripDelta).toBeLessThanOrEqual(0.35);
});

test('blendshapeAssist builds a capture-set consensus raw UV mask', () => {
  const neutral = makeCaptureSetShot('neutral');
  const smile = makeCaptureSetShot('smile', { scaleX: 1.16, scaleY: 1.05 });
  const pucker = makeCaptureSetShot('pucker', { scaleX: 0.96, scaleY: 1.16 });
  const mouthOpen = makeCaptureSetShot('mouthOpen', { scaleY: 1.2 });

  const uvOnlyPackage = buildGeneratedLipPackage({
    nativeResult: neutral,
    providerResults: [neutral, smile, pucker, mouthOpen],
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const blendPackage = buildGeneratedLipPackage({
    nativeResult: neutral,
    providerResults: [neutral, smile, pucker, mouthOpen],
    expressionMode: 'blendshapeAssist',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const blendMetadata = blendPackage.uvCoverageMetadata!;

  expect(blendPackage.runtimeApplyPayload.maskRawRgbaBase64).not.toBe(
    uvOnlyPackage.runtimeApplyPayload.maskRawRgbaBase64,
  );
  expect(blendMetadata.blendMaskKind).toBe('capture_set_consensus_v1');
  expect(blendMetadata.blendShotKindsUsed).toEqual([
    'neutral',
    'smile',
    'pucker',
    'mouthOpen',
  ]);
  expect(blendMetadata.blendUsableShotCount).toBe(4);
  expect(blendMetadata.uvOnlyAlphaChecksum).toBe(
    uvOnlyPackage.uvCoverageMetadata?.alphaChecksum,
  );
  expect(blendMetadata.blendAlphaChecksum).not.toBe(
    blendMetadata.uvOnlyAlphaChecksum,
  );
  expect(blendMetadata.uvOnlyVsBlendAlphaDelta).toBeGreaterThan(0);
  expect(blendPackage.blendshapeAssist.blendMaskKind).toBe(
    'capture_set_consensus_v1',
  );
  expect(blendPackage.blendshapeAssist.uvOnlyVsBlendAlphaDelta).toBeGreaterThan(
    0,
  );
  expect(blendPackage.qualityWarnings).toContain(
    'blend_mask_capture_set_consensus_v1_4_shots',
  );
});

test('blendshapeAssist records an honest fallback with one usable shot', () => {
  const neutral = makeCaptureSetShot('neutral');
  const uvOnlyPackage = buildGeneratedLipPackage({
    nativeResult: neutral,
    providerResults: [neutral],
    expressionMode: 'uvOnly',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;
  const blendPackage = buildGeneratedLipPackage({
    nativeResult: neutral,
    providerResults: [neutral],
    expressionMode: 'blendshapeAssist',
    adjustment: ZERO_ADJUSTMENT,
    generatedAtMs: 1000,
  }).package!;

  expect(blendPackage.runtimeApplyPayload.maskRawRgbaBase64).toBe(
    uvOnlyPackage.runtimeApplyPayload.maskRawRgbaBase64,
  );
  expect(blendPackage.uvCoverageMetadata?.blendMaskKind).toBe(
    'neutral_single_shot_v1',
  );
  expect(blendPackage.uvCoverageMetadata?.blendFallbackReason).toBe(
    'blend_fallback_single_shot',
  );
  expect(blendPackage.uvCoverageMetadata?.uvOnlyVsBlendAlphaDelta).toBe(0);
  expect(blendPackage.blendshapeAssist.warning).toBe(
    'blend_fallback_single_shot',
  );
  expect(blendPackage.qualityWarnings).toContain('blend_fallback_single_shot');
});

test('UV mask raw texture rows match Unity bottom-left texture memory', () => {
  const uv = buildUvMaskRawRgba({
    boundary: {
      coordinateSpace: 'frame_image_pixel_top_left',
      source: 'vision',
      generationMethod: 'test_top_half_boundary',
      outerPoints: [
        { x: 70, y: 24 },
        { x: 170, y: 24 },
        { x: 170, y: 64 },
        { x: 70, y: 64 },
      ],
      innerPoints: [],
    },
    arFaceExport: {
      capturePairId: 'pair_face_boundary_test_0001',
      screenVertices: [
        [0, 0, 1],
        [240, 0, 1],
        [0, 240, 1],
        [240, 240, 1],
      ],
      uvs: [
        [0, 1],
        [1, 1],
        [0, 0],
        [1, 0],
      ],
      indices: [0, 1, 2, 1, 3, 2],
      display: {
        videoFrameSize: [240, 240],
        orientation: 'portrait',
        isMirrored: false,
      },
    },
    resolution: 32,
    sampleStride: 2,
  });

  expect(uv.positiveTexels).toBeGreaterThan(0);
  expect(uv.alphaBoundingBoxTexels?.minRow).toBeGreaterThan(20);
});
