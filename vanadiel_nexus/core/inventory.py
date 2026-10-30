"""Inventory: classify items into categories and roll up stacks across bags and characters."""

ITEM_CATEGORIES = [
    "💎 Upgrade Currencies & REMA / JSE Mats",
    "⚔️ Weapons (Main / Sub)",
    "🛡️ Shields, Grips & Straps",
    "🏹 Ranged & Ammo",
    "👑 Head & Neck",
    "🧥 Body & Hands",
    "👖 Legs, Feet & Waist",
    "💍 Rings, Earrings & Back (Capes)",
    "🧪 Consumables, Food & Medicines",
    "📦 General, Pop Items & Storage"
]


def classify_ffxi_item(name: str, category_hint: str = "", augments: str = "") -> str:
    """
    Classifies an FFXI item into one of the 10 display categories for Page 4.
    """
    nl = (name or "").lower().strip()
    ch = (category_hint or "").lower().strip()

    # 1. Check Upgrade Currencies & REMA / JSE Materials first
    currency_keywords = (
        "alexandrite", "pluton", "beitetsu", "riftborn boulder", "heavy metal plate",
        "riftdross", "riftcinder", "card", "voidhead", "voidtorso", "voidhand", "voidleg",
        "voidfoot", "headshard", "torsoshard", "handshard", "legshard", "footshard",
        "lustreless", "starstone", "gallimaufry", "eikondrite", "abjuration", "detritus",
        "scale", "byne bill", "bronzepiece", "whiteshell", "silverpiece", "goldpiece",
        "jade", "cinder", "dross", "mulcibar", "pouch", "case +1", "case +2", "voucher",
        "seal", "crest", "orb", "corpselight", "siren's hair", "niobium", "lightweave",
        "scrap", "organ", "chip", "stone +1", "stone +2", "medal"
    )
    # Exclude actual equippable rings/earrings/capes/ammo from currency match
    gear_suffixes = (
        "ring", "earring", "cape", "mantle", "shawl", "belt", "sash", "obi", "rope",
        "yotai", "tathlum", "bomblet", "feather", "pinion", "arrow", "bullet", "bolt",
        "shuriken", "boomerang", "chakram", "shield", "buckler", "grip", "strap",
        "helm", "hat", "cap", "crown", "masque", "mask", "bandeau", "coif", "keffiyeh",
        "kavuk", "mortarboard", "bonnet", "chapeau", "chappel", "galea", "visor",
        "hairpin", "hood", "tam", "sallet", "headpiece", "zucchetto", "coronal",
        "coat", "lorica", "breastplate", "mail", "surcoat", "tabard", "jubbah",
        "mintan", "doublet", "gown", "sayon", "kaftan", "jacket", "platemail",
        "harness", "corazza", "robe", "chasuble", "chas.", "jupon", "vest", "tunic",
        "tunica", "apron", "garb", "kalasiris", "shomonjijoe", "cuirie",
        "gauntlets", "mufflers", "gloves", "mitts", "mittens", "bracers", "bazubands",
        "gantherots", "mitons", "cuffs", "wrist.", "dastanas", "fin. ga.", "manopolas",
        "bazu.", "armlets", "gages",
        "cuisses", "trousers", "subligar", "pants", "slops", "tights", "fuseau",
        "spats", "shalwar", "tayt", "chausses", "cosciales", "lappas", "braconi",
        "seraweels", "sera.", "hose", "guards",
        "greaves", "calligae", "boots", "bottes", "sollerets", "sabots", "pumps",
        "pigaches", "loafers", "houseaux", "charuqs", "basmak", "leggings", "gambieras",
        "jam.", "clogs", "crackows", "gaiters", "galosh.", "socks", "ocreae",
        "torque", "gorget", "necklace", "pendant", "collar", "amulet", "choker",
        "beads", "locket", "charm", "kubikazari"
    )

    is_obvious_gear = any(g in nl for g in gear_suffixes) or bool((augments or "").strip())

    if not is_obvious_gear and any(k in nl for k in currency_keywords):
        return "💎 Upgrade Currencies & REMA / JSE Mats"

    # 2. Consumables, Food & Medicines
    consumable_keywords = (
        "daifuku", "sushi", "ramen", "akamochi", "stewpot", "crepe", "pie", "bun",
        "echo drops", "remedy", "holy water", "panacea", "antacid", "elixir",
        "potion", "ether", "milk", "juice", "cluster", "crystal", "reraiser",
        "warp", "tabula", "forbidden key", "linkpearl", "linkshell"
    )
    if not is_obvious_gear and (any(k in nl for k in consumable_keywords) or "consumable" in ch):
        return "🧪 Consumables, Food & Medicines"

    # 3. Shields, Grips & Straps
    if any(k in nl for k in ("shield", "buckler", "grip", "strap", "culminus", "sors", "ammurapi", "adapa", "genmei shield", "beatific shield")) or "shield" in ch:
        return "🛡️ Shields, Grips & Straps"

    # 4. Ranged & Ammo
    if any(k in nl for k in (
        "tathlum", "bomblet", "feather", "pinion", "sachet", "treatise", "eye",
        "floestone", "focal orb", "sapience orb", "ginsen", "hydrocera", "impatiens",
        "knobkierrie", "yamarang", "shuriken", "boomerang", "bow", "gun", "crossbow",
        "fomalhaut", "death penalty", "gastraphetes", "annihilator", "armageddon",
        "fail-not", "yoichinoyumi", "gjallarhorn", "daurdabla", "marsyas", "yasakani",
        "regal gem", "esper stone", "kalboron stone", "ghastly", "pemphredo", "staunch"
    )) or "ranged" in ch:
        return "🏹 Ranged & Ammo"

    # 5. Weapons (Main / Sub)
    weapon_keywords = (
        "chango", "ukonvasara", "burtgang", "laphria", "nirvana", "tizona", "epeolatry",
        "lionheart", "naegling", "colada", "aettir", "arktoi", "chidori", "izhiikoh",
        "nibiru", "akademos", "coeus", "odium", "isuka", "rubicundity", "espiritus",
        "gridarvor", "fettering", "raicho", "siriti", "chatoyant", "keraunos",
        "bolelabunga", "rogetsurin", "kannakiri", "excalipoor", "gada", "pukulatmuj",
        "hepatizon", "deacon", "sword", "blade", "saber", "axe", "chopper", "katana",
        "cudgel", "rod", "staff", "pole", "scythe", "lance", "spear", "dagger", "knife",
        "claws", "fists", "bell", "virga", "brand", "debahocho", "serenity"
    )
    if any(k in nl for k in weapon_keywords) or "weapon" in ch:
        return "⚔️ Weapons (Main / Sub)"

    # 6. Head & Neck
    head_neck_keywords = (
        "helm", "hat", "cap", "crown", "masque", "mask", "bandeau", "coif", "keffiyeh",
        "kavuk", "mortarboard", "m.board", "bonnet", "chapeau", "chappel", "galea",
        "visor", "hairpin", "hood", "tam", "sallet", "headpiece", "zucchetto", "coronal",
        "horn", "beret", "band", "head",
        "torque", "gorget", "necklace", "pendant", "collar", "amulet", "choker",
        "beads", "locket", "charm", "kubikazari"
    )
    if any(k in nl for k in head_neck_keywords) or "head" in ch:
        return "👑 Head & Neck"

    # 7. Body & Hands
    body_hands_keywords = (
        "coat", "lorica", "breastplate", "mail", "surcoat", "tabard", "jubbah",
        "mintan", "doublet", "gown", "sayon", "kaftan", "jacket", "platemail",
        "harness", "corazza", "robe", "chasuble", "chas.", "jupon", "vest", "tunic",
        "tunica", "apron", "garb", "kalasiris", "shomonjijoe", "cuirie", "cloak", "body",
        "gauntlets", "mufflers", "gloves", "mitts", "mittens", "bracers", "bazubands",
        "gantherots", "mitons", "cuffs", "wrist.", "dastanas", "fin. ga.", "manopolas",
        "bazu.", "babu.", "armlets", "gages", "hands"
    )
    if any(k in nl for k in body_hands_keywords) or "body" in ch:
        return "🧥 Body & Hands"

    # 8. Legs, Feet & Waist
    legs_feet_waist_keywords = (
        "cuisses", "trousers", "subligar", "pants", "slops", "tights", "fuseau",
        "spats", "shalwar", "tayt", "chausses", "cosciales", "lappas", "braconi",
        "seraweels", "sera.", "hose", "guards", "legs",
        "greaves", "calligae", "boots", "bottes", "sollerets", "sabots", "pumps",
        "pigaches", "loafers", "houseaux", "charuqs", "basmak", "leggings", "gambieras",
        "jam.", "clogs", "crackows", "gaiters", "galosh.", "socks", "ocreae", "feet",
        "belt", "sash", "obi", "rope", "yotai", "stone"
    )
    if any(k in nl for k in legs_feet_waist_keywords) or "legs" in ch:
        return "👖 Legs, Feet & Waist"

    # 9. Rings, Earrings & Back (Capes)
    ring_ear_back_keywords = (
        "ring", "band", "earring", "suppanomimi", "cape", "mantle", "shawl"
    )
    if any(k in nl for k in ring_ear_back_keywords) or "ring" in ch:
        return "💍 Rings, Earrings & Back (Capes)"

    return "📦 General, Pop Items & Storage"


