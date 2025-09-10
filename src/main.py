"""CLI entrypoint for pcb-maker (early pipeline prototype).

Responsibilities (current scope):
    1. Parse CLI arguments
    2. Configure logging verbosity
    3. Load and validate the pipeline YAML
    4. List declared stages
    5. If a ``loader.kicad`` stage exists, parse the KiCad .gbrjob file and
         output a concise summary (board size, layers, subset of design rules).

No execution of subsequent stages happens yet; this is intentionally a
visibility / discovery step while the execution engine is being designed.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path
from typing import List, Optional, Any
from pipeline import load_pipeline, PipelineError, execute_pipeline
from kicad_job import parse_kicad_job_if_present


def cli(argv: List[str] | None = None) -> int:
    """Entry point used by tests & __main__.

    Orchestrates the high level flow by delegating to smaller, intention-revealing
    helpers. Returns a process exit code (0 success / non‑zero error).
    """
    args = parse_args(argv)
    log = configure_logging(args.verbose)

    cfg = load_pipeline_config(args.pipeline, log)
    if cfg is None:
        return 1

    list_declared_stages(cfg, log)
    # parse and attach KiCad job (if present) so loader stages may reuse it
    job = parse_kicad_job_if_present(cfg, cfg.source_path.parent if cfg.source_path else Path.cwd(), log, verbose=args.verbose)
    if job is not None:
        # attach parsed job to the config object so stage implementations can consult it
        try:
            cfg.parsed_kicad_job = job
        except Exception:
            # Fall back to setattr for unexpected config shapes
            setattr(cfg, "parsed_kicad_job", job)

    # Execute the pipeline (stage implementations may consult cfg._parsed_kicad_job)
    log.info("Executing pipeline stages...")
    result_ctx = execute_pipeline(cfg, log)
    log.info("Pipeline finished. Last stage output: %s", type(result_ctx.get("last")))
    return 0


def parse_args(argv: List[str] | None) -> argparse.Namespace:
    """Parse command line arguments.

    Parameters
    ----------
    argv: Optional explicit argument list (None uses sys.argv).
    """
    parser = argparse.ArgumentParser(description="pcb-maker (pipeline prototype)")
    parser.add_argument("--pipeline", type=Path, required=True, help="Path to pipeline YAML definition")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging output")
    return parser.parse_args(argv)

def configure_logging(verbose: bool) -> logging.Logger:
    """Configure root logging and return the project logger.

    Verbosity toggles DEBUG/INFO levels.
    """
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format="%(levelname)s: %(message)s",
    )
    return logging.getLogger("pcb_maker")

def load_pipeline_config(path: Path, log: logging.Logger) -> Optional[Any]:  # Any for early prototype
    """Load pipeline YAML into a parsed configuration object.

    Returns None and logs an error if loading or validation fails.
    """
    try:
        cfg = load_pipeline(path)
    except PipelineError as e:
        log.error("Pipeline load failed: %s", e)
        return None
    log.info("Loaded pipeline version: %s", cfg.version)
    return cfg


def list_declared_stages(cfg: Any, log: logging.Logger) -> None:
    """Log each declared stage (informational; no execution yet)."""
    log.info("Declared stages (execution not implemented yet):")
    for idx, st in enumerate(cfg.stages, 1):
        log.info("  %02d. %s  uses=%s", idx, st.name, st.uses)




__all__ = [
    "cli",
    "parse_args",
    "configure_logging",
    "load_pipeline_config",
    "list_declared_stages",
]


def main():  # pragma: no cover
    return cli()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
