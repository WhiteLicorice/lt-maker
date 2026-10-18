# Engine notes

Loaded when working under `app/engine/`. Combat cleanup ordering lives in `combat/CLAUDE.md`.

## Codegen

`app/engine/codegen/source_generator.py::generate_all()` runs at startup (both entry points) when not a built release. It generates source files; **do not hand-edit generated files**, edit the inputs:

- `compile_item_system()` / `compile_skill_system()` (in `app/engine/component_system/`) copy `item_system_base.py` / `skill_system_base.py` and emit one dispatch function per entry in the `ITEM_HOOKS` / `SKILL_HOOKS` dict, producing `app/engine/item_system.py` and `app/engine/skill_system.py` (git-ignored).
- `generate_event_command_python_wrappers()` emits Python wrappers for event commands.

A new hook name needs an entry in `ITEM_HOOKS` / `SKILL_HOOKS`; a component method whose name isn't in that dict is never dispatched. After editing the dict or a base file, rerun `python -m app.engine.codegen.source_generator`. Regenerating with no source change does not touch the generated files: every generator writes through `codegen_utils.GeneratedSource`, which compares before writing. A plain `open(path, 'w')` empties the file first, and with tests running in several processes another one imported it empty.

## Component system

Items and skills are composed of **components**, not subclasses. A component (e.g. in `app/engine/item_components/formula_components.py`) declares `nid`, `tag`, an `expose` type for its editor field, and implements named **hook methods** like `damage_formula(unit, item)` or `on_hit(...)`. The codegen step collects all components and builds `item_system`/`skill_system` dispatch functions that fan a hook call out across whatever components an item/skill carries. To add a behavior: add a component class with the right hook method name, then regenerate. `item_component_access.py` / `skill_component_access.py` expose the catalogs.

Each hook method has a **resolution policy** controlling how multiple components' return values combine: `ALL_DEFAULT_FALSE` (any False → False; e.g., `is_weapon`), `UNIQUE` (last-defined wins; e.g., `damage_formula`), `NUMERIC_ACCUM` (sum all numerics; e.g., `modify_damage`), `UNION` (merge all returned sets; e.g., `target_icon`). The policy is the `HookInfo(args, ResolvePolicy.X)` value of the hook's entry in `ITEM_HOOKS` / `SKILL_HOOKS` (`app/engine/component_system/compile_*_system.py`) — pick the right one when adding a new hook.

A per-combat consumption (`one_loss_per_combat` and kin in `usable_components.py`) must apply in the `cleanup_combat` hook, not `end_combat` — see `combat/CLAUDE.md`.

## Save / restart system

`app/engine/save.py` keeps **two parallel slot listings**: `SAVE_SLOTS` (the Load Game menu) and `RESTART_SLOTS` (the Restart Level menu). They are different files — `-{N}.p` vs `-restart{N}.p` — so a save can appear in one menu but not the other. Restart files are **slot-keyed** and seeded only at new game (the lone `kind=='start'` save in `title_screen.build_new_game`); every later save in `save_io` just **copies the restart file forward** from the slot you loaded into (`old_slot`) to the slot you save into. There is no per-chapter 'start' save.

Gotcha: **"Test Chapter"** (editor → engine via `game_state.start_level()`) bypasses new game entirely — it writes no 'start' save and leaves `current_save_slot = None`. So a first in-session save (e.g. a base/prep save) has no restart file to carry forward; `save_io` falls back to seeding the restart from that save, which is *not* a pristine chapter start. Preload saves (also `kind=='start'` only) are likewise never produced in a Test Chapter session.

A save outlives the shape of the project that made it, since it refers to the DB by nid. Restore raises **`StaleSaveError`** (`app/engine/stale_save.py`) with a "no class with that nid was found in the database" style message when a save names a class, AI, weapon type (in a `ComponentType.WeaponType` item component) or tilemap the project no longer has — those used to crash later, far from the cause. Items and skills missing from the DB deliberately fall back to placeholders, and a missing overworld is skipped. `test_save_round_trip.py` covers both kinds.

## Aura system

An aura is a parent skill (carrying the Aura component) plus a shared **subskill** object that gets applied to every affected unit — one `SkillObject` instance, one uid, sitting in many units' skill lists at once. Affected units are tracked **only** by board bookkeeping (`game_board.known_auras` / `aura_grid`), never an explicit "who has my aura" list. `aura_funcs.py` is the whole system: `propagate_aura`/`release_aura` (source moves/leaves), `pull_auras` (a unit arrives), `repopulate_aura` (board rebuild on load).

Teardown must be **authoritative**, not board-derived. When a unit leaves the map it drops *all* its AURA-sourced skills (`aura_funcs.remove_all_auras`, called from `game.leave`) by walking its own skill list — a board-position lookup is fragile because `reset_aura` clears board state but not unit skill lists, so re-propagation / teardown ordering / save-load can desync the two and orphan a child skill. AURA `source_type` is non-removable and non-displaceable ([source_type.py](source_type.py)): removable only via its exact source uid (the live parent skill instance). Aura children are therefore **not serialized** (`UnitObject.save`/`restore` filter `SourceType.AURA`); they're re-derived from the live board after units arrive on load (`game.load_level` → `pull_auras`) so each child's source points at the current parent. Skip this and a game-over restart restores children with a stale parent uid → unremovable forever (the "permanent aura skill" bug).

## Caching (LTCache) — invalidate *after* mutating component state

`app/engine/utils/ltcache.py`: `@ltcached` wraps a function in `lru_cache` and clears that cache whenever a global "state" uuid changes; the uuid is bumped by `game.on_alter_game_state()`. The cache key is the function's **args** (a `SkillObject`/`UnitObject`, hashed by identity/uid) — it does **not** see a component's mutable internal state. Stateful conditional components (`CombatCondition._condition`, `Nihil._condition` in `skill_components/`) therefore "publish" their state to the cache by calling `game.on_alter_game_state()`. **Gotcha: invalidate *after* writing the state variable, not only before.** `skill_system.condition` is `@ltcached`, and evaluating a combat-condition string re-enters it (a condition referencing `item_system.weapon_type`/`weapon_triangle_override` routes through `item_override` → `condition`). So invalidating before setting `_condition` re-caches the **stale** value under the freshly-bumped state, and it sticks until some unrelated hook bumps state again — e.g. a Weapon-Triangle item-override silently failed to apply on the first hit and "course-corrected" mid-combat. `combat_calcs.compute_advantage` is also `@ltcached` and depends on item overrides, so it inherits the same staleness window.

## Fog of war / sight

Board vision is precomputed state in `game_board.fog_of_war_grids`, mutated **only** by `update_fow` / `change_sight_range` (driven by the `UpdateFogOfWar` action). `game_board.fow_vantage_point[unit.nid]` is the tile a unit "sees from". A unit's sight is `skill_system.sight_range(unit) + fog radius`, and `sight_range` is gated by component `condition`, so a terrain-conditional sight bonus changes with `unit.position`. **Gotcha: during a move preview the vantage stays at the unit's start tile — a unit must not reveal new vision until it Waits** (`Wait.do` → `UpdateFogOfWar` moves the vantage and applies full sight; cancelling instead reverses the move). `action.recalc_unit` (fired by the `@recalculate_unit` decorator on `AddSkill`/equip/terrain-status/etc.) must therefore only refresh sight when `unit.position == fow_vantage_point[unit.nid]`. Refreshing mid-move applies the conditional sight bonus at the *stale* vantage (revealing tiles from the start position) and — because it writes straight to the board rather than as a reversible action — that change survives cancelling the move.
