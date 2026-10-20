# -*- coding: utf-8 -*-
"""t255 (Photolab M6, photocraft 0.10) — le panneau Actions : le pont et le VRAI moteur.
[1] liste blanche (PM.commande_autorisee) : les 15 commandes actions.* que l'écran lance passent avec ses paramètres ;
    formes refusées (nom vide ou trop long, rang négatif, couleur hors liste, `path` jamais admis, data non base64…) ;
    les 3 commandes qui ne sont que des ÉTAPES (stopMessage, conditional, photoshopStep) refusées seules ; Insérer
    vérifie l'étape posée comme une commande de l'écran (file.saveAs, prefs.*, commande 0.10 fermée, paramètres faux :
    refusés ; Arrêt, Exécuter l'action, Condition, Nouveau document : admis).
[2] réserve des actions (photolab_actions : valider, lire, ecrire) : forme stricte, bornes, fichier illisible = vide.
[3] VRAI moteur : une séquence interne du pont (vignettes, histogramme, repères) pendant un enregistrement ne
    s'enregistre PAS et l'enregistrement reprend ; la lecture est vérifiée EN PROFONDEUR (étape refusée posée dans le
    moteur, action appelée, condition) et refusée avant le moindre pas ; les étapes refusées sont éteintes à l'arrêt et
    à l'import ; un moteur relancé retrouve ses actions (réserve) ; export/import .atn en données ; Traitement par
    lots d'une image (document ouvert, action jouée, enregistré, refermé, document actif rendu).
Section VRAI moteur rouge si le binaire manque — jamais de saut silencieux.
Run : & $PY -X utf8 tests/test_photolab_m6.py   (depuis backend/)"""
import base64, json, os, pathlib, shutil, sys, tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzt255_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(_tmp / "images")
os.environ["OUTPUTS_FOLDER"] = str(_tmp / "outputs")
os.environ.setdefault("FAL_KEY", "test-key")
(_tmp / "images").mkdir(parents=True, exist_ok=True)
sys.stdout.reconfigure(encoding="utf-8")
BACKEND = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND))
sys.path.insert(0, str(BACKEND / "tests"))
from app.services import photolab_moteur as PM                # noqa: E402
from app.services import photolab_registre as PR              # noqa: E402
from app.services import photolab_neuves as PN                # noqa: E402
from app.services import photolab_actions as PA               # noqa: E402

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {str(detail)[:600]}")


def admise(reg, cid, params):
    try:
        PM.commande_autorisee(cid, params, reg)
        return True, ""
    except ValueError as e:
        return False, str(e)


REG = PR.structurer(json.loads((BACKEND / "tests" / "photocraft_commandes_0.10.0.json").read_text(encoding="utf-8")))
ACTIONS = sorted(i for i in REG if i.startswith("actions."))
print("[1] liste blanche")
check("1.0 les 18 commandes actions.* sont ouvertes (aucune dans photolab_neuves)",
      len(ACTIONS) == 18 and not (set(ACTIONS) & PN.COMMANDES_NEUVES_FERMEES), ACTIONS)
