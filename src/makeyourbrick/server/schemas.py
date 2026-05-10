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
    target_studs: int = Field(default=48, ge=8, le=128)
    sample_colors: bool = True
    optimize: bool = True
    optimizer: Literal["greedy", "layered"] = "greedy"
    fill: bool = True
    default_color_id: int = Field(default=16, ge=0, le=999)
    repair_mode: Literal["none", "basic", "manifold", "convex-hull"] = "basic"
    sculpture_mode: Literal["solid", "shell"] = "solid"
    wall_thickness: int = Field(default=1, ge=1, le=16)
    base_thickness: int = Field(default=0, ge=0, le=64)
    steps_by_layer: bool = False


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
    raw_mesh_url: str
    cleaned_mesh_url: str
    mesh_inspect_url: str | None = None
    repair_report_url: str | None = None
    voxel_url: str
    brick_count: int | None = None
    reduction_percent: float | None = None
    warnings: list[str] = Field(default_factory=list)
