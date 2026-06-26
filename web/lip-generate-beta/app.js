"use strict";

const SERVER_URL = "http://127.0.0.1:8791";
const ADJUSTMENT_KEYS = [
  "cornerReach",
  "upperLipTightness",
  "lowerLipTightness",
  "verticalOffset",
];

const state = {
  fixtures: [],
  selectedFixtureId: "pair_face_20260622T143334Z_03",
  provider: "vision",
  expressionMode: "uvOnly",
  adjustment: {
    cornerReach: 0,
    upperLipTightness: 0,
    lowerLipTightness: 0,
    verticalOffset: 0,
  },
  lastResult: null,
  compareResults: [],
};

const els = {
  statusLine: document.getElementById("statusLine"),
  fixtureSelect: document.getElementById("fixtureSelect"),
  providerSelect: document.getElementById("providerSelect"),
  assistSelect: document.getElementById("assistSelect"),
  refreshFixturesButton: document.getElementById("refreshFixturesButton"),
  generateButton: document.getElementById("generateButton"),
  compareButton: document.getElementById("compareButton"),
  adjustmentControls: document.getElementById("adjustmentControls"),
  gateStatus: document.getElementById("gateStatus"),
  gateUv: document.getElementById("gateUv"),
  gateRoundTrip: document.getElementById("gateRoundTrip"),
  gateRuntime: document.getElementById("gateRuntime"),
  frameImage: document.getElementById("frameImage"),
  maskImage: document.getElementById("maskImage"),
  uvImage: document.getElementById("uvImage"),
  roundTripImage: document.getElementById("roundTripImage"),
  compareGrid: document.getElementById("compareGrid"),
  payloadPreview: document.getElementById("payloadPreview"),
  warningList: document.getElementById("warningList"),
};

function setStatus(message, tone = "neutral") {
  els.statusLine.textContent = message;
  els.statusLine.dataset.tone = tone;
}

function artifactUrl(path) {
  if (!path) {
    return "";
  }
  return `${SERVER_URL}/api/lip-mask/artifact?path=${encodeURIComponent(path)}`;
}

function getSelectedFixture() {
  return (
    state.fixtures.find((fixture) => fixture.fixtureId === state.selectedFixtureId) ||
    state.fixtures[0]
  );
}

function buildRequest(provider = state.provider, expressionMode = state.expressionMode) {
  return {
    requestId: `web-${Date.now()}`,
    provider,
    expressionMode,
    adjustment: { ...state.adjustment },
    frameSource: "fixture",
    fixtureId: state.selectedFixtureId,
    privacy: {
      localOnly: true,
      offDeviceUpload: false,
      longTermRawFrameStored: false,
    },
  };
}

async function getJson(path) {
  const response = await fetch(`${SERVER_URL}${path}`);
  if (!response.ok) {
    throw new Error(`${path} ${response.status}`);
  }
  return response.json();
}

