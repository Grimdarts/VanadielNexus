"""Independent T1 arithmetic/text oracles, entirely fictional selected snapshots."""
from dataclasses import replace
import hashlib
from pathlib import Path
from types import MappingProxyType

import pytest

from vanadiel_nexus.core import equipment_effects as e
from vanadiel_nexus.core.equipment_matching import SLOTS
from vanadiel_nexus.core.item_res import Item, SLOT_BITS

STIKINI = 'MND+8 Magic Accuracy+11\nAll magic skills +8\n"Refresh"+1'
EPONA = '"Double Attack"+3% "Triple Attack"+3%'
DEFENDING = 'Damage taken-10%'
NYAME = ('DEF:156 HP+91 MP+59 STR+26 DEX+25\nVIT+24 AGI+23 INT+28 MND+26 CHR+24\n'
         'Accuracy+40 Attack+30\nRanged Accuracy+40\nRanged Attack+30\nMagic Accuracy+40\n'
         '"Magic Atk. Bonus"+30\nEvasion+91 Magic Evasion+123\n"Magic Def. Bonus"+5 Haste+6%\n'
         'Magic burst damage +5\n"Skillchain Bonus"+5\nDamage taken-7%\nPet: Accuracy+50\n'
         'Ranged Accuracy+50\nMagic Accuracy+50')
AVATAR = ('DEF:165 HP+107 MP+91 STR+34\nDEX+31 VIT+36 AGI+33 INT+52\nMND+42 CHR+40\nMagic Accuracy+42\n'
          '"Magic Atk. Bonus"+40\nMagic Damage+22\nEvasion+87 Magic Evasion+110\n"Magic Def. Bonus"+10\n'
          'Haste+3% Enmity-10\n"Fast Cast"+10%\nDamage taken-6%\nAvatar: Accuracy+42\n'
          'Ranged Accuracy+42\nMagic Accuracy+42\nCritical hit rate+8%')
ASSIDUITY = ('DEF:105 HP+43 MP+29 STR+25 VIT+12\nAGI+17 INT+36 MND+26 CHR+19\nEvasion+27 Magic Evasion+107\n'
             '"Magic Def. Bonus"+6 Haste+5%\nEnmity-6\nAvatar perpetuation cost-3\nUnity Ranking: "Refresh"+1～2')
INY = {
    25577: 'DEF:101 HP+45 MP+50 STR+10 DEX+10\nVIT+18 INT+34 MND+33 CHR+32\nMagic Accuracy+44\nEvasion+33 Magic Evasion+114\n"Magic Def. Bonus"+8\nHaste+4% "Regen" potency +14%\nMagic Damage taken-5%\nSet: Enhances "Refresh" effect',
    25793: 'DEF:129 HP+85 MP+90 STR+16 DEX+19\nVIT+24 AGI+23 INT+48 MND+43 CHR+42\nMagic Accuracy+46\nEvasion+38 Magic Evasion+120\n"Magic Def. Bonus"+11\nHaste+2% "Fast Cast"+14%\nMagic Damage taken-8%\nSet: Enhances "Refresh" effect',
    25831: 'DEF:88 HP+35 MP+40 STR+3 DEX+23\nVIT+28 AGI+9 INT+34 MND+47 CHR+32\nMagic Accuracy+43\nEvasion+19 Magic Evasion+77\n"Magic Def. Bonus"+5\nHaste+4% Magic skills +20\nMagic Damage taken-4%\nSet: Enhances "Refresh" effect',
    25882: 'DEF:110 HP+55 MP+60 STR+19 VIT+14\nAGI+20 INT+51 MND+38 CHR+32\nMagic Accuracy+45\nEvasion+24 Magic Evasion+147\n"Magic Def. Bonus"+9\nHaste+4% Song effect duration +17%\nMagic Damage taken-6%\nSet: Enhances "Refresh" effect',
    25949: 'DEF:70 HP+25 MP+30 STR+6 DEX+6\nVIT+14 AGI+33 INT+32 MND+33 CHR+46\nMagic Accuracy+42\nEvasion+60 Magic Evasion+147\n"Magic Def. Bonus"+8\nHaste+2% Magic Damage taken-3%\nAvatar: "Blood Pact" damage +9\nSet: Enhances "Refresh" effect',
    26207: 'DEF:6 Magic Accuracy+6\nMagic Evasion+12\nMagic Damage taken-2%\nSet: Enhances "Refresh" effect',
}


