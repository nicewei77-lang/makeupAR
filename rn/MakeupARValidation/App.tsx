import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import {
  GestureResponderEvent,
  LayoutChangeEvent,
  LogBox,
  PanResponder,
  Pressable,
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

LogBox.ignoreAllLogs(true);

export const RECIPE_COLOR_OPTIONS = [
  { name: 'rose', label: 'rose', color: '#D94B74' },
  { name: 'coral', label: 'coral', color: '#E67B5F' },
  { name: 'nude', label: 'nude', color: '#B9826B' },
  { name: 'berry', label: 'berry', color: '#A8325F' },
  { name: 'red', label: 'red', color: '#C21F3A' },
  { name: 'pale_pink', label: 'pale pink', color: '#ECC4CB' },
] as const;
export const EYEBROW_COLOR_OPTIONS = [
  { name: 'black', label: 'black', color: '#171412' },
  { name: 'dark_brown', label: 'dark brown', color: '#3B2A22' },
  { name: 'brown', label: 'brown', color: '#6B4A34' },
  { name: 'light_brown', label: 'light brown', color: '#8B6447' },
  { name: 'wine', label: 'wine', color: '#6A243B' },
] as const;

const CORE_RECIPE_REGION_OPTIONS = ['lip', 'cheek', 'eye'] as const;
const RECIPE_REGION_OPTIONS = [...CORE_RECIPE_REGION_OPTIONS, 'eyebrow'] as const;
export const RECIPE_TEXTURE_SAMPLE_OPTIONS = [
  {
    name: 'matte_lip',
    label: 'matte lip',
    region: 'lip',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#F29BAA',
    intensity: 0.92,
    feather: 0.23,
    coverage: 0.94,
    finish: 'matte',
    roughness: 1,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0.02,
    preserveDetail: true,
  },
  {
    name: 'gloss_lip',
    label: 'gloss lip',
    region: 'lip',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#F29BAA',
    intensity: 0.92,
    feather: 0.23,
    coverage: 0.94,
    finish: 'gloss',
    roughness: 0.26,
    specular: 0.78,
    specularPower: 36,
    glossBoost: 0.68,
    gradientAmount: 0.02,
    preserveDetail: true,
  },
  {
    name: 'full_lip',
    label: 'full lip',
    region: 'lip',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#E06482',
    intensity: 0.74,
    feather: 0.24,
    coverage: 0.74,
    finish: 'satin',
    roughness: 0.46,
    specular: 0.14,
    specularPower: 16,
    glossBoost: 0.06,
    gradientAmount: 0.04,
    preserveDetail: true,
  },
  {
    name: 'gradient_lip',
    label: 'gradient lip',
    region: 'lip',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#EC8FA0',
    intensity: 0.92,
    feather: 0.38,
    coverage: 0.94,
    finish: 'gradient',
    roughness: 1,
    specular: 0.02,
    specularPower: 12,
    glossBoost: 0,
    gradientAmount: 1,
    preserveDetail: true,
  },
  {
    name: 'overline_lip',
    label: 'overline lip',
    region: 'lip',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#D94B74',
    intensity: 0.5,
    feather: 0.24,
    coverage: 0.42,
    finish: 'overline',
    roughness: 0.44,
    specular: 0.1,
    specularPower: 18,
    glossBoost: 0.04,
    gradientAmount: 0.18,
    preserveDetail: true,
  },
  {
    name: 'soft_blush',
    label: 'soft blush',
    region: 'cheek',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#F2A59A',
    intensity: 0.82,
    feather: 0.86,
    coverage: 0.84,
    finish: 'powder',
    roughness: 0.92,
    specular: 0.02,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'blush_session_1',
    label: 'Daily',
    region: 'cheek',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#F2A59A',
    intensity: 0.76,
    feather: 0.86,
    coverage: 0.78,
    finish: 'powder',
    roughness: 0.96,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'blush_session_2',
    label: 'Lovely',
    region: 'cheek',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#F3A1A6',
    intensity: 0.76,
    feather: 0.88,
    coverage: 0.78,
    finish: 'powder',
    roughness: 0.96,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'blush_session_3',
    label: 'Under eye',
    region: 'cheek',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#F0A0B0',
    intensity: 0.76,
    feather: 0.84,
    coverage: 0.78,
    finish: 'powder',
    roughness: 0.98,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'blush_session_4',
    label: 'Sun 1',
    region: 'cheek',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#EFA07F',
    intensity: 0.76,
    feather: 0.86,
    coverage: 0.78,
    finish: 'powder',
    roughness: 0.98,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'blush_session_5',
    label: 'Sun 2',
    region: 'cheek',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#EAA07A',
    intensity: 0.76,
    feather: 0.88,
    coverage: 0.78,
    finish: 'powder',
    roughness: 0.98,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'shimmer_eye',
    label: 'shimmer eye',
    region: 'eye',
    textureMode: 'sample',
    blendMode: 'screen',
    secondaryColor: '#F8D6B3',
    intensity: 0.64,
    feather: 0.38,
    coverage: 1,
    finish: 'shimmer',
    roughness: 0.5,
    specular: 0.18,
    specularPower: 22,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'eyebrow_candidate_1',
    label: 'soft arch',
    region: 'eyebrow',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#6C5043',
    intensity: 0.82,
    feather: 0.34,
    coverage: 0.9,
    finish: 'brow',
    roughness: 1,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'eyebrow_candidate_2',
    label: 'straight',
    region: 'eyebrow',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#6C5043',
    intensity: 0.82,
    feather: 0.34,
    coverage: 0.9,
    finish: 'brow',
    roughness: 1,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
  {
    name: 'eyebrow_candidate_3',
    label: 'slim tail',
    region: 'eyebrow',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#6C5043',
    intensity: 0.82,
    feather: 0.34,
    coverage: 0.9,
    finish: 'brow',
    roughness: 1,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
] as const;
const VALIDATION_VIEW_MODE_OPTIONS = [
  { name: 'clean', label: 'Clean' },
  { name: 'compact', label: 'HUD' },
  { name: 'full', label: 'Debug' },
] as const;
const E7_BOUNDARY_PLAN_VERSION = 'E7.03 v2.1';
const E7_EVIDENCE_MODE = 'cheek-blush-validation-v1';
const E7_LOOK_ID = 'cheek_blush_validation_v1';
const E7_RECIPE_PREFIX = 'cheek-blush-v1';

export type RecipeColor =
  | (typeof RECIPE_COLOR_OPTIONS)[number]
  | (typeof EYEBROW_COLOR_OPTIONS)[number];
export type CoreRecipeRegion = (typeof CORE_RECIPE_REGION_OPTIONS)[number];
export type RecipeRegion = (typeof RECIPE_REGION_OPTIONS)[number];
export type RecipeTextureSample =
  (typeof RECIPE_TEXTURE_SAMPLE_OPTIONS)[number];
export const LIP_TEXTURE_STYLE_OPTIONS: RecipeTextureSample[] =
  RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureSample =>
      textureSample.region === 'lip' &&
      (textureSample.name === 'matte_lip' ||
        textureSample.name === 'gloss_lip' ||
        textureSample.name === 'gradient_lip'),
  );
export const CHEEK_BLUSH_REGION_OPTIONS: RecipeTextureSample[] =
  RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureSample =>
      textureSample.region === 'cheek' &&
      (textureSample.name === 'blush_session_1' ||
        textureSample.name === 'blush_session_2' ||
        textureSample.name === 'blush_session_3' ||
        textureSample.name === 'blush_session_4' ||
        textureSample.name === 'blush_session_5'),
  );
const TEXTURE_STYLE_OPTIONS_BY_REGION: Record<
  RecipeRegion,
  RecipeTextureSample[]
> = {
  lip: LIP_TEXTURE_STYLE_OPTIONS,
  cheek: CHEEK_BLUSH_REGION_OPTIONS,
  eye: RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureSample => textureSample.region === 'eye',
  ),
  eyebrow: RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureSample => textureSample.region === 'eyebrow',
  ),
};
export type RendererMode = 'smooth-region-mask';
type MaskTextureId =
  | 'lip-vision-boundary-v1'
  | 'lip-drawn-style-atlas-v1'
  | 'lip-drawn-gradient-density-atlas-v1'
  | 'lip-drawn-mask-v1'
  | 'cheek-session-mask-1-v1'
  | 'cheek-session-mask-2-v1'
  | 'cheek-session-mask-3-v1'
  | 'cheek-session-mask-4-v1'
  | 'cheek-session-mask-5-v1'
  | 'eye-drawn-mask-v1'
  | 'eyebrow-hair-atlas-v1'
  | 'eyebrow-hair-atlas-1-v1'
  | 'eyebrow-hair-atlas-2-v1'
  | 'eyebrow-hair-atlas-3-v1'
  | 'eyebrow-hair-atlas-4-v1'
  | 'eyebrow-hair-atlas-5-v1'
  | 'lip-style-atlas-v1'
  | 'lip-smooth-mask-v1'
  | 'eye-smooth-mask-v1';
