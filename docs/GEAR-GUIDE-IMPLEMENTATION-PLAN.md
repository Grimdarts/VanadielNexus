# Implementation plan: verified guides, item cards, calculator and builder

Date: 2026-11-03. Branch: `codex/sets-copy-fixes-review`.
Base commit: `5657f2092c0e0d84331d0741b1518669201e25d4`.
Continuation disposition: Jason approved the concrete T4 mockup as a starting
point and requested as much implementation progress as practical tonight.
T4 Guide integration and T5's bounded core/worker are implemented in source;
see [T4–T5 handoff](GEAR-GUIDE-T4-T5-HANDOFF.md). Jason subsequently approved
the concrete T6 preview and requested refinements after future live testing.
T6's shared cards and existing-set analyzer are implemented in source; see
[T6 handoff](GEAR-GUIDE-T6-HANDOFF.md) for validation and remaining acceptance.
The existing commit, build,
installation, release, migration and Lua-activation boundaries still apply.
The historical approval wording below does not reopen accepted specification
or visual decisions. The T6 concrete mockup gate is now satisfied.
Status: APPROVED by the user on 2026-11-03 after interactive engineering review and two Claude document-only challenge passes. The proposed numerical budgets and staged plan are accepted. T1 read-only research, evidence/coverage matrices and concrete compatibility specifications are authorized to begin. App-code implementation, real-data migration, commit, build/install, push, release and Lua activation are not authorized by this approval; the named evidence/visual gates remain.

Design baselines: [guide catalog](designs/verified-gear-guide-catalog.md) and [item cards/calculator/builder](designs/item-details-calculator-builder.md), both approved by the user on 2026-11-03. Detailed decision evidence and test diagram: [engineering review](GEAR-GUIDE-CATALOG-ENG-REVIEW.md).

T1's [consolidated review packet](GEAR-GUIDE-T1-REVIEW.md) was accepted by the user on 2026-11-03, with explicit authorization to start T2–T3 core implementation in a new session. Supporting artifacts: [source/job coverage](GEAR-GUIDE-T1-COVERAGE.md), [stat-rule evidence and expected cases](GEAR-GUIDE-T1-STAT-RULES.md) and [proposed data/compatibility contracts](GEAR-GUIDE-T1-CONTRACTS.md). All other named gates remain. These specifications do not certify the full catalog or constitute implemented/tested rules.

## Scope and delivery

Refresh eight existing jobs and add fourteen jobs using verified public evidence, useful relevant priorities, concrete equipment versions, explicit older/budget labels and attributed Nexus recommendations. Keep the Purpose -> Set -> Version workflow. Required job-priority/N/A matrix gets one consolidated user review; a finished audit with gaps is not a completed all-job catalog.

In the feature track, first deliver styled item cards and equipment/conditional analysis of existing read-only sets; compare two existing selections under one scenario. Later deliver owned/planning set construction, substitutions and saved drafts. Keep player Lua/Windower read-only throughout. Earlier design approval is not installation permission.

## What already exists

| Existing component | Reuse and boundary |
|---|---|
| `resources/gear_guides.json`, `core/gear_guides.py` | One catalog, grouping, target checks and explicit tracking; extend, do not build a parallel guide service. |
| `ui/pages/guides.py`, `ui/item_links.py` | Existing picker, source controls and separate item-wiki navigation. |
| `core/item_res.py`, local Windower resources | Non-executing resource reads, item/job/slot/bag identity and source caching. Description text is an input, not proven numeric effects. |
| `core/set_manager.py` | Bag-aware distinct-copy allocation and GearSwap selector behavior; extract reusable pure primitives while preserving policy distinctions. |
| `core/gearswap_reader.py`, `ui/equip_grid.py`, Sets page | Read-only resolved sets and existing slot display. Do not sum aliases or treat omitted slots as proven empty. |
| `core/database.py`, `core/jsonfile.py`, settings | Existing target snapshots and atomic JSON/backup patterns; extend only with reviewed compatibility and write-failure behavior. |
| pytest/pytest-qt, `tools/check_frozen.py` | Core/UI/integration and actual frozen-artifact checks. No new feature tests have run. |

## Decisions already resolved

