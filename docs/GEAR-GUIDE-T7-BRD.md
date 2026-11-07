# T7 BRD candidate batch — 2026-11-04

BRD has **28 effective Nexus-authored, composition-verified recommendations
across nine tracked priorities**, in explicitly bounded song/instrument,
MP-subjob recovery and BRD/WAR 99/49 sword/shield contexts. The batch contains
39 immutable BRD revision records: 28 initial records plus 11 corrective
successors. The eleven initial augment encodings are withdrawn from the effective
recommendations; their records remain intact for history. Use version-order 2
where listed in the amendment packet. This is a candidate milestone, not every
BRD tier, weapon, song-access variant or gameplay niche.

## Compositions and prerequisites

All keys below have prefix `nexus:brd:`. Each full composition declares 16 slots,
with an instrument in range and ammo deliberately empty. Source omissions remain
omissions in the source observations.

| Tracked priority | Effective candidate keys | Bounded context |
|---|---|---|
| DT Idle | dt-idle | Master Fili/Nyame/shield protection; Linos retained; no DT cap or Shell assumption |
| Refresh Idle | refresh-idle | Daybreak/shield with a usable MP pool/MP-using subjob; two physical Stikini +1 copies; no citizenship or low-MP latent assumed |
| Song effect / duration | song-general, march, minuet, madrigal, prelude, ballad, scherzo, paeon, etude, carol, minne, mambo | Base Kali/shield and exact level-99 Gjallarhorn; song-family armor/cape bonuses stay specific; Ballad/Minne legs and Scherzo/Mambo feet sacrifice duration pieces |
| Song effect / duration | honor-march | Marsyas equipped for Honor March; no borrowed Gjallarhorn All songs +4 or automatic extra slot |
| Song effect / duration | dummy-terpander, dummy-daurdabla | Separate one-extra-song and two-extra-song instruments; discretionary duration/song+ pieces removed; recipient slots must be maintained |
| Debuff accuracy | debuff-accuracy, threnody, lullaby-wind, lullaby-string | CHR/skill/magic accuracy versus Threnody potency; wind and Blurred Harp +1 string contexts separated; no radius breakpoint or landing rate |
| Precast | fast-cast, song-precast, honor-precast | Generic magic, ordinary song cast-time and instrument-gated Honor March; no inferred FC/recast cap or 550-JP gift |
| Engaged Balanced / DT / Accuracy | engaged-balanced, engaged-dt, engaged-accuracy | Separate Naegling/shield tradeoffs; BRD/WAR99/49, no Dual Wield or Carnwenhan AM3 |
| WS | savage-blade | Naegling/shield Savage Blade; explicit STR/WSD cape and Linos, Nyame Path B with unspecified rank |

Mousai **including NQ** requires Su3 / 500 BRD Job Points. Blurred Harp +1
requires Su2 / 100 BRD Job Points. Learned songs, usable actions, recipient
capacity and equipment access are separate prerequisites; item eligibility does
not supply them. No merits, JP gifts, ML, skill caps, five-song operation or
Clarion Call is assumed.

The installed resources contain NQ Mousai Manteel, Seraweels and Crackows but
not their HQ records. Nexus deliberately selects their exact NQ IDs with +1
song-family effects, without importing the source HQ +2 effects. Etude/Carol
use the available exact HQ turban/gages IDs. Missing HQ identities remain an
unclaimed alternative; no resource replacement or resource-currency claim.

Exact instruments: Gjallarhorn **18572** (level99 All songs+4), Daurdabla
**18571** (level99, two additional songs), Marsyas **21398**, Blurred Harp +1
**21401**, Terpander **21407**, Linos **21404**. A name alone cannot select an
instrument stage: the older source's Gjallarhorn link points at level75 ID18342.
Kali **20599** uses its base effects, without Path D skill augments or a mythic
duration bonus. Kali is the sole appended hand record: public Dagger evidence
and local skill2/slot-mask checks; prior 18 records remain AST-identical.

## Augment correction and immutable history

The first save used guide presentation strings such as DEX+30 and unquoted
Fast Cast/Store TP in eleven strict augment requirements. A review of the actual
`requirements_match` policy found that it compares whole observed augment parts;
it does not sum DEX+20 and DEX+10 or remove quotation marks. Those initial
requirements would reject legitimate decoded copies. This was an authoring error,
not a source-content or player-data error.

