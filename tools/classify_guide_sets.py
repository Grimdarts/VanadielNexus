"""Gives every guide set in gear_guides.json a plain purpose, target and version for the Guide upgrades picker.

    py -3 tools/classify_guide_sets.py

Guide titles mix what a set is for ("Savage Blade") with how good the gear is ("Dream Tier"). This splits them:
  purpose       one of PURPOSES (what GearSwap would use the set for)
  target        the specific use in plain words ("Savage Blade", "TP (max haste)", "Fast Cast")
  version       the guide's own tier words ("Dream tier", "High", "Starter #2"), "" when there is only one
  version_rank  1 = best; orders the version buttons
  note          the rest of a long title (augment advice, update dates)

Rules cover most titles; OVERRIDES (by set ID) covers the rest. Re-run after re-collecting guides: it prints every
set it can't place and exits with status 1 instead of guessing. Also writes docs/guide-set-groups.md for review.
"""
import json
import os
import re
import sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CATALOG = os.path.join(ROOT, 'vanadiel_nexus', 'resources', 'gear_guides.json')
REVIEW = os.path.join(ROOT, 'docs', 'guide-set-groups.md')

sys.path.insert(0, ROOT)
from vanadiel_nexus.core.gear_guides import PURPOSES  # noqa: E402

# (pattern at the start or end of a title, version words, rank). Longest phrases first.
TIERS = [
    (r'dream tier', 'Dream tier', 1), (r'high end', 'High end', 1), (r'elite', 'Elite', 1),
    (r'max', 'Max', 1), (r'high', 'High', 1), (r'advanced', 'Advanced', 2), (r'current', 'Current', 2),
    (r'mid tier', 'Mid tier', 3), (r'medium|meduim', 'Medium', 3), (r'med', 'Med', 3),
    (r'intermediate|interm\.?', 'Intermediate', 3), (r'low', 'Low', 4), (r'lower', 'Lower', 5),
    (r'entry level', 'Entry level', 6), (r'starter', 'Starter', 6), (r'beginner', 'Beginner', 6),
    (r'budget', 'Budget', 6), (r'return', 'Returning player', 6),
]

# Abbreviations in titles -> plain target names
NAMES = {
    'savage': 'Savage Blade', 'sw': 'Single wield', 'wf': 'Wildfire', 'leaden': 'Leaden Salute',
    'cdc': 'Chant du Cygne', 'expiacion': 'Expiacion', 'requiescat': 'Requiescat', 'sanguine': 'Sanguine Blade',
    'reso': 'Resolution', 'qd dmg': 'Quick Draw damage', 'qd acc': 'Quick Draw accuracy',
    'qa acc': 'Quick Draw accuracy', 'qd': 'Quick Draw', 'ra': 'Ranged attack', 'magical': 'Magical spells',
    'crit/am3': 'Crit / Aftermath III', 'tp': 'TP', 'fc': 'Fast Cast', 'macc': 'Magic accuracy',
    'm.eva': 'Magic evasion', 'phys bp': 'Physical Blood Pact', 'merit bp': 'Magical Blood Pact (merit)',
    'merit bp magic': 'Magical Blood Pact (merit)', 'precast bp': 'Blood Pact delay', 'pet macc': 'Pet magic accuracy',
    'hybrid(flaming crush)': 'Hybrid Blood Pact (Flaming Crush)', 'melee smn': 'Melee', 'tp dw': 'TP (dual wield)',
    'tp tizona': 'TP (Tizona)', 'cure potency r.': 'Cure potency (received)', 'cure potency set': 'Cure potency',
    'enfeebling set': 'Enfeebling', 'tp max': 'TP (max haste)', 'hybrid': 'TP (hybrid)',
}

