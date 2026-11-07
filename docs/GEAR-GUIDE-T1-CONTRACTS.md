# T1 catalog and personal-workspace contracts

Date: 2026-11-03. Status: proposed implementation specification; no schema migration or app code performed.

Companions: [coverage](GEAR-GUIDE-T1-COVERAGE.md), [effect evidence](GEAR-GUIDE-T1-STAT-RULES.md), [approved plan](GEAR-GUIDE-IMPLEMENTATION-PLAN.md).

The [consolidated T1 review packet](GEAR-GUIDE-T1-REVIEW.md) brings these proposed contracts, the initial rule subset and all-job coverage together for one user review. Specification acceptance and implementation authorization remain distinct.

## Catalog v2 proposal

Keep one bundled `gear_guides.json`. Preserve previous data while preparing an independently validated candidate. `schema_version: 2` is a proposed contract, not a version already accepted by the existing loader. Existing `load_catalog()` currently returns decoded JSON without validating it; future code must add validation before consuming v2 data.

| Record | Required identity and meaning |
|---|---|
| Source | Stable source ID, source kind, public URL, author/title where available, access date and exact table/context locator. Access date is not last update or verification date. |
| Conceptual set | Stable set ID; job applicability, existing purpose, context and priority/mode label. Does not encode a claim that one version is always better. |
| Immutable revision | Set ID + revision ID; label, equipment-version label/order within comparable context, origin, currency and verification evidence; source references; explicit slots. Any equipment/requirement correction creates a new revision. |
| Slot requirement | Canonical slot, exact item ID/name and required augments/path/rank when proven; explicit intentional-empty when applicable. One occupied slot requires one item; repeated item IDs across different slots are valid. |
| Coverage disposition | Job + required priority, included set references or a specific N/A reason, supporting context/evidence and review status. Missing evidence stays a gap. |

Canonical slot names should match the existing reader/grid convention after inspecting its normalizer. Reject two supplied aliases that collapse into the same slot; never silently overwrite. Item eligibility masks describe possible slots and must never substitute for the source's selected slot. In particular, `left_ring/right_ring` in legacy rows is ambiguous and cannot be mechanically converted into two exact requirements.

Origin (source adaptation or Nexus recommendation), currency (current/older/unknown), equipment version (budget/progression/etc.) and verification are independent fields. A current page date does not verify every set. Historical immutable revisions remain available to saved references. Source actions resolve the selected revision; one reference opens directly and several offer a contextual chooser.

Candidate validation checks schema/version, ID uniqueness, reference integrity, source metadata/URL kinds, job/slot eligibility, slot collisions, item requirement types, required coverage and evidence completeness. Candidate failure preserves the prior prepared catalog. Runtime catalog corruption yields a Guide-page error while leaving the rest of the app and personal files usable.

## Personal workspace v1 proposal

Use a separate file under the existing user-data-root policy; proposed basename `gear_workspace.json`, `schema_version: 1`. Confirm naming against the existing path policy during implementation. It contains new targets, draft sets and personal exact-copy bindings, not curated catalog data or an item/stat cache.

| Record | Required identity and meaning |
|---|---|
| Target | Stable target ID, character identity, conceptual set/revision reference and immutable target snapshot. Personal requirement overrides remain explicitly separate. |
| Slot binding | Target/draft + canonical slot, character, designated bag ID and item requirements; optional observed-copy evidence from a particular snapshot. |
| Draft | Stable draft ID/revision, owned or planning mode, slot states, observed versus assumed requirements, source references and scenario. |
| Legacy association | Original legacy identity/snapshot and proven association evidence, or unresolved/conflicting status. It is not authoritative dual-writing. |

Bag ID is personal placement. It is never universal guide metadata. A snapshot position is observation evidence, not permanent physical identity; bag positions can change. Re-evaluate allocation against a fresh snapshot without silently changing the designated bag. A moved item may still be owned while not ready under its saved placement. Different augments remain distinct requirements.

Allocate simultaneously across all occupied slots, consuming each observed physical copy at most once. Left/right rings and ears need separate slot requirements even when their item IDs and augment text match. Deterministic selection cannot prove which of indistinguishable copies the player intended beyond the available observation/bag evidence. Report ambiguity rather than fabricate identity.

Read/view/load cannot rewrite user files or adopt catalog revisions. Explicit adoption/import presents the revision/slot/requirement/bag changes, saves the selected change atomically, and publishes in-memory state only after write success. Failed writes preserve both memory and disk. Unknown newer workspace versions fail closed for editing and retain the file. Corrupt primary/backup cases produce recoverable diagnostics; do not silently save an empty replacement.

Existing `jsonfile.write_json()` provides temp/backup/replace primitives; transaction/publication and schema/error policy remain implementation work. Do not claim that helper alone establishes concurrent-write safety or migration correctness.

