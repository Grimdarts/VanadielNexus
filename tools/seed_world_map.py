#!/usr/bin/env python3
"""Seed and validate vanadiel_nexus/resources/world_map_data.json.

Combines:
1. Canonical Windower zone IDs, names, and `can_mount` flags from `res/zones.lua`
2. Unescaped Home Point crystal lists from `addons/Homepoints/map.lua` + post-2015 additions
3. Curated Vana'diel zone-to-zone connectivity (`edges[]`), Survival Guide flags, and Era clusters
4. Deterministic regional sector placement + bounding-box collision relaxation (`3600 x 2400`)
"""
from __future__ import annotations

import json
import math
import os
import re
import sys
from collections import deque

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_PATH = os.path.join(REPO_ROOT, "vanadiel_nexus", "resources", "world_map_data.json")
WINDOWER_ZONES_PATH = r"C:\Users\Jason\Games\Windower4\res\zones.lua"
WINDOWER_HOMEPOINTS_PATH = r"C:\Users\Jason\Games\Windower4\addons\Homepoints\map.lua"

# Explicit allowlist of non-navigable / transit-vessel / cutscene / PvP / GM zones in res/zones.lua
EXCLUDED_ZONE_IDS: dict[int, str] = {
    0: "unknown (technical placeholder)",
    1: "Phanauet Channel (barge transit vessel)",
    3: "Manaclipper (barge transit vessel)",
    43: "Diorama Abdhaljs-Ghelsba (Brenner PvP)",
    44: "Abdhaljs Isle-Purgonorgo (Ballista PvP)",
    46: "Open sea route to Al Zahbi (ferry vessel)",
    47: "Open sea route to Mhaura (ferry vessel)",
    58: "Silver Sea route to Nashmau (ferry vessel)",
    59: "Silver Sea route to Al Zahbi (ferry vessel)",
    70: "Chocobo Circuit (minigame non-travel zone)",
    71: "The Colosseum (Pankration minigame)",
    131: "Mordion Gaol (GM jail)",
    183: "Maquette Abdhaljs-LegionA (Ambuscade/Legion lobby sub-ID)",
    220: "Ship bound for Selbina (ferry vessel)",
    221: "Ship bound for Mhaura (ferry vessel)",
    223: "San d'Oria-Jeuno Airship (airship vessel)",
    224: "Bastok-Jeuno Airship (airship vessel)",
    225: "Windurst-Jeuno Airship (airship vessel)",
    226: "Kazham-Jeuno Airship (airship vessel)",
    227: "Ship bound for Selbina (pirate ferry vessel)",
    228: "Ship bound for Mhaura (pirate ferry vessel)",
    229: "Throne Room [V] (cutscene/battlefield sub-ID)",
    278: "Gwora - Corridor (mission cutscene sub-ID)",
    280: "Mog Garden (personal instance)",
    282: "Mount Kamihr (mission cutscene sub-ID)",
    283: "Silver Knife (guild cutscene sub-ID)",
    285: "Feretory (Monstrosity lobby)",
    287: "Maquette Abdhaljs-LegionB (Ambuscade battle sub-ID)",
    290: "Desuetia - Empyreal Paradox (mission cutscene sub-ID)",
    299: "Gwora - Throne Room (mission cutscene sub-ID)",
}

# Post-2015 Home Point additions missing from Windower's older Homepoints/map.lua
SUPPLEMENTAL_HOMEPOINTS: dict[str, list[str]] = {
    "Upper Jeuno": ["Upper Jeuno 4"],
    "Reisenjima": ["Reisenjima 1", "Reisenjima 2", "Reisenjima 3", "Reisenjima 4", "Reisenjima 5", "Reisenjima 6", "Reisenjima 7", "Reisenjima 8", "Reisenjima 9"],
    "Outer Ra'Kaznar": ["Outer Ra'Kaznar 1"],
    "Bostaunieux Oubliette": ["Bostaunieux Oubliette 1"],
    "Ru'Lude Gardens": ["Ru'Lude Gardens 4"],
    "Port San d'Oria": ["Port San d'Oria 4"],
    "Port Windurst": ["Port Windurst 4"],
}

# Zones with Survival Guide books in modern FFXI
SURVIVAL_GUIDE_ZONE_IDS: set[int] = {
    # Cities & Hubs
    230, 231, 232, 234, 235, 236, 238, 239, 240, 241, 243, 244, 245, 246,
    247, 248, 249, 250, 252, 26, 48, 50, 53, 80, 87, 94, 256, 257,
    # Core & Zilart Fields
    100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113,
    114, 115, 116, 117, 118, 119, 120, 121, 122, 123, 124, 125, 126, 127,
    128, 130,
    # Core & Zilart Dungeons
    139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151, 152,
    153, 154, 157, 158, 159, 160, 161, 162, 163, 165, 166, 167, 168, 169,
    170, 172, 173, 174, 176, 177, 178, 184, 190, 191, 192, 193, 194, 195,
    196, 197, 198, 200, 204, 205, 206, 208, 212, 213,
    # CoP
    2, 4, 5, 7, 9, 11, 12, 24, 25, 27, 28,
    # ToAU
    51, 52, 54, 61, 62, 65, 68, 72, 79,
    # WotG [S]
    81, 82, 83, 84, 85, 88, 89, 90, 91, 92, 95, 96, 97, 98, 99, 136, 137,
    138, 155, 164, 171, 175,
}

# Regional constellation definitions (18 geographic/era clusters on 3600 x 2400 canvas)
REGIONS: list[dict] = [
    {"id": "ronfaure", "name": "San d'Oria & Ronfaure", "era": "core_zilart", "cx": 1520.0, "cy": 420.0, "rx": 360.0, "ry": 210.0},
    {"id": "zulkheim_norvallen", "name": "Zulkheim & Norvallen", "era": "core_zilart", "cx": 1220.0, "cy": 830.0, "rx": 350.0, "ry": 210.0},
    {"id": "fauregandi_valdeaunia", "name": "Beaucedine & Xarcabard", "era": "core_zilart", "cx": 2120.0, "cy": 420.0, "rx": 370.0, "ry": 210.0},
    {"id": "jeuno_qufim", "name": "Jeuno & Qufim Hub", "era": "core_zilart", "cx": 1820.0, "cy": 1060.0, "rx": 350.0, "ry": 210.0},
    {"id": "gustaberg_derfland", "name": "Bastok, Gustaberg & Derfland", "era": "core_zilart", "cx": 1220.0, "cy": 1380.0, "rx": 390.0, "ry": 240.0},
    {"id": "sarutabaruta_aragoneu", "name": "Windurst, Saruta & Aragoneu", "era": "core_zilart", "cx": 2360.0, "cy": 1420.0, "rx": 400.0, "ry": 250.0},
    {"id": "kolshushu_litelor", "name": "Buburimu & Sanctuary of Zi'Tah", "era": "core_zilart", "cx": 2450.0, "cy": 960.0, "rx": 320.0, "ry": 190.0},
    {"id": "kuzotz_vollbow", "name": "Altepa, Rabao & Cape Teriggan", "era": "core_zilart", "cx": 1180.0, "cy": 1960.0, "rx": 390.0, "ry": 220.0},
    {"id": "elshimo", "name": "Kazham, Norg & Elshimo", "era": "core_zilart", "cx": 2050.0, "cy": 1980.0, "rx": 380.0, "ry": 220.0},
    {"id": "tulia_sky", "name": "Tu'Lia (Sky)", "era": "core_zilart", "cx": 2660.0, "cy": 520.0, "rx": 280.0, "ry": 170.0},
    {"id": "tavnazia_cop", "name": "Tavnazia, Promyvion & CoP", "era": "cop", "cx": 900.0, "cy": 420.0, "rx": 390.0, "ry": 250.0},
    {"id": "lumoria_sea", "name": "Lumoria (Sea) & Limbus", "era": "cop", "cx": 420.0, "cy": 420.0, "rx": 280.0, "ry": 190.0},
    {"id": "aht_urhgan", "name": "Aht Urhgan & Near East", "era": "toau", "cx": 3140.0, "cy": 1160.0, "rx": 380.0, "ry": 390.0},
    {"id": "nyzul_salvage", "name": "Nyzul, Salvage & Assault", "era": "toau", "cx": 3140.0, "cy": 1920.0, "rx": 360.0, "ry": 230.0},
    {"id": "shadowreign_wotg", "name": "Shadowreign [S] & Walk of Echoes", "era": "wotg", "cx": 3140.0, "cy": 460.0, "rx": 390.0, "ry": 290.0},
    {"id": "adoulin_ulbuka", "name": "Adoulin, Ulbuka & Ra'Kaznar", "era": "adoulin", "cx": 480.0, "cy": 1220.0, "rx": 390.0, "ry": 360.0},
    {"id": "escha_reisenjima", "name": "Escha, Reisenjima & Omen", "era": "escha_abyssea", "cx": 480.0, "cy": 1820.0, "rx": 320.0, "ry": 180.0},
    {"id": "abyssea_dynamis", "name": "Abyssea & Dynamis / [D]", "era": "escha_abyssea", "cx": 480.0, "cy": 2180.0, "rx": 390.0, "ry": 190.0},
]

# Consolidated multi-layer endgame nodes: primary_id -> metadata
CONSOLIDATED_NODES: dict[int, dict] = {
    275: {
        "member_zone_ids": [275, 133, 189],
        "name": "Sortie (Outer Ra'Kaznar [U1-U3])",
        "short_name": "Sortie (Ra'Kaznar U1-U3)",
        "aliases": ["Sortie", "Outer Ra'Kaznar [U1]", "Outer Ra'Kaznar [U2]", "Outer Ra'Kaznar [U3]"],
        "region_id": "adoulin_ulbuka",
        "era": "adoulin",
        "kind": "endgame",
        "wiki_slug": "Category:Sortie",
        "notes": "Enter via Diaphanous Transposer at Outer Ra'Kaznar (G-8) or Kamihr Drifts (F-6).",
    },
    298: {
        "member_zone_ids": [298, 279],
        "name": "Odyssey (Walk of Echoes [P1]/[P2])",
        "short_name": "Odyssey (WoE P1/P2)",
        "aliases": ["Odyssey", "Sheol A", "Sheol B", "Sheol C", "Sheol Gaol", "Walk of Echoes [P1]", "Walk of Echoes [P2]"],
        "region_id": "shadowreign_wotg",
        "era": "wotg",
        "kind": "endgame",
        "wiki_slug": "Category:Odyssey",
        "notes": "Enter via Veridical Conflux in Rabao (G-6).",
    },
    292: {
        "member_zone_ids": [292],
        "name": "Omen (Reisenjima Henge)",
        "short_name": "Omen (Reisenjima Henge)",
        "aliases": ["Omen", "Reisenjima Henge"],
        "region_id": "escha_reisenjima",
        "era": "escha_abyssea",
        "kind": "endgame",
        "wiki_slug": "Category:Omen",
        "notes": "Enter via Ethereal Ingress at Reisenjima (F-5).",
    },
    294: {
        "member_zone_ids": [294, 295, 296, 297],
        "name": "Dynamis Divergence ([D] Cities & Jeuno)",
        "short_name": "Dynamis Divergence [D]",
        "aliases": [
            "Dynamis Divergence",
            "Dynamis [D]",
            "Dynamis - San d'Oria [D]",
            "Dynamis - Bastok [D]",
            "Dynamis - Windurst [D]",
            "Dynamis - Jeuno [D]",
        ],
        "region_id": "abyssea_dynamis",
        "era": "escha_abyssea",
        "kind": "endgame",
        "wiki_slug": "Category:Dynamis_-_Divergence",
        "notes": "Enter via Enigmatic Footprints in Southern San d'Oria, Bastok Mines, Windurst Walls, or Ru'Lude Gardens.",
    },
    185: {
        "member_zone_ids": [185, 186, 187, 188, 134, 135],
        "name": "Dynamis (Cities & Northlands)",
        "short_name": "Dynamis (Classic/North)",
        "aliases": [
            "Dynamis",
            "Dynamis - San d'Oria",
            "Dynamis - Bastok",
            "Dynamis - Windurst",
            "Dynamis - Jeuno",
            "Dynamis - Beaucedine",
            "Dynamis - Xarcabard",
        ],
        "region_id": "abyssea_dynamis",
        "era": "escha_abyssea",
        "kind": "endgame",
        "wiki_slug": "Category:Dynamis",
        "notes": "Enter via Trail Markings in starter cities, Ru'Lude Gardens, Beaucedine Glacier, or Xarcabard.",
    },
    39: {
        "member_zone_ids": [39, 40, 41, 42],
        "name": "Dynamis (Dreamworld: Val/Bub/Quf/Tav)",
        "short_name": "Dynamis (Dreamworld)",
        "aliases": [
            "Dynamis Dreamworld",
            "Dynamis - Valkurm",
            "Dynamis - Buburimu",
            "Dynamis - Qufim",
            "Dynamis - Tavnazia",
        ],
        "region_id": "abyssea_dynamis",
        "era": "escha_abyssea",
        "kind": "endgame",
        "wiki_slug": "Category:Dynamis",
        "notes": "Enter via Hieroglyphics in Valkurm Dunes, Buburimu Peninsula, Qufim Island, or Tavnazian Safehold.",
    },
    73: {
        "member_zone_ids": [73, 74, 75, 76],
        "name": "Salvage (Remnants: Zhayolm/Arrapago/Bhaflau/Silver Sea)",
        "short_name": "Salvage (All Remnants)",
        "aliases": [
            "Salvage",
            "Zhayolm Remnants",
            "Arrapago Remnants",
            "Bhaflau Remnants",
            "Silver Sea Remnants",
        ],
        "region_id": "nyzul_salvage",
        "era": "toau",
        "kind": "endgame",
        "wiki_slug": "Category:Salvage",
        "notes": "Enter via Runic Seal in Alzadaal Undersea Ruins.",
    },
    55: {
        "member_zone_ids": [55, 56, 63, 66, 69],
        "name": "ToAU Assault Sanctums (Leujaoam/Mamool/Lebros/Periqia/Ilrusi)",
        "short_name": "Assault Sanctums (ToAU)",
        "aliases": [
            "Assault",
            "Ilrusi Atoll",
            "Periqia",
            "Lebros Cavern",
            "Mamool Ja Training Grounds",
            "Leujaoam Sanctum",
        ],
        "region_id": "nyzul_salvage",
        "era": "toau",
        "kind": "endgame",
        "wiki_slug": "Category:Assault",
        "notes": "Enter via Runic Portals and Staging Points across Aht Urhgan.",
    },
    16: {
        "member_zone_ids": [16, 17, 18, 19, 20, 21, 22, 23],
        "name": "Promyvion & Spires (Holla, Dem, Mea, Vahzl)",
        "short_name": "Promyvion (Holla/Dem/Mea/Vahzl)",
        "aliases": [
            "Promyvion",
            "Promyvion - Holla",
            "Spire of Holla",
            "Promyvion - Dem",
            "Spire of Dem",
            "Promyvion - Mea",
            "Spire of Mea",
            "Promyvion - Vahzl",
            "Spire of Vahzl",
        ],
        "region_id": "tavnazia_cop",
        "era": "cop",
        "kind": "dungeon",
        "wiki_slug": "Category:Promyvion",
        "notes": "Entered via Hall of Transference in the Crags of Holla, Dem, and Mea, or Pso'Xja.",
    },
    201: {
        "member_zone_ids": [201, 202, 203, 207, 209, 211],
        "name": "Avatar Cloisters (Gales/Storms/Frost/Flames/Tremors/Tides)",
        "short_name": "Avatar Cloisters (6x)",
        "aliases": [
            "Cloister of Gales",
            "Cloister of Storms",
            "Cloister of Frost",
            "Cloister of Flames",
            "Cloister of Tremors",
            "Cloister of Tides",
        ],
        "region_id": "elshimo",
        "era": "core_zilart",
        "kind": "dungeon",
        "wiki_slug": "Trial_by_Fire",
        "notes": "Avatar Protocrystal arenas in Cape Teriggan, Boyahda Tree, Fei'Yin, Ifrit's Cauldron, Quicksand Caves, and Den of Rancor.",
    },
    259: {
        "member_zone_ids": [259, 264, 271],
        "name": "Skirmish / Vagary / Incursion ([U] Layers)",
        "short_name": "Skirmish & Vagary [U]",
        "aliases": [
            "Skirmish",
            "Vagary",
            "Incursion",
            "Delve",
            "Rala Waterways [U]",
            "Yorcia Weald [U]",
            "Cirdas Caverns [U]",
        ],
        "region_id": "adoulin_ulbuka",
        "era": "adoulin",
        "kind": "endgame",
        "wiki_slug": "Category:Vagary",
        "notes": "Adoulin layered content entered via Augmented Erdverg / Odyssean Passage in Eastern Adoulin or Leafallia.",
    },
    86: {
        "member_zone_ids": [86, 93, 129],
        "name": "WotG Campaign Ops Instances (Everbloom/Ruhotz/Ghoyu)",
        "short_name": "WotG Instances (Ops/BCNM)",
        "aliases": ["Everbloom Hollow", "Ruhotz Silvermines", "Ghoyu's Reverie"],
        "region_id": "shadowreign_wotg",
        "era": "wotg",
        "kind": "dungeon",
        "wiki_slug": "Everbloom_Hollow",
        "notes": "Entered from East Ronfaure [S], North Gustaberg [S], and West Sarutabaruta [S].",
    },
}

