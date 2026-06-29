#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';
import { spawnSync } from 'node:child_process';

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(scriptDir, '..', '..');
const args = new Set(process.argv.slice(2));
const runChildChecks = args.has('--run-checks') || args.has('--full');
const writeReport = !args.has('--no-report');

const fixtureRoot = path.join(
  repoRoot,
  'evidence',
  'logs',
  'e7-device-pull-20260627-post-user-review',
);
const generatedPackagePath = path.join(
  fixtureRoot,
  'generated-package',
  'generated_lip_package.json',
);
const savedRecordPath = path.join(
  fixtureRoot,
  'generated-package',
  'saved_record.json',
);
const sourceFramePath = path.join(
  fixtureRoot,
  'source-pair-111840Z-12',
  'frame.png',
);
const arFaceExportPath = path.join(
  fixtureRoot,
  'source-pair-111840Z-12',
  'arface_export.json',
);
const rnAppPath = path.join(repoRoot, 'rn', 'MakeupARValidation', 'App.tsx');
const rnAppTestPath = path.join(
  repoRoot,
  'rn',
  'MakeupARValidation',
  '__tests__',
  'App.test.tsx',
);
const rnPackagePath = path.join(
  repoRoot,
  'rn',
  'MakeupARValidation',
  'package.json',
);
const personalizedPipelinePath = path.join(
  repoRoot,
  'rn',
  'MakeupARValidation',
  'src',
  'e7PersonalizedGeneratePipeline.ts',
);
const nativeProviderPath = path.join(
  repoRoot,
  'rn',
  'MakeupARValidation',
  'ios',
  'MakeupARValidation',
  'E7NativeLipBoundaryProviders.swift',
);
const nativeBridgePath = path.join(
  repoRoot,
  'rn',
  'MakeupARValidation',
  'ios',
  'MakeupARValidation',
  'E7NativeLipBoundaryProvidersBridge.m',
);
const rnNativeCheckPath = path.join(
  repoRoot,
  'rn',
  'MakeupARValidation',
  'scripts',
  'check-e7-native-generate.js',
);
const unityBridgePath = path.join(
  repoRoot,
  'unity',
  'MakeupARUnityValidation',
  'Assets',
  'Scripts',
  'RNBridge.cs',
);
const unityCaptureExporterPath = path.join(
  repoRoot,
  'unity',
  'MakeupARUnityValidation',
  'Assets',
  'Scripts',
  'E7SynchronizedCaptureExporter.cs',
);
const unityFrameworkPath = path.join(
  repoRoot,
  'rn',
  'MakeupARValidation',
  'node_modules',
  '@azesmway',
  'react-native-unity',
  'ios',
  'UnityFramework.framework',
);
const reportDir = path.join(
  repoRoot,
  'evidence',
  'logs',
  'e7-prebuild-gate',
  'latest',
);

const checks = [];

function addCheck(id, ok, detail, meta = {}) {
  checks.push({
    id,
    status: ok ? 'pass' : 'fail',
    detail,
    ...meta,
  });
}

function addWarn(id, detail, meta = {}) {
  checks.push({
    id,
    status: 'warn',
    detail,
    ...meta,
  });
}

function exists(filePath) {
  return fs.existsSync(filePath);
}

function readText(filePath) {
  return fs.readFileSync(filePath, 'utf8');
}

function readJson(filePath) {
  return JSON.parse(readText(filePath).replace(/^\uFEFF/, ''));
}

function safeReadText(filePath) {
  return exists(filePath) ? readText(filePath) : '';
}

function readTextFilesUnder(rootPath) {
  if (!exists(rootPath)) {
    return '';
  }
  const stack = [rootPath];
  const chunks = [];
  const textExtensions = new Set([
    '.cjs',
    '.js',
    '.jsx',
    '.mjs',
    '.ts',
    '.tsx',
  ]);
  while (stack.length > 0) {
    const current = stack.pop();
    const stat = fs.statSync(current);
    if (stat.isDirectory()) {
      if (
        ['.git', 'build', 'coverage', 'node_modules', 'Pods'].includes(
          path.basename(current),
        )
      ) {
        continue;
      }
      for (const child of fs.readdirSync(current)) {
        stack.push(path.join(current, child));
      }
      continue;
    }
    if (stat.isFile() && textExtensions.has(path.extname(current))) {
      chunks.push(readText(current));
    }
  }
  return chunks.join('\n');
}

function matchesAll(source, patterns) {
  return patterns.every(pattern => pattern.test(source));
}

function matchesAny(source, patterns) {
  return patterns.some(pattern => pattern.test(source));
}

function sourceWindows(source, anchorPatterns, radius = 1600) {
  const windows = [];
  for (const pattern of anchorPatterns) {
    const flags = pattern.flags.includes('g')
      ? pattern.flags
      : `${pattern.flags}g`;
    const globalPattern = new RegExp(pattern.source, flags);
    let match = globalPattern.exec(source);
    while (match) {
      windows.push(
        source.slice(
          Math.max(0, match.index - radius),
          Math.min(source.length, match.index + match[0].length + radius),
        ),
      );
      if (match[0].length === 0) {
        globalPattern.lastIndex += 1;
      }
      match = globalPattern.exec(source);
    }
  }
  return windows;
}

function anyWindowMatchesAll(source, anchorPatterns, requiredPatterns, radius) {
  return sourceWindows(source, anchorPatterns, radius).some(window =>
    matchesAll(window, requiredPatterns),
  );
}

function patternPresenceDetail(source, requirements) {
  return requirements
    .map(({ label, pattern }) => `${label}=${pattern.test(source) ? 'yes' : 'no'}`)
    .join(' ');
}

