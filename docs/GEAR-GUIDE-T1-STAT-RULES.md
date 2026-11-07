# T1 equipment-effect evidence matrix

Date: 2026-11-03. Status: research draft; no numeric rules implemented or certified.

The [consolidated review packet](GEAR-GUIDE-T1-REVIEW.md) now recommends a bounded initial rule subset from this evidence. Its disposition table supersedes earlier open-ended next-research wording for that proposal. Acceptance and future implementation tests remain pending. Original observations and their evidence limits are preserved below.

This matrix separates text that local resources actually contain from mechanics that still need independent evidence. Item/job/slot eligibility does not prove current best gear, ownership, augments or effect stacking. Resource descriptions are display evidence, not a complete calculator specification.

## Reproducible input snapshot

Read-only files under `C:\Users\Jason\Games\Windower4\res`; no inventory or personal Lua was evaluated.

| File | Bytes | SHA-256 |
|---|---:|---|
| items.lua | 5040087 | 92f32adb795f71645b241cf6764a6b89d4a953c69d4b9330e9fddbc334efb36f |
| item_descriptions.lua | 4972281 | 160d5e6c2562e49c4004e1add78575e8ac30b5d64f2fb89d6fdea7eb6457388c |
| jobs.lua | 3264 | 88d1561636a15e03337a5c704b06491faf35e965965822ca9ca4da26606c1585 |
| bags.lua | 3944 | dc827886a53d597ab7b7bdf36c4d22bf655c2b1b5f48ef00de91c301f68646ef |

## Initial rule families and evidence gaps

Quoted fragments below are local resource observations. They establish parsing challenges, not authoritative formulas. All rows still require independently sourced mechanics and expected-result fixtures before supported numeric status.

| Family / representative item | Observed description | Proposed representation | Remaining evidence / verification |
|---|---|---|---|
| Flat master values: Stikini Ring +1 (26184) | MND +8, magic accuracy +11, all magic skills +8 | Separate numeric stat keys and a skill-family contribution; retain original label | Enumerate supported skills; do not expand into every unrelated skill or double count a family and its members |
| Defensive: Defending Ring (13566) | Damage taken -10% | Signed percentage-point equipment contribution in its own category | Verify DT/PDT/MDT category interactions, applicable caps and rounding; raw equipment totals do not assert final damage reduction |
| Recovery: Stikini Ring +1 | Refresh +1 | Master refresh contribution with a supported unit | Verify refresh timing/unit and stacking; two physical rings must contribute twice only after distinct-copy allocation |
| Multiattack: Epona's Ring (11651) | Double Attack +3%, Triple Attack +3% | Two independent equipment stats | Do not add percentages into one proc chance; effective attack distribution is outside initial totals |
| Multiple recipients: Nyame Helm (23761) | Master values followed by Pet: Accuracy, ranged accuracy and magic accuracy across lines | Recipient scope persists across line breaks until a proven boundary | Verify each value and scope; avoid accidentally assigning pet lines to master totals |
| Avatar-specific: Indomitable Coat (24155) | Master fast cast/DT, then Avatar: accuracy/ranged accuracy/magic accuracy/critical rate | Avatar recipient distinct from master and generic pet | Verify applicability and exact augmented values separately; displayed item rank alone must not synthesize rank effects |
| Time conditional: Fenrir's Earring (13399) | Daytime attack +10; nighttime ranged attack +10 | Mutually exclusive named conditions and separate stats | Verify time boundaries and scenario semantics; unresolved time must not enable both |
| Ranking range: Bathy Choker +1 (27518) | Unity Ranking: Evasion +5 to +15 | Conditional range with unresolved ranking input | Verify mapping from ranking to magnitude; do not choose maximum or zero by default |
| Ambiguous: Hoxne Earring (26120) | Mastery Rank: All BP -30 to +30 | Unsupported raw effect with conservative uncertainty | Resolve resource wording and retail behavior before mapping BP to any stat |
| Set bonuses | Not certified by this sample | One loadout-level rule, qualifying distinct selected pieces | Verify thresholds, eligible families, recipient, stacking and conditions; never attach the full bonus to every item |
| Augments/path/rank | Observations and guide requirements are different inputs | Preserve observed raw text, structured rank/path and provenance separately | Verify per-item augmentation tables and observed magnitude; unknown augments remain unknown |

