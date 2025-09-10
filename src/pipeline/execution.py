"""Pipeline execution engine.

Sequentially instantiates and runs stage implementations.
"""

from __future__ import annotations

from typing import Any, Dict, Optional
import logging

from .config import PipelineConfig, Stage, PipelineError
from .stages import STAGE_CLASS_REGISTRY, BaseStageImpl


def create_stage_impl(stage: Stage) -> BaseStageImpl:
    cls = STAGE_CLASS_REGISTRY.get(stage.uses)
    if not cls:
        raise PipelineError(f"Unknown stage uses '{stage.uses}'")
    return cls(stage)


def execute_pipeline(cfg: PipelineConfig, log: Optional[logging.Logger] = None) -> Dict[str, Any]:
    if log is None:  # pragma: no cover
        log = logging.getLogger('pcb_maker')
    context: Dict[str, Any] = {'pipeline_version': cfg.version}
    pipeline_dir = str(cfg.source_path.parent) if cfg.source_path else None
    prev_output: Any = None
    for st in cfg.stages:
        st.raw.setdefault('__pipeline_dir__', pipeline_dir)
        impl = create_stage_impl(st)
        log.debug('[pipeline] running stage %s (%s)', st.name, st.uses)
        prev_output = impl.run(prev_output, context, log)
        context['last'] = prev_output
    return context

__all__ = [
    'create_stage_impl',
    'execute_pipeline',
]