# Ordered (purpose, pattern) rules over the cleaned title, lower-case. First match wins.
RULES = [
    ('Gear reference', r'^(af|relic|empy|empyrean)( \+\d)?$|\b(af|relic|empyrean|empy) ?\+\d'),
    ('Precast', r'precast bp|fast cast|quick magic|precast|\bsnap(shot)?\b|\bfc\b|spell interrupt|sird|\bmc_'),
    ('Pet', r'\bpet\b|\bready\b|\bbp\b|blood pact|\bward\b|wind.s blessing|siphon|call beast|\bcharm\b|'
            r'\breward\b|\bsic\b|feral howl|metallic body|single hit|flaming crush'),
    ('Ranged', r'\bra\b|triple shot|true shot|ranged'),
    ('Weapon skill', r'savage|expiacion|requiescat|\bcdc\b|evisceration|leaden|\bwf\b|wildfire|last stand|'
                     r'hot shot|aeolian|sanguine|seraph|red lotus|black halo|imperator|ruthless|knights|'
                     r'empyreal arrow|dimidiation|resolution|\breso\b|blade: |shockwave|fimbulvetr|ruinator|'
                     r'cloudsplitter|onslaught|primal rend|rampage|mistral|decimation|\bblitz\b|garland|myrkr|'
                     r'retribution|magical ws|\bws\b|pdl swaps|oshala'),
    ('Midcast: healing', r'cure|white wind|cursna'),
    ('Midcast: enfeebling', r'enfeeb|gravity|\bdia\b|inundation|fraz|dist|\bmacc\b|magic accuracy'),
    ('Midcast: nuking', r'nuke|magic burst|magical|impact|occult|drain|aspir|\bmab\b'),
    ('Midcast: enhancing', r'enhanc|phalanx|refresh (potency|other)|aquaveil|stoneskin|bar-type|regen set|'
                           r'self.enhancing|other enhancing'),
    ('Midcast: blue magic', r'physical (i|ii|iii)\b|^skill$'),
    ('Midcast: ninjutsu', r'utsusemi|ninjutsu'),
    ('Idle', r'idle|turtle|movement'),
    ('Defense', r'\bpdt\b|\bmdt\b|\bdt\b|m\.?eva|magic evasion|evasion|resist|tank|parry|def/vit'),
    ('Job ability', r'phantom roll|\broll\b|quick draw|\bqd\b|\bqa acc\b|waltz|one for all|vivacious pulse|'
                    r'enmity|lunge|swipe|utility swaps'),
    ('Melee / TP', r'\btp\b|\bdd\b|melee|hybrid|enspell|acc swaps|stp swaps|haste|am3|\bdw\b|aymur|'
                   r'lionheart|5 hit|subtle blow|accuracy|\bsw\b'),
]

