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
    intensity: 0.72,
    feather: 0.04,
  },
  {
    name: 'soft_blush',
    label: 'soft blush',
    region: 'cheek',
    textureMode: 'sample',
    blendMode: 'normal',
    intensity: 0.6,
    feather: 0.32,
  },
  {
    name: 'shimmer_eye',
    label: 'shimmer eye',
    region: 'eye',
    textureMode: 'sample',
    blendMode: 'screen',
    intensity: 0.82,
    feather: 0.08,
  },
] as const;
const RENDERER_MODE_OPTIONS = [
  { name: 'e3e4-baseline', label: 'Baseline' },
  { name: 'e7-arface-uv-candidate', label: 'E7 UV' },
  { name: 'e7-arface-authored-atlas', label: 'Heuristic' },
] as const;
const ATLAS_VARIANT_OPTIONS = [
  {
    id: 'lip-ring-v0-tight',
    label: 'lip tight',
    region: 'lip',
    status: 'manual lip ring',
  },
  {
    id: 'lip-ring-v0-balanced',
    label: 'lip balanced',
    region: 'lip',
    status: 'default lip ring',
  },
  {
    id: 'lip-ring-v0-wide',
    label: 'lip wide',
    region: 'lip',
    status: 'stress spill check',
  },
  {
    id: 'cheek-soft-v0-balanced',
    label: 'cheek balanced',
    region: 'cheek',
    status: 'default soft cheek',
  },
  {
    id: 'cheek-soft-v0-high',
    label: 'cheek high',
    region: 'cheek',
    status: 'cheekbone emphasis',
  },
  {
    id: 'cheek-soft-v0-wide',
    label: 'cheek wide',
    region: 'cheek',
    status: 'soft-zone spill check',
  },
  {
    id: 'eye-band-v0-tight',
    label: 'eye tight',
    region: 'eye',
    status: 'manual eyelid band',
  },
  {
    id: 'eye-band-v0-balanced',
    label: 'eye balanced',
    region: 'eye',
    status: 'default eyelid band',
  },
  {
    id: 'eye-band-v0-extended',
    label: 'eye extended',
    region: 'eye',
    status: 'stress spill check',
  },
] as const;
const VALIDATION_VIEW_MODE_OPTIONS = [
  { name: 'clean', label: 'Clean' },
  { name: 'compact', label: 'Compact HUD' },
  { name: 'full', label: 'Full Debug' },
] as const;
const E7_BOUNDARY_PLAN_VERSION = 'E7.03 v2.1';
const E7_EVIDENCE_MODE = 'phase2-arface-manual-heuristic-baseline';

type RecipeColor = (typeof RECIPE_COLOR_OPTIONS)[number];
type RecipeRegion = (typeof RECIPE_REGION_OPTIONS)[number];
type RecipeTextureSample = (typeof RECIPE_TEXTURE_SAMPLE_OPTIONS)[number];
type RendererMode = (typeof RENDERER_MODE_OPTIONS)[number]['name'];
type AtlasVariantOption = (typeof ATLAS_VARIANT_OPTIONS)[number];
type AtlasVariantId = AtlasVariantOption['id'];
type ValidationViewMode = (typeof VALIDATION_VIEW_MODE_OPTIONS)[number]['name'];
type RegionRecipe = {
  color: RecipeColor;
  opacity: number;
  textureSample: RecipeTextureSample;
};
type ValidationCandidateOption = {
  id: string;
  label: string;
  status: string;
  rendererMode?: RendererMode;
};

const VALIDATION_CANDIDATE_OPTIONS: ValidationCandidateOption[] = [
  {
    id: 'e3e4-baseline',
    label: 'Baseline',
    status: 'selectable Q1 fallback',
    rendererMode: 'e3e4-baseline',
  },
  {
    id: 'e7-procedural-arface-uv',
    label: 'Procedural UV',
    status: 'selectable rejected baseline',
    rendererMode: 'e7-arface-uv-candidate',
  },
  {
    id: 'arface-authored-atlas',
    label: 'ARFace heuristic',
    status: 'selectable manual ellipse baseline',
    rendererMode: 'e7-arface-authored-atlas',
  },
  {
    id: 'arface-vertex-blendshape',
    label: 'Vertex+blendshape',
    status: 'pending after atlas',
  },
  {
    id: 'apple-vision-ref',
    label: 'Apple Vision ref',
    status: 'offline reference only',
  },
  {
    id: 'mediapipe-ref',
    label: 'MediaPipe ref',
    status: 'offline reference only',
  },
  {
    id: 'parsing-ref',
    label: 'Parsing ref',
    status: 'offline visual cross-check only',
  },
  {
    id: 'hybrid-candidate',
    label: 'Hybrid',
    status: 'future runtime gate',
  },
];

