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
- Local web shell and FastAPI job stub
- Mesh inspection reports
- Mesh repair modes
- SAM adapter contract with PLY artifact classification

## Next Work

### 1. Real SAM 3D Environment Spike

Run `facebookresearch/sam-3d-objects` in a suitable GPU/Linux environment and finalize the upstream command that writes or exposes a triangle mesh.

This is the highest-risk remaining task because official quickstart examples export Gaussian splat PLY files. These are preserved as raw artifacts, while the MakeYourBrick pipeline requires a triangle mesh.

See `docs/phase6_todo.md` for the detailed preparation plan.

### 1.5 Backend Real Runner Mode

Replace the hardcoded fake runner in backend jobs with a runner factory that can choose `fake`, `command`, or `sam3d` mode through configuration.

### 2. Real Segmentation Backend

Replace placeholder mask generation with a real SAM/SAM 2 segmentation predictor so user point and box prompts produce semantic object masks.

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
- Real SAM output may need a mesh extraction path if only Gaussian splats are available.
- Watertight repair is explicit but may still approximate difficult AI-generated meshes.
- Physical buildability is only approximate.
- LDraw optimized part placement should be visually checked in Stud.io.