# Titles the rules can't read or read wrongly: set ID -> fields to use instead.
OVERRIDES = {
    # BLU
    '386024': {'purpose': 'Midcast: blue magic', 'target': 'Magic accuracy (survivable)',
               'note': 'Reaving Wind: for spells like Dream Flower while being hit'},
    '386029': {'purpose': 'Midcast: blue magic', 'target': 'Blue magic skill'},
    '386030': {'purpose': 'Melee / TP', 'target': 'Subtle Blow'},
    '386022': {'purpose': 'Midcast: blue magic', 'target': 'Magic accuracy'},
    '386025': {'purpose': 'Midcast: blue magic', 'target': 'Magic accuracy', 'version': 'Hybrid', 'version_rank': 2},
    '337111': {'purpose': 'Midcast: healing', 'target': 'Cure (others)'},
    '337112': {'purpose': 'Midcast: healing', 'target': 'Cure (self)'},
    '348471': {'purpose': 'Midcast: healing', 'target': 'White Wind', 'version': 'Max potency', 'version_rank': 1},
    '379049': {'purpose': 'Midcast: healing', 'target': 'White Wind', 'version': 'Recommended', 'version_rank': 2},
    '337124': {'purpose': 'Midcast: blue magic', 'target': 'Physical spells', 'version': 'I', 'version_rank': 1},
    '337125': {'purpose': 'Midcast: blue magic', 'target': 'Physical spells', 'version': 'II', 'version_rank': 2},
    '337126': {'purpose': 'Midcast: blue magic', 'target': 'Physical spells', 'version': 'III', 'version_rank': 3},
    # NIN
    '363537': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Entry level (RoE upgrades)', 'version_rank': 6},
    '363538': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Entry level, 35%+ haste', 'version_rank': 6},
    '363539': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Entry level, 43%+ haste', 'version_rank': 6},
    '344236': {'purpose': 'Weapon skill', 'target': 'Magical weapon skills'},
    '344603': {'purpose': 'Midcast: nuking', 'target': 'Magic attack', 'version': 'Conditional', 'version_rank': 2},
    '344602': {'purpose': 'Midcast: nuking', 'target': 'Magic attack', 'version': '', 'version_rank': 1},
    # RUN
    '372858': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Starter #1', 'version_rank': 6},
    '372859': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Starter #2', 'version_rank': 6},
    '372860': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Starter #3', 'version_rank': 6},
    '372861': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Mid tier #1', 'version_rank': 3},
    '372862': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Mid tier #2', 'version_rank': 3},
    '372678': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Parry (best)', 'version_rank': 1},
    '372679': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Magic evasion', 'version_rank': 1},
    '398906': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Kalunga V25', 'version_rank': 1},
    '398905': {'purpose': 'Defense', 'target': 'Tank', 'version': 'August/Arebati V25', 'version_rank': 1},
    '372761': {'purpose': 'Defense', 'target': 'Tank', 'version': 'Hybrid', 'version_rank': 2},
    '372864': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Starter #1', 'version_rank': 6},
    '372865': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Starter #2', 'version_rank': 6},
    '372866': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Mid tier #1', 'version_rank': 3},
    '372868': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Mid tier #2', 'version_rank': 3},
    '372762': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Lionheart', 'version_rank': 2},
    '372891': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Aftermath III up', 'version_rank': 2},
    '372680': {'purpose': 'Melee / TP', 'target': 'TP', 'version': '5-hit (no Samurai Roll)', 'version_rank': 2},
    '372677': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Max accuracy / hybrid', 'version_rank': 2},
    '372892': {'purpose': 'Weapon skill', 'target': 'Shockwave'},
    '372670': {'purpose': 'Weapon skill', 'target': 'Resolution', 'version': 'Pre-Nyame R25', 'version_rank': 3},
    '397818': {'purpose': 'Weapon skill', 'target': 'Resolution', 'version': 'Nyame R25+', 'version_rank': 1},
    '376362': {'purpose': 'Weapon skill', 'target': 'Resolution', 'version': 'DT', 'version_rank': 2},
    '372671': {'purpose': 'Weapon skill', 'target': 'Dimidiation', 'version': 'Herculean', 'version_rank': 2},
    '372764': {'purpose': 'Weapon skill', 'target': 'Dimidiation', 'version': 'Lustratio', 'version_rank': 2},
    '376359': {'purpose': 'Weapon skill', 'target': 'Dimidiation', 'version': 'DT', 'version_rank': 3},
    '397819': {'purpose': 'Weapon skill', 'target': 'Fimbulvetr / Savage Blade'},
    '372672': {'purpose': 'Weapon skill', 'target': 'Magic accuracy weapon skills', 'version': ''},
    '372998': {'purpose': 'Idle', 'target': 'Idle', 'version': 'DEF / VIT', 'version_rank': 2},
    '372997': {'purpose': 'Idle', 'target': 'Idle', 'version': 'Regular', 'version_rank': 1},
    '372999': {'purpose': 'Idle', 'target': 'Idle', 'version': 'Refresh', 'version_rank': 1},
    '372663': {'purpose': 'Midcast: enhancing', 'target': 'Enhancing skill'},
    '372673': {'purpose': 'Midcast: enhancing', 'target': 'Enhancing duration'},
    '372674': {'purpose': 'Midcast: enhancing', 'target': 'Regen'},
    '372665': {'purpose': 'Midcast: enhancing', 'target': 'Phalanx', 'version': 'HP / DT', 'version_rank': 2},
    '368747': {'purpose': 'Midcast: enhancing', 'target': 'Phalanx', 'version': 'Max skill', 'version_rank': 1},
    '402038': {'purpose': 'Midcast: enhancing', 'target': 'Phalanx', 'version': 'Dream (ML50)', 'version_rank': 1},
    '372768': {'purpose': 'Midcast: enhancing', 'target': 'Spell interruption down'},
    '372765': {'purpose': 'Precast', 'target': 'Fast Cast', 'version': '', 'note': 'Cape: HP / Fast Cast'},
    '372664': {'purpose': 'Job ability', 'target': 'Enmity', 'version': 'DT / HP', 'version_rank': 2},
    '372675': {'purpose': 'Job ability', 'target': 'Enmity', 'version': 'Max', 'version_rank': 1},
    '372666': {'purpose': 'Job ability', 'target': 'Lunge / Swipe'},
    # SMN
    '366321': {'purpose': 'Pet', 'target': 'Hybrid Blood Pact (Flaming Crush)', 'version': 'Medium A',
               'version_rank': 3},
    '367498': {'purpose': 'Pet', 'target': 'Hybrid Blood Pact (Flaming Crush)', 'version': 'Medium B',
               'version_rank': 3},
    '401867': {'purpose': 'Weapon skill', 'target': 'Oshala (check guide)'},
    '374268': {'purpose': 'Pet', 'target': "Wind's Blessing"},
    '401897': {'purpose': 'Pet', 'target': 'Physical Blood Pact', 'version': 'Single hit', 'version_rank': 2},
    # BST
    '311276': {'purpose': 'Job ability', 'target': 'Charm'},
    '308312': {'purpose': 'Job ability', 'target': 'Reward'},
    '365917': {'purpose': 'Job ability', 'target': 'Reward', 'version': 'Beginner', 'version_rank': 6},
    '335643': {'purpose': 'Job ability', 'target': 'Call Beast'},
    '333131': {'purpose': 'Job ability', 'target': 'Feral Howl'},
    '281814': {'purpose': 'Job ability', 'target': 'Sic / Ready recast'},
    '390390': {'purpose': 'Pet', 'target': 'Metallic Body'},
    '337064': {'purpose': 'Pet', 'target': 'Ready', 'version': 'Max accuracy', 'version_rank': 1},
    '337063': {'purpose': 'Pet', 'target': 'Ready', 'version': 'High accuracy', 'version_rank': 2},
    '337061': {'purpose': 'Pet', 'target': 'Ready', 'version': 'Low accuracy', 'version_rank': 3},
    '302857': {'purpose': 'Defense', 'target': 'DT', 'version': 'Killer effects', 'version_rank': 2},
    '378207': {'purpose': 'Idle', 'target': 'Idle', 'version': 'Regain', 'version_rank': 1},
    '264975': {'purpose': 'Idle', 'target': 'Idle', 'version': 'Refresh', 'version_rank': 1},
    '264977': {'purpose': 'Idle', 'target': 'Idle', 'version': 'Regen', 'version_rank': 1},
    '326554': {'purpose': 'Weapon skill', 'target': 'Ruinator', 'version': 'Returning player', 'version_rank': 6},
    '333218': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Returning player', 'version_rank': 6},
    '333128': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Max buffs', 'version_rank': 1},
    '381576': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Multi-attack', 'version_rank': 2},
    '381577': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Gleti PDL', 'version_rank': 2},
    '381578': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Malignance', 'version_rank': 2},
    '250145': {'purpose': 'Melee / TP', 'target': 'TP', 'version': 'Dual wield (non-DM)', 'version_rank': 2},
    '371161': {'purpose': 'Melee / TP', 'target': 'TP', 'version': '/DNC Aymur AM3', 'version_rank': 2},
    '378247': {'purpose': 'Melee / TP', 'target': 'TP', 'version': '/NIN Aymur AM3', 'version_rank': 2},
    '366307': {'purpose': 'Precast', 'target': 'Blood Pact delay', 'version': 'Medium', 'version_rank': 3,
               'note': 'Cape: Blood Pact delay II -3, summoning magic skill'},
    '401874': {'purpose': 'Idle', 'target': 'Idle', 'version': 'Idle / prep / magic evasion', 'version_rank': 1},
    '378463': {'purpose': 'Idle', 'target': 'Idle', 'version': 'Magic evasion', 'version_rank': 1},
    '375613': {'purpose': 'Idle', 'target': 'Idle', 'version': 'Max refresh', 'version_rank': 1},
    '366418': {'purpose': 'Pet', 'target': 'Physical Blood Pact', 'version': 'High accuracy', 'version_rank': 1},
    # COR
    '355021': {'purpose': 'Job ability', 'target': 'Quick Draw', 'version': 'Magic accuracy / weather swaps'},
    # RDM
    '391011': {'purpose': 'Midcast: enfeebling', 'target': 'Frazzle / Distract',
               'version': 'Master level, Empyrean +3', 'version_rank': 1},
    '391024': {'purpose': 'Midcast: enfeebling', 'target': 'Frazzle / Distract', 'version': 'Before master level',
               'version_rank': 2},
    '376050': {'purpose': 'Melee / TP', 'target': 'Enspell (0 TP)', 'version': 'Standard', 'version_rank': 1},
    '399010': {'purpose': 'Melee / TP', 'target': 'Enspell (0 TP)', 'version': 'Solo', 'version_rank': 1},
    '402072': {'purpose': 'Melee / TP', 'target': 'Enspell (0 TP)', 'version': 'Sworn', 'version_rank': 1},
    # SCH
    '338349': {'purpose': 'Midcast: healing', 'target': 'Cure'},
    '378846': {'purpose': 'Midcast: healing', 'target': 'Cure', 'version': 'Weather', 'version_rank': 1},
}

