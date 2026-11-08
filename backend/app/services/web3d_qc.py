# -*- coding: utf-8 -*-
"""t441 (lot M8 « Méthodes », 08/11/2026) — le RAPPORT DE POIDS d'un modèle 3D destiné au web, pour l'agent métier
ARTISTE 3D DE JEU (méthodes little-lights, full-self-flying, small-worlds-real-craft, lamplighter : « chaque modèle
sous un mégaoctet », « des triangles MESURÉS plutôt que lus dans l'annonce du modèle »).

Lecture seule, locale et gratuite : les compteurs viennent des lecteurs déjà éprouvés du dépôt
(`mesh_optimize.glb_stats` : triangles et sommets comptés dans les accesseurs ; `mesh_report.gltf_inventory` :
textures, octets réels, extensions). Le rapport compare au BUDGET donné (taille, triangles) et dit quoi faire :
compresser la géométrie (meshopt / Draco), les textures (WebP / KTX2), réduire la densité (LOD de l'Établi).
"""
from __future__ import annotations

from app.services import briques as BR

BUDGET_MO = 5.0
BUDGET_TRIS = 100_000
COMPRESSIONS_GEOMETRIE = ("EXT_meshopt_compression", "KHR_meshopt_compression", "KHR_draco_mesh_compression")
COMPRESSIONS_TEXTURES = ("EXT_texture_webp", "KHR_texture_basisu")


def rapport(chemin: str, budget_mo: float = BUDGET_MO, budget_tris: int = BUDGET_TRIS) -> dict:
    from app.services import mesh_optimize as MO
    from app.services import mesh_report as MR
    p = BR.confiner(chemin)
    if p.suffix.lower() != ".glb":
        raise ValueError("Le rapport de poids lit un modèle .glb.")
    try:
        bm, bt = float(budget_mo), int(budget_tris)
    except (TypeError, ValueError):
        raise ValueError("Budget invalide.") from None
    if not (0 < bm <= 2000 and 0 < bt <= 50_000_000):
        raise ValueError("Budget invalide.")
    try:
        st = MO.glb_stats(p)
        inv = MR.gltf_inventory(p)
    except Exception as e:  # noqa: BLE001 — un GLB illisible est un refus, pas une trace
        raise ValueError(f"GLB illisible : {str(e)[:200]}") from None
    octets = int(st["bytes"])
    tex = int(inv.get("texture_bytes") or 0)
    ext = set(inv.get("extensions_used") or [])
    geo_comp = sorted(ext & set(COMPRESSIONS_GEOMETRIE))
    tex_comp = sorted(ext & set(COMPRESSIONS_TEXTURES))
    images = inv.get("images") or []
    png = [i for i in images if i.get("mime") == "image/png"]
    conseils = []
    if octets > bm * 1e6:
        conseils.append(f"{round(octets / 1e6, 2)} Mo > budget {bm} Mo")
    if st["tris"] > bt:
        conseils.append(f"{st['tris']} triangles > budget {bt} : réduis la densité (LOD de l'Établi)")
    if not geo_comp and st["tris"] > 5000:
        conseils.append("géométrie non compressée : meshopt (ou Draco) divise souvent la taille par 3 à 10")
    if tex and not tex_comp and tex > 0.3 * octets:
        conseils.append(f"les textures font {round(100 * tex / max(1, octets))} % du fichier : passe-les en WebP ou KTX2")
    if png and not tex_comp:
        conseils.append(f"{len(png)} texture(s) PNG : le WebP pèse souvent 3 à 5 fois moins")
    return {"chemin": str(p.relative_to(BR.racine())).replace("\\", "/"), "octets": octets,
            "mo": round(octets / 1e6, 3), "triangles": st["tris"], "sommets": st["verts"], "maillages": st["meshes"],
            "materiaux": st["materials"], "textures": len(images), "octets_textures": tex,
            "part_textures": round(tex / octets, 3) if octets else 0.0, "animations": inv.get("animations"),
            "squelettes": inv.get("skins"), "compression_geometrie": geo_comp, "compression_textures": tex_comp,
            "budget": {"mo": bm, "triangles": bt},
            "dans_le_budget": octets <= bm * 1e6 and st["tris"] <= bt, "conseils": conseils}
