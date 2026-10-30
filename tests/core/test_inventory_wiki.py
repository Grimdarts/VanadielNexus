from vanadiel_nexus.core import inventory, wiki


def item(name, count, bag, character="A", augments=""):
    return {"name": name, "count": count, "character": character, "bag": bag, "augments": augments}


def test_stackables_roll_up_across_bags():
    rows = inventory.consolidate_inventory_items([
        item("Alexandrite", 1240, "Mog Case"), item("Alexandrite", 380, "Mog Satchel"),
    ])
    alex = [r for r in rows if r["name"] == "Alexandrite"]
    assert len(alex) == 1 and alex[0]["total_count"] == 1620 and alex[0]["scattered"]


def test_same_gear_with_different_augments_stays_separate():
    rows = inventory.consolidate_inventory_items([
        item("Rosmerta's Cape", 1, "Wardrobe 1", augments="DEX+20"),
        item("Rosmerta's Cape", 1, "Wardrobe 2", augments="INT+20"),
    ])
    assert len([r for r in rows if r["name"] == "Rosmerta's Cape"]) == 2


def test_classify_returns_a_known_category():
    cat = inventory.classify_ffxi_item("Alexandrite")
    assert isinstance(cat, str) and cat


def test_wiki_urls_and_parsing():
    urls = wiki.build_wiki_urls("Lugalbanda Earring")
    assert "bg-wiki.com" in urls["bgwiki"] and "Lugalbanda_Earring" in urls["bgwiki"]
    parsed = wiki.parse_wiki_url_or_name("https://www.bg-wiki.com/ffxi/Lugalbanda_Earring")
    assert parsed["name"] == "Lugalbanda Earring"
    assert wiki.parse_wiki_url_or_name("Nyame Helm")["name"] == "Nyame Helm"
