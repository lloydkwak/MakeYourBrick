from __future__ import annotations

from makeyourbrick.pipeline import DEFAULT_BASE_SIZE_STUDS, DEFAULT_BASE_THICKNESS, DEFAULT_WALL_THICKNESS

STUDIO_IMPORT_PRESET_OPTIONS = {
    "base_size_studs": DEFAULT_BASE_SIZE_STUDS,
    "wall_thickness": DEFAULT_WALL_THICKNESS,
    "base_thickness": DEFAULT_BASE_THICKNESS,
    "up_axis": "auto",
    "steps_by_layer": True,
}


def studio_import_preset_options() -> dict[str, object]:
    return dict(STUDIO_IMPORT_PRESET_OPTIONS)
