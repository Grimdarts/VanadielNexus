# Tonight's FFXI / Vana'diel Nexus test checklist

For Jason, Monday November 2, 2026. Start with sections 1–4. The later sections
are optional checks or work that is not ready to test yet. Check a box when it
passes; leave failures open and record the item ID and what happened at the end.
If you already completed an item, write the result rather than repeating it.

This combines the VN handoffs with the newer FFXI/graphics handoff. Older notes
were checked for superseding results: ReShade/avatars are installed, Layout
keyboard controls and G13 M-buttons already passed, and the old zoning-crash
diagnostic plan is superseded. Details and sources are at the bottom.

## 1. Start the correct app and game

- [ ] **START-1 — Launch the existing VN app:**
  `C:\Users\Jason\Games\VanadielNexus\VanadielNexus.exe`.
  It should open normally and show your usual saved data. Today's bundle commit
  does not replace/rebuild this executable; the Sets usability build is already
  installed. Its source reference is `6397caf` (app version 2.2.0).
- [ ] **START-2 — Connect to your character.** Launch FFXI normally and confirm VN
  sees the correct character/job and an inventory snapshot. Use your existing
  addon setup; if the bridge is missing, the existing command is
  `//lua load vanadielnexus`. Record connection failures before testing Sets.

## 2. VN Sets page — main outstanding app test

These checks were explicitly left pending in the November 1 handoff. They do not
require editing a player Lua or installing the new GearSwap bundle.

- [ ] **SETS-1 — Item right-click menu.** Open Sets, select a job/set and right-click
  a named gear cell. BG-Wiki, FFXIAH and FFXIclopedia choices should appear. Try
  each and confirm it opens the intended item, not a different piece.
- [ ] **SETS-2 — Empty-cell selection.** Right-click an empty slot. There should be
  no item wiki menu, and the highlighted slot and details panel must agree. You
  should not still see a replacement/copy action for the previously selected slot.
- [ ] **SETS-3 — Replacement readability.** Select a populated slot. In Owned
  replacements, names should be readable on one line with Location separate.
  Selecting a candidate should show its full name, bag and augments. If an
  other-character candidate is available, its owner should be named and copying
  it should be unavailable for the current character.
- [ ] **SETS-4 — Open job file.** Before selecting a replacement, click **Open job
  file**. It should open that job's Lua using your Windows file association.
  Opening is sufficient; do not edit it for this test.
- [ ] **SETS-5 — Open source file.** Select a replacement with a verified source
  destination and use **Open source file**. It should open the displayed source
  file. An ambiguous location should be explained, not presented as verified.
  Mark N/A if no verified-source example is available tonight.
- [ ] **SETS-6 — Safe copy preview.** Copy one proposed slot line and paste it into
  **Notepad only**. Check item name, exact augments, any bag/priority constraint,
  and the named destination. If **Copy N snippets** is available, each snippet
  should have its own destination instructions. Do not paste into live Lua as a test.
- [ ] **SETS-7 — Alt-tab refresh.** With a replacement selected, switch to Notepad
  and back without changing files. The same replacement should remain selected
  after refresh; copying may be briefly disabled during the refresh.
- [ ] **SETS-8 — Optional keyboard menu.** Focus the grid, use arrow keys to select
  a cell, then Menu/Shift+F10. A populated slot should open one context menu and
  retain a visible focus indicator. Skip if your keyboard makes this awkward.

Already reported working: selectors/follow-game updates on job changes and the
earlier BLU/SMN/RUN grid-versus-equipped comparisons. Do not repeat the entire
gear comparison unless a new mismatch appears. The old RUN coat-name mismatch
is a known separate issue; a `nova_gear` key is not an FFXI item ID. Also, GearInfo
can immediately re-equip idle gear after `//gs equip naked`; avoid using that
command as the starting point for tonight's app checks.

## 3. EnemyHUD — remaining self-buff/dispel check

The newer FFXI handoff says icons/sleep behavior passed, but enemy self-buff tiles
and dispel removal were still untested. Installed EnemyHUD identifies as 1.3.0.

- [ ] **ENEMY-1 — Enemy self-buff.** In an ordinary safe encounter, watch a target
  apply a visible self-buff such as Protect, Shell or Haste. Confirm the matching
  buff tile appears on EnemyHUD for that target.
