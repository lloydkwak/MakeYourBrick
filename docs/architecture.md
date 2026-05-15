# Architecture

MakeYourBrick has been reduced to one core Studio-like sculpture pipeline.

## Data Flow

```text
image path
  -> Sam3DRunner command
  -> raw triangle mesh
  -> convert_mesh_to_ldr()

mesh path
  -> load_mesh()
  -> orient_mesh_to_y_up()
  -> compute footprint pitch from base_size_studs, optionally auto-selected from mesh complexity
  -> scale Y by 20/24 for brick-height LDraw proportions
  -> slice mesh into filled X/Z layer footprints
  -> fall back to surface voxel fill for open or highly fragmented meshes
  -> polish closed slice voxels, or preserve open surface voxels
  -> derive a Studio-style shell target or an open-mesh detail target
  -> tile each layer with Studio brick combinations using lower/upper attachment awareness
  -> write .ldr and report.json
```

## Core Modules

- `src/makeyourbrick/pipeline.py`: orchestration for mesh and image conversion
- `src/makeyourbrick/ai/sam3d_runner.py`: external SAM command contract
- `src/makeyourbrick/mesh/solidify.py`: Trimesh loading and scene flattening
- `src/makeyourbrick/mesh/orient.py`: source up-axis handling
- `src/makeyourbrick/voxel/voxelize.py`: layer-slice voxelization
- `src/makeyourbrick/voxel/sculpture.py`: layer cleanup, shell/base helper masks
- `src/makeyourbrick/sculpture/`: target mask building and layer placement
- `src/makeyourbrick/brickify/optimizer.py`: Studio brick-combination tiler
- `src/makeyourbrick/io/ldr_writer.py`: LDraw output
- `src/makeyourbrick/server/`: local API and job runner

## Current Algorithm

1. Base size defines the maximum X/Z footprint in studs. It can be set explicitly or auto-selected from mesh proportions, face count, and fragmentation.
2. The mesh is oriented to Y-up.
3. The Y axis is scaled by the LEGO brick ratio `20/24` before slicing.
4. Each horizontal layer is filled from mesh cross-section contours.
5. If the mesh is open and the slice result is sparse, surface voxelization with fill is used as a fallback.
6. Closed slice output uses a contour-shell target: outer shell plus fully filled bottom layers.
7. Open surface fallback output uses a surface-detail target: the recovered occupancy is preserved so seats, wheels, trims, and separated OBJ components are not erased by shell extraction.
8. Wall thickness and base thickness directly control the closed sculpture target, matching Studio's sculpture import settings. For open surface-detail mode, the base mask is still reported, but the full recovered target is kept for detail.
9. Each layer is tiled exactly with the selected Studio sculpture brick set. Candidate layouts are selected with a lower/upper attachment check so a brick may be considered buildable when it connects to the layer below or to a later upper subassembly.
10. `0 STEP` is inserted between layers.

The active default is equivalent to Studio-like settings:

```text
base_size_studs: 32
wall_thickness: 2
base_thickness: 3
coloring: by layer
up_axis: auto
```

## Removed Experimental Paths

The following were intentionally removed from the active codebase:

- synthetic voxel demos
- legacy greedy optimizer
- plate-height output
- surface/ray/surface-only voxelizers
- lattice/rib infill modes
- BrickFormer reward experiments
- Studio `.io` analysis utilities
- mesh sample comparison utilities

They were useful during exploration, but they made the code harder to reason about while the actual target is a Studio-like OBJ-to-sculpture converter.
