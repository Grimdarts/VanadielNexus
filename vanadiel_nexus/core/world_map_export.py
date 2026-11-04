"""Standalone single-file HTML/SVG version of the World Map (the "Open in Browser" button).

The page embeds the same graph and coordinates the app uses. Its route finder (ROUTE_JS) is a line-for-line
port of core.world_map.find_route; tests/core/test_world_map.py runs both on the same zone pairs with Node
(when installed) so the two can't quietly drift apart.
"""
from __future__ import annotations

import json
import os

ROUTE_JS = r"""
const HP_WARP_COST = 25, SG_WARP_COST = 30, WARP_RING_COST = 35, OTHER_REGION_TIEBREAK = 1, HUB_ID = 246;

function edgeWeight(fromZone, e) {
  if (e.kind === 'transport') return 180;
  if (e.kind === 'gated') return 120;
  if (e.kind === 'warp' || e.kind === 'endgame_entry') return 40;
  return fromZone.can_mount ? 60 : 110;
}

function positionIn(e, zoneId) { return zoneId === e.from_id ? e.exit_pos : e.entry_pos; }

function stepLabel(fromZone, toZone, e) {
  const pos = positionIn(e, fromZone.id);
  const sfx = pos ? ' ' + pos : '';
  if (e.kind === 'transport') return 'Board' + (sfx || ' transport') + ' → ' + toZone.name;
  if (e.kind === 'gated') return 'Pass gate' + sfx + ' → ' + toZone.name;
  if (e.kind === 'endgame_entry') return 'Enter' + sfx + ' → ' + toZone.name;
  if (e.kind === 'warp') return 'Teleport' + sfx + ' → ' + toZone.name;
  return (fromZone.can_mount ? 'Ride' : 'Walk') + sfx + ' → ' + toZone.name;
}

// Binary heap of [dist, id]; ties broken by insertion order like Python's heapq on (dist, id).
class Heap {
  constructor() { this.a = []; }
  get size() { return this.a.length; }
  less(i, j) { const x = this.a[i], y = this.a[j]; return x[0] < y[0] || (x[0] === y[0] && x[1] < y[1]); }
  push(v) { const a = this.a; a.push(v); let i = a.length - 1;
    while (i > 0) { const p = (i - 1) >> 1; if (!this.less(i, p)) break; [a[i], a[p]] = [a[p], a[i]]; i = p; } }
  pop() { const a = this.a; const top = a[0]; const last = a.pop();
    if (a.length) { a[0] = last; let i = 0;
      for (;;) { const l = 2 * i + 1, r = l + 1; let m = i;
        if (l < a.length && this.less(l, m)) m = l; if (r < a.length && this.less(r, m)) m = r;
        if (m === i) break; [a[i], a[m]] = [a[m], a[i]]; i = m; } }
    return top; }
}

function buildAdjacency(data) {
  const adj = new Map(data.zones.map(z => [z.id, []]));
  for (const e of data.edges) {
    adj.get(e.from_id).push([e.to_id, e]);
    if (e.bidirectional) adj.get(e.to_id).push([e.from_id, e]);
  }
  return adj;
}

function findRoute(data, zones, adj, startId, targetId, useHp, useSg) {
  const s = zones.get(startId), t = zones.get(targetId);
  if (!s || !t) return null;
  if (startId === targetId) return { steps: [], total_cost: 0 };
  const hpZones = useHp ? data.zones.filter(z => z.homepoints.length > 0) : [];
  const sgZones = useSg ? data.zones.filter(z => z.has_survival_guide) : [];
  const dist = new Map([[startId, 0]]), prev = new Map(), pq = new Heap();
  pq.push([0, startId]);
  const relax = (u, v, d, w, marker) => {
    const nd = d + w;
    if (nd < (dist.has(v) ? dist.get(v) : Infinity)) { dist.set(v, nd); prev.set(v, [u, marker, w]); pq.push([nd, v]); }
  };
  while (pq.size) {
    const [d, u] = pq.pop();
    if (d > (dist.has(u) ? dist.get(u) : Infinity)) continue;
    if (u === targetId) break;
    const uz = zones.get(u);
    if (u !== startId && uz.member_count > 1) continue;
    for (const [v, e] of adj.get(u)) relax(u, v, d, edgeWeight(uz, e), e);
    if (useHp && uz.homepoints.length) for (const z of hpZones) if (z.id !== u)
      relax(u, z.id, d, HP_WARP_COST + (z.region_id === uz.region_id ? 0 : OTHER_REGION_TIEBREAK), 'homepoint');
    if (useSg && uz.has_survival_guide) for (const z of sgZones) if (z.id !== u)
      relax(u, z.id, d, SG_WARP_COST + (z.region_id === uz.region_id ? 0 : OTHER_REGION_TIEBREAK), 'survival_guide');
    if (u === startId && (useHp || useSg) && !uz.homepoints.length && !uz.has_survival_guide && zones.has(HUB_ID))
      relax(u, HUB_ID, d, WARP_RING_COST, 'warp_ring');
  }
  if (!dist.has(targetId)) return null;
  const chain = [];
  for (let cur = targetId; cur !== startId;) { const [p, m, w] = prev.get(cur); chain.push([p, cur, m, w]); cur = p; }
  chain.reverse();
  const steps = chain.map(([p, c, m, w]) => {
    const dz = zones.get(c);
    if (m === 'homepoint') return { from_id: p, to_id: c, kind: 'homepoint', label: 'Home Point warp → ' + dz.homepoints[0], requirement: '', cost: w };
    if (m === 'survival_guide') return { from_id: p, to_id: c, kind: 'survival_guide', label: 'Survival Guide warp → ' + dz.name, requirement: '', cost: w };
    if (m === 'warp_ring') return { from_id: p, to_id: c, kind: 'warp_ring', label: 'Warp Ring / Warp → ' + dz.name, requirement: '', cost: w };
    return { from_id: p, to_id: c, kind: m.kind, label: stepLabel(zones.get(p), dz, m), requirement: m.requirement, cost: w };
  });
  return { steps, total_cost: dist.get(targetId) };
}
"""


