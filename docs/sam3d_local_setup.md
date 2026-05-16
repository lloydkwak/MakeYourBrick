# Local SAM 3D Objects Setup

MakeYourBrick is designed to run without vendoring Meta's SAM 3D Objects
repository or model checkpoints. The recommended integration is a local external
checkout plus a command template that writes a textured triangle mesh to
MakeYourBrick's `{output}` path.

## Recommended Integration

Use this layout:

```text
MakeYourBrick/
  scripts/
  src/
  third_party/
    sam-3d-objects/        # local checkout, ignored by git
      checkpoints/         # local checkpoint cache, ignored by git
```

Do not use a git submodule for the first integration. SAM 3D Objects has a large
and fast-moving dependency stack, and its checkpoints require gated Hugging Face
access. Keeping it as an external checkout makes MakeYourBrick easier to clone,
test, and share.

## Requirements

SAM 3D Objects is the heavy part of the pipeline. Plan for:

- Linux or WSL2/Linux for the SAM environment
- NVIDIA GPU
- CUDA-compatible PyTorch
- large VRAM budget; the official setup recommends a high-memory GPU
- Hugging Face account with access to `facebook/sam-3d-objects`

MakeYourBrick itself can run on normal Python, but the real SAM runner should be
started from the same environment where SAM 3D Objects and its checkpoints are
available.

## Install Flow

1. Clone MakeYourBrick.

2. Clone SAM 3D Objects under `third_party/`.

   ```bash
   git clone https://github.com/facebookresearch/sam-3d-objects.git third_party/sam-3d-objects
   ```

3. Follow the official SAM 3D Objects setup instructions in that checkout.

4. Request access to the Hugging Face model and authenticate locally.

   ```bash
   huggingface-cli login
   ```

5. Download or cache checkpoints according to the official SAM 3D Objects
   documentation. Keep them under `third_party/sam-3d-objects/` or another local
   cache path. Do not commit checkpoints.

## Export Contract

MakeYourBrick only needs one artifact from SAM:

```text
input image + mask -> textured triangle mesh at {output}
```

Preferred output:

```text
raw_model.glb
```

Textured GLB is preferred over OBJ because it keeps geometry, transforms, UVs,
materials, and texture images in one file. MakeYourBrick can load OBJ too, but
OBJ texture handoff depends on sidecar `.mtl` and image files staying together.

The SAM export command should:

- accept `--image`
- accept `--mask`
- accept `--output`
- write a Trimesh-loadable `.glb`
- preserve texture or vertex/face colour when available

## MakeYourBrick CLI

Once a SAM export command exists, call it through `image_to_ldr.py`:

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --mask data/masks/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "python path/to/sam3d_export.py --image {image} --mask {mask} --output {output}" \
  --raw-mesh outputs/meshes/raw_model.glb \
  --base-size-studs 32 \
  --wall-thickness 2 \
  --base-thickness 3 \
  --color-strategy mesh \
  --report outputs/reports/image_report.json \
  --output outputs/ldr/image_output.ldr
```

Use `--color-strategy mesh` for real SAM output so voxel colours are sampled from
the generated textured mesh.

## Local Web API

For the local web shell, configure the backend with environment variables:

```bash
export MAKEYOURBRICK_RUNNER_MODE=sam3d
export MAKEYOURBRICK_SAM_REPO=third_party/sam-3d-objects
export MAKEYOURBRICK_SAM_COMMAND="python path/to/sam3d_export.py --image {image} --mask {mask} --output {output}"
python -m uvicorn makeyourbrick.server.main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

On Windows PowerShell:

```powershell
$env:MAKEYOURBRICK_RUNNER_MODE = "sam3d"
$env:MAKEYOURBRICK_SAM_REPO = "third_party/sam-3d-objects"
$env:MAKEYOURBRICK_SAM_COMMAND = "python path/to/sam3d_export.py --image {image} --mask {mask} --output {output}"
python -m uvicorn makeyourbrick.server.main:app --app-dir src --host 127.0.0.1 --port 8000 --reload
```

Then open `apps/web/index.html`, upload an image, select an object, and run the
conversion job.

## Verification

Before running the full LEGO pipeline, verify the raw mesh:

```bash
python scripts/image_to_ldr.py \
  --image data/input_images/sample.png \
  --mask data/masks/sample.png \
  --sam-repo third_party/sam-3d-objects \
  --sam-command "python path/to/sam3d_export.py --image {image} --mask {mask} --output {output}" \
  --raw-mesh outputs/meshes/raw_model.glb \
  --raw-mesh-report outputs/reports/raw_mesh_inspect.json \
  --color-strategy mesh \
  --output outputs/ldr/image_output.ldr
```

Check `outputs/reports/raw_mesh_inspect.json`:

- `voxelization_ready` should be `true`
- `face_count` should be greater than zero
- `color_source` should ideally be `texture`, `vertex`, `face`, or `material`
- `asset_type` may be `scene` for GLB and that is fine

## Why Not Commit SAM or Checkpoints?

- SAM 3D Objects is an external research dependency with its own setup.
- The checkpoint is gated and should not be redistributed in this repository.
- The local command-template boundary keeps MakeYourBrick usable with fake,
  future, or alternative 3D reconstruction backends.

## References

- SAM 3D Objects GitHub: https://github.com/facebookresearch/sam-3d-objects
- SAM 3D Objects model page: https://huggingface.co/facebook/sam-3d-objects
- Meta SAM 3D research page: https://ai.meta.com/research/sam3d/
