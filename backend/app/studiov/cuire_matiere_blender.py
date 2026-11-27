# -*- coding: utf-8 -*-
"""SVH (14/11/2026) — CUIT une matière de Blender (nœuds procéduraux ou images) en trois cartes que le studio virtuel
et la Forge savent lire : couleur, normale (convention OpenGL), rugosité — plus le métal quand la matière en a.
C'est le chemin « depuis Blender lui-même » du décorateur : la matière qu'on a composée (ou trouvée dans une
bibliothèque d'assets de Blender) devient une matière de l'utilisateur dans la Forge, donc un habillage du studio.

  blender --background MON_FICHIER.blend --python backend/app/studiov/cuire_matiere_blender.py -- --sortie <dossier>
      [--matiere "Nom"] [--taille 1024] [--metres 1.0] [--liste]

Sans `--matiere`, toutes les matières du fichier qui ont des nœuds sont cuites. `--liste` n'écrit rien : il imprime
les noms. `--metres` = le côté du carreau cuit, en mètres (les textures procédurales se répètent à cette échelle).
Sortie : <dossier>/<nom-sûr>/{basecolor,normal,roughness[,metallic]}.png + meta.json ; la dernière ligne imprimée est
`CUISSON_OK {…}`. L'application le lance elle-même (Studio virtuel › Décorer › Matières › Mes matières › Depuis
Blender : services/studiov_habillage.cuire_blender) et range les cartes cuites dans la Forge.

Le fichier ouvert n'est JAMAIS enregistré : la cuisson travaille sur une COPIE de la matière, posée sur un plan neuf.
Aucun réseau. Les énumérations sont lues, les nœuds cherchés par TYPE (les noms sont traduits selon la langue)."""
import argparse
import json
import pathlib
import re
import sys

import bpy


def arguments():
    brut = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--sortie")
    p.add_argument("--matiere")
    p.add_argument("--taille", type=int, default=1024)
    p.add_argument("--metres", type=float, default=1.0)
    p.add_argument("--liste", action="store_true")
    return p.parse_args(brut)


def nom_sur(nom: str) -> str:
    return (re.sub(r"[^a-z0-9]+", "_", nom.lower()).strip("_") or "matiere")[:40]


def noeud(mat, type_):
    return next((n for n in mat.node_tree.nodes if n.type == type_), None)


def candidates():
    return [m for m in bpy.data.materials if m.use_nodes and m.node_tree and not m.is_grease_pencil and noeud(m, "OUTPUT_MATERIAL")]


def moteur_cycles(sc):
    try:
        sc.render.engine = "CYCLES"
    except TypeError as e:                                  # le message liste les moteurs présents
        raise SystemExit(f"Cycles est nécessaire à la cuisson : {e}") from None
    sc.cycles.samples = 16
    sc.cycles.use_denoising = False
    try:
        sc.cycles.device = "CPU"                            # reproductible, et sans pilote à charger en mode sans fenêtre
    except TypeError:
        pass


def image(nom, taille, couleur):
    im = bpy.data.images.new(nom, taille, taille, alpha=False)
    if not couleur:
        im.colorspace_settings.name = "Non-Color"
    return im


def ecrire(im, chemin):
    im.filepath_raw = str(chemin)
    im.file_format = "PNG"
    im.save()


def cuire_passe(mat, cible, type_, filtre=None):
    """Cuit une passe de Cycles dans l'image `cible` (le nœud image actif de la matière)."""
    arbre = mat.node_tree
    n = arbre.nodes.new("ShaderNodeTexImage")
    n.image = cible
    for x in arbre.nodes:
        x.select = False
    n.select = True
    arbre.nodes.active = n
    try:
        if filtre:
            bpy.ops.object.bake(type=type_, pass_filter=filtre)
        else:
            bpy.ops.object.bake(type=type_)
    finally:
        arbre.nodes.remove(n)


