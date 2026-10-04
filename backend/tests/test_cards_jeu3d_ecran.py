# -*- coding: utf-8 -*-
"""Card Forge — tâche #87 PR B à l'écran (plan-cartes T16-T17, 04/10/2026) : « Objets du jeu » dans la pièce 09.
DÉCISIONS DE L'UTILISATEUR (04/10) : hors du graphe ; jeton en relief de la carte ; vraie tuck box en PDF.
Les fonctions LIVRÉES sont extraites de mod-forge3d.js et EXÉCUTÉES sous node (aucun appel réel).
Témoin positif : la base (21e9efcd) n'a pas d'objets du jeu.
Run (depuis backend/) : & $PY tests/test_cards_jeu3d_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
SRC = (RACINE / "frontend/cardforge/js/mod-forge3d.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cfjeue_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "21e9efcd"
b = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-forge3d.js"], capture_output=True, cwd=str(RACINE)).stdout
check("E1 témoin : la base n'a pas d'objets du jeu", b and b"objetDuJeu" not in b)
boutons = [l for l in SRC.split("\n") if "data-jeu=" in l and "<button" in l]
check("E2 cinq boutons, chacun TITRÉ ; la feuille est un choix titré ; le clic est câblé ; le graphe n'est pas touché",
      len(boutons) == 5 and all('title="' in l for l in boutons) and 'id="cf-forge3d-jeu-feuille" title="' in SRC
      and 'if (o === "boite") boiteDepliee(); else objetDuJeu(o);' in SRC
      and '"jeton"' not in SRC[SRC.find("CF-FORGE3D-NODES-BEGIN"):SRC.find("CF-FORGE3D-NODES-END")], str(boutons))


def fonction(src, nom):
    k = src.find("function " + nom + "(")
    if k < 0:
        return ""
    i, prof, ch, vu = src.find("{", src.find(")", k)), 0, None, False
    while i < len(src):
        c_ = src[i]
        if ch:
            if c_ == "\\": i += 2; continue
            if c_ == ch: ch = None
        elif src.startswith("/*", i):
            i = src.find("*/", i) + 2; continue
        elif src.startswith("//", i) and src[i - 1] != ":":
            i = src.find("\n", i); continue
        elif c_ in "\"'`": ch = c_
        elif c_ == "{": prof += 1; vu = True
        elif c_ == "}":
            prof -= 1
            if vu and prof == 0: return src[k - 6 if src[k - 6:k] == "async " else k:i + 1]
        i += 1
    return ""


NOMS = ("jeuStatut", "objetDuJeu", "boiteDepliee")
COUCHE = "\n".join(fonction(SRC, n) for n in NOMS)
check("E3 la couche livrée est extraite", COUCHE.count("function ") >= 3)

HARNAIS = r"""
var JEUV = false;
var APPELS = [], DIAL = [], SAISIE = "25", CONF = false, TOASTS = [], REP = {}, ERR = {}, DL = [], OPEN = [], STATUT = {textContent: ""}, CUR = 2;
class FormData { constructor() { this.e = []; } append(k, v, n) { this.e.push([k, typeof v === "string" ? v : "<blob " + (n || "") + ">"]); } }
var SEL = {value: "a3"};
function $(s) { return s === "#cf-forge3d-jeu-status" ? STATUT : (s === "#cf-forge3d-jeu-feuille" ? SEL : null); }
var window = {__dzDialogue: {saisir: async function (m, o) { DIAL.push(["saisir", m, o]); return SAISIE; },
                             confirmer: async function (m, o) { DIAL.push(["confirmer", m, o]); return CONF; }}};
var CF = {doc: function () { return {name: "Mon jeu"}; }, current: function () { return CUR; }, cards: function () { return new Array(54); },
          cardBlob: async function (i, o) { APPELS.push(["cardBlob", i, o.face]); return {blob: i}; },
          print3d: {open: async function (d) { OPEN.push(d); }}};
var M = {toast: function (t, e) { TOASTS.push([t, !!e]); }, download: function (b, n) { DL.push([b, n]); },
         api: {post: async function (u, b) { APPELS.push([u, b.e ? b.e : b]); await new Promise(function (s) { setTimeout(s, 5); });
                                            if (ERR[u]) throw new Error(ERR[u]); return REP[u]; },
               blob: async function (m, u, b) { APPELS.push([m + " " + u, b]); if (ERR[u]) throw new Error(ERR[u]); return {pdf: true}; }}};
