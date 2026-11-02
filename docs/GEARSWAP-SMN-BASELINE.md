# Stage-1 read-only baseline

Captured 2026-11-02 from the current Windower files, using the existing Nexus sandbox reader. No installed files were edited, no live commands were issued, and no in-game timing or physical LCD test was performed.

Private evidence directory: `%USERPROFILE%/.gstack/projects/Grimdarts-VanadielNexus/stage1-baseline-20261102/`. It contains manifest/source hashes, 35 dependency snapshots, per-context read/canonical JSON, and a private instrumented context-capture sandbox. Personal equipment definitions stay there, outside repository fixtures.

## Static captures

| Job/subjob context | Canonical sets | Equipment slots captured | Included Lua files | Load errors/partial result |
|---|---:|---:|---:|---|
| SMN, unspecified subjob | 100 | 930 | 12 | None / no |
| SMN/SCH | 100 | 936 | 12 | None / no |
| SMN/RDM | 100 | 930 | 12 | None / no |
| SMN/WHM | 100 | 930 | 12 | None / no |
| BLU/NIN | 78 | 921 | 3 | None / no |
| RUN/BLU | 80 | 996 | 3 | None / no |

These are instantiated sets in the specified mocked contexts, not proof of every conditional configuration. Six SMN/SCH slot differences show why subjob context must be retained. Initial capture hashed 154 candidate source files before and after; zero changed. Supplemental G13 source files were included in the evidence manifest.

SMN load order captured: shared gear -> Nova controls -> SMN library -> Mote include -> Mote mappings -> Modes -> Mote utility -> Mote selfcommands -> Mote globals -> user globals -> SMN sets -> organizer. The character entry itself is also snapshotted. `custom_includes` is false in the current source; no active custom_aliases/custom_commands dependency was observed in these contexts.

## Paper mapping against the proposed contract

| Current example | Proposed representation | Framework implication |
|---|---|---|
| SMN `sets.midcast.Pet.MagicalBloodPactRage` | Stable set ID; path array `{"midcast","Pet","MagicalBloodPactRage"}`; catalog/plain slot values; declared bases for accuracy variants | Prepared data supplied through existing Mote `init_gear_sets` path |
| BLU `sets.TP.AccuracyFull` | Same definition structure, path `{"TP","AccuracyFull"}`; 13 populated slots in this capture | Custom `get_sets` adapter; no forced Mote conversion |
| RUN `sets.OneHandedTP.AccuracyFull` | Same structure, path `{"OneHandedTP","AccuracyFull"}`; 13 populated slots | Custom initialization and existing weapon/defensive rules remain |

Thus the player-data representation can cover all three observed naming patterns without standardizing internal job frameworks. Exact conversion and equivalent action behavior remain implementation/test work.

## Aliases and empty sets

SMN has nine captured canonical sets with additional paths, including:

- `sets.idle.Avatar` also appears as `sets.engaged` and `sets.perp`.
- Ward, healing, debuff, hybrid, magical and physical pact aliases.
- Shared precast Ward/Rage and physical-WS/WS paths.

Source lines 1034-1036 in the SMN sets create a self-alias through `sets.engaged.Perp`. It must be traversed cycle-safely and handled as explicit runtime compatibility, not mistaken for a circular declaration of base sets. The draft contract distinguishes those concepts.

Eleven captured empty sets are legitimate baseline output, including `sets.buff`, `sets.defense`, `sets.damagetaken.None`, Siphon overlays and unused ranged sets. Empty sets differ from missing definitions and intentionally unequipped slots. Existing reader tests also document legacy absent branches; do not invent gear for them.

## Controlled action-context capture

A private copy of the existing sandbox was instrumented; the application sandbox and installed files were not edited. It uses mocked SMN/SCH with Garuda, records strings instead of sending commands, and does not run queued waits. Evidence is `SMN-SCH-contexts.json`.

- Recorded 29 mode values and all 66 G-key positions across M1/M2/M3, including avatar-resolved labels and intentionally unassigned keys.
- Mapping samples: Predator Claws -> TPPhysicalBloodPactRage; Flaming Crush -> HybridBloodPactRage; Wind Blade and Impact -> TPMagicalBloodPactRage in the mocked low-TP context. Hastega II returns no custom map, leaving the existing framework fallback responsible.
- Recorded successful command-generation requests for `smn ifrit`, `supportmode`, `nukemode`, `buffrotation`, and `siphon`. This proves these mocked codepaths produced the captured requests, not that spell targets, cooldowns, timing or every sequence work live.
- Current representative defaults include OffenseMode Perp, CastingMode Normal, IdleMode Normal, Favor MP Saver, defense/pet defense None, and burst mode Normal. Full values remain in the private snapshot.

## Action-initiation classification

