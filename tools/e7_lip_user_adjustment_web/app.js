"use strict";

const REVIEW_SCHEMA_VERSION = "e7-lip-user-adjustment-review-v0";
const CANDIDATE_SCHEMA_VERSION = "e7-lip-user-adjustment-candidates-v0";
const PARAM_KEYS = [
  "cornerReach",
  "upperLipTightness",
  "lowerLipTightness",
  "verticalOffset",
];
const LEGACY_PARAM_KEYS = ["tightness", "upperLowerBalance", "cornerShrink"];
const DEFAULT_PARAMS = {
  cornerReach: 0,
  upperLipTightness: 0,
  lowerLipTightness: 0,
  verticalOffset: 0,
};
const CUSTOM_CANDIDATE_IDS = {
  slider: "ua-web-slider-custom",
};
const DEFAULT_SAMPLE_URL = "./local-assets/e7-user-adjustment-smoke/user_adjustment_candidates.json";
const DEFAULT_SAMPLE_ASSET_DIR = "./local-assets/e7-user-adjustment-smoke";
const LOCAL_SERVER_URL = "http://127.0.0.1:8787/tools/e7_lip_user_adjustment_web/";
const SHAPE_SCALE_INTENSITY = 1.15;

const PARAM_META = {
  cornerReach: {
    label: "cornerReach",
    help: "+ 입꼬리 쪽 확장, - 입꼬리 spill 축소",
  },
  upperLipTightness: {
    label: "upperLipTightness",
    help: "+ 윗입술을 타이트하게, - 윗입술 덮임 증가",
  },
  lowerLipTightness: {
    label: "lowerLipTightness",
    help: "+ 아랫입술을 타이트하게, - 아랫입술 덮임 증가",
  },
  verticalOffset: {
    label: "verticalOffset",
    help: "image-space 기준 + 아래, - 위",
  },
};

const state = {
  mode: "slider",
  candidatesPayload: null,
  candidates: [],
  selectedCandidateId: null,
  params: Object.assign({}, DEFAULT_PARAMS),
  assetUrls: new Map(),
  assetFiles: new Map(),
  imageCache: new Map(),
  assets: {
    frame: null,
    baseMask: null,
    upperMask: null,
    lowerMask: null,
    innerMask: null,
  },
  generatedMask: null,
  generatedMetrics: {},
  confirmed: false,
};

const els = {
  statusLine: document.getElementById("statusLine"),
  candidateJsonInput: document.getElementById("candidateJsonInput"),
  assetFolderInput: document.getElementById("assetFolderInput"),
  loadSampleButton: document.getElementById("loadSampleButton"),
  sliderControls: document.getElementById("sliderControls"),
  selectionPreview: document.getElementById("selectionPreview"),
  adjustmentCanvas: document.getElementById("adjustmentCanvas"),
  previewFallback: document.getElementById("previewFallback"),
  paramReadout: document.getElementById("paramReadout"),
  reviewJsonOutput: document.getElementById("reviewJsonOutput"),
  resetParamsButton: document.getElementById("resetParamsButton"),
  confirmButton: document.getElementById("confirmButton"),
  downloadReviewButton: document.getElementById("downloadReviewButton"),
  downloadCandidatesButton: document.getElementById("downloadCandidatesButton"),
  downloadMaskButton: document.getElementById("downloadMaskButton"),
};

function clamp(value, min = -1, max = 1) {
  return Math.max(min, Math.min(max, value));
}

function roundParam(value) {
  return Number(clamp(value).toFixed(2));
}

function copyParams(params) {
  return {
    cornerReach: Number(params.cornerReach || 0),
    upperLipTightness: Number(params.upperLipTightness || 0),
    lowerLipTightness: Number(params.lowerLipTightness || 0),
    verticalOffset: Number(params.verticalOffset || 0),
  };
}

function normalizePath(value) {
  return String(value || "").split("\\").join("/");
}

function basename(value) {
  return normalizePath(value)
    .split("/")
    .filter(Boolean)
    .pop();
}

function repoRelativeUrl(value) {
  const text = normalizePath(value);
  const markers = ["/evidence/", "/tools/", "/docs/", "/scripts/"];
  for (const marker of markers) {
    const index = text.indexOf(marker);
    if (index >= 0) {
      return `/${text.slice(index + 1)}`;
    }
  }
  return text.startsWith("evidence/") ? `/${text}` : null;
}

function localTmpAssetUrl(value) {
  const text = normalizePath(value);
  const privateTmpMarker = "/private/tmp/";
  const tmpMarker = "/tmp/";
  const privateIndex = text.indexOf(privateTmpMarker);
  if (privateIndex >= 0) {
    return `./local-assets/${text.slice(privateIndex + privateTmpMarker.length)}`;
  }
  const tmpIndex = text.indexOf(tmpMarker);
  if (tmpIndex >= 0) {
    return `./local-assets/${text.slice(tmpIndex + tmpMarker.length)}`;
  }
  return null;
}

