from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from makeyourbrick.types import Brick, BrickSpec


DEFAULT_BRICKS = (
    BrickSpec("3006.dat", 2, 10),
    BrickSpec("3007.dat", 2, 8),
    BrickSpec("2456.dat", 2, 6),
    BrickSpec("3001.dat", 2, 4),
    BrickSpec("3008.dat", 1, 8),
    BrickSpec("3002.dat", 2, 3),
    BrickSpec("3009.dat", 1, 6),
    BrickSpec("3010.dat", 1, 4),
    BrickSpec("3003.dat", 2, 2),
    BrickSpec("3622.dat", 1, 3),
    BrickSpec("3004.dat", 1, 2),
    BrickSpec("3005.dat", 1, 1),
)

STUDIO_SCULPTURE_BRICKS = (
    BrickSpec("3008.dat", 1, 8),
    BrickSpec("3007.dat", 2, 8),
    BrickSpec("3009.dat", 1, 6),
    BrickSpec("2456.dat", 2, 6),
    BrickSpec("3010.dat", 1, 4),
    BrickSpec("3001.dat", 2, 4),
    BrickSpec("3622.dat", 1, 3),
    BrickSpec("3002.dat", 2, 3),
    BrickSpec("3004.dat", 1, 2),
    BrickSpec("3003.dat", 2, 2),
    BrickSpec("3005.dat", 1, 1),
)

COMPACT_SCULPTURE_BRICKS = (
    BrickSpec("3010.dat", 1, 4),
    BrickSpec("3001.dat", 2, 4),
    BrickSpec("3622.dat", 1, 3),
    BrickSpec("3002.dat", 2, 3),
    BrickSpec("3004.dat", 1, 2),
    BrickSpec("3003.dat", 2, 2),
    BrickSpec("3005.dat", 1, 1),
)

PLATE_SCULPTURE_BRICKS = (
    BrickSpec("3020.dat", 2, 4),
    BrickSpec("3710.dat", 1, 4),
    BrickSpec("3021.dat", 2, 3),
    BrickSpec("3022.dat", 2, 2),
    BrickSpec("3023.dat", 1, 2),
    BrickSpec("3024.dat", 1, 1),
)

BRICK_PALETTES = ("full", "studio", "compact", "plates")


def brick_specs_for_palette(palette: str) -> tuple[BrickSpec, ...]:
    if palette == "full":
        return DEFAULT_BRICKS
    if palette == "studio":
        return STUDIO_SCULPTURE_BRICKS
    if palette == "compact":
        return COMPACT_SCULPTURE_BRICKS
    if palette == "plates":
        return PLATE_SCULPTURE_BRICKS
    raise ValueError(f"Unsupported brick palette: {palette}")


def _validate_voxel_inputs(occupancy: np.ndarray, color_ids: np.ndarray) -> None:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    if color_ids.shape != occupancy.shape:
        raise ValueError("Color id array must have the same shape as occupancy.")


def iter_occupied_voxels(occupancy: np.ndarray):
    """Yield occupied voxel coordinates bottom-up, then depth, then width."""
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    width, height, depth = occupancy.shape
    for y in range(height):
        for z in range(depth):
            for x in range(width):
                if occupancy[x, y, z]:
                    yield x, y, z


def iter_layer_voxels(occupancy: np.ndarray, y: int):
    """Yield occupied voxel coordinates for one layer, then depth, then width."""
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    width, _height, depth = occupancy.shape
    for z in range(depth):
        for x in range(width):
            if occupancy[x, y, z]:
                yield x, y, z


def brickify_1x1(occupancy: np.ndarray, color_ids: np.ndarray, part_id: str = "3005.dat") -> list[Brick]:
    _validate_voxel_inputs(occupancy, color_ids)
    bricks: list[Brick] = []
    for x, y, z in iter_occupied_voxels(occupancy):
        bricks.append(
            Brick(
                part_id=part_id,
                color_id=int(color_ids[x, y, z]),
                x=int(x),
                y=int(y),
                z=int(z),
                width=1,
                depth=1,
            )
        )
    return bricks


