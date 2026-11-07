# Guide upgrades page: Jason's feedback from 2.2.0 RC testing (2026-11-07)

Jason gave this feedback while testing A16 on the staged 2.2.0 RC. **Not for 2.2.0.** It goes into the next
update cycle, after 2.2.0 ships.

## Fix first in the next update (known issue shipped in 2.2.0)

- **A26 failed: Wishlist "Add item" keeps the old slot when you pick a different suggestion.** Pick
  Intarabus's Cape → Slot fills "Back"; change Item to Naegling → Slot stays "Back" (should be "Main").
  Cause: `FormDialog.fill` in `vanadiel_nexus/ui/forms.py` only fills empty fields. Fix: remember which
  fields were auto-filled and let a new pick replace those, never anything the player typed. Add a pytest-qt
  test for this exact case. Non-equipment names (e.g. Potion) correctly get no slot. Jason chose to ship
  2.2.0 with this as a known issue and fix it first next cycle (2026-11-07).

## Other pages (same test session)

- **A8, Sets: focus on "Copy slot line" is invisible.** The cyan focus outline matches the button's colour,
  so you can't tell when the keyboard is on it (still true in the 2.2.0 RC). Jason's suggestion: invert the
  button's colours when it has focus (e.g. dark fill with cyan text/border, or vice versa). Check every
  primary (cyan) button for the same problem. Shipped in 2.2.0 as a known issue (Jason, 2026-11-07).
- **A10, Sets: the Owned replacements selection clears about a second after returning to the page.**
  The grid slot stays selected; the replacement row looks selected, then drops. Likely cause:
  `SetsPage.on_shown` in `vanadiel_nexus/ui/pages/sets.py` re-reads with `self.request()` without
  `preserve_replacement=True` (the window-activation path already passes it), so the background re-read
  resets the list when it finishes. Add a pytest-qt test: select replacement → show another page → show
  Sets → wait for the read → same row still current. Shipped in 2.2.0 as a known issue.

- **Sets: upgrade badge offers a copy that's already used in the same set.** SMN `midcast.RefreshSelf`:
  Ring 1 = Stikini Ring +1, Ring 2 = Stikini Ring with an upgrade badge and "Higher tier owned: Stikini
  Ring +1". The snapshot has exactly one Stikini Ring +1 and one Stikini Ring (both Wardrobe 3), so the
  only +1 is already in Ring 1. Cause: `tier_upgrades` in `core/set_manager.py` checks each slot alone
  and ignores physical copies allocated to the set's other slots. `copy_shortages` should still warn in
  the copy preview ("not enough matching copies for Ring 1 / Ring 2"). Fix: subtract copies the set already
  uses (from `allocate`) before offering an upgrade; add a test with one +1 and one NQ ring.
- **Sets: tab labels show a stray underline.** "Attention & copy fixes" renders as "Attention _copy fixes"
  and "Contribution trail & unknown effects" the same way, because Qt treats `&` as a keyboard-shortcut
  marker. Use `&&` or reword. Jason also wants simpler names; "Attention & copy fixes" is unclear.
- **Sets: Attention tab layout.** The "Needs attention · 1" heading and the message sit far apart with
  large empty gaps; lay it out as a compact list.
