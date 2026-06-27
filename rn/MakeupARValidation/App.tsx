import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  GestureResponderEvent,
  Image,
  LayoutChangeEvent,
  LogBox,
  NativeModules,
  PanResponder,
  Pressable,
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  useColorScheme,
  View,
} from 'react-native';
import UnityView from '@azesmway/react-native-unity';
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';
import {
  buildUnityMessageFromPackage,
  ExpressionAssistMode as GeneratedExpressionAssistMode,
  LipGeneratePackage,
  LipMaskProvider as GeneratedLipMaskProvider,
} from '../../packages/lip-generate-core/src';
import {
  buildGeneratedLipPackage,
  E7CaptureShotKind,
  E7GeneratedCandidate,
  E7NativeBoundaryResult,
} from './src/e7PersonalizedGeneratePipeline';

LogBox.ignoreAllLogs(true);

const RECIPE_COLOR_OPTIONS = [
  { name: 'rose', color: '#D94B74' },
  { name: 'coral', color: '#E67B5F' },
  { name: 'nude', color: '#B9826B' },
] as const;

const RECIPE_REGION_OPTIONS = ['lip', 'cheek', 'eye'] as const;
const RECIPE_TEXTURE_SAMPLE_OPTIONS = [
  {
    name: 'matte_lip',
    label: 'matte lip',
    region: 'lip',
    textureMode: 'sample',
    blendMode: 'normal',
    intensity: 0.58,
    feather: 0.18,
  },
  {
    name: 'soft_blush',
    label: 'soft blush',
    region: 'cheek',
    textureMode: 'sample',
    blendMode: 'normal',
    intensity: 0.56,
    feather: 0.46,
  },
  {
    name: 'shimmer_eye',
    label: 'shimmer eye',
    region: 'eye',
    textureMode: 'sample',
    blendMode: 'screen',
    intensity: 0.58,
    feather: 0.38,
  },
] as const;
const LIP_COLOR_OPTIONS = [
  { name: 'rose', color: '#C76B74' },
  { name: 'berry', color: '#B83A55' },
  { name: 'muted', color: '#A94E5F' },
  { name: 'coral', color: '#D46A5E' },
  { name: 'nude', color: '#B9826B' },
] as const;
const LIP_SAMPLE_OPTIONS = [
  {
    name: 'lip_daily',
    label: 'daily',
    concept: 'daily',
    color: '#C76B74',
    opacity: 0.42,
    coverage: 0.72,
    feather: 0.1,
    blendMode: 'multiply',
    finish: 'cream',
    textureAmount: 0.08,
    roughness: 0.7,
    specular: 0.08,
    specularPower: 16,
    glossBoost: 0,
  },
  {
    name: 'lip_gloss',
    label: 'gloss',
    concept: 'gloss',
    color: '#B83A55',
    opacity: 0.62,
    coverage: 0.86,
    feather: 0.06,
    blendMode: 'multiply',
    finish: 'gloss',
    textureAmount: 0.05,
    roughness: 0.18,
    specular: 0.65,
    specularPower: 80,
    glossBoost: 0.55,
  },
  {
    name: 'lip_texture',
    label: 'texture',
    concept: 'texture',
    color: '#A94E5F',
    opacity: 0.54,
    coverage: 0.78,
    feather: 0.09,
    blendMode: 'multiply',
    finish: 'matte',
    textureAmount: 0.34,
    roughness: 0.92,
    specular: 0.02,
    specularPower: 8,
    glossBoost: 0,
  },
] as const;
const LIP_FINISH_OPTIONS = [
  { name: 'matte', label: 'matte' },
  { name: 'cream', label: 'cream' },
  { name: 'gloss', label: 'gloss' },
] as const;
const LIP_FINISH_DEFAULTS = {
  matte: {
    roughness: 0.92,
    specular: 0.02,
    specularPower: 8,
    glossBoost: 0,
  },
  cream: {
    roughness: 0.7,
    specular: 0.08,
    specularPower: 16,
    glossBoost: 0,
  },
  gloss: {
    roughness: 0.18,
    specular: 0.65,
    specularPower: 80,
    glossBoost: 0.55,
  },
} as const;
const LIP_TUNING_FIELD_OPTIONS = [
  { name: 'opacity', label: 'opac' },
  { name: 'coverage', label: 'cover' },
  { name: 'feather', label: 'edge' },
  { name: 'textureAmount', label: 'tex' },
  { name: 'glossBoost', label: 'gloss' },
] as const;
const LIP_ADJUSTMENT_FIELD_OPTIONS = [
  { name: 'cornerReach', label: 'corner' },
  { name: 'upperLipTightness', label: 'upper' },
  { name: 'lowerLipTightness', label: 'lower' },
  { name: 'verticalOffset', label: 'y' },
] as const;
const LIP_RUNTIME_CANDIDATE_OPTIONS = [
  {
    candidateId: 'lip-smooth-mask-v1',
    label: 'base',
    maskTextureId: 'lip-smooth-mask-v1',
    maskThreshold: 0.04,
    coverage: 0.72,
    feather: 0.1,
    status: 'baseline',
  },
  {
    candidateId: 'lip-tight-auto-v0',
    label: 'auto',
    maskTextureId: 'e7-lip-validation-tight-auto-v0',
    maskThreshold: 0.5,
    coverage: 0.72,
    feather: 0.08,
    status: 'validation-only',
  },
  {
    candidateId: 'lip-tight-user-v0',
    label: 'user',
    maskTextureId: 'e7-lip-validation-tight-user-v0',
    maskThreshold: 0.5,
    coverage: 0.72,
    feather: 0.08,
    status: 'pending-confirm',
  },
  {
    candidateId: 'lip-safe-v0',
    label: 'safe',
    maskTextureId: 'e7-lip-validation-safe-v0',
    maskThreshold: 0.65,
    coverage: 0.64,
    feather: 0.06,
    status: 'spill-check',
  },
  {
    candidateId: 'cv-parsing-smooth-v1',
    label: 'parse',
    maskTextureId: 'e7-lip-validation-cv-parsing-smooth-v1',
    maskThreshold: 0.5,
    coverage: 0.7,
    feather: 0.075,
    status: 'cv-smooth',
  },
  {
    candidateId: 'cv-vision-fill-v1',
    label: 'vision',
    maskTextureId: 'e7-lip-validation-cv-vision-fill-v1',
    maskThreshold: 0.5,
    coverage: 0.69,
    feather: 0.07,
    status: 'curve-fill',
  },
  {
    candidateId: 'cv-vision-color-v1',
    label: 'color',
    maskTextureId: 'e7-lip-validation-cv-vision-color-v1',
    maskThreshold: 0.5,
    coverage: 0.69,
    feather: 0.07,
    status: 'edge-snap',
  },
  {
    candidateId: 'cv-hybrid-safe-v1',
    label: 'safe2',
    maskTextureId: 'e7-lip-validation-cv-hybrid-safe-v1',
    maskThreshold: 0.54,
    coverage: 0.66,
    feather: 0.065,
    status: 'low-spill',
  },
  {
    candidateId: 'cv-hybrid-balanced-v1',
    label: 'bal2',
    maskTextureId: 'e7-lip-validation-cv-hybrid-balanced-v1',
    maskThreshold: 0.52,
    coverage: 0.7,
    feather: 0.07,
    status: 'coverage',
  },
] as const;
const LIP_GENERATE_PROVIDER_OPTIONS: Array<{
  name: GeneratedLipMaskProvider;
  label: string;
}> = [
  { name: 'vision', label: 'Vision' },
  { name: 'mediapipe', label: 'MediaPipe' },
];
const LIP_GENERATE_EXPRESSION_OPTIONS: Array<{
  name: GeneratedExpressionAssistMode;
  label: string;
}> = [
  { name: 'uvOnly', label: '기본 블렌딩' },
  { name: 'blendshapeAssist', label: '표정 보조' },
];
const E7_WIZARD_STEPS = [
  'start',
  'align',
  'capture',
  'extract',
  'blend',
  'adjust',
  'apply',
] as const;
const E7_CAPTURE_SHOT_OPTIONS: Array<{
  kind: E7CaptureShotKind;
  label: string;
  guidance: string;
}> = [
  { kind: 'neutral', label: '정면 기준', guidance: '입에 힘 빼고 정면' },
  { kind: 'mouthOpen', label: '살짝 벌림', guidance: '입 안쪽 분리 확인' },
  { kind: 'smile', label: '미소', guidance: '입꼬리 확장 확인' },
  { kind: 'pucker', label: '오므림', guidance: '중앙 압축 확인' },
  { kind: 'yawLeft', label: '왼쪽 각도', guidance: '가림/투영 안정성' },
  { kind: 'yawRight', label: '오른쪽 각도', guidance: '가림/투영 안정성' },
];
const GENERATED_LIP_MASK_SMOKE_RAW_RGBA_BASE64 =
  'AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA/////////////////////wAAAAAAAAAAAAAAAP////8AAAAAAAAAAAAAAAAAAAAA/////wAAAAAAAAAA////////////////////////////////AAAAAAAAAAAAAAAA/////////////////////wAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA==';
const E7_FULL_FACE_REGION_RUNTIME_LAYERS = [
  {
    region: 'lip',
    layer: 'lip',
    candidateId: 'lip-balanced-gold-v0',
    maskTextureId: 'e7-lip-balanced-uv-v0',
    maskThreshold: 0.35,
    maskFeatherUvNormalized: 0.07,
    color: '#C76B74',
    opacity: 0.62,
    texture: 'matte_lip',
    blendMode: 'multiply',
    intensity: 0.72,
    coverage: 1.0,
    skinAdaptive: true,
  },
  {
    region: 'blush',
    layer: 'blush',
    candidateId: 'blush-balanced-soft-oval-v0',
    maskTextureId: 'e7-blush-balanced-uv-v0',
    maskThreshold: 0.18,
    maskFeatherUvNormalized: 0.07,
    color: '#E67B5F',
    opacity: 0.45,
    texture: 'soft_blush',
    blendMode: 'normal',
    intensity: 0.45,
    coverage: 0.68,
    skinAdaptive: false,
  },
  {
    region: 'brow',
    layer: 'brow',
    candidateId: 'brow-balanced-stroke-envelope-v0',
    maskTextureId: 'e7-brow-balanced-uv-v0',
    maskThreshold: 0.14,
    maskFeatherUvNormalized: 0.07,
    color: '#5F4A42',
    opacity: 0.48,
    texture: 'shimmer_eye',
    blendMode: 'multiply',
    intensity: 0.72,
    coverage: 0.72,
    skinAdaptive: false,
  },
  {
    region: 'eyeliner',
    layer: 'eyeliner',
    candidateId: 'eyeliner-minimal-safe-lashline-v0',
    maskTextureId: 'e7-eyeliner-minimal-safe-uv-v0',
    maskThreshold: 0.12,
    maskFeatherUvNormalized: 0.07,
    color: '#2F2730',
    opacity: 0.66,
    texture: 'shimmer_eye',
    blendMode: 'multiply',
    intensity: 0.72,
    coverage: 0.72,
    skinAdaptive: false,
  },
] as const;
const E7_BOUNDARY_PLAN_VERSION = 'E7.03 v2.1';
const E7_EVIDENCE_MODE = 'smooth-mask-validation';
const LIP_ADJUSTMENT_STEP = 0.05;
const E7_CAPTURE_ACK_TIMEOUT_MS = 7_000;
const GENERATED_APPLY_ACK_TIMEOUT_MS = 10_000;
const GENERATED_CONTROL_ACK_TIMEOUT_MS = 3_000;
const GENERATED_MASK_VALIDATION_COLORS = [
  { name: 'rose', color: '#D94B74' },
  { name: 'hot', color: '#FF2D8A' },
  { name: 'gold', color: '#F2B84B' },
] as const;
const DEFAULT_GENERATED_MASK_VALIDATION_CONTROLS = {
  maskVisible: true,
  strongMode: true,
  colorHex: '#D94B74',
  opacity: 0.86,
  boundaryDebugVisible: false,
};

type RecipeColor = (typeof RECIPE_COLOR_OPTIONS)[number];
type RecipeRegion = (typeof RECIPE_REGION_OPTIONS)[number];
type RecipeTextureSample = (typeof RECIPE_TEXTURE_SAMPLE_OPTIONS)[number];
type LipColor = (typeof LIP_COLOR_OPTIONS)[number];
type LipSampleName = (typeof LIP_SAMPLE_OPTIONS)[number]['name'];
type LipFinish = (typeof LIP_FINISH_OPTIONS)[number]['name'];
type LipTuningField = (typeof LIP_TUNING_FIELD_OPTIONS)[number]['name'];
type LipAdjustmentField =
  (typeof LIP_ADJUSTMENT_FIELD_OPTIONS)[number]['name'];
type LipRuntimeCandidate =
  (typeof LIP_RUNTIME_CANDIDATE_OPTIONS)[number];
type LipRuntimeCandidateId = LipRuntimeCandidate['candidateId'];
type LipUserAdjustment = Record<LipAdjustmentField, number>;
type LipSample = {
  name: LipSampleName;
  label: string;
  concept: string;
  color: string;
  opacity: number;
  coverage: number;
  feather: number;
  blendMode: 'multiply';
  finish: LipFinish;
  textureAmount: number;
  roughness: number;
  specular: number;
  specularPower: number;
  glossBoost: number;
};
type RendererMode = 'smooth-region-mask';
type MaskTextureId =
  | 'lip-smooth-mask-v1'
  | 'e7-lip-validation-tight-auto-v0'
  | 'e7-lip-validation-tight-user-v0'
  | 'e7-lip-validation-safe-v0'
  | 'e7-lip-validation-cv-parsing-smooth-v1'
  | 'e7-lip-validation-cv-vision-fill-v1'
  | 'e7-lip-validation-cv-vision-color-v1'
  | 'e7-lip-validation-cv-hybrid-safe-v1'
  | 'e7-lip-validation-cv-hybrid-balanced-v1'
  | 'cheek-smooth-mask-v1'
  | 'eye-smooth-mask-v1';
type ValidationViewMode = 'clean' | 'compact' | 'full';
type E7WizardStep = (typeof E7_WIZARD_STEPS)[number];
type E7ShotStatus = 'pending' | 'capturing' | 'captured' | 'blocked';
type E7CaptureShotState = {
  kind: E7CaptureShotKind;
  status: E7ShotStatus;
  capturePairId?: string;
  relativeDirectory?: string;
  framePreviewUri?: string;
  detail?: string;
};
type E7NativeBoundaryModule = {
  extractLipBoundary?: (requestJson: string) => Promise<string>;
  saveGeneratedPackage?: (packageJson: string) => Promise<string>;
  renderLipMaskPreview?: (packageJson: string) => Promise<string>;
};
type E7SavedPackageRecord = {
  generatedMaskId?: string;
  packagePath?: string;
  metadataPath?: string;
  status?: string;
};
type E7GeneratedPreviewState = 'pending' | 'ready' | 'blocked';
type E7GeneratedPreviewResult = {
  status?: E7GeneratedPreviewState;
  previewUri?: string;
  previewPath?: string;
  blockedReason?: string;
};
type E7GeneratedCandidateWithPreview = E7GeneratedCandidate & {
  previewUri?: string;
  previewStatus?: E7GeneratedPreviewState;
  previewError?: string;
};
type E7GeneratedApplyStatus =
  | 'idle'
  | 'saving'
  | 'posting'
  | 'waitingAck'
  | 'applied'
  | 'blocked'
  | 'timeout';
type E7GeneratedApplyState = {
  status: E7GeneratedApplyStatus;
  generatedMaskId?: string;
  startedAtMs?: number;
  updatedAtMs: number;
  elapsedMs?: number;
  blockedReason?: string;
  error?: string;
  ack?: UnityEventPayload;
};
type GeneratedMaskValidationControls = {
  maskVisible: boolean;
  strongMode: boolean;
  colorHex: string;
  opacity: number;
  boundaryDebugVisible: boolean;
};
type PendingGeneratedControlCheck = {
  generatedMaskId: string;
  controls: GeneratedMaskValidationControls;
  requestedAtMs: number;
};
type E7AlignmentGateState = 'waiting' | 'ready' | 'blocked';
type E7AlignmentGate = {
  label: string;
  value: string;
  state: E7AlignmentGateState;
};
type RegionRecipe = {
  color: RecipeColor;
  opacity: number;
  textureSample: RecipeTextureSample;
};
type ActiveRegionMap = Record<RecipeRegion, boolean>;

const DEFAULT_RECIPE_REGION: RecipeRegion = 'lip';
const DEFAULT_RECIPE_COLOR = RECIPE_COLOR_OPTIONS[0];
const DEFAULT_LIP_SAMPLE = LIP_SAMPLE_OPTIONS[0];
const DEFAULT_LIP_RUNTIME_CANDIDATE = LIP_RUNTIME_CANDIDATE_OPTIONS[0];
const DEFAULT_LIP_USER_ADJUSTMENT: LipUserAdjustment = {
  cornerReach: 0,
  upperLipTightness: 0,
  lowerLipTightness: 0,
  verticalOffset: 0,
};
const DEFAULT_TEXTURE_SAMPLE_BY_REGION: Record<
  RecipeRegion,
  RecipeTextureSample
> = {
  lip: RECIPE_TEXTURE_SAMPLE_OPTIONS[0],
  cheek: RECIPE_TEXTURE_SAMPLE_OPTIONS[1],
  eye: RECIPE_TEXTURE_SAMPLE_OPTIONS[2],
};
const DEFAULT_REGION_RECIPES: Record<RecipeRegion, RegionRecipe> = {
  lip: {
    color: DEFAULT_RECIPE_COLOR,
    opacity: 0.52,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip,
  },
  cheek: {
    color: RECIPE_COLOR_OPTIONS[1],
    opacity: 0.44,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.cheek,
  },
  eye: {
    color: DEFAULT_RECIPE_COLOR,
    opacity: 0.48,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.eye,
  },
};
const DEFAULT_MASK_TEXTURE_ID_BY_REGION: Record<RecipeRegion, MaskTextureId> = {
  lip: 'lip-smooth-mask-v1',
  cheek: 'cheek-smooth-mask-v1',
  eye: 'eye-smooth-mask-v1',
};
const DEFAULT_ACTIVE_REGIONS: ActiveRegionMap = {
  lip: true,
  cheek: false,
  eye: false,
};
const E7_NATIVE_BOUNDARY_MODULE =
  NativeModules.E7NativeLipBoundaryProviders as E7NativeBoundaryModule | undefined;
const OPACITY_STEP = 0.05;
const UNITY_EVENT_HISTORY_LIMIT = 5;
const DEFAULT_RENDERER_MODE: RendererMode = 'smooth-region-mask';
const UNITY_EVENT_TYPES = [
  'unity_initialized',
  'face_detected',
  'face_lifecycle',
  'face_feature_snapshot',
  'e7_metric_sample',
  'e7_reference_capture',
  'recipe_applied',
  'generated_lip_mask_applied',
] as const;

type UnityMessageEvent = {
  nativeEvent: {
    message?: string;
  };
};

function createDefaultLipSampleSettings(): Record<LipSampleName, LipSample> {
  return LIP_SAMPLE_OPTIONS.reduce((settings, sample) => {
    settings[sample.name] = { ...sample };
    return settings;
  }, {} as Record<LipSampleName, LipSample>);
}

function createInitialCaptureShots(): Record<
  E7CaptureShotKind,
  E7CaptureShotState
> {
  return E7_CAPTURE_SHOT_OPTIONS.reduce((shots, option) => {
    shots[option.kind] = {
      kind: option.kind,
      status: 'pending',
    };
    return shots;
  }, {} as Record<E7CaptureShotKind, E7CaptureShotState>);
}

function createCaptureSetId(entryCount: number) {
  return `e7-capture-set-${entryCount}-${Date.now()}`;
}

function createGeneratedApplyState(
  status: E7GeneratedApplyStatus,
  patch: Partial<Omit<E7GeneratedApplyState, 'status' | 'updatedAtMs'>> = {},
): E7GeneratedApplyState {
  return {
    status,
    updatedAtMs: Date.now(),
    ...patch,
  };
}

function buildGeneratedMaskUnityMessage(
  generatedPackage: LipGeneratePackage,
  controls: GeneratedMaskValidationControls,
  options: { includeTexture: boolean },
) {
  const message: Record<string, unknown> = {
    ...buildUnityMessageFromPackage(generatedPackage),
    visible: controls.maskVisible,
    maskVisible: controls.maskVisible,
    validationVisible: controls.maskVisible,
    enabled: controls.maskVisible,
    strongValidationMode: controls.strongMode,
    validationStrongMode: controls.strongMode,
    validationStrong: controls.strongMode,
    strongMode: controls.strongMode,
    validationMode: controls.strongMode ? 'strong' : 'standard',
    validationViewMode: controls.strongMode ? 'strong' : 'standard',
    color: controls.colorHex,
    colorHex: controls.colorHex,
    validationColor: controls.colorHex,
    validationColorHex: controls.colorHex,
    opacity: controls.opacity,
    maskOpacity: controls.opacity,
    validationOpacity: controls.opacity,
    boundaryDebugVisible: controls.boundaryDebugVisible,
    boundaryDebug: controls.boundaryDebugVisible,
    debugBoundary: controls.boundaryDebugVisible,
    showBoundary: controls.boundaryDebugVisible,
    debugOverlayVisible: controls.boundaryDebugVisible,
  };

  if (!options.includeTexture) {
    delete message.maskPngBase64;
    delete message.maskRawRgbaBase64;
  }

  return message;
}

function doesGeneratedControlAckMatch(
  event: UnityEventPayload,
  controls: GeneratedMaskValidationControls,
) {
  const validationControls = isRecord(event.validationControls)
    ? event.validationControls
    : {};
  const visible = readBoolean(
    validationControls.visible ??
      event.visible ??
      event.maskVisible ??
      event.validationVisible,
  );
  const strongMode = readBoolean(
    validationControls.strongMode ??
      event.strongMode ??
      event.strongValidationMode,
  );
  const boundaryDebugVisible = readBoolean(
    validationControls.boundaryDebugVisible ??
      event.boundaryDebugVisible ??
      event.debugBoundary,
  );
  const colorHex = String(
    validationControls.colorHex ??
      validationControls.color ??
      event.colorHex ??
      event.validationColor ??
      event.color ??
      '',
  );
  const opacity = readNumber(
    validationControls.opacity ?? event.validationOpacity ?? event.opacity,
  );

  return (
    visible === controls.maskVisible &&
    strongMode === controls.strongMode &&
    boundaryDebugVisible === controls.boundaryDebugVisible &&
    colorHex.toLowerCase() === controls.colorHex.toLowerCase() &&
    opacity !== undefined &&
    Math.abs(opacity - controls.opacity) <= 0.011
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value);
}

function readBoolean(value: unknown) {
  return typeof value === 'boolean' ? value : undefined;
}

function getWizardStepIndex(step: E7WizardStep) {
  return E7_WIZARD_STEPS.indexOf(step);
}

function isCapturedShot(state: E7CaptureShotState) {
  return state.status === 'captured' && Boolean(state.relativeDirectory);
}

function countCapturedShots(
  shots: Record<E7CaptureShotKind, E7CaptureShotState>,
) {
  return Object.values(shots).filter(isCapturedShot).length;
}

type UnityEventPayload = {
  type?: string;
  tracked?: boolean;
  faceCount?: number;
  totalTrackables?: number;
  trackingStates?: string;
  timestamp?: string;
  phase?: string;
  sequence?: number;
  status?: string;
  selectedActiveFaceId?: string;
  previousActiveFaceId?: string;
  lastTrackedFaceId?: string;
  activeFaceChanged?: boolean;
  trackingState?: string;
  addedCount?: number;
  updatedCount?: number;
  removedCount?: number;
  addedFaces?: string;
  updatedFaces?: string;
  removedFaces?: string;
  faceTransform?: string;
  meshSummary?: string;
  providerCapabilitySnapshot?: string;
  schemaVersion?: number;
  timestampMs?: number;
  source?: string;
  deviceModel?: string;
  arSessionState?: string;
  cameraFacing?: string;
  orientation?: string;
  faceDetected?: boolean;
  lifecycleState?: string;
  rawCameraFrameStored?: boolean;
  offDeviceUpload?: boolean;
  activeRegionSummary?: string;
  appliedTextureSampleSummary?: string;
  activeRegions?: unknown;
  appliedTextureSamples?: unknown;
  activeFace?: unknown;
  mesh?: unknown;
  regions?: unknown;
  privacy?: unknown;
  capabilities?: unknown;
  region?: string;
  layer?: string;
  appliedRegion?: string;
  applied?: boolean;
  provider?: string;
  expressionMode?: string;
  generatedMaskId?: string;
  runtimeReady?: boolean;
  color?: string;
  opacity?: number;
  texture?: string;
  sample?: string;
  textureMode?: string;
  intensity?: number;
  feather?: number;
  blendMode?: string;
  runId?: string;
  rendererMode?: string;
  maskSource?: string;
  stateAction?: string;
  maskStatus?: string;
  regionUvAvailable?: boolean;
  regionMaskTriangles?: number;
  regionAppliedTriangles?: number;
  uvAvailable?: boolean;
  maskTriangles?: number;
  meshVertexCount?: number;
  meshIndexCount?: number;
  meshUvCount?: number;
  unityFrameworkBuildLabel?: string;
  lookId?: string;
  recipeId?: string;
  recipeBatchId?: string;
  layerCount?: number;
  enabledLayerCount?: number;
  payloadBytes?: number;
  sentAtMs?: number;
  appliedAtMs?: number;
  appliedFrame?: number;
  receivedAtMs?: number;
  coverage?: number;
  finish?: string;
  textureAmount?: number;
  roughness?: number;
  specular?: number;
  specularPower?: number;
  glossBoost?: number;
  shimmer?: number;
  shimmerColor?: string;
  skinAdaptive?: boolean;
  preserveDetail?: boolean;
  materialId?: string;
  shaderMode?: string;
  passCount?: number;
  candidateId?: string;
  maskTextureId?: string;
  maskThreshold?: number;
  maskFeatherUvNormalized?: number;
  cornerReach?: number;
  upperLipTightness?: number;
  lowerLipTightness?: number;
  verticalOffset?: number;
  cameraBackdropAvailable?: boolean;
  lightEstimateAvailable?: boolean;
  sampleWindowMs?: number;
  sampleFrameCount?: number;
  averageFps?: number;
  averageFrameTimeMs?: number;
  worstFrameTimeMs?: number;
  sustainedSub20FpsObserved?: boolean;
  memoryMetricAvailable?: boolean;
  memoryMetricSource?: string;
  allocatedMemoryMb?: number;
  reservedMemoryMb?: number;
  monoUsedMemoryMb?: number;
  memoryWarningObserved?: boolean;
  memoryMetricYellowCap?: boolean;
  thermalEvidenceType?: string;
  thermalWarningObserved?: boolean;
  manualHeatObservation?: string;
  thermalMetricYellowCap?: boolean;
  visualLatencyConfirmedByRecording?: boolean;
  visualLatencyObservation?: string;
  meshTriangles?: number;
  topologyAuditStatus?: string;
  topologyAuditSummary?: string;
  boundaryRenderer?: string;
  capturePairId?: string;
  relativeDirectory?: string;
  coordinateSpaceValidated?: boolean;
  coordinateSpaceValidationStatus?: string;
  detail?: string;
  framePreviewUri?: string;
  frameWidth?: number;
  validationControls?: unknown;
  [key: string]: unknown;
};

