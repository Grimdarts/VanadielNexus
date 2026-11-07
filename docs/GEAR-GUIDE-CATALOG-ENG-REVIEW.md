# Gear Guide catalog: engineering review

Design baseline: [approved design](designs/verified-gear-guide-catalog.md).
Branch: `codex/sets-copy-fixes-review`.
Started: 2026-11-03 through GStack /plan-eng-review.
Status: ENGINEERING PLAN APPROVED by the user on 2026-11-03; T1 research/specification work is authorized and beginning. Architecture decisions 1 through 5, code-quality decision 1, performance decision 1 and two substantive outside follow-ups are resolved; planned test coverage is mapped. Two Claude document-only challenge passes are complete. Numerical budgets are accepted targets, not measured feature results. Supported-rule evidence, job coverage and visuals retain their named gates. No app-code implementation, real-data migration, executable replacement, Lua activation, commit, push or release is authorized by this approval.

## Scope and existing foundation

Implement the accepted information standard in the existing catalog and Guide upgrades workflow: refresh eight jobs and author coverage for fourteen more, with verified evidence, relevant priorities, concrete equipment versions, labeled historical/budget alternatives, and attributed Nexus recommendations. Preserve existing user data and current interface organization. The full all-job matrix remains a consolidated user review item.

Reuse `gear_guides.json`, `core/gear_guides.py`, `ui/pages/guides.py`, item resource/wiki helpers, existing classifier/review tooling, and core/Qt tests. Wishlist currently stores per-item `guideTarget` snapshots; there is no reason to replace the app database or create a parallel guide service. Sets-page matching/allocation helpers are candidates for reuse, subject to checking semantic compatibility rather than importing an entire unrelated subsystem.

No new service, concurrency system, game-side component, or publication mechanism is proposed. Keep the existing JSON resource and load-time processing. A precise implementation file list follows the decisions, not a speculative framework rewrite.

## Architecture decision 1: stable identities and immutable revisions

Approved by the user on 2026-11-03: **A — stable set identities with immutable revisions**.

Motivation in current code:

- `ui/pages/guides.py:128` applies personal overrides using job + set ID + item ID, without a revision distinction.
- `core/gear_guides.py:128-129` records a set ID and per-item target snapshot, without explicit guide revision identity.
- The approved design requires identifiable requirement changes and preservation of personal targets until explicit adoption.

This is a gap for the planned refresh, not evidence that existing saved data has been corrupted.

### Required behavior

- A recognizable conceptual set retains its stable identity; equipment/requirement/context changes are represented by a new immutable revision rather than replacing the prior revision's meaning.
- The current recommendation can advance independently of previously saved targets. A saved target refers to the exact revision/requirements chosen; simply opening the app or refreshing the catalog cannot adopt a newer target.
- Preserve existing per-item snapshots and personal augment targets. Show a reviewable old/new difference and require explicit adoption before changing what the player is pursuing. Exact UI treatment remains subject to engineering/visual review within the accepted interface constraints.
- Existing unversioned saved data must be preserved and interpreted through an explicit compatibility path. Recover an exact historical association only with evidence; otherwise retain the snapshot/override and flag it for review instead of guessing a revision.
- Removed, split, or retired entries retain a truthful reference/disposition. Do not redirect an old target to a different objective or another character.
- Repeated tracking/adoption must be idempotent. Unexpected or ambiguous references fail with a clear diagnostic and no destructive mutation. Any necessary data migration requires its separate reviewed backup/preservation plan.

### Validation included in the approved remedy

Exercise old unversioned saves, matching versus unknown historical associations, changed requirements on the same item, replacement/removed items, retired/split sets, personal overrides, repeated tracking, explicit adoption, and preservation of unrelated wishlist/goals. Verify viewing the refreshed catalog alone never changes a saved target. Source and frozen-executable validation remain separate.

Alternative not selected: assign a new unrelated set ID for every materially changed set and retain separate historical entries. This avoids a revision field but shifts complexity into grouping/retirement and obscures the relationship between successive recommendations.

## Architecture decision 2: explicit slot targets with designated bags

Approved by the user on 2026-11-03: **A — an explicit target per occupied equipment slot**, with the additional requirement to distinguish duplicate items through their designated bags. The user's example is a left ring from one box and a right ring from another.

Motivation in current code:

