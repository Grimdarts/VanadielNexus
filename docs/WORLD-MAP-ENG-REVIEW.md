# World Map — `/plan-eng-review` Engineering Review Record

- **Reviewer:** Vesper (GStack `/plan-eng-review` + Independent Outside Voice Subagent `cf6b6821-decf-4184-b840-e5713ef27853`)
- **Authority & Decisions:** Jason (`D1`–`D8`)
- **Date:** 2026-11-04
- **Target Plan:** [docs/designs/interactive-world-map.md](designs/interactive-world-map.md)
- **Test Plan Artifact:** `C:\Users\Jason\.gstack\projects\Grimdarts-VanadielNexus\Jason-codex-sets-copy-fixes-review-eng-review-test-plan-20261104.md`

---

## Step 0: Scope Challenge & Existing Code Reuse

| Sub-Problem | Existing Code in Repo | Action |
|---|---|---|
| Crash-safe JSON persistence (temp + `.bak` swap) | `vanadiel_nexus/core/jsonfile.py:7-27` (`read_json`, `write_json`) | Reuse for `world_map_layout.json` |
| Bundled resource & writable data paths | `vanadiel_nexus/core/paths.py:18-49` (`resource_path`, `data_dir`) | Reuse for `world_map_data.json` & `ctx.data_dir` |
| BG-Wiki URL generation | `vanadiel_nexus/core/wiki.py:50-71` (`build_wiki_urls`) | Reuse with optional `wiki_slug` override |
| Responsive wrapping filter pill bar | `vanadiel_nexus/ui/widgets.py:25` (`FlowLayout`) | Reuse for Row 2 Era/Endgame filter pills |
| Interactive `QGraphicsView` pan/zoom/drag pattern | `vanadiel_nexus/ui/pages/layout.py:1-120` | Reuse `QGraphicsScene`/`QGraphicsView` architecture |
| Live player zone from Windower UDP | `vanadiel_nexus/resources/VanadielNexus.lua:339` (`zone_name`) & `bridge/udp.py:224` (`state_received`) | Surface via `AppContext.zone_changed = Signal(str)` |
| Frozen build smoke test | `tools/check_frozen.py:53` & `vanadiel_nexus/__main__.py:43-45` | Add `'map'` to required page keys |

---

## Section 1: Architecture Review (`D1`–`D2`)

### Issue 1 (`D1`): `[P2] (confidence: 9/10) vanadiel_nexus/ui/context.py:68-84` — `AppContext` ignores `state["zone_name"]`
- **Finding:** `VanadielNexus.lua:339` sends `"zone_name"` in every `STATE_UPDATE` packet, and `GameBridge._publish()` (`vanadiel_nexus/bridge/udp.py:220-224`) stores `self.state = state` and emits `state_received`. However, `AppContext._on_state()` (`vanadiel_nexus/ui/context.py:68-84`) only reads `main_job` and `inventory`.
- **Decision (`D1` — Option 1A Chosen):** Add `zone_changed = Signal(str)` and `self.zone_name: str = ""` on `AppContext`. In `AppContext._on_state()`, normalize `zone = (state.get("zone_name") or "").strip()` and emit `self.zone_changed.emit(zone)` only when `zone` is non-empty, not `"Unknown"`/`"unknown"`, and `zone != self.zone_name`.

### Issue 2 (`D2`): `[P2] (confidence: 9/10) vanadiel_nexus/ui/pages/layout.py:43` — `ItemIgnoresTransformations` causes text to overflow node boxes at low zoom
- **Finding:** If a `QGraphicsSimpleTextItem` uses `ItemIgnoresTransformations` inside a scene-space node pill/diamond, zooming out to `0.35×` shrinks a `150px` node box to `52.5` screen pixels while the `12px` screen-space label stays `~140` screen pixels wide, spilling outside the node border and colliding with neighbors.
- **Decision (`D2` — Option 2A Chosen):** Render node shapes and labels together in scene coordinates inside custom `NodeItem.paint()` (`14px` scene font, elided to the node rect width with full zone name tooltip on hover), clamp `QGraphicsView` minimum zoom to `0.55×` (`7.7pt` screen floor), and apply `ItemIgnoresTransformations` only to regional header banners (`13px` fixed screen font).

---

## Section 2: Code Quality & DRY Review (`D3`)

