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



# ══ PR B : L'IMPRIMANTE ET LE CONTOUR DU PLATEAU (tâche #88, plan-etabli T4) ═══════════════════════════════════════
def _fonction_viewer(nom: str) -> str:
    js = _lire("lib3d/viewer.js")
    i = js.find("\nfunction " + nom + "(")
    if i < 0:
        i = js.find("\nexport function " + nom + "(")
    assert i >= 0, f"fonction {nom} introuvable dans viewer.js"
    return js[i:js.index("\n}\n", i) + 2].replace("\nexport function", "\nfunction")


FAUX_THREE = r"""
class Vector3 { constructor(x, y, z) { this.x = x || 0; this.y = y || 0; this.z = z || 0; } }
class Group { constructor() { this.children = []; this.name = ""; } add(o) { this.children.push(o); }
  traverse(f) { f(this); this.children.forEach((c) => c.traverse ? c.traverse(f) : f(c)); } updateMatrixWorld() {} }
class BufferGeometry { setFromPoints(p) { this.points = p.map((q) => [q.x, q.y, q.z]); return this; } dispose() { this.libre = true; } }
class LineBasicMaterial { constructor(o) { this.color = o.color; } dispose() {} }
class LineLoop { constructor(g, m) { this.geometry = g; this.material = m; } }
const THREE = { Vector3, Group, BufferGeometry, LineBasicMaterial, LineLoop };
const LEVEE_REGLES = 0.0015;
"""


def test_le_contour_du_plateau_est_dessine_au_coin_des_regles_et_efface():
    src = (FAUX_THREE + "const _contours = new WeakMap();\n"
           + re.search(r"^const COULEUR_CONTOUR = .*;$", _lire("lib3d/viewer.js"), re.M).group(0) + "\n"
           + re.search(r"^const COULEUR_EXCLUE = .*;$", _lire("lib3d/viewer.js"), re.M).group(0) + "\n"
           + _fonction_viewer("_effacerContour") + _fonction_viewer("dessinerContourPlateau"))
    R = json.loads(_node(src + r"""
const scene = { objets: [], add(o) { this.objets.push(o); }, remove(o) { this.objets = this.objets.filter((x) => x !== o); } };
const api = { scene };
const g = { axe: "y", u: "x", v: "z", cote: 10, niveau: -0.5, coin: { x: -5, y: -0.5, z: 5 }, sens: { u: -1, v: -1 } };
const r = dessinerContourPlateau(api, g, { l: 4, p: 2, zones: [[3, 0, 4, 1], [1, "x", 2, 3]] });
const R = { zones: r.zones, n: scene.objets.length, rects: scene.objets[0].children.map((c) => [c.material.color, c.geometry.points]) };
dessinerContourPlateau(api, g, { l: 4, p: 2 }); R.apres = scene.objets.length;
R.nul = dessinerContourPlateau(api, g, null); R.vide = scene.objets.length;
R.sansCote = dessinerContourPlateau(api, g, { l: 0, p: 2 });
console.log(JSON.stringify(R));
""").strip().splitlines()[-1])
    assert R["zones"] == 1 and R["n"] == 1, R                     # la zone illisible est écartée
    couleur, pts = R["rects"][0]
    niv = -0.5 + 10 * 0.0015 * 2
    assert pts == [[-5, niv, 5], [-9, niv, 5], [-9, niv, 3], [-5, niv, 3]], pts      # au coin, DANS le sens des règles
    assert R["rects"][1][1][0] == [-8, niv, 5] and R["rects"][0][0] != R["rects"][1][0]   # la zone exclue, autre couleur
    assert R["apres"] == 1, "un redessin REMPLACE, il n'empile pas"
    assert R["nul"] is None and R["vide"] == 0 and R["sansCote"] is None


HARNAIS_IMP = r"""
let S = { vueA: { id: "vue" } }, PLQ = { active: true };
const REP = { cibleMm: 80, echelle: 40, pas: null };
const PROFIL = { liste: [], actif: null, slicer: null, erreur: "" };
const APPELS = [], AVIS = [], REFUS = [];
function plateauDe() { return { coin: {} }; }
function dessinerContourPlateau(api, g, cotes) { APPELS.push(["contour", cotes]); }
function enMillimetres() { return REP.echelle !== null; }
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const BOX = { innerHTML: "" }, SEL = { ecoute: [] }, BTN = { ecoute: [] };
const $ = (s) => (s === "#imprimante" ? BOX : s === "#impProfil" ? { addEventListener: (e, f) => SEL.ecoute.push(e) }
  : s === "#impSlicer" ? { addEventListener: (e, f) => BTN.ecoute.push(e) } : null);
let REPONSES = {};
async function jget(p) { APPELS.push(["get", p]); if (REPONSES[p] instanceof Error) throw REPONSES[p]; return REPONSES[p]; }
async function jpost(p, c) { APPELS.push(["post", p, c]); if (REPONSES[p] instanceof Error) throw REPONSES[p]; return REPONSES[p]; }
function direAvis(m) { AVIS.push(m); } function direRefus(m) { REFUS.push(m); }
"""


