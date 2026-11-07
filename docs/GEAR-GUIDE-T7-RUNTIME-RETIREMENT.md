# Gear guide runtime retirement - implementation (2026-11-05)

Claude alone, started by Jason in chat ("start the next T7 slice"). Application code and tests only.
No catalog data, production bundle, resources or hands changed. Implements
[GEAR-GUIDE-T7-RUNTIME-RETIREMENT-DESIGN.md](GEAR-GUIDE-T7-RUNTIME-RETIREMENT-DESIGN.md).

## What changed

- `core/guide_catalog.py`: new `retirements(catalog)` builds the retired-revision map from
  `authoring_amendments` and fails closed (`CatalogError`). `validate_catalog` attaches it as
  the derived `_retirements` key. New `effective_revision_id(catalog, id)`. `resolve_reference` status
  order is now `unavailable_source`, `conflicting_revision`, `retired`, `current`.
- `core/gear_guides.py`: `revision_tree` never lists a retired revision. Each of the 25 affected sets
  now shows one revision with no version pills. A remembered retired pick falls through to the head
  and nothing is written to settings.
- `ui/guide_revisions.py`: a saved target on a retired revision shows the amber Caption banner
  (DESIGN.md warning tone #F59E0B), the " · outdated" combo suffix and "Review update…", which goes
  straight to the effective head through the existing `RevisionReview`/`prepare_adoption`. Edit is
  disabled with a tooltip. Slots whose curated requirement changed show "Outdated requirement"
  instead of being graded.
- `tools/prepare_guide_catalog.py` (not in the design's file list; see Deviations): new
  `serialize()` keeps derived `_`-prefixed keys out of saved candidates.

## Deviations from the design, and why

1. **The authoring tool writes validated catalogs to disk.** Without a fix, `--output` would have
   persisted `_retirements` into the candidate file, which the design forbids. Fixed with
   `serialize()` and a regression test. Behaviour is otherwise unchanged.
2. **"Every set has exactly one effective revision" applies only to sets with at least one
   retirement.** Applying it to every set would reject existing fixtures that have two unretired
   revisions and no amendments. Design test 3 requires those to behave exactly as before. The real
   candidate passes either way: 547 revisions - 27 retired = 520 sets.
3. **`resolve_reference` still returns a 2-tuple.** For `retired`, the head comes from
   `effective_revision_id`. This avoids a return value whose length depends on the status.
4. **A personal override on a changed slot is graded normally and still shown.** The user's own
   requirement is not outdated curated data. The literal design text would have hidden the
   override behind "Outdated requirement". The code review flagged this case.
5. **The banner also shows while browsing a set whose saved target is retired**, and the button reads
   "Review update…". Previously only a short note showed. This follows rule 3 ("Outdated is always
   visible").
6. **Duplicate amendment batch IDs are rejected.** The UI derives the date and plain reason from
   the batch ID.

## Code review (/code-review medium) disposition

Fixed: override text/grading (4), explicit version pick honoured before the retired-head default,
banner in browse mode (5), duplicate batch IDs (6), ISO date parsing via `date.fromisoformat`, and a
cheap id lookup before `resolve_reference`'s snapshot copy.

Not changed, recorded as follow-ups:
- Amendment history is not part of the immutable-history checks. A later candidate that drops an
  amendment would quietly un-retire a revision. The T7 count tests (27 retired / 512 effective)
  would catch it today. A durable guard belongs in `save_candidate`/`CatalogStore` in its own slice.
- `prepare_target`/`prepare_adoption` still accept a retired revision id. Only the picker and UI
  prevent it. A core guard would be stricter.
- Plain banner reasons are mapped per batch ID, as the design specifies. Unknown batches fall back to
  the amendment's own reason.
- The cycle check cannot fire because version order strictly increases. The design asks for it, so
  it stays as a second guard.

## Tests

`tests/core/test_guide_retirement.py` (new, 23) and 9 additions to `tests/ui/test_guide_revisions.py`
cover design tests 1-14, plus the authoring-save, override and browse-mode cases. These tests were
written first and confirmed failing before the code existed (RED): import error, then 7/7 UI
failures.

| Run | Result |
|---|---|
| Focused native (pre-review) | 808 passed / 0 failed / 0 skipped, 72.92s |
| Full native (pre-review) | 1533 / 0 / 0, 162.28s |
| Focused native (final) | 811 / 0 / 0, 72.79s |
| Full native (final) | 1536 / 0 / 0, 165.62s |

The harness and logs are in `.t7-retirement-checks/`: isolated launcher, fictional Windower, inventory
seeding off, unique TEMP/TMP/VN_DATA_DIR/basetemp. Readback is in `.t7-retirement-checks/readback.json`:
- the candidate (ca787650...1926) and production (b57b6bb3...4300) are unchanged;
- resources 863 and hands 55/v19 are unchanged;
- only the five named files changed, plus the one new test file;
- each file keeps its own line endings (`gear_guides.py` CRLF, the rest LF), with no trailing whitespace.

## Still open

Manual check of design section 5 cases 1-3 in the built app. This is listed for Jason in
[PRE-RELEASE-CHECKLIST-PENDING.md](PRE-RELEASE-CHECKLIST-PENDING.md) and is not tested. Production is
still v1, so players see none of this until the v2 catalog replaces it. Not committed, pushed, built
or released.
