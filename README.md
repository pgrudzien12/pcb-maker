pcb-maker
=========

Prototype command-line tool to turn KiCad Gerber outputs (and drill / Excellon files) into a G-code toolpath for (initially) Snapmaker 2.0 Laser and CNC module experimentation. Parsing/validation uses [PyGerber](https://pypi.org/project/pygerber/).
Internally (planned): parse with PyGerber -> convert primitives (flashes, strokes, regions) into a normalized set of 2D geometries (polylines / polygons) represented by [Shapely](https://shapely.readthedocs.io/) for robust offsetting, unions, buffering and later SVG / G-code emission.

Vision: KiCad Gerber Job (.gbrjob) + Laser-First Pipeline
--------------------------------------------------------
Initial milestone: fast laser-based copper isolation marking (spot-trace offsets + optional outline scoring) driven by a tiny YAML pipeline. Second milestone: add CNC drilling stage to produce hole drilling G-code for PTH/NPTH from KiCad drill files. Broader CNC milling (isolation via end mill, board cutout tabs, multi-depth) follows later.

Early scope centers on artifacts KiCad already produces (.gbrjob + drill files) and two focused outputs:
1. Laser isolation G-code (mark / ablate copper boundaries)
2. CNC drill G-code (hole drilling only)

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

Focused Near-Term Roadmap (laser isolation + drills)
---------------------------------------------------
1. YAML loader + minimal schema (no variable expansion initially)
2. `.gbrjob` parse: extract copper layers + outline candidate
3. Drill file parse: aggregate holes (size, plated vs non-plated if detectable)
4. Laser isolation v1: outline-follow with spot diameter compensation + single pass
5. Laser G-code emitter (`output.laser_gcode`) with power scaling + safe preamble
6. Add optional extra offset ring(s) for isolation clearance
7. CNC drilling stage: generate drill peck or simple plunge sequence (feed, retract height)
8. Basic tests: job parse, drill parse, isolation offset, laser G-code header/footer
9. CLI `--pipeline` execution path
10. SVG preview for isolation (debug)
11. (Stretch) Laser outline scoring vs full cut differentiation

Stage Names (immediate focus)
-----------------------------
- `loader.kicad` load job + (optionally) drills
- `laser.isolation` compute laser isolation paths (spot-compensated)
- `cnc.drill_holes` generate drilling toolpath from hole list
- `output.laser_gcode` emit laser job
- `output.cnc_drill_gcode` emit drill-only job (later may merge)

Deferred (later phases):
- `milling.isolation` end-mill isolation
- `milling.board_cutout` outline with tabs
- `output.cnc_gcode` combined milling program

Design Considerations / Open Questions
--------------------------------------
- Geometry pipeline: PyGerber model -> Shapely geometries (LineString, Polygon, MultiPolygon) enabling:
	* Spot/tool diameter compensation via buffer + difference operations
	* Boolean ops for isolation gap expansion
	* Simplification / densification strategies (preserve small features)
	* Area / length metrics for progress & optimization heuristics
- Config layering: allow CLI overrides of YAML (precedence rules)?
- Schema validation: pydantic vs. jsonschema vs. handwritten?
- Determinism: require sorted inputs + explicit random seeds for heuristics
- Coordinate precision & unit scaling: central utility vs stage-local logic
- Performance: incremental parse caching vs. reparsing each run
- Extensibility: plugin namespace entry points (`pcb_maker.stage_plugins`)

Contributing
------------
Starter contribution ideas (current focus):
- `.gbrjob` parser returning dataclass (layers, outline polyline if present)
- Drill parser (aggregate holes; detect plating via header or filename heuristic)
- Laser isolation path generator (outline-follow + optional extra rings)
- Laser G-code emitter (M3 S, safe travel, power normalization 0–100%)
- Spot compensation utility (offset geometry by half spot diameter)
- Unit tests for isolation offset geometry & drill grouping
- YAML loader & lightweight validation (early fail on unknown keys)

Development tips:
- Keep a tiny KiCad test project in `testdata/` with: one copper layer + edge cuts + drills
- Add golden SVG fixtures for isolation preview
- Create sample laser vs drill G-code golden headers to snapshot test

License
-------
MIT
