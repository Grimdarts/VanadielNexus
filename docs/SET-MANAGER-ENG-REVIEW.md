# Set manager slice 1: engineering review

Status: REVIEWED with Jason, 2026-11-01 (gstack `/plan-eng-review`). Reviews issue
[#2](https://github.com/Grimdarts/VanadielNexus/issues/2) ("read every GearSwap set and show it like the
equipment menu") against the approved design `docs/SET-MANAGER-DESIGN.md` and wireframe
`docs/set-manager-wireframe.png`. Decision dec-4891397d (Approach A: no writes to a player's Lua) is not
reopened here.

This review checked the spec's claims against the code instead of re-reading the spec. It read
`vanadiel_nexus/__main__.py`, `ui/main_window.py`, `ui/context.py`, `ui/pages/base.py`, `core/wiki.py`,
`core/gear_guides.py`, `core/jobs.py`, `ui/pages/addons.py`, `VanadielNexus.spec`, `tools/check_frozen.py` and
both workflows. It also read GearSwap's `refresh.lua`, `user_functions.lua`, `equip_processing.lua`,
`helper_functions.lua` and `statics.lua`, Jason's 8 job files, `Nova-Common.lua`, the Mote libs, Windower's
`addons/libs` and `res/`. Two load-bearing claims were settled with live probes on Jason's PC.

Everything below amends #2. Where this doc and #2 disagree, this doc wins.

## 1. What the probes showed

| Probe | Result | Consequence |
|---|---|---|
| lupa.luajit21, count hook, JIT on | A 3e9-step `for` loop finished in 2.97 s with no hook call. `while true do end` ran until killed. | The hook alone guards nothing. `jit.off()` is required (#2 had this). |
| Same, `jit.off()` first | Stopped at 200M steps in 0.40-0.42 s. | 200M ≈ 0.4 s of interpreted Lua. |
| Loop compiled **before** arming, then `jit.off()` | Ran 14.5 s past the limit (hook bypassed). | `jit.off()` doesn't flush compiled traces. |
| Same, `jit.off(); jit.flush()` | Stopped at the limit in 0.41 s. | **Decision D4**: off + flush, armed first. |
| Onefile, windowed PyInstaller 6.22.3 exe (Python 3.14.6, lupa 2.8), spawn child imports `lupa.luajit21` | Works. LuaJIT 2.1, `bit` present, `sys.stdout is None` in the child, and Lua `print` doesn't crash. Round trip 0.81-0.94 s, with the main script importing PySide6 at top level. | Frozen spawn is viable. An explicit import is enough for PyInstaller to collect lupa; keep `hiddenimports` anyway. |
| `terminate()` on a spinning child | Exit code **-15**. Process count went 2 → 3 → 2, so no orphan. | **D5**: timeout message from a flag, not the exit code. |
| `os._exit(3)` in the child | Parent `recv()` raises EOFError, exit 3. | Crash path as specified. |
| Child sends 5 MB, parent calls `join(3)` first | Child still alive after 3 s (blocked in send). `recv()` then worked. | **D5**: poll → recv → join. |
| Stream `res/items.lua` (5.0 MB, 23,556 lines, 15,527 with `slots=`) | 0.02 s for a substring scan. | `item_res` parse cost is negligible. |

The probe scripts were scratch files and are not in the repo. Rebuild them from this table if needed.

## 2. Spec claims checked

| #2 claim | Verdict | Evidence |
|---|---|---|
| Job file names and order | ✅ | `refresh.lua:100-103`. A `user_file` (from `//gs load`) is tried first (`refresh.lua:97`); the app has none, which is fine. |
| Search dirs and per-file order | ✅ | `refresh.lua:700-729`. Base dirs are relative to `addons/GearSwap/` except #9 (`<windower>/addons/libs/`). |
| `user_env` keys | ❌ list wrong | `refresh.lua:114-147`. The key is `include_path`, not `user_include_path`. Missing: `set_language`, `show_swaps`, `debug_mode`, `move_spell_target`, `language`, `_addon`, `lua_base_path`, `set`, `list`, `queue`, `pack`, `functions`, `print`. `verify_equip` and `force_send` are not keys. **D9.** |
| `windower` in user_env | ⚠ | `user_functions.lua:418-423`: `user_windower` has `__index=windower`, so every `windower.*` call works in game. The spec stub only had four `ffxi` getters. **D2.** |
| `coroutine` | ⚠ | `user_functions.lua:420-422`: Windower's coroutine with `schedule`/`sleep`/`yield`. `resources/Mote_Nexus_Hook.lua:52` (shipped by this app) calls `coroutine.schedule` at load. **D2.** |
| `include` behaviour | ✅ | `user_functions.lua:300-333`. With `dest_table` it runs in `pcall` (errors are swallowed) and returns `dest`. |
| File body errors vs get_sets errors | ⚠ not distinguished | Body error: GearSwap raises and sets `sets=nil` (`refresh.lua:166-172`). get_sets error: caught by `user_pcall`, and `sets = user_env.sets` is kept (`refresh.lua:178-182`). **D3.** |
| `set_combine` slot-only merge | ✅ | `helper_functions.lua:304-330` via `unify_slots` (`:131`). Values are copied by reference, so `table_id` survives inheritance. |
| Slot aliases | ✅ | `statics.lua:156-182`. Lookups go through `user_key_filter`, so they are case-insensitive. |
| Item entry forms | ✅ | `equip_processing.lua:80-100`. |
| "`owned` = checks at `equip_processing.lua:136-140`" | ❌ citation | The wearability gate is `check_wearable`, `equip_processing.lua:36-49`: job, level, **race** and **superior level**. **D10.** |
| Designated bag names | ❌ | GearSwap: `bag_string_lookup[lower(nospace(name))]` from `res/bags.lua` (`statics.lua:45-48`, `helper_functions.lua:213`); bag 8 is `"Wardrobe"`. The snapshot says `"Wardrobe 1"` (79 rows). **D8.** |
| Jason's 8 job files load in the specified sandbox | ❌ | All 8 call `Nova.install()`. Its wrapped `get_sets` calls `Nova.refresh()` → `Nova.export_controls()` → `io.open(...,'w')` (`Nova-Common.lua:210,228`). SMN: `windower.ffxi.get_ability_recasts()` (`:197`) and `res.moon_phases` (`Someonesmall-SMN-lib.lua`). **D2.** |
| `sets.SavageBlade.index`, `sets.magicalpact` | ✅ | `Nova-BLU-sets.lua:471`, `Someonesmall-SMN-sets.lua:147`. |
| `ui/main_window.py:33` NAV | ✅ | Line 33-34. |
| `Page.on_shown()` for lazy first read | ✅ | `ui/pages/base.py:18`, called by `MainWindow.show_page` (`main_window.py:186`). |
| Live player/job | ✅ | `ctx.bridge.state` (`bridge/udp.py:38,220`). Used the same way in `guides.py:87`. |
| `QRunnable` + `QThreadPool` pattern | ✅ | `ui/pages/addons.py:22-32`. |
| `--startup-check` exists, `check_frozen` fails on it | ✅ | `__main__.py:15-50`, `tools/check_frozen.py:187-211`. Required pages are `{'gear','guides','g13'}`; add `'sets'` (**D6**). |
| `freeze_support()` "first" | ⚠ underspecified | `__main__.py:64-71`: `QApplication` → `--startup-check` → `_already_running()`. Placement inside `main()` would let a frozen child hit the single-instance socket. **D6.** |
| CI | ✅ | `tests.yml` and `release.yml` install `requirements.txt` and run the full suite on windows-latest. Adding lupa makes the 21 Lua tests run in CI (no longer skipped). |

## 3. Decisions (all made by Jason in this review)

| ID | Issue | Decision |
|---|---|---|
| D1 | Step 0 scope (13 files, 6 new modules) | Keep all of #2, built as **two commits** (section 6). |
| D2 | Raising stubs break all 8 jobs | **Fail soft + real res.** |
| D3 | get_sets errors | **Partial read + banner.** |
| D4 | Runaway guard | **`jit.off(); jit.flush()`, hook armed first.** |
| D5 | Parent wait order, exit -15 | **poll → recv → join**, with a timed-out flag. |
| D6 | `freeze_support` placement, Qt in the child | **Top of `if __name__ == "__main__"`, PySide6 imports moved into functions.** |
| D7 | Sandbox escape through `getfenv` / the string metatable | **Capture, then scrub the real globals.** |
| D8 | Wardrobe naming | **`bag_key()` + GearSwap's own bag names in snippets.** |
| D9 | `user_env` key list | **Constant copied from `refresh.lua:114-147`, plus a local drift check.** |
| D10 | Race and superior level | **Parse both, note them on the cell.** |
| D11 | DRY | **Reuse `gear_guides.identity`, shared `RANK_RE`/`PATH_RE`, `jobs.ALL_FFXI_JOBS`.** Amended by D18: Path is a real augment and is no longer dropped. |
| D12 | Backslash keys | **Backslash keys are odd paths too.** |
| D13 | 50 ms timing test | **Behaviour test in CI, wall-clock check local only.** |
| D14 | Missing tests | **Add all 8.** |
| D15 | Rapid job switching | **Single-flight, latest wins.** |
| D16 | TODO: race/superior level from the addon | **Added to section 12.** |
| D17 | Codex 1: real io/os still reachable via `package.loaded`, `include('io')` and C loaders | **Patch the real tables in place; Lua-only loader; no cpath.** |
| D18 | Codex 2: exact augment equality ≠ GearSwap matching | **`equip_match` mirrors `extdata.compare_augments`: subset, GearSwap's strip, Rare bypass, Path kept.** |
| D19 | Codex 3: the addon's "Rank N" would land in `augments=` | **Strip "Rank N" in snippets; every snippet self-checks with `equip_match`.** |
| D20 | Codex 4: greedy passes can falsely leave a slot missing | **Maximum matching (Kuhn) with preference order.** |
| D21 | Codex 5: combine history can blame the wrong set | **Provenance counts only when the recorded values still match on both sides.** |
| D22 | Codex 6: find_line guesses, including in commented code | **Comments stripped; verified-unique or "Location ambiguous" with candidates.** |
| D23 | Codex 7: wiki wrapper drops non-equipment names (regression) | **One all-rows parser in item_res; `items()` filters it; full_names unchanged in behaviour.** |
| D24 | Codex 8: tie rule makes the Ifrit alias canonical | **Bare alias assignment lines are never canonical while another path exists.** |

## 4. Locked architecture

### 4.1 Data flow (amends the #2 diagram)

```
UI thread: SetsPage                     QThreadPool: _ReadTask (one at a time, D15)          child (spawn)
─────────────────────                   ───────────────────────────────────────────          ─────────────
on_shown (first) / combo change
  request(key, gen) ──► busy? pending = (key, gen)        (latest wins)
                        idle? start ─► read_job(win, char, job, sub, force)
                                         find_job_file ─ none ─► JobRead(error="No GearSwap file", searched)
                                         cache valid? ── yes ──► JobRead (≤0.2 s)
                                         spawn Process(gs_worker.main, Pipe) ───────────────► freeze_support →
                                         deadline = now + timeout (10 s)                       gs_worker.main(args)
                                         conn.poll(remaining) ◄── JSON-able result ───────────  lupa.luajit21 +
                                           ├ data ─► recv() ─► join(2) ─► JobRead               gs_sandbox.lua
                                           ├ EOF, exit≠0 ─► "stopped unexpectedly (exit N)"
                                           ├ EOF, exit=0 ─► "closed without an answer"
                                           └ timeout ─► terminate(), join ─► "took too long (over 10 s)"
                                         cache store (also for superseded results)
  ◄── done(gen, JobRead) ─── draw only if gen == latest; then start pending, if any
set_manager(JobRead, ctx.all_inventory(), item_res) ─► view model ─► tree / EquipGrid / panel
inventory_changed ─► recompute set_manager only (no Lua)
windower_changed  ─► clear reader + item_res caches, re-request
```

### 4.2 Sandbox boot order (gs_sandbox.lua): D2, D4, D7

```
1. jit.off(); jit.flush(); debug.sethook(count guard, "", 1000)   -- before anything else (D4 probe)
2. capture locals: sethook, traceback, loadstring, setfenv, getfenv, string.dump, io.open, debug.setmetatable
3. package.loaded stubs: resources (lazy real res), extdata, texts, images, packets, socket, logger,
   config, files (read-only), mime. luau and json require these.
4. load the real Windower libs (tables sets lists strings functions maths queues json chat luau)
   through py_read_source + the loadstring wrapper. strings/functions/maths call debug.setmetatable
   at load, so this step must come BEFORE the scrub.
5. scrub the real globals (D7, D17): patch the REAL io, os, string and debug tables IN PLACE (so globals,
   package.loaded.io/os/string/debug, include('io'), require and getfenv all see the safe functions);
   python = nil; package.loadlib, dofile, loadfile, load (non-string), real loadstring → denied/wrapper;
   package.loaders = { one Lua-only loader via py_read_source }, package.cpath = '';
   package.loaded/preload ffi, jit, debug cleared.
6. build user_env from GEARSWAP_USER_ENV_KEYS (D9); _G = user_env
7. run the job file body (xpcall). Error → read error card (GearSwap also refuses the file).
8. call get_sets if it's a function (xpcall). Error → partial = true, error kept (D3).
9. walk `sets` → JSON-able result {sets, files, absent_deps, error, error_details, partial}
```

Fail-soft rules (D2). "Read-only disk" semantics:

| Call | Behaviour |
|---|---|
| `io.open(p, 'r'/'rb')` inside `allowed_roots` | Works via `py_read_source` (`read('*a')`, `lines()`, `close()`). |
| `io.open(p, 'r')` outside the roots | `nil, "<p>: not available in Vana'diel Nexus"`. |
| `io.open(p, 'w'/'a'/'+')` anywhere | `nil, "<p>: writing is not available in Vana'diel Nexus"`. No file is created. |
| `io.write`, `io.output`, `io.popen`, `os.execute`, `os.exit`, `os.remove`, `os.rename`, `os.tmpname`, `os.setlocale`, `dofile`, `loadfile`, `load(fn)`, `string.dump`, `package.loadlib`, `require('ffi'/'jit'/'debug')`, `newproxy`, bytecode `loadstring`, any `debug.*` | Raise `"<name> is not available in Vana'diel Nexus"`. |
| `windower.ffxi.<any get_*>` | Returns a safe table: `get_player` → the player stub; `get_info` → `{logged_in=true, moon_phase=0, moon=0, time=0, day=0, weather=0, zone=0, language='english'}`; others → `{}`. |
| `windower.*` other functions (`register_event`, `raw_register_event`, `send_command`, `add_to_chat`, `text.*`, `prim.*`, `file_exists`, `dir_exists`) | No-ops returning sensible values (`register_event` → incrementing id; `file_exists`/`dir_exists` → real checks inside the roots only). |
| `coroutine.schedule`, `coroutine.sleep` | No-ops. `coroutine.yield`/`wrap`/`create` stay real. |
| `resources.<name>` | Loads `<windower>/res/<name>.lua` on first access (read-only), wrapped as the real resources lib does (`T` tables with `:with`, `:type`, …). An unknown name gives an empty `T{}`. |

Criterion 14 changes: `io.open('x','w')` returns nil and no file appears. The other seven escape fixtures still
produce a read error naming the denied function.

### 4.3 Parent/child contract (gearswap_reader ↔ gs_worker): D5, D6

- `read_job(..., timeout=10.0)`. Tests pass a short timeout.
- The child entry is a module-level function in `core/gs_worker.py` (Qt-free).
- `__main__.py`:
  ```python
  if __name__ == "__main__":
      multiprocessing.freeze_support()   # before QApplication and the single-instance check (D6)
      sys.exit(main())
  ```
  PySide6 imports move from module top into `main()` and `startup_check()`, so the child loads only
  multiprocessing, gs_worker and lupa.
- Test-only hooks: `args['_test_crash']` → `os._exit(3)`; `args['_test_hang']` → `time.sleep(60)` before
  Lua. Only the reader tests set them.
- lupa missing (`ImportError` in the child) → result `error="Lua runtime missing (lupa)"`.
- `read_job` is only ever called from one `_ReadTask` at a time (D15), so the cache dict needs no lock.

### 4.4 Errors the page can show

| Situation | Page shows |
|---|---|
| No Windower folder / no `addons/GearSwap` / no job file | Centered card (as #2), with the `searched` list for "no job file". |
| Syntax error or job file body error | Card: "Couldn't read <file>: <first line>" + Details. |
| get_sets error | Sets as read + amber banner "Read with an error: <first line>. Some sets may be missing." + Details (D3). |
| Timeout / crash / no answer / lupa missing | Card with the message from 4.3. Other jobs still work. |
| Snapshot absent / empty | As #2. |

## 5. Module amendments

**`core/gearswap_files.py`.** As #2. `search_dirs` base dirs 1-5 are under `addons/GearSwap/`, 6-8 under
`%APPDATA%/Windower/GearSwap/`, and 9 is `<windower>/addons/libs/`.

**`core/gs_worker.py` + `resources/gs_sandbox.lua`.** Sections 4.2 and 4.3. `GEARSWAP_USER_ENV_KEYS` lives in
`gs_worker.py` (the sandbox builds the env from it; the test checks it). The values follow `refresh.lua:114-147`:
`include_path` sets the include path, `party` = `alliance[1]` = `{}`, `language='english'`,
`lua_base_path = <windower>/addons/GearSwap/`, `_addon = {name='GearSwap', version=…}`, and `print` is a no-op.
`dofile` stays denied; Nova's `pcall(dofile, …)` handles that.

**`core/gearswap_reader.py`.** `JobRead` gains `partial: bool = False`. Error classification as in 4.3/4.4.

**`core/item_res.py`.** One streaming parser reads every row of `res/items.lua` once: `id`, `en`, `enl`,
plus `slots`, `jobs`, `level`, `races`, `superior_level` and `flags` when present (D23). `items()` filters the
equipment rows from it; `wiki.full_names` builds from all rows, so its behaviour is unchanged.
**Regression test (required):** `tests/core/test_guide_catalog.py:80` stays unchanged and passes, and a new
case keeps a non-equipment shortened name (e.g. `Taru F. Screen`). `Item` gains `races`, `superior_level`
(D10) and `rare` (`flags & 0x8000`, D18). Adds `bags(windower_dir) -> dict[str, str]`, mapping
`bag_key → GearSwap name` from `res/bags.lua` (D8).

**`core/set_manager.py`.**
- `bag_key(name)`: lowercase, spaces removed, `wardrobe1` → `wardrobe`. Used for every bag comparison,
  `REACHABLE_BAGS` and designated bags. Reachable = keys `inventory`, `wardrobe`, `wardrobe2` … `wardrobe8` (D8).
- `fix_snippet` writes `bag="<GearSwap name>"` for the new copy: a Wardrobe 1 copy → `bag="Wardrobe"` (D8).
- `owned` detail notes "race-limited: check your race" when `races` isn't all-races (510 on Jason's res), and
  "needs superior level N" when `superior_level > 0`. The state stays `owned`. "What owned promises" cites
  `check_wearable`, `equip_processing.lua:36-49` (D10).
- `augment_key` uses `gear_guides.identity` per part and drops only the addon's synthetic "Rank N" part
  (`gear_guides.RANK_RE`, moved there from inside `equipment_status`, D11). Path parts stay (D18).
  `augment_key` only groups identical copies; it never decides a match.
- `equip_match(goal, copy_augs, rare)` mirrors `extdata.compare_augments` (`addons/libs/extdata.lua:2261+`):
  each part lowercased with everything except letters, digits, `-` and `,` removed; the goal must be a
  subset of the copy, with duplicates consumed; Rare items (res `flags & 0x8000`, `resources.lua:195`) always
  match, as `equip_processing.lua:158` does. Tests: subset, `+`/quotes stripped, Rare bypass, path-only item,
  duplicates (D18).
- `allocate` is a maximum bipartite matching (Kuhn's augmenting paths) between the set's slots and candidate
  copies. A copy is a candidate when the id fits, the bag (by `bag_key`) matches any designated bag, and
  `equip_match` passes. Candidates are tried in preference order: reachable first, then plain copies for
  pieces without augments, then by bag name. `kind`/`detail` are derived as in #2. Test: Codex's overlap case
  (ring1 augments X, ring2 X + `bag="Wardrobe"`, copies in Wardrobe and Wardrobe 2: both owned), plus #2's
  criterion 8 cases (D20).
- `fix_snippet` drops the leading "Rank N" from snapshot augments and keeps the rest, Path included. Every
  generated snippet must compile in lupa and its augments must `equip_match` its own source copy (D19).
- Provenance: `set_combine` records the value per slot at combine time. `inherited_from`/`origin_path` hold
  only if the derived set's current value and the source set's current value both rawequal the recorded one.
  Otherwise provenance is cleared and fixes target this set, never a bulk root fix. Tests: derived-mutation
  and source-mutation fixtures (D21).
- `find_line` strips comments (`--` to end of line, `--[[ … ]]` blocks) first. A location is verified only if
  exactly one candidate matches the set path, or, for a shared definition, exactly one table literal contains
  all the old augments. Otherwise the panel shows "Location ambiguous" with up to 5 candidate file:line
  entries, and the paste note becomes "search your file for <set path>". The "first hit in the main file"
  fallback is removed (D22).
- Canonical path: a path whose source line is a bare alias assignment (`<path> = sets…`, found with
  find_line's normalisation on comment-stripped text) is never canonical while another path exists; then
  most keys, then walk order. Criterion 4 becomes: SMN lists `sets.magicalpact` and
  `sets.midcast.Pet.IfritMagicalBloodPactRage` both as "same as sets.midcast.Pet.MagicalBloodPactRage".
  Fixture with all three paths (D24).
- `odd_path` is true for any key with a backslash, both quote types, or any control character, and for
  everything below it (D12).

**`ui/pages/sets.py`.**
- Single-flight `_ReadTask` with a latest-wins pending slot (D15).
- The job combos use `jobs.ALL_FFXI_JOBS` without `"All"` (D11).
- Construction does no I/O: combos are filled and the first read runs in `on_shown` (D13).
- Partial banner (D3).

**Packaging (D6).** `requirements.txt` `lupa==2.8`. `VanadielNexus.spec` `hiddenimports=['lupa.luajit21',
'vanadiel_nexus.core.gs_worker']`. The `--startup-check` spawn self-test runs `gs_worker` on a 3-line fixture
through real spawn, timed separately (≤5 s). `check_frozen.py` requires `'sets'` in pages and a passing spawn check.

**Criteria reworded.** 1 (timing → behaviour + local, D13); 4 (Ifrit alias also listed as "same as", D24);
8 (`bag="Wardrobe"` matches a Wardrobe 1 row, D8; the "augmented + plain copy" case uses subset matching,
D18); 10 (`augment_key` keeps Path parts, D18); 14 (`io.open('x','w')` returns nil, D2; plus
`include('io')`/`package.loaded` escapes, D17); 17 (spawn check inside the startup check, D6).

## 6. Build order (D1: two commits)

```
Commit 1  "Sets page: read every GearSwap set and show it in the 4×4 grid"
  1. item_res.py (+ races, superior_level, bags) and wiki.full_names wrapper      tests: item_res, wiki unchanged
  2. gearswap_files.py                                                            tests: gearswap_files
  3. gs_sandbox.lua + gs_worker.py (boot order 4.2, fail-soft, scrub, walk)       tests: sandbox in-process
  4. gearswap_reader.py (spawn contract 4.3, cache, partial)                      tests: reader (3 real-spawn)
  5. set_manager.py: bag_key, augment_key, resolve, allocate, classify            tests: set_manager (reading half)
  6. equip_grid.py, then sets.py (tree, grid, warnings, single-flight, banner)    tests: UI (read_job patched)
  7. __main__.py freeze_support + lazy Qt, requirements, spec, startup check      tests: frozen startup, check_frozen
  8. Local real-file pass on the 8 jobs; Jason runs criterion 5 in game
Commit 2  "Sets page: upgrade badges and copy-paste fixes"
  9. set_manager.py: tier_upgrades, lua_str, fix_snippet, fix_plan, find_line     tests: set_manager (fix half)
 10. sets.py right panel: Owned that fit, Copy fix, Copy all, Open file           tests: UI picker/clipboard
```

Committing `.py` triggers the post-commit rebuild, which restarts Jason's running app. Say so before each
commit. Run `py -3 -m pytest -q` before each.

## 7. Test coverage

Framework: pytest + pytest-qt (CLAUDE.md). The spec's count was +88 (#2 table, including local-only); this
review adds about +30, all tied to a decision above.

```
CODE PATHS                                                         USER FLOWS
[+] gs_sandbox.lua / gs_worker.run (in-process)                    [+] Open Sets page
  ├── [★★★ PLAN] fixtures from #2 (24)                               ├── [★★★ PLAN] construction does no I/O (D13)
  ├── [★★★ ADD]  Nova.install-style fixture loads, fs unchanged (D2) ├── [★★  PLAN] first show reads once (D13)
  ├── [★★★ ADD]  io.open w → nil, no file (D2)                       └── [★   LOCAL] 50 ms wall clock (local only)
  ├── [★★★ ADD]  ffxi.get_ability_recasts, coroutine.schedule,     [+] Browse jobs
  │              res.moon_phases work (D2)                            ├── [★★★ ADD] 5 quick changes → ≤2 reads,
  ├── [★★★ ADD]  get_sets error after 3 sets → 3 sets, partial (D3)   │             last drawn (D15)
  ├── [★★★ ADD]  syntax error → error, no sets (D3)                   ├── [★★  PLAN] stale result ignored (#2)
  ├── [★★★ ADD]  while-true + warm-trace both stop (D4)               └── [★★  PLAN] job with no file disabled
  ├── [★★★ ADD]  getfenv(0).io/os, getfenv(2) via include,         [+] Inspect a set
  │              ("").dump, getfenv(0).python (D7)                    ├── [★★  PLAN] grid fills, states render
  ├── [★★★ ADD]  each real-lib stand-in loads after stubs (4.2)       ├── [★★  ADD]  alias row → canonical (D14)
  └── [★★★ ADD]  env has every GEARSWAP_USER_ENV_KEYS key (D9)        ├── [★★  ADD]  search by piece name (D14)
[+] gearswap_reader                                                   └── [★★  PLAN] partial banner shown (D3)
  ├── [★★★ PLAN] cache hit / mtime / new file / res / force (#2)   [+] Fix a piece (commit 2)
  ├── [★★★ ADD]  >1 MB payload intact, real spawn (D5)                ├── [★★  PLAN] picker order, Copy fix
  ├── [★★★ ADD]  _test_hang → timeout message, not exit -15 (D5)      ├── [★★  ADD]  Copy all N fixes (D14)
  ├── [★★★ PLAN] _test_crash → exit 3 (#2)                            └── [★★  ADD]  Open file → startfile (D14)
  └── [★★  ADD]  windower change clears caches (D14)               [+] Data changes while open
[+] item_res                                                          ├── [★★  ADD]  inventory_changed recolours, no Lua (D14)
  ├── [★★★ PLAN] rows, slot bits, pairs, wearable, by_name            ├── [★★  ADD]  sets_character restored (D14)
  ├── [★★  ADD]  races + superior_level parsed (D10)                  └── [GAP→design] live job change while open
  ├── [★★  ADD]  bags() maps wardrobe1 → "Wardrobe" (D8)
  └── [★★  ADD]  items.lua mtime change invalidates (D14)          [+] Frozen exe
[+] set_manager                                                       ├── [★★★ PLAN] spawn check in --startup-check (D6)
  ├── [★★★ PLAN] allocation cases (#2 crit. 8, bag wording per D8)    └── [★★  PLAN] check_frozen requires 'sets' (D6)
  ├── [★★★ ADD]  bag_key: Wardrobe ≡ Wardrobe 1, wardrobe3 (D8)
  ├── [★★★ ADD]  snippet to a Wardrobe 1 copy → bag="Wardrobe" (D8)
  ├── [★★  ADD]  race-limited / SL3 → owned + note (D10)
  ├── [★★★ ADD]  odd_path: \, \n, both quotes; apostrophe not odd (D12)
  └── [★★★ PLAN] classify 28 paths, fix_plan, find_line (#2)
[+] Existing code touched
  ├── [★★★ REGRESSION] gear_guides tests unchanged after RANK_RE/PATH_RE move (D11)
  ├── [★★★ REGRESSION] wiki.full_names tests unchanged (#2)
  └── [★★  REGRESSION] __main__ lazy imports: test_frozen_startup + test_smoke still pass (D6)

Added after the Codex pass (all ★★★, PLAN):
  sandbox: include('io').open w → nil; package.loaded.os.remove raises; require('io') safe; no C loader (D17)
  set_manager: equip_match subset / strip / Rare / Path / duplicates (D18); snippet Rank strip + self-check
    (D19); overlap allocation case (D20); derived- and source-mutation provenance (D21); find_line comment,
    two-candidate and common-first-augment cases (D22); three-path canonical fixture (D24)
  item_res: [REGRESSION] existing full-name test unchanged + non-equipment shortened name kept (D23)

COVERAGE (planned): every path above has a test in the plan except one design question.
GAPS: 1 (live job change while the page is open → /plan-design-review). E2E: criterion 5 in game (manual).
```

UI tests patch `read_job` with canned `JobRead`s and never spawn Lua. Real spawn is limited to three reader
tests plus the frozen startup check.

## 8. Failure modes

| New path | Realistic failure | Test | Handling | User sees |
|---|---|---|---|---|
| Sandbox boot | A Windower lib update adds a load-time call to a scrubbed global | stand-in lib tests; local real-file test | xpcall → card | clear error |
| Fail-soft stubs | A player file writes with `assert(io.open(p,'w'))` | io.open-w fixture | assert raises → get_sets error → partial | banner, sets still listed |
| Count guard | A legit huge file needs >200M steps | local real-file timings | error "took too long" | clear error (raise the limit if it ever happens) |
| Pipe | Large result | >1 MB spawn test | poll → recv first | nothing |
| Timeout | Child hangs in C code (hook can't fire) | `_test_hang` test | terminate at 10 s | "took too long" |
| Frozen spawn | `freeze_support` misplaced by a later edit | startup spawn check | check_frozen fails the build | build fails, not players |
| Cache | Game update changes res; new higher-priority include | mtime + absent_deps tests | invalidation | fresh data |
| Bag | Snapshot naming differs from GearSwap | bag_key tests | normalisation | correct status |
| Single-flight | Result for an old job arrives late | generation test | not drawn | nothing |
| Item names | Lua uses a name not in res (typo) | resolve tests | `unknown` state | "not in game data" |

No critical gaps: every failure has a test or handling, and none is silent.

## 9. NOT in scope

- Everything #2 lists as out of scope (icons, Nexus sets, Equip now, rule cards, live view, the Gear-page grid issue).
- A persistent Lua worker process: per-read spawn measured 0.85 s frozen, and the cache makes re-reads ≤0.2 s.
- Killing an in-flight read when a newer request arrives (D15 chose single-flight without kills).
- Exact race/superior-level checks (TODO in section 12).
- Read-only `dofile` support: Nova's only use is `pcall`'d, and nothing needs it yet.

## 10. What already exists

| Need | Existing code | Plan |
|---|---|---|
| Casefold + whitespace identity | `gear_guides.identity` (`gear_guides.py:51`) | Reused (D11) |
| Rank/Path parsing | `gear_guides.equipment_status` (`:86-90`) | Moved to `RANK_RE`/`PATH_RE`, shared (D11); Set manager drops only Rank (D18) |
| GearSwap augment matching | `extdata.compare_augments` (Windower libs, Lua) | Mirrored in Python as `equip_match` (D18) |
| Job list | `jobs.ALL_FFXI_JOBS` (`jobs.py:3`) | Reused (D11) |
| items.lua line regex | `wiki.full_names` (`wiki.py:18-38`) | Becomes a wrapper over `item_res` (#2) |
| Background work | `QRunnable`/`QThreadPool` (`addons.py:22-32`) | Same pattern + single-flight |
| Lazy page work | `Page.on_shown` (`base.py:18`) | Used for the first read |
| Live player | `ctx.bridge.state` | Used for defaults |
| Search toolbar | `widgets.SearchToolbar` (`widgets.py:145`) | Reused (#2) |
| Frozen self-test | `--startup-check` + `check_frozen.py` | Extended (D6) |
| Lua test harness | `tests/test_inventory_lua.py` (lupa, `VN_LUA_RUNTIME`) | Same skip rules for new Lua tests |

## 11. Worktree parallelization

| Step | Modules touched | Depends on |
|---|---|---|
| A. item_res + wiki wrapper | core/ | — |
| B. gearswap_files | core/ | — |
| C. gs_worker + gs_sandbox.lua | core/, resources/ | B (paths) |
| D. gearswap_reader | core/ | B, C |
| E. set_manager | core/ | A |
| F. equip_grid | ui/ | — |
| G. sets page | ui/pages/ | D, E, F |
| H. packaging + `__main__` | root, tools/ | C |

- Lane 1: B → C → D → H (sandbox and process; the riskiest path).
- Lane 2: A → E (data and rules).
- Lane 3: F (widget, no GearSwap knowledge).
- Then G.

Lanes 1 and 2 both add files under `core/` but touch different files, so merge risk is low. `gear_guides.py`
(D11) is touched only by lane 2. In practice Jason works one session at a time, so sequential order
(section 6) is the default; the lanes are there if a parallel session is wanted.

## 12. TODOs

- **Race and superior level from the addon** (D16). Add `race_id` and `superior_level` to the addon's
  STATE_UPDATE, store them per character, and make `set_manager.wearable()` apply GearSwap's full
  `check_wearable` (`equip_processing.lua:36-49`). Why: D10 only notes race-limited/SL items on the cell.
  Start in `resources/VanadielNexus.lua` and `bridge/udp.py:198-224`. Depends on slice 1 (item_res fields).
  Effort: human ~4h / CC ~40 min. Needs an addon version bump and Jason's reload.

## 13. Questions for /plan-design-review

Resolved 2026-11-01 in `docs/SET-MANAGER-DESIGN-REVIEW.md`: following the live job → D12, banner and cell
notes → D7/D9, cell colours → D7. That doc also changes the cell size (D15: 112×128 × text scale) and the
page layout (D3), which affect the `ui/equip_grid.py` and `ui/pages/sets.py` amendments in section 5.

- Should the page follow a live job change while open (only if Jason hasn't picked a job by hand)? This is the one test gap.
- Look of the partial-read amber banner, and of the "race-limited" / "needs superior level N" cell notes.
- Final cell colours (#2 defers them to design review).

## Implementation Tasks

Synthesized from this review's findings. Each task derives from a specific finding above.

- [ ] **T1 (P1, human: ~4h / CC: ~30 min)**: gs_sandbox: fail-soft stubs + lazy real `resources`
  - Surfaced by: Architecture, D2 (Nova.install → `io.open(...,'w')` in all 8 jobs)
  - Files: `vanadiel_nexus/resources/gs_sandbox.lua`, `tests/core/test_gs_worker.py`, `tests/fixtures/gearswap/**`
  - Verify: Nova-style fixture loads with no error and the fs hash is unchanged; local 8-job test has no error card
- [ ] **T2 (P1, human: ~1h / CC: ~10 min)**: gs_sandbox/reader: partial read on get_sets error
  - Surfaced by: Architecture, D3 (`refresh.lua:166-182`)
  - Files: `gs_sandbox.lua`, `core/gearswap_reader.py`, `ui/pages/sets.py`
  - Verify: 3-sets-then-error fixture → 3 sets + `partial`; syntax-error fixture → card
- [ ] **T3 (P1, human: ~30 min / CC: ~5 min)**: gs_sandbox: `jit.off(); jit.flush()` + hook first
  - Surfaced by: Architecture, D4 (probe: 14.5 s bypass without flush)
  - Files: `gs_sandbox.lua`, `tests/core/test_gs_worker.py`
  - Verify: while-true and warm-trace tests stop with "took too long to load"
- [ ] **T4 (P1, human: ~1h / CC: ~10 min)**: gearswap_reader: poll → recv → join, timed-out flag
  - Surfaced by: Architecture, D5 (probe: join-first stuck on 5 MB; terminate → -15)
  - Files: `core/gearswap_reader.py`, `core/gs_worker.py`, `tests/core/test_gearswap_reader.py`
  - Verify: >1 MB payload, `_test_hang`, `_test_crash` tests
- [ ] **T5 (P1, human: ~30 min / CC: ~5 min)**: `__main__`: `freeze_support` at top, lazy PySide6 imports, spawn check
  - Surfaced by: Architecture, D6 (`__main__.py:64-71`)
  - Files: `vanadiel_nexus/__main__.py`, `tools/check_frozen.py`, `VanadielNexus.spec`, `requirements.txt`
  - Verify: `build.ps1` then `tools/check_frozen.py dist/VanadielNexus.exe`; `tests/core/test_frozen_startup.py`
- [ ] **T6 (P1, human: ~2h / CC: ~20 min)**: gs_sandbox: scrub real globals after the libs load
  - Surfaced by: Architecture, D7 (getfenv(0), getfenv(2) via include, string metatable)
  - Files: `gs_sandbox.lua`, `tests/core/test_gs_worker.py`
  - Verify: five escape tests
- [ ] **T7 (P1, human: ~1h / CC: ~10 min)**: set_manager/item_res: `bag_key()` + GearSwap bag names
  - Surfaced by: Code quality, D8 (`statics.lua:45-48`; snapshot "Wardrobe 1")
  - Files: `core/set_manager.py`, `core/item_res.py`, `tests/core/test_set_manager.py`
  - Verify: bag_key and snippet tests; criterion 8 reworded
- [ ] **T8 (P2, human: ~1h / CC: ~10 min)**: `GEARSWAP_USER_ENV_KEYS` from refresh.lua + drift check
  - Surfaced by: Code quality, D9
  - Files: `core/gs_worker.py`, `gs_sandbox.lua`, `tests/core/test_gs_worker.py`, `tests/test_gearswap_real_files.py`
  - Verify: env-keys test; local drift test against the installed refresh.lua
- [ ] **T9 (P2, human: ~45 min / CC: ~10 min)**: item_res races/superior_level + cell notes
  - Surfaced by: Code quality, D10 (`equip_processing.lua:36-49`)
  - Files: `core/item_res.py`, `core/set_manager.py`, tests
  - Verify: race-limited and SL3 fixtures
- [ ] **T10 (P2, human: ~30 min / CC: ~5 min)**: reuse `identity`, `RANK_RE`/`PATH_RE`, `ALL_FFXI_JOBS`
  - Surfaced by: Code quality, D11
  - Files: `core/gear_guides.py`, `core/set_manager.py`, `ui/pages/sets.py`
  - Verify: existing gear-guide tests unchanged and green
- [ ] **T11 (P2, human: ~15 min / CC: ~3 min)**: odd_path for backslash keys
  - Surfaced by: Code quality, D12 (`helper_functions.lua:380`, learning gs-parse-set-keys-quotes)
  - Files: `gs_sandbox.lua`, tests
  - Verify: odd_path tests
- [ ] **T12 (P2, human: ~30 min / CC: ~5 min)**: construction-does-no-I/O test; 50 ms check local only
  - Surfaced by: Tests, D13
  - Files: `tests/ui/test_sets_page.py`, `tests/test_gearswap_real_files.py`
  - Verify: tests pass on CI and locally
- [ ] **T13 (P2, human: ~3h / CC: ~20 min)**: the 8 missing tests
  - Surfaced by: Tests, D14
  - Files: `tests/ui/test_sets_page.py`, `tests/core/test_gearswap_reader.py`, `tests/core/test_item_res.py`, `tests/core/test_set_manager.py`
  - Verify: `py -3 -m pytest -q`
- [ ] **T14 (P2, human: ~1h / CC: ~10 min)**: SetsPage single-flight, latest wins
  - Surfaced by: Performance, D15
  - Files: `ui/pages/sets.py`, `tests/ui/test_sets_page.py`
  - Verify: 5-quick-changes test → ≤2 reads, last drawn

- [ ] **T15 (P1, human: ~1h / CC: ~10 min)**: gs_sandbox: patch real io/os/string/debug in place, Lua-only loader
  - Surfaced by: Outside voice, D17 (`user_functions.lua:306` returns `package.loaded[str]`)
  - Files: `gs_sandbox.lua`, `tests/core/test_gs_worker.py`
  - Verify: include('io'), package.loaded, require and loader tests
- [ ] **T16 (P1, human: ~2h / CC: ~15 min)**: set_manager: `equip_match` mirroring compare_augments, Rare flag
  - Surfaced by: Outside voice, D18 (`extdata.lua:2261+`, `equip_processing.lua:158`, `resources.lua:195`)
  - Files: `core/set_manager.py`, `core/item_res.py`, `core/gear_guides.py`, tests
  - Verify: subset/strip/Rare/Path/duplicate tests; criterion 5 in game
- [ ] **T17 (P2, human: ~30 min / CC: ~5 min)**: fix_snippet strips "Rank N"; snippet self-check
  - Surfaced by: Outside voice, D19 (`resources/VanadielNexus.lua:79-82`)
  - Files: `core/set_manager.py`, tests
  - Verify: ranked-row snippet test; every snippet compiles and equip_matches its source
- [ ] **T18 (P2, human: ~2h / CC: ~15 min)**: allocate as maximum matching
  - Surfaced by: Outside voice, D20
  - Files: `core/set_manager.py`, tests
  - Verify: overlap fixture + criterion 8 cases
- [ ] **T19 (P1, human: ~1h / CC: ~10 min)**: provenance verified by recorded values
  - Surfaced by: Outside voice, D21 (`helper_functions.lua:324`)
  - Files: `gs_sandbox.lua`, `core/set_manager.py`, tests
  - Verify: derived- and source-mutation fixtures; criterion 6
- [ ] **T20 (P2, human: ~1h / CC: ~10 min)**: find_line: strip comments; verified or ambiguous
  - Surfaced by: Outside voice, D22 (`Someonesmall-SMN-sets.lua:111-115`)
  - Files: `core/set_manager.py`, `ui/pages/sets.py`, tests
  - Verify: comment, two-candidate and common-augment tests
- [ ] **T21 (P1, human: ~45 min / CC: ~10 min)**: item_res all-rows parser; wiki behaviour unchanged (REGRESSION)
  - Surfaced by: Outside voice, D23 (`tests/core/test_guide_catalog.py:80`, `core/wiki.py:31`)
  - Files: `core/item_res.py`, `core/wiki.py`, `tests/core/test_item_res.py`, `tests/core/test_guide_catalog.py` (new case only)
  - Verify: existing full-name test unchanged and green; non-equipment shortened name kept
- [ ] **T22 (P2, human: ~45 min / CC: ~10 min)**: canonical path skips bare alias lines
  - Surfaced by: Outside voice, D24 (`Someonesmall-SMN-sets.lua:146`)
  - Files: `gs_sandbox.lua` or `core/gearswap_reader.py`, tests
  - Verify: three-path fixture; criterion 4 on the real SMN file

Build-order placement: T15 and T19 go with step 3 (sandbox), T21 with step 1, T16/T18/T22 with step 5, and
T17/T20 with step 9 (commit 2).

## Outside voice (Codex)

Codex (`gpt-6-astra`, high reasoning, read-only, about 96K tokens) reviewed #2 plus this doc after the four
sections. It found 8 issues; all were verified against the code before being presented, and Jason accepted all
8 (D17-D24). Cross-model tension: one point. D11 (with #2) dropped "Path: X" when matching augments; Codex
showed that GearSwap treats Path as a real augment (`extdata.lua:1758`), so D18 reverses that part of D11. The
other seven were gaps this review missed, not disagreements. Codex's overall line: "Revise the plan before
implementation because its sandbox still exposes unsafe functions and its matching and provenance rules can
produce incorrect ownership results and misdirected Lua fixes." Those revisions are now in this doc.

## Completion summary

- Step 0: Scope Challenge: scope accepted as-is, built as 2 commits (D1)
- Architecture Review: 6 issues found (D2-D7)
- Code Quality Review: 5 issues found (D8-D12)
- Test Review: diagram produced, 2 issues (D13-D14), 1 gap left for design review
- Performance Review: 1 issue found (D15)
- NOT in scope: written
- What already exists: written
- TODOS updates: 1 item proposed, added to section 12 (repo has no TODOS.md)
- Failure modes: 0 critical gaps flagged
- Outside voice: ran (Codex, after re-enabling `codex_reviews`): 8 findings, all accepted (D17-D24)
- Parallelization: 3 lanes, 3 parallel / then 1 sequential (G)
- Lake Score: 22/22 recommendations chose the complete option
- Unresolved decisions: 0

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Outside Review | Codex via `/plan-eng-review` | Independent 2nd opinion | 1 | completed | 8 findings (4 P1, 4 P2), all accepted |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 22 issues (14 review + 8 Codex), 0 critical gaps, all resolved |
| Design Review | `/plan-design-review` | UI/UX gaps | 0 | — | — |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **OUTSIDE COVERAGE:** codex, plan-review phase: completed (gpt-6-astra). An earlier attempt the same day was skipped because `codex_reviews` was disabled in config; Jason re-enabled it.
- **CROSS-MODEL:** native review (Claude) and Codex overlap on sandbox hardening. Codex extended D7 (package.loaded) and corrected D11 (Path is a real augment). The other 7 Codex findings were not covered by the native review.
- **VERDICT:** ENG CLEARED, ready to implement after `/plan-design-review` settles the 3 design questions in section 13.

NO UNRESOLVED DECISIONS
