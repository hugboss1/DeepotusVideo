# -*- coding: utf-8 -*-
"""Card Forge — tâche #85 PR C à l'écran (plan-cartes T11, 04/10/2026) : « Lien Google Sheets… » et l'export Notion
déposé dans l'import existant. Les fonctions LIVRÉES sont extraites de mod-data.js et EXÉCUTÉES sous node.
Témoin positif : la base (6f77e3a3) n'a ni bouton Sheets ni .zip accepté.
Run (depuis backend/) : & $PY tests/test_cards_imports_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
DATA = (RACINE / "frontend/cardforge/js/mod-data.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cfimpe_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "6f77e3a3"
b = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-data.js"], capture_output=True, cwd=str(RACINE)).stdout
check("T1 témoin : la base n'a ni bouton Sheets ni .zip accepté", b and b"importSheets" not in b and b".ods,.zip" not in b)
check("T2 l'import accepte le .zip et le DIT ; le bouton Sheets paraît dans les deux états du panneau, TITRÉ",
      '.ods,.zip,application/zip,text/csv,' in DATA and "ou un export Notion (.zip)</b>" in DATA
      and DATA.count("boutonSheets()") == 3 and 'b.title = "Importer une feuille Google Sheets partagée' in DATA)
check("T3 une archive (classeur OU export Notion) n'est pas comparée octet à octet comme un CSV, et la raison le dit",
      "wb: !!(tb.workbook || tb.archive)," in DATA and "l'entrée est une archive (classeur ou export Notion)" in DATA)


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


COUCHE = "\n".join(fonction(DATA, n) for n in ("b64bytes", "importSheets"))
check("T4 la couche livrée est extraite", "function importSheets(" in COUCHE and "function b64bytes(" in COUCHE)

HARNAIS = r"""
var SHEETSV = false, LASTRAW = null, APPELS = [], IMPORTS = [], TOASTS = [], REP = null, ERR = null, SAISI = "https://docs.google.com/x", DIAL = [];
var window = {__dzDialogue: {saisir: async function (m, o) { DIAL.push([m, o]); return SAISI; }}};
var M = {busy: function () {}, toast: function (t, e) { TOASTS.push([t, !!e]); },
         api: {post: async function (u, b) { APPELS.push([u, b]); await new Promise(function (s) { setTimeout(s, 5); }); if (ERR) throw new Error(ERR); return REP; }}};
async function importBytes(buf, nom, o) { IMPORTS.push([Array.from(new Uint8Array(buf)), nom, o]); }
var atob = function (s) { return Buffer.from(s, "base64").toString("binary"); };
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
REP = {b64: Buffer.from("Nom,Coût\\nGobelin,2\\n", "utf-8").toString("base64"), nom: "Mon jeu - Cartes.csv"};
SAISI = "  https://docs.google.com/spreadsheets/d/x/edit  ";
var p1 = importSheets(), p2 = importSheets(); await p1; await p2;
R.dial = DIAL.slice(); R.appels = APPELS.slice(); R.imp = IMPORTS.slice(); R.raw = Array.from(new Uint8Array(LASTRAW));
SAISI = null; APPELS = []; await importSheets(); R.annule = APPELS.length;
SAISI = "   "; await importSheets(); R.vide = APPELS.length;
SAISI = "https://docs.google.com/y"; ERR = "La feuille n'est pas partagée"; IMPORTS = []; await importSheets();
R.err = [TOASTS[TOASTS.length - 1], IMPORTS.length, SHEETSV];
""")
check("I0 sous node : l'import Sheets s'exécute", R is not None)
if R:
    attendu = list("Nom,Coût\nGobelin,2\n".encode("utf-8"))
    check("I1 le dialogue maison demande le lien et dit l'onglet lu ; UN appel au double clic, lien nettoyé",
          len(R["dial"]) == 1 and "#gid=" in R["dial"][0][0] and R["dial"][0][1]["ok"] == "Importer"
          and R["appels"] == [["import-url", {"url": "https://docs.google.com/spreadsheets/d/x/edit"}]], str(R["appels"]))
    check("I2 les OCTETS (UTF-8 exacts) passent par importBytes, le chemin d'un fichier déposé ; LASTRAW les garde",
          R["imp"] == [[attendu, "Mon jeu - Cartes.csv", {}]] and R["raw"] == attendu, str(R["imp"]))
    check("I3 annuler ou laisser vide : rien ne part ; un refus du serveur est DIT, rien n'est importé, le verrou est rendu",
          R["annule"] == 0 and R["vide"] == 0 and "pas partagée" in R["err"][0][0] and R["err"][0][1] is True
          and R["err"][1] == 0 and R["err"][2] is False, str(R))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
