"""KiCad Gerber Job (.gbrjob) parsing utilities.

Parses the JSON job file emitted by KiCad fabrication output to extract:
  - General specs (board size, thickness, layer count)
  - Design rules (first ruleset for now)
  - File / layer attributes (copper layers, profile outline, masks, etc.)

The aim is to provide structured data for subsequent pipeline stages to decide
which Gerber layer files to load for isolation / drilling / outline detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import json


@dataclass(slots=True)
class LayerFile:
    path: str
    functions: List[str]
    polarity: Optional[str] = None
    layer_index: Optional[int] = None  # copper layer index (1-based) if applicable
    side: Optional[str] = None  # 'Top' | 'Bot' | None
    is_copper: bool = False
    is_profile: bool = False


@dataclass(slots=True)
class KiCadJob:
    source_path: Path
    board_size_x: float
    board_size_y: float
    board_thickness: Optional[float]
    layer_number: Optional[int]
    design_rules: Dict[str, Any] = field(default_factory=dict)
    layers: List[LayerFile] = field(default_factory=list)

    def copper_layers(self) -> List[LayerFile]:
        return [l for l in self.layers if l.is_copper]

    def outline_layer(self) -> Optional[LayerFile]:
        for l in self.layers:
            if l.is_profile:
                return l
        return None

    def layer_by_index(self, idx: int) -> Optional[LayerFile]:
        for l in self.layers:
            if l.layer_index == idx:
                return l
        return None

    def summarize(self, log, *, verbose: bool = False) -> None:
        """Log a concise summary of this job (board metrics, layers).

        This centralizes CLI-friendly summarization so callers don't duplicate
        logging code.
        """
        log.info("KiCad Job Summary:")
        log.info(
            "  Board size: %s x %s mm  thickness=%s mm",
            self.board_size_x,
            self.board_size_y,
            self.board_thickness,
        )
        log.info(
            "  Copper layers: %d  Outline layer: %s",
            len(self.copper_layers()),
            "yes" if self.outline_layer() else "no",
        )
        if self.design_rules:
            dr = self.design_rules
            brief = ", ".join(
                f"{k}={v}" for k, v in list(dr.items())[:5] if isinstance(v, (int, float, str))
            )
            log.info("  Design rules (subset): %s", brief)
        if verbose:
            log.debug("  Layer files:")
            for lf in self.layers:
                flags = []
                if lf.is_copper:
                    flags.append(f"Cu{lf.layer_index}")
                if lf.is_profile:
                    flags.append("outline")
                if lf.side:
                    flags.append(lf.side.lower())
                flag_str = ",".join(flags) if flags else "-"
                log.debug("    - %s (%s) polarity=%s", lf.path, flag_str, lf.polarity)


class KiCadJobError(Exception):
    pass


def parse_file_function(func_str: str) -> Dict[str, Any]:
    parts = [p.strip() for p in func_str.split(",") if p.strip()]
    info: Dict[str, Any] = {"parts": parts}
    if not parts:
        return info
    if parts[0].lower() == "copper":
        # Expect something like Copper,L1,Top
        for p in parts[1:]:
            if p.upper().startswith("L") and p[1:].isdigit():
                info["layer_index"] = int(p[1:])
            elif p in ("Top", "Bot"):
                info["side"] = p
        info["type"] = "copper"
    elif parts[0].lower() == "profile":
        info["type"] = "profile"
    else:
        info["type"] = parts[0].lower()
    return info


def load_kicad_job(path: Path) -> KiCadJob:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except OSError as e:  # pragma: no cover - filesystem issues
        raise KiCadJobError(f"Cannot read job file: {e}") from e
    except json.JSONDecodeError as e:
        raise KiCadJobError(f"Invalid JSON: {e}") from e

    try:
        general = raw.get("GeneralSpecs", {})
        size = general.get("Size", {})
        board_size_x = float(size.get("X", 0.0))
        board_size_y = float(size.get("Y", 0.0))
        board_thickness = general.get("BoardThickness")
        layer_number = general.get("LayerNumber")
    except Exception as e:  # pragma: no cover - defensive
        raise KiCadJobError(f"Missing or malformed GeneralSpecs: {e}") from e

    design_rules_list = raw.get("DesignRules", [])
    design_rules: Dict[str, Any] = {}
    if isinstance(design_rules_list, list) and design_rules_list:
        # Use first ruleset for now
        first = design_rules_list[0]
        if isinstance(first, dict):
            design_rules = first

    files_attr = raw.get("FilesAttributes", [])
    layers: List[LayerFile] = []
    if not isinstance(files_attr, list):  # pragma: no cover - defensive
        raise KiCadJobError("FilesAttributes must be a list")
    for entry in files_attr:
        if not isinstance(entry, dict):
            continue
        fpath = entry.get("Path")
        ffunc = entry.get("FileFunction", "")
        pol = entry.get("FilePolarity")
        if not fpath or not ffunc:
            continue
        parsed = parse_file_function(ffunc)
        layer = LayerFile(
            path=fpath,
            functions=parsed.get("parts", []),
            polarity=pol,
            layer_index=parsed.get("layer_index"),
            side=parsed.get("side"),
            is_copper=parsed.get("type") == "copper",
            is_profile=parsed.get("type") == "profile",
        )
        layers.append(layer)

    return KiCadJob(
        source_path=path,
        board_size_x=board_size_x,
        board_size_y=board_size_y,
        board_thickness=board_thickness,
        layer_number=layer_number,
        design_rules=design_rules,
        layers=layers,
    )


def _resolve_job_path_from_stage(stage: object, base_dir: Path) -> Optional[Path]:
    """Resolve job Path from a stage object.

    Prefer the structured `with` mapping (exposed as `stage.with_args`).
    Fall back to the raw stage mapping for backward compatibility.
    """
    job_name = None
    folder = None

    # Prefer modern, coerced 'with' mapping where stage.with_args exists.
    with_args = getattr(stage, "with_args", None)
    if isinstance(with_args, dict):
        job_name = with_args.get("job")
        folder = with_args.get("folder")

    # Fall back to raw mapping if necessary (legacy support).
    if not job_name:
        raw = getattr(stage, "raw", {})
        if isinstance(raw, dict):
            job_name = raw.get("job")
            folder = raw.get("folder")

    if not job_name:
        return None

    job_path = Path(folder) / job_name if folder else Path(job_name)
    if not job_path.is_absolute():
        job_path = (base_dir / job_path).resolve()
    return job_path


def parse_kicad_job_if_present(cfg: object, base_dir: Path, log, *, verbose: bool = False):
    """If a loader.kicad stage exists in the pipeline config, parse and return the KiCad job.

    Returns KiCadJob or None. Logs lightweight messages and delegates summarization
    to KiCadJob.summarize.
    """
    # Find loader.kicad stage
    loader = None
    for st in getattr(cfg, 'stages', []):
        if getattr(st, 'uses', None) == 'loader.kicad':
            loader = st
            break
    if not loader:
        log.debug("No loader.kicad stage present; skipping job parse")
        return None
    job_path = _resolve_job_path_from_stage(loader, base_dir)
    if not job_path:
        log.warning("loader.kicad stage found but job path missing")
        return None
    try:
        job = load_kicad_job(job_path)
    except KiCadJobError as e:
        log.error("Failed to parse job file: %s", e)
        return None
    job.summarize(log, verbose=verbose)
    return job


__all__ = [
    "LayerFile",
    "KiCadJob",
    "KiCadJobError",
    "load_kicad_job",
    "parse_file_function",
]