### Issue 3 (`D3`): `[P2] (confidence: 9/10) vanadiel_nexus/core/jsonfile.py:1` & `vanadiel_nexus/core/wiki.py:50` — Unify JSON I/O, Wiki URLs, and HTML `<script>` escaping
- **Finding:** `core/world_map.py` should not duplicate atomic JSON persistence or BG-Wiki URL builders, and `export_standalone_html()` must guard against `</script>` termination inside embedded JSON.
- **Decision (`D3` — Option 3A Chosen):**
  1. Reuse `jsonfile.read_json` / `write_json` for `world_map_layout.json`.
  2. Compute BG-Wiki URLs dynamically via `wiki.build_wiki_urls(zone.name, zone.wiki_slug)["bgwiki"]`.
  3. Escape `</` (`<\/`) and `<!--` (`<\!--`) when embedding JSON inside `<script id="world-map-data">` in `export_standalone_html()`.

---

## Section 3: Test Review (`D4`)

### ASCII Test Coverage Diagram

```
CODE PATH / USER FLOW                                      TEST FILE & COVERAGE
═════════════════════════════════════════════════════════  ═══════════════════════════════════════════════
tools/seed_world_map.py
  ├── Parse Windower res/zones.lua & regions.lua           tests/core/test_world_map.py::test_bundled_data_integrity
  ├── Parse & unescape Homepoints/map.lua + 2015+ HPs      tests/core/test_world_map.py::test_homepoints_unescaped
  └── Validate 0 dangling edge IDs & 0 orphan nodes        tests/core/test_world_map.py::test_no_orphan_or_dangling_edges
                                                           tests/core/test_world_map.py::test_single_connected_component

vanadiel_nexus/core/world_map.py
  ├── load_world_map()
  │   ├── Load bundled world_map_data.json                 tests/core/test_world_map.py::test_load_default_graph
  │   ├── Overlay valid user data/world_map_layout.json    tests/core/test_world_map.py::test_load_with_valid_overrides
  │   └── Corrupt / schema-mismatch / NaN override fallbacktests/core/test_world_map.py::test_corrupt_override_fallback
  ├── save_layout_overrides() / reset_layout_overrides()
  │   ├── Atomic write via jsonfile.write_json (.bak)      tests/core/test_world_map.py::test_save_and_reset_overrides
  │   └── Never mutates bundled resources JSON             tests/core/test_world_map.py::test_resources_never_mutated
  ├── search_zones()
  │   ├── Exact ID, name, alias ("sky", "sea"), substring  tests/core/test_world_map.py::test_search_zones_queries
  │   └── Empty / non-matching query                       tests/core/test_world_map.py::test_search_zones_empty
  ├── find_route() (Weighted Dijkstra + Star Hubs)
  │   ├── Same zone (from_id == to_id -> 0 hops)           tests/core/test_world_map.py::test_route_same_zone
  │   ├── Walk-only multi-hop path (HP=False, SG=False)    tests/core/test_world_map.py::test_route_walk_only
  │   ├── Fast-travel shortcut (VIRTUAL_HP_HUB / SG_HUB)   tests/core/test_world_map.py::test_route_fast_travel_hp_sg
  │   ├── No illegal SG-only -> HP-only cross-network warp tests/core/test_world_map.py::test_no_cross_network_warp
  │   ├── One-way drop edge (A->B allowed, B->A blocked)   tests/core/test_world_map.py::test_route_one_way_edge
  │   ├── Endgame instance entry (Jeuno -> Sortie/Omen)    tests/core/test_world_map.py::test_route_to_endgame_zones
  │   └── Unreachable / invalid zone ID -> None            tests/core/test_world_map.py::test_route_unreachable
  └── export_standalone_html()
      ├── Generates self-contained offline HTML + SVG      tests/core/test_world_map.py::test_export_html_self_contained
      └── Escapes "</script>" & reflects layout overrides  tests/core/test_world_map.py::test_export_html_script_escape

vanadiel_nexus/ui/context.py & pages/world_map.py
  ├── AppContext._on_state() -> zone_changed Signal(str)   tests/ui/test_world_map_page.py::test_context_zone_signal
  ├── WorldMapPage.on_shown() lazy scene build             tests/ui/test_world_map_page.py::test_page_lazy_load_on_shown
  ├── Node click -> Detail Panel + BG-Wiki URL + neighbors tests/ui/test_world_map_page.py::test_node_selection_details
  ├── Connected neighbor button click -> navigates node    tests/ui/test_world_map_page.py::test_neighbor_button_navigation
  ├── Era filter tabs -> dims non-matching nodes/edges     tests/ui/test_world_map_page.py::test_era_filter_dimming
  ├── Search input -> filters & focuses matching zone      tests/ui/test_world_map_page.py::test_search_input_focus
  ├── Route Finder UI -> highlights path & Warp Arc        tests/ui/test_world_map_page.py::test_route_finder_ui_highlight
  ├── Live UDP zone -> highlights current player node      tests/ui/test_world_map_page.py::test_live_player_zone_badge
  └── Arrange Layout toggle + drag node + Reset Layout     tests/ui/test_world_map_page.py::test_arrange_mode_drag_reset

tools/check_frozen.py
  └── Verify 'map' in payload['pages'] on --startup-check  tools/check_frozen.py:53
```

