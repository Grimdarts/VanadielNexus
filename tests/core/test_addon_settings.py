import os

from vanadiel_nexus.core import addon_settings as s

SAMPLE = """<?xml version="1.1" ?>
<settings>
    <!-- keep me -->
    <global>
        <bg>
            <alpha>72</alpha>
            <blue>0</blue>
            <green>0</green>
            <red>0</red>
        </bg>
        <hide_on_zone>true</hide_on_zone>
        <pos>
            <x>500</x>
            <y>500</y>
        </pos>
        <label>Hello</label>
    </global>
    <Someonesmall>
        <hide_on_zone>false</hide_on_zone>
    </Someonesmall>
</settings>
"""


def write_sample(tmp_path):
    data = tmp_path / "addon" / "data"
    data.mkdir(parents=True)
    (data / "settings.xml").write_text(SAMPLE, encoding="utf-8")
    (data / "colors.xml").write_text("<settings/>", encoding="utf-8")
    return str(data / "settings.xml")


def test_parses_xml_1_1_and_lists_sections(tmp_path):
    f = s.SettingsFile(write_sample(tmp_path))
    assert f.declaration.startswith('<?xml version="1.1"')
    assert f.sections() == ["global", "Someonesmall"]


def test_edit_and_save_keeps_declaration_comments_and_backup(tmp_path):
    path = write_sample(tmp_path)
    f = s.SettingsFile(path)
    f.root.find("global/pos/x").text = "640"
    f.save()
    text = open(path, encoding="utf-8").read()
    assert text.startswith('<?xml version="1.1" ?>')
    assert "<!-- keep me -->" in text and "<x>640</x>" in text and "<label>Hello</label>" in text
    assert any(n.endswith(".bak") for n in os.listdir(os.path.dirname(path)))
    assert s.SettingsFile(path).root.find("Someonesmall/hide_on_zone").text == "false"


def test_value_kinds_and_color_groups(tmp_path):
    f = s.SettingsFile(write_sample(tmp_path))
    assert s.value_kind("true") == "bool" and s.value_kind("-12") == "int"
    assert s.value_kind("1.5") == "float" and s.value_kind("Hello") == "text"
    assert s.is_color_group(f.root.find("global/bg"))
    assert not s.is_color_group(f.root.find("global/pos"))
    assert s.is_leaf(f.root.find("global/label"))


def test_settings_files_lists_settings_xml_first(tmp_path):
    write_sample(tmp_path)
    names = [os.path.basename(p) for p in s.settings_files(str(tmp_path / "addon"))]
    assert names == ["settings.xml", "colors.xml"]


def test_real_style_file_round_trips_unchanged_values(tmp_path):
    path = write_sample(tmp_path)
    before = {el.tag: el.text for el in s.SettingsFile(path).root.iter() if isinstance(el.tag, str)}
    s.SettingsFile(path).save()
    after = {el.tag: el.text for el in s.SettingsFile(path).root.iter() if isinstance(el.tag, str)}
    assert {k: (v or "").strip() for k, v in before.items()} == {k: (v or "").strip() for k, v in after.items()}


def test_numeric_list_tags_survive_a_round_trip(tmp_path):
    data = tmp_path / "data"
    data.mkdir()
    path = data / "settings.xml"
    path.write_text('<?xml version="1.1" ?>\n<settings><global><fonts><1>consolas</1><2>courier new</2></fonts>'
                    "</global></settings>\n", encoding="utf-8")
    f = s.SettingsFile(str(path))
    fonts = f.root.find("global/fonts")
    assert [s.display_tag(c.tag) for c in fonts] == ["1", "2"]
    f.save()
    assert "<1>consolas</1>" in path.read_text(encoding="utf-8")
