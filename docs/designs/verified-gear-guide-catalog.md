# Design: Verified gear guides and relevant modes for all 22 jobs

Generated through GStack /office-hours on 2026-11-03.
Branch: codex/sets-copy-fixes-review.
Repo: Grimdarts/VanadielNexus.
Mode: Builder.
Status: APPROVED by the user on 2026-11-03 after native and Claude document review. Approach B and this revised design are accepted as the design baseline. Engineering details and the consolidated job coverage matrix remain to be reviewed; this approval does not authorize implementation, installation, commit, push, or release.

## Problem and intended experience

The existing Guide upgrades page feels right to the user. Its information needs to be verified, refreshed, and expanded consistently across all 22 jobs before research-driven GearSwap equipment changes. Guides differ in how many sets and equipment tiers they provide. A consistent catalog must preserve useful differences without inventing tiers or treating every published set as a universal best choice.

The user wants relevant selectable gear priorities on every job, including choices such as DT Idle and Refresh Idle. The guide should explain what each priority does, show source-supported equipment versions, compare exact requirements against inventory, and provide a dependable reference for later job-specific Lua work.

## Decisions and constraints

- Preserve the current appearance and Purpose -> Set -> Version workflow. Reuse existing controls and descriptive areas. Defer visual improvements until the user can review the app in person.
- Cover all 22 standard jobs using one information standard; job-specific mechanics and relevant choices remain distinct.
- Retain useful starter, budget, and older alternatives with explicit labels. Age and affordability are separate facts; an older item is not automatically obsolete or cheap.
- Add useful missing sets through additional research. Label assembled sets **Nexus recommendation**, retain supporting sources, and explain selection criteria and tradeoffs. Do not attribute an assembled set to a guide that never published it.
- Keep guide targets separate from owned working gear and player preferences. Do not infer ownership, rank, path, or augments from a guide or a base item name.
- Keep Windower and all current player Lua read-only. No Lua activation, installed-file replacement, game commands, or job-framework conversion belongs to this catalog project.
- Preserve the approved managed-bundle design in `docs/designs/gearswap-job-bundles.md`; this project supplies research and a mode reference, not a replacement architecture. BLU/RUN retain separate logic; SMN retains its existing framework responsibilities.
- Preserve inventory, wishlist, goals, saved guide selections, and personal requirement overrides. Use fictional or temporary data for validation.
- Follow-up clarification accepted on 2026-11-03: explicit per-slot targets must support personal designated bags for duplicate items, e.g. left ring from one Wardrobe and right ring from another. Match item requirements and bag on the same copy, allocate distinct copies to simultaneous slots, and preserve ownership versus equip-readiness distinctions. Bag placement is personal binding data rather than a universal guide requirement. See architecture decision 2 in `docs/GEAR-GUIDE-CATALOG-ENG-REVIEW.md`.

## Existing foundation and evidence

Read-only inspection on 2026-11-03 found 376 catalog sets across BLU, BST, COR, NIN, RDM, RUN, SCH, and SMN, with a catalog-level review date of 2026-10-31. This date does not establish that every individual claim was recently checked.

This is both a refresh and new authoring: those eight jobs have existing entries to audit; WAR, MNK, WHM, BLM, THF, PLD, DRK, BRD, RNG, SAM, DRG, PUP, DNC, and GEO currently have no catalog entries. Per-job coverage and research effort must be established before any schedule is promised. An existing job is not assumed complete because it has many entries.

The user-provided private Drive research folder contains 22 job handoffs, a universal Lua template, a specialization guide, and an architecture handoff. The architecture handoff was read first; equipment-table coverage was inventoried across the job documents. This is discovery evidence, not independent verification of the claimed equipment, caps, update dates, or Lua snippets. Some rows combine distinct actions and several alternative items; they cannot be imported as precise equipment records without interpretation and verification.

Private research is an input. Do not publish private Drive links, personal inventory, or copied personal profiles in the distributed catalog or repository. Public source citations should support the distributed recommendations.