def cuire_entree(mat, cible, entree):
    """Cuit la VALEUR d'une entrée du Principled (couleur de base, métal) : branchée un instant sur une émission —
    la passe « diffuse » de Cycles rend noir un métal, alors que sa couleur de base est bien là."""
    arbre, liens = mat.node_tree, mat.node_tree.links
    sortie = noeud(mat, "OUTPUT_MATERIAL")
    surface = sortie.inputs["Surface"] if "Surface" in sortie.inputs else sortie.inputs[0]
    avant = surface.links[0].from_socket if surface.is_linked else None
    em = arbre.nodes.new("ShaderNodeEmission")
    try:
        if entree.is_linked:
            liens.new(entree.links[0].from_socket, em.inputs[0])
        else:
            v = entree.default_value
            em.inputs[0].default_value = (v[0], v[1], v[2], 1.0) if hasattr(v, "__len__") else (v, v, v, 1.0)
        liens.new(em.outputs[0], surface)
        cuire_passe(mat, cible, "EMIT")
    finally:
        arbre.nodes.remove(em)
        if avant is not None:
            liens.new(avant, surface)


def cuire(source, dossier, taille, metres):
    sc = bpy.context.scene
    mat = source.copy()                                     # la matière du fichier n'est jamais touchée
    maille = bpy.data.meshes.new("dz_cuisson")
    d = metres / 2
    maille.from_pydata([(-d, -d, 0), (d, -d, 0), (d, d, 0), (-d, d, 0)], [], [(0, 1, 2, 3)])
    uv = maille.uv_layers.new(name="UVMap")
    for boucle, c in zip(uv.data, [(0, 0), (1, 0), (1, 1), (0, 1)]):
        boucle.uv = c
    ob = bpy.data.objects.new("dz_cuisson", maille)
    sc.collection.objects.link(ob)
    ob.data.materials.append(mat)
    bpy.context.view_layer.update()
    for x in list(sc.objects):                              # (la couche de vue garde un instant l'objet de la cuisson d'avant)
        if x is not None and x.name in bpy.context.view_layer.objects:
            x.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    dossier.mkdir(parents=True, exist_ok=True)
    cartes, bsdf = [], noeud(mat, "BSDF_PRINCIPLED")
    try:
        base = image("dz_basecolor", taille, True)
        if bsdf is not None:
            cuire_entree(mat, base, bsdf.inputs["Base Color"])
        else:
            cuire_passe(mat, base, "DIFFUSE", {"COLOR"})
        ecrire(base, dossier / "basecolor.png")
        cartes.append("basecolor")
        normale = image("dz_normal", taille, False)
        cuire_passe(mat, normale, "NORMAL")
        ecrire(normale, dossier / "normal.png")
        cartes.append("normal")
        rug = image("dz_roughness", taille, False)
        cuire_passe(mat, rug, "ROUGHNESS")
        ecrire(rug, dossier / "roughness.png")
        cartes.append("roughness")
        if bsdf is not None and (bsdf.inputs["Metallic"].is_linked or bsdf.inputs["Metallic"].default_value > 0.01):
            metal = image("dz_metallic", taille, False)
            cuire_entree(mat, metal, bsdf.inputs["Metallic"])
            ecrire(metal, dossier / "metallic.png")
            cartes.append("metallic")
    finally:
        bpy.data.objects.remove(ob)
        bpy.data.meshes.remove(maille)
        bpy.data.materials.remove(mat)
    meta = {"nom": source.name, "cartes": cartes, "taille": taille, "metres": metres, "blender": bpy.app.version_string,
            "fichier": pathlib.Path(bpy.data.filepath).name if bpy.data.filepath else ""}
    (dossier / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), "utf-8")
    return meta


def main():
    a = arguments()
    mats = candidates()
    if a.liste:
        print("MATIERES " + json.dumps([m.name for m in mats], ensure_ascii=False))
        return
    if not a.sortie:
        raise SystemExit("--sortie <dossier> est attendu")
    if a.matiere:
        mats = [m for m in mats if m.name == a.matiere]
        if not mats:
            raise SystemExit(f"matière introuvable : {a.matiere}")
    taille = max(256, min(4096, a.taille))
    metres = max(0.05, min(20.0, a.metres))
    moteur_cycles(bpy.context.scene)
    sortie, faits, pris = pathlib.Path(a.sortie), [], set()
    for m in mats:
        nom = nom_sur(m.name)
        while nom in pris:
            nom += "_2"
        pris.add(nom)
        faits.append(dict(cuire(m, sortie / nom, taille, metres), dossier=nom))
    print("CUISSON_OK " + json.dumps(faits, ensure_ascii=False))


if __name__ == "__main__":
    main()