1. Stable conceptual set IDs with immutable revisions; saved targets do not follow the latest recommendation automatically.
2. Explicit slot targets with personal designated bags for duplicates; one observed physical copy cannot serve two simultaneous slots. Bag placement is not universal guide data.
3. Validate the whole proposed catalog before delivery; reject malformed updates. Runtime corruption yields a clear Guide-page failure without crashing other pages or modifying saved targets. Inaccessible research is not malformed data to silently repair: keep it in the private gap report.
4. Verified reusable description rules plus targeted, sourced exceptions; unknown/ambiguous effects stay uncalculated with per-result completeness.
5. Selected-entry/revision source actions; direct for one reference, contextual chooser for several; retain truthful Nexus authorship.
6. Neutral pure matching/allocation core; GearSwap selectability, strict target completion and effect calculation are separate policies.
7. User delegated cache decision: choose an in-memory prepared index and bounded result caches; no persistent item/stat index initially.
8. Outside-review persistence decision: use a separate, small versioned personal-workspace file for new drafts and revision/slot/bag-bound targets; no authoritative dual-write into legacy mutable target records.
9. Outside-review export decision: pin syntax validation to LuaJIT/Lua 5.1-compatible semantics, then round-trip generated active output through the existing read-only reader and shared selector policy using temporary fixtures. Compare intended slots, augments and designated bags; reject unresolved/ambiguous selections rather than claiming exact-copy equivalence.

## Concrete data contracts to implement

### Catalog and saved targets

Advance the bundled catalog to a versioned supported schema. A canonical revision record identifies its conceptual set, immutable revision, job applicability, purpose/context, equipment version, origin, verification/currency and source references. Give each occupied slot exactly one concrete item requirement, including item ID, augment/rank/path/quantity where applicable. Contextual variants are separate Set groups, not automatically ordered as progression tiers. Exact field spelling can follow existing conventions without changing these identities.

Validate source kinds/URLs, revision uniqueness, conceptual/reference integrity, slot alias collisions, requirements and evidence completeness before publishing a candidate. Keep previous prepared artifacts untouched if preparation fails. Do not remove historical reference information just to satisfy a validator.

Saved personal bindings refer to character + conceptual set + revision + slot. They retain target snapshots and personal overrides separately from curated requirements, including designated bags. Existing unversioned references are preserved. Associate them with an exact historic revision only when existing snapshot/source evidence establishes it; otherwise retain the old data and show an unresolved reference. Do not guess slots for legacy ring/ear eligibility lists. A catalog-version change must not silently apply one old item override to both paired slots.

Viewing or loading cannot migrate/rewrite targets. Explicit adoption presents a reviewable change and updates only selected references after a successful persistent write. Drafts and targets must remain unchanged in memory as well as on disk if saving fails. User data migrations, if necessary, require their separate reviewed backup/preservation plan before running against real data.

New authoritative targets and drafts live in a separate versioned workspace file under the existing per-user data-root policy. Validate its version/shape; write atomically with backups and recoverable diagnostics. Older app versions do not display it, but their legacy writes must leave it intact. Do not mirror new authoritative records into legacy target shapes. Join proven associations only for truthful display; retain unresolved/conflicting versions rather than guessing or silently merging them.

Explicit adoption/import copies a reviewed legacy snapshot without silently removing or changing the original. Conversion of existing records counts as migration and needs its separately reviewed preservation/backup authorization. Empty workspaces and explicitly saved new drafts are ordinary feature persistence, not migration permission. Test an old-app legacy save/edit/recovery round trip with the separate workspace byte-for-byte intact, followed by new-app reopening. This is personal saved data, not an item/stat cache.

### Shared effects and results

Keep raw source/observations immutable. A normalized effect has a stable stat key, recipient, unit, operation, applicable condition, rule/exception identity and source provenance. Preserve unsupported text and uncertainty. Matching normalization that discards synthetic Rank text must not erase the raw rank observation or turn it into a real augment.

Explicitly classify item-scoped versus loadout/multi-item effects. Supported set bonuses evaluate qualifying distinct selected pieces once at loadout scope using the rule's actual counting/stacking semantics; do not attach and sum the same bonus on every piece. Unresolved set-bonus conditions or applicability affect the relevant loadout results' completeness, not just the text of one item.

Build a supported-rule matrix before numeric implementation. Each rule has independent evidence, recognized wording/context, units/rounding, condition/stacking semantics, source/version applicability and independently derived test results. Prioritize representative core/defensive/Refresh, physical, casting and pet examples to prove the model; do not label that sample complete stat coverage. Unknown rules are blocked from exact/cap claims, not force-coerced to zero. Do not infer effect magnitudes from a displayed rank alone.

