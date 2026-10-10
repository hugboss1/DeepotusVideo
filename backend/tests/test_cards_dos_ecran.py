# -*- coding: utf-8 -*-
"""Card Forge — tâche #85 PR A à l'écran (plan-cartes T8, 04/10/2026) : la ligne « Dos » de la pièce 04 et le bouton
« Mire recto-verso » de la pièce 07. Les fonctions LIVRÉES sont extraites et EXÉCUTÉES sous node.
Témoin positif : la base (5e837e61) n'a ni l'une ni l'autre.
Run (depuis backend/) : & $PY tests/test_cards_dos_ecran.py"""
import sys as _sys_l7, pathlib as _pl_l7; _sys_l7.path.insert(0, str(_pl_l7.Path(__file__).resolve().parent))  # noqa: E401,E702
import _cartes_avant_l7  # noqa: F401,E402  (t147 : la source du Card Forge d'avant la traduction L7)
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
DATA = (RACINE / "frontend/cardforge/js/mod-data.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
PRNT = (RACINE / "frontend/cardforge/js/mod-print.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cfdose_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "5e837e61"
b1 = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-data.js"], capture_output=True, cwd=str(RACINE)).stdout
b2 = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-print.js"], capture_output=True, cwd=str(RACINE)).stdout
check("T1 témoin : la base n'a ni la ligne Dos ni la mire", b1 and b2 and b"checkDos" not in b1 and b'data-act="mire"' not in b2)
check("T2 la ligne Dos suit chaque vérification d'illustration (2 points) ; le bouton mire est TITRÉ et câblé",
      DATA.count("    checkArt();\n    checkDos();") == 2 and "REFS.dosline = dosl;" in DATA
      and PRNT.count('data-act="mire" title="') == 1 and 'else if (a === "mire") exportMire();' in PRNT)


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


def bloc(src, debut, fin):
    k = src.find(debut)
    return src[k:src.find(fin, k) + len(fin)] if k >= 0 else ""


COUCHE = "\n".join([bloc(DATA, "const DOS_MOT = {", "};"), fonction(DATA, "backColumn"), fonction(DATA, "checkDos"),
                    fonction(DATA, "paintDos"), bloc(PRNT, "let MIREV = false;", ";"), fonction(PRNT, "exportMire")])
check("T3 la couche livrée est extraite", all(x in COUCHE for x in ("DOS_MOT", "function backColumn(", "function checkDos(",
                                                                     "function paintDos(", "function exportMire(")))

HARNAIS = r"""
var DOS = null, DOSSEQ = 0, APPELS = [], DL = [], TOASTS = [], REP = {}, SHEET = "letter";
var T = {columns: ["nom", "verso", "qty"], rows: [["a", "lattice", "2"]], off: [1], map: {verso: "back", nom: "title"}, qty_col: "qty"};
var esc = function (s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); };
var REFS = {dosline: {innerHTML: "", className: ""}};
var M = {api: {post: async function (u, b) { APPELS.push([u, JSON.parse(JSON.stringify(b))]); if (REP.err) throw new Error(REP.err); return REP[u]; },
               blob: async function (m, u) { APPELS.push([m, u]); return {size: 4321}; }}};
var CF = {busy: function () {}, toast: function (t, e) { TOASTS.push([t, !!e]); }, download: function (b, n) { DL.push(n); }};
function st() { return {sheet: SHEET}; } var LOG = []; function logLine(n, s, note) { LOG.push([n, s, note]); }
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
REP["dos"] = {colonne: "verso", total_cartes: 6, dos_commun: true, dos: [
  {valeur: "", cartes: 3, origine: "commun"}, {valeur: "lattice", cartes: 2, origine: "motif_ignore"},
  {valeur: "x<y", cartes: 1, origine: "introuvable"}],
  avertissements: ["1 carte(s) portent un dos qui n'est ni un motif…", "« Dos commun » est coché…"]};
await checkDos();
R.appel = APPELS[0]; R.html = REFS.dosline.innerHTML; R.cls = REFS.dosline.className;
REP["dos"] = {colonne: "verso", total_cartes: 2, dos_commun: false, dos: [{valeur: "lattice", cartes: 2, origine: "motif"}], avertissements: []};
await checkDos(); R.clsOk = REFS.dosline.className; R.htmlOk = REFS.dosline.innerHTML;
REP["dos"] = {colonne: "", total_cartes: 2, dos: [], avertissements: ["Aucune colonne « dos »"]};
await checkDos(); R.sans = REFS.dosline.innerHTML;
REP["dos"] = {colonne: "verso", total_cartes: 2, dos_commun: true, dos: [{valeur: "lattice", cartes: 2, origine: "motif_ignore"}], avertissements: []};
await checkDos(); R.clsIgnore = REFS.dosline.className;
REP.err = "500"; await checkDos(); R.panne = REFS.dosline.innerHTML; REP.err = null;
T.columns = []; APPELS = []; await checkDos(); R.vide = [APPELS.length, REFS.dosline.innerHTML];
""")
check("D0 sous node : la ligne Dos s'exécute", R is not None)
if R:
    check("D1 la table part avec ses lignes écartées, sa quantité et la colonne MAPPÉE sur « Dos »",
          R["appel"] == ["dos", {"columns": ["nom", "verso", "qty"], "rows": [["a", "lattice", "2"]], "off": [1],
                                 "back_col": "verso", "qty_col": "qty"}], str(R["appel"]))
    check("D2 la ligne dit chaque origine en mots (pièce 01 / 02), en cartes, ÉCHAPPÉE, et les avertissements ; rouge s'il y a perte",
          "Dos (colonne « verso ») — 6 carte(s)" in R["html"] and "lattice × 2 → motif ignoré — « dos commun » coché (pièce 02)" in R["html"]
          and "x&lt;y × 1 → introuvable — sortira avec le dos commun" in R["html"] and "— × 3 → dos commun" in R["html"]
          and R["html"].count('class="cf-data-dosav"') == 2 and R["cls"] == "cf-data-dosline bad", R["html"])
    check("D3 tout va bien : vert, motif du catalogue (pièce 02)", R["clsOk"] == "cf-data-dosline ok"
          and "motif du catalogue (pièce 02)" in R["htmlOk"], R["htmlOk"])
    check("D4 sans colonne de dos, une panne ou une table vide : la ligne se tait (rien d'inventé), sans appel pour une table vide",
          R["sans"] == "" and R["panne"] == "" and R["vide"] == [0, ""], str(R))
    check("D5 un motif IGNORÉ (« dos commun » coché) suffit à mettre la ligne en rouge", R["clsIgnore"] == "cf-data-dosline bad", R["clsIgnore"])

R = node("""
var p1 = exportMire(), p2 = exportMire(); await p1; await p2;
R.appels = APPELS.slice(); R.dl = DL.slice(); R.log = LOG[0]; R.toast = TOASTS[0];
SHEET = "card"; APPELS = []; DL = []; await exportMire(); R.carte = [APPELS[0][1], DL[0]];
""")
check("M0 sous node : la mire s'exécute", R is not None)
if R:
    check("M1 UNE demande au double clic, à la taille de la feuille choisie ; nommée, journalisée, et le toast dit comment imprimer",
          R["appels"] == [["GET", "mire?sheet=letter"]] and R["dl"] == ["mire_recto_verso_letter.pdf"]
          and "dixième de millimètre" in R["log"][2] and "recto-verso, à 100 %" in R["toast"][0], str(R))
    check("M2 « 1 carte / page » : la mire sort en A4", R["carte"] == ["mire?sheet=a4", "mire_recto_verso_a4.pdf"], str(R["carte"]))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
