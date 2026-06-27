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
  ScrollView,
  StatusBar,
  StyleSheet,
  Text,
  useColorScheme,
  useWindowDimensions,
  View,
} from 'react-native';
import UnityView from '@azesmway/react-native-unity';
import {
  SafeAreaProvider,
  useSafeAreaInsets,
} from 'react-native-safe-area-context';

LogBox.ignoreAllLogs(true);

export const RECIPE_COLOR_OPTIONS = [
  { name: 'rose', color: '#D94B74' },
  { name: 'coral', color: '#E67B5F' },
  { name: 'nude', color: '#B9826B' },
  { name: 'berry', color: '#A8325F' },
  { name: 'red', color: '#C21F3A' },
] as const;
export const BROW_COLOR_OPTIONS = [
  { name: 'ash_brown', color: '#3F352F' },
  { name: 'neutral_brown', color: '#4A342B' },
  { name: 'dark_brown', color: '#2F241F' },
  { name: 'soft_black', color: '#1F1B18' },
] as const;

const RECIPE_REGION_OPTIONS = ['lip', 'cheek', 'eye', 'brow'] as const;
export type RecipeColor =
  | (typeof RECIPE_COLOR_OPTIONS)[number]
  | (typeof BROW_COLOR_OPTIONS)[number];
export type RecipeRegion = (typeof RECIPE_REGION_OPTIONS)[number];
export type RecipeTextureSampleName =
  | 'matte_lip'
  | 'gloss_lip'
  | 'full_lip'
  | 'gradient_lip'
  | 'overline_lip'
  | 'soft_blush'
  | 'shimmer_eye'
  | 'natural_brow'
  | 'soft_brow';
export type RecipeTextureSample = {
  name: RecipeTextureSampleName;
  label: string;
  region: RecipeRegion;
  textureMode: 'sample';
  blendMode: 'multiply' | 'normal' | 'screen';
  secondaryColor: string;
  intensity: number;
  feather: number;
  coverage: number;
  finish: string;
  roughness: number;
  specular: number;
  specularPower: number;
  glossBoost: number;
  gradientAmount: number;
  preserveDetail: boolean;
};
export type LipFinishType = 'normal' | 'matte' | 'glossy';
export type LipAreaStyle = 'full' | 'gradient' | 'overline';

export const LIP_FINISH_TYPE_OPTIONS: {
  id: LipFinishType;
  label: string;
}[] = [
  { id: 'normal', label: 'Normal' },
  { id: 'matte', label: 'Matte' },
  { id: 'glossy', label: 'Glossy' },
];
export const LIP_AREA_STYLE_OPTIONS: {
  id: LipAreaStyle;
  label: string;
  textureSampleName: RecipeTextureSampleName;
}[] = [
  { id: 'full', label: 'Full', textureSampleName: 'full_lip' },
  { id: 'gradient', label: 'Gradient', textureSampleName: 'gradient_lip' },
  { id: 'overline', label: 'Overlip', textureSampleName: 'overline_lip' },
];

export const RECIPE_TEXTURE_SAMPLE_OPTIONS: RecipeTextureSample[] = [
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
    label: 'overlip lip',
    region: 'lip',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#D94B74',
    intensity: 0.5,
    feather: 0.24,
    coverage: 0.42,
    finish: 'overlip',
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
    blendMode: 'normal',
    secondaryColor: '#F5A49B',
    intensity: 0.64,
    feather: 0.46,
    coverage: 1,
    finish: 'powder',
    roughness: 0.92,
    specular: 0.02,
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
    name: 'natural_brow',
    label: 'natural brow',
    region: 'brow',
    textureMode: 'sample',
    blendMode: 'multiply',
    secondaryColor: '#4A342B',
    intensity: 0.68,
    feather: 0.48,
    coverage: 0.62,
    finish: 'powder-brow',
    roughness: 1,
    specular: 0,
    specularPower: 6,
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
    secondaryColor: '#5A4034',
    intensity: 0.56,
    feather: 0.48,
    coverage: 0.58,
    finish: 'soft-powder-brow',
    roughness: 1,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
    gradientAmount: 0,
    preserveDetail: true,
  },
];
const VALIDATION_VIEW_MODE_OPTIONS = [
  { name: 'clean', label: 'Clean' },
  { name: 'compact', label: 'HUD' },
  { name: 'full', label: 'Debug' },
] as const;
const MASK_DEBUG_VIEW_MODE_OPTIONS = [
  { id: 'final', label: 'Final' },
  { id: 'raw', label: 'Raw' },
  { id: 'processed', label: 'Processed' },
] as const;
const COLOR_OPTIONS_BY_REGION: Record<
  RecipeRegion,
  readonly RecipeColor[]
> = {
  lip: RECIPE_COLOR_OPTIONS,
  cheek: RECIPE_COLOR_OPTIONS,
  eye: RECIPE_COLOR_OPTIONS,
  brow: BROW_COLOR_OPTIONS,
};
const E7_BOUNDARY_PLAN_VERSION = 'E7.03 v2.1';
const E7_EVIDENCE_MODE = 'lip-makeup-validation-v1';
const E7_LIP_LOOK_ID = 'lip_makeup_validation_v1';
const E7_RECIPE_PREFIX = 'lip-style-v1';

const DEFAULT_LIP_FINISH_TYPE: LipFinishType = 'normal';
const DEFAULT_LIP_AREA_STYLE: LipAreaStyle = 'full';
const LIP_FINISH_MATERIAL_VALUES: Record<
  LipFinishType,
  Pick<
    RecipeTextureSample,
    'finish' | 'roughness' | 'specular' | 'specularPower' | 'glossBoost'
  >
> = {
  normal: {
    finish: 'normal',
    roughness: 0.55,
    specular: 0.18,
    specularPower: 18,
    glossBoost: 0.08,
  },
  matte: {
    finish: 'matte',
    roughness: 1,
    specular: 0,
    specularPower: 6,
    glossBoost: 0,
  },
  glossy: {
    finish: 'gloss',
    roughness: 0.26,
    specular: 0.78,
    specularPower: 36,
    glossBoost: 0.68,
  },
};

function getRecipeTextureSampleByName(
  name: RecipeTextureSampleName,
): RecipeTextureSample {
  const textureSample = RECIPE_TEXTURE_SAMPLE_OPTIONS.find(
    sample => sample.name === name,
  );

  if (!textureSample) {
    throw new Error(`Missing recipe texture sample: ${name}`);
  }

  return textureSample;
}

function getLipAreaStyleOption(areaStyle: LipAreaStyle) {
  return LIP_AREA_STYLE_OPTIONS.find(option => option.id === areaStyle)!;
}

export function composeLipTextureSample(
  finishType: LipFinishType,
  areaStyle: LipAreaStyle,
): RecipeTextureSample {
  const areaOption = getLipAreaStyleOption(areaStyle);
  const areaSample = getRecipeTextureSampleByName(areaOption.textureSampleName);
  const finishValues = LIP_FINISH_MATERIAL_VALUES[finishType];
  const finishLabel = formatLipFinishTypeLabel(finishType).toLowerCase();
  const areaLabel = areaOption.label.toLowerCase();

  return {
    ...areaSample,
    label: `${finishLabel} ${areaLabel} lip`,
    finish: finishValues.finish,
    roughness: finishValues.roughness,
    specular: finishValues.specular,
    specularPower: finishValues.specularPower,
    glossBoost: finishValues.glossBoost,
  };
}

