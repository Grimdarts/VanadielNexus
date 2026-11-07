# T7 COR bounded candidate batch — 2026-11-04

COR now has **29 separately attributed Nexus-authored, composition-verified
recommendations across all eleven actual coverage rows**, limited to the declared
contexts below. Nova handled COR directly; Vesper remained unassigned. Jason's
fresh-session request and COR kickoff authorized this job only. **Stop after COR.**
No next job or T8/T9 is authorized by this milestone.

This fixed base/explicit-augment checkpoint does not certify all tiers, weapon
stages, aftermaths, rolls, targets, spell/subjob utility, or job completion.
Jason's requested sequence remains: finish the remaining initial job passes,
then return to BRD and DRG issues. They are deferred, not resolved or waived.
DRG still has zero recommendations and eight gaps. Eleven withdrawn BRD initial
encodings, corrected successors and amendment histories remain unchanged.
Runtime retirement is unimplemented; this partial candidate must not replace
production.

## Compositions and actual prerequisites

All keys below have prefix `nexus:cor:`. Every composition declares all 16 slots.
The two roll-only snapshots deliberately leave ammo empty; all others select
**Fomalhaut21485 and Chrono Bullet21296**. This exact unaugmented dispenser gun
is distinct from augmented Fomalhaut22143, which was independently read as an
observation and was not added to the selected-resource packet. No gun rank,
mythic/empyrean/prime stage or aftermath is silently substituted.

| Actual priority | Candidate keys | Bounded context |
|---|---|---|
| DT Idle | dt-idle | Naegling/Nusku, base Nyame defense, Defending/Gelatinous; no Shell or capped DT |
| Refresh Idle | refresh-idle | COR99/WHM49 with useful recoverable MP; base Rawhide mask/Mekosu body and two physical Stikini+1 copies; wearer Refresh and sphere separate |
| Engaged Balanced | engaged-balanced | Naegling main/Tauret sub, protective Malignance and explicit DEX/DA cape; external HasteII only |
| Engaged DT | engaged-dt | Separate Loricate/Defending swaps; no capped defense or delay claim |
| Engaged Accuracy | engaged-accuracy | Combatant/Telos and two Chirich+1 copies; actual target evasion unknown |
| Ranged | ranged-normal, ranged-accuracy, ranged-triple-shot | Shot completion, separate ranged accuracy and actually active Triple Shot/occasional Quad Shot; no fixed x-hit or proc-rate result |
| Physical WS | last-stand, savage-blade, evisceration | Physical two-hit ranged Last Stand, Naegling-main Savage, Tauret-main critical dagger Evisceration; distinct usable WS/TP and ammo requirements |
| Magical WS | leaden-salute, wildfire, hot-shot, aeolian-edge | Dark Leaden, fire Wildfire, physical/fire hybrid Hot Shot and wind AoE dagger Aeolian; no shared QD formula or guaranteed skillchain |
| Rolls | roll-initial, roll-double-up, random-deal, fold, snake-eye, wild-card | Initial Chaos/Samurai versus actual Double-Up window; four separate JA snapshots, recipient/recast/merit/random-result conditions |
| Quick Draw | quick-draw-damage, quick-draw-elemental-window, light-shot, dark-shot, quick-draw-tp | Fire damage versus Chasseur-feet next-magic window, Light sleep, Dark dispel and StoreTP utility; charges/cards/target effects separate |
| Preshot | preshot-no-flurry, preshot-flurry1, preshot-flurry2 | Normal ranged initiation; distinct actual Flurry states, base/path-unknown equipment and Snapshot cape; no capped70% or Rapid Shot timing claim |

**COR99/NIN49** is explicit wherever two weapons are used: engaged targets,
Savage/Evisceration/Aeolian and all Quick Draw targets. NIN45's usable Dual Wield
was independently checked; equipment does not grant the trait by itself.
**COR99/WAR49** uses Naegling/Nusku for shooting, ranged WS, preshot, DT idle,
rolls and four utility abilities. **COR99/WHM49** uses the shield for MP recovery.
No master levels, JP gifts, capped merits or modeled subjob stats are assumed.
Tauret's Evisceration grant/bonus and Naegling's Savage grant/bonus apply in the
actual main-hand contexts, not to offhand weapons.

