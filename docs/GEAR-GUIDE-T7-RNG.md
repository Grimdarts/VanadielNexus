# T7 RNG bounded candidate milestone

Date: 2026-11-04. Jason authorized RNG after approving BRD; the older stop-at-BRD
boundary is superseded for this batch only. Nova handled RNG directly; Vesper
remained unassigned. Existing checkout/branch/HEAD and all prior work preserved.

**30 Nexus-authored RNG compositions reconcile the ten tracked RNG priorities
in explicit, bounded contexts.** This is composition verification in an offline
candidate. It does not establish current BiS, every tier, complete numeric effects,
timing, inventory ownership, supply, safe runtime swaps or all-job completion.

## Obligations and declared contexts

| Tracked priority | Candidate keys | Bounded context |
|---|---|---|
| DT Idle | dt-idle | Naegling/Nusku, retained exact Fomalhaut, Nyame protection, ammo intentionally empty; no DT cap |
| Refresh Idle | refresh-idle | RNG/WHM99/49 with useful MP; Null Masque and two physical Stikini +1 copies; no latent/citizenship/Unity maximum |
| Ranged TP | ranged-tp, ranged-dt, double-shot, critical-armageddon, critical-gandiva, critical-gastraphetes, critical-double-shot, barrage | Ordinary/defensive, ability-active and three weapon-specific AM3 contexts; these are separate states |
| Ranged accuracy | ranged-accuracy | Full Fomalhaut/Chrono Bullet assembly applying the source's partial accuracy swaps; no hit-rate guarantee |
| Preshot | preshot-standard-f0/f1/f2, preshot-gastraphetes-f0/f1/f2 | No Flurry, Flurry I and Flurry II distinguished for exact Fomalhaut versus Gastraphetes; no inferred cap |
| Physical ranged WS | last-stand, coronach, jishnu, namas, apex-arrow | Exact equipped weapon/action access, expendable matching ammo; AGI/STR/DEX and critical/WSD cape variants explicit |
| Magical ranged WS | trueflight, wildfire, hot-shot, flaming-arrow | Magic versus hybrid contexts; single base Malevolence/shield, unconditional belt/earring replacements; no weather/distance assumption |
| Supported melee Balanced | melee-balanced, savage-blade | RNG/WAR99/49 sword/shield, Velocity Shot off; ranged weapon retained and ammo empty; no Dual Wield or TP-bonus bow |
| Supported melee DT | melee-dt | Defensive accessories replace STP/accuracy priorities; no DT/haste cap |
| Supported melee Accuracy | melee-accuracy | Explicit fixed accuracy accessories; no inferred landing rate |

Every full recommendation declares 16 canonical slot states. The six deliberate
ammo empties are in melee/idle; they do not rewrite the source's placeholders.
No automatic ability overlay, ranged weapon switch, ammo guard or GearSwap command
is implemented by these targets. Ranged contexts do not certify Velocity Shot
percentages or Hover Shot stacks. Melee explicitly turns Velocity Shot off.

## Exact weapons, ammunition and access

| Exact base resource | ID | Selected expendable ammunition / role |
|---|---:|---|
| Fomalhaut | 21485 | Chrono Bullet21296; Last Stand / standard preshot / ranged TP |
| Gastraphetes | 21266 | Quelling Bolt21311; crossbow preshot, Trueflight, Barrage and separately active mythic AM3 |
| Annihilator | 21267 | Chrono Bullet21296; Coronach; this gun dispenses Eradicating bullets, **not** the selected Chrono bullets |
| Armageddon | 21269 | Devastating Bullet21325; Wildfire and separately active empyrean AM3 |
| Gandiva | 22116 | Chrono Arrow21297; Jishnu and separately active empyrean AM3; Chrono supply comes separately from Fail-Not |
| Yoichinoyumi | 22115 | Chrono Arrow21297; Namas; this bow dispenses Yoichi's arrows, **not** the selected Chrono arrows |
| Fail-Not | 22117 | Chrono Arrow21297; Apex/Flaming Arrow |

All seven are exact **base afterglow/aeonic checkpoints**, deliberately different
from the replacement guide's Augmented weapon links. No rank or augmented-stage
magnitude is credited. Display names alone cannot select these stages. Base stages
with Dispense are distinct from augmented successors that move ammunition generation
to separate waist items. The public cards and local resources match these exact IDs;
that does not establish ownership or a working supply chain.

Bullets, bolts and arrows are consumable. Crossbow and gun both have resource
skill26; matching the skill number is insufficient to establish ammunition
compatibility. This batch independently checks Gastraphetes/bolt, guns/bullets and
bows/arrows. The existing service validates identity/job/slot/hand composition;
it does **not** implement a general ammo-family or consumption safety policy.