- `core/gear_guides.py:122` uses set/item IDs for a tracked target, so two slots with the same item would share a key.
- `ui/pages/guides.py:128,238-241` applies/saves item-based overrides without a slot distinction.
- `core/gear_guides.py:109-112` counts duplicate item IDs and checks each row independently; it does not allocate distinct matching copies across slot-specific requirements.
- Current catalog inspection found no repeated item IDs within a set. These are limitations for the planned precise sets, not proof that existing saved data was corrupted.
- Existing `core/set_manager.py` already provides bag-aware candidate matching and one-copy-per-slot allocation; `core/item_res.py:161-168` normalizes bag names including Wardrobe 1. Reuse compatible pure helpers rather than building a conflicting second set of bag rules. Guide rank/path requirements still need to be respected; reuse does not waive those checks.

### Required behavior

- Keep left/right ring and ear slots distinct. Give each target a stable slot identity within its set/revision; neither shared item ID nor list position is a sufficient persistent target key.
- A selected personal target can designate an equipment bag: for example left ring = item X in Wardrobe, right ring = item X in Wardrobe 2. Match the item, all required augments/rank/path, and the designated bag on the same physical copy for the selected character.
- Personal bag placement belongs to character-owned target/binding data, not a universal published-guide requirement. Curated set requirements and the player's physical-copy designation remain distinguishable and do not overwrite each other.
- Bag designation is supported where needed; do not require moving every duplicate to separate bags. Distinguishable augmented copies may be selected by their actual requirements. If identical copies cannot be uniquely distinguished, do not invent a persistent inventory-index identity; retain quantity/ambiguity information and require a bag designation where deterministic copy selection is needed.
- Allocate copies across the whole set so a physical copy cannot satisfy both simultaneous slots. Two matching copies in the same bag may meet an ownership/quantity target, but do not claim that bag alone uniquely identifies one of those copies for future Lua selection.
- Normalize display aliases to supported bag identities. Later Lua snippets use the actual GearSwap-accepted bag names. Preserve any existing bag/priority metadata when mapping targets to Lua; this phase writes no Lua.
- An owned item in storage is not automatically equip-ready. Keep ownership, designated-bag match, and equipment-bag reachability distinguishable. If a designated copy moves, report the mismatch rather than silently choosing another bag, rewriting its target, or moving inventory.
- Legacy item-based overrides that cannot be assigned to one slot unambiguously remain preserved and flagged for review. Do not duplicate one old override across distinct augmented targets or silently choose left versus right.

### Validation included in the approved remedy

Use fictional fixtures for paired slots with identical item IDs in different bags; distinct augments in either the same or different bags; one-copy shortages; two identical copies in one bag; moved/missing designated copies; matching items in the wrong bag; inaccessible storage; bag-name aliases; rank/path/augment requirements on one copy; character isolation; independent slot overrides/tracking; repeated tracking; and ambiguous legacy references. Confirm no inventory, personal Lua, or Windower writes occur.

Alternative not selected: shared requirement records with separate slot links. Explicit slot records are easier to inspect and map to equipment sets; compatible duplicate requirements may be repeated without adding another reference layer.

## Architecture decision 3: reject invalid catalog updates before delivery

Approved by the user on 2026-11-03: **A — validate the complete proposed catalog and block an invalid update as a whole**.

Motivation: `core/gear_guides.py:29-31` currently returns decoded JSON directly; `picker_tree` includes entries by job. The planned revision, slot, provenance and verification model needs an explicit validation boundary. This is a requirement for the new format, not an observed failure of the existing catalog.

### Required behavior and failure handling

- Validate the complete proposed deliverable before it can replace the existing catalog. Missing IDs, conflicting revisions, invalid slots, unsupported schema, malformed requirements, broken internal references, and incomplete verification records produce specific preparation diagnostics.
- Keep unresolved research in the private gap report, outside active verified-current recommendations. Automated validation checks structure and evidence records; it does not prove the research or equipment is correct.
- A malformed proposed entry must be corrected or explicitly excluded from the proposed deliverable before validation passes. Exclusion does not erase a required coverage gap or make a partial catalog complete. Historical references remain subject to the preservation policy.
- Failed preparation leaves the previous catalog intact; do not replace it with a partially generated file.
- Defensively validate supported resource structure at runtime. A corrupt or unsupported installed catalog yields a clear Guide-page error and leaves player data and the rest of Nexus intact. Do not silently substitute another schema, mark unverified data current, or mutate saved targets during recovery.