function setStatus(message, tone = "neutral") {
  els.statusLine.textContent = message;
  els.statusLine.dataset.tone = tone;
}

function resolveAssetUrl(pathOrName) {
  const text = normalizePath(pathOrName);
  const name = basename(pathOrName);
  if (name && state.assetUrls.has(name)) {
    return state.assetUrls.get(name);
  }
  if (text.indexOf("./") === 0 || text.indexOf("local-assets/") === 0) {
    return text.indexOf("./") === 0 ? text : `./${text}`;
  }
  const localUrl = localTmpAssetUrl(pathOrName);
  if (localUrl) {
    return localUrl;
  }
  const repoUrl = repoRelativeUrl(pathOrName);
  return repoUrl || "";
}

function candidateById(candidateId) {
  return state.candidates.find((item) => item.candidateId === candidateId) || null;
}

function normalizeCandidate(item) {
  return {
    candidateId: item.candidateId,
    label: item.label || item.candidateId,
    params: Object.assign({}, DEFAULT_PARAMS, item.params || {}),
    maskPath: item.maskPath || item.selectedMaskPath || "",
    overlayPath: item.overlayPath || "",
    metrics: item.metrics || {},
  };
}

function setParam(key, value) {
  state.params[key] = roundParam(value);
  state.confirmed = false;
  renderSliders();
  syncAfterParamChange();
}

function renderSliders() {
  els.sliderControls.innerHTML = "";
  for (const key of PARAM_KEYS) {
    const row = document.createElement("div");
    row.className = "range-row";
    const label = document.createElement("label");
    label.htmlFor = `range-${key}`;
    label.textContent = PARAM_META[key].label;
    const help = document.createElement("small");
    help.textContent = PARAM_META[key].help;
    label.append(help);
    const decrement = document.createElement("button");
    decrement.type = "button";
    decrement.className = "step-button";
    decrement.textContent = "-";
    decrement.title = `${key} -0.05`;
    decrement.addEventListener("click", () => setParam(key, state.params[key] - 0.05));
    const input = document.createElement("input");
    input.id = `range-${key}`;
    input.type = "range";
    input.min = "-1";
    input.max = "1";
    input.step = "0.05";
    input.value = state.params[key];
    const value = document.createElement("span");
    value.className = "number-pill";
    value.textContent = state.params[key].toFixed(2);
    input.addEventListener("input", () => {
      state.params[key] = roundParam(Number(input.value));
      value.textContent = state.params[key].toFixed(2);
      state.confirmed = false;
      syncAfterParamChange();
    });
    const increment = document.createElement("button");
    increment.type = "button";
    increment.className = "step-button";
    increment.textContent = "+";
    increment.title = `${key} +0.05`;
    increment.addEventListener("click", () => setParam(key, state.params[key] + 0.05));
    row.append(label, decrement, input, increment, value);
    els.sliderControls.append(row);
  }
}

function renderParamReadout() {
  els.paramReadout.innerHTML = "";
  for (const key of PARAM_KEYS) {
    const dt = document.createElement("dt");
    dt.textContent = key;
    const dd = document.createElement("dd");
    dd.textContent = Number(state.params[key] || 0).toFixed(2);
    els.paramReadout.append(dt, dd);
  }
}

function renderPreview() {
  els.selectionPreview.style.display = "none";
  els.adjustmentCanvas.style.display = "none";
  els.previewFallback.style.display = "none";

  if (state.generatedMask) {
    drawAdjustmentPreview();
    els.adjustmentCanvas.style.display = "block";
    return;
  }

  const previewUrl = samplePreviewUrl();
  if (previewUrl) {
    els.selectionPreview.src = previewUrl;
    els.selectionPreview.style.display = "block";
  } else {
    els.previewFallback.style.display = "block";
  }
}

function samplePreviewUrl() {
  const selected = candidateById(state.selectedCandidateId) || state.candidates[0];
  if (selected && (selected.overlayPath || selected.maskPath)) {
    return resolveAssetUrl(selected.overlayPath || selected.maskPath);
  }
  return `${DEFAULT_SAMPLE_ASSET_DIR}/user_adjustment_candidate_ua-00-baseline_overlay.png`;
}

function buildReviewPayload() {
  const candidateId = CUSTOM_CANDIDATE_IDS.slider;
  const selectedMaskPath = `user_adjustment_candidate_${candidateId}_mask.png`;
  return {
    schemaVersion: REVIEW_SCHEMA_VERSION,
    status: state.confirmed ? "user_confirmed" : "needs_user_selection",
    confirmedByUser: state.confirmed,
    selectedCandidateId: candidateId,
    selectedMaskPath,
    params: copyParams(state.params),
    observedFixes: observedFixes(),
    knownWeaknesses: [
      "buildless_web_ui_experiment_only",
      "does_not_claim_runtime_ready",
    ],
    uiExperiment: {
      source: "tools/e7_lip_user_adjustment_web",
      mode: state.mode,
      usesCurrentContractKeys: PARAM_KEYS,
      legacyParamsNotAccepted: LEGACY_PARAM_KEYS,
    },
  };
}

