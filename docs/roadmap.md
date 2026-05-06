# Roadmap and Known Limitations

## Completed

- Synthetic voxel to LDraw
- Mesh to voxel artifact
- Mesh to LDraw
- RGB to LDraw color quantization
- Mesh vertex/face color sampling
- Greedy brick optimization
- LDraw rotation output
- Optimizer report JSON
- Image pipeline orchestration through a SAM command contract

## Next Work

### 1. Real SAM 3D Adapter

Write a concrete adapter command for `facebookresearch/sam-3d-objects` that accepts `{image}` and writes a Trimesh-loadable triangle mesh to `{output}`.

This is the highest-risk remaining task because upstream SAM examples may produce Gaussian splats or point-cloud-like PLY files rather than triangle meshes.

See `docs/phase6_todo.md` for the detailed preparation plan.

### 1.5 User Interface

Build a tool UI where users can upload an image, select the target object with point or box prompts, preview the mask, configure LEGO output options, and run the conversion job.

See `docs/ui_integration_plan.md` for the proposed UX, API, repository structure, and milestones.

### 2. Stronger Mesh Repair

The current mesh cleanup path does not guarantee watertight manifold output. Add `manifold3d` repair or a documented fallback strategy for open/noisy AI-generated meshes.

### 3. Better Color Sampling

Current color sampling supports nearest vertex and nearest face color. Add material and UV texture sampling for GLB assets.

### 4. LDraw Part Origin Calibration

The current LDraw writer uses a simple grid-to-LDU mapping. Visually verify optimized bricks in Stud.io or LDraw tools and add part-specific origin offsets if needed.

### 5. Structural Stability

Greedy optimization reduces brick count but does not guarantee physical stability. Add:

- support ratio checks
- floating brick detection
- overhang limits
- staggered placement preference
- stability score inspired by StableLego and related LEGO optimization work

### 6. Palette Expansion

The bundled LDraw palette is a starter subset. Replace it with a broader, validated LDraw palette before final color-sensitive output.

## Current Risk Summary

- Real SAM inference has not been run inside this repository.
- Real SAM output may need a mesh conversion adapter.
- Watertight repair is not yet robust enough for all generated meshes.
- Physical buildability is only approximate.
- LDraw optimized part placement should be visually checked in Stud.io.
