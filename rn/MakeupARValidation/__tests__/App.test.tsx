/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';

jest.setTimeout(15000);

const mockUnityPostMessage = jest.fn();
const mockE7NativeLipBoundaryProviders: {
  extractLipBoundary?: jest.Mock;
  saveGeneratedPackage?: jest.Mock;
  renderLipMaskPreview?: jest.Mock;
} = {};
const mockNativeModules: Record<string, any> = {
  E7NativeLipBoundaryProviders: mockE7NativeLipBoundaryProviders,
};

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
    NativeModules: mockNativeModules,
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

let App: React.ComponentType;
let consoleLogSpy: jest.SpyInstance;
let consoleErrorSpy: jest.SpyInstance;

beforeAll(() => {
  // Load after React Native mocks are registered so App captures mocked modules.
  App = require('../App').default;
});

beforeEach(() => {
  (globalThis as any).IS_REACT_ACT_ENVIRONMENT = true;
  mockUnityPostMessage.mockClear();
  mockE7NativeLipBoundaryProviders.extractLipBoundary = undefined;
  mockE7NativeLipBoundaryProviders.saveGeneratedPackage = undefined;
  mockE7NativeLipBoundaryProviders.renderLipMaskPreview = undefined;
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

function enterGenerateWizard(renderer: ReactTestRenderer.ReactTestRenderer) {
  pressByText(renderer, '시작');
}

function emitUnityReferenceCapture(
  renderer: ReactTestRenderer.ReactTestRenderer,
  capturePairId: string,
  patch: Record<string, unknown> = {},
) {
  const unityView = renderer.root.findByProps({ testID: 'unity-view' });

  ReactTestRenderer.act(() => {
    unityView.props.onUnityMessage({
      nativeEvent: {
        message: JSON.stringify({
          type: 'e7_reference_capture',
          status: 'exported',
          capturePairId,
          captureSetId: patch.captureSetId,
          captureShotKind: patch.captureShotKind,
          relativeDirectory: `Documents/e7-reference-atlas/capture_pairs/${capturePairId}`,
          framePreviewUri: `file:///tmp/${capturePairId}-frame.png`,
          detail: 'pending_projected_mesh_overlay_review',
          meshVertexCount: 1220,
          meshIndexCount: 6912,
          meshUvCount: 1220,
          frameWidth: 1179,
          ...patch,
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

function getUnityPostMessageCalls(method: string) {
  return mockUnityPostMessage.mock.calls.filter(
    call => call[0] === 'RNBridge' && call[1] === method,
  );
}

function getLastUnityPostPayload(method: string) {
  const call = getUnityPostMessageCalls(method).at(-1);
  expect(call).toBeTruthy();
  return JSON.parse(String(call?.[2]));
}

function captureNextWizardShot(renderer: ReactTestRenderer.ReactTestRenderer) {
  pressByTestID(renderer, 'e7-wizard-capture-primary');
  const request = getLastUnityPostPayload('CaptureE7ReferenceFrameJson');
  emitUnityReferenceCapture(renderer, request.capturePairId, {
    captureSetId: request.captureSetId,
    captureShotKind: request.captureShotKind,
  });
  return request;
}

function captureAllWizardShots(renderer: ReactTestRenderer.ReactTestRenderer) {
  return [captureNextWizardShot(renderer)];
}

function emitGeneratedLipMaskApplied(
  renderer: ReactTestRenderer.ReactTestRenderer,
  overrides: Record<string, unknown> = {},
) {
  const unityView = renderer.root.findByProps({ testID: 'unity-view' });

  ReactTestRenderer.act(() => {
    unityView.props.onUnityMessage({
      nativeEvent: {
        message: JSON.stringify({
          type: 'generated_lip_mask_applied',
          status: 'partial',
          generatedMaskId: 'generated-id-pending',
          provider: 'vision',
          expressionMode: 'uvOnly',
          applied: true,
          uvAvailable: true,
          maskTriangles: 12,
          ...overrides,
        }),
      },
    });
  });
}

function makeNativeBoundaryResponse(
  provider: 'vision' | 'mediapipe',
  patch: Partial<ReturnType<typeof makeBaseNativeBoundaryResponse>> = {},
) {
  return {
    ...makeBaseNativeBoundaryResponse(provider),
    ...patch,
  };
}

function makeBaseNativeBoundaryResponse(provider: 'vision' | 'mediapipe') {
  return {
    status: 'ready',
    provider,
    captureSetId: 'e7-capture-set-test',
    capturePairId: 'pair_face_test_0001',
    captureShotKind: 'neutral',
    framePath: 'Documents/e7-reference-atlas/capture_pairs/pair/frame.png',
    framePreviewUri: 'file:///tmp/e7-frame-preview.png',
    arFaceExportPath:
      'Documents/e7-reference-atlas/capture_pairs/pair/arface_export.json',
    fullFaceLandmarksPath:
      'Documents/e7-reference-atlas/capture_pairs/pair/provider_landmarks.json',
    frameWidth: 200,
    frameHeight: 200,
    boundary: {
      coordinateSpace: 'frame_image_pixel_top_left',
      source: provider,
      generationMethod: `${provider}_current_frame_test`,
      outerPoints: [
        { x: 72, y: 106 },
        { x: 100, y: 92 },
        { x: 128, y: 106 },
        { x: 100, y: 122 },
      ],
      innerPoints: [
        { x: 90, y: 106 },
        { x: 100, y: 102 },
        { x: 110, y: 106 },
        { x: 100, y: 110 },
      ],
    },
    arFaceExport: {
      capturePairId: 'pair_face_test_0001',
      screenVertices: [
        [0, 0, 1],
        [200, 0, 1],
        [0, 200, 1],
        [200, 200, 1],
      ],
      uvs: [
        [0, 1],
        [1, 1],
        [0, 0],
        [1, 0],
      ],
      indices: [0, 1, 2, 1, 3, 2],
      display: {
        videoFrameSize: [200, 200],
        orientation: 'portrait',
        isMirrored: true,
      },
    },
    blendShapes: {
      available: true,
      keySignals: {
        mouthSmileLeft: 0.12,
        mouthPucker: 0.03,
      },
    },
    warnings: ['test_current_frame_native_provider'],
  };
}

function installNativeGenerateSuccessMock(
  provider: 'vision' | 'mediapipe' = 'vision',
) {
  mockE7NativeLipBoundaryProviders.extractLipBoundary = jest.fn(
    async requestJson => {
      const request = JSON.parse(String(requestJson));
      const shotKind = String(request.captureShotKind ?? 'neutral');
      const shotSignalScale =
        shotKind === 'pucker'
          ? 0.42
          : shotKind === 'smile'
          ? 0.31
          : shotKind === 'mouthOpen'
          ? 0.24
          : 0.12;
      const response = makeNativeBoundaryResponse(provider, {
        captureSetId: request.captureSetId,
        capturePairId: request.capturePairId,
        captureShotKind: request.captureShotKind,
        framePath: request.framePath,
        arFaceExportPath: request.arFaceExportPath,
        blendShapes: {
          available: true,
          keySignals: {
            mouthSmileLeft: shotSignalScale,
            mouthPucker: shotKind === 'pucker' ? 0.58 : 0.03,
          },
        },
      });
      const scaleX =
        shotKind === 'smile' ? 1.16 : shotKind === 'pucker' ? 0.94 : 1;
      const scaleY =
        shotKind === 'mouthOpen' ? 1.18 : shotKind === 'pucker' ? 1.12 : 1;
      const center = { x: 100, y: 108 };
      response.boundary = {
        ...response.boundary,
        outerPoints: response.boundary.outerPoints.map(point => ({
          x: center.x + (point.x - center.x) * scaleX,
          y: center.y + (point.y - center.y) * scaleY,
        })),
        innerPoints: response.boundary.innerPoints.map(point => ({
          x: center.x + (point.x - center.x) * scaleX,
          y: center.y + (point.y - center.y) * scaleY,
        })),
      };
      return JSON.stringify(response);
    },
  );
  mockE7NativeLipBoundaryProviders.renderLipMaskPreview = jest.fn(
    async (packageJson: string) => {
      const generatedPackage = JSON.parse(packageJson);
      return JSON.stringify({
        status: 'ready',
        generatedMaskId: generatedPackage.generatedMaskId,
        previewUri: `file:///tmp/${generatedPackage.generatedMaskId}.preview.png`,
        previewPath: `/tmp/${generatedPackage.generatedMaskId}.preview.png`,
      });
    },
  );
  mockE7NativeLipBoundaryProviders.saveGeneratedPackage = jest.fn(
    async (packageJson: string) => {
      const generatedPackage = JSON.parse(packageJson);
      return JSON.stringify({
        status: 'saved_local_only',
        generatedMaskId: generatedPackage.generatedMaskId,
        packagePath: `Documents/e7-generated-lip-packages/${generatedPackage.generatedMaskId}/generated_lip_package.json`,
      });
    },
  );
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
  expect(
    getLastUnityPostPayload('SetE7RegionOverlayVisibleJson'),
  ).toMatchObject({
    visible: false,
  });
});

test('initial recipe post keeps lip disabled until the user applies a mask', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);

  ReactTestRenderer.act(() => {
    jest.advanceTimersByTime(1000);
  });

  const recipePayload = getLastUnityPostPayload('ApplyRecipeJson');
  expect(recipePayload.activeRegions).toBe('none');
  expect(recipePayload.enabledLayerCount).toBe(0);
  expect(
    recipePayload.layers.find(
      (layer: { region: string }) => layer.region === 'lip',
    )?.enabled,
  ).toBe(false);
  expect(
    getLastUnityPostPayload('SetE7RegionOverlayVisibleJson'),
  ).toMatchObject({
    visible: false,
  });
  expect(renderer).toBeTruthy();
});

test('keeps later steps locked until previous gates are reached', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);

  expect(
    renderer!.root.findByProps({ testID: 'e7-wizard-step-adjust' }).props
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
    renderer!.root.findByProps({ testID: 'e7-wizard-step-adjust' }).props
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
    call => call[0] === 'RNBridge' && call[1] === 'CaptureE7ReferenceFrameJson',
  );

  expect(captureCall).toBeTruthy();
  const request = JSON.parse(String(captureCall?.[2]));
  expect(request.captureSetId).toContain('e7-capture-set');
  expect(request.captureShotKind).toBe('neutral');
  expect(request.requestedBy).toBe('rn-personalized-generate-wizard');
});

test('unblocks capture when Unity capture response is missing', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);
  pressByTestID(renderer!, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer!);
  pressByTestID(renderer!, 'e7-wizard-align-next');
  pressByTestID(renderer!, 'e7-wizard-capture-primary');

  expect(collectText(renderer!)).toContain('촬영 중');

  ReactTestRenderer.act(() => {
    jest.advanceTimersByTime(7_000);
  });

  const text = collectText(renderer!);
  expect(text).toContain('촬영 응답이 늦습니다');
  expect(text).toContain('다시 촬영');
  expect(text).toContain('정면 사진 촬영');
});

test('ignores late capture ack from an older capture request', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);
  pressByTestID(renderer!, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer!);
  pressByTestID(renderer!, 'e7-wizard-align-next');

  pressByTestID(renderer!, 'e7-wizard-capture-primary');
  const firstRequest = getLastUnityPostPayload('CaptureE7ReferenceFrameJson');

  ReactTestRenderer.act(() => {
    jest.advanceTimersByTime(7_000);
  });

  pressByTestID(renderer!, 'e7-wizard-capture-primary');
  const secondRequest = getLastUnityPostPayload('CaptureE7ReferenceFrameJson');

  emitUnityReferenceCapture(renderer!, firstRequest.capturePairId, {
    captureSetId: firstRequest.captureSetId,
    captureShotKind: firstRequest.captureShotKind,
  });

  let text = collectText(renderer!);
  expect(text).toContain('촬영 중');
  expect(text).not.toContain('캡처 프레임 검토');
  expect(
    renderer!.root.findAll(
      node =>
        node.props.source?.uri ===
        `file:///tmp/${firstRequest.capturePairId}-frame.png`,
    ),
  ).toHaveLength(0);

  emitUnityReferenceCapture(renderer!, secondRequest.capturePairId, {
    captureSetId: secondRequest.captureSetId,
    captureShotKind: secondRequest.captureShotKind,
  });

  text = collectText(renderer!);
  expect(text).toMatch(/1\s*\/\s*1\s*장\s*완료/);
  expect(text).toContain('정면 사진');
  expect(text).toContain('사진이 저장되었습니다');
  expect(text).toContain('저장됨');
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
    call => call[0] === 'RNBridge' && call[1] === 'CaptureE7ReferenceFrameJson',
  );
  const request = JSON.parse(String(captureCall?.[2]));
  emitUnityReferenceCapture(renderer!, request.capturePairId, {
    captureSetId: request.captureSetId,
    captureShotKind: request.captureShotKind,
  });

  pressByTestID(renderer!, 'e7-wizard-capture-primary');
  await ReactTestRenderer.act(async () => {
    renderer!.root
      .findByProps({ testID: 'e7-wizard-generate-candidates' })
      .props.onPress();
  });

  const text = collectText(renderer!);

  expect(text).toContain('후보 생성이 막혔습니다');
  expect(text).toContain('미리보기를 만들 수 없습니다');
  expect(text).toContain('기본 마스크');
  expect(text).not.toContain('native_boundary_module_unavailable');
  expect(text).not.toContain('provider blockedReason');
  expect(text).not.toContain('MediaPipe · blocked');
});