The correction is **append-only**. Eleven new version-order2 revisions supersede
the affected initial revisions; no prior source, set or revision was rewritten.
`authoring_amendments` and the portable amendment packet identify every withdrawn
ID and its recommended successor. The source's numeric choices remain unchanged:

- TP cape: separate DEX+20 / DEX+10, Accuracy+20 Attack+20, `"Store TP"+10`, DT-5.
- Savage Blade cape: separate STR+20 / STR+10, Accuracy+20 Attack+20, WSD10, DT-5.
- Accuracy cape: CHR20, combined magic accuracy/damage20 and separate magic accuracy10.
- Generic FC Linos/cape: `"Fast Cast"+6` / `"Fast Cast"+10`.
- TP Linos: Accuracy+15 Attack+15, `"Store TP"+4`, `Quadruple Attack +3`.
- WS Linos: Accuracy+15 Attack+15, STR8, WSD3; Nyame requires Path B, with **no
  asserted rank or rank-derived magnitude**.

Separate copies/augment variants are needed across these contexts. Native part
punctuation was checked by reading the installed **public Windower extdata
library**, not player Lua or inventory, and the separate cape augment categories
were read on [Intarabus's Cape revision568487](https://www.bg-wiki.com/index.php?title=Intarabus%27s_Cape&oldid=568487).
No library or player Lua was executed. Fictional-copy regression checks exercise
actual strict matching and reject source-summary totals as a single augment.

The service's generic summary counts immutable stored flags: **167 verified
revision records**, including the eleven withdrawn initial encodings. The
meaningful effective count is **156 current compositions** across six authored
jobs, including **28 BRD**. There are **8 unchanged unresolved originals**.
Do not report 167 different usable recommendations or 39 different BRD loadouts.
The existing loader does not interpret the new authoring-amendment metadata as
a runtime retirement mechanism; this remains an offline candidate requiring its
report/amendment trail, not a production-ready picker catalog.

## Sources, observations and access

Primary recent source: [Community Bard Guide revision781483](https://www.bg-wiki.com/index.php?title=Community_Bard_Guide&oldid=781483),
whose observed footer says October30,2026. Instruments, Weapons, Song+ Effects,
Song Duration, Song Accuracy, Horde Lullaby II, Fast Cast, TP/WS, Idle, Playability
and Gearswap notes were read in ordinary Chrome. It labels itself a community
opinion guide/stub. The page date does not certify every composition as current
BiS; candidate currency stays unknown.

[Briko node355](https://www.ffxiah.com/node/355) has a May10,2022 footer and
April1,2022 internal edit note. Its cape/Linos/Nyame requirements remain distinct
by purpose. Its image-only song swaps were not successfully interpreted; new
song-family recommendations use independent BG text and exact item cards rather
than claiming to extract those images.

Ten original table macros were read through Chrome, preserving their observed
order, omissions and unresolved stages:

- Songs: [363883](https://www.ffxiah.com/item-sets/363883),
  [363884](https://www.ffxiah.com/item-sets/363884),
  [369352](https://www.ffxiah.com/item-sets/369352),
  [369355](https://www.ffxiah.com/item-sets/369355).
- Precast: [363887](https://www.ffxiah.com/item-sets/363887),
  [363900](https://www.ffxiah.com/item-sets/363900).
- Idle: [363878](https://www.ffxiah.com/item-sets/363878),
  [363874](https://www.ffxiah.com/item-sets/363874).
- TP/WS: [363865](https://www.ffxiah.com/item-sets/363865),
  [363903](https://www.ffxiah.com/item-sets/363903).

These are **manual structured transcriptions of rendered Equipment Macros** and
hashed paraphrased guide observations, not raw HTML/full DOM captures. Hashes
fingerprint the recorded observations, not an immutable upstream page. Older
source AM3/subjob titles, omitted hands and instrument stages, original staff/
grip recovery and precast title totals remain source observations. Nexus full
compositions and replacements are separately attributed.

Public base cards were inspected for all **37 new selected resource IDs**, plus
Sibyl Scarf as an excluded conditional check. Sibyl's Refresh needs Windurst
citizenship; the recommendation uses Loricate instead. No Linos Refresh, random
Chironic Refresh, Fucho latent, Moonshade augment or maximum Unity is assumed.
Exact BG instrument/access pages and Mousai NQ/HQ pages supply additional
revision locators. Local-description hashes do not claim retained public HTML.

Reader requests for tables failed and the BG reader returned403. Ordinary Chrome
succeeded during this session, resolving those reads without changing security
settings. Reader failure responses are preserved separately; they are not the
successful browser evidence and no access failure became N/A.

## Artifacts, counts and validation

- `docs/catalog/gear-guide-t7-brd-definitions.json`: 28 effective definitions,
  corrected slot requirements and successor IDs where applicable.
- `docs/catalog/gear-guide-t7-brd-observations.json`: ten ordered macro
  transcriptions, hashed guide observations, omissions and conflicts.
- `docs/catalog/gear-guide-t7-brd-item-evidence.json`: 37 independent public-card
  checks, exact BG stage/access locators and excluded citizenship check.
- `docs/catalog/gear-guide-t7-brd-augment-amendments.json`: eleven exact ID links,
  native-part evidence and public-library hash.
- `docs/catalog/gear-guide-t7-brd-reader-access.json`: actual reader responses
  and their access limits; not raw live HTML/browser captures.
- `docs/catalog/gear-guide-t7-brd-readback.json`: baseline hashes, immutable
  retention, exact resource/production and protected-input readback.

Candidate: **164 sets / 175 revisions / 278 sources**. Coverage:
**225 rows / 76 included / 149 gaps across 16 remaining jobs / zero N/A**.
All non-BRD coverage rows survive unchanged. Effective current recommendations:
WHM23, SCH28, BLM22, RDM38, GEO17, BRD28 = **156**. Historical stored slots:
2,607 selected +167 intentional empty; withdrawn revisions are included in those
historical slot counts. All pre-BRD **136 sets /136 revisions /218 sources**,
all343 prior detached resource records/descriptions and every previous source
amendment/batch remain unchanged. Resource packet now has **380 records**.

Hand registry: **19 records / hands.2026-11-04.v5**. The four original upstream
resource hashes and fingerprint remain unchanged:
`0c9d2cdb0e9f8b6ae7b029e3d9482d248e53aad4dd7e831e42bf057321c4cc78`.
Production v1 SHA-256 remains:
`54b99040d197605a39a34876ad69ea65cf90902f5950771b7d4e6ffa35543f85`.

Focused final checks: **136 passed /0 failed /0 skipped in5.31s**.
Whole-candidate actual-resource preparation, independent history/resource readback
and `git diff --check` passed. Full final isolated native Windows suite:
**931 passed /0 failed /0 skipped in120.91s (2:00)**. No core/UI/test/tool
implementation changed after this run; only documentation/readback was finalized.

The first focused attempt had133 passes and one test-only failure: a broad count
update accidentally changed the original DNC slot-count expectation from10 to11.
That assertion was restored. A corrected focused pass had134 passes; the first
full isolated native run had929 passes in122.51s. The subsequent augment-part
review added the eleven successors and two strict-copy/amendment regressions;
only final-source results above/current handoff apply to the final candidate.

Pre-edit byte backups/hashes and isolated launcher/scratch remain under
`.t7-brd-checks/`. Full tests use fresh task-local TEMP/TMP/VN_DATA_DIR/basetemp,
redirected Windower discovery and disabled inventory seeding. No player persistence
was loaded for fictional verification. Branch/HEAD remains
`codex/sets-copy-fixes-review` / `5657f2092c0e0d84331d0741b1518669201e25d4`.

Unclaimed: prime/Loughnashade stages and Aria compositions, Miracle Cheer fixed
duration rules, Carnwenhan stages/aftermath, dual-wield and dagger WS, every gear
tier, high-string-skill/ML radius sets, healing/enhancing niches, every learned
song/JA niche, live weapon/TP/MP transitions, caps/totals/duration/landing rates,
ownership, bag readiness and current BiS. These are explicit limits of the bounded
included priorities, not new N/A dispositions or all-job completion.

No core/UI/numeric-policy/tool implementation changed beyond the appended exact
Kali hand evidence. Existing job-specific tests survive; earlier tests change
only candidate-wide counts/remaining-job assertions. No subagent/Vesper task,
branch switch/reset/stash/worktree, commit/push, build/install/release, production
replacement, real-data migration, game command or Lua activation. Windower/player
files remain read-only. T8/T9 and human/frozen/live acceptance remain later.
Stop at BRD; no next job has been started.
