"""Core Studio-like sculpture conversion components."""

from makeyourbrick.sculpture.builder import SculptureTargets, build_contour_shell_targets
from makeyourbrick.sculpture.catalog import BrickCatalog, catalog_for_palette
from makeyourbrick.sculpture.model import LayeredBrickModel, SculptureSettings, VoxelModel
from makeyourbrick.sculpture.placement import (
    STUDIO_LAYER_COLOR_IDS,
    assign_brick_colors_by_layer,
    layered_model_matches_target,
    layered_model_occupancy,
    place_layered_bricks,
)

__all__ = [
    "BrickCatalog",
    "LayeredBrickModel",
    "SculptureSettings",
    "SculptureTargets",
    "STUDIO_LAYER_COLOR_IDS",
    "VoxelModel",
    "assign_brick_colors_by_layer",
    "build_contour_shell_targets",
    "catalog_for_palette",
    "layered_model_matches_target",
    "layered_model_occupancy",
    "place_layered_bricks",
]
