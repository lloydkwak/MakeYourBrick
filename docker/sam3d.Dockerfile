# syntax=docker/dockerfile:1
#
# SAM 3D Objects + MakeYourBrick local GPU image.
#
# This Dockerfile follows Meta's official SAM 3D Objects setup flow:
# - linux-64
# - CUDA/PyTorch cu121 package indexes
# - environments/default.yml
# - pip extras: dev, p3d, inference
# - Kaolin find-links for torch-2.5.1/cu121
# - hydra patch script
#
# Checkpoints are gated and must not be baked into the image. Mount or download
# them at runtime after authenticating with Hugging Face.

FROM nvidia/cuda:12.1.1-devel-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive
ARG SAM3D_REPO=https://github.com/facebookresearch/sam-3d-objects.git
ARG SAM3D_REF=main
ARG SAM2_REPO=https://github.com/facebookresearch/sam2.git
ARG SAM2_REF=main
ARG MINIFORGE_URL=https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh

ENV CONDA_DIR=/opt/conda
ENV SAM3D_DIR=/opt/sam-3d-objects
ENV SAM2_DIR=/opt/sam2
ENV APP_DIR=/workspace/MakeYourBrick
ENV PATH=${CONDA_DIR}/envs/sam3d-objects/bin:${CONDA_DIR}/bin:${PATH}
ENV PIP_EXTRA_INDEX_URL="https://pypi.ngc.nvidia.com https://download.pytorch.org/whl/cu121"
ENV PIP_FIND_LINKS="https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.5.1_cu121.html"
ENV PIP_DISABLE_PIP_VERSION_CHECK=1
ENV PIP_NO_INPUT=1
ENV MAMBA_NO_BANNER=1
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

SHELL ["/bin/bash", "-lc"]

RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    ca-certificates \
    curl \
    ffmpeg \
    git \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ninja-build \
    wget \
    && rm -rf /var/lib/apt/lists/*

RUN curl -L "${MINIFORGE_URL}" -o /tmp/miniforge.sh \
    && bash /tmp/miniforge.sh -b -p "${CONDA_DIR}" \
    && rm /tmp/miniforge.sh \
    && conda install -n base -c conda-forge -y mamba \
    && mamba clean -afy \
    && mamba --version

RUN git clone --depth 1 --branch "${SAM3D_REF}" "${SAM3D_REPO}" "${SAM3D_DIR}"

WORKDIR ${SAM3D_DIR}

RUN mamba env create -f environments/default.yml \
    && mamba clean -afy

RUN --mount=type=cache,target=/root/.cache/pip \
    source "${CONDA_DIR}/etc/profile.d/conda.sh" \
    && conda activate sam3d-objects \
    && python -m pip install -e '.[dev]'

RUN --mount=type=cache,target=/root/.cache/pip \
    source "${CONDA_DIR}/etc/profile.d/conda.sh" \
    && conda activate sam3d-objects \
    && python -m pip install -e '.[p3d]'

ARG CUDA_ARCH_LIST=7.5;8.0;8.6;8.9;9.0
ENV TORCH_CUDA_ARCH_LIST=${CUDA_ARCH_LIST}

RUN --mount=type=cache,target=/root/.cache/pip \
    source "${CONDA_DIR}/etc/profile.d/conda.sh" \
    && conda activate sam3d-objects \
    && python -m pip install -e '.[inference]'

RUN --mount=type=cache,target=/root/.cache/pip \
    source "${CONDA_DIR}/etc/profile.d/conda.sh" \
    && conda activate sam3d-objects \
    && python -m pip install 'huggingface-hub[cli]<1.0' \
    && ./patching/hydra

RUN git clone --depth 1 --branch "${SAM2_REF}" "${SAM2_REPO}" "${SAM2_DIR}" \
    && source "${CONDA_DIR}/etc/profile.d/conda.sh" \
    && conda activate sam3d-objects \
    && cd "${SAM2_DIR}" \
    && SAM2_BUILD_CUDA=0 python -m pip install --no-build-isolation --no-deps -e .

WORKDIR ${APP_DIR}

COPY . ${APP_DIR}

RUN --mount=type=cache,target=/root/.cache/pip \
    source "${CONDA_DIR}/etc/profile.d/conda.sh" \
    && conda activate sam3d-objects \
    && python -m pip install -r requirements.txt \
    && python -m pip install -e .

ENV MAKEYOURBRICK_RUNNER_MODE=sam3d
ENV MAKEYOURBRICK_SEGMENTER_MODE=sam2
ENV MAKEYOURBRICK_SAM2_MODEL_ID=facebook/sam2.1-hiera-large
ENV MAKEYOURBRICK_SAM2_DEVICE=auto
ENV MAKEYOURBRICK_SAM3D_MODEL_ID=facebook/sam-3d-objects
ENV PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
ENV MAKEYOURBRICK_SAM_REPO=${SAM3D_DIR}
ENV MAKEYOURBRICK_SAM_COMMAND="python /workspace/MakeYourBrick/scripts/sam3d_export.py --repo {repo} --depth-device cpu --dino-dtype fp16 --image {image} --mask {mask} --output {output}"
ENV MAKEYOURBRICK_RAW_MESH_SUFFIX=.glb

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "makeyourbrick.server.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