def candidate_orientations(spec: BrickSpec, allow_rotations: bool = True) -> tuple[tuple[int, int, int], ...]:
    orientations = [(spec.width, spec.depth, 0)]
    if allow_rotations and spec.width != spec.depth:
        orientations.append((spec.depth, spec.width, 90))
    return tuple(orientations)


def can_place_brick(
    occupancy: np.ndarray,
    used: np.ndarray,
    color_ids: np.ndarray,
    x: int,
    y: int,
    z: int,
    width: int,
    depth: int,
    height: int,
    color_id: int,
) -> bool:
    max_x, max_y, max_z = occupancy.shape
    if x + width > max_x or y + height > max_y or z + depth > max_z:
        return False
    x_slice = slice(x, x + width)
    y_slice = slice(y, y + height)
    z_slice = slice(z, z + depth)
    volume = occupancy[x_slice, y_slice, z_slice]
    if not volume.all():
        return False
    if used[x_slice, y_slice, z_slice].any():
        return False
    return bool((color_ids[x_slice, y_slice, z_slice] == color_id).all())


def mark_used(used: np.ndarray, brick: Brick) -> None:
    used[
        brick.x : brick.x + brick.width,
        brick.y : brick.y + brick.height,
        brick.z : brick.z + brick.depth,
    ] = True


@dataclass(frozen=True)
class PlacementCandidate:
    spec_index: int
    part_id: str
    color_id: int
    x: int
    z: int
    width: int
    depth: int
    height: int
    rotation_degrees: int = 0

    @property
    def area(self) -> int:
        return int(self.width * self.depth)


def support_ratio_for_area(
    occupied_or_used: np.ndarray,
    x: int,
    y: int,
    z: int,
    width: int,
    depth: int,
) -> float:
    if y <= 0:
        return 1.0
    support = occupied_or_used[x : x + width, y - 1, z : z + depth]
    area = width * depth
    return float(support.sum() / area) if area else 0.0


def horizontal_boundary_ratio(
    occupancy: np.ndarray,
    x: int,
    y: int,
    z: int,
    width: int,
    depth: int,
) -> float:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    area = width * depth
    if area <= 0:
        return 0.0
    boundary_cells = 0
    max_x, _max_y, max_z = occupancy.shape
    for cx in range(x, x + width):
        for cz in range(z, z + depth):
            for dx, dz in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nx = cx + dx
                nz = cz + dz
                if not (0 <= nx < max_x and 0 <= nz < max_z) or not occupancy[nx, y, nz]:
                    boundary_cells += 1
                    break
    return float(boundary_cells / area)


def seam_overlap_ratio(bricks: list[Brick], y: int, x: int, z: int, width: int, depth: int) -> float:
    lower_layer = [brick for brick in bricks if brick.y == y - 1]
    if y <= 0 or not lower_layer:
        return 0.0
    current_edges = set()
    for edge_x in (x, x + width):
        for edge_z in range(z, z + depth + 1):
            current_edges.add(("x", edge_x, edge_z))
    for edge_z in (z, z + depth):
        for edge_x in range(x, x + width + 1):
            current_edges.add(("z", edge_z, edge_x))
    lower_edges = set()
    for brick in lower_layer:
        for edge_x in (brick.x, brick.x + brick.width):
            for edge_z in range(brick.z, brick.z + brick.depth + 1):
                lower_edges.add(("x", edge_x, edge_z))
        for edge_z in (brick.z, brick.z + brick.depth):
            for edge_x in range(brick.x, brick.x + brick.width + 1):
                lower_edges.add(("z", edge_z, edge_x))
    if not current_edges:
        return 0.0
    return len(current_edges.intersection(lower_edges)) / len(current_edges)


def _layer_candidate_color_id(layer_colors: np.ndarray, x: int, z: int, width: int, depth: int) -> int | None:
    colors = layer_colors[x : x + width, z : z + depth]
    colors = colors[colors > 0]
    if not len(colors):
        return None
    color_id = int(colors[0])
    if not np.all(colors == color_id):
        return None
    return color_id


