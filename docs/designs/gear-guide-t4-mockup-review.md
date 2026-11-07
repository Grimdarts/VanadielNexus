# Gear Guide T4 visual review

Date: 2026-11-03. Status: APPROVED by Jason in the continuation chat. He accepted
this as a starting point and asked to continue implementation, with refinements
guided by hands-on use. T4 source implementation and offline Qt validation are
recorded in `../GEAR-GUIDE-T4-T5-HANDOFF.md`; installed-app testing remains pending.
Scope: T4 Guide UI and source integration only. T1–T3 decisions remain accepted.

The approved implementation plan requires: "Visual labels/menus require mockup
approval before UI implementation." This review supplies that concrete mockup;
it does not reopen architecture or authorize production catalog authorship.

## Reviewable preview

Interactive source:
`C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a326-580a-7f13-b143-8d737c8aed55/gear-guide-t4-review.html`

Browser-inspected screenshot:
`C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a326-580a-7f13-b143-8d737c8aed55/gear-guide-t4-review.png`

The data is illustrative, including the revision history, character observations,
generic example equipment and verification labels. No playable composition or
current guide recommendation is being certified by this mockup. Stikini Ring +1
is used to make duplicate-slot behavior recognizable. No live player data was read.

## Proposed layout and interactions

- Retain the app's navy/cyan/gold theme, existing Purpose → Set → Version workflow,
  character picker and equipment table. Version labels describe alternatives;
  immutable revision identity appears separately beneath the context metadata.
- Put origin, currency and scoped verification on a compact text line. Show the
  saved revision and availability of a newer recommendation on the following line.
  Do not combine currency and equipment version into a quality rating.
- Preserve the five existing table columns: Item, Status, Slot, Target / assumptions
  and Inventory check. Canonical paired slots appear as Ring 1/Ring 2. Personal
  designated bags appear with requirements; observed location appears in Inventory
  check. Ownership and readiness are distinct when an item moved bags.
- Keep partial/omitted/unknown/intentional-empty distinctions visible. No inventory
  snapshot yields unverified comparison, never an ownership or readiness claim.
- One primary action: Track this revision when untracked, or Review newer revision
  when a saved target has an available update. Navigation alone never adopts it.
- A revision review shows before/after requirements and context/currency changes,
  retained personal bags/overrides and the exact selected target. Saving updates
  only that target after persistence succeeds. Failure keeps the original revision
  authoritative and leaves the proposal available for review.
- Sources resolve the selected revision. One supported reference opens directly;
  several references use a contextual chooser with specific title/locator/evidence
  role. Item wiki navigation remains a separate action. The illustrative preview
  uses source-detail placeholders rather than fabricated live guide URLs.
- Selecting a row and choosing Edit selected target opens a slot-specific personal
  override/bag editor. Curated revision requirements remain visible and immutable.
  The preview shows this panel inline for review; final Qt dialog placement follows
  existing application conventions. Unsupported ownership assumptions stay visible.
- Legacy ambiguous ring eligibility remains preserved and unresolved, with tracking/
  adoption unavailable until a separately reviewed exact association/import exists.
  Options lists remain reference collections and cannot become simultaneous targets.
- Catalog errors remain local to the Guide page. New mutations are unavailable and
  existing personal targets are preserved. No automatic recovery or adoption occurs.

The Preview state selector belongs to the review surface only. It is not a proposed
application feature or additional runtime mode. It exposes saved/untracked targets,
moved duplicate ring, unknown item, missing snapshot, unresolved legacy association,
source options, catalog error and failed adoption save states.

## Verification

An isolated headless Chrome profile opened the local fictional preview. The check
exercised adoption, failed save preserving r1, explicit bag rebinding, source details,
tracking guards and missing-snapshot behavior. Layout checks passed at 1024, 736
and 320 pixels with no page-level horizontal overflow; the equipment table retains
its own horizontal scrolling at narrow sizes. Browser exception count: zero.
The screenshot was inspected. The first sandbox browser attempt timed out; the
same check passed outside the sandbox with a dedicated profile.

No app/core/test source was changed for this mockup. No database/settings instance,
live inventory, Windower file, build, commit, installation or release was used.
The existing T2–T3 result remains 709 passed, 0 skipped; it is source-core validation,
not evidence that the proposed T4 Qt interactions have been implemented.

## Approval and next implementation

Historical gate at mockup preparation (now satisfied): Jason reviews the layout, labels, source behavior, personal-target editor
and revision review. Record his disposition here before T4 UI coding. Once approved,
implement these interactions using the T2–T3 core, preserving current legacy usage
and isolated workspace authority, and add meaningful Qt/persistence integration
tests. The production v2 catalog, T5 numerical engine, T6 cards/analyzer and builder
remain later tasks. Real-data conversion and commit/build/install/release retain
their separate authorization gates.