Artifact destinations are explicit: ship sanitized equipment definitions, requirements, verification metadata, and public citations in the catalog; put only generic job coverage and sanitized source summaries in public repository documentation. Keep raw research captures, private Drive references, current personal Lua mappings, and the detailed verification/gap report in the local private GStack project store. Do not upload copies to Drive without a request. The detailed gap report is a separate planning artifact, not a new in-app screen; any later in-app presentation goes through the visual walkthrough.

Reuse:

- `vanadiel_nexus/resources/gear_guides.json`: current catalog and identifiers.
- `vanadiel_nexus/core/gear_guides.py`: grouping, same-copy requirement checks, and explicit idempotent tracking.
- `vanadiel_nexus/ui/pages/guides.py`: current picker, inventory comparison, assumptions, and source actions.
- `vanadiel_nexus/core/item_res.py` and existing wiki helpers: resource identity, slot eligibility, and item links.
- `tools/classify_guide_sets.py`, existing catalog/guide tests, and `docs/guide-set-groups.md`: classification and review infrastructure.

This extends the information scope deferred as batch 4 in `docs/GUIDE-UPGRADES-SPEC.md`. It does not supersede the completed picker design or the separate GearSwap bundle design.

## Information standard

These are logical requirements. Exact field names and schema evolution belong to engineering review; avoid a second catalog or parallel parser when existing fields can be extended.

| Concept | Meaning and rule |
|---|---|
| Job | Explicit job applicability, using the existing abbreviations. Shared sets require verified applicability and matching assumptions. |
| Purpose | Broad equipment use, reusing existing purpose categories wherever they fit. |
| Set / priority | Specific action or player priority, e.g. Savage Blade, DT Idle, Refresh Idle, or TP Accuracy. Keep distinct objectives distinct. |
| Selection behavior | Distinguish a player-selected mode from an action-specific set or an automatic conditional overlay. A published table name alone does not prove a selectable runtime mode exists. |
| Equipment version | A supported equipment alternative for the same purpose and priority. Use source wording where accurate; do not manufacture Entry/Mid/Endgame tiers for a one-version guide. |
| Origin | Published guide set or Nexus recommendation. Research handoffs are discovery notes, not proof of published authorship. |
| Currency and verification | Record what was checked, against which sources, and when. Distinguish verified current, useful older reference, and unresolved/conflicting claims. Keep source update dates separate from verification dates. |
| Requirements | Exact item ID/name, slot, quantity, augment/path/rank, and other necessary conditions. Unknown values remain unknown. |
| Assumptions | Relevant weapon/offhand, buffs, subjob, master level, attack/accuracy assumptions, pet state, encounter context, or other conditions that change suitability. |
| Rationale | Explain when to choose the set and significant compromises. Nexus recommendations need an explicit reason for their composition. |
| Provenance | Public guide URL plus a specific section/table/item-set reference where available. Preserve multiple sources and disagreements rather than selecting an unsupported winner. |
| Stable identity | Preserve conceptual IDs for the same purpose/priority and source lineage, while making changes to equipment requirements identifiable. Use stable, namespaced IDs for new concepts; external FFXIAH set IDs must not be repurposed to identify Nexus-authored sets. |

Tier, origin, and currency are independent. **Starter** and **Budget alternative** describe access/progression; **Older reference** describes currency only, never a gear tier or price. For example, **Budget alternative** and **Nexus recommendation** can both apply to one entry. Do not compress these into one ambiguous quality score. A condition such as attack-capped is also not a progression tier.

Version order must not imply a universal best choice across different weapon, buff, attack, or accuracy assumptions. Conceptually, distinct contexts belong to distinct Set groups, with concise context qualifiers such as 'TP - Naegling - capped haste' or 'Savage Blade - attack capped'. Equipment versions within a group share its objective and assumptions. Automatic overlays have separate condition/parent references and selection-behavior annotations; they are not progression Versions or implied manual toggles. Engineering review must determine the representation and readable grouping within the existing controls, without combining incomparable contexts into a best-first upgrade list. Any necessary layout change waits for user review.

