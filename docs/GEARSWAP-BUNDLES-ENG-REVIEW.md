# GearSwap bundles: stage-1 engineering plan

Design baseline: [approved design](designs/gearswap-job-bundles.md).
Status: APPROVED by Jason on 2026-11-02. Begin T1/T2 contract specification and read-only baseline capture; dependent implementation follows their evidence and decision gates. Installed-file activation and publication remain separate actions.

## Review depth

Approved: detailed first-stage plan for file ownership, supported data format, character-profile loading, validation, and SMN parity. Check later Nexus/G13/automation integration boundaries; their detailed implementation remains staged. All baseline features remain in scope.

## Architecture decision 1: preserve initialization frameworks

Approved: one shared player-facing file contract and loader, with small framework-specific integration layers. Preserve SMN's existing Mote initialization and BLU/RUN's custom event handling during migration. Do not convert every job to one framework in this stage.

Evidence: Someonesmall-SMN-lib.lua:70-75 initializes Mote-Include. Mote-Include.lua:146-175 loads globals and sidecars, runs setup, then initializes sets. Someonesmall-RUN.lua:25-27 directly loads its sets. Nova-Common.lua:293 onward wraps get_sets and installs controls after original initialization.

Required validation within this decision: supported player data must be ready at the appropriate job lifecycle point; attach shared controls once after successful setup; clean partial initialization on failure; verify reload/unload leaves no duplicate owned bindings or callbacks. Preserve existing working mode and M-button behavior.

## Architecture decision 2: declarative set inheritance

Approved: player sets declare base sets (including ordered multiple bases when needed) and slot overrides as data. Maintained code resolves the final GearSwap tables. Players do not need to write combination functions for supported managed sets. Plain item names and catalog references remain supported as approved in the design.

Required within this remedy: missing-base and cycle detection; catalog-reference and slot validation; errors naming affected set and slot. Stage 1 retains per-slot origin information for the later Nexus stage to distinguish inherited equipment from local overrides. Preserve existing SMN combination precedence during conversion. Exact data syntax, whole-slot replacement, intentional empty/omitted-slot behavior, and representation of nested set paths must be specified before implementation.

Evidence: Someonesmall-SMN-sets.lua:139-142 combines base/accuracy/TP Blood Pact sets with set_combine; lines 153 and 170 define additional derived sets. The new format must represent these existing combinations without changing resolved equipment.

## Architecture decision 3: directory ownership boundary

Approved: separate maintained PlayerSystem and personal PlayerProfiles folders under GearSwap/data, with small character-job entry files discoverable by GearSwap. PlayerSystem contains core, job logic, integrations, and inactive examples. PlayerProfiles/<profile> contains Equipment.lua, Settings.lua, Hotkeys.lua, Sets/<JOB>.lua, and optional G13.lua/Automation.lua personal configuration. Names are neutral. This is the agreed target organization; implementation must verify include-path resolution and collisions before installation.

Updates replace maintained code only and never overwrite active personal profiles. Incompatible existing profiles require an explicit migration. Optional feature behavior belongs in maintained modules, with preferences in the profile. Required file failures follow the design's clear-error rule. Explicit character/server binding was approved in architecture decision 4; metadata syntax and profile naming remain specification tasks. Entry-file ownership and compatibility with existing discovery precedence must be specified before migration.

## Architecture decision 4: explicit character-to-profile binding

Approved: setup explicitly binds the character entry/configuration to a profile and intended character/server identity. Profile selection does not depend on Nexus, folder-name guessing, or a generic Main/default character. Verify available live identity before initializing managed behavior. A missing profile or mismatch is a clear setup error. Temporarily unavailable identity permits bounded deferred initialization; permanent failure must report an actionable error rather than wait forever. Determine the actual identity source and retry policy before implementation.

Evidence motivating isolation: the current resource bridge VanadielNexus.lua:175-176 uses player.name or Main for inventory labeling. Do not reuse that inventory fallback as the new profile resolver. This is not evidence of an existing wrong-profile bug. Exact server validation and binding metadata syntax remain engineering tasks.

## Architecture decision 5: settings and hotkey override semantics

Approved: recursively merge named settings across built-in defaults, character shared settings, and character job overrides. Omitted values inherit. Replace ordered lists as a whole, rather than merging their elements. Supply a documented explicit removal marker for inherited optional entries/hotkeys. Reject unknown settings and invalid types with actionable configuration errors; do not silently coerce them. Exact marker spelling and schema belong in the supported-format specification.

