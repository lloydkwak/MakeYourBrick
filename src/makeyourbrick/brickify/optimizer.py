from __future__ import annotations

from collections import defaultdict

import numpy as np

from makeyourbrick.types import Brick, BrickSpec

STUDIO_SCULPTURE_BRICKS = (
    BrickSpec("3010.dat", 4, 1),
    BrickSpec("3001.dat", 4, 2),
    BrickSpec("3008.dat", 8, 1),
    BrickSpec("3009.dat", 6, 1),
    BrickSpec("3622.dat", 3, 1),
    BrickSpec("3004.dat", 2, 1),
    BrickSpec("3002.dat", 3, 2),
    BrickSpec("3007.dat", 8, 2),
    BrickSpec("2456.dat", 6, 2),
    BrickSpec("3003.dat", 2, 2),
    BrickSpec("3005.dat", 1, 1),
)

STUDIO_SPAN_1_LENGTH_PRIORITY = {8: 0, 6: 1, 4: 2, 3: 3, 2: 4, 1: 5}
STUDIO_SPAN_2_PART_PRIORITY = {
    "3001.dat": 0,
    "3002.dat": 1,
    "3007.dat": 2,
    "2456.dat": 3,
    "3003.dat": 4,
}


def _validate_voxel_inputs(occupancy: np.ndarray, color_ids: np.ndarray) -> None:
    if occupancy.ndim != 3:
        raise ValueError("Occupancy must be a 3D array.")
    if color_ids.shape != occupancy.shape:
        raise ValueError("Color id array must match occupancy shape.")


