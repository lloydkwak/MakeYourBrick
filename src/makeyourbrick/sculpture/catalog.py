from __future__ import annotations

from dataclasses import dataclass

from makeyourbrick.brickify.optimizer import STUDIO_SCULPTURE_BRICKS
from makeyourbrick.types import BrickSpec


@dataclass(frozen=True)
class BrickCatalog:
    name: str
    specs: tuple[BrickSpec, ...]

    @property
    def part_ids(self) -> tuple[str, ...]:
        return tuple(spec.part_id for spec in self.specs)


def catalog_for_palette(name: str = "studio") -> BrickCatalog:
    if name != "studio":
        raise ValueError("Only the Studio sculpture brick catalog is supported.")
    return BrickCatalog("studio", STUDIO_SCULPTURE_BRICKS)
