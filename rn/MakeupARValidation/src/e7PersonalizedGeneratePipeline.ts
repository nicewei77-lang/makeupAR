import {
  ExpressionAssistMode,
  LipAdjustment,
  LipGeneratePackage,
  LipMaskProvider,
} from '../../../packages/lip-generate-core/src';

export type E7CaptureShotKind =
  | 'neutral'
  | 'mouthOpen'
  | 'mouthClosed'
  | 'smile'
  | 'pucker'
  | 'yawLeft'
  | 'yawRight';

export type E7Point2D = {
  x: number;
  y: number;
};

export type E7LipBoundarySmoothingAlgorithm = 'curve_densified_v1';

export type E7LipBoundarySmoothingDiagnostics = {
  samplesPerSegment: number;
  originalOuterPointCount: number;
  originalInnerPointCount: number;
  smoothedOuterPointCount: number;
  smoothedInnerPointCount: number;
};

export type E7NativeBoundaryResult = {
  status: 'ready' | 'partial' | 'blocked';
  provider: LipMaskProvider;
  captureSetId: string;
  capturePairId: string;
  captureShotKind: E7CaptureShotKind;
  framePath: string;
  framePreviewUri?: string;
  arFaceExportPath: string;
  fullFaceLandmarksPath?: string;
  debugArtifacts?: {
    fullFaceLandmarks?: string;
  };
  frameWidth: number;
  frameHeight: number;
  boundary?: {
    coordinateSpace: 'frame_image_pixel_top_left';
    outerPoints: E7Point2D[];
    innerPoints: E7Point2D[];
    source: LipMaskProvider;
    generationMethod: string;
    boundarySmoothing?: E7LipBoundarySmoothingAlgorithm;
    originalPointCount?: number;
    smoothedPointCount?: number;
    smoothingDiagnostics?: E7LipBoundarySmoothingDiagnostics;
  };
  arFaceExport?: E7ArFaceExport;
  blendShapes?: E7BlendShapeState;
  warnings?: string[];
  blockedReason?: string;
};

export type E7ArFaceExport = {
  capturePairId?: string;
  screenVertices: number[][];
  uvs: number[][];
  indices: number[];
  display?: {
    videoFrameSize?: number[];
    orientation?: string;
    isMirrored?: boolean;
  };
};

export type E7BlendShapeState = {
  available: boolean;
  keySignals?: Record<string, number>;
  reason?: string;
};

export type E7GeneratedCandidate = {
  candidateKey: string;
  title: string;
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  status: 'ready' | 'partial' | 'blocked';
  package?: LipGeneratePackage;
  warnings: string[];
  blockedReason?: string;
};

const BASE64_ALPHABET =
  'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
const CURVE_DENSIFIED_ALGORITHM: E7LipBoundarySmoothingAlgorithm =
  'curve_densified_v1';
const CURVE_DENSIFIED_SAMPLES_PER_SEGMENT = 6;
const ADJUSTMENT_CORNER_REACH_SCALE = 0.46;
const ADJUSTMENT_VERTICAL_OFFSET_SCALE = 0.72;
const ADJUSTMENT_LIP_TIGHTNESS_SCALE = 0.48;
const UV_ALPHA_CHECKSUM_MOD = 2147483647;

type E7UvAlphaBoundingBox = {
  minColumn: number;
  minRow: number;
  maxColumn: number;
  maxRow: number;
};

type E7UvCoverageMetadataWithDiagnostics = NonNullable<
  LipGeneratePackage['uvCoverageMetadata']
> & {
  positiveTexels: number;
  alphaSum: number;
  alphaChecksum: number;
  alphaBoundingBoxTexels?: E7UvAlphaBoundingBox;
  boundarySmoothing: E7LipBoundarySmoothingAlgorithm;
  originalPointCount: number;
  smoothedPointCount: number;
};

export function encodeBase64(bytes: Uint8Array): string {
  let output = '';
  let index = 0;
  for (; index + 2 < bytes.length; index += 3) {
    const first = bytes[index];
    const second = bytes[index + 1];
    const third = bytes[index + 2];
    output += BASE64_ALPHABET[Math.floor(first / 4)];
    output += BASE64_ALPHABET[((first % 4) * 16) + Math.floor(second / 16)];
    output += BASE64_ALPHABET[((second % 16) * 4) + Math.floor(third / 64)];
    output += BASE64_ALPHABET[third % 64];
  }
  if (index < bytes.length) {
    const second = index + 1 < bytes.length ? bytes[index + 1] : 0;
    output += BASE64_ALPHABET[Math.floor(bytes[index] / 4)];
    output +=
      BASE64_ALPHABET[((bytes[index] % 4) * 16) + Math.floor(second / 16)];
    output +=
      index + 1 < bytes.length
        ? BASE64_ALPHABET[(second % 16) * 4]
        : '=';
    output += '=';
  }
  return output;
}

