# Phase 6 TODO: Real SAM Adapter Preparation and Mesh Robustness

Phase 6 is the bridge between the tested MakeYourBrick pipeline and a real SAM 3D Objects deployment.

Real SAM 3D inference is intentionally deferred until a suitable GPU/Linux environment is available. This phase prepares the project so that when SAM 3D is installed, its outputs can be inspected, adapted, repaired, and converted with minimal guesswork.

## Phase 6 Goal

Make the project ready for real image-to-LDraw execution by adding the missing tooling around SAM output validation and AI-generated mesh robustness.

Target flow:

```text
input image
  -> segmentation target selection
  -> real SAM 3D adapter
  -> raw SAM output
  -> mesh inspection
  -> mesh conversion/repair if needed
  -> voxelization
  -> color sampling / quantization
  -> brick optimization
  -> LDraw + reports
```

## Current Baseline

Already implemented:

- image pipeline orchestration through `Sam3DRunner`
- command-template based SAM runner contract
- fake SAM command tests
- mesh-to-LDraw pipeline
- sampled vertex/face colors
- greedy optimizer
- optimizer reports
- mesh inspection reports
- explicit mesh repair modes
- SAM adapter contract and PLY artifact classification

Not yet implemented:

- verified real SAM 3D inference command
- point cloud / Gaussian splat to triangle mesh conversion
- real image manual verification
- real SAM runner mode in the backend

## Phase 6.1: Real SAM Environment Spike

### Purpose

Confirm the real SAM 3D Objects environment and determine what artifacts the upstream model actually emits for a single image.

### Steps

1. Prepare a GPU/Linux environment.
   - Prefer a Linux workstation, cloud GPU VM, or Colab-like environment.
   - Record OS, GPU model, CUDA version, Python version, PyTorch version, and VRAM.
2. Clone SAM 3D Objects.
   ```bash
   git clone https://github.com/facebookresearch/sam-3d-objects third_party/sam-3d-objects
   ```
3. Follow upstream setup.
   - Use `doc/setup.md` in the external repository.
   - Authenticate Hugging Face if checkpoint access is required.
4. Run the upstream demo/notebook on one image.
5. Record generated files.
   - file names
   - file extensions
   - whether each file is a triangle mesh, point cloud, Gaussian splat, or metadata
6. Try loading outputs with Trimesh.
   ```bash
   python -c "import trimesh; print(trimesh.load('path/to/output'))"
   ```

### Done Criteria

- Real SAM 3D can run on one image.
- The output artifact types are documented.
- The next adapter approach is clear: direct mesh export or conversion required.

## Phase 6.2: Mesh Output Inspector

### Purpose

Create a tool that answers: "Can this output be consumed by MakeYourBrick?"

Status: implemented for triangle mesh compatibility reporting. Memory-cost estimation and dry-run voxelization remain future hardening tasks.

### New Files

```text
src/makeyourbrick/mesh/inspect.py
scripts/inspect_mesh.py
tests/test_mesh_inspect.py
```

### Inspection Fields

- path
- exists
- load status
- asset type: mesh, scene, point cloud, unknown
- vertex count
- face count
- geometry count for scenes
- bounds
- extents
- watertight
- volume estimate if available
- vertex color availability
- face color availability
- material/texture hint if available
- warnings
- fatal errors

### CLI

```bash
python scripts/inspect_mesh.py \
  --mesh outputs/meshes/raw_model.glb \
  --report outputs/reports/mesh_inspect.json
```

### Done Criteria

- Valid triangle meshes produce a pass report.
- Point-cloud-like outputs produce a clear warning or failure.
- JSON report can be used before running voxelization.

## Phase 6.3: SAM 3D Adapter Command

### Purpose

Implement the concrete command that `scripts/image_to_ldr.py --sam-command` will call.

Status: contract adapter implemented with PLY classification. The final upstream SAM command still needs to be filled in after a real SAM 3D environment spike.

### New Files

```text
scripts/adapters/sam3d_to_mesh.py
docs/sam3d_adapter.md
tests/test_sam3d_adapter_contract.py
```