- [ ] **ENEMY-2 — Successful removal.** When you or a party member successfully
  removes that buff with an appropriate dispel, its tile should clear. A resisted
  dispel is not a successful-removal test. Note the mob, buff and combat-log result
  if the tile remains. Mark N/A if you do not encounter a suitable buff tonight.

## 4. XIVPetBar — theme persistence

The compact layout already passed. Theme persistence was explicitly not checked.

- [ ] **PET-1 — Select the intended theme.** With a pet out, note the current look,
  then run `//petbar theme ffxi`. Confirm the pet bar remains compact/readable and
  matches the chosen theme. Record your previous theme if you want to restore it.
- [ ] **PET-2 — Reload persistence.** In a safe location run
  `//lua reload XIVPetBar`. Summon/release as needed and check that the selected
  theme survives. If you later restart FFXI tonight, check once more after login.

## 5. Graphics — post-merge check, not a new installation

Newer notes say ReShade was installed/tested and avatar choices were reviewed.
The avatar files were subsequently merged, and the post-merge summon check
remained pending. Current XIPivot configuration was read back as:

```text
AV-ShivaAlt,NextHD-Avatars,XI-View,Sky-Marked-HD,Remapster-Marked-HD,Remapster,FFXI HD Pack
```

- [ ] **GRAPHICS-1 — Active overlay list after a fresh launch.** After fully closing
  FFXI and PlayOnline and relaunching through Windower, run `//pivot s`. Expect
  seven configured overlays in the order above. Record the actual list if it
  differs; per-character XIPivot settings can override global settings.
- [ ] **GRAPHICS-2 — Summons after the merge.** Summon one or two familiar avatars
  and confirm they still use the selected models, with no missing/broken textures.
  If convenient, include Shiva: `AV-ShivaAlt` currently takes precedence over
  NextHD's Shiva.
- [ ] **GRAPHICS-3 — Normal zoning observation.** During ordinary travel, note any
  crash, missing map, unexpected textures or new severe FPS issue. Marked maps
  were subsequently reported OK; this is a smoke check after the merge, not an
  instruction to redo the superseded October 31 crash-isolation experiment.
- [ ] **GRAPHICS-4 — Optional Shiva preference.** Decide whether to keep the active
  alternative Shiva or request NextHD Shiva. Record the choice here; no overlay
  changes are required just to report a preference.

ReShade is already present, so do not rerun the staged installer for this list.
Current readback and the newer handoff agree: the **backtick key** opens its menu and
**Home** toggles effects. Its first in-game confirmation is already recorded.

## 6. Optional VN regression checks — status not confirmed in the handoffs

These come from earlier feature acceptance plans. They are useful if you have
time, but they were not all explicitly left pending in the latest handoff.

- [ ] **GUIDE-1 — Guide picker.** On Guide upgrades, try BLU, COR, RDM and SMN.
  Purpose → Set → Version should make sense and load the selected equipment.
  One concrete example: COR → Weapon skill → Savage Blade, then change version.
  Record any set grouped somewhere you would not look for it.
- [ ] **GUIDE-2 — Item links outside Sets.** Right-click an item on Guide upgrades,
  Inventory, Gear and Wishlist. Check the three wiki choices. Double-click on
  Guide upgrades/Inventory should open the default site; Gear/Wishlist should
  still open Edit. Cancel Edit without changing data.
- [ ] **GUIDE-3 — Existing augment targets.** If you previously saved an augment
  target, confirm it is still attached to the same item. No need to invent or
  change a target to run this check.
- [ ] **LAYOUT-1 — Optional position/scale check.** With VN open, use `//vn layout`
  and check frame alignment at your normal UI scale. Drag/cancel first. The
  earlier walking-on-frame-click and keyboard-control problem is recorded as
  passed after the later fix; report a regression if it returns.
- [ ] **LAYOUT-2 — Optional save/persistence check.** If you want to test Save,
  record one overlay's original position, move/save it, check the in-game result,
  and restore the original position through the UI. Layout Save intentionally
  updates addon settings; skip this if you only want read-only app checks tonight.
- [ ] **G13-1 — Optional current LCD check.** On SMN, check whether the existing
  physical LCD shows the avatar and useful Rage/Ward recasts as they change.
  The `G13 SMN HUD.lnk` Startup shortcut now exists, superseding the old note
  asking you to create it. Record stale/missing LCD data; the new bundle's LCD
  redesign is not installed.
