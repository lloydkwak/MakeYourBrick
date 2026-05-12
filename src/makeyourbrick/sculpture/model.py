from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from makeyourbrick.types import Brick

HeightUnit = Literal["brick", "plate"]
ColorMode = Literal["constant", "mesh", "layer"]


@dataclass(frozen=True)
class VoxelModel:
    occupancy: np.ndarray
    color_ids: np.ndarray
    pitch: float
    origin: tuple[float, float, float]
    height_unit: HeightUnit = "brick"

    def __post_init__(self) -> None:
        if self.occupancy.ndim != 3:
            raise ValueError("occupancy must be a 3D array.")
        if self.color_ids.shape != self.occupancy.shape:
            raise ValueError("color_ids must match occupancy shape.")
        if self.pitch <= 0:
            raise ValueError("pitch must be positive.")
        if len(self.origin) != 3:
            raise ValueError("origin must have three coordinates.")
        if self.height_unit not in {"brick", "plate"}:
            raise ValueError(f"Unsupported height unit: {self.height_unit}")

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(int(value) for value in self.occupancy.shape)

    @property
    def occupied_count(self) -> int:
        return int(self.occupancy.sum())

    def with_occupancy(self, occupancy: np.ndarray, color_ids: np.ndarray | None = None) -> "VoxelModel":
        return VoxelModel(
            occupancy=occupancy.astype(bool),
            color_ids=self.color_ids.copy() if color_ids is None else color_ids.astype(np.int32),
            pitch=self.pitch,
            origin=self.origin,
            height_unit=self.height_unit,
        )


@dataclass(frozen=True)
class SculptureSettings:
    base_size_studs: int | None = None
    target_width_studs: int | None = None
    target_depth_studs: int | None = None
    wall_thickness: int = 1
    base_thickness: int = 0
    brick_palette: str = "compact"
    height_unit: HeightUnit = "brick"
    color_mode: ColorMode = "mesh"
    steps_by_layer: bool = True

    def __post_init__(self) -> None:
        if self.base_size_studs is not None and self.base_size_studs <= 0:
            raise ValueError("base_size_studs must be positive when provided.")
        if self.target_width_studs is not None and self.target_width_studs <= 0:
            raise ValueError("target_width_studs must be positive when provided.")
        if self.target_depth_studs is not None and self.target_depth_studs <= 0:
            raise ValueError("target_depth_studs must be positive when provided.")
        if self.wall_thickness < 1:
            raise ValueError("wall_thickness must be at least 1.")
        if self.base_thickness < 0:
            raise ValueError("base_thickness must be non-negative.")
        if self.height_unit not in {"brick", "plate"}:
            raise ValueError(f"Unsupported height unit: {self.height_unit}")
        if self.color_mode not in {"constant", "mesh", "layer"}:
            raise ValueError(f"Unsupported color mode: {self.color_mode}")


@dataclass
class LayeredBrickModel:
    bricks_by_layer: dict[int, list[Brick]]

    @classmethod
    def from_bricks(cls, bricks: list[Brick]) -> "LayeredBrickModel":
        layers: dict[int, list[Brick]] = {}
        for brick in bricks:
            layers.setdefault(int(brick.y), []).append(brick)
        return cls(bricks_by_layer=dict(sorted(layers.items())))

    def bricks(self) -> list[Brick]:
        return [
            brick
            for layer in sorted(self.bricks_by_layer)
            for brick in self.bricks_by_layer[layer]
        ]

    @property
    def layer_count(self) -> int:
        return len(self.bricks_by_layer)

    @property
    def brick_count(self) -> int:
        return sum(len(bricks) for bricks in self.bricks_by_layer.values())

