from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from makeyourbrick.sculpture.model import SculptureSettings, VoxelModel
from makeyourbrick.voxel.sculpture import (
    base_fill_mask,
    contour_shell_mask,
    layer_components,
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


def _support_column_cells(
    planned_mask: np.ndarray,
    solid_mask: np.ndarray,
    x: int,
    y: int,
    z: int,
) -> tuple[int, ...] | None:
    cells: list[int] = []
    for column_y in range(y - 1, -1, -1):
        if planned_mask[x, column_y, z]:
            break
        if not solid_mask[x, column_y, z]:
            return None
        cells.append(column_y)
    return tuple(cells)


def plan_sparse_support_columns(
    target_mask: np.ndarray,
    solid_mask: np.ndarray,
    *,
    base_thickness: int = 0,
    support_spacing: int = 3,
) -> np.ndarray:
    if target_mask.ndim != 3 or solid_mask.ndim != 3:
        raise ValueError("Support masks must be 3D arrays.")
    if target_mask.shape != solid_mask.shape:
        raise ValueError("Support masks must have the same shape.")
    if base_thickness < 0:
        raise ValueError("base_thickness must be non-negative.")
    if support_spacing < 1:
        raise ValueError("support_spacing must be at least 1.")

    planned = target_mask.astype(bool).copy()
    solid = solid_mask.astype(bool)
    support = np.zeros_like(planned, dtype=bool)
    start_y = max(1, int(base_thickness))

    for y in range(start_y, planned.shape[1]):
        unsupported = planned[:, y, :] & ~planned[:, y - 1, :]
        for component in layer_components(unsupported):
            if not component:
                continue
            centroid_x = sum(x for x, _z in component) / len(component)
            centroid_z = sum(z for _x, z in component) / len(component)
            candidates: list[tuple[int, float, int, int, tuple[int, ...]]] = []
            for x, z in component:
                cells = _support_column_cells(planned, solid, x, y, z)
                if cells is None or not cells:
                    continue
                distance = abs(x - centroid_x) + abs(z - centroid_z)
                candidates.append((len(cells), distance, x, z, cells))
            candidates.sort()
            target_count = max(1, int(np.ceil(len(component) / float(support_spacing * support_spacing))))
            selected: list[tuple[int, int, tuple[int, ...]]] = []
            for _cost, _distance, x, z, cells in candidates:
                too_close = any(
                    abs(x - selected_x) + abs(z - selected_z) < support_spacing
                    for selected_x, selected_z, _ in selected
                )
                if too_close:
                    continue
                selected.append((x, z, cells))
                if len(selected) >= target_count:
                    break
            if not selected and candidates:
                _cost, _distance, x, z, cells = candidates[0]
                selected.append((x, z, cells))
            for x, z, cells in selected:
                support[x, list(cells), z] = True
                planned[x, list(cells), z] = True

    return support & solid & ~target_mask.astype(bool)


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
    support_mask = plan_sparse_support_columns(
        shell_base_mask,
        solid_mask,
        base_thickness=settings.base_thickness,
        support_spacing=settings.support_spacing,
    )
    target_mask = (shell_base_mask | support_mask) & solid_mask

    return SculptureTargets(
        solid=_mask_model(model, solid_mask),
        shell=_mask_model(model, shell_mask),
        base=_mask_model(model, base_mask),
        support=_mask_model(model, support_mask),
        target=_mask_model(model, target_mask),
    )
