# T7 PUP — bounded initial candidate milestone

2026-11-05. Claude handled PUP directly in the existing checkout, assigned by
Jason, in the same chat that finished BST. No other agent wrote to the checkout
(last write before this task was the BST finalize at 09:12); Vesper unassigned; no
other agents, worktree or concurrent integration.

**16 complete attributed Nexus compositions cover all ten actual PUP priority
rows** on eight fixed hand-to-hand weapon/animator pairs. This is not complete
job, weapon, head, frame, attachment, automaton-WS, Overdrive, tier, buff or
encounter coverage.

Read the four packets in `docs/catalog/gear-guide-t7-pup-*`: definitions with
original/current row reconciliation; observations; independent item evidence;
readback with exact validation counts and preservation results.

Candidate: **499 sets / 510 historical revisions / 1127 sources**. There are
**491 effective recommendations** versus 502 stored verified flags including 11
withdrawn BRD encodings; eight unresolved originals unchanged. Coverage: **225
rows / 216 included / 9 gaps in one job (DNC 9) / zero N/A**. Only the ten PUP
rows changed. Resources: **828**, retaining all 802 prior records and
descriptions; 26 independently checked PUP items appended. Hands: **53 /
hands.2026-11-05.v18**; the 48 prior records are AST-identical and five reviewed
exact hand-to-hand records were appended: Kenkonken 20511 (iLevel 119 III),
Xiucoatl 21526, Ohtas 20535, Gnafron's Adargas 20542 and Denouements 20516.
Godhands and Sakpata's Fists were already reviewed records.

Resource fingerprint remains
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.
Production SHA256 remains
`54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85`.

## Sources

- [FFXIAH node 426, PUP Gearsets](https://www.ffxiah.com/node/426) (Falsetto,
  collaborator Aerix), "Last Update: October 20th 2022", footer last modified
  2022-11-26. All 71 linked item sets were fetched. Each set page has a 16-cell
  equipbox in FFXI slot order with numbered placeholders for empty slots, so 21
  sets are recorded as slot grids. All 21 were re-fetched and matched cell for
  cell, and every placeholder number equalled its slot position.
