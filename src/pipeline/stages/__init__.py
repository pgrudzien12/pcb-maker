"""Stage implementation classes & registry (placeholder logic).

Each stage returns a lightweight artifact; real geometry / G-code logic will be
introduced incrementally.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Type
import logging

from ..config import Stage, PipelineError


class BaseStageImpl:
    """Base executable stage.

    run(prev_output, context, log) -> new_output
    """

    def __init__(self, cfg: Stage):
        self.cfg = cfg

    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # pragma: no cover - abstract
        raise NotImplementedError


class LoaderKiCadStage(BaseStageImpl):
    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        params = {**self.cfg.raw, **self.cfg.with_args}
        folder = params.get("folder") or params.get("with", {}).get("folder")
        job_name = params.get("job") or params.get("with", {}).get("job")
        if not job_name:
            raise PipelineError("loader.kicad stage requires 'job' path")
        job_path = Path(folder) / job_name if folder else Path(job_name)
        if not job_path.is_absolute() and self.cfg.raw.get("__pipeline_dir__"):
            job_path = (Path(self.cfg.raw["__pipeline_dir__"]) / job_path).resolve()
        from kicad_job import load_kicad_job  # type: ignore
        log.debug("[loader.kicad] loading job %s", job_path)
        job = load_kicad_job(job_path)
        context['job'] = job
        return job


class LaserIsolationStage(BaseStageImpl):
    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        job = context.get('job')
        result = {'type': 'laser_isolation_paths', 'source': 'job' if job else None, 'paths': []}
        context['laser_isolation'] = result
        return result


class LaserOutlineStage(BaseStageImpl):
    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        job = context.get('job')
        outline = None
        if job and hasattr(job, 'outline_layer'):
            layer = job.outline_layer()
            outline = getattr(layer, 'path', None) if layer else None
        context['laser_outline'] = outline
        return outline


class LaserRasterStage(BaseStageImpl):
    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        data = {'type': 'laser_raster', 'enabled': self.cfg.with_args.get('enabled', False)}
        context['laser_raster'] = data
        return data


class MillingIsolationStage(BaseStageImpl):
    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        result = {'type': 'milling_isolation', 'tool_diameter': self.cfg.with_args.get('tool_diameter')}
        context['milling_isolation'] = result
        return result


class MillingBoardCutoutStage(BaseStageImpl):
    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        result = {'type': 'milling_board_cutout', 'tabs': self.cfg.with_args.get('tabs')}
        context['milling_board_cutout'] = result
        return result


class OutputLaserGcodeStage(BaseStageImpl):
    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        outfile = self.cfg.with_args.get('file')
        gcode = f"; laser gcode placeholder for {outfile}" if outfile else "; laser gcode placeholder"
        context['laser_gcode'] = gcode
        return gcode


class OutputCncGcodeStage(BaseStageImpl):
    def run(self, prev_output: Any, context: Dict[str, Any], log: logging.Logger) -> Any:  # noqa: D401
        outfile = self.cfg.with_args.get('file')
        gcode = f"; cnc gcode placeholder for {outfile}" if outfile else "; cnc gcode placeholder"
        context['cnc_gcode'] = gcode
        return gcode


STAGE_CLASS_REGISTRY: Dict[str, Type[BaseStageImpl]] = {
    'loader.kicad': LoaderKiCadStage,
    'laser.isolation': LaserIsolationStage,
    'laser.outline': LaserOutlineStage,
    'laser.raster': LaserRasterStage,
    'milling.isolation': MillingIsolationStage,
    'milling.board_cutout': MillingBoardCutoutStage,
    'output.laser_gcode': OutputLaserGcodeStage,
    'output.cnc_gcode': OutputCncGcodeStage,
}

__all__ = [
    'BaseStageImpl',
    'STAGE_CLASS_REGISTRY',
]
