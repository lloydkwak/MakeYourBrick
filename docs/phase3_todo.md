# Phase 3 TODO: Color Quantization

This temporary working document tracks Phase 3 until it is fully implemented and verified.

## Goal

Add a deterministic color path so voxel RGB values are mapped to valid LDraw color IDs.

Phase 3 keeps geometry unchanged from Phase 2:

```text
mesh file -> cleaned mesh -> filled voxel matrix -> voxel RGB/color IDs -> 1x1 bricks -> .ldr
```

The first implementation focuses on reliable RGB-to-LDraw quantization. Full texture sampling from arbitrary GLB materials can come later once the color contract is stable.

## Inputs and Outputs

Inputs:

- `rgb: uint8[nx, ny, nz, 3]`
- `occupancy: bool[nx, ny, nz]`
- `data/ldraw/ldraw_colors.json`

Outputs:

- `color_ids: int32[nx, ny, nz]`
- `.npz` artifacts containing both `rgb` and quantized `color_ids`
- `.ldr` files whose part color IDs come from quantized voxel colors

## Reference Ideas

- LDraw color table: use integer color IDs and RGB values.
- CIELAB distance: compare perceptual color distances instead of raw RGB distances.
- SciPy `cdist`: vectorized nearest-neighbor palette lookup.
- Phase 1/2: reuse existing brickification and LDraw writer without changing their contracts.

## Algorithm

1. Load LDraw palette JSON.
2. Validate each palette entry:
   - integer `id`
   - non-empty `name`
   - RGB triplet in `[0, 255]`
3. Convert input RGB values to CIELAB.
4. Convert palette RGB values to CIELAB.
5. Compute pairwise distances with `scipy.spatial.distance.cdist`.
6. Assign the nearest LDraw color ID to each voxel.
7. Preserve default color behavior when no RGB sampling is requested.
8. Store both original RGB and quantized color IDs in voxel `.npz`.

## Completion Checklist

- [x] Add Phase 3 TODO document.
- [x] Harden LDraw palette loading and validation.
- [x] Add CIELAB quantization tests.
- [x] Add voxel RGB-to-LDraw color ID helper.
- [x] Add color-aware voxel artifact test coverage.
- [ ] Add CLI options for constant RGB color and palette path.
- [ ] Add end-to-end CLI test proving `.ldr` color IDs are quantized.
- [ ] Run verification commands.
- [ ] Commit and push each completed feature checkpoint.

## Verification Commands

```bash
python -m compileall src scripts
python -m pytest
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 24 --rgb 242 205 55 --output outputs/ldr/yellow_mesh_output.ldr
```

## Phase 3 Done Definition

- All tests pass.
- Palette loading rejects invalid color rows.
- Known RGB values map to expected nearest LDraw IDs.
- `mesh_to_ldr.py --rgb R G B` produces an `.ldr` using the quantized LDraw color ID.
- Existing Phase 1 and Phase 2 behavior remains intact when no RGB override is supplied.