Results distinguish known contributions, supported conditional evaluation and unresolved effects. Track completeness for affected results; unknown unscoped effects require conservative uncertainty rather than an unjustified precise total. Master/pet and incompatible stacking categories stay separate. A buff toggle enables a supported conditional equipment effect, not a full buff/trait simulation.

Compose explicit slots with verified replacement precedence. Preserve omitted, intentional-empty, unknown and selected states; show a partial-set contribution when full loadout context is absent. Compare the same scenario and comparable stat meanings. A larger number is not automatically an upgrade.

### Drafts and output

Default to owned gear; Planning explicitly permits verified legal targets and assumed augments without presenting them as observed or equip-ready. Enforce slot/job and supported cross-slot restrictions; retain ambiguity when legality is unresolved. Quantity checks allocate distinct copies across the set.

Save independent character-bound Nexus drafts with chosen guide revision and observed copy/snapshot details. On reopen/refresh, flag moved/missing/changed/ambiguous copies against the latest appropriate snapshot; never silently rebind or adopt new augments. An unavailable/stale snapshot cannot establish current ownership. Explicit rebinding or conversion to Planning is the player's choice.

Normal active Lua output requires resolved, supported legal selections and sufficiently confirmed bindings. Hypothetical Planning output is a separate, fully commented scaffold; unknown augments/ranks never become active equipment assertions. Validate output syntax and structure offline. No writes to player Lua, equipment commands or inventory moves.

Export verification uses the existing `lupa.luajit21` runtime and records the runtime identity/version. Load generated active output inside a temporary GearSwap entry fixture using the existing bounded read-only reader, then apply the shared selector policy. Independently expected slot/name/augment/bag values must agree with the builder selection. Never use an unstable inventory index as proof of a unique copy; ambiguous indistinguishable copies remain unresolved under the existing identity policy. Cover quoting/control-character escaping, paired slots, augment formatting, bags, empty/omitted slots and rejected output. Planning scaffolds receive the compatible-runtime syntax check plus an assertion that no active equipment assignments or commands were emitted. Passing these offline checks does not prove live timing or activation parity.

## In-memory preparation and performance

```text
first relevant page use / explicit source refresh
  -> one coalesced background preparation request (bounded input/work)
  -> read local sources as data -> English/item index -> discard unused parsed rows
  -> publish only if source/root generation still matches
       -> item card lookup
       -> bounded normalized-effect/result cache
            keys include source/rule version + exact augments + selection/conditions
            -> selected-set evaluation -> main-thread UI publication if still current

source/rule/character/selection change
  -> invalidate dependent results / discard stale completions
failure -> clear loading state + truthful unavailable/partial details, no saved-data mutation
```

Use a Qt worker/thread pattern consistent with existing code for bounded resource preparation; no arbitrary Lua execution or new external service. Keep Qt widgets on the GUI thread. Do not run preparation on every hover; do not add polling/watchers or game-side requests. Dispose/cancel pending work on page/app shutdown and reject late completions using generation/request identity. Cache eviction can require recomputation, never change results or cause target adoption.

One existing-parser probe read 4,972,281 source bytes/23,456 rows in 0.7644 seconds with `tracemalloc`, retaining 13.90 MiB before a separate English index; 10,000 lookups took 0.0029 seconds. This is instrumented local input preparation, not feature latency or cold-disk/RSS evidence.

Proposed engineering acceptance targets, not measured results, for final plan acceptance and implementation on this reference machine:

- First-use preparation finishes within 3 seconds on the recorded resource size, outside the interaction path; the UI remains usable and shows loading details meanwhile.
- Warm card presentation within 100 ms of the configured hover dwell expiring; warm 16-slot recalculation within 50 ms at p95 for the declared supported-rule fixture. Record timing methodology and sample size.
- During first-use preparation, target no observed GUI event-loop gap over 100 ms on the reference fixture. Measure actual event-loop responsiveness; moving Python work to a thread is not itself proof that the GIL cannot stall the UI. A failing preparation strategy must be corrected within the bounded off-hover design or returned for review.
- Incremental feature memory settles within 64 MiB of the same-page baseline after warm-up, with no upward trend over repeated hover/set changes; transient preparation stays within 96 MiB of baseline. Bound cache entries and retained bytes; measure whole-process memory as well as traced Python allocations.
- Calculator/card-specific frozen size increase stays within 2 MiB against a build with the same catalog/resources. Measure the 22-job catalog size separately; don't attribute catalog content growth to the calculator. No new runtime dependency or bundled image/item database by default.
- Zero additional addon/game polls or scan requests from card/calculator/builder actions. A home-session coexistence check remains required; do not promise zero game impact from app-only measurements.

