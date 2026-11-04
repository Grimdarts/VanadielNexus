"""World Map graph engine, weighted route finder, layout override persistence, and standalone HTML exporter."""
from __future__ import annotations

import heapq
import math
import os
from dataclasses import dataclass, field

from . import jsonfile, paths, wiki

DEFAULT_HUB_ZONE_ID = 246  # Port Jeuno

ERA_LABELS: dict[str, str] = {
    "all": "All Eras",
    "core_zilart": "Core & Zilart",
    "cop": "CoP",
    "toau": "ToAU",
    "wotg": "WotG [S]",
    "adoulin": "Adoulin",
    "escha_abyssea": "Escha & Abyssea",
    "endgame": "Endgame",
}


@dataclass
class RegionCluster:
    id: str
    name: str
    era: str
    cx: float
    cy: float
    rx: float
    ry: float


@dataclass
class ZoneNode:
    id: int
    member_zone_ids: list[int]
    name: str
    short_name: str
    aliases: list[str]
    region_id: str
    era: str
    kind: str
    x: float
    y: float
    can_mount: bool
    homepoints: list[str] = field(default_factory=list)
    has_survival_guide: bool = False
    wiki_slug: str | None = None
    notes: str = ""
    default_x: float = 0.0
    default_y: float = 0.0

    @property
    def bgwiki_url(self) -> str:
        custom = ""
        if self.wiki_slug:
            if "bg-wiki.com" in self.wiki_slug:
                custom = self.wiki_slug
            else:
                custom = f"https://www.bg-wiki.com/ffxi/{self.wiki_slug}"
        return wiki.build_wiki_urls(self.name, custom)["bgwiki"]


@dataclass
class ZoneEdge:
    from_id: int
    to_id: int
    bidirectional: bool
    kind: str
    exit_pos: str = ""   # where the exit is, in the from_id zone
    requirement: str = ""
    entry_pos: str = ""  # where the same exit is, in the to_id zone
    source: str = ""     # "bg-wiki", "curated" or "unverified"

    def position_in(self, zone_id: int) -> str:
        """The exit's grid position(s) as seen from zone_id."""
        return self.exit_pos if zone_id == self.from_id else self.entry_pos


@dataclass
class RouteStep:
    from_id: int
    to_id: int
    kind: str
    label: str
    requirement: str = ""
    exit_pos: str = ""
    cost: int = 0


@dataclass
class RouteResult:
    start_id: int
    target_id: int
    steps: list[RouteStep]
    total_cost: int


@dataclass
class WorldMapGraph:
    schema_version: int
    canvas_width: int
    canvas_height: int
    regions: dict[str, RegionCluster]
    zones: dict[int, ZoneNode]
    edges: list[ZoneEdge]
    excluded_zone_ids: dict[int, str]
    adjacency: dict[int, list[tuple[int, ZoneEdge]]]
    _name_index: dict[str, int]
    _member_index: dict[int, int]

    def resolve_zone(self, query: str | int | None) -> ZoneNode | None:
        if query is None:
            return None
        if isinstance(query, int):
            zid = self._member_index.get(query, query)
            return self.zones.get(zid)
        s = str(query).strip()
        if not s:
            return None
        if s.isdigit():
            val = int(s)
            zid = self._member_index.get(val, val)
            if zid in self.zones:
                return self.zones[zid]
        low = s.casefold()
        if low in self._name_index:
            return self.zones[self._name_index[low]]
        return None


def default_resource_path() -> str:
    return paths.resource_path("world_map_data.json")


def _validate_override_payload(data) -> bool:
    return (
        isinstance(data, dict)
        and data.get("schema_version") == 1
        and isinstance(data.get("zones"), dict)
    )


