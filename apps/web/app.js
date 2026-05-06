const imageInput = document.querySelector("#imageInput");
const resetButton = document.querySelector("#resetButton");
const pointModeButton = document.querySelector("#pointModeButton");
const boxModeButton = document.querySelector("#boxModeButton");
const positiveButton = document.querySelector("#positiveButton");
const negativeButton = document.querySelector("#negativeButton");
const undoButton = document.querySelector("#undoButton");
const clearButton = document.querySelector("#clearButton");
const maskToggle = document.querySelector("#maskToggle");
const dropZone = document.querySelector("#dropZone");
const canvas = document.querySelector("#selectionCanvas");
const scanLayer = document.querySelector("#scanLayer");
const emptyState = document.querySelector("#emptyState");
const imageMeta = document.querySelector("#imageMeta");
const payloadPreview = document.querySelector("#payloadPreview");
const targetStuds = document.querySelector("#targetStuds");
const apiBaseUrl = document.querySelector("#apiBaseUrl");
const defaultColor = document.querySelector("#defaultColor");
const sampleColors = document.querySelector("#sampleColors");
const optimizeBricks = document.querySelector("#optimizeBricks");
const exportButton = document.querySelector("#exportButton");
const syncButton = document.querySelector("#syncButton");
const mockRunButton = document.querySelector("#mockRunButton");
const statusText = document.querySelector("#statusText");
const reconstructionPreview = document.querySelector("#reconstructionPreview");
const previewTitle = document.querySelector("#previewTitle");
const previewSubtitle = document.querySelector("#previewSubtitle");

const ctx = canvas.getContext("2d");

const state = {
  image: null,
  imageFile: null,
  imageName: null,
  imageSize: null,
  backend: {
    imageId: null,
    imageUrl: null,
    maskId: null,
    maskUrl: null,
  },
  mode: "point",
  pointType: "positive",
  positivePoints: [],
  negativePoints: [],
  box: null,
  draftBox: null,
  isDraggingBox: false,
  layout: { x: 0, y: 0, width: canvas.width, height: canvas.height, scale: 1 },
};

function setMode(mode) {
  state.mode = mode;
  pointModeButton.classList.toggle("is-active", mode === "point");
  boxModeButton.classList.toggle("is-active", mode === "box");
  canvas.style.cursor = mode === "box" ? "crosshair" : "copy";
  draw();
}

function setPointType(pointType) {
  state.pointType = pointType;
  positiveButton.classList.toggle("is-active", pointType === "positive");
  negativeButton.classList.toggle("is-active", pointType === "negative");
}

function resizeCanvas() {
  const rect = dropZone.getBoundingClientRect();
  const pixelRatio = window.devicePixelRatio || 1;
  canvas.width = Math.max(640, Math.floor(rect.width * pixelRatio));
  canvas.height = Math.max(420, Math.floor(rect.height * pixelRatio));
  draw();
}

function fitImage() {
  if (!state.image) {
    state.layout = { x: 0, y: 0, width: canvas.width, height: canvas.height, scale: 1 };
    return;
  }
  const scale = Math.min(canvas.width / state.image.width, canvas.height / state.image.height);
  const width = state.image.width * scale;
  const height = state.image.height * scale;
  state.layout = {
    x: (canvas.width - width) / 2,
    y: (canvas.height - height) / 2,
    width,
    height,
    scale,
  };
}

function imageToCanvas(point) {
  return {
    x: state.layout.x + point.x * state.layout.scale,
    y: state.layout.y + point.y * state.layout.scale,
  };
}

function canvasToImage(event) {
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const canvasX = (event.clientX - rect.left) * scaleX;
  const canvasY = (event.clientY - rect.top) * scaleY;
  const x = Math.round((canvasX - state.layout.x) / state.layout.scale);
  const y = Math.round((canvasY - state.layout.y) / state.layout.scale);
  return {
    x: Math.max(0, Math.min(state.image.width - 1, x)),
    y: Math.max(0, Math.min(state.image.height - 1, y)),
  };
}

