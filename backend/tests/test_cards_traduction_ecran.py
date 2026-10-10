# -*- coding: utf-8 -*-
"""Card Forge — tâche #86 PR B à l'écran (plan-cartes T13, 04/10/2026) : la TRADUCTION dans la pièce 04.
DÉCISIONS DE L'UTILISATEUR (04/10) : coût annoncé AVANT par le dialogue maison ; validation CARTE PAR CARTE seulement
(aucun « tout accepter »), la proposition se corrige avant d'être acceptée.
Les fonctions LIVRÉES sont extraites de mod-data.js et EXÉCUTÉES sous node (aucun appel réel).
Témoin positif : la base (0cd41ee6) n'a pas de traduction.
Run (depuis backend/) : & $PY tests/test_cards_traduction_ecran.py"""
import sys as _sys_l7, pathlib as _pl_l7; _sys_l7.path.insert(0, str(_pl_l7.Path(__file__).resolve().parent))  # noqa: E401,E702
import _cartes_avant_l7  # noqa: F401,E402  (t147 : la source du Card Forge d'avant la traduction L7)
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
DATA = (RACINE / "frontend/cardforge/js/mod-data.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cftrade_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "0cd41ee6"
b = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-data.js"], capture_output=True, cwd=str(RACINE)).stdout
check("T1 témoin : la base n'a pas de traduction", b and b"traduireLangue" not in b)
check("T2 aucun « tout accepter » ; chaque bouton de traduction est TITRÉ ; les clics sont câblés",
      "tout accepter" not in DATA.lower().replace("aucun « tout accepter »", "")
      and DATA.count('data-trad-go="1" title="') == 1 and DATA.count("data-trad-ok=\"' + i + '\" title=\"") == 1
      and DATA.count("data-trad-non=\"' + i + '\" title=\"") == 1
      and "if (a) { tradAccepter(Number(a.dataset.tradOk)); return; }" in DATA and "if (n) tradRefuser(Number(n.dataset.tradNon));" in DATA)


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


COUCHE = "\n".join(fonction(DATA, n) for n in ("traductionHTML", "traduireLangue", "tradAccepter", "tradRefuser"))
check("T3 la couche livrée est extraite", COUCHE.count("function ") >= 4)

HARNAIS = r"""
var TRAD = [], TRADV = false, TRADSEL = {source: "", cible: "", moteur: "auto"};
var LANGS = {connues: {fr: "français", en: "anglais", de: "allemand"},
             langues: [{code: "fr", label: "français"}, {code: "en", label: "anglais"}]};
var T = {columns: ["id", "titre_fr", "regles_fr"], rows: [["c1", "Golem", "Bloque."], ["c2", "Elfe", "Vole."]], off: [3],
         map: {titre_fr: "title"}};
var APPELS = [], DIAL = [], DREP = true, TOASTS = [], REP = {}, ERR = {}, UNDO = 0, COMMIT = 0, RENDER = 0, SCHED = 0, PAINT = 0;
var esc = function (s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); };
var INPUTS = {};
var REFS = {langues: {querySelector: function (s) { var m = /data-trad-in="(\d+)"/.exec(s); return m && INPUTS[m[1]] ? {value: INPUTS[m[1]]} : null; }}};
var window = {__dzDialogue: {confirmer: async function (m, o) { DIAL.push([m, o]); return DREP; }}};
var M = {busy: function () {}, toast: function (t, e) { TOASTS.push([t, !!e]); },
         api: {post: async function (u, b) { APPELS.push([u, JSON.parse(JSON.stringify(b))]); await new Promise(function (s) { setTimeout(s, 5); });
                                            if (ERR[u]) throw new Error(ERR[u]); return REP[u]; }}};
function pushUndo() { UNDO++; } function commit() { COMMIT++; } function render() { RENDER++; } function schedule() { SCHED++; } function paintLangues() { PAINT++; }
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
R.barre = traductionHTML(LANGS.langues);
REP["traduire/devis"] = {n: 2, restants: 0, usd: 0.0031, payant: true, fournisseur: "anthropic", dispo: {auto: true, ollama: false}, colonnes_a_creer: ["titre_en", "regles_en"]};
REP["traduire"] = {propositions: [{ligne: 1, colonne: "titre_en", source: "Golem", proposition: "Golem"},
                                  {ligne: 2, colonne: "regles_en", source: "Vole.", proposition: "Fl<ies>."}]};
var p1 = traduireLangue(), p2 = traduireLangue(); await p1; await p2;
R.appels = APPELS.slice(); R.dial = DIAL.slice(); R.trad = TRAD.slice(); R.liste = traductionHTML(LANGS.langues);
DIAL = []; APPELS = []; DREP = false; await traduireLangue(); R.annule = [DIAL.length, APPELS.map(function (a) { return a[0]; })];
""")
check("D0 sous node : la traduction s'exécute", R is not None)
if R:
    bar = R["barre"]
    check("D1 la barre : source = langues de la table, cible = langues connues sauf la source, moteur des Réglages ou Ollama ; bouton TITRÉ",
          '<option value="fr" selected>français</option><option value="en">anglais</option></select> vers' in bar
          and '<option value="en" selected>anglais</option><option value="de">allemand</option>' in bar
          and '<option value="ollama">Ollama (local, gratuit)</option>' in bar and "Devis d’abord" in bar
          and 'vers <select' in bar and '<option value="fr"' not in bar.split("vers <select")[1].split("</select>")[0], bar)
    check("D2 UN devis au double clic, puis le dialogue ANNONCE cellules, coût, fournisseur, plafond, colonnes créées, et que rien n'entre sans clic",
          [a[0] for a in R["appels"]] == ["traduire/devis", "traduire"] and len(R["dial"]) == 1
          and "2 cellule(s) de français vers anglais : ≈ 0.0031 $ avec anthropic — PAYANT, plafond « cartes » appliqué" in R["dial"][0][0]
          and "Colonne(s) créée(s) à l’acceptation : titre_en, regles_en" in R["dial"][0][0]
          and "rien n’entre dans la table sans votre clic" in R["dial"][0][0] and R["dial"][0][1]["ok"] == "Traduire (≈ 0.0031 $)", str(R["dial"]))
    check("D3 la demande part avec la table, les lignes écartées, le mappage, source, cible et moteur",
          R["appels"][1][1] == {"columns": ["id", "titre_fr", "regles_fr"], "rows": [["c1", "Golem", "Bloque."], ["c2", "Elfe", "Vole."]],
                                "off": [3], "map": {"titre_fr": "title"}, "source": "fr", "cible": "en", "moteur": "auto"}, str(R["appels"][1]))
    check("D4 les propositions s'affichent une à une, corrigeables (champ), ÉCHAPPÉES, avec Accepter / Refuser",
          len(R["trad"]) == 2 and 'data-trad-in="1" value="Fl&lt;ies>."' in R["liste"] and R["liste"].count(">Accepter</button>") == 2
          and R["liste"].count(">Refuser</button>") == 2 and "ligne 2 · regles_en : « Vole. »" in R["liste"], R["liste"])
    check("D5 annuler le dialogue : le devis seul est parti, aucune traduction", R["annule"] == [1, ["traduire/devis"]], str(R["annule"]))