- [BG All Jobs Gear Sets/Puppetmaster](https://www.bg-wiki.com/ffxi/All_Jobs_Gear_Sets/Puppetmaster)
  rendered wgRevisionId **772450** (footer 13 July 2026): master WS and Kenkonken/
  Varga TP grids only, Neo Animator locked; six grids transcribed.
- [BG String Theory](https://www.bg-wiki.com/ffxi/String_Theory) rendered **689269**
  (26 September 2023): roles, support jobs, automaton WS, animators (Animator P +1
  is Su2) and 40 option grids; none transferred verbatim.
- Mechanics and weapon pages with their own revision ids: Kenkonken (Level 119 III)
  778097, Xiucoatl 627527, Ohtas 582433, Gnafron's Adargas 658748, Denouements
  586896, Sakpata's Fists 665669, Neo Animator 777476, Animator P +1 777474,
  Animator P II +1 576579, Stringing Pummel 741058, Asuran Fists 740989, Howling
  Fist 741054, Shijin Spiral 741055, Raging Fists 740987, Maneuver 675700, Overdrive
  661623, Automaton 777440, Activate 588463, Deploy 763627, Kara. Earring +2 664277,
  Hoxne Earring 775328, Visucius's Mantle 568491.
- 26 new item IDs checked: 25 against public BG item pages whose FFXIAH exact-ID
  link equals the local ID, and Buffoon's Collar +1 against FFXIAH's exact item
  page 16282, because its BG page has no FFXIAH link. No index.php oldid link was
  requested; no Cloudflare/bot check was completed or bypassed.

## Weapon/animator pairs and recipients

| Pair | Main / range | Used for |
|---|---|---|
| H | Kenkonken 20511 / Animator P +1 21457 | DT idle, master refresh, hybrid, maneuver |
| M | Kenkonken 20511 / Neo Animator 21433 | master engaged, Stringing Pummel, Asuran Fists |
| O | Ohtas 20535 / Animator P +1 | pet-only melee |
| R | Xiucoatl 21526 / Animator P II +1 21459 | pet-only ranged (Sharpshot) |
| W | Xiucoatl 21526 / Animator P +1 | automaton WS, Overdrive (Sharpshot) |
| T | Gnafron's Adargas 20542 / Neo Animator | automaton durability |
| C | Sakpata's Fists 21527 / Animator P II +1 | automaton magic |
| D | Denouements 20516 / Animator P II +1 | mage-automaton MP recovery |

Hand-to-hand occupies main with sub empty (the validator rejects any sub beside a
hand-to-hand main). The batch gate itself requires a reviewed exact main
classification, because the structural check only judges selected subs. Ammo is
deliberately empty: node 426's Automat. Oil +3 is a consumable, not an equipment
stat. "Automaton:" lines go only to the automaton. Generic "Pet:" lines are kept
as pet-labeled; their automaton applicability is the source guides' claim, not
Nexus-certified. Neither kind is added to master totals. Changing main or animator
resets master TP, so pet-only rows assume the master is not building TP.

## Actual rows

| Priority | Compositions | Bounded context |
|---|---|---|
| DT Idle | dt-idle | Node HP/DT/MEVA 352987 exactly (node main empty; Nexus pair H) |
| Refresh Idle | refresh-idle, automaton-refresh-idle | Master: PUP99/WHM49 positive subjob MP and deficit; Vrikodara, two Stikini, Fucho-no-Obi, Null Masque. Automaton: mage head; Denouements, Pitre Taj +3, Contriver's Cape |
| Master engaged Balanced | engaged-balanced | BG Kenkonken -25% DT grid; literal DEX/Acc-Atk/STP/DEX/PDT Visucius from node cape notes |
| Master engaged DT | engaged-dt | BG -50% DT grid (Alabaster, Karagoz Guanti +3) |
| Master engaged Accuracy | engaged-accuracy | Nexus Malignance accuracy alternative (Pup. Collar +2, two Chirich +1, Null Shawl) |
| Hybrid engaged | hybrid-engaged | Node Dual TP 353038; base Visucius (pet cape not inherited) |
| Pet engaged | pet-engaged-melee, pet-engaged-ranged, overdrive-sharpshot | Node Pet TP with Taeon slots replaced (base Taeon has no pet lines); node Pet Ranged TP exactly; Nyame OD (SS) with base Visucius for the unconfirmable Dispersal TP Bonus augment |
| Pet durability | pet-durability | Nexus automaton-durability set on the node Turtle Tank weapon/animator; base Rao (no pet lines without Path C) not borrowed |
| Pet actions | pet-ws, pet-magic, maneuver | Node Pet TP Bonus (Nyame) and Pet MACC; maneuver gear at JA use on the hybrid base (BG Maneuver threshold equipment) |
| WS | stringing-pummel, asuran-fists | PUP main; Stringing Pummel via Kenkonken/quest; Asuran Fists needs The Walls of Your Mind (Kenkonken does not grant it) |

All 16 declare all 16 slots (sub and ammo empty). Kara. Earring +2 sits in ear2 in
all of them because its text says "Right ear:". Source ranks, paths and random
augments (Odyssey R30, Nyame B/D, Ryuo A/C/D, Rao C, Taeon/Herculean randoms,
Anwig, Dispersal TP Bonus, pet capes) are not inherited. Three Visucius's Mantle
master builds are literal copies from node 426 notes (DEX/Acc-Atk/STP/DEX/PDT;
STR/Acc-Atk/Crit/STR/PDT; STR/Acc-Atk/WSD/STR/PDT). Double Attack resin capes are
not authored because the decoder's `"Dbl.Atk."` string has no percent and the
Ambuscade resin code is unconfirmed.

Source conflicts are kept: node 426 links Kenkonken as level-75 ID 18988 and
Verethragna as level-80 ID 19397. Node 352950 prints its cape as an aggregate
(STR+30/...) instead of the per-augment list. String Theory's turtle animator
differs from node 426. String Theory's refresh idle credits Denouements, whose
Refresh+4 is Automaton-labeled. Hoxne Earring is Mastery-rank dependent, so it is
not selected.

## Validation and preservation

Presave literal augment tests: **8 passed / 0 failed / 0 skipped in 0.76s**
(first run), and **8 / 0 / 0 in 0.74s** immediately before the single save
(rerun after a scope-key edit to the definitions). Before the first run, one
whitespace negative was rewritten as a positive assertion: `identity()` collapses
whitespace and casefolds.

Initial focused **570 passed / 16 failed / 0 skipped in 43.14s**: all 16
failures were one line of the new PUP batch test, which expected "never added to
master" while the context says "neither is ever added to master totals". Only that
expected phrase was corrected. Focused **586 passed / 0 failed / 0 skipped in
43.82s**. Full isolated native **1400 passed / 0 failed / 0 skipped in
139.12s** (1377 prior + 23 new PUP tests). **40 independent readback checks
passed**, covering protected bytes, history, resources, hands AST, line endings,
whitespace, recipients, literal copies and the successor prompt.

Prior batch tests changed only in aggregate counts, PUP gap→included, hands
48→53 (v17→v18, including the BST test's hands slice) and authored-job lists
(exact replacement table, enforced by readback). 372 pre-edit byte backups and all
task scripts/logs are under `.t7-pup-checks/`. No source/player Lua executed, no
inventory loaded. Branch `codex/sets-copy-fixes-review` and HEAD
`8f91ca164bd6737a4ad87185656eb96fcc1d45d4` preserved. Byte-identical: both DRG
artifact sets, all THF packets, the BST report, its four packets and BST-START,
PUP-START, World Map and the second-pass plan. No worktree,
switch/reset/stash/clean, commit, push, build, install, release, production
replacement, migration, game command or Lua activation.

## Remaining work and stop

Declared PUP limits (second-pass obligations, not waived): other master weapons
and stages (Godhands, Verethragna, Varga Purnikawa, Karambit, Condemners, Nibiru
Sainti, daggers) and WS (Howling Fist, Shijin Spiral, Raging Fists, Victory Smite,
Dragon Blow, Maru Kala, Evisceration, Aeolian Edge); specific heads, frames,
attachments and automaton WS (Bone Crusher, Arcuballista/Daze); Valoredge
Overdrive, Bruiser/Dual Tankmaton/Pet Enmity, pet curing/nuking/idle-precast,
Repair, Cooldown, Deus Ex Automata, Role Reversal, Ventriloquy, Tactical Switch,
master utility casting and MDT/kiting/regen idles; Taeon/Herculean/Rao/Odyssey/
pet-cape/Dispersal augments; pet haste caps, overload probability and HP
preservation. Second-pass observation for BST: its packets recorded node 227
item sets as unordered lists, though FFXIAH set pages carry slot grids. BST is
unchanged here.

Remaining initial queue: **DNC 9**. DNC is next and is the last initial pass. Then
the second pass across **all 22 jobs**; not started. BRD withdrawals retained;
runtime retirement unimplemented. `GEAR-GUIDE-T7-DNC-START.md` and the standalone
`GEAR-GUIDE-T7-NEXT-JOB-PROMPT.md` (start the next slice in the current chat) are
prepared. **STOP AFTER PUP AND THE COPYABLE PROMPT.**
