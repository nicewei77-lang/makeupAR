/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import App, {
  BROW_COLOR_OPTIONS,
  BROW_TEXTURE_STYLE_OPTIONS,
  buildValidationRecipeBatchPayload,
  DEFAULT_ACTIVE_REGIONS,
  DEFAULT_DEBUG_DISPLAY_OPTIONS,
  DEFAULT_REGION_RECIPES,
  DEFAULT_RENDERER_MODE,
  DEFAULT_REGION_TUNING,
  LIP_AREA_STYLE_OPTIONS,
  LIP_FINISH_TYPE_OPTIONS,
  RECIPE_COLOR_OPTIONS,
  RECIPE_TEXTURE_SAMPLE_OPTIONS,
  composeLipTextureSample,
  getSelectedMaskTextureOptionId,
} from '../App';

declare const __dirname: string;
declare function require(moduleName: 'fs'): {
  readFileSync: (filePath: string, encoding: string) => string;
};
declare function require(moduleName: 'path'): {
  resolve: (...paths: string[]) => string;
};
declare function require(moduleName: string): any;

const fs = require('fs');
const path = require('path');
const mockMakeupARLocalMedia = {
  capturePhoto: jest.fn(() =>
    Promise.resolve({ status: 'saved', mediaType: 'photo' }),
  ),
  startVideoRecording: jest.fn(() =>
    Promise.resolve({ status: 'recording', mediaType: 'video' }),
  ),
  stopVideoRecording: jest.fn(() =>
    Promise.resolve({ status: 'saved', mediaType: 'video' }),
  ),
};

jest.mock('react-native', () => {
  const ReactRuntime = require('react');

  const createComponent = (name: string) =>
    ReactRuntime.forwardRef(
      (
        { children, style, onAccessibilityAction, ...props }: any,
        ref: any,
      ) =>
        ReactRuntime.createElement(
          name,
          {
            ...props,
            accessibilityActionHandler: onAccessibilityAction,
            ref,
            style,
          },
          children,
        ),
    );

  const View = createComponent('View');
  const ScrollView = createComponent('ScrollView');
  const Text = createComponent('Text');

  const Pressable = ReactRuntime.forwardRef(
    ({ children, style, ...props }: any, ref: any) =>
      ReactRuntime.createElement(
        'Pressable',
        {
          ...props,
          ref,
          style:
            typeof style === 'function' ? style({ pressed: false }) : style,
        },
        children,
      ),
  );

  return {
    GestureResponderEvent: {},
    LayoutChangeEvent: {},
    LogBox: { ignoreAllLogs: jest.fn() },
    NativeModules: { MakeupARLocalMedia: mockMakeupARLocalMedia },
    PanResponder: {
      create: jest.fn(() => ({ panHandlers: {} })),
    },
    Platform: { OS: 'ios', select: (values: any) => values.ios },
    Pressable,
    ScrollView,
    StatusBar: jest.fn(() => null),
    StyleSheet: {
      create: (styles: object) => styles,
      hairlineWidth: 1,
    },
    Text,
    useColorScheme: jest.fn(() => 'light'),
    useWindowDimensions: jest.fn(() => ({ width: 390, height: 844 })),
    View,
  };
});

jest.mock('react-native-safe-area-context', () => {
  const ReactRuntime = require('react');

  return {
    SafeAreaProvider: ({ children }: { children: React.ReactNode }) =>
      ReactRuntime.createElement(ReactRuntime.Fragment, null, children),
    useSafeAreaInsets: jest.fn(() => ({
      top: 0,
      right: 0,
      bottom: 0,
      left: 0,
    })),
  };
});

jest.mock('@azesmway/react-native-unity', () => {
  const ReactRuntime = require('react');
  const { View } = require('react-native');

  return ReactRuntime.forwardRef((props: any, ref: any) => {
    ReactRuntime.useImperativeHandle(ref, () => ({
      postMessage: jest.fn(),
    }));

    return <View testID="unity-view" {...props} />;
  });
});

let consoleLogSpy: jest.SpyInstance;
let consoleErrorSpy: jest.SpyInstance;

beforeEach(() => {
  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  require('react-native').NativeModules.MakeupARLocalMedia =
    mockMakeupARLocalMedia;
  consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
  consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
  mockMakeupARLocalMedia.capturePhoto.mockClear();
  mockMakeupARLocalMedia.startVideoRecording.mockClear();
  mockMakeupARLocalMedia.stopVideoRecording.mockClear();
  jest.useFakeTimers();
});

afterEach(() => {
  jest.clearAllTimers();
  jest.useRealTimers();
  consoleLogSpy.mockRestore();
  consoleErrorSpy.mockRestore();
});

function collectJsonText(
  node:
    | ReactTestRenderer.ReactTestRendererJSON
    | ReactTestRenderer.ReactTestRendererJSON[]
    | null,
): string {
  if (node === null) {
    return '';
  }

  if (Array.isArray(node)) {
    return node.map(collectJsonText).join('\n');
  }

  return (node.children ?? [])
    .map(child => (typeof child === 'string' ? child : collectJsonText(child)))
    .join('\n');
}

function collectInstanceText(
  node: ReactTestRenderer.ReactTestInstance,
): string {
  return node.children
    .map(child =>
      typeof child === 'string'
        ? child
        : collectInstanceText(child as ReactTestRenderer.ReactTestInstance),
    )
    .join('\n');
}

function collectText(renderer: ReactTestRenderer.ReactTestRenderer) {
  return collectJsonText(renderer.toJSON());
}

function enterUnityScreen(renderer: ReactTestRenderer.ReactTestRenderer) {
  const existingUnityViews = renderer.root.findAll(
    node => node.props.testID === 'unity-view',
  );
  if (existingUnityViews.length > 0) {
    return;
  }

  const startButton = renderer.root
    .findAll(node => typeof node.props.onPress === 'function')
    .find(node => collectInstanceText(node).includes('Start AR'));

  expect(startButton).toBeTruthy();

  ReactTestRenderer.act(() => {
    startButton?.props.onPress();
  });
}

function pressByText(
  renderer: ReactTestRenderer.ReactTestRenderer,
  text: string,
) {
  const button = renderer.root
    .findAll(node => typeof node.props.onPress === 'function')
    .find(node => collectInstanceText(node).includes(text));

  expect(button).toBeTruthy();

  ReactTestRenderer.act(() => {
    button?.props.onPress();
  });
}

function pressByTestID(
  renderer: ReactTestRenderer.ReactTestRenderer,
  testID: string,
) {
  const button = renderer.root.findByProps({ testID });

  expect(button).toBeTruthy();

  ReactTestRenderer.act(() => {
    button.props.onPress();
  });
}

async function pressByTestIDAsync(
  renderer: ReactTestRenderer.ReactTestRenderer,
  testID: string,
) {
  const button = renderer.root.findByProps({ testID });

  expect(button).toBeTruthy();

  await ReactTestRenderer.act(async () => {
    await button.props.onPress();
  });
}

function incrementSliderByTestID(
  renderer: ReactTestRenderer.ReactTestRenderer,
  testID: string,
  count = 1,
) {
  const slider = renderer.root.findByProps({ testID });

  expect(slider).toBeTruthy();

  ReactTestRenderer.act(() => {
    let sliderValue = slider.props.value;

    Array.from({ length: count }).forEach(() => {
      sliderValue = Number(
        Math.min(
          1,
          (Math.round(sliderValue / 0.05) + 1) * 0.05,
        ).toFixed(2),
      );

      slider.props.onChange(sliderValue);
    });
  });
}

function sendUnityMessage(
  renderer: ReactTestRenderer.ReactTestRenderer,
  payload: object,
) {
  const unityView = renderer.root.findByProps({ testID: 'unity-view' });

  ReactTestRenderer.act(() => {
    unityView.props.onUnityMessage({
      nativeEvent: {
        message: JSON.stringify(payload),
      },
    });
  });
}

test('opens AR by default and keeps home available after close', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });

  const text = collectText(renderer!);

  expect(text).toContain('Close');
  expect(text).toContain('HUD');
  expect(text).toContain('AR Status');
  expect(text).not.toContain('Region ' + 'Precision');
  expect(text).not.toContain('Validation status');
  expect(text).not.toContain('E7.3');

  pressByText(renderer!, 'Close');

  const homeText = collectText(renderer!);
  expect(homeText).toContain('Makeup AR Validation');
  expect(homeText).toContain('Ready to start AR');
});

test('does not render old selector controls', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const text = collectText(renderer!);

  expect(text).not.toContain('Cand' + 'idate');
  expect(text).not.toContain('cand' + 'idate');
  expect(text).not.toContain('Vari' + 'ant');
  expect(text).not.toContain('vari' + 'ant');
  expect(text).not.toContain('soft-' + 'wide');
  expect(text).not.toContain('co' + 're');

  pressByText(renderer!, 'Debug');
  const debugText = collectText(renderer!);
  expect(debugText).not.toContain('cand' + 'idateId');
  expect(debugText).not.toContain('vari' + 'antId');
});

