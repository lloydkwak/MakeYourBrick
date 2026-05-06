# Phase 4 TODO: Greedy Brick Optimization

This temporary working document tracks Phase 4 until it is fully implemented and verified.

## Goal

Reduce brick count by merging occupied 1x1 voxels into larger LEGO bricks while preserving occupancy and color.

Phase 4 keeps the geometry and color contracts from previous phases:

```text
occupancy + color_ids -> optimized bricks -> .ldr
```

## Brick Candidates

The first optimizer uses a deterministic top-down greedy search:

| Priority | Part | Size |
| --- | --- | --- |
| 1 | `3001.dat` | 2 x 4 brick |
| 2 | `3010.dat` | 1 x 4 brick |
| 3 | `3003.dat` | 2 x 2 brick |
| 4 | `3004.dat` | 1 x 2 brick |
| 5 | `3005.dat` | 1 x 1 brick |

All bricks are one brick high in Phase 4.

## Algorithm

1. Validate `occupancy` and `color_ids` shapes.
2. Keep a `used` matrix with the same shape as `occupancy`.
3. Iterate voxels deterministically, bottom layer first.
4. Skip empty or already used voxels.
5. Read the voxel color.
6. Try each candidate brick from largest to smallest.
7. If rotations are enabled, try `(width, depth)` and `(depth, width)`.
8. A placement is valid only if:
   - the candidate footprint is inside matrix bounds
   - all cells in the candidate volume are occupied
   - no cells in the candidate volume are already used
   - all occupied cells in the candidate volume have the same color
9. Mark the candidate volume as used and append a `Brick`.
10. Fall back to `3005.dat` if no larger candidate fits.

## Known Limitations

- No physical stability scoring yet.
- No brick staggering preference yet.
- No support for plates or slopes.
- Part origins are still approximate; Phase 4 only adds basic rotation matrix support for `.ldr` output.

## Completion Checklist

- [x] Add Phase 4 TODO document.
- [ ] Implement candidate placement validation.
- [ ] Implement greedy brick optimizer.
- [ ] Add round-trip and brick count reduction tests.
- [ ] Add rotation-aware LDraw writer support.
- [ ] Add optimizer mode to `mesh_to_ldr.py`.
- [ ] Add end-to-end CLI test proving optimized output uses fewer bricks.
- [ ] Run verification commands.
- [ ] Commit and push each completed feature checkpoint.

## Verification Commands

```bash
python -m compileall src scripts
python -m pytest
python scripts/make_synthetic_ldr.py --shape box --size 4 1 2 --color 16 --output outputs/ldr/optimized_box.ldr --optimize
```

## Phase 4 Done Definition

- All tests pass.
- Greedy optimization preserves original occupancy via round-trip reconstruction.
- Uniform 4x1x2 boxes compress from 8 one-by-one bricks to 1 or 2 larger bricks depending on orientation.
- Mixed-color regions are not merged across color boundaries.
- Existing 1x1-only behavior remains available.
