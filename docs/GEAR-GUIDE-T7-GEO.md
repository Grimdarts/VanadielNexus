# T7 GEO candidate batch — 2026-11-04

GEO has **17 explicitly Nexus-authored, composition-verified base-item
recommendations across its eight tracked priorities**. This is bounded
non-Idris caster/club-and-shield coverage, not every gear tier or gameplay niche.
Production v1 and installed Windower/player Lua remain unchanged.

## Compositions and deliberate distinctions

| Tracked priority | Candidate keys | Bounded behavior |
|---|---|---|
| DT Idle | dt-idle | Master protection; no pet-defense or effective-cap claim |
| Refresh Idle | refresh-idle, refresh-jse | Fixed base recovery versus JSE defense/recovery tradeoff; Dunna retained and ammo intentionally empty |
| Geomancy / Indi duration | geomancy-skill, indi-duration, entrust, geocolure | Skill versus self-duration, other-recipient Entrust, and Geo creation kept separate |
| Luopan durability | luopan-durability, luopan-recovery | Explicit non-Idris pet core with separate master protection or MP-recovery body choice |
| Casting potency | free-nuke, free-nuke-jse | Base Agwu versus JSE checkpoint; no asserted universal ordering |
| Magic accuracy | magic-accuracy, enfeebling-mnd, enfeebling-int | Elemental accuracy and accessible MND/INT enfeebling contexts kept separate |
| Magic burst | magic-burst | Explicit Ea +1 access and compatible burst window; no burst total or cap |
| Precast | fast-cast, fast-cast-defense | Casting-speed versus threatened-defense checkpoint; separate correct midcast still required |

All keys have prefix nexus:geo:. Each recommendation declares 16 canonical
slots, with one deliberate range/ammo empty state. Other source omissions remain
omissions. Identical paired Stikini +1 rings need two distinct physical copies.
Every selected piece uses its base item only; requirements do not silently count
Odyssey ranks, Unity maximums, random augments, cape augments or relic merits.

The casting/Indi/Geo/pet targets use base Solstice, not a guessed Path D.
All recommendations use reviewed one-handed main plus shield. No Idris stage,
Dual Wield trait, offhand potency/aftermath or source's weapon pairing is inherited.
Ea +1 requires GEO Su3 / 500 Job Points. Learned spells and usable Entrust are
explicit action/access prerequisites, not supplied by equipment eligibility.

## Evidence and source currency

