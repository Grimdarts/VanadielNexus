# Design: Item cards, equipment totals, and a set builder

Generated through GStack /office-hours on 2026-11-03.
Repo: Grimdarts/VanadielNexus.
Branch: codex/sets-copy-fixes-review.
Mode: Builder.
Status: APPROVED by the user on 2026-11-03 after native and Claude document review. The workflow, conditional-layer scope, owned/planning behavior and delivery order are accepted as the design baseline. Engineering details, supported-stat coverage, performance budgets and visual mockups remain to be reviewed before implementation. No app/Lua implementation, installation, commit, push, or release is authorized by this record.

Related baselines: [verified guide catalog](verified-gear-guide-catalog.md), [guide engineering review](../GEAR-GUIDE-CATALOG-ENG-REVIEW.md), and [managed GearSwap bundles](gearswap-job-bundles.md). This document extends the product scope; it does not replace those decisions.

## Problem and intended experience

Players need to understand an equipment item's actual attributes and augments, distinguish duplicate copies, compare complete equipment choices, and assemble their own sets in Nexus. The user wants a cleaner, styled presentation than the game's item window while keeping the app responsive, the installation small, and game-side overhead low.

The intended flow is: inspect an item card, view an existing set's supported contributions and conditions, try a replacement, see the before/after differences, then save a personal draft set. Reuse one consistent item/stat model so the card, set analyzer, and builder cannot quietly disagree.

## User decisions

- Begin with equipment contributions and an added conditional layer, not a full character, food, buff or damage simulator.
- Distinguish always-active contributions, enabled conditional contributions, and effects not calculated. Let players inspect which pieces and rules contribute.
- Build with owned gear by default; provide an explicit Planning option for unowned equipment and target augments. Hypothetical inputs must never look like observed copies or equip-ready gear.
- Delivery order A selected: prove item cards and totals on existing sets first, then add the builder on that shared foundation. Builder-first was not selected because draft persistence, selection UI and calculation correctness would need to be validated together.
- Keep the current app's visual language. Review compact mockups and placement before implementation; do not turn this into a broad app redesign.
- Preserve exact augmented copies, character identity, designated bags, and one-copy-per-simultaneous-slot allocation. The guide's stable identities and immutable revisions continue to apply.

## Available foundation and limits

Current source provides equipment grids and plain tooltips, read-only parsed GearSwap sets, item/job/slot metadata, and inventory snapshots containing item IDs, bag locations and decoded augments. The Sets allocation code already distinguishes bags and physical copies. The guide format is separately being reviewed to add precise slots and revisions.

Read-only inspection found Windower's local `res/item_descriptions.lua` at 4,972,281 bytes on 2026-11-03. It contains base-description text and is a candidate local source. This does not measure the proposed feature's memory cost or establish complete, up-to-date machine-readable stat rules. The existing item-resource parser does not currently provide a complete stat engine.

Reuse local resource inputs and the existing inventory snapshot; do not bundle a duplicate full item database by default. Reuse or adapt compatible pure matching helpers without bringing Lua execution or UI dependencies into calculation. Source updates, supported languages, ambiguous descriptions and missing resources need explicit handling in engineering review.

## Item cards

A shared card should show full item name, relevant equipment/level/job information, organized base effects, and the selected copy's observed augment/rank/path details. Character, designated/observed bag, quantity and snapshot age must remain clear when a specific owned copy is being shown.

Keep three distinct kinds of content visibly separate: source-described base attributes, observed copy data, and planned/guide requirements. If only an item ID or generic name is known, show generic information rather than guessing which owned copy it represents. For unresolved duplicate copies, show the ambiguity and let the player choose.

Preserve raw special-effect text whenever grouping or calculation is unsupported. Formatting must not silently discard conditions or imply an unverified numeric interpretation. Icons are optional follow-up presentation; this phase does not require extracting or shipping a full image collection.

Use a short hover delay and reuse one transient card rather than opening a persistent window for every row. Provide an accessible focus/click route to the same details and a way to keep lengthy content open. Essential information cannot be hover-only; preserve existing double-click/edit and selection behavior. Exact interaction, delay, dimensions and placement are mockup/engineering decisions, including screen-edge positioning and text scaling.