# Mapping every remaining individual zone ID to (region_id, kind, short_name_override, wiki_slug, extra_aliases, notes)
ZONE_CATALOG: dict[int, tuple[str, str, str | None, str | None, list[str], str]] = {
    # San d'Oria & Ronfaure
    230: ("ronfaure", "hub", None, None, ["Sandy", "S. San d'Oria"], "Starter kingdom hub; Home Points #1-4 & Survival Guide."),
    231: ("ronfaure", "hub", None, None, ["N. San d'Oria"], "Cathedral, Guilds, and Chateau entrance."),
    232: ("ronfaure", "hub", None, None, ["P. San d'Oria"], "Airship dock to Jeuno."),
    233: ("ronfaure", "hub", None, None, ["Chateau"], "Royal palace of San d'Oria."),
    100: ("ronfaure", "field", None, None, ["W. Ronfaure"], "Outside Southern/Port San d'Oria."),
    101: ("ronfaure", "field", None, None, ["E. Ronfaure"], "Outside Southern/Northern San d'Oria; Cavernous Maw to [S]."),
    140: ("ronfaure", "dungeon", None, None, [], "Orcish outpost northwest of West Ronfaure."),
    141: ("ronfaure", "dungeon", None, None, [], "Leads to Horlais Peak BCNM."),
    142: ("ronfaure", "dungeon", None, None, [], "Orcish stronghold with Home Point #1."),
    139: ("ronfaure", "dungeon", None, None, [], "San d'Oria BCNM arena."),
    167: ("ronfaure", "dungeon", "Bostaunieux Oubliette", None, ["Oubliette"], "Dungeon beneath Chateau d'Oraguille; one-way drop to West Ronfaure."),
    190: ("ronfaure", "dungeon", "King Ranperre's Tomb", None, ["KRT"], "Connects East Ronfaure to South Ronfaure cliffside."),

    # Zulkheim & Norvallen
    102: ("zulkheim_norvallen", "field", None, None, ["La Theine", "Crag of Holla"], "Crag of Holla (Teleport-Holla), Cavernous Maw to Abyssea - La Theine, Escha - Zi'Tah portal."),
    103: ("zulkheim_norvallen", "field", None, None, ["Dunes"], "Classic leveling beach; connects to Selbina and Gustav Tunnel."),
    248: ("zulkheim_norvallen", "hub", None, None, [], "Ferry port to Mhaura; Home Point & Nomad Moogle."),
    193: ("zulkheim_norvallen", "dungeon", None, None, ["Ordelles"], "Connects La Theine Plateau pathways."),
    196: ("zulkheim_norvallen", "dungeon", None, None, [], "Haunted mine in Konschtat Highlands."),
    104: ("zulkheim_norvallen", "field", None, None, ["Jugner"], "Forested road to Davoi and Batallia Downs; Cavernous Maw to [S]."),
    105: ("zulkheim_norvallen", "field", None, None, ["Batallia"], "Outside Jeuno; Cavernous Maw to Batallia Downs [S]."),
    149: ("zulkheim_norvallen", "dungeon", None, None, [], "Orcish stronghold in Jugner Forest."),
    150: ("zulkheim_norvallen", "dungeon", None, None, [], "Inner sanctum of Davoi."),
    195: ("zulkheim_norvallen", "dungeon", "Eldieme Necropolis", None, ["Eldieme"], "Ancient tomb entered from Batallia Downs."),

    # Fauregandi & Valdeaunia
    166: ("fauregandi_valdeaunia", "dungeon", None, None, [], "Mountain pass linking East Ronfaure to Beaucedine Glacier."),
    111: ("fauregandi_valdeaunia", "field", None, None, ["Glacier"], "Frozen cliffs linking Ranguemont, Batallia, Fei'Yin, Pso'Xja, and Xarcabard."),
    204: ("fauregandi_valdeaunia", "dungeon", None, None, [], "Ruins in NE Beaucedine Glacier; Home Points #1-2 & Qu'Bia Arena."),
    206: ("fauregandi_valdeaunia", "dungeon", None, None, [], "BCNM arena inside Fei'Yin."),
    112: ("fauregandi_valdeaunia", "field", None, None, ["Teleport-Vahzl"], "Crag of Vahzl (Teleport-Vahzl); leads to Castle Zvahl and Uleguerand Range."),
    161: ("fauregandi_valdeaunia", "dungeon", "Castle Zvahl Baileys", None, ["Zvahl Baileys"], "Outer demon fortress in Xarcabard."),
    162: ("fauregandi_valdeaunia", "dungeon", "Castle Zvahl Keep", None, ["Zvahl Keep"], "Inner demon fortress; Home Point #1 before Throne Room."),
    165: ("fauregandi_valdeaunia", "dungeon", None, None, [], "Shadow Lord battlefield."),

    # Jeuno & Qufim Hub
    243: ("jeuno_qufim", "hub", None, None, ["Ru'Lude"], "Grand Ducal Palace, Airship pass, Voidwatch & Dynamis [D] Jeuno."),
    244: ("jeuno_qufim", "hub", None, None, [], "Chocobo stables, Monberaux clinic, Home Points #1-4."),
    245: ("jeuno_qufim", "hub", None, None, [], "Auction House, Tenshodo, Gobbiebag; exits to Rolanberry/Batallia/Sauromugue."),
    246: ("jeuno_qufim", "hub", None, None, ["Jeuno"], "Primary central hub: Airships to all 4 nations, Abyssea Joachim, Voidwatch."),
    126: ("jeuno_qufim", "field", None, None, ["Qufim"], "Reached via Port Jeuno tunnel; Escha - Zi'Tah & Escha - Ru'Aun portals."),
    127: ("jeuno_qufim", "field", "Behemoth's Dominion", None, [], "King Behemoth spawn area off Qufim Island."),
    184: ("jeuno_qufim", "dungeon", "Lower Delkfutt's Tower", None, ["Lower Delkfutt"], "Tower on Qufim Island."),
    157: ("jeuno_qufim", "dungeon", "Middle Delkfutt's Tower", None, ["Middle Delkfutt"], "Middle floors of Delkfutt's Tower."),
    158: ("jeuno_qufim", "dungeon", "Upper Delkfutt's Tower", None, ["Upper Delkfutt"], "Top floors of Delkfutt's Tower; Home Point #1 before Stellar Fulcrum."),
    179: ("jeuno_qufim", "dungeon", None, None, [], "Kam'lanaut Zilart battlefield."),

    # Gustaberg & Derfland
    234: ("gustaberg_derfland", "hub", None, None, [], "Alchemy guild,Zeruhn Mines entrance, Dynamis [D] Bastok."),
    235: ("gustaberg_derfland", "hub", None, None, [], "Goldsmithing guild, Home Points #1-4."),
    236: ("gustaberg_derfland", "hub", None, None, [], "Airship to Jeuno, Tenshodo."),
    237: ("gustaberg_derfland", "hub", None, None, [], "President's Office, Cid's Workshop, Home Points #1-2."),
    172: ("gustaberg_derfland", "dungeon", None, None, [], "Starter mine inside Bastok Mines; connects to Korroloka Tunnel."),
    106: ("gustaberg_derfland", "field", None, None, ["N. Gustaberg"], "Outside Bastok Markets/Mines; Cavernous Maw to [S]."),
    107: ("gustaberg_derfland", "field", None, None, ["S. Gustaberg"], "Outside Bastok Markets/Port."),
    191: ("gustaberg_derfland", "dungeon", None, None, ["Wadi"], "Geyser valley west of South Gustaberg."),
    143: ("gustaberg_derfland", "dungeon", None, None, ["Palborough"], "Quadav mine in North Gustaberg; Home Point #1."),
    144: ("gustaberg_derfland", "dungeon", None, None, [], "Bastok BCNM arena."),
    108: ("gustaberg_derfland", "field", "Konschtat Highlands", None, ["Konschtat", "Crag of Dem"], "Crag of Dem (Teleport-Dem), Abyssea - Konschtat Maw, Escha - Zi'Tah portal."),
    109: ("gustaberg_derfland", "field", "Pashhow Marshlands", None, ["Pashhow"], "Swampland linking Konschtat, Rolanberry, and Beadeaux; Cavernous Maw to [S]."),
    110: ("gustaberg_derfland", "field", None, None, ["Rolanberry"], "Outside Lower Jeuno; Cavernous Maw to Rolanberry Fields [S]."),
    147: ("gustaberg_derfland", "dungeon", None, None, [], "Quadav stronghold in Pashhow Marshlands."),
    148: ("gustaberg_derfland", "dungeon", None, None, [], "Inner sanctum of Beadeaux."),
    197: ("gustaberg_derfland", "dungeon", None, None, ["Nest"], "Dungeon in Rolanberry Fields."),

    # Sarutabaruta & Aragoneu
    238: ("sarutabaruta_aragoneu", "hub", None, None, [], "Culinary guild, Rhinostimulator, Home Points #1-4."),
    239: ("sarutabaruta_aragoneu", "hub", None, None, [], "Heavens Tower access, Toraimarai Canal entrance, Dynamis [D] Windurst."),
    240: ("sarutabaruta_aragoneu", "hub", None, None, [], "Airship dock to Jeuno, Fishing guild."),
    241: ("sarutabaruta_aragoneu", "hub", None, None, [], "Weaver/Bonecraft guilds, East Sarutabaruta exit, Home Points #1-5."),
    242: ("sarutabaruta_aragoneu", "hub", None, None, [], "Star Sibyl's palace in Windurst Walls."),
    115: ("sarutabaruta_aragoneu", "field", None, None, ["W. Sarutabaruta"], "Outside Windurst Waters/Port; Cavernous Maw to [S]."),
    116: ("sarutabaruta_aragoneu", "field", None, None, ["E. Sarutabaruta"], "Outside Windurst Woods/Port; Horutoto Ruins entrances."),
    145: ("sarutabaruta_aragoneu", "dungeon", None, None, [], "Yagudo settlement in West Sarutabaruta; Home Point #1."),
    146: ("sarutabaruta_aragoneu", "dungeon", None, None, [], "Windurst BCNM arena."),
    192: ("sarutabaruta_aragoneu", "dungeon", "Inner Horutoto Ruins", None, ["Inner Horutoto"], "Leads to Three Mage Gate and Toraimarai Canal."),
    194: ("sarutabaruta_aragoneu", "dungeon", "Outer Horutoto Ruins", None, ["Outer Horutoto"], "Ancient magic towers in Sarutabaruta."),
    169: ("sarutabaruta_aragoneu", "dungeon", None, None, ["Toraimarai"], "Underground canal linking Windurst Walls (Portal Charm), Inner Horutoto (Three Mage Gate), and Full Moon Fountain."),
    170: ("sarutabaruta_aragoneu", "dungeon", None, None, [], "Fenrir / Windurst mission battlefield."),
    119: ("sarutabaruta_aragoneu", "field", "Meriphataud Mountains", None, ["Meriphataud"], "Connects Tahrongi, Sauromugue, and Castle Oztroja; Cavernous Maw to [S]."),
    120: ("sarutabaruta_aragoneu", "field", "Sauromugue Champaign", None, ["Sauromugue"], "Outside Lower Jeuno; Cavernous Maw to [S]."),
    151: ("sarutabaruta_aragoneu", "dungeon", None, None, ["Oztroja"], "Yagudo fortress in Meriphataud Mountains."),
    152: ("sarutabaruta_aragoneu", "dungeon", None, None, [], "Inner sanctum of Castle Oztroja."),
    200: ("sarutabaruta_aragoneu", "dungeon", None, None, ["Garlaige"], "Fortress in Sauromugue Champaign with Banishing Gates."),

    # Kolshushu & Li'Telor
    117: ("kolshushu_litelor", "field", None, None, ["Tahrongi", "Crag of Mea"], "Crag of Mea (Teleport-Mea), Abyssea - Tahrongi Maw, Escha - Zi'Tah portal."),
    118: ("kolshushu_litelor", "field", None, None, ["Buburimu"], "Peninsula leading to Mhaura and Bibiki Bay."),
    249: ("kolshushu_litelor", "hub", None, None, [], "Ferry port to Selbina and Al Zahbi (Aht Urhgan); Home Point & Nomad Moogle."),
    198: ("kolshushu_litelor", "dungeon", None, None, ["Shakhrami"], "Fossil caves between Tahrongi Canyon and Buburimu Peninsula."),
    213: ("kolshushu_litelor", "dungeon", "Labyrinth of Onzozo", None, ["Onzozo"], "High-level cave in Buburimu Peninsula."),
    121: ("kolshushu_litelor", "field", "The Sanctuary of Zi'Tah", None, ["Zi'Tah"], "Ancient forest reached via Meriphataud Mountains."),
    153: ("kolshushu_litelor", "dungeon", None, None, ["Boyahda"], "Giant tree dungeon; Home Point #1 near Cloister of Storms & Dragon's Aery."),
    154: ("kolshushu_litelor", "dungeon", None, None, ["Aery"], "Fafnir / Nidhogg spawn arena."),
    122: ("kolshushu_litelor", "field", None, None, [], "Moonlit ruins leading to Hall of the Gods and Tu'Lia (Sky)."),
    251: ("kolshushu_litelor", "dungeon", None, None, [], "Gateway between Ro'Maeve and Tu'Lia (Sky)."),

    # Kuzotz & Vollbow
    173: ("kuzotz_vollbow", "dungeon", None, None, ["Korroloka"], "Undersea tunnel connecting Zeruhn Mines (Bastok) to Eastern Altepa Desert."),
    114: ("kuzotz_vollbow", "field", "Eastern Altepa Desert", None, ["E. Altepa", "Teleport-Altep"], "Teleport-Altep crag; connects Korroloka, Western Altepa, and Quicksand Caves."),
    125: ("kuzotz_vollbow", "field", "Western Altepa Desert", None, ["W. Altepa"], "Connects to Rabao, Kuftal Tunnel, and Quicksand Caves."),
    247: ("kuzotz_vollbow", "hub", None, None, ["Odyssey Hub"], "Desert oasis town; Home Points #1-2 and Veridical Conflux to Odyssey."),
    208: ("kuzotz_vollbow", "dungeon", None, None, ["Quicksand"], "Antican caves with weight doors; Home Points #1-2."),
    168: ("kuzotz_vollbow", "dungeon", None, None, [], "Zilart mission / BCNM arena via Quicksand Caves."),
    174: ("kuzotz_vollbow", "dungeon", None, None, ["Kuftal"], "Connects Western Altepa Desert to Cape Teriggan."),
    113: ("kuzotz_vollbow", "field", None, None, ["Teriggan"], "Windy coastline; Home Point #1 near Cloister of Gales and Valley of Sorrows."),
    128: ("kuzotz_vollbow", "field", None, None, [], "Adamantoise spawn valley off Gustav Tunnel."),
    212: ("kuzotz_vollbow", "dungeon", None, None, ["Gustav"], "Connects Valkurm Dunes (H-7) to Cape Teriggan and Valley of Sorrows."),

    # Elshimo
    250: ("elshimo", "hub", None, None, [], "Airship from Port Jeuno (requires Kazham Airship Pass); Home Point #1."),
    252: ("elshimo", "hub", None, None, [], "Pirate cove reached via Sea Serpent Grotto; Samurai/Ninja quests, Home Points #1-2."),
    123: ("elshimo", "field", None, None, ["Yuhtunga"], "Lower jungle outside Kazham; leads to Sea Serpent Grotto and Ifrit's Cauldron."),
    124: ("elshimo", "field", None, None, ["Yhoator", "Teleport-Yhoat"], "Upper jungle (Teleport-Yhoat); leads to Temple of Uggalepih."),
    176: ("elshimo", "dungeon", None, None, ["SSG"], "Sahagin caves connecting Yuhtunga Jungle to Norg."),
    159: ("elshimo", "dungeon", "Temple of Uggalepih", None, ["Uggalepih"], "Tonberry temple in Yhoator Jungle."),
    160: ("elshimo", "dungeon", None, None, ["Rancor"], "Caverns beneath Uggalepih; Home Points #1-2."),
    163: ("elshimo", "dungeon", "Sacrificial Chamber", None, [], "Zilart mission battlefield via Den of Rancor."),
    205: ("elshimo", "dungeon", None, None, ["Cauldron"], "Volcanic labyrinth in Yuhtunga/Yhoator; Home Point #1 before Cloister of Flames."),

    # Tu'Lia (Sky)
    130: ("tulia_sky", "field", "Ru'Aun Gardens (Sky)", None, ["Sky", "Tu'Lia", "Ru'Aun Gardens"], "Floating Zilart islands; Home Points #1-5 covering all four God islands."),
    177: ("tulia_sky", "dungeon", "Ve'Lugannon Palace", None, ["Ve'Lugannon"], "Palace walkways beneath Ru'Aun Gardens."),
    178: ("tulia_sky", "dungeon", "Shrine of Ru'Avitau", None, ["Ru'Avitau"], "Central shrine of Sky; Home Point #1 near Kirin & Celestial Nexus."),
    180: ("tulia_sky", "dungeon", "La'Loff Amphitheater", None, ["La'Loff"], "Ark Angel battlefield entrances."),
    181: ("tulia_sky", "dungeon", "The Celestial Nexus", None, ["Celestial Nexus"], "Eald'narche Zilart final battlefield."),

    # Tavnazia, Promyvion & CoP
    14: ("tavnazia_cop", "dungeon", "Hall of Transference", None, [], "Dimensional chambers inside the Crags of Holla, Dem, and Mea."),
    26: ("tavnazia_cop", "hub", "Tavnazian Safehold", None, ["Tavnazia"], "CoP hub city; Home Points #1-3 & Survival Guide."),
    24: ("tavnazia_cop", "field", None, None, ["Lufaise"], "Coastal meadows outside Tavnazian Safehold."),
    25: ("tavnazia_cop", "field", None, None, ["Misareaux"], "Cliffs outside Tavnazian Safehold; Home Point #1 & Escha - Ru'Aun portal."),
    27: ("tavnazia_cop", "dungeon", "Phomiuna Aqueducts", None, ["Aqueducts"], "Aqueducts beneath Tavnazia."),
    28: ("tavnazia_cop", "dungeon", None, None, [], "Fomor cathedral off Misareaux Coast."),
    29: ("tavnazia_cop", "dungeon", "Riverne - Site #B01", None, ["Riverne B01"], "Floating islands via Misareaux Coast (G-6); Home Point #1."),
    30: ("tavnazia_cop", "dungeon", "Riverne - Site #A01", None, ["Riverne A01"], "Floating islands via Misareaux Coast; Home Point #1."),
    31: ("tavnazia_cop", "dungeon", None, None, [], "Bahamut / CoP battlefield at the end of Riverne."),
    32: ("tavnazia_cop", "dungeon", None, None, [], "Airship dock inside Tavnazian Safehold leading to Al'Taieu (Sea)."),
    2: ("tavnazia_cop", "field", "Carpenters' Landing", None, [], "Reached via Jugner Forest; barge via Phanauet Channel."),
    4: ("tavnazia_cop", "field", None, None, [], "Reached via Buburimu Peninsula; Manaclipper to Purgonorgo Isle."),
    5: ("tavnazia_cop", "field", None, None, ["Uleguerand"], "Frozen mountains off Xarcabard; Home Points #1-5."),
    6: ("tavnazia_cop", "dungeon", None, None, [], "BCNM peak at top of Uleguerand Range."),
    7: ("tavnazia_cop", "field", None, None, ["Attohwa"], "Canyon reached via Maze of Shakhrami; Home Point #1."),
    8: ("tavnazia_cop", "dungeon", None, None, [], "Battlefield at end of Attohwa Chasm."),
    9: ("tavnazia_cop", "dungeon", None, None, [], "Ancient towers beneath Beaucedine Glacier; Home Point #1 before Spire of Vahzl."),
    10: ("tavnazia_cop", "dungeon", None, None, [], "Diabolos battlefield in Pso'Xja."),
    11: ("tavnazia_cop", "dungeon", "Oldton Movalpolos", None, ["Oldton"], "Goblin mines reached via North Gustaberg."),
    12: ("tavnazia_cop", "dungeon", "Newton Movalpolos", None, ["Newton"], "Deep Goblin mines; Home Point #1."),
    13: ("tavnazia_cop", "dungeon", None, None, [], "Battlefield at end of Newton Movalpolos."),

    # Lumoria (Sea) & Limbus
    33: ("lumoria_sea", "field", "Al'Taieu (Sea)", None, ["Sea", "Lumoria", "Al'Taieu"], "Submerged Zilart capital; Home Points #1-3 and Limbus Dimensional Portals."),
    34: ("lumoria_sea", "dungeon", "Grand Palace of Hu'Xzoi", None, ["Hu'Xzoi"], "Palace in Al'Taieu; Home Point #1."),
    35: ("lumoria_sea", "dungeon", "The Garden of Ru'Hmet", None, ["Ru'Hmet"], "Upper tower of Hu'Xzoi; Home Point #1."),
    36: ("lumoria_sea", "dungeon", "Empyreal Paradox", None, [], "Promathia / Dawn battlefield."),
    37: ("lumoria_sea", "endgame", "Temenos (Limbus)", "Category:Limbus", ["Temenos", "Limbus"], "Enter via Dimensional Portal in Al'Taieu (H-4) with Cosmo-Cleanse."),
    38: ("lumoria_sea", "endgame", "Apollyon (Limbus)", "Category:Limbus", ["Apollyon", "Limbus"], "Enter via Swirling Vortex in Al'Taieu (E-6) or (K-6) with Cosmo-Cleanse."),

    # Aht Urhgan & Near East
    50: ("aht_urhgan", "hub", "Aht Urhgan Whitegate", None, ["Whitegate"], "Imperial capital hub; Home Points #1-4, Runic Portal Chamber, Ferry to Mhaura & Nashmau."),
    48: ("aht_urhgan", "hub", None, None, [], "Besieged district, Auction House, Home Point #1."),
    51: ("aht_urhgan", "field", None, None, ["Wajaom"], "Outside Al Zahbi; connects to Mamook, Halvung, and Aydeewa."),
    52: ("aht_urhgan", "field", None, None, ["Bhaflau"], "Outside Aht Urhgan Whitegate; Home Point #1 at Sea Dock to Nashmau."),
    65: ("aht_urhgan", "dungeon", None, None, [], "Mamool Ja stronghold off Wajaom Woodlands."),
    67: ("aht_urhgan", "dungeon", None, None, [], "Battlefield inside Mamook."),
    61: ("aht_urhgan", "field", None, None, ["Zhayolm"], "Volcanic island; Home Point #1 at Halvung gate."),
    62: ("aht_urhgan", "dungeon", None, None, [], "Troll stronghold connecting Wajaom Woodlands and Mount Zhayolm."),
    64: ("aht_urhgan", "dungeon", "Navukgo Execution Chamber", None, ["Navukgo"], "Battlefield via Halvung."),
    68: ("aht_urhgan", "dungeon", "Aydeewa Subterrane", None, ["Aydeewa"], "Subterranean caverns beneath Wajaom and Bhaflau."),
    53: ("aht_urhgan", "hub", None, None, [], "Qiqirn port on Azouph Isle; Home Point #1."),
    79: ("aht_urhgan", "field", None, None, ["Caedarva"], "Mire outside Nashmau and via Runic Portals; Home Point #1."),
    54: ("aht_urhgan", "dungeon", None, None, ["Arrapago"], "Shipwreck reef north of Caedarva Mire (Lamian Fang Key)."),
    57: ("aht_urhgan", "dungeon", None, None, [], "Rock cleave battlefield off Caedarva Mire / Arrapago Reef."),
    60: ("aht_urhgan", "dungeon", None, None, ["Ashu Talif"], "Corsair ship battlefield anchored off Arrapago Reef."),

    # Nyzul, Salvage & Einherjar
    72: ("nyzul_salvage", "dungeon", "Alzadaal Undersea Ruins", None, ["Alzadaal", "Undersea Ruins"], "Hub for Nyzul Isle and Salvage Remnants (costs 1 Imperial Mythril/Silver Piece)."),
    77: ("nyzul_salvage", "endgame", "Nyzul Isle (Charted/Uncharted)", "Category:Nyzul_Isle", ["Nyzul", "Nyzul Isle"], "Enter via Runic Seal in Alzadaal Undersea Ruins (G-8)."),
    78: ("nyzul_salvage", "endgame", "Einherjar (Hazhalm Grounds)", "Category:Einherjar", ["Einherjar", "Hazhalm Testing Grounds"], "Enter via Glowing Lamp in Caedarva Mire (F-8) near Nashmau."),

    # Shadowreign [S] & Walk of Echoes
    80: ("shadowreign_wotg", "hub", "Southern San d'Oria [S]", "Southern_San_d'Oria_(S)", ["S. San d'Oria [S]"], "Past San d'Oria hub; Home Point #1 & Survival Guide."),
    81: ("shadowreign_wotg", "field", "East Ronfaure [S]", "East_Ronfaure_(S)", [], "Past Ronfaure; Cavernous Maw to present East Ronfaure."),
    82: ("shadowreign_wotg", "field", "Jugner Forest [S]", "Jugner_Forest_(S)", [], "Past Jugner; Cavernous Maw to present Jugner Forest."),
    83: ("shadowreign_wotg", "field", "Vunkerl Inlet [S]", "Vunkerl_Inlet_(S)", ["Vunkerl [S]"], "Reached via Jugner Forest [S] or Pashhow Marshlands [S]."),
    84: ("shadowreign_wotg", "field", "Batallia Downs [S]", "Batallia_Downs_(S)", [], "Past Batallia; Cavernous Maw to present Batallia Downs."),
    85: ("shadowreign_wotg", "dungeon", "La Vaule [S]", "La_Vaule_(S)", [], "Orcish stronghold in Jugner Forest [S]."),
    87: ("shadowreign_wotg", "hub", "Bastok Markets [S]", "Bastok_Markets_(S)", [], "Past Bastok hub; Home Point #1 & Survival Guide."),
    88: ("shadowreign_wotg", "field", "North Gustaberg [S]", "North_Gustaberg_(S)", [], "Past Gustaberg; Cavernous Maw to present North Gustaberg."),
    89: ("shadowreign_wotg", "field", "Grauberg [S]", "Grauberg_(S)", [], "Reached via North Gustaberg [S] or Pashhow Marshlands [S]."),
    90: ("shadowreign_wotg", "field", "Pashhow Marshlands [S]", "Pashhow_Marshlands_(S)", [], "Past Pashhow; Cavernous Maw to present Pashhow."),
    91: ("shadowreign_wotg", "field", "Rolanberry Fields [S]", "Rolanberry_Fields_(S)", [], "Past Rolanberry; Cavernous Maw to present Rolanberry."),
    92: ("shadowreign_wotg", "dungeon", "Beadeaux [S]", "Beadeaux_(S)", [], "Quadav stronghold in Pashhow Marshlands [S]."),
    94: ("shadowreign_wotg", "hub", "Windurst Waters [S]", "Windurst_Waters_(S)", [], "Past Windurst hub; Home Point #1 & Survival Guide."),
    95: ("shadowreign_wotg", "field", "West Sarutabaruta [S]", "West_Sarutabaruta_(S)", [], "Past Sarutabaruta; Cavernous Maw to present West Sarutabaruta."),
    96: ("shadowreign_wotg", "field", "Fort Karugo-Narugo [S]", "Fort_Karugo-Narugo_(S)", ["Karugo-Narugo [S]"], "Reached via West Sarutabaruta [S] or Meriphataud Mountains [S]."),
    97: ("shadowreign_wotg", "field", "Meriphataud Mountains [S]", "Meriphataud_Mountains_(S)", [], "Past Meriphataud; Cavernous Maw to present Meriphataud."),
    98: ("shadowreign_wotg", "field", "Sauromugue Champaign [S]", "Sauromugue_Champaign_(S)", [], "Past Sauromugue; Cavernous Maw to present Sauromugue."),
    99: ("shadowreign_wotg", "dungeon", "Castle Oztroja [S]", "Castle_Oztroja_(S)", [], "Yagudo stronghold in Meriphataud Mountains [S]."),
    136: ("shadowreign_wotg", "field", "Beaucedine Glacier [S]", "Beaucedine_Glacier_(S)", [], "Reached via Batallia Downs [S]."),
    137: ("shadowreign_wotg", "field", "Xarcabard [S]", "Xarcabard_(S)", [], "Past Xarcabard; Home Point #1 & Veridical Conflux to Walk of Echoes."),
    138: ("shadowreign_wotg", "dungeon", "Castle Zvahl Baileys [S]", "Castle_Zvahl_Baileys_(S)", [], "Outer past Zvahl."),
    155: ("shadowreign_wotg", "dungeon", "Castle Zvahl Keep [S]", "Castle_Zvahl_Keep_(S)", [], "Inner past Zvahl; Home Point #1."),
    156: ("shadowreign_wotg", "dungeon", "Throne Room [S]", "Throne_Room_(S)", [], "WotG final battlefield."),
    164: ("shadowreign_wotg", "dungeon", "Garlaige Citadel [S]", "Garlaige_Citadel_(S)", [], "Past Garlaige via Sauromugue Champaign [S]."),
    171: ("shadowreign_wotg", "dungeon", "Crawlers' Nest [S]", "Crawlers'_Nest_(S)", [], "Past Nest via Rolanberry Fields [S]."),
    175: ("shadowreign_wotg", "dungeon", "Eldieme Necropolis [S]", "The_Eldieme_Necropolis_(S)", [], "Past Eldieme via Batallia Downs [S]."),
    182: ("shadowreign_wotg", "endgame", "Walk of Echoes (Surges)", "Walk_of_Echoes", ["WoE"], "Enter via Veridical Conflux in Xarcabard [S] (H-9) or Pashhow [S] / Grauberg [S]."),
    222: ("shadowreign_wotg", "endgame", "Provenance (Voidwatch)", "Provenance", ["Provenance Watcher"], "Final Voidwatch arena entered via Shimmeringdisplacement in Qufim / Walk of Echoes."),

    # Adoulin, Ulbuka & Ra'Kaznar
    256: ("adoulin_ulbuka", "hub", None, None, ["W. Adoulin"], "Adoulin port city; Pioneer's Coalition, Home Points #1-2, Waypoints."),
    257: ("adoulin_ulbuka", "hub", None, None, ["E. Adoulin"], "Castle Adoulin, Peacekeepers, Oboro JSE weapons, Home Points #1-2."),
    284: ("adoulin_ulbuka", "hub", "Celennia Memorial Library", None, ["Library"], "Inside Eastern Adoulin; Aeonic/Ergon lore."),
    258: ("adoulin_ulbuka", "dungeon", None, None, ["Rala"], "Waterways beneath Western & Eastern Adoulin."),
    260: ("adoulin_ulbuka", "field", "Yahse Hunting Grounds", None, ["Yahse"], "North exit from Western Adoulin."),
    261: ("adoulin_ulbuka", "field", "Ceizak Battlegrounds", None, ["Ceizak"], "South exit from Western Adoulin; Home Point #1 at Bivouac/Colkhab."),
    268: ("adoulin_ulbuka", "dungeon", None, None, [], "Cavern linking Ceizak, Yahse, Foret de Hennetiel, and Moh Gates."),
    269: ("adoulin_ulbuka", "dungeon", None, None, [], "Geothermal cavern linking Yahse, Ceizak, and Morimar Basalt Fields."),
    262: ("adoulin_ulbuka", "field", "Foret de Hennetiel", None, ["Hennetiel"], "Water forest via Sih Gates; Home Point #1 near Tchakka."),
    265: ("adoulin_ulbuka", "field", "Morimar Basalt Fields", None, ["Morimar"], "Volcanic cliffs via Moh Gates; Home Point #1 near Achuka."),
    270: ("adoulin_ulbuka", "dungeon", None, None, ["Cirdas"], "Central Ulbuka caverns linking Sih, Moh, Dho, and Woh Gates."),
    263: ("adoulin_ulbuka", "field", None, None, ["Yorcia"], "Misty forest via Cirdas Caverns; Home Point #1 near Yumcax."),
    272: ("adoulin_ulbuka", "dungeon", None, None, [], "Caverns linking Foret de Hennetiel, Yorcia, and Marjami Ravine."),
    266: ("adoulin_ulbuka", "field", None, None, ["Marjami"], "Canyon via Dho Gates; Home Point #1 near Hurkan."),
    273: ("adoulin_ulbuka", "dungeon", None, None, [], "Ice/rock caverns linking Morimar, Marjami, Cirdas, and Kamihr Drifts."),
    267: ("adoulin_ulbuka", "field", None, None, ["Kamihr"], "Snowy peaks via Woh Gates; Home Point #1 near Kumhau & Outer Ra'Kaznar entrance."),
    281: ("adoulin_ulbuka", "hub", None, None, [], "Yggdrasil sanctuary off Ceizak Battlegrounds; Home Point #1."),
    274: ("adoulin_ulbuka", "dungeon", None, None, ["Ra'Kaznar"], "Entered from Kamihr Drifts (F-6); Home Point #1 at Sortie Transposer (G-8)."),
    276: ("adoulin_ulbuka", "dungeon", "Ra'Kaznar Inner Court", None, ["Inner Ra'Kaznar"], "Deep Ra'Kaznar; Home Point #1."),
    277: ("adoulin_ulbuka", "endgame", "Ra'Kaznar Turris", None, ["Hades"], "SoA final battlefield / Sinister Reign arena."),

    # Escha, Reisenjima & Omen
    288: ("escha_reisenjima", "endgame", "Escha - Zi'Tah (Geas Fete)", "Escha_-_Zi'Tah", ["Escha Zi'Tah"], "Enter via Undulating Confluence in Qufim (F-8), La Theine (J-7), Konschtat (I-6), or Tahrongi (H-11)."),
    289: ("escha_reisenjima", "endgame", "Escha - Ru'Aun (Geas Fete)", "Escha_-_Ru'Aun", ["Escha Ru'Aun"], "Enter via Undulating Confluence in Misareaux Coast (G-5) or Qufim (G-6)."),
    291: ("escha_reisenjima", "endgame", "Reisenjima (Geas Fete/Aeonic)", "Reisenjima", [], "Enter via Dimensional Portal in La Theine, Konschtat, or Tahrongi; Home Points #1-9."),
    293: ("escha_reisenjima", "endgame", "Reisenjima Sanctorium", "Reisenjima_Sanctorium", ["Cloud of Darkness"], "Rhapsodies of Vana'diel final battlefield."),

    # Abyssea & Dynamis
    15: ("abyssea_dynamis", "endgame", "Abyssea - Konschtat", "Abyssea_-_Konschtat", [], "Enter via Cavernous Maw in Konschtat Highlands (I-12)."),
    45: ("abyssea_dynamis", "endgame", "Abyssea - Tahrongi", "Abyssea_-_Tahrongi", [], "Enter via Cavernous Maw in Tahrongi Canyon (H-12)."),
    132: ("abyssea_dynamis", "endgame", "Abyssea - La Theine", "Abyssea_-_La_Theine", [], "Enter via Cavernous Maw in La Theine Plateau (E-4)."),
    215: ("abyssea_dynamis", "endgame", "Abyssea - Attohwa", "Abyssea_-_Attohwa", [], "Enter via Cavernous Maw in Buburimu Peninsula (F-7)."),
    216: ("abyssea_dynamis", "endgame", "Abyssea - Misareaux", "Abyssea_-_Misareaux", [], "Enter via Cavernous Maw in Valkurm Dunes (I-9)."),
    217: ("abyssea_dynamis", "endgame", "Abyssea - Vunkerl", "Abyssea_-_Vunkerl", [], "Enter via Cavernous Maw in Jugner Forest (J-8)."),
    218: ("abyssea_dynamis", "endgame", "Abyssea - Altepa", "Abyssea_-_Altepa", [], "Enter via Cavernous Maw in South Gustaberg (J-10)."),
    253: ("abyssea_dynamis", "endgame", "Abyssea - Uleguerand", "Abyssea_-_Uleguerand", [], "Enter via Cavernous Maw in Xarcabard (H-8)."),
    254: ("abyssea_dynamis", "endgame", "Abyssea - Grauberg", "Abyssea_-_Grauberg", [], "Enter via Cavernous Maw in North Gustaberg (G-7)."),
    255: ("abyssea_dynamis", "endgame", "Abyssea - Empyreal Paradox", "Abyssea_-_Empyreal_Paradox", ["Shinryu"], "Enter via Transcendental Radiance in Qufim Island (F-7)."),
}

