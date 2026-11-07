# T7 DNC — bounded initial candidate milestone (last initial pass)

2026-11-05. Claude handled DNC directly in the existing checkout, assigned by
Jason, in the same chat that finished PUP. No other agent wrote to the checkout
(last write before this task was the PUP finalize at 09:56); Vesper unassigned;
no other agents, worktree or concurrent integration.

**15 complete attributed Nexus compositions cover all nine actual DNC priority
rows** on one fixed dagger pair. This is not complete job, weapon, subjob,
haste-tier, WS, Waltz-variant, buff or encounter coverage.

Read the four packets in `docs/catalog/gear-guide-t7-dnc-*`: definitions with
original/current row reconciliation; observations; independent item evidence;
readback with exact validation counts and preservation results.

Candidate: **514 sets / 525 historical revisions / 1271 sources**. There are
**506 effective recommendations** versus 517 stored verified flags including 11
withdrawn BRD encodings; eight unresolved originals unchanged (including the
ten-slot DNC "DT Shell V" pilot). Coverage: **225 rows / 225 included / 0 gaps /
zero N/A**. Only the nine DNC rows changed. Resources: **859**, retaining all 828
prior records and descriptions; 31 independently checked DNC items appended.
Hands: **55 / hands.2026-11-05.v19**; the 53 prior records are AST-identical and
two reviewed exact one-handed dagger records were appended: Terpsichore 20584
(iLevel 119 III) and Twashtar 20587 (iLevel 119 III).

Resource fingerprint remains
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.
Production SHA256 remains
`54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85`.

## Sources

- [FFXIAH node 373, Dancer guide](https://www.ffxiah.com/node/373) (author
  kate99, collaborator SimonSes; the T1 note said Katriina/SimonSes), "Last
  Update: June 12, 2020", footer last modified 2022-10-17. All 58 linked item
  sets were fetched as 16-cell equipbox slot grids and later re-fetched: all 928
  cells matched, and every placeholder number equalled its slot position.