Primary guide: [Bubble Trouble, node 112](https://www.ffxiah.com/node/112).
The node labels a 2019 rewrite, 2022 footer and unfinished core/old sections.
Reader crawl timestamps do not prove every linked set current. Source tables
can contain later items than the guide footer; they are separate observations.
New recommendation currency stays **unknown**; composition verification does not
certify current BiS, skill thresholds, caps, duration, landing rate or damage.

Thirteen original-site table representations were inspected, preserving ordered
Equipment Macros, explicit source comments, omissions and conflicts:

- Recovery: [371134](https://www.ffxiah.com/item-sets/371134),
  [371132](https://www.ffxiah.com/item-sets/371132).
- Geomancy: [346417](https://www.ffxiah.com/item-sets/346417),
  [341832](https://www.ffxiah.com/item-sets/341832).
- Master/pet defense: [316322](https://www.ffxiah.com/item-sets/316322),
  [319868](https://www.ffxiah.com/item-sets/319868),
  [333672](https://www.ffxiah.com/item-sets/333672).
- Casting: [316497](https://www.ffxiah.com/item-sets/316497),
  [316509](https://www.ffxiah.com/item-sets/316509),
  [354155](https://www.ffxiah.com/item-sets/354155),
  [343476](https://www.ffxiah.com/item-sets/343476).
- Enfeebling: [316507](https://www.ffxiah.com/item-sets/316507),
  [319965](https://www.ffxiah.com/item-sets/319965).

343476 is an additional source observation, not a separately completed Dark
magic priority. The historical guide's cap/Conserve MP/damage claims are retained
as source context without applying them to Nexus substitutions.

Public base cards were checked for all 16 newly added resource IDs. Their name,
slot/GEO eligibility and described effects were compared with actual installed
public resources. Prior 327 resource records/descriptions remain unchanged.
No new hand classification was needed; all 18 existing hand entries are unchanged.

Retrieval used web-reader parsed original-site representations with provider
crawl metadata, including some older cached material; **not raw live HTML**.
Failed reads are preserved in the capture packet. Prior direct HTTPS requests
returned 403; ordinary browser access is disabled in Work settings. BG's
Compendium returned 403 and was not successfully read. No access failure became
N/A, no private source was used, and no security setting was changed.

## Source conflicts and Vesper reconciliation

- 333672 is a ten-slot source with Sucellus main / Idris sub and explicit
  Telchine/cape comment text. It is not this full shield-based Nexus loadout.
  No main-hand Idris, Dual Wield or pet cap is transferred. The new reader
  snapshot has its own row order; Vesper's earlier literal extraction is retained
  with its original order, not overwritten.
- 341832's Idris/Solstice context and Vanya/Merlinic requirements stay source
  observations. 346417's title/commentary does not establish its advertised
  Conserve MP or JP result for the later table selections or this assembly.
- Homiliary is GEO-ineligible and is absent from all new recommendations.
  Fi Follet Cape +1 is not credited with unconditional base FC. Lifestream's
  unaugmented base is selected without a guessed FC magnitude or cape augment.
- All original Vesper proposal files and reviewed source excerpts remain untouched
  as historical drafts. They were not promoted into catalog verification.
  Vesper's accepted literal extraction is credited only for extraction fidelity.
  Joint-pilot source access and token savings remain unproven; no Vesper task
  is currently released.

## Artifacts and counts

- docs/catalog/gear-guide-t7-geo-definitions.json: 17 explicit definitions,
  rationale, complete slot states and action/recipient/access contexts.
- docs/catalog/gear-guide-t7-geo-source-captures.json: ten actual reader responses,
  byte hashes, source URLs, crawl limits and failed attempts. Parsed representations
  are labeled as such; these hashes do not convert them into raw HTML captures.
- docs/catalog/gear-guide-t7-geo-observations.json: 13 hashed ordered observations.
- docs/catalog/gear-guide-t7-geo-item-evidence.json: 16 new exact-ID public base
  card observations with independent resource-description hashes.
- docs/catalog/gear-guide-t7-geo-readback.json: pre-edit backups/hashes, prior
  record retention, resource/production identity and protected-file readback.

Candidate: **136 sets / 136 revisions / 218 sources**. **128 verified Nexus
compositions**: WHM 23, SCH 28, BLM 22, RDM 38, GEO 17. **Eight original unresolved
revisions are preserved unchanged.** There are 2,022 selected slots and 128
intentional empty slots. Coverage: **225 rows / 67 included / 158 gaps across
17 remaining jobs / zero N/A**. All non-GEO coverage rows remain unchanged.

All previous 119 sets, 119 revisions and 188 sources retain identical canonical
content. Existing source-observation amendments and authoring batches survive.
Resource packet: 343 records, all independently matched to actual resources;
four upstream file hashes and fingerprint remain unchanged:
0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78.
Production v1 SHA-256 remains:
54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85.

## Validation and remaining limits

Focused suite: **114 passed / 0 failed / 0 skipped in 4.33 s**. Actual-resource
whole-candidate preparation and independent history/resource/production readback
passed. Full isolated native suite: **892 passed / 0 failed / 0 skipped in
114.00 s (1:54)**. No app/core/UI/test/tool source changed afterward.
The new tests guard the actual GEO-ineligible ammo regression, incorrect base-FC
assumptions, recipient distinctions, pet/master scope, physical ring copies,
source ordering/hashes, immutable history and bounded interpretation.
Earlier tests update only candidate-wide counts and remaining-job exclusions;
their original job-specific checks remain intact.

Test persistence uses fictional data, redirected auto-discovery and disabled
inventory seeding via the existing real-file native launcher. No app/core/UI/
numeric-rule/tool implementation changed. No executable was built or replaced.
No commit/push/install/release/migration/game command/Lua activation occurred.

Unclaimed: every equipment tier, Idris variants/aftermath, dual-wield/melee/WS,
all healing/enhancing/dark/JA niches, optimal cape/augment configurations, skill
and potency thresholds, FC/MB/DT/Refresh caps, perpetual luopan sustain, live
weapon/TP/MP transitions, ownership/bags and gameplay readiness. T8/T9 and the
existing human/frozen/live acceptance gates remain separate. Continue T7 on the
remaining jobs; the partial catalog is not a production replacement.