# Ground-truth FFXI zone connection graph:
# (from_id, to_id, bidirectional, kind, exit_pos, requirement)
RAW_EDGES: list[tuple[int, int, bool, str, str, str]] = [
    # San d'Oria & Ronfaure
    (230, 231, True, "walk", "(I-7)", ""),
    (230, 232, True, "walk", "(J-10)", ""),
    (231, 232, True, "walk", "(F-10)", ""),
    (231, 233, True, "walk", "(I-6)", ""),
    (230, 100, True, "walk", "(I-11)", ""),
    (230, 101, True, "walk", "(K-9)", ""),
    (231, 101, True, "walk", "(M-5)", ""),
    (232, 100, True, "walk", "(F-8)", ""),
    (100, 101, True, "walk", "(I-11)", ""),
    (100, 140, True, "walk", "(F-6)", ""),
    (140, 141, True, "walk", "(G-6)", ""),
    (140, 142, True, "walk", "(I-8)", ""),
    (141, 142, True, "walk", "(H-10)", ""),
    (142, 139, True, "walk", "(J-6)", ""),
    (233, 167, True, "walk", "(I-7)", ""),
    (167, 100, False, "walk", "One-way Drop (D-10)", ""),
    (101, 190, True, "walk", "(H-10)", ""),
    (101, 166, True, "walk", "(J-4)", ""),
    (166, 111, True, "walk", "(I-5)", ""),

    # Zulkheim & Norvallen
    (100, 102, True, "walk", "(I-13)", ""),
    (102, 193, True, "walk", "(F-7)", ""),
    (102, 103, True, "walk", "(E-10)", ""),
    (102, 104, True, "walk", "(L-7)", ""),
    (102, 108, True, "walk", "(I-12)", ""),
    (103, 248, True, "walk", "(I-9)", ""),
    (103, 108, True, "walk", "(K-9)", ""),
    (103, 212, True, "walk", "(H-7)", ""),
    (104, 149, True, "walk", "(H-11)", ""),
    (149, 150, True, "walk", "(H-8)", ""),
    (104, 105, True, "walk", "(K-6)", ""),
    (104, 2, True, "walk", "(E-6)", ""),
    (105, 195, True, "walk", "(J-7)", ""),
    (105, 111, True, "walk", "(D-5)", ""),
    (105, 110, True, "walk", "(I-11)", ""),
    (105, 244, True, "walk", "(K-8)", ""),
    (105, 245, True, "walk", "(K-9)", ""),

    # Fauregandi & Valdeaunia
    (111, 204, True, "walk", "(K-5)", ""),
    (204, 206, True, "walk", "(G-6)", ""),
    (111, 112, True, "walk", "(F-10)", ""),
    (111, 9, True, "walk", "(H-8)", ""),
    (112, 161, True, "walk", "(D-8)", ""),
    (161, 162, True, "walk", "(I-8)", ""),
    (162, 165, True, "walk", "(H-8)", ""),
    (112, 5, True, "walk", "(G-5)", ""),

    # Jeuno & Qufim
    (243, 244, True, "walk", "(H-10)", ""),
    (244, 245, True, "walk", "(G-10)", ""),
    (245, 246, True, "walk", "(G-11)", ""),
    (246, 126, True, "walk", "(J-8)", ""),
    (245, 110, True, "walk", "(G-11)", ""),
    (245, 120, True, "walk", "(H-11)", ""),
    (246, 120, True, "walk", "(G-8)", ""),
    (126, 127, True, "walk", "(E-6)", ""),
    (126, 184, True, "walk", "(H-7)", ""),
    (184, 157, True, "walk", "(H-8)", ""),
    (157, 158, True, "walk", "(H-8)", ""),
    (158, 179, True, "walk", "Elevator (H-8)", "Delkfutt Key"),

    # Airships & Ferries
    (246, 232, True, "transport", "Airship Dock", "Airship Pass"),
    (246, 236, True, "transport", "Airship Dock", "Airship Pass"),
    (246, 240, True, "transport", "Airship Dock", "Airship Pass"),
    (246, 250, True, "transport", "Airship Dock", "Kazham Airship Pass"),
    (248, 249, True, "transport", "Ferry Dock", ""),
    (249, 48, True, "transport", "Ferry to Aht Urhgan", "Boarding Permit"),
    (50, 53, True, "transport", "Silver Sea Ferry", ""),

    # Gustaberg, Bastok & Derfland
    (234, 235, True, "walk", "(H-9)", ""),
    (234, 237, True, "walk", "(J-8)", ""),
    (235, 236, True, "walk", "(I-5)", ""),
    (234, 172, True, "walk", "(D-8)", ""),
    (234, 106, True, "walk", "(I-5)", ""),
    (235, 106, True, "walk", "(D-9)", ""),
    (235, 107, True, "walk", "(E-11)", ""),
    (236, 106, True, "walk", "(G-5)", ""),
    (236, 107, True, "walk", "(J-13)", ""),
    (106, 107, True, "walk", "(F-11)", ""),
    (107, 191, True, "walk", "(E-8)", ""),
    (106, 191, True, "walk", "(D-8)", ""),
    (106, 143, True, "walk", "(K-3)", ""),
    (143, 144, True, "walk", "(H-10)", ""),
    (106, 108, True, "walk", "(F-4)", ""),
    (106, 11, True, "walk", "(L-7)", ""),
    (108, 196, True, "walk", "(J-8)", ""),
    (108, 109, True, "walk", "(L-6)", ""),
    (109, 147, True, "walk", "(L-9)", ""),
    (147, 148, True, "walk", "(I-7)", ""),
    (109, 110, True, "walk", "(K-5)", ""),
    (110, 197, True, "walk", "(E-11)", ""),
    (110, 120, True, "walk", "(J-11)", ""),

    # Sarutabaruta, Windurst & Aragoneu
    (238, 239, True, "walk", "(J-5)", ""),
    (238, 240, True, "walk", "(G-10)", ""),
    (239, 241, True, "walk", "(J-10)", ""),
    (239, 242, True, "walk", "(H-4)", ""),
    (240, 241, True, "walk", "(M-6)", ""),
    (238, 115, True, "walk", "(F-5)", ""),
    (240, 115, True, "walk", "(A-6)", ""),
    (240, 116, True, "walk", "(M-4)", ""),
    (241, 116, True, "walk", "(I-12)", ""),
    (115, 116, True, "walk", "(K-8)", ""),
    (115, 145, True, "walk", "(F-4)", ""),
    (145, 146, True, "walk", "(H-7)", ""),
    (115, 194, True, "walk", "(F-11)", ""),
    (116, 192, True, "walk", "(J-7)", ""),
    (116, 194, True, "walk", "(H-3)", ""),
    (192, 169, True, "gated", "Three Mage Gate (H-9)", "Portal Charm / WHM+BLM+RDM"),
    (239, 169, True, "gated", "Priming Gate (H-3)", "Rhinostery Certificate"),
    (169, 170, True, "walk", "(H-4)", ""),
    (116, 117, True, "walk", "(H-3)", ""),
    (117, 198, True, "walk", "(K-6)", ""),
    (117, 118, True, "walk", "(J-12)", ""),
    (117, 119, True, "walk", "(H-4)", ""),
    (198, 118, True, "walk", "(G-6)", ""),
    (198, 7, True, "walk", "(K-9)", ""),
    (118, 249, True, "walk", "(G-9)", ""),
    (118, 213, True, "walk", "(I-6)", ""),
    (118, 4, True, "walk", "(F-6)", ""),
    (119, 151, True, "walk", "(M-8)", ""),
    (151, 152, True, "walk", "(G-8)", ""),
    (119, 120, True, "walk", "(E-4)", ""),
    (119, 121, True, "walk", "(L-6)", ""),
    (120, 200, True, "walk", "(L-10)", ""),

    # Li'Telor & Tu'Lia (Sky)
    (121, 153, True, "walk", "(K-7)", ""),
    (153, 154, True, "walk", "(D-5)", ""),
    (121, 122, True, "walk", "(I-5)", ""),
    (122, 251, True, "walk", "(H-6)", ""),
    (251, 130, True, "gated", "Shimmering Circle (H-6)", "Sky Access (Zilart M13)"),
    (130, 177, True, "walk", "(H-9)", ""),
    (177, 178, True, "walk", "(H-6)", ""),
    (130, 178, True, "walk", "(H-6)", ""),
    (178, 180, True, "walk", "(H-8)", ""),
    (178, 181, True, "walk", "(H-8)", ""),

    # Kuzotz & Vollbow
    (172, 173, True, "walk", "(F-7)", ""),
    (173, 114, True, "walk", "(A-9)", ""),
    (114, 125, True, "walk", "(E-8)", ""),
    (114, 208, True, "walk", "(I-6)", ""),
    (125, 247, True, "walk", "(G-6)", ""),
    (125, 208, True, "walk", "(D-12)", ""),
    (208, 168, True, "gated", "Weight Door (D-5)", "Loadstone / 3 Players"),
    (125, 174, True, "walk", "(F-4)", ""),
    (174, 113, True, "walk", "(I-9)", ""),
    (113, 128, True, "walk", "(G-5)", ""),
    (212, 113, True, "walk", "(G-6)", ""),
    (212, 128, True, "walk", "(F-6)", ""),

    # Elshimo
    (250, 123, True, "walk", "(F-9)", ""),
    (123, 176, True, "walk", "(K-6)", ""),
    (176, 252, True, "walk", "(J-13)", ""),
    (123, 124, True, "walk", "(F-5)", ""),
    (123, 205, True, "walk", "(F-6)", ""),
    (124, 205, True, "walk", "(G-6)", ""),
    (124, 159, True, "walk", "(J-11)", ""),
    (159, 160, True, "walk", "(H-8)", ""),
    (160, 163, True, "gated", "Unlit Lanterns (E-5)", "4x Rancor Flame"),

    # Avatar Cloisters (201)
    (113, 201, True, "warp", "Cloister of Gales (F-9)", ""),
    (153, 201, True, "warp", "Cloister of Storms (F-6)", ""),
    (204, 201, True, "warp", "Cloister of Frost (H-5)", ""),
    (205, 201, True, "warp", "Cloister of Flames (H-6)", ""),
    (208, 201, True, "warp", "Cloister of Tremors (J-9)", ""),
    (160, 201, True, "warp", "Cloister of Tides (I-12)", ""),

    # CoP, Tavnazia & Sea
    (102, 14, True, "warp", "Crag of Holla (J-8)", ""),
    (108, 14, True, "warp", "Crag of Dem (I-8)", ""),
    (117, 14, True, "warp", "Crag of Mea (G-9)", ""),
    (14, 16, True, "warp", "Large Apparatus", ""),
    (9, 16, True, "gated", "Tower to Spire of Vahzl", "CoP Chapter 5"),
    (16, 24, False, "warp", "Spire Victory Warp", "CoP Chapter 2"),
    (24, 26, True, "walk", "(G-8)", ""),
    (24, 25, True, "walk", "(J-6)", ""),
    (26, 25, True, "walk", "(H-6)", ""),
    (26, 27, True, "walk", "(J-8)", ""),
    (25, 27, True, "walk", "(F-7)", ""),
    (25, 28, True, "gated", "Iron Gate (H-8)", "CoP Chapter 4"),
    (25, 29, True, "gated", "Spatial Displacement (G-6)", "CoP Chapter 2"),
    (25, 30, True, "gated", "Spatial Displacement (F-7)", "CoP Chapter 4"),
    (29, 31, True, "warp", "Spatial Displacement", ""),
    (30, 31, True, "warp", "Spatial Displacement", ""),
    (26, 32, True, "walk", "Walnut Door (K-7)", ""),
    (32, 33, True, "warp", "Airship to Sea", "CoP Chapter 8"),
    (33, 34, True, "walk", "(H-6)", ""),
    (34, 35, True, "walk", "(H-8)", ""),
    (35, 36, True, "warp", "Transcendental Radiance", "CoP Chapter 8"),
    (33, 37, True, "endgame_entry", "Dimensional Portal (H-4)", "Cosmo-Cleanse + White Card"),
    (33, 38, True, "endgame_entry", "Swirling Vortex (E-6)/(K-6)", "Cosmo-Cleanse + Red/Black Card"),
    (5, 6, True, "walk", "(J-9)", ""),
    (7, 8, True, "walk", "(F-6)", ""),
    (9, 10, True, "walk", "(G-8)", ""),
    (11, 12, True, "walk", "(K-10)", ""),
    (12, 13, True, "walk", "(J-9)", ""),

    # Aht Urhgan & Near East
    (50, 48, True, "walk", "(E-8)", ""),
    (48, 51, True, "walk", "(F-10)", ""),
    (50, 52, True, "walk", "(F-8)", ""),
    (51, 52, True, "walk", "(J-6)", ""),
    (51, 65, True, "walk", "(E-12)", ""),
    (65, 67, True, "walk", "(E-8)", ""),
    (51, 62, True, "walk", "(D-10)", ""),
    (62, 61, True, "walk", "(G-8)", ""),
    (62, 64, True, "walk", "(D-8)", ""),
    (51, 68, True, "walk", "(F-5)", ""),
    (52, 68, True, "walk", "(G-10)", ""),
    (53, 79, True, "walk", "(H-6)", ""),
    (50, 79, True, "warp", "Runic Portal (Azouph/Dvucca)", "Runic Portal Permit"),
    (50, 61, True, "warp", "Runic Portal (Halvung)", "Runic Portal Permit"),
    (50, 52, True, "warp", "Runic Portal (Mamool)", "Runic Portal Permit"),
    (50, 54, True, "warp", "Runic Portal (Ilrusi)", "Runic Portal Permit"),
    (79, 54, True, "gated", "Iron Gate (I-6)", "Lamian Fang Key"),
    (79, 57, True, "walk", "(E-9)", ""),
    (54, 57, True, "walk", "(E-8)", ""),
    (54, 60, True, "walk", "Cutter (H-11)", ""),
    (52, 72, True, "gated", "Undersea Ruins Gate (F-6)", "Imperial Silver Piece"),
    (51, 72, True, "gated", "Undersea Ruins Gate (C-8)", "Imperial Silver Piece"),
    (79, 72, True, "gated", "Undersea Ruins Gate (J-9)", "Imperial Silver Piece"),
    (72, 77, True, "endgame_entry", "Runic Seal (G-8)", "Nyzul Isle Disc"),
    (72, 73, True, "endgame_entry", "Remnants Gate", "Remnants Permit"),
    (79, 78, True, "endgame_entry", "Glowing Lamp (F-8)", "Smoldering Lamp"),
    (50, 55, True, "endgame_entry", "Commissions Agency / Runic Portal", "Imperial Army I.D. Tag"),

    # WotG [S] Shadowreign & Odyssey
    (101, 81, True, "warp", "Cavernous Maw (H-5)", "Pure White Feather"),
    (104, 82, True, "warp", "Cavernous Maw (H-11)", "Pure White Feather"),
    (105, 84, True, "warp", "Cavernous Maw (H-5)", "Pure White Feather"),
    (106, 88, True, "warp", "Cavernous Maw (K-7)", "Pure White Feather"),
    (109, 90, True, "warp", "Cavernous Maw (K-8)", "Pure White Feather"),
    (110, 91, True, "warp", "Cavernous Maw (H-6)", "Pure White Feather"),
    (115, 95, True, "warp", "Cavernous Maw (H-9)", "Pure White Feather"),
    (119, 97, True, "warp", "Cavernous Maw (K-6)", "Pure White Feather"),
    (120, 98, True, "warp", "Cavernous Maw (J-10)", "Pure White Feather"),
    (80, 81, True, "walk", "(I-11)", ""),
    (81, 82, True, "walk", "(G-11)", ""),
    (81, 86, True, "walk", "(F-10)", ""),
    (82, 85, True, "walk", "(F-8)", ""),
    (82, 83, True, "walk", "(F-11)", ""),
    (82, 84, True, "walk", "(K-6)", ""),
    (83, 90, True, "walk", "(J-11)", ""),
    (84, 91, True, "walk", "(I-11)", ""),
    (84, 175, True, "walk", "(J-7)", ""),
    (84, 136, True, "walk", "(D-5)", ""),
    (136, 137, True, "walk", "(F-10)", ""),
    (137, 138, True, "walk", "(D-8)", ""),
    (138, 155, True, "walk", "(I-8)", ""),
    (155, 156, True, "walk", "(H-8)", ""),
    (137, 182, True, "endgame_entry", "Veridical Conflux (H-9)", "Kupofried's Medallion"),
    (182, 222, True, "endgame_entry", "Shimmering Displacement", "Voidwatch Final Tier"),
    (87, 88, True, "walk", "(D-9)", ""),
    (88, 89, True, "walk", "(E-7)", ""),
    (88, 86, True, "walk", "(K-3)", ""),
    (89, 90, True, "walk", "(J-6)", ""),
    (90, 92, True, "walk", "(L-9)", ""),
    (90, 91, True, "walk", "(K-5)", ""),
    (91, 171, True, "walk", "(E-11)", ""),
    (91, 98, True, "walk", "(J-11)", ""),
    (94, 95, True, "walk", "(F-5)", ""),
    (95, 86, True, "walk", "(F-4)", ""),
    (95, 96, True, "walk", "(G-11)", ""),
    (96, 97, True, "walk", "(J-6)", ""),
    (97, 99, True, "walk", "(M-8)", ""),
    (97, 98, True, "walk", "(E-4)", ""),
    (98, 164, True, "walk", "(L-10)", ""),
    (247, 298, True, "endgame_entry", "Veridical Conflux (G-6)", "Lustreless Scale/Hide/Wing"),

    # Adoulin, Ulbuka & Sortie
    (245, 256, True, "warp", "Geomagnetic Fount / Daurdabla", "Adoulin Charter Permit"),
    (256, 257, True, "walk", "Big Bridge (J-9)", ""),
    (257, 284, True, "walk", "(F-7)", ""),
    (256, 258, True, "walk", "(E-8)", ""),
    (257, 258, True, "walk", "(G-9)", ""),
    (257, 259, True, "endgame_entry", "Odyssean Passage", "Simulacrum / Vagary Key"),
    (256, 260, True, "walk", "(E-5)", ""),
    (256, 261, True, "walk", "(E-11)", ""),
    (261, 281, True, "walk", "(H-11)", ""),
    (260, 268, True, "walk", "(F-7)", ""),
    (261, 268, True, "walk", "(F-6)", ""),
    (260, 269, True, "walk", "(G-10)", ""),
    (261, 269, True, "walk", "(G-4)", ""),
    (268, 262, True, "walk", "(F-10)", ""),
    (269, 265, True, "walk", "(G-6)", ""),
    (268, 270, True, "walk", "(H-8)", ""),
    (269, 270, True, "walk", "(H-6)", ""),
    (270, 263, True, "walk", "(G-9)", ""),
    (262, 272, True, "walk", "(F-7)", ""),
    (263, 272, True, "walk", "(F-8)", ""),
    (272, 266, True, "walk", "(G-7)", ""),
    (265, 273, True, "walk", "(E-6)", ""),
    (266, 273, True, "walk", "(G-5)", ""),
    (270, 273, True, "walk", "(I-6)", ""),
    (273, 267, True, "walk", "(G-6)", ""),
    (267, 274, True, "walk", "Transposer (F-6)", ""),
    (274, 276, True, "walk", "(H-8)", ""),
    (276, 277, True, "endgame_entry", "Diaphanous Transposer", "SoA / Sinister Reign"),
    (274, 275, True, "endgame_entry", "Diaphanous Transposer (G-8)", "Ra'Kaznar Plate"),
    (267, 275, True, "endgame_entry", "Diaphanous Transposer (F-6)", "Ra'Kaznar Plate"),

    # Escha, Reisenjima & Omen
    (126, 288, True, "warp", "Undulating Confluence (F-8)", "RoV Chapter 1"),
    (102, 288, True, "warp", "Undulating Confluence (J-7)", "RoV Chapter 1"),
    (108, 288, True, "warp", "Undulating Confluence (I-6)", "RoV Chapter 1"),
    (117, 288, True, "warp", "Undulating Confluence (H-11)", "RoV Chapter 1"),
    (25, 289, True, "warp", "Undulating Confluence (G-5)", "RoV Chapter 2"),
    (126, 289, True, "warp", "Undulating Confluence (G-6)", "RoV Chapter 2"),
    (102, 291, True, "warp", "Dimensional Portal (J-8)", "RoV Chapter 3"),
    (108, 291, True, "warp", "Dimensional Portal (I-7)", "RoV Chapter 3"),
    (117, 291, True, "warp", "Dimensional Portal (H-11)", "RoV Chapter 3"),
    (291, 292, True, "endgame_entry", "Ethereal Ingress (F-5)", "Mystical Canteen"),
    (291, 293, True, "endgame_entry", "Etched Rock (#9)", "RoV Final Mission"),

    # Abyssea & Dynamis / [D]
    (108, 15, True, "endgame_entry", "Cavernous Maw (I-12)", "Traverser Stone"),
    (117, 45, True, "endgame_entry", "Cavernous Maw (H-12)", "Traverser Stone"),
    (102, 132, True, "endgame_entry", "Cavernous Maw (E-4)", "Traverser Stone"),
    (118, 215, True, "endgame_entry", "Cavernous Maw (F-7)", "Traverser Stone"),
    (103, 216, True, "endgame_entry", "Cavernous Maw (I-9)", "Traverser Stone"),
    (104, 217, True, "endgame_entry", "Cavernous Maw (J-8)", "Traverser Stone"),
    (107, 218, True, "endgame_entry", "Cavernous Maw (J-10)", "Traverser Stone"),
    (112, 253, True, "endgame_entry", "Cavernous Maw (H-8)", "Traverser Stone"),
    (106, 254, True, "endgame_entry", "Cavernous Maw (G-7)", "Traverser Stone"),
    (126, 255, True, "endgame_entry", "Transcendental Radiance (F-7)", "Abyssea 9x Clear"),
    (243, 294, True, "endgame_entry", "Enigmatic Footprints (I-9)", "Blackened Hourglass"),
    (230, 294, True, "endgame_entry", "Enigmatic Footprints (M-5)", "Blackened Hourglass"),
    (234, 294, True, "endgame_entry", "Enigmatic Footprints (K-8)", "Blackened Hourglass"),
    (239, 294, True, "endgame_entry", "Enigmatic Footprints (C-12)", "Blackened Hourglass"),
    (243, 185, True, "endgame_entry", "Trail Markings (I-9)", "Prismatic Hourglass"),
    (111, 185, True, "endgame_entry", "Trail Markings (F-10)", "Prismatic Hourglass"),
    (112, 185, True, "endgame_entry", "Trail Markings (J-9)", "Prismatic Hourglass"),
    (103, 39, True, "endgame_entry", "Hieroglyphics (G-8)", "Prismatic Hourglass"),
    (118, 39, True, "endgame_entry", "Hieroglyphics (I-9)", "Prismatic Hourglass"),
    (126, 39, True, "endgame_entry", "Hieroglyphics (H-7)", "Prismatic Hourglass"),
    (26, 39, True, "endgame_entry", "Hieroglyphics (H-9)", "Prismatic Hourglass"),
]