TIER_RE = '|'.join(t for t, _, _ in TIERS)


def _tier(words: str):
    words = words.strip().lower()
    for pattern, name, rank in TIERS:
        if re.fullmatch(pattern, words):
            return name, rank
    return None


def split_title(label: str):
    """'Mid Tier - Savage' -> ('Savage', 'Mid tier', 3, ''); 'BST Charm - Updated ...' -> ('Charm', '', 0, note)."""
    head, sep, tail = label.partition(' - ')
    note = ''
    version, rank = '', 0
    head_tier = _tier(head)
    if sep and head_tier:
        head, (version, rank) = tail, head_tier
        if ' - ' in head:
            head, _, note = head.partition(' - ')
    elif sep:
        rest, _, more = tail.partition(' - ')
        if _tier(rest):
            (version, rank), note = _tier(rest), more
        elif len(rest.split()) <= 3 and not re.search(r'updated|\d{4}|[:%]', rest, re.I):
            version, rank, note = rest, 1, more
        else:
            note = tail
    head = re.sub(r'^(BLU|BST|SMN|Smn|RDM|NIN|RUN|COR|SCH)\s+', '', head.strip())
    head = re.sub(r'^\((.*)\)$', r'\1', head).strip()
    head = re.sub(r'\s+\d{1,2}/\d{4}$', '', head)  # "Blade: Metsu 02/2020"
    extra = ''
    match = re.match(r'^(.*?)\s+(v\d)$', head, re.I)
    if match:
        head, extra = match[1], match[2].lower()
    if not version:
        match = re.match(rf'^({TIER_RE})\b\s*(.*)$', head, re.I)
        if match and match[2]:
            version, rank = _tier(match[1])
            head = match[2]
        match = re.match(rf'^(.*?)\s+({TIER_RE})(\s+atk (?:cap|uncap))?$', head, re.I)
        if match and _tier(match[2]):
            version, rank = _tier(match[2])
            if match[3]:
                version += ' · ATK ' + match[3].split()[-1].lower()
            head = match[1]
    if extra:
        version = f'{version} {extra}'.strip()
        rank = rank or 2
    return head.strip(), version, rank, note.strip()


