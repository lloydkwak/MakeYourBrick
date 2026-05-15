from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ImageUploadResponse(BaseModel):
    image_id: str
    image_url: str
    width: int
    height: int
    filename: str


class SelectionRequest(BaseModel):
    positive_points: list[tuple[int, int]] = Field(default_factory=list)
    negative_points: list[tuple[int, int]] = Field(default_factory=list)
    box: tuple[int, int, int, int] | None = None


class SelectionResponse(BaseModel):
    image_id: str
    mask_id: str
    mask_url: str
    status: str


class HealthResponse(BaseModel):
    status: str


class ServerConfigResponse(BaseModel):
    runner_mode: str
    sam_repo: str
    has_sam_command: bool
    timeout_seconds: int
    requires_mask: bool


class JobRequest(BaseModel):
    image_id: str
    mask_id: str | None = None
    base_size_studs: int = Field(default=32, ge=8, le=256)
    wall_thickness: int = Field(default=2, ge=1, le=16)
    base_thickness: int = Field(default=3, ge=0, le=64)
    up_axis: Literal["auto", "none", "x", "y", "z"] = "auto"


class JobStatusResponse(BaseModel):
    job_id: str
    image_id: str
    status: str
    stage: str
    progress: float
    message: str
    error: str | None = None


class JobResultResponse(BaseModel):
    job_id: str
    status: str
    ldr_url: str
    report_url: str
    mesh_inspect_url: str
    raw_mesh_url: str
    voxel_url: str
    brick_count: int | None = None
    reduction_percent: float | None = None
    warnings: list[str] = Field(default_factory=list)
