"""Public pipeline package API (config + execution)."""

from .config import (
    Stage,
    PipelineConfig,
    PipelineError,
    load_pipeline,
    load_pipeline_from_string,
)
from .execution import create_stage_impl, execute_pipeline

__all__ = [
    'Stage',
    'PipelineConfig',
    'PipelineError',
    'load_pipeline',
    'load_pipeline_from_string',
    'create_stage_impl',
    'execute_pipeline',
]
