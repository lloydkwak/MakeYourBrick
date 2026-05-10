# Sculpture Brickification TODO

This document tracks the Studio-like sculpture conversion improvements for MakeYourBrick.

Reference behavior from BrickLink Studio Sculpture import:

- converts OBJ/STL into a LEGO sculpture
- builds the sculpture layer by layer
- exposes base size, wall thickness, base thickness, brick selection, color mode, orientation, and layer step options
- can run connection checks after import

MakeYourBrick will keep its mesh-first pipeline and add a sculpture-oriented brickification mode around the existing voxel and LDraw stages.

## Target Flow

```text
mesh or SAM output
  -> repair
  -> voxelization
  -> sculpture occupancy post-process
       solid: keep filled occupancy
       shell: keep surface/walls and fill base layers
  -> layer-aware brickification
  -> stability report
  -> LDR with optional 0 STEP per layer
```

## Phase 1: Layer Step Output

Status: completed.

Purpose:

Make generated LDR files easier to inspect and build by inserting `0 STEP` markers whenever the vertical layer changes.

Tasks:

- [x] Add `step_by_layer` option to `write_ldr()`.
- [x] Insert `0 STEP` between different brick `y` layers.
- [x] Keep the default output unchanged unless requested.
- [x] Add tests for layer step insertion and default behavior.
- [x] Add CLI/API option `--steps-by-layer` / `steps_by_layer`.

Acceptance criteria:

- [x] LDR output can be opened as layer-by-layer instructions.
- [x] Existing LDR tests continue to pass.

## Phase 2: Sculpture Occupancy Mode

Status: completed.

Purpose:

Support Studio-like solid and shell sculpture modes.

Tasks:

- [x] Add `sculpture_mode`: `solid` or `shell`.
- [x] Add `wall_thickness` in studs.
- [x] Add `base_thickness` in layers.
- [x] In `solid` mode, keep the current filled occupancy.
- [x] In `shell` mode, keep surface voxels within `wall_thickness` of empty space or model boundary.
- [x] Always fill the bottom `base_thickness` layers inside the occupied footprint.
- [x] Preserve voxel color IDs for retained voxels.
- [x] Add tests for hollowing, wall thickness, base thickness, and color preservation.

Acceptance criteria:

- [x] Shell mode reduces occupied voxels on a solid fixture.
- [x] Base layers remain solid.
- [x] Shell mode never adds voxels outside the original occupancy.

## Phase 3: Layer-Aware Brick Optimizer

Status: completed.

Purpose:

Improve stability and build quality beyond largest-first greedy placement.

Tasks:

- [x] Keep existing `greedy_brickify()` unchanged.
- [x] Add `layered_brickify()` with scored candidate placement.
- [x] Score candidates with:
  - brick area
  - support ratio from the layer below
  - overhang penalty
  - vertical seam alignment penalty
  - color consistency
- [x] Prefer stable candidates over slightly larger unstable candidates.
- [x] Add tests for support-aware selection and seam staggering.

Acceptance criteria:

- [x] Occupancy is preserved.
- [x] Color boundaries are preserved.
- [x] Support and seam metrics are deterministic and covered by targeted tests.

## Phase 4: Stability Report

Status: completed.

Purpose:

Make sculpture output quality visible and measurable.

Tasks:

- [x] Add `build_stability_report()`.
- [x] Report unsupported brick count.
- [x] Report floating brick count.
- [x] Report average support ratio.
- [x] Report vertical seam alignment score.
- [x] Report layer count.
- [x] Include `sculpture_mode`, `wall_thickness`, and `base_thickness`.
- [x] Merge stability fields into optimizer report JSON.

Acceptance criteria:

- [x] Reports show both brick reduction and stability metrics.
- [x] Metrics are deterministic and covered by tests.

## Phase 5: CLI and Backend Options

Status: completed.

Purpose:

Expose sculpture controls through command-line and local backend flows.

Tasks:

- [x] Add CLI options:
  - `--sculpture-mode solid|shell`
  - `--wall-thickness`
  - `--base-thickness`
  - `--steps-by-layer`
  - `--optimizer greedy|layered`
- [x] Add backend `JobRequest` fields with validation.
- [x] Pass settings through `run_from_image()` and `convert_mesh_to_ldr()`.
- [x] Update usage docs and architecture docs.

Acceptance criteria:

- [x] Existing defaults match current behavior.
- [x] New options work through mesh CLI, image CLI, and backend jobs.
- [x] Full test suite passes.

## Deferred Work

- True Studio connectivity checks.
- Part-specific LDraw origin offset calibration.
- Broader brick palette and plate support.
- Cost-aware or inventory-aware brick selection.
