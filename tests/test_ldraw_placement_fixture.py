from __future__ import annotations

from scripts.make_ldraw_placement_fixture import placement_fixture_bricks
from makeyourbrick.io.ldr_writer import brick_to_ldr_line


def test_placement_fixture_covers_supported_basic_bricks() -> None:
    bricks = placement_fixture_bricks()

    assert {brick.part_id for brick in bricks} == {
        "3001.dat",
        "3010.dat",
        "3003.dat",
        "3004.dat",
        "3005.dat",
    }
    assert any(brick.rotation_degrees == 90 for brick in bricks)


def test_placement_fixture_uses_centered_large_brick_origins() -> None:
    lines = [brick_to_ldr_line(brick) for brick in placement_fixture_bricks()]

    assert "1 2 90 0 10 1 0 0 0 1 0 0 0 1 3003.dat" in lines
    assert "1 15 190 0 30 1 0 0 0 1 0 0 0 1 3001.dat" in lines
    assert "1 16 30 -24 90 0 0 1 0 1 0 -1 0 0 3001.dat" in lines
