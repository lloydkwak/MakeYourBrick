from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MeshArtifact:
    path: Path
    source: str
    is_watertight: bool = False


@dataclass(frozen=True)
class VoxelArtifact:
    path: Path
    pitch: float
    origin: tuple[float, float, float]


@dataclass(frozen=True)
class BrickSpec:
    part_id: str
    width: int
    depth: int
    height: int = 1


@dataclass(frozen=True)
class Brick:
    part_id: str
    color_id: int
    x: int
    y: int
    z: int
    width: int
    depth: int
    height: int = 1
    rotation_degrees: int = 0

