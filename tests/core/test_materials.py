from vanadiel_nexus.core import materials as m


def test_parse_accepts_common_formats():
    parsed = m.parse_materials("Pluton x1500\n1,500 Beitetsu\nRiftborn Boulder: 30\n3x Voidhead: BLU\n- Old Case +1\n\n")
    assert parsed == [
        {"name": "Pluton", "need": 1500},
        {"name": "Beitetsu", "need": 1500},
        {"name": "Riftborn Boulder", "need": 30},
        {"name": "Voidhead: BLU", "need": 3},
        {"name": "Old Case +1", "need": 1},
    ]


def test_format_round_trips():
    mats = [{"name": "Pluton", "need": 1500}, {"name": "Voidhead: BLU", "need": 3}]
    assert m.parse_materials(m.format_materials(mats)) == mats


def test_counts_sum_across_bags_and_characters_case_insensitively():
    inv = [{"name": "Pluton", "count": 1000, "bag": "Case"}, {"name": "pluton", "count": 600, "character": "Alt"},
           {"name": "Beitetsu", "count": 5}]
    counted = m.with_counts([{"name": "Pluton", "need": 1500}, {"name": "Beitetsu", "need": 10}],
                            m.inventory_totals(inv))
    assert counted[0]["have"] == 1600 and counted[0]["done"]
    assert counted[1]["have"] == 5 and not counted[1]["done"]


def test_progress_caps_each_material_at_its_need():
    counted = [{"name": "A", "need": 10, "have": 50}, {"name": "B", "need": 10, "have": 0}]
    assert m.progress(counted) == 50.0
    assert m.progress([]) == 0.0


def test_goal_auto_count_only_when_enabled():
    totals = {"alexandrite": 19660}
    assert m.goal_current_from_inventory({"unit": "Alexandrite", "autoCount": True}, totals) == 19660
    assert m.goal_current_from_inventory({"unit": "Alexandrite"}, totals) is None
