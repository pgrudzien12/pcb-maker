# AI Assistant Instructions for pcb-maker

Purpose: Early-stage CLI prototype to turn KiCad fabrication outputs (.gbrjob + Gerber + drills) into laser isolation and CNC drilling G-code using a declarative YAML pipeline.

## Big Picture
- Core flow (planned): KiCad .gbrjob + drill files -> parse & normalize -> geometry ops (Shapely) -> toolpath planning -> G-code emit.
- Current implementation status: only configuration parsing & .gbrjob metadata extraction. No stage execution / geometry yet.
- Architecture intent: small, declarative stage list (YAML) with simple `uses` identifiers (e.g. `loader.kicad`, `laser.isolation`, `output.laser_gcode`). Stages will later dispatch to functions via a registry.

## Key Files
- source directory: `src/`
- `src/main.py`: CLI orchestration (arg parse, logging, pipeline load, optional KiCad job parse & summary). Keep functions small & intention-revealing.
- `docs/examples/*.yaml`: Canonical shape of minimal pipeline definitions (laser vs CNC variants). Use these for tests & documentation examples.
- `pyproject.toml`: Declares dependencies (pygerber, shapely, pyyaml, pytest). Entry point script: `pcb-maker` -> `main:cli`.

## Conventions & Patterns
- Pipeline YAML: inline parameters only, list under `stages:`; each stage has `name`, `uses`, optional `with` mapping. Additional top-level keys inside a stage (e.g. `folder`, `job`) are preserved in `Stage.raw` for future semantic validation.
- Stage naming: `namespace.action` in `uses`. First segment (`namespace`) will guide future dispatch.
- Logging: use `logging` (not prints). `--verbose` flag elevates to DEBUG.
- Dataclasses use `slots=True` for lightweight objects and predictable attributes.
- Tests (future expansion) should import via module names (`pipeline`, `kicad_job`) rather than relative package paths since project isn't packaged as a package directory yet.
- when opening new terminals, run `uv` to activate the virtual environment.
- use `uv` to maintain environment consistency.
- use 'pytest' to run tests.

## Dependency Notes
- `pygerber` will supply primitive geometry; convert to Shapely `LineString`/`Polygon` for offset/boolean operations.
- Keep versions pinned where determinism matters (already pinned: shapely, pyyaml, pytest). Avoid introducing large frameworks.

## Style & Quality
- Favor small pure functions; side effects (filesystem writes) will belong to output stages.
- When introducing new public functions, add a concise doctring explaining purpose + inputs/outputs.
- Use early returns for error handling; raise custom exceptions if expanding semantic validation.
- Update readme and docs with any new stages or parameters.