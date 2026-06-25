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
const DEFAULT_PARAMS = Object.fromEntries(PARAM_KEYS.map((key) => [key, 0]));
const CUSTOM_CANDIDATE_IDS = {
  slider: "ua-web-slider-custom",
  guided: "ua-web-guided-custom",
};
const DEFAULT_SAMPLE_URL = "./local-assets/e7-user-adjustment-smoke/user_adjustment_candidates.json";

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

const GUIDED_GROUPS = [
  {
    title: "가로 폭 / 입꼬리",
    actions: [
      ["입꼬리 더 잡기", "cornerReach", 0.05],
      ["입꼬리 spill 줄이기", "cornerReach", -0.05],
    ],
  },
  {
    title: "윗입술",
    actions: [
      ["윗입술 번짐 줄이기", "upperLipTightness", 0.05],
      ["윗입술 덮임 늘리기", "upperLipTightness", -0.05],
    ],
  },
  {
    title: "아랫입술",
    actions: [
      ["아랫입술 번짐 줄이기", "lowerLipTightness", 0.05],
      ["아랫입술 덮임 늘리기", "lowerLipTightness", -0.05],
    ],
  },
  {
    title: "높낮이",
    actions: [
      ["위로 올리기", "verticalOffset", -0.05],
      ["아래로 내리기", "verticalOffset", 0.05],
    ],
  },
];

const state = {
  mode: "select",
  candidatesPayload: null,
  candidates: [],
  selectedCandidateId: null,
  params: { ...DEFAULT_PARAMS },
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
  candidateGrid: document.getElementById("candidateGrid"),
  candidateCountBadge: document.getElementById("candidateCountBadge"),
  sliderControls: document.getElementById("sliderControls"),
  guidedControls: document.getElementById("guidedControls"),
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

function basename(value) {
  return String(value || "")
    .replaceAll("\\", "/")
    .split("/")
    .filter(Boolean)
    .pop();
}

function repoRelativeUrl(value) {
  const text = String(value || "").replaceAll("\\", "/");
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
  const text = String(value || "").replaceAll("\\", "/");
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
  const name = basename(pathOrName);
  if (name && state.assetUrls.has(name)) {
    return state.assetUrls.get(name);
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
    params: { ...DEFAULT_PARAMS, ...(item.params || {}) },
    maskPath: item.maskPath || item.selectedMaskPath || "",
    overlayPath: item.overlayPath || "",
    metrics: item.metrics || {},
  };
}

function renderCandidates() {
  els.candidateGrid.innerHTML = "";
  els.candidateCountBadge.textContent = `${state.candidates.length} candidates`;
  if (!state.candidates.length) {
    const empty = document.createElement("div");
    empty.className = "candidate-placeholder";
    empty.textContent = "user_adjustment_candidates.json을 불러오세요.";
    els.candidateGrid.append(empty);
    return;
  }

  for (const candidate of state.candidates) {
    const card = document.createElement("button");
    card.type = "button";
    card.className = "candidate-card";
    if (candidate.candidateId === state.selectedCandidateId) {
      card.classList.add("selected");
    }
    const imageUrl = resolveAssetUrl(candidate.overlayPath || candidate.maskPath);
    if (imageUrl) {
      const img = document.createElement("img");
      img.alt = candidate.label;
      img.src = imageUrl;
      card.append(img);
    } else {
      const placeholder = document.createElement("div");
      placeholder.className = "candidate-placeholder";
      placeholder.textContent = candidate.candidateId;
      card.append(placeholder);
    }
    const meta = document.createElement("div");
    meta.className = "candidate-meta";
    const title = document.createElement("strong");
    title.textContent = candidate.candidateId;
    const label = document.createElement("span");
    label.textContent = candidate.label;
    meta.append(title, label);
    card.append(meta);
    card.addEventListener("click", () => selectCandidate(candidate.candidateId));
    els.candidateGrid.append(card);
  }
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
    row.append(label, input, value);
    els.sliderControls.append(row);
  }
}

