# Overlay Layout: design (draft for Jason, 2026-10-31)

Arrange every addon that draws on the game screen, the way FFXIV's HUD Layout works.
You can do it in two places, and each job keeps its own layout.

## What you get

1. **Layout page in the app.** A picture of your game screen with a labeled box for each overlay. Drag the boxes, then Save. The app writes each addon's position and reloads it in game.
2. **Layout mode in game.** Type `//vn layout`. Every overlay shows as a labeled frame on top of the game. Drag them where you want, then click **Save** or **Cancel** on screen. The app does the saving, so it needs to be open.
3. **One layout per job.** Pick a job at the top of the page (or just be on that job in game). Jobs you haven't set up use your **Default** layout. When you change job, the overlays move to that job's spots by themselves. A switch turns that off.
4. **Show or hide per job.** Each overlay has a "Shown on this job" box. Pet TP on SMN and BST only, for example. Hidden means the app unloads that addon on that job.

Layouts are saved per character, so your alts keep their own.

## The Layout page

```
┌──────────────────────────────────────────────────────────────────────────┐
│ Layout   Job: [ SMN ▾ ]  [Copy from… ▾]   ☑ Switch with my job   [Save]  │
├───────────────────────────────────────────────────┬──────────────────────┤
│                                                   │ Overlays             │
│   ┌ Parse: melee ┐                ┌ EnemyHUD ┐    │ ☑ EnemyHUD   733,40  │
│   └──────────────┘                └──────────┘    │ ☑ Parse: melee       │
│                                                   │ ☑ SMN HUD  1476,234  │
│                        (your game screen)         │ ☐ Debuffing (hidden) │
│                                   ┌ SMN HUD ┐     │ ☑ Pet TP             │
│   ┌ Skillchains ┐                 └─────────┘     │ …                    │
│   └─────────────┘     ┌─── xivbar ───┐            │ X [ 1476 ] Y [ 234 ] │
│                       └──────────────┘            │                      │
└───────────────────────────────────────────────────┴──────────────────────┘
```

- **Moving boxes:** drag one, or use the arrow keys to nudge it 1 pixel (Shift+arrow moves 10). Boxes snap to the screen edges, the center line and each other.
- **Background:** optional. Pick one of your FFXI screenshots so you can see where the game's own menus sit.
- **Capture current positions:** if you drag an overlay in game outside layout mode, this button copies its real spots into the job you're editing.
- **Undo:** Save backs up every file it changes first, the same way the addon settings editor does.

## Which overlays

Every installed addon that draws on screen, loaded or not. Ones that aren't running can still be placed, and they appear in place the next time they load.

| Kind | Addons |
|---|---|
| Single window | Debuffed, Debuffing, distance, enemybar, EnemyHUD, equipviewer, findAll, maga, Omen, PetTP, pointwatch, scoreboard, SpeedChecker, zonetimer, ConsoleBG, GearInfo, bluguide |
| Several windows (each placed on its own) | Parse (melee, ranged, magic, defense), DistancePlus (main, pet, height, ability), Skillchains |
| Placed from the bottom center | xivbar, XIVPetBar |
| Your custom files | SMN HUD (`GearSwap/data/Someonesmall-SMN-hud.lua`), Parse per-character spots (`parse/data/<name>_positions.lua`) |
| Can't be moved, left off the page | TParty (sticks to the game's party list), TargetLines (draws in the 3D world, not on the screen) |

The app also finds new addons by itself. Any addon whose settings have an x/y position shows up as a plain box, labeled "size unknown".

## How it works (engineering)

- **One list of overlays** (`resources/overlays.json`) says, for each addon:
  - where its position lives (file and setting)
  - how to read it: from the top left, from the right edge (negative numbers, like DistancePlus), or from the bottom center (xivbar)
  - its rough size
  - the command that shows a preview, if it has one (e.g. `//petbar test`)
- **Reading and writing** go through the existing settings code (`core/addon_settings.py`), which already rewrites all 37 of your settings files without changing anything else in them.
  - Positions go into your character's own section of the file, so alts aren't affected.
- **Applying a layout** touches only the addons that actually move, in this order:
  1. Unload the addon.
  2. Write the file.
  3. Load the addon.
  - Not a plain reload: some addons save their old position as they unload and would overwrite the new one.
- **Job switch:** the in-game Nexus addon already reports job changes. The app looks up that job's layout and applies the differences.
- **In-game layout mode:**
  - The Nexus addon draws its own labeled frames. One addon can't move another addon's windows, so the frames stand in for them.
  - It sends the final spots to the app over the existing game link.
  - It also reports your screen size, so the app's picture matches your screen.
- **Saved data:** `data/layouts.json` holds character → job → overlay → position and shown/hidden. This is player data, so updates never touch it.

## Things to know

- **Box sizes are close estimates.** The app can't measure what the game draws. In layout mode you see the real overlay under each frame, which makes up for it.
- **Changing job reloads the overlays that move.** For Parse and scoreboard, that resets their numbers. You usually change jobs in the Mog House, so this rarely matters.
- **First thing to check in game:** that positions line up with UI scale 2. The game reports its own sizes, and the first test confirms it.

## Build order

1. **Overlay list and Layout page:** read and write every addon above, Default plus per-job layouts, Save and backups. Tests make sure every one of your settings files still loads and rewrites cleanly.
2. **Switch with job, and show or hide per job.**
3. **In-game layout mode** (`//vn layout`).

Each step ends with a short list of things to try in game.

## Decided with Jason (2026-10-31)

- Both the app page and in-game mode.
- All addons that can draw on screen.
- One layout per job.

- Overlays move automatically when you change job, with a switch to turn that off.
- "Shown on this job": the app loads and unloads addons per job. GearSwap is never unloaded, because that would stop gear swaps.

## Built (2026-10-31)

All three steps: `core/overlays.py` + `resources/overlays.json`, `ui/layout_manager.py`, `ui/pages/layout.py`, addon 1.4.0 (`//vn layout`, reports the UI resolution). Not built yet: the per-addon preview commands (e.g. `//petbar test`) while arranging.