If a target fails, diagnose and improve the bounded implementation; do not silently widen budgets or add persistent caching. A genuinely necessary scope/budget change returns for review. Numeric rule coverage is not cut to meet a timing target without an explicit support-boundary decision.

## Test map and realistic failures

The detailed ASCII coverage diagram is in the engineering review. These are implementation requirements, not test-pass claims:

| Path / failure | Required verification and user-visible behavior |
|---|---|
| Catalog parse/schema/reference failure | Candidate rejected with file/entry diagnostics, previous artifact intact; runtime Guide error, other pages usable; no user-data writes. |
| Old/changed/retired revision or ambiguous legacy slot | Preservation/adoption tests across temporary DB/settings; unresolved target remains inspectable and unchanged. |
| Duplicate item, wrong bag, unknown rank/path or other character | Allocation and policy tests; no false completion, reused copy or silent rebinding. Preserve existing selector compatibility tests. |
| Source menu becomes stale or URL unavailable | Qt integration: correct selected-revision reference or explicit unavailable state; no wrong-set navigation. |
| Unsupported text/exception mismatch/unknown condition | Independent numeric/text fixtures; visible uncertainty, no unjustified exact cap or upgrade claim. |
| Partial set/aliases/overlay collision | Independent slot-composition expectations; no double counting or invented empty slots. |
| Worker failure/source changes/rapid selection/shutdown | Delayed/out-of-order Qt tests; no stale UI publication, stuck loading state, leaked work or widget access off GUI thread. |
| Cache eviction/invalidated rule or source | Recomputed results equivalent under same inputs; memory bounded; no target mutation. |
| Draft save fails/corrupt reference/inventory drifts | Temporary persistence integration, old data and in-memory state preserved; actionable diagnostic and explicit recovery choices. |
| Planned or illegal active export | Block normal output; commented scaffold remains hypothetical; syntax/structure validation does not claim live parity. |
| Frozen resource/import/worker failure | Validate exact staged executable before authorized installation, then hash/read back and recheck the installed artifact. |

Existing tests provide partial baseline coverage for tracking, matching and UI selection. Extend them and add focused effect/condition and draft suites. Use pytest/pytest-qt, fictional fixtures and read-only real-resource probes. No real player data migration as a test. Full `py -3 -m pytest -q -rs` with exact pass/skip counts remains mandatory during implementation.

## Implementation Tasks

Tasks derive from the approved decisions and failure map. Effort estimates are deferred until T1 establishes source/rule coverage; no calendar promise is made for research across 22 jobs.

