import {
  fetchDemoCases,
  fetchHealth,
  fileFromUrl,
  requestRecommendation,
} from "./modules/api.js";
import { analyzeConfidence } from "./modules/confidence.js";
import { exportRecommendation } from "./modules/download.js";
import { buildForegroundPreviewUrl } from "./modules/image-preview.js";
import { renderCandidateOverlay } from "./modules/overlay.js";

const ui = {
  form: document.querySelector("#recommend-form"),
  backgroundInput: document.querySelector("#background-input"),
  foregroundInput: document.querySelector("#foreground-input"),
  maskInput: document.querySelector("#mask-input"),
  backgroundSource: document.querySelector("#background-source"),
  foregroundSource: document.querySelector("#foreground-source"),
  maskSource: document.querySelector("#mask-source"),
  candidateCount: document.querySelector("#candidate-count"),
  foregroundScale: document.querySelector("#foreground-scale"),
  scorerMode: document.querySelector("#scorer-mode"),
  scaleValue: document.querySelector("#scale-value"),
  serviceStatus: document.querySelector("#service-status"),
  demoCaseStatus: document.querySelector("#demo-case-status"),
  demoCaseList: document.querySelector("#demo-case-list"),
  demoCaseNote: document.querySelector("#demo-case-note"),
  backgroundPreview: document.querySelector("#background-preview"),
  overlayLayer: document.querySelector("#overlay-layer"),
  candidateList: document.querySelector("#candidate-list"),
  requestMeta: document.querySelector("#request-meta"),
  exportJsonButton: document.querySelector("#export-json"),
  exportCsvButton: document.querySelector("#export-csv"),
  confidenceTier: document.querySelector("#confidence-tier"),
  confidenceList: document.querySelector("#confidence-list"),
  caseLinks: document.querySelector("#case-links"),
  modelBadge: document.querySelector("#model-badge"),
  presentationToggle: document.querySelector("#presentation-toggle"),
  stageTitle: document.querySelector("#stage-title"),
  coordType: document.querySelector("#coord-type"),
  runtime: document.querySelector("#runtime"),
  imageSize: document.querySelector("#image-size"),
  stage: document.querySelector("#stage"),
};

const state = {
  responsePayload: null,
  activeIndex: 0,
  backgroundUrl: null,
  foregroundUrl: null,
  serviceLabel: "local",
  serviceMode: "mock",
  demoCases: [],
  activeDemoCase: null,
  demoFiles: {
    background: null,
    foreground: null,
    mask: null,
  },
};

init();

function init() {
  bindEvents();
  refreshHealthStatus();
  refreshDemoCaseList();
}

function bindEvents() {
  ui.foregroundScale.addEventListener("input", () => {
    ui.scaleValue.textContent = `${Math.round(Number(ui.foregroundScale.value) * 100)}%`;
  });

  ui.backgroundInput.addEventListener("change", () => {
    const file = ui.backgroundInput.files[0];
    if (!file) return;
    state.demoFiles.background = null;
    state.activeDemoCase = null;
    setBackgroundPreview(file);
    ui.backgroundSource.textContent = file.name;
    resetResults("背景已加载");
  });

  ui.foregroundInput.addEventListener("change", () => {
    const file = ui.foregroundInput.files[0];
    if (!file) return;
    state.demoFiles.foreground = null;
    state.activeDemoCase = null;
    setForegroundPreview(file, getActiveFile("mask"));
    ui.foregroundSource.textContent = file.name;
    resetResults("前景已加载");
  });

  ui.maskInput.addEventListener("change", () => {
    const file = ui.maskInput.files[0];
    state.demoFiles.mask = null;
    state.activeDemoCase = null;
    ui.maskSource.textContent = file ? file.name : "可选";
    const foregroundFile = getActiveFile("foreground");
    if (foregroundFile) setForegroundPreview(foregroundFile, file);
    resetResults(file ? "Mask 已加载" : "Mask 已清空");
  });

  ui.exportJsonButton.addEventListener("click", () => exportCurrentResult("json"));
  ui.exportCsvButton.addEventListener("click", () => exportCurrentResult("csv"));
  ui.presentationToggle.addEventListener("click", togglePresentationMode);
  ui.form.addEventListener("submit", runRecommendation);
  window.addEventListener("resize", renderOverlay);
  ui.backgroundPreview.addEventListener("load", renderOverlay);
}

async function runRecommendation(event) {
  event.preventDefault();
  const backgroundFile = getActiveFile("background");
  const foregroundFile = getActiveFile("foreground");
  const maskFile = getActiveFile("mask");
  if (!backgroundFile || !foregroundFile) {
    ui.requestMeta.textContent = "请选择背景图和前景物体，或加载内置案例";
    return;
  }

  setLoading(true);
  try {
    state.responsePayload = await requestRecommendation({
      backgroundFile,
      foregroundFile,
      maskFile,
      candidateCount: ui.candidateCount.value,
      foregroundScale: ui.foregroundScale.value,
      mode: ui.scorerMode.value,
    });
    state.activeIndex = state.responsePayload.best_index || 0;
    renderResults();
  } catch (error) {
    ui.serviceStatus.textContent = "error";
    ui.requestMeta.textContent = error.message;
  } finally {
    setLoading(false);
  }
}

