from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import torch
from PIL import Image


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prompt SAM2 from Hugging Face and write a PNG mask.")
    parser.add_argument("--image", required=True, type=Path)
    parser.add_argument("--selection", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model-id", default="facebook/sam2.1-hiera-large")
    parser.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    parser.add_argument("--threshold", default=0.0, type=float)
    return parser.parse_args()


def select_device(value: str) -> str:
    if value == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    if value == "cuda" and not torch.cuda.is_available():
        return "cpu"
    return value


def point_inside(mask: np.ndarray, point: list[int] | tuple[int, int]) -> bool:
    height, width = mask.shape
    x = int(max(0, min(width - 1, point[0])))
    y = int(max(0, min(height - 1, point[1])))
    return bool(mask[y, x])


def box_overlap(mask: np.ndarray, box: list[int] | tuple[int, int, int, int]) -> tuple[float, float]:
    height, width = mask.shape
    x0 = int(max(0, min(width - 1, min(box[0], box[2]))))
    y0 = int(max(0, min(height - 1, min(box[1], box[3]))))
    x1 = int(max(0, min(width - 1, max(box[0], box[2]))))
    y1 = int(max(0, min(height - 1, max(box[1], box[3]))))
    if x1 <= x0 or y1 <= y0:
        return 0.0, 1.0
    inside = np.zeros_like(mask, dtype=bool)
    inside[y0 : y1 + 1, x0 : x1 + 1] = True
    mask_area = float(np.count_nonzero(mask))
    if mask_area == 0.0:
        return 0.0, 1.0
    inside_count = float(np.count_nonzero(mask & inside))
    return inside_count / mask_area, float(np.count_nonzero(mask & ~inside)) / mask_area


def choose_mask(
    masks: np.ndarray,
    scores: np.ndarray,
    positive_points: list[list[int]],
    negative_points: list[list[int]],
    box: list[int] | tuple[int, int, int, int] | None,
) -> np.ndarray:
    height, width = masks[0].shape
    image_area = float(height * width)
    candidates: list[tuple[float, np.ndarray]] = []
    for mask, raw_score in zip(masks, scores, strict=False):
        binary = np.asarray(mask) > 0
        area_ratio = float(np.count_nonzero(binary)) / image_area
        if area_ratio <= 0.001:
            continue

        score = float(raw_score)
        if positive_points:
            hit_count = sum(1 for point in positive_points if point_inside(binary, point))
            score += 2.5 * (hit_count / len(positive_points))
            if hit_count == 0:
                score -= 3.0
        if negative_points:
            false_count = sum(1 for point in negative_points if point_inside(binary, point))
            score -= 2.0 * false_count
        if box is not None:
            inside_ratio, outside_ratio = box_overlap(binary, box)
            score += 1.5 * inside_ratio
            score -= 1.5 * outside_ratio
        else:
            score -= max(0.0, area_ratio - 0.55) * 4.0

        candidates.append((score, binary))

    if not candidates:
        return np.asarray(masks[int(np.argmax(scores))]) > 0
    candidates.sort(key=lambda item: item[0], reverse=True)
    return candidates[0][1]


def main() -> int:
    args = parse_args()
    image = Image.open(args.image).convert("RGB")
    selection = json.loads(args.selection.read_text(encoding="utf-8"))
    positive_points = selection.get("positive_points") or []
    negative_points = selection.get("negative_points") or []
    box = selection.get("box")
    if not positive_points and not box:
        raise ValueError("SAM2 segmentation requires at least one positive point or a box.")

    from sam2.sam2_image_predictor import SAM2ImagePredictor

    device = select_device(args.device)
    try:
        predictor = SAM2ImagePredictor.from_pretrained(args.model_id, device=device)
    except TypeError:
        predictor = SAM2ImagePredictor.from_pretrained(args.model_id)
        predictor.model.to(device)

    point_coords = None
    point_labels = None
    points = [*positive_points, *negative_points]
    if points:
        point_coords = np.array(points, dtype=np.float32)
        point_labels = np.array([1] * len(positive_points) + [0] * len(negative_points), dtype=np.int32)

    box_array = None
    if box is not None:
        box_array = np.array(box, dtype=np.float32)

    image_array = np.array(image)
    if device == "cuda":
        autocast_dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
        context = torch.autocast("cuda", dtype=autocast_dtype)
    else:
        context = torch.autocast("cpu", enabled=False)

    with torch.inference_mode(), context:
        predictor.set_image(image_array)
        masks, scores, _ = predictor.predict(
            point_coords=point_coords,
            point_labels=point_labels,
            box=box_array,
            multimask_output=True,
        )

    if masks is None or len(masks) == 0:
        raise RuntimeError("SAM2 returned no masks.")

    mask = choose_mask(
        np.asarray(masks) > args.threshold,
        np.asarray(scores),
        positive_points,
        negative_points,
        box,
    )
    if not np.any(mask):
        raise RuntimeError("SAM2 returned an empty mask.")

    output = Image.fromarray((mask.astype(np.uint8) * 255), mode="L")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    output.save(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