function bounds(points) {
  if (!Array.isArray(points) || points.length === 0) {
    return null;
  }
  return points.reduce(
    (acc, point) => ({
      minX: Math.min(acc.minX, Number(point.x)),
      minY: Math.min(acc.minY, Number(point.y)),
      maxX: Math.max(acc.maxX, Number(point.x)),
      maxY: Math.max(acc.maxY, Number(point.y)),
    }),
    {
      minX: Number.POSITIVE_INFINITY,
      minY: Number.POSITIVE_INFINITY,
      maxX: Number.NEGATIVE_INFINITY,
      maxY: Number.NEGATIVE_INFINITY,
    },
  );
}

function polygonArea(points) {
  if (!Array.isArray(points) || points.length < 3) {
    return 0;
  }
  let area = 0;
  for (let index = 0; index < points.length; index += 1) {
    const current = points[index];
    const next = points[(index + 1) % points.length];
    area += Number(current.x) * Number(next.y) - Number(next.x) * Number(current.y);
  }
  return Math.abs(area) * 0.5;
}

function analyzeRawRgba(payload) {
  const width = Number(payload?.maskTextureWidth ?? 0);
  const height = Number(payload?.maskTextureHeight ?? 0);
  const raw = Buffer.from(String(payload?.maskRawRgbaBase64 ?? ''), 'base64');
  const expectedBytes = width * height * 4;
  let nonzeroAlpha = 0;
  let strongAlpha = 0;
  let edgeBandAlpha = 0;
  let maxAlpha = 0;
  let minX = width;
  let minY = height;
  let maxX = -1;
  let maxY = -1;
  if (width > 0 && height > 0 && raw.length === expectedBytes) {
    for (let index = 0; index < width * height; index += 1) {
      const alpha = raw[index * 4 + 3];
      maxAlpha = Math.max(maxAlpha, alpha);
      if (alpha > 0) {
        nonzeroAlpha += 1;
        const x = index % width;
        const y = Math.floor(index / width);
        minX = Math.min(minX, x);
        minY = Math.min(minY, y);
        maxX = Math.max(maxX, x);
        maxY = Math.max(maxY, y);
      }
      if (alpha >= 128) {
        strongAlpha += 1;
      }
      if (alpha > 8 && alpha < 247) {
        edgeBandAlpha += 1;
      }
    }
  }

  return {
    width,
    height,
    bytes: raw.length,
    expectedBytes,
    nonzeroAlpha,
    strongAlpha,
    edgeBandAlpha,
    edgeBandRatio: nonzeroAlpha > 0 ? edgeBandAlpha / nonzeroAlpha : 0,
    maxAlpha,
    bbox: maxX >= minX ? { minX, minY, maxX, maxY } : null,
  };
}

function pointsToSvg(points) {
  return (points ?? [])
    .map(point => `${Number(point.x).toFixed(2)},${Number(point.y).toFixed(2)}`)
    .join(' ');
}

function writePreviewArtifacts(generatedPackage) {
  const metadata = generatedPackage.sourceFrameMetadata ?? {};
  const width = Number(metadata.frameWidth ?? 0);
  const height = Number(metadata.frameHeight ?? 0);
  const outer = generatedPackage.lipBoundary2D?.outerPoints ?? [];
  const inner = generatedPackage.lipBoundary2D?.innerPoints ?? [];
  const frameHref = pathToFileURL(sourceFramePath).href;

  fs.mkdirSync(reportDir, { recursive: true });
  const svgPath = path.join(reportDir, 'mask-preview.svg');
  const htmlPath = path.join(reportDir, 'mask-preview.html');
  const reportStyle = 'font-family:-apple-system,BlinkMacSystemFont,Helvetica,Arial,sans-serif;';
  const svg = [
    `<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">`,
    `  <image href="${frameHref}" x="0" y="0" width="${width}" height="${height}" preserveAspectRatio="xMidYMid meet"/>`,
    `  <polygon points="${pointsToSvg(outer)}" fill="#db4778" fill-opacity="0.48" stroke="#ffffff" stroke-width="7" stroke-linejoin="round"/>`,
    inner.length >= 3
      ? `  <polygon points="${pointsToSvg(inner)}" fill="#111111" fill-opacity="0.32" stroke="#ffe7f1" stroke-width="4" stroke-linejoin="round"/>`
      : '',
    `  <text x="32" y="58" fill="#ffffff" font-size="38" font-family="Helvetica" font-weight="700">E7 prebuild actual package preview</text>`,
    '</svg>',
    '',
  ].join('\n');
  const html = [
    '<!doctype html>',
    '<meta charset="utf-8">',
    `<title>E7 Prebuild Mask Preview</title>`,
    `<body style="${reportStyle} margin:0; background:#111; color:white;">`,
    '<main style="max-width:920px; margin:0 auto; padding:24px;">',
    '<h1 style="font-size:24px;">E7 Prebuild Mask Preview</h1>',
    '<p>이 파일은 generated_lip_package.json의 lipBoundary2D를 그대로 그립니다. 앱 preview가 이 형태와 다르면 빌드 금지입니다.</p>',
    `<img src="${path.basename(svgPath)}" style="width:100%; height:auto; border:1px solid #555;">`,
    '</main>',
    '</body>',
    '',
  ].join('\n');
  fs.writeFileSync(svgPath, svg);
  fs.writeFileSync(htmlPath, html);
  return { svgPath, htmlPath };
}

function fileContainsBytes(rootPath, needle) {
  if (!exists(rootPath)) {
    return false;
  }
  const needleBuffer = Buffer.from(needle);
  const stack = [rootPath];
  while (stack.length > 0) {
    const current = stack.pop();
    const stat = fs.statSync(current);
    if (stat.isDirectory()) {
      for (const child of fs.readdirSync(current)) {
        stack.push(path.join(current, child));
      }
      continue;
    }
    if (!stat.isFile() || stat.size === 0) {
      continue;
    }
    const content = fs.readFileSync(current);
    if (content.includes(needleBuffer)) {
      return true;
    }
  }
  return false;
}