def load_world_map(
    resource_path: str | None = None,
    user_override_path: str | None = None,
) -> WorldMapGraph:
    res_path = resource_path or default_resource_path()
    raw = jsonfile.read_json(res_path, validator=lambda d: isinstance(d, dict) and "zones" in d)
    if not isinstance(raw, dict):
        raise ValueError(f"Failed to load world map dataset from {res_path}")

    schema_version = int(raw.get("schema_version", 1))
    canvas = raw.get("canvas") or {}
    canvas_width = int(canvas.get("width", 3600))
    canvas_height = int(canvas.get("height", 2400))

    regions: dict[str, RegionCluster] = {}
    for r in raw.get("regions", []):
        rc = RegionCluster(
            id=str(r["id"]),
            name=str(r["name"]),
            era=str(r["era"]),
            cx=float(r["cx"]),
            cy=float(r["cy"]),
            rx=float(r["rx"]),
            ry=float(r["ry"]),
        )
        regions[rc.id] = rc

    zones: dict[int, ZoneNode] = {}
    name_index: dict[str, int] = {}
    member_index: dict[int, int] = {}

    for z in raw.get("zones", []):
        zid = int(z["id"])
        x_val = float(z["x"])
        y_val = float(z["y"])
        m_ids = [int(m) for m in z.get("member_zone_ids", [zid])]
        node = ZoneNode(
            id=zid,
            member_zone_ids=m_ids,
            name=str(z["name"]),
            short_name=str(z.get("short_name") or z["name"]),
            aliases=[str(a) for a in z.get("aliases", [])],
            region_id=str(z["region_id"]),
            era=str(z["era"]),
            kind=str(z["kind"]),
            x=x_val,
            y=y_val,
            can_mount=bool(z.get("can_mount", False)),
            homepoints=[str(hp) for hp in z.get("homepoints", [])],
            has_survival_guide=bool(z.get("has_survival_guide", False)),
            wiki_slug=z.get("wiki_slug"),
            notes=str(z.get("notes") or ""),
            default_x=x_val,
            default_y=y_val,
        )
        zones[zid] = node
        for m in m_ids:
            member_index[m] = zid
        name_index[node.name.casefold()] = zid
        name_index[node.short_name.casefold()] = zid
        for alias in node.aliases:
            if alias:
                name_index.setdefault(alias.casefold(), zid)

    # Apply user coordinate overrides if present and valid
    if user_override_path and os.path.exists(user_override_path):
        override_data = jsonfile.read_json(user_override_path, validator=_validate_override_payload)
        if isinstance(override_data, dict):
            z_overrides = override_data.get("zones", {})
            for k, pos in z_overrides.items():
                try:
                    zid = int(k)
                    if zid not in zones or not isinstance(pos, dict):
                        continue
                    ox = float(pos["x"])
                    oy = float(pos["y"])
                    limit_x = canvas_width + 1000.0
                    limit_y = canvas_height + 1000.0
                    if (
                        math.isfinite(ox)
                        and math.isfinite(oy)
                        and -500.0 <= ox <= limit_x
                        and -500.0 <= oy <= limit_y
                    ):
                        zones[zid].x = round(ox, 1)
                        zones[zid].y = round(oy, 1)
                except (ValueError, TypeError, KeyError):
                    continue

    edges: list[ZoneEdge] = []
    adjacency: dict[int, list[tuple[int, ZoneEdge]]] = {zid: [] for zid in zones}
    for e in raw.get("edges", []):
        fid = int(e["from_id"])
        tid = int(e["to_id"])
        if fid not in zones or tid not in zones:
            raise ValueError(f"Dangling edge endpoint {fid} -> {tid}")
        edge = ZoneEdge(
            from_id=fid,
            to_id=tid,
            bidirectional=bool(e.get("bidirectional", True)),
            kind=str(e.get("kind", "walk")),
            exit_pos=str(e.get("exit_pos") or ""),
            requirement=str(e.get("requirement") or ""),
            entry_pos=str(e.get("entry_pos") or ""),
            source=str(e.get("source") or ""),
        )
        edges.append(edge)
        adjacency[fid].append((tid, edge))
        if edge.bidirectional:
            adjacency[tid].append((fid, edge))

    excluded_raw = raw.get("excluded_zone_ids") or {}
    excluded = {int(k): str(v) for k, v in excluded_raw.items()}

    recompute_region_bounds(regions, zones)

    return WorldMapGraph(
        schema_version=schema_version,
        canvas_width=canvas_width,
        canvas_height=canvas_height,
        regions=regions,
        zones=zones,
        edges=edges,
        excluded_zone_ids=excluded,
        adjacency=adjacency,
        _name_index=name_index,
        _member_index=member_index,
    )


def recompute_region_bounds(
    regions: dict[str, RegionCluster],
    zones: dict[int, ZoneNode],
) -> None:
    by_region: dict[str, list[ZoneNode]] = {rid: [] for rid in regions}
    for z in zones.values():
        if z.region_id in by_region:
            by_region[z.region_id].append(z)
    for rid, members in by_region.items():
        if not members:
            continue
        reg = regions[rid]
        min_x = min(z.x - 85.0 for z in members)
        max_x = max(z.x + 85.0 for z in members)
        min_y = min(z.y - 24.0 for z in members)
        max_y = max(z.y + 24.0 for z in members)
        reg.cx = round((min_x + max_x) / 2.0, 1)
        reg.cy = round((min_y + max_y) / 2.0, 1)
        reg.rx = round((max_x - min_x) / 2.0 + 36.0, 1)
        reg.ry = round((max_y - min_y) / 2.0 + 34.0, 1)