const DEFAULT_RECIPE_REGION: RecipeRegion = 'lip';
const DEFAULT_RECIPE_COLOR = RECIPE_COLOR_OPTIONS[0];
const DEFAULT_RECIPE_OPACITY = 0.65;
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
    opacity: 0.72,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.lip,
  },
  cheek: {
    color: RECIPE_COLOR_OPTIONS[1],
    opacity: 0.46,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.cheek,
  },
  eye: {
    color: DEFAULT_RECIPE_COLOR,
    opacity: DEFAULT_RECIPE_OPACITY,
    textureSample: DEFAULT_TEXTURE_SAMPLE_BY_REGION.eye,
  },
};
const DEFAULT_ATLAS_VARIANT_BY_REGION: Record<RecipeRegion, AtlasVariantId> = {
  lip: 'lip-ring-v0-balanced',
  cheek: 'cheek-soft-v0-balanced',
  eye: 'eye-band-v0-balanced',
};
const OPACITY_STEP = 0.05;
const UNITY_EVENT_HISTORY_LIMIT = 5;
const DEFAULT_RENDERER_MODE: RendererMode = 'e7-arface-authored-atlas';
const UNITY_EVENT_TYPES = [
  'unity_initialized',
  'face_detected',
  'face_lifecycle',
  'face_feature_snapshot',
  'e7_metric_sample',
  'recipe_applied',
] as const;

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
  opacity?: number;
  texture?: string;
  sample?: string;
  textureMode?: string;
  intensity?: number;
  feather?: number;
  blendMode?: string;
  runId?: string;
  rendererMode?: string;
  candidateId?: string;
  variantId?: string;
  maskSource?: string;
  stateAction?: string;
  regionPrecisionStatus?: string;
  regionUvAvailable?: boolean;
  regionBaselineTriangles?: number;
  regionCandidateTriangles?: number;
  regionAppliedTriangles?: number;
  uvAvailable?: boolean;
  baselineTriangles?: number;
  candidateTriangles?: number;
  meshVertexCount?: number;
  meshIndexCount?: number;
  meshUvCount?: number;
  unityFrameworkBuildLabel?: string;
  lookId?: string;
  recipeId?: string;
  sentAtMs?: number;
  appliedAtMs?: number;
  appliedFrame?: number;
  receivedAtMs?: number;
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
  usedFallback?: boolean;
  atlasVersion?: string;
  atlasLabelMapVersion?: string;
  atlasLabelGroup?: string;
  atlasConfigSummary?: string;
  atlasConfigHash?: string;
  topologyAuditStatus?: string;
  topologyAuditSummary?: string;
  atlasVertexLabelSummary?: string;
  atlasDataFallback?: boolean;
  atlasFallbackReason?: string;
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
        <Text style={styles.kicker}>E7.3</Text>
        <Text style={styles.title}>Region Precision</Text>
        <Text style={styles.statusLabel}>Validation status</Text>
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
  const [selectedRendererMode, setSelectedRendererMode] =
    useState<RendererMode>(DEFAULT_RENDERER_MODE);
  const [selectedRegion, setSelectedRegion] = useState<RecipeRegion>(
    DEFAULT_RECIPE_REGION,
  );
  const [regionRecipes, setRegionRecipes] = useState<
    Record<RecipeRegion, RegionRecipe>
  >(DEFAULT_REGION_RECIPES);
  const [selectedAtlasVariantByRegion, setSelectedAtlasVariantByRegion] =
    useState<Record<RecipeRegion, AtlasVariantId>>(
      DEFAULT_ATLAS_VARIANT_BY_REGION,
    );
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

  const buildRecipeJson = useCallback(
    (
      region: RecipeRegion,
      recipe: RegionRecipe,
      rendererMode: RendererMode,
      atlasVariantId: AtlasVariantId,
      sentAtMs: number,
    ) => {
      const isRegionPrecision = rendererMode !== 'e3e4-baseline';
      const candidateId = getCandidateIdForRenderer(rendererMode);
      const variantId = getVariantIdForRenderer(
        rendererMode,
        region,
        atlasVariantId,
      );
      const lookId = isRegionPrecision
        ? 'e7_region_precision_debug'
        : 'baseline_debug_mask';
      const recipePrefix =
        rendererMode === 'e7-arface-authored-atlas'
          ? 'e7-region-precision-atlas'
          : rendererMode === 'e7-arface-uv-candidate'
          ? 'e7-region-precision'
          : 'e7-baseline';
      const recipeId = `${recipePrefix}-${region}-${
        recipe.textureSample.name
      }-${variantId}-${Math.round(sentAtMs)}`;

      return JSON.stringify({
        version: 1,
        recipeId,
        lookId,
        sentAtMs,
        rendererMode,
        candidateId,
        variantId,
        region,
        texture: recipe.textureSample.name,
        sample: recipe.textureSample.name,
        textureMode: recipe.textureSample.textureMode,
        layers: [
          {
            id: `${region}-${recipe.textureSample.name}`,
            recipeId,
            lookId,
            sentAtMs,
            rendererMode,
            candidateId,
            variantId,
            region,
            layer: region,
            color: recipe.color.color,
            opacity: recipe.opacity,
            texture: recipe.textureSample.name,
            sample: recipe.textureSample.name,
            textureMode: recipe.textureSample.textureMode,
            intensity: recipe.textureSample.intensity,
            feather: recipe.textureSample.feather,
            blendMode: recipe.textureSample.blendMode,
            enabled: true,
          },
        ],
      });
    },
    [],
  );

  const postRecipe = useCallback(
    (
      region: RecipeRegion,
      recipe: RegionRecipe,
      rendererMode = selectedRendererMode,
      atlasVariantId = selectedAtlasVariantByRegion[region],
    ) => {
      const sentAtMs = Date.now();
      const recipeJson = buildRecipeJson(
        region,
        recipe,
        rendererMode,
        atlasVariantId,
        sentAtMs,
      );
      const candidateId = getCandidateIdForRenderer(rendererMode);
      const variantId = getVariantIdForRenderer(
        rendererMode,
        region,
        atlasVariantId,
      );
      console.log(
        '[E7] rn_texture_recipe_post',
        `rendererMode=${rendererMode}`,
        `candidateId=${candidateId}`,
        `variantId=${variantId}`,
        `lookId=${
          rendererMode !== 'e3e4-baseline'
            ? 'e7_region_precision_debug'
            : 'baseline_debug_mask'
        }`,
        `region=${region}`,
        `color=${recipe.color.color}`,
        `opacity=${recipe.opacity}`,
        `texture=${recipe.textureSample.name}`,
        `mode=${recipe.textureSample.textureMode}`,
        `intensity=${recipe.textureSample.intensity}`,
        `sentAtMs=${sentAtMs}`,
      );
      unityRef.current?.postMessage('RNBridge', 'ApplyRecipeJson', recipeJson);
    },
    [buildRecipeJson, selectedAtlasVariantByRegion, selectedRendererMode],
  );

  const postRecipeAck = useCallback(
    (payload: UnityEventPayload, receivedAtMs: number) => {
      const ackJson = JSON.stringify({
        type: 'recipe_ack',
        runId: payload.runId ?? 'e7-baseline',
        phase: payload.phase ?? 'baseline',
        rendererMode: payload.rendererMode ?? 'e3e4-baseline',
        candidateId: payload.candidateId ?? 'e3e4-baseline',
        variantId: payload.variantId ?? 'baseline-v0',
        lookId: payload.lookId ?? 'baseline_debug_mask',
        recipeId: payload.recipeId ?? 'none',
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
          logE7RecipeLatency(parsed, receivedAtMs);
          postRecipeAck(parsed, receivedAtMs);
        }

        console.log(
          parsed.type === 'face_feature_snapshot'
            ? '[E5] rn_face_feature_snapshot_received'
            : parsed.type === 'e7_metric_sample'
            ? '[E7] rn_metric_sample_received'
            : parsed.type === 'recipe_applied'
            ? '[E7] rn_recipe_applied_received'
            : parsed.type === 'face_lifecycle'
            ? '[E2] rn_unity_message_received'
            : '[M6] rn_unity_message_received',
          parsed.type === 'face_feature_snapshot'
            ? `rawCameraFrameStored=${String(
                readSnapshotPrivacyFlag(parsed, 'rawCameraFrameStored'),
              )} offDeviceUpload=${String(
                readSnapshotPrivacyFlag(parsed, 'offDeviceUpload'),
              )}`
            : '',
          rawMessage,
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
      setUnityEventHistory(currentHistory =>
        [record, ...currentHistory].slice(0, UNITY_EVENT_HISTORY_LIMIT),
      );
    },
    [postRecipeAck],
  );

  useEffect(() => {
    const initialPostTimer = setTimeout(() => {
      postRecipe(
        DEFAULT_RECIPE_REGION,
        DEFAULT_REGION_RECIPES[DEFAULT_RECIPE_REGION],
        selectedRendererMode,
      );
    }, 1000);

    return () => clearTimeout(initialPostTimer);
  }, [postRecipe, selectedRendererMode]);

  const selectedRecipe = regionRecipes[selectedRegion];
  const selectedColor = selectedRecipe.color;
  const selectedTextureSample = selectedRecipe.textureSample;
  const selectedAtlasVariantId = selectedAtlasVariantByRegion[selectedRegion];
  const selectedAtlasVariant = getAtlasVariantOption(selectedAtlasVariantId);
  const atlasVariantsForSelectedRegion =
    getAtlasVariantsForRegion(selectedRegion);
  const opacity = selectedRecipe.opacity;
  const latestMetric = unityEventStatus.e7_metric_sample?.parsed;
  const latestLifecycle = unityEventStatus.face_lifecycle?.parsed;
  const latestRecipe = unityEventStatus.recipe_applied?.parsed;
  const latestSnapshot = unityEventStatus.face_feature_snapshot?.parsed;
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
        selectedAtlasVariantId,
        selectedRegion,
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
      selectedRegion,
      selectedAtlasVariantId,
      selectedRendererMode,
      validationViewMode,
    ],
  );
  const showFullDebug = validationViewMode === 'full';
  const showFullControls = validationViewMode === 'full';
  const showCompactControls = validationViewMode !== 'clean';

  const selectRendererMode = useCallback(
    (rendererMode: RendererMode) => {
      setSelectedRendererMode(rendererMode);
      postRecipe(selectedRegion, selectedRecipe, rendererMode);
    },
    [postRecipe, selectedRecipe, selectedRegion],
  );

  const selectRegion = useCallback(
    (region: RecipeRegion) => {
      setSelectedRegion(region);
      postRecipe(region, regionRecipes[region], selectedRendererMode);
    },
    [postRecipe, regionRecipes, selectedRendererMode],
  );

  const selectColor = useCallback(
    (color: RecipeColor) => {
      const nextRecipe = {
        ...selectedRecipe,
        color,
      };

      setRegionRecipes(currentRecipes => ({
        ...currentRecipes,
        [selectedRegion]: nextRecipe,
      }));
      postRecipe(selectedRegion, nextRecipe);
    },
    [postRecipe, selectedRecipe, selectedRegion],
  );

  const updateOpacity = useCallback(
    (nextOpacity: number) => {
      const nextRecipe = {
        ...selectedRecipe,
        opacity: nextOpacity,
      };

      setRegionRecipes(currentRecipes => ({
        ...currentRecipes,
        [selectedRegion]: nextRecipe,
      }));
      postRecipe(selectedRegion, nextRecipe);
    },
    [postRecipe, selectedRecipe, selectedRegion],
  );

  const selectTextureSample = useCallback(
    (textureSample: RecipeTextureSample) => {
      const nextRegion = textureSample.region;
      const nextRecipe = {
        ...regionRecipes[nextRegion],
        textureSample,
      };

      setSelectedRegion(nextRegion);
      setRegionRecipes(currentRecipes => ({
        ...currentRecipes,
        [nextRegion]: nextRecipe,
      }));
      postRecipe(nextRegion, nextRecipe);
    },
    [postRecipe, regionRecipes],
  );

  const selectAtlasVariant = useCallback(
    (variantId: AtlasVariantId) => {
      const variant = getAtlasVariantOption(variantId);
      if (!variant || variant.region !== selectedRegion) {
        return;
      }

      setSelectedAtlasVariantByRegion(currentVariants => ({
        ...currentVariants,
        [selectedRegion]: variantId,
      }));
      postRecipe(selectedRegion, selectedRecipe, selectedRendererMode, variantId);
    },
    [postRecipe, selectedRecipe, selectedRegion, selectedRendererMode],
  );

  const opacityPercent = Math.round(opacity * 100);

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

        <CompactEvidenceHud
          validationViewMode={validationViewMode}
          selectedRendererMode={selectedRendererMode}
          selectedAtlasVariantId={selectedAtlasVariantId}
          selectedRegion={selectedRegion}
          latestMetric={latestMetric}
          latestLifecycle={latestLifecycle}
          latestRecipe={latestRecipe}
          recipeLatencyMs={recipeLatencyMs}
        />

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
              currentRegion={selectedRegion}
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
            ]}
          >
            <View style={styles.recipePanelHeader}>
              <Text style={styles.recipePanelLabel}>Candidate</Text>
              <Text style={styles.recipePanelMetaText} numberOfLines={1}>
                {`${formatSelectedCandidateId(
                  selectedRendererMode,
                )} / variant=${getVariantIdForRenderer(
                  selectedRendererMode,
                  selectedRegion,
                  selectedAtlasVariantId,
                )} / region=${selectedRegion}`}
              </Text>
            </View>

            <View style={styles.modeButtonRow}>
              {RENDERER_MODE_OPTIONS.map(modeOption => {
                const isSelected = modeOption.name === selectedRendererMode;

                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: isSelected }}
                    key={modeOption.name}
                    style={({ pressed }) => [
                      styles.modeButton,
                      isSelected && styles.modeButtonSelected,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={() => selectRendererMode(modeOption.name)}
                  >
                    <Text
                      style={[
                        styles.modeButtonText,
                        isSelected && styles.modeButtonTextSelected,
                      ]}
                    >
                      {modeOption.label}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {showFullControls && (
              <View style={styles.candidateCatalog}>
                {VALIDATION_CANDIDATE_OPTIONS.map(candidateOption => {
                  const isSelected =
                    candidateOption.rendererMode === selectedRendererMode;
                  const isPending = !candidateOption.rendererMode;

                  return (
                    <View
                      key={candidateOption.id}
                      style={[
                        styles.candidateCatalogRow,
                        isSelected && styles.candidateCatalogRowSelected,
                        isPending && styles.candidateCatalogRowPending,
                      ]}
                    >
                      <Text
                        style={[
                          styles.candidateCatalogText,
                          isSelected && styles.candidateCatalogTextSelected,
                        ]}
                        numberOfLines={1}
                      >
                        {candidateOption.id}
                      </Text>
                      <Text
                        style={styles.candidateCatalogStatusText}
                        numberOfLines={1}
                      >
                        {candidateOption.status}
                      </Text>
                    </View>
                  );
                })}
              </View>
            )}

            {showFullControls &&
              selectedRendererMode === 'e7-arface-authored-atlas' && (
                <View style={styles.variantPanel}>
                  <Text style={styles.debugSubLabel}>Heuristic variant</Text>
                  <View style={styles.variantButtonRow}>
                    {atlasVariantsForSelectedRegion.map(variantOption => {
                      const isSelected =
                        variantOption.id === selectedAtlasVariantId;

                      return (
                        <Pressable
                          accessibilityRole="button"
                          accessibilityState={{ selected: isSelected }}
                          key={variantOption.id}
                          style={({ pressed }) => [
                            styles.variantButton,
                            isSelected && styles.variantButtonSelected,
                            pressed && styles.colorButtonPressed,
                          ]}
                          onPress={() => selectAtlasVariant(variantOption.id)}
                        >
                          <Text
                            style={[
                              styles.variantButtonText,
                              isSelected && styles.variantButtonTextSelected,
                            ]}
                            numberOfLines={1}
                          >
                            {variantOption.label}
                          </Text>
                          <Text
                            style={styles.variantStatusText}
                            numberOfLines={1}
                          >
                            {variantOption.status}
                          </Text>
                        </Pressable>
                      );
                    })}
                  </View>
                  <Text style={styles.recipePanelMetaText} numberOfLines={1}>
                    {`selected=${selectedAtlasVariant?.id ?? selectedAtlasVariantId}`}
                  </Text>
                </View>
              )}

            <View style={styles.regionButtonRow}>
              {RECIPE_REGION_OPTIONS.map(regionOption => {
                const isSelected = regionOption === selectedRegion;

                return (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityState={{ selected: isSelected }}
                    key={regionOption}
                    style={({ pressed }) => [
                      styles.regionButton,
                      isSelected && styles.regionButtonSelected,
                      pressed && styles.colorButtonPressed,
                    ]}
                    onPress={() => selectRegion(regionOption)}
                  >
                    <Text
                      style={[
                        styles.regionButtonText,
                        isSelected && styles.regionButtonTextSelected,
                      ]}
                    >
                      {regionOption}
                    </Text>
                  </Pressable>
                );
              })}
            </View>

            {showFullControls && (
              <>
                <View style={styles.colorButtonRow}>
                  {RECIPE_COLOR_OPTIONS.map(colorOption => {
                    const isSelected = colorOption.name === selectedColor.name;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={colorOption.name}
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

                <View style={styles.textureButtonRow}>
                  {RECIPE_TEXTURE_SAMPLE_OPTIONS.map(textureOption => {
                    const isSelected =
                      textureOption.name === selectedTextureSample.name;
                    const isCurrentRegion =
                      textureOption.region === selectedRegion;

                    return (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityState={{ selected: isSelected }}
                        key={textureOption.name}
                        style={({ pressed }) => [
                          styles.textureButton,
                          isSelected && styles.textureButtonSelected,
                          isCurrentRegion && styles.textureButtonCurrentRegion,
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
                          {textureOption.name}
                        </Text>
                        <Text
                          style={[
                            styles.textureButtonRegionText,
                            isSelected && styles.textureButtonTextSelected,
                          ]}
                        >
                          {textureOption.region}
                        </Text>
                      </Pressable>
                    );
                  })}
                </View>

                <OpacitySlider
                  value={opacity}
                  width={sliderWidth}
                  onLayoutWidth={setSliderWidth}
                  onChange={updateOpacity}
                />

                <Text style={styles.recipeValueText} numberOfLines={3}>
                  renderer {selectedRendererMode} / region {selectedRegion} /{' '}
                  {selectedColor.name} {selectedColor.color} / opacity{' '}
                  {opacityPercent}% / texture {selectedTextureSample.name} /
                  mode {selectedTextureSample.textureMode} / intensity{' '}
                  {selectedTextureSample.intensity.toFixed(2)} / variant{' '}
                  {getVariantIdForRenderer(
                    selectedRendererMode,
                    selectedRegion,
                    selectedAtlasVariantId,
                  )}
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
  currentRegion: RecipeRegion;
  metricRecord?: UnityEventRecord;
  recipeRecord?: UnityEventRecord;
};

function E7StatusPanel({
  currentRegion,
  metricRecord,
  recipeRecord,
}: E7StatusPanelProps) {
  const metric = metricRecord?.parsed;
  const recipe = recipeRecord?.parsed;
  const latencyMs = getRecipeAckLatencyMs(recipe, recipeRecord?.receivedAtMs);

  return (
    <View style={styles.e7Panel}>
      <View style={styles.e7Header}>
        <Text style={styles.e7Label}>E7.3 precision</Text>
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
          ? `phase=${String(metric.phase ?? 'baseline')} look=${String(
              metric.lookId ?? 'baseline_debug_mask',
            )} mode=${String(
              metric.rendererMode ?? 'e3e4-baseline',
            )} candidate=${String(
              metric.candidateId ?? 'n/a',
            )} variant=${String(metric.variantId ?? 'n/a')} region=${String(
              metric.region ?? currentRegion,
            )}`
          : `look=baseline_debug_mask mode=e3e4-baseline region=${currentRegion}`}
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
          ? `mask=${String(metric.maskSource ?? 'centroid_broad')} uv=${String(
              metric.regionUvAvailable ?? metric.uvAvailable ?? false,
            )} base=${String(
              metric.regionBaselineTriangles ??
                metric.baselineTriangles ??
                'n/a',
            )} cand=${String(
              metric.regionCandidateTriangles ??
                metric.candidateTriangles ??
                'n/a',
            )}`
          : 'region precision waiting'}
      </Text>
      <Text style={styles.e7Text} numberOfLines={1}>
        {metric || recipe
          ? `topology=${String(
              metric?.topologyAuditStatus ??
                recipe?.topologyAuditStatus ??
                'not_run',
            )} atlas=${String(
              metric?.atlasVersion ?? recipe?.atlasVersion ?? 'none',
            )} hash=${String(
              metric?.atlasConfigHash ?? recipe?.atlasConfigHash ?? 'none',
            )}`
          : 'heuristic audit waiting'}
      </Text>
      <Text style={styles.e7Text} numberOfLines={1}>
        {metric || recipe
          ? `label=${String(
              metric?.atlasLabelGroup ?? recipe?.atlasLabelGroup ?? 'none',
            )} fallback=${String(
              metric?.atlasDataFallback ?? recipe?.atlasDataFallback ?? false,
            )} reason=${String(
              metric?.atlasFallbackReason ?? recipe?.atlasFallbackReason ?? 'none',
            )}`
          : 'manual label waiting'}
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
  selectedRendererMode: RendererMode;
  selectedAtlasVariantId: AtlasVariantId;
  selectedRegion: RecipeRegion;
  latestMetric?: UnityEventPayload;
  latestLifecycle?: UnityEventPayload;
  latestRecipe?: UnityEventPayload;
  recipeLatencyMs?: number;
};

function CompactEvidenceHud({
  validationViewMode,
  selectedRendererMode,
  selectedAtlasVariantId,
  selectedRegion,
  latestMetric,
  latestLifecycle,
  latestRecipe,
  recipeLatencyMs,
}: CompactEvidenceHudProps) {
  if (validationViewMode === 'clean') {
    return null;
  }

  const candidateId = formatSelectedCandidateId(selectedRendererMode);
  const variantId = getVariantIdForRenderer(
    selectedRendererMode,
    selectedRegion,
    selectedAtlasVariantId,
  );
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
        <Text style={styles.compactHudLabel}>E7.03 HUD</Text>
        <Text style={styles.compactHudBadge}>{validationViewMode}</Text>
      </View>
      <Text style={styles.compactHudText} numberOfLines={1}>
        {`candidate=${candidateId} variant=${variantId} region=${selectedRegion}`}
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
  selectedAtlasVariantId: AtlasVariantId;
  selectedRegion: RecipeRegion;
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
  selectedAtlasVariantId,
  selectedRegion,
  latestMetric,
  latestLifecycle,
  latestRecipe,
  latestSnapshot,
  lastUnityEvent,
}: EvidenceMetadataInput) {
  const candidateId = formatSelectedCandidateId(selectedRendererMode);
  const selectedVariantId = getVariantIdForRenderer(
    selectedRendererMode,
    selectedRegion,
    selectedAtlasVariantId,
  );
  const latencyMs = getRecipeAckLatencyMs(
    latestRecipe,
    latestRecipe?.receivedAtMs,
  );
  const meshSource = latestMetric ?? latestSnapshot;
  const candidateOption = getValidationCandidateOption(selectedRendererMode);

  return [
    `evidenceMode=${E7_EVIDENCE_MODE} plan=${E7_BOUNDARY_PLAN_VERSION}`,
    `entry=${entryCount} mounted=${mountedAt} viewMode=${validationViewMode}`,
    `candidateId=${candidateId} rendererMode=${selectedRendererMode} status=${
      candidateOption?.status ?? 'unknown'
    }`,
    `variantId=${selectedVariantId} eventVariant=${formatLifecycleValue(
      latestRecipe?.variantId ?? latestMetric?.variantId,
    )}`,
    `region=${selectedRegion} metricRegion=${formatLifecycleValue(
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
    `atlas=${String(
      latestMetric?.atlasVersion ?? latestRecipe?.atlasVersion ?? 'none',
    )} labelMap=${String(
      latestMetric?.atlasLabelMapVersion ??
        latestRecipe?.atlasLabelMapVersion ??
        'none',
    )} labelGroup=${String(
      latestMetric?.atlasLabelGroup ?? latestRecipe?.atlasLabelGroup ?? 'none',
    )}`,
    `topology=${String(
      latestMetric?.topologyAuditStatus ??
        latestRecipe?.topologyAuditStatus ??
        'not_run',
    )} atlasHash=${String(
      latestMetric?.atlasConfigHash ?? latestRecipe?.atlasConfigHash ?? 'none',
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
    case 'recipe_applied':
      return `${formatRecipeAppliedSummary(parsed)} ${event.receivedAt}`;
  }
}

function formatE7MetricSummary(event: UnityEventPayload) {
  return `fps=${formatMetricNumber(
    event.averageFps,
  )} frame=${formatMetricNumber(event.averageFrameTimeMs)}ms mem=${String(
    event.memoryMetricAvailable ?? false,
  )} thermal=${String(event.thermalEvidenceType ?? 'n/a')} phase=${String(
    event.phase ?? 'baseline',
  )} mode=${String(event.rendererMode ?? 'e3e4-baseline')} look=${String(
    event.lookId ?? 'baseline_debug_mask',
  )} candidate=${String(event.candidateId ?? 'n/a')} variant=${String(
    event.variantId ?? 'n/a',
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
      event.runId ?? `e7-baseline-rn-${new Date().toISOString().slice(0, 10)}`,
    )}`,
    `phase=${String(event.phase ?? 'baseline')}`,
    `timestampMs=${receivedAtMs}`,
    `rendererMode=${String(event.rendererMode ?? 'e3e4-baseline')}`,
    `candidateId=${String(event.candidateId ?? 'e3e4-baseline')}`,
    `variantId=${String(event.variantId ?? 'baseline-v0')}`,
    `lookId=${String(event.lookId ?? 'baseline_debug_mask')}`,
    `recipeId=${String(event.recipeId ?? 'none')}`,
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

function getValidationCandidateOption(rendererMode: RendererMode) {
  return VALIDATION_CANDIDATE_OPTIONS.find(
    candidateOption => candidateOption.rendererMode === rendererMode,
  );
}

function formatSelectedCandidateId(rendererMode: RendererMode) {
  return getValidationCandidateOption(rendererMode)?.id ?? rendererMode;
}

function getCandidateIdForRenderer(rendererMode: RendererMode) {
  switch (rendererMode) {
    case 'e7-arface-authored-atlas':
      return 'arface-authored-atlas';
    case 'e7-arface-uv-candidate':
      return 'e7-procedural-arface-uv';
    default:
      return 'e3e4-baseline';
  }
}

function getVariantIdForRenderer(
  rendererMode: RendererMode,
  region: RecipeRegion,
  atlasVariantId: AtlasVariantId,
) {
  if (rendererMode === 'e7-arface-authored-atlas') {
    const atlasVariant = getAtlasVariantOption(atlasVariantId);
    return atlasVariant?.region === region
      ? atlasVariant.id
      : DEFAULT_ATLAS_VARIANT_BY_REGION[region];
  }

  return rendererMode === 'e7-arface-uv-candidate'
    ? 'procedural-v0'
    : 'baseline-v0';
}

function getAtlasVariantsForRegion(region: RecipeRegion) {
  return ATLAS_VARIANT_OPTIONS.filter(
    variantOption => variantOption.region === region,
  );
}

function getAtlasVariantOption(variantId: AtlasVariantId) {
  return ATLAS_VARIANT_OPTIONS.find(
    variantOption => variantOption.id === variantId,
  );
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
  fallbackEvent: UnityEventPayload | undefined,
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
    primaryEvent?.[directKeys[key]] ?? fallbackEvent?.[directKeys[key]];
  const directNumber = readNumber(directValue);
  if (directNumber !== undefined) {
    return directNumber.toFixed(0);
  }

  const primaryMesh = asRecord(primaryEvent?.mesh);
  const fallbackMesh = asRecord(fallbackEvent?.mesh);
  const nestedValue =
    primaryMesh?.[nestedKeys[key]] ?? fallbackMesh?.[nestedKeys[key]];
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
    event.rendererMode ?? event.textureMode ?? 'n/a',
  )} candidate=${String(event.candidateId ?? 'n/a')} variant=${String(
    event.variantId ?? 'n/a',
  )} color=${String(event.color)} opacity=${String(
    event.opacity,
  )} intensity=${String(event.intensity ?? 'n/a')} applied=${String(
    event.applied ?? false,
  )} faceCount=${String(event.faceCount ?? 'n/a')} meshTriangles=${String(
    event.meshTriangles ?? 'n/a',
  )} base=${String(event.baselineTriangles ?? 'n/a')} cand=${String(
    event.candidateTriangles ?? 'n/a',
  )} uv=${String(event.uvAvailable ?? false)} state=${String(
    event.stateAction ?? 'n/a',
  )} fallback=${String(
    event.usedFallback ?? false,
  )} topology=${String(
    event.topologyAuditStatus ?? 'not_run',
  )} atlasHash=${String(
    event.atlasConfigHash ?? 'none',
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

type OpacitySliderProps = {
  value: number;
  width: number;
  onLayoutWidth: (width: number) => void;
  onChange: (value: number) => void;
};

function OpacitySlider({
  value,
  width,
  onLayoutWidth,
  onChange,
}: OpacitySliderProps) {
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
        <Text style={styles.opacityLabel}>Opacity</Text>
        <Text style={styles.opacityValue}>{value.toFixed(2)}</Text>
      </View>
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
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
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
  viewModeRow: {
    flex: 1,
    minHeight: 40,
    flexDirection: 'row',
    justifyContent: 'flex-end',
    gap: 6,
  },
  viewModeButton: {
    minHeight: 40,
    minWidth: 64,
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
    alignSelf: 'flex-start',
    width: '58%',
    maxWidth: 320,
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.58)',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.22)',
    paddingHorizontal: 10,
    paddingVertical: 8,
    gap: 2,
  },
  compactHudFull: {
    backgroundColor: 'rgba(0, 0, 0, 0.48)',
  },
  compactHudHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  compactHudLabel: {
    color: '#D1FAE5',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
  },
  compactHudBadge: {
    color: '#111827',
    backgroundColor: '#FDE68A',
    borderRadius: 8,
    overflow: 'hidden',
    paddingHorizontal: 6,
    paddingVertical: 2,
    fontSize: 9,
    fontWeight: '900',
    letterSpacing: 0,
  },
  compactHudText: {
    color: '#F9FAFB',
    fontSize: 10,
    lineHeight: 14,
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
  candidateCatalog: {
    gap: 4,
  },
  candidateCatalogRow: {
    minHeight: 22,
    borderRadius: 8,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.18)',
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
    paddingHorizontal: 8,
  },
  candidateCatalogRowSelected: {
    backgroundColor: 'rgba(209, 250, 229, 0.22)',
    borderColor: '#D1FAE5',
  },
  candidateCatalogRowPending: {
    opacity: 0.72,
  },
  candidateCatalogText: {
    flex: 1,
    color: '#F9FAFB',
    fontSize: 10,
    fontWeight: '800',
    letterSpacing: 0,
  },
  candidateCatalogTextSelected: {
    color: '#D1FAE5',
  },
  candidateCatalogStatusText: {
    flex: 1,
    color: '#BAE6FD',
    fontSize: 9,
    lineHeight: 12,
    letterSpacing: 0,
    textAlign: 'right',
  },
  variantPanel: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.14)',
    paddingTop: 6,
    gap: 6,
  },
  variantButtonRow: {
    flexDirection: 'row',
    gap: 6,
  },
  variantButton: {
    flex: 1,
    minHeight: 44,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1,
    borderColor: 'rgba(255, 255, 255, 0.24)',
    backgroundColor: 'rgba(255, 255, 255, 0.08)',
    paddingHorizontal: 4,
  },
  variantButtonSelected: {
    backgroundColor: '#ECFDF5',
    borderColor: '#D1FAE5',
    borderWidth: 2,
  },
  variantButtonText: {
    color: '#F9FAFB',
    fontSize: 10,
    fontWeight: '900',
    letterSpacing: 0,
    textAlign: 'center',
  },
  variantButtonTextSelected: {
    color: '#064E3B',
  },
  variantStatusText: {
    color: '#BAE6FD',
    fontSize: 8,
    lineHeight: 11,
    letterSpacing: 0,
    marginTop: 2,
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
