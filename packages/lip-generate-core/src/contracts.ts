export type LipMaskProvider = 'vision' | 'mediapipe';

export type ExpressionAssistMode = 'uvOnly' | 'blendshapeAssist';

export type LipGenerateStatus = 'ready' | 'partial' | 'blocked';

export type LipFrameSource = 'fixture' | 'webcam' | 'ios-current-frame';

export type LipAdjustment = {
  cornerReach: number;
  upperLipTightness: number;
  lowerLipTightness: number;
  verticalOffset: number;
};

export type LipGeneratePrivacy = {
  localOnly: true;
  offDeviceUpload: false;
  longTermRawFrameStored: false;
};

export type LipGenerateRequest = {
  requestId: string;
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  adjustment: LipAdjustment;
  frameSource: LipFrameSource;
  fixtureId?: string;
  privacy: LipGeneratePrivacy;
};

export type LipPoint2D = {
  x: number;
  y: number;
};

export type LipBoundary2D = {
  coordinateSpace: 'frame_image_pixel_top_left';
  outerPoints: LipPoint2D[];
  innerPoints: LipPoint2D[];
  source: LipMaskProvider;
};

export type LipSourceFrameMetadata = {
  capturePairId?: string;
  framePath?: string;
  frameWidth?: number;
  frameHeight?: number;
  orientation?: string;
  isMirrored?: boolean;
};

export type LipSourceFaceState = {
  blendshapeAvailable: boolean;
  warning?: string;
  values?: Record<string, number>;
};

export type LipUvCoverageMetadata = {
  uvResolution?: number;
  coverageTexels?: number;
  unknownTexels?: number;
  roundTripKind?: 'same_frame_self_reconstruction' | 'held_out_projection';
  roundTripScore?: {
    iou?: number;
    precision?: number;
    recall?: number;
    leakage?: number;
    miss?: number;
  };
};

export type LipRuntimeApplyPayload = {
  schemaVersion: 'e7-generated-lip-mask-runtime-payload-v0';
  generatedMaskId: string;
  captureSetId?: string;
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  adjustment: LipAdjustment;
  maskTexturePath?: string;
  maskTextureId?: string;
  maskTextureEncoding?: 'png_base64' | 'raw_rgba_base64';
  maskPngBase64?: string;
  maskRawRgbaBase64?: string;
  maskTextureWidth?: number;
  maskTextureHeight?: number;
  maskThreshold: number;
  maskFeatherUvNormalized: number;
  localOnly: true;
  offDeviceUpload: false;
  longTermRawFrameStored: false;
  runtimeReady: boolean;
};

export type LipProviderResultSummary = {
  status: LipGenerateStatus;
  provider: LipMaskProvider;
  capturePairId?: string;
  captureShotKind?: string;
  frameWidth?: number;
  frameHeight?: number;
  outerPointCount?: number;
  innerPointCount?: number;
  generationMethod?: string;
  fullFaceLandmarksPath?: string;
  blockedReason?: string;
  warnings?: string[];
};

export type LipBlendshapeAssistMetadata = {
  mode: ExpressionAssistMode;
  enabled: boolean;
  source: 'arface-blendshapes';
  materialFeatherUvNormalized: number;
  values?: Record<string, number>;
  warning?: string;
};

export type LipGeneratePackage = {
  schemaVersion: 'e7-personalized-lip-generate-package-v0';
  generatedMaskId: string;
  captureSetId: string;
  provider: LipMaskProvider;
  providerResults: Partial<Record<LipMaskProvider, LipProviderResultSummary>>;
  expressionMode: ExpressionAssistMode;
  blendshapeAssist: LipBlendshapeAssistMetadata;
  adjustment: LipAdjustment;
  sourceFrameMetadata: LipSourceFrameMetadata;
  sourceFaceState: LipSourceFaceState;
  lipBoundary2D?: LipBoundary2D;
  uvMaskTexture?: string;
  uvCoverageMetadata?: LipUvCoverageMetadata;
  roundTripPreview?: string;
  runtimeApplyPayload: LipRuntimeApplyPayload;
  qualityWarnings: string[];
  createdAt: string;
  privacyFlags: LipGeneratePrivacy;
};

export type LipGenerateResult = {
  status: LipGenerateStatus;
  generatedMaskId: string;
  provider: LipMaskProvider;
  expressionMode: ExpressionAssistMode;
  uvMaskReady: boolean;
  roundTripReady: boolean;
  runtimeApplyReady: boolean;
  warnings: string[];
  blockedReason?: string;
  package?: LipGeneratePackage;
};

export const DEFAULT_LIP_ADJUSTMENT: LipAdjustment = {
  cornerReach: 0,
  upperLipTightness: 0,
  lowerLipTightness: 0,
  verticalOffset: 0,
};

export const REQUIRED_PACKAGE_FIELDS = [
  'generatedMaskId',
  'captureSetId',
  'provider',
  'providerResults',
  'expressionMode',
  'blendshapeAssist',
  'adjustment',
  'sourceFrameMetadata',
  'sourceFaceState',
  'lipBoundary2D',
  'uvMaskTexture',
  'uvCoverageMetadata',
  'roundTripPreview',
  'runtimeApplyPayload',
  'qualityWarnings',
  'createdAt',
  'privacyFlags',
] as const;
