from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

from makeyourbrick.ai.gpu_lock import gpu_lock
from makeyourbrick.server.schemas import SelectionRequest

try:
    import cv2
except ImportError:  # pragma: no cover - optional dependency in local dev environments
    cv2 = None


def clamp_point(point: tuple[int, int], width: int, height: int) -> tuple[int, int]:
    x, y = point
    return max(0, min(width - 1, int(x))), max(0, min(height - 1, int(y)))


def create_placeholder_mask(
    image_size: tuple[int, int],
    selection: SelectionRequest,
    output_path: Path,
) -> Path:
    width, height = image_size
    mask = Image.new("L", (width, height), 0)
    draw = ImageDraw.Draw(mask)
    soft_layer = Image.new("L", (width, height), 0)
    soft_draw = ImageDraw.Draw(soft_layer)

    min_dimension = min(width, height)
    point_radius = max(36, min_dimension // 4)
    core_radius = max(8, int(point_radius * 0.55))

    if selection.box is not None:
        x0, y0 = clamp_point((selection.box[0], selection.box[1]), width, height)
        x1, y1 = clamp_point((selection.box[2], selection.box[3]), width, height)
        left, top, right, bottom = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
        corner_radius = max(6, min(right - left, bottom - top) // 8)
        draw.rounded_rectangle((left, top, right, bottom), radius=corner_radius, fill=180)
        inset_x = max(1, (right - left) // 12)
        inset_y = max(1, (bottom - top) // 12)
        soft_draw.ellipse(
            (left - inset_x, top - inset_y, right + inset_x, bottom + inset_y),
            fill=150,
        )

    for point in selection.positive_points:
        x, y = clamp_point(point, width, height)
        soft_draw.ellipse((x - point_radius, y - point_radius, x + point_radius, y + point_radius), fill=220)
        draw.ellipse((x - core_radius, y - core_radius, x + core_radius, y + core_radius), fill=255)

    blur_radius = max(3, min_dimension // 80)
    mask = ImageChops.lighter(mask, soft_layer.filter(ImageFilter.GaussianBlur(blur_radius)))
    mask = mask.filter(ImageFilter.MaxFilter(5))
    mask = mask.filter(ImageFilter.GaussianBlur(max(1, blur_radius // 2)))

    for point in selection.negative_points:
        x, y = clamp_point(point, width, height)
        cut_radius = max(point_radius, min_dimension // 8)
        ImageDraw.Draw(mask).ellipse((x - cut_radius, y - cut_radius, x + cut_radius, y + cut_radius), fill=0)

    mask = mask.point(lambda value: 255 if value >= 64 else 0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask.save(output_path)
    return output_path


def create_interactive_mask(
    image: Image.Image,
    selection: SelectionRequest,
    output_path: Path,
) -> Path:
    rgb_image = image.convert("RGB")
    if _segmenter_mode() == "sam2" and _has_mask_target(selection):
        if _create_sam2_mask(rgb_image, selection, output_path):
            return output_path

    mask_array = _grabcut_mask(rgb_image, selection)
    if mask_array is None or not np.any(mask_array):
        return create_placeholder_mask(rgb_image.size, selection, output_path)

    mask = Image.fromarray((mask_array.astype(np.uint8) * 255), mode="L")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask.save(output_path)
    return output_path


def _segmenter_mode() -> str:
    return os.environ.get("MAKEYOURBRICK_SEGMENTER_MODE", "grabcut").strip().lower()


def _has_mask_target(selection: SelectionRequest) -> bool:
    return bool(selection.positive_points or selection.box)


def _create_sam2_mask(
    image: Image.Image,
    selection: SelectionRequest,
    output_path: Path,
) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    script_text = os.environ.get("MAKEYOURBRICK_SAM2_SCRIPT", "").strip()
    if script_text:
        script_path = Path(script_text).expanduser()
    else:
        script_path = Path(__file__).resolve().parents[3] / "scripts" / "sam2_segment.py"
    if not script_path.is_file():
        return False

    with tempfile.TemporaryDirectory(prefix="makeyourbrick-sam2-") as temp_dir:
        temp_root = Path(temp_dir)
        image_path = temp_root / "image.png"
        selection_path = temp_root / "selection.json"
        image.save(image_path)
        selection_path.write_text(selection.model_dump_json(), encoding="utf-8")
        command = [
            sys.executable,
            str(script_path),
            "--image",
            str(image_path),
            "--selection",
            str(selection_path),
            "--output",
            str(output_path),
            "--model-id",
            os.environ.get("MAKEYOURBRICK_SAM2_MODEL_ID", "facebook/sam2.1-hiera-large"),
            "--device",
            os.environ.get("MAKEYOURBRICK_SAM2_DEVICE", "auto"),
        ]
        env = os.environ.copy()
        env.setdefault("PYTORCH_CUDA_ALLOC_CONF", "expandable_segments:True")
        try:
            with gpu_lock():
                result = subprocess.run(
                    command,
                    check=False,
                    cwd=Path(__file__).resolve().parents[3],
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=int(os.environ.get("MAKEYOURBRICK_SAM2_TIMEOUT_SECONDS", "180")),
                )
        except (OSError, subprocess.TimeoutExpired):
            return False

    if result.returncode != 0:
        _write_sam2_error(output_path, result.stdout, result.stderr)
        return False
    return output_path.exists()


def _write_sam2_error(output_path: Path, stdout: str, stderr: str) -> None:
    debug_path = output_path.with_suffix(".sam2.log")
    debug_path.write_text(
        json.dumps({"stdout": stdout[-4000:], "stderr": stderr[-4000:]}, indent=2) + "\n",
        encoding="utf-8",
    )


def _grabcut_mask(image: Image.Image, selection: SelectionRequest) -> np.ndarray | None:
    if cv2 is None:
        return None

    width, height = image.size
    if width < 3 or height < 3:
        return None

    rgb = np.array(image)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    mask = np.full((height, width), cv2.GC_PR_BGD, dtype=np.uint8)

    rect = _selection_rect(selection, width, height)
    if rect is None and not selection.positive_points:
        return None

    if rect is not None:
        left, top, right, bottom = rect
        mask[:, :] = cv2.GC_BGD
        mask[top : bottom + 1, left : right + 1] = cv2.GC_PR_FGD
    else:
        border = max(2, min(width, height) // 40)
        mask[:border, :] = cv2.GC_BGD
        mask[-border:, :] = cv2.GC_BGD
        mask[:, :border] = cv2.GC_BGD
        mask[:, -border:] = cv2.GC_BGD

    seed_radius = max(4, min(width, height) // 36)
    soft_radius = max(seed_radius * 3, min(width, height) // 10)
    for point in selection.positive_points:
        x, y = clamp_point(point, width, height)
        cv2.circle(mask, (x, y), soft_radius, cv2.GC_PR_FGD, -1)
        cv2.circle(mask, (x, y), seed_radius, cv2.GC_FGD, -1)
    for point in selection.negative_points:
        x, y = clamp_point(point, width, height)
        cv2.circle(mask, (x, y), soft_radius, cv2.GC_BGD, -1)

    if not np.any(mask == cv2.GC_FGD):
        return None

    bgd_model = np.zeros((1, 65), np.float64)
    fgd_model = np.zeros((1, 65), np.float64)
    try:
        cv2.grabCut(bgr, mask, None, bgd_model, fgd_model, 5, cv2.GC_INIT_WITH_MASK)
    except cv2.error:
        return None

    binary = np.logical_or(mask == cv2.GC_FGD, mask == cv2.GC_PR_FGD).astype(np.uint8)
    if rect is not None:
        region = np.zeros_like(binary)
        left, top, right, bottom = _expand_rect(rect, width, height, margin=max(4, min(width, height) // 24))
        region[top : bottom + 1, left : right + 1] = 1
        binary &= region

    return _clean_mask(binary, selection, width, height)


def _selection_rect(selection: SelectionRequest, width: int, height: int) -> tuple[int, int, int, int] | None:
    if selection.box is not None:
        x0, y0 = clamp_point((selection.box[0], selection.box[1]), width, height)
        x1, y1 = clamp_point((selection.box[2], selection.box[3]), width, height)
        left, top, right, bottom = min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)
        if right - left >= 4 and bottom - top >= 4:
            return left, top, right, bottom

    if not selection.positive_points:
        return None

    points = [clamp_point(point, width, height) for point in selection.positive_points]
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    span_x = max(max(xs) - min(xs), width // 5)
    span_y = max(max(ys) - min(ys), height // 4)
    margin_x = max(24, int(span_x * 1.2), width // 8)
    margin_y = max(24, int(span_y * 1.4), height // 8)
    left = max(0, min(xs) - margin_x)
    right = min(width - 1, max(xs) + margin_x)
    top = max(0, min(ys) - margin_y)
    bottom = min(height - 1, max(ys) + margin_y)
    if right - left < 5 or bottom - top < 5:
        return None
    return left, top, right, bottom


def _expand_rect(
    rect: tuple[int, int, int, int],
    width: int,
    height: int,
    margin: int,
) -> tuple[int, int, int, int]:
    left, top, right, bottom = rect
    return (
        max(0, left - margin),
        max(0, top - margin),
        min(width - 1, right + margin),
        min(height - 1, bottom + margin),
    )


def _clean_mask(
    binary: np.ndarray,
    selection: SelectionRequest,
    width: int,
    height: int,
) -> np.ndarray:
    kernel_size = max(3, min(width, height) // 80)
    kernel = np.ones((kernel_size, kernel_size), np.uint8)
    cleaned = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel, iterations=2)
    cleaned = cv2.morphologyEx(cleaned, cv2.MORPH_OPEN, kernel, iterations=1)
    cleaned = _fill_holes(cleaned)

    component = _seed_component(cleaned, selection, width, height)
    if component is not None:
        cleaned = component

    area_ratio = float(np.count_nonzero(cleaned)) / float(width * height)
    if area_ratio <= 0.0 or area_ratio > 0.9:
        return np.zeros_like(cleaned)
    return cleaned.astype(bool)


def _fill_holes(binary: np.ndarray) -> np.ndarray:
    flood = (binary * 255).astype(np.uint8)
    h, w = flood.shape
    flood_mask = np.zeros((h + 2, w + 2), np.uint8)
    cv2.floodFill(flood, flood_mask, (0, 0), 255)
    holes = cv2.bitwise_not(flood)
    return np.logical_or(binary, holes > 0).astype(np.uint8)


def _seed_component(
    binary: np.ndarray,
    selection: SelectionRequest,
    width: int,
    height: int,
) -> np.ndarray | None:
    count, labels, stats, _ = cv2.connectedComponentsWithStats(binary.astype(np.uint8), connectivity=8)
    if count <= 1:
        return None

    seeded_labels: set[int] = set()
    for point in selection.positive_points:
        x, y = clamp_point(point, width, height)
        label = int(labels[y, x])
        if label:
            seeded_labels.add(label)

    if not seeded_labels:
        largest = max(range(1, count), key=lambda label: stats[label, cv2.CC_STAT_AREA])
        seeded_labels.add(largest)

    output = np.isin(labels, list(seeded_labels)).astype(np.uint8)
    return output
