# Vana'diel Nexus v2 Engineering Plan

Status: REVIEWED 2026-10-30 (gstack /plan-eng-review). Inputs: `docs/REDESIGN-PLAN.md` (product, agreed) and `DESIGN.md` (visual, approved).
Goal of v2.0: replace the 4,000-line Tkinter overlay with a Qt companion app that looks like `docs/design-preview.html`, without losing any player data or the auto-update path.

## Step 0: scope challenge

**What already exists and gets reused (moved, not rewritten):**
- Hotkey scanning and the job-aware conflict logic (`scan_all_hotkeys_and_conflicts`, `compute_hotkey_conflicts`, `classify_gearswap_lua`), verified against Jason's Windower folder in v1.2.1.
- Inventory classification and roll-up (`classify_ffxi_item`, `consolidate_inventory_items`).
- Wiki URL parsing (`parse_wiki_url_or_name`, `build_wiki_urls`).
- Database load/save with `.bak` fallback, Windower folder detection, settings file.
- Self-updater (GitHub Releases), `build.ps1`, `release.ps1`, Actions release workflow, post-commit rebuild hook.
- The Windower addon `VanadielNexus.lua` and the UDP protocol (ports 5017/5018).

**Minimum change for v2.0:** new Qt shell (sidebar, top bar, theme), pages ported with the same features, logic moved into testable modules. **Deferred to later phases:** My Addons, addon settings editor, GearInfo fix, upgrade-guidance content.

**Removed in v2.0 (agreed in premises 1 and 3):** always-on-top, opacity slider, compact HUD, the live-stats page, the `modules/*.py` plugin loader (runs arbitrary code; no one uses it; can return later as proper addon management).

**Complexity check:** v2.0 touches more than 8 files and adds several classes. This is intended: it is the "scrap the foundation" rewrite Jason approved (option B), and the alternative (patching one 4,000-line file) is what caused the current problems. Mitigation: logic moves first with tests, then UI is built on top, in separate commits.

## Architecture

```
vanadiel_nexus/
  __main__.py            entry point: python -m vanadiel_nexus
  core/                  pure Python, no Qt imports -> unit-testable
    paths.py             app dir, data dir (next to exe, %APPDATA% fallback if not writable)
    settings.py          data/settings.json
    database.py          tracker DB: atomic save, .bak fallback, schema migrations
    windower.py          find Windower4, list addons/plugins, read/edit scripts/init.txt (with backup)
    hotkeys.py           scan + conflict rules (from v1.2.1)
    inventory.py         classification + roll-up (from v1)
    wiki.py              BG-Wiki / FFXIAH / FFXIclopedia URL parsing
    setup_check.py       the Setup checklist: Windower found? addon installed? hook installed?
    updater.py           GitHub Releases check + exe swap script
  bridge/
    udp.py               QUdpSocket bridge to VanadielNexus.lua (signals, main thread)
  ui/
    theme.py             DESIGN.md tokens -> one Qt stylesheet; dark title bar (DWM)
    main_window.py       sidebar + top bar + page stack; remembers size/position/monitor
    widgets/             StatusPill, ProgressCard, SearchToolbar, DetailPanel
    pages/               gear.py, wishlist.py, inventory.py, addons.py, hotkeys.py, settings.py
    dialogs/             setup_checklist.py, add_gear.py, wiki_import.py
  resources/
    VanadielNexus.lua    the Windower addon as a real file (no more 300-line string in Python)
    Mote_Nexus_Hook.lua
    default_database.json
    fonts/Cinzel-SemiBold.ttf
    VanadielNexus.ico
tests/
  core/                  pytest, one file per core module
  ui/test_smoke.py       pytest-qt: window builds, every page opens, theme applies
```

### Data flow

```
 FFXI + Windower                        Vana'diel Nexus (Qt, one process)
 ┌──────────────────────┐   UDP 5017    ┌───────────────┐  signals   ┌──────────────┐
 │ VanadielNexus.lua    │ ────────────▶ │ bridge/udp.py │ ─────────▶ │ ui/pages/*   │
 │ (character, job,     │ ◀──────────── │ (QUdpSocket)  │            │ (Qt models)  │
 │  inventory, binds)   │   UDP 5018    └───────────────┘            └──────┬───────┘
 └──────────────────────┘                                                   │ edits
                                         ┌───────────────┐   load/save      │
   Windower4/ folder  ◀── read/edit ───  │ core/*        │ ◀────────────────┘
   (addons, init.txt,     (with .bak)    │ (pure Python) │ ──▶ data/ffxi_database.json (+ .bak)
    GearSwap data)                       └───────────────┘ ──▶ data/settings.json
```

Player data never leaves `data/`. Updates replace only the exe; the addon `.lua` is copied into Windower only when its contents changed.

### Key decisions (made, with reasons)

