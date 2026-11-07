# Gear Guide T6 continuation handoff

Date: 2026-11-03. Checkout `codex/sets-copy-fixes-review`, HEAD `5657f20`.
Jason accepted the concrete T6 preview and asked to refine each section after
later committed/live app testing. Do not reopen accepted T1–T5 decisions or T6's
visual gate. T6 is implemented in source; human/frozen/live acceptance remains.
All T2–T6 changes are still uncommitted, with important new files untracked.

## Implemented source

- `core/equipment_analysis.py` adapts already resolved GearSwap declarations to
  T5's evaluator. Missing slots stay omitted; explicit empties and unresolved
  identities stay distinct. No implicit equipped/base set or alias double count.
  Name indexes deduplicate normalized short/long names before asserting a unique
  ID. Job eligibility uses retail job-bit order, not the app's display ordering.
- Snapshot normalization detaches exactly one matching non-imported character's
  observations, uses supplied resource bag mappings, checks bounded quantities,
  and retains observed rank/path as unsupported effects rather than magnitudes.
  Absent versus explicitly empty snapshots differ. Requirements remain separate
  from observations. Strict analysis matching does not borrow GearSwap's Rare
  shortcut; conservative mismatches remain uncalculated rather than certified.
- Strict allocator ambiguity now also covers multiple stored/unreachable
  candidates when no ready candidates exist. It never asserts an arbitrary
  stored copy as uniquely identified. One simultaneous allocation still applies.
- `ui/equipment_details.py` shares one lazy source service and bounded T5 result
  cache per context. Sets/Gear/Guides request preparation on relevant first use;
  explicit refresh can retry. Warm requests reuse indexes, and failures do not
  reparse on every hover. Root changes clear dependent source/results. Main-window
  shutdown closes/cancels the shared adapter; QObject destruction also cancels.
- SourceSnapshot now also holds an immutable normalized name index (mapping to
  ID tuples). It is built in the cancellable preparation worker before final
  source-signature validation. GUI publication does not scan all 15,527 items.
  Small explicitly injected test snapshots retain an optional-field fallback;
  no persistence or resource-file format changed.
- One scrollable nonmodal ItemCard per consumer supports 350 ms hover dwell,
  250 ms leave grace, Keep open, explicit details, refresh, Escape/Close and focus
  restoration. It fits within app/screen bounds. Base effects/full original text,
  declared requirements and observed data are separate. Generic Gear/Guide rows
  never bind to an arbitrary copy. Sets can inspect saved observations without
  replacing equipment or persisting a binding. Unsupported augments/ranks/paths
  stay uncalculated; master/Pet/Avatar recipients remain separate.
- `ui/equipment_analyzer.py` analyzes only existing read-only declarations in
  Owned mode. No snapshot means unavailable Owned contributions. A second
  existing declaration uses the same character/job/source/snapshot/scenario.
  Incompatible or absent result keys are unavailable, never implied zero.
  Signed known changes retain per-result uncertainty and partial-loadout labels.
- Unity has unknown/verified-first/verified-other offline scenario inputs shared
  by both selections and labeled manual assumptions. Unknown Unity ranges remain
  visible beside the subtotal. Inyanga membership/bonus derives once per loadout.
  No unsupported time/weather/buff/Fucho controls or character/effective caps.
- Contribution trails retain selected/baseline, slot state, omitted slots, unique
  saved bag/augment observations or explicit copy ambiguity, snapshot metadata,
  item/rule/evidence/resource provenance, conditions and uncalculated text.
- Sets keeps its tree/grid and existing attention/copy-fix workflow. Attention
  remains the default tab; Equipment analysis is adjacent below the grid.
  Grid Enter retains the established slot-panel action. New Item details, Alt+I
  and context actions provide keyboard-equivalent card access. Existing edit,
  activation, double-click and wiki actions remain intact in Gear and Guides.
- New analyzer widgets and the existing per-label style pass are deferred to
  first Sets use. Profiling identified the style pass as a material startup
  cost; the existing 50 ms construction requirement was retained, not widened.
- Only item IDs requested by either compared alternative enter physical-copy
  expansion. Unrelated material stacks are excluded from that allocator; a
  regression fixture includes a 9,999-unit unrelated stack. Generic/unknown item
  declarations remain inspectable during source failure without asserting copies.
