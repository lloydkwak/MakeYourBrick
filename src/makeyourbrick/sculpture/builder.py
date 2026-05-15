from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from makeyourbrick.sculpture.model import SculptureSettings, VoxelModel
from makeyourbrick.voxel.sculpture import (
    base_fill_mask,
    contour_shell_mask,
    repair_sculpture_colors,
    vertical_support_mask,
    volume_shell_mask,
)


@dataclass(frozen=True)
class SculptureTargets:
    solid: VoxelModel
    shell: VoxelModel
    base: VoxelModel
    supports: VoxelModel
    target: VoxelModel


def _mask_model(source: VoxelModel, mask: np.ndarray) -> VoxelModel:
    mask = mask.astype(bool)
    colors = repair_sculpture_colors(source.occupancy, mask, source.color_ids)
    colors[~mask] = 0
    return source.with_occupancy(mask, colors)


def build_contour_shell_targets(model: VoxelModel, settings: SculptureSettings) -> SculptureTargets:
    solid_mask = model.occupancy.astype(bool)
    shell_mask = volume_shell_mask(solid_mask, settings.wall_thickness)
    base_mask = base_fill_mask(solid_mask, settings.base_thickness)
    visible_mask = (shell_mask | base_mask) & solid_mask
    support_mask = vertical_support_mask(solid_mask, visible_mask, allow_external_supports=True)
    target_mask = visible_mask | support_mask
    return SculptureTargets(
        solid=_mask_model(model, solid_mask),
        shell=_mask_model(model, shell_mask),
        base=_mask_model(model, base_mask),
        supports=_mask_model(model, support_mask),
        target=_mask_model(model, target_mask),
    )


def build_filled_layer_targets(model: VoxelModel, settings: SculptureSettings) -> SculptureTargets:
    """Build the Studio-like default target: every filled layer footprint is bricked.

    Studio exposes wall thickness for hollow sculpture output, but its preview is
    generated from voxelized layer footprints. For the current MakeYourBrick
    default we keep the complete filled footprint so the LDR does not contain
    artificial interior holes from an over-aggressive shell extraction step.
    """

    solid_mask = model.occupancy.astype(bool)
    shell_mask = contour_shell_mask(solid_mask, settings.wall_thickness)
    base_mask = base_fill_mask(solid_mask, settings.base_thickness)
    return SculptureTargets(
        solid=_mask_model(model, solid_mask),
        shell=_mask_model(model, shell_mask),
        base=_mask_model(model, base_mask),
        supports=_mask_model(model, np.zeros_like(solid_mask, dtype=bool)),
        target=_mask_model(model, solid_mask),
    )