- [BG Community Dancer Guide](https://www.bg-wiki.com/ffxi/Community_Dancer_Guide)
  rendered wgRevisionId **774984** (footer 6 August 2026): 27 grids transcribed
  with their annotations, plus mechanics prose.
- [BG All Jobs Gear Sets/Dancer](https://www.bg-wiki.com/ffxi/All_Jobs_Gear_Sets/Dancer)
  rendered **772443**: recorded as a lead only (17 grids not transcribed; links an
  unread FFXIAH "Last Dance III" guide).
- Mechanics and weapon pages with their own revision ids: Terpsichore (Level 119
  III) 700774, Twashtar (Level 119 III) 713481, Waltz 774384, Curing Waltz 588493,
  Presto 640417, Quickstep 764050, Finishing Move 757034, Violent Flourish 698541,
  Reverse Flourish 774499, Climactic Flourish 752283, Striking Flourish 725963,
  Ternary Flourish 588514, Saber Dance 752275, Fan Dance 752276, Haste Samba
  588482, Spectral Jig 776116, Dual Wield 753673, Rudra's Storm 776638, Pyrrhic
  Kleos 741065, Moonshade Earring 777274.
- 31 new item IDs checked against public BG item pages whose FFXIAH exact-ID link
  equals the local ID; slot, DNC eligibility and description compared. No
  index.php oldid link was requested; no Cloudflare/bot check was completed or
  bypassed.

## Weapons, Dual Wield and recipients

Every composition keeps exact Terpsichore 20584 main and Twashtar 20587 sub, the
BG "TP Terpsichore" pair, so no swap resets TP. Range is deliberately empty and
ammo is used. Both hands are reviewed one-handed daggers, and the batch gate
requires both exact classifications because the structural check only judges
main/sub pairs. Dual Wield is explicit: native DNC trait by level (DNC80 IV 30%;
V 35% only with the actual 550 JP gift). Terpsichore's Pyrrhic Kleos grant and
extra Finishing Move are main-hand properties. Twashtar's Rudra's Storm grant is
not asserted for the sub hand, so Rudra's Storm needs actual access.

Waltz potency lines on the Dancer act for whatever target it heals. "Waltz
potency received" lines count only when the wearer is the recipient (self-target);
another target's own received gear and VIT apply. Step, Flourish, Samba and Jig gear
counts at use; the Daze, Finishing Moves and buffs persist by their own rules.
Finishing Moves, TP costs, Presto, Saber Dance (blocks Waltzes), Fan Dance (blocks
Sambas) and Climactic/Striking/Ternary Flourish (mutually exclusive) are explicit
inputs. Refresh Idle uses a declared DNC99/WHM49 context with positive usable
subjob MP, because DNC has no native MP and neither source recommends a mage subjob.

## Actual rows

| Priority | Compositions | Bounded context |
|---|---|---|
| DT Idle | dt-idle | Node DT No Shell V 348201 exactly; Nexus fills ears (Alabaster, Genmei) and back (Moonlight Cape) |
| Refresh Idle | refresh-idle | DNC99/WHM49; Null Masque and two Stikini Ring +1 on the DT base |
| Engaged Balanced | engaged-balanced | BG TP Terpsichore grid exactly except the cape (base Null Shawl) |
| Engaged DT | engaged-dt | Node Hybrid Swaps 367834 on that base |
| Engaged Accuracy | engaged-accuracy | BG Acc TP grid (Setan Kober sub not transferred) |
| WS | rudra-storm, climactic-rudra, pyrrhic-kleos | BG Normal/Climactic Rudra and Pyrrhic Kleos grids; Ishvara replaces Moonshade |
| Waltz | curing-waltz | BG Waltz Potency Capped; Regal Gloves, Carb. Ring +1, Aristo Belt from node Waltz set |
| Steps | steps | BG Steps grid; two Mache Earring +1 copies |
| Utility | violent-flourish, reverse-flourish, climactic-flourish, samba, jig | BG VF grid exactly; Macu. Bangles +3; Maculele Tiara +3 at activation; Maxixi Tiara +4 + base Senuna's; Jig +50% legs/feet |

All 15 declare all 16 slots. Every selection is a base copy, and no DNC augment
requirement is authored. Node 373 cape notes have no magnitudes ("DEX/Acc/STP"),
and BG prints aggregates ("DEX30 + ACC/ATT 20+10STP"), the kind PUP declined to
encode. So Senuna's Mantle builds become base Null Shawl (TP/WS/Steps) or base
Senuna's (Climactic crit damage, Samba duration). Adhemar/Lustratio paths,
Herculean/Samnuha randoms, Metamorph Ring and Moonshade reward augments are not
inherited. Maculele Earring sits in ear2 for its "Right ear:" text.

Source conflicts are kept: node 373 links Twashtar as level-80 ID 19398 and
Terpsichore as level-75 ID 18969. BG Toetapper Mantle "Reverse Flourish +30" is a
cape augment. CDG "TP Twashtar" uses an Airy Buckler single-wield shield,
"Acc TP" Setan Kober, "TP" Centovente (Magian TP Bonus path). The printed Waltz
potency in the source grid exceeds the 50% cap both guides state.

## Validation and preservation

Presave literal augment tests: **5 passed / 0 failed / 0 skipped in 0.72s**
(first run), and **5 / 0 / 0 in 0.74s** immediately before the single save.
They assert every selection is a base copy, and that literal encodings of the BG
aggregates would never match natively decoded separate-part copies. They also
cover separate 20/10 versus combined strings, split dust, repeated and missing
parts, native punctuation, and the identity() whitespace/case collapse.

Focused **609 passed / 0 failed / 0 skipped in 47.66s** on the first run (586 prior +
23 new DNC tests). Full isolated native **1423 passed / 0 failed / 0 skipped in
155.62s**. **Independent readback (protected bytes, history, resources, hands AST, line
endings, whitespace, recipients, base copies, successor prompt) and the fourth
packet gear-guide-t7-dnc-readback.json were NOT produced before the usage limit;
they are an outstanding DNC gate.**

Prior batch tests changed only in aggregate counts, DNC gap→included (zero gaps),
hands 53→55 (v18→v19, including the PUP test's hands slice) and authored-job
lists (exact replacement table, enforced by readback). 379 pre-edit byte backups
and all task scripts/logs are under `.t7-dnc-checks/`. No source/player Lua
executed, no inventory loaded. Branch `codex/sets-copy-fixes-review` and HEAD
`8f91ca164bd6737a4ad87185656eb96fcc1d45d4` preserved. Byte-identical: both DRG
artifact sets, all THF, BST and PUP reports/packets, BST-START, PUP-START,
DNC-START, World Map and the second-pass plan. No worktree,
switch/reset/stash/clean, commit, push, build, install, release, production
replacement, migration, game command or Lua activation.

## Remaining work and stop

Declared DNC limits (second-pass obligations, not waived): low/zero-haste Dual
Wield brackets and single-wield /WAR; other weapons and stages (Mpu Gandring,
Aeneas, Tauret, Centovente, Gleti's Knife, Karambit); WS Evisceration,
Exenterator, Aeolian Edge, Shark Bite, Dancing Edge, Ruthless Stroke and PDL
swaps; Striking/Ternary/Building Flourish WS variants; Divine/Healing and
self-received Waltz variants and Waltz recast/TP-cost gear; Feather/Box Step,
Presto/No Foot Rise/Trance/Grand Pas timing; Animated Flourish/enmity,
Utsusemi/FC, MDT/MEVA/Resist/Regen and Shell V idles; Senuna's Mantle and other
augment builds; AJGS/Dancer grids and "Last Dance III"; caps and HP preservation.

No unattempted initial job remains. The successor is the **second pass across all
22 jobs**, not started. `GEAR-GUIDE-T7-SECOND-PASS-START.md` and the standalone
`GEAR-GUIDE-T7-NEXT-JOB-PROMPT.md` (start in the current chat) are prepared. BRD
withdrawals retained; runtime retirement unimplemented. **STOP AFTER DNC AND THE
COPYABLE PROMPT.**
