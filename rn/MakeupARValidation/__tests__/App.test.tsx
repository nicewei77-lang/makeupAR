/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import App, {
  buildValidationRecipeBatchPayload,
  DEFAULT_ACTIVE_REGIONS,
  DEFAULT_REGION_RECIPES,
  DEFAULT_RENDERER_MODE,
  LIP_TEXTURE_STYLE_OPTIONS,
  RECIPE_COLOR_OPTIONS,
  RECIPE_TEXTURE_SAMPLE_OPTIONS,
} from '../App';

jest.mock('react-native', () => {
  const ReactRuntime = require('react');

  const createComponent = (name: string) =>
    ReactRuntime.forwardRef(({ children, style, ...props }: any, ref: any) =>
      ReactRuntime.createElement(name, { ...props, ref, style }, children),
    );

  const View = createComponent('View');
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
    PanResponder: {
      create: jest.fn(() => ({ panHandlers: {} })),
    },
    Pressable,
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
      postMessage: jest.fn(),
    }));

    return <View testID="unity-view" {...props} />;
  });
});

let consoleLogSpy: jest.SpyInstance;
let consoleErrorSpy: jest.SpyInstance;

beforeEach(() => {
  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
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

test('shows lip color, finish, and intensity controls in HUD mode', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const hudText = collectText(renderer!);

  expect(hudText).toContain('rose');
  expect(hudText).toContain('coral');
  expect(hudText).toContain('Matte');
  expect(hudText).toContain('Glow');
  expect(hudText).toContain('Gradient');
  expect(hudText).toContain('Intensity');
  expect(hudText).toContain('matte_lip');

  pressByText(renderer!, 'Glow');

  expect(collectText(renderer!)).toContain('gloss_lip');

  pressByText(renderer!, 'Gradient');

  expect(collectText(renderer!)).toContain('gradient_lip');
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
    texture: 'matte_lip',
    sample: 'matte_lip',
    textureMode: 'sample',
    blendMode: 'multiply',
    finish: 'matte',
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
    visionBoundaryCoordinateMode: 'raw-y',
    visionBoundaryOuterPointCount: 12,
    visionBoundaryInnerPointCount: 8,
    visionBoundaryImageWidth: 1179,
    visionBoundaryImageHeight: 2556,
    visionBoundaryAgeMs: 90,
    sourceTriangles: 2304,
    culledTriangles: 2081,
    meshCullingMode: 'apple_vision_lip_landmark_screen_space',
    maskTextureActivePixelCountGt8: 1,
    maskTextureActiveCoverageGt8: 1,
    maskTextureActiveBbox: 'left=0,top=0,right=0,bottom=0,width=1,height=1',
  });

  const text = collectText(renderer!);

  expect(text).toContain('apple_vision_runtime_lip_landmarks');
  expect(text).toContain('blend=multiply');
  expect(text).toContain('finish=matte');
  expect(text).toContain('maskTex=lip-vision-boundary-v1');
  expect(text).toContain('vision=ok:12/8');
  expect(text).toContain('texGt8=');
  expect(text).toContain('1');
  expect(text).toContain('left=0,top=0,right=0,bottom=0');
  expect(text).toContain('cull=2081/2304');
  expect(text).toContain('apple_vision_lip_landmark_screen_space');
});

test('posts smooth mask renderer by default before build', async () => {
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
  expect(recipePostCall).not.toContain('cand' + 'idateId=');
  expect(recipePostCall).not.toContain('vari' + 'antId=');
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

    expect(payload.layers).toHaveLength(3);
    expect(payload.rendererMode).toBe('smooth-region-mask');
    expect(payload.lookId).toBe('lip_makeup_validation_v1');
    expect(payload.activeRegions).toBe('lip');
    expect(payload.enabledLayerCount).toBe(1);
    expect(lipLayer.texture).toBe(textureSample.name);
    expect(lipLayer.maskTextureId).toBe('lip-drawn-style-atlas-v1');
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
      expect(lipLayer.specular).toBeGreaterThan(0.9);
      expect(lipLayer.glossBoost).toBe(1);
      expect(lipLayer.passCount).toBe(2);
    }
    if (textureSample.name === 'matte_lip') {
      expect(lipLayer.preserveDetail).toBe(true);
      expect(lipLayer.specular).toBe(0);
      expect(lipLayer.passCount).toBe(1);
    }
    if (textureSample.name === 'gradient_lip') {
      expect(lipLayer.gradientAmount).toBeGreaterThan(0.8);
      expect(lipLayer.passCount).toBe(1);
    }
    expect(cheekLayer.texture).toBe('soft_blush');
    expect(cheekLayer.maskTextureId).toBe('cheek-drawn-mask-v1');
    expect(cheekLayer.enabled).toBe(false);
    expect(eyeLayer.texture).toBe('shimmer_eye');
    expect(eyeLayer.maskTextureId).toBe('eye-drawn-mask-v1');
    expect(eyeLayer.enabled).toBe(false);
  });
});

test('passes selected lip color, finish, and intensity through payload', () => {
  const selectedColor = RECIPE_COLOR_OPTIONS.find(
    colorOption => colorOption.name === 'berry',
  )!;
  const selectedTextureSample = LIP_TEXTURE_STYLE_OPTIONS.find(
    textureOption => textureOption.name === 'gloss_lip',
  )!;
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

  expect(payload.texture).toBe('gloss_lip');
  expect(payload.textureAmount).toBe(0.85);
  expect(lipLayer.color).toBe('#A8325F');
  expect(lipLayer.texture).toBe('gloss_lip');
  expect(lipLayer.intensity).toBe(0.85);
  expect(lipLayer.textureAmount).toBe(0.85);
  expect(lipLayer.finish).toBe('gloss');
  expect(lipLayer.blendMode).toBe('multiply');
  expect(lipLayer.passCount).toBe(2);
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

test('allows cheek and eye toggles for placement validation while preserving 3-layer batch', async () => {
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
    },
    'lip',
    DEFAULT_RENDERER_MODE,
    12345,
  );

  expect(payload.layers).toHaveLength(3);
  expect(payload.layers.find(layer => layer.region === 'lip')!.enabled).toBe(
    true,
  );
  expect(payload.layers.find(layer => layer.region === 'cheek')!.enabled).toBe(
    true,
  );
  expect(payload.layers.find(layer => layer.region === 'eye')!.enabled).toBe(
    true,
  );
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