def brickify_1x1(occupancy: np.ndarray, color_ids: np.ndarray) -> list[Brick]:
    _validate_voxel_inputs(occupancy, color_ids)
    bricks: list[Brick] = []
    for x, y, z in np.argwhere(occupancy):
        bricks.append(
            Brick(
                part_id="3005.dat",
                color_id=int(color_ids[int(x), int(y), int(z)]),
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


def _run_specs_for_axis(
    brick_specs: tuple[BrickSpec, ...],
    *,
    axis: str,
    allow_rotations: bool = True,
) -> dict[int, list[tuple[int, str, int, int, int]]]:
    specs_by_span: dict[int, list[tuple[int, str, int, int, int]]] = defaultdict(list)
    for spec in brick_specs:
        for width, depth, rotation in candidate_orientations(spec, allow_rotations):
            if axis == "x" and depth <= 2:
                specs_by_span[depth].append((width, spec.part_id, width, depth, rotation))
            elif axis == "z" and width <= 2:
                specs_by_span[width].append((depth, spec.part_id, width, depth, rotation))
    for span, specs in specs_by_span.items():
        if span == 1:
            specs.sort(key=lambda item: (STUDIO_SPAN_1_LENGTH_PRIORITY.get(item[0], 999), item[1]))
        elif span == 2:
            specs.sort(key=lambda item: (STUDIO_SPAN_2_PART_PRIORITY.get(item[1], 999), item[0], item[1]))
        else:
            specs.sort(key=lambda item: (-item[0], item[1]))
    return dict(specs_by_span)


def _work_arrays(layer_occupancy: np.ndarray, layer_colors: np.ndarray, axis: str) -> tuple[np.ndarray, np.ndarray]:
    if axis == "x":
        return layer_occupancy, layer_colors
    if axis == "z":
        return layer_occupancy.T, layer_colors.T
    raise ValueError(f"Unsupported axis: {axis}")


def _footprint_color(
    work_occupancy: np.ndarray,
    work_colors: np.ndarray,
    used: np.ndarray,
    primary: int,
    secondary: int,
    length: int,
    span: int,
) -> int | None:
    if primary + length > work_occupancy.shape[0] or secondary + span > work_occupancy.shape[1]:
        return None
    footprint = work_occupancy[primary : primary + length, secondary : secondary + span]
    if not footprint.all():
        return None
    if used[primary : primary + length, secondary : secondary + span].any():
        return None
    colors = work_colors[primary : primary + length, secondary : secondary + span]
    colors = colors[colors > 0]
    if len(colors) == 0:
        return None
    color_id = int(colors[0])
    return color_id if bool(np.all(colors == color_id)) else None


def _brick_from_work(
    *,
    axis: str,
    primary: int,
    secondary: int,
    y: int,
    part_id: str,
    color_id: int,
    width: int,
    depth: int,
    rotation_degrees: int,
) -> Brick:
    if axis == "x":
        x, z = primary, secondary
    elif axis == "z":
        x, z = secondary, primary
    else:
        raise ValueError(f"Unsupported axis: {axis}")
    return Brick(
        part_id=part_id,
        color_id=color_id,
        x=int(x),
        y=int(y),
        z=int(z),
        width=int(width),
        depth=int(depth),
        rotation_degrees=int(rotation_degrees),
    )


def _mark_used(used: np.ndarray, brick: Brick, axis: str) -> None:
    if axis == "x":
        used[brick.x : brick.x + brick.width, brick.z : brick.z + brick.depth] = True
    else:
        used[brick.z : brick.z + brick.depth, brick.x : brick.x + brick.width] = True


def _first_fitting_brick(
    *,
    work_occupancy: np.ndarray,
    work_colors: np.ndarray,
    used: np.ndarray,
    axis: str,
    y: int,
    primary: int,
    secondary: int,
    max_length: int,
    span: int,
    specs: list[tuple[int, str, int, int, int]],
) -> Brick | None:
    for length, part_id, width, depth, rotation in specs:
        if length > max_length:
            continue
        color_id = _footprint_color(work_occupancy, work_colors, used, primary, secondary, length, span)
        if color_id is None:
            continue
        return _brick_from_work(
            axis=axis,
            primary=primary,
            secondary=secondary,
            y=y,
            part_id=part_id,
            color_id=color_id,
            width=width,
            depth=depth,
            rotation_degrees=rotation,
        )
    return None


def _fill_stripe(
    *,
    work_occupancy: np.ndarray,
    work_colors: np.ndarray,
    used: np.ndarray,
    axis: str,
    y: int,
    secondary: int,
    span: int,
    specs: list[tuple[int, str, int, int, int]],
) -> list[Brick]:
    bricks: list[Brick] = []
    primary = 0
    while primary < work_occupancy.shape[0]:
        color_id = _footprint_color(work_occupancy, work_colors, used, primary, secondary, 1, span)
        if color_id is None:
            primary += 1
            continue

        run_end = primary
        while run_end < work_occupancy.shape[0]:
            if _footprint_color(work_occupancy, work_colors, used, run_end, secondary, 1, span) != color_id:
                break
            run_end += 1

        cursor = primary
        while cursor < run_end:
            brick = _first_fitting_brick(
                work_occupancy=work_occupancy,
                work_colors=work_colors,
                used=used,
                axis=axis,
                y=y,
                primary=cursor,
                secondary=secondary,
                max_length=run_end - cursor,
                span=span,
                specs=specs,
            )
            if brick is None:
                brick = _brick_from_work(
                    axis=axis,
                    primary=cursor,
                    secondary=secondary,
                    y=y,
                    part_id="3005.dat",
                    color_id=color_id,
                    width=1,
                    depth=1,
                    rotation_degrees=0,
                )
            bricks.append(brick)
            _mark_used(used, brick, axis)
            cursor += brick.width if axis == "x" else brick.depth
        primary = run_end
    return bricks


def _tile_layer(
    layer_occupancy: np.ndarray,
    layer_colors: np.ndarray,
    brick_specs: tuple[BrickSpec, ...],
    *,
    axis: str,
    pair_offset: int,
    y: int,
    allow_rotations: bool,
    span_order: tuple[int, ...] = (2, 1),
) -> list[Brick]:
    work_occupancy, work_colors = _work_arrays(layer_occupancy, layer_colors, axis)
    used = np.zeros(work_occupancy.shape, dtype=bool)
    specs_by_span = _run_specs_for_axis(brick_specs, axis=axis, allow_rotations=allow_rotations)
    bricks: list[Brick] = []

    for span in span_order:
        if span == 2:
            secondary_values = range(pair_offset, work_occupancy.shape[1] - 1, 2)
        elif span == 1:
            secondary_values = range(work_occupancy.shape[1])
        else:
            continue
        for secondary in secondary_values:
            bricks.extend(
                _fill_stripe(
                    work_occupancy=work_occupancy,
                    work_colors=work_colors,
                    used=used,
                    axis=axis,
                    y=y,
                    secondary=secondary,
                    span=span,
                    specs=specs_by_span.get(span, []),
                )
            )

    if 1 not in span_order:
        for secondary in range(work_occupancy.shape[1]):
            bricks.extend(
                _fill_stripe(
                    work_occupancy=work_occupancy,
                    work_colors=work_colors,
                    used=used,
                    axis=axis,
                    y=y,
                    secondary=secondary,
                    span=1,
                    specs=specs_by_span.get(1, []),
                )
            )

    for primary, secondary in np.argwhere(work_occupancy & ~used):
        color_id = int(work_colors[int(primary), int(secondary)])
        brick = _brick_from_work(
            axis=axis,
            primary=int(primary),
            secondary=int(secondary),
            y=y,
            part_id="3005.dat",
            color_id=color_id,
            width=1,
            depth=1,
            rotation_degrees=0,
        )
        bricks.append(brick)
        _mark_used(used, brick, axis)
    return bricks


def _overlap_area(a: Brick, b: Brick) -> int:
    overlap_x = min(a.x + a.width, b.x + b.width) - max(a.x, b.x)
    overlap_z = min(a.z + a.depth, b.z + b.depth) - max(a.z, b.z)
    return max(0, overlap_x) * max(0, overlap_z)


def _has_vertical_neighbor(brick: Brick, neighbors: list[Brick]) -> bool:
    return any(_overlap_area(brick, other) > 0 for other in neighbors)


def _candidate_key(bricks: list[Brick]) -> tuple[tuple[str, int, int, int, int, int], ...]:
    return tuple(sorted((brick.part_id, brick.x, brick.y, brick.z, brick.width, brick.depth) for brick in bricks))


def _layer_tiling_candidates(
    layer: np.ndarray,
    layer_colors: np.ndarray,
    brick_specs: tuple[BrickSpec, ...],
    *,
    y: int,
    preferred_axis: str,
    allow_rotations: bool,
) -> list[tuple[tuple[int, int, int], list[Brick]]]:
    candidates: list[tuple[tuple[int, int, int], list[Brick]]] = []
    seen: set[tuple[tuple[str, int, int, int, int, int], ...]] = set()
    for axis in ("x", "z"):
        axis_penalty = 0 if axis == preferred_axis else 1
        for span_order_index, span_order in enumerate(((2, 1), (1, 2))):
            pair_offsets = (0, 1) if 2 in span_order and span_order[0] == 2 else (0,)
            for pair_offset in pair_offsets:
                layer_bricks = _tile_layer(
                    layer,
                    layer_colors,
                    brick_specs,
                    axis=axis,
                    pair_offset=pair_offset,
                    y=y,
                    allow_rotations=allow_rotations,
                    span_order=span_order,
                )
                key = _candidate_key(layer_bricks)
                if key in seen:
                    continue
                seen.add(key)
                candidates.append(((len(layer_bricks), axis_penalty, span_order_index), layer_bricks))
    return candidates


def _support_flags_from_lower(bricks: list[Brick], lower: list[Brick], *, y: int) -> list[bool]:
    if y <= 0:
        return [True for _ in bricks]
    return [_has_vertical_neighbor(brick, lower) for brick in bricks]


def _support_flags_from_upper(bricks: list[Brick], upper: list[Brick]) -> list[bool]:
    return [_has_vertical_neighbor(brick, upper) for brick in bricks]


def _unattached_count(
    bricks: list[Brick],
    support_from_lower: list[bool],
    upper: list[Brick],
) -> int:
    support_from_upper = _support_flags_from_upper(bricks, upper)
    return sum(
        1
        for lower_ok, upper_ok in zip(support_from_lower, support_from_upper)
        if not lower_ok and not upper_ok
    )


def _score_add(left: tuple[int, int, int, int, int], right: tuple[int, int, int, int, int]) -> tuple[int, int, int, int, int]:
    return tuple(a + b for a, b in zip(left, right))


def run_length_layered_brickify(
    occupancy: np.ndarray,
    color_ids: np.ndarray,
    brick_specs: tuple[BrickSpec, ...] = STUDIO_SCULPTURE_BRICKS,
    allow_rotations: bool = True,
) -> list[Brick]:
    """Tile each occupied layer exactly with Studio sculpture brick combinations."""

    _validate_voxel_inputs(occupancy, color_ids)
    occupied_layers = [int(y) for y in range(occupancy.shape[1]) if occupancy[:, y, :].any()]
    if not occupied_layers:
        return []

    layer_candidates: dict[int, list[tuple[tuple[int, int, int], list[Brick]]]] = {}
    for y in occupied_layers:
        layer = occupancy[:, y, :]
        preferred_axis = "x" if y % 2 == 0 else "z"
        layer_candidates[y] = _layer_tiling_candidates(
            layer,
            color_ids[:, y, :],
            brick_specs,
            y=y,
            preferred_axis=preferred_axis,
            allow_rotations=allow_rotations,
        )
        if not layer_candidates[y]:
            raise ValueError(f"No tiling candidates generated for occupied layer {y}.")

    # Dynamic programming over layer-level tiling candidates. A local one-step
    # lookahead can believe a brick will attach to some future candidate and
    # then choose a different upper layer later. The DP finalizes each layer only
    # after the actual next layer candidate is known.
    first_y = occupied_layers[0]
    states: list[tuple[tuple[int, int, int, int, int], list[int], list[bool]]] = []
    for index, (base_score, candidate) in enumerate(layer_candidates[first_y]):
        lower_flags = _support_flags_from_lower(candidate, [], y=first_y)
        no_lower = sum(1 for value in lower_flags if not value)
        states.append(((0, no_lower, base_score[0], base_score[1], base_score[2]), [index], lower_flags))

    for layer_position in range(1, len(occupied_layers)):
        previous_y = occupied_layers[layer_position - 1]
        y = occupied_layers[layer_position]
        adjacent = y == previous_y + 1
        previous_candidates = layer_candidates[previous_y]
        current_candidates = layer_candidates[y]
        next_states: list[tuple[tuple[int, int, int, int, int], list[int], list[bool]]] = []

        for state_score, path, previous_lower_flags in states:
            previous_bricks = previous_candidates[path[-1]][1]
            for current_index, (base_score, current_bricks) in enumerate(current_candidates):
                lower = previous_bricks if adjacent else []
                current_lower_flags = _support_flags_from_lower(current_bricks, lower, y=y)
                upper = current_bricks if adjacent else []
                finalized_unattached = _unattached_count(previous_bricks, previous_lower_flags, upper)
                no_lower = sum(1 for value in current_lower_flags if not value)
                transition_score = (
                    finalized_unattached,
                    no_lower,
                    base_score[0],
                    base_score[1],
                    base_score[2],
                )
                next_states.append((_score_add(state_score, transition_score), [*path, current_index], current_lower_flags))

        best_by_current: dict[int, tuple[tuple[int, int, int, int, int], list[int], list[bool]]] = {}
        for score, path, lower_flags in next_states:
            current_index = path[-1]
            if current_index not in best_by_current or score < best_by_current[current_index][0]:
                best_by_current[current_index] = (score, path, lower_flags)
        states = list(best_by_current.values())

    last_y = occupied_layers[-1]
    last_candidates = layer_candidates[last_y]
    finalized_states: list[tuple[tuple[int, int, int, int, int], list[int]]] = []
    for score, path, lower_flags in states:
        last_bricks = last_candidates[path[-1]][1]
        final_unattached = _unattached_count(last_bricks, lower_flags, [])
        finalized_states.append((_score_add(score, (final_unattached, 0, 0, 0, 0)), path))

    _best_score, best_path = min(finalized_states, key=lambda item: item[0])
    bricks: list[Brick] = []
    for y, candidate_index in zip(occupied_layers, best_path):
        bricks.extend(layer_candidates[y][candidate_index][1])
    return bricks


def bricks_to_occupancy(bricks: list[Brick], shape: tuple[int, int, int]) -> np.ndarray:
    occupancy = np.zeros(shape, dtype=bool)
    for brick in bricks:
        occupancy[
            brick.x : brick.x + brick.width,
            brick.y : brick.y + brick.height,
            brick.z : brick.z + brick.depth,
        ] = True
    return occupancy


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


def seam_overlap_ratio(bricks: list[Brick], y: int, x: int, z: int, width: int, depth: int) -> float:
    if y <= 0:
        return 0.0
    lower = [brick for brick in bricks if brick.y == y - 1]
    if not lower:
        return 0.0
    current_edges = set()
    for edge_x in (x, x + width):
        for edge_z in range(z, z + depth + 1):
            current_edges.add(("x", edge_x, edge_z))
    for edge_z in (z, z + depth):
        for edge_x in range(x, x + width + 1):
            current_edges.add(("z", edge_z, edge_x))
    lower_edges = set()
    for brick in lower:
        for edge_x in (brick.x, brick.x + brick.width):
            for edge_z in range(brick.z, brick.z + brick.depth + 1):
                lower_edges.add(("x", edge_x, edge_z))
        for edge_z in (brick.z, brick.z + brick.depth):
            for edge_x in range(brick.x, brick.x + brick.width + 1):
                lower_edges.add(("z", edge_z, edge_x))
    return len(current_edges & lower_edges) / len(current_edges) if current_edges else 0.0