type ValidationViewMode = (typeof VALIDATION_VIEW_MODE_OPTIONS)[number]['name'];
export type RegionRecipe = {
  color: RecipeColor;
  opacity: number;
  intensity: number;
  textureSample: RecipeTextureSample;
};
export type ActiveRegionMap = Record<CoreRecipeRegion, boolean> &
  Partial<Record<Exclude<RecipeRegion, CoreRecipeRegion>, boolean>>;

const DEFAULT_RECIPE_REGION: RecipeRegion = 'cheek';
const DEFAULT_RECIPE_COLOR = RECIPE_COLOR_OPTIONS[0];
const DEFAULT_EYEBROW_COLOR = EYEBROW_COLOR_OPTIONS.find(
  colorOption => colorOption.name === 'dark_brown',
) as RecipeColor;
const DEFAULT_TEXTURE_SAMPLE_BY_REGION: Record<
  RecipeRegion,
  RecipeTextureSample
> = {
  lip: RECIPE_TEXTURE_SAMPLE_OPTIONS.find(
    textureSample => textureSample.name === 'matte_lip',
  ) as RecipeTextureSample,
  cheek: RECIPE_TEXTURE_SAMPLE_OPTIONS.find(
    textureSample => textureSample.name === 'blush_session_1',
  ) as RecipeTextureSample,
  eye: RECIPE_TEXTURE_SAMPLE_OPTIONS.find(
    textureSample => textureSample.name === 'shimmer_eye',
  ) as RecipeTextureSample,
  eyebrow: RECIPE_TEXTURE_SAMPLE_OPTIONS.find(
    textureSample => textureSample.name === 'eyebrow_candidate_1',
  ) as RecipeTextureSample,
};
export const DEFAULT_REGION_RECIPES: Record<RecipeRegion, RegionRecipe> = {
  lip: {
    color: DEFAULT_RECIPE_COLOR,
    opacity: 0.9,
    intensity: 0.84,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip,
  },
  cheek: {
    color: RECIPE_COLOR_OPTIONS[1],
    opacity: 0.58,
    intensity: DEFAULT_TEXTURE_SAMPLE_BY_REGION.cheek.intensity,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.cheek,
  },
  eye: {
    color: DEFAULT_RECIPE_COLOR,
    opacity: 0.54,
    intensity: DEFAULT_TEXTURE_SAMPLE_BY_REGION.eye.intensity,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.eye,
  },
  eyebrow: {
    color: DEFAULT_EYEBROW_COLOR,
    opacity: 0.75,
    intensity: DEFAULT_TEXTURE_SAMPLE_BY_REGION.eyebrow.intensity,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.eyebrow,
  },
};
const DEFAULT_MASK_TEXTURE_ID_BY_REGION: Record<RecipeRegion, MaskTextureId> = {
  lip: 'lip-drawn-style-atlas-v1',
  cheek: 'cheek-session-mask-1-v1',
  eye: 'eye-drawn-mask-v1',
  eyebrow: 'eyebrow-hair-atlas-1-v1',
};
const GRADIENT_LIP_MASK_TEXTURE_ID: MaskTextureId =
  'lip-drawn-gradient-density-atlas-v1';

function resolveMaskTextureIdForRecipe(
  region: RecipeRegion,
  textureSample: RecipeTextureSample,
): MaskTextureId {
  if (region === 'lip' && textureSample.name === 'gradient_lip') {
    return GRADIENT_LIP_MASK_TEXTURE_ID;
  }

  if (region === 'cheek') {
    switch (textureSample.name) {
      case 'blush_session_1':
        return 'cheek-session-mask-1-v1';
      case 'blush_session_2':
        return 'cheek-session-mask-2-v1';
      case 'blush_session_3':
        return 'cheek-session-mask-3-v1';
      case 'blush_session_4':
        return 'cheek-session-mask-4-v1';
      case 'blush_session_5':
        return 'cheek-session-mask-5-v1';
    }
  }

  if (region === 'eyebrow') {
    switch (textureSample.name) {
      case 'eyebrow_candidate_1':
        return 'eyebrow-hair-atlas-1-v1';
      case 'eyebrow_candidate_2':
        return 'eyebrow-hair-atlas-2-v1';
      case 'eyebrow_candidate_3':
        return 'eyebrow-hair-atlas-3-v1';
    }

    return 'eyebrow-hair-atlas-1-v1';
  }

  return DEFAULT_MASK_TEXTURE_ID_BY_REGION[region];
}
export const DEFAULT_ACTIVE_REGIONS: ActiveRegionMap = {
  lip: false,
  cheek: false,
  eye: false,
  eyebrow: false,
};
const INTENSITY_STEP = 0.01;
const OPACITY_STEP = 0.01;
const UNITY_EVENT_HISTORY_LIMIT = 5;
export const DEFAULT_RENDERER_MODE: RendererMode = 'smooth-region-mask';
const UNITY_EVENT_TYPES = [
  'unity_initialized',
  'face_detected',
  'face_lifecycle',
  'face_feature_snapshot',
  'e7_metric_sample',
  'e7_reference_capture',
  'e7_vision_lip_boundary',
  'e7_mediapipe_eyebrow_boundary',
  'recipe_applied',
] as const;