Fomalhaut's printed TP Bonus is **Marksmanship-WS-only**. It is never applied to
Savage, Evisceration or Aeolian. Last Stand access from this exact gun is
independently documented. Leaden/Wildfire require actual unlocked access; Hot
Shot/Aeolian require usable skill/access. All WS require actual1000+TP and a
susceptible target. No Death Penalty Leaden enhancement, Armageddon aftermath,
Ataktos trial bonus, Earp Terminus or Rostam path is credited to substitutions.
Actual aftermath is inactive before the selected snapshots; generated AM is not
modeled. Establish weapons before building TP; pair/gun changes can erase TP/AM.
Roll-only Compensator21482 swaps are expressly subject to that transition.

BG independently confirms the exact Fomalhaut/Chrono compatibility and dispenser
supply. Actual accessible equipped bullets and enough disposable quantity still
must be established; no ownership, bag placement, refill timing or consumption
safety is certified. Ordinary attacks/WS consume bullets, and multi-shot can use
several. Quick Draw instead requires an actual charge, gun/bullet and a matching
card or main-COR Trump Card; the card is consumed, the bullet is not consumed by
QD itself. No runtime ammo guard or inventory read was implemented.

Roll+n potency takes only the highest selected effect. Regal+7 is the sole
selected roll+n item; duration, actual roll number, lucky/unlucky/XI/Bust state,
matching-job presence in party/zone, head proc, Crooked Cards, merits and JP remain
separate conditions. Initial roll and Double-Up are distinct. Intended party
recipients must actually be in range of Luzaf's enlarged AoE; no alliance-wide,
retroactive matching-job bonus or fixed ten/eleven-minute duration is promised.
Crooked Cards is inactive in these two targets. Merited Fold/Snake Eye require
actual access; Random Deal/Wild Card require ready recasts, eligible recipients
and actual random outcomes. No guaranteed reset chain or SP result is claimed.

Preshot gear is for initiation; completion gear is for the shot. No runtime
switching is implemented. Triple Shot gear requires active Triple Shot and does
not apply its ability effect to WS. HasteII in engaged contexts and FlurryI/II in
preshot contexts must actually be present from external casters. No other haste,
songs, rolls, geomancy, food, day/weather, Berserk/Warcry or shot elemental bonus
is assumed unless explicitly stated. No delay, damage, accuracy, recovery,
potency, duration, charge, gear-total or cap is calculated.

Only explicitly specified NyameB, literal cape parts and Moonshade Attack4/
TPBonus250 are required. Nyame/Odyssey/Unity/neck ranks and random Carmine,
Adhemar/Pursuer paths remain unknown. Base Nyame legs deliberately replace
source PathD Rawhide legs in MP recovery; no base-leg Refresh bonus is invented.
Quick Draw's Nyame legs deliberately remain B rather than importing source C.
Distinct cape variants remain separate copies, and two simultaneous Stikini or
Chirich rings require two physical copies. No universal cape copy is inferred.

## Original evidence, access and preserved conflicts