- **Decision (`D4` — Option 4A Chosen):** Implement all 16+ core tests in `tests/core/test_world_map.py`, all 9+ UI tests in `tests/ui/test_world_map_page.py`, and add `'map'` to `tools/check_frozen.py:53`.

---

## Section 4: Performance Review (`D5`)

### Issue 4 (`D5`): `[P2] (confidence: 9/10)` — Scene Drag Rebuilds, Disk Flush Frequency, and Virtual Hub Complexity
- **Decision (`D5` — Option 5A Chosen):**
  1. **O(degree) Incremental Edge Geometry Updates:** `NodeItem` stores `self.incident_edges: list[EdgeItem]` and enables `ItemSendsGeometryChanges`. In `itemChange(ItemPositionHasChanged)`, only the 1–6 incident `EdgeItem`s and parent `RegionHaloItem` recompute geometry—never rebuilding the `QGraphicsScene`.
  2. **Debounced Persistence on `mouseReleaseEvent`:** Disk writes via `save_layout_overrides()` occur only when a drag finishes (`mouseReleaseEvent` with `self.pos() != self._drag_start_pos`) or when toggling `Arrange Layout` off.
  3. **O(V + E) Virtual Star-Hub Routing:** `find_route()` uses virtual hub nodes (`O(V)` virtual edges) instead of `O(V²)` pairwise warp edges.

---

## Outside Voice — Independent Plan Challenge (`D6`–`D8`)

Subagent `cf6b6821-decf-4184-b840-e5713ef27853` performed a cold-read adversarial review and surfaced 3 high-signal engineering tension points, all resolved with Jason:

1. **Fast-Travel Network Separation, Hub ID Consistency (`246`), & Canvas Warp Arcs (`D6` — Option 6A Chosen):**
   - Separate `VIRTUAL_HP_HUB` (`-1`) and `VIRTUAL_SG_HUB` (`-2`) so Survival Guide-only zones cannot illegally warp directly to Home Point-only zones.
   - Entry into `VIRTUAL_HP_HUB` strictly checks `len(zone.homepoints) > 0`; entry into `VIRTUAL_SG_HUB` strictly checks `zone.has_survival_guide is True`.
   - Standardize on `246` (`Port Jeuno`) as the default fallback origin and one-time initial `"warp_ring"` hub.
   - Render a transient dashed gold quadratic Bézier `QGraphicsPathItem` arc (`#E0B04A`) with a directional arrowhead whenever an active route takes a non-physical fast-travel hop.
2. **BG-Wiki Consolidated Slugs, `Homepoints/map.lua` Unescaping, & Graph Invariant Tests (`D7` — Option 7A Chosen):**
   - Add optional `wiki_slug: str | None` on `ZoneNode` and pass it as `custom_bg_url` to `wiki.build_wiki_urls(zone.name, zone.wiki_slug)["bgwiki"]` so `[S]` zones (`Southern_San_d'Oria_(S)`) and consolidated endgame nodes (`Category:Sortie`, `Category:Odyssey`) resolve to valid BG-Wiki pages.
   - Unescape Lua backslashes (`\[`, `\]`, `\#`, `\'`) when parsing `Homepoints/map.lua` in `tools/seed_world_map.py` and supplement post-2015 Home Points (`Reisenjima #1–#9`, `Upper Jeuno #4`).
   - Enforce a 100% single-connected-component test from `Port Jeuno` (`246`) and verify `res/zones.lua` completeness against an explicit non-zone exclusion allowlist in `tests/core/test_world_map.py`.
3. **Dynamic Region Halos, 2-Row Responsive Toolbar, Override Validation, & `ctx.data_dir` Exports (`D8` — Option 8A Chosen):**
   - Compute `RegionHaloItem` bounds dynamically from member `NodeItem` positions + `40px` padding (with group-drag only on the region's header banner) so background left-drag panning never accidentally grabs a region ellipse.
   - Split the top toolbar into 2 rows (Row 1: Search + `Arrange Layout` + `Reset Layout` + `Open in Browser ↗`; Row 2: `widgets.FlowLayout` with the 8 Era/Endgame filter pills) so it never overflows at `900px`–`1180px` window widths.
   - Coerce override keys with `int(k)` and validate `math.isfinite(x)` / `math.isfinite(y)` within `-500..4500`.
   - Write standalone HTML exports to `os.path.join(ctx.data_dir, "exports", "vanadiel_world_map.html")`.
