# -*- coding: utf-8 -*-
"""Card Forge — tâche #87 PR C à l'écran (plan-cartes T18-T19, 04/10/2026) : livret, mockup et fiche dans la pièce 11.
L'écart du livret (texte en image à 300 DPI) est DIT à l'écran ; le rendu 3D est renvoyé à la pièce 05.
Les fonctions LIVRÉES sont extraites de mod-edition.js et EXÉCUTÉES sous node (aucun appel réel).
Témoin positif : la base (21ce8994) n'a pas de livret.
Run (depuis backend/) : & $PY tests/test_cards_livret_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
SRC = (RACINE / "frontend/cardforge/js/mod-edition.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cflivrete_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "21ce8994"
b = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-edition.js"], capture_output=True, cwd=str(RACINE)).stdout
check("E1 témoin : la base n'a pas de livret", b and b"livretPdf" not in b)
boutons = [l for l in SRC.split("\n") if "<button" in l and ('data-act="livret"' in l or 'data-act="mockup"' in l or 'data-act="fiche"' in l)]
check("E2 l'écart est écrit À L'ÉCRAN (300 DPI, pas sélectionnable, pour l'impression) ; le 3D renvoyé à la pièce 05 ; boutons titrés et câblés",
      "texte n’est pas sélectionnable" in SRC and "<b>300 DPI</b>" in SRC and "<b>pour l’impression</b>" in SRC
      and "pièce 05 (Volume)" in SRC and len(boutons) == 3 and all('title="' in l for l in boutons)
      and 'else if (t.dataset.act === "livret") livretPdf();' in SRC and "if (el) reglage(el);" in SRC
      and all(k in SRC for k in ('livret_texte: ""', 'mockup_cible: "carre"')), str(boutons))


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


NOMS = ("ed", "etatDe", "reglage", "slugJeu", "livretPdf", "mockupPng", "ficheProduit", "paintFiche")
COUCHE = "\n".join(fonction(SRC, n) for n in NOMS)
k0 = SRC.find("  const DEFAULTS = {")
COUCHE = SRC[k0:SRC.find("};", k0) + 2] + "\n" + COUCHE
check("E3 la couche livrée est extraite", COUCHE.count("function ") >= len(NOMS), str([n for n in NOMS if not fonction(SRC, n)]))

HARNAIS = r"""
var VERROU = false, POLICES = [], FICHE = null;
var esc = function (s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;"); };
var ROLES = {}; var HOST = {querySelector: function (s) { var m = /data-role="([^"]+)"/.exec(s); if (!m) return null;
  return ROLES[m[1]] || (ROLES[m[1]] = {textContent: "", innerHTML: ""}); }};
var EDITION = {}, NCARTES = 7;
var APPELS = [], TOASTS = [], DL = [], PATCH = [], BUSY = [], ERR = {}, REP = {};
class FormData { constructor() { this.e = []; } append(k, v, n) { this.e.push([k, typeof v === "string" ? v : "<blob " + n + ">"]); } }
var CF = {doc: function () { return {name: "Mon Jeu Été", edition: EDITION}; }, cards: function () { return new Array(NCARTES); },
          cardBlob: async function (i, o) { APPELS.push(["cardBlob", i, o.face]); return {}; },
          download: function (b, n) { DL.push(n); }, busy: function (on) { BUSY.push(!!on); }, toast: function (t, e) { TOASTS.push([t, !!e]); }};