### Validation included in the approved remedy

Cover malformed JSON/data, unsupported schema, missing and duplicate IDs/references, conflicting revisions, invalid/duplicate slots, requirement types, verification eligibility and diagnostics. Verify failed preparation preserves the prior catalog and failed runtime loading does not crash the rest of Nexus or change saved user data. The corresponding user-flow recovery and frozen-executable checks must be included in the final test plan.

Alternative not selected: quarantine malformed entries at runtime and render the valid remainder. The chosen approach catches bad proposed updates before delivery and keeps runtime recovery narrow.

## Open architecture work

The identified architecture decisions are recorded below and above. Continue evaluating legacy consumers, supported-rule coverage and implementation coupling during code-quality/test review. New independent findings need their own decision; previous remedies and validation obligations must not be re-asked or silently weakened. Keep catalog and feature-design boundaries explicit.

## Architecture decision 5: selected-entry source references and contextual chooser

Approved by the user on 2026-11-03: **A — selected-entry sources, with a chooser only when needed**.

Motivation: `ui/pages/guides.py:246-252` opens one selected-set URL and a job-level guide URL; the refreshed catalog supports multiple guides per job and multi-source Nexus assemblies without an FFXIAH item-set page.

### Required behavior and failure handling

- Source actions follow the selected conceptual set/revision, not simply the first guide for that job. Preserve distinct reference purposes such as published equipment table, job guide and supporting evidence.
- Reuse the current source-button area. Open a single applicable reference directly; when several apply, offer a small menu with truthful source labels. Final labels, styling and placement remain visual-review decisions.
- Explicitly identify Nexus recommendations and their rationale; a supporting page must not be presented as publishing the entire assembled set. Do not invent FFXIAH URLs for internal IDs.
- Keep item-wiki navigation separate from set/guide evidence. Preserve correct navigation for both new targets and legacy saved wishlist items.
- Validate supported source types and URLs before publication. Missing/unavailable historical references produce a clear unavailable state without changing the saved target or substituting an unrelated reference. Do not automatically open pages during selection, hover or calculation.

### Validation included in the approved remedy

Cover single/multiple references, multiple guides for one job, selected-revision source changes, published versus Nexus-authored sets, absent/invalid/unavailable historical references, item-wiki separation, correct legacy saved-target navigation, and source selection that changes while a menu is open. Invalid or stale navigation must not open a different set's source. Detailed handling remains part of the implementation/test review; no source UI has been changed yet.

Alternative not selected: open only a designated primary reference and list the remaining references in details. The selected chooser keeps all relevant evidence accessible from existing controls.

## Architecture decision 4: verified description rules with targeted exceptions

Approved by the user on 2026-11-03: **A — verified reusable description rules plus targeted item-specific exceptions**.

Motivation: `core/item_res.py:24-34,106-117` provides item identity and eligibility metadata rather than normalized stat effects. The local description resource supplies text, not an already validated numeric effect model. The accepted feature design requires one shared interpretation for cards, calculations and later draft sets.

### Required behavior

- Define supported stat wording and its scope once, with explicit units, recipient and conditional/stacking semantics. Never scrape arbitrary signed numbers and assume they are additive master stats.
- Preserve source text and a contribution trail for recognized effects. Keep display grouping distinct from numeric interpretation: showing readable description text does not assert that it has been calculated.
- Use reviewed, version-identified exceptions for unusual or hidden effects, with evidence and applicability conditions. Maintain focused exceptions rather than a second full database of every item.
- Preserve observed augment/rank/path data and target assumptions separately. A rank without decoded or independently established effects is not a calculated augment contribution.
- Unsupported or ambiguous wording remains visible and uncalculated, with affected-result completeness as defined in the approved feature design. Never present it as zero or a reliable cap/upgrade conclusion.
- Resource identity/version changes invalidate affected cached interpretations; rule/exception version changes also invalidate dependent results. An exception whose applicability to changed source data is unresolved cannot silently override the new text.
- Parsing and resolution remain local and non-executing for source data. No game polling or online request is triggered by a hover, calculation or draft edit.
- Unknown stat effects are supported analytical states, not necessarily malformed guide records. Keep schema/verification eligibility validation separate from calculator coverage; a verified guide composition can have explicitly unsupported stat effects without fabricating a complete total.

