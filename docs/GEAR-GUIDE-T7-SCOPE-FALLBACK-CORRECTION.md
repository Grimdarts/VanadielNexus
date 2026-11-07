# T7 second pass - scope-source fallback correction (BST/PUP)

2026-11-05. Claude alone in the same existing checkout. Jason asked to fix what the other27 audit found. No agents, worktree, new window or concurrent integration.

## Found and fixed

Six candidate scope sources had an observation without a URL, and the original authoring fell back to kind bgwiki with a BG mechanics URL.

- **Confirmed, 2.** bst:t7:scope-bg-ready (BG Ready rev709840) and pup:t7:scope-bg-maneuver (BG Maneuver rev675700) name their own page.
- **Attribution defects, 4.** Each now has an append-only successor source and an explicit source-observation amendment; the observations themselves were correct and are unchanged.
  - bst community-guide -> https://www.bg-wiki.com/ffxi/Community_Beastmaster_Guide (rev745000).
  - pup node-inventory -> https://www.ffxiah.com/node/426 (71 linked sets, Date Last Modified 2022-11-26 03:56:43).
  - pup stage-conflicts -> node 426 as primary; the locator names BG All Jobs rev772450, BG Kenkonken (Level 119 III) rev778097 and BG String Theory rev689269. Kenkonken 18988 / Verethragna 19397 come from node 426's linked item-set pages, which were not re-read here.
  - pup automaton-actions -> https://www.bg-wiki.com/ffxi/String_Theory (rev689269), plus node 426's GearSwap "cannot predict or intercept" note.
- **Citation completion.** Engaged-accuracy's plural "node 227 AM3 grids" now also cites NIN AM3 378247 (both ring slots Chirich Ring +1 26182), via a new grid source.

Two cited records received provenance-only successor revisions with authoring retirement links: nexus:pup:overdrive-sharpshot (version 2) and nexus:bst:engaged-accuracy (version 3). Selected gear, requirements, verification, contexts and coverage are identical. No automatic saved-target retargeting or runtime retirement.

## Evidence

Node 426: ordinary public GET, 200, raw HTML retained under .t7-scope-fallback-checks/source-html/; FFXIAH exposes no revision id or Last-Modified header. The two BG pages returned 403 to direct GET. They were then read with ordinary navigation in the desktop built-in browser, with no challenge shown or touched. Both current revisions equal the recorded ones: Community Beastmaster Guide 745000 (edited 22 August 2025) and String Theory 689269 (edited 26 September 2023). Content-text hashes are recorded; BG raw HTML bytes were not retained.

## Not fixed: production duplicate copies

The five protected production records that hold one copy where the source selects two (378247, 333131, 339931, 339932, 365917; also 264975, 302857, 371161, 333993, 264979 among the earlier 21) are unchanged. Changing vanadiel_nexus/resources/gear_guides.json is a production replacement, which the standing T7 rules forbid. The v1 records have no quantity field, and no production set repeats an item ID, so a fix also needs an app/schema decision. Recorded in catalog/gear-guide-t7-bst-other27-audit.json only.

## Candidate and validation

Candidate **520 sets / 547 revisions / 1331 sources**; 539 stored verified flags include 27 retired (11 BRD, 15 BST, 1 PUP); **512 effective / eight unresolved**. 231 included / zero recorded gaps / zero N/A across all22jobs is not full T1/job coverage. Resources 863; hands 55 / hands.2026-11-05.v19; fingerprint unchanged. Candidate SHA256 ca787650965d61046e91323bd1e1c991d9245f4b2d7d340935159afc9f511926 (prior 9e721bbd8a8488ac7ca15f71363700a763ba09721b643277b7c9f00ecab18bf3). Production SHA256 54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85 unchanged.

Presave **40 passed / 0 failed / 0 skipped** (BST 11, DNC 5, SMN 7, Hasso 6, this slice 11), with independently typed fictional literal strings. Whole-candidate actual-resource prepare passed, then a single append-only save_candidate. Fresh focused native **687/0/0 in 64.86s**; fresh serial full native **1501/0/0 in 160.50s**; real-file Python 3.14 launchers, unique TEMP/TMP/VN_DATA_DIR/basetemp, fictional Windower discovery, inventory seeding disabled.

Diagnostics retained: the test-count updater twice stopped on its own line-ending assertion before writing anything (test_guide_authoring.py is CRLF). An initial focused run had 686 passed / 1 failed: my earlier other27 test assumed no later revisions; it was rescoped to the records present at that batch. The first full native run had 1499 passed / 2 failed in 164.10s. Both failures were tests/ui/test_item_links.py tests hitting a Windows PermissionError on the atomic replace of a temporary fictional settings.json inside their own temp folder; this is the same transient lock seen in the BST provenance slice, and no catalog behaviour is involved. Both passed unchanged in an isolated rerun (2/0/0, 0.77s), and the full result above is the later fresh serial run. The lock holder was not identified. 23 prior tests changed only counts, the retired total, the hash chain and that scoping; one new regression file. No application, validator or tool change. 413 pre-edit byte backups. Readback: catalog/gear-guide-t7-scope-fallback-readback.json.

STOP after this correction and the successor prompt. No production replacement, commit/push/build/install/release/migration, T8/T9, game command, Lua execution or activation, inventory loading or settings change.