- **Sets: Equipment analysis tab redesign (Jason's vision; ties to the next phase).** Today it shows
  "Partial declaration · supported subset only · saved inventory evidence · no supported contributions
  available; inspect diagnostics" and an empty table. That means nothing to a player and gives no idea
  what the tab is for or what to do. What Jason wants: pick a slot in the set, swap in a piece you own
  (or a new or upgraded piece), and see **the stats you gain and the stats you lose** before changing
  anything. Purpose: help players fit their own gear into GearSwap Lua files, since most copy someone
  else's Lua or advice and struggle to substitute their own gear. Same idea as Guide upgrades item 6
  ("stats from all the gear"); likely one shared stat engine. Next phase after 2.2.0: a Nexus-packaged
  GearSwap Lua framework players can build from, built with Jason's AI agents. Jason's own job Lua files
  currently have wrong gear, which this would help fix.

  Jason's answers (2026-11-07):
  1. **Multi-piece swaps.** Click a slot → see possible replacements (as the side panel does now) →
     choose "swap it in". Repeat for any number of slots, up to replacing the whole set. The area below
     shows the full running tally of every change together.
  2. **All stats,** across character and equipment, including special stat lines (e.g. "Refresh",
     latent or set-bonus style text). Swapping shows everything you'd gain and lose.
  3. **Lua editing:** the app auto-edits only the Lua files Nexus packages (the planned framework). Every
     other Lua file keeps today's copy-and-paste flow; the app never writes those.
  4. **Same feature in both places:** Sets → Equipment analysis and Guide upgrades (item 6). One shared
     stat engine.
  5. **Any player's Lua:** it must scan any GearSwap file, find all its sets and display them the way it
     does for Jason's files today (the Sets reader already aims at this).

  Note: the catalog and analyzer deliberately don't model numeric totals or caps today, and item stats
  come from resource descriptions, so a full stat engine is real engineering work. Plan it with
  `/plan-eng-review` and `/plan-design-review` before building.

- **Sets can't show runtime-built jobs.** `Someonesmall_BST/COR/NIN/RDM.lua` are identical 6-line stubs
  that include `Nova-NewJob.lua` and pick gear at runtime from `Nova-GuideCandidates.lua`. The Sets page
  correctly shows the generic set skeleton with every set "(empty in file)" and says "This job may pick gear
  at runtime", but a player would read that as broken. Jason thought it was because he hadn't played those
  jobs with the app running; the reader is static and never uses game state. Consider for the framework
  phase: either explain this plainly on the page or have the packaged framework declare sets the reader can
  see. Also minor: the `naked` set shows "✓ All pieces owned · 16/16" for 16 Unequip slots.

- **Setup badge goes stale.** After the addon was updated while the app was open, the top bar kept saying
  "Setup 2 of 3" until Jason clicked it and opened the checklist. Re-run the setup checks when the addon
  connects or reports its version (and on window activation), so the badge clears by itself.

- **Layout: in-game drag-and-drop isn't seen by the app, so the app can overwrite fine-tuning.** Moving
  a window with an addon's own drag-and-drop updates that addon's file, but the Layout page keeps its own
  stored position (`layouts.json`) and writes it back on the next save or job switch. Jason wants the app
  to pick up in-game moves and keep them. Options: read each overlay's current file position (and/or ask
  the addon for live screen positions, as `//vn layout` already does with LAYOUT_RESULT) before saving or
  switching, and treat a newer in-game position as the truth. `//vn layout` (A5) is the in-game path that
  does sync back today, and the Layout page's **Capture current** button (under the window list, easy to
  miss) reads the windows' current file positions; documented in the player guide as the workaround. The
  real fix is doing this automatically.
- **Layout: no live preview when dropping a box,** so you can't see whether the box lands where the
  overlay will. Move the real window live while dragging (or on drop), before Save.
- **Layout: boxes aren't 1:1 with the real windows.** Sizes in `resources/overlays.json` are fixed guesses
  (e.g. parse 330×150); measure real sizes (the addon can report text box extents) so box = window.
- **Personal parser jump (not in player builds).** Jason's patched `parse` addon keeps per-character
  positions in `data/Someonesmall_positions.lua`, re-saves *all* its windows' live positions whenever any
  one is dragged, and restores that file after every zone. On 2026-11-07 the app's saved layout had
  melee at 1103,666, but the file was rewritten at 10:34 with melee at 570,50 (the old top spot). The
  zone-in restore then snapped it back to the top. Likely sequence: the app wrote the file, then a drag
  in game made parse save its stale live melee position over it. Fix in the personal parse patch (reload
  the file before saving, or save only the dragged window) after 2.2.0. Stock Parse uses settings.xml and
  doesn't have this restore.

## Requested changes

