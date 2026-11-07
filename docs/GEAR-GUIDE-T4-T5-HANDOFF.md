# Gear Guide T4–T5 continuation handoff

Date: 2026-11-03. Checkout: `codex/sets-copy-fixes-review`; HEAD `5657f20`.
All source work remains uncommitted, including the earlier T2–T3 changes.
Jason accepted the concrete T4 mockup as a useful starting point and requested
continued implementation tonight. Do not repeat that visual approval or T1's
accepted architecture/specification questions.

## T4 source implementation

- Existing `GuidesPage` and Purpose → Set → Version workflow support both the
  shipped legacy catalog and prepared v2 revision catalogs. `ui/guide_revisions.py`
  contains the revision interactions; pure presentation/comparison helpers extend
  `core/gear_guides.py`, rather than creating a second catalog service.
- Revision targets live only in the separate `WorkspaceStore`. Viewing, changing
  versions and refreshing cannot adopt or rewrite them. A saved snapshot remains
  inspectable after revision retirement, catalog disappearance/corruption, or a
  return to the v1 catalog. Empty complete character snapshots differ from absent
  snapshots. Legacy ring/ear eligibility remains unresolved; no exact-slot import.
- Strict item IDs, one simultaneous allocation and verified numeric bag resource
  mappings drive comparisons. Ownership, bag readiness, ambiguity, unknown,
  omitted and intentional-empty states remain distinct. The table describes saved
  inventory evidence, never current game readiness or full eligibility certification.
- Personal requirements and designated bags are edited per canonical slot.
  Curated requirements remain visible and immutable. A Ring 2 override cannot
  modify Ring 1. Unknown bag mappings cannot establish readiness.
- Source actions use the displayed revision's retained provenance. One reference
  opens directly; several use title/locator choices. Stale selections and unsafe/
  unavailable links are rejected. Item wiki actions remain separate.
- Adoption reviews one exact character/target, before/after requirements, context,
  currency, verification, assumptions, rationale, sources and retained personal
  choices. It saves only after explicit acceptance and successful persistence.
  Changed selection/workspace during review invalidates the proposal. Disappearing
  bound/overridden slots block adoption for reconciliation rather than dropping data.
- Failed saves retain the old primary/authoritative memory and the store's pending
  proposal. Conflicting writers require reload/review. Reload asks before discarding
  pending work. Corrupt-primary recovery is explicit, preserves evidence and retains
  the good backup. Unsupported newer workspaces remain read-only.
- The production catalog is still v1. Revision-aware catalog integration is exercised
  with prepared fictional candidates; no real legacy records were converted. The
  v2 runtime loader validates against local item resources and fails closed on
  unsupported weapon composition evidence. T7 must supply the reviewed production
  catalog and hand-type evidence integration. T4 does not certify existing entries.
- Revision targets are inspectable in the Guide page's saved-target selector. They
  are not mirrored into legacy Wishlist records. Existing legacy Wishlist tracking
  remains usable through its existing policy.

## T5 source implementation

- `core/equipment_effects.py`: immutable source/effect/result records; item/rule/
  source/slot provenance; separate master, Pet and Avatar recipients and units;
  conservative per-result completeness; Owned versus Planning contributions.
- Supported inspected base contexts: Stikini +1 MND/direct magic accuracy/all-magic
  skill family/Refresh; described DT/MDT/PDT on the pinned inspected items; Epona
  DA/TA rates; inspected Fast Cast; Nyame Pet and Indomitable Avatar boundaries.
  No expansion of all-magic-skill points into accuracy or of Pet into every pet type.
- Inyanga uses the six exact approved +2/accessory IDs, once per legally selected
  loadout, `min(4, max(0, distinct qualifying pieces - 1))`. Set scope resets the
  preceding Avatar block. Missing/unknown membership retains uncertainty.
- Assiduity +1 uses verified Unity membership/standing, independently of augment
  rank: first place 2, another verified valid standing 1, unknown standing unresolved
  1–2 MP per three-second tick. No affiliation/invalid input remains unsupported.
- Exact inspected English-description hashes pin applicability. New/changed wording,
  missing descriptions, unsupported augments/rank/path magnitudes and other effects
  remain visible as unresolved; unscoped unknowns conservatively affect every subtotal.
  No effective caps, incoming damage, proc distributions, final cast/recast times,
  Fucho threshold formula, hypothetical maximum augment, or full-stat coverage claim.
- Owned evaluation first allocates distinct matching observations from the selected
  character; missing copies do not become target contributions. Explicit equippable
  bag IDs allow the shared allocator to prefer designated bags. Ambiguous copies
  retain uncertainty. Callers must supply snapshot availability and canonical evidence.
- `prepare_source` reads only `res/items.lua` and `res/item_descriptions.lua` as data,
  bounds combined bytes (16 MiB), rows (50,000/file) and line length (65,536 chars),
  rejects changing/duplicate/unreadable resources and returns detached English indexes.
  No player data, database/settings instance, game poll or Lua execution is involved.
