from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from makeyourbrick.types import Brick


@dataclass(frozen=True)
class VoxelModel:
    occupancy: np.ndarray
    color_ids: np.ndarray
    pitch: float
    origin: tuple[float, float, float]

    def __post_init__(self) -> None:
        if self.occupancy.ndim != 3:
            raise ValueError("occupancy must be a 3D array.")
        if self.color_ids.shape != self.occupancy.shape:
            raise ValueError("color_ids must match occupancy.")
        if self.pitch <= 0:
            raise ValueError("pitch must be positive.")

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(int(value) for value in self.occupancy.shape)

    @property
    def occupied_count(self) -> int:
        return int(self.occupancy.sum())

    def with_occupancy(self, occupancy: np.ndarray, color_ids: np.ndarray) -> "VoxelModel":
        return VoxelModel(
            occupancy=occupancy.astype(bool),
            color_ids=color_ids.astype(np.int32),
            pitch=self.pitch,
            origin=self.origin,
        )


@dataclass(frozen=True)
class SculptureSettings:
    wall_thickness: int = 2
    base_thickness: int = 3

    def __post_init__(self) -> None:
        if self.wall_thickness < 1:
            raise ValueError("wall_thickness must be at least 1.")
        if self.base_thickness < 0:
            raise ValueError("base_thickness must be non-negative.")


@dataclass
class LayeredBrickModel:
    bricks_by_layer: dict[int, list[Brick]]

    @classmethod
    def from_bricks(cls, bricks: list[Brick]) -> "LayeredBrickModel":
        layers: dict[int, list[Brick]] = {}
        for brick in bricks:
            layers.setdefault(int(brick.y), []).append(brick)
        return cls(dict(sorted(layers.items())))

    def bricks(self) -> list[Brick]:
        return [brick for layer in sorted(self.bricks_by_layer) for brick in self.bricks_by_layer[layer]]

    @property
    def layer_count(self) -> int:
        return len(self.bricks_by_layer)

    @property
    def brick_count(self) -> int:
        return sum(len(bricks) for bricks in self.bricks_by_layer.values())
