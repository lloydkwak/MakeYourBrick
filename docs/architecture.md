# Architecture

MakeYourBrick has one production path: select an object in an image, reconstruct
it with SAM 3D Objects, preview the raw mesh, and convert it into a Studio-like
LDraw sculpture.

## Data Flow

```text
web image upload
  -> FastAPI session storage
  -> SAM2 prompt segmentation
  -> mask PNG
  -> SAM 3D Objects export script
  -> raw_model.glb
  -> browser GLB preview
  -> convert_mesh_to_ldr()
  -> output.ldr + report.json + model_voxels.npz
```

Mesh-only conversion enters at `convert_mesh_to_ldr()` with an OBJ/GLB/STL or
any Trimesh-loadable triangle mesh.

## Core Modules

- `apps/web/`: browser UI, SAM mask overlay, GLB preview, artifact links
- `apps/web/glb-viewer.js`: dependency-free GLB previewer with WebGL and 2D canvas fallback
- `src/makeyourbrick/server/`: FastAPI app, storage, job registry, SAM2 mask creation
- `scripts/sam2_segment.py`: SAM2 prompt-to-mask helper
- `scripts/sam3d_export.py`: SAM 3D Objects GLB export helper with checkpoint auto-resolution and low-VRAM modes
- `src/makeyourbrick/pipeline.py`: conversion orchestration
- `src/makeyourbrick/mesh/`: mesh loading, inspection, orientation
- `src/makeyourbrick/voxel/`: base-size selection, layer slicing, surface fallback, cleanup
- `src/makeyourbrick/brickify/`: LDraw color matching, shadow softening, Studio-like placement reports
- `src/makeyourbrick/sculpture/`: target masks and brick placement
- `src/makeyourbrick/io/ldr_writer.py`: LDraw writer

## Reconstruction

The Docker runtime clones SAM2 and SAM 3D Objects during build. At runtime:

- SAM2 (`facebook/sam2.1-hiera-large` by default) creates prompt masks.
- SAM 3D Objects (`facebook/sam-3d-objects`) creates the raw GLB mesh.
- Checkpoints are loaded from the mounted Hugging Face cache.
- `--depth-device staged-cuda` is recommended for RTX 3080-class 10 GB GPUs.

The GLB is kept as a first-class artifact. The UI previews it directly, while
the LDR remains a download artifact for Studio/LDraw inspection.

## Conversion Algorithm

1. Load and flatten OBJ/GLB/STL scenes through Trimesh.
2. Orient the mesh to Y-up.
3. Select base size explicitly or with `auto`.
4. Compute pitch from the selected X/Z footprint size.
5. Scale Y by `20/24` so voxel layers match LEGO brick height proportions.
6. Slice closed meshes into filled X/Z layer footprints.
7. Fall back to surface voxel fill for open or fragmented meshes.
8. Sample mesh colors from vertex colors, face colors, UV textures, or material diffuse color.
9. Soften baked photo shadows before CIELAB LDraw color quantization.
10. Build a contour-shell target for closed slice output, or preserve surface-detail output for fragmented/open meshes.
11. Tile each layer with the Studio sculpture brick set, respecting color boundaries in mesh-color mode.
12. Add attachment-only plates for bricks that are otherwise unattached from both below and above.
13. Write `.ldr` with `0 STEP` between layers and a JSON report.

## Auto Base Size

`auto` chooses from `16/24/32/48` studs. It uses footprint-to-height ratio,
mesh density, and fragmentation:

- simple compact objects can stay at `16` or `24`
- dense tall objects such as the queen demo resolve to `32`
- wide or highly fragmented objects can rise to `32` or `48`

This avoids the earlier behavior where high SAM mesh face counts alone pushed
small objects to oversized `48`-stud outputs.

## Color Handling

Mesh color mode is the default for image/SAM output. The converter samples
available mesh color data and quantizes to the solid LDraw palette in CIELAB
space. Before quantization, dark photo shadows are lifted toward the object's
mid-tone so background lighting does not become black or very dark brown LEGO
bricks.

## Defaults

```text
base_size_studs: auto
wall_thickness: 2
base_thickness: 3
color_strategy: mesh
up_axis: auto
raw_mesh_suffix: .glb
```
