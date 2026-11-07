# T7 WHM verified recommendation batch

Successor status: [SCH's report](GEAR-GUIDE-T7-SCH.md) and the
[current handoff](GEAR-GUIDE-T7-HANDOFF.md) record the next batch. WHM's 23
compositions and evidence remain unchanged; candidate-wide counts below describe
the WHM milestone and are historical after SCH was appended.

Checked 2026-11-03. **WHM's ten tracked required priorities now have verified
Nexus recommendations for the explicitly declared contexts below.** This is one
job's authoring milestone in a still-partial 22-job project. It is not a claim to
cover every published tier, every weapon/subjob, every spell variation, all game
mechanics or an installed/live-tested application.

The candidate remains outside production. The bundled v1 catalog, player Lua,
personal targets, inventory and installed executable remain unchanged.

## What verified means here

Each new recommendation has 16 canonical slot states: 15 exact selected items
and one **intentional empty range**. The empty is a documented Nexus choice,
not a reinterpretation of an author's blank grid. IDs/names, WHM job and slot
eligibility, Rare duplicates, quantity, main/sub types, required rank/path/augment
prerequisites, purpose/context and authorship were checked. Every simultaneous
ring slot still needs its own physical copy.

These are **Nexus assemblies**, with rationale and cited source inspirations.
They are not attributed as exact author-published compositions. They may fill
omitted slots, replace an ambiguous augment-dependent item with a fixed base
piece, or choose a specific prerequisite checkpoint. Those decisions are written
into each immutable revision. Unlisted augments are optional for the described
minimum, not asserted absent from a real inventory or silently counted at maximum.

Composition verification does not enable new numeric rules. Character skill,
merits, job points, master level, buffs, incoming damage, hit rate, haste/DT/cure
caps, spell durations and damage remain outside this claim. Unsupported effects
remain visible and uncalculated per result. No player ownership, bag placement,
working-set selection, gear equip command or runtime mode is inferred.

## Source access and currency

The research tool could not fetch several FFXIAH pages and returned HTTP 403 for
BG pages. The normal browser successfully read them. The browser outcome
supersedes those access gaps for the named pages only; it does not prove that all
other unreadable pages are available or that every source claim is correct.

The principal current context is the [Community White Mage Guide, revision
781508](https://www.bg-wiki.com/index.php?title=Community_White_Mage_Guide&oldid=781508),
whose footer reports October 30, 2026. Its Idle Sets, Fast Cast, Cure/Curaga,
Enhancing, melee, cape and spell-context sections were read. The date is a source
revision date, not proof that each embedded table was refreshed on that date.
Wotasu's [On Healing Hands v3](https://www.ffxiah.com/node/408), footer July 5,
2025, supplies independently inspected exact table/context leads. New Nexus
recommendations are labeled current as recommendations checked on the date above,
not as current-BiS or simulated upgrades. Older exact source observations retain
their original unresolved/currency metadata.

BG's real Permanent links use `/index.php?title=...&oldid=...`. The existing
catalog validator now admits that exact read-only shape for BG only, requiring
one nonblank title and one positive numeric revision. Other source-host checks
remain. Source actions retain the exact query/fragment rather than replacing it
with the live page. No second catalog loader or discovery service was introduced.

## Required priorities and explicit contexts

| Required priority | Concrete recommendations | Scope and tradeoff |
|---|---|---|
| DT Idle | 1 | Five base Nyame pieces, Defending Ring, Moonbeam, Daybreak/Genmei and explicit protective accessories. No Nyame augment or effective cap required for the described base defense. |
| Refresh Idle | 1 | Backline MP recovery with Daybreak, Homiliary, Ebers +3 body, Inyanga membership and a Stikini +1. Excludes Moonshade, Fucho and Unity legs so the recovery objective does not depend on their unresolved prerequisites/conditions. Trade physical defense for recovery; choose DT when threatened. |
| Cure | 2 | Separate single-target Solace and party Curaga selections. Weather-independent minimums. Ebers +1 pants retained; Curaga replaces the Solace-focused body/cape. No cure amount or 50% badge. |
| Status removal / Cursna | 4 | Ordinary single-target removal, exact Yagrush level-75 utility alternative, Divine Caress-active midcast, and separate Cursna with Vanya B15 and two Ephedra Rings. No guaranteed Ebers proc, generic alliance-wide Erase, immunity count or Doom success percentage. |
| Enhancing | 6 | Duration, elemental Barspells, Boost skill, Regen, Stoneskin and Aquaveil remain distinct spell contexts. Required Telchine duration augments are explicit. No 500-skill, +25-stat, 236-resistance, Regen tick or interruption-count certification. |
| Precast | 1 | General Fast Cast with Vanya D15, a required FC+10 cape and fixed-base alternatives. Regal +1 Unity contribution remains conditional. This is not an effective cast/recast/Quick Magic cap claim. |
| Engaged Balanced | 2 | Niche Maxentius/Genmei single-wield and separately declared WHM/NIN 99/49 Maxentius/Daybreak dual-wield. Exact DA or DW cape minimums; Bunzi R30 QA not assumed. |
| Engaged DT | 2 | Protective Nyame/Defending/Moonbeam choices in both weapon contexts. Dual wield gives up Genmei's shield defense; no promise to retain it or cap delay. |
| Engaged Accuracy | 2 | Exact accuracy-swap choices completed by Nexus, Gazu +1 rank 15 and two Chirich +1 copies in each weapon context. Unknown Unity standing is not set to maximum. Gazu Attack-17 and loss of the defensive ring remain tradeoffs. |
| Physical WS | 2 | Black Halo with Maxentius main, each of five Nyame pieces at B15, explicit MND20/WSD10 cape minimum and fixed accessories. Separate single/dual-wield contexts. No assumed Moonshade TP augment, unspecified neck rank, R30 bonuses or damage comparison. |

Total: **23 full recommendations**. The four melee obligations were made explicit
from the accepted common engaged baseline once both original WHM guides showed
that supported niche role. They were not silently excluded because WHM's primary
role is healing. No N/A or blanket idle exception was added.

The declared dual-wield legality context is a level-99 WHM/NIN with level-49
subjob and usable Dual Wield. This is a manual scenario prerequisite, not a
discovery of Jason's current job, trait or buff state. Exact delay tuning under
other subjobs/haste and specialized offhands remain different, unclaimed contexts.
Daybreak is a fixed support-oriented offhand, not an assertion that it beats
Kraken Club or another specialized weapon. Automatic swaps and TP preservation
remain later Lua work; existing weapon and defensive locks retain priority.

## Exact prerequisite evidence

| Requirement | Checked original | Boundary |
|---|---|---|
| Vanya Hood B15 / D15 | [Hood revision 600769](https://www.bg-wiki.com/index.php?title=Vanya_Hood&oldid=600769) | B15 healing skill and D15 Fast Cast are distinct paths. A B15 owned copy cannot satisfy D15. |
| Vanya Clogs B15 | [Clogs revision 600798](https://www.bg-wiki.com/index.php?title=Vanya_Clogs&oldid=600798) | Explicit B15 target for the Cursna skill objective. Base-only Cure version does not silently inherit an augmentation. |
| Fanatic base versus possible augments | [Fanatic revision 729192](https://www.bg-wiki.com/index.php?title=Fanatic_Gloves&oldid=729192) | Base Cursna +15 is distinct from potential Healing Skill +10 / FC+7. Neither potential augment is inferred. |
| Alaunus minimum augments | [Cape revision 568473](https://www.bg-wiki.com/index.php?title=Alaunus%27s_Cape&oldid=568473) | Base Solace/Cursna properties are separate from the deliberately selected FC10, DEX20/DA10, DEX20/DW10 or MND20/WSD10 prerequisites. Optional dye/resin is not counted. |
| Telchine duration +10 on exact pieces | [Alluvion armor revision 715143, Telchine section](https://www.bg-wiki.com/index.php?title=Category:Alluvion_Skirmish_Armor&oldid=715143) | Duskdim duration +1 to +10 is documented. +10 is chosen as a target requirement; no observed-copy or effective-duration inference. |
| Gazu +1 rank 15 | [Gazu revision 749889](https://www.bg-wiki.com/index.php?title=Gazu_Bracelets_%2B1&oldid=749889) | Rank-15 augmentation is independent of the Unity standing bonus; required rank cannot be satisfied by another copy's augments. |
| Nyame B15 | [Head 665696](https://www.bg-wiki.com/index.php?title=Nyame_Helm&oldid=665696), [body 665695](https://www.bg-wiki.com/index.php?title=Nyame_Mail&oldid=665695), [hands 665694](https://www.bg-wiki.com/index.php?title=Nyame_Gauntlets&oldid=665694), [legs 671845](https://www.bg-wiki.com/index.php?title=Nyame_Flanchard&oldid=671845), [feet 665692](https://www.bg-wiki.com/index.php?title=Nyame_Sollerets&oldid=665692) | Each Path B table was expanded and its rank-15 row read. No rank-16+ DA or rank-21+ accuracy bonus inferred. No numeric rule for Nyame augments was added. |
| Maxentius | [Revision 766327](https://www.bg-wiki.com/index.php?title=Maxentius&oldid=766327) | Exact ID 22031; Club, WHM eligibility and main-hand Black Halo context. No damage model. |
| Beneficus / Bolelabunga / Ammurapi / Yagrush 75 | [Beneficus 627412](https://www.bg-wiki.com/index.php?title=Beneficus&oldid=627412), [Bolelabunga 592101](https://www.bg-wiki.com/index.php?title=Bolelabunga&oldid=592101), [Ammurapi 706776](https://www.bg-wiki.com/index.php?title=Ammurapi_Shield&oldid=706776), [Yagrush 419933](https://www.bg-wiki.com/index.php?title=Yagrush_(Level_75)&oldid=419933) | Exact-ID hand evidence and relevant utility descriptions. Other Yagrush stages are not silently equivalent. |

[Moonbeam](https://www.ffxiah.com/item/26268/moonbeam-cape) supplies a fixed base
defensive cape alternative. [Gendewitha +1](https://www.ffxiah.com/item/28021/gende-gages-1)
supplies fixed FC+7. [Meili](https://www.ffxiah.com/item/26098/meili-earring) and
[Kishar](https://www.ffxiah.com/item/26188/kishar-ring) confirm exact ID and base
properties. Their public item records were checked as supporting evidence for the
Nexus choices; they do not turn these assemblies into author-published sets.

Windower's installed `addons/libs/extdata.lua` was inspected **as text only** to
check the labels used by strict augment matching. Its hash and scoped label notes
are in the public resource-evidence packet. No library was executed and no player
augmentation observations were read. Availability, target requirement and observed
magnitude remain three different claims.

## Published source tables remain distinct from Nexus choices

The browser inspected 13 WHM support tables and the eight-slot accuracy-swap
reference. Exact macro occupancy and item hyperlinks are retained in the public
observation files. The remaining original tables are still only leads until read.

- [366767 defensive](https://www.ffxiah.com/item-sets/366767), [366768 MEVA](https://www.ffxiah.com/item-sets/366768), [372567 hybrid](https://www.ffxiah.com/item-sets/372567): sparse selections, not a full set including every placeholder.
- [373997](https://www.ffxiah.com/item-sets/373997) and [373998](https://www.ffxiah.com/item-sets/373998): Refresh v1/v2 exact selections now readable. No inferred Moonshade augmentation or Fucho/Unity activation.
- [373971 Fast Cast](https://www.ffxiah.com/item-sets/373971): selected shield with omitted main. Nexus supplies a reviewed main under its own authorship.
- [373983 Cursna](https://www.ffxiah.com/item-sets/373983): two Ephedra slots remain separate; head/feet paths come from the guide column and item evidence.
- [373991 status removal](https://www.ffxiah.com/item-sets/373991): macros select both Vanya Hood and Ebers Cap +3; generated Lua collapses the first. Both observations are retained. Nexus explicitly chooses Ebers rather than treating last-write-wins as exact authorship.
- [373993 Caress](https://www.ffxiah.com/item-sets/373993), [373995 duration](https://www.ffxiah.com/item-sets/373995), [369805 Regen](https://www.ffxiah.com/item-sets/369805), [373996 Barspells](https://www.ffxiah.com/item-sets/373996), [372276 Cure](https://www.ffxiah.com/item-sets/372276): exact sparse cores/overlays retain their spell context; omitted slots are filled only in separate Nexus revisions.
- [374390 accuracy swaps](https://www.ffxiah.com/item-sets/374390): eight swaps, with main and other slots omitted. It is not imported as a simultaneous complete source composition.

The old 373999 WHM source revision remains unchanged and unresolved. The new
recommendations do not silently promote, replace or associate it with existing
personal records.

## Artifacts and continuation

- `docs/catalog/gear-guide-t7-candidate.json`: **31 sets/revisions**, comprising
  23 verified Nexus WHM compositions and the original 8 unresolved source records.
- `docs/catalog/gear-guide-t7-whm-observations.json`: 13 public support-table
  observations and the first 15 explicit recommendation definitions.
- `docs/catalog/gear-guide-t7-whm-melee-evidence.json`: accuracy-swap observation,
  eight melee definitions and scoped rank/evidence references.
- `docs/catalog/gear-guide-t7-resource-evidence.json`: expanded detached public
  resource records/descriptions and decoder-label evidence; no player data.
- Two authoring-batch records preserve canonical hashes of the previous 8 and
  previous 23 sets/revisions/sources. New batches were appended through the
  existing whole-candidate preparation tool; earlier revisions were not edited.

The coverage ledger now has **205 records: 10 included WHM priorities and 195
gaps for the other 21 jobs**, with no N/A dispositions. The row count changed
because WHM's supported niche role was made explicit, not because a priority was
deleted or a gap relabeled as completion. Required idle remains explicit for all
22 jobs. Source-only research records do not count as another finished job.

WHM's declared-priority recommendation authoring is covered. Source-parity for
every guide tier, specialized other weapons/subjobs, new numeric rules, character
ownership, full-app/frozen testing and live acceptance remain separate. Next T7
work should apply this standard to the next job rather than duplicate speculative
tiers or restart the accepted design review.
