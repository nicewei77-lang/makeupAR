import { execFileSync } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

function assert(condition, message) {
  if (!condition) {
    throw new Error(message);
  }
}

const scriptDir = dirname(fileURLToPath(import.meta.url));
const packageRoot = resolve(scriptDir, "..");
const tscBin = resolve(
  packageRoot,
  "../../rn/MakeupARValidation/node_modules/.bin/tsc"
);
const outDir = mkdtempSync(join(tmpdir(), "lip-generate-core-validation-"));

function buildPackage(overrides = {}) {
  const runtimeApplyPayload = {
    schemaVersion: "e7-generated-lip-mask-runtime-payload-v0",
    generatedMaskId: "validation-gate-smoke",
    captureSetId: "validation-capture-set",
    provider: "vision",
    expressionMode: "uvOnly",
    adjustment: {
      cornerReach: 0,
      upperLipTightness: 0,
      lowerLipTightness: 0,
      verticalOffset: 0,
      innerFill: 0,
      upperInnerFill: 0,
    },
    maskTextureId: "validation-gate-smoke",
    maskTextureEncoding: "raw_rgba_base64",
    maskRawRgbaBase64: "AAAA",
    maskTextureWidth: 1,
    maskTextureHeight: 1,
    maskThreshold: 0.5,
    maskFeatherUvNormalized: 0.07,
    localOnly: true,
    offDeviceUpload: false,
    longTermRawFrameStored: false,
    runtimeReady: false,
    ...(overrides.runtimeApplyPayload ?? {}),
  };
  const privacyFlags = {
    localOnly: true,
    offDeviceUpload: false,
    longTermRawFrameStored: false,
    ...(overrides.privacyFlags ?? {}),
  };

  return {
    schemaVersion: "e7-personalized-lip-generate-package-v0",
    generatedMaskId: "validation-gate-smoke",
    captureSetId: "validation-capture-set",
    provider: "vision",
    providerResults: {
      vision: {
        status: "ready",
        provider: "vision",
        capturePairId: "validation-pair",
        captureShotKind: "neutral",
        frameWidth: 1,
        frameHeight: 1,
        outerPointCount: 20,
        innerPointCount: 20,
        generationMethod: "validation",
        warnings: [],
      },
    },
    expressionMode: "uvOnly",
    blendshapeAssist: {
      mode: "uvOnly",
      enabled: false,
      source: "arface-blendshapes",
      materialFeatherUvNormalized: 0.07,
      warning: "validation",
    },
    adjustment: runtimeApplyPayload.adjustment,
    sourceFrameMetadata: {
      framePath: "fixture/frame.png",
      frameWidth: 1,
      frameHeight: 1,
    },
    sourceFaceState: {
      blendshapeAvailable: false,
    },
    lipBoundary2D: {
      coordinateSpace: "frame_image_pixel_top_left",
      outerPoints: [],
      innerPoints: [],
      source: "vision",
    },
    uvMaskTexture: "fixture/uv.png",
    uvCoverageMetadata: {
      uvResolution: 1,
      roundTripKind: "held_out_projection",
    },
    roundTripPreview: "fixture/round-trip.png",
    runtimeApplyPayload,
    qualityWarnings: [],
    createdAt: "2026-06-27T00:00:00.000Z",
    privacyFlags,
    ...overrides.package,
  };
}

try {
  execFileSync(
    tscBin,
    [
      "-p",
      join(packageRoot, "tsconfig.json"),
      "--outDir",
      outDir,
      "--declaration",
      "false",
      "--module",
      "CommonJS",
      "--target",
      "ES2022",
    ],
    { cwd: packageRoot, stdio: "inherit" }
  );

  const { validateGeneratedPackage } = await import(
    pathToFileURL(join(outDir, "validationGates.js")).href
  );

  const cleanGate = validateGeneratedPackage(buildPackage());
  assert(
    cleanGate.status === "ready",
    `expected clean package to be ready, got ${cleanGate.status}`
  );

  const uploadGate = validateGeneratedPackage(
    buildPackage({
      runtimeApplyPayload: {
        offDeviceUpload: true,
      },
    })
  );
  assert(
    uploadGate.blockers.includes(
      "runtime_payload.privacy.offDeviceUpload_must_be_false"
    ),
    "runtimeApplyPayload.offDeviceUpload=true must block generated package"
  );

  const storedFrameGate = validateGeneratedPackage(
    buildPackage({
      privacyFlags: {
        longTermRawFrameStored: true,
      },
    })
  );
  assert(
    storedFrameGate.blockers.includes(
      "package_privacy_flags.privacy.longTermRawFrameStored_must_be_false"
    ),
    "privacyFlags.longTermRawFrameStored=true must block generated package"
  );

  const pngEncodingGate = validateGeneratedPackage(
    buildPackage({
      runtimeApplyPayload: {
        maskTextureEncoding: "png_base64",
        maskRawRgbaBase64: undefined,
        maskPngBase64: "AAAA",
      },
    })
  );
  assert(
    pngEncodingGate.blockers.includes(
      "runtime_payload.maskTextureEncoding_must_be_raw_rgba_base64"
    ),
    "runtimeApplyPayload.maskTextureEncoding=png_base64 must block generated package"
  );
  assert(
    pngEncodingGate.blockers.includes(
      "runtime_payload.missing_maskRawRgbaBase64"
    ),
    "runtimeApplyPayload.maskRawRgbaBase64 is required for Unity runtime payload"
  );

  const invalidSizeGate = validateGeneratedPackage(
    buildPackage({
      runtimeApplyPayload: {
        maskTextureWidth: 0,
        maskTextureHeight: -1,
      },
    })
  );
  assert(
    invalidSizeGate.blockers.includes(
      "runtime_payload.invalid_maskTextureWidth"
    ),
    "runtimeApplyPayload.maskTextureWidth must be positive"
  );
  assert(
    invalidSizeGate.blockers.includes(
      "runtime_payload.invalid_maskTextureHeight"
    ),
    "runtimeApplyPayload.maskTextureHeight must be positive"
  );

  console.log("[lip-generate-core] validation gates ok");
} finally {
  rmSync(outDir, { force: true, recursive: true });
}
