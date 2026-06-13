import { getRenderedImageRect } from "./overlay.js?v=manual-placement-2";

const MIN_SIZE = 0.05;
const MAX_SIZE = 0.8;

export function createManualPlacementController({
  stage,
  backgroundPreview,
  layer,
  onPlacementChange,
}) {
  const box = document.createElement("div");
  box.className = "manual-object";
  box.tabIndex = 0;
  box.setAttribute("aria-label", "手动放置的前景物体");

  const image = document.createElement("img");
  image.alt = "";
  image.draggable = false;

  const handle = document.createElement("div");
  handle.className = "manual-resize-handle";
  handle.setAttribute("aria-label", "调整前景大小");
  handle.setAttribute("role", "button");

  box.append(image, handle);
  layer.appendChild(box);

  const state = {
    enabled: false,
    scale: 0.25,
    normalizedAspect: 1,
    placement: { x: 0.375, y: 0.375, w: 0.25, h: 0.25 },
    interaction: null,
  };

  image.addEventListener("load", () => {
    updateAspect();
    resizeAroundCenter(state.scale);
  });
  box.addEventListener("pointerdown", startDrag);
  handle.addEventListener("pointerdown", startResize);
  window.addEventListener("pointermove", movePointer);
  window.addEventListener("pointerup", endPointer);
  window.addEventListener("resize", render);
  backgroundPreview.addEventListener("load", () => {
    updateAspect();
    resizeAroundCenter(state.scale);
  });

  function setEnabled(enabled) {
    state.enabled = enabled;
    layer.hidden = !enabled;
    render();
  }

  function setForeground(url) {
    image.src = url || "";
    box.hidden = !url;
    render();
  }

  function setScale(scale) {
    state.scale = clamp(Number(scale), 0.1, 0.7);
    resizeAroundCenter(state.scale);
  }

  function getPlacement() {
    return { ...state.placement };
  }

  function resetPosition() {
    const { w, h } = state.placement;
    state.placement.x = (1 - w) / 2;
    state.placement.y = (1 - h) / 2;
    emitChange("end");
    render();
  }

  function updateAspect() {
    if (!image.naturalWidth || !image.naturalHeight) return;
    if (!backgroundPreview.naturalWidth || !backgroundPreview.naturalHeight) return;
    const pixelAspect = image.naturalWidth / image.naturalHeight;
    state.normalizedAspect =
      pixelAspect * (backgroundPreview.naturalHeight / backgroundPreview.naturalWidth);
  }

  function resizeAroundCenter(scale) {
    const centerX = state.placement.x + state.placement.w / 2;
    const centerY = state.placement.y + state.placement.h / 2;
    const dimensions = dimensionsFromScale(scale);
    state.placement = {
      x: clamp(centerX - dimensions.w / 2, 0, 1 - dimensions.w),
      y: clamp(centerY - dimensions.h / 2, 0, 1 - dimensions.h),
      ...dimensions,
    };
    emitChange("resize");
    render();
  }

  function dimensionsFromScale(scale) {
    const aspect = Math.max(0.05, state.normalizedAspect);
    if (aspect >= 1) {
      return { w: scale, h: scale / aspect };
    }
    return { w: scale * aspect, h: scale };
  }

  function startDrag(event) {
    if (event.target === handle || !state.enabled) return;
    event.preventDefault();
    box.setPointerCapture?.(event.pointerId);
    state.interaction = {
      type: "drag",
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
      placement: getPlacement(),
    };
    box.classList.add("is-dragging");
  }

  function startResize(event) {
    if (!state.enabled) return;
    event.preventDefault();
    event.stopPropagation();
    handle.setPointerCapture?.(event.pointerId);
    state.interaction = {
      type: "resize",
      pointerId: event.pointerId,
      clientX: event.clientX,
      clientY: event.clientY,
      placement: getPlacement(),
    };
    box.classList.add("is-resizing");
  }

  function movePointer(event) {
    if (!state.interaction || event.pointerId !== state.interaction.pointerId) return;
    const rect = getRenderedImageRect(stage, backgroundPreview);
    if (!rect.width || !rect.height) return;
    const deltaX = (event.clientX - state.interaction.clientX) / rect.width;
    const deltaY = (event.clientY - state.interaction.clientY) / rect.height;
    const start = state.interaction.placement;

    if (state.interaction.type === "drag") {
      state.placement.x = clamp(start.x + deltaX, 0, 1 - start.w);
      state.placement.y = clamp(start.y + deltaY, 0, 1 - start.h);
    } else {
      const aspect = Math.max(0.05, state.normalizedAspect);
      const widthFromX = start.w + deltaX;
      const widthFromY = (start.h + deltaY) * aspect;
      const proposedWidth =
        Math.abs(deltaX) >= Math.abs(deltaY * aspect) ? widthFromX : widthFromY;
      const maxWidth = Math.min(
        MAX_SIZE,
        MAX_SIZE * aspect,
        1 - start.x,
        (1 - start.y) * aspect,
      );
      const width = clamp(proposedWidth, MIN_SIZE, Math.max(MIN_SIZE, maxWidth));
      state.placement.w = width;
      state.placement.h = width / aspect;
      state.scale = Math.max(state.placement.w, state.placement.h);
    }

    emitChange("move");
    render();
  }

  function endPointer(event) {
    if (!state.interaction || event.pointerId !== state.interaction.pointerId) return;
    state.interaction = null;
    box.classList.remove("is-dragging", "is-resizing");
    emitChange("end");
  }

  function render() {
    if (!state.enabled || !image.src || !backgroundPreview.naturalWidth) {
      box.hidden = true;
      return;
    }
    box.hidden = false;
    const rect = getRenderedImageRect(stage, backgroundPreview);
    box.style.left = `${rect.left + state.placement.x * rect.width}px`;
    box.style.top = `${rect.top + state.placement.y * rect.height}px`;
    box.style.width = `${state.placement.w * rect.width}px`;
    box.style.height = `${state.placement.h * rect.height}px`;
  }

  function emitChange(phase) {
    onPlacementChange?.(getPlacement(), {
      phase,
      scale: state.scale,
    });
  }

  return {
    getPlacement,
    render,
    resetPosition,
    setEnabled,
    setForeground,
    setScale,
  };
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}