def save_layout_overrides(graph: WorldMapGraph, user_override_path: str) -> None:
    payload = {
        "schema_version": 1,
        "zones": {
            str(zid): {"x": round(z.x, 1), "y": round(z.y, 1)}
            for zid, z in sorted(graph.zones.items())
            if abs(z.x - z.default_x) > 0.05 or abs(z.y - z.default_y) > 0.05
        },
    }
    jsonfile.write_json(user_override_path, payload)


def reset_layout_overrides(graph: WorldMapGraph, user_override_path: str | None = None) -> None:
    if user_override_path:
        for candidate in (user_override_path, user_override_path + ".bak", user_override_path + ".tmp"):
            try:
                if os.path.exists(candidate):
                    os.remove(candidate)
            except OSError:
                pass
    for z in graph.zones.values():
        z.x = z.default_x
        z.y = z.default_y
    recompute_region_bounds(graph.regions, graph.zones)


def search_zones(graph: WorldMapGraph, query: str) -> list[ZoneNode]:
    q = (query or "").strip()
    if not q:
        return []
    low = q.casefold()

    # Exact ID match first
    if q.isdigit():
        exact = graph.resolve_zone(int(q))
        if exact:
            return [exact]

    scored: list[tuple[int, str, ZoneNode]] = []
    for z in graph.zones.values():
        name_l = z.name.casefold()
        short_l = z.short_name.casefold()
        aliases_l = [a.casefold() for a in z.aliases]
        if low == name_l or low == short_l or low in aliases_l:
            scored.append((0, z.name, z))
        elif name_l.startswith(low) or short_l.startswith(low) or any(a.startswith(low) for a in aliases_l):
            scored.append((1, z.name, z))
        elif low in name_l or low in short_l or any(low in a for a in aliases_l):
            scored.append((2, z.name, z))
    scored.sort(key=lambda item: (item[0], item[1]))
    return [item[2] for item in scored]


def _edge_weight(from_zone: ZoneNode, edge: ZoneEdge) -> int:
    if edge.kind == "transport":
        return 180
    if edge.kind == "gated":
        return 120
    if edge.kind in ("warp", "endgame_entry"):
        return 40
    # Default "walk"
    return 60 if from_zone.can_mount else 110


def _step_label(from_zone: ZoneNode, to_zone: ZoneNode, edge: ZoneEdge) -> str:
    pos = edge.position_in(from_zone.id)
    pos_suffix = f" {pos}" if pos else ""
    if edge.kind == "transport":
        return f"Board{pos_suffix or ' transport'} → {to_zone.name}"
    if edge.kind == "gated":
        return f"Pass gate{pos_suffix} → {to_zone.name}"
    if edge.kind == "endgame_entry":
        return f"Enter{pos_suffix} → {to_zone.name}"
    if edge.kind == "warp":
        return f"Teleport{pos_suffix} → {to_zone.name}"
    verb = "Ride" if from_zone.can_mount else "Walk"
    return f"{verb}{pos_suffix} → {to_zone.name}"


HP_WARP_COST = 25
SG_WARP_COST = 30
WARP_RING_COST = 35
OTHER_REGION_TIEBREAK = 1  # prefer warping within the same town when two warps take equally long


