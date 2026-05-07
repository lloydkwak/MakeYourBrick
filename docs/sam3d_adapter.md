# SAM 3D Adapter

The SAM 3D adapter is the boundary between an external `facebookresearch/sam-3d-objects` checkout and the MakeYourBrick mesh pipeline.

It does not assume a stable upstream Python API. Instead, it accepts either:

- an upstream command template that produces a mesh-like artifact
- or an existing candidate artifact from a SAM experiment

The adapter classifies and inspects the candidate, verifies that it is a voxelization-ready triangle mesh, and exports a normalized mesh file for MakeYourBrick.

SAM 3D Objects official quickstart exports a Gaussian splat PLY through `output["gs"].save_ply("splat.ply")`. The upstream pipeline also exposes mesh/GLB post-processing paths. MakeYourBrick should prefer direct GLB or triangle mesh export and preserve Gaussian splat PLY only for debugging and visualization.

## Artifact Policy

```text
raw_splat.ply       Optional preserved SAM Gaussian splat output
raw_model.glb       Required triangle mesh input for MakeYourBrick
mesh_inspect.json   Geometry compatibility report
repair_report.json  Mesh repair report
output.ldr          Final LDraw model
```

PLY files are classified before conversion:

- `mesh_ply`: has face elements and can be adapted to GLB
- `gaussian_splat_ply`: has Gaussian properties such as opacity, scale, rotation, or feature fields; mesh extraction is required
- `point_cloud_ply`: has vertices without faces or Gaussian properties; mesh reconstruction is required

Preferred real SAM export order:

1. `output["glb"].export(raw_model.glb)`
2. convert `output["mesh"][0]` to GLB through Trimesh
3. save `output["gs"]` as an optional debug PLY
4. fail before voxelization if no mesh output is available

## Command Contract

```bash
python scripts/adapters/sam3d_to_mesh.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --output outputs/meshes/raw_model.glb \
  --sam-command "<upstream command that writes {output} or {work_dir}>"
```

Supported command placeholders:

- `{repo}`
- `{image}`
- `{output}`
- `{output_dir}`
- `{work_dir}`

## Existing Candidate Mode

Use this mode after running SAM manually and locating an output artifact:

```bash
python scripts/adapters/sam3d_to_mesh.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --candidate path/to/sam/output.glb \
  --output outputs/meshes/raw_model.glb \
  --report outputs/reports/sam3d_adapter.json
```

## Report

The adapter report includes:

- repository path
- input image path
- selected candidate path
- output path
- source mesh inspection
- output mesh inspection
- final status

If the candidate is a point cloud, Gaussian splat, empty scene, or unsupported asset type, the adapter fails clearly instead of passing a bad artifact into voxelization. The failure report records the detected artifact type and the required next action.

## Image Pipeline Usage

Once a real upstream command is known, use it through the existing image pipeline:

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "python scripts/adapters/sam3d_to_mesh.py --repo {repo} --image {image} --output {output} --sam-command '<upstream command>'" \
  --target-studs 48 \
  --sample-colors \
  --optimize \
  --repair-report outputs/reports/repair_report.json \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

The nested command above is intentionally explicit. For real use, prefer storing the upstream command in a script or shell wrapper to avoid quoting issues.

## Current Limitation

This adapter prepares the contract but does not yet encode a verified SAM 3D Objects inference command. That command must be finalized after running the upstream repository in a suitable GPU/Linux environment and documenting the actual produced artifacts.