type UnityEventRecord = {
  id: number;
  receivedAt: string;
  receivedAtMs: number;
  rawMessage: string;
  displayText: string;
  parsed?: UnityEventPayload;
  parseError?: string;
};

type UnityEventType = (typeof UNITY_EVENT_TYPES)[number];
type UnityEventStatusMap = Partial<Record<UnityEventType, UnityEventRecord>>;

function App() {
  const isDarkMode = useColorScheme() === 'dark';
  const [isUnityOpen, setIsUnityOpen] = useState(false);
  const [unityEntryCount, setUnityEntryCount] = useState(0);
  const [unityExitCount, setUnityExitCount] = useState(0);

  const handleStartUnity = useCallback(() => {
    setUnityEntryCount(currentCount => {
      const nextCount = currentCount + 1;

      console.log('[E7] unity_screen_open', `entry=${nextCount}`);

      return nextCount;
    });
    setIsUnityOpen(true);
  }, []);

  const handleCloseUnity = useCallback(() => {
    setUnityExitCount(currentCount => {
      const nextCount = currentCount + 1;

      console.log('[E7] unity_screen_close', `exit=${nextCount}`);

      return nextCount;
    });
    setIsUnityOpen(false);
  }, []);

  return (
    <SafeAreaProvider>
      <StatusBar
        barStyle={isDarkMode ? 'light-content' : 'dark-content'}
        hidden={isUnityOpen}
      />
      <AppContent
        isUnityOpen={isUnityOpen}
        unityEntryCount={unityEntryCount}
        unityExitCount={unityExitCount}
        onStartUnity={handleStartUnity}
        onCloseUnity={handleCloseUnity}
      />
    </SafeAreaProvider>
  );
}

type AppContentProps = {
  isUnityOpen: boolean;
  unityEntryCount: number;
  unityExitCount: number;
  onStartUnity: () => void;
  onCloseUnity: () => void;
};

function AppContent({
  isUnityOpen,
  unityEntryCount,
  unityExitCount,
  onStartUnity,
  onCloseUnity,
}: AppContentProps) {
  if (isUnityOpen) {
    return (
      <UnityScreen
        key={`unity-entry-${unityEntryCount}`}
        entryCount={unityEntryCount}
        exitCount={unityExitCount}
        onClose={onCloseUnity}
      />
    );
  }

  return (
    <HomeScreen
      completedExitCount={unityExitCount}
      nextEntryCount={unityEntryCount + 1}
      onStart={onStartUnity}
    />
  );
}

type HomeScreenProps = {
  completedExitCount: number;
  nextEntryCount: number;
  onStart: () => void;
};

function HomeScreen({
  completedExitCount,
  nextEntryCount,
  onStart,
}: HomeScreenProps) {
  const safeAreaInsets = useSafeAreaInsets();
  const completedCycles = Math.min(completedExitCount, 3);

  return (
    <View
      style={[
        styles.home,
        {
          paddingTop: safeAreaInsets.top + 28,
          paddingBottom: safeAreaInsets.bottom + 28,
        },
      ]}
    >
      <View style={styles.homeBody}>
        <Text style={styles.kicker}>Makeup AR</Text>
        <Text style={styles.title}>맞춤 Generate</Text>
        <Text style={styles.statusLabel}>로컬 생성 준비</Text>
        <Text style={styles.statusText}>
          {`Entry #${nextEntryCount}. 얼굴 정렬, 촬영, 블렌딩 선택, 조정, 저장하고 AR 실행을 순서대로 진행합니다. Completed exits ${completedCycles}/3.`}
        </Text>
      </View>

      <Pressable
        accessibilityRole="button"
        style={({ pressed }) => [
          styles.primaryButton,
          pressed && styles.primaryButtonPressed,
        ]}
        onPress={onStart}
      >
          <Text style={styles.primaryButtonText}>시작</Text>
      </Pressable>
    </View>
  );
}

type UnityScreenProps = {
  entryCount: number;
  exitCount: number;
  onClose: () => void;
};