Gear set resolution is a distinct operation: do not apply settings deep-merge behavior to equipment records or augment arrays. Preserving ordered base precedence and per-slot semantics is required by the approved inheritance remedy.

## Architecture section status

Main decisions approved. Implementation specification still must provide concrete syntax, identity source/retry policy, discovery-compatible entry naming, and cleanup order. These are explicit engineering tasks under the approved remedies, not a completed implementation. Cross-stage boundaries remain as in the approved design: managed-data inspection for Nexus, commands/state for optional displays, optional action initiation separate from core swaps, independent experimental coordination.

## Code-quality decision 1: isolate working equipment tables

Approved: resolve independent working equipment records at successful job load. Copy nested augment lists and other item metadata; do not expose mutable catalog tables as working equipment. Treat the loaded catalog and resolved source sets as definitions. Job logic makes temporary working overrides rather than editing shared definitions. A saved catalog edit affects consumers after the next successful reload, not as an unreviewed hot mutation.

Required validation in this remedy: modifying one resolved item/augment list cannot change another resolved set or the source catalog; inheritance and temporary overrides preserve intended values, bag constraints, priorities, and intentional empty slots. Do not deep-copy the entire catalog per action. Cache lifetime and reload invalidation are part of the performance review.

Evidence: Someonesmall-SMN-sets.lua:55 and :58 assign two named uses to the same catalog cape record. This proves aliasing exists, not that the installed job currently mutates it incorrectly.

## Remaining code-quality review

No additional issues beyond the approved remedies. Reuse existing job logic, discovery rules, item metadata, and command meanings. Do not duplicate the existing sandbox reader or add a second full Lua evaluator. A small, versioned managed-data format must be defined before conversion; its parser accepts only that format and does not execute arbitrary profile code. Existing custom Lua remains on the existing sandboxed/read-only inspection and copy workflow.

Initial format specification task must cover: version tag; named equipment records with separate readable labels; plain item strings or explicit record references; named set paths; ordered base references; local slot overrides; allowed comments/literals; explicit settings-removal marker; bag/priority metadata; and intentional empty-slot versus absent-slot semantics. Later base sets override earlier ones, then local slots override bases. Replace equipment slots as whole records, not merged item fields. Retain source provenance for diagnostics and future editor display. Unsupported custom expressions must be diagnosed rather than silently discarded.

Legacy plain runtime sets and aliases may contain cycles or intentionally absent branches; do not blindly serialize the entire runtime table graph. Capture canonical equipment leaves plus required aliases/behavior, with cycle-safe traversal. Existing real-file tests already distinguish known non-set/absent branches; establish which are relevant before conversion. Do not silently fix unrelated old behavior while measuring parity.

## Loading and failure flow

```text
GearSwap-selected character/job entry
  -> explicit profile binding
  -> verify live name + server association
       temporary identity absence -> bounded wait -> retry or clear failure
       mismatch -> error, no managed job initialization
  -> read required profile data into candidate configuration
       missing/syntax/version/type/reference/cycle error -> diagnostic + stop
  -> resolve settings, catalog, ordered bases and independent gear records
  -> initialize existing job framework through its integration layer
       setup failure -> release this attempt's owned resources + stop
  -> attach shared commands/keyboard controls once
  -> optionally attach existing G13 compatibility, preserve working behavior
  -> publish ready state

unload/job change -> stop owned work -> remove owned handlers/bindings
                 -> remove ready/session state -> release resolved tables
```

Put the initialization/cleanup flow in a comment near the loader state machine during implementation. Use explicit lifecycle ownership; errors are surfaced once with profile/file/set/slot context as applicable. No last-good profile fallback or cross-character fallback. Invalid edited files require correction and reload. Partial initialization may not leave managed actions active.

Identity evidence: Windower's official definitions document get_info().server as a server ID when logged in and nil otherwise (https://github.com/Windower/Lua/blob/dev/definitions/windower.lua). Prefer this existing API with get_player().name; verify actual installed runtime availability in the read-only probe before implementation. Never use GearSwap world.area as a server identifier. The exact bounded wait and explicit-retry behavior is part of T1's specification.

## What already exists