@pytest.fixture
def source():
    descriptions = {26184: STIKINI, 11651: EPONA, 13566: DEFENDING, 23761: NYAME, 24155: AVATAR, 28135: ASSIDUITY, **INY}
    # Fictional resource eligibility: arithmetic tests do not claim a game-ready composition.
    items = {i: Item(i, f'Fictional item {i}', slots=0xffff, jobs=1 << 3,
                     flags=0x8000 if i in {11651, 13566, 26207} else 0) for i in descriptions}
    return e.SourceSnapshot('fictional', (), 'fictional-resources-v1', MappingProxyType(items), MappingProxyType(descriptions))


def selected(slot, item_id, **requirements):
    return {'slot': slot, 'state': 'selected', 'item_id': item_id, 'requirements': requirements}


def calc(source, slots, **kwargs):
    return e.evaluate(slots, source, job='WHM', **kwargs)


def test_flat_pair_and_refresh_are_distinct_keys_and_units(source):
    result = calc(source, [selected('ring1', 26184), selected('ring2', 26184)])
    assert result.get('mnd').known == 16
    assert result.get('magic_accuracy').known == 22
    assert result.get('all_magic_skills').known == 16
    assert result.get('refresh').known == 2
    assert result.get('refresh').unit == 'MP per 3-second tick'
    assert result.get('refresh').complete
    assert result.partial and result.mode == 'planning'
    assert {t.slot for t in result.get('refresh').trace} == {'ring1', 'ring2'}


def test_owned_shortage_does_not_sum_target_rows(source):
    slots = [selected('ring1', 26184), selected('ring2', 26184)]
    observed = [{'item_id': 26184, 'character_key': 'alice', 'bag_id': 8, 'count': 1}]
    result = calc(source, slots, mode='owned', inventory=observed, character='alice', snapshot_available=True)
    assert result.get('refresh').known == 1
    assert not result.get('refresh').complete
    assert any('copy unavailable' in u.reason for u in result.unresolved)
    result = calc(source, slots, mode='owned', inventory=observed, character='alice', snapshot_available=False)
    assert result.get('refresh') is None
    assert len(result.unresolved) == 2


def test_master_pet_and_avatar_do_not_merge(source):
    nyame = calc(source, [selected('head', 23761)])
    assert nyame.get('accuracy').known == 40
    assert nyame.get('accuracy', 'pet').known == 50
    assert nyame.get('magic_accuracy').known == 40
    assert nyame.get('magic_accuracy', 'pet').known == 50
    avatar = calc(source, [selected('body', 24155)])
    assert avatar.get('magic_accuracy').known == 42
    assert avatar.get('magic_accuracy', 'avatar').known == 42
    assert avatar.get('critical_rate', 'avatar').known == 8
    assert avatar.get('critical_rate') is None
    assert avatar.get('fast_cast').known == 10
    assert avatar.get('dt').known == -6
    assert avatar.get('dt', 'avatar') is None
    assert not avatar.get('magic_accuracy').complete  # unrelated unsupported fields remain visible


@pytest.mark.parametrize('count,expected', [(0, 0), (1, 0), (2, 1), (3, 2), (4, 3), (5, 4), (6, 4)])
def test_inyanga_count_once_with_six_piece_cap(source, count, expected):
    ids = list(INY)[:count]
    slots = [selected(s, i) for s, i in zip(('head', 'body', 'hands', 'legs', 'feet', 'ring1'), ids)]
    slots += [{'slot': s, 'state': 'empty'} for s in SLOTS if s not in {r['slot'] for r in slots}]
    result = calc(source, slots)
    refresh = result.get('refresh')
    assert (refresh.known if refresh else 0) == expected
    if count:
        assert len(refresh.trace) == 1
        assert refresh.trace[0].rule_id == 'refresh.inyanga.loadout.v1'
        assert refresh.recipient == 'master'