# ---------------------------------------------------------------------------------------------------------
# BG-Wiki connection data (tools/fetch_zone_connections.py -> tools/world_map/zone_connections.json)
#
# Walking connections, one-way exits, Cavernous Maws/Confluxes, boats and airships come from the wiki's
# "Connected Zone" tables. RAW_EDGES above is only used to (a) add a gate name / key item to a connection the
# wiki also has, and (b) reach instanced zones whose wiki pages have no connection table. A hand-written
# edge between two zones that both have wiki tables, but which the wiki doesn't list, is dropped.
# ---------------------------------------------------------------------------------------------------------
WIKI_CONNECTIONS_PATH = os.path.join(REPO_ROOT, "tools", "world_map", "zone_connections.json")

# Consolidated nodes whose members are entered from different places. Routing to "Dynamis - Bastok" must end
# at Bastok's entrance, so these become one node per zone. True multi-layer instances (Sortie, Odyssey,
# Salvage, Dynamis [D]) stay consolidated, as do the Campaign and [U] instances (the wiki tables don't say
# where each one is entered).
DISSOLVE_CONSOLIDATED: set[int] = {16, 201, 185, 39, 55}

# Hand-written edges kept even though the wiki tables don't list them.
KEEP_CURATED_PAIRS: set[frozenset[int]] = {
    frozenset((245, 256)),  # Jeuno <-> Adoulin: the wiki tables don't describe this trip. UNVERIFIED.
}

