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
  const Image = createComponent('Image');

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
    Image,
    LayoutChangeEvent: {},
    LogBox: { ignoreAllLogs: jest.fn() },
    NativeModules: {},
    PanResponder: {
      create: jest.fn(() => ({ panHandlers: {} })),
    },
    Pressable,
    ScrollView,
    StatusBar: jest.fn(() => null),
    StyleSheet: {
      create: (styles: object) => styles,
      absoluteFillObject: {
        position: 'absolute',
        top: 0,
        right: 0,
        bottom: 0,
        left: 0,
      },
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

function enterGenerateWizard(renderer: ReactTestRenderer.ReactTestRenderer) {
  pressByText(renderer, '시작');
}

function emitUnityReferenceCapture(
  renderer: ReactTestRenderer.ReactTestRenderer,
  capturePairId: string,
) {
  const unityView = renderer.root.findByProps({ testID: 'unity-view' });

  ReactTestRenderer.act(() => {
    unityView.props.onUnityMessage({
      nativeEvent: {
        message: JSON.stringify({
          type: 'e7_reference_capture',
          status: 'exported',
          capturePairId,
          relativeDirectory: `Documents/e7-reference-atlas/capture_pairs/${capturePairId}`,
          detail: 'pending_projected_mesh_overlay_review',
          meshVertexCount: 1220,
          meshIndexCount: 6912,
          meshUvCount: 1220,
          frameWidth: 1179,
        }),
      },
    });
  });
}

function emitUnityFaceTracking(renderer: ReactTestRenderer.ReactTestRenderer) {
  const unityView = renderer.root.findByProps({ testID: 'unity-view' });

  ReactTestRenderer.act(() => {
    unityView.props.onUnityMessage({
      nativeEvent: {
        message: JSON.stringify({
          type: 'face_lifecycle',
          status: 'tracking',
          tracked: true,
          faceDetected: true,
          faceCount: 1,
          trackingState: 'Tracking',
        }),
      },
    });
  });
}

test('renders personalized Generate home instead of old validation entry', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });

  const text = collectText(renderer!);

  expect(text).toContain('맞춤 Generate');
  expect(text).toContain('로컬 생성 준비');
  expect(text).not.toContain('Makeup AR Validation');
  expect(text).not.toContain('Start AR');
});

test('opens forced wizard as the default app flow', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);

  const text = collectText(renderer!);

  expect(text).toContain('로컬 맞춤 생성');
  expect(text).toContain('얼굴 정렬 시작');
  expect(text).toContain('시작');
  expect(text).toContain('정렬');
  expect(text).toContain('촬영');
  expect(text).not.toContain('Regions');
  expect(text).not.toContain('daily');
  expect(text).not.toContain('Full-face');
});

test('keeps later steps locked until previous gates are reached', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);

  expect(
    renderer!.root.findByProps({ testID: 'e7-wizard-step-blend' }).props
      .disabled,
  ).toBe(true);

  pressByTestID(renderer!, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer!);

  expect(
    renderer!.root.findByProps({ testID: 'e7-wizard-step-capture' }).props
      .disabled,
  ).toBe(true);
  expect(
    renderer!.root.findByProps({ testID: 'e7-wizard-align-next' }).props
      .disabled,
  ).toBe(false);
  expect(
    renderer!.root.findByProps({ testID: 'e7-wizard-step-blend' }).props
      .disabled,
  ).toBe(true);
});

test('posts Unity capture request for a wizard neutral shot', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);
  pressByTestID(renderer!, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer!);
  pressByTestID(renderer!, 'e7-wizard-align-next');
  pressByTestID(renderer!, 'e7-wizard-capture-primary');

  const captureCall = mockUnityPostMessage.mock.calls.find(
    call =>
      call[0] === 'RNBridge' && call[1] === 'CaptureE7ReferenceFrameJson',
  );

  expect(captureCall).toBeTruthy();
  const request = JSON.parse(String(captureCall?.[2]));
  expect(request.captureSetId).toContain('e7-capture-set');
  expect(request.captureShotKind).toBe('neutral');
  expect(request.requestedBy).toBe('rn-personalized-generate-wizard');
});

test('blocks current-frame generation when native module is unavailable', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);
  pressByTestID(renderer!, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer!);
  pressByTestID(renderer!, 'e7-wizard-align-next');
  pressByTestID(renderer!, 'e7-wizard-capture-primary');

  const captureCall = mockUnityPostMessage.mock.calls.find(
    call =>
      call[0] === 'RNBridge' && call[1] === 'CaptureE7ReferenceFrameJson',
  );
  const request = JSON.parse(String(captureCall?.[2]));
  emitUnityReferenceCapture(renderer!, request.capturePairId);

  for (let index = 1; index < 6; index += 1) {
    const captureCallForShot = mockUnityPostMessage.mock.calls
      .filter(
        call =>
          call[0] === 'RNBridge' && call[1] === 'CaptureE7ReferenceFrameJson',
      )
      .at(-1);
    const previousRequest = JSON.parse(String(captureCallForShot?.[2]));
    emitUnityReferenceCapture(renderer!, previousRequest.capturePairId);
    pressByTestID(renderer!, 'e7-wizard-capture-primary');
  }
  const finalCaptureCall = mockUnityPostMessage.mock.calls
    .filter(
      call =>
        call[0] === 'RNBridge' && call[1] === 'CaptureE7ReferenceFrameJson',
    )
    .at(-1);
  const finalRequest = JSON.parse(String(finalCaptureCall?.[2]));
  emitUnityReferenceCapture(renderer!, finalRequest.capturePairId);
  pressByTestID(renderer!, 'e7-wizard-capture-primary');
  await ReactTestRenderer.act(async () => {
    renderer!.root
      .findByProps({ testID: 'e7-wizard-generate-candidates' })
      .props.onPress();
  });

  const text = collectText(renderer!);

  expect(text).toContain('native_boundary_module_unavailable');
  expect(text).toContain('기본 블렌딩');
  expect(text).not.toContain('MediaPipe · blocked');
});
