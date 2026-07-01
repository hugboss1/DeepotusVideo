"""Studio overlay recovery from the source graph.

Bug: only the Spatial-compose render path (frontend dzCompose) collected the
TextOverlay / Ticker / Separator nodes wired to the Render node's `overlay`
port. The UGC branch (tpl_studio_ugc), the Concatenate branch and the Animation
branch built their base output WITHOUT those overlays, so a text overlay added
in Studio never appeared in the final render.

Every Studio render request carries the full `source_graph`. This module reads
that graph and rebuilds the overlay regions/elements in the BACKEND, so overlays
are applied uniformly for ANY upstream node chain — not just Spatial compose.
Region ids match the frontend scheme ("ov_<id>" / "ovb_<id>") so paths that
already injected them (Spatial compose) are not duplicated.
"""
from __future__ import annotations

OVERLAY_TYPES = ("TextOverlay", "Ticker", "Separator")


def _node(graph: dict, nid):
    for n in graph.get("nodes", []):
        if n.get("id") == nid:
            return n
    return None


def _feeder(graph: dict, to_id, to_port):
    """The node whose output is wired into <to_id>.<to_port> (mirrors frontend Wt)."""
    for e in graph.get("edges", []):
        if e.get("to") == to_id and e.get("toPort") == to_port:
            return _node(graph, e.get("from"))
    return None


def _reaches(graph: dict, a, b) -> bool:
    """True if node `a` can reach node `b` following edge direction."""
    seen, stack = set(), [a]
    edges = graph.get("edges", [])
    while stack:
        x = stack.pop()
        if x == b:
            return True
        if x in seen:
            continue
        seen.add(x)
        for e in edges:
            if e.get("from") == x:
                stack.append(e.get("to"))
    return False


def _overlay_nodes(graph: dict):
    """Overlay nodes attached to the Render node: the chain wired into its
    `overlay` port, plus any overlay node upstream of the Render node."""
    render = next((n for n in graph.get("nodes", []) if n.get("type") == "Render"), None)
    if not render:
        return []
    rid = render["id"]
    picked, order = set(), []

    def add(nd):
        if nd and nd.get("id") not in picked and nd.get("type") in OVERLAY_TYPES:
            picked.add(nd["id"]); order.append(nd)

    # 1. chain wired into Render.overlay (overlay -> its `in` -> ...)
    ov = _feeder(graph, rid, "overlay")
    guard = 0
    while ov and ov.get("type") in OVERLAY_TYPES and guard < 24:
        add(ov)
        ov = _feeder(graph, ov["id"], "in")
        guard += 1
    # 2. any other overlay node upstream of Render
    for n in graph.get("nodes", []):
        if n.get("type") in OVERLAY_TYPES and n["id"] not in picked and _reaches(graph, n["id"], rid):
            add(n)
    return order


def overlay_regions(graph: dict, W: int, H: int, start_z: int = 60):
    """Build template regions for the graph's overlay nodes (frontend mapping)."""
    regions, z = [], start_z
    for nd in _overlay_nodes(graph):
        P = nd.get("props") or {}
        t = nd.get("type")
        if t == "TextOverlay":
            y = round(H * (P["y"] / 100 if P.get("y") is not None else 0.72))
            x = round(W * (P["x"] / 100 if P.get("x") is not None else 0.15))
            wdt = round(W * (P["w"] / 100 if P.get("w") is not None else 0.70))
            if P.get("bg"):
                regions.append({"id": "ovb_" + nd["id"], "type": "separator", "x": x, "y": y,
                                "width": wdt, "height": 140, "z_index": z, "color": P["bg"]}); z += 1
            regions.append({"id": "ov_" + nd["id"], "type": "text", "x": x, "y": y,
                            "width": wdt, "height": 140, "z_index": z,
                            "text": P.get("text", "") or "", "size": P.get("size", 64),
                            "color": P.get("color", "#ffffff"),
                            "font": P.get("font", "Space Grotesk"), "align": "center",
                            **({"effect": "pulse"} if P.get("pulse") else {})}); z += 1
        elif t == "Ticker":
            tnode = _feeder(graph, nd["id"], "text")
            txt = ((tnode or {}).get("props", {}).get("value") if tnode else None) or P.get("text", "") or ""
            y = round(H * P["y"] / 100) if P.get("y") is not None else H - 72
            regions.append({"id": "ov_" + nd["id"], "type": "ticker", "x": 0, "y": y,
                            "width": W, "height": 64, "z_index": z, "text": txt,
                            "speed": P.get("speed", 60), "direction": P.get("direction", "left"),
                            "size": 36, "font": P.get("font", "Bebas Neue"),
                            "color": P.get("color", "#00e5ff"),
                            "background_color": P.get("bg", "") or ""}); z += 1
        else:  # Separator
            y = round(H * P["y"] / 100) if P.get("y") is not None else round(H / 2)
            regions.append({"id": "ov_" + nd["id"], "type": "separator", "x": 0, "y": y,
                            "width": W, "height": P.get("thickness", 2), "z_index": z,
                            "color": P.get("color", "#00e5ff")}); z += 1
    return regions


def inject_overlays(template: dict, graph: dict) -> dict:
    """Return `template` with the graph's overlay regions merged in. Regions
    whose id is already present (Spatial-compose path) are left untouched."""
    if not template or not graph:
        return template
    canvas = template.get("canvas") or {}
    W = int(canvas.get("width") or 1080)
    H = int(canvas.get("height") or 1920)
    existing = {r.get("id") for r in template.get("regions", [])}
    extra = [r for r in overlay_regions(graph, W, H) if r["id"] not in existing]
    if not extra:
        return template
    out = dict(template)
    out["regions"] = list(template.get("regions", [])) + extra
    return out


def overlay_elements(graph: dict, W: int, H: int):
    """Overlay nodes as Animation-node elements (for the /api/animate path).
    Text overlays become static full-duration text elements."""
    els = []
    for nd in _overlay_nodes(graph):
        if nd.get("type") != "TextOverlay":
            continue  # ticker/separator are region-only
        P = nd.get("props") or {}
        x = P["x"] if P.get("x") is not None else 15
        y = P["y"] if P.get("y") is not None else 72
        pos = {"x": float(x), "y": float(y), "scale": 1.0, "rotation": 0.0, "opacity": 1.0}
        els.append({
            "type": "text", "text": P.get("text", "") or "",
            "style": {"size": P.get("size", 64), "color": P.get("color", "#ffffff"),
                      "font": P.get("font", "Space Grotesk")},
            "start": 0, "dur": 0.001, "hold": 10_000,
            "from": pos, "to": pos,
        })
    return els
