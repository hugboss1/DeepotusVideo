# -*- coding: utf-8 -*-
"""t378 (30/10/2026) — Réglages › Chemins : l'ÉCRAN des emplacements (frontend/shared/dz-chemins.js) et le maillon
de queue dzchemins (après dza2d). Le comportement du panneau est joué sous node par frontend/shared/qa/chemins.test.mjs
(lancé ici) ; ce banc tient le reste :
  1. le dictionnaire chemins.json : chaque clé employée existe (y compris les clés COMPOSÉES : chemins.etat.<code>,
     chemins.type.<type>, chemins.role.<rôle>[_aide]), FR et EN non vides, mêmes variables, aucune orpheline ; les
     codes d'état sont EXACTEMENT ceux du service (emplacements.ETATS) ; dictionnaire assemblé à jour ;
  2. le script : copie identique dans frontend/dist/shared, chargé par la SPA APRÈS dz-i18n.js, aucun innerHTML,
     aucun arrondi (angles vifs), aucune chaîne française en dur hors dzT ;
  3. le maillon : hôte du panneau DANS Réglages › Chemins (`_m`) après « Version du backend », hôte du Diagnostic
     DANS DzDiag avant le journal ; appliqué, inverse avant_dzchemins exact, appelé EN TÊTE de avant_dza2d, hors
     couche, sonde de dza2d, aucun .bak laissé, comptes figés intacts, octets ;
  4. le panneau joué sous node (chemins.test.mjs) ;
  5. AGENTS.md nomme le service, l'écran et le maillon.
Run : & $PY tests/test_emplacements_ecran.py   (depuis backend/)
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
    import patch_bundle_dzchemins as M                               # noqa: E402
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
SRC_P = RACINE / "frontend" / "shared" / "dz-chemins.js"
SRC = SRC_P.read_text(encoding="utf-8") if SRC_P.exists() else ""
_d = RACINE / "frontend" / "shared" / "i18n" / "chemins.json"
DICO = json.loads(_d.read_text(encoding="utf-8")) if _d.exists() else {}

print("\n[1] le dictionnaire")
ETATS = []
try:
    os.environ.setdefault("DEEPOTUS_DATA_DIR", str(pathlib.Path(os.environ.get("TEMP", ".")) / "dzempl_ecran"))
    from app.services import emplacements as E                     # noqa: E402
    ETATS, TYPES, ROLES = list(E.ETATS), list(E.TYPES), list(E.ROLES)
    from app.services import emplacements_cablage as EC              # noqa: E402 — t379 : genres de la galerie
    GENRES = list(EC.GENRES)
except Exception as e:                                               # noqa: BLE001
    TYPES, ROLES, GENRES = [], [], []
    print(f"  (service illisible : {e!r})")
CODE = re.sub(r"/\*.*?\*/|//[^\n]*", "", SRC, flags=re.S)        # le script sans ses commentaires
directes = {k for k in re.findall(r'"(chemins\.[a-z0-9_.]+)"', CODE) if not k.endswith((".", "_"))}
composees = ({f"chemins.etat.{c}" for c in ETATS} | {f"chemins.type.{t}" for t in TYPES}
             | {f"chemins.role.{r}" for r in ROLES} | {f"chemins.role.{r}_aide" for r in ROLES}
             | {f"chemins.biblio.genre_{g}" for g in GENRES})
employees = directes | composees
check("1.1 chaque clé employée existe, FR et EN non vides", employees and all(
    k in DICO and DICO[k]["fr"] and DICO[k]["en"] for k in employees), sorted(k for k in employees if k not in DICO))
check("1.2 aucune orpheline", DICO and set(DICO) == employees, sorted(set(DICO) ^ employees))
check("1.3 trois segments, mêmes variables en FR et en EN", DICO and all(
    k.count(".") == 2 and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
    for k, v in DICO.items()))
check("1.4 les clés composées le sont dans le script (etat. / type. / role.)", all(
    f'T("chemins.{z}." +' in SRC for z in ("etat", "type", "role")), "")
check("1.5 les codes d'état du service ont tous leur texte", ETATS and all(f"chemins.etat.{c}" in DICO for c in ETATS))
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True)
check("1.6 dictionnaire assemblé à jour", r.returncode == 0, r.stdout[-200:])

print("\n[2] le script")
COPIE = RACINE / "frontend" / "dist" / "shared" / "dz-chemins.js"
check("2.1 copie identique dans frontend/dist/shared", COPIE.exists() and COPIE.read_bytes() == SRC_P.read_bytes())
PAGE = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
i_ch, i_i18n = PAGE.find('<script src="/shared/dz-chemins.js"></script>'), PAGE.find('/shared/dz-i18n.js')
check("2.2 la SPA charge dz-chemins.js, après dz-i18n.js", i_ch > i_i18n > 0, (i_ch, i_i18n))
check("2.3 aucun innerHTML", CODE and "innerHTML" not in CODE)
rayons = re.findall(r"border-radius:\s*([^;\"]+)", SRC)
check("2.4 angles vifs : aucun arrondi", SRC and all(x.strip() == "0" for x in rayons), rayons)
dur = [m for m in re.findall(r'"([^"\n]*[éèàùç«»][^"\n]*)"', CODE)]
check("2.5 aucune chaîne française en dur hors dzT", SRC and not dur, dur)
check("2.6 suppression derrière __dzDialogue.confirmer", "dlg.confirmer(T(\"chemins.action.supprimer_confirmer\"" in SRC)

print("\n[3] le maillon de queue")
i0, i1 = BUN.find("function _m(){"), BUN.find("function zm(){")
FN_M = BUN[i0:i1] if 0 < i0 < i1 else ""
d0 = BUN.find("function DzDiag(")
FN_D = BUN[d0:BUN.find("function DzMaj(", d0)] if d0 > 0 else ""
check("3.0 le maillon existe", M is not None)
check("3.1 l'hôte du panneau est dans Réglages › Chemins, après « Version du backend »",
      'data-dz-chemins-hote' in FN_M and FN_M.find("reglages.chemins.version_api") < FN_M.find("data-dz-chemins-hote"))
check("3.2 l'hôte du Diagnostic est dans DzDiag, avant le journal", "data-dz-chemins-diag" in FN_D
      and FN_D.find("data-dz-chemins-diag") < FN_D.find('reglages.diag.journal'))
check("3.3 les hôtes appellent monter / diag par une ref (aucun hook)", "window.__dzChemins.monter(el)" in FN_M
      and "window.__dzChemins.diag(el)" in FN_D and BUN.count("x.useState(") == 731)
if M is not None:
    r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzchemins.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    check("3.4 le maillon est appliqué (--check)", r.returncode == 0 and "déjà appliqué" in r.stdout,
          (r.stdout + r.stderr)[-300:])
    avant = AIDE.avant_dzchemins(BUN) if hasattr(AIDE, "avant_dzchemins") else ""
    check("3.5 l'inverse avant_dzchemins défait le maillon, et le rejouer redonne le bundle à l'octet",
          avant and M.MARKER not in avant and "data-dz-chemins" not in avant
          and M.appliquer(avant) == BUN)
    src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
    _g = src_aide[src_aide.index("def avant_dza2d("):]
    _g = _g[:_g.index("\ndef ", 5)]
    check("3.6 avant_dza2d défait d'abord dzchemins (maillon posé après lui)",
          "bundle = avant_dzchemins(bundle)" in _g and _g.index("avant_dzchemins(") < _g.index("_m.defaire("))
    check("3.7 aucune paire dans une couche __DZ_*_BEGIN__", all(M.hors_couche(BUN, z) for _a, z in M.PAIRES))
    check("3.8 le maillon suit dza2d (sonde de son marqueur)", any(j == "/*dza2d*/" for _t, j, _n in M.SONDE_AMONT))
    check("3.9 aucun .bak_dzchemins laissé, un seul marqueur", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzchemins"))
          .exists() and BUN.count(M.MARKER) == 1)
    check("3.10 lecture et écriture du bundle en octets", "read_text(" not in pathlib.Path(M.__file__).read_text(
        encoding="utf-8") and BUNDLE.read_bytes().count(b"\r\n") > 15000
        and BUNDLE.read_bytes().count(b"\n") == BUNDLE.read_bytes().count(b"\r\n"))
    check("3.11 comptes figés intacts", BUN.count("v2.8.0") == 4 and BUN.count("DzTracks") == 181
          and BUN.count("await window.__dzDialogue.confirmer(") == 30)

print("\n[3b] t379 : la relance « emplacement » du Job Dock, SANS toucher au remplacement de dzdock")
r0 = BUN.find("function __dzRelancer(")
FN_R = BUN[r0:BUN.find("function ", r0 + 30)] if r0 > 0 else ""
check("3b.1 __dzRelancer (remplacement de dzdock) est intact : aucun cas « emplacement » dans le bundle",
      FN_R and "emplacement" not in FN_R)
check("3b.2 le serveur rend la relance « emplacement » (le Dock pose donc son bouton « Réessayer »)",
      'if j.provider == "emplacement":' in (RACINE / "backend" / "app" / "api" / "routes.py").read_text(encoding="utf-8"))
check("3b.3 dz-chemins.js intercepte ce bouton en phase de CAPTURE et rejoue l'opération",
      'addEventListener("click", surClicDock, true)' in CODE and '"/operations/"' in CODE
      and 'T("coque.file.reessayer_direct_aide")' in CODE)

print("\n[4] le panneau joué sous node")
r = subprocess.run(["node", str(RACINE / "frontend" / "shared" / "qa" / "chemins.test.mjs")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=120)
check("4.1 chemins.test.mjs vert", r.returncode == 0, (r.stdout + r.stderr)[-1500:])

print("\n[5] la documentation")
AG = (RACINE / "AGENTS.md").read_text(encoding="utf-8")
check("5.1 AGENTS.md nomme le service, l'écran et le maillon", all(x in AG for x in (
    "backend/app/services/emplacements.py", "frontend/shared/dz-chemins.js", "patch_bundle_dzchemins.py",
    "backend/app/services/emplacements_cablage.py")))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
