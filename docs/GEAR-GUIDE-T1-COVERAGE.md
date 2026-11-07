# T1: source audit and proposed job-priority coverage

RDM successor (2026-11-04): [the RDM report](GEAR-GUIDE-T7-RDM.md) records 38
composition-verified Nexus recommendations across 18 declared caster/combat
priorities. Self/other, Composure/Saboteur, WS main hand and source macro/options
conflicts remain explicit. RDM's historical gaps below are superseded only within
that scope. The partial all-job catalog now has 18 open jobs; no N/A or new
numeric rule was introduced.

BLM successor (2026-11-04): [the BLM report](GEAR-GUIDE-T7-BLM.md) records 22
composition-verified Nexus recommendations across 15 declared caster/staff
priorities. Historical BLM gaps below are superseded only within that scope;
BG access remains unresolved, with readable FFXIAH originals used instead.
The all-job catalog still has 19 open jobs; no N/A or numeric rule was added.

SCH successor (2026-11-03): [the SCH report](GEAR-GUIDE-T7-SCH.md) records 28
composition-verified Nexus recommendations in declared contexts, including
explicit Sublimation and niche engaged priorities. The illegal Fast Cast source
pairing and historical/live healing-tier distinction remain preserved. SCH's
named composition gaps below are superseded only within that report's scope.
The other 20 jobs remain open; no N/A or new numeric rule is introduced.

