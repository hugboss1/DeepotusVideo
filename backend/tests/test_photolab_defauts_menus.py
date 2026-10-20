# -*- coding: utf-8 -*-
"""#415 (relevé du 20/10/2026, docs/superpowers/specs/2026-10-20-photolab-defauts-menus-releve.md) — dialogues des menus
du Photolab que le registre de photocraft 0.10 décrivait mal : le pont les répare À LA SOURCE (photolab_registre).
  [1] Affichage › Nouveau repère… : `position` (requise) est un nombre en px, `color` la liste du moteur ;
  [2] Image › Recouvrement… : `{width:px>=1=1}` (clé sans guillemets) ne donnait AUCUN champ — `width` 1..100 px ;
  [3] les valeurs que l'écran fournit par ses listes de choix passent la liste blanche (couche de Charger la sélection,
      document de Dupliquer le calque, motif du calque de remplissage), les mauvaises sont refusées.
Hors ligne : bibliothèque standard seulement, aucun moteur.
Run : & $PY -X utf8 tests/test_photolab_defauts_menus.py   (depuis backend/)"""
import json, pathlib, sys
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
from app.services import photolab_registre as PR              # noqa: E402
import photocraft_version as _PV                                # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


def passe(cid, params):
    try:
        return PR.verifier(STRUCT, cid, params) == params
    except ValueError:
        return False


def champs(cid):
    return {c["cle"]: c for c in STRUCT[cid]["champs"]}


def main():
    global STRUCT
    STRUCT = PR.structurer(json.loads(_PV.fichier_commandes().read_text(encoding="utf-8")))

    print("[1] Nouveau repère…")
    g = champs("view.newGuide")
    check("1a position : nombre en px, requis", g["position"]["type"] == "number" and g["position"].get("unite") == "px"
          and not g["position"]["optionnel"], g["position"])
    check("1b couleur : facultative et cachée (sans elle, celle des Préférences)", g["color"]["type"] == "?" and g["color"]["optionnel"], g["color"])
    check("1d admis : vertical à 120 px", passe("view.newGuide", {"orientation": "vertical", "position": 120}))
    check("1e refusés : position texte ou infinie",
          not passe("view.newGuide", {"orientation": "vertical", "position": "50%"})
          and not passe("view.newGuide", {"orientation": "vertical", "position": float("inf")}))
    check("1f position sans bornes : un champ numérique à l'écran, pas un curseur", "min" not in g["position"])

    print("[2] Recouvrement…")
    t = champs("image.trap")
    check("2a un champ width : 1..100 px, entier, défaut 1, requis", list(t) == ["width"] and t["width"]["type"] == "number"
          and t["width"]["min"] == 1 and t["width"]["max"] == 100 and t["width"]["entier"] and t["width"]["defaut"] == 1
          and t["width"]["unite"] == "px" and not t["width"]["optionnel"], t)
    check("2b admis : 3 px ; refusés : 0, 101, texte", passe("image.trap", {"width": 3}) and not passe("image.trap", {"width": 0})
          and not passe("image.trap", {"width": 101}) and not passe("image.trap", {"width": "2"}))
    check("2c clé inconnue refusée", not passe("image.trap", {"width": 2, "path": "c:/x"}))

    print("[3] valeurs des listes de choix de l'écran")
    check("3a Charger la sélection : transparence, masque, couche alpha 0", all(passe("select.loadSelection", {"channel": c, "operation": "new", "invert": False})
          for c in ("transparency", "mask", "vectorMask", 0)))
    check("3b Charger la sélection : un chemin de fichier refusé", not passe("select.loadSelection", {"channel": "c:/profil.icc"}))
    check("3c Dupliquer le calque : nouveau document, document 1", passe("layer.duplicate", {"document": "new", "name": "copie"})
          and passe("layer.duplicate", {"document": 1}))
    check("3d Remplissage motif : l'id d'un motif", passe("layer.newFillLayer.pattern", {"pattern": "059289fb-e0b5-6144-cf07-4e299f48629e", "scale": 100,
          "angle": 0, "link": True}))

    print("[5] Vérifier l'orthographe… : les clés de change / changeAll / addToDictionary")
    f = {"action": "change", "layer": 4, "start": 0, "end": 6, "word": "Bonjur", "replace": "Bonjour"}
    check("5a Changer passe (calque, bornes, mot vérifié, remplacement)", passe("edit.checkSpelling", f))
    check("5b Tout changer, Ajouter, liste avec ignore", passe("edit.checkSpelling", {"action": "changeAll", "word": "a", "replace": "b"})
          and passe("edit.checkSpelling", {"action": "addToDictionary", "word": "mondee"})
          and passe("edit.checkSpelling", {"action": "list", "ignore": ["le"]}))
    check("5c refusés : début négatif, action hors liste, remplacement trop long, chemin",
          not passe("edit.checkSpelling", {**f, "start": -1}) and not passe("edit.checkSpelling", {"action": "supprimer"})
          and not passe("edit.checkSpelling", {**f, "replace": "x" * 300}) and not passe("edit.checkSpelling", {**f, "path": "c:/x"}))

    print("[4] Barre d'outils… : outils masqués dans les préférences de l'écran")
    from app.services import photolab_preferences as PP
    check("4a défaut : aucun outil masqué", PP.etat_defaut()["outils"] == {"masques": []})
    check("4b admis, sans doublon", PP.valider({"outils": {"masques": ["zoom", "lasso", "zoom"]}})["outils"] == {"masques": ["zoom", "lasso"]})
    refus = []
    for mauvais in ({"masques": "zoom"}, {"masques": ["../x"]}, {"masques": [3]}, {"masques": ["a"] * 101}, {"autre": []}):
        try:
            PP.valider({"outils": mauvais}); refus.append(False)
        except ValueError:
            refus.append(True)
    check("4c refusés : texte, chemin, nombre, plus de 100, clé inconnue", all(refus), refus)
    check("4d un état sans « outils » (fichier d'avant #415) reste lisible", PP.valider({"version": 1})["outils"] == {"masques": []})

    print(f"\n=== {ok} passed, {fail} failed ===")
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
