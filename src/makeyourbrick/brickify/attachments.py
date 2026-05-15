from __future__ import annotations

from collections import deque

import numpy as np

from makeyourbrick.brickify.optimizer import support_ratio_for_area
from makeyourbrick.types import Brick

PLATE_LAYER_OFFSET = 1.0 / 3.0

PLATE_PARTS: dict[tuple[int, int], str] = {
    (1, 1): "3024.dat",
    (2, 1): "3023.dat",
    (3, 1): "3623.dat",
    (4, 1): "3710.dat",
    (6, 1): "3666.dat",
    (8, 1): "3460.dat",
    (2, 2): "3022.dat",
    (3, 2): "3021.dat",
    (4, 2): "3020.dat",
    (6, 2): "3795.dat",
    (8, 2): "3034.dat",
}

PLATE_SPECS = tuple(
    sorted(
        [
            (width * depth, width, depth, 0, part_id)
            for (width, depth), part_id in PLATE_PARTS.items()
        ]
        + [
            (width * depth, depth, width, 90, part_id)
            for (width, depth), part_id in PLATE_PARTS.items()
            if width != depth
        ],
        reverse=True,
    )
)


def _overlap_area(a: Brick, b: Brick) -> int:
    overlap_x = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
    overlap_z = min(a.z + a.depth, b.z + b.depth) - max(a.z, b.z)
    return max(0, overlap_x) * max(0, overlap_z)


def _has_neighbor(brick: Brick, candidates: list[Brick]) -> bool:
    return any(_overlap_area(brick, other) > 0 for other in candidates)


def _dilate_2d(mask: np.ndarray) -> np.ndarray:
    padded = np.pad(mask.astype(bool), 1, mode="constant", constant_values=False)
    return (
        padded[1:-1, 1:-1]
        | padded[:-2, 1:-1]
        | padded[2:, 1:-1]
        | padded[1:-1, :-2]
        | padded[1:-1, 2:]
    )


def _component_masks(mask: np.ndarray) -> list[np.ndarray]:
    visited = np.zeros_like(mask, dtype=bool)
    components: list[np.ndarray] = []
    width, depth = mask.shape
    for start_x, start_z in np.argwhere(mask):
        start = (int(start_x), int(start_z))
        if visited[start]:
            continue
        component = np.zeros_like(mask, dtype=bool)
        queue = deque([start])
        visited[start] = True
        while queue:
            x, z = queue.popleft()
            component[x, z] = True
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx, nz = x + dx, z + dz
                if 0 <= nx < width and 0 <= nz < depth and mask[nx, nz] and not visited[nx, nz]:
                    visited[nx, nz] = True
                    queue.append((nx, nz))
        components.append(component)
    return components


def _patch_to_stable(component: np.ndarray, layer_mask: np.ndarray, stable_mask: np.ndarray, max_growth: int = 3) -> np.ndarray:
    patch = component.astype(bool).copy()
    for _ in range(max_growth + 1):
        if (patch & stable_mask).any():
            return patch
        patch = _dilate_2d(patch) & layer_mask
    return patch


def _regularize_patch(patch: np.ndarray, layer_mask: np.ndarray) -> np.ndarray:
    points = np.argwhere(patch)
    if len(points) == 0:
        return patch
    min_x, min_z = points.min(axis=0)
    max_x, max_z = points.max(axis=0) + 1
    rectangle = np.zeros_like(patch, dtype=bool)
    rectangle[min_x:max_x, min_z:max_z] = True
    rectangle &= layer_mask
    if not patch[~rectangle].any():
        extra = int(rectangle.sum() - patch.sum())
        if extra <= max(4, int(np.ceil(patch.sum() * 0.6))):
            return rectangle
    return patch


def _top_clear(brick_occupancy: np.ndarray, y: int, x: int, z: int, width: int, depth: int) -> bool:
    return y + 1 >= brick_occupancy.shape[1] or not brick_occupancy[x : x + width, y + 1, z : z + depth].any()