function setLoading(isLoading) {
  ui.form.querySelector(".primary-action").disabled = isLoading;
  ui.presentationToggle.disabled = isLoading;
  ui.demoCaseList.querySelectorAll("button").forEach((button) => {
    button.disabled = isLoading || button.dataset.available !== "true";
  });
  ui.serviceStatus.textContent = isLoading ? "running" : state.serviceLabel;
}

function resetResults(title) {
  state.responsePayload = null;
  state.activeIndex = 0;
  ui.candidateList.innerHTML = "";
  ui.overlayLayer.innerHTML = "";
  ui.requestMeta.textContent = "等待推理";
  ui.stageTitle.textContent = title;
  ui.runtime.textContent = "-- ms";
  ui.imageSize.textContent = "--";
  ui.confidenceTier.textContent = "待运行";
  ui.confidenceTier.className = "";
  ui.confidenceList.innerHTML = "<li>运行推荐后显示分数饱和、候选重叠和低可信提示。</li>";
  ui.caseLinks.innerHTML = "";
  setExportEnabled(false);
}

function renderResults() {
  const payload = state.responsePayload;
  if (!payload) return;
  ui.modelBadge.textContent = payload.model_version;
  ui.coordType.textContent = payload.coord_type;
  ui.runtime.textContent = `${payload.runtime_ms} ms`;
  ui.imageSize.textContent = `${payload.image_width} x ${payload.image_height}`;
  ui.requestMeta.textContent = payload.request_id;
  ui.stageTitle.textContent = "本地推荐结果";
  ui.serviceStatus.textContent = ui.scorerMode.value === "auto" ? state.serviceLabel : ui.scorerMode.value;
  setExportEnabled(true);

  ui.candidateList.innerHTML = "";
  payload.candidates.forEach((candidate, index) => {
    ui.candidateList.appendChild(createCandidateItem(candidate, index));
  });

  renderConfidence();
  renderOverlay();
}

function createCandidateItem(candidate, index) {
  const item = document.createElement("li");
  item.className = `candidate-item ${candidate.tier}${index === state.activeIndex ? " active" : ""}`;
  item.tabIndex = 0;

  const rank = document.createElement("span");
  rank.className = "rank";
  rank.textContent = candidate.rank;

  const main = document.createElement("span");
  main.className = "candidate-main";
  const label = document.createElement("strong");
  label.textContent = candidate.label;
  const reason = document.createElement("span");
  reason.textContent = candidate.reason;
  main.append(label, reason);

  const score = document.createElement("span");
  score.className = "candidate-score";
  const scoreValue = document.createElement("strong");
  scoreValue.textContent = Math.round(candidate.score * 100);
  const scoreTier = document.createElement("span");
  scoreTier.textContent = candidate.tier;
  score.append(scoreValue, scoreTier);

  item.append(rank, main, score);
  item.addEventListener("click", () => selectCandidate(index));
  item.addEventListener("keydown", (event) => {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      selectCandidate(index);
    }
  });
  return item;
}

async function refreshHealthStatus() {
  try {
    const health = await fetchHealth();
    state.serviceMode = health.scorer_mode || "mock";
    state.serviceLabel = `${state.serviceMode}:${health.scorer_status || "ready"}`;
    ui.serviceStatus.textContent = state.serviceLabel;
    ui.modelBadge.textContent = health.model_version || "mock-v0";
  } catch (error) {
    state.serviceMode = "offline";
    state.serviceLabel = "offline";
    ui.serviceStatus.textContent = "offline";
  }
}

async function refreshDemoCaseList() {
  try {
    state.demoCases = await fetchDemoCases();
    renderDemoCases();
  } catch (error) {
    ui.demoCaseStatus.textContent = "offline";
    ui.demoCaseList.innerHTML = "";
    ui.demoCaseNote.textContent = "内置案例暂不可用，可继续手动选择图片。";
  }
}

function renderDemoCases() {
  ui.demoCaseStatus.textContent = `${state.demoCases.filter((item) => item.available).length}/${state.demoCases.length}`;
  ui.demoCaseList.innerHTML = "";
  state.demoCases.forEach((demoCase) => {
    const button = document.createElement("button");
    button.type = "button";
    const isActive = state.activeDemoCase?.case_id === demoCase.case_id;
    button.className = `demo-case-button ${demoCase.case_type}${isActive ? " active" : ""}`;
    button.dataset.available = String(demoCase.available);
    button.setAttribute("aria-pressed", String(isActive));
    button.disabled = !demoCase.available;

    const title = document.createElement("strong");
    title.textContent = demoCase.title;
    const id = document.createElement("span");
    id.textContent = demoCase.case_id;
    button.append(title, id);

    button.addEventListener("click", () => loadDemoCase(demoCase));
    ui.demoCaseList.appendChild(button);
  });
}