test('uses one capture CTA and switches to captured-frame review after required shots', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterGenerateWizard(renderer!);
  pressByTestID(renderer!, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer!);
  pressByTestID(renderer!, 'e7-wizard-align-next');

  expect(
    renderer!.root.findByProps({ testID: 'e7-wizard-capture-primary' }),
  ).toBeTruthy();
  expect(
    renderer!.root.findAll(
      node =>
        typeof node.props.testID === 'string' &&
        node.props.testID.startsWith('e7-capture-shot-') &&
        typeof node.props.onPress === 'function',
    ),
  ).toHaveLength(0);

  const requests = captureAllWizardShots(renderer!);
  const text = collectText(renderer!);

  expect(requests.map(request => request.captureShotKind)).toEqual(['neutral']);
  expect(text).toMatch(/1\s*\/\s*1\s*장\s*완료/);
  expect(text).toContain('캡처 프레임 검토');
  expect(text).toContain('저장된 얼굴 프레임');
  expect(text).toContain('사진이 저장되었습니다');
  expect(text).not.toContain('살짝 벌림');
  expect(text).not.toContain('오른쪽 각도');
  expect(
    renderer!.root.findAll(
      node =>
        node.props.source?.uri ===
        `file:///tmp/${requests[0].capturePairId}-frame.png`,
    ),
  ).not.toHaveLength(0);
  expect(text).not.toContain('frame.png');
  expect(text).not.toContain('arface_export.json');
});

