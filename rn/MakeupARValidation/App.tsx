import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  GestureResponderEvent,
  LayoutChangeEvent,
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

const RECIPE_COLOR_OPTIONS = [
  {name: 'rose', color: '#D94B74'},
  {name: 'coral', color: '#E67B5F'},
  {name: 'nude', color: '#B9826B'},
] as const;

type RecipeColor = (typeof RECIPE_COLOR_OPTIONS)[number];

const DEFAULT_RECIPE_COLOR = RECIPE_COLOR_OPTIONS[0];
const DEFAULT_RECIPE_OPACITY = 0.65;
const OPACITY_STEP = 0.05;
const UNITY_EVENT_HISTORY_LIMIT = 3;
const UNITY_EVENT_TYPES = [
  'unity_initialized',
  'face_detected',
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
  layer?: string;
  color?: string;
  opacity?: number;
  [key: string]: unknown;
};

type UnityEventRecord = {
  id: number;
  receivedAt: string;
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

      console.log('[M7] unity_screen_open', `entry=${nextCount}`);

      return nextCount;
    });
    setIsUnityOpen(true);
  }, []);

  const handleCloseUnity = useCallback(() => {
    setUnityExitCount(currentCount => {
      const nextCount = currentCount + 1;

      console.log('[M7] unity_screen_close', `exit=${nextCount}`);

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
      ]}>
      <View style={styles.homeBody}>
        <Text style={styles.kicker}>M7</Text>
        <Text style={styles.title}>Unity Re-entry Stability Validation</Text>
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
        onPress={onStart}>
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
  const [selectedColor, setSelectedColor] =
    useState<RecipeColor>(DEFAULT_RECIPE_COLOR);
  const [opacity, setOpacity] = useState(DEFAULT_RECIPE_OPACITY);
  const [sliderWidth, setSliderWidth] = useState(1);
  const [lastUnityEvent, setLastUnityEvent] =
    useState<UnityEventRecord | null>(null);
  const [unityEventHistory, setUnityEventHistory] = useState<
    UnityEventRecord[]
  >([]);
  const [unityEventStatus, setUnityEventStatus] =
    useState<UnityEventStatusMap>({});

  useEffect(() => {
    console.log(
      '[M7] unity_screen_mounted',
      `entry=${entryCount}`,
      `mounted=${mountedAt}`,
    );

    return () => {
      console.log('[M7] unity_screen_unmounted', `entry=${entryCount}`);
    };
  }, [entryCount, mountedAt]);

  const handleClose = useCallback(() => {
    console.log('[M7] unity_screen_close_pressed', `entry=${entryCount}`);
    onClose();
  }, [entryCount, onClose]);

  const buildRecipeJson = useCallback(
    (color: RecipeColor, nextOpacity: number) =>
      JSON.stringify({
        layer: 'lip',
        color: color.color,
        opacity: nextOpacity,
      }),
    [],
  );

  const postRecipe = useCallback(
    (color: RecipeColor, nextOpacity: number) => {
      unityRef.current?.postMessage(
        'RNBridge',
        'ApplyRecipeJson',
        buildRecipeJson(color, nextOpacity),
      );
    },
    [buildRecipeJson],
  );

  const handleUnityMessage = useCallback((event: UnityMessageEvent) => {
    const rawMessage = String(event.nativeEvent.message ?? '');
    const receivedAt = new Date().toLocaleTimeString();
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
      record = {
        id: Date.now(),
        receivedAt,
        rawMessage,
        parsed,
        displayText: formatUnityEvent(parsed),
      };

      console.log('[M6] rn_unity_message_received', rawMessage);

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
  }, []);

  useEffect(() => {
    const initialPostTimer = setTimeout(() => {
      postRecipe(DEFAULT_RECIPE_COLOR, DEFAULT_RECIPE_OPACITY);
    }, 1000);

    return () => clearTimeout(initialPostTimer);
  }, [postRecipe]);

  const selectColor = useCallback(
    (color: RecipeColor) => {
      setSelectedColor(color);
      postRecipe(color, opacity);
    },
    [opacity, postRecipe],
  );

  const updateOpacity = useCallback(
    (nextOpacity: number) => {
      setOpacity(nextOpacity);
      postRecipe(selectedColor, nextOpacity);
    },
    [postRecipe, selectedColor],
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
        ]}>
        <Pressable
          accessibilityRole="button"
          style={({ pressed }) => [
            styles.closeButton,
            pressed && styles.closeButtonPressed,
          ]}
          onPress={handleClose}>
          <Text style={styles.closeButtonText}>Close</Text>
        </Pressable>

        <View style={styles.debugPanel}>
          <Text style={styles.debugMetaText}>
            {`M7 entry #${entryCount} mounted=${mountedAt} previous_exits=${exitCount}`}
          </Text>
          <Text style={styles.debugLabel}>Latest Unity event</Text>
          <Text style={styles.debugText} numberOfLines={2}>
            {lastUnityEvent
              ? `${lastUnityEvent.receivedAt} ${lastUnityEvent.displayText}`
              : `waiting_for_unity_event mounted=${mountedAt}`}
          </Text>
          <View style={styles.debugStatus}>
            <Text style={styles.debugSubLabel}>Last by type</Text>
            {UNITY_EVENT_TYPES.map(type => {
              const statusEvent = unityEventStatus[type];

              return (
                <Text key={type} style={styles.debugHistoryText} numberOfLines={1}>
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
                  numberOfLines={1}>
                  {historyEvent.receivedAt} {historyEvent.displayText}
                </Text>
              ))
            )}
          </View>
        </View>

        <View style={styles.recipePanel}>
          <View style={styles.colorButtonRow}>
            {RECIPE_COLOR_OPTIONS.map(colorOption => {
              const isSelected = colorOption.name === selectedColor.name;

              return (
                <Pressable
                  accessibilityRole="button"
                  accessibilityState={{selected: isSelected}}
                  key={colorOption.name}
                  style={({pressed}) => [
                    styles.colorButton,
                    {backgroundColor: colorOption.color},
                    isSelected && styles.colorButtonSelected,
                    pressed && styles.colorButtonPressed,
                  ]}
                  onPress={() => selectColor(colorOption)}>
                  <Text style={styles.colorButtonText}>
                    {colorOption.name}
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

          <Text style={styles.recipeValueText}>
            {selectedColor.name} {selectedColor.color} / opacity{' '}
            {opacityPercent}%
          </Text>
        </View>
      </View>
    </View>
  );
}

function formatUnityEvent(event: UnityEventPayload) {
  switch (event.type) {
    case 'unity_initialized':
      return 'unity_initialized';
    case 'face_detected':
      return `face_detected tracked=${String(
        event.tracked,
      )} faceCount=${String(event.faceCount)}${formatFaceTrackingDetails(
        event,
      )}`;
    case 'recipe_applied':
      return `recipe_applied layer=${String(event.layer)} color=${String(
        event.color,
      )} opacity=${String(event.opacity)}`;
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
    case 'recipe_applied':
      return `recipe_applied: layer=${String(parsed.layer)} color=${String(
        parsed.color,
      )} opacity=${String(parsed.opacity)} ${event.receivedAt}`;
  }
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
        accessibilityValue={{min: 0, max: 1, now: value}}
        style={styles.sliderTrack}
        onLayout={handleLayout}
        {...panResponder.panHandlers}>
        <View style={[styles.sliderFill, {width: fillWidth}]} />
        <View style={[styles.sliderThumb, {left: fillWidth}]} />
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
  debugPanel: {
    alignSelf: 'center',
    width: '76%',
    maxHeight: 250,
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
});

export default App;