function getLipFinishTypeForSample(
  textureSample: RecipeTextureSample,
): LipFinishType {
  if (textureSample.region !== 'lip') {
    return DEFAULT_LIP_FINISH_TYPE;
  }

  if (textureSample.finish === 'gloss' || textureSample.glossBoost >= 0.3) {
    return 'glossy';
  }

  if (
    textureSample.finish === 'matte' ||
    (textureSample.specular <= 0.01 && textureSample.glossBoost <= 0.01)
  ) {
    return 'matte';
  }

  return 'normal';
}

function getRecipePassCount(textureSample: RecipeTextureSample) {
  return getLipFinishTypeForSample(textureSample) === 'glossy' ? 2 : 1;
}

function formatLipFinishTypeLabel(finishType: LipFinishType) {
  return (
    LIP_FINISH_TYPE_OPTIONS.find(option => option.id === finishType)?.label ??
    'Normal'
  );
}

function formatLipAreaStyleLabel(areaStyle: LipAreaStyle) {
  return getLipAreaStyleOption(areaStyle).label;
}

export const LIP_TEXTURE_STYLE_OPTIONS: RecipeTextureSample[] =
  LIP_AREA_STYLE_OPTIONS.map(option =>
    getRecipeTextureSampleByName(option.textureSampleName),
  );
export const BROW_TEXTURE_STYLE_OPTIONS: RecipeTextureSample[] =
  RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureSample => textureSample.region === 'brow',
  );
export type RendererMode = 'smooth-region-mask';
type MaskTextureId =
  | 'lip-vision-boundary-v1'
  | 'lip-drawn-style-atlas-v1'
  | 'lip-drawn-gradient-density-atlas-v1'
  | 'lip-drawn-mask-v1'
  | 'cheek-drawn-mask-v1'
  | 'eye-drawn-mask-v1'
  | 'lip-style-atlas-v1'
  | 'lip-smooth-mask-v1'
  | 'cheek-smooth-mask-v1'
  | 'eye-smooth-mask-v1'
  | 'brow-soft-arch-fine-hair-v1'
  | 'brow-back-arch-soft-mix-v1'
  | 'brow-slim-tail-fine-hair-v1'
  | 'brow-drawn-mask-v1';
type ValidationViewMode = (typeof VALIDATION_VIEW_MODE_OPTIONS)[number]['name'];
export type MaskDebugViewMode =
  (typeof MASK_DEBUG_VIEW_MODE_OPTIONS)[number]['id'];
export type RegionRecipe = {
  color: RecipeColor;
  opacity: number;
  intensity: number;
  textureSample: RecipeTextureSample;
};
export type ActiveRegionMap = Record<RecipeRegion, boolean>;
export type RegionTuningParameters = {
  feather: number;
  coverage: number;
  roughness: number;
  specular: number;
  specularPower: number;
  glossBoost: number;
  gradientAmount: number;
  preserveDetail: boolean;
  maskTextureId: MaskTextureId;
};
export type DebugDisplayOptions = {
  maskOverlayVisible: boolean;
  guideOverlayVisible: boolean;
  meshOverlayVisible: boolean;
  diagnosticsHudVisible: boolean;
  maskDebugViewMode: MaskDebugViewMode;
};
type BooleanDebugDisplayOption = Exclude<
  keyof DebugDisplayOptions,
  'maskDebugViewMode'
>;

export const DEBUG_GUIDE_OVERLAY_MODE = 'mesh_landmarks';
export const DEBUG_MESH_RENDER_MODE = 'wireframe';

const DEFAULT_RECIPE_REGION: RecipeRegion = 'lip';
const DEFAULT_RECIPE_COLOR = RECIPE_COLOR_OPTIONS[0];
const DEFAULT_TEXTURE_SAMPLE_BY_REGION: Record<
  RecipeRegion,
  RecipeTextureSample
> = {
  lip: composeLipTextureSample(DEFAULT_LIP_FINISH_TYPE, DEFAULT_LIP_AREA_STYLE),
  cheek: getRecipeTextureSampleByName('soft_blush'),
  eye: getRecipeTextureSampleByName('shimmer_eye'),
  brow: getRecipeTextureSampleByName('natural_brow'),
};
const DEFAULT_MASK_TEXTURE_ID_BY_REGION: Record<RecipeRegion, MaskTextureId> = {
  lip: 'lip-drawn-style-atlas-v1',
  cheek: 'cheek-drawn-mask-v1',
  eye: 'eye-drawn-mask-v1',
  brow: 'brow-soft-arch-fine-hair-v1',
};
const GRADIENT_LIP_MASK_TEXTURE_ID: MaskTextureId =
  'lip-drawn-gradient-density-atlas-v1';
export const DEFAULT_REGION_RECIPES: Record<RecipeRegion, RegionRecipe> = {
  lip: {
    color: DEFAULT_RECIPE_COLOR,
    opacity: 0.9,
    intensity: 0.84,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip,
  },
  cheek: {
    color: RECIPE_COLOR_OPTIONS[1],
    opacity: 0.52,
    intensity: DEFAULT_TEXTURE_SAMPLE_BY_REGION.cheek.intensity,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.cheek,
  },
  eye: {
    color: DEFAULT_RECIPE_COLOR,
    opacity: 0.54,
    intensity: DEFAULT_TEXTURE_SAMPLE_BY_REGION.eye.intensity,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.eye,
  },
  brow: {
    color: BROW_COLOR_OPTIONS[1],
    opacity: 0.68,
    intensity: DEFAULT_TEXTURE_SAMPLE_BY_REGION.brow.intensity,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.brow,
  },
};
export const DEFAULT_REGION_TUNING: Record<
  RecipeRegion,
  RegionTuningParameters
> = {
  lip: buildDefaultRegionTuningForSample(
    'lip',
    DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip,
  ),
  cheek: buildDefaultRegionTuningForSample(
    'cheek',
    DEFAULT_TEXTURE_SAMPLE_BY_REGION.cheek,
  ),
  eye: buildDefaultRegionTuningForSample(
    'eye',
    DEFAULT_TEXTURE_SAMPLE_BY_REGION.eye,
  ),
  brow: buildDefaultRegionTuningForSample(
    'brow',
    DEFAULT_TEXTURE_SAMPLE_BY_REGION.brow,
  ),
};
export const DEFAULT_DEBUG_DISPLAY_OPTIONS: DebugDisplayOptions = {
  maskOverlayVisible: true,
  guideOverlayVisible: true,
  meshOverlayVisible: false,
  diagnosticsHudVisible: true,
  maskDebugViewMode: 'final',
};
const MASK_TEXTURE_OPTIONS_BY_REGION: Record<
  RecipeRegion,
  { id: MaskTextureId; label: string }[]
