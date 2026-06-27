#!/usr/bin/env node
import childProcess from 'node:child_process';
import crypto from 'node:crypto';
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '../..');
const args = new Set(process.argv.slice(2));
const writeReport = !args.has('--no-report');
const jsonOnly = args.has('--json');

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
];

const docsPrefixes = ['docs/', 'README.md', 'TECH_VALIDATION_RESULT.md', 'AGENTS.md'];

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

function classifyChangedFile(filePath) {
  if (startsWithAny(filePath, runtimeUnityPrefixes)) {
    return 'unity-runtime';
  }
  if (startsWithAny(filePath, editorUnityPrefixes)) {
    return 'unity-editor';
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

  const runtimeScripts = unityFiles
    .filter(filePath => filePath.startsWith(`${UNITY_PROJECT}/Assets/Scripts/`))
    .map(filePath => {
      const className = path.basename(filePath, '.cs');
      const references = findTextReferences(className, textSearchFiles, filePath);
      return {
        file: filePath,
        className,
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
      const runtimeReferences = references.filter(
        reference =>
          reference === `${RN_PROJECT}/App.tsx` ||
          reference.includes('/Assets/Scripts/'),
      );
      return {
        file: filePath,
        id,
        status:
          runtimeReferences.length > 0
            ? 'runtime-referenced'
            : references.length > 0
            ? 'tooling-or-registry-referenced'
            : 'no-static-reference',
        references: references.slice(0, 8),
      };
    });

  return {
    summary: {
      runtimeScripts: runtimeScripts.length,
      editorOnlyScripts: editorScripts.length,
      smoothMaskResources: smoothMaskResources.length,
      noStaticReferenceResources: smoothMaskResources.filter(
        item => item.status === 'no-static-reference',
      ).length,
    },
    runtimeScripts,
    editorScripts,
    smoothMaskResources,
    cleanupAdvice:
      'Do not delete Unity assets solely from this static audit. Remove old RN sample selectors and registries first, then rerun this script and Unity import/compile.',
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
        'Only RN/iOS app-side files changed and UnityFramework reference/package hashes are synced.',
      commands: [
        'cd rn/MakeupARValidation && ./node_modules/.bin/tsc --noEmit',
        'cd rn/MakeupARValidation && npm test -- --runInBand --watchman=false',
        'cd rn/MakeupARValidation && npm run e7:prebuild:full -- --no-report',
        'cd rn/MakeupARValidation && npm run ios -- --device "위승철의 iPhone" --no-packager --extra-params DEVELOPMENT_TEAM=9G4K6N63MK',
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
    `- runtime scripts: ${result.unityAssetAudit.summary.runtimeScripts}`,
    `- editor-only scripts: ${result.unityAssetAudit.summary.editorOnlyScripts}`,
    `- SmoothRegionMasks resources: ${result.unityAssetAudit.summary.smoothMaskResources}`,
    `- no static reference resources: ${result.unityAssetAudit.summary.noStaticReferenceResources}`,
    '',
    result.unityAssetAudit.cleanupAdvice,
    '',
  );
  return `${lines.join('\n')}\n`;
}

const changedFiles = unique([
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
  console.log('nextCommands:');
  build.commands.forEach(command => console.log(`- ${command}`));
  if (writeReport) {
    console.log(`report=${REPORT_DIR}/minimum-build-decision.md`);
  }
}
