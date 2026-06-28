#!/usr/bin/env node
import childProcess from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '../..');
const rawArgs = process.argv.slice(2);
const args = new Set(rawArgs);
const writeReport = !args.has('--no-report');
const jsonOnly = args.has('--json');
const simulatedChangedFiles = rawArgs
  .filter(arg => arg.startsWith('--changed-file='))
  .map(arg => arg.slice('--changed-file='.length))
  .filter(Boolean);

const UNITY_PROJECT = 'unity/MakeupARUnityValidation';
const RN_PROJECT = 'rn/MakeupARValidation';
const RN_FRAMEWORK = `${RN_PROJECT}/unity/builds/ios/UnityFramework.framework`;
const PACKAGE_FRAMEWORK =
  `${RN_PROJECT}/node_modules/@azesmway/react-native-unity/ios/UnityFramework.framework`;
const REPORT_DIR = 'evidence/logs/e7-build-plan/latest';

const frameworkKeyFiles = [
  'UnityFramework',
  'Data/boot.config',
  'Data/globalgamemanagers',
  'Data/level0',
  'Data/resources.assets',
  'Data/Managed/Metadata/global-metadata.dat',
  'Data/ScriptingAssemblies.json',
  'Data/sharedassets0.assets',
];

const runtimeUnityPrefixes = [
  `${UNITY_PROJECT}/Assets/Scripts/`,
  `${UNITY_PROJECT}/Assets/Plugins/iOS/`,
  `${UNITY_PROJECT}/Assets/Shaders/`,
  `${UNITY_PROJECT}/Assets/Materials/`,
  `${UNITY_PROJECT}/Assets/Prefabs/`,
  `${UNITY_PROJECT}/Assets/Scenes/`,
  `${UNITY_PROJECT}/Assets/Resources/`,
  `${UNITY_PROJECT}/Assets/XR/`,
  `${UNITY_PROJECT}/ProjectSettings/`,
  `${UNITY_PROJECT}/Packages/`,
];

const editorUnityPrefixes = [`${UNITY_PROJECT}/Assets/Editor/`];

const rnNativePrefixes = [
  `${RN_PROJECT}/ios/`,
  `${RN_PROJECT}/android/`,
  `${RN_PROJECT}/Gemfile`,
  `${RN_PROJECT}/Gemfile.lock`,
];

const rnJsPrefixes = [
  `${RN_PROJECT}/App.tsx`,
  `${RN_PROJECT}/index.js`,
  `${RN_PROJECT}/__tests__/`,
  `${RN_PROJECT}/scripts/`,
  `${RN_PROJECT}/package.json`,
  `${RN_PROJECT}/package-lock.json`,
  `${RN_PROJECT}/babel.config.js`,
  `${RN_PROJECT}/metro.config.js`,
  `${RN_PROJECT}/jest.config.js`,
  `${RN_PROJECT}/.eslintrc.js`,
];

const prebuildPrefixes = [
  'scripts/e7_prebuild_gate/',
  'scripts/e7_build/',
  'docs/runbooks/E7_PREBUILD_GATE_RUNBOOK_KO.md',
  'docs/runbooks/E7_BUILD_MINIMIZATION_RUNBOOK_KO.md',
];

const docsPrefixes = ['docs/', 'README.md', 'TECH_VALIDATION_RESULT.md', 'AGENTS.md'];

const smoothRegionMaskPrefix = `${UNITY_PROJECT}/Assets/Resources/SmoothRegionMasks/`;
const unityEditorPrefix = `${UNITY_PROJECT}/Assets/Editor/`;

const productFallbackMaskIds = new Set([
  'lip-smooth-mask-v1',
  'cheek-smooth-mask-v1',
  'eye-smooth-mask-v1',
]);

const fullFaceRegionMaskIds = new Set([
  'e7-lip-balanced-uv-v0',
  'e7-blush-balanced-uv-v0',
  'e7-brow-balanced-uv-v0',
  'e7-eyeliner-minimal-safe-uv-v0',
  'e7-full-face-region-runtime-assets',
]);

const legacyValidationMaskIds = new Set([
  'e7-lip-validation-tight-auto-v0',
  'e7-lip-validation-tight-user-v0',
  'e7-lip-validation-safe-v0',
  'e7-lip-validation-cv-parsing-smooth-v1',
  'e7-lip-validation-cv-vision-fill-v1',
  'e7-lip-validation-cv-vision-color-v1',
  'e7-lip-validation-cv-hybrid-safe-v1',
  'e7-lip-validation-cv-hybrid-balanced-v1',
  'e7-lip-validation-runtime-candidates',
]);