test('keeps validation modes visually compact before build', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const hudText = collectText(renderer!);
  expect(hudText).toContain('Clean');
  expect(hudText).toContain('HUD');
  expect(hudText).toContain('Debug');
  expect(hudText).toContain('Regions');
  expect(hudText).toContain('AR Status');
  expect(hudText.indexOf('Regions')).toBeLessThan(hudText.indexOf('AR Status'));
  expect(hudText).toContain('active=lip');
  expect(hudText).not.toContain('E7.03 HUD');

  pressByText(renderer!, 'Clean');
  expect(collectText(renderer!)).not.toContain('Regions');
  expect(collectText(renderer!)).not.toContain('E7.03 HUD');

  pressByText(renderer!, 'Debug');
  expect(collectText(renderer!)).toContain('Evidence metadata');
  expect(collectText(renderer!)).toContain('Regions');
});

test('saves user-triggered photo and video locally without reference capture', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);
  pressByText(renderer!, 'Clean');

  expect(collectText(renderer!)).toContain('Save Photo');
  expect(collectText(renderer!)).toContain('Record Video');

  await pressByTestIDAsync(renderer!, 'local-photo-save-button');

  expect(mockMakeupARLocalMedia.capturePhoto).toHaveBeenCalledTimes(1);
  expect(collectText(renderer!)).toContain('photo saved locally');

  await pressByTestIDAsync(renderer!, 'local-video-record-button');

  expect(mockMakeupARLocalMedia.startVideoRecording).toHaveBeenCalledTimes(1);
  expect(collectText(renderer!)).toContain('recording video');
  expect(collectText(renderer!)).toContain('Stop Video');

  await pressByTestIDAsync(renderer!, 'local-video-record-button');

  expect(mockMakeupARLocalMedia.stopVideoRecording).toHaveBeenCalledTimes(1);
  expect(collectText(renderer!)).toContain('video saved locally');
  expect(mockMakeupARLocalMedia.capturePhoto.mock.calls[0]).toEqual([]);
  expect(consoleLogSpy.mock.calls.join('\n')).not.toContain('frame.png');
});

test('shows lip color, finish type, area style, and intensity controls in HUD mode', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const hudText = collectText(renderer!);

  expect(hudText).toContain('rose');
  expect(hudText).toContain('coral');
  expect(hudText).toContain('Normal');
  expect(hudText).toContain('Matte');
  expect(hudText).toContain('Glossy');
  expect(hudText).toContain('Full');
  expect(hudText).toContain('Gradient');
  expect(hudText).toContain('Overlip');
  expect(hudText).toContain('Intensity');
  expect(hudText).not.toContain('matte_lip');

  pressByText(renderer!, 'Glossy');

  expect(collectText(renderer!)).toContain('type Glossy');
  expect(collectText(renderer!)).not.toContain('gloss_lip');

  pressByText(renderer!, 'Gradient');

  expect(collectText(renderer!)).toContain('area Gradient');
  expect(collectText(renderer!)).not.toContain('gradient_lip');
});

test('marks lip finish and area options as one-selected radio groups', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const finishButtons = LIP_FINISH_TYPE_OPTIONS.map(option =>
    renderer!.root.findByProps({ testID: `lip-finish-${option.id}` }),
  );
  const areaButtons = LIP_AREA_STYLE_OPTIONS.map(option =>
    renderer!.root.findByProps({ testID: `lip-area-${option.id}` }),
  );

  expect(
    finishButtons.every(button => button.props.accessibilityRole === 'radio'),
  ).toBe(true);
  expect(
    areaButtons.every(button => button.props.accessibilityRole === 'radio'),
  ).toBe(true);
  expect(
    finishButtons.filter(button => button.props.accessibilityState?.selected)
      .length,
  ).toBe(1);
  expect(
    areaButtons.filter(button => button.props.accessibilityState?.selected)
      .length,
  ).toBe(1);

  pressByText(renderer!, 'Glossy');
  pressByText(renderer!, 'Gradient');

  const selectedFinishButtons = LIP_FINISH_TYPE_OPTIONS.map(option =>
    renderer!.root.findByProps({ testID: `lip-finish-${option.id}` }),
  ).filter(button => button.props.accessibilityState?.selected);
  const selectedAreaButtons = LIP_AREA_STYLE_OPTIONS.map(option =>
    renderer!.root.findByProps({ testID: `lip-area-${option.id}` }),
  ).filter(button => button.props.accessibilityState?.selected);

  expect(selectedFinishButtons).toHaveLength(1);
  expect(selectedFinishButtons[0].props.testID).toBe('lip-finish-glossy');
  expect(selectedAreaButtons).toHaveLength(1);
  expect(selectedAreaButtons[0].props.testID).toBe('lip-area-gradient');
});

test('maps gradient density atlas to the Atlas diagnostic UI option', () => {
  expect(
    getSelectedMaskTextureOptionId(
      'lip',
      'lip-drawn-gradient-density-atlas-v1',
    ),
  ).toBe('lip-drawn-style-atlas-v1');
});

test('renders collapsible per-region tuning controls in HUD mode', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  let text = collectText(renderer!);

  expect(text).toContain('Tune');
  expect(text).toContain('Mask');
  expect(text).toContain('Guide');
  expect(text).toContain('Mesh');
  expect(text).toContain('Diagnostics');
  expect(text).toContain('Debug View');
  expect(text).toContain('RAW');
  expect(text).toContain('PROCESSED');
  expect(text).toContain('FINAL');
  expect(text.indexOf('RAW')).toBeLessThan(text.indexOf('PROCESSED'));
  expect(text.indexOf('PROCESSED')).toBeLessThan(text.indexOf('FINAL'));
  expect(text).toContain('Opacity');
  expect(text).toContain('Coverage');
  expect(text).toContain('Feather');
  expect(text).toContain('Specular');
  expect(text).toContain('focus lip');

  const maxHeightStyles = renderer!.root
    .findAll(node => Array.isArray(node.props.style))
    .flatMap(node => node.props.style)
    .filter(Boolean)
    .filter(style => typeof style.maxHeight === 'number');

  expect(maxHeightStyles.some(style => style.maxHeight <= 405)).toBe(true);

  pressByText(renderer!, 'Hide Tune');
  text = collectText(renderer!);

  expect(text).toContain('Show Tune');
  expect(text).not.toContain('Coverage');

  pressByText(renderer!, 'Show Tune');
  pressByText(renderer!, 'cheek');
  text = collectText(renderer!);

  expect(text).toContain('focus cheek');
  expect(text).toContain('Blush');
  expect(text).not.toContain('soft_blush');
  expect(text).toContain('Opacity');
  expect(text).toContain('Coverage');
});

test('posts green guide and yellow mesh overlay visibility toggles immediately', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);
  consoleLogSpy.mockClear();

  pressByText(renderer!, 'Mesh');

  const meshVisibilityCall = consoleLogSpy.mock.calls.find(
    call =>
      call.includes('[E7] rn_region_overlay_visibility_post') &&
      call.includes('meshOverlayVisible=true'),
  );

  expect(meshVisibilityCall).toBeTruthy();
  expect(meshVisibilityCall).toContain('guideOverlayVisible=true');
  expect(meshVisibilityCall).toContain('guideColor=green');
  expect(meshVisibilityCall).toContain('meshColor=yellow');
  expect(meshVisibilityCall).toContain('meshRenderMode=wireframe');
  expect(meshVisibilityCall).toContain('guideOverlayMode=mesh_landmarks');
  expect(meshVisibilityCall).toContain('faceDebugSurfaceSuppressed=true');

  pressByText(renderer!, 'RAW');

  const rawMaskDebugCall = consoleLogSpy.mock.calls.find(
    call =>
      call.includes('[E7] rn_region_overlay_visibility_post') &&
      call.includes('maskDebugViewMode=raw'),
  );

  expect(rawMaskDebugCall).toBeTruthy();
});

