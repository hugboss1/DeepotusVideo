# -*- coding: utf-8 -*-
"""Card Forge — tâche #86 PR A à l'écran (plan-cartes T12, 04/10/2026) : la LANGUE ACTIVE dans la pièce 04.
Les fonctions LIVRÉES sont extraites de mod-data.js et EXÉCUTÉES sous node.
Témoin positif : la base (f40144b6) n'a aucune langue.
Run (depuis backend/) : & $PY tests/test_cards_langues_ecran.py"""
import json, pathlib, subprocess, sys, tempfile
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
DATA = (RACINE / "frontend/cardforge/js/mod-data.js").read_bytes().decode("utf-8").replace("\r\n", "\n")
_TMP = pathlib.Path(tempfile.mkdtemp(prefix="cflange_"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


BASE = "f40144b6"
b = subprocess.run(["git", "show", f"{BASE}:frontend/cardforge/js/mod-data.js"], capture_output=True, cwd=str(RACINE)).stdout
check("T1 témoin : la base n'a aucune langue", b and b"checkLangues" not in b and b"lang:" not in b)
check("T2 la langue vit dans l'état (déclarée, lue, enregistrée avec la table) et part avec CHAQUE /build",
      'lang: "",         /* tache #86' in DATA and 'lang: typeof d.lang === "string" ? d.lang : "",' in DATA
      and "      lang: T.lang || \"\",\n    });" in DATA
      and 'columns: T.columns, rows: T.rows, off: T.off, map: T.map, lang: T.lang || "",' in DATA
      and DATA.count("    checkStats();\n    checkLangues();") == 2)


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


COUCHE = "\n".join(fonction(DATA, n) for n in ("checkLangues", "choisirLangue", "paintLangues"))
check("T3 la couche livrée est extraite", COUCHE.count("function ") >= 3)

HARNAIS = r"""
var LANGS = null, LGSEQ = 0, APPELS = [], PATCH = [], SCHED = 0, TOASTS = [], REP = {};
var T = {columns: ["id", "nom_fr", "nom_en"], rows: [["c1", "Colosse", "Colossus"]], off: [2],
         map: {nom_fr: "titre"}, qty_col: "qty", lang: ""};
var esc = function (s) { return String(s == null ? "" : s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/"/g, "&quot;"); };
var REFS = {langues: {innerHTML: "", className: ""}};
function schedule(ms) { SCHED++; }
var M = {patch: function (o) { PATCH.push(o); }, toast: function (t) { TOASTS.push(t); },
         api: {post: async function (u, b) { APPELS.push([u, JSON.parse(JSON.stringify(b))]); if (REP.err) throw new Error(REP.err); return REP[u]; }}};
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
REP["langues"] = {neutres: ["id"], langues: [
  {code: "fr", label: "français", cartes_incompletes: 0, details: [], absentes: []},
  {code: "en", label: "anglais", cartes_incompletes: 1, details: [{ligne: 2, cartes: 1, colonnes: ["texte_<en>"]}], absentes: ["flavor"]}]};
await checkLangues();
R.appel = APPELS[0]; R.html0 = REFS.langues.innerHTML; R.cls0 = REFS.langues.className;
choisirLangue("en");
R.apres = [T.lang, PATCH.slice(), SCHED, TOASTS.slice()]; R.html1 = REFS.langues.innerHTML;
choisirLangue("en"); R.rien = [PATCH.length, SCHED];
choisirLangue(""); R.retour = [T.lang, PATCH[PATCH.length - 1], TOASTS[TOASTS.length - 1]];
T.lang = "en"; PATCH = []; SCHED = 0; REP["langues"] = {neutres: ["a"], langues: []}; await checkLangues();
R.disparue = [T.lang, PATCH.slice(), SCHED, REFS.langues.className, REFS.langues.innerHTML];
REP["langues"] = {neutres: [], langues: [{code: "en", label: "anglais", cartes_incompletes: 0, details: [], absentes: []}]};
await checkLangues(); R.avantPanne = REFS.langues.className;
REP.err = "500"; await checkLangues(); R.panne = [REFS.langues.className];
""")
check("L0 sous node : le panneau s'exécute", R is not None)
if R:
    check("L1 la table part avec son mappage RÉEL, ses lignes écartées et sa quantité",
          R["appel"] == ["langues", {"columns": ["id", "nom_fr", "nom_en"], "rows": [["c1", "Colosse", "Colossus"]], "off": [2],
                                     "map": {"nom_fr": "titre"}, "qty_col": "qty"}], str(R["appel"]))
    h = R["html0"]
    check("L2 un bouton par langue TITRÉ (et « telle que mappée ») ; la langue incomplète est marquée ; renvoi à la pièce 03",
          'data-lang="" title="Les colonnes exactement comme le mappage les désigne">telle que mappée</button>' in h
          and 'data-lang="fr" title="Rendre tout le jeu en français — complet">français</button>' in h
          and 'title="Rendre tout le jeu en anglais — 1 carte(s) avec une colonne manquante">anglais ⚠</button>' in h
          and "<b>pièce 03</b>" in h and "Impression et Édition sortent dans la langue active" in h
          and R["cls0"] == "cf-data-langues", h)
    check("L3 choisir l'anglais : la langue est ENREGISTRÉE seule (pas la table), le jeu se reconstruit, c'est dit",
          R["apres"][0] == "en" and R["apres"][1] == [{"lang": "en"}] and R["apres"][2] == 1
          and R["apres"][3] == ["jeu rendu en anglais"], str(R["apres"]))
    h1 = R["html1"]
    check("L4 la langue active dit ce qui manque, carte par carte, ÉCHAPPÉ, et que la cellule sort VIDE — jamais dans une autre langue",
          'cf-data-langbtn' not in h1 and 'class="btn sm cf-data-langb on" data-lang="en"' in h1
          and "anglais : 1 carte(s) avec une colonne manquante — la cellule sort VIDE, jamais dans une autre langue" in h1
          and "ligne 2 (1 carte(s)) : texte_&lt;en>" in h1 and "aucune colonne « flavor » en anglais" in h1, h1)
    check("L5 re-choisir la même langue ne fait rien ; revenir à « telle que mappée » est enregistré et dit",
          R["rien"] == [1, 1] and R["retour"] == ["", {"lang": ""}, "jeu rendu tel que mappé"], str(R["rien"]) + str(R["retour"]))
    check("L6 une langue retenue que la table ne porte plus : retour au mappage tel quel, enregistré, jeu reconstruit, bloc caché",
          R["disparue"][:3] == ["", [{"lang": ""}], 1] and R["disparue"][3] == "cf-data-langues hidden" and R["disparue"][4] == "", str(R["disparue"]))
    check("L7 une panne APRÈS un état affiché cache le bloc (rien d'inventé)",
          R["avantPanne"] == "cf-data-langues" and R["panne"] == ["cf-data-langues hidden"], str(R["panne"]))

print(f"\n{ok} PASS, {fail} FAIL")
sys.exit(1 if fail else 0)
