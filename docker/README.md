# Docker SAM 3D Runtime

This directory contains a GPU Docker image for local MakeYourBrick + SAM 3D
Objects use. It follows the official SAM 3D Objects setup rather than vendoring
checkpoints or the external repository into MakeYourBrick.

## Build

From the repository root:

```bash
docker build \
  -f docker/sam3d.Dockerfile \
  -t makeyourbrick-sam3d:local \
  .
```

For clearer logs during the long SAM dependency install, use:

```bash
docker build --progress=plain \
  -f docker/sam3d.Dockerfile \
  -t makeyourbrick-sam3d:local \
  .
```

To pin a specific SAM 3D Objects commit or tag:

```bash
docker build \
  -f docker/sam3d.Dockerfile \
  --build-arg SAM3D_REF=<commit-or-tag> \
  -t makeyourbrick-sam3d:local \
  .
```

The image sets `TORCH_CUDA_ARCH_LIST` during build because Docker builds do not
normally expose the host GPU to PyTorch extension compilation. The default
covers common Turing, Ampere, Ada, and Hopper GPUs. To narrow or change it:

```bash
docker build \
  -f docker/sam3d.Dockerfile \
  --build-arg CUDA_ARCH_LIST="8.6" \
  -t makeyourbrick-sam3d:local \
  .
```

On the host, `nvidia-smi --query-gpu=compute_cap --format=csv,noheader` prints
the value to use for your GPU.

## GPU Check

Before running the app, confirm Docker can see the NVIDIA GPU:

```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

## Hugging Face Models

SAM 3D Objects checkpoints are gated. Do not bake them into the image or commit
tokens. After Hugging Face access is approved, pass a token at runtime and keep
the Hugging Face cache mounted. SAM2 and SAM 3D Objects weights are downloaded
on demand into `third_party/sam-3d-objects/hf-cache`.

Linux/macOS bash:

```bash
read -rsp "Hugging Face token: " HF_TOKEN
echo
export HF_TOKEN
```

PowerShell:

```powershell
$env:HF_TOKEN = Read-Host -AsSecureString "Hugging Face token" |
  ConvertFrom-SecureString -AsPlainText
```

Unset the variable after the run if you no longer need it. If a token was pasted
into a terminal or chat, revoke it in Hugging Face settings and create a new one.

To inspect or pre-warm the cache from a shell inside the container:

```bash
docker run --rm -it --gpus all \
  -e HF_TOKEN \
  -v "$(pwd)/third_party/sam-3d-objects/hf-cache:/root/.cache/huggingface" \
  makeyourbrick-sam3d:local \
  bash
```

## Run Real SAM UI

Run the UI + backend with the real SAM runners:

```bash
docker run --rm --gpus all -p 8000:8000 \
  -e HF_TOKEN \
  -v "$(pwd)/outputs:/workspace/MakeYourBrick/outputs" \
  -v "$(pwd)/third_party/sam-3d-objects/torch-cache:/root/.cache/torch" \
  -v "$(pwd)/third_party/sam-3d-objects/hf-cache:/root/.cache/huggingface" \
  makeyourbrick-sam3d:local
```

Open:

```text
http://127.0.0.1:8000
```

Then upload an image, select the target object with points or a box, and wait
for the mask preview. The image uses SAM2 from Hugging Face
(`facebook/sam2.1-hiera-large`) for interactive segmentation, then SAM 3D
Objects (`facebook/sam-3d-objects`) auto-resolves its gated checkpoints from the
same Hugging Face cache, writes a GLB, voxelizes it, and returns an LDraw `.ldr`
artifact when you click Generate LDR.

SAM2 and SAM 3D share a single in-process GPU lock so a click segmentation and a
3D reconstruction do not run on the GPU at the same time. If another host
process is using VRAM, close it first; SAM 3D can need almost the full 10 GB on
an RTX 3080 during model load. On 10 GB GPUs, prefer the staged depth mode below
instead of keeping the depth model resident on CUDA for the whole SAM 3D run.

To use a smaller SAM2 checkpoint, override the model id:

```bash
docker run --rm --gpus all -p 8000:8000 \
  -e HF_TOKEN \
  -v "$(pwd)/outputs:/workspace/MakeYourBrick/outputs" \
  -v "$(pwd)/third_party/sam-3d-objects/torch-cache:/root/.cache/torch" \
  -v "$(pwd)/third_party/sam-3d-objects/hf-cache:/root/.cache/huggingface" \
  -e MAKEYOURBRICK_SAM2_MODEL_ID=facebook/sam2.1-hiera-base-plus \
  makeyourbrick-sam3d:local
```

The image's default SAM command is:

```text
python /workspace/MakeYourBrick/scripts/sam3d_export.py --repo {repo} --depth-device cpu --dino-dtype fp16 --image {image} --mask {mask} --output {output}
```

For RTX 3080-class 10 GB GPUs, run the depth model on CUDA first, free it, and
then load SAM 3D with the precomputed point map:

```bash
docker run --rm --gpus all -p 8000:8000 \
  -e HF_TOKEN \
  -v "$(pwd)/outputs:/workspace/MakeYourBrick/outputs" \
  -v "$(pwd)/third_party/sam-3d-objects/torch-cache:/root/.cache/torch" \
  -v "$(pwd)/third_party/sam-3d-objects/hf-cache:/root/.cache/huggingface" \
  -e 'MAKEYOURBRICK_SAM_COMMAND=python /workspace/MakeYourBrick/scripts/sam3d_export.py --repo {repo} --depth-device staged-cuda --dino-dtype fp16 --image {image} --mask {mask} --output {output}' \
  makeyourbrick-sam3d:local
```

When `/opt/sam-3d-objects/checkpoints/hf/pipeline.yaml` is missing, the script
downloads `MAKEYOURBRICK_SAM3D_MODEL_ID` from Hugging Face, finds the snapshot's
`checkpoints/` directory, and symlinks it into the SAM 3D repo. It writes a
vertex-colour GLB mesh by default because that is faster for an end-to-end test
than SAM texture baking. To override it, set `MAKEYOURBRICK_SAM_COMMAND`
explicitly. For example, add `--texture-baking` for slower textured GLB export.
Use `--depth-device cuda` only on GPUs with enough VRAM to keep MoGe and SAM 3D
resident at the same time; on 10 GB cards, use `--depth-device staged-cuda`.

After the first successful download, the app can reuse the mounted cache. If you
want to force offline cache use, append `--local-files-only` to
`MAKEYOURBRICK_SAM_COMMAND`.

## Run Fake Backend

To verify the web/backend/LEGO pipeline without SAM checkpoints, override the
runner mode:

```bash
docker run --rm --gpus all -p 8000:8000 \
  -v "$(pwd)/outputs:/workspace/MakeYourBrick/outputs" \
  -e MAKEYOURBRICK_RUNNER_MODE=fake \
  makeyourbrick-sam3d:local
```

## Notes

- Native Windows execution is not the target for SAM 3D Objects.
- Docker Desktop must use the WSL2 backend for GPU passthrough.
- The container uses CUDA 12.1 because the official SAM setup references
  PyTorch/cu121 and Kaolin wheels for torch 2.5.1/cu121.
- Build time can be long because PyTorch3D/Kaolin/SAM dependencies are heavy.
- If Docker Desktop exits with `failed to receive status ... EOF`, the build
  process usually lost contact with the Docker daemon during a long dependency
  install. Re-run the same build command; the Dockerfile keeps the official SAM
  install steps split into cacheable layers so it can resume closer to the
  failing package. If it repeats, increase Docker Desktop memory/disk limits and
  rebuild with `--progress=plain`.