test('posts independent tuning parameters for each region', () => {
  const payload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      lip: {
        ...DEFAULT_REGION_RECIPES.lip,
        opacity: 0.81,
        intensity: 0.77,
      },
      cheek: {
        ...DEFAULT_REGION_RECIPES.cheek,
        opacity: 0.46,
        intensity: 0.38,
      },
      eye: {
        ...DEFAULT_REGION_RECIPES.eye,
        opacity: 0.42,
        intensity: 0.71,
      },
    },
    {
      lip: true,
      cheek: true,
      eye: true,
      brow: false,
    },
    'cheek',
    DEFAULT_RENDERER_MODE,
    12345,
    {
      ...DEFAULT_REGION_TUNING,
      lip: {
        ...DEFAULT_REGION_TUNING.lip,
        feather: 0.31,
        coverage: 0.88,
        roughness: 0.72,
        specular: 0.18,
        glossBoost: 0.22,
        gradientAmount: 0.12,
      },
      cheek: {
        ...DEFAULT_REGION_TUNING.cheek,
        feather: 0.62,
        coverage: 0.58,
        roughness: 0.91,
        specular: 0.04,
        preserveDetail: false,
      },
      eye: {
        ...DEFAULT_REGION_TUNING.eye,
        feather: 0.41,
        coverage: 0.73,
        roughness: 0.36,
        specular: 0.43,
        glossBoost: 0.16,
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const lipLayer = payload.layers.find(layer => layer.region === 'lip')!;
  const cheekLayer = payload.layers.find(layer => layer.region === 'cheek')!;
  const eyeLayer = payload.layers.find(layer => layer.region === 'eye')!;

  expect(payload.region).toBe('cheek');
  expect(payload.debugDisplay.maskOverlayVisible).toBe(true);
  expect(payload.debugDisplay.maskDebugViewMode).toBe('final');
  expect(lipLayer.opacity).toBe(0.81);
  expect(lipLayer.intensity).toBe(0.77);
  expect(lipLayer.feather).toBe(0.31);
  expect(lipLayer.coverage).toBe(0.88);
  expect(lipLayer.roughness).toBe(0.72);
  expect(lipLayer.specular).toBe(0.18);
  expect(lipLayer.glossBoost).toBe(0.22);
  expect(lipLayer.gradientAmount).toBe(0.12);
  expect(cheekLayer.opacity).toBe(0.46);
  expect(cheekLayer.intensity).toBe(0.38);
  expect(cheekLayer.feather).toBe(0.62);
  expect(cheekLayer.coverage).toBe(0.58);
  expect(cheekLayer.preserveDetail).toBe(false);
  expect(eyeLayer.opacity).toBe(0.42);
  expect(eyeLayer.intensity).toBe(0.71);
  expect(eyeLayer.feather).toBe(0.41);
  expect(eyeLayer.coverage).toBe(0.73);
  expect(eyeLayer.specular).toBe(0.43);
  expect(eyeLayer.glossBoost).toBe(0.16);
});

test('posts eyebrow as a fourth independent region layer', () => {
  const browSample = BROW_TEXTURE_STYLE_OPTIONS.find(
    textureSample => textureSample.name === 'natural_brow',
  );
  const softBrowSample = BROW_TEXTURE_STYLE_OPTIONS.find(
    textureSample => textureSample.name === 'soft_brow',
  );

  expect(browSample).toBeTruthy();
  expect(softBrowSample).toBeTruthy();
  expect(browSample!.intensity).toBe(0.76);
  expect(browSample!.feather).toBe(0.42);
  expect(browSample!.coverage).toBe(0.66);
  expect(browSample!.specular).toBe(0);
  expect(softBrowSample!.intensity).toBe(0.62);
  expect(softBrowSample!.coverage).toBe(0.54);
  expect(softBrowSample!.feather).toBe(0.48);
  expect(DEFAULT_REGION_RECIPES.brow.opacity).toBe(0.75);
  expect(DEFAULT_REGION_RECIPES.brow.color).toBe(BROW_COLOR_OPTIONS[1]);
  expect(DEFAULT_REGION_TUNING.lip.maskTextureId).toBe(
    'psd-arcore-lip-style-v1',
  );
  expect(DEFAULT_REGION_TUNING.cheek.maskTextureId).toBe(
    'psd-arcore-cheek-undereye-v1',
  );
  expect(DEFAULT_REGION_TUNING.brow.maskTextureId).toBe(
    'psd-arcore-brow-semi-arch-v1',
  );
  expect(DEFAULT_REGION_TUNING.brow.detailAmount).toBe(0.52);
  expect(DEFAULT_REGION_TUNING.brow.maskSpreadX).toBe(0);
  expect(DEFAULT_REGION_TUNING.brow.maskOffsetY).toBe(0);
  expect((DEFAULT_REGION_TUNING.brow as any).browGap).toBe(0);
  expect((DEFAULT_REGION_TUNING.brow as any).browAngle).toBe(0);
  expect((DEFAULT_REGION_TUNING.brow as any).browArch).toBe(0);
  expect((DEFAULT_REGION_TUNING.brow as any).browArchPosition).toBe(0);
  expect((DEFAULT_REGION_TUNING.brow as any).browCleanupStrength).toBe(0.24);
  expect((DEFAULT_REGION_TUNING.brow as any).browCleanupEnabled).toBe(true);
  expect((DEFAULT_REGION_TUNING.brow as any).browReshapeStrength).toBe(0.16);
  expect((DEFAULT_REGION_TUNING.brow as any).browCleanupSourceMode).toBe(
    'grabpass',
  );

  const payload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      brow: {
        color: BROW_COLOR_OPTIONS[1],
        opacity: DEFAULT_REGION_RECIPES.brow.opacity,
        intensity: browSample!.intensity,
        textureSample: browSample!,
      },
    },
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24680,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        feather: browSample!.feather,
        coverage: browSample!.coverage,
        maskSpreadX: DEFAULT_REGION_TUNING.brow.maskSpreadX,
        maskOffsetY: 0,
        browGap: (DEFAULT_REGION_TUNING.brow as any).browGap,
        browAngle: 0,
        browArch: 0,
        roughness: browSample!.roughness,
        specular: browSample!.specular,
        glossBoost: 0,
        gradientAmount: 0,
        maskTextureId: DEFAULT_REGION_TUNING.brow.maskTextureId,
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

  expect(payload.region).toBe('brow');
  expect(payload.layerCount).toBe(4);
  expect(payload.enabledLayerCount).toBe(2);
  expect(payload.activeRegions).toBe('lip,brow');
  expect(browLayer).toBeTruthy();
  expect(browLayer.enabled).toBe(true);
  expect(browLayer.texture).toBe('natural_brow');
  expect(browLayer.sample).toBe('natural_brow');
  expect(browLayer.maskTextureId).toBe('psd-arcore-brow-semi-arch-v1');
  expect(browLayer.color).toBe('#4A342B');
  expect(browLayer.opacity).toBe(0.75);
  expect(browLayer.intensity).toBe(0.76);
  expect(browLayer.detailAmount).toBe(0.52);
  expect(browLayer.feather).toBe(0.42);
  expect(browLayer.coverage).toBe(0.66);
  expect(browLayer.maskSpreadX).toBe(0);
  expect(browLayer.maskOffsetY).toBe(0);
  expect((browLayer as any).browGap).toBe(0);
  expect((browLayer as any).browAngle).toBe(0);
  expect((browLayer as any).browArch).toBe(0);
  expect((browLayer as any).browArchPosition).toBe(0);
  expect((browLayer as any).browCleanupEnabled).toBe(true);
  expect((browLayer as any).browCleanupStrength).toBe(0.24);
  expect((browLayer as any).browReshapeStrength).toBe(0.16);
  expect((payload as any).browCleanupEnabled).toBe(true);
  expect((payload as any).browCleanupSourceMode).toBe('grabpass');
  expect((browLayer as any).browCleanupSourceMode).toBe('grabpass');
  expect(browLayer.specular).toBe(0);
  expect(browLayer.materialId).toBe('natural_brow-validation-material');
  expect(browLayer.shaderMode).toBe('unlit-alpha-validation');
});

test('passes runtime texture override settings through focused region and layers', () => {
  const payload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    260629,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...(DEFAULT_REGION_TUNING.brow as any),
        runtimeTextureOverrideMode: 'documents_png',
        runtimeTextureOverridePath: 'runtime-overrides/brow-test.png',
      },
    } as any,
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const lipLayer = payload.layers.find(layer => layer.region === 'lip')!;
  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

  expect((payload as any).runtimeTextureOverrideMode).toBe('documents_png');
  expect((payload as any).runtimeTextureOverridePath).toBe(
    'runtime-overrides/brow-test.png',
  );
  expect((browLayer as any).runtimeTextureOverrideMode).toBe('documents_png');
  expect((browLayer as any).runtimeTextureOverridePath).toBe(
    'runtime-overrides/brow-test.png',
  );
  expect((lipLayer as any).runtimeTextureOverrideMode).toBe('off');
  expect((lipLayer as any).runtimeTextureOverridePath).toBe('');
});