### Contract

```bash
python scripts/adapters/sam3d_to_mesh.py \
  --repo third_party/sam-3d-objects \
  --image data/input_images/sample.png \
  --output outputs/meshes/raw_model.glb
```

### Responsibilities

1. Validate `--repo`.
2. Validate `--image`.
3. Run the upstream SAM 3D inference entry point.
4. Locate the produced artifact.
5. If the output is a triangle mesh, copy/export it to `--output`.
6. If the output is not a triangle mesh, fail with a clear conversion-needed error.
7. Emit concise logs with the detected output type.

### Done Criteria

- Adapter command creates the requested `{output}` file for a known SAM output.
- `scripts/image_to_ldr.py` can call the adapter without code changes.
- Failure modes are explicit and actionable.

Additional policy:

- Preserve Gaussian splat PLY as a raw artifact only.
- Use GLB or another triangle mesh format as the pipeline input.
- Reject Gaussian splat PLY and point cloud PLY before voxelization unless a mesh extraction fallback is explicitly enabled later.

## Phase 6.4: Mesh Conversion Fallback

### Purpose

Handle cases where SAM output is not directly a triangle mesh.

### Candidate Strategies

- If output is a point cloud:
  - Poisson reconstruction
  - alpha shape
  - marching cubes from occupancy approximation
- If output is Gaussian splat:
  - find upstream mesh extraction if available
  - render depth maps and fuse
  - convert through a dedicated splat-to-mesh tool if available

### Done Criteria

- The project either converts the SAM output into a mesh or clearly documents why the current output type is unsupported.
- The adapter never silently passes a non-mesh artifact into voxelization.

## Phase 6.5: Mesh Repair Upgrade

### Purpose

Improve success rate for AI-generated meshes that are open, noisy, self-intersecting, or non-manifold.

Status: implemented for explicit repair modes and repair reports. Further hardening can add deeper non-manifold diagnostics and model-size limits.

### New Files

```text
src/makeyourbrick/mesh/repair.py
tests/test_mesh_repair.py
```

### Repair Modes

- `none`: load and export only
- `basic`: Trimesh cleanup, normals, hole filling where possible
- `manifold`: use `manifold3d` if available
- `convex-hull`: fallback for severe failures

### CLI Option

```bash
python scripts/mesh_to_ldr.py --mesh raw.glb --repair-mode basic
```

### Done Criteria

- Repair report records mode, watertight status, face count changes, and warnings.
- Tests cover at least one intentionally open mesh.

## Phase 6.6: Real Image End-to-End Verification

### Purpose

Run a real user image through the full system.

### Command Shape

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "python scripts/adapters/sam3d_to_mesh.py --repo {repo} --image {image} --output {output}" \
  --target-studs 48 \
  --sample-colors \
  --optimize \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

### Manual Checks

- `raw_model` opens in a mesh viewer.
- voxel artifact is non-empty.
- `.ldr` opens in Stud.io or an LDraw-compatible viewer.
- optimizer report contains reasonable brick counts.
- color distribution is plausible.

### Done Criteria

- One real image produces a valid `.ldr`.
- The run is documented with command, hardware, output counts, and known issues.

## Phase 6.7: Documentation and Cleanup

### Purpose

Make the real SAM path reproducible.

### Documentation Updates

- `docs/sam3d_manual_setup.md`
- `docs/usage.md`
- `docs/testing.md`
- `docs/roadmap.md`

### Done Criteria

- Real SAM setup instructions are accurate.
- The adapter command is documented.
- Known limitations are explicit.

## Phase 6 Commit Plan

Recommended commits:

1. `Add mesh inspection report`
2. `Add SAM 3D adapter command`
3. `Add mesh conversion fallback notes`
4. `Add configurable mesh repair modes`
5. `Document real image verification`

## Phase 6 Risks

- SAM output may not be a triangle mesh.
- Upstream SAM APIs may change.
- GPU environment may differ from local test environment.
- Mesh repair may alter shape too aggressively.
- Large voxel grids may generate too many bricks.