## Compatibility and failure fixtures required before implementation acceptance

Fixtures are fictional and have not been implemented or run in this research step.

| Case | Expected invariant |
|---|---|
| Legacy target with one ring eligibility row | Retain original data and unresolved exact slots; do not infer a second ring |
| Two identical rings, designated bags 1 and 2 | Distinct allocation; one missing/moved copy does not satisfy both slots |
| Same item with different observed augments | Match all requirements on one copy; do not combine augments across copies |
| Current catalog revision changes | Saved target continues using its original immutable snapshot until explicit adoption |
| Old app edits/recovery of legacy file | Separate workspace bytes remain unchanged; new app later reopens its records |
| New workspace version / corrupt primary and backup | Preserve files and prevent destructive editing; other app areas remain usable |
| Save permission/replace failure | No changed authoritative in-memory target/draft and no false success indicator |
| Omitted / unknown / intentional-empty slot | Preserve all three meanings; label partial-set contributions truthfully |
| Planning item or assumed augment export | Fully commented Lua only; no active equipment assignments |
| Owned export with duplicate bags | LuaJIT51 syntax validation and restricted-reader/selector round trip preserve slot/bag requirements |

Migration of real records remains separately gated. No personal data was converted, no catalog schema changed and no compatibility fixture has passed merely because this document describes it.

## Interface calibration: continuation at HEAD 5657f20

Read-only code inspection on 2026-11-03 establishes the following integration points. These are current-source observations, not new behavior or tested feature claims.

| Interface | Observed contract | Specification consequence |
|---|---|---|
| `core/gearswap_reader.py:SLOT_ORDER`, `ui/equip_grid.py:EquipGrid.SLOT_ORDER` | `main, sub, range, ammo, head, neck, ear1, ear2, body, hands, ring1, ring2, back, waist, legs, feet` | Use these 16 canonical keys in v2/v1. UI order differs from resource slot-bit order; never use an array index as the bit number. |
| `resources/gs_sandbox.lua:SLOTS/slot_of` | Case-insensitive aliases include ranged, left/right_ear, learring/rearring, lear/rear, left/right_ring and lring/rring | At the import boundary, normalize recognized aliases and reject collisions before constructing a slot map. Serialized new records use canonical keys only. Slash-separated eligibility text is not a recognized occupied-slot alias. |
| `core/item_res.py:fits/wearable` | Paired ear/ring bits are accepted by either paired slot. Wearable checks job/level, while race and superior level remain separate notes. | Slot eligibility is not source occupancy. A pass here alone cannot prove full legality or active-output readiness. |
| `core/item_res.py:bag_key/bags` | Snapshot Wardrobe 1 normalizes to wardrobe; resource/GearSwap name is Wardrobe. Name lookup returns normalized key -> resource name. | Resolve personal numeric bag ID through a verified bag-resource snapshot. Retain observed spelling separately. Never reinterpret personal bag 1 as Wardrobe 1. Missing ID mapping remains unresolved. |
| `core/paths.py:data_dir` | `VN_DATA_DIR` override, otherwise portable app `data`, otherwise APPDATA/VanadielNexus. Function performs directory/probe writes. | Use the selected app data root for the proposed workspace, never cwd or resource path. Research must inspect code rather than call this function against real data. Test through a temporary override. No new data-root discovery/migration policy. |
| `core/database.py:Database`, `core/settings.py:Settings` | Legacy basenames are `ffxi_database.json` and `settings.json`. Database loading can migrate/recover and write. Settings publishes `_values` before `write_json`. | Do not instantiate against real data for research. New workspace view/load must not reuse legacy auto-repair behavior or mutate live state before save success. |
| `core/jsonfile.py:read_json/write_json` | Reader returns primary/backup parsed value or None without full diagnostic provenance; writer uses fixed `.tmp`, copies primary to `.bak`, then `os.replace`. | New workspace needs explicit absent/invalid/newer-version/recovered outcomes. Helper does not provide writer isolation, in-memory transactionality or a general rollback of backup/temp side effects. |
| `core/gear_guides.py:track_set`, `ui/pages/guides.py` augment override callback | Legacy identity includes job/set/item ID, without slot/revision; callback updates legacy guideTarget by that identity. | Keep new authoritative slot/revision records isolated. A duplicate legacy item ID cannot map itself into both paired slots. Existing picker state is navigation, not an authoritative new target. |

### Concrete fictional record shapes for review

Field names below are proposed, not an implemented schema. A slot list is deliberate: validators can report duplicate canonical slots before creating a lookup dictionary. Reject duplicate JSON object keys during decoding as well; ordinary JSON object decoding can otherwise discard the original collision before validation.

