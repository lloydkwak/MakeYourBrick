from __future__ import annotations

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


class JobRequest(BaseModel):
    image_id: str
    mask_id: str | None = None
    target_studs: int = Field(default=48, ge=8, le=128)
    sample_colors: bool = True
    optimize: bool = True
    fill: bool = True
    default_color_id: int = Field(default=16, ge=0, le=999)


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
    voxel_url: str
    brick_count: int | None = None
    reduction_percent: float | None = None
    warnings: list[str] = Field(default_factory=list)
