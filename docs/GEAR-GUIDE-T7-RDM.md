# T7 RDM recommendation batch

Checked 2026-11-04. Jason explicitly requested RDM after the BLM batch.
**38 Nexus-authored full compositions cover RDM's 18 tracked priorities in the
declared caster, sword/shield and RDM/NIN sword/club contexts.** The all-job
catalog remains incomplete, with 18 jobs still open.

Verification establishes the stated composition and prerequisites: exact
IDs/names, job/slot eligibility, reviewed main/sub types, explicit Dual Wield
where applicable, 16 canonical slot states, duplicate-copy constraints and
declared augments/path/rank. Every recommendation has 15 selected items and one
intentional empty range. Sparse author tables and options remain separate.

These are explicitly Nexus choices, not source-exact imports or a universal
best-in-slot ranking. Composition review does not calculate effective caps,
skill/stat totals, target dSTAT, potency, hit rates, durations, TP return, damage
or ownership. Actual spell/WS/trait access is a scenario prerequisite. Unsupported
effects remain uncalculated; no numeric rules were added.

## Source evidence and corrections

[Anything You Can Do, node 425](https://www.ffxiah.com/node/425) labels its last
update October 24, 2026. Its action, subjob, JP-gift, weapon and equipment sections
were read, with 33 exact linked live tables followed through public HTTP. That
date is not proof that every individual table or mechanical claim was refreshed.

The [August–September discussion on page 24](https://www.ffxiah.com/forum/topic/55398/anything-you-can-do-i-can-do-better-rdm-guide/24/)
and [October 1 discussion on page 25](https://www.ffxiah.com/forum/topic/55398/anything-you-can-do-i-can-do-better-rdm-guide/25/)
were read for current context. In particular, participants disagree about
zero-damage conditions and trade accuracy, defense and TP equipment. Their
personal outcomes and numerical reports are not certified results for Nexus.

Several source details require explicit handling:

- [375613 Refresh](https://www.ffxiah.com/item-sets/375613) currently selects
  Vitiation +4 head, Colada, Chironic pieces, two Stikini +1 rings and Moonshade.
  The guide requires Refresh+2 on Colada/Chironic pieces, and cautions against
  dedicating Moonshade to Refresh. Nexus instead chooses fixed Daybreak,
  Homiliary, Vitiation +3 head and Lethargy +3 body; no random Refresh, Fucho
  threshold, Moonshade augment or +4 equivalence is assumed.
- [402064 Turtle](https://www.ffxiah.com/item-sets/402064) displays Sworn and
  other defensive selections, but the surrounding guide explicitly offers
  mix-and-match options. It is retained as `equipment_options` research, not a
  simultaneous source-authored loadout. Nexus's full Nyame assembly is its own.
- [399008 Seraph Blade](https://www.ffxiah.com/item-sets/399008) currently puts
  **Daybreak main / Crocea Mors sub** in the macros, while the guide describes
  sword-main Seraph Blade use. A sword WS cannot use club main. The observed
  conflict remains intact; Nexus independently chooses **Naegling main /
  Daybreak offhand**, with no Crocea Path C effects or copied source damage.
- [404156 burst](https://www.ffxiah.com/item-sets/404156) has two ammo macro
  lines: Pemphredo, then Ghastly +1. [404364 TP](https://www.ffxiah.com/item-sets/404364)
  has Grunfeld, then Sailfi +1 in the waist. [375670 Stoneskin](https://www.ffxiah.com/item-sets/375670)
  repeats the identical Shedir legs line. **Macro order is not an authorship
  resolution rule.** The initial captures flattened these repeated slots;
  independent tests exposed the mismatch. The 33 initial hashed captures remain
  preserved as historical records. Three appended corrections retain all
  ordered macro lines, unique occupied slots and explicit alternatives. Neither
  conflicting ammo nor belt is declared uniquely selected in the correction.

The source-capture corrections add three immutable source identities and
`source_observation_amendments` links to the affected revision IDs. All 119
sets/revisions and all 185 source records present before those amendments remain
unchanged. No recommendation gear changed: Nexus already explicitly chose
Pemphredo for burst, Grunfeld for ordinary TP and one Shedir legs piece. These
choices do not rely on last-write-wins. The amendment records are evidence
metadata; no second loader, UI workflow or version-selection behavior was added.

Public item-card requests initially hit HTTP 429. They were paused, then resumed
sequentially at a slower pace with successful reads retained. All 42 new exact-ID
card names and RDM eligibility checks succeeded. Public card and resource
description hashes are in the evidence packet. BG requests for Seraph Blade and
Sanguine Blade returned 403; no BG RDM page read/revision is claimed. Browser
control was not used. Source access failures did not become N/A dispositions.

## Declared priorities and contexts

| Priority | Recommendations | Scope and tradeoff |
|---|---:|---|
| DT Idle | 1 | Fixed Daybreak/Genmei, full base Nyame, Defending and Moonbeam. No augment or block-rate/cap certification. |
| Refresh Idle | 1 | Fixed recovery choices above; two separate Stikini +1 copies. Keeps Nyame extremities and gives up some DT protection. |
| Engaged Balanced | 2 | Naegling/Genmei single wield with Malignance/Null, and Naegling/Daybreak dual wield with an explicit DW10 cape. |
| Engaged DT | 2 | Base Nyame/Defending; single wield keeps Moonbeam/Genmei, dual wield replaces shield and defensive cape for Daybreak/DW cape. These protection contributions do not carry over. |
| Engaged Accuracy | 2 | Exact Lethargy +3 physical-accuracy choices in both weapon contexts; trades some protection. No monster hit-rate guarantee. |
| Enspell | 2 shared | Separate enhancing-skill casting checkpoint and ordinary Pukulatmuj +1/Daybreak tier-I Enspell melee. Fixed sword/Umuthi/Ghostfyre choices; no R15 Pukulat effects, Crocea multipliers or zero-TP-feed claim. |
| WS | 5 | Naegling Savage Blade in both weapon contexts; Maxentius/Genmei Black Halo; non-Crocea Naegling/Daybreak Sanguine and Seraph. Main-hand action and STR/MND/INT cape distinctions remain explicit. |
| Enfeebling potency | 7 | Frazzle/Distract skill/effect, inactive-Saboteur dMND/dINT, active-Saboteur dMND/dINT, duration and Immunobreak tradeoff. No target stat/skill cap or effect multiplier certification. |
| Enfeebling accuracy | 2 shared | Fixed landing-accuracy checkpoint and explicit Immunobreak option. Source omitted main/sub positions are completed under Nexus authorship; armor hands were present in the source. |
| Enhancing | 8 | Enspell I/Temper skill, self duration, other-target duration with Composure, Gain, self/other Refresh, self Phalanx and other-target Phalanx II. Spell/recipient behavior is not interchangeable. |
| Precast | 1 | Atrophy +3 head, Vitiation +3 body, fixed Merlinic feet and FC10 cape. No random Merlinic FC6, Quick Magic or effective cap assumed. |
| Healing | 1 | Native Cure I–IV, defensive Daybreak/Ammurapi/Bunzi/Kaykaus/Atrophy/Vanya choices. No Kaykaus path augments, cure amount or cap promised. |
| Cursna | 1 | Declared RDM/SCH 99/49 with available Cursna under Addendum: White. Vanya B15 head/feet and two Ephedra rings; no guaranteed removal. |
| Free nuke | 1 | Exact Lethargy +3 fixed casting checkpoint with INT20/macc20/MAB10 cape. Learned spell/gift access required. No weather or distance bonus assumed. |
| Magic burst | 1 | Exact Ea +1 head/body, base Amalric +1 hands, Lethargy +3 legs/feet, Mujin and explicit cape. No Amalric D15, copied cap or favorable weather/distance assumption. |
| Stoneskin | 1 | Explicit full loadout around fixed Nodens/Earthcry/Stone Mufflers/Shedir/Siegel utility pieces. No 475HP certification. |
| Aquaveil | 1 | Fixed Amalric +1 head, Regal Cuffs, Shedir legs and Emphatikos waist. No guaranteed interruption count. |
| SIRD | 1 | Fixed casting-under-pressure checkpoint and explicit SIRD10 cape. No extra random Chironic SIRD or 102% cap result; trades spell-specific gear. |

Rows share some compositions; the distinct total is **38**. The seven new rows
make supported casting roles explicit rather than waive existing priorities or
define new Lua modes. All 11 earlier RDM obligations are retained and included.

## Prerequisites and boundaries to preserve

**Self/other and buffs:** self duration uses Vitiation +3 body and Telchine
duration10 cap/legs. Other-target duration uses four exact Lethargy +3 pieces
with Atrophy +3 hands while Composure is active; it is not a five-piece set.
Gain retains Vitiation +3 hands. Self Refresh uses Gishdubar; Refresh on others
uses Embla, since the caster's received effect does not transfer to a recipient.

Phalanx received on Sakpata's Sword and each Taeon head/hands/feet copy is a
self-received context. Those caster bonuses are absent from the Phalanx II
other-target checkpoint. Each Taeon piece explicitly requires `Phalanx +3`;
there is no inferred random +4/+5 alternative. Actual skill/mitigation is not
calculated. Telchine/Vanya/Nyame path/augment evidence reuses the retained exact
public references alongside node 425's explicit requirements.

**Enfeebling:** Regal Cuffs duration versus Lethargy +3 hands under active
Saboteur is an intentional tradeoff. The skill/effect checkpoint keeps Lethargy
hands even when Saboteur is inactive, for their fixed skill, while their active
bonus remains conditional. MND and INT capes are distinct physical-copy
requirements. Immunobreak changes Lethargy legs to base Chironic Hose, losing
that set membership; optional random stat/macc augments are not counted.

**Weapons/haste/WS:** dual-wield recommendations explicitly assume usable Dual
Wield on RDM/NIN 99/49. The DW10 cape cases declare a capped-magic-haste scenario;
no exact delay cap is certified, and this is not all-haste or /DNC coverage.
The ordinary Enspell version instead uses Reiki/Eabani and a fixed Ghostfyre
cape, with its own uncalculated delay tuning. Single-wield sets do not carry DW
equipment requirements. All actions still require actual learned/usable access,
retained TP and suitable targets. Planning targets do not execute weapon swaps.

Naegling main grants the Savage Blade context; Maxentius main grants Black
Halo. Black Halo uses MND physical-WS cape requirements; Savage uses STR.
Non-Crocea Sanguine uses INT magic-WS requirements; Seraph uses MND with a sword
main and Daybreak offhand. Nyame body/legs used for the relevant physical WS
checkpoints explicitly require B15; magical WS only inherits the specified
body B15 requirement, not unlisted ranks. No Moonshade, Thibron, PDL support,
Crocea Path C or universal damage advantage is assumed.

**Access and inventory:** Frazzle III/Distract III/Addle II require their
550-JP gift. Temper II/Refresh III require their 1200-JP gift. Cursna's declared
/SCH/Addendum context is a prerequisite, not detection of Jason's current
subjob/spells. Owning a base item does not satisfy its specified augment/path.
One cape must satisfy every one of its requirements, and simultaneous identical
rings need two actual copies. The current strict matcher compares augment
strings; higher/different augment text is not automatically treated as equivalent
to the explicitly authored checkpoint. No ownership conclusion is drawn here.

Unclaimed contexts include every source tier, +4 JSE parity, full Sworn progression,
Crocea/Thibron/prime/aftermath setups, bows/ranged WS, CDC/crit WS, every subjob,
zero-physical-damage dagger Enspell strategies, Impact/cloak occupancy, all Dark
Magic/Occult Acumen/Convert niches, every spell/merit variation and every weather
scenario. The declared coverage does not imply universal job completeness.

## Artifacts and preservation

- `docs/catalog/gear-guide-t7-rdm-definitions.json`: all 38 explicit definitions,
  rationale, slots, target/buff/access/haste context and exact requirements.
- `docs/catalog/gear-guide-t7-rdm-observations.json`: 33 initial hashed source
  captures plus 3 append-only ordered-macro corrections; initial capture limits
  and supersession are explicit.
- `docs/catalog/gear-guide-t7-rdm-item-evidence.json`: 42 hashed exact-ID public
  card observations, matched names, card/description hashes and source-access
  limits. Decoder labels were inspected as text only, with file hash recorded.
- `docs/catalog/gear-guide-t7-rdm-readback.json`: baseline file hashes/backups,
  resource/production identity, exact counts and readback results.
- `docs/catalog/gear-guide-t7-resource-evidence.json`: 327 detached records;
  all previous 285 records/descriptions are unchanged and all 327 match actual
  installed public-resource readback. All four upstream file hashes match.
- Candidate: **119 sets / 119 revisions / 188 sources**, with **111 verified
  Nexus compositions** (23 WHM + 28 SCH + 22 BLM + 38 RDM) and **8 unchanged
  unresolved originals**. **1,767 selected slots + 111 intentional empties**.
- Fifth authoring batch retains canonical hashes of all previous **81 sets,
  81 revisions and 107 sources**. Every prior immutable record/hash matches.
- Coverage: **225 rows / 59 included / 166 gaps across 18 remaining jobs /
  0 N/A**. All 22 jobs retain explicit DT/Refresh dispositions.
- `core/equipment_hands.py`: only three appended exact-ID evidence records,
  Naegling **21621**, Pukulatmuj +1 **20614**, Sakpata's Sword **21637**. Public
  sword classification and local skill 3/slot masks match. Registry revision
  `hands.2026-11-04.v4`, 18 records. All 15 older evidence records are AST-identical.
  No heuristic, new rule, inferred Dual Wield or GUI resource scan was added.
- `tests/core/test_guide_rdm_batch.py`: context, source-conflict, physical-copy,
  hand classification, prerequisite and immutable-history regression checks.
  Earlier tests only update candidate-wide counts, added hand count and the
  remaining-job exclusion list; prior job-specific checks remain intact.

Pre-edit copies/hashes for candidate, resource packet, hand registry, affected
earlier tests and docs were created under `.t7-rdm-checks/baseline/` before edits.
The normal app continues to use production v1. Its SHA-256 remains
`54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85`.
Resource fingerprint remains
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.

No app/UI behavior, numeric-rule implementation or authoring-tool implementation
changed. The three source hand-evidence entries are staged source changes;
no executable was built or replaced. No commit, push, real-data migration,
Wishlist dual-write, installation, release, game command or Lua activation
occurred. Windower/player Lua were read-only; no player Lua was evaluated.
T8/T9/full-app/frozen/live acceptance and separate approval gates remain later.

## Validation and continuation

Focused exact-source checks: **89 passed / 0 failed / 0 skipped in 2.05 s**.
The first focused run had 87 passes and one failure: its macro-count assertion
exposed three repeated-slot source captures. The append-only corrections and
amendment links fixed the evidence, preserving all candidate revisions and source
records; the tests now assert every conflicting line explicitly.

Actual-resource whole-candidate preparation passed: 119 revisions, 111 verified,
8 unresolved, 225 coverage rows, 166 open priorities. Prior-record hashes,
all resource readbacks and production v1 identity passed. Full isolated native
Windows suite: **867 passed / 0 failed / 0 skipped in 82.66 s (1:22)**.
No app/core/UI/test/tool source changed after that run. Tests use fictional persistence, redirected
auto-discovery and disabled inventory seeding via the existing real-file launcher.
No frozen or gameplay verification is claimed.

Continue T7 on one of the remaining 18 jobs. No next job has been selected or
authorized as an additional batch by this RDM request. Preserve the candidate's
immutable history and use the existing preparation/save service. Keep source
options, omissions, macro conflicts and Nexus choices distinct. Do not publish
the partial candidate to production or restart the accepted architecture review.
