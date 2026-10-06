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
            '"reparer_maillage", "creuser", "decimer"];') in js
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
function marquerPiece() {} function rendreRotation() {} function lirePieceCourante() {} function noterPlan() { APPELS.push(["plan"]); }
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
           + _fonction_etabli("contradictionDeLaFile") + _fonction_etabli_async("ecrireVersion")
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

# ── tâche #89 PR E : creuser ───────────────────────────────────────────────────────────────────────────────────────
BASE_E = "df8cce69"


def test_temoin_la_base_e_n_a_pas_de_creusage():
    b = subprocess.run(["git", "show", f"{BASE_E}:frontend/etabli/etabli.js"], capture_output=True, cwd=str(RACINE)).stdout
    assert b and b"fCreuser" not in b and b'creuser: "/api/etabli/creuser"' not in b


def _gestionnaire_creuser() -> str:
    fiche = _fonction_etabli("rendreFiche")
    debut = '$("#fCreuser").addEventListener("click", async () => {'
    corps = fiche.split(debut, 1)[1].split("\n  });", 1)[0]
    return "async function cliquerCreuser() {" + corps + "\n}\n"



def _creuser(corps: str) -> dict:
    src = ("let REP = { echelle: null };\nconst REFUS = [], AVIS = [], ECRIT = [];\nlet SAISIE = \"2\", RETENUS = { noeuds: [], source: undefined };\n"
           "const $ = (q) => (q === \"#fParoi\" ? { value: SAISIE } : null);\n"
           "function direRefus(m) { REFUS.push(m); } function direAvis(m) { AVIS.push(m); }\n"
           "const noeudsRetenus = () => RETENUS;\n"
           "async function ecrireSeule(op, charge, source) { ECRIT.push([op, charge, source === undefined ? null : source]);\n"
           "  return { derniere: { version: 5, source: { paroi: charge.paroi, pieces: [{}, {}], avertissement: null, limite: \"L\" } } }; }\n"
           + _fonction_etabli("enMillimetres") + _fonction_etabli("versUnites") + _fonction_etabli("uniteCourante")
           + _fonction_etabli("fmtMesure") + _fonction_etabli("direBilanCreusage") + _gestionnaire_creuser()
           + "\n(async () => { const R = {};\n" + corps + "\nconsole.log(JSON.stringify(R)); })();")
    return json.loads(_node(src).strip().splitlines()[-1])


def test_creuser_EXIGE_une_taille_cible_convertit_par_la_garde_et_dit_le_bilan():
    R = _creuser("""
await cliquerCreuser(); R.sansCible = [REFUS.slice(), ECRIT.length];
REP.echelle = 8; REFUS.length = 0;
SAISIE = "0"; await cliquerCreuser(); SAISIE = "abc"; await cliquerCreuser(); R.absurde = [REFUS.slice(), ECRIT.length];
SAISIE = "2"; await cliquerCreuser(); R.tout = ECRIT[0]; R.avis = AVIS.slice();
RETENUS = { noeuds: [3, 1], source: "nom" }; await cliquerCreuser(); R.sel = ECRIT[1];
""")
    assert R["sansCible"] == [["pose une taille cible : une paroi en millimètres n'a de sens qu'avec une échelle"], 0]
    assert R["absurde"] == [["paroi : un nombre de millimètres > 0"] * 2, 0]
    # 2 millimètres ÷ 8 millimètres par unité = 0,25 unité ; rien de retenu = tout le modèle (null)
    assert R["tout"] == ["creuser", {"paroi": 0.25, "paroi_millimetres": 2, "noeuds": None}, None]
    assert R["sel"] == ["creuser", {"paroi": 0.25, "paroi_millimetres": 2, "noeuds": [3, 1]}, "nom"]
    assert R["avis"] == ["creusé (version 5) : paroi 2,00 mm sur 2 pièce(s) — limite : L"]


def test_le_bilan_du_creusage_dit_ce_qui_ne_tient_pas_DANS_l_unite_courante():
    R = _creuser("""
REP.echelle = 10;
direBilanCreusage({ version: 7, source: { paroi: 0.3, paroi_max: 0.125, pieces: [{}], avertissement: "12 triangle(s) effondré(s)", limite: "L" } });
REP.echelle = null;
direBilanCreusage({ version: 8, source: { paroi: 0.3, paroi_max: 0.125, pieces: [{}], avertissement: "A", limite: "L" } });
direBilanCreusage({ version: 9, source: {} }); direBilanCreusage(null);
R.avis = AVIS.slice();
""")
    assert R["avis"] == [
        "creusé (version 7) : paroi 3,00 mm sur 1 pièce(s) — paroi qui tient : 1,25 mm — 12 triangle(s) effondré(s) — limite : L",
        "creusé (version 8) : paroi 0,300 u. glTF sur 1 pièce(s) — paroi qui tient : 0,125 u. glTF — A — limite : L"]


