# -*- coding: utf-8 -*-
"""t345 (29/10/2026, D1 du lot Scenario) — banc de l'ÉCRAN du serveur MCP : Réglages › Serveur MCP et les cartes de
demande de lancement (frontend/shared/dz-mcp.js), l'onglet posé par le maillon de queue scripts/patch_bundle_dzmcp.py.
  1. le script partagé : copie octet pour octet, une balise dans la SPA, aucun innerHTML, routes de génération en
     liste blanche, le lancement passe par …/commencer puis la route puis …/resultat ;
  2. les textes : chaque clé mcp.* lue par le script existe en FR et en EN, assemblée (i18n_assembler --check) ;
  3. le maillon : marqueur x1, --check « déjà appliqué », aucun .bak laissé, inverse exact (avant_dzmcp == defaire),
     appelé EN TÊTE de avant_dzapify, épingles intactes (x.useState( 731, CRLF), onglet + section + rubrique ;
  4. la recherche des Réglages connaît la rubrique « mcp ».
Run (depuis backend/) : & $PY tests/test_mcp_ecran.py"""
import json, os, pathlib, re, subprocess, sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import tempfile
_tmp = pathlib.Path(tempfile.mkdtemp(prefix="dzmcpe_"))
os.environ["DEEPOTUS_DATA_DIR"] = str(_tmp)
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{(_tmp / 't.db').as_posix()}"
_ICI = pathlib.Path(__file__).resolve().parent
REPO = _ICI.parent.parent
sys.path.insert(0, str(_ICI.parent))
sys.path.insert(0, str(_ICI))
sys.path.insert(0, str(REPO / "scripts"))

ok = fail = 0
def check(label, cond, detail=""):
    global ok, fail
    if cond: ok += 1; print(f"  PASS  {label}")
    else: fail += 1; print(f"  FAIL  {label} {detail}")


SRC = REPO / "frontend" / "shared" / "dz-mcp.js"
DIST = REPO / "frontend" / "dist" / "shared" / "dz-mcp.js"
js = SRC.read_text(encoding="utf-8")

print("[1] le script partagé")
check("1.1 copie identique dans frontend/dist/shared", DIST.read_bytes() == SRC.read_bytes())
html = (REPO / "frontend" / "dist" / "index.html").read_text(encoding="utf-8")
check("1.2 une balise classique dans la SPA", html.count('<script src="/shared/dz-mcp.js"></script>') == 1)
check("1.3 aucun innerHTML", ".innerHTML" not in js and "insertAdjacentHTML" not in js)
check("1.4 les trois routes de génération en liste blanche, celles des cartes de Campagnes",
      'var ROUTES = { video: "/api/generate", image: "/api/images/generate", voix: "/api/audio/voiceover" };' in js)
i_l = js.index("async function lancer(d)")
lanc = js[i_l:js.index("async function refuser(d)")]
check("1.5 le lancement : …/commencer, PUIS la route figée vérifiée, PUIS …/resultat",
      lanc.index("/commencer") < lanc.index("c.route !== ROUTES[c.genre]") < lanc.index("window.fetch(c.route")
      < lanc.index("/resultat"))
check("1.6 un clic en cours ne relance pas (occupees)", "if (occupees[d.id])" in lanc)
check("1.7 window.__dzMcp expose monter (Réglages) et le sondage", "window.__dzMcp = { monter: monter" in js)
check("1.8 le montant est sur la carte ET sur le bouton Lancer",
      'T("mcp.carte.cout", { usd: usd(d.usd) })' in js and 'T("mcp.carte.lancer", { usd: usd(d.usd) })' in js)

print("\n[2] les textes")
dico = json.loads((REPO / "frontend" / "shared" / "i18n" / "mcp.json").read_text(encoding="utf-8"))
cles = set(re.findall(r'T\("(mcp\.[a-z0-9_.]+)"', js)) | set(re.findall(r'"(mcp\.journal\.[a-z]+)"', js))
cles |= {"mcp.genre.image", "mcp.genre.video", "mcp.genre.voix", "mcp.nature.lecture", "mcp.nature.devis",
         "mcp.nature.demande", "mcp.reglages.onglet"}
