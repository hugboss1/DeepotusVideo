# -*- coding: utf-8 -*-
"""t138 (Photolab P3, tâche B3) — libellés des paramètres, des valeurs d'énumération, des réglages et des dialogues.

  [1] node lance frontend/photolab/qa/outils/libelles.mjs sur le registre structuré de la fixture : MÊME définition de
      « clé visible » que l'écran (mod-champs.js champsVisibles), sur le périmètre des dialogues (filtres du menu hors
      « bientôt », ajustements, calques de réglage, styles de calque).
  [2] toute clé visible a son photolab.param.<cle> et toute valeur d'énumération fermée son photolab.valeur.<v>, en fr ET en.
  [3] aucune entrée photolab.param.* / photolab.valeur.* orpheline (absente du périmètre) ; les modes de fusion restent
      sous photolab.fusion.* (jamais de photolab.valeur.* pour un champ `blend`).
  [4] les 16 photolab.kind.<kind> couvrent exactement les kinds de layer.newAdjustmentLayer.* ; les en-têtes des dialogues
      (Réglages, Courbes, Niveaux, Styles) existent.
  [5] le dictionnaire assemblé (frontend/shared et frontend/dist/shared) porte ces clés : l'assemblage est à jour.
Hors ligne : aucun moteur ; node requis. Le registre passe par FICHIER temporaire.
Run : & $PY -X utf8 tests/test_photolab_libelles.py   (depuis backend/)"""
import json, pathlib, re, shutil, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
ROOT = BACKEND.parent
sys.path.insert(0, str(BACKEND))
from app.services import photolab_registre as PR             # noqa: E402

OUTIL = ROOT / "frontend" / "photolab" / "qa" / "outils" / "libelles.mjs"
MENUS = ROOT / "frontend" / "photolab" / "donnees" / "menus.json"
DICO = ROOT / "frontend" / "shared" / "i18n" / "photolab.json"
ASSEMBLES = [ROOT / "frontend" / "shared" / "dz-i18n-dico.js", ROOT / "frontend" / "dist" / "shared" / "dz-i18n-dico.js"]
ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:1500]}")


COMMANDES = json.loads((BACKEND / "tests" / "photocraft_commandes_0.3.0.json").read_text(encoding="utf-8"))
REG = PR.structurer(COMMANDES)
DIC = json.loads(DICO.read_text(encoding="utf-8"))


def plein(cle):
    e = DIC.get(cle)
    return bool(e) and isinstance(e.get("fr"), str) and isinstance(e.get("en"), str) and e["fr"].strip() != "" and e["en"].strip() != ""


print("[1] périmètre calculé par mod-champs.js (node)")
node = shutil.which("node")
check("1.1 node présent", node is not None)
check("1.2 l'outil existe", OUTIL.is_file(), OUTIL)
perim = {"ids": [], "params": {}, "valeurs": {}}
if node and OUTIL.is_file():
    with tempfile.TemporaryDirectory() as d:
        entree, res = pathlib.Path(d) / "registre.json", pathlib.Path(d) / "libelles.json"
        entree.write_text(json.dumps({k: {"champs": v["champs"]} for k, v in REG.items()}), encoding="utf-8")
        r = subprocess.run([node, str(OUTIL), str(entree), str(MENUS), str(res)], capture_output=True, text=True, encoding="utf-8")
        check("1.3 l'outil tourne", r.returncode == 0, r.stderr[-800:])
        if r.returncode == 0:
            perim = json.loads(res.read_text(encoding="utf-8"))
ids = perim["ids"]
check("1.4 périmètre : au moins 100 commandes", len(ids) >= 100, len(ids))
for pre, mini in (("filter.", 60), ("image.adjustments.", 15), ("layer.newAdjustmentLayer.", 16), ("layer.layerStyle.", 12)):
    n = sum(1 for i in ids if i.startswith(pre))
    check(f"1.5 {pre}* : au moins {mini}", n >= mini, n)
check("1.6 D9, SANS_EDITEUR et Galerie hors périmètre", not any(i in ids for i in ("filter.cameraRaw", "filter.liquify", "filter.vanishingPoint",
      "filter.adaptiveWideAngle", "filter.filterGallery", "filter.other.custom", "filter.convertForSmartFilters"))
      and not any(i.startswith("filter.gallery.") for i in ids))
check("1.7 des clés et des valeurs à traduire", len(perim["params"]) >= 150 and len(perim["valeurs"]) >= 100,
      (len(perim["params"]), len(perim["valeurs"])))

# Le dictionnaire est en minuscules (convention test_i18n_l0) et mod-champs.js compose photolab.param.<cle>.toLowerCase() :
# deux clés (ou valeurs) du moteur qui ne diffèrent que par la casse s'écraseraient.
for nom, ens in (("clés", perim["params"]), ("valeurs", perim["valeurs"]), ("kinds", {i[len("layer.newAdjustmentLayer."):]: 1 for i in REG if i.startswith("layer.newAdjustmentLayer.")})):
    groupes = {}
    for x in ens:
        groupes.setdefault(x.lower(), set()).add(x)
    coll = sorted(sorted(g) for g in groupes.values() if len(g) > 1)
    check(f"1.8 aucune collision de casse entre {nom} du moteur", not coll, coll)