def test_creuser_passe_par_l_entonnoir_SEUL_et_se_libelle_dans_l_unite_courante():
    src = (_objet_etabli("ORDRE_ECRITURE") + _objet_etabli("ROUTES") + _objet_etabli("LIBELLES_ATTENTE") + ENTONNOIR
           + "let REP = { echelle: 4 };\n" + _fonction_etabli("enMillimetres") + _fonction_etabli("uniteCourante")
           + _fonction_etabli("fmtMesure") + _fonction_etabli("fileOrdonnee") + _fonction_etabli("contradictionDeLaFile") + _fonction_etabli_async("ecrireVersion")
           + """
(async () => { const R = {};
S.enAttente.push({ operation: "creuser", charge: { paroi: 0.5, paroi_millimetres: 2, noeuds: null } });
R.lib = LIBELLES_ATTENTE.creuser(S.enAttente[0]);
await ecrireVersion(); R.corps = CORPS.slice();
console.log(JSON.stringify(R)); })();""")
    R = json.loads(_node(src).strip().splitlines()[-1])
    assert R["corps"] == [["/api/etabli/creuser", {"job": "j", "version": 1, "paroi": 0.5, "paroi_millimetres": 2,
                                                   "noeuds": None}]]
    assert R["lib"] == "creuser : paroi 2,00 mm"
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert 'creuser: "/api/etabli/creuser",' in js and 'creuser: "creuser"' in _objet_etabli("LIBELLE_OP")
    fiche = _fonction_etabli("rendreFiche")
    assert '<button id="fCreuser" title="' in fiche and 'id="fParoi"' in fiche and "paroi (millimètres)" in fiche
    h = _gestionnaire_creuser()
    assert h.index("versUnites(saisie)") < h.index('ecrireSeule("creuser"'), "la garde AVANT l'écriture"
    assert "REP.echelle" not in h, "la conversion passe par versUnites, jamais par un cinquième site"


# ── T090 / plan T11 : la lecture chiffrée de la pièce que l'on glisse ──────────
def test_la_lecture_du_glisser_est_relative_au_COIN_du_plateau_EXECUTEE():
    """La cote qu'un préparateur lit sur un plateau part du COIN du plateau, pas de l'origine du monde : c'est le
    zéro des règles (voir geometriePlateau). Une lecture en coordonnées monde afficherait −3 pour une pièce posée
    à 2 du bord — deux nombres pour un seul geste."""
    src = """
      const REP = { echelle: 10, cibleMm: 100, pas: null };
      const uniteCourante = () => "mm";
      const fmtMesure = (v) => (v * REP.echelle).toFixed(2);
      const PLQ = { active: true, courante: 7, pieces: [{ cle: 7, nom: "cadre" }] };
      const S = { vueA: {} };
      let SENS = { u: 1, v: 1 };
      const plateauDe = () => ({ u: "x", v: "z", axe: "y", coin: { x: -5, z: SENS.v > 0 ? -5 : 5 }, sens: SENS });
      const empreinteDe = () => ({ u: -3, v: -1, l: 2, p: 4 });
      const rotationDe = () => 90;
      const box = { textContent: "x" };
      const document = { querySelector: (q) => (q === "#plaqueLecture" ? box : null) };
    """ + _fonction_etabli("nomDePiece") + _fonction_etabli("lirePieceCourante") + """
      const r = [];
      lirePieceCourante(); r.push(box.textContent);
      PLQ.courante = null; lirePieceCourante(); r.push(box.textContent);
      PLQ.courante = 9; lirePieceCourante(); r.push(box.textContent);
      PLQ.active = false; PLQ.courante = 7; lirePieceCourante(); r.push(box.textContent);
      // l'axe v des règles DÉCROÎT depuis le coin (z = +5) : la lecture est sens·(p − coin), et le point de la
      // pièce le plus proche du zéro des règles est son bord HAUT (v + p = 3) → 5 − 3 = 2 u → 20,00 mm
      PLQ.active = true; SENS = { u: 1, v: -1 }; lirePieceCourante(); r.push(box.textContent);
      console.log(JSON.stringify(r));
    """
    r = json.loads(_node(src))
    # coin relatif : (−3 − (−5)) = 2 u → 20,00 mm ; (−1 − (−5)) = 4 u → 40,00 mm
    assert "cadre" in r[0] and "20.00 ; 40.00" in r[0], r[0]
    assert "20.00 × 40.00 mm" in r[0] and "90°" in r[0], r[0]
    assert r[1] == "", "aucune pièce courante : la ligne se VIDE (elle ne garde pas la pièce d'avant)"
    assert r[2].startswith("pièce 9"), "une clé sans nom se dit par sa clé"
    assert r[3] == "", "hors plaque, la ligne se vide"
    assert "coin 20.00 ; 20.00" in r[4], ("le SENS des règles compte (preuve 8799 : −0,630 lu sur un axe "
                                          "décroissant)", r[4])


