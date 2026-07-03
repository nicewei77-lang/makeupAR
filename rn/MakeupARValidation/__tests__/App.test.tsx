/**
 * @format
 */

import React from 'react';
import ReactTestRenderer from 'react-test-renderer';
import App, {
  buildValidationRecipeBatchPayload,
  CHEEK_BLUSH_REGION_OPTIONS,
  DEFAULT_REGION_RECIPES,
  DEFAULT_RENDERER_MODE,
  EYEBROW_COLOR_OPTIONS,
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

function expandRecipePanel(renderer: ReactTestRenderer.ReactTestRenderer) {
  if (!collectText(renderer).includes('Show')) {
    return;
  }

  ReactTestRenderer.act(() => {
    renderer.root
      .findByProps({ testID: 'recipe-panel-collapse-toggle' })
      .props.onPress();
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
  expect(hudText).toContain('Controls');
  expect(hudText).toContain('Show');
  expect(hudText).not.toContain('AR Status');
  expect(hudText).toContain('active=none');
  expect(hudText).not.toContain('E7.03 HUD');

  pressByText(renderer!, 'Clean');
  expect(collectText(renderer!)).not.toContain('Controls');
  expect(collectText(renderer!)).not.toContain('E7.03 HUD');

  pressByText(renderer!, 'Debug');
  expect(collectText(renderer!)).toContain('Controls');
  expect(collectText(renderer!)).toContain('Show');

  expandRecipePanel(renderer!);
  expect(collectText(renderer!)).toContain('Evidence metadata');
});

test('shows blush region, style, intensity, and opacity controls in HUD mode', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);
  expandRecipePanel(renderer!);

  const hudText = collectText(renderer!);

  expect(hudText).toContain('rose');
  expect(hudText).toContain('coral');
  expect(hudText).toContain('pale pink');
  expect(hudText).toContain('Blush Region');
  expect(hudText).toContain('Daily');
  expect(hudText).not.toContain('Default 2');
  expect(hudText).toContain('Lovely');
  expect(hudText).toContain('Under');
  expect(hudText).toContain('Sun 1');
  expect(hudText).toContain('Sun 2');
  expect(hudText).toContain('Intensity');
  expect(hudText).toContain('Opacity');
  expect(hudText).toContain('blush_session_1');

  pressByText(renderer!, 'Lovely');

  expect(collectText(renderer!)).toContain('blush_session_2');
  expect(collectText(renderer!)).toContain('active=cheek');

  pressByText(renderer!, 'lip');
  expect(collectText(renderer!)).toContain('Matte');
  expect(collectText(renderer!)).toContain('Glow');
  expect(collectText(renderer!)).toContain('Gradient');

  pressByText(renderer!, 'Glow');

  expect(collectText(renderer!)).toContain('gloss_lip');

  pressByText(renderer!, 'Gradient');

  expect(collectText(renderer!)).toContain('gradient_lip');
});

test('keeps focused cheek recipe summary when later eye ack arrives', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);
  expandRecipePanel(renderer!);

  sendUnityMessage(renderer!, {
    type: 'recipe_applied',
    region: 'cheek',
    layer: 'cheek',
    texture: 'blush_session_2',
    sample: 'blush_session_2',
    textureMode: 'sample',
    blendMode: 'multiply',
    finish: 'powder',
    maskTextureId: 'cheek-session-mask-2-v1',
    maskSoftSampleMode: 'feather_scaled_13tap_near_far',
    maskSource: 'user_session_2d_png_luminance_multiband',
    color: '#D94B74',
    opacity: 0.52,
    intensity: 0.95,
    applied: true,
    faceCount: 1,
    uvAvailable: true,
  });

  sendUnityMessage(renderer!, {
    type: 'recipe_applied',
    region: 'eye',
    layer: 'eye',
    texture: 'shimmer_eye',
    sample: 'shimmer_eye',
    textureMode: 'sample',
    blendMode: 'screen',
    finish: 'shimmer',
    maskTextureId: 'eye-drawn-mask-v1',
    applied: false,
  });

  const text = collectText(renderer!);

  expect(text).toContain('recipe_applied region=cheek texture=blush_session_2');
  expect(text).toContain('maskTex=cheek-session-mask-2-v1');
  expect(text).not.toContain('recipe_applied region=eye texture=shimmer_eye');
});