# Requirements on hand-written edges that the wiki contradicts.
REQUIREMENT_OVERRIDES: dict[frozenset[int], str] = {
    frozenset((126, 288)): "",  # Escha - Zi'Tah: BG-Wiki lists no requirement
    frozenset((25, 289)): "",   # Escha - Ru'Aun: BG-Wiki lists no requirement
}

# One-way drops where the two wiki pages disagree about direction: (from node, to node).
ONE_WAY_OVERRIDES: set[tuple[int, int]] = {
    (167, 100),  # Bostaunieux Oubliette drops into West Ronfaure; there is no way back in from there
}

ONE_WAY_EXIT = {"exit", "exit only", "exit to only", "exits to only"}
ONE_WAY_ENTER = {"enter", "entrance", "entrance only", "enter only"}
WARP_FLAGS = ("maw", "conflux", "runic portal", "staging point", "portal", "displacement")
IGNORED_ROWS = {"chocobo circuit", "the colosseum", "mog house", "survival guide", "phanauet channel",
                "manaclipper"}
NAME_ALIASES = {"crawler's nest": "Crawlers' Nest", "celestial nexus": "The Celestial Nexus",
                "empyreal paradox": "Empyreal Paradox"}
# Assault staging points (wiki rows on the zone that holds them) -> the Assault area they lead to.
STAGING_POINTS = {
    "mamool ja staging point": "Mamool Ja Training Grounds",
    "ilrusi atoll staging point": "Ilrusi Atoll",
    "halvung staging point": "Lebros Cavern",
    "azouph isle staging point": "Leujaoam Sanctum",
    "dvucca isle staging point": "Periqia",
}
TRANSPORT_REQUIREMENTS = {
    "airship, jeuno - kazham": "Airship Pass for Kazham",
    "airship, jeuno - san d'oria": "Airship Pass",
    "airship, jeuno - bastok": "Airship Pass",
    "airship, jeuno - windurst": "Airship Pass",
    "ferry - mhaura/al zahbi": "Boarding Permit",
}