> = {
  lip: [
    { id: 'lip-drawn-style-atlas-v1', label: 'Atlas' },
    { id: 'lip-vision-boundary-v1', label: 'Vision' },
    { id: 'lip-drawn-mask-v1', label: 'Flat' },
  ],
  cheek: [
    { id: 'cheek-drawn-mask-v1', label: 'Drawn' },
    { id: 'cheek-smooth-mask-v1', label: 'Smooth' },
  ],
  eye: [
    { id: 'eye-drawn-mask-v1', label: 'Drawn' },
    { id: 'eye-smooth-mask-v1', label: 'Smooth' },
  ],
  brow: [
    { id: 'brow-soft-arch-fine-hair-v1', label: 'Soft arch fine' },
    { id: 'brow-back-arch-soft-mix-v1', label: 'Back arch soft' },
    { id: 'brow-slim-tail-fine-hair-v1', label: 'Slim tail fine' },
    { id: 'brow-drawn-mask-v1', label: 'Legacy drawn' },
  ],
};

function resolveMaskTextureIdForRecipe(
  region: RecipeRegion,
  textureSample: RecipeTextureSample,
): MaskTextureId {
  if (region === 'lip' && textureSample.name === 'gradient_lip') {
    return GRADIENT_LIP_MASK_TEXTURE_ID;
  }

  return DEFAULT_MASK_TEXTURE_ID_BY_REGION[region];
}

export function getSelectedMaskTextureOptionId(
  region: RecipeRegion,
  maskTextureId: MaskTextureId,
): MaskTextureId {
  if (
    region === 'lip' &&
    (maskTextureId === GRADIENT_LIP_MASK_TEXTURE_ID ||
      maskTextureId === 'lip-style-atlas-v1')
  ) {
    return 'lip-drawn-style-atlas-v1';
  }

  return maskTextureId;
}

function resolveMaskTextureIdForUiOption(
  region: RecipeRegion,
  maskTextureId: MaskTextureId,
  lipAreaStyle: LipAreaStyle,
): MaskTextureId {
  if (
    region === 'lip' &&
    maskTextureId === 'lip-drawn-style-atlas-v1' &&
    lipAreaStyle === 'gradient'
  ) {
    return GRADIENT_LIP_MASK_TEXTURE_ID;
  }

  return maskTextureId;
}

function formatMaskTextureSummary(
  region: RecipeRegion,
  maskTextureId: MaskTextureId,
) {
  if (region === 'lip') {
    if (maskTextureId === 'lip-vision-boundary-v1') {
      return 'Vision';
    }

    if (maskTextureId === 'lip-drawn-mask-v1') {
      return 'Flat';
    }

    if (maskTextureId === GRADIENT_LIP_MASK_TEXTURE_ID) {
      return 'Atlas gradient';
    }

    return 'Atlas';
  }

  return maskTextureId.replace(/-v1$/, '').split('-').join(' ');
}

function buildDefaultRegionTuningForSample(
  region: RecipeRegion,
  textureSample: RecipeTextureSample,
): RegionTuningParameters {
  return {
    feather: textureSample.feather,
    coverage: textureSample.coverage,
    roughness: textureSample.roughness,
    specular: textureSample.specular,
    specularPower: textureSample.specularPower,
    glossBoost: textureSample.glossBoost,
    gradientAmount: textureSample.gradientAmount,
    preserveDetail: textureSample.preserveDetail,
    maskTextureId: resolveMaskTextureIdForRecipe(region, textureSample),
  };
}

function resolveRegionTuning(
  region: RecipeRegion,
  textureSample: RecipeTextureSample,
  regionTuning?: Record<RecipeRegion, RegionTuningParameters>,
) {
  return regionTuning?.[region] ?? buildDefaultRegionTuningForSample(
    region,
    textureSample,
  );
}
export const DEFAULT_ACTIVE_REGIONS: ActiveRegionMap = {
  lip: true,
  cheek: false,
  eye: false,
  brow: false,
};
const INTENSITY_STEP = 0.05;
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
  'recipe_applied',
] as const;

