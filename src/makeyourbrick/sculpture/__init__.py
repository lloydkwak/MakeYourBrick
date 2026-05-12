"""Studio-like sculpture conversion core."""

from makeyourbrick.sculpture.builder import SculptureTargets, build_contour_shell_targets
from makeyourbrick.sculpture.catalog import BrickCatalog, catalog_for_palette
from makeyourbrick.sculpture.model import (
    ColorMode,
    HeightUnit,
    LayeredBrickModel,
    SculptureSettings,
    VoxelModel,
)

__all__ = [
    "BrickCatalog",
    "ColorMode",
    "HeightUnit",
    "LayeredBrickModel",
    "SculptureSettings",
    "SculptureTargets",
    "VoxelModel",
    "build_contour_shell_targets",
    "catalog_for_palette",
]
