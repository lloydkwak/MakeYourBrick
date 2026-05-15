from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from makeyourbrick.sculpture.model import SculptureSettings, VoxelModel
from makeyourbrick.voxel.sculpture import base_fill_mask, contour_shell_mask, repair_sculpture_colors


@dataclass(frozen=True)
class SculptureTargets:
    solid: VoxelModel
    shell: VoxelModel
    base: VoxelModel
    target: VoxelModel


def _mask_model(source: VoxelModel, mask: np.ndarray) -> VoxelModel:
    mask = mask.astype(bool)
    colors = repair_sculpture_colors(source.occupancy, mask, source.color_ids)
    colors[~mask] = 0
    return source.with_occupancy(mask, colors)


def build_contour_shell_targets(model: VoxelModel, settings: SculptureSettings) -> SculptureTargets:
    solid_mask = model.occupancy.astype(bool)
    shell_mask = contour_shell_mask(solid_mask, settings.wall_thickness)
    base_mask = base_fill_mask(solid_mask, settings.base_thickness)
    target_mask = (shell_mask | base_mask) & solid_mask
    return SculptureTargets(
        solid=_mask_model(model, solid_mask),
        shell=_mask_model(model, shell_mask),
        base=_mask_model(model, base_mask),
        target=_mask_model(model, target_mask),
    )