def load_wiki_connections(path: str = WIKI_CONNECTIONS_PATH) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def make_name_resolver(windower_zones: dict[int, dict]):
    index: dict[str, int] = {}
    for zid, info in windower_zones.items():
        if zid in EXCLUDED_ZONE_IDS:
            continue
        name = info["en"]
        for variant in (name, re.sub(r"\s*\[S\]$", " (S)", name), name.replace("#", "")):
            index.setdefault(" ".join(variant.split()).casefold(), zid)

    def resolve(name: str) -> int | None:
        key = " ".join(name.split()).casefold()
        key = NAME_ALIASES.get(key, key)
        return index.get(" ".join(key.split()).casefold())

    return resolve


def _grid(pos: str) -> str:
    pos = pos.strip().strip("()")
    return f"({pos})" if pos else ""


def _join_positions(values: list[str]) -> str:
    seen: list[str] = []
    for v in values:
        g = _grid(v)
        if g and g not in seen:
            seen.append(g)
    return " / ".join(seen)


def build_wiki_edges(wiki: dict, resolve, node_of: dict[int, int]) -> tuple[dict[frozenset[int], dict], list[str]]:
    """Returns ({node pair: edge dict}, warnings)."""
    warnings: list[str] = []
    rows_by_pair: dict[tuple[int, int], list[dict]] = {}
    vessels: dict[str, list[tuple[int, dict]]] = {}
    edges_staging: list[tuple[int, int, dict]] = []
    for wid_str, page in wiki["zones"].items():
        a = node_of.get(int(wid_str))
        if a is None:
            continue
        for row in page["connections"]:
            name = " ".join(row["zone"].split())
            low = name.casefold()
            if "escape" in (row["here"].casefold(), row["there"].casefold()):
                continue  # where the Escape spell drops you, not a real exit
            if low in STAGING_POINTS:
                b_wid = resolve(STAGING_POINTS[low])
                if b_wid in node_of:
                    edges_staging.append((a, node_of[b_wid], row))
                continue
            if low in IGNORED_ROWS:
                continue
            if low.startswith("airship,") or low.startswith("ferry -"):
                vessels.setdefault(low, []).append((a, row))
                continue
            b_wid = resolve(name)
            if b_wid is None or b_wid not in node_of:
                warnings.append(f"unknown zone '{name}' on page {page['name']}")
                continue
            b = node_of[b_wid]
            if a != b:
                rows_by_pair.setdefault((a, b), []).append(row)

    edges: dict[frozenset[int], dict] = {}
    for a, b in sorted({tuple(sorted(p)) for p in rows_by_pair}):
        ab = rows_by_pair.get((a, b), [])   # rows on a's page listing b
        ba = rows_by_pair.get((b, a), [])   # rows on b's page listing a
        # A pair is two-way if any exit between them is two-way; flags mark single one-way exit points.
        dirs: set[tuple[int, int]] = set()
        two_way = False
        warp = False
        for here, there, rows in ((a, b, ab), (b, a, ba)):
            for r in rows:
                flag = r.get("only", "").strip().casefold()
                if any(w in flag for w in WARP_FLAGS):
                    warp = True
                if flag in ONE_WAY_EXIT:
                    dirs.add((here, there))
                elif flag in ONE_WAY_ENTER:
                    dirs.add((there, here))
                else:
                    two_way = True
        if (a, b) in ONE_WAY_OVERRIDES or (b, a) in ONE_WAY_OVERRIDES:
            dirs = {(a, b)} if (a, b) in ONE_WAY_OVERRIDES else {(b, a)}
        elif two_way or not dirs:
            dirs = {(a, b), (b, a)}
        frm, to = (a, b) if (a, b) in dirs else (b, a)
        pos_in = {a: [r["here"] for r in ab] + [r["there"] for r in ba],
                  b: [r["here"] for r in ba] + [r["there"] for r in ab]}
        edges[frozenset((a, b))] = {
            "from_id": frm, "to_id": to, "bidirectional": len(dirs) == 2,
            "kind": "warp" if warp else "walk",
            "exit_pos": _join_positions(pos_in[frm]), "entry_pos": _join_positions(pos_in[to]),
            "requirement": "", "source": "bg-wiki",
        }

    for vessel, listers in sorted(vessels.items()):
        req = TRANSPORT_REQUIREMENTS.get(vessel, "")
        ends = sorted({a for a, _ in listers})
        if vessel.startswith("airship,"):
            ends = sorted(set(ends) | {DEFAULT_PORT_JEUNO})
        pos = {a: _join_positions([r["here"] for x, r in listers if x == a]) for a in ends}
        label = vessel.split(",")[0].title() if vessel.startswith("airship") else "Ferry"
        for i, a in enumerate(ends):
            for b in ends[i + 1:]:
                edges[frozenset((a, b))] = {
                    "from_id": a, "to_id": b, "bidirectional": True, "kind": "transport",
                    "exit_pos": f"{label} {pos.get(a, '')}".strip(), "entry_pos": f"{label} {pos.get(b, '')}".strip(),
                    "requirement": req, "source": "bg-wiki",
                }
    for a, b, row in edges_staging:
        edges[frozenset((a, b))] = {
            "from_id": a, "to_id": b, "bidirectional": True, "kind": "endgame_entry",
            "exit_pos": f"{row['zone']} {_grid(row['here'])}".strip(), "entry_pos": "",
            "requirement": "Assault Orders (Imperial Army I.D. Tag)", "source": "bg-wiki",
        }
    return edges, warnings


