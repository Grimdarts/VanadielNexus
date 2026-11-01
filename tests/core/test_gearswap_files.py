import os
from pathlib import Path

import pytest

from vanadiel_nexus.core import gearswap_files as gf


def touch(path: Path, text='-- test'):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding='utf-8')
    return path


@pytest.fixture
def win(tmp_path):
    (tmp_path / 'windower' / 'addons' / 'GearSwap' / 'data').mkdir(parents=True)
    (tmp_path / 'appdata').mkdir()
    return tmp_path / 'windower'


@pytest.fixture
def appdata(tmp_path):
    return str(tmp_path / 'appdata')


def test_job_file_names_in_gearswap_order():
    assert gf.job_file_names('Alice', 'BLU', 'Blue Mage') == [
        'Alice_BLU.lua', 'Alice-BLU.lua', 'Alice_Blue Mage.lua', 'Alice-Blue Mage.lua', 'Alice.lua', 'BLU.lua',
        'Blue Mage.lua', 'default.lua']


def test_search_dirs_are_the_nine_bases(win, appdata):
    dirs = gf.search_dirs(str(win), 'Alice', appdata)
    gs = win / 'addons' / 'GearSwap'
    app = Path(appdata) / 'Windower' / 'GearSwap'
    assert dirs == [str(gs / 'libs-dev'), str(gs / 'libs'), str(gs / 'data' / 'Alice'), str(gs / 'data' / 'common'),
                    str(gs / 'data'), str(app / 'Alice'), str(app / 'common'), str(app),
                    str(win / 'addons' / 'libs')]


@pytest.mark.parametrize('base', ['libs-dev', 'libs', 'data/Alice', 'data/common', 'data'])
@pytest.mark.parametrize('name', gf.job_file_names('Alice', 'BLU', 'Blue Mage'))
def test_every_name_in_every_gearswap_dir_is_found(win, appdata, base, name):
    path = touch(win / 'addons' / 'GearSwap' / base / name)
    found = gf.find_job_file(str(win), 'Alice', 'BLU', appdata)
    assert Path(found.path) == path
    assert found.shared == (name in ('Alice.lua', 'BLU.lua', 'Blue Mage.lua', 'default.lua'))


def test_character_folder_beats_data_and_names_beat_later_dirs(win, appdata):
    data = win / 'addons' / 'GearSwap' / 'data'
    touch(data / 'Alice_BLU.lua')
    folder = touch(data / 'Alice' / 'BLU.lua')
    assert Path(gf.find_job_file(str(win), 'Alice', 'BLU', appdata).path) == folder  # directory order first


def test_libs_and_appdata_dirs_are_searched(win, appdata):
    lib = touch(win / 'addons' / 'libs' / 'Alice_BLU.lua')
    assert Path(gf.find_job_file(str(win), 'Alice', 'BLU', appdata).path) == lib
    app = touch(Path(appdata) / 'Windower' / 'GearSwap' / 'Alice_BLU.lua')
    found = gf.find_job_file(str(win), 'Alice', 'BLU', appdata)
    assert Path(found.path) == app
    assert gf.inside_roots(found.path, gf.allowed_roots(str(win), appdata))


def test_include_path_is_tried_per_filename(win, appdata):
    data = win / 'addons' / 'GearSwap' / 'data'
    touch(data / 'p' / 'Alice_BLU.lua')
    touch(data / 'BLU.lua')
    names = gf.job_file_names('Alice', 'BLU', 'Blue Mage')
    found = [p for p in gf.candidates(str(win), 'Alice', names, 'p', appdata) if os.path.isfile(p)]
    assert Path(found[0]) == data / 'p' / 'Alice_BLU.lua'
    touch(data / 'Alice_BLU.lua')
    touch(data / 'p' / 'BLU.lua')
    (data / 'p' / 'Alice_BLU.lua').unlink()
    found = [p for p in gf.candidates(str(win), 'Alice', names, 'p', appdata) if os.path.isfile(p)]
    assert Path(found[0]) == data / 'Alice_BLU.lua'  # data/Alice_BLU.lua beats data/p/BLU.lua


def test_searched_is_filled_when_nothing_is_found(win, appdata):
    found = gf.find_job_file(str(win), 'Alice', 'BLU', appdata)
    assert found.path is None and not found.shared
    assert len(found.searched) == 9 * 8
    assert str(win / 'addons' / 'GearSwap' / 'data' / 'Alice_BLU.lua') in found.searched


def test_resolve_include_lowercases_and_returns_earlier_candidates(win, appdata):
    lib = touch(win / 'addons' / 'GearSwap' / 'libs' / 'mote-include.lua')
    path, earlier = gf.resolve_include('Mote-Include', str(win), 'Alice', appdata=appdata)
    assert Path(path) == lib
    assert earlier == [str(win / 'addons' / 'GearSwap' / 'libs-dev' / 'mote-include.lua')]
    assert gf.resolve_include('missing', str(win), 'Alice', appdata=appdata)[0] is None


def test_characters_with_files(win):
    data = win / 'addons' / 'GearSwap' / 'data'
    touch(data / 'Alice_BLU.lua')
    touch(data / 'Bob-Summoner.lua')
    touch(data / 'Carol' / 'WAR.lua')
    touch(data / 'Nova-BLU-sets.lua')
    touch(data / 'Someone-Augments-lib.lua')
    touch(data / 'icons' / 'readme.txt')
    touch(data / 'common' / 'BLU.lua')
    assert gf.characters_with_files(str(win)) == {'Alice', 'Bob', 'Carol'}
