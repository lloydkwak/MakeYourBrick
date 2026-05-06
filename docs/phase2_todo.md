# Phase 2 TODO: Mesh to Voxel to 1x1 LDraw

This temporary working document tracks Phase 2 until it is fully implemented and verified.

## Goal

Build a deterministic, testable non-AI path from an existing mesh file (`.glb`, `.obj`, `.stl`) to a 1x1-brick LDraw `.ldr` file.

Phase 2 intentionally skips SAM 3D generation. It proves that user-provided or previously generated mesh artifacts can flow through:

```text
mesh file -> cleaned mesh -> filled voxel matrix -> 1x1 bricks -> .ldr
```

## Inputs and Outputs

Input:

- `data/examples/*.glb`
- `data/examples/*.obj`
- `data/examples/*.stl`
- or any mesh path provided via CLI

Outputs:

- `outputs/meshes/watertight_model.glb`
- `outputs/voxels/model_voxels.npz`
- `outputs/ldr/mesh_output.ldr`

## Reference Ideas

- Trimesh: mesh loading, scene handling, geometry cleanup, export, voxelization.
- Manifold3D: reserved for stronger watertight repair, but Phase 2 can start with Trimesh cleanup and clear reporting.
- Phase 1 code: reuse 1x1 brickification and LDraw writer exactly as the final output path.

## Algorithm

1. Load a mesh file with `trimesh.load`.
2. If the file is a `Scene`, merge geometries into one `Trimesh`.
3. Clean the mesh:
   - remove unreferenced vertices
   - remove duplicate faces
   - remove degenerate faces where available
   - export the cleaned artifact
4. Compute voxel pitch:
   - `pitch = max(mesh.extents.max() / target_longest_studs, min_pitch)`
5. Voxelize:
   - `grid = mesh.voxelized(pitch)`
   - if enabled, `grid = grid.fill()`
6. Save `.npz`:
   - `occupancy`
   - default `color_ids`
   - placeholder `rgb`
   - `origin`
   - `pitch`
7. Convert occupied voxels to `3005.dat` bricks.
8. Write `.ldr`.

## Completion Checklist

- [x] Add Phase 2 TODO document.
- [ ] Improve mesh loading and scene-to-mesh handling.
- [ ] Add mesh cleanup/solidification tests.
- [ ] Add voxel artifact helpers for saving/loading occupancy and colors.
- [ ] Add voxelization tests with a synthetic Trimesh mesh.
- [ ] Add `mesh_to_ldr` CLI.
- [ ] Add end-to-end CLI test from generated STL to LDR.
- [ ] Run verification commands.
- [ ] Commit and push each completed feature checkpoint.

## Verification Commands

```bash
python -m compileall src scripts
python -m pytest
python scripts/mesh_to_ldr.py --mesh data/examples/sample.stl --target-studs 24 --output outputs/ldr/mesh_output.ldr
```

## Phase 2 Done Definition

- All non-skipped tests pass.
- Mesh loading handles both `Trimesh` and `Scene` inputs.
- Voxel `.npz` artifacts can be loaded back into memory.
- Existing mesh input can generate a valid 1x1-brick `.ldr`.
- Phase 1 LDraw writer and brickification remain unchanged in behavior.
