# Set manager slice 1: design review

Status: REVIEWED with Jason, 2026-11-01 (gstack `/plan-design-review`). Covers the UI of issue
[#2](https://github.com/Grimdarts/VanadielNexus/issues/2) (the Sets page and the reusable `EquipGrid`), as
amended by `docs/SET-MANAGER-ENG-REVIEW.md`. Checked against `DESIGN.md` and `ui/theme.py`. The wireframe
`docs/set-manager-wireframe.png` (top half) is the visual starting point; this doc wins where they differ.

Rule order: this doc > `SET-MANAGER-ENG-REVIEW.md` > issue #2 for anything visible. Engineering behaviour is unchanged.

- **Mockups:** the gstack AI mockup tool needs an OpenAI API key, and none is set up, so no AI mockups were
  made. The specs below are written to be built straight from, and `tools/screenshot_pages.py` checks them
  after implementation.
- **Outside voices:** both ran (Codex and an independent Claude reviewer). Their full text is in the appendix.

## 1. Scores

| Pass | Before | After | Why it isn't 10 |
|---|---|---|---|
| Step 0 (overall impression) | 6/10 | | |
| 1. Information architecture | 5 | 9 | Final proof needs screenshots of the built page |
| 2. Interaction states | 5 | 9 | Same |
| 3. User journey | 5 | 9 | Same |
| 4. AI-slop risk | 8 | 9 | Same |
| 5. Design-system fit | 6 | 9 | Same |
| 6. Responsive and accessibility | 4 | 9 | Same |
| 7. Unresolved decisions | — | 3 resolved (eng review §13), 0 open | |
| **Overall (lowest pass)** | **4** | **9** | Run `/design-review` on the built page |

## 2. Decisions (all made by Jason)

| ID | Issue | Decision |
|---|---|---|
| D1 | Review focus | All 7 passes |
| D2 | Outside voices | Run both (Codex + Claude reviewer) |
| D3 | Panes don't fit 788-912 px of content width | **Splitter + sliding panel** |
| D4 | Verdict buried in counts | **Verdict-first header** |
| D5 | Long paths and aliases in the tree | **Short names, middle elision, ↪ alias rows, read-only caption, search states** |
| D6 | No primary action | **The panel's copy button is the one primary; Reload is a ghost "⟳ Reload files"** |
| D7 | Colour-only states, no selection look | **A word on every state, token per state, selection ≠ focus** |
| D8 | Loading/idle/empty unspecified | **All specified; copy disabled across context changes** |
| D9 | Snapshot/freshness/errors scattered | **One status strip in priority order + freshness line** |
| D10 | Warnings list repeats the grid | **"Needs attention · N", actionable only, capped at 4** |
| D11 | Copy loop | **Scope summary, payload-named button, "Copied" status, re-read on focus, changed-cell outline** |
| D12 | Live job changes | **Follow the game; pin on manual pick; "Follow game" link** |
| D13 | Replacement list | **"Owned replacements", grouped, two-line rows, filter, stored-copy guidance** |
| D14 | Card frames everywhere | **Frames on slot cells only** |
| D15 | Cell can't hold its content | **112×128 × text scale, icon tile doubles as slot label** |
| D16 | No keyboard/screen-reader path | **Full keyboard map + accessible names** |

## 3. Layout (D3, D4, D5, D6, D9, D14)

```
WIDE: content width ≥ tree + grid + panel (about 200 + 472 + 330 + gaps ≈ 1,030 px)
┌ Toolbar ───────────────────────────────────────────────────────────────────────────────────────┐
│ [Search sets or items…] [Someonesmall ▾] [BLU ▾] [WAR ▾] [⟳ Reload files]   (ghost)            │
│ Lua read 2 min ago · Inventory from 1 Nov 14:20        Game is on SMN/WHM · Follow game  (D12)  │
├────────────────────┬───────────────────────────────────────────┬────────────────────────────────┤
│ FROM YOUR LUA      │ ⚠ 2 need attention          16px/600 amber│ HEAD                           │
│ (read-only)  12px  │ SavageBlade.Attack          14px          │ Hashishin Kavuk +2 · owned     │
│ Uses BLU.lua, shared│ Weapon skill · Nova-BLU-sets.lua ·        │ ─────────────────────────────  │
│ with other jobs    │   15/16 set · 1 upgrade     12px muted    │ Owned replacements   [filter]  │
│ Weapon skill (12)  │ ┌ one status strip (D9), if any ───────┐ │  Higher tier owned             │
│   SavageBlade.Att… │ └──────────────────────────────────────┘ │   Hashishin Kavuk +3   [↑]     │
│        [↑1] [⚠2]   │ ┌────┐┌────┐┌────┐┌────┐  slot cells:     │   Wardrobe 3                   │
│   ↪ savage (alias) │ │MAIN││SUB ││RNG ││AMMO│  the only framed  │  In your wardrobes …           │
│ Idle (4)           │ └────┘└────┘└────┘└────┘  elements (D14)   │  Stored …                      │
│   …                │ … 4 rows of 4, 112×128 each, gap 8        │  On other characters (2) ▸     │
│                    │ Needs attention · 2                       │ Replace 1 slot line in         │
│                    │   Ring 2: Sroda Ring is in Mog Safe 1. …  │   Nova-BLU-sets.lua (D11)      │
│                    │   +N more                                 │ ┌ head="Hashishin Kavuk +3", ┐ │
│                    │                                           │ └────────────────────────────┘ │
│                    │                                           │ [Copy slot line] (primary)     │
│                    │                                           │ Open file · Copy 3 snippets    │
├────────────────────┴───────────────────────────────────────────┴────────────────────────────────┤
│ status line: "Copied: paste into Nova-BLU-sets.lua, then //gs reload"                            │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘

NARROW (900×600 minimum, 1180×760 default): tree | centre. The panel slides in OVER the centre from the
right on a cell click (160 ms), with "← Back" at its top; Esc or Back closes it and returns focus to the cell.
```

- **Splitter:** `QSplitter` like `gear.py:84`. The tree has a minimum of 200 px and a remembered width
  (setting `sets_tree_width`). The grid has a fixed size. The centre column (header, strip, grid, Needs
  attention) is inside a `QScrollArea`, so 600 px of height works.
- **Header (D4):** line 1 is the verdict, 16 px/600:
  - gold `✓ All pieces owned`;
  - amber `⚠ N need attention`, counting unreachable, missing, other_character and unknown cells;
  - faint `No inventory snapshot`.
  Line 2 is the path without `sets.` (14 px), plus `· also called magicalpact` when there are aliases. Line 3
  is a 12 px muted caption: `purpose · file · N/16 set · N upgrade(s)`.
- **Tree (D5):**
  - A 12 px caption "From your Lua (read-only)" sits above the tree. The shared-file note is a 12 px caption
    under it, not a banner (D9).
  - Purpose groups show counts and hide when empty.
  - Rows show the path without `sets.`, elided in the middle, with the full path as tooltip and accessible name.
  - Badges are right-aligned `widgets.pill`: gold `↑ N`, warning `⚠ N`.
  - Alias rows are one faint line, `↪ magicalpact`; selecting one selects the canonical set.
  - Search matches paths, aliases and item names, and expands the matching groups. With no match the tree
    shows `No set or item matches "x"` with a **Clear** link.
- **Buttons (D6):**
  - The only primary (cyan fill, navy text) is the panel's copy button, shown only when a replacement is chosen.
  - **Open file** and **Copy N snippets** are secondary.
  - **⟳ Reload files** is a ghost button.
  - The "Follow game" link is a ghost link.
- **Freshness (D9):** a 12 px muted line next to Reload: `Lua read <relative time> · Inventory from <time>`
  (from settings `inventory_updated`, `context.py:80-82`), or `No inventory yet`.

## 4. EquipGrid cell (D7, D15)

```
┌──────────────── 112 × scale ────────────────┐
│ ┌──────┐                                    │
│ │ HEAD │  32 px icon tile (surface-2).  [↑] │  ↑ = gold badge on the tile's top-right corner
│ └──────┘  Shows the faint 12 px slot name   │  •  = amber dot when requirements are unverified
│           until slice 2 swaps in the icon.  │
│ Hashishin Kavuk +2      13 px, 2 lines,     │  middle elision keeps the "+N" suffix
│                         elided in middle    │
│ Wardrobe 3              12 px caption       │  priority: state word > "from sets.X" > bag
└──────────────────── 128 × scale ────────────┘
Grid: 4 × 112 + 3 × 8 = 472 px at 100% text (612 px at 130%).
```

| State | Name | Caption | Frame |
|---|---|---|---|
| `owned` | `GOLD` | bag (`Wardrobe 3`) | `#Card` |
| `unreachable` | `TEXT` | `WARNING` "⚠ Mog Safe 1" / "⚠ on a slip" | `#Card` + `WARNING` border |
| `missing` | `FAINT` | "✕ Not owned" / "only 1 owned" / "not in Wardrobe 3" / "BLU can't wear this" | `#Card` |
| `other_character` | `FAINT` | "On Aynon" | `#Card` |
| `unknown` | `TEXT` | `DANGER` "Unknown item" / "Wrong slot" | `#Card` |
| `no_snapshot` | `FAINT` | "No snapshot" | `#Card` |
| `empty` | `FAINT` italic "Unequip" | — | `#Card` |
| `not_set` | `FAINT` "Not specified" | — | dashed `BORDER` |

- **Inherited slots:** caption "from SavageBlade" (short path); the full path is in the panel.
- **Selected:** a 2 px `ACCENT` ring outside the state border.
- **Keyboard focus:** a 1 px dotted `ACCENT` inner ring. Focus and selection never share a look.
- **Changed after a re-read (D11):** a 1 px `ACCENT` outline for one read cycle (no animation).
- Every state reads in words; colour only reinforces it.
- `CellData` gains `note: str` (amber dot plus panel line), `changed: bool` and `accessible_name: str`.
  Sizes come from `scale` (the app's text scale).

## 5. Interaction states (D8, D9, D10)

| Feature | Loading | Empty | Error | Success | Partial |
|---|---|---|---|---|---|
| Whole page | First read: centre shows "Reading <file>…" | No Windower folder / no GearSwap: `widgets.EmptyState` with a button or text (as #2). No job files: EmptyState listing the searched folders | A card replaces the tree and centre only; the toolbar stays usable to switch job | Tree + grid + header | Amber strip "Read incomplete: some sets may be missing · Details · Retry" |
| Re-read (Reload, focus, follow) | Previous grid stays, dimmed, with "Reading <file>…" over the centre | — | Card as above | Same set, slot and scroll kept on a same-job reload | Strip as above |
| Context change (char/job/sub) | The panel clears; copy is disabled until the new result arrives | — | — | Auto-select (below) | — |
| Tree | — | "No set or item matches "x" · Clear" | — | First set needing attention selected, else the first set | — |
| Grid | dimmed during reload | 16 cells per state table | — | per state table | — |
| Status strip (max one) | — | hidden | priority: error (DANGER) > read incomplete (WARNING) > no snapshot (FAINT "Log in with the Nexus addon running to see what you own") | hidden | amber strip |
| Needs attention | — | hidden when N = 0 | — | ≤4 sentence rows + "+N more"; click selects the cell; skips empty, not_set, no_snapshot | — |
| Panel | — | "Click a slot to see what you own for it." | — | Slot details + Owned replacements | — |
| Details expander | — | — | Scrolls, capped at 8 lines (tracebacks, searched paths) | — | — |

## 6. Journey storyboard (D8, D11, D12, D13)

```
STEP | YOU DO                                   | YOU FEEL               | PLAN SPECIFIES
1    | Open Sets while playing BLU              | "show me my BLU sets"  | Follows the game (D12); auto-selects the first set needing attention (D8)
2    | Scan the tree badges                     | quick triage           | Gold ↑ / amber ⚠ pills (D5)
3    | Read the header, look at the grid        | instant verdict        | Verdict line (D4); a word on every cell (D7)
4    | Click the amber/↑ cell                   | confident choice       | Grouped, two-line Owned replacements; full augments on select (D13)
5    | Copy, paste into the Lua, //gs reload    | small risk, reassured  | Scope summary + payload-named button + "Copied: paste into <file>" (D11)
6    | Alt-tab back to the app                  | "did it take?"         | Quiet re-read on focus; changed cells outlined once (D11)
7    | Change job in game                       | page keeps up          | Follows unless pinned; never mid-copy (D12)
8    | Look at another character's sets by hand | in control             | Pinned, with a "Game is on SMN/WHM · Follow game" link (D12)
```

Time horizons:
- **5 seconds:** the verdict line and the grid's gold/amber.
- **5 minutes:** triage and copy fixes.
- **Long term:** trust, built by the freshness line (D9) and fixes that land (D11).

## 7. Panel: Owned replacements (D11, D13)

- **Header:** slot, then the current piece (name, augments one per line, bag constraint, priority, status
  detail, any amber "Requirements unverified: race-limited / needs superior level N").
- **Heading** "Owned replacements". A filter box appears when there are more than 8 rows.
- **Groups**, in order:
  - "Higher tier owned" (gold `↑` chip);
  - "In your wardrobes";
  - "Stored": rows readable (not dimmed), caption "Move from Mog Safe 1 before use";
  - "On other characters (N)", collapsed.
- **Rows** are plain two-line list rows, not cards: the name with its tier suffix never elided, then
  `bag · key augments`. Selecting a row expands its full augments, then shows the copy area.
- **Copy area:**
  - A one-line scope summary: "Replace 1 slot line in Nova-BLU-sets.lua", "Fix at root SavageBlade · fixes 3
    sets", or "Replace shared table · affects 4 sets ▸" (expands the list). When the location is ambiguous
    (eng D22), it adds "Location ambiguous · search for <path>".
  - The snippet is a monospace block on `SURFACE_2` with a 6 px radius.
  - The primary button is named for its payload: **Copy slot line** / **Copy table** / **Copy N snippets**.
  - Then **Open file** (secondary) and the read-only note.
- **After copying**, the status line says "Copied: paste into <file>, then //gs reload". Never "Fixed".

## 8. Keyboard and accessibility (D16)

| Key | Action |
|---|---|
| Tab order | search → character → job → sub job → ⟳ Reload files → tree → grid (one stop) → panel |
| ← → ↑ ↓ (grid) | move in the 4×4 order (Main Sub Range Ammo / Head Neck Ear1 Ear2 / Body Hands Ring1 Ring2 / Back Waist Legs Feet) |
| Enter / Space (grid) | open the panel for that slot (same as a click) |
| Esc | close the panel, focus back on the originating cell |
| Ctrl+F | focus search |
| F5 | Reload files |

- **Accessible names:** each cell gets one, e.g. "Head: Hashishin Kavuk +2, owned, Wardrobe 3, upgrade
  available". Tree rows use the full path. The verdict line is announced on selection.
- **Nothing needed is hover-only:** the panel always shows full names and augments.
- **Text:** all text is 12 px or larger at 100%, and every size scales with the 90-130% text setting.
- **Contrast:** colours come from `theme.py` tokens (WCAG AA per DESIGN.md). Dimming uses `FAINT`, never opacity.

## 9. NOT in scope

- AI mockups: the tool needs an OpenAI key. Run `/design-shotgun` later if Jason sets one up.
- Item icons (slice 2). D15 reserves their tile now.
- The Gear page in the 4×4 layout: own issue, but it inherits D7, D15 and D16 through `EquipGrid`.
- A light theme: the app is dark-only (DESIGN.md).

## 10. What already exists (reuse)

| Need | Existing |
|---|---|
| Colours, fonts, pills, tones | `ui/theme.py` tokens, `*[tone=…]` styles, `widgets.pill` |
| Framed cells / panel | `#Card`, `#Panel` (`theme.py:105`); G13 page cell grid (`pages/g13.py:25-38`) |
| Empty states | `widgets.EmptyState` (`widgets.py:186`) |
| Toolbar | `widgets.SearchToolbar` (`widgets.py:145`) |
| Resizable panes | `QSplitter` on the Gear page (`gear.py:84`) |
| Right detail panel | `GuidePanel` pattern (`ui/guide_panel.py`) |
| Status line | `Page.status()` → `MainWindow.show_status` |
| Inventory timestamps | settings `inventory_updated` (`context.py:80-82`) |
| Text scale | settings `text_scale`, `MainWindow.apply_text_scale` |

## TODOs

None new. Every decision above is in scope for slice 1. Visual QA happens with `/design-review` after the build.

## Implementation Tasks

Synthesized from this review's findings. These attach to build steps 6 and 10 of `SET-MANAGER-ENG-REVIEW.md` §6.

- [ ] **DT1 (P1, human: ~3h / CC: ~25 min)**: sets page: splitter, sliding panel, scroll area (D3)
  - Files: `ui/pages/sets.py`, `tests/ui/test_sets_page.py`
  - Verify: `tools/screenshot_pages.py` at 900×600 and 1180×760, 100% and 130%; panel opens over the grid when narrow, and Esc returns focus
- [ ] **DT2 (P1, human: ~1h / CC: ~10 min)**: EquipGrid: 112×128 × scale cell, icon tile as slot label, middle elision (D15)
  - Files: `ui/equip_grid.py`, `tests/ui/test_equip_grid.py`
  - Verify: "+3" never elided; nothing under 12 px; screenshot at 130%
- [ ] **DT3 (P1, human: ~1.5h / CC: ~15 min)**: EquipGrid: per-state words/tokens, selection vs focus rings, note dot, changed outline (D7, D11)
  - Files: `ui/equip_grid.py`, `ui/theme.py` (cell styles), tests
  - Verify: each state renders its caption word; selection and focus look different
- [ ] **DT4 (P1, human: ~2h / CC: ~15 min)**: EquipGrid + page keyboard map and accessible names (D16)
  - Files: `ui/equip_grid.py`, `ui/pages/sets.py`, tests
  - Verify: arrow/Enter/Esc/Ctrl+F/F5 tests; accessible-name text test
- [ ] **DT5 (P2, human: ~1.5h / CC: ~15 min)**: page states: auto-select, placeholder, dimmed re-read, copy disabled across context change, keep selection on reload (D8)
  - Files: `ui/pages/sets.py`, tests
  - Verify: tests for each state in §5
- [ ] **DT6 (P2, human: ~1h / CC: ~10 min)**: header verdict, status strip priority, freshness line, shared-file caption (D4, D9)
  - Files: `ui/pages/sets.py`, tests
  - Verify: strip priority test; freshness text from `inventory_updated`
- [ ] **DT7 (P2, human: ~1h / CC: ~10 min)**: tree short names, alias rows, pills, search states, read-only caption (D5)
  - Files: `ui/pages/sets.py`, tests
  - Verify: elision keeps the end of the path; alias selects canonical; no-match + Clear
- [ ] **DT8 (P2, human: ~45 min / CC: ~10 min)**: Needs attention list (D10)
  - Files: `ui/pages/sets.py`, tests
  - Verify: skips empty/not_set/no_snapshot; caps at 4; click selects the cell
- [ ] **DT9 (P2, human: ~1.5h / CC: ~15 min)**: Owned replacements groups, two-line rows, filter (D13); scope summary, payload button, Copied status (D11). Commit 2
  - Files: `ui/pages/sets.py`, tests
  - Verify: groups in order; button label per payload; status text after copy
- [ ] **DT10 (P2, human: ~1h / CC: ~10 min)**: follow game / pin / Follow game link; re-read on window focus (D11, D12)
  - Files: `ui/pages/sets.py`, tests
  - Verify: a live state change switches the job unless pinned; never while a copy summary is open; focus triggers read_job (cache hit)
- [ ] **DT11 (P2, human: ~15 min / CC: ~3 min)**: frames on cells only; primary/ghost button kinds (D6, D14)
  - Files: `ui/pages/sets.py`
  - Verify: screenshot shows one cyan button at most

## Completion summary

```
+====================================================================+
|         DESIGN PLAN REVIEW — COMPLETION SUMMARY                    |
+====================================================================+
| System Audit         | DESIGN.md + theme.py present; UI: Sets page, |
|                      | EquipGrid (reused by Gear later)            |
| Step 0               | 6/10; all 7 passes                          |
| Pass 1  (Info Arch)  | 5/10 → 9/10 after fixes                     |
| Pass 2  (States)     | 5/10 → 9/10 after fixes                     |
| Pass 3  (Journey)    | 5/10 → 9/10 after fixes                     |
| Pass 4  (AI Slop)    | 8/10 → 9/10 after fixes                     |
| Pass 5  (Design Sys) | 6/10 → 9/10 after fixes                     |
| Pass 6  (Responsive) | 4/10 → 9/10 after fixes                     |
| Pass 7  (Decisions)  | 3 resolved, 0 deferred                      |
+--------------------------------------------------------------------+
| NOT in scope         | written (4 items)                           |
| What already exists  | written                                     |
| TODOS.md updates     | 0 items proposed                            |
| Approved Mockups     | 0 generated (no OpenAI key), 0 approved     |
| Decisions made       | 14 added to plan (D3-D16)                   |
| Decisions deferred   | 0                                           |
| Overall design score | 4/10 → 9/10                                 |
+====================================================================+
```

All passes are 8+. The plan is design-complete; run `/design-review` after implementation for visual QA.

## Appendix: outside voices (findings as written, lightly condensed)

Litmus scorecard:

```
  Check                                    Claude  Codex  Consensus
  1. Brand unmistakable in first screen?   —       YES    single
  2. One strong visual anchor?             YES*    YES    CONFIRMED
  3. Scannable by headlines only?          NO*     NO     CONFIRMED fail → D4, D5
  4. Each section has one job?             —       YES    single
  5. Cards actually necessary?             —       NO     single → D14
  6. Motion improves hierarchy?            —       YES    single
  7. Premium without decorative shadows?   —       YES    single
  Hard rejections triggered:               none    none   CONFIRMED none
  * read from the Claude reviewer's findings 8 and 11 (it did a completeness pass, not the litmus list)
```

### CODEX SAYS (design critique), gpt-6-astra, read-only

```text
Classification: APP UI. Keep the purpose tree → equipment grid → slot inspector structure. It matches the
player's task and makes the familiar FFXI equipment arrangement the visual anchor. The plan needs revision
before implementation: its dimensions fail inside the actual app shell, and its ownership and copy-fix
presentation overstates certainty.

Hard rejection checks: 1-7 all NO (the 4×4 represents equipment slots, not dashboard metrics; no imagery;
no carousel; the primary composition is a functional three-pane workspace; keep replacement candidates as
list rows).

Litmus: 1 YES, 2 YES (the 4×4 equipment grid), 3 NO (raw Lua paths and "Owned that fit" do not explain
status, replacement scope, or the paste destination), 4 YES, 5 NO (slot boundaries are necessary;
additional card shells around metadata, warnings, and replacement rows are not), 6 YES (brief inspector
slide; repeated updates should remain still), 7 YES.

Rule failures: dense but readable, calm surface hierarchy, utility language.

1. [P1] The fixed three-pane layout does not fit the supported window. 260 + 408 + 330 = 998 px, about
   1,014 px with gaps. At the default 1180 px window the sidebar and margins leave 912 px; at 900 px, 788 px.
   Fix: adaptive modes (three panes when they fit; otherwise the inspector replaces the centre with
   Back/Esc; collapse the tree into a drawer at large text), resizable splitters with remembered widths,
   validate at 900×600 and 1180×760 at 100% and 130%. SearchToolbar moves its whole control group to a
   second row, so it needs a measured compact layout.
2. [P1] A 96×96 cell cannot hold the specified content at readable sizes (12 px label, 32 px placeholder,
   two 14 px lines, 12 px caption). The wireframe fits only with 9-11 px text. Fix: 96 as a minimum; a
   compact slot marker instead of an empty 32×32 placeholder; item name priority; preserve tier suffixes;
   one short status line; inheritance paths in the inspector; size from font metrics; reserve an explicit
   future icon layout.
3. [P1] "Owned that fit" promises more than the amended checks establish (D10 keeps race/superior-level
   unverified items owned; snapshot age not shown). Fix: "Owned replacements"; gold for ownership plus an
   amber "Requirements unverified" marker in the cell and candidate row; show requirements before copying;
   "Inventory recorded …" separate from "Lua read …" (timestamps in context.py:80); never "Ready to equip".
4. [P1] The copy workflow needs a visible scope and destination before the action (slot vs inherited root
   vs shared table; one count can't represent both edits and impact). Fix: summary such as "Replace shared
   table definition · 1 edit location · affects 4 sets" with an expandable affected-set list; payload-named
   buttons ("Copy slot replacement", "Copy table replacement", "Copy 3 replacement snippets"); one cyan
   primary, bulk copy secondary; "Location ambiguous" beside the destination; keep "Open file" (not "Open
   file at line"); feedback says "Copied", never "Fixed".
5. [P2] The status system hides problems and overproduces warnings (missing/other-character muted while
   owned is gold; warnings include empty, not_set and repeated no-snapshot; generic unknown text
   contradicts "wrong slot"). Fix: labels Missing / Stored elsewhere / Other character / Wrong slot /
   Unknown item; amber for availability, danger for invalid; cyan for selection/focus independent of status
   borders; empty = "Unequip", not_set = "Not specified"; one page-level no-snapshot message; "Needs
   attention · N" with a few actionable rows and an expandable remainder; clicking selects the cell.
6. [P2] Long paths and aliases overwhelm a 260 px tree. Fix: shortest unambiguous suffix, right-aligned
   counts, full path in header and tooltip, small alias marker, search over paths/aliases/items that expands
   groups and names the matched item, "No matching sets" with Clear search.
7. [P2] The replacement list needs its own search and copy identity. Fix: searchable two-line rows (name,
   then bag plus distinguishing augments); groups for higher tier, reachable, stored; stored rows readable
   with "Move from Mog Safe 1 before use"; expand full augments on selection; label upgrades "Higher tier
   owned".
8. [P2] Live context and refresh behaviour remain undefined. Fix: "Following game" and "Pinned selection"
   modes; manual choice pins; quiet "Follow game" action; on context change clear the inspector and disable
   copying until the matching result arrives; keep selection and scroll on same-context Reload; label the
   action "Reload files".
9. [P2] Partial reads need a stable, restrained presentation. Fix: one compact amber strip "Read
   incomplete — some sets may be missing" with Details and Retry; raw errors in the expander; shared-file
   information as quiet metadata; bounded, scrollable detail areas.
10. [P2] The reusable grid has no keyboard or focus contract. Fix: one Tab stop with arrow keys in the 4×4
    order; Enter opens the inspector; Esc closes and returns focus; accessible names/descriptions with slot,
    full name, status, upgrade; focus visually distinct from selection; no hover-only essentials.

Recommendation: Revise the plan before implementation because its fixed layout cannot fit the supported
window and its ownership and copy-fix cues do not yet communicate usability, destination, and scope reliably.
```

(The Codex output above is condensed only by joining wrapped lines and shortening its file links. Findings,
numbers and recommendations are as Codex wrote them.)

### CLAUDE SUBAGENT (design completeness)

```text
1. CRITICAL: three panes don't fit at the minimum window, or the default. Tree 260 + grid 408 + panel 330
   leaves 166 px for the grid at 900 px wide and 290 px at the default 1180. Fix: QSplitter like gear.py
   (tree min 200, grid fixed); below about 1300 px the detail panel becomes a right-side overlay that slides
   over the grid and closes with Esc.
2. CRITICAL: cell content can't fit 96×96 and the grid can't fit 600 px of height; 130% text scale makes
   both worse. Fix: cells ≥ 104×116 × text_scale; centre column in a QScrollArea; one caption line chosen by
   priority (state word > "from sets.X" > bag).
3. HIGH: several states are colour-only; "selected" has no look and would clash with the amber and dashed
   borders. Fix: a word or glyph per state (owned gold name + bag; unreachable WARNING "⚠ Mog Safe 1";
   missing FAINT "✕ not owned"; other_character "on Nova"; unknown DANGER); selection = 2 px ACCENT outer
   ring; dim with FAINT, never opacity.
4. HIGH: the no-snapshot explanation is only in the picker, seen after a click; no snapshot age. Fix:
   snapshot state as a centre-header banner; always show "Inventory from <time>".
5. HIGH: the copy → paste → Reload loop breaks: no selection persistence, no "Copied" feedback; the
   wireframe's "read 2 min ago ⟳" was dropped. Fix: keep set path and slot across reloads; "Copied: paste it
   into <file>"; "Read <file> · <time>" by Reload; mark changed cells for one cycle.
6. HIGH: idle and loading states unspecified (selection after read, panel before a click, old grid during a
   read, search with no matches, all jobs "(no file)"). Fix: auto-select the first set with warnings; panel
   placeholder; dim the grid with "Reading <file>…"; "No set or item matches '<q>'"; EmptyState with paths.
7. HIGH: no keyboard path. Fix: focusable cells, arrows in the 4×4, Enter/Space click, Ctrl+F, F5, Esc;
   tab order search → combos → tree → grid → panel; setAccessibleName per cell.
8. MEDIUM: the verdict is buried in the count string; long paths don't fit 260 px; the wireframe's "FROM
   YOUR LUA (READ-ONLY)" label is missing. Fix: verdict first line, then path 16/600, counts as 12 px
   caption; drop "sets." and middle-elide with a tooltip; add the read-only label.
9. MEDIUM: banners and error cards have no order or extent. Fix: the card replaces tree + centre only,
   toolbar stays enabled; banner order read error > partial > snapshot with theme tones; shared-file note as
   a caption under the tree header.
10. MEDIUM: the warnings list repeats the grid, grows without limit, and has no room. Fix: omit no_snapshot,
    not_set, empty; 4 lines then "+N more"; clicking selects the cell.
11. MEDIUM: primary button and badges unspecified. Fix: Copy fix primary; Copy all and Open file secondary;
    Reload ghost; tree badges as widgets.pill gold "↑ N" / warning "⚠ N"; upgrade chip tone="gold".
12. MEDIUM: follow-live-job undecided. Fix: follow until the user changes a picker by hand, then show "Game
    is on SMN/WHM. Switch" and keep the manual choice for the session.
```

**CROSS-MODEL:** both reviewers agreed on 9 of the issues (D3, D4, D5, D7, D8 in part, D9, D10, D12, D16).
Codex alone raised copy scope/destination (D11, part), the "Owned that fit" wording and replacement search
(D13), and the card frames (D14). The Claude reviewer alone raised loading/idle states (D8), the copy loop
feedback (D11, part) and the primary button (D6). They disagreed in only two places. On cell size, the
Claude reviewer proposed 104×116 and Codex a compact marker with no reserved icon space; D15 took a reserved
icon tile at 112×128. On gold for owned items, both kept it, and D7 follows them.

## GSTACK REVIEW REPORT

| Review | Trigger | Why | Runs | Status | Findings |
|--------|---------|-----|------|--------|----------|
| CEO Review | `/plan-ceo-review` | Scope & strategy | 0 | — | — |
| Outside Review | Codex via `/plan-eng-review` and `/plan-design-review` | Independent 2nd opinion | 2 | completed | eng: 8 findings, all accepted; design: 10 findings, folded into D3-D16 |
| Eng Review | `/plan-eng-review` | Architecture & tests (required) | 1 | CLEAR (PLAN) | 22 issues, 0 critical gaps |
| Design Review | `/plan-design-review` | UI/UX gaps | 1 | CLEAR (FULL) | score: 4/10 → 9/10, 14 decisions |
| DX Review | `/plan-devex-review` | Developer experience gaps | 0 | — | — |

- **OUTSIDE COVERAGE:** codex, design phase: completed (gpt-6-astra). Native Claude subagent, design phase: completed. codex, plan-review phase: completed (8 findings).
- **CROSS-MODEL:** Codex and the native Claude reviewer agreed on 9 design issues and differed only on cell sizing (resolved by D15).
- **VERDICT:** ENG + DESIGN CLEARED, ready to implement (build order in `SET-MANAGER-ENG-REVIEW.md` §6, design tasks DT1-DT11 above).

NO UNRESOLVED DECISIONS
