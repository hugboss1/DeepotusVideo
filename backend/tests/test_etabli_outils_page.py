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
            '"reparer_maillage", "decimer"];') in js
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
           + re.search(r"^const ECART_PLATEAUX = [^;]*;", _lire("lib3d/viewer.js"), re.M).group(0) + "\n"
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
const trois = dessinerContourPlateau(api, g, { l: 4, p: 2, zones: [[3, 0, 4, 1]], plateaux: 3 });
R.trois = { dec: trois.decalages, n: trois.plateaux, rects: scene.objets[0].children.length,
            debut3: scene.objets[0].children[4].geometry.points[0], zone3: scene.objets[0].children[5].geometry.points[0] };
R.borne = dessinerContourPlateau(api, g, { l: 4, p: 2, plateaux: 40 }).plateaux;
console.log(JSON.stringify(R));
""").strip().splitlines()[-1])
    assert R["zones"] == 1 and R["n"] == 1, R                     # la zone illisible est écartée
    couleur, pts = R["rects"][0]
    niv = -0.5 + 10 * 0.0015 * 2
    assert pts == [[-5, niv, 5], [-9, niv, 5], [-9, niv, 3], [-5, niv, 3]], pts      # au coin, DANS le sens des règles
    assert R["rects"][1][1][0] == [-8, niv, 5] and R["rects"][0][0] != R["rects"][1][0]   # la zone exclue, autre couleur
    assert R["apres"] == 1, "un redessin REMPLACE, il n'empile pas"
    assert R["nul"] is None and R["vide"] == 0 and R["sansCote"] is None
    # PLUSIEURS PLATEAUX (tâche #89) : côte à côte au pas 1,25 l, chacun avec sa zone exclue, décalages RENDUS
    assert R["trois"]["dec"] == [0, 5, 10] and R["trois"]["n"] == 3 and R["trois"]["rects"] == 6, R["trois"]
    assert R["trois"]["debut3"] == [-5 - 10, niv, 5], "le 3e plateau commence à 10 unités, dans le SENS des règles"
    assert R["trois"]["zone3"] == [-5 - 13, niv, 5], "la zone exclue suit SON plateau"
    assert R["borne"] == 8


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
REP.echelle = null; contourPlateau(); R.sansCible = APPELS.pop(); REP.echelle = 40;
PLQ.plateaux = 3; contourPlateau(); R.trois = APPELS.pop()[1].plateaux; delete PLQ.plateaux;
PLQ.active = false; REP.echelle = 40; contourPlateau(); R.horsPlaque = APPELS.pop();
""" % (json.dumps([CC2, KOBRA]), json.dumps(KOBRA)))
    h = R["html"]
    assert '<optgroup label="Elegoo"><option value="integre:elegoo-centauri-carbon-2" selected>' in h
    assert '<optgroup label="Anycubic"><option value="orcaslicer:Kobra">Kobra &lt;x&gt;</option>' in h
    assert "plateau 256 × 256 mm · &lt;b&gt;" in h, "le résumé du serveur, ÉCHAPPÉ"
    assert 'id="impSlicer" title="' in h and "Prendre « Kobra &lt;x&gt; » (actif dans le slicer)" in h
    assert 'id="impProfil" title="' in h and R["ecoute"] == [["change"], ["click"]]
    # le contour en UNITÉS : 256 mm / 40 mm par unité
    assert R["contour"][1] == {"l": 6.4, "p": 6.4, "zones": [[6.15, 0, 6.4, 0.5]], "plateaux": 1}, R["contour"]
    assert R["post"] == ["post", "/api/print3d/profils/actif", {"id": "orcaslicer:Kobra"}] and R["avis"] == ["imprimante : Kobra <x>"]
    assert "impSlicer" not in R["html2"], "le preset du slicer EST l'actif : plus rien à proposer"
    assert R["contour2"][1]["l"] == 5.5
    assert R["sansCible"] == ["contour", None] and R["horsPlaque"] == ["contour", None]
    assert R["trois"] == 3, "le contour dessine autant de plateaux que le rangement en a ouverts"


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