DEFAULT_PORT_JEUNO = 246


def parse_windower_zones(path: str) -> dict[int, dict]:
    zones: dict[int, dict] = {}
    line_re = re.compile(r"^\s*\[(\d+)\]\s*=\s*\{(.+)\},\s*$")
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = line_re.match(line)
            if not m:
                continue
            zid = int(m.group(1))
            body = m.group(2)
            en_match = re.search(r'en="((?:\\"|[^"])*)"', body)
            search_match = re.search(r'search="((?:\\"|[^"])*)"', body)
            can_mount = "can_mount=true" in body
            zones[zid] = {
                "id": zid,
                "en": en_match.group(1).replace('\\"', '"') if en_match else f"Zone {zid}",
                "search": search_match.group(1) if search_match else "",
                "can_mount": can_mount,
            }
    return zones


def parse_windower_homepoints(path: str) -> dict[str, list[str]]:
    by_zone: dict[str, list[str]] = {}
    key_re = re.compile(r'\["((?:\\.|[^"])*)"\]\s*=')
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            m = key_re.search(line)
            if not m:
                continue
            raw_key = m.group(1)
            # Unescape Lua backslashes (e.g. \[S\], \#B01, \')
            unescaped = re.sub(r"\\(.)", r"\1", raw_key)
            # Split off trailing crystal number: "Southern San d'Oria [S] 1" -> "Southern San d'Oria [S]"
            parts = unescaped.rsplit(" ", 1)
            if len(parts) == 2 and parts[1].isdigit():
                zone_name = parts[0]
                by_zone.setdefault(zone_name, []).append(unescaped)
    for zname, extra_list in SUPPLEMENTAL_HOMEPOINTS.items():
        existing = by_zone.setdefault(zname, [])
        for hp in extra_list:
            if hp not in existing:
                existing.append(hp)
    for zname in by_zone:
        by_zone[zname].sort(key=lambda s: int(s.rsplit(" ", 1)[1]))
    return by_zone


NODE_HALF_W = 76.0
NODE_HALF_H = 16.0


def _segment_hits_box(x1, y1, x2, y2, cx, cy, hw=NODE_HALF_W + 4.0, hh=NODE_HALF_H + 4.0) -> bool:
    """Liang-Barsky clip: does segment (x1,y1)-(x2,y2) pass through the box centred at (cx,cy)?"""
    dx, dy = x2 - x1, y2 - y1
    t0, t1 = 0.0, 1.0
    for p, q in ((-dx, x1 - (cx - hw)), (dx, (cx + hw) - x1), (-dy, y1 - (cy - hh)), (dy, (cy + hh) - y1)):
        if p == 0:
            if q < 0:
                return False
            continue
        t = q / p
        if p < 0:
            if t > t1:
                return False
            t0 = max(t0, t)
        else:
            if t < t0:
                return False
            t1 = min(t1, t)
    return t0 < t1


def count_pass_throughs(zones: list[dict], edges: list[dict]) -> int:
    pos = {z["id"]: (z["x"], z["y"]) for z in zones}
    hits = 0
    for e in edges:
        (x1, y1), (x2, y2) = pos[e["from_id"]], pos[e["to_id"]]
        if math.hypot(x2 - x1, y2 - y1) > 700.0:
            continue  # long cross-region links are hidden on the canvas unless selected
        for z in zones:
            if z["id"] in (e["from_id"], e["to_id"]):
                continue
            if _segment_hits_box(x1, y1, x2, y2, z["x"], z["y"]):
                hits += 1
    return hits


def _optimize_region_cells(members: list[dict], cells: list[tuple[float, float]], zones: list[dict],
                           incident: dict[int, list[int]]) -> None:
    """Greedy pairwise swaps of grid cells (including empty ones) to shorten edges and avoid boxes."""
    pos = {z["id"]: [z["x"], z["y"]] for z in zones}
    member_ids = [z["id"] for z in members]
    slot: dict[int, int] = {}   # cell index -> zone id
    for zid in member_ids:
        for ci, (cx, cy) in enumerate(cells):
            if abs(cx - pos[zid][0]) < 1 and abs(cy - pos[zid][1]) < 1:
                slot[ci] = zid
    nearby = [z["id"] for z in zones]

    def cost(zid: int) -> float:
        x, y = pos[zid]
        total = 0.0
        for other in incident.get(zid, []):
            ox, oy = pos[other]
            d = math.hypot(ox - x, oy - y)
            total += d
            if d <= 700.0:
                for n in nearby:
                    if n != zid and n != other and _segment_hits_box(x, y, ox, oy, pos[n][0], pos[n][1]):
                        total += 260.0
        return total

    for _ in range(12):
        improved = False
        for i in range(len(cells)):
            for j in range(i + 1, len(cells)):
                a, b = slot.get(i), slot.get(j)
                if a is None and b is None:
                    continue
                movers = [m for m in (a, b) if m is not None]
                before = sum(cost(m) for m in movers)
                if a is not None:
                    pos[a] = list(cells[j])
                if b is not None:
                    pos[b] = list(cells[i])
                after = sum(cost(m) for m in movers)
                if after + 1e-6 < before:
                    improved = True
                    if a is not None:
                        slot[j] = a
                    else:
                        slot.pop(j, None)
                    if b is not None:
                        slot[i] = b
                    else:
                        slot.pop(i, None)
                else:
                    if a is not None:
                        pos[a] = list(cells[i])
                    if b is not None:
                        pos[b] = list(cells[j])
        if not improved:
            break
    for z in members:
        z["x"], z["y"] = round(pos[z["id"]][0], 1), round(pos[z["id"]][1], 1)


REGION_GAP = 60.0


def _region_box(members: list[dict]) -> tuple[float, float, float, float]:
    """Halo box as the canvas draws it: node boxes plus banner room on top."""
    return (min(z["x"] for z in members) - NODE_HALF_W - 28.0, min(z["y"] for z in members) - NODE_HALF_H - 34.0,
            max(z["x"] for z in members) + NODE_HALF_W + 28.0, max(z["y"] for z in members) + NODE_HALF_H + 24.0)


def separate_regions(by_region: dict[str, list[dict]]) -> None:
    """Push overlapping region boxes apart, moving each region as a block, so halos never overlap."""
    ids = sorted(rid for rid, m in by_region.items() if m)
    for _ in range(400):
        moved = False
        boxes = {rid: _region_box(by_region[rid]) for rid in ids}
        for i, a in enumerate(ids):
            for b in ids[i + 1:]:
                ax1, ay1, ax2, ay2 = boxes[a]
                bx1, by1, bx2, by2 = boxes[b]
                ox = min(ax2, bx2) - max(ax1, bx1) + REGION_GAP
                oy = min(ay2, by2) - max(ay1, by1) + REGION_GAP
                if ox <= 0 or oy <= 0:
                    continue
                moved = True
                if ox < oy:
                    sign = 1.0 if (bx1 + bx2) >= (ax1 + ax2) else -1.0
                    dx, dy = sign * (ox / 2.0 + 1.0), 0.0
                else:
                    sign = 1.0 if (by1 + by2) >= (ay1 + ay2) else -1.0
                    dx, dy = 0.0, sign * (oy / 2.0 + 1.0)
                for z in by_region[a]:
                    z["x"] = round(z["x"] - dx, 1); z["y"] = round(z["y"] - dy, 1)
                for z in by_region[b]:
                    z["x"] = round(z["x"] + dx, 1); z["y"] = round(z["y"] + dy, 1)
                boxes[a] = _region_box(by_region[a]); boxes[b] = _region_box(by_region[b])
        if not moved:
            break
    # Shift everything so the map starts near the canvas origin
    all_z = [z for rid in ids for z in by_region[rid]]
    min_x = min(_region_box(by_region[rid])[0] for rid in ids)
    min_y = min(_region_box(by_region[rid])[1] for rid in ids)
    for z in all_z:
        z["x"] = round(z["x"] - min_x + 80.0, 1)
        z["y"] = round(z["y"] - min_y + 80.0, 1)


