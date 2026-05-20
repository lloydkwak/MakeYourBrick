# SAM 3D Local Setup

The supported local setup is Docker-first. MakeYourBrick does not vendor Meta's
SAM 3D Objects repository, SAM2, or checkpoints into this repository.

## Docker Build

```bash
docker build -f docker/sam3d.Dockerfile -t makeyourbrick-sam3d:local .
```

The image:

- clones SAM 3D Objects into `/opt/sam-3d-objects`
- clones SAM2 into `/opt/sam2`
- creates the official `sam3d-objects` conda environment
- installs MakeYourBrick
- starts the FastAPI app on port `8000`

## Hugging Face Access

SAM 3D Objects is gated. Request access on Hugging Face and pass a token at
runtime:

```bash
read -rsp "Hugging Face token: " HF_TOKEN
echo
export HF_TOKEN
```

Do not paste tokens into committed files. Revoke any token that has been exposed.

## Run

For RTX 3080-class 10 GB GPUs, use staged depth mode:

```bash
docker run --rm --gpus all -p 8000:8000 \
  -e HF_TOKEN \
  -v "$(pwd)/outputs:/workspace/MakeYourBrick/outputs" \
  -v "$(pwd)/third_party/sam-3d-objects/torch-cache:/root/.cache/torch" \
  -v "$(pwd)/third_party/sam-3d-objects/hf-cache:/root/.cache/huggingface" \
  -e 'MAKEYOURBRICK_SAM_COMMAND=python /workspace/MakeYourBrick/scripts/sam3d_export.py --repo {repo} --depth-device staged-cuda --dino-dtype fp16 --image {image} --mask {mask} --output {output}' \
  makeyourbrick-sam3d:local
```

Open:

```text
http://127.0.0.1:8000
```

## What Happens At Runtime

1. The UI uploads the image to the FastAPI backend.
2. User points or boxes are sent to SAM2.
3. SAM2 writes a mask PNG.
4. SAM 3D Objects reconstructs a raw `.glb`.
5. The UI previews the raw GLB directly.
6. MakeYourBrick converts the GLB to `.ldr`.

When `/opt/sam-3d-objects/checkpoints/hf/pipeline.yaml` is missing,
`scripts/sam3d_export.py` downloads `MAKEYOURBRICK_SAM3D_MODEL_ID` from
Hugging Face, finds the snapshot `checkpoints/` directory, and links it into the
SAM 3D checkout.

## Low-VRAM Notes

The default Docker image command uses CPU depth because it is conservative. For
10 GB GPUs, the recommended runtime override is:

```text
--depth-device staged-cuda --dino-dtype fp16
```

That computes depth on CUDA, frees the depth model, then loads SAM 3D for
reconstruction. Use `--depth-device cuda` only when the GPU has enough VRAM to
keep the depth model and SAM 3D resident together.

## Export Contract

MakeYourBrick expects:

```text
input image + mask -> raw_model.glb
```

GLB is preferred because it keeps geometry, transforms, vertex colors/materials,
and textures in one file. OBJ can still be used for mesh-only conversion, but
sidecar `.mtl` and texture files must stay together.

## Offline Cache

After the first successful download, the mounted caches can be reused. To force
offline cache use, append `--local-files-only` to `MAKEYOURBRICK_SAM_COMMAND`.

## References

- SAM 3D Objects GitHub: https://github.com/facebookresearch/sam-3d-objects
- SAM 3D Objects model page: https://huggingface.co/facebook/sam-3d-objects
- SAM2 GitHub: https://github.com/facebookresearch/sam2
- Meta SAM 3D research page: https://ai.meta.com/research/sam3d/