def test_la_lecture_du_glisser_ne_redessine_PAS_le_rail_a_chaque_image():
    """lireRepere() coûte 2,057 ms à douze sélections HORS navigateur — 12 % d'une trame à 60 Hz. Un `pointermove`
    ne peut donc pas l'appeler ; il écrit un textContent sur UNE pièce."""
    f = _fonction_etabli("lirePieceCourante")
    assert "textContent" in f and "innerHTML" not in f
    assert "lireRepere" not in f and "rendreParties" not in f
    glisse = _fonction_etabli("glisserSurPlaque")
    assert "lirePieceCourante()" in glisse and "lireRepere()" not in glisse
    assert glisse.index("rendreRotation();") < glisse.index("lirePieceCourante()")
    # les autres sites : le clavier, le panneau (qui recrée la ligne), les règles, le repère (l'unité change)
    assert "lirePieceCourante()" in _fonction_etabli("toucheClavierPlaque")
    # TOUT geste qui pose une pièce relit la ligne — le plan ne listait ni le rangement ni la saisie en degrés,
    # et la preuve 8799 a montré une cote figée après « Ranger sur le plateau »
    for f in (_fonction_etabli_async("arrangerPlaque"), _fonction_etabli("poserRotation")):
        assert f.index("rendreRotation();") < f.index("lirePieceCourante();")
    parties = _fonction_etabli("rendreParties")
    # le panneau RECRÉE la ligne vide, puis la refait par lireRepere() — sa dernière instruction
    assert 'id="plaqueLecture"' in parties and parties.rstrip()[:-1].rstrip().endswith("lireRepere();")
    assert "lirePieceCourante()" in _fonction_etabli("graduerPlateau")
    assert "lirePieceCourante()" in _fonction_etabli("lireRepere")
    css = _lire("etabli/etabli.css")
    assert ".plaque-lecture" in css and "tabular-nums" in css and "min-height: 13px" in css


# ── T090 / plan T13 : la contradiction assise / recentrer, DITE et refusée ─────
def test_assise_et_recentrer_dans_la_MEME_file_sont_refuses_en_le_disant():
    src = """
      const S = { enAttente: [] };
    """ + _fonction_etabli("contradictionDeLaFile") + """
      const cas = [];
      const poser = (l) => { S.enAttente = l; return contradictionDeLaFile(); };
      cas.push(poser([{ operation: "assise", charge: {} }]));
      cas.push(poser([{ operation: "reparer", charge: { recentrer: false } }]));
      cas.push(poser([{ operation: "assise", charge: {} },
                      { operation: "reparer", charge: { recentrer: false } }]));
      cas.push(poser([{ operation: "assise", charge: {} },
                      { operation: "reparer", charge: { recentrer: true } }]));
      cas.push(poser([{ operation: "reparer", charge: { recentrer: true } }]));
      console.log(JSON.stringify(cas));
    """
    r = json.loads(_node(src))
    assert r[0] is None and r[1] is None and r[2] is None and r[4] is None
    assert isinstance(r[3], str)
    assert "recentr" in r[3] and "face" in r[3]
    assert r[3].startswith("« recentrer » défait"), "le geste d'abord : la barre coupe la fin de la phrase"


def test_la_barre_dit_la_contradiction_et_le_bouton_d_ecriture_se_grise():
    barre = _fonction_etabli("rendreAttente")
    assert "contradictionDeLaFile()" in barre
    assert 'class="attente-refus"' in barre
    # le bouton est grisé par la MÊME expression que le verrou d'écriture ; « annuler » ne l'est PAS
    assert '<button id="btnEcrire"${_ecritEnCours || contra ? " disabled" : ""}>' in barre
    assert '<button id="btnAnnuler"${_ecritEnCours ? " disabled" : ""}>' in barre
    # le texte entre en textContent, jamais dans le gabarit
    assert "r.textContent = contra;" in barre and "r.title = contra;" in barre
    ecrit = _fonction_etabli_async("ecrireVersion")
    assert ecrit.index("contradictionDeLaFile()") < ecrit.index("_ecritEnCours = true")
    assert ".attente-refus" in _lire("etabli/etabli.css")


def test_ecrireVersion_REFUSE_une_file_contradictoire_sans_prendre_le_verrou_EXECUTEE():
    corps = _fonction_etabli_async("ecrireVersion")
    debut = corps[:corps.index("_ecritEnCours = true")] + "_ecritEnCours = true; return 'ECRIT'; }\n"
    src = """
      let _ecritEnCours = false;
      const REFUS = [];
      const direRefus = (m) => REFUS.push(m);
      const S = { a: { job: "j" }, enAttente: [{ operation: "assise", charge: {} },
                                              { operation: "reparer", charge: { recentrer: true } }] };
    """ + _fonction_etabli("contradictionDeLaFile") + debut + """
      (async () => {
        const a = await ecrireVersion();
        const verrou = _ecritEnCours;
        S.enAttente[1].charge.recentrer = false;
        const b = await ecrireVersion();
        console.log(JSON.stringify({ a, verrou, b, refus: REFUS }));
      })();
    """
    r = json.loads(_node(src))
    assert r["a"] is None and r["verrou"] is False and len(r["refus"]) == 1 and "recentr" in r["refus"][0]
    assert r["b"] == "ECRIT"


