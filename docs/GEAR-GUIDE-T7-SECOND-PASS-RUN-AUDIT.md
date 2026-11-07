# RUN second pass - correctness and conflict audit (2026-11-05)

Jason clarified that this slice should check correctness and conflicting information in existing guide sets. Nova worked alone in the existing checkout, with no other writer per Jason. No additional action or weapon variants were requested.

**The existing 20 RUN loadouts passed the bounded correctness checks. No gear, slot, literal augment or source-grid correction was required.** This does not establish complete RUN coverage or refresh inaccessible BG mechanics. One stale delivery-status statement was corrected, retaining its prior text as labeled history.

## Evidence and findings

- Fresh ordinary public GETs of [Destiny's Device node 397](https://www.ffxiah.com/node/397), all 20 previously selected item sets and all 43 exact-ID public cards succeeded. Raw bytes and response metadata are retained under `.t7-run-audit-checks/source-html/`; the canonical audit packet carries source URLs, hashes and exact grids. Node's displayed modification timestamp is 2026-03-04 09:06:25, not proof that every section is current.
- All 320 source cells and all competing macro values match the immutable RUN observations. Source Erilaz Earring +1 25547 remains in the wrong ear in 372679/372997; it is observation-only and absent from recommendations. The final Gurebu ring in 372999 remains distinct from Nexus's explicitly attributed two-Stikini choice. Repeated/competing macros are not additional physical copies.
- Every saved RUN composition still matches its definition and validates against actual local public resources and reviewed hands. All 863 detached item records/descriptions, upstream resource hashes and fingerprint match. All 43 current public card names and RUN eligibility match the historical card ledger.
- Seven context groups independently cover all 20 sets: defensive/recovery/engaged, the two weapon skills, enmity and casting phases, enhancing/self recipients, Vallation/Valiance recipients, Gambit/Rayke, and Vivacious Pulse. The packet records each review. Source caps, merit maxima, random rolls and guaranteed recovery/status outcomes were not transferred into the recommendations.
- Current BG `/ffxi/Community_Rune_Fencer_Guide` fetch returned 403. Ordinary Chrome failed; after resetting the browser session, the built-in browser also reported local browser use disabled. No settings or challenge was changed. Historical rendered BG revision 781614 remains historical evidence; its first-save/late-recovery history is preserved. Current BG mechanics refresh is **source-limited**, not passed or N/A.
- The candidate delivery note incorrectly still described runtime retirement as open and an old SMN stop boundary. A current status now precedes the verbatim historical note, recording implemented retirement, pending human checks and Jason's release scope. `prepare` dry run and `save_candidate` passed. Only `delivery_status` changed; every set, revision, source, amendment, batch, coverage row and other field is identical. `gear-guide-t7-run-status-correction.json` records the hash successor; the existing hash-chain test now reconstructs the predecessor byte hash by reversing only this metadata change, preserving every earlier chain assertion.

## Scope and open items

All 29 historical RUN register entries have an explicit current disposition in `catalog/gear-guide-t7-run-second-pass-audit.json`; the original inventory and packets are unchanged. Existing action contexts were checked, not expanded. Lunge/Swipe, One for All, Battuta, Liement, Pflug received gear, Embolden and Epeolatry/alternate weapon contexts remain unauthored/pending after 2.2.0. HP-preserving transitions remain live-gated. DRG/PUP/DNC/ALL22 and all other declared limitations remain open; this is not a waiver or full-job acceptance.

Candidate: 520 sets / 547 revisions / 1331 sources / 27 retired / 512 effective verified / eight unresolved originals. Resources 863; hands 55/v19. Candidate SHA256 `d0b3af52d96f01ae2fe721ac9ef83d8150045a93c61d6f8a7c1c17a395b61f1a` (metadata-only successor of ca787650965d61046e91323bd1e1c991d9245f4b2d7d340935159afc9f511926). Production remains unchanged at `b57b6bb34bc0e969140610fa623efe00fbaef3379c23ab00d9a29db7b6be4300`.

## Validation

- Independent fictional decoded-augment checks: 7 passed / 0 failed / 0 skipped, 0.04s.
- Final focused native: 811 passed / 0 failed / 0 skipped, 69.59s (0:01:09).
- Final full native: 1536 passed / 0 failed / 0 skipped, 158.52s (0:02:38).
- Initial focused 811/0/0 in 69.47s and full 1536/0/0 in 153.55s are retained as pre-final-status runs. Full-suite execution overlapped the metadata-only status correction; only the final isolated rerun counts as final-source validation.
- The first post-status focused run was 810 passed / 1 stale hash-chain assertion failed / 0 skipped (69.72s). An unnecessary full rerun was interrupted before completion when that focused failure was inspected; it has no final pass count. The hash-chain expectation was extended using explicit correction evidence, not relaxed.
- That extension initially omitted its local candidate variable: the next focused run was 810 passed / 1 NameError failed / 0 skipped (68.64s). The test-only error was corrected before the final successful runs.
- Launchers are real files using Python 3.14 at the documented native path, unique TEMP/TMP/VN_DATA_DIR/basetemp, fictional Windower discovery and inventory seeding disabled. Whole-candidate preparation and byte/history readback are separate from tests. `gear-guide-t7-run-second-pass-readback.json` records preservation checks and `git diff --check`.

466 pre-edit file backups retain their hashes and original line endings. One existing test was extended for the metadata successor; no application code, gear record, production bundle, Windower/player Lua, inventory or settings changed. No commit/push/build/install/release/migration, live command or activation occurred. Stop here. Next is production replacement only when Jason starts that separate slice; integration/RC and pre-release checklist follow as their own slices. World Map is excluded.
