from __future__ import annotations

from pathlib import Path

from PIL import Image

from makeyourbrick.server.masks import create_placeholder_mask
from makeyourbrick.server.schemas import SelectionRequest


def test_placeholder_mask_combines_box_points_and_negative_cuts() -> None:
    output_path = Path("outputs/test_placeholder_mask.png")
    try:
        create_placeholder_mask(
            (120, 90),
            SelectionRequest(
                positive_points=[(60, 45)],
                negative_points=[(95, 45)],
                box=(30, 20, 100, 70),
            ),
            output_path,
        )

        mask = Image.open(output_path).convert("L")
        assert mask.getbbox() is not None
        assert mask.getpixel((60, 45)) == 255
        assert mask.getpixel((95, 45)) == 0
        assert mask.getpixel((5, 5)) == 0
    finally:
        output_path.unlink(missing_ok=True)