def _tile_plate_patch(
    patch: np.ndarray,
    *,
    y: int,
    color_id: int,
    brick_occupancy: np.ndarray,
    problem_mask: np.ndarray,
    stable_mask: np.ndarray,
) -> tuple[list[Brick], np.ndarray]:
    used = np.zeros_like(patch, dtype=bool)
    plates: list[Brick] = []
    for x, z in np.argwhere(problem_mask):
        x = int(x)
        z = int(z)
        if used[x, z]:
            continue
        selected: tuple[int, int, int, str] | None = None
        for _area, width, depth, rotation, part_id in PLATE_SPECS:
            min_x = max(0, x - width + 1)
            max_x = min(x, patch.shape[0] - width)
            min_z = max(0, z - depth + 1)
            max_z = min(z, patch.shape[1] - depth)
            for plate_x in range(min_x, max_x + 1):
                for plate_z in range(min_z, max_z + 1):
                    footprint = (slice(plate_x, plate_x + width), slice(plate_z, plate_z + depth))
                    if used[footprint].any():
                        continue
                    if not patch[footprint].all():
                        continue
                    if not problem_mask[footprint].any():
                        continue
                    if not stable_mask[footprint].any():
                        continue
                    if not _top_clear(brick_occupancy, y, plate_x, plate_z, width, depth):
                        continue
                    selected = (plate_x, plate_z, width, depth, rotation, part_id)
                    break
                if selected is not None:
                    break
            if selected is not None:
                break
        if selected is None:
            continue
        plate_x, plate_z, width, depth, rotation, part_id = selected
        plate_y = float(y) + PLATE_LAYER_OFFSET
        plates.append(
            Brick(
                part_id=part_id,
                color_id=int(color_id),
                x=plate_x,
                y=plate_y,
                z=plate_z,
                width=width,
                depth=depth,
                height=0,
                rotation_degrees=rotation,
            )
        )
        used[plate_x : plate_x + width, plate_z : plate_z + depth] = True
    return plates, used


def _brick_mask(bricks: list[Brick], shape: tuple[int, int]) -> np.ndarray:
    mask = np.zeros(shape, dtype=bool)
    for brick in bricks:
        mask[brick.x : brick.x + brick.width, brick.z : brick.z + brick.depth] = True
    return mask


def _brick_covered_by_mask(brick: Brick, mask: np.ndarray) -> bool:
    return bool(mask[brick.x : brick.x + brick.width, brick.z : brick.z + brick.depth].any())


def _is_resolved_by_plates(brick: Brick, plates: list[Brick], stable_bricks: list[Brick]) -> bool:
    for plate in plates:
        if int(plate.y) != brick.y:
            continue
        if _overlap_area(brick, plate) == 0:
            continue
        if any(stable.y == brick.y and _overlap_area(stable, plate) > 0 for stable in stable_bricks):
            return True
    return False


def _support_part_for_brick(brick: Brick) -> tuple[str, int, int, int]:
    candidates: list[tuple[int, int, int, str]] = []
    support_parts: dict[tuple[int, int], str] = {
        (1, 1): "3005.dat",
        (2, 1): "3004.dat",
        (3, 1): "3622.dat",
        (4, 1): "3010.dat",
        (6, 1): "3009.dat",
        (8, 1): "3008.dat",
        (2, 2): "3003.dat",
        (3, 2): "3002.dat",
        (4, 2): "3001.dat",
        (6, 2): "2456.dat",
        (8, 2): "3007.dat",
    }
    for (width, depth), part_id in support_parts.items():
        for support_width, support_depth, rotation in ((width, depth, 0), (depth, width, 90)):
            if support_width >= brick.width and support_depth >= brick.depth:
                candidates.append((support_width * support_depth, support_width, support_depth, rotation, part_id))
    if not candidates:
        return "3005.dat", brick.width, brick.depth, 0
    _area, width, depth, rotation, part_id = min(candidates)
    return part_id, int(width), int(depth), int(rotation)


def _fallback_support_bricks(unresolved: list[Brick], brick_occupancy: np.ndarray) -> list[Brick]:
    supports: list[Brick] = []
    occupied_keys: set[tuple[int, int, int, int, int]] = set()
    for brick in unresolved:
        if not isinstance(brick.y, int) or brick.y <= 0:
            continue
        part_id, width, depth, rotation = _support_part_for_brick(brick)
        x = min(max(0, brick.x), max(0, brick_occupancy.shape[0] - width))
        z = min(max(0, brick.z), max(0, brick_occupancy.shape[2] - depth))
        if brick_occupancy[x : x + width, brick.y - 1, z : z + depth].any():
            continue
        key = (brick.y - 1, x, z, width, depth)
        if key in occupied_keys:
            continue
        occupied_keys.add(key)
        supports.append(
            Brick(
                part_id=part_id,
                color_id=int(brick.color_id),
                x=x,
                y=brick.y - 1,
                z=z,
                width=width,
                depth=depth,
                height=1,
                rotation_degrees=rotation,
            )
        )
    return supports


