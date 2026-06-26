/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import App from '../App';

const mockUnityPostMessage = jest.fn();

jest.mock('react-native', () => {
  const ReactRuntime = require('react');

  const createComponent = (name: string) =>
    ReactRuntime.forwardRef(({ children, style, ...props }: any, ref: any) =>
      ReactRuntime.createElement(name, { ...props, ref, style }, children),
    );

  const View = createComponent('View');
  const Text = createComponent('Text');
  const ScrollView = createComponent('ScrollView');

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
    PanResponder: {
      create: jest.fn(() => ({ panHandlers: {} })),
    },
    Pressable,
    ScrollView,
    StatusBar: jest.fn(() => null),
    StyleSheet: {
      create: (styles: object) => styles,
      hairlineWidth: 1,
    },
    Text,
    useColorScheme: jest.fn(() => 'light'),
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
      postMessage: mockUnityPostMessage,
    }));

    return <View testID="unity-view" {...props} />;
  });
});

let consoleLogSpy: jest.SpyInstance;
let consoleErrorSpy: jest.SpyInstance;

beforeEach(() => {
  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  mockUnityPostMessage.mockClear();
  consoleLogSpy = jest.spyOn(console, 'log').mockImplementation(() => {});
  consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation(() => {});
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

function getLastRecipePayload() {
  const recipeCall = [...mockUnityPostMessage.mock.calls]
    .reverse()
    .find(
      call => call[0] === 'RNBridge' && call[1] === 'ApplyRecipeJson',
    );

  expect(recipeCall).toBeTruthy();

  return JSON.parse(String(recipeCall?.[2]));
}

function getLastGeneratedLipMaskPayload() {
  const generatedCall = [...mockUnityPostMessage.mock.calls]
    .reverse()
    .find(
      call =>
        call[0] === 'RNBridge' && call[1] === 'ApplyGeneratedLipMaskJson',
    );

  expect(generatedCall).toBeTruthy();

  return JSON.parse(String(generatedCall?.[2]));
}

test('renders home with neutral validation copy', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });

  const text = collectText(renderer!);

  expect(text).toContain('Makeup AR Validation');
  expect(text).toContain('Ready to start AR');
  expect(text).not.toContain('Region ' + 'Precision');
  expect(text).not.toContain('Validation status');
  expect(text).not.toContain('E7.3');
});

test('does not render old selector controls', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const text = collectText(renderer!);

  expect(text).not.toContain('Vari' + 'ant');
  expect(text).not.toContain('vari' + 'ant');
  expect(text).not.toContain('soft-' + 'wide');
  expect(text).not.toContain('co' + 're');

  pressByText(renderer!, 'Debug');
  const debugText = collectText(renderer!);
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
  expect(hudText).toContain('daily');
  expect(hudText).toContain('opac');
  expect(hudText.indexOf('Regions')).toBeLessThan(
    hudText.indexOf('AR Status'),
  );
  expect(hudText).toContain('active=lip');
  expect(hudText).not.toContain('E7.03 HUD');

  pressByText(renderer!, 'Clean');
  expect(collectText(renderer!)).not.toContain('Regions');
  expect(collectText(renderer!)).not.toContain('E7.03 HUD');
  expect(collectText(renderer!)).not.toContain('opac');

  pressByText(renderer!, 'Debug');
  expect(collectText(renderer!)).toContain('Evidence metadata');
  expect(collectText(renderer!)).not.toContain('AR Status');
  expect(collectText(renderer!)).not.toContain('opac');
});

