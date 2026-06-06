const form = document.querySelector("#recommend-form");
const backgroundInput = document.querySelector("#background-input");
const foregroundInput = document.querySelector("#foreground-input");
const maskInput = document.querySelector("#mask-input");
const backgroundSource = document.querySelector("#background-source");
const foregroundSource = document.querySelector("#foreground-source");
const maskSource = document.querySelector("#mask-source");
const candidateCount = document.querySelector("#candidate-count");
const foregroundScale = document.querySelector("#foreground-scale");
const scorerMode = document.querySelector("#scorer-mode");
const scaleValue = document.querySelector("#scale-value");
const serviceStatus = document.querySelector("#service-status");
const demoCaseStatus = document.querySelector("#demo-case-status");
const demoCaseList = document.querySelector("#demo-case-list");
const demoCaseNote = document.querySelector("#demo-case-note");
const backgroundPreview = document.querySelector("#background-preview");
const overlayLayer = document.querySelector("#overlay-layer");
const candidateList = document.querySelector("#candidate-list");
const requestMeta = document.querySelector("#request-meta");
const exportJsonButton = document.querySelector("#export-json");
const exportCsvButton = document.querySelector("#export-csv");
const confidenceTier = document.querySelector("#confidence-tier");
const confidenceList = document.querySelector("#confidence-list");
const caseLinks = document.querySelector("#case-links");
const modelBadge = document.querySelector("#model-badge");
const stageTitle = document.querySelector("#stage-title");
const coordType = document.querySelector("#coord-type");
const runtime = document.querySelector("#runtime");
const imageSize = document.querySelector("#image-size");
const stage = document.querySelector("#stage");

let responsePayload = null;
let activeIndex = 0;
let backgroundUrl = null;
let foregroundUrl = null;
let serviceLabel = "local";
let demoCases = [];
let activeDemoCase = null;
let demoFiles = {
  background: null,
  foreground: null,
  mask: null,
};

refreshHealth();
refreshDemoCases();

foregroundScale.addEventListener("input", () => {
  scaleValue.textContent = `${Math.round(Number(foregroundScale.value) * 100)}%`;
});

backgroundInput.addEventListener("change", () => {
  const file = backgroundInput.files[0];
  if (!file) return;
  demoFiles.background = null;
  activeDemoCase = null;
  setBackgroundPreview(file);
  backgroundSource.textContent = file.name;
  resetResults("背景已加载");
});

foregroundInput.addEventListener("change", () => {
  const file = foregroundInput.files[0];
  if (!file) return;
  demoFiles.foreground = null;
  activeDemoCase = null;
  setForegroundPreview(file, getActiveFile("mask"));
  foregroundSource.textContent = file.name;
  resetResults("前景已加载");
});

maskInput.addEventListener("change", () => {
  const file = maskInput.files[0];
  demoFiles.mask = null;
  activeDemoCase = null;
  maskSource.textContent = file ? file.name : "可选";
  const foregroundFile = getActiveFile("foreground");
  if (foregroundFile) setForegroundPreview(foregroundFile, file);
  resetResults(file ? "Mask 已加载" : "Mask 已清空");
});

exportJsonButton.addEventListener("click", () => exportResult("json"));
exportCsvButton.addEventListener("click", () => exportResult("csv"));

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const backgroundFile = getActiveFile("background");
  const foregroundFile = getActiveFile("foreground");
  const maskFile = getActiveFile("mask");
  if (!backgroundFile || !foregroundFile) {
    requestMeta.textContent = "请选择背景图和前景物体，或加载内置案例";
    return;
  }

  const data = new FormData();
  data.append("background", backgroundFile);
  data.append("foreground", foregroundFile);
  if (maskFile) data.append("mask", maskFile);
  data.append("candidate_count", candidateCount.value);
  data.append("foreground_scale", foregroundScale.value);
  data.append("mode", scorerMode.value);

  setLoading(true);
  try {
    const response = await fetch("/api/place/recommend", {
      method: "POST",
      body: data,
    });
    if (!response.ok) {
      throw new Error(await buildErrorMessage(response));
    }
    responsePayload = await response.json();
    activeIndex = responsePayload.best_index || 0;
    renderResults();
  } catch (error) {
    serviceStatus.textContent = "error";
    requestMeta.textContent = error.message;
  } finally {
    setLoading(false);
  }
});