B64 = base64.b64encode(b"8BIM-donnees-atn").decode()
ADMIS = (
    ("actions.list", {}), ("actions.stop", {}),
    ("actions.get", {"action": "Mon action"}), ("actions.get", {"action": 0}),
    ("actions.record", {}), ("actions.record", {"name": "Vignette sépia"}), ("actions.record", {"action": 2}),
    ("actions.play", {"action": "A"}), ("actions.play", {"action": 1, "from": 3}),
    ("actions.delete", {"action": "A"}), ("actions.delete", {"action": "A", "step": 0}),
    ("actions.toggle", {"action": "A"}), ("actions.toggle", {"action": "A", "step": 2, "enabled": False}),
    ("actions.dialog", {"action": 0, "step": 1}), ("actions.dialog", {"action": "A", "enabled": True}),
    ("actions.rename", {"action": "A", "name": "B"}),
    ("actions.setColor", {"action": "A", "color": "violet"}), ("actions.setColor", {"action": "A", "color": ""}),
    ("actions.move", {"action": "A", "to": 0}), ("actions.move", {"action": "A", "step": 4, "to": 1}),
    ("actions.assignSet", {"action": "A", "set": "Mes actions"}), ("actions.assignSet", {"action": "A", "set": None}),
    ("actions.insert", {"action": "A", "id": "filter.blur.gaussianBlur", "params": {"radius": 4}}),
    ("actions.insert", {"action": "A", "id": "image.adjustments.invert", "at": 0}),
    ("actions.insert", {"action": "A", "id": "actions.stopMessage", "params": {"message": "Vérifie le cadrage", "allowContinue": True}}),
    ("actions.insert", {"action": "A", "id": "actions.play", "params": {"action": "B"}}),
    ("actions.insert", {"action": "A", "id": "actions.conditional", "params": {"if": "hasSelection", "then": "B", "else": None}}),
    ("actions.insert", {"action": "A", "id": "file.new", "params": {"width": 800, "height": 600, "background": "white"}}),
    ("actions.load", {"data": B64}), ("actions.load", {"data": B64, "set": "Importé", "replace": False}),
    ("actions.save", {}), ("actions.save", {"set": "Mes actions", "skipUnsupported": True}), ("actions.save", {"action": "A"}),
    # lecture pas à pas (segment), Condition jouée seule, Modifier l'étape (clés du pont)
    ("actions.play", {"action": "A", "from": 1, "until": 3}), ("actions.conditional", {"if": "always", "then": "A", "else": None}),
    ("actions.insert", {"action": "A", "id": "filter.blur.gaussianBlur", "params": {"radius": 2}, "at": 1, "replace": True}),
)
for cid, p in ADMIS:
    a, m = admise(REG, cid, p)
    check(f"1.1 admis : {cid} {json.dumps(p, ensure_ascii=False)[:70]}", a, m)
REFUS = (
    ("actions.get", {}, "requis"),
    ("actions.get", {"action": -1}, "rang"),
    ("actions.get", {"action": True}, "action"),
    ("actions.record", {"name": "  "}, "nom"),
    ("actions.record", {"name": "x" * 129}, "nom"),
    ("actions.record", {"name": "a\u0007b"}, "nom"),
    ("actions.record", {"name": "A", "action": 0}, "ensemble"),
    ("actions.play", {"action": "A", "from": -2}, "rang"),
    ("actions.play", {"action": "A", "from": 1.5}, "rang"),
    ("actions.delete", {"action": "A", "step": "1"}, "rang"),
    ("actions.toggle", {"action": "A", "enabled": "oui"}, "booléen"),
    ("actions.rename", {"action": "A"}, "requis"),
    ("actions.setColor", {"action": "A", "color": "pink"}, "couleur"),
    ("actions.move", {"action": "A"}, "requis"),
    ("actions.assignSet", {"action": "A"}, "requis"),
    ("actions.assignSet", {"action": "A", "set": ""}, "nom"),
    ("actions.load", {"path": "C:/Users/x.atn"}, "inconnu"),
    ("actions.load", {"data": "pas du base64 !"}, "base64"),
    ("actions.load", {"data": ""}, "base64"),
    ("actions.load", {"data": "A" * 3_000_000}, "base64"),
    ("actions.save", {"path": "sortie.atn"}, "inconnu"),
    ("actions.list", {"x": 1}, "inconnu"),
    ("actions.stopMessage", {"message": "hé"}, "étape"),
    ("actions.conditional", {"if": "toujours", "then": "A"}, "condition"),
    ("actions.play", {"action": "A", "from": 2, "until": 2}, "until"),
    ("actions.insert", {"action": "A", "id": "image.adjustments.invert", "replace": True}, "at"),
    ("actions.photoshopStep", {"event": "Xyz ", "name": "T"}, "étape"),
    ("actions.insert", {"action": "A", "id": "file.saveAs", "params": {"path": "x.png"}}, "réservée"),
    ("actions.insert", {"action": "A", "id": "prefs.set", "params": {}}, "réservée"),
    ("actions.insert", {"action": "A", "id": "swatches.add", "params": {}}, "pas encore ouverte"),
    ("actions.insert", {"action": "A", "id": "filter.blur.gaussianBlur", "params": {"radius": "abc"}}, "radius"),
    ("actions.insert", {"action": "A", "id": "foo.bar", "params": {}}, "inconnue"),
    ("actions.insert", {"action": "A", "id": "actions.photoshopStep", "params": {"event": "Abcd", "name": "T"}}, ".atn"),
    ("actions.insert", {"action": "A", "id": "actions.record", "params": {}}, "étape"),
    ("actions.insert", {"action": "A", "id": "actions.stopMessage", "params": {"message": ""}}, "message"),
    ("actions.insert", {"action": "A", "id": "actions.conditional", "params": {"if": "estJoli", "then": "B"}}, "condition"),
    ("actions.insert", {"action": "A", "id": "actions.play", "params": {"action": ""}}, "action"),
    ("actions.insert", {"action": "A", "id": "file.new", "params": {"path": "a.png"}}, "inconnu"),
    ("actions.insert", {"action": "A", "id": "image.adjustments.invert", "params": []}, "objet"),
    ("actions.insert", {"action": "A"}, "requis"),
)
for cid, p, attendu in REFUS:
    a, m = admise(REG, cid, p)
    check(f"1.2 refusé ({attendu}) : {cid} {json.dumps(p, ensure_ascii=False)[:60]}", not a and attendu.lower() in m.lower(), m)