## Relevant modes and automatic behavior

Build a coverage matrix for every job: purpose/priority, available equipment versions, source/origin, verification state, selection behavior, and known current Lua mapping. Mark proposed modes separately from verified existing runtime modes.

The full user-reviewed matrix lives in the private local GStack project store because it includes personal Lua mappings. Only a sanitized generic coverage summary may be copied into public documentation.

Accepted minimum coverage: DT Idle for every job; Refresh Idle for MP-using jobs and relevant MP-using subjob contexts; balanced, defensive, and accuracy priorities for supported engaged roles; and applicable casting/pet priorities. A non-MP context can have Refresh Idle marked not applicable with reasoning rather than an empty or misleading mode. Different equipment contexts remain documented independently of manual mode selection.

The engineer/researcher proposes each job's required-priority list and any N/A dispositions using this baseline and actual mechanics, before detailed set authoring. The user reviews the consolidated matrix and exceptions in one scope decision; do not create 22 separate approval interviews. Unaccepted exceptions and missing required recommendations remain open gaps. Additional relevant priorities can be proposed in that matrix without silently expanding the accepted scope.

Examples for the matrix, not a mandatory identical control menu:

- Idle: damage reduction, refresh where meaningful, and job-specific pet or recovery priorities.
- Engaged: balanced, defensive, accuracy, and relevant weapon/haste contexts.
- Casting: potency, accuracy, burst, or defensive priorities where supported and useful.
- Pet jobs: relevant pet durability, physical/magical actions, accuracy, and master/pet tradeoffs.

Automatic spell, ability, buff, weapon, or pet-state selection should remain automatic where the existing job logic supports it. Do not turn every set into a manual toggle. Document the distinction and retain defense priority and explicit weapon locks in future Lua mapping.

A relevant mode does not require a second copy of an identical equipment set just to fill a grid. Shared equipment may serve multiple documented priorities when justified. Missing evidence is a research gap, not permission to fill slots with guesses.

The guide records recommended coverage and mappings; implementing or binding new runtime mode controls is later GearSwap work with its own staged validation. Approval of this document does not assert that all jobs currently have those controls.

## Verification and recommendation policy

1. Inventory each source and its claimed sets; use the Drive research to find the underlying public material.
2. Open cited guides, relevant embedded equipment tables/item-set pages, and applicable recent discussion. Confirm links resolve to the claimed material; do not treat a URL or a 2026 title as verification.
3. Confirm exact resources, job/slot eligibility, required quantities, and augment/rank/path prerequisites against appropriate source evidence. Retain exact physical-copy requirements in inventory comparison.
4. Separate combined rows when actions or assumptions require different gear. Represent alternatives as concrete set versions with one exact item per slot rather than storing text such as 'item A or item B' as an equipable item name. Each version gets its own inventory comparison; owning a different alternative must not mark the selected version complete. Publish representative, justified combinations rather than every possible Cartesian combination of per-slot alternatives. Retain all meaningfully distinct source-supported versions; explain additional interchangeable choices in the rationale without pretending they are trackable gear versions. A future OR-per-slot system is outside this design.
5. Evaluate missing useful priorities through additional research. For a Nexus recommendation, record the objective, constraints, equipment choices, evidence, and known compromises. Do not claim simulation, damage superiority, cap attainment, or gameplay validation that was not performed.
6. Record inaccessible, ambiguous, conflicting, or unsupported claims as unresolved with a specific next check. Quarantine them from verified-current choices and from any automatic recommendation or upgrade claim. The private verification/gap report must retain the issue without presenting it as playable gear advice.
7. Produce a per-job verification and coverage report. A coverage audit may finish with gaps, but the all-job catalog deliverable remains incomplete where a required relevant priority lacks a usable, evidence-supported recommendation. A priority may be marked not applicable only with job-specific reasoning. Clearly label any interim partial delivery; do not turn documented gaps into completion claims.

Do not mechanically retain outdated sets that no longer serve a valid use. Useful historical alternatives stay clearly marked; invalid or disproven entries must not remain actionable recommendations.

