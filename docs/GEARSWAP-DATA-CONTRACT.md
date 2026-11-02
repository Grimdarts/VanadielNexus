# Managed GearSwap data contract, version 1

Status: version-1 specification implementing approved stage-1 decisions, with T3 reader/resolver implemented and tested in staging. See [T3 validation](GEARSWAP-T3-VALIDATION.md) and [staged host API](../staging/gearswap/README.md). No active Lua profile or installed file has changed. SMN lifecycle integration and personal-data parity remain T4/T5 gates.

## Files and ownership

Maintained files live in `GearSwap/data/PlayerSystem/{core,jobs,integrations,examples}`. Personal files live in `GearSwap/data/PlayerProfiles/<profile>/`: `Equipment.lua`, `Settings.lua`, `Hotkeys.lua`, `Sets/<JOB>.lua`, and optional `G13.lua` and `Automation.lua`. `<profile>` is an opaque local folder ID with no path separators, traversal segments or automatic character-name inference.

A character/job entry is ordinary maintained bootstrap Lua plus a clearly identified personal binding to that profile. Preserve GearSwap's actual discovery precedence. Existing entries are inventoried before activating a new one; no competing entry is silently deleted. Maintainer updates must preserve binding metadata and personal files. Packaging/installer behavior beyond local staged migration is deferred.

## Supported text grammar

The single maintained Lua reader accepts one optional UTF-8 BOM, whitespace/comments, the keyword `return`, one literal table, and end of file. Newline style may be LF or CRLF. Preserve original spans/newlines/comments for later edit planning; version 1 does not itself implement saving.

Values: UTF-8 quoted strings, finite decimal numbers with optional sign/fraction/exponent, booleans, and tables. Keys: Lua identifiers followed by `=`, or bracketed literal string/integer keys. List values use implicit consecutive integer keys. Comma/semicolon separators and trailing separators are accepted. Reject duplicate keys, duplicate implicit/explicit list positions, holes in required arrays, ambiguous mixtures of list/map data, invalid UTF-8, and excessive size/depth.

String escapes: escaped quote, backslash, `\a \b \f \n \r \t \v`, up to three decimal escape digits in byte range 0-255, and escaped newline normalized to newline. Comments: line comments and Lua long comments with matching equals-delimited brackets. For the initial managed format, long-bracket string values and executable/interpolated expressions are unsupported; show their location and offer the custom-Lua copy workflow. Restrict identifiers to keys; an identifier used as a value is not evaluated. `nil`, functions, function calls, concatenation, operators, variable references, metatables, file inclusion and arbitrary code are rejected.

All managed roots have `schema = 1` and a file-specific `kind` string. Unknown schema versions or fields are errors naming the file/key. Maintain source line/column/span for every value and reference. Default resource limits: 2 MiB per managed file, 64 nested tables, 100,000 parsed values, 4,096 records/sets per file, and bounded reference depth. These are initial defensive implementation limits to measure against fixtures, not player performance claims. Errors name the exceeded limit; never silently truncate.

Resolution additionally allows at most 100,000 copied values/tables (`materialized_values`) per candidate. Catalog-reference expansion, inherited gear/provenance, copied source spans and runtime equipment copies share this budget. Charge before each copy and fail with file/set/slot context; input size limits alone do not bound repeated reference expansion. Hosts may tighten this limit but cannot raise it. No partial candidate is published on exhaustion.

The Lua module is shared by GearSwap and the existing isolated Nexus worker. Never `include` or `loadstring` the managed file as code before validation. Loading maintained modules is separate. Future editor writes use a separate token/span-aware patch layer; a parsed table alone does not prove round-trip safety.

## Equipment catalog

Illustrative syntax only; sample equipment below is not a claim about player ownership:

```lua
return {
    schema = 1,
    kind = "equipment",
    items = {
        cape_0001 = {
            label = "SMN magical pact cape",
            name = "Campestres's Cape",
            augments = { "Pet: M.Acc.+20 Pet: M.Dmg.+20", },
        },
    },
}
```