def _generate_layer_candidates(
    layer_occupancy: np.ndarray,
    layer_colors: np.ndarray,
    brick_specs: tuple[BrickSpec, ...],
    *,
    allow_rotations: bool = True,
) -> list[PlacementCandidate]:
    candidates: list[PlacementCandidate] = []
    width_limit, depth_limit = layer_occupancy.shape
    for spec_index, spec in enumerate(brick_specs):
        if spec.height != 1:
            continue
        for width, depth, rotation_degrees in candidate_orientations(spec, allow_rotations):
            if width > width_limit or depth > depth_limit:
                continue
            for x in range(width_limit - width + 1):
                for z in range(depth_limit - depth + 1):
                    footprint = layer_occupancy[x : x + width, z : z + depth]
                    if not footprint.all():
                        continue
                    color_id = _layer_candidate_color_id(layer_colors, x, z, width, depth)
                    if color_id is None:
                        continue
                    candidates.append(
                        PlacementCandidate(
                            spec_index=spec_index,
                            part_id=spec.part_id,
                            color_id=color_id,
                            x=int(x),
                            z=int(z),
                            width=int(width),
                            depth=int(depth),
                            height=int(spec.height),
                            rotation_degrees=int(rotation_degrees),
                        )
                    )
    return candidates


def _candidate_overlaps_used(candidate: PlacementCandidate, used_layer: np.ndarray) -> bool:
    return bool(used_layer[candidate.x : candidate.x + candidate.width, candidate.z : candidate.z + candidate.depth].any())


def _connectible_side_count(width: int, depth: int) -> int:
    return int((width * 2) + (depth * 2))


def _same_layer_neighbor_ratio(candidate: PlacementCandidate, placement_map: np.ndarray) -> float:
    touched = 0
    total = _connectible_side_count(candidate.width, candidate.depth)
    for x in range(candidate.x, candidate.x + candidate.width):
        for z in (candidate.z - 1, candidate.z + candidate.depth):
            if 0 <= z < placement_map.shape[1] and placement_map[x, z] >= 0:
                touched += 1
    for z in range(candidate.z, candidate.z + candidate.depth):
        for x in (candidate.x - 1, candidate.x + candidate.width):
            if 0 <= x < placement_map.shape[0] and placement_map[x, z] >= 0:
                touched += 1
    return float(touched / total) if total else 0.0


def _previous_layer_connection(
    candidate: PlacementCandidate,
    previous_placement_map: np.ndarray | None,
) -> tuple[float, int]:
    if previous_placement_map is None:
        return 1.0, candidate.area
    previous = previous_placement_map[
        candidate.x : candidate.x + candidate.width,
        candidate.z : candidate.z + candidate.depth,
    ]
    supported = previous >= 0
    support_ratio = float(supported.sum() / candidate.area) if candidate.area else 0.0
    connected_ids = set(int(value) for value in previous[supported])
    return support_ratio, len(connected_ids)


def reward_candidate_score(
    candidate: PlacementCandidate,
    *,
    y: int,
    max_area: int,
    current_placement_map: np.ndarray,
    previous_placement_map: np.ndarray | None,
) -> float:
    """Score one slice placement using BrickFormer-style reward terms."""

    area_score = candidate.area / max(1, max_area)
    neighbor_score = _same_layer_neighbor_ratio(candidate, current_placement_map)
    support_ratio, connected_bricks = _previous_layer_connection(candidate, previous_placement_map)
    connected_score = min(1.0, connected_bricks / max(1, candidate.area))
    unsupported_penalty = (1.0 - support_ratio) * (1.8 if y > 0 else 0.0)
    long_axis_penalty = max(0, max(candidate.width, candidate.depth) - 6) * 0.04
    return (
        (area_score * 2.8)
        + (support_ratio * 2.2)
        + (connected_score * 1.1)
        + (neighbor_score * 0.7)
        - unsupported_penalty
        - long_axis_penalty
    )