test('collapses AR makeup control panel to keep face visible', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  expect(collectText(renderer!)).toContain('Show');
  expect(collectText(renderer!)).not.toContain('Blush Region');
  expect(collectText(renderer!)).not.toContain('Daily');

  const collapseToggle = renderer!.root.findByProps({
    testID: 'recipe-panel-collapse-toggle',
  });

  ReactTestRenderer.act(() => {
    collapseToggle.props.onPress();
  });

  expect(collectText(renderer!)).toContain('Hide');
  expect(collectText(renderer!)).toContain('Blush Region');
  expect(collectText(renderer!)).toContain('Daily');
  expect(collectText(renderer!)).toContain('Intensity');
  expect(collectText(renderer!)).toContain('Opacity');

  ReactTestRenderer.act(() => {
    renderer!.root
      .findByProps({ testID: 'recipe-panel-collapse-toggle' })
      .props.onPress();
  });

  expect(collectText(renderer!)).toContain('Show');
  expect(collectText(renderer!)).not.toContain('Blush Region');
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
  expandRecipePanel(renderer!);

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

test('surfaces MediaPipe eyebrow boundary diagnostics from Unity events', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  sendUnityMessage(renderer!, {
    type: 'e7_mediapipe_eyebrow_boundary',
    status: 'ok',
    available: true,
    source: 'mediapipe_face_landmarker_runtime_eyebrow_boundary',
    coordinateMode: 'mediapipe-image-top-left',
    faceCount: 1,
    leftOuterPointCount: 36,
    rightOuterPointCount: 36,
    leftEyePointCount: 16,
    rightEyePointCount: 16,
    hairRefinement: 'pixel_refined_boundary_first',
    leftHairPixels: 421,
    rightHairPixels: 408,
    leftBrowEyeGapPx: 14.2,
    rightBrowEyeGapPx: 13.6,
    faceMotionScore: 0.072,
    faceMotionRisk: 'stable_face_motion',
    rawCameraFrameStored: false,
    offDeviceUpload: false,
  });

  pressByText(renderer!, 'Debug');
  const text = collectText(renderer!);

  expect(text).toContain('e7_mediapipe_eyebrow_boundary');
  expect(text).toContain('status=ok');
  expect(text).toContain(
    'source=mediapipe_face_landmarker_runtime_eyebrow_boundary',
  );
  expect(text).toContain('face=1');
  expect(text).toContain('brow=36/36');
  expect(text).toContain('eye=16/16');
  expect(text).toContain('gap=14.2/13.6');
  expect(text).toContain('hair=421/408');
  expect(text).toContain('refine=pixel_refined_boundary_first');
  expect(text).toContain('privacy raw=false offDevice=false');
});

