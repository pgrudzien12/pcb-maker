"""Minimal pipeline-only CLI stub.

Current behavior:
  pcb-maker --pipeline path/to/pipeline.yaml

Loads the pipeline YAML and prints a stage listing. No execution yet.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List
from pipeline import load_pipeline, PipelineError  # type: ignore!


def cli(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="pcb-maker (pipeline loader prototype)")
    parser.add_argument("--pipeline", type=Path, required=True, help="Path to pipeline YAML definition")
    args = parser.parse_args(argv)

    try:
        cfg = load_pipeline(args.pipeline)
    except PipelineError as e:
        parser.error(f"Pipeline load failed: {e}")

    print(f"Loaded pipeline version: {cfg.version}")
    print("Stages:")
    for idx, st in enumerate(cfg.stages, 1):
        print(f"  {idx:02d}. {st.name}  uses={st.uses}")
    return 0


def main():  # pragma: no cover
    return cli()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