test('generates one default mask and opens the fixed-photo adjustment editor', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });

  enterGenerateWizard(renderer!);
  pressByTestID(renderer!, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer!);
  pressByTestID(renderer!, 'e7-wizard-align-next');
  captureAllWizardShots(renderer!);
  pressByTestID(renderer!, 'e7-wizard-capture-primary');
  await pressByTestIDAsync(renderer!, 'e7-wizard-generate-candidates');

  const text = collectText(renderer!);

  expect(text).toContain('마스크 미세 조정');
  expect(text).toContain('기본 마스크');
  expect(text).toContain('입술 확대 미리보기');
  expect(text).toContain('마스크');
  expect(text).toContain('경계');
  expect(text).toContain('비교');
  expect(text).not.toContain('블렌딩 선택');
  expect(text).not.toContain('표정 보조');
  expect(
    mockE7NativeLipBoundaryProviders.renderLipMaskPreview,
  ).toHaveBeenCalledTimes(1);

  expect(
    mockE7NativeLipBoundaryProviders.extractLipBoundary,
  ).toHaveBeenCalledTimes(1);
  const requestedShotKinds =
    mockE7NativeLipBoundaryProviders.extractLipBoundary?.mock.calls.map(
      call => JSON.parse(String(call[0])).captureShotKind,
    );
  expect(requestedShotKinds).toEqual(['neutral']);

  const previewPackages =
    mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.map(
      call => JSON.parse(String(call[0])),
    ) ?? [];
  expect(previewPackages).toHaveLength(1);
  expect(previewPackages[0].expressionMode).toBe('uvOnly');
  expect(Object.keys(previewPackages[0].captureSetShotResults)).toEqual([
    'neutral',
  ]);
});

