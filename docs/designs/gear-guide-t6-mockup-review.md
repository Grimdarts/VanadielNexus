# T6 item-card and existing-set analyzer visual review

Date: 2026-11-03. Status: APPROVED by Jason in the T6 chat. He asked to work
with this direction and refine each section after later committed/live testing.
T1–T5 decisions remain accepted. This is the concrete T6 mockup gate, not a
replacement architecture review. T6 implementation is now authorized; commit,
build and installation remain separate steps. The existing attention section
stays the initial Sets tab to preserve its established workflow; Equipment
analysis is adjacent, and item details are available from the grid/context menu.

## Preview

Interactive conversation preview:
`C:/Users/Jason/.codex/visualizations/2026/11/03/01a1a3bd-153e-7b42-9b45-cbd2d66f7702/gear-guide-t6-review.html`

The preview uses fictional observations and illustrative selections. Arithmetic
demonstrates the accepted rule boundaries; it is not a new calculator test or
a certified playable composition. Preview-state controls and abbreviated raw
description placeholders belong to the review surface only. Actual cards must
retain the complete available description, metadata and unsupported text.

## Proposed placement and access

- Keep the Sets character/job context, read-only tree and 16-slot grid. Add an
  Equipment analysis section below the grid; retain existing attention and copy
  fixes through an adjacent section selector. Selecting either is navigation only.
- Reuse one item-card surface, opening at the right edge of the set content. In
  Qt it must be constrained to the available screen/window bounds, scroll when
  needed and respect text scaling. Do not add a permanent window per item.
- Hover dwell proposal: 350 ms. Warm presentation budget remains 100 ms after
  dwell. The preview illustrates delayed opening; final Qt transient dismissal
  must allow moving into the card and hide it after leaving trigger/card, unless
  explicitly kept open. Keyboard focus alone must not steal selection.
- A selected cell/row plus Item details, Enter or the item context menu opens
  the same information without hover. Keep existing selection/double-click/edit
  behavior; do not repurpose an existing edit gesture. Keep open permits reading
  long content. Escape/Close restores focus to the invoking cell/row/control.
- At 900×600 and 130% text scale, the existing Sets drawer pattern should provide
  a bounded right overlay rather than squeezing all columns. At wider sizes use
  the established details panel. Verify exact fit in Qt after approval; the inline
  review reflows the tree below 760 px and is not pixel-equivalent Qt evidence.
- Reuse the card in relevant Gear/Guide item rows through explicit details and
  context actions without changing existing source/adoption/edit actions. A guide
  target shows requirements separately from an observed copy; generic items never
  acquire an arbitrary copy binding. T6 introduces no replacement picker.

## Card content

Full item name/ID, canonical selected slot, level/jobs/equipment information,
source-described base effects and full raw description form one group. Observed
character/copy/bag/quantity/snapshot time/augments/rank/path form a separate group.
Declared set or guide requirements/designated bags form a third group. Missing
metadata is unavailable, never inferred. Same-name observations remain distinct.
Ambiguous allocation displays generic base information and unresolved identity,
not invented observed augments. The Pet/rank review state illustrates two Nyame
observations with different ranks/bags; it does not substitute either into the set.
Unsupported rank magnitudes stay uncalculated; Pet/master values remain separate.

## Analysis and interaction contract

- Analyze only the selected read-only declaration. Omitted, unknown and explicit
  empty slots stay different. No automatic filling from currently equipped gear.
  Aliases/inherited slots require resolved precedence. Unsupported runtime
  composition or hand legality shows diagnostics rather than certified totals.
- Owned allocation uses distinct saved observations for the same character. No
  snapshot yields unavailable Owned contributions, not zero or a Planning switch.
  Missing copies never turn requested gear into owned contributions. Readiness
  and ownership are separate; a saved snapshot is not current game state.
- Compare existing set selects a second existing read-only set within the same
  character/job context. Both use one scenario/source/snapshot. Show signed known
  changes only for compatible stat/recipient/unit keys and mark incomplete sides
  and deltas. Unavailable/unmatched keys remain unavailable, not implied zero.
- Keep supported unconditional contributions, condition branches and uncalculated
  effects inspectable. The review shows Refresh, MND, direct magic accuracy and
  all-magic-skills family points; final supported rows follow actual T5 results,
  not an invented universal stat sheet. Master, Pet and Avatar use distinct groups.
- Unity controls use unknown versus explicitly evidenced membership/standing as
  offline scenario inputs. A user's manually entered evidence remains labeled a
  manual assumption, never a live-state observation. Standing and augment rank
  are independent. No unsupported time/weather/buff formulas or fake toggles.
- Inyanga qualifying count is derived, not a manually enabled buff. Evaluate once
  per selection and show the counted pieces. Additional unknown membership can
  keep Refresh incomplete even when the known bonus is precise.
- Every number can disclose its slot/copy, base/conditional origin, rule/evidence,
  units, resource fingerprint and uncertainty. Unknown unscoped effects keep all
  plausibly affected subtotals incomplete. No effective cap or upgrade verdict.
- Source preparation starts on first relevant use or explicit refresh, using the
  T5 coalesced worker. Selection/character/source changes clear incompatible old
  results immediately; both comparison sides publish only for current input
  identity on the GUI thread. Cancel/dispose consumer work on teardown. No polls.
- Loading and failure keep navigation usable and remove stale contributions.
  Refresh retries source preparation without adopting targets or editing data.

## Illustration oracle

Recovery A declares two qualifying Inyanga pieces, two distinct Stikini +1 rings
and Assiduity +1. Recovery B adds a third qualifying Inyanga piece. Other slots
are omitted. Known Refresh excluding unresolved Unity is 3 versus 4 MP per
three-second tick. Verified Unity first place adds 2 to each; another verified
valid standing adds 1 to each. Unknown standing retains unresolved 1–2, never
chooses a maximum. Comparing A minus B shows -1 known, explicitly partial.
Both have ring-only MND 16, magic accuracy 22 and all-magic-skills family 16.
Other source fields remain unsupported: these are partial contributions, not
complete character stats. The preview's missing/ambiguous/loading/failure states
illustrate labels; they do not validate allocation or asynchronous Qt behavior.

## Review and validation boundary

Jason accepted this placement/interaction direction in the T6 chat and asked to
refine sections after later committed/live testing. Implementation is authorized
within T6; T7/T8 and build/install/commit gates remain separate.

Source implementation uses adjacent Attention & copy fixes / Equipment analysis
tabs beneath the existing grid, preserving Attention as the default. Cards reuse
one scrollable nonmodal tool per consuming page and fit within the app/screen
bounds. Grid Enter retains its existing slot-panel action; Item details, Alt+I
and the context menu provide the keyboard route to the new card without changing
edit/double-click gestures. Hover dwell is 350 ms, with a 250 ms leave grace.
Source-page renders and measured limits are recorded in the T6 handoff.

The browser tool rejected the local file URL under its protocol policy. No
alternate browser/server route was used to bypass that restriction. Browser
screenshots or browser interaction walkthrough are not claimed. Subsequent
actual Qt source-page offscreen renders at 900×600, 1024×768 and 130% text scale,
fictional-fixture tests and a source UI profiler are available in
`../GEAR-GUIDE-T6-HANDOFF.md`. Human keyboard/hover/screen-edge checks, the complete
app workload, frozen size and game coexistence remain later acceptance work.
