"""Bounded, evidenced equipment contributions, never full character statistics.

The accepted T1 evidence packet defines support. Exact description hashes pin
the inspected resource versions; unfamiliar versions/text remain unresolved.
No inferred augment magnitudes, effective caps, damage or spell simulation.
"""
from collections import OrderedDict
from dataclasses import dataclass
import hashlib
import io
import json
from pathlib import Path
import re
from types import MappingProxyType

from . import item_res
from .equipment_matching import SLOTS, allocate_requirements, units
from .guide_catalog import composition_diagnostics, normalize_slots

RULE_VERSION = 'equipment-contributions-1'
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_ROWS = 50000
INYANGA = frozenset({25577, 25793, 25831, 25882, 25949, 26207})
# English descriptions inspected read-only against T1's accepted evidence.
DESCRIPTION_HASHES = {
    11651: 'b4cfbd9654d60f60941154bcafeefc472e68deaf599ad4487840532e0fcc6543',
    13566: '03f8699a6c4bc7d5622c8c9c46d5b37ae2379f543340c3a93ff936fd82c95ec0',
    23761: 'db2e43fb44dbafe6dd35492402e44b0b58c902e95a9e1844446a853d6b0d7f49',
    24155: '66a24d211c7aa9987e0735f3ceac0bed1a91b64f7ade13f439ccc49327e2403d',
    25577: 'd61839897e68cb15a333be58b331f9ef0683d0784901bdc156244370a8c92dc2',
    25793: '9c39106310ded28d2d1e375504577829c311c1c4f4a301378c923c761b19980e',
    25831: 'e5e649b258a053cb4cf8306c1761c45d99ee6a29ef432a81fcb7b3f0707c97c7',
    25882: 'fffcaec9816e1a1bc3f0900ada7d9e159f9fbfc85a0e566d2d87762eed82e184',
    25949: '9e3bb8e414d20625bc9aac423e570beba4c73cd97ebe8372d0e16debbe131488',
    26184: '71d6925120297e7c3a4cba6ca382a27171167ede5b8e7ea96db60e465a0143b9',
    26207: 'f7749787d85c4b02d9ddb490cd6bbe85b87ff1c1099eafb6f28c16c6b8fd7bb0',
    28135: '0e240282a088656f1331b77ea50e6975c8002a48808096d2112e8e9651eb62fc',
    26002: '0071c43e3743726de2d8d893b0b595e1365981f0d384dc52f9661ee7c374f6d0',
    27645: '7a5a7767f059c7654a12ef4995f4fa6c78855a2bae54562ab2bfeced94ff7f79',
}


@dataclass(frozen=True)
class Rule:
    id: str
    evidence: tuple[str, ...]
    scope: str = 'item'
    operation: str = 'integer addition; no rounding or effective cap'
    boundary: str = 'Exact inspected English description; base equipment only'
    evidence_document: str = 'docs/GEAR-GUIDE-T1-STAT-RULES.md'


RULES = MappingProxyType({r.id: r for r in (
    Rule('flat.base.v1', ('E-FLAT-01', 'FLAT-PAIR-01')),
    Rule('defense.described.v1', ('E-DT-01', 'E-DT-02', 'DT-CATEGORY-01')),
    Rule('refresh.base.v1', ('E-REF-01', 'E-REF-03', 'REF-PAIR-01')),
    Rule('physical.multiattack.described.v1', ('MULTI-BASE-01', 'MULTI-KIND-01')),
    Rule('casting.fast-cast.described.v1', ('FC-BASE-01', 'FC-KIND-01')),
    Rule('recipient.accuracy.base.v1', ('PET-SCOPE-01', 'AVATAR-SCOPE-01')),
    Rule('refresh.inyanga.loadout.v1', ('INY-COUNT-01', 'INY-PILOT-01', 'INY-SIX-01'), 'loadout',
         'min(4, max(0, distinct qualifying pieces - 1)); once per loadout'),
    Rule('refresh.assiduity-hq.unity.v1', ('ASSID-RANK-01',), 'item',
         'verified member rank 1 -> 2; other verified valid standing -> 1; unknown -> unresolved 1..2'),
)})


