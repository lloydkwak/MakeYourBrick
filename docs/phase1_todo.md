# Phase 1 TODO: Synthetic Voxel to 1x1 LDraw

This temporary working document tracks Phase 1 until it is fully implemented and verified.

## Goal

Build a deterministic, testable path from an in-memory voxel matrix to a valid LDraw `.ldr` file using only `3005.dat` 1x1 bricks.

## Reference Ideas

- Brickalize: use the same validation mindset of converting voxel-like data into bricks and checking that the brick representation reconstructs the original occupancy.
- LDraw file format: use line type 1 part references with a 3x3 transform matrix.
- StableLego / Brick Optimization Builder: keep brick data structured as part id, color, grid position, and rotation so later stability and packing stages can reuse it.

## Algorithm

1. Generate or receive `occupancy: bool[nx, ny, nz]`.
2. Generate or receive `color_ids: int[nx, ny, nz]`.
3. Visit voxels deterministically, bottom layer first.
4. For each occupied voxel, emit one `Brick(part_id="3005.dat")`.
5. Convert voxel coordinates into LDraw coordinates:
   - `x_ldu = x * 20`
   - `y_ldu = -y * 24`
   - `z_ldu = z * 20`
6. Write LDraw line type 1 with an identity transform.

## Completion Checklist

- [ ] Add synthetic voxel generators.
- [ ] Make 1x1 brickification deterministic and validate input shapes.
- [ ] Add brick-to-occupancy round-trip helper for tests.
- [ ] Harden LDraw writer output and coordinate tests.
- [ ] Add a synthetic LDR CLI.
- [ ] Add pytest coverage for synthetic voxels, brickification, round-trip, and LDR writer.
- [ ] Run verification commands.
- [ ] Commit and push each completed feature checkpoint.

## Verification Commands

```bash
python -m compileall src scripts
python -m pytest
python scripts/make_synthetic_ldr.py --shape box --size 4 3 2 --color 16 --output outputs/ldr/synthetic_box.ldr
```

## Phase 1 Done Definition

- All tests pass.
- A synthetic `.ldr` can be generated from the CLI.
- Occupied voxel count equals emitted brick count.
- Round-trip reconstruction matches the original occupancy.
- Coordinate conversion is tested against LDraw unit expectations.