| Existing behavior | Trigger and classification | Migration requirement |
|---|---|---|
| Avatar switch | Explicit `gs c smn <avatar>`; may request release then summon | Preserve as player-command sequence, not unattended routine |
| Support/nuke preparation | Explicit command; finite Arts/Addendum/Sublimation/storm sequence | Preserve command availability independently of unattended-automation toggle |
| Next buff | Explicit `buffrotation`; advances one indexed entry per request | Do not infer a continuous buffing loop from the name |
| Elemental Siphon helper | Explicit `siphon`; selects spirit/storm and emits a finite sequence including restoring prior avatar | Preserve observed command behavior; validate actual timing later |
| Trust/prebuff/warp aliases | Explicit alias/hotkey; delayed finite requests | Inventory command ownership and cancellation semantics; do not start them automatically |
| `EquipBP`, `updategear`, Ward reset | Delayed gear/state maintenance after existing events | Core gear/state behavior; a delay alone does not make it action automation |
| HUD update and pet-TP packet handling | Display/state maintenance | Separate from gameplay action routines |
| Macro book and lockstyle setup | Job setup; changes interface/appearance | Record existing preferences; do not confuse with unattended combat routines |

No unattended casting loop or automatic resummon was identified in the inspected active SMN hooks. A commented-out release/resummon line is not active behavior. This is a bounded source finding, not proof about every external addon or a live session. The optional automation design stays unchanged; any newly discovered automatic behavior requires review before migration.

The Siphon helper currently replaces its precast source set based on day. Refactor to a transient working override during migration, under the already-approved no-source-mutation rule, and compare action-context equipment. Do not omit the day-dependent behavior.

## Lag-setting decision and dependent migration defect

The current SMN entry has two separate lag flags:

- `LagMode = true` at entry line 182 controls delayed BP gear handling at library lines 590/611.
- `state.lagmode = M(false, 'Lag Mode')` at entry line 237 is displayed in the legacy HUD at library line 171 and bound to Alt+F11 at entry line 255.
- `gs c lagmode` separately toggles `LagMode` at library lines 1022-1025; `gs c toggle lagmode` addresses the Mote state.

They are distinct code variables, with different initial values. A controlled trace through the installed `self_command` path in the private sandbox confirms: initial runtime/display = true/false; first `toggle lagmode` = true/true; second toggle = true/false; direct `lagmode` = false/false. Commands were captured, never issued to the live game. Thus the displayed toggle and actual timing flag are independently controlled in this test.

Jason delegated this decision after the recommendation, so choose one authoritative lag-compensation setting, initially true to preserve the currently active path. Both command spellings and the display must use it. This is an intentional, recorded correction rather than an unexplained parity difference.

A private flag-only candidate and regression probe confirm one initial true state and successive toggle results false/true/false through the existing commands. Active source hashes remain unchanged. However, exercising the OFF timing path in BOTH the original and candidate reproduces `attempt to call global 'equipBPGear' (a nil value)` at library line 612. The active library calls but does not define that helper; similarly named complete routines appear in archived, inactive Lua files and have not been imported. The ON path emits the existing delayed EquipBP command, but successful command generation does not prove the active job handles that delayed command or equips the right gear.

The flag-only patch is therefore NOT ready for activation. Resolve and validate pact-gear handling in the staged migration before wiring the authoritative toggle into an active profile. This is a dependency repair of existing SMN behavior, not permission to add new automatic actions or import an archival implementation wholesale. Record any proposed timing/gear change for review; independent format/reader work can continue. Private evidence: `lag-mode-candidate/result.json` and `check_lag_candidate.py` under the baseline directory.

## Displays and integrations to preserve

- M-button script and Nova bindings remain snapshotted; Jason previously confirmed immediate switching live. This capture did not press physical buttons.
- Current Nova overlay settings: size 7, compact view, position (396,724). Separate SMN legacy HUD position: (1476,234). Pixel dimensions and actual appearance still need a live reference/mockup later.
- Legacy SMN HUD is configured hidden by default; Nova controls provide the separate visible overlay. Do not conflate these displays.
- `g13_smn_bridge` writes the existing single-character home telemetry file. Its automatic Binder-alias feature is currently false. This is not a validated multi-character bridge; replacement/isolation belongs to the later G13/coordination stage.
- Actual LCD applet source has not yet been located in the inspected project/graphics locations. Do not claim a full LCD baseline or adjust it until inspected.
- Installed identity availability/server ID has not been probed in game. No server identity was inferred from sandbox data or Vana'diel area names.

## Validation and current gates

Existing repository suite: `py -3 -m pytest -q` -> **477 passed in 69.40 seconds**, no skips reported. These tests validate current application behavior and baseline tooling dependencies, not a new loader or future parser.

T1: concrete format drafted and checked against representative SMN/BLU/RUN structures; no new reader implemented. T2: offline sources, canonical leaves, modes/keymap and selected command contexts captured. Lag-setting direction is resolved. Still pending: dependent pact-gear helper/dispatch repair and validation, live identity probe, broader action/equipment timing checks, and physical display confirmation. New-reader work may proceed independently under the approved stage plan; SMN activation cannot be called ready from this baseline alone.