## Calculation contract

### Supported contributions, not asserted character totals

Compute only stats whose meaning, units and combination rules have been verified. Potential priorities include core attributes, HP/MP, accuracy/attack contributions, defensive values, Refresh/Regen, haste, multi-attack, Store TP, casting and pet effects. This is a candidate support list, not a promise that every listed stat is immediately supported on every item.

Separate different stat families and recipients. Master and pet stats, flat and percentage values, and differently stacking categories must not be merged merely because their labels look alike. Do not derive effective character accuracy, damage, healing, delay reduction or other outcomes from equipment-only sums without the required contextual model.

Every reported number has a contribution trail: selected slot/copy, base versus augment source, applicable rule and condition. Keep rounding and internal units explicit where relevant. A displayed description or rank alone is not proof of an augment's numeric contribution.

### Conditions and completeness

- Show supported unconditional equipment contributions separately from conditional contributions and unknown effects. The conditional component is not always an arithmetic addition: supported replacement, multiplier, cap or stacking rules must be applied in their verified order and explain their result.
- Determine supported conditions from selected gear where sufficient, such as qualifying set membership. Count distinct equipped pieces according to that bonus's actual rules; do not infer set bonuses from similar names.
- Use explicit offline scenario inputs for supported state-dependent conditions, such as a threshold, time/weather context or required buff. Unknown conditions remain unknown, not silently on or off. Mark manually enabled assumptions; do not claim they are current game state.
- Turning on a required-buff condition applies the supported equipment effect, not all character bonuses granted by that buff. Full buff/trait/food modeling remains a separate future layer.
- Keep unknown or unsupported effects visible and attach completeness to the affected result. Do not present an incomplete result as zero, an exact total, a reliable cap result or an upgrade verdict. An item may have a known contribution for one stat and an unresolved effect for another.
- Caps and stacking rules need individual evidence. Show raw equipment contributions and the applied equipment-scope limit only when the necessary rules/context are known. Do not treat a character-wide cap as an equipment-only cap.

### Set and comparison context

The analyzer totals the declared equipment selection, not the player's guaranteed currently equipped state. An omitted Lua slot means no request for that slot, not proof of an empty slot. Distinguish declared empty, omitted, unresolved and selected slots. A partial set/overlay can show its known contribution but cannot claim a complete loadout total unless explicitly composed with a known base.

Use slot replacement precedence to compose supported base/overlay selections; never add mutually exclusive action sets or double-count aliases/inherited slots. Preserve the distinction between precast, midcast, idle and other action contexts. Runtime logic not captured by the read-only snapshot remains explicitly unresolved.

Compare candidate and baseline under the same explicit scenario. Show positive/negative changes for comparable stats, but do not infer that a stat increase is an overall upgrade. If one side is incomplete, mark the comparison accordingly. Changing conditions changes both sides consistently or clearly identifies two intentionally different scenarios.

## Set builder

Start from an inspected set, a guide revision, a saved draft or a blank equipment grid. Choose character/job and relevant set purpose/context. Default to owned copies that fit the slot/job; retain exact augments and bag designation, and show stored/unreachable copies distinctly from equip-ready ones. Do not automatically move inventory or equip anything in game.

Planning mode explicitly permits missing equipment and specified target augments/ranks/paths, using verified legal item/slot data and supported augment information. Do not invent achievable augments or treat an assumption as an observed rank. Each planned slot retains its provenance and unknowns. Mixed owned/planned sets stay visibly hypothetical.

Allocate observed physical copies across the entire selection. One item cannot fill two simultaneous slots. Two identical copies in the same bag may satisfy quantity but do not establish deterministic identity for future Lua selection; preserve ambiguity and support designated bags where needed. Hypothetical duplicates need the required count visibly recorded.

Validate supported cross-slot equipment restrictions, including main/sub and ranged/ammo compatibility under the declared job/context. An illegal or unresolved combination may remain inspectable as a draft, but must not be presented as an equip-ready loadout.

Update supported totals and same-scenario deltas when equipment or assumptions change. Keep condition overrides inspectable and reversible. Unsupported effects remain visible; a draft cannot silently become a live profile or a validated playable set.