test('posts lip daily sample by default before build', async () => {
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
  expect(recipePostCall).toContain('rendererMode=smooth-region-mask');
  expect(recipePostCall).toContain('lookId=lip_daily');
  expect(recipePostCall).toContain('finish=cream');
  expect(recipePostCall).toContain('activeRegions=lip');
  expect(recipePostCall).toContain('enabledLayerCount=1');
  expect(recipePostCall).not.toContain('cand' + 'idateId=');
  expect(recipePostCall).not.toContain('vari' + 'antId=');

  const payload = getLastRecipePayload();
  expect(payload.version).toBe(2);
  expect(payload.lookId).toBe('lip_daily');
  expect(payload.candidateId).toBe('lip-smooth-mask-v1');
  expect(payload.maskTextureId).toBe('lip-smooth-mask-v1');
  expect(payload.cornerReach).toBe(0);
  expect(payload.upperLipTightness).toBe(0);
  expect(payload.lowerLipTightness).toBe(0);
  expect(payload.verticalOffset).toBe(0);
  expect(payload.activeRegions).toBe('lip');
  expect(payload.enabledLayerCount).toBe(1);
  expect(payload.layers).toHaveLength(3);
  expect(payload.layers.map((layer: any) => layer.enabled)).toEqual([
    true,
    false,
    false,
  ]);
  expect(payload.layers[0]).toMatchObject({
    region: 'lip',
    texture: 'matte_lip',
    finish: 'cream',
    textureAmount: 0.08,
    glossBoost: 0,
    cornerReach: 0,
    upperLipTightness: 0,
    lowerLipTightness: 0,
    verticalOffset: 0,
  });
});

test('switches lip sample pack values without changing 3-layer contract', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByText(renderer!, 'gloss');
  let payload = getLastRecipePayload();
  expect(payload.lookId).toBe('lip_gloss');
  expect(payload.activeRegions).toBe('lip');
  expect(payload.enabledLayerCount).toBe(1);
  expect(payload.layers).toHaveLength(3);
  expect(payload.layers[0]).toMatchObject({
    region: 'lip',
    enabled: true,
    finish: 'gloss',
    textureAmount: 0.05,
    glossBoost: 0.55,
  });
  expect(payload.layers[1].enabled).toBe(false);
  expect(payload.layers[2].enabled).toBe(false);

  pressByText(renderer!, 'texture');
  payload = getLastRecipePayload();
  expect(payload.lookId).toBe('lip_texture');
  expect(payload.activeRegions).toBe('lip');
  expect(payload.enabledLayerCount).toBe(1);
  expect(payload.layers[0]).toMatchObject({
    region: 'lip',
    enabled: true,
    finish: 'matte',
    textureAmount: 0.34,
    glossBoost: 0,
  });
  expect(payload.layers.map((layer: any) => layer.enabled)).toEqual([
    true,
    false,
    false,
  ]);
});

test('updates lip color finish and tuning values from HUD', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByTestID(renderer!, 'lip-color-berry');

  let payload = getLastRecipePayload();
  expect(payload.lookId).toBe('lip_daily');
  expect(payload.layers[0]).toMatchObject({
    color: '#B83A55',
    finish: 'cream',
    opacity: 0.42,
  });

  pressByTestID(renderer!, 'lip-finish-matte');

  payload = getLastRecipePayload();
  expect(payload.layers[0]).toMatchObject({
    color: '#B83A55',
    finish: 'matte',
    roughness: 0.92,
    specular: 0.02,
    specularPower: 8,
    glossBoost: 0,
  });

  pressByTestID(renderer!, 'lip-tuning-step-opac-up');

  payload = getLastRecipePayload();
  expect(payload.layers[0]).toMatchObject({
    color: '#B83A55',
    finish: 'matte',
    opacity: 0.45,
  });
});

test('posts lip user adjustment probe values from HUD', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByTestID(renderer!, 'lip-adjustment-step-corner-up');

  let payload = getLastRecipePayload();
  expect(payload.cornerReach).toBe(0.05);
  expect(payload.upperLipTightness).toBe(0);
  expect(payload.layers[0]).toMatchObject({
    region: 'lip',
    cornerReach: 0.05,
    upperLipTightness: 0,
    lowerLipTightness: 0,
    verticalOffset: 0,
  });

  pressByTestID(renderer!, 'lip-adjust-field-upperLipTightness');
  pressByTestID(renderer!, 'lip-adjustment-step-upper-down');

  payload = getLastRecipePayload();
  expect(payload.cornerReach).toBe(0.05);
  expect(payload.upperLipTightness).toBe(-0.05);
  expect(payload.layers[0]).toMatchObject({
    cornerReach: 0.05,
    upperLipTightness: -0.05,
  });
});