- Selection/read/snapshot/source changes clear old cards/results. Source-worker
  publication remains on the GUI thread and inherits T5's generation/root guards.
  Expensive source preparation is shared and off-hover. No addon/game poll,
  equipment command, inventory move or Lua write was added.

## Validation

Final exact-source native full suite: **777 passed, 0 failed, 0 skipped in
148.55 s (2:28)**. The focused worker/index/card/analyzer/startup set passed
**47 tests in 1.14 s** immediately before the final full run. Earlier affected
Sets/equipment regression set: 89 passed in 13.81 s. `git diff --check` passed;
existing LF/CRLF notices are warnings only. No app/core/test/profiler source
changes followed the final full run; subsequent work updated this handoff and
removed task-created temporary fixtures.

Earlier intermediate full runs passed 776 tests in 108.90 s and 170.36 s, then
777 in 144.34 s before the final publication-performance correction. A separate
intermediate run had 775 passes and a single 50 ms construction-budget failure
(110 ms observed). Lazy analyzer construction and first-use style application
fixed that regression without relaxing the test. These intermediate numbers do
not substitute for the final 777-pass exact-source run above.

New core/Qt tests cover normalized-name uniqueness and actual job-bit order,
omitted/empty/unknown states, character isolation and absent/empty snapshots,
unknown bag mappings, stored duplicate ambiguity, distinct copy shortages,
comparison-key availability, same-scenario comparison, snapshot/source failure
clearing, character comparison reset, card content/Escape and unsupported rank.
T5's existing preparation/reentrant/stale-publication tests remain in the suite.
Prepared name indexes are checked for expected identity and immutability, and
the irrelevant-stack regression verifies bounded equipment-only expansion.
The context-menu regression now includes Item details and still checks wiki URLs.

Test execution uses isolated writable TEMP/TMP/VN_DATA_DIR, a fictional fallback
Windower containing an inert addon stub and disabled automatic addon snapshot
seeding. Existing read-only installed-GearSwap regression tests remain read-only.
No AppContext/Database/Settings test instance used actual player persistence.
Native permissions are required for Windows atomic replace/junction/UDP tests.
The existing Python interpreter is:
`C:/Users/Jason/AppData/Local/Python/pythoncore-3.14-64/python.exe`.

Reproducible task-local launcher (run from the repository root):
`C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a3bd-153e-7b42-9b45-cbd2d66f7702/t6-isolated-checks.py`.
Set TEMP/TMP to a new writable isolated directory, VN_DATA_DIR to its fictional
child, then pass `-q -rs --basetemp=<new isolated pytest directory>` to the launcher.
For example, from this checkout:

```powershell
$testRoot = Join-Path (Get-Location) ('.isolated-tests-' + [guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $testRoot | Out-Null
$env:TEMP = $testRoot
$env:TMP = $testRoot
$env:VN_DATA_DIR = Join-Path $testRoot 'fictional-data'
& 'C:/Users/Jason/AppData/Local/Python/pythoncore-3.14-64/python.exe' `
  'C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a3bd-153e-7b42-9b45-cbd2d66f7702/t6-isolated-checks.py' `
  -q -rs --basetemp (Join-Path $testRoot 'pytest')
```

The launcher separately creates `.t6-checks/fictional-windower` under the current
checkout for its inert fallback; remove only the verified task-created scratch
paths after tests exit. The final run's `.t6-checks` tree was removed after all
test/probe processes exited; the reusable launcher remains in the visualization
directory outside that scratch tree.
It must be a real file: running pytest through stdin breaks Windows spawned
workers because `<stdin>` cannot be reloaded. An initial interrupted full attempt
and a diagnostic run (193 passed, one worker timeout) established that launcher
problem. The first sandbox focused run was 116 passed, four failed, one skipped:
two collection-shape integration failures were fixed, the context-menu assertion
was updated for the new control, and native isolated execution resolved a Windows
atomic-replace permission failure. These are historical diagnostics, not current
unresolved product failures.