Older references may show inventory ownership and be explicitly tracked as historical targets, but cannot generate automatic upgrade suggestions over verified-current entries or be selected by default as the current recommendation. Currency is not proof of superiority: any upgrade claim, including between current entries, needs comparable assumptions and supporting evidence. Until established, present a target comparison rather than claiming an upgrade.

Evidence roles: use version-identified game/Windower resource data for item identity and job/slot eligibility, authoritative item/mechanics references for stats and requirements, published guide tables for attributed compositions, and reasoned calculations or documented comparisons for Nexus assemblies. Forum discussion can supply dated claims or conflicts but is not proof by itself; seek corroboration. Resource/guide disagreements or potentially stale installed resources must be investigated, not resolved by blind precedence. Record the source version/date and scope of evidence.

Re-verification is triggered by a relevant game/item/mechanics update, a source revision, credible contradictory evidence, or a proposed change to that set. Verification means 'checked on this date against these sources', not perpetual freshness. During each refresh review timestamps and unresolved triggers; do not introduce a background watcher or automatic gameplay change. Engineering review must define how potentially stale status is represented without falsely retaining an unqualified verified-current claim.

## Compatibility and migration obligations

Existing saved requirement keys and tracked entries depend on guide set/item identifiers. A normal equipment refresh may preserve the conceptual set ID when its objective and source lineage stay the same. Changed requirements must be identifiable, however, and must not silently retarget saved overrides or previously tracked wishlist items. A different purpose/priority or source lineage needs a distinct identity. Engineering review must settle how revisions and affected-reference dispositions are represented before implementation.

Before changing/removing/splitting an entry, inventory references and define an explicit compatibility policy for saved picks, personal requirement overrides, and previously tracked wishlist targets. Personal overrides remain distinct from curated guide requirements; neither may silently overwrite or falsely satisfy the other. Retired references need a clear disposition instead of silent reassignment. Any necessary local data migration needs a separate reviewed plan, backup, and preservation checks.

The user-facing guarantee is to retain tracked target snapshots and personal overrides until the player explicitly adopts a changed target. Identify changed/retired references and offer a reviewable adoption step through existing interactions where possible; exact mechanics and any additional UI require engineering/visual review. Never overwrite an old goal merely because its conceptual guide ID still exists.

Engineering review must assess whether the existing per-item `guideTarget` snapshots preserve the required set/revision context and whether additional persistence is needed. This is a required future behavior, not a claim that the current model already implements revision-aware adoption.

Source actions must work for both FFXIAH sets and recommendations without an external item-set page. Do not fabricate FFXIAH URLs for internal IDs. Where a precise public source is unavailable, use a truthful supported reference or an explicit unavailable state. Present verification/origin labels in the existing descriptive areas where feasible; any layout change waits for user review.

## Chosen approach and rejected alternative

**Approach B, selected:** define one maintainable catalog standard, then refresh all 22 jobs against it. Extend the existing catalog, grouping, and readers only as necessary to represent and show the agreed information accurately. This supports later mode mapping without requiring a visual redesign.

Approach A, existing labels/notes only, was not selected: it minimizes changes but leaves verification, authorship, and mode semantics dependent on inconsistent prose.

## Success criteria

- All 22 jobs have reviewed coverage matrices and usable, evidence-supported recommendations for their required relevant priorities. Not-applicable priorities have a job-specific rationale. Open required gaps mean a clearly labeled partial delivery, not completion of the all-job catalog.
- Every active recommendation has traceable evidence, a verification date/status, exact equipment requirements, and relevant assumptions. Unresolved entries cannot masquerade as verified current targets.
- Starter/budget tiers, older-reference currency, Nexus authorship, and conditional assumptions are visible and unambiguous; useful older alternatives are retained without unsupported upgrade claims.
- Modes, automatic conditions, and equipment versions remain distinguishable. No unsupported tiers, cap claims, or universal-best ordering are invented.
- Stable identities and user preferences survive refreshes; repeated tracking stays idempotent; exact augments and duplicate-copy requirements remain valid and character-specific.
- The current interface remains familiar. Proposed visual improvements and any unavoidable layout changes are reviewed with the user at the app.
- No Windower or player Lua files change, no game commands execute, and no existing bundle activation occurs.

