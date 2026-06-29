#!/usr/bin/env node

const fs = require('fs');
const path = require('path');

const root = path.resolve(__dirname, '..');
const iosRoot = path.join(root, 'ios');
const checks = [];

function read(relativePath) {
  return fs.readFileSync(path.join(root, relativePath), 'utf8');
}

function assertCheck(name, condition, detail) {
  checks.push({ name, ok: Boolean(condition), detail });
}

const podfile = read('ios/Podfile');
const podfileLock = read('ios/Podfile.lock');
const project = read('ios/MakeupARValidation.xcodeproj/project.pbxproj');
const providerSwift = read('ios/MakeupARValidation/E7NativeLipBoundaryProviders.swift');
const providerBridge = read('ios/MakeupARValidation/E7NativeLipBoundaryProvidersBridge.m');
const modelPath = path.join(
  iosRoot,
  'MakeupARValidation',
  'E7Models',
  'face_landmarker.task',
);
const modelStats = fs.existsSync(modelPath) ? fs.statSync(modelPath) : null;

assertCheck(
  'MediaPipeTasksVision pod declared',
  /pod ['"]MediaPipeTasksVision['"], ['"]0\.10\.35['"]/.test(podfile),
  'ios/Podfile should pin MediaPipeTasksVision 0.10.35',
);
assertCheck(
  'MediaPipeTasksVision pod installed',
  /MediaPipeTasksVision \(0\.10\.35\)/.test(podfileLock),
  'ios/Podfile.lock should contain MediaPipeTasksVision 0.10.35',
);
assertCheck(
  'face_landmarker.task exists',
  modelStats && modelStats.size > 1_000_000,
  `model size=${modelStats?.size ?? 0}`,
);
assertCheck(
  'face_landmarker.task in Xcode resources',
  /face_landmarker\.task in Resources/.test(project),
  'project.pbxproj must copy model into app bundle',
);
assertCheck(
  'native provider Swift in Xcode sources',
  /E7NativeLipBoundaryProviders\.swift in Sources/.test(project),
  'project.pbxproj must compile native provider Swift',
);
assertCheck(
  'native provider bridge in Xcode sources',
  /E7NativeLipBoundaryProvidersBridge\.m in Sources/.test(project),
  'project.pbxproj must compile React Native bridge',
);
assertCheck(
  'Swift imports Vision',
  /import Vision/.test(providerSwift),
  'Vision current-frame provider must remain available',
);
assertCheck(
  'Swift imports MediaPipe conditionally',
  /#if canImport\(MediaPipeTasksVision\)[\s\S]*import MediaPipeTasksVision/.test(
    providerSwift,
  ),
  'MediaPipe provider should compile only when pod is present',
);
assertCheck(
  'Swift resolves bundled MediaPipe model',
  /Bundle\.main\.(?:url|path)\(\s*forResource: "face_landmarker",\s*(?:withExtension|ofType): "task"/.test(
    providerSwift,
  ),
  'MediaPipe path must use bundled face_landmarker.task',
);
assertCheck(
  'Swift exposes current-frame extraction',
  /@objc\(extractLipBoundary:resolver:rejecter:\)/.test(providerSwift) &&
    /extractVisionFaceLandmarks/.test(providerSwift) &&
    /extractMediaPipeBoundary/.test(providerSwift),
  'React Native bridge must reach Vision and MediaPipe providers',
);
assertCheck(
  'Swift exposes local package save',
  /@objc\(saveGeneratedPackage:resolver:rejecter:\)/.test(providerSwift),
  'Generated package must be saved locally before Unity apply',
);
assertCheck(
  'Swift exposes actual package preview render',
  /@objc\(renderLipMaskPreview:resolver:rejecter:\)/.test(providerSwift) &&
    /renderRawUvMaskProjection/.test(providerSwift) &&
    /maskRawRgbaBase64/.test(providerSwift) &&
    /raw_uv_mask_projection/.test(providerSwift),
  'RN preview must come from generated_lip_package.json runtime raw UV mask, not bbox/rounded-rect View drawing',
);
assertCheck(
  'Objective-C bridge exports native methods',
  /RCT_EXTERN_METHOD\(extractLipBoundary/.test(providerBridge) &&
    /RCT_EXTERN_METHOD\(saveGeneratedPackage/.test(providerBridge) &&
    /RCT_EXTERN_METHOD\(renderLipMaskPreview/.test(providerBridge),
  'Bridge must export extract/save/preview methods to RN',
);

const failed = checks.filter(check => !check.ok);
for (const check of checks) {
  const mark = check.ok ? 'ok' : 'FAIL';
  console.log(`[e7-native-generate] ${mark} ${check.name} - ${check.detail}`);
}

if (failed.length > 0) {
  console.error(
    `[e7-native-generate] ${failed.length} check(s) failed; native Generate is not pre-Xcode-ready.`,
  );
  process.exit(1);
}

console.log('[e7-native-generate] native Generate pre-Xcode checks ok');
