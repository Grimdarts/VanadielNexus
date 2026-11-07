# Release2.2.0 integration, staged RC and phone checklist update (2026-11-05)

Jason authorized continuing the release integration/RC slice and updating only missing tests in the newer checklist moved by Gemini to Nova AI Operations Hub/Projects/FFXI. Nova worked alone in the existing checkout. No new worktree/session/agent, index/ref update, commit, push or installation.

## Integrated release input

Local release/2.2.0 tip260774924c55fe6c9e49cf47bd6330ad7bb96ab4 descends directly from current HEAD8f91ca164bd6737a4ad87185656eb96fcc1d45d4 through four commits. Its delta was applied to the current dirty working tree using exact release bytes for untouched files and normalized diff3 for overlapping text, preserving each existing file's own byte style. The sole conflict was tests/ui/test_guide_controls.py; both added tests and the retained-v1 fixture were kept. This is working-tree integration, not a Git merge commit or branch move. The existing VN-release checkout was inspected read-only and remains untouched.

Release changes include the empty new-player tracker, safe Lua editor actions, Wishlist suggestions, cache-race and Sets follow-loop fixes, layout reload fixes, the packaged addon1.5.1 and player guide. The T7 candidate and production bundle remain byte-identical to the prior slice. No gear research or coverage expansion.

World Map's source/modules/data/tests/scratch are retained byte-for-byte. The release navigation omits its page, and the spec excludes its Python modules/data from the RC. Release-only map fixes were not imported. The obsolete Mote hook file is also retained in source but excluded from packaging, matching the release removal without deleting preserved work. The player guide now describes the v2 guide UI and deferred map accurately.483 baseline source/doc/test/root-file backups and the per-file integration ledger are in `.t7-release-integration-checks/`.

## Staged RC

- Executable: `C:\Users\Jason\Games\VanadielNexus\.t7-release-integration-checks\dist\VanadielNexus.exe`.
- SHA256: `979e3a8d435f5fc275b3e3297e059d9156559c7d7c16a57d6c184189aaa466dd`;45470252bytes.
- PyInstaller6.22.3/Python3.14.6; PySide66.12.0; version2.2.0.
- Exact bundled production SHA256 `fa24c857b90cf6cf1db6a03b26fb99d2da9ec605e84d31219c76054945a586f1`:512sets/539historical revisions/27retired/512effective recommendations. Full candidate remains520sets/547revisions/eight unresolved originals in retained audit history; source/coverage/amendments unchanged.
- Archive inspection confirmed required guide modules, exact bundle bytes, and absent WorldMap/Mote hook release content. Existing Windows system-DLL filtering passed.
- `tools/check_frozen.py` now accepts explicit detached public-resource evidence to write only fictional resources inside its isolated startup directory. Startup explicitly disables inventory seeding and reports real guide-loader status/counts. All10 intended pages opened; catalog validation passed; the actual spawned Lua fixture read passed in0.27s. This executes no player Lua.
- Built with the repository spec and task-local work/dist paths; build.ps1/release.ps1 were not invoked. Installed app/addon hashes are unchanged. The installed addon remains1.5.0; the RC packages1.5.1, so live addon/layout acceptance requires a separately backed-up swap. No swap, restart or game command was performed.

## Validation

Targeted integration:104passed/0failed/0skipped in18.13s. Final focused:1002passed/0failed/0skipped in144.02s (0:02:24). Final full:1571passed/0failed/0skipped in162.41s (0:02:42). Fresh native real-file launchers, unique TEMP/TMP/VN_DATA_DIR/basetemp, fictional Windower discovery/public metadata and disabled inventory seeding. Actual-resource production validation and independent preservation checks are recorded separately in the readback packet.

The first focused run was1001passed/1failed/0skipped in149.31s: Windows denied renaming a just-created fictional resource fixture directory. The fixture now writes its file directly to the expected temporary directory; no production validation or assertion was weakened. Targeted startup rerun4/0/0 in3.45s, followed by final focused/full passes. Build and frozen validation used final application code; the later fixture change was test-only.

## Checklist update and test readiness

Updated the same existing Drive Markdown file, preserving its ID, folder, sharing, existing checkbox states and personal checks: **VanadielNexus - Test Checklist and Status (2026-11-04).md**, ID`1oJH-Xlki_H5_iztOxPVJoEMCwZwHPYVe`. Current location was verified through FFXI → Projects → Nova AI Operations Hub metadata. This is the newer Nov4 checklist, not TONIGHT-TEST-CHECKLIST-2026-11-02.md. Original bytes are retained as `checklist-before.md`; updated bytes and readback evidence are retained alongside.

Added only12 missing test IDs A16–A27: scoped source/catalog selection, BRD Fast Cast and changed-requirement retirement, BST direct-to-head correction, character/copy/bag truth, literal augments on one copy, saved overrides/adoption persistence, item-details consistency, bounded equipment analysis, safe editor actions, Wishlist identity suggestions and rapid selection/follow-loop behavior. Existing copy/layout steps gained relevant new-behavior notes. A11–A13 remain explicitly deferred after2.2.0 and unchecked. Obsolete active status/scope statements were corrected; no historical pass was promoted to RC acceptance. The three pending GUIDE-RETIRE cases are mapped to A17–A19.

The optional `Launch-RC-Testing.ps1` opens the staged RC with a separate fictional profile, refusing to launch while another Nexus is open so the old single-instance app cannot be mistaken for the RC. It was prepared, not executed. The profile has public resources and three fictional old targets, with no owned inventory or copied player data. It supports offline review/cancel/adoption tests immediately. To test real connection, ownership and live layout behavior, Jason must deliberately choose the intended Windower/addon pair; the installed1.5.0 addon does not certify RC1.5.1 acceptance.

Cloud readback verified the updated content. Offline RC testing can begin. Human results remain unchecked. DRG/PUP/DNC/ALL22/additionalRUN and every declared gear limitation remain pending after2.2.0; currentBG refresh remains source-limited. No currentBiS/caps/HP-preservation/ownership/live acceptance is inferred from offline results. Public release still needs Jason's tests and explicit approval.