# ══ PR C : RANGER ET MESURER, côté page (tâche #89, plan-etabli T5 et T8) ════════════════════════════════════════════
HARNAIS_RANGER = r"""
const PLQ = { active: true, pieces: [{ cle: "A" }, { cle: "B" }, { cle: "C" }], masquees: new Set(["C"]), courante: null, plateaux: 1 };
const REP = { cibleMm: 100, echelle: 10, pas: null };
const PROFIL = { actif: { contour: { l: 100, p: 100, zones: [[90, 0, 100, 20]] } } };
let S = { vueA: { id: "vue" } };
const APPELS = [], AVIS = [], REFUS = [];
const PIECES = { A: { u: 3, v: 4, l: 9.6, p: 4, rot: 0 }, B: { u: 0, v: 0, l: 4, p: 9.6, rot: 37 } };
let G = { axe: "y", u: "x", v: "z", coin: { x: -5, y: 0, z: 5 }, sens: { u: -1, v: -1 } };
function enMillimetres() { return REP.echelle !== null; }
function versUnites(v) { return enMillimetres() ? v / REP.echelle : null; }
function plateauDe() { return G; }
function empreinteDe(api, cle) { const p = PIECES[cle]; return p ? { u: p.u, v: p.v, l: p.l, p: p.p } : null; }
function rotationDe(api, cle) { return PIECES[cle].rot; }
function poserAngle(api, cle, d) { const p = PIECES[cle]; if (Math.round((d - p.rot) / 90) % 2) { const t = p.l; p.l = p.p; p.p = t; }
  p.rot = d; APPELS.push(["angle", cle, d]); return true; }
function poserCoin(api, cle, u, v) { PIECES[cle].u = u; PIECES[cle].v = v; APPELS.push(["coin", cle, +u.toFixed(6), +v.toFixed(6)]); return true; }
function marquerPiece() {} function rendreRotation() {} function noterPlan() { APPELS.push(["plan"]); }
function contourPlateau() { APPELS.push(["contour", PLQ.plateaux]); return { decalages: Array.from({ length: PLQ.plateaux }, (_, k) => k * 12.5) }; }
let REPONSE = null;
async function jpost(p, c) { APPELS.push(["post", p, JSON.parse(JSON.stringify(c))]); if (REPONSE instanceof Error) throw REPONSE; return REPONSE; }
function direAvis(m) { AVIS.push(m); } function direRefus(m) { REFUS.push(m); }
"""


def _ranger(corps: str) -> dict:
    js = _lire("etabli/etabli.js")
    marge = re.search(r"^const MARGE_PLATEAU = [^;]*;", js, re.M).group(0)
    src = (HARNAIS_RANGER + marge + "\n" + _fonction_etabli_async("arrangerPlaque")
           + "\n(async () => { const R = {};\n" + corps + "\nconsole.log(JSON.stringify(R)); })();")
    return json.loads(_node(src).strip().splitlines()[-1])


def test_ranger_envoie_des_UNITES_tourne_en_RELATIF_et_pose_dans_le_SENS_des_regles():
    R = _ranger("""
REPONSE = { plateaux: [[{ cle: "A", u: 0, v: 0, rot: 0, l: 9.6, p: 4 }], [{ cle: "B", u: 1, v: 2, rot: 90, l: 4, p: 9.6 }]],
            debordent: ["Z"], taux: [0.384, 0.1], marge: 0.2, exclusions_ignorees: 1 };
await arrangerPlaque();
R.appels = APPELS.slice(); R.avis = AVIS.slice(); R.plateaux = PLQ.plateaux; R.B = PIECES.B;
""")
    post = R["appels"][0]
    assert post == ["post", "/api/etabli/ranger", {"pieces": [{"cle": "A", "l": 9.6, "p": 4}, {"cle": "B", "l": 4, "p": 9.6}],
                                                   "plateau": [10, 10], "marge": 0.2, "rotation": True,
                                                   "exclusions": [[9, 0, 10, 2]]}], post
    assert R["plateaux"] == 2 and ["contour", 2] in R["appels"]
    # A, plateau 0 : sens u = -1 → u = -5 - 0 - 9.6 ; sens v = -1 → v = 5 - 0 - 4
    assert ["coin", "A", -14.6, 1] in R["appels"], R["appels"]
    # B : un quart de tour DE PLUS que ses 37°, puis ses côtés échangés (9.6 x 4) ; plateau 1 décalé de 12.5
    assert ["angle", "B", 127] in R["appels"] and R["B"]["l"] == 9.6 and R["B"]["p"] == 4
    assert ["coin", "B", -5 - (12.5 + 1) - 9.6, 5 - 2 - 4] in R["appels"], R["appels"]
    assert R["appels"][-1] == ["plan"], "la disposition s'enregistre comme une retouche"
    assert "rangé : 2 plateau(x), occupation 38 % · 10 %" in R["avis"][0] and "1 pièce(s) plus grande(s)" in R["avis"][0]
    assert "1 zone(s) exclue(s) loin du bord avant NON évitée(s)" in R["avis"][0]