def layout_nodes_within_regions(regions: list[dict], zones: list[dict], edges: list[dict] | None = None) -> None:
    """Place nodes on a grid inside each regional cluster, then swap cells so linked zones sit together."""
    region_map = {r["id"]: r for r in regions}
    by_region: dict[str, list[dict]] = {r["id"]: [] for r in regions}
    for z in zones:
        by_region[z["region_id"]].append(z)

    kind_order = {"hub": 0, "field": 1, "dungeon": 2, "endgame": 3}
    cells_by_region: dict[str, list[tuple[float, float]]] = {}
    for rid, members in by_region.items():
        reg = region_map[rid]
        members.sort(key=lambda z: (kind_order.get(z["kind"], 9), z["id"]))
        n = len(members)
        if n == 0:
            continue
        cols = 5 if n >= 20 else (4 if n >= 13 else (3 if n >= 7 else 2))
        rows = math.ceil(n / cols)
        if rows * cols - n < 2:
            rows += 1  # spare cells give the optimiser room to move
        dx, dy = 178.0, 50.0
        start_x = reg["cx"] - ((cols - 1) * dx) / 2.0
        start_y = reg["cy"] - ((rows - 1) * dy) / 2.0 + 10.0
        cells = [(round(start_x + c * dx, 1), round(start_y + r * dy, 1)) for r in range(rows) for c in range(cols)]
        cells_by_region[rid] = cells
        for idx, z in enumerate(members):
            z["x"], z["y"] = cells[idx]

    if edges:
        incident: dict[int, list[int]] = {}
        for e in edges:
            incident.setdefault(e["from_id"], []).append(e["to_id"])
            incident.setdefault(e["to_id"], []).append(e["from_id"])
        for _ in range(2):
            for rid, members in by_region.items():
                if members:
                    _optimize_region_cells(members, cells_by_region[rid], zones, incident)

    separate_regions(by_region)

    # Safety net: node-level collision relaxation (the grids and region separation should leave none)
    min_dx, min_dy = 165.0, 42.0
    for _ in range(200):
        moved = False
        for i in range(len(zones)):
            for j in range(i + 1, len(zones)):
                a, b = zones[i], zones[j]
                ddx, ddy = b["x"] - a["x"], b["y"] - a["y"]
                if abs(ddx) < min_dx and abs(ddy) < min_dy:
                    moved = True
                    ox, oy = min_dx - abs(ddx), min_dy - abs(ddy)
                    if ox < oy:
                        push = (ox / 2.0 + 1.0) * (1.0 if ddx >= 0 else -1.0)
                        a["x"] = round(a["x"] - push, 1); b["x"] = round(b["x"] + push, 1)
                    else:
                        push = (oy / 2.0 + 1.0) * (1.0 if ddy >= 0 else -1.0)
                        a["y"] = round(a["y"] - push, 1); b["y"] = round(b["y"] + push, 1)
        if not moved:
            break

    for rid, members in by_region.items():
        if not members:
            continue
        reg = region_map[rid]
        min_x = min(z["x"] - 85.0 for z in members)
        max_x = max(z["x"] + 85.0 for z in members)
        min_y = min(z["y"] - 24.0 for z in members)
        max_y = max(z["y"] + 24.0 for z in members)
        reg["cx"] = round((min_x + max_x) / 2.0, 1)
        reg["cy"] = round((min_y + max_y) / 2.0, 1)
        reg["rx"] = round((max_x - min_x) / 2.0 + 36.0, 1)
        reg["ry"] = round((max_y - min_y) / 2.0 + 34.0, 1)


def build_world_map_dataset(report: list[str] | None = None) -> dict:
    report = report if report is not None else []
    windower_zones = parse_windower_zones(WINDOWER_ZONES_PATH)
    homepoint_names = parse_windower_homepoints(WINDOWER_HOMEPOINTS_PATH)
    wiki = load_wiki_connections()
    resolve = make_name_resolver(windower_zones)
    region_eras = {r["id"]: r["era"] for r in REGIONS}

    consolidated = {k: v for k, v in CONSOLIDATED_NODES.items() if k not in DISSOLVE_CONSOLIDATED}
    catalog = dict(ZONE_CATALOG)
    dissolved_ids: set[int] = set()
    for pid in sorted(DISSOLVE_CONSOLIDATED):
        meta = CONSOLIDATED_NODES[pid]
        for mid in meta["member_zone_ids"]:
            catalog[mid] = (meta["region_id"], meta["kind"], None, None, [], "")
            dissolved_ids.add(mid)

    # Verify completeness of res/zones.lua coverage
    covered_ids: set[int] = set(EXCLUDED_ZONE_IDS.keys())
    for primary_id, cmeta in consolidated.items():
        for mid in cmeta["member_zone_ids"]:
            if mid in covered_ids:
                raise AssertionError(f"Duplicate member_zone_id {mid}")
            covered_ids.add(mid)
    for zid in catalog:
        if zid in covered_ids:
            raise AssertionError(f"Zone {zid} in both CONSOLIDATED_NODES/EXCLUDED and ZONE_CATALOG")
        covered_ids.add(zid)
    missing_from_seed = sorted(set(windower_zones.keys()) - covered_ids)
    extra_in_seed = sorted(covered_ids - set(windower_zones.keys()))
    if missing_from_seed or extra_in_seed:
        raise AssertionError(f"Zone coverage mismatch! Missing={missing_from_seed}, Extra={extra_in_seed}")

    # Survival Guides and Home Points from BG-Wiki's master lists
    sg_wids = set()
    for name in wiki.get("survival_guides", []):
        wid = resolve(name)
        if wid is None:
            report.append(f"Survival Guide list: unknown zone '{name}'")
        else:
            sg_wids.add(wid)
    hp_by_wid: dict[int, list[str]] = {}
    for name, numbers in wiki.get("home_points", {}).items():
        wid = resolve(name)
        if wid is None:
            report.append(f"Home Point list: unknown zone '{name}'")
            continue
        en = windower_zones[wid]["en"]
        hp_by_wid[wid] = [f"{en} #{n}" for n in sorted(numbers)]
    # Zones the wiki list doesn't cover but Windower's Homepoints addon knows.
    for wid, info in windower_zones.items():
        if wid in EXCLUDED_ZONE_IDS or wid in hp_by_wid or not homepoint_names.get(info["en"]):
            continue
        if info["en"] in SUPPLEMENTAL_HOMEPOINTS:
            continue  # guesses from the original seed, not confirmed by BG-Wiki
        hp_by_wid[wid] = [f"{info['en']} #{n.rsplit(' ', 1)[1]}" for n in homepoint_names[info["en"]]]
        report.append(f"Home Points for {info['en']} from Windower's Homepoints addon (not on BG-Wiki list)")

    def aliases_for(base: list[str], member_ids: list[int]) -> list[str]:
        out = list(base)
        for mid in member_ids:
            for extra in (windower_zones[mid]["en"], windower_zones[mid]["search"]):
                if extra and extra not in out:
                    out.append(extra)
        return out

    zones: list[dict] = []
    for primary_id, cmeta in sorted(consolidated.items()):
        members = cmeta["member_zone_ids"]
        zones.append({
            "id": primary_id, "member_zone_ids": members, "name": cmeta["name"],
            "short_name": cmeta["short_name"][:26], "aliases": aliases_for(cmeta["aliases"], members),
            "region_id": cmeta["region_id"], "era": cmeta["era"], "kind": cmeta["kind"], "x": 0.0, "y": 0.0,
            "can_mount": any(windower_zones[m]["can_mount"] for m in members),
            "homepoints": [hp for m in members for hp in hp_by_wid.get(m, [])],
            "has_survival_guide": any(m in sg_wids for m in members),
            "wiki_slug": cmeta["wiki_slug"], "notes": cmeta["notes"],
        })
    for zid, (region_id, kind, short_override, wiki_slug, extra_aliases, notes) in sorted(catalog.items()):
        en_name = windower_zones[zid]["en"]
        short_name = short_override or en_name
        if len(short_name) > 26:
            short_name = short_name[:25] + "…"
        zones.append({
            "id": zid, "member_zone_ids": [zid], "name": en_name, "short_name": short_name,
            "aliases": aliases_for(extra_aliases, [zid]), "region_id": region_id,
            "era": region_eras[region_id], "kind": kind, "x": 0.0, "y": 0.0,
            "can_mount": windower_zones[zid]["can_mount"], "homepoints": hp_by_wid.get(zid, []),
            "has_survival_guide": zid in sg_wids, "wiki_slug": wiki_slug, "notes": notes,
        })
    zones.sort(key=lambda z: z["id"])
    zone_by_id = {z["id"]: z for z in zones}
    node_of = {m: z["id"] for z in zones for m in z["member_zone_ids"]}

    # Edges: BG-Wiki first, then hand-written detail and instance entrances
    edge_map, warnings = build_wiki_edges(wiki, resolve, node_of)
    report.extend(warnings)
    wiki_nodes = {node_of[int(w)] for w, p in wiki["zones"].items() if p["connections"] and int(w) in node_of}
    for from_w, to_w, bidir, kind, exit_pos, req in RAW_EDGES:
        a, b = node_of[from_w], node_of[to_w]
        if a == b:
            continue
        key = frozenset((a, b))
        req = REQUIREMENT_OVERRIDES.get(key, req)
        label = re.sub(r"\s*\([A-Z]-\d+[^)]*\)", "", exit_pos).strip()
        if key in edge_map:
            e = edge_map[key]
            if kind in ("gated", "endgame_entry", "warp") and e["kind"] in ("walk", "warp"):
                e["kind"] = kind
            if req and not e["requirement"]:
                e["requirement"] = req
            if label and e["kind"] != "transport":
                if e["from_id"] == a:
                    e["exit_pos"] = f"{label} {e['exit_pos']}".strip()
                else:
                    e["entry_pos"] = f"{label} {e['entry_pos']}".strip()
            continue
        if a in wiki_nodes and b in wiki_nodes and key not in KEEP_CURATED_PAIRS:
            report.append(f"Dropped hand-written edge not on BG-Wiki: {zone_by_id[a]['name']} -> "
                          f"{zone_by_id[b]['name']} ({kind}; {exit_pos}; {req})")
            continue
        edge_map[key] = {"from_id": a, "to_id": b, "bidirectional": bidir, "kind": kind,
                         "exit_pos": exit_pos, "entry_pos": "", "requirement": req,
                         "source": "unverified" if key in KEEP_CURATED_PAIRS else "curated"}
    edges = sorted(edge_map.values(), key=lambda e: (e["from_id"], e["to_id"]))
    for e in edges:  # walking into an instanced area is an instance entrance
        if e["kind"] == "walk" and "endgame" in (zone_by_id[e["from_id"]]["kind"], zone_by_id[e["to_id"]]["kind"]):
            e["kind"] = "endgame_entry"

    # Dissolved nodes (cloisters, Promyvions…) sit in the region of the zone they're entered from
    adjacency: dict[int, set[int]] = {zid: set() for zid in zone_by_id}
    for e in edges:
        adjacency[e["from_id"]].add(e["to_id"])
        adjacency[e["to_id"]].add(e["from_id"])
    for zid in sorted(dissolved_ids):
        z = zone_by_id[zid]
        parents = [zone_by_id[n] for n in sorted(adjacency[zid]) if n not in dissolved_ids]
        if parents and z["kind"] != "endgame":
            z["region_id"] = parents[0]["region_id"]
            z["era"] = region_eras[z["region_id"]]

    # 100% reachability from Port Jeuno (246), following one-way edges
    out_adj: dict[int, set[int]] = {zid: set() for zid in zone_by_id}
    for e in edges:
        out_adj[e["from_id"]].add(e["to_id"])
        if e["bidirectional"]:
            out_adj[e["to_id"]].add(e["from_id"])
    visited: set[int] = {246}
    queue: deque[int] = deque([246])
    while queue:
        curr = queue.popleft()
        for nxt in out_adj[curr]:
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    unreachable = sorted(set(zone_by_id) - visited)
    if unreachable:
        raise AssertionError("Unreachable zones from Port Jeuno (246): "
                             + ", ".join(f"{u} ({zone_by_id[u]['name']})" for u in unreachable))

    regions_copy = [dict(r) for r in REGIONS]
    layout_nodes_within_regions(regions_copy, zones, edges)

    for i in range(len(zones)):
        for j in range(i + 1, len(zones)):
            a, b = zones[i], zones[j]
            if abs(a["x"] - b["x"]) < 164.0 and abs(a["y"] - b["y"]) < 41.0:
                raise AssertionError(f"Node overlap between {a['name']} and {b['name']}")

    return {
        "schema_version": 1,
        "canvas": {"width": int(max(z["x"] for z in zones) + 200), "height": int(max(z["y"] for z in zones) + 160)},
        "sources": {"connections": f"BG-Wiki, fetched {wiki.get('fetched', '?')}"},
        "excluded_zone_ids": {str(k): v for k, v in sorted(EXCLUDED_ZONE_IDS.items())},
        "regions": regions_copy,
        "zones": zones,
        "edges": edges,
    }


def main() -> int:
    report: list[str] = []
    data = build_world_map_dataset(report)
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    for line in report:
        print("  note:", line)
    print(
        f"Seeded {len(data['zones'])} zones, {len(data['regions'])} regions, "
        f"and {len(data['edges'])} edges -> {OUTPUT_PATH}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