@dataclass(frozen=True)
class Effect:
    stat: str
    recipient: str
    unit: str
    value: int | None
    rule_id: str
    item_id: int | None
    source_fingerprint: str
    raw: str
    condition: str = 'unconditional'
    bounds: tuple[int, int] | None = None
    slot: str = ''


@dataclass(frozen=True)
class Unresolved:
    raw: str
    reason: str
    item_id: int | None = None
    # Empty scope conservatively affects every reported result/recipient.
    keys: tuple[tuple[str, str], ...] = ()


@dataclass(frozen=True)
class Interpretation:
    effects: tuple[Effect, ...]
    unresolved: tuple[Unresolved, ...]


@dataclass(frozen=True)
class Contribution:
    recipient: str
    stat: str
    unit: str
    known: int
    complete: bool
    trace: tuple[Effect, ...]


@dataclass(frozen=True)
class Evaluation:
    contributions: tuple[Contribution, ...]
    unresolved: tuple[Unresolved, ...]
    slot_states: tuple[tuple[str, str], ...]
    partial: bool
    mode: str
    diagnostics: tuple[str, ...]

    def get(self, stat, recipient='master'):
        return next((c for c in self.contributions if c.stat == stat and c.recipient == recipient), None)


@dataclass(frozen=True)
class SourceSnapshot:
    root: str
    signature: tuple
    fingerprint: str
    items: object
    descriptions: object
    names: object = None
    hand_types: object = None


def source_signature(root):
    return tuple((name, (Path(root) / 'res' / name).stat().st_mtime_ns,
                  (Path(root) / 'res' / name).stat().st_size)
                 for name in ('items.lua', 'item_descriptions.lua'))


def prepare_source(root, cancelled=lambda: False):
    """Non-executing worker operation; bounded bytes/rows; detached English index.

    Return only immutable records. No UI, persistence or game/addon requests.
    A changing source is rejected rather than publishing a mixed generation.
    """
    root = str(Path(root).resolve())
    before = source_signature(root)
    if sum(row[2] for row in before) > MAX_SOURCE_BYTES:
        raise ValueError('Equipment resources exceed the bounded preparation size')
    digest = hashlib.sha256()
    items, descriptions = {}, {}
    remaining_bytes = MAX_SOURCE_BYTES
    for name, _, _ in before:
        if cancelled():
            raise ValueError('Equipment preparation cancelled')
        with (Path(root) / 'res' / name).open('rb') as stream:
            raw = stream.read(remaining_bytes + 1)
        if len(raw) > remaining_bytes:
            raise ValueError('Equipment resource exceeds byte limit')
        remaining_bytes -= len(raw)
        digest.update(name.encode() + b'\0' + raw)
        count, seen = 0, set()
        for line in io.StringIO(raw.decode('utf-8')):
            if cancelled():
                raise ValueError('Equipment preparation cancelled')
            if len(line) > 65536:
                raise ValueError('Equipment resource line exceeds preparation limit')
            match = item_res._ROW_RE.match(line)
            if not match:
                continue
            count += 1
            if count > MAX_ROWS:
                raise ValueError('Equipment resource exceeds row limit')
            row = {k: item_res._value(v) for k, v in item_res._FIELD_RE.findall(match[1])}
            item_id = row.get('id')
            if type(item_id) is not int or item_id in seen:
                raise ValueError('Equipment resource has invalid/duplicate item IDs')
            seen.add(item_id)
            if not isinstance(row.get('en'), str):
                continue
            if name == 'items.lua' and row.get('slots'):
                items[item_id] = item_res.Item(item_id, row['en'], row.get('enl', ''), row.get('category', ''),
                                               row['slots'], row.get('jobs', 0), row.get('level', 0),
                                               row.get('races', 0), row.get('superior_level', 0), row.get('flags', 0),
                                               row.get('skill', 0), row.get('shield_size', 0))
            elif name == 'item_descriptions.lua':
                descriptions[item_id] = row['en']
        if not count:
            raise ValueError(f'No readable resource rows in {name}')
    from .equipment_analysis import name_index
    from .equipment_hands import hand_types
    names = MappingProxyType({name: tuple(ids) for name, ids in name_index(items, cancelled).items()})
    hands = hand_types(items)
    if source_signature(root) != before or cancelled():
        raise ValueError('Equipment source changed or preparation was cancelled')
    return SourceSnapshot(root, before, digest.hexdigest(), MappingProxyType(items), MappingProxyType(descriptions), names, hands)


