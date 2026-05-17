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
const apiBaseUrl = document.querySelector("#apiBaseUrl");
const baseSizeStuds = document.querySelector("#baseSizeStuds");
const wallThickness = document.querySelector("#wallThickness");
const baseThickness = document.querySelector("#baseThickness");
const colorStrategy = document.querySelector("#colorStrategy");
const runButton = document.querySelector("#runButton");
const statusText = document.querySelector("#statusText");
const reconstructionPreview = document.querySelector("#reconstructionPreview");
const previewTitle = document.querySelector("#previewTitle");
const previewSubtitle = document.querySelector("#previewSubtitle");
const previewEmpty = document.querySelector("#previewEmpty");
const ldrPreviewCanvas = document.querySelector("#ldrPreviewCanvas");
const resultPanel = document.querySelector("#resultPanel");
const ldrLink = document.querySelector("#ldrLink");
const startDropZone = document.querySelector("#startDropZone");
const allFileInputs = document.querySelectorAll('input[type="file"]');

const ctx = canvas.getContext("2d");
const ldrCtx = ldrPreviewCanvas?.getContext("2d");

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
    maskImage: null,
    jobId: null,
    jobStatus: null,
    jobStage: null,
    result: null,
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

function apiUrl(path) {
  return `${apiBaseUrl.value.replace(/\/$/, "")}${path}`;
}

function hasSelection() {
  return state.positivePoints.length > 0 || state.negativePoints.length > 0 || Boolean(state.box);
}

function resetBackendArtifacts({ keepImage = true } = {}) {
  state.backend.maskId = null;
  state.backend.maskUrl = null;
  state.backend.maskImage = null;
  state.backend.jobId = null;
  state.backend.jobStatus = null;
  state.backend.jobStage = null;
  state.backend.result = null;
  resultPanel.hidden = true;
  if (!keepImage) {
    state.backend.imageId = null;
    state.backend.imageUrl = null;
  }
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
  if (ldrPreviewCanvas) {
    const previewRect = ldrPreviewCanvas.getBoundingClientRect();
    ldrPreviewCanvas.width = Math.max(640, Math.floor(previewRect.width * pixelRatio));
    ldrPreviewCanvas.height = Math.max(420, Math.floor(previewRect.height * pixelRatio));
    if (state.backend.result?.ldr_url) {
      renderLdrFromUrl(apiUrl(state.backend.result.ldr_url));
    }
  }
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
  if (state.backend.maskImage) {
    drawBackendMask();
    return;
  }
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

function drawBackendMask() {
  const maskCanvas = document.createElement("canvas");
  maskCanvas.width = canvas.width;
  maskCanvas.height = canvas.height;
  const maskCtx = maskCanvas.getContext("2d");
  maskCtx.drawImage(
    state.backend.maskImage,
    state.layout.x,
    state.layout.y,
    state.layout.width,
    state.layout.height,
  );
  maskCtx.globalCompositeOperation = "source-in";
  maskCtx.fillStyle = "#1a7f64";
  maskCtx.fillRect(0, 0, maskCanvas.width, maskCanvas.height);

  ctx.save();
  ctx.globalAlpha = 0.34;
  ctx.drawImage(maskCanvas, 0, 0);
  ctx.globalAlpha = 1;
  ctx.strokeStyle = "rgba(26, 127, 100, 0.85)";
  ctx.lineWidth = 2;
  const box = state.box;
  if (box) {
    const start = imageToCanvas({ x: box[0], y: box[1] });
    const end = imageToCanvas({ x: box[2], y: box[3] });
    ctx.strokeRect(start.x, start.y, end.x - start.x, end.y - start.y);
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
    emptyState.style.display = "";
    updatePayload();
    return;
  }
  emptyState.hidden = true;
  emptyState.style.display = "none";
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
      base_size_studs: Number(baseSizeStuds.value),
      wall_thickness: Number(wallThickness.value),
      base_thickness: Number(baseThickness.value),
      up_axis: "auto",
      color_strategy: colorStrategy.value,
      steps_by_layer: true,
    },
    job: {
      job_id: state.backend.jobId,
      status: state.backend.jobStatus,
      stage: state.backend.jobStage,
      result: state.backend.result,
    },
  };
}