1. **Bigger text at the top and bottom of the page only.** The rest of the app is a good size. The global
   Settings → Text size slider is not the fix; enlarge just these two areas.
2. **Label each text area** so the player knows what it is.
3. **Only relevant information in each area.** Today most of the text stays the same when you switch sets,
   and much of it reads as internal verification notes that would confuse players. Example of the top text on
   RUN Dt Idle: "Nexus recommendation · unknown · verified (2026-11-04: Offline composition: exact
   ID/RUN/slot eligibility, reviewed GreatSword/grip hands, 16 slot states, …".
   - **Top area:** everything about *this* set and its gear (what the set is for, conditions that matter
     to the player).
   - **Bottom area:** a "readme" for the whole guide: what BiS means here, which game version or update the
     guides reflect, and when the guide and gear data were last updated. Information that doesn't change
     between sets and jobs.
   - Jason is open to being asked what counts as relevant.
4. **Remove the search box** on this page. It only searches the items already listed in the set.
5. **Use the 4×4 gear grid** (like the Sets page) instead of the current list.
6. **Show the character's stats from all the gear** on the right side of the page. The meaning still needs
   pinning down; see the questions below.
7. **Allow selecting and copying text** from these areas (Jason couldn't highlight and copy text).
8. **Trim Sources to two kinds of link:** the full guide (e.g. Destiny's Device for RUN) and the gear set the
   choice was based on (e.g. the FFXIAH "Dimidiation" item set). Drop the per-item pages (Aettir, Utu Grip,
   Regal Ring …): players can already right-click an item to open its wiki page. The catalog can keep the
   item citations internally; they just shouldn't appear in the player-facing Sources list.
9. **Hide hashes and fingerprints** from the page (the SHA-style IDs). Players don't need them.
10. **Rework the "Review update…" window.** Jason's reaction: "HOLY COW." Information overload that would
    scare a normal player; most people wouldn't know what the screen is for or what to do on it. It needs to
    explain itself: what changed, why, what happens if you accept, and that your choices are kept. Show the
    differences plainly instead of the full raw comparison.
11. **The amber outdated notice** (and the "Saved revision / Available revision" line under it) has the same
    problems: tiny text, revision hashes, internal wording. Rewrite in plain words, e.g. "The guide
    corrected the augment wording for 2 items in this set. Your gear choices are the same. Review the
    update."

11b. **Plain status messages for copies.** When a set needs two of an item and you own one (A20, RUN
    Refresh Idle Ring 2), the row says "Upgrade / verify · Required copy/rank/path/augments unmet,
    unreported or allocated to another slot." Say it directly, e.g. "You have 1 — this set needs 2."
12. **The gear hover pop-up and the Item details window** need refining. Jason flagged both on
    2026-11-07 (A23 passed functionally); details still to discuss with him.

13. **App-wide formatting pass with Jason.** He wants to go over every screen, dropdown and menu for
    formatting and naming fixes. Example: "Dt Idle" should read "DT Idle". Other auto title-cased RUN names
    seen in the catalog with the same problem: "Engaged Dt", "Enmity Ja", "Sird Completion" (should be
    DT, JA, SIRD). Likely other jobs too; check every set name built from GearSwap-style names.

## Open questions for item 6 ("stats from all the gear")

To ask Jason before planning:

- Should it show stat totals for the selected set only (STR, DEX, Acc, Att, DT, Haste, Fast Cast …), or a
  full character sheet including base stats from job and level?
- Should it show the recommended set, the gear the character actually owns, or both side by side (the
  difference an upgrade makes)?
- Which stats matter most: the ones the set is built for (DT for idle, Fast Cast for precast), or every stat?
- Should it show the caps (DT −50%, Haste 25% from gear) and whether the set reaches them?

Note: the catalog deliberately avoids claiming numeric totals or caps today (it doesn't model them), so
this is new engineering work, not just a display change.

## Other observations from the same session

- The catalog has no set with exactly one source today (the minimum is 3), so the single-source part of A16
  can't be checked by hand right now.