| Existing component | Reuse / check |
|---|---|
| SMN entry, sets, and library | Preserve Mote hooks, pact classification, modes, equipment and command behavior; separate responsibilities incrementally |
| BLU/RUN custom job logic and separate sets | Paper-map representative sets and initialization to the same data contract; no migration of these jobs in stage 1 |
| Someonesmall-gear.lua | Source for exact equipment records and augments; preserve identity when creating the new profile catalog |
| Nova-Common.lua | Source for command/key labels, weapon-lock behavior, working M-button bindings, display compatibility; avoid attaching both old and new owners to one hook |
| GearSwap refresh.lua:98-105, :700-729 | Authoritative entry/include search order; check for shadowing before changing any entry file |
| Nexus core/gearswap_files.py | Reuse its discovery knowledge and tests; do not change arbitrary-Lua write policy |
| Nexus core/gearswap_reader.py and gs_sandbox.lua | Existing bounded child-process read, dependency cache, item metadata/provenance; inspect managed-format compatibility without weakening isolation |
| pytest + lupa.luajit21 tests | Reuse test infrastructure, local read-only job fixtures, discovery/cache tests; report skipped dependencies |

## Test review and planned coverage

No independent new design decision is needed: the approved remedies already require validation, cleanup, mutation isolation, and parity checks. Existing tests cover legacy discovery, sandbox timeouts, caching and real-file reads; they do not prove future managed loader behavior. All new branches below are planned coverage, not tests already passed.

```text
PLANNED CODE PATHS                     PLAYER FLOWS
profile binding + identity             initial setup / login [LIVE]
  valid / nil / mismatch / timeout       correct profile; useful retry/error
required data parse + schema           hand edit -> reload
  valid / missing / malformed            named file/key diagnostics
  unknown version/type/key               no silent fallback or half-ready job
reference + inheritance resolver       add gear / reuse / derive set
  missing ref/base / cycles              exact augments; clear bad-reference error
  ordered bases / local override         intended final equipment
  absent / intentional empty slot        preserve omission versus empty behavior
  bag / priority / duplicate item        preserve constraints and leaf metadata
settings + hotkeys                     common defaults -> job override
  recursive map / list replace           unrelated values preserved
  explicit removal / invalid types       inherited binding can be disabled
working-copy materialization           temporary job-specific adjustment
  nested mutation isolation              catalog and other sets unchanged
framework adapter + control attach     reload / change job [LIVE]
  success / failure at each step          no duplicate hooks, stale commands
  reload/unload idempotence               optional modules absent still works
SMN behavior comparison                summon / pacts / modes / locks [LIVE]
  canonical leaves + action snapshots    exact copies and timing requirements
read-only inspection integration       view managed job in current Nexus
  discover includes / warm cache         no writes or GUI-thread execution
```

Failures and recovery obligations:

| Path | Realistic failure | Planned handling and verification |
|---|---|---|
| Entry discovery | Old underscore entry shadows new hyphen entry | Inspect actual search precedence; demonstrate selected path in staging; never delete a competing entry without a migration record |
| Identity | get_player/get_info absent during login | Bounded deferred init with explicit retry path; no actions/profile fallback; unit fixtures plus live probe |
| Profile parser | Typo, unsupported expression, truncated file | Identify file/location; reject candidate before setup; parser and sandbox-boundary tests |
| Version/overrides | Old schema or unexpected setting type | Explain required version/key; no silent coercion or rewriting personal files; schema matrix tests |
| Equipment | Reference missing or conflicting inherited slot | Named set/slot/reference error; exact resolution and order tests |
| Working copy | Nested augments still alias source | Nested mutation test across catalog/base/derived/temporary sets |
| Framework setup | Failure after an event/binding is attached | Ownership ledger and cleanup; inject failure at each init boundary and reload afterward |
| Unload | Duplicate call, delayed callback after teardown | Idempotent teardown and generation/liveness checks where needed; no stale ready data |
| Compatibility | Controls or weapon locks change while moving hooks | Offline command/state snapshots plus actual SMN/M-button/live gear checks |
| Baseline | Legacy reader omits dynamic branches | Document coverage; action-context snapshots and live checks supplement static leaf comparison |

No known critical gap is left without planned handling/test, but none of these future tests has run. Full gameplay parity cannot be inferred from a sandbox set dump alone.

Test commands during implementation: focused new contract/loader pytest suites backed by Lua 5.1-compatible fixtures; existing tests/core/test_gearswap_files.py, tests/core/test_gearswap_reader.py and tests/test_gearswap_real_files.py as relevant; then the repository-required `py -3 -m pytest -q`. Run syntax checks against staged Lua, not by replacing installed files. Skip reporting must identify unavailable dependencies. No LLM prompt features or web routes are part of this stage.

