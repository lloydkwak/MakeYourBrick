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

To pin a specific SAM 3D Objects commit or tag:

```bash
docker build \
  -f docker/sam3d.Dockerfile \
  --build-arg SAM3D_REF=<commit-or-tag> \
  -t makeyourbrick-sam3d:local \
  .
```

## GPU Check

Before running the app, confirm Docker can see the NVIDIA GPU:

```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

## Checkpoints

SAM 3D Objects checkpoints are gated. Do not bake them into the image. After
Hugging Face access is approved, either:

- mount a local checkpoint directory into `/opt/sam-3d-objects/checkpoints`, or
- run `hf auth login` inside the container and download checkpoints there.

Example persistent mount:

```bash
docker run --rm -it --gpus all \
  -v "%cd%/third_party/sam-3d-objects/checkpoints:/opt/sam-3d-objects/checkpoints" \
  makeyourbrick-sam3d:local \
  bash
```

On PowerShell, `${PWD}` may be used instead of `%cd%`:

```powershell
docker run --rm -it --gpus all `
  -v "${PWD}/third_party/sam-3d-objects/checkpoints:/opt/sam-3d-objects/checkpoints" `
  makeyourbrick-sam3d:local `
  bash
```

## Run Fake Backend

The default container command starts the local FastAPI backend with the fake SAM
runner. This verifies the web/backend/LEGO pipeline without downloading SAM
checkpoints:

```bash
docker run --rm --gpus all -p 8000:8000 makeyourbrick-sam3d:local
```

Open `apps/web/index.html` on the host and set the API URL to:

```text
http://127.0.0.1:8000
```

## Run Real SAM Backend

After implementing or providing a SAM export script that writes a textured GLB
to `{output}`, run:

```bash
docker run --rm --gpus all -p 8000:8000 \
  -v "%cd%/outputs:/workspace/MakeYourBrick/outputs" \
  -v "%cd%/third_party/sam-3d-objects/checkpoints:/opt/sam-3d-objects/checkpoints" \
  -e MAKEYOURBRICK_RUNNER_MODE=sam3d \
  -e MAKEYOURBRICK_SAM_REPO=/opt/sam-3d-objects \
  -e MAKEYOURBRICK_SAM_COMMAND="python path/to/sam3d_export.py --image {image} --mask {mask} --output {output}" \
  makeyourbrick-sam3d:local
```

The export command contract is:

```text
image + mask -> textured triangle mesh at {output}, preferably raw_model.glb
```

## Notes

- Native Windows execution is not the target for SAM 3D Objects.
- Docker Desktop must use the WSL2 backend for GPU passthrough.
- The container uses CUDA 12.1 because the official SAM setup references
  PyTorch/cu121 and Kaolin wheels for torch 2.5.1/cu121.
- Build time can be long because PyTorch3D/Kaolin/SAM dependencies are heavy.