### Shared flow

```text
local item metadata + description text + observed augments / planning requirements
  -> bounded non-executing read and source identity
  -> verified rules + applicable item-specific exceptions
  -> normalized known effects + conditions + unresolved effects + provenance
       -> item-card presentation
       -> declared-set composition + one-copy/slot/context validation
            -> equipment contributions + supported conditional rules
            -> per-result completeness + same-scenario comparison
                 -> existing-set analyzer first
                 -> owned/planning drafts later
```

### Validation included in the approved remedy

Use independently expected fixtures for common base stats, augments, supported conditionals and verified exceptions; ambiguous/unrecognized wording; master versus pet recipients; units/signs; partial recognition; rule/source version changes; inapplicable exceptions; missing resources; and consistency between card and calculator contribution data. Do not use the engine's own output as its expected result. Coverage matrices, exact rule representation and performance budgets remain engineering work, not claimed validated behavior.

Alternative not selected: maintain a curated numeric definition for every supported item. That simplifies runtime lookup but increases per-item maintenance and duplicates more of the locally available source data.

## Extension discovery: item cards and equipment calculator/builder

This section records the accepted feature direction and its lineage, not a completed engineering implementation plan.

The separate feature design is [item cards, equipment totals and set builder](designs/item-details-calculator-builder.md). The user approved it on 2026-11-03 after native and Claude review; the previously approved catalog design and architecture decisions remain intact.

- The user wants styled item hover cards that explain equipment and the selected copy's augments more cleanly than the in-game window, helping distinguish gear choices. Keep observed copy details, guide requirements, and personal bag designations distinct.
- They also want a calculator in relevant equipment-set views and the ability to assemble their own sets in Nexus.
- Selected calculator direction on 2026-11-03: **equipment totals first, with an added layer for conditionals**. This is not a request for a full character/buff/food or damage simulation engine.
- Builder inventory direction accepted on 2026-11-03: **Owned gear by default, with an explicit Planning option**. Owned selections retain exact observed copies, augments, character and bag bindings. Planning may include unowned gear and specified target augments, but must visibly distinguish those assumptions from observations and must not present a hypothetical set as equip-ready.
- Delivery order A accepted on 2026-11-03: prove shared item cards and equipment/conditional totals on existing sets first, then implement the owned/planning builder on that foundation. Both phases remain in the intended scope. The extension design is now accepted; detailed implementation and visuals remain review gates.
- The user explicitly prioritizes a small installation and avoiding app/game slowdown. Reuse available local item descriptions and inventory snapshots; do not assume a need for a large bundled equipment database or new in-game polling.
- Read-only discovery found the local Windower `res/item_descriptions.lua` at 4,972,281 bytes. It contains base-description text; the current addon already exports observed augments and bag locations in inventory snapshots. These are useful inputs, not a complete validated stat-calculation engine. No size/latency/memory benchmark for the proposed feature has been performed.
- Proposed behavior for further discussion: a supported unconditional equipment contribution, a separately attributed conditional contribution under explicit assumptions, and a clearly identified list of unresolved/unsupported effects. An unknown effect cannot silently become zero or an asserted cap result. Automatic set-count conditions and manually chosen scenario conditions need a precise rule design.
- The agreed user workflow includes before/after changes when replacing equipment, inspectable contribution sources, explicit scenario conditions, and a visible not-calculated category. Enabling a required-buff condition applies supported conditional equipment effects only; it does not assert a full calculation of that buff's character-stat bonuses. Exact condition rules and supported-stat coverage still require research and validation.
- Preserve the user's read-only player-Lua boundary. Set drafting inside Nexus and copyable output can be explored; automatic player-Lua writes, item movement, game commands, and bundle activation are not authorized.
- The accepted extension design does not approve a final calculator layout or stat engine implementation. Visual mockups, stat/rule scope, condition handling, draft persistence, tests, and performance acceptance still need review. No calculator or hover-card implementation has begun.

## Code-quality decision 1: shared pure matching core with explicit policies

Approved by the user on 2026-11-03: **A — extract small shared matching/allocation primitives and retain explicit policy boundaries**.

Motivation: `core/set_manager.py:12` imports shared values from `gear_guides`; a reverse top-level import would create a cycle. Existing GearSwap matching deliberately accepts some combinations that do not establish strict guide completion, including the Rare-item shortcut in `equip_match`. The new features must not confuse selectability with verified requirements or calculated effects.