var M = {patch: function (o) { PATCH.push(o); Object.assign(EDITION, o); },
         api: {blob: async function (m, u, b) { APPELS.push([m + " " + u, b.e]); await new Promise(function (s) { setTimeout(s, 5); });
                                                 if (ERR[u]) throw new Error(ERR[u]); return {}; },
               post: async function (u, b) { APPELS.push([u, b]); if (ERR[u]) throw new Error(ERR[u]); return REP[u]; }}};
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
await livretPdf(); R.vide = [APPELS.length, TOASTS[0]];
EDITION.livret_texte = "# But\\nGagner."; EDITION.livret_feuille = "a4"; EDITION.livret_fonte = "Cinzel.ttf";
var p1 = livretPdf(), p2 = livretPdf(); await p1; await p2;
R.livret = APPELS.slice(); R.dl = DL.slice(); R.etat = ROLES["livret-etat"].textContent; R.v = VERROU; R.busy = BUSY[BUSY.length - 1];
APPELS = []; EDITION.livret_planche = false; await livretPdf(); R.sans = APPELS.map(function (a) { return a[0]; });
APPELS = []; TOASTS = []; ERR["livret"] = "400 Feuille inconnue"; await livretPdf(); R.err = [TOASTS[0], VERROU];
""")
check("L0 sous node : le livret s'exécute", R is not None)
if R:
    check("L1 sans texte : dit, rien ne part", R["vide"][0] == 0 and "texte des règles" in R["vide"][1][0], str(R["vide"]))
    spec = json.loads(R["livret"][-1][1][0][1]) if R["livret"] else {}
    check("L2 UN livret au double clic : titre (le nom du jeu), texte, feuille, fonte ; la planche rend les 7 cartes recto",
          [a[0] for a in R["livret"]].count("POST livret") == 1 and [a[0] for a in R["livret"]].count("cardBlob") == 7
          and R["livret"][0][2] == "front" and spec == {"titre": "Mon Jeu Été", "texte": "# But\nGagner.", "feuille": "a4", "fonte": "Cinzel.ttf"}
          and len(R["livret"][-1][1]) == 8, str(R["livret"][-1]))
    check("L3 le fichier se télécharge sous le nom du jeu ; l'état dit la planche et le 300 DPI ; verrou et attente rendus",
          R["dl"] == ["mon-jeu-ete_livret.pdf"] and "planche de 7 carte(s)" in R["etat"] and "300 DPI" in R["etat"]
          and R["v"] is False and R["busy"] is False, str(R))
    check("L4 sans planche : aucune carte rendue", R["sans"] == ["POST livret"], str(R["sans"]))
    check("L5 un refus du serveur est dit, verrou rendu", "Feuille inconnue" in R["err"][0][0] and R["err"][0][1] is True and R["err"][1] is False, str(R["err"]))

R = node("""
EDITION.mockup_cible = "story"; EDITION.mockup_sous_titre = "60 cartes";
await mockupPng(); R.m = APPELS.slice(); R.dl = DL.slice(); R.etat = ROLES["mockup-etat"].textContent;
APPELS = []; NCARTES = 0; await mockupPng(); R.zero = [APPELS.length, TOASTS[TOASTS.length - 1]]; NCARTES = 3;
APPELS = []; DL = []; await mockupPng(); R.trois = [APPELS.filter(function (a) { return a[0] === "cardBlob"; }).length, ROLES["mockup-etat"].textContent];
""")
check("M0 sous node : le mockup s'exécute", R is not None)
if R:
    spec = json.loads(R["m"][-1][1][0][1])
    check("M1 cinq cartes au plus (les premières), la cible, le titre par défaut, le sous-titre ; l'état le dit",
          [a[0] for a in R["m"]].count("cardBlob") == 5 and spec["cible"] == "story" and spec["titre"] == "Mon Jeu Été"
          and spec["sous_titre"] == "60 cartes" and R["dl"] == ["mon-jeu-ete_mockup_story.png"]
          and "les 5 premières sur 7" in R["etat"], str(R))
    check("M2 sans carte : dit, rien ne part ; trois cartes : trois rendues, sans « premières »",
          R["zero"][0] == 0 and "Aucune carte" in R["zero"][1][0] and R["trois"][0] == 3 and "premières" not in R["trois"][1], str(R))

R = node("""
REP["fiche"] = {cartes: 7, format: "Poker <US>", dimensions_mm: [63.5, 88.9], epaisseur_deck_mm: 2.24, epaisseur_carte_mm: 0.32,
                boite_mm: [64.5, 89.9, 3.24], langues: [], texte: "7 cartes <b>"};
await ficheProduit(); R.appel = APPELS[0]; R.html = ROLES["fiche"].innerHTML;
REP["fiche"].langues = ["français", "anglais"]; REP["fiche"].boite_mm = null; await ficheProduit(); R.html2 = ROLES["fiche"].innerHTML;
var e = {getAttribute: function () { return "livret_planche"; }, type: "checkbox", checked: false}; reglage(e);
var e2 = {getAttribute: function () { return "pirate"; }, type: "text", value: "x"}; reglage(e2); R.patch = PATCH.slice();
""")
check("F0 sous node : la fiche s'exécute", R is not None)
if R:
    check("F1 la fiche part avec le nombre de cartes du jeu ; chiffres en virgule française, ÉCHAPPÉS ; langues absentes dites",
          R["appel"] == ["fiche", {"cartes": 7}] and "Poker &lt;US&gt; — 63,5 x 88,9 mm" in R["html"] and "2,24 mm (0,32 mm par carte, pièce 05)" in R["html"]
          and "64,5 x 89,9 x 3,24 mm" in R["html"] and "non précisées" in R["html"] and "7 cartes &lt;b&gt;" in R["html"]
          and "readonly" in R["html"], R["html"])
    check("F2 langues nommées, boîte absente dite « — »", "français, anglais" in R["html2"] and "<th>Boîte</th><td>—</td>" in R["html2"], R["html2"])
    check("F3 un réglage s'enregistre dans le sous-arbre de la pièce ; une clé hors schéma est ignorée",
          R["patch"] == [{"livret_planche": False}], str(R["patch"]))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