def find_route(
    graph: WorldMapGraph,
    start_zone_id: int,
    target_zone_id: int,
    *,
    allow_fast_travel: bool = True,
    include_gated: bool = True,
    use_hp: bool = True,
    use_sg: bool = True,
) -> RouteResult | None:
    """Weighted Dijkstra over walking/portal edges plus Home Point and Survival Guide warps.

    Home Points only warp to Home Points and Survival Guides only to Survival Guides, so a guide-only zone
    can never jump straight to a crystal-only zone.
    """
    start_node = graph.resolve_zone(start_zone_id)
    target_node = graph.resolve_zone(target_zone_id)
    if start_node is None or target_node is None:
        return None
    s_id = start_node.id
    t_id = target_node.id
    if s_id == t_id:
        return RouteResult(start_id=s_id, target_id=t_id, steps=[], total_cost=0)

    enable_hp = allow_fast_travel and use_hp
    enable_sg = allow_fast_travel and use_sg
    hp_zones = [z for z in graph.zones.values() if z.homepoints] if enable_hp else []
    sg_zones = [z for z in graph.zones.values() if z.has_survival_guide] if enable_sg else []

    inf = 10**9
    dist: dict[int, int] = {s_id: 0}
    prev: dict[int, tuple[int, ZoneEdge | str, int]] = {}
    pq: list[tuple[int, int]] = [(0, s_id)]

    def relax(u: int, v: int, d: int, w: int, marker) -> None:
        nd = d + w
        if nd < dist.get(v, inf):
            dist[v] = nd
            prev[v] = (u, marker, w)
            heapq.heappush(pq, (nd, v))

    while pq:
        d, u = heapq.heappop(pq)
        if d > dist.get(u, inf):
            continue
        if u == t_id:
            break
        u_zone = graph.zones[u]

        # Consolidated instance nodes (Sortie layers, Dynamis [D]...) are destinations, not shortcuts.
        if u != s_id and len(u_zone.member_zone_ids) > 1:
            continue

        for v, edge in graph.adjacency.get(u, []):
            if edge.kind == "gated" and not include_gated:
                continue
            relax(u, v, d, _edge_weight(u_zone, edge), edge)

        if enable_hp and u_zone.homepoints:
            for dest in hp_zones:
                if dest.id != u:
                    tie = 0 if dest.region_id == u_zone.region_id else OTHER_REGION_TIEBREAK
                    relax(u, dest.id, d, HP_WARP_COST + tie, "homepoint")
        if enable_sg and u_zone.has_survival_guide:
            for dest in sg_zones:
                if dest.id != u:
                    tie = 0 if dest.region_id == u_zone.region_id else OTHER_REGION_TIEBREAK
                    relax(u, dest.id, d, SG_WARP_COST + tie, "survival_guide")

        # Warp Ring / Warp spell from a start zone with neither a crystal nor a guide
        if (u == s_id and (enable_hp or enable_sg) and not u_zone.homepoints
                and not u_zone.has_survival_guide and DEFAULT_HUB_ZONE_ID in graph.zones):
            relax(u, DEFAULT_HUB_ZONE_ID, d, WARP_RING_COST, "warp_ring")

    if t_id not in dist:
        return None

    chain: list[tuple[int, int, ZoneEdge | str, int]] = []
    curr = t_id
    while curr != s_id:
        p_id, marker, step_cost = prev[curr]
        chain.append((p_id, curr, marker, step_cost))
        curr = p_id
    chain.reverse()

    steps: list[RouteStep] = []
    for p_id, c_id, marker, step_cost in chain:
        dest = graph.zones[c_id]
        if marker == "homepoint":
            steps.append(RouteStep(p_id, c_id, "homepoint", f"Home Point warp → {dest.homepoints[0]}",
                                   exit_pos="Home Point crystal", cost=step_cost))
        elif marker == "survival_guide":
            steps.append(RouteStep(p_id, c_id, "survival_guide", f"Survival Guide warp → {dest.name}",
                                   exit_pos="Survival Guide", cost=step_cost))
        elif marker == "warp_ring":
            steps.append(RouteStep(p_id, c_id, "warp_ring", f"Warp Ring / Warp → {dest.name}",
                                   exit_pos="Warp Ring", cost=step_cost))
        else:
            edge = marker
            steps.append(RouteStep(p_id, c_id, edge.kind, _step_label(graph.zones[p_id], dest, edge),
                                   requirement=edge.requirement, exit_pos=edge.position_in(p_id),
                                   cost=step_cost))
    return RouteResult(start_id=s_id, target_id=t_id, steps=steps, total_cost=dist[t_id])


def export_standalone_html(
    graph: WorldMapGraph,
    output_path: str,
    *,
    current_zone_id: int | None = None,
    selected_zone_id: int | None = None,
    active_route: RouteResult | None = None,
) -> str:
    """Write the self-contained browser map (see core/world_map_export.py)."""
    from . import world_map_export

    recompute_region_bounds(graph.regions, graph.zones)
    data = world_map_export.serialize_graph(graph, current_zone_id=current_zone_id,
                                            selected_zone_id=selected_zone_id, default_hub=DEFAULT_HUB_ZONE_ID)
    return world_map_export.write_page(data, output_path, ERA_LABELS)