# ── T091 / plan T16 : l'aperçu de tranchage INDICATIF ──────────────────────────
def _fonction_surplomb(nom: str) -> str:
    js = _lire("lib3d/surplomb.js")
    m = re.search(r"^export function " + nom + r"\(", js, re.M)
    assert m, f"fonction {nom} introuvable dans surplomb.js"
    return js[m.start():js.index("\n}\n", m.start()) + 2].replace("export function", "function", 1) + "\n"


def test_la_pente_du_surplomb_suit_la_convention_des_slicers_EXECUTEE():
    """Convention de Prusa : la pente se mesure DEPUIS L'HORIZONTALE, 90 = mur vertical (rien à faire), 0 = plafond
    plat (le pire). Une face qui regarde vers le HAUT n'est jamais un surplomb, quelle que soit sa pente."""
    src = _fonction_surplomb("penteDepuisHorizontale") + _fonction_surplomb("estSurplomb") + """
const H = { x: 0, y: 1, z: 0 };
const bas = { x: 0, y: -1, z: 0 };
const mur = { x: 1, y: 0, z: 0 };
const biais = { x: 0.7071067811865476, y: -0.7071067811865475, z: 0 };
const haut = { x: 0, y: 1, z: 0 };
const pente30 = { x: 0.5, y: -0.8660254037844386, z: 0 };   // 30° depuis l'horizontale
console.log(JSON.stringify({
  p_bas: penteDepuisHorizontale(bas, H), p_mur: penteDepuisHorizontale(mur, H),
  p_biais: penteDepuisHorizontale(biais, H), p_haut: penteDepuisHorizontale(haut, H),
  p_30: penteDepuisHorizontale(pente30, H),
  p_long: penteDepuisHorizontale({ x: 0, y: -7, z: 0 }, { x: 0, y: 3, z: 0 }),
  p_30_long: penteDepuisHorizontale({ x: 1, y: -1.7320508075688772, z: 0 }, { x: 0, y: 2, z: 0 }),
  s_bas: estSurplomb(bas, H, 45), s_mur: estSurplomb(mur, H, 45),
  s_biais45: estSurplomb(biais, H, 45), s_biais50: estSurplomb(biais, H, 50),
  s_haut: estSurplomb(haut, H, 45), s_nul: estSurplomb({ x: 0, y: 0, z: 0 }, H, 45),
  s_axeZ: estSurplomb({ x: 0, y: 0, z: -1 }, { x: 0, y: 0, z: 1 }, 45),
}));
"""
    r = json.loads(_node(src))
    assert r["p_bas"] == 0 and r["p_mur"] == 90 and r["p_long"] == 0, r
    assert abs(r["p_biais"] - 45) < 1e-6 and abs(r["p_30"] - 30) < 1e-6
    assert abs(r["p_30_long"] - 30) < 1e-6, "ni la normale ni l'axe haut ne sont supposés unitaires"
    assert r["p_haut"] is None                    # une face vers le ciel n'a pas de pente
    assert r["s_bas"] is True and r["s_mur"] is False
    assert r["s_biais45"] is False                # 45 n'est pas SOUS le seuil 45
    assert r["s_biais50"] is True
    assert r["s_haut"] is False and r["s_nul"] is False
    assert r["s_axeZ"] is True, "l'axe haut est un ARGUMENT : sur la plaque il peut être z"


def test_les_surplombs_suivent_l_axe_de_la_plaque_et_s_eteignent_au_chargement():
    js = _lire("etabli/etabli.js")
    assert 'import { peindreSurplombs } from "/lib3d/surplomb.js";' in js
    assert "const SEUIL_SURPLOMB = 45;" in js
    assert "const SURPLOMB = { actif: false };" in js
    axe = _fonction_etabli("axeHautImpression")
    assert "plateauDe(S.vueA)" in axe and "g.axe ===" in axe
    b = _fonction_etabli("basculerSurplombs")
    assert "axeHautImpression()" in b and "SEUIL_SURPLOMB" in b
    assert "apercusSurLaPlaque();" in _fonction_etabli("graduerPlateau")
    ap = _fonction_etabli("apercusSurLaPlaque")
    assert "peindreSurplombs(S.vueA, SEUIL_SURPLOMB, axeHautImpression())" in ap
    assert "TRANCHES.actives && PLQ.active" in ap and "dessinerTranches(S.vueA, null)" in ap
    o = _fonction_etabli_async("_ouvrirPrincipale")
    assert "eteindreApercus()" in o
    e = _fonction_etabli("eteindreApercus")
    assert "peindreSurplombs(S.vueA, 0" in e and "dessinerTranches(S.vueA, null)" in e
    assert "SURPLOMB.actif = false" in e and "TRANCHES.actives = false" in e
    assert '<button class="outil-btn" id="btnSurplombs"></button>' in _lire("etabli/index.html")
    # le calque ne touche AUCUN matériau du modèle (leçon des teintes partagées)
    s = _code("lib3d/surplomb.js")
    assert ".material.color" not in s and "o.material =" not in s


