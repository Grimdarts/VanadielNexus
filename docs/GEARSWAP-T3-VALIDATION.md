# GearSwap bundle T3 validation

Date: 2026-11-02. Branch: `codex/sets-copy-fixes-review`.
Base commit: `6397caf`. Source work is captured by the commit titled
`GearSwap: stage managed bundles and consolidate tonight's tests` (find its exact
hash with `git log --oneline -- docs/TONIGHT-TEST-CHECKLIST-2026-11-02.md`). No push,
release, installed-file activation, or executable replacement was performed.

T3 is complete as a staged pure-data component. See the
[approved plan](GEARSWAP-BUNDLES-ENG-REVIEW.md),
[contract](GEARSWAP-DATA-CONTRACT.md) and
[host API and boundary notes](../staging/gearswap/README.md).

Pre-commit review follow-up: the reader/resolver now has **110 focused tests**,
including slot-alias/case collision and materialization-budget regressions. Final
full suite: **659 passed, 0 skipped**. Original T3 run results below are historical;
the current review and integration results are in the T4 validation report.

## Delivered

- One maintained Lua 5.1 module in
  `staging/gearswap/PlayerSystem/core/managed_data.lua`. It reads supported
  profile literals without executing them and retains original source, key/value
  spans, UTF-8 columns and table shapes for future edit planning.
- Defensive file size, nesting, value, record and reference limits; rejection of
  unsupported expressions, duplicate keys/slot aliases, invalid UTF-8, schema,
  fields, types, references, arrays and conflicting runtime destinations.
- Catalog validation, ordered/forward inheritance, whole-slot replacement,
  empty sentinel versus inherited omission, per-use bag/priority overrides,
  source/identity provenance and independent item/augment copies.
- Canonical-path mounting followed by aliases, including the SMN-style
  `engaged.Perp` self-alias. Cycle-safe working copies and canonical-only worker
  serialization avoid traversing runtime graphs as trees.
- Schema-driven settings merge, atomic list replacement, explicit optional
  removal, command-registry validation and normalized keyboard chord validation.
  No bindings or gameplay commands are installed or issued by these components.
- Required-file preparation returns one complete candidate or raises a named
  error. A staged Python harness calls the same Lua module under the existing
  Nexus worker conventions; it is not connected to production routing.
- Fictional profile examples, using SMN reference paths and the already-resolved
  `lag_compensation = true` preference. These are not Jason's converted gear or a
  replacement SMN job.

## Verification

`py -3 -m pytest -q -rs tests/core/test_managed_gearswap.py`:
**102 passed, 0 skipped**. Coverage includes direct LuaJIT and a real spawned
Python consumer, grammar/source locations, invalid data and resource bounds,
inheritance/cycles, aliases and mount collisions, omission/empty handling,
provenance, exact augmented identities, copy isolation, settings/hotkeys,
resource-validation callback, instruction budget and atomic failure.

`py -3 -m pytest -q -rs`: **579 passed, 0 skipped in 69.10 seconds**. This includes
all existing 477 tests plus 102 staged component tests. Tests use in-memory data and fictional equipment;
personal equipment was not added to repository fixtures.

Read-only SHA-256 comparison against T2's private source manifest:
**35 dependencies checked; 0 changed**. No Windower write operation was used.
Slot aliases were checked directly against installed GearSwap `statics.lua`;
the parser does not execute that file.

## Integration boundaries and next work

T4 must supply the actual SMN schemas/command registry and resource callback;
validate explicit profile binding and safe file access; probe live server ID;
implement bounded readiness, framework-aware failure cleanup and final profile
precedence. The diagnostic `profile` label in the pure reader is not a verified
identity or a file-access capability. Unselected job settings receive structural
validation; a later all-job editor must provide those jobs' schemas.

Production Nexus discovery, worker routing, dependency caching and UI remain
unchanged. The staged consumer demonstrates the shared-reader boundary; it does
not claim managed jobs are already discoverable in the installed executable.
No text-edit/save engine or arbitrary-Lua write support was introduced.

T4/T5 must repair and validate the pre-existing missing `equipBPGear`/pact dispatch
path while integrating the authoritative lag preference. The flag-only private
candidate remains unsuitable for activation. Personal SMN conversion, zero
unexplained set/action parity differences, actual equipment timing, reload/job
change/unload checks and activation authorization remain outstanding.

No new feature request was added to scope. The pure parser's source indexing and
cycle-safe copying were implementation details within the approved bounds and
legacy-alias obligations. No planning decisions were reopened.

Resume with: Read the approved design, engineering review, data contract, SMN
baseline and this validation report. T3 is staged and tested; continue T4's SMN
lifecycle integration. Keep Windower unchanged, preserve framework/legacy
precedence and compatibility commands, repair pact-gear handling in staging,
and validate lifecycle failures before personal conversion or activation.