# Reusable exact label recognition, enabled only for inspected item/version
# contexts. Each pattern consumes its whole label/unit; damage/potency/time
# modifiers cannot match the shorter rate label.
_PATTERNS = (
    ('mnd', 'points', 'flat.base.v1', re.compile(r'(?<!\w)MND([+-]\d+)(?![\d%])')),
    ('magic_accuracy', 'points', 'flat.base.v1', re.compile(r'(?<!\w)Magic Accuracy([+-]\d+)(?![\d%])')),
    ('all_magic_skills', 'points', 'flat.base.v1', re.compile(r'All magic skills ([+-]\d+)(?![\d%])')),
    ('dt', 'percentage points', 'defense.described.v1', re.compile(r'(?<!\w)Damage taken([+-]\d+)%')),
    ('mdt', 'percentage points', 'defense.described.v1', re.compile(r'Magic Damage taken([+-]\d+)%')),
    ('pdt', 'percentage points', 'defense.described.v1', re.compile(r'Physical Damage taken([+-]\d+)%')),
    ('refresh', 'MP per 3-second tick', 'refresh.base.v1', re.compile(r'"Refresh"([+-]\d+)(?![\d%])')),
    ('double_attack', 'percentage points', 'physical.multiattack.described.v1', re.compile(r'"Double Attack"([+-]\d+)%')),
    ('triple_attack', 'percentage points', 'physical.multiattack.described.v1', re.compile(r'"Triple Attack"([+-]\d+)%')),
    ('fast_cast', 'percentage points', 'casting.fast-cast.described.v1', re.compile(r'"Fast Cast"([+-]\d+)%')),
    ('ranged_accuracy', 'points', 'recipient.accuracy.base.v1', re.compile(r'Ranged Accuracy([+-]\d+)(?![\d%])')),
    ('accuracy', 'points', 'recipient.accuracy.base.v1', re.compile(r'(?<!\w)Accuracy([+-]\d+)(?![\d%])')),
    ('critical_rate', 'percentage points', 'recipient.accuracy.base.v1', re.compile(r'Critical hit rate([+-]\d+)%')),
)