def test_l_axe_haut_de_l_impression_est_celui_du_PLATEAU_sur_la_plaque_EXECUTEE():
    src = """
      const S = { vueA: {} };
      const PLQ = { active: false };
      let AXE = "z";
      const plateauDe = () => ({ axe: AXE });
    """ + _fonction_etabli("axeHautImpression") + """
      const r = [axeHautImpression()];
      PLQ.active = true; r.push(axeHautImpression());
      AXE = "x"; r.push(axeHautImpression());
      console.log(JSON.stringify(r));
    """
    r = json.loads(_node(src))
    assert r == [{"x": 0, "y": 1, "z": 0}, {"x": 0, "y": 0, "z": 1}, {"x": 1, "y": 0, "z": 0}]


def test_l_apercu_de_tranchage_ne_promet_QUE_l_indicatif_et_n_ecrit_rien():
    js = _lire("etabli/etabli.js")
    assert "dessinerTranches" in js.split('from "/lib3d/viewer.js"', 1)[0]
    assert "const TRANCHES = { actives: false };" in js and "const NB_TRANCHES = 20;" in js
    f = _fonction_etabli_async("basculerTranches")
    assert '"/api/etabli/tranches"' in f and "ecrireSeule" not in f and "ecrireVersion" not in f
    assert "Aperçu seulement" in f and "le slicer tranche pour de vrai" in f
    assert "fmtMesure(" in f and "uniteCourante()" in f and "axeHautImpression()" in f
    assert '<button class="outil-btn" id="btnTranches"></button>' in _lire("etabli/index.html")
    # aucune des deux routes de REGARD n'entre dans la table des écritures
    routes = _objet_etabli("ROUTES")
    assert "tranches" not in routes and "ranger" not in routes
    v = _lire("lib3d/viewer.js")
    assert "export function dessinerTranches(api, couches)" in v


def test_les_libelles_des_deux_apercus_disent_leur_ETAT():
    m = _fonction_etabli("majOutils")
    assert 'SURPLOMB.actif ? "Surplombs ✓" : "Surplombs"' in m
    assert 'TRANCHES.actives ? "Tranches ✓" : "Tranches"' in m


# ── T091 : « → Impression 3D » dans l'Établi, sur la version AFFICHÉE ──────────
def test_l_etabli_imprime_la_version_AFFICHEE_sous_une_taille_cible_EXECUTEE():
    corps = _fonction_etabli_async("imprimerVersion")
    src = """
      const REFUS = [], AVIS = [], POSTS = [];
      const direRefus = (m) => REFUS.push(m);
      const direAvis = (m) => AVIS.push(m);
      let REPONSE = { dossier: "cube-20261005", triangles: 24, avertissement: null };
      const jpost = async (u, b) => { POSTS.push([u, b]); return REPONSE; };
      const REP = { cibleMm: null };
      const enMillimetres = () => REP.cibleMm !== null;
      const S = { a: null, enAttente: [] };
      let IMPRESSION = null;
    """ + corps + """
      (async () => {
        const r = [];
        await imprimerVersion(); r.push(REFUS.length);                                  // rien de chargé
        S.a = { job: null, meshy: "t1", version: null };
        await imprimerVersion(); r.push(REFUS.length);                                  // une tâche Meshy non adoptée
        S.a = { job: "job_x", version: 3 };
        await imprimerVersion(); r.push(REFUS.length);                                  // pas de taille cible
        REP.cibleMm = 80; S.enAttente = [{ operation: "assise" }];
        await imprimerVersion(); r.push(REFUS.length);                                  // file non écrite
        S.enAttente = [];
        await imprimerVersion();
        console.log(JSON.stringify({ r, refus: REFUS, posts: POSTS, avis: AVIS, imp: IMPRESSION }));
      })();
    """
    o = json.loads(_node(src))
    assert o["r"] == [1, 2, 3, 4]
    assert "taille cible" in o["refus"][2] and "attente" in o["refus"][3]
    assert o["posts"] == [["/api/print3d/from-assets3d/job_x", {"version": 3, "cible_millimetres": 80, "nom": "job_x-v3"}]]
    assert "version 3" in o["avis"][0] and "24 triangles" in o["avis"][0]
    assert o["imp"] == "cube-20261005", "le DOSSIER retenu pour « Ouvrir dans le slicer »"


