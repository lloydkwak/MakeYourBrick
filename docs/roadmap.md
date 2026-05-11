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
- Local web shell and FastAPI job flow
- Mesh inspection reports
- Mesh repair modes
- SAM adapter contract with PLY artifact classification
- Backend job runner selection for fake, command, and SAM adapter modes
- SAM 3D Objects GLB export wrapper
- Backend `sam3d` mode mask validation and config endpoint
- Studio-like sculpture options: shell mode, base thickness, layer steps, layered optimizer, and stability metrics
- LDraw center-origin placement calibration for the supported basic brick set
- Procedural mesh quality samples and comparison reports
- Auto Y-up mesh orientation for Z-up OBJ/STL sculpture assets
- Expanded Studio-style brick candidate set through 2x10 and 1x8 bricks
- Studio-like vertical ray voxelizer for open OBJ/STL sculpture assets

## Next Work

### 1. Real SAM 3D Environment Spike

Run `facebookresearch/sam-3d-objects` in a suitable GPU/Linux environment and finalize the upstream command that writes or exposes a triangle mesh.

This is the highest-risk remaining task because it requires external checkpoints, CUDA, and enough VRAM. The local wrapper already prefers `output["glb"]`, falls back to `output["mesh"][0]`, and preserves Gaussian splat PLY only as a debug artifact.

See `docs/real_sam3d_integration.md` for the detailed preparation plan.

### 1.5 Real SAM Backend Configuration

Point backend `sam3d` mode at the verified wrapper command in a real GPU/SAM environment and run one UI-to-LDraw sample.

### 2. Real Segmentation Backend

Replace placeholder mask generation with a real SAM/SAM 2 segmentation predictor so user point and box prompts produce semantic object masks.

### 3. Better Color Sampling

Current color sampling supports nearest vertex and nearest face color. Add material and UV texture sampling for GLB assets.

### 4. LDraw Visual Calibration

The writer now uses center-origin placement for the supported basic brick set. Visually verify the generated placement fixture in Stud.io or LDraw tools and add part-specific exceptions if a broader part palette introduces non-standard origins.

### 5. Structural Stability

Layered optimization now reports support, seam, connected component, and overhang-risk metrics. Further work can add:

- hard overhang limits
- global layer optimization instead of local scored placement
- stability score inspired by StableLego and related LEGO optimization work

### 6. Palette Expansion

The bundled LDraw palette is a starter subset. Replace it with a broader, validated LDraw palette before final color-sensitive output.

## Current Risk Summary

- Real SAM inference has not been run inside this repository.
- Real SAM output may need a mesh extraction path if the current upstream wrapper cannot access GLB or mesh output in the installed version.
- Watertight repair is explicit but may still approximate difficult AI-generated meshes.
- Non-watertight meshes can still produce holes unless repaired externally or approximated with `convex-hull`.
- Physical buildability is only approximate.
- Studio's internal sculpture algorithm is proprietary; MakeYourBrick approximates it from documented options and observed `.io` output.
- LDraw optimized part placement should still be visually checked in Stud.io with the generated fixture.