def target_name(text: str) -> str:
    lower = text.lower()
    if lower in NAMES:
        return NAMES[lower]
    tp = re.match(r'^tp (max|mid|low|no)haste$', lower)
    if tp:
        return f'TP ({tp[1]} haste)'
    if re.match(r'^(tp|acc|stp|hybrid|pdl|utility|enmity) swaps', lower):
        return text
    return text[:1].upper() + text[1:]


def classify(entry: dict) -> dict:
    head, version, rank, note = split_title(entry['label'])
    lower = head.lower()
    gear_ref = re.match(r'^(?:rdm |run |blu )?(af|relic|empy|empyrean)(?: \+(\d))?$', lower)
    if gear_ref:
        plus = int(gear_ref[2] or 0)
        name = {'af': 'AF', 'relic': 'Relic', 'empy': 'Empyrean', 'empyrean': 'Empyrean'}[gear_ref[1]]
        result = {'purpose': 'Gear reference', 'target': name, 'version': f'+{plus}' if plus else 'NQ',
                  'version_rank': 5 - plus, 'note': note}
    else:
        swaps = re.match(r'^(pdl|acc|stp|enmity|utility) swaps$', lower)
        hybrid = re.match(r'^hybrid swaps (.+)$', lower)
        haste = re.match(r'^[mj]/[jm]a haste (\d+%\+?) tp(\+?)$', lower)
        variant = re.match(r'^(idle|tp)\s+(?!\()(.+)$|^(refresh) idle$', lower)
        if swaps and version:  # "PDL Swaps - Savage": swaps for Savage Blade
            short = {'pdl': 'PDL', 'stp': 'STP', 'acc': 'Accuracy'}.get(swaps[1], swaps[1].title())
            head, version, rank = version, f'{short} swaps', 2
            lower = head.lower()
        elif hybrid:
            head = 'TP (hybrid swaps)'
            version, rank = ('Single wield' if hybrid[1] == 'sw' else f'{hybrid[1]} haste'), 1
        elif haste:
            head, version, rank = f'TP ({haste[1]} haste)', ('TP+' if haste[2] else 'TP'), (1 if haste[2] else 2)
            lower = 'tp'
        elif variant and lower not in NAMES and not version:  # "Idle Refresh" -> Idle, version Refresh
            kind, rest = (variant[1], variant[2]) if variant[1] else ('idle', variant[3])
            head, version, rank = 'TP' if kind == 'tp' else 'Idle', rest[:1].upper() + rest[1:], 1
        purpose = next((p for p, pattern in RULES if re.search(pattern, lower)), '')
        result = {'purpose': purpose, 'target': target_name(head), 'version': version,
                  'version_rank': rank or (1 if not version else 2), 'note': note}
    result.update(OVERRIDES.get(str(entry['id']), {}))
    return result


