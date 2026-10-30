# Vana'diel Nexus Redesign Plan (draft for discussion)

Status: AGREED 2026-10-29 (premises, points 1-5, Qt rebuild). Icon choice pending. Nothing built yet.

## What the app is for (in your words)

A **companion app** you run next to FFXI, on a second monitor or by alt-tabbing. It:

1. Tracks the gear you have, the gear you need or want, and the items you currently hold.
2. Guides you toward getting or upgrading that gear.
3. Shows the addons and plugins you use, lets you turn them on or off, and holds the addons you write yourself.
4. Launches the in-game overlays (like a fixed **GearInfo**), which live inside the game as Windower addons.

Gemini merged two ideas: an always-on-top overlay and a companion app. The plan separates them again. The **app** is a normal window. **Overlays** are real Windower addons that the app installs, starts and stops.

## Premises (please agree or push back)

1. The app is a normal desktop window, not always on top. In-game overlays are Windower addons drawn by the game client, not by the app.
2. GearInfo should be a **fixed GearInfo addon** running in game, not a page inside the app. The app's job is to install, configure and launch it.
3. Gear tracking and guidance are the heart of the app. Live stats and Mote modes are secondary and can move or go away.
4. Other players will use it, so nothing can depend on your folders, your character, or your key bindings.

## Your six points: what's wrong and what I'd do

### 1. Colors, unreadable dropdowns, loud buttons

What's actually happening:
- The **white top bar** is the Windows title bar. Windows draws it in light mode because the app never asks for a dark one.
- **Dropdowns are unreadable** because the app styles everything in light text but never styles the dropdown, so you get light text on a white box. That's also why the job picker looks like the slider.
- **Buttons are loud** because nearly every button has its own saturated color (blue, green, purple, orange, red). When everything shouts, nothing stands out.

Fix: one small design system (a `DESIGN.md`) with a dark palette, a single accent color for the one main action on each screen, quiet secondary buttons, and red only for destructive actions. Dark Windows title bar. Properly styled dropdowns, sliders and tables.

### 2. Buttons lost in a window, cramped small text

What's actually happening: the six tabs and the top bar are laid out in fixed rows that assume a near-full-width window. The base font is 9pt, with many 8pt labels.

Fix:
- Replace the six wide tabs with a **left sidebar** (Gear, Wishlist, Inventory, Addons, Hotkeys, Settings). It works from about 900px wide up.
- Toolbars wrap or collapse into a "More" menu instead of falling off the edge.
- Base text 11pt, table rows taller, a text-size setting.
- The app remembers its size, position and monitor.

### 3. Always on top; companion app vs overlay

Fix: drop the always-on-top flag, the opacity slider, and the "compact HUD" mode from the main window. The app becomes a normal window you can alt-tab to. An optional "pin on top" toggle in Settings is cheap to keep if you ever want it. Anything you want to *see in game* becomes an addon overlay (point 3b below).

### 3b. GearInfo

GearInfo is an existing open-source addon by Sebyg666 (v1.7.2.7, already in your Windower addons folder). Gemini rebuilt part of it as a page in the app instead of fixing the addon.

Fix: keep GearInfo as an in-game addon and fix it to work with your job GearSwap files. Jason's report: it doesn't calculate everything correctly, most likely **haste that ignores buffs from other jobs** (for example Haste/Haste II, March, Geo-Haste, Embrava). This is a separate piece of work: confirm the exact gap in game first, then fix it in the addon. The app then gets a GearInfo card in the Addons screen: installed version, on/off, settings, and "open in game".

### 4. Addons & Plugins tab

What's actually happening: the tab shows a **hard-coded list of 8 addons** with made-up "loaded" states. One of them (superwarp) isn't even installed on your PC, and your real ones (XIPivot, Skillchains, equipviewer, and about 45 others) aren't shown.

Fix:
- Read the real `Windower4/addons` and `Windower4/plugins` folders.
- Show which ones start automatically (from `scripts/init.txt`), which are running now, and let you load, unload or reload each one.
- An **autoload toggle** that edits `init.txt` for you, with a backup.
- **Settings in one place (Jason's main goal for this tab):** click any addon to see and edit its settings (most Windower addons keep them in `addons/<name>/data/settings.xml`), with a backup before saving and a reload after.
- A **My Addons** section (later phase): Jason hasn't written other addons yet. Default folder `Documents/VanadielNexus/MyAddons`; the app installs them into Windower and reloads them in one click.

### 5. The 1-click install buried in tab 3

Fix: a **setup status indicator** in the top bar, for example "Setup: 2 of 3 done". Clicking it opens a short checklist: Windower folder found, Nexus addon installed, GearSwap hook installed, GearInfo installed. Each line has one "Fix" button. New players see this automatically on first launch.

### 6. Icon

The feather is the default Python/Tk icon. Options that fit FFXI without copying Square Enix art or logos:
- A faceted **crystal** (crystals are core to Vana'diel's look), with a subtle "VN".
- A **compass rose** shaped like a crystal, which fits "guide me to my gear".
- An **adventurer's satchel or gear emblem** inside a crystal frame.

I'd generate a few variants with gstack's `/design-shotgun` and you pick.

## The bigger choice: how to rebuild the UI

| | A. Restyle the current app (Tkinter) | B. New UI on Qt (PySide6), keep the logic **(recommended)** | C. Web-style UI (HTML/CSS in a desktop window) |
|---|---|---|---|
| Effort | Small | Medium | Medium to large |
| Looks | Better, but Tkinter fights dark themes and resizing | Modern dark theme, proper dropdowns and tables, resizes cleanly | Most flexible looks |
| Risk | Low | Low to medium | Medium: more moving parts |
| Exe size | ~12 MB | ~60 to 80 MB | ~20 MB plus a browser engine |

Why B: your points 1 and 2 are mostly Tkinter limits. Qt gives real dark styling, layouts that reflow, high-DPI support, and system tray support out of the box. It's still Python, so the tracking logic, database and update system carry over. While moving to Qt, the 4,000-line single file gets split into small modules (gear, inventory, addons, hotkeys, updater), which makes every later change safer.

## Proposed build order

1. **Foundation:** split the code into modules, new Qt window with sidebar, design system, dark title bar, remembered window size. Same features, readable.
2. **Gear & wishlist:** the heart of the app, laid out properly with upgrade guidance.
3. **Addons hub:** real addon and plugin list, load/unload, autoload, My Addons.
4. **Setup checklist and icon.**
5. **GearInfo fix** (addon side), plus its card in the app.
6. Inventory, hotkeys and settings polish.

Each phase ships as its own release, so other players only get finished pieces.

## How gstack fits

1. `/office-hours` (this document): agree on what the app is.
2. `/design-consultation`: writes `DESIGN.md` (colors, fonts, spacing, button rules). `/design-shotgun` for icon variants.
3. `/plan-eng-review`: checks the architecture before building (Qt structure, how the app talks to Windower).
4. Build, then `/review` on each phase.

gstack's `/qa` and `/design-review` are built for web apps, so for this desktop app I'd test by running it and taking screenshots instead. You don't need another skill set installed.

## Decisions so far

- Premises 1-4: agreed.
- Points 1, 2, 3, 4, 5: agreed as written, plus the addon settings editor.
- UI rebuild: option B (Qt / PySide6).
- Live stats and Mote modes: secondary (premise 3); they move into overlays or Settings.
- Icon: choosing from `docs/icon-options.html`.
- GearInfo: suspected haste calculation gap with buffs from other jobs.
