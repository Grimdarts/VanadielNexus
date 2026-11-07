# T7 second pass - SMN99/SAM49 Hasso master-staff counterparts

2026-11-05. Claude alone, working in the same existing checkout; Nova finished all writes and stopped, and Vesper is unassigned. No other agent, session, window or worktree was created. This bounded follow-up resolves the Hasso source boundary that the prior evidence packet (`catalog/gear-guide-t7-smn-sam-context.json`, kept byte-identical) left open. It appends three separately attributed /SAM counterparts. The /WAR identities, revisions, coverage rows, defaults and saved targets are unchanged.

## What changed in access

This session ran in the Claude desktop app, which has a built-in browser pane. Ordinary article navigation read pages that native HTTPS and the reader had refused with 403/402 in the prior slice:

| Page | Revision (from the article's own MediaWiki config) | Last edited |
|---|---|---|
| [BG Hasso](https://www.bg-wiki.com/ffxi/Hasso) | 752340 (current) | 9 Dec 2025 |
| [BG Attack Speed](https://www.bg-wiki.com/ffxi/Attack_Speed) | 757807 (current) | 5 Feb 2026 |
| [BG Samurai](https://www.bg-wiki.com/ffxi/Samurai) | 696531 (current) | 8 Mar 2024 |
| [BG Category:Blood Pact](https://www.bg-wiki.com/ffxi/Blood_Pact) | 745754 (current) | 5 Sep 2025 |
| [FFXIclopedia Hasso](https://ffxiclopedia.fandom.com/wiki/Hasso) | 1542307 (current) | not read |

The BG history page served an HTTP 403 Cloudflare challenge. I did not interact with it, so the revisions come from each article's config, where `wgRevisionId` equals `wgCurRevisionId`. No setting was changed, no challenge was completed, and no alternate protected endpoint was used. Captures, text and SHA256 are under `.t7-smn-hasso-checks/source-browser`. FFXIclopedia is older-era content and serves only as independent corroboration.

## Reconciliation

The details are in `catalog/gear-guide-t7-smn-hasso-evidence.json` (HASSO-01 to HASSO-07).

- **Access and uptime.** Hasso is SAM level 25 and Sub-Job Accessible. SMN99/SAM49 requires a SAM support job that is actually unlocked and leveled. The context requires that Hasso has been used and is still active (5:00 duration, 1:00 recast). Having the ability available does not mean it is up. Nothing reapplies it automatically.
- **Two-handed staff and Seigan.** Hasso works only with two-handed weapons, and the reviewed Mpaca22100 is two_handed with grip Khonsu22218. Seigan and Hasso overwrite each other, so Seigan is inactive. Expiration, Seigan, cancellation or any non-two-handed main ends the credited state.
- **Haste categories.** Hasso counts as job-ability haste. Equipment, magic and job-ability haste have separate category caps, so Hasso does not displace the printed equipment haste. The 10% figure is a source statement only. No delay total, cap reached, x-hit or minimum haste is claimed, and no magic haste, March or Haste Samba is credited.
- **Traits.** The context covers only SAM support traits at or below level 49. No /WAR Double Attack trait, Berserk, Aggressor or Warcry carries over. The Hasso-Zanshin extra attack is SAM-main-only, and Hasso Effect job points and SAM merits are main-job categories, so none of these is imported. The sub-level STR bonus is not a modeled total.
- **Casting versus Blood Pacts.** While Hasso is active, magic, songs and Ninjutsu (re-summoning included) take a source-stated 50% casting and recast increase. Blood Pact activation is a job ability. No page read states a Hasso effect on Blood Pact delay in either direction, so no pact timing is claimed.
- **Avatar.** Hasso is a self effect on the master. An ordinary living avatar keeps the Sroda conditional master Double Attack comparable with /WAR. It does not prove that a Ward was used or applied to the master. No Favor, Ward or avatar haste is credited.
- **Gear support.** In [node380](https://www.ffxiah.com/node/380) the "Melee Summoner!" grids 401864/401863/401865 are followed directly by: "Subjobs are either /sam(Hasso 10%JA Haste) or /war". The twelve armor/accessory cells per grid are therefore attributed to either subjob. The Nexus Mpaca/Khonsu/Seraphicaller fills, the intentional empty range and the DT/Accuracy substitutions cite no /WAR trait or ability.

## Decision and compositions

Separately attributed /SAM counterparts are supported. They keep identical 16-slot states because no source establishes a different gear choice for /SAM. No /SAM rebalance was invented and no optimality is claimed.

| New identity | /WAR counterpart (unchanged) | New coverage row |
|---|---|---|
| nexus:smn:engaged-sam-balanced | nexus:smn:engaged-balanced | SMN Hasso Engaged Balanced |
| nexus:smn:engaged-sam-dt | nexus:smn:engaged-dt | SMN Hasso Engaged DT |
| nexus:smn:engaged-sam-accuracy | nexus:smn:engaged-accuracy | SMN Hasso Engaged Accuracy |

Each revision cites the prior grid/card sources plus five new BG/FFXIclopedia sources whose locators carry the revision IDs. The official PlayOnline 2006-10-19 update and 2007-03-13 notice are not an allowed candidate source kind, so they stay cited in the evidence packet; the validator was not changed. No new resources, hands or requirements. The two Accuracy Chirich Ring +1 slots still need two distinct physical copies.

## Validation and preservation

- Presave (before the one save): 29 passed / 0 failed / 0 skipped. That is the prior BST11, DNC5 and SMN7 fictional literal files, plus 6 new tests: the actual draft's identities and independent literals for separate 20/10 parts, combined, repeated and missing parts, native punctuation, subset semantics and whitespace/casefold. Requirements were not used as their own oracle.
- Fresh focused-native: 677 passed / 0 failed / 0 skipped in 55.56s.
- Fresh full-native (serial): 1491 passed / 0 failed / 0 skipped in 161.57s.

All runs used native Python 3.14 with real-file launchers, unique TEMP/TMP/VN_DATA_DIR/basetemp, fictional Windower discovery and inventory seeding disabled. There was one whole-candidate `prepare` and one append-only `save_candidate`. The saved bytes equal the validated draft. No application, validator or tool code changed. Nineteen existing guide tests had their aggregate counts updated, and test_guide_second_pass.py extends its hash and coverage chain to this packet. Each file kept its own CRLF/LF style. The new regression file is `tests/core/test_guide_smn_hasso.py`. A first count-update attempt stopped on a line-ending assertion before writing anything. It was corrected to preserve each file's style, and that diagnostic is in this report.

The candidate now has 520 sets / 545 historical revisions / 1325 sources. Its 537 stored verified flags include 11 withdrawn BRD and 14 superseded BST records, leaving 512 effective recommendations and 8 unresolved originals. Coverage is 231 included rows with zero gaps and zero N/A across all 22 jobs. SMN now has 20 compositions and 17 rows. These counts do not establish complete T1/job coverage. Resources (863), hands (55, hands.2026-11-05.v19) and fingerprint 0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78 are unchanged. Candidate SHA256 is 353a82ca85334eebedad99c44f6cb575c836336ddba2fd2ac7ad2142f004c658 (prior cf3868c2677c185982f98ddb8176c0badab34a507d43d3905759beda2f417162). Production SHA256 54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85 is unchanged. 404 pre-edit byte backups are in `.t7-smn-hasso-checks/baseline`. The independent readback (`catalog/gear-guide-t7-smn-hasso-readback.json`) passes 67/67 checks. Its first run failed one check. A name filter meant for the protected DRG/WorldMap artifacts also matched the declared count-update file `tests/core/test_guide_drg_batch.py`. The filter now excludes tests/, which the exact declared-changed-set check already covers. No data changed between the runs, and the first log is kept as `readback-initial-diagnostic.log`. `git diff --check` exits 0.

The BST earring correction remains resolved: source Dedition27544 ear1 / Sherida26084 ear2, Nexus Sherida26084 ear1 / Dedition27544 ear2, and Telos27545 absent. All 22 jobs and DNC stay in delivery_status. The other 27 linked BST sets, BRD runtime retirement and the DRG/RUN/PUP/DNC/BST and remaining inventory limits are still open. Every prior report, packet, both DRG artifact sets and WorldMap are byte-identical.

## Remaining limits and stop

These remain unclaimed: numeric Hasso haste/accuracy/STR values, trait totals, delay totals, caps reached, x-hit and hit-rate targets; any Hasso/Blood Pact delay interaction; every other SMN pact, Ward, WS or ability variant, weapon, subjob, haste tier, buff or recipient context; ownership/bags, HP preservation, current BiS and human/frozen/live acceptance. The BG Hasso history page is unread because of the challenge.

STOP after this slice and its standalone successor prompt. No automatic chain. No T8/T9, production replacement, commit, push, build, install, release, migration, game command, source/player Lua execution or activation, inventory loading, usage purchase, banked reset or settings change.