- [x] **T1 (P1) — Contracts and coverage evidence.** Specify schema/compatibility fixtures, the consolidated job-priority/N/A matrix, supported-stat/rule matrix and public evidence ledger. User reviews job exceptions; unsupported stat effects remain explicit. Files: review/spec artifacts and fictional fixtures; personal Lua mappings/private research stay in the private project store. Verify against actual resource/source interfaces before any numeric rule is treated as supported. Accepted for specification purposes on 2026-11-03; not full-catalog or numeric implementation certification.
- [x] **T2 (P1) — Neutral matching core.** Extract approved pure primitives and preserve existing callers; keep strict guide requirements separate from GearSwap selectability. Files: core matching helper, `set_manager.py`, `gear_guides.py`, relevant core tests. Verify both import orders, original selector tests, paired slots/bags/characters and strict rank/path cases. Implemented and offline-tested on 2026-11-03; see [T2–T3 handoff](GEAR-GUIDE-T2-T3-HANDOFF.md).
- [x] **T3 (P1) — Catalog validator, revision compatibility and isolated workspace.** Implement complete candidate validation, immutable revisions, non-mutating legacy normalization and separate versioned target-workspace persistence. Files: `gear_guides.py`, focused catalog/workspace core, existing per-user path/JSON helpers, core tests. Verify failed preparation, historical snapshots, unknown references, old-app writes/recovery leaving workspace intact, failed workspace writes and no implicit adoption. Do not run real-data conversion without its migration gate. Implemented and offline-tested on 2026-11-03: final full suite 709 passed, 0 skipped; production v2 authoring/UI integration remain later tasks.
- [x] **T4 (P1) — Guide UI and source integration.** Approved mockup implemented with saved snapshots, strict slot/copy/bag comparison, scoped sources, personal overrides, explicit adoption and recoverable failures. Legacy usage preserved. See T4–T5 handoff for validation and production-catalog boundaries.
- [x] **T5 (P1) — Shared source/effect model and bounded preparation.** Accepted bounded contribution rules, immutable source preparation, per-result uncertainty, bounded result cache and generation-safe Qt adapter implemented and tested. Standalone resource/worker probe records latency, event-loop gaps and process memory; full-page/card/frozen/live acceptance remains T6/T9. No persistent index or game polling.
- [ ] **T6 (P1) — Existing-set cards and analyzer.** Approved direction implemented in source: shared item cards in Sets/Gear/Guides, Owned read-only declarations, Unity scenarios, derived Inyanga effects, same-scenario comparison, copy/source/rule provenance and uncertainty. Core/Qt regression tests and a source Sets-page performance/render probe are recorded in the T6 handoff. Final human keyboard/hover/layout acceptance, broader workload/full-app measurements and separately authorized frozen/live checks remain; this checkbox does not certify them. No draft editing, full-stat coverage, or live readiness claim.
- [ ] **T7 (P1) — Verified all-job catalog.** [WHM authoring](GEAR-GUIDE-T7-WHM.md) preserves 23 verified Nexus compositions; [SCH authoring](GEAR-GUIDE-T7-SCH.md) adds 28 across explicit support/casting and niche staff contexts. Candidate: 59 sets/revisions (51 verified + 8 preserved unresolved), 57 sources, 867 selected slots + 51 intentional empty range states; 210 coverage records (10 WHM + 16 SCH included / 184 gaps for the remaining 20 jobs). Hand evidence remains 15 exact IDs. See [current handoff](GEAR-GUIDE-T7-HANDOFF.md) for 822-pass validation and source/currency limits. Production remains v1. No all-job, every-tier, full-effect, ownership or live-readiness claim. Jason instructed stopping after SCH for the night; do not start another job or T8/T9 in this continuation.
- [ ] **T8 (P1) — Owned/planning drafts and output.** Add builder selection, substitution deltas, reversible per-draft conditions, independent persistence, drift handling and safe copyable output. Files: draft core/persistence, builder UI integrated into relevant set workflow, tests. Depends on proven T2/T3/T5/T6 behavior and approved builder mockup. Verify failure atomicity, missing/illegal/ambiguous pieces, snapshots, compatible-runtime syntax and existing-reader/selector round trips of active output. Verify the planning scaffold is fully commented with no active commands/assignments. No live Lua writes.
- [ ] **T9 (P1) — Full verification and reviewable artifacts.** Run focused/full tests and performance/size measurements, refresh source/coverage reports, perform source/outside review, then stage and check the exact executable. Install/commit/push/release only with their applicable separate authorization. Home-session visual/game coexistence and any future Lua parity remain distinct evidence.

The full project necessarily spans multiple core/UI/test files; the accepted staged deliveries are the scope-control mechanism. Keep the first usable analyzer separate from builder editing rather than adding services to force a big-bang implementation. No task is automatically marked complete from this plan.

## Execution dependencies and parallelization

T1 -> T2/T3 -> T4; T1/T2 -> T5 -> T6 -> T8; T3 -> T8; T1/T3 -> T7; relevant completed deliveries -> T9. Guide research may progress job by job; using a target as authoritative requires its verified revision. Do not wait for all 22 jobs to plan one verified job's later Lua work, and do not call the overall catalog complete early.

Implementation is sequential in the existing checkout by default. Core/UI/fixtures overlap heavily. After T1's contracts stabilize, public-source research/private evidence can proceed independently of core implementation, but catalog changes merge sequentially through validation. No new worktree, subagent implementation or parallel file mutation is authorized by this document. Independent reviewers are read-only.

## NOT in scope

- Full effective-character, buff/food/trait or damage simulation; this phase is equipment contributions plus supported conditions.
- Exhaustive automatic set optimization; manual selection and bounded comparisons come first.
- Live Lua writes, profile activation, equipment commands or inventory movement; drafts and copyable output only.
- Persistent stat databases, new external services, a shipped image pack, extra polling or background watchers; no measured need.
- Broad app redesign; source labels/cards/analyzer/builder get specific mockup review within the existing visual system.
- Automatic publication, hook-driven unvalidated installs or new distribution infrastructure; retain existing separate gates.

Before any authorized Python/spec commit, account for the hook that can rebuild/replace/relaunch Nexus. Use a scoped one-command bypass where necessary; no persistent hook changes. The validated staged executable must be the exact installed artifact, checked again afterward. A hook that silently rebuilds another executable cannot substitute for this boundary.