function observedFixes() {
  const fixes = [];
  if (state.params.cornerReach > 0) fixes.push("corner_reach_extended");
  if (state.params.cornerReach < 0) fixes.push("corner_spill_reduced");
  if (state.params.upperLipTightness > 0) fixes.push("upper_lip_spill_tightened");
  if (state.params.upperLipTightness < 0) fixes.push("upper_lip_coverage_expanded");
  if (state.params.lowerLipTightness > 0) fixes.push("lower_lip_spill_tightened");
  if (state.params.lowerLipTightness < 0) fixes.push("lower_lip_coverage_expanded");
  if (state.params.verticalOffset < 0) fixes.push("vertical_offset_moved_up");
  if (state.params.verticalOffset > 0) fixes.push("vertical_offset_moved_down");
  if (!fixes.length) fixes.push("baseline_or_zero_adjustment_user_reviewed");
  return fixes;
}

function syncJsonOutput() {
  els.reviewJsonOutput.value = `${JSON.stringify(buildReviewPayload(), null, 2)}\n`;
}

async function readFileAsText(file) {
  return await file.text();
}

async function loadCandidateJson(file) {
  const payload = JSON.parse(await readFileAsText(file));
  await loadCandidatePayload(payload, file.name);
}

async function loadCandidatePayload(payload, sourceLabel) {
  state.candidatesPayload = payload;
  const sourceCandidates = payload.candidates || payload.candidateOptions || [];
  state.candidates = sourceCandidates.map(normalizeCandidate);
  const selected = (state.candidates[0] && state.candidates[0].candidateId) || null;
  state.selectedCandidateId = selected;
  if (selected) {
    state.params = Object.assign({}, DEFAULT_PARAMS, candidateById(selected).params);
  }
  state.confirmed = false;
  renderSliders();
  renderParamReadout();
  try {
    await loadBaseAssets();
  } catch {
    state.assets.frame = null;
    state.assets.baseMask = null;
    state.assets.upperMask = null;
    state.assets.lowerMask = null;
    state.assets.innerMask = null;
  }
  syncAfterParamChange();
  setStatus(`${sourceLabel} loaded. 샘플 미리보기가 자동으로 표시됩니다.`);
}

async function loadDefaultSample() {
  try {
    const response = await fetch(DEFAULT_SAMPLE_URL, { cache: "no-store" });
    if (response.ok) {
      await loadCandidatePayload(await response.json(), "sample user_adjustment_candidates.json");
      return;
    }
  } catch {
    // Fall through to the path-only sample so the UI is still usable when fetch is unavailable.
  }
  await loadCandidatePayload(defaultSamplePayload(), "built-in local sample paths");
}

function defaultSamplePayload() {
  return {
    schemaVersion: CANDIDATE_SCHEMA_VERSION,
    inputs: {
      framePath: "evidence/e7-reference-atlas/capture_pairs/pair_face_20260622T143334Z_03/frame.png",
      baseMaskPath: `${DEFAULT_SAMPLE_ASSET_DIR}/user_adjustment_candidate_ua-00-baseline_mask.png`,
      upperLipMaskPath: null,
      lowerLipMaskPath: null,
      innerMouthMaskPath: null,
    },
    candidates: [
      {
        candidateId: "ua-00-baseline",
        label: "baseline",
        params: Object.assign({}, DEFAULT_PARAMS),
        maskPath: `${DEFAULT_SAMPLE_ASSET_DIR}/user_adjustment_candidate_ua-00-baseline_mask.png`,
        overlayPath: `${DEFAULT_SAMPLE_ASSET_DIR}/user_adjustment_candidate_ua-00-baseline_overlay.png`,
        metrics: {},
      },
    ],
  };
}

function loadAssetFolder(files) {
  for (const url of state.assetUrls.values()) {
    URL.revokeObjectURL(url);
  }
  state.assetUrls.clear();
  state.assetFiles.clear();
  state.imageCache.clear();
  for (const file of files) {
    state.assetFiles.set(file.name, file);
    state.assetUrls.set(file.name, URL.createObjectURL(file));
  }
  loadBaseAssets().then(() => {
    syncAfterParamChange();
    setStatus(`${files.length} image/files loaded for preview.`);
  }).catch(() => {
    syncAfterParamChange();
    setStatus("출력 폴더 이미지를 일부 읽지 못했지만 샘플 미리보기로 계속 표시합니다.", "warn");
  });
}