function runNodeCheck(label, commandArgs, cwd) {
  const result = spawnSync(process.execPath, commandArgs, {
    cwd,
    encoding: 'utf8',
  });
  return {
    label,
    ok: result.status === 0,
    status: result.status,
    stdout: result.stdout.trim(),
    stderr: result.stderr.trim(),
  };
}

function runMain() {
  addCheck(
    'fixture.frame_exists',
    exists(sourceFramePath),
    sourceFramePath,
  );
  addCheck(
    'fixture.arface_export_exists',
    exists(arFaceExportPath),
    arFaceExportPath,
  );
  addCheck(
    'fixture.generated_package_exists',
    exists(generatedPackagePath),
    generatedPackagePath,
  );
  addCheck('fixture.saved_record_exists', exists(savedRecordPath), savedRecordPath);

  let generatedPackage = null;
  let arFaceExport = null;
  let savedRecord = null;
  try {
    generatedPackage = readJson(generatedPackagePath);
    arFaceExport = readJson(arFaceExportPath);
    savedRecord = readJson(savedRecordPath);
  } catch (error) {
    addCheck('fixture.json_parse', false, error.message);
  }

  const rnAppSource = safeReadText(rnAppPath);
  const personalizedPipelineSource = safeReadText(personalizedPipelinePath);
  const nativeProviderSource = safeReadText(nativeProviderPath);
  const nativeBridgeSource = safeReadText(nativeBridgePath);
  const unityBridgeSource = safeReadText(unityBridgePath);
  const unityCaptureExporterSource = safeReadText(unityCaptureExporterPath);

  if (generatedPackage && arFaceExport && savedRecord) {
    const boundary = generatedPackage.lipBoundary2D;
    const outer = boundary?.outerPoints ?? [];
    const inner = boundary?.innerPoints ?? [];
    const outerBounds = bounds(outer);
    const outerArea = polygonArea(outer);
    const bboxArea = outerBounds
      ? Math.max(0, outerBounds.maxX - outerBounds.minX) *
        Math.max(0, outerBounds.maxY - outerBounds.minY)
      : 0;
    const areaRatio = bboxArea > 0 ? outerArea / bboxArea : 0;
    const uvStats = analyzeRawRgba(generatedPackage.runtimeApplyPayload);
    const previewPaths = writeReport ? writePreviewArtifacts(generatedPackage) : null;

    addCheck(
      'package.schema',
      generatedPackage.schemaVersion === 'e7-personalized-lip-generate-package-v0',
      `schemaVersion=${generatedPackage.schemaVersion}`,
    );
    addCheck(
      'package.privacy_local_only',
      generatedPackage.privacyFlags?.localOnly === true &&
        generatedPackage.privacyFlags?.offDeviceUpload === false &&
        generatedPackage.privacyFlags?.longTermRawFrameStored === false,
      JSON.stringify(generatedPackage.privacyFlags),
    );
    addCheck(
      'package.boundary_points',
      outer.length >= 8 && inner.length >= 3,
      `outer=${outer.length} inner=${inner.length}`,
      { outerPointCount: outer.length, innerPointCount: inner.length },
    );
    addCheck(
      'package.boundary_not_bbox_proxy',
      areaRatio > 0.25 && areaRatio < 0.85,
      `polygonArea=${outerArea.toFixed(1)} bboxArea=${bboxArea.toFixed(1)} areaRatio=${areaRatio.toFixed(3)}`,
      { outerBounds, outerArea, bboxArea, areaRatio },
    );
    addCheck(
      'package.runtime_payload_shape',
      generatedPackage.runtimeApplyPayload?.schemaVersion ===
        'e7-generated-lip-mask-runtime-payload-v0' &&
        generatedPackage.runtimeApplyPayload?.maskTextureEncoding ===
          'raw_rgba_base64' &&
        generatedPackage.runtimeApplyPayload?.localOnly === true &&
        generatedPackage.runtimeApplyPayload?.offDeviceUpload === false,
      `payloadSchema=${generatedPackage.runtimeApplyPayload?.schemaVersion}`,
    );
    addCheck(
      'package.uv_mask_nonempty',
      uvStats.bytes === uvStats.expectedBytes &&
        uvStats.nonzeroAlpha > 0 &&
        uvStats.strongAlpha > 0,
      `bytes=${uvStats.bytes}/${uvStats.expectedBytes} nonzeroAlpha=${uvStats.nonzeroAlpha} strongAlpha=${uvStats.strongAlpha} edgeBandAlpha=${uvStats.edgeBandAlpha} edgeBandRatio=${uvStats.edgeBandRatio.toFixed(4)} maxAlpha=${uvStats.maxAlpha} bbox=${JSON.stringify(uvStats.bbox)}`,
      { uvStats },
    );
    const fixtureHasUvQualityMetrics =
      Number(generatedPackage.uvCoverageMetadata?.uvResolution ?? 0) >= 512 &&
      Number(generatedPackage.runtimeApplyPayload?.maskTextureWidth ?? 0) >= 512 &&
      Number(generatedPackage.runtimeApplyPayload?.maskTextureHeight ?? 0) >= 512 &&
      Number(generatedPackage.uvCoverageMetadata?.edgeBandRatio ?? -1) >= 0 &&
      Number(generatedPackage.uvCoverageMetadata?.innerHolePositiveRatio ?? 1) <= 0.05 &&
      Number(generatedPackage.uvCoverageMetadata?.previewVsUvRoundTripDelta ?? 1) <= 0.5;
    const sourceHasUvQualityMetrics = matchesAll(personalizedPipelineSource, [
      /GENERATED_UV_MASK_RESOLUTION\s*=\s*512/,
      /GENERATED_UV_SUPERSAMPLE_GRID\s*=\s*2/,
      /edgeBandRatio/,
      /innerHolePositiveRatio/,
      /previewVsUvRoundTripDelta/,
    ]);
    addCheck(
      'package.uv_mask_quality_metrics',
      fixtureHasUvQualityMetrics || sourceHasUvQualityMetrics,
      `fixtureReady=${fixtureHasUvQualityMetrics ? 'yes' : 'no'} sourceReady=${sourceHasUvQualityMetrics ? 'yes' : 'no'} uvResolution=${generatedPackage.uvCoverageMetadata?.uvResolution ?? 'missing'} texture=${generatedPackage.runtimeApplyPayload?.maskTextureWidth ?? 0}x${generatedPackage.runtimeApplyPayload?.maskTextureHeight ?? 0} edgeBandRatio=${generatedPackage.uvCoverageMetadata?.edgeBandRatio ?? 'missing'} innerHolePositiveRatio=${generatedPackage.uvCoverageMetadata?.innerHolePositiveRatio ?? 'missing'} previewVsUvRoundTripDelta=${generatedPackage.uvCoverageMetadata?.previewVsUvRoundTripDelta ?? 'missing'}`,
      {
        uvCoverageMetadata: generatedPackage.uvCoverageMetadata,
        runtimeApplyPayload: {
          maskTextureWidth: generatedPackage.runtimeApplyPayload?.maskTextureWidth,
          maskTextureHeight: generatedPackage.runtimeApplyPayload?.maskTextureHeight,
        },
      },
    );
    addCheck(
      'package.saved_record_is_not_apply_proof',
      savedRecord.status === 'saved_local_only' &&
        savedRecord.runtimeReady === false,
      `status=${savedRecord.status} runtimeReady=${savedRecord.runtimeReady}`,
    );
    addCheck(
      'fixture.arface_mesh_uv_ready',
      Array.isArray(arFaceExport.screenVertices) &&
        arFaceExport.screenVertices.length >= 1000 &&
        Array.isArray(arFaceExport.uvs) &&
        arFaceExport.uvs.length >= 1000 &&
        Array.isArray(arFaceExport.indices) &&
        arFaceExport.indices.length >= 3000,
      `screenVertices=${arFaceExport.screenVertices?.length ?? 0} uvs=${arFaceExport.uvs?.length ?? 0} indices=${arFaceExport.indices?.length ?? 0}`,
    );
    if (previewPaths) {
      addCheck(
        'report.actual_package_preview_written',
        exists(previewPaths.svgPath) && exists(previewPaths.htmlPath),
        `${path.relative(repoRoot, previewPaths.htmlPath)} / ${path.relative(repoRoot, previewPaths.svgPath)}`,
      );
    }
  }

  const rnFocusedProofSource = [
    safeReadText(rnAppTestPath),
    readTextFilesUnder(
      path.join(repoRoot, 'rn', 'MakeupARValidation', '__tests__'),
    ),
    readTextFilesUnder(
      path.join(repoRoot, 'rn', 'MakeupARValidation', 'scripts'),
    ),
  ].join('\n');
  const rnPackage = exists(rnPackagePath) ? readJson(rnPackagePath) : {};

  const hasFakePreviewHelper = /function\s+buildGeneratedMaskPreviewStyle/.test(
    rnAppSource,
  );
  const hasRoundedRectPreviewStyle =
    /generatedAdjustmentMaskOverlay\s*:\s*\{[\s\S]*?borderRadius\s*:\s*999/.test(
      rnAppSource,
    );
  addCheck(
    'rn.preview_no_fake_bbox_overlay',
    !hasFakePreviewHelper && !hasRoundedRectPreviewStyle,
    hasFakePreviewHelper || hasRoundedRectPreviewStyle
      ? 'RN still contains bbox/rounded-rect generated mask preview. Build would show a fake pill instead of the actual lip mask.'
      : 'No bbox rounded-rect preview helper found.',
  );
  addCheck(
    'rn.preview_native_png_contract',
    /renderLipMaskPreview/.test(rnAppSource) &&
      /previewUri|maskPreviewUri|generatedPreviewUri/.test(rnAppSource),
    'RN must display a preview image generated from generated_lip_package.json, not a hand-drawn bbox View.',
  );
  addCheck(
    'ios.native_preview_method_exported',
    /@objc\(renderLipMaskPreview:resolver:rejecter:\)/.test(
      nativeProviderSource,
    ) &&
      /RCT_EXTERN_METHOD\(renderLipMaskPreview/.test(nativeBridgeSource),
    'Native iOS preview helper must render the actual lipBoundary2D to a file:// PNG for RN.',
  );
  addCheck(
    'rn.flow_ack_gate_present',
    /generated_lip_mask_applied/.test(rnAppSource) &&
      /maskTriangles/.test(rnAppSource) &&
      /uvAvailable/.test(rnAppSource) &&
      /(generatedApplyState\s*===\s*['"]applied['"]|generatedApplyState\.status\s*===\s*['"]applied['"])/.test(
        rnAppSource,
      ),
    'RN apply success must depend on Unity ack with applied=true, uvAvailable=true, maskTriangles>0.',
  );
  addCheck(
    'rn.copy_blending_not_compare',
    /블렌딩 선택/.test(rnAppSource) && !/Compare/.test(rnAppSource),
    'Product UI should say 블렌딩 선택, and Compare should stay out of the active flow.',
  );
  addCheck(
    'rn.package_script_registered',
    Boolean(rnPackage.scripts?.['e7:prebuild']),
    'rn/MakeupARValidation/package.json should expose npm run e7:prebuild.',
  );

  const smoothingContractRequirements = [
    { label: 'curve_densified_v1', pattern: /curve_densified_v1/ },
    { label: 'originalPointCount', pattern: /originalPointCount/ },
    { label: 'smoothedPointCount', pattern: /smoothedPointCount/ },
    {
      label: 'packageBoundary',
      pattern:
        /lipBoundary2D\s*:\s*smoothedAdjustedBoundary|lipBoundary2D[\s\S]{0,300}(curve_densified_v1|boundarySmoothing|smoothedPointCount)/,
    },
    {
      label: 'uvDiagnostics',
      pattern:
        /uvCoverageMetadata[\s\S]{0,700}(boundarySmoothing|smoothedPointCount|originalPointCount|alphaChecksum)/,
    },
  ];
  const smoothingCountProofSource = [
    personalizedPipelineSource,
    rnFocusedProofSource,
  ].join('\n');
  const hasSmoothingPointGrowthProof = matchesAny(smoothingCountProofSource, [
    /smoothedPointCount[\s\S]{0,180}>[\s\S]{0,120}originalPointCount/,
    /originalPointCount[\s\S]{0,180}<[\s\S]{0,120}smoothedPointCount/,
    /expect\([\s\S]{0,120}smoothedPointCount[\s\S]{0,120}\)\.toBeGreaterThan\([\s\S]{0,120}originalPointCount[\s\S]{0,20}\)/,
    /smoothedPointCount[\s\S]{0,180}toBeGreaterThan\([\s\S]{0,120}originalPointCount/,
  ]);
  addCheck(
    'v2.boundary_smoothing_ts_contract',
    matchesAll(
      personalizedPipelineSource,
      smoothingContractRequirements.map(item => item.pattern),
    ) && hasSmoothingPointGrowthProof,
    `TS package path must record curve_densified_v1, carry smoothing metadata into lipBoundary2D/UV diagnostics, and prove smoothedPointCount > originalPointCount. ${patternPresenceDetail(personalizedPipelineSource, smoothingContractRequirements)} pointGrowthProof=${hasSmoothingPointGrowthProof ? 'yes' : 'no'}`,
  );
  addCheck(
    'v2.unity_raw_uv_texture_origin',
    /function\s+uvToIndex[\s\S]{0,220}row\s*=\s*Math\.round\(\s*v\s*\*\s*\(\s*resolution\s*-\s*1\s*\)\s*\)/.test(
      personalizedPipelineSource,
    ) &&
      !/function\s+uvToIndex[\s\S]{0,220}row\s*=\s*Math\.round\(\s*\(\s*1\s*-\s*v\s*\)/.test(
        personalizedPipelineSource,
      ),
    'Generated raw RGBA UV masks must use Unity Texture2D bottom-left row order; using 1-v here vertically flips the AR mask onto the wrong face region.',
  );

  const renderPreviewUsesSmoothPath =
    /renderLipMaskPreview[\s\S]{0,5000}(appendSmoothClosedCurve|addCurve\s*\(|addQuadCurve\s*\()/i.test(
      nativeProviderSource,
    );
  const swiftPreviewCurveOk =
    /@objc\(renderLipMaskPreview:resolver:rejecter:\)/.test(
      nativeProviderSource,
    ) &&
    renderPreviewUsesSmoothPath &&
    matchesAny(nativeProviderSource, [
      /addCurve\s*\(/,
      /addQuadCurve\s*\(/,
      /CGPath[\s\S]{0,120}curve/i,
    ]) &&
    matchesAny(nativeProviderSource, [
      /smooth/i,
      /curve/i,
      /densif/i,
      /catmull/i,
    ]);
  addCheck(
    'v2.boundary_smoothing_swift_preview_curve',
    swiftPreviewCurveOk,
    swiftPreviewCurveOk
      ? 'Swift renderLipMaskPreview uses a smooth closed curve path for lip boundaries; any addLine helper should remain fallback-only for too few points.'
      : `Swift renderLipMaskPreview must draw a smooth closed curve for lip boundaries. renderUsesSmooth=${renderPreviewUsesSmoothPath ? 'yes' : 'no'} addCurve=${/(addCurve\s*\(|addQuadCurve\s*\()/.test(nativeProviderSource) ? 'yes' : 'no'}`,
  );

  const adjustmentProofCorpus = [
    rnFocusedProofSource,
    personalizedPipelineSource,
    nativeProviderSource,
  ].join('\n');
  const hasAdjustmentDeltaMarker = matchesAny(adjustmentProofCorpus, [
    /e7_v2_adjustment_preview_package_uv_delta/i,
    /adjustment[_-]?preview[_-]?delta/i,
    /uv[_-]?alpha[_-]?delta/i,
    /alpha\s+distribution[\s\S]{0,120}change/i,
    /alpha(?:Checksum|Sum)[\s\S]{0,180}(not\.(?:toEqual|toBe)|!==|diff|delta|change)/i,
    /maskRawRgbaBase64[\s\S]{0,220}(not\.(?:toEqual|toBe)|!==|diff|delta|change)/i,
    /(previewUri|preview\s+revision|preview\s+hash)[\s\S]{0,220}(not\.(?:toEqual|toBe)|!==|diff|delta|change)/i,
  ]);
  const hasAdjustedPackageRebuildMarker = matchesAny(adjustmentProofCorpus, [
    /selectedCandidate\.package/i,
    /selectedGeneratedCandidate[\s\S]{0,180}package/i,
    /rebuilt\s+adjusted\s+package/i,
    /adjusted\s+package\s+rebuild/i,
    /same\s+adjusted\s+boundary/i,
    /buildGeneratedLipPackage[\s\S]{0,180}adjustment/i,
  ]);
  const hasAdjustmentPreviewRevisionMarker = matchesAny(adjustmentProofCorpus, [
    /formatAdjustmentHash[\s\S]{0,260}generatedMaskId/i,
    /generatedMaskId[\s\S]{0,260}formatAdjustmentHash/i,
    /preview(?:Uri|Revision|Hash)[\s\S]{0,220}(adjustment|generatedMaskId|hash)/i,
    /e7-generated-lip-previews[\s\S]{0,220}generatedMaskId/i,
  ]);
  addCheck(
    'v2.adjustment_preview_package_uv_delta_proof',
    hasAdjustmentDeltaMarker &&
      hasAdjustedPackageRebuildMarker &&
      hasAdjustmentPreviewRevisionMarker,
    `Need a focused test/check or explicit marker proving adjustment rebuilds the selected package, changes preview/cache identity, and changes UV alpha. rebuildProof=${hasAdjustedPackageRebuildMarker ? 'yes' : 'no'} deltaProof=${hasAdjustmentDeltaMarker ? 'yes' : 'no'} previewRevisionProof=${hasAdjustmentPreviewRevisionMarker ? 'yes' : 'no'}`,
  );

  const hasCurrentPhotoRegenerate = matchesAny(rnAppSource, [
    /현재\s*사진으로\s*다시\s*생성/,
    /regenerate\s+(?:from\s+)?current\s+(?:photo|frame|capture)/i,
    /same\s+captured\s+frame[\s\S]{0,120}regenerat/i,
  ]);
  const hasRetake = matchesAny(rnAppSource, [
    /다시\s*촬영/,
    /\bretake\b/i,
    /new\s+capture/i,
  ]);
  const oldRegenerateLabelRemoved = !/경계\s*다시\s*추출/.test(rnAppSource);
  const hasApplyStateClear = matchesAny(rnAppSource, [
    /setGeneratedApplyState\s*\(\s*['"]idle['"]\s*\)/,
    /setGeneratedApplyState\s*\(\s*createGeneratedApplyState\s*\(\s*['"]idle['"]\s*\)/,
    /setGeneratedApplyState\s*\(\s*\{[\s\S]{0,120}status\s*:\s*['"]idle['"]/,
  ]);
  const hasPendingApplyClear = matchesAny(rnAppSource, [
    /setPendingGeneratedMaskId\s*\(\s*(?:undefined|null|['"]['"])\s*\)/,
    /pendingGeneratedMaskId[\s\S]{0,160}(?:undefined|null)/,
  ]);
  addCheck(
    'v2.regenerate_retake_clear_state',
    hasCurrentPhotoRegenerate &&
      hasRetake &&
      oldRegenerateLabelRemoved &&
      hasApplyStateClear &&
      hasPendingApplyClear,
    `Regenerate and retake must be separate and clear stale apply state. currentPhotoRegenerate=${hasCurrentPhotoRegenerate ? 'yes' : 'no'} retake=${hasRetake ? 'yes' : 'no'} oldLabelRemoved=${oldRegenerateLabelRemoved ? 'yes' : 'no'} applyStateClear=${hasApplyStateClear ? 'yes' : 'no'} pendingMaskClear=${hasPendingApplyClear ? 'yes' : 'no'}`,
  );

  const hasCaptureSetNativeExtraction = matchesAny(rnAppSource, [
    /capturedShotKinds[\s\S]{0,400}invokeNativeBoundaryProvider\s*\(\s*lipGenerateProvider\s*,\s*shotKind\s*\)/,
    /E7_CAPTURE_SHOT_OPTIONS[\s\S]{0,500}extractLipBoundary/,
  ]);
  const hasCaptureSetPackageEvidence = matchesAll(rnAppSource, [
    /nativeProviderShotResults/,
    /providerShotResults/,
  ]) && matchesAll(personalizedPipelineSource, [
    /captureSetShotResults/,
    /blendshape_assist_capture_set_summary/,
    /captureSetShotCount/,
  ]);
  addCheck(
    'v2.capture_set_used_for_blendshape_assist',
    hasCaptureSetNativeExtraction && hasCaptureSetPackageEvidence,
    `The n-shot capture flow must feed generation, not only gate UI. nativeExtraction=${hasCaptureSetNativeExtraction ? 'yes' : 'no'} packageEvidence=${hasCaptureSetPackageEvidence ? 'yes' : 'no'}`,
  );

  const captureTimeoutAndPreviewReady = matchesAll(rnAppSource, [
    /E7_CAPTURE_ACK_TIMEOUT_MS/,
    /촬영 응답이 늦습니다/,
    /framePreviewUri/,
    /capturedFrameImage/,
  ]) && /framePreviewUri/.test(unityBridgeSource + unityCaptureExporterSource);
  addCheck(
    'v2.capture_timeout_and_captured_frame_preview',
    captureTimeoutAndPreviewReady,
    `Capture flow must recover from missing Unity capture events and show the saved captured frame, not only a dark live-camera shield. ready=${captureTimeoutAndPreviewReady ? 'yes' : 'no'}`,
  );

  const applyStateRequirements = [
    { label: 'idle', pattern: /['"]idle['"]/ },
    { label: 'saving', pattern: /['"]saving['"]/ },
    { label: 'posting', pattern: /['"]posting['"]/ },
    { label: 'waitingAck', pattern: /['"]waitingAck['"]/ },
    { label: 'applied', pattern: /['"]applied['"]/ },
    { label: 'blocked', pattern: /['"]blocked['"]/ },
    { label: 'timeout', pattern: /['"]timeout['"]/ },
    { label: 'reason', pattern: /\b(blockedReason|reason|errorReason|timeoutReason)\b/ },
  ];
  const hasTimeoutMechanism = matchesAny(rnAppSource, [
    /setTimeout\s*\(/,
    /timeoutMs\b/i,
    /elapsedMs\b/i,
    /ackTimeout/i,
  ]);
  const hasAckMatching = /generated_lip_mask_applied/.test(rnAppSource) &&
    /generatedMaskId/.test(rnAppSource);
  addCheck(
    'v2.apply_loading_timeout_reason_states',
    matchesAll(rnAppSource, applyStateRequirements.map(item => item.pattern)) &&
      hasTimeoutMechanism &&
      hasAckMatching,
    `Apply state must include loading/posting/waitingAck/applied/blocked/timeout with user-readable reason and generatedMaskId matching. ${patternPresenceDetail(rnAppSource, applyStateRequirements)} timeoutMechanism=${hasTimeoutMechanism ? 'yes' : 'no'} ackMatching=${hasAckMatching ? 'yes' : 'no'}`,
  );

  const generatedValidationControlRequirements = [
    {
      label: 'onOff',
      pattern: /ON\s*\/\s*OFF|mask\s*(?:on|off)|maskEnabled|generated-mask-toggle|마스크\s*(?:켜기|끄기)/i,
    },
    {
      label: 'strong',
      pattern: /strong|validationStrong|strongValidation|진하게|강하게/i,
    },
    {
      label: 'color',
      pattern: /color\s*swatch|generated-mask-color|validationColor|색상|컬러/i,
    },
    {
      label: 'opacity',
      pattern: /opacity|generated-mask-opacity|불투명|투명도/i,
    },
  ];
  const hasGeneratedValidationAnchor = matchesAny(rnAppSource, [
    /Generated(?:Mask|Ar|AR)Validation(?:Bar|Controls)/,
    /e7-generated-ar-validation/i,
    /generated-mask-(?:toggle|opacity|color|strong)/i,
  ]);
  const hasControlsNearAppliedState = anyWindowMatchesAll(
    rnAppSource,
    [
      /generatedApplyState[\s\S]{0,80}['"]applied['"]/,
      /hasGeneratedMaskApplied/,
      /GeneratedRuntimeAppliedBanner/,
    ],
    generatedValidationControlRequirements.map(item => item.pattern),
    2200,
  );
  addCheck(
    'v2.ar_validation_controls_present',
    (hasGeneratedValidationAnchor || hasControlsNearAppliedState) &&
      matchesAll(rnAppSource, generatedValidationControlRequirements.map(item => item.pattern)),
    `Post-applied generated mask UI must expose ON/OFF, strong validation mode, color, and opacity controls. anchor=${hasGeneratedValidationAnchor ? 'yes' : 'no'} nearApplied=${hasControlsNearAppliedState ? 'yes' : 'no'} ${patternPresenceDetail(rnAppSource, generatedValidationControlRequirements)}`,
  );

  const validationControlAckReady = matchesAll(rnAppSource, [
    /pendingGeneratedControlCheck/,
    /doesGeneratedControlAckMatch/,
    /controlRequestId/,
    /generated_lip_mask_control_ack_mismatch/,
    /postRegionOverlayVisibility\(\s*nextControls\.maskVisible/,
    /GENERATED_CONTROL_ACK_TIMEOUT_MS/,
    /AR 검증 변경이 반영되었습니다/,
    /AR 검증 변경 확인이 늦습니다/,
  ]) && matchesAll(unityBridgeSource, [
    /controlRequestId/,
    /validationControlRequestId/,
    /validationControls[\s\S]{0,240}controlRequestId/,
  ]);
  addCheck(
    'v2.ar_validation_controls_ack_confirmed',
    validationControlAckReady,
    `AR validation controls must wait for a matching generated-mask ack or show a delayed confirmation state. ready=${validationControlAckReady ? 'yes' : 'no'}`,
  );

  const userFacingDeveloperCopyRemoved = [
    /fixture replay/,
    /capture directory/,
    /saved:\s*\{/,
    /reason:\s*\{/,
    /AR 립 적용 중/,
    /입술 미세 조정/,
    /native 경계 추출/,
    /Debug에서 persisted ack/,
    /Debug에서 원인/,
    /Unity generated_lip_mask_applied ack/,
    /Unity 적용 실패 또는 미확인/,
    /provider blockedReason/,
    /actual mask preview/,
    /실제 mask preview/,
    /전체 얼굴 기준 mask overlay/,
    /새 frame\.png \/ arface_export\.json/,
  ].every(pattern => !pattern.test(rnAppSource));
  const userFacingArCopyPresent = matchesAll(rnAppSource, [
    /AR 립 검증/,
    /AR 립 적용됨/,
    /AR 화면입니다/,
    /AR 적용 응답이 늦습니다/,
    /AR 화면에서 적용 확인을 기다립니다/,
    /전체 얼굴 기준 마스크 미리보기/,
    /마스크 ON/,
    /진하게 보기/,
    /경계 보기/,
    /농도/,
  ]);
  addCheck(
    'v2.user_facing_ar_copy_no_developer_terms',
    userFacingDeveloperCopyRemoved && userFacingArCopyPresent,
    `User-facing Generate/AR copy must avoid developer terms and clearly communicate AR transition. oldTermsRemoved=${userFacingDeveloperCopyRemoved ? 'yes' : 'no'} arCopy=${userFacingArCopyPresent ? 'yes' : 'no'}`,
  );

  addCheck(
    'v2.preview_images_show_full_face',
    /generateWizardCandidatePreviewImage:\s*{[\s\S]*?resizeMode:\s*['"]contain['"]/.test(
      rnAppSource,
    ) &&
      /generatedAdjustmentPreviewImage:\s*{[\s\S]*?resizeMode:\s*['"]contain['"]/.test(
        rnAppSource,
      ),
    'Generated candidate and adjustment previews must use contain, not cover, so full-face mask quality is inspectable before build.',
  );

  const candidatePreviewLargeEnough = matchesAll(rnAppSource, [
    /generateWizardCandidateCard:\s*{[\s\S]*?width:\s*282/,
    /generateWizardCandidatePreview:\s*{[\s\S]*?height:\s*286/,
    /generatedAdjustmentPreviewImage:\s*{[\s\S]*?height:\s*300/,
  ]);
  addCheck(
    'v2.preview_cards_large_enough_for_quality_judgment',
    candidatePreviewLargeEnough,
    `Candidate and adjustment previews should remain large enough for picky visual review. largePreview=${candidatePreviewLargeEnough ? 'yes' : 'no'}`,
  );

  addCheck(
    'unity.source_persists_generated_ack',
    /e7-runtime-events/.test(unityBridgeSource) &&
      /generated_lip_mask_applied\.latest\.json/.test(unityBridgeSource) &&
      /generated_lip_mask_applied\.jsonl/.test(unityBridgeSource),
    'Unity RNBridge source must persist generated_lip_mask_applied latest/jsonl.',
  );
  addCheck(
    'unity.source_ack_success_contract',
    /result\.Applied/.test(unityBridgeSource) &&
      /result\.UvAvailable/.test(unityBridgeSource) &&
      /result\.MaskTriangleCount\s*>\s*0/.test(unityBridgeSource),
    'Unity ack success must require Applied, UV, and maskTriangles.',
  );
  addCheck(
    'unity.framework_contains_ack_persistence',
    fileContainsBytes(unityFrameworkPath, 'e7-runtime-events') &&
      fileContainsBytes(
        unityFrameworkPath,
        'generated_lip_mask_applied.latest.json',
      ) &&
      fileContainsBytes(
        unityFrameworkPath,
        'overlaySyncPhase',
      ) &&
      (
        fileContainsBytes(
          unityFrameworkPath,
          'validationControlRequestId',
        ) ||
        fileContainsBytes(
          unityFrameworkPath,
          'controlRequestId',
        )
      ),
    exists(unityFrameworkPath)
      ? 'UnityFramework must contain current RNBridge ack persistence, overlay sync, and control request strings. If this fails, rebuild/sync UnityFramework before Xcode.'
      : `missing ${unityFrameworkPath}`,
  );

  if (runChildChecks) {
    if (exists(rnNativeCheckPath)) {
      const child = runNodeCheck(
        'rn native Generate static checks',
        [rnNativeCheckPath],
        path.dirname(rnPackagePath),
      );
      addCheck(
        'child.rn_native_generate_check',
        child.ok,
        child.ok ? child.stdout : `${child.stdout}\n${child.stderr}`,
        { childStatus: child.status },
      );
    } else {
      addWarn('child.rn_native_generate_check', 'script missing');
    }
  } else {
    addWarn(
      'child.checks_skipped',
      'Pass --run-checks to also run child static scripts. Default gate stays fast for edit loops.',
    );
  }

  const failed = checks.filter(check => check.status === 'fail');
  const warned = checks.filter(check => check.status === 'warn');
  const passed = checks.filter(check => check.status === 'pass');
  const summary = {
    schemaVersion: 'e7-prebuild-gate-report-v0',
    createdAt: new Date().toISOString(),
    repoRoot,
    fixtureRoot,
    result: failed.length === 0 ? 'pass' : 'fail',
    counts: {
      pass: passed.length,
      fail: failed.length,
      warn: warned.length,
    },
    checks,
  };

  if (writeReport) {
    fs.mkdirSync(reportDir, { recursive: true });
    fs.writeFileSync(
      path.join(reportDir, 'gate-report.json'),
      JSON.stringify(summary, null, 2),
    );
    fs.writeFileSync(path.join(reportDir, 'gate-report.md'), renderMarkdown(summary));
  }

  for (const check of checks) {
    const mark =
      check.status === 'pass' ? 'ok' : check.status === 'warn' ? 'WARN' : 'FAIL';
    console.log(`[e7-prebuild] ${mark} ${check.id} - ${check.detail}`);
  }
  console.log(
    `[e7-prebuild] result=${summary.result} pass=${passed.length} fail=${failed.length} warn=${warned.length}`,
  );
  if (writeReport) {
    console.log(
      `[e7-prebuild] report=${path.relative(repoRoot, path.join(reportDir, 'gate-report.md'))}`,
    );
  }
  if (failed.length > 0) {
    process.exit(1);
  }
}

function renderMarkdown(summary) {
  const lines = [
    '# E7 Prebuild Gate Report',
    '',
    `- result: ${summary.result}`,
    `- createdAt: ${summary.createdAt}`,
    `- fixture: ${path.relative(repoRoot, summary.fixtureRoot)}`,
    `- pass/fail/warn: ${summary.counts.pass}/${summary.counts.fail}/${summary.counts.warn}`,
    '',
    '## Checks',
    '',
    'The `v2.*` checks are targeted fix-build v2 blockers. They are buildless/source/fixture checks only: passing them means the next Xcode build is less likely to repeat the known preview/adjust/apply/control failures, not that the mask was accepted on device.',
    '',
    '| Status | Check | Detail |',
    '| --- | --- | --- |',
  ];
  for (const check of summary.checks) {
    lines.push(
      `| ${check.status} | ${check.id} | ${String(check.detail).replaceAll('\n', '<br>').replaceAll('|', '\\|')} |`,
    );
  }
  lines.push(
    '',
    '## Preview',
    '',
    '- `mask-preview.html` renders the actual `generated_lip_package.json` boundary over the captured iPhone frame.',
    '- If RN shows anything materially different, do not run Xcode build.',
    '- v2 still requires later real-device flow evidence for capture, extraction, blending, adjustment, save/apply ack, AR controls, and visual acceptance.',
    '',
  );
  return lines.join('\n');
}

runMain();
