# Fresh-session handoff: T7 BRD, Nova only

Jason requested the next phase begin in a new session after the GEO milestone.
Continue **T7 candidate authoring with BRD**, the next remaining queue job.
Do not interpret next phase as T8/T9. Begin the work; no new architecture or
delegation interview is needed. Nova owns this batch end to end.

## First reads

1. Repository/global instructions and shared Hindsight context.
2. docs/GEAR-GUIDE-T7-HANDOFF.md, current GEO section.
3. docs/GEAR-GUIDE-T7-GEO.md for latest evidence/validation boundaries.
4. docs/GEAR-GUIDE-T1-REVIEW.md, BRD role/action obligations, and
   docs/GEAR-GUIDE-T7-EVIDENCE.md, original BRD source leads.
5. Candidate, resource evidence, authoring service and relevant tests before edits.

## Current verified milestone

Repository: C:/Users/Jason/Games/VanadielNexus.
Branch: codex/sets-copy-fixes-review. HEAD: 5657f2092c0e0d84331d0741b1518669201e25d4.
Working tree is intentionally dirty: nine tracked files modified by preceding
work, plus substantial untracked app/core/tests/docs/tools and authoring scratch.
Git alone will not show diffs for untracked artifacts. Do not reset, stash, clean,
switch branches, overwrite prior work or assume untracked means disposable.

Candidate: 136 sets / 136 revisions / 218 sources. 128 verified Nexus compositions
(WHM23, SCH28, BLM22, RDM38, GEO17), eight preserved unresolved originals.
Coverage: 225 rows / 67 included / 158 gaps across 17 remaining jobs / zero N/A.
343 detached resource records. Hand registry: 18 entries, hands.2026-11-04.v4.
All earlier immutable records and source amendments remain present.
Production v1 SHA-256:
54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85.
Resource fingerprint:
0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78.

Latest validation: focused114 passed/0failed/0skipped (4.33s); full isolated native
892 passed/0failed/0skipped (114.00s). Actual-resource whole-candidate preparation,
history/resource/production readback and git diff --check passed. These are GEO
milestone results, not fresh BRD tests. Do not rerun unchanged tests merely for
handoff; run appropriate focused/full checks for the new batch.

## BRD work

Reconcile every existing BRD coverage row and accepted role/action obligation.
Keep song potency/duration, instrument and song-capacity/access distinctions,
precast, debuff/casting and any supported niche melee contexts explicit. Inspect
exact cape/Linos/Nyame paths where used. Do not assume instruments, extra songs,
augments, access, ownership, gear tiers or capped totals. Preserve source conflicts,
omissions and options. Assemble complete compositions only when their evidence
and prerequisites are explicit; otherwise retain a named gap.

Back up/hash affected artifacts before changes. Reuse existing exact-ID evidence,
but verify BRD slot/job eligibility and any new hand/instrument classification.
Use tools/prepare_guide_catalog.py / existing save_candidate service to validate
whole-candidate resources and immutable history before saving. Do not publish to
vanadiel_nexus/resources/gear_guides.json.

Read-only actual-resource validation:
py -3 tools/prepare_guide_catalog.py docs/catalog/gear-guide-t7-candidate.json --windower C:/Users/Jason/Games/Windower4

Full tests must use the real-file isolation launcher in the canonical T7 handoff
with fresh task-local TEMP/TMP/VN_DATA_DIR/basetemp, redirected Windower discovery
and inventory seeding disabled. Latest scratch/examples: .t7-geo-checks/.
Never let tests discover/seed player data. Use py -3 on this Windows machine.

## Efficiency and Vesper decision

Jason accepted Nova's recommendation to do the next batch directly. Vesper is
unassigned. Its broad GEO drafts contained errors; the later literal trial passed,
but new-source access/token savings are unproven. Do not restart packet-002,
replay extraction trials, dispatch another agent or redesign team infrastructure.
Keep updates concise. Use existing tools for mechanical work and avoid duplicate
research. No new Vesper prompt is required without a concrete authorized task.

## Boundaries and next handoff

Windower/player Lua remain read-only; never execute player Lua. No commit, push,
build, install, release, production replacement, real-data migration, game command
or Lua activation. T8/T9, human UI/frozen/live acceptance remain separate gates.
No current-BiS, effects/caps, duration, ownership or live-readiness claim follows
from composition validation. Source-access failures are limitations, never N/A.

At the BRD milestone, report exact scope, counts and validation; update the canonical
T7 handoff and BRD report, retain concise Hindsight status, and preserve every
historical source/revision. Do not begin another job implicitly in this handoff.
