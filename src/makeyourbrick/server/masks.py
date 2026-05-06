from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageFilter

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
    soft_layer = Image.new("L", (width, height), 0)
    soft_draw = ImageDraw.Draw(soft_layer)

    min_dimension = min(width, height)
    point_radius = max(12, min_dimension // 10)
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
