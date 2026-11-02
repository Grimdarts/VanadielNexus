# Staged GearSwap bundle components (T3/T4)

Inactive source candidate for the approved GearSwap bundle project. Nothing in
this directory is loaded by Windower or packaged into the Nexus executable.
Do not copy the examples into an installed profile as a playable SMN migration.
Their equipment is illustrative and does not assert player ownership.

`PlayerSystem/core/managed_data.lua` is the single Lua 5.1 reader used by both
the direct Lua tests and `managed_worker.py`. The Python harness reuses Nexus's
LuaJIT dependency, denied-attribute callback, and instruction budget. Tests
exercise it in a spawned process with a parent timeout, following the existing
worker pattern. There is no independent Python interpretation of player Lua.
Production Nexus worker routing remains later integration work. T4 adds the
staged lifecycle, checked Windows reader and SMN compatibility adapter described
below; installed-runtime host wiring and activation remain open.

The reader accepts source **bytes**, not executed Lua. Only the trusted module
is compiled by the host. Invalid files raise location-aware errors. A host may
use `pcall` to catch them; it must discard the entire candidate on failure.
`prepare` performs no I/O or game-side actions and returns only after all four
required documents validate. Do not publish its partial intermediate work.

## Maintained host API

- `parse(bytes, filename, limits?)` returns an AST document with original source,
  table shape, key spans and a node for each value. Spans use 1-based byte
  `[start, finish)` offsets, 1-based lines and UTF-8 character columns. CRLF,
  CR and LF are recognized. Limit overrides may only tighten the defaults.
  Resolution has a separate lower-only `materialized_values = 100000` copy-work
  budget so repeated catalog/base references cannot amplify small input without
  bound. Copy-budget errors name the affected file, set and slot.
- `catalog(document)` validates equipment records. Runtime `item` records omit
  the UI label; stable IDs and record source spans remain separate.
- `resolve(sets_document, catalog, options)` resolves forward/ordered bases,
  whole-slot replacement, omissions and explicit empty values. `options.job`
  checks the job. `options.empty` must be the actual GearSwap sentinel whenever
  an empty marker occurs. Optional maintained `validate_item(item, slot)` returns
  true or false plus a diagnostic, for resource-backed eligibility checks.
- Resolution returns `sets` (runtime graph), `definitions` (canonical equipment
  plus slot provenance) and `paths` (parsed declarations). Canonical sets have
  independent item/augment copies; aliases intentionally share their table.
  The runtime graph may cycle. Serialize canonical definitions, not that graph.
  `copy(table)` is cycle-safe for later transient working copies.
- `settings(document, job, schema, defaults)` merges named maps, replaces arrays
  atomically and supports optional-entry removal. Schemas define `type`, map
  `fields`, array `item`, scalar `enum`, and `required`. Empty table meaning
  comes from the schema. A selected job's maintained schema validates shared
  and selected-job values; other job groups receive structural validation only.
  The future all-job editor must supply the other job schemas before editing them.
- `hotkeys(document, job, commands, defaults?)` validates literal command records.
  Command descriptors optionally define applicable `jobs` and an argument schema
  in `args`. This installs no bindings. Supported chords have distinct Windower
  modifiers followed by a lowercase letter/digit, F1-F12, or the named navigation
  keys listed in the module. Equivalent modifier order is normalized; duplicates
  in one group fail. Additional key syntax requires maintained validation first.
- `prepare(sources, options)` requires Equipment.lua, Settings.lua, Hotkeys.lua
  and Sets/JOB.lua. `sources` maps those relative names to source bytes. Options
  provide `job`, diagnostic `profile` label, `empty`, `settings_schema`, maintained
  settings `defaults`, command registry `commands`, optional maintained `hotkeys`,
  optional tighter `limits` and resource callback `validate_item`.

The `profile` option is only a diagnostic label. It grants no path access and
does not establish identity. The adapter must validate explicit character/server
binding and path containment before reading files. The staged worker accepts
in-memory sources and deliberately has no profile-path reader.

Run focused checks with:

```powershell
py -3 -m pytest -q -rs tests/core/test_managed_gearswap.py
```