- Extract only needed pure normalization/copy-allocation primitives into a neutral core module. It must not import Guide UI, Sets UI or Lua-reader host execution. Preserve existing public helper imports through thin wrappers/re-exports where needed.
- Keep GearSwap selector compatibility, strict guide-target verification, and equipment-effect interpretation as separate policies using shared facts. A Rare-item selector match must not waive unknown guide rank/path/augment requirements.
- Preserve immutable raw observations alongside normalized matching values. Dropping synthetic rank text for GearSwap comparison must not erase the rank observation or turn it into a real augment for calculation/export.
- Keep item/job eligibility, bag-name normalization and one-unit-per-slot allocation consistent across guides, Sets and builder. Reuse existing source rules without copying competing implementations.
- Validate both module import orders, existing Sets and Guide behavior, matching subset/duplicates/quotes/path semantics, strict guide requirements on Rare and non-Rare items, unknown rank/path, and paired-slot/bag/character cases. Existing compatibility tests remain meaningful; new strict-policy expectations must be tested separately.

Alternative not selected: a translation adapter around the entire Sets subsystem. This would couple guide/draft targets to Lua-reader-oriented objects and require dependency cleanup anyway.

The remaining code-quality pass found no new independent issue beyond these approved remedies. Interpretation errors, stale references, unresolved conditions and partial data are already covered by decisions 1–5 and the accepted feature design; do not ask again for their included failure handling.

## Test review: execution paths and coverage obligations

Framework: Python pytest + pytest-qt, with LuaJIT-backed existing suites; `requirements.txt` includes pytest and pytest-qt. Use the existing test conventions and temporary/fictional player fixtures. No code changed and no test suite was run for this planning update.

Existing evidence read in source:

- `tests/core/test_gear_guides.py` covers same-copy augment requirements, character matching, unknown rank/path, two-copy shortage, idempotent tracking and preserved personal goals.
- `tests/core/test_set_manager.py` covers selector compatibility, duplicate augment consumption, rank/path handling and allocation. The new common-core extraction must retain these semantics.
- `tests/core/test_guide_catalog.py` covers grouping/purposes/version ordering and unknown title classification. Update its old best-first assumptions only where the accepted contextual grouping requires it; do not weaken integrity checks.
- `tests/ui/test_guide_controls.py` checks character selection, no implicit import and idempotent explicit tracking. These remain relevant but do not prove the new revision, source or calculator behavior.

The diagram labels future coverage as PLANNED, not passed. Existing tests cover portions of some branches; the new behavior remains to be implemented and verified.

```text
CODE / DATA PATHS                                 PLAYER FLOWS
proposed catalog -> validator                     open Guide upgrades
  valid schema/references [PLANNED]                  verified eligible entries -> picker [PLANNED]
  bad schema/IDs/slots -> reject [PLANNED]            corrupt resource -> page error, app usable [PLANNED -> Qt]
  unresolved research -> private gap report          no automatic tracking/adoption [EXISTING + EXTEND]
  failed preparation -> old artifact intact

set identity -> immutable revision                revisit saved target after refresh
  legacy exact/unknown -> preserve [PLANNED]          old target remains old [PLANNED -> integration]
  changed/retired/split -> disposition                explicit adoption -> intended changes only
  new revision -> current recommendation             repeated track/adopt -> no duplicates
  item sources -> one/direct or many/menu            stale menu -> no wrong-set page [PLANNED -> Qt]

slot targets + inventory -> shared copy matching   select paired slots / designated bag
  units -> candidate graph -> allocation              one copy cannot serve both [EXISTING + EXTEND]
  augments + rank/path + bag + character              wrong bag / unknown rank / other character honest
  selector policy vs strict target policy            old unscoped override -> review, not guessed
  missing/ambiguous/inaccessible -> diagnostic

source text + raw augments -> effect model          inspect item / compare two existing sets
  supported rule -> attributed effects [PLANNED]      focus/click details equal hover [PLANNED -> Qt]
  verified exception -> source/version check          snapshot copy vs planned target distinguishable
  unknown text -> unresolved effects                 unsupported effect visible, not zero
  source/rule change -> invalidate                    rapid selection -> no stale card/result

declared slots + context -> equipment results      same-scenario condition toggle
  omissions/empty/overlay/alias [PLANNED]             selected contributions update together
  known vs unknown conditions / effect order         incomplete result -> no exact cap/upgrade claim
  recipient/unit/rounding/cap separation              before/after existing-set comparison honest
  independent expected outcomes per verified rule

builder (later slice) -> Nexus-owned draft         owned default / explicit Planning
  slot/job/cross-slot + quantity validation           illegal/ambiguous -> not equip-ready
  saved observations + revision snapshot              inventory moved/changed -> review, no silent bind
  save/reopen/corrupt/stale data -> preserve           unrelated wishlist/goals/source files unchanged
  resolved output vs commented planning scaffold      copy only, no live-file write or game command
```