function updateStages() {
  const stages = document.querySelectorAll(".stage-list li");
  stages.forEach((stage) => {
    stage.classList.remove("is-current", "is-done");
  });
  const hasImage = Boolean(state.image);
  const selectionReady = hasSelection();
  reconstructionPreview.classList.toggle("is-active", selectionReady);
  previewTitle.textContent = selectionReady ? "Target locked" : "Waiting for target";
  previewSubtitle.textContent = selectionReady
    ? "Mask preview is ready for LEGO conversion."
    : "Select an object to prepare reconstruction.";
  if (selectionReady && state.backend.jobStage) {
    setPipelineStage(state.backend.jobStage);
    return;
  }
  document.querySelector('[data-stage="upload"]').classList.toggle("is-done", hasImage);
  document.querySelector('[data-stage="upload"]').classList.toggle("is-current", !hasImage);
  document.querySelector('[data-stage="select"]').classList.toggle("is-current", hasImage && !selectionReady);
  document.querySelector('[data-stage="select"]').classList.toggle("is-done", selectionReady);
  document.querySelector('[data-stage="segment"]').classList.toggle("is-current", selectionReady);
}

function updatePayload() {
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
      state.backend = {
        imageId: null,
        imageUrl: null,
        maskId: null,
        maskUrl: null,
        maskImage: null,
        jobId: null,
        jobStatus: null,
        jobStage: null,
        result: null,
      };
      state.positivePoints = [];
      state.negativePoints = [];
      state.box = null;
      state.draftBox = null;
      document.body.classList.add("has-image");
      imageMeta.textContent = `${file.name} · ${image.width} x ${image.height}`;
      statusText.textContent = "Image ready";
      resultPanel.hidden = true;
      window.requestAnimationFrame(resizeCanvas);
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
  document.body.classList.remove("has-image");
  state.image = null;
  state.imageFile = null;
  state.imageName = null;
  state.imageSize = null;
  state.backend = {
    imageId: null,
    imageUrl: null,
    maskId: null,
    maskUrl: null,
    maskImage: null,
    jobId: null,
    jobStatus: null,
    jobStage: null,
    result: null,
  };
  state.positivePoints = [];
  state.negativePoints = [];
  state.box = null;
  state.draftBox = null;
  imageInput.value = "";
  imageMeta.textContent = "No image loaded";
  statusText.textContent = "Waiting for image";
  resultPanel.hidden = true;
  clearLdrPreview();
  draw();
}

allFileInputs.forEach((input) => {
  input.addEventListener("change", (event) => loadFile(event.target.files[0]));
});
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
  resetBackendArtifacts();
  statusText.textContent = "Selection updated";
  draw();
});

clearButton.addEventListener("click", () => {
  state.positivePoints = [];
  state.negativePoints = [];
  state.box = null;
  state.draftBox = null;
  resetBackendArtifacts();
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
    resetBackendArtifacts();
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
  resetBackendArtifacts();
  canvas.releasePointerCapture(event.pointerId);
  statusText.textContent = "Box selected";
  triggerScan();
  draw();
});

for (const zone of [dropZone, startDropZone].filter(Boolean)) {
  for (const eventName of ["dragenter", "dragover"]) {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.add("is-dragging");
    });
  }

  for (const eventName of ["dragleave", "drop"]) {
    zone.addEventListener(eventName, (event) => {
      event.preventDefault();
      zone.classList.remove("is-dragging");
    });
  }

  zone.addEventListener("drop", (event) => {
    loadFile(event.dataTransfer.files[0]);
  });
}

for (const input of [apiBaseUrl, baseSizeStuds, wallThickness, baseThickness, colorStrategy]) {
  input.addEventListener("change", updatePayload);
}

function triggerScan() {
  scanLayer.classList.remove("is-active");
  void scanLayer.offsetWidth;
  scanLayer.classList.add("is-active");
}

