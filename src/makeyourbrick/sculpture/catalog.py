from __future__ import annotations

from dataclasses import dataclass

from makeyourbrick.brickify.optimizer import (
    COMPACT_SCULPTURE_BRICKS,
    DEFAULT_BRICKS,
    PLATE_SCULPTURE_BRICKS,
    STUDIO_SCULPTURE_BRICKS,
)
from makeyourbrick.types import BrickSpec


@dataclass(frozen=True)
class BrickCatalog:
    name: str
    specs: tuple[BrickSpec, ...]
    support_specs: tuple[BrickSpec, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("catalog name is required.")
        if not self.specs:
            raise ValueError("catalog specs must not be empty.")

    @property
    def max_span(self) -> int:
        return max(max(spec.width, spec.depth) for spec in self.specs)

    @property
    def part_ids(self) -> tuple[str, ...]:
        return tuple(spec.part_id for spec in self.specs)


def catalog_for_palette(name: str) -> BrickCatalog:
    if name == "full":
        return BrickCatalog("full", DEFAULT_BRICKS)
    if name == "studio":
        return BrickCatalog("studio", STUDIO_SCULPTURE_BRICKS)
    if name == "compact":
        return BrickCatalog("compact", COMPACT_SCULPTURE_BRICKS)
    if name == "plates":
        return BrickCatalog("plates", PLATE_SCULPTURE_BRICKS)
    raise ValueError(f"Unsupported brick catalog: {name}")