function drawMaskShape() {
  if (!maskToggle.checked || !state.image) return;
  ctx.save();
  ctx.fillStyle = "rgba(26, 127, 100, 0.28)";
  ctx.strokeStyle = "rgba(26, 127, 100, 0.8)";
  ctx.lineWidth = 3;

  const box = state.draftBox || state.box;
  if (box) {
    const start = imageToCanvas({ x: box[0], y: box[1] });
    const end = imageToCanvas({ x: box[2], y: box[3] });
    const x = Math.min(start.x, end.x);
    const y = Math.min(start.y, end.y);
    const width = Math.abs(end.x - start.x);
    const height = Math.abs(end.y - start.y);
    ctx.fillRect(x, y, width, height);
    ctx.strokeRect(x, y, width, height);
  }

  for (const point of state.positivePoints) {
    const current = imageToCanvas(point);
    const radius = Math.max(28, Math.min(70, 44 * state.layout.scale));
    const gradient = ctx.createRadialGradient(current.x, current.y, 8, current.x, current.y, radius);
    gradient.addColorStop(0, "rgba(26, 127, 100, 0.42)");
    gradient.addColorStop(1, "rgba(26, 127, 100, 0)");
    ctx.fillStyle = gradient;
    ctx.beginPath();
    ctx.arc(current.x, current.y, radius, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.restore();
}

function drawPoint(point, color, label) {
  const current = imageToCanvas(point);
  ctx.save();
  ctx.fillStyle = "#ffffff";
  ctx.strokeStyle = color;
  ctx.lineWidth = 4;
  ctx.beginPath();
  ctx.arc(current.x, current.y, 9, 0, Math.PI * 2);
  ctx.fill();
  ctx.stroke();
  ctx.fillStyle = color;
  ctx.font = "bold 18px system-ui";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.fillText(label, current.x, current.y - 1);
  ctx.restore();
}

function drawPulse(point, color) {
  if (typeof point.createdAt !== "number") return;
  const current = imageToCanvas(point);
  const age = performance.now() - point.createdAt;
  const duration = 900;
  if (age < 0 || age > duration) return;
  const progress = age / duration;
  ctx.save();
  ctx.strokeStyle = color;
  ctx.globalAlpha = 1 - progress;
  ctx.lineWidth = 3;
  ctx.beginPath();
  ctx.arc(current.x, current.y, 14 + progress * 34, 0, Math.PI * 2);
  ctx.stroke();
  ctx.restore();
  requestAnimationFrame(draw);
}

function draw() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  fitImage();
  if (!state.image) {
    dropZone.classList.remove("has-selection");
    emptyState.hidden = false;
    updatePayload();
    return;
  }
  emptyState.hidden = true;
  const hasSelection =
    state.positivePoints.length > 0 || state.negativePoints.length > 0 || Boolean(state.box);
  dropZone.classList.toggle("has-selection", hasSelection);
  ctx.drawImage(state.image, state.layout.x, state.layout.y, state.layout.width, state.layout.height);
  drawMaskShape();
  state.positivePoints.forEach((point) => {
    drawPulse(point, "#1a7f64");
    drawPoint(point, "#1a7f64", "+");
  });
  state.negativePoints.forEach((point) => {
    drawPulse(point, "#c9352b");
    drawPoint(point, "#c9352b", "-");
  });
  updatePayload();
}

function buildPayload() {
  return {
    image: state.image
      ? {
          image_id: state.backend.imageId,
          name: state.imageName,
          width: state.image.width,
          height: state.image.height,
          size_bytes: state.imageSize,
          image_url: state.backend.imageUrl,
        }
      : null,
    selection: {
      mask_id: state.backend.maskId,
      mask_url: state.backend.maskUrl,
      positive_points: state.positivePoints.map((point) => [point.x, point.y]),
      negative_points: state.negativePoints.map((point) => [point.x, point.y]),
      box: state.box,
    },
    lego: {
      target_studs: Number(targetStuds.value),
      default_color_id: Number(defaultColor.value),
      sample_colors: sampleColors.checked,
      optimize: optimizeBricks.checked,
      fill: true,
    },
  };
}

function updateStages() {
  const stages = document.querySelectorAll(".stage-list li");
  stages.forEach((stage) => {
    stage.classList.remove("is-current", "is-done");
  });
  const hasImage = Boolean(state.image);
  const hasSelection =
    state.positivePoints.length > 0 || state.negativePoints.length > 0 || Boolean(state.box);
  reconstructionPreview.classList.toggle("is-active", hasSelection);
  previewTitle.textContent = hasSelection ? "Target locked" : "Waiting for target";
  previewSubtitle.textContent = hasSelection
    ? "Mask preview is ready for LEGO conversion."
    : "Select an object to prepare reconstruction.";
  document.querySelector('[data-stage="upload"]').classList.toggle("is-done", hasImage);
  document.querySelector('[data-stage="upload"]').classList.toggle("is-current", !hasImage);
  document.querySelector('[data-stage="select"]').classList.toggle("is-current", hasImage && !hasSelection);
  document.querySelector('[data-stage="select"]').classList.toggle("is-done", hasSelection);
  document.querySelector('[data-stage="segment"]').classList.toggle("is-current", hasSelection);
}

function updatePayload() {
  payloadPreview.textContent = JSON.stringify(buildPayload(), null, 2);
  updateStages();
}

function loadFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  const reader = new FileReader();
  reader.onload = () => {
    const image = new Image();
    image.onload = () => {
      state.image = image;
      state.imageFile = file;
      state.imageName = file.name;
      state.imageSize = file.size;
      state.backend = { imageId: null, imageUrl: null, maskId: null, maskUrl: null };
      state.positivePoints = [];
      state.negativePoints = [];
      state.box = null;
      state.draftBox = null;
      imageMeta.textContent = `${file.name} · ${image.width} x ${image.height}`;
      statusText.textContent = "Image ready";
      draw();
    };
    image.src = reader.result;
  };
  reader.readAsDataURL(file);
}