window.addEventListener("resize", () => renderOverlay());
backgroundPreview.addEventListener("load", () => renderOverlay());

function setLoading(isLoading) {
  form.querySelector("button").disabled = isLoading;
  demoCaseList.querySelectorAll("button").forEach((button) => {
    button.disabled = isLoading || button.dataset.available !== "true";
  });
  serviceStatus.textContent = isLoading ? "running" : serviceLabel;
}

function resetResults(title) {
  responsePayload = null;
  candidateList.innerHTML = "";
  overlayLayer.innerHTML = "";
  requestMeta.textContent = "等待推理";
  stageTitle.textContent = title;
  runtime.textContent = "-- ms";
  imageSize.textContent = "--";
  confidenceTier.textContent = "待运行";
  confidenceTier.className = "";
  confidenceList.innerHTML = "<li>运行推荐后显示分数饱和、候选重叠和低可信提示。</li>";
  caseLinks.innerHTML = "";
  setExportEnabled(false);
}

function renderResults() {
  if (!responsePayload) return;
  modelBadge.textContent = responsePayload.model_version;
  coordType.textContent = responsePayload.coord_type;
  runtime.textContent = `${responsePayload.runtime_ms} ms`;
  imageSize.textContent = `${responsePayload.image_width} x ${responsePayload.image_height}`;
  requestMeta.textContent = responsePayload.request_id;
  stageTitle.textContent = "本地推荐结果";
  serviceLabel = scorerMode.value === "auto" ? serviceLabel : scorerMode.value;
  serviceStatus.textContent = serviceLabel;
  setExportEnabled(true);

  candidateList.innerHTML = "";
  responsePayload.candidates.forEach((candidate, index) => {
    const item = document.createElement("li");
    item.className = `candidate-item ${candidate.tier}${index === activeIndex ? " active" : ""}`;
    item.tabIndex = 0;
    item.innerHTML = `
      <span class="rank">${candidate.rank}</span>
      <span class="candidate-main">
        <strong>${candidate.label}</strong>
        <span>${candidate.reason}</span>
      </span>
      <span class="candidate-score">
        <strong>${Math.round(candidate.score * 100)}</strong>
        <span>${candidate.tier}</span>
      </span>
    `;
    item.addEventListener("click", () => selectCandidate(index));
    item.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") selectCandidate(index);
    });
    candidateList.appendChild(item);
  });

  renderConfidence();
  renderOverlay();
}

async function refreshHealth() {
  try {
    const response = await fetch("/api/health");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const health = await response.json();
    serviceLabel = `${health.scorer_mode}:${health.scorer_status}`;
    serviceStatus.textContent = serviceLabel;
    modelBadge.textContent = health.model_version;
  } catch (error) {
    serviceLabel = "offline";
    serviceStatus.textContent = "offline";
  }
}

async function refreshDemoCases() {
  try {
    const response = await fetch("/api/demo/cases");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    demoCases = await response.json();
    renderDemoCases();
  } catch (error) {
    demoCaseStatus.textContent = "offline";
    demoCaseList.innerHTML = "";
    demoCaseNote.textContent = "内置案例暂不可用，可继续手动选择图片。";
  }
}

function renderDemoCases() {
  demoCaseStatus.textContent = `${demoCases.filter((item) => item.available).length}/${demoCases.length}`;
  demoCaseList.innerHTML = "";
  demoCases.forEach((demoCase) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `demo-case-button ${demoCase.case_type}`;
    button.dataset.available = String(demoCase.available);
    button.disabled = !demoCase.available;
    button.innerHTML = `
      <strong>${demoCase.title}</strong>
      <span>${demoCase.case_id}</span>
    `;
    button.addEventListener("click", () => loadDemoCase(demoCase));
    demoCaseList.appendChild(button);
  });
}

