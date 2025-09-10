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
from pipeline import load_pipeline, PipelineError  # type: ignore!


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
    parse_kicad_job_if_present(cfg, log, verbose=args.verbose)
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

def parse_kicad_job_if_present(cfg: Any, log: logging.Logger, *, verbose: bool) -> None:
    """Locate and parse KiCad .gbrjob if a loader.kicad stage exists."""
    stage = find_kicad_loader_stage(cfg)
    if not stage:
        log.debug("No loader.kicad stage present; skipping job parse")
        return
    job_path = resolve_kicad_job_path(stage, cfg.source_path.parent if cfg.source_path else Path.cwd())
    if not job_path:
        log.warning("loader.kicad stage found but job path missing")
        return
    from kicad_job import load_kicad_job, KiCadJobError  # type: ignore
    log.debug("Parsing KiCad job file: %s", job_path)
    try:
        job = load_kicad_job(job_path)
    except KiCadJobError as e:
        log.error("Failed to parse job file: %s", e)
        return
    summarize_kicad_job(job, log, verbose=verbose)


def summarize_kicad_job(job: Any, log: logging.Logger, *, verbose: bool) -> None:
    """Emit a concise summary of board metrics, layers and (optionally) layer files."""
    log.info("KiCad Job Summary:")
    log.info(
        "  Board size: %s x %s mm  thickness=%s mm",
        job.board_size_x,
        job.board_size_y,
        job.board_thickness,
    )
    log.info(
        "  Copper layers: %d  Outline layer: %s",
        len(job.copper_layers()),
        "yes" if job.outline_layer() else "no",
    )
    if job.design_rules:
        dr = job.design_rules
        brief = ", ".join(
            f"{k}={v}" for k, v in list(dr.items())[:5] if isinstance(v, (int, float, str))
        )
        log.info("  Design rules (subset): %s", brief)
    if verbose:
        log.debug("  Layer files:")
        for lf in job.layers:
            flags = []
            if lf.is_copper:
                flags.append(f"Cu{lf.layer_index}")
            if lf.is_profile:
                flags.append("outline")
            if lf.side:
                flags.append(lf.side.lower())
            flag_str = ",".join(flags) if flags else "-"
            log.debug("    - %s (%s) polarity=%s", lf.path, flag_str, lf.polarity)


def find_kicad_loader_stage(cfg: Any) -> Optional[Any]:
    """Return the first stage whose 'uses' value is 'loader.kicad'."""
    for st in cfg.stages:
        if st.uses == "loader.kicad":
            return st
    return None


def resolve_kicad_job_path(stage: Any, base_dir: Path) -> Optional[Path]:
    """Resolve the job file path from stage inline parameters relative to base_dir."""
    raw = getattr(stage, "raw", {})
    job_name = raw.get("job") if isinstance(raw, dict) else None
    folder = raw.get("folder") if isinstance(raw, dict) else None
    if not job_name:
        return None
    job_path = Path(folder) / job_name if folder else Path(job_name)
    if not job_path.is_absolute():
        job_path = (base_dir / job_path).resolve()
    return job_path


__all__ = [
    "cli",
    "parse_args",
    "configure_logging",
    "load_pipeline_config",
    "list_declared_stages",
    "parse_kicad_job_if_present",
    "summarize_kicad_job",
]


def main():  # pragma: no cover
    return cli()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