def test_ranger_refuse_hors_plaque_hors_millimetres_et_sans_piece_visible():
    R = _ranger("""
PLQ.active = false; await arrangerPlaque(); R.a = REFUS.slice(); PLQ.active = true;
REP.echelle = null; await arrangerPlaque(); R.b = REFUS.slice(); REP.echelle = 10;
PROFIL.actif = null; await arrangerPlaque(); R.c = REFUS.slice(); PROFIL.actif = { contour: { l: 100, p: 100 } };
PLQ.masquees = new Set(["A", "B", "C"]); await arrangerPlaque(); R.d = REFUS.slice(); PLQ.masquees = new Set();
REPONSE = new Error("→ 400"); await arrangerPlaque(); R.e = REFUS.slice(); R.posts = APPELS.filter((a) => a[0] === "post").length;
R.poses = APPELS.filter((a) => a[0] === "coin").length;
""")
    assert "passe d'abord sur la plaque" in R["a"][0]
    assert "pose une taille cible" in R["b"][1] and "pose une taille cible" in R["c"][2]
    assert "aucune pièce visible" in R["d"][3] and "rangement refusé : → 400" in R["e"][4]
    assert R["posts"] == 1 and R["poses"] == 0, "un seul appel (le refus serveur), rien posé"


def test_ranger_sans_rien_lire_de_REP_echelle():
    f = _fonction_etabli_async("arrangerPlaque")
    assert "REP.echelle" not in f and "versUnites(c.l)" in f and "decalages" in f
    assert '<button class="outil-btn" id="btnArranger"></button>' in _lire("etabli/index.html")
    assert '$("#btnArranger").addEventListener("click", arrangerPlaque);' in _lire("etabli/etabli.js")


def _mesure(nom: str) -> str:
    js = _lire("lib3d/mesure.js")
    m = re.search(r"^export function " + nom + r"\(", js, re.M)
    assert m, nom
    return js[m.start():js.index("\n}\n", m.start()) + 2].replace("export function", "function", 1) + "\n"


def test_la_mesure_rend_une_distance_des_composantes_et_l_angle_DIEDRE_EXECUTES():
    src = _mesure("distance") + _mesure("composantes") + _mesure("angleDeFaces") + """
console.log(JSON.stringify({ d: distance({x:0,y:0,z:0},{x:3,y:4,z:0}),
  c: composantes({x:1,y:2,z:3},{x:4,y:6,z:3}),
  plat: angleDeFaces({x:0,y:1,z:0},{x:0,y:2,z:0}), droit: angleDeFaces({x:0,y:1,z:0},{x:1,y:0,z:0}),
  rentrant: angleDeFaces({x:0,y:1,z:0},{x:0,y:-1,z:0}), nul: angleDeFaces({x:0,y:0,z:0},{x:0,y:1,z:0}) === null,
  absent: angleDeFaces(null, {x:0,y:1,z:0}) === null,
  /* (1, 2, 3) avec lui-même : le cosinus calculé vaut 1.0000000000000002 — sans la borne, acos rend NaN */
  memes: angleDeFaces({x:1,y:2,z:3},{x:1,y:2,z:3}), c3: composantes({x:0,y:0,z:0},{x:2,y:3,z:6}).norme }));
"""
    r = json.loads(_node(src))
    assert r["d"] == 5 and r["c"] == {"dx": 3, "dy": 4, "dz": 0, "norme": 5}
    assert r["plat"] == 180 and r["droit"] == 90 and r["rentrant"] == 0 and r["nul"] is True and r["absent"] is True
    assert r["memes"] == 180 and r["c3"] == 7