The browser tool blocked the HTML mockup's file URL. No workaround was attempted.
Later Qt source rendering is independent of that browser preview: actual widgets
are rendered offscreen by the script below, without launching the installed app.
The script explicitly registers installed Segoe UI for readable offscreen renders.

## Source UI performance and renders

`tools/profile_equipment_ui.py WINDOWER_ROOT OUTPUT_DIRECTORY` constructs the
actual source SetsPage using an in-memory QObject context, fictional character
and snapshot, and local read-only resource files. It never creates AppContext,
Database, Settings, a bridge connection, or a Lua reader task. The existing
`tools/screenshot_pages.py` is not used because it copies repository player data.

Artifact directory:
`C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a3bd-153e-7b42-9b45-cbd2d66f7702/t6-source-ui/`.
It contains `equipment-ui-profile.json` and analyzer/card PNGs at 900×600,
1024×768 and 900×600 with 130% text scale. Analysis content uses the existing
scroll area, with its own scrollable contribution table; long card content also
scrolls. Screenshots demonstrate source rendering, not a human interaction pass
or the complete sidebar/app shell. The 130% narrow view is intentionally compact
and remains subject to Jason's requested live-layout refinement.

Fixture: fictional WHM, five Inyanga +2 pieces, Loricate +1, two distinct Stikini
+1 observations in one bag, eight intentional empty slots; baseline omits feet.
Known Refresh is 6 MP per three-second tick, incomplete. All descriptions/items
are read from the exact T1/T5 source fingerprint
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.
The probe uses 200 warm card publications and 200 whole-analyzer recalculations
with cache misses, plus ten settled RSS batches. Timings exclude hover dwell and
include Qt publication/processEvents. Baseline already contains the same page
and existing item_res caches. This is one supported fixture, not a full workload.

Final uninstrumented source-page probe after the publication fix:

| Measurement | Observed / accepted target |
|---|---|
| Worker preparation and first publication | 0.7089 s / 3 s |
| Maximum GUI event-loop gap | 23.96 ms over 77 samples / 100 ms |
| Warm card presentation | 1.767 ms p95, 200 samples / 100 ms after dwell |
| Whole analyzer recalculation, cache misses | 4.141 ms p95, 200 samples / 50 ms |
| Sampled preparation RSS increase | 24.73 MiB / 96 MiB |
| Ten settled RSS batches | 8.16 MiB in every batch / 64 MiB |

These meet the numeric targets on this fixture/run. A prior exact-source probe
observed a 303.74 ms cold event-loop gap and is retained as
`equipment-ui-profile-cold-gap.json`. A separate instrumented diagnostic
(`../t6-cold-diagnostic/cold.pstats` in the visualization directory) traced the
GUI publication cost to name_index (200 ms under profiling). Moving that index
into the existing worker produced the measurements above; the target was not
widened. Instrumented diagnostic timings are not acceptance measurements.

## Remaining acceptance and next work

- Human walkthrough: hover-to-card movement, Keep open, Escape/focus restoration,
  table/keyboard equivalence, screen edges, two copies with different augments/
  ranks/bags, source refresh/failure, rapid context changes and both-sided Unity
  changes. Review final layout in the later authorized installed app as requested.
- Broader same-page/full-app memory and all-rule/large-inventory workloads;
  full-shell 900×600/130% behavior. The small source fixture does not certify these.
- Frozen executable size/startup checks and in-game coexistence remain T9. No
  frozen-size or live responsiveness claim is made. No build/install was run.
- T7 production v2 22-job catalog and hand-type evidence integration remain.
  Unresolved main/sub legality can suppress analysis with diagnostics; T6 does
  not infer hand types or weaken the accepted fail-closed rule. Production catalog
  remains v1, with no real legacy conversion or Wishlist dual-write.
- T8 replacement editing, Owned/Planning drafts, persistence/drift reconciliation
  and safe Lua output remain separate. No builder has been delivered by T6.

Preserve every existing tracked/untracked change, planning document and
`.codex-remote-attachments`. Windower/player Lua remain read-only. No real-data
migration, commit, push, build, executable replacement, installation, release or
staged GearSwap activation was performed. The installed post-commit hook can
rebuild/replace/relaunch Nexus; future commit/build/install steps must respect
the already documented separate gates and exact-artifact validation policy.
