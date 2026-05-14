from __future__ import annotations

STUDIO_IMPORT_PRESET_OPTIONS = {
    "voxelizer": "slice",
    "optimize": True,
    "optimizer": "layered",
    "brick_palette": "studio",
    "height_unit": "brick",
    "sculpture_engine": "layered",
    "sculpture_mode": "contour-shell",
    "wall_thickness": 3,
    "base_thickness": 0,
    "support_spacing": 0,
    "voxel_smoothing": "polished",
    "color_strategy": "majority",
    "steps_by_layer": True,
    "repair_mode": "none",
}


def studio_import_preset_options() -> dict[str, object]:
    return dict(STUDIO_IMPORT_PRESET_OPTIONS)
