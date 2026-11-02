"""Native Windows file-handle containment, using temporary fictional profiles."""
import os
import subprocess
from pathlib import Path

import pytest

from tests.core.test_managed_gearswap import env, lupa, quiet_faulthandler  # noqa: F401

MODULE = Path(__file__).parents[2] / 'staging/gearswap/PlayerSystem/integrations/windows_profile_files.lua'
pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows native reader')


@pytest.fixture
def reader(env, tmp_path):
    lua, _ = env
    root = tmp_path / 'PlayerProfiles'
    profile = root / 'example'
    (profile / 'Sets').mkdir(parents=True)
    (profile / 'Equipment.lua').write_bytes(b'return {schema=1,kind="equipment",items={}}')
    module = lua.execute(MODULE.read_bytes())
    ffi = lua.eval(b'require("ffi")')
    return module[b'new'](ffi, str(root).encode()), profile


def test_checked_read_and_missing_file(reader):
    read, profile = reader
    before = (profile / 'Equipment.lua').read_bytes()
    assert read(b'example', b'Equipment.lua', 2097152) == before
    assert read(b'example', b'Settings.lua', 2097152) is None
    assert (profile / 'Equipment.lua').read_bytes() == before


@pytest.mark.parametrize('profile,name', [(b'..', b'Equipment.lua'), (b'example/../../outside', b'Equipment.lua'),
    (b'C:\\outside', b'Equipment.lua'), (b'example', b'../outside.lua'), (b'example', b'Equipment.lua:stream')])
def test_traversal_and_unexpected_names_rejected(reader, profile, name):
    with pytest.raises(lupa.LuaError, match='invalid profile|unsupported profile'):
        reader[0](profile, name, 2097152)


def test_byte_limit_closes_handle_on_error(reader):
    read, profile = reader
    with pytest.raises(lupa.LuaError, match='bytes limit'):
        read(b'example', b'Equipment.lua', 4)
    # A leaked non-delete-sharing handle would prevent this ordinary rename.
    (profile / 'Equipment.lua').rename(profile / 'renamed.lua')


def test_directory_cannot_be_profile_source(reader):
    read, profile = reader
    (profile / 'Settings.lua').mkdir()
    with pytest.raises(lupa.LuaError, match='unexpected file type'):
        read(b'example', b'Settings.lua', 2097152)


def test_unicode_profile_root(env, tmp_path):
    lua, _ = env
    root = tmp_path / 'Profilés'
    (root / 'example').mkdir(parents=True)
    (root / 'example/Hotkeys.lua').write_bytes('return {é="中文"}'.encode())
    module = lua.execute(MODULE.read_bytes())
    read = module[b'new'](lua.eval(b'require("ffi")'), str(root).encode())
    assert read(b'example', b'Hotkeys.lua', 2097152) == 'return {é="中文"}'.encode()


def test_junction_escape_rejected(reader, tmp_path):
    read, profile = reader
    target = tmp_path / 'outside'
    target.mkdir()
    (target / 'SMN.lua').write_bytes(b'return {}')
    (profile / 'Sets').rmdir()
    # Fixed test paths, one PowerShell shell end-to-end. No deletion through a link.
    link = profile / 'Sets'
    proc = subprocess.run(['powershell', '-NoProfile', '-NonInteractive', '-Command',
                           '& { param($link,$target) New-Item -ItemType Junction -Path $link -Target $target | Out-Null }',
                           str(link), str(target)], capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    try:
        with pytest.raises(lupa.LuaError, match='reparse point rejected'):
            read(b'example', b'Sets/SMN.lua', 2097152)
        assert (target / 'SMN.lua').read_bytes() == b'return {}'
    finally:
        # Resolve and verify the parent workspace; rmdir removes only the junction.
        assert link.parent.resolve() == profile.resolve()
        os.rmdir(link)