1. **PySide6-Essentials, not full PySide6.** Essentials has everything this app uses (widgets, network, SVG) and cuts the exe to roughly 45 to 60 MB instead of ~80 MB. Confirmed 6.12.0 installs on Jason's Python 3.14.
2. **Core logic has no Qt imports.** Every rule (conflicts, inventory roll-up, DB migration, init.txt editing) is tested with plain pytest, fast and without a screen.
3. **UDP moves onto Qt's event loop (QUdpSocket).** v1 updated Tkinter from background threads, which Tkinter does not support and can crash randomly. Qt signals remove that class of bug.
4. **Tables use Qt models, refreshed on change.** v1 rebuilt every table four times a second. v2 redraws only rows that changed, so large inventories stay smooth.
5. **The Lua addon becomes a real file** bundled with the exe. It's editable, diffable and reviewable, and the hash comparison decides when to copy it into Windower.
6. **Data stays next to the exe** (portable, matches v1, Jason's data needs no migration). If that folder isn't writable (for example under Program Files), fall back to `%APPDATA%\VanadielNexus` and say so in Settings.
7. **One-file exe stays,** so the updater keeps working unchanged. Startup cost (unpacking Qt) is measured in phase 1. If it is over about 3 seconds, switch to a one-folder build and update the updater to swap the folder.
8. **init.txt and addon settings edits always write a timestamped `.bak` first** and never touch a file while it fails to parse.
9. **Database schema version field + migrations.** v1 databases (no version) migrate to v2 on first load, and the original is kept as `ffxi_database.v1-backup.json`.

## Failure modes and edge cases

| Situation | What the player sees |
|---|---|
| Windower not found | Setup checklist opens on first launch with "Choose Windower folder". Hotkeys and Addons pages show an empty state with the same button. |
| Game not running / addon not loaded | Top bar shows "Game not connected"; tracker pages work fully offline. |
| UDP port 5017 already in use (second copy of the app) | Second copy shows a message and focuses the first window instead of starting. |
| Corrupt database | Loads `.bak`, shows a one-line notice; never silently resets to the demo data. |
| init.txt edited while the game is running | Edit still writes (with backup); notice says to run `//exec init.txt` or restart. |
| Update download fails or is cut off | Partial file is deleted; current version keeps running; retry offered. |
| Data folder not writable | Falls back to `%APPDATA%`; Settings shows the active data folder. |
| High-DPI or 4K monitor | Qt scales everything; text stays crisp. |
| Window opened on a monitor that's now unplugged | Saved position is ignored if off-screen; window opens centered on the main monitor. |

## Tests

```
core/database      load/save, .bak fallback, v1 -> v2 migration, unknown fields preserved
core/hotkeys       job files never conflict; subfolders inactive; Mote override; init.txt vs GearSwap conflicts
core/inventory     stack roll-up, augment separation, scattered detection
core/windower      folder detection order, addon/plugin listing, init.txt autoload toggle + backup
core/wiki          BG-Wiki / FFXIAH / FFXIclopedia URLs and plain names
core/updater       version compare, asset selection, swap-script contents
core/setup_check   each checklist state
ui/smoke           window opens, all six pages render, theme applied, no Qt warnings
```

A regression fixture copies the shape of Jason's real GearSwap folder (file names only, no contents) so the "206 to 27 conflicts" result is locked in. CI: a new GitHub Actions workflow runs the tests on every push; the release workflow refuses to publish if tests fail.

## Performance

- Startup target: under 3 seconds to a usable window (measured in phase 1; see decision 7).
- Inventory of 3,000+ items: filtering stays instant via a Qt proxy model.
- Hotkey scan runs in a background worker and fills in when done; the page never freezes.

## Build phases (each ends in a release)

| Phase | Contents | Release |
|---|---|---|
| 1 | Core modules + tests, Qt shell with theme, sidebar, top bar, dark title bar, icon, Setup checklist, all existing pages ported (Gear, Wishlist, Inventory, Addons list, Hotkeys, Settings). HUD, opacity and plugin loader removed. | v2.0.0 |
| 2 | Gear and wishlist depth: upgrade-guidance layout, progress cards, better add/import flows | v2.1 |
| 3 | Addons hub: real addon/plugin list, load/unload/reload, autoload toggle, per-addon settings editor | v2.2 |
| 4 | GearInfo: find the haste gap in game, fix the addon, GearInfo card in Addons | v2.3 |
| 5 | My Addons folder, inventory and hotkey polish | v2.4 |

## NOT in scope (v2.0)

- My Addons, addon settings editor (phase 3/5).
- GearInfo fix (phase 4; needs in-game testing with Jason).
- Live "is this addon loaded right now" detection: to be investigated in phase 3 (Windower may not expose a loaded-addon list to other addons; needs a probe, not an assumption).
- Code signing the exe (Windows SmartScreen will still warn new players on first download).

## GSTACK REVIEW REPORT

| Run | Status | Findings |
|---|---|---|
| Step 0 scope | Done | Rewrite justified (approved option B); reuse list above; 4 features deferred, 4 removed |
| Architecture | Done | 9 decisions recorded; threading bug class (Tk from threads) eliminated by QUdpSocket |
| Code quality | Done | Embedded Lua string, 250 ms full redraw, duplicated defaults, and arbitrary-code plugin loader all removed |
| Tests | Done | 8 test areas + regression fixture + CI gate on releases |
| Performance | Done | Startup budget 3 s with a fallback plan; model/view tables; background hotkey scan |
| Outside voice | Skipped | No second model configured on this machine |

VERDICT: READY TO BUILD phase 1, pending Jason's go-ahead.

NO UNRESOLVED DECISIONS
