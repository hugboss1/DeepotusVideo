# -*- coding: utf-8 -*-
"""SV2, étape 1 (14/11/2026) — la FABRIQUE Blender du studio virtuel : lit la recette d'un décor
(backend/app/studiov/livres.json ou un fichier .json) et bâtit dans Blender, SANS FENÊTRE, la coque du studio —
pièce (sol, murs, plafond) aux matières PBR, lumières (surfaces lumineuses pour clé / appoint / contre / fenêtre,
tubes pour les néons, ciel pour l'ambiance), écrans, caméras de la recette — puis rend une image de référence par
caméra et exporte un GLB. Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md (C2, lot SV2).

  blender --background --python scripts/studiov/fabriquer_decor.py -- --decor livre-tech --sortie <dossier>
      [--recette fichier.json] [--objets direct.glb] [--rendu 1] [--echantillons 32] [--largeur 1280]

`--objets` : le GLB des objets du niveau « direct » (exporté par le moteur three.js) ; il est importé tel quel, puis
biseauté. Sans lui, la coque seule est bâtie (les objets restent ceux du rendu direct).
Repère : la recette est en repère three.js (y vers le haut) ; Blender est en z vers le haut : (x, y, z) -> (x, -z, y).
Ce script ne lit que la recette et n'écrit que dans --sortie. Aucun réseau."""
import argparse
import json
import math
import pathlib
import sys

import bpy

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
ROLES = {"principale": "#f0b429", "accent": "#00e5ff", "texte": "#ffffff", "fond": "#0b0f14"}


def arguments():
    brut = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--decor", default="livre-tech")
    p.add_argument("--recette")
    p.add_argument("--objets")
    p.add_argument("--sortie", required=True)
    p.add_argument("--rendu", type=int, default=1)
    p.add_argument("--echantillons", type=int, default=32)
    p.add_argument("--largeur", type=int, default=1280)
    p.add_argument("--principale")
    p.add_argument("--accent")
    return p.parse_args(brut)


def rvb(ref, defaut="#808890"):
    h = ref if isinstance(ref, str) and ref.startswith("#") and len(ref) == 7 else ROLES.get(ref, defaut)
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [1.0]     # sRGB -> linéaire


def vers_blender(x, y, z):
    return (x, -z, y)


def noeud(mat, type_):
    return next(n for n in mat.node_tree.nodes if n.type == type_)


