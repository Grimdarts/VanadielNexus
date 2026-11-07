# Gear guide runtime retirement - design (2026-11-05)

Design only. No application code changed in this slice. Implementation is a separate,
separately authorized slice, and its result goes on the pre-release test checklist.

Jason's direction: no outdated information that causes confusion. A retired guide revision
must never be offered as the current recommendation. This document says exactly how.

## 1. The problem today

The v2 candidate (`docs/catalog/gear-guide-t7-candidate.json`) records 27 retired revisions in
`authoring_amendments`: 11 BRD (`brd-augment-parts-2026-11-04`), 13 BST
(`bst-provenance-2026-11-05`), 1 BST (`bst-ear-labels-2026-11-05`) and 2 more
(`scope-fallback-2026-11-05`: 1 PUP, 1 BST). They affect 25 sets. Every set with more than one
revision is one of these 25. Two BST sets have chains: `engaged-balanced` v1 -> v2 -> v3 and
`engaged-accuracy` v1 -> v2 -> v3.

The runtime ignores `authoring_amendments`. Read from the code, it does this:

- `validate_catalog` (core/guide_catalog.py) never reads `authoring_amendments`. Retired and
  effective revisions are both loaded as equals.
- No set has a `default_revision_id` (0 of 520). `revision_tree` (core/gear_guides.py) sorts by
  `(id != default, version_order, label)`, so **the retired v1 sorts first**. `_versions`
  (ui/pages/guides.py) selects index 0, so **the app opens the retired revision by default** for all
  25 sets. It also shows version pills for both revisions. For BRD those pills have the same
  `equipment_version` text, so the user cannot tell them apart.
- `_revision_update` (ui/guide_revisions.py) proposes only `default_revision_id`, which is never set.
  A saved target that points at a retired revision **gets no update offer and no notice**.
- `resolve_reference` (core/guide_catalog.py) reports `current` whenever the catalog still contains
  an identical revision. A retired revision therefore reads as current.
- For the 11 BRD retired revisions, the inventory table would compare against wrong augment strings
  (`DEX+30`, unquoted `Fast Cast+10`, and so on). It would show "Upgrade / verify" for a
  correctly augmented cape or Linos. This is exactly the confusing outdated information to remove.

Production today is v1 (`vanadiel_nexus/resources/gear_guides.json`, schema 1). None of this can
reach players until a v2 catalog ships. **Retirement must be implemented before any v2 catalog is
published.**

## 2. Rules

1. **One current recommendation per set.** A retired revision is never listed, selected or
   proposed as current. It stays in the catalog only as history and for saved targets.
