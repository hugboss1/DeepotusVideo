# -*- coding: utf-8 -*-
"""t382 (30/10/2026) — Réglages › Apparence : l'ÉCRAN de la palette (frontend/shared/dz-apparence.js) et le maillon de
queue dzapparence (après dzfils). Le comportement est joué sous node par frontend/shared/qa/apparence.test.mjs (lancé
ici) ; ce banc tient le reste :
  1. le dictionnaire apparence.json : chaque clé employée existe (y compris les clés COMPOSÉES apparence.preset.<id>,
     apparence.jeton.<id>, apparence.contraste.<id>), FR et EN non vides, mêmes variables, aucune orpheline ;
     dictionnaire assemblé à jour ;
  2. le script : copie identique dans frontend/dist/shared, chargé par la SPA TÔT (script classique, avant le bundle,
     après dz-i18n.js) pour peindre avant le premier rendu, aucun innerHTML, aucun arrondi, aucune chaîne française en
     dur hors dzT, aucun hexadécimal hors des préréglages et du repli de l'encre ;
  3. le maillon : hôte dans Réglages › Apparence (`Cm`), après l'aide et AVANT la carte des animations ; appliqué,
     inverse avant_dzapparence exact, appelé EN TÊTE de avant_dzfils, hors couche, sonde de dzfils, aucun .bak laissé,
     comptes figés intacts, octets ;
  4. le panneau joué sous node (apparence.test.mjs) ;
  5. AGENTS.md nomme l'écran, le service et le maillon.
Run : & $PY tests/test_apparence_ecran.py   (depuis backend/)
"""
import json, os, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
_ICI = pathlib.Path(__file__).resolve().parent
RACINE = _ICI.parent.parent
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(RACINE / "scripts"))
import _i18n_l1_aide as AIDE                                         # noqa: E402

try:
    import patch_bundle_dzapparence as M                             # noqa: E402
except Exception as e:                                               # le banc rougit, ne meurt pas
    M = None
    print(f"  (import du maillon impossible : {e!r})")

ok = fail = 0


def check(label, cond, detail=""):
    global ok, fail
    if cond:
        ok += 1; print(f"  PASS  {label}")
    else:
        fail += 1; print(f"  FAIL  {label} {detail}")


BUNDLE = RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"
BUN = BUNDLE.read_bytes().decode("utf-8")
SRC_P = RACINE / "frontend" / "shared" / "dz-apparence.js"
SRC = SRC_P.read_text(encoding="utf-8") if SRC_P.exists() else ""
_d = RACINE / "frontend" / "shared" / "i18n" / "apparence.json"
DICO = json.loads(_d.read_text(encoding="utf-8")) if _d.exists() else {}
CODE = re.sub(r"/\*.*?\*/|//[^\n]*", "", SRC, flags=re.S)        # le script sans ses commentaires

print("\n[1] le dictionnaire")
PRESETS = ["sombre", "clair", "contraste", "deeplab"]
JETONS = ["fond", "panneau", "texte", "accent", "succes", "erreur"]
CONTROLES = ["texte_fond", "texte_panneau", "secondaire_panneau", "accent_panneau", "bouton", "succes_panneau",
             "erreur_panneau"]
directes = {k for k in re.findall(r'"(apparence\.[a-z0-9_.]+)"', CODE) if not k.endswith((".", "_"))}
composees = ({f"apparence.preset.{p}" for p in PRESETS} | {f"apparence.jeton.{j}" for j in JETONS}
             | {f"apparence.contraste.{c}" for c in CONTROLES})
employees = directes | composees
check("1.1 chaque clé employée existe, FR et EN non vides", employees and all(
    k in DICO and DICO[k]["fr"] and DICO[k]["en"] for k in employees), sorted(k for k in employees if k not in DICO))
check("1.2 aucune orpheline", DICO and set(DICO) == employees, sorted(set(DICO) ^ employees))
check("1.3 trois segments, mêmes variables en FR et en EN", DICO and all(
    k.count(".") == 2 and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
    for k, v in DICO.items()))
check("1.4 les clés composées le sont dans le script", all(
    f'T("apparence.{z}." +' in SRC for z in ("preset", "jeton", "contraste")))
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True)
check("1.5 dictionnaire assemblé à jour", r.returncode == 0, r.stdout[-200:])

print("\n[2] le script")
COPIE = RACINE / "frontend" / "dist" / "shared" / "dz-apparence.js"
check("2.1 copie identique dans frontend/dist/shared", COPIE.exists() and SRC_P.exists()
      and COPIE.read_bytes() == SRC_P.read_bytes())
PAGE = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
balise = '<script src="/shared/dz-apparence.js"></script>'
i_a, i_i18n, i_bun = PAGE.find(balise), PAGE.find("/shared/dz-i18n.js"), PAGE.find("/assets/index-BEOJX8L5.js")
check("2.2 la SPA charge dz-apparence.js tôt : après dz-i18n.js, avant le bundle (aucun éclair au démarrage)",
      0 < i_i18n < i_a < i_bun and PAGE.count(balise) == 1, (i_i18n, i_a, i_bun))