def interpret(item_id, description, fingerprint, *, scenario=None, augments=()):
    """Preserve unsupported text and observations; exact applicability fails closed."""
    scenario = scenario or {}
    effects, unresolved = [], []
    if not description or hashlib.sha256(description.encode()).hexdigest() != DESCRIPTION_HASHES.get(item_id):
        raw_augments = [augments] if isinstance(augments, str) else augments
        return Interpretation((), (Unresolved(description or '(description unavailable)',
                                               'Uninspected item/description version', item_id),) +
                              tuple(Unresolved(str(a), 'Unsupported observed augment', item_id) for a in raw_augments if str(a).strip()))
    recipient = 'master'
    for raw in description.splitlines():
        line = raw
        if line.startswith(('Pet:', 'Avatar:')):
            boundary, line = line.split(':', 1)
            recipient = boundary.casefold()
        if raw.startswith('Set:') and item_id in INYANGA:
            recipient = 'master'  # loadout effect never inherits the preceding Avatar block
            continue
        if raw.startswith('Unity Ranking:') and item_id == 28135:
            rank, member = scenario.get('unity_rank'), scenario.get('unity_member')
            verified = scenario.get('unity_verified') is True
            known = verified and member is True and type(rank) is int and rank > 0
            value = (2 if rank == 1 else 1) if known else None
            effects.append(Effect('refresh', 'master', 'MP per 3-second tick', value,
                                  'refresh.assiduity-hq.unity.v1', item_id, fingerprint, raw,
                                  'verified Unity standing' if known else 'Unity standing unknown',
                                  None if known or member is False else (1, 2)))
            if not known:
                unresolved.append(Unresolved(raw, 'Valid Unity membership/standing not established', item_id,
                                             (('master', 'refresh'),)))
            continue
        spans = []
        # Specific labels before general suffix labels to avoid double counting
        # Magic Accuracy as Accuracy or Magic Damage taken as generic DT.
        patterns = sorted(_PATTERNS, key=lambda p: p[0] in ('accuracy', 'dt'))
        for stat, unit, rule, pattern in patterns:
            allowed = ((rule == 'flat.base.v1' and item_id == 26184) or
                       (rule == 'defense.described.v1' and item_id in ({13566, 23761, 24155, 26002, 27645} | INYANGA)) or
                       (rule == 'refresh.base.v1' and item_id == 26184) or
                       (rule == 'physical.multiattack.described.v1' and item_id == 11651) or
                       (rule == 'casting.fast-cast.described.v1' and item_id in {24155, 25793}) or
                       (rule == 'recipient.accuracy.base.v1' and item_id in {23761, 24155}) or
                       (stat == 'magic_accuracy' and item_id in {23761, 24155}))
            if not allowed:
                continue
            for match in pattern.finditer(line):
                if any(match.start() < end and match.end() > start for start, end in spans):
                    continue
                spans.append(match.span())
                actual_rule = 'recipient.accuracy.base.v1' if item_id in {23761, 24155} and stat == 'magic_accuracy' else rule
                effects.append(Effect(stat, recipient, unit, int(match[1]), actual_rule, item_id, fingerprint, match[0]))
        remaining = list(line)
        for start, end in spans:
            remaining[start:end] = ' ' * (end - start)
        rest = ''.join(remaining).strip()
        if rest:
            unresolved.append(Unresolved(raw, 'Effect outside the accepted rule subset', item_id))
    for augment in ([augments] if isinstance(augments, str) else augments):
        if str(augment).strip():
            unresolved.append(Unresolved(str(augment), 'Observed augment has no supported magnitude rule', item_id))
    return Interpretation(tuple(effects), tuple(unresolved))


def sum_effects(effects, unresolved):
    grouped = {}
    for effect in effects:
        grouped.setdefault((effect.recipient, effect.stat, effect.unit), []).append(effect)
    return tuple(Contribution(recipient, stat, unit, sum(e.value for e in trace if e.value is not None),
                              all(e.value is not None for e in trace) and
                              not any(not u.keys or (recipient, stat) in u.keys for u in unresolved), tuple(trace))
                 for (recipient, stat, unit), trace in sorted(grouped.items()))