`items` maps stable catalog record IDs to records. IDs use ASCII letters/digits/underscore, beginning with a letter; they are not FFXI item IDs and are not recomputed when augments/labels change. Existing IDs remain stable during migration where valid. Create another ID for a distinct physical copy; never infer that identical descriptors prove two copies are the same. Exact selection among indistinguishable copies may require a bag constraint.

Record fields: required nonempty `name`, required readable `label`, optional ordered string `augments`, optional GearSwap-compatible `bag`, optional integer `priority`. Labels need not be unique; IDs must be. Distinguish empty augment array from unspecified augments and document matching implications. Do not invent rank/path augments or assume resource-derived ownership. Initial validation proves structure/references and supported resource eligibility where available; absence from a currently incomplete inventory scan must not silently substitute another item.

Changing a label retains identity. Deleting/renaming an ID requires checking all consumers and explicit reassignment; there is no silent redirect. Runtime resolution copies full item records, dropping UI-only label/ID fields from actual GearSwap equipment and retaining identity/provenance separately.

## Job sets

```lua
return {
    schema = 1,
    kind = "sets",
    job = "SMN",
    definitions = {
        pact_magic = {
            path = { "midcast", "Pet", "MagicalBloodPactRage" },
            slots = { back = { ref = "cape_0001" }, },
        },
        pact_magic_accuracy = {
            path = { "midcast", "Pet", "MagicalBloodPactRageAcc" },
            bases = { "pact_magic" },
            slots = { neck = "Sanctity Necklace", },
        },
    },
}
```

Stable definition IDs are separate from GearSwap paths. `path` contains literal string or nonnegative integer components, excluding the root `sets`. Preserve exact case, punctuation and spaces. This avoids interpreting dots inside names as path separators. Every exported canonical path must be unique.

`bases` is an ordered list of definition IDs. Resolve left to right, last base wins per slot, then apply local `slots`. Resolve forward references using memoization, detect cycles with a complete reference-chain diagnostic, reject missing bases and bound nesting. A declared empty set with no bases/slots exports an empty table; it is different from a definition not present.

Slot values:

- String item name: ordinary unaugmented/name-matched gear, as approved.
- `{ ref = "record_id" }`: exact catalog record. Optional `bag`/`priority` on this reference override only those per-use constraints; they do not mutate the catalog or merge augments.
- `{ empty = true }`: intentional GearSwap `empty`, meaning unequip that slot. Materialize the real GearSwap sentinel, not an empty Lua table.
- `{ omit = true }`: remove this slot from inherited resolved equipment; no equip request for this slot. This is different from intentionally unequipping it.

Normalize supported GearSwap slot aliases to the 16 canonical slots using installed slot mappings. Reject two local keys resolving to the same slot. Whole slot replacement replaces all item fields, including augments; do not recursively merge equipment. Base definitions retain their own values. Every distinct canonical set gets independent item/augment copies.

Required provenance for each resolved slot: defining set, inheritance chain, catalog record ID if any, source file/span, whether the destination supplied an override, and resulting bag/priority. This is stage-1 data, not a stage-1 Nexus UI requirement.

### Existing SMN aliases and cycles

The baseline contains intentional path aliases (`sets.ward`, `sets.perp`, etc.) and a self-referential path created by `sets.engaged.Perp = sets.perp`. An inheritance-cycle error is not the same thing as a legacy runtime alias cycle.

Represent canonical equipment once; store optional `aliases` as additional literal path arrays on that definition. Mount canonical tables first, then aliases in parent-path order. An alias intentionally names the SAME semantic set, so both paths refer to its canonical runtime table; distinct canonical sets still have independent equipment. Preserve required self-aliases explicitly and traverse runtime graphs cycle-safely. Reject an alias that overwrites another canonical set or points ambiguously to a conflicting destination. Verify all baseline aliases before conversion. No deliberate legacy alias is silently flattened or removed.

Maintained job logic must treat resolved definitions as read-only. Existing routines that replace or mutate source sets need conversion to temporary working overrides with action-context comparisons; alias mounting does not grant permission for arbitrary source mutation. If identity-sensitive behavior cannot be preserved this way, discuss it before migration.

## Settings and hotkeys