## Performance review

No additional issue requiring a user decision. The approved load-time materialization avoids deep-copying all gear per action. Specify and verify:

- Parse, validate, and resolve only the selected profile/job at load or explicit reload. Do not scan 22 job files, read disk, or call Nexus in action handlers.
- Resolve inheritance with memoization and explicit cycle detection. Bound accepted input size/depth and report a clear diagnostic, avoiding unbounded recursion on malformed profiles.
- Reuse prepared tables for normal selection; construct only necessary temporary overrides. Cache is scoped to a character/job load generation and discarded on unload or reload, so catalog edits take effect on successful reload.
- Runtime mode/buff/pet changes remain dynamic inputs to existing job logic; they must not be frozen into the load-time cache.
- No background file watcher or new polling loop in stage 1. Preserve current display refresh behavior; shaped rendering is later.
- Record load time, action-handler time and memory before/after with equivalent fixtures. Report measured changes rather than inventing a numeric budget. Existing Nexus cold/warm-read tests are reader budgets, not gameplay timing evidence.

## NOT in scope for stage 1

- Shaped in-game G13 renderer and LCD page redesign: retained scope for the next display stage after actual applet inspection/mockup approval. Preserve current functioning displays now.
- Nexus direct-save implementation: later stage against the proven data format; keep existing arbitrary-Lua inspection/copy behavior.
- New automatic action routines, multibox transport and coordination: separate experimental workstream, requires live volunteer validation.
- Migrating all other jobs, changing SMN gameplay, or applying research gear upgrades: first prove reference behavior and review improvements individually.
- Public release channel, updater and CI publication: deferred packaging decision; no publish/tag/push in this review. Initial artifact is a local staged Windows/Windower bundle with examples, manifest, migration and rollback instructions.
- Standalone new TODO proposals: none. Existing deferred scope remains documented in the approved design rather than being re-added to TODOS.md.

## Implementation Tasks

Tasks derive from approved architecture/code-quality findings. Exact new source filenames must follow the contract; proposed module locations below are destinations in a staged bundle, not authorization to edit live Windower. Estimates are deliberately not supplied before the SMN baseline inventory; dependency order is actionable without speculative time promises.

- [ ] **T1 (P1) — Specify and prove the managed data contract.** Architecture 1-5. Write the schema/examples, profile binding/identity readiness policy, entry discovery/migration rules, set-path and ordered-base semantics, empty/omitted slots, whole-item override behavior, settings removal and version compatibility. Read-only check SMN plus representative BLU/RUN mappings. Locations: docs/ and staged bundle examples/. Verify examples express current combinations and exact augmented records; capture installed runtime identity availability. Gate: contract evidence before converter/loader implementation.
- [ ] **T2 (P1) — Capture the SMN reference behavior.** Architecture 1 and code-quality 1. Inventory source hashes, required dependencies, modes, actions, defaults, automatic action use, and existing G13 command/display behavior. Record canonical resolved leaves plus selected action-context snapshots, cycle-safe. Locations: private local staging manifest and sanitized tests/ fixtures. No personal inventory committed. Verify baseline read is non-mutating; Jason supplies live observations where mocks cannot prove behavior. Gate unresolved parity expectations for discussion instead of silently fixing them.
- [x] **T3 (P1) — Implement and test candidate loading and resolution.** Architecture 2/4/5 and code-quality 1. Staged PlayerSystem/core plus profile examples; pure-data validation, named diagnostics, ordered inheritance, item-copy isolation and override semantics. LuaJIT and isolated Python-consumer coverage completed; see [T3 validation](GEARSWAP-T3-VALIDATION.md). Live binding/readiness and framework ownership remain T4 integration duties.
- [ ] **T4 (P1) — Integrate SMN through its existing lifecycle.** Architecture 1/3/4. Staged controller, ownership cleanup, SMN schemas/registry, Mote adapter, pact-gear repair and inactive entry template implemented; offline failures/retries and four subjob contexts validated. See [T4 progress](GEARSWAP-T4-VALIDATION.md). Remains open for installed-runtime service wiring/control snapshots and live identity verification before activation. Keep unconverted jobs and shared live dependencies unchanged.
- [ ] **T5 (P1) — Convert personal SMN data without behavior drift.** Architecture 2/3 and code-quality 1. Staged PlayerProfiles: catalog, settings, hotkeys, Sets/SMN.lua and optional existing preferences. Preserve augments, bags, priorities, alias uses and inherited order. Verify canonical and action-context comparisons against T2; every intentional difference needs explicit review. Verify supported structures remain inspectable by Nexus or report a compatibility block before activation.
- [ ] **T6 (P1) — Package a reversible local candidate and validate live.** Architecture 3 plus parity obligation. Staged manifest, setup examples/instructions, source conflict checks, backup/restore procedure, personal-file preservation. Gate installation separately from this planning review. After authorized installation independently hash/read back files; run the focused/full checks and Jason's live checklist. A failed check blocks extension to other jobs. No Nexus executable change expected; if integration unexpectedly requires one, evaluate scope first and require actual frozen startup checks.