async function loadDemoCase(demoCase) {
  if (!demoCase.available) return;

  setLoading(true);
  ui.demoCaseStatus.textContent = "loading";
  try {
    const [backgroundFile, foregroundFile, maskFile] = await Promise.all([
      fileFromUrl(demoCase.background_url, `${demoCase.case_id}_background.jpg`),
      fileFromUrl(demoCase.foreground_url, `${demoCase.case_id}_foreground.jpg`),
      fileFromUrl(demoCase.mask_url, `${demoCase.case_id}_mask.jpg`),
    ]);

    ui.backgroundInput.value = "";
    ui.foregroundInput.value = "";
    ui.maskInput.value = "";
    state.demoFiles = {
      background: backgroundFile,
      foreground: foregroundFile,
      mask: maskFile,
    };
    state.activeDemoCase = demoCase;
    renderDemoCases();
    setLoading(true);

    setBackgroundPreview(backgroundFile);
    await setForegroundPreview(foregroundFile, maskFile);
    ui.foregroundScale.value = Math.min(Number(ui.foregroundScale.max), demoCase.foreground_scale).toFixed(2);
    ui.scaleValue.textContent = `${Math.round(Number(ui.foregroundScale.value) * 100)}%`;
    ui.candidateCount.value = String(demoCase.candidate_count || 3);
    ui.scorerMode.value = "auto";
    ui.backgroundSource.textContent = `${demoCase.case_id} background`;
    ui.foregroundSource.textContent = `${demoCase.case_id} foreground`;
    ui.maskSource.textContent = `${demoCase.case_id} mask`;
    ui.demoCaseNote.textContent = demoCase.note || "内置案例已加载。";
    resetResults(`${demoCase.title} 已加载`);
  } catch (error) {
    ui.demoCaseNote.textContent = `加载失败：${error.message}`;
  } finally {
    ui.demoCaseStatus.textContent = `${state.demoCases.filter((item) => item.available).length}/${state.demoCases.length}`;
    setLoading(false);
  }
}

function selectCandidate(index) {
  state.activeIndex = index;
  renderResults();
}

function togglePresentationMode() {
  const enabled = !document.body.classList.contains("presentation-mode");
  document.body.classList.toggle("presentation-mode", enabled);
  ui.presentationToggle.setAttribute("aria-pressed", String(enabled));
  ui.presentationToggle.textContent = enabled ? "退出演示" : "演示模式";
  window.setTimeout(renderOverlay, 180);
}

function getActiveFile(kind) {
  if (kind === "background") return ui.backgroundInput.files[0] || state.demoFiles.background;
  if (kind === "foreground") return ui.foregroundInput.files[0] || state.demoFiles.foreground;
  return ui.maskInput.files[0] || state.demoFiles.mask;
}

function setBackgroundPreview(file) {
  if (state.backgroundUrl) URL.revokeObjectURL(state.backgroundUrl);
  state.backgroundUrl = URL.createObjectURL(file);
  ui.backgroundPreview.src = state.backgroundUrl;
}

async function setForegroundPreview(file, maskFile = null) {
  if (state.foregroundUrl) URL.revokeObjectURL(state.foregroundUrl);
  state.foregroundUrl = await buildForegroundPreviewUrl(file, maskFile);
  renderOverlay();
}

function setExportEnabled(enabled) {
  ui.exportJsonButton.disabled = !enabled;
  ui.exportCsvButton.disabled = !enabled;
}

function renderConfidence() {
  const confidence = analyzeConfidence(state.responsePayload);
  ui.confidenceTier.textContent = confidence.label;
  ui.confidenceTier.className = confidence.tier;
  ui.confidenceList.innerHTML = "";
  confidence.items.forEach((text) => {
    const item = document.createElement("li");
    item.textContent = text;
    ui.confidenceList.appendChild(item);
  });
  renderCaseLinks();
}

function renderCaseLinks() {
  ui.caseLinks.innerHTML = "";
  if (!state.activeDemoCase) return;
  const links = [
    ["案例图", state.activeDemoCase.panel_url],
    ["遮挡热力图", state.activeDemoCase.heatmap_url],
  ].filter((item) => item[1]);
  links.forEach(([label, url]) => {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = label;
    ui.caseLinks.appendChild(link);
  });
}

function exportCurrentResult(format) {
  exportRecommendation(format, {
    responsePayload: state.responsePayload,
    activeDemoCase: state.activeDemoCase,
    confidence: analyzeConfidence(state.responsePayload),
  });
}

function renderOverlay() {
  renderCandidateOverlay({
    overlayLayer: ui.overlayLayer,
    backgroundPreview: ui.backgroundPreview,
    stage: ui.stage,
    responsePayload: state.responsePayload,
    activeIndex: state.activeIndex,
    foregroundUrl: state.foregroundUrl,
  });
}