async function advanceToGeneratedAdjustStep(
  renderer: ReactTestRenderer.ReactTestRenderer,
) {
  enterGenerateWizard(renderer);
  pressByTestID(renderer, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer);
  pressByTestID(renderer, 'e7-wizard-align-next');
  captureAllWizardShots(renderer);
  pressByTestID(renderer, 'e7-wizard-capture-primary');
  await pressByTestIDAsync(renderer, 'e7-wizard-generate-candidates');
}

async function flushAdjustmentPreviewDebounce() {
  await ReactTestRenderer.act(async () => {
    jest.advanceTimersByTime(200);
    await Promise.resolve();
  });
}

test('renders full-face mask preview and applies only after matching Unity ack', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);

  expect(collectText(renderer!)).toContain('입술 확대 미리보기');
  pressByTestID(renderer!, 'e7-adjust-preview-toggle-zoom');
  expect(collectText(renderer!)).toContain('전체 얼굴 기준 마스크 미리보기');
  pressByTestID(renderer!, 'e7-adjust-preview-mode-boundary');
  expect(collectText(renderer!)).toContain('경계 보기');
  pressByTestID(renderer!, 'e7-adjust-preview-mode-compare');
  expect(collectText(renderer!)).toContain('원본 비교');
  expect(
    renderer!.root.findAll(
      node => node.props.source?.uri === 'file:///tmp/e7-frame-preview.png',
    ),
  ).not.toHaveLength(0);
  pressByTestID(renderer!, 'e7-adjust-preview-mode-mask');
  expect(collectText(renderer!)).toContain('마스크');

  await pressByTestIDAsync(renderer!, 'e7-wizard-save-and-run');
  const applyPayload = getLastUnityPostPayload('ApplyGeneratedLipMaskJson');
  expect(applyPayload.generatedMaskId).toContain('e7-generated-lip');
  expect(
    getLastUnityPostPayload('SetE7RegionOverlayVisibleJson'),
  ).toMatchObject({
    visible: true,
  });
  expect(collectText(renderer!)).toContain('AR 화면에서 적용 여부');
  expect(collectText(renderer!)).toContain(
    'AR 화면에서 적용 확인을 기다립니다',
  );
  expect(collectText(renderer!)).not.toContain('ApplyGeneratedLipMaskJson');
  expect(collectText(renderer!)).not.toContain('reason:');
  expect(collectText(renderer!)).not.toContain('AR 립 적용 중');
  expect(collectText(renderer!)).not.toContain(
    'Unity generated_lip_mask_applied ack',
  );
  expect(collectText(renderer!)).not.toContain('actual mask preview');
  expect(collectText(renderer!)).not.toContain('provider blockedReason');

  emitGeneratedLipMaskApplied(renderer!, {
    generatedMaskId: applyPayload.generatedMaskId,
  });

  const text = collectText(renderer!);
  expect(text).toContain('AR 립 검증');
  expect(text).toContain('AR 립 적용됨');
  expect(text).toContain('AR 화면입니다');
  expect(text).toContain('마스크 ON');
  expect(text).toContain('진하게 보기');
  expect(text).toContain('경계 보기');
  expect(text).toContain('농도');
  expect(text).not.toContain('저장하고 AR 실행');
  expect(text).not.toContain('Unity ack');
  expect(text).not.toContain('triangles=');
});