function repoPath(...parts) {
  return path.join(repoRoot, ...parts);
}

function toPosix(value) {
  return value.split(path.sep).join('/');
}

function runGit(gitArgs) {
  try {
    const output = childProcess.execFileSync('git', gitArgs, {
      cwd: repoRoot,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    return output
      .split('\n')
      .map(line => line.trim())
      .filter(Boolean);
  } catch {
    return [];
  }
}

function unique(values) {
  return [...new Set(values)].sort();
}

function startsWithAny(filePath, prefixes) {
  return prefixes.some(prefix => filePath === prefix || filePath.startsWith(prefix));
}

function withoutMetaExtension(filePath) {
  return filePath.endsWith('.meta') ? filePath.slice(0, -'.meta'.length) : filePath;
}

function fileStem(filePath) {
  return path.basename(withoutMetaExtension(filePath), path.extname(withoutMetaExtension(filePath)));
}

function classifySmoothRegionMaskId(id) {
  if (productFallbackMaskIds.has(id)) {
    return {
      profile: 'product-runtime-fallback',
      buildImpact: 'unity-runtime',
      canExcludeFromProductBuild: false,
      exclusionStatus: 'keep-required',
      reason: 'Default region fallback mask still accepted by RN/Unity runtime.',
    };
  }
  if (fullFaceRegionMaskIds.has(id)) {
    return {
      profile: 'product-runtime-reference',
      buildImpact: 'unity-runtime',
      canExcludeFromProductBuild: false,
      exclusionStatus: 'keep-required',
      reason: 'Full-face region Generate reference asset is part of the active roadmap path.',
    };
  }
  if (legacyValidationMaskIds.has(id)) {
    return {
      profile: 'legacy-validation-debug',
      buildImpact: 'unity-legacy-debug-resource',
      canExcludeFromProductBuild: false,
      exclusionStatus: 'blocked-by-known-reference',
      reason: 'Legacy validation candidate; product flow should not depend on it, but references remain.',
    };
  }
  return {
    profile: 'needs-review',
    buildImpact: 'unity-runtime',
    canExcludeFromProductBuild: false,
    exclusionStatus: 'review-required',
    reason: 'Unknown SmoothRegionMasks resource; keep until references and runtime role are reviewed.',
  };
}

function classifyUnityAssetProfile(filePath) {
  const basePath = withoutMetaExtension(filePath);
  if (basePath.startsWith(unityEditorPrefix)) {
    return {
      profile: 'editor-only',
      buildImpact: 'unity-editor',
      canExcludeFromProductBuild: true,
      exclusionStatus: 'already-editor-only',
      reason: 'Assets/Editor is not part of the Unity player build.',
    };
  }
  if (basePath.startsWith(smoothRegionMaskPrefix)) {
    return classifySmoothRegionMaskId(fileStem(basePath));
  }
  if (basePath === `${UNITY_PROJECT}/Assets/Resources/SmoothRegionMaskMaterial.mat`) {
    return {
      profile: 'product-runtime-required',
      buildImpact: 'unity-runtime',
      canExcludeFromProductBuild: false,
      exclusionStatus: 'keep-required',
      reason: 'Smooth region material is loaded by the Unity runtime overlay.',
    };
  }
  if (
    basePath.includes('/Assets/XR/UserSimulationSettings/')
    || basePath.endsWith('/Assets/XR/Loaders/SimulationLoader.asset')
    || basePath.endsWith('/Assets/XR/Resources/XRSimulationRuntimeSettings.asset')
    || basePath.endsWith('/Assets/XR/Settings/XRSimulationSettings.asset')
  ) {
    return {
      profile: 'xr-simulation-debug',
      buildImpact: 'unity-editor',
      canExcludeFromProductBuild: true,
      exclusionStatus: 'exclude-candidate-after-unity-import-check',
      reason: 'XR Simulation is editor/debug support; ARKit loader remains the iPhone runtime path.',
    };
  }
  if (
    basePath.startsWith(`${UNITY_PROJECT}/Assets/Scripts/`)
    || basePath.startsWith(`${UNITY_PROJECT}/Assets/Plugins/iOS/`)
    || basePath.startsWith(`${UNITY_PROJECT}/Assets/Shaders/`)
    || basePath.startsWith(`${UNITY_PROJECT}/Assets/Materials/`)
    || basePath.startsWith(`${UNITY_PROJECT}/Assets/Prefabs/`)
    || basePath.startsWith(`${UNITY_PROJECT}/Assets/Scenes/`)
    || basePath.startsWith(`${UNITY_PROJECT}/Assets/XR/`)
    || basePath.startsWith(`${UNITY_PROJECT}/ProjectSettings/`)
    || basePath.startsWith(`${UNITY_PROJECT}/Packages/`)
  ) {
    return {
      profile: 'product-runtime-required',
      buildImpact: 'unity-runtime',
      canExcludeFromProductBuild: false,
      exclusionStatus: 'keep-required',
      reason: 'Unity runtime source, scene, plugin, material, shader, XR, package, or project setting.',
    };
  }
  if (basePath.startsWith(`${UNITY_PROJECT}/Assets/`)) {
    return {
      profile: 'needs-review',
      buildImpact: 'manual-review',
      canExcludeFromProductBuild: false,
      exclusionStatus: 'review-required',
      reason: 'Unity asset outside known product/debug buckets.',
    };
  }
  return {
    profile: 'not-unity-asset',
    buildImpact: 'not-unity',
    canExcludeFromProductBuild: false,
    exclusionStatus: 'not-applicable',
    reason: 'Not a Unity asset path.',
  };
}

function classifyChangedFile(filePath) {
  if (startsWithAny(filePath, editorUnityPrefixes)) {
    return 'unity-editor';
  }
  if (filePath.startsWith(`${UNITY_PROJECT}/Assets/`)) {
    const profile = classifyUnityAssetProfile(filePath);
    if (profile.buildImpact === 'unity-legacy-debug-resource') {
      return 'unity-legacy-debug-resource';
    }
    if (profile.buildImpact === 'unity-editor') {
      return 'unity-editor';
    }
    if (profile.buildImpact === 'manual-review') {
      return 'unknown';
    }
    if (profile.buildImpact === 'unity-runtime') {
      return 'unity-runtime';
    }
  }
  if (startsWithAny(filePath, runtimeUnityPrefixes)) {
    return 'unity-runtime';
  }
  if (startsWithAny(filePath, rnNativePrefixes)) {
    return 'rn-native';
  }
  if (startsWithAny(filePath, rnJsPrefixes)) {
    return 'rn-js';
  }
  if (startsWithAny(filePath, prebuildPrefixes)) {
    return 'prebuild-tooling';
  }
  if (startsWithAny(filePath, docsPrefixes)) {
    return 'docs';
  }
  if (filePath.startsWith('scripts/')) {
    return 'script';
  }
  return 'unknown';
}

function hashFile(filePath) {
  if (!fs.existsSync(filePath)) {
    return null;
  }
  const hash = crypto.createHash('sha256');
  hash.update(fs.readFileSync(filePath));
  return hash.digest('hex');
}

function fileContains(filePath, needle) {
  if (!fs.existsSync(filePath)) {
    return false;
  }
  return fs.readFileSync(filePath).includes(Buffer.from(needle));
}

function frameworkContains(frameworkPath, needle) {
  const searchFiles = ['UnityFramework', ...frameworkKeyFiles];
  return searchFiles.some(keyFile =>
    fileContains(path.join(frameworkPath, keyFile), needle),
  );
}

function inspectFramework(frameworkRelativePath) {
  const frameworkPath = repoPath(frameworkRelativePath);
  const files = {};
  for (const keyFile of frameworkKeyFiles) {
    files[keyFile] = hashFile(path.join(frameworkPath, keyFile));
  }
  return {
    path: frameworkRelativePath,
    exists: fs.existsSync(frameworkPath),
    files,
    strings: {
      generatedLipMaskAck: frameworkContains(
        frameworkPath,
        'generated_lip_mask_applied',
      ),
      captureReference: frameworkContains(
        frameworkPath,
        'CaptureE7ReferenceFrameJson',
      ),
      validationControls: frameworkContains(frameworkPath, 'validationControls'),
    },
  };
}

function compareFrameworks(reference, packaged) {
  if (!reference.exists || !packaged.exists) {
    return {
      synced: false,
      reason: !reference.exists
        ? 'rn_reference_unityframework_missing'
        : 'package_unityframework_missing',
      mismatches: frameworkKeyFiles,
    };
  }
  const mismatches = frameworkKeyFiles.filter(
    keyFile => reference.files[keyFile] !== packaged.files[keyFile],
  );
  const requiredStringKeys = ['generatedLipMaskAck', 'captureReference'];
  const missingStrings = requiredStringKeys.filter(key => !packaged.strings[key]);
  const optionalMissingStrings = Object.entries(packaged.strings)
    .filter(([key, present]) => !requiredStringKeys.includes(key) && !present)
    .map(([key]) => key);
  return {
    synced: mismatches.length === 0 && missingStrings.length === 0,
    reason:
      mismatches.length > 0
        ? 'framework_hash_mismatch'
        : missingStrings.length > 0
        ? 'framework_required_strings_missing'
        : 'frameworks_synced',
    mismatches,
    missingStrings,
    optionalMissingStrings,
  };
}

function walkFiles(rootRelativePath, options = {}) {
  const rootPath = repoPath(rootRelativePath);
  const output = [];
  const maxBytes = options.maxBytes ?? 2_000_000;
  const skipDirs = new Set(options.skipDirs ?? ['node_modules', 'Library', 'Logs']);
  function walk(currentPath) {
    if (!fs.existsSync(currentPath)) {
      return;
    }
    const stat = fs.statSync(currentPath);
    if (stat.isDirectory()) {
      const base = path.basename(currentPath);
      if (skipDirs.has(base)) {
        return;
      }
      for (const entry of fs.readdirSync(currentPath)) {
        walk(path.join(currentPath, entry));
      }
      return;
    }
    if (stat.size > maxBytes) {
      return;
    }
    output.push(toPosix(path.relative(repoRoot, currentPath)));
  }
  walk(rootPath);
  return output.sort();
}

function readTextIfSmall(relativePath) {
  const fullPath = repoPath(relativePath);
  if (!fs.existsSync(fullPath)) {
    return '';
  }
  const stat = fs.statSync(fullPath);
  if (stat.size > 2_000_000) {
    return '';
  }
  try {
    return fs.readFileSync(fullPath, 'utf8');
  } catch {
    return '';
  }
}

function findTextReferences(needle, files, selfFile) {
  return files.filter(filePath => {
    if (filePath === selfFile || filePath.endsWith('.meta')) {
      return false;
    }
    return readTextIfSmall(filePath).includes(needle);
  });
}

function countBy(items, keyName) {
  return items.reduce((acc, item) => {
    const key = item[keyName] ?? 'unknown';
    acc[key] = (acc[key] ?? 0) + 1;
    return acc;
  }, {});
}

function inspectUnityAssets() {
  const unityFiles = walkFiles(`${UNITY_PROJECT}/Assets`, {
    maxBytes: 1_500_000,
    skipDirs: [],
  }).filter(filePath => !filePath.endsWith('.meta'));
  const textSearchFiles = unique([
    ...walkFiles(`${UNITY_PROJECT}/Assets`, {maxBytes: 1_500_000, skipDirs: []}),
    `${RN_PROJECT}/App.tsx`,
    ...walkFiles('scripts', {maxBytes: 1_000_000, skipDirs: ['__pycache__']}),
  ]).filter(filePath => !filePath.endsWith('.png') && !filePath.endsWith('.jpg'));

  const unityAssetProfiles = unityFiles.map(filePath => {
    const profile = classifyUnityAssetProfile(filePath);
    const fullPath = repoPath(filePath);
    const sizeBytes = fs.existsSync(fullPath) ? fs.statSync(fullPath).size : 0;
    return {
      file: filePath,
      sizeBytes,
      ...profile,
    };
  });

  const runtimeScripts = unityFiles
    .filter(filePath => filePath.startsWith(`${UNITY_PROJECT}/Assets/Scripts/`))
    .map(filePath => {
      const className = path.basename(filePath, '.cs');
      const references = findTextReferences(className, textSearchFiles, filePath);
      const profile = classifyUnityAssetProfile(filePath);
      return {
        file: filePath,
        className,
        profile: profile.profile,
        buildImpact: profile.buildImpact,
        exclusionStatus: profile.exclusionStatus,
        status: references.some(
          reference =>
            reference.includes('/Scenes/') ||
            reference.includes('/Prefabs/') ||
            reference.endsWith('RNBridge.cs') ||
            reference.endsWith('E7SynchronizedCaptureExporter.cs') ||
            reference.endsWith('FaceTrackingStatusReporter.cs'),
        )
          ? 'runtime-referenced'
          : references.length > 0
          ? 'source-referenced'
          : 'no-static-reference',
        references: references.slice(0, 8),
      };
    });

  const editorScripts = unityFiles
    .filter(filePath => filePath.startsWith(`${UNITY_PROJECT}/Assets/Editor/`))
    .map(filePath => ({file: filePath, status: 'editor-only'}));

  const smoothMaskResources = unityFiles
    .filter(filePath =>
      filePath.startsWith(`${UNITY_PROJECT}/Assets/Resources/SmoothRegionMasks/`),
    )
    .map(filePath => {
      const extension = path.extname(filePath);
      const id = path.basename(filePath, extension);
      const references = findTextReferences(id, textSearchFiles, filePath);
      const profile = classifySmoothRegionMaskId(id);
      const runtimeReferences = references.filter(
        reference =>
          reference === `${RN_PROJECT}/App.tsx` ||
          reference.includes('/Assets/Scripts/'),
      );
      const status =
        runtimeReferences.length > 0
          ? 'runtime-referenced'
          : references.length > 0
          ? 'tooling-or-registry-referenced'
          : 'no-static-reference';
      const exclusionStatus =
        status === 'no-static-reference' && profile.profile === 'legacy-validation-debug'
          ? 'exclude-ready-after-move'
          : status === 'runtime-referenced' && profile.profile === 'legacy-validation-debug'
          ? 'blocked-by-runtime-reference'
          : profile.exclusionStatus;
      return {
        file: filePath,
        id,
        profile: profile.profile,
        buildImpact: profile.buildImpact,
        status,
        canExcludeFromProductBuild:
          status === 'no-static-reference' && profile.profile === 'legacy-validation-debug',
        exclusionStatus,
        reason: profile.reason,
        references: references.slice(0, 8),
      };
    });

  return {
    summary: {
      unityAssetProfiles: unityAssetProfiles.length,
      profileCounts: countBy(unityAssetProfiles, 'profile'),
      buildImpactCounts: countBy(unityAssetProfiles, 'buildImpact'),
      exclusionStatusCounts: countBy(unityAssetProfiles, 'exclusionStatus'),
      runtimeScripts: runtimeScripts.length,
      editorOnlyScripts: editorScripts.length,
      smoothMaskResources: smoothMaskResources.length,
      noStaticReferenceResources: smoothMaskResources.filter(
        item => item.status === 'no-static-reference',
      ).length,
      excludeReadyResources: smoothMaskResources.filter(
        item => item.exclusionStatus === 'exclude-ready-after-move',
      ).length,
      legacyValidationResources: smoothMaskResources.filter(
        item => item.profile === 'legacy-validation-debug',
      ).length,
      productRequiredOrFallbackResources: smoothMaskResources.filter(
        item =>
          item.profile === 'product-runtime-fallback'
          || item.profile === 'product-runtime-reference',
      ).length,
    },
    unityAssetProfiles,
    runtimeScripts,
    editorScripts,
    smoothMaskResources,
    cleanupAdvice:
      'Do not delete Unity assets solely from this static audit. Legacy validation resources can move out of Resources only after RN/Unity runtime references are removed and Unity import/compile passes.',
  };
}

function decideBuild(changedFiles, frameworkSync) {
  const buckets = changedFiles.reduce((acc, filePath) => {
    const bucket = classifyChangedFile(filePath);
    acc[bucket] ??= [];
    acc[bucket].push(filePath);
    return acc;
  }, {});

  const hasUnityRuntime = Boolean(buckets['unity-runtime']?.length);
  const hasUnityEditor = Boolean(buckets['unity-editor']?.length);
  const hasUnityLegacyDebugResource = Boolean(
    buckets['unity-legacy-debug-resource']?.length,
  );
  const hasRnNative = Boolean(buckets['rn-native']?.length);
  const hasRnJs = Boolean(buckets['rn-js']?.length);
  const hasUnknown = Boolean(buckets.unknown?.length);

  if (hasUnityRuntime) {
    return {
      decision: 'run-unityframework-build',
      reason: 'Unity runtime source/assets changed.',
      commands: [
        'bash scripts/build_m3_unityframework.sh',
        'cd rn/MakeupARValidation && npm run e7:prebuild:full -- --no-report',
        'cd rn/MakeupARValidation && npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK',
      ],
      buckets,
    };
  }

  if (!frameworkSync.synced) {
    return {
      decision: 'sync-or-rebuild-unityframework-before-xcode',
      reason: frameworkSync.reason,
      commands: [
        'If only package framework differs from RN reference, sync the reference framework into node_modules.',
        'If required strings are missing or reference framework is stale, run: bash scripts/build_m3_unityframework.sh',
        'Then rerun: cd rn/MakeupARValidation && npm run e7:prebuild:full -- --no-report',
      ],
      buckets,
    };
  }

  if (hasRnNative || hasRnJs) {
    return {
      decision: 'skip-unityframework-run-rn-xcode-only',
      reason:
        hasUnityLegacyDebugResource
          ? 'RN/iOS app-side files changed; only additional Unity asset changes are legacy/debug resources, and UnityFramework hashes are synced.'
          : 'Only RN/iOS app-side files changed and UnityFramework reference/package hashes are synced.',
      commands: [
        'cd rn/MakeupARValidation && ./node_modules/.bin/tsc --noEmit',
        'cd rn/MakeupARValidation && npm test -- --runInBand --watchman=false',
        'cd rn/MakeupARValidation && npm run e7:prebuild:full -- --no-report',
        'cd rn/MakeupARValidation && npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK',
      ],
      buckets,
    };
  }

  if (hasUnityLegacyDebugResource) {
    return {
      decision: 'skip-product-phone-build-legacy-debug-resource-only',
      reason:
        'Only legacy/debug Unity resources changed. Product Generate path should not require an iPhone build; rebuild UnityFramework only if deliberately reviewing those legacy candidates.',
      commands: [
        'cd rn/MakeupARValidation && npm run e7:build-plan -- --no-report',
        'cd rn/MakeupARValidation && npm run e7:prebuild:full -- --no-report',
        'If legacy candidate visuals must be tested, ask the user before running UnityFramework/Xcode.',
      ],
      buckets,
    };
  }

  if (hasUnityEditor) {
    return {
      decision: 'skip-unityframework-run-unity-import-if-needed',
      reason: 'Only Unity editor/smoke tooling changed; player framework should not change.',
      commands: [
        'Run the targeted Unity batchmode smoke/import only if this editor tooling is part of the gate.',
        'Skip Xcode unless RN/native/runtime files also changed.',
      ],
      buckets,
    };
  }

  if (hasUnknown) {
    return {
      decision: 'manual-review-before-build',
      reason: 'Unknown changed paths require human classification before skipping Unity.',
      commands: ['Inspect unknown files, then rerun this script.'],
      buckets,
    };
  }

  return {
    decision: changedFiles.length > 0 ? 'no-phone-build-needed' : 'no-local-changes',
    reason: changedFiles.length > 0 ? 'Only docs/tooling files changed.' : 'No changed files detected.',
    commands: ['No UnityFramework rebuild needed from the current diff.'],
    buckets,
  };
}

function writeJson(relativePath, value) {
  const fullPath = repoPath(relativePath);
  fs.mkdirSync(path.dirname(fullPath), {recursive: true});
  fs.writeFileSync(fullPath, `${JSON.stringify(value, null, 2)}\n`);
}

function renderCounts(counts) {
  return Object.entries(counts)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([key, value]) => `- ${key}: ${value}`);
}

function renderSmoothMaskRows(items) {
  if (items.length === 0) {
    return ['_No SmoothRegionMasks resources found._'];
  }
  return [
    '| id | profile | reference status | exclusion status |',
    '| --- | --- | --- | --- |',
    ...items.map(
      item =>
        `| \`${item.id}\` | \`${item.profile}\` | \`${item.status}\` | \`${item.exclusionStatus}\` |`,
    ),
  ];
}

function renderMarkdown(result) {
  const lines = [
    '# E7 Minimum Build Decision',
    '',
    `- decision: \`${result.build.decision}\``,
    `- reason: ${result.build.reason}`,
    `- changed files: ${result.changedFiles.length}`,
    `- framework sync: ${result.framework.sync.synced ? 'synced' : 'not synced'} (${result.framework.sync.reason})`,
    '',
    '## Commands',
    '',
    ...result.build.commands.map(command => `- ${command}`),
    '',
    '## Changed Buckets',
    '',
  ];
  for (const [bucket, files] of Object.entries(result.build.buckets)) {
    lines.push(`### ${bucket}`, '');
    files.forEach(filePath => lines.push(`- ${filePath}`));
    lines.push('');
  }
  lines.push(
    '## Unity Asset Audit',
    '',
    `- profiled Unity assets: ${result.unityAssetAudit.summary.unityAssetProfiles}`,
    `- runtime scripts: ${result.unityAssetAudit.summary.runtimeScripts}`,
    `- editor-only scripts: ${result.unityAssetAudit.summary.editorOnlyScripts}`,
    `- SmoothRegionMasks resources: ${result.unityAssetAudit.summary.smoothMaskResources}`,
    `- no static reference resources: ${result.unityAssetAudit.summary.noStaticReferenceResources}`,
    `- legacy validation resources: ${result.unityAssetAudit.summary.legacyValidationResources}`,
    `- product required/fallback resources: ${result.unityAssetAudit.summary.productRequiredOrFallbackResources}`,
    `- exclude-ready resources: ${result.unityAssetAudit.summary.excludeReadyResources}`,
    '',
    '### Build Impact Counts',
    '',
    ...renderCounts(result.unityAssetAudit.summary.buildImpactCounts),
    '',
    '### Product/Debug Profile Counts',
    '',
    ...renderCounts(result.unityAssetAudit.summary.profileCounts),
    '',
    '### SmoothRegionMasks File Decisions',
    '',
    ...renderSmoothMaskRows(result.unityAssetAudit.smoothMaskResources),
    '',
    result.unityAssetAudit.cleanupAdvice,
    '',
    'Full file-level profile data is in `minimum-build-decision.json` under `unityAssetAudit.unityAssetProfiles`.',
    '',
  );
  return `${lines.join('\n')}\n`;
}

const changedFiles = simulatedChangedFiles.length > 0
  ? unique(simulatedChangedFiles)
  : unique([
      ...runGit(['diff', '--name-only', 'HEAD', '--']),
      ...runGit(['diff', '--name-only', '--cached', '--']),
      ...runGit(['ls-files', '--others', '--exclude-standard']),
    ]);
const referenceFramework = inspectFramework(RN_FRAMEWORK);
const packageFramework = inspectFramework(PACKAGE_FRAMEWORK);
const frameworkSync = compareFrameworks(referenceFramework, packageFramework);
const unityAssetAudit = inspectUnityAssets();
const build = decideBuild(changedFiles, frameworkSync);

const result = {
  schemaVersion: 'e7-minimum-build-decision-v1',
  generatedAt: new Date().toISOString(),
  simulatedChangedFiles: simulatedChangedFiles.length > 0,
  changedFiles,
  framework: {
    reference: referenceFramework,
    package: packageFramework,
    sync: frameworkSync,
  },
  build,
  unityAssetAudit,
};

if (writeReport) {
  writeJson(`${REPORT_DIR}/minimum-build-decision.json`, result);
  fs.writeFileSync(repoPath(`${REPORT_DIR}/minimum-build-decision.md`), renderMarkdown(result));
}

if (jsonOnly) {
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} else {
  console.log(`decision=${build.decision}`);
  console.log(`reason=${build.reason}`);
  console.log(`changedFiles=${changedFiles.length}`);
  console.log(
    `unityFrameworkSync=${frameworkSync.synced ? 'true' : 'false'} reason=${frameworkSync.reason}`,
  );
  console.log(
    `unityAssetAudit smoothRegionMasks=${unityAssetAudit.summary.smoothMaskResources} noStaticReference=${unityAssetAudit.summary.noStaticReferenceResources}`,
  );
  console.log(
    `unityAssetProfiles=${unityAssetAudit.summary.unityAssetProfiles} legacyValidation=${unityAssetAudit.summary.legacyValidationResources} excludeReady=${unityAssetAudit.summary.excludeReadyResources}`,
  );
  console.log('nextCommands:');
  build.commands.forEach(command => console.log(`- ${command}`));
  if (writeReport) {
    console.log(`report=${REPORT_DIR}/minimum-build-decision.md`);
  }
}