function normalizeBox(start, end) {
  return [
    Math.min(start.x, end.x),
    Math.min(start.y, end.y),
    Math.max(start.x, end.x),
    Math.max(start.y, end.y),
  ];
}

function resetAll() {
  state.image = null;
  state.imageFile = null;
  state.imageName = null;
  state.imageSize = null;
  state.backend = { imageId: null, imageUrl: null, maskId: null, maskUrl: null };
  state.positivePoints = [];
  state.negativePoints = [];
  state.box = null;
  state.draftBox = null;
  imageInput.value = "";
  imageMeta.textContent = "No image loaded";
  statusText.textContent = "Waiting for image";
  draw();
}

imageInput.addEventListener("change", (event) => loadFile(event.target.files[0]));
resetButton.addEventListener("click", resetAll);
pointModeButton.addEventListener("click", () => setMode("point"));
boxModeButton.addEventListener("click", () => setMode("box"));
positiveButton.addEventListener("click", () => setPointType("positive"));
negativeButton.addEventListener("click", () => setPointType("negative"));
maskToggle.addEventListener("change", draw);

undoButton.addEventListener("click", () => {
  if (state.mode === "box" && state.box) {
    state.box = null;
  } else if (state.pointType === "negative" && state.negativePoints.length) {
    state.negativePoints.pop();
  } else if (state.positivePoints.length) {
    state.positivePoints.pop();
  } else if (state.negativePoints.length) {
    state.negativePoints.pop();
  }
  statusText.textContent = "Selection updated";
  draw();
});

clearButton.addEventListener("click", () => {
  state.positivePoints = [];
  state.negativePoints = [];
  state.box = null;
  state.draftBox = null;
  statusText.textContent = "Selection cleared";
  draw();
});

canvas.addEventListener("pointerdown", (event) => {
  if (!state.image) return;
  const point = canvasToImage(event);
  if (state.mode === "point") {
    point.createdAt = performance.now();
    if (state.pointType === "positive") {
      state.positivePoints.push(point);
    } else {
      state.negativePoints.push(point);
    }
    statusText.textContent = "Selection updated";
    triggerScan();
    draw();
    return;
  }
  state.isDraggingBox = true;
  state.boxStart = point;
  state.draftBox = [point.x, point.y, point.x, point.y];
  canvas.setPointerCapture(event.pointerId);
});

canvas.addEventListener("pointermove", (event) => {
  if (!state.image || !state.isDraggingBox) return;
  const point = canvasToImage(event);
  state.draftBox = normalizeBox(state.boxStart, point);
  draw();
});