def serialize_graph(graph, *, current_zone_id=None, selected_zone_id=None, default_hub=246) -> dict:
    return {
        "canvas": {"width": graph.canvas_width, "height": graph.canvas_height},
        "current_zone_id": current_zone_id,
        "selected_zone_id": selected_zone_id or current_zone_id or default_hub,
        "regions": [{"id": r.id, "name": r.name, "era": r.era, "cx": r.cx, "cy": r.cy, "rx": r.rx, "ry": r.ry}
                    for r in graph.regions.values()],
        "zones": [{
            "id": z.id, "member_count": len(z.member_zone_ids), "name": z.name, "short_name": z.short_name,
            "aliases": z.aliases, "region_id": z.region_id, "era": z.era, "kind": z.kind, "x": z.x, "y": z.y,
            "can_mount": z.can_mount, "homepoints": z.homepoints, "has_survival_guide": z.has_survival_guide,
            "bgwiki_url": z.bgwiki_url, "notes": z.notes,
        } for z in sorted(graph.zones.values(), key=lambda item: item.id)],
        "edges": [{
            "from_id": e.from_id, "to_id": e.to_id, "bidirectional": e.bidirectional, "kind": e.kind,
            "exit_pos": e.exit_pos, "entry_pos": e.entry_pos, "requirement": e.requirement,
        } for e in graph.edges],
    }


def safe_json(data: dict) -> str:
    """JSON that can sit inside a <script> element."""
    return json.dumps(data, ensure_ascii=False).replace("</", "<\\/").replace("<!--", "<\\!--")


