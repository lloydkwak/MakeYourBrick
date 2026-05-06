from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    parser.add_argument("--exit-code", type=int, default=0)
    args = parser.parse_args()
    if args.exit_code:
        raise SystemExit(args.exit_code)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(b"mesh")


if __name__ == "__main__":
    main()