def evaluate(slots, source, *, job, context=None, hand_types=None, mode='planning', scenario=None,
             inventory=(), character='', bindings=(), snapshot_available=False, equippable_bag_ids=()):
    if mode not in ('owned', 'planning'):
        raise ValueError('Equipment evaluation requires owned or planning mode')
    slots = normalize_slots(slots)
    states = {s['slot']: s['state'] for s in slots}
    partial = len(states) != 16 or any(s == 'unknown' for s in states.values())
    if hand_types is None:
        hand_types = source.hand_types
    diagnostics = composition_diagnostics(slots, source.items, [job], hand_types=hand_types, context=context or {})
    if diagnostics:
        unknown = (Unresolved('Selection', 'Selection legality is unresolved: ' + '; '.join(diagnostics)),)
        return Evaluation((), unknown, tuple(states.items()), partial, mode, tuple(diagnostics))
    effects, unresolved, selected_ids = [], [], []
    allocation, observed = {}, []
    if mode == 'owned' and snapshot_available:
        # Callers provide canonical character/bag IDs, as for strict guide matching.
        allocation = allocate_requirements(slots, inventory, character, bindings,
                                           equippable_bag_ids=equippable_bag_ids)
        observed = list(units([r for r in inventory if r.get('character_key') == character]))
    for slot in slots:
        if slot['state'] != 'selected':
            if slot['state'] == 'unknown':
                unresolved.append(Unresolved(slot['slot'], 'Unknown selected equipment'))
            continue
        observed_augments = ()
        if mode == 'owned':
            match = allocation.get(slot['slot'])
            if not match or not match['owned']:
                unresolved.append(Unresolved(slot['slot'], 'Distinct observed copy unavailable', slot['item_id']))
                continue
            observed_augments = observed[match['unit']].get('augments', ())
            if match['ambiguous']:
                unresolved.append(Unresolved(slot['slot'], 'Observed physical copy remains ambiguous', slot['item_id']))
        elif slot['requirements']:
            unresolved.append(Unresolved(str(slot['requirements']), 'Planned augments/rank/path do not establish effects', slot['item_id']))
        interpretation = interpret(slot['item_id'], source.descriptions.get(slot['item_id']), source.fingerprint,
                                   scenario=scenario, augments=observed_augments)
        # Mark each contribution with the exact canonical slot for provenance.
        from dataclasses import replace
        effects.extend(replace(effect, slot=slot['slot']) for effect in interpretation.effects)
        unresolved.extend(interpretation.unresolved)
        if (slot['item_id'] in INYANGA and hashlib.sha256(source.descriptions.get(slot['item_id'], '').encode()).hexdigest()
                == DESCRIPTION_HASHES[slot['item_id']]):
            selected_ids.append(slot['item_id'])
    if selected_ids:
        effects.append(Effect('refresh', 'master', 'MP per 3-second tick', min(4, max(0, len(set(selected_ids)) - 1)),
                              'refresh.inyanga.loadout.v1', None, source.fingerprint,
                              'Distinct qualifying item IDs: ' + ', '.join(map(str, sorted(set(selected_ids))))))
        if partial or any(u.reason == 'Distinct observed copy unavailable' for u in unresolved):
            unresolved.append(Unresolved('Loadout membership', 'Omitted/unknown/unavailable pieces may affect set bonus',
                                         keys=(('master', 'refresh'),)))
    return Evaluation(sum_effects(effects, unresolved), tuple(unresolved), tuple(states.items()), partial, mode, ())


class EvaluationCache:
    """Bound entries and retained serialized input/result size; no persistent index."""
    def __init__(self, max_entries=256, max_bytes=2 * 1024 * 1024):
        self.max_entries, self.max_bytes = max_entries, max_bytes
        self._entries, self.retained_bytes = OrderedDict(), 0

    def clear(self):
        self._entries.clear()
        self.retained_bytes = 0

    def evaluate(self, slots, source, **kwargs):
        # All selection, observation and condition inputs contribute to the key.
        raw = json.dumps([RULE_VERSION, source.fingerprint, slots, kwargs], sort_keys=True,
                         ensure_ascii=False, allow_nan=False).encode()
        key = hashlib.sha256(raw).digest()
        if key in self._entries:
            result, _ = self._entries[key]
            self._entries.move_to_end(key)
            return result
        result = evaluate(slots, source, **kwargs)
        size = len(raw) + len(repr(result).encode()) * 4  # conservative retained-text allowance
        if size <= self.max_bytes:
            self._entries[key] = result, size
            self.retained_bytes += size
            while len(self._entries) > self.max_entries or self.retained_bytes > self.max_bytes:
                _, (_, removed) = self._entries.popitem(last=False)
                self.retained_bytes -= removed
        return result