```json
{
  "schema_version": 2,
  "sources": [
    {"id": "source-fixture", "kind": "fixture", "url": null}
  ],
  "sets": [
    {"id": "fixture-refresh", "jobs": ["RDM"], "purpose": "Idle", "target": "Refresh Idle"}
  ],
  "revisions": [
    {
      "id": "fixture-refresh-r1", "set_id": "fixture-refresh",
      "source_ids": ["source-fixture"], "verification": "fixture-only",
      "slots": [
        {"slot": "ring1", "state": "selected", "item_id": 26184, "requirements": {}},
        {"slot": "ring2", "state": "selected", "item_id": 26184, "requirements": {}}
      ]
    }
  ]
}
```

This is a compatibility fixture fragment, not a distributable catalog candidate: source kind fixture/null URL and fixture-only evidence are permitted only in isolated fixtures. Production validation must reject these. A full production revision also supplies the required origin/currency/version/context metadata above. Each selected slot is one copy; no per-slot quantity 2. Missing slots are omitted, not empty. Intentional empty uses `state: empty` without item requirements; unresolved uses `state: unknown` with diagnostic provenance, never a fake item ID 0. Unresolved research records are not silently promoted to active verified catalog entries.

```json
{
  "schema_version": 1,
  "targets": [
    {
      "id": "target-fixture", "character_key": "fixture-character-a",
      "set_id": "fixture-refresh", "revision_id": "fixture-refresh-r1",
      "snapshot": {"revision_id": "fixture-refresh-r1", "slots": [
        {"slot": "ring1", "state": "selected", "item_id": 26184, "requirements": {}},
        {"slot": "ring2", "state": "selected", "item_id": 26184, "requirements": {}}
      ]},
      "overrides": [],
      "bindings": [
        {"slot": "ring1", "bag_id": 8},
        {"slot": "ring2", "bag_id": 10}
      ]
    }
  ],
  "drafts": [], "legacy_associations": []
}
```

IDs/character are fictional; bag IDs 8/10 require the fixture's explicit resource mapping to Wardrobe/Wardrobe 2. A character key must resolve to one existing character identity; this example does not authorize inventing a global character-ID migration. Production target snapshots must preserve the complete chosen revision requirements/context/provenance, not only the abbreviated slot fragment shown. Resource and inventory observations carry separate source/snapshot identities. An override never mutates the immutable snapshot.

### Compatibility fixture procedure and failure oracles

Implementation fixtures must operate in a newly created temporary data root, importing only code/resources. Never copy live player files. Existing `tests/core/test_backup_recovery.py` and `tests/ui/test_settings_recovery.py` show temporary recovery patterns; their existence is not evidence for the new workspace behavior.

1. **COMPAT-OLD-01:** Seed fictional database/settings plus the workspace above and nontrivial whitespace/UTF-8 bytes. Record exact workspace bytes and SHA-256. Using the pinned HEAD 5657f20 legacy Database/Settings code, save a fictional legacy wishlist change and a navigation setting. Compare workspace bytes, not only parsed equality. Reopen with the future workspace reader; both original slot bindings/snapshot survive. Repeat legacy database recovery from a good backup and from rejected primary/backup with defaults. Verify workspace primary, backup and any evidence files remain unchanged. This only proves compatibility with the pinned version; test other shipped versions separately when identified.
2. **COMPAT-ALIAS-01:** Inputs `left_ring` plus `RING1` collide and reject the complete candidate; `left_ring` plus `right_ring` normalize to ring1/ring2 and remain two requirements. `left_ring/right_ring` rejects as ambiguous. Reader aliases identify one set, not extra loadouts to sum.
3. **COMPAT-COPY-01:** Supply character A/item 26184 copies in fixture bags 8 and 10. Both designated slots can be allocated once. Remove bag-10 copy: ring2 not ready; never reuse bag-8 copy. Move it to bag 11: ownership may remain true, saved bag binding remains 10 and readiness fails. Character B's bag-10 ring cannot satisfy A. Same-bag identical copies can prove quantity without proving permanent copy identity.
4. **COMPAT-POLICY-01:** One fixture copy has required augment A and another required augment B; a requirement A+B remains unmet. A Rare-item selector shortcut or dropped synthetic Rank text must not satisfy a strict target's unmet rank/path. Preserve selector's existing behavior in its own policy and raw rank in observations.
5. **COMPAT-REV-01:** Add revision r2, then change catalog default ordering. Saved r1 bytes/requirements remain unchanged. Missing catalog r1 resolves to the saved snapshot with an unavailable-source diagnostic, not r2. Deliberately change content under r1 identity: candidate rejects immutable-history conflict. Explicit adoption prepares the full delta, saves once, then publishes the new state.
6. **COMPAT-WRITE-01:** Inject serialization, temp-write, backup-copy and replace failures independently. Before successful replacement, authoritative primary bytes and published in-memory target/draft stay at their prior state. A temp file may require cleanup and backup may have changed; record these secondary outcomes rather than falsely claiming all files were untouched. Subsequent load must not treat leftover `.tmp` as committed. After successful replacement, publish committed memory and report success; verify readback. Crash/restart loads a valid committed primary or offers explicit recovery without an automatic empty save.
7. **COMPAT-VERSION-01:** Newer-version primary plus older valid backup must show unsupported-version status and prohibit editing; do not silently fall back and overwrite newer data. Malformed primary plus supported backup offers inspectable recovery without writing on view. Both corrupt preserve both files and diagnostics. Missing both is a distinct empty state, with no file created until explicit save.
8. **COMPAT-WRITER-01:** Two app instances load the same generation; first saves, then second attempts a stale save. Reject the second with a recoverable conflict and retain its unsaved proposal separately from committed state. A hash check alone has a check/replace race; implementation must establish writer exclusion across check/write/replace (or refuse concurrent editing) and use an isolated temp per transaction. Choose the minimal mechanism during T3, test interleaving, and do not claim the existing fixed-temp helper solves it.