async function loadDemoCase(demoCase) {
  if (!demoCase.available) return;

  setLoading(true);
  demoCaseStatus.textContent = "loading";
  try {
    const [backgroundFile, foregroundFile, maskFile] = await Promise.all([
      fileFromUrl(demoCase.background_url, `${demoCase.case_id}_background.jpg`),
      fileFromUrl(demoCase.foreground_url, `${demoCase.case_id}_foreground.jpg`),
      fileFromUrl(demoCase.mask_url, `${demoCase.case_id}_mask.jpg`),
    ]);

    backgroundInput.value = "";
    foregroundInput.value = "";
    maskInput.value = "";
    demoFiles = {
      background: backgroundFile,
      foreground: foregroundFile,
      mask: maskFile,
    };
    activeDemoCase = demoCase;

    setBackgroundPreview(backgroundFile);
    await setForegroundPreview(foregroundFile, maskFile);
    foregroundScale.value = Math.min(Number(foregroundScale.max), demoCase.foreground_scale).toFixed(2);
    scaleValue.textContent = `${Math.round(Number(foregroundScale.value) * 100)}%`;
    candidateCount.value = String(demoCase.candidate_count || 3);
    scorerMode.value = demoCase.recommended_mode || "simopa";
    backgroundSource.textContent = `${demoCase.case_id} background`;
    foregroundSource.textContent = `${demoCase.case_id} foreground`;
    maskSource.textContent = `${demoCase.case_id} mask`;
    demoCaseNote.textContent = demoCase.note || "内置案例已加载。";
    resetResults(`${demoCase.title} 已加载`);
  } catch (error) {
    demoCaseNote.textContent = `加载失败：${error.message}`;
  } finally {
    demoCaseStatus.textContent = `${demoCases.filter((item) => item.available).length}/${demoCases.length}`;
    setLoading(false);
  }
}

async function fileFromUrl(url, filename) {
  const response = await fetch(url);
  if (!response.ok) throw new Error(`${url} HTTP ${response.status}`);
  const blob = await response.blob();
  return new File([blob], filename, { type: blob.type || "image/jpeg" });
}

async function buildErrorMessage(response) {
  try {
    const payload = await response.json();
    if (payload.detail) return `HTTP ${response.status}: ${payload.detail}`;
  } catch (error) {
    // Fall through to the compact HTTP status message.
  }
  return `HTTP ${response.status}`;
}

function selectCandidate(index) {
  activeIndex = index;
  renderResults();
}

function getActiveFile(kind) {
  if (kind === "background") return backgroundInput.files[0] || demoFiles.background;
  if (kind === "foreground") return foregroundInput.files[0] || demoFiles.foreground;
  return maskInput.files[0] || demoFiles.mask;
}

function setBackgroundPreview(file) {
  if (backgroundUrl) URL.revokeObjectURL(backgroundUrl);
  backgroundUrl = URL.createObjectURL(file);
  backgroundPreview.src = backgroundUrl;
}

async function setForegroundPreview(file, maskFile = null) {
  if (foregroundUrl) URL.revokeObjectURL(foregroundUrl);
  foregroundUrl = maskFile
    ? await buildMaskedForegroundUrl(file, maskFile)
    : URL.createObjectURL(file);
  renderOverlay();
}

async function buildMaskedForegroundUrl(foregroundFile, maskFile) {
  try {
    const [foregroundImage, maskImage] = await Promise.all([
      loadImageFromFile(foregroundFile),
      loadImageFromFile(maskFile),
    ]);
    const canvas = document.createElement("canvas");
    canvas.width = foregroundImage.naturalWidth || foregroundImage.width;
    canvas.height = foregroundImage.naturalHeight || foregroundImage.height;
    const context = canvas.getContext("2d");
    context.drawImage(foregroundImage, 0, 0, canvas.width, canvas.height);
    const foregroundData = context.getImageData(0, 0, canvas.width, canvas.height);

    const maskCanvas = document.createElement("canvas");
    maskCanvas.width = canvas.width;
    maskCanvas.height = canvas.height;
    const maskContext = maskCanvas.getContext("2d");
    maskContext.drawImage(maskImage, 0, 0, canvas.width, canvas.height);
    const maskData = maskContext.getImageData(0, 0, canvas.width, canvas.height);

    for (let index = 0; index < foregroundData.data.length; index += 4) {
      foregroundData.data[index + 3] = maskData.data[index];
    }
    context.putImageData(foregroundData, 0, 0);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
    if (!blob) return URL.createObjectURL(foregroundFile);
    return URL.createObjectURL(blob);
  } catch (error) {
    return URL.createObjectURL(foregroundFile);
  }
}

