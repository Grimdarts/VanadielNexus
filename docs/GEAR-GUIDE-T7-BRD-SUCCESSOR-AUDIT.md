# T7 BRD - effective-successor audit (2026-11-05)

Claude worked alone in the existing checkout (branch `codex/sets-copy-fixes-review`, HEAD
`8f91ca164bd6737a4ad87185656eb96fcc1d45d4`). Jason started the slice in chat. Nova and Vesper were
unassigned, with no agents, worktree or new window. This was an evidence and design slice:
no candidate save, no production edit and no application code change.

## Question

The 2026-11-04 BRD batch retired 11 initial augment encodings (`brd-augment-parts-2026-11-04`).
For each one, the audit checked two things: does it have exactly one effective successor, and do
the successor's decoded augment parts match the cited source literally?

## Structure (actual candidate, read-only)

For all 11 sets the audit confirmed:

- The retired revision is v1 and the successor is v2.
- `supersedes_revision_id` equals the retired id.
- The successor is not retired by any later amendment.
- The successor is the set's only unretired revision.
- No set has a `default_revision_id`.
- Slot identities (slot, state, item ID, name) are identical. Only `requirements` changed, plus
  the label, rationale and one added source (`brd:t7:cape-augment-parts:2026-11-04`).

Changed slots:

- Back only: debuff-accuracy, threnody, lullaby-wind, lullaby-string, song-precast, honor-precast
  and savage-blade.
- Range and back: fast-cast, engaged-balanced, engaged-dt and engaged-accuracy.

The Savage Blade Linos was already correct in v1.

## Sources re-read (ordinary navigation, no challenge, no settings change)

| Source | Cited | Observed now | Literal used |
|---|---|---|---|
| BG Community Bard Guide | oldid 781483 | /ffxi/ page, wgRevisionId 781483 | FC: "Linos 6 Fast Cast", "Intarabus's Cape 10 Fast Cast". Song Accuracy cape: "20 CHR, 20+10 Magic Accuracy". TP Linos: "15 Attack+Accuracy, 4 Store TP, 3 Quadruple Attack" |
| FFXIAH node 355 (Briko) | node/355 | Date Last Modified 2022-05-10 17:30:58, unchanged; urllib 200, sha256 1fbbbfac... | Sub NIN or WAR cape: "30DEX, 20Acc/Atk, 10 Store TP, -5 DT". Savage Blade cape: "30STR, 20Acc/Atk, 10 WS Damage, -5 DT". Linos: "15Acc/Atk, 8STR, 3 WS Damage". Nyame: "Path B" |
| BG Intarabus's Cape | oldid 568487 | /ffxi/ page, wgRevisionId 568487 | Thread stat max +20. Dye stat max +10, and Magic Accuracy max +10 as a separate row. Dust combined Acc/Atk and combined M.Acc/M.Dmg max +20. Sap WSD/STP/FC max 10. Resin DT max -5% |
| Windower public `libs/extdata.lua` | sha256 70694398... | unchanged; read, not executed | Native templates 0x023 `Mag. Acc.`, 0x044, 0x047, 0x050, 0x08C, 0x08E, 0x147, 0x162, 0x200/0x201/0x206 and the `string_augment` sign, percent and joining rules |

The cited oldid permalinks were not opened, because they hit a bot challenge that the slice may
not complete. The ordinary /ffxi/ pages report the same revision ids, so the cited content was
read directly. Captures are in `.t7-brd-successor-checks/source-captures/`.

## Independent literal check

`.t7-brd-successor-checks/test_brd_successor_audit.py` types its oracle by hand from the literals
above. It renders the oracle with its own re-statement of the extdata rule, and cross-checks it
against a second set of bare typed strings. It never uses a requirement record as its own oracle.
Checks covered:

- Each successor's requirements equal the oracle exactly.
- A fictional native copy matches the successor, with or without an unrelated extra part.
- The same copy fails every changed retired requirement, which demonstrates the retired defect.
- Dropping any one part fails.
- Separate 20/10 parts are required. A source total (`DEX+30`) or a repeated wrong part fails, and
  a split combined part fails.
- Native punctuation is enforced: unquoted `Fast Cast`, `Quadruple Attack+3`,
  `Weapon skill damage+10%`, `Mag. Acc.+20 /...` and `Damage taken -5%` all fail.
- Whitespace and case differences are tolerated.

Result: **31 passed / 0 failed / 0 skipped**. The first run had 30 passed and 1 failed. That failure
was an error in my test: it asserted that the unchanged Savage Blade Linos must fail in v1. That
log is kept as `audit-initial-unchanged-slot-assert.log`.

## Classification

| Set | Classification |
|---|---|
| debuff-accuracy, threnody, lullaby-wind, lullaby-string | confirmed |
| fast-cast, song-precast, honor-precast | confirmed |
| engaged-balanced, engaged-dt, engaged-accuracy | confirmed |
| savage-blade | confirmed |

The result is **11 confirmed, 0 defect, 0 drift, 0 source-limited**, so no correction was needed. One
observation, which is not a defect: BG 781483 also shows a different TP cape
(DEX20/Acc-Atk20/Acc10/DW10/DT-5) and a different WS Linos (WSD3/STR8/Attack20). The successors
deliberately cite node 355's /WAR TP row and Savage Blade row instead. One limitation, which is not
N/A: the BG Linos page (rev 774058) shows no augment table in its rendered text. The Linos part
categories therefore rest on the guides plus the native templates.

## Runtime retirement design

See `docs/GEAR-GUIDE-T7-RUNTIME-RETIREMENT-DESIGN.md`. It covers all 27 retired records (11 BRD,
15 BST, 1 PUP). The key finding: today the app opens the retired v1 first for all 25 multi-revision
sets and never offers an update to a saved target on a retired revision. The design hides retired
revisions from the picker and flags saved targets on them as outdated. A one-step review moves
them to the effective head, and changed-requirement slots are not graded. It also lists 14 tests
and a pre-release manual check. Implementation is a separate slice.

## Validation

- Audit test: 31/0/0.
- Fresh isolated native runs used real-file launchers, fictional Windower discovery, inventory
  seeding disabled, and unique TEMP/TMP/VN_DATA_DIR/basetemp, with Python 3.14.
- Focused native: **709/0/0 in 55.43s**.
- Full native: **1505/0/0 in 162.65s**.
- Readback: `docs/catalog/gear-guide-t7-brd-successor-readback.json`.

Packet: `docs/catalog/gear-guide-t7-brd-successor-audit.json`. The candidate
(`ca787650...1926`), production (`b57b6bb3...4300`), resources and hands are unchanged.

## Stop

No candidate save, production change, commit, push, build, install, release, migration, game
command, Lua execution, inventory loading or settings change. Offline checks do not certify
ownership, bags, caps, current BiS or live acceptance.
