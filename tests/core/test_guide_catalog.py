"""Every guide set has a plain purpose, target and ranked version for the Guide upgrades picker; item links."""
from collections import defaultdict

from vanadiel_nexus.core import gear_guides, wiki


def test_every_set_has_a_purpose_from_the_fixed_list_and_a_target():
    catalog = gear_guides.load_catalog()
    assert len(catalog['sets']) >= 376
    for entry in catalog['sets']:
        assert entry['purpose'] in gear_guides.PURPOSES, entry['label']
        assert entry['target'].strip(), entry['label']
        assert isinstance(entry['version_rank'], int) and entry['version_rank'] >= 1, entry['label']


def test_picker_lists_stay_short_for_every_job():
    catalog = gear_guides.load_catalog()
    for guide in catalog['guides']:
        tree = gear_guides.picker_tree(catalog, guide['job'])
        assert len(tree) <= len(gear_guides.PURPOSES)
        for purpose, targets in tree.items():
            assert len(targets) <= 15, (guide['job'], purpose, len(targets))


def test_versions_are_ordered_best_first_and_tiers_split_from_purpose():
    catalog = gear_guides.load_catalog()
    tree = gear_guides.picker_tree(catalog, 'COR')
    assert len(tree) <= 10
    savage = tree['Weapon skill']['Savage Blade']
    assert [e['version'] for e in savage][:1] == ['Dream tier']
    assert [e['version_rank'] for e in savage] == sorted(e['version_rank'] for e in savage)
    assert {'Dream tier', 'Mid tier', 'Entry level'} <= {e['version'] for e in savage}
    by_label = {e['label']: e for e in catalog['sets']}
    assert by_label['RDM AF +4']['purpose'] == 'Gear reference'
    assert by_label['BLU (Fast Cast)']['purpose'] == 'Precast'


def test_no_target_is_split_between_purposes_for_one_job():
    catalog = gear_guides.load_catalog()
    seen = defaultdict(set)
    for entry in catalog['sets']:
        for src in entry['sources']:
            seen[(src['job'], entry['target'])].add(entry['purpose'])
    assert not {key: purposes for key, purposes in seen.items() if len(purposes) > 1}


def test_classifier_splits_tiers_from_titles_and_never_guesses_unknown_titles():
    import os
    import sys
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'tools'))
    import classify_guide_sets as classify
    assert classify.split_title('Mid Tier - Savage') == ('Savage', 'Mid tier', 3, '')
    assert classify.split_title('BLU (TP Tizona High)')[:3] == ('TP Tizona', 'High', 1)
    assert classify.split_title('BST Charm - Updated June 12th, 2025.')[0] == 'Charm'
    assert classify.split_title('Smn Phys BP Advanced v2')[:2] == ('Phys BP', 'Advanced v2')
    saved = classify.classify({'id': 'x', 'label': 'PDL Swaps - Savage'})
    assert (saved['purpose'], saved['target'], saved['version']) == ('Weapon skill', 'Savage Blade', 'PDL swaps')
    assert classify.classify({'id': 'x', 'label': 'Zzyzx Qwerty'})['purpose'] == ''


def test_item_urls_use_item_id_for_ffxiah_and_never_open_a_foreign_link_as_bg_wiki():
    urls = wiki.item_urls("Nyame Helm", 23761)
    assert urls['ffxiah'] == 'https://www.ffxiah.com/item/23761'
    assert urls['bgwiki'] == 'https://www.bg-wiki.com/ffxi/Nyame_Helm'
    assert urls['ffxiclopedia'].endswith('/wiki/Nyame_Helm')
    assert wiki.item_urls("Nyame Helm")['ffxiah'].startswith('https://www.ffxiah.com/search/item?q=Nyame')
    foreign = wiki.item_urls("Nyame Helm", wiki_url='https://www.ffxiah.com/item-sets/386031')
    assert foreign['bgwiki'] == 'https://www.bg-wiki.com/ffxi/Nyame_Helm'
    custom = wiki.item_urls("Nyame Helm", wiki_url='https://www.bg-wiki.com/ffxi/Nyame_Helm_(Path_B)')
    assert custom['bgwiki'].endswith('(Path_B)')
    assert wiki.item_urls("", None)['bgwiki'] == 'https://www.bg-wiki.com'
    assert set(wiki.item_urls("x")) == {key for key, _ in wiki.SITES}


def test_ffxiclopedia_uses_full_names_from_windower_resources(tmp_path):
    res = tmp_path / 'res'
    res.mkdir()
    (res / 'items.lua').write_text(
        'return {\n'
        '    [23637] = {id=23637,en="Chas. Culottes +3",ja="x",enl="chasseur\'s culottes +3",jal="x"},\n'
        '    [14461] = {id=14461,en="Taru. Maillot +1",ja="x",enl="Tarutaru maillot +1",jal="x"},\n'
        '    [26176] = {id=26176,en="Dim. Ring (Holla)",ja="x",enl="dimensional ring (Holla)",jal="x"},\n'
        '    [11651] = {id=11651,en="Epona\'s Ring",ja="x",enl="Epona\'s ring",jal="x"},\n'
        '}\n', encoding='utf-8')
    names = wiki.full_names(str(tmp_path))
    assert names == {23637: "Chasseur's Culottes +3", 14461: 'Tarutaru Maillot +1',
                     26176: 'Dimensional Ring (Holla)'}  # only shortened names are kept
    urls = wiki.item_urls('Chas. Culottes +3', 23637, full_name=names[23637])
    assert urls['ffxiclopedia'].endswith("/wiki/Chasseur's_Culottes_%2B3")
    assert urls['bgwiki'].endswith('/ffxi/Chas._Culottes_%2B3')  # BG-Wiki titles pages by the short name
    assert wiki.full_names(str(tmp_path / 'missing')) == {}


def test_full_names_keep_shortened_names_of_non_equipment(tmp_path):
    res = tmp_path / 'res'
    res.mkdir()
    (res / 'items.lua').write_text(
        'return {\n'
        '    [3000] = {id=3000,en="Taru F. Screen",ja="x",enl="Tarutaru folding screen",jal="x",category="General"},\n'
        '}\n', encoding='utf-8')
    assert wiki.full_names(str(tmp_path)) == {3000: 'Tarutaru Folding Screen'}