async function loadImage(pathOrName) {
  const name = basename(pathOrName);
  const url = resolveAssetUrl(pathOrName);
  if (!url) return null;
  const key = `${name}:${url}`;
  if (state.imageCache.has(key)) return state.imageCache.get(key);
  const image = new Image();
  image.decoding = "async";
  const promise = new Promise((resolve, reject) => {
    image.onload = () => resolve(image);
    image.onerror = () => reject(new Error(`image_load_failed:${pathOrName}`));
  });
  image.src = url;
  await promise;
  state.imageCache.set(key, image);
  return image;
}

async function imageToMask(pathOrName, expectedSize = null) {
  const image = await loadImage(pathOrName);
  if (!image) return null;
  const width = image.naturalWidth || image.width;
  const height = image.naturalHeight || image.height;
  if (expectedSize && (width !== expectedSize.width || height !== expectedSize.height)) {
    return null;
  }
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.drawImage(image, 0, 0);
  const pixels = context.getImageData(0, 0, width, height).data;
  const data = new Uint8Array(width * height);
  for (let i = 0, j = 0; i < pixels.length; i += 4, j += 1) {
    data[j] = pixels[i] > 16 || pixels[i + 1] > 16 || pixels[i + 2] > 16 ? 1 : 0;
  }
  return { width, height, data };
}

async function loadBaseAssets() {
  const inputs = (state.candidatesPayload && state.candidatesPayload.inputs) || {};
  const baseline = candidateById("ua-00-baseline") || state.candidates[0] || {};
  const framePath = inputs.framePath || "frame.png";
  const basePath = inputs.baseMaskPath || baseline.maskPath || "lip-tight-auto-v0_mask.png";
  const upperPath = inputs.upperLipMaskPath || "face_parsing_upper_lip_mask.png";
  const lowerPath = inputs.lowerLipMaskPath || "face_parsing_lower_lip_mask.png";
  const innerPath = inputs.innerMouthMaskPath || "face_parsing_inner_mouth_mask.png";

  try {
    state.assets.frame = await loadImage(framePath);
  } catch {
    state.assets.frame = null;
  }
  state.assets.baseMask = await imageToMask(basePath);
  if (!state.assets.baseMask && baseline.maskPath && baseline.maskPath !== basePath) {
    state.assets.baseMask = await imageToMask(baseline.maskPath);
  }
  if (!state.assets.baseMask) {
    state.assets.baseMask = await imageToMask("user_adjustment_candidate_ua-00-baseline_mask.png");
  }
  const size = state.assets.baseMask
    ? { width: state.assets.baseMask.width, height: state.assets.baseMask.height }
    : null;
  state.assets.upperMask = size ? await imageToMask(upperPath, size) : null;
  state.assets.lowerMask = size ? await imageToMask(lowerPath, size) : null;
  state.assets.innerMask = size ? await imageToMask(innerPath, size) : null;
}

function bbox(mask) {
  if (!mask) return null;
  let minX = mask.width;
  let minY = mask.height;
  let maxX = -1;
  let maxY = -1;
  let count = 0;
  for (let y = 0; y < mask.height; y += 1) {
    const row = y * mask.width;
    for (let x = 0; x < mask.width; x += 1) {
      if (mask.data[row + x]) {
        count += 1;
        if (x < minX) minX = x;
        if (x > maxX) maxX = x;
        if (y < minY) minY = y;
        if (y > maxY) maxY = y;
      }
    }
  }
  if (!count) return null;
  return {
    minX,
    minY,
    maxX,
    maxY,
    width: maxX - minX + 1,
    height: maxY - minY + 1,
    count,
  };
}

function maskFromData(template, data) {
  return { width: template.width, height: template.height, data };
}

function cloneMask(mask) {
  return maskFromData(mask, new Uint8Array(mask.data));
}

function shiftMask(mask, dx = 0, dy = 0) {
  const out = new Uint8Array(mask.width * mask.height);
  const srcX0 = Math.max(0, -dx);
  const srcX1 = Math.min(mask.width, mask.width - dx);
  const srcY0 = Math.max(0, -dy);
  const srcY1 = Math.min(mask.height, mask.height - dy);
  const dstX0 = Math.max(0, dx);
  const dstY0 = Math.max(0, dy);
  for (let y = srcY0; y < srcY1; y += 1) {
    const srcRow = y * mask.width;
    const dstRow = (dstY0 + y - srcY0) * mask.width;
    for (let x = srcX0; x < srcX1; x += 1) {
      out[dstRow + dstX0 + x - srcX0] = mask.data[srcRow + x];
    }
  }
  return maskFromData(mask, out);
}