function UnityScreen({ entryCount, exitCount, onClose }: UnityScreenProps) {
  const safeAreaInsets = useSafeAreaInsets();
  const mountedAt = useMemo(() => new Date().toLocaleTimeString(), []);
  const unityRef = useRef<UnityView>(null);
  const [validationViewMode, setValidationViewMode] =
    useState<ValidationViewMode>('compact');
  const selectedRendererMode = DEFAULT_RENDERER_MODE;
  const [focusedRegion, setFocusedRegion] = useState<RecipeRegion>(
    DEFAULT_RECIPE_REGION,
  );
  const [activeRegions, setActiveRegions] = useState<ActiveRegionMap>(
    DEFAULT_ACTIVE_REGIONS,
  );
  const [regionRecipes] = useState<Record<RecipeRegion, RegionRecipe>>(
    DEFAULT_REGION_RECIPES,
  );
  const [selectedLipSampleName, setSelectedLipSampleName] =
    useState<LipSampleName>(DEFAULT_LIP_SAMPLE.name);
  const [selectedLipRuntimeCandidateId, setSelectedLipRuntimeCandidateId] =
    useState<LipRuntimeCandidateId>(
      DEFAULT_LIP_RUNTIME_CANDIDATE.candidateId,
    );
  const [lipSampleSettings, setLipSampleSettings] = useState<
    Record<LipSampleName, LipSample>
  >(createDefaultLipSampleSettings);
  const [lipUserAdjustment, setLipUserAdjustment] =
    useState<LipUserAdjustment>(DEFAULT_LIP_USER_ADJUSTMENT);
  const [lipGenerateProvider, setLipGenerateProvider] =
    useState<GeneratedLipMaskProvider>('vision');
  const [lipGenerateExpressionMode, setLipGenerateExpressionMode] =
    useState<GeneratedExpressionAssistMode>('uvOnly');
  const [lastGeneratedLipMaskSummary, setLastGeneratedLipMaskSummary] =
    useState('generated=none');
  const [activeLipTuningField, setActiveLipTuningField] =
    useState<LipTuningField>('opacity');
  const [activeLipAdjustmentField, setActiveLipAdjustmentField] =
    useState<LipAdjustmentField>('cornerReach');
  const [sliderWidth, setSliderWidth] = useState(1);
  const [lastUnityEvent, setLastUnityEvent] = useState<UnityEventRecord | null>(
    null,
  );
  const [unityEventHistory, setUnityEventHistory] = useState<
    UnityEventRecord[]
  >([]);
  const [unityEventStatus, setUnityEventStatus] = useState<UnityEventStatusMap>(
    {},
  );
  const [captureRequestSequence, setCaptureRequestSequence] = useState(1);
  const [pendingCapturePairId, setPendingCapturePairId] = useState<
    string | null
  >(null);
  const [wizardStep, setWizardStep] = useState<E7WizardStep>('start');
  const [captureSetId, setCaptureSetId] = useState(() =>
    createCaptureSetId(entryCount),
  );
  const [captureShots, setCaptureShots] = useState(
    createInitialCaptureShots,
  );
  const [pendingCaptureShotKind, setPendingCaptureShotKind] =
    useState<E7CaptureShotKind | null>(null);
  const [nativeProviderResults, setNativeProviderResults] = useState<
    Partial<Record<GeneratedLipMaskProvider, E7NativeBoundaryResult>>
  >({});
  const [nativeProviderShotResults, setNativeProviderShotResults] = useState<
    Partial<Record<GeneratedLipMaskProvider, E7NativeBoundaryResult[]>>
  >({});
  const [generatedCandidates, setGeneratedCandidates] = useState<
    E7GeneratedCandidateWithPreview[]
  >([]);
  const [selectedGeneratedCandidateKey, setSelectedGeneratedCandidateKey] =
    useState('vision/uvOnly');
  const [generatedCandidatesStale, setGeneratedCandidatesStale] =
    useState(false);
  const [savedGeneratedPackage, setSavedGeneratedPackage] =
    useState<E7SavedPackageRecord | null>(null);
  const [generatedApplyState, setGeneratedApplyState] =
    useState<E7GeneratedApplyState>(() => createGeneratedApplyState('idle'));
  const [pendingGeneratedMaskId, setPendingGeneratedMaskId] =
    useState<string | null>(null);
  const [pendingGeneratedPackage, setPendingGeneratedPackage] =
    useState<LipGeneratePackage | null>(null);
  const [appliedGeneratedPackage, setAppliedGeneratedPackage] =
    useState<LipGeneratePackage | null>(null);
  const [generatedValidationControls, setGeneratedValidationControls] =
    useState<GeneratedMaskValidationControls>({
      ...DEFAULT_GENERATED_MASK_VALIDATION_CONTROLS,
    });
  const [pendingGeneratedControlCheck, setPendingGeneratedControlCheck] =
    useState<PendingGeneratedControlCheck | null>(null);
  const [wizardNotice, setWizardNotice] = useState(
    '촬영부터 시작하는 맞춤 Generate flow입니다.',
  );
  const [isGeneratingCandidates, setIsGeneratingCandidates] = useState(false);
  const [isSavingGeneratedPackage, setIsSavingGeneratedPackage] =
    useState(false);
  const selectedLipSample =
    lipSampleSettings[selectedLipSampleName] ?? DEFAULT_LIP_SAMPLE;
  const selectedLipRuntimeCandidate =
    LIP_RUNTIME_CANDIDATE_OPTIONS.find(
      candidate => candidate.candidateId === selectedLipRuntimeCandidateId,
    ) ?? DEFAULT_LIP_RUNTIME_CANDIDATE;

  const resetGeneratedApplyFlow = useCallback((reason: string) => {
    setGeneratedApplyState(createGeneratedApplyState('idle'));
    setPendingGeneratedMaskId(null);
    setPendingGeneratedPackage(null);
    setAppliedGeneratedPackage(null);
    setPendingGeneratedControlCheck(null);
    console.log('[E7] generated_apply_state_reset', reason);
  }, []);

  useEffect(() => {
    console.log(
      '[E7] unity_screen_mounted',
      `entry=${entryCount}`,
      `mounted=${mountedAt}`,
    );

    return () => {
      console.log('[E7] unity_screen_unmounted', `entry=${entryCount}`);
    };
  }, [entryCount, mountedAt]);

  const handleClose = useCallback(() => {
    console.log('[E7] unity_screen_close_pressed', `entry=${entryCount}`);
    onClose();
  }, [entryCount, onClose]);

  const buildRecipeBatchJson = useCallback(
    (
      recipes: Record<RecipeRegion, RegionRecipe>,
      enabledRegions: ActiveRegionMap,
      focusRegion: RecipeRegion,
      rendererMode: RendererMode,
      sentAtMs: number,
      lipSample: LipSample,
      lipRuntimeCandidate: LipRuntimeCandidate,
      userAdjustment: LipUserAdjustment,
    ) => {
      const lookId = lipSample.name;
      const recipePrefix = 'lip-sample-pack-v0';
      const recipeBatchId = `${recipePrefix}-batch-${Math.round(sentAtMs)}`;
      const activeRegionSummary = formatActiveRegionSummary(enabledRegions);
      const enabledLayerCount = countActiveRegions(enabledRegions);
      const layers = RECIPE_REGION_OPTIONS.map(region => {
        const recipe = recipes[region];
        const isLipSampleLayer = region === 'lip';
        const maskTextureId = isLipSampleLayer
          ? lipRuntimeCandidate.maskTextureId
          : DEFAULT_MASK_TEXTURE_ID_BY_REGION[region];
        const maskThreshold = isLipSampleLayer
          ? lipRuntimeCandidate.maskThreshold
          : 0.04;
        const textureSample = isLipSampleLayer
          ? DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip
          : recipe.textureSample;
        const color = isLipSampleLayer ? lipSample.color : recipe.color.color;
        const opacity = isLipSampleLayer ? lipSample.opacity : recipe.opacity;
        const coverage = isLipSampleLayer ? lipSample.coverage : 0;
        const feather = isLipSampleLayer
          ? lipRuntimeCandidate.feather
          : recipe.textureSample.feather;
        const blendMode = isLipSampleLayer
          ? lipSample.blendMode
          : recipe.textureSample.blendMode;
        const finish = isLipSampleLayer
          ? lipSample.finish
          : 'validation-placeholder';
        const textureAmount = isLipSampleLayer
          ? lipSample.textureAmount
          : recipe.textureSample.intensity;
        const intensity = isLipSampleLayer ? 1 : textureAmount;
        const roughness = isLipSampleLayer ? lipSample.roughness : 0;
        const specular = isLipSampleLayer ? lipSample.specular : 0;
        const specularPower = isLipSampleLayer ? lipSample.specularPower : 0;
        const glossBoost = isLipSampleLayer ? lipSample.glossBoost : 0;
        const layerRecipeId = `${recipePrefix}-${region}-${
          textureSample.name
        }-${Math.round(sentAtMs)}`;

        return {
          id: `${region}-${textureSample.name}`,
          candidateId: isLipSampleLayer
            ? lipRuntimeCandidate.candidateId
            : DEFAULT_MASK_TEXTURE_ID_BY_REGION[region],
          recipeId: layerRecipeId,
          recipeBatchId,
          lookId,
          sentAtMs,
          rendererMode,
          activeRegions: activeRegionSummary,
          layerCount: RECIPE_REGION_OPTIONS.length,
          enabledLayerCount,
          region,
          layer: region,
          color,
          opacity,
          texture: textureSample.name,
          sample: textureSample.name,
          textureMode: textureSample.textureMode,
          intensity,
          feather,
          blendMode,
          enabled: enabledRegions[region],
          coverage,
          finish,
          textureAmount,
          roughness,
          specular,
          specularPower,
          glossBoost,
          shimmer: 0,
          shimmerColor: '#FFFFFF',
          skinAdaptive: isLipSampleLayer,
          preserveDetail: true,
          materialId: `${textureSample.name}-${finish}-sample-material`,
          shaderMode: 'smooth-lip-finish-v0',
          passCount: 1,
          maskTextureId,
          maskThreshold,
          maskFeatherUvNormalized: feather,
          cornerReach: isLipSampleLayer ? userAdjustment.cornerReach : 0,
          upperLipTightness: isLipSampleLayer
            ? userAdjustment.upperLipTightness
            : 0,
          lowerLipTightness: isLipSampleLayer
            ? userAdjustment.lowerLipTightness
            : 0,
          verticalOffset: isLipSampleLayer ? userAdjustment.verticalOffset : 0,
          cameraBackdropAvailable: false,
          lightEstimateAvailable: false,
        };
      });

      return JSON.stringify({
        version: 2,
        recipeBatchId,
        recipeId: recipeBatchId,
        lookId,
        candidateId: lipRuntimeCandidate.candidateId,
        sentAtMs,
        rendererMode,
        region: focusRegion,
        activeRegions: activeRegionSummary,
        layerCount: layers.length,
        enabledLayerCount,
        texture: DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip.name,
        sample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip.name,
        textureMode: DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip.textureMode,
        coverage: lipSample.coverage,
        finish: lipSample.finish,
        textureAmount: lipSample.textureAmount,
        roughness: lipSample.roughness,
        specular: lipSample.specular,
        specularPower: lipSample.specularPower,
        glossBoost: lipSample.glossBoost,
        shimmer: 0,
        shimmerColor: '#FFFFFF',
        skinAdaptive: true,
        preserveDetail: true,
        materialId: `${DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip.name}-${lipSample.finish}-sample-material`,
        shaderMode: 'smooth-lip-finish-v0',
        passCount: 1,
        maskTextureId: lipRuntimeCandidate.maskTextureId,
        maskThreshold: lipRuntimeCandidate.maskThreshold,
        maskFeatherUvNormalized: lipRuntimeCandidate.feather,
        cornerReach: userAdjustment.cornerReach,
        upperLipTightness: userAdjustment.upperLipTightness,
        lowerLipTightness: userAdjustment.lowerLipTightness,
        verticalOffset: userAdjustment.verticalOffset,
        cameraBackdropAvailable: false,
        lightEstimateAvailable: false,
        layers,
      });
    },
    [],
  );

  const postRecipeBatch = useCallback(
    (
      recipes = regionRecipes,
      enabledRegions = activeRegions,
      focusRegion = focusedRegion,
      rendererMode = selectedRendererMode,
      lipSample = lipSampleSettings[selectedLipSampleName] ?? DEFAULT_LIP_SAMPLE,
      lipRuntimeCandidate = selectedLipRuntimeCandidate,
      userAdjustment = lipUserAdjustment,
    ) => {
      const sentAtMs = Date.now();
      const recipeJson = buildRecipeBatchJson(
        recipes,
        enabledRegions,
        focusRegion,
        rendererMode,
        sentAtMs,
        lipSample,
        lipRuntimeCandidate,
        userAdjustment,
      );
      const activeRegionSummary = formatActiveRegionSummary(enabledRegions);
      console.log(
        '[E7] rn_texture_recipe_batch_post',
        `rendererMode=${rendererMode}`,
        `lookId=${lipSample.name}`,
        `candidateId=${lipRuntimeCandidate.candidateId}`,
        `maskTextureId=${lipRuntimeCandidate.maskTextureId}`,
        `maskThreshold=${lipRuntimeCandidate.maskThreshold.toFixed(2)}`,
        `cornerReach=${userAdjustment.cornerReach.toFixed(2)}`,
        `upperLipTightness=${userAdjustment.upperLipTightness.toFixed(2)}`,
        `lowerLipTightness=${userAdjustment.lowerLipTightness.toFixed(2)}`,
        `verticalOffset=${userAdjustment.verticalOffset.toFixed(2)}`,
        `finish=${lipSample.finish}`,
        `textureAmount=${lipSample.textureAmount.toFixed(2)}`,
        `glossBoost=${lipSample.glossBoost.toFixed(2)}`,
        `coverage=${lipSample.coverage.toFixed(2)}`,
        `feather=${lipSample.feather.toFixed(2)}`,
        `activeRegions=${activeRegionSummary}`,
        `enabledLayerCount=${countActiveRegions(enabledRegions)}`,
        `focusRegion=${focusRegion}`,
        `payloadBytes=${recipeJson.length}`,
        `sentAtMs=${sentAtMs}`,
      );
      unityRef.current?.postMessage('RNBridge', 'ApplyRecipeJson', recipeJson);
    },
    [
      activeRegions,
      buildRecipeBatchJson,
      focusedRegion,
      lipSampleSettings,
      regionRecipes,
      selectedLipSampleName,
      selectedRendererMode,
      selectedLipRuntimeCandidate,
      lipUserAdjustment,
    ],
  );

  const postGeneratedLipMask = useCallback(() => {
    const sentAtMs = Date.now();
    const generatedMaskId =
      `e7-generated-lip-${lipGenerateProvider}-${lipGenerateExpressionMode}` +
      `-${Math.round(sentAtMs)}`;
    const generatedPackage: LipGeneratePackage = {
      schemaVersion: 'e7-personalized-lip-generate-package-v0',
      generatedMaskId,
      captureSetId,
      provider: lipGenerateProvider,
      providerResults: {
        [lipGenerateProvider]: {
          status: 'partial',
          provider: lipGenerateProvider,
          capturePairId: 'rn-buildless-synthetic',
          captureShotKind: 'synthetic',
          frameWidth: 8,
          frameHeight: 8,
          outerPointCount: 0,
          innerPointCount: 0,
          generationMethod: 'rn_buildless_synthetic',
          warnings: ['rn_buildless_synthetic_mask_until_ios_provider'],
        },
      },
      expressionMode: lipGenerateExpressionMode,
      blendshapeAssist: {
        mode: lipGenerateExpressionMode,
        enabled: lipGenerateExpressionMode === 'blendshapeAssist',
        source: 'arface-blendshapes',
        materialFeatherUvNormalized:
          lipGenerateExpressionMode === 'blendshapeAssist' ? 0.09 : 0.07,
        warning: 'rn_buildless_synthetic_until_ios_provider',
      },
      adjustment: lipUserAdjustment,
      sourceFrameMetadata: {
        orientation: 'ios-current-frame-pending-native-provider',
        isMirrored: false,
      },
      sourceFaceState: {
        blendshapeAvailable: false,
        warning: 'rn_buildless_synthetic_until_ios_provider',
      },
      lipBoundary2D: {
        coordinateSpace: 'frame_image_pixel_top_left',
        outerPoints: [],
        innerPoints: [],
        source: lipGenerateProvider,
      },
      uvMaskTexture: 'rn-buildless-synthetic-8x8-raw-rgba',
      uvCoverageMetadata: {
        uvResolution: 8,
        roundTripKind: 'same_frame_self_reconstruction',
      },
      roundTripPreview: 'rn-buildless-synthetic-preview-unavailable',
      runtimeApplyPayload: {
        schemaVersion: 'e7-generated-lip-mask-runtime-payload-v0',
        generatedMaskId,
        captureSetId,
        provider: lipGenerateProvider,
        expressionMode: lipGenerateExpressionMode,
        adjustment: lipUserAdjustment,
        maskTextureId: generatedMaskId,
        maskTextureEncoding: 'raw_rgba_base64',
        maskRawRgbaBase64: GENERATED_LIP_MASK_SMOKE_RAW_RGBA_BASE64,
        maskTextureWidth: 8,
        maskTextureHeight: 8,
        maskThreshold: 0.5,
        maskFeatherUvNormalized:
          lipGenerateExpressionMode === 'blendshapeAssist' ? 0.09 : 0.07,
        localOnly: true,
        offDeviceUpload: false,
        longTermRawFrameStored: false,
        runtimeReady: false,
      },
      qualityWarnings: [
        'rn_buildless_synthetic_mask_until_ios_provider',
        'runtimeReady_false_until_real_iPhone_generate_evidence',
      ],
      createdAt: new Date(sentAtMs).toISOString(),
      privacyFlags: {
        localOnly: true,
        offDeviceUpload: false,
        longTermRawFrameStored: false,
      },
    };
    const unityMessageJson = JSON.stringify(
      buildUnityMessageFromPackage(generatedPackage),
    );

    console.log(
      '[E7] rn_generated_lip_mask_post',
      `provider=${lipGenerateProvider}`,
      `expressionMode=${lipGenerateExpressionMode}`,
      `generatedMaskId=${generatedMaskId}`,
      `payloadBytes=${unityMessageJson.length}`,
      'runtimeReady=false',
      'source=rn_buildless_synthetic',
    );

    setActiveRegions(regions => ({ ...regions, lip: true }));
    setLastGeneratedLipMaskSummary(
      `${lipGenerateProvider}/${lipGenerateExpressionMode} ` +
        `payload=${unityMessageJson.length}B synthetic`,
    );
    unityRef.current?.postMessage(
      'RNBridge',
      'ApplyGeneratedLipMaskJson',
      unityMessageJson,
    );
  }, [
    captureSetId,
    lipGenerateExpressionMode,
    lipGenerateProvider,
    lipUserAdjustment,
  ]);

  const postFullFaceRegionPackage = useCallback(() => {
    const sentAtMs = Date.now();
    const recipeBatchId = `e7-full-face-region-batch-${Math.round(sentAtMs)}`;
    const enabledLayerCount = E7_FULL_FACE_REGION_RUNTIME_LAYERS.length;
    const layers = E7_FULL_FACE_REGION_RUNTIME_LAYERS.map(layer => ({
      id: `${layer.region}-${layer.candidateId}`,
      recipeId: `${recipeBatchId}-${layer.region}`,
      recipeBatchId,
      lookId: 'e7_full_face_region_generate_v0',
      sentAtMs,
      activeRegions: 'lip,blush,brow,eyeliner',
      layerCount: E7_FULL_FACE_REGION_RUNTIME_LAYERS.length,
      enabledLayerCount,
      region: layer.region,
      layer: layer.layer,
      color: layer.color,
      opacity: layer.opacity,
      texture: layer.texture,
      sample: layer.texture,
      textureMode: 'sample',
      intensity: layer.intensity,
      feather: layer.maskFeatherUvNormalized,
      blendMode: layer.blendMode,
      rendererMode: selectedRendererMode,
      enabled: true,
      coverage: layer.coverage,
      finish: 'validation-placeholder',
      textureAmount: 0,
      roughness: 0,
      specular: 0,
      specularPower: 0,
      glossBoost: 0,
      shimmer: 0,
      shimmerColor: '#FFFFFF',
      skinAdaptive: layer.skinAdaptive,
      preserveDetail: true,
      materialId: `e7-full-face-${layer.region}-material-v0`,
      shaderMode: 'smooth-lip-finish-v0',
      passCount: 1,
      candidateId: layer.candidateId,
      maskTextureId: layer.maskTextureId,
      maskThreshold: layer.maskThreshold,
      maskFeatherUvNormalized: layer.maskFeatherUvNormalized,
      cornerReach: layer.region === 'lip' ? lipUserAdjustment.cornerReach : 0,
      upperLipTightness:
        layer.region === 'lip' ? lipUserAdjustment.upperLipTightness : 0,
      lowerLipTightness:
        layer.region === 'lip' ? lipUserAdjustment.lowerLipTightness : 0,
      verticalOffset: layer.region === 'lip' ? lipUserAdjustment.verticalOffset : 0,
      cameraBackdropAvailable: false,
      lightEstimateAvailable: false,
    }));
    const recipeJson = JSON.stringify({
      version: 2,
      recipeBatchId,
      recipeId: recipeBatchId,
      lookId: 'e7_full_face_region_generate_v0',
      sentAtMs,
      rendererMode: selectedRendererMode,
      region: 'lip',
      activeRegions: 'lip,blush,brow,eyeliner',
      layerCount: layers.length,
      enabledLayerCount,
      texture: 'matte_lip',
      sample: 'matte_lip',
      textureMode: 'sample',
      coverage: 0.72,
      finish: 'validation-placeholder',
      textureAmount: 0,
      roughness: 0,
      specular: 0,
      specularPower: 0,
      glossBoost: 0,
      shimmer: 0,
      shimmerColor: '#FFFFFF',
      skinAdaptive: true,
      preserveDetail: true,
      materialId: 'e7-full-face-region-batch-material-v0',
      shaderMode: 'smooth-lip-finish-v0',
      passCount: 1,
      cameraBackdropAvailable: false,
      lightEstimateAvailable: false,
      layers,
    });

    console.log(
      '[E7] rn_full_face_region_package_post',
      `recipeBatchId=${recipeBatchId}`,
      `layerCount=${layers.length}`,
      `activeRegions=lip,blush,brow,eyeliner`,
      `payloadBytes=${recipeJson.length}`,
      'runtimeReady=false',
      'source=e7_full_face_region_generate_pre_xcode',
    );

    setFocusedRegion('lip');
    setActiveRegions({ lip: true, cheek: true, eye: true });
    setLastGeneratedLipMaskSummary(
      `full-face package payload=${recipeJson.length}B pre-Xcode`,
    );
    unityRef.current?.postMessage('RNBridge', 'ApplyRecipeJson', recipeJson);
  }, [lipUserAdjustment, selectedRendererMode]);

  const postRecipeAck = useCallback(
    (payload: UnityEventPayload, receivedAtMs: number) => {
      const ackJson = JSON.stringify({
        type: 'recipe_ack',
        runId: payload.runId ?? 'smooth-mask',
        phase: payload.phase ?? 'smooth_mask',
        rendererMode: payload.rendererMode ?? DEFAULT_RENDERER_MODE,
        lookId: payload.lookId ?? 'smooth_region_mask',
        recipeId: payload.recipeId ?? 'none',
        recipeBatchId: payload.recipeBatchId ?? payload.recipeId ?? 'none',
        activeRegions:
          payload.activeRegionSummary ?? payload.activeRegions ?? 'none',
        layerCount: readNumber(payload.layerCount) ?? 0,
        enabledLayerCount: readNumber(payload.enabledLayerCount) ?? 0,
        payloadBytes: readNumber(payload.payloadBytes) ?? 0,
        region: payload.region ?? payload.appliedRegion ?? 'none',
        texture: payload.texture ?? payload.sample ?? 'none',
        finish: payload.finish ?? 'n/a',
        textureAmount: readNumber(payload.textureAmount) ?? 0,
        glossBoost: readNumber(payload.glossBoost) ?? 0,
        coverage: readNumber(payload.coverage) ?? 0,
        feather: readNumber(payload.feather) ?? 0,
        sentAtMs: readNumber(payload.sentAtMs) ?? 0,
        appliedAtMs: readNumber(payload.appliedAtMs) ?? 0,
        appliedFrame: readNumber(payload.appliedFrame) ?? 0,
        receivedAtMs,
        visualLatencyConfirmedByRecording:
          payload.visualLatencyConfirmedByRecording ?? false,
        visualLatencyObservation:
          payload.visualLatencyObservation ?? 'pending_recording_review',
      });

      unityRef.current?.postMessage('RNBridge', 'LogRecipeAck', ackJson);
    },
    [],
  );

  const postRegionOverlayVisibility = useCallback(
    (visible: boolean, reason: string) => {
      const payloadJson = JSON.stringify({
        visible,
        validationViewMode,
        reason,
        entryCount,
      });

      console.log(
        '[E7] rn_region_overlay_visibility_post',
        `visible=${visible}`,
        'faceDebugSurfaceSuppressed=true',
        `validationViewMode=${validationViewMode}`,
        `reason=${reason}`,
      );

      unityRef.current?.postMessage(
        'RNBridge',
        'SetE7RegionOverlayVisibleJson',
        payloadJson,
      );
    },
    [entryCount, validationViewMode],
  );

  const postWizardCaptureShot = useCallback(
    (shotKind: E7CaptureShotKind) => {
      if (pendingCapturePairId) {
        setWizardNotice(`현재 ${pendingCapturePairId} 촬영이 끝나길 기다리는 중입니다.`);
        return;
      }

      const requestedAtMs = Date.now();
      const capturePairId = buildReferenceCapturePairId(
        captureRequestSequence,
        requestedAtMs,
      );
      const requestJson = JSON.stringify({
        capturePairId,
        captureSetId,
        captureShotKind: shotKind,
        requestedAtMs,
        requestedBy: 'rn-personalized-generate-wizard',
        purpose: `e7_personalized_generate_capture_${shotKind}`,
      });

      setCaptureShots(currentShots => ({
        ...currentShots,
        [shotKind]: {
          ...currentShots[shotKind],
          status: 'capturing',
          capturePairId,
          detail: 'capturing_current_frame',
        },
      }));
      setPendingCapturePairId(capturePairId);
      setPendingCaptureShotKind(shotKind);
      setCaptureRequestSequence(sequence => sequence + 1);
      setValidationViewMode('clean');
      setWizardNotice(`${shotKind} 촬영 요청을 보냈습니다.`);
      postRegionOverlayVisibility(false, `wizard_capture_${shotKind}`);

      unityRef.current?.postMessage(
        'RNBridge',
        'CaptureE7ReferenceFrameJson',
        requestJson,
      );
    },
    [
      captureRequestSequence,
      captureSetId,
      pendingCapturePairId,
      postRegionOverlayVisibility,
    ],
  );

  const invokeNativeBoundaryProvider = useCallback(
    async (
      provider: GeneratedLipMaskProvider,
      shotKind: E7CaptureShotKind = 'neutral',
    ): Promise<E7NativeBoundaryResult> => {
      const captureShot = captureShots[shotKind];
      if (!isCapturedShot(captureShot)) {
        return {
          status: 'blocked',
          provider,
          captureSetId,
          capturePairId: captureShot.capturePairId ?? `${shotKind}_missing`,
          captureShotKind: shotKind,
          framePath: '',
          arFaceExportPath: '',
          frameWidth: 0,
          frameHeight: 0,
          warnings: [`${shotKind}_capture_required_before_native_extract`],
          blockedReason: `${shotKind}_capture_missing`,
        };
      }

      const captureDirectory = captureShot.relativeDirectory ?? '';
      const requestJson = JSON.stringify({
        provider,
        captureSetId,
        capturePairId: captureShot.capturePairId,
        captureShotKind: shotKind,
        framePath: `${captureDirectory}/frame.png`,
        arFaceExportPath: `${captureDirectory}/arface_export.json`,
        orientation: 'up',
        adjustment: lipUserAdjustment,
        privacy: {
          localOnly: true,
          offDeviceUpload: false,
          longTermRawFrameStored: false,
        },
      });

      if (!E7_NATIVE_BOUNDARY_MODULE?.extractLipBoundary) {
        return {
          status: 'blocked',
          provider,
          captureSetId,
          capturePairId: captureShot.capturePairId ?? `${shotKind}_missing`,
          captureShotKind: shotKind,
          framePath: `${captureDirectory}/frame.png`,
          arFaceExportPath: `${captureDirectory}/arface_export.json`,
          frameWidth: 0,
          frameHeight: 0,
          warnings: ['native_boundary_module_unavailable_in_js_test_runtime'],
          blockedReason: 'native_boundary_module_unavailable',
        };
      }

      const responseJson =
        await E7_NATIVE_BOUNDARY_MODULE.extractLipBoundary(requestJson);
      return JSON.parse(responseJson) as E7NativeBoundaryResult;
    },
    [captureSetId, captureShots, lipUserAdjustment],
  );

  const renderGeneratedCandidatePreviews = useCallback(
    async (
      candidates: E7GeneratedCandidate[],
    ): Promise<E7GeneratedCandidateWithPreview[]> =>
      Promise.all(
        candidates.map(async candidate => {
          if (!candidate.package) {
            return {
              ...candidate,
              previewStatus: 'blocked',
              previewError:
                candidate.blockedReason ?? 'generated_package_missing',
            };
          }

          if (!E7_NATIVE_BOUNDARY_MODULE?.renderLipMaskPreview) {
            return {
              ...candidate,
              previewStatus: 'blocked',
              previewError: 'native_preview_module_unavailable',
            };
          }

          try {
            const responseJson =
              await E7_NATIVE_BOUNDARY_MODULE.renderLipMaskPreview(
                JSON.stringify(candidate.package),
              );
            const result = JSON.parse(responseJson) as E7GeneratedPreviewResult;
            if (result.status === 'ready' && result.previewUri) {
              return {
                ...candidate,
                previewUri: result.previewUri,
                previewStatus: 'ready',
              };
            }

            return {
              ...candidate,
              previewStatus: 'blocked',
              previewError:
                result.blockedReason ?? 'native_preview_uri_missing',
            };
          } catch (error) {
            return {
              ...candidate,
              previewStatus: 'blocked',
              previewError:
                error instanceof Error
                  ? error.message
                  : 'native_preview_render_failed',
            };
          }
        }),
      ),
    [],
  );

  const generateWizardCandidates = useCallback(async (options?: {
    stayOnStep?: boolean;
    reason?: 'manual' | 'auto-adjustment';
  }) => {
    if (isGeneratingCandidates) {
      return;
    }
    setIsGeneratingCandidates(true);
    setWizardNotice(
      `현재 촬영 frame에서 ${formatProviderLabel(
        lipGenerateProvider,
      )} 후보를 생성하는 중입니다.`,
    );

    try {
      const capturedShotKinds = E7_CAPTURE_SHOT_OPTIONS.filter(option =>
        isCapturedShot(captureShots[option.kind]),
      ).map(option => option.kind);
      const results = await Promise.all(
        capturedShotKinds.map(shotKind =>
          invokeNativeBoundaryProvider(lipGenerateProvider, shotKind),
        ),
      );
      const neutralResult =
        results.find(result => result.captureShotKind === 'neutral') ??
        results[0] ??
        (await invokeNativeBoundaryProvider(lipGenerateProvider, 'neutral'));
      const resultMap = [neutralResult].reduce((map, result) => {
        map[result.provider] = result;
        return map;
      }, {} as Partial<Record<GeneratedLipMaskProvider, E7NativeBoundaryResult>>);
      const candidates = LIP_GENERATE_EXPRESSION_OPTIONS.map(
        expressionOption =>
          buildGeneratedLipPackage({
            nativeResult: neutralResult,
            providerResults: results.length ? results : [neutralResult],
            expressionMode: expressionOption.name,
            adjustment: lipUserAdjustment,
          }),
      );
      const candidatesWithPreviews =
        await renderGeneratedCandidatePreviews(candidates);
      setCaptureShots(currentShots => {
        let nextShots = currentShots;
        results.forEach(result => {
          if (!result.framePreviewUri) {
            return;
          }
          const shotKind = result.captureShotKind;
          nextShots = {
            ...nextShots,
            [shotKind]: {
              ...nextShots[shotKind],
              framePreviewUri: result.framePreviewUri,
            },
          };
        });
        return nextShots;
      });
      const firstUsable =
        candidatesWithPreviews.find(
          candidate => candidate.package && candidate.previewUri,
        )?.candidateKey ??
        candidatesWithPreviews.find(candidate => candidate.package)
          ?.candidateKey ??
        candidatesWithPreviews[0]?.candidateKey ??
        'vision/uvOnly';
      const keepSelectedCandidate =
        candidatesWithPreviews.some(
          candidate =>
            candidate.candidateKey === selectedGeneratedCandidateKey &&
            candidate.package,
        ) && options?.stayOnStep;

      setNativeProviderResults(resultMap);
      setNativeProviderShotResults(currentResults => ({
        ...currentResults,
        [lipGenerateProvider]: results.length ? results : [neutralResult],
      }));
      setGeneratedCandidates(candidatesWithPreviews);
      setSelectedGeneratedCandidateKey(
        keepSelectedCandidate ? selectedGeneratedCandidateKey : firstUsable,
      );
      setGeneratedCandidatesStale(false);
      setSavedGeneratedPackage(null);
      resetGeneratedApplyFlow('generate_candidates');
      if (!options?.stayOnStep) {
        setWizardStep('blend');
      }
      setWizardNotice(
        candidatesWithPreviews.some(candidate => candidate.package)
          ? options?.reason === 'auto-adjustment'
            ? '조정값이 현재 후보에 자동 반영되었습니다.'
            : `${formatProviderLabel(
                lipGenerateProvider,
              )} 후보 생성 완료. 블렌딩 선택 후 조정하세요.`
          : '후보 생성이 막혔습니다. 다시 생성하거나 다른 방식을 선택하세요.',
      );
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'unknown_native_generate_error';
      setWizardNotice(`후보 생성 실패: ${message}`);
    } finally {
      setIsGeneratingCandidates(false);
    }
  }, [
    captureShots,
    invokeNativeBoundaryProvider,
    isGeneratingCandidates,
    lipGenerateProvider,
    lipUserAdjustment,
    renderGeneratedCandidatePreviews,
    resetGeneratedApplyFlow,
    selectedGeneratedCandidateKey,
  ]);

  const saveSelectedGeneratedPackage = useCallback(async () => {
    if (isSavingGeneratedPackage || generatedCandidatesStale) {
      setWizardNotice('조정값은 현재 후보에 즉시 반영되어야 합니다. 후보를 다시 확인하세요.');
      return;
    }
    const selectedCandidate = generatedCandidates.find(
      candidate => candidate.candidateKey === selectedGeneratedCandidateKey,
    );
    if (!selectedCandidate?.package) {
      setWizardNotice('저장할 수 있는 후보가 없습니다.');
      return;
    }

    setIsSavingGeneratedPackage(true);
    setGeneratedApplyState(
      createGeneratedApplyState('saving', {
        generatedMaskId: selectedCandidate.package.generatedMaskId,
        startedAtMs: Date.now(),
        blockedReason: 'saving_local_generated_package',
      }),
    );
    setPendingGeneratedMaskId(selectedCandidate.package.generatedMaskId);
    setPendingGeneratedPackage(selectedCandidate.package);
    setAppliedGeneratedPackage(null);
    try {
      if (!E7_NATIVE_BOUNDARY_MODULE?.saveGeneratedPackage) {
        throw new Error('native_save_module_unavailable');
      }

      const packageJson = JSON.stringify(selectedCandidate.package);
      const recordJson =
        await E7_NATIVE_BOUNDARY_MODULE.saveGeneratedPackage(packageJson);
      const record = JSON.parse(recordJson) as E7SavedPackageRecord;
      const unityMessageJson = JSON.stringify(
        buildGeneratedMaskUnityMessage(
          selectedCandidate.package,
          generatedValidationControls,
          { includeTexture: true },
        ),
      );

      setSavedGeneratedPackage(record);
      setLastGeneratedLipMaskSummary(
        `${selectedCandidate.provider}/${selectedCandidate.expressionMode} saved`,
      );
      setActiveRegions(regions => ({ ...regions, lip: true }));
      setGeneratedApplyState(
        createGeneratedApplyState('posting', {
          generatedMaskId: selectedCandidate.package.generatedMaskId,
          startedAtMs: Date.now(),
          blockedReason: 'posting_apply_payload_to_unity',
        }),
      );
      unityRef.current?.postMessage(
        'RNBridge',
        'ApplyGeneratedLipMaskJson',
        unityMessageJson,
      );
      setGeneratedApplyState(
        createGeneratedApplyState('waitingAck', {
          generatedMaskId: selectedCandidate.package.generatedMaskId,
          startedAtMs: Date.now(),
          blockedReason: 'waiting_for_generated_lip_mask_applied_ack',
        }),
      );
      setWizardStep('apply');
      setWizardNotice('저장 완료. AR 화면에서 적용 확인을 기다립니다.');
    } catch (error) {
      const message =
        error instanceof Error ? error.message : 'unknown_save_error';
      setPendingGeneratedMaskId(null);
      setPendingGeneratedPackage(null);
      setGeneratedApplyState(
        createGeneratedApplyState('blocked', {
          generatedMaskId: selectedCandidate.package.generatedMaskId,
          blockedReason: 'save_or_post_failed',
          error: message,
        }),
      );
      setWizardNotice(
        message === 'native_save_module_unavailable'
          ? '기기 저장 기능을 확인하지 못했습니다. 앱을 다시 빌드한 뒤 확인해 주세요.'
          : '마스크 저장에 실패했습니다. 다시 시도해 주세요.',
      );
    } finally {
      setIsSavingGeneratedPackage(false);
    }
  }, [
    generatedCandidates,
    generatedCandidatesStale,
    generatedValidationControls,
    isSavingGeneratedPackage,
    selectedGeneratedCandidateKey,
  ]);

  const updateGeneratedMaskValidationControls = useCallback(
    (patch: Partial<GeneratedMaskValidationControls>) => {
      const nextControls: GeneratedMaskValidationControls = {
        ...generatedValidationControls,
        ...patch,
        opacity: Number(
          Math.max(
            0,
            Math.min(1, patch.opacity ?? generatedValidationControls.opacity),
          ).toFixed(2),
        ),
      };
      setGeneratedValidationControls(nextControls);

      const packageForUpdate =
        appliedGeneratedPackage ?? pendingGeneratedPackage;
      if (!packageForUpdate) {
        setWizardNotice('적용된 generated mask가 없어 검증 컨트롤을 보낼 수 없습니다.');
        return;
      }

      const unityMessageJson = JSON.stringify(
        buildGeneratedMaskUnityMessage(packageForUpdate, nextControls, {
          includeTexture: false,
        }),
      );
      unityRef.current?.postMessage(
        'RNBridge',
        'ApplyGeneratedLipMaskJson',
        unityMessageJson,
      );
      setPendingGeneratedControlCheck({
        generatedMaskId: packageForUpdate.generatedMaskId,
        controls: nextControls,
        requestedAtMs: Date.now(),
      });
      setWizardNotice(
        `AR 검증 변경을 확인하는 중입니다: ${
          nextControls.maskVisible ? 'ON' : 'OFF'
        } / ${nextControls.strongMode ? '진하게' : '기본'} / ${
          nextControls.colorHex
        } / 농도 ${nextControls.opacity.toFixed(2)}`,
      );
    },
    [
      appliedGeneratedPackage,
      generatedValidationControls,
      pendingGeneratedPackage,
    ],
  );

  const handleUnityMessage = useCallback(
    (event: UnityMessageEvent) => {
      const rawMessage = String(event.nativeEvent.message ?? '');
      const receivedAt = new Date().toLocaleTimeString();
      const receivedAtMs = Date.now();
      let record: UnityEventRecord;

      try {
        const parsedMessage = JSON.parse(rawMessage);

        if (
          parsedMessage === null ||
          typeof parsedMessage !== 'object' ||
          Array.isArray(parsedMessage)
        ) {
          throw new Error('Unity message JSON is not an object.');
        }

        const parsed = parsedMessage as UnityEventPayload;
        parsed.receivedAtMs = receivedAtMs;
        record = {
          id: Date.now(),
          receivedAt,
          receivedAtMs,
          rawMessage,
          parsed,
          displayText: formatUnityEvent(parsed),
        };

        if (parsed.type === 'recipe_applied') {
          if (validationViewMode === 'full') {
            logE7RecipeLatency(parsed, receivedAtMs);
          }
          postRecipeAck(parsed, receivedAtMs);
        }

        if (parsed.type === 'generated_lip_mask_applied') {
          const generatedMaskId =
            typeof parsed.generatedMaskId === 'string'
              ? parsed.generatedMaskId
              : '';
          const status = String(parsed.status ?? 'unknown');
          const isMatchingPendingMask = pendingGeneratedMaskId
            ? generatedMaskId === pendingGeneratedMaskId
            : Boolean(generatedMaskId);
          const isRuntimeApplyStatus =
            status === 'partial' || status === 'ready';
          const isApplied =
            isMatchingPendingMask &&
            isRuntimeApplyStatus &&
            parsed.applied === true &&
            parsed.uvAvailable === true &&
            (readNumber(parsed.maskTriangles) ?? 0) > 0;
          const blockedReason = !isMatchingPendingMask
            ? 'generatedMaskId_mismatch'
            : String(
                parsed.blockedReason ??
                  parsed.error ??
                  parsed.status ??
                  'unity_apply_unknown',
              );

          if (isApplied) {
            const didConfirmPendingControls =
              Boolean(pendingGeneratedControlCheck) &&
              generatedMaskId === pendingGeneratedControlCheck?.generatedMaskId &&
              doesGeneratedControlAckMatch(
                parsed,
                pendingGeneratedControlCheck.controls,
              );
            setGeneratedApplyState(
              createGeneratedApplyState('applied', {
                generatedMaskId,
                ack: parsed,
                blockedReason: 'ack_applied_uv_mask_triangles_ready',
              }),
            );
            setAppliedGeneratedPackage(
              currentPackage =>
                currentPackage ??
                pendingGeneratedPackage ??
                generatedCandidates.find(
                  candidate =>
                    candidate.package?.generatedMaskId === generatedMaskId,
                )?.package ??
                null,
            );
            setPendingGeneratedMaskId(null);
            if (didConfirmPendingControls) {
              setPendingGeneratedControlCheck(null);
            }
            setWizardNotice(
              didConfirmPendingControls
                ? 'AR 검증 변경이 반영되었습니다. 화면에서 마스크 차이를 확인하세요.'
                : 'AR 화면입니다. 마스크가 보이는지 아래 컨트롤로 확인하세요.',
            );
          } else {
            setGeneratedApplyState(
              createGeneratedApplyState('blocked', {
                generatedMaskId,
                ack: parsed,
                blockedReason,
                error: String(parsed.error ?? ''),
              }),
            );
            setWizardNotice(formatGeneratedApplyBlockedNotice(blockedReason));
          }
        }

        if (parsed.type === 'e7_reference_capture') {
          const captureStatus = String(parsed.status ?? 'unknown');
          const capturePairId = String(parsed.capturePairId ?? '');
          const capturedShotKind = pendingCaptureShotKind;
          if (
            captureStatus === 'exported' ||
            captureStatus === 'failed' ||
            captureStatus === 'busy'
          ) {
            setPendingCapturePairId(currentPairId =>
              currentPairId === parsed.capturePairId || captureStatus === 'failed'
                ? null
                : currentPairId,
            );
            setPendingCaptureShotKind(null);
          }
          if (capturedShotKind && capturePairId) {
            setCaptureShots(currentShots => ({
              ...currentShots,
              [capturedShotKind]: {
                ...currentShots[capturedShotKind],
                status:
                  captureStatus === 'exported'
                    ? 'captured'
                    : captureStatus === 'failed' || captureStatus === 'busy'
                    ? 'blocked'
                    : currentShots[capturedShotKind].status,
                capturePairId,
                relativeDirectory:
                  typeof parsed.relativeDirectory === 'string'
                    ? parsed.relativeDirectory
                    : currentShots[capturedShotKind].relativeDirectory,
                framePreviewUri:
                  typeof parsed.framePreviewUri === 'string'
                    ? parsed.framePreviewUri
                    : currentShots[capturedShotKind].framePreviewUri,
                detail:
                  typeof parsed.detail === 'string'
                    ? parsed.detail
                    : captureStatus,
              },
            }));
            if (captureStatus === 'exported') {
              setWizardNotice(`${capturedShotKind} 촬영 완료.`);
            } else if (captureStatus === 'failed' || captureStatus === 'busy') {
              setWizardNotice(`${capturedShotKind} 촬영 실패: ${parsed.detail ?? captureStatus}`);
            }
          }
        }

        const logPrefix =
          parsed.type === 'face_feature_snapshot'
            ? '[E5] rn_face_feature_snapshot_received'
            : parsed.type === 'e7_metric_sample'
            ? '[E7] rn_metric_sample_received'
            : parsed.type === 'e7_reference_capture'
            ? '[E7] rn_reference_capture_received'
            : parsed.type === 'recipe_applied'
            ? '[E7] rn_recipe_applied_received'
            : parsed.type === 'face_lifecycle'
            ? '[E2] rn_unity_message_received'
            : '[M6] rn_unity_message_received';
        const privacySummary =
          parsed.type === 'face_feature_snapshot'
            ? `rawCameraFrameStored=${String(
                readSnapshotPrivacyFlag(parsed, 'rawCameraFrameStored'),
              )} offDeviceUpload=${String(
                readSnapshotPrivacyFlag(parsed, 'offDeviceUpload'),
              )}`
            : '';

        console.log(
          logPrefix,
          privacySummary,
          validationViewMode === 'full' ? rawMessage : record.displayText,
        );

        const knownType = getKnownUnityEventType(parsed.type);
        if (knownType) {
          setUnityEventStatus(currentStatus => ({
            ...currentStatus,
            [knownType]: record,
          }));
        }
      } catch (error) {
        const parseError =
          error instanceof Error ? error.message : 'Unknown parse error';

        record = {
          id: Date.now(),
          receivedAt,
          receivedAtMs,
          rawMessage,
          parseError,
          displayText: `parse_failed ${parseError}`,
        };

        console.log(
          '[M6] rn_unity_message_parse_failed',
          rawMessage,
          parseError,
        );
      }

      setLastUnityEvent(record);
      if (validationViewMode === 'full') {
        setUnityEventHistory(currentHistory =>
          [record, ...currentHistory].slice(0, UNITY_EVENT_HISTORY_LIMIT),
        );
      }
    },
    [
      generatedCandidates,
      pendingCaptureShotKind,
      pendingGeneratedControlCheck,
      pendingGeneratedMaskId,
      pendingGeneratedPackage,
      postRecipeAck,
      validationViewMode,
    ],
  );

  useEffect(() => {
    if (
      generatedApplyState.status !== 'waitingAck' ||
      !generatedApplyState.startedAtMs
    ) {
      return undefined;
    }

    const elapsedMs = Date.now() - generatedApplyState.startedAtMs;
    const remainingMs = Math.max(
      0,
      GENERATED_APPLY_ACK_TIMEOUT_MS - elapsedMs,
    );
    const timeout = setTimeout(() => {
      setGeneratedApplyState(currentState => {
        if (
          currentState.status !== 'waitingAck' ||
          currentState.generatedMaskId !== generatedApplyState.generatedMaskId
        ) {
          return currentState;
        }

        return createGeneratedApplyState('timeout', {
          generatedMaskId: currentState.generatedMaskId,
          startedAtMs: currentState.startedAtMs,
          elapsedMs: Date.now() - (currentState.startedAtMs ?? Date.now()),
          blockedReason: 'generated_lip_mask_applied_ack_timeout',
        });
      });
      setWizardNotice(
        'AR 적용 응답이 늦습니다. 다시 시도하거나 촬영부터 다시 진행할 수 있습니다.',
      );
    }, remainingMs);

    return () => clearTimeout(timeout);
  }, [generatedApplyState.generatedMaskId, generatedApplyState.startedAtMs, generatedApplyState.status]);

  useEffect(() => {
    if (!pendingCapturePairId || !pendingCaptureShotKind) {
      return undefined;
    }

    const timeout = setTimeout(() => {
      setCaptureShots(currentShots => {
        const currentShot = currentShots[pendingCaptureShotKind];
        if (
          currentShot.capturePairId !== pendingCapturePairId ||
          currentShot.status !== 'capturing'
        ) {
          return currentShots;
        }

        return {
          ...currentShots,
          [pendingCaptureShotKind]: {
            ...currentShot,
            status: 'blocked',
            detail: 'capture_response_timeout',
          },
        };
      });
      setPendingCapturePairId(currentPairId =>
        currentPairId === pendingCapturePairId ? null : currentPairId,
      );
      setPendingCaptureShotKind(currentShotKind =>
        currentShotKind === pendingCaptureShotKind ? null : currentShotKind,
      );
      setWizardNotice('촬영 응답이 늦습니다. 같은 컷을 다시 촬영해 주세요.');
    }, E7_CAPTURE_ACK_TIMEOUT_MS);

    return () => clearTimeout(timeout);
  }, [pendingCapturePairId, pendingCaptureShotKind]);

  useEffect(() => {
    if (!pendingGeneratedControlCheck) {
      return undefined;
    }

    const timeout = setTimeout(() => {
      setPendingGeneratedControlCheck(currentCheck => {
        if (
          currentCheck?.generatedMaskId !==
            pendingGeneratedControlCheck.generatedMaskId ||
          currentCheck.requestedAtMs !== pendingGeneratedControlCheck.requestedAtMs
        ) {
          return currentCheck;
        }
        return null;
      });
      setWizardNotice(
        'AR 검증 변경 확인이 늦습니다. 다시 눌러 확인할 수 있습니다.',
      );
    }, GENERATED_CONTROL_ACK_TIMEOUT_MS);

    return () => clearTimeout(timeout);
  }, [pendingGeneratedControlCheck]);

  useEffect(() => {
    const initialPostTimer = setTimeout(() => {
      postRecipeBatch();
    }, 1000);

    return () => clearTimeout(initialPostTimer);
  }, [postRecipeBatch]);

  const activeLipTuning =
    LIP_TUNING_FIELD_OPTIONS.find(
      fieldOption => fieldOption.name === activeLipTuningField,
    ) ?? LIP_TUNING_FIELD_OPTIONS[0];
  const activeLipAdjustment =
    LIP_ADJUSTMENT_FIELD_OPTIONS.find(
      fieldOption => fieldOption.name === activeLipAdjustmentField,
    ) ?? LIP_ADJUSTMENT_FIELD_OPTIONS[0];
  const activeRegionSummary = formatActiveRegionSummary(activeRegions);
  const latestMetric = unityEventStatus.e7_metric_sample?.parsed;
  const latestLifecycle = unityEventStatus.face_lifecycle?.parsed;
  const latestRecipe = unityEventStatus.recipe_applied?.parsed;
  const latestSnapshot = unityEventStatus.face_feature_snapshot?.parsed;
  const unityInitializedAt =
    unityEventStatus.unity_initialized?.receivedAtMs ?? 0;

  useEffect(() => {
    postRegionOverlayVisibility(true, 'validation_view_mode_changed');
  }, [
    postRegionOverlayVisibility,
    validationViewMode,
    unityInitializedAt,
  ]);

  const latestRecipeRecord = unityEventStatus.recipe_applied;
  const recipeLatencyMs = getRecipeAckLatencyMs(
    latestRecipe,
    latestRecipeRecord?.receivedAtMs,
  );
  const evidenceMetadataLines = useMemo(
    () =>
      buildEvidenceMetadataLines({
        entryCount,
        mountedAt,
        validationViewMode,
        selectedRendererMode,
        focusedRegion,
        activeRegions,
        selectedLipSample,
        selectedLipRuntimeCandidate,
        lipUserAdjustment,
        latestMetric,
        latestLifecycle,
        latestRecipe,
        latestSnapshot,
        lastUnityEvent,
      }),
    [
      entryCount,
      lastUnityEvent,
      latestLifecycle,
      latestMetric,
      latestRecipe,
      latestSnapshot,
      mountedAt,
      focusedRegion,
      selectedRendererMode,
      activeRegions,
      validationViewMode,
      selectedLipSample,
      selectedLipRuntimeCandidate,
      lipUserAdjustment,
    ],
  );
  const showFullDebug = validationViewMode === 'full';
  const capturedShotCount = countCapturedShots(captureShots);
  const faceAlignmentTracked =
    latestLifecycle?.tracked === true ||
    latestLifecycle?.faceDetected === true ||
    (readNumber(latestLifecycle?.faceCount) ?? 0) > 0 ||
    String(latestLifecycle?.trackingState ?? '').toLowerCase() === 'tracking';
  const faceAlignmentReady =
    Boolean(latestLifecycle) && faceAlignmentTracked;
  const alignmentGates: E7AlignmentGate[] = [
    {
      label: '얼굴 추적',
      value: latestLifecycle
        ? faceAlignmentTracked
          ? 'tracking'
          : 'not found'
        : '측정 대기',
      state: latestLifecycle
        ? faceAlignmentTracked
          ? 'ready'
          : 'blocked'
        : 'waiting',
    },
    {
      label: '방향',
      value: latestLifecycle ? '얼굴 인식 기준' : '측정 대기',
      state: latestLifecycle ? (faceAlignmentTracked ? 'ready' : 'blocked') : 'waiting',
    },
    {
      label: '카메라',
      value: latestMetric ? '신호 수신' : '측정 대기',
      state: latestMetric ? 'ready' : 'waiting',
    },
    {
      label: '프레임',
      value: latestMetric ? '촬영 가능' : '측정 대기',
      state: latestMetric ? 'ready' : 'waiting',
    },
  ];
  const selectedGeneratedCandidate =
    generatedCandidates.find(
      candidate => candidate.candidateKey === selectedGeneratedCandidateKey,
    ) ?? generatedCandidates[0];
  const canGenerateCandidates =
    isCapturedShot(captureShots.neutral) &&
    capturedShotCount >= E7_CAPTURE_SHOT_OPTIONS.length;
  const canSaveGeneratedPackage = Boolean(
    selectedGeneratedCandidate?.package && !generatedCandidatesStale,
  );
  const wizardStepIndex = getWizardStepIndex(wizardStep);
  const hasGeneratedMaskApplied = generatedApplyState.status === 'applied';
  const isUsingCapturedFrameReview =
    (wizardStepIndex >= getWizardStepIndex('extract') ||
      capturedShotCount >= E7_CAPTURE_SHOT_OPTIONS.length) &&
    !hasGeneratedMaskApplied;
  const capturedFramePreviewUri =
    E7_CAPTURE_SHOT_OPTIONS.map(option => captureShots[option.kind]).find(
      shot => isCapturedShot(shot) && Boolean(shot.framePreviewUri),
    )?.framePreviewUri ??
    nativeProviderResults[lipGenerateProvider]?.framePreviewUri ??
    nativeProviderShotResults[lipGenerateProvider]?.find(result =>
      Boolean(result.framePreviewUri),
    )?.framePreviewUri;
  const showCompactControls = false;

  const toggleRegion = useCallback(
    (region: RecipeRegion) => {
      const nextActiveRegions = {
        ...activeRegions,
        [region]: !activeRegions[region],
      };

      setFocusedRegion(region);
      setActiveRegions(nextActiveRegions);
      postRecipeBatch(regionRecipes, nextActiveRegions, region);
    },
    [activeRegions, postRecipeBatch, regionRecipes],
  );

  const selectLipSample = useCallback(
    (lipSample: LipSample) => {
      const nextActiveRegions = { ...DEFAULT_ACTIVE_REGIONS };
      const nextLipSample = lipSampleSettings[lipSample.name] ?? lipSample;

      setSelectedLipSampleName(lipSample.name);
      setFocusedRegion('lip');
      setActiveRegions(nextActiveRegions);
      postRecipeBatch(
        regionRecipes,
        nextActiveRegions,
        'lip',
        selectedRendererMode,
        nextLipSample,
        selectedLipRuntimeCandidate,
        lipUserAdjustment,
      );
    },
    [
      lipSampleSettings,
      postRecipeBatch,
      regionRecipes,
      selectedRendererMode,
      selectedLipRuntimeCandidate,
      lipUserAdjustment,
    ],
  );

  const updateSelectedLipSample = useCallback(
    (patch: Partial<LipSample>) => {
      const currentLipSample =
        lipSampleSettings[selectedLipSampleName] ?? DEFAULT_LIP_SAMPLE;
      const nextLipSample = {
        ...currentLipSample,
        ...patch,
      };
      const nextActiveRegions = { ...DEFAULT_ACTIVE_REGIONS };

      setLipSampleSettings(currentSettings => ({
        ...currentSettings,
        [selectedLipSampleName]: {
          ...(currentSettings[selectedLipSampleName] ?? currentLipSample),
          ...patch,
        },
      }));
      setFocusedRegion('lip');
      setActiveRegions(nextActiveRegions);
      postRecipeBatch(
        regionRecipes,
        nextActiveRegions,
        'lip',
        selectedRendererMode,
        nextLipSample,
        selectedLipRuntimeCandidate,
        lipUserAdjustment,
      );
    },
    [
      lipSampleSettings,
      postRecipeBatch,
      regionRecipes,
      selectedLipSampleName,
      selectedRendererMode,
      selectedLipRuntimeCandidate,
      lipUserAdjustment,
    ],
  );

  const selectLipRuntimeCandidate = useCallback(
    (candidate: LipRuntimeCandidate) => {
      const nextActiveRegions = { ...DEFAULT_ACTIVE_REGIONS };

      setSelectedLipRuntimeCandidateId(candidate.candidateId);
      setFocusedRegion('lip');
      setActiveRegions(nextActiveRegions);
      postRecipeBatch(
        regionRecipes,
        nextActiveRegions,
        'lip',
        selectedRendererMode,
        selectedLipSample,
        candidate,
        lipUserAdjustment,
      );
    },
    [
      lipUserAdjustment,
      postRecipeBatch,
      regionRecipes,
      selectedLipSample,
      selectedRendererMode,
    ],
  );

  const updateLipUserAdjustment = useCallback(
    async (field: LipAdjustmentField, nextValue: number) => {
      const roundedValue = Number(
        Math.max(-1, Math.min(1, nextValue)).toFixed(2),
      );
      const nextAdjustment = {
        ...lipUserAdjustment,
        [field]: roundedValue,
      };
      const nextActiveRegions = { ...DEFAULT_ACTIVE_REGIONS };
      const providerResult = nativeProviderResults[lipGenerateProvider];
      const providerShotResults =
        nativeProviderShotResults[lipGenerateProvider] ??
        (providerResult ? [providerResult] : []);

      setLipUserAdjustment(nextAdjustment);
      setSavedGeneratedPackage(null);
      resetGeneratedApplyFlow(`lip_adjustment_${field}`);
      if (providerResult?.boundary && providerResult.arFaceExport) {
        const rebuiltCandidates = LIP_GENERATE_EXPRESSION_OPTIONS.map(
          expressionOption =>
            buildGeneratedLipPackage({
              nativeResult: providerResult,
              providerResults: providerShotResults.length
                ? providerShotResults
                : [providerResult],
              expressionMode: expressionOption.name,
              adjustment: nextAdjustment,
            }),
        );
        const rebuiltCandidatesWithPreviews =
          await renderGeneratedCandidatePreviews(rebuiltCandidates);
        const selectedCandidateStillAvailable = rebuiltCandidates.some(
          candidate =>
            candidate.candidateKey === selectedGeneratedCandidateKey &&
            candidate.package,
        );

        setGeneratedCandidates(rebuiltCandidatesWithPreviews);
        setSelectedGeneratedCandidateKey(
          selectedCandidateStillAvailable
            ? selectedGeneratedCandidateKey
            : rebuiltCandidatesWithPreviews.find(candidate => candidate.package)
                ?.candidateKey ?? `${lipGenerateProvider}/uvOnly`,
        );
        setGeneratedCandidatesStale(false);
        setWizardNotice('조정값이 현재 사진과 저장 후보에 바로 반영되었습니다.');
      } else {
        setGeneratedCandidatesStale(generatedCandidates.length > 0);
        setWizardNotice('추출 결과가 없어 조정 preview를 다시 만들 수 없습니다.');
      }
      setFocusedRegion('lip');
      setActiveRegions(nextActiveRegions);
      postRecipeBatch(
        regionRecipes,
        nextActiveRegions,
        'lip',
        selectedRendererMode,
        selectedLipSample,
        selectedLipRuntimeCandidate,
        nextAdjustment,
      );
    },
    [
      generatedCandidates.length,
      lipUserAdjustment,
      lipGenerateProvider,
      nativeProviderResults,
      nativeProviderShotResults,
      postRecipeBatch,
      regionRecipes,
      renderGeneratedCandidatePreviews,
      resetGeneratedApplyFlow,
      selectedGeneratedCandidateKey,
      selectedLipSample,
      selectedLipRuntimeCandidate,
      selectedRendererMode,
    ],
  );

  const selectLipColor = useCallback(
    (color: LipColor) => {
      updateSelectedLipSample({ color: color.color });
    },
    [updateSelectedLipSample],
  );

  const selectLipFinish = useCallback(
    (finish: LipFinish) => {
      updateSelectedLipSample({
        finish,
        ...LIP_FINISH_DEFAULTS[finish],
      });
    },
    [updateSelectedLipSample],
  );

  const updateLipTuningValue = useCallback(
    (field: LipTuningField, value: number) => {
      updateSelectedLipSample({ [field]: value } as Partial<LipSample>);
    },
    [updateSelectedLipSample],
  );

  return (
    <View style={styles.unityScreen}>
      <UnityView
        key={`unity-view-${entryCount}`}
        ref={unityRef}
        style={styles.unityView}
        onUnityMessage={handleUnityMessage}
      />

      {isUsingCapturedFrameReview && (
        <View pointerEvents="none" style={styles.capturedFrameShield}>
          {capturedFramePreviewUri ? (
            <Image
              source={{ uri: capturedFramePreviewUri }}
              style={styles.capturedFrameImage}
            />
          ) : null}
          <View style={styles.capturedFrameScrim} />
          <Text style={styles.capturedFrameShieldTitle}>캡처 프레임 검토</Text>
          <Text style={styles.capturedFrameShieldText}>
            {capturedFramePreviewUri
              ? '저장된 얼굴 프레임을 기준으로 마스크를 만듭니다.'
              : '촬영은 끝났고 저장된 얼굴 프레임을 준비하고 있습니다.'}
          </Text>
        </View>
      )}

      <View
        pointerEvents="box-none"
        style={[
          styles.unityOverlay,
          {
            paddingTop: safeAreaInsets.top + 12,
            paddingBottom: safeAreaInsets.bottom + 16,
          },
        ]}
      >
        <View style={styles.topChrome}>
          <View style={styles.topActionRow}>
            <Pressable
              accessibilityRole="button"
              style={({ pressed }) => [
                styles.closeButton,
                pressed && styles.closeButtonPressed,
              ]}
              onPress={handleClose}
            >
              <Text style={styles.closeButtonText}>Close</Text>
            </Pressable>
          </View>

          <View style={styles.productTitlePill}>
            <Text style={styles.productTitleText}>
              {hasGeneratedMaskApplied ? 'AR 립 검증' : '맞춤 Generate'}
            </Text>
            <Pressable
              accessibilityRole="button"
              testID="e7-debug-toggle"
              style={({ pressed }) => [
                styles.productDebugButton,
                validationViewMode === 'full' && styles.productDebugButtonOn,
                pressed && styles.colorButtonPressed,
              ]}
              onPress={() =>
                setValidationViewMode(current =>
                  current === 'full' ? 'compact' : 'full',
                )
              }
            >
              <Text style={styles.productDebugButtonText}>Debug</Text>
            </Pressable>
          </View>
        </View>

        {hasGeneratedMaskApplied ? (
          <GeneratedRuntimeAppliedBanner
            notice={wizardNotice}
            controls={generatedValidationControls}
            onChangeControls={updateGeneratedMaskValidationControls}
            onReopenGenerate={() => {
              resetGeneratedApplyFlow('reopen_generate_after_apply');
              setWizardStep('adjust');
              setWizardNotice('마스크 조정 화면을 다시 열었습니다.');
            }}
          />
        ) : (
          <E7GenerateWizard
            activeStep={wizardStep}
            activeStepIndex={wizardStepIndex}
            captureShots={captureShots}
            capturedShotCount={capturedShotCount}
            alignmentGates={alignmentGates}
            generatedCandidates={generatedCandidates}
            generatedCandidatesStale={generatedCandidatesStale}
            generatedApplyState={generatedApplyState}
            isGeneratingCandidates={isGeneratingCandidates}
            isSavingGeneratedPackage={isSavingGeneratedPackage}
            nativeProviderResults={nativeProviderResults}
            notice={wizardNotice}
            canProceedFromAlign={faceAlignmentReady}
            canGenerateCandidates={canGenerateCandidates}
            canSaveGeneratedPackage={canSaveGeneratedPackage}
            savedGeneratedPackage={savedGeneratedPackage}
            selectedProvider={lipGenerateProvider}
            selectedCandidate={selectedGeneratedCandidate}
            selectedCandidateKey={selectedGeneratedCandidateKey}
            selectedLipSample={selectedLipSample}
            lipUserAdjustment={lipUserAdjustment}
            activeLipAdjustment={activeLipAdjustment}
            activeLipAdjustmentField={activeLipAdjustmentField}
            onStepRequest={step => {
              const requestedIndex = getWizardStepIndex(step);
              if (requestedIndex <= wizardStepIndex + 1) {
                setWizardStep(step);
              } else {
                setWizardNotice('이전 단계를 먼저 통과해야 합니다.');
              }
            }}
            onBack={() => {
              const previousStep = E7_WIZARD_STEPS[wizardStepIndex - 1];
              if (previousStep) {
                setWizardStep(previousStep);
              }
            }}
            onCaptureShot={postWizardCaptureShot}
            onSelectProvider={provider => {
              setLipGenerateProvider(provider);
              setNativeProviderResults({});
              setNativeProviderShotResults({});
              setGeneratedCandidates([]);
              setSavedGeneratedPackage(null);
              resetGeneratedApplyFlow(`select_provider_${provider}`);
              setGeneratedCandidatesStale(false);
              setSelectedGeneratedCandidateKey(`${provider}/uvOnly`);
              setWizardNotice(
                `${formatProviderLabel(provider)} 추출 방식이 선택되었습니다.`,
              );
            }}
            onGenerateCandidates={() =>
              generateWizardCandidates({
                stayOnStep: wizardStep === 'adjust',
                reason: wizardStep === 'adjust' ? 'manual' : undefined,
              })
            }
            onRetakeCapture={() => {
              setCaptureSetId(createCaptureSetId(entryCount));
              setCaptureShots(createInitialCaptureShots());
              setPendingCapturePairId(null);
              setPendingCaptureShotKind(null);
              setNativeProviderResults({});
              setNativeProviderShotResults({});
              setGeneratedCandidates([]);
              setSavedGeneratedPackage(null);
              setGeneratedCandidatesStale(false);
              setSelectedGeneratedCandidateKey(`${lipGenerateProvider}/uvOnly`);
              resetGeneratedApplyFlow('retake_capture');
              setWizardStep('capture');
              setWizardNotice('다시 촬영합니다. 새 얼굴 프레임을 저장한 뒤 마스크를 만드세요.');
            }}
            onSelectCandidate={candidateKey => {
              setSelectedGeneratedCandidateKey(candidateKey);
              resetGeneratedApplyFlow(`select_candidate_${candidateKey}`);
              setSavedGeneratedPackage(null);
            }}
            onSelectAdjustmentField={setActiveLipAdjustmentField}
            onAdjustLip={updateLipUserAdjustment}
            onSave={saveSelectedGeneratedPackage}
          />
        )}

        {showFullDebug && (
          <View style={styles.debugPanel}>
            <Text style={styles.debugMetaText}>
              {`${E7_BOUNDARY_PLAN_VERSION} entry #${entryCount} mounted=${mountedAt} previous_exits=${exitCount}`}
            </Text>
            <Text style={styles.debugLabel}>Evidence metadata</Text>
            {evidenceMetadataLines.map(line => (
              <Text
                key={line}
                style={styles.debugHistoryText}
                numberOfLines={1}
              >
                {line}
              </Text>
            ))}
            <Text style={styles.debugLabel}>Latest Unity event</Text>
            <Text style={styles.debugText} numberOfLines={2}>
              {lastUnityEvent
                ? `${lastUnityEvent.receivedAt} ${lastUnityEvent.displayText}`
                : `waiting_for_unity_event mounted=${mountedAt}`}
            </Text>
            <FaceLifecyclePanel
              event={unityEventStatus.face_lifecycle?.parsed}
              receivedAt={unityEventStatus.face_lifecycle?.receivedAt}
            />
            <FaceFeatureSnapshotPanel
              event={unityEventStatus.face_feature_snapshot?.parsed}
              receivedAt={unityEventStatus.face_feature_snapshot?.receivedAt}
            />
            <E7StatusPanel
              currentRegions={activeRegionSummary}
              metricRecord={unityEventStatus.e7_metric_sample}
              recipeRecord={unityEventStatus.recipe_applied}
            />
            <View style={styles.debugStatus}>
              <Text style={styles.debugSubLabel}>Last by type</Text>
              {UNITY_EVENT_TYPES.map(type => {
                const statusEvent = unityEventStatus[type];

                return (
                  <Text
                    key={type}
                    style={styles.debugHistoryText}
                    numberOfLines={1}
                  >
                    {formatUnityEventTypeStatus(type, statusEvent)}
                  </Text>
                );
              })}
            </View>
            <View style={styles.debugHistory}>
              {unityEventHistory.length === 0 ? (
                <Text style={styles.debugHistoryText}>history empty</Text>
              ) : (
                unityEventHistory.map(historyEvent => (
                  <Text
                    key={`${historyEvent.id}-${historyEvent.rawMessage}`}
                    style={styles.debugHistoryText}
                    numberOfLines={1}
                  >
                    {historyEvent.receivedAt} {historyEvent.displayText}
                  </Text>
                ))
              )}
            </View>
          </View>
        )}

        {showCompactControls && (
          <View
            style={[
              styles.recipePanel,
              styles.recipePanelCompact,
            ]}
          >
            <View style={styles.recipePanelHeader}>
              <Text style={styles.recipePanelLabel}>Regions</Text>
              <Text style={styles.recipePanelMetaText} numberOfLines={1}>
                {`active=${activeRegionSummary} / focus=${focusedRegion}`}
              </Text>
            </View>

            <CompactEvidenceHud
              validationViewMode={validationViewMode}
              activeRegionSummary={activeRegionSummary}
              focusedRegion={focusedRegion}
              currentLipSample={selectedLipSample}
              latestMetric={latestMetric}
              latestLifecycle={latestLifecycle}
              latestRecipe={latestRecipe}
              recipeLatencyMs={recipeLatencyMs}
            />

            <View style={styles.generateControlBlock}>
              <View style={styles.modeButtonRow}>
                {LIP_GENERATE_PROVIDER_OPTIONS.map(providerOption => {
                  const isSelected =
                    providerOption.name === lipGenerateProvider;

                  return (
                    <Pressable
                      accessibilityRole="button"
                      accessibilityState={{ selected: isSelected }}
                      key={providerOption.name}
                      testID={`lip-generate-provider-${providerOption.name}`}
                      style={({ pressed }) => [
                        styles.modeButton,
                        isSelected && styles.modeButtonSelected,
                        pressed && styles.colorButtonPressed,
                      ]}
                      onPress={() =>
                        setLipGenerateProvider(providerOption.name)
                      }
                    >
                      <Text
                        style={[
                          styles.modeButtonText,
                          isSelected && styles.modeButtonTextSelected,
                        ]}
                      >
                        {providerOption.label}
                      </Text>
                    </Pressable>
                  );
                })}
              </View>

              <View style={styles.modeButtonRow}>
                {LIP_GENERATE_EXPRESSION_OPTIONS.map(expressionOption => {
                  const isSelected =
                    expressionOption.name === lipGenerateExpressionMode;

                  return (
                    <Pressable
                      accessibilityRole="button"
                      accessibilityState={{ selected: isSelected }}
                      key={expressionOption.name}
                      testID={`lip-generate-expression-${expressionOption.name}`}
                      style={({ pressed }) => [
                        styles.modeButton,
                        isSelected && styles.modeButtonSelected,
                        pressed && styles.colorButtonPressed,
                      ]}
                      onPress={() =>
                        setLipGenerateExpressionMode(expressionOption.name)
                      }
                    >
                      <Text
                        style={[
                          styles.modeButtonText,
                          isSelected && styles.modeButtonTextSelected,
                        ]}
                      >
                        {expressionOption.label}
                      </Text>
                    </Pressable>
                  );
                })}
                <Pressable
                  accessibilityRole="button"
                  testID="lip-generate-apply"
                  style={({ pressed }) => [
                    styles.generatedMaskButton,
                    pressed && styles.colorButtonPressed,
                  ]}
                  onPress={postGeneratedLipMask}
                >
                  <Text style={styles.generatedMaskButtonText}>Generate</Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  testID="full-face-region-package-apply"
                  style={({ pressed }) => [
                    styles.generatedMaskButton,
                    pressed && styles.colorButtonPressed,
                  ]}
                  onPress={postFullFaceRegionPackage}
                >
                  <Text style={styles.generatedMaskButtonText}>Full-face</Text>
                </Pressable>
              </View>

              <Text style={styles.recipePanelMetaText} numberOfLines={1}>
                {lastGeneratedLipMaskSummary}
              </Text>
            </View>

            <View style={styles.regionButtonRow}>
              {RECIPE_REGION_OPTIONS.map(regionOption => {
                const isActive = activeRegions[regionOption];
                const isFocused = regionOption === focusedRegion;

                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{
                      checked: isActive,
                      selected: isFocused,
                    }}
                    key={regionOption}
                    testID={`region-toggle-${regionOption}`}
                    style={({ pressed }) => [
                      styles.regionButton,
                      isActive && styles.regionButtonSelected,
                      isFocused && styles.regionButtonFocused,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={() => toggleRegion(regionOption)}
                  >
                    <Text
                      style={[
                        styles.regionButtonText,
                        isActive && styles.regionButtonTextSelected,
                      ]}
                    >
                      {regionOption}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {showCompactControls && (
              <>
                <View style={styles.lipSampleButtonRow}>
                  {LIP_SAMPLE_OPTIONS.map(lipSample => {
                    const isSelected = lipSample.name === selectedLipSample.name;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={lipSample.name}
                        style={({ pressed }) => [
                          styles.lipSampleButton,
                          isSelected && styles.lipSampleButtonSelected,
                          pressed && styles.colorButtonPressed,
                        ]}
                        onPress={() => selectLipSample(lipSample)}
                      >
                        <Text
                          style={[
                            styles.lipSampleButtonText,
                            isSelected && styles.lipSampleButtonTextSelected,
                          ]}
                        >
                          {lipSample.label}
                        </Text>
                        <Text
                          style={[
                            styles.lipSampleButtonMetaText,
                            isSelected && styles.lipSampleButtonTextSelected,
                          ]}
                        >
                          {lipSample.finish}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                <ScrollView
                  horizontal
                  showsHorizontalScrollIndicator={false}
                  contentContainerStyle={styles.lipRuntimeCandidateRow}
                >
                  {LIP_RUNTIME_CANDIDATE_OPTIONS.map(candidate => {
                    const isSelected =
                      candidate.candidateId ===
                      selectedLipRuntimeCandidate.candidateId;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={candidate.candidateId}
                        testID={`lip-runtime-candidate-${candidate.candidateId}`}
                        style={({ pressed }) => [
                          styles.lipRuntimeCandidateButton,
                          isSelected &&
                            styles.lipRuntimeCandidateButtonSelected,
                          pressed && styles.colorButtonPressed,
                        ]}
                        onPress={() => selectLipRuntimeCandidate(candidate)}
                      >
                        <Text
                          style={[
                            styles.lipRuntimeCandidateText,
                            isSelected &&
                              styles.lipRuntimeCandidateTextSelected,
                          ]}
                        >
                          {candidate.label}
                        </Text>
                        <Text
                          style={[
                            styles.lipRuntimeCandidateMetaText,
                            isSelected &&
                              styles.lipRuntimeCandidateTextSelected,
                          ]}
                          numberOfLines={1}
                        >
                          {candidate.status}
                        </Text>
                      </Pressable>
                    );
                  })}
                </ScrollView>

                <View style={styles.colorButtonRow}>
                  {LIP_COLOR_OPTIONS.map(colorOption => {
                    const isSelected =
                      colorOption.color === selectedLipSample.color;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={colorOption.name}
                        testID={`lip-color-${colorOption.name}`}
                        style={({ pressed }) => [
                          styles.colorButton,
                          { backgroundColor: colorOption.color },
                          isSelected && styles.colorButtonSelected,
                          pressed && styles.colorButtonPressed,
                        ]}
                        onPress={() => selectLipColor(colorOption)}
                      >
                        <Text style={styles.colorButtonText}>
                          {colorOption.name}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                <View style={styles.modeButtonRow}>
                  {LIP_FINISH_OPTIONS.map(finishOption => {
                    const isSelected =
                      finishOption.name === selectedLipSample.finish;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={finishOption.name}
                        testID={`lip-finish-${finishOption.name}`}
                        style={({ pressed }) => [
                          styles.modeButton,
                          isSelected && styles.modeButtonSelected,
                          pressed && styles.colorButtonPressed,
                        ]}
                        onPress={() => selectLipFinish(finishOption.name)}
                      >
                        <Text
                          style={[
                            styles.modeButtonText,
                            isSelected && styles.modeButtonTextSelected,
                          ]}
                        >
                          {finishOption.label}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                <View style={styles.tuningFieldButtonRow}>
                  {LIP_TUNING_FIELD_OPTIONS.map(fieldOption => {
                    const isSelected =
                      fieldOption.name === activeLipTuningField;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={fieldOption.name}
                        style={({ pressed }) => [
                          styles.tuningFieldButton,
                          isSelected && styles.tuningFieldButtonSelected,
                          pressed && styles.colorButtonPressed,
                        ]}
                        onPress={() => setActiveLipTuningField(fieldOption.name)}
                      >
                        <Text
                          style={[
                            styles.tuningFieldButtonText,
                            isSelected && styles.tuningFieldButtonTextSelected,
                          ]}
                        >
                          {fieldOption.label}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                <TuningSlider
                  label={activeLipTuning.label}
                  value={selectedLipSample[activeLipTuning.name]}
                  width={sliderWidth}
                  onLayoutWidth={setSliderWidth}
                  onChange={value =>
                    updateLipTuningValue(activeLipTuning.name, value)
                  }
                />

                <View style={styles.adjustmentFieldButtonRow}>
                  {LIP_ADJUSTMENT_FIELD_OPTIONS.map(fieldOption => {
                    const isSelected =
                      fieldOption.name === activeLipAdjustmentField;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={fieldOption.name}
                        testID={`lip-adjust-field-${fieldOption.name}`}
                        style={({ pressed }) => [
                          styles.adjustmentFieldButton,
                          isSelected && styles.adjustmentFieldButtonSelected,
                          pressed && styles.colorButtonPressed,
                        ]}
                        onPress={() =>
                          setActiveLipAdjustmentField(fieldOption.name)
                        }
                      >
                        <Text
                          style={[
                            styles.adjustmentFieldButtonText,
                            isSelected &&
                              styles.adjustmentFieldButtonTextSelected,
                          ]}
                        >
                          {fieldOption.label}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                <AdjustmentStepper
                  label={activeLipAdjustment.label}
                  value={lipUserAdjustment[activeLipAdjustment.name]}
                  onChange={value =>
                    updateLipUserAdjustment(activeLipAdjustment.name, value)
                  }
                />

                <Text style={styles.recipeValueText} numberOfLines={4}>
                  선택 룩 {selectedLipSample.label} / 색 {selectedLipSample.color}{' '}
                  / 질감 {formatLipFinishLabel(selectedLipSample.finish)} / 농도{' '}
                  {Math.round(selectedLipSample.opacity * 100)}% / 경계 조정{' '}
                  {lipUserAdjustment.cornerReach.toFixed(2)},{' '}
                  {lipUserAdjustment.upperLipTightness.toFixed(2)},{' '}
                  {lipUserAdjustment.lowerLipTightness.toFixed(2)},{' '}
                  {lipUserAdjustment.verticalOffset.toFixed(2)}
                </Text>
              </>
            )}

            <Text style={styles.recipeAppliedText} numberOfLines={2}>
              {formatRecipeAppliedSummary(
                unityEventStatus.recipe_applied?.parsed,
              )}
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

type E7GenerateWizardProps = {
  activeStep: E7WizardStep;
  activeStepIndex: number;
  captureShots: Record<E7CaptureShotKind, E7CaptureShotState>;
  capturedShotCount: number;
  alignmentGates: E7AlignmentGate[];
  generatedCandidates: E7GeneratedCandidateWithPreview[];
  generatedCandidatesStale: boolean;
  generatedApplyState: E7GeneratedApplyState;
  isGeneratingCandidates: boolean;
  isSavingGeneratedPackage: boolean;
  nativeProviderResults: Partial<
    Record<GeneratedLipMaskProvider, E7NativeBoundaryResult>
  >;
  notice: string;
  canProceedFromAlign: boolean;
  canGenerateCandidates: boolean;
  canSaveGeneratedPackage: boolean;
  savedGeneratedPackage: E7SavedPackageRecord | null;
  selectedProvider: GeneratedLipMaskProvider;
  selectedCandidate?: E7GeneratedCandidateWithPreview;
  selectedCandidateKey: string;
  selectedLipSample: LipSample;
  lipUserAdjustment: LipUserAdjustment;
  activeLipAdjustment: (typeof LIP_ADJUSTMENT_FIELD_OPTIONS)[number];
  activeLipAdjustmentField: LipAdjustmentField;
  onStepRequest: (step: E7WizardStep) => void;
  onBack: () => void;
  onCaptureShot: (shotKind: E7CaptureShotKind) => void;
  onRetakeCapture: () => void;
  onSelectProvider: (provider: GeneratedLipMaskProvider) => void;
  onGenerateCandidates: () => void;
  onSelectCandidate: (candidateKey: string) => void;
  onSelectAdjustmentField: (field: LipAdjustmentField) => void;
  onAdjustLip: (field: LipAdjustmentField, nextValue: number) => void;
  onSave: () => void;
};

function E7GenerateWizard({
  activeStep,
  activeStepIndex,
  captureShots,
  capturedShotCount,
  alignmentGates,
  generatedCandidates,
  generatedCandidatesStale,
  generatedApplyState,
  isGeneratingCandidates,
  isSavingGeneratedPackage,
  nativeProviderResults,
  notice,
  canProceedFromAlign,
  canGenerateCandidates,
  canSaveGeneratedPackage,
  savedGeneratedPackage,
  selectedProvider,
  selectedCandidate,
  selectedCandidateKey,
  selectedLipSample,
  lipUserAdjustment,
  activeLipAdjustment,
  activeLipAdjustmentField,
  onStepRequest,
  onBack,
  onCaptureShot,
  onRetakeCapture,
  onSelectProvider,
  onGenerateCandidates,
  onSelectCandidate,
  onSelectAdjustmentField,
  onAdjustLip,
  onSave,
}: E7GenerateWizardProps) {
  const selectedGeneratedCandidate =
    selectedCandidate ??
    generatedCandidates.find(
      candidate => candidate.candidateKey === selectedCandidateKey,
    );
  const nextCaptureShot = E7_CAPTURE_SHOT_OPTIONS.find(
    shot => !isCapturedShot(captureShots[shot.kind]),
  );
  const isNextCaptureInProgress = nextCaptureShot
    ? captureShots[nextCaptureShot.kind].status === 'capturing'
    : false;
  const visionStatus = nativeProviderResults.vision?.status ?? 'pending';
  const mediapipeStatus = nativeProviderResults.mediapipe?.status ?? 'pending';

  return (
    <View style={styles.generateWizardSheet} pointerEvents="box-none">
      <View
        style={[
          styles.generateWizardCard,
          activeStep === 'adjust' && styles.generateWizardCardAdjust,
        ]}
      >
        <ScrollView
          horizontal
          showsHorizontalScrollIndicator={false}
          contentContainerStyle={styles.generateWizardStepRow}
        >
          {E7_WIZARD_STEPS.map((step, index) => {
            const isActive = step === activeStep;
            const isLocked = index > activeStepIndex;

            return (
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ selected: isActive, disabled: isLocked }}
                key={step}
                disabled={isLocked}
                testID={`e7-wizard-step-${step}`}
                style={({ pressed }) => [
                  styles.generateWizardStepChip,
                  isActive && styles.generateWizardStepChipActive,
                  isLocked && styles.generateWizardStepChipLocked,
                  pressed && styles.colorButtonPressed,
                ]}
                onPress={() => onStepRequest(step)}
              >
                <Text
                  style={[
                    styles.generateWizardStepText,
                    isActive && styles.generateWizardStepTextActive,
                  ]}
                >
                  {index + 1}. {formatWizardStepLabel(step)}
                </Text>
              </Pressable>
            );
          })}
        </ScrollView>

        <View style={styles.generateWizardHeader}>
          <Pressable
            accessibilityRole="button"
            disabled={activeStepIndex === 0}
            testID="e7-wizard-back"
            style={({ pressed }) => [
              styles.generateWizardBackButton,
              activeStepIndex === 0 && styles.generateWizardButtonDisabled,
              pressed && styles.colorButtonPressed,
            ]}
            onPress={onBack}
          >
            <Text style={styles.generateWizardBackText}>이전</Text>
          </Pressable>
          <View>
            <Text style={styles.generateWizardEyebrow}>
              STEP {activeStepIndex + 1}
            </Text>
            <Text style={styles.generateWizardTitle}>
              {formatWizardStepTitle(activeStep)}
            </Text>
          </View>
          <Text style={styles.generateWizardMeta} numberOfLines={2}>
            {notice}
          </Text>
        </View>

        {activeStep === 'start' && (
          <View style={styles.generateWizardBody}>
            <Text style={styles.generateWizardBodyText}>
              현재 얼굴에서 촬영하고, 기기 안에서만 입술 마스크를 만듭니다.
            </Text>
            <Text style={styles.generateWizardBodyText}>
              촬영 데이터는 업로드하지 않고 이 기기 안에서만 처리합니다.
            </Text>
            <Pressable
              accessibilityRole="button"
              testID="e7-wizard-start-next"
              style={styles.generateWizardPrimaryButton}
              onPress={() => onStepRequest('align')}
            >
              <Text style={styles.generateWizardPrimaryText}>얼굴 정렬 시작</Text>
            </Pressable>
          </View>
        )}

        {activeStep === 'align' && (
          <View style={styles.generateWizardBody}>
            <View style={styles.generateWizardCheckGrid}>
              {alignmentGates.map(gate => (
                <AlignmentGatePill gate={gate} key={gate.label} />
              ))}
            </View>
            <Text style={styles.generateWizardBodyText}>
              얼굴이 잡히고 카메라 신호가 안정되면 촬영으로 넘어갑니다.
            </Text>
            <Pressable
              accessibilityRole="button"
              disabled={!canProceedFromAlign}
              testID="e7-wizard-align-next"
              style={[
                styles.generateWizardPrimaryButton,
                !canProceedFromAlign && styles.generateWizardButtonDisabled,
              ]}
              onPress={() => onStepRequest('capture')}
            >
              <Text style={styles.generateWizardPrimaryText}>
                {canProceedFromAlign ? '촬영으로 이동' : '얼굴 측정 대기'}
              </Text>
            </Pressable>
          </View>
        )}

        {activeStep === 'capture' && (
          <View style={styles.generateWizardBody}>
            <Text style={styles.generateWizardBodyText}>
              {capturedShotCount}/{E7_CAPTURE_SHOT_OPTIONS.length} 컷 완료.
              버튼 하나로 필요한 표정 큐를 순서대로 저장합니다.
            </Text>
            {nextCaptureShot ? (
              <Text style={styles.generateWizardBodyText}>
                다음 컷: {nextCaptureShot.label} · {nextCaptureShot.guidance}
              </Text>
            ) : (
              <Text style={styles.generateWizardBodyText}>
                모든 컷이 저장되었습니다. 이제 저장된 얼굴 프레임으로 마스크를 만듭니다.
              </Text>
            )}
            <View style={styles.generateWizardShotGrid}>
              {E7_CAPTURE_SHOT_OPTIONS.map(shot => {
                const state = captureShots[shot.kind];
                const isDone = state.status === 'captured';
                const isCapturing = state.status === 'capturing';
                const isNext = nextCaptureShot?.kind === shot.kind;

                return (
                  <View
                    key={shot.kind}
                    testID={`e7-capture-shot-${shot.kind}`}
                    style={[
                      styles.generateWizardShotButton,
                      isNext && styles.generateWizardShotButtonNext,
                      isDone && styles.generateWizardShotButtonDone,
                      state.status === 'blocked' &&
                        styles.generateWizardShotButtonBlocked,
                    ]}
                  >
                    <Text style={styles.generateWizardShotLabel}>
                      {shot.label}
                    </Text>
                    <Text style={styles.generateWizardShotMeta}>
                      {state.status === 'blocked'
                        ? '다시 촬영'
                        : isCapturing
                        ? '촬영 중'
                        : isDone
                          ? '저장됨'
                          : isNext
                            ? shot.guidance
                            : '대기'}
                    </Text>
                  </View>
                );
              })}
            </View>
            <Pressable
              accessibilityRole="button"
              disabled={isNextCaptureInProgress}
              testID="e7-wizard-capture-primary"
              style={[
                styles.generateWizardPrimaryButton,
                isNextCaptureInProgress && styles.generateWizardButtonDisabled,
              ]}
              onPress={() => {
                if (nextCaptureShot) {
                  onCaptureShot(nextCaptureShot.kind);
                } else {
                  onStepRequest('extract');
                }
              }}
            >
              <Text style={styles.generateWizardPrimaryText}>
                {nextCaptureShot
                  ? isNextCaptureInProgress
                    ? '촬영 중'
                    : `${nextCaptureShot.label} 촬영`
                  : '추출 단계로 이동'}
              </Text>
            </Pressable>
          </View>
        )}

        {activeStep === 'extract' && (
          <View style={styles.generateWizardBody}>
            <View style={styles.generateWizardProviderRow}>
              <ProviderStatusPill
                label="Vision"
                status={visionStatus}
                selected={selectedProvider === 'vision'}
                onPress={() => onSelectProvider('vision')}
              />
              <ProviderStatusPill
                label="MediaPipe"
                status={mediapipeStatus}
                selected={selectedProvider === 'mediapipe'}
                onPress={() => onSelectProvider('mediapipe')}
              />
            </View>
            <Text style={styles.generateWizardBodyText}>
              둘 중 하나를 선택하면 방금 촬영한 얼굴에서 입술 경계를 만듭니다.
            </Text>
            <Pressable
              accessibilityRole="button"
              disabled={!canGenerateCandidates || isGeneratingCandidates}
              testID="e7-wizard-generate-candidates"
              style={[
                styles.generateWizardPrimaryButton,
                (!canGenerateCandidates || isGeneratingCandidates) &&
                  styles.generateWizardButtonDisabled,
              ]}
              onPress={onGenerateCandidates}
            >
              <Text style={styles.generateWizardPrimaryText}>
                {isGeneratingCandidates
                  ? '생성 중'
                  : `${formatProviderLabel(selectedProvider)} 후보 생성`}
              </Text>
            </Pressable>
          </View>
        )}

        {activeStep === 'blend' && (
          <View style={styles.generateWizardBody}>
            <ScrollView
              horizontal
              showsHorizontalScrollIndicator={false}
              contentContainerStyle={styles.generateWizardCandidateGrid}
            >
              {generatedCandidates.map(candidate => {
                const isSelected = candidate.candidateKey === selectedCandidateKey;

                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: isSelected }}
                    key={candidate.candidateKey}
                    testID={`e7-candidate-${candidate.candidateKey}`}
                    style={({ pressed }) => [
                      styles.generateWizardCandidateCard,
                      isSelected && styles.generateWizardCandidateCardSelected,
                      candidate.status === 'blocked' &&
                        styles.generateWizardCandidateCardBlocked,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={() => onSelectCandidate(candidate.candidateKey)}
                  >
                    <View style={styles.generateWizardCandidatePreview}>
                      {candidate.previewUri ? (
                        <Image
                          source={{ uri: candidate.previewUri }}
                          style={styles.generateWizardCandidatePreviewImage}
                        />
                      ) : (
                        <View style={styles.generateWizardCandidatePreviewEmpty}>
                          <Text style={styles.generateWizardCandidateReason}>
                            {formatCandidatePreviewStatus(candidate)}
                          </Text>
                        </View>
                      )}
                    </View>
                    <View style={styles.generateWizardCandidateCopy}>
                      <Text style={styles.generateWizardCandidateTitle}>
                        {formatGeneratedCandidateTitle(candidate)}
                      </Text>
                      <Text style={styles.generateWizardCandidateMeta}>
                        {formatGeneratedCandidateMeta(candidate)}
                      </Text>
                      <Text
                        style={styles.generateWizardCandidateReason}
                        numberOfLines={2}
                      >
                        {formatGeneratedCandidateDescription(candidate)}
                      </Text>
                    </View>
                  </Pressable>
                );
              })}
            </ScrollView>
            {!selectedGeneratedCandidate?.package && (
              <Pressable
                accessibilityRole="button"
                testID="e7-wizard-select-provider-after-blocked"
                style={styles.generateWizardSecondaryButton}
                onPress={() => onStepRequest('extract')}
              >
                <Text style={styles.generateWizardSecondaryText}>
                  다른 방식 선택
                </Text>
              </Pressable>
            )}
            <Pressable
              accessibilityRole="button"
              disabled={!selectedGeneratedCandidate?.package}
              testID="e7-wizard-blend-next"
              style={[
                styles.generateWizardPrimaryButton,
                !selectedGeneratedCandidate?.package &&
                  styles.generateWizardButtonDisabled,
              ]}
              onPress={() => onStepRequest('adjust')}
            >
              <Text style={styles.generateWizardPrimaryText}>조정으로 이동</Text>
            </Pressable>
          </View>
        )}

        {activeStep === 'adjust' && (
          <View style={styles.generateWizardBody}>
            <GeneratedAdjustmentPreview
              candidate={selectedGeneratedCandidate}
              selectedCandidateKey={selectedCandidateKey}
            />
            <View style={styles.adjustmentFieldButtonRow}>
              {LIP_ADJUSTMENT_FIELD_OPTIONS.map(fieldOption => {
                const isSelected = fieldOption.name === activeLipAdjustmentField;

                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: isSelected }}
                    key={fieldOption.name}
                    testID={`lip-adjust-field-${fieldOption.name}`}
                    style={({ pressed }) => [
                      styles.adjustmentFieldButton,
                      isSelected && styles.adjustmentFieldButtonSelected,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={() => onSelectAdjustmentField(fieldOption.name)}
                  >
                    <Text
                      style={[
                        styles.adjustmentFieldButtonText,
                        isSelected && styles.adjustmentFieldButtonTextSelected,
                      ]}
                    >
                      {fieldOption.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>
            <AdjustmentStepper
              label={activeLipAdjustment.label}
              value={lipUserAdjustment[activeLipAdjustment.name]}
              onChange={value => onAdjustLip(activeLipAdjustment.name, value)}
            />
            <Text style={styles.generateWizardBodyText}>
              {generatedCandidatesStale
                ? '추출 결과가 없어 조정 preview를 만들 수 없습니다.'
                : '조정값이 미리보기와 저장 후보에 바로 반영됩니다.'}
            </Text>
            <Text style={styles.generateWizardBodyText}>
              선택 룩: {selectedLipSample.label} / 질감:{' '}
              {formatLipFinishLabel(selectedLipSample.finish)}
            </Text>
            <View style={styles.generateWizardActionRow}>
              <Pressable
                accessibilityRole="button"
                testID="e7-wizard-regenerate-after-adjust"
                style={styles.generateWizardSecondaryButton}
                onPress={onGenerateCandidates}
              >
                <Text style={styles.generateWizardSecondaryText}>현재 사진으로 다시 생성</Text>
              </Pressable>
              <Pressable
                accessibilityRole="button"
                testID="e7-wizard-retake-after-adjust"
                style={styles.generateWizardSecondaryButton}
                onPress={onRetakeCapture}
              >
                <Text style={styles.generateWizardSecondaryText}>다시 촬영</Text>
              </Pressable>
            </View>
            <View style={styles.generateWizardActionRow}>
              <Pressable
                accessibilityRole="button"
                disabled={!canSaveGeneratedPackage}
                testID="e7-wizard-save-and-run"
                style={[
                  styles.generateWizardPrimaryButton,
                  !canSaveGeneratedPackage && styles.generateWizardButtonDisabled,
                ]}
                onPress={onSave}
              >
                <Text style={styles.generateWizardPrimaryText}>
                  {isSavingGeneratedPackage ? '저장 중' : '저장하고 AR 실행'}
                </Text>
              </Pressable>
            </View>
          </View>
        )}

        {activeStep === 'apply' && (
          <View style={styles.generateWizardBody}>
            <Text style={styles.generateWizardBodyText}>
              {formatGeneratedApplyUserMessage(generatedApplyState)}
            </Text>
            <Text style={styles.generateWizardBodyText}>
              저장 완료 후 AR 화면에서 마스크가 보일 때까지 확인합니다.
            </Text>
            <Text style={styles.generateWizardBodyText} numberOfLines={2}>
              {generatedApplyState.status === 'blocked' ||
              generatedApplyState.status === 'timeout'
                ? formatGeneratedApplyRecoveryMessage(generatedApplyState)
                : '잠시만 기다려 주세요. 성공하면 조정 패널이 접히고 AR 검증 컨트롤이 표시됩니다.'}
            </Text>
            <View style={styles.generateWizardApplyGateGrid}>
              <ApplyGatePill
                label="저장"
                value={savedGeneratedPackage ? '완료' : '대기'}
                ready={Boolean(savedGeneratedPackage)}
              />
              <ApplyGatePill
                label="전송"
                value={
                  generatedApplyState.status === 'posting' ||
                  generatedApplyState.status === 'waitingAck' ||
                  generatedApplyState.status === 'applied'
                    ? '전송'
                    : '대기'
                }
                ready={
                  generatedApplyState.status === 'waitingAck' ||
                  generatedApplyState.status === 'applied'
                }
              />
              <ApplyGatePill
                label="AR 확인"
                value={
                  generatedApplyState.status === 'applied'
                    ? '확인'
                    : generatedApplyState.status === 'blocked'
                      ? '차단'
                    : generatedApplyState.status === 'timeout'
                        ? '지연'
                      : '대기'
                }
                ready={generatedApplyState.status === 'applied'}
              />
            </View>
            {(generatedApplyState.status === 'blocked' ||
              generatedApplyState.status === 'timeout') && (
              <View style={styles.generateWizardActionRow}>
                <Pressable
                  accessibilityRole="button"
                  disabled={isSavingGeneratedPackage}
                  testID="e7-wizard-apply-retry"
                  style={[
                    styles.generateWizardPrimaryButton,
                    styles.generateWizardActionButton,
                    isSavingGeneratedPackage &&
                      styles.generateWizardButtonDisabled,
                  ]}
                  onPress={onSave}
                >
                  <Text style={styles.generateWizardPrimaryText}>
                    저장/적용 재시도
                  </Text>
                </Pressable>
                <Pressable
                  accessibilityRole="button"
                  testID="e7-wizard-apply-retake"
                  style={styles.generateWizardSecondaryButton}
                  onPress={onRetakeCapture}
                >
                  <Text style={styles.generateWizardSecondaryText}>
                    촬영부터 다시
                  </Text>
                </Pressable>
              </View>
            )}
            <Text style={styles.generateWizardBodyText}>
              AR 화면 확인 전에는 적용 완료로 표시하지 않습니다.
            </Text>
          </View>
        )}
      </View>
    </View>
  );
}

function ProviderStatusPill({
  label,
  status,
  selected = false,
  onPress,
}: {
  label: string;
  status: string;
  selected?: boolean;
  onPress?: () => void;
}) {
  const content = (
    <>
      <Text style={styles.generateWizardProviderLabel}>{label}</Text>
      <Text style={styles.generateWizardProviderStatus}>
        {selected
          ? `선택됨 / ${formatProviderStatusLabel(status)}`
          : formatProviderStatusLabel(status)}
      </Text>
    </>
  );

  if (onPress) {
    return (
      <Pressable
        accessibilityRole="button"
        accessibilityState={{ selected }}
        style={({ pressed }) => [
          styles.generateWizardProviderPill,
          selected && styles.generateWizardProviderPillSelected,
          status === 'blocked' && styles.generateWizardProviderPillBlocked,
          pressed && styles.colorButtonPressed,
        ]}
        onPress={onPress}
      >
        {content}
      </Pressable>
    );
  }

  return (
    <View
      style={[
        styles.generateWizardProviderPill,
        selected && styles.generateWizardProviderPillSelected,
        status === 'blocked' && styles.generateWizardProviderPillBlocked,
      ]}
    >
      {content}
    </View>
  );
}

function GeneratedRuntimeAppliedBanner({
  notice,
  controls,
  onChangeControls,
  onReopenGenerate,
}: {
  notice: string;
  controls: GeneratedMaskValidationControls;
  onChangeControls: (patch: Partial<GeneratedMaskValidationControls>) => void;
  onReopenGenerate: () => void;
}) {
  return (
    <View
      style={styles.generateAppliedBanner}
      testID="e7-generated-ar-validation-controls"
    >
      <View style={styles.generateAppliedHeader}>
        <View>
          <Text style={styles.generateAppliedBannerTitle}>AR 립 적용됨</Text>
          <Text style={styles.generateAppliedBannerText} numberOfLines={2}>
            {notice}
          </Text>
        </View>
        <Pressable
          accessibilityRole="button"
          testID="e7-generated-reopen-generate"
          style={styles.generateAppliedSmallButton}
          onPress={onReopenGenerate}
        >
          <Text style={styles.generateAppliedSmallButtonText}>다시 조정</Text>
        </Pressable>
      </View>
      <Text style={styles.generateAppliedBannerText} numberOfLines={1}>
        마스크 ON/OFF, 진하게 보기, 색, 농도로 적용 상태를 확인하세요.
      </Text>
      <View style={styles.generateAppliedControlRow}>
        <Pressable
          accessibilityRole="button"
          testID="generated-mask-toggle"
          style={[
            styles.generateAppliedControlButton,
            controls.maskVisible && styles.generateAppliedControlButtonActive,
          ]}
          onPress={() =>
            onChangeControls({ maskVisible: !controls.maskVisible })
          }
        >
          <Text style={styles.generateAppliedControlText}>
            {controls.maskVisible ? '마스크 ON' : '마스크 OFF'}
          </Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          testID="generated-mask-strong"
          style={[
            styles.generateAppliedControlButton,
            controls.strongMode && styles.generateAppliedControlButtonActive,
          ]}
          onPress={() => onChangeControls({ strongMode: !controls.strongMode })}
        >
          <Text style={styles.generateAppliedControlText}>진하게 보기</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          testID="generated-mask-boundary"
          style={[
            styles.generateAppliedControlButton,
            controls.boundaryDebugVisible &&
              styles.generateAppliedControlButtonActive,
          ]}
          onPress={() =>
            onChangeControls({
              boundaryDebugVisible: !controls.boundaryDebugVisible,
            })
          }
        >
          <Text style={styles.generateAppliedControlText}>경계 보기</Text>
        </Pressable>
      </View>
      <View style={styles.generateAppliedColorRow}>
        {GENERATED_MASK_VALIDATION_COLORS.map(color => (
          <Pressable
            accessibilityRole="button"
            accessibilityState={{ selected: controls.colorHex === color.color }}
            key={color.name}
            testID={`generated-mask-color-${color.name}`}
            style={[
              styles.generateAppliedColorButton,
              { backgroundColor: color.color },
              controls.colorHex === color.color &&
                styles.generateAppliedColorButtonSelected,
            ]}
            onPress={() => onChangeControls({ colorHex: color.color })}
          >
            <Text style={styles.generateAppliedColorText}>{color.name}</Text>
          </Pressable>
        ))}
      </View>
      <View style={styles.generateAppliedControlRow}>
        <Pressable
          accessibilityRole="button"
          testID="generated-mask-opacity-minus"
          style={styles.generateAppliedControlButton}
          onPress={() => onChangeControls({ opacity: controls.opacity - 0.1 })}
        >
          <Text style={styles.generateAppliedControlText}>-</Text>
        </Pressable>
        <Text style={styles.generateAppliedOpacityText}>
          농도 {controls.opacity.toFixed(2)}
        </Text>
        <Pressable
          accessibilityRole="button"
          testID="generated-mask-opacity-plus"
          style={styles.generateAppliedControlButton}
          onPress={() => onChangeControls({ opacity: controls.opacity + 0.1 })}
        >
          <Text style={styles.generateAppliedControlText}>+</Text>
        </Pressable>
      </View>
    </View>
  );
}

function AlignmentGatePill({ gate }: { gate: E7AlignmentGate }) {
  const mark =
    gate.state === 'ready' ? '✓' : gate.state === 'blocked' ? '!' : '…';

  return (
    <View
      style={[
        styles.generateWizardCheckItem,
        gate.state === 'ready' && styles.generateWizardCheckItemReady,
        gate.state === 'blocked' && styles.generateWizardCheckItemBlocked,
      ]}
    >
      <Text style={styles.generateWizardCheckMark}>{mark}</Text>
      <Text style={styles.generateWizardCheckText}>{gate.label}</Text>
      <Text style={styles.generateWizardCheckMeta}>{gate.value}</Text>
    </View>
  );
}

function ApplyGatePill({
  label,
  value,
  ready,
}: {
  label: string;
  value: string;
  ready: boolean;
}) {
  return (
    <View
      style={[
        styles.generateWizardApplyGate,
        ready && styles.generateWizardApplyGateReady,
      ]}
    >
      <Text style={styles.generateWizardApplyGateLabel}>{label}</Text>
      <Text style={styles.generateWizardApplyGateValue}>{value}</Text>
    </View>
  );
}

function formatGeneratedApplyUserMessage(state: E7GeneratedApplyState) {
  switch (state.status) {
    case 'idle':
      return 'AR 실행을 준비합니다.';
    case 'saving':
      return '마스크를 기기에 저장하는 중입니다.';
    case 'posting':
      return 'AR 화면에 마스크를 보내는 중입니다.';
    case 'waitingAck':
      return 'AR 화면에서 적용 여부를 확인하는 중입니다.';
    case 'applied':
      return 'AR 화면에 마스크가 적용되었습니다.';
    case 'blocked':
      return 'AR 적용을 확인하지 못했습니다.';
    case 'timeout':
      return 'AR 적용 응답이 늦습니다.';
  }
}

function formatGeneratedApplyRecoveryMessage(state: E7GeneratedApplyState) {
  if (state.status === 'timeout') {
    return '다시 시도하거나 촬영부터 다시 진행할 수 있습니다.';
  }
  return '다시 시도해도 안 되면 촬영부터 다시 진행해 주세요.';
}

function formatGeneratedApplyBlockedNotice(reason: string) {
  if (reason === 'generatedMaskId_mismatch') {
    return '이전 마스크 응답이 도착했습니다. 현재 마스크로 다시 적용해 주세요.';
  }
  if (reason.toLowerCase().includes('timeout')) {
    return 'AR 적용 응답이 늦습니다. 다시 시도하거나 촬영부터 다시 진행할 수 있습니다.';
  }
  return 'AR 적용을 확인하지 못했습니다. 다시 시도하거나 촬영부터 다시 진행해 주세요.';
}

function GeneratedAdjustmentPreview({
  candidate,
  selectedCandidateKey,
}: {
  candidate?: E7GeneratedCandidateWithPreview;
  selectedCandidateKey: string;
}) {
  return (
    <View style={styles.generatedAdjustmentPreview}>
      {candidate?.previewUri ? (
        <Image
          source={{ uri: candidate.previewUri }}
          style={styles.generatedAdjustmentPreviewImage}
        />
      ) : (
      <View style={styles.generatedAdjustmentPreviewEmpty}>
        <Text style={styles.generatedAdjustmentPreviewTitle}>
            마스크 미리보기 대기
          </Text>
          <Text style={styles.generatedAdjustmentPreviewText}>
            {candidate
              ? formatCandidatePreviewStatus(candidate)
              : '후보를 먼저 생성하세요.'}
          </Text>
        </View>
      )}
      <View style={styles.generatedAdjustmentMaskBadge}>
        <Text style={styles.generatedAdjustmentMaskBadgeText}>
          {candidate
            ? `${formatProviderLabel(candidate.provider)} · ${formatGeneratedCandidateTitle(
                candidate,
              )}`
            : selectedCandidateKey}
        </Text>
      </View>
      <Text style={styles.generatedAdjustmentPreviewCaption}>
        전체 얼굴 기준 마스크 미리보기
      </Text>
    </View>
  );
}

function formatProviderLabel(provider: GeneratedLipMaskProvider) {
  return (
    LIP_GENERATE_PROVIDER_OPTIONS.find(option => option.name === provider)
      ?.label ?? provider
  );
}

function formatLipFinishLabel(finish: LipFinish) {
  switch (finish) {
    case 'matte':
      return '매트';
    case 'cream':
      return '크림';
    case 'gloss':
      return '글로스';
  }
}

function formatGeneratedCandidateTitle(candidate: E7GeneratedCandidate) {
  if (candidate.expressionMode === 'blendshapeAssist') {
    return '표정 보조';
  }
  return '기본 블렌딩';
}

function formatGeneratedCandidateMeta(candidate: E7GeneratedCandidateWithPreview) {
  if (candidate.previewStatus === 'blocked' || candidate.status === 'blocked') {
    return '생성 실패';
  }
  return `${formatProviderLabel(candidate.provider)} 후보`;
}

function formatGeneratedCandidateDescription(
  candidate: E7GeneratedCandidateWithPreview,
) {
  if (candidate.previewStatus === 'blocked' || candidate.status === 'blocked') {
    return '다시 생성하거나 다른 방식을 선택하세요.';
  }
  if (candidate.expressionMode === 'blendshapeAssist') {
    return '표정 촬영 신호로 소재와 번짐 안정성을 보조합니다.';
  }
  return '기본 경계와 색감을 먼저 확인합니다.';
}

function formatCandidatePreviewStatus(
  candidate: E7GeneratedCandidateWithPreview,
) {
  if (candidate.previewStatus === 'ready') {
    return '마스크 미리보기 준비';
  }
  if (candidate.previewStatus === 'blocked') {
    return '미리보기를 만들 수 없습니다. 다시 생성해 주세요.';
  }
  return '마스크 미리보기 생성 중';
}

function formatProviderStatusLabel(status: string) {
  switch (status) {
    case 'ready':
      return '준비됨';
    case 'partial':
      return '부분 준비';
    case 'blocked':
      return '확인 필요';
    case 'pending':
      return '대기';
    case 'generated':
      return '생성됨';
    default:
      return status ? '확인 중' : '대기';
  }
}

function formatWizardStepLabel(step: E7WizardStep) {
  switch (step) {
    case 'start':
      return '시작';
    case 'align':
      return '정렬';
    case 'capture':
      return '촬영';
    case 'extract':
      return '추출';
    case 'blend':
      return '블렌딩 선택';
    case 'adjust':
      return '조정';
    case 'apply':
      return 'AR 실행';
  }
}

function formatWizardStepTitle(step: E7WizardStep) {
  switch (step) {
    case 'start':
      return '로컬 맞춤 생성';
    case 'align':
      return '얼굴 정렬';
    case 'capture':
      return '표정별 촬영';
    case 'extract':
      return '경계 추출';
    case 'blend':
      return '블렌딩 선택';
    case 'adjust':
      return '마스크 미세 조정';
    case 'apply':
      return '저장하고 AR 실행';
  }
}

type FaceLifecyclePanelProps = {
  event?: UnityEventPayload;
  receivedAt?: string;
};

function FaceLifecyclePanel({ event, receivedAt }: FaceLifecyclePanelProps) {
  const status = formatLifecycleStatus(event);

  return (
    <View style={styles.faceStatePanel}>
      <View style={styles.faceStateHeader}>
        <Text style={styles.faceStateLabel}>Face state</Text>
        <Text
          style={[
            styles.faceStateBadge,
            status === 'lost' && styles.faceStateBadgeLost,
            status === 'limited' && styles.faceStateBadgeLimited,
            status === 'reacquired' && styles.faceStateBadgeReacquired,
          ]}
        >
          {status}
        </Text>
      </View>
      <Text style={styles.faceStateText} numberOfLines={1}>
        {event
          ? `active=${formatLifecycleValue(
              event.selectedActiveFaceId,
            )} state=${formatLifecycleValue(
              event.trackingState,
            )} count=${String(event.faceCount ?? 'n/a')}/${String(
              event.totalTrackables ?? 'n/a',
            )}`
          : 'waiting for E2 lifecycle event'}
      </Text>
      <Text style={styles.faceStateText} numberOfLines={1}>
        {event
          ? `lastTracked=${formatLifecycleValue(
              event.lastTrackedFaceId,
            )} changed=${String(event.activeFaceChanged ?? false)}`
          : 'lastTracked=waiting'}
      </Text>
      <Text style={styles.faceStateText} numberOfLines={1}>
        {event
          ? `change +${String(event.addedCount ?? 0)} ~${String(
              event.updatedCount ?? 0,
            )} -${String(event.removedCount ?? 0)} phase=${formatLifecycleValue(
              event.phase,
            )}`
          : 'change +0 ~0 -0'}
      </Text>
      <Text style={styles.faceStateText} numberOfLines={1}>
        {event
          ? `mesh=${formatLifecycleValue(event.meshSummary)}`
          : 'mesh=waiting'}
      </Text>
      <Text style={styles.faceStateText} numberOfLines={1}>
        {event
          ? `caps=${formatLifecycleValue(event.providerCapabilitySnapshot)} ${
              receivedAt ?? ''
            }`
          : 'caps=waiting'}
      </Text>
    </View>
  );
}

type FaceFeatureSnapshotPanelProps = {
  event?: UnityEventPayload;
  receivedAt?: string;
};

function FaceFeatureSnapshotPanel({
  event,
  receivedAt,
}: FaceFeatureSnapshotPanelProps) {
  const rawFrameStored = readSnapshotPrivacyFlag(event, 'rawCameraFrameStored');
  const offDeviceUpload = readSnapshotPrivacyFlag(event, 'offDeviceUpload');

  return (
    <View style={styles.snapshotPanel}>
      <View style={styles.snapshotHeader}>
        <Text style={styles.snapshotLabel}>FaceFeatureSnapshot</Text>
        <Text
          style={[
            styles.snapshotBadge,
            rawFrameStored === false &&
              offDeviceUpload === false &&
              styles.snapshotBadgeGreen,
          ]}
        >
          {event ? 'received' : 'waiting'}
        </Text>
      </View>
      <Text style={styles.snapshotText} numberOfLines={1}>
        {event
          ? `schema=${String(event.schemaVersion ?? 'n/a')} ${String(
              event.lifecycleState ?? event.status ?? 'lost',
            )} face=${String(event.faceCount ?? 'n/a')}/${String(
              event.totalTrackables ?? 'n/a',
            )} camera=${String(event.cameraFacing ?? 'n/a')}`
          : 'waiting for E5 snapshot'}
      </Text>
      <Text style={styles.snapshotText} numberOfLines={1}>
        {event ? formatSnapshotMesh(event) : 'mesh=waiting'}
      </Text>
      <Text style={styles.snapshotText} numberOfLines={1}>
        {event
          ? `regions=${formatLifecycleValue(
              event.activeRegionSummary,
            )} samples=${formatLifecycleValue(
              event.appliedTextureSampleSummary,
            )}`
          : 'regions=waiting samples=waiting'}
      </Text>
      <Text style={styles.snapshotText} numberOfLines={1}>
        {event
          ? `rawFrameStored=${String(rawFrameStored)} upload=${String(
              offDeviceUpload,
            )} ${receivedAt ?? ''}`
          : 'rawFrameStored=false upload=false'}
      </Text>
    </View>
  );
}

type E7StatusPanelProps = {
  currentRegions: string;
  metricRecord?: UnityEventRecord;
  recipeRecord?: UnityEventRecord;
};

function E7StatusPanel({
  currentRegions,
  metricRecord,
  recipeRecord,
}: E7StatusPanelProps) {
  const metric = metricRecord?.parsed;
  const recipe = recipeRecord?.parsed;
  const latencyMs = getRecipeAckLatencyMs(recipe, recipeRecord?.receivedAtMs);

  return (
    <View style={styles.e7Panel}>
      <View style={styles.e7Header}>
        <Text style={styles.e7Label}>Diagnostics</Text>
        <Text
          style={[
            styles.e7Badge,
            metric?.type === 'e7_metric_sample' && styles.e7BadgeGreen,
          ]}
        >
          {metric ? 'metric' : 'waiting'}
        </Text>
      </View>
      <Text style={styles.e7Text} numberOfLines={1}>
        {metric
          ? `look=${String(
              metric.lookId ?? 'smooth_region_mask',
            )} active=${String(
              metric.activeRegionSummary ?? metric.activeRegions ?? currentRegions,
            )}`
          : `look=smooth_region_mask active=${currentRegions}`}
      </Text>
      <Text style={styles.e7Text} numberOfLines={1}>
        {metric
          ? `fps=${formatMetricNumber(
              metric.averageFps,
            )} frame=${formatMetricNumber(
              metric.averageFrameTimeMs,
            )}ms worst=${formatMetricNumber(
              metric.worstFrameTimeMs,
            )}ms sub20=${String(metric.sustainedSub20FpsObserved ?? false)}`
          : 'fps/frame-time waiting'}
      </Text>
      <Text style={styles.e7Text} numberOfLines={1}>
        {metric
          ? `memory=${String(
              metric.memoryMetricAvailable ?? false,
            )} alloc=${formatMetricNumber(
              metric.allocatedMemoryMb,
            )}MB reserved=${formatMetricNumber(metric.reservedMemoryMb)}MB`
          : 'memory waiting'}
      </Text>
      <Text style={styles.e7Text} numberOfLines={1}>
        {metric
          ? `thermal=${String(
              metric.thermalEvidenceType ?? 'manual-device-heat',
            )} heat=${String(
              metric.manualHeatObservation ?? 'not_recorded',
            )} warning=${String(metric.thermalWarningObserved ?? false)}`
          : 'thermal waiting'}
      </Text>
      <Text style={styles.e7Text} numberOfLines={1}>
        {metric
          ? `mask=${String(metric.maskSource ?? 'smooth_region_mask')} uv=${String(
              metric.regionUvAvailable ?? metric.uvAvailable ?? false,
            )} triangles=${String(
              metric.regionMaskTriangles ?? metric.maskTriangles ?? 'n/a',
            )}`
          : 'region metrics waiting'}
      </Text>
      <Text style={styles.e7Text} numberOfLines={1}>
        {metric || recipe
          ? `topology=${String(
              metric?.topologyAuditStatus ??
                recipe?.topologyAuditStatus ??
                'not_run',
            )}`
          : 'heuristic audit waiting'}
      </Text>
      <Text style={styles.e7Text} numberOfLines={1}>
        {recipe
          ? `latency=${formatMetricNumber(
              latencyMs,
            )}ms sent=${formatMetricNumber(recipe.sentAtMs, 0)} state=${String(
              recipe.stateAction ?? 'n/a',
            )} frame=${String(recipe.appliedFrame ?? 'n/a')} ${
              recipeRecord?.receivedAt ?? ''
            }`
          : 'latency waiting'}
      </Text>
    </View>
  );
}

type CompactEvidenceHudProps = {
  validationViewMode: ValidationViewMode;
  activeRegionSummary: string;
  focusedRegion: RecipeRegion;
  currentLipSample: LipSample;
  latestMetric?: UnityEventPayload;
  latestLifecycle?: UnityEventPayload;
  latestRecipe?: UnityEventPayload;
  recipeLatencyMs?: number;
};

function CompactEvidenceHud({
  validationViewMode,
  activeRegionSummary,
  focusedRegion,
  currentLipSample,
  latestMetric,
  latestLifecycle,
  latestRecipe,
  recipeLatencyMs,
}: CompactEvidenceHudProps) {
  if (validationViewMode === 'clean') {
    return null;
  }

  const trackingState = readTrackingState(latestLifecycle, latestMetric);
  const faceCount = readFaceCount(latestLifecycle, latestMetric);
  const meshCounts = formatMeshCountSummary(latestMetric);
  const stateAction = String(
    latestRecipe?.stateAction ?? latestMetric?.stateAction ?? 'waiting',
  );
  const lookId = String(latestRecipe?.lookId ?? currentLipSample.name);
  const finish = String(latestRecipe?.finish ?? currentLipSample.finish);

  return (
    <View
      style={[
        styles.compactHud,
        validationViewMode === 'full' && styles.compactHudFull,
      ]}
    >
      <View style={styles.compactHudHeader}>
        <Text style={styles.compactHudLabel}>AR Status</Text>
        <Text style={styles.compactHudBadge}>{validationViewMode}</Text>
      </View>
      <Text style={styles.compactHudText} numberOfLines={1}>
        {`look=${lookId} finish=${finish} active=${activeRegionSummary} focus=${focusedRegion}`}
      </Text>
      <Text style={styles.compactHudText} numberOfLines={1}>
        {`tracking=${trackingState} faces=${faceCount} mesh=${meshCounts}`}
      </Text>
      <Text style={styles.compactHudText} numberOfLines={1}>
        {`fps=${formatMetricNumber(
          latestMetric?.averageFps,
        )} frame=${formatMetricNumber(
          latestMetric?.averageFrameTimeMs,
        )}ms state=${stateAction} latency=${formatMetricNumber(
          recipeLatencyMs,
        )}ms`}
      </Text>
    </View>
  );
}

type EvidenceMetadataInput = {
  entryCount: number;
  mountedAt: string;
  validationViewMode: ValidationViewMode;
  selectedRendererMode: RendererMode;
  focusedRegion: RecipeRegion;
  activeRegions: ActiveRegionMap;
  selectedLipSample: LipSample;
  selectedLipRuntimeCandidate: LipRuntimeCandidate;
  lipUserAdjustment: LipUserAdjustment;
  latestMetric?: UnityEventPayload;
  latestLifecycle?: UnityEventPayload;
  latestRecipe?: UnityEventPayload;
  latestSnapshot?: UnityEventPayload;
  lastUnityEvent: UnityEventRecord | null;
};

function buildEvidenceMetadataLines({
  entryCount,
  mountedAt,
  validationViewMode,
  selectedRendererMode,
  focusedRegion,
  activeRegions,
  selectedLipSample,
  selectedLipRuntimeCandidate,
  lipUserAdjustment,
  latestMetric,
  latestLifecycle,
  latestRecipe,
  latestSnapshot,
  lastUnityEvent,
}: EvidenceMetadataInput) {
  const activeRegionSummary = formatActiveRegionSummary(activeRegions);
  const latencyMs = getRecipeAckLatencyMs(
    latestRecipe,
    latestRecipe?.receivedAtMs,
  );
  const meshSource = latestMetric ?? latestSnapshot;

  return [
    `evidenceMode=${E7_EVIDENCE_MODE} plan=${E7_BOUNDARY_PLAN_VERSION}`,
    `entry=${entryCount} mounted=${mountedAt} viewMode=${validationViewMode}`,
    `rendererMode=${selectedRendererMode} look=${selectedLipSample.name} finish=${selectedLipSample.finish}`,
    `candidateId=${selectedLipRuntimeCandidate.candidateId} maskTextureId=${selectedLipRuntimeCandidate.maskTextureId} maskThreshold=${selectedLipRuntimeCandidate.maskThreshold.toFixed(2)}`,
    `adjustment cornerReach=${lipUserAdjustment.cornerReach.toFixed(2)} upperLipTightness=${lipUserAdjustment.upperLipTightness.toFixed(2)} lowerLipTightness=${lipUserAdjustment.lowerLipTightness.toFixed(2)} verticalOffset=${lipUserAdjustment.verticalOffset.toFixed(2)}`,
    `activeRegions=${activeRegionSummary} focusRegion=${focusedRegion}`,
    `metricRegion=${formatLifecycleValue(
      latestMetric?.region,
    )}`,
    `trackingState=${readTrackingState(
      latestLifecycle,
      latestMetric,
    )} faceCount=${readFaceCount(latestLifecycle, latestMetric)}`,
    `mesh vertex=${formatMeshCountValue(
      meshSource,
      latestSnapshot,
      'vertex',
    )} index=${formatMeshCountValue(
      meshSource,
      latestSnapshot,
      'index',
    )} uv=${formatMeshCountValue(meshSource, latestSnapshot, 'uv')}`,
    `blendshapeFieldsUsed=${String(
      latestMetric?.blendshapeFieldsUsed ?? 'not_exposed_in_phase1_ui',
    )}`,
    `topology=${String(
      latestMetric?.topologyAuditStatus ??
        latestRecipe?.topologyAuditStatus ??
        'not_run',
    )}`,
    `fps=${formatMetricNumber(
      latestMetric?.averageFps,
    )} frameTimeMs=${formatMetricNumber(
      latestMetric?.averageFrameTimeMs,
    )} latencyMs=${formatMetricNumber(latencyMs)}`,
    `stateAction=${String(
      latestRecipe?.stateAction ?? latestMetric?.stateAction ?? 'waiting',
    )} visualDecisionNotes=pending_runtime_review`,
    `device=${String(
      latestSnapshot?.deviceModel ?? latestMetric?.deviceModel ?? 'n/a',
    )} orientation=${String(
      latestSnapshot?.orientation ?? latestMetric?.orientation ?? 'n/a',
    )}`,
    `evidenceKind=runtime_ui_overlay rawFrameStored=${String(
      readSnapshotPrivacyFlag(latestSnapshot, 'rawCameraFrameStored'),
    )} upload=${String(
      readSnapshotPrivacyFlag(latestSnapshot, 'offDeviceUpload'),
    )}`,
    `lastEvent=${
      lastUnityEvent
        ? `${lastUnityEvent.receivedAt} ${lastUnityEvent.displayText}`
        : 'waiting'
    }`,
  ];
}

function formatUnityEvent(event: UnityEventPayload) {
  switch (event.type) {
    case 'unity_initialized':
      return 'unity_initialized';
    case 'face_detected':
      return `face_detected tracked=${String(event.tracked)} faceCount=${String(
        event.faceCount,
      )}${formatFaceTrackingDetails(event)}`;
    case 'face_lifecycle':
      return `face_lifecycle ${formatFaceLifecycleSummary(event)}`;
    case 'face_feature_snapshot':
      return `face_feature_snapshot ${formatFaceFeatureSnapshotSummary(event)}`;
    case 'e7_metric_sample':
      return `e7_metric_sample ${formatE7MetricSummary(event)}`;
    case 'e7_reference_capture':
      return `e7_reference_capture ${formatE7ReferenceCaptureSummary(event)}`;
    case 'recipe_applied':
      return formatRecipeAppliedSummary(event);
    default:
      return event.type ? String(event.type) : 'unknown_unity_event';
  }
}

function getKnownUnityEventType(type: unknown): UnityEventType | null {
  if (typeof type !== 'string') {
    return null;
  }

  return UNITY_EVENT_TYPES.includes(type as UnityEventType)
    ? (type as UnityEventType)
    : null;
}

function formatUnityEventTypeStatus(
  type: UnityEventType,
  event?: UnityEventRecord,
) {
  if (!event?.parsed) {
    return `${type}: waiting`;
  }

  const parsed = event.parsed;

  switch (type) {
    case 'unity_initialized':
      return `unity_initialized: seen ${event.receivedAt}`;
    case 'face_detected':
      return `face_detected: tracked=${String(
        parsed.tracked,
      )} faceCount=${String(parsed.faceCount)}${formatFaceTrackingDetails(
        parsed,
      )} ${event.receivedAt}`;
    case 'face_lifecycle':
      return `face_lifecycle: ${formatFaceLifecycleSummary(parsed)} ${
        event.receivedAt
      }`;
    case 'face_feature_snapshot':
      return `face_feature_snapshot: ${formatFaceFeatureSnapshotSummary(
        parsed,
      )} ${event.receivedAt}`;
    case 'e7_metric_sample':
      return `e7_metric_sample: ${formatE7MetricSummary(parsed)} ${
        event.receivedAt
      }`;
    case 'e7_reference_capture':
      return `e7_reference_capture: ${formatE7ReferenceCaptureSummary(
        parsed,
      )} ${event.receivedAt}`;
    case 'recipe_applied':
      return `${formatRecipeAppliedSummary(parsed)} ${event.receivedAt}`;
  }
}

function formatE7ReferenceCaptureSummary(event: UnityEventPayload) {
  return `status=${String(event.status ?? 'unknown')} pair=${String(
    event.capturePairId ?? 'pair_face_0001',
  )} dir=${String(event.relativeDirectory ?? 'n/a')} mesh=${String(
    event.meshVertexCount ?? 'n/a',
  )}/${String(event.meshIndexCount ?? 'n/a')}/${String(
    event.meshUvCount ?? 'n/a',
  )} frameWidth=${String(event.frameWidth ?? 'n/a')} coordinate=${String(
    event.coordinateSpaceValidationStatus ??
      (event.coordinateSpaceValidated ? 'validated' : 'pending'),
  )}`;
}

function formatE7MetricSummary(event: UnityEventPayload) {
  return `fps=${formatMetricNumber(
    event.averageFps,
  )} frame=${formatMetricNumber(event.averageFrameTimeMs)}ms mem=${String(
    event.memoryMetricAvailable ?? false,
  )} thermal=${String(event.thermalEvidenceType ?? 'n/a')} phase=${String(
    event.phase ?? 'smooth_mask',
  )} mode=${String(event.rendererMode ?? 'smooth-region-mask')} look=${String(
    event.lookId ?? 'smooth_region_mask',
  )} active=${String(
    event.activeRegionSummary ?? event.activeRegions ?? 'n/a',
  )} enabled=${String(
    event.enabledLayerCount ?? 'n/a',
  )} topology=${String(
    event.topologyAuditStatus ?? 'not_run',
  )} uv=${String(event.regionUvAvailable ?? event.uvAvailable ?? false)}`;
}

function logE7RecipeLatency(event: UnityEventPayload, receivedAtMs: number) {
  const sentAtMs = readNumber(event.sentAtMs);
  const appliedAtMs = readNumber(event.appliedAtMs);
  const sendToAckLatencyMs =
    sentAtMs === undefined ? undefined : receivedAtMs - sentAtMs;

  console.log(
    '[E7] recipe_latency',
    `runId=${String(
      event.runId ?? `smooth-mask-rn-${new Date().toISOString().slice(0, 10)}`,
    )}`,
    `phase=${String(event.phase ?? 'smooth_mask')}`,
    `timestampMs=${receivedAtMs}`,
    `rendererMode=${String(event.rendererMode ?? 'smooth-region-mask')}`,
    `lookId=${String(event.lookId ?? 'smooth_region_mask')}`,
    `recipeId=${String(event.recipeId ?? 'none')}`,
    `recipeBatchId=${String(event.recipeBatchId ?? event.recipeId ?? 'none')}`,
    `activeRegions=${String(
      event.activeRegionSummary ?? event.activeRegions ?? 'none',
    )}`,
    `enabledLayerCount=${String(event.enabledLayerCount ?? 'n/a')}`,
    `payloadBytes=${String(event.payloadBytes ?? 'n/a')}`,
    `region=${String(event.region ?? event.layer ?? 'none')}`,
    `texture=${String(event.texture ?? event.sample ?? 'none')}`,
    `finish=${String(event.finish ?? 'n/a')}`,
    `textureAmount=${String(event.textureAmount ?? 'n/a')}`,
    `glossBoost=${String(event.glossBoost ?? 'n/a')}`,
    `coverage=${String(event.coverage ?? 'n/a')}`,
    `feather=${String(event.feather ?? 'n/a')}`,
    `sentAtMs=${formatMetricNumber(sentAtMs, 0)}`,
    `appliedAtMs=${formatMetricNumber(appliedAtMs, 0)}`,
    `appliedFrame=${String(event.appliedFrame ?? 'n/a')}`,
    `receivedAtMs=${receivedAtMs}`,
    `sendToAckLatencyMs=${formatMetricNumber(sendToAckLatencyMs)}`,
    'visualLatencyConfirmedByRecording=false',
    `visualLatencyObservation=${String(
      event.visualLatencyObservation ?? 'pending_recording_review',
    )}`,
  );
}

function getRecipeAckLatencyMs(
  event: UnityEventPayload | undefined,
  receivedAtMs: number | undefined,
) {
  const sentAtMs = readNumber(event?.sentAtMs);
  if (sentAtMs === undefined || receivedAtMs === undefined) {
    return undefined;
  }

  return receivedAtMs - sentAtMs;
}

function readTrackingState(
  lifecycleEvent?: UnityEventPayload,
  metricEvent?: UnityEventPayload,
) {
  return String(
    lifecycleEvent?.trackingState ??
      lifecycleEvent?.status ??
      metricEvent?.trackingState ??
      metricEvent?.status ??
      'waiting',
  );
}

function readFaceCount(
  lifecycleEvent?: UnityEventPayload,
  metricEvent?: UnityEventPayload,
) {
  return String(
    lifecycleEvent?.faceCount ??
      metricEvent?.faceCount ??
      lifecycleEvent?.totalTrackables ??
      metricEvent?.totalTrackables ??
      'n/a',
  );
}

function formatMeshCountSummary(event?: UnityEventPayload) {
  return `v=${formatMeshCountValue(
    event,
    undefined,
    'vertex',
  )}/i=${formatMeshCountValue(
    event,
    undefined,
    'index',
  )}/uv=${formatMeshCountValue(event, undefined, 'uv')}`;
}

function formatMeshCountValue(
  primaryEvent: UnityEventPayload | undefined,
  secondaryEvent: UnityEventPayload | undefined,
  key: 'vertex' | 'index' | 'uv',
) {
  const directKeys = {
    vertex: 'meshVertexCount',
    index: 'meshIndexCount',
    uv: 'meshUvCount',
  } as const;
  const nestedKeys = {
    vertex: 'vertexCount',
    index: 'indexCount',
    uv: 'uvCount',
  } as const;

  const directValue =
    primaryEvent?.[directKeys[key]] ?? secondaryEvent?.[directKeys[key]];
  const directNumber = readNumber(directValue);
  if (directNumber !== undefined) {
    return directNumber.toFixed(0);
  }

  const primaryMesh = asRecord(primaryEvent?.mesh);
  const secondaryMesh = asRecord(secondaryEvent?.mesh);
  const nestedValue =
    primaryMesh?.[nestedKeys[key]] ?? secondaryMesh?.[nestedKeys[key]];
  const nestedNumber = readNumber(nestedValue);

  return nestedNumber === undefined ? 'n/a' : nestedNumber.toFixed(0);
}

function readNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value)
    ? value
    : undefined;
}

function formatMetricNumber(value: unknown, fractionDigits = 1) {
  const numberValue = readNumber(value);
  if (numberValue === undefined) {
    return 'n/a';
  }

  return numberValue.toFixed(fractionDigits);
}

function formatFaceFeatureSnapshotSummary(event: UnityEventPayload) {
  return `${String(
    event.lifecycleState ?? event.status ?? 'lost',
  )} face=${String(event.faceCount ?? 'n/a')}/${String(
    event.totalTrackables ?? 'n/a',
  )} mesh=${formatSnapshotMesh(event)} regions=${formatLifecycleValue(
    event.activeRegionSummary,
  )} rawFrame=${String(
    readSnapshotPrivacyFlag(event, 'rawCameraFrameStored'),
  )} upload=${String(readSnapshotPrivacyFlag(event, 'offDeviceUpload'))}`;
}

function formatSnapshotMesh(event: UnityEventPayload) {
  const mesh = asRecord(event.mesh);
  const vertexCount = mesh?.vertexCount ?? 'n/a';
  const indexCount = mesh?.indexCount ?? 'n/a';
  const uvCount = mesh?.uvCount ?? 'n/a';
  const hasStableUv = mesh?.hasStableUv ?? 'n/a';

  return `mesh v=${String(vertexCount)} i=${String(indexCount)} uv=${String(
    uvCount,
  )} stableUv=${String(hasStableUv)}`;
}

function readSnapshotPrivacyFlag(
  event: UnityEventPayload | undefined,
  key: 'rawCameraFrameStored' | 'offDeviceUpload',
) {
  if (!event) {
    return false;
  }

  const directValue = event[key];
  if (typeof directValue === 'boolean') {
    return directValue;
  }

  const privacy = asRecord(event.privacy);
  const nestedValue = privacy?.[key];
  return typeof nestedValue === 'boolean' ? nestedValue : false;
}

function asRecord(value: unknown): Record<string, unknown> | undefined {
  if (value === null || typeof value !== 'object' || Array.isArray(value)) {
    return undefined;
  }

  return value as Record<string, unknown>;
}

function formatRecipeAppliedSummary(event?: UnityEventPayload) {
  if (!event) {
    return 'recipe_applied waiting';
  }

  const texture = String(event.texture ?? event.sample ?? 'none');
  const latencyMs = getRecipeAckLatencyMs(event, event.receivedAtMs);

  return `recipe_applied region=${String(
    event.region ?? event.layer,
  )} look=${String(event.lookId ?? 'n/a')} active=${String(
    event.activeRegionSummary ?? event.activeRegions ?? 'n/a',
  )} enabled=${String(
    event.enabledLayerCount ?? 'n/a',
  )} texture=${texture} mode=${String(
    event.textureMode ?? 'n/a',
  )} color=${String(event.color)} opacity=${String(
    event.opacity,
  )} intensity=${String(event.intensity ?? 'n/a')} applied=${String(
    event.applied ?? false,
  )} coverage=${String(event.coverage ?? 'n/a')} feather=${String(
    event.feather ?? 'n/a',
  )} finish=${String(event.finish ?? 'n/a')} textureAmount=${String(
    event.textureAmount ?? 'n/a',
  )} gloss=${String(event.glossBoost ?? 'n/a')} faceCount=${String(
    event.faceCount ?? 'n/a',
  )} meshTriangles=${String(
    event.meshTriangles ?? 'n/a',
  )} mask=${String(
    event.maskTriangles ?? event.regionMaskTriangles ?? 'n/a',
  )} uv=${String(event.uvAvailable ?? false)} state=${String(
    event.stateAction ?? 'n/a',
  )} topology=${String(
    event.topologyAuditStatus ?? 'not_run',
  )} latency=${formatMetricNumber(latencyMs)}ms`;
}

function formatFaceTrackingDetails(event: UnityEventPayload) {
  const details: string[] = [];

  if (typeof event.totalTrackables === 'number') {
    details.push(`total=${String(event.totalTrackables)}`);
  }

  if (typeof event.trackingStates === 'string' && event.trackingStates) {
    details.push(`states=${event.trackingStates}`);
  }

  return details.length > 0 ? ` ${details.join(' ')}` : '';
}

function formatFaceLifecycleSummary(event: UnityEventPayload) {
  return `${formatLifecycleStatus(event)} active=${formatLifecycleValue(
    event.selectedActiveFaceId,
  )} lastTracked=${formatLifecycleValue(
    event.lastTrackedFaceId,
  )} state=${formatLifecycleValue(event.trackingState)} faceCount=${String(
    event.faceCount ?? 'n/a',
  )}/${String(event.totalTrackables ?? 'n/a')} change=+${String(
    event.addedCount ?? 0,
  )}/~${String(event.updatedCount ?? 0)}/-${String(event.removedCount ?? 0)}`;
}

function formatLifecycleStatus(event?: UnityEventPayload) {
  const status = event?.status;

  if (
    status === 'tracking' ||
    status === 'limited' ||
    status === 'lost' ||
    status === 'reacquired'
  ) {
    return status;
  }

  return 'lost';
}

function formatLifecycleValue(value: unknown) {
  if (value === null || value === undefined || value === '') {
    return 'none';
  }

  return String(value);
}

function formatActiveRegionSummary(activeRegions: ActiveRegionMap) {
  const regions = RECIPE_REGION_OPTIONS.filter(region => activeRegions[region]);
  return regions.length === 0 ? 'none' : regions.join(',');
}

function countActiveRegions(activeRegions: ActiveRegionMap) {
  return RECIPE_REGION_OPTIONS.reduce(
    (count, region) => count + (activeRegions[region] ? 1 : 0),
    0,
  );
}

function buildReferenceCapturePairId(sequence: number, requestedAtMs: number) {
  const timestamp = new Date(requestedAtMs)
    .toISOString()
    .replace(/[-:]/g, '')
    .replace(/\.\d{3}Z$/, 'Z');

  return `pair_face_${timestamp}_${String(sequence).padStart(2, '0')}`;
}

type TuningSliderProps = {
  label: string;
  value: number;
  width: number;
  onLayoutWidth: (width: number) => void;
  onChange: (value: number) => void;
};

function TuningSlider({
  label,
  value,
  width,
  onLayoutWidth,
  onChange,
}: TuningSliderProps) {
  const clampedWidth = Math.max(width, 1);
  const fillWidth = value * clampedWidth;

  const valueFromEvent = useCallback(
    (event: GestureResponderEvent) => {
      const raw = Math.max(
        0,
        Math.min(event.nativeEvent.locationX, clampedWidth),
      );
      const steppedValue =
        Math.round(raw / clampedWidth / OPACITY_STEP) * OPACITY_STEP;

      return Number(Math.max(0, Math.min(1, steppedValue)).toFixed(2));
    },
    [clampedWidth],
  );

  const updateFromEvent = useCallback(
    (event: GestureResponderEvent) => {
      onChange(valueFromEvent(event));
    },
    [onChange, valueFromEvent],
  );
  const stepValue = useCallback(
    (direction: -1 | 1) => {
      const nextValue =
        Math.round((value + direction * OPACITY_STEP) / OPACITY_STEP) *
        OPACITY_STEP;

      onChange(Number(Math.max(0, Math.min(1, nextValue)).toFixed(2)));
    },
    [onChange, value],
  );

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onMoveShouldSetPanResponder: () => true,
        onStartShouldSetPanResponder: () => true,
        onPanResponderGrant: updateFromEvent,
        onPanResponderMove: updateFromEvent,
      }),
    [updateFromEvent],
  );

  const handleLayout = useCallback(
    (event: LayoutChangeEvent) => {
      onLayoutWidth(event.nativeEvent.layout.width);
    },
    [onLayoutWidth],
  );

  return (
    <View style={styles.opacityControl}>
      <View style={styles.opacityHeader}>
        <Text style={styles.opacityLabel}>{label}</Text>
        <Text style={styles.opacityValue}>{value.toFixed(2)}</Text>
      </View>
      <View style={styles.sliderControlRow}>
        <Pressable
          accessibilityRole="button"
          testID={`lip-tuning-step-${label}-down`}
          style={({ pressed }) => [
            styles.sliderStepButton,
            pressed && styles.colorButtonPressed,
          ]}
          onPress={() => stepValue(-1)}
        >
          <Text style={styles.sliderStepButtonText}>-</Text>
        </Pressable>
        <View
          accessibilityRole="adjustable"
          accessibilityValue={{ min: 0, max: 1, now: value }}
          style={styles.sliderTrack}
          onLayout={handleLayout}
          {...panResponder.panHandlers}
        >
          <View style={[styles.sliderFill, { width: fillWidth }]} />
          <View style={[styles.sliderThumb, { left: fillWidth }]} />
        </View>
        <Pressable
          accessibilityRole="button"
          testID={`lip-tuning-step-${label}-up`}
          style={({ pressed }) => [
            styles.sliderStepButton,
            pressed && styles.colorButtonPressed,
          ]}
          onPress={() => stepValue(1)}
        >
          <Text style={styles.sliderStepButtonText}>+</Text>
        </Pressable>
      </View>
    </View>
  );
}

type AdjustmentStepperProps = {
  label: string;
  value: number;
  onChange: (value: number) => void;
};

function AdjustmentStepper({ label, value, onChange }: AdjustmentStepperProps) {
  const stepValue = useCallback(
    (direction: -1 | 1) => {
      const nextValue =
        Math.round((value + direction * LIP_ADJUSTMENT_STEP) / LIP_ADJUSTMENT_STEP) *
        LIP_ADJUSTMENT_STEP;

      onChange(Number(Math.max(-1, Math.min(1, nextValue)).toFixed(2)));
    },
    [onChange, value],
  );

  return (
    <View style={styles.adjustmentStepper}>
      <View style={styles.opacityHeader}>
        <Text style={styles.opacityLabel}>{label}</Text>
        <Text style={styles.opacityValue}>{value.toFixed(2)}</Text>
      </View>
      <View style={styles.adjustmentStepperRow}>
        <Pressable
          accessibilityRole="button"
          testID={`lip-adjustment-step-${label}-down`}
          style={({ pressed }) => [
            styles.adjustmentStepButton,
            pressed && styles.colorButtonPressed,
          ]}
          onPress={() => stepValue(-1)}
        >
          <Text style={styles.adjustmentStepButtonText}>-</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          testID={`lip-adjustment-step-${label}-reset`}
          style={({ pressed }) => [
            styles.adjustmentResetButton,
            pressed && styles.colorButtonPressed,
          ]}
          onPress={() => onChange(0)}
        >
          <Text style={styles.adjustmentStepButtonText}>0</Text>
        </Pressable>
        <Pressable
          accessibilityRole="button"
          testID={`lip-adjustment-step-${label}-up`}
          style={({ pressed }) => [
            styles.adjustmentStepButton,
            pressed && styles.colorButtonPressed,
          ]}
          onPress={() => stepValue(1)}
        >
          <Text style={styles.adjustmentStepButtonText}>+</Text>
        </Pressable>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  home: {
    flex: 1,
    backgroundColor: '#F7F7F2',
    paddingHorizontal: 24,
    justifyContent: 'space-between',
  },
  homeBody: {
    gap: 12,
  },
  kicker: {
    color: '#28666E',
    fontSize: 14,
    fontWeight: '700',
    letterSpacing: 0,
  },
  title: {
    color: '#111827',
    fontSize: 30,
    fontWeight: '800',
    lineHeight: 36,
    letterSpacing: 0,
  },
  statusLabel: {
    color: '#5B5B5B',
    fontSize: 13,
    fontWeight: '700',
    marginTop: 16,
    letterSpacing: 0,
  },
  statusText: {
    color: '#1F2937',
    fontSize: 17,
    lineHeight: 24,
    letterSpacing: 0,
  },
  primaryButton: {
    minHeight: 54,
    borderRadius: 8,
    backgroundColor: '#D94B74',
    alignItems: 'center',
    justifyContent: 'center',
  },
  primaryButtonPressed: {
    opacity: 0.82,
  },
  primaryButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '800',
    letterSpacing: 0,
  },
  unityScreen: {
    flex: 1,
    backgroundColor: '#000000',
  },
  unityView: {
    flex: 1,
  },
  unityOverlay: {
    ...StyleSheet.absoluteFill,
    justifyContent: 'space-between',
    paddingHorizontal: 16,
  },
  topChrome: {
    alignItems: 'stretch',
    gap: 8,
  },
  topActionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  closeButton: {
    alignSelf: 'flex-start',
    minHeight: 44,
    minWidth: 84,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.72)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.42)',
  },
  closeButtonPressed: {
    opacity: 0.78,
  },
  closeButtonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '800',
    letterSpacing: 0,
  },
  productTitlePill: {
    alignSelf: 'stretch',
    minHeight: 42,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.58)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    paddingHorizontal: 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  productTitleText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 0,
  },
  productDebugButton: {
    minHeight: 32,
    minWidth: 72,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.14)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
  },
  productDebugButtonOn: {
    backgroundColor: '#1F2937',
    borderColor: '#FFFFFF',
  },
  productDebugButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardSheet: {
    alignSelf: 'stretch',
    justifyContent: 'flex-end',
  },
  generateWizardCard: {
    alignSelf: 'stretch',
    maxHeight: 440,
    borderRadius: 8,
    backgroundColor: 'rgba(8, 13, 24, 0.82)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    padding: 10,
    gap: 10,
  },
  generateWizardCardAdjust: {
    maxHeight: 700,
  },
  generateWizardStepRow: {
    flexDirection: 'row',
    gap: 6,
    paddingRight: 6,
  },
  generateWizardStepChip: {
    minHeight: 34,
    borderRadius: 8,
    paddingHorizontal: 10,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.22)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  generateWizardStepChipActive: {
    backgroundColor: '#D1FAE5',
    borderColor: '#FFFFFF',
  },
  generateWizardStepChipLocked: {
    opacity: 0.38,
  },
  generateWizardStepText: {
    color: '#F9FAFB',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardStepTextActive: {
    color: '#064E3B',
  },
  generateWizardHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 10,
  },
  generateWizardBackButton: {
    width: 50,
    minHeight: 34,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
  },
  generateWizardBackText: {
    color: '#F9FAFB',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardEyebrow: {
    color: '#5EEAD4',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardTitle: {
    color: '#F9FAFB',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 0,
    lineHeight: 24,
  },
  generateWizardMeta: {
    flex: 1,
    color: '#CBD5E1',
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 15,
    letterSpacing: 0,
    textAlign: 'right',
  },
  generateWizardBody: {
    gap: 10,
  },
  generateWizardBodyText: {
    color: '#E5E7EB',
    fontSize: 12,
    lineHeight: 17,
    fontWeight: '700',
    letterSpacing: 0,
  },
  generateWizardPrimaryButton: {
    minHeight: 42,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#D94B74',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.42)',
    paddingHorizontal: 10,
  },
  generateWizardActionButton: {
    flex: 1,
  },
  generateWizardSecondaryButton: {
    flex: 1,
    minHeight: 42,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(255, 255, 255, 0.10)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    paddingHorizontal: 10,
  },
  generateWizardButtonDisabled: {
    opacity: 0.42,
  },
  generateWizardPrimaryText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  generateWizardSecondaryText: {
    color: '#F9FAFB',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  generateWizardCheckGrid: {
    flexDirection: 'row',
    gap: 8,
  },
  generateWizardCheckItem: {
    flex: 1,
    minHeight: 44,
    borderRadius: 8,
    backgroundColor: 'rgba(20, 184, 166, 0.20)',
    borderWidth: 1,
    borderColor: 'rgba(94, 234, 212, 0.28)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  generateWizardCheckMark: {
    color: '#5EEAD4',
    fontSize: 15,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardCheckText: {
    color: '#F9FAFB',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardShotGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  generateWizardShotButton: {
    width: '31.9%',
    minHeight: 54,
    borderRadius: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  generateWizardShotButtonNext: {
    backgroundColor: 'rgba(234, 179, 8, 0.26)',
    borderColor: '#FDE68A',
  },
  generateWizardShotButtonDone: {
    backgroundColor: 'rgba(16, 185, 129, 0.34)',
    borderColor: '#A7F3D0',
  },
  generateWizardShotButtonBlocked: {
    backgroundColor: 'rgba(185, 28, 28, 0.30)',
    borderColor: '#FCA5A5',
  },
  generateWizardShotLabel: {
    color: '#FFFFFF',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardShotMeta: {
    color: '#CBD5E1',
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0,
    textAlign: 'center',
  },
  generateWizardProviderRow: {
    flexDirection: 'row',
    gap: 8,
  },
  generateWizardProviderPill: {
    flex: 1,
    minHeight: 54,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(94, 234, 212, 0.32)',
    backgroundColor: 'rgba(20, 184, 166, 0.18)',
    paddingHorizontal: 8,
    justifyContent: 'center',
  },
  generateWizardProviderPillBlocked: {
    borderColor: '#FCA5A5',
    backgroundColor: 'rgba(185, 28, 28, 0.22)',
  },
  generateWizardProviderPillSelected: {
    borderColor: '#D1FAE5',
    borderWidth: 2,
    backgroundColor: 'rgba(209, 250, 229, 0.22)',
  },
  generateWizardProviderLabel: {
    color: '#F9FAFB',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardProviderStatus: {
    color: '#CBD5E1',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
    marginTop: 2,
  },
  generateWizardCandidateGrid: {
    flexDirection: 'row',
    gap: 12,
    paddingRight: 4,
  },
  generateWizardCandidateCard: {
    width: 282,
    minHeight: 396,
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    overflow: 'hidden',
    justifyContent: 'space-between',
  },
  generateWizardCandidateCardSelected: {
    backgroundColor: 'rgba(209, 250, 229, 0.22)',
    borderColor: '#D1FAE5',
    borderWidth: 2,
  },
  generateWizardCandidateCardBlocked: {
    backgroundColor: 'rgba(185, 28, 28, 0.20)',
    borderColor: '#FCA5A5',
  },
  generateWizardCandidatePreview: {
    height: 286,
    overflow: 'hidden',
    backgroundColor: 'rgba(15, 23, 42, 0.84)',
  },
  generateWizardCandidatePreviewImage: {
    width: '100%',
    height: '100%',
    resizeMode: 'contain',
  },
  generateWizardCandidatePreviewEmpty: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 12,
  },
  generateWizardCandidateCopy: {
    minHeight: 108,
    padding: 12,
    gap: 5,
  },
  generateWizardCandidateTitle: {
    color: '#F9FAFB',
    fontSize: 17,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateWizardCandidateMeta: {
    color: '#5EEAD4',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  generateWizardCandidateReason: {
    color: '#CBD5E1',
    fontSize: 12,
    lineHeight: 15,
    fontWeight: '800',
    letterSpacing: 0,
  },
  generateWizardActionRow: {
    flexDirection: 'row',
    gap: 8,
  },
  capturedFrameShield: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: '#050812',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 24,
    overflow: 'hidden',
  },
  capturedFrameImage: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    width: '100%',
    height: '100%',
    resizeMode: 'contain',
  },
  capturedFrameScrim: {
    position: 'absolute',
    top: 0,
    right: 0,
    bottom: 0,
    left: 0,
    backgroundColor: 'rgba(6, 10, 18, 0.42)',
  },
  capturedFrameShieldTitle: {
    color: '#F9FAFB',
    fontSize: 22,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  capturedFrameShieldText: {
    marginTop: 8,
    color: '#CBD5E1',
    fontSize: 13,
    fontWeight: '800',
    lineHeight: 18,
    letterSpacing: 0,
    textAlign: 'center',
  },
  generatedAdjustmentPreview: {
    minHeight: 300,
    overflow: 'hidden',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  generatedAdjustmentPreviewImage: {
    width: '100%',
    height: 300,
    resizeMode: 'contain',
  },
  generatedAdjustmentPreviewEmpty: {
    minHeight: 300,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 14,
  },
  generatedAdjustmentPreviewTitle: {
    color: '#F9FAFB',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  generatedAdjustmentPreviewText: {
    marginTop: 5,
    color: '#CBD5E1',
    fontSize: 11,
    fontWeight: '700',
    lineHeight: 15,
    letterSpacing: 0,
    textAlign: 'center',
  },
  generatedAdjustmentMaskBadge: {
    position: 'absolute',
    left: 10,
    right: 10,
    bottom: 10,
    minHeight: 28,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: 'rgba(217, 75, 116, 0.86)',
  },
  generatedAdjustmentMaskBadgeText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generatedAdjustmentPreviewCaption: {
    position: 'absolute',
    right: 10,
    top: 10,
    overflow: 'hidden',
    borderRadius: 8,
    backgroundColor: 'rgba(15, 23, 42, 0.72)',
    color: '#FFFFFF',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  generateWizardApplyGateGrid: {
    flexDirection: 'row',
    gap: 8,
  },
  generateWizardApplyGate: {
    flex: 1,
    minHeight: 54,
    borderRadius: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.22)',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 4,
  },
  generateWizardApplyGateReady: {
    backgroundColor: 'rgba(16, 185, 129, 0.32)',
    borderColor: '#A7F3D0',
  },
  generateWizardApplyGateLabel: {
    color: '#F9FAFB',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  generateWizardApplyGateValue: {
    color: '#CBD5E1',
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0,
    textAlign: 'center',
    marginTop: 2,
  },
  captureDock: {
    alignSelf: 'stretch',
    marginBottom: 16,
  },
  captureButton: {
    alignSelf: 'stretch',
    minHeight: 44,
    minWidth: 0,
    borderRadius: 8,
    backgroundColor: 'rgba(217, 75, 116, 0.88)',
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.48)',
    paddingHorizontal: 8,
  },
  captureButtonPending: {
    backgroundColor: 'rgba(55, 65, 81, 0.88)',
  },
  captureButtonText: {
    color: '#FFFFFF',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  viewModeRow: {
    minHeight: 40,
    flexDirection: 'row',
    justifyContent: 'flex-start',
    gap: 6,
  },
  viewModeButton: {
    flex: 1,
    minHeight: 40,
    minWidth: 0,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(0, 0, 0, 0.54)',
    paddingHorizontal: 8,
  },
  viewModeButtonSelected: {
    backgroundColor: '#F9FAFB',
    borderColor: '#FFFFFF',
  },
  viewModeButtonText: {
    color: '#F9FAFB',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  viewModeButtonTextSelected: {
    color: '#111827',
  },
  compactHud: {
    alignSelf: 'stretch',
    borderRadius: 6,
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.16)',
    paddingHorizontal: 8,
    paddingVertical: 5,
    gap: 1,
  },
  compactHudFull: {
    backgroundColor: 'rgba(255, 255, 255, 0.05)',
  },
  compactHudHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  compactHudLabel: {
    color: '#D1FAE5',
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0,
  },
  compactHudBadge: {
    color: '#111827',
    backgroundColor: '#FDE68A',
    borderRadius: 6,
    overflow: 'hidden',
    paddingHorizontal: 6,
    paddingVertical: 2,
    fontSize: 8,
    fontWeight: '900',
    letterSpacing: 0,
  },
  compactHudText: {
    color: '#F9FAFB',
    fontSize: 9,
    lineHeight: 12,
    letterSpacing: 0,
  },
  debugPanel: {
    position: 'absolute',
    left: 16,
    right: 16,
    bottom: 16,
    maxHeight: 220,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.68)',
    paddingHorizontal: 10,
    paddingVertical: 8,
    overflow: 'hidden',
    zIndex: 3,
  },
  debugMetaText: {
    color: '#FDE68A',
    fontSize: 10,
    lineHeight: 14,
    fontWeight: '800',
    letterSpacing: 0,
    marginBottom: 4,
  },
  debugLabel: {
    color: '#D1FAE5',
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0,
    marginBottom: 4,
    textTransform: 'uppercase',
  },
  debugText: {
    color: '#F9FAFB',
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0,
  },
  generateWizardCheckItemReady: {
    backgroundColor: 'rgba(22, 101, 52, 0.48)',
    borderColor: 'rgba(187, 247, 208, 0.64)',
  },
  generateWizardCheckItemBlocked: {
    backgroundColor: 'rgba(127, 29, 29, 0.38)',
    borderColor: 'rgba(254, 202, 202, 0.58)',
  },
  generateWizardCheckMeta: {
    color: '#D1D5DB',
    fontSize: 9,
    lineHeight: 12,
    fontWeight: '700',
    letterSpacing: 0,
    marginTop: 2,
  },
  faceStatePanel: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.18)',
    marginTop: 6,
    paddingTop: 6,
    gap: 2,
  },
  faceStateHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  faceStateLabel: {
    color: '#FDE68A',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  faceStateBadge: {
    color: '#DCFCE7',
    backgroundColor: 'rgba(22, 101, 52, 0.82)',
    borderRadius: 8,
    overflow: 'hidden',
    paddingHorizontal: 8,
    paddingVertical: 2,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
  },
  faceStateBadgeLost: {
    color: '#FEE2E2',
    backgroundColor: 'rgba(153, 27, 27, 0.82)',
  },
  faceStateBadgeLimited: {
    color: '#FEF3C7',
    backgroundColor: 'rgba(146, 64, 14, 0.82)',
  },
  faceStateBadgeReacquired: {
    color: '#DBEAFE',
    backgroundColor: 'rgba(30, 64, 175, 0.82)',
  },
  faceStateText: {
    color: '#E5E7EB',
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 0,
  },
  snapshotPanel: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.18)',
    marginTop: 6,
    paddingTop: 6,
    gap: 2,
  },
  snapshotHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  snapshotLabel: {
    color: '#BAE6FD',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
  },
  snapshotBadge: {
    color: '#E5E7EB',
    backgroundColor: 'rgba(75, 85, 99, 0.82)',
    borderRadius: 8,
    overflow: 'hidden',
    paddingHorizontal: 8,
    paddingVertical: 2,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
  },
  snapshotBadgeGreen: {
    color: '#DCFCE7',
    backgroundColor: 'rgba(22, 101, 52, 0.82)',
  },
  snapshotText: {
    color: '#E5E7EB',
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 0,
  },
  e7Panel: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.18)',
    marginTop: 6,
    paddingTop: 6,
    gap: 2,
  },
  e7Header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  e7Label: {
    color: '#FBCFE8',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  e7Badge: {
    color: '#E5E7EB',
    backgroundColor: 'rgba(75, 85, 99, 0.82)',
    borderRadius: 8,
    overflow: 'hidden',
    paddingHorizontal: 8,
    paddingVertical: 2,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
  },
  e7BadgeGreen: {
    color: '#DCFCE7',
    backgroundColor: 'rgba(22, 101, 52, 0.82)',
  },
  e7Text: {
    color: '#E5E7EB',
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 0,
  },
  debugStatus: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.18)',
    marginTop: 6,
    paddingTop: 6,
    gap: 2,
  },
  debugSubLabel: {
    color: '#BAE6FD',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  debugHistory: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.18)',
    marginTop: 6,
    paddingTop: 6,
    gap: 2,
  },
  debugHistoryText: {
    color: '#E5E7EB',
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 0,
  },
  recipePanel: {
    alignSelf: 'stretch',
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.72)',
    paddingHorizontal: 12,
    paddingVertical: 12,
    gap: 12,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.22)',
  },
  recipePanelCompact: {
    paddingHorizontal: 10,
    paddingVertical: 8,
    gap: 8,
  },
  recipePanelHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  recipePanelLabel: {
    color: '#FDE68A',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  recipePanelMetaText: {
    flex: 1,
    color: '#F9FAFB',
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 0,
    textAlign: 'right',
  },
  generateControlBlock: {
    gap: 6,
  },
  modeButtonRow: {
    flexDirection: 'row',
    gap: 8,
  },
  modeButton: {
    flex: 1,
    minHeight: 34,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(15, 23, 42, 0.82)',
  },
  modeButtonSelected: {
    backgroundColor: '#D1FAE5',
    borderColor: '#ECFDF5',
  },
  modeButtonText: {
    color: '#F9FAFB',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  modeButtonTextSelected: {
    color: '#064E3B',
  },
  generatedMaskButton: {
    minHeight: 34,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 12,
    borderWidth: 1,
    borderColor: '#E7F0FF',
    backgroundColor: '#E7F0FF',
  },
  generatedMaskButtonText: {
    color: '#08111F',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  generateAppliedBanner: {
    position: 'absolute',
    left: 18,
    right: 18,
    bottom: 22,
    borderRadius: 8,
    backgroundColor: 'rgba(15, 23, 42, 0.74)',
    borderWidth: 1,
    borderColor: 'rgba(187, 247, 208, 0.52)',
    paddingHorizontal: 14,
    paddingVertical: 12,
    zIndex: 2,
  },
  generateAppliedHeader: {
    minHeight: 40,
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 10,
  },
  generateAppliedBannerTitle: {
    color: '#D1FAE5',
    fontSize: 16,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateAppliedBannerText: {
    marginTop: 3,
    color: '#F9FAFB',
    fontSize: 13,
    lineHeight: 18,
    fontWeight: '700',
    letterSpacing: 0,
  },
  generateAppliedSmallButton: {
    minHeight: 40,
    minWidth: 92,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(209, 250, 229, 0.72)',
    backgroundColor: 'rgba(209, 250, 229, 0.18)',
    paddingHorizontal: 10,
  },
  generateAppliedSmallButtonText: {
    color: '#D1FAE5',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
  },
  generateAppliedControlRow: {
    marginTop: 8,
    minHeight: 42,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  generateAppliedControlButton: {
    flex: 1,
    minHeight: 42,
    minWidth: 0,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 8,
  },
  generateAppliedControlButtonActive: {
    borderColor: '#D1FAE5',
    backgroundColor: 'rgba(209, 250, 229, 0.24)',
  },
  generateAppliedControlText: {
    color: '#F9FAFB',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  generateAppliedColorRow: {
    marginTop: 8,
    minHeight: 42,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  generateAppliedColorButton: {
    flex: 1,
    minHeight: 42,
    minWidth: 0,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.22)',
    paddingHorizontal: 8,
  },
  generateAppliedColorButtonSelected: {
    borderColor: '#FFFFFF',
    borderWidth: 2,
  },
  generateAppliedColorText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  generateAppliedOpacityText: {
    flex: 1.35,
    minHeight: 42,
    borderRadius: 8,
    overflow: 'hidden',
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    color: '#F9FAFB',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
    lineHeight: 42,
    textAlign: 'center',
  },
  regionButtonRow: {
    flexDirection: 'row',
    gap: 8,
  },
  regionButton: {
    flex: 1,
    minHeight: 36,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
  },
  regionButtonSelected: {
    backgroundColor: '#F9FAFB',
    borderColor: '#FFFFFF',
  },
  regionButtonFocused: {
    borderColor: '#FDE68A',
    borderWidth: 2,
  },
  regionButtonText: {
    color: '#F9FAFB',
    fontSize: 13,
    fontWeight: '900',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  regionButtonTextSelected: {
    color: '#111827',
  },
  colorButtonRow: {
    flexDirection: 'row',
    gap: 8,
  },
  colorButton: {
    flex: 1,
    minHeight: 42,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
  },
  colorButtonSelected: {
    borderColor: '#FFFFFF',
    borderWidth: 2,
  },
  colorButtonPressed: {
    opacity: 0.8,
  },
  colorButtonText: {
    color: '#FFFFFF',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  lipSampleButtonRow: {
    flexDirection: 'row',
    gap: 8,
  },
  lipSampleButton: {
    flex: 1,
    minHeight: 48,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(248, 113, 113, 0.18)',
    paddingHorizontal: 4,
  },
  lipSampleButtonSelected: {
    backgroundColor: '#FCE7F3',
    borderColor: '#FFFFFF',
    borderWidth: 2,
  },
  lipSampleButtonText: {
    color: '#F9FAFB',
    fontSize: 12,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  lipSampleButtonMetaText: {
    color: '#FBCFE8',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
    marginTop: 2,
    textTransform: 'uppercase',
  },
  lipSampleButtonTextSelected: {
    color: '#831843',
  },
  lipRuntimeCandidateRow: {
    flexDirection: 'row',
    gap: 6,
    paddingRight: 6,
  },
  lipRuntimeCandidateButton: {
    minWidth: 72,
    minHeight: 42,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(20, 83, 45, 0.24)',
    paddingHorizontal: 4,
  },
  lipRuntimeCandidateButtonSelected: {
    backgroundColor: '#D1FAE5',
    borderColor: '#FFFFFF',
    borderWidth: 2,
  },
  lipRuntimeCandidateText: {
    color: '#F9FAFB',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  lipRuntimeCandidateMetaText: {
    color: '#BBF7D0',
    fontSize: 8,
    fontWeight: '800',
    letterSpacing: 0,
    marginTop: 2,
    textAlign: 'center',
  },
  lipRuntimeCandidateTextSelected: {
    color: '#064E3B',
  },
  adjustmentFieldButtonRow: {
    flexDirection: 'row',
    gap: 6,
  },
  adjustmentFieldButton: {
    flex: 1,
    minHeight: 32,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    backgroundColor: 'rgba(59, 130, 246, 0.18)',
    paddingHorizontal: 3,
  },
  adjustmentFieldButtonSelected: {
    backgroundColor: '#DBEAFE',
    borderColor: '#FFFFFF',
    borderWidth: 2,
  },
  adjustmentFieldButtonText: {
    color: '#EFF6FF',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  adjustmentFieldButtonTextSelected: {
    color: '#1E3A8A',
  },
  adjustmentStepper: {
    gap: 6,
  },
  adjustmentStepperRow: {
    flexDirection: 'row',
    gap: 8,
  },
  adjustmentStepButton: {
    flex: 1,
    minHeight: 34,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.32)',
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
  },
  adjustmentResetButton: {
    flex: 1,
    minHeight: 34,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.32)',
    backgroundColor: 'rgba(15, 23, 42, 0.22)',
  },
  adjustmentStepButtonText: {
    color: '#F9FAFB',
    fontSize: 14,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  textureButtonRow: {
    flexDirection: 'row',
    gap: 8,
  },
  textureButton: {
    flex: 1,
    minHeight: 48,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 4,
  },
  textureButtonCurrentRegion: {
    borderColor: '#FDE68A',
  },
  textureButtonSelected: {
    backgroundColor: '#F9FAFB',
    borderColor: '#FFFFFF',
    borderWidth: 2,
  },
  textureButtonText: {
    color: '#F9FAFB',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  textureButtonRegionText: {
    color: '#BAE6FD',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
    marginTop: 2,
    textTransform: 'uppercase',
  },
  textureButtonTextSelected: {
    color: '#111827',
  },
  tuningFieldButtonRow: {
    flexDirection: 'row',
    gap: 6,
  },
  tuningFieldButton: {
    flex: 1,
    minHeight: 32,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.26)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 2,
  },
  tuningFieldButtonSelected: {
    backgroundColor: '#FDE68A',
    borderColor: '#FFFFFF',
    borderWidth: 2,
  },
  tuningFieldButtonText: {
    color: '#F9FAFB',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  tuningFieldButtonTextSelected: {
    color: '#111827',
  },
  opacityControl: {
    gap: 8,
  },
  opacityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  opacityLabel: {
    color: '#F9FAFB',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 0,
  },
  opacityValue: {
    color: '#F9FAFB',
    fontSize: 14,
    fontWeight: '800',
    letterSpacing: 0,
  },
  sliderControlRow: {
    minHeight: 32,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  sliderStepButton: {
    width: 32,
    height: 32,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.32)',
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
  },
  sliderStepButtonText: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '900',
    letterSpacing: 0,
    lineHeight: 22,
  },
  sliderTrack: {
    flex: 1,
    height: 32,
    borderRadius: 8,
    backgroundColor: 'rgba(255, 255, 255, 0.24)',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  sliderFill: {
    position: 'absolute',
    bottom: 0,
    left: 0,
    top: 0,
    backgroundColor: '#D94B74',
  },
  sliderThumb: {
    position: 'absolute',
    width: 22,
    height: 22,
    borderRadius: 8,
    marginLeft: -11,
    backgroundColor: '#FFFFFF',
    borderWidth: 2,
    borderColor: '#111827',
  },
  recipeValueText: {
    color: '#F9FAFB',
    fontSize: 13,
    lineHeight: 18,
    letterSpacing: 0,
  },
  recipeAppliedText: {
    color: '#BAE6FD',
    fontSize: 11,
    lineHeight: 15,
    letterSpacing: 0,
  },
});

export default App;