## Validation and delivery

The design phase changes documentation only. No source/catalog implementation or executable build is authorized by this document alone.

During implementation, exercise catalog integrity, all-job grouping, version/condition distinctions, origin and source handling, verification states, item eligibility, same-copy requirements, saved-ID compatibility, wishlist preservation, and representative single/multi-version jobs. Update brittle catalog assumptions deliberately rather than weakening them to accept any result. Use temporary/fictional user fixtures.

Run focused checks and the repository-required `py -3 -m pytest -q -rs`; report exact pass/skip counts and unresolved failures. If app code or bundled resources change, validate a staged frozen executable with `tools/check_frozen.py` / `--startup-check` before any separately authorized installation, and verify the installed executable afterward. Source tests do not establish what the current executable displays.

Commit, push, local executable replacement, and public release remain their applicable separate authorization gates. Use the existing release/build pipeline; do not create a new distribution system. Public publication and Lua activation are deferred.

Research and engineering preparation may proceed job by job. Once a job's required coverage is accepted and its equipment is verified, planning its later Lua changes may resume without waiting for all 22 jobs; only confirmed owned gear is eligible for working-set proposals. This does not authorize implementation, installation, or activation. The catalog is still a partial delivery until the all-job criteria pass. Bundling or publishing completed jobs incrementally is a separate release decision, not authorized by this design.

## Next steps and open decisions

1. Design record approved on 2026-11-03. Perform an engineering review of catalog/schema compatibility, normalization, provenance, stable IDs, and tests. No implementation before that review is settled.
2. Research and verify source claims, then prepare the all-job coverage and gap report. Prioritize representative idle, engaged, casting, and pet examples to prove the standard before applying it across the full catalog; the final scope remains all 22 jobs.
3. Confirm the consolidated required-priority matrix and N/A exceptions, then define final visible labels and the representation of distinct contextual Set groups within the current controls. The conceptual separation above is settled by design acceptance; any decision that requires seeing the app waits for the in-person walkthrough.
4. Implement and validate the agreed catalog update in reviewable stages. Discuss any preservation-sensitive migration before it runs.
5. After the guide is dependable, resume staged job-specific GearSwap planning using verified targets and confirmed owned equipment. Guide completeness does not itself establish Lua parity or live safety.

Concrete user assignment for the later walkthrough: choose one familiar job in Guide upgrades and try selecting DT Idle, Refresh Idle where relevant, and Starter/non-starter versions of the same priority. Also compare a verified-current entry with an Older reference where available. Report any label that fails to explain when to choose it; do not repeat the completed Sets checklist.

## User priorities informing this design

- "I like the way it looks and feels now" sets a clear boundary around visual redesign.
- "They have to be clearly marked" makes labels and provenance part of correctness.
- The request for DT Idle, Refresh Idle, and relevant choices on all jobs makes mode coverage a requirement rather than a byproduct of whatever a source happens to list.

## Planning limitations

External review record: Claude Code, reported model `claude-opus-5-5`, completed two document-only passes on 2026-11-03. The first identified nine design issues, which were addressed; the second reported all nine resolved and a verdict of **Ready for user acceptance**, with all five dimensions passing and five low-priority clarifications. Those clarifications were subsequently folded into this draft through primary review; they were not sent for a third external pass. No external repository or equipment-source inspection was performed. Detailed responses and session metadata remain in private local review artifacts.

The GStack launcher initially failed with a Windows sandbox access error during office-hours; the installed instructions were read directly. The Claude-review launcher later succeeded through approved execution. Claude's document-only external review used the configured model reported as claude-opus-5-5; repository inspection was not included. No general landscape search or independent equipment verification was performed during discovery. Public source verification remains required research, and UI acceptance remains pending. This record does not claim that the Drive research is correct or that any gear has been tested in game.