function splitY(base, upper, lower) {
  const upperBox = bbox(upper);
  const lowerBox = bbox(lower);
  if (upperBox && lowerBox) {
    return Math.round((upperBox.maxY + lowerBox.minY) / 2);
  }
  const box = bbox(base);
  return box ? Math.round((box.minY + box.maxY) / 2) : Math.round(base.height / 2);
}

function horizontalExpand(mask, pixels) {
  const box = bbox(mask);
  const out = new Uint8Array(mask.data);
  if (!box || pixels <= 0) return maskFromData(mask, out);
  for (let y = box.minY; y <= box.maxY; y += 1) {
    const row = y * mask.width;
    for (let x = box.minX; x <= box.maxX; x += 1) {
      if (!mask.data[row + x]) continue;
      const from = Math.max(0, x - pixels);
      const to = Math.min(mask.width - 1, x + pixels);
      for (let xx = from; xx <= to; xx += 1) {
        out[row + xx] = 1;
      }
    }
  }
  return maskFromData(mask, out);
}

function verticalExpand(mask, pixels, direction, split) {
  const box = bbox(mask);
  const out = new Uint8Array(mask.data);
  if (!box || pixels <= 0) return maskFromData(mask, out);
  const yStart = direction < 0 ? box.minY : split + 1;
  const yEnd = direction < 0 ? split : box.maxY;
  for (let y = Math.max(0, yStart); y <= Math.min(mask.height - 1, yEnd); y += 1) {
    const row = y * mask.width;
    for (let x = box.minX; x <= box.maxX; x += 1) {
      if (!mask.data[row + x]) continue;
      for (let step = 1; step <= pixels; step += 1) {
        const yy = y + direction * step;
        if (yy >= 0 && yy < mask.height) {
          out[yy * mask.width + x] = 1;
        }
      }
    }
  }
  return maskFromData(mask, out);
}

function partBox(mask, predicate) {
  let minX = mask.width;
  let minY = mask.height;
  let maxX = -1;
  let maxY = -1;
  let count = 0;
  for (let y = 0; y < mask.height; y += 1) {
    const row = y * mask.width;
    for (let x = 0; x < mask.width; x += 1) {
      if (!mask.data[row + x] || !predicate(x, y)) continue;
      count += 1;
      if (x < minX) minX = x;
      if (x > maxX) maxX = x;
      if (y < minY) minY = y;
      if (y > maxY) maxY = y;
    }
  }
  if (!count) return null;
  return { minX, minY, maxX, maxY, width: maxX - minX + 1, height: maxY - minY + 1, count };
}

function transformedBounds(box, scaleX, scaleY, anchorX, anchorY, width, height) {
  const xs = [
    anchorX + (box.minX - anchorX) * scaleX,
    anchorX + (box.maxX - anchorX) * scaleX,
  ];
  const ys = [
    anchorY + (box.minY - anchorY) * scaleY,
    anchorY + (box.maxY - anchorY) * scaleY,
  ];
  return {
    minX: Math.max(0, Math.floor(Math.min(xs[0], xs[1])) - 2),
    maxX: Math.min(width - 1, Math.ceil(Math.max(xs[0], xs[1])) + 2),
    minY: Math.max(0, Math.floor(Math.min(ys[0], ys[1])) - 2),
    maxY: Math.min(height - 1, Math.ceil(Math.max(ys[0], ys[1])) + 2),
  };
}

function resampleMaskPart(mask, scaleX, scaleY, anchorX, anchorY, predicate) {
  const box = partBox(mask, predicate);
  if (!box || (scaleX === 1 && scaleY === 1)) return cloneMask(mask);
  const out = new Uint8Array(mask.data);
  for (let y = 0; y < mask.height; y += 1) {
    const row = y * mask.width;
    for (let x = 0; x < mask.width; x += 1) {
      if (predicate(x, y)) out[row + x] = 0;
    }
  }
  const bounds = transformedBounds(box, scaleX, scaleY, anchorX, anchorY, mask.width, mask.height);
  let count = 0;
  for (let y = bounds.minY; y <= bounds.maxY; y += 1) {
    for (let x = bounds.minX; x <= bounds.maxX; x += 1) {
      if (!predicate(x, y)) continue;
      const sourceX = Math.round(anchorX + (x - anchorX) / scaleX);
      const sourceY = Math.round(anchorY + (y - anchorY) / scaleY);
      if (
        sourceX >= 0 &&
        sourceX < mask.width &&
        sourceY >= 0 &&
        sourceY < mask.height &&
        predicate(sourceX, sourceY) &&
        mask.data[sourceY * mask.width + sourceX]
      ) {
        out[y * mask.width + x] = 1;
        count += 1;
      }
    }
  }
  return count ? maskFromData(mask, out) : cloneMask(mask);
}

function scaleFromAmount(amount, intensity, invert = false) {
  const direction = invert ? -1 : 1;
  return clamp(1 + Number(amount || 0) * intensity * direction, 0.55, 1.55);
}

