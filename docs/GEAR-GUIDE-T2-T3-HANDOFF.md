# Gear Guide T2–T3 core handoff

Date: 2026-11-03. Checkout: `codex/sets-copy-fixes-review`, HEAD `5657f20`.
T1 was accepted and T2–T3 implementation authorized in the originating chat.
This handoff describes source changes and offline fictional-fixture validation.
No commit, hook, build, installation, release, migration or Lua activation was run.

## Implemented core

- `core/equipment_matching.py`: Qt-free identity, slot aliases, augment keys,
  GearSwap selector matching and maximum matching extracted from existing callers.
  `set_manager` retains its selector policy and original allocation ordering.
  Legacy guide matching retains its existing substring policy through an explicit
  adapter; new `requirements_match` checks whole augment parts, multiplicity,
  observed minimum rank and exact path on one copy without the Rare shortcut.
- `allocate_requirements`: strict character-scoped physical-copy allocation with
  personal numeric bag bindings. Callers must supply verified equippable bag IDs;
  missing bag evidence cannot establish readiness. Ownership and readiness share
  one feasible assignment, prioritizing ready slots then remaining ownership.
  Unit indices are temporary observation indices, never permanent identities.
  Indistinguishable matching units retain ambiguity. Inputs are validated slot
  records from the catalog/workspace boundary and fictional or supplied snapshots.
- `core/guide_catalog.py`: duplicate-key-rejecting JSON decode, detached v2 candidate
  validation, atomic in-memory publication, revision history conflict checks,
  strict slot/state/requirement validation, public source kind/URL/evidence checks,
  resource job/slot checks, supported main/sub legality and Rare-copy restrictions.
  Canonical imports reject alias collisions before constructing slot maps.
  Production validation requires explicit DT/Refresh idle coverage dispositions
  for 22 jobs; gaps remain gaps. Other applicable role coverage remains a T7
  authorship obligation, not a claim established by schema acceptance.
- Catalog compositions distinguish `loadout`, `partial_loadout` and
  `equipment_options`. Options cannot materialize into a simultaneous target.
  Source-grid placeholders stay omitted. Unknown and intentional empty remain
  distinct states. Resource IDs and supplied hand-type evidence determine the
  supported main/sub checks; unknown legality rejects playable certification.
  This is not a complete game legality or numerical-stat engine.
- `normalize_legacy` is display-only and copies its inputs. Only a complete exact
  historical snapshot proves a revision association; old ring eligibility strings
  cannot infer occupied slots. Conflicting explicit references remain conflicting.
  `resolve_reference` returns the saved snapshot when a revision disappears;
  current default ordering never adopts a newer revision.
- `core/gear_workspace.py`: separate `gear_workspace.json`, schema version 1,
  under the existing `data_dir` policy through `WorkspaceStore.for_user`.
  The core is not wired to automatic app startup or to any legacy writer.
  `prepare_target` snapshots the complete revision, conceptual context and sources.
  Personal overrides/bindings remain separate; `prepare_adoption` returns a detached
  proposal plus before/after records. Only an explicit successful save publishes it.
- Workspace loads distinguish missing, valid, recovery available, unsupported,
  corrupt and unavailable states. Loading never repairs or saves records. Newer
  primary versions block editing even with a usable older backup. Recovery requires
  explicit `accept_recovery=True`; rejected primary bytes are retained as uniquely
  named evidence. Invalid primary/backup and leftover transaction files are retained.
- Workspace saves validate/serialize before publication, use a unique transaction
  temporary file, flush it, back up the previous primary and replace atomically.
  An OS sidecar lock covers generation check through replacement. The lock file
  stays in place and OS locking releases on process exit. Stale or concurrent
  cooperating writers fail with `WorkspaceConflict`; the unsaved proposal remains
  in `pending`, separate from committed `data`. Arbitrary external writers that
  ignore the lock are outside writer isolation; changes before save are detected.
  Failed backup copies can change backup bytes, while failed saves before primary
  replacement preserve authoritative primary and memory. This limitation is tested.
- Existing `gear_guides.load_catalog` continues to load/validate the shipped v1
  catalog. Its Guide-page failure handling displays a local diagnostic and safely
  tolerates refresh. No new feature layout or T4 interaction was implemented.

## Concrete schema/API decisions

The T1 JSON fragments were abbreviated examples. Implemented targets retain
`snapshot` as the full revision including its `id` and `set_id`, plus
`set_snapshot` and `source_snapshots`, so context/provenance survive catalog removal.
Navigation-only `default_revision_id` is excluded from the set snapshot.

