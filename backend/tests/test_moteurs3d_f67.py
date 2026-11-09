"""t485 (F6.7, lot « Fiches modèle ») — réglages de coût de Meshy 7.1 et Rodin 2.5 servis par fal.

Schémas et prix relus le 09/11/2026 :
- Meshy 7.1 : `model_type` est une constante « standard » (Smart Topology a ses propres endpoints) ;
  `target_polycount` n'agit qu'avec `should_remesh` (vrai par défaut) ;
- Rodin 2.5 : l'add-on HighPack (`addons`) coûte 0,80 $ de plus par génération ; cinq maillages ajoutés.

Run: <python embarqué> backend/tests/test_moteurs3d_f67.py
"""
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
sys.stdout.reconfigure(encoding="utf-8")

from app.services import moteurs3d_neufs as M  # noqa: E402

ok = fail = 0


def check(nom, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1
        print(f"  PASS  {nom}")
    else:
        fail += 1
        print(f"  FAIL  {nom} {detail}")


def refuse(moteur, reglages):
    try:
        M.valider(moteur, reglages)
    except ValueError as e:
        return str(e)
    return None


def reg(moteur, cle):
    return next((r for r in M.schema(moteur) if r["cle"] == cle), None)


print("\n[1] Meshy 7.1")
check("1.1 model_type : seule valeur « standard »", reg("meshy-7.1", "model_type")["valeurs"] == ["standard"])
check("1.2 lowpoly et smart-topology refusés AVANT l'envoi", refuse("meshy-7.1", {"model_type": "lowpoly"})
      and refuse("meshy-7.1", {"model_type": "smart-topology"}))
e = refuse("meshy-7.1", {"should_remesh": False, "target_polycount": 20000})
check("1.3 polycount avec remaillage coupé : refusé, message clair", e is not None and "should_remesh" in e, e)
check("1.4 polycount avec remaillage actif (explicite) : accepté",
      M.valider("meshy-7.1", {"should_remesh": True, "target_polycount": 20000}) ==
      {"should_remesh": True, "target_polycount": 20000})
check("1.5 polycount seul (remaillage par défaut) : accepté", M.valider("meshy-7.1", {"target_polycount": 20000})
      == {"target_polycount": 20000})
check("1.6 remaillage coupé sans polycount : accepté", M.valider("meshy-7.1", {"should_remesh": False})
      == {"should_remesh": False})
a = M.args("meshy-7.1", ["http://img"], {"reglages": {"target_polycount": 12000}, "pose": "a-pose"})
check("1.7 arguments : polycount, pose, image", a.get("target_polycount") == 12000 and a.get("pose_mode") == "a-pose"
      and a.get("image_url") == "http://img", a)
check("1.8 prix Meshy inchangé (texturé 1,20 $, sans texture 0,80 $)",
      M.prix("meshy-7.1", {}) == [("Meshy 7.1 texturé", 1.20)]
      and M.prix("meshy-7.1", {"should_texture": False}) == [("Meshy 7.1 sans texture", 0.80)])

print("\n[2] Rodin 2.5")
h = reg("rodin-2.5", "highpack")
check("2.1 réglage highpack : booléen, faux par défaut, surcoût 0,80 $ affiché",
      h and h["type"] == "bool" and h["defaut"] is False and h.get("surcout") == 0.80, h)
a = M.args("rodin-2.5", ["http://img"], {"reglages": {"highpack": True}})
check("2.2 highpack -> addons [HighPack], la clé de l'app ne part pas", a.get("addons") == ["HighPack"]
      and "highpack" not in a, a)
a = M.args("rodin-2.5", ["http://img"], {"reglages": {"highpack": False}})
check("2.3 highpack coupé : ni addons ni highpack envoyés", "addons" not in a and "highpack" not in a, a)
a = M.args("rodin-2.5", ["http://img"], {"reglages": {}})
check("2.4 sans réglage : rien ajouté (inchangé)", "addons" not in a and "highpack" not in a, a)
check("2.5 devis : 0,40 $ seul, 1,20 $ avec HighPack", M.prix("rodin-2.5", {}) == [("Rodin 2.5", 0.40)]
      and M.prix("rodin-2.5", {"highpack": True}) == [("Rodin 2.5", 0.40), ("HighPack", 0.80)])
nouveaux = {"100K Quad", "200K Quad", "50K Triangle", "1M Triangle", "2M Triangle"}
check("2.6 maillages ajoutés par fal présents", nouveaux <= set(reg("rodin-2.5", "quality_mesh_option")["valeurs"]))
check("2.7 un maillage inconnu reste refusé", refuse("rodin-2.5", {"quality_mesh_option": "3M Triangle"}) is not None)
check("2.8 le registre sert le surcoût à l'écran", any(r["cle"] == "highpack" and r.get("surcout") == 0.80
                                                       for r in M.registre()["rodin-2.5"]["reglages"]))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