Implementation test additions map to existing core/Qt suites where they belong; isolate new effect/condition and draft-persistence tests rather than packing them into one UI smoke test. Exact test filenames follow the final module names. Numeric rule fixtures must have independently derived expected values and source evidence. No LLM feature is proposed, so LLM evals are not applicable.

Integration coverage is required where unit mocking could hide preservation failures: old database/settings plus refreshed catalog, exact-copy allocation across a set, draft save/reopen with inventory drift, source actions through UI selection, and installed frozen-resource startup. Use temporary data; do not migrate the real database as a test.

Mandatory regression protections include existing source-reader/read-only boundaries, Sets selection/snippet behavior, guide tracking and item-wiki behavior, and unrelated app pages after a catalog-load error. The earlier Sets manual checklist is not reopened; the new feature gets its own relevant walkthrough. Full `py -3 -m pytest -q -rs` and staged/installed artifact checks follow the accepted implementation gates, with exact pass/skip reporting.

These tests instantiate remedies already approved; no new independent test tradeoff is raised. New code has no test-pass evidence yet. The supported-stat/rule matrix and independent numeric cases remain a concrete pre-implementation engineering task, not a claim of full stat coverage.

## Performance evidence and pending decision

A read-only probe on 2026-11-03 used the existing `item_res.parse_rows` against the installed local description resource. It did not modify Windower, query the running game, or emit personal equipment data.

| Measurement | Observed |
|---|---:|
| Source bytes | 4,972,281 |
| Parsed description rows | 23,456 |
| Full parse with Python memory tracing enabled | 0.7644 seconds |
| Traced retained allocations before separate English index | 13.90 MiB |
| Traced peak allocations before separate English index | 14.06 MiB |
| Build English ID/text lookup from parsed rows | 0.0045 seconds |
| 10,000 dictionary lookups with tracing enabled | 0.0029 seconds |

This is one instrumented parser probe, not a cold-disk benchmark, whole-app RSS measurement, new feature latency test or game-performance test. Tracing changes timing; full parsed rows include content the final feature need not retain. It establishes a concrete reason to keep first-load preparation off the hover path and reuse an index, not a proven final cache size or responsiveness budget.

## Performance decision 1: in-memory prepared index and bounded results

The user delegated this decision on 2026-11-03; the recommended **A — in-memory prepared index with bounded result caches** was selected. No persistent item/stat index is introduced initially.

- Prepare local data on first relevant use outside the interactive hover path, coalesce duplicate requests, and retain only needed normalized/index data rather than unused full resource rows.
- Show a truthful loading/unavailable state and raw fallback details where available. Discard stale completions after selection/source changes; errors and shutdown must release work without leaving the page loading or touching saved data.
- Bound retained data/results and invalidate them on relevant source/rule/augment/scenario changes. No hover-triggered scan, game polling or network request.
- Measure first-use preparation, warm hover/recalculation, app memory/cache growth and frozen size. This decision does not claim final performance from the parser probe.

Alternative not selected: persistent validated local index, which would add disk-cache versioning/corruption recovery to optimize restart preparation before a measured need exists.

The draft [execution plan](GEAR-GUIDE-IMPLEMENTATION-PLAN.md) supplies proposed numerical targets, implementation tasks, failure coverage and remaining evidence/visual gates. The user has not yet accepted those targets or authorized implementation. A future measured need for persistent caching or changed budgets returns for review rather than being silently added.

## Outside-review decision 1: isolate new personal workspace persistence

Approved by the user on 2026-11-03: **A — a separate, small versioned personal-workspace file** for new drafts and revision/slot/bag-bound targets. This is saved player work, not a persistent item/stat cache or bundled equipment database.