test('posts generated lip mask payload with provider and assist choices', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  pressByTestID(renderer!, 'lip-generate-provider-mediapipe');
  pressByTestID(renderer!, 'lip-generate-expression-blendshapeAssist');
  pressByTestID(renderer!, 'lip-adjustment-step-corner-up');
  pressByTestID(renderer!, 'lip-generate-apply');

  const generatedPayload = getLastGeneratedLipMaskPayload();

  expect(generatedPayload.type).toBe('apply_generated_lip_mask');
  expect(generatedPayload.schemaVersion).toBe(
    'e7-generated-lip-mask-runtime-payload-v0',
  );
  expect(generatedPayload.provider).toBe('mediapipe');
  expect(generatedPayload.expressionMode).toBe('blendshapeAssist');
  expect(generatedPayload.localOnly).toBe(true);
  expect(generatedPayload.offDeviceUpload).toBe(false);
  expect(generatedPayload.longTermRawFrameStored).toBe(false);
  expect(generatedPayload.runtimeReady).toBe(false);
  expect(generatedPayload.maskTextureEncoding).toBe('raw_rgba_base64');
  expect(generatedPayload.maskTextureId).toContain(
    'e7-generated-lip-mediapipe-blendshapeAssist',
  );
  expect(generatedPayload.maskRawRgbaBase64.length).toBeGreaterThan(100);
  expect(generatedPayload.maskTextureWidth).toBe(8);
  expect(generatedPayload.maskTextureHeight).toBe(8);
  expect(generatedPayload.adjustment.cornerReach).toBeCloseTo(0.05);
});

test('keeps Unity face debug surface suppressed while Clean preserves makeup overlay', async () => {
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
  expect(latestVisibilityPostCall).toContain('visible=true');
  expect(latestVisibilityPostCall).toContain('faceDebugSurfaceSuppressed=true');
  expect(latestVisibilityPostCall).toContain('validationViewMode=clean');
});

test('allows all regions to be off before build', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  ReactTestRenderer.act(() => {
    renderer!.root.findByProps({ testID: 'region-toggle-lip' }).props.onPress();
  });

  for (const region of ['lip', 'cheek', 'eye']) {
    expect(
      renderer!.root.findByProps({ testID: `region-toggle-${region}` }).props
        .accessibilityState.checked,
    ).toBe(false);
  }

  expect(collectText(renderer!)).toContain('active=none');

  const latestRecipePostCall = [...consoleLogSpy.mock.calls]
    .reverse()
    .find(call => call.includes('[E7] rn_texture_recipe_batch_post'));

  expect(latestRecipePostCall).toBeTruthy();
  expect(latestRecipePostCall).toContain('activeRegions=none');
  expect(latestRecipePostCall).toContain('enabledLayerCount=0');
});

test.each(['lip', 'cheek', 'eye'])(
  'toggles %s region on and off',
  async region => {
    let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

    await ReactTestRenderer.act(() => {
      renderer = ReactTestRenderer.create(<App />);
    });
    enterUnityScreen(renderer!);

    const getToggle = () =>
      renderer!.root.findByProps({ testID: `region-toggle-${region}` });

    const startsEnabled = region === 'lip';

    expect(getToggle().props.accessibilityState.checked).toBe(startsEnabled);

    ReactTestRenderer.act(() => {
      getToggle().props.onPress();
    });

    expect(getToggle().props.accessibilityState.checked).toBe(!startsEnabled);

    ReactTestRenderer.act(() => {
      getToggle().props.onPress();
    });

    expect(getToggle().props.accessibilityState.checked).toBe(startsEnabled);
  },
);