function pointInPolygon(point: E7Point2D, polygon: E7Point2D[]) {
  let inside = false;
  for (
    let index = 0, previousIndex = polygon.length - 1;
    index < polygon.length;
    previousIndex = index++
  ) {
    const current = polygon[index];
    const previous = polygon[previousIndex];
    const intersects =
      current.y > point.y !== previous.y > point.y &&
      point.x <
        ((previous.x - current.x) * (point.y - current.y)) /
          (previous.y - current.y || Number.EPSILON) +
          current.x;
    if (intersects) {
      inside = !inside;
    }
  }
  return inside;
}

function isInLipMask(point: E7Point2D, outer: E7Point2D[], inner: E7Point2D[]) {
  if (outer.length < 3) {
    return false;
  }
  if (!pointInPolygon(point, outer)) {
    return false;
  }
  return inner.length < 3 || !pointInPolygon(point, inner);
}

function adjustNativeLipBoundary(
  boundary: NonNullable<E7NativeBoundaryResult['boundary']>,
  adjustment: LipAdjustment,
  frameSize: { width: number; height: number },
): NonNullable<E7NativeBoundaryResult['boundary']> {
  const referenceBounds = bounds(boundary.outerPoints);
  if (!referenceBounds) {
    return { ...boundary, outerPoints: [], innerPoints: [] };
  }

  return {
    ...boundary,
    outerPoints: applyLipAdjustmentToPoints(
      boundary.outerPoints,
      adjustment,
      referenceBounds,
      frameSize,
    ),
    innerPoints: applyLipAdjustmentToPoints(
      boundary.innerPoints,
      adjustment,
      referenceBounds,
      frameSize,
      { inner: true },
    ),
  };
}

export function smoothLipBoundaryCurveDensified(
  boundary: NonNullable<E7NativeBoundaryResult['boundary']>,
  frameSize: { width: number; height: number },
): NonNullable<E7NativeBoundaryResult['boundary']> {
  const outerPoints = densifyClosedCurve(
    boundary.outerPoints,
    frameSize,
    CURVE_DENSIFIED_SAMPLES_PER_SEGMENT,
  );
  const innerPoints = densifyClosedCurve(
    boundary.innerPoints,
    frameSize,
    CURVE_DENSIFIED_SAMPLES_PER_SEGMENT,
  );
  const originalPointCount =
    boundary.outerPoints.length + boundary.innerPoints.length;
  const smoothedPointCount = outerPoints.length + innerPoints.length;

  return {
    ...boundary,
    outerPoints,
    innerPoints,
    generationMethod: `${boundary.generationMethod}+${CURVE_DENSIFIED_ALGORITHM}`,
    boundarySmoothing: CURVE_DENSIFIED_ALGORITHM,
    originalPointCount,
    smoothedPointCount,
    smoothingDiagnostics: {
      samplesPerSegment: CURVE_DENSIFIED_SAMPLES_PER_SEGMENT,
      originalOuterPointCount: boundary.outerPoints.length,
      originalInnerPointCount: boundary.innerPoints.length,
      smoothedOuterPointCount: outerPoints.length,
      smoothedInnerPointCount: innerPoints.length,
    },
  };
}

function densifyClosedCurve(
  points: E7Point2D[],
  frameSize: { width: number; height: number },
  samplesPerSegment: number,
): E7Point2D[] {
  if (points.length < 3) {
    return points.map(point => ({
      x: clamp(point.x, 0, Math.max(0, frameSize.width - 1)),
      y: clamp(point.y, 0, Math.max(0, frameSize.height - 1)),
    }));
  }

  const densified: E7Point2D[] = [];
  const count = points.length;
  for (let index = 0; index < count; index++) {
    const previous = points[(index - 1 + count) % count];
    const current = points[index];
    const next = points[(index + 1) % count];
    const afterNext = points[(index + 2) % count];

    for (let sample = 0; sample < samplesPerSegment; sample++) {
      const t = sample / samplesPerSegment;
      const point = catmullRomPoint(previous, current, next, afterNext, t);
      densified.push({
        x: clamp(point.x, 0, Math.max(0, frameSize.width - 1)),
        y: clamp(point.y, 0, Math.max(0, frameSize.height - 1)),
      });
    }
  }

  return densified;
}