Calibration: existing Settings/database writers preserve many unknown fields, so generic loss of all unknown fields was not demonstrated. The concrete concern is the legacy augment editor's `guideTarget` update by job/set/item (`guides.py:238-242`), without slot/revision distinctions. Do not place new authoritative records in that mutable legacy shape.

- Store authoritative workspace data independently under the existing per-user data-root policy, with explicit version/shape validation, atomic writes, backup/recovery and no silent downgrade of unsupported versions.
- Leave legacy data unchanged. Explicit import/adoption copies a reviewed snapshot; the original is not silently removed or retargeted. Associate records for display only when identity is proven; unresolved conflicts remain visible instead of automatically merged.
- Older Nexus builds cannot display the new workspace but do not write it. Do not dual-write authoritative records back into legacy targets. The new UI may join entries for display while preserving their origin and authority.
- Conversion of existing records is a migration requiring its separately reviewed backup/preservation plan and authorization. Creating an empty workspace or explicitly saving a new draft is ordinary feature persistence, not permission to migrate existing records.
- Test old-app save/edit/recovery on legacy fixtures while the workspace remains byte-for-byte intact; new-app reopening; failed saves; corrupt/unsupported workspace versions; explicit import/adoption; duplicate presentation; and independent legacy edits. Preserve both sides of a conflict for review.

Alternative not selected: new namespaced records inside the existing database, requiring stronger evidence across older writers/recovery paths.

Generated-Lua verification was subsequently approved separately as outside-review decision 2 below.

## Outside-review decision 2: existing-reader export round trips

Approved by the user on 2026-11-03: **A — existing-reader round trips**, with explicit LuaJIT/Lua 5.1-compatible syntax validation and runtime identity reporting.

- Test generated active output in temporary entry fixtures through the existing bounded read-only reader and shared selector policy. Compare independently expected slot/name/augment/designated-bag values to the builder selection.
- Preserve ambiguity: do not assert exact physical-copy identity for indistinguishable unresolved selections or use a transient inventory index as persistent identity. Invalid/unresolved active output remains blocked by the accepted contract.
- Cover quoting/control characters, duplicate paired slots, augment formatting, designated bags, empty/omitted slots and invalid output. Planning scaffolds receive compatible syntax validation and a check for no active assignments/commands.
- The current worker already uses `lupa.luajit21`; the outside review identified a missing explicit exporter test contract, not an observed Lua 5.4 worker bug. Offline equivalence does not establish live timing or activation parity.

Alternative not selected: maintain a dedicated minimal export-test harness. Reuse the production reader boundary instead.

## Outside hook clarification and optional refinements

The accepted design already requires a one-command hook bypass where needed and exact staged/installed artifact validation. The hook follow-up is resolved by specifying `git -c core.hooksPath=<verified-empty-temporary-directory> commit ...` for a future separately authorized commit; `--no-verify` is not a post-commit bypass. Do not change persistent config/hooks. Check installed-executable hash and absence of new build activity, accounting for any pre-existing build, then use only separately authorized controlled build/install steps. No command is executed by recording this mechanism.

The execution plan also makes three existing requirements concrete: measure actual GUI event-loop gaps during preparation; evaluate supported set-count/multi-item effects at loadout scope (already required by the feature design); and distinguish build-time artifact preservation from the installed resource failure path. These clarify accepted failure/performance obligations and do not introduce persistent caching, full simulation or automatic rollback.

## Review progress

| Section | State |
|---|---|
| Scope and reuse | Existing JSON/core/Qt workflow retained; no new services proposed |
| Architecture | Initial pass complete; decisions 1 through 5 approved |
| Code quality | Initial pass complete; shared-core decision 1 approved |
| Tests and execution diagram | Planned coverage mapped; no implementation test run |
| Performance | Read-only parser probe recorded; in-memory strategy selected under user delegation |
| Outside engineering-plan challenge | Two passes complete; substantive follow-ups resolved; ready for final acceptance |

The [execution plan](GEAR-GUIDE-IMPLEMENTATION-PLAN.md) records the tasks, coverage/failure map, proposed numerical budgets, complete review summary and outside-review calibration. Persistence and export remedies received individual user approval; the hook mechanism clarifies the already-approved policy. The outside recheck found no remaining material contradiction and reported **Ready for final plan acceptance**; primary review applied its minor dependency/hook/status edits without a third external pass. User acceptance is pending. No code tests were run for this documentation-only record.