def _candidate_to_brick(candidate: PlacementCandidate, y: int) -> Brick:
    return Brick(
        part_id=candidate.part_id,
        color_id=candidate.color_id,
        x=candidate.x,
        y=int(y),
        z=candidate.z,
        width=candidate.width,
        depth=candidate.depth,
        height=candidate.height,
        rotation_degrees=candidate.rotation_degrees,
    )


def reward_layered_brickify(
    occupancy: np.ndarray,
    color_ids: np.ndarray,
    brick_specs: tuple[BrickSpec, ...] = DEFAULT_BRICKS,
    allow_rotations: bool = True,
) -> list[Brick]:
    _validate_voxel_inputs(occupancy, color_ids)
    max_area = max((spec.width * spec.depth for spec in brick_specs if spec.height == 1), default=1)
    bricks: list[Brick] = []
    previous_placement_map: np.ndarray | None = None

    for y in range(occupancy.shape[1]):
        layer_occupancy = occupancy[:, y, :]
        if not layer_occupancy.any():
            previous_placement_map = None
            continue
        layer_colors = color_ids[:, y, :]
        used_layer = np.zeros(layer_occupancy.shape, dtype=bool)
        current_placement_map = np.full(layer_occupancy.shape, -1, dtype=np.int32)
        candidates = _generate_layer_candidates(
            layer_occupancy,
            layer_colors,
            brick_specs,
            allow_rotations=allow_rotations,
        )
        next_pid = 0

        while True:
            uncovered = layer_occupancy & ~used_layer
            if not uncovered.any():
                break

            best: tuple[tuple[float, int, int, int, int], PlacementCandidate] | None = None
            for candidate in candidates:
                if _candidate_overlaps_used(candidate, used_layer):
                    continue
                score = reward_candidate_score(
                    candidate,
                    y=y,
                    max_area=max_area,
                    current_placement_map=current_placement_map,
                    previous_placement_map=previous_placement_map,
                )
                rank = (score, candidate.area, -candidate.spec_index, -candidate.x, -candidate.z)
                if best is None or rank > best[0]:
                    best = (rank, candidate)

            if best is None:
                x, z = (int(value) for value in np.argwhere(uncovered)[0])
                candidate = PlacementCandidate(
                    spec_index=len(brick_specs),
                    part_id="3005.dat",
                    color_id=int(color_ids[x, y, z]),
                    x=x,
                    z=z,
                    width=1,
                    depth=1,
                    height=1,
                    rotation_degrees=0,
                )
            else:
                candidate = best[1]

            brick = _candidate_to_brick(candidate, y)
            bricks.append(brick)
            used_layer[brick.x : brick.x + brick.width, brick.z : brick.z + brick.depth] = True
            current_placement_map[brick.x : brick.x + brick.width, brick.z : brick.z + brick.depth] = next_pid
            next_pid += 1

        previous_placement_map = current_placement_map

    return bricks


def greedy_brickify(
    occupancy: np.ndarray,
    color_ids: np.ndarray,
    brick_specs: tuple[BrickSpec, ...] = DEFAULT_BRICKS,
    allow_rotations: bool = True,
) -> list[Brick]:
    _validate_voxel_inputs(occupancy, color_ids)
    used = np.zeros_like(occupancy, dtype=bool)
    bricks: list[Brick] = []

    for x, y, z in iter_occupied_voxels(occupancy):
        if used[x, y, z]:
            continue
        color_id = int(color_ids[x, y, z])
        placed = False
        for spec in brick_specs:
            for width, depth, rotation_degrees in candidate_orientations(spec, allow_rotations):
                if can_place_brick(
                    occupancy,
                    used,
                    color_ids,
                    x,
                    y,
                    z,
                    width,
                    depth,
                    spec.height,
                    color_id,
                ):
                    brick = Brick(
                        part_id=spec.part_id,
                        color_id=color_id,
                        x=int(x),
                        y=int(y),
                        z=int(z),
                        width=int(width),
                        depth=int(depth),
                        height=int(spec.height),
                        rotation_degrees=rotation_degrees,
                    )
                    bricks.append(brick)
                    mark_used(used, brick)
                    placed = True
                    break
            if placed:
                break
        if not placed:
            brick = Brick(
                part_id="3005.dat",
                color_id=color_id,
                x=int(x),
                y=int(y),
                z=int(z),
                width=1,
                depth=1,
            )
            bricks.append(brick)
            mark_used(used, brick)
    return bricks