function catmullRomPoint(
  p0: E7Point2D,
  p1: E7Point2D,
  p2: E7Point2D,
  p3: E7Point2D,
  t: number,
): E7Point2D {
  const t2 = t * t;
  const t3 = t2 * t;
  return {
    x:
      0.5 *
      (2 * p1.x +
        (-p0.x + p2.x) * t +
        (2 * p0.x - 5 * p1.x + 4 * p2.x - p3.x) * t2 +
        (-p0.x + 3 * p1.x - 3 * p2.x + p3.x) * t3),
    y:
      0.5 *
      (2 * p1.y +
        (-p0.y + p2.y) * t +
        (2 * p0.y - 5 * p1.y + 4 * p2.y - p3.y) * t2 +
        (-p0.y + 3 * p1.y - 3 * p2.y + p3.y) * t3),
  };
}

function applyLipAdjustmentToPoints(
  points: E7Point2D[],
  adjustment: LipAdjustment,
  referenceBounds: [number, number, number, number],
  frameSize: { width: number; height: number },
  options: { inner?: boolean } = {},
): E7Point2D[] {
  const [minX, minY, maxX, maxY] = referenceBounds;
  const width = Math.max(maxX - minX, 1);
  const height = Math.max(maxY - minY, 1);
  const centerX = minX + width * 0.5;
  const centerY = minY + height * 0.5;
  const cornerScale = options.inner ? 0.45 : 1;
  const tightnessScale = options.inner ? 0.35 : 1;

  return points.map(point => {
    const dx = point.x - centerX;
    const dy = point.y - centerY;
    const cornerWeight = Math.min(1, Math.abs(dx) / (width * 0.5));
    const verticalWeight = Math.min(1, Math.abs(dy) / (height * 0.5));

    let x =
      centerX +
      dx *
        (1 +
          adjustment.cornerReach *
            ADJUSTMENT_CORNER_REACH_SCALE *
            cornerWeight *
            cornerScale);
    let y =
      point.y +
      adjustment.verticalOffset * height * ADJUSTMENT_VERTICAL_OFFSET_SCALE;

    if (dy < 0) {
      y +=
        adjustment.upperLipTightness *
        height *
        ADJUSTMENT_LIP_TIGHTNESS_SCALE *
        verticalWeight *
        tightnessScale;
    } else if (dy > 0) {
      y -=
        adjustment.lowerLipTightness *
        height *
        ADJUSTMENT_LIP_TIGHTNESS_SCALE *
        verticalWeight *
        tightnessScale;
    }

    return {
      x: clamp(x, 0, Math.max(0, frameSize.width - 1)),
      y: clamp(y, 0, Math.max(0, frameSize.height - 1)),
    };
  });
}

function bounds(points: E7Point2D[]): [number, number, number, number] | null {
  if (!points.length) {
    return null;
  }

  return points.reduce(
    ([minX, minY, maxX, maxY], point) => [
      Math.min(minX, point.x),
      Math.min(minY, point.y),
      Math.max(maxX, point.x),
      Math.max(maxY, point.y),
    ],
    [
      Number.POSITIVE_INFINITY,
      Number.POSITIVE_INFINITY,
      Number.NEGATIVE_INFINITY,
      Number.NEGATIVE_INFINITY,
    ] as [number, number, number, number],
  );
}

function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

function barycentric(
  px: number,
  py: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
  cx: number,
  cy: number,
) {
  const denominator = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy);
  if (Math.abs(denominator) < 1e-6) {
    return null;
  }
  const w0 = ((by - cy) * (px - cx) + (cx - bx) * (py - cy)) / denominator;
  const w1 = ((cy - ay) * (px - cx) + (ax - cx) * (py - cy)) / denominator;
  const w2 = 1 - w0 - w1;
  if (w0 < -1e-5 || w1 < -1e-5 || w2 < -1e-5) {
    return null;
  }
  return [w0, w1, w2] as const;
}