test('can disable eyebrow skin restoration without losing cleanup slider value', () => {
  const payload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24688,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        browCleanupEnabled: false,
        browCleanupStrength: 0.41,
      } as any,
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;
  const lipLayer = payload.layers.find(layer => layer.region === 'lip')!;

  expect((payload as any).browCleanupEnabled).toBe(false);
  expect((payload as any).browCleanupStrength).toBe(0);
  expect((payload as any).browCleanupSourceMode).toBe('none');
  expect((browLayer as any).browCleanupEnabled).toBe(false);
  expect((browLayer as any).browCleanupStrength).toBe(0);
  expect((browLayer as any).browCleanupSourceMode).toBe('none');
  expect((lipLayer as any).browCleanupEnabled).toBe(false);
  expect((lipLayer as any).browCleanupStrength).toBe(0);
  expect((lipLayer as any).browCleanupSourceMode).toBe('none');
});

test('can switch eyebrow cleanup source to AR camera background in payload', () => {
  const payload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24689,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        browCleanupSourceMode: 'ar_camera_background',
      } as any,
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;
  const lipLayer = payload.layers.find(layer => layer.region === 'lip')!;

  expect((payload as any).browCleanupSourceMode).toBe(
    'ar_camera_background',
  );
  expect((browLayer as any).browCleanupSourceMode).toBe(
    'ar_camera_background',
  );
  expect((lipLayer as any).browCleanupSourceMode).toBe('none');
});

test('passes eyebrow placement deltas without hidden ARKit UV baseline offsets', () => {
  const payload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24682,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        maskSpreadX: 0.12,
        maskOffsetY: 0.024,
        browGap: 0.12,
        browAngle: -0.12,
        browArch: 0.027,
        browArchPosition: -0.08,
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

  expect(payload.maskSpreadX).toBe(0.12);
  expect(payload.maskOffsetY).toBeCloseTo(0.024);
  expect((payload as any).browGap).toBe(0.12);
  expect((payload as any).browAngle).toBe(-0.12);
  expect((payload as any).browArch).toBe(0.027);
  expect((payload as any).browArchPosition).toBe(-0.08);
  expect(browLayer.maskSpreadX).toBe(0.12);
  expect(browLayer.maskOffsetY).toBeCloseTo(0.024);
  expect((browLayer as any).browGap).toBe(0.12);
  expect((browLayer as any).browAngle).toBe(-0.12);
  expect((browLayer as any).browArch).toBe(0.027);
  expect((browLayer as any).browArchPosition).toBe(-0.08);
});

test('keeps MediaPipe canonical brow styles free of hidden ARKit UV placement offsets', () => {
  const softFlatPayload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24687,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        maskTextureId: 'brow-back-arch-soft-mix-v1',
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const pngHairPayload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24688,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        maskTextureId: 'brow-png-natural-hair-v1',
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );
  const psdPayload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24689,
    DEFAULT_REGION_TUNING,
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  expect(softFlatPayload.maskSpreadX).toBe(0);
  expect(softFlatPayload.maskOffsetY).toBe(0);
  expect(pngHairPayload.maskSpreadX).toBe(0);
  expect(pngHairPayload.maskOffsetY).toBe(0);
  expect(psdPayload.maskTextureId).toBe('psd-arcore-brow-semi-arch-v1');
  expect(psdPayload.maskSpreadX).toBe(0);
  expect(psdPayload.maskOffsetY).toBe(0);
});

test('keeps PSD semi-arch brow at the source-brow placement baseline', () => {
  const payload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24689,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        maskTextureId: 'psd-arcore-brow-semi-arch-v1',
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

  expect(payload.maskTextureId).toBe('psd-arcore-brow-semi-arch-v1');
  expect(payload.maskSpreadX).toBe(0);
  expect(payload.maskOffsetY).toBe(0);
  expect(browLayer.maskTextureId).toBe('psd-arcore-brow-semi-arch-v1');
  expect(browLayer.maskOffsetY).toBe(0);
});

test('applies eyebrow color warmth and depth parameters to payload color', () => {
  const payload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      brow: {
        ...DEFAULT_REGION_RECIPES.brow,
        color: BROW_COLOR_OPTIONS[1],
        colorWarmth: 0.75,
        colorDepth: 0.8,
      },
    },
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24681,
    DEFAULT_REGION_TUNING,
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

  expect(browLayer.color).toBe('#422C1E');
});

test('passes PNG eyebrow hair texture and light brow blend controls to payload', () => {
  const browSample = BROW_TEXTURE_STYLE_OPTIONS.find(
    textureSample => textureSample.name === 'natural_brow',
  )!;
  const lightBrown = BROW_COLOR_OPTIONS.find(
    colorOption => colorOption.name === 'light_brown',
  );

  expect(lightBrown).toBeTruthy();

  const payload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      brow: {
        ...DEFAULT_REGION_RECIPES.brow,
        color: lightBrown!,
        colorDepth: 0.24,
        textureSample: browSample,
      },
    },
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24683,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        detailAmount: 0.52,
        maskTextureId: 'brow-png-daily-hair-v1',
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

  expect(payload.maskTextureId).toBe('brow-png-daily-hair-v1');
  expect(payload.detailAmount).toBe(0.52);
  expect(payload.color).toBe('#A7836F');
  expect(browLayer.maskTextureId).toBe('brow-png-daily-hair-v1');
  expect(browLayer.detailAmount).toBe(0.52);
  expect(browLayer.blendMode).toBe('normal');
  expect(browLayer.shaderMode).toBe('unlit-alpha-validation');
});

test('compares flatter daily PNG normal, sharp, and multiply detail probes', () => {
  const browSample = BROW_TEXTURE_STYLE_OPTIONS.find(
    textureSample => textureSample.name === 'natural_brow',
  )!;
  const lightBrown = BROW_COLOR_OPTIONS.find(
    colorOption => colorOption.name === 'light_brown',
  )!;

  const sharpPayload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      brow: {
        ...DEFAULT_REGION_RECIPES.brow,
        color: lightBrown,
        textureSample: browSample,
      },
    },
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24685,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        detailAmount: 0.56,
        maskTextureId: 'brow-png-dailyflat-sharp-v1',
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );
  const multiplyPayload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      brow: {
        ...DEFAULT_REGION_RECIPES.brow,
        color: lightBrown,
        textureSample: browSample,
      },
    },
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24686,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        detailAmount: 0.56,
        maskTextureId: 'brow-png-dailyflat-multiply-v1',
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );
  const sharpLayer = sharpPayload.layers.find(layer => layer.region === 'brow')!;
  const multiplyLayer = multiplyPayload.layers.find(
    layer => layer.region === 'brow',
  )!;

  expect(sharpPayload.maskTextureId).toBe('brow-png-dailyflat-sharp-v1');
  expect(sharpPayload.detailAmount).toBe(0.56);
  expect(sharpLayer.blendMode).toBe('normal');
  expect(multiplyPayload.maskTextureId).toBe('brow-png-dailyflat-multiply-v1');
  expect(multiplyPayload.detailAmount).toBe(0.56);
  expect(multiplyLayer.blendMode).toBe('multiply');
});

test('keeps darker PNG eyebrow hair textures on multiply blend', () => {
  const browSample = BROW_TEXTURE_STYLE_OPTIONS.find(
    textureSample => textureSample.name === 'natural_brow',
  )!;

  const payload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      brow: {
        ...DEFAULT_REGION_RECIPES.brow,
        color: BROW_COLOR_OPTIONS[1],
        textureSample: browSample,
      },
    },
    {
      ...DEFAULT_ACTIVE_REGIONS,
      brow: true,
    },
    'brow',
    DEFAULT_RENDERER_MODE,
    24684,
    {
      ...DEFAULT_REGION_TUNING,
      brow: {
        ...DEFAULT_REGION_TUNING.brow,
        detailAmount: 0.52,
        maskTextureId: 'brow-png-daily-hair-v1',
      },
    },
    DEFAULT_DEBUG_DISPLAY_OPTIONS,
  );

  const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

  expect(browLayer.maskTextureId).toBe('brow-png-daily-hair-v1');
  expect(browLayer.detailAmount).toBe(0.52);
  expect(browLayer.blendMode).toBe('multiply');
});

