# T7 BST — bounded initial candidate milestone

2026-11-05. Claude handled BST directly in the existing checkout, assigned by
Jason. Nova did not run concurrently (Codex idle; no checkout writes after the DRG
finalize at 07:20 before this task); Vesper unassigned; no other agents,
worktree or concurrent integration. Jason also changed the T7 instructions: the
"start a NEW LOCAL chat/window" wording (written for Nova running unattended) is
removed, and each next slice starts in the current chat.

**14 complete attributed Nexus compositions cover all eleven actual BST priority
rows** on three fixed dual-wield axe pairs plus one /WHM shield pair. This is not
complete job, weapon, pet, jug, Ready-move, tier, buff or encounter coverage.

Read the four packets in `docs/catalog/gear-guide-t7-bst-*`: definitions with
original/current row reconciliation; observations; independent item evidence;
readback with exact validation counts and preservation results.

Candidate: **483 sets / 494 historical revisions / 1045 sources**. There are
**475 effective recommendations** versus 486 stored verified flags including 11
withdrawn BRD encodings; eight unresolved originals unchanged. Coverage: **225
rows / 206 included / 19 gaps across two jobs (PUP 10, DNC 9) / zero N/A**. Only
the eleven BST rows changed. Resources: **802**, retaining all 766 prior records
and descriptions; 36 independently checked BST items appended. Hands: **48 /
hands.2026-11-05.v17**; the 43 prior records are AST-identical and five reviewed
exact records were appended: Spalirisos 21730, Ikenga's Axe 21723, Aymur 20793 and
Telopanos Axe 21738 (one_handed axes) and Diamond Aspis 26488 (shield, size 2).

Resource fingerprint remains
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.
Production SHA256 remains
`54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85`.

## Sources