export function buildValidationRecipeBatchPayload(
  recipes: Record<RecipeRegion, RegionRecipe>,
  enabledRegions: ActiveRegionMap,
  focusRegion: RecipeRegion,
  rendererMode: RendererMode,
  sentAtMs: number,
  regionTuning?: Record<RecipeRegion, RegionTuningParameters>,
  debugDisplay: DebugDisplayOptions = DEFAULT_DEBUG_DISPLAY_OPTIONS,
) {
  const lookId = E7_LIP_LOOK_ID;
  const recipeBatchId = `${E7_RECIPE_PREFIX}-batch-${Math.round(sentAtMs)}`;
  const activeRegionSummary = formatActiveRegionSummary(enabledRegions);
  const enabledLayerCount = countActiveRegions(enabledRegions);
  const layers = RECIPE_REGION_OPTIONS.map(region => {
    const recipe = recipes[region];
    const sample = recipe.textureSample;
    const tuning = resolveRegionTuning(region, sample, regionTuning);
    const layerIntensity = recipe.intensity;
    const maskTextureId = tuning.maskTextureId;
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
      layerCount: RECIPE_REGION_OPTIONS.length,
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
      feather: tuning.feather,
      blendMode: sample.blendMode,
      enabled: enabledRegions[region],
      coverage: tuning.coverage,
      finish: sample.finish,
      textureAmount: layerIntensity,
      roughness: tuning.roughness,
      specular: tuning.specular,
      specularPower: tuning.specularPower,
      glossBoost: tuning.glossBoost,
      gradientAmount: tuning.gradientAmount,
      shimmer: sample.name === 'shimmer_eye' ? layerIntensity : 0,
      shimmerColor:
        sample.name === 'shimmer_eye' ? sample.secondaryColor : '#FFFFFF',
      skinAdaptive: false,
      preserveDetail: tuning.preserveDetail,
      materialId: `${sample.name}-validation-material`,
      shaderMode:
        region === 'lip'
          ? 'lip-style-atlas-validation'
          : 'unlit-alpha-validation',
      passCount: getRecipePassCount(sample),
      maskTextureId,
      cameraBackdropAvailable: false,
      lightEstimateAvailable: false,
    };
  });
  const focusSample = recipes[focusRegion].textureSample;
  const focusTuning = resolveRegionTuning(
    focusRegion,
    focusSample,
    regionTuning,
  );
  const focusMaskTextureId = focusTuning.maskTextureId;
  const focusIntensity = recipes[focusRegion].intensity;

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
    debugDisplay,
    texture: focusSample.name,
    sample: focusSample.name,
    textureMode: focusSample.textureMode,
    secondaryColor: focusSample.secondaryColor,
    coverage: focusTuning.coverage,
    finish: focusSample.finish,
    textureAmount: focusIntensity,
    roughness: focusTuning.roughness,
    specular: focusTuning.specular,
    specularPower: focusTuning.specularPower,
    glossBoost: focusTuning.glossBoost,
    gradientAmount: focusTuning.gradientAmount,
    shimmer: focusSample.name === 'shimmer_eye' ? focusIntensity : 0,
    shimmerColor:
      focusSample.name === 'shimmer_eye'
        ? focusSample.secondaryColor
        : '#FFFFFF',
    skinAdaptive: false,
    preserveDetail: focusTuning.preserveDetail,
    materialId: `${focusSample.name}-validation-material`,
    shaderMode:
      focusRegion === 'lip'
        ? 'lip-style-atlas-validation'
        : 'unlit-alpha-validation',
    passCount: getRecipePassCount(focusSample),
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
  regionTuning?: Record<RecipeRegion, RegionTuningParameters>,
  debugDisplay: DebugDisplayOptions = DEFAULT_DEBUG_DISPLAY_OPTIONS,
) {
  return JSON.stringify(
    buildValidationRecipeBatchPayload(
      recipes,
      enabledRegions,
      focusRegion,
      rendererMode,
      sentAtMs,
      regionTuning,
      debugDisplay,
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
  rendererId?: string;
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
  const windowDimensions = useWindowDimensions();
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
  const [regionRecipes, setRegionRecipes] = useState<
    Record<RecipeRegion, RegionRecipe>
  >(DEFAULT_REGION_RECIPES);
  const [lipFinishType, setLipFinishType] = useState<LipFinishType>(
    DEFAULT_LIP_FINISH_TYPE,
  );
  const [lipAreaStyle, setLipAreaStyle] = useState<LipAreaStyle>(
    DEFAULT_LIP_AREA_STYLE,
  );
  const [regionTuning, setRegionTuning] = useState<
    Record<RecipeRegion, RegionTuningParameters>
  >(DEFAULT_REGION_TUNING);
  const [debugDisplayOptions, setDebugDisplayOptions] =
    useState<DebugDisplayOptions>(DEFAULT_DEBUG_DISPLAY_OPTIONS);
  const [isTuningPanelExpanded, setIsTuningPanelExpanded] = useState(true);
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
      tuning: Record<RecipeRegion, RegionTuningParameters>,
      displayOptions: DebugDisplayOptions,
    ) => {
      return buildValidationRecipeBatchJson(
        recipes,
        enabledRegions,
        focusRegion,
        rendererMode,
        sentAtMs,
        tuning,
        displayOptions,
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
      tuning = regionTuning,
      displayOptions = debugDisplayOptions,
    ) => {
      const sentAtMs = Date.now();
      const recipeJson = buildRecipeBatchJson(
        recipes,
        enabledRegions,
        focusRegion,
        rendererMode,
        sentAtMs,
        tuning,
        displayOptions,
      );
      const activeRegionSummary = formatActiveRegionSummary(enabledRegions);
      const focusMaskTextureId = resolveRegionTuning(
        focusRegion,
        recipes[focusRegion].textureSample,
        tuning,
      ).maskTextureId;
      const lipMaskTextureId = resolveRegionTuning(
        'lip',
        recipes.lip.textureSample,
        tuning,
      ).maskTextureId;
      console.log(
        '[E7] rn_texture_recipe_batch_post',
        `rendererMode=${rendererMode}`,
        `lookId=${E7_LIP_LOOK_ID}`,
        `activeRegions=${activeRegionSummary}`,
        `enabledLayerCount=${countActiveRegions(enabledRegions)}`,
        `focusRegion=${focusRegion}`,
        `focusMaskTextureId=${focusMaskTextureId}`,
        `lipMaskTextureId=${lipMaskTextureId}`,
        `maskOverlayVisible=${String(displayOptions.maskOverlayVisible)}`,
        `guideOverlayVisible=${String(displayOptions.guideOverlayVisible)}`,
        `meshOverlayVisible=${String(displayOptions.meshOverlayVisible)}`,
        `diagnosticsHudVisible=${String(
          displayOptions.diagnosticsHudVisible,
        )}`,
        `maskDebugViewMode=${displayOptions.maskDebugViewMode}`,
        `payloadBytes=${recipeJson.length}`,
        `sentAtMs=${sentAtMs}`,
      );
      unityRef.current?.postMessage('RNBridge', 'ApplyRecipeJson', recipeJson);
    },
    [
      activeRegions,
      buildRecipeBatchJson,
      debugDisplayOptions,
      focusedRegion,
      regionTuning,
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
        lookId: payload.lookId ?? E7_LIP_LOOK_ID,
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
    (
      visible: boolean,
      reason: string,
      displayOptions: DebugDisplayOptions = debugDisplayOptions,
    ) => {
      const maskOverlayVisible =
        visible && displayOptions.maskOverlayVisible;
      const guideOverlayVisible =
        visible && displayOptions.guideOverlayVisible;
      const meshOverlayVisible =
        visible && displayOptions.meshOverlayVisible;
      const payloadJson = JSON.stringify({
        visible,
        maskOverlayVisible,
        guideOverlayVisible,
        meshOverlayVisible,
        guideOverlayMode: DEBUG_GUIDE_OVERLAY_MODE,
        meshRenderMode: DEBUG_MESH_RENDER_MODE,
        diagnosticsHudVisible: displayOptions.diagnosticsHudVisible,
        maskDebugViewMode: displayOptions.maskDebugViewMode,
        validationViewMode,
        reason,
        entryCount,
      });

      console.log(
        '[E7] rn_region_overlay_visibility_post',
        `visible=${visible}`,
        `maskOverlayVisible=${maskOverlayVisible}`,
        `guideOverlayVisible=${guideOverlayVisible}`,
        `meshOverlayVisible=${meshOverlayVisible}`,
        `diagnosticsHudVisible=${displayOptions.diagnosticsHudVisible}`,
        `maskDebugViewMode=${displayOptions.maskDebugViewMode}`,
        'guideColor=green',
        'meshColor=yellow',
        `meshRenderMode=${DEBUG_MESH_RENDER_MODE}`,
        `guideOverlayMode=${DEBUG_GUIDE_OVERLAY_MODE}`,
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
    [debugDisplayOptions, entryCount, validationViewMode],
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
  const focusedTuning = regionTuning[focusedRegion];
  const selectedColor = focusedRecipe.color;
  const selectedTextureSample = focusedRecipe.textureSample;
  const colorOptionsForFocusedRegion = COLOR_OPTIONS_BY_REGION[focusedRegion];
  const textureOptionsForFocusedRegion = RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureSample => textureSample.region === focusedRegion,
  );
  const activeRegionSummary = formatActiveRegionSummary(activeRegions);
  const focusedIntensity = focusedRecipe.intensity;
  const latestMetric = unityEventStatus.e7_metric_sample?.parsed;
  const latestLifecycle = unityEventStatus.face_lifecycle?.parsed;
  const latestRecipe = unityEventStatus.recipe_applied?.parsed;
  const latestSnapshot = unityEventStatus.face_feature_snapshot?.parsed;
  const unityInitializedAt =
    unityEventStatus.unity_initialized?.receivedAtMs ?? 0;

  useEffect(() => {
    postRegionOverlayVisibility(
      validationViewMode !== 'clean',
      'validation_view_mode_changed',
    );
  }, [postRegionOverlayVisibility, validationViewMode, unityInitializedAt]);

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
  const showDiagnosticsHud =
    showCompactControls && debugDisplayOptions.diagnosticsHudVisible;
  const parameterPanelMaxHeight = Math.floor(windowDimensions.height * 0.48);
  const tuningScrollMaxHeight = Math.max(
    96,
    parameterPanelMaxHeight - (showDiagnosticsHud ? 150 : 92),
  );

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

  const updateFocusedRecipeValue = useCallback(
    (key: 'opacity' | 'intensity', nextValue: number) => {
      const nextRecipe = {
        ...regionRecipes[focusedRegion],
        [key]: nextValue,
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
      const nextTuning = {
        ...regionTuning,
        [focusedRegion]: buildDefaultRegionTuningForSample(
          focusedRegion,
          textureSample,
        ),
      };

      setRegionRecipes(nextRecipes);
      setActiveRegions(nextActiveRegions);
      setRegionTuning(nextTuning);
      postRecipeBatch(
        nextRecipes,
        nextActiveRegions,
        focusedRegion,
        selectedRendererMode,
        nextTuning,
      );
    },
    [
      activeRegions,
      focusedRegion,
      postRecipeBatch,
      regionRecipes,
      regionTuning,
      selectedRendererMode,
    ],
  );

  const applyLipTextureAxes = useCallback(
    (finishType: LipFinishType, areaStyle: LipAreaStyle) => {
      const textureSample = composeLipTextureSample(finishType, areaStyle);
      const nextRecipes = {
        ...regionRecipes,
        lip: {
          ...regionRecipes.lip,
          textureSample,
        },
      };
      const nextActiveRegions = {
        ...activeRegions,
        lip: true,
      };
      const nextTuning = {
        ...regionTuning,
        lip: buildDefaultRegionTuningForSample('lip', textureSample),
      };

      setLipFinishType(finishType);
      setLipAreaStyle(areaStyle);
      setFocusedRegion('lip');
      setRegionRecipes(nextRecipes);
      setActiveRegions(nextActiveRegions);
      setRegionTuning(nextTuning);
      postRecipeBatch(
        nextRecipes,
        nextActiveRegions,
        'lip',
        selectedRendererMode,
        nextTuning,
      );
    },
    [
      activeRegions,
      postRecipeBatch,
      regionRecipes,
      regionTuning,
      selectedRendererMode,
    ],
  );

  const selectLipFinishType = useCallback(
    (finishType: LipFinishType) => {
      applyLipTextureAxes(finishType, lipAreaStyle);
    },
    [applyLipTextureAxes, lipAreaStyle],
  );

  const selectLipAreaStyle = useCallback(
    (areaStyle: LipAreaStyle) => {
      applyLipTextureAxes(lipFinishType, areaStyle);
    },
    [applyLipTextureAxes, lipFinishType],
  );

  const updateFocusedTuningValue = useCallback(
    (
      key:
        | 'feather'
        | 'coverage'
        | 'roughness'
        | 'specular'
        | 'specularPower'
        | 'glossBoost'
        | 'gradientAmount',
      nextValue: number,
    ) => {
      const nextTuning = {
        ...regionTuning,
        [focusedRegion]: {
          ...regionTuning[focusedRegion],
          [key]: nextValue,
        },
      };

      setRegionTuning(nextTuning);
      postRecipeBatch(
        regionRecipes,
        activeRegions,
        focusedRegion,
        selectedRendererMode,
        nextTuning,
      );
    },
    [
      activeRegions,
      focusedRegion,
      postRecipeBatch,
      regionRecipes,
      regionTuning,
      selectedRendererMode,
    ],
  );

  const updateFocusedMaskTexture = useCallback(
    (maskTextureId: MaskTextureId) => {
      const resolvedMaskTextureId = resolveMaskTextureIdForUiOption(
        focusedRegion,
        maskTextureId,
        lipAreaStyle,
      );
      const nextTuning = {
        ...regionTuning,
        [focusedRegion]: {
          ...regionTuning[focusedRegion],
          maskTextureId: resolvedMaskTextureId,
        },
      };

      setRegionTuning(nextTuning);
      postRecipeBatch(
        regionRecipes,
        activeRegions,
        focusedRegion,
        selectedRendererMode,
        nextTuning,
      );
    },
    [
      activeRegions,
      focusedRegion,
      lipAreaStyle,
      postRecipeBatch,
      regionRecipes,
      regionTuning,
      selectedRendererMode,
    ],
  );

  const toggleFocusedPreserveDetail = useCallback(() => {
    const nextTuning = {
      ...regionTuning,
      [focusedRegion]: {
        ...regionTuning[focusedRegion],
        preserveDetail: !regionTuning[focusedRegion].preserveDetail,
      },
    };

    setRegionTuning(nextTuning);
    postRecipeBatch(
      regionRecipes,
      activeRegions,
      focusedRegion,
      selectedRendererMode,
      nextTuning,
    );
  }, [
    activeRegions,
    focusedRegion,
    postRecipeBatch,
    regionRecipes,
    regionTuning,
    selectedRendererMode,
  ]);

  const resetFocusedRegion = useCallback(() => {
    const nextRecipes = {
      ...regionRecipes,
      [focusedRegion]: DEFAULT_REGION_RECIPES[focusedRegion],
    };
    const nextTuning = {
      ...regionTuning,
      [focusedRegion]: DEFAULT_REGION_TUNING[focusedRegion],
    };

    setRegionRecipes(nextRecipes);
    setRegionTuning(nextTuning);
    if (focusedRegion === 'lip') {
      setLipFinishType(DEFAULT_LIP_FINISH_TYPE);
      setLipAreaStyle(DEFAULT_LIP_AREA_STYLE);
    }
    postRecipeBatch(
      nextRecipes,
      activeRegions,
      focusedRegion,
      selectedRendererMode,
      nextTuning,
    );
  }, [
    activeRegions,
    focusedRegion,
    postRecipeBatch,
    regionRecipes,
    regionTuning,
    selectedRendererMode,
  ]);

  const resetAllTuning = useCallback(() => {
    setRegionRecipes(DEFAULT_REGION_RECIPES);
    setRegionTuning(DEFAULT_REGION_TUNING);
    setActiveRegions(DEFAULT_ACTIVE_REGIONS);
    setFocusedRegion(DEFAULT_RECIPE_REGION);
    setLipFinishType(DEFAULT_LIP_FINISH_TYPE);
    setLipAreaStyle(DEFAULT_LIP_AREA_STYLE);
    postRecipeBatch(
      DEFAULT_REGION_RECIPES,
      DEFAULT_ACTIVE_REGIONS,
      DEFAULT_RECIPE_REGION,
      selectedRendererMode,
      DEFAULT_REGION_TUNING,
    );
  }, [postRecipeBatch, selectedRendererMode]);

  const toggleDebugDisplayOption = useCallback(
    (key: BooleanDebugDisplayOption) => {
      const nextDisplayOptions = {
        ...debugDisplayOptions,
        [key]: !debugDisplayOptions[key],
      };

      setDebugDisplayOptions(nextDisplayOptions);
      postRegionOverlayVisibility(
        validationViewMode !== 'clean',
        `${key}_changed`,
        nextDisplayOptions,
      );
      postRecipeBatch(
        regionRecipes,
        activeRegions,
        focusedRegion,
        selectedRendererMode,
        regionTuning,
        nextDisplayOptions,
      );
    },
    [
      activeRegions,
      debugDisplayOptions,
      focusedRegion,
      postRecipeBatch,
      postRegionOverlayVisibility,
      regionRecipes,
      regionTuning,
      selectedRendererMode,
      validationViewMode,
    ],
  );

  const selectMaskDebugViewMode = useCallback(
    (maskDebugViewMode: MaskDebugViewMode) => {
      const nextDisplayOptions = {
        ...debugDisplayOptions,
        maskDebugViewMode,
      };

      setDebugDisplayOptions(nextDisplayOptions);
      postRegionOverlayVisibility(
        validationViewMode !== 'clean',
        'mask_debug_view_mode_changed',
        nextDisplayOptions,
      );
      postRecipeBatch(
        regionRecipes,
        activeRegions,
        focusedRegion,
        selectedRendererMode,
        regionTuning,
        nextDisplayOptions,
      );
    },
    [
      activeRegions,
      debugDisplayOptions,
      focusedRegion,
      postRecipeBatch,
      postRegionOverlayVisibility,
      regionRecipes,
      regionTuning,
      selectedRendererMode,
      validationViewMode,
    ],
  );

  const intensityPercent = Math.round(focusedIntensity * 100);
  const opacityPercent = Math.round(focusedRecipe.opacity * 100);
  const formatTextureLabel = useCallback(
    (textureSample: RecipeTextureSample) => {
      switch (textureSample.name) {
        case 'gloss_lip':
          return 'Glossy';
        case 'gradient_lip':
          return 'Gradient';
        case 'full_lip':
          return 'Full';
        case 'overline_lip':
          return 'Overlip';
        case 'soft_blush':
          return 'Blush';
        case 'shimmer_eye':
          return 'Shimmer';
        case 'natural_brow':
          return 'natural_brow';
        case 'soft_brow':
          return 'soft_brow';
        default:
          return 'Normal';
      }
    },
    [],
  );
  const focusedTextureSummary =
    focusedRegion === 'lip'
      ? `type ${formatLipFinishTypeLabel(
          lipFinishType,
        )} / area ${formatLipAreaStyleLabel(lipAreaStyle)}`
      : `sample ${formatTextureLabel(selectedTextureSample)}`;

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
              !showFullControls && styles.recipePanelCompact,
              { maxHeight: parameterPanelMaxHeight },
            ]}
          >
            <View style={styles.recipePanelHeader}>
              <Text style={styles.recipePanelLabel}>Tune Regions</Text>
              <Text style={styles.recipePanelMetaText} numberOfLines={1}>
                {`active=${activeRegionSummary} / focus ${focusedRegion}`}
              </Text>
            </View>

            <View style={styles.tuningToolbar}>
              <Pressable
                accessibilityRole="button"
                accessibilityState={{ expanded: isTuningPanelExpanded }}
                style={({ pressed }) => [
                  styles.tuningToggleButton,
                  pressed && styles.colorButtonPressed,
                ]}
                onPress={() =>
                  setIsTuningPanelExpanded(isExpanded => !isExpanded)
                }
              >
                <Text style={styles.tuningToggleButtonText}>
                  {isTuningPanelExpanded ? 'Hide Tune' : 'Show Tune'}
                </Text>
              </Pressable>

              <Pressable
                accessibilityRole="switch"
                accessibilityState={{
                  checked: debugDisplayOptions.maskOverlayVisible,
                }}
                style={({ pressed }) => [
                  styles.displayToggleButton,
                  debugDisplayOptions.maskOverlayVisible &&
                    styles.displayToggleButtonSelected,
                  pressed && styles.colorButtonPressed,
                ]}
                onPress={() => toggleDebugDisplayOption('maskOverlayVisible')}
              >
                <Text
                  style={[
                    styles.displayToggleButtonText,
                    debugDisplayOptions.maskOverlayVisible &&
                      styles.displayToggleButtonTextSelected,
                  ]}
                >
                  Mask
                </Text>
              </Pressable>

              <Pressable
                accessibilityRole="switch"
                accessibilityState={{
                  checked: debugDisplayOptions.guideOverlayVisible,
                }}
                style={({ pressed }) => [
                  styles.displayToggleButton,
                  debugDisplayOptions.guideOverlayVisible &&
                    styles.displayToggleButtonSelected,
                  pressed && styles.colorButtonPressed,
                ]}
                onPress={() => toggleDebugDisplayOption('guideOverlayVisible')}
              >
                <Text
                  style={[
                    styles.displayToggleButtonText,
                    debugDisplayOptions.guideOverlayVisible &&
                      styles.displayToggleButtonTextSelected,
                  ]}
                >
                  Guide
                </Text>
              </Pressable>

              <Pressable
                accessibilityRole="switch"
                accessibilityState={{
                  checked: debugDisplayOptions.meshOverlayVisible,
                }}
                style={({ pressed }) => [
                  styles.displayToggleButton,
                  debugDisplayOptions.meshOverlayVisible &&
                    styles.displayToggleButtonSelected,
                  pressed && styles.colorButtonPressed,
                ]}
                onPress={() => toggleDebugDisplayOption('meshOverlayVisible')}
              >
                <Text
                  style={[
                    styles.displayToggleButtonText,
                    debugDisplayOptions.meshOverlayVisible &&
                      styles.displayToggleButtonTextSelected,
                  ]}
                >
                  Mesh
                </Text>
              </Pressable>

              <Pressable
                accessibilityRole="switch"
                accessibilityState={{
                  checked: debugDisplayOptions.diagnosticsHudVisible,
                }}
                style={({ pressed }) => [
                  styles.displayToggleButton,
                  debugDisplayOptions.diagnosticsHudVisible &&
                    styles.displayToggleButtonSelected,
                  pressed && styles.colorButtonPressed,
                ]}
                onPress={() =>
                  toggleDebugDisplayOption('diagnosticsHudVisible')
                }
              >
                <Text
                  style={[
                    styles.displayToggleButtonText,
                    debugDisplayOptions.diagnosticsHudVisible &&
                      styles.displayToggleButtonTextSelected,
                  ]}
                >
                  Diagnostics
                </Text>
              </Pressable>

              {MASK_DEBUG_VIEW_MODE_OPTIONS.map(maskDebugOption => {
                const isSelected =
                  maskDebugOption.id ===
                  debugDisplayOptions.maskDebugViewMode;

                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: isSelected }}
                    key={maskDebugOption.id}
                    testID={`mask-debug-${maskDebugOption.id}`}
                    style={({ pressed }) => [
                      styles.displayToggleButton,
                      isSelected && styles.displayToggleButtonSelected,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={() =>
                      selectMaskDebugViewMode(maskDebugOption.id)
                    }
                  >
                    <Text
                      style={[
                        styles.displayToggleButtonText,
                        isSelected &&
                          styles.displayToggleButtonTextSelected,
                      ]}
                    >
                      {maskDebugOption.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {showDiagnosticsHud && (
              <CompactEvidenceHud
                validationViewMode={validationViewMode}
                activeRegionSummary={activeRegionSummary}
                focusedRegion={focusedRegion}
                latestMetric={latestMetric}
                latestLifecycle={latestLifecycle}
                latestRecipe={latestRecipe}
                recipeLatencyMs={recipeLatencyMs}
              />
            )}

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

            {isTuningPanelExpanded && (
              <ScrollView
                style={[
                  styles.tuningScroll,
                  !showFullControls && styles.tuningScrollCompact,
                  { maxHeight: tuningScrollMaxHeight },
                ]}
                contentContainerStyle={styles.tuningScrollContent}
              >
                <View style={styles.colorButtonRow}>
                  {colorOptionsForFocusedRegion.map(colorOption => {
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
                          {colorOption.name}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                {focusedRegion === 'lip' ? (
                  <>
                    <View style={styles.textureButtonRow}>
                      {LIP_FINISH_TYPE_OPTIONS.map(finishOption => {
                        const isSelected = finishOption.id === lipFinishType;

                        return (
                          <Pressable
                            accessibilityRole="radio"
                            accessibilityState={{ selected: isSelected }}
                            key={finishOption.id}
                            testID={`lip-finish-${finishOption.id}`}
                            style={({ pressed }) => [
                              styles.textureButton,
                              isSelected && styles.textureButtonSelected,
                              pressed && styles.colorButtonPressed,
                            ]}
                            onPress={() => selectLipFinishType(finishOption.id)}
                          >
                            <Text
                              style={[
                                styles.textureButtonText,
                                isSelected && styles.textureButtonTextSelected,
                              ]}
                            >
                              {finishOption.label}
                            </Text>
                          </Pressable>
                        );
                      })}
                    </View>

                    <View style={styles.textureButtonRow}>
                      {LIP_AREA_STYLE_OPTIONS.map(areaOption => {
                        const isSelected = areaOption.id === lipAreaStyle;

                        return (
                          <Pressable
                            accessibilityRole="radio"
                            accessibilityState={{ selected: isSelected }}
                            key={areaOption.id}
                            testID={`lip-area-${areaOption.id}`}
                            style={({ pressed }) => [
                              styles.textureButton,
                              isSelected && styles.textureButtonSelected,
                              pressed && styles.colorButtonPressed,
                            ]}
                            onPress={() => selectLipAreaStyle(areaOption.id)}
                          >
                            <Text
                              style={[
                                styles.textureButtonText,
                                isSelected && styles.textureButtonTextSelected,
                              ]}
                            >
                              {areaOption.label}
                            </Text>
                          </Pressable>
                        );
                      })}
                    </View>
                  </>
                ) : (
                  <View style={styles.textureButtonRow}>
                    {textureOptionsForFocusedRegion.map(textureOption => {
                      const isSelected =
                        textureOption.name === selectedTextureSample.name;

                      return (
                        <Pressable
                          accessibilityRole="button"
                          accessibilityState={{ selected: isSelected }}
                          key={textureOption.name}
                          testID={`${focusedRegion}-finish-${textureOption.name}`}
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
                )}

                <View style={styles.maskSourceRow}>
                  {MASK_TEXTURE_OPTIONS_BY_REGION[focusedRegion].map(
                    maskOption => {
                      const isSelected =
                        maskOption.id ===
                        getSelectedMaskTextureOptionId(
                          focusedRegion,
                          focusedTuning.maskTextureId,
                        );

                      return (
                        <Pressable
                          accessibilityRole="button"
                          accessibilityState={{ selected: isSelected }}
                          key={maskOption.id}
                          testID={`${focusedRegion}-mask-${maskOption.id}`}
                          style={({ pressed }) => [
                            styles.maskSourceButton,
                            isSelected && styles.maskSourceButtonSelected,
                            pressed && styles.colorButtonPressed,
                          ]}
                          onPress={() =>
                            updateFocusedMaskTexture(maskOption.id)
                          }
                        >
                          <Text
                            style={[
                              styles.maskSourceButtonText,
                              isSelected &&
                                styles.maskSourceButtonTextSelected,
                            ]}
                          >
                            {maskOption.label}
                          </Text>
                        </Pressable>
                      );
                    },
                  )}
                </View>

                <ValueSlider
                  label="Opacity"
                  value={focusedRecipe.opacity}
                  width={sliderWidth}
                  fillColor={selectedColor.color}
                  onLayoutWidth={setSliderWidth}
                  onChange={value => updateFocusedRecipeValue('opacity', value)}
                />

                <ValueSlider
                  label="Intensity"
                  value={focusedIntensity}
                  width={sliderWidth}
                  fillColor={selectedColor.color}
                  onLayoutWidth={setSliderWidth}
                  onChange={value =>
                    updateFocusedRecipeValue('intensity', value)
                  }
                />

                <ValueSlider
                  label="Coverage"
                  value={focusedTuning.coverage}
                  width={sliderWidth}
                  fillColor="#FDE68A"
                  onLayoutWidth={setSliderWidth}
                  onChange={value =>
                    updateFocusedTuningValue('coverage', value)
                  }
                />

                <ValueSlider
                  label="Feather"
                  value={focusedTuning.feather}
                  width={sliderWidth}
                  fillColor="#BAE6FD"
                  onLayoutWidth={setSliderWidth}
                  onChange={value => updateFocusedTuningValue('feather', value)}
                />

                <ValueSlider
                  label="Roughness"
                  value={focusedTuning.roughness}
                  width={sliderWidth}
                  fillColor="#D1FAE5"
                  onLayoutWidth={setSliderWidth}
                  onChange={value =>
                    updateFocusedTuningValue('roughness', value)
                  }
                />

                <ValueSlider
                  label="Specular"
                  value={focusedTuning.specular}
                  width={sliderWidth}
                  fillColor="#FBCFE8"
                  onLayoutWidth={setSliderWidth}
                  onChange={value =>
                    updateFocusedTuningValue('specular', value)
                  }
                />

                <ValueSlider
                  label="Glossy"
                  value={focusedTuning.glossBoost}
                  width={sliderWidth}
                  fillColor="#F9A8D4"
                  onLayoutWidth={setSliderWidth}
                  onChange={value =>
                    updateFocusedTuningValue('glossBoost', value)
                  }
                />

                <ValueSlider
                  label="Gradient"
                  value={focusedTuning.gradientAmount}
                  width={sliderWidth}
                  fillColor="#C4B5FD"
                  onLayoutWidth={setSliderWidth}
                  onChange={value =>
                    updateFocusedTuningValue('gradientAmount', value)
                  }
                />

                <View style={styles.tuningActionRow}>
                  <Pressable
                    accessibilityRole="switch"
                    accessibilityState={{
                      checked: focusedTuning.preserveDetail,
                    }}
                    style={({ pressed }) => [
                      styles.tuningActionButton,
                      focusedTuning.preserveDetail &&
                        styles.tuningActionButtonSelected,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={toggleFocusedPreserveDetail}
                  >
                    <Text
                      style={[
                        styles.tuningActionButtonText,
                        focusedTuning.preserveDetail &&
                          styles.tuningActionButtonTextSelected,
                      ]}
                    >
                      Detail
                    </Text>
                  </Pressable>

                  <Pressable
                    accessibilityRole="button"
                    style={({ pressed }) => [
                      styles.tuningActionButton,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={resetFocusedRegion}
                  >
                    <Text style={styles.tuningActionButtonText}>
                      Reset Region
                    </Text>
                  </Pressable>

                  <Pressable
                    accessibilityRole="button"
                    style={({ pressed }) => [
                      styles.tuningActionButton,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={resetAllTuning}
                  >
                    <Text style={styles.tuningActionButtonText}>Reset All</Text>
                  </Pressable>
                </View>

                <Text style={styles.recipeValueText} numberOfLines={4}>
                  active {activeRegionSummary} / focus {focusedRegion} /{' '}
                  {selectedColor.name} {selectedColor.color} / opacity{' '}
                  {opacityPercent}% / intensity {intensityPercent}% / mask{' '}
                  {formatMaskTextureSummary(
                    focusedRegion,
                    focusedTuning.maskTextureId,
                  )}{' '}
                  / {focusedTextureSummary}
                </Text>

                <Text style={styles.recipeAppliedText} numberOfLines={2}>
                  {formatRecipeAppliedSummary(
                    unityEventStatus.recipe_applied?.parsed,
                  )}
                </Text>
              </ScrollView>
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
          ? `look=${String(metric.lookId ?? E7_LIP_LOOK_ID)} active=${String(
              metric.activeRegionSummary ??
                metric.activeRegions ??
                currentRegions,
            )}`
          : `look=${E7_LIP_LOOK_ID} active=${currentRegions}`}
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
    `rendererMode=${selectedRendererMode} look=${E7_LIP_LOOK_ID}`,
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
    case 'e7_vision_lip_boundary':
      return `e7_vision_lip_boundary: ${formatE7VisionLipBoundarySummary(
        parsed,
      )} ${event.receivedAt}`;
    case 'recipe_applied':
      return `${formatRecipeAppliedSummary(parsed)} ${event.receivedAt}`;
  }
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
    event.lookId ?? E7_LIP_LOOK_ID,
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
    `lookId=${String(event.lookId ?? E7_LIP_LOOK_ID)}`,
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
  )} renderer=${String(
    event.rendererId ?? 'n/a',
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
  )} intensity=${String(event.intensity ?? 'n/a')} coverage=${String(
    event.coverage ?? 'n/a',
  )} specular=${String(
    event.specular ?? 'n/a',
  )} gloss=${String(event.glossBoost ?? 'n/a')} gradient=${String(
    event.gradientAmount ?? 'n/a',
  )} preserveDetail=${String(event.preserveDetail ?? 'n/a')} applied=${String(
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

type ValueSliderProps = {
  label: string;
  value: number;
  width: number;
  fillColor: string;
  onLayoutWidth: (width: number) => void;
  onChange: (value: number) => void;
};

function ValueSlider({
  label,
  value,
  width,
  fillColor,
  onLayoutWidth,
  onChange,
}: ValueSliderProps) {
  const clampedWidth = Math.max(width, 1);
  const fillWidth = value * clampedWidth;

  const valueFromEvent = useCallback(
    (event: GestureResponderEvent) => {
      const raw = Math.max(
        0,
        Math.min(event.nativeEvent.locationX, clampedWidth),
      );
      const steppedValue =
        Math.round(raw / clampedWidth / INTENSITY_STEP) * INTENSITY_STEP;

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
      <Text style={styles.opacityLabel} numberOfLines={1}>
        {label}
      </Text>
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
      <Text style={styles.opacityValue} numberOfLines={1}>
        {value.toFixed(2)}
      </Text>
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
    paddingHorizontal: 10,
    paddingVertical: 9,
    gap: 7,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.22)',
  },
  recipePanelCompact: {
    paddingHorizontal: 8,
    paddingVertical: 6,
    gap: 6,
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
  tuningToolbar: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 4,
  },
  tuningToggleButton: {
    minHeight: 26,
    minWidth: 76,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.34)',
    backgroundColor: '#F9FAFB',
    paddingHorizontal: 7,
  },
  tuningToggleButtonText: {
    color: '#111827',
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  displayToggleButton: {
    flexGrow: 1,
    minHeight: 26,
    minWidth: 58,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 6,
  },
  displayToggleButtonSelected: {
    backgroundColor: '#D1FAE5',
    borderColor: '#ECFDF5',
  },
  displayToggleButtonText: {
    color: '#F9FAFB',
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  displayToggleButtonTextSelected: {
    color: '#064E3B',
  },
  tuningScroll: {
    maxHeight: 440,
  },
  tuningScrollCompact: {
    maxHeight: 320,
  },
  tuningScrollContent: {
    gap: 6,
    paddingBottom: 2,
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
    gap: 5,
  },
  regionButton: {
    flex: 1,
    minHeight: 27,
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
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  regionButtonTextSelected: {
    color: '#111827',
  },
  colorButtonRow: {
    flexDirection: 'row',
    gap: 5,
  },
  colorButton: {
    flex: 1,
    minHeight: 28,
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
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0,
    textTransform: 'uppercase',
  },
  textureButtonRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 5,
  },
  textureButton: {
    flexGrow: 1,
    flexBasis: '30%',
    minWidth: 68,
    minHeight: 28,
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
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  textureButtonRegionText: {
    color: '#BAE6FD',
    fontSize: 9,
    fontWeight: '800',
    letterSpacing: 0,
    marginTop: 2,
    textTransform: 'uppercase',
  },
  textureButtonTextSelected: {
    color: '#111827',
  },
  maskSourceRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 5,
  },
  maskSourceButton: {
    flexGrow: 1,
    minHeight: 27,
    minWidth: 64,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 6,
  },
  maskSourceButtonSelected: {
    backgroundColor: '#BAE6FD',
    borderColor: '#E0F2FE',
  },
  maskSourceButtonText: {
    color: '#F9FAFB',
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  maskSourceButtonTextSelected: {
    color: '#0C4A6E',
  },
  opacityControl: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  opacityHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  opacityLabel: {
    color: '#F9FAFB',
    width: 64,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
  },
  opacityValue: {
    color: '#F9FAFB',
    width: 32,
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
    textAlign: 'right',
  },
  sliderTrack: {
    flex: 1,
    height: 18,
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
    width: 14,
    height: 14,
    borderRadius: 8,
    marginLeft: -7,
    backgroundColor: '#FFFFFF',
    borderWidth: 2,
    borderColor: '#111827',
  },
  tuningActionRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 5,
  },
  tuningActionButton: {
    flexGrow: 1,
    minHeight: 27,
    minWidth: 72,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.28)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 6,
  },
  tuningActionButtonSelected: {
    backgroundColor: '#FDE68A',
    borderColor: '#FEF3C7',
  },
  tuningActionButtonText: {
    color: '#F9FAFB',
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
    textTransform: 'uppercase',
  },
  tuningActionButtonTextSelected: {
    color: '#78350F',
  },
  recipeValueText: {
    color: '#F9FAFB',
    fontSize: 10,
    lineHeight: 14,
    letterSpacing: 0,
  },
  recipeAppliedText: {
    color: '#BAE6FD',
    fontSize: 10,
    lineHeight: 13,
    letterSpacing: 0,
  },
});

export default App;