Double Shot's [ability page revision773759](https://www.bg-wiki.com/index.php?title=Double_Shot&oldid=773759)
describes extra ammunition and excludes WS. It shares a recast with
[Unlimited Shot revision752272](https://www.bg-wiki.com/index.php?title=Unlimited_Shot&oldid=752272).
[Barrage revision764379](https://www.bg-wiki.com/index.php?title=Barrage&oldid=764379)
conflicts with Unlimited Shot. No capped Recycle, free shot, protected rare-ammo
macro, projectile count, proc rate or replenishment sufficiency is certified.
Hauksbok/stat-ammo shooting and Sparrowhawk TP-bonus setups remain unclaimed.

Equipped weapons supply their named WS access in these declared contexts.
Hot Shot and Flaming Arrow still require the learned action. Active aftermath
is a separate prerequisite: equipment is not evidence that the status exists.
Gastraphetes AM3 differs from empyrean AM3; no status is inherited when switching
weapons. Establishing/maintaining aftermath and any main/sub/ranged weapon changes
require separate TP-loss, buff and live sequencing review.

Main/sub additions are exact Perun+1 **20805** (axe), Malevolence **20595** (dagger),
and Nusku Shield **26421**. Public type/slot/skill evidence was read; prior19 hand
records remain AST-identical. Registry: **22 / hands.2026-11-04.v6**. Main/sub
recommendations use a shield; no Dual Wield prerequisite is silently inferred.

Oshosi pieces require RNG's **Superior3 designation**. Local resource eligibility
alone cannot establish job-point access. Amini Earring+2 is deliberately in the
right ear, with no random augment credited. Neither Tonberry Grudge critical
magnitude nor Sroda's alter-ego attack is assumed. These conditional base effects
remain visible limitations rather than invented numeric contributions.

## Original sources, omissions and conflicts

Primary source: [Shoot - Aww Made You Look revision689561](https://www.bg-wiki.com/index.php?title=Shoot_-_Aww_Made_You_Look&oldid=689561),
observed footer October4,2023. All **35 rendered equipment grids** and their
accompanying notes were read in ordinary Chrome and manually structured. They
are transcriptions/paraphrases, **not raw HTML/full DOM captures**. Their hashes
fingerprint recorded observations, not immutable live webpage bytes. Currency
remains unknown.

[Kunami node365](https://www.ffxiah.com/node/365) explicitly retires itself and
names the BG replacement. Its action/weapon context and Snapshot/Snapshot note
remain historical corroboration. Its claims about caps, merits and damage do not
become verified rules or a current recommendation from this read.

Preserved source distinctions:

- All six preshot grids select nine items and omit seven, including the range
  cell even in the Gastraphetes section. Category placeholders are not empties.
- Accuracy swaps select seven slots; Double Shot selects six; True Shot selects
  four and explicitly calls for Ikenga clogs R15+. These stay partial observations.
- The guide preamble assumes maximum Unity/JSE-neck augments. Nexus uses explicit
  base checkpoints and does not transfer those maximum effects. Iskur replaces
  the TP neck; preshot retains base Scout's Gorget+2 without a cap claim.
- Source Coronach NQ uses AGI cape, HQ uses STR. Source Jishnu uncapped uses
  STR/WSD, its alternate uses DEX/Crit. Both original choices survive; Nexus's
  DEX/Crit Jishnu is separately attributed.
- The Namas & Apex heading contains only Namas grids. Apex is a separately authored
  Nexus AGI/physical archery checkpoint, not a claimed source Apex transcription.
- Cohort Cloak's head placeholder, dual augmented Malevolences, unknown Herculean
  magnitudes, Moonshade choices, Orpheus/Hachirin and weather-ring options remain
  source details. Fixed single-dagger/shield, belt and earring replacements are
  explicit Nexus decisions; no source-author endorsement is implied.
- Melee TP, Evisceration and Misc Sets headings have no compositions. The three
  supported melee priorities and both common idle obligations use separately
  attributed Nexus assemblies with independently checked gear, not empty headings
  presented as source loadouts.

BG reader403 and several public item-reader errors were resolved through ordinary
Chrome for the named source/card reads. A later wiki access search encountered
security verification; no challenge was solved and no unread result was claimed.
No browser setting changed. No access failure became N/A. All **57 newly selected
resource IDs** had independent ordinary-Chrome public base-card checks.

## Augments checked before save

The strict matcher compares whole decoded parts and multiplicity. Source totals
are not native parts. The public Windower extdata library was read, never executed;
its SHA-256 is in the RNG item packet. No player Lua or inventory was accessed.

- Ranged cape: AGI20 + AGI10; combined `Rng.Acc.+20 Rng.Atk.+20`; explicit STP10,
  WSD10 or Crit10 Sap variant. STR/DEX variants remain purpose-specific.
- Magic cape: separate stat20/stat10 plus combined magic accuracy/damage20 and WSD10.
- Melee capes: separate DEX/STR20 and10, combined Accuracy/Attack20, STP10/WSD10,
  and DT5. These are different required copies.
- Belenus preshot cape: one `"Snapshot"+10` part, supported by its Sap category.
- Taeon head: **two `"Snapshot"+5` parts**, independently supported by Leaf and
  Dusk categories in [Alluvion Skirmish Armor revision715143](https://www.bg-wiki.com/index.php?title=Category:Alluvion_Skirmish_Armor&oldid=715143).
  A single summary10 or a single5 fails. The prior BRD error was prevented here
  before publication, rather than repaired by rewriting an immutable revision.
- Carmine D, Adhemar D, Pursuer A and Nyame B are explicit paths; **rank unspecified**.

The [Belenus Cape categories revision568477](https://www.bg-wiki.com/index.php?title=Belenus%27s_Cape&oldid=568477)
support the separately selected augment categories/magnitudes. Independent literal
fictional-copy checks passed before save for11 augment variants,4 paths,
duplicate-copy allocation and negative summary-total/missing-part cases. This is
matcher verification; no live owned copy is certified.

## Artifacts and preservation

- `docs/catalog/gear-guide-t7-rng-definitions.json`:30 full explicit definitions.
- `docs/catalog/gear-guide-t7-rng-observations.json`:35 original grids, accompanying
  notes/options, omissions, conflicts and hashed paraphrased guide findings.
- `docs/catalog/gear-guide-t7-rng-item-evidence.json`:57 exact public-card checks,
  ability/stage/augment locators and public-library encoding hash.
- `docs/catalog/gear-guide-t7-rng-readback.json`:independent baseline/history,
  resource, hand and protected-input readback.
- `.t7-rng-checks/baseline/` and manifest:37 affected-input byte backups/hashes.
  Task-local authoring, pre-save validation and isolated-test launcher also remain.

Candidate: **194 sets /205 historical revisions /345 sources**. **186 effective
current compositions**: WHM23/SCH28/BLM22/RDM38/GEO17/BRD28/RNG30. Eight original
unresolved revisions and all eleven withdrawn initial BRD augment encodings remain
unchanged. Generic service summary counts **197 stored verified flags**, including
those eleven withdrawn records. Loader retirement behavior is unchanged; this
partial candidate must not be published to the production picker.

Coverage: **225 rows /86 included /139 gaps across15 remaining jobs /zero N/A**.
Only the ten RNG rows changed. Historical stored slots: **3,081 selected +173
intentional empty**; historical counts include withdrawn revisions. All prior
164 sets/175 revisions/278 sources, both amendment trails, authoring batches and
380 resource records/descriptions are unchanged. Resource packet now **437**.

Four upstream resource file hashes and fingerprint unchanged:
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.
Production v1 unchanged:
`54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85`.

## Validation and boundaries

Whole actual-resource preparation and independent history/resource/protected-input
readback passed. Focused final suite: **173 passed /0 failed /0 skipped in7.83s**.
The first focused attempt had171 passes and two older coverage assertions still
excluding RNG from the authored-job list; those assertions were updated without
changing source records, behavior or prior job-specific evidence assertions.

Full isolated native suite: **951 passed /0 failed /0 skipped in121.95s (2:01)**.
No core/UI/test/tool change followed this run. `git diff --check` passed; existing
LF/CRLF notices are warnings only. Fresh task-local
TEMP/TMP/VN_DATA_DIR/basetemp, redirected discovery, disabled inventory seeding;
real-file launcher `.t7-rng-checks/isolated-checks.py`. No player persistence loaded.

Unclaimed: every gear tier, prime/throwing weapon contexts, augmented REMA ranks,
Su5 branches, dual wield/Kraken, Evisceration/Aeolian full recommendations, rare
stat-ammo protection, true-shot distance/rank thresholds, all utility/JA niches,
active buff detection and complete live weapon/TP/MP/ammo transitions. Included
priorities are bounded compositions, not N/A dispositions for these variants.

No architecture/service/UI change beyond three appended exact hand records.
Existing job tests changed only shared catalog counts/remaining-job expectations
and the hand-registry size check. New RNG regressions preserve exact stage/ammo,
native augment parts, source conflicts/omissions and ability/access boundaries.

No subagent/Vesper task, reset/stash/clean/branch switch/worktree, commit/push,
build/install/release, production replacement, migration, game command or Lua
activation. Windower/player files stayed read-only. Branch/HEAD remains
`codex/sets-copy-fixes-review` /`5657f2092c0e0d84331d0741b1518669201e25d4`.
T8/T9 and human/frozen/live gates remain. **Stop after RNG; no next job started.**
