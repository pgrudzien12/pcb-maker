pcb-maker
=========

Prototype command-line tool to turn KiCad Gerber outputs (and drill / Excellon files) into a G-code toolpath for (initially) Snapmaker 2.0 Laser and CNC module experimentation. Parsing/validation uses [PyGerber](https://pypi.org/project/pygerber/).

Vision: KiCad Gerber Job (.gbrjob) + Minimal YAML Pipeline
---------------------------------------------------------
We are narrowing early scope to the artifacts KiCad already produces. KiCad can emit a single Gerber Job file (`.gbrjob`) describing all layers, plus separate drill (Excellon) files. A minimal YAML pipeline will reference that job file and a list of drill files, then declare parameters for:
1. Isolation routing (tool diameter, clearance, strategy, ordering)
2. Board cutout (tool, margin, tabs)
3. CNC emission (Z settings, multi-depth passes, feeds, spindle)

Status: The CLI today still only accepts a file/directory and emits naive G-code. Pipeline execution is not implemented yet; see `docs/examples/` for evolving draft pipeline YAMLs.

Why a pipeline?
- Reproducibility & versioning (store the YAML with your board design)
- Composability of future strategies (different isolation planners, ordering heuristics, multi-pass depth, drilling, engraving)
- Easier experimentation & automated benchmarks
- Deterministic artifact naming / caching potential

Current CLI (Prototype)
-----------------------
Installation (local dev):

```
uv pip install -e .
```

Usage examples (pipeline-only draft):

```
pcb-maker --pipeline docs/examples/cnc-sample-pipeline.yaml
pcb-maker --pipeline docs/examples/laser-sample-pipeline.yaml
```

Output
------
Generates a simplistic single-path G-code file (Snapmaker-flavored but mostly generic metric G-code) plus optional SVG of the path or isolation hull.

Focused Near-Term Roadmap (KiCad first)
--------------------------------------
1. Implement YAML loader + simple variable expansion (`${paths.job_file}`)
2. Parse `.gbrjob` to extract layer metadata (copper, mask, outline)
3. Load drill files (merge PTH/NPTH, produce hole list)
4. Isolation router v1: follow copper outline offsets using tool_diameter + clearance
5. Board outline extraction from job (fallback: detect `Edge.Cuts` layer)
6. Cutout path with margin + tab insertion
7. Multi-depth G-code emission (passes until reaching final cut_z or board thickness parameter)
8. Basic unit tests (job parse, isolation offset, tab placement)
9. CLI `--pipeline` flag to run this flow
10. Optional SVG emission for isolation + cutout debug

Stage Names (current minimal draft)
----------------------------------
- `loader.kicad` load job + drills in one step
- `milling.isolation` compute isolation toolpaths
- `milling.board_cutout` compute outline + tabs
- `output.cnc_gcode` merge toolpaths into final G-code

Design Considerations / Open Questions
--------------------------------------
- Config layering: allow CLI overrides of YAML (precedence rules)?
- Schema validation: pydantic vs. jsonschema vs. handwritten?
- Determinism: require sorted inputs + explicit random seeds for heuristics
- Coordinate precision & unit scaling: central utility vs stage-local logic
- Performance: incremental parse caching vs. reparsing each run
- Extensibility: plugin namespace entry points (`pcb_maker.stage_plugins`)

Contributing
------------
Starter contribution ideas (KiCad scope):
- Implement `.gbrjob` parser returning dataclass with layers + outline candidate
- Drill file parser that infers hole sizes & plating from filename or header
- Isolation path generator (outline offset only) using PyGerber polygon data
- Board cutout generator with evenly spaced tab placement logic
- Multi-depth pass planner producing Z step list from target depth & pass_depth
- YAML loader + validation (pydantic or lightweight schema function)

Development tips:
- Keep a tiny KiCad test project in `testdata/` with copper + edge cuts + drills
- Add golden SVG fixtures to visually diff isolation changes
- Gate changes with a path length + segment count test (regression guard)

License
-------
MIT