Save drafts as character-associated Nexus-owned data with stable draft identity. Preserve unrelated player data; use the existing database/persistence patterns, with any required schema change reviewed before implementation. Saving a draft must not alter a guide, tracked wishlist target or source Lua. Snapshot the chosen guide revision/requirements rather than following a mutable latest target. Reopening stale/missing resource references shows a diagnostic without destroying the saved draft.

Preserve the selected copy's observations and snapshot identity/time as saved. On reopen or inventory refresh, compare those saved observations with the latest available snapshot for the same character. Flag moved, missing, re-augmented, rank-changed or ambiguous copies; never silently rebind, adopt upgraded augments or substitute another character's copy. The saved draft remains recoverable. With no suitable fresh snapshot, say what was known as of the recorded snapshot rather than claiming current ownership or readiness. A player may explicitly update a binding or convert a missing slot to Planning; that choice is not automatic.

Offer explicit copyable Lua with destination/context guidance, preserving supported slot names, actual augments and designated bags. Do not emit synthetic observed rank text as a GearSwap augment. Normal active-set output requires resolved, supported legal selections and sufficiently confirmed copy bindings; block it with actionable diagnostics for illegal, missing, ambiguous or unresolved selections. Planning output is a separately labeled, fully commented reference scaffold: unobserved target augments/ranks and missing pieces are hypothetical comments, never active equipment assertions. It cannot be presented as a ready-to-equip set. Unsupported/dynamic compositions need honest limits. Exact output syntax and validity checks are an engineering gate; there is no automatic write into current player Lua or activation.

## Size and performance policy

- Read local resources through a lazy, bounded cache or index; do not parse all descriptions or scan all inventory anew on every hover.
- Share normalized item/effect data between cards and calculations. Invalidate it when the relevant source identity/version changes; include selected augments and condition inputs in result-cache identity where applicable.
- Recompute on user selection/condition changes for the selected set, not on a perpetual timer. Keep expensive first-load/index preparation off the interactive hover path. Avoid stale results from earlier selections after asynchronous work completes.
- Add no game-side polling, inventory scan or network request triggered by hovering, calculating or drafting. Offline planning works with available cached/local resources; missing data is reported rather than queried from the game repeatedly.
- This is manual set construction and bounded comparison, not exhaustive search across every possible equipment combination. Automatic optimization and damage simulation are out of scope.
- Do not add a heavyweight runtime, image pack or bundled external database without a measured need and separate review. Required curated rules must be traceable and their licensing/distribution suitability checked before reuse.

Before implementation completion, measure first-open/index cost, warm card latency, repeated slot-change responsiveness, app memory/cache growth and frozen executable size against the current baseline on the same machine/data. Set numeric acceptance budgets during engineering review before coding; no performance or install-size result is claimed yet. No new game work is planned, but app/game coexistence still needs a home-session check.

## Delivery slices and dependencies

1. **Prove the data and rules.** Inventory available metadata, validate a small representative set of base/augment/conditional rules, define supported/unknown states and shared contribution provenance. Check existing stat-parser prior art before inventing a new grammar; do not adopt another project's correctness or code without review.
2. **Existing-set cards and analyzer.** Review compact mockups, integrate the shared data into familiar item/set views, validate copy identity, totals, condition assumptions, comparisons and responsiveness. This slice compares two existing read-only selections under the same scenario; it does not include a replacement picker, editable set, Planning editor or draft persistence. Support representative item types and job contexts before claiming broad coverage. Clearly publish the supported-stat boundary.
3. **Owned/planning builder.** Add selection, independent draft persistence, quantity/slot checks, saved per-draft condition overrides and copyable output on the proven model. Reuse the scenario controls already present in slice 2; this slice adds persistence and editing of draft-specific assumptions rather than deferring all condition controls until the builder. This is part of the intended deliverable, not a discarded future wish.

The verified-guide project remains active. Accurate local item analysis need not wait for all 22 job guides; using a guide as an authoritative target depends on its verified revision. The new feature must not bypass the catalog's validation/quarantine or silently revise the accepted guide design. Neither the 22-job catalog nor full stat coverage is considered complete just because a representative slice works.

