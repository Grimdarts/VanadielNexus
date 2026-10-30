"""Configured startup detection uses launcher settings and active scripts, never generated caches."""
from vanadiel_nexus.core import windower
import pytest


def test_root_launcher_autoloads_have_sources_and_ignore_generated_cache(tmp_path):
    (tmp_path / "settings.xml").write_text(
        '<settings><autoload><addon>GearSwap</addon><plugin>Timers.dll</plugin></autoload>'
        '<profiles><profile><autoload><addon>OtherProfile</addon></autoload></profile></profiles></settings>'
    )
    scripts = tmp_path / "scripts"
    (scripts / "autoload").mkdir(parents=True)
    (scripts / "init.txt").write_text("lua load XIPivot\n")
    (scripts / "autoload" / "autoload.txt").write_text("lua load Stale\n")
    loads = windower.autoloads(str(tmp_path))
    assert loads["addons"] == {"gearswap", "xipivot"}
    assert loads["plugins"] == {"timers"}
    assert loads["sources"]["addons"] == {
        "gearswap": ["settings.xml"], "xipivot": ["scripts/init.txt"]}
    assert loads["sources"]["plugins"]["timers"] == ["settings.xml"]


@pytest.mark.parametrize("xml, expected", [
    ('<settings xmlns="urn:windower"><autoload><addon> GearSwap </addon>'
     '<plugin>Timers</plugin></autoload></settings>', {"gearswap"}),
    ('<settings><autoload><addon>Partial</addon>', set()),
])
def test_launcher_xml_namespace_and_malformed_safety(tmp_path, xml, expected):
    (tmp_path / "settings.xml").write_text(xml)
    (tmp_path / "scripts").mkdir()
    (tmp_path / "scripts" / "init.txt").write_text("lua load XIPivot\n")
    loads = windower.autoloads(str(tmp_path))
    assert loads["addons"] == expected | {"xipivot"}


def test_active_scripts_parse_comments_quotes_semicolons_and_guard_exec(tmp_path):
    scripts = tmp_path / "scripts"
    (scripts / "nested").mkdir(parents=True)
    (scripts / "init.txt").write_text(
        '// lua load Commented\n'
        'lua load "XIPivot"; lua l Skillchains // lua load Hidden; load Hidden\n'
        'exec "nested/start up.txt"; load "Timers.dll" // comment\n'
        'exec ../outside.txt; exec "' + (tmp_path / "outside.txt").as_posix() + '"\n'
        'alias shortcut "lua load NotStartup; load AlsoNot"\n'
    )
    (scripts / "nested" / "start up.txt").write_text(
        "lua load GearSwap; exec init.txt; exec missing.txt\n")
    (tmp_path / "outside.txt").write_text("lua load Escaped\n")
    loads = windower.autoloads(str(tmp_path))
    assert loads["addons"] == {"xipivot", "skillchains", "gearswap"}
    assert loads["plugins"] == {"timers"}
    assert loads["sources"]["addons"]["gearswap"] == ["scripts/nested/start up.txt"]


@pytest.mark.parametrize("source", ["settings.xml", "scripts/extra.txt"])
def test_set_autoload_refuses_uncontrolled_sources_without_writing(tmp_path, source):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    init = scripts / "init.txt"
    init.write_text("lua load GearSwap\nexec extra.txt\n")
    managed = tmp_path / source
    managed.write_text('<settings><autoload><addon>GearSwap</addon></autoload></settings>'
                       if source == "settings.xml" else "lua load GearSwap\n")
    before = {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()}
    assert windower.set_autoload(str(tmp_path), "GearSwap", "addons", True) is None
    with pytest.raises(ValueError, match=source):
        windower.set_autoload(str(tmp_path), "GearSwap", "addons", False)
    assert {p: p.read_bytes() for p in tmp_path.rglob("*") if p.is_file()} == before


@pytest.mark.parametrize("kind, name, command", [
    ("addons", "XIPivot", 'lua load "XIPivot"'),
    ("plugins", "Timers.dll", 'load "Timers.dll"'),
])
def test_init_toggle_removes_only_matching_commands_preserving_comments(tmp_path, kind, name, command):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    init = scripts / "init.txt"
    init.write_text(command + '; lua load Keep // keep comment\n'
                    'lua load KeepToo; ' + command + ' // another comment\n'
                    '// ' + command + '\n')
    assert windower.set_autoload(str(tmp_path), name, kind, False) is None
    loads = windower.autoloads(str(tmp_path))
    assert name.lower().removesuffix(".dll") not in loads[kind]
    assert loads["addons"] == {"keep", "keeptoo"}
    text = init.read_text()
    assert "// keep comment" in text and "// another comment" in text
    assert '// ' + command in text
    assert list(scripts.glob("*.bak"))


def test_installed_rows_report_startup_origins(tmp_path):
    (tmp_path / "addons" / "GearSwap").mkdir(parents=True)
    (tmp_path / "addons" / "GearSwap" / "GearSwap.lua").touch()
    (tmp_path / "plugins").mkdir()
    (tmp_path / "plugins" / "Timers.dll").touch()
    (tmp_path / "settings.xml").write_text(
        '<settings><autoload><addon>GearSwap</addon><plugin>Timers</plugin></autoload></settings>')
    for row in windower.list_addons(str(tmp_path)) + windower.list_plugins(str(tmp_path)):
        assert row["autoload"] is True
        assert row["autoload_sources"] == ["settings.xml"]


def test_exec_accepts_extensionless_script_names_and_windows_separators(tmp_path):
    scripts = tmp_path / "scripts"
    (scripts / "nested").mkdir(parents=True)
    (scripts / "init.txt").write_text('exec "nested\\startup"\n')
    (scripts / "nested" / "startup.txt").write_text("lua load GearSwap\n")
    assert windower.autoloads(str(tmp_path))["addons"] == {"gearswap"}