## Result contract

Each result reports known contributions, conditional contributions and unresolved effects. Conditions use true / false / unknown; unknown is not false. Preserve signed values and units. Keep master, avatar, automaton and other supported recipients separate. Unsupported text without a reliable stat scope conservatively affects the completeness of the result, rather than silently disappearing.

An equipment total is not a full character statistic. Job traits, merits, food, buffs, enemy defenses, effective damage and simulator outputs are outside the first delivery. A scenario toggle evaluates a supported conditional equipment effect only. A capped/effective value can be shown only after its full required context and mechanics are supported; the uncapped equipment contribution remains distinguishable.

Rules require stable IDs, versioned evidence, recognized text/context, units, operation, recipient, item/loadout scope, conditions, stacking/rounding policy and independently derived fixtures. A matching expression alone is insufficient. Unsupported forms remain visible with the original text. Input/resource changes invalidate affected cached interpretations.

## Next checks

Obtain public retail mechanics evidence for the first flat/defensive/Refresh families, independently calculate small examples, then add physical, casting and pet families. Test duplicate allocation, multiline recipient scope, mutually exclusive conditions, unknown ranges and one loadout bonus before expanding numeric coverage. The existence of this matrix does not satisfy the supported-rule evidence gate.

## Independent evidence continuation: 2026-11-03

The two resource hashes for `items.lua` and `item_descriptions.lua` were read back and match the snapshot above. Specific item rows were inspected as data, without evaluating Lua. No numeric rule is certified by this continuation.