All eight procedures remain unimplemented/unrun. The proposed record shapes and failure oracles make the next review concrete; they do not satisfy T1 acceptance, authorize T2/T3 coding or permit running any conversion against real data.

## Source composition classification refinement

Original-source expansion found a concrete input distinction: [THF node 393](https://www.ffxiah.com/node/393) explicitly says defensive ItemSets 375302/375304 are equipment options, not actual sets to copy. [DNC 367871](https://www.ffxiah.com/item-sets/367871) is a ten-slot defensive candidate with two explicit Moonlight Rings and six omitted slots. Both use the same external ItemSet URL form; URL kind cannot establish loadout semantics.

Proposed required revision provenance field `composition_kind` distinguishes `loadout`, `partial_loadout` and `equipment_options`. This describes the source's intent, independently of evidence status, origin, purpose or currency. An options list stays a research/reference record and cannot be automatically materialized as a simultaneous equipment target, analyzer loadout or active export. A Nexus-authored selection from it is a new attributed composition with its own evidence/revision, not a silently repaired copy of the list. No new UI control is specified here.

`partial_loadout` preserves source omissions and assumptions explicitly; it does not gain invented empty slots to become `loadout`. Even a 16-slot source still needs eligibility, augment and cross-slot checks. A full armor-family reference remains a reference collection unless a playable composition is established; do not confuse ownership of a collection with a configured action set.

Additional fictional fixtures, specified but not implemented:

| ID | Input | Required outcome |
|---|---|---|
| COMPAT-LIST-01 | External ItemSet-shaped fixture labeled equipment_options, with multiple alternative pieces for one slot | Preserve reference and item options. Reject automatic target/analyzer/export materialization; no first/last-row winner, slot inference or partial write. |
| COMPAT-PARTIAL-01 | Ten selected slots patterned on the DNC pilot, including two ring1/ring2 copies of one non-Rare item | Allocate two distinct units, preserve six omitted states and Shell assumption; report partial equipment contributions. Never assert a full capped loadout. |
| COMPAT-PROVENANCE-01 | User explicitly selects one legal option per slot into a future draft | Draft remains personal. Publishing a curated recommendation is a separate workflow, with new origin/revision and supporting sources; original source is not rewritten as author of the assembled selection. |

This refinement operationalizes the approved distinction between equipment references and precise targets. It does not add a second catalog, alter the picker or authorize real-data conversion.

## Cross-slot legality and source-grid refinement

The [Scholar source pilot](GEAR-GUIDE-T1-COVERAGE.md) establishes two additional concrete validation inputs. Its BG grid contains a category-link ranged placeholder while selecting 15 real items; this is an omitted source selection, not an item identity or an intentional empty state. Its Alternative Fast Cast table pairs a staff with a shield, despite both passing individual SCH/slot masks.

Validate composed equipment constraints after per-item eligibility. Preserve the original selection and a diagnostic on failure; never repair a source by silently removing/replacing its sub item. A proposed Nexus correction requires its own attributed composition/revision. Unknown weapon variants or context cannot pass this check merely because display names match: the Hvergelmir name has several resource IDs.

Additional fictional fixture specifications (not implemented/run): **COMPAT-GRID-01** maps the 4x4 grid's third cell to omitted `range`, retains both ring cells, and ignores category placeholders as identities. **COMPAT-LEGAL-01** gives individually SCH-eligible staff/main and shield/sub inputs; composition must reject playable certification and active output, retain both source observations and explain the conflict. A separately sourced staff/grip control may pass this constraint without proving all other requirements. Unresolved legality must remain visible in Planning analysis and cannot be presented as equip-ready.