function renderGuidedControls() {
  els.guidedControls.innerHTML = "";
  for (const group of GUIDED_GROUPS) {
    const row = document.createElement("section");
    row.className = "guided-row";
    const title = document.createElement("strong");
    title.textContent = group.title;
    const actions = document.createElement("div");
    actions.className = "guided-actions";
    for (const [label, key, delta] of group.actions) {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = label;
      button.addEventListener("click", () => {
        state.params[key] = roundParam(state.params[key] + delta);
        state.confirmed = false;
        renderSliders();
        syncAfterParamChange();
      });
      actions.append(button);
    }
    row.append(title, actions);
    els.guidedControls.append(row);
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

function selectedCandidatePreviewUrl() {
  const candidate = candidateById(state.selectedCandidateId);
  if (!candidate) {
    return "";
  }
  return resolveAssetUrl(candidate.overlayPath || candidate.maskPath);
}

function renderPreview() {
  els.selectionPreview.style.display = "none";
  els.adjustmentCanvas.style.display = "none";
  els.previewFallback.style.display = "none";

  if (state.mode === "select") {
    const url = selectedCandidatePreviewUrl();
    if (url) {
      els.selectionPreview.src = url;
      els.selectionPreview.style.display = "block";
    } else {
      els.previewFallback.style.display = "block";
    }
    return;
  }

  if (state.generatedMask) {
    drawAdjustmentPreview();
    els.adjustmentCanvas.style.display = "block";
  } else {
    els.previewFallback.style.display = "block";
  }
}

function buildReviewPayload() {
  const isSelect = state.mode === "select";
  const candidateId = isSelect
    ? state.selectedCandidateId
    : CUSTOM_CANDIDATE_IDS[state.mode];
  const candidate = isSelect ? candidateById(candidateId) : null;
  const selectedMaskPath = isSelect
    ? basename(candidate?.maskPath || "")
    : `user_adjustment_candidate_${candidateId}_mask.png`;
  return {
    schemaVersion: REVIEW_SCHEMA_VERSION,
    status: state.confirmed ? "user_confirmed" : "needs_user_selection",
    confirmedByUser: state.confirmed,
    selectedCandidateId: candidateId,
    selectedMaskPath,
    params: { ...state.params },
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

function selectCandidate(candidateId) {
  const candidate = candidateById(candidateId);
  if (!candidate) return;
  state.selectedCandidateId = candidateId;
  state.params = { ...DEFAULT_PARAMS, ...candidate.params };
  state.confirmed = false;
  renderCandidates();
  renderSliders();
  renderParamReadout();
  renderPreview();
  syncJsonOutput();
}

function switchMode(mode) {
  state.mode = mode;
  for (const tab of document.querySelectorAll(".tab")) {
    tab.classList.toggle("active", tab.dataset.mode === mode);
  }
  for (const panel of document.querySelectorAll(".mode-panel")) {
    panel.classList.toggle("hidden", panel.dataset.panel !== mode);
  }
  state.confirmed = false;
  syncAfterParamChange();
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
  const selected = state.candidates[0]?.candidateId || null;
  state.selectedCandidateId = selected;
  if (selected) {
    state.params = { ...DEFAULT_PARAMS, ...candidateById(selected).params };
  }
  state.confirmed = false;
  renderCandidates();
  renderSliders();
  renderParamReadout();
  await loadBaseAssets();
  renderPreview();
  syncJsonOutput();
  setStatus(`${sourceLabel} loaded. 이미지가 안 보이면 이미지 폴더 또는 local-assets 연결을 확인하세요.`);
}

async function loadDefaultSample() {
  const response = await fetch(DEFAULT_SAMPLE_URL, { cache: "no-store" });
  if (!response.ok) {
    throw new Error("sample_not_available: local-assets/e7-user-adjustment-smoke 연결이 필요합니다.");
  }
  await loadCandidatePayload(await response.json(), "sample user_adjustment_candidates.json");
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
  renderCandidates();
  loadBaseAssets().then(() => {
    syncAfterParamChange();
    setStatus(`${files.length} image/files loaded for preview.`);
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
  const inputs = state.candidatesPayload?.inputs || {};
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

function applySupport(mask, support) {
  if (!support) return mask;
  const out = new Uint8Array(mask.data);
  for (let i = 0; i < out.length; i += 1) {
    out[i] = out[i] && support.data[i] ? 1 : 0;
  }
  return maskFromData(mask, out);
}

function applyInnerMouthExclusion(mask, inner) {
  if (!inner) return mask;
  const out = new Uint8Array(mask.data);
  for (let i = 0; i < out.length; i += 1) {
    if (inner.data[i]) out[i] = 0;
  }
  return maskFromData(mask, out);
}

function applyCornerReach(mask, amount, support) {
  const box = bbox(mask);
  if (!box || amount === 0) return cloneMask(mask);
  const pixels = Math.max(1, Math.round(Math.abs(amount) * Math.max(2, box.width) * 0.18));
  if (amount > 0) {
    return applySupport(horizontalExpand(mask, pixels), support);
  }
  const out = new Uint8Array(mask.data);
  const centerX = (box.minX + box.maxX) / 2;
  for (let y = box.minY; y <= box.maxY; y += 1) {
    const row = y * mask.width;
    for (let x = box.minX; x <= box.maxX; x += 1) {
      const keepX = x >= box.minX + pixels && x <= box.maxX - pixels;
      const centerBand = Math.abs(x - centerX) <= Math.max(1, box.width * 0.18);
      if (!keepX && !centerBand) out[row + x] = 0;
    }
  }
  return maskFromData(mask, out);
}

function applyUpperTightness(mask, amount, split, support) {
  const box = bbox(mask);
  if (!box || amount === 0) return cloneMask(mask);
  const pixels = Math.max(1, Math.round(Math.abs(amount) * Math.max(2, box.height) * 0.22));
  const out = new Uint8Array(mask.data);
  if (amount > 0) {
    const limit = box.minY + pixels;
    for (let y = box.minY; y < Math.min(limit, split + 1); y += 1) {
      out.fill(0, y * mask.width, y * mask.width + mask.width);
    }
    return maskFromData(mask, out);
  }
  return applySupport(verticalExpand(mask, pixels, -1, split), support);
}

function applyLowerTightness(mask, amount, split, support) {
  const box = bbox(mask);
  if (!box || amount === 0) return cloneMask(mask);
  const pixels = Math.max(1, Math.round(Math.abs(amount) * Math.max(2, box.height) * 0.22));
  const out = new Uint8Array(mask.data);
  if (amount > 0) {
    const limit = box.maxY - pixels;
    for (let y = Math.max(split + 1, limit + 1); y <= box.maxY; y += 1) {
      out.fill(0, y * mask.width, y * mask.width + mask.width);
    }
    return maskFromData(mask, out);
  }
  return applySupport(verticalExpand(mask, pixels, 1, split), support);
}

function applyVerticalOffset(mask, amount) {
  const box = bbox(mask);
  if (!box || amount === 0) return cloneMask(mask);
  const pixels = Math.round(amount * Math.max(2, box.height) * 0.16);
  return shiftMask(mask, 0, pixels);
}

function unionMasks(a, b) {
  if (!a && !b) return null;
  if (!a) return cloneMask(b);
  if (!b) return cloneMask(a);
  const out = new Uint8Array(a.data.length);
  for (let i = 0; i < out.length; i += 1) {
    out[i] = a.data[i] || b.data[i] ? 1 : 0;
  }
  return maskFromData(a, out);
}

function applyUserAdjustment(base, params, upper, lower, inner) {
  const support = unionMasks(upper, lower);
  const split = splitY(base, upper, lower);
  let adjusted = applyCornerReach(base, Number(params.cornerReach || 0), support);
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
    positivePixels: box?.count || 0,
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
  const maxWidth = 390;
  const scale = Math.min(1, maxWidth / mask.width);
  canvas.width = Math.max(1, Math.round(mask.width * scale));
  canvas.height = Math.max(1, Math.round(mask.height * scale));
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
  for (let y = 0; y < canvas.height; y += 1) {
    const sourceY = Math.min(mask.height - 1, Math.floor(y / scale));
    for (let x = 0; x < canvas.width; x += 1) {
      const sourceX = Math.min(mask.width - 1, Math.floor(x / scale));
      if (!mask.data[sourceY * mask.width + sourceX]) continue;
      const i = (y * canvas.width + x) * 4;
      data[i] = data[i] * 0.48 + 255 * 0.52;
      data[i + 1] = data[i + 1] * 0.48 + 45 * 0.52;
      data[i + 2] = data[i + 2] * 0.48 + 120 * 0.52;
      data[i + 3] = 255;
    }
  }
  context.putImageData(image, 0, 0);
}

function syncAfterParamChange() {
  if (state.mode !== "select") {
    updateGeneratedMask();
  }
  renderParamReadout();
  renderPreview();
  syncJsonOutput();
}

function buildCustomCandidate() {
  const candidateId = CUSTOM_CANDIDATE_IDS[state.mode] || CUSTOM_CANDIDATE_IDS.slider;
  return {
    candidateId,
    label: `${state.mode} custom`,
    params: { ...state.params },
    maskPath: `user_adjustment_candidate_${candidateId}_mask.png`,
    overlayPath: null,
    metrics: state.generatedMetrics || {},
  };
}

function buildCandidatesPayloadForExport() {
  if (state.mode === "select" && state.candidatesPayload) {
    return state.candidatesPayload;
  }
  const existing = state.candidatesPayload || {
    schemaVersion: CANDIDATE_SCHEMA_VERSION,
    candidates: [],
  };
  const custom = buildCustomCandidate();
  const candidates = [
    ...(existing.candidates || []).filter((item) => item.candidateId !== custom.candidateId),
    custom,
  ];
  return {
    ...existing,
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
  };
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
    setStatus("custom mask를 만들려면 이미지 폴더에서 base mask가 필요합니다.", "warn");
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
  if (state.mode === "select" && !state.selectedCandidateId) {
    setStatus("먼저 후보를 선택하세요.", "warn");
    return;
  }
  if (state.mode !== "select" && !state.generatedMask) {
    setStatus("직접 조정 모드는 base mask가 있어야 확정할 수 있습니다.", "warn");
    return;
  }
  state.confirmed = true;
  syncJsonOutput();
  setStatus("user_confirmed review JSON이 준비됐습니다.");
}

function resetParams() {
  state.params = { ...DEFAULT_PARAMS };
  state.confirmed = false;
  renderSliders();
  syncAfterParamChange();
}

function bindEvents() {
  els.loadSampleButton.addEventListener("click", () => {
    loadDefaultSample().catch((error) => setStatus(error.message, "warn"));
  });
  els.candidateJsonInput.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (file) {
      loadCandidateJson(file).catch((error) => setStatus(error.message, "warn"));
    }
  });
  els.assetFolderInput.addEventListener("change", (event) => {
    const files = Array.from(event.target.files || []);
    if (files.length) loadAssetFolder(files);
  });
  for (const tab of document.querySelectorAll(".tab")) {
    tab.addEventListener("click", () => switchMode(tab.dataset.mode));
  }
  els.resetParamsButton.addEventListener("click", resetParams);
  els.confirmButton.addEventListener("click", confirmCurrent);
  els.downloadReviewButton.addEventListener("click", downloadReviewJson);
  els.downloadCandidatesButton.addEventListener("click", downloadCandidatesJson);
  els.downloadMaskButton.addEventListener("click", downloadCustomMask);
}

function boot() {
  bindEvents();
  renderCandidates();
  renderSliders();
  renderGuidedControls();
  renderParamReadout();
  syncJsonOutput();
  loadDefaultSample().catch(() => {
    setStatus("candidate JSON과 이미지 폴더를 불러오면 바로 비교할 수 있습니다.");
  });
  window.E7LipUserAdjustmentApi = {
    PARAM_KEYS,
    REVIEW_SCHEMA_VERSION,
    CANDIDATE_SCHEMA_VERSION,
    buildReviewPayload,
    applyUserAdjustment,
  };
}

boot();