def layered_candidate_score(
    *,
    placed_bricks: list[Brick],
    used: np.ndarray,
    occupancy: np.ndarray | None = None,
    x: int,
    y: int,
    z: int,
    width: int,
    depth: int,
) -> float:
    area = width * depth
    support_ratio = support_ratio_for_area(used, x, y, z, width, depth)
    unsupported_cells = area * (1.0 - support_ratio)
    seam_overlap = seam_overlap_ratio(placed_bricks, y, x, z, width, depth)
    overhang_penalty = unsupported_cells * 12.0 if y > 0 else 0.0
    weak_support_penalty = 18.0 if 0 < support_ratio < 0.5 else 0.0
    boundary_ratio = horizontal_boundary_ratio(occupancy, x, y, z, width, depth) if occupancy is not None else 0.0
    long_axis = max(width, depth)
    boundary_length_penalty = max(0, long_axis - 4) * boundary_ratio * 20.0
    return (
        (area * 6.0)
        + (support_ratio * 30.0)
        - overhang_penalty
        - weak_support_penalty
        - (seam_overlap * 6.0)
        - boundary_length_penalty
    )


def layered_brickify(
    occupancy: np.ndarray,
    color_ids: np.ndarray,
    brick_specs: tuple[BrickSpec, ...] = DEFAULT_BRICKS,
    allow_rotations: bool = True,
) -> list[Brick]:
    _validate_voxel_inputs(occupancy, color_ids)
    used = np.zeros_like(occupancy, dtype=bool)
    bricks: list[Brick] = []

    for y in range(occupancy.shape[1]):
        for x, _y, z in iter_layer_voxels(occupancy, y):
            if used[x, y, z]:
                continue
            color_id = int(color_ids[x, y, z])
            candidates: list[tuple[float, int, Brick]] = []
            for spec_index, spec in enumerate(brick_specs):
                for width, depth, rotation_degrees in candidate_orientations(spec, allow_rotations):
                    if can_place_brick(
                        occupancy,
                        used,
                        color_ids,
                        x,
                        y,
                        z,
                        width,
                        depth,
                        spec.height,
                        color_id,
                    ):
                        score = layered_candidate_score(
                            placed_bricks=bricks,
                            used=used,
                            occupancy=occupancy,
                            x=x,
                            y=y,
                            z=z,
                            width=width,
                            depth=depth,
                        )
                        candidates.append(
                            (
                                score,
                                -spec_index,
                                Brick(
                                    part_id=spec.part_id,
                                    color_id=color_id,
                                    x=int(x),
                                    y=int(y),
                                    z=int(z),
                                    width=int(width),
                                    depth=int(depth),
                                    height=int(spec.height),
                                    rotation_degrees=rotation_degrees,
                                ),
                            )
                        )
            if candidates:
                _score, _spec_order, brick = max(candidates, key=lambda item: (item[0], item[1]))
            else:
                brick = Brick(
                    part_id="3005.dat",
                    color_id=color_id,
                    x=int(x),
                    y=int(y),
                    z=int(z),
                    width=1,
                    depth=1,
                )
            bricks.append(brick)
            mark_used(used, brick)
    return bricks


def bricks_to_occupancy(bricks: list[Brick], shape: tuple[int, int, int]) -> np.ndarray:
    occupancy = np.zeros(shape, dtype=bool)
    for brick in bricks:
        x_slice = slice(brick.x, brick.x + brick.width)
        y_slice = slice(brick.y, brick.y + brick.height)
        z_slice = slice(brick.z, brick.z + brick.depth)
        occupancy[x_slice, y_slice, z_slice] = True
    return occupancy