- `EvaluationCache` bounds entries (256) and a conservative retained-size estimate
  (2 MiB). Keys include source fingerprint, rule version, exact selection/observations,
  context and conditions. Results are immutable; eviction changes no arithmetic.
- `ui/equipment_preparation.py`: explicit coalesced requests, one active parse plus
  only the newest pending request, cancellation on close/destruction and GUI-thread
  publication guarded by root/signature/generation. Guards also cover reentrant
  loading-state listeners. No widgets are touched from workers, and no watcher/poll
  was added. T6 consumers must request it on relevant first use/explicit refresh and
  close/cancel it when disposed; this adapter is not yet wired to card/analyzer UI.

## Validation

All UI/core fixtures use temporary `VN_DATA_DIR` and fictional inventory/resources.
The only real-resource probes read local resource files, with no player Lua/data.
`py -3` was attempted; the WindowsApps launcher remains inaccessible. Use the
existing interpreter:

```powershell
& 'C:/Users/Jason/AppData/Local/Python/pythoncore-3.14-64/python.exe' -m pytest -q -rs
```

Direct TEMP/TMP/VN_DATA_DIR to a writable isolated test root. The first full sandbox
run had 728 passes and the same native junction/UDP failures as T2–T3. The two
unchanged tests plus the actual Qt render passed with native permissions (3 passed).
T4's focused compatibility/UI/core run passed 88 tests before later guard additions.
T4/T5's subsequent focused run passed 53 tests; the expanded reentrant worker suite
then passed 7 tests. A full native run passed 763 tests in 90.43 seconds; two
reentrant worker fixtures were added after that run's collection. Final exact-
source native full-suite result: **765 passed, 0 failed, 0 skipped in 87.37 s**.
`git diff --check` passed. The local item/description SHA-256 values were read back
and still match the T1 evidence snapshot. No source changes followed this final run.

The real Qt Guide page was rendered and inspected at 900×600 and 1024×768. The
offscreen sandbox requires explicitly registering installed Segoe UI for readable
screenshots; this is test/probe setup, not a product font change.

`tools/profile_equipment_effects.py` provides a reproducible read-only preparation,
event-loop, RSS, traced-memory and recalculation probe. Its JSON records exact source
fingerprint, input bytes, sample counts and declared fixture. Baseline is a standalone
QCoreApplication: full-page/card presentation, frozen size and live coexistence
remain T6/T9 acceptance work. Final probe results follow.

Final exact-source standalone probe (same resource fingerprint
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`):

| Measurement | Result / scope |
|---|---|
| Inputs | items.lua 5,040,087 bytes; descriptions 4,972,281 bytes |
| Prepared index | 15,527 equipment rows; 23,456 English descriptions |
| Worker preparation | 0.6373 s, uninstrumented |
| GUI event loop | Maximum observed gap 12.32 ms over 70 samples, 5 ms timer |
| Whole-process RSS | Sampled preparation peak +37.48 MiB; ten settled batches +16.31–16.33 MiB |
| Python allocation probe | Separate instrumented second preparation: retained 11.81 MiB; peak 34.46 MiB |
| Cache | 256-entry cap; conservative retained-size estimate capped at 2 MiB |
| 16-slot recalculation | 200 varying-scenario cache misses; p95 0.998 ms |
| Warm result lookup | 1,000 hits; p95 0.0175 ms |
| Fixture meaning | Five Inyanga +2 pieces, Loricate +1, two Stikini +1; eight explicit empty slots; known Refresh subtotal 6 remains incomplete |

These observations meet the standalone source/worker portions of the proposed
budgets on this run. They do not satisfy same-page memory, card dwell/presentation,
full all-rule workload, frozen artifact size or in-game coexistence acceptance.
The trace/index cache remains in memory; the JSON above is diagnostic output only.

Stable artifacts for this continuation chat:

- `C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a3a0-116a-7702-ba9a-92c16b210e24/gear-guide-t4-900.png`
- `C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a3a0-116a-7702-ba9a-92c16b210e24/gear-guide-t4-1024.png`
- `C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a3a0-116a-7702-ba9a-92c16b210e24/equipment-effects-profile.json`

## Remaining work and boundaries

Next: T6 concrete item-card/analyzer visual review and integration using the T5
core. Preserve supported-subset/partial/uncertainty labels and exact copy evidence.
T7 production 22-job catalog authorship, T8 builder/output and T9 final integration/
performance/frozen checks remain. No real migration, build, executable replacement,
commit, push, installation, release or GearSwap activation was performed.
Windower/player Lua stayed read-only. The installed post-commit build/relaunch hook
still exists; do not commit app code casually. Keep all existing untracked planning
documents and `.codex-remote-attachments` intact.

Resume from this handoff and the accepted T1 packet. Do not reopen accepted T4
visual choices merely because the mockup file contains historical pending wording.