Dependencies: T1/T2 -> T3 -> T4 -> T5 -> T6. Sequential implementation is preferred: contract, lifecycle and conversion overlap and parity evidence drives each step. No parallel agents/worktrees are required or requested for implementation.

## Outside-review decision 1: one restricted profile-data reader

Approved: one maintained Lua tokenizer/parser defines and reads the supported managed-data format. GearSwap uses it directly; Nexus invokes the same module inside its existing isolated worker. Accepted input is the documented data grammar, not arbitrary Lua execution. Unsupported expressions produce location-aware diagnostics. Do not use include/loadstring to evaluate managed data and validate only after expressions have already executed. Maintain shared fixtures for in-game and worker invocation, including supported comments, references, removal marker, malformed input, bounds and source locations.

This is a reader, not a second general Lua evaluator and not a complete text-editing engine. Future Nexus text splices/round-trip preservation still require their own implementation and validation. Maintained job logic remains normal Lua; the restriction applies to managed player-data files. Update T1/T3 to specify/implement this single module and its worker boundary, avoiding independent Lua/Python interpretations.

Outside challenge completed through Claude Code, session 11434e85-5f0b-41a1-a2c0-35d641266b1c. Saved result: ~/.gstack/projects/Grimdarts-VanadielNexus/20261102-gearswap-eng-outside-review.md. The review supplied plan-only findings, not observed implementation failures.

## Outside-review decision 2: framework-aware failed-load cleanup

Approved: complete managed-data parsing, validation and resolution before entering Mote initialization. Record completed setup phases. A subsequent failure safely invokes applicable existing framework unload/cleanup and releases resources owned by this integration, including partial initialization. Do not assume Mote finished or that every cleanup hook is already defined. Use guarded, phase-aware, idempotent cleanup; do not blindly unbind controls owned by unrelated jobs/addons.

Required proof: inject failures before framework entry, during its globals/setup stages, during managed control attachment, and after ready publication; verify no duplicate callbacks, lingering owned bindings or stale managed ready state; retry and unload must remain safe. Existing framework cleanup behavior must be inspected and tested, not merely called by name. No manual-reload-only recovery shortcut was accepted. This specifies resource cleanup, not reversal of game actions already issued by arbitrary legacy setup code.

## Outside-review decision 3: migrated profile takes precedence

Approved: inventory overlapping legacy Mote globals, character globals and sidecars; transfer intended migrated values/bindings into the new profile. For defined migrated settings/hotkeys the new profile has final precedence. Preserve framework initialization and unrelated legacy behavior; do not change shared files used by unconverted jobs. Document overlaps and verify load order cannot reverse the profile's settings. T1/T2 capture sources and T4 tests actual effective values and key commands.

## Outside-review disposition and remaining gates

- Shared restricted reader: approved in D8; specified above.
- Framework-aware cleanup: approved in D9; specified above.
- Legacy configuration precedence: approved in D10; specified above.
- Existing automatic behavior: already covered by the approved baseline's discussion-before-change rule and T2's unresolved-parity gate. Inventory and classify actual behavior first, then present any conflict between preservation and optional automation before T4. No specific automatic behavior has been removed or approved by this review.
- Identity wait simplification: NOT adopted. Retain the approved bounded-wait behavior for genuinely temporary missing identity. Probe installed runtime and specify bounds/source; do not infer guaranteed readiness from the normal login path. A later request to eliminate the wait would be evaluated as a change.
- Binding wording: corrected to reflect the already-approved explicit association; only naming/syntax remains to specify.
- Nexus inherited/local wording: clarified to match already-approved stage boundaries: origin data now, editor presentation later.

## Completion summary

