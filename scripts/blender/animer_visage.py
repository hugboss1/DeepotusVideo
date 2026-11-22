# -*- coding: utf-8 -*-
"""Anime le VISAGE d'un personnage dans Blender, depuis la ligne de commande (22/11/2026).

Utilise le même moteur que l'application (backend/app/services/visage_blender.py) : lèvres sur un texte, un JSON de
Rhubarb Lip Sync ou un WAV ; expressions ; clignements. Fonctionne sur :
  * un rig des personnages de Blender Studio (studio.blender.org/characters : Rain, Snow, Einar, Sprite Fright…),
    Rigify ou Auto-Rig Pro : les os du visage sont trouvés par leur nom (--mode os) ; si un os ne bouge pas dans le
    bon sens, forcez-le avec --os NOM=COMMANDE:CANAL:GAIN (ex. --os "jaw_master=jawOpen:rotation:-1") ;
  * un personnage à clés de forme ARKit / visèmes (Ready Player Me, VRM, CC4…) : --mode cles ;
  * un personnage GÉNÉRÉ (Meshy, Tripo, Rodin : .glb sans visage animable) : des clés DZ_ sont sculptées autour de
    repères réglables (--bouche U,V --oeil-gauche U,V --oeil-droit U,V), --mode procedural.

Exemples (depuis la racine du dépôt) :
  python scripts/blender/animer_visage.py --source perso.glb --texte "Bonjour !" --expression joie:0:2 --glb sortie.glb
  python scripts/blender/animer_visage.py --blend rain.blend --wav voix.wav --rhubarb voix.json --sortie rain_anime.blend
  python scripts/blender/animer_visage.py --blend rain.blend --texte "Salut" --mode os --rapport
  python scripts/blender/animer_visage.py --script-seul visage.py --texte "Bonjour"   (puis Blender › Scripting › Run)

Blender : BLENDER_PATH, sinon le plus récent sous « C:\\Program Files\\Blender Foundation ». Aucun appel réseau.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RACINE / "backend"))
os.environ.setdefault("DEEPOTUS_DATA_DIR", str(Path.home() / ".deepotus-visage"))

from app.services import visage_blender as V  # noqa: E402


def _uv(t: str) -> list[float]:
    u, v = t.split(",")
    return [float(u), float(v)]


def _expression(t: str) -> dict:
    morceaux = t.split(":")
    nom, debut, fin = morceaux[0], float(morceaux[1]), float(morceaux[2])
    e = {"nom": nom, "debut": debut, "fin": fin}
    if len(morceaux) > 3:
        e["intensite"] = float(morceaux[3])
    return e


def _os(t: str) -> tuple[str, dict]:
    nom, reste = t.split("=", 1)
    cmd, canal, gain = reste.split(":")
    return nom, {"commande": cmd, "canal": canal, "gain": float(gain)}


def main(argv=None) -> int:
    a = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = a.add_argument_group("personnage")
    src.add_argument("--blend", help="le .blend à ouvrir (rig de Blender Studio, Rigify…)")
    src.add_argument("--source", help="ou un .glb / .fbx à importer (personnage généré)")
    src.add_argument("--objet", default="", help="le maillage du visage (défaut : celui qui a le plus de clés)")
    src.add_argument("--armature", default="", help="l'armature (défaut : celle du maillage)")
    src.add_argument("--mode", default="auto", choices=V.MODES)
    src.add_argument("--face", default="-Y", choices=V.FACES, help="l'avant du personnage (glTF importé : -Y)")
    par = a.add_argument_group("parole et jeu")
    par.add_argument("--texte", default="")
    par.add_argument("--rhubarb", help="JSON de Rhubarb Lip Sync (rhubarb -f json voix.wav)")
    par.add_argument("--wav", help="la voix : sa durée cale le texte, son énergie ouvre la mâchoire")
    par.add_argument("--expression", action="append", default=[], help="nom:debut:fin[:intensite] en secondes ; "
                                                                        "noms : " + ", ".join(V.EXPRESSIONS))
    par.add_argument("--sans-clignements", action="store_true")
    par.add_argument("--fps", type=int, default=24)
    par.add_argument("--debut", type=int, default=1, help="première image")
    par.add_argument("--amplitude", type=float, default=1.0)
    rep = a.add_argument_group("réglages")
    rep.add_argument("--bouche", type=_uv, help="U,V de la bouche (tête vue de face, 0..1)")
    rep.add_argument("--oeil-gauche", type=_uv, help="U,V de l'œil gauche DU PERSONNAGE")
    rep.add_argument("--oeil-droit", type=_uv)
    rep.add_argument("--os", action="append", default=[], help="NOM=COMMANDE:CANAL:GAIN (canal : haut, avant, "
                                                                "cote, rotation)")
    out = a.add_argument_group("sorties")
    out.add_argument("--sortie", help="le .blend animé (copie ; l'original n'est jamais écrasé)")
    out.add_argument("--glb", help="un .glb avec morphes animés (Studio 3D, web)")
    out.add_argument("--script-seul", help="écrit seulement le script Blender ici (à lancer dans Blender ouvert)")
    out.add_argument("--rapport", action="store_true", help="affiche le JSON complet du résultat")
    x = a.parse_args(argv)

    reperes = {}
    if x.bouche:
        reperes["bouche"] = x.bouche
    if x.oeil_gauche:
        reperes["oeil_gauche"] = x.oeil_gauche
    if x.oeil_droit:
        reperes["oeil_droit"] = x.oeil_droit
    rh = Path(x.rhubarb).read_text(encoding="utf-8") if x.rhubarb else None
    abs_ = lambda p: str(Path(p).resolve()) if p else None  # noqa: E731
    try:
        params = V.parametres(texte=x.texte, rhubarb=rh, wav=x.wav, expressions=[_expression(e) for e in x.expression],
                              clignements=not x.sans_clignements, fps=x.fps, debut_image=x.debut, objet=x.objet,
                              armature=x.armature, mode=x.mode, face=x.face, reperes=reperes, amplitude=x.amplitude,
                              os_reglages=dict(_os(o) for o in x.os), source=abs_(x.source),
                              sortie_blend=abs_(x.sortie), sortie_glb=abs_(x.glb))
    except V.VisageRefuse as e:
        print(f"Paramètres refusés : {e}", file=sys.stderr)
        return 2
    if x.script_seul:
        Path(x.script_seul).write_text(V.generer_script(params), encoding="utf-8")
        print(f"Script écrit : {x.script_seul} ({len(params['controles'])} commandes, images {params['images']})")
        return 0
    if not (x.blend or x.source):
        print("--blend ou --source requis (ou --script-seul)", file=sys.stderr)
        return 2
    if not (x.sortie or x.glb):
        print("Aucune sortie : ajoutez --sortie anime.blend et/ou --glb anime.glb", file=sys.stderr)
        return 2
    res = V.animer_fichier(params, abs_(x.blend))
    if x.rapport:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(f"mode : {res.get('mode')}  objet : {res.get('objet')}  armature : {res.get('armature')}")
        for l in res.get("animees", [])[:30]:
            print("  animé  " + l)
        for l in res.get("crees", []):
            print("  créé   " + l)
        if res.get("absentes"):
            print("  absent " + ", ".join(sorted(set(res["absentes"]))))
        for l in res.get("erreurs", []):
            print("  ERREUR " + l)
    return 0 if res.get("mode") and not res.get("erreurs") else 1


if __name__ == "__main__":
    sys.exit(main())
