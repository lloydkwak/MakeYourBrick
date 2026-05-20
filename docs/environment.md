# Environment

## Recommended Runtime

Use the Docker image for real SAM2 + SAM 3D Objects runs. It installs the SAM
stack, MakeYourBrick, and the local web backend in one CUDA-enabled container.

Requirements:

- Linux with NVIDIA Container Toolkit, or Windows Docker Desktop with WSL2 GPU passthrough
- NVIDIA GPU
- Docker access to the GPU
- Hugging Face token with access to `facebook/sam-3d-objects`
- mounted caches for Hugging Face and torch model downloads

Verify GPU passthrough:

```bash
docker run --rm --gpus all nvidia/cuda:12.1.1-base-ubuntu22.04 nvidia-smi
```

## Python Development

For non-SAM development and mesh-only tests:

- Python 3.10+
- verified locally with Python 3.12 for lightweight checks

Install:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
```

Core dependencies:

- `numpy`
- `scipy`
- `trimesh`
- `Pillow`
- `fastapi`
- `pydantic`
- `uvicorn`
- `python-multipart`
- `pytest`
- `ruff`

## Model Data

Do not commit model checkpoints. Runtime caches should live under:

```text
third_party/sam-3d-objects/hf-cache/
third_party/sam-3d-objects/torch-cache/
```

The Docker run commands mount those directories to:

```text
/root/.cache/huggingface
/root/.cache/torch
```

## Generated Files

Generated artifacts belong under:

```text
outputs/
```

Typical outputs:

- uploaded images and masks
- raw SAM GLB meshes
- voxel `.npz` files
- conversion reports
- final `.ldr` files

Only placeholder files should be versioned under generated-output directories.