def test_inyanga_partial_membership_and_unknown_versions_remain_uncertain(source):
    result = calc(source, [selected('head', 25577), selected('hands', 25831), selected('feet', 25949), selected('ring1', 26207)])
    assert result.get('refresh').known == 3
    assert not result.get('refresh').complete
    assert any('membership' in u.raw.lower() for u in result.unresolved)
    descriptions = dict(source.descriptions)
    descriptions[25577] += '\nNew uninspected effect'
    changed = replace(source, descriptions=MappingProxyType(descriptions), fingerprint='changed')
    result = calc(changed, [selected('head', 25577), selected('ring1', 26207)])
    assert result.get('refresh').known == 0
    assert not result.get('refresh').complete


@pytest.mark.parametrize('scenario,expected,bounds', [
    ({'unity_member': True, 'unity_verified': True, 'unity_rank': 1}, 2, None),
    ({'unity_member': True, 'unity_verified': True, 'unity_rank': 2}, 1, None),
    ({'unity_member': True}, None, (1, 2)), ({'unity_member': False}, None, None),
    ({'unity_member': True, 'unity_verified': True, 'unity_rank': 0}, None, (1, 2)),
])
def test_unity_standing_is_not_augmentation_rank(scenario, expected, bounds):
    result = e.interpret(28135, ASSIDUITY, 'fixture', scenario=scenario, augments=['Rank 15'])
    refresh = next(v for v in result.effects if v.stat == 'refresh')
    assert refresh.value == expected and refresh.bounds == bounds
    assert any(u.raw == 'Rank 15' for u in result.unresolved)


def test_damage_categories_do_not_match_suffixes_or_effective_caps(source):
    result = calc(source, [selected('ring1', 13566), selected('head', 25577), selected('hands', 25831)])
    assert result.get('dt').known == -10
    assert result.get('mdt').known == -9
    assert all(c.stat not in ('effective_dt', 'cap', 'incoming_damage') for c in result.contributions)
    assert not result.get('dt').complete


def test_multiattack_rates_are_separate_not_damage_or_proc_model(source):
    result = calc(source, [selected('ring1', 11651)])
    assert result.get('double_attack').known == 3 and result.get('triple_attack').known == 3
    assert result.get('double_attack').complete
    assert not e.interpret(11651, '"Double Attack" damage+20%', 'fixture').effects
    assert not e.interpret(26184, 'Enhances "Refresh" effect', 'fixture').effects


def test_uninspected_text_and_augments_cannot_supply_magnitudes(source):
    result = calc(source, [selected('ring1', 26184, rank=15, augments=['Refresh+8'])])
    assert result.get('refresh').known == 1 and not result.get('refresh').complete
    unknown = e.interpret(99999, None, 'fixture', augments=['A+1'])
    assert len(unknown.unresolved) == 2 and not unknown.effects
    mutated = e.interpret(26184, STIKINI.replace('+1', '+9'), 'new-source')
    assert not mutated.effects and mutated.unresolved


def test_illegal_rare_duplicates_and_alias_collisions_do_not_certify(source):
    result = calc(source, [selected('ring1', 13566), selected('ring2', 13566)])
    assert not result.contributions and result.diagnostics
    with pytest.raises(ValueError):
        calc(source, [selected('ring1', 26184), selected('left_ring', 26184)])


def test_owned_character_requirements_and_augment_uncertainty(source):
    slots = [selected('ring1', 26184, rank=15)]
    obs = [{'item_id': 26184, 'character_key': 'bob', 'augments': 'Rank 15'}]
    assert not calc(source, slots, mode='owned', inventory=obs, character='alice', snapshot_available=True).contributions
    obs[0]['character_key'] = 'alice'
    result = calc(source, slots, mode='owned', inventory=obs, character='alice', snapshot_available=True)
    assert result.get('refresh').known == 1 and not result.get('refresh').complete


