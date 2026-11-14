# -*- coding: utf-8 -*-
"""SVO (15/11/2026) — SORT un objet d'un fichier Blender en GLB autonome, pour la bibliothèque d'objets importés du
studio virtuel. C'est le chemin des assets qu'on ne trouve que DANS Blender (BlenderKit, bibliothèques d'assets,
modèles faits main) : l'utilisateur pose l'asset dans son fichier, avec son compte ; l'application en tire un GLB.

  blender --background --disable-autoexec MON_FICHIER.blend --python backend/app/studiov/exporter_objet_blender.py -- --liste
  blender --background --disable-autoexec MON_FICHIER.blend --python … -- --sortie <dossier> --objet "Nom"

`--liste` imprime `OBJETS [{nom, faces}]` : les objets de premier niveau qui portent une surface (eux ou leurs enfants).
L'export prend l'objet ET ses enfants, modificateurs appliqués, textures incluses, sans compression (le moteur de
l'application n'ouvre ni Draco ni Meshopt), axe Y vers le haut. Dernière ligne imprimée : `EXPORT_OK {…}`.
Le fichier ouvert n'est JAMAIS enregistré. Aucun réseau."""
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
    p.add_argument("--objet")
    p.add_argument("--liste", action="store_true")
    return p.parse_args(brut)


def famille(ob):
    out = [ob]
    for e in ob.children:
        out += famille(e)
    return out


def faces(ob):
    return sum(len(x.data.polygons) for x in famille(ob) if x.type == "MESH" and x.data)


def candidats():
    return [o for o in bpy.context.scene.objects if o.parent is None and faces(o) > 0]


def main():
    a = arguments()
    obs = candidats()
    if a.liste:
        print("OBJETS " + json.dumps([{"nom": o.name, "faces": faces(o)} for o in obs][:300], ensure_ascii=False))
        return
    if not a.sortie or not a.objet:
        raise SystemExit("--sortie <dossier> et --objet <nom> sont attendus")
    ob = next((o for o in obs if o.name == a.objet), None)
    if ob is None:
        raise SystemExit(f"objet introuvable : {a.objet}")
    for x in bpy.context.scene.objects:
        x.select_set(False)
    membres = [x for x in famille(ob) if x.name in bpy.context.view_layer.objects]
    for x in membres:
        x.hide_set(False)
        x.select_set(True)
    bpy.context.view_layer.objects.active = ob
    sortie = pathlib.Path(a.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    nom = (re.sub(r"[^a-z0-9]+", "_", ob.name.lower()).strip("_") or "objet")[:40]
    glb = sortie / f"{nom}.glb"
    options = {"filepath": str(glb), "export_format": "GLB", "use_selection": True, "export_apply": True, "export_yup": True,
               "export_cameras": False, "export_lights": False, "export_animations": False}
    connues = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
    if "export_draco_mesh_compression_enable" in connues:
        options["export_draco_mesh_compression_enable"] = False
    bpy.ops.export_scene.gltf(**{k: v for k, v in options.items() if k in connues})
    print("EXPORT_OK " + json.dumps({"nom": ob.name, "fichier": glb.name, "faces": faces(ob), "octets": glb.stat().st_size,
                                     "blender": bpy.app.version_string}, ensure_ascii=False))


if __name__ == "__main__":
    main()
