"""Attach Studio **Effects/Mask** nodes to the render, from the source graph.

The Effects node stores its effect specs + target node ids in its props; the
graph is sent as `source_graph` on every render. Here (backend) we read those
nodes and attach the effects either to the whole render (`post_effects`) or to
the specific layers (regions) that the targeted nodes fill — resolved by
matching each video/image region's slot_value back to the graph node that
produced it. Same source-graph-driven pattern as graph_overlays (overlay fix),
so it works on EVERY render branch (UGC, Concatenate, Spatial compose) with no
frontend compiler change.

Effect spec: {"type": <name>, "intensity": 0..100, ...}. See effects_engine.
"""
from __future__ import annotations

from app.services.graph_overlays import _node, _feeder  # reuse graph helpers

GLOBAL_TARGETS = {"all", "render", "global", ""}


def _d(x):
    """SlotValue (pydantic) or dict -> plain dict."""
    if x is None:
        return {}
    if hasattr(x, "model_dump"):
        try:
            return x.model_dump()
        except Exception:
            pass
    if isinstance(x, dict):
        return x
    return getattr(x, "__dict__", {}) or {}


def _region_node_map(template: dict, graph: dict, slot_values: dict) -> dict:
    """{graph_node_id: [region_id, ...]} — which node fills each video/image slot.
    Matched via the slot_value identifier (job_id / filename / seedance image)."""
    nodes = graph.get("nodes", [])

    def props(n):
        return n.get("props") or {}

    m: dict = {}
    for r in template.get("regions", []):
        if r.get("type") not in ("video_slot", "image_slot"):
            continue
        sv = _d(slot_values.get(r.get("slot_name")))
        if not sv:
            continue
        sk = sv.get("source_kind")
        nid = None
        if sk == "job":
            j = sv.get("job_id")
            n = next((n for n in nodes if props(n).get("jobId") == j), None)
            nid = n and n["id"]
        elif sk in ("upload", "file"):
            fn = sv.get("upload_filename") or sv.get("file")
            n = next((n for n in nodes if props(n).get("filename") == fn), None)
            nid = n and n["id"]
        elif sk == "seedance":
            img = (sv.get("seedance") or {}).get("image_filename")
            for n in nodes:
                if n.get("type") == "Seedance":
                    im = _feeder(graph, n["id"], "image")
                    if im and (im.get("props") or {}).get("filename") == img:
                        nid = n["id"]
                        break
        if nid:
            m.setdefault(nid, []).append(r["id"])
    return m


def inject_effects(template: dict, graph: dict, slot_values: dict) -> dict:
    """Return template with Effects-node specs attached to regions / post_effects."""
    if not template or not graph:
        return template
    eff_nodes = [n for n in graph.get("nodes", []) if n.get("type") == "Effects"]
    if not eff_nodes:
        return template

    out = dict(template)
    regions = [dict(r) for r in out.get("regions", [])]
    by_id = {r["id"]: r for r in regions}
    node2regions = _region_node_map(out, graph, slot_values or {})
    post = list(out.get("post_effects") or [])

    for en in eff_nodes:
        P = en.get("props") or {}
        specs = P.get("effects") or []
        if isinstance(specs, dict):
            specs = [specs]
        specs = [s for s in specs if isinstance(s, dict) and s.get("type")]
        if not specs:
            continue
        targets = P.get("targets")
        if isinstance(targets, str):
            targets = [targets]
        # global if no explicit target, or any global keyword present
        if not targets or any(str(t).lower() in GLOBAL_TARGETS for t in targets):
            post += specs
        else:
            for tid in targets:
                for rid in node2regions.get(tid, []):
                    r = by_id.get(rid)
                    if r is not None:
                        r["effects"] = list(r.get("effects") or []) + specs

    out["regions"] = regions
    if post:
        out["post_effects"] = post
    return out