[Luck of the Draw node326](https://www.ffxiah.com/node/326) was read in ordinary
Chrome for subjobs, merits/JP, rolls, abilities, weapons, all gear sections,
capes and FAQ. It labels September2023 and has an October19,2023 footer; neither
establishes embedded-grid currency. **Nineteen selected original grids** were
opened separately, including recovered historical [357016 DT/Meva](https://www.ffxiah.com/item-sets/357016)
and the partial [357015 Refresh](https://www.ffxiah.com/item-sets/357015).
No reader/browser failure was converted into N/A.

[BG COR772442](https://www.bg-wiki.com/index.php?title=All_Jobs_Gear_Sets/Corsair&oldid=772442)
was read through the normal article in Chrome; its rendered Permanent link and
July13,2026 footer were verified. Visible current tables cover Terminus, Last
Stand, Hot Shot, Leaden, Wildfire, Savage, Evisceration, Aeolian, Quick Draw and
Naegling/Gleti TP. Most OdysseyR30/NyameR25B, no True Shot and excluded ranged
Orpheus are source-model assumptions. +4JSE, Clemency and staged ultimate weapons
remain observations; source damage/DT/delay benchmarks were not inherited.

Seven other BG articles were independently read through normal routes and their
rendered Permanent links verified: [Camulus568480](https://www.bg-wiki.com/index.php?title=Camulus%27s_Mantle&oldid=568480),
[Fomalhaut765790](https://www.bg-wiki.com/index.php?title=Fomalhaut&oldid=765790),
[Chrono589749](https://www.bg-wiki.com/index.php?title=Chrono_Bullet&oldid=589749),
[Quick Draw775674](https://www.bg-wiki.com/index.php?title=Quick_Draw&oldid=775674),
[Phantom Roll780130](https://www.bg-wiki.com/index.php?title=Category:Phantom_Roll&oldid=780130),
[Triple Shot773760](https://www.bg-wiki.com/index.php?title=Triple_Shot&oldid=773760)
and [Dual Wield753673](https://www.bg-wiki.com/index.php?title=Dual_Wield&oldid=753673).
A search returned a private-server mirror; it was never opened or used. No
security setting, warning, verification or paywall was bypassed.

Preserved observations and conflicts:

- Savage356928 has **Gleti main/Naegling sub**, contrary to intended sword Savage
  use. Nexus's Naegling-main/Tauret-sub is separately authored; the source was not
  silently reversed. Source Ataktos/Bayeux prerequisites are not transferred.
- QD accuracy357009 puts **right-ear Chasseur+2 in ear1**, omits the gun and leaves
  random augment/stage prerequisites unresolved. Nexus chooses Digni/Crepuscular
  earrings and fixed gun/ammo independently.
- Last Stand357137 names **Earp without stage**. BG's Last Stand uses Fomalhaut,
  while Terminus specifies Earp119II. No prime stage, AM or Terminus target was
  manufactured from the generic source name.
- BG Last Stand and Hot Shot mid tables label **STR cape**, high tables **AGI**;
  FFXIAH prose favors AGI variants. Nexus's explicit AGI cape choices are separately
  attributed, not a performance resolution or optimum claim.
- Original node326 lists **Triple Shot one-minute recast**; BG773760 lists five.
  QD recast text also differs: guide discusses a ten-second gift/gear cap while
  BG775674 describes a different overall25-second reduction/35-second recast.
  No recast or timing cap is certified from either source.
- The guide's generic QD elemental-bonus prose says25%, while its +3 foot card and
  BG775674 distinguish31% at+3. Laksamana QD damage and Chasseur next-same-element
  damage enhancement are different properties. Light/Dark effects must succeed
  for the Empyrean window; no-effect/miss is not guaranteed bonus application.
- Original Refresh357015 still has **eleven omissions** and PathD Rawhide legs
  only supported in guide prose. The unresolved historical record survives;
  separately authored full MP-subjob recovery does not rewrite it.
- Preshot tables contain only8–9 cells; ranged356894 and QD356986 omit the gun;
  Triple Shot356892 has only six swaps; roll355063 has eight cells. Source
  omissions remain omissions, never mechanical intentional empties or full sets.

The packets contain manual structured transcriptions/paraphrases, not retained
rawHTML or immutable upstream webpage snapshots. Observation digests identify
our records; description hashes identify local public resource descriptions.
**Thirty-one exact public cards** were independently read, including all 26 new
selected IDs and Naegling/Nusku/base and augmented Fomalhaut/Chrono corroboration.
Public extdata decoder tables/native formatting were read only, never executed.
No player Lua or inventory was loaded. Prior shared item evidence remains intact.

## Validation and preservation

Before the single candidate save, **10 independent literal fictional-copy tests
passed / 0 failed / 0 skipped in 0.98s**. Separate20/10stat parts, combined ranged/
physical/magical strings, repeated/missing parts, native DA/STP/Crit/MAB/Snapshot/
WSD/DT punctuation, TPBonus spacing and wrong paths are checked against literal
copies. Requirements are not their own expected-copy oracle. The marker binds
both definitions and test-file hashes. Actual-resource whole-candidate preparation
and append-only `save_candidate` passed without relaxing any validator.

Focused authoring/prior-job/COR suite: **374 passed / 0 failed / 0 skipped in 23.50s**.
The 48 new COR cases cover 29 compositions, exact-hand fail-closed behavior, literal
copies, physical duplicate allocation, weapon/ammo/action/Flurry/TS/roll/QD
contexts, source conflicts and immutable history. Earlier tests change only
reviewed catalog-wide counts/job lists and a stable historical hand index.
Independent readback replays those exact transformations against byte backups.
The initial focused run had370 passes and 4 test-only failures: three calls used an
incorrect allocation API, and one expected observation-only 22143 in the selected
resource packet. Tests were corrected; no candidate/validator repair was needed.

Full isolated native suite: **1,132 passed / 0 failed / 0 skipped in 128.09s
(2:08)**. The first sandboxed full run had 1,130 passes / 2 failures / 0 skips
in 141.19s: Windows junction creation/inspection and loopback UDP delivery were
restricted. Both unchanged tests passed natively (2 passed / 0 failed / 0 skipped
in 0.96s), followed by the complete unchanged-source native rerun above. No
persistence, network or safety assertion was weakened.
Independent actual-resource/history/protected-byte readback: **26 checks passed**.
Final `git diff --check`: **passed**. New untracked COR files also passed an
independent trailing-whitespace check. No core/UI/test/tool implementation
changed after the final full run; only documentation and readback were finalized.

Candidate **312 sets / 323 historical revisions / 629 sources; 304 effective
recommendations**, including 29 COR. Generic 315 stored verified flags include the
eleven withdrawn BRD encodings. All 283 prior sets / 294 revisions / 570 sources, eight
unresolved originals, corrected successors, amendments and batches survive.
Coverage **225 rows / 138 included / 87 gaps across 10 jobs / zero N/A**. Only the eleven
COR row dispositions changed; all other coverage, including eight DRG gaps,
remains unchanged. Included rows cover only the declared bounded contexts.

Detached resources **586**, with all 560 prior records/descriptions unchanged.
Hand registry **34 / hands.2026-11-04.v11**: prior 33 records AST-identical, only exact
Tauret21565 appended after independent Main/Daggers/COR/skill250 card verification
and reconciliation with actual slots3/skill2/shield0. Four upstream resource
hashes/fingerprint remain unchanged:
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.
Public decoder bytes match the prior BLU packet. Protected production v1 SHA256:
`54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85`, unchanged.

Backups of 309 existing canonical files, hash manifest, HEAD/status, fresh real-file
isolation launcher, presave tests/marker, authoring/count scripts and independent
readback remain in `.t7-cor-checks/`. Tests use fresh COR-local real files and
TEMP/TMP/VN_DATA_DIR/basetemp, fictional Windower discovery and disabled inventory
seeding. Interpreter:
`C:/Users/Jason/AppData/Local/Python/pythoncore-3.14-64/python.exe`.
Branch `codex/sets-copy-fixes-review`, HEAD
`8f91ca164bd6737a4ad87185656eb96fcc1d45d4`, World Map work and all earlier tracked/
untracked work and scratch are preserved. No worktree or concurrent integration.

Portable packets:

- `docs/catalog/gear-guide-t7-cor-definitions.json`: 29 targets, eleven actual-row
  reconciliations and explicit unclaimed variants.
- `docs/catalog/gear-guide-t7-cor-observations.json`: 19 ordered original grids,
  nine guide/supporting observations, access, conflicts and hashes.
- `docs/catalog/gear-guide-t7-cor-item-evidence.json`: 31 independent exact-card
  observations, conditional limits and native augment evidence.
- `docs/catalog/gear-guide-t7-cor-readback.json`: 26 independent checks, baseline/
  history/resource/protected-byte evidence and artifact hashes.

## Explicit unclaimed variants and stop

Every progression tier and attack/accuracy/haste/DW bracket; DP/Armageddon/Earp/
Ataktos/Rostam stages/paths/ranks/aftermaths/Terminus; AM3critical/TrueShot/enmity
niches; every roll including special Blitzer/Allies/Courser/Caster gear, Crooked
Cards and XI/Bust/recipient groups; dedicated QD charge/recast and every card/
element/immunity; Requiescat/other meleeWS and skillchain/TP transitions; mage-
subjob precast/completion/healing/enhancing/status and /DNCwaltz/step/jig utility;
movement/tanking/subtleblow and guaranteed reset chains remain unclaimed. These
are explicit limits, never blanket N/A or job-completion claims.

Offline composition does not establish ownership, bags/ammo readiness, numeric
caps/totals, currentBiS, live switching, complete job coverage or human/frozen/live
acceptance. No extra-agent/Vesper setup, architecture interview, branch/worktree
switch, reset/stash/clean, commit/push, build/install/release, production
replacement, real migration, game command or Lua activation occurred.
Windower/player Lua stayed read-only. BRD/DRG follow-up remains deferred until
remaining initial passes finish; neither issue is resolved or waived.
**Stop after COR.**