def _write(path: str, text: str) -> None:
    """Writes beside the file and swaps it in, so an interrupted run never leaves a half-written catalog."""
    with open(path + '.tmp', 'w', encoding='utf-8', newline='\n') as out:
        out.write(text)
    os.replace(path + '.tmp', path)


def main() -> int:
    with open(CATALOG, encoding='utf-8') as source:
        catalog = json.load(source)
    problems = []
    groups = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for entry in catalog['sets']:
        entry.update(classify(entry))
        if entry['purpose'] not in PURPOSES or not entry['target']:
            problems.append(f"#{entry['id']} {entry['label'][:80]!r} -> {entry['purpose']!r} / {entry['target']!r}")
        for job in sorted({src['job'] for src in entry['sources']}):
            groups[job][entry['purpose']][entry['target']].append(entry)
    unknown = sorted(set(OVERRIDES) - {str(entry['id']) for entry in catalog['sets']})
    if unknown:
        print(f"OVERRIDES name set IDs no longer in the catalog (remove them): {', '.join(unknown)}")
    if problems:
        print(f'{len(problems)} sets could not be placed; add them to OVERRIDES:')
        print('\n'.join('  ' + p for p in problems))
        return 1
    _write(CATALOG, json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    lines = ['# Guide set groups', '',
             f"Generated by `tools/classify_guide_sets.py` from the guide snapshot of {catalog['reviewed_on']}. "
             'Each set is listed as Job → Purpose → Set, with its versions best first and the original guide '
             'title in quotes. Check that each set sits where you would look for it.', '']
    for job in sorted(groups):
        lines += [f'## {job}', '']
        for purpose in [p for p in PURPOSES if p in groups[job]]:
            targets = groups[job][purpose]
            lines.append(f'**{purpose}** ({sum(len(v) for v in targets.values())})')
            lines.append('')
            for target in sorted(targets, key=str.lower):
                versions = sorted(targets[target], key=lambda e: e['version_rank'])
                parts = [f"{e['version'] or 'only version'} (\"{e['label'][:60]}\")" for e in versions]
                lines.append(f'- {target}: ' + '; '.join(parts))
            lines.append('')
    _write(REVIEW, '\n'.join(lines))
    print(f"Classified {len(catalog['sets'])} sets; review list: {os.path.relpath(REVIEW, ROOT)}")
    return 0


if __name__ == '__main__':
    sys.exit(main())
