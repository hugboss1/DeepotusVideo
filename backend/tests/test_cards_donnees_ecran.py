# -*- coding: utf-8 -*-
"""Card Forge — tâche #85 PR B à l'écran (plan-cartes T9, 04/10/2026) : le panneau « Statistiques du jeu » de la
pièce 04. DÉCISION DE L'UTILISATEUR (04/10) : un panneau, pas seulement la route. Les fonctions LIVRÉES sont
extraites de mod-data.js et EXÉCUTÉES sous node.
Témoin positif : la base (2014083f) n'a pas de statistiques.
Run (depuis backend/) : & $PY tests/test_cards_donnees_ecran.py"""
import sys as _sys_l7, pathlib as _pl_l7; _sys_l7.path.insert(0, str(_pl_l7.Path(__file__).resolve().parent))  # noqa: E401,E702
import _cartes_avant_l7  # noqa: F401,E402  (t147 : la source du Card Forge d'avant la traduction L7)
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
DATA = (RACINE / "frontend/cardforge/js/mod-data.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cfste_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "2014083f"
b = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-data.js"], capture_output=True, cwd=str(RACINE)).stdout
check("T1 témoin : la base n'a pas de statistiques", b and b"checkStats" not in b)
check("T2 les statistiques suivent chaque vérification (2 points) ; un bloc repliable dans le pied",
      DATA.count("    checkDos();\n    checkStats();") == 2 and 'const stats = h("details", "cf-data-stats", "");' in DATA
      and "REFS.stats = stats;" in DATA)


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


NOMS = ("checkStats", "nfr", "barres", "paintStats")
COUCHE = "\n".join(fonction(DATA, n) for n in NOMS)
check("T3 la couche livrée est extraite", all(fonction(DATA, n) for n in NOMS))

HARNAIS = r"""
var STATS = null, STSEQ = 0, APPELS = [], REP = {};
var T = {columns: ["nom", "img", "dos", "id", "atk", "qty"], rows: [["a", "a.png", "x", "1", "2", "3"]], off: [4],
         map: {img: "art", dos: "back", id: "id", nom: "title"}, qty_col: "qty"};
var esc = function (s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); };
var CL = {}; var REFS = {stats: {innerHTML: "", classList: {add: function (c) { CL[c] = true; }, remove: function (c) { CL[c] = false; }}}};
var M = {api: {post: async function (u, b) { APPELS.push([u, JSON.parse(JSON.stringify(b))]); if (REP.err) throw new Error(REP.err); return REP[u]; }}};
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
REP["stats"] = {total_cartes: 15, lignes: 5, qty_col: "qty", colonnes: [
  {nom: "atk", genre: "numerique", discret: true, n: 14, vides: 1, min: 1, max: 3, moyenne: 1.5714, mediane: 2,
   classes: [{de: 1, a: 1, n: 4}, {de: 2, a: 2, n: 2}, {de: 3, a: 3, n: 8}], note: ""},
  {nom: "poids", genre: "numerique", discret: false, n: 3, vides: 0, min: 0, max: 10.5, moyenne: 4.58, mediane: 3.25,
   classes: [{de: 0, a: 1.3125, n: 1}, {de: 1.3125, a: 2.625, n: 2}], note: "1 valeur(s) sur 4 ne sont pas des nombres"},
  {nom: "rare<té>", genre: "categoriel", n: 15, vides: 0, distinctes: 3, tronque: 2,
   valeurs: [{valeur: "commune", n: 7}, {valeur: "épique", n: 5}], note: ""}]};
await checkStats();
R.appel = APPELS[0]; R.html = REFS.stats.innerHTML; R.cache = CL.hidden;
REP.err = "500"; await checkStats(); R.panne = [REFS.stats.innerHTML, CL.hidden]; REP.err = null;
T.columns = []; APPELS = []; await checkStats(); R.vide = [APPELS.length, CL.hidden];
R.nfr = [nfr(4.5833), nfr(2), nfr(0.1 + 0.2)];
""")
check("S0 sous node : le panneau s'exécute", R is not None)
if R:
    check("S1 la table part avec les lignes écartées, la quantité, et SANS les colonnes d'images, de dos et d'identifiants",
          R["appel"] == ["stats", {"columns": ["nom", "img", "dos", "id", "atk", "qty"], "rows": [["a", "a.png", "x", "1", "2", "3"]],
                                   "off": [4], "qty_col": "qty", "skip": ["img", "dos", "id"]}], str(R["appel"]))
    h = R["html"]
    check("S2 l'en-tête dit les cartes, les lignes et la quantité appliquée ; le bloc paraît",
          "<summary>Statistiques du jeu — 15 carte(s) sur 5 ligne(s) (quantités de « qty » appliquées)</summary>" in h
          and R["cache"] is False, h[:200])
    check("S3 un numérique : n, min, max, moyenne, médiane à la virgule ; un entier : une barre par valeur, la plus haute à 100 %",
          "14 carte(s) · min 1 · max 3 · moyenne 1,57 · médiane 2 · 1 vide(s)" in h
          and '<span class="cf-data-stlab">3</span><span class="cf-data-stbar"><i style="width:100%"></i></span><span class="cf-data-stn">8</span>' in h
          and '<span class="cf-data-stlab">1</span><span class="cf-data-stbar"><i style="width:50%"></i></span>' in h, h)
    check("S4 des réels : des intervalles « de–à » ; la NOTE d'exclusion est dite",
          '<span class="cf-data-stlab">1,31–2,63</span>' in h and "1 valeur(s) sur 4 ne sont pas des nombres" in h, h)
    check("S5 une catégorie : valeurs, distinctes, non montrées ; le nom de colonne est ÉCHAPPÉ",
          "15 carte(s) · 3 valeur(s) distincte(s) · 2 autre(s) non montrée(s)" in h and "<b>rare&lt;té></b>" in h
          and '<span class="cf-data-stlab">commune</span>' in h, h)
    check("S6 une panne ou une table vide : le bloc se cache, rien d'inventé, aucun appel pour une table vide",
          R["panne"] == ["", True] and R["vide"] == [0, True], str(R["panne"]) + str(R["vide"]))
    check("S7 les nombres à la française, arrondis au centième", R["nfr"] == ["4,58", "2", "0,3"], str(R["nfr"]))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
