from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from makeyourbrick.sculpture.model import SculptureSettings, VoxelModel
from makeyourbrick.voxel.sculpture import (
    add_vertical_support_columns,
    base_fill_mask,
    contour_shell_mask,
    repair_sculpture_colors,
)


@dataclass(frozen=True)
class SculptureTargets:
    solid: VoxelModel
    shell: VoxelModel
    base: VoxelModel
    support: VoxelModel
    target: VoxelModel

    @property
    def target_mask(self) -> np.ndarray:
        return self.target.occupancy


def _mask_model(source: VoxelModel, mask: np.ndarray) -> VoxelModel:
    mask = mask.astype(bool)
    colors = repair_sculpture_colors(
        source.occupancy.astype(bool),
        mask,
        source.color_ids,
    )
    colors[~mask] = 0
    return source.with_occupancy(mask, colors)


def build_contour_shell_targets(
    model: VoxelModel,
    settings: SculptureSettings,
) -> SculptureTargets:
    """Build named Studio-like sculpture targets from a solid voxel model.

    The returned masks intentionally keep shell, base, and support separate.
    Placement code can then use different brick choices for exterior contour,
    bottom fill, and internal support without re-deriving those regions.
    """

    solid_mask = model.occupancy.astype(bool)
    shell_mask = contour_shell_mask(solid_mask, settings.wall_thickness)
    base_mask = base_fill_mask(solid_mask, settings.base_thickness)
    shell_base_mask = (shell_mask | base_mask) & solid_mask
    supported_mask = add_vertical_support_columns(
        shell_base_mask,
        solid_mask,
        base_thickness=settings.base_thickness,
        support_spacing=settings.support_spacing,
    )
    support_mask = supported_mask & ~shell_base_mask
    target_mask = (shell_base_mask | support_mask) & solid_mask

    return SculptureTargets(
        solid=_mask_model(model, solid_mask),
        shell=_mask_model(model, shell_mask),
        base=_mask_model(model, base_mask),
        support=_mask_model(model, support_mask),
        target=_mask_model(model, target_mask),
    )
