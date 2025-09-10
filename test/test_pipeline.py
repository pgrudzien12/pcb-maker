import pytest
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pipeline import load_pipeline_from_string, PipelineError, load_pipeline  # noqa: E402

def _load_kicad_job_module():
    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    try:
        import kicad_job as module  # type: ignore
        return module
    except ModuleNotFoundError:
        src_dir = ROOT / 'src'
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        import kicad_job as module  # type: ignore
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

