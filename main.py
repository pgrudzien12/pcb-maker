"""pcb-maker: CLI to experiment with Gerber -> Snapmaker 2.0 G-code using PyGerber.

DISCLAIMER:
    Work in progress. We now rely on PyGerber for parsing/validation instead of a
    home-grown regex. Coordinate extraction is still placeholder: currently we
    pull raw X/Y statements directly from source for path sequencing. Future work
    will traverse PyGerber's parsed model to extract true draw/flash primitives,
    distinguish moves vs exposures, apply aperture/tool widths and isolation.
"""

from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List

def main():  # backward compatibility
    print("pcb-maker: CLI to experiment with Gerber -> Snapmaker 2.0 G-code using PyGerber")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
