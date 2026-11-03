# Sets manual-review follow-up — November 3, 2026

## Current state

Repository: `C:\Users\Jason\Games\VanadielNexus`.
Branch: `codex/sets-copy-fixes-review`.
Base HEAD: `7d32bcaeb9a4f9efab6e7eb9966130f8893c5e80`. Jason approved the screenshots and explicitly authorized committing this work and the resulting local build/install on November 3. The containing commit is titled **Sets: improve panel readability and keyboard focus**; use `git log -1 --format=fuller -- vanadiel_nexus/ui/pages/sets.py` for its exact identity.

Jason authorized implementing the clear improvements from his completed manual review.
The original review remains in
`.codex-remote-attachments/01a1a0ea-5de2-7db1-bc19-99c15cf3c08e/5ab29cb8-8286-49bc-bf00-b372dc9574fd/REVIEW-RESULTS-2026-11-03.md`.
Do not delete the attachments or repeat the checklist interview.

## Implemented in source

- Sets inspector details, warnings, source location, copy guidance, and snippet text now use scaled 14px body text instead of 12px captions / 13px snippet text.
- Current item links and Replacement links use standard outlined secondary buttons.
- Search instructions stay below Open job/source file, including Ctrl+F, the relevant set path and slot, and a verified filename/line when available. They appear before a replacement is selected, track slot changes, distinguish shared table searches from slot searches, and flag ambiguous destinations. File-opening and clipboard behavior remain unchanged.
- Sets buttons and trees have explicit cyan focus borders; link menus outline the active choice. Both trees retain a visible selected row when focus moves away. The snippet editor keeps a focus border too.

Changes are limited to `vanadiel_nexus/ui/pages/sets.py`, `tests/ui/test_sets_page.py`, and this handoff. No player Lua, Windower files, staged GearSwap bundles, or user data were edited.

## Validation

- Focused UI suite: `49 passed`, zero skipped.
- Final full suite: `py -3 -m pytest -q -rs` — **660 passed in 84.74s, zero skipped**. The earlier full run also passed (660 passed in 89.66s).
- `git diff --check` passed.
- Synthetic source previews inspected at 1280×800 / 100% text and 900×600 / 130% text, including button, tree and menu focus. The narrow inspector scrolls. These are source previews, not Jason's live verification.
- Preview script and PNGs: `C:\Users\Jason\.codex\visualizations\2026\11\03\01a1a16a-eebb-7ce0-9833-4b7e69f1f157`. The script uses temporary fixtures and explicitly loads Windows fonts for Qt offscreen rendering.
- Native source review and independent native adversarial review found no actionable regressions. External Claude review was unavailable through the sandbox's gstack launcher; no outside review completion is claimed.
- Build/install is the next authorized operation after committing this handoff. The post-commit hook is bypassed for this commit only so the staged executable can be checked before replacement. Persistent hook configuration is unchanged.
- The old executable was backed up and SHA256 verified at `data/backups/sets-readability-20261103-083620/VanadielNexus.exe` (SHA256 `FDB88BBD723870E9A78EF7874A6AF89EFD5FA183915DF2A2065AEFB135BFA034`). `commit-build.json` alongside it records the exact commit, staged/installed hashes and frozen startup results as the installation completes. Check that manifest before claiming this version is installed. No push or release is authorized.

## Laptop discussion still needed

Keep this focused on what Jason sees; do not restart the full review.

- SETS-3 / SETS-8: identify the exact title-menu controls, the keystrokes before highlighting disappears, and where focus should return. This styling pass does not establish the root cause or resolution of the intermittent title-menu failure.
- SETS-4: hear Jason's Open job file questions before changing its behavior. Do not assume staged Lua bundles resolve them.
- SETS-6: identify the confusing parts of the copy preview before redesigning it. Bag/priority constraints remain untested.
- SETS-7: cross-app return passed previously; changing tabs inside Nexus still needs testing.

## Separate investigations and remaining live checks

- Parser position mismatch: the in-game parser resets to the top while Layout shows the saved position. Capture the trigger, persistence behavior, and whether other overlays are affected before a fix.
- Possible lag spikes: gather timing/reproduction evidence separately. No cause has been established; do not attribute them to graphics or overlays.
- Remaining live checks: active overlay order via `//pivot s` after a fresh launch; layout saving/persistence and other overlays; bag/priority constraints; successful dispel removal; further augment-target checks.
- Avatar alternatives remain deferred. BUNDLE-1 through BUNDLE-4 remain gated; no staged profile activation is authorized.
- The review also records an XIVBar manual clarification to handle separately: XIVBar theme selection is a settings.xml Name value plus reload, while XIVPetBar has a theme command. No manual or installed addon was changed in this pass.

## Boundaries and next action

Keep `C:\Users\Jason\Games\Windower4` and all player Lua read-only. Fixes remain explicit copy-paste snippets. Preserve `data/` and use synthetic fixtures for tests.

This Sets commit and its local build/install are authorized. Push, release, future commits, and Lua activation still require their applicable separate authorization. A Python/spec commit normally triggers the post-commit build hook, which can replace/restart the running app. Validate the staged executable with `tools/check_frozen.py` / `--startup-check` before replacement and recheck the installed executable.

Resume prompt:

> Read docs/HANDOFF-SETS-2026-11-03.md, its referenced build manifest, and my November 3 review. Sets screenshots are approved, and the Sets commit/local install were authorized. Continue with the focused laptop discussion about exact title-menu focus failures, Open job file, and copy-preview clarity. Keep parser/lag investigations separate. Today's Lua discussion is in a separate chat; review the current architecture and staging documents before proposing changes. Do not push, release, make further commits, or activate staged Lua without the applicable explicit authorization.