test('surfaces styled eyebrow H B A S T diagnostics from Unity events', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);

  sendUnityMessage(renderer!, {
    type: 'e7_mediapipe_eyebrow_styled_boundary',
    status: 'ok',
    available: true,
    coordinateMode:
      'mediapipe-image-top-left->screen->face-local-warp->brow-style-1',
    leftOuterPointCount: 144,
    rightOuterPointCount: 144,
    controlPointMode: 'head_body_arch_tailStart_tail_styled',
    headBodySplitProgress: 0.2,
    bodyEndProgress: 0.62,
    archProgress: 0.64,
    tailStartProgress: 0.64,
    tailRootProgress: 0.985,
    tailTaperStartProgress: 0.64,
    leftControls: 'H=(320.1,512.4),B=(250.2,496.3),A=(185.0,492.1),S=(185.0,492.1),T=(84.4,505.1)',
    rightControls: 'H=(520.1,512.4),B=(590.2,496.3),A=(655.0,492.1),S=(655.0,492.1),T=(755.4,505.1)',
    leftShapeMetrics: 'h/w=0.155,px=271.6x42.2,th=H0.70/B0.66/S0.66/A0.66/T0.14',
    rightShapeMetrics: 'h/w=0.177,px=239.1x42.2,th=H0.70/B0.66/S0.66/A0.66/T0.14',
    shapeGateStyle: 1,
    shapeGateStatus: 'pass',
    shapeGateChecks:
      'Lh=pass,Rh=pass,Lt=pass,Rt=pass,sep=pass,sym=pass,target=h0.145-0.225/t0.10-0.36',
    candidateTriangles: 128,
    hitTriangles: 42,
    activePixels: 2401,
    activeCoverage: 0.0092,
    rawCameraFrameStored: false,
    offDeviceUpload: false,
  });

  pressByText(renderer!, 'Debug');
  const text = collectText(renderer!);

  expect(text).toContain('e7_mediapipe_eyebrow_styled_boundary');
  expect(text).toContain('mode=head_body_arch_tailStart_tail_styled');
  expect(text).toContain('split=H:0.20/B:0.62/A:0.64/S:0.64/root:0.98/taper:0.64');
  expect(text).toContain('left=H=(320.1,512.4)');
  expect(text).toContain('S=(185.0,492.1)');
  expect(text).toContain('right=H=(520.1,512.4)');
  expect(text).toContain('shape=L:h/w=0.155');
  expect(text).toContain('/R:h/w=0.177');
  expect(text).toContain('gate=pass/Lh=pass');
  expect(text).toContain('uv=42/128');
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
  expandRecipePanel(renderer!);

  const text = collectText(renderer!);

  expect(text).toContain('texture=matte_lip');
  expect(text).toContain('layers=soft_sdf_logical_multilayer');
  expect(text).toContain('gloss=none');
  expect(text).toContain('finish=matte');
  expect(text).toContain('soft=feather_scaled_13tap_near_far');
  expect(text).toContain('featherPx=3.45/6.38');
  expect(text).not.toContain('matte_base_wet_sheen');
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
  expect(recipePostCall).toContain('activeRegions=none');
  expect(recipePostCall).toContain('enabledLayerCount=0');
  expect(recipePostCall).toContain('focusRegion=cheek');
  expect(recipePostCall).toContain('focusMaskTextureId=cheek-session-mask-1-v1');
  expect(recipePostCall).toContain('lipMaskTextureId=lip-drawn-style-atlas-v1');
  expect(recipePostCall).toContain('cheekMaskTextureId=cheek-session-mask-1-v1');
  expect(recipePostCall).not.toContain('lipMaskTextureId=lip-vision-boundary-v1');
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
      {
        lip: true,
        cheek: false,
        eye: false,
      },
      'lip',
      DEFAULT_RENDERER_MODE,
      12345,
    );
    const lipLayer = payload.layers.find(layer => layer.region === 'lip')!;
    const cheekLayer = payload.layers.find(layer => layer.region === 'cheek')!;
    const eyeLayer = payload.layers.find(layer => layer.region === 'eye')!;

    expect(payload.layers).toHaveLength(3);
    expect(payload.rendererMode).toBe('smooth-region-mask');
    expect(payload.lookId).toBe('cheek_blush_validation_v1');
    expect(payload.activeRegions).toBe('lip');
    expect(payload.enabledLayerCount).toBe(1);
    expect(lipLayer.texture).toBe(textureSample.name);
    expect(lipLayer.maskTextureId).toBe(
      textureSample.name === 'gradient_lip'
        ? 'lip-drawn-gradient-density-atlas-v1'
        : 'lip-drawn-style-atlas-v1',
    );
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
      expect(lipLayer.maskTextureId).toBe(
        'lip-drawn-gradient-density-atlas-v1',
      );
      expect(lipLayer.coverage).toBeGreaterThan(0.9);
      expect(lipLayer.gradientAmount).toBe(1);
      expect(lipLayer.passCount).toBe(1);
    }
    expect(cheekLayer.texture).toBe('blush_session_1');
    expect(cheekLayer.maskTextureId).toBe('cheek-session-mask-1-v1');
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
    {
      lip: true,
      cheek: false,
      eye: false,
    },
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