function interpolateUv(
  weights: readonly [number, number, number],
  triangleUvs: number[][],
  triangleScreen: number[][],
) {
  const clipW = triangleScreen.map(vertex =>
    Math.abs(vertex[3] ?? 1) < 1e-6 ? 1 : vertex[3] ?? 1,
  );
  const invW = clipW.map(value => 1 / value);
  const denominator =
    weights[0] * invW[0] + weights[1] * invW[1] + weights[2] * invW[2];
  const safeDenominator = Math.abs(denominator) < 1e-6 ? 1 : denominator;
  const u =
    (weights[0] * triangleUvs[0][0] * invW[0] +
      weights[1] * triangleUvs[1][0] * invW[1] +
      weights[2] * triangleUvs[2][0] * invW[2]) /
    safeDenominator;
  const v =
    (weights[0] * triangleUvs[0][1] * invW[0] +
      weights[1] * triangleUvs[1][1] * invW[1] +
      weights[2] * triangleUvs[2][1] * invW[2]) /
    safeDenominator;
  return { u: Math.max(0, Math.min(1, u)), v: Math.max(0, Math.min(1, v)) };
}

function uvToIndex(u: number, v: number, resolution: number) {
  const column = Math.round(u * (resolution - 1));
  const row = Math.round((1 - v) * (resolution - 1));
  return row * resolution + column;
}

export function buildUvMaskRawRgba(input: {
  boundary: NonNullable<E7NativeBoundaryResult['boundary']>;
  arFaceExport: E7ArFaceExport;
  resolution?: number;
  sampleStride?: number;
}) {
  const resolution = input.resolution ?? 128;
  const sampleStride = input.sampleStride ?? 4;
  const texelCount = resolution * resolution;
  const positiveVotes = new Uint16Array(texelCount);
  const totalVotes = new Uint16Array(texelCount);
  const { boundary, arFaceExport } = input;
  const { screenVertices, uvs, indices } = arFaceExport;

  for (let index = 0; index + 2 < indices.length; index += 3) {
    const triangle = [indices[index], indices[index + 1], indices[index + 2]];
    if (
      triangle.some(
        vertexIndex =>
          vertexIndex < 0 ||
          vertexIndex >= screenVertices.length ||
          vertexIndex >= uvs.length,
      )
    ) {
      continue;
    }

    const triScreen = triangle.map(vertexIndex => screenVertices[vertexIndex]);
    const triUv = triangle.map(vertexIndex => uvs[vertexIndex]);
    const minX = Math.max(0, Math.floor(Math.min(...triScreen.map(v => v[0]))));
    const maxX = Math.min(
      Math.max(0, input.boundary.outerPoints.reduce((max, p) => Math.max(max, p.x), 0) * 3),
      Math.ceil(Math.max(...triScreen.map(v => v[0]))),
    );
    const minY = Math.max(0, Math.floor(Math.min(...triScreen.map(v => v[1]))));
    const maxY = Math.ceil(Math.max(...triScreen.map(v => v[1])));
    if (maxX < minX || maxY < minY) {
      continue;
    }

    for (let y = minY; y <= maxY; y += sampleStride) {
      for (let x = minX; x <= maxX; x += sampleStride) {
        const weights = barycentric(
          x,
          y,
          triScreen[0][0],
          triScreen[0][1],
          triScreen[1][0],
          triScreen[1][1],
          triScreen[2][0],
          triScreen[2][1],
        );
        if (!weights) {
          continue;
        }
        const uv = interpolateUv(weights, triUv, triScreen);
        const texelIndex = uvToIndex(uv.u, uv.v, resolution);
        totalVotes[texelIndex] = Math.min(65535, totalVotes[texelIndex] + 1);
        if (
          isInLipMask(
            { x, y },
            boundary.outerPoints,
            boundary.innerPoints,
          )
        ) {
          positiveVotes[texelIndex] = Math.min(
            65535,
            positiveVotes[texelIndex] + 1,
          );
        }
      }
    }
  }

  const raw = new Uint8Array(texelCount * 4);
  let coverageTexels = 0;
  let positiveTexels = 0;
  let alphaSum = 0;
  let alphaChecksum = 0;
  let minColumn = resolution;
  let minRow = resolution;
  let maxColumn = -1;
  let maxRow = -1;
  for (let texelIndex = 0; texelIndex < texelCount; texelIndex++) {
    const total = totalVotes[texelIndex];
    const probability = total > 0 ? positiveVotes[texelIndex] / total : 0;
    const alpha = Math.round(Math.max(0, Math.min(1, probability)) * 255);
    const rawIndex = texelIndex * 4;
    raw[rawIndex] = alpha;
    raw[rawIndex + 1] = alpha;
    raw[rawIndex + 2] = alpha;
    raw[rawIndex + 3] = alpha;
    if (total > 0) {
      coverageTexels += 1;
    }
    alphaSum += alpha;
    alphaChecksum =
      (alphaChecksum + ((texelIndex + 1) * alpha) % UV_ALPHA_CHECKSUM_MOD) %
      UV_ALPHA_CHECKSUM_MOD;
    if (alpha > 8) {
      positiveTexels += 1;
      const row = Math.floor(texelIndex / resolution);
      const column = texelIndex % resolution;
      minColumn = Math.min(minColumn, column);
      minRow = Math.min(minRow, row);
      maxColumn = Math.max(maxColumn, column);
      maxRow = Math.max(maxRow, row);
    }
  }

  return {
    rawRgbaBase64: encodeBase64(raw),
    width: resolution,
    height: resolution,
    coverageTexels,
    positiveTexels,
    unknownTexels: texelCount - coverageTexels,
    alphaSum,
    alphaChecksum,
    alphaBoundingBoxTexels:
      positiveTexels > 0
        ? { minColumn, minRow, maxColumn, maxRow }
        : undefined,
  };
}