HARNAIS_MESURE = r"""
const THREE = { Vector3: class { constructor(x, y, z) { this.x = x; this.y = y; this.z = z; } },
  Group: class { constructor() { this.children = []; } add(o) { this.children.push(o); } traverse(f) { f(this); this.children.forEach(f); } },
  BufferGeometry: class { setFromPoints(p) { this.n = p.length; return this; } dispose() {} },
  PointsMaterial: class { constructor(o) { this.o = o; } dispose() {} }, LineBasicMaterial: class { constructor(o) { this.o = o; } dispose() {} },
  Points: class { constructor(g, m) { this.geometry = g; this.material = m; this.type = "Points"; } },
  Line: class { constructor(g, m) { this.geometry = g; this.material = m; this.type = "Line"; } } };
const scene = { objets: [], add(o) { this.objets.push(o); }, remove(o) { this.objets = this.objets.filter((x) => x !== o); } };
let S = { vueA: { scene } };
const BOX = { innerHTML: "" };
const $ = (s) => { if (s !== "#repereMesure") throw new TypeError(s); return BOX; };
const REFUS = [];
function direRefus(m) { REFUS.push(m); }
let ECHELLE = null;
function uniteCourante() { return ECHELLE ? "mm" : "u. glTF"; }
function fmtMesure(v) { return (ECHELLE ? v * ECHELLE : v).toFixed(2); }
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
"""


def test_la_mesure_se_lit_dans_le_rail_se_trace_et_se_range():
    js = _lire("etabli/etabli.js")
    mes = re.search(r"^const MESURE = [^;]*;", js, re.M).group(0)
    src = (HARNAIS_MESURE + _mesure("composantes") + _mesure("angleDeFaces") + mes + "\n"
           + _fonction_etabli("tracerMesure") + _fonction_etabli("mesurerAuClic") + _fonction_etabli("rangerMesure")
           + _fonction_etabli("rendreMesure") + r"""
const R = {};
const pt = (x, y, z) => ({ x, y, z });
mesurerAuClic({ name: "socle<x>" }, { point: pt(0, 0, 0), normale: pt(0, 1, 0) }); R.un = [BOX.innerHTML, scene.objets.length, scene.objets[0].children.length];
mesurerAuClic({ name: "pied" }, { point: pt(3, 4, 0), normale: pt(1, 0, 0) }); R.deux = [BOX.innerHTML, scene.objets.length, scene.objets[0].children.map((c) => c.type)];
ECHELLE = 10; rendreMesure(); R.mm = BOX.innerHTML;
mesurerAuClic({ name: "x" }, { point: pt(9, 9, 9), normale: null }); R.trois = [BOX.innerHTML, scene.objets.length];
mesurerAuClic(null, null); R.vide = REFUS.slice();
rangerMesure(); R.range = [BOX.innerHTML, scene.objets.length];
console.log(JSON.stringify(R));
""")
    R = json.loads(_node(src).strip().splitlines()[-1])
    assert R["un"] == ["<b>mesure</b> : clique un second point", 1, 1]
    html, n, types = R["deux"]
    assert n == 1 and types == ["Points", "Line"], "un seul tracé, remplacé"
    assert "socle&lt;x&gt; → pied" in html and "d = 5.00 u. glTF (x 3.00 · y 4.00 · z 0.00)" in html and "angle des faces : 90.0°" in html
    assert "d = 50.00 mm (x 30.00" in R["mm"], "la lecture suit l'unité (fmtMesure / uniteCourante)"
    assert R["trois"] == ["<b>mesure</b> : clique un second point", 1], "un troisième clic recommence"
    assert R["vide"] == ["mesure : clique sur le modèle"]
    assert R["range"] == ["", 0]