cles = {k for k in cles if not k.endswith(".")}
manque = sorted(k for k in cles if k not in dico)
check("2.1 chaque clé lue existe dans mcp.json", not manque, manque)
check("2.2 FR et EN non vides, trois segments", all(v.get("fr") and v.get("en") and len(k.split(".")) == 3
                                                    for k, v in dico.items()))
r = subprocess.run([sys.executable, str(REPO / "scripts" / "i18n_assembler.py"), "--check"], capture_output=True)
check("2.3 dictionnaire assemblé à jour (i18n_assembler --check)", r.returncode == 0, r.stdout[-200:])
check("2.4 la carte dit que rien n'est parti et que les plafonds s'appliquent",
      "plafonds" in dico["mcp.carte.aide"]["fr"] and "caps" in dico["mcp.carte.aide"]["en"])

print("\n[3] le maillon de queue dzmcp")
import patch_bundle_dzmcp as M                                      # noqa: E402
import _i18n_l1_aide as AIDE                                        # noqa: E402
B = M.BUNDLE.read_bytes().decode("utf-8")
check("3.1 marqueur x1 dans le bundle livré", B.count(M.MARKER) == 1)
check("3.2 aucun .bak_dzmcp laissé", not M.BAK.exists())
r = subprocess.run([sys.executable, str(REPO / "scripts" / "patch_bundle_dzmcp.py"), "--check"], capture_output=True,
                   env={**os.environ, "PYTHONUTF8": "1"})
check("3.3 --check : déjà appliqué", r.returncode == 0 and "appliqu" in r.stdout.decode("utf-8", "replace"), r.stdout)
avant = AIDE.avant_dzmcp(B)
# t373 : dzcurseur est posé APRÈS dzmcp ; avant_dzmcp le défait d'abord, l'aller-retour se lit donc sur le bundle d'avant dzcurseur
_SANS_CURSEUR = AIDE.avant_dzcurseur(B)
check("3.4 avant_dzmcp == defaire, et le bundle d'avant ne connaît pas l'onglet",
      avant == M.defaire(_SANS_CURSEUR) and "mcp.reglages.onglet" not in avant and M.appliquer(avant) == _SANS_CURSEUR)
src = (_ICI / "_i18n_l1_aide.py").read_text(encoding="utf-8")
i = src.index("def avant_dzapify(")
check("3.5 avant_dzmcp appelé EN TÊTE de avant_dzapify", "avant_dzmcp(bundle)" in src[i:src.index("def ", i + 10)])
raw = M.BUNDLE.read_bytes()
check("3.6 épingles : x.useState( 731, v2.8.0 x4, CRLF homogène",
      B.count("x.useState(") == 731 and B.count("v2.8.0") == 4 and raw.count(b"\r\n") > 15000
      and raw.count(b"\n") == raw.count(b"\r\n"))
check("3.7 l'onglet, la section ?section=, le corps et la rubrique de recherche",
      '{k:"mcp",l:dzT("mcp.reglages.onglet")}' in B and '"pricing","mcp"];/*dzmcp*/' in B
      and '"data-dz-mcp-hote":"1"' in B and 'mcp:dzT("mcp.reglages.onglet")' in B)
check("3.8 le corps appelle window.__dzMcp.monter par une ref, sans hook", "window.__dzMcp.monter(el)" in M.HOTE
      and "useState" not in M.HOTE and "useEffect" not in M.HOTE)
check("3.9 le patcher lit et écrit en octets", "read_text(" not in (REPO / "scripts" / "patch_bundle_dzmcp.py").read_text("utf-8"))

print("\n[4] la recherche des Réglages")
from app.api import settings_routes as SR                            # noqa: E402
check("4.1 rubrique « mcp » et une entrée d'index qui parle de Claude Code",
      SR._RUBRIQUES.get("mcp") == "Serveur MCP" and any(s == "mcp" and "claude" in m for s, _l, m in SR._INDEX_FIXE))
check("4.2 le libellé serveur = le libellé FR de l'onglet", SR._RUBRIQUES["mcp"] == dico["mcp.reglages.onglet"]["fr"])

print(f"\n{ok} passed, {fail} failed")
sys.exit(1 if fail else 0)