REP["jeu"] = {dossier: "mon-jeu-jeton-20261004", triangles: 256, avertissement: ""};
"""


def node(corps):
    f = _TMP / f"m{abs(hash(corps)) % 10**9}.js"
    f.write_text(COUCHE + "\n" + HARNAIS + "\n(async function(){var R={};" + corps + "\nconsole.log(JSON.stringify(R));process.exit(0)})()", encoding="utf-8")
    p = subprocess.run(["node", str(f)], capture_output=True, text=True, encoding="utf-8", timeout=60)
    try:
        return json.loads(p.stdout.strip().splitlines()[-1])
    except Exception:
        print("   (node)", (p.stderr or p.stdout)[-800:])
        return None


R = node("""
var p1 = objetDuJeu("jeton"), p2 = objetDuJeu("jeton"); await p1; await p2;
R.jeton = APPELS.slice(); R.dial = DIAL.slice(); R.statut = STATUT.textContent; R.open = OPEN.slice(); R.v = JEUV;
APPELS = []; DIAL = []; CONF = true; SAISIE = "30"; await objetDuJeu("jeton_relief"); R.relief = APPELS.slice(); R.open2 = OPEN.slice();
APPELS = []; DIAL = []; await objetDuJeu("presentoir"); R.pres = [APPELS.slice(), DIAL.map(function (d) { return d[0]; })];
APPELS = []; DIAL = []; SAISIE = null; var nt = TOASTS.length; await objetDuJeu("jeton"); R.annule = [APPELS.length, JEUV, TOASTS.length - nt];
APPELS = []; SAISIE = "abc"; await objetDuJeu("jeton"); R.mauvais = [APPELS.length, TOASTS[TOASTS.length - 1]];
APPELS = []; SAISIE = "25"; ERR["jeu"] = "400 Le diamètre du jeton doit tenir entre 5 et 300 mm"; await objetDuJeu("jeton");
R.err = [TOASTS[TOASTS.length - 1], JEUV, STATUT.textContent];
""")
check("J0 sous node : les objets s'exécutent", R is not None)
if R:
    check("J1 UN appel au double clic : le diamètre est demandé, l'objet part en FormData (objet, params, nom)",
          [a[0] for a in R["jeton"]] == ["jeu"] and R["jeton"][0][1] == [["objet", "jeton"], ["params", "{\"diam_mm\":25}"], ["nom", "Mon jeu jeton"]]
          and R["dial"][0][0] == "saisir" and "Diamètre" in R["dial"][0][1] and R["v"] is False, str(R["jeton"]))
    check("J2 le bilan est dit (dossier, triangles) et le slicer n'ouvre que sur un OUI",
          R["statut"] == "mon-jeu-jeton-20261004 · 256 triangles" and R["open"] == [] and R["dial"][1][0] == "confirmer"
          and "Imprimante 3D" in R["dial"][1][1], str(R))
    check("J3 le relief : la carte COURANTE est rendue (face avant) et jointe ; le slicer s'ouvre sur un oui",
          R["relief"][0] == ["cardBlob", 2, "front"] and R["relief"][1][1][3] == ["image", "<blob carte.png>"]
          and R["relief"][1][1][1] == ["params", "{\"diam_mm\":30}"] and R["open2"] == ["mon-jeu-jeton-20261004"], str(R["relief"]))
    check("J4 le présentoir ne demande rien (largeur et rainure lues du jeu par le serveur)",
          R["pres"][0][0][1][1] == ["params", "{}"] and R["pres"][1] == ["confirmer"], str(R["pres"]))
    check("J5 annuler la saisie : rien ne part, le verrou est rendu ; un diamètre illisible est dit sans appel",
          R["annule"] == [0, False, 0] and R["mauvais"][0] == 0 and "invalide" in R["mauvais"][1][0], str(R))
    check("J6 un refus du serveur est dit, le statut effacé, le verrou rendu",
          "300 mm" in R["err"][0][0] and R["err"][0][1] is True and R["err"][1] is False and R["err"][2] == "", str(R["err"]))

R = node("""
SAISIE = "54"; await boiteDepliee(); R.boite = [APPELS.slice(), DL.slice(), DIAL[0][2].valeur, STATUT.textContent];
APPELS = []; DIAL = []; SAISIE = "0"; await boiteDepliee(); R.zero = [APPELS.length, TOASTS[TOASTS.length - 1]];
APPELS = []; SAISIE = null; await boiteDepliee(); R.annule = APPELS.length;
SAISIE = "400"; ERR["boite"] = "400 aucune feuille ne convient"; await boiteDepliee(); R.err = [TOASTS[TOASTS.length - 1], JEUV];
""")
check("B0 sous node : la boîte s'exécute", R is not None)
if R:
    check("B1 la boîte : le nombre de cartes proposé est celui du jeu, la feuille choisie part, le PDF se télécharge",
          R["boite"][0] == [["POST boite", {"cartes": 54, "feuille": "a3"}]] and R["boite"][1] == [[{"pdf": True}, "boite-54-cartes.pdf"]]
          and R["boite"][2] == "54" and "pointillé = plier" in R["boite"][3], str(R["boite"]))
    check("B2 un nombre hors bornes est dit sans appel ; annuler ne fait rien",
          R["zero"][0] == 0 and "1 à 1000" in R["zero"][1][0] and R["annule"] == 0, str(R))
    check("B3 un refus du serveur (feuille) est dit, verrou rendu", "aucune feuille" in R["err"][0][0] and R["err"][1] is False, str(R["err"]))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
