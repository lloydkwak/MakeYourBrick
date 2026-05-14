from __future__ import annotations

STUDIO_IMPORT_PRESET_OPTIONS = {
    "voxelizer": "slice",
    "optimize": True,
    "optimizer": "layered",
    "brick_palette": "plates",
    "height_unit": "plate",
    "sculpture_engine": "layered",
    "sculpture_mode": "solid",
    "wall_thickness": 1,
    "base_thickness": 0,
    "support_spacing": 3,
    "voxel_smoothing": "polished",
    "color_strategy": "majority",
    "steps_by_layer": True,
}


def studio_import_preset_options() -> dict[str, object]:
    return dict(STUDIO_IMPORT_PRESET_OPTIONS)