test('combines lip finish type and area style independently in payload', () => {
  expect(LIP_FINISH_TYPE_OPTIONS.map(option => option.label)).toEqual([
    'Normal',
    'Matte',
    'Glossy',
  ]);
  expect(LIP_AREA_STYLE_OPTIONS.map(option => option.label)).toEqual([
    'Full',
    'Gradient',
    'Overlip',
  ]);

  const glossyGradientSample = composeLipTextureSample('glossy', 'gradient');
  const normalFullSample = composeLipTextureSample('normal', 'full');
  const matteOverlineSample = composeLipTextureSample('matte', 'overline');

  expect(normalFullSample.name).toBe('full_lip');
  expect(normalFullSample.finish).toBe('normal');
  expect(normalFullSample.specular).toBeGreaterThan(0);
  expect(normalFullSample.glossBoost).toBeLessThan(0.2);
  expect(glossyGradientSample.name).toBe('gradient_lip');
  expect(glossyGradientSample.finish).toBe('gloss');
  expect(glossyGradientSample.specular).toBeGreaterThan(0.7);
  expect(glossyGradientSample.glossBoost).toBeGreaterThan(0.6);
  expect(glossyGradientSample.glossBoost).toBeLessThan(0.75);
  expect(glossyGradientSample.gradientAmount).toBe(1);
  expect(matteOverlineSample.name).toBe('overline_lip');
  expect(matteOverlineSample.finish).toBe('matte');
  expect(matteOverlineSample.specular).toBe(0);
  expect(matteOverlineSample.glossBoost).toBe(0);

  const payload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      lip: {
        ...DEFAULT_REGION_RECIPES.lip,
        textureSample: glossyGradientSample,
      },
    },
    DEFAULT_ACTIVE_REGIONS,
    'lip',
    DEFAULT_RENDERER_MODE,
    12345,
  );
  const lipLayer = payload.layers.find(layer => layer.region === 'lip')!;

  expect(lipLayer.texture).toBe('gradient_lip');
  expect(lipLayer.finish).toBe('gloss');
  expect(lipLayer.maskTextureId).toBe('psd-arcore-lip-style-v1');
  expect(lipLayer.passCount).toBe(2);
  expect(lipLayer.specular).toBeGreaterThan(0.7);
  expect(lipLayer.glossBoost).toBeGreaterThan(0.6);
  expect(lipLayer.glossBoost).toBeLessThan(0.75);
  expect(lipLayer.gradientAmount).toBe(1);
});

test('surfaces Apple Vision lip boundary diagnostics from Unity recipe events', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  sendUnityMessage(renderer!, {
    type: 'recipe_applied',
    region: 'lip',
    layer: 'lip',
    texture: 'gloss_lip',
    sample: 'gloss_lip',
    textureMode: 'sample',
    lipRenderLayerMode: 'soft_sdf_logical_multilayer',
    glossHighlightMode: 'matte_base_wet_sheen',
    blendMode: 'multiply',
    finish: 'gloss',
    maskTextureId: 'lip-vision-boundary-v1',
    color: '#D94B74',
    opacity: 0.72,
    intensity: 0.68,
    applied: true,
    faceCount: 1,
    meshTriangles: 2304,
    maskTriangles: 2304,
    uvAvailable: true,
    stateAction: 'tracking_render',
    topologyAuditStatus: 'pass_uv_topology_ready',
    maskSource: 'apple_vision_runtime_lip_landmarks',
    visionBoundaryStatus: 'ok',
    visionBoundarySource: 'apple_vision_runtime_lip_landmarks',
    visionBoundaryCoordinateMode: 'raw-y->flip-y->face-local-warp->arface-uv-bake',
    visionBoundaryOuterPointCount: 12,
    visionBoundaryInnerPointCount: 8,
    visionBoundaryImageWidth: 1179,
    visionBoundaryImageHeight: 2556,
    visionBoundaryAgeMs: 90,
    visionBoundaryFaceMotionScore: 0.276,
    visionBoundaryFaceCenterShiftPx: 42.4,
    visionBoundaryFaceScaleDelta: 0.08,
    visionBoundaryFaceMotionRisk: 'medium_face_motion',
    sourceTriangles: 2304,
    culledTriangles: 2081,
    meshCullingMode: 'apple_vision_lip_landmark_arface_uv_baked',
    maskSoftSampleMode: 'feather_scaled_13tap_near_far',
    maskFeatherNearRadiusPx: 3.447,
    maskFeatherFarRadiusPx: 6.377,
    maskTextureDiagnosticStatus:
      'vision_arface_uv_baked_outer_minus_inner_soft_falloff',
    maskTextureActivePixelCountGt8: 1,
    maskTextureActiveCoverageGt8: 1,
    maskTextureActiveBbox: 'left=0,top=0,right=0,bottom=0,width=1,height=1',
  });

  const text = collectText(renderer!);

  expect(text).toContain('apple_vision_runtime_lip_landmarks');
  expect(text).toContain('layers=soft_sdf_logical_multilayer');
  expect(text).toContain('gloss=matte_base_wet_sheen');
  expect(text).toContain('blend=multiply');
  expect(text).toContain('finish=gloss');
  expect(text).toContain('maskTex=lip-vision-boundary-v1');
  expect(text).toContain('soft=feather_scaled_13tap_near_far');
  expect(text).toContain('featherPx=3.45/6.38');
  expect(text).toContain('vision=ok:12/8');
  expect(text).toContain(
    'visionCoord=raw-y->flip-y->face-local-warp->arface-uv-bake',
  );
  expect(text).toContain('visionMotion=0.276/medium_face_motion');
  expect(text).toContain(
    'maskDiag=vision_arface_uv_baked_outer_minus_inner_soft_falloff',
  );
  expect(text).toContain('texGt8=');
  expect(text).toContain('1');
  expect(text).toContain('left=0,top=0,right=0,bottom=0');
  expect(text).toContain('cull=2081/2304');
  expect(text).toContain('apple_vision_lip_landmark_arface_uv_baked');
});

test('surfaces Vision smoothing transition and capture motion events', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  sendUnityMessage(renderer!, {
    type: 'e7_vision_lip_boundary',
    status: 'ok',
    available: true,
    source: 'apple_vision_runtime_lip_landmarks',
    coordinateMode: 'raw-y',
    outerPointCount: 12,
    innerPointCount: 8,
    imageWidth: 1179,
    imageHeight: 2556,
    stabilizationMode: 'temporal_smooth_transition|large_face_motion_smooth',
    transitionProgress: 0.42,
    transitionDurationMs: 160,
    faceBoundsAvailable: true,
    visionBoundaryFaceMotionScore: 0.39,
    visionBoundaryFaceCenterShiftPx: 64.2,
    visionBoundaryFaceScaleDelta: 0.13,
    visionBoundaryFaceMotionRisk: 'large_face_motion',
    rawCameraFrameStored: false,
    offDeviceUpload: false,
  });

  pressByText(renderer!, 'Debug');
  const text = collectText(renderer!);

  expect(text).toContain('e7_vision_lip_boundary');
  expect(text).toContain('status=ok');
  expect(text).toContain('coord=raw-y');
  expect(text).toContain('points=12/8');
  expect(text).toContain(
    'smooth=temporal_smooth_transition|large_face_motion_smooth',
  );
  expect(text).toContain('t=0.42/160');
  expect(text).toContain('faceLocal=true');
  expect(text).toContain('motion=0.390/large_face_motion');
  expect(text).toContain('privacy raw=false offDevice=false');
});

test('keeps thin wet-line diagnostics off matte lip recipe events', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  sendUnityMessage(renderer!, {
    type: 'recipe_applied',
    region: 'lip',
    layer: 'lip',
    texture: 'matte_lip',
    sample: 'matte_lip',
    rendererId: 'lip-smooth-region-mask-renderer',
    textureMode: 'sample',
    lipRenderLayerMode: 'soft_sdf_logical_multilayer',
    glossHighlightMode: 'none',
    blendMode: 'multiply',
    finish: 'matte',
    maskTextureId: 'lip-drawn-style-atlas-v1',
    color: '#D94B74',
    opacity: 0.72,
    intensity: 0.84,
    applied: true,
    faceCount: 1,
    meshTriangles: 2304,
    maskTriangles: 2304,
    uvAvailable: true,
    stateAction: 'tracking_render',
    topologyAuditStatus: 'pass_uv_topology_ready',
    maskSource: 'lip_style_atlas_v1_uv_back_projection',
    boundaryRenderer: 'rgba_style_atlas_logical_multilayer_sdf_feather',
    sourceTriangles: 2304,
    culledTriangles: 2081,
    meshCullingMode: 'lip_atlas_threshold_sample',
    maskSoftSampleMode: 'feather_scaled_13tap_near_far',
    maskFeatherNearRadiusPx: 3.447,
    maskFeatherFarRadiusPx: 6.377,
    maskTextureActivePixelCountGt8: 957,
    maskTextureActiveCoverageGt8: 0.0036,
    maskTextureActiveBbox:
      'left=207,top=292,right=302,bottom=347,width=96,height=56',
  });

  const text = collectText(renderer!);

  expect(text).toContain('texture=matte_lip');
  expect(text).toContain('renderer=lip-smooth-region-mask-renderer');
  expect(text).toContain('layers=soft_sdf_logical_multilayer');
  expect(text).toContain('gloss=none');
  expect(text).toContain('finish=matte');
  expect(text).toContain('soft=feather_scaled_13tap_near_far');
  expect(text).toContain('featherPx=3.45/6.38');
  expect(text).not.toContain('matte_base_wet_sheen');
});