def test_le_bouton_d_impression_et_l_ouverture_dans_le_slicer_sont_branches():
    html = _lire("etabli/index.html")
    assert '<button id="btnImprimer"' in html and '<button id="btnSlicer"' in html
    js = _lire("etabli/etabli.js")
    assert '$("#btnImprimer").addEventListener("click", imprimerVersion);' in js
    assert '$("#btnSlicer").addEventListener("click", ouvrirDansSlicer);' in js
    o = _fonction_etabli_async("ouvrirDansSlicer")
    assert '"/api/print3d/open"' in o and "{ dossier: IMPRESSION }" in o
    # l'export n'écrit AUCUNE version : il n'entre pas dans la table des écritures
    assert "print3d" not in _objet_etabli("ROUTES")


# ── T091 / plan T14 : le chapitre 21 du guide, FR et EN ────────────────────────
GUIDE = RACINE / "docs" / "guide"
TERMES_LEXIQUE = ["assise", "surplomb", "support", "brim", "raft", "jupe", "remplissage", "couture", "retraction",
                  "couche", "perimetre", "pont", "warping", "etancheite", "manifold", "decimation", "creusage",
                  "drainage"]


def test_le_chapitre_21_existe_dans_les_DEUX_langues_avec_son_entree_de_sommaire():
    for nom, titre in (("fr.html", "Préparer avant le slicer"), ("en.html", "Prepare before slicing")):
        h = (GUIDE / nom).read_text("utf-8")
        assert '<h2 id="c21">' in h and titre in h
        assert '<a href="#c21">' in h
        # le chapitre 21 vient APRÈS le 20 dans le sommaire ET dans le corps, et AVANT le pied de page
        assert h.index('<a href="#c20"') < h.index('<a href="#c21"')
        assert h.index('<h2 id="c20"') < h.index('<h2 id="c21"') < h.index('<div class="footer">')


def test_le_lexique_a_ses_DIX_HUIT_termes_ancres_dans_les_deux_langues():
    for nom in ("fr.html", "en.html"):
        h = (GUIDE / nom).read_text("utf-8")
        for t in TERMES_LEXIQUE:
            assert h.count(f'id="lex-{t}"') == 1, (nom, t)
        assert h.count('id="lex-') == 18


def test_chaque_ressource_du_guide_est_DATEE_et_pointe_un_domaine_verifie():
    domaines = {"help.prusa3d.com", "github.com", "www.simplify3d.com", "wiki.elegoo.com"}
    jeux = []
    for nom in ("fr.html", "en.html"):
        h = (GUIDE / nom).read_text("utf-8")
        bloc = h.split('<h2 id="c21"', 1)[1].split('<div class="footer">', 1)[0]
        liens = re.findall(r'<a href="(https?://[^"]+)"[^>]*>', bloc)
        assert len(liens) >= 12, (nom, len(liens))
        for u in liens:
            assert u.split("/")[2] in domaines, u
        # une date de vérification par ligne de ressource
        rows = re.findall(r"<tr>.*?</tr>", bloc, re.S)
        for r in [r for r in rows if '<a href="http' in r]:
            assert "05/10/2026" in r, r[:120]
        jeux.append(liens)
    assert jeux[0] == jeux[1], "MÊME table de ressources dans les deux langues"
    # l'adresse morte relevée le 05/10 (redirection 302) ne revient pas
    assert all("help.prusa3d.com/materials" not in u for u in jeux[0])


def test_le_guide_ne_cite_QUE_des_libelles_qui_existent_dans_l_ecran():
    """Le guide dit « cliquez X » : X doit exister. Un libellé renommé dans l'écran et resté dans le guide
    enverrait le débutant chercher un bouton fantôme — et c'est en écrivant ce chapitre qu'on a découvert que
    l'export n'imprimait pas la version affichée."""
    ecran = (_lire("etabli/etabli.js") + _lire("etabli/index.html") + _lire("studio3d/index.html"))
    for libelle in ("Réparer en un clic", "Poser sur une face", "Surplombs", "Tranches", "Creuser", "Décimer",
                    "Ranger sur le plateau", "Mesurer", "→ Impression 3D", "Ouvrir dans le slicer",
                    "07 · Établi 3D →", "écrire la version", "taille cible", "Sur la plaque", "Orienter"):
        # comme TEXTE d'un contrôle — balisage `>libellé<` ou chaîne exacte écrite par le JS —, pas n'importe où :
        # « → Impression 3D » vit aussi dans un message de refus, qui survivait au renommage du bouton
        assert re.search(r">\s*" + re.escape(libelle) + r"\s*<", ecran) or f'"{libelle}"' in ecran, libelle
        for nom in ("fr.html", "en.html"):
            h = (GUIDE / nom).read_text("utf-8").split('<h2 id="c21"', 1)[1]
            assert libelle in h or libelle in ("Sur la plaque",) or nom == "en.html" and libelle in (
                "taille cible", "écrire la version"), (nom, libelle)