function formatAdjustmentHash(adjustment: LipAdjustment): string {
  const scaled = [
    adjustment.cornerReach,
    adjustment.upperLipTightness,
    adjustment.lowerLipTightness,
    adjustment.verticalOffset,
  ].map(value => {
    const rounded = Math.round(value * 1000);
    const prefix = rounded < 0 ? 'm' : 'p';
    return `${prefix}${Math.abs(rounded).toString(36)}`;
  });
  return `adj-${scaled.join('-')}`;
}

export function buildGeneratedLipPackage(input: {
  nativeResult: E7NativeBoundaryResult;
  providerResults?: E7NativeBoundaryResult[];
  expressionMode: ExpressionAssistMode;
  adjustment: LipAdjustment;
  generatedAtMs?: number;
}): E7GeneratedCandidate {
  const { nativeResult, expressionMode, adjustment } = input;
  const generatedAtMs = input.generatedAtMs ?? Date.now();
  const candidateKey = `${nativeResult.provider}/${expressionMode}`;
  const title = `${nativeResult.provider} / ${
    expressionMode === 'blendshapeAssist' ? 'blend' : 'off'
  }`;
  const warnings = [...(nativeResult.warnings ?? [])];

  if (
    nativeResult.status === 'blocked' ||
    !nativeResult.boundary ||
    !nativeResult.arFaceExport
  ) {
    return {
      candidateKey,
      title,
      provider: nativeResult.provider,
      expressionMode,
      status: 'blocked',
      warnings,
      blockedReason:
        nativeResult.blockedReason ??
        'native_boundary_or_arface_export_missing',
    };
  }

  const adjustedBoundary = adjustNativeLipBoundary(
    nativeResult.boundary,
    adjustment,
    {
      width: nativeResult.frameWidth,
      height: nativeResult.frameHeight,
    },
  );
  const smoothedAdjustedBoundary = smoothLipBoundaryCurveDensified(
    adjustedBoundary,
    {
      width: nativeResult.frameWidth,
      height: nativeResult.frameHeight,
    },
  );
  const uv = buildUvMaskRawRgba({
    boundary: smoothedAdjustedBoundary,
    arFaceExport: nativeResult.arFaceExport,
  });
  const generatedMaskId = [
    'e7-generated-lip',
    nativeResult.captureSetId,
    nativeResult.provider,
    expressionMode,
    formatAdjustmentHash(adjustment),
    Math.round(generatedAtMs),
  ].join('-');
  const packageStatus =
    uv.positiveTexels > 0 && uv.coverageTexels > 0 ? 'partial' : 'blocked';
  const qualityWarnings = Array.from(
    new Set([
      ...warnings,
      'native_current_frame_generated',
      'runtimeReady_false_until_real_iPhone_apply_evidence',
      'same_frame_round_trip_pending_in_app_preview',
      'boundary_smoothing_curve_densified_v1',
      'adjustment_applied_before_uv_projection',
      expressionMode === 'blendshapeAssist'
        ? 'blendshape_assist_metadata_included'
        : 'blendshape_assist_off',
    ]),
  );
  const uvCoverageMetadata: E7UvCoverageMetadataWithDiagnostics = {
    uvResolution: uv.width,
    coverageTexels: uv.coverageTexels,
    positiveTexels: uv.positiveTexels,
    unknownTexels: uv.unknownTexels,
    alphaSum: uv.alphaSum,
    alphaChecksum: uv.alphaChecksum,
    alphaBoundingBoxTexels: uv.alphaBoundingBoxTexels,
    boundarySmoothing: CURVE_DENSIFIED_ALGORITHM,
    originalPointCount: smoothedAdjustedBoundary.originalPointCount ?? 0,
    smoothedPointCount: smoothedAdjustedBoundary.smoothedPointCount ?? 0,
    roundTripKind: 'same_frame_self_reconstruction',
  };
  const providerResults = Object.fromEntries(
    (input.providerResults ?? [nativeResult]).map(result => [
      result.provider,
      {
        status: result.status,
        provider: result.provider,
        capturePairId: result.capturePairId,
        captureShotKind: result.captureShotKind,
        frameWidth: result.frameWidth,
        frameHeight: result.frameHeight,
        outerPointCount: result.boundary?.outerPoints.length ?? 0,
        innerPointCount: result.boundary?.innerPoints.length ?? 0,
        generationMethod: result.boundary?.generationMethod,
        fullFaceLandmarksPath: result.fullFaceLandmarksPath,
        blockedReason: result.blockedReason,
        warnings: result.warnings ?? [],
      },
    ]),
  );
  const materialFeatherUvNormalized =
    expressionMode === 'blendshapeAssist' ? 0.09 : 0.07;
  const generatedPackage: LipGeneratePackage = {
    schemaVersion: 'e7-personalized-lip-generate-package-v0',
    generatedMaskId,
    captureSetId: nativeResult.captureSetId,
    provider: nativeResult.provider,
    providerResults,
    expressionMode,
    blendshapeAssist: {
      mode: expressionMode,
      enabled: expressionMode === 'blendshapeAssist',
      source: 'arface-blendshapes',
      materialFeatherUvNormalized,
      values: nativeResult.blendShapes?.keySignals,
      warning: nativeResult.blendShapes?.available
        ? undefined
        : nativeResult.blendShapes?.reason ?? 'blendshape_unavailable',
    },
    adjustment,
    sourceFrameMetadata: {
      capturePairId: nativeResult.capturePairId,
      framePath: nativeResult.framePath,
      frameWidth: nativeResult.frameWidth,
      frameHeight: nativeResult.frameHeight,
      orientation: nativeResult.arFaceExport.display?.orientation ?? 'unknown',
      isMirrored: nativeResult.arFaceExport.display?.isMirrored ?? false,
    },
    sourceFaceState: {
      blendshapeAvailable: Boolean(nativeResult.blendShapes?.available),
      warning: nativeResult.blendShapes?.available
        ? undefined
        : nativeResult.blendShapes?.reason ?? 'blendshape_unavailable',
      values: nativeResult.blendShapes?.keySignals,
    },
    lipBoundary2D: smoothedAdjustedBoundary,
    uvMaskTexture: `${generatedMaskId}.raw-rgba-${uv.width}x${uv.height}`,
    uvCoverageMetadata,
    roundTripPreview: 'in_app_round_trip_preview_pending',
    runtimeApplyPayload: {
      schemaVersion: 'e7-generated-lip-mask-runtime-payload-v0',
      generatedMaskId,
      captureSetId: nativeResult.captureSetId,
      provider: nativeResult.provider,
      expressionMode,
      adjustment,
      maskTextureId: generatedMaskId,
      maskTextureEncoding: 'raw_rgba_base64',
      maskRawRgbaBase64: uv.rawRgbaBase64,
      maskTextureWidth: uv.width,
      maskTextureHeight: uv.height,
      maskThreshold: 0.5,
      maskFeatherUvNormalized: materialFeatherUvNormalized,
      localOnly: true,
      offDeviceUpload: false,
      longTermRawFrameStored: false,
      runtimeReady: false,
    },
    qualityWarnings,
    createdAt: new Date(generatedAtMs).toISOString(),
    privacyFlags: {
      localOnly: true,
      offDeviceUpload: false,
      longTermRawFrameStored: false,
    },
  };

  return {
    candidateKey,
    title,
    provider: nativeResult.provider,
    expressionMode,
    status: packageStatus,
    package: generatedPackage,
    warnings: qualityWarnings,
    blockedReason:
      packageStatus === 'blocked' ? 'uv_projection_empty_mask' : undefined,
  };
}
