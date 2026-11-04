"""Unit tests for vanadiel_nexus.core.world_map and bundled world_map_data.json."""
from __future__ import annotations

import json
import os
from collections import deque

import pytest

from vanadiel_nexus.core import world_map


def test_bundled_data_integrity():
    graph = world_map.load_world_map()
    assert graph.schema_version == 1
    assert len(graph.zones) >= 220
    assert len(graph.regions) >= 15
    assert len(graph.edges) >= 300
    for z in graph.zones.values():
        assert z.region_id in graph.regions
        assert z.era in ("core_zilart", "cop", "toau", "wotg", "adoulin", "escha_abyssea")
        assert z.kind in ("hub", "field", "dungeon", "endgame")


def test_homepoints_and_guides_from_bgwiki():
    graph = world_map.load_world_map()
    # BG-Wiki writes [S] zones as "(S)" and drops Riverne's "#"; both must map back to Windower names
    assert graph.zones[80].homepoints == ["Southern San d'Oria [S] #1"]
    assert graph.zones[29].homepoints == ["Riverne - Site #B01 #1"]
    assert graph.zones[246].homepoints == ["Port Jeuno #1", "Port Jeuno #2"]
    # Jeuno's Survival Guide is in Ru'Lude Gardens, not Port Jeuno
    assert graph.zones[243].has_survival_guide is True
    assert graph.zones[246].has_survival_guide is False
    # Reisenjima has no Home Point crystals (the first draft invented nine)
    assert graph.zones[291].homepoints == []
    assert 90 <= sum(z.has_survival_guide for z in graph.zones.values()) <= 110


def _neighbours(graph, name):
    z = graph.resolve_zone(name)
    return {graph.zones[v].name for v, e in graph.adjacency[z.id] if e.source != "unverified"}


def test_connections_match_bgwiki():
    """Spot checks against BG-Wiki's Connected Zone tables (each was wrong in the hand-typed first draft)."""
    graph = world_map.load_world_map()
    assert _neighbours(graph, "Lower Jeuno") == {"Upper Jeuno", "Port Jeuno", "Rolanberry Fields"}
    assert "Northern San d'Oria" in _neighbours(graph, "Port San d'Oria")
    assert "Southern San d'Oria" not in _neighbours(graph, "Port San d'Oria")
    assert _neighbours(graph, "Escha - Zi'Tah") == {"Qufim Island"}
    assert _neighbours(graph, "Escha - Ru'Aun") == {"Misareaux Coast"}
    assert "Yahse Hunting Grounds" not in _neighbours(graph, "Western Adoulin")
    assert {"La Theine Plateau", "Konschtat Highlands", "Tahrongi Canyon"} <= _neighbours(graph, "Reisenjima")
    # The Mhaura ferry docks at Aht Urhgan Whitegate
    assert "Aht Urhgan Whitegate" in _neighbours(graph, "Mhaura")


def test_every_edge_has_a_source():
    graph = world_map.load_world_map()
    sources = {e.source for e in graph.edges}
    assert sources <= {"bg-wiki", "curated", "unverified"}
    assert sum(e.source == "bg-wiki" for e in graph.edges) > 0.9 * len(graph.edges)


def test_dynamis_zones_route_to_their_own_entrance():
    graph = world_map.load_world_map()
    bastok = graph.resolve_zone("Dynamis - Bastok")
    assert bastok is not None and bastok.member_zone_ids == [bastok.id]
    route = world_map.find_route(graph, graph.resolve_zone("Port Windurst").id, bastok.id)
    assert route.steps[-1].from_id == graph.resolve_zone("Bastok Mines").id
    assert route.steps[-1].kind == "endgame_entry"


