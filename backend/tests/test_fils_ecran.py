# -*- coding: utf-8 -*-
"""t381 (30/10/2026) — News › Sources : l'ÉCRAN des fils sociaux suivis (frontend/shared/dz-fils.js) et le maillon de
queue dzfils (après dzchemins). Le comportement du panneau est joué sous node par frontend/shared/qa/fils.test.mjs
(lancé ici) ; ce banc tient le reste :
  1. le dictionnaire fils.json : chaque clé employée existe (y compris les clés COMPOSÉES : fils.etat.<code>,
     fils.lecture.<lecture>, fils.cadre.<cadre>, fils.agent.<agent>), FR et EN non vides, mêmes variables, aucune
     orpheline ; les états et travaux sont EXACTEMENT ceux du service (news_fils) ; dictionnaire assemblé à jour ;
  2. le script : copie identique dans frontend/dist/shared, chargé par la SPA APRÈS dz-i18n.js, aucun innerHTML,
     aucun arrondi, aucune chaîne française en dur hors dzT ;
  3. le maillon : hôte DANS la liste défilante des Sources de News, après les flux et avant le pied ; un élément de
     fil reste dans la liste des articles ; appliqué, inverse avant_dzfils exact, appelé EN TÊTE de avant_dzchemins,
     hors couche, sonde de dzchemins, aucun .bak laissé, comptes figés intacts, octets ;
  4. le panneau joué sous node (fils.test.mjs) ;
  5. AGENTS.md nomme l'écran et le maillon.
Run : & $PY tests/test_fils_ecran.py   (depuis backend/)
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
    import patch_bundle_dzfils as M                                  # noqa: E402
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
SRC_P = RACINE / "frontend" / "shared" / "dz-fils.js"
SRC = SRC_P.read_text(encoding="utf-8") if SRC_P.exists() else ""
_d = RACINE / "frontend" / "shared" / "i18n" / "fils.json"
DICO = json.loads(_d.read_text(encoding="utf-8")) if _d.exists() else {}

print("\n[1] le dictionnaire")
ETATS, LECTURES, CADRES, ECRITS = [], [], [], set()
try:
    os.environ.setdefault("DEEPOTUS_DATA_DIR", str(pathlib.Path(os.environ.get("TEMP", ".")) / "dzfils_ecran"))
    from app.services import news_fils as NF                       # noqa: E402
    SRV = pathlib.Path(NF.__file__).read_text(encoding="utf-8")
    ETATS = list(NF.ETATS)
    _fils_srv = SRV[:SRV.index("# ---- suggestions")]                 # les états écrits sur un FIL (pas les suggestions)
    ECRITS = set(re.findall(r'etat="([a-z_]+)"', _fils_srv)) | set(re.findall(r'"([a-z_]+)" if apify else "([a-z_]+)"', _fils_srv)[0])
    LECTURES = sorted({v["lecture"] for v in NF.PLATEFORMES.values()})
    CADRES = list(NF.CADRES)
except Exception as e:                                               # noqa: BLE001
    print(f"  (service illisible : {e!r})")
CODE = re.sub(r"/\*.*?\*/|//[^\n]*", "", SRC, flags=re.S)        # le script sans ses commentaires
directes = {k for k in re.findall(r'"(fils\.[a-z0-9_.]+)"', CODE) if not k.endswith((".", "_"))}
composees = ({f"fils.etat.{c}" for c in ETATS} | {f"fils.lecture.{x}" for x in LECTURES}
             | {f"fils.cadre.{c}" for c in CADRES} | {"fils.agent.campagnes"})
employees = directes | composees
check("1.1 chaque clé employée existe, FR et EN non vides", employees and all(
    k in DICO and DICO[k]["fr"] and DICO[k]["en"] for k in employees), sorted(k for k in employees if k not in DICO))
check("1.2 aucune orpheline", DICO and set(DICO) == employees, sorted(set(DICO) ^ employees))
check("1.3 trois segments, mêmes variables en FR et en EN", DICO and all(
    k.count(".") == 2 and set(re.findall(r"\{(\w+)\}", v["fr"])) == set(re.findall(r"\{(\w+)\}", v["en"]))
    for k, v in DICO.items()))
check("1.4 les clés composées le sont dans le script (etat. / lecture. / cadre. / agent.)", all(
    f'T("fils.{z}." +' in SRC for z in ("etat", "lecture", "cadre", "agent")), "")
check("1.5 tout état écrit sur un fil est dans news_fils.ETATS (donc traduit)", ETATS and ECRITS and ECRITS <= set(ETATS),
      sorted(ECRITS - set(ETATS)))
check("1.6 les travaux de l'agent ont leur texte", CADRES == ["campagne", "veille", "prospects"], CADRES)
r = subprocess.run([sys.executable, str(RACINE / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True)
check("1.7 dictionnaire assemblé à jour", r.returncode == 0, r.stdout[-200:])

print("\n[2] le script")
COPIE = RACINE / "frontend" / "dist" / "shared" / "dz-fils.js"
check("2.1 copie identique dans frontend/dist/shared", COPIE.exists() and COPIE.read_bytes() == SRC_P.read_bytes())
PAGE = (RACINE / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
i_f, i_i18n = PAGE.find('<script src="/shared/dz-fils.js"></script>'), PAGE.find('/shared/dz-i18n.js')
check("2.2 la SPA charge dz-fils.js, après dz-i18n.js", i_f > i_i18n > 0, (i_f, i_i18n))
check("2.3 aucun innerHTML", CODE and "innerHTML" not in CODE)
rayons = re.findall(r"border-radius:\s*([^;\"]+)", SRC)
check("2.4 angles vifs : aucun arrondi", SRC and all(x.strip() == "0" for x in rayons), rayons)
dur = [m for m in re.findall(r'"([^"\n]*[éèàùçÉ«»][^"\n]*)"', CODE)]
check("2.5 aucune chaîne française en dur hors dzT", SRC and not dur, dur)
check("2.6 retirer un fil passe par __dzDialogue.confirmer", 'dlg.confirmer(T("fils.action.retirer_confirmer"' in SRC)
check("2.7 l'accord envoie confirme_cout et le plafond choisi", "confirme_cout: true" in CODE and "plafond_usd: Number(dv.plafond)" in CODE)

print("\n[3] le maillon de queue")
i0 = BUN.find('dzT("news.sources.ajouter")')
COL = BUN[i0:BUN.find('dzT("news.sources.defauts")', i0)] if i0 > 0 else ""
check("3.0 le maillon existe", M is not None)
check("3.1 l'hôte est dans la liste des Sources de News, après les flux, avant « Tout actualiser »",
      "data-dz-fils-hote" in COL and COL.find('dzT("news.sources.vide")') < COL.find("data-dz-fils-hote")
      < COL.find('dzT("news.sources.tout_actualiser")'))
check("3.2 l'hôte appelle monter par une ref (aucun hook)", "window.__dzFils.monter(el)" in COL
      and BUN.count("x.useState(") == 731)
check("3.3 un élément de fil reste dans la liste des articles",
      "items.filter(i=>ena.has(i.source_id)||!!i.plateforme)" in BUN
      and "doublons:z.doublons||[],plateforme:z.plateforme||null}" in BUN)
if M is not None:
    r = subprocess.run([sys.executable, str(RACINE / "scripts" / "patch_bundle_dzfils.py"), "--check"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    check("3.4 le maillon est appliqué (--check)", r.returncode == 0 and "déjà appliqué" in r.stdout,
          (r.stdout + r.stderr)[-300:])
    avant = AIDE.avant_dzfils(BUN) if hasattr(AIDE, "avant_dzfils") else ""
    check("3.5 l'inverse avant_dzfils défait le maillon, et le rejouer redonne le bundle à l'octet",
          avant and M.MARKER not in avant and "data-dz-fils" not in avant and "!!i.plateforme" not in avant and "plateforme:z.plateforme" not in avant
          and M.appliquer(avant) == BUN)
    src_aide = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
    _g = src_aide[src_aide.index("def avant_dzchemins("):]
    _g = _g[:_g.index("\ndef ", 5)]
    check("3.6 avant_dzchemins défait d'abord dzfils (maillon posé après lui)",
          "bundle = avant_dzfils(bundle)" in _g and _g.index("avant_dzfils(") < _g.index("_m.defaire("))
    check("3.7 aucune paire dans une couche __DZ_*_BEGIN__", all(M.hors_couche(BUN, z) for _a, z in M.PAIRES))
    check("3.8 le maillon suit dzchemins (sonde de son marqueur)", any(j == "/*dzchemins*/" for _t, j, _n in M.SONDE_AMONT))
    check("3.9 aucun .bak_dzfils laissé, un seul marqueur", not (BUNDLE.parent / (BUNDLE.name + ".bak_dzfils"))
          .exists() and BUN.count(M.MARKER) == 1)
    check("3.10 lecture et écriture du bundle en octets", "read_text(" not in pathlib.Path(M.__file__).read_text(
        encoding="utf-8") and BUNDLE.read_bytes().count(b"\r\n") > 15000
        and BUNDLE.read_bytes().count(b"\n") == BUNDLE.read_bytes().count(b"\r\n"))
    check("3.11 comptes figés intacts", BUN.count("v2.8.0") == 4 and BUN.count("DzTracks") == 181
          and BUN.count("await window.__dzDialogue.confirmer(") == 30)
    r = subprocess.run(["node", "--check", str(BUNDLE)], capture_output=True, text=True)
    check("3.12 bundle node --check", r.returncode == 0, r.stderr[-300:])

print("\n[4] le panneau joué sous node")
r = subprocess.run(["node", str(RACINE / "frontend" / "shared" / "qa" / "fils.test.mjs")], capture_output=True,
                   text=True, encoding="utf-8", errors="replace", timeout=120)
check("4.1 fils.test.mjs vert", r.returncode == 0, (r.stdout + r.stderr)[-1500:])

print("\n[5] la documentation")
AG = (RACINE / "AGENTS.md").read_text(encoding="utf-8")
check("5.1 AGENTS.md nomme l'écran et le maillon", all(x in AG for x in (
    "frontend/shared/dz-fils.js", "patch_bundle_dzfils.py", "backend/app/services/news_fils.py")))

print(f"\n{ok} PASS / {fail} FAIL")
sys.exit(1 if fail else 0)
