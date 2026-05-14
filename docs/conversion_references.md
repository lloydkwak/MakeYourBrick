# Conversion Reference Review

This document records how external OBJ-to-LDraw and instruction-generation tools influence
MakeYourBrick. The implementation remains clean-room: we use public workflow concepts, not copied
source code.

## Source Review

### Brickalize

Repository: https://github.com/CreativeMindstorms/brickalize

Brickalize is a GPLv3 Python package for converting STL meshes into voxel arrays, extracting hollow
shells, placing bricks from a user-defined brick set, generating sparse support pillars, and
rendering layer-by-layer images. Its public README describes the core flow as:

```text
STL mesh -> voxel array -> shell boundary -> brick model -> support array -> layer images
```

Use in MakeYourBrick:

- Keep the conceptual split between target voxels, support voxels, and a layered brick model.
- Keep occupancy verification after placement.
- Do not copy source code or class internals because the license is GPLv3 and this project is
  Apache-2.0.

### 3DToLD

Repository: https://github.com/Nexusnui/3DToLD

3DToLD converts many 3D file formats, including OBJ, STL, 3MF, PLY, GLTF, GLB, STEP, and DAE, into
LDraw `.dat` custom part geometry. This is useful for creating custom LDraw parts, but it is not the
same as brickifying a sculpture into standard LEGO bricks.

Use in MakeYourBrick:

- Confirm that OBJ-first input is sensible.
- Keep Trimesh as the general mesh loader.
- Do not route MakeYourBrick through `.dat` custom part generation, because the goal is a buildable
  brick model made of standard parts.

### BrickFormer

Website: https://brickformer.io/
Repository: https://github.com/loryruta/brickformer

BrickFormer is a GPU/CUDA tool for converting GLB/GLTF models into LEGO constructions. Its public
guide exposes model orientation, XZ resolution, color constraints, conversion, construction slices,
and export to LXF. The source shows a slice-first converter: scale the model by X/Z resolution,
apply a brick-height Y correction, slice the mesh into 2D color maps, enumerate all possible
placements for each slice, score each placement with size/color/connectivity/support terms, choose
the best placement repeatedly, assign nearest available colors, and export a construction format.
The implementation is GPLv3 and CUDA-oriented.

Use in MakeYourBrick:

- Treat XZ resolution/base size as the primary sculpture scale control.
- Use LEGO height scaling before voxelization.
- Replace local scan-order placement with a reward-based per-slice placement solver.
- Score candidate bricks by area, same-layer neighbors, previous-layer support/connectivity, and
  color-compatible coverage.
- Preserve bottom-to-top construction slices through LDraw `0 STEP`.
- Keep CPU Python implementation small and testable; do not copy BrickFormer GPL source.

### LPub3D

Website: https://trevorsandy.github.io/lpub3d/
Repository: https://github.com/trevorsandy/lpub3d

LPub3D is a GPLv3 WYSIWYG editor for LDraw building instructions. It reads LDR/MPD models and uses
LPUB meta commands for instruction layout.

Use in MakeYourBrick:

- Emit valid LDR with `0 STEP` markers.
- Add optional LPUB meta commands later, after the brick model is stable.
- Do not integrate LPub3D source; call the external application or document manual import instead.

### LDraw Third-Party Ecosystem

Directory: https://www.ldraw.org/downloads-2/third-party-software.html

LDraw is the interchange standard. MakeYourBrick should stay conservative: standard part references,
valid transforms, `0 STEP` build sequencing, and optional future MPD/LPUB metadata.

## Architecture Decisions

- Primary SAM output format: OBJ triangle mesh.
- Supported mesh inputs: OBJ, STL, PLY mesh, GLB/GLTF, and other Trimesh-loadable triangle meshes.
- Rejected as direct conversion input: Gaussian splat PLY and point-cloud PLY.
- Main conversion target: `.ldr` model using standard LEGO/LDraw parts.
- Non-goal: converting a mesh into one custom `.dat` part.
- Instruction path: LDR `0 STEP` first; LPub3D/MPD page metadata later.

## Current Clean Pipeline

```text
image + mask
  -> SAM 3D Objects command
  -> raw_model.obj
  -> mesh inspect / repair / orientation
  -> base-size or longest-axis pitch
  -> voxel target
  -> contour shell + base + sparse support
  -> reward-based layered brick placement
  -> strict or majority color assignment
  -> output.ldr with 0 STEP markers
  -> JSON reports
```
