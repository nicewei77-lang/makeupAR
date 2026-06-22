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
const VALIDATION_VIEW_MODE_OPTIONS = [
  { name: 'clean', label: 'Clean' },
  { name: 'compact', label: 'HUD' },
  { name: 'full', label: 'Debug' },
] as const;
const E7_BOUNDARY_PLAN_VERSION = 'E7.03 v2.1';
const E7_EVIDENCE_MODE = 'phase2-arface-manual-heuristic-baseline';

type RecipeColor = (typeof RECIPE_COLOR_OPTIONS)[number];
type RecipeRegion = (typeof RECIPE_REGION_OPTIONS)[number];
type RecipeTextureSample = (typeof RECIPE_TEXTURE_SAMPLE_OPTIONS)[number];
type RendererMode = 'e7-reference-uv-alpha';
type AtlasVariantId =
  | 'lip-uvref-v0-balanced'
  | 'cheek-uvref-v0-balanced'
  | 'eye-uvref-v0-balanced';
type ValidationViewMode = (typeof VALIDATION_VIEW_MODE_OPTIONS)[number]['name'];
type RegionRecipe = {
  color: RecipeColor;
  opacity: number;
  textureSample: RecipeTextureSample;
};
type ActiveRegionMap = Record<RecipeRegion, boolean>;

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
  lip: 'lip-uvref-v0-balanced',
  cheek: 'cheek-uvref-v0-balanced',
  eye: 'eye-uvref-v0-balanced',
};
const DEFAULT_ACTIVE_REGIONS: ActiveRegionMap = {
  lip: true,
  cheek: true,
  eye: true,
};
const OPACITY_STEP = 0.05;
const UNITY_EVENT_HISTORY_LIMIT = 5;
const DEFAULT_RENDERER_MODE: RendererMode = 'e7-reference-uv-alpha';
const UNITY_EVENT_TYPES = [
  'unity_initialized',
  'face_detected',
  'face_lifecycle',
  'face_feature_snapshot',
  'e7_metric_sample',
  'e7_reference_capture',
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
  maskTextureId?: string;
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
  boundaryRenderer?: string;
  capturePairId?: string;
  relativeDirectory?: string;
  detail?: string;
  frameWidth?: number;
  coordinateSpaceValidated?: boolean;
  coordinateSpaceValidationStatus?: string;
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
    ) => {
      const lookId = 'smooth_region_mask';
      const recipePrefix = 'smooth-mask';
      const recipeBatchId = `${recipePrefix}-batch-${Math.round(sentAtMs)}`;
      const activeRegionSummary = formatActiveRegionSummary(enabledRegions);
      const enabledLayerCount = countActiveRegions(enabledRegions);
      const layers = RECIPE_REGION_OPTIONS.map(region => {
        const recipe = recipes[region];
        const variantId = DEFAULT_ATLAS_VARIANT_BY_REGION[region];
        const layerRecipeId = `${recipePrefix}-${region}-${
          recipe.textureSample.name
        }-${variantId}-${Math.round(sentAtMs)}`;

        return {
          id: `${region}-${recipe.textureSample.name}`,
          recipeId: layerRecipeId,
          recipeBatchId,
          lookId,
          sentAtMs,
          rendererMode,
          variantId,
          activeRegions: activeRegionSummary,
          layerCount: RECIPE_REGION_OPTIONS.length,
          enabledLayerCount,
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
          enabled: enabledRegions[region],
          coverage: 0,
          finish: 'validation-placeholder',
          textureAmount: recipe.textureSample.intensity,
          roughness: 0,
          specular: 0,
          specularPower: 0,
          glossBoost: 0,
          shimmer: 0,
          shimmerColor: '#FFFFFF',
          skinAdaptive: false,
          preserveDetail: true,
          materialId: `${recipe.textureSample.name}-validation-material`,
          shaderMode: 'unlit-alpha-validation',
          passCount: 1,
          maskTextureId: variantId,
          cameraBackdropAvailable: false,
          lightEstimateAvailable: false,
        };
      });

      return JSON.stringify({
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
        texture: recipes[focusRegion].textureSample.name,
        sample: recipes[focusRegion].textureSample.name,
        textureMode: recipes[focusRegion].textureSample.textureMode,
        coverage: 0,
        finish: 'validation-placeholder',
        textureAmount: recipes[focusRegion].textureSample.intensity,
        roughness: 0,
        specular: 0,
        specularPower: 0,
        glossBoost: 0,
        shimmer: 0,
        shimmerColor: '#FFFFFF',
        skinAdaptive: false,
        preserveDetail: true,
        materialId: `${recipes[focusRegion].textureSample.name}-validation-material`,
        shaderMode: 'unlit-alpha-validation',
        passCount: 1,
        maskTextureId: DEFAULT_ATLAS_VARIANT_BY_REGION[focusRegion],
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
      console.log(
        '[E7] rn_texture_recipe_batch_post',
        `rendererMode=${rendererMode}`,
        'lookId=smooth_region_mask',
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
      regionRecipes,
      selectedRendererMode,
    ],
  );

  const postRecipeAck = useCallback(
    (payload: UnityEventPayload, receivedAtMs: number) => {
      const ackJson = JSON.stringify({
        type: 'recipe_ack',
        runId: payload.runId ?? 'e7-baseline',
        phase: payload.phase ?? 'baseline',
        rendererMode: payload.rendererMode ?? DEFAULT_RENDERER_MODE,
        candidateId: payload.candidateId,
        variantId: payload.variantId,
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
      const faceDebugSurfaceVisible = false;
      const payloadJson = JSON.stringify({
        visible,
        faceDebugSurfaceVisible,
        validationViewMode,
        reason,
        entryCount,
      });

      console.log(
        '[E7] rn_region_overlay_visibility_post',
        `visible=${visible}`,
        `faceDebugSurfaceVisible=${faceDebugSurfaceVisible}`,
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
        }

        if (parsed.type === 'e7_reference_capture') {
          setPendingCapturePairId(null);
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
    [postRecipeAck, validationViewMode],
  );

  useEffect(() => {
    const initialPostTimer = setTimeout(() => {
      postRecipeBatch();
    }, 1000);

    return () => clearTimeout(initialPostTimer);
  }, [postRecipeBatch]);

  const selectedRecipe = regionRecipes[focusedRegion];
  const selectedColor = selectedRecipe.color;
  const selectedTextureSample = selectedRecipe.textureSample;
  const activeRegionSummary = formatActiveRegionSummary(activeRegions);
  const opacity = selectedRecipe.opacity;
  const latestMetric = unityEventStatus.e7_metric_sample?.parsed;
  const latestCapture = unityEventStatus.e7_reference_capture?.parsed;
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
        latestMetric,
        latestCapture,
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
      latestCapture,
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
        ...selectedRecipe,
        color,
      };

      setRegionRecipes(currentRecipes => ({
        ...currentRecipes,
        [focusedRegion]: nextRecipe,
      }));
      postRecipeBatch(
        {
          ...regionRecipes,
          [focusedRegion]: nextRecipe,
        },
        activeRegions,
      );
    },
    [activeRegions, focusedRegion, postRecipeBatch, regionRecipes, selectedRecipe],
  );

  const updateOpacity = useCallback(
    (nextOpacity: number) => {
      const nextRecipe = {
        ...selectedRecipe,
        opacity: nextOpacity,
      };

      setRegionRecipes(currentRecipes => ({
        ...currentRecipes,
        [focusedRegion]: nextRecipe,
      }));
      postRecipeBatch(
        {
          ...regionRecipes,
          [focusedRegion]: nextRecipe,
        },
        activeRegions,
      );
    },
    [activeRegions, focusedRegion, postRecipeBatch, regionRecipes, selectedRecipe],
  );

  const selectTextureSample = useCallback(
    (textureSample: RecipeTextureSample) => {
      const nextRegion = textureSample.region;
      const nextRecipe = {
        ...regionRecipes[nextRegion],
        textureSample,
      };
      const nextRecipes = {
        ...regionRecipes,
        [nextRegion]: nextRecipe,
      };
      const nextActiveRegions = {
        ...activeRegions,
        [nextRegion]: true,
      };

      setFocusedRegion(nextRegion);
      setRegionRecipes(nextRecipes);
      setActiveRegions(nextActiveRegions);
      postRecipeBatch(nextRecipes, nextActiveRegions, nextRegion);
    },
    [activeRegions, postRecipeBatch, regionRecipes],
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

        <CompactEvidenceHud
          validationViewMode={validationViewMode}
          activeRegionSummary={activeRegionSummary}
          focusedRegion={focusedRegion}
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
            ]}
          >
            <View style={styles.recipePanelHeader}>
              <Text style={styles.recipePanelLabel}>Regions</Text>
              <Text style={styles.recipePanelMetaText} numberOfLines={1}>
                {`active=${activeRegionSummary} / focus=${focusedRegion}`}
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
                      textureOption.region === focusedRegion;

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
                  active {activeRegionSummary} / focus {focusedRegion} /{' '}
                  {selectedColor.name} {selectedColor.color} / opacity{' '}
                  {opacityPercent}% / texture {selectedTextureSample.name} /
                  mode {selectedTextureSample.textureMode} / intensity{' '}
                  {selectedTextureSample.intensity.toFixed(2)}
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
          ? `mask=${String(metric.maskSource ?? 'smooth_uv_mask')} uv=${String(
              metric.regionUvAvailable ?? metric.uvAvailable ?? false,
            )} triangles=${String(
              metric.regionCandidateTriangles ?? metric.candidateTriangles ?? 'n/a',
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
  latestCapture?: UnityEventPayload;
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
  latestCapture,
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
    `rendererMode=${selectedRendererMode} look=smooth_region_mask`,
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
    `capturePair=${String(
      latestCapture?.capturePairId ?? 'pair_face_0001',
    )} captureStatus=${String(
      latestCapture?.status ?? 'not_requested',
    )} captureDir=${String(latestCapture?.relativeDirectory ?? 'n/a')}`,
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
  )} dir=${String(event.relativeDirectory ?? 'n/a')} v=${String(
    event.meshVertexCount ?? 'n/a',
  )} i=${String(event.meshIndexCount ?? 'n/a')} uv=${String(
    event.meshUvCount ?? 'n/a',
  )} coordinate=${String(
    event.coordinateSpaceValidationStatus ?? 'pending_projected_mesh_overlay_review',
  )} detail=${String(event.detail ?? 'none')}`;
}

function buildReferenceCapturePairId(sequence: number, requestedAtMs: number) {
  const timestamp = new Date(requestedAtMs)
    .toISOString()
    .replace(/[-:]/g, '')
    .replace(/\.\d{3}Z$/, 'Z');

  return `pair_face_${timestamp}_${String(sequence).padStart(2, '0')}`;
}

function formatE7MetricSummary(event: UnityEventPayload) {
  return `fps=${formatMetricNumber(
    event.averageFps,
  )} frame=${formatMetricNumber(event.averageFrameTimeMs)}ms mem=${String(
    event.memoryMetricAvailable ?? false,
  )} thermal=${String(event.thermalEvidenceType ?? 'n/a')} phase=${String(
    event.phase ?? 'smooth_mask',
  )} mode=${String(event.rendererMode ?? 'e7-reference-uv-alpha')} look=${String(
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
      event.runId ?? `e7-baseline-rn-${new Date().toISOString().slice(0, 10)}`,
    )}`,
    `phase=${String(event.phase ?? 'smooth_mask')}`,
    `timestampMs=${receivedAtMs}`,
    `rendererMode=${String(event.rendererMode ?? 'e7-reference-uv-alpha')}`,
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

function getCandidateIdForRenderer(rendererMode: RendererMode) {
  switch (rendererMode) {
    case 'e7-reference-uv-alpha':
      return 'arface-reference-uv-alpha';
    case 'e7-reference-uv-atlas':
      return 'arface-reference-uv-atlas';
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
    switch (region) {
      case 'cheek':
        return 'cheek-soft-v0-balanced';
      case 'eye':
        return 'eye-band-v0-balanced';
      default:
        return 'lip-ring-v0-balanced';
    }
  }

  if (
    rendererMode === 'e7-reference-uv-alpha' ||
    rendererMode === 'e7-reference-uv-atlas'
  ) {
    return atlasVariantId ?? DEFAULT_ATLAS_VARIANT_BY_REGION[region];
  }

  return rendererMode === 'e7-arface-uv-candidate'
    ? 'procedural-v0'
    : 'baseline-v0';
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
    event.textureMode ?? 'n/a',
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
  captureDock: {
    alignSelf: 'stretch',
    marginBottom: 16,
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