canvas.addEventListener("pointerup", (event) => {
  if (!state.image || !state.isDraggingBox) return;
  const point = canvasToImage(event);
  state.box = normalizeBox(state.boxStart, point);
  state.draftBox = null;
  state.isDraggingBox = false;
  canvas.releasePointerCapture(event.pointerId);
  statusText.textContent = "Box selected";
  triggerScan();
  draw();
});

for (const eventName of ["dragenter", "dragover"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.add("is-dragging");
  });
}

for (const eventName of ["dragleave", "drop"]) {
  dropZone.addEventListener(eventName, (event) => {
    event.preventDefault();
    dropZone.classList.remove("is-dragging");
  });
}

dropZone.addEventListener("drop", (event) => {
  loadFile(event.dataTransfer.files[0]);
});

for (const input of [apiBaseUrl, targetStuds, defaultColor, sampleColors, optimizeBricks]) {
  input.addEventListener("change", updatePayload);
}

function triggerScan() {
  scanLayer.classList.remove("is-active");
  void scanLayer.offsetWidth;
  scanLayer.classList.add("is-active");
}

exportButton.addEventListener("click", () => {
  const blob = new Blob([JSON.stringify(buildPayload(), null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = "makeyourbrick-selection.json";
  link.click();
  URL.revokeObjectURL(url);
});

async function uploadImageToBackend() {
  if (state.backend.imageId) return;
  if (!state.imageFile) throw new Error("Upload an image first.");
  const formData = new FormData();
  formData.append("file", state.imageFile, state.imageFile.name);
  const response = await fetch(`${apiBaseUrl.value}/api/images`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    throw new Error(`Image upload failed: ${response.status}`);
  }
  const payload = await response.json();
  state.backend.imageId = payload.image_id;
  state.backend.imageUrl = payload.image_url;
}

async function submitSelectionToBackend() {
  if (!state.backend.imageId) return;
  const payload = buildPayload();
  const response = await fetch(`${apiBaseUrl.value}/api/images/${state.backend.imageId}/selection`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload.selection),
  });
  if (!response.ok) {
    throw new Error(`Selection sync failed: ${response.status}`);
  }
  const result = await response.json();
  state.backend.maskId = result.mask_id;
  state.backend.maskUrl = result.mask_url;
}

syncButton.addEventListener("click", async () => {
  try {
    statusText.textContent = "Syncing with backend";
    await uploadImageToBackend();
    await submitSelectionToBackend();
    statusText.textContent = state.backend.maskId ? "Backend selection synced" : "Backend image synced";
    updatePayload();
  } catch (error) {
    statusText.textContent = error.message;
  }
});

mockRunButton.addEventListener("click", () => {
  const payload = buildPayload();
  const hasSelection =
    payload.selection.positive_points.length > 0 ||
    payload.selection.negative_points.length > 0 ||
    payload.selection.box;
  if (!payload.image || !hasSelection) {
    statusText.textContent = "Image and selection required";
    return;
  }
  statusText.textContent = "Mock conversion queued";
  document.querySelector('[data-stage="segment"]').classList.add("is-done");
  document.querySelector('[data-stage="reconstruct"]').classList.add("is-current");
  reconstructionPreview.classList.add("is-active");
  previewTitle.textContent = "Reconstructing object";
  previewSubtitle.textContent = "Mock 3D and LEGO conversion are in progress.";
  window.setTimeout(() => {
    document.querySelector('[data-stage="reconstruct"]').classList.remove("is-current");
    document.querySelector('[data-stage="reconstruct"]').classList.add("is-done");
    document.querySelector('[data-stage="convert"]').classList.add("is-current");
    previewTitle.textContent = "Building LEGO model";
    previewSubtitle.textContent = "Optimizing bricks and preparing LDraw output.";
  }, 700);
  window.setTimeout(() => {
    document.querySelector('[data-stage="convert"]').classList.remove("is-current");
    document.querySelector('[data-stage="convert"]').classList.add("is-done");
    statusText.textContent = "Mock conversion complete";
    previewTitle.textContent = "Preview complete";
    previewSubtitle.textContent = "Ready for backend integration.";
  }, 1500);
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
setMode("point");
setPointType("positive");
updatePayload();
