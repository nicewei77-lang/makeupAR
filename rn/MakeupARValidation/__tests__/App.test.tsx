/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import App from '../App';

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

test('renders home with neutral validation copy', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });

  const text = collectText(renderer!);

  expect(text).toContain('Makeup AR Validation');
  expect(text).toContain('Ready to start AR');
  expect(text).not.toContain('Region Precision');
  expect(text).not.toContain('Validation status');
  expect(text).not.toContain('E7.3');
});

test('does not render candidate or variant controls', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  const text = collectText(renderer!);

  expect(text).not.toContain('Candidate');
  expect(text).not.toContain('candidate');
  expect(text).not.toContain('Variant');
  expect(text).not.toContain('variant');
  expect(text).not.toContain('soft-wide');
  expect(text).not.toContain('core');

  pressByText(renderer!, 'Debug');
  const debugText = collectText(renderer!);
  expect(debugText).not.toContain('candidateId');
  expect(debugText).not.toContain('variantId');
});

test('keeps validation modes visually compact before build', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  expect(collectText(renderer!)).toContain('Clean');
  expect(collectText(renderer!)).toContain('HUD');
  expect(collectText(renderer!)).toContain('Debug');
  expect(collectText(renderer!)).toContain('Regions');
  expect(collectText(renderer!)).toContain('AR Status');
  expect(collectText(renderer!)).toContain('active=lip,cheek,eye');
  expect(collectText(renderer!)).not.toContain('E7.03 HUD');

  pressByText(renderer!, 'Clean');
  expect(collectText(renderer!)).toContain('Capture Pair');
  expect(collectText(renderer!)).not.toContain('Regions');
  expect(collectText(renderer!)).not.toContain('E7.03 HUD');

  pressByText(renderer!, 'Debug');
  expect(collectText(renderer!)).toContain('Evidence metadata');
  expect(collectText(renderer!)).toContain('Regions');
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
  expect(recipePostCall).toContain('rendererMode=e7-reference-uv-alpha');
  expect(recipePostCall).not.toContain('candidateId=');
  expect(recipePostCall).not.toContain('variantId=');
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
  expect(latestVisibilityPostCall).toContain('faceDebugSurfaceVisible=false');
  expect(latestVisibilityPostCall).toContain('validationViewMode=full');

  pressByText(renderer!, 'Clean');

  latestVisibilityPostCall = [...consoleLogSpy.mock.calls]
    .reverse()
    .find(call => call.includes('[E7] rn_region_overlay_visibility_post'));

  expect(latestVisibilityPostCall).toBeTruthy();
  expect(latestVisibilityPostCall).toContain('visible=false');
  expect(latestVisibilityPostCall).toContain('faceDebugSurfaceVisible=false');
  expect(latestVisibilityPostCall).toContain('validationViewMode=clean');
});

test('allows all regions to be off before build', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  for (const region of ['lip', 'cheek', 'eye']) {
    ReactTestRenderer.act(() => {
      renderer!.root
        .findByProps({ testID: `region-toggle-${region}` })
        .props.onPress();
    });
  }

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

    expect(getToggle().props.accessibilityState.checked).toBe(true);

    ReactTestRenderer.act(() => {
      getToggle().props.onPress();
    });

    expect(getToggle().props.accessibilityState.checked).toBe(false);

    ReactTestRenderer.act(() => {
      getToggle().props.onPress();
    });

    expect(getToggle().props.accessibilityState.checked).toBe(true);
  },
);
