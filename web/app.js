const form = document.querySelector("#recommend-form");
const backgroundInput = document.querySelector("#background-input");
const foregroundInput = document.querySelector("#foreground-input");
const maskInput = document.querySelector("#mask-input");
const candidateCount = document.querySelector("#candidate-count");
const foregroundScale = document.querySelector("#foreground-scale");
const scaleValue = document.querySelector("#scale-value");
const serviceStatus = document.querySelector("#service-status");
const backgroundPreview = document.querySelector("#background-preview");
const overlayLayer = document.querySelector("#overlay-layer");
const candidateList = document.querySelector("#candidate-list");
const requestMeta = document.querySelector("#request-meta");
const modelBadge = document.querySelector("#model-badge");
const stageTitle = document.querySelector("#stage-title");
const coordType = document.querySelector("#coord-type");
const runtime = document.querySelector("#runtime");
const imageSize = document.querySelector("#image-size");
const stage = document.querySelector("#stage");

let responsePayload = null;
let activeIndex = 0;
let foregroundUrl = null;

foregroundScale.addEventListener("input", () => {
  scaleValue.textContent = `${Math.round(Number(foregroundScale.value) * 100)}%`;
});

backgroundInput.addEventListener("change", () => {
  const file = backgroundInput.files[0];
  if (!file) return;
  backgroundPreview.src = URL.createObjectURL(file);
  resetResults("背景已加载");
});

foregroundInput.addEventListener("change", () => {
  const file = foregroundInput.files[0];
  if (!file) return;
  if (foregroundUrl) URL.revokeObjectURL(foregroundUrl);
  foregroundUrl = URL.createObjectURL(file);
  resetResults("前景已加载");
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!backgroundInput.files[0] || !foregroundInput.files[0]) return;

  const data = new FormData();
  data.append("background", backgroundInput.files[0]);
  data.append("foreground", foregroundInput.files[0]);
  if (maskInput.files[0]) data.append("mask", maskInput.files[0]);
  data.append("candidate_count", candidateCount.value);
  data.append("foreground_scale", foregroundScale.value);
  data.append("mode", "auto");

  setLoading(true);
  try {
    const response = await fetch("/api/place/recommend", {
      method: "POST",
      body: data,
    });
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
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
  serviceStatus.textContent = isLoading ? "running" : "local";
}

function resetResults(title) {
  responsePayload = null;
  candidateList.innerHTML = "";
  overlayLayer.innerHTML = "";
  requestMeta.textContent = "等待推理";
  stageTitle.textContent = title;
  runtime.textContent = "-- ms";
  imageSize.textContent = "--";
}

function renderResults() {
  if (!responsePayload) return;
  modelBadge.textContent = responsePayload.model_version;
  coordType.textContent = responsePayload.coord_type;
  runtime.textContent = `${responsePayload.runtime_ms} ms`;
  imageSize.textContent = `${responsePayload.image_width} x ${responsePayload.image_height}`;
  requestMeta.textContent = responsePayload.request_id;
  stageTitle.textContent = "本地推荐结果";

  candidateList.innerHTML = "";
  responsePayload.candidates.forEach((candidate, index) => {
    const item = document.createElement("li");
    item.className = `candidate-item${index === activeIndex ? " active" : ""}`;
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

  renderOverlay();
}

function selectCandidate(index) {
  activeIndex = index;
  renderResults();
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