def test_le_guide_ne_promet_pas_ce_que_l_etabli_ne_fait_pas_encore():
    # T092 : l'orientation automatique EXISTE — le guide la décrit, avec l'avertissement du wiki OrcaSlicer
    for nom, phrase in (("fr.html", "ne trouve pas toujours la meilleure pose"),
                        ("en.html", "does not always find the best pose")):
        h = (GUIDE / nom).read_text("utf-8")
        assert phrase in h and "<em>Orienter</em>" in h, nom
        assert "pas encore d'orientation" not in h and "no auto-orientation" not in h, nom
    fr = (GUIDE / "fr.html").read_text("utf-8")
    assert "Le trou de drainage n'est pas encore dans l'Établi" in fr


def test_les_PDF_sont_plus_recents_que_leur_source_HTML():
    """Le PDF est REGÉNÉRÉ, pas oublié : c'est lui que l'utilisateur imprime.

    PAR LES DATES DE COMMIT, et c'est la correction du 06/10 : dans un worktree neuf, git écrit les fichiers dans un
    ordre quelconque et leurs dates de modification ne disent plus rien (le banc rougissait sur une extraction
    propre). Un HTML MODIFIÉ et non commité, lui, se juge à la date du fichier : c'est le cas d'un guide qu'on édite."""
    def git(*a):
        return subprocess.run(["git", *a], capture_output=True, text=True, cwd=str(RACINE)).stdout.strip()
    for html, pdf in (("fr.html", "Deepotus-Guide-FR.pdf"), ("en.html", "Deepotus-Guide-EN.pdf")):
        h, f = f"docs/guide/{html}", f"docs/guide/{pdf}"
        if git("status", "--porcelain", "--", h):
            assert (GUIDE / pdf).stat().st_mtime >= (GUIDE / html).stat().st_mtime, (html, "modifié sans PDF")
        else:
            th, tf = git("log", "-1", "--format=%ct", "--", h), git("log", "-1", "--format=%ct", "--", f)
            assert th and tf and int(tf) >= int(th), (html, pdf, th, tf)


# ── T091 / plan T15 : l'aide contextuelle, alignée sur le guide ─────────────────
def test_l_aide_de_l_etabli_ne_definit_QUE_des_termes_qui_existent_dans_LE_GUIDE():
    """DEUX NIVEAUX, UNE SEULE VÉRITÉ : l'écran donne une phrase, le guide donne le chapitre. Un terme défini à
    l'écran et absent du guide enverrait sur une ancre morte."""
    aide = _lire("etabli/aide.js")
    cles = re.findall(r"^\s{2}([a-z]+): \{", aide, re.M)
    assert sorted(cles) == sorted(TERMES_LEXIQUE)
    for lang in ("fr.html", "en.html"):
        h = (GUIDE / lang).read_text("utf-8")
        for c in cles:
            assert f'id="lex-{c}"' in h, (lang, c)


def test_l_aide_pointe_le_guide_dans_la_langue_de_la_page_et_par_ancre_EXECUTEE():
    aide = _lire("etabli/aide.js")
    m = re.search(r"^export function lienGuide\(", aide, re.M)
    corps = aide[m.start():aide.index("\n}\n", m.start()) + 2].replace("export function", "function", 1)
    r = json.loads(_node("const document = { documentElement: { lang: 'fr' } };\n" + corps + """
      const a = [lienGuide("surplomb"), lienGuide(null)];
      document.documentElement.lang = "en-GB"; a.push(lienGuide("brim"));
      console.log(JSON.stringify(a));
    """))
    assert r == ["/guide/fr.html#lex-surplomb", "/guide/fr.html#c21", "/guide/en.html#lex-brim"]


def test_l_aide_est_branchee_dans_l_en_tete_sans_casser_l_invariant():
    js, html = _lire("etabli/etabli.js"), _lire("etabli/index.html")
    assert 'import { ouvrirAide } from "./aide.js";' in js
    assert '$("#btnAide").addEventListener("click", basculerAide);' in js
    assert '<button class="head-btn" id="btnAide"' in html and 'id="panAide"' in html
    entete = re.sub(r"<!--.*?-->", "", html.split("<header", 1)[1].split("</header>", 1)[0], flags=re.S)
    assert entete.count("<button") == entete.count('class="head-btn"') == 4
    # le pas à pas de l'aide est celui du guide : mêmes gestes, même ordre
    aide = _lire("etabli/aide.js")
    pas = re.findall(r"<li>(.*?)</li>", aide.split('<ol class="aide-pas">', 1)[1].split("</ol>", 1)[0], re.S)
    assert len(pas) == 8
    for mot, k in (("taille cible", 0), ("imprimante", 1), ("Répare", 2), ("Pose", 3), ("Surplombs", 4),
                   ("Creuse", 5), ("Range", 6), ("Impression 3D", 7)):
        assert mot in pas[k], (k, mot, pas[k])
    # le texte des définitions est échappé à l'écriture : jamais de balisage venu du lexique
    assert "esc(" in aide