- [FFXIAH node 227, The Beastmaster Compendium](https://www.ffxiah.com/node/227)
  (Falkirk; forum topic 45830), rendered "Last Modified: 2026-06-25". FFXIAH has no
  revision ids, so the node stamp and each item-set page's own update note are the
  locators. All 48 linked item sets were fetched; 21 are recorded as scoped item
  lists with exact IDs (no slot positions exist on those pages).
- [BG All Jobs Gear Sets/Beastmaster](https://www.bg-wiki.com/ffxi/All_Jobs_Gear_Sets/Beastmaster)
  rendered wgRevisionId **772439** (footer 13 July 2026): master WS and
  Spalirisos + Ikenga TP grids only; five grids transcribed.
- BG Community Beastmaster Guide (745000) is a prose stub with an empty Equipment
  section; no sets taken from it.
- Mechanics pages with their own revision ids: Ready 709840, Sic 753952, Dual Wield
  753673, Telopanos Axe 768660, Aymur (Level 119 II) 565071, Spalirisos (Level 119
  III) 692670, Blitz 689650, Rampage 741040, Mistral Axe 777215, Diamond Aspis 770015.
- 36 new item IDs checked against public BG item pages whose FFXIAH exact-ID link
  equals the local ID (slot, BST eligibility, base text). No index.php oldid link
  was requested; no Cloudflare/bot check was completed or bypassed.

## Weapon pairs and recipients

| Pair | Main / sub | Used for | Why |
|---|---|---|---|
| A | Spalirisos 21730 / Ikenga's Axe 21723 | idle, engaged, WS | BG TP grids and node WS sets; /DNC49 DW II or /NIN49 DW III |
| B | Aymur 20793 / Telopanos Axe 21738 | Ready physical/multi-hit/magical, pet durability, Ready precast | BG Ready: Aymur Pet TP Bonus+1000 is a main-slot effect; Telopanos pet lines are "Main hand:" only |
| C | Spalirisos 21730 / Telopanos Axe 21738 | pet accuracy | Node Ready Max Acc lists both without hands; BG Dual Wield: Ultimate job bonuses main-hand only, so Spalirisos is main (Nexus decision) |
| S | Spalirisos 21730 / Diamond Aspis 26488 | Refresh Idle (BST99/WHM49) | /WHM has no Dual Wield |

Pet: lines are pet recipient only and never added to master totals (e.g. every
line after "Pet:" on Thurandaut Ring +1). Switching between pair A and pet pairs
resets master TP; pet rows assume the master is not building TP.

## Actual rows

| Priority | Compositions | Bounded context |
|---|---|---|
| DT Idle | dt-idle | Node PDT Gleti grid + Killer DT rings; master recipient |
| Refresh Idle | refresh-idle | BST99/WHM49 positive subjob MP and deficit; Null Masque + two Stikini; Sibyl Scarf (Windurst citizenship) and Valorous Refresh+2 (random) not selected |
| Engaged Balanced | engaged-balanced | BG -25% DT grid = node TP MA; base Duty, no Odyssey rank |
| Engaged DT | engaged-dt | BG -50% DT grid; literal DEX/STP/PDT Artio's |
| Engaged Accuracy | engaged-accuracy | Nexus accuracy alternative (Bst. Collar +2, Crep. Earring, two Chirich +1, Klouskap +1) |
| WS | blitz, rampage, mistral-axe | Blitz needs Spalirisos Level 119 II+ main; Rampage native; Mistral Axe BST/WAR main only. Node lists identical items for Blitz and Mistral Axe, so those two compositions are slot-identical |
| Pet physical | ready-physical, ready-multihit | Node Ready Low Acc / Multihit accessories; base Emicho, Nyame, Artio's |
| Pet magical | ready-magical | Node Magic Ready accessories; augmented Kumbhakarna pair and Taupe Valorous not invented |
| Pet accuracy | pet-accuracy | Node Ready Max Acc items exactly, pair C |
| Pet durability | pet-durability | Node Pet DT/PDT accessories; Pangu/Izizoeksi and pet-cape/Nyame-path augments not borrowed |
| Ready precast | ready-precast | Gleti's Breeches "Sic"/"Ready" delay -5 at command use, then the move set |

All 14 declare all 16 slots; range is deliberately empty (ammo used). Source
ranks, paths and random augments (Odyssey R15–R30, Nyame B/D, Emicho C, Valorous,
Kumbhakarna, Telopanos R23+) are not inherited. Three Artio's builds are literal
copies from node 227 set notes (DEX/Acc-Atk/Acc/STP/PDT; STR/Acc-Atk/STR/WSD;
STR/Acc-Atk/STR/Crit). Pet sets use base Artio's: the decoder's combined pet
augment format cannot be confirmed without real game data, so no pet cape augment
is invented. Nukumi Earring +2 sits in ear2 because its card says "Right ear:".

## Validation and preservation

First presave **10 passed / 1 failed / 0 skipped in 0.94s**: my own test
expected exact-set augment matching, but `requirements_match` uses subset
semantics (a copy with an extra PDT part still has every required part). Only the
task's test was corrected (and a reverse 4-part-vs-5-part negative added); the
validator is unchanged. Presave then **11 passed / 0 / 0** (0.74s) and again
immediately before the single save (0.74s).

Initial focused **562 passed / 1 failed / 0 skipped in 37.90s**: the new BST
batch test expected a phrase worded differently in the access note; only that
expected phrase was corrected. Focused **563 passed / 0 failed / 0 skipped in
39.76s**. Full isolated native **1377 passed / 0 failed / 0 skipped in
140.95s**. **34 independent readback checks passed**, including
line-ending preservation (three files I first rewrote as LF were restored to CRLF
before any save) and the new no-new-window prompt wording.

Prior batch tests changed only in aggregate counts, BST gap→included, hands
43→48 and authored-job lists (exact replacement table, enforced by readback). 365
pre-edit byte backups and all task scripts/logs are under `.t7-bst-checks/`. No
source/player Lua executed, no inventory loaded. Branch
`codex/sets-copy-fixes-review` and HEAD `8f91ca164bd6737a4ad87185656eb96fcc1d45d4`
preserved; both DRG artifact sets, all THF packets, World Map and the second-pass
plan byte-identical. No worktree, switch/reset/stash/clean, commit, push, build,
install, release, production replacement, migration, game command or Lua activation.

## Remaining work and stop

Declared BST limits (second-pass obligations, not waived): other weapons/stages
(Spalirisos II/I, Aymur 119 III, Guttler, Farsha, Tri-edge, Dolichenus, Agwu,
Pangu, Izizoeksi, Skullrender, Kumbhakarna, Fernagu) and their WS (Decimation,
Onslaught, Calamity, Ruinator, Bora Axe, Primal Rend, Cloudsplitter); single-weapon
Fencer and two-handed /DRK or /SAM contexts; Reward, Call Beast, Charm, Killer
Instinct, Feral Howl, Spur/Run Wild/Unleash/Familiar, Metallic Body, Waltz, MDT,
regen/regain idle, pet TP; individual Ready moves/jugs and charge costs; pet-cape
and Odyssey augments; caps, pet damage/TP/recast floors, HP preservation.

Remaining initial queue: **PUP 10, DNC 9**. PUP is next. Then the second pass across
**all 22 jobs**; not started. BRD withdrawals retained; runtime retirement
unimplemented. `GEAR-GUIDE-T7-PUP-START.md` and the standalone
`GEAR-GUIDE-T7-NEXT-JOB-PROMPT.md` (start the next slice in the current chat) are
prepared. **STOP AFTER BST AND THE COPYABLE PROMPT.**