# une étape de réglage : admise si UN type de réglage admet ses clés (le calque visé n'est connu qu'à la lecture)
r1 = PR.refus_etape(REG, "layer.setAdjustment", {"layer": 3, "brightness": 20})
r2 = PR.refus_etape(REG, "layer.setAdjustment", {"layer": 3, "zorglub": 1})
r3 = PR.refus_etape(REG, "layer.setAdjustment", {"layer": 3, "brightness": 20}, kind="levels")
check("1.3 étape layer.setAdjustment : admise sans kind connu si un type l'admet ; refusée sinon ; kind connu = ses clés",
      r1 is None and r2 is not None and r3 is not None, (r1, r2, r3))
check("1.4 refus_etape : None pour une étape admise, la raison sinon",
      PR.refus_etape(REG, "image.adjustments.invert", {}) is None
      and "réservée" in (PR.refus_etape(REG, "file.saveAs", {"path": "a.png"}) or "")
      and PR.refus_etape(REG, "actions.photoshopStep", {"event": "Abcd", "name": "T"}) is None, "")

print("[2] réserve des actions")
ACT = {"name": "Sépia", "set": "Mes actions", "color": "red", "steps": [["image.adjustments.invert", {}],
       ["actions.stopMessage", {"message": "ok", "allowContinue": True}]], "disabled": [1], "dialogs": [0]}
v = PA.valider({"version": 1, "actions": [ACT]})
check("2.1 valider garde une réserve juste", v["actions"][0] == ACT, v)
for mauvais, quoi in (({"version": 2, "actions": []}, "version"), ({"version": 1, "actions": [{**ACT, "name": ""}]}, "nom"),
                      ({"version": 1, "actions": [{**ACT, "zz": 1}]}, "clé"), ({"version": 1, "actions": [ACT, ACT]}, "doublon"),
                      ({"version": 1, "actions": [{**ACT, "disabled": [9]}]}, "rang"),
                      ({"version": 1, "actions": [{**ACT, "steps": [["x", {}]]}]}, "étape"),
                      ({"version": 1, "actions": [{**ACT, "color": "rose"}]}, "couleur")):
    try:
        PA.valider(mauvais); m = None
    except ValueError as e:
        m = str(e)
    check(f"2.2 valider refuse ({quoi})", m is not None, mauvais)
PA.ecrire({"version": 1, "actions": [ACT]})
check("2.3 ecrire puis lire rend la même réserve", PA.lire() == {"version": 1, "actions": [ACT]}, PA.lire())
PA.chemin().write_text("{pas du json", encoding="utf-8")
check("2.4 réserve illisible -> vide (jamais d'exception)", PA.lire() == {"version": 1, "actions": []}, PA.lire())
PA.chemin().unlink()

print("[3] VRAI moteur")
try:
    CLI = str(PM.chemin_cli())
    present = pathlib.Path(CLI).is_file()
except Exception as e:                                   # noqa: BLE001
    CLI, present = None, False