R = node("""
TRAD = [{ligne: 1, colonne: "titre_en", source: "Golem", proposition: "Golem"}, {ligne: 2, colonne: "titre_en", source: "Elfe", proposition: "Elf"},
        {ligne: 9, colonne: "titre_en", source: "x", proposition: "y"}];
INPUTS["1"] = "  Elven scout  ";
tradAccepter(1);
R.t1 = JSON.parse(JSON.stringify(T)); R.c1 = [UNDO, COMMIT, RENDER, SCHED, TRAD.length];
tradAccepter(0); R.t2 = JSON.parse(JSON.stringify(T)); R.cols = T.columns.length;
INPUTS["0"] = "   "; tradAccepter(0); R.vide = [TRAD.length, TOASTS[TOASTS.length - 1]];
delete INPUTS["0"]; tradAccepter(0); R.disparue = [TRAD.length, TOASTS[TOASTS.length - 1][1], UNDO];
TRAD = [{ligne: 1, colonne: "regles_fr", source: "a", proposition: "b"}]; tradRefuser(0); R.refus = [TRAD.length, T.rows[0][2], PAINT];
""")
check("A0 sous node : l'acceptation s'exécute", R is not None)
if R:
    check("A1 accepter : la valeur du CHAMP (corrigée, nettoyée) entre dans la table, la colonne absente est CRÉÉE, annulable (pushUndo), jeu reconstruit",
          R["t1"]["columns"] == ["id", "titre_fr", "regles_fr", "titre_en"] and R["t1"]["rows"][1] == ["c2", "Elfe", "Vole.", "Elven scout"]
          and R["t1"]["rows"][0] == ["c1", "Golem", "Bloque.", ""] and R["c1"] == [1, 1, 1, 1, 2], str(R["t1"]) + str(R["c1"]))
    check("A2 la colonne n'est créée qu'UNE fois ; une proposition vide est refusée et dite",
          R["cols"] == 4 and R["t2"]["rows"][0][3] == "Golem" and R["vide"][0] == 1 and R["vide"][1][1] is True, str(R))
    check("A3 une ligne qui n'existe plus : dit, écartée, rien écrit (pas d'annulation empilée)",
          R["disparue"][0] == 0 and R["disparue"][1] is True and R["disparue"][2] == 2, str(R["disparue"]))
    check("A4 refuser : la proposition disparaît, la table est intacte", R["refus"][0] == 0 and R["refus"][1] == "Bloque." and R["refus"][2] >= 1, str(R["refus"]))