# ── T092 / plan T19 : l'auto-orient PROPOSE, et c'est l'assise qui écrit ──────
def test_l_auto_orient_PROPOSE_et_c_est_l_assise_qui_ecrit():
    f = _fonction_etabli_async("proposerOrientation")
    assert "/api/etabli/orienter?job=" in f
    assert 'ecrireSeule("assise", { normale: c.rotation, point: null })' in f
    assert 'ecrireSeule("orienter"' not in f
    # l'avertissement vient du serveur : textContent, et il est RÉPÉTÉ dans la barre
    assert 'zone.querySelector(".note").textContent = d.avertissement;' in f
    assert f.count("d.avertissement") >= 2
    assert "innerHTML" not in f.split("zone.innerHTML", 1)[1].split(";", 1)[1] if "zone.innerHTML" in f else True
    assert '<button class="outil-btn" id="btnOrienter"></button>' in _lire("etabli/index.html")
    assert "orienter" not in _objet_etabli("ROUTES")
    m = _fonction_etabli("majOutils")
    assert '$("#btnOrienter")' in m
    assert '$("#btnOrienter").addEventListener("click", proposerOrientation);' in _lire("etabli/etabli.js")


def test_les_poses_proposees_se_disent_dans_l_UNITE_courante_EXECUTEE():
    corps = _fonction_etabli_async("proposerOrientation")
    src = """
      const REFUS = [], AVIS = [], ECRITS = [];
      const direRefus = (m) => REFUS.push(m), direAvis = (m) => AVIS.push(m);
      const fmtMesure = (v) => (v * 10).toFixed(2), uniteCourante = () => "mm";
      const esc = (v) => String(v);
      const S = { a: { job: "j", version: 2 }, enAttente: [] };
      const D = { seuil_surplomb: 45, avertissement: "ne trouve pas toujours la meilleure pose",
                  candidats: [{ part_contact: 0.1666, part_surplomb: 0, hauteur: 0.05, score: -0.5, rotation: [0, -1, 0] },
                              { part_contact: 0.02, part_surplomb: 0.013, hauteur: 0.4, score: 0.1, rotation: [1, 0, 0] }] };
      const jget = async (u) => { ECRITS.push(u); return D; };
      const ecrireSeule = async (op, charge) => { ECRITS.push([op, charge]); return { derniere: { version: 3 } }; };
      class El { constructor() { this.enfants = []; this.ecoute = {}; this.className = ""; this._html = "";
                 this.dataset = {}; this.boutons = []; this.noteEl = { textContent: "" }; }
        set innerHTML(h) { this._html = h; this.boutons = [...h.matchAll(/data-orient="(\d+)"/g)].map((m) => {
          const b = { dataset: { orient: m[1] }, ecoute: {}, addEventListener(t, f) { this.ecoute[t] = f; } }; return b; }); }
        get innerHTML() { return this._html; }
        querySelector(q) { return q === ".note" ? this.noteEl : (q === ".orient" ? null : null); }
        querySelectorAll() { return this.boutons; }
        appendChild(e) { this.enfants.push(e); } remove() {} }
      const panneau = new El();
      const ONGLETS_VUS = []; const montrerOnglet = (k) => ONGLETS_VUS.push(k);
    """ + re.search(r"^const pourCent = .*$", _lire("etabli/etabli.js"), re.M).group(0) + """
      const $ = (q) => (q === "#panFiche" ? panneau : null);
      const document = { createElement: () => new El() };
    """ + corps + """
      (async () => {
        await proposerOrientation();
        const zone = panneau.enfants[0];
        await zone.boutons[0].ecoute.click();
        S.a = { job: null, version: null }; await proposerOrientation();
        console.log(JSON.stringify({ html: zone.innerHTML, note: zone.noteEl.textContent, ecrits: ECRITS,
                                     avis: AVIS, refus: REFUS }));
      })();
    """
    o = json.loads(_node(src))
    assert o["ecrits"][0] == "/api/etabli/orienter?job=j&version=2"
    assert o["ecrits"][1] == ["assise", {"normale": [0, -1, 0], "point": None}]
    assert "appui 17 %" in o["html"] and "surplomb 0 %" in o["html"] and "hauteur 0.50 mm" in o["html"], o["html"]
    assert "surplomb 1 %" in o["html"], "arrondi au pour-cent"
    assert o["note"] == "ne trouve pas toujours la meilleure pose"
    assert any("version 3" in a for a in o["avis"]) and len(o["refus"]) == 1

if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