test('shows apply progress immediately while generated package save is still pending', async () => {
  installNativeGenerateSuccessMock('vision');
  let resolveSave: ((value: string | PromiseLike<string>) => void) | undefined;
  let pendingRecordJson = '';
  mockE7NativeLipBoundaryProviders.saveGeneratedPackage = jest.fn(
    (packageJson: string) =>
      new Promise<string>(resolve => {
        const generatedPackage = JSON.parse(packageJson);
        resolveSave = resolve;
        pendingRecordJson = JSON.stringify({
          status: 'saved_local_only',
          generatedMaskId: generatedPackage.generatedMaskId,
          packagePath: `Documents/e7-generated-lip-packages/${generatedPackage.generatedMaskId}/generated_lip_package.json`,
        });
      }),
  );
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);

  pressByTestID(renderer!, 'e7-wizard-save-and-run');

  expect(collectText(renderer!)).toContain('마스크를 기기에 저장하는 중입니다');
  expect(collectText(renderer!)).toContain('진행');
  expect(getUnityPostMessageCalls('ApplyGeneratedLipMaskJson')).toHaveLength(0);

  await ReactTestRenderer.act(async () => {
    resolveSave?.(pendingRecordJson);
    await Promise.resolve();
  });

  expect(getUnityPostMessageCalls('ApplyGeneratedLipMaskJson')).toHaveLength(1);
  expect(collectText(renderer!)).toContain('AR 화면에서 적용 확인');
});

test('ignores a late native save result after retaking capture', async () => {
  installNativeGenerateSuccessMock('vision');
  let resolveSave: ((value: string | PromiseLike<string>) => void) | undefined;
  let lateRecordJson = '';
  mockE7NativeLipBoundaryProviders.saveGeneratedPackage = jest.fn(
    (packageJson: string) =>
      new Promise<string>(resolve => {
        const generatedPackage = JSON.parse(packageJson);
        lateRecordJson = JSON.stringify({
          status: 'saved_local_only',
          generatedMaskId: generatedPackage.generatedMaskId,
          packagePath: `Documents/e7-generated-lip-packages/${generatedPackage.generatedMaskId}/generated_lip_package.json`,
        });
        resolveSave = resolve;
      }),
  );
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);

  pressByTestID(renderer!, 'e7-wizard-save-and-run');
  pressByTestID(renderer!, 'e7-wizard-back');
  pressByTestID(renderer!, 'e7-wizard-retake-after-adjust');

  await ReactTestRenderer.act(async () => {
    resolveSave?.(lateRecordJson);
    await Promise.resolve();
  });

  expect(getUnityPostMessageCalls('ApplyGeneratedLipMaskJson')).toHaveLength(0);
  expect(collectText(renderer!)).toContain('다시 촬영합니다');
  expect(collectText(renderer!)).not.toContain('AR 립 적용됨');
});

