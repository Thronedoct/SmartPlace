export function renderCandidateOverlay({
  overlayLayer,
  backgroundPreview,
  stage,
  responsePayload,
  activeIndex,
  foregroundUrl,
}) {
  overlayLayer.innerHTML = "";
  if (!responsePayload || !backgroundPreview.naturalWidth || !backgroundPreview.naturalHeight) return;

  const rect = getRenderedImageRect(stage, backgroundPreview);
  responsePayload.candidates.forEach((candidate, index) => {
    const box = document.createElement("div");
    box.className = `candidate-box ${candidate.tier}${index === activeIndex ? " active" : ""}`;
    box.style.left = `${rect.left + candidate.x * rect.width}px`;
    box.style.top = `${rect.top + candidate.y * rect.height}px`;
    box.style.width = `${candidate.w * rect.width}px`;
    box.style.height = `${candidate.h * rect.height}px`;

    const label = document.createElement("span");
    label.className = "box-label";
    label.textContent = `#${candidate.rank} ${Math.round(candidate.score * 100)}`;
    box.appendChild(label);

    if (foregroundUrl) {
      const image = document.createElement("img");
      image.src = foregroundUrl;
      image.alt = "";
      box.appendChild(image);
    }
    overlayLayer.appendChild(box);
  });
}

function getRenderedImageRect(stage, backgroundPreview) {
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
