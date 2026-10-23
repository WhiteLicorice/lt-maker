# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**Lex Talionis** is a Fire Emblem fangame engine (pygame runtime) plus **LT-maker**, a PyQt5 graphical editor built on top of it. A game is a `.ltproj` directory of JSON data + resources; the engine loads one and plays it, the editor mutates one. The sample project `default.ltproj` (Sacred Stones) ships in-repo.

## Commands

- Run the editor: `python run_editor.py`
- Run the engine on a project: `python run_engine.py` (auto-finds a `*.ltproj` in the repo root)
- Run the map maker: `python run_map_maker.py`
- Run all tests: `python utilities/build_tools/run_tests_parallel.py` — every test module, spread over 8 processes (about 30s, against a few minutes serially). Arguments filter by module name (`run_tests_parallel.py save combat`), `-j N` sets the process count, `--slowest N` lists the slow modules. Only failing modules print their output.
- Run all tests serially: `python -m unittest discover -s app/tests -p 'test*.py'` (wrapper: `./utilities/build_tools/run_tests.sh`)
- Run one test module: `python -m unittest app.tests.test_engine`
- Build docs: `./docs/make.bat html` (output in `_build/html`)
- Install dev deps: `pip install -r requirements_dev.txt` (engine-only: `requirements_engine.txt`, editor: `requirements_editor.txt`, CI tests: `requirements_test.txt`). Python 3.12 + PyQt5 + pygame-ce 2.5, the same Python and pygame-ce the browser build runs.
- Build the browser version: `python utilities/build_tools/build_web.py [project.ltproj] [--zip]`, the same build as the editor's File > Export for Web (`app/utilities/web_export.py`; no pygbag needed, it fills in a vendored copy of pygbag's page, `app/web/pygbag_default.tmpl`). Output in `build/web/<project>/`; `utilities/build_tools/web/serve.py` serves it to a phone on the local network. The page's own files (`main.py`, `page.js`) live in `app/web/`, so a release editor ships them.

`LT_PROFILE=1` env var enables per-frame timing prints in `driver.py`; `LT_PROFILE_THRESHOLD=<ms>` only prints slow frames. `LT_FRAME_STATS=1` prints a summary (`LTPERF`) every 120 frames instead.

The browser build (`sys.platform == 'emscripten'`) cannot start threads (`app/utilities/threads.py` runs work in place there), opens deferred music, sounds and battle sheets through `app/engine/deferred_files.ensure`, and runs the main loop one frame per call (`driver.MainLoop.run_frame`, paced by `run_async`).

## Codegen

`app/engine/item_system.py`, `app/engine/skill_system.py` and the event command Python wrappers are **generated** (`app/engine/codegen/source_generator.py`) — never hand-edit them; edit the inputs and rerun `python -m app.engine.codegen.source_generator`. Details in `app/engine/CLAUDE.md`.

## Architecture

Three top-level halves under `app/`:

- **`app/engine/`** — the runtime game (pygame). Entry: `driver.start()` then `driver.run(game)`, a fixed loop pulling input → `game.state.update()` → blit. The whole game is a singleton `GameState` (`game_state.py`) holding every registry (units, items, skills, regions, parties, teams, vars). Control flow is a **stack-based state machine** (`state_machine.py`, `state.py`); states are registered by string nid in `StateMachine.load_states` and pushed/popped (`game.state.change/back`). Combat lives in `app/engine/combat/` driven by a `solver` producing a `playback` log that map/animation combat replay. Live game objects are in `app/engine/objects/` (UnitObject, ItemObject, SkillObject, etc.) — these wrap the static DB prefabs with per-playthrough state.

- **`app/data/`** — the project data model and (de)serialization. Two global singletons: `DB` (`app/data/database/database.py`) for game design data and `RESOURCES` (`app/data/resources/resources.py`) for assets. Both `.load(path, version)` a `.ltproj`. On-disk format is versioned JSON; migration logic is in `app/data/serialization/` (`versions.py`, `migrators/`, `loaders/`). `CURRENT_SERIALIZATION_VERSION` gates load behavior. Validation in `app/data/validation/`; a project with `has_fatal_errors` refuses to launch.

- **`app/editor/`** — PyQt5 editor. One sub-package per data type (e.g. `item_editor/`, `class_editor/`, `event_editor/`), each typically a `*_tab.py` (Qt view), `*_model.py` (Qt model over the DB), and `*_properties.py` (the edit form). `main_editor.py` is the window. Editor state lives in `app/editor/lib/state_editor/`. The editor edits `DB`/`RESOURCES` in memory and serializes back to the `.ltproj`.

Also: **`app/events/`** — the eventing/scripting system, including a custom Python-eventing compiler under `app/events/python_eventing/` (analyzer → compiler → postcomp) that turns user event scripts into runnable code. Event triggers are defined in `app/events/triggers.py` (chapter start/end, unit death, talk, level up, etc.) and matched against `EventPrefab.triggers` at runtime. **`app/map_maker/`** — a separate procedural tile-map tool, with its own palette pipeline (see `app/map_maker/README.md`). **`app/engine/roam/`** — a free-roam exploration mode (town menus, NPC interactions) that runs as its own state machine alongside but separate from tactical map states; **`app/engine/overworld/`** — the node-based overworld graph (map selection, cinematics, route branching).

Subsystem notes live next to the code — read the relevant one before changing that area:

- `app/engine/CLAUDE.md` — codegen, component system and hook resolution policies, save/restart slots and `StaleSaveError`, auras, LTCache invalidation, fog of war / sight
- `app/engine/combat/CLAUDE.md` — combat cleanup phase ordering (`cleanup_combat` vs `end_combat`)
- `app/tests/CLAUDE.md` — `EngineTestCase` / `EngineHarness`, global-state and sprite leaks between tests, headless Qt

## Conventions

- Objects are referenced by string ids: **NID** (named id, design-time, stable across a project) and **UID** (unique id, runtime instance). Types in `app/utilities/typing.py`.
- Shared, framework-agnostic helpers live in `app/utilities/` (no Qt, no pygame deps) — prefer reusing `utils.py`, `str_utils.py`, `static_random.py` (deterministic RNG for turnwheel/replays) over rolling your own.
- The engine must stay importable without PyQt5 (it ships as a standalone executable); keep editor-only imports out of `app/engine`.
- A MAJOR_FEATURES DB constant (e.g. `support`, `fatigue`) is usually **not** the runtime gate — it enables the feature in the editor/UI. The actual runtime switch is a `_`-prefixed game var (`_supports`, `_fatigue`, `_convoy`, `_turnwheel`) set via an event command (e.g. `game_var;_supports;True`), often deliberately deferred to a story beat. When gating engine behavior on a feature, check the game var, and check it in **every** path (combat, info menu, accumulation, etc.) — a missing check in one path leaks the feature inconsistently.
- Tests live in `app/tests/`, mostly engine/data/event coverage (the editor is largely untested). **Tests cover engine and editor code only, never a particular game's content or rules** — a game's own events and data are checked by hand or a throwaway script, not in this suite. The full suite takes minutes: while iterating, run only the test modules for what changed (`python utilities/build_tools/run_tests_parallel.py test_x test_y`) and run everything once before a commit. Several tests load the sample `.ltproj`s, so don't break their data integrity (`test_base_project_integrity.py`). Read `app/tests/CLAUDE.md` before writing a test or a headless engine/editor script.
