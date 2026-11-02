# GearSwap bundle T4: staged SMN integration

Date: 2026-11-02. Branch: `codex/sets-copy-fixes-review`. Base commit: `6397caf`.
Status: staged components implemented and offline-validated; T4 remains open for
installed-runtime host services and live identity verification. Source captured
in the commit titled `GearSwap: stage managed bundles and consolidate tonight's tests`.
No activation, push, publication, executable build/replacement, or installed file edit.

This continues the approved stage plan. No Office Hours or settled architecture,
Lag Mode, display taste or automation questions were reopened. The user authorized
the next phase after T3. Personal profile conversion remains T5.

## Implemented staging components

The [staging README](../staging/gearswap/README.md) describes module APIs and
host obligations. New modules cover explicit binding, bounded readiness,
candidate-before-framework ordering, guarded timers/callbacks, ownership-aware
rollback, actual SMN schemas and command IDs, resource eligibility, the Mote
compatibility adapter and an inactive entry template. The existing restricted
reader remains the only interpretation of managed player source.

The Windows checked-reader service uses read-only native handles. It rejects
profile traversal, unexpected filenames/streams, reparse points and final-path
redirection; verifies directory/file types; bounds reads; and closes handles on
success/failure. Tests use fictional profiles in temporary directories, including
a real junction pointing outside the selected profile. No active Lua is read as
an executable managed profile.

Native service injection is deliberate, but it is unfinished installed-runtime
wiring: the probe supplies control snapshots, monotonic time, timers and the
inventoried legacy source loader. A current binding/alias snapshot service for
Windower has not been implemented or verified. Unknown controls must not be
treated as absent to bypass that requirement. Windows native-file tests use the
available LuaJIT host; running Windower's 32-bit ABI/access still needs testing.

## Pact-gear investigation and repair

Reproduced the original private regression before implementing the repair:
lag OFF called undefined `equipBPGear`; lag ON emitted `EquipBP` without an active
handler. The active Mote library already has `handle_actions`, filters,
`get_pet_midcast_set`, default equipping, post overlays and cleanup.

The staged repair keeps normal pet-midcast processing through Mote in both lag
modes, removes the redundant undefined-helper path, and uses that same full
pipeline for the existing 0.5-second compensation intent. Only Blood Pact
midcasts request compensation. Compatibility `EquipBP`/helper calls can act only
on the current guarded pact context, never arbitrary named sets. Completion,
replacement, pet change, lag toggle or teardown invalidates pending work.

`state.lagmode` is authoritative, initially true, with the profile value defining
its reset default. Existing direct and Mote-toggle command spellings plus the
neutral managed command ID address that mode. No `LagMode` authority remains in
the adapter. Gear handling and the legacy display read the same mode.

Siphon keeps the existing finite action command builder but runs its legacy
in-place assignment against a transient set graph. The actual Siphon precast
selector combines the captured day overlay into a working set. Fire, Light and
Dark contexts were compared without modifying the prepared canonical graph.

These are approved dependency/parity repairs. No unattended action feature or
archival helper implementation was imported. The formerly broken compensation
pass is an intentional correction and still requires actual game timing checks.

## Lifecycle findings and evidence

Mote conditionally defines `file_unload`. Leaving the bootstrap unload hook in
place during Mote initialization suppressed its framework cleanup and caused a
recursive teardown through Nova's captured unload hook. The adapter now lets
Mote define its cleanup, captures that complete framework chain, and restores
the controller as the external unload owner. The controller also rejects
reentrant stop during cleanup and invalidates callbacks before releasing anything.

Ownership cleanup separately covers partial legacy setup, registered event IDs,
Organizer's unhandled-command registry, native HUD objects, controls and an owned
weapon lock. A cleanup exception does not prevent the remaining releases.
Bindings acquired during setup restore their prior payload only if still owned;
unrelated keys and intervening owners' changes survive. Late sidecar settings,
key definitions and `init_gear_sets` overrides were injected through Mote's real
sidecar path; managed definitions and final profile preferences take precedence.

Offline probe evidence is private at:
`%USERPROFILE%/.gstack/projects/Grimdarts-VanadielNexus/stage4-smn-20261102/report.json`.
It records assertions, not personal equipment. Current legacy gear is copied only
in sandbox memory for exercising the adapter; this is not a converted profile or
an independent T5 canonical parity result.

- Four contexts: SMN with unspecified subjob, SCH, RDM and WHM.
- 32 pact cases per context: eight physical/hybrid/magical/ward/healing/debuff
  actions, low/high pet TP, accuracy and burst states. Compensation gear sequences
  match the corresponding normal Mote pet pipeline. Both lag modes work in the
  sandbox, with identical immediate gear and no OFF compensation pass.
- Seven injected failure points: candidate preparation, pre-entry, Mote globals,
  job setup, control attachment, publication and an owned event after ready.
  All clear ready/resources, restore controls and support a clean retry.