V2 revision metadata uses `label`, `equipment_version`, `version_order`, `origin`
(`source_adaptation` or `nexus_recommendation`), `currency`, `resource_fingerprint`,
`verification` (`status`, `checked_on`, `scope`), `source_ids`, `assumptions`,
`rationale`, `composition_kind` and `slots` or `options`.
Conceptual sets use `id`, `jobs`, `purpose`, `target`, `context` and optional default.
Source records use `id`, `kind`, `url`, `title`, `locator` and `accessed_on`.
Fictional source/evidence shortcuts require explicit `fixture=True` candidate
validation; production candidate validation rejects those shortcuts.

Workspace targets require stable ID/character/set/revision identity, the complete
snapshots, `overrides` and `bindings`. Draft persistence validates stable ID,
integer revision, character, owned/planning mode, slot states, observed/assumed
requirement origin, scenario, source references and bindings. This schema does not
implement the builder, ownership freshness evaluation or output generation.
Callers can supply existing character keys to enforce identity resolution.

The shipped `resources/gear_guides.json` remains unchanged at v1. V2 candidates
use `CatalogStore.prepare(raw, items=..., hand_types=...)`; they are not passed to
the legacy picker. T7 authoring and later UI integration must supply the real
candidate, verified resources and required coverage evidence. This core does not
certify the current 376 entries or provide a finished 22-job catalog.

## Acceptance fixtures and validation

`tests/core/test_guide_core_v2.py` covers all eight T1 compatibility procedures:

| Procedure | Implemented offline oracle |
|---|---|
| COMPAT-OLD-01 | Assert legacy Database/Settings/JSON helper bytes match pinned HEAD; fictional save/edit and both recovery paths preserve UTF-8 workspace/backup/evidence bytes; new reader reopens bindings |
| COMPAT-ALIAS-01 | Duplicate aliases reject, paired aliases retain two slots, slash eligibility stays ambiguous |
| COMPAT-COPY-01 | Two physical rings, shortage, moved/designated bags, other character, identical-copy ambiguity |
| COMPAT-POLICY-01 | Same-copy augment requirements; Rare selector/rank distinction; exact path/augment multiplicity |
| COMPAT-REV-01 | r2 addition/default ordering, r1 retirement/saved fallback, immutable conflict after retirement, detached adoption and successful/failed adoption saves |
| COMPAT-WRITE-01 | Serialization/temp/backup/replace failures for target/draft proposals; partial temp-flush/backup failures; unchanged primary/memory; safe retry/reopen |
| COMPAT-VERSION-01 | Missing/corrupt primary/backup, newer primary/backup, explicit recovery with evidence, uncommitted temporary debris ignored |
| COMPAT-WRITER-01 | Stale generation rejection and actual second process holding the OS lock during a competing save |

Additional fixtures cover equipment options, personal composition provenance,
ten-slot partial sources and Shell assumption, ranged-grid placeholders, illegal
staff/shield and legal staff/grip control. Both import orders and original guide/
selector tests run. The preferred allocation algorithm is checked against an
independent exhaustive oracle over all 729 three-slot/two-unit candidate graphs.
The Qt regression checks a catalog error cannot mutate targets or crash refresh.

The requested `py -3 -m pytest -q -rs` was attempted. The WindowsApps `py.exe`
alias was inaccessible. Tests use the existing installed interpreter instead:

```powershell
& 'C:/Users/Jason/AppData/Local/Python/pythoncore-3.14-64/python.exe' -m pytest -q -rs
```

`TEMP`, `TMP` and `VN_DATA_DIR` were explicitly directed to a dedicated writable
temporary root under this chat's visualization workspace. No live player database
or Settings instance was used. The first sandbox full run reported **698 passed,
2 failed, 0 skipped**: pre-existing native junction creation and actual UDP loopback
fixtures failed under sandbox restrictions. Both passed outside the sandbox
unchanged (**2 passed**). The first full native run passed **709 passed, 0 skipped**.
Final exact-source full native rerun: **709 passed, 0 failed, 0 skipped in 91.07s**.
The focused guide/selector/core/Qt suite passed **182 passed, 0 skipped** before
the final snapshot metadata checks; the affected core/Qt suite was then rerun
successfully (**51 passed, 0 skipped**) before the final full native rerun.
`git diff --check` passed. HEAD remains `5657f20`; bundled catalog, legacy
persistence modules and staged GearSwap files have no tracked diff.

## Remaining gates

T4+ UI/item cards, T5 numeric effects, T7 production catalog authoring, calculator/
builder/output and any real-data import/migration are not implemented in this
slice. Their approved task dependencies and visual/evidence gates still apply.
Manual app/game verification, frozen builds and installed executable checks have
not been performed. Commit/push/build/install/release and GearSwap activation
remain separately gated. Windower and player Lua remained read-only.

Resume from the accepted T1 packet and this handoff; do not repeat resolved
planning or infer permission to activate the staged GearSwap system. Keep current
untracked planning documents and `.codex-remote-attachments` intact. Any future
commit must account for the installed post-commit build/relaunch hook.
