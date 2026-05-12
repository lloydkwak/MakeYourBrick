"""Studio-like sculpture conversion core."""

from makeyourbrick.sculpture.builder import (
    SculptureTargets,
    build_contour_shell_targets,
    plan_sparse_support_columns,
)
from makeyourbrick.sculpture.catalog import BrickCatalog, catalog_for_palette
from makeyourbrick.sculpture.model import (
    ColorMode,
    HeightUnit,
    LayeredBrickModel,
    SculptureSettings,
    VoxelModel,
)
from makeyourbrick.sculpture.placement import (
    assign_brick_colors_by_majority,
    layered_model_matches_target,
    layered_model_occupancy,
    place_layered_bricks,
)

__all__ = [
    "BrickCatalog",
    "ColorMode",
    "HeightUnit",
    "LayeredBrickModel",
    "SculptureSettings",
    "SculptureTargets",
    "VoxelModel",
    "assign_brick_colors_by_majority",
    "build_contour_shell_targets",
    "catalog_for_palette",
    "layered_model_matches_target",
    "layered_model_occupancy",
    "place_layered_bricks",
    "plan_sparse_support_columns",
]