T7 continuation note (2026-11-03): [WHM's current authoring report](GEAR-GUIDE-T7-WHM.md)
supersedes the WHM access-gap and unchecked-composition status below for its named
sources and declared recommendations only. Browser reads resolved the source
tables and BG access; 23 separate Nexus compositions now cover WHM's ten tracked
priorities. Historical observations and conflicts remain preserved. Other jobs'
historical observations and the accepted T1 evidence boundaries are unchanged.

Date: 2026-11-03. Plan: [approved execution plan](GEAR-GUIDE-IMPLEMENTATION-PLAN.md).
Status: T1 CONSOLIDATED REVIEW PREPARED in the [review packet](GEAR-GUIDE-T1-REVIEW.md), using the continuation checks below. The matrix remains proposed, not accepted runtime mode definitions or verified playable sets. No bundled catalog, app code, inventory or player Lua was changed. T1 acceptance is pending; the packet distinguishes initial rule decisions from T7's remaining composition verification.

## Evidence levels

- **Lead:** supplied research points to a source; neither its date nor equipment claims are automatically accepted.
- **Source inspected:** the underlying page was readable and relevant content was inspected. This is not verification of every linked equipment set or a current-best claim.
- **Equipment/quantity checked:** particular source contents were compared with resource/catalog data; scope is named.
- **Composition verified:** exact slots, quantities, eligibility, augments, conditions and source assumptions all checked. No entire job has reached this level in this pass.

The 22 job handoffs were inventoried earlier in this chat. Private Drive links, personal inventories and Lua mappings are not reproduced in this public report. BG-Wiki references below remain source leads where direct access was blocked. A search result or third-party mirror does not certify the retail page's complete contents.

## Starting catalog and readable sources

Current bundled catalog: 376 distinct set entries across eight jobs, catalog date 2026-10-31. Counts below are per-job associations and must not be summed as distinct entries because some sets have multiple sources/jobs.

| Job | Existing associations | Underlying source inspected | Initial disposition |
|---|---:|---|---|
| BLU | 67 | [The Beast Within, node 25](https://www.ffxiah.com/node/25) | Relevant idle/Refresh and tier/context explanations inspected; complete gear currency still to verify. |
| SMN | 43 | [Summoner gear guide, node 380](https://www.ffxiah.com/node/380) | Page labels an update in January 2026 and supplies multiple idle/perpetuation and pact-related alternatives. Date is the author's claim, not full equipment verification. |
| RUN | 47 | [Destiny's Device, node 397](https://www.ffxiah.com/node/397) | Tank/DD tiers and separate idle/Refresh contexts inspected. Set-specific weapon, attack and augment assumptions need retention. |
| SCH | 2 | [Forum page 103](https://www.ffxiah.com/forum/topic/32145/a-scholars-education-guide/103/) and [thread first page](https://www.ffxiah.com/forum/topic/32145/a-scholars-education-guide/) | Existing collection is a discussion-page sample, not complete guide coverage. First page links node 41; its present relevance needs follow-up. |
| NIN | 26 | [Node 35](https://www.ffxiah.com/node/35) | Page reports gear updates in 2020 and a 2021 notice ending constructive updates. Treat as older reference, not a verified-current basis. Linked [spreadsheet repository](https://github.com/NextGames2000/Spreadsheets) is another research lead, not imported logic. |
| COR | 79 | [Luck of the Draw, node 326](https://www.ffxiah.com/node/326) | Page labels its last update September 2023. Useful tier/role structure; current equipment needs rechecking. Roll-potency discussion is evidence that not all equipment bonuses should be summed. |
| BST | 48 | [The Beast Within, node 227](https://www.ffxiah.com/node/227) | Distinct defensive, recovery, melee and pet contexts inspected. Confirmed duplicate-count discrepancy described below. |
| RDM | 64 | [Anything You Can Do, node 425](https://www.ffxiah.com/node/425) | Page labels an October 24, 2026 update. Relevant idle/Refresh and casting distinctions inspected; newer date does not independently prove each set. |

Site header clocks, crawl dates and forum thread creation dates are not guide-update dates. Do not convert those values into per-set verification evidence.

## Confirmed findings

### F1: published duplicate ring is collapsed in the current catalog

The [BST Idle Refresh equipment page, set 264975](https://www.ffxiah.com/item-sets/264975) explicitly lists Stikini Ring +1 in both ring slots. Its source table contains eight occupied slots. The bundled catalog has seven item rows and only one Stikini Ring +1 row, whose slot is `left_ring/right_ring`.

This is a concrete source-to-catalog quantity/slot mismatch. The two possible slots describe eligibility, not two recorded targets. Preserve legacy saved references, but rebuild this revision from exact source slots with two required copies; do not label the current row a verified two-ring target. No repair was applied in this pass. The source's listed recovery total was not independently recalculated.

### F2: a catalog source is explicitly retired

[NIN node 35](https://www.ffxiah.com/node/35) is not a current source merely because its page remains accessible. Retain useful validated older alternatives with the proper currency label; source new current entries independently. Do not silently delete old targets or treat every old item as invalid.

### F3: source coverage differs from recommendation coverage

[BLU node 25](https://www.ffxiah.com/node/25) distinguishes defensive and Refresh idle purposes. [BST node 227](https://www.ffxiah.com/node/227) also includes a Refresh idle context despite the job's usual non-MP main-job role. This supports context-aware priorities, not a blanket ban on Refresh for non-native casters. Whether Refresh is useful depends on the declared MP-using setup, not simply a job label.

### F4: direct BG-Wiki access is incomplete

Direct opens of the All Jobs hub, its BLU and SMN pages, Community RUN/SCH pages and Bravery set page returned HTTP 403 in the research tool. These pages are not marked fully read. Do not copy a private-server mirror into retail recommendations as a substitute.

Later browser checks on 2026-11-03 successfully read the RNG replacement, Community Scholar Guide, Damage Taken and Refresh (Status). Their scoped findings below supersede the earlier access gap for those pages only. Research-tool 403 is not evidence that a page is unavailable in the browser; other BG leads have not thereby been inspected.

The original All Jobs author has a [public simulator repository](https://github.com/IzaKastra/wsdist_beta) and [dated discussion of guide updates](https://www.ffxiah.com/forum/topic/57175/all-jobs-damage-simulator-and-gear-sets/19/). The latter confirms that composition depends on declared enemy/buff/TP contexts. It does not independently verify current tables or authorize importing the simulator as Nexus's stat engine.

## Proposed all-job priority matrix

Every row requires DT Idle. Every row also requires Refresh Idle when a declared MP-using job/subjob/equipment context makes it useful; otherwise record a specific N/A reason. Do not turn automatic action/ability/buff overlays into manual controls solely to fill this matrix.

`Engaged` means evaluate Balanced/DT/Accuracy priorities for supported weapon/role contexts, with separate equipment versions under comparable assumptions. If the role is niche, label it; do not pretend it is the job's normal purpose. Entries below are coverage candidates drawn from the research and job responsibilities, not a determination that every proposed runtime toggle must exist.

| Job | Existing catalog? | Relevant groups beyond required idle | Special conditions/overlays to distinguish | Source status |
|---|---|---|---|---|
| WAR | New | Engaged; physical WS; defensive/utility roles | Weapon/Fencer contexts, attack assumptions | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Warrior_Guide); verification pending |
| MNK | New | Engaged; physical WS; defensive/Subtle Blow contexts | Impetus, Footwork, hand-to-hand restrictions | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Monk_Guide); [discussion lead](https://www.ffxiah.com/forum/topic/36705/iipunch-monk-guide/379/) located, sets unverified |
| WHM | New | Cure; status removal/Cursna; enhancing; precast | Spell/ability-specific enhancements versus mode choice | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_White_Mage_Guide); [v3 discussion lead](https://www.ffxiah.com/forum/topic/55005/on-healing-hands-a-comprehensive-whm-guide-v3/12/) located |
| BLM | New | Free nuke; burst; magic accuracy; precast/dark magic | Mana Wall and resource-threshold equipment | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Black_Mage_Guide); [discussion lead](https://www.ffxiah.com/forum/topic/49789/the-black-sacrament-a-guide-to-black-mage/51/) located |
| RDM | Existing | Engaged/Enspell; WS; enfeebling potency/accuracy; enhancing; precast | Self/other target, Composure/Saboteur | Underlying source inspected; compositions pending |
| THF | New | Engaged; WS; Treasure Hunter; defensive/evasion | SA/TA and tagging overlays | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Thief_Guide); verification pending |
| PLD | New | Tank/engaged; enmity; FC/SIRD; Phalanx; WS | Shield context, HP preservation, spell/ability overlays | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Paladin_Guide); verification pending |
| DRK | New | Engaged; WS; dark magic; precast | Drain/Dread Spikes, weapon/HP context | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Dark_Knight_Guide); verification pending |
| BST | Existing | Engaged; WS; pet physical/magical/accuracy/durability; Ready precast | Pet-only/master roles, jug/move/TP context | Underlying source and one quantity mismatch inspected; broader sets pending |
| BRD | New | Song effect/duration; debuff accuracy; precast; engaged/WS | Instrument/song capacity, dummy song and buff overlays | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Bard_Guide); verification pending |
| RNG | New | Ranged TP/accuracy; preshot; physical/magical ranged WS; supported melee | Ammo safety, ranged weapon, Double Shot/aftermath | [Finans guide lead](https://www.bg-wiki.com/ffxi/Finans_Gearset_Guides/Ranger); verification pending |
| SAM | New | Engaged; physical/hybrid WS; defensive contexts | Weapon, attack/buff context, WS ability overlays | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Samurai_Guide); verification pending |
| NIN | Existing | Engaged; physical/hybrid WS; ninjutsu potency/accuracy/burst; Utsusemi | Haste/DW context and time-dependent effects | Existing source retired; replacement/current sets pending |
| DRG | New | Engaged; WS; jumps; wyvern-support/breath gear | Jump/wyvern state, weapon context | [Finans guide lead](https://www.bg-wiki.com/ffxi/Finans_Gearset_Guides/Dragoon); verification pending |
| SMN | Existing | Pact physical/magical/hybrid/accuracy; Ward/skill; perpetuation/pet durability; precast | Avatar, pet TP, burst and ability contexts | Underlying source inspected; compositions pending |
| BLU | Existing | Engaged; WS; physical/magical blue magic; accuracy/skill/healing; precast | Weapon/aftermath/DW and spell/buff overlays | Underlying source and Refresh table inspected; current compositions pending |
| COR | Existing | Engaged; ranged; physical/magical WS; rolls; Quick Draw; preshot | Ammo, weapon/aftermath/Triple Shot, non-additive roll effects | Underlying source inspected, dated 2023; current sets pending |
| PUP | New | Master/pet/hybrid engaged roles; pet durability; pet actions; WS | Frame/head, attachments and Overdrive context | [String Theory lead](https://www.bg-wiki.com/ffxi/String_Theory); verification pending |
| DNC | New | Engaged; WS; Waltz; Steps; utility | Flourish, self/other healing and ability overlays | [Community guide lead](https://www.bg-wiki.com/ffxi/Community_Dancer_Guide); verification pending |
| SCH | Existing, narrow | Free nuke/burst; Helix; healing; enhancing/Regen; accuracy; precast | Arts/stratagem, weather, Sublimation | Discussion samples inspected; guide expansion/current sets pending |
| GEO | New | Geomancy/Indi duration; pet durability; casting potency/accuracy/burst; precast | Luopan, Entrust and weapon effects | [Compendium lead](https://www.bg-wiki.com/ffxi/Compendium_of_Colure:_The_Art_of_Geomancy); verification pending |
| RUN | Existing | Tank/engaged; enmity; FC/SIRD; enhancing/Phalanx; WS | HP preservation, weapon/defense locks and ability overlays | Underlying source inspected; complete compositions pending |

Full per-job required/not-applicable dispositions still need the user's consolidated review after deeper source verification. The broad baseline is already approved; this table does not reopen that decision or count an unverified handoff as a finished job.

## Next evidence work

Resolve BG access or locate independently attributable retail originals/author backups; inspect precise tables and recent relevant author discussion; record per-set dates and assumptions; compare exact slots and item-resource eligibility; verify all augment/rank/path/quantity requirements. Preserve found older references and personal identities while preparing new revisions. T7 performs the complete equipment refresh; this first pass does not certify 376 existing sets or all 22 jobs.

## Continuation source checks: 2026-11-03

Public-source summaries only; no private handoff captures or player mappings. These checks refine the matrix above without accepting it or certifying a job.

| Job | Newly inspected original / locator | Supported observation and limit |
|---|---|---|
| SCH | [Node 41](https://www.ffxiah.com/node/41), Economics, World Religions, Physics and footer | Footer identifies Tooheyv, an internal September 4, 2014 version and last modification May 2, 2015. Contains distinct idle, defensive, precast, healing, enhancing, enfeebling and offensive contexts. Some entries are explicitly lists of options, not complete sets. Retain as historical coverage evidence; it does not fill the current-SCH gap. |
| WHM | [Wotasu node 408](https://www.ffxiah.com/node/408), Idle Refresh, Idle PDT/MEVA, Paralyna/Cursna and footer; linked by the [v3 thread opening](https://www.ffxiah.com/forum/topic/55005/on-healing-hands-a-comprehensive-whm-guide-v3/) | Footer modified July 5, 2025. Refresh sets 373997/373998/373999, defensive contexts 366767/366768/372567, and four Doom-removal versions are concrete verification candidates. Source differentiates healing, Curaga, status removal, enhancing and enfeebling. Its theoretical Doom-removal success claim depends on master level and earring; do not turn this into a guaranteed calculator result. Individual compositions remain unchecked. |
| PUP | [String Theory thread opening](https://www.ffxiah.com/forum/topic/52194/string-theory-a-puppetmasters-guide-new/), Fabiano opening and second post | Opening labels last update April 26, 2019 and links BG plus node 426. Supports locating an attributable original, not current composition verification. Direct node 426 returned a tool accessibility error (not a proven HTTP 403). The BG guide has not been read in this continuation. |
| PLD | [Divine Protector thread opening](https://www.ffxiah.com/forum/topic/58104/the-divine-protector-pld-guide-2025/) and [page 2](https://jp.ffxiah.com/forum/topic/58104/the-divine-protector-pld-guide-2025/2/) | Opening links node 482; direct English node returned an accessibility error. Page 2 contains first-person enmity tests and discussion of their resolution limits. Its repeated guide text is not independent corroboration of the node. Keep mechanics testing separate from guide tables; no PLD recommendation certified. |

Direct BG Damage Taken and Refresh (Status) requests also returned HTTP 403. FFXIclopedia Refresh (Status Effect) returned a robots denial; its Damage Taken request was inaccessible. These are specific access outcomes, not proof that every page/domain is unavailable. Search results from private-server wikis were excluded from retail mechanics evidence.

The next composition candidates are WHM's separate idle groups and a current SCH replacement source. The consolidated matrix still requires broader research and one user review; no missing-job N/A has been invented from an access failure.

## WHM exact-slot pilot and SCH follow-up

### WHM 373999: source occupancy and local eligibility checked

[WHM Idle Refresh v3, 373999](https://www.ffxiah.com/item-sets/373999), inspected 2026-11-03. Its macro and set blocks agree on 15 occupied slots:

| Slot | Item | Local item ID |
|---|---|---:|
| main | Daybreak | 22040 |
| sub | Genmei Shield | 27645 |
| ammo | Homiliary | 22268 |
| head | Inyanga Tiara +2 | 25577 |
| neck | Loricate Torque +1 | 26002 |
| ear1 | Moonshade Earring | 11697 |
| ear2 | Etiolation Earring | 28478 |
| body | Ebers Bliaut +3 | 23489 |
| hands | Inyan. Dastanas +2 | 25831 |
| ring1 | Inyanga Ring | 26207 |
| ring2 | Defending Ring | 13566 |
| back | Alaunus's Cape | 26248 |
| waist | Fucho-no-Obi | 28452 |
| legs | Assid. Pants +1 | 28135 |
| feet | Inyan. Crackows +2 | 25949 |

No repeated item IDs. Range is omitted, not declared empty. No augments are supplied in this table. This is a live page observation, not an immutable author revision.

Read-only comparison with the recorded resource snapshot resolved all 15 exact English names uniquely; all 15 have the WHM job bit and the stated slot bit. `jobs.lua` confirms WHM ID 3. No ownership, full cross-slot legality or numeric completeness is established by those mask checks. Item and description SHA-256 values still match the stat document's snapshot.

Augment, latent, ranking and loadout-bonus questions are specified in the [stat evidence continuation](GEAR-GUIDE-T1-STAT-RULES.md#whm-pilot-conditional-effects). This pilot is equipment/quantity checked, not composition verified. No catalog entry was added.

Other requested WHM tables 373997, 373998, 366767, 366768 and 372567 returned tool accessibility errors. Retrying the first three with trailing slashes did not resolve them. Their guide links establish leads only; no exact item lists were inferred from neighboring tiers. Further retries of URL spelling are not the next research step.

### SCH: 2026 discussion provides context, not a complete replacement guide

[Page 103](https://www.ffxiah.com/forum/topic/32145/a-scholars-education-guide/103/) has Chimerawizard's April 4, 2026 reply linking healing sets 378846 and 338349; the author explicitly qualifies their review depth. Both direct set pages are readable and contain 15 occupied slots. They are exactly the two current SCH catalog IDs, confirmed by a read-only catalog inspection. This does not expand SCH coverage.

[378846](https://www.ffxiah.com/item-sets/378846) is a weather-oriented healing candidate using Chatoyant Staff, Khonsu, Twilight Cape and Hachirin-no-Obi. [338349](https://www.ffxiah.com/item-sets/338349) provides a defensive healing alternative including Arbatel Gown +3, Murky Ring, Defending Ring and Loricate Torque +1. Neither page's live contents can be assumed byte-identical to its April forum reference. Augment paths, conditions and independently calculated totals remain open. Published automatic stat tables were not used as expected-result oracles.

[Page 104](https://www.ffxiah.com/forum/topic/32145/a-scholars-education-guide/104/) includes July/September 2026 operational discussion, not a comprehensive current equipment table. A new post date is not a refreshed gear-guide revision. Do not fill absent idle, enhancing, Regen, Helix or burst coverage from the two healing sets.

## Original-source expansion for all fourteen missing catalog jobs

Inspected 2026-11-03. This section supersedes the initial matrix's source-status cells where it supplies newer evidence; proposed priority groups remain unchanged. Specific guide sections/footer metadata were inspected, not every linked table. All entries remain below whole-job composition verification. Dates are the page's own modification/update fields, not independently established equipment currency.

| Job | Attributable retail source and date evidence | Concrete coverage candidates and qualification |
|---|---|---|
| WAR | [Ejiin's Parthenon original thread](https://www.ffxiah.com/forum/topic/35200/the-parthenon-a-warriors-kyklos/), Gear Sets posts | Chango TP 381945/285667/285786, sword/shield TP 349896/322217/322218 and Savage Blade 322221/322222/322223 provide separate weapon/accuracy contexts; defensive candidate 236360. Guide mixes older progression text with newer equipment headings. Original 2012 posting date does not date every edit; no reliable whole-guide update date established. Preserve context-specific cape/roll notes. |
| MNK | [Minjo node 173](https://www.ffxiah.com/node/173), footer modified April 21, 2015; [miscellaneous node 176](https://www.ffxiah.com/node/176), sections dated March 1, 2015 | PDT 333679, MDT 333680, physical/magical hybrid 324490/324491 and Chakra 333681 support distinct historical objectives. Node 173 warns that some entries involve proposed/DAT-mined changes. Retain as older references with current replacement research required. Nodes 175/178 were inaccessible; the linked weapons node 174 was readable but does not itself supply the missing current gear tables. |
| WHM | [Wotasu node 408](https://www.ffxiah.com/node/408), footer July 5, 2025 | Original sections and one exact-slot pilot recorded above. Refresh, defensive idle, healing, status removal and enhancing candidates exist; latent/augment/set-rule questions remain. Other idle versions could not be fetched, so no tier contents were inferred. |
| BLM | [Black Sacrament node 297](https://www.ffxiah.com/node/297), footer modified March 1, 2021 | Mana Wall 347384/349691, PDT 348770/340500/340501/340502/340503, MDT 340505/340506/340507 and idle 348771/340509 give exact follow-up locators. Source explicitly requires Refresh augments on Merlinic idle pieces. Older guide, not a current-BiS certificate. Mana Wall is a declared action/buff context, not proof of another universal manual mode. |
| THF | [Sevrina node 393](https://www.ffxiah.com/node/393), footer September 12, 2020; opening attributed by the [new-guide thread](https://www.ffxiah.com/forum/topic/54552/a-rogues-guide-to-the-precious-a-new-thief-guide/) | TP 371523/371524/371527, separate SA/TA candidates 371491/371526, and unstacked WS versions. Defensive 375302/375304 are explicitly equipment-option lists, not actual sets to copy. Complete DT Idle still requires a verified composition or attributed Nexus recommendation. Earlier direct-node error was temporary: following the original thread link returned readable content. |
| PLD | [Tetsouou node 482](https://www.ffxiah.com/node/482), footer August 28, 2026 | Readable through its original thread link after earlier direct-open failure. Targeted idle sections distinguish low/mid/top defensive contexts, MDT, XP and safe-town Refresh 397548; low/mid idle locators 397651/397653. Separate enmity, FC/SIRD, Phalanx and self/other cures are supported coverage candidates. Published totals, caps and swap-priority Lua are not certified or imported. Safe-town recovery is not interchangeable with combat idle. |
| DRK | [Quetzacoatl node 52](https://www.ffxiah.com/node/52), footer May 18, 2017 | Historical starter/scythe/greatsword progression, TP accuracy, WS, dark magic/Drain/Aspir, Dread Spikes and Fast Cast contexts inspected. Named paths/augments and HP assumptions matter. AF/relic/empyrean collection tables are equipment references, not a single simultaneous action set. Find current replacements before labeling active recommendations current. |
| BRD | [Briko node 355](https://www.ffxiah.com/node/355), footer May 10, 2022; internal edits label April 1, 2022 | TP 363865/370496/363866, WS, song/debuff/lullaby, healing and enhancing contexts. Subjob and exact Linos/cape/Nyame path requirements differ by purpose; one generic Linos is insufficient evidence. Some song swaps are images rather than parsed slot tables. Treat as older source, and independently verify song capacity/duration requirements. |
| RNG | [Kunami node 365](https://www.ffxiah.com/node/365), footer/internal update March 16, 2023 | Author explicitly says out of date and unlikely to be updated again. Preshot 364537/364539/364540 separates Flurry contexts; midshot 364775/364777/364778/364776 and Double Shot 364809/364816 are separate action contexts. Author's replacement link [Shoot - Aww Made You Look](https://www.bg-wiki.com/ffxi/Shoot_-_Aww_Made_You_Look) returned 403. Preserve retired-source label; no copied cap claim becomes a verified rule. |
| SAM | [Reiden node 125](https://www.ffxiah.com/node/125), footer September 24, 2020; some WS sections date to 2016/2019 | Separate TP/WS accuracy versions, bow reference, Regen 319759, PDT 365416, MDT 365417 and enmity 365419. Exact section dates differ from footer. Preserve as older evidence; contemporary discussion is not a blanket refresh of these tables. Regen is not a substitute for required context-dependent Refresh research. |
| DRG | [Bleusummers node 182](https://www.ffxiah.com/node/182), footer September 28, 2014; original [Sigurd thread](https://www.ffxiah.com/forum/topic/44396/sigurds-descendants-the-art-of-dragon-slaying/) links it | Ryunohige versus Gungnir/non-RME accuracy contexts; Jump/High Jump/Spirit Jump/Soul Jump 327951/327952/327948/327950; returning-player versions. Historical source explicitly distinguishes /SAM implications and wyvern-related actions. Not a current polearm/prime recommendation. Newer DRG sources in the initial matrix remain leads. |
| PUP | [Falsetto/Aerix node 426](https://www.ffxiah.com/node/426), footer November 26, 2022 | Readable via original String Theory thread link. Separates master TP, dual master/pet TP, pet-only TP, pet WS, tanking, casting, Overdrive and utility. Food, roll, head/frame, aftermath and augment assumptions are explicit. Pet idle/precast 352991/378439/378364/368252/378366 supplies candidates, not proof that the master gains those pet stats. Source timing advice does not authorize automation changes. |
| DNC | [Katriina/SimonSes node 373](https://www.ffxiah.com/node/373), footer October 17, 2022; internal Last Update June 12, 2020 | Ability, melee, WS, idle 348201/367871/367872/367874 and utility 367866/367868/367869/367870 groups inspected. Preserve both date fields. Defensive exact-slot pilot below shows quantity/context requirements; other sets and augment/cape choices still need verification. |
| GEO | [Brixy node 112](https://www.ffxiah.com/node/112), footer September 10, 2022; rewrite note March 19, 2019 | [Original thread opening](https://www.ffxiah.com/forum/topic/41358/bubble-trouble-a-geomancer-guide/) warns the node is partly broken and editing locked. Core idle 371134/371132, older idle 316321/316539, geomancy 346417/341832 and defensive 316322/319868/333672 are concrete leads. Master recovery, luopan effects and casting must stay separate. Direct Compendium of Colure returned 403. No player modifier is inferred from a pet line. |

The eight existing-job rows plus these fourteen now have attributable original-page context inspected. That is source discovery progress across 22 jobs, not verified equipment coverage across 22 jobs. Current-source replacement, exact compositions, requirements and consolidated user review remain open. No N/A is assigned merely because a guide is old, incomplete or unavailable.

### Additional findings affecting the contract

- **F5: source tables may be equipment lists.** THF node 393 expressly classifies its defensive collections as options, not playable sets. Source classification must precede slot extraction; the website's ItemSet identifier is not sufficient. A future assembled loadout needs separate Nexus authorship and exact selected requirements.
- **F6: another source is explicitly retired.** RNG node 365 names its own replacement and says it will probably receive no more updates. Keep the old source and its useful context, while researching the replacement; do not relabel the old tables current because their URLs still resolve.
- **F7: transient tool errors are not permanent source dispositions.** THF/PUP/PLD node requests later succeeded through original thread links. Their successful checks above supersede the earlier inaccessible outcome, without claiming uninterrupted availability or full-page verification. BG responses reported as 403 remain distinct from generic accessibility errors.

### DNC 367871: duplicate quantity and partial loadout checked

[DT Shell V, set 367871](https://www.ffxiah.com/item-sets/367871) lists ten occupied slots. Macro and set blocks agree. Local identity/eligibility checks on 2026-11-03:

| Slot | Item | ID |
|---|---|---:|
| ammo | Yamarang | 22280 |
| head | Malignance Chapeau | 23732 |
| neck | Warder's Charm +1 | 27505 |
| body | Malignance Tabard | 23733 |
| hands | Malignance Gloves | 23734 |
| ring1 | Moonlight Ring | 26190 |
| ring2 | Moonlight Ring | 26190 |
| waist | Engraved Belt | 28414 |
| legs | Malignance Tights | 23735 |
| feet | Malignance Boots | 23736 |

All ten requirements pass the DNC job bit (ID 19) and corresponding slot bit in the recorded resource snapshot. This requires **two** Moonlight Rings. Main/sub/range/ear1/ear2/back are omitted, not intentional empty. Source's Shell V label is an assumption, not a measured current buff or verified cap. The open slots can materially change defense and HP, so this partial candidate cannot establish complete-loadout totals or safe runtime behavior. Source supplies no exact augment/rank values here; do not infer a fully augmented neck. No current-best claim or ownership check was made.

### Next bounded verification queue

1. Source replacements: RNG's named replacement, current MNK/SAM/DRG/DRK compositions and complete SCH contexts. Seek attributable retail originals or author-preserved versions; do not substitute private-server mirrors.
2. Exact compositions: choose defensive and recovery candidates with readable slot tables, retain every duplicate and omitted slot, then verify item IDs, legal context and augments. THF defensive option lists cannot fulfill this step directly.
3. Numeric rules: finish the narrow additive/Refresh evidence gate before claiming totals for these sources. Modern source totals are comparison leads, not independent expected-value fixtures.
4. Consolidated review: present required versus included versus unsupported/N/A-by-context dispositions together after the remaining material evidence is assembled. This queue does not authorize implementation or additional runtime modes.

### Contemporary discussion cross-checks

[MNK page 379](https://www.ffxiah.com/forum/topic/36705/iipunch-monk-guide/379/), January 31, 2026 discussion, distinguishes attack/PDL assumptions, Footwork/kick contexts and event-specific Subtle Blow equipment. Posters disagree about maintaining separate toggles; one quoted statement is explicitly identified as sarcasm. Their individual control preferences do not override the approved context-aware coverage baseline. This is evidence to retain assumptions, not a verified new composition or permission to remove DT/Accuracy priorities.

[SAM page 179](https://www.ffxiah.com/forum/topic/41903/bushido-the-way-of-the-samurai-a-guide-v-20/179/), September 10, 2026, contains a specific Leg Sweep equipment example after discussion of accuracy and magic accuracy for the additional effect. Preserve this utility context separately from damage-first WS recommendations. Another proposed experiment on the page was explicitly abandoned by its author in July; a test proposal is not a test result. No numerical claim from either conversation was certified.

Direct contemporary DRG page 121 returned a timeout, and the probed DRK page returned a generic accessibility error. These requests did not provide replacement composition evidence. Current-job completeness remains open despite the newer discussion leads.

### Browser-access continuation: RNG and SCH

Checked 2026-11-03 through the ordinary Chrome browser, without login or a security challenge. Revision links identify the content inspected; a page edit date is not a date of verification for every table.

| Source | Revision / date | Scoped finding |
|---|---|---|
| [RNG replacement: Shoot - Aww Made You Look](https://www.bg-wiki.com/index.php?title=Shoot_-_Aww_Made_You_Look&oldid=689561) | 689561; footer October 4, 2023, 13:07 | Readable replacement for retired node 365. Standard and Gastraphetes preshot each distinguish Flurry contexts; ranged midshot, Barrage and separate physical/magical WS tables are populated. Unity gear/JSE necks assume maximum augments. Some melee/miscellaneous headings have no composition: headings alone cannot satisfy coverage. Replacement is not established as current for 2026. |
| [Community Scholar Guide](https://www.bg-wiki.com/index.php?title=Community_Scholar_Guide&oldid=781558) | 781558; footer October 30, 2026, 22:34 | Actual tables cover Refresh idle, Sublimation, FC, healing/Cursna/Regen, enhancing/enfeebling, free nukes/bursts/Helix, dark magic, defense and niche melee/utility. Latest Updates entries still describe 2022/2023 work and acknowledge source copying/formatting-only edits. The recent footer does not certify equipment currency. DT and recovery compositions are now concrete research inputs, beyond the two bundled discussion samples. |

RNG standard no-Flurry preshot has nine selected slots: head Taeon Chapeau, neck Scout's Gorget +2, body Amini Caban +3, hands Carmine Fin. Ga. +1, ring1 Crepuscular Ring, back Belenus's Cape, waist Yemaya Belt, legs Orion Braccae +3 and feet Meg. Jam. +2. Head/back require Snapshot 10; hands specify path D. The other seven grid cells are category placeholders, not deliberate empty slots. In particular, a weapon-context heading does not silently select a ranged weapon. Snapshot caps and buff amounts remain source claims until covered by the stat-rule gate.

### SCH Refresh Idle Example: exact-slot pilot

The Scholar revision above contains this 15-slot example. Source grid cells, rather than the adjacent list's order, establish slots. Read-only checks against the recorded resource snapshot passed SCH job bit 20 and the corresponding slot bit for all 15 requirements (14 distinct item IDs):

| Slot | Selected item | ID |
|---|---|---:|
| main | Mpaca's Staff | 22100 |
| sub | Khonsu | 22218 |
| ammo | Homiliary | 22268 |
| head | Befouled Crown | 26790 |
| neck | Sibyl Scarf | 25416 |
| ear1 | Etiolation Earring | 28478 |
| ear2 | Ethereal Earring | 15965 |
| body | Arbatel Gown +2 | 23171 |
| hands | Volte Gloves | 23718 |
| ring1 | Stikini Ring +1 | 26184 |
| ring2 | Stikini Ring +1 | 26184 |
| back | Moonbeam Cape | 26268 |
| waist | Embla Sash | 26354 |
| legs | Assid. Pants +1 | 28135 |
| feet | Volte Gaiters | 23726 |

Range is omitted/category-placeholder, not intentional empty. Two physical Stikini +1 copies are required. Source notes condition the neck on Windurst citizenship and identify this as a Refresh-focused example, with defensive substitutions described separately. Citizenship and Unity standing are distinct conditions. No augmentation magnitude, owned-copy availability, complete recovery total or current-best status is inferred.

The neighboring More Ideal Refresh Idle table changes gear and includes explicit DT -5 cape and DT -9 legs requirements. Its note mentions a belt substitution after Sublimation charging; retain that as source context requiring clarification rather than inventing an unconditional overlay. The defensive DT table states Agwu's legs need augments and suggests Nyame otherwise. Each alternative needs its own exact requirements and evidence.

**F8: individually eligible items can form an invalid loadout.** The same revision's Alternative 80% Fast Cast grid explicitly pairs Hvergelmir (Level 119 III) with Chanter's Shield. [Hvergelmir's item page](https://www.bg-wiki.com/ffxi/Hvergelmir_(Level_119_III)) identifies Staff skill; local item 22064 confirms skill 12/main-only, while shield 27635 has shield_size 2/sub eligibility. Both allow SCH individually. The staff/shield pairing fails the cross-slot equipment constraint, even though independent job/slot checks pass. Preserve the source discrepancy and block playable-target certification; do not silently substitute a grip or attribute a repaired composition to the guide author.

### Contemporary DRG and DRK originals located

[Uncommon DRG Sets 2026](https://www.ffxiah.com/forum/topic/58853/uncommon-drg-sets-2026/1/), Smobo's February 26, 2026 opening, explicitly describes personal niche compositions with imperfect augments. Concrete locators include hybrid TP 382735, DT/MEVA TP 402150, wyvern-related idle 402151 and Arke idle 402152. Event/weapon/pet assumptions and later disagreements matter; these are newer attributable candidates, not universal replacements or verified full compositions.

[DRK guide page 223](https://www.ffxiah.com/forum/topic/35174/dont-fear-the-reaper-a-dark-knight-guide/223/), October 11, 2026 replies by Buukki and Vyre, distinguishes damage/weapon approaches from dark-magic HP needs, utility control and specialist party support. It supports retaining separate contexts during current-source research; it supplies no newly verified idle composition. This readable actual page supersedes the earlier failed probe without implying that the failed guessed page was read.

Next research scope is exact requirements and current-source comparison for these candidates, plus representative physical/casting/pet effect rules. T1 does not require completing T7's entire catalog first. The consolidated job-exception review and supported-rule evidence gate remain open; no additional runtime modes are authorized here.

### All Jobs source framework now inspected

The browser also read [Kastra's All Jobs hub, revision 772437](https://www.bg-wiki.com/index.php?title=All_Jobs_Gear_Sets&oldid=772437), footer July 13, 2026. It explicitly provides modeled combat recommendations and redirects utility coverage to job guides. Mid/high-buff scenarios use a declared enemy and different buffs; neither is a universal ranking. Stated exclusions include Nyame R30 and paths A/C, Sortie +2 earrings, stage-5 primes and Voracious rings. Stated included assumptions include other Odyssey/Limbus R30, Nyame R25 and Hoxne mastery rank 7. Preserve exclusions and assumptions with any imported composition. Modeled damage captions are not independently verified expected values for the Nexus equipment analyzer.

| Inspected child revision | Scoped finding / missing coverage |
|---|---|
| [Ninja 772448](https://www.bg-wiki.com/index.php?title=All_Jobs_Gear_Sets/Ninja&oldid=772448), July 13, 2026 | Readable newer WS candidates include mid/high-buff tables with modern gear. Hitaki is explicitly excluded despite its situational value. This supplements the retired node; it does not replace idle, ninjutsu, Utsusemi or utility research. Generic cape labels such as DEX/DA are not exact augment magnitudes. |
| [Summoner 772456](https://www.bg-wiki.com/index.php?title=All_Jobs_Gear_Sets/Summoner&oldid=772456), July 13, 2026 | The entire displayed composition list contains four **master WS** groups: Garland of Bliss, Shattersoul, Retribution and Gate of Tartarus. Some notes date individual updates May 3, 2026. This page supplies no Blood Pact, Ward or perpetuation composition; the Summoner job label cannot stand in for pet-role coverage. Buff assumptions include avatar favors and other pet-granted buffs affecting the master. |
| [Blue Mage 772441](https://www.bg-wiki.com/index.php?title=All_Jobs_Gear_Sets/Blue_Mage&oldid=772441), July 13, 2026 | Intro enables Thibron, disables certain alternative swords unless specified, and derives traits/stats from a particular Zahak Reborn spell list. Preserve that declared spell setup; modeled contributions from spells/traits are not equipment effects to import into Nexus totals. Only intro/context and initial table content inspected; no all-table verification claim. |

These checks supersede F4's earlier access gap for this hub and these three children. The other nineteen children were not read by following the hub's links. The public source code remains a provenance lead only: no code was run, copied or used as the numeric oracle. A single source family cannot fill every required priority even when it has a page for all 22 jobs.