def test_step_shows_exit_position_in_the_zone_you_are_leaving():
    graph = world_map.load_world_map()
    pj, lj = graph.resolve_zone("Port Jeuno"), graph.resolve_zone("Lower Jeuno")
    edge = next(e for v, e in graph.adjacency[pj.id] if v == lj.id)
    there = world_map.find_route(graph, pj.id, lj.id, allow_fast_travel=False).steps[0]
    back = world_map.find_route(graph, lj.id, pj.id, allow_fast_travel=False).steps[0]
    assert there.exit_pos == edge.position_in(pj.id)
    assert back.exit_pos == edge.position_in(lj.id)
    assert there.exit_pos != back.exit_pos


def test_no_orphan_or_dangling_edges():
    graph = world_map.load_world_map()
    connected_ids: set[int] = set()
    for e in graph.edges:
        assert e.from_id in graph.zones
        assert e.to_id in graph.zones
        connected_ids.add(e.from_id)
        connected_ids.add(e.to_id)
    assert connected_ids == set(graph.zones.keys())


def test_single_connected_component():
    graph = world_map.load_world_map()
    visited = {246}
    queue = deque([246])
    while queue:
        curr = queue.popleft()
        for nxt, _ in graph.adjacency[curr]:
            if nxt not in visited:
                visited.add(nxt)
                queue.append(nxt)
    assert visited == set(graph.zones.keys())


def test_zero_node_box_overlaps_at_1x():
    graph = world_map.load_world_map()
    zones = list(graph.zones.values())
    for i in range(len(zones)):
        for j in range(i + 1, len(zones)):
            a, b = zones[i], zones[j]
            assert not (abs(a.x - b.x) < 164.0 and abs(a.y - b.y) < 41.0), (
                f"Overlap between {a.name} and {b.name}"
            )


def test_load_with_valid_overrides(tmp_path):
    override_file = tmp_path / "world_map_layout.json"
    override_file.write_text(
        json.dumps({"schema_version": 1, "zones": {"246": {"x": 1234.5, "y": 678.9}}}),
        encoding="utf-8",
    )
    graph = world_map.load_world_map(user_override_path=str(override_file))
    assert graph.zones[246].x == 1234.5
    assert graph.zones[246].y == 678.9
    assert graph.zones[246].default_x != 1234.5


def test_corrupt_override_fallback(tmp_path):
    override_file = tmp_path / "world_map_layout.json"
    override_file.write_text("{not valid json", encoding="utf-8")
    graph = world_map.load_world_map(user_override_path=str(override_file))
    assert graph.zones[246].x == graph.zones[246].default_x

    # Out-of-range coordinates ignored
    override_file.write_text(
        json.dumps({"schema_version": 1, "zones": {"246": {"x": 999999.0, "y": -99999.0}}}),
        encoding="utf-8",
    )
    graph2 = world_map.load_world_map(user_override_path=str(override_file))
    assert graph2.zones[246].x == graph2.zones[246].default_x


def test_save_and_reset_overrides(tmp_path):
    override_file = tmp_path / "world_map_layout.json"
    graph = world_map.load_world_map(user_override_path=str(override_file))
    orig_x, orig_y = graph.zones[246].default_x, graph.zones[246].default_y
    graph.zones[246].x = orig_x + 150.0
    graph.zones[246].y = orig_y - 80.0
    world_map.save_layout_overrides(graph, str(override_file))
    assert override_file.exists()

    reloaded = world_map.load_world_map(user_override_path=str(override_file))
    assert reloaded.zones[246].x == round(orig_x + 150.0, 1)

    world_map.reset_layout_overrides(reloaded, str(override_file))
    assert not override_file.exists()
    assert reloaded.zones[246].x == orig_x


def test_resources_never_mutated(tmp_path):
    res_path = world_map.default_resource_path()
    before_mtime = os.path.getmtime(res_path)
    override_file = tmp_path / "world_map_layout.json"
    graph = world_map.load_world_map(user_override_path=str(override_file))
    graph.zones[230].x += 50.0
    world_map.save_layout_overrides(graph, str(override_file))
    assert os.path.getmtime(res_path) == before_mtime