PAGE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Vana'diel Nexus — World Map</title>
<style>
  :root { --bg:#0B1020; --surface:#121A2E; --surface2:#18223A; --border:#26324D; --text:#E6EAF2;
          --muted:#9AA6BF; --accent:#22D3EE; --gold:#E0B04A; --warn:#F59E0B; --ok:#34D399; }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: var(--bg); color: var(--text); font: 14px "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif;
         height: 100vh; display: flex; flex-direction: column; overflow: hidden; }
  header { background: var(--surface); border-bottom: 1px solid var(--border); padding: 10px 16px;
           display: flex; flex-direction: column; gap: 8px; }
  .row { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
  h1 { font: 600 20px Cinzel, Cambria, Georgia, serif; color: var(--gold); margin-right: 8px; }
  input[type=search], select { background: var(--surface2); color: var(--text); border: 1px solid var(--border);
         border-radius: 6px; padding: 6px 10px; font-size: 14px; }
  input[type=search] { flex: 1; min-width: 220px; max-width: 520px; }
  button { font: inherit; cursor: pointer; }
  .pill { background: var(--surface2); color: var(--muted); border: 1px solid var(--border); border-radius: 999px;
          padding: 5px 12px; font-size: 13px; }
  .pill.active { background: rgba(34,211,238,.16); color: var(--accent); border-color: var(--accent); font-weight: 600; }
  .ghost { background: transparent; color: var(--muted); border: 1px solid var(--border); border-radius: 6px; padding: 5px 12px; }
  .ghost:hover, .pill:hover { border-color: var(--accent); color: var(--text); }
  .workspace { flex: 1; display: flex; overflow: hidden; }
  .canvas { flex: 1; position: relative; overflow: hidden; cursor: grab; touch-action: none;
            background: radial-gradient(circle at 50% 45%, #111A30 0%, #0B1020 75%); }
  .canvas.dragging { cursor: grabbing; }
  svg { width: 100%; height: 100%; display: block; user-select: none; }
  .hint { position: absolute; left: 12px; bottom: 10px; color: var(--muted); font-size: 12px; pointer-events: none; }
  .zone-label { font-size: 13px; fill: var(--text); pointer-events: none; }
  svg.far .zone-label { display: none; }
  svg.far .zone-label.keep { display: inline; }
  .region-label { font-weight: 600; fill: var(--muted); pointer-events: none; }
  aside { width: 350px; background: var(--surface); border-left: 1px solid var(--border); padding: 16px; overflow-y: auto;
          display: flex; flex-direction: column; gap: 14px; }
  .card { background: var(--surface2); border: 1px solid var(--border); border-radius: 8px; padding: 12px;
          display: flex; flex-direction: column; gap: 8px; }
  .title { font-size: 17px; font-weight: 600; color: var(--gold); }
  .muted { font-size: 12px; color: var(--muted); }
  .badges { display: flex; flex-wrap: wrap; gap: 6px; }
  .badge { font-size: 12px; padding: 3px 8px; border-radius: 999px; border: 1px solid var(--border); color: var(--muted); }
  .badge.hp { color: var(--accent); border-color: rgba(34,211,238,.4); }
  .badge.sg { color: var(--gold); border-color: rgba(224,176,74,.4); }
  .badge.mnt { color: var(--ok); border-color: rgba(52,211,153,.4); }
  a.wiki { text-align: center; background: var(--accent); color: #0B1020; font-weight: 600; text-decoration: none;
           padding: 7px 12px; border-radius: 6px; }
  .rowbtn { background: #101729; border: 1px solid var(--border); border-radius: 6px; padding: 7px 10px; font-size: 13px;
            color: var(--text); text-align: left; }
  .rowbtn:hover, .rowbtn:focus { border-color: var(--accent); outline: none; }
  label.chk { font-size: 13px; display: flex; gap: 6px; align-items: center; }
</style>
</head>
<body>
<header>
  <div class="row">
    <h1>Vana'diel World Map</h1>
    <input type="search" id="search" placeholder="Search a zone (Enter jumps to it)…">
    <button class="ghost" id="wholeMap">Whole map</button>
    <button class="ghost" id="resetView">Reset view</button>
  </div>
  <div class="row" id="eras"></div>
</header>
<div class="workspace">
  <div class="canvas" id="canvas">
    <svg id="svg">
      <defs>
        <marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 1L10 5L0 9z" fill="#9AA6BF"/></marker>
        <marker id="arrowGold" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto"><path d="M0 1L10 5L0 9z" fill="#E0B04A"/></marker>
      </defs>
      <g id="viewport"><g id="halos"></g><g id="edges"></g><g id="arcs"></g><g id="nodes"></g><g id="regionLabels"></g></g>
    </svg>
    <div class="hint">Scroll to zoom · drag to pan · Esc clears</div>
  </div>
  <aside>
    <div class="card">
      <div class="title" id="dName"></div>
      <div class="muted" id="dMeta"></div>
      <div class="badges" id="dBadges"></div>
      <div class="muted" id="dNotes"></div>
      <a class="wiki" id="dWiki" target="_blank" rel="noopener">Open on BG-Wiki ↗</a>
    </div>
    <div class="card">
      <div style="font-weight:600">How do I get here?</div>
      <label class="muted" for="from">From</label>
      <select id="from"></select>
      <label class="chk"><input type="checkbox" id="useHp" checked> Use Home Points</label>
      <label class="chk"><input type="checkbox" id="useSg" checked> Use Survival Guides</label>
      <div id="steps" style="display:flex;flex-direction:column;gap:6px"></div>
    </div>
    <div class="card">
      <div style="font-weight:600">Connected zones</div>
      <div id="neighbors" style="display:flex;flex-direction:column;gap:6px"></div>
    </div>
  </aside>
</div>
<script id="world-map-data" type="application/json">__DATA__</script>
<script>
__ROUTE_JS__
const DATA = JSON.parse(document.getElementById('world-map-data').textContent);
const ZONES = new Map(DATA.zones.map(z => [z.id, z]));
const REGIONS = new Map(DATA.regions.map(r => [r.id, r]));
const ADJ = buildAdjacency(DATA);
const ERA_LABELS = __ERAS__;
const SVGNS = 'http://www.w3.org/2000/svg';
const NODE_W = 152, NODE_H = 32, LABEL_ZOOM = 0.62;
const svg = document.getElementById('svg'), viewport = document.getElementById('viewport');
const canvas = document.getElementById('canvas');
let era = 'all', selected = DATA.selected_zone_id, view = { x: 0, y: 0, k: 1 };
const fromSel = document.getElementById('from');

function el(tag, attrs, parent) {
  const n = document.createElementNS(SVGNS, tag);
  for (const k in attrs) n.setAttribute(k, attrs[k]);
  if (parent) parent.appendChild(n);
  return n;
}

// ---- pan & zoom ----
function applyView() {
  viewport.setAttribute('transform', `translate(${view.x},${view.y}) scale(${view.k})`);
  svg.classList.toggle('far', view.k < LABEL_ZOOM);
  document.querySelectorAll('.region-label').forEach(t => t.setAttribute('font-size', (14 / view.k).toFixed(1)));
}
function zoomAt(px, py, factor) {
  const k = Math.min(3, Math.max(0.08, view.k * factor));
  view.x = px - (px - view.x) * (k / view.k); view.y = py - (py - view.y) * (k / view.k); view.k = k; applyView();
}
function fitBox(minX, minY, maxX, maxY) {
  const w = canvas.clientWidth, h = canvas.clientHeight;
  const k = Math.min((w - 40) / (maxX - minX), (h - 40) / (maxY - minY), 1.2);
  view.k = k; view.x = w / 2 - k * (minX + maxX) / 2; view.y = h / 2 - k * (minY + maxY) / 2; applyView();
}
function wholeMap() {
  const xs = DATA.zones.map(z => z.x), ys = DATA.zones.map(z => z.y);
  fitBox(Math.min(...xs) - 120, Math.min(...ys) - 80, Math.max(...xs) + 120, Math.max(...ys) + 60);
}
function centerOn(id, k) {
  const z = ZONES.get(id); if (!z) return;
  if (k) view.k = k;
  view.x = canvas.clientWidth / 2 - view.k * z.x; view.y = canvas.clientHeight / 2 - view.k * z.y; applyView();
}
canvas.addEventListener('wheel', ev => {
  ev.preventDefault(); const r = canvas.getBoundingClientRect();
  zoomAt(ev.clientX - r.left, ev.clientY - r.top, ev.deltaY < 0 ? 1.15 : 1 / 1.15);
}, { passive: false });
let drag = null;
canvas.addEventListener('pointerdown', ev => { drag = { x: ev.clientX, y: ev.clientY, vx: view.x, vy: view.y, moved: false }; });
window.addEventListener('pointermove', ev => {
  if (!drag) return;
  const dx = ev.clientX - drag.x, dy = ev.clientY - drag.y;
  if (Math.abs(dx) + Math.abs(dy) > 3) { drag.moved = true; canvas.classList.add('dragging'); }
  view.x = drag.vx + dx; view.y = drag.vy + dy; applyView();
});
window.addEventListener('pointerup', () => { setTimeout(() => { drag = null; }, 0); canvas.classList.remove('dragging'); });
document.getElementById('wholeMap').onclick = wholeMap;
document.getElementById('resetView').onclick = () => centerOn(selected, 1);

// ---- static layers ----
function regionBounds(rid) {
  const m = DATA.zones.filter(z => z.region_id === rid);
  if (!m.length) return null;
  return { x1: Math.min(...m.map(z => z.x)) - NODE_W / 2 - 28, x2: Math.max(...m.map(z => z.x)) + NODE_W / 2 + 28,
           y1: Math.min(...m.map(z => z.y)) - NODE_H / 2 - 34, y2: Math.max(...m.map(z => z.y)) + NODE_H / 2 + 24 };
}
function drawStatic() {
  const halos = document.getElementById('halos'), labels = document.getElementById('regionLabels');
  for (const r of DATA.regions) {
    const b = regionBounds(r.id); if (!b) continue;
    el('rect', { x: b.x1, y: b.y1, width: b.x2 - b.x1, height: b.y2 - b.y1, rx: 18, fill: 'rgba(18,26,46,.42)',
                 stroke: '#26324D', 'stroke-dasharray': '6 4' }, halos);
    const t = el('text', { x: (b.x1 + b.x2) / 2, y: b.y1 + 18, 'text-anchor': 'middle', class: 'region-label' }, labels);
    t.textContent = r.name;
  }
}

// ---- dynamic render ----
function eraMatch(z, endgameHubs) {
  if (era === 'all') return true;
  if (era === 'endgame') return z.kind === 'endgame' || endgameHubs.has(z.id);
  return z.era === era;
}
function render() {
  const fromId = Number(fromSel.value);
  const route = findRoute(DATA, ZONES, ADJ, fromId, selected,
                          document.getElementById('useHp').checked, document.getElementById('useSg').checked);
  const steps = route ? route.steps : [];
  const onRoute = new Set([fromId, selected]); steps.forEach(s => { onRoute.add(s.from_id); onRoute.add(s.to_id); });
  const routePairs = new Set(steps.filter(s => !['homepoint', 'survival_guide', 'warp_ring'].includes(s.kind))
                                 .map(s => s.from_id + '>' + s.to_id));
  const q = document.getElementById('search').value.trim().toLowerCase();
  const endgameHubs = new Set();
  if (era === 'endgame') for (const e of DATA.edges) {
    if (ZONES.get(e.from_id).kind === 'endgame') endgameHubs.add(e.to_id);
    if (ZONES.get(e.to_id).kind === 'endgame') endgameHubs.add(e.from_id);
  }
  const active = z => (eraMatch(z, endgameHubs) && (!q || z.name.toLowerCase().includes(q) ||
                       z.aliases.some(a => a.toLowerCase().includes(q)))) || onRoute.has(z.id);

  const edgesG = document.getElementById('edges'); edgesG.innerHTML = '';
  for (const e of DATA.edges) {
    const a = ZONES.get(e.from_id), b = ZONES.get(e.to_id);
    const fwd = routePairs.has(e.from_id + '>' + e.to_id), rev = e.bidirectional && routePairs.has(e.to_id + '>' + e.from_id);
    const hot = fwd || rev, touches = e.from_id === selected || e.to_id === selected;
    if (Math.hypot(b.x - a.x, b.y - a.y) > 700 && !hot && !touches) continue;
    const [p, q2] = rev ? [b, a] : [a, b];
    const len = Math.hypot(q2.x - p.x, q2.y - p.y) || 1;
    const ex = q2.x - (q2.x - p.x) * (NODE_W / 2.4) / len, ey = q2.y - (q2.y - p.y) * (NODE_H / 1.2) / len;
    const color = hot ? '#E0B04A' : e.kind === 'transport' ? '#0EA5C6' : e.kind === 'gated' ? '#F59E0B' : '#3B4B72';
    const line = el('line', { x1: p.x, y1: p.y, x2: (hot || !e.bidirectional) ? ex : q2.x, y2: (hot || !e.bidirectional) ? ey : q2.y,
                              stroke: color, 'stroke-width': hot ? 3 : 1.8 }, edgesG);
    if (e.kind === 'transport') line.setAttribute('stroke-dasharray', '6 4');
    if (e.kind === 'gated') line.setAttribute('stroke-dasharray', '3 3');
    if (hot) line.setAttribute('marker-end', 'url(#arrowGold)');
    else if (!e.bidirectional) line.setAttribute('marker-end', 'url(#arrow)');
    line.setAttribute('opacity', hot || touches ? 1 : (active(a) && active(b) ? 1 : 0.18));
  }

  const arcs = document.getElementById('arcs'); arcs.innerHTML = '';
  for (const s of steps) {
    if (!['homepoint', 'survival_guide', 'warp_ring'].includes(s.kind)) continue;
    const a = ZONES.get(s.from_id), b = ZONES.get(s.to_id);
    el('path', { d: `M${a.x} ${a.y} Q${(a.x + b.x) / 2} ${(a.y + b.y) / 2 - 70} ${b.x} ${b.y}`, fill: 'none',
                 stroke: '#E0B04A', 'stroke-width': 2.6, 'stroke-dasharray': '8 5', 'marker-end': 'url(#arrowGold)' }, arcs);
  }

  const nodesG = document.getElementById('nodes'); nodesG.innerHTML = '';
  for (const z of DATA.zones) {
    const g = el('g', { opacity: active(z) || z.id === selected ? 1 : 0.18, style: 'cursor:pointer' }, nodesG);
    g.addEventListener('click', () => { if (!drag || !drag.moved) select(z.id); });
    const live = z.id === DATA.current_zone_id, isSel = z.id === selected, hot = onRoute.has(z.id);
    const stroke = live ? '#22D3EE' : (isSel || hot) ? '#E0B04A' : z.kind === 'endgame' ? '#E0B04A' : z.kind === 'hub' ? '#9AA6BF' : '#3B4B72';
    const fill = isSel ? '#1E2D4F' : z.kind === 'endgame' ? '#1B192E' : z.kind === 'hub' ? '#16223B' : '#121A2E';
    if (z.kind === 'endgame') {
      const c = 10, l = z.x - NODE_W / 2, r = z.x + NODE_W / 2, t = z.y - NODE_H / 2, bt = z.y + NODE_H / 2;
      el('polygon', { points: `${l + c},${t} ${r - c},${t} ${r},${z.y} ${r - c},${bt} ${l + c},${bt} ${l},${z.y}`,
                      fill, stroke, 'stroke-width': (isSel || hot || live) ? 2.5 : 1.6 }, g);
    } else {
      const rect = el('rect', { x: z.x - NODE_W / 2, y: z.y - NODE_H / 2, width: NODE_W, height: NODE_H,
                                rx: z.kind === 'hub' ? NODE_H / 2 : 6, fill, stroke, 'stroke-width': (isSel || hot || live) ? 2.5 : 1.4 }, g);
      if (z.kind === 'dungeon' && !(isSel || hot || live)) rect.setAttribute('stroke-dasharray', '5 3');
    }
    const t = el('text', { x: z.x, y: z.y + 4.5, 'text-anchor': 'middle',
                           class: 'zone-label' + ((isSel || hot || live) ? ' keep' : '') }, g);
    t.textContent = (live ? '★ ' : z.kind === 'endgame' ? '◆ ' : '') + z.short_name;
    if (live) t.setAttribute('style', 'fill:#22D3EE;font-weight:600');
    const tip = el('title', {}, g); tip.textContent = z.name;
  }
  drawDetails(route);
}

function rowButton(text, onClick) {
  const b = document.createElement('button'); b.className = 'rowbtn'; b.textContent = text; b.onclick = onClick; return b;
}
function drawDetails(route) {
  const z = ZONES.get(selected); if (!z) return;
  document.getElementById('dName').textContent = z.name;
  document.getElementById('dMeta').textContent = `${REGIONS.get(z.region_id)?.name || z.region_id} · ${ERA_LABELS[z.era] || z.era}`;
  document.getElementById('dNotes').textContent = z.notes || '';
  document.getElementById('dWiki').href = z.bgwiki_url;
  const badges = document.getElementById('dBadges'); badges.innerHTML = '';
  const badge = (text, cls) => { const s = document.createElement('span'); s.className = 'badge ' + cls; s.textContent = text; badges.appendChild(s); };
  badge(z.kind[0].toUpperCase() + z.kind.slice(1), '');
  if (z.homepoints.length) badge(`Home Point ×${z.homepoints.length}`, 'hp');
  if (z.has_survival_guide) badge('Survival Guide ✓', 'sg');
  if (z.can_mount) badge('Mount ✓', 'mnt');
  const stepsEl = document.getElementById('steps'); stepsEl.innerHTML = '';
  if (!route) stepsEl.innerHTML = '<div class="muted">No route found between these zones.</div>';
  else if (!route.steps.length) stepsEl.innerHTML = '<div class="muted">You are already in this zone.</div>';
  else route.steps.forEach((s, i) => stepsEl.appendChild(rowButton(
      `${i + 1}. ${s.label}${s.requirement ? ' (' + s.requirement + ')' : ''}`, () => centerOn(s.to_id))));
  const nb = document.getElementById('neighbors'); nb.innerHTML = '';
  const seen = new Set();
  for (const [v, e] of ADJ.get(z.id)) {
    const pos = positionIn(e, z.id), key = v + '|' + pos;
    if (seen.has(key)) continue; seen.add(key);
    const n = ZONES.get(v);
    nb.appendChild(rowButton(`→ ${n.short_name}${pos ? ' · ' + pos : ''}${e.requirement ? ' [' + e.requirement + ']' : ''}`,
                             () => { select(v); centerOn(v); }));
  }
}

function select(id) { selected = id; render(); }

// ---- controls ----
DATA.zones.slice().sort((a, b) => a.name.localeCompare(b.name)).forEach(z => {
  const o = document.createElement('option'); o.value = z.id; o.textContent = z.name; fromSel.appendChild(o);
});
fromSel.value = String(DATA.current_zone_id || HUB_ID);
const erasEl = document.getElementById('eras');
for (const [key, label] of Object.entries(ERA_LABELS)) {
  const b = document.createElement('button'); b.className = 'pill' + (key === 'all' ? ' active' : '');
  b.textContent = label;
  b.onclick = () => { era = key; erasEl.querySelectorAll('.pill').forEach(p => p.classList.toggle('active', p === b)); render(); };
  erasEl.appendChild(b);
}
fromSel.onchange = render;
document.getElementById('useHp').onchange = render;
document.getElementById('useSg').onchange = render;
const search = document.getElementById('search');
search.oninput = render;
search.onkeydown = ev => {
  if (ev.key !== 'Enter') return;
  const q = search.value.trim().toLowerCase(); if (!q) return;
  const hit = DATA.zones.find(z => z.name.toLowerCase() === q || z.aliases.some(a => a.toLowerCase() === q))
           || DATA.zones.find(z => z.name.toLowerCase().startsWith(q))
           || DATA.zones.find(z => z.name.toLowerCase().includes(q) || z.aliases.some(a => a.toLowerCase().includes(q)));
  if (hit) { select(hit.id); centerOn(hit.id, Math.max(view.k, 0.9)); }
};
document.addEventListener('keydown', ev => {
  if (ev.key !== 'Escape') return;
  if (search.value) { search.value = ''; render(); }
  else { selected = Number(fromSel.value); render(); }
});
window.addEventListener('resize', applyView);
drawStatic();
render();
centerOn(selected, 1);
</script>
</body>
</html>
"""


def write_page(data: dict, output_path: str, era_labels: dict[str, str]) -> str:
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    doc = (PAGE.replace("__ROUTE_JS__", ROUTE_JS)
               .replace("__ERAS__", json.dumps(era_labels, ensure_ascii=False))
               .replace("__DATA__", safe_json(data)))
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(doc)
    return output_path
