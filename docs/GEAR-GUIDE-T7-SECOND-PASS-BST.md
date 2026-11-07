# T7 second pass — first bounded BST evidence slice

2026-11-05. Nova only, in the existing checkout/current chat; Jason confirmed no other writer. DNC's missing independent closeout is now complete: 55 checks, with its historical tests distinguished from fresh runs. See gear-guide-t7-dnc-readback.json and .t7-second-pass-checks/finish_dnc_readback.py. The original DNC report and packets remain unchanged.

The all-22-job inventory is delivered in SECOND-PASS-INVENTORY.md and catalog/gear-guide-t7-second-pass-inventory.json. It contains 493 classified review entries, not 493 product defects: 88 declared deferrals, 399 partial-source/access boundaries, three fixable-now items (including completed DNC closeout), and three historical issues not reproduced. All 23 reports and 91 then-present job packets were parsed in full. Precise source-scope JSON path clarifications are appended in the BST review packet rather than rewriting the inventory.

## Fixed in this evidence slice

The original BST report and 21 scoped list observations incorrectly denied slot positions on FFXIAH item-set pages. The new gear-guide-t7-bst-second-pass-slots.json records 21 exact original 16-cell equipboxes: **336 cells / 275 selected / 61 source omissions**. Each successor identifies the retained prior key/hash, current URL, retrieval timestamp, raw HTML hash, page update note, ordered macros and placeholder numbers. All 21 grids agree with their Equipment Macros. Empty eqN cells remain source omissions.

Node 227 currently reports Date Last Modified 2026-06-25 20:01:27. FFXIAH supplies no revision id or HTTP Last-Modified here. Browser automation was disabled in Work settings; ordinary public HTTPS GETs succeeded. Raw original HTML and response metadata are retained under .t7-second-pass-checks/bst-source-html/. No browser/window/tab was opened and no bot check or setting change occurred. No BG page was newly read in this slice; earlier BG revisions retain historical scope.

Set 302857 has **one Kaidate in sub**, while its ordered macros repeat the same sub command twice. The old list's extra shield entry must not imply two simultaneous copies. Its two Bird Earrings occupy separate ear cells. Set 264975 has **two distinct Stikini Ring +1 cells**; the existing Nexus Refresh already requires two. Twenty of 21 old item multisets match the grids; the repeated Kaidate accounts for the one discrepancy. Historical upstream changes were not established. `set_note_changed` only compares current note text with earlier sometimes-abbreviated summaries.

Nineteen explicit comparisons reconcile the captured source grids with the 14 existing BST Nexus compositions. Slots, omissions and substitutions are recorded separately; source exactness is not inferred from a matching item multiset. No new gear/resource/hand/augment requirement or coverage disposition was authored. Candidate/resources/hands remain byte-identical; there was **no candidate save**, so no redundant save_candidate transaction or count-only prior-test updates were needed. Whole actual-resource preparation still passes.

## Unresolved and next boundary

The external source corrections have **not yet been propagated into candidate source records or successor revision provenance**. That is the next bounded BST slice, with all presave/history/test gates. In particular, pet-accuracy's old rationale says axes were listed without hands; 337064/347643 actually specify Telopanos main / Spalirisos sub, reversed deliberately by Nexus. Engaged-balanced's “identical” source claim also needs clarification because node 381576 and Nexus swap Sherida/Telos ear sides. These are attribution corrections, not established gear-legality failures. Existing immutable revisions are not rewritten here.

The other 27 node-linked sets and all original BST weapon/WS/pet/action/augment/HP/cap limits remain deferred. The inventory also flags SMN's accepted common master-engaged obligations as explicitly unclaimed and absent from dedicated matrix rows; no new included rows were fabricated. BRD runtime retirement and every other job's recorded limitations remain open. DRG's final 15-composition authoring supersedes the old zero/eight-gap checkpoint; both artifact sets are preserved.

## Fresh validation

- New source/inventory regressions: 26 passed / 0 failed / 0 skipped, 0.25s.
- Independent literal fictional BST augments: 11 passed / 0 failed / 0 skipped, 0.75s.
- Independent DNC base-copy/literal boundary: 5 passed / 0 failed / 0 skipped, 0.75s.
- Fresh focused authoring/all initial job batches plus second-pass checks: 635 passed / 0 failed / 0 skipped, 52.37s.
- Fresh full native suite: 1449 passed / 0 failed / 0 skipped, 148.56s.

Every run uses unique task-local TEMP/TMP/VN_DATA_DIR/basetemp, a real-file launcher, fictional Windower discovery and disabled inventory seeding with the explicit native Python 3.14 path. The successor readback packet records independent raw-HTML parsing, protected-byte/history/resource checks, exact log hashes, whitespace and line-ending checks. Task-script checks initially caught two local assumptions (normalized subprocess log hash versus CRLF bytes; BST job id 9 versus DRK 8); only new task scripts were corrected. No canonical artifact or validator was changed to make them pass.

Baseline remains 514 sets / 525 revisions / 1271 sources; 517 stored flags / 506 effective recommendations / 11 withdrawn BRD / eight unresolved originals. Coverage 225 included / zero matrix gaps / zero N/A; resources 859; hands 55 / v19. Production and resource fingerprint unchanged. 416 pre-edit byte backups and all scratch are preserved. Branch codex/sets-copy-fixes-review and HEAD 8f91ca164bd6737a4ad87185656eb96fcc1d45d4 preserved.

Stop after this inventory and bounded evidence slice. NEXT-JOB-PROMPT.md continues BST provenance integration in this same chat; no automatic chain. No production, commit/push/build/install/release/migration, T8/T9, game command, player Lua execution/activation or inventory loading. Offline checks do not establish complete job coverage, ownership/bags, caps, HP preservation, current BiS or human/frozen/live acceptance.