function applyInnerMouthExclusion(mask, inner) {
  if (!inner) return mask;
  const out = new Uint8Array(mask.data);
  for (let i = 0; i < out.length; i += 1) {
    if (inner.data[i]) out[i] = 0;
  }
  return maskFromData(mask, out);
}

function applyCornerReach(mask, amount) {
  const box = bbox(mask);
  if (!box || amount === 0) return cloneMask(mask);
  const centerX = (box.minX + box.maxX) / 2;
  const centerY = (box.minY + box.maxY) / 2;
  const scaleX = scaleFromAmount(amount, SHAPE_SCALE_INTENSITY);
  return resampleMaskPart(mask, scaleX, 1, centerX, centerY, () => true);
}

function applyUpperTightness(mask, amount, split, support) {
  const box = bbox(mask);
  if (!box || amount === 0) return cloneMask(mask);
  const scaleY = scaleFromAmount(amount, SHAPE_SCALE_INTENSITY, true);
  return resampleMaskPart(mask, 1, scaleY, (box.minX + box.maxX) / 2, split, (x, y) => y <= split);
}

function applyLowerTightness(mask, amount, split, support) {
  const box = bbox(mask);
  if (!box || amount === 0) return cloneMask(mask);
  const scaleY = scaleFromAmount(amount, SHAPE_SCALE_INTENSITY, true);
  return resampleMaskPart(mask, 1, scaleY, (box.minX + box.maxX) / 2, split, (x, y) => y > split);
}

function applyVerticalOffset(mask, amount) {
  const box = bbox(mask);
  if (!box || amount === 0) return cloneMask(mask);
  const pixels = Math.round(amount * Math.max(2, box.height) * 0.16);
  return shiftMask(mask, 0, pixels);
}

function mergeAddedPixels(original, expanded, support) {
  if (!support) return expanded;
  const out = new Uint8Array(original.data);
  for (let i = 0; i < out.length; i += 1) {
    if (!original.data[i] && expanded.data[i] && support.data[i]) {
      out[i] = 1;
    }
  }
  return maskFromData(original, out);
}

function applyUserAdjustment(base, params, upper, lower, inner) {
  const split = splitY(base, upper, lower);
  let adjusted = applyCornerReach(base, Number(params.cornerReach || 0));
  adjusted = applyUpperTightness(adjusted, Number(params.upperLipTightness || 0), split, upper);
  adjusted = applyLowerTightness(adjusted, Number(params.lowerLipTightness || 0), split, lower);
  adjusted = applyVerticalOffset(adjusted, Number(params.verticalOffset || 0));
  adjusted = applyInnerMouthExclusion(adjusted, inner);
  return adjusted;
}

function maskMetrics(mask, baseline) {
  const box = bbox(mask);
  const baseBox = bbox(baseline);
  return {
    positivePixels: box ? box.count : 0,
    bbox: box
      ? {
          available: true,
          minX: box.minX,
          minY: box.minY,
          maxX: box.maxX,
          maxY: box.maxY,
          width: box.width,
          height: box.height,
        }
      : { available: false },
    bboxWidthDelta: box && baseBox ? box.width - baseBox.width : null,
    bboxHeightDelta: box && baseBox ? box.height - baseBox.height : null,
  };
}

function maskValue(mask, x, y) {
  if (!mask || x < 0 || y < 0 || x >= mask.width || y >= mask.height) return 0;
  return mask.data[y * mask.width + x];
}

function maskEdge(mask, x, y) {
  if (!maskValue(mask, x, y)) return false;
  return (
    !maskValue(mask, x - 1, y) ||
    !maskValue(mask, x + 1, y) ||
    !maskValue(mask, x, y - 1) ||
    !maskValue(mask, x, y + 1)
  );
}

function paintDisplayPixel(display, width, height, x, y, radius) {
  for (let yy = Math.max(0, y - radius); yy <= Math.min(height - 1, y + radius); yy += 1) {
    const row = yy * width;
    for (let xx = Math.max(0, x - radius); xx <= Math.min(width - 1, x + radius); xx += 1) {
      display[row + xx] = 1;
    }
  }
}

function maskToDisplayMask(mask, displayWidth, displayHeight, scale, radius, edgeOnly = false) {
  const display = new Uint8Array(displayWidth * displayHeight);
  const box = bbox(mask);
  if (!box) return display;
  for (let y = box.minY; y <= box.maxY; y += 1) {
    const row = y * mask.width;
    for (let x = box.minX; x <= box.maxX; x += 1) {
      if (!mask.data[row + x]) continue;
      if (edgeOnly && !maskEdge(mask, x, y)) continue;
      const displayX = Math.max(0, Math.min(displayWidth - 1, Math.round(x * scale)));
      const displayY = Math.max(0, Math.min(displayHeight - 1, Math.round(y * scale)));
      paintDisplayPixel(display, displayWidth, displayHeight, displayX, displayY, radius);
    }
  }
  return display;
}

