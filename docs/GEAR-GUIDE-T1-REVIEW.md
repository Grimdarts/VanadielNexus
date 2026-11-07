# T1 consolidated review: coverage, rules and contracts

Date: 2026-11-03. Status: ACCEPTED by the user for specification purposes. The user approved this packet and authorized T2–T3 core implementation in a new session. Other implementation, visual, migration, commit, build/install, release and Lua activation gates remain in place.

This is the decision packet for the [approved plan's T1 gate](GEAR-GUIDE-IMPLEMENTATION-PLAN.md). Supporting detail is in the [source/equipment ledger](GEAR-GUIDE-T1-COVERAGE.md), [rule evidence and independent expected results](GEAR-GUIDE-T1-STAT-RULES.md), and [catalog/workspace compatibility contracts](GEAR-GUIDE-T1-CONTRACTS.md). It resolves the proposed initial scope without treating every researched candidate as implemented or every source as current.

## Recommendation for this review

Accept the 22-job coverage obligations below, the bounded initial equipment-rule subset and the proposed compatibility contracts. No blanket job-level idle exception is proposed. Retain all named evidence gaps as explicit unsupported effects or T7 catalog-authoring work. Acceptance of this packet establishes the specification; it does not approve app-code changes, visual layouts, real-data conversion, commits, builds, installation, release or Lua activation.

Full verification of every playable composition belongs to T7. T1 establishes what must be covered, the evidence standard, representative checked compositions, rule applicability and reproducible acceptance cases. Do not require the entire T7 catalog to exist before T1 can be reviewed, or weaken T7 because source discovery is complete.

## Consolidated 22-job coverage

For **every job**, DT Idle is required. Refresh Idle is required whenever the declared main/subjob/equipment setup uses MP and recovery is useful. A context without useful MP recovery may receive a specific N/A disposition supported by that context; none is pre-assigned to an entire job here. A missing source is a gap, never an N/A reason. Engaged coverage evaluates Balanced/DT/Accuracy priorities for applicable weapon/role contexts. Niche roles remain labeled niche. Automatic spell, ability and buff overlays remain separate from manual priorities.

The following table specifies required research/authoring groups beyond those common idle obligations. Its evidence column describes what is actually available, rather than claiming all those groups already have verified targets.

| Job | Required groups beyond common idle | Context that must survive into each revision | Evidence disposition / remaining authoring |
|---|---|---|---|
| WAR | Engaged, physical WS, defensive/utility | Weapon, Fencer, attack assumptions | Original WAR source inspected; exact current idle/combat revisions remain T7 work. |
| MNK | Engaged, physical WS, Subtle Blow/defensive | Impetus, Footwork, hand-to-hand | Historical tables and 2026 discussion inspected; current compositions remain unverified. |
| WHM | Cure, status removal/Cursna, enhancing, precast | Self/other target and spell-specific effects | Original 2025 guide and 15-slot recovery pilot checked; conditional effects and other tiers remain explicit. |
| BLM | Free nuke, burst, accuracy, dark magic, precast | Mana Wall and resource thresholds | Older original guide supplies exact follow-up tables; current replacements and augment requirements remain open. |
| RDM | Engaged/Enspell, WS, enfeebling potency/accuracy, enhancing, precast | Composure, Saboteur, self/other | Source labels October 2026 update; composition-level verification remains required. |
| THF | Engaged, WS, Treasure Hunter, defensive/evasion | SA/TA, tagging | Original guide inspected. Defensive option lists require a separately attributed assembled recommendation. |
| PLD | Tank/engaged, WS, enmity, FC/SIRD, Phalanx, cures | Shield, HP preservation, combat versus town | August 2026 source inspected with concrete idle locators; exact tiers/requirements remain to verify. |
| DRK | Engaged, WS, dark magic, precast | Weapon, Drain/Dread Spikes HP, utility control | Historical guide plus October 2026 original discussion inspected; current idle/combat compositions remain open. |
| BST | Engaged, WS, pet physical/magical/accuracy/durability, Ready precast | Jug/move/pet TP, master versus pet-only | Original guide inspected; published two-ring recovery target is collapsed in current catalog and needs a new exact revision. |
| BRD | Song effects/duration, debuff accuracy, precast, engaged/WS | Instrument capacity, dummy songs, subjob, exact augments | Original guide inspected; image-based song swaps and current compositions need verification. |
| RNG | Ranged TP/accuracy, preshot, physical/magical ranged WS, supported melee | Ranged weapon/ammo, Flurry, Double Shot/aftermath | Retired guide and readable 2023 replacement inspected. Partial preshot grids and augment assumptions retained. |
| SAM | Engaged, physical/hybrid WS, defensive/utility | Weapon, attack/buffs, WS overlays | Older tables and 2026 Leg Sweep discussion inspected; utility accuracy is separate from damage-first WS. |
| NIN | Engaged, physical/hybrid WS, ninjutsu potency/accuracy/burst, Utsusemi | Haste/DW, weapon, time effects | Retired guide plus 2026 modeled WS source inspected; replacement WS evidence does not cover idle/utility. |
| DRG | Engaged, WS, jumps, wyvern support/breath | Weapon, wyvern state, niche event use | Historical guide and 2026 niche-set original inspected; published niche idle is a candidate, not a universal recommendation. |
| SMN | Physical/magical/hybrid/accuracy pacts, Ward/skill, perpetuation/pet durability, precast; supported master WS | Avatar, pet TP, burst, ability state | Original SMN guide inspected. All Jobs SMN page contains master WS only and cannot fill pact/idle coverage. |
| BLU | Engaged, WS, physical/magical blue magic, accuracy/skill/healing, precast | Spell-set traits, weapon/aftermath/DW | Original guide plus modeled source context inspected; modeled traits are excluded from equipment totals. |
| COR | Engaged, ranged, physical/magical WS, rolls, Quick Draw, preshot | Ammo, weapon/aftermath/Triple Shot, roll semantics | Original 2023 source inspected; current compositions and non-additive roll effects need independent verification. |
| PUP | Master/pet/hybrid engaged, pet durability/actions, WS | Head/frame, attachments, food/rolls, Overdrive | Original source distinguishes these roles; exact compositions and recipient applicability remain to verify. |
| DNC | Engaged, WS, Waltz, Steps, utility | Flourishes, self/other healing | Ten-slot defensive pilot checked, including two Moonlight Rings; six omissions and Shell assumption retained. |
| SCH | Free nuke/burst, Helix, healing, enhancing/Regen, accuracy, dark magic, precast; niche melee/WS | Arts/stratagems, weather, Sublimation | Expanded original guide and 15-slot recovery pilot checked. Staff/shield Fast Cast source conflict blocks that composition. |
| GEO | Geomancy/Indi duration, luopan durability, casting potency/accuracy/burst, precast | Luopan, Entrust, weapon effects | Original guide inspected with exact idle/defensive locators; current compositions and master/luopan separation remain required. |
| RUN | Tank/engaged, WS, enmity, FC/SIRD, enhancing/Phalanx | HP preservation, weapon/defense locks, ability effects | Original source inspected; exact current versions, augments and complete composition validation remain T7 work. |

Proposed exceptions to the common idle baseline: **none**. Proposed blanket removal of a job's engaged/accuracy/defensive coverage: **none**. Context-specific N/A records require a reason and review under the accepted model; this table does not create extra runtime switches or certify 22 jobs.

## Initial supported-rule specification proposed for acceptance

“Include” below means sufficiently specified and evidenced for the initial implementation scope **after this review**, with the stated boundaries and future acceptance tests. It does not mean a rule currently runs or has passed tests. Arithmetic fixtures are derived from explicit source values. Direct controlled testing of every possible sum is not an added prerequisite for reporting described contributions; effective mechanics and disputed exceptions retain their specific gates.

| Rule group | Proposed decision | Scope of the accepted claim | Evidence / independent examples |
|---|---|---|---|
| Base flat equipment values | Include the inspected representative fields | Exact item/version and recognized labels: Stikini MND, direct magic accuracy and all-magic-skill family; no skill-to-accuracy conversion or inferred skill enumeration | E-FLAT-01; FLAT-PAIR-01. Two allocated rings give 16 MND, 22 direct magic accuracy, 16 all-magic-skill family points. |
| Described DT/PDT/MDT/BDT contributions | Include distinct raw categories | Signed percentage points per verified recipient; no combined generic total, effective reduction, cap badge or exact incoming-damage value | E-DT-01/02; DT-CONTRIB-01, DT-CATEGORY-01, DT-SCOPE-01. Unsupported MDT augment leaves affected breath interpretation incomplete. |
| Base gear Refresh | Include exact supported base values | Master MP per three-second tick; gear contributions sum after distinct-copy allocation. Spell potency/duration and status overwrite are separate | E-REF-01/03; REF-PAIR-01, REF-COPY-01, REF-KIND-01. Two Stikini +1 copies contribute 2 MP/tick under the defined equipment model. |
| Inyanga Refresh | Include the bounded, sourced loadout exception | Only the six recorded exact +2/accessory IDs; master, once per loadout; `min(4, max(0, n-1))`. Unknown membership retains uncertainty | Original two-piece observation, original six-piece cap report, secondary threshold/membership reference; INY-COUNT/PILOT/NEG/SIX. Four known members contribute 3; six contribute 4. |
| Assiduity +1 Unity Refresh | Include the bounded condition | Item 28135; verified Unity rank 1 gives 2, another verified valid standing gives 1 MP/tick. Unknown gives 1–2 unresolved; no affiliation/invalid input unsupported. Augment rank is independent | Independent reference and authored article; ASSID-RANK-01. Do not extend this exact mapping to other Unity items. |
| DA/TA equipment rates | Include inspected base-label contributions | Separate percentage-point keys; damage-enhancement wording cannot match rate. No combined proc chance or attack/damage model | Epona description and Double Attack revision; MULTI-BASE-01, MULTI-KIND-01. One ring gives DA 3 and TA 3. |
| Fast Cast equipment contribution | Include inspected base-label contributions | Raw percentage points; Quick Magic, Cure casting time, arts and traits excluded. Do not infer a maximum augment or effective cast/recast cap | Fast Cast revision and exact item text; FC-BASE/KIND/AUG. Explicit base 10 and 5 sum to 15. |
| Pet/avatar scoped base values | Include inspected item/recipient boundaries | Nyame master versus Pet accuracy keys; Indomitable master versus Avatar keys. No automatic expansion of generic Pet applicability to every entity type | Corroborated descriptions; PET-SCOPE-01, AVATAR-SCOPE/AUG. Never add pet accuracy to master accuracy. |

This is a representative supported subset, rather than full stat coverage. An item's recognized fields can be complete while other fields on that same item remain unsupported. Published maximum augmentation tables do not establish selected or observed effects. The implementation must fail recognition visibly when a version/text/context falls outside a rule's evidence.

### Explicitly unresolved effects and claims

| Effect / claim | Disposition for the initial delivery | What can remain visible |
|---|---|---|
| Fucho activation denominator and equality boundary | Exclude automatic activation formula; contradictory/incomplete evidence | Original latent text and magnitude; condition unknown. An explicitly hypothetical active/inactive scenario remains labeled as an assumption. |
| Moonshade augment in WHM pilot | Exclude an assumed Refresh augment | Identity and missing augment requirement. An absent base description is unavailable data. |
| Heka/Nefer historical pair | Keep research-only pending exact membership/magnitude verification | Historical original report with authority/date distinctions. |
| Fenrir time boundaries / broad Unity scaling / Hoxne wording | Keep unsupported formulas | Raw text and unresolved conditions/ranges. No both-day-and-night activation or maximum rank guess. |
| Effective DT caps, quantization, bypass items and arbitrary MDT-to-BDT mapping | Exclude effective/cap claims until exact applicable rules are supported | Raw categories and sourced mechanics notes; unresolved effects affect completeness. |
| Effective DA/TA distributions, cast/recast times, damage, hit rate and full character stats | Outside initial equipment-contribution scope | Equipment contributions with their units, recipients and limitations. |
| Unknown augments/rank/path effects | Exclude synthesized magnitudes | Observed raw augments, requirements and provenance; unknown remains unknown. |

The conditional Inyanga/Unity recommendations are an evidence judgment based on the independent sources recorded in the ledger. Additional controlled observations are useful corroboration, but are not treated as an indefinite research requirement for every supported combination. New conflicting retail evidence reopens the affected rule and invalidates its cached results. The disputed Fucho formula remains excluded because its unresolved boundary materially changes activation.

## Concrete rule representation and evaluation contract

Each rule needs a stable rule ID and revision; exact item/version or recognized text applicability; source/evidence locators; resource fingerprint; recipient; stat key; unit; item or loadout scope; operation and rounding; condition inputs; explicit unsupported cases; and independently expected fixture IDs. Evidence status, implementation status and test status are separate fields.

Raw flat values, percentage-point contributions and integer MP/tick values retain exact integer arithmetic in the initial examples. No rounding is applied to those sums. Inyanga performs its integer threshold operation once. Unity chooses exactly one branch when known. These operations do not inherit damage quantization or recast rounding. Any future rule requiring fractional representation must specify that representation before enabling it.

Evaluation order:

1. Validate revision and slot states, identity/eligibility, cross-slot legality and context. Retain omitted, unknown and intentional empty distinctly.
2. In Owned mode allocate distinct observed copies against the character/bag requirements. In Planning retain assumptions explicitly. Failed ownership cannot turn target gear into owned contributions.
3. Interpret verified base and explicitly supported augmentation effects with item, rule, resource and evidence provenance. Unrecognized effects remain attached to their item.
4. Evaluate supported conditions with true/false/unknown states. A false condition contributes zero **under that evaluated condition**; an unknown condition retains unresolved magnitude/range. Neither state proves that all effects on the item were recognized.
5. Evaluate loadout exceptions once against the validated composed selection. Do not sum a full bonus per item. Unknown slots can leave additional qualifying membership unresolved.
6. Sum only compatible stat/unit/recipient keys. Return contribution traces, condition results and completeness per key/recipient. Do not fill an omitted slot from current equipped gear without an explicit composition input.

An unresolved effect with uncertain stat/recipient scope must conservatively affect all plausibly affected completeness results. A precise known subtotal remains inspectable, but cannot be labeled a complete total. A whole-item or whole-set “verified” flag cannot substitute for this per-effect accounting.

## Compatibility contract proposed for acceptance

Accept catalog v2 and a separate personal workspace v1 as the proposed record shapes in the contracts document, subject to implementation validation. Retain stable conceptual IDs, immutable revisions, exact canonical selected slots, source composition classification, distinct-copy allocation and personal designated bags. Legacy targets stay preserved; exact historical associations require evidence. No automatic adoption or dual-writing into legacy guide targets.

All eight named compatibility procedures and five later source/composition cases remain required implementation acceptance fixtures. They cover old-app writes, aliases, allocation, strict versus selector policy, revisions, failed saves, unsupported versions, writer conflicts, option lists, partial sources, provenance, placeholders and cross-slot legality. The two JSON examples are fixture fragments; neither is a production catalog or a migration tool.

The persistence contract publishes authoritative memory only after a successful isolated transaction. Read/load cannot repair or rewrite user records. Unsupported newer versions prevent editing; corrupt files retain recoverable diagnostics. A fixed `.tmp` helper and a pre-write hash check alone do not establish concurrency safety.

## T1 exit and next authorization

| T1 deliverable | Current disposition |
|---|---|
| Actual source/resource/interface calibration | Documented, including two 15-slot pilots, one ten-slot pilot, duplicate mismatch, source options and illegal pairing. No full-job certification. |
| Public evidence ledger | Documented with attributable originals, revision-pinned references, access limits and authority distinctions. |
| Initial rule subset and unsupported effects | Concrete recommendation above; independent expected cases specified; user review pending. |
| Schema and compatibility specification | Concrete proposed records, integration points and failure oracles; user review pending; implementation tests unrun. |
| 22-job required coverage and exceptions | Consolidated above; no blanket idle exception proposed; user review pending. |

User disposition: accepted this packet and authorized T2–T3 core implementation in a new session on 2026-11-03. Earlier pending-review labels describe the packet at preparation time; this disposition supersedes them. T1 is accepted for specification purposes; it does not certify implemented rules or the full catalog. Visual work follows its own gate before UI coding. Full catalog authorship and composition verification remain T7 obligations; excluded numeric effects remain visible throughout. No additional source browsing is required merely to re-prove the accepted bounded proposal.