check("3.0 binaire du moteur présent (PHOTOCRAFT_CLI ou installation)", present, CLI)
if present:
    d = PM.dossier_travail()
    for sous in ("entrees", "exports", "rendus"):
        (d / sous).mkdir(parents=True, exist_ok=True)
    s = PM.SessionMoteur([CLI, "serve", "--automation-read-root", str(d), "--automation-write-root", str(d)])
    PM._SESSION = s
    reg = PM.registre(s)
    ex = lambda c, p=None: s.appeler("engine.execute", {"command": c, "params": p or {}})
    pa = lambda c, p=None: PA.executer(s, reg, c, p or {})[0]
    s.appeler("doc.new", {"width": 40, "height": 30})
    check("3.1 liste vide au départ (réserve vide)", pa("actions.list") == {"actions": [], "recording": None}, pa("actions.list"))
    pa("actions.record", {"name": "Inverser"})
    ex("image.adjustments.invert")
    PM.vignettes(s, 32); PM.histogramme(s, None, 32); PM.reperes(s)
    ex("select.all")
    r = pa("actions.stop")
    g = pa("actions.get", {"action": "Inverser"})
    check("3.2 vignettes / histogramme / repères pendant l'enregistrement : rien d'enregistré, l'enregistrement reprend",
          [e[0] for e in g["steps"]] == ["image.adjustments.invert", "select.all"], g)
    check("3.3 la réserve suit (enregistrée à l'arrêt)", [a["name"] for a in PA.lire()["actions"]] == ["Inverser"], PA.lire())
    h0 = s.appeler("doc.inspect")["history"]
    r = pa("actions.play", {"action": "Inverser"})
    h1 = s.appeler("doc.inspect")["history"]
    check("3.4 lecture : un état par étape jouée (Invert, Select All)", r.get("ran") == 2 and h1[len(h0):] == ["Invert", "Select All"],
          (r, h1[len(h0):]))
    # une étape refusée posée DANS le moteur (sans le pont) : la lecture refuse avant le moindre pas
    ex("actions.insert", {"action": "Inverser", "id": "file.saveAs", "params": {"path": "exports/x.png"}})
    try:
        pa("actions.play", {"action": "Inverser"}); m = None
    except ValueError as e:
        m = str(e)
    h2 = s.appeler("doc.inspect")["history"]
    check("3.5 lecture refusée (étape file.saveAs) sans aucun pas joué", m and "file.saveAs" in m and h2 == h1, (m, h2[len(h1):]))
    ex("actions.record", {"name": "Appelante"}); ex("actions.stop")
    ex("actions.insert", {"action": "Appelante", "id": "actions.play", "params": {"action": "Inverser"}})
    try:
        pa("actions.play", {"action": "Appelante"}); m = None
    except ValueError as e:
        m = str(e)
    check("3.6 refus EN PROFONDEUR : l'action appelée porte l'étape refusée", m and "Inverser" in m, m)
    ex("actions.record", {"name": "Cond"}); ex("actions.stop")
    ex("actions.insert", {"action": "Cond", "id": "actions.conditional", "params": {"if": "always", "then": "Inverser", "else": None}})
    try:
        pa("actions.play", {"action": "Cond"}); m = None
    except ValueError as e:
        m = str(e)
    check("3.7 refus en profondeur par une Condition", m and "Inverser" in m, m)
    ex("actions.toggle", {"action": "Inverser", "step": 2, "enabled": False})
    r = pa("actions.play", {"action": "Appelante"})
    check("3.8 l'étape refusée éteinte : la lecture passe", r.get("ran") == 1 and not r.get("failed"), r)
    try:
        pa("actions.toggle", {"action": "Inverser", "step": 2, "enabled": True}); m = None
    except ValueError as e:
        m = str(e)
    check("3.9 rallumer une étape refusée : refusé par le pont", m and "file.saveAs" in m, m)
    r = pa("actions.toggle", {"action": "Inverser"})
    g = pa("actions.get", {"action": "Inverser"})
    check("3.10 tout basculer : l'étape refusée reste éteinte", 2 in g["disabled"], (r, g))
    try:
        pa("actions.play", {"action": "Fantome"}); m = None
    except Exception as e:                               # noqa: BLE001
        m = str(e)
    check("3.11 action inconnue : erreur dite", m, m)
    # arrêt d'enregistrement : les étapes refusées enregistrées sont éteintes (Nouveau document admis)
    pa("actions.record", {"name": "AvecNouveau"})
    s.appeler("doc.new", {"width": 20, "height": 20})
    ex("image.adjustments.invert")
    r = pa("actions.stop")
    g = pa("actions.get", {"action": "AvecNouveau"})
    check("3.12 Nouveau document s'enregistre (file.new) et reste allumé", g["steps"][0][0] == "file.new" and g["disabled"] == [], g)
    s.appeler("doc.close", {"index": 1})
    # .atn : export en données puis import
    sv = pa("actions.save", {"action": "Inverser", "skipUnsupported": True})
    check("3.13 export .atn en données (base64, aucun chemin)", isinstance(sv.get("data"), str) and "path" not in sv, {k: v for k, v in sv.items() if k != "data"})
    ld = pa("actions.load", {"data": sv["data"], "set": "Importé"})
    nom = ld["actions"][0]
    g = pa("actions.get", {"action": nom})
    check("3.14 import .atn : l'action revient dans le jeu demandé", g["set"] == "Importé" and len(g["steps"]) >= 2, (ld, g))
    # import d'une action qui porte une étape refusée : éteinte à l'import
    ex("actions.record", {"name": "Ferme"}); ex("actions.stop")
    # file.revert : refusée par le pont (préfixe file.) mais exportable en .atn (relevé du 20/10)
    ex("actions.insert", {"action": "Ferme", "id": "file.revert", "params": {}})
    ex("actions.insert", {"action": "Ferme", "id": "image.adjustments.invert", "params": {}})
    sv2 = pa("actions.save", {"action": "Ferme", "skipUnsupported": True})
    ld2 = pa("actions.load", {"data": sv2["data"], "set": "Importé 2"})
    g2 = pa("actions.get", {"action": ld2["actions"][0]})
    check("3.15 import : l'étape que le pont refuse arrive éteinte, l'autre allumée, et la réponse le dit",
          sv2.get("steps") == 2 and g2["disabled"] == [0] and [e["step"] for e in ld2.get("eteintes", [])] == [0]
          and "file.revert" in ld2["eteintes"][0]["raison"], (sv2.get("skipped"), ld2, g2))
    ex("actions.delete", {"action": "Ferme"})
    ex("actions.delete", {"action": ld2["actions"][0]})
    # lecture pas à pas : un SEGMENT [from, until) ; l'Arrêt temporaire ne reste ni dans l'action ni dans la réserve
    pa("actions.record", {"name": "Seg"}); ex("image.adjustments.invert"); ex("select.all"); ex("image.adjustments.invert"); pa("actions.stop")
    av = pa("actions.get", {"action": "Seg"})
    h0 = s.appeler("doc.inspect")["history"]
    r = pa("actions.play", {"action": "Seg", "from": 0, "until": 2})
    h1 = s.appeler("doc.inspect")["history"]
    ap = pa("actions.get", {"action": "Seg"})
    check("3.21 segment [0, 2) : 2 étapes jouées, pas de « failed », 2 états", r.get("ran") == 2 and not r.get("failed")
          and h1[len(h0):] == ["Invert", "Select All"], (r, h1[len(h0):]))
    check("3.22 … l'action et la réserve sont intactes (aucun Arrêt temporaire)", ap == av
          and next(a for a in PA.lire()["actions"] if a["name"] == "Seg")["steps"] == av["steps"], (av, ap))
    r = pa("actions.play", {"action": "Seg", "from": 2, "until": 9})
    check("3.23 segment jusqu'au bout (until ≥ nombre d'étapes) : la fin se joue", r.get("ran") == 1, r)
    pa("actions.toggle", {"action": "Seg", "step": 1, "enabled": False})
    pa("actions.dialog", {"action": "Seg", "step": 1, "enabled": True})
    pa("actions.insert", {"action": "Seg", "id": "filter.blur.gaussianBlur", "params": {"radius": 3}, "at": 1, "replace": True})
    g = pa("actions.get", {"action": "Seg"})
    check("3.24 Modifier l'étape : remplacée à sa place, éteinte et dialogue gardés",
          [e[0] for e in g["steps"]] == ["image.adjustments.invert", "filter.blur.gaussianBlur", "image.adjustments.invert"]
          and g["steps"][1][1] == {"radius": 3} and g["disabled"] == [1] and g["dialogs"] == [1], g)
    ex("actions.record", {"name": "Piege"}); ex("actions.stop")
    ex("actions.insert", {"action": "Piege", "id": "file.saveAs", "params": {"path": "exports/p.png"}})
    h0 = s.appeler("doc.inspect")["history"]
    try:
        pa("actions.conditional", {"if": "always", "then": "Piege", "else": None}); m = None
    except ValueError as e:
        m = str(e)
    check("3.25 Condition jouée seule : l'action visée est vérifiée en profondeur, rien n'est joué",
          m and "Piege" in m and "file.saveAs" in m and s.appeler("doc.inspect")["history"] == h0, m)
    ex("actions.delete", {"action": "Piege"})
    r = pa("actions.conditional", {"if": "never", "then": None, "else": "Seg"})
    check("3.26 Condition jouée seule : la branche « sinon » joue", r.get("holds") is False and r.get("played") == "Seg", r)
    cp = PA.dupliquer(s, reg, "Seg", "Seg copie")[0]
    check("3.27 Dupliquer : étapes, éteintes, dialogues copiés ; réserve à jour", cp["steps"] == g["steps"] and cp["disabled"] == [1]
          and cp["dialogs"] == [1] and "Seg copie" in [a["name"] for a in PA.lire()["actions"]], cp)
    pa("actions.delete", {"action": "Seg copie"})
    PA.sauver(s)
    noms = [a["name"] for a in pa("actions.list")["actions"]]
    # moteur relancé : la réserve rend les actions (étapes, éteintes, dialogues, couleur, jeu)
    pa("actions.setColor", {"action": "Inverser", "color": "green"})
    pa("actions.dialog", {"action": "Inverser", "step": 0})
    pa("actions.assignSet", {"action": "Inverser", "set": "Mes actions"})
    avant = {a["name"]: a for a in PA.lire()["actions"]}
    s.fermer()
    apres_l = pa("actions.list")
    apres = {a["name"]: pa("actions.get", {"action": a["name"]}) for a in apres_l["actions"]}
    check("3.16 moteur relancé : mêmes actions dans le même ordre", [a["name"] for a in apres_l["actions"]] == noms, (noms, apres_l))
    check("3.17 … étapes, éteintes, dialogues, couleur et jeu restaurés",
          all(apres[n]["steps"] == avant[n]["steps"] and apres[n]["disabled"] == avant[n]["disabled"]
              and apres[n]["dialogs"] == avant[n]["dialogs"] and apres[n]["color"] == avant[n]["color"]
              and apres[n]["set"] == avant[n]["set"] for n in avant), (avant.get("Inverser"), apres.get("Inverser")))
    # Traitement par lots : une image, ouverte, action jouée, enregistrée, refermée, document actif rendu
    from PIL import Image
    s.appeler("doc.new", {"width": 16, "height": 16})
    Image.new("RGB", (12, 8), (255, 0, 0)).save(d / "entrees" / "lot.png")
    n0 = len(s.appeler("session.list")["documents"])
    actif0 = s.appeler("session.list")["active"]
    pa("actions.toggle", {"action": "Inverser", "step": 1, "enabled": False})       # pas de « Tout sélectionner »
    sortie = PA.lot_une(s, reg, "Inverser", "entrees/lot.png", "lot-sortie", "png", None)[0]
    sl = s.appeler("session.list")
    px = Image.open(d / "exports" / sortie).convert("RGB").getpixel((0, 0)) if (d / "exports" / sortie).is_file() else None
    check("3.18 lot : fichier écrit sous exports/, pixels traités par l'action (rouge inversé = cyan)", px == (0, 255, 255), (sortie, px))
    check("3.19 lot : le document ouvert est refermé, l'actif rendu", len(sl["documents"]) == n0 and sl["active"] == actif0, sl)
    pa("actions.record", {"name": "LotRefus"}); pa("actions.stop")
    ex("actions.insert", {"action": "LotRefus", "id": "prefs.set", "params": {}}) if "prefs.set" in reg else None
    ex("actions.insert", {"action": "LotRefus", "id": "file.saveAs", "params": {"path": "exports/y.png"}})
    try:
        PA.lot_une(s, reg, "LotRefus", "entrees/lot.png", "lot-refus", "png", None); m = None
    except ValueError as e:
        m = str(e)
    sl2 = s.appeler("session.list")
    check("3.20 lot : action refusée -> rien n'est ouvert ni écrit", m and len(sl2["documents"]) == n0
          and not (d / "exports" / "lot-refus.png").exists(), (m, sl2))
    s.fermer(definitif=True)
    PM._SESSION = None

    print("[4] routes")
    import asyncio

    async def routes():
        import httpx
        from app.main import app
        Image.new("RGB", (10, 6), (255, 0, 0)).save(_tmp / "images" / "rouge-lot.png")
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, client=("127.0.0.1", 5000)), base_url="http://t") as c:
            r = await c.get("/api/photolab/actions")
            j = r.json()
            check("4.1 GET /actions : un moteur neuf reçoit la réserve (mêmes actions)", r.status_code == 200
                  and [a["name"] for a in j["actions"]] == [a["name"] for a in PA.lire()["actions"]] and j["recording"] is None,
                  (r.status_code, r.text[:300]))
            r = await c.post("/api/photolab/executer", json={"command": "actions.insert",
                             "params": {"action": "Inverser", "id": "file.saveAs", "params": {"path": "x.png"}}})
            check("4.2 /executer Insérer une étape refusée : 400 qui dit pourquoi", r.status_code == 400 and "file.saveAs" in r.text, r.text)
            r = await c.post("/api/photolab/executer", json={"command": "actions.load", "params": {"path": "a.atn"}})
            check("4.3 /executer actions.load avec un chemin : 400", r.status_code == 400 and "path" in r.text, r.text)
            r = await c.post("/api/photolab/executer", json={"command": "actions.stopMessage", "params": {"message": "x"}})
            check("4.4 /executer une étape seule (Arrêt) : 400", r.status_code == 400, r.text)
            from app.services import library_index as LI
            notes = []

            async def noter(files, source, **kw):
                notes.append((list(files), source, kw.get("parent"), kw.get("relation")))
            LI.noter, noter0 = noter, LI.noter
            r = await c.post("/api/photolab/actions/lot", json={"action": "Inverser", "filename": "rouge-lot.png", "format": "png",
                                                                  "suffixe": "inverse"})
            LI.noter = noter0
            nom = r.json().get("filename", "") if r.status_code == 200 else ""
            f = _tmp / "images" / nom
            px = Image.open(f).convert("RGB").getpixel((0, 0)) if nom and f.is_file() else None
            check("4.5 /actions/lot : l'image traitée arrive dans la Bibliothèque (photolab_…_rouge-lot-inverse.png, cyan)",
                  r.status_code == 200 and nom.startswith("photolab_") and nom.endswith("_rouge-lot-inverse.png") and px == (0, 255, 255),
                  (r.status_code, r.text, px))
            check("4.6 /actions/lot : noté « photolab », lignée vers l'image d'origine (retouche)",
                  notes == [([nom], "photolab", "rouge-lot.png", "retouche")], notes)
            for corps, quoi in (({"action": "Inverser", "filename": "../x.png"}, "nom"),
                                ({"action": "Inverser", "filename": "rouge-lot.png", "format": "tif"}, "format"),
                                ({"action": "Inverser", "filename": "rouge-lot.png", "path": "a"}, "inconnu"),
                                ({"action": "Inverser", "filename": "absente.png"}, "absente"),
                                ({"action": "", "filename": "rouge-lot.png"}, "action")):
                r = await c.post("/api/photolab/actions/lot", json=corps)
                check(f"4.7 /actions/lot refusé ({quoi}) : 4xx, jamais un 500", 400 <= r.status_code < 500, (r.status_code, r.text))
        PM.fermer()
    asyncio.run(routes())

print(f"\n=== {ok} passed, {fail} failed ===")
shutil.rmtree(_tmp, ignore_errors=True)
sys.exit(1 if fail else 0)