Both roots use `schema`, `kind`, `shared` and `jobs` (job abbreviation -> override group). `Settings.lua` has `kind = "settings"`; `Hotkeys.lua` has `kind = "hotkeys"`. One personal file of each kind covers shared defaults and per-job overrides, avoiding per-job duplication.

Named setting maps merge recursively in this order: maintained defaults, profile shared, selected-job override. Ordered arrays replace atomically; an explicitly empty array replaces with no entries. Scalars replace compatible scalars; type mismatch is an error. `{ remove = true }` removes an optional inherited entry; it is not a boolean false or the same as omitting the key. Required keys cannot be removed. Use the schema to distinguish empty maps from empty arrays.

Settings are validated against the selected job's maintained schema/modes. Preserve job-specific modes such as `favor`, `damagetaken`, `petdamagetaken`, `tplock`, `bpmagicacc` and `burstmode`. Following source and isolated command tracing, Jason delegated the SMN lag-setting decision: use one authoritative `lag_compensation` preference, initially true, mapped to the runtime mode used by both gear handling and display. Retain existing command spellings as compatibility routes to that one setting. The flag-only candidate exposes an existing missing helper on the OFF path, so pact-gear handling must be repaired and verified before activating this change. Do not silently merge other distinct settings just because names look alike.

Keyboard bindings map key chords to command-ID records with optional validated literal arguments, rather than unrestricted code. Maintained command definitions provide labels, applicability, and execution. Per-job bindings may override/remove shared keys. Validate unknown commands and unsupported key syntax before installing anything. Profile key names and command IDs remain neutral; compatibility routing retains existing `gs c nova ...` and G13 aliases until a tested migration replaces them. G13 bindings live only in optional G13 configuration, not Hotkeys.lua.

Legacy Mote globals/sidecars remain for framework compatibility and unconverted jobs. Inventory the actual load order. Transfer migrated preferences into the profile and apply them at the correct lifecycle point so its defined fields/bindings have final precedence. Diagnose overlap; do not rewrite shared globals or let a late legacy include silently undo a migrated value.

## Binding, readiness and lifecycle

The setup binding records a stable profile ID, expected character name and numeric server ID. Server display name is informational; compare numeric IDs to avoid name/localization ambiguity. Profile paths must stay inside the configured PlayerProfiles root; reject traversal and unexpected redirection.

Read `windower.ffxi.get_player().name` and `windower.ffxi.get_info().server` without depending on Nexus. The documented server field must be verified on the installed runtime before activation. This has not been probed in the live game yet. Missing identity: bounded retry for up to 10 seconds at 0.5-second intervals, coalesced diagnostics, then a clear failure requiring retry/reload. An explicit mismatch fails immediately. Temporary waiting registers only the readiness observer; no job framework, swaps, bindings, automation or display attaches yet. Job change/logout/unload cancels the observer and invalidates its generation token.

After identity, parse/validate/resolve required data completely before including the existing framework. On success, run the appropriate integration initialization, apply authoritative migrated settings/bindings, and publish ready once. No candidate data is published on failure. Errors after framework entry require phase-aware cleanup of existing framework and new resources, tolerating partial hooks and repeated teardown. No other character or last-good profile is substituted.

Mote may invoke event handlers during initialization. Integration tests must show prepared definitions are available before those calls and that failure cleanup also covers framework-owned resources. Preserve existing SMN paths first; BLU/RUN only receive a paper mapping in this stage.

## Migration and activation gates

1. Compare this format against canonical leaves, aliases, empty sets, subjob branches and selected action-context captures in the private baseline.
2. Classify actual automatic action use separately from player-triggered sequences and delayed gear/HUD work. Present any behavior needing a decision before modifying it.
3. Implement the restricted reader/resolver only after contract findings are resolved. Test pure resolution, errors, provenance and mutation isolation before a framework adapter.
4. Convert data in staging, then require zero unexplained parity differences and successful lifecycle tests before activation.

No automatic migration writes player files in version 1. A conversion candidate is a separate staged output, with reviewable diff and source hashes. Saved catalog edits take effect after a successful reload. Later Nexus writes and public packaging remain separate stages.