- [ ] **NOVA-1 — Optional current HUD/countdowns.** Check the existing Nova HUD's
  mode labels and Rage/Ward countdowns (tenths, e.g. `4.3s`) during normal SMN use.
  The newer handoff specifically lists Nova HUD/countdown changes as an optional
  remaining check. Physical M1/M2/M3 switching was already confirmed working.

## 7. New GearSwap bundle — not ready for an in-game pass tonight

T3 and the offline T4 components are staged only. Today's commit does not install
them. The installed SMN still has its legacy Lag Mode behavior and missing OFF-path
helper; do not toggle it off just to test the repaired candidate. The private
flag-only candidate is also not an activation build.

The following remain on the project list, but **do not mark them as testable or
passed merely because you play your current SMN profile tonight**:

- [ ] **BUNDLE-1 — Gated:** finish native host/control snapshots and live
  character/server-ID verification with a reviewed diagnostic procedure.
- [ ] **BUNDLE-2 — Gated:** prepare the converted personal SMN profile and validate
  independent canonical/action parity before any installation.
- [ ] **BUNDLE-3 — Gated:** after explicit activation authorization, test load,
  reload, unload/job change, settings/key precedence, G13 compatibility, defense
  priority and weapon locks in the candidate.
- [ ] **BUNDLE-4 — Gated:** in that authorized candidate, test both Lag Mode
  command spellings, display agreement and normal/compensated pact gear timing:
  physical, magical, hybrid, healing, buff/debuff, accuracy/burst and Siphon.

The next agent should read [T4 validation](GEARSWAP-T4-VALIDATION.md) rather than
telling you to copy `staging/gearswap` into Windower.

## Results to send back

```text
Date / character / main job / subjob:
App used: installed VanadielNexus.exe
Passed IDs:
Failed IDs:
Skipped / N/A IDs and why:

For each failure:
ID:
Exact command/click and expected result:
What happened (copy the complete error if any):
Screenshot or short clip, if helpful:
For gear/HUD: avatar, pact/spell, active modes and relevant buffs:

Shiva preference (optional):
Anything already tested earlier that this list should mark complete:
```

## Sources and how this list was reconciled

- [Sets handoff](HANDOFF-SETS-2026-11-01.md): explicit pending usability checks;
  earlier selectors/live gear comparisons already reported working. The private
  November 1 checkpoint records installed build hash
  `FDB88BBD723870E9A78EF7874A6AF89EFD5FA183915DF2A2065AEFB135BFA034`, independently
  matching the installed executable during this checklist's preparation.
- [Guide acceptance plan](GUIDE-UPGRADES-SPEC.md) and
  [guide grouping review](guide-set-groups.md): optional manual grouping/link checks.
- [Layout plan](LAYOUT-PLAN.md): optional alignment/save checks, reconciled with
  later reported PASS results rather than treating every old plan checkbox as pending.
- `C:\Users\Jason\Games\FFXI-Graphics\NEXT-SESSION.md` (updated November 1):
  EnemyHUD self-buff/dispel, pet-bar theme and post-merge avatar checks; already
  passed GearInfo, Layout keys/HUDToggle, G13 M-buttons and initial ReShade/avatar review.
- `C:\Users\Jason\Games\FFXI-Graphics\README.md`, especially its November 1
  updates: marked maps reported OK and older crash-isolation notes superseded.
- Current read-only checks: XIPivot overlay settings, ReShade hotkeys/files,
  installed EnemyHUD source version, physical LCD script/Startup shortcut, and
  the unchanged VN executable hash. Configuration/files do not by themselves
  prove that a feature passed a live test.
- [Bundle engineering plan](GEARSWAP-BUNDLES-ENG-REVIEW.md),
  [SMN baseline](GEARSWAP-SMN-BASELINE.md) and
  [T4 validation](GEARSWAP-T4-VALIDATION.md): separate staged future checks from
  currently installed behavior.

Search coverage: this VN repository and its recent local checkpoint/handoff,
the linked older Claude VN handover, Nova-Control-Tower's FFXI records, and the
newer FFXI-Graphics handoff/install log. This is not a claim to have searched every
private conversation from every AI. User-reported results in newer handoffs take
precedence over stale staging notes. No gameplay command or installed-file edit
was issued while preparing this document.