- Repeated start/reload/unload, waiting cancellation, timeout/retry, stale timers,
  omitted optional bridge/automation, M-layer compatibility, weapon lock,
  Mote show-set filters and immutable Siphon day overlays are covered.
- Read-only SHA-256 comparison against T2: **35 dependencies checked, 0 changed**.

The expanded T3 key allowlist includes baseline numpad and punctuation chords and
corrects `%` documentation to chat suppression. This is a required baseline
compatibility correction within T4, not a new controls feature.

## Remaining T4 and activation gates

### Pre-commit review follow-up

The final commit review repaired these staging defects and added regressions:

1. A guarded/reentrant setup abort could resume through attachment/publication.
   The controller now checks the active generation after every external phase.
2. Generic working copies cloned GearSwap's identity-sensitive `empty` sentinel.
   Mote/Siphon working copies now seed that sentinel into their copy memo.
3. A control-snapshot exception could interrupt environment restoration during
   teardown. Per-control snapshot/restore now participates in aggregate cleanup.
4. Child paths using slot aliases or case variations could bypass mount collision
   detection. Collision checks normalize GearSwap slot aliases and case while
   preserving the actual exported path spelling. Slot-named child mounts also
   reject empty/omitted parent slots instead of turning omission into an equip request.
5. Parsed-input limits did not bound catalog/base copy amplification in direct
   GearSwap use. A separate 100,000 copied-value/table budget now bounds reference
   expansion, inherited provenance/spans and runtime clones. A small 32-reference
   fixture with a tightened budget proves rejection before excessive allocation.
6. Resource eligibility now accepts raw bitmasks and Windower's processed Set
   fields, indexes long resource names and rejects duplicate-name ambiguity
   deterministically. The installed `resources.lua` conversion was inspected.
7. The native directory-reader handles request directory-list access as well as
   attribute access so the non-delete-sharing policy participates in share checks.

Guarded setup callback failures also unwind the initializer immediately, and the
adapter checks activity after legacy loading/initialization. Ready-state identity
polling remains throttled and identity-loss teardown now gives a retry diagnostic.

Review coverage: primary source review, independent native adversarial review
(rechecked the fixes) and a completed Claude Code adversarial challenge, session
`1975a80e-4628-4876-9afe-4b194bae45e9`, reported model `claude-opus-5-5`.
The separate outside structured pass timed out at 540 seconds and provides no
coverage. Full outside output and disposition metadata are private in the
project's `.gstack` store. Native command-queue read-your-writes semantics and
compound/delayed control grammar remain explicit installed-host verification
gates; the offline ledger is synchronous and cannot prove those live properties.

Final pre-commit suite: **659 passed, 0 skipped in 71.09 seconds**. This supersedes
the 642-test implementation run below and interim review runs. The added cases exercise
failure/cancellation during setup, cleanup-service errors, real-adapter sentinel
identity and canonical/alias/case slot-path conflicts. Changes remain inactive.

Tonight's consolidated user checklist is
[TONIGHT-TEST-CHECKLIST-2026-11-02.md](TONIGHT-TEST-CHECKLIST-2026-11-02.md).

Final verification commands:

```text
py -3 -m pytest -q -rs
642 passed in 69.21s (0:01:09), 0 skipped

py -3 -m pytest -q -rs tests/core/test_gearswap_lifecycle.py tests/core/test_gearswap_profile_files.py tests/test_gearswap_smn_integration.py
63 passed in 3.13s, 0 skipped

LuaJIT syntax compilation: 15 staged Lua files/templates, 0 failures
```

The initial implementation suite consisted of 477 existing tests, 102 T3 tests
and 63 T4 tests. After review regressions, the final 659-test suite consists of
477 existing tests, 110 reader/resolver tests and 72 lifecycle/native/integration tests.
`git diff --check` reported no errors. These checks do not run the game or change
the installed executable. The private report contains the four context results,
seven failure/retry results and baseline hash readback.

Finish and verify the installed-runtime host service bundle: current control
snapshots/collision handling, monotonic timing, trusted staged-source loading and
the checked-reader's actual Windower environment. Probe
`windower.ffxi.get_player().name` and `get_info().server` live; no real server ID
has been inferred from mocked `server = 1`, character folders or area names.
The documented server field is confirmed in
[Windower's official definitions](https://github.com/Windower/Lua/blob/dev/definitions/windower.lua),
which does not establish its availability in Jason's running instance.

Then complete T5 personal conversion and independent canonical/action comparisons
against T2. Actual packet timing, representative pacts/summons, setup failure,
reload/job change/unload and optional integrations need live confirmation before
activation. The template is intentionally inactive and fails closed without host
services. No existing entry is renamed, deleted, or shadowed automatically.

Resume prompt: Read the approved design/review, data contract, SMN baseline and
T3/T4 validation reports. Continue T4's installed-runtime host/service verification
without changing Windower files. Preserve the validated SMN/Mote adapter and pact
repair; do not claim T4 complete or begin activation from offline results alone.
T5 personal data conversion and full legacy parity are still pending.