check("2.3 aucun innerHTML", CODE and "innerHTML" not in CODE)
rayons = re.findall(r"border-radius:\s*([^;\"]+)", SRC)
check("2.4 angles vifs : aucun arrondi", SRC and all(x.strip() == "0" for x in rayons), rayons)
dur = [m for m in re.findall(r'"([^"\n]*[éèàùçÉ«»][^"\n]*)"', CODE)]
check("2.5 aucune chaîne française en dur hors dzT", SRC and not dur, dur)
_p = CODE[CODE.find("var PRESETS"):CODE.find("var ORDRE")]
hors = re.findall(r"#[0-9a-fA-F]{6}\b", CODE.replace(_p, "")) if "var PRESETS" in CODE else ["?"]
check("2.6 aucun hexadécimal hors des préréglages (le reste se dérive)", set(hors) <= {"#000000", "#ffffff"}, hors)
check("2.7 la palette s'écrit en style en ligne sur <html> (gagne sur toute feuille, coque et labs)",
      "var r = doc && doc.documentElement;" in CODE and "r.style.setProperty(k, v[k])" in CODE
      and "r.style.removeProperty(k)" in CODE)
check("2.8 le serveur fait foi : /api/reglages/apparence lu et écrit", CODE.count('"/api/reglages/apparence"') == 1
      and "method: \"POST\"" in CODE)

print("\n[3] le maillon de queue")
i0 = BUN.find("function Cm(){")
CM = BUN[i0:BUN.find("function _m(){", i0)] if i0 >= 0 else ""
check("3.0 le maillon existe", M is not None)
check("3.1 l'hôte est dans Réglages › Apparence, après l'aide et avant la carte des animations",
      "data-dz-apparence-hote" in CM and CM.find('dzT("reglages.apparence.aide")') < CM.find("data-dz-apparence-hote")
      < CM.find('dzT("reglages.apparence.mouvement_reduit")'))
check("3.2 l'hôte appelle monter par une ref (aucun hook)", "window.__dzApparence.monter(el)" in CM
      and BUN.count("x.useState(") == 731)
if M is not None:
    r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzapparence.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    check("3.4 le maillon est appliqué (--check)", r.returncode == 0 and "déjà appliqué" in r.stdout,
          (r.stdout + r.stderr)[-300:])
    avant = AIDE.avant_dzapparence(BUN) if hasattr(AIDE, "avant_dzapparence") else ""
    check("3.5 l'inverse avant_dzapparence défait le maillon, et le rejouer redonne le bundle à l'octet",
          avant and M.MARKER not in avant and "data-dz-apparence" not in avant and M.appliquer(avant) == BUN)
    src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
    _g = src_aide[src_aide.index("def avant_dzfils("):]
    _g = _g[:_g.index("\ndef ", 5)]
    check("3.6 avant_dzfils défait d'abord dzapparence (maillon posé après lui)",
          "bundle = avant_dzapparence(bundle)" in _g and _g.index("avant_dzapparence(") < _g.index("_m.defaire("))
    check("3.7 aucune paire dans une couche __DZ_*_BEGIN__", all(M.hors_couche(BUN, z) for _a, z in M.PAIRES))
    check("3.8 le maillon suit dzfils (sonde de son marqueur)", any(j == "/*dzfils*/" for _t, j, _n in M.SONDE_AMONT))
    check("3.9 aucun .bak_dzapparence laissé, un seul marqueur", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzapparence"))
          .exists() and BUN.count(M.MARKER) == 1)
    check("3.10 lecture et écriture du bundle en octets", "read_text(" not in pathlib.Path(M.__file__).read_text(
        encoding="utf-8") and BUNDLE.read_bytes().count(b"\r\n") > 15000
        and BUNDLE.read_bytes().count(b"\n") == BUNDLE.read_bytes().count(b"\r\n"))
    check("3.11 comptes figés intacts", BUN.count("v2.8.0") == 4 and BUN.count("DzTracks") == 181
          and BUN.count("await window.__dzDialogue.confirmer(") == 30)
    r = subprocess.run(["node", "--check", str(BUNDLE)], capture_output=True, text=True)
    check("3.12 bundle node --check", r.returncode == 0, r.stderr[-300:])

print("\n[4] le panneau joué sous node")
r = subprocess.run(["node", str(RACINE / "frontend" / "shared" / "qa" / "apparence.test.mjs")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=120)
check("4.1 apparence.test.mjs vert", r.returncode == 0, (r.stdout + r.stderr)[-1500:])

print("\n[5] la documentation")
AG = (RACINE / "AGENTS.md").read_text(encoding="utf-8")
check("5.1 AGENTS.md nomme l'écran, le service et le maillon", all(x in AG for x in (
    "frontend/shared/dz-apparence.js", "patch_bundle_dzapparence.py", "backend/app/services/apparence.py")))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