export function buildValidationRecipeBatchPayload(
  recipes: Record<RecipeRegion, RegionRecipe>,
  enabledRegions: ActiveRegionMap,
  focusRegion: RecipeRegion,
  rendererMode: RendererMode,
  sentAtMs: number,
) {
  const lookId = E7_LOOK_ID;
  const recipeBatchId = `${E7_RECIPE_PREFIX}-batch-${Math.round(sentAtMs)}`;
  const activeRegionSummary = formatActiveRegionSummary(enabledRegions);
  const enabledLayerCount = countActiveRegions(enabledRegions);
  const payloadRegions = shouldIncludeEyebrowLayer(
    enabledRegions,
    focusRegion,
  )
    ? RECIPE_REGION_OPTIONS
    : CORE_RECIPE_REGION_OPTIONS;
  const layers = payloadRegions.map(region => {
    const recipe = recipes[region];
    const sample = recipe.textureSample;
    const layerIntensity = recipe.intensity;
    const maskTextureId = resolveMaskTextureIdForRecipe(region, sample);
    const layerRecipeId = `${E7_RECIPE_PREFIX}-${region}-${
      sample.name
    }-${Math.round(sentAtMs)}`;

    return {
      id: `${region}-${sample.name}`,
      recipeId: layerRecipeId,
      recipeBatchId,
      lookId,
      sentAtMs,
      rendererMode,
      activeRegions: activeRegionSummary,
      layerCount: payloadRegions.length,
      enabledLayerCount,
      region,
      layer: region,
      color: recipe.color.color,
      secondaryColor: sample.secondaryColor,
      opacity: recipe.opacity,
      texture: sample.name,
      sample: sample.name,
      textureMode: sample.textureMode,
      intensity: layerIntensity,
      feather: sample.feather,
      blendMode: sample.blendMode,
      enabled: enabledRegions[region],
      coverage: sample.coverage,
      finish: sample.finish,
      textureAmount: layerIntensity,
      roughness: sample.roughness,
      specular: sample.specular,
      specularPower: sample.specularPower,
      glossBoost: sample.glossBoost,
      gradientAmount: sample.gradientAmount,
      shimmer: sample.name === 'shimmer_eye' ? layerIntensity : 0,
      shimmerColor:
        sample.name === 'shimmer_eye' ? sample.secondaryColor : '#FFFFFF',
      skinAdaptive: region === 'cheek',
      preserveDetail: sample.preserveDetail,
      materialId: `${sample.name}-validation-material`,
      shaderMode:
        region === 'lip'
          ? 'lip-style-atlas-validation'
            : region === 'cheek'
              ? 'cheek-blush-multiband-skin-aware-validation'
              : region === 'eyebrow'
                ? 'eyebrow-boundary-tone-lift-validation'
                : 'unlit-alpha-validation',
      passCount: region === 'eyebrow'
        ? 4
        : sample.name === 'gloss_lip'
          ? 2
          : 1,
      maskTextureId,
      cameraBackdropAvailable: false,
      lightEstimateAvailable: false,
    };
  });
  const focusSample = recipes[focusRegion].textureSample;
  const focusMaskTextureId = resolveMaskTextureIdForRecipe(
    focusRegion,
    focusSample,
  );
  const focusIntensity =
    recipes[focusRegion].intensity;

  return {
    version: 1,
    recipeBatchId,
    recipeId: recipeBatchId,
    lookId,
    sentAtMs,
    rendererMode,
    region: focusRegion,
    activeRegions: activeRegionSummary,
    layerCount: layers.length,
    enabledLayerCount,
    texture: focusSample.name,
    sample: focusSample.name,
    textureMode: focusSample.textureMode,
    secondaryColor: focusSample.secondaryColor,
    coverage: focusSample.coverage,
    finish: focusSample.finish,
    textureAmount: focusIntensity,
    roughness: focusSample.roughness,
    specular: focusSample.specular,
    specularPower: focusSample.specularPower,
    glossBoost: focusSample.glossBoost,
    gradientAmount: focusSample.gradientAmount,
    shimmer: focusSample.name === 'shimmer_eye' ? focusIntensity : 0,
    shimmerColor:
      focusSample.name === 'shimmer_eye'
        ? focusSample.secondaryColor
        : '#FFFFFF',
    skinAdaptive: focusRegion === 'cheek',
    preserveDetail: focusSample.preserveDetail,
    materialId: `${focusSample.name}-validation-material`,
    shaderMode:
      focusRegion === 'lip'
        ? 'lip-style-atlas-validation'
        : focusRegion === 'cheek'
          ? 'cheek-blush-multiband-skin-aware-validation'
          : focusRegion === 'eyebrow'
            ? 'eyebrow-boundary-tone-lift-validation'
            : 'unlit-alpha-validation',
    passCount: focusRegion === 'eyebrow'
      ? 4
      : focusSample.name === 'gloss_lip'
        ? 2
        : 1,
    maskTextureId: focusMaskTextureId,
    cameraBackdropAvailable: false,
    lightEstimateAvailable: false,
    layers,
  };
}

export function buildValidationRecipeBatchJson(
  recipes: Record<RecipeRegion, RegionRecipe>,
  enabledRegions: ActiveRegionMap,
  focusRegion: RecipeRegion,
  rendererMode: RendererMode,
  sentAtMs: number,
) {
  return JSON.stringify(
    buildValidationRecipeBatchPayload(
      recipes,
      enabledRegions,
      focusRegion,
      rendererMode,
      sentAtMs,
    ),
  );
}