test('selects exactly one cheek blush region mask per cheek layer', () => {
  const expectedMaskIds: Record<string, string> = {
    blush_session_1: 'cheek-session-mask-1-v1',
    blush_session_2: 'cheek-session-mask-2-v1',
    blush_session_3: 'cheek-session-mask-3-v1',
    blush_session_4: 'cheek-session-mask-4-v1',
    blush_session_5: 'cheek-session-mask-5-v1',
  };

  expect(CHEEK_BLUSH_REGION_OPTIONS.map(option => option.name)).toEqual([
    'blush_session_1',
    'blush_session_2',
    'blush_session_3',
    'blush_session_4',
    'blush_session_5',
  ]);

  CHEEK_BLUSH_REGION_OPTIONS.forEach(regionMaskOption => {
    const payload = buildValidationRecipeBatchPayload(
      {
        ...DEFAULT_REGION_RECIPES,
        cheek: {
          ...DEFAULT_REGION_RECIPES.cheek,
          textureSample: regionMaskOption,
        },
      },
      {
        lip: false,
        cheek: true,
        eye: false,
      },
      'cheek',
      DEFAULT_RENDERER_MODE,
      12345,
    );
    const cheekLayers = payload.layers.filter(layer => layer.region === 'cheek');
    const cheekLayer = cheekLayers[0];

    expect(payload.layers).toHaveLength(3);
    expect(cheekLayers).toHaveLength(1);
    expect(payload.activeRegions).toBe('cheek');
    expect(payload.enabledLayerCount).toBe(1);
    expect(payload.texture).toBe(regionMaskOption.name);
    expect(payload.maskTextureId).toBe(expectedMaskIds[regionMaskOption.name]);
    expect(cheekLayer.texture).toBe(regionMaskOption.name);
    expect(cheekLayer.maskTextureId).toBe(
      expectedMaskIds[regionMaskOption.name],
    );
    expect(cheekLayer.enabled).toBe(true);
    expect(cheekLayer.blendMode).toBe('multiply');
    expect(cheekLayer.finish).toBe('powder');
    expect(cheekLayer.shaderMode).toBe(
      'cheek-blush-multiband-skin-aware-validation',
    );
    expect(cheekLayer.skinAdaptive).toBe(true);
    expect(cheekLayer.intensity).toBeGreaterThanOrEqual(0.72);
    expect(cheekLayer.intensity).toBeLessThanOrEqual(0.88);
    expect(cheekLayer.coverage).toBeGreaterThanOrEqual(0.66);
    expect(cheekLayer.coverage).toBeLessThanOrEqual(0.92);
    expect(cheekLayer.preserveDetail).toBe(true);
  });
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

test('allows lip and eye toggles for placement validation while preserving 3-layer batch', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);
  expandRecipePanel(renderer!);

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

  expect(collectText(renderer!)).toContain('active=none');

  ReactTestRenderer.act(() => {
    renderer!.root.findByProps({ testID: 'region-toggle-eye' }).props.onPress();
  });

  expect(
    renderer!.root.findByProps({ testID: 'region-toggle-eye' }).props
      .accessibilityState.checked,
  ).toBe(true);
  expect(collectText(renderer!)).toContain('active=eye');

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

test('adds eyebrow as optional fourth layer without changing legacy payloads', () => {
  const eyebrowSample = RECIPE_TEXTURE_SAMPLE_OPTIONS.find(
    textureOption => textureOption.name === 'eyebrow_candidate_1',
  )!;
  const eyebrowColor = EYEBROW_COLOR_OPTIONS.find(
    colorOption => colorOption.name === 'dark_brown',
  )!;
  const legacyPayload = buildValidationRecipeBatchPayload(
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
  const eyebrowPayload = buildValidationRecipeBatchPayload(
    {
      ...DEFAULT_REGION_RECIPES,
      eyebrow: {
        ...DEFAULT_REGION_RECIPES.eyebrow,
        color: eyebrowColor,
        textureSample: eyebrowSample,
      },
    },
    {
      lip: false,
      cheek: false,
      eye: false,
      eyebrow: true,
    },
    'eyebrow',
    DEFAULT_RENDERER_MODE,
    12345,
  );
  const eyebrowLayer = eyebrowPayload.layers.find(
    layer => layer.region === 'eyebrow',
  )!;

  expect(legacyPayload.layers).toHaveLength(3);
  expect(legacyPayload.layers.some(layer => layer.region === 'eyebrow')).toBe(
    false,
  );
  expect(eyebrowPayload.layers).toHaveLength(4);
  expect(eyebrowPayload.activeRegions).toBe('eyebrow');
  expect(eyebrowPayload.enabledLayerCount).toBe(1);
  expect(eyebrowPayload.texture).toBe('eyebrow_candidate_1');
  expect(eyebrowPayload.maskTextureId).toBe('eyebrow-hair-atlas-1-v1');
  expect(eyebrowPayload.shaderMode).toBe(
    'eyebrow-boundary-tone-lift-validation',
  );
  expect(eyebrowPayload.passCount).toBe(4);
  expect(eyebrowLayer.enabled).toBe(true);
  expect(eyebrowLayer.color).toBe('#3B2A22');
  expect(eyebrowLayer.maskTextureId).toBe('eyebrow-hair-atlas-1-v1');
  expect(eyebrowLayer.blendMode).toBe('multiply');
  expect(eyebrowLayer.finish).toBe('brow');
  expect(eyebrowLayer.skinAdaptive).toBe(false);
});

test('maps the three eyebrow styles to Unity mask resources', () => {
  const eyebrowSamples = RECIPE_TEXTURE_SAMPLE_OPTIONS.filter(
    textureOption => textureOption.region === 'eyebrow',
  );

  expect(eyebrowSamples.map(sample => sample.name)).toEqual([
    'eyebrow_candidate_1',
    'eyebrow_candidate_2',
    'eyebrow_candidate_3',
  ]);

  eyebrowSamples.forEach((sample, index) => {
    const payload = buildValidationRecipeBatchPayload(
      {
        ...DEFAULT_REGION_RECIPES,
        eyebrow: {
          ...DEFAULT_REGION_RECIPES.eyebrow,
          textureSample: sample,
        },
      },
      {
        lip: false,
        cheek: false,
        eye: false,
        eyebrow: true,
      },
      'eyebrow',
      DEFAULT_RENDERER_MODE,
      12345,
    );

    expect(payload.maskTextureId).toBe(`eyebrow-hair-atlas-${index + 1}-v1`);
  });
});

test('exposes eyebrow wine color option', () => {
  expect(EYEBROW_COLOR_OPTIONS.map(color => color.name)).toEqual([
    'black',
    'dark_brown',
    'brown',
    'light_brown',
    'wine',
  ]);
  expect(
    EYEBROW_COLOR_OPTIONS.find(color => color.name === 'wine')?.color,
  ).toBe('#6A243B');
});

test('toggles lip region alongside default cheek blush', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);
  expandRecipePanel(renderer!);

  const getToggle = () =>
    renderer!.root.findByProps({ testID: 'region-toggle-lip' });

  expect(getToggle().props.accessibilityState.checked).toBe(false);
  expect(collectText(renderer!)).toContain('active=none');

  ReactTestRenderer.act(() => {
    getToggle().props.onPress();
  });

  expect(getToggle().props.accessibilityState.checked).toBe(true);
  expect(collectText(renderer!)).toContain('active=lip');

  ReactTestRenderer.act(() => {
    getToggle().props.onPress();
  });

  expect(getToggle().props.accessibilityState.checked).toBe(false);
  expect(collectText(renderer!)).toContain('active=none');
});

test('keeps existing regions active when focusing eyebrow controls', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);
  expandRecipePanel(renderer!);

  const getLipToggle = () =>
    renderer!.root.findByProps({ testID: 'region-toggle-lip' });
  const getCheekToggle = () =>
    renderer!.root.findByProps({ testID: 'region-toggle-cheek' });
  const getEyebrowToggle = () =>
    renderer!.root.findByProps({ testID: 'region-toggle-eyebrow' });

  ReactTestRenderer.act(() => {
    getLipToggle().props.onPress();
  });
  ReactTestRenderer.act(() => {
    getCheekToggle().props.onPress();
  });
  ReactTestRenderer.act(() => {
    getLipToggle().props.onPress();
  });
  ReactTestRenderer.act(() => {
    getEyebrowToggle().props.onPress();
  });

  expect(getLipToggle().props.accessibilityState.checked).toBe(true);
  expect(getCheekToggle().props.accessibilityState.checked).toBe(true);
  expect(getEyebrowToggle().props.accessibilityState.checked).toBe(true);
  expect(collectText(renderer!)).toContain('active=lip,cheek,eyebrow');

  const latestRecipePostCall = [...consoleLogSpy.mock.calls]
    .reverse()
    .find(call => call.includes('[E7] rn_texture_recipe_batch_post'));

  expect(latestRecipePostCall).toBeTruthy();
  expect(latestRecipePostCall).toContain('activeRegions=lip,cheek,eyebrow');
  expect(latestRecipePostCall).toContain('enabledLayerCount=3');
  expect(latestRecipePostCall).toContain('focusRegion=eyebrow');
  expect(latestRecipePostCall).toContain(
    'eyebrowMaskTextureId=eyebrow-hair-atlas-1-v1',
  );
});

test('does not show stale eye recipe status while eyebrow is focused', async () => {
  let renderer: ReactTestRenderer.ReactTestRenderer | undefined;

  await ReactTestRenderer.act(() => {
    renderer = ReactTestRenderer.create(<App />);
  });
  enterUnityScreen(renderer!);
  expandRecipePanel(renderer!);

  sendUnityMessage(renderer!, {
    type: 'recipe_applied',
    region: 'eye',
    layer: 'eye',
    texture: 'shimmer_eye',
    sample: 'shimmer_eye',
    textureMode: 'sample',
    blendMode: 'screen',
    finish: 'shimmer',
    maskTextureId: 'eye-drawn-mask-v1',
    applied: false,
  });

  ReactTestRenderer.act(() => {
    renderer!.root
      .findByProps({ testID: 'region-toggle-eyebrow' })
      .props.onPress();
  });

  const text = collectText(renderer!);

  expect(text).toContain('active=eyebrow');
  expect(text).toContain('recipe_applied waiting');
  expect(text).not.toContain('recipe_applied region=eye texture=shimmer_eye');
});