Step 0: approved stage-1 detailed scope, later product scope retained. Architecture: 5 issues addressed through approved remedies. Code quality: 1 issue addressed. Test review: coverage/flows diagram and failure matrix produced, 0 additional independent decisions; future implementation coverage is planned, not existing. Performance: 0 additional decision issues. Outside voice: completed through Claude Code; 3 approved follow-up remedies (cleanup and precedence came from one combined outside finding). NOT in scope, reuse and sequential execution documented. No new TODOS.md entries proposed; already deferred product work remains in the design. No known unhandled silent critical gap in the plan. Lake score: 1/1 explicit complete-versus-shortcut decision (failed-load cleanup); other choices differed in kind.

Implementation details deliberately assigned to T1/T2 are gated deliverables, not silent defaults. If either reveals a material new tradeoff or unsupported parity expectation, stop and discuss it before affected implementation. Public release/coordination readiness is not cleared by this review. No implementation code has changed; no future test or live readiness result is claimed as passed.

## T1/T2 execution progress, 2026-11-02

Jason approved this plan and work began with contract specification and read-only baseline capture. See [data contract](GEARSWAP-DATA-CONTRACT.md) and [baseline report](GEARSWAP-SMN-BASELINE.md). The new parser/loader has not been implemented.

Captured six contexts: SMN default/SCH/RDM/WHM, BLU/NIN, RUN/BLU; all loaded without sandbox errors or partial results. Snapshotted 35 dependencies privately; pre/post hashing covered 154 input files with no changes, and final readback of the 35 dependencies also matched. Captured 29 modes, 66 key positions, five spell-map contexts and five finite command-sequence contexts. Existing repository suite: 477 passed in 69.40s, no skips reported. This is existing-code/offline evidence, not live timing proof.

Separate SMN LagMode timing and state.lagmode display flags disagree and toggle independently; source inspection and sandbox command trace confirm this. Jason delegated the choice, and the selected remedy is one authoritative flag, initially true, used by both display and commands. A private candidate proves the flag behavior but exposes a pre-existing missing equipBPGear helper when the OFF pet-midcast path is exercised. This occurs in the original too. Do not activate a flag-only patch: include dependency repair/dispatch validation in T4/T5 before SMN activation. No new unattended action feature is implied. Live identity, physical LCD and equipment timing checks remain pending. No installation or active files changed.

## GSTACK REVIEW REPORT

| Review | Trigger | Scope | Status | Findings |
|---|---|---|---|---|
| Engineering | /plan-eng-review | Stage-1 architecture, quality, tests, performance | Review complete; plan approval pending | 5 architecture and 1 code-quality issue addressed; test and failure obligations documented |
| Outside voice | Claude Code, plan-review | Independent challenge of stage-1 plan | Completed | Shared reader, framework cleanup, and legacy precedence approved; other suggestions dispositioned above |
| Office Hours design | /office-hours | Full 22-job product baseline | Approved | Product scope retained |
| Visual design review | Not run in this stage | Future shaped overlay/LCD mockup | Deferred | Existing displays preserved during first-stage migration |

OUTSIDE COVERAGE: host=codex, provider=claude-code, phase=plan-review, outside_status=completed; session 11434e85-5f0b-41a1-a2c0-35d641266b1c; reported model claude-opus-5-5. This was a plan-only review with no implementation tests.

VERDICT: Stage-1 engineering review complete and plan approved by Jason on 2026-11-02. T1/T2 specification and parity evidence gates precede implementation dependent on them. Installed-file activation and publication remain separate actions.

NO UNRESOLVED DECISIONS

## Commit and manual-test checkpoint, 2026-11-02

Jason authorized committing the staged work and consolidating outstanding test
lists. Commit title: `GearSwap: stage managed bundles and consolidate tonight's tests`.
T3 is complete; T4 remains open at the documented native-host/live verification
gates. See [T4 validation](GEARSWAP-T4-VALIDATION.md) for pre-commit review repairs
and **659 passed, 0 skipped**. No push, release or activation was authorized by
this commit request. The post-commit automatic app build is bypassed for this
single commit because its Python changes are staged tools/tests, not app code.
The installed VN executable remains the existing Sets usability build.

[Tonight's checklist](TONIGHT-TEST-CHECKLIST-2026-11-02.md) combines the VN Sets,
guide/layout acceptance notes and newer FFXI-Graphics handoff, preserving already
reported PASS results and keeping uninstalled bundle tests gated.
