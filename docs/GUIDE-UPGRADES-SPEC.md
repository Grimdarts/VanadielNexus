# Item links on every item page, and a Purpose → Set → Version picker for Guide upgrades

Status: APPROVED by Jason 2026-11-01 (gstack /spec). Batch 1 of 4 (batch 2: G13 page drawn like the keypad;
batch 3: Set manager; batch 4: Guide catalog for all jobs).

## Context

Guide upgrades is where Jason picks which guide sets to build into his GearSwap files. Two things get in the way.
There is no way to open an item's wiki page from the table, and the set dropdown is one flat list of up to 79
FFXIAH titles per job, where each title mixes *what the set is for* ("Savage Blade") with *how good the gear is*
("Dream Tier"). This batch fixes both, and gives every guide set a plain purpose that the GearSwap manager
(batch 3) will later map to each job file's real set names.

## Current State (verified 2026-11-01)

Item links today:

| Page | Right-click menu | Double-click | Sites | Notes |
|------|------------------|--------------|-------|-------|
| Guide upgrades (`ui/pages/guides.py`) | none | nothing | none | Only "Open equipment set ↗" (FFXIAH set page) and "Open job guide ↗" |
| Gear (`ui/pages/gear.py:313`) | Open BG-Wiki ↗ | Edit (`gear.py:93`) | BG-Wiki | `_open_wiki(provider)` already accepts other providers but nothing passes one |
| Wishlist (`ui/pages/wishlist.py:209`) | Open BG-Wiki ↗ | Edit (`wishlist.py:57`) | BG-Wiki | Opens `row['wikiUrl']` blindly |
| Inventory (`ui/pages/inventory.py:168`) | Open BG-Wiki ↗ | nothing | BG-Wiki | Rows carry `item_id` |
| Guide panel (`ui/guide_panel.py:130`) | n/a | n/a | BG-Wiki | Side panel on Gear and Wishlist |

`core/wiki.py:build_wiki_urls` already builds BG-Wiki, FFXIAH (search) and FFXIclopedia URLs.