Concrete mechanism for the already-approved per-command bypass: after separate commit authorization, use `git -c core.hooksPath=<verified-empty-temporary-directory> commit ...`, with a freshly verified absolute empty directory and actual arguments prepared for that commit. Do not use `--no-verify` as a post-commit bypass. Read back the installed executable hash and confirm no new build process/log activity started from that commit; account for any already-running build before beginning. Keep persistent `core.hooksPath` and hook files unchanged. Then perform only a separately authorized controlled stage/validate/install operation. [Git's hook documentation](https://git-scm.com/docs/githooks) and [core.hooksPath documentation](https://git-scm.com/docs/git-config#Documentation/git-config.txt-corehooksPath) support the mechanism. This names the existing safeguard; it is not authorization to commit or disable hooks now.

The empty hooks directory suppresses every Git hook for that invocation. Inspect the configured hooks directory immediately before any future bypassed commit and manually run applicable non-build checks under the same authorization; do not assume today's hook inventory remains unchanged. No hook or commit was run during this plan review.

Artifact preservation means failed build-time candidate generation leaves earlier prepared artifacts intact. An installed executable's bundled resource is not a separate last-good runtime cache: corrupt/unsupported resources yield the approved Guide-page diagnostic. Recovery through an executable rollback remains a separate user-authorized action, not an automatic resource substitution.

## Remaining gates and open status

No unanswered user decision from the initial seven choices and two substantive outside follow-ups is being defaulted. The hook follow-up names the mechanism of the existing accepted per-command bypass without changing its policy. Final engineering-plan and proposed numerical-budget acceptance were given on 2026-11-03. T1 research/specification work is beginning. Remaining gates are T1's reviewed contracts/rule evidence/job matrix, relevant visual mockups, any real-data migration permission and app-code implementation authorization. These are named dependencies, not claims that source verification or visuals are done.

No new unrelated TODO is proposed; all identified work belongs to T1–T9 or the explicitly deferred design scope. No `TODOS.md` is created. JSONL task aggregation requires jq; it was not available in the current command inventory, so the structured task artifact is skipped rather than hand-written. The Markdown task list remains usable.

## GSTACK REVIEW REPORT

| Review section | Outcome |
|---|---|
| Scope | Approved catalog and feature designs retained; staged existing-set analysis before builder; no unrelated scope added |
| Architecture | Five initial findings resolved through individual decisions |
| Code quality | One finding resolved: neutral shared primitives, explicit policies |
| Tests | Execution diagram and eleven failure/test groups mapped; future coverage requirements, not new test-pass evidence |
| Performance | One finding resolved under user delegation; in-memory strategy, parser probe and proposed measurable budgets recorded |
| Outside challenge | Two Claude document-only passes, reported model `claude-opus-5-5`; three initial follow-ups resolved |
| Existing code / NOT in scope | Written above |
| Failure handling | Every mapped new path has planned handling and tests; no known silent critical gap left unassigned |
| Execution | Sequential implementation by default; independent research can follow stabilized contracts; no worktrees/implementation agents launched |
| Additional TODO proposals | Zero; all identified work is T1–T9 or explicitly out of scope |
| Lake score | N/A: decisions compared implementation kinds, not accepted coverage shortcuts |
| Unresolved review choices | Zero; plan accepted 2026-11-03; explicitly listed execution/evidence/visual gates remain |

Initial outside session: `8231b0ff-00af-4d47-b96b-32a90d532494`. Recheck session: `9fc763c1-b515-4e64-8eae-419634f3959e`, verdict **Ready for final plan acceptance**. Three minor edits requested by the recheck (T3-to-T8 dependency, all-hook bypass implications, and stale status text) were applied afterward by primary review without a third external pass. Full responses and metadata remain in private local review artifacts. Prior design reviews do not substitute for this engineering challenge. The challenge did not inspect code or verify stats/performance.

Current-code calibration: Settings and database persistence retain many unknown fields, so generic claims that an older build necessarily drops every new field are unproven. However, the existing augment editor mutates tracked `guideTarget` requirements based only on job/set/item (`guides.py:238-242`); the user approved isolating new authoritative records in a separate workspace. The worker already imports `lupa.luajit21` (`gs_worker.py:116,147`); the user approved explicitly pinned syntax and reader/selector round-trip checks, not a claim that the worker uses Lua 5.4. The installed hook path is `tools/hooks` and demonstrably starts `build.ps1` for Python/spec commits; the accepted per-command override now has a named mechanism. No code, source/stat or performance correctness is inferred from these planning amendments.
