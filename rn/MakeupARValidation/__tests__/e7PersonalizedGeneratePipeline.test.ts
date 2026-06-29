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
};

const VISIBLE_ADJUSTMENT: LipAdjustment = {
  cornerReach: 0.8,
  upperLipTightness: 0.65,
  lowerLipTightness: 0.7,
  verticalOffset: 0.35,
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

function maxY(points: NonNullable<E7NativeBoundaryResult['boundary']>['outerPoints']) {
  return Math.max(...points.map(point => point.y));
}

function minY(points: NonNullable<E7NativeBoundaryResult['boundary']>['outerPoints']) {
  return Math.min(...points.map(point => point.y));
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