test('updates generated package after adjustment without a regenerate step', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);

  const renderCallsBeforeAdjustment =
    mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.length ??
    0;
  const recipePostsBeforeAdjustment =
    getUnityPostMessageCalls('ApplyRecipeJson').length;
  const beforeAdjustmentPackage = JSON.parse(
    String(
      mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.at(
        -1,
      )?.[0],
    ),
  );
  expect(beforeAdjustmentPackage.generatedMaskId).toContain(
    'adj-p0-p0-p0-p0-p0-p0',
  );
  expect(collectText(renderer!)).not.toContain('현재 사진으로 다시 생성');
  expect(collectText(renderer!)).toContain('다시 촬영');
  expect(collectText(renderer!)).not.toContain('경계 다시 추출');

  pressByTestID(renderer!, 'lip-adjustment-step-cornerReach-up');

  expect(collectText(renderer!)).toContain('0.05');
  expect(collectText(renderer!)).toContain('조정값을 저장 후보에 바로 반영');
  expect(collectText(renderer!)).toContain('미리보기 갱신 중');
  expect(
    renderer!.root.findByProps({ testID: 'e7-wizard-save-and-run' }).props
      .disabled,
  ).toBe(false);

  await flushAdjustmentPreviewDebounce();

  expect(
    mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.length,
  ).toBeGreaterThan(renderCallsBeforeAdjustment);
  const afterAdjustmentPackage = JSON.parse(
    String(
      mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.at(
        -1,
      )?.[0],
    ),
  );
  expect(afterAdjustmentPackage.generatedMaskId).toContain(
    'adj-p1e-p0-p0-p0-p0-p0',
  );
  expect(afterAdjustmentPackage.generatedMaskId).not.toBe(
    beforeAdjustmentPackage.generatedMaskId,
  );
  expect(afterAdjustmentPackage.adjustment.cornerReach).toBe(0.05);
  expect(getUnityPostMessageCalls('ApplyRecipeJson')).toHaveLength(
    recipePostsBeforeAdjustment,
  );
  expect(collectText(renderer!)).toContain('바로 반영됩니다');

  pressByTestID(renderer!, 'e7-wizard-retake-after-adjust');

  const textAfterRetake = collectText(renderer!);
  expect(textAfterRetake).toContain('다시 촬영합니다');
  expect(textAfterRetake).toContain('사진 촬영');
  expect(textAfterRetake).not.toContain('Unity 적용 실패 또는 미확인');
});

test('persists user-tuned upper inner fill into saved package and AR apply payload', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);

  pressByTestID(renderer!, 'lip-adjust-field-upperInnerFill');
  pressByTestID(renderer!, 'lip-adjustment-step-upperInnerFill-up');
  pressByTestID(renderer!, 'lip-adjustment-step-upperInnerFill-up');

  expect(collectText(renderer!)).toContain('0.10');
  expect(collectText(renderer!)).toContain('미리보기 갱신 중');

  await flushAdjustmentPreviewDebounce();

  const previewPackage = JSON.parse(
    String(
      mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.at(
        -1,
      )?.[0],
    ),
  );
  expect(previewPackage.adjustment.upperInnerFill).toBe(0.1);
  expect(previewPackage.adjustment.innerFill).toBe(0);
  expect(previewPackage.generatedMaskId).toContain('adj-p0-p0-p0-p0-p0-p2s');

  await pressByTestIDAsync(renderer!, 'e7-wizard-save-and-run');

  const savedPackage = JSON.parse(
    String(
      mockE7NativeLipBoundaryProviders.saveGeneratedPackage?.mock.calls.at(
        -1,
      )?.[0],
    ),
  );
  const applyPayload = getLastUnityPostPayload('ApplyGeneratedLipMaskJson');

  expect(savedPackage.adjustment.upperInnerFill).toBe(0.1);
  expect(savedPackage.runtimeApplyPayload.adjustment.upperInnerFill).toBe(0.1);
  expect(applyPayload.adjustment.upperInnerFill).toBe(0.1);
  expect(applyPayload.adjustment.innerFill).toBe(0);
});