test('surfaces eyebrow placement diagnostics from Unity recipe events', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  sendUnityMessage(renderer!, {
    type: 'recipe_applied',
    region: 'brow',
    layer: 'brow',
    texture: 'natural_brow',
    sample: 'natural_brow',
    rendererId: 'brow-smooth-region-mask-renderer',
    textureMode: 'sample',
    blendMode: 'normal',
    finish: 'matte',
    maskTextureId: 'brow-back-arch-soft-mix-v1',
    color: '#4A342B',
    opacity: 0.75,
    intensity: 0.75,
    coverage: 0.62,
    maskSpreadX: 0.12,
    maskOffsetY: 0.024,
    browGap: 0.12,
    browAngle: -0.12,
    browArch: 0.027,
    applied: true,
    faceCount: 1,
    meshTriangles: 512,
    maskTriangles: 512,
    uvAvailable: true,
    stateAction: 'tracking_render',
    topologyAuditStatus: 'pass_uv_topology_ready',
    maskSource: 'brow-back-arch-soft-mix-v1',
    boundaryRenderer: 'brow_smooth_region_mask',
    browCleanupSource: 'ar_camera_background_texture',
    browCleanupFallback: 'grabpass_live_frame_skin_sample',
    browCleanupStatus: 'ar_camera_background_ready',
    browCleanupSourceMode: 'ar_camera_background',
    browCleanupFallbackAvailable: true,
    browCleanupCameraTextureWidth: 1179,
    browCleanupCameraTextureHeight: 2556,
  });

  const text = collectText(renderer!);

  expect(text).toContain('Renderer Legacy mask');
  expect(text).toContain('recipe_applied region=brow');
  expect(text).toContain('renderer=brow-smooth-region-mask-renderer');
  expect(text).toContain('maskTex=brow-back-arch-soft-mix-v1');
  expect(text).toContain('gap=0.120');
  expect(text).toContain('y=0.024');
  expect(text).toContain('angle=-0.120');
  expect(text).toContain('arch=0.027');
  expect(text).toContain('cleanupSource=ar_camera_background_texture');
  expect(text).toContain('cleanupFallback=grabpass_live_frame_skin_sample');
  expect(text).toContain('cleanupStatus=ar_camera_background_ready');
  expect(text).toContain('cleanupMode=ar_camera_background');
  expect(text).toContain('cleanupFallbackAvailable=true');
  expect(text).toContain('cleanupCameraTex=1179x2556');
});

test('posts MediaPipe region overlay renderer by default before build', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  ReactTestRenderer.act(() => {
    jest.advanceTimersByTime(1000);
  });

  const recipePostCall = consoleLogSpy.mock.calls.find(call =>
    call.includes('[E7] rn_texture_recipe_batch_post'),
  );

  expect(recipePostCall).toBeTruthy();
  expect(recipePostCall).toContain('rendererMode=mediapipe-region-overlay');
  expect(recipePostCall).toContain('focusRegion=lip');
  expect(recipePostCall).toContain('focusMaskTextureId=psd-arcore-lip-style-v1');
  expect(recipePostCall).toContain('lipMaskTextureId=psd-arcore-lip-style-v1');
  expect(recipePostCall).not.toContain('lipMaskTextureId=lip-vision-boundary-v1');
  expect(recipePostCall).not.toContain('cand' + 'idateId=');
  expect(recipePostCall).not.toContain('vari' + 'antId=');
});

test('presents MediaPipe as the product route and labels alternate sources as diagnostics', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  sendUnityMessage(renderer!, {
    type: 'recipe_applied',
    region: 'lip',
    rendererMode: 'mediapipe-region-overlay',
    rendererId: 'lip-mediapipe-region-overlay-renderer',
    maskTextureId: 'psd-arcore-lip-style-v1',
    stateAction: 'mediapipe_region_rendered',
  });

  const text = collectText(renderer!);
  expect(text).toContain('Renderer MediaPipe');
  expect(text).toContain('MediaPipe lip');
  expect(text).toContain('MediaPipe flat');
  expect(text).toContain('Legacy atlas diagnostic');
  expect(text).toContain('Vision diagnostic');
  expect(text).toContain('Legacy mask');
  expect(text).not.toContain('Renderer lip-mediapipe-region-overlay-renderer');
  expect(text).not.toContain('PSD ARCORE');
  expect(text).not.toContain('PSD FLAT');
  expect(text).not.toContain('ATLAS');
  expect(text).not.toContain('VISION');
  expect(text).not.toContain('FLAT SHARP');
});

test('builds five lip style recipe payloads with preset material fields', () => {
  const lipStyles = RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureOption => textureOption.region === 'lip',
  );

  expect(lipStyles.map(textureOption => textureOption.name)).toEqual([
    'matte_lip',
    'gloss_lip',
    'full_lip',
    'gradient_lip',
    'overline_lip',
  ]);

  lipStyles.forEach(textureSample => {
    const payload = buildValidationRecipeBatchPayload(
      {
        ...DEFAULT_REGION_RECIPES,
        lip: {
          ...DEFAULT_REGION_RECIPES.lip,
          textureSample,
        },
      },
      DEFAULT_ACTIVE_REGIONS,
      'lip',
      DEFAULT_RENDERER_MODE,
      12345,
    );
    const lipLayer = payload.layers.find(layer => layer.region === 'lip')!;
    const cheekLayer = payload.layers.find(layer => layer.region === 'cheek')!;
    const eyeLayer = payload.layers.find(layer => layer.region === 'eye')!;
    const browLayer = payload.layers.find(layer => layer.region === 'brow')!;

    expect(payload.layers).toHaveLength(4);
    expect(payload.rendererMode).toBe('mediapipe-region-overlay');
    expect(payload.lookId).toBe('lip_makeup_validation_v1');
    expect(payload.activeRegions).toBe('lip');
    expect(payload.enabledLayerCount).toBe(1);
    expect(lipLayer.texture).toBe(textureSample.name);
    expect(lipLayer.maskTextureId).toBe('psd-arcore-lip-style-v1');
    expect(lipLayer.enabled).toBe(true);
    expect(lipLayer.intensity).toBe(DEFAULT_REGION_RECIPES.lip.intensity);
    expect(lipLayer.textureAmount).toBe(DEFAULT_REGION_RECIPES.lip.intensity);
    expect(lipLayer.secondaryColor).toBe(textureSample.secondaryColor);
    expect(lipLayer.coverage).toBe(textureSample.coverage);
    expect(lipLayer.finish).toBe(textureSample.finish);
    expect(lipLayer.roughness).toBe(textureSample.roughness);
    expect(lipLayer.specular).toBe(textureSample.specular);
    expect(lipLayer.specularPower).toBe(textureSample.specularPower);
    expect(lipLayer.glossBoost).toBe(textureSample.glossBoost);
    expect(lipLayer.gradientAmount).toBe(textureSample.gradientAmount);
    expect(lipLayer.preserveDetail).toBe(textureSample.preserveDetail);
    expect(lipLayer.blendMode).toBe('multiply');
    if (textureSample.name === 'gloss_lip') {
      expect(lipLayer.specular).toBeGreaterThan(0.7);
      expect(lipLayer.glossBoost).toBeGreaterThan(0.6);
      expect(lipLayer.glossBoost).toBeLessThan(0.75);
      expect(lipLayer.passCount).toBe(2);
    }
    if (textureSample.name === 'matte_lip') {
      expect(lipLayer.preserveDetail).toBe(true);
      expect(lipLayer.specular).toBe(0);
      expect(lipLayer.passCount).toBe(1);
    }
    if (textureSample.name === 'gradient_lip') {
      expect(lipLayer.maskTextureId).toBe('psd-arcore-lip-style-v1');
      expect(lipLayer.coverage).toBeGreaterThan(0.9);
      expect(lipLayer.gradientAmount).toBe(1);
      expect(lipLayer.passCount).toBe(1);
    }
    expect(cheekLayer.texture).toBe('soft_blush');
    expect(cheekLayer.maskTextureId).toBe('psd-arcore-cheek-undereye-v1');
    expect(cheekLayer.enabled).toBe(false);
    expect(eyeLayer.texture).toBe('shimmer_eye');
    expect(eyeLayer.maskTextureId).toBe('eye-drawn-mask-v1');
    expect(eyeLayer.enabled).toBe(false);
    expect(browLayer.texture).toBe('natural_brow');
    expect(browLayer.maskTextureId).toBe('psd-arcore-brow-semi-arch-v1');
    expect(browLayer.enabled).toBe(false);
  });
});