Latent bug: `core/gear_guides.py:88` (`track_set`) stores the FFXIAH *set* URL in the wishlist row's `wikiUrl`, so
"Open BG-Wiki" on a guide-tracked wishlist item would open the FFXIAH set page instead (no such rows exist in
Jason's data today).

Set picker today: `guides.py:_sets` adds every set whose sources include the job, labelled `"<FFXIAH title> · #<id>"`.

| Job | Sets | Job | Sets |
|-----|------|-----|------|
| COR | 79 | RUN | 47 |
| BLU | 67 | SMN | 43 |
| RDM | 64 | NIN | 26 |
| BST | 48 | SCH | 2 |

376 sets in all (`resources/gear_guides.json`, reviewed 2026-10-31). A keyword-rule prototype gives 345 of them
(92%) a purpose from the title alone. The other 31 have titles like "Starter tank set #2", "BLU (Reaving Wind)" and
"Oshala SMN".

GearSwap set names differ per job file, so the picker can't show one "real" set name:
BLU uses `sets.BlueMagic.Cures`, SMN uses `sets.damagetaken.PDT`, the Mote-based jobs use `sets.midcast.Cure`.

## Proposed Change

### A. Item links (Guide upgrades, Gear, Wishlist, Inventory, guide panel)

1. **`core/wiki.py`**: add
   ```python
   SITES = (('bgwiki', 'BG-Wiki'), ('ffxiah', 'FFXIAH'), ('ffxiclopedia', 'FFXIclopedia'))
   def item_urls(name: str, item_id: int | None = None, wiki_url: str = '') -> dict[str, str]
   ```
   - BG-Wiki: `wiki_url` only when its host is `bg-wiki.com`, otherwise `https://www.bg-wiki.com/ffxi/<Name_With_Underscores>`.
     This guard fixes the latent `track_set` bug for every caller.
   - FFXIAH: `https://www.ffxiah.com/item/<item_id>` when an ID is known, otherwise the existing search URL.
   - FFXIclopedia: the existing `/wiki/<slug>` URL.
   - `build_wiki_urls` and `parse_wiki_url_or_name` keep their current signatures and output.
2. **New `ui/item_links.py`** (shared, so all pages behave the same):
   - `add_open_actions(menu, ctx, row)`: adds "Open on BG-Wiki ↗", "Open on FFXIAH ↗", "Open on FFXIclopedia ↗".
     The default site's action comes first.
   - `open_default(ctx, row)`: opens the row on the default site.
   - Row fields read: `name` (or `title` for goals), `item_id`, `wikiUrl`.
3. **Settings**: new key `wiki_site` (default `'bgwiki'`) in `core/settings.py:DEFAULTS`, and a "Default wiki site"
   dropdown on the Settings page.
4. **Pages**:
   - Guide upgrades: new right-click menu with the three actions. Double-click opens the default site.
   - Inventory: the menu's single "Open BG-Wiki ↗" becomes the three actions. Double-click opens the default site.
   - Gear and Wishlist: the menu's "Open BG-Wiki ↗" becomes the three actions. **Double-click stays Edit.** Gear's
     bottom "Open BG-Wiki ↗" button becomes "Open wiki ↗" and uses the default site.
   - Guide panel: its link uses the default site.

### B. Purpose → Set → Version picker (Guide upgrades)

1. **Catalog fields.** Every entry in `gear_guides.json` → `sets[]` gains:
   ```json
   {"purpose": "Weapon skill", "target": "Savage Blade", "version": "Mid tier", "version_rank": 2, "note": ""}
   ```
   - `purpose` is one of this fixed list, shown in this order:
     Idle · Defense · Melee / TP · Weapon skill · Ranged · Precast · Midcast: healing · Midcast: enhancing ·
     Midcast: enfeebling · Midcast: nuking · Midcast: blue magic · Midcast: ninjutsu · Job ability · Pet ·
     Gear reference. ("Pet", for Blood Pacts and Ready moves, was added during the build: 21 SMN and 11 BST
     sets would otherwise have crowded Job ability.)
   - `target` is the specific use in plain words ("Savage Blade", "TP (max haste)", "Fast Cast", "Phantom Roll",
     "Tank", "AF +3").
   - `version` uses the guide's own words ("Dream tier", "Mid tier", "Entry level", "High", "ATK cap"), or `""` when
     the guide has only one. `version_rank` orders them best first (1 = best).
   - `note` holds the rest of a long title ("Telchine each augmented with 50 HP…"), shown in the caption.
   - AF / Relic / Empyrean reference sets (25 sets: RDM AF/Relic/Empyrean +1 to +4, BLU AF/Relic/Empyrean, etc.) go
     under **Gear reference**.
2. **`tools/classify_guide_sets.py`**: keyword rules plus an `OVERRIDES` table keyed by set ID for the titles the
   rules can't read. It must run again unchanged on a re-collected catalog (batch 4 adds all 22 jobs), and print
   every set it couldn't classify instead of guessing. Run it, commit the updated JSON, and write
   `docs/guide-set-groups.md` (job → purpose → target → versions) for Jason to check before the build is called
   done. Every set gets a purpose; there is no "Other" group.
3. **Toolbar** (replaces the single set dropdown): `Job ▾  Purpose ▾  Set ▾  [Dream tier | Mid tier | Entry level]  Character ▾`
   - Purpose lists only purposes this job has, with counts: "Weapon skill (28)".
   - Set lists that purpose's targets, A–Z.
   - Version buttons show only when the target has more than one version, ordered by `version_rank`. The best
     version is selected by default.
   - One plain line under the table says what the purpose is for, e.g. "Worn while casting Cure spells (GearSwap
     midcast)." No per-file set names in this batch.
   - The last purpose/set/version per job is remembered in settings key `guide_picks`.
4. **Unchanged**: Track this set, Set augment target…, Open equipment set ↗, Open job guide ↗, the inventory check
   logic, and `guide_requirements` keys (`<job>-<set id>-<item id>`), so saved augment targets survive.

## Acceptance Criteria

1. On Guide upgrades, Gear (all three tabs), Wishlist and Inventory, right-clicking an item row shows "Open on
   BG-Wiki ↗", "Open on FFXIAH ↗" and "Open on FFXIclopedia ↗", and each opens the matching URL from `item_urls`.
