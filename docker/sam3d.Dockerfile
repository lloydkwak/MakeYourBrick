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
ARG MINIFORGE_URL=https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh

ENV CONDA_DIR=/opt/conda
ENV SAM3D_DIR=/opt/sam-3d-objects
ENV APP_DIR=/workspace/MakeYourBrick
ENV PATH=${CONDA_DIR}/envs/sam3d-objects/bin:${CONDA_DIR}/bin:${PATH}
ENV PIP_EXTRA_INDEX_URL="https://pypi.ngc.nvidia.com https://download.pytorch.org/whl/cu121"
ENV PIP_FIND_LINKS="https://nvidia-kaolin.s3.us-east-2.amazonaws.com/torch-2.5.1_cu121.html"
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

RUN source "${CONDA_DIR}/etc/profile.d/conda.sh" \
    && conda activate sam3d-objects \
    && pip install -e '.[dev]' \
    && pip install -e '.[p3d]' \
    && pip install -e '.[inference]' \
    && pip install 'huggingface-hub[cli]<1.0' \
    && ./patching/hydra

WORKDIR ${APP_DIR}

COPY . ${APP_DIR}

RUN source "${CONDA_DIR}/etc/profile.d/conda.sh" \
    && conda activate sam3d-objects \
    && pip install -r requirements.txt \
    && pip install -e .

ENV MAKEYOURBRICK_RUNNER_MODE=fake
ENV MAKEYOURBRICK_SAM_REPO=${SAM3D_DIR}
ENV MAKEYOURBRICK_SAM_COMMAND=""

EXPOSE 8000

CMD ["python", "-m", "uvicorn", "makeyourbrick.server.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]