test('keeps Unity cheek PSD mask allowlist in sync with RN options', () => {
  const overlayPath = path.resolve(
    __dirname,
    '../../../unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs',
  );
  const overlaySource = fs.readFileSync(overlayPath, 'utf8');

  [
    'psd-arcore-cheek-undereye-v1',
    'psd-arcore-cheek-asia-z-v1',
    'psd-arcore-cheek-sunkissed-v1',
    'psd-arcore-cheek-daily-oval-v1',
    'psd-arcore-cheek-undereye2-v1',
    'psd-arcore-cheek-lovely-round-v1',
    'psd-arcore-cheek-lifted-diagonal-v1',
  ].forEach(maskTextureId => {
    expect(overlaySource).toContain(`maskTextureId == "${maskTextureId}"`);
  });
});

test('keeps brow rendering from auto-starting MediaPipe screen capture', () => {
  const rnBridgePath = path.resolve(
    __dirname,
    '../../../unity/MakeupARUnityValidation/Assets/Scripts/RNBridge.cs',
  );
  const rnBridgeSource = fs.readFileSync(rnBridgePath, 'utf8');

  expect(rnBridgeSource).not.toContain(
    'SetRuntimeRequested(IsActiveRegionIncluded(activeRegions, "brow"))',
  );
  expect(rnBridgeSource).toContain(
    'mediaPipeBrowLandmarkRuntime.SetRuntimeRequested(false)',
  );
});

test('keeps Vision lip boundary updates from hiding makeup overlays during capture', () => {
  const visionRuntimePath = path.resolve(
    __dirname,
    '../../../unity/MakeupARUnityValidation/Assets/Scripts/E7VisionLipBoundaryRuntime.cs',
  );
  const visionRuntimeSource = fs.readFileSync(visionRuntimePath, 'utf8');

  expect(visionRuntimeSource).toContain('CaptureIntervalSeconds = 0.35f');
  expect(visionRuntimeSource).toContain('FreshBoundaryMaxAgeMs = 900');
  expect(visionRuntimeSource).not.toContain(
    'regionMaskOverlay.SetVisionCaptureSuppressed(true)',
  );
  expect(visionRuntimeSource).not.toContain(
    'regionMaskOverlay.SetVisionCaptureSuppressed(false)',
  );
});

test('passes selected lip color, finish, and intensity through payload', () => {
  const selectedColor = RECIPE_COLOR_OPTIONS.find(
    colorOption => colorOption.name === 'berry',
  )!;
  const selectedTextureSample = composeLipTextureSample('glossy', 'full');
  const payload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      lip: {
        ...DEFAULT_REGION_RECIPES.lip,
        color: selectedColor,
        intensity: 0.85,
        textureSample: selectedTextureSample,
      },
    },
    DEFAULT_ACTIVE_REGIONS,
    'lip',
    DEFAULT_RENDERER_MODE,
    12345,
  );
  const lipLayer = payload.layers.find(layer => layer.region === 'lip')!;

  expect(payload.texture).toBe('full_lip');
  expect(payload.textureAmount).toBe(0.85);
  expect(lipLayer.color).toBe('#A8325F');
  expect(lipLayer.texture).toBe('full_lip');
  expect(lipLayer.intensity).toBe(0.85);
  expect(lipLayer.textureAmount).toBe(0.85);
  expect(lipLayer.finish).toBe('gloss');
  expect(lipLayer.specular).toBeGreaterThan(0.7);
  expect(lipLayer.glossBoost).toBeGreaterThan(0.6);
  expect(lipLayer.glossBoost).toBeLessThan(0.75);
  expect(lipLayer.blendMode).toBe('multiply');
  expect(lipLayer.passCount).toBe(2);
});

test('enables shader glossy pass from separate highlight mask across lip areas', () => {
  const shaderPath = path.resolve(
    __dirname,
    '../../../unity/MakeupARUnityValidation/Assets/Shaders/SmoothRegionMask.shader',
  );
  const shaderSource = fs.readFileSync(shaderPath, 'utf8');

  expect(shaderSource).not.toContain(
    '_LipStyleMode < 0.5 || _LipStyleMode >= 1.5',
  );
  expect(shaderSource).toContain('_GlossBoost <= 0.001');
  expect(shaderSource).toContain('sampler2D _GlossMaskTex');
  expect(shaderSource).toContain('tex2D(_GlossMaskTex');
  expect(shaderSource).toContain('styleGlossSeed');
  expect(shaderSource).toContain('_DebugMaskMode > 0.5');
  expect(shaderSource).toContain('return fixed4(rawMask.xxx');
  expect(shaderSource).not.toContain(
    'styleGlossSeed = max(styleGlossSeed, saturate(max(mask.b',
  );
});

test('uses lip style channels for mesh culling instead of full-only culling', () => {
  const overlayPath = path.resolve(
    __dirname,
    '../../../unity/MakeupARUnityValidation/Assets/Scripts/E3RegionMaskOverlay.cs',
  );
  const overlaySource = fs.readFileSync(overlayPath, 'utf8');

  expect(overlaySource).toContain('ResolveMaskCullingChannelMask');
  expect(overlaySource).toContain('case "gradient_lip":');
  expect(overlaySource).toContain('MaskChannelR | MaskChannelB');
  expect(overlaySource).toContain('case "overline_lip":');
  expect(overlaySource).toContain('MaskChannelR | MaskChannelG');
});

test('keeps Unity face debug surface disabled across view modes', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'Debug');

  let latestVisibilityPostCall = [...consoleLogSpy.mock.calls]
    .reverse()
    .find(call => call.includes('[E7] rn_region_overlay_visibility_post'));

  expect(latestVisibilityPostCall).toBeTruthy();
  expect(latestVisibilityPostCall).toContain('visible=true');
  expect(latestVisibilityPostCall).toContain('faceDebugSurfaceSuppressed=true');
  expect(latestVisibilityPostCall).toContain('validationViewMode=full');

  pressByText(renderer!, 'Clean');

  latestVisibilityPostCall = [...consoleLogSpy.mock.calls]
    .reverse()
    .find(call => call.includes('[E7] rn_region_overlay_visibility_post'));

  expect(latestVisibilityPostCall).toBeTruthy();
  expect(latestVisibilityPostCall).toContain('visible=false');
  expect(latestVisibilityPostCall).toContain('faceDebugSurfaceSuppressed=true');
  expect(latestVisibilityPostCall).toContain('validationViewMode=clean');
});

test('shows eyebrow region and brow texture controls in HUD mode', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'brow');
  const text = collectText(renderer!);

  expect(text).toContain('focus brow');
  expect(text).toContain('Natural');
  expect(text).toContain('Soft Powder');
  expect(text).not.toContain('natural_brow');
  expect(text).not.toContain('soft_brow');
  expect(text).toContain('ash_brown');
  expect(text).toContain('neutral_brown');
  expect(text).toContain('dark_brown');
  expect(text).toContain('soft_black');
  expect(text).toContain('light_brown');
  expect(text).not.toContain('rose');
  expect(text).not.toContain('red');
  expect(text).toContain('Brow QA');
  expect(text).toContain('Color');
  expect(text).toContain('Placement');
  expect(text).toContain('Temperature');
  expect(text).toContain('Depth');
  expect(text).toContain('Gap');
  expect(text).toContain('Angle');
  expect(text).toContain('Arch');
  expect(text).toContain('Arch Position');
  expect(text).not.toContain('Brow Spread');
  expect(text).not.toContain('Brow X');
  expect(text).toContain('Brow Y');
  expect(text).toContain('Soft flat');
  expect(text).toContain('Slim tail fine');
  expect(text).toContain('Daily flat');
  expect(text).toContain('Flat sharp');
  expect(text).toContain('Flat multiply');
  expect(text).toContain('Daily hair');
  expect(text).toContain('Natural hair');
  expect(text).toContain('Narrow hair');
  expect(text).toContain('Light brown');
  expect(text).toContain('Texture Detail');
  expect(text).not.toContain('High arch fine');
  expect(text).not.toContain('Legacy drawn');
  expect(text).not.toContain('LEGACY DRAWN');
});