def consolidate_inventory_items(raw_inventory: list) -> list:
    """
    Consolidates raw inventory items according to Jason's rules:
    1. Stackables / Currencies / Unaugmented identical items are totaled across
       all bags and characters.
    2. Same-name gear pieces with DIFFERENT augments are NEVER merged together;
       each unique (name, augment) pair remains its own distinct entry.
    3. Detects and flags when the same (name, augment) exists in 2 or more
       bags/characters ("scattered": True, "bag_count": N).
    """
    grouped = {}
    order_keys = []

    for row in raw_inventory:
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        cnt = int(row.get("count", 1) or 1)
        char_name = str(row.get("character", "Main")).strip() or "Main"
        bag_name = str(row.get("bag", "Inventory")).strip() or "Inventory"
        augments = str(row.get("augments", "")).strip()
        cat_hint = str(row.get("category", "")).strip()

        # Grouping key includes normalized name AND normalized augments so
        # same-name gear with different augments stays strictly separated!
        key = (name.lower(), augments.lower())

        if key not in grouped:
            category = classify_ffxi_item(name, cat_hint, augments)
            grouped[key] = {
                "name": name,
                "augments": augments,
                "category": category,
                "total_count": 0,
                "locations": [],       # list of dicts: {"character": ..., "bag": ..., "count": ...}
                "characters_set": set(),
                "bags_set": set(),
            }
            order_keys.append(key)

        entry = grouped[key]
        entry["total_count"] += cnt
        entry["locations"].append({
            "character": char_name,
            "bag": bag_name,
            "count": cnt
        })
        entry["characters_set"].add(char_name)
        entry["bags_set"].add(f"{char_name}:{bag_name}")

    results = []
    for key in order_keys:
        e = grouped[key]
        loc_parts = []
        for loc in e["locations"]:
            if loc["count"] > 1:
                loc_parts.append(f"{loc['character']} • {loc['bag']} ({loc['count']:,})")
            else:
                loc_parts.append(f"{loc['character']} • {loc['bag']}")

        bag_slot_count = len(e["locations"])
        is_scattered = bag_slot_count > 1

        results.append({
            "name": e["name"],
            "augments": e["augments"],
            "category": e["category"],
            "total_count": e["total_count"],
            "bag_count": bag_slot_count,
            "scattered": is_scattered,
            "scattered_badge": f"⚠️ SCATTERED ({bag_slot_count} bags)" if is_scattered else "✅ Single Bag",
            "locations_str": "  |  ".join(loc_parts),
            "characters": sorted(list(e["characters_set"])),
            "bags": [loc["bag"] for loc in e["locations"]],
            "raw_locations": e["locations"]
        })

    return results