async function postJson(path, payload) {
  const response = await fetch(`${SERVER_URL}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.reason || data.blockers?.join(", ") || `${path} ${response.status}`);
  }
  return data;
}

function renderAdjustmentControls() {
  els.adjustmentControls.innerHTML = "";
  for (const key of ADJUSTMENT_KEYS) {
    const row = document.createElement("div");
    row.className = "range-row";
    const label = document.createElement("label");
    label.htmlFor = `range-${key}`;
    label.textContent = key;
    const input = document.createElement("input");
    input.id = `range-${key}`;
    input.type = "range";
    input.min = "-1";
    input.max = "1";
    input.step = "0.05";
    input.value = state.adjustment[key];
    const output = document.createElement("output");
    output.htmlFor = input.id;
    output.textContent = Number(state.adjustment[key]).toFixed(2);
    input.addEventListener("input", () => {
      state.adjustment[key] = Number(Number(input.value).toFixed(2));
      output.textContent = state.adjustment[key].toFixed(2);
      renderPayloadPreview();
    });
    label.append(input);
    row.append(label, output);
    els.adjustmentControls.append(row);
  }
}

function renderFixtureOptions() {
  els.fixtureSelect.innerHTML = "";
  for (const fixture of state.fixtures) {
    const option = document.createElement("option");
    option.value = fixture.fixtureId;
    option.textContent = fixture.label || fixture.fixtureId;
    els.fixtureSelect.append(option);
  }
  els.fixtureSelect.value = state.selectedFixtureId;
}

function renderFixturePreview() {
  const fixture = getSelectedFixture();
  els.frameImage.src = fixture ? artifactUrl(fixture.framePath) : "";
}

function renderResult(result) {
  state.lastResult = result;
  const pkg = result.package || {};
  els.gateStatus.textContent = result.status || "-";
  els.gateUv.textContent = String(Boolean(result.uvMaskReady));
  els.gateRoundTrip.textContent = String(Boolean(result.roundTripReady));
  els.gateRuntime.textContent = String(Boolean(result.runtimeApplyReady));
  els.maskImage.src = artifactUrl(result.maskOutputs?.mask);
  els.uvImage.src = artifactUrl(pkg.uvMaskTexture);
  els.roundTripImage.src = artifactUrl(pkg.roundTripPreview);
  renderWarnings(result.warnings || []);
  renderPayloadPreview();
}

function renderWarnings(warnings) {
  els.warningList.innerHTML = "";
  for (const warning of warnings) {
    const item = document.createElement("li");
    item.textContent = warning;
    els.warningList.append(item);
  }
}

function renderPayloadPreview() {
  const request = buildRequest();
  const payload = {
    request,
    lastPackage: state.lastResult?.package || null,
    unityMessagePreview: state.lastResult?.package?.runtimeApplyPayload || null,
  };
  els.payloadPreview.textContent = JSON.stringify(payload, null, 2);
}

function renderCompare() {
  els.compareGrid.innerHTML = "";
  for (const result of state.compareResults) {
    const card = document.createElement("article");
    card.className = "compare-card";
    const header = document.createElement("header");
    const title = document.createElement("strong");
    title.textContent = `${result.provider} / ${result.expressionMode}`;
    const status = document.createElement("small");
    status.textContent = result.status;
    header.append(title, status);
    const image = document.createElement("img");
    image.alt = `${result.provider} ${result.expressionMode} round trip`;
    image.src = artifactUrl(result.package?.roundTripPreview);
    const footer = document.createElement("header");
    const score = result.package?.uvCoverageMetadata?.roundTripScore || {};
    footer.innerHTML = `<small>IoU ${score.iou ?? "-"} · UV ${Boolean(
      result.uvMaskReady,
    )}</small>`;
    card.append(header, image, footer);
    els.compareGrid.append(card);
  }
}

async function refreshFixtures() {
  setStatus("로컬 서버 fixture 확인 중");
  const inventory = await getJson("/api/lip-mask/fixtures");
  state.fixtures = inventory.fixtures || [];
  state.selectedFixtureId = inventory.defaultFixtureId || state.selectedFixtureId;
  renderFixtureOptions();
  renderFixturePreview();
  renderPayloadPreview();
  setStatus("로컬 fixture 준비 완료");
}

async function generateSelected() {
  setStatus("마스크 생성 및 UV round-trip 실행 중");
  const result = await postJson("/api/lip-mask/generate", buildRequest());
  renderResult(result);
  setStatus(`${result.provider} ${result.expressionMode} 생성 완료: ${result.status}`, "warn");
}

async function runCompare() {
  setStatus("4-way 비교 생성 중");
  const combos = [
    ["vision", "uvOnly"],
    ["vision", "blendshapeAssist"],
    ["mediapipe", "uvOnly"],
    ["mediapipe", "blendshapeAssist"],
  ];
  const results = [];
  for (const [provider, expressionMode] of combos) {
    results.push(await postJson("/api/lip-mask/generate", buildRequest(provider, expressionMode)));
  }
  state.compareResults = results;
  renderCompare();
  renderResult(results[0]);
  setStatus("4-way 비교 생성 완료", "warn");
}

function bindEvents() {
  els.refreshFixturesButton.addEventListener("click", () => {
    refreshFixtures().catch((error) => setStatus(error.message, "bad"));
  });
  els.generateButton.addEventListener("click", () => {
    generateSelected().catch((error) => setStatus(error.message, "bad"));
  });
  els.compareButton.addEventListener("click", () => {
    runCompare().catch((error) => setStatus(error.message, "bad"));
  });
  els.fixtureSelect.addEventListener("change", () => {
    state.selectedFixtureId = els.fixtureSelect.value;
    renderFixturePreview();
    renderPayloadPreview();
  });
  els.providerSelect.addEventListener("change", () => {
    state.provider = els.providerSelect.value;
    renderPayloadPreview();
  });
  els.assistSelect.addEventListener("change", () => {
    state.expressionMode = els.assistSelect.value;
    renderPayloadPreview();
  });
}

async function init() {
  bindEvents();
  renderAdjustmentControls();
  renderPayloadPreview();
  await refreshFixtures();
}

init().catch((error) => {
  setStatus(`로컬 서버를 먼저 실행하세요: ${error.message}`, "bad");
});