test('shows region-specific tuning controls for lip and brow', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'lip');
  const lipText = collectText(renderer!);

  expect(lipText).toContain('focus lip');
  expect(lipText).toContain('Normal');
  expect(lipText).toContain('Matte');
  expect(lipText).toContain('Glossy');
  expect(lipText).toContain('Full');
  expect(lipText).toContain('Gradient');
  expect(lipText).toContain('Overlip');
  expect(lipText).not.toContain('Brow QA');
  expect(lipText).not.toContain('natural_brow');
  expect(lipText).not.toContain('soft_brow');
  expect(lipText).not.toContain('Gap');
  expect(lipText).not.toContain('Angle');
  expect(lipText).not.toContain('Arch');
  expect(lipText).not.toContain('Texture Detail');

  pressByText(renderer!, 'brow');
  const browText = collectText(renderer!);

  expect(browText).toContain('focus brow');
  expect(browText).toContain('Natural');
  expect(browText).toContain('Soft Powder');
  expect(browText).not.toContain('natural_brow');
  expect(browText).not.toContain('soft_brow');
  expect(browText).toContain('Gap');
  expect(browText).toContain('Angle');
  expect(browText).toContain('Arch');
  expect(browText).toContain('Arch Position');
  expect(browText).toContain('Skin Restore');
  expect(browText).toContain('Cleanup');
  expect(browText).toContain('Reshape');
  expect(browText).toContain('Texture Detail');
  expect(browText).toContain('Coverage');
  expect(browText).toContain('Feather');
  expect(browText).not.toContain('Normal');
  expect(browText).not.toContain('Overlip');
  expect(browText).not.toContain('Roughness');
  expect(browText).not.toContain('Specular');
  expect(browText).not.toContain('Glossy');
  expect(browText).not.toContain('Gradient');
});

test('toggles eyebrow skin restoration from brow QA controls', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'brow');
  pressByTestID(renderer!, 'brow-cleanup-enabled-toggle');

  const toggle = renderer!.root.findByProps({
    testID: 'brow-cleanup-enabled-toggle',
  });
  const latestRecipePostCall = [...consoleLogSpy.mock.calls]
    .reverse()
    .map(call => call.join(' '))
    .find(call => call.includes('[E7] rn_texture_recipe_batch_post'));

  expect(toggle.props.accessibilityState.checked).toBe(false);
  expect(collectText(renderer!)).toContain('Skin Restore Off');
  expect(latestRecipePostCall).toBeTruthy();
  expect(latestRecipePostCall).toContain('focusRegion=brow');
  expect(latestRecipePostCall).toContain('payloadBytes=');
});

test('adds fine nudge buttons for brow placement sliders', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'brow');
  pressByTestID(renderer!, 'brow-gap-slider-increment');

  expect(collectText(renderer!)).toContain('gap 0.007');

  pressByTestID(renderer!, 'brow-gap-slider-decrement');

  expect(collectText(renderer!)).toContain('gap 0.000');
});

test('keeps selected brow mask and placement warp when switching natural and soft brow presets', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'brow');
  pressByTestID(renderer!, 'brow-mask-brow-png-daily-hair-v1');
  incrementSliderByTestID(renderer!, 'brow-gap-slider');
  incrementSliderByTestID(renderer!, 'brow-angle-slider', 5);
  incrementSliderByTestID(renderer!, 'brow-arch-slider', 5);
  incrementSliderByTestID(renderer!, 'brow-arch-position-slider', 5);

  let dailyHairButton = renderer!.root.findByProps({
    testID: 'brow-mask-brow-png-daily-hair-v1',
  });
  expect(dailyHairButton.props.accessibilityState?.selected).toBe(true);

  pressByTestID(renderer!, 'brow-finish-soft_brow');

  dailyHairButton = renderer!.root.findByProps({
    testID: 'brow-mask-brow-png-daily-hair-v1',
  });
  const flatSharpButton = renderer!.root.findByProps({
    testID: 'brow-mask-brow-png-dailyflat-sharp-v1',
  });

  expect(dailyHairButton.props.accessibilityState?.selected).toBe(true);
  expect(flatSharpButton.props.accessibilityState?.selected).toBe(false);
  const text = collectText(renderer!);

  expect(text).toContain('style Soft Powder');
  expect(text).toContain('gap 0.034');
  expect(text).toContain('angle 0.080');
  expect(text).toContain('arch 0.025');
  expect(text).toContain('archPos 0.075');
});

test('resets brow placement deltas when changing brow mask design', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'brow');
  incrementSliderByTestID(renderer!, 'brow-gap-slider');
  incrementSliderByTestID(renderer!, 'brow-y-slider');
  incrementSliderByTestID(renderer!, 'brow-angle-slider', 5);
  incrementSliderByTestID(renderer!, 'brow-arch-slider', 5);
  incrementSliderByTestID(renderer!, 'brow-arch-position-slider', 5);

  expect(collectText(renderer!)).toContain('gap 0.034');

  pressByTestID(renderer!, 'brow-mask-brow-png-dailyflat-sharp-v1');
  const flatSharpButton = renderer!.root.findByProps({
    testID: 'brow-mask-brow-png-dailyflat-sharp-v1',
  });
  const text = collectText(renderer!);

  expect(flatSharpButton.props.accessibilityState?.selected).toBe(true);
  expect(text).toContain('gap 0.000');
  expect(text).toContain('y 0.000');
  expect(text).toContain('angle 0.000');
  expect(text).toContain('arch 0.000');
  expect(text).toContain('archPos 0.000');
});

test('applies PSD semi-arch brow detail and cleanup defaults on mask selection', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'brow');
  pressByTestID(renderer!, 'brow-mask-psd-arcore-brow-semi-arch-v1');

  const psdButton = renderer!.root.findByProps({
    testID: 'brow-mask-psd-arcore-brow-semi-arch-v1',
  });
  const text = collectText(renderer!);

  expect(psdButton.props.accessibilityState?.selected).toBe(true);
  expect(text).toContain('detail 64%');
  expect(text).toContain('cleanup 52%');
  expect(text).toContain('y 0.000');
});

test('allows cheek and eye toggles for placement validation while preserving 4-layer batch', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const cheekToggle = renderer!.root.findByProps({
    testID: 'region-toggle-cheek',
  });
  const eyeToggle = renderer!.root.findByProps({ testID: 'region-toggle-eye' });

  expect(cheekToggle.props.disabled).toBeUndefined();
  expect(cheekToggle.props.accessibilityState.disabled).toBeUndefined();
  expect(cheekToggle.props.accessibilityState.checked).toBe(false);
  expect(eyeToggle.props.disabled).toBeUndefined();
  expect(eyeToggle.props.accessibilityState.disabled).toBeUndefined();
  expect(eyeToggle.props.accessibilityState.checked).toBe(false);

  expect(collectText(renderer!)).toContain('active=lip');

  ReactTestRenderer.act(() => {
    cheekToggle.props.onPress();
  });

  expect(
    renderer!.root.findByProps({ testID: 'region-toggle-cheek' }).props
      .accessibilityState.checked,
  ).toBe(true);
  expect(collectText(renderer!)).toContain('active=lip,cheek');

  ReactTestRenderer.act(() => {
    renderer!.root.findByProps({ testID: 'region-toggle-eye' }).props.onPress();
  });

  expect(
    renderer!.root.findByProps({ testID: 'region-toggle-eye' }).props
      .accessibilityState.checked,
  ).toBe(true);
  expect(collectText(renderer!)).toContain('active=lip,cheek,eye');

  const payload = buildValidationRecipeBatchPayload(
    DEFAULT_REGION_RECIPES,
    {
      lip: true,
      cheek: true,
      eye: true,
      brow: false,
    },
    'lip',
    DEFAULT_RENDERER_MODE,
    12345,
  );

  expect(payload.layers).toHaveLength(4);
  expect(payload.layers.find(layer => layer.region === 'lip')!.enabled).toBe(
    true,
  );
  expect(payload.layers.find(layer => layer.region === 'cheek')!.enabled).toBe(
    true,
  );
  expect(payload.layers.find(layer => layer.region === 'eye')!.enabled).toBe(
    true,
  );
  expect(payload.layers.find(layer => layer.region === 'brow')!.enabled).toBe(
    false,
  );
});

test('keeps active regions enabled when selecting them from another focus', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  ReactTestRenderer.act(() => {
    renderer!.root.findByProps({ testID: 'region-toggle-cheek' }).props.onPress();
  });

  expect(collectText(renderer!)).toContain('active=lip,cheek');
  expect(collectText(renderer!)).toContain('focus cheek');

  ReactTestRenderer.act(() => {
    renderer!.root.findByProps({ testID: 'region-toggle-lip' }).props.onPress();
  });

  expect(collectText(renderer!)).toContain('active=lip,cheek');
  expect(collectText(renderer!)).toContain('focus lip');
  expect(
    renderer!.root.findByProps({ testID: 'region-toggle-lip' }).props
      .accessibilityState.checked,
  ).toBe(true);
});

test('toggles lip region on and off', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const getToggle = () =>
    renderer!.root.findByProps({ testID: 'region-toggle-lip' });

  expect(getToggle().props.accessibilityState.checked).toBe(true);

  ReactTestRenderer.act(() => {
    getToggle().props.onPress();
  });

  expect(getToggle().props.accessibilityState.checked).toBe(false);
  expect(collectText(renderer!)).toContain('active=none');

  ReactTestRenderer.act(() => {
    getToggle().props.onPress();
  });

  expect(getToggle().props.accessibilityState.checked).toBe(true);
  expect(collectText(renderer!)).toContain('active=lip');
});
