# Vana'diel Nexus — notes for Claude

FFXI / Windower 4 companion app (PySide6 desktop window) plus a small Windower Lua addon that talks to it
over UDP (ports 5017/5018). Public repo: Grimdarts/VanadielNexus. Jason is the owner and only tester.

## Layout

- `vanadiel_nexus/core/` — logic with no UI (inventory, hotkeys, addons, gear guides, updater, paths).
- `vanadiel_nexus/ui/` — Qt windows; one module per page under `ui/pages/`.
- `vanadiel_nexus/bridge/udp.py` — the app side of the addon protocol.
- `vanadiel_nexus/resources/VanadielNexus.lua` — the Windower addon (its own version in `_addon.version`).
- `tests/` — pytest + pytest-qt (`tests/core`, `tests/ui`, Lua harness tests at the top level).
- `DESIGN.md` — the approved visual system. Follow it for any UI change.
- `docs/*-PLAN.md` — past product, engineering and layout plans. New plans go in `docs/` too.
- `data/` — Jason's own player data. Never commit it, never overwrite it in tests.

## Test

```bash
py -3 -m pytest -q
```

171 tests, all passing on 2026-11-01. 21 of them are Lua tests that need `lupa` (installed in Jason's
Python since 2026-11-01; `py -3 -m pip install lupa` if missing). Without it they skip, or point
`VN_LUA_RUNTIME` at a folder containing lupa. Report skipped tests honestly; don't count them as passes.

Use `py -3`, not `python` (bare `python` is the Microsoft Store stub on this PC).

## Build

- `build.ps1` rebuilds `VanadielNexus.exe` with PyInstaller, closes the running app, swaps the exe and
  relaunches it. `tools/check_frozen.py` checks the frozen build starts.
- The post-commit hook (`tools/hooks/post-commit`) runs `build.ps1` in the background after any commit that
  touches `.py` or `.spec` files, so committing app code restarts Jason's running app. Mention that before
  committing if the app is open.

## Addon changes

After editing `VanadielNexus.lua`, bump its `_addon.version`, syntax-check it with lupa, and copy it to
`C:\Users\Jason\Games\Windower4\addons\VanadielNexus\`. Jason reloads it in game (`//lua reload vanadielnexus`).
Before editing anything in the Windower folder (settings.xml, init.txt, addon settings), check the app isn't
writing to the same file and back up first to `C:\Users\Jason\Games\FFXI-Backups`.

## Release (publishes to every player)

`.\release.ps1 X.Y.Z` bumps `__version__` in `vanadiel_nexus/__init__.py`, commits, tags `vX.Y.Z` and pushes.
GitHub Actions then builds the exe and publishes a Release, and every player's app offers it on next launch.

- Release only after Jason has tested the change himself and explicitly says to release.
- Versioning lives in `__init__.py` only. There is no VERSION file or CHANGELOG.md; don't create them.
  Release notes go on the GitHub Release.
- Pushing commits to `main` without a tag doesn't reach players, but the repo is public: ask before pushing.

## gstack in this repo

| Stage | Use | Notes |
|---|---|---|
| Shape an idea | `/office-hours` or `/spec` | `/office-hours` when the idea is still fuzzy, `/spec` when Jason knows what he wants. |
| Review the plan | `/plan-eng-review`, `/plan-design-review` | Design review for anything visible in the app; plans saved under `docs/`. |
| Build | normal coding, tests first where practical | Run the full test command above before calling a step done. |
| Debug | `/investigate` | |
| Review the change | `/review` (or `/code-review`) | Before committing. |
| Ship | commit → Jason tests in game → `release.ps1` | Don't use `/ship` or `/land-and-deploy` as-is: they expect VERSION/CHANGELOG and a PR flow this repo doesn't use. |

Not applicable here: `/qa`, `/qa-only`, `/browse`, `/canary`, `/benchmark`, `/setup-deploy` (they test web
apps; this is a desktop app). Visual checks use `tools/screenshot_pages.py` and Jason's own testing.