def test_la_mesure_est_un_MODE_range_en_le_quittant_et_lue_par_lireRepere():
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'const MODES_GESTE = ["selection", "glisser", "assise", "couteau", "mesure"];' in js
    assert 'import { angleDeFaces, composantes } from "/lib3d/mesure.js";' in js
    assert 'if (GESTE.mode === "mesure" && mode !== "mesure") rangerMesure();' in _fonction_etabli("armerGeste")
    assert 'if (GESTE.mode === "mesure") { mesurerAuClic(obj, touche); return; }' in code
    assert code.index('if (GESTE.mode === "assise") { poserSurFace(obj, touche); return; }') \
        < code.index('if (GESTE.mode === "mesure") { mesurerAuClic(obj, touche); return; }')
    assert "rendreMesure();" in _fonction_etabli("lireRepere") and 'id="repereMesure"' in _fonction_etabli("rendreRepere")
    assert 'GESTE.mode !== "mesure") return false;' in _fonction_etabli("toucheClavierOutils")
    assert '<button class="outil-btn" id="btnMesure"></button>' in _lire("etabli/index.html")
    assert ".repere-mesure" in _lire("etabli/etabli.css")
    f = _fonction_etabli("rendreMesure")
    assert "fmtMesure(" in f and "uniteCourante()" in f and "esc(" in f


# ── tâche #89 PR D : extraire une par une, décimer dans la lignée ─────────────────────────────────────────────────
BASE_D = "2de62acc"


def test_temoin_la_base_d_n_a_ni_une_par_une_ni_decimer():
    b = subprocess.run(["git", "show", f"{BASE_D}:frontend/etabli/etabli.js"], capture_output=True, cwd=str(RACINE)).stdout
    assert b and b"pSeparement" not in b and b'decimer: "/api/etabli/decimer"' not in b
    assert b'noterAttente("extraire", idx, source);' in b, "la base mettait une LISTE nue en file"


ENTONNOIR = r"""
let S = { a: { job: "j", version: 1 }, enAttente: [] }, _ecritEnCours = false;
const CORPS = [], REFUS = [], NOTES = [];
let PROCHAINE = 2;
async function jpost(route, corps) { CORPS.push([route, JSON.parse(JSON.stringify(corps))]); return { version: PROCHAINE++ }; }
async function jget() { return {}; }
function rendreAttente() {} function rendreChrono() {}
async function ouvrirPrincipale() { return false; }
async function capturerVignette() {}
function direRefus(m) { REFUS.push(m); } function direGeometrie() {}
function noterAttente(op, charge, source) { NOTES.push([op, charge, source]); S.enAttente.push({ operation: op, charge, source }); }
let COCHE = null;
const $ = (q) => (q === "#pSeparement" ? COCHE : null);
const noeudsRetenus = () => ({ noeuds: [4, 7], source: "nom" });
"""


def _entonnoir(corps: str) -> dict:
    src = (_objet_etabli("ORDRE_ECRITURE") + _objet_etabli("ROUTES") + _objet_etabli("LIBELLES_ATTENTE") + ENTONNOIR
           + _fonction_etabli("fileOrdonnee") + _fonction_etabli("separerSelection")
           + _fonction_etabli_async("ecrireVersion")
           + "\n(async () => { const R = {};\n" + corps + "\nconsole.log(JSON.stringify(R)); })();")
    return json.loads(_node(src).strip().splitlines()[-1])


def test_separer_porte_le_choix_une_par_une_et_les_TROIS_sites_lisent_la_meme_charge():
    R = _entonnoir("""
separerSelection(); R.sans = NOTES.slice(); R.lib0 = LIBELLES_ATTENTE.extraire(S.enAttente[0]);
COCHE = { checked: false }; S.enAttente.length = 0; NOTES.length = 0; separerSelection(); R.decoche = NOTES[0][1];
COCHE = { checked: true }; S.enAttente.length = 0; NOTES.length = 0; separerSelection(); R.coche = NOTES[0];
R.lib1 = LIBELLES_ATTENTE.extraire(S.enAttente[0]);
S.enAttente.push({ operation: "transformer", charge: { 2: { t: [1, 0, 0] } } });
await ecrireVersion(); R.corps = CORPS.slice(); R.refus = REFUS.slice();
""")
    assert R["sans"] == [["extraire", {"noeuds": [4, 7], "separement": False}, "nom"]], "sans case : ensemble"
    assert R["decoche"] == {"noeuds": [4, 7], "separement": False}
    assert R["coche"] == ["extraire", {"noeuds": [4, 7], "separement": True}, "nom"]
    assert R["lib0"] == "2 nœud(s) à séparer" and R["lib1"] == "2 nœud(s) à séparer — un fichier par élément"
    # l'ordre de la page (transformer d'abord), puis l'extraction CHAÎNÉE sur la version que transformer a rendue
    assert R["corps"] == [["/api/etabli/transformer", {"job": "j", "version": 1, "transforms": {"2": {"t": [1, 0, 0]}}}],
                          ["/api/etabli/extraire", {"job": "j", "version": 2, "noeuds": [4, 7], "separement": True}]]
    assert R["refus"] == []
    code = _code("etabli/etabli.js")
    assert "t.charge.length" not in code, "la charge d'extraire n'est plus une liste NULLE PART"
    assert 'id="pSeparement"' in _fonction_etabli("rendreParties") and ".sep-mode" in _lire("etabli/etabli.css")
    assert '<label class="sep-mode" title="' in _fonction_etabli("rendreParties")