function loadImageFromFile(file) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const image = new Image();
    image.onload = () => {
      URL.revokeObjectURL(url);
      resolve(image);
    };
    image.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error(`Could not load ${file.name}`));
    };
    image.src = url;
  });
}

function setExportEnabled(enabled) {
  exportJsonButton.disabled = !enabled;
  exportCsvButton.disabled = !enabled;
}

function renderConfidence() {
  const confidence = analyzeConfidence();
  confidenceTier.textContent = confidence.label;
  confidenceTier.className = confidence.tier;
  confidenceList.innerHTML = confidence.items.map((item) => `<li>${item}</li>`).join("");
  renderCaseLinks();
}

function analyzeConfidence() {
  if (!responsePayload || !responsePayload.candidates.length) {
    return {
      tier: "neutral",
      label: "待运行",
      items: ["运行推荐后显示分数饱和、候选重叠和低可信提示。"],
      metrics: {},
    };
  }

  const candidates = responsePayload.candidates;
  const top = candidates[0];
  const second = candidates[1];
  const top3 = candidates.slice(0, 3);
  const topGap = second ? top.score - second.score : top.score;
  const saturatedCount = top3.filter((candidate) => candidate.score >= 0.995).length;
  const maxIou = maxCandidateIou(top3);
  const items = [];

  if (top.score < 0.45) {
    items.push("Top 1 分数低于不推荐阈值，本次结果应作为拒绝或重新取图处理。");
  }
  if (saturatedCount >= 2) {
    items.push("Top 3 中多个候选接近 1.0，存在分数饱和，需要人工复查排序差异。");
  }
  if (topGap < 0.05 && candidates.length > 1) {
    items.push("Top 1 与 Top 2 分差小于 0.05，首选位置不够唯一。");
  }
  if (maxIou >= 0.75) {
    items.push("Top 3 候选框重叠较高，建议启用 IoU 去重或人工选择更多样的位置。");
  }
  if (top.score >= 0.75 && items.length === 0) {
    items.push("Top 1 分数高、候选差异清晰，可作为高可信推荐展示。");
  }
  if (items.length === 0) {
    items.push("结果可用，但建议结合画面语义做一次人工复查。");
  }

  let tier = "review";
  let label = "需要复查";
  if (top.score < 0.45) {
    tier = "low";
    label = "低可信";
  } else if (items.length === 1 && top.score >= 0.75 && saturatedCount < 2 && maxIou < 0.75) {
    tier = "high";
    label = "高可信";
  }

  return {
    tier,
    label,
    items,
    metrics: {
      top_score: round4(top.score),
      top_gap: round4(topGap),
      saturated_top3: saturatedCount,
      max_top3_iou: round4(maxIou),
    },
  };
}

function renderCaseLinks() {
  caseLinks.innerHTML = "";
  if (!activeDemoCase) return;
  const links = [
    ["案例图", activeDemoCase.panel_url],
    ["遮挡热力图", activeDemoCase.heatmap_url],
  ].filter((item) => item[1]);
  links.forEach(([label, url]) => {
    const link = document.createElement("a");
    link.href = url;
    link.target = "_blank";
    link.rel = "noreferrer";
    link.textContent = label;
    caseLinks.appendChild(link);
  });
}

function maxCandidateIou(candidates) {
  let maxIou = 0;
  for (let i = 0; i < candidates.length; i += 1) {
    for (let j = i + 1; j < candidates.length; j += 1) {
      maxIou = Math.max(maxIou, candidateIou(candidates[i], candidates[j]));
    }
  }
  return maxIou;
}