def matiere(nom, m):
    mat = bpy.data.materials.new(nom)
    mat.use_nodes = True
    b = noeud(mat, "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = rvb(m["couleur"])
    b.inputs["Roughness"].default_value = m["rugosite"]
    b.inputs["Metallic"].default_value = m["metal"]
    if m["emission"] > 0:
        b.inputs["Emission Color"].default_value = rvb(m["couleur"])
        b.inputs["Emission Strength"].default_value = m["emission"]
    motif = m["motif"]
    if motif != "uni":                              # un relief procédural discret : la texture finale vient de Poly Haven
        arbre, liens = mat.node_tree.nodes, mat.node_tree.links
        coord = arbre.new("ShaderNodeTexCoord")
        if motif == "brique":
            t = arbre.new("ShaderNodeTexBrick")
            t.inputs["Scale"].default_value = 4.0 / m["echelle"]
            t.inputs["Color1"].default_value = rvb(m["couleur"])
            t.inputs["Color2"].default_value = [c * 0.8 for c in rvb(m["couleur"])[:3]] + [1.0]
            t.inputs["Mortar"].default_value = (0.75, 0.72, 0.68, 1.0)
            liens.new(coord.outputs["UV"], t.inputs["Vector"])          # les UV des plans sont en MÈTRES
            liens.new(t.outputs["Color"], b.inputs["Base Color"])
        else:
            t = arbre.new("ShaderNodeTexNoise")
            t.inputs["Scale"].default_value = {"bois": 6, "parquet": 8, "lattes": 8, "beton": 14, "tissu": 60, "pelouse": 90,
                                               "grille": 20, "carreaux": 20, "metal": 40}.get(motif, 12) / m["echelle"]
            bosse = arbre.new("ShaderNodeBump")
            bosse.inputs["Strength"].default_value = 0.15
            liens.new(coord.outputs["UV"], t.inputs["Vector"])
            liens.new(t.outputs["Fac"], bosse.inputs["Height"])
            liens.new(bosse.outputs["Normal"], b.inputs["Normal"])
    return mat


def lueur(nom, couleur, force):
    mat = bpy.data.materials.new(nom)
    mat.use_nodes = True
    b = noeud(mat, "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0, 0, 0, 1)
    b.inputs["Emission Color"].default_value = rvb(couleur)
    b.inputs["Emission Strength"].default_value = force
    return mat


def plan(nom, coins, mat):
    """Un quadrilatère (coins en repère three.js, dans l'ordre) ; la normale suit la règle de la main droite."""
    maille = bpy.data.meshes.new(nom)
    maille.from_pydata([vers_blender(*c) for c in coins], [], [(0, 1, 2, 3)])
    maille.uv_layers.new(name="UVMap")
    lu = math.dist(coins[0], coins[1])
    hv = math.dist(coins[1], coins[2])
    for boucle, uv in zip(maille.uv_layers[0].data, [(0, 0), (lu, 0), (lu, hv), (0, hv)]):      # UV en mètres
        boucle.uv = uv
    ob = bpy.data.objects.new(nom, maille)
    ob.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def viser(ob, cible):
    d = [c - p for c, p in zip(cible, ob.location)]
    import mathutils
    ob.rotation_euler = mathutils.Vector(d).to_track_quat("-Z", "Y").to_euler()


def batir(d):
    sc = bpy.context.scene
    P, mats = d["piece"], {k: matiere("dz_" + k, m) for k, m in d["matieres"].items()}
    l, p, h, av = P["l"], P["p"], P["h"], 5.0
    plan("dz_sol", [(-l / 2 - 2, 0, p / 2 + av), (l / 2 + 2, 0, p / 2 + av), (l / 2 + 2, 0, -p / 2), (-l / 2 - 2, 0, -p / 2)], mats[P["sol"]])
    plan("dz_mur_fond", [(-l / 2 - 2, 0, -p / 2), (l / 2 + 2, 0, -p / 2), (l / 2 + 2, h, -p / 2), (-l / 2 - 2, h, -p / 2)], mats[P["mur"]])
    if not P["ouvert"]:
        plan("dz_mur_gauche", [(-l / 2, 0, p / 2 + av), (-l / 2, 0, -p / 2), (-l / 2, h, -p / 2), (-l / 2, h, p / 2 + av)], mats[P["mur"]])
        plan("dz_mur_droit", [(l / 2, 0, -p / 2), (l / 2, 0, p / 2 + av), (l / 2, h, p / 2 + av), (l / 2, h, -p / 2)], mats[P["mur"]])
        plan("dz_plafond", [(-l / 2, h, -p / 2), (l / 2, h, -p / 2), (l / 2, h, p / 2 + av), (-l / 2, h, p / 2 + av)], mats[P["plafond"]])
    # le ciel : la couleur de fond de l'ambiance + la lumière d'ambiance
    monde = bpy.data.worlds.new("dz_monde")
    monde.use_nodes = True
    fond = noeud(monde, "BACKGROUND")
    ambiance = [x for x in d["lumieres"] if x["type"] == "ambiance"]
    fond.inputs["Color"].default_value = rvb(ambiance[0]["couleur"] if ambiance else d["ambiance"]["fond"], "#0b0f14")
    fond.inputs["Strength"].default_value = 0.12 * (ambiance[0]["intensite"] if ambiance else 0.3)
    sc.world = monde
    # les lumières : surfaces lumineuses (douces, comme une softbox) et tubes pour les néons
    for i, x in enumerate(d["lumieres"]):
        if x["type"] == "ambiance":
            continue
        if x["type"] == "neon":
            maille = bpy.data.meshes.new(f"dz_neon_{i}")
            ob = bpy.data.objects.new(f"dz_neon_{i}", maille)
            sc.collection.objects.link(ob)
            import bmesh
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.022, radius2=0.022, depth=x["l"])
            bm.to_mesh(maille)
            bm.free()
            ob.location = vers_blender(x["x"], x["y"], x["z"])
            ob.rotation_euler = (math.pi / 2, 0, -math.radians(x["ry"]))        # le tube est couché, le long de z (three.js)
            ob.data.materials.append(lueur(f"dz_lueur_{i}", x["couleur"], 6.0 * x["intensite"]))
            continue
        lum = bpy.data.lights.new(f"dz_{x['type']}_{i}", "AREA")
        lum.color = rvb(x["couleur"], "#ffffff")[:3]
        lum.energy = 28.0 * x["intensite"]
        lum.shape = "RECTANGLE"
        lum.size, lum.size_y = (x["l"], x["h"]) if x["type"] == "fenetre" else (0.9, 0.6)
        ob = bpy.data.objects.new(lum.name, lum)
        sc.collection.objects.link(ob)
        ob.location = vers_blender(x["x"], x["y"], x["z"])
        viser(ob, vers_blender(*x["vers"]))
    # les écrans : un cadre et une dalle lumineuse nommée (le moteur y pose l'écran partagé)
    for i, e in enumerate(d["ecrans"]):
        a = math.radians(e["ry"])
        dx, dz = math.cos(a) * e["l"] / 2, -math.sin(a) * e["l"] / 2
        nx, nz = math.sin(a) * 0.052, math.cos(a) * 0.052
        coins = [(e["x"] - dx + nx, e["y"] - e["h"] / 2, e["z"] - dz + nz), (e["x"] + dx + nx, e["y"] - e["h"] / 2, e["z"] + dz + nz),
                 (e["x"] + dx + nx, e["y"] + e["h"] / 2, e["z"] + dz + nz), (e["x"] - dx + nx, e["y"] + e["h"] / 2, e["z"] - dz + nz)]
        plan(f"dz_ecran_{i}", coins, lueur(f"dz_dalle_{i}", "principale", 1.5 if e["source"] != "eteint" else 0.0))
    # les caméras de la recette (capteur 36 × 24 mm : la focale se lit telle quelle)
    cams = []
    for i, c in enumerate(d["cameras"]):
        cam = bpy.data.cameras.new(f"dz_cam_{i}")
        cam.lens, cam.sensor_width, cam.sensor_fit = c["focale"] * 27 / 32, 36.0, "HORIZONTAL"     # champ vertical de la recette, image 16:9
        ob = bpy.data.objects.new(f"dz_cam_{i}_{c['nom']}", cam)
        sc.collection.objects.link(ob)
        ob.location = vers_blender(c["x"], c["y"], c["z"])
        viser(ob, vers_blender(*c["vers"]))
        cams.append(ob)
    return cams


def importer_objets(chemin):
    avant = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(chemin))
    neufs = [o for o in bpy.data.objects if o not in avant and o.type == "MESH"]
    for o in neufs:                                     # arêtes adoucies : la lumière accroche les bords
        mod = o.modifiers.new("dz_biseau", "BEVEL")
        mod.width, mod.segments, mod.limit_method = 0.006, 2, "ANGLE"
    return len(neufs)


