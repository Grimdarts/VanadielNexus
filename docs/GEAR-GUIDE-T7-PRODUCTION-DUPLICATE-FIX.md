# T7 production duplicate-copy fix (2026-11-05)

Jason authorized this in chat ("1. Yes fix.") as a narrow production data edit. It is not the T8 replacement.

## What changed

`vanadiel_nexus/resources/gear_guides.json`: SHA256 `54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85` -> `b57b6bb34bc0e969140610fa623efe00fbaef3379c23ab00d9a29db7b6be4300` (2894204 -> 2900403 bytes, LF).

Ten BST guide sets selected two copies of an item in their source grid but recorded one. The v1 app counts repeated item IDs as required copies, so owning one copy wrongly showed the item as complete. Each fix inserts a deep copy of the existing record directly after it.

| Set | Added second copy | Evidence |
|---|---|---|
| 264975 | Stikini Ring +1 (ring1/ring2) | gear-guide-t7-bst-second-pass-slots.json |
| 302857 | Bird Earring (ear1/ear2) | gear-guide-t7-bst-second-pass-slots.json |
| 371161 | Chirich Ring +1 (ring1/ring2) | gear-guide-t7-bst-second-pass-slots.json |
| 333993 | Kumbhakarna (main/sub) | gear-guide-t7-bst-second-pass-slots.json |
| 264979 | Skullrender (main/sub), Varar Ring +1 (ring1/ring2) | gear-guide-t7-bst-second-pass-slots.json |
| 378247 | Chirich Ring +1 (ring1/ring2) | gear-guide-t7-bst-other27-audit.json |
| 333131 | Stikini Ring +1 (ring1/ring2) | gear-guide-t7-bst-other27-audit.json |
| 339931 | Kumbhakarna (main/sub) | gear-guide-t7-bst-other27-audit.json |
| 339932 | Kumbhakarna (main/sub) | gear-guide-t7-bst-other27-audit.json |
| 365917 | Levia. Ring (ring1/ring2) | gear-guide-t7-bst-other27-audit.json |

11 copies across 10 sets. The other 366 sets, top-level fields and set order are byte-identical. No schema, code, validator or tool change.

## Validation

- Independent gap recomputation over all 48 BST node 227 grids: exactly these 10 sets / 11 copies; no other gap.
- New `tests/core/test_guide_production_duplicate_fix.py` (4 tests), including a fictional-inventory check that one Chirich Ring +1 now shows 1/2 Missing and two show 2/2 Owned.
- Updated two tests that pinned the old production hash (other27, scope-fallback) to follow the authorized successor; the historical packets are unchanged.
- Isolated native runs with Jason's Python 3.14, fictional Windower and no inventory seeding: focused 709/0/0 in 59.98s; full 1505/0/0 in 166.06s.
- Readback from the backup bytes: 53/53 (`catalog/gear-guide-t7-production-duplicate-fix-readback.json`).

## Limits

- Only BST's 48 FFXIAH grids were compared copy-by-copy with production. Other jobs' v1 sets were not; the T8 replacement supersedes them.
- Track-set still adds one wishlist row per item ID, and a saved augment target keyed by item ID applies to both copies (unchanged behaviour).
- Not committed, pushed, built or released. Offline checks do not establish ownership/bags, caps/totals, HP preservation, current BiS or live acceptance.

## Jason's decisions recorded the same day

1. Duplicate copies: fix now (done here).
2. Next slice: BRD; all jobs to be finished.
3. Outdated versions: Jason does not want outdated info that causes confusion. The BRD slice designs hiding retired revisions; implementation follows as its own slice and goes on the release test checklist.
4. Replacement: after T7, replace the production guide file with the complete, gap-free worked-out sets.
5. After T7: deliver an updated checklist of every system and update Jason must test before a public release; test, adjust, then ship.
