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
]