test('close after generated adjustment keeps captured work instead of exiting', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);

  pressByText(renderer!, 'Close');

  const text = collectText(renderer!);
  expect(text).toContain('촬영한 사진은 유지됩니다');
  expect(text).toContain('마스크 미세 조정');
  expect(text).toContain('저장하고 AR 실행');
  expect(text).not.toContain('얼굴 정렬 시작');
});

test('shows a generation loading panel while native extraction is running', async () => {
  installNativeGenerateSuccessMock('vision');
  mockE7NativeLipBoundaryProviders.extractLipBoundary = jest.fn(
    () => new Promise<string>(() => {}),
  );
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });

  enterGenerateWizard(renderer!);
  pressByTestID(renderer!, 'e7-wizard-start-next');
  emitUnityFaceTracking(renderer!);
  pressByTestID(renderer!, 'e7-wizard-align-next');
  captureAllWizardShots(renderer!);
  pressByTestID(renderer!, 'e7-wizard-capture-primary');
  pressByTestID(renderer!, 'e7-wizard-generate-candidates');

  const text = collectText(renderer!);
  expect(text).toContain('마스크 생성 중');
  expect(text).toContain('입술 경계를 찾고 미리보기를 준비하고 있습니다');
});

test('accumulates rapid generated adjustment taps before slow preview rebuild', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);

  const renderCallsBeforeAdjustment =
    mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.length ??
    0;

  pressByTestID(renderer!, 'lip-adjustment-step-cornerReach-up');
  pressByTestID(renderer!, 'lip-adjustment-step-cornerReach-up');
  pressByTestID(renderer!, 'lip-adjustment-step-cornerReach-up');

  expect(collectText(renderer!)).toContain('0.15');
  expect(
    mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.length,
  ).toBe(renderCallsBeforeAdjustment);

  await flushAdjustmentPreviewDebounce();

  const afterAdjustmentPackage = JSON.parse(
    String(
      mockE7NativeLipBoundaryProviders.renderLipMaskPreview?.mock.calls.at(
        -1,
      )?.[0],
    ),
  );
  expect(afterAdjustmentPackage.adjustment.cornerReach).toBe(0.15);
  expect(afterAdjustmentPackage.generatedMaskId).toContain('adj-');
  expect(afterAdjustmentPackage.generatedMaskId).not.toContain(
    'adj-p0-p0-p0-p0-p0-p0',
  );
});

test('shows apply timeout and retries from a user-readable blocked state', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);
  await pressByTestIDAsync(renderer!, 'e7-wizard-save-and-run');

  ReactTestRenderer.act(() => {
    jest.advanceTimersByTime(10_000);
  });

  const text = collectText(renderer!);
  expect(text).toContain('지연');
  expect(text).toContain('AR 적용 응답이 늦습니다');
  expect(text).toContain('다시 시도하거나 촬영부터 다시 진행');
  expect(text).not.toContain('generated_lip_mask_applied_ack_timeout');
  expect(text).not.toContain('timeout');
  expect(text).not.toContain('Debug에서 원인');
  expect(text).toContain('저장/적용 재시도');
  expect(text).toContain('촬영부터 다시');
});

test('keeps AR apply pending and retries when Unity reports transient no-face ack', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);
  await pressByTestIDAsync(renderer!, 'e7-wizard-save-and-run');

  const applyPayload = getLastUnityPostPayload('ApplyGeneratedLipMaskJson');
  const postCountBeforeAck = getUnityPostMessageCalls(
    'ApplyGeneratedLipMaskJson',
  ).length;
  emitGeneratedLipMaskApplied(renderer!, {
    generatedMaskId: applyPayload.generatedMaskId,
    status: 'blocked',
    applied: false,
    faceCount: 0,
    maskTriangles: 0,
    uvAvailable: true,
  });

  let text = collectText(renderer!);
  expect(text).toContain('AR 화면에서 얼굴을 찾는 중입니다');
  expect(text).not.toContain('AR 적용을 확인하지 못했습니다');

  ReactTestRenderer.act(() => {
    jest.advanceTimersByTime(800);
  });

  expect(
    getUnityPostMessageCalls('ApplyGeneratedLipMaskJson').length,
  ).toBeGreaterThan(postCountBeforeAck);

  emitGeneratedLipMaskApplied(renderer!, {
    generatedMaskId: applyPayload.generatedMaskId,
  });

  text = collectText(renderer!);
  expect(text).toContain('AR 립 적용됨');
  expect(text).toContain('AR 화면입니다');
});

