import pytest
from pathlib import Path
import importlib.util, sys

# Allow importing pipeline.py as a module when project root isn't on PYTHONPATH.
ROOT = Path(__file__).resolve().parent.parent
pipeline_path = ROOT / "pipeline.py"
if "pipeline" not in sys.modules:
    spec = importlib.util.spec_from_file_location("pipeline", pipeline_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["pipeline"] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
else:  # pragma: no cover - defensive
    module = sys.modules["pipeline"]

from pipeline import load_pipeline_from_string, PipelineError, load_pipeline  # type: ignore  # noqa: E402

def _load_kicad_job_module():
    import importlib.util
    job_path = ROOT / "kicad_job.py"
    if "kicad_job" in sys.modules:
        return sys.modules["kicad_job"]
    spec = importlib.util.spec_from_file_location("kicad_job", job_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules["kicad_job"] = module
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module

VALID_YAML = """
version: 0.2-min-inline
stages:
  - name: load
    uses: loader.kicad
    folder: ./test/hexapod/
    job: hexapod-job.gbrjob
  - name: isolation_routing
    uses: laser.isolation
    with:
      tool_diameter: 0.80
  - name: generate_gcode
    uses: output.laser_gcode
    with:
      file: build/out.nc
"""


def test_load_pipeline_from_string_ok():
    cfg = load_pipeline_from_string(VALID_YAML)
    assert cfg.version == "0.2-min-inline"
    assert len(cfg.stages) == 3
    iso = cfg.find_stage("isolation_routing")
    assert iso is not None
    assert iso.with_args["tool_diameter"] == 0.80
    assert iso.namespace == "laser"
    assert iso.action == "isolation"


def test_pipeline_missing_version():
    bad = "stages: []"  # missing version and empty stages
    with pytest.raises(PipelineError) as e:
        load_pipeline_from_string(bad)
    assert "missing 'version'" in str(e.value) or "Pipeline 'stages'" in str(e.value)


def test_pipeline_missing_stages():
    bad = "version: 1.0"  # no stages
    with pytest.raises(PipelineError) as e:
        load_pipeline_from_string(bad)
    assert "non-empty list" in str(e.value)


def test_stage_missing_uses():
    bad = """
version: 1.0
stages:
  - name: load
    folder: ./
"""
    with pytest.raises(PipelineError) as e:
        load_pipeline_from_string(bad)
    assert "missing string 'uses'" in str(e.value)


def test_stage_with_args_type_error():
    bad = """
version: 1.0
stages:
  - name: x
    uses: a.b
    with: 123
"""
    with pytest.raises(PipelineError) as e:
        load_pipeline_from_string(bad)
    assert "must be a mapping" in str(e.value)


def test_load_pipeline_file(tmp_path: Path):
    p = tmp_path / "pipe.yaml"
    p.write_text(VALID_YAML)
    cfg = load_pipeline(p)
    assert cfg.source_path == p
    assert [s.name for s in cfg.stages] == ["load", "isolation_routing", "generate_gcode"]


def test_kicad_job_parsing():
    m = _load_kicad_job_module()
    job_file = ROOT / "test" / "hexapod" / "hexapod-job.gbrjob"
    assert job_file.exists(), "Sample job file missing"
    job = m.load_kicad_job(job_file)
    assert job.board_size_x == 100.2
    assert job.board_size_y == 107.2
    assert job.board_thickness == 1.6
    # Expect at least copper + profile layers
    copper = job.copper_layers()
    assert len(copper) == 2
    outline = job.outline_layer()
    assert outline is not None
    # Copper layer indexes should be 1 and 2
    assert sorted(l.layer_index for l in copper) == [1, 2]
    # Design rules basic keys present
    assert "PadToPad" in job.design_rules