2. Double-clicking a row on Guide upgrades or Inventory opens the default site. Double-clicking on Gear or Wishlist
   still opens Edit.
3. Settings → Default wiki site changes which site double-click and Gear's "Open wiki ↗" use, and survives an app
   restart.
4. For an item with a known `item_id`, the FFXIAH link is `https://www.ffxiah.com/item/<id>`.
5. A row whose `wikiUrl` is not a bg-wiki.com URL never opens that URL from a BG-Wiki action.
6. All 376 catalog sets have a `purpose` from the fixed list and a non-empty `target`. A test fails if any set is
   missing either.
7. For COR, the Purpose dropdown shows at most 10 entries, and no Set dropdown for any job shows more than 15.
8. Choosing COR → Weapon skill → Savage Blade shows version buttons for each Savage Blade version in the guide, and
   picking one loads that set's items into the table.
9. A saved augment target recorded before this change still shows on the same item after it.
10. `py -3 -m pytest -q` passes with no skips (lupa installed), including the new tests.

## Testing Plan

| Layer | What | Count |
|-------|------|-------|
| Unit (`tests/core`) | `item_urls`: ID vs. search URL, bg-wiki guard, empty name | +4 |
| Unit (`tests/core`) | Catalog: every set has purpose/target; purposes in fixed list; versions ranked | +3 |
| UI (`tests/ui`) | Item-link menu on each of the 4 pages; double-click behavior per page | +5 |
| UI (`tests/ui`) | Picker: COR purposes and counts, Savage Blade versions, set loads, picks remembered per job | +4 |
| UI (`tests/ui`) | Settings default site persists | +1 |
| Manual | Jason checks `docs/guide-set-groups.md` and tries the picker on BLU, COR, RDM, SMN | — |

## Rollback Plan

Revert the commit. The catalog changes only add fields, and the new settings keys are ignored by older builds. No
player data is migrated.

## Effort Estimate

| Part | Human | CC |
|------|-------|----|
| `item_urls`, `item_links.py`, 4 pages, Settings | ~1 day | ~30 min |
| Classifier, overrides for the 31 unread titles, review list | ~1 day | ~45 min (+ Jason's review) |
| Picker UI | ~1 day | ~45 min |
| Tests | ~0.5 day | ~20 min |

## Files Reference

| File | Change |
|------|--------|
| `vanadiel_nexus/core/wiki.py` | Add `SITES`, `item_urls` |
| `vanadiel_nexus/ui/item_links.py` | New: shared menu actions and default-site open |
| `vanadiel_nexus/core/settings.py:6` | Add `wiki_site`, `guide_picks` defaults |
| `vanadiel_nexus/ui/pages/settings.py` | Default wiki site dropdown |
| `vanadiel_nexus/ui/pages/guides.py` | Purpose/Set/Version picker, menu, double-click |
| `vanadiel_nexus/ui/pages/gear.py:94,310,313` | Menu actions, "Open wiki ↗" button |
| `vanadiel_nexus/ui/pages/wishlist.py:207,215` | Menu actions |
| `vanadiel_nexus/ui/pages/inventory.py:163,171` | Menu actions, double-click |
| `vanadiel_nexus/ui/guide_panel.py:130` | Default site |
| `vanadiel_nexus/resources/gear_guides.json` | Add purpose/target/version/version_rank/note to all 376 sets |
| `tools/classify_guide_sets.py` | New: one-time classifier with overrides |
| `docs/guide-set-groups.md` | New: review list for Jason |
| `tests/core/test_wiki.py`, `tests/core/test_gear_guides.py`, `tests/ui/…` | New tests |

## Out of Scope

- Creating, editing or removing sets, the in-game equipment layout, item icons, shared / job-specific /
  conditional sets, and any change to GearSwap files (batch 3, Set manager).
- Collecting guides for all 22 jobs, keeping them current for every player, and fixing SCH's 2 sets (batch 4,
  Guide catalog). SCH's source is page 103 of a forum thread rather than a guide page, so only the 2 sets linked
  on that one page were collected.
- Allakhazam or other extra sites.
- The G13 page (batch 2).
