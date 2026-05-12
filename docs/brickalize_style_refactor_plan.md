# Brickalize-Style Sculpture Refactor Plan

This document defines the next MakeYourBrick architecture step. The goal is not to copy
`CreativeMindstorms/brickalize` source code. That project is GPLv3, while MakeYourBrick is
Apache-2.0. We will use the public workflow concepts as reference and implement our own clean
pipeline around MakeYourBrick's existing SAM, color, LDraw, and backend code.

## Why Refactor

The current pipeline has grown through incremental modes:

- `solid`
- `shell`
- `density`
- `contour-shell`
- compact and plate palettes
- several smoothing presets

This helped diagnose the queen OBJ problem, but the core model is still too implicit. Studio-like
sculpture conversion needs separate target arrays and a layered brick model:

```text
mesh or SAM mesh
  -> oriented/scaled mesh
  -> solid voxel model
  -> surface/shell target
  -> base fill target
  -> sparse support target
  -> layer brick model
  -> color assignment
  -> LDraw export
```

## Reference Concepts

Brickalize's public workflow is:

- voxelize mesh into a 3D array
- extract shell to hollow the model
- convert target voxels to a layer brick model using a brick set
- generate sparse supports for overhangs
- convert support voxels into support bricks
- verify brick model occupancy against the target array
- generate layer-by-layer views

Studio Sculpture's public workflow is:

- import OBJ/STL
- choose base size
- choose wall thickness
- choose base thickness
- choose brick set
- choose color mode
- choose orientation
- build the model layer by layer
- optionally run a connectivity check

MakeYourBrick should combine these ideas with its own mesh color sampling, LDraw palette
quantization, SAM adapter, and backend job flow.

## Target Modules

```text
src/makeyourbrick/sculpture/
  __init__.py
  model.py        # VoxelModel, SculptureSettings, LayeredBrickModel
  catalog.py      # BrickCatalog and Studio-like palettes
  builder.py      # target arrays and support generation
  placement.py    # layer-by-layer brick placement
  verify.py       # occupancy and support validation
```

## Phase A: Core Data Model

Status: complete.

Tasks:

- [x] Add `VoxelModel` with occupancy, color ids, pitch, origin, and height unit.
- [x] Add `SculptureSettings` with base size, wall thickness, base thickness, palette, color mode, and orientation.
- [x] Add `BrickCatalog` with brick and plate palettes.
- [x] Add `LayeredBrickModel` as the canonical intermediate representation before LDraw export.
- [x] Add tests for validation and conversion from existing `Brick` lists.

Acceptance criteria:

- [x] New model classes are independent from current pipeline behavior.
- [x] Existing targeted tests still pass.

## Phase B: Shell and Base Target Builder

Status: complete.

Tasks:

- [x] Wrap contour shell extraction in `sculpture.builder`.
- [x] Produce named target arrays: `solid`, `shell`, `base`, `support`.
- [x] Preserve color ids for retained voxels.
- [x] Add fixture tests for hollow shell, base fill, and layer boundary behavior.

Acceptance criteria:

- [x] Surface-only target does not fill the entire interior.
- [x] Base thickness fully fills requested bottom layers.
- [x] Output target remains within original solid occupancy.

## Phase C: Sparse Support Planner

Status: complete.

Tasks:

- [x] Replace current eager support column fill with a support planner.
- [x] For each unsupported voxel region, choose sparse columns with minimum added voxels.
- [x] Stop columns at base, existing shell, or existing support.
- [x] Mark support cells separately from shell cells.

Acceptance criteria:

- [x] Support count is lower than full vertical fill when spacing is increased.
- [x] Unsupported/floating metrics can be measured separately from shell output.

## Phase D: Layered Brick Placement

Status: complete.

Tasks:

- [x] Place bricks layer by layer from a `BrickCatalog`.
- [x] Prefer compact exterior bricks through the compact catalog and existing boundary score.
- [x] Use larger bricks on stable base/interior/support regions through the layered score.
- [x] Preserve occupancy verification after placement.

Acceptance criteria:

- [x] Occupancy from placed bricks matches shell + support target.
- [x] Long rods can be excluded by selecting the compact catalog.

## Phase E: Color Assignment

Status: pending.

Tasks:

- [ ] Add per-brick color assignment by majority voxel color.
- [ ] Add optional average RGB then LDraw quantization.
- [ ] Keep support bricks optionally neutral or inherited.

Acceptance criteria:

- [ ] Colored mesh voxels produce colored bricks.
- [ ] Color boundaries remain deterministic.

## Phase F: Pipeline Integration

Status: pending.

Tasks:

- [ ] Add `--sculpture-engine legacy|layered`.
- [ ] Keep legacy output available for comparison.
- [ ] Route `layered` through the new builder.
- [ ] Add queen comparison fixtures and reports.

Acceptance criteria:

- [ ] Existing CLI/API calls keep working.
- [ ] New engine generates LDR and report artifacts.

## Current Recommended Visual Command

For the current legacy path, the best visual candidate to inspect is:

```bash
python scripts/mesh_to_ldr.py \
  --mesh queen.obj \
  --target-studs 60 \
  --target-width-studs 38 \
  --target-depth-studs 37 \
  --up-axis auto \
  --voxelizer slice \
  --optimize \
  --optimizer layered \
  --brick-palette compact \
  --sculpture-mode contour-shell \
  --wall-thickness 2 \
  --base-thickness 2 \
  --voxel-smoothing polished \
  --steps-by-layer \
  --output outputs/ldr/queen_slice_contour_shell_sparse_compact_60.ldr
```