def test_search_zones_queries():
    graph = world_map.load_world_map()
    assert world_map.search_zones(graph, "246")[0].id == 246
    assert world_map.search_zones(graph, "Sortie")[0].id == 275
    assert world_map.search_zones(graph, "Outer Ra'Kaznar [U2]")[0].id == 275
    assert world_map.search_zones(graph, "sky")[0].id == 130
    assert world_map.search_zones(graph, "sea")[0].id == 33


def test_search_zones_empty():
    graph = world_map.load_world_map()
    assert world_map.search_zones(graph, "") == []
    assert world_map.search_zones(graph, "   ") == []
    assert world_map.search_zones(graph, "zzzz_nonexistent_zone") == []


def test_route_same_zone():
    graph = world_map.load_world_map()
    route = world_map.find_route(graph, 246, 246)
    assert route is not None
    assert route.total_cost == 0
    assert route.steps == []


def test_route_walk_only():
    graph = world_map.load_world_map()
    # Southern San d'Oria (230) -> Beaucedine Glacier (111) without fast travel
    route = world_map.find_route(graph, 230, 111, allow_fast_travel=False)
    assert route is not None
    assert len(route.steps) >= 3
    assert all(s.kind not in ("homepoint", "survival_guide", "warp_ring") for s in route.steps)
    # Should traverse East Ronfaure (101) -> Ranguemont Pass (166) -> Beaucedine Glacier (111)
    hop_targets = [s.to_id for s in route.steps]
    assert hop_targets[-1] == 111
    assert 166 in hop_targets


def test_route_fast_travel_hp_sg():
    graph = world_map.load_world_map()
    # Port Jeuno (246) -> Kamihr Drifts (267): one Home Point warp
    route_hp = world_map.find_route(graph, 246, 267, allow_fast_travel=True, use_hp=True, use_sg=True)
    assert route_hp is not None
    assert len(route_hp.steps) == 1
    assert route_hp.steps[0].kind == "homepoint"
    assert route_hp.total_cost == world_map.HP_WARP_COST + world_map.OTHER_REGION_TIEBREAK
    # Port Jeuno has no Survival Guide: warp to a crystal in Jeuno's own region first, then take a guide
    route = world_map.find_route(graph, 246, 291)
    assert [s.kind for s in route.steps][:2] == ["homepoint", "survival_guide"]
    assert graph.zones[route.steps[0].to_id].region_id == graph.zones[246].region_id


def test_no_cross_network_warp():
    graph = world_map.load_world_map()
    # Ordelle's Caves (193) has a Survival Guide (has_survival_guide=True) but NO Home Point.
    # Leafallia (281) has a Home Point ("Leafallia 1") but NO Survival Guide.
    assert graph.zones[193].has_survival_guide is True
    assert len(graph.zones[193].homepoints) == 0
    assert len(graph.zones[281].homepoints) > 0
    assert graph.zones[281].has_survival_guide is False

    route = world_map.find_route(graph, 193, 281, allow_fast_travel=True, use_hp=True, use_sg=True)
    assert route is not None
    # Cannot be a single 1-hop warp from 193 directly to 281!
    assert len(route.steps) >= 2


def test_route_one_way_edge():
    graph = world_map.load_world_map()
    # Bostaunieux Oubliette (167) -> West Ronfaure (100) is a 1-way drop
    drop_route = world_map.find_route(graph, 167, 100, allow_fast_travel=False)
    reverse_route = world_map.find_route(graph, 100, 167, allow_fast_travel=False)
    assert drop_route is not None
    assert reverse_route is not None
    assert len(drop_route.steps) == 1
    # Going from West Ronfaure (100) into Bostaunieux Oubliette (167) must go through San d'Oria -> Chateau (3+ hops)
    assert len(reverse_route.steps) >= 3