function updateGeneratedMask() {
  const base = state.assets.baseMask;
  if (!base) {
    state.generatedMask = null;
    state.generatedMetrics = {};
    return;
  }
  state.generatedMask = applyUserAdjustment(
    base,
    state.params,
    state.assets.upperMask,
    state.assets.lowerMask,
    state.assets.innerMask,
  );
  state.generatedMetrics = maskMetrics(state.generatedMask, base);
}

function drawAdjustmentPreview() {
  const mask = state.generatedMask;
  if (!mask) return;
  const canvas = els.adjustmentCanvas;
  const frame = state.assets.frame;
  const base = state.assets.baseMask;
  const maxWidth = 390;
  const sourceWidth = frame ? frame.naturalWidth || frame.width : mask.width;
  const sourceHeight = frame ? frame.naturalHeight || frame.height : mask.height;
  const scale = Math.min(1, maxWidth / sourceWidth);
  canvas.width = Math.max(1, Math.round(sourceWidth * scale));
  canvas.height = Math.max(1, Math.round(sourceHeight * scale));
  const context = canvas.getContext("2d", { willReadFrequently: true });
  context.clearRect(0, 0, canvas.width, canvas.height);
  if (frame) {
    context.drawImage(frame, 0, 0, canvas.width, canvas.height);
  } else {
    context.fillStyle = "#f8f8f6";
    context.fillRect(0, 0, canvas.width, canvas.height);
  }
  const image = context.getImageData(0, 0, canvas.width, canvas.height);
  const data = image.data;
  const fillRadius = 0;
  const edgeRadius = 0;
  const currentDisplay = maskToDisplayMask(mask, canvas.width, canvas.height, scale, fillRadius);
  const baseDisplay = maskToDisplayMask(base, canvas.width, canvas.height, scale, fillRadius);
  const currentEdge = maskToDisplayMask(mask, canvas.width, canvas.height, scale, edgeRadius, true);
  const baseEdge = maskToDisplayMask(base, canvas.width, canvas.height, scale, edgeRadius, true);
  for (let y = 0; y < canvas.height; y += 1) {
    const row = y * canvas.width;
    for (let x = 0; x < canvas.width; x += 1) {
      const displayIndex = row + x;
      const i = (y * canvas.width + x) * 4;
      const currentHit = currentDisplay[displayIndex];
      const baseHit = baseDisplay[displayIndex];
      if (currentHit && baseHit) {
        data[i] = data[i] * 0.42 + 255 * 0.58;
        data[i + 1] = data[i + 1] * 0.42 + 45 * 0.58;
        data[i + 2] = data[i + 2] * 0.42 + 120 * 0.58;
        data[i + 3] = 255;
      }
      if (currentHit && !baseHit) {
        data[i] = data[i] * 0.62 + 40 * 0.38;
        data[i + 1] = data[i + 1] * 0.62 + 190 * 0.38;
        data[i + 2] = data[i + 2] * 0.62 + 105 * 0.38;
        data[i + 3] = 255;
      }
      if (baseHit && !currentHit) {
        data[i] = data[i] * 0.78 + 0 * 0.22;
        data[i + 1] = data[i + 1] * 0.78 + 210 * 0.22;
        data[i + 2] = data[i + 2] * 0.78 + 230 * 0.22;
        data[i + 3] = 255;
      }
      if (baseEdge[displayIndex]) {
        data[i] = 0;
        data[i + 1] = 180;
        data[i + 2] = 190;
        data[i + 3] = 255;
      }
      if (currentEdge[displayIndex]) {
        data[i] = 255;
        data[i + 1] = 220;
        data[i + 2] = 0;
        data[i + 3] = 255;
      }
    }
  }
  context.putImageData(image, 0, 0);
}

function syncAfterParamChange() {
  updateGeneratedMask();
  renderParamReadout();
  renderPreview();
  syncJsonOutput();
}

function buildCustomCandidate() {
  const candidateId = CUSTOM_CANDIDATE_IDS[state.mode] || CUSTOM_CANDIDATE_IDS.slider;
  return {
    candidateId,
    label: `${state.mode} custom`,
    params: copyParams(state.params),
    maskPath: `user_adjustment_candidate_${candidateId}_mask.png`,
    overlayPath: null,
    metrics: state.generatedMetrics || {},
  };
}