The reference fixture uses SMN path names, catalog references and the resolved
`lag_compensation = true` preference. Its schema is a test host schema, not the
final SMN mode/command registry. Existing pact dispatch, lifecycle teardown,
legacy-precedence integration and personal-data conversion are T4/T5. They must
be validated before any activation authorization is sought.

## T4 SMN integration

See [T4 progress and evidence](../../docs/GEARSWAP-T4-VALIDATION.md).

- `core/lifecycle.lua` validates explicit binding and gates setup on character,
  numeric server and job. Missing identity retries at 0.5-second intervals for
  up to 10 seconds. Generation guards invalidate stale observers/timers. Failure
  clears ready state before idempotent rollback; a later explicit start retries.
- `core/ownership.lua` tracks attempt-owned controls, event IDs, unhandled command
  callbacks and native HUD objects. Legacy cleanup cannot unbind a key this
  attempt never acquired. Prior controls are restored only while still owned.
  Both fully initialized and partial framework cleanup are exercised.
- `jobs/SMN.lua` supplies the selected SMN schemas, defaults and a literal command
  registry. `jobs/smn_pacts.lua` repairs missing helper/dispatch behavior through
  the actual Mote pet action pipeline, preserves normal pet-midcast handling,
  adds guarded 0.5-second compensation, and uses transient Siphon day overlays.
- `integrations/mote_smn.lua` loads inventoried legacy sources only after full
  candidate preparation, supplies working set copies during Mote setup, and
  applies managed settings/hotkeys after globals and sidecar precedence. It
  preserves the existing Nova control renderer and M-button compatibility.
- `integrations/prepare_host.lua` supplies the identity/readiness/parse boundary.
  `integrations/windows_profile_files.lua` provides a tested read-only LuaJIT FFI
  reader: component handles, reparse rejection, final-path checks, bounded reads,
  and handle cleanup. `core/eligibility.lua` checks available resource slot,
  job/level and equipment-bag metadata without asserting ownership.
- `integrations/bootstrap.lua` connects maintained modules and trusted native
  services. `examples/Player-SMN-entry.lua.example` is an inactive, fail-closed
  entry template. Its binding placeholders and host dependency are deliberate.

The host must provide verified `read_profile`, `get_control`, `now`, `schedule`
and `load_legacy` services, plus optional notification/bridge leases. `get_control`
must return current binding/alias payloads, including unrelated owners' changes;
an empty map is not a substitute for probing the running instance. Timer services
must use monotonic real time and return a cancellation function where supported.
The control service must also provide read-your-writes semantics for accepted
queued commands, while detecting other owners' changes. The synchronous probe
ledger does not establish that guarantee for Windower's native command queue.
`load_legacy` must load the reviewed, hash-recorded maintained/staged source in
the supplied environment; automatic character/profile discovery is not provided.
The real GearSwap unhandled-command registry is reused for callback teardown.

These services are injected by the offline probe. A complete installed-runtime
service bundle, live server-identity probe and 32-bit Windower validation are
still required. T4 remains open for that work. The Windows reader was exercised
with the available Windows LuaJIT host; this does not establish its ABI or native
service availability in the running game. Production files and the executable
are unchanged.

Native host verification must trace compound/delayed bind and alias commands
through Windower's actual command grammar before extending the compatibility
wrapper beyond the captured sources. Splitting existing macro bodies on every
semicolon would change player-triggered sequences. The current wrapper is not
a general command parser; managed profile hotkeys use the literal registry.

Keyboard validation now also covers the existing SMN numpad/punctuation keys
and `%` chat suppression syntax. This closes a baseline compatibility gap in the
initial T3 allowlist; profile commands remain literal registry references.

Run the read-only local integration probe with:

```powershell
py -3 staging/gearswap/check_smn_integration.py --windower C:/path/to/Windower4 --character YourCharacter
py -3 -m pytest -q -rs tests/core/test_gearswap_lifecycle.py tests/core/test_gearswap_profile_files.py tests/test_gearswap_smn_integration.py
```

The probe uses current legacy equipment in sandbox memory to exercise the adapter.
It does not emit a converted profile, include personal equipment in fixtures, or
prove T5 canonical/action parity against an independently converted profile.