type UnityMessageEvent = {
  nativeEvent: {
    message?: string;
  };
};

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
  color?: string;
  secondaryColor?: string;
  opacity?: number;
  texture?: string;
  sample?: string;
  textureMode?: string;
  lipRenderLayerMode?: string;
  glossHighlightMode?: string;
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
  sourceTriangles?: number;
  culledTriangles?: number;
  meshCullingMode?: string;
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
  gradientAmount?: number;
  shimmer?: number;
  shimmerColor?: string;
  skinAdaptive?: boolean;
  preserveDetail?: boolean;
  materialId?: string;
  shaderMode?: string;
  passCount?: number;
  maskTextureId?: string;
  maskSoftSampleMode?: string;
  maskFeatherNearRadiusPx?: number;
  maskFeatherFarRadiusPx?: number;
  maskTextureDiagnosticStatus?: string;
  maskTextureWidth?: number;
  maskTextureHeight?: number;
  maskTextureActivePixelCountGt8?: number;
  maskTextureActiveCoverageGt8?: number;
  maskTextureActiveBbox?: string;
  maskTextureThresholdPixelCount?: number;
  maskTextureThresholdCoverage?: number;
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
  visionBoundaryStatus?: string;
  visionBoundarySource?: string;
  visionBoundaryCoordinateMode?: string;
  visionBoundaryOuterPointCount?: number;
  visionBoundaryInnerPointCount?: number;
  visionBoundaryImageWidth?: number;
  visionBoundaryImageHeight?: number;
  visionBoundaryAgeMs?: number;
  visionBoundaryFaceMotionScore?: number;
  visionBoundaryFaceCenterShiftPx?: number;
  visionBoundaryFaceScaleDelta?: number;
  visionBoundaryFaceMotionRisk?: string;
  outerPointCount?: number;
  innerPointCount?: number;
  available?: boolean;
  stabilizationMode?: string;
  transitionProgress?: number;
  transitionDurationMs?: number;
  faceBoundsAvailable?: boolean;
  leftOuterPointCount?: number;
  rightOuterPointCount?: number;
  leftEyePointCount?: number;
  rightEyePointCount?: number;
  hairRefinement?: string;
  leftHairPixels?: number;
  rightHairPixels?: number;
  leftBrowEyeGapPx?: number;
  rightBrowEyeGapPx?: number;
  faceMotionScore?: number;
  faceMotionRisk?: string;
  capturePairId?: string;
  relativeDirectory?: string;
  coordinateSpaceValidated?: boolean;
  coordinateSpaceValidationStatus?: string;
  detail?: string;
  frameWidth?: number;
  imageWidth?: number;
  imageHeight?: number;
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
type RecipeEventStatusByRegion = Partial<Record<RecipeRegion, UnityEventRecord>>;

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
        <Text style={styles.title}>Makeup AR Validation</Text>
        <Text style={styles.statusLabel}>Ready to start AR</Text>
        <Text style={styles.statusText}>
          {`Ready for entry #${nextEntryCount}. Completed exits ${completedCycles}/3.`}
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
        <Text style={styles.primaryButtonText}>Start AR</Text>
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
  const [controlsCollapsed, setControlsCollapsed] = useState(true);
  const selectedRendererMode = DEFAULT_RENDERER_MODE;
  const [focusedRegion, setFocusedRegion] = useState<RecipeRegion>(
    DEFAULT_RECIPE_REGION,
  );
  const [activeRegions, setActiveRegions] = useState<ActiveRegionMap>(
    DEFAULT_ACTIVE_REGIONS,
  );
  const [regionRecipes, setRegionRecipes] = useState<
    Record<RecipeRegion, RegionRecipe>
  >(DEFAULT_REGION_RECIPES);
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
  const [recipeEventStatusByRegion, setRecipeEventStatusByRegion] =
    useState<RecipeEventStatusByRegion>({});
  const [captureRequestSequence, setCaptureRequestSequence] = useState(1);
  const [pendingCapturePairId, setPendingCapturePairId] = useState<
    string | null
  >(null);
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
    ) => {
      return buildValidationRecipeBatchJson(
        recipes,
        enabledRegions,
        focusRegion,
        rendererMode,
        sentAtMs,
      );
    },
    [],
  );

  const postRecipeBatch = useCallback(
    (
      recipes = regionRecipes,
      enabledRegions = activeRegions,
      focusRegion = focusedRegion,
      rendererMode = selectedRendererMode,
    ) => {
      const sentAtMs = Date.now();
      const recipeJson = buildRecipeBatchJson(
        recipes,
        enabledRegions,
        focusRegion,
        rendererMode,
        sentAtMs,
      );
      const activeRegionSummary = formatActiveRegionSummary(enabledRegions);
      const focusMaskTextureId = resolveMaskTextureIdForRecipe(
        focusRegion,
        recipes[focusRegion].textureSample,
      );
      const lipMaskTextureId = resolveMaskTextureIdForRecipe(
        'lip',
        recipes.lip.textureSample,
      );
      const cheekMaskTextureId = resolveMaskTextureIdForRecipe(
        'cheek',
        recipes.cheek.textureSample,
      );
      const eyebrowMaskTextureId = resolveMaskTextureIdForRecipe(
        'eyebrow',
        recipes.eyebrow.textureSample,
      );
      console.log(
        '[E7] rn_texture_recipe_batch_post',
        `rendererMode=${rendererMode}`,
        `lookId=${E7_LOOK_ID}`,
        `activeRegions=${activeRegionSummary}`,
        `enabledLayerCount=${countActiveRegions(enabledRegions)}`,
        `focusRegion=${focusRegion}`,
        `focusMaskTextureId=${focusMaskTextureId}`,
        `lipMaskTextureId=${lipMaskTextureId}`,
        `cheekMaskTextureId=${cheekMaskTextureId}`,
        `eyebrowMaskTextureId=${eyebrowMaskTextureId}`,
        `payloadBytes=${recipeJson.length}`,
        `sentAtMs=${sentAtMs}`,
      );
      unityRef.current?.postMessage('RNBridge', 'ApplyRecipeJson', recipeJson);
    },
    [
      activeRegions,
      buildRecipeBatchJson,
      focusedRegion,
      regionRecipes,
      selectedRendererMode,
    ],
  );

  const postRecipeAck = useCallback(
    (payload: UnityEventPayload, receivedAtMs: number) => {
      const ackJson = JSON.stringify({
        type: 'recipe_ack',
        runId: payload.runId ?? E7_RECIPE_PREFIX,
        phase: payload.phase ?? 'smooth_mask',
        rendererMode: payload.rendererMode ?? DEFAULT_RENDERER_MODE,
        lookId: payload.lookId ?? E7_LOOK_ID,
        recipeId: payload.recipeId ?? 'none',
        recipeBatchId: payload.recipeBatchId ?? payload.recipeId ?? 'none',
        activeRegions:
          payload.activeRegionSummary ?? payload.activeRegions ?? 'none',
        layerCount: readNumber(payload.layerCount) ?? 0,
        enabledLayerCount: readNumber(payload.enabledLayerCount) ?? 0,
        payloadBytes: readNumber(payload.payloadBytes) ?? 0,
        region: payload.region ?? payload.appliedRegion ?? 'none',
        texture: payload.texture ?? payload.sample ?? 'none',
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

  const postReferenceCaptureRequest = useCallback(() => {
    if (pendingCapturePairId) {
      console.log(
        '[E7] reference_capture_request_ignored',
        `pendingCapturePairId=${pendingCapturePairId}`,
      );
      return;
    }

    const requestedAtMs = Date.now();
    const capturePairId = buildReferenceCapturePairId(
      captureRequestSequence,
      requestedAtMs,
    );
    const requestJson = JSON.stringify({
      capturePairId,
      requestedAtMs,
      requestedBy: 'rn-validation-ui',
      purpose: 'synchronized_capture_one_frame_common_lip_eye_cheek',
    });

    console.log(
      '[E7] reference_capture_request_post',
      `capturePairId=${capturePairId}`,
      `requestedAtMs=${requestedAtMs}`,
      'regions=lip,eye,cheek',
      'purpose=synchronized_capture_one_frame_common_lip_eye_cheek',
    );

    setPendingCapturePairId(capturePairId);
    setCaptureRequestSequence(sequence => sequence + 1);
    setValidationViewMode('clean');
    postRegionOverlayVisibility(false, 'capture_pair_preclean');

    unityRef.current?.postMessage(
      'RNBridge',
      'CaptureE7ReferenceFrameJson',
      requestJson,
    );
  }, [
    captureRequestSequence,
    pendingCapturePairId,
    postRegionOverlayVisibility,
  ]);

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
          const recipeRegion = getRecipeRegionFromEvent(parsed);
          if (recipeRegion) {
            setRecipeEventStatusByRegion(currentStatus => ({
              ...currentStatus,
              [recipeRegion]: record,
            }));
          }
        }

        if (parsed.type === 'e7_reference_capture') {
          const captureStatus = String(parsed.status ?? 'unknown');
          if (
            captureStatus === 'exported' ||
            captureStatus === 'failed' ||
            captureStatus === 'busy'
          ) {
            setPendingCapturePairId(currentPairId =>
              currentPairId === parsed.capturePairId ||
              captureStatus === 'failed'
                ? null
                : currentPairId,
            );
          }
        }

        const logPrefix =
          parsed.type === 'face_feature_snapshot'
            ? '[E5] rn_face_feature_snapshot_received'
            : parsed.type === 'e7_metric_sample'
            ? '[E7] rn_metric_sample_received'
            : parsed.type === 'e7_reference_capture'
            ? '[E7] rn_reference_capture_received'
            : parsed.type === 'e7_vision_lip_boundary'
            ? '[E7] rn_vision_lip_boundary_received'
            : parsed.type === 'e7_mediapipe_eyebrow_boundary'
            ? '[E7] rn_mediapipe_eyebrow_boundary_received'
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
    [postRecipeAck, validationViewMode],
  );

  useEffect(() => {
    const initialPostTimer = setTimeout(() => {
      postRecipeBatch();
    }, 1000);

    return () => clearTimeout(initialPostTimer);
  }, [postRecipeBatch]);

  const focusedRecipe = regionRecipes[focusedRegion];
  const selectedColor = focusedRecipe.color;
  const selectedTextureSample = focusedRecipe.textureSample;
  const focusedTextureOptions = TEXTURE_STYLE_OPTIONS_BY_REGION[focusedRegion];
  const focusedColorOptions =
    focusedRegion === 'eyebrow' ? EYEBROW_COLOR_OPTIONS : RECIPE_COLOR_OPTIONS;
  const activeRegionSummary = formatActiveRegionSummary(activeRegions);
  const focusedIntensity = focusedRecipe.intensity;
  const focusedOpacity = focusedRecipe.opacity;
  const latestMetric = unityEventStatus.e7_metric_sample?.parsed;
  const latestLifecycle = unityEventStatus.face_lifecycle?.parsed;
  const focusedRecipeRecord = recipeEventStatusByRegion[focusedRegion];
  const latestRecipeRecord =
    focusedRecipeRecord ??
    (focusedRegion === 'eyebrow' ? undefined : unityEventStatus.recipe_applied);
  const latestRecipe = latestRecipeRecord?.parsed;
  const latestSnapshot = unityEventStatus.face_feature_snapshot?.parsed;
  const unityInitializedAt =
    unityEventStatus.unity_initialized?.receivedAtMs ?? 0;

  useEffect(() => {
    postRegionOverlayVisibility(
      validationViewMode !== 'clean',
      'validation_view_mode_changed',
    );
  }, [postRegionOverlayVisibility, validationViewMode, unityInitializedAt]);

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
    ],
  );
  const showFullDebug = validationViewMode === 'full';
  const showFullControls = validationViewMode === 'full';
  const showCompactControls = validationViewMode !== 'clean';

  const toggleRegion = useCallback(
    (region: RecipeRegion) => {
      const isActive = activeRegions[region] === true;
      const shouldDisable = isActive && focusedRegion === region;
      const nextActiveRegions = {
        ...activeRegions,
        [region]: !shouldDisable,
      };

      setFocusedRegion(region);
      setActiveRegions(nextActiveRegions);
      postRecipeBatch(regionRecipes, nextActiveRegions, region);
    },
    [activeRegions, focusedRegion, postRecipeBatch, regionRecipes],
  );

  const selectColor = useCallback(
    (color: RecipeColor) => {
      const nextRecipe = {
        ...regionRecipes[focusedRegion],
        color,
      };
      const nextRecipes = {
        ...regionRecipes,
        [focusedRegion]: nextRecipe,
      };

      setRegionRecipes(nextRecipes);
      postRecipeBatch(nextRecipes, activeRegions, focusedRegion);
    },
    [activeRegions, focusedRegion, postRecipeBatch, regionRecipes],
  );

  const updateFocusedIntensity = useCallback(
    (nextIntensity: number) => {
      const nextRecipe = {
        ...regionRecipes[focusedRegion],
        intensity: nextIntensity,
      };
      const nextRecipes = {
        ...regionRecipes,
        [focusedRegion]: nextRecipe,
      };

      setRegionRecipes(nextRecipes);
      postRecipeBatch(nextRecipes, activeRegions, focusedRegion);
    },
    [activeRegions, focusedRegion, postRecipeBatch, regionRecipes],
  );

  const updateFocusedOpacity = useCallback(
    (nextOpacity: number) => {
      const nextRecipe = {
        ...regionRecipes[focusedRegion],
        opacity: nextOpacity,
      };
      const nextRecipes = {
        ...regionRecipes,
        [focusedRegion]: nextRecipe,
      };

      setRegionRecipes(nextRecipes);
      postRecipeBatch(nextRecipes, activeRegions, focusedRegion);
    },
    [activeRegions, focusedRegion, postRecipeBatch, regionRecipes],
  );

  const selectTextureSample = useCallback(
    (textureSample: RecipeTextureSample) => {
      if (textureSample.region !== focusedRegion) {
        return;
      }

      const nextRecipe = {
        ...regionRecipes[focusedRegion],
        textureSample,
      };
      const nextRecipes = {
        ...regionRecipes,
        [focusedRegion]: nextRecipe,
      };
      const nextActiveRegions = {
        ...activeRegions,
        [focusedRegion]: true,
      };

      setRegionRecipes(nextRecipes);
      setActiveRegions(nextActiveRegions);
      postRecipeBatch(nextRecipes, nextActiveRegions, focusedRegion);
    },
    [activeRegions, focusedRegion, postRecipeBatch, regionRecipes],
  );

  const intensityPercent = Math.round(focusedIntensity * 100);
  const opacityPercent = Math.round(focusedOpacity * 100);
  const focusedTextureControlLabel =
    focusedRegion === 'cheek'
      ? 'Blush Region'
      : focusedRegion === 'lip'
        ? 'Lip Finish'
        : focusedRegion === 'eyebrow'
          ? 'Eyebrow Style'
          : 'Eye Style';
  const formatTextureLabel = useCallback(
    (textureSample: RecipeTextureSample) => {
      switch (textureSample.name) {
        case 'gloss_lip':
          return 'Glow';
        case 'gradient_lip':
          return 'Gradient';
        case 'blush_session_1':
          return 'Daily';
        case 'blush_session_2':
          return 'Lovely';
        case 'blush_session_3':
          return 'Under';
        case 'blush_session_4':
          return 'Sun 1';
        case 'blush_session_5':
          return 'Sun 2';
        case 'shimmer_eye':
          return 'Shimmer';
        case 'eyebrow_candidate_1':
          return 'Soft Arch';
        case 'eyebrow_candidate_2':
          return 'Straight';
        case 'eyebrow_candidate_3':
          return 'Slim Tail';
        default:
          return 'Matte';
      }
    },
    [],
  );

  return (
    <View style={styles.unityScreen}>
      <UnityView
        key={`unity-view-${entryCount}`}
        ref={unityRef}
        style={styles.unityView}
        onUnityMessage={handleUnityMessage}
      />

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

          <View style={styles.viewModeRow}>
            {VALIDATION_VIEW_MODE_OPTIONS.map(modeOption => {
              const isSelected = modeOption.name === validationViewMode;

              return (
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{ selected: isSelected }}
                  key={modeOption.name}
                  style={({ pressed }) => [
                    styles.viewModeButton,
                    isSelected && styles.viewModeButtonSelected,
                    pressed && styles.colorButtonPressed,
                  ]}
                  onPress={() => setValidationViewMode(modeOption.name)}
                >
                  <Text
                    style={[
                      styles.viewModeButtonText,
                      isSelected && styles.viewModeButtonTextSelected,
                    ]}
                  >
                    {modeOption.label}
                  </Text>
                </Pressable>
              );
            })}
          </View>
        </View>

        {validationViewMode === 'clean' && (
          <View style={styles.captureDock}>
            <Pressable
              accessibilityRole="button"
              disabled={Boolean(pendingCapturePairId)}
              style={({ pressed }) => [
                styles.captureButton,
                pendingCapturePairId && styles.captureButtonPending,
                pressed && styles.closeButtonPressed,
              ]}
              onPress={postReferenceCaptureRequest}
            >
              <Text style={styles.captureButtonText}>
                {pendingCapturePairId ? 'Capturing' : 'Capture Pair'}
              </Text>
            </Pressable>
          </View>
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
              recipeRecord={latestRecipeRecord}
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
              !showFullControls && styles.recipePanelCompact,
              controlsCollapsed && styles.recipePanelCollapsed,
            ]}
          >
            <View style={styles.recipePanelHeader}>
              <Text style={styles.recipePanelLabel}>Controls</Text>
              <Text style={styles.recipePanelMetaText} numberOfLines={1}>
                {`active=${activeRegionSummary} / focus=${focusedRegion}`}
              </Text>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ expanded: !controlsCollapsed }}
                testID="recipe-panel-collapse-toggle"
                style={({ pressed }) => [
                  styles.panelToggleButton,
                  pressed && styles.colorButtonPressed,
                ]}
                onPress={() =>
                  setControlsCollapsed(collapsed => !collapsed)
                }
              >
                <Text style={styles.panelToggleButtonText}>
                  {controlsCollapsed ? 'Show' : 'Hide'}
                </Text>
              </Pressable>
            </View>

            {!controlsCollapsed && (
              <>
                <CompactEvidenceHud
                  validationViewMode={validationViewMode}
                  activeRegionSummary={activeRegionSummary}
                  focusedRegion={focusedRegion}
                  latestMetric={latestMetric}
                  latestLifecycle={latestLifecycle}
                  latestRecipe={latestRecipe}
                  recipeLatencyMs={recipeLatencyMs}
                />

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

                <View style={styles.colorButtonRow}>
                  {focusedColorOptions.map(colorOption => {
                    const isSelected = colorOption.name === selectedColor.name;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={colorOption.name}
                        testID={`${focusedRegion}-color-${colorOption.name}`}
                        style={({ pressed }) => [
                          styles.colorButton,
                          { backgroundColor: colorOption.color },
                          isSelected && styles.colorButtonSelected,
                          pressed && styles.colorButtonPressed,
                        ]}
                        onPress={() => selectColor(colorOption)}
                      >
                        <Text style={styles.colorButtonText}>
                          {colorOption.label}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                <View style={styles.controlSectionHeader}>
                  <Text style={styles.controlSectionLabel}>
                    {focusedTextureControlLabel}
                  </Text>
                </View>

                <View style={styles.textureButtonRow}>
                  {focusedTextureOptions.map(textureOption => {
                    const isSelected =
                      textureOption.name === selectedTextureSample.name;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={textureOption.name}
                        testID={
                          textureOption.region === 'cheek'
                            ? `cheek-region-${textureOption.name}`
                            : `${textureOption.region}-finish-${textureOption.name}`
                        }
                        style={({ pressed }) => [
                          styles.textureButton,
                          isSelected && styles.textureButtonSelected,
                          pressed && styles.colorButtonPressed,
                        ]}
                        onPress={() => selectTextureSample(textureOption)}
                      >
                        <Text
                          style={[
                            styles.textureButtonText,
                            isSelected && styles.textureButtonTextSelected,
                          ]}
                        >
                          {formatTextureLabel(textureOption)}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                <ValueSlider
                  label="Intensity"
                  value={focusedIntensity}
                  width={sliderWidth}
                  fillColor={selectedColor.color}
                  onLayoutWidth={setSliderWidth}
                  onChange={updateFocusedIntensity}
                  step={INTENSITY_STEP}
                />

                <ValueSlider
                  label="Opacity"
                  value={focusedOpacity}
                  width={sliderWidth}
                  fillColor={selectedColor.color}
                  onLayoutWidth={setSliderWidth}
                  onChange={updateFocusedOpacity}
                  step={OPACITY_STEP}
                />

                <Text style={styles.recipeValueText} numberOfLines={3}>
                  active {activeRegionSummary} / focus {focusedRegion} /{' '}
                  {selectedColor.label} {selectedColor.color} / intensity{' '}
                  {intensityPercent}% / opacity {opacityPercent}% / shape{' '}
                  {selectedTextureSample.name}
                </Text>

                <Text style={styles.recipeAppliedText} numberOfLines={2}>
                  {formatRecipeAppliedSummary(latestRecipe)}
                </Text>
              </>
            )}
          </View>
        )}
      </View>
    </View>
  );
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
          ? `look=${String(metric.lookId ?? E7_LOOK_ID)} active=${String(
              metric.activeRegionSummary ??
                metric.activeRegions ??
                currentRegions,
            )}`
          : `look=${E7_LOOK_ID} active=${currentRegions}`}
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
          ? `mask=${String(
              metric.maskSource ?? 'smooth_region_mask',
            )} uv=${String(
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
  latestMetric?: UnityEventPayload;
  latestLifecycle?: UnityEventPayload;
  latestRecipe?: UnityEventPayload;
  recipeLatencyMs?: number;
};

function CompactEvidenceHud({
  validationViewMode,
  activeRegionSummary,
  focusedRegion,
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
        {`active=${activeRegionSummary} focus=${focusedRegion}`}
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
    `rendererMode=${selectedRendererMode} look=${E7_LOOK_ID}`,
    `activeRegions=${activeRegionSummary} focusRegion=${focusedRegion}`,
    `metricRegion=${formatLifecycleValue(latestMetric?.region)}`,
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
    case 'e7_vision_lip_boundary':
      return `e7_vision_lip_boundary ${formatE7VisionLipBoundarySummary(
        event,
      )}`;
    case 'e7_mediapipe_eyebrow_boundary':
      return `e7_mediapipe_eyebrow_boundary ${formatE7MediaPipeEyebrowBoundarySummary(
        event,
      )}`;
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

function getRecipeRegionFromEvent(
  event: UnityEventPayload,
): RecipeRegion | undefined {
  const region = String(event.region ?? event.layer ?? '').toLowerCase();

  return RECIPE_REGION_OPTIONS.includes(region as RecipeRegion)
    ? (region as RecipeRegion)
    : undefined;
}

function shouldIncludeEyebrowLayer(
  activeRegions: ActiveRegionMap,
  focusRegion: RecipeRegion,
) {
  return focusRegion === 'eyebrow' || activeRegions.eyebrow === true;
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
    case 'e7_vision_lip_boundary':
      return `e7_vision_lip_boundary: ${formatE7VisionLipBoundarySummary(
        parsed,
      )} ${event.receivedAt}`;
    case 'e7_mediapipe_eyebrow_boundary':
      return `e7_mediapipe_eyebrow_boundary: ${formatE7MediaPipeEyebrowBoundarySummary(
        parsed,
      )} ${event.receivedAt}`;
    case 'recipe_applied':
      return `${formatRecipeAppliedSummary(parsed)} ${event.receivedAt}`;
  }
}

function formatE7MediaPipeEyebrowBoundarySummary(event: UnityEventPayload) {
  return `status=${String(event.status ?? 'unknown')} available=${String(
    event.available ?? false,
  )} source=${String(
    event.source ?? 'mediapipe_face_landmarker_runtime_eyebrow_boundary',
  )} coord=${String(event.coordinateMode ?? 'mediapipe-image-top-left')} face=${String(
    event.faceCount ?? 'n/a',
  )} brow=${String(event.leftOuterPointCount ?? 'n/a')}/${String(
    event.rightOuterPointCount ?? 'n/a',
  )} eye=${String(event.leftEyePointCount ?? 'n/a')}/${String(
    event.rightEyePointCount ?? 'n/a',
  )} gap=${formatMetricNumber(event.leftBrowEyeGapPx, 1)}/${formatMetricNumber(
    event.rightBrowEyeGapPx,
    1,
  )} hair=${String(event.leftHairPixels ?? 'n/a')}/${String(
    event.rightHairPixels ?? 'n/a',
  )} refine=${String(event.hairRefinement ?? 'n/a')} motion=${formatMetricNumber(
    event.faceMotionScore,
    3,
  )}/${String(event.faceMotionRisk ?? 'n/a')} privacy raw=${String(
    event.rawCameraFrameStored ?? false,
  )} offDevice=${String(event.offDeviceUpload ?? false)}`;
}

function formatE7VisionLipBoundarySummary(event: UnityEventPayload) {
  return `status=${String(event.status ?? 'unknown')} available=${String(
    event.available ?? false,
  )} source=${String(event.source ?? 'apple_vision_runtime_lip_landmarks')} coord=${String(
    event.coordinateMode ?? event.visionBoundaryCoordinateMode ?? 'raw-y',
  )} points=${String(
    event.outerPointCount ?? event.visionBoundaryOuterPointCount ?? 'n/a',
  )}/${String(
    event.innerPointCount ?? event.visionBoundaryInnerPointCount ?? 'n/a',
  )} image=${String(
    event.visionBoundaryImageWidth ?? event.frameWidth ?? event.imageWidth ?? 'n/a',
  )}x${String(
    event.visionBoundaryImageHeight ?? event.imageHeight ?? 'n/a',
  )} smooth=${String(event.stabilizationMode ?? 'n/a')} t=${String(
    event.transitionProgress ?? 'n/a',
  )}/${String(event.transitionDurationMs ?? 'n/a')} faceLocal=${String(
    event.faceBoundsAvailable ?? false,
  )} motion=${formatMetricNumber(
    event.visionBoundaryFaceMotionScore,
    3,
  )}/${String(
    event.visionBoundaryFaceMotionRisk ?? 'n/a',
  )} privacy raw=false offDevice=false`;
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
    event.lookId ?? E7_LOOK_ID,
  )} active=${String(
    event.activeRegionSummary ?? event.activeRegions ?? 'n/a',
  )} enabled=${String(event.enabledLayerCount ?? 'n/a')} topology=${String(
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
      event.runId ??
        `${E7_RECIPE_PREFIX}-rn-${new Date().toISOString().slice(0, 10)}`,
    )}`,
    `phase=${String(event.phase ?? 'smooth_mask')}`,
    `timestampMs=${receivedAtMs}`,
    `rendererMode=${String(event.rendererMode ?? 'smooth-region-mask')}`,
    `lookId=${String(event.lookId ?? E7_LOOK_ID)}`,
    `recipeId=${String(event.recipeId ?? 'none')}`,
    `recipeBatchId=${String(event.recipeBatchId ?? event.recipeId ?? 'none')}`,
    `activeRegions=${String(
      event.activeRegionSummary ?? event.activeRegions ?? 'none',
    )}`,
    `enabledLayerCount=${String(event.enabledLayerCount ?? 'n/a')}`,
    `payloadBytes=${String(event.payloadBytes ?? 'n/a')}`,
    `region=${String(event.region ?? event.layer ?? 'none')}`,
    `texture=${String(event.texture ?? event.sample ?? 'none')}`,
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
  )} texture=${texture} mode=${String(
    event.textureMode ?? 'n/a',
  )} layers=${String(
    event.lipRenderLayerMode ?? 'n/a',
  )} gloss=${String(
    event.glossHighlightMode ?? 'n/a',
  )} blend=${String(event.blendMode ?? 'n/a')} finish=${String(
    event.finish ?? 'n/a',
  )} maskTex=${String(
    event.maskTextureId ?? 'n/a',
  )} soft=${String(
    event.maskSoftSampleMode ?? 'n/a',
  )} featherPx=${formatMetricNumber(
    event.maskFeatherNearRadiusPx,
    2,
  )}/${formatMetricNumber(
    event.maskFeatherFarRadiusPx,
    2,
  )} color=${String(event.color)} opacity=${String(
    event.opacity,
  )} intensity=${String(event.intensity ?? 'n/a')} applied=${String(
    event.applied ?? false,
  )} faceCount=${String(event.faceCount ?? 'n/a')} meshTriangles=${String(
    event.meshTriangles ?? 'n/a',
  )} mask=${String(
    event.maskTriangles ?? event.regionMaskTriangles ?? 'n/a',
  )} cull=${String(event.culledTriangles ?? 'n/a')}/${String(
    event.sourceTriangles ?? 'n/a',
  )} cullMode=${String(event.meshCullingMode ?? 'n/a')} uv=${String(
    event.uvAvailable ?? false,
  )} state=${String(event.stateAction ?? 'n/a')} src=${String(
    event.maskSource ?? 'n/a',
  )} vision=${String(
    event.visionBoundaryStatus ?? 'n/a',
  )}:${String(event.visionBoundaryOuterPointCount ?? 'n/a')}/${String(
    event.visionBoundaryInnerPointCount ?? 'n/a',
  )} visionCoord=${String(
    event.visionBoundaryCoordinateMode ?? 'n/a',
  )} visionAge=${String(
    event.visionBoundaryAgeMs ?? 'n/a',
  )} visionMotion=${formatMetricNumber(
    event.visionBoundaryFaceMotionScore,
    3,
  )}/${String(
    event.visionBoundaryFaceMotionRisk ?? 'n/a',
  )} maskDiag=${String(
    event.maskTextureDiagnosticStatus ?? 'n/a',
  )} texGt8=${String(
    event.maskTextureActivePixelCountGt8 ?? 'n/a',
  )}/${formatMetricNumber(
    event.maskTextureActiveCoverageGt8,
    3,
  )} texBbox=${String(event.maskTextureActiveBbox ?? 'n/a')} topology=${String(
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
  const regions = RECIPE_REGION_OPTIONS.filter(
    region => activeRegions[region] === true,
  );
  return regions.length === 0 ? 'none' : regions.join(',');
}

function countActiveRegions(activeRegions: ActiveRegionMap) {
  return RECIPE_REGION_OPTIONS.reduce(
    (count, region) => count + (activeRegions[region] === true ? 1 : 0),
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

type ValueSliderProps = {
  label: string;
  value: number;
  width: number;
  fillColor: string;
  onLayoutWidth: (width: number) => void;
  onChange: (value: number) => void;
  step?: number;
};

function ValueSlider({
  label,
  value,
  width,
  fillColor,
  onLayoutWidth,
  onChange,
  step = INTENSITY_STEP,
}: ValueSliderProps) {
  const clampedWidth = Math.max(width, 1);
  const fillWidth = value * clampedWidth;

  const valueFromEvent = useCallback(
    (event: GestureResponderEvent) => {
      const raw = Math.max(
        0,
        Math.min(event.nativeEvent.locationX, clampedWidth),
      );
      const normalizedStep = Math.max(step, 0.001);
      const steppedValue =
        Math.round(raw / clampedWidth / normalizedStep) * normalizedStep;

      return Number(Math.max(0, Math.min(1, steppedValue)).toFixed(2));
    },
    [clampedWidth, step],
  );

  const updateFromEvent = useCallback(
    (event: GestureResponderEvent) => {
      onChange(valueFromEvent(event));
    },
    [onChange, valueFromEvent],
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
      <View
        accessibilityRole="adjustable"
        accessibilityValue={{ min: 0, max: 1, now: value }}
        style={styles.sliderTrack}
        onLayout={handleLayout}
        {...panResponder.panHandlers}
      >
        <View
          style={[
            styles.sliderFill,
            { width: fillWidth, backgroundColor: fillColor },
          ]}
        />
        <View style={[styles.sliderThumb, { left: fillWidth }]} />
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
    alignSelf: 'center',
    width: '84%',
    maxHeight: 500,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.68)',
    paddingHorizontal: 10,
    paddingVertical: 8,
    overflow: 'hidden',
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
  recipePanelCollapsed: {
    alignSelf: 'center',
    minWidth: 260,
    maxWidth: '92%',
    paddingHorizontal: 10,
    paddingVertical: 7,
    gap: 0,
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
  panelToggleButton: {
    minWidth: 52,
    minHeight: 30,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.32)',
    backgroundColor: 'rgba(255, 255, 255, 0.12)',
    paddingHorizontal: 8,
  },
  panelToggleButtonText: {
    color: '#F9FAFB',
    fontSize: 11,
    fontWeight: '900',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  controlSectionHeader: {
    marginTop: -2,
  },
  controlSectionLabel: {
    color: '#BAE6FD',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textTransform: 'uppercase',
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
  regionButtonDisabled: {
    opacity: 0.42,
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
    minHeight: 38,
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
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  textureButtonRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
  },
  textureButton: {
    flexGrow: 1,
    flexBasis: '30%',
    minWidth: 92,
    minHeight: 42,
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
  sliderTrack: {
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