def moteur_de_rendu(sc, echantillons):
    permis = [i.identifier for i in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items]
    for nom in ("CYCLES", "BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"):
        try:
            sc.render.engine = nom
            break
        except TypeError:
            continue
    if sc.render.engine == "CYCLES":
        sc.cycles.samples = echantillons
        sc.cycles.use_denoising = True
    return sc.render.engine, permis


def main():
    a = arguments()
    sortie = pathlib.Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    if a.principale:
        ROLES["principale"] = a.principale
    if a.accent:
        ROLES["accent"] = a.accent
    if a.recette:
        d = json.loads(pathlib.Path(a.recette).read_text("utf-8"))
    else:
        d = json.loads((RACINE / "backend" / "app" / "studiov" / "livres.json").read_text("utf-8"))[a.decor]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    cams = batir(d)
    objets = importer_objets(a.objets) if a.objets else 0
    moteur, _ = moteur_de_rendu(sc, a.echantillons)
    sc.render.resolution_x, sc.render.resolution_y = a.largeur, round(a.largeur * 9 / 16)
    sc.view_settings.exposure = math.log2(max(0.2, d["ambiance"]["exposition"]))
    rendus = []
    for cam in cams[:max(0, a.rendu)]:
        sc.camera = cam
        sc.render.filepath = str(sortie / f"{a.decor}_{cam.name}.png")
        bpy.ops.render.render(write_still=True)
        rendus.append(pathlib.Path(sc.render.filepath).name)
    glb = sortie / f"{a.decor}.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", export_cameras=True, export_lights=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(sortie / f"{a.decor}.blend"))
    bilan = {"decor": a.decor, "blender": bpy.app.version_string, "moteur": moteur, "objets_importes": objets,
             "cameras": [c.name for c in cams], "rendus": rendus, "glb": glb.name, "glb_octets": glb.stat().st_size}
    (sortie / f"{a.decor}.fabrique.json").write_text(json.dumps(bilan, ensure_ascii=False, indent=1), "utf-8")
    print("FABRIQUE_OK " + json.dumps(bilan, ensure_ascii=False))


if __name__ == "__main__":
    main()