def add_attachment_plates(
    bricks: list[Brick],
    occupancy_shape: tuple[int, int, int],
) -> tuple[list[Brick], dict]:
    """Add clean plate patches over fully unattached same-layer regions.

    The plates are attachment-only parts: they are written to LDR output but
    intentionally excluded from exact-cover voxel metrics.
    """

    by_layer: dict[int, list[Brick]] = {}
    for brick in bricks:
        if isinstance(brick.y, int):
            by_layer.setdefault(brick.y, []).append(brick)

    brick_occupancy = np.zeros(occupancy_shape, dtype=bool)
    for brick in bricks:
        if not isinstance(brick.y, int):
            continue
        brick_occupancy[
            brick.x : brick.x + brick.width,
            brick.y : brick.y + brick.height,
            brick.z : brick.z + brick.depth,
        ] = True

    stable_by_layer: dict[int, list[Brick]] = {}
    unattached_by_layer: dict[int, list[Brick]] = {}
    unattached: list[Brick] = []
    for brick in bricks:
        if not isinstance(brick.y, int):
            continue
        has_lower = brick.y <= 0 or support_ratio_for_area(
            brick_occupancy,
            brick.x,
            brick.y,
            brick.z,
            brick.width,
            brick.depth,
        ) > 0.0
        has_upper = _has_neighbor(brick, by_layer.get(brick.y + 1, []))
        if has_lower or has_upper:
            stable_by_layer.setdefault(brick.y, []).append(brick)
        elif brick.y > 0:
            unattached_by_layer.setdefault(brick.y, []).append(brick)
            unattached.append(brick)

    plates: list[Brick] = []
    covered_masks_by_layer: dict[int, np.ndarray] = {}
    for y, layer_unattached in unattached_by_layer.items():
        layer_mask = _brick_mask(by_layer.get(y, []), (occupancy_shape[0], occupancy_shape[2]))
        unattached_mask = _brick_mask(layer_unattached, layer_mask.shape)
        stable_mask = _brick_mask(stable_by_layer.get(y, []), layer_mask.shape)
        covered_masks_by_layer.setdefault(y, np.zeros_like(layer_mask, dtype=bool))

        for component in _component_masks(unattached_mask):
            patch = _patch_to_stable(component, layer_mask, stable_mask)
            if not (patch & stable_mask).any():
                continue
            patch = _regularize_patch(patch, layer_mask)
            patch &= ~covered_masks_by_layer[y]
            if not patch.any():
                continue
            color_id = int(layer_unattached[0].color_id)
            selected_plates, used = _tile_plate_patch(
                patch,
                y=y,
                color_id=color_id,
                brick_occupancy=brick_occupancy,
                problem_mask=component,
                stable_mask=stable_mask,
            )
            if not selected_plates:
                continue

            plates.extend(selected_plates)
            covered_masks_by_layer[y] |= used

    stable_bricks = [brick for layer in stable_by_layer.values() for brick in layer]
    plate_resolved = {brick for brick in unattached if _is_resolved_by_plates(brick, plates, stable_bricks)}
    unresolved = [brick for brick in unattached if brick not in plate_resolved]
    support_bricks = _fallback_support_bricks(unresolved, brick_occupancy)
    support_resolved = {
        brick
        for brick in unresolved
        if any(
            support.y == brick.y - 1 and _overlap_area(support, brick) > 0
            for support in support_bricks
        )
    }
    resolved = plate_resolved | support_resolved
    return [*plates, *support_bricks], {
        "attachment_plate_count": int(len(plates)),
        "attachment_plate_strategy": "layer_patch",
        "fallback_support_brick_count": int(len(support_bricks)),
        "bidirectional_unattached_before_plates": int(len(unattached)),
        "resolved_bidirectional_unattached_count": int(len(resolved)),
        "remaining_bidirectional_unattached_count": int(len(unattached) - len(resolved)),
        "plate_layer_offset_bricks": PLATE_LAYER_OFFSET,
    }