def test_route_to_endgame_zones():
    graph = world_map.load_world_map()
    # Port Jeuno (246) -> Sortie (275), Odyssey (298), Omen (292)
    for target_id in (275, 298, 292):
        r = world_map.find_route(graph, 246, target_id, allow_fast_travel=True)
        assert r is not None
        assert r.steps[-1].to_id == target_id
        assert r.steps[-1].kind == "endgame_entry"


def test_route_unreachable():
    graph = world_map.load_world_map()
    assert world_map.find_route(graph, 246, 999999) is None
    assert world_map.find_route(graph, 999999, 246) is None


def test_wiki_slug_urls():
    graph = world_map.load_world_map()
    assert graph.zones[275].bgwiki_url == "https://www.bg-wiki.com/ffxi/Category:Sortie"
    assert graph.zones[80].bgwiki_url == "https://www.bg-wiki.com/ffxi/Southern_San_d'Oria_(S)"
    assert graph.zones[246].bgwiki_url == "https://www.bg-wiki.com/ffxi/Port_Jeuno"


def test_export_html_self_contained_and_script_escape(tmp_path):
    graph = world_map.load_world_map()
    graph.zones[246].notes = "Dangerous </script><!-- injection test"
    out_file = tmp_path / "exports" / "vanadiel_world_map.html"
    written = world_map.export_standalone_html(graph, str(out_file), current_zone_id=246, selected_zone_id=275)
    assert os.path.exists(written)
    content = out_file.read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in content
    assert "</script><!--" not in content
    assert "<\\/script><\\!--" in content
    assert 'src="http' not in content


PARITY_PAIRS = [(246, 291), (246, 267), (230, 111), (167, 100), (100, 167), (246, 275), (193, 281), (110, 289)]

PARITY_DRIVER = """
const data = JSON.parse(require('fs').readFileSync(process.argv[2], 'utf8'));
const zones = new Map(data.zones.map(z => [z.id, z]));
const adj = buildAdjacency(data);
const out = JSON.parse(require('fs').readFileSync(process.argv[3], 'utf8')).map(([a, b, hp, sg]) => {
  const r = findRoute(data, zones, adj, a, b, hp, sg);
  return r && { cost: r.total_cost, steps: r.steps.map(s => [s.from_id, s.to_id, s.kind, s.label]) };
});
console.log(JSON.stringify(out));
"""


def test_browser_route_finder_matches_python(tmp_path):
    """The exported page's JavaScript router must give the same answers as find_route."""
    import shutil
    import subprocess

    from vanadiel_nexus.core import world_map_export

    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js not installed; can't run the browser router")
    graph = world_map.load_world_map()
    cases = [[a, b, hp, sg] for a, b in PARITY_PAIRS for hp, sg in ((True, True), (False, False), (True, False))]
    script = tmp_path / "parity.js"
    script.write_text(world_map_export.ROUTE_JS + PARITY_DRIVER, encoding="utf-8")
    data_file = tmp_path / "data.json"
    data_file.write_text(json.dumps(world_map_export.serialize_graph(graph)), encoding="utf-8")
    cases_file = tmp_path / "cases.json"
    cases_file.write_text(json.dumps(cases), encoding="utf-8")
    result = subprocess.run([node, str(script), str(data_file), str(cases_file)],
                            capture_output=True, text=True, encoding="utf-8", check=True)
    js = json.loads(result.stdout)
    for (a, b, hp, sg), got in zip(cases, js):
        r = world_map.find_route(graph, a, b, allow_fast_travel=hp or sg, use_hp=hp, use_sg=sg)
        want = r and {"cost": r.total_cost, "steps": [[s.from_id, s.to_id, s.kind, s.label] for s in r.steps]}
        assert got == want, (a, b, hp, sg)


def test_export_has_pan_zoom_and_reset():
    from vanadiel_nexus.core import world_map_export

    page = world_map_export.PAGE
    assert "addEventListener('wheel'" in page
    assert "pointerdown" in page
    assert "getElementById('resetView').onclick" in page