async function uploadImageToBackend() {
  if (state.backend.imageId) return;
  if (!state.imageFile) throw new Error("Upload an image first.");
  const formData = new FormData();
  formData.append("file", state.imageFile, state.imageFile.name);
  const response = await fetch(apiUrl("/api/images"), {
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
  const response = await fetch(apiUrl(`/api/images/${state.backend.imageId}/selection`), {
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
  await loadBackendMask(result.mask_url);
}

async function loadBackendMask(maskUrl) {
  const image = new Image();
  image.crossOrigin = "anonymous";
  const loaded = new Promise((resolve, reject) => {
    image.onload = resolve;
    image.onerror = () => reject(new Error("Backend mask preview failed to load."));
  });
  const separator = maskUrl.includes("?") ? "&" : "?";
  image.src = `${apiUrl(maskUrl)}${separator}t=${Date.now()}`;
  await loaded;
  state.backend.maskImage = image;
  draw();
}

function setPipelineStage(stage) {
  const stages = document.querySelectorAll(".stage-list li");
  stages.forEach((item) => item.classList.remove("is-current", "is-done"));
  document.querySelector('[data-stage="upload"]').classList.add("is-done");
  document.querySelector('[data-stage="select"]').classList.add("is-done");
  if (stage === "queued" || stage === "segment") {
    document.querySelector('[data-stage="segment"]').classList.add("is-current");
  } else if (stage === "reconstruction" || stage === "mesh_inspection" || stage === "conversion") {
    document.querySelector('[data-stage="segment"]').classList.add("is-done");
    document
      .querySelector('[data-stage="reconstruct"]')
      .classList.toggle("is-current", stage === "reconstruction" || stage === "mesh_inspection");
    document.querySelector('[data-stage="reconstruct"]').classList.toggle("is-done", stage === "conversion");
    document.querySelector('[data-stage="convert"]').classList.toggle("is-current", stage === "conversion");
  } else if (stage === "completed") {
    document.querySelector('[data-stage="segment"]').classList.add("is-done");
    document.querySelector('[data-stage="reconstruct"]').classList.add("is-done");
    document.querySelector('[data-stage="convert"]').classList.add("is-done");
  }
}

function setResultLinks(result) {
  if (result.ldr_url) {
    ldrLink.href = apiUrl(result.ldr_url);
  }
  resultPanel.hidden = false;
  if (result.ldr_url) {
    renderLdrFromUrl(apiUrl(result.ldr_url));
  }
}

const ldrawColors = {
  0: "#1d1e22",
  1: "#0055bf",
  2: "#237841",
  3: "#008f9b",
  4: "#c91a09",
  5: "#c870a0",
  6: "#583927",
  7: "#9ba19d",
  8: "#6d6e5c",
  9: "#b4d2e3",
  10: "#4b9f4a",
  11: "#55a5af",
  12: "#f2705e",
  13: "#fc97ac",
  14: "#f2cd37",
  15: "#ffffff",
  19: "#a5a5cb",
  20: "#d9e4a7",
  27: "#ffaa80",
  71: "#a0a5a9",
};

const partFootprints = {
  "3005.dat": [1, 1],
  "3004.dat": [2, 1],
  "3003.dat": [2, 2],
  "3622.dat": [3, 1],
  "3002.dat": [3, 2],
  "3010.dat": [4, 1],
  "3001.dat": [4, 2],
  "3009.dat": [6, 1],
  "2456.dat": [6, 2],
  "3008.dat": [8, 1],
  "3007.dat": [8, 2],
  "3024.dat": [1, 1],
  "3023.dat": [2, 1],
  "3022.dat": [2, 2],
  "3623.dat": [3, 1],
  "3710.dat": [4, 1],
  "3021.dat": [3, 2],
  "3020.dat": [4, 2],
  "3666.dat": [6, 1],
  "3460.dat": [8, 1],
  "3795.dat": [2, 6],
  "3034.dat": [2, 8],
};

function clearLdrPreview() {
  if (!ldrCtx || !ldrPreviewCanvas) return;
  ldrCtx.clearRect(0, 0, ldrPreviewCanvas.width, ldrPreviewCanvas.height);
  previewEmpty.hidden = false;
  reconstructionPreview.classList.remove("is-active");
}

async function renderLdrFromUrl(url) {
  if (!ldrCtx || !ldrPreviewCanvas) return;
  try {
    const response = await fetch(url);
    if (!response.ok) throw new Error(`LDR preview failed: ${response.status}`);
    renderLdrPreview(await response.text());
  } catch (error) {
    previewTitle.textContent = "LDR preview unavailable";
    previewSubtitle.textContent = error.message;
    clearLdrPreview();
  }
}

function parseLdrBricks(ldrText) {
  const bricks = [];
  for (const line of ldrText.split(/\r?\n/)) {
    const parts = line.trim().split(/\s+/);
    if (parts.length < 15 || parts[0] !== "1") continue;
    const colorId = Number(parts[1]);
    const x = Number(parts[2]) / 20;
    const y = -Number(parts[3]) / 24;
    const z = Number(parts[4]) / 20;
    const partId = parts[14].toLowerCase();
    const footprint = partFootprints[partId] || [1, 1];
    const rotated = Math.abs(Number(parts[5])) < 0.5 && Math.abs(Number(parts[7])) > 0.5;
    bricks.push({
      color: ldrawColors[colorId] || "#d6d9dd",
      x,
      y,
      z,
      width: rotated ? footprint[1] : footprint[0],
      depth: rotated ? footprint[0] : footprint[1],
    });
  }
  return bricks;
}

function shadeColor(hex, amount) {
  const value = Number.parseInt(hex.slice(1), 16);
  const red = Math.max(0, Math.min(255, (value >> 16) + amount));
  const green = Math.max(0, Math.min(255, ((value >> 8) & 255) + amount));
  const blue = Math.max(0, Math.min(255, (value & 255) + amount));
  return `rgb(${red}, ${green}, ${blue})`;
}

function drawIsoBrick(context, brick, transform) {
  const cx = ldrPreviewCanvas.width / 2;
  const cy = ldrPreviewCanvas.height * 0.68;
  const x0 = brick.x - transform.midX;
  const z0 = brick.z - transform.midZ;
  const layer = brick.y - transform.minY;
  const halfW = brick.width / 2;
  const halfD = brick.depth / 2;
  const corners = [
    [x0 - halfW, z0 - halfD],
    [x0 + halfW, z0 - halfD],
    [x0 + halfW, z0 + halfD],
    [x0 - halfW, z0 + halfD],
  ].map(([x, z]) => ({
    x: cx + (x - z) * transform.scale,
    y: cy + (x + z) * transform.scale * 0.52 - layer * transform.scale * 0.72,
  }));
  context.beginPath();
  context.moveTo(corners[0].x, corners[0].y);
  corners.slice(1).forEach((point) => context.lineTo(point.x, point.y));
  context.closePath();
  context.fillStyle = brick.color;
  context.strokeStyle = "rgba(0, 0, 0, 0.28)";
  context.lineWidth = Math.max(0.5, transform.scale * 0.035);
  context.fill();
  context.stroke();

  const studCount = Math.max(1, Math.round(Math.min(brick.width, 8)));
  context.fillStyle = shadeColor(brick.color, 24);
  for (let i = 0; i < studCount; i += 1) {
    const t = (i + 0.5) / studCount;
    const sx = corners[0].x + (corners[1].x - corners[0].x) * t;
    const sy = corners[0].y + (corners[1].y - corners[0].y) * t;
    context.beginPath();
    context.ellipse(sx, sy - transform.scale * 0.13, transform.scale * 0.16, transform.scale * 0.08, 0, 0, Math.PI * 2);
    context.fill();
  }
}

function renderLdrPreview(ldrText) {
  const bricks = parseLdrBricks(ldrText);
  ldrCtx.clearRect(0, 0, ldrPreviewCanvas.width, ldrPreviewCanvas.height);
  if (!bricks.length) {
    clearLdrPreview();
    return;
  }
  const minX = Math.min(...bricks.map((brick) => brick.x - brick.width / 2));
  const maxX = Math.max(...bricks.map((brick) => brick.x + brick.width / 2));
  const minZ = Math.min(...bricks.map((brick) => brick.z - brick.depth / 2));
  const maxZ = Math.max(...bricks.map((brick) => brick.z + brick.depth / 2));
  const minY = Math.min(...bricks.map((brick) => brick.y));
  const maxY = Math.max(...bricks.map((brick) => brick.y));
  const span = Math.max(maxX - minX, maxZ - minZ, (maxY - minY) * 0.7, 1);
  const transform = {
    midX: (minX + maxX) / 2,
    midZ: (minZ + maxZ) / 2,
    minY,
    scale: Math.max(5, Math.min(18, Math.min(ldrPreviewCanvas.width, ldrPreviewCanvas.height) / (span * 2.25))),
  };
  ldrCtx.save();
  ldrCtx.clearRect(0, 0, ldrPreviewCanvas.width, ldrPreviewCanvas.height);
  bricks
    .sort((a, b) => a.x + a.z + a.y * 5 - (b.x + b.z + b.y * 5))
    .forEach((brick) => drawIsoBrick(ldrCtx, brick, transform));
  ldrCtx.restore();
  previewEmpty.hidden = true;
  reconstructionPreview.classList.add("is-active");
}

function delay(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

async function pollJob(jobId) {
  for (;;) {
    const response = await fetch(apiUrl(`/api/jobs/${jobId}`));
    if (!response.ok) throw new Error(`Job polling failed: ${response.status}`);
    const job = await response.json();
    state.backend.jobStatus = job.status;
    state.backend.jobStage = job.stage;
    statusText.textContent = `${job.stage}: ${job.message}`;
    setPipelineStage(job.stage);
    if (job.status === "completed") {
      const resultResponse = await fetch(apiUrl(`/api/jobs/${jobId}/result`));
      if (!resultResponse.ok) throw new Error(`Result request failed: ${resultResponse.status}`);
      const result = await resultResponse.json();
      state.backend.result = result;
      statusText.textContent = "Conversion complete";
      previewTitle.textContent = "LEGO output ready";
      previewSubtitle.textContent = "LDR and report artifacts are available.";
      setPipelineStage("completed");
      setResultLinks(result);
      updatePayload();
      return;
    }
    if (job.status === "failed") {
      throw new Error(job.error || job.message || "Pipeline job failed");
    }
    await delay(650);
  }
}

runButton.addEventListener("click", async () => {
  const payload = buildPayload();
  const selectionReady =
    payload.selection.positive_points.length > 0 ||
    payload.selection.negative_points.length > 0 ||
    payload.selection.box;
  if (!payload.image || !selectionReady) {
    statusText.textContent = "Image and selection required";
    return;
  }
  try {
    runButton.disabled = true;
    resultPanel.hidden = true;
    statusText.textContent = "Preparing backend job";
    await uploadImageToBackend();
    await submitSelectionToBackend();
    setPipelineStage("segment");
    reconstructionPreview.classList.add("is-active");
    previewTitle.textContent = "Reconstructing object";
    previewSubtitle.textContent = "Backend conversion job is running.";
    const response = await fetch(apiUrl("/api/jobs"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        image_id: state.backend.imageId,
        mask_id: state.backend.maskId,
        base_size_studs: payload.lego.base_size_studs,
        wall_thickness: payload.lego.wall_thickness,
        base_thickness: payload.lego.base_thickness,
        up_axis: payload.lego.up_axis,
        color_strategy: payload.lego.color_strategy,
      }),
    });
    if (!response.ok) throw new Error(`Job creation failed: ${response.status}`);
    const job = await response.json();
    state.backend.jobId = job.job_id;
    state.backend.jobStatus = job.status;
    state.backend.jobStage = job.stage;
    statusText.textContent = "Conversion job queued";
    updatePayload();
    await pollJob(job.job_id);
  } catch (error) {
    statusText.textContent = error.message;
  } finally {
    runButton.disabled = false;
  }
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
setMode("point");
setPointType("positive");
updatePayload();