test('posts AR validation controls without resending texture after Unity ack', async () => {
  installNativeGenerateSuccessMock('mediapipe');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);
  await pressByTestIDAsync(renderer!, 'e7-wizard-save-and-run');

  const applyPayload = getLastUnityPostPayload('ApplyGeneratedLipMaskJson');
  expect(applyPayload.maskRawRgbaBase64).toBeTruthy();
  emitGeneratedLipMaskApplied(renderer!, {
    generatedMaskId: applyPayload.generatedMaskId,
    provider: 'mediapipe',
  });

  expect(collectText(renderer!)).toContain('AR 립 적용됨');
  pressByTestID(renderer!, 'generated-mask-toggle');
  pressByTestID(renderer!, 'generated-mask-color-hot');
  pressByTestID(renderer!, 'generated-mask-opacity-minus');

  const controlPayload = getLastUnityPostPayload('ApplyGeneratedLipMaskJson');
  expect(controlPayload.generatedMaskId).toBe(applyPayload.generatedMaskId);
  expect(controlPayload.maskVisible).toBe(false);
  expect(controlPayload.visible).toBe(false);
  expect(controlPayload.controlRequestId).toBeGreaterThan(0);
  expect(controlPayload.validationControlRequestId).toBe(
    controlPayload.controlRequestId,
  );
  expect(controlPayload.controlRevision).toBe(controlPayload.controlRequestId);
  expect(controlPayload.colorHex).toBe('#FF2D8A');
  expect(controlPayload.validationColor).toBe('#FF2D8A');
  expect(controlPayload.opacity).toBeCloseTo(0.76);
  expect(controlPayload.maskRawRgbaBase64).toBeUndefined();
  expect(controlPayload.maskPngBase64).toBeUndefined();
  expect(
    getLastUnityPostPayload('SetE7RegionOverlayVisibleJson'),
  ).toMatchObject({
    visible: false,
  });
  expect(collectText(renderer!)).toContain('AR 검증 변경을 확인하는 중입니다');

  emitGeneratedLipMaskApplied(renderer!, {
    generatedMaskId: applyPayload.generatedMaskId,
    provider: 'mediapipe',
    validationControls: {
      controlRequestId: controlPayload.controlRequestId + 100,
      controlRevision: controlPayload.controlRevision,
      visible: false,
      strongMode: true,
      colorHex: '#FF2D8A',
      opacity: 0.76,
      boundaryDebugVisible: false,
    },
  });

  expect(collectText(renderer!)).toContain('AR 검증 변경을 확인하는 중입니다');
  expect(collectText(renderer!)).not.toContain('AR 검증 변경이 반영되었습니다');

  emitGeneratedLipMaskApplied(renderer!, {
    generatedMaskId: applyPayload.generatedMaskId,
    provider: 'mediapipe',
    controlRequestId: controlPayload.controlRequestId,
    controlRevision: controlPayload.controlRevision,
    validationControls: {
      controlRequestId: controlPayload.controlRequestId,
      controlRevision: controlPayload.controlRevision,
      visible: false,
      strongMode: true,
      colorHex: '#FF2D8A',
      opacity: 0.76,
      boundaryDebugVisible: false,
    },
  });

  expect(collectText(renderer!)).toContain('AR 검증 변경이 반영되었습니다');
});

test('rejects generated-mask ack when generatedMaskId does not match pending package', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);
  await pressByTestIDAsync(renderer!, 'e7-wizard-save-and-run');

  emitGeneratedLipMaskApplied(renderer!, {
    generatedMaskId: 'wrong-generated-mask-id',
  });

  const text = collectText(renderer!);
  expect(text).toContain('이전 마스크 응답이 도착했습니다');
  expect(text).not.toContain('AR 립 적용 중');
  expect(text).not.toContain('Unity 적용 실패 또는 미확인');
});

test('ignores stale generated-mask ack after retaking capture', async () => {
  installNativeGenerateSuccessMock('vision');
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  await advanceToGeneratedAdjustStep(renderer!);
  await pressByTestIDAsync(renderer!, 'e7-wizard-save-and-run');

  const applyPayload = getLastUnityPostPayload('ApplyGeneratedLipMaskJson');
  pressByTestID(renderer!, 'e7-wizard-back');
  pressByTestID(renderer!, 'e7-wizard-retake-after-adjust');

  emitGeneratedLipMaskApplied(renderer!, {
    generatedMaskId: applyPayload.generatedMaskId,
  });

  const text = collectText(renderer!);
  expect(text).toContain('다시 촬영합니다');
  expect(text).not.toContain('AR 립 적용됨');
  expect(text).not.toContain('AR 화면입니다');
  expect(text).not.toContain('이전 마스크 응답이 도착했습니다');
});