def _imp(corps: str) -> dict:
    src = (HARNAIS_IMP + _fonction_etabli("versUnites") + _fonction_etabli("contourPlateau")
           + _fonction_etabli("rendreImprimante") + _fonction_etabli_async("chargerProfils")
           + _fonction_etabli_async("choisirProfil")
           + "\n(async () => { const R = {};\n" + corps + "\nconsole.log(JSON.stringify(R)); })();")
    return json.loads(_node(src).strip().splitlines()[-1])


CC2 = {"id": "integre:elegoo-centauri-carbon-2", "nom": "Elegoo Centauri Carbon 2", "marque": "Elegoo",
       "resume": "plateau 256 × 256 mm · <b>", "contour": {"l": 256, "p": 256, "zones": [[246, 0, 256, 20]]}}
KOBRA = {"id": "orcaslicer:Kobra", "nom": "Kobra <x>", "marque": "Anycubic", "resume": "plateau 220 × 220 mm",
         "contour": {"l": 220, "p": 220, "zones": []}}


def test_l_imprimante_se_choisit_groupee_par_marque_et_le_preset_du_slicer_est_PROPOSE():
    R = _imp("""
REPONSES["/api/print3d/profils"] = { profils: %s, actif: "integre:elegoo-centauri-carbon-2",
  actif_slicer: { nom: "Kobra <x>", id: "orcaslicer:Kobra" } };
await chargerProfils(); R.html = BOX.innerHTML; R.contour = APPELS.filter((a) => a[0] === "contour").pop(); R.ecoute = [SEL.ecoute.slice(), BTN.ecoute.slice()];
REPONSES["/api/print3d/profils/actif"] = { ok: true, actif: "orcaslicer:Kobra", profil: %s };
APPELS.length = 0; await choisirProfil("orcaslicer:Kobra"); R.post = APPELS[0]; R.avis = AVIS.slice(); R.html2 = BOX.innerHTML;
R.contour2 = APPELS.filter((a) => a[0] === "contour").pop();
REP.echelle = null; contourPlateau(); R.sansCible = APPELS.pop();
PLQ.active = false; REP.echelle = 40; contourPlateau(); R.horsPlaque = APPELS.pop();
""" % (json.dumps([CC2, KOBRA]), json.dumps(KOBRA)))
    h = R["html"]
    assert '<optgroup label="Elegoo"><option value="integre:elegoo-centauri-carbon-2" selected>' in h
    assert '<optgroup label="Anycubic"><option value="orcaslicer:Kobra">Kobra &lt;x&gt;</option>' in h
    assert "plateau 256 × 256 mm · &lt;b&gt;" in h, "le résumé du serveur, ÉCHAPPÉ"
    assert 'id="impSlicer" title="' in h and "Prendre « Kobra &lt;x&gt; » (actif dans le slicer)" in h
    assert 'id="impProfil" title="' in h and R["ecoute"] == [["change"], ["click"]]
    # le contour en UNITÉS : 256 mm / 40 mm par unité
    assert R["contour"][1] == {"l": 6.4, "p": 6.4, "zones": [[6.15, 0, 6.4, 0.5]]}, R["contour"]
    assert R["post"] == ["post", "/api/print3d/profils/actif", {"id": "orcaslicer:Kobra"}] and R["avis"] == ["imprimante : Kobra <x>"]
    assert "impSlicer" not in R["html2"], "le preset du slicer EST l'actif : plus rien à proposer"
    assert R["contour2"][1]["l"] == 5.5
    assert R["sansCible"] == ["contour", None] and R["horsPlaque"] == ["contour", None]


def test_les_refus_de_profil_sont_dits_et_la_page_vit_sans_eux():
    R = _imp("""
REPONSES["/api/print3d/profils"] = new Error("/api/print3d/profils → 500");
await chargerProfils(); R.html = BOX.innerHTML; R.contour = APPELS.filter((a) => a[0] === "contour").pop();
REPONSES["/api/print3d/profils/actif"] = new Error("→ 400"); await choisirProfil("x"); R.refus = REFUS.slice();
""")
    assert "profils d&#39;imprimante illisibles" in R["html"] and "Centauri Carbon 2" in R["html"], R["html"]
    assert R["contour"] == ["contour", None] and R["refus"] == ["imprimante refusée : → 400"]


def test_la_page_n_ecrit_aucune_unite_et_lit_le_contour_du_serveur():
    code = _code("etabli/etabli.js")
    assert "_mm" not in _fonction_etabli("contourPlateau") and "_mm" not in _fonction_etabli("rendreImprimante")
    assert "contourPlateau();" in _fonction_etabli("lireRepere")
    assert _fonction_etabli("lireRepere").index("graduerPlateau();") < _fonction_etabli("lireRepere").index("contourPlateau();")
    assert re.search(r"^chargerProfils\(\);$", code, re.M) and '<div class="imprimante" id="imprimante"></div>' in _lire("etabli/index.html")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
