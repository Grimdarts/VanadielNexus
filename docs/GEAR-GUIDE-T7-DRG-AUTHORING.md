# T7 DRG — bounded initial candidate milestone

2026-11-05. Claude handled DRG directly in the existing checkout, assigned by
Jason while Nova was paused for its usage reset. Nova did not run concurrently;
Vesper remained unassigned; no other agents, worktree or concurrent integration.

**15 complete attributed Nexus compositions cover all eight actual DRG priority
rows in bounded Shining One/Utu Grip contexts.** This closes the DRG initial-pass
gap left by the 2026-11-04 evidence checkpoint (`GEAR-GUIDE-T7-DRG.md`), which is
preserved byte-identical together with its four `gear-guide-t7-drg-*` packets.
It does not certify complete job, weapon, tier, action, buff, wyvern or encounter
coverage.

Read the four new packets in `docs/catalog/gear-guide-t7-drg-authoring-*`:
definitions with original/current row reconciliation; observations; independent
item evidence; and readback with exact validation counts and preservation results.

Candidate: **469 sets / 480 historical revisions / 967 sources**. There are
**461 effective recommendations**, versus 472 stored verified flags including
11 withdrawn BRD encodings; eight unresolved originals remain unchanged.
Coverage: **225 rows / 195 included / 30 gaps across three jobs / zero N/A**.
Only the eight DRG rows changed. Resources: **766**, retaining all 739 previous
records and descriptions; 27 independently checked DRG items appended. Hands:
**43 / hands.2026-11-05.v16**, unchanged: Shining One 21883 (two_handed) and
Utu Grip 22212 (grip) were already reviewed records, so nothing was appended.

Resource fingerprint remains
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.
Protected production SHA256 remains
`54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85`.
Four upstream resource hashes and the public native decoder bytes are unchanged.

## What unblocked DRG

