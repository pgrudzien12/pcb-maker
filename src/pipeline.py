"""Pipeline configuration loading for pcb-maker.

Currently supports the super-minimal inline pipeline format used in
`docs/examples/*-sample-pipeline.yaml`.

Example expected YAML structure (subset):

version: 0.2-min-inline
stages:
  - name: load
    uses: loader.kicad
    folder: ./path/
    job: board.gbrjob
    drills:
      - board-PTH.drl
  - name: isolation_routing
    uses: laser.isolation
    with:
      tool_diameter: 0.80
  - name: generate_gcode
    uses: output.laser_gcode
    with:
      file: build/out.nc

This module does not perform semantic validation of stage-specific
parameters yet; it ensures required top-level structure and provides
typed access to common fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml
import logging


@dataclass(slots=True)
class Stage:
    name: str
    uses: str
    raw: Dict[str, Any] = field(default_factory=dict)
    with_args: Dict[str, Any] = field(default_factory=dict)

    @property
    def namespace(self) -> str:
        return self.uses.split(".")[0] if "." in self.uses else self.uses

    @property
    def action(self) -> str:
        return self.uses.split(".", 1)[1] if "." in self.uses else ""


@dataclass(slots=True)
class PipelineConfig:
    version: str
    stages: List[Stage]
    source_path: Optional[Path] = None

    def find_stage(self, name: str) -> Optional[Stage]:
        for s in self.stages:
            if s.name == name:
                return s
        return None

    def stages_by_namespace(self, namespace: str) -> List[Stage]:
        return [s for s in self.stages if s.namespace == namespace]


class PipelineError(Exception):
    pass


class BaseStageImpl:
    """Base class for executable stage implementations.

    Contract:
      run(prev_output, context, log) -> new_output
    The context dict accumulates named artifacts (e.g. job, isolation_paths, etc.).
    prev_output is the value returned by the previous stage (None for first).
    """

    def __init__(self, cfg: Stage):
        self.cfg = cfg

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # pragma: no cover - interface
        raise NotImplementedError


class LoaderKiCadStage(BaseStageImpl):
    """Load KiCad .gbrjob metadata and store in context['job'].

    Accepts inline parameters either under raw or 'with'.
    Expected keys: folder, job.
    """

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        params = {**self.cfg.raw, **self.cfg.with_args}
        folder = params.get("folder") or params.get("with", {}).get("folder")
        job_name = params.get("job") or params.get("with", {}).get("job")
        if not job_name:
            raise PipelineError("loader.kicad stage requires 'job' path")
        job_path = Path(folder) / job_name if folder else Path(job_name)
        if not job_path.is_absolute() and self.cfg.raw.get("__pipeline_dir__"):
            job_path = (Path(self.cfg.raw["__pipeline_dir__"]) / job_path).resolve()
        try:
            from kicad_job import load_kicad_job  # type: ignore
        except ImportError as e:  # pragma: no cover - defensive
            raise PipelineError(f"kicad_job module unavailable: {e}") from e
        log.debug("[loader.kicad] loading job %s", job_path)
        job = load_kicad_job(job_path)
        context['job'] = job
        return job


class LaserIsolationStage(BaseStageImpl):
    """Placeholder laser isolation planner.

    Uses context['job'] if present. Produces a dict with placeholder geometry info.
    """

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        job = context.get('job')
        result = {
            'type': 'laser_isolation_paths',
            'source': 'job' if job else None,
            'paths': [],  # future list of polylines
        }
        context['laser_isolation'] = result
        return result


class LaserOutlineStage(BaseStageImpl):
    """Placeholder for laser outline scoring.

    Returns outline layer path if available in job metadata.
    """

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        job = context.get('job')
        outline = None
        if job and hasattr(job, 'outline_layer'):
            layer = job.outline_layer()
            outline = getattr(layer, 'path', None) if layer else None
        context['laser_outline'] = outline
        return outline


class LaserRasterStage(BaseStageImpl):
    """Placeholder for future raster mask ablation (currently returns disabled info)."""

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        data = {'type': 'laser_raster', 'enabled': self.cfg.with_args.get('enabled', False)}
        context['laser_raster'] = data
        return data


class MillingIsolationStage(BaseStageImpl):
    """Placeholder for milling isolation planning."""

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        result = {'type': 'milling_isolation', 'tool_diameter': self.cfg.with_args.get('tool_diameter')}
        context['milling_isolation'] = result
        return result


class MillingBoardCutoutStage(BaseStageImpl):
    """Placeholder for milling board cutout with tabs."""

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        result = {'type': 'milling_board_cutout', 'tabs': self.cfg.with_args.get('tabs')}
        context['milling_board_cutout'] = result
        return result


class OutputLaserGcodeStage(BaseStageImpl):
    """Placeholder laser G-code emitter (does not write files yet)."""

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        outfile = self.cfg.with_args.get('file')
        gcode = f"; laser gcode placeholder for {outfile}" if outfile else "; laser gcode placeholder"
        context['laser_gcode'] = gcode
        return gcode


class OutputCncGcodeStage(BaseStageImpl):
    """Placeholder CNC G-code emitter."""

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        outfile = self.cfg.with_args.get('file')
        gcode = f"; cnc gcode placeholder for {outfile}" if outfile else "; cnc gcode placeholder"
        context['cnc_gcode'] = gcode
        return gcode


STAGE_CLASS_REGISTRY: Dict[str, type[BaseStageImpl]] = {
    'loader.kicad': LoaderKiCadStage,
    'laser.isolation': LaserIsolationStage,
    'laser.outline': LaserOutlineStage,
    'laser.raster': LaserRasterStage,
    'milling.isolation': MillingIsolationStage,
    'milling.board_cutout': MillingBoardCutoutStage,
    'output.laser_gcode': OutputLaserGcodeStage,
    'output.cnc_gcode': OutputCncGcodeStage,
}


def create_stage_impl(stage: Stage) -> BaseStageImpl:
    """Factory method returning an instantiated stage implementation.

    Raises PipelineError if the 'uses' identifier is unknown.
    """
    cls = STAGE_CLASS_REGISTRY.get(stage.uses)
    if not cls:
        raise PipelineError(f"Unknown stage uses '{stage.uses}'")
    return cls(stage)


def execute_pipeline(cfg: PipelineConfig, log: Optional[logging.Logger] = None) -> Dict[str, Any]:
    """Execute all stages sequentially.

    Each stage receives the previous output plus a shared context dict.
    The context gains a key per logical artifact and 'last' referencing
    the most recent stage output. Returns the full context.
    """
    if log is None:  # pragma: no cover - convenience fallback
        log = logging.getLogger('pcb_maker')
    context: Dict[str, Any] = {'pipeline_version': cfg.version}
    # Provide pipeline directory to stage raw so relative resolution works.
    pipeline_dir = str(cfg.source_path.parent) if cfg.source_path else None
    prev_output: Any = None
    for st in cfg.stages:
        # annotate stage raw with pipeline dir for path resolution
        st.raw.setdefault('__pipeline_dir__', pipeline_dir)
        impl = create_stage_impl(st)
        log.debug("[pipeline] running stage %s (%s)", st.name, st.uses)
        prev_output = impl.run(prev_output, context, log)
        context['last'] = prev_output
    return context
def _coerce_stage(obj: Dict[str, Any]) -> Stage:
    if not isinstance(obj, dict):  # pragma: no cover - defensive
        raise PipelineError("Stage entry must be a mapping")
    name = obj.get("name")
    uses = obj.get("uses")
    if not name or not isinstance(name, str):
        raise PipelineError("Stage missing string 'name'")
    if not uses or not isinstance(uses, str):
        raise PipelineError(f"Stage '{name}' missing string 'uses'")
    with_args = obj.get("with")
    if with_args is None:
        with_args = {}
    elif not isinstance(with_args, dict):
        raise PipelineError(f"Stage '{name}' field 'with' must be a mapping if present")
    # Keep any unknown keys inside raw for future semantic validation.
    raw = dict(obj)
    return Stage(name=name, uses=uses, raw=raw, with_args=with_args)


def load_pipeline(path: Path) -> PipelineConfig:
    """Load pipeline YAML from path.

    Raises PipelineError on structural issues.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as e:  # pragma: no cover - filesystem issues
        raise PipelineError(f"Cannot read pipeline file: {e}") from e
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise PipelineError(f"YAML parse error: {e}") from e
    if not isinstance(data, dict):
        raise PipelineError("Pipeline root must be a mapping")
    version = data.get("version", "")
    if not version:
        raise PipelineError("Pipeline missing 'version'")
    stages_raw = data.get("stages")
    if not isinstance(stages_raw, list) or not stages_raw:
        raise PipelineError("Pipeline 'stages' must be a non-empty list")
    stages: List[Stage] = []
    for entry in stages_raw:
        stages.append(_coerce_stage(entry))
    return PipelineConfig(version=version, stages=stages, source_path=path)


def load_pipeline_from_string(text: str) -> PipelineConfig:
    tmp_path = Path("<string>")
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        raise PipelineError(f"YAML parse error: {e}") from e
    if not isinstance(data, dict):
        raise PipelineError("Pipeline root must be a mapping")
    version = data.get("version", "")
    if not version:
        raise PipelineError("Pipeline missing 'version'")
    stages_raw = data.get("stages")
    if not isinstance(stages_raw, list) or not stages_raw:
        raise PipelineError("Pipeline 'stages' must be a non-empty list")
    stages: List[Stage] = []
    for entry in stages_raw:
        stages.append(_coerce_stage(entry))
    return PipelineConfig(version=version, stages=stages, source_path=tmp_path)


__all__ = [
    "Stage",
    "PipelineConfig",
    "PipelineError",
    "load_pipeline",
    "load_pipeline_from_string",
    "create_stage_impl",
    "execute_pipeline",
]