R = node("""
REP["traduire/devis"] = {n: 0}; await traduireLangue(); R.rien = [APPELS.length, DIAL.length, TOASTS[0][0]];
APPELS = []; TOASTS = []; REP["traduire/devis"] = {n: 3, usd: 0, payant: false, fournisseur: "ollama", dispo: {auto: false, ollama: true}, colonnes_a_creer: []};
TRADSEL.moteur = "ollama"; ERR["traduire"] = "503 Service Unavailable"; await traduireLangue();
R.ollama = [DIAL[0][0], DIAL[0][1].ok, TOASTS[0], TRADV, APPELS[1][1].moteur];
APPELS = []; TOASTS = []; DIAL = []; REP["traduire/devis"] = {n: 3, usd: 0, payant: false, fournisseur: "", dispo: {auto: false, ollama: false}};
TRADSEL.moteur = "auto"; await traduireLangue(); R.aucun = [APPELS.map(function (a) { return a[0]; }), DIAL.length, TOASTS[0], TRADV];
APPELS = []; TOASTS = []; TRADSEL.moteur = "ollama"; await traduireLangue(); R.aucun_ol = [APPELS.length, DIAL.length, TOASTS[0]];
""")
check("O0 sous node : les cas limites s'exécutent", R is not None)
if R:
    check("O1 rien à traduire : dit, aucun dialogue, aucun appel payant", R["rien"][0] == 1 and R["rien"][1] == 0 and "rien à traduire" in R["rien"][2], str(R["rien"]))
    check("O2 Ollama : le dialogue dit local et gratuit ; un refus du serveur est dit ; le verrou est rendu",
          "Ollama, local — gratuit" in R["ollama"][0] and R["ollama"][1] == "Traduire" and "503" in R["ollama"][2][0]
          and R["ollama"][2][1] is True and R["ollama"][3] is False and R["ollama"][4] == "ollama", str(R["ollama"]))
    check("O3 aucun moteur prêt : dit AVANT tout dialogue (Réglages / OLLAMA_MODEL), seul le devis est parti, le verrou est rendu",
          R["aucun"][0] == ["traduire/devis"] and R["aucun"][1] == 0 and "Réglages" in R["aucun"][2][0] and R["aucun"][2][1] is True
          and R["aucun"][3] is False and R["aucun_ol"][0] == 1 and R["aucun_ol"][1] == 0 and "OLLAMA_MODEL" in R["aucun_ol"][2][0], str(R))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
