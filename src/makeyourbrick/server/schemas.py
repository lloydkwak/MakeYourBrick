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

