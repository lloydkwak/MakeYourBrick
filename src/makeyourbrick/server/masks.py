from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from makeyourbrick.server.schemas import SelectionRequest


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

    if selection.box is not None:
        x0, y0 = clamp_point((selection.box[0], selection.box[1]), width, height)
        x1, y1 = clamp_point((selection.box[2], selection.box[3]), width, height)
        draw.rectangle((min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1)), fill=220)

    radius = max(10, min(width, height) // 20)
    for point in selection.positive_points:
        x, y = clamp_point(point, width, height)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=255)

    for point in selection.negative_points:
        x, y = clamp_point(point, width, height)
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=0)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    mask.save(output_path)
    return output_path

