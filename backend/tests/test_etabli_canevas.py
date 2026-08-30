"""L'Établi P2+P3 — canevas, chronologie et Parties
(plan 2026-08-29-etabli-p2-p3-canevas-parties).

Bancs MIROIRS : ils lisent les fichiers frontend comme du texte et y épinglent
des marqueurs. Patron de test_library_picker.py — c'est ainsi que le dépôt
garde un frontend vanilla sans navigateur au banc.

Run: .\\scripts\\run-tests.ps1 -Filter test_etabli_canevas.py
"""
import json
import os
import pathlib
import re
import sys
import tempfile

# Configuration AVANT tout import de app.main : `settings` est figé au
# premier import, et la section B en déclenche un. Au niveau module, donc,
# comme dans test_etabli_socle.py — dans _client() ces lignes arriveraient
# toujours trop tard en suite complète.
_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
os.environ["VECTOR_FOLDER"] = str(pathlib.Path(_tmp, "vector"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
FRONT = RACINE / "frontend"


def _lire(rel: str) -> str:
    # Réservé aux sections suivantes (chronologie, Parties) : la section A
    # ne fait que vérifier des chemins de fichiers, pas leur contenu texte.
    return (FRONT / rel).read_text(encoding="utf-8")


# ── A. three.js vendorisé ────────────────────────────────────────────────────

def test_three_est_vendorise_et_non_pointe_vers_un_cdn():
    trois = FRONT / "dist" / "assets" / "three"
    assert (trois / "three.module.min.js").is_file()
    # three.module.min.js importe "./three.core.min.js" (build recent scinde
    # en deux) : sans ce frere, l'import 404 et l'ecran reste noir sans
    # qu'aucune erreur ne remonte ici — voir VERSION.txt, piege 1.
    assert (trois / "three.core.min.js").is_file()
    assert (trois / "addons" / "loaders" / "GLTFLoader.js").is_file()
    assert (trois / "addons" / "controls" / "OrbitControls.js").is_file()
    assert (trois / "addons" / "controls" / "TransformControls.js").is_file()
    # un moteur de rendu tronqué serait pire qu'absent
    assert (trois / "three.module.min.js").stat().st_size > 100_000


def test_les_decodeurs_de_compression_sont_la():
    """Sans eux, un GLB Draco ou meshopt s'affiche NOIR au lieu de s'afficher."""
    addons = FRONT / "dist" / "assets" / "three" / "addons"
    assert (addons / "libs" / "meshopt_decoder.module.js").is_file()
    assert (addons / "loaders" / "DRACOLoader.js").is_file()
    assert (addons / "libs" / "draco").is_dir()


def test_les_freres_reclames_par_gltfloader_sont_la():
    """GLTFLoader.js importe '../utils/BufferGeometryUtils.js' et
    '../utils/SkeletonUtils.js' — ces deux fichiers ne figurent pas dans la
    liste litterale de la tache 1, mais un import reel les reclame. Sans
    eux, le chargement du premier GLB echoue en 404, en silence : ce banc
    ne verifierait rien d'anormal si on les supprimait sans cette assertion.
    """
    utils = FRONT / "dist" / "assets" / "three" / "addons" / "utils"
    assert (utils / "BufferGeometryUtils.js").is_file()
    assert (utils / "SkeletonUtils.js").is_file()


def test_l_importmap_resout_les_specifiers_nus():
    trois = FRONT / "dist" / "assets" / "three"
    carte = json.loads((trois / "importmap.json").read_text("utf-8"))
    assert carte["imports"]["three"] == "/assets/three/three.module.min.js"
    assert carte["imports"]["three/addons/"] == "/assets/three/addons/"


def test_la_version_et_le_poids_sont_consignes():
    """La spec promettait de MESURER le poids plutot que de l'estimer."""
    txt = (FRONT / "dist" / "assets" / "three" / "VERSION.txt").read_text("utf-8")
    assert "octets" in txt
    assert "model-viewer" in txt


# ── B. montages ──────────────────────────────────────────────────────────────

def _client():
    """Ne fait QUE construire le client : la configuration est posée au
    niveau module (voir en tête), seule position où elle serve à quelque
    chose — app.config.settings est figé au PREMIER import de app.main, et
    une vingtaine de modules de tests/ l'importent dès la collecte.
    """
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def test_la_page_etabli_est_servie():
    r = _client().get("/etabli/")
    assert r.status_code == 200
    assert "etabli.js" in r.text


def test_lib3d_est_servi_et_partageable():
    """viewer.js vit hors de la page : c'est la précondition écrite d'avance
    de la convergence du Plateau (spec §12)."""
    r = _client().get("/lib3d/viewer.js")
    assert r.status_code == 200
    assert "creerCanevas" in r.text


def test_l_importmap_de_la_page_est_en_ligne_et_conforme_au_fichier():
    """Les import maps EXTERNES (<script type=importmap src=...>) ne sont
    supportées par aucun navigateur : mesure faite dans un vrai navigateur, la
    page reste inerte avec « Failed to resolve module specifier "three" ». La
    page porte donc sa carte EN LIGNE, et AVANT le premier module — posée
    après lui, elle arriverait trop tard pour lui. Ce banc interdit en
    outre qu'elle dérive de importmap.json, la référence du dossier
    vendorisé.
    """
    # les commentaires sont retirés d'abord : celui de la page CITE la
    # forme fautive `<script type="importmap" src="…">`, et sans ce
    # nettoyage le banc épinglerait sa propre explication.
    html = re.sub(r"<!--.*?-->", "", _lire("etabli/index.html"), flags=re.S)
    assert 'type="importmap"' in html
    apres = html.split('type="importmap"', 1)[1]
    # ce qui reste de la balise ouvrante ne doit porter aucun src=
    assert "src=" not in apres.split(">", 1)[0]
    en_ligne = json.loads(apres.split(">", 1)[1].split("</script>", 1)[0])
    fichier = json.loads(
        (FRONT / "dist" / "assets" / "three" / "importmap.json")
        .read_text(encoding="utf-8"))
    assert en_ligne == fichier
    # et elle doit PRÉCÉDER le premier <script type="module"> : posée après,
    # elle arrive trop tard, le module ayant déjà tenté sa résolution.
    assert html.index('type="importmap"') < html.index('type="module"')


# ── C. chargement et cadrage ─────────────────────────────────────────────────

def test_le_viewer_branche_les_deux_decodeurs():
    """IMPORTER un décodeur ne le BRANCHE pas : sans setMeshoptDecoder(), le
    module est bien téléchargé, mais GLTFLoader LÈVE « setMeshoptDecoder must
    be called before loading compressed files » dès que l'extension figure
    dans extensionsRequired (côté Draco : « No DRACOLoader instance
    provided. »). C'est une PROMESSE REJETÉE, pas un rendu noir — le noir est
    le mode de la section A, décodeurs ABSENTS donc 404. Ici charger() rejette
    et le canevas reste vide, exactement ce que décrit le commentaire de
    charger() dans viewer.js. On épingle donc les deux câblages, plus
    le chemin du décodeur Draco : VERSION.txt lui consacre une démonstration
    entière (la RACINE, pas le sous-dossier gltf/), et rien n'empêcherait
    sinon qu'il dérive vers gltf/ ou vers un CDN sans le moindre bruit.
    """
    js = _lire("lib3d/viewer.js")
    assert "meshopt_decoder" in js
    assert "DRACOLoader" in js
    assert "setDRACOLoader" in js
    assert "setMeshoptDecoder" in js
    assert "/assets/three/addons/libs/draco/" in js   # la racine vendorisée
    assert "libs/draco/gltf/" not in js               # et PAS le sous-dossier


def test_le_viewer_cadre_sur_la_boite_englobante():
    """Sans cadrage, un modèle en mètres et un modèle en centimètres donnent
    l'un un point, l'autre un mur : le cadrage est ce qui rend les étapes
    comparables."""
    js = _lire("lib3d/viewer.js")
    # l'EXPORT, pas le seul nom : la tâche 5 l'importe nommément, et un
    # `assert "cadrer" in js` resterait vrai sur une fonction devenue privée.
    assert "export function cadrer" in js
    assert "export async function charger" in js
    assert "Box3" in js


def test_le_viewer_libere_la_memoire_entre_deux_chargements():
    """Charger dix étapes de 200 Mo sans disposer sature le GPU.

    Les marqueurs portent sur du CODE : un simple `"dispose" in js` était
    satisfait par le commentaire de vider() lui-même (« sans disposer sature
    la carte »), au point qu'on pouvait vider le corps de la fonction en
    gardant sa prose et laisser le banc au vert. Vérifié par mutation.
    """
    js = _lire("lib3d/viewer.js")
    assert "export function vider" in js
    assert "geometry.dispose" in js and "m.dispose" in js
    # la mémoire HÔTE compte autant que la GPU : `gltf` retient parser.json,
    # les ArrayBuffers du GLB entier et le cache d'images.
    assert "api.gltf = null" in js


def test_le_redimensionnement_compare_le_tampon_et_non_les_pixels_css():
    """`canvas.width` est le tampon de dessin (multiplié par le pixelRatio),
    `clientWidth` des pixels CSS : les comparer directement rend la condition
    vraie à chaque image dès que le DPR dépasse 1. Mesure : tampon 800x600
    contre client 400x300, en permanence.
    """
    js = _lire("lib3d/viewer.js")
    assert "getPixelRatio" in js


# ── D. la chronologie ────────────────────────────────────────────────────────

def test_la_page_lit_la_chronologie_unifiee():
    js = _lire("etabli/etabli.js")
    assert 'jget("/api/etabli/sources")' in js
    # et la page l'appelle vraiment : sans cette ligne, elle ne démarre jamais
    assert "\namorcer();" in js
    # les libellés viennent du DISQUE — un nom de dossier, un `asset.json`
    # écrit à la main : sans esc(), une apostrophe double ferme l'attribut qui
    # les porte et emporte la ligne entière. On COMPTE les deux occurrences :
    # un simple `in` se satisfaisait de la branche Meshy et laissait retirer
    # esc() de la branche jobs — le chemin principal — sans rien casser.
    assert js.count('data-libelle="${esc(') == 2   # jobs ET meshy


def test_le_seuil_de_charge_est_affiche_et_configurable():
    """La spec §4.1 : 300 000 triangles ou 80 Mo, montré, jamais caché.

    Les marqueurs portent sur les COMPARAISONS, pas sur la constante : un
    « 300 000 » ou un « 80 Mo » écrit en commentaire suffisait à garder ce
    banc vert alors que le seuil n'était plus affiché nulle part. Vérifié
    par mutation — `lourd = false` et le bloc de la barre supprimé.
    """
    js = _lire("etabli/etabli.js")
    # VERROU D'ORTHOGRAPHE, et rien d'autre : il fige la valeur que la spec
    # documente, donc il attrape un seuil changé par accident — mais il mord
    # aussi sur `80 * 1024 ** 2`, identique en valeur comme en comportement.
    # Ce n'est PAS une garde de comportement ; les trois suivantes le sont.
    assert "80 * 1024 * 1024" in js
    assert "geo.tris > SEUIL.triangles" in js     # montré dans la barre du bas
    assert "tri > SEUIL.triangles" in js          # montré sur la puce
    assert "e.bytes > SEUIL.octets" in js         # montré sur la puce


def test_alt_clic_ouvre_la_comparaison():
    js = _lire("etabli/etabli.js")
    assert "ev.altKey" in js and "ouvrirComparaison(cible)" in js


def test_le_refus_se_voit_et_le_canevas_a_une_hauteur():
    """Les quatre finesses de la tâche 4, en quatre ancres sur du CODE.

    La file : sans le `.catch`, `_file` reste rejetée pour toujours et la
    chronologie devient muette au premier échec. Le refus : la classe posée
    par le JS doit exister dans la CSS, sinon l'échec est invisible. Les
    hauteurs : les deux maillons les PLUS SILENCIEUX de la chaîne, ceux dont
    le retrait ne laisse aucune trace — les cinq autres qu'énumère le
    commentaire de tête d'etabli.css ne sont pas gardés ici, un banc miroir
    qui lit du texte ne sachant pas suivre une chaîne de hauteurs.
    """
    js, css = _lire("etabli/etabli.js"), _lire("etabli/etabli.css")
    assert "_file = _file.then(" in js and ").catch(" in js
    assert 'classList.add("erreur")' in js and "#barreGeo.erreur" in css
    assert "grid-template-rows: minmax(0, 1fr)" in css
    assert "position: absolute; inset: 0" in css


# ── E. comparaison A/B ───────────────────────────────────────────────────────

def test_les_cameras_des_deux_vues_sont_synchronisees():
    """Comparer deux etapes sous deux angles differents ne compare rien.

    On ancre le BRANCHEMENT, pas le mot : `synchroniser` se cable DANS LES
    DEUX SENS. Une seule direction ferait suivre B quand on tourne A et
    laisserait A immobile quand on tourne B — la moitie des gestes
    comparerait alors deux angles differents, ce que cette fonction existe
    precisement pour empecher. Un `"synchroniser" in js` seul restait vert
    sur un seul des deux appels.
    """
    js = _lire("etabli/etabli.js")
    assert "synchroniser" in js
    assert "synchroniser(S.vueA, S.vueB)" in js
    assert "synchroniser(S.vueB, S.vueA)" in js


def test_la_ligne_d_ecart_chiffre_la_comparaison():
    js = _lire("etabli/etabli.js")
    for mot in ("triangles", "sha256", "dimensions"):
        assert mot in js
    assert "/report" in js
    # Les quatre marqueurs ci-dessus sont ceux du plan, et AUCUN ne mord :
    # « triangles » et « dimensions » sont les libelles affiches, « sha256 »
    # et « /report » vivent aussi dans les commentaires du fichier. Verifie
    # par mutation — detourner la requete vers /rapport les laissait tous les
    # quatre verts. La ligne suivante epingle l'APPEL ; les cles lues, elles,
    # le sont par le banc suivant.
    assert "/api/assets/3d/${encodeURIComponent(cible.job)}/report" in js


def test_la_ligne_d_ecart_lit_les_VRAIES_cles_de_la_fiche():
    """mesh_report nomme le compte `tris_lus` et les cotes `dims` (un objet
    largeur/hauteur/profondeur). Se tromper de cle afficherait des tirets
    partout sans rien casser : le banc doit donc ancrer les CLES, pas les
    libelles affiches, qui satisfont un `in` sans rien prouver.
    """
    js = _lire("etabli/etabli.js")
    assert "tris_lus" in js
    assert "dims" in js
    # ...et sur du CODE, pas sur de la prose. Les deux lignes ci-dessus sont
    # satisfaites par le commentaire qui NOMME ces cles — exactement le piege
    # que ce banc denonce, et verifie par mutation : renommer la lecture
    # `ga.tris_lus` en `ga.triangles` les laissait vertes. On epingle donc
    # les LECTURES elles-memes.
    assert "ga.tris_lus" in js and "gb.tris_lus" in js
    assert "g.dims.largeur" in js


def test_la_ligne_d_ecart_se_replie_sur_la_geometrie_du_navigateur():
    """`/api/assets/3d/{job}/report` REND 404 tant qu'aucune fiche n'existe, et
    ficheDe() avale ce 404 en rendant null. Sans repli, comparer deux etapes
    sans fiche afficherait des tirets partout — « le pire des echecs :
    silencieux ». La geometrie que charger() a MESUREE dans le navigateur est
    donc retenue dans S et passee a ligneEcart, qui la lit quand la fiche
    manque. On ancre les trois maillons : la declaration, la memorisation, la
    lecture — chacun se supprime sans bruit.
    """
    js = _lire("etabli/etabli.js")
    assert "geoA: null, geoB: null" in js        # declarees a la ligne de S
    assert "S.geoA = geo" in js                  # la vue A retient sa mesure
    assert "S.geoB = geoB" in js                 # la vue B aussi
    assert "geoA.tris" in js and "geoB.tris" in js   # et le repli les LIT
    # le plan passait `{ tris: null }`, qui annulait le repli qu'il concevait
    assert "{ tris: null }" not in js


def test_le_cadrage_tient_compte_de_l_aspect_et_A_est_recadree():
    """Ouvrir la vue B coupe la largeur en deux : c'est cette fonction meme qui
    fabrique le cas que cadrer() ne savait pas traiter. Mesure en navigateur,
    fenetre 1440x900 : une vue seule fait 860x824 (aspect 1,04) ; deux vues
    cote a cote tombent vers 0,5, ou plus d'un tiers de chaque modele sort du
    cadre — dans la fonction dont le but est de comparer deux modeles.

    Trois ancres : le cadrage CALCULE le recul (et seulement sous le seuil de
    rognage), il l'UTILISE dans la distance, et A est RE-cadree — a
    l'ouverture de B comme a sa fermeture, son aspect changeant dans les deux
    sens.
    """
    vue = _lire("lib3d/viewer.js")
    js = _lire("etabli/etabli.js")
    assert "const recul = aspect < seuil ? seuil / aspect : 1;" in vue
    assert "rayon * marge * recul" in vue
    assert js.count("cadrer(S.vueA)") == 2       # ouverture ET fermeture


def test_la_vue_B_a_son_propre_verrou_de_serialisation():
    """charger() n'est pas re-entrant et le dit : sur deux alt-clics rapides,
    le vider() du second s'execute pendant que le loadAsync du premier est
    encore en vol, puis les DEUX font scene.add() — le perdant reste dans le
    graphe pour toujours. La tache 4 a resolu cela pour la vue A ; B a besoin
    de la SIENNE, un jeton partage ferait qu'un clic sur A annulerait
    l'alt-clic sur B qui l'attendait (« seule la derniere demande compte » n'a
    de sens qu'A L'INTERIEUR d'une vue).
    """
    js = _lire("etabli/etabli.js")
    assert "_fileB = _fileB.then(" in js
    # fermer retire les demandes en file : sans cette garde, un chargement en
    # vol re-ouvrirait la vue B qu'on vient de fermer.
    assert "numero !== _demandeB" in js


def test_la_ligne_d_ecart_echappe_ce_qui_vient_du_disque():
    """Les libelles viennent du DISQUE (nom de dossier, `asset.json` ecrit a
    la main) et le sha256 d'un `report.json` que la doctrine du module decrit
    comme ouvert aux mains de l'utilisateur : les trois entrent dans
    innerHTML. esc() existe dans le fichier depuis la tache 4 ; la ligne
    d'ecart n'a pas le droit de faire exception.
    """
    js = _lire("etabli/etabli.js")
    assert "esc(S.a.libelle)" in js
    assert "esc(cible.libelle)" in js
    assert "esc(String(f.sha256)" in js
