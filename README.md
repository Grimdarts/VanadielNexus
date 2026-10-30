# Vana'diel Nexus

All-in-one FFXI Windower 4 overlay: JSE/REMA/checkpoint tracker, wishlist, live stats & Mote modes,
inventory browser, addon manager and hotkey conflict scanner. Talks to the `VanadielNexus` Windower
addon over local UDP (ports 5017/5018).

## For players

1. Download `VanadielNexus.exe` from the latest [Release](https://github.com/Grimdarts/VanadielNexus/releases/latest)
   and put it in its own folder (ideally next to your `Windower4` folder).
2. Run it. It finds Windower4 automatically, or asks you to pick the folder once. It installs the
   Windower addon for you; in game run `//lua load vanadielnexus`.
3. Updates: the app checks GitHub on launch and offers to update itself. Only the exe is replaced.
   Your tracker data in `data\` (next to the exe) is never touched.

## For development

| Task | Command |
|------|---------|
| Run from source | `py vanadielnexus_overlay.py` |
| Rebuild your local exe | `.\build.ps1` (closes, rebuilds, relaunches) |
| Ship a version to players | `.\release.ps1 1.3.0` |

- After cloning, enable the auto-rebuild hook once: `git config core.hooksPath tools/hooks`.
  Every commit that changes a `.py`/`.spec` file then rebuilds `VanadielNexus.exe` in the background
  (log: `.git\last-build.log`).
- `release.ps1` bumps `APP_VERSION`, tags `vX.Y.Z` and pushes; GitHub Actions
  (`.github/workflows/release.yml`) builds the exe and publishes the Release players update from.
- The Windower addon Lua is embedded in `vanadielnexus_overlay.py` (`VANADIEL_NEXUS_LUA_CODE`) and
  synced into `Windower4\addons\VanadielNexus` on launch, so addon changes ship with app updates.
- Player data (`data/`) and build output are git-ignored.