Slice 2 has its own acceptance gate: approved cards/details access; exact-copy identity, designated bags and duplicate ambiguity; correct supported totals and condition provenance for representative existing sets; scenario inputs and supported condition toggles; honest unknown/partial-set handling; same-scenario comparison of two existing sets; and the agreed performance checks. No builder claim is made at that gate. Slice 3 additionally requires replacement deltas, owned/planning selection, save/reopen and inventory-drift handling, duplicate/cross-slot validity, and safe output; only then is the intended builder delivered.

## Validation and acceptance

Engineering review must produce evidence-based rules and meaningful tests for recognized/unrecognized text; exact augments and rank/path unknowns; conditional states and combination order; independent stat families; supported caps and internal units; set bonuses; omissions/empties/overlays/aliases; paired slots and bags; job/character isolation; planned versus observed gear; baseline comparison; draft save/reopen/malformed references; inventory movement, sale/removal, changed augments/ranks, stale snapshots and explicit rebinding; active versus fully commented hypothetical export; missing/stale resources; keyboard/focus behavior; rapid hover/selection changes; and cache invalidation/bounded growth.

Use fictional fixtures and independently expected numeric results for supported rules; an engine comparing its output to itself is not verification. Include representative real-resource read-only checks with honest coverage limits, source review, and manual comparisons where the game exposes a suitable reference. Do not require all effective character stats to equal gear-only totals.

Run relevant core/Qt checks and the full `py -3 -m pytest -q -rs` suite during implementation, reporting exact pass/skip counts. Validate the staged frozen executable before any separately authorized local install, hash/read back the installed artifact afterward, and distinguish offline harness evidence from in-game confirmation.

Acceptance means item/copy/target distinctions are clear; supported totals and conditional effects have traceable evidence; incomplete effects cannot masquerade as complete totals; draft edits leave player Lua and original guides untouched; the accepted visual and measured performance criteria pass; and both delivery phases are clearly reported. Commit, installation, push and release remain separate gates.

The existing post-commit hook can build, replace and relaunch the executable after Python/spec commits. Preserve separate commit/install authorization: use a scoped one-command hook bypass where needed, with no persistent hook changes. On any authorized installation path, the exact executable to be installed must first pass staged frozen validation and then be hash-matched/read back and checked after installation. A hook that independently rebuilds and swaps an unvalidated artifact does not meet that requirement; do not run that path for this work unless it can satisfy the same artifact-validation boundary. Exact orchestration belongs to engineering review. No commit is authorized by this document.

## Decisions still needed

Engineering: supported-stat/rule matrix, context composition, exact missing/unsupported semantics, persistence/export schema, compatibility with legacy consumers, performance budgets and implementation file scope.

Visual: card styling/placement, pin/focus interaction, conditional controls, contribution breakdown and totals placement in relevant set views. These require mockup approval and a later in-app walkthrough. No visual redesign has been accepted from this text alone.

Concrete slice-2 walkthrough when at the app: inspect two same-name copies with different augments/bags, compare two existing sets under one scenario, toggle one supported condition, and confirm unknown effects are unmistakable. The slice-3 walkthrough adds one substitution and its delta, a clearly hypothetical Planning item, and reopening a saved draft after a copy's bag or augments change. No live Lua activation is needed for either review.

## Research and review limits

Public prior-art discovery included [Windower item descriptions](https://github.com/Windower/Resources/blob/master/resources_data/item_descriptions.lua) and [OmniWatch's documented equipment/stat/simulation features](https://github.com/BalladOfWorms/OmniWatch). No outside parser, calculator or numerical rule has been validated or imported. Current source inspection is not a benchmark or live-game test. Private personal gear/research evidence stays outside public design artifacts.

Native design review passed at 9/10; its cross-slot-legality clarification was incorporated. Claude Code document-only review, reported model `claude-opus-5-5`, completed two passes. The second confirmed all four initial findings resolved and reported **Ready for acceptance**, with three low-priority clarifications. Those clarifications were incorporated afterward by primary review without a third external pass. Full responses and metadata remain in private local review artifacts. These reviews assess the design, not stat accuracy, runtime correctness or performance.
