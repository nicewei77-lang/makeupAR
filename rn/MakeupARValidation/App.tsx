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

function App() {
  const isDarkMode = useColorScheme() === 'dark';
  const [isUnityOpen, setIsUnityOpen] = useState(false);

  return (
    <SafeAreaProvider>
      <StatusBar
        barStyle={isDarkMode ? 'light-content' : 'dark-content'}
        hidden={isUnityOpen}
      />
      <AppContent
        isUnityOpen={isUnityOpen}
        onStartUnity={() => setIsUnityOpen(true)}
        onCloseUnity={() => setIsUnityOpen(false)}
      />
    </SafeAreaProvider>
  );
}

type AppContentProps = {
  isUnityOpen: boolean;
  onStartUnity: () => void;
  onCloseUnity: () => void;
};

function AppContent({
  isUnityOpen,
  onStartUnity,
  onCloseUnity,
}: AppContentProps) {
  if (isUnityOpen) {
    return <UnityScreen onClose={onCloseUnity} />;
  }

  return <HomeScreen onStart={onStartUnity} />;
}

type HomeScreenProps = {
  onStart: () => void;
};

function HomeScreen({ onStart }: HomeScreenProps) {
  const safeAreaInsets = useSafeAreaInsets();

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
        <Text style={styles.kicker}>Session 6 / M5</Text>
        <Text style={styles.title}>RN to Unity Recipe Validation</Text>
        <Text style={styles.statusLabel}>Validation status</Text>
        <Text style={styles.statusText}>
          Ready to send recipe color and opacity to the local UnityFramework
          artifact on this iPhone.
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
  onClose: () => void;
};

function UnityScreen({ onClose }: UnityScreenProps) {
  const safeAreaInsets = useSafeAreaInsets();
  const mountedAt = useMemo(() => new Date().toLocaleTimeString(), []);
  const unityRef = useRef<UnityView>(null);
  const [selectedColor, setSelectedColor] =
    useState<RecipeColor>(DEFAULT_RECIPE_COLOR);
  const [opacity, setOpacity] = useState(DEFAULT_RECIPE_OPACITY);
  const [sliderWidth, setSliderWidth] = useState(1);

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

  useEffect(() => {
    const initialPostTimer = setTimeout(() => {
      postRecipe(selectedColor, opacity);
    }, 1000);

    return () => clearTimeout(initialPostTimer);
  }, [opacity, postRecipe, selectedColor]);

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
      <UnityView ref={unityRef} style={styles.unityView} />

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
          onPress={onClose}>
          <Text style={styles.closeButtonText}>Close</Text>
        </Pressable>

        <View style={styles.debugPanel}>
          <Text style={styles.debugText}>
            UnityView mounted for M5 validation at {mountedAt}.
          </Text>
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
    alignSelf: 'stretch',
    borderRadius: 8,
    backgroundColor: 'rgba(0, 0, 0, 0.68)',
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  debugText: {
    color: '#F9FAFB',
    fontSize: 13,
    lineHeight: 18,
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
