"""L'Établi — outils de préparation, côté PAGE (plan 2026-09-03-plan-etabli). Tâche #88 PR A (T2, 04/10/2026) :
« Réparer en un clic » dans la fiche, écriture SEULE (ecrireSeule), le détail dans la barre.

Les aides `_lire`, `_code`, `_node`, `_fonction_etabli`, `_fonction_etabli_async` sont RECOPIÉES de
test_etabli_canevas.py (une trentaine de lignes) plutôt qu'importées d'un module de 9 700 lignes qui figerait
`settings` deux fois. Les fonctions LIVRÉES sont exécutées sous node avec un faux DOM minimal.
Témoin positif : la base (a832d79a) n'a pas de réparation du maillage.
Run : cd backend ; & $PY -m pytest tests/test_etabli_outils_page.py -q
"""
import json
import pathlib
import re
import shutil
import subprocess
import sys

import pytest

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend"
BASE = "a832d79a"


def _lire(rel: str) -> str:
    return (FRONT / rel).read_text(encoding="utf-8")


def _code(rel: str) -> str:
    """Le fichier SANS ses commentaires `/* … */` — pour les assertions NÉGATIVES."""
    return re.sub(r"/\*.*?\*/", "", _lire(rel), flags=re.S)


def _node(source: str) -> str:
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : la règle ne peut pas être EXÉCUTÉE ici")
    r = subprocess.run([node, "-e", source], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:800]
    return r.stdout.decode("utf-8", "replace")


def _fonction_etabli(nom: str) -> str:
    js = _lire("etabli/etabli.js")
    i = js.find("\nfunction " + nom + "(")
    assert i >= 0, f"fonction {nom} introuvable dans etabli.js"
    return js[i:js.index("\n}\n", i) + 2]


def _fonction_etabli_async(nom: str) -> str:
    js = _lire("etabli/etabli.js")
    i = js.find("\nasync function " + nom + "(")
    assert i >= 0, f"fonction async {nom} introuvable dans etabli.js"
    return js[i:js.index("\n}\n", i) + 2]


def _objet_etabli(nom: str) -> str:
    """Une constante objet/tableau d'etabli.js sur PLUSIEURS lignes, verbatim (jusqu'au `};` ou `];` de fin)."""
    js = _lire("etabli/etabli.js")
    m = re.search(r"^const " + nom + r" = [\s\S]*?[\]}];$", js, re.M)
    assert m, f"constante {nom} introuvable dans etabli.js"
    return m.group(0) + "\n"


def test_temoin_la_base_n_a_pas_la_reparation_du_maillage():
    b = subprocess.run(["git", "show", f"{BASE}:frontend/etabli/etabli.js"], capture_output=True, cwd=str(RACINE)).stdout
    assert b and b"reparer_maillage" not in b and b"ecrireSeule" not in b


def test_la_surface_route_ordre_bouton_et_cablage():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'reparer_maillage: "/api/etabli/reparer-maillage"' in js
    # l'ordre tient sur UNE ligne (les bancs le lisent ainsi), reparer_maillage la ferme
    assert ('const ORDRE_ECRITURE = ["transformer", "assise", "reparer", "extraire", "couper", '
            '"reparer_maillage"];') in js
    assert 'const ACTIONS_PAR_DEFAUT = ["souder", "doublons", "degeneres", "normales"];' in js
    fiche = _fonction_etabli("rendreFiche")
    assert '<button id="fReparerMaillage" title="' in fiche and "Réparer en un clic" in fiche
    assert 'ecrireSeule("reparer_maillage", { actions })' in code and "direBilanReparation(bilan.derniere)" in code
    assert '"[data-action]:checked"' in fiche
    assert 'if (!actions.length) { direRefus("cochez au moins une action de réparation"); return; }' in fiche
    # la route du serveur a la même liste par défaut que la page
    from_py = (RACINE / "backend/app/services/mesh_repair.py").read_text(encoding="utf-8")
    assert 'PAR_DEFAUT = ("souder", "doublons", "degeneres", "normales")' in from_py


HARNAIS = r"""
let S = { a: { job: "j" }, enAttente: [] }, _ecritEnCours = false;
const REFUS = [], AVIS = [], APPELS = [];
let BILAN = { ecrites: ["reparer_maillage"], derniere: { version: 3 }, echec: null };
function direRefus(m) { REFUS.push(m); }
function direAvis(m) { AVIS.push(m); }
function noterAttente(op, charge, source) { S.enAttente.push({ operation: op, charge, source }); APPELS.push(["noter", op, charge]); }
async function ecrireVersion() { APPELS.push(["ecrire", S.enAttente.map((t) => t.operation)]); const b = BILAN;
  if (b && b.ecrites.length) S.enAttente.length = 0; return b; }
function rendreAttente() { APPELS.push(["rendre"]); }
"""


