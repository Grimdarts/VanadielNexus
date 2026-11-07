"""Reviewed exact-item hand evidence, independent of names or inferred categories.

Scope and public locators: docs/GEAR-GUIDE-T7-EVIDENCE.md. A different ID or
changed resource classification stays unresolved. This registry certifies only
hand type, never stats, augment paths, Dual Wield, ownership or suitability.
"""
from dataclasses import dataclass
from types import MappingProxyType


EVIDENCE_REVISION = 'hands.2026-11-05.v19'


@dataclass(frozen=True)
class HandEvidence:
    item_id: int
    name: str
    category: str
    slots: int
    skill: int
    shield_size: int
    hand_type: str
    url: str
    locator: str
    checked_on: str = '2026-11-03'


# Explicit records, not a general skill/category heuristic. Stat discrepancies
# between website and resources do not authorize numerical interpretations.
EVIDENCE = (
    HandEvidence(22040, 'Daybreak', 'Weapon', 3, 11, 0, 'one_handed',
                 'https://www.ffxiah.com/item/22040/daybreak', 'Main; Clubs; Club skill'),
    HandEvidence(27645, 'Genmei Shield', 'Armor', 2, 0, 1, 'shield',
                 'https://www.ffxiah.com/item/27645/genmei-shield', 'Sub; Shields; Shield skill'),
    HandEvidence(22100, "Mpaca's Staff", 'Weapon', 1, 12, 0, 'two_handed',
                 'https://www.ffxiah.com/item/22100/mpacas-staff', 'Main; Staves; Staff skill'),
    HandEvidence(22218, 'Khonsu', 'Weapon', 2, 0, 0, 'grip',
                 'https://www.ffxiah.com/item/22218/khonsu', 'Sub; Weapons > Ammo&Misc > Grips'),
    HandEvidence(22064, 'Hvergelmir', 'Weapon', 1, 12, 0, 'two_handed',
                 'https://www.ffxiah.com/item/22064/hvergelmir', 'Exact ID 22064; Main; Staff skill'),
    HandEvidence(27635, "Chanter's Shield", 'Armor', 2, 0, 2, 'shield',
                 'https://www.ffxiah.com/item/27635/chanters-shield', 'Sub; Shields; Shield skill'),
    HandEvidence(18633, 'Chatoyant Staff', 'Weapon', 1, 12, 0, 'two_handed',
                 'https://www.ffxiah.com/item/18633/chatoyant-staff', 'Main; Staves; exact ID 18633'),
    HandEvidence(21085, 'Solstice', 'Weapon', 3, 11, 0, 'one_handed',
                 'https://www.ffxiah.com/item/21085/solstice', 'Main; Clubs; Club skill'),
    HandEvidence(20515, 'Godhands', 'Weapon', 1, 1, 0, 'hand_to_hand',
                 'https://www.ffxiah.com/item/20515/godhands', 'Main; Hand to Hand; exact ID 20515'),
    HandEvidence(21527, "Sakpata's Fists", 'Weapon', 1, 1, 0, 'hand_to_hand',
                 'https://www.ffxiah.com/item/21527/sakpatas-fists', 'Main; Hand to Hand'),
    HandEvidence(17077, 'Beneficus', 'Weapon', 3, 11, 0, 'one_handed',
                 'https://www.bg-wiki.com/index.php?title=Beneficus&oldid=627412', 'Weapon Information: Club; exact local ID 17077'),
    HandEvidence(21111, 'Bolelabunga', 'Weapon', 3, 11, 0, 'one_handed',
                 'https://www.bg-wiki.com/index.php?title=Bolelabunga&oldid=592101', 'Weapon Information: Club; exact local ID 21111'),
    HandEvidence(26419, 'Ammurapi Shield', 'Armor', 2, 0, 1, 'shield',
                 'https://www.bg-wiki.com/index.php?title=Ammurapi_Shield&oldid=706776', 'Shield Information: size 1; exact local ID 26419'),
    HandEvidence(18973, 'Yagrush', 'Weapon', 3, 11, 0, 'one_handed',
                 'https://www.bg-wiki.com/index.php?title=Yagrush_(Level_75)&oldid=419933', 'Level 75; Club; exact ID 18973 only, not other Yagrush stages'),
    HandEvidence(22031, 'Maxentius', 'Weapon', 3, 11, 0, 'one_handed',
                 'https://www.bg-wiki.com/index.php?title=Maxentius&oldid=766327', 'Weapon Information: Club; exact ID 22031; main-hand Black Halo context'),
    HandEvidence(21621, 'Naegling', 'Weapon', 3, 3, 0, 'one_handed',
                 'https://www.ffxiah.com/item/21621/naegling', 'Exact ID 21621; Weapons > Swords; Sword skill; RDM eligibility', checked_on='2026-11-04'),
    HandEvidence(20614, 'Pukulatmuj +1', 'Weapon', 3, 3, 0, 'one_handed',
                 'https://www.ffxiah.com/item/20614/pukulatmuj-1', 'Exact ID 20614; Weapons > Swords; Sword skill; RDM eligibility; base effects only', checked_on='2026-11-04'),
    HandEvidence(21637, "Sakpata's Sword", 'Weapon', 3, 3, 0, 'one_handed',
                 'https://www.ffxiah.com/item/21637', 'Exact ID 21637; Weapons > Swords; Sword skill; RDM eligibility; base effects only', checked_on='2026-11-04'),
    HandEvidence(20599, 'Kali', 'Weapon', 3, 2, 0, 'one_handed',
                 'https://www.bg-wiki.com/index.php?title=Kali&oldid=635192', 'Weapon Information: Dagger; exact ID 20599 corroborated by FFXIAH item/20599 and local skill 2; BRD', checked_on='2026-11-04'),
    HandEvidence(20805, 'Perun +1', 'Weapon', 3, 5, 0, 'one_handed',
                 'https://www.ffxiah.com/item/20805/perun-1', 'Exact ID 20805; Main; Weapons > Axes; Axe skill +242; RNG; base checkpoint, no Unity maximum or rank inferred', checked_on='2026-11-04'),
    HandEvidence(20595, 'Malevolence', 'Weapon', 3, 2, 0, 'one_handed',
                 'https://www.ffxiah.com/item/20595/malevolence', 'Exact ID 20595; Main; Weapons > Daggers; Dagger skill +242; RNG; base checkpoint without random augments', checked_on='2026-11-04'),
    HandEvidence(26421, 'Nusku Shield', 'Armor', 2, 0, 2, 'shield',
                 'https://www.ffxiah.com/item/26421/nusku-shield', 'Exact ID 26421; Sub; Armor > Shields; Shield skill +107; RNG; local size 2', checked_on='2026-11-04'),
    HandEvidence(21956, 'Masamune', 'Weapon', 1, 10, 0, 'two_handed',
                 'https://www.ffxiah.com/item/21956', 'Exact ID21956; Main; Great Katana; skill +269; SAM99; DMG308 base afterglow stage, no rank inferred', checked_on='2026-11-04'),
    HandEvidence(21025, 'Dojikiri Yasutsuna', 'Weapon', 1, 10, 0, 'two_handed',
                 'https://www.ffxiah.com/item/21025', 'Exact ID21025; Main; Great Katana; skill +269; SAM99; base stage, no rank inferred', checked_on='2026-11-04'),
    HandEvidence(21883, 'Shining One', 'Weapon', 1, 8, 0, 'two_handed',
                 'https://www.ffxiah.com/item/21883', 'Exact ID21883; Main; Polearm; skill +250; SAM99; Impulse Drive listed', checked_on='2026-11-04'),
    HandEvidence(22212, 'Utu Grip', 'Weapon', 2, 0, 0, 'grip',
                 'https://www.ffxiah.com/item/22212', 'Exact ID22212; Sub; Weapons > Ammo&Misc > Grips; SAM99', checked_on='2026-11-04'),
    HandEvidence(20977, 'Heishi Shorinken', 'Weapon', 3, 9, 0, 'one_handed',
                 'https://www.ffxiah.com/item/20977', 'Exact ID20977; Main; Katana; skill +269; NIN99; DMG159 base Aeonic stage. Explicit usable native Dual Wield context separately required', checked_on='2026-11-04'),
    HandEvidence(21922, 'Gokotai', 'Weapon', 3, 9, 0, 'one_handed',
                 'https://www.ffxiah.com/item/21922', 'Exact ID21922; Main; Katana; skill +250; NIN99; main-hand Blade: Ku grant; local slot-mask3 reviewed for offhand eligibility', checked_on='2026-11-04'),
    HandEvidence(21925, 'Kunimitsu', 'Weapon', 3, 9, 0, 'one_handed',
                 'https://www.ffxiah.com/item/21925', 'Exact ID21925; Main; Katana; skill +248; NIN99; local slot-mask3 reviewed for offhand eligibility; base effects without rank', checked_on='2026-11-04'),
    HandEvidence(21149, 'Espiritus', 'Weapon', 1, 12, 0, 'two_handed',
                 'https://www.ffxiah.com/item/21149', 'Exact ID21149; Main; Staves; Staff skill+242; SMN99; base only, no augment path/rank inferred', checked_on='2026-11-04'),
    HandEvidence(21174, 'Gridarvor', 'Weapon', 1, 12, 0, 'two_handed',
                 'https://www.ffxiah.com/item/21174', 'Exact ID21174; Main; Staves; Staff skill+242; SMN99; base only', checked_on='2026-11-04'),
    HandEvidence(19058, 'Vox Grip', 'Weapon', 2, 0, 0, 'grip',
                 'https://www.ffxiah.com/item/19058', 'Exact ID19058; Sub; Weapons > Ammo&Misc > Grips; SMN eligible', checked_on='2026-11-04'),
    HandEvidence(22041, "Bunzi's Rod", 'Weapon', 3, 11, 0, 'one_handed',
                 'https://www.ffxiah.com/item/22041', 'Exact ID22041; Main; Clubs; Club skill+242; BLU99; local slot-mask3 independently reconciled; base only, no Odyssey rank inferred', checked_on='2026-11-04'),
    HandEvidence(21565, 'Tauret', 'Weapon', 3, 2, 0, 'one_handed',
                 'https://www.ffxiah.com/item/21565', 'Exact ID21565; Main; Daggers; Dagger skill+250; COR99; local slot-mask3 independently reconciled; Evisceration grant/bonus main hand only; usable subjob Dual Wield separately required', checked_on='2026-11-04'),
    HandEvidence(20761, 'Aettir', 'Weapon', 1, 4, 0, 'two_handed',
                 'https://www.ffxiah.com/item/20761/aettir', 'Exact ID20761; Main; Great Swords; Great Sword skill+242; RUN99; base only, no Oboro augment inferred', checked_on='2026-11-04'),
    HandEvidence(21417, 'Refined Grip +1', 'Weapon', 2, 0, 0, 'grip',
                 'https://www.ffxiah.com/item/21417/refined-grip-1', 'Exact ID21417; Sub; Ammo&Misc > Grips; RUN99; no Unity maximum or augment rank inferred', checked_on='2026-11-04'),
    HandEvidence(21694, 'Lionheart', 'Weapon', 1, 4, 0, 'two_handed',
                 'https://www.ffxiah.com/item/21694/lionheart', 'Exact base ID21694; Main; Great Swords; Great Sword skill+269; RUN99; Resolution grant; no alternate augmented identity, rank or aftermath inferred', checked_on='2026-11-04'),
    HandEvidence(28648, 'Priwen', 'Armor', 2, 0, 3, 'shield',
                 'https://www.ffxiah.com/item/28648/priwen', 'Exact ID28648; Sub; Armor > Shields; PLD99; size3 independently corroborated by rendered Community Paladin Guide oldid780215 shield notes. Base only, no Oboro augment or ultimate-shield properties', checked_on='2026-11-04'),
    HandEvidence(20890, 'Anguta', 'Weapon', 1, 7, 0, 'two_handed',
                 'https://www.ffxiah.com/item/20890', 'Exact ID20890; Main; Weapons > Scythes; skill+269; DRK99; base DMG370 Entropy-grant stage only, no rank/aftermath transferred', checked_on='2026-11-04'),
    HandEvidence(21689, 'Montante +1', 'Weapon', 1, 4, 0, 'two_handed',
                 'https://www.ffxiah.com/item/21689', 'Exact ID21689; Main; Weapons > Great Swords; skill+242; DRK99; base DMG299, no Unity maximum or rank inferred', checked_on='2026-11-04'),
    HandEvidence(20843, 'Chango', 'Weapon', 1, 6, 0, 'two_handed',
                 'https://www.ffxiah.com/item/20843', 'Exact ID20843; Main; Weapons > Great Axes; WAR99; skill+269; base DMG336 Upheaval-grant identity only; no alternate rank or aftermath presumed', checked_on='2026-11-05'),
    HandEvidence(27644, 'Blurred Shield +1', 'Armor', 2, 0, 3, 'shield',
                 'https://www.ffxiah.com/item/27644', 'Exact ID27644; Sub; Armor > Shields; WAR99; size3/Su2 independently read on BG Blurred_Shield_%2B1. Public cards include DRK while local jobs386 excludes DRK; WAR overlap only selected. No other job eligibility inferred', checked_on='2026-11-05'),
    HandEvidence(21567, "Gleti's Knife", 'Weapon', 3, 2, 0, 'one_handed',
                 'https://www.ffxiah.com/item/21567', 'Exact ID21567; Daggers; THF99; base DMG133 Delay200 skill255. Offhand in rendered retail Community Thief Guide781560 corroborates local slotmask3. No R15/R20/R30 or aftermath inherited', checked_on='2026-11-05'),
    HandEvidence(21730, 'Spalirisos', 'Weapon', 3, 5, 0, 'one_handed',
                 'https://www.bg-wiki.com/ffxi/Spalirisos_(Level_119_III)', 'Exact ID21730 (BG page FFXIAH link 21730, rev692670); Level 119 III Prime; Axe skill; BST99; DMG218 Delay280. Main/sub slotmask3; Ultimate pet/Blitz lines main-hand only. No other stage inferred', checked_on='2026-11-05'),
    HandEvidence(21723, "Ikenga's Axe", 'Weapon', 3, 5, 0, 'one_handed',
                 'https://www.bg-wiki.com/ffxi/Ikenga%27s_Axe', 'Exact ID21723 (BG rev671185); Axe skill; WAR/BST99; DMG192 Delay288; offhand in BG All Jobs BST grids rev772439. No Odyssey rank inherited', checked_on='2026-11-05'),
    HandEvidence(20793, 'Aymur', 'Weapon', 3, 5, 0, 'one_handed',
                 'https://www.bg-wiki.com/ffxi/Aymur_(Level_119_II)', 'Exact ID20793 (BG rev565071); Level 119 II Mythic with Afterglow; Axe skill; BST99; DMG155 Delay312. Mythic pet TP bonus is main-hand only (BG Ready709840, Dual Wield753673). Not 20792/21751', checked_on='2026-11-05'),
    HandEvidence(21738, 'Telopanos Axe', 'Weapon', 3, 5, 0, 'one_handed',
                 'https://www.bg-wiki.com/ffxi/Telopanos_Axe', 'Exact ID21738 (BG rev768660); Axe skill; BST99; DMG181 Delay268; pet lines printed "Main hand:". No Rank 23/30 augment inherited', checked_on='2026-11-05'),
    HandEvidence(26488, 'Diamond Aspis', 'Armor', 2, 0, 2, 'shield',
                 'https://www.bg-wiki.com/ffxi/Diamond_Aspis', 'Exact ID26488 (BG rev770015); Shields, size 2; WAR/WHM/RDM/THF/PLD/BST99. Sub only', checked_on='2026-11-05'),
    HandEvidence(20511, 'Kenkonken', 'Weapon', 1, 1, 0, 'hand_to_hand',
                 'https://www.bg-wiki.com/ffxi/Kenkonken_(Level_119_III)', 'Exact ID20511 (BG page FFXIAH link 20511, rev778097); Kenkonken iLevel 119 III Mythic; Hand-to-Hand skill; PUP99; DMG144 Delay+79; main-only slotmask1, sub empty. Node 426 ID 18988 is the level-75 stage, not inferred', checked_on='2026-11-05'),
    HandEvidence(21526, 'Xiucoatl', 'Weapon', 1, 1, 0, 'hand_to_hand',
                 'https://www.bg-wiki.com/ffxi/Xiucoatl', 'Exact ID21526 (BG rev627527); Hand-to-Hand skill; PUP99; DMG192 Delay+121; Automaton accuracy lines; main-only slotmask1. No path augment inherited', checked_on='2026-11-05'),
    HandEvidence(20535, 'Ohtas', 'Weapon', 1, 1, 0, 'hand_to_hand',
                 'https://www.bg-wiki.com/ffxi/Ohtas', 'Exact ID20535 (BG rev582433); Hand-to-Hand skill; PUP99; DMG107 Delay+84; Automaton Refresh/Regain; main-only slotmask1', checked_on='2026-11-05'),
    HandEvidence(20542, "Gnafron's Adargas", 'Weapon', 1, 1, 0, 'hand_to_hand',
                 'https://www.bg-wiki.com/ffxi/Gnafron%27s_Adargas', 'Exact ID20542 (BG rev658748); Hand-to-Hand skill; PUP99; DMG50 Delay+54; Automaton max HP/MP and skill effects; main-only slotmask1', checked_on='2026-11-05'),
    HandEvidence(20516, 'Denouements', 'Weapon', 1, 1, 0, 'hand_to_hand',
                 'https://www.bg-wiki.com/ffxi/Denouements', 'Exact ID20516 (BG rev586896); Hand-to-Hand skill; MNK/PUP99; DMG165 Delay+126; Automaton Regen/Refresh+4; main-only slotmask1', checked_on='2026-11-05'),
    HandEvidence(20584, 'Terpsichore', 'Weapon', 3, 2, 0, 'one_handed',
                 'https://www.bg-wiki.com/ffxi/Terpsichore_(Level_119_III)', 'Exact ID20584 (BG page FFXIAH link 20584, rev700774); Terpsichore iLevel 119 III Mythic; Dagger skill; DNC99; DMG128 Delay205; slotmask3. Pyrrhic Kleos/Finishing Move bonus are main-hand properties; node 373 IDs 18969 (Lv75) not inferred. Usable Dual Wield separately required', checked_on='2026-11-05'),
    HandEvidence(20587, 'Twashtar', 'Weapon', 3, 2, 0, 'one_handed',
                 'https://www.bg-wiki.com/ffxi/Twashtar_(Level_119_III)', 'Exact ID20587 (BG page FFXIAH link 20587, rev713481); Twashtar iLevel 119 III Empyrean; Dagger skill; THF/BRD/DNC99; DMG124 Delay176; slotmask3. Node 373 ID 19398 is the level-80 stage, not inferred. Usable Dual Wield separately required', checked_on='2026-11-05'),
)
_BY_ID = MappingProxyType({row.item_id: row for row in EVIDENCE})


def hand_evidence(item):
    evidence = _BY_ID.get(item.id)
    if evidence and (item.en, item.category, item.slots, item.skill, item.shield_size) == (
            evidence.name, evidence.category, evidence.slots, evidence.skill, evidence.shield_size):
        return evidence
    return None


def hand_type(item):
    evidence = hand_evidence(item)
    return evidence.hand_type if evidence else None


def hand_types(items):
    return MappingProxyType({item_id: kind for item_id, item in items.items()
                             if (kind := hand_type(item)) is not None})