def test_decimer_passe_par_l_entonnoir_SEUL_avec_le_preset_choisi():
    R = _entonnoir("""
S.enAttente.push({ operation: "decimer", charge: { preset: "game" } });
R.lib = LIBELLES_ATTENTE.decimer(S.enAttente[0]);
R.lib2 = LIBELLES_ATTENTE.decimer({ charge: { target_tris: 1234 } });
await ecrireVersion(); R.corps = CORPS.slice();
""")
    assert R["corps"] == [["/api/etabli/decimer", {"job": "j", "version": 1, "preset": "game"}]]
    assert R["lib"] == "décimer vers game triangles" and R["lib2"] == "décimer vers 1234 triangles"
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'decimer: "/api/etabli/decimer",' in js and 'decimer: "décimer"' in _objet_etabli("LIBELLE_OP")
    assert 'ecrireSeule("decimer", { preset: $("#fDecPreset").value })' in code
    assert "direBilanDecimation(bilan.derniere)" in code
    fiche = _fonction_etabli("rendreFiche")
    assert '<button id="fDecimer" title="' in fiche and '<select id="fDecPreset" title="' in fiche


def test_chaque_option_de_decimation_est_une_CLE_du_service_et_dit_son_vrai_compte():
    """Le `<select>` ne recopie pas des chiffres : chaque `value` existe dans `mesh_optimize.PRESETS` et le libellé porte
    le compte que le service applique VRAIMENT ; « jeu » est choisi d'office (décision de l'utilisateur, 05/10)."""
    src = (RACINE / "backend/app/services/mesh_optimize.py").read_text(encoding="utf-8")
    presets = {k: int(v) for k, v in re.findall(r'^\s+"([a-z]+)": (\d+),', src.split("PRESETS = {", 1)[1].split("}", 1)[0], re.M)}
    fiche = _fonction_etabli("rendreFiche")
    bloc = fiche.split('id="fDecPreset"', 1)[1].split("</select>", 1)[0]
    options = re.findall(r'<option value="([a-z]+)"( selected)?>([^<]+)</option>', bloc)
    assert [o[0] for o in options] == ["ultra", "high", "game", "detailed"]
    for cle, _sel, libelle in options:
        assert int(re.sub(r"[^0-9]", "", libelle)) == presets[cle], (cle, libelle)
    assert [o[0] for o in options if o[1]] == ["game"]


def test_le_bilan_de_la_decimation_dit_les_VRAIS_comptes():
    src = ("const AVIS = []; function direAvis(m) { AVIS.push(m); }\n" + _fonction_etabli("direBilanDecimation") + """
direBilanDecimation({ version: 6, source: { before: { tris: 7200 }, after: { tris: 1003 }, reduction_pct: 86.1, aggressive: false } });
direBilanDecimation({ version: 7, source: { before: { tris: 900 }, after: { tris: 101 }, reduction_pct: 88.8, aggressive: true } });
direBilanDecimation({ version: 9, source: { before: { tris: 14400 }, after: { tris: 463 }, reduction_pct: 96.8, aggressive: true,
  cible_atteinte: false, target_tris: 100 } });
direBilanDecimation({ version: 8, source: {} }); direBilanDecimation(null);
console.log(JSON.stringify(AVIS));
""")
    assert json.loads(_node(src).strip().splitlines()[-1]) == [
        "décimé (version 6) : 7200 → 1003 triangles (−86.1 %)",
        "décimé (version 7) : 900 → 101 triangles (−88.8 %), passe agressive",
        "décimé (version 9) : 14400 → 463 triangles (−96.8 %), passe agressive — cible de 100 NON atteinte, "
        "le maillage ne se simplifie pas plus"]

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