The checkpoint stopped because BG-Wiki returned 403 to the web reader and
browser automation was disabled for Nova. This session's built-in browser could
render BG-Wiki `/ffxi/` pages normally. The
[Community Dragoon Guide](https://www.bg-wiki.com/ffxi/Community_Dragoon_Guide)
rendered with its own `wgRevisionId` **780419** (footer 7 October 2026 18:06).
The `index.php?oldid=780419` permanent link hit a Cloudflare bot check (HTTP 403);
it was **not** completed or bypassed, so revision identity rests on the rendered
page's own revision id. No source access failure is marked N/A.

## Evidence and source distinctions

The guide holds 80 `table.EquipmentSet` grids; nine Galkapryme grids are empty
placeholders and older Sulevia/Flamma progression grids were not selected.
Nineteen scoped grids (TP Endgame/Pre-Ody, Boposhopo Standard TP/DT swaps/
Stardiver/Impulse Drive/Camlann-Sonic/Jump/Spirit and Soul Jump swaps,
Galkapryme DT/Acc/MEVA/Jump, Utility Call Wyvern/Spirit Link/Healing Breath/
Steady Wing, community Sonic grid) plus four contextual scopes were transcribed
from the DOM's item-link titles and annotation tooltips. Nineteen grids do not
mean nineteen complete source loadouts: most utility grids are partial swaps.

Fourteen public mechanics pages were read with their own revision ids: Impulse
Drive 741100, Stardiver 741102, Sonic Thrust 741101, Shining One 766324, Jump
779909, High Jump 759209, Spirit Jump 759214, Soul Jump 710287, Call Wyvern
707585, Spirit Link 776970, Wyvern (Healing Breath) 763534, Restoring Breath
570441, Steady Wing 669559, Cure III 606019. Twenty-seven new item IDs were each
checked against a public BG-Wiki item page whose own FFXIAH exact-ID link equals
the local ID; slot, DRG eligibility and base text were compared. This differs
from Nova's FFXIAH-card method and is recorded as such. Previously verified items
reuse their existing source records.

The 2026-11-04 FFXIAH observations (node182, Sigurd thread, Smobo tables
including both conflicting Arke 402152 variants) remain in the checkpoint packet
and were not re-adjudicated.

## Actual rows and contexts

| Priority | Compositions | Bounded context |
|---|---|---|
| DT Idle | dt-idle | Disengaged defense; wyvern state, current/maxHP actual |
| Refresh Idle | refresh-idle | DRG99/WHM49 learned Cure III, positive usable MP and deficit; two Stikini copies |
| Engaged Balanced | engaged-balanced | Wyvern present (Sroda pet-alive effect); /SAM Hasso/haste actual |
| Engaged DT | engaged-dt | Boposhopo DT swaps on the balanced base; no cap |
| Engaged Accuracy | engaged-accuracy | Galkapryme accuracy grid; target evasion unknown |
| WS | impulse-drive, stardiver, sonic-thrust | Shining One grants Impulse Drive; Stardiver needs Martial Mastery + merit; Sonic Thrust native, area |
| Jumps | jump, spirit-jump, soul-jump | Gear at execution; Spirit/Soul bonuses only with wyvern present |
| Wyvern support / breath | call-wyvern, spirit-link, restoring-breath, steady-wing | Summon-time persistence, activation-time swap, breath-resolution gear, HP gear ticked before use |

All 15 declare all 16 canonical slots. Exact **Shining One 21883** main and **Utu
Grip 22212** sub stay fixed; range is deliberately empty. Shining One's TP-scaled
polearm WS critical bonus is a weapon property, not a universal hold-TP rule.
No Trishula Aeonic TP bonus, Ryunohige forced Jump critical, Rhongomiant,
Gungnir or Gae Buide property is borrowed even where the source grid names those
weapons; those source mains are retained as observations.

Source +4 artifact/relic pieces were not transferred: exact +3 tiers are used
where the guide itself shows +3 elsewhere (Ptero. Brais +3 in Pre-Ody and
Galkapryme, Vis. Fng. Gaunt. +3 in Galkapryme Jump). BG's Jump-family pages print
the same All Jumps TP bonus for Vishap +3 and +4, but other stats differ; no
parity claim is made. Ranks (R15/R20/R25), paths and random augments in source
tooltips are not inherited; Gleti, Coiste Bodhar, Dgn. Collar +2 and Pel.
Earring +2 are base only. Varar Ring +1 (pet/master applicability) is replaced by
Chirich Ring +1 and attributed as a Nexus choice. Valorous Greaves (random
augments) in the Soul Jump swap are not invented; Ostro Greaves stays.

Five Brigantia's Mantle builds are distinct literal copies: STR/DA, DEX/DA,
DEX/STP, STR/WSD and STR/DA-WS. The guide's thread stat often reads "Dex/Str";
that ambiguity stays in the observation and a single literal stat is selected.
The breath set uses an **unaugmented** Brigantia: the Wyvern page lists base
Brigantia at 38/256 enhances-breath and Ptero. Armet +3 at 72/256, which already
exceed the 96/256 cap, so Glassblower's Belt and the augmented Updraft Mantle are
not needed. No healing amount or cap position is certified.

Wyvern-only card lines are never counted as master stats. Call Wyvern trait
modifications persist from summon until the wyvern dies, is dismissed or the DRG
zones. Steady Wing and Healing Breath recovery scale with wyvern max HP, and HP+
gear only counts after a tic with it equipped. Healing Breath triggers on a
defensive-wyvern spell below the real HP threshold, or by Restoring Breath
regardless; the Vishap Armet midcast trigger trick is a declared limit.

## Validation and preservation

Presave **15 passed / 0 failed / 0 skipped in 0.82s**, repeated before each save
(0.74s, 0.75s). Focused **542 passed / 0 failed / 0 skipped in 38.90s**. Full
isolated native **1356 passed / 0 failed / 0 skipped in 136.61s**.
**30 independent readback checks passed.** Whole-candidate actual-resource
preparation and append-only `save_candidate` passed.

The first focused run had **538 passed / 4 failed / 0 skipped in 38.59s**: the
WAR/DRK/MNK/PLD batch tests expect the token `all22jobs` in `delivery_status`, and
the first save wrote `all-22-jobs`. Only the status text was corrected and the
candidate re-saved deterministically from the pre-edit baseline (revision ids are
content digests and did not change); no test or validator was weakened. Prior
batch tests changed only in aggregate counts, the DRG gap→included assertions and
the authored-job lists, enforced by an independent readback check.

359 pre-edit byte backups, the hash manifest and all task scripts/logs are under
`.t7-drgc-checks/`. Launchers use the known Python 3.14 executable, DRG-local
TEMP/TMP/VN_DATA_DIR/basetemp, fictional Windower discovery and disabled inventory
seeding. No source/player Lua executed, no inventory loaded. Branch
`codex/sets-copy-fixes-review` and HEAD `8f91ca164bd6737a4ad87185656eb96fcc1d45d4`
preserved. No worktree, switch/reset/stash/clean, commit, push, build, install,
release, production replacement, migration, game command or Lua activation.

## Remaining work and stop

Declared DRG limits: other weapons and stages (Trishula, Ryunohige, Rhongomiant,
Gungnir, Gae Buide, Naegling/Savage Blade, Malignance Pole, Reikikon) and their
WS (Drakesbane, Camlann's Torment, Geirskogul, Diarmuid, Raiden Thrust,
Cataclysm, Judgment, Retribution); Angon, Ancient Circle, Dragon Breaker, Spirit
Surge, Fly High, Deep Breathing, Smiting Breath, Super Jump, Removal Breath and the
Healing Breath midcast trigger; fast cast/SIRD and magic evasion; wyvern-absent
variants of every row. These are later review obligations, not waived.

Finish the remaining initial passes FIRST (BST 11, PUP 10, DNC 9 gaps), then the
second pass across **all 22 jobs** for issues affecting **any job**. Not started.
BRD withdrawn encodings and successors retained; runtime retirement
unimplemented. All declared issues deferred, not resolved or waived. No HP
preservation, caps/current BiS, ownership/bags or human/frozen/live acceptance
follows from offline composition verification.

**BST** remains the next unattempted initial job. `GEAR-GUIDE-T7-BST-START.md` and
the standalone `GEAR-GUIDE-T7-NEXT-JOB-PROMPT.md` were refreshed with this
baseline. **STOP AFTER DRG AND THE COPYABLE PROMPT.**