def test_cache_eviction_source_rule_conditions_and_immutable_results(source, monkeypatch):
    cache = e.EvaluationCache(max_entries=2, max_bytes=100000)
    slots = [selected('ring1', 26184)]
    first = cache.evaluate(slots, source, job='WHM')
    assert cache.evaluate(slots, source, job='WHM') is first
    second = cache.evaluate(slots, replace(source, fingerprint='v2'), job='WHM')
    assert second is not first
    monkeypatch.setattr(e, 'RULE_VERSION', 'new-rules')
    assert cache.evaluate(slots, source, job='WHM') is not first
    assert len(cache._entries) == 2 and cache.retained_bytes < 100000
    cache.clear()
    assert cache.evaluate(slots, source, job='WHM') == first
    small = e.EvaluationCache(max_bytes=1)
    assert small.evaluate(slots, source, job='WHM') == first
    assert not small._entries and small.retained_bytes == 0


def write_source(root, *, duplicate=False):
    folder = root / 'res'
    folder.mkdir(parents=True)
    item = '[1] = {id=26184,en="Fictional Ring",slots=24576,jobs=8},\n'
    (folder / 'items.lua').write_text(item * (2 if duplicate else 1), encoding='utf-8')
    import json
    (folder / 'item_descriptions.lua').write_text('[1] = {id=26184,en=' + json.dumps(STIKINI) + '},\n', encoding='utf-8')
    return root


def test_preparation_is_detached_bounded_and_nonexecuting(tmp_path, monkeypatch):
    root = write_source(tmp_path / 'source')
    source = e.prepare_source(root)
    assert source.items[26184].en == 'Fictional Ring'
    assert source.descriptions[26184] == STIKINI
    with pytest.raises(TypeError):
        source.descriptions[1] = 'mutate'
    before = source.fingerprint
    with (root / 'res/items.lua').open('a') as stream:
        stream.write('-- data-only input; never execute Lua\n')
    assert e.prepare_source(root).fingerprint != before
    with pytest.raises(ValueError, match='cancelled'):
        e.prepare_source(root, lambda: True)
    monkeypatch.setattr(e, 'MAX_SOURCE_BYTES', 1)
    with pytest.raises(ValueError, match='size'):
        e.prepare_source(root)


def test_duplicate_and_missing_resources_reject(tmp_path):
    with pytest.raises(ValueError, match='duplicate'):
        e.prepare_source(write_source(tmp_path / 'duplicate', duplicate=True))
    with pytest.raises(OSError):
        e.prepare_source(tmp_path / 'missing')


def test_raw_categories_compatible_units_and_fast_cast_arithmetic():
    def effect(stat, value, unit='percentage points', recipient='master'):
        return e.Effect(stat, recipient, unit, value, 'fixture-only', None, 'fictional', 'Independent input')
    effects = (effect('dt', -10), effect('pdt', -5), effect('fast_cast', 10), effect('fast_cast', 5),
               effect('bdt', -2), effect('accuracy', 40, 'points'), effect('accuracy', 50, 'points', 'pet'))
    unsupported = (e.Unresolved('Unknown MDT augment', 'Breath interpretation unresolved', keys=(('master', 'bdt'),)),)
    result = {(c.recipient, c.stat): c for c in e.sum_effects(effects, unsupported)}
    assert result['master', 'dt'].known == -10 and result['master', 'pdt'].known == -5
    assert result['master', 'fast_cast'].known == 15
    assert result['master', 'accuracy'].known == 40 and result['pet', 'accuracy'].known == 50
    assert not result['master', 'bdt'].complete
    assert result['master', 'dt'].complete


def test_pdt_pin_cannot_be_counted_as_generic_dt():
    text = 'DEF:114 Accuracy+15 Attack+15\nShield skill +112 "Counter"+4\nChance of successful block +6\nPhysical Damage taken-10%'
    result = e.interpret(27645, text, 'fictional')
    assert [(v.stat, v.value) for v in result.effects] == [('pdt', -10)]


def test_preparation_rejects_overlong_rows_and_changes_during_parse(tmp_path, monkeypatch):
    root = write_source(tmp_path / 'huge')
    (root / 'res/items.lua').write_text('x' * 65537)
    with pytest.raises(ValueError, match='line exceeds'):
        e.prepare_source(root)
    root = write_source(tmp_path / 'change')
    signature = e.source_signature
    calls = []
    def changed(root):
        value = signature(root)
        calls.append(value)
        return value if len(calls) == 1 else value + (('different', 0, 0),)
    monkeypatch.setattr(e, 'source_signature', changed)
    with pytest.raises(ValueError, match='changed'):
        e.prepare_source(root)