function candidateIou(a, b) {
  const ax2 = a.x + a.w;
  const ay2 = a.y + a.h;
  const bx2 = b.x + b.w;
  const by2 = b.y + b.h;
  const overlapWidth = Math.max(0, Math.min(ax2, bx2) - Math.max(a.x, b.x));
  const overlapHeight = Math.max(0, Math.min(ay2, by2) - Math.max(a.y, b.y));
  const intersection = overlapWidth * overlapHeight;
  if (intersection <= 0) return 0;
  const union = a.w * a.h + b.w * b.h - intersection;
  return union > 0 ? intersection / union : 0;
}

function exportResult(format) {
  if (!responsePayload) return;
  const confidence = analyzeConfidence();
  const baseName = `${responsePayload.request_id || "smartplace-result"}`;
  if (format === "json") {
    const payload = {
      exported_at: new Date().toISOString(),
      demo_case: activeDemoCase,
      confidence,
      recommendation: responsePayload,
    };
    downloadBlob(
      `${baseName}.json`,
      JSON.stringify(payload, null, 2),
      "application/json",
    );
    return;
  }

  const rows = responsePayload.candidates.map((candidate) => ({
    request_id: responsePayload.request_id,
    model_version: responsePayload.model_version,
    runtime_ms: responsePayload.runtime_ms,
    confidence_label: confidence.label,
    rank: candidate.rank,
    score: candidate.score,
    tier: candidate.tier,
    label: candidate.label,
    x: candidate.x,
    y: candidate.y,
    w: candidate.w,
    h: candidate.h,
    reason: candidate.reason,
  }));
  downloadBlob(`${baseName}.csv`, toCsv(rows), "text/csv;charset=utf-8");
}

function toCsv(rows) {
  if (!rows.length) return "";
  const headers = Object.keys(rows[0]);
  const lines = [headers.join(",")];
  rows.forEach((row) => {
    lines.push(headers.map((key) => csvEscape(row[key])).join(","));
  });
  return lines.join("\n");
}

function csvEscape(value) {
  const text = String(value ?? "");
  if (/[",\r\n]/.test(text)) {
    return `"${text.replace(/"/g, '""')}"`;
  }
  return text;
}

function downloadBlob(filename, content, type) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

function round4(value) {
  return Math.round(value * 10000) / 10000;
}

function renderOverlay() {
  overlayLayer.innerHTML = "";
  if (!responsePayload || !backgroundPreview.naturalWidth || !backgroundPreview.naturalHeight) return;

  const rect = getRenderedImageRect();
  responsePayload.candidates.forEach((candidate, index) => {
    const box = document.createElement("div");
    box.className = `candidate-box${index === activeIndex ? " active" : ""}`;
    box.style.left = `${rect.left + candidate.x * rect.width}px`;
    box.style.top = `${rect.top + candidate.y * rect.height}px`;
    box.style.width = `${candidate.w * rect.width}px`;
    box.style.height = `${candidate.h * rect.height}px`;
    box.innerHTML = `<span class="box-label">#${candidate.rank} ${Math.round(candidate.score * 100)}</span>`;
    if (foregroundUrl) {
      const image = document.createElement("img");
      image.src = foregroundUrl;
      image.alt = "";
      box.appendChild(image);
    }
    overlayLayer.appendChild(box);
  });
}

function getRenderedImageRect() {
  const stageWidth = stage.clientWidth;
  const stageHeight = stage.clientHeight;
  const imageRatio = backgroundPreview.naturalWidth / backgroundPreview.naturalHeight;
  const stageRatio = stageWidth / stageHeight;

  if (imageRatio > stageRatio) {
    const width = stageWidth;
    const height = width / imageRatio;
    return {
      left: 0,
      top: (stageHeight - height) / 2,
      width,
      height,
    };
  }

  const height = stageHeight;
  const width = height * imageRatio;
  return {
    left: (stageWidth - width) / 2,
    top: 0,
    width,
    height,
  };
}