| Evidence ID | Public source and precise locator | What it establishes / does not establish |
|---|---|---|
| E-FLAT-01 | [Stikini Ring +1, item 26184](https://www.ffxiah.com/item/26184/stikini-ring-1), description/equip block | Independently displayed MND 8, magic accuracy 11, all-magic skill 8 and Refresh 1 agree with local descriptions. Level 99, all 22 jobs. Does not independently demonstrate additive behavior or enumerate the skill family. FFXIAH may share client-derived input, so matching text is corroboration, not independent mechanics testing. |
| E-DT-01 | [Defending Ring, item 13566](https://www.ffxiah.com/item/13566/defending-ring), description/equip block | Displays DT -10%, Rare/Ex, level 70/all jobs; agrees with local rows. One generic signed percentage-point contribution is a candidate. Internal quantization, final-damage rounding, category interactions and caps remain unverified. Two equipped Defending Rings are not a legal duplicate fixture. |
| E-REF-01 | [My Rdm is coming out of hiding](https://forum.square-enix.com/ffxi/threads/42970-My-Rdm-is-coming-out-of-hiding), Crimsonwizard post 2, June 26, 2014 | First-person community explanation identifies equipment Refresh units as MP per tick and gives an additive multi-item example. Player report on the official forum, not a developer statement or instrumented test. Supports a narrow candidate gear-contribution rule; does not verify Stikini specifically or establish timing by itself. |
| E-REF-02 | [Incorrect Description of Equipment Properties](https://forum.square-enix.com/ffxi/threads/28035-Incorrect-Description-of-Equipment-Properties?p=369483), Llana_Virren posts 3/5 and Ordostrillicus post 7, October 2012 | Player reports distinguish Heka body Refresh 1 from a pair bonus 2. Developer post confirms removal of misleading improved wording, not the player's numerical test. Preserve that authority distinction. Bare Adds Refresh text cannot safely imply magnitude 1; set effects require a sourced membership rule. |

Evidence candidates are scoped to retail-facing originals. A forum's domain does not turn player replies into official mechanics documentation. No private-server implementation or author simulator code was used as a mechanics oracle.

### Independently derived expected examples (specifications, not executed tests)

Expected arithmetic below was derived directly from the stated inputs rather than from a future parser's output. Each row says which mechanics assumption still prevents certification. A supported contribution does not establish complete item/loadout results.

| Fixture ID | Explicit inputs | Independent expected result | Remaining gate |
|---|---|---|---|
| FLAT-PAIR-01 | Two allocated Stikini +1 copies, one in each ring slot; only their described base attributes | MND `8 + 8 = 16`; direct magic accuracy `11 + 11 = 22`; all-magic skill family `8 + 8 = 16`. Never report magic accuracy 38 by adding skill points to direct accuracy. | Flat-addition semantics and exact skill-family expansion need independent mechanics evidence. No effective spell accuracy or full-loadout claim. |
| REF-PAIR-01 | Same two distinct rings; unconditional, non-augmented gear Refresh only | Candidate gear contribution `1 + 1 = 2 MP/tick`. Spell potency/duration equipment is a different effect and excluded. | E-REF-01 supports stacking, but direct two-ring observation and independently attributable timing evidence remain open. Do not convert to MP/second yet. |
| REF-COPY-01 | Two ring requirements, only one observed physical copy | Owned-mode allocation cannot satisfy both slots. Known allocated contribution is at most one ring; target/planning two-ring arithmetic stays explicitly hypothetical. | Future allocation/effect integration fixture. Never sum both target rows as owned gear. |
| DT-CONTRIB-01 | One Defending Ring; no other selected pieces | Described equipment DT contribution `-10 percentage points`; no effective damage value. | E-DT-01 verifies display only. Do not infer that an arbitrary 1000-point incoming hit becomes exactly 900. |
| REF-SET-01 | Historical candidate pair: Heka body and qualifying Nefer head; player-reported base 1 and pair bonus 2 | Conditional candidate: body alone `1`; head alone `0` base Refresh; pair `1 + 2 = 3`, not `1 + 2 + 2 = 5 MP/tick`. | E-REF-02 supports an exception-shaped example, not a certified rule. Verify exact item IDs/NQ/HQ membership and magnitudes independently before enabling it. |
| UNKNOWN-01 | A selected item has unquantified Adds Refresh or unsupported set-bonus wording | Preserve unresolved text; no numeric zero or assumed 1. Known contributions from other pieces remain inspectable with incomplete Refresh. | Conservative result contract, not a retail numerical assertion. |

Percent signs do not authorize effective arithmetic. Store described DT as a separate signed equipment contribution; keep PDT, MDT, BDT and their II variants separate until their combination rules are verified. Modern guide examples and repeated forum opening posts are leads, not independent cap/rounding evidence. This pass does not certify caps, a generic bare-Refresh parser, all-magic-skill expansion or a complete flat-stat family.

### WHM pilot conditional effects

The coverage document records exact slots for the WHM pilot. All observations below were checked against its selected local item-description rows; public references corroborate specific descriptions or provide clearly qualified mechanics evidence.

| Effect / item | Evidence and candidate interpretation | Boundary before numeric support |
|---|---|---|
| Unconditional described Refresh | Local Daybreak 22040 `+1`, Homiliary 22268 `+1`, Ebers Bliaut +3 23489 `+4` | Independently derived described subtotal `1 + 1 + 4 = 6`, under the proposed additive rule. This is not the set's total or measured MP recovery. Other selected effects remain unresolved. |
| Latent Refresh: Fucho-no-Obi 28452 | [Item page](https://www.ffxiah.com/item/28452/fucho-no-obi) displays latent Refresh 1. A search-indexed original comment by Asura.Milkmanskid, March 25, 2014, reports testing below 50% MP and an unusual subset of MP-bearing slots; Bismarck.Ihina's April 25 reply supplies a counterexample to using displayed max MP unchanged. | Full direct page extraction did not expose comments. Record as a primary-report lead seen in search, not a fully verified formula. Do not implement `current MP <= displayed max MP / 2`; denominator, boundary equality, MP-percent gear and excluded slots need exact verification. Unknown scenario keeps the effect conditional/unknown. |
| Unity Refresh: Assid. Pants +1 28135 | [Item page](https://www.ffxiah.com/item/28135/assid-pants-1) agrees with local range 1–2. [December 2014 update discussion](https://www.ffxiah.com/forum/topic/45167/update-12914-superior-1-additions/) contains player explanations about Unity ranking. | Unity standing is different from the item's augment rank. No complete ranking-to-magnitude mapping or endpoint rounding is established. Preserve a range/unknown, never assume 2 or synthesize it from Rank 15. |
| Moonshade Earring 11697 | [Base item page](https://www.ffxiah.com/item/11697/moonshade-earring) supplies no numeric Refresh. The local description row is absent; its item row alone establishes identity/eligibility. | Source's bare item name does not establish a particular chosen augment or its latent. An absent base description is unavailable data, not proof of no effects. Require sourced augment options and explicit requirement/observation before counting Refresh. |
| Inyanga loadout bonus | Local head/hands/feet/ring each display a Refresh set-effect line. [April 2017 original discussion](https://www.ffxiah.com/forum/topic/50675/april-2017-version-update/7/), Odin.Calipso April 4 at 22:10:49 and April 5 at 01:37:36, directly reports hands +2 plus ring giving one MP/tick of auto-refresh. | A useful first-person two-piece observation. It does not verify this four-piece combination, all NQ/HQ mixing or the six-piece cap. A later post in the same thread speculates on six pieces; do not promote that extrapolation to a test. Count qualifying pieces once at loadout scope only after membership/threshold evidence is complete. |
| Defensive described contributions | Local descriptions give generic DT `-10 -6 = -16` (ring/neck); PDT `-10` (shield); MDT `-5 -4 -3 -2 -3 = -17` (head/hands/feet/ring/ear). | Independent raw-label arithmetic, excluding unknown augments; three separate categories. No final reduction, cap verdict or whole-loadout completeness. Do not sum the three into a generic DT number. |

New fixture specifications: **WHM-PARTIAL-01** must retain the known described Refresh subtotal with unresolved latent/ranking/augment/set effects; **WHM-SCOPE-01** must keep the feet's Avatar Blood Pact effect separate from the master and from the following loadout set line. A line break alone cannot close recipient scope, while a verified Set boundary cannot inherit Avatar scope blindly. **WHM-RANK-01** must distinguish Unity standing from item augmentation rank. None has been implemented or passed.

This real source pilot demonstrates why exact slots and eligibility are insufficient for numeric certification. The next evidence task is the Inyanga membership/threshold matrix and direct Fucho denominator tests, alongside a verified basic additive rule; no unknown was replaced with zero.

### Conditional Refresh follow-up: evidence and bounded candidate rules

Checked 2026-11-03. These are evidence-backed candidates for review, not implemented/certified rules. Distinguish original player observations from secondary reference summaries; agreement between pages on one wiki is not independent corroboration.

**Inyanga:** [Pergatory's January 9, 2020 post, 10:51:22](https://www.ffxiah.com/forum/topic/44724/on-healing-hands-a-comprehensive-whm-guide-v2/94/) states that adding the ring to five +2 armor pieces supplies no further Refresh. Aerison's following reply describes using four armor pieces plus ring. This later original discussion contradicts the *speculative* six-piece extrapolation in the April 2017 thread; retain the earlier observed two-piece result, not its guessed maximum.

The Japanese retail [Inyanga reference, HQ2 section](https://wiki.ffo.jp/html/36226.html) explicitly describes two pieces giving 1 MP per three seconds, each additional qualifying piece adding one, capped at four with five pieces; six equipped pieces do not increase it further. This is secondary mechanics evidence, consistent with the original two-piece observation and later cap discussion, but not a published controlled test of every combination. The [combination reference](https://wiki.ffo.jp/html_2006/23620.html) also distinguishes +2/accessory membership from NQ/+1 armor. It shares the same publisher and is not an additional independent test.

Read-only local item/description checks resolve a proposed exact membership list:

| Slot family | Qualifying +2/accessory item | ID |
|---|---|---:|
| head | Inyanga Tiara +2 | 25577 |
| body | Inyanga Jubbah +2 | 25793 |
| hands | Inyan. Dastanas +2 | 25831 |
| legs | Inyanga Shalwar +2 | 25882 |
| feet | Inyan. Crackows +2 | 25949 |
| ring | Inyanga Ring | 26207 |

Use exact IDs, never a name-prefix test. As a negative control, local Tiara NQ 25665 and +1 25666 lack the set-effect line. Item descriptions establish wording and identity, not numeric mechanics. No other lookalike/version is automatically a member; unexpected later versions require new evidence.

Candidate **refresh.inyanga.loadout.v1**: master recipient, loadout scope, integer MP/tick, unconditional once qualifying selected pieces are known. Proposed contribution is `min(4, max(0, n - 1))`, evaluated once for the entire composed loadout. This is a formula derived from the evidence above, not copied simulator logic. Count distinct legally selected pieces; a set alias is not another piece and an impossible second Rare ring cannot increase the count. Unknown selected slots make membership completeness uncertain. No spell Refresh potency increase is implied.

| Fictional fixture | Independently expected candidate contribution | Evidence limit |
|---|---|---|
| INY-COUNT-01: n = 0, 1, 2, 3, 4, 5, 6 | `0, 0, 1, 2, 3, 4, 4 MP/tick` | Two-piece original observation, later original cap report and secondary intermediate thresholds; not seven executed tests. |
| INY-PILOT-01: selected head +2, hands +2, feet +2, ring | Four members -> one loadout contribution of `3`; not `3` attached to each of four items | Four-piece threshold lacks a direct controlled observation in the inspected originals. |
| INY-NEG-01: Tiara +1 plus hands +2 and ring | Two qualifying members -> `1`, not `2` | Exact-ID membership proposed from secondary description and resource wording; verify mixed-tier cases before certification. |
| INY-SIX-01: five +2 armor pieces plus ring | Still `4`; no sixth-piece increase | Explicit later community cap report; early guess of `5` is not accepted. |

**Assiduity:** The [HQ section of the Japanese retail reference](https://wiki.ffo.jp/html/32493.html) explicitly says the +2 Refresh value occurs only at Unity rank 1. An independently authored [Summoner equipment article, idle section](https://from20020516.hatenablog.com/entry/2016/07/25/170000) likewise qualifies the displayed +2 as first-place Unity only, otherwise +1. These provide a precise review candidate, not an instrumented rank-transition test. The URL's date is not treated as the article's last modification date.

Candidate **refresh.assiduity-hq.unity.v1** for item 28135: with verified Unity membership/standing context, rank 1 -> `2`, other valid ranks -> `1 MP/tick`; unknown standing -> unresolved described range `1–2`. No affiliation/invalid rank remains unsupported, not assumed zero or one. Keep equipment augmentation rank/path independent. Fixture **ASSID-RANK-01**: Unity rank 1 with item augment rank 0 -> candidate 2; Unity rank 2 with item augment rank 15 -> candidate 1; item rank 15 with unknown Unity standing stays unresolved. None was run.

**Fucho:** [The item reference](https://wiki.ffo.jp/html/31075.html) cautiously describes activation at half MP or below; its [latent-effect index](https://wiki.ffo.jp/html_2006/1768.html) instead uses strictly below half. Neither specifies the denominator exclusions reported by the original item comments. Thus even mutually similar summaries do not settle equality or which MP modifiers count.

Independently recomputing the indexed original comment's numbers gives `575/1126 = 51.07%` and `575/1156 = 49.74%`. These explain why a displayed-MP threshold could classify the same reported stopping point differently. They do not reveal the exact latent formula or a tick boundary. **FUCHO-BOUNDARY-01** must eventually distinguish just-below/equal/just-above the *verified* threshold, holding other Refresh sources and tick phase constant; **FUCHO-MP-01** must vary excluded-slot flat MP, included-slot flat MP, percentage MP and negative MP separately. These are proposed evidence protocols, not instructions executed in game or a request to change player gear now. This latent remains unsupported for automatic condition evaluation; an explicit hypothetical active/inactive assumption must stay labeled and does not establish the formula.

Under the candidate Inyanga rule, the pilot's previously described Refresh subtotal 6 would gain one loadout bonus 3 -> `9`, before Unity, latent and augment effects. That is candidate arithmetic with declared assumptions, not a certified total, range, live MP rate or complete-loadout result. Fucho and Moonshade remain unresolved; candidate Unity behavior is now concrete enough to review. No numeric support gate has been declared satisfied.

### Browser-readable mechanics: units and defensive categories

Checked 2026-11-03. Ordinary browser access resolved the research fetch's 403 for these pages. These revision-pinned secondary references add mechanics evidence; they do not become controlled original tests merely because they are readable.

| Evidence ID | Revision and precise scope | Consequence for rule specifications |
|---|---|---|
| E-REF-03 | [Refresh (Status), revision 775074](https://www.bg-wiki.com/index.php?title=Refresh_(Status)&oldid=775074), footer August 7, 2026; Description and Refresh Equipment sections | Defines a tick as three seconds, distinguishes gear recovery without a status icon from named spell/item statuses, and lists Stikini +1 as 1 MP/tick. This supplies the previously missing attributable timing reference. Named Refresh status effects typically overwrite rather than stack; do not apply gear-addition rules to spell potency, duration or status overwrites. The equipment list's omissions do not prove an omitted item's effect absent. |
| E-DT-02 | [Damage Taken, revision 736655](https://www.bg-wiki.com/index.php?title=Damage_Taken&oldid=736655), footer June 7, 2025; opening and type-specific sections | Describes ordinary DT as additive within physical, magical and breath categories, with a 50% ordinary category cap and separate bypass exceptions. Describes /256 quantization and a special interaction between augmented MDT and breath reduction. A single generic DT sum cannot represent these mechanisms or prove final damage. |

For REF-PAIR-01, E-REF-01 plus E-REF-03 now supports the proposed unit and basic additive interpretation: two explicitly allocated base Stikini +1 contributions give candidate `2 MP per 3-second tick`. The absence of a direct controlled two-ring observation remains recorded; neither spells nor elapsed-time recovery are part of this fixture. Do not report a guaranteed two MP gained during an arbitrary three-second observation window, which can be affected by tick phase, MP cap and equipment changes.

For defensive analysis, retain separately (1) described signed equipment contributions, (2) any supported category combination/cap operation, and (3) final incoming-damage mechanics, which remain outside initial delivery. A cap label requires supported applicable gear/conditions and quantization; an ordinary 50-point cap does not justify clamping every individual label or treating DT II as ordinary DT. Master/pet applicability also needs its own evidence. No calculator implementation or effective-defense certification follows from this reference.

New independent fixture specifications: **DT-CATEGORY-01** uses fictional described inputs DT -10 and PDT -5; the raw categories remain `DT=-10`, `PDT=-5`, and a candidate ordinary physical sum is -15, while magic/breath receive only the generic -10 absent other supported effects. **DT-SCOPE-01** adds an unsupported MDT augment: the breath category becomes incomplete rather than assuming that augment contributes zero. **REF-KIND-01** combines base gear Refresh 1 with a spell-duration modifier: only the gear line enters the equipment MP/tick subtotal. These examples specify separation and uncertainty, not exact damage outputs or executed tests.

The linked original [GearInfo discussion](https://www.ffxiah.com/forum/topic/52145/finally-releasing-this-addon-gearinfo/8/#3344204) was subsequently inspected. Martel's May 8, 2018, 19:06:48 post supplies a no-DT/BDT control target, a separate test target and paired Balaur breath logs. Observed pairs include 210/204, 420/408, 210/201 and 210/184. Their damage differences are not exact integer-percent multiplication. Gear configurations reside partly in an image, so these logs alone do not establish each augment's exact internal value. The author explicitly allows possible exceptions; do not turn the reported generalization into an unbounded parser rule. Chiaia's following reply reports earlier corroboration without reproducing its data. The same page records a Luopan-DT-to-player-DT attribution bug, demonstrating the need for recipient separation independently of the wiki summary. No addon code was used as a mechanics oracle.

### Representative physical, casting and pet rule candidates

This expands T1's model coverage without claiming complete numeric support. Local item-description observations were read as data. Item-page agreement may share client-derived text and is distinguished from mechanical tests.

| Candidate rule / recognized context | Evidence, units and operation | Independently expected fixture / open boundary |
|---|---|---|
| `physical.multiattack.described.v1`: exact Double Attack / Triple Attack base labels on Epona's Ring 11651 | [Item page](https://www.ffxiah.com/item/11651/eponas-ring) agrees with local DA 3%, TA 3%. [Double Attack revision 778573](https://www.bg-wiki.com/index.php?title=Double_Attack&oldid=778573), September 13, 2026, separates rate enhancement from double-attack damage enhancement and describes limits on attack events. Proposed separate signed percentage-point keys, master/item scope, additive raw contributions only, no rounding at this layer. | **MULTI-BASE-01:** one Epona -> DA +3 and TA +3 separately; never one +6 proc chance. **MULTI-KIND-01:** Double Attack damage +20 must not match the DA-rate rule. Effective proc ordering/distribution, traits, attack-round limits and damage are outside these totals. Two Epona rings are not a legal duplicate fixture. |
| `casting.fast-cast.described.v1`: exact base Fast Cast label, excluding spell-specific time reductions, Quick Magic and enhanced-effect wording | [Fast Cast revision 780482](https://www.bg-wiki.com/index.php?title=Fast_Cast&oldid=780482), October 9, 2026, distinguishes cast/recast effects, equipment timing and whole-percent recast rounding. It lists base and maximum augment values separately. Proposed master/item signed percentage-point contribution; sum raw supported equipment values without clamping the equipment subtotal. | **FC-BASE-01:** explicit fictional base contributions 10 and 5 -> raw equipment FC +15. **FC-KIND-01:** Cure spellcasting time -7 and Quick Magic +2 remain separate effects, not FC +9. **FC-AUG-01:** Merlinic Hood's displayed base 8 plus an explicitly specified supported augment 5 would give 13; unspecified augment does not become its published maximum 7. This does not certify final cast/recast time, gear-swap timing or an 80% effective-cap verdict. |
| `recipient.pet-accuracy.base.v1`: Nyame Helm 23761, multiline Pet boundary | [Item page](https://www.ffxiah.com/item/23761/nyame-helm) corroborates master accuracy/ranged accuracy/magic accuracy 40 each, followed by pet 50 each. Proposed separate flat-point effects under master and pet; recipient continues across the three pet lines. | **PET-SCOPE-01:** master accuracy 40 and pet accuracy 50, never master 90. Ranged accuracy and magic accuracy likewise remain separate keys. No derived hit rate or universal assumption about which pet types benefit. All unrelated lines retain their own completeness status. |
| `recipient.avatar-accuracy.base.v1`: Indomitable Coat 24155, multiline Avatar boundary | [Item revision 755417](https://www.bg-wiki.com/index.php?title=Indomitable_Coat&oldid=755417) agrees with local master magic accuracy 42, FC 10%, DT -6%, followed by avatar accuracy/ranged accuracy/magic accuracy 42 and critical rate 8%. Proposed master/avatar scope separation; flat points versus percentage points remain distinct. | **AVATAR-SCOPE-01:** master magic accuracy 42 and avatar magic accuracy 42, not master 84; avatar critical +8, not player/automaton +8. **AVATAR-AUG-01:** presence of an augmentation system does not supply actual selected/observed augments. SU5 requirement is explicit on the item page; passing a job mask alone does not prove equip readiness. |

These are scoped candidate rules with concrete expected data, not broad regex permissions. Recognized base text does not certify every effect on the item. New wording, resource changes, augment variants, recipient ambiguity and unknown conditions invalidate the affected interpretation instead of falling back to zero or maximum magnitude.

The cited Fast Cast page links [Mojo/Byrth recast testing](https://www.bluegartr.com/threads/103597-Temporary-Random-Facts-Thread?p=4654357&viewfull=1#post4654357); direct research fetch was inaccessible. The secondary rounding statement is recorded, but exact effective-recast support remains open. No source simulator or addon implementation was substituted for that evidence. Remaining T1 work is to review the narrow supported subset, unresolved effects and compatibility fixtures together with consolidated job exceptions; T7 retains full catalog authoring.