def _executer(corps: str) -> dict:
    src = (_objet_etabli("LIBELLE_OP") + _objet_etabli("LIBELLE_ACTION") + _objet_etabli("ACTIONS_PAR_DEFAUT")
           + HARNAIS + _fonction_etabli_async("ecrireSeule") + _fonction_etabli("direBilanReparation")
           + "\n(async () => { const R = {};\n" + corps + "\nconsole.log(JSON.stringify(R)); })();")
    return json.loads(_node(src).strip().splitlines()[-1])


def test_ecrire_seule_refuse_derriere_une_file_et_entre_seule_dans_l_entonnoir():
    R = _executer("""
S.enAttente.push({ operation: "transformer", charge: {} });
R.file = await ecrireSeule("reparer_maillage", { actions: ["souder"] });
R.refus = REFUS.slice(); R.appels = APPELS.slice();
S.enAttente.length = 0; REFUS.length = 0; APPELS.length = 0;
_ecritEnCours = true; R.encours = await ecrireSeule("reparer_maillage", { actions: ["souder"] }); _ecritEnCours = false;
R.encoursRefus = REFUS.slice();
S.a = null; R.vide = await ecrireSeule("reparer_maillage", { actions: ["souder"] }); S.a = { job: "j" };
REFUS.length = 0; APPELS.length = 0;
R.ok = await ecrireSeule("reparer_maillage", { actions: ["souder", "trous"] }); R.okAppels = APPELS.slice(); R.okFile = S.enAttente.length;
APPELS.length = 0; BILAN = { ecrites: [], derniere: null, echec: "400" };
R.ko = await ecrireSeule("reparer_maillage", { actions: ["souder"] }); R.koFile = S.enAttente.length; R.koAppels = APPELS.slice();
""")
    assert R["file"] is None and "1 modification(s) en attente" in R["refus"][0] and "réparer le maillage" in R["refus"][0]
    assert R["appels"] == [], "derrière une file, RIEN n'est noté ni écrit"
    assert R["encours"] is None and "écriture est en cours" in R["encoursRefus"][0] and R["vide"] is None
    assert R["ok"]["derniere"]["version"] == 3 and R["okFile"] == 0
    assert R["okAppels"] == [["noter", "reparer_maillage", {"actions": ["souder", "trous"]}], ["ecrire", ["reparer_maillage"]]]
    # refusée par le serveur : la ligne ressort de la file, la barre est refaite
    assert R["ko"] is None and R["koFile"] == 0 and R["koAppels"][-1] == ["rendre"]


def test_le_detail_de_la_reparation_est_dit_dans_la_barre():
    R = _executer("""
direBilanReparation({ version: 4, source: { actions: ["souder", "normales", "trous"], ferme_avant: false, ferme_apres: false,
  pieces: [{ soudes: 2, doublons: 0, degeneres: 1, retournes: 5, trous: { bouches: 1, non_bouches: 2 } },
           { soudes: 1, doublons: 3, degeneres: 0, retournes: 0, trous: { bouches: 0, non_bouches: 0 } }] } });
direBilanReparation({ version: 5, source: { actions: ["souder"], ferme_avant: true, ferme_apres: true,
  pieces: [{ soudes: 0, doublons: 0, degeneres: 0, retournes: 0, trous: null }] } });
direBilanReparation({ version: 6, source: { actions: ["normales"], ferme_avant: true, ferme_apres: false, pieces: [] } });
direBilanReparation(null);
R.avis = AVIS.slice();
""")
    a = R["avis"]
    assert len(a) == 3, a
    assert a[0] == ("maillage réparé (version 4) : 3 sommet(s) soudé(s), 3 doublon(s), 1 triangle(s) plat(s), 5 retourné(s), "
                    "1 trou(s) bouché(s), 2 NON bouché(s) (raisons dans la fiche) — encore ouvert"), a[0]
    assert "trou" not in a[1] and a[1].endswith("— fermé"), "sans l'action « trous », on n'en parle pas"
    assert a[2].endswith("fermé avant, OUVERT après")


def test_la_fiche_coche_tout_sauf_les_trous_et_lit_les_cases_cochees():
    R = _executer("""
const html = (""" + json.dumps(_fonction_etabli("rendreFiche")) + """).match(/<div class="reparer-actions">\\$\\{([\\s\\S]*?)\\}<\\/div>/)[1];
R.cases = eval(html);
""")
    cases = R["cases"]
    for a in ("souder", "doublons", "degeneres", "normales"):
        assert f'data-action="{a}" checked>' in cases, a
    assert 'data-action="trous">' in cases and 'data-action="trous" checked' not in cases
    assert "trous bouchés" in cases and "sommets confondus" in cases


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