function buildCandidatesPayloadForExport() {
  const existing = state.candidatesPayload || {
    schemaVersion: CANDIDATE_SCHEMA_VERSION,
    candidates: [],
  };
  const custom = buildCustomCandidate();
  const baseCandidates = existing.candidates || [];
  const candidates = baseCandidates
    .filter((item) => item.candidateId !== custom.candidateId)
    .concat([custom]);
  return Object.assign({}, existing, {
    schemaVersion: CANDIDATE_SCHEMA_VERSION,
    createdAtUtc: new Date().toISOString(),
    candidateCount: candidates.length,
    candidates,
    parameterContract: {
      keys: PARAM_KEYS,
      cornerReach: "+ expands corner reach, - shrinks corner spill",
      upperLipTightness: "+ tightens upper lip, - adds upper coverage",
      lowerLipTightness: "+ tightens lower lip, - adds lower coverage",
      verticalOffset: "image-space + moves down, - moves up",
      legacyParamsNotAcceptedForUserConfirmed: LEGACY_PARAM_KEYS,
    },
    limits: {
      buildlessOnly: true,
      lipOnly: true,
      doesNotRunLiveFaceParsingOrCoreMl: true,
      doesNotUpload: true,
      doesNotClaimRuntimeReady: true,
      doesNotClaimE73Green: true,
    },
  });
}

function downloadText(filename, text, mime = "application/json") {
  const blob = new Blob([text], { type: `${mime};charset=utf-8` });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.append(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function downloadReviewJson() {
  downloadText("user_adjustment_review.json", `${JSON.stringify(buildReviewPayload(), null, 2)}\n`);
}

function downloadCandidatesJson() {
  downloadText(
    "user_adjustment_candidates.json",
    `${JSON.stringify(buildCandidatesPayloadForExport(), null, 2)}\n`,
  );
}

function maskToCanvas(mask) {
  const canvas = document.createElement("canvas");
  canvas.width = mask.width;
  canvas.height = mask.height;
  const context = canvas.getContext("2d");
  const image = context.createImageData(mask.width, mask.height);
  for (let i = 0; i < mask.data.length; i += 1) {
    const value = mask.data[i] ? 255 : 0;
    const j = i * 4;
    image.data[j] = value;
    image.data[j + 1] = value;
    image.data[j + 2] = value;
    image.data[j + 3] = 255;
  }
  context.putImageData(image, 0, 0);
  return canvas;
}

function downloadCustomMask() {
  if (!state.generatedMask) {
    setStatus("custom mask를 만들려면 출력 폴더에서 base mask가 필요합니다.", "warn");
    return;
  }
  const candidateId = CUSTOM_CANDIDATE_IDS[state.mode] || CUSTOM_CANDIDATE_IDS.slider;
  const filename = `user_adjustment_candidate_${candidateId}_mask.png`;
  maskToCanvas(state.generatedMask).toBlob((blob) => {
    if (!blob) return;
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  }, "image/png");
}

function confirmCurrent() {
  if (!state.generatedMask) {
    setStatus("직접 조정 모드는 base mask가 있어야 확정할 수 있습니다.", "warn");
    return;
  }
  state.confirmed = true;
  syncJsonOutput();
  setStatus("user_confirmed review JSON이 준비됐습니다.");
}

function resetParams() {
  state.params = Object.assign({}, DEFAULT_PARAMS);
  state.confirmed = false;
  renderSliders();
  syncAfterParamChange();
}

function bindEvents() {
  els.loadSampleButton.addEventListener("click", () => {
    loadDefaultSample().catch(() => setStatus("샘플 자동 로드를 완료하지 못했습니다. 출력 폴더를 선택해 주세요.", "warn"));
  });
  els.candidateJsonInput.addEventListener("change", (event) => {
    const file = event.target.files && event.target.files[0];
    if (file) {
      loadCandidateJson(file).catch((error) => setStatus(error.message, "warn"));
    }
  });
  els.assetFolderInput.addEventListener("change", (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length) loadAssetFolder(files);
  });
  els.resetParamsButton.addEventListener("click", resetParams);
  els.confirmButton.addEventListener("click", confirmCurrent);
  els.downloadReviewButton.addEventListener("click", downloadReviewJson);
  els.downloadCandidatesButton.addEventListener("click", downloadCandidatesJson);
  els.downloadMaskButton.addEventListener("click", downloadCustomMask);
}

function boot() {
  bindEvents();
  renderSliders();
  renderParamReadout();
  syncJsonOutput();
  loadDefaultSample().catch(() => {
    setStatus("후보 JSON과 같은 출력 폴더를 선택하면 미리보기가 표시됩니다.");
  });
  window.E7LipUserAdjustmentApi = {
    PARAM_KEYS,
    REVIEW_SCHEMA_VERSION,
    CANDIDATE_SCHEMA_VERSION,
    buildReviewPayload,
    applyUserAdjustment,
  };
}

function redirectFileProtocolToLocalServer() {
  if (window.location.protocol !== "file:") return false;
  window.location.replace(LOCAL_SERVER_URL);
  return true;
}

if (!redirectFileProtocolToLocalServer()) {
  boot();
}
