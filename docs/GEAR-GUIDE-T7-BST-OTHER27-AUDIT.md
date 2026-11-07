# T7 BST - other27 node-linked source-scope audit

2026-11-05. Claude alone in the same existing checkout, assigned by Jason; the prior Hasso session had finished and stopped; Nova and Vesper unassigned. No agents, worktree, new window or concurrent integration.

## Scope and what was recorded

BST-PROVENANCE deferred 27 of the 48 item sets linked from FFXIAH node 227. The candidate held no per-set record of any of them. Their only per-set provenance is the protected production v1 guide (vanadiel_nexus/resources/gear_guides.json, reviewed 2026-10-31; read-only here): its BST node 227 set_ids list and one record per set with label, note, exact item IDs/names and generic slot labels. The candidate covers them only through source bst:t7:scope-node-inventory:2026-11-05 and the node-inventory observation. No raw capture of the 27 pages had been retained, so all 27 were recaptured.

## Evidence

Ordinary public HTTPS GETs (urllib; no cookies, auth, proxy, challenge or settings change) returned 200 for node 227 and all 27 pages. Raw HTML and response metadata are under .t7-bst-other27-checks/source-html/. FFXIAH exposes no revision id and no Last-Modified header. Node 227 states Date Last Modified 2026-06-25 20:01:27. Its 48 links, in order, equal both the earlier 15:59 capture and the production list. Only the users-online and view counters differ. Each page's date is its set-note text where present; 339928/339931/339932 have no date, so retrieval time and raw hash are the only temporal locators.

Each page parses to exactly 16 equipbox cells: **432 cells / 338 selected / 94 source omissions**. Ordered Equipment Macros agree with every grid (0 conflicts), and every selected ID fits its cell and is BST-wearable in the actual resource (fingerprint 0c9d2cdb...c4cc78). Titles and notes equal the production labels/notes, and production names equal exact resource names. Production ear/ring labels are generic both-side resource labels and claim no side, so there is no side-label conflict. Exact sides are now recorded from the grids.

## Classification (27)

- **Confirmed, 22.** Exact item multiset, names, title and note match.
- **Label/attribution defect, 5**, all in protected production records holding one entry per item ID where the grid and macros select two copies: 378247 NIN (Aymur AM3), Chirich Ring +1 26182 ring1+ring2; 333131 Feral Howl, Stikini Ring +1 26184 ring1+ring2; 339931 Ready Interm. and 339932 Ready Advanced, Kumbhakarna 20809 main+sub; 365917 Reward Beginner, Levia. Ring 27566 ring1+ring2. Production has no repeated item ID in any of its 376 sets; five of the 21 already-scoped sets show the same pattern. The v1 collector is not in the repository, so its mechanism is not established. Corrected only as append-only evidence amendments; production bytes are unchanged (replacement not authorized).
- **Source drift, 0.** Not established. Notes equal the 2026-10-31 record, and the node stamp predates it. No earlier raw page exists for comparison.
- **Source-limited, 0.** No access failure occurred. The absence of revision ids is recorded per page, not treated as N/A.

## Candidate correction

Candidate source bst:t7:scope-node-inventory:2026-11-05 was attributed to kind bgwiki and https://www.bg-wiki.com/ffxi/Ready, although its hashed observation is the FFXIAH node 227 linked-set inventory. That observation also says "eleven WS sets", but the node's Weaponskills section links 8 (Rampage, Mistral Axe, Decimation, Ruinator, Onslaught, Primal Rend, Cloudsplitter, Blitz). Its "Killer Instinct utility" is not a linked scope; it remains a declared variant. The fix appends one successor source, bst:other27:node-inventory:2026-11-05 (ffxiah, node 227), plus one explicit source-observation amendment, one authoring batch with baseline record hashes and a delivery_status suffix. No revision cites either record. Sets, revisions, selected gear, requirements, contexts, defaults, coverage, resources and hands are unchanged. The prior source and observation are retained.

Engaged-accuracy's "two physical Chirich Ring +1 copies (node 227 AM3 grids)" is confirmed: cited 371161 and uncited 378247 both select 26182 in ring1 and ring2. No successor revision is needed. The resolved earring correction stays as recorded (source Dedition27544 ear1 / Sherida26084 ear2; Nexus Sherida26084 ear1 / Dedition27544 ear2; Telos27545 absent).

Observed but out of scope, not corrected: the same null-URL fallback (kind bgwiki, a BG mechanics URL) on BST community-guide and bg-ready and on PUP node-inventory, stage-conflicts, bg-maneuver and automaton-actions (two of these PUP sources are cited by revisions).

## Candidate and validation

Candidate **520 sets / 545 revisions / 1326 sources**; 537 stored flags include 11 BRD + 14 BST superseded; **512 effective / eight unresolved**. 231 included / zero recorded gaps / zero N/A across all22jobs is not full T1/job coverage. SMN 20/17 unchanged. Resources 863; hands 55 / hands.2026-11-05.v19; fingerprint unchanged. Candidate SHA256 9e721bbd8a8488ac7ca15f71363700a763ba09721b643277b7c9f00ecab18bf3 (prior 353a82ca85334eebedad99c44f6cb575c836336ddba2fd2ac7ad2142f004c658). Production SHA256 54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85 unchanged.

Presave **39 passed / 0 failed / 0 skipped**: BST 11, DNC 5, SMN 7, Hasso 6 and this slice's 10, in separate isolated processes. The new gate checks actual-draft identity and uses its own independently typed fictional literal strings for separate 20/10, combined/repeated/missing parts, native punctuation, subset semantics and whitespace/casefold. Whole-candidate actual-resource prepare passed, then a single append-only save_candidate. Fresh focused native: **683/0/0 in 63.22s**. Fresh serial full native: **1497/0/0 in 164.49s**. Both use real-file Python 3.14 launchers, unique TEMP/TMP/VN_DATA_DIR/basetemp, fictional Windower discovery and disabled inventory seeding. Twelve prior guide tests changed only the source count 1325 to 1326 and the hash chain; one new regression file. No application, validator or tool change. 409 pre-edit byte backups. Independent readback: catalog/gear-guide-t7-bst-other27-readback.json.

Packets: catalog/gear-guide-t7-bst-other27-audit.json (27 grid observations, node-inventory successor, five production amendments, corroboration) and its readback. All prior reports, packets, captures and histories are retained. Branch codex/sets-copy-fixes-review, HEAD 8f91ca164bd6737a4ad87185656eb96fcc1d45d4.

## Stop

Still open: declared BST variants, BRD runtime retirement, SMN pact/Ward/WS/ability variants, the Hasso/Blood Pact delay interaction and all other inventory limits. STOP after this slice and the standalone successor prompt; no automatic chain. No production replacement, commit/push/build/install/release/migration, T8/T9, game command, Lua execution or activation, inventory loading or settings change. Offline checks do not establish ownership/bags, caps/totals, HP preservation, current BiS or human/frozen/live acceptance.