2. **Personal work is never silently retargeted.** A saved target keeps its frozen snapshot until
   the user reviews and accepts the update. This keeps the existing rule ("Saved snapshots win;
   latest ordering never retargets personal work").
3. **Outdated is always visible.** Wherever a retired revision shows, the screen says it is
   outdated, names the replacement and gives a one-step path to review it.
4. **Outdated requirements are not graded.** A slot whose requirement changed in the replacement
   never shows Missing, Upgrade or Owned results computed from the outdated requirement.
5. **Fail closed.** A malformed retirement record makes the catalog fail preparation
   (`CatalogError`). The app never guesses which revision is current.

## 3. Data: the retirement map

The source of truth is the existing `authoring_amendments` list. The schema does not change and
no records are rewritten. Each amendment gives `set_id`, `retired_revision_id`,
`successor_revision_id` and `reason`. Its batch gives `id`.

New pure function in `core/guide_catalog.py`, called at the end of `validate_catalog`:

```
retirements(catalog) -> {retired_id: {'successor': id, 'effective': id, 'set_id': id,
                                      'batch': batch_id, 'reason': text}}
```

Validation, each failure raises `CatalogError`:

- `authoring_amendments` is a list of objects. Each has a non-empty `id` and a non-empty
  `amendments` list. Each amendment has the four text fields.
- The retired and successor revisions both exist, and both have the amendment's `set_id`.
- The successor's `version_order` is greater than the retired revision's `version_order`.
- A revision is retired by at most one amendment, so each retired revision has exactly one successor.
- Following successors never revisits a revision (no cycles). The end of the chain, the
  **effective** revision, is not retired and is not `equipment_options`.
- If a set has a `default_revision_id`, it is not retired.
- Every set has exactly one effective revision. The current candidate passes this check because
  each of the 25 multi-revision sets resolves to a single head. A future set with two
  unretired revisions would need an explicit `default_revision_id`, or the check fails.

`validate_catalog` returns the catalog with one added derived key, `_retirements`. It is not
written back to disk. `CatalogStore` history and immutability checks are unchanged. A catalog with
no amendments yields an empty map and behaves exactly as today. That covers v1 and all existing
fixtures.

## 4. Behaviour by surface

### 4.1 Guide picker (`revision_tree`, `_versions`)

- `revision_tree` drops retired revisions. Each of the 25 sets then lists one revision, so the
  version pills disappear for them. The count in the purpose combo (`Purpose (n)`) counts only
  effective revisions.
- A remembered picker choice (settings `versions`) that names a retired id is replaced by that
  set's effective revision. The setting is rewritten only on the user's next pick, so nothing is
  written just by opening the page.
- A retired revision cannot be selected from the picker.

### 4.2 Saved target on a retired revision

This is the only place a retired revision is shown. Under the existing provenance line:

- **Banner** (Caption style, warning tone from DESIGN.md, not a modal):
  "Outdated guide revision. This saved target uses <retired id>, replaced on <batch date> by
  <effective id>: <plain reason>. Review the update to switch; your saved choices are kept."
  Plain reasons by batch:
  - `brd-augment-parts-2026-11-04`: "augment requirements corrected to the exact in-game augment
    text; the gear is the same."
  - `bst-provenance-2026-11-05`, `scope-fallback-2026-11-05`: "guide citations corrected; the gear
    and requirements are the same."
  - `bst-ear-labels-2026-11-05`: "earring names corrected; the gear and requirements are the same."
- **Saved combo** entry text ends with " · outdated".
- **Track button** reads "Review update…" and is enabled whenever the workspace is writable. It opens
  the existing `RevisionReview` dialog from the retained snapshot straight to the **effective**
  revision, skipping intermediate chain links. Accepting it calls the existing `prepare_adoption`,
  which keeps bindings and overrides, then `_save_workspace`. Cancelling changes nothing.
- **Edit selected target** is disabled with the tooltip "Review the update first; edits to an
  outdated revision would carry the old requirements forward." Bindings and overrides already
  saved are carried into the adoption unchanged. If the existing removed-slot rule applies,
  adoption is blocked, as it is today.
- **Inventory table:** rows come from the retained snapshot, as today. A selected slot whose
  `requirements` differ from the effective revision's same slot shows:
  - status `Outdated requirement`;
  - requirement column: the retained requirement text;
  - detail "Requirement changed in the current revision; review the update to compare correctly."

  This applies to the BRD cape and Linos slots. Slots with identical requirements (all slots in the
  16 gear-identical BST/PUP retirements) are graded normally. Their comparison is still correct.
- `resolve_reference` gains a status. Its order becomes: `unavailable_source` (revision missing),
  `conflicting_revision` (catalog differs from snapshot), `retired` (identical but retired;
  returns the effective id), `current`.

### 4.3 Saved target on an effective revision

No change. If a later batch retires that revision, the target follows 4.2 the next time it is
opened.

### 4.4 Legacy associations (`normalize_legacy`)

A `proven` association whose revision is retired is reported as proven, and is then shown with
the 4.2 banner. It is never silently mapped to the successor.

### 4.5 Counts and reports

Authoring tools and reports count **effective** revisions: stored verified minus retired.
Today that is 539 stored flags, 27 retired and 512 effective. The UI never shows the stored total.

## 5. What the user sees: three cases

1. **Browsing BRD Fast Cast.** One revision, no version pills. The table grades the cape against
   `"Fast Cast"+10`. Nothing mentions the old encoding.
2. **A BRD Engaged target saved before the correction.** The banner names the update. The cape and
   Linos rows show "Outdated requirement" instead of a misleading "Upgrade / verify". The other 14
   slots are graded normally. "Review update…" shows the requirement diff. After accepting, the target
   points at v2, the banner goes away and all rows are graded.
3. **A BST engaged-balanced target saved at v1.** The banner says citations and earring names
   were corrected and the gear is the same. Every row is graded normally. "Review update…" goes straight
   to v3.

## 6. Tests that would prove it

Core (`tests/core/test_guide_retirement.py`, fictional catalogs, plus actual-candidate checks):

1. The actual candidate yields 27 retired ids, 25 sets and 25 distinct effective heads. Both BST
   chains resolve to v3.
2. A fictional amendment rejects each of these: unknown retired or successor revision, set
   mismatch, successor not newer, two successors for one retired revision, a cycle, an
   options-kind head, a retired `default_revision_id`, and a set with two unretired revisions and
   no default.
3. A catalog with no `authoring_amendments` gives an empty map and an unchanged
   `revision_tree`, which keeps the v1 and existing fixture behaviour.
4. `revision_tree` on the actual candidate lists no retired id, and for each of the 25 sets lists
   only the effective head.
5. `resolve_reference` order: missing -> `unavailable_source`; changed -> `conflicting_revision`;
   identical retired -> `retired` with the effective id; effective -> `current`.
6. `prepare_adoption` from a retired snapshot to the effective head keeps bindings and overrides,
   and is still blocked by a removed bound slot.
7. `validate_catalog` remains idempotent. The derived `_retirements` key is not part of revision
   immutability and is never written to the workspace.

UI (`tests/ui/test_guide_revisions.py` additions, pytest-qt, fictional catalog with one retired
revision whose requirement changed and one whose gear is identical):

8. Opening the set selects the effective revision and shows no version pills.
9. A remembered retired picker choice opens the effective revision, and no setting is written.
10. A saved target on a retired revision shows the banner text, the " · outdated" combo
    suffix, the "Review update…" button enabled and Edit disabled.
11. A changed-requirement slot shows `Outdated requirement` and never Missing, Upgrade or Owned.
    Unchanged slots are graded as before.
12. Accepting the review saves the effective revision, keeps the bindings and clears the banner.
    Cancelling leaves the workspace bytes unchanged.
13. A chain (v1 retired by v2, v2 retired by v3) reviews straight to v3.
14. A malformed amendment produces the existing catalog-error state: saved snapshots stay
    inspectable and mutation is blocked.

Release gate: before any v2 catalog is published, the full suite passes and the pre-release
checklist includes a manual check of cases 1-3 in section 5 in the built app.

## 7. Out of scope

Rewriting or deleting retired records, automatically migrating saved targets, changing v1
production behaviour, and any schema version bump. Implementation is the next authorized slice:
code and tests in `core/guide_catalog.py`, `core/gear_guides.py`, `ui/guide_revisions.py` and
`ui/pages/guides.py` only. It changes no catalog data.