nonmin = sorted(k for k in DIC if k.startswith(("photolab.param.", "photolab.valeur.", "photolab.kind.")) and k != k.lower())
check("1.9 clés des trois familles toutes en minuscules", not nonmin, nonmin[:8])

print("\n[2] chaque clé visible et chaque valeur fermée est traduite (fr ET en)")
sans = sorted(c for c in perim["params"] if not plein("photolab.param." + c.lower()))
check("2.1 photolab.param.<cle> fr+en non vides pour toute clé visible", not sans, sans)
sans = sorted(v for v in perim["valeurs"] if not plein("photolab.valeur." + v.lower()))
check("2.2 photolab.valeur.<valeur> fr+en non vides pour toute valeur fermée", not sans, sans)
vides = sorted(k for k in DIC if k.startswith(("photolab.param.", "photolab.valeur.", "photolab.kind.")) and not plein(k))
check("2.3 aucune entrée à moitié vide dans les trois familles", not vides, vides)
# Une traduction qui recopie la clé brute (« blurAngle ») n'en est pas une.
brutes = sorted(k for k in DIC if k.startswith("photolab.param.") and re.search(r"[a-z][A-Z]", DIC[k]["en"]) or re.search(r"[a-z][A-Z]", DIC[k]["fr"]))
check("2.4 aucun libellé en camelCase brut", not brutes, brutes)

print("\n[3] pas d'orphelins")
orph_p = sorted(k for k in DIC if k.startswith("photolab.param.") and k[len("photolab.param."):] not in {c.lower() for c in perim["params"]})
check("3.1 aucune photolab.param.* hors périmètre", not orph_p, orph_p)
orph_v = sorted(k for k in DIC if k.startswith("photolab.valeur.") and k[len("photolab.valeur."):] not in {v.lower() for v in perim["valeurs"]})
check("3.2 aucune photolab.valeur.* hors périmètre", not orph_v, orph_v)
fusion = [c for i in ids for c in REG[i]["champs"] if str(c["cle"]).lower() == "blend"]
check("3.3 des champs blend existent et leurs modes ne passent pas par photolab.valeur.*",
      fusion and all(not any(str(v) in perim["valeurs"] and "blend" in (i.lower() for i in perim["valeurs"][str(v)]) for v in (c.get("valeurs") or [])) for c in fusion))

print("\n[4] noms de réglages et en-têtes de dialogues")
kinds = sorted(i[len("layer.newAdjustmentLayer."):] for i in REG if i.startswith("layer.newAdjustmentLayer."))
check("4.1 16 kinds de calques de réglage dans le registre", len(kinds) == 16, kinds)
manque = [k for k in kinds if not plein("photolab.kind." + k.lower())]
check("4.2 photolab.kind.<kind> fr+en pour chacun", not manque, manque)
extra = sorted(k[len("photolab.kind."):] for k in DIC if k.startswith("photolab.kind.") and k[len("photolab.kind."):] not in [k.lower() for k in kinds])
check("4.3 aucun photolab.kind.* hors des 16 kinds", not extra, extra)
entetes = ["photolab.reglages.onglet_proprietes", "photolab.reglages.onglet_reglages", "photolab.reglages.gamme",
           "photolab.courbes.titre", "photolab.courbes.canal", "photolab.courbes.entree", "photolab.courbes.sortie",
           "photolab.niveaux.titre", "photolab.niveaux.canal", "photolab.niveaux.entree", "photolab.niveaux.sortie",
           "photolab.canal.rvb", "photolab.canal.rouge", "photolab.canal.vert", "photolab.canal.bleu",
           "photolab.styles.options_fusion", "photolab.styles.non_relisible",
           "photolab.reglage.apercu", "photolab.reglage.ok", "photolab.reglage.annuler", "photolab.reglage.reinitialiser",
           "photolab.reglage.calcul", "photolab.reglage.erreur_apercu"]
manque = [k for k in entetes if not plein(k)]
check("4.4 en-têtes des dialogues fr+en", not manque, manque)
check("4.5 la mention des styles non relisibles est présente", DIC.get("photolab.styles.non_relisible", {}).get("fr", "").startswith("Paramètres non relisibles"))

print("\n[5] dictionnaire assemblé à jour")
for f in ASSEMBLES:
    txt = f.read_text(encoding="utf-8") if f.is_file() else ""
    cles = [k for k in DIC if k.startswith(("photolab.param.", "photolab.valeur.", "photolab.kind.", "photolab.canal.", "photolab.courbes.", "photolab.niveaux.", "photolab.styles.", "photolab.reglages."))]
    absentes = [k for k in cles if '"' + k + '"' not in txt]
    check(f"5.1 {f.relative_to(ROOT)} porte les {len(cles)} clés", f.is_file() and not absentes, absentes[:8])

print(f"\n=== {ok} passed, {fail} failed ===")
sys.exit(1 if fail else 0)
