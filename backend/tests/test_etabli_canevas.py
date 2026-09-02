"""L'Établi P2+P3 — canevas, chronologie et Parties
(plan 2026-08-29-etabli-p2-p3-canevas-parties).

Bancs MIROIRS : ils lisent les fichiers frontend comme du texte et y épinglent
des marqueurs. Patron de test_library_picker.py — c'est ainsi que le dépôt
garde un frontend vanilla sans navigateur au banc.

Run: .\\scripts\\run-tests.ps1 -Filter test_etabli_canevas.py
"""
import collections
import json
import math
import os
import pathlib
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

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


def _code(rel: str) -> str:
    """Le fichier SANS ses commentaires `/* … */`.

    Réservé aux assertions NÉGATIVES, et il leur est indispensable. Ce dépôt
    commente en expliquant ce qu'il ÉCARTE — « `sessionStorage` et non
    `localStorage` », « le partage passe par une classe, jamais par
    `#btnRetour` ». Un `assert "localStorage" not in js` posé sur le fichier
    entier est donc satisfait par la phrase même qui jure de ne pas s'en
    servir : le banc dirait rouge à un commentaire et vert à un appel. C'est
    la cinquième fois que ce dépôt corrige un marqueur satisfait par sa propre
    prose ; ici la prose faisait l'inverse, mais c'est le même défaut.

    Seuls les blocs `/* … */` tombent : les lignes `//` sont laissées, un
    retrait naïf couperait la moindre chaîne contenant `//`.
    """
    return re.sub(r"/\*.*?\*/", "", _lire(rel), flags=re.S)


# La fin d'une fonction écrite au premier niveau : une accolade SEULE en
# colonne 0. Nommée plutôt qu'écrite en clair partout — un littéral à
# échappement (deux retours à la ligne autour d'une accolade) recopié dix fois
# finit par en perdre un, et le découpage rend alors la fonction ENTIÈRE.
FIN_FONCTION = chr(10) + "}" + chr(10)


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
    """Comparer deux étapes sous deux angles différents ne compare rien.

    `assert "synchroniser" in js` est le corps littéral du plan, donc une
    exigence de spec — mais il ne garde RIEN par lui-même : le mot vit aussi
    dans les commentaires, et il restait vert sur un seul des deux appels.
    Ce qui mord, ce sont les deux lignes suivantes : le câblage se fait DANS
    LES DEUX SENS. Une seule direction ferait suivre B quand on tourne A et
    laisserait A immobile quand on tourne B — un geste sur deux comparerait
    alors deux angles différents, ce que cette vue existe pour empêcher.
    """
    js = _lire("etabli/etabli.js")
    assert "synchroniser" in js
    assert "synchroniser(S.vueA, S.vueB)" in js
    assert "synchroniser(S.vueB, S.vueA)" in js


def test_la_ligne_d_ecart_chiffre_la_comparaison():
    """Le corps du plan, tel quel — et AUCUN de ses quatre marqueurs ne mord.

    « triangles » et « dimensions » sont les libellés AFFICHÉS ; « sha256 » et
    « /report » vivent aussi dans les commentaires du fichier. Vérifié par
    mutation : détourner la requête de `/report` vers `/rapport` laissait les
    quatre au vert. Le nom de ce banc promet donc plus qu'il ne garde, et
    c'est dit ici plutôt que dans un commentaire de corps — ce qu'on lit en
    faisant tourner la suite, c'est le nom et cette docstring. La cinquième
    assertion, elle, épingle l'APPEL ; les clés lues le sont par le banc
    suivant, et le repli par celui d'après.
    """
    js = _lire("etabli/etabli.js")
    for mot in ("triangles", "sha256", "dimensions"):
        assert mot in js
    assert "/report" in js
    assert "/api/assets/3d/${encodeURIComponent(cible.job)}/report" in js


def test_la_ligne_d_ecart_lit_les_VRAIES_cles_de_la_fiche():
    """mesh_report nomme le compte `tris_lus` et les cotes `dims` (un objet
    largeur/hauteur/profondeur). Se tromper de clé afficherait des tirets
    partout sans rien casser : le banc doit donc ancrer les CLÉS, pas les
    libellés affichés, qui satisfont un `in` sans rien prouver.

    Les deux premières assertions sont celles de la spec, et elles sont
    satisfaites par le commentaire qui NOMME ces clés — le piège même que ce
    banc dénonce, vérifié par mutation : renommer la lecture `ga.tris_lus` en
    `ga.triangles` les laissait vertes. On épingle donc les LECTURES.
    """
    js = _lire("etabli/etabli.js")
    assert "tris_lus" in js
    assert "dims" in js
    assert "ga.tris_lus" in js and "gb.tris_lus" in js
    assert "g.dims.largeur" in js


def test_la_ligne_d_ecart_se_replie_sur_la_geometrie_du_navigateur():
    """`/api/assets/3d/{job}/report` REND 404 tant qu'aucune fiche n'existe, et
    ficheDe() avale ce 404 en rendant null. Sans repli, comparer deux étapes
    sans fiche n'afficherait que des tirets — « le pire des échecs :
    silencieux ». La géométrie que charger() a MESURÉE dans le navigateur est
    donc retenue dans S et passée à ligneEcart, qui la lit quand la fiche
    manque. On ancre les trois maillons — déclaration, mémorisation, lecture —
    parce que chacun se supprime sans bruit.
    """
    js = _lire("etabli/etabli.js")
    assert "geoA: null, geoB: null" in js        # déclarées à la ligne de S
    assert "S.geoA = geo" in js                  # la vue A retient sa mesure
    assert "S.geoB = geoB" in js                 # la vue B aussi
    assert "geoA.tris" in js and "geoB.tris" in js   # et le repli les LIT
    # le plan passait `{ tris: null }`, qui annulait le repli qu'il concevait
    assert "{ tris: null }" not in js


def test_le_cadrage_tient_compte_de_l_aspect_et_A_est_recadree():
    """Ouvrir la vue B coupe la largeur en deux : c'est cette fonction même qui
    fabrique le cas que cadrer() ne savait pas traiter. Mesuré en navigateur,
    fenêtre 1440×900 : une vue seule fait 860×824 (aspect 1,04) ; deux vues
    côte à côte tombent vers 0,58, où un tiers de chaque modèle sortait du
    cadre — dans la fonction dont le but est de comparer deux modèles. Après
    correction, les deux tiennent entiers et reçoivent la MÊME distance
    (4,0740 seul, 5,7213 à deux, identique à 1e-9 entre A et B).

    Trois ancres : le cadrage CALCULE le recul (et seulement sous le seuil de
    rognage), il l'UTILISE dans la distance, et A est RE-cadrée — à l'ouverture
    de B comme à sa fermeture, son aspect changeant dans les deux sens.

    SI LE COMPTE PASSE AU ROUGE : un troisième appel légitime est possible
    (P4/P5 peuvent re-cadrer ailleurs). Vérifier d'abord que les DEUX sites
    d'origine sont intacts — l'ouverture dans _ouvrirComparaison() et la
    fermeture dans fermerComparaison() — puis monter le compte délibérément.
    Ne jamais remplacer ce `count` par un `in` : c'est lui qui garde la paire.

    COMPTE MONTÉ À 4, DÉLIBÉRÉMENT (tâche « la plaque »). Les deux appels
    neufs sont l'entrée et la sortie de la vue « Sur la plaque » : l'empreinte
    étalée est bien plus large que le modèle assemblé, et l'aspect du modèle
    change donc dans les deux sens, exactement comme à l'ouverture et à la
    fermeture de la vue B. La PAIRE d'origine, elle, cesse d'être gardée par
    le seul total : elle l'est maintenant site par site, ci-dessous — un
    nombre qui monte à chaque tâche finirait sinon par ne plus rien dire.
    """
    vue = _lire("lib3d/viewer.js")
    js = _lire("etabli/etabli.js")
    assert "const recul = aspect < seuil ? seuil / aspect : 1;" in vue
    assert "rayon * marge * recul" in vue
    assert js.count("cadrer(S.vueA)") == 4
    # LES DEUX SITES D'ORIGINE, chacun dans SA fonction — c'est ce que le
    # compte gardait, et ce qu'il ne garde plus seul.
    ouvre = js.split("async function _ouvrirComparaison", 1)[1]
    ouvre = ouvre.split("\n}\n", 1)[0]
    assert "cadrer(S.vueA);" in ouvre
    ferme = js.split("function fermerComparaison", 1)[1]
    ferme = ferme.split("\n}\n", 1)[0]
    assert "cadrer(S.vueA);" in ferme


def test_la_boite_d_ecart_prend_sa_hauteur_avant_tout_cadrage():
    """Ce banc n'ancre PAS le cadrage : il ancre l'ORDRE dont il dépend.

    Mesure en navigateur (1440×900, deux GLB du dépôt) : la boîte d'écart
    passe de 1 à 5 lignes, soit 56 px repris aux vues, APRÈS le cadrage —
    l'aspect mesuré vaut alors 0,538 au lieu de 0,579 et les deux modèles
    sont posés 7,6 % trop loin (6,1536 au lieu de 5,7213), à la valeur près,
    trois fois sur trois. Le squelette à tirets donne à la boîte sa hauteur
    FINALE dès le démasquage, comme #vueB juste au-dessus. Un rAF ne
    corrigerait rien : le contenu final arrive après deux requêtes réseau.

    DEUX sites, et on les compte. Le second est perimerEcart() : écrit en
    `textContent`, il reprenait à la boîte quatre de ses cinq rangées APRÈS
    que charger() ait cadré la vue A — mêmes 56 px, mêmes 7,6 %, mais TROP
    PRÈS cette fois, donc ~3,8 % de la largeur rognée à chaque bord. Trop
    loin ne rogne jamais ; trop près, si. L'ancre d'ordre n'en est pas
    affectée : index() rend la première occurrence, qui reste le démasquage.

    La règle CSS, elle, rend l'invariant vrai par CONSTRUCTION. Sans elle,
    « même hauteur » n'est qu'une coïncidence arithmétique : la ligne
    `dimensions` (~87 caractères, ~548 px, suffixe d'unité compris)
    s'enroulait sous une fenêtre d'environ 1036 px dans le contenu final et
    pas dans le squelette — six rangées au lieu de cinq, après le cadrage.
    """
    js, css = _lire("etabli/etabli.js"), _lire("etabli/etabli.css")
    assert js.count("ligneEcart(null") == 2   # démasquage ET péremption
    assert js.index("ligneEcart(null") < js.index("charger(S.vueB") \
        < js.index("cadrer(S.vueA)")
    assert ".ecart > div" in css              # cinq rangées restent cinq


def test_la_vue_B_a_son_propre_verrou_de_serialisation():
    """charger() n'est pas ré-entrant et le dit : sur deux alt-clics rapides,
    le vider() du second s'exécute pendant que le loadAsync du premier est
    encore en vol, puis les DEUX font scene.add() — le perdant reste dans le
    graphe pour toujours. La tâche 4 a résolu cela pour la vue A ; B a besoin
    de la SIENNE, un jeton partagé ferait qu'un clic sur A annule l'alt-clic
    sur B qui l'attendait (« seule la dernière demande compte » n'a de sens
    qu'À L'INTÉRIEUR d'une vue).
    """
    js = _lire("etabli/etabli.js")
    assert "_fileB = _fileB.then(" in js
    # Fermer retire les demandes en file, sinon un chargement en vol rouvrirait
    # la vue qu'on vient de fermer. QUATRE sites : en tête, dans le `catch`,
    # après le chargement, après les deux fiches. Le `catch` est le dernier
    # venu — sans lui, fermer pendant un chargement qui échoue ouvrait une
    # bande d'erreur pour une comparaison que plus personne n'attend.
    assert js.count("numero !== _demandeB") == 4


def test_la_ligne_d_ecart_ne_melange_jamais_deux_modeles_A():
    """Les files de A et de B sont indépendantes et s'entrelacent : S.a peut
    passer de A1 à A2 pendant les deux requêtes /report. Sans capture du terme
    de gauche, la boîte afficherait le libellé de A2 au-dessus des triangles,
    des cotes et du sha256 de A1 — « une fiche fausse est pire qu'une fiche
    absente », la doctrine que ficheDe() invoque quatorze lignes plus haut.
    Le `!==` couvre du même geste le cas où A a échoué (S.a devenu null).
    """
    js = _lire("etabli/etabli.js")
    assert "const a = S.a;" in js
    assert "ficheDe(a)" in js
    assert "if (S.a !== a)" in js


def test_le_refus_de_la_vue_B_se_voit_comme_les_autres():
    """« Le refus se VOIT » : #barreGeo.erreur existe depuis la tâche 4 sous ce
    commentaire, et la ligne d'écart est le seul refus de la page qui n'y
    obéissait pas. La classe doit exister dans la CSS — sinon l'échec est
    invisible — et le JS doit la RETIRER au démasquage comme
    _ouvrirPrincipale() le fait pour la sienne, faute de quoi une erreur reste
    accrochée à la comparaison suivante. La page introduit par ailleurs
    `.ecart-tete` : sans règle, l'en-tête se rend comme une ligne de données et
    les <b> des données sont plus gras que le titre.
    """
    js, css = _lire("etabli/etabli.js"), _lire("etabli/etabli.css")
    assert ".ecart.erreur" in css and ".ecart-tete {" in css
    assert 'boite.classList.remove("hidden", "erreur")' in js
    # On COMPTE les trois sites qui posent la classe sur la boîte d'écart :
    # l'échec de chargement de B, la comparaison abandonnée, et la péremption.
    # Un simple `in` était satisfait par le seul perimerEcart() et laissait
    # retirer la classe des DEUX chemins de refus — vérifié par mutation.
    # Si ce compte rougit : vérifier que les trois sites sont là, puis le
    # monter délibérément.
    assert js.count('boite.classList.add("erreur")') == 3
    # et la boîte périme quand la vue A change de modèle sous elle
    assert "function perimerEcart()" in js
    assert js.count("perimerEcart();") == 2      # succès ET échec de la vue A


def test_la_ligne_d_ecart_echappe_ce_qui_vient_du_disque():
    """Les libellés viennent du DISQUE (nom de dossier, `asset.json` écrit à la
    main) et le sha256 d'un `report.json` que la doctrine du module décrit
    comme ouvert aux mains de l'utilisateur : les trois entrent dans innerHTML.
    esc() existe dans le fichier depuis la tâche 4 ; la ligne d'écart n'a pas
    le droit de faire exception.
    """
    js = _lire("etabli/etabli.js")
    assert "esc(S.a.libelle)" in js
    assert "esc(cible.libelle)" in js
    assert "esc(String(f.sha256)" in js


# ── F. le bout de chaine dans /studio3d ──────────────────────────────────────

def test_le_graphe_porte_le_noeud_07_etabli():
    js = _lire("studio3d/studio3d.js")
    assert '"etabli"' in js
    assert "07 · établi" in js


def test_la_viewbox_a_ete_elargie_pour_le_noeud_07():
    """Le nœud export tenait déjà le bord droit : sans élargissement, le 07
    serait hors cadre."""
    html = _lire("studio3d/index.html")
    assert "0 0 892 330" in html


def test_le_noeud_07_ouvre_la_page_etabli():
    js = _lire("studio3d/studio3d.js")
    assert "/etabli" in js


def test_la_geometrie_du_noeud_07_ferme_le_cadre_a_892():
    """892 = 760 + 132, et aucun des trois marqueurs ci-dessus ne le prouve.

    « etabli » entre guillemets, le libellé « 07 · établi » et la chaîne
    « /etabli » vivent tous les trois dans de la PROSE : un commentaire les
    satisfait sans qu'un seul nœud existe. On épingle donc les nombres de
    l'entrée NODES, et le câble qui relie le bord droit d'export (740) au port
    gauche du 07 (760) à mi-hauteur (94 + 164 / 2 = 176).

    La quatrième assertion est la seule que le plan ne demandait pas et la
    seule qui manquait vraiment : chaque câble du graphe part d'un CENTRE DE
    PORT — k1 part de 132,88 qui est le port [128, 56] de `prompt` (0 + 128 +
    3,5 ; 28 + 56 + 3,5, la pastille faisant 7 px). Or `export` ne portait
    qu'un port d'ENTRÉE, [-4, 78]. Sans le port de sortie [128, 78], k9
    partirait d'un bord nu, seul câble du graphe à ne pas naître d'une pastille.
    """
    js = _lire("studio3d/studio3d.js")
    assert 'id: "etabli", phase: "etabli", x: 760, y: 94, w: 132, h: 164' in js
    assert '"M740,176 C750,176 750,176 760,176"' in js
    assert 'kicker: "07 · établi"' in js
    assert 'kicker: "06 · export", chips: true, ports: [[-4, 78], [128, 78]] }' in js


def test_le_cadre_css_suit_la_viewbox_sinon_les_huit_cables_decrochent():
    """`.graph svg` porte une LARGEUR EXPLICITE (740 px), pas un 100 %.

    Élargir la seule viewBox à 892 ferait tenir 892 unités dans 740 px :
    preserveAspectRatio vaut « xMidYMid meet » par défaut, donc tout le dessin
    rétrécirait de 17 % et descendrait de 28 px — les HUIT câbles d'origine
    décrocheraient de leurs nœuds. Le conteneur `.graph` fait lui aussi 740 px
    de large, et le nœud 07 (760 → 892) tomberait entièrement hors de sa boîte.
    Le plan annonçait « trois constantes, aucune autre géométrie ne bouge » :
    c'est faux, la CSS porte deux fois la même largeur et doit suivre.
    """
    css = _lire("studio3d/studio3d.css")
    assert ".graph { position: relative; width: 892px; height: 354px; }" in css
    assert "width: 892px; height: 330px;" in css


def test_le_noeud_07_se_clique_mais_ne_s_edite_pas():
    """La boucle de construction branche SOIT les gestionnaires génériques,
    SOIT la porte — jamais les deux. `openEditor("etabli")` ouvrirait un
    éditeur de tâche Meshy pour un nœud qui n'est pas une tâche, et
    `S.pinned = "etabli"` épinglerait au panneau droit une phase dont aucun
    pipeline n'émettra jamais l'état.
    """
    js = _lire("studio3d/studio3d.js")
    assert "function brancherEtabli" in js
    # le `else` est TOUTE l'assertion : sans lui les deux branchements
    # coexistent et le double-clic ouvre un éditeur pour une porte
    assert "if (n.door) brancherEtabli(el);\n    else {" in js


def test_le_07_navigue_DANS_l_iframe_et_previent_avant_de_tuer_une_serie():
    """CE BANC A ÉTÉ RETOURNÉ, et il dit pourquoi.

    La tâche 6 ouvrait l'Établi dans un NOUVEL ONGLET, précisément pour ne pas
    naviguer dans l'iframe : /studio3d est réellement iframé
    (patch_bundle_studio3d.py greffe un sous-onglet « 3D Studio » =
    `iframe src="/studio3d/"` dans le hub Game Assets), et y charger l'Établi
    détruit cette page — avec elle la série Meshy que runPipeline() pilote
    depuis ici.

    L'utilisateur a tranché autrement, en connaissance de cet écran : « je veux
    conserver l'atelier dans une vue iframe pour éviter toute confusion, et
    rajoute du coup un bouton pour revenir au graph ». Un outil qui s'échappe
    dans un onglet quand tout le reste de l'application vit dans le hub est une
    confusion de plus ; l'Établi prend donc la place du graphe, et un bouton
    « ← 3D Studio » l'y ramène (section J).

    PARTIR COÛTE DEUX CHOSES, et le banc épingle le traitement des deux.

    La CONFIGURATION du studio (`S.cfg` : prompt, nom, image, modèle,
    polycount, animations, formats) ne vivait qu'en mémoire — aucune
    persistance, et le boot ne relit que status/health/balance/tasks. Sous
    l'ancienne décision la page survivait dans son onglet ; c'est CE
    retournement qui introduit la perte, et le bouton de retour qui la rend
    routinière — un aller-retour est le geste normal, la série en vol est
    l'exception. Elle est donc RÉPARÉE, pas documentée : voir
    test_le_studio_garde_sa_configuration_entre_deux_visites_a_l_etabli.

    La SÉRIE MESHY EN VOL, elle, est IRRÉDUCTIBLE : un pipeline est une suite
    d'appels en cours, pas un état ; aucun stockage ne la rattrape, et Meshy ne
    rembourse que les tâches ÉCHOUÉES, pas celles qu'on abandonne. Ce coût-là
    ne se répare pas — il se DEMANDE. C'est la garde ci-dessous, épinglée au
    même titre que la navigation.
    """
    js = _lire("studio3d/studio3d.js")
    assert "?job=${encodeURIComponent(S.cfg.name)}" in js
    # LE CORPS ENTIER, comme avant le retournement et pour le même motif : ce
    # qui compte est ce que la fonction FAIT, pas l'orthographe d'un plan.
    corps = js.split("function ouvrirEtabli", 1)[1].split("\n}\n", 1)[0]
    # UNE SEULE instruction de navigation, et elle vaut pour les deux cas :
    # dans l'iframe quand la page y est embarquée, dans l'onglet sinon. Un
    # `window.open` de repli rouvrirait par la bande l'onglet qu'on retire.
    assert "location.href = url;" in corps
    assert "window.open" not in corps
    # ET LA GARDE, AVANT la navigation. Une garde posée APRÈS le
    # `location.href` serait du code mort dans une page déjà en train de
    # partir : la série serait morte avant que la question soit posée.
    assert 'S.run && S.run.status === "running"' in corps
    assert corps.index('S.run.status === "running"') < corps.index("location.href")
    # DEMANDER et non refuser, par la règle de réversibilité : on demande quand
    # le coût est inévitable, on refuse quand le remède est à un clic. Ici
    # aucun geste ne sauve la série, et un refus sec enfermerait l'utilisateur
    # hors de l'Établi pour toute la durée d'une série — qui se compte en
    # minutes. (L'Établi, lui, REFUSE : son remède est dans la barre du bas.
    # Voir test_le_retour_refuse_de_perdre_les_modifications_en_attente.)
    assert "confirm(" in corps


def test_le_rail_gauche_offre_l_etape_07():
    html, js = _lire("studio3d/index.html"), _lire("studio3d/studio3d.js")
    assert 'id="goEtabli"' in html
    # `$("#goEtabli")` lèverait si le bouton manquait : les deux vont ensemble
    assert '$("#goEtabli").addEventListener("click", ouvrirEtabli);' in js


def test_le_noeud_07_ne_peint_aucun_etat_de_tache():
    """Aucun MeshyPipeline n'émettra jamais la phase « etabli ».

    phaseView() ne lève pas pour autant — elle rend un objet par défaut — mais
    ce qu'elle rend est un PENDING ÉTERNEL, barre à 0 % et « 0 cr ». Un état
    inventé sur un nœud qui n'est pas une tâche est un mensonge d'interface :
    la promesse est donc réduite, et ce nœud n'a ni barre, ni état, ni
    crédits — ni dans le gabarit qui le construit, ni dans paint().

    Le câble compte pareil : peint par phase, k9 resterait en pointillé
    « en attente » d'une phase qui ne démarrera pas.

    L'autre moitié du dessin est ce qu'il montre BIEN, et elle n'était gardée
    par rien : supprimer l'un des deux libellés laissait les bancs verts alors
    que le nœud perdait son titre à l'écran. Ils vivent dans le GABARIT et non
    dans paint() — ils ne changent jamais, et paint() est cadencée à 16 ms
    pendant une série —, ce qui les rend épinglables ici.
    """
    js = _lire("studio3d/studio3d.js")
    assert "if (n.door) continue;" in js
    assert """${n.door ? "L'Établi" : ""}""" in js
    assert '${n.door ? "parties · rig · versions" : ""}' in js
    assert '<span class="node-door">ouvrir →</span>' in js
    assert "if (c.door) {" in js
    # DEUX sites dans la CSS : la règle de base et l'état de survol. Un simple
    # `".node-door" in css` restait vert quand on retirait la règle de base —
    # le sélecteur de survol la contient en sous-chaîne. Vérifié par mutation.
    assert _lire("studio3d/studio3d.css").count(".node-door") == 2


# ── G. ?job= : la promesse du lien tenue par la page ─────────────────────────

def test_l_etabli_tient_la_promesse_du_parametre_job():
    """Le nœud 07 passe `?job=<nom>` ; sans lecture, la page ignorait la chaîne
    de requête et l'utilisateur atterrissait sur la chronologie entière, sans
    rapport visible avec le job d'où il venait — une URL qui promet et ne tient
    pas. La page MARQUE le bloc et y fait défiler.

    Elle n'OUVRE rien : charger() passe par un verrou de sérialisation, et une
    ouverture surprise au chargement de page serait coûteuse autant que
    déroutante. Job absent de la chronologie : rien, en silence.
    """
    js, css = _lire("etabli/etabli.js"), _lire("etabli/etabli.css")
    assert 'URLSearchParams(location.search).get("job")' in js
    assert "function marquerJobVise" in js
    assert "marquerJobVise();" in js              # et elle est APPELÉE
    assert 'classList.add("vise")' in js
    assert "scrollIntoView" in js
    # sans la règle, le marquage est posé et INVISIBLE — le pire des échecs
    assert ".job.vise {" in css
    # les blocs portent de quoi se laisser retrouver : l'id du dossier ET le nom
    assert 'data-job="${esc(j.id)}" data-nom="${esc(j.nom)}"' in js


def test_le_marquage_du_job_ne_charge_rien_tout_seul():
    """Ce banc garde la RETENUE de la fonction, pas son existence : y glisser
    un `ouvrirPrincipale(...)` ferait charger un GLB au chargement de la page,
    par-dessus le verrou de sérialisation et sans que personne l'ait demandé.
    """
    js = _lire("etabli/etabli.js")
    corps = js.split("function marquerJobVise", 1)[1].split("\n}\n", 1)[0]
    assert "ouvrirPrincipale" not in corps
    assert "charger(" not in corps


# ── H. Parties : selection et isolation ──────────────────────────────────────
# (le plan appelait cette section « G » ; la lettre etait deja prise par la
# section ?job=, on enchaine donc sur H.)

def test_les_trois_granularites_de_selection_existent():
    """EXIGENCE DE SPEC — CE BANC NE GARDE RIEN PAR LUI-MÊME. Les trois mots
    sont satisfaits par de la PROSE : le commentaire de tête du module en
    contient déjà deux. Ce dépôt a payé quatre fois cette erreur (un banc de
    la tâche 3 asserait `"dispose" in js`, satisfait par le mot « disposer »
    d'un commentaire, et le corps de la fonction pouvait disparaître en
    restant vert). Ce qui MORD est `..._sont_REELLEMENT_branchees`, plus bas.
    """
    js = _lire("lib3d/selection.js")
    for mot in ("noeud", "maillage", "materiau"):
        assert mot in js


def test_la_selection_se_fait_aussi_au_clic_dans_le_canevas():
    """EXIGENCE DE SPEC, GARDE FAIBLE : le seul mot « Raycaster » serait
    satisfait par un import inutilisé. Le banc qui mord sur le clic est
    `..._est_volontaire_et_ne_vole_pas_l_orbite`.
    """
    js = _lire("lib3d/selection.js")
    assert "Raycaster" in js


def test_l_isolation_est_un_affichage_et_n_ecrit_rien():
    """Isoler ne doit toucher AUCUNE route d'ecriture.

    Les deux premières assertions sont des exigences de spec faibles
    (« isoler » vit aussi dans les commentaires). La TROISIÈME, elle, est une
    vraie garde STRUCTURELLE, et la plus précieuse du lot : elle tient la
    règle « le navigateur voit et manipule, Python écrit » quoi qu'il advienne
    du corps des fonctions. Ne pas l'affaiblir.
    """
    js = _lire("lib3d/selection.js")
    assert "isoler" in js
    assert "/api/etabli/extraire" not in js
    assert "fetch" not in js


def test_l_index_de_noeud_gltf_est_conserve_pour_le_serveur():
    """Le serveur raisonne en index de noeud glTF ; three.js en objets. Sans
    ce pont, l'extraction viserait le mauvais noeud.

    EXIGENCE DE SPEC, GARDE FAIBLE : « userData » et « indexGltf » se lisent
    aussi dans un commentaire. C'est
    `..._vient_de_parser_associations_et_non_des_noms` qui garde la JUSTESSE
    du pont — la seule chose qui compte ici.
    """
    js = _lire("lib3d/selection.js")
    assert "userData" in js
    assert "indexGltf" in js


def test_les_trois_granularites_sont_REELLEMENT_branchees():
    """Trois granularités parce que les moteurs ne découpent pas pareil : un
    modèle Meshy arrive souvent en un nœud UNIQUE à plusieurs matériaux — le
    lister par nœud n'en montrerait qu'une ligne — quand un Tripo arrive en
    plusieurs nœuds. Aucune des trois ne suffit seule, donc les trois doivent
    être PRODUITES, ATTEIGNABLES, et opérantes jusqu'à l'isolation.
    """
    sel, js = _lire("lib3d/selection.js"), _lire("etabli/etabli.js")
    # l'inventaire remplit vraiment les trois listes
    assert "noeuds.push(" in sel
    assert "maillages.push(" in sel
    assert "materiaux.set(" in sel
    # La Map est remplie ci-dessus, encore faut-il qu'elle SORTE. Mutation
    # confirmée : `materiaux: []` gardait tout le reste vert — la chaîne était
    # couverte aux deux bouts (production, panneau, isolation) et percée
    # exactement à la jointure. Un banc qui promet cette couverture dans son
    # docstring sans la tenir est pire qu'un banc absent.
    assert "materiaux: [...materiaux.values()]" in sel
    # le panneau sait aller chercher les trois, et offre le choix
    for cle in ("inv.noeuds", "inv.maillages", "inv.materiaux"):
        assert cle in js, cle
    assert '["noeud", "maillage", "materiau"].map' in js
    # et l'isolation sait retenir un MATÉRIAU par son uuid. Sans cette
    # branche, cocher un matériau puis isoler passerait le modèle ENTIER en
    # fantôme : la granularité serait affichée, et inopérante — le pire des
    # échecs, silencieux.
    assert "retenu.has(m.uuid)" in sel
    # et un NŒUD retenu emporte son sous-arbre : un nœud glTF peut n'être
    # qu'un contenant, sans géométrie propre. Sans la remontée des parents,
    # le retenir n'isolerait rien et passerait le modèle entier en fantôme.
    assert "n = n.parent" in sel


def test_l_index_glTF_vient_de_parser_associations_et_non_des_noms():
    """LE pont qui décide quel nœud le serveur extraira (tâche 8). Vérifié
    dans le GLTFLoader vendorisé (0.185.1) : le parser tient `associations`,
    une Map Object3D → {nodes, meshes, primitives}, remplie à la construction
    de la scène (`parser.associations.get( node ).nodes = nodeIndex`) puis
    RÉDUITE aux objets réellement entrés dans la scène. C'est la
    correspondance exacte, établie par celui qui a construit les objets.

    La deviner en appariant les NOMS échoue en silence dans au moins trois
    cas : un nœud sans nom n'obtient jamais d'index ; deux nœuds de même nom
    reçoivent les leurs dans l'ordre de PARCOURS, qui n'est pas forcément le
    leur ; un nom porté à la fois par un nœud et par un maillage brouille la
    carte. L'extraction viserait alors le mauvais maillage, et écrirait un GLB
    faux sans que rien ne grince.
    """
    js = _lire("lib3d/selection.js")
    assert "parser.associations" in js
    # Le champ est LU, et c'est bien LUI qui devient l'index. Un simple
    # `"lien.nodes" in js` restait VERT quand l'affectation prenait une
    # autre valeur — la garde `lien.nodes === undefined` deux lignes plus
    # haut suffisait à le satisfaire. Mesuré par mutation, corrigé ici.
    assert "o.userData.indexGltf = lien.nodes;" in js
    # la carte du chargeur passe AVANT le repli par nom, qui reste un repli
    assert js.index("assoc.get(o)") < js.index("parNom.get(")
    # ATTENTION : la ligne ci-dessus ne garde que l'ordre du TEXTE. Le
    # gate d'exécution, lui, est ce `return` — sans lui le repli tourne
    # quand même et réattribue par nom des index que la Map avait déjà
    # posés justes. Vérifié par mutation : inverser la condition ne
    # bougeait AUCUNE des autres assertions.
    assert "if (poses) return;" in js
    # et la provenance se DÉCLARE : la tâche 8 saura sur quoi elle s'appuie
    assert "indexGltfSource" in js
    assert '"associations"' in js and '"nom"' in js


def test_le_clic_de_selection_est_volontaire_et_ne_vole_pas_l_orbite():
    """OrbitControls est branché sur le MÊME canevas (viewer.js le construit
    avec le <canvas>). Sur un simple `pointerdown`, chaque début de rotation
    sélectionnerait ce qui passe sous le curseur : on ne pourrait plus tourner
    le modèle sans le désigner. La sélection réclame donc un aller-retour au
    même endroit, et le bouton gauche seulement.
    """
    js = _lire("lib3d/selection.js")
    avant, apres = js.split('"pointerup"', 1)
    # le bouton est filtré au POSER
    assert "ev.button !== 0" in avant
    # le rayon n'est tiré qu'au RELEVER, et nulle part avant
    assert "setFromCamera" in apres
    assert "setFromCamera" not in avant
    # et seulement si le pointeur n'a pas dérivé entre les deux
    assert "const TOLERANCE_CLIC" in js
    assert "Math.hypot(" in apres and "TOLERANCE_CLIC" in apres


def test_le_clic_de_selection_n_est_branche_qu_une_seule_fois():
    """`etabli:charge` est émis à CHAQUE chargement réussi. Brancher
    designerAuClic() dans son écouteur sans garde empile un écouteur par
    modèle : au troisième GLB, un clic tire trois rayons et redessine trois
    fois le panneau. Le canevas, lui, est créé une fois pour la vie de la page
    (viewer.js met les deux vues en cache et ne démonte jamais le canevas) :
    un seul branchement suffit, et il vaut pour tous les modèles suivants.
    """
    js = _lire("etabli/etabli.js")
    assert js.count("designerAuClic(") == 1        # un SEUL site d'appel
    bloc = js.split('addEventListener("etabli:charge"', 1)[1]
    assert bloc.index("if (_clicBranche) return;") < bloc.index("designerAuClic(")
    assert "_clicBranche = true;" in bloc


def test_la_selection_ne_survit_pas_au_changement_de_modele():
    """Les uuid retenus appartiennent au modèle PRÉCÉDENT : gardés, ils ne
    désignent plus rien — ou pire, désigneront un jour autre chose, et la
    tâche 8 les enverra tels quels au serveur. Exactement le problème que la
    tâche 4 a résolu pour S.enAttente, et le même remède : vidés là où le
    modèle affiché change, quoi qu'il arrive, et donc AVANT le chargement —
    pas dans un rendu qui n'a lieu qu'en cas de succès.
    """
    js = _lire("etabli/etabli.js")
    assert "SEL.retenus.clear();" in js
    i_vide = js.index("SEL.retenus.clear();")      # le PREMIER site du fichier
    assert js.index("S.enAttente.length = 0;") < i_vide
    assert i_vide < js.index("await charger(S.vueA")


def test_le_panneau_Parties_echappe_les_noms_venus_du_GLB():
    """Les noms de nœuds, de maillages et de matériaux viennent du FICHIER
    GLB — donc du dehors, au même titre que les libellés du disque de la
    tâche 4. Ce fichier s'est donné la règle que tout ce qui entre dans
    innerHTML passe par esc(), et les attributs data- ne font pas exception :
    c'est même là qu'un guillemet casse la ligne entière.
    """
    js = _lire("etabli/etabli.js")
    assert "esc(x.nom)" in js
    assert "esc(x.uuid)" in js
    assert "esc(x.indexGltf" in js
    corps = js.split("function rendreParties", 1)[1].split("\n}\n", 1)[0]
    assert '$("#panParties")' in corps
    assert "box.innerHTML" in corps
    # aucune interpolation NUE de ce qui vient du fichier
    assert "${x.nom}" not in corps
    assert "${x.uuid}" not in corps


def test_l_isolation_rend_l_opacite_d_origine_et_reste_un_affichage():
    """« Tout revoir » ne repose pas une opacité arbitraire : le matériau doit
    retrouver CELLE QU'IL AVAIT — un verre à 0,4 resterait sinon opaque après
    une isolation, et le modèle serait durablement faux à l'écran alors même
    que rien n'a été écrit. D'où une mémoire posée UNE seule fois, avant la
    première altération.
    """
    sel, js = _lire("lib3d/selection.js"), _lire("etabli/etabli.js")
    assert "m.userData.opaciteOrigine === undefined" in sel
    assert "m.opacity = dedans ? m.userData.opaciteOrigine : fantome;" in sel
    assert "m.transparent = dedans ? m.userData.transparentOrigine : true;" in sel
    # surligner() a la MÊME dette, et son échec est plus silencieux encore :
    # rendre 0x000000 au lieu de l'émission d'origine noircit DÉFINITIVEMENT
    # une lampe ou un néon — courants sur un Meshy — au premier clic, sans
    # retour, et l'utilisateur accusera le modèle. Garder l'ancre de l'opacité
    # et pas celle-ci serait arbitraire : les deux restaurations sont jumelles.
    assert ": m.userData.emissiveOrigine);" in sel
    # « tout revoir » isole SUR RIEN, ce qui restaure tout
    assert "isoler(S.vueA, [])" in js


def test_le_module_de_selection_est_servi_a_la_page():
    """La page l'importe par URL ABSOLUE. Non servi, le panneau Parties serait
    mort-ne et le refus ne vivrait que dans la console du navigateur — nulle
    part au banc. Le chemin de l'import est epingle avec : les deux ne peuvent
    plus diverger en silence.
    """
    assert '"/lib3d/selection.js"' in _lire("etabli/etabli.js")
    r = _client().get("/lib3d/selection.js")
    assert r.status_code == 200
    assert "export function isoler" in r.text


def test_le_module_de_selection_ne_connait_aucune_route():
    """La règle structurante de la page, vue du navigateur : il voit et
    manipule, Python écrit. Ce module n'a donc aucune adresse à connaître, ni
    aucun moyen de fabriquer un GLB. Garde STRUCTURELLE, comme le
    `"fetch" not in js` plus haut : elle tient même si le corps des fonctions
    change du tout au tout.
    """
    js = _lire("lib3d/selection.js")
    assert "/api/" not in js
    assert "GLTFExporter" not in js
    assert "XMLHttpRequest" not in js


# ── I. la porte d'ecriture : separer, transformer, reparer ───────────────────
# (le plan nommait cette section « I » ; G etait prise par ?job=, H par les
# Parties. Tant que « ecrire la version » n'a pas ete clique, rien n'a bouge
# sur le disque : ces bancs gardent cette phrase-la.)

def test_la_page_appelle_les_routes_d_ecriture_de_p1():
    """EXIGENCE DE SPEC — CE BANC NE GARDE PRESQUE RIEN. Les trois chaînes
    sont satisfaites par de la PROSE : le commentaire de tête du fichier écrit
    déjà « /api/etabli/* », et une table de constantes jamais lue les
    contiendrait tout aussi bien. Ce qui MORD est
    `..._un_echec_au_milieu_d_une_serie_se_dit_et_ne_fourche_pas`, qui épingle
    l'APPEL, et `..._l_extraction_est_ecrite_en_DERNIER`, qui épingle l'ordre.
    """
    js = _lire("etabli/etabli.js")
    for route in ("/api/etabli/extraire", "/api/etabli/transformer",
                  "/api/etabli/reparer"):
        assert route in js


def test_rien_n_est_ecrit_sans_le_bouton():
    """Les deux premières assertions sont celles du plan, et elles NE GARDENT
    RIEN : « enAttente » et « btnEcrire » sont deux mots que n'importe quel
    commentaire satisfait, et ce fichier les écrit tous les deux en prose. La
    file est gardée par les bancs de fusion, d'ordre et d'échec ci-dessous.

    Les deux dernières mordent, et sur un défaut réel : le gizmo redessine la
    barre à CHAQUE glissement (noterAttente appelle rendreAttente), si bien que
    le bouton grisé pendant les requêtes renaît ACTIF au milieu de la série.
    Deux séries en vol écriraient deux fois la même correction sous deux
    numéros de version. Le verrou tombe dans un `finally` : posé pour de bon,
    il condamnerait le bouton pour le reste de la session.
    """
    js = _lire("etabli/etabli.js")
    assert "enAttente" in js
    assert "btnEcrire" in js
    assert "if (_ecritEnCours) return;" in js
    # Et le bouton PORTE l'etat du verrou : sans cet attribut il renait actif
    # au milieu de la serie, le clic se solde par le `return` muet ci-dessus,
    # et ce fichier ne se tait nulle part ailleurs. Verifie par mutation :
    # retirer l'interpolation laissait tout vert.
    assert '<button id="btnEcrire"${_ecritEnCours ? " disabled" : ""}>' in js
    corps = js.split("async function ecrireVersion", 1)[1].split("\n}\n", 1)[0]
    assert corps.index("} finally {") < corps.index("_ecritEnCours = false;")


def test_la_page_ne_fabrique_jamais_un_glb():
    """Regle de l'option C : pas de GLTFExporter, pas de Blob GLB cote client.
    Son absence du bundle rend la regle impossible a enfreindre par megarde.

    LA GARDE LA PLUS PRÉCIEUSE DU LOT, et la seule du plan qui morde : elle
    tient « le navigateur voit et manipule, Python écrit » quoi qu'il advienne
    du corps des fonctions. Les QUATRE fichiers du canevas sont couverts —
    selection.js l'est aussi par `..._ne_connait_aucune_route` et plaque.js
    par `test_LA_PLAQUE_N_ECRIT_RIEN...`, et le doublon est délibéré : si ce
    banc-ci était un jour le seul survivant, il devrait couvrir la chaîne
    entière à lui seul. TOUT FICHIER NEUF DE /lib3d SE JOINT À CETTE LISTE.
    """
    js = _lire("etabli/etabli.js")
    assert "GLTFExporter" not in js
    viewer = _lire("lib3d/viewer.js")
    assert "GLTFExporter" not in viewer
    assert "GLTFExporter" not in _lire("lib3d/selection.js")
    assert "GLTFExporter" not in _lire("lib3d/plaque.js")


def test_les_gizmos_sont_branches():
    """La première assertion est celle du plan, et elle NE GARDE RIEN : le seul
    mot « TransformControls » est satisfait par un import inutilisé — ou par le
    commentaire qui raconte le piège juste au-dessus. Les deux suivantes
    mordent : sans l'APPEL depuis le clic dans le canevas, et sans l'`attach()`
    qui suit, poserGizmo() serait du code mort et la page n'aurait aucun gizmo,
    tout en gardant vert le banc du helper ci-dessous — vérifié par mutation.
    """
    js = _lire("etabli/etabli.js")
    assert "TransformControls" in js
    bloc = js.split("designerAuClic(", 1)[1]
    assert "poserGizmo(obj);" in bloc
    assert "GIZMO.attach(noeud);" in js


def test_le_gizmo_entre_dans_la_scene_par_son_HELPER():
    """PIÈGE FATAL ET MUET. Dans le three.js vendorisé (0.185.1),
    `TransformControls` n'est PLUS un Object3D : le fichier déclare
    `class TransformControls extends Controls` (ligne 77). Or `Object3D.add()`
    d'un non-Object3D se contente d'un avertissement en console et rend la
    main sans rien faire — le gizmo ne serait JAMAIS visible, et aucun banc
    qui lit du texte ne le verrait. Ce qui entre dans la scène est son helper :
    `getHelper()` (ligne 453) rend `this._root` (ligne 455), un
    `TransformControlsRoot extends Object3D` (ligne 1111).
    """
    js = _lire("etabli/etabli.js")
    assert "S.vueA.scene.add(GIZMO.getHelper());" in js
    # et surtout PAS l'objet de controle lui-meme, qui ne ferait rien
    assert "scene.add(GIZMO)" not in js


def test_le_gizmo_lache_son_noeud_AVANT_le_chargement_suivant():
    """`GIZMO.attach(objet)` garde une référence FORTE. Au chargement suivant,
    `charger()` appelle `vider()`, qui `dispose()` géométries et matériaux : le
    gizmo tiendrait alors un objet mort et continuerait de le peindre. Le
    `detach()` doit donc s'exécuter là où le modèle affiché change quoi qu'il
    arrive — à côté de `S.enAttente.length = 0` et de `SEL.retenus.clear()` —
    et non dans l'écouteur `etabli:charge`, qui n'arrive qu'APRÈS le
    chargement et SEULEMENT en cas de succès. Même leçon, troisième fois.
    """
    js = _lire("etabli/etabli.js")
    assert "GIZMO.detach();" in js
    assert js.index("S.enAttente.length = 0;") < js.index("GIZMO.detach();") \
        < js.index("await charger(S.vueA")


def test_deux_noeuds_deplaces_ne_s_ecrasent_pas():
    """`findIndex` + remplacement de l'entrée entière perd le premier nœud
    déplacé au profit du second, en silence : la barre continue d'annoncer
    « 1 modification en attente » et le serveur ne reçoit qu'un TRS. Or
    `/api/etabli/transformer` accepte un dictionnaire de PLUSIEURS nœuds. Les
    charges `transformer` FUSIONNENT donc — `reparer` et `extraire` se
    remplacent, et le fichier dit pourquoi.
    """
    js = _lire("etabli/etabli.js")
    corps = js.split("function noterAttente", 1)[1].split("\n}\n", 1)[0]
    assert 'operation === "transformer"' in corps
    assert "Object.assign(S.enAttente[i].charge, charge)" in corps
    # La barre ENUMERE, et c'est ce qui rend la fusion visible a l'ecran. On
    # epingle le COMPTE, pas le libelle : `"nœud(s) déplacé(s)" in js` restait
    # VERT quand la barre reaffichait « 1 modification » — le commentaire de
    # libelleAttente cite justement ce libelle. Verifie par mutation.
    assert "${Object.keys(t.charge).length} nœud(s) déplacé(s)" in js


def test_l_extraction_est_ecrite_en_DERNIER_car_elle_renumerote():
    """`mesh_edit.extraire` REMAPPE le document (`_carte`) : les index de nœud
    du modèle affiché ne valent plus rien après elle. `reparer` AJOUTE au
    contraire un nœud racine en fin de tableau et `transformer` ne touche
    qu'un champ — aucun des deux ne déplace un index existant. Écrire
    l'extraction avant une transformation ferait donc porter les index du
    modèle AFFICHÉ sur un document déjà remappé : le mauvais maillage, sur
    disque, sans que rien ne grince. L'ordre d'écriture est donc FIXE, et ne
    suit pas l'ordre où l'utilisateur a cliqué.
    """
    js = _lire("etabli/etabli.js")
    assert 'const ORDRE_ECRITURE = ["reparer", "transformer", "extraire"];' in js
    # LE TRI LUI-MEME. Mesure : remplacer le corps de fileOrdonnee() par
    # `return [...S.enAttente];` remet la file dans l'ordre des CLICS et ne
    # faisait rougir personne — la table pouvait rester declaree et inerte,
    # et ce banc restait vert sous un titre qui promettait le contraire.
    tri = js.split("function fileOrdonnee", 1)[1].split("\n}\n", 1)[0]
    assert ("ORDRE_ECRITURE.indexOf(a.operation) - "
            "ORDRE_ECRITURE.indexOf(b.operation)") in tri
    corps = js.split("async function ecrireVersion", 1)[1].split("\n}\n", 1)[0]
    assert "fileOrdonnee()" in corps
    # et surtout PAS l'ordre d'insertion, qui est celui des clics
    assert "for (const t of S.enAttente)" not in corps


def test_un_echec_au_milieu_d_une_serie_se_dit_et_ne_fourche_pas():
    """C'EST LA FONCTION QUI ÉCRIT SUR LE DISQUE, et le plan ne lui donnait
    pas un `try`. Si la troisième de cinq opérations échoue, les deux
    premières SONT déjà écrites : sans traitement, la file n'est pas vidée, la
    chronologie n'est pas rafraîchie, et l'utilisateur ne sait ni ce qui est
    passé ni ce qui reste. Pire, rejouer le reste repartirait de l'ANCIENNE
    version et forcherait l'historique en silence.

    Le contrat tenu ici : on dit ce qui a été écrit et ce qui ne l'a pas été,
    la file est vidée dès que quelque chose a touché le disque (ce qui reste
    est indexé sur le modèle d'avant), et la chronologie apprend les versions
    neuves même en cas d'échec partiel.
    """
    js = _lire("etabli/etabli.js")
    corps = js.split("async function ecrireVersion", 1)[1].split("\n}\n", 1)[0]
    assert "try {" in corps and "} catch (e) {" in corps
    assert "jpost(ROUTES[t.operation], corps)" in corps    # l'APPEL, epingle
    assert "ecrites.push(t.operation);" in corps           # ce qui EST passe
    # LE CHAINAGE, sans quoi la serie n'est pas une lignee. Mesure : supprimer
    # cette ligne fait ecrire trois versions SŒURS nees du meme parent — la
    # deuxieme perd la premiere, la troisieme perd les deux — et le banc
    # restait entierement vert. C'est la fourche que ce banc dit empecher.
    assert "base.version = derniere.version;" in corps
    # Et l'adoption Meshy, qui CREE un job sur disque (dossier, copie du GLB,
    # registre), ne se laisse pas resumer par « ecrit : rien » au moment meme
    # ou rendreChrono() fait apparaitre ce job dans la chronologie.
    assert "adopte = true;" in corps and "adoption faite" in corps
    assert "abandonné" in corps                            # et ce qui ne l'est pas
    assert "direRefus(" in corps                           # le refus se DIT
    assert "if (ecrites.length) S.enAttente.length = 0;" in corps
    # le refus est ecrit APRES le rechargement : _ouvrirPrincipale() reecrit
    # #barreGeo, et un message pose avant lui disparaitrait sans etre lu.
    # (On vise le refus de SORTIE, pas la garde « aucun modele charge » qui
    # ouvre la fonction — d'ou le prefixe litteral.)
    assert corps.index("await ouvrirPrincipale(") < corps.index("direRefus(`écrit :")


def test_le_client_ne_normalise_jamais_le_quaternion():
    """`mesh_edit.transformer` refuse un quaternion non normé en 400, et sa
    docstring dit pourquoi : « Normaliser un quaternion en douce masquerait un
    bug amont ; le refuser le montre. » Le client ne doit donc pas le faire
    non plus — il masquerait le même bug d'un cran plus haut. Le refus, lui,
    remonte dans la barre du bas par le `catch` gardé ci-dessus.
    """
    js = _lire("etabli/etabli.js")
    assert ".normalize()" not in js


def test_aucun_refus_ne_passe_par_alert():
    """`alert()` n'est pas le geste du dépôt : il bloque la page, il ne
    ressemble à rien de ce que l'Établi affiche, et la page a DÉJÀ une façon
    de refuser en le disant — la barre du bas, où `_ouvrirPrincipale()` écrit
    ses échecs de chargement avec la classe `erreur`.
    """
    js = _lire("etabli/etabli.js")
    assert "alert(" not in js
    assert "function direRefus(" in js
    corps = js.split("function separerSelection", 1)[1].split("\n}\n", 1)[0]
    assert "direRefus(" in corps


def test_un_index_deduit_d_un_NOM_se_dit_avant_d_ecrire():
    """selection.js pose `userData.indexGltfSource` : « associations », la
    carte du GLTFParser, ou « nom », une heuristique que son propre
    commentaire décrit comme faillible en trois cas. Ces index partent au
    serveur, QUI ÉCRIT UN GLB — un index faux écrit sur le mauvais maillage
    sans que rien ne grince. C'est la seule occasion où ce marqueur peut
    servir ; s'il ne sert pas ici, il ne servira jamais. La page ne refuse
    pas (le repli vaut mieux que rien), elle le DIT dans la barre.
    """
    js, css = _lire("etabli/etabli.js"), _lire("etabli/etabli.css")
    assert 'indexGltfSource !== "associations"' in js
    # LE CALCUL du drapeau, et pas seulement sa lecture. Mesure : `const doute
    # = false;` dans noterAttente fait disparaitre l'avertissement « index de
    # nœud deduits d'un NOM » en gardant tout vert — et c'est un avertissement
    # qui PRECEDE une ecriture disque.
    note = js.split("function noterAttente", 1)[1].split("\n}\n", 1)[0]
    assert 'source !== undefined && source !== "associations"' in note
    corps = js.split("function rendreAttente", 1)[1].split("\n}\n", 1)[0]
    # La LECTURE du drapeau, et non le mot : `"heuristique" in corps` restait
    # VERT quand la condition devenait `false`, le message d'avertissement
    # contenant lui-meme « repli heuristique ». Verifie par mutation.
    assert "S.enAttente.some((t) => t.heuristique)" in corps
    assert "attente-doute" in corps
    # sans la regle CSS, l'avertissement est ECRIT et se lit comme le reste
    assert ".attente-doute" in css


def test_la_porte_refuse_l_etape_decimee_qui_n_a_pas_de_version():
    """`mesh_sources` donne `version: null` à l'étape « décimée », qui est un
    FICHIER À PART (`model.opt.glb`). Or la route retombe sur la version 1
    quand le corps n'en porte pas : écrire depuis cette étape partirait du
    BROUILLON, qui n'a ni la même géométrie ni les mêmes index que ce qui est
    à l'écran — un GLB faux, sur disque, en silence. `ficheDe()` refuse déjà
    cette étape pour exactement la même raison.
    """
    js = _lire("etabli/etabli.js")
    corps = js.split("async function ecrireVersion", 1)[1].split("\n}\n", 1)[0]
    assert "if (!S.a.version) {" in corps
    assert "décimée" in corps


def test_la_barre_d_attente_est_redessinee_quand_le_modele_change():
    """`_ouvrirPrincipale()` vide `S.enAttente` — mais vider le tableau ne
    redessine pas la barre : elle continuerait d'annoncer « 2 modifications en
    attente » et d'offrir un bouton « écrire la version » pour une file vide.
    La barre AFFIRME quelque chose ; elle doit donc être refaite là même où la
    file est vidée, et avant tout chargement.
    """
    js = _lire("etabli/etabli.js")
    i = js.index("S.enAttente.length = 0;")
    assert js.index("rendreAttente();", i) < js.index("await charger(S.vueA")


def test_le_bouton_Separer_est_rendu_par_le_gabarit_comme_ses_voisins():
    """Le bouton fut d'abord greffé au panneau depuis une fonction à part. Il
    ne s'empilait pas — mais seulement parce qu'on l'appelait APRÈS le
    `box.innerHTML` qui repart d'une page blanche : une sûreté qui tenait à un
    ordre d'appel, donc un danger qu'il fallait garder. Rendu par le gabarit
    comme `#btnIsoler` et `#btnToutVoir`, et branché à côté d'eux, ce danger
    n'existe plus — on le RETIRE au lieu de le garder.

    LES DEUX ASSERTIONS SUFFISENT, et ce banc ne va délibérément pas plus
    loin. Il a un temps interdit `createElement` et `appendChild` dans tout le
    fichier : une garde qui visait à faux, le danger n'ayant jamais été la
    primitive mais une mutation du panneau HORS du rendu unique — un
    `insertAdjacentHTML` serait passé sans être moins dangereux. Elle poussait
    de surcroît le code à venir vers `innerHTML`, c'est-à-dire vers la
    primitive qui exige `esc()` partout, quand `createElement` + `textContent`
    est le chemin sûr ; et elle était unique au dépôt — studio3d.js, la page
    sœur dont l'Établi se réclame, en compte huit, materialforge.js
    trente et un.
    """
    js = _lire("etabli/etabli.js")
    corps = js.split("function rendreParties", 1)[1].split("\n}\n", 1)[0]
    assert '<button id="btnSeparer">' in corps
    assert '$("#btnSeparer").addEventListener("click", separerSelection);' in corps


def test_le_bloc_reparer_met_en_attente_au_lieu_d_ecrire():
    """Le panneau Fiche règle l'assise — axe haut, échelle, recentrage — et
    n'écrit RIEN : il pose une ligne dans la file, comme le gizmo et comme
    « Séparer ». La porte reste le seul chemin vers le disque.
    """
    js = _lire("etabli/etabli.js")
    corps = js.split("function rendreFiche", 1)[1].split("\n}\n", 1)[0]
    assert '$("#panFiche")' in corps
    assert 'noterAttente("reparer"' in corps
    assert "jpost(" not in corps                      # ce panneau n'ecrit pas
    assert "rendreFiche();" in js                     # et il est APPELE
    # Les trois reglages de mesh_edit.reparer, aux noms que la route attend —
    # et on epingle les LIGNES, pas les mots : le commentaire du corps nomme
    # les trois cles, si bien qu'un `"axe_haut" in corps` restait VERT sur un
    # `axeHaut:` qui serait passe en 200 sans rien corriger. Par mutation.
    assert 'axe_haut: $("#fAxe").value,' in corps
    assert 'echelle: Number($("#fEchelle").value) || 1,' in corps
    assert 'recentrer: $("#fRecentrer").checked,' in corps


def test_les_onglets_du_rail_droit_se_changent_vraiment():
    """Les quatre boutons portent `data-onglet` depuis la tâche 2 et PERSONNE
    ne les écoutait : #panFiche naît `hidden` dans index.html et le restait.
    Le bloc « Réparer l'assise » y aurait donc été écrit et rendu
    INATTEIGNABLE — le pire des échecs, silencieux, et sur la moitié de cette
    tâche. Les panneaux Rig et Export restent des coquilles qui annoncent P4
    et P5 ; encore faut-il pouvoir les lire.
    """
    js, html = _lire("etabli/etabli.js"), _lire("etabli/index.html")
    assert 'data-onglet="fiche"' in html
    assert 'classList.toggle("hidden", cle !== b.dataset.onglet)' in js
    assert '"#panFiche"' in js and '"#panExport"' in js
# ── J. le retour au 3D Studio ────────────────────────────────────────────────

def test_l_etabli_ramene_au_3D_studio_et_le_bouton_est_a_gauche():
    """L'Établi remplace le graphe DANS l'iframe du hub (voir section F, banc
    retourné) : sans porte de sortie, le sous-onglet « 3D Studio » resterait
    coincé sur l'Établi jusqu'au prochain rechargement du hub. Le bouton EST
    la moitié de la demande de l'utilisateur, pas un ornement.

    Il vit à GAUCHE, avant le titre : c'est là qu'on cherche la sortie d'un
    écran, et `.head-right` porte les contrôles de la VUE (« A/B ✕ »), pas la
    navigation. Mélanger les deux ferait d'un bouton qui quitte la page le
    voisin immédiat d'un bouton qui ferme un panneau.

    Le style n'est pas réinventé : les deux boutons de l'en-tête partagent UNE
    règle. Et le partage passe par une CLASSE, jamais par un `id` : `#btnRetour`
    dans ce sélecteur pèserait 1-0-0 quand `.head-right button` pèse 0-1-1, si
    bien qu'une surcharge de thème écrite en classes gagnerait contre
    #btnCompare et perdrait contre #btnRetour — le partage se déferait en
    silence, ce que ce banc est là pour empêcher.
    """
    html = _lire("etabli/index.html")
    js, css = _lire("etabli/etabli.js"), _lire("etabli/etabli.css")
    assert 'id="btnRetour"' in html
    assert "← 3D Studio" in html
    # la PLACE, et non seulement la présence : dans `.head-right` le bouton
    # serait vert ici sans cette comparaison, et lu comme un contrôle de vue.
    assert html.index('id="btnRetour"') < html.index('class="head-title"')
    assert '$("#btnRetour").addEventListener("click"' in js
    # TOUS les boutons de l'en-tête portent la classe : c'est elle, et rien
    # d'autre, qui les rend identiques. Un seul ne la portant pas, le partage
    # serait un mot.
    #
    # COMPTE MONTÉ DE 2 À 3, DÉLIBÉRÉMENT (tâche « la plaque ») : la bascule
    # « Assemblé / Sur la plaque » est le troisième bouton du bandeau. Et
    # l'invariant cesse d'être un nombre à retoucher à chaque tâche — la
    # ligne suivante le rend AUTO-PORTANT : on compare le nombre de boutons
    # DE L'EN-TÊTE à ceux qui portent la classe. Un quatrième bouton posé
    # sans elle rougira sans qu'il faille avoir pensé à monter le compte.
    assert html.count('class="head-btn"') == 3
    entete = html.split('<header class="head">', 1)[1].split("</header>", 1)[0]
    entete = re.sub(r"<!--.*?-->", "", entete, flags=re.S)
    assert entete.count("<button") == entete.count('class="head-btn"')
    # LES DEUX sélecteurs partagés — base et survol. Sans le second, le bouton
    # est le seul de l'en-tête qui ne réagit pas au passage du curseur.
    assert ".head-right button, .head-btn {" in css
    assert ".head-right button:hover, .head-btn:hover" in css
    # AUCUN `id` dans les RÈGLES : c'est l'assertion qui tient la spécificité.
    # Elle serait verte si l'on ajoutait `#btnRetour` À CÔTÉ de la classe —
    # d'où la forme négative. Sur le code seul : le commentaire de la feuille
    # nomme `#btnRetour` pour dire pourquoi il n'y sert pas (voir _code).
    assert "#btnRetour" not in _code("etabli/etabli.css")


def test_le_retour_refuse_de_perdre_les_modifications_en_attente():
    """`S.enAttente` porte des corrections qui ne sont PAS sur le disque —
    c'est toute la doctrine de cette page : le bouton met en attente, la porte
    d'écriture écrit. Partir sur une file pleine les perdrait EN SILENCE, le
    mode d'échec que ce fichier traque partout ailleurs.

    REFUS et non `confirm()`, par la règle de RÉVERSIBILITÉ : on demande quand
    le coût est inévitable, on refuse quand le remède est à un clic. C'est la
    même règle qui fait DEMANDER le 3D Studio avant de venir ici — là-bas une
    série Meshy en vol meurt quoi qu'on fasse. Ici « écrire la version » et
    « annuler » sont deux boutons de la barre du bas, frères du
    `<footer class="barre">` où le refus s'écrit, et « annuler » vide la file
    en un clic : offrir « pars quand même et perds tout » serait offrir
    STRICTEMENT PIRE que ce qui est déjà sous les yeux. Que la doctrine
    anti-`alert` de la page (test_aucun_refus_ne_passe_par_alert) aille dans le
    même sens est une confirmation, pas l'argument — elle justifierait aussi
    bien un modal maison, et n'expliquerait pas le droit du studio à demander.

    Et le refus ne DÉSIGNE JAMAIS un bouton grisé : pendant une série
    d'écritures, `#btnEcrire` est `disabled` alors que la file n'est pas encore
    vidée. Un refus qui montre du doigt un bouton mort est un refus qui ment.

    Enfin la navigation est une adresse ABSOLUE et rien d'autre : /etabli/
    s'ouvre aussi en direct, et un `window.top` ou un `window.parent` ne
    marcherait qu'embarqué — ou casserait la page autonome.
    """
    js = _lire("etabli/etabli.js")
    depart = js.split('$("#btnRetour").addEventListener', 1)[1]
    corps = depart.split("\n});\n", 1)[0]
    assert "if (S.enAttente.length) {" in corps
    assert 'location.href = "/studio3d/";' in corps
    # le message se PLIE au verrou d'écriture. Sans la lecture de
    # `_ecritEnCours`, il envoie vers « écrire la version » pendant que ce
    # bouton est `disabled` — la seule fenêtre où son conseil est inapplicable.
    assert "direRefus(_ecritEnCours" in corps
    assert "en cours d'écriture" in corps
    # L'ORDRE est toute l'assertion : un direRefus() posé APRÈS la navigation
    # écrirait un message dans une page qui part déjà, et la file serait
    # perdue quand même. Le `return;` doit précéder lui aussi.
    assert corps.index("direRefus(") < corps.index("location.href")
    assert corps.index("return;") < corps.index("location.href")
    # la doctrine de refus de la page, pinglée là où elle se joue
    assert "confirm(" not in corps
    # embarqué ET autonome : une seule adresse, aucune supposition de parent
    assert "window.top" not in corps and "window.parent" not in corps
    # `?job=` ne repart PAS : le studio a son propre état, et une chaîne de
    # requête qu'il ne lit pas serait une URL qui promet sans tenir.
    assert "job=" not in corps


def test_le_retour_n_est_branche_qu_une_seule_fois():
    """Ce fichier a DÉJÀ empilé un écouteur par modèle en le posant dans
    `etabli:charge`, émis à chaque chargement réussi (voir `_clicBranche`). Le
    branchement du retour vit donc au PREMIER NIVEAU du module, qui ne
    s'exécute qu'à l'import : posé dans l'écouteur, trois GLB chargés
    feraient trois navigations pour un clic.
    """
    js = _lire("etabli/etabli.js")
    assert js.count('$("#btnRetour").addEventListener') == 1
    # AU PREMIER NIVEAU : la ligne commence en colonne 0. Indentée, elle
    # serait dans un `function` ou dans l'écouteur `etabli:charge` — et le
    # simple `count == 1` ci-dessus resterait vert.
    assert '\n$("#btnRetour").addEventListener' in js
def test_le_studio_garde_sa_configuration_entre_deux_visites_a_l_etabli():
    """L'aller-retour 3D Studio → 07 → « ← 3D Studio » est le geste NORMAL, et
    il rechargeait /studio3d aux valeurs d'usine : `S.cfg` ne vit qu'en
    mémoire, le boot ne relit que status/health/balance/tasks, et la page ne
    lit pas `location.search`. Le prompt tapé, le nom de l'asset, l'image
    choisie dans la Library, le modèle, le polycount, la liste d'animations,
    les formats d'export — tout repartait à zéro. Sous l'ancienne décision
    (onglet séparé) la page survivait et tout tenait : c'est le retournement
    qui a introduit la perte, c'est donc ici qu'elle se répare.

    `sessionStorage` et non `localStorage` : la portée est l'ONGLET, ce qui
    couvre exactement un aller-retour sans rien imposer à une session future —
    la portée même retenue par
    docs/superpowers/specs/2026-08-06-preservation-etat-ecrans-design.md
    (« En session uniquement »). Cette spec vise les écrans REACT du bundle et
    les garde en variables de module (`__dzKeep`, scripts/patch_bundle_
    keepstate.py) : cela survit à un démontage de composant, jamais à une
    navigation de page. /studio3d est une page autonome — autre outil, même
    portée, aucune contradiction.

    ET SEULEMENT `S.cfg`. Ressusciter `S.run` ou `S.pipeline` d'une session
    morte peindrait une progression qui ne progresse plus et des crédits qui ne
    se consomment plus : un mensonge d'interface, sur ce qui coûte.
    """
    js = _lire("studio3d/studio3d.js")
    # la PORTÉE : l'onglet, pas la machine. `localStorage` imposerait la config
    # d'aujourd'hui à toutes les sessions futures ; le fichier n'en avait aucun.
    # Sur le code seul : le commentaire cite `localStorage` pour l'écarter.
    assert "sessionStorage" in js
    assert "localStorage" not in _code("studio3d/studio3d.js")
    # ce qu'on écrit, et RIEN d'autre : la charge est `S.cfg`, nommée.
    assert "sessionStorage.setItem(CLE_CFG, JSON.stringify(S.cfg))" in js
    for vivant in ("S.run", "S.pipeline", "S.persisted", "S.balance"):
        assert f"JSON.stringify({vivant})" not in js
    # ÉCRIT AVANT DE PARTIR, et l'ordre est toute l'assertion : après le
    # `location.href`, l'appel serait du code mort dans une page qui part.
    corps = js.split("function ouvrirEtabli", 1)[1].split("\n}\n", 1)[0]
    assert "memoriserCfg();" in corps
    assert corps.index("memoriserCfg();") < corps.index("location.href")
    # le filet des départs qui ne passent pas par là (rechargement, fermeture)
    assert 'window.addEventListener("pagehide", memoriserCfg);' in js
    # RELU AU BOOT, et avant le premier rendu : après, la page clignoterait du
    # défaut vers la config retrouvée.
    init = js.split("(function init()", 1)[1]
    assert init.index("rehydraterCfg();") < init.index("render();")


def test_la_relecture_de_la_configuration_ne_peut_pas_casser_la_page():
    """Un JSON illisible, une clé absente, une forme changée depuis : rien ne
    doit empêcher /studio3d de démarrer, et rien ne doit faire disparaître un
    champ que le défaut connaît.

    La FUSION sur le défaut est le cœur : un remplacement en bloc
    (`S.cfg = lu`) rendrait `undefined` tout champ ajouté au défaut après
    l'écriture d'un vieux JSON — et tout ce qui le lit casserait, longtemps
    après, sans rapport visible avec la cause. Le défaut fait la liste des
    clés ; le stockage ne fournit que des valeurs.
    """
    js = _lire("studio3d/studio3d.js")
    corps = js.split("function rehydraterCfg", 1)[1].split("\n}\n", 1)[0]
    # un JSON casse ne doit pas remonter : le parse est garde, et la sortie
    # rend la main au defaut au lieu de laisser `S.cfg` a moitie ecrase.
    assert "JSON.parse(sessionStorage.getItem(CLE_CFG)" in corps
    assert "catch { return; }" in corps
    # LA FUSION, et non le remplacement. `S.cfg = lu` serait vert sur un simple
    # `"CFG_DEFAUT" in corps` — le defaut etant deja cite par le commentaire.
    assert "for (const cle of Object.keys(CFG_DEFAUT))" in corps
    assert "if (lu[cle] === undefined) continue;" in corps
    assert "S.cfg = lu" not in corps
    # LE CONTRÔLE DE FORME, étroit et suffisant : `animationActions` et
    # `exportFormats` sont parcourus sans détour (.map, .join, .includes) par
    # estimate() et paramsOf(), appelés dès le premier render() — une chaîne à
    # leur place et la page ne peint plus rien. Un `typeof` général serait
    # FAUX : `imageUrl` vaut `null` par défaut et une URL est une chaîne, si
    # bien qu'il rejetterait la valeur même qu'on cherche à retrouver.
    assert ("if (Array.isArray(lu[cle]) !== Array.isArray(CFG_DEFAUT[cle]))"
            " continue;") in corps
    # l'ECRITURE aussi est gardee : `sessionStorage` leve en navigation privee
    # ou sur quota plein, et un clic sur 07 qui n'aboutit pas serait un bogue.
    ecrit = js.split("function memoriserCfg", 1)[1].split("\n}\n", 1)[0]
    assert "try {" in ecrit and "} catch" in ecrit
    # le DEFAUT est un clone PROFOND : `{ ...S.cfg }` partagerait le tableau
    # `animationActions`, et le premier geste de l'editeur souillerait le repli.
    assert "const CFG_DEFAUT = JSON.parse(JSON.stringify(S.cfg));" in js
    # la spec de preservation d'etat est CITEE : la prochaine main doit savoir
    # qu'elle existe, qu'elle vise le bundle, et pourquoi elle ne sert pas ici.
    # (Assertion de PROSE, assumee comme telle : elle tient la citation, pas le
    # mecanisme — celui-ci est tenu par les assertions ci-dessus.)
    assert "2026-08-06-preservation-etat-ecrans-design.md" in js


# ── K. la catégorie « Établi » de la Bibliothèque ────────────────────────────
# « Il convient aussi de rajouter les dossiers générés dans une catégorie
# spécifique de la librairie pour pouvoir facilement la retrouver. » La MOITIÉ
# SERVEUR de cette demande : une route qui dit ce que l'Établi a produit.
# L'onglet côté bundle est une autre tâche — rien ici ne le touche.


def _glb_de_banc() -> bytes:
    """Un GLB RÉEL, pas des octets quelconques.

    `mesh_edit.ecrire_version` passe par `mesh_report.write_report`, qui en
    tire silhouettes et géométrie : c'est cette fiche-là que la route relit.
    Un faux GLB ferait écrire une fiche dégradée et le banc ne verrait jamais
    la vignette de silhouette (le cas `prod_vign_rien` ci-dessous s'en sert
    justement, mais délibérément).
    """
    from app.services import gltf_builder
    return gltf_builder.build_glb({}, None, "cube", "banc")


def _glb_plus_lourd() -> bytes:
    """Le même cube PLUS un quad de sol : 14 triangles au lieu de 12.

    Deux maillages qu'on peut distinguer par le COMPTE, sans lire un octet —
    c'est ce qui permet de dire quelle version l'impression 3D a réellement
    servie.
    """
    import io
    from PIL import Image
    from app.services import gltf_builder
    tampon = io.BytesIO()
    Image.new("RGBA", (1, 1)).save(tampon, "PNG")
    return gltf_builder.build_glb({}, None, "cube", "banc",
                                  stage_png=tampon.getvalue())


def _job(nom: str):
    """Un job `assets3d` avec son brouillon — comme en sortie de moteur."""
    from app.config import settings
    d = settings.outputs_path / "assets3d" / nom
    d.mkdir(parents=True, exist_ok=True)
    (d / "model.glb").write_bytes(_glb_de_banc())
    return d


def _items():
    r = _client().get("/api/etabli/productions")
    assert r.status_code == 200
    return r.json()["items"]


def test_la_route_ne_rend_que_les_maillages_ecrits_par_l_etabli():
    """Le marqueur est `source.outil == "etabli"` dans le registre du job —
    `mesh_edit.ecrire_version` le pose, personne d'autre.

    Le brouillon `model.glb` d'un job vient du MOTEUR (Tripo, Meshy, Rodin) :
    ce n'est pas une production de l'Établi, et il doit rester dehors même
    quand le job en contient une. Un filtre relâché — « tout job qui a une
    fiche » — rendrait les deux, et la catégorie ne voudrait plus rien dire.
    """
    from app.services import mesh_edit
    _job("prod_libre")                    # brouillon seul : jamais touché
    _job("prod_atelier")
    mesh_edit.ecrire_version("prod_atelier", _glb_de_banc(),
                             operation="reparer", detail={"axe_haut": "Z"})

    cles = {(e["job"], e["version"]) for e in _items()}
    assert ("prod_atelier", 2) in cles
    assert ("prod_atelier", 1) not in cles     # le brouillon du moteur
    assert not [c for c in cles if c[0] == "prod_libre"]

    e = [x for x in _items() if x["job"] == "prod_atelier"][0]
    assert e["operation"] == "reparer"
    assert e["origine"] == "version"
    assert e["fichier"] == "model.v2.glb"


def test_une_tache_meshy_adoptee_est_une_production_comptee_UNE_fois():
    """`adopter_meshy` pose DEUX marqueurs sur le même maillage : un
    `asset.json` `stage == "adopte"` ET une fiche `outil == "etabli"`,
    `operation == "adoption"`. Les deux sont nécessaires — l'adoption garde
    ses trois écritures SÉPARÉES, si bien qu'une adoption interrompue laisse
    l'un sans l'autre. Les additionner sortirait la même v1 deux fois.
    """
    from app.config import settings
    from app.services import mesh_edit
    tid = "tache_adoptee_0123456789"
    src = settings.outputs_path / "meshy3d" / tid
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_glb_de_banc())
    job = mesh_edit.adopter_meshy(tid)

    miennes = [e for e in _items() if e["job"] == job]
    assert len(miennes) == 1
    assert miennes[0]["version"] == 1
    assert miennes[0]["origine"] == "adoption"


def test_l_url_porte_le_nom_de_dossier_ENTIER_et_sert_vraiment_les_octets():
    """LE PIÈGE DE CETTE TÂCHE. La carte 3D du bundle fabrique ses URL avec
    `job_id.slice(0, 8)`, parce qu'un job `assets3d` normal a pour dossier les
    8 premiers caractères de son UUID (POST /api/assets/3d : `short =
    job_id[:8]`). Un job ADOPTÉ, lui, s'appelle `meshy_<task_id>` : le couper
    à huit donnerait `meshy_t`, et les routes `/api/assets/3d/{job}/…`
    prennent le segment LITTÉRALEMENT (`Path(job).name`, aucune résolution de
    préfixe). La vignette et le téléchargement seraient morts.

    La route rend donc des URL DÉJÀ FAITES, portant le nom de dossier entier,
    et `short` vaut ce même nom — c'est lui que réclame « Envoyer vers →
    Impression 3D » (`__dzPrint3d(m.short)` → /api/print3d/from-assets3d/<sh>).
    """
    from app.config import settings
    from app.services import mesh_edit
    tid = "tache_url_9876543210"
    src = settings.outputs_path / "meshy3d" / tid
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_glb_de_banc())
    job = mesh_edit.adopter_meshy(tid)
    assert len(job) > 8                       # sinon le banc ne prouve rien

    c = _client()
    e = [x for x in c.get("/api/etabli/productions").json()["items"]
         if x["job"] == job][0]
    assert e["url"] == f"/api/assets/3d/{job}/version/1"
    assert e["short"] == job
    assert e["short"] != job[:8]
    # et l'URL n'est pas qu'une chaîne bien formée : elle SERT le maillage
    r = c.get(e["url"])
    assert r.status_code == 200
    assert r.content == _glb_de_banc()


def test_l_etape_decimee_n_est_pas_une_production():
    """`model.opt.glb` sort de l'optimiseur (chantier 10a), porte
    `version: None` dans la chronologie, et n'a jamais été écrit par
    l'Établi. Le ranger ici ferait proposer un maillage décimé comme
    « dossier généré par l'Établi ».

    CE QUI L'EXCLUT, c'est l'absence de fiche `outil == "etabli"` : ce banc
    rougit quand ce filtre saute (il rend alors [1, 2], et le décimé fait
    lever `int(None)`). Le `if v is None: continue` de la route est une garde
    de SÛRETÉ par-dessus — le retirer seul ne change rien d'observable
    aujourd'hui, et c'est dit ici plutôt que présenté comme mesuré.
    """
    from app.services import mesh_edit
    d = _job("prod_opt")
    mesh_edit.ecrire_version("prod_opt", _glb_de_banc(),
                             operation="transformer", detail={})
    (d / "model.opt.glb").write_bytes(_glb_de_banc())

    miennes = [e for e in _items() if e["job"] == "prod_opt"]
    assert [e["version"] for e in miennes] == [2]
    assert all(e["fichier"] != "model.opt.glb" for e in miennes)


def test_une_fiche_egaree_sur_le_decime_ne_fait_pas_tomber_le_job():
    """LA GARDE `v is None`, et ce qu'elle coûte le jour où elle saute.

    `model.opt.glb` porte `version: None` dans la chronologie. Qu'une fiche
    `outil == "etabli"` atterrisse dessus, et `_etabli_entree` calcule
    `int(None)` pour la vignette : la lecture du job LÈVE, le filet
    rattrape, et le job ENTIER quitte la catégorie — sa v2 légitime
    comprise. Le décimé ne serait pas seulement mal rangé : il emporterait
    la production qu'on cherchait.

    Aucun appelant ne pose cette fiche aujourd'hui ; c'est une garde, et ce
    banc la tient plutôt que de la laisser à son commentaire. Sans elle,
    `miennes` sort vide au lieu de `[2]` — mesuré.
    """
    from app.services import mesh_edit, mesh_report
    d = _job("prod_opt_fiche")
    mesh_edit.ecrire_version("prod_opt_fiche", _glb_de_banc(),
                             operation="reparer", detail={})
    (d / "model.opt.glb").write_bytes(_glb_de_banc())
    # le VRAI écrivain de fiches, avec le marqueur de l'Établi
    mesh_report.write_report("prod_opt_fiche", "model.opt.glb", version=3,
                             avec_silhouettes=False,
                             extra={"outil": "etabli", "operation": "banc"})

    miennes = [e for e in _items() if e["job"] == "prod_opt_fiche"]
    assert [e["version"] for e in miennes] == [2]


def test_un_report_illisible_est_DIT_sans_faire_disparaitre_le_job():
    """`mesh_sources._versions_du_job` fait déjà
    `except (FileNotFoundError, ValueError): pass` : un registre illisible y
    vaut SANS FICHE, et le job reste listable. La route s'aligne, et c'est
    le contraire de ce qu'elle faisait d'abord.

    Ce que corrigeait cet alignement était visible et déroutant : le job
    s'affichait dans la chronologie et dans `/etabli/sources`, et
    disparaissait du seul onglet « Établi » — alors que son `asset.json`
    intact disait encore, à lui seul, que l'Établi l'avait adopté. Deux
    pannes qui disent la même chose ; une seule était rattrapée.

    La fixture est une ADOPTION, et c'est ce qui rend l'assertion mordante :
    sans ce rattrapage l'entrée disparaît. Le job est nommé dans les logs —
    un fichier illisible ne s'avale pas en silence pour autant.
    """
    from loguru import logger
    from app.config import settings
    from app.services import mesh_edit
    tid = "tache_cassee_5555555555"
    src = settings.outputs_path / "meshy3d" / tid
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_glb_de_banc())
    casse = mesh_edit.adopter_meshy(tid)
    d = settings.outputs_path / "assets3d" / casse
    assert (d / "asset.json").is_file()          # le marqueur d'adoption EST là
    (d / "report.json").write_text("{ ceci n'est pas du JSON", encoding="utf-8")

    dits = []
    sid = logger.add(dits.append, level="WARNING")
    try:
        miennes = [e for e in _items() if e["job"] == casse]
    finally:
        logger.remove(sid)

    assert len(miennes) == 1
    assert miennes[0]["origine"] == "adoption"
    assert any(casse in str(m) for m in dits)


def test_un_job_sans_fiche_ne_fait_AUCUN_bruit():
    """Le cas COURANT, et il ne doit pas crier. Un job de moteur n'a pas de
    `report.json` tant que personne n'a demandé sa fiche : traiter cette
    absence comme de la casse ferait remonter un WARNING par job sans fiche,
    À CHAQUE REQUÊTE de la Bibliothèque. `FileNotFoundError` est donc
    attrapée à part de tout le reste.
    """
    from loguru import logger
    from app.config import settings
    _job("prod_muet")
    assert not (settings.outputs_path / "assets3d" / "prod_muet"
                / "report.json").exists()

    dits = []
    sid = logger.add(dits.append, level="WARNING")
    try:
        _items()
    finally:
        logger.remove(sid)
    assert not [m for m in dits if "prod_muet" in str(m)], dits


def test_le_repechage_par_asset_json_rattrape_une_fiche_sans_source():
    """LA BRANCHE QUE RIEN N'ATTEIGNAIT. `adopter_meshy` écrit les DEUX
    marqueurs, donc le chemin par fiche gagne toujours et le repêchage par
    `asset.json` restait du code que l'on pouvait supprimer en entier sans
    faire rougir un seul banc — mesuré.

    Ses trois écritures sont pourtant gardées séparées EXPRÈS : une adoption
    interrompue, ou un registre réécrit sans son `source`, laisse le
    `asset.json` seul à savoir. C'est cet état-là qu'on reconstitue ici, en
    retirant `source` de la fiche v1 qu'a écrite le vrai producteur.
    """
    import json as _json
    from app.config import settings
    from app.services import mesh_edit
    tid = "tache_repechee_7777777777"
    src = settings.outputs_path / "meshy3d" / tid
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_glb_de_banc())
    job = mesh_edit.adopter_meshy(tid)

    d = settings.outputs_path / "assets3d" / job
    reg = _json.loads((d / "report.json").read_text(encoding="utf-8"))
    for e in reg["entries"]:
        e.pop("source", None)            # la fiche ne dit plus « etabli »
    (d / "report.json").write_text(_json.dumps(reg), encoding="utf-8")

    miennes = [e for e in _items() if e["job"] == job]
    assert len(miennes) == 1
    assert miennes[0]["origine"] == "adoption"
    assert miennes[0]["version"] == 1


def test_un_registre_d_un_AUTRE_TYPE_perd_ce_job_seul_et_le_DIT():
    """`read_registry` rend ce que `json.loads` trouve : un `report.json`
    contenant `[1, 2, 3]` est du JSON VALIDE, il ne déclenche donc aucune
    `ValueError` — le `.get("entries")` qui suit part en `AttributeError`,
    d'un TYPE que rien n'attend. C'est le filet PAR JOB qui le rattrape : sans
    lui, la route entière rend 500 pour UN dossier abîmé.

    ASYMÉTRIE ASSUMÉE avec le banc précédent : des octets tronqués sont une
    écriture à moitié faite et valent « sans fiche » ; un registre d'un autre
    type dit que ce dossier n'est plus ce qu'on croit, et il est perdu. La
    fixture est une adoption, donc son absence mord : sans le filet, son
    `asset.json` la ferait sortir quand même.
    """
    from loguru import logger
    from app.config import settings
    from app.services import mesh_edit
    _job("prod_liste_sain")
    mesh_edit.ecrire_version("prod_liste_sain", _glb_de_banc(),
                             operation="reparer", detail={})
    tid = "tache_liste_4444444444"
    src = settings.outputs_path / "meshy3d" / tid
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_glb_de_banc())
    liste = mesh_edit.adopter_meshy(tid)
    d = settings.outputs_path / "assets3d" / liste
    (d / "report.json").write_text("[1, 2, 3]", encoding="utf-8")

    # `_items()` exige un 200 ET du JSON : sans le filet par job, la route
    # entière rend 500 et toutes ces lignes tombent ensemble.
    dits = []
    sid = logger.add(dits.append, level="WARNING")
    try:
        jobs = {e["job"] for e in _items()}
    finally:
        logger.remove(sid)
    assert "prod_liste_sain" in jobs
    assert liste not in jobs
    assert any(liste in str(m) for m in dits)


def test_la_vignette_montre_le_RENDU_du_moteur_avant_le_MASQUE_de_controle():
    """BANC RETOURNÉ. Il épinglait l'ordre INVERSE — silhouette d'abord — et
    c'est cette préférence-là qui a produit le défaut rapporté : « les
    nouvelles versions apparaissent bien dans la librairie, mais les
    illustrations ne se montrent pas ». Six vignettes sur huit étaient des
    rectangles blancs.

    Le raisonnement d'origine se tenait : la silhouette est celle de la
    VERSION demandée, tandis que le rendu ne montre que le brouillon. La
    MESURE le dément. `sil_v<n>/silhouette_face.png` n'illustre rien : c'est
    un MASQUE de contrôle, écrit par `mesh_report.silhouettes()` pour la
    comparaison de silhouette du QC — une forme blanche pleine sur fond
    noir. Sur le job réel de l'utilisateur, `sil_v5/silhouette_face.png`
    compte 60 % de pixels CLAIRS quand son `preview.png` en compte 0 %. La
    vignette s'affichait parfaitement ; elle ne montrait simplement pas
    l'objet.

    L'ordre est donc RETOURNÉ : `preview.png` → `shot_0.png` → silhouette →
    `None`. Le rendu du moteur date du premier tir, il montre la version 1
    et non la version listée — prix assumé, acceptable parce que la carte
    DIT le numéro en toutes lettres, « 6e0a8a5f · v5 · transformer », ce que
    la dernière assertion mesure. La silhouette n'est plus un choix mais un
    PIS-ALLER : quand elle sort, elle est la seule image du dossier.

    Une URL morte donnerait une case grise sans erreur nulle part : les
    quatre vignettes non nulles sont donc TIRÉES, pas seulement comparées.
    """
    from PIL import Image
    from app.services import mesh_edit

    def _png(p):
        Image.new("RGB", (1, 1)).save(p)

    # les TROIS images à la fois : seule fixture où l'ordre ENTIER se mesure
    d0 = _job("prod_vign_tout")
    _png(d0 / "preview.png")
    _png(d0 / "shot_0.png")
    mesh_edit.ecrire_version("prod_vign_tout", _glb_de_banc(),
                             operation="reparer", detail={})
    # sans `preview.png` : le shot du moteur passe AVANT le masque
    d1 = _job("prod_vign_shot")
    _png(d1 / "shot_0.png")
    mesh_edit.ecrire_version("prod_vign_shot", _glb_de_banc(),
                             operation="reparer", detail={})
    # ni preview ni shot : la silhouette est la SEULE image du dossier —
    # l'état du job `6e0a8a5f` de l'utilisateur, quatre silhouettes et rien
    # d'autre. Elle sort, faute de mieux.
    _job("prod_vign_sil")
    mesh_edit.ecrire_version("prod_vign_sil", _glb_de_banc(),
                             operation="reparer", detail={})
    # des octets illisibles : la fiche dégrade proprement, donc PAS de
    # silhouette — c'est ainsi qu'on atteint les deux dernières branches
    d3 = _job("prod_vign_prev")
    mesh_edit.ecrire_version("prod_vign_prev", b"ceci n'est pas un GLB",
                             operation="reparer", detail={})
    _png(d3 / "preview.png")
    _job("prod_vign_rien")
    mesh_edit.ecrire_version("prod_vign_rien", b"ceci n'est pas un GLB",
                             operation="reparer", detail={})

    c = _client()
    par_job = {e["job"]: e
               for e in c.get("/api/etabli/productions").json()["items"]}
    assert par_job["prod_vign_tout"]["thumb"] == \
        "/api/assets/3d/prod_vign_tout/preview"
    assert par_job["prod_vign_shot"]["thumb"] == \
        "/api/assets/3d/prod_vign_shot/shot/0"
    assert par_job["prod_vign_sil"]["thumb"] == \
        "/api/assets/3d/prod_vign_sil/silhouette/face?v=2"
    assert par_job["prod_vign_prev"]["thumb"] == \
        "/api/assets/3d/prod_vign_prev/preview"
    assert par_job["prod_vign_rien"]["thumb"] is None
    # et les quatre URL servent VRAIMENT une image
    for j in ("prod_vign_tout", "prod_vign_shot", "prod_vign_sil",
              "prod_vign_prev"):
        assert c.get(par_job[j]["thumb"]).status_code == 200
    # ce qui rend le prix acceptable : à côté d'une image du brouillon, la
    # carte porte le numéro de la version qu'elle liste
    assert "v2" in par_job["prod_vign_tout"]["name"]


def test_les_productions_sortent_de_la_plus_recente_a_la_plus_ancienne():
    """`mesh_sources.lister()` trie par NOM de dossier — un préfixe d'UUID,
    donc sans rapport avec le temps ; sa docstring demande à l'appelant de
    retrier. Ce que la personne cherche, c'est son DERNIER dossier.

    IL EN FAUT TROIS. Avec deux, aucun choix de noms ne mord des deux
    côtés : ranger le neuf en tête alphabétiquement rend le banc vert quand
    on retire le tri ENTIER, et le ranger en queue le rend vert quand on
    retire `created_at` de la clé (il reste alors un tri par nom
    décroissant). Les deux mutations ont été mesurées. Trois dates dans un
    ordre qui ne suit NI le nom croissant NI le nom décroissant ferment les
    deux : attendu `m_neuf, z_moyen, a_vieux` ; par nom croissant on aurait
    `a_vieux, m_neuf, z_moyen`, par nom décroissant `z_moyen, m_neuf,
    a_vieux`.

    Les `created_at` du registre sont à la seconde, si bien que deux
    écritures de banc y tombent ensemble : on VIEILLIT donc des fiches déjà
    écrites par `write_report` — leur forme reste la leur, seule leur date
    bouge.
    """
    import json as _json
    from app.services import mesh_edit

    def _date(nom, quand):
        d = _job(nom)
        mesh_edit.ecrire_version(nom, _glb_de_banc(),
                                 operation="reparer", detail={})
        if quand:
            reg = _json.loads((d / "report.json").read_text(encoding="utf-8"))
            for e in reg["entries"]:
                e["created_at"] = quand
            (d / "report.json").write_text(_json.dumps(reg), encoding="utf-8")

    _date("prod_a_vieux", "2001-01-01T00:00:00+00:00")
    _date("prod_z_moyen", "2010-01-01T00:00:00+00:00")
    _date("prod_m_neuf", None)                       # maintenant

    attendus = ("prod_m_neuf", "prod_z_moyen", "prod_a_vieux")
    sortis = [e["job"] for e in _items() if e["job"] in attendus]
    assert sortis == list(attendus)


def test_une_version_ne_se_donne_pas_pour_imprimable():
    """`kind: "asset3d"` fait apparaître « Envoyer vers → Impression 3D » sur
    toute carte portant un `short`, et ce menu appelle
    `POST /api/print3d/from-assets3d/<short>`. Or cette route lit `model.stl`
    sinon `model.glb` — JAMAIS `model.v<n>.glb` — et n'accepte aucun numéro de
    version : une entrée « v2 · reparer » y ferait imprimer le BROUILLON, en
    silence, et l'utilisateur tiendrait dans la main un objet faux.

    Le banc le MESURE plutôt que de le croire : la v2 pèse 14 triangles, le
    brouillon 12, et l'export d'impression en compte 12. `imprimable` dit donc
    faux sur une version écrite et vrai sur une adoption, dont la v1 EST le
    maillage que la route servirait. Le jour où `print3d_from_assets3d`
    apprendra les versions, c'est ce banc qu'il faudra rouvrir.
    """
    from app.services import mesh_edit
    _job("prod_impr")                                  # model.glb : 12 tris
    mesh_edit.ecrire_version("prod_impr", _glb_plus_lourd(),
                             operation="reparer", detail={})   # v2 : 14 tris

    c = _client()
    e = [x for x in c.get("/api/etabli/productions").json()["items"]
         if x["job"] == "prod_impr"][0]
    assert e["version"] == 2
    assert e["triangles"] == 14
    assert e["imprimable"] is False

    # ce que le menu enverrait vraiment au slicer, mesuré
    r = c.post(f"/api/print3d/from-assets3d/{e['short']}", json={})
    assert r.status_code == 200, r.text
    assert r.json()["triangles"] == 12, "l'impression sert le BROUILLON"

    # une adoption, elle, imprime bien son propre maillage
    from app.config import settings
    tid = "tache_impr_3333333333"
    src = settings.outputs_path / "meshy3d" / tid
    src.mkdir(parents=True, exist_ok=True)
    (src / "model.glb").write_bytes(_glb_de_banc())
    job = mesh_edit.adopter_meshy(tid)
    a = [x for x in c.get("/api/etabli/productions").json()["items"]
         if x["job"] == job][0]
    assert a["imprimable"] is True


def test_la_route_ne_gele_pas_la_boucle_d_evenements():
    """`mesh_sources.lister()` et la relecture des `report.json` sont de l'E/S
    disque SYNCHRONE. Appelées directement depuis une coroutine, elles gèlent
    la boucle pendant tout le parcours des dossiers — donc TOUTES les requêtes
    du serveur, pas seulement celle-ci. La docstring de `lister()` le dit.

    Marqueur STRUCTUREL, sur l'arbre syntaxique : un `"asyncio.to_thread" in
    source` serait satisfait par le commentaire qui explique la règle, et ce
    dépôt a déjà corrigé six bancs pris à ce piège. Ici l'assertion porte sur
    un APPEL réellement présent dans le corps de la route.
    """
    import ast
    import inspect
    from app.api import routes
    arbre = ast.parse(inspect.getsource(routes.etabli_productions))
    # ce qui est CONFIÉ au fil : `asyncio.to_thread` appelée sur autre chose
    # laisserait la lecture de disque sur la boucle
    confie = {ast.unparse(a)
              for n in ast.walk(arbre)
              if isinstance(n, ast.Call)
              and ast.unparse(n.func) == "asyncio.to_thread"
              for a in n.args}
    assert "_etabli_productions" in confie


def test_l_entree_epouse_la_forme_de_la_carte_3D_du_bundle():
    """LE CONTRAT AVEC L'AUTRE TÂCHE. L'onglet « Établi » réutilisera la carte
    EXISTANTE de la Bibliothèque, celle que T3 alimente pour l'onglet 3D :

        {name, kind, size, date, provider, jobId, short, url, thumb}

    D'où `kind: "asset3d"` : la carte 3D, sa vignette et son lien, sans une
    ligne de rendu de plus. Ce qu'il ne donne PAS est mesuré par
    `..._une_version_ne_se_donne_pas_pour_imprimable`. `size` reste vide comme
    dans T3 (le bundle a `go(bytes)` pour ça) et `date` porte l'ISO brut, que
    l'onglet devra repasser par `mo()`.
    """
    from app.services import mesh_edit
    _job("prod_forme")
    mesh_edit.ecrire_version("prod_forme", _glb_de_banc(),
                             operation="extraire", detail={"noeuds": [0]})

    e = [x for x in _items() if x["job"] == "prod_forme"][0]
    for cle in ("name", "kind", "size", "date", "provider",
                "jobId", "short", "url", "thumb"):
        assert cle in e, cle
    assert e["kind"] == "asset3d"
    assert e["provider"] == "Établi"
    assert "imprimable" in e
    assert e["jobId"] == "prod_forme"
    # le libellé dit de quel maillage il s'agit : le job, sa version, le geste
    assert "prod_forme" in e["name"]
    assert "v2" in e["name"]
    assert "extraire" in e["name"]
    # et de quoi retrouver le maillage sans repasser par une autre route
    assert e["bytes"] > 0
    assert e["sha256"]
    assert e["created_at"]


# ── L. l'onglet « Établi » du bundle ─────────────────────────────────────────
# La MOITIÉ BUNDLE de la même demande — la section K a livré la route, celle-ci
# livre la catégorie qui la montre. Forme choisie : un SEPTIÈME onglet, à côté
# d'Images / Renders / 3D / Sprites / Audio / Favoris.
#
# Greffé par `scripts/patch_bundle_etabli.py`, dernier maillon de la chaîne
# Bibliothèque (libpicker → libprov → libsend → etabli). Banc MIROIR comme le
# reste du fichier : il lit le bundle comme du texte.

_BUNDLE_REL = "dist/assets/index-BEOJX8L5.js"
_PATCHER = RACINE / "scripts" / "patch_bundle_etabli.py"


def _bundle() -> str:
    return _lire(_BUNDLE_REL)


def _patcher():
    """Le patcher CHARGÉ comme un module, jamais lu comme de la prose.

    Ses `PATCHES` sont des données : y poser une assertion, c'est épingler le
    patch lui-même — pas une phrase de docstring qui le décrirait.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("_pb_etabli", _PATCHER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_les_negations_de_cette_section_n_utilisent_PAS__code():
    """`_code()` est l'outil des assertions négatives de ce fichier. Sur le
    BUNDLE MINIFIÉ il est un piège, et cette section s'en passe exprès.

    Il retire les blocs `/* … */`. Un bundle minifié en contient dans des
    littéraux — regex, chaînes d'URL — sans le `*/` qui va avec : le `re.S`
    avale alors tout jusqu'au `*/` suivant, des centaines de milliers de
    caractères plus loin. Mesuré ici plutôt que supposé : l'écran Library
    ENTIER disparaît, si bien qu'un `assert X not in _code(bundle)` serait vert
    quoi qu'on écrive dans le patch. Les négations d'ici portent donc sur
    `_lire`, ce qui est sans risque pour la raison inverse de celle qui a
    motivé `_code` : un bundle minifié n'a aucune prose française où un
    marqueur pourrait se satisfaire tout seul.
    """
    entier, ampute = _lire(_BUNDLE_REL), _code(_BUNDLE_REL)
    assert len(entier) - len(ampute) > 400_000
    # et c'est bien la région patchée qui tombe
    assert "Object.keys(vo)" in entier
    assert "Object.keys(vo)" not in ampute
    assert 'if(m.kind==="asset3d"&&m.short' in entier
    assert 'if(m.kind==="asset3d"&&m.short' not in ampute


def test_l_onglet_sort_de_la_rangee_EXISTANTE_sans_une_ligne_de_markup():
    """« Respecte le design complet de l'application. » Pris au mot : le patch
    n'écrit AUCUN composant, AUCUNE CSS, AUCUN style.

    La rangée d'onglets du bundle est `Object.keys(vo).map(...)` — `vo` est
    l'objet de démonstration. Ajouter une clé y suffit : le bouton « Établi »
    sort du même `map` que ses six voisins, donc même balise, même typographie,
    même hauteur, mêmes jetons de couleur, même pastille de compte. Un onglet
    fabriqué à la main aurait pu se voir ; celui-ci ne le peut pas.
    """
    s = _bundle()
    # la clé, donc le bouton
    assert ',"3D":[],Sprites:[],Audio:[],Favoris:[],"Établi":[]};' in s
    # UNE seule rangée, toujours pilotée par `vo`
    assert s.count("Object.keys(vo)") == 1
    assert ("children:Object.keys(vo).map(C=>{const Q=(T[C]||[]).length,"
            "ee=Q>0?Q:vo[C].length;") in s
    # le gabarit du bouton, INTACT et unique — le nôtre passe par lui
    assert s.count('onClick:()=>{i(C);dzSFs("")},style:{height:26,'
                   'padding:"0 10px",background:o===C?"var(--bg-panel-2)"'
                   ':"transparent"') == 1
    # et la preuve structurelle : rien de visuel n'est injecté nulle part
    interdits = ("r.jsx", "style:", "className", "createElement",
                 "document.head", "borderRadius", "<button", "<div")
    for tag, _ancre, repl in _patcher().PATCHES:
        for mot in interdits:
            assert mot not in repl, (tag, mot)


def test_l_onglet_vide_ne_se_remplit_pas_d_items_de_demonstration():
    """`vo` n'est pas qu'une liste de noms d'onglets : le bundle s'en sert de
    REPLI quand la catégorie réelle est vide (`Y.length>0?Y:vo[o]`), et il lit
    `vo[C].length` pour la pastille de compte.

    D'où le tableau VIDE plutôt qu'une liste peuplée : sans lui, l'onglet
    montrerait des maquettes à qui n'a encore rien produit, et la pastille
    afficherait un faux compte.

    Et d'où une CLÉ, plutôt que rien : `C` vient de `Object.keys(vo)`, donc
    `vo[C]` est toujours défini et une clé absente ne LÈVE pas — elle donne
    zéro onglet, un patch invisible et muet, plus difficile à repérer qu'un
    crash. Le bundle porte d'ailleurs un second déréférencement non gardé au
    site de rendu, `(T[o]||[]).length||vo[o].length`, inatteignable pour
    exactement la même raison : `o` n'est jamais écrit qu'avec une clé de `vo`.
    """
    s = _bundle()
    assert "Y.length>0?Y:vo[o]" in s
    assert "return(T[o]||[]).length||vo[o].length," in s
    assert '"Établi":[]' in s
    assert '"Établi":[{' not in s          # jamais d'items de démonstration
    assert s.count("Établi") == 2          # la clé de `vo` + celle de `T`


def test_la_liste_vient_de_la_route_greffee_sur_le_sondage_EXISTANT():
    """La catégorie est alimentée par `GET /api/etabli/productions`, lue dans
    l'effet de sondage QUE `vm` A DÉJÀ — celui qui rafraîchit images, jobs et
    audio toutes les 8 s, avec son drapeau de montage et son `clearInterval`.

    C'est le chemin que T3 emprunte pour ses jobs, et l'imiter évite d'inventer
    un cycle de vie : pas de second `useEffect`, pas de second intervalle, pas
    de second démontage à tenir. Le drapeau `C` est repris tel quel, sinon une
    réponse en retard écrirait dans un composant démonté.
    """
    s = _bundle()
    assert s.count("/api/etabli/productions") == 1
    assert s.count("__dzEtabli") == 2      # la définition + l'appel
    assert "d(W),f(R||[]),__dzEtabli(function(L){if(C)dzEtas(L)})," in s
    assert '[dzSF,dzSFs]=x.useState(""),[dzEta,dzEtas]=x.useState([]),' in s
    assert '__dzFavImgHas(z.name))),"Établi":dzEta},Y=T[o]||[],' in s
    # aucun cycle de vie neuf : la preuve est dans les greffes elles-mêmes
    for tag, _ancre, repl in _patcher().PATCHES:
        assert "useEffect" not in repl, tag
        assert "setInterval" not in repl, tag


def test_la_date_ISO_de_la_route_est_repassee_par_mo():
    """La route rend `date` en ISO BRUT là où T3 envoie à la carte une date
    déjà passée par `mo()` (« 3h ago »). Sans correction, la carte afficherait
    `2026-08-30T20:39:30+00:00`.

    L'assertion porte sur la POSITION du champ, pas sur sa présence : le
    mapping est un `Object.assign({}, z, {…})`, et seul ce qui se trouve dans
    le TROISIÈME argument écrase la valeur du serveur. Un `date:` resté du côté
    de `z` ne corrigerait rien.
    """
    s = _bundle()
    i = s.index("function __dzEtabli(cb){")
    corps = s[i:i + 700]
    ecrase = corps.split("Object.assign({},z,{", 1)[1]
    assert ecrase.startswith('date:mo(z&&z.date)||""')


def test_un_thumb_NUL_recoit_le_repli_shot_0_que_React_ne_declencherait_pas():
    """La vignette vaut `null` quand le job n'a ni `preview.png` ni silhouette
    (section K). La carte 3D a pourtant un repli :

        <img src={C.thumb} onError={… src = "/api/assets/3d/"+C.short+"/shot/0"}>

    Il ne joue JAMAIS sur `null` : React OMET l'attribut `src` quand la valeur
    est nulle, le navigateur ne demande donc rien et n'émet aucun `error`. La
    case reste vide, sans que rien ne le signale. Le repli est donc posé À LA
    LECTURE, avant que la carte ne le voie.

    La carte, elle, n'est pas touchée — les deux assertions du milieu le
    disent : c'est bien son `onError` qui était impuissant, pas absent.
    """
    s = _bundle()
    assert 'thumb:(z&&z.thumb)||("/api/assets/3d/"+sh+"/shot/0")' in s
    assert "src:C.thumb,alt:C.name,onError:" in s
    assert 'ee.currentTarget.src="/api/assets/3d/"+C.short+"/shot/0"' in s
    # 3 occurrences d'origine + la nôtre
    assert s.count("/shot/0") == 4


def test_le_menu_masque_l_Impression_3D_quand_imprimable_est_faux():
    """`kind: "asset3d"` fait apparaître « Envoyer vers → Impression 3D » sur
    toute carte portant un `short`, et ce menu appelle
    `POST /api/print3d/from-assets3d/<short>` — une route qui lit `model.glb`
    et JAMAIS `model.v<n>.glb`. Une entrée « v2 · reparer » y ferait imprimer
    le BROUILLON, en silence, et l'objet sorti de l'imprimante serait faux.
    `..._une_version_ne_se_donne_pas_pour_imprimable` (section K) le mesure.

    L'onglet masque donc l'entrée. Il ne RÉPARE pas la route d'impression :
    c'est un autre chantier, et le menu ne sait de toute façon pas transmettre
    un numéro de version — d'où le pin à 3 ci-dessous, qui dit qu'elle n'a pas
    bougé.

    Deux détails portent tout :
      * `!==!1` et non `===!0` dans la garde : les cartes de l'onglet 3D
        n'ont pas ce champ, `undefined!==false` reste vrai, et leur entrée
        d'impression survit intacte ;
      * `===!0` et non `!!` dans le mapping : si la route cessait un jour
        d'envoyer le champ, le menu se FERMERAIT au lieu de s'ouvrir sur un
        mensonge.

    CONSÉQUENCE ASSUMÉE : dans `__dzSendTo`, toutes les cibles sont sous des
    gardes de `kind`, et `asset3d` n'en a QU'UNE — l'impression. Une production
    de l'Établi non imprimable obtient donc un menu ENTIÈREMENT VIDE, c'est-à-
    dire « Aucune cible pour cet asset » : la carte offre un « Envoyer vers… »
    qui ne peut que décliner. C'est disgracieux, et infiniment préférable à
    imprimer le brouillon en silence. Cela se corrigera le jour où
    `print3d_from_assets3d` acceptera un numéro de version, pas avant.
    """
    s = _bundle()
    assert 'if(m.kind==="asset3d"&&m.short&&m.imprimable!==!1){' in s
    assert ('if(!items.length){__dzToast("Aucune cible pour cet asset");'
            'return}') in s
    assert 'if(m.kind==="asset3d"&&m.short){' not in s
    assert "imprimable:(z&&z.imprimable)===!0" in s
    assert s.count("__dzPrint3d") == 3


def test_les_chips_de_provenance_restent_muettes_sur_l_onglet_Etabli():
    """`__dzSrcChips` (maillon libprov) ne rend rien hors « Images » et
    « Renders » : la rangée de filtres ne s'affiche donc pas ici, et c'est bien
    — les productions de l'Établi ont toutes la même provenance.

    Reste le piège : `dzSF` est remis à zéro au changement d'onglet par ce même
    libprov. Le patch ne touche ni la garde ni la remise à zéro, si bien qu'on
    ne peut pas arriver sur « Établi » avec un filtre resté armé, qui viderait
    la catégorie sans dire pourquoi.
    """
    s = _bundle()
    assert ('function __dzSrcChips(o,T,sf,setSf){'
            'if(o!=="Images"&&o!=="Renders")return null;') in s
    assert s.count("__dzSrcChips") == 2
    assert 'onClick:()=>{i(C);dzSFs("")}' in s
    for tag, _ancre, repl in _patcher().PATCHES:
        assert "__dzSrcChips" not in repl, tag
        assert "dzSFs(" not in repl, tag


def test_les_maillons_voisins_de_la_chaine_Bibliotheque_gardent_leurs_comptes():
    """Un patcher de bundle qui vise mal efface le maillon d'à côté sans un
    mot. Ces comptes sont ceux que les bancs voisins épinglent déjà
    (test_library_picker, test_library_provenance, test_library_sendto,
    test_print3d) ; les répéter ici attrape la casse AU MOMENT où elle se
    produit, pas trois fichiers plus loin.
    """
    s = _bundle()
    attendus = {
        "__dzLibPicker": 10, "__dzSrcChips": 2, "__dzSendTo": 2,
        "__dzPrint3d": 3, "__dzToSpriteLab": 5, "__dzQuickStart": 3,
        "__dzMontageAdd": 4, "deepotus:select-post": 6,
        "dz_nav_collapsed": 2, "__dzCatBar": 2,
    }
    for jeton, combien in attendus.items():
        assert s.count(jeton) == combien, jeton
    # et le patcher porte les mêmes comptes, avant comme après
    P = _patcher()
    for _nom, sonde, combien in P.STABLE_PROBES:
        if sonde in attendus:
            assert combien == attendus[sonde], sonde
    for sonde, combien in P.POST_COUNTS:
        assert s.count(sonde) == combien, sonde


def test_le_patcher_etabli_est_un_assert_garde_en_queue_de_chaine():
    """Le patron du dépôt : une ancre cherchée, une exception bruyante si elle
    manque ou si elle est ambiguë, une sauvegarde dédiée `.bak_etabli`, un
    `--check` qui n'écrit rien, et jamais de `repatch_all` sur cette chaîne.

    `apply` est APPELÉE ici, pas lue : c'est la garde elle-même qu'on éprouve,
    sur une ancre absente puis sur une ancre en double.
    """
    import pytest
    P = _patcher()
    assert P.TAG == "etabli"
    assert P.MARKER == "__dzEtabli"
    assert P.REL_BUNDLE.as_posix() == "frontend/dist/assets/index-BEOJX8L5.js"
    assert P.deltas() == (P.SPEC_CHAR_DELTA, P.SPEC_BYTE_DELTA)
    assert P.check_spec_parity() == P.deltas()

    with pytest.raises(SystemExit):
        P.apply("rien de tel ici", "ancre-absente", "x", "t-absente")
    with pytest.raises(SystemExit):
        P.apply("aa", "a", "x", "t-ambigue")
    assert P.apply("-a-", "a", "b", "t-ok") == "-b-"

    src = _PATCHER.read_text(encoding="utf-8")
    assert "guard_downstream" in src and "STABLE_PROBES" in src
    assert '.bak_" + TAG' in src and "--check" in src
    # CRLF partout : un patch qui normalise les fins de ligne réécrirait tout
    crlf, lf, cr = P.eol_stats((FRONT / _BUNDLE_REL).read_bytes())
    assert crlf > 0 and (lf, cr) == (0, 0)


def test_le_bundle_livre_est_EXACTEMENT_le_patch_applique_UNE_fois():
    """L'épingle la plus forte de la section : le bundle versionné n'est pas
    « un bundle qui contient nos marqueurs », c'est le résultat EXACT des six
    greffes appliquées une fois à la ligne de base post-libsend.

    Le banc défait le patch (chaque remplacement est unique, donc réversible),
    vérifie qu'aucune trace ne survit, puis le refait par `apply` — la vraie
    fonction, avec sa garde d'unicité — et compare caractère à caractère.

    Modifier un seul caractère d'un remplacement du patcher rend ce test rouge.

    Ce test ne dit RIEN de l'idempotence, contrairement à ce qu'affirmait sa
    première rédaction : trois des six ancres SURVIVENT dans le fichier livré,
    et c'est `..._l_idempotence_ne_vient_PAS_des_ancres...`, ci-dessous, qui
    mesure d'où elle vient vraiment.
    """
    P = _patcher()
    livre = _bundle()

    nu = livre
    for tag, ancre, repl in reversed(P.PATCHES):
        assert nu.count(repl) == 1, tag
        nu = nu.replace(repl, ancre)
    assert P.MARKER not in nu
    assert "Établi" not in nu
    assert len(livre) - len(nu) == P.SPEC_CHAR_DELTA

    refait = nu
    for tag, ancre, repl in P.PATCHES:
        assert refait.count(ancre) == 1, tag
        refait = P.apply(refait, ancre, repl, tag)
    assert refait == livre
    assert livre.count(P.MARKER) == P.MARKER_ATTENDU


def test_l_idempotence_ne_vient_PAS_des_ancres_mais_du_marqueur_et_du_backup():
    """Où l'idempotence de ce patcher se trouve vraiment — mesuré, parce que la
    réponse intuitive est fausse et que la première rédaction du banc s'y était
    laissé prendre.

    On croirait qu'un patcher assert-garde s'auto-protège : chaque ancre étant
    consommée par sa greffe, une seconde passe ne trouverait plus rien et
    lèverait. C'est vrai de E4, E5 et E6, qui REMPLACENT leur ancre. Ce ne
    l'est pas de E1, E2 et E3, qui greffent par préfixe ou par suffixe : leur
    remplacement CONTIENT leur ancre, si bien que l'ancre survit intacte dans
    le fichier livré. Une seconde passe d'`apply` sur le bundle versionné
    doublerait ces trois greffes SANS RIEN LEVER — le marqueur passerait de 2
    à 4. C'est mesuré ci-dessous, pas supposé.

    L'idempotence est pourtant réelle (quatre passages, même sha256), mais elle
    tient à deux gardes du patcher :

      * `shutil.copy2(bak, bundle)` RESTAURE la ligne de base avant de patcher,
        si bien que chaque passage repart du bundle post-libsend ;
      * le refus « marqueur présent sans `.bak_etabli` » ferme le seul chemin
        par lequel on patcherait un fichier déjà patché — celui où la
        sauvegarde a disparu.

    Le banc les épingle PARCE QUE la docstring fautive nommait le mauvais
    mécanisme : un mainteneur qui l'aurait crue pouvait retirer la restauration
    en la jugeant redondante, et le patch se serait mis à doubler en silence.

    Les deux assertions de gardes portent sur l'ARBRE SYNTAXIQUE de `main`, et
    non sur son texte : un `"shutil.copy2" in source` serait satisfait par la
    prose ci-dessus. Même raison, et même forme, que
    `..._la_route_ne_gele_pas_la_boucle_d_evenements` en section K.

    Et la restauration est cherchée DANS LA BRANCHE `else` de
    `if not bak.exists()`, pas n'importe où : `main` appelle
    `shutil.copy2(bak, bundle)` une SECONDE fois, pour défaire l'écriture
    quand la vérification post-patch échoue. Un simple « cet appel existe
    quelque part » restait vert alors que la restauration d'entrée avait été
    retirée — mutant mesuré, assertion resserrée.
    """
    import ast
    import inspect
    P = _patcher()
    livre = _bundle()

    survivantes = {tag for tag, ancre, _r in P.PATCHES if ancre in livre}
    assert survivantes == {"E1-lecteur", "E2-etat", "E3-charge"}
    epuisees = {tag for tag, ancre, _r in P.PATCHES if ancre not in livre}
    assert epuisees == {"E4-liste", "E5-onglet", "E6-garde-impression"}

    # ce qu'une seconde passe NAÏVE ferait vraiment au bundle livré
    doublee = livre
    for _tag, ancre, repl in P.PATCHES:
        if doublee.count(ancre) == 1:
            doublee = doublee.replace(ancre, repl)
    assert doublee.count(P.MARKER) == 2 * P.MARKER_ATTENDU
    assert len(doublee) > len(livre)

    # les deux gardes qui tiennent l'idempotence, lues sur l'arbre syntaxique
    arbre = ast.parse(inspect.getsource(P.main))
    porte = [n for n in ast.walk(arbre) if isinstance(n, ast.If)
             and ast.unparse(n.test) == "not bak.exists()"]
    assert len(porte) == 1
    dans_le_else = {ast.unparse(c) for b in porte[0].orelse
                    for c in ast.walk(b) if isinstance(c, ast.Call)}
    assert "shutil.copy2(bak, bundle)" in dans_le_else
    tests = {ast.unparse(n.test) for n in ast.walk(arbre)
             if isinstance(n, ast.If)}
    assert "MARKER in read_src(bundle)" in tests        # l'état ambigu refusé


# ── M. la vignette du canevas : fabriquée À L'ÉCRITURE ───────────────────────
# LE DÉFAUT MESURÉ. L'onglet « Établi » montrait des vignettes blanches parce
# que l'image N'EXISTE PAS SUR LE DISQUE pour la plupart des jobs : sur les
# trois jobs de l'utilisateur, un seul porte un vrai rendu de moteur
# (`4fce8946`, 190 couleurs distinctes) ; `7f34b585` a un `preview.png` ET un
# `shot_0.png` qui sont le MÊME aplat ambré (14 couleurs) ; `6e0a8a5f` n'a ni
# rendu ni shot, seulement des masques de silhouette. La section K a corrigé
# l'ORDRE de préférence (`preview` → `shot_0` → silhouette) : juste, mais
# impuissant — aucun ordre n'invente une image absente.
#
# Le remède est de la FABRIQUER : l'Établi affiche déjà le maillage cadré en
# three.js, il capture son canevas. La règle structurante tient et se dit —
# « le navigateur voit et manipule, Python écrit » porte sur l'AUTORITÉ DU
# MAILLAGE, et `test_la_page_ne_fabrique_jamais_un_glb` reste vert : une
# vignette PNG n'est pas un GLB, et c'est bien Python qui écrit le fichier.
#
# À L'ÉCRITURE SEULEMENT — décision de l'utilisateur, gardée par
# `..._nait_A_L_ECRITURE_SEULEMENT` : aucun rattrapage à l'ouverture, aucun
# bouton de régénération, aucun traitement par lots.


def _png_de_banc(w: int = 8, h: int = 8) -> bytes:
    """Un PNG RÉEL — la route vérifie la signature, pas la taille."""
    import io
    from PIL import Image
    t = io.BytesIO()
    Image.new("RGB", (w, h), (30, 80, 140)).save(t, "PNG")
    return t.getvalue()


def _poster_vignette(c, job, version, octets: bytes):
    return c.post("/api/etabli/vignette",
                  params={"job": job, "version": version},
                  content=octets, headers={"Content-Type": "image/png"})


def test_la_vignette_du_canevas_est_ecrite_par_PYTHON_et_servie():
    """LA CHAÎNE ENTIÈRE, FRAPPÉE. Le navigateur envoie les octets d'un PNG ;
    Python les écrit dans le dossier du job, sous un nom qui porte le NUMÉRO
    DE VERSION ; une route les rend. Rien ici ne cherche une chaîne dans un
    fichier : une route d'écriture se teste en la frappant.
    """
    from app.config import settings
    from app.services import mesh_edit
    _job("vign_canevas")
    mesh_edit.ecrire_version("vign_canevas", _glb_de_banc(),
                             operation="reparer", detail={})
    octets = _png_de_banc()

    c = _client()
    r = _poster_vignette(c, "vign_canevas", 2, octets)
    assert r.status_code == 200, r.text
    assert r.json()["fichier"] == "vignette_v2.png"

    # sur le DISQUE, dans le dossier du job, à l'octet près
    p = settings.outputs_path / "assets3d" / "vign_canevas" / "vignette_v2.png"
    assert p.is_file()
    assert p.read_bytes() == octets

    # et servie
    g = c.get("/api/assets/3d/vign_canevas/vignette", params={"v": 2})
    assert g.status_code == 200
    assert g.headers["content-type"] == "image/png"
    assert g.content == octets
    # une version sans vignette ne se sert pas en lien mort
    assert c.get("/api/assets/3d/vign_canevas/vignette",
                 params={"v": 7}).status_code == 404


def test_la_vignette_du_canevas_passe_AVANT_le_rendu_du_moteur():
    """L'ORDRE DE PRÉFÉRENCE, RALLONGÉ EN TÊTE. La section K a établi
    `preview` → `shot_0` → silhouette et cet ordre-là ne bouge pas ; la
    vignette du canevas se pose AVANT lui, et pour la raison qui a motivé
    toute la tâche : `preview.png` date du premier tir du moteur, il montre
    le BROUILLON — quand il montre quelque chose — là où la capture montre la
    version qui vient d'être écrite.

    La fixture porte les DEUX images du moteur pour que la préséance se
    mesure : sans la nouvelle branche, `preview.png` gagnerait.
    """
    from PIL import Image
    from app.services import mesh_edit
    d = _job("vign_avant_preview")
    Image.new("RGB", (1, 1)).save(d / "preview.png")
    Image.new("RGB", (1, 1)).save(d / "shot_0.png")
    mesh_edit.ecrire_version("vign_avant_preview", _glb_de_banc(),
                             operation="reparer", detail={})

    c = _client()
    par_job = {e["job"]: e
               for e in c.get("/api/etabli/productions").json()["items"]}
    # avant la capture : le rendu du moteur, l'ordre de la section K
    assert par_job["vign_avant_preview"]["thumb"] == \
        "/api/assets/3d/vign_avant_preview/preview"

    assert _poster_vignette(c, "vign_avant_preview", 2,
                            _png_de_banc()).status_code == 200
    par_job = {e["job"]: e
               for e in c.get("/api/etabli/productions").json()["items"]}
    assert par_job["vign_avant_preview"]["thumb"] == \
        "/api/assets/3d/vign_avant_preview/vignette?v=2"
    # et l'URL sert VRAIMENT des octets : une URL morte donnerait une case
    # grise sans erreur nulle part (la leçon de la section K)
    assert c.get(par_job["vign_avant_preview"]["thumb"]).status_code == 200


def test_la_vignette_est_liee_a_SA_version_et_ne_deteint_pas_ailleurs():
    """Chaque version a la sienne, ou n'en a pas. Une vignette qui déteindrait
    sur toute la lignée remettrait exactement le défaut d'origine : une image
    qui ne montre pas ce que la carte annonce. La v3 n'a pas été capturée —
    elle retombe donc sur le rendu du moteur, et c'est ce qu'on mesure.
    """
    from PIL import Image
    from app.services import mesh_edit
    d = _job("vign_par_version")
    Image.new("RGB", (1, 1)).save(d / "preview.png")
    mesh_edit.ecrire_version("vign_par_version", _glb_de_banc(),
                             operation="reparer", detail={})       # v2
    c = _client()
    assert _poster_vignette(c, "vign_par_version", 2,
                            _png_de_banc()).status_code == 200
    mesh_edit.ecrire_version("vign_par_version", _glb_de_banc(),
                             operation="transformer", detail={})   # v3

    par_v = {e["version"]: e
             for e in c.get("/api/etabli/productions").json()["items"]
             if e["job"] == "vign_par_version"}
    assert par_v[2]["thumb"] == "/api/assets/3d/vign_par_version/vignette?v=2"
    assert par_v[3]["thumb"] == "/api/assets/3d/vign_par_version/preview"


def test_la_route_d_ecriture_verifie_que_c_est_REELLEMENT_un_PNG():
    """UNE ROUTE D'ÉCRITURE NON GARDÉE EST UNE PORTE OUVERTE. Le corps vient
    du navigateur : l'en-tête `Content-Type` ne prouve rien, seule la
    SIGNATURE le fait. Un JPEG, un HTML, un corps vide, huit octets tronqués —
    chacun refusé PARLANT, et rien sur le disque.
    """
    import io
    from PIL import Image
    from app.config import settings
    from app.services import mesh_edit
    _job("vign_pas_png")
    mesh_edit.ecrire_version("vign_pas_png", _glb_de_banc(),
                             operation="reparer", detail={})
    t = io.BytesIO()
    Image.new("RGB", (8, 8)).save(t, "JPEG")

    c = _client()
    for corps in (t.getvalue(), b"<html>pas une image</html>", b"", b"\x89PN"):
        r = _poster_vignette(c, "vign_pas_png", 2, corps)
        assert r.status_code == 400, corps[:8]
        assert "PNG" in r.text
    assert not (settings.outputs_path / "assets3d" / "vign_pas_png"
                / "vignette_v2.png").exists()


def test_la_route_d_ecriture_borne_la_taille_du_corps():
    """Le client REDIMENSIONNE avant d'envoyer (512 px de plus grand côté),
    mais le serveur ne peut pas le croire sur parole : un canevas 2000×1500
    ferait plusieurs mégaoctets, et rien n'oblige l'appelant à être notre
    page. La borne est à 2 Mio.

    Le corps du banc porte la SIGNATURE PNG : c'est bien la garde de TAILLE
    qui doit mordre, pas celle du format — sans quoi ce banc resterait vert
    en supprimant la borne.
    """
    from app.config import settings
    from app.services import mesh_edit
    _job("vign_trop_grosse")
    mesh_edit.ecrire_version("vign_trop_grosse", _glb_de_banc(),
                             operation="reparer", detail={})
    enorme = b"\x89PNG\r\n\x1a\n" + b"\0" * (2 * 1024 * 1024)

    r = _poster_vignette(_client(), "vign_trop_grosse", 2, enorme)
    assert r.status_code == 413, r.status_code
    assert "Mio" in r.text
    assert not (settings.outputs_path / "assets3d" / "vign_trop_grosse"
                / "vignette_v2.png").exists()


def test_la_route_d_ecriture_assainit_le_job_et_n_ecrit_que_dans_assets3d():
    """`Path(...).name`, ou une traversée. `../../evade` doit se réduire au
    NOM, `evade`, et l'écriture rester sous `outputs/assets3d`.

    Mesure par mutation : sans l'aplatissement, le chemin devient
    `outputs/assets3d/../../evade/…` — la garde d'existence de la version
    tombe alors sur un dossier qui n'existe pas, et le 200 attendu ici vire
    au 404. L'assertion mord des deux côtés.
    """
    from app.config import settings
    from app.services import mesh_edit
    _job("evade")
    mesh_edit.ecrire_version("evade", _glb_de_banc(),
                             operation="reparer", detail={})

    c = _client()
    r = _poster_vignette(c, "../../evade", 2, _png_de_banc())
    assert r.status_code == 200, r.text
    assert (settings.outputs_path / "assets3d" / "evade"
            / "vignette_v2.png").is_file()
    # et RIEN au-dessus du dossier des jobs
    assert not (settings.outputs_path / "vignette_v2.png").exists()
    assert not (settings.outputs_path.parent / "vignette_v2.png").exists()
    # un job vide ne fabrique pas de dossier
    assert _poster_vignette(c, "", 2, _png_de_banc()).status_code == 400
    assert not (settings.outputs_path / "assets3d"
                / "vignette_v2.png").exists()


def test_le_job_ne_peut_pas_remonter_d_un_cran():
    """`Path(...).name` N'APLATIT PAS `..`, ET LE BANC D'À CÔTÉ NE LE VOYAIT PAS.

    MESURÉ, pas supposé — `pathlib` normalise le point SIMPLE, jamais le
    point-point :

        Path("../../evade").name -> 'evade'   <- le seul cas d'abord testé
        Path("..").name          -> '..'      <- passe TEL QUEL
        Path("a/..").name        -> '..'      <- idem
        Path(".").name           -> ''

    `job=".."` composait donc `outputs/assets3d/../vignette_v1.png`, et la
    route répondait 200 en écrivant UN CRAN AU-DESSUS du dossier des jobs.
    L'évasion est d'un seul cran — `Path("../..").name` vaut encore `..` — et
    la seule chose qui la bloquait était la garde d'EXISTENCE du maillage : il
    fallait un `outputs/model.glb`, qu'aucun chemin de code ne crée. Non
    exploitable en l'état, donc, mais l'invariant qui nous sauvait n'était pas
    celui que le commentaire désignait — et une garde documentée comme tenant
    alors qu'elle ne tient pas est ce qui casse au refactor suivant.

    CE BANC ARME LE PIÈGE. Il pose ce `outputs/model.glb` exprès : sans lui,
    la route refuserait `..` en 404 « maillage introuvable » et le défaut
    resterait invisible, comme il l'est resté à vingt-quatre mutations.

    LE CORRECTIF N'EST PAS UN SECOND APLATISSEMENT — ce serait le même angle
    mort en double, et deux gardes IDENTIQUES se couvrent l'une l'autre. Le
    nom dégénéré se REFUSE. C'est le message qui est épinglé ici, pas
    seulement le code : la garde de confinement, d'une autre nature, refuse
    les mêmes entrées en disant AUTRE CHOSE, et il faut pouvoir dire laquelle
    des deux a parlé.
    """
    from app.config import settings
    from app.services import mesh_edit
    _job("vign_cran")
    mesh_edit.ecrire_version("vign_cran", _glb_de_banc(),
                             operation="reparer", detail={})
    hors = settings.outputs_path / "model.glb"
    hors.write_bytes(_glb_de_banc())
    try:
        c = _client()
        for j in ("..", "a/..", "peu/importe/..", ".", ""):
            r = _poster_vignette(c, j, 1, _png_de_banc())
            assert r.status_code == 400, (j, r.status_code, r.text[:200])
            assert "nom de job" in r.text, (j, r.text[:200])
        # et RIEN au-dessus du dossier des jobs
        assert not list(settings.outputs_path.glob("vignette_*.png"))
        # le job honnête, lui, passe toujours
        assert _poster_vignette(c, "vign_cran", 2,
                                _png_de_banc()).status_code == 200
    finally:
        hors.unlink(missing_ok=True)
        for x in settings.outputs_path.glob("vignette_*.png"):
            x.unlink()


def test_le_confinement_voit_ce_que_le_NOM_ne_dit_pas():
    """LA SECONDE GARDE, ET ELLE EST D'UNE AUTRE NATURE — c'est tout l'intérêt.

    Celle du dessus lit le NOM. Celle-ci RÉSOUT le chemin, donc elle voit ce
    qu'aucune lecture de nom ne peut voir : une jonction (ou un lien) posée
    dans le dossier des jobs. `vign_jonction` est un nom parfaitement
    honnête — pas de `..`, pas de séparateur, la première garde le laisse
    passer — et le chemin sort pourtant du dossier des jobs.

    DEUX GARDES QUI COMPOSENT, PAS QUI SE DOUBLENT, et ce fichier a déjà payé
    pour connaître la différence : deux `Path(...).name` en parallèle se
    couvraient si bien qu'en retirer un laissait tout vert. Ici, retirer la
    garde de NOM rougit le banc du dessus et laisse celui-ci vert ; retirer la
    garde de CONFINEMENT fait l'inverse. Chacune se prouve seule.

    La jonction est créée par `mklink /J`, qui ne demande aucun privilège sur
    Windows (mesuré). Là où elle échoue, le banc se retire plutôt que de
    mentir : il ne prouverait rien de plus en tombant.
    """
    import os
    import subprocess
    import pytest
    from app.config import settings

    ailleurs = settings.outputs_path / "hors_des_jobs"
    ailleurs.mkdir(parents=True, exist_ok=True)
    # le maillage attendu par la garde d'existence, posé DE L'AUTRE CÔTÉ de
    # la jonction : sans lui la route refuserait en 404 et ce banc ne dirait
    # rien du confinement
    (ailleurs / "model.v2.glb").write_bytes(_glb_de_banc())
    jobs = settings.outputs_path / "assets3d"
    jobs.mkdir(parents=True, exist_ok=True)
    lien = jobs / "vign_jonction"
    if lien.exists():
        os.rmdir(lien)
    fait = subprocess.run(["cmd", "/c", "mklink", "/J", str(lien),
                           str(ailleurs)], capture_output=True)
    if fait.returncode != 0:
        pytest.skip("jonction de répertoire impossible sur cette machine")
    try:
        r = _poster_vignette(_client(), "vign_jonction", 2, _png_de_banc())
        assert r.status_code == 400, (r.status_code, r.text[:200])
        assert "hors du dossier des jobs" in r.text, r.text[:200]
        assert not (ailleurs / "vignette_v2.png").exists()
        # ET LA LECTURE AUSSI. La route de service prend son `job` dans un
        # segment d'URL, donc du reseau elle aussi : servir un fichier de
        # l'autre cote de la jonction dirait deja ce qui existe hors du
        # dossier des jobs. Les deux routes franchissent la meme porte, et
        # cette assertion est ce qui l'epingle.
        (ailleurs / "vignette_v2.png").write_bytes(_png_de_banc())
        g = _client().get("/api/assets/3d/vign_jonction/vignette",
                          params={"v": 2})
        assert g.status_code == 400, (g.status_code, g.text[:200])
    finally:
        os.rmdir(lien)          # retire la JONCTION, pas sa cible
        for x in ailleurs.glob("*"):
            x.unlink()
        ailleurs.rmdir()


def test_la_vignette_s_ecrit_par_un_temporaire_puis_un_remplacement():
    """L'ÉCRITURE EST ATOMIQUE, ET RIEN NE L'ÉPINGLAIT. Remplacer le couple
    `tmp` + `replace` par un `p.write_bytes()` direct laissait le banc
    ENTIÈREMENT vert : une écriture interrompue (disque plein, processus tué)
    aurait alors laissé une vignette TRONQUÉE que la route sert — pire qu'une
    absence, qui est dite proprement.

    Rien de ce défaut n'est observable depuis une requête : le banc lit donc
    la fonction. Mais il la lit en AST, pas en texte — ni les commentaires ni
    la docstring ne sont des nœuds `ast.Call`, si bien qu'une prose promettant
    l'atomicité ne peut pas satisfaire cette garde. C'est le `_code()` des
    bancs frontend, avec l'outil juste pour du Python.
    """
    import ast
    import inspect
    from app.api import routes
    arbre = ast.parse(inspect.getsource(routes.etabli_vignette_ecrire))
    appels = {ast.unparse(n.func) for n in ast.walk(arbre)
              if isinstance(n, ast.Call)}
    assert "tmp.write_bytes" in appels
    assert "tmp.replace" in appels          # os.replace de pathlib, sans import
    assert "p.write_bytes" not in appels    # l'écriture directe, non atomique


def test_la_route_d_ecriture_refuse_une_version_qui_n_existe_pas():
    """Une vignette sans maillage est un mensonge en attente : la carte de la
    Bibliothèque la montrerait pour une version que le disque ignore. Le job
    inconnu, la version absente et la version non entière sont donc refusés
    AVANT toute écriture — et `0` avec eux, qui n'est le numéro de rien.
    """
    from app.config import settings
    from app.services import mesh_edit
    _job("vign_version")
    mesh_edit.ecrire_version("vign_version", _glb_de_banc(),
                             operation="reparer", detail={})
    png = _png_de_banc()
    c = _client()

    assert _poster_vignette(c, "job_inconnu_ici", 1, png).status_code == 404
    assert _poster_vignette(c, "vign_version", 9, png).status_code == 404
    assert _poster_vignette(c, "vign_version", 0, png).status_code == 400
    assert _poster_vignette(c, "vign_version", -3, png).status_code == 400
    assert _poster_vignette(c, "vign_version", "abc", png).status_code == 422
    d = settings.outputs_path / "assets3d" / "vign_version"
    assert not list(d.glob("vignette_*.png"))


def test_la_vignette_n_est_pas_capturee_par_la_route_des_formats():
    """PIÈGE D'ORDRE DE DÉCLARATION, le même que `/preview` porte déjà en
    commentaire. `GET /assets/3d/{job}/{fmt}` sert `model.<fmt>` : déclarée
    après lui, la route de la vignette serait avalée comme `fmt="vignette"`
    et irait chercher un `model.vignette`. Mesuré par mutation : déplacer la
    déclaration sous `/{fmt}` fait tomber le 200 de la dernière ligne.
    """
    from app.services import mesh_edit
    _job("vign_ordre")
    mesh_edit.ecrire_version("vign_ordre", _glb_de_banc(),
                             operation="reparer", detail={})
    c = _client()
    assert _poster_vignette(c, "vign_ordre", 2,
                            _png_de_banc()).status_code == 200
    # sans `v`, la route retombe sur 1 comme sa sœur silhouette
    assert c.get("/api/assets/3d/vign_ordre/vignette").status_code == 404
    assert c.get("/api/assets/3d/vign_ordre/vignette",
                 params={"v": 2}).status_code == 200


# ── M (suite). le côté navigateur : la capture ───────────────────────────────
# Bancs MIROIRS, comme tout le frontend de ce fichier.


def _capture() -> str:
    """Le corps de `capturerVignette`, commentaires COMPRIS — les assertions
    d'ordre ci-dessous sont POSITIVES : elles épinglent du code, aucune n'est
    satisfaite par de la prose. La seule négative de la série passe par
    `_code()`, comme le veut ce fichier."""
    js = _lire("etabli/etabli.js")
    return js.split("async function capturerVignette", 1)[1] \
             .split("\n}\n", 1)[0]


def test_la_capture_REND_le_canevas_avant_de_le_LIRE():
    """LE PIÈGE PRINCIPAL, ET IL EST MUET. `creerCanevas()` construit son
    `WebGLRenderer` sans `preserveDrawingBuffer`, donc à `false` : le tampon
    de dessin est effacé dès que le compositeur l'a pris. Lu à n'importe quel
    autre moment, le canevas rend une image TRANSPARENTE — c'est-à-dire
    exactement la vignette blanche que cette tâche existe pour supprimer, mais
    fabriquée par nos soins et sans la moindre erreur nulle part.

    Le remède ne touche PAS `creerCanevas`, canevas partagé du dépôt dont
    viewer.js annonce qu'un autre écran le réutilisera : il suffit de rendre
    et de lire DANS LE MÊME TOUR. L'ordre des deux lignes est donc porteur, et
    l'absence d'`await` entre elles l'est tout autant — un seul rendrait la
    main à la boucle d'évènements, qui effacerait le tampon.

    `drawImage` LIT le tampon comme `toDataURL` : `reduireCanevas` tombe sous
    la même règle et reste SYNCHRONE.
    """
    js = _lire("etabli/etabli.js")
    bloc = _capture()
    i_rendu = bloc.index("vue.renderer.render(vue.scene, vue.camera);")
    i_lu = bloc.index("reduireCanevas(vue.renderer.domElement)")
    assert i_rendu < i_lu
    assert "await" not in bloc[i_rendu:i_lu]
    # et la réduction ne rend la main nulle part non plus
    assert "async function reduireCanevas" not in js
    reduc = js.split("function reduireCanevas", 1)[1].split("\n}\n", 1)[0]
    assert "drawImage(source, 0, 0" in reduc
    assert "await" not in reduc


def test_le_gizmo_est_masque_pour_la_capture_et_RETABLI_meme_si_elle_leve():
    """`poserGizmo()` pose `GIZMO.getHelper()` dans `S.vueA.scene`, et
    `attach()` le rend visible (TransformControls.js ligne 806) : photographié,
    il poserait trois flèches rouge/vert/bleu en travers du maillage. On le
    masque avant le rendu.

    ET ON LE RÉTABLIT DANS UN `finally`. Une capture qui lève — contexte WebGL
    perdu, canevas de taille nulle — laisserait sinon le gizmo invisible pour
    le reste de la session : l'utilisateur cliquerait un nœud et ne verrait
    rien apparaître, sans qu'aucun message ne l'explique.
    """
    bloc = _capture()
    i_masque = bloc.index("if (helper) helper.visible = false;")
    i_rendu = bloc.index("vue.renderer.render(")
    i_finally = bloc.index("} finally {")
    i_retabli = bloc.index("if (helper) helper.visible = visible;")
    assert i_masque < i_rendu < i_finally < i_retabli
    # l'état est RELU, pas supposé : attach() le pose, detach() l'efface
    assert "const visible = helper ? helper.visible : false;" in bloc
    # et c'est bien le HELPER, l'Object3D de la scène, pas le contrôleur
    assert "GIZMO.getHelper()" in bloc


def test_la_capture_arrive_APRES_la_reouverture_et_si_elle_a_REUSSI():
    """LE MOMENT. `ecrireVersion()` écrit, rafraîchit la chronologie, puis
    ROUVRE le modèle sur la version écrite. Capturer avant cette réouverture
    photographierait la version PRÉCÉDENTE : la vignette mentirait, ce qui est
    pire que pas de vignette du tout.

    Et SEULEMENT si la réouverture a rendu vrai. `ouvrirPrincipale()` rend une
    promesse qui vaut `S.a === cible` — elle dit que la FILE est vide, pas
    qu'un modèle est chargé : un échec est avalé par son `.catch`, une demande
    dépassée se retire sans rien charger. Sans cette garde, on capturerait un
    canevas VIDE (charger() vide la vue AVANT d'échouer) et on écrirait la
    vignette blanche qu'on prétend supprimer.
    """
    js = _lire("etabli/etabli.js")
    corps = js.split("async function ecrireVersion", 1)[1].split("\n}\n", 1)[0]
    assert "const ouvert = await ouvrirPrincipale(cible);" in corps
    assert corps.index("const ouvert = await ouvrirPrincipale(cible);") \
        < corps.index("capturerVignette(")
    assert "if (ouvert) {" in corps
    assert corps.index("if (ouvert) {") < corps.index("capturerVignette(")


def test_un_echec_de_vignette_ne_fait_jamais_echouer_l_ecriture():
    """LA VERSION EST ÉCRITE, C'EST CE QUI COMPTE ; la vignette est un
    agrément. Deux ceintures, et les deux sont nécessaires :

      * `capturerVignette()` attrape ses propres échecs — la fabrication et
        l'envoi séparément — et les DIT dans la barre du bas, en rappelant que
        la version, elle, est sur le disque ;
      * le site d'appel ajoute un `.catch` parce que le `try` d'ecrireVersion
        n'a PAS de `catch` : un rejet inattendu partirait dans le vide APRÈS
        une écriture réussie, et rien ne le montrerait.
    """
    js = _lire("etabli/etabli.js")
    corps = js.split("async function ecrireVersion", 1)[1].split("\n}\n", 1)[0]
    assert "await capturerVignette(cible.job, cible.version).catch(() => {});" \
        in corps
    bloc = _capture()
    assert bloc.count("} catch (e) {") == 2      # la fabrication ET l'envoi
    assert bloc.count("direRefus(") == 2
    assert bloc.count("est écrite") == 2         # ce qui n'a PAS échoué


def test_la_capture_ne_s_insere_pas_dans_la_file_de_serialisation():
    """`_ouvrirPrincipale` est protégé par une file de promesses (`_file`) et
    un jeton (`_demande`). La capture vient APRÈS que la file s'est vidée et
    ne s'y greffe pas : un `_file = _file.then(...)` ferait attendre tout clic
    suivant sur un encodage PNG et un aller-retour réseau, et un rejet y
    laisserait la file rejetée POUR TOUJOURS.

    Assertion NÉGATIVE, donc posée sur `_code()` : ce fichier commente en
    expliquant ce qu'il écarte, et la prose de la capture contient précisément
    les deux noms qu'on interdit ici — la dernière ligne le prouve.
    """
    code = _code("etabli/etabli.js")
    bloc = code.split("async function capturerVignette", 1)[1] \
               .split("\n}\n", 1)[0]
    assert "_file" not in bloc
    assert "_demande" not in bloc
    assert "_file" in _capture()          # le témoin : la prose, elle, en parle


def test_la_vignette_est_REDUITE_avant_l_envoi_et_ne_grossit_jamais():
    """LA TAILLE. Un canevas d'écran fait couramment 2000×1500 sur un écran
    HiDPI (`setPixelRatio` va jusqu'à 2) : le PNG pèserait plusieurs
    mégaoctets pour une carte de bibliothèque large de deux cents pixels. 512
    est la taille des vignettes 3D du dépôt — `mesh_report.SILHOUETTE_PX`, les
    planches de matériaux — et l'ordre de grandeur d'un `preview.png` de
    moteur.

    L'aspect est GARDÉ : écraser le rendu dans un carré déformerait les
    proportions, ce que cette page-ci existe justement pour montrer. Et
    l'échelle est bornée à 1 — on réduit, on n'agrandit jamais un rendu de
    400 px en 512 flous.

    C'est le canevas RÉDUIT qui part : blober le canevas source annulerait
    tout le bénéfice sans que rien ne le dise.
    """
    js = _lire("etabli/etabli.js")
    assert "const VIGNETTE_PX = 512;" in js
    reduc = js.split("function reduireCanevas", 1)[1].split("\n}\n", 1)[0]
    assert "Math.min(1, VIGNETTE_PX / Math.max(w, h))" in reduc
    assert 'document.createElement("canvas")' in reduc
    bloc = _capture()
    assert bloc.index("reduireCanevas(") < bloc.index("reduite.toBlob(")
    assert '"Content-Type": "image/png"' in bloc
    assert "/api/etabli/vignette?job=" in bloc


def test_la_vignette_nait_A_L_ECRITURE_SEULEMENT():
    """DÉCISION DE L'UTILISATEUR, ET ELLE SE GARDE. Pas de rattrapage à
    l'ouverture, pas de bouton « régénérer », pas de traitement par lots : ses
    productions actuelles resteront sans vignette jusqu'à ce qu'il en écrive
    de neuves, et c'est assumé — le prix achète qu'aucune écriture disque ne
    le surprenne.

    Ce que ce banc mesure n'est pas une phrase mais un COMPTE : la définition,
    et UN seul site d'appel. Greffer la capture dans `_ouvrirPrincipale` ou
    derrière un bouton le ferait passer à trois, et ce banc rougirait.
    """
    code = _code("etabli/etabli.js")
    assert code.count("capturerVignette(") == 2      # la définition + l'appel
    corps = code.split("async function ecrireVersion", 1)[1] \
                .split("\n}\n", 1)[0]
    assert corps.count("capturerVignette(") == 1     # et il est ICI


# ── N. la plaque : étaler pour VOIR, jamais pour changer ─────────────────────
# Demande de l'utilisateur, mot pour mot : « pour pouvoir sélectionner
# décemment il faut intégrer une étape intermédiaire de visualisation sur
# plaque pour voir les différents éléments répartis sur la plaque ».
#
# LA RÈGLE QUI DOMINE CETTE SECTION : la plaque est une VUE, jamais une
# mutation. Sans garde, l'utilisateur étale, clique « écrire la version », et
# son modèle part ÉCLATÉ ET DÉFINITIF sur le disque. Ce n'est pas une
# intention : les bancs ci-dessous l'épinglent par trois mécanismes
# indépendants, et chacun a été vérifié par MUTATION.


def _plaque_bloc():
    """Le bloc de la plaque dans etabli.js, COMMENTAIRES RETIRÉS.

    Ce bloc est écrit dans le style du fichier — il EXPLIQUE ce qu'il refuse,
    et sa prose nomme `noterAttente`, `S.enAttente` et `piece.position`. Un
    `not in` posé sur le texte entier serait donc satisfait par la phrase même
    qui jure de ne pas s'en servir : le banc dirait rouge à un commentaire et
    vert à un appel. C'est le défaut que ce dépôt a corrigé huit fois sur ce
    chantier ; il ne sera pas commis une neuvième.
    """
    code = _code("etabli/etabli.js")
    # La borne de FIN est le branchement du bouton, dernière ligne du bloc —
    # et elle est écrite EN ENTIER. Coupée à `$("#btnPlaque")` seul, elle
    # tombait sur le `const b = $("#btnPlaque")` de majBoutonPlaque, deux
    # lignes plus bas : l'extrait faisait treize caractères et TOUTES les
    # assertions négatives posées dessus étaient vertes sur le vide. Mesuré
    # par mutation (un `noterAttente()` glissé dans basculerPlaque ne faisait
    # rougir personne), et c'est exactement le défaut que ce chantier a payé
    # huit fois : un banc satisfait par autre chose que ce qu'il vise.
    return code.split("function majBoutonPlaque", 1)[1] \
               .split('$("#btnPlaque").addEventListener', 1)[0]


def _plaque_liste():
    """Le BALISAGE de la liste latérale, commentaires retirés.

    Il vit dans rendreParties() et non dans le bloc ci-dessus : la liste est
    rendue par le rendu du panneau Parties lui-même, ce qui lui évite un
    second branchement d'évènements (voir #btnSeparer, l'erreur déjà payée).
    Extrait précisément, parce que `esc(x.nom)` existe AUSSI dans les rangées
    ordinaires du panneau : un banc posé sur la fonction entière serait vert
    même sans la moindre liste de plaque.
    """
    code = _code("etabli/etabli.js")
    return code.split("const plaqueBloc = !PLQ.active", 1)[1] \
               .split("box.innerHTML", 1)[0]


def test_le_module_de_la_plaque_est_servi_et_importe_par_la_page():
    """Le canevas est PARTAGÉ (spec §12) : ce qui est général vit dans
    /lib3d, ce qui est propre à l'Établi reste dans /etabli. L'étalement est
    général — le Plateau du jour où en voudra un. Non servi, le bouton de
    bascule serait mort-né et le refus ne vivrait que dans la console.
    """
    assert '"/lib3d/plaque.js"' in _lire("etabli/etabli.js")
    r = _client().get("/lib3d/plaque.js")
    assert r.status_code == 200
    assert "export function etaler" in r.text


def test_LA_PLAQUE_N_ECRIT_RIEN___ni_le_disque_ni_la_file():
    """L'ASSERTION LA PLUS IMPORTANTE DE LA TÂCHE.

    `S.enAttente` est la file de ce qui partira au serveur, et « écrire la
    version » est le seul entonnoir de cette page vers les trois plumes de P1.
    Si l'étalement l'alimentait, il suffirait d'étaler puis d'écrire pour
    graver un modèle éclaté. Chez Meshy, « Sur la plaque » est un aperçu ; le
    modèle assemblé reste la vérité.

    Deux gardes STRUCTURELLES, l'une sur chaque moitié de la chaîne : le
    module ne connaît AUCUNE route et aucun moyen de fabriquer un GLB ; le
    bloc de la page n'appelle JAMAIS noterAttente() ni ne touche à la file.
    Elles tiennent même si le corps des fonctions change du tout au tout.

    L'EXCEPTION, ET ELLE EST NOMMÉE : depuis la plaque façon slicer, la
    disposition composée sur la plaque est un PLAN DE PLAQUE, écrit par Python
    dans `plaque.v<N>.json` à côté du .glb (route `/api/etabli/plaque`). Ce
    n'est ni une version, ni un GLB, ni une ligne de la file : c'est la
    séparation maillage / disposition du 3MF. Le module reste sans route, le
    bloc de bascule reste sans écriture, et la route du plan n'entre PAS dans
    la table ROUTES — l'entonnoir d'écriture des versions garde ses trois
    plumes. Le banc du plan (section Q) mesure le reste.

    MUTATION VÉRIFIÉE : glisser `noterAttente("transformer", {});` dans
    basculerPlaque() fait rougir ce banc, et lui seul de la section.
    """
    plaque = _lire("lib3d/plaque.js")
    assert "fetch" not in plaque
    assert "/api/" not in plaque
    assert "XMLHttpRequest" not in plaque
    assert "GLTFExporter" not in plaque
    # le module ne connaît même pas le NOM de la file
    assert "enAttente" not in plaque
    assert "noterAttente" not in plaque
    bloc = _plaque_bloc()
    # L'EXTRAIT COUVRE BIEN LES TROIS FONCTIONS DE BASCULE. Sans cette
    # vérification, une borne mal placée réduirait le bloc à quelques
    # caractères et les trois assertions ci-dessous seraient vertes sur du
    # vide — c'est arrivé, et une mutation l'a montré.
    for atteste in ("function basculerPlaque", "function quitterPlaque",
                    "function oublierPlaque", "etaler(S.vueA, plan)"):
        assert atteste in bloc, atteste
    assert "noterAttente" not in bloc
    assert "S.enAttente" not in bloc
    assert "fetch" not in bloc
    # le témoin : la prose, elle, en parle — c'est pourquoi _code() est
    # indispensable au-dessus, et pourquoi ce banc ne s'en satisfait pas.
    assert "noterAttente" in _lire("etabli/etabli.js")
    # …ET LA ROUTE DU PLAN N'EST PAS UNE PLUME DE L'ENTONNOIR : la table des
    # routes d'écriture de version garde ses trois entrées, et le plan part
    # par sa propre constante. Le glisser vit HORS du bloc de bascule.
    routes = _table_js("etabli/etabli.js", "ROUTES")
    assert "plaque" not in routes, routes
    assert routes.count("/api/etabli/") == 3, routes
    assert 'const ROUTE_PLAQUE = "/api/etabli/plaque";' in _code("etabli/etabli.js")
    assert "ROUTE_PLAQUE" not in bloc


def test_le_decalage_d_etalement_ne_touche_JAMAIS_la_pose_d_une_piece():
    """LE PIÈGE LE PLUS CHER DE LA TÂCHE, DÉSARMÉ STRUCTURELLEMENT.

    Le seul producteur d'une ligne `transformer` est l'écouteur
    `objectChange` du gizmo, et il envoie au serveur `[o.position.x, y, z]`.
    Une pièce déplacée par l'étalement puis saisie au gizmo enverrait donc une
    translation qui INCLUT le décalage d'étalement — un GLB éclaté sur le
    disque, sans que rien ne grince.

    Le remède ne demande pas de vigilance : le décalage vit dans un BERCEAU,
    un Group neuf glissé entre la pièce et son parent, et la pièce garde sa
    pose au bit près. Le gizmo ne PEUT pas lire un décalage qui n'est pas là.

    MUTATION VÉRIFIÉE : remplacer `berceau.position.copy(` par
    `m.piece.position.copy(` fait rougir les deux moitiés de ce banc.
    """
    code = _code("lib3d/plaque.js")
    assert "berceau.position.copy(" in code
    # la pièce n'est JAMAIS écrite — ni translation, ni rotation, ni échelle
    assert "piece.position" not in code
    assert "piece.quaternion" not in code
    assert "piece.scale" not in code
    assert "piece.matrix" not in code
    # le témoin : la prose du module NOMME `piece.position.add(...)` pour dire
    # pourquoi elle ne l'écrit pas. Sans _code(), tout ce banc serait vert sur
    # sa propre explication.
    assert "piece.position" in _lire("lib3d/plaque.js")
    # et le berceau reprend la PLACE de la pièce dans la fratrie : l'ordre de
    # parcours ordonne le panneau Parties, et une liste qui se réordonne à la
    # bascule donnerait l'impression que le modèle a changé.
    assert "parent.children.splice(rang, 0, berceau)" in code


def test_le_gizmo_est_refuse_tant_que_la_plaque_est_affichee():
    """LA SECONDE GARDE, indépendante de la première. Le berceau rend le
    décalage illisible ; celle-ci empêche carrément de saisir une pièce
    étalée. Deux mécanismes sur le seul mode d'échec de cette tâche qui écrive
    un GLB faux — et le refus se DIT, comme partout sur cette page, plutôt que
    de laisser un clic sans effet.

    MUTATION VÉRIFIÉE : retirer le `if (estEtalee(S.vueA))` de poserGizmo()
    fait rougir ce banc et aucun autre.
    """
    code = _code("etabli/etabli.js")
    gz = code.split("function poserGizmo(objet)", 1)[1].split("\n}\n", 1)[0]
    # La garde ENTIÈRE, et son `return` : `"estEtalee(S.vueA)" in gz` seul
    # restait vert sur un `if (false && estEtalee(S.vueA))`. Mesuré par
    # mutation.
    assert "if (estEtalee(S.vueA)) {" in gz
    garde = gz.split("if (estEtalee(S.vueA)) {", 1)[1].split("  }", 1)[0]
    assert "GIZMO.detach();" in garde
    assert "return;" in garde
    assert "direRefus(" in garde
    # AVANT la remontée des parents : posée après, la garde laisserait
    # `attach()` s'exécuter sur le chemin nominal.
    assert gz.index("estEtalee(S.vueA)") < gz.index("let noeud = objet;")
    # et le gizmo LÂCHE avant l'étalement, plutôt que de suivre une pièce en
    # train de s'envoler à l'autre bout de la plaque
    bp = code.split("function basculerPlaque()", 1)[1].split("\n}\n", 1)[0]
    assert bp.index("GIZMO.detach();") < bp.index("etaler(S.vueA, plan)")
    # ET LE CLIC DE DÉSIGNATION SE TAIT. Le refus de poserGizmo() s'écrit en
    # ROUGE dans la barre du bas, et le clic dans le canevas est justement le
    # geste que la plaque existe pour servir : désigner une pièce qu'on voit
    # enfin. Sans cette garde, chaque sélection réussie sur le plateau
    # peindrait la barre en rouge — un refus qui ment sur un geste qui a
    # marché. La garde bruyante reste dans poserGizmo pour tout autre appelant.
    clic = code.split("designerAuClic(S.vueA", 1)[1]
    assert "if (!estEtalee(S.vueA)) poserGizmo(obj);" in clic


def test_l_etalement_se_range_AVANT_tout_changement_de_modele():
    """Piège hérité, et il se referme sur trois choses à la fois. Les berceaux
    et les couleurs d'origine sont accrochés aux objets et aux matériaux du
    modèle SORTANT, que le vider() de charger() est sur le point de libérer ;
    et le PLATEAU vit dans la scène, que vider() ne touche pas — il ne retire
    que `api.racine`. Non rangé, le plateau resterait sur la carte pour
    toujours, et un second étalement en poserait un deuxième par-dessus.

    Même place et même raison que `GIZMO.detach()` et `SEL.retenus.clear()` :
    là où le modèle affiché change, quoi qu'il arrive, et donc AVANT le
    chargement — pas dans un rendu qui n'a lieu qu'en cas de succès.

    DÉCISION ASSUMÉE : changer de modèle pendant que la plaque est affichée
    RAMÈNE à « Assemblé ». Ré-étaler le modèle entrant serait plus doux, et
    c'est justement ce qu'on refuse — la vue reviendrait éclatée après chaque
    écriture de version, sur un modèle que l'utilisateur vient d'écrire et
    qu'il veut voir tel qu'il est sur le disque.

    MUTATION VÉRIFIÉE : retirer l'appel laisse tout le reste vert.
    """
    js = _lire("etabli/etabli.js")
    ouvre = js.split("async function _ouvrirPrincipale", 1)[1].split("\n}\n", 1)[0]
    assert "oublierPlaque();" in ouvre
    assert ouvre.index("oublierPlaque();") < ouvre.index("await charger(S.vueA")
    # et `oublierPlaque` RANGE vraiment, il ne se contente pas d'oublier un
    # booléen — sans `ranger()`, le plateau survivrait au changement de modèle.
    ob = js.split("function oublierPlaque()", 1)[1].split("\n}\n", 1)[0]
    assert "ranger(S.vueA);" in ob
    assert "PLQ.active = false;" in ob


def test_le_retour_a_l_assemble_rend_le_modele_SANS_RECHARGER():
    """COROLLAIRE DE LA RÈGLE, et il n'est pas une optimisation. Un
    `ouvrirPrincipale(S.a)` repasserait par le verrou de sérialisation et par
    un téléchargement du GLB — 9 Mo sur le modèle de l'utilisateur — pour
    rendre un modèle que personne n'a modifié.

    ranger() défait ce qu'étaler a fait, dans l'ordre inverse et jusqu'au
    bout : la pièce remise à SA place dans la fratrie, la couleur d'origine
    rendue au matériau (et sa mémoire EFFACÉE, sans quoi le prochain
    étalement croirait l'avoir déjà mémorisée et ce matériau ne serait plus
    jamais restauré), la visibilité restaurée, le plateau libéré.

    MUTATION VÉRIFIÉE : remplacer le corps de quitterPlaque() par
    `ouvrirPrincipale(S.a)` fait rougir la première moitié ; retirer le
    `delete mat.userData.couleurOrigine` fait rougir la seconde.
    """
    code = _code("etabli/etabli.js")
    ob = code.split("function oublierPlaque()", 1)[1].split("\n}\n", 1)[0]
    qt = code.split("function quitterPlaque()", 1)[1].split("\n}\n", 1)[0]
    for interdit in ("ouvrirPrincipale(", "charger(", "fetch", "jget("):
        assert interdit not in ob + qt, interdit
    pl = _code("lib3d/plaque.js")
    rg = pl.split("export function ranger(api)", 1)[1].split("\n}\n", 1)[0]
    assert "e.piece.visible = e.visible;" in rg
    assert "e.parent.children.splice(e.rang, 0, e.piece)" in rg
    assert "mat.color.setHex(mat.userData.couleurOrigine)" in rg
    assert "delete mat.userData.couleurOrigine;" in rg
    # le plateau est LIBÉRÉ, pas seulement retiré : dix bascules laisseraient
    # sinon dix géométries et dix matériaux sur la carte. Et la POIGNÉE de
    # rotation avec lui, qui vit dans la même scène depuis la plaque slicer.
    assert "o.geometry.dispose()" in rg
    assert "for (const groupe of [etat.plateau, etat.poignee])" in rg
    assert "api.scene.remove(groupe)" in rg
    # le pivot de rotation se vide comme le berceau : la pièce n'y reste pas
    assert "e.pivot.clear();" in rg


def test_la_couleur_d_une_piece_est_STABLE_et_ne_clone_aucun_materiau():
    """UNE COULEUR PAR PIÈCE, et la même d'un affichage à l'autre : la teinte
    se DÉDUIT de l'index de nœud glTF par l'angle d'or, elle n'est pas lue
    dans une palette énumérée — laquelle aurait dépendu de l'ORDRE de la
    liste, donc du tri par surface, donc de la taille des pièces.

    ET AUCUN CLONE. glTF PARTAGE les matériaux : deux pièces qui se partagent
    le leur ne peuvent pas recevoir deux couleurs — exactement la limite
    d'`isoler()`, traitée exactement pareil. On ne clone PAS (il faudrait
    aussi libérer les clones, et le vider() de viewer.js ne saurait pas les
    retrouver) : on RÉDUIT LA PROMESSE, on COMPTE les matériaux partagés, et
    le panneau le DIT. La pastille de la liste, elle, ne ment jamais — elle
    est calculée, pas lue sur le maillage.
    """
    code = _code("lib3d/plaque.js")
    assert "const ANGLE_OR = 137.508;" in code
    assert "(((Number(cle) || 0) * ANGLE_OR) % 360) / 360" in code
    et = code.split("export function etaler(api, plan = null)", 1)[1].split("\n}\n", 1)[0]
    # aucun matériau n'est ni cloné ni créé pendant l'étalement
    assert "clone" not in et
    assert "Material" not in et
    # la couleur d'origine est mémorisée UNE fois, avant la première
    # altération — même dette et même remède que `opaciteOrigine`
    assert "mat.userData.couleurOrigine === undefined" in et
    assert "mat.color.copy(teinte)" in et
    # la limite est COMPTÉE...
    assert "filter((s) => s.size > 1).length" in code
    # ...et DITE à l'écran, sans quoi elle serait un commentaire de plus
    assert "PLQ.partages" in _code("etabli/etabli.js")
    assert "matériau(x) partagé(s)" in _lire("etabli/etabli.js")


def test_le_rangement_est_par_etageres_recentre_et_MESURABLE():
    """L'algorithme, et il est délibérément bête : boîte englobante par pièce,
    étagères par ordre de SURFACE DÉCROISSANTE, marge constante. On ne cherche
    pas l'optimalité — NP-difficile, et surtout illisible : les pièces
    changeraient de voisin au moindre changement de modèle.

    LA PURETÉ N'EST PAS UN ORNEMENT : sans three.js dans son corps, la
    fonction se mesure hors navigateur, ce qu'aucun autre morceau de ce
    canevas ne permet. Mesuré ainsi sur 12 pièces de tailles voisines — le
    modèle réel de l'utilisateur : 12 cases, ZÉRO chevauchement, empreinte
    5,176 × 6,876, milieu exactement (0, 0), et le même résultat quel que soit
    l'ordre d'entrée.

    La MARGE est relative à la plus grande pièce, et c'est une conséquence de
    l'absence d'échelle : un GLB n'a pas de millimètres, une marge absolue
    écarterait un modèle de 0,01 unité en poussière tout en collant les pièces
    d'un modèle de 100. Elle reste CONSTANTE au sens qui compte — une seule
    valeur pour tout l'étalement.
    """
    code = _code("lib3d/plaque.js")
    assert "export function rangerEnEtageres" in code
    corps = code.split("export function rangerEnEtageres", 1)[1].split("\n}\n", 1)[0]
    # pure : mesurable hors navigateur, et c'est cette assertion qui le tient
    assert "THREE." not in corps
    # surface DÉCROISSANTE
    assert "(b.l * b.p) - (a.l * a.p)" in corps
    # une nouvelle étagère quand la rangée déborde
    assert "x + b.l > cible" in corps
    # et l'étalement est RECENTRÉ sur l'origine : le plateau y est posé, et
    # cadrer() vise la boîte englobante du modèle.
    assert "p.x -= largeur / 2;" in corps
    assert "p.z -= profondeur / 2;" in corps
    # la marge, une seule fois, pour tout l'étalement
    assert "const marge = MARGE_RELATIVE * plusGrande;" in code


def test_la_regle_des_pieces_est_LA_PROFONDEUR_et_la_GEOMETRIE():
    """LE MIROIR DE TEXTE de la règle que les quatre bancs exécutés
    ci-dessous EXERCENT. Il ne garde pas le comportement — eux s'en chargent,
    et c'est justement parce qu'un miroir de texte NE POUVAIT PAS voir le
    défaut que la plaque est sortie sans étaler quoi que ce soit. Il garde les
    deux CLAUSES de la règle, pour qu'aucune ne disparaisse en silence : la
    géométrie (un pivot vide n'est pas un volume) et la profondeur (un nœud
    qui en contient un autre est une enveloppe, pas une pièce).

    Ce banc portait la règle INVERSE — « les nœuds les plus HAUTS » — et il
    était vert sur elle. Une mesure en navigateur l'a démentie ; on garde la
    trace de l'échange plutôt que de la remplacer sans un mot.
    """
    code = _code("lib3d/plaque.js")
    pd = code.split("export function piecesDe(api)", 1)[1].split("\n}\n", 1)[0]
    assert "o.userData.indexGltf === undefined" in pd
    # CLAUSE 1 — la géométrie, calculée en une seule descente
    assert "porteurs.has(o)" in pd
    assert "o.isMesh && o.geometry" in pd
    # CLAUSE 2 — la profondeur : on regarde EN DESSOUS, et on renonce
    assert "if (plusBas) return;" in pd
    dessous = pd.split("let plusBas = false;", 1)[1]
    assert "enfant.traverse((n)" in dessous
    assert "porteurs.has(n)) plusBas = true;" in dessous
    # et une pièce dont la boîte est vide n'est pas étalée non plus : elle
    # occuperait une case sans rien y montrer, et son œil ne commanderait
    # rien de visible.
    assert "boite.isEmpty()" in code


def test_le_plateau_a_sa_grille_et_N_INVENTE_AUCUN_MILLIMETRE():
    """UN GLB N'A AUCUNE ÉCHELLE EN MM. C'est
    `print3d.mettre_a_l_echelle(tris, cible_mm)` qui en fabrique une, au
    moment d'écrire un STL, et la garde du plateau de la Centauri Carbon 2
    (256 mm, print3d.py) vit LÀ-BAS. Écrire ici « 256 mm » afficherait une
    cote vraie sur un modèle sans échelle — une règle qui MENT.

    Le plateau se dimensionne donc sur l'empreinte de l'étalement, en unités
    du modèle. Sa GRADUATION existe depuis la plaque façon slicer, et c'est
    l'architecture qui tient la doctrine : plaque.js expose la GÉOMÉTRIE du
    plateau (côté, axe, coin, pas — un pas de plateau tiré de `pasGradue`),
    viewer.js DESSINE les règles, et la page seule écrit les libellés, par le
    formateur qui connaît la taille cible. Aucun des deux modules ne met un
    nombre en forme.

    Assertions NÉGATIVES, donc posées sur `_code()` : l'en-tête du module
    explique précisément qu'il n'y a pas de millimètres ici, et nomme les 256
    pour dire d'où ils ne viennent pas.
    """
    code = _code("lib3d/plaque.js")
    assert "GridHelper" in code
    # le pas du plateau vient de la règle 1-2-5 du canevas partagé, importée —
    # jamais d'une seconde règle écrite ici
    assert 'import { pasGradue, sensDesRegles } from "./viewer.js";' in code
    assert "pasGradue(brut)" in _fonction_plaque("geometriePlateau")
    # et NI le module du plateau NI le dessinateur des règles ne mettent un
    # nombre en forme : une mise en forme est un site où une unité peut naître
    for module, texte in (("plaque.js", code),
                          ("dessinerRegles", _fonction_viewer("dessinerRegles")),
                          ("bandeDeLibelles", _fonction_viewer("bandeDeLibelles"))):
        for forme in ("toFixed", "toLocaleString", " mm", "cible_mm"):
            assert forme not in texte, (module, forme)
    # dans la SCÈNE et non dans le modèle : vider() ne retire que api.racine,
    # un plateau greffé au modèle disparaîtrait sans que personne ne l'ait
    # rangé — et sans que sa géométrie ne soit libérée.
    assert "api.scene.add(groupe)" in code
    for menteur in (" mm", "cible_mm", "256"):
        assert menteur not in code, menteur
        assert menteur not in _plaque_bloc(), menteur
        assert menteur not in _plaque_liste(), menteur
    # le témoin : la prose, elle, en parle — c'est tout l'objet de son
    # avertissement.
    assert " mm" in _lire("lib3d/plaque.js")
    assert "256" in _lire("lib3d/plaque.js")


def test_la_liste_laterale_a_une_pastille_et_un_oeil_par_piece():
    """« une liste latérale avec un œil pour montrer ou masquer chacune » — la
    demande. Elle est rendue DANS le panneau Parties, par rendreParties()
    lui-même : un second panneau aurait dupliqué le branchement des
    évènements, et ce fichier a déjà payé cette erreur (voir #btnSeparer).

    Et les RÈGLES CSS comptent autant que le balisage : sans elles le bloc
    EXISTE et ne se lit pas — des pastilles invisibles faute de taille, des
    œils au style natif du navigateur. Une pastille est un <i> VIDE : sans
    largeur ni hauteur explicites, elle ne mesure rien et la couleur n'existe
    pas à l'écran. C'est le pire des échecs, le silencieux.
    """
    js, css = _lire("etabli/etabli.js"), _lire("etabli/etabli.css")
    bloc = _plaque_liste()
    assert 'class="plaque-oeil"' in bloc
    assert 'class="pastille"' in bloc
    # un œil PAR PIÈCE, et il porte la clé de la pièce — sans `data-cle`,
    # l'écouteur ne saurait pas quelle pièce masquer.
    assert 'data-cle="${esc(x.cle)}"' in bloc
    assert "montrerPiece(S.vueA, cle, masquee)" in js
    # la bascule vit dans l'en-tête, avec les contrôles de la VUE
    assert 'id="btnPlaque"' in _lire("etabli/index.html")
    assert '$("#btnPlaque").addEventListener("click", basculerPlaque);' in js
    # ET LE LIBELLÉ EST POSÉ AU DÉMARRAGE. index.html livre le bouton SANS
    # texte, délibérément : son libellé change avec l'état, et deux sources
    # pour un même texte divergent à la première retouche. Sans cet appel au
    # premier niveau du module, le bouton de l'en-tête naît VIDE — l'échec
    # silencieux que ce fichier traque partout. Jumeau exact du
    # `assert "rendreFiche();" in js  # et il est APPELÉ` de la tâche 2.
    #
    # Les ancres de COLONNE 0 ne sont pas décoratives : `majBoutonPlaque();`
    # est aussi appelé DANS oublierPlaque(), où il est indenté. Un `in js` nu
    # serait donc satisfait par cet appel-là, et le bouton pourrait naître
    # vide en gardant le banc vert.
    assert re.search(r"^rendreParties\(\);$.*?^majBoutonPlaque\(\);$"
                     r".*?^rendreFiche\(\);$", js, re.M | re.S)
    # les règles qui rendent le bloc LISIBLE
    assert ".plaque-oeil {" in css
    assert ".pastille {" in css
    assert "width: 10px; height: 10px" in css
    assert ".plaque-rang {" in css
    # hauteur POSÉE, jamais déduite : ce dépôt a vu 998 rangées s'effondrer
    # à 2 px sous un overflow:hidden.
    assert "min-height: 22px" in css.split(".plaque-rang {", 1)[1]
    # et la liste borne sa propre hauteur, sinon un modèle à cinquante nœuds
    # chasse les boutons d'isolation hors du rail
    assert "max-height" in css.split(".plaque-liste {", 1)[1].split("}", 1)[0]


def test_les_noeuds_sans_geometrie_sont_COMPTES_ET_DITS():
    """`vides` est le jumeau de `partages` : une mesure que la plaque fait et
    que le panneau doit DIRE. Sur un modèle à pivot vide, le panneau Parties
    liste treize nœuds et la plaque en montre douze — sans un mot, l'écart se
    lit comme une pièce perdue.

    Le champ était rendu par `etaler` et lu par PERSONNE. Une surface publique
    morte est une promesse qu'on croira tenue : soit on la dit, soit on la
    retire. On la dit, comme `partages`.
    """
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    # il est COMPTÉ dans le module...
    assert "vides++" in _code("lib3d/plaque.js")
    assert "partages, vides," in _code("lib3d/plaque.js")
    # ...REMONTÉ jusqu'à l'état du panneau...
    assert "PLQ.vides = etalement.vides;" in code
    # L'ancre etait `vides: 0 };`, soit la FIN de la declaration de PLQ, et
    # elle a rougi a la tache « vue isometrique », qui y ajoute `axe`. Ce que
    # ce banc veut dire, c'est que `vides` est DECLARE dans PLQ — pas qu'il en
    # est la derniere cle. On garde le deux-points, seul a distinguer la
    # declaration (`vides: 0,`) des remises a zero d'oublierPlaque()
    # (`PLQ.vides = 0;`), et on lache l'accolade.
    assert "vides: 0," in code
    # ...et DIT à l'écran, dans la même note que `partages`.
    liste = _plaque_liste()
    assert "PLQ.vides" in liste
    assert "sans géométrie ne sont pas étalés" in js


def test_l_oeil_NE_TOUCHE_PAS_a_la_selection_du_panneau_Parties():
    """LE JUGEMENT DE LA TÂCHE, ÉPINGLÉ. Masquer et retenir ne veulent pas
    dire la même chose et ne durent pas aussi longtemps : `SEL.retenus` est la
    CHARGE que separerSelection() convertit en index de nœud et met en file
    pour le serveur, QUI ÉCRIT UN GLB ; la visibilité est un geste d'écran,
    qui meurt au retour à « Assemblé ». Les confondre ferait perdre trois
    pièces d'une extraction à qui masque trois pièces pour mieux voir les
    autres — en silence, le mode d'échec que cette page traque partout.

    Deux raisons de plus, mécaniques : `SEL.retenus` est VIDÉ à chaque
    changement de granularité, si bien que l'œil perdrait son état en passant
    sur l'onglet « matériau » ; et la plaque ne connaît qu'une granularité, le
    NŒUD, quand le panneau en offre trois.

    CE QUI EST PARTAGÉ, et qui suffit : la COULEUR. Chaque rangée du panneau
    porte la pastille de la pièce dont elle fait partie, si bien que le nom
    qu'on coche est visiblement la pièce qu'on voit sur le plateau — sans
    qu'aucun état ne soit dupliqué.

    MUTATION VÉRIFIÉE : ajouter `SEL.retenus.delete(cle);` dans l'écouteur de
    l'œil fait rougir ce banc, et lui seul.
    """
    code = _code("etabli/etabli.js")
    oeil = code.split('querySelectorAll(".plaque-oeil")', 1)[1] \
               .split('$("#btnIsoler")', 1)[0]
    assert "SEL" not in oeil
    assert "PLQ.masquees" in oeil
    # côté module, l'œil ne touche QUE `visible` : ni opacité (qui passerait
    # par les matériaux, donc par la limite du partage), ni retrait de la
    # scène (qui ferait perdre sa place à la pièce).
    pl = _code("lib3d/plaque.js")
    mp = pl.split("export function montrerPiece", 1)[1].split("\n}\n", 1)[0]
    assert "e.piece.visible = !!visible;" in mp
    for interdit in ("opacity", "material", "remove("):
        assert interdit not in mp, interdit
    # LE PONT, et il est le seul : la teinte d'une pièce descend sur les
    # rangées de son sous-arbre. Sans lui, le panneau et la plaque parleraient
    # des mêmes pièces sans qu'on puisse les rapprocher de l'œil.
    assert "PLQ.teintes.get(x.uuid)" in code
    assert "teintes.set(o.uuid, css)" in pl


def test_la_liste_de_la_plaque_echappe_les_noms_venus_du_GLB():
    """Les noms de pièces viennent du FICHIER GLB, donc du dehors. Ce fichier
    s'est donné la règle que tout ce qui entre dans innerHTML passe par esc(),
    et les attributs data- ne font pas exception : c'est même là qu'un
    guillemet casse la ligne entière.
    """
    bloc = _plaque_liste()
    assert "esc(x.nom)" in bloc
    assert "esc(x.cle)" in bloc
    assert "esc(x.couleur)" in bloc
    # aucune interpolation NUE de ce qui vient du fichier
    assert "${x.nom}" not in bloc
    assert "${x.couleur}" not in bloc


# ── N (suite). le CHOIX DES PIÈCES, EXÉCUTÉ et non lu ────────────────────────
# CE QUE LE BANC DE TEXTE N'A PAS PU VOIR, et il faut le dire en tête. La
# première livraison étalait « les nœuds glTF les plus HAUTS ». Mesurée dans
# un vrai navigateur sur le modèle réel de l'utilisateur (model.v5.glb, 12
# pièces, 144 274 triangles), elle rendait UN berceau, décalé de (0, 0) : la
# carte restait debout, entière, sur le plateau.
#
# La cause n'est pas un cas particulier. L'arbre réel est
#
#     Group      "carte3d"
#       Object3D "etabli_correction" [gltf 13]
#         Object3D "carte3d_1"       [gltf 12]
#           Mesh "fond-matiere" [gltf 0] … douze maillages [gltf 0..11]
#
# et ce nœud d'enveloppe vient de `mesh_edit.reparer`, qui en AJOUTE UN À
# CHAQUE FOIS (`doc.setdefault("nodes", []).append(...)`). Tout modèle passé
# par « Réparer l'assise » — le cas COURANT, pas le rare — n'a donc qu'un seul
# nœud au sommet, et la plaque n'étalait rien pour lui.
#
# Les vingt mutations de la section N étaient sérieuses, et le rangement avait
# été mesuré hors navigateur sur douze boîtes ; le défaut était EN AMONT du
# rangement, dans le CHOIX DES PIÈCES, et rien ne l'exerçait. La leçon est
# celle que test_cards_capture a déjà payée : une règle se lit mal et
# s'EXÉCUTE bien. `piecesDe` ne touche à aucune API de three.js — elle ne lit
# que `children`, `traverse`, `userData`, `isMesh`, `geometry` — donc elle
# tourne dans node sur de faux objets, exactement comme rangerEnEtageres() se
# mesurait déjà.


def _fonction_plaque(nom: str) -> str:
    """La fonction ENTIÈRE de plaque.js, prête à tourner dans node.

    Extraite de la VRAIE source, jamais recopiée ici : une copie de la règle
    est une règle qui dérive, et le banc jurerait alors sur un texte que
    personne n'exécute.
    """
    js = _lire("lib3d/plaque.js")
    i = js.index("export function " + nom + "(")
    j = js.index("\n}\n", i)
    return js[i:j + 2].replace("export function", "function", 1)


def _resoudre(a, d):
    """Résout A·x = d par élimination de Gauss avec pivot partiel.

    SECOND ALGORITHME, délibérément : `versLocalLineaire` inverse par les
    cofacteurs, et recopier cette même algèbre ici n'aurait vérifié qu'une
    faute de frappe. Deux chemins qui tombent sur le même nombre, c'est une
    mesure ; un seul chemin écrit deux fois, c'est un écho.
    """
    m = [list(ligne) + [v] for ligne, v in zip(a, d)]
    n = len(m)
    for col in range(n):
        piv = max(range(col, n), key=lambda r: abs(m[r][col]))
        m[col], m[piv] = m[piv], m[col]
        assert abs(m[col][col]) > 1e-12, "matrice singuliere"
        for r in range(n):
            if r == col:
                continue
            k = m[r][col] / m[col][col]
            for c in range(col, n + 1):
                m[r][c] -= k * m[col][c]
    return [m[r][n] / m[r][r] for r in range(n)]


def _constantes_plaque(*noms: str) -> str:
    """Les constantes de plaque.js, VERBATIM, pour le harnais node.

    Elles ne sont PAS recopiées ici : une valeur recopiée est une valeur qui
    dérive, et le harnais mesurerait alors un seuil que le module n'applique
    plus. Le défaut s'est présenté tout de suite — le premier harnais avait
    posé `SEUIL_APLATI = 0.5` à la main dans un banc et l'avait oublié dans
    l'autre, qui est mort sur un ReferenceError plutôt que de mentir ; la
    prochaine fois il aurait pu mentir.
    """
    js = _lire("lib3d/plaque.js")
    bouts = []
    for n in noms:
        m = re.search(r"^const " + n + r" = .*?;$", js, re.M)
        assert m, f"constante {n} introuvable dans plaque.js"
        bouts.append(m.group(0))
    return "\n".join(bouts) + "\n"


def _node(source: str) -> str:
    """Exécute du JS dans node et rend sa sortie.

    OPTIONNEL, comme le `_node` de test_cards_capture : sur une machine sans
    node le contrôle se saute plutôt que de rougir pour une raison qui n'est
    pas la sienne.
    """
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : la règle ne peut pas être EXÉCUTÉE ici")
    r = subprocess.run([node, "-e", source], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:600]
    return r.stdout.decode("utf-8", "replace")


# Le faux Object3D : le contrat MINIMAL que piecesDe consomme. L'écrire en
# entier ici est délibéré — c'est la liste exacte de ce que la fonction a le
# droit de supposer, et le jour où elle supposera davantage, ce harnais
# rougira au lieu de la laisser dépendre en douce de three.js.
_FAUX_ARBRE = """
function N(nom, opt) {
  opt = opt || {};
  const o = {
    name: nom, children: [], parent: null,
    userData: (opt.index === undefined ? {} : { indexGltf: opt.index }),
    isMesh: !!opt.mesh, geometry: (opt.mesh ? { attributes: {} } : null),
  };
  o.traverse = function (f) {
    f(this);
    for (const c of this.children) c.traverse(f);
  };
  o.add = function (c) { c.parent = this; this.children.push(c); return this; };
  return o;
}
const noms = (l) => l.map((o) => o.name).join(",");
"""


def test_les_pieces_sont_CELLES_DU_PANNEAU_et_non_l_enveloppe_de_reparation():
    """LE BANC QUI MANQUAIT, ET IL EST EXÉCUTÉ.

    L'arbre est celui du modèle réel de l'utilisateur, enveloppe de
    `mesh_edit.reparer` comprise. La plaque doit rendre les DOUZE pièces que
    le panneau Parties montre — `fond-matiere`, `illustration`, `cadre`… — et
    non l'unique nœud d'enveloppe qui les contient toutes.

    Avant correctif ce banc rendait 1 : vérifié par mutation (rétablir la
    règle « les plus hauts » le fait rougir).
    """
    sortie = _node(_fonction_plaque("piecesDe") + _FAUX_ARBRE + """
      const racine = N("carte3d");
      const env = N("etabli_correction", { index: 13 });
      const grp = N("carte3d_1", { index: 12 });
      racine.add(env); env.add(grp);
      const feuilles = ["fond-matiere", "illustration", "cadre",
        "typographie", "ornements", "lisere",
        "fond-matiere_verso", "illustration_verso", "cadre_verso",
        "typographie_verso", "ornements_verso", "lisere_verso"];
      feuilles.forEach((n, i) => grp.add(N(n, { index: i, mesh: true })));
      const p = piecesDe({ racine });
      console.log(p.length + "|" + noms(p));
    """)
    combien, noms = sortie.strip().split("|")
    assert int(combien) == 12, f"{combien} pièce(s) au lieu de 12 : {noms}"
    assert "fond-matiere" in noms and "typographie_verso" in noms
    # et surtout PAS les contenants : ce sont des enveloppes, pas des volumes.
    # Les étaler ferait voyager la carte entière d'un bloc — le défaut mesuré.
    assert "etabli_correction" not in noms
    assert "carte3d_1" not in noms


def test_un_maillage_MULTI_PRIMITIVES_reste_UNE_piece():
    """LA MÉCANIQUE QU'IL NE FALLAIT PAS CASSER en changeant de cible.

    Chez GLTFLoader, un nœud à plusieurs primitives donne un Group pour le
    nœud et un Mesh par primitive — et ces Mesh n'ont PAS de `nodes` dans
    `parser.associations`, indexerNoeuds() refusant délibérément de leur en
    inventer un. C'est le cas ordinaire d'un Meshy.

    Étaler « les maillages » au sens littéral aurait donc produit des pièces
    SANS index de nœud : sans clé, pas de teinte stable, pas d'œil, et rien
    que le serveur sache nommer le jour où on extrait. La pièce reste le
    NŒUD ; ses primitives voyagent avec lui.
    """
    sortie = _node(_fonction_plaque("piecesDe") + _FAUX_ARBRE + """
      const racine = N("carte3d");
      const noeud = N("meshy_0", { index: 5 });
      racine.add(noeud);
      noeud.add(N("prim_0", { mesh: true }));
      noeud.add(N("prim_1", { mesh: true }));
      const p = piecesDe({ racine });
      console.log(p.length + "|" + noms(p));
    """)
    combien, noms = sortie.strip().split("|")
    assert int(combien) == 1, f"{combien} pièce(s) : {noms}"
    assert noms == "meshy_0"


def test_un_noeud_indexe_SANS_geometrie_n_est_pas_une_piece():
    """Un pivot, un contenant vide : il occuperait une case sans rien y
    montrer, et son œil ne commanderait rien de visible. Le décor est celui
    qui piège — le pivot est une FEUILLE indexée, donc « le plus bas » au sens
    du parcours ; seule la géométrie le disqualifie.
    """
    sortie = _node(_fonction_plaque("piecesDe") + _FAUX_ARBRE + """
      const racine = N("carte3d");
      racine.add(N("pivot_vide", { index: 7 }));
      racine.add(N("piece_pleine", { index: 8, mesh: true }));
      const p = piecesDe({ racine });
      console.log(p.length + "|" + noms(p));
    """)
    combien, noms = sortie.strip().split("|")
    assert int(combien) == 1, f"{combien} pièce(s) : {noms}"
    assert noms == "piece_pleine"


def test_AUCUNE_piece_n_en_contient_une_autre():
    """LE DANGER QUE L'ANCIENNE RÈGLE GARDAIT, et qui doit rester gardé sous
    la nouvelle : deux pièces imbriquées recevraient deux berceaux, et le
    décalage de la fille s'ajouterait à celui de sa mère — elle partirait deux
    fois plus loin que sa voisine, pour une raison invisible.

    L'ancienne règle (« les plus hauts ») l'interdisait par construction. La
    nouvelle aussi, par l'argument SYMÉTRIQUE : une pièce n'a aucun nœud
    indexé porteur en dessous d'elle, donc elle n'en contient aucune. Le banc
    l'EXÉCUTE sur un arbre à trois étages tous indexés et porteurs, plutôt que
    de croire l'argument.
    """
    sortie = _node(_fonction_plaque("piecesDe") + _FAUX_ARBRE + """
      const racine = N("r");
      const a = N("a", { index: 1, mesh: true });
      const b = N("b", { index: 2, mesh: true });
      const c = N("c", { index: 3, mesh: true });
      racine.add(a); a.add(b); b.add(c);
      const p = piecesDe({ racine });
      const dedans = p.some((x) => p.some((y) => {
        if (x === y) return false;
        let trouve = false;
        y.traverse((n) => { if (n === x) trouve = true; });
        return trouve;
      }));
      console.log(p.length + "|" + noms(p) + "|" + dedans);
    """)
    combien, noms, dedans = sortie.strip().split("|")
    assert dedans == "false", f"des pièces imbriquées : {noms}"
    assert int(combien) == 1 and noms == "c"


# ── N (suite). le PLAN d'étalement, mesuré sur le GLB réel ───────────────────
# LA SECONDE ERREUR DE CETTE TÂCHE, et le banc qui la garde.
#
# Choisir les bonnes pièces ne suffisait pas : encore fallait-il les étaler
# dans un plan où elles se voient. La première écriture étalait toujours au
# SOL (x, z), en supposant des volumes posés sur un plateau d'imprimante. Les
# douze pièces du modèle réel de l'utilisateur sont des PLANS — mesurées hors
# navigateur en lisant directement le GLB (assets3d/6e0a8a5f/model.v5.glb,
# 9 442 200 octets, 14 nœuds, 12 maillages) :
#
#     fond-matiere        x=0,0630  y=0,0880  z=0,0000
#     illustration        x=0,0630  y=0,0880  z=0,0000
#     cadre               x=0,0630  y=0,0880  z=0,0011
#     … les douze pareil, épaisseur nulle à un cadre près
#
# Leur empreinte AU SOL vaut donc largeur × zéro. Passées au vrai rangeur,
# elles donnaient DOUZE ÉTAGÈRES D'UNE PIÈCE : douze plans coplanaires empilés
# le long de l'axe de vue, à 0,0076 l'un de l'autre. La caméra les regarde
# précisément par cet axe — l'utilisateur aurait revu UNE carte, à peine
# éventée. Étaler des pièces qui se cachent les unes les autres n'étale rien.
#
# Les constantes ci-dessous sont donc des MESURES, pas des exemples. Elles
# valent contrat : si le rangement cesse un jour de les mettre en grille, ce
# banc rougit sur le modèle même de l'utilisateur.

# Les douze pièces du modèle réel, telles que lues dans le GLB.
_CARTE_REELLE = ("[" + ", ".join(
    "{x: 0.0630, y: 0.0880, z: %s}" % ("0.0011" if i == 3 else "0.0000")
    for i in range(12)) + "]")


def test_le_plan_d_etalement_se_choisit_sur_les_PIECES_et_non_sur_le_sol():
    """L'axe d'empilement est celui sur lequel les pièces n'ont pas d'étendue.

    Avec HYSTÉRÉSIS : on ne quitte le plancher (y) que pour un modèle
    FRANCHEMENT aplati. Sans elle, un modèle quasi cubique verrait son plan
    basculer au gré du bruit de mesure, et deux chargements du même maillage
    ne se ressembleraient plus — la stabilité que la teinte par angle d'or
    cherche déjà par ailleurs.
    """
    sortie = _node(_constantes_plaque("AXES", "SEUIL_APLATI")
                   + _fonction_plaque("axeEmpile") + """
      const rep = (l) => axeEmpile(l);
      const rep3 = (x, y, z) => rep([{x,y,z},{x,y,z},{x,y,z}]);
      console.log([
        rep(%s),          // la carte reelle : plans dans XY
        rep3(1, 1, 1),    // cubique : on garde le plancher
        rep3(1, 1, 0.6),  // a peine aplati : hysteresis, plancher
        rep3(1, 1, 0.2),  // franchement aplati : on bascule
        rep3(0.1, 1, 1),  // aplati en X
        rep3(1, 0.2, 1),  // aplati en Y : c'est deja le plancher
      ].join(","));
    """ % _CARTE_REELLE)
    reel, cube, presque, plat, platX, platY = sortie.strip().split(",")
    # LE CAS QUI COMPTE : le modèle de l'utilisateur s'étale dans SON plan.
    assert reel == "z", f"la carte reelle s'etalerait dans le plan {reel}"
    assert cube == "y" and presque == "y"      # hystérésis : le plancher tient
    assert plat == "z" and platX == "x" and platY == "y"


def test_les_douze_pieces_REELLES_forment_une_GRILLE_et_non_une_pile():
    """LE BANC QUI MANQUAIT LA SECONDE FOIS, et il est exécuté sur les cotes
    VRAIES. Il enchaîne les deux fonctions pures — le choix du plan puis le
    rangement — exactement comme etaler() les enchaîne, et vérifie ce que
    l'utilisateur verra : plusieurs pièces PAR RANGÉE, aucune sur une autre.

    Mesuré après correctif : trois étagères de quatre, empreinte
    0,2837 × 0,2851 (presque carrée), zéro chevauchement. Avant correctif :
    douze étagères d'une pièce.

    Le seuil est posé à « au moins trois par rangée » plutôt qu'à « exactement
    4+4+4 » : c'est la LISIBILITÉ qui est promise, pas un pavage. Une retouche
    de l'élancement ne doit pas rougir ; un retour à la pile, si.
    """
    sortie = _node(
        _constantes_plaque("AXES", "SEUIL_APLATI", "ELANCEMENT",
                           "MARGE_RELATIVE")
        + _fonction_plaque("axeEmpile")
        + _fonction_plaque("rangerEnEtageres") + """
      const tailles = %s;
      const axe = axeEmpile(tailles);
      const [a1, a2] = AXES.filter((a) => a !== axe);
      const boites = tailles.map((t, i) => ({ cle: i, l: t[a1], p: t[a2] }));
      const marge = MARGE_RELATIVE * Math.max(...boites.map(
        (b) => Math.max(b.l, b.p)));
      const r = rangerEnEtageres(boites, marge);
      const rangs = new Map();
      for (const p of r.places) {
        const k = (p.z - p.p / 2).toFixed(6);
        rangs.set(k, (rangs.get(k) || 0) + 1);
      }
      let chevauchements = 0;
      for (let i = 0; i < r.places.length; i++) {
        for (let j = i + 1; j < r.places.length; j++) {
          const a = r.places[i], b = r.places[j];
          if (Math.abs(a.x - b.x) - (a.l + b.l) / 2 < -1e-9
           && Math.abs(a.z - b.z) - (a.p + b.p) / 2 < -1e-9) chevauchements++;
        }
      }
      console.log([...rangs.values()].join("+") + "|" + chevauchements
        + "|" + r.largeur.toFixed(4) + "|" + r.profondeur.toFixed(4));
    """ % _CARTE_REELLE)
    etageres, chev, largeur, profondeur = sortie.strip().split("|")
    rangees = [int(n) for n in etageres.split("+")]
    assert int(chev) == 0, f"des pièces se chevauchent : {etageres}"
    assert sum(rangees) == 12, etageres
    # PLUSIEURS par rangée : c'est tout l'écart entre une grille et une pile.
    assert len(rangees) > 1, f"une seule étagère : {etageres}"
    assert min(rangees) >= 3, \
        f"des rangées trop maigres ({etageres}) : on retombe vers la pile"
    # et l'empreinte reste à peu près carrée — un bandeau de douze cartes
    # obligerait à dézoomer jusqu'à ne plus rien distinguer.
    rapport = float(largeur) / float(profondeur)
    assert 0.4 < rapport < 2.5, f"empreinte {largeur} x {profondeur}"


def test_le_plateau_BASCULE_avec_le_plan_et_recule_d_un_cheveu():
    """La grille de GridHelper naît dans le plan XZ, normale +Y. Laissée là
    quand les pièces s'étalent dans XY, elle serait vue PAR LA TRANCHE — un
    trait, sous des cartes qui flottent. Elle bascule donc avec le plan.

    ET ELLE RECULE. Les pièces sont posées AU CONTACT du plateau (leur minimum
    sur l'axe d'empilement vaut zéro), or les pièces mesurées ont une épaisseur
    NULLE : coplanaires, la carte et la grille clignoteraient (z-fighting).
    C'est un défaut qu'aucun banc de texte ne peut voir et qu'un recul d'un
    cheveu supprime.
    """
    code = _code("lib3d/plaque.js")
    pp = code.split("function poserPlateau", 1)[1].split("\n}\n", 1)[0]
    assert "groupe.rotation.x = Math.PI / 2;" in pp
    assert "groupe.rotation.z = -Math.PI / 2;" in pp
    assert "groupe.position[axe] = -cote * RECUL_PLATEAU;" in pp
    assert "const RECUL_PLATEAU" in code
    # et le plan choisi ARRIVE vraiment jusqu'au plateau : sans cet argument,
    # la grille resterait au sol pendant que les pièces s'étalent ailleurs.
    assert ("poserPlateau(\n    api, mise.largeur, mise.profondeur, "
            "mise.marge, mise.axe)") in code


def test_la_MISE_EN_PLACE_des_douze_pieces_REELLES_est_EXECUTEE():
    """LE BANC DE BOUT EN BOUT, sur les cotes VRAIES du modèle de
    l'utilisateur — lues dans son GLB, minimums et centres compris (la
    douzième pièce, `ornements_verso`, est miroir des onze autres : son centre
    diffère, et c'est elle qui exerce l'arithmétique).

    POURQUOI CE BANC EXISTE. Deux erreurs de suite sont passées dans cette
    tâche : les mauvaises pièces, puis le mauvais plan. Toutes deux vivaient
    dans le câblage d'etaler(), qui manipule des Object3D et ne tourne donc
    que dans un navigateur ; aucun miroir de texte ne pouvait les voir. La
    décision a été SORTIE dans `disposer`, pure, et la voici EXÉCUTÉE. Ce que
    ce banc vérifie est ce que l'utilisateur verra :

      - l'étalement se fait dans le plan des pièces (z est l'axe d'empilement),
      - aucune pièce n'en recouvre une autre,
      - plusieurs pièces PAR RANGÉE — une grille, pas une pile,
      - et chacune est posée AU CONTACT du plateau.
    """
    sortie = _node(
        _constantes_plaque("AXES", "SEUIL_APLATI", "ELANCEMENT",
                           "MARGE_RELATIVE")
        + _fonction_plaque("axeEmpile")
        + _fonction_plaque("rangerEnEtageres")
        + _fonction_plaque("disposer") + """
      // Les douze pièces de assets3d/6e0a8a5f/model.v5.glb, lues dans le GLB.
      // Toutes 0,0630 × 0,0880 × ~0 : des PLANS, pas des volumes.
      const zmin = [-0.00073, -0.00038, -0.00003, -0.00073, 0.00067, 0.00102,
                    -0.00073, -0.00078, -0.00060, -0.00092, 0.00054, 0.00108];
      const zhaut = [0, 0, 0, 0.0011, 0, 0, 0, 0, 0, 0, 0, 0];
      const mesurees = zmin.map((zm, i) => ({
        cle: i,
        taille: { x: 0.0630, y: 0.0880, z: zhaut[i] },
        // la douzième est miroir : centre opposé en x et en y
        centre: { x: i === 11 ? -0.01407 : 0.01407,
                  y: i === 11 ? 0.01213 : -0.01213,
                  z: zm + zhaut[i] / 2 },
        bas: { x: i === 11 ? -0.04557 : -0.01743, y: -0.05613 + (i === 11 ? 0.02426 : 0),
               z: zm },
      }));
      const m = disposer(mesurees);
      const AX = ["x", "y", "z"];
      const [a1, a2] = AX.filter((a) => a !== m.axe);
      const boites = mesurees.map((p) => {
        const d = m.decalages.get(p.cle);
        return {
          u: p.centre[a1] + d[a1], v: p.centre[a2] + d[a2],
          l: p.taille[a1], w: p.taille[a2],
          contact: p.bas[m.axe] + d[m.axe],
        };
      });
      let chevauchements = 0;
      for (let i = 0; i < boites.length; i++) {
        for (let j = i + 1; j < boites.length; j++) {
          const a = boites[i], b = boites[j];
          if (Math.abs(a.u - b.u) - (a.l + b.l) / 2 < -1e-9
           && Math.abs(a.v - b.v) - (a.w + b.w) / 2 < -1e-9) chevauchements++;
        }
      }
      const rangs = new Map();
      for (const b of boites) {
        const k = (b.v - b.w / 2).toFixed(6);
        rangs.set(k, (rangs.get(k) || 0) + 1);
      }
      const horsPlateau = boites.filter(
        (b) => Math.abs(b.contact) > 1e-9).length;
      console.log([m.axe, chevauchements, [...rangs.values()].join("+"),
                   horsPlateau, boites.length].join("|"));
    """)
    axe, chev, etageres, hors, combien = sortie.strip().split("|")
    assert int(combien) == 12, combien
    # LE CAS QUI COMPTE : la carte s'étale dans SON plan, pas au sol.
    assert axe == "z", f"axe d'empilement {axe}"
    assert int(chev) == 0, f"des pièces se recouvrent : {etageres}"
    rangees = [int(n) for n in etageres.split("+")]
    assert len(rangees) > 1, f"une seule étagère : {etageres}"
    # PLUSIEURS par rangée : tout l'écart entre une grille et une pile. Avant
    # correctif, c'étaient douze rangées d'UNE pièce.
    assert min(rangees) >= 3, \
        f"des rangées trop maigres ({etageres}) : on retombe vers la pile"
    # et chaque pièce touche le plateau : son minimum sur l'axe d'empilement
    # tombe exactement à zéro.
    assert int(hors) == 0, f"{hors} pièce(s) ne touchent pas le plateau"


def test_le_decalage_se_convertit_dans_l_espace_du_parent_EN_Z_UP():
    """LE DERNIER MAILLON DE LA CHAÎNE DE PLACEMENT, et il dormait.

    `versLocal` ramène le décalage d'étalement dans l'espace local du parent.
    Sur le modèle mesuré il ne fait RIEN : `mesh_edit._ROT["Y"]` est
    l'identité, donc une réparation en Y à l'échelle 1 le rend transparent, et
    le remplacer par le décalage brut ne changerait pas un pixel. Une mesure
    en navigateur ne pouvait donc pas le voir.

    Mais « Z (Blender, Unreal) » est une option de premier rang du panneau
    Fiche. Choisie, l'enveloppe de réparation porte une rotation de 90° et
    TOUTES les pièces vivent dessous : cette conversion est alors la seule
    chose qui tienne, et sans elle l'étalement enverrait chaque pièce à un
    autre endroit que sa case.

    LA MATRICE N'EST PAS RECOPIÉE ICI : elle est produite par le vrai
    `_matrice(_ROT[...], s, t)` de mesh_edit. Le jour où la convention Z-up
    change côté serveur, ce banc suit — une matrice recopiée, elle, aurait
    mesuré une convention que plus personne n'applique.
    """
    from app.services.mesh_edit import _ROT, _matrice

    def js_liste(m):
        return "[" + ", ".join(repr(float(x)) for x in m) + "]"

    zup = _matrice(_ROT["Z"], 1.0, (0.0, 0.0, 0.0))
    zup2 = _matrice(_ROT["Z"], 2.0, (7.0, 8.0, 9.0))
    yup = _matrice(_ROT["Y"], 1.0, (0.0, 0.0, 0.0))
    # UNE MATRICE QUELCONQUE, et elle n'est pas décorative. Les matrices de
    # `_matrice` sont creuses — une rotation d'axe porte six zéros — si bien
    # qu'une faute d'indice tombe le plus souvent sur un zéro et ne se voit
    # pas. MESURÉ : intervertir les colonnes et les lignes de la lecture
    # (`e[4]` lu en `e[1]`) laissait ce banc VERT sur les seules matrices de
    # mesh_edit. Celle-ci a ses neuf coefficients distincts et non nuls, et
    # une échelle non uniforme : aucune faute d'indice n'y passe.
    quelconque = [2.0, 0.0, 1.0, 0.0,
                  1.0, 3.0, 0.0, 0.0,
                  0.0, 1.0, 4.0, 0.0,
                  11.0, 12.0, 13.0, 1.0]
    sortie = _node(_fonction_plaque("versLocalLineaire") + """
      const p = (o) => [o.x, o.y, o.z].map((v) => v.toFixed(4)).join(",");
      console.log([
        p(versLocalLineaire(%s, {x: 3, y: 5, z: 7})),
        p(versLocalLineaire(%s, {x: 3, y: 5, z: 7})),
        p(versLocalLineaire(%s, {x: 3, y: 5, z: 7})),
        p(versLocalLineaire([0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1],
                            {x: 3, y: 5, z: 7})),
        p(versLocalLineaire(%s, {x: 3, y: 5, z: 7})),
      ].join("|"));
    """ % (js_liste(zup), js_liste(zup2), js_liste(yup),
           js_liste(quelconque)))
    z, z2, y, degenere, gen = sortie.strip().split("|")
    # Z-up envoie +Y sur +Z : (x, y, z) -> (x, -z, y). L'inverse rend donc
    # (3, 5, 7) sous la forme (3, 7, -5).
    assert z == "3.0000,7.0000,-5.0000", z
    # l'ÉCHELLE compte aussi, et la TRANSLATION du parent ne doit PAS compter :
    # un décalage est un vecteur, pas un point.
    assert z2 == "1.5000,3.5000,-2.5000", z2
    # en Y-up — le cas mesuré — la conversion est un no-op, et c'est
    # exactement pourquoi elle a besoin d'un banc plutôt que d'un navigateur.
    assert y == "3.0000,5.0000,7.0000", y
    # un parent écrasé à zéro n'a pas d'inverse : on rend le décalage tel quel
    # plutôt que des NaN, qui feraient disparaître la pièce sans un mot.
    assert degenere == "3.0000,5.0000,7.0000", degenere
    # LE CONTRÔLE CROISÉ : la réponse attendue est calculée ICI, par une
    # élimination de Gauss — un SECOND algorithme, pas la même algèbre des
    # cofacteurs recopiée en Python, qui n'aurait rien vérifié du tout.
    a = [[2.0, 1.0, 0.0], [0.0, 3.0, 1.0], [1.0, 0.0, 4.0]]
    attendu = _resoudre(a, [3.0, 5.0, 7.0])
    assert gen == ",".join(f"{v:.4f}" for v in attendu), (gen, attendu)


def test_le_placement_PASSE_par_le_helper_pur():
    """Le miroir qui interdit de contourner le helper : sans lui, la
    conversion retournerait dans du three.js, hors de portée de tout banc —
    et c'est précisément la catégorie qui a laissé passer deux défauts.
    """
    code = _code("lib3d/plaque.js")
    vl = code.split("function versLocal(parent, deltaMonde)", 1)[1] \
             .split("\n}\n", 1)[0]
    assert "versLocalLineaire(parent.matrixWorld.elements, deltaMonde)" in vl
    # la part calculatoire est PURE : c'est ce qui la rend exécutable
    pur = code.split("export function versLocalLineaire", 1)[1] \
              .split("\n}\n", 1)[0]
    assert "THREE." not in pur
    # et le placement l'emprunte vraiment
    et = code.split("export function etaler(api, plan = null)", 1)[1].split("\n}\n", 1)[0]
    assert "versLocal(parent, decalage)" in et


def test_le_cablage_d_etaler_PASSE_par_la_mise_en_place():
    """Le miroir de texte qui reste, et il ne garde qu'une chose : que le
    câblage d'etaler() consomme bien `disposer` plutôt que de refaire le
    calcul au sol. Le COMPORTEMENT est gardé par le banc exécuté plus haut ;
    celui-ci interdit qu'on le contourne.
    """
    code = _code("lib3d/plaque.js")
    et = code.split("export function etaler(api, plan = null)", 1)[1].split("\n}\n", 1)[0]
    assert "const mise = disposer(mesurees);" in et
    assert "const d = mise.decalages.get(m.cle);" in et
    assert "new THREE.Vector3(d.x, d.y, d.z)" in et
    # et rien n'est plus décidé sur place : ni plan, ni marge, ni rangement
    for refait in ("axeEmpile(", "rangerEnEtageres(", "MARGE_RELATIVE"):
        assert refait not in et, refait
    # `disposer`, elle, ne connaît pas three.js : c'est ce qui la rend
    # mesurable, et c'est la leçon des deux défauts de cette tâche.
    dis = code.split("export function disposer(mesurees)", 1)[1] \
              .split("\n}\n", 1)[0]
    assert "THREE." not in dis
    assert "d[axe] = -m.bas[axe];" in dis


# ── O. le point de vue : perspective ⇄ isométrique, face/dessus/profil ───────
# CE QUE LE BANC-MIROIR NE PEUT PAS VOIR, et il faut le dire en tête. Une
# OrthographicCamera n'a ni `fov` ni `aspect` ; lui en lire un rend `undefined`
# (donc NaN, donc écran noir) et lui en écrire un ne fait RIEN. Aucune de ces
# deux pannes ne lève, aucune n'apparaît en console, aucune ne rougit un banc
# de texte. La section se tient donc sur deux jambes :
#   — des MARQUEURS, pour les câblages qu'un texte peut voir (la boucle rend la
#     caméra active, les contrôles et le gizmo reçoivent la nouvelle caméra, la
#     synchronisation A/B ne recopie pas un `fov` à une ortho) ;
#   — des RÈGLES PURES EXÉCUTÉES dans node, sur des nombres, pour tout ce qui
#     décide de la géométrie. Le cadrage d'une ortho n'est PAS le cadrage d'une
#     perspective transposé : la demi-hauteur s'y rend en BORDS et non en
#     distance, et le seuil de rognage change avec la direction de vue.


def _fonction_viewer(nom: str) -> str:
    """La fonction ENTIÈRE de viewer.js, prête à tourner dans node.

    Extraite de la VRAIE source, jamais recopiée ici — même règle que
    `_fonction_plaque` : une copie de la règle est une règle qui dérive.

    EXPORTÉE OU NON, indifféremment, et ce n'est pas un détail de confort : la
    première écriture ne cherchait que « export function », si bien que deux
    règles internes portaient un `export` dont le SEUL motif était d'être
    lisibles ici. Un extracteur de banc n'a pas à façonner la surface publique
    d'un module partagé — il lit, il ne demande rien.
    """
    js = _lire("lib3d/viewer.js")
    m = re.search(r"^(?:export )?function " + nom + r"\(", js, re.M)
    assert m, f"fonction {nom} introuvable dans viewer.js"
    j = js.index("\n}\n", m.start())
    return js[m.start():j + 2].replace("export function", "function", 1)


def _table_js(rel: str, nom: str) -> str:
    """Une table `const NOM = { … };` d'un fichier, VERBATIM.

    Même motif que `_constantes_plaque` : recopier une table dans un banc,
    c'est mesurer un appariement que le code n'applique plus.
    """
    js = _lire(rel)
    i = js.find("const " + nom + " = {")
    assert i >= 0, f"table {nom} introuvable dans {rel}"
    return js[i:js.index("};", i) + 2]


def _fonction_etabli(nom: str) -> str:
    """Une fonction d'etabli.js, VERBATIM, pour le harnais node.

    Ancrée en colonne 0 (`\nfunction x(`) : le nom vit aussi indenté ailleurs,
    et une ancre lâche prendrait un appel pour une définition.
    """
    js = _lire("etabli/etabli.js")
    i = js.find("\nfunction " + nom + "(")
    assert i >= 0, f"fonction {nom} introuvable dans etabli.js"
    return js[i:js.index("\n}\n", i) + 2]


def _harnais_vue() -> str:
    """Les constantes, la table des orientations et les cinq règles pures de
    viewer.js, VERBATIM, prêtes pour node.

    Rien n'est recopié : ni DIR, ni NORME_DIR, ni la table. Le harnais de la
    plaque avait déjà payé la leçon (un SEUIL_APLATI recopié à la main dans un
    banc et oublié dans l'autre). Ici la table des orientations EST le sujet du
    contrôle — la recopier reviendrait à mesurer une table que le module
    n'applique plus.
    """
    js = _lire("lib3d/viewer.js")
    bouts = []
    for n in ("DIR", "NORME_DIR", "HAUT_Y"):
        # `[^\n]*?;` et non `.*?;$` : la ligne de NORME_DIR porte un
        # commentaire `// 1,25` APRÈS le point-virgule.
        m = re.search(r"^const " + n + r" = [^\n]*?;", js, re.M)
        assert m, f"constante {n} introuvable dans viewer.js"
        bouts.append(m.group(0))
    i = js.find("const ORIENTATIONS = {")
    assert i >= 0, "table ORIENTATIONS introuvable dans viewer.js"
    bouts.append(js[i:js.index("\n};", i) + 3])
    for f in ("demiLargeurPireCas", "cadrageDe", "cadreOrtho", "coupeDe",
              "orientationDe"):
        bouts.append(_fonction_viewer(f))
    return "\n".join(bouts) + "\n"


def _normaliser(v):
    n = math.hypot(*v)
    return [c / n for c in v]


def _croix(a, b):
    """Le produit vectoriel, écrit PAR PERMUTATION CIRCULAIRE.

    viewer.js l'écrit en trois lignes d'indices explicites. Le réécrire ici de
    la même façon n'aurait vérifié qu'une faute de frappe recopiée ; sous cette
    forme, un indice interverti là-bas donne un autre nombre ici. Encore
    faut-il l'exercer sur des vecteurs QUELCONQUES : sur les axes de la table
    (deux zéros sur trois) toute permutation d'indices rend le MÊME
    Σ|ri|/|r| — c'est le piège de la matrice creuse, et c'est pour cela que le
    contrôle ci-dessous tire aussi des directions obliques.
    """
    return [a[(i + 1) % 3] * b[(i + 2) % 3] - a[(i + 2) % 3] * b[(i + 1) % 3]
            for i in range(3)]


def _base_lookat(oeil, cible, haut):
    """La base caméra que produit `Matrix4.lookAt` de three.js.

    Reconstruite ici parce que c'est elle, et non une algèbre de notre choix,
    qui décide de ce qui se projette où : z = normalize(oeil − cible),
    x = normalize(haut × z), y = z × x. Rend (droite, haut d'écran, axe de vue).
    """
    z = _normaliser([oeil[k] - cible[k] for k in range(3)])
    x = _normaliser(_croix(haut, z))
    return x, _croix(z, x), z


def _extremes_projetes(demis, droite, haut):
    """Les demi-étendues projetées des HUIT SOMMETS d'une boîte centrée.

    Huit sommets énumérés, et non une somme Σ hi·|ri| : cette dernière est
    justement la formule que `demiLargeurPireCas` applique, et la refaire ici
    n'aurait vérifié qu'une faute de frappe. On projette, on prend le max.
    """
    xs, ys = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            for sz in (-1, 1):
                p = (sx * demis[0], sy * demis[1], sz * demis[2])
                xs.append(sum(p[k] * droite[k] for k in range(3)))
                ys.append(sum(p[k] * haut[k] for k in range(3)))
    return max(abs(v) for v in xs), max(abs(v) for v in ys)


def test_le_pire_cas_de_LARGEUR_est_calcule_PAR_VUE_et_retrouve_le_1_372():
    """LA CONSTANTE DE LA TÂCHE 3 EST DEVENUE UNE FONCTION, et il le fallait.

    `LARGEUR_PIRE_CAS = 1,372` était juste — pour la SEULE direction que la
    caméra savait prendre. Une isométrique la voit sous un autre angle et le
    pire cas y vaut √2 : garder 1,372 aurait rogné l'isométrie de 3,1 % en
    largeur sous le seuil, sans rien casser de visible sinon un modèle coupé.

    Chaque valeur attendue vient d'une FORME FERMÉE différente, pas de la
    fonction testée : la formule littérale de la tâche 3 pour la vue libre,
    √2 pour l'isométrie (le carré de côté 2·rayon vu selon (1,1,1) se projette
    sur une largeur de 2√2·rayon), et 1 pour les trois vues d'axe — un cube
    regardé selon un axe se projette sur un carré de son propre côté.
    """
    attendu = {
        "libre": (0.6 + 1) / math.hypot(0.6, 1),    # la formule de la tâche 3
        "iso": math.sqrt(2),
        "face": 1.0, "dessus": 1.0, "profil": 1.0,
    }
    rendu = json.loads(_node(_harnais_vue() + """
      const o = {};
      for (const n of Object.keys(ORIENTATIONS))
        o[n] = demiLargeurPireCas(ORIENTATIONS[n].dir, ORIENTATIONS[n].haut);
      console.log(JSON.stringify(o));
    """))
    assert set(rendu) == set(attendu), rendu
    for n, v in attendu.items():
        assert abs(rendu[n] - v) < 1e-12, f"{n} : {rendu[n]} au lieu de {v}"
    # Et le SEUIL de la vue libre reste celui que la tâche précédente a mesuré,
    # 0,813030 — la demande exige que ce cadrage-là continue de valoir.
    seuils = json.loads(_node(_harnais_vue() + """
      const o = {};
      for (const n of Object.keys(ORIENTATIONS))
        o[n] = cadrageDe(1, 1, 1.35, ORIENTATIONS[n]).seuil;
      console.log(JSON.stringify(o));
    """))
    assert abs(seuils["libre"] - 0.813030) < 1e-6, seuils["libre"]
    assert abs(seuils["iso"] - 0.838052) < 1e-6, seuils["iso"]
    assert abs(seuils["face"] - 0.592593) < 1e-6, seuils["face"]
    # ── ET SUR DES DIRECTIONS OBLIQUES, ce qui est la moitié du contrôle.
    # Les cinq vues de la table sont des axes ou des diagonales : deux
    # composantes nulles sur trois dans chaque `haut`, si bien qu'un indice
    # interverti dans le produit vectoriel rend EXACTEMENT le même nombre —
    # Σ|ri|/|r| ne dépend pas de l'ordre des composantes. Le contrôle ci-dessus
    # serait donc vert sur une règle fausse. Ces couples-ci n'ont ni zéro, ni
    # orthogonalité, ni norme unité, et la valeur attendue vient d'un produit
    # vectoriel écrit autrement (permutation circulaire, voir _croix).
    obliques = [((0.31, 0.87, -0.42), (0.13, 0.61, 0.28)),
                ((-1.7, 0.25, 0.9), (0.4, -0.9, 0.17)),
                ((2.3, -1.1, 0.6), (-0.21, 0.77, 0.5))]
    src = _harnais_vue() + "const P = " + json.dumps(
        [[list(d), list(h)] for d, h in obliques]) + ";\n" + """
      console.log(JSON.stringify(P.map(([d, h]) => demiLargeurPireCas(
        { x: d[0], y: d[1], z: d[2] }, { x: h[0], y: h[1], z: h[2] }))));
    """
    obtenus = json.loads(_node(src))
    for (d, h), obtenu in zip(obliques, obtenus):
        r = _croix(h, _normaliser(d))
        vise = sum(abs(c) for c in r) / math.hypot(*r)
        assert abs(obtenu - vise) < 1e-12, (d, h, obtenu, vise)
    # et ils sont bien tous DIFFÉRENTS : trois fois la même valeur ne
    # discriminerait rien.
    assert len(set(round(v, 9) for v in obtenus)) == 3, obtenus


def test_le_cadre_ORTHOGRAPHIQUE_contient_la_boite_et_COLLE_au_bord_sous_le_seuil():
    """LA MESURE QUI DÉCIDE DU CADRAGE ORTHO, exécutée sur des nombres.

    Une ortho ne se cadre pas comme une perspective : reculer une projection
    parallèle ne change RIEN à son image, si bien que le facteur de recul de la
    tâche 3 doit s'appliquer aux BORDS et non à la distance. Transposé par
    analogie, il n'aurait rien fait du tout — sans erreur, sans banc rouge.

    Ce contrôle projette les HUIT SOMMETS et vérifie deux choses :
      — CONTENANCE : rien ne sort du cadre, pour dix-huit combinaisons de vue,
        de rayon, d'aspect et de marge, sur trois boîtes dont deux ne sont PAS
        cubiques (la leçon de la matrice creuse : des données symétriques
        laissent passer une erreur d'indice) ;
      — JUSTESSE : sous le seuil, le cube du pire cas touche les deux bords à
        1e-12 près. C'est le gain propre à l'orthographique — sous perspective
        le coin le plus proche se projette plus loin, et le critère n'était
        qu'un ordre de grandeur. Au-dessus du seuil la marge restante vaut
        exactement seuil/aspect, calculé ici par un second chemin.
    """
    vues = ["libre", "iso", "face", "dessus", "profil"]
    cas = []
    for v in vues:
        for rayon, aspect, marge in ((1.3, 0.42, 1.35), (0.37, 0.58, 1.35),
                                     (12.5, 1.04, 1.35), (1.3, 2.37, 1.9),
                                     (0.37, 0.813030, 1.35), (12.5, 0.5, 1.0)):
            cas.append({"vue": v, "rayon": rayon, "aspect": aspect,
                        "marge": marge})
    rendu = json.loads(_node(
        _harnais_vue() + "const CAS = " + json.dumps(cas) + ";\n" + """
      console.log(JSON.stringify(CAS.map((c) => {
        const o = orientationDe(c.vue);
        const g = cadrageDe(c.rayon, c.aspect, c.marge, o);
        return { seuil: g.seuil, recul: g.recul,
                 cadre: cadreOrtho(g.demiHauteur, c.aspect) };
      })));
    """))
    assert len(rendu) == len(cas)
    orientations = json.loads(_node(_harnais_vue()
        + "console.log(JSON.stringify(ORIENTATIONS));"))
    colles = 0
    for c, r in zip(cas, rendu):
        o = orientations[c["vue"]]
        dirv = [o["dir"]["x"], o["dir"]["y"], o["dir"]["z"]]
        hautv = [o["haut"]["x"], o["haut"]["y"], o["haut"]["z"]]
        droite, haut, _ = _base_lookat(dirv, [0, 0, 0], hautv)
        ray = c["rayon"]
        # BOÎTES ASYMÉTRIQUES : la première est le pire cas (le cube), les
        # deux autres sont plates et posées sur deux axes différents, pour
        # qu'une erreur d'indice ne tombe pas sur un demi-côté égal.
        for demis in ((ray, ray, ray), (ray, 0.31 * ray, 0.77 * ray),
                      (0.19 * ray, 0.62 * ray, ray)):
            dx, dy = _extremes_projetes(demis, droite, haut)
            assert dx <= r["cadre"]["right"] * (1 + 1e-12), \
                f"{c} rogne en largeur : {dx} > {r['cadre']['right']}"
            assert -dx >= r["cadre"]["left"] * (1 + 1e-12), c
        # LA JUSTESSE, sur le cube seul — c'est lui que le cadre vise.
        dx, _ = _extremes_projetes((ray, ray, ray), droite, haut)
        reste = dx / r["cadre"]["right"]
        # SECOND CHEMIN : la fraction de cadre occupée vaut seuil/aspect
        # au-dessus du seuil, et 1 exactement en dessous.
        attendu = min(1.0, r["seuil"] / c["aspect"])
        assert abs(reste - attendu) < 1e-12, f"{c} : {reste} au lieu de {attendu}"
        if c["aspect"] <= r["seuil"]:
            colles += 1
            assert abs(dx - r["cadre"]["right"]) < 1e-12 * max(1.0, dx), c
    # Le contrôle serait vide s'il n'exerçait jamais le cas serré : on compte.
    assert colles >= 10, f"seulement {colles} cas sous le seuil"


def test_toutes_les_vues_nommees_tiennent_VERTICALEMENT_a_la_marge_par_defaut():
    """LE CADRAGE VERTICAL EST INCHANGÉ — c'était l'exigence — et il fallait
    vérifier qu'il TIENT ENCORE pour des directions qu'il n'a jamais vues.

    La demi-hauteur reste NORME_DIR·marge·rayon, soit 1,6875·rayon. MESURÉ, la
    demi-hauteur du pire cas vaut 1,4269·rayon en vue libre (18 % de marge),
    1,6330 en isométrique (3,3 % — la plus juste des cinq) et 1,0000 sur un
    axe. Toutes passent. Une sixième vue posée sans ce contrôle pourrait, elle,
    ne pas passer, et son modèle sortirait par le haut sans que rien ne grince.

    NON GARANTI SOUS LA MARGE PAR DÉFAUT, et c'est dit : à marge = 1, la
    demi-hauteur tombe à 1,25·rayon et l'isométrie déborde. Aucun appelant ne
    passe de marge ; le jour où l'un le fera, il lira ceci.
    """
    orientations = json.loads(_node(_harnais_vue()
        + "console.log(JSON.stringify(ORIENTATIONS));"))
    cadres = json.loads(_node(_harnais_vue() + """
      const o = {};
      for (const n of Object.keys(ORIENTATIONS))
        o[n] = cadrageDe(1, 1.0, 1.35, ORIENTATIONS[n]).demiHauteur;
      console.log(JSON.stringify(o));
    """))
    marges = {}
    for nom, o in orientations.items():
        dirv = [o["dir"]["x"], o["dir"]["y"], o["dir"]["z"]]
        hautv = [o["haut"]["x"], o["haut"]["y"], o["haut"]["z"]]
        droite, haut, _ = _base_lookat(dirv, [0, 0, 0], hautv)
        _, dy = _extremes_projetes((1, 1, 1), droite, haut)
        assert dy <= cadres[nom], f"{nom} deborde par le haut : {dy} > {cadres[nom]}"
        marges[nom] = cadres[nom] / dy
    assert abs(marges["iso"] - 1.0334) < 1e-3, marges["iso"]
    assert abs(marges["libre"] - 1.1827) < 1e-3, marges["libre"]


def test_aucune_orientation_n_a_un_HAUT_PARALLELE_a_sa_direction():
    """LE NaN QUI FAIT L'ÉCRAN NOIR, épinglé à sa source.

    `demiLargeurPireCas` divise par la norme de haut × dir. Un `haut` parallèle à
    `dir` — la faute naturelle sur une vue de dessus, où (0,1,0) semble être le
    haut évident — rend ce produit NUL, donc le seuil NaN, donc le recul NaN,
    donc une caméra posée sur trois NaN. Rien ne lève, rien ne s'affiche.
    """
    rendu = json.loads(_node(_harnais_vue() + """
      const o = {};
      for (const n of Object.keys(ORIENTATIONS)) {
        const v = ORIENTATIONS[n];
        const L = demiLargeurPireCas(v.dir, v.haut);
        const c = cadrageDe(1.3, 0.42, 1.35, v);
        o[n] = { fini: Number.isFinite(L) && Number.isFinite(c.demiHauteur),
                 L: L, demi: c.demiHauteur };
      }
      console.log(JSON.stringify(o));
    """))
    for nom, v in rendu.items():
        assert v["fini"], f"{nom} rend un NaN : {v}"
        assert v["L"] > 0 and v["demi"] > 0, f"{nom} : {v}"


def test_le_HAUT_de_la_vue_DESSUS_est_celui_que_lookAt_produit_VRAIMENT():
    """POURQUOI (0, 0, −1) ET NON (0, 1, 0), refait par un second chemin.

    La vue de dessus pose la caméra exactement au pôle. three.js ne s'y casse
    pas : `Spherical.setFromVector3` y rend theta = atan2(0, 0) = 0 et
    `makeSafe()` relève phi à EPS, si bien que le décalage repart vers +Z ; le
    `lookAt` d'OrbitControls, avec un `up` resté à (0, 1, 0), rend alors la
    base (droite = +X, haut d'écran = −Z). C'est CE haut-là que la géométrie de
    cadrage doit connaître, et il n'est pas celui qu'on écrirait d'instinct.

    L'EPS n'est pas recopié : il est LU dans le three.js vendorisé. Une version
    qui le changerait ferait bouger la mesure, pas le banc.
    """
    coeur = (FRONT / "dist" / "assets" / "three" / "three.core.min.js") \
        .read_text(encoding="utf-8", errors="replace")
    m = re.search(r"makeSafe\(\)\{const \w+=([0-9.e-]+);", coeur)
    assert m, "makeSafe() introuvable dans le three.js vendorise"
    eps = float(m.group(1))
    assert 0 < eps < 1e-4, eps
    rayon = 3.0
    oeil = [0.0, rayon * math.cos(eps), rayon * math.sin(eps)]
    droite, haut, _ = _base_lookat(oeil, [0, 0, 0], [0, 1, 0])
    for obtenu, vise in ((droite, (1, 0, 0)), (haut, (0, 0, -1))):
        for k in range(3):
            assert abs(obtenu[k] - vise[k]) < 1e-4, (obtenu, vise)
    # …et c'est exactement ce que la table déclare.
    orientations = json.loads(_node(_harnais_vue()
        + "console.log(JSON.stringify(ORIENTATIONS));"))
    assert orientations["dessus"]["haut"] == {"x": 0, "y": 0, "z": -1}
    assert orientations["dessus"]["dir"] == {"x": 0, "y": 1, "z": 0}


def test_les_PLANS_DE_COUPE_restent_EXACTEMENT_ceux_de_la_tache_3():
    """LA MOITIÉ DE L'EXIGENCE QUI N'AVAIT AUCUN GARDE-FOU.

    « Le cadrage conscient de l'aspect doit continuer de valoir » ne parle pas
    que de la position : `near` et `far` en font partie. La tâche 3 les
    déduisait d'un scalaire `d = rayon·marge·recul / tan(fov/2)` qui N'ÉTAIT PAS
    la distance — la caméra était posée à `d·DIR`, de norme 1,25. `coupeDe()`
    reçoit désormais la distance VRAIE et doit donc la rediviser par 1,25 :
    l'oublier déplace les deux plans de 25 %, sans qu'un pixel ne bouge à
    l'écran tant que le modèle reste loin des plans.

    LE SECOND CHEMIN NE MENTIONNE JAMAIS NORME_DIR : il refait `d` par la
    formule de la tâche 3, à partir du rayon, de la marge, du recul et du fov
    de 45° — et le recul lui-même vient de `cadrageDe`, exécutée. Les deux
    routes ne se rejoignent que si le facteur est juste.
    """
    cas = []
    for vue in ("libre", "iso", "face", "dessus", "profil"):
        for rayon, aspect, marge in ((1.3, 0.42, 1.35), (0.37, 1.04, 1.35),
                                     (12.5, 0.58, 1.9), (0.019, 2.37, 1.0)):
            cas.append({"vue": vue, "rayon": rayon, "aspect": aspect,
                        "marge": marge})
    rendu = json.loads(_node(
        _harnais_vue() + "const CAS = " + json.dumps(cas) + ";\n" + """
      console.log(JSON.stringify(CAS.map((c) => {
        const g = cadrageDe(c.rayon, c.aspect, c.marge, orientationDe(c.vue));
        /* la distance VRAIE, celle que cadrer() calcule */
        const distance = g.demiHauteur / Math.tan((45 * Math.PI) / 360);
        return { recul: g.recul, distance: distance, coupe: coupeDe(distance) };
      })));
    """))
    ecarts = 0
    for c, r in zip(cas, rendu):
        # LA FORMULE DE LA TÂCHE 3, mot pour mot, sans NORME_DIR nulle part.
        d = (c["rayon"] * c["marge"] * r["recul"]) / math.tan(math.radians(22.5))
        assert abs(r["coupe"]["near"] - max(d / 1000, 0.001)) < 1e-15, (c, r)
        assert abs(r["coupe"]["far"] - d * 100) < 1e-12 * abs(d * 100), (c, r)
        # …et la distance vraie en vaut 1,25 fois autant : c'est ce facteur-là
        # que coupeDe() doit annuler, et le seul endroit où il se lit.
        assert abs(r["distance"] - 1.25 * d) < 1e-12 * r["distance"], (c, r)
        if r["coupe"]["near"] > 0.001:
            ecarts += 1
    # `near` est borné par le bas à 0,001 : sur un modèle minuscule le plancher
    # gagne, et un contrôle qui ne verrait QUE ce cas ne mesurerait rien.
    assert ecarts >= 15, f"seulement {ecarts} cas hors du plancher de near"
    # Le modèle tient entre les deux plans : la profondeur du pire cas vaut
    # √3·rayon = 1,733·rayon, contre une distance de 4,0740·rayon.
    for c, r in zip(cas, rendu):
        demi_profondeur = math.sqrt(3) * c["rayon"]
        assert r["coupe"]["near"] < r["distance"] - demi_profondeur, (c, r)
        assert r["coupe"]["far"] > r["distance"] + demi_profondeur, (c, r)


def test_la_boucle_rend_la_CAMERA_ACTIVE_et_les_deux_cameras_sont_declarees():
    """La boucle de rendu tenait la caméra dans sa fermeture. Laissée telle
    quelle, elle aurait rendu la perspective pour toujours : la bascule aurait
    changé `api.camera`, `api.projection`, les contrôles — et rien à l'écran.

    Le contrat de forme d'`api` est épinglé au même endroit, parce que c'est la
    règle que le fichier se donne en toutes lettres (« toute clé de `api` se
    déclare ICI »). Ce contrôle porte sur du CODE : `_code` retire les blocs de
    commentaire, sans quoi la prose du fichier — qui nomme ces clés — le
    satisferait toute seule.
    """
    code = _code("lib3d/viewer.js")
    assert "renderer.render(scene, api.camera);" in code
    # …et JAMAIS la variable de fermeture, le défaut que ce banc garde.
    assert "renderer.render(scene, camera)" not in code
    assert "new THREE.OrthographicCamera(" in code
    # LE FOV, ET C'EST LE SEUL ENDROIT QUI LE TIENT. Le montage du harnais de
    # bout en bout reprend 45 en dur, et la valeur attendue de la distance
    # passe par tan(22,5°) : passer le vrai canevas à 60 laisserait tout au
    # vert, en mesurant une caméra que la page n'a plus.
    assert "new THREE.PerspectiveCamera(45," in code
    for cle in ("cameraPerspective: camera", "cameraOrthographique: cameraOrtho",
                'projection: "perspective"', 'vueCadrage: "libre"'):
        assert cle in code, cle


def test_le_redimensionnement_ne_pose_JAMAIS_un_aspect_sur_une_ORTHO():
    """`camera.aspect = w / h` sur une OrthographicCamera ne lève pas, ne fait
    rien, et ne se voit pas : le modèle reste simplement déformé. Le
    redimensionnement écrit donc l'aspect sur la perspective NOMMÉMENT, et
    refait les bords de l'ortho à demi-hauteur constante.
    """
    code = _code("lib3d/viewer.js")
    assert "api.cameraPerspective.aspect = w / h;" in code
    assert "api.camera.aspect" not in code
    # la demi-hauteur est RELUE sur la caméra, jamais réinventée : top/bottom
    # sont la mémoire du cadrage, et un redimensionnement n'y touche pas.
    assert "poserCadreOrtho(o, (o.top - o.bottom) / 2, w / h);" in code


def test_le_cadrage_ne_lit_JAMAIS_le_fov_de_la_camera_ACTIVE():
    """LE PIÈGE LE PLUS COURT DE CETTE TÂCHE. `api.camera.fov` rend `undefined`
    sous une ortho, `Math.tan(undefined)` rend NaN, `position.set` avale trois
    NaN et l'écran devient noir — sans exception, sans console, sans banc rouge.
    La distance se lit donc sur la caméra PERSPECTIVE, nommément.
    """
    code = _code("lib3d/viewer.js")
    assert "api.cameraPerspective.fov" in code
    assert "api.camera.fov" not in code
    # Et le cadre de l'ortho passe par les BORDS, pas par la distance : c'est
    # la différence qu'une transposition par analogie aurait manquée.
    cad = code.split("export function cadrer(api, marge = 1.35)", 1)[1] \
              .split("\n}\n", 1)[0]
    assert "api.camera.isOrthographicCamera" in cad
    assert "poserCadreOrtho(api.camera, cadre.demiHauteur, aspect);" in cad


def test_les_TROIS_references_de_camera_sont_repassees_a_la_bascule():
    """OrbitControls, TransformControls et la vue B retiennent chacun LEUR
    caméra. Aucun des trois oublis ne lève :
      — les contrôles piloteraient une caméra que personne ne rend (écran figé),
      — le gizmo taillerait et piquerait ses poignées avec la mauvaise (des
        poignées visibles et inattrapables),
      — la vue B resterait en perspective (une comparaison qui ne compare rien).
    """
    vue, js = _code("lib3d/viewer.js"), _code("etabli/etabli.js")
    proj = vue.split("export function projeter(api, mode)", 1)[1] \
              .split("\n}\n", 1)[0]
    assert "api.controls.object = apres;" in proj
    assert "api.camera = apres;" in proj
    # le gizmo : une propriété DÉFINIE de TransformControls, qui repropage la
    # caméra au gizmo et à son plan de saisie — lui réaffecter suffit.
    assert "GIZMO.camera = S.vueA.camera;" in js
    assert "reposerCameraDuGizmo();" in js
    # LES DEUX VUES, jamais A seule — et un seul chemin les sert, la bascule
    # n'étant qu'un raccourci vers appliquerVue().
    applique = js.split("function appliquerVue(nom)", 1)[1].split("\n}\n", 1)[0]
    # L'ORDRE COMPTE — voir test_appliquerVue_laisse_la_vue_A_REFERENCE, qui le
    # mesure. Ici on ne garde que la présence des deux.
    assert "for (const v of [S.vueB, S.vueA])" in applique
    assert "reposerCameraDuGizmo();" in applique


def test_la_synchronisation_AB_ne_recopie_PAS_un_fov_a_une_ortho():
    """`dst.camera.fov = src.camera.fov` sur deux orthos écrit une propriété
    que personne ne lit : les deux vues divergeraient à la première image, et
    c'est exactement ce qu'une comparaison A/B promet de ne jamais faire.

    Le cadre de dst est REFAIT sur SON aspect plutôt que recopié : recopier
    left/right imposerait à B l'aspect de A. Et la projection s'aligne AVANT le
    reste, faute de quoi une vue B née pendant que A est en isométrie
    comparerait deux projections.
    """
    js = _code("etabli/etabli.js")
    syn = js.split("function synchroniser(src, dst)", 1)[1].split("\n}\n", 1)[0]
    assert "if (dst.projection !== src.projection) {" in syn
    assert "projeter(dst, src.projection);" in syn
    # ET LE GIZMO AVEC. Le câblage est tête-bêche : dans le sens B → A, c'est
    # `S.vueA.camera` qui change ici, et le gizmo garderait sinon une caméra que
    # plus personne ne rend — poignées mal taillées et impossibles à attraper.
    # Deux sites sur trois étaient traités ; l'oubli était celui-ci.
    assert "reposerCameraDuGizmo();" in syn
    assert syn.index("projeter(dst, src.projection);")         < syn.index("reposerCameraDuGizmo();")
    assert "src.camera.isOrthographicCamera" in syn
    assert "cadreOrtho((src.camera.top - src.camera.bottom) / 2, aspectDe(dst))" in syn
    assert "dst.camera.zoom = src.camera.zoom;" in syn
    # le `fov` reste — pour la perspective, et SEULEMENT dans cette branche
    assert "dst.camera.fov = src.camera.fov;" in syn
    assert syn.index("src.camera.isOrthographicCamera") \
        < syn.index("dst.camera.fov = src.camera.fov;")
    # et B naît sur le point de vue de A, AVANT de charger : charger() cadre,
    # et cadrer() lit `api.vueCadrage`.
    ouvre = js.split("async function _ouvrirComparaison", 1)[1] \
              .split("\n}\n", 1)[0]
    assert "projeter(S.vueB, S.vueA.projection);" in ouvre
    assert "orienter(S.vueB, S.vueA.vueCadrage);" in ouvre
    assert ouvre.index("orienter(S.vueB") < ouvre.index("charger(S.vueB")


def test_le_viewer_n_ecrit_JAMAIS_camera_up():
    """LA RAISON EST DANS LE FICHIER VENDORISÉ, ligne 406 : OrbitControls fige
    son repère à la CONSTRUCTION (`_quat` depuis `object.up`) et ne le
    recalcule jamais dans update(). Écrire `camera.up` après coup laisserait
    l'orbite tourner dans l'ANCIEN repère — le modèle pivote de travers sous la
    souris, sans erreur nulle part.

    On vérifie donc DEUX choses : que le module ne l'écrit pas, et que la
    raison est encore vraie dans le three.js du dépôt.
    """
    code = _code("lib3d/viewer.js")
    for interdit in (".up.set(", ".up.copy(", "camera.up ="):
        assert interdit not in code, interdit
    orbit = (FRONT / "dist" / "assets" / "three" / "addons" / "controls"
             / "OrbitControls.js").read_text(encoding="utf-8")
    assert "this._quat = new Quaternion().setFromUnitVectors( object.up" in orbit
    # …et update() ne le refait pas : un seul site d'écriture dans le fichier.
    assert orbit.count("this._quat = ") == 1


def test_les_DEUX_OPTIONS_sont_offertes_DANS_le_canevas():
    """La demande, à la lettre : « deux options, celui qui existe déjà et une
    vue isométrique ». Le bouton porte la DESTINATION comme ses voisins, et
    naît sans texte — majBoutonProjection() l'écrit dès l'import, source unique.

    DANS le canevas, et non dans l'en-tête : deux comptes rigides y veillent
    (trois `head-btn`, et autant de `<button>` que de porteurs de la classe).
    Ces boutons portent `cam-btn`.
    """
    html, css = _lire("etabli/index.html"), _lire("etabli/etabli.css")
    js = _code("etabli/etabli.js")
    # Découpe sur l'ID du VOISIN et non sur son balisage exact : la première
    # écriture reproduisait l'indentation d'index.html, et un reformatage
    # l'aurait fait tomber en IndexError nu plutôt qu'en assertion lisible.
    assert 'id="vueB"' in html
    vue_a = html.split('id="vueA"', 1)[1].split('id="vueB"', 1)[0]
    assert 'id="vueCam"' in vue_a
    assert 'id="btnProjection"></button>' in vue_a      # il naît SANS texte
    for nom in ("face", "dessus", "profil"):
        assert f'data-vue="{nom}"' in vue_a, nom
    assert html.count('class="cam-btn"') == 4
    assert "head-btn" not in vue_a
    # la barre est AU-DESSUS du canevas et ne vole pas l'orbite entre ses
    # boutons — sans quoi le coin haut-droit cesserait de tourner et de
    # sélectionner, en silence.
    reg = css.split(".vue-cam {", 1)[1].split("}", 1)[0]
    assert "z-index: 2" in reg and "pointer-events: none" in reg
    assert "pointer-events: auto" in css.split(".cam-btn {", 1)[1].split("}", 1)[0]
    # LE SURVOL N'IMITE PAS L'ÉTAT COURANT. Les deux règles étaient identiques :
    # sous le pointeur, un bouton inactif était indiscernable de l'actif — au
    # moment précis où l'on parcourt la barre pour choisir. Un `:hover` qui
    # imite l'état courant efface l'état courant.
    survol = css.split(".cam-btn:hover {", 1)[1].split("}", 1)[0]
    actif = css.split(".cam-btn.actif {", 1)[1].split("}", 1)[0]
    assert "background" in actif and "background" not in survol
    # câblage, et les libellés qui naissent vides sont écrits à l'import
    assert '$("#btnProjection").addEventListener("click", basculerProjection);' in js
    assert 'document.querySelectorAll("#vueCam [data-vue]")' in js
    assert js.count("majBoutonProjection();") >= 2
    assert 'b.textContent = iso ? "Perspective" : "Isométrique";' in js
    # les deux options sont COMPLÈTES : chacune pose sa projection ET sa
    # direction. Une ortho laissée sur le trois-quarts historique serait
    # orthographique et non isométrique — le mot du bouton serait faux.
    bascule = js.split("function basculerProjection()", 1)[1].split("\n}\n", 1)[0]
    assert 'appliquerVue(S.vueA.projection === "orthographique" ' \
           '? "libre" : "iso");' in bascule
    # La bascule N'EST QU'UN RACCOURCI vers deux des cinq vues : elle ne peut
    # donc pas poser une projection que la vue ne porte pas, ce que deux
    # commandes séparées auraient permis.
    assert "projeter(" not in bascule


def test_les_vues_d_AXE_sont_ORTHOGRAPHIQUES_et_la_MESURE_le_dit():
    """LE CHOIX QUE LE PILOTE DE RUNTIME A IMPOSÉ, avec son chiffre.

    Le cadrage de la tâche 3 compare des étendues AU PLAN DU CENTRE et laisse
    depuis toujours passer la fuite du coin le plus proche. En vue libre elle
    ne se voyait pas : le pire cas y vaut 1,372·rayon quand le cadre en offre
    1,6875·aspect, donc du mou. Une vue d'AXE a un pire cas de 1,000·rayon —
    le cadre y est serré sur le modèle, et le mou disparaît.

    MESURÉ sur une boîte 3 × 1,1 × 0,4 dans un canevas 430 × 824 (la
    demi-largeur exacte de la comparaison A/B), vue « dessus » : caméra posée à
    6,940, face proche à 6,390, magnification 1,086 — soit 8,6 % de la largeur
    hors du cadre, 4,3 % rognés à chaque bord. La même vue en orthographique
    tient à 1,000000, exactement.

    Corriger la fuite aurait demandé de reculer AVANT le seuil de rognage, donc
    de déplacer aussi le cadrage vertical, donc de casser ce que la demande
    exige de conserver. Les trois vues d'axe passent donc en orthographique —
    ce sont les vues du dessin technique, et Blender fait le même choix.

    Ce contrôle EXÉCUTE les deux projections plutôt que de citer les nombres.
    """
    aspect = 430 / 824
    rayon, profondeur, demi_largeur = 1.5, 0.55, 1.5
    rendu = json.loads(_node(_harnais_vue()
        + "const A = " + json.dumps(aspect) + ";\n"
        + "const R = " + json.dumps(rayon) + ";\n" + """
      const g = cadrageDe(R, A, 1.35, orientationDe("dessus"));
      console.log(JSON.stringify({ demi: g.demiHauteur, seuil: g.seuil,
                                   cadre: cadreOrtho(g.demiHauteur, A) }));
    """))
    demi = rendu["demi"]
    # ORTHOGRAPHIQUE : la demi-largeur du modèle contre celle du cadre.
    assert abs(demi_largeur / rendu["cadre"]["right"] - 1.0) < 1e-12, rendu
    # PERSPECTIVE : la distance qui rend cette demi-hauteur, puis la division
    # par la profondeur — c'est la fuite, et elle sort du cadre.
    distance = demi / math.tan(math.radians(45) / 2)
    assert abs(distance - 6.9402) < 1e-3, distance
    fuite = (demi_largeur * distance) / ((distance - profondeur) * demi * aspect)
    assert 1.08 < fuite < 1.09, fuite
    # …et la règle est écrite, pour les cinq vues, en un seul endroit.
    js = _code("etabli/etabli.js")
    assert 'const PROJECTION_DE_VUE = { libre: "perspective", ' \
           'iso: "orthographique",' in js
    for nom in ("face", "dessus", "profil"):
        assert f'{nom}: "orthographique"' in js, nom
    applique = js.split("function appliquerVue(nom)", 1)[1].split("\n}\n", 1)[0]
    assert "projeter(v, PROJECTION_DE_VUE[nom]);" in applique
    # PROJETER AVANT D'ORIENTER : orienter() recadre, et le cadre d'une ortho
    # ne s'écrit pas comme celui d'une perspective.
    assert applique.index("projeter(v,") < applique.index("orienter(v, nom);")


def test_les_vues_nommees_sont_les_axes_DU_MODELE_et_DISENT_le_plan_de_la_plaque():
    """LA DÉCISION FACE À L'AVERTISSEMENT DE LA TÂCHE PRÉCÉDENTE, épinglée.

    `axeEmpile` choisit le plan d'étalement d'après les PIÈCES : y pour des
    volumes posés, z pour les douze cartes du modèle réel de l'utilisateur.
    « Dessus » n'est donc pas toujours la vue qui regarde la plaque en face.

    Deux réponses étaient possibles. Faire suivre les boutons — « Dessus »
    regarderait selon X un jour sur deux, un libellé qui ment. Ou les garder
    sur les axes DU MODÈLE, ceux-là mêmes que le serveur nomme dans `axe_haut`,
    et DIRE laquelle des trois tombe en face. C'est la seconde qui est livrée :
    l'axe remonte de `etaler()` jusqu'à `PLQ.axe`, et une table le convertit en
    nom de vue. Les pièces étant posées du côté POSITIF de l'axe (leur minimum
    y vaut zéro, le plateau recule en dessous), la caméra du côté positif les
    regarde de face et non par le dos.
    """
    plq, js = _code("lib3d/plaque.js"), _code("etabli/etabli.js")
    css = _lire("etabli/etabli.css")
    # l'axe est RENDU par le module — il ne l'était pas
    et = plq.split("export function etaler(api, plan = null)", 1)[1].split("\n}\n", 1)[0]
    assert "axe: mise.axe," in et
    # …REMONTÉ jusqu'à l'état du panneau, et remis à zéro avec la plaque
    assert "PLQ.axe = etalement.axe;" in js
    assert "PLQ.axe = null;" in js
    # …et CONVERTI en nom de vue, jamais recalculé sur place
    assert 'const VUE_DE_PLAQUE = { x: "profil", y: "dessus", z: "face" };' in js
    assert "axeEmpile" not in js       # la règle reste dans plaque.js
    maj = js.split("function majBoutonsVue()", 1)[1].split("\n}\n", 1)[0]
    assert "VUE_DE_PLAQUE[PLQ.axe]" in maj
    assert 'b.classList.toggle("plaque", nom === face);' in maj
    assert "regarde la plaque en face" in maj
    assert ".cam-btn.plaque" in css
    # ET LE MODULE PARTAGÉ NE CONNAÎT PAS LA PLAQUE. L'assertion portait sur
    # `_code()`, donc sur un texte AMPUTÉ de ses commentaires : elle ne voyait
    # pas que l'en-tête de viewer.js nommait `VUE_DE_PLAQUE`, un identifiant
    # d'etabli.js — un module partagé qui documente une page. On garde les deux
    # moitiés séparément : la DÉPENDANCE se lit dans les imports, la PROSE dans
    # le fichier entier.
    vue = _code("lib3d/viewer.js")
    assert "axeEmpile" not in vue and "plaque" not in vue
    for ligne in _lire("lib3d/viewer.js").splitlines():
        if ligne.startswith("import"):
            assert "plaque" not in ligne and "etabli" not in ligne, ligne
    assert "VUE_DE_PLAQUE" not in _lire("lib3d/viewer.js")


# ── O (suite). le point de vue, EXÉCUTÉ CONTRE LE VRAI three.js ──────────────
# CE QUE LES CONTRÔLES CI-DESSUS NE POUVAIENT PAS VOIR, et il faut le dire.
# Ils mesurent les règles PURES — le pire cas, le seuil, le cadre, les plans de
# coupe — et c'est la moitié du travail. L'autre moitié est faite de fonctions
# qui ÉCRIVENT sur de vrais objets three.js : cadrer() pose une caméra,
# orienter() la fait recadrer, projeter() la remplace. Un banc de texte ne voit
# pas une caméra posée au mauvais endroit, et un banc qui n'exerce que les
# briques ne dit rien de la fonction qui les assemble.
#
# Six mutations l'ont prouvé : le facteur 1,25 des plans de coupe retiré, le
# recadrage d'orienter() court-circuité, le zoom de cadrer() supprimé — trois
# défauts francs, et le banc restait vert.
#
# On charge donc le VRAI viewer.js, avec le VRAI three.js vendorisé, et on
# projette les huit sommets par la matrice que le GPU utiliserait.


_TROIS = FRONT / "dist" / "assets" / "three"


def _node_trois(importe: str, source: str) -> str:
    """Exécute du JS dans node, avec le three.js vendorisé RÉSOLU.

    viewer.js importe « three » et « three/addons/… » — des spécifieurs NUS que
    la page résout par son import map en ligne et que node ne connaît pas. On
    lui en donne un : un crochet de résolution (`module.register`) qui renvoie
    les deux préfixes vers le dossier vendorisé. RIEN N'EST COPIÉ ni réécrit :
    le module chargé est le fichier livré, à l'octet près, ce qui est tout
    l'intérêt — un viewer.js recopié puis rafistolé mesurerait la copie.

    OPTIONNEL comme `_node` : sans node, le contrôle se saute plutôt que de
    rougir pour une raison qui n'est pas la sienne.
    """
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : la règle ne peut pas être EXÉCUTÉE ici")
    # `module.register` demande node 20.6, et pas davantage : node 20 est
    # encore LTS, et un seuil trop haut sauterait TOUTE la preuve d'exécution
    # en laissant la suite au vert. Sauter plutôt que rougir pour une raison
    # qui n'est pas la sienne — même doctrine que l'absence de node.
    v = subprocess.run([node, "-v"], capture_output=True, timeout=30)
    m = re.match(r"v(\d+)\.(\d+)", v.stdout.decode().strip())
    assert m, v.stdout
    majeure, mineure = int(m.group(1)), int(m.group(2))
    if (majeure, mineure) < (20, 6):
        pytest.skip(f"node {majeure}.{mineure} : module.register demande 20.6+")
    tmp = pathlib.Path(tempfile.mkdtemp())
    trois = _TROIS.resolve().as_uri() + "/"
    (tmp / "resolveur.mjs").write_text(
        f'const T = {json.dumps(trois)};\n'
        'const P = "three/addons/";\n'
        "export function resolve(spec, ctx, next) {\n"
        '  if (spec === "three") return next(T + "three.module.min.js", ctx);\n'
        "  if (spec.startsWith(P)) return next(T + \"addons/\""
        " + spec.slice(P.length), ctx);\n"
        "  return next(spec, ctx);\n"
        "}\n", encoding="utf-8")
    (tmp / "hook.mjs").write_text(
        'import { register } from "node:module";\n'
        'register("./resolveur.mjs", import.meta.url);\n', encoding="utf-8")
    vue = (FRONT / "lib3d" / "viewer.js").resolve().as_uri()
    tete = (f"import * as THREE from \"three\";\n"
            f"import {{ OrbitControls }} from"
            f" \"three/addons/controls/OrbitControls.js\";\n"
            f"import {{ {importe} }} from {json.dumps(vue)};\n")
    r = subprocess.run(
        [node, "--import", (tmp / "hook.mjs").as_uri(),
         "--input-type=module", "-e", tete + _MONTAGE + source],
        capture_output=True, timeout=120)
    shutil.rmtree(tmp, ignore_errors=True)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:900]
    return r.stdout.decode("utf-8", "replace")


# Le MONTAGE : `creerCanevas()` moins son WebGLRenderer, qui exige un canevas et
# un contexte GPU que node n'a pas. Écrit ici EN ENTIER, délibérément — même
# raison que le `_FAUX_ARBRE` de la section N : c'est la liste exacte de ce que
# les fonctions exportées ont le droit de supposer, et le jour où elles
# supposeront davantage, ce harnais rougira au lieu de les laisser dériver. Les
# clés d'`api`, elles, sont épinglées séparément sur la vraie déclaration par
# test_la_boucle_rend_la_CAMERA_ACTIVE_et_les_deux_cameras_sont_declarees.
_MONTAGE = """
/* Le canevas 2D FACTICE des règles d'un plateau : le SEUL autre point de
   contact de viewer.js avec le DOM, `renderer.domElement.ownerDocument
   .createElement("canvas")`. Il ENREGISTRE les textes écrits et leur abscisse
   dans `appels` — c'est ce que les bancs lisent, par `material.map.image`. Un
   autre élément demandé LÈVE : le contrat est celui-là, pas « le DOM ». */
function fauxCanevas2d() {
  const cv = { width: 0, height: 0, appels: [] };
  const ctx = { font: "", fillStyle: "", textAlign: "", textBaseline: "",
    clearRect() {}, fillRect() {},
    measureText(t) { return { width: 10 * String(t).length }; },
    fillText(t, x, y) { cv.appels.push({ texte: String(t), x, y }); } };
  cv.getContext = (k) => (k === "2d" ? ctx : null);
  return cv;
}
function monter(w, h) {
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 5000);
  camera.position.set(2.5, 1.8, 3.2);
  const ortho = new THREE.OrthographicCamera(-1, 1, 1, -1, 0.01, 5000);
  ortho.position.copy(camera.position);
  const controls = new OrbitControls(camera, null);
  controls.enableDamping = true;
  /* `dispatchEvent` EST DANS LE CONTRAT, et il a failli ne pas y être :
     majRepere() crie le pas sur le canevas, et onze contrôles avaient recollé
     la méthode sur place (`= () => true`). Le docstring ci-dessus promet que ce
     montage ROUGIT quand une fonction suppose davantage ; onze rustines
     rendaient cette promesse fausse, et le douzième oubli aurait échoué sur une
     TypeError remontée de node plutôt que sur une assertion lisible. */
  return { renderer: { domElement: { clientWidth: w, clientHeight: h,
                                     dispatchEvent() { return true; },
                                     ownerDocument: { createElement(tag) {
                                       if (tag !== "canvas") {
                                         throw new Error("createElement : seul un canvas est fourni, pas " + tag);
                                       }
                                       return fauxCanevas2d();
                                     } } } },
           scene, camera, controls, racine: null, gltf: null,
           cameraPerspective: camera, cameraOrthographique: ortho,
           projection: "perspective", vueCadrage: "libre" };
}
/* Une boite ASYMETRIQUE et DECENTREE : trois cotes distincts et un centre hors
   de l'origine, pour qu'une erreur d'axe ou un centre oublie ne tombe pas sur
   un zero. rayon = max(cote)/2 = 1,5. */
function poserModele(api, l, h, p, cx, cy, cz) {
  const m = new THREE.Mesh(new THREE.BoxGeometry(l, h, p),
                           new THREE.MeshBasicMaterial());
  m.position.set(cx, cy, cz);
  const racine = new THREE.Group();
  racine.add(m);
  api.scene.add(racine);
  api.racine = racine;
  racine.updateMatrixWorld(true);
}
/* Les huit sommets, projetes par la matrice que le GPU utiliserait. */
function projeterBoite(api) {
  const b = new THREE.Box3().setFromObject(api.racine);
  api.camera.updateMatrixWorld(true);
  api.camera.updateProjectionMatrix();
  let x = 0, y = 0, zmin = Infinity, zmax = -Infinity, nan = false;
  for (const sx of [b.min.x, b.max.x])
    for (const sy of [b.min.y, b.max.y])
      for (const sz of [b.min.z, b.max.z]) {
        const q = new THREE.Vector3(sx, sy, sz).project(api.camera);
        if (![q.x, q.y, q.z].every(Number.isFinite)) nan = true;
        x = Math.max(x, Math.abs(q.x)); y = Math.max(y, Math.abs(q.y));
        zmin = Math.min(zmin, q.z); zmax = Math.max(zmax, q.z);
      }
  return { x, y, zmin, zmax, nan };
}
const etat = (api) => ({
  pos: api.camera.position.toArray(),
  cible: api.controls.target.toArray(),
  distance: api.camera.position.distanceTo(api.controls.target),
  near: api.camera.near, far: api.camera.far, zoom: api.camera.zoom,
  ortho: !!api.camera.isOrthographicCamera,
  projection: api.projection, vue: api.vueCadrage,
  pilotee: api.controls.object === api.camera,
  boite: projeterBoite(api),
});
"""

# Les vues, leur seuil et leur projection — recopiés NULLE PART : ils sont lus
# dans le module par les contrôles purs ci-dessus. Ici on ne se sert que du nom.
_VUES = ("libre", "iso", "face", "dessus", "profil")


def _distance_tache_3(rayon, marge, recul):
    """La distance de pose, par le chemin de la TÂCHE 3 et lui seul.

    Elle posait `d = rayon·marge·recul / tan(fov/2)` puis la caméra à `d·DIR`,
    de norme 1,25 : la distance vraie vaut donc 1,25·d. Aucun terme de cette
    fonction ne vient de viewer.js — c'est ce qui en fait un second chemin.
    """
    d = (rayon * marge * recul) / math.tan(math.radians(22.5))
    return 1.25 * d, d


def test_cadrer_POSE_VRAIMENT_la_camera_sous_LES_DEUX_projections():
    """LE BANC QUI MANQUAIT : cadrer() appelée, pas lue.

    Pour cinq vues et trois aspects — dont la demi-largeur exacte de la
    comparaison A/B — on enchaîne `projeter()` puis `orienter()`, la séquence
    même d'appliquerVue(), et on regarde ce que la caméra fait VRAIMENT :
      — aucun NaN (le mode d'échec de `fov` lu sur une ortho),
      — les huit sommets DANS le cadre,
      — les huit sommets ENTRE les plans de coupe,
      — les contrôles branchés sur la caméra active,
      — la distance et les plans de coupe ÉGAUX à ce que la tâche 3 posait,
        recalculés par une formule qui ne mentionne ni NORME_DIR ni demiHauteur.
    """
    cas = [{"vue": v, "w": w, "h": h}
           for v in _VUES for w, h in ((860, 824), (430, 824), (1400, 500))]
    sortie = json.loads(_node_trois(
        "projeter, orienter, cadrer, aspectDe, cadrageDe, orientationDe",
        _table_js("etabli/etabli.js", "PROJECTION_DE_VUE") + "\n"
        + "const CAS = " + json.dumps(cas) + ";\n" + """
      console.log(JSON.stringify(CAS.map((c) => {
        const api = monter(c.w, c.h);
        poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
        projeter(api, PROJECTION_DE_VUE[c.vue]);
        orienter(api, c.vue);
        const g = cadrageDe(1.5, aspectDe(api), 1.35, orientationDe(c.vue));
        return { ...etat(api), recul: g.recul, seuil: g.seuil };
      })));
    """))
    assert len(sortie) == len(cas)
    for c, e in zip(cas, sortie):
        quoi = f"{c['vue']} {c['w']}x{c['h']}"
        assert not e["boite"]["nan"], quoi
        assert e["boite"]["x"] <= 1 + 1e-9, f"{quoi} rogne en largeur : {e}"
        assert e["boite"]["y"] <= 1 + 1e-9, f"{quoi} rogne en hauteur : {e}"
        assert -1 < e["boite"]["zmin"] and e["boite"]["zmax"] < 1, quoi
        assert e["pilotee"], f"{quoi} : les contrôles pilotent une autre caméra"
        assert e["ortho"] == (c["vue"] != "libre"), quoi
        assert e["vue"] == c["vue"] and e["zoom"] == 1, quoi
        # LA TÂCHE 3, refaite sans un terme de viewer.js.
        distance, d3 = _distance_tache_3(1.5, 1.35, e["recul"])
        assert abs(e["distance"] - distance) < 1e-12 * distance, (quoi, e)
        assert abs(e["near"] - max(d3 / 1000, 0.001)) < 1e-15, (quoi, e)
        assert abs(e["far"] - d3 * 100) < 1e-9, (quoi, e)
    # Le repère de la tâche 3, à la sixième décimale : 4,0740 rayon en vue
    # libre à l'aspect 860/824. C'est le chiffre du banc d'aspect existant.
    libre = next(e for c, e in zip(cas, sortie)
                 if c["vue"] == "libre" and c["w"] == 860)
    assert abs(libre["distance"] / 1.5 - 4.073985) < 1e-6, libre["distance"]


def test_orienter_RECADRE_VRAIMENT_et_ne_pivote_pas_seulement():
    """« La vue nommée RECADRE, elle ne fait pas que pivoter » — vérifié.

    Ce que le fichier écrit n'était gardé par rien. Court-circuiter le
    recadrage laissait le banc vert, et le défaut est visible : le pire cas de
    largeur vaut 1,372·rayon en vue libre contre 1,000 sur un axe, donc les
    deux vues ne demandent PAS la même distance au même aspect.

    À l'aspect 0,4174 (430 × 1030, sous les deux seuils), la vue libre recule
    de 0,813030/0,4174 = 1,9478 et la vue de face de 0,592593/0,4174 = 1,4198 :
    un pivot sans recadrage laisserait la caméra 37 % trop loin. On mesure donc
    la DIRECTION et la DISTANCE, et le fait que la boîte remplit alors le cadre
    exactement — un modèle aussi large que son cube englobant touche les deux
    bords sous le seuil, à 1e-12.
    """
    sortie = json.loads(_node_trois("projeter, orienter, cadrageDe, "
                                    "orientationDe, aspectDe", """
      const api = monter(430, 1030);
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      projeter(api, "orthographique");
      orienter(api, "iso");
      const avant = etat(api);
      orienter(api, "face");
      const apres = etat(api);
      console.log(JSON.stringify({ aspect: aspectDe(api), avant, apres,
        reculFace: cadrageDe(1.5, aspectDe(api), 1.35,
                             orientationDe("face")).recul,
        reculIso: cadrageDe(1.5, aspectDe(api), 1.35,
                            orientationDe("iso")).recul }));
    """))
    aspect = sortie["aspect"]
    assert abs(aspect - 430 / 1030) < 1e-12
    # les deux reculs DIFFÈRENT : sans quoi le contrôle ne discriminerait rien
    assert sortie["reculIso"] > sortie["reculFace"] * 1.15, sortie
    # LA DIRECTION : la caméra est passée sur +Z, en face du centre.
    px, py, pz = sortie["apres"]["pos"]
    cx, cy, cz = sortie["apres"]["cible"]
    assert abs(px - cx) < 1e-12 and abs(py - cy) < 1e-12, sortie["apres"]
    assert pz - cz > 0, sortie["apres"]
    # LA DISTANCE : celle de « face », pas celle qu'« iso » avait laissée.
    attendue, _ = _distance_tache_3(1.5, 1.35, sortie["reculFace"])
    assert abs(sortie["apres"]["distance"] - attendue) < 1e-11, sortie
    assert abs(sortie["avant"]["distance"] - attendue) > 0.5, \
        "les deux vues tomberaient à la même distance : rien ne serait mesuré"
    # ET LE CADRE SUIT : la boîte fait 3 de large pour un rayon de 1,5, donc
    # elle touche exactement les deux bords sous le seuil.
    assert abs(sortie["apres"]["boite"]["x"] - 1.0) < 1e-12, sortie["apres"]


def test_cadrer_REPART_du_zoom_1_sinon_le_geste_d_avant_deteint():
    """Le zoom d'OrbitControls vit dans `camera.zoom` sous une ortho, et il
    survivrait au cadrage : « Face » atterrirait sur le grossissement du geste
    d'avant, et deux modèles chargés à la suite ne seraient plus comparables —
    ce que cadrer() existe pour garantir. Mesuré : à zoom 2,3, la boîte occupe
    2,3 fois le cadre, donc 130 % de sa largeur hors champ.
    """
    sortie = json.loads(_node_trois("projeter, orienter, cadrer", """
      const api = monter(430, 1030);
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      projeter(api, "orthographique");
      orienter(api, "face");
      const cadre = etat(api);
      /* le geste de l'utilisateur : la molette, sous une ortho */
      api.camera.zoom = 2.3;
      api.camera.updateProjectionMatrix();
      const zoome = etat(api);
      cadrer(api);
      console.log(JSON.stringify({ cadre, zoome, rendu: etat(api) }));
    """))
    # le zoom SORT bien du cadre — sans quoi le contrôle ne mesurerait rien
    assert sortie["zoome"]["zoom"] == 2.3
    assert abs(sortie["zoome"]["boite"]["x"] - 2.3) < 1e-9, sortie["zoome"]
    # …et cadrer() le reprend
    assert sortie["rendu"]["zoom"] == 1, sortie["rendu"]
    assert abs(sortie["rendu"]["boite"]["x"] - 1.0) < 1e-12, sortie["rendu"]
    assert abs(sortie["rendu"]["distance"] - sortie["cadre"]["distance"]) < 1e-12


def test_projeter_REPORTE_LA_POSE_et_ne_calcule_RIEN_de_plus():
    """LE CONTRAT RÉDUIT, dans les deux sens : ce qu'elle fait, et ce qu'elle
    ne fait plus.

    ELLE FAIT : changer la caméra active, lui reporter la pose, repointer les
    contrôles. La pose est OBSERVÉE — `controls.object = apres` fait aussitôt
    lire `apres.position` par OrbitControls, et une caméra d'arrivée laissée à
    sa position d'origine ferait sauter le point de vue partout où la bascule
    n'est pas suivie d'un cadrage : la vue B de _ouvrirComparaison(), qui est
    projetée avant d'avoir son GLB.

    ELLE NE FAIT PLUS : reporter la demi-hauteur visible. C'était juste et
    mesuré, et les trois appelants l'écrasaient à la ligne suivante. Le
    marqueur négatif ci-dessous garde la réduction — sans lui, le calcul
    inobservable reviendrait à la première retouche, et il faudrait à nouveau
    l'entretenir sans jamais pouvoir le mesurer.
    """
    sortie = json.loads(_node_trois("projeter, orienter, cadrer", """
      const api = monter(860, 824);
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      cadrer(api);
      const persp = etat(api);
      projeter(api, "orthographique");           /* SANS cadrer derrière */
      const ortho = etat(api);
      projeter(api, "perspective");
      const retour = etat(api);
      /* et sur une vue SANS modèle — le cas de _ouvrirComparaison() */
      const vide = monter(430, 824);
      vide.camera.position.set(11.5, 1.4, 8.1);
      vide.controls.target.set(7, -2, 0.5);
      projeter(vide, "orthographique");
      console.log(JSON.stringify({ persp, ortho, retour,
        posVide: vide.cameraOrthographique.position.toArray(),
        piloteeVide: vide.controls.object === vide.cameraOrthographique }));
    """))
    # LA POSE EST REPORTÉE, dans les deux sens. À 1e-9 et non à l'égalité :
    # `controls.update()` réécrit la position en la faisant passer par ses
    # coordonnées sphériques, et l'aller-retour coûte le dernier bit (mesuré :
    # 8,1 revient à 8,100000000000001). Sans la recopie, l'écart serait de
    # plusieurs unités — la caméra d'arrivée est encore à sa pose d'origine.
    for k in ("ortho", "retour"):
        for i in range(3):
            assert abs(sortie[k]["pos"][i] - sortie["persp"]["pos"][i]) < 1e-9,                 (k, sortie[k]["pos"], sortie["persp"]["pos"])
        assert sortie[k]["pilotee"], k
    assert sortie["ortho"]["ortho"] is True
    assert sortie["ortho"]["projection"] == "orthographique"
    assert sortie["retour"]["ortho"] is False
    # sur une vue sans modèle, la pose est TOUT ce qui garantit le point de vue
    for i, v in enumerate((11.5, 1.4, 8.1)):
        assert abs(sortie["posVide"][i] - v) < 1e-9, sortie["posVide"]
    assert sortie["piloteeVide"]
    # LA RÉDUCTION, gardée : plus aucun calcul de cadre dans projeter().
    proj = _code("lib3d/viewer.js").split(
        "export function projeter(api, mode)", 1)[1].split("\n}\n", 1)[0]
    for interdit in ("poserCadreOrtho", "poserCoupe", "cadreOrtho",
                     "Math.tan", "aspectDe", "zoom"):
        assert interdit not in proj, \
            f"projeter() recalcule « {interdit} » — que ses appelants écrasent"


def test_appliquerVue_laisse_la_vue_A_REFERENCE_et_pas_l_inverse():
    """LE DÉFAUT LE PLUS CHER DE CETTE TÂCHE, et rien ne le voyait.

    Chaque `orienter()` finit par un `cadrer()`, donc par un « change » que la
    synchronisation recopie vers l'AUTRE vue : dans une boucle sur les deux
    vues, LA DERNIÈRE CADRÉE GAGNE. Traiter A en premier faisait donc gagner B,
    et la vue A héritait du cadrage de B — position, cible, plans de coupe et
    bords ortho compris. `_ouvrirComparaison()` dit pourtant le contraire noir
    sur blanc : A est la référence, et si B est plus gros, c'est B qui déborde.

    MESURÉ ici même, sur le vrai viewer.js, la largeur projetée de A après un
    clic sur « Face » (1,000 = touche le cadre) :

        B deux fois plus gros, même centre   A = 0,500   (moitié trop petit)
        B décalé, le cas d'une extraction    A = 4,333   L'ÉCRAN EST NOIR

    Rien ne lève. Dans l'ordre B puis A, A revient à 1,000 dans les deux cas et
    c'est B qui déborde — ce que la comparaison promet.

    LE HARNAIS EST STRICT, DÉLIBÉRÉMENT : `synchroniser` et `appliquerVue` sont
    extraites VERBATIM et les cinq fonctions d'écran qu'elles appellent sont des
    coquilles. Le jour où appliquerVue() en appellera une sixième, node lèvera
    un ReferenceError et ce contrôle rougira — plutôt que de mesurer en silence
    une version de la fonction que la page n'a plus.
    """
    sortie = json.loads(_node_trois(
        "projeter as vraiProjeter, orienter, cadrer, cadreOrtho, aspectDe",
        "let gardeSync = 0;\n"
        "const projeter = (a, m) => { gardeSync++; return vraiProjeter(a, m); };\n"
        "const direRefus = () => {}, reposerCameraDuGizmo = () => {},\n"
        "      majBoutonProjection = () => {}, majBoutonsVue = () => {},\n"
        "      direGeometrie = () => {};\n"
        + _table_js("etabli/etabli.js", "PROJECTION_DE_VUE") + "\n"
        + _fonction_etabli("synchroniser") + "\n"
        + _fonction_etabli("appliquerVue") + "\n" + """
      const S = { vueA: null, vueB: null };
      function largeur(api) { return projeterBoite(api).x; }
      function scenario(nom, bl, bh, bp, bx, by, bz) {
        S.vueA = monter(430, 1030); poserModele(S.vueA, 3, 1.1, 0.4, 7, -2, 0.5);
        S.vueB = monter(430, 1030); poserModele(S.vueB, bl, bh, bp, bx, by, bz);
        cadrer(S.vueA); cadrer(S.vueB);
        synchroniser(S.vueA, S.vueB); synchroniser(S.vueB, S.vueA);
        cadrer(S.vueA);                       /* A est la référence à l'ouverture */
        const ouverture = largeur(S.vueA);
        gardeSync = 0;
        appliquerVue("face");
        return { nom, ouverture, a: largeur(S.vueA), b: largeur(S.vueB),
                 gardeSync };
      }
      console.log(JSON.stringify([
        scenario("B deux fois plus gros", 6, 2.2, 0.8, 7, -2, 0.5),
        scenario("B decale (extraction)", 3, 1.1, 0.4, 12, -2, 0.5),
      ]));
    """))
    assert len(sortie) == 2
    for r in sortie:
        # A EST CADRÉE SUR ELLE-MÊME : sa boîte fait 3 de large pour un rayon de
        # 1,5, donc elle touche exactement les deux bords sous le seuil.
        assert abs(r["a"] - 1.0) < 1e-9, \
            f"{r['nom']} : la vue A a pris le cadrage de B ({r['a']})"
        # …ET LA DIFFÉRENCE DE TAILLE SE VOIT, ce que la comparaison promet.
        assert r["b"] > r["a"] * 1.5, r
        # le contrôle ne mesurerait rien si A était déjà cadrée avant le clic
        assert abs(r["ouverture"] - 1.0) > 0.2, r
    # LE COMPTE DE LA SECONDE GARDE, celui que le commentaire de synchroniser()
    # affirme. Trois appels à projeter() par appliquerVue() : DEUX que la boucle
    # fait elle-même, UN que la synchronisation déclenche parce que la première
    # vue cadrée lève un « change » alors que l'autre est encore sur l'ancienne
    # projection. Ce chemin avait été déclaré mort ; il est vivant.
    for r in sortie:
        assert r["gardeSync"] == 3, r


def test_les_CINQ_VUES_vivent_dans_PLUSIEURS_tables_et_on_les_APPARIE():
    """UNE SIXIÈME ORIENTATION AJOUTÉE DANS viewer.js SEUL, et rien ne grince.

    `projeter(v, undefined)` : la garde de projeter() rend `null`, la projection
    ne change pas, `orienter()` cadre quand même, et la vue est rendue sous la
    MAUVAISE projection. Les `return null` de projeter() et d'orienter() ne
    gardent RIEN — non parce qu'ils seraient indiscriminants (projeter() rend
    bien `null` sur ce seul cas, et son mode sinon), mais parce que PERSONNE NE
    LES LIT : appliquerVue() jette les deux valeurs. Et les lire ne suffirait
    pas — un `if` muet laisserait le clic sans effet, quand cette page DIT
    toujours ses refus. Deux remèdes, tous deux nécessaires : appliquerVue()
    refuse EN LE DISANT, et ce contrôle apparie les tables.

    Les clés ne sont recopiées nulle part : les deux tables sont extraites, le
    balisage est lu, et c'est leur COMPARAISON qui est l'assertion.
    """
    # `_harnais_vue()` plutôt que la table seule : ses entrées citent DIR
    # et HAUT_Y, que le harnais extrait déjà de la vraie source.
    cles = json.loads(_node(
        _harnais_vue()
        + _table_js("etabli/etabli.js", "PROJECTION_DE_VUE") + "\n"
        + "console.log(JSON.stringify({ o: Object.keys(ORIENTATIONS),"
          " p: Object.keys(PROJECTION_DE_VUE) }));"))
    assert set(cles["o"]) == set(cles["p"]), cles
    assert len(cles["o"]) == 5, cles
    # LES BOUTONS sont un SOUS-ensemble : « libre » et « iso » n'en ont pas, la
    # bascule les porte. Mais aucun bouton ne peut nommer une vue absente.
    html = _lire("etabli/index.html")
    js = _lire("etabli/etabli.js")
    boutons = set(re.findall(r'data-vue="([a-z]+)"', html))
    # Les CLÉS, pas la prose : la première écriture ancrait le motif sur
    # « Depuis », si bien qu'une infobulle reformulée aurait fait rougir un
    # contrôle qui ne parle pas de son texte.
    titres = set(re.findall(r"^  (\w+):", _table_js(
        "etabli/etabli.js", "TITRE_VUE"), re.M))
    assert boutons == titres, (boutons, titres)
    assert boutons <= set(cles["p"]), (boutons, cles["p"])
    assert boutons == {"face", "dessus", "profil"}, boutons
    # …et le refus, qui rattrape ce que le banc ne peut pas voir à l'exécution.
    applique = _code("etabli/etabli.js").split(
        "function appliquerVue(nom)", 1)[1].split("\n}\n", 1)[0]
    assert "if (!PROJECTION_DE_VUE[nom]) {" in applique
    assert "direRefus(" in applique.split("if (!PROJECTION_DE_VUE[nom]) {", 1)[1]


# ── P. la graduation, le repère, et les millimètres qu'on n'invente pas ──────
# Demande de l'utilisateur, mot pour mot : dans les deux modes de manipulation,
# « une graduation visible » et « la possibilité de visualiser sur un repère 3D
# la position de chaque sélection par rapport à l'origine ».
#
# LE POINT DUR DE LA SECTION, ET IL EST DEHORS : un GLB N'A AUCUNE ÉCHELLE EN
# MILLIMÈTRES. Celle qui existe dans ce dépôt est fabriquée par
# `print3d.mettre_a_l_echelle(tris, cible_mm)` au moment d'écrire un STL, en
# portant la plus grande dimension à la cible. Afficher « 63 mm » sous un
# modèle que personne n'a mis à l'échelle serait une règle qui MENT — le pire
# des affichages, puisqu'il a l'autorité du chiffre. Les contrôles ci-dessous
# tiennent donc les deux moitiés : que la graduation EXISTE et se lise sous les
# deux projections, et qu'aucun millimètre ne sorte d'ailleurs que d'une taille
# cible POSÉE, par la règle même que Python appliquera.
#
# La moitié géométrique est EXÉCUTÉE, jamais lue : un miroir de texte ne voit
# pas un pas trop grand, et c'est la leçon que la plaque a payée deux fois.


def _constantes_viewer(*noms: str) -> str:
    """Les constantes de viewer.js, VERBATIM, pour le harnais node.

    Jumeau de `_constantes_plaque`, et pour la même raison : une valeur
    recopiée dans un banc est une valeur qui dérive, et le harnais mesurerait
    alors un seuil que le module n'applique plus.
    """
    js = _lire("lib3d/viewer.js")
    bouts = []
    for n in noms:
        m = re.search(r"^const " + n + r" = [^\n]*?;", js, re.M)
        assert m, f"constante {n} introuvable dans viewer.js"
        bouts.append(m.group(0))
    return "\n".join(bouts) + "\n"


def _mantisse(v: float):
    """La mantisse 1-2-5 d'un nombre, PAR UN SECOND CHEMIN.

    `pasGradue` la choisit par deux comparaisons sur `brut/décade` ; ici on
    repart du RÉSULTAT et on le décompose. Les deux chemins ne peuvent pas se
    tromper de la même façon.
    """
    k = math.floor(math.log10(v))
    m = v / (10.0 ** k)
    for candidat in (1.0, 2.0, 5.0):
        if abs(m - candidat) < 1e-9:
            return candidat
    return m


def test_la_GRADUATION_vit_dans_le_CANEVAS_PARTAGE_et_pas_dans_la_page():
    """« Dans les deux modes de manipulation » — et c'est la PLACE du code qui
    le garantit, pas une intention.

    Posée dans /etabli, la règle aurait eu à se souvenir de la projection
    courante à chaque bascule ; posée dans le canevas PARTAGÉ, elle vaut sous
    les deux par construction, et le Plateau du jour où il viendra l'aura sans
    une ligne (spec §12, la condition de convergence écrite d'avance).

    ELLE EST DANS LA BOUCLE, ET C'EST LE SEUL ENDROIT JUSTE : le pas se déduit
    de l'étendue VISIBLE, qui change à chaque molette. Posé au cadrage, il
    deviendrait une trame illisible au premier zoom — le contrôle
    `..._SUIT_le_ZOOM...` le mesure, celui-ci épingle le câblage.
    """
    code = _code("lib3d/viewer.js")
    # LES NEUF, et le compte est rigide : le recensement en énumérait sept
    # alors que `planDeTrame` et `axeDeVue` étaient exportées — une surface
    # publique sous-estimée de deux est une surface que personne ne relit.
    # Depuis la plaque façon slicer, TROIS de plus, et pour une seule raison :
    # les RÈGLES d'un plateau (dessinerRegles, effacerRegles) sont un
    # accessoire du regard, dessiné par le canevas partagé avec les libellés
    # que la page lui donne, et sensDesRegles est la pure qui DÉDUIT de la
    # table des orientations le coin d'origine — exportée parce que c'est la
    # géométrie du plateau (plaque.js) qui la consomme, une fois, pour que le
    # coin et les règles n'aient qu'une source. (graduationsDe est interne :
    # le banc l'extrait par son nom.)
    exportes = set(re.findall(r"^export (?:async )?function (\w+)\(",
                              code, re.M))
    attendus = {"pasGradue", "casesGraduees", "echelleMm", "etendueVisible",
                "planDeTrame", "axeDeVue", "majRepere", "marquerAuRepere",
                "montrerRepere", "creerCanevas", "vider", "orientationDe",
                "cadrageDe", "cadreOrtho", "aspectDe", "cadrer", "projeter",
                "orienter", "charger", "dessinerRegles", "effacerRegles",
                "sensDesRegles"}
    assert exportes == attendus, (exportes ^ attendus)
    # la boucle gradue AVANT de rendre : après, la trame reconstruite
    # n'apparaîtrait qu'à l'image suivante.
    boucle = code.split("(function boucle()", 1)[1].split("})();", 1)[0]
    assert boucle.index("majRepere(api);") \
        < boucle.index("renderer.render(scene, api.camera);")
    # DANS LA SCÈNE, jamais dans le modèle : vider() ne retire que api.racine,
    # et un repère greffé au modèle disparaîtrait au premier chargement.
    maj = _fonction_viewer("majRepere")
    assert "api.scene.add(e.groupe);" in maj
    assert "new THREE.GridHelper(" in maj
    # La négative est posée sur un texte AMPUTÉ de ses commentaires : la prose
    # de cette fonction NOMME `api.racine` pour dire d'où le repère ne vient
    # pas, et un `not in` nu serait satisfait par cette phrase-là — le défaut
    # que ce fichier a corrigé neuf fois.
    assert "api.racine" not in re.sub(r"/\*.*?\*/", "", maj, flags=re.S)
    assert "api.racine" in maj             # le témoin : la prose, elle, en parle
    # …et la reconstruction LIBÈRE, sinon dix paliers de zoom laissent dix
    # trames sur la carte — la fuite même que vider() existe pour empêcher.
    assert "libererLigne(e.trame);" in maj
    lib = _fonction_viewer("libererLigne")
    assert "geometry.dispose()" in lib and "material.dispose()" in lib
    # LE PIÈGE DE L'ORTHO, une fois de plus : `.fov` sur la caméra active rend
    # `undefined`, donc NaN, donc pas de graduation et aucune erreur.
    etendue = _fonction_viewer("etendueVisible")
    assert "api.cameraPerspective.fov" in etendue
    assert "cam.isOrthographicCamera" in etendue
    assert "api.camera.fov" not in code
    # la page IMPORTE ce que le module offre, et rien de plus
    js = _lire("etabli/etabli.js")
    assert "echelleMm, marquerAuRepere, montrerRepere" in js


def test_le_PAS_de_graduation_est_EXECUTE_sur_six_decades():
    """LA RÈGLE DU PAS, EXÉCUTÉE — un miroir de texte ne voit pas un pas faux.

    Quatre propriétés, et aucune n'est la formule recopiée :
      — la forme 1-2-5, retrouvée en DÉCOMPOSANT le résultat (_mantisse) ;
      — l'arrondi PAR LE BAS (`pas <= étendue/divisions`), qui est ce qui
        garantit qu'au moins `divisions` pas tiennent dans le champ ;
      — le nombre de pas visibles dans [10 ; 25), la seule promesse que la
        fonction fasse, et elle vaut à TOUS les zooms ;
      — l'invariance d'échelle et la monotonie, qui sont ce qui fait qu'un
        zoom continu ne fasse pas sauter la trame en tous sens.

    LES ÉTENDUES SONT IRRATIONNELLES ET BALAYENT SIX DÉCADES, délibérément :
    sur des puissances de dix rondes, toute erreur de décade tomberait pile sur
    un palier et le banc serait vert sur un pas dix fois trop grand.
    """
    etendues = [7.3e-4 * (1.37 ** i) for i in range(48)]
    sortie = json.loads(_node(
        _constantes_viewer("DIVISIONS_VISEES")
        + _fonction_viewer("pasGradue")
        + "const E = " + json.dumps(etendues) + ";\n"
        + "console.log(JSON.stringify({ pas: E.map((e) => pasGradue(e)),"
          " dix: E.map((e) => pasGradue(e * 10)),"
          " nul: [pasGradue(0), pasGradue(-1), pasGradue(Infinity),"
          " pasGradue(NaN), pasGradue(1, 0)] }));"))
    assert sortie["nul"] == [None] * 5, sortie["nul"]
    precedent = 0.0
    for e, pas in zip(etendues, sortie["pas"]):
        assert pas > 0, (e, pas)
        assert _mantisse(pas) in (1.0, 2.0, 5.0), (e, pas)
        # PAR LE BAS : au moins DIVISIONS_VISEES pas dans le champ.
        assert pas <= e / 10 * (1 + 1e-12), (e, pas)
        assert 10 <= e / pas < 25, (e, pas, e / pas)
        assert pas >= precedent, (e, pas, precedent)   # monotone
        precedent = pas
    # INVARIANCE D'ÉCHELLE : un modèle en mètres et le même en décimètres
    # reçoivent la MÊME trame, à un facteur dix près. Sans elle, la graduation
    # dépendrait de l'unité dans laquelle le GLB a été exporté.
    for pas, pas10 in zip(sortie["pas"], sortie["dix"]):
        assert abs(pas10 - pas * 10) < 1e-12 * pas10, (pas, pas10)


def test_les_CASES_couvrent_le_CHAMP_et_ne_se_refont_pas_a_chaque_image():
    """LE COMPTE DE CASES, EXÉCUTÉ. Trois choses en dépendent, et aucune n'est
    lisible dans du texte :

      — la trame ATTEINT le bord du champ (sinon la règle s'arrête avant ce
        qu'elle mesure) ET rejoint l'origine quand le modèle en est loin ;
      — elle est QUANTIFIÉE, sans quoi le compte changerait à chaque image de
        zoom et la géométrie se reconstruirait soixante fois par seconde ;
      — elle est BORNÉE, sinon un modèle posé à mille unités de l'origine
        fabriquerait des dizaines de milliers de segments.

    Le plancher est DÉRIVÉ et non choisi : la demi-hauteur visible vaut au plus
    12,5 pas (contrôle ci-dessus), donc la demi-largeur au plus 12,5·aspect ;
    48 couvre les aspects jusqu'à 3,84 quand les trois canevas de cette page
    valent 1,0437, 0,5218 et 2,8000. On le vérifie sur ces trois-là.
    """
    portees = [0.0, 0.3, 3.0, 7.0, 24.0, 40.0, 127.5, 1000.0]
    sortie = json.loads(_node(
        _constantes_viewer("CASES_MIN", "CASES_MAX", "CASES_QUANTUM")
        + _fonction_viewer("casesGraduees")
        + "const P = " + json.dumps(portees) + ";\n"
        + "console.log(JSON.stringify({ min: CASES_MIN, max: CASES_MAX,"
          " q: CASES_QUANTUM, cases: P.map((p) => casesGraduees(0.5, p)),"
          " nul: [casesGraduees(0, 10), casesGraduees(-1, 10),"
          " casesGraduees(NaN, 10)] }));"))
    mini, maxi, quantum = sortie["min"], sortie["max"], sortie["q"]
    assert sortie["nul"] == [0, 0, 0], sortie["nul"]
    for portee, cases in zip(portees, sortie["cases"]):
        assert mini <= cases <= maxi, (portee, cases)
        assert cases % quantum == 0, (portee, cases)
        # COUVRE, sauf quand le plafond a parlé — et il le dit alors en
        # rendant exactement le plafond, pas un compte tronqué au hasard.
        # COUVRE — sauf quand le plafond a mordu, et il doit alors avoir
        # VRAIMENT mordu : le quantum seul peut atteindre le plafond sans
        # rogner quoi que ce soit (portée 127,5 → 255 cases → 256).
        if cases * 0.5 < portee:
            assert cases == maxi and portee / 0.5 > maxi, (portee, cases)
    # LE PLANCHER COUVRE LES TROIS CANEVAS DE CETTE PAGE. 12,5 pas de
    # demi-hauteur au pire (voir le contrôle du pas), fois l'aspect.
    for w, h in ((860, 824), (430, 824), (1400, 500)):
        assert 12.5 * (w / h) <= mini, (w, h, mini)


def test_la_graduation_SUIT_le_ZOOM_sous_LES_DEUX_projections():
    """LE CŒUR DE LA DEMANDE, EXÉCUTÉ CONTRE LE VRAI three.js.

    « Dans les deux modes de manipulation » : on cadre pour de vrai, on zoome,
    et on regarde le pas que la graduation choisit — sous la perspective ET
    sous l'orthographique, dont les grandeurs ne sont PAS les mêmes (une ortho
    rend sa demi-hauteur en BORDS, une perspective en DISTANCE : c'est le piège
    que cadreOrtho nomme, et le transposer par analogie aurait donné une trame
    figée sous l'une des deux).

    MESURÉ ICI, sur la boîte 3 × 1,1 × 0,4 du harnais (rayon 1,5) dans un
    canevas 860 × 824, marge 1,35 — donc une demi-hauteur cadrée de
    1,25 × 1,5 × 1,35 = 2,53125 :

        zoom 0,5   étendue 10,1250   pas 1,00    10,125 pas visibles
        zoom 1     étendue  5,0625   pas 0,50    10,125
        zoom 2     étendue  2,5313   pas 0,20    12,656
        zoom 4     étendue  1,2656   pas 0,10    12,656
        zoom 8     étendue  0,6328   pas 0,05    12,656

    et les MÊMES cinq nombres sous l'orthographique, à 1e-12 — c'est cette
    égalité qui prouve que les deux projections sont graduées par la même
    étendue et non par deux formules qui se ressembleraient.

    ET LA TRAME NE SE REFAIT PAS POUR RIEN : trois appels au même zoom ne
    crient qu'UNE fois. Sans le mémo, la géométrie serait reconstruite à chaque
    image — invisible à l'écran, et payé en continu par le GPU.
    """
    zooms = [0.5, 1, 2, 4, 8]
    sortie = json.loads(_node_trois(
        "projeter, orienter, cadrer, majRepere, etendueVisible",
        _table_js("etabli/etabli.js", "PROJECTION_DE_VUE") + "\n"
        + "const ZOOMS = " + json.dumps(zooms) + ";\n" + """
      let cris = 0, dernier = null;
      function monterEcoute(w, h) {
        const api = monter(w, h);
        /* Le harnais donne un faux canevas : on lui ajoute le SEUL point de
           contact que majRepere() ait avec le DOM. S'il en gagnait un second,
           node leverait ici plutot que de mesurer en silence. */
        api.renderer.domElement.dispatchEvent = (ev) => {
          cris++; dernier = ev.detail; return true;
        };
        return api;
      }
      function serie(projection, vue) {
        const api = monterEcoute(860, 824);
        poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
        projeter(api, projection);
        orienter(api, vue);
        const cadree = etendueVisible(api).demiHauteur;
        const pas = ZOOMS.map((z) => {
          api.camera.zoom = z;
          api.camera.updateProjectionMatrix();
          const e = etendueVisible(api);
          majRepere(api);
          return { z, demi: e.demiHauteur, pas: dernier.pas,
                   cases: dernier.cases };
        });
        api.camera.zoom = 1;
        api.camera.updateProjectionMatrix();
        cris = 0;
        majRepere(api); majRepere(api); majRepere(api);
        const groupe = api.scene.children.filter(
          (o) => o.name === "lib3d-repere");
        return { cadree, pas, crisIdentiques: cris, groupes: groupe.length,
                 enfants: groupe[0].children.length };
      }
      console.log(JSON.stringify({
        perspective: serie("perspective", "libre"),
        ortho: serie("orthographique", "iso"),
      }));
    """))
    attendu = {0.5: 1.0, 1: 0.5, 2: 0.2, 4: 0.1, 8: 0.05}
    for nom in ("perspective", "ortho"):
        s = sortie[nom]
        assert abs(s["cadree"] - 2.53125) < 1e-9, (nom, s["cadree"])
        for ligne in s["pas"]:
            quoi = (nom, ligne)
            assert abs(ligne["pas"] - attendu[ligne["z"]]) < 1e-12, quoi
            assert 10 <= (2 * ligne["demi"]) / ligne["pas"] < 25, quoi
            # la trame COUVRE le champ, sinon la règle s'arrête avant ce
            # qu'elle mesure — le modèle est posé à 7 de l'origine.
            assert ligne["cases"] * ligne["pas"] >= 7, quoi
        # UN SEUL groupe dans la scène : un repère par vue, jamais un de plus.
        assert s["groupes"] == 1, s
        assert s["enfants"] == 2, s          # la trame ET les trois axes
        # LE MÉMO : trois appels au même zoom ne reconstruisent qu'une fois
        # (le premier, qui change de pas depuis le zoom 8 précédent).
        assert s["crisIdentiques"] == 1, s
    # LES DEUX PROJECTIONS SONT GRADUÉES PAR LA MÊME ÉTENDUE.
    for a, b in zip(sortie["perspective"]["pas"], sortie["ortho"]["pas"]):
        assert abs(a["demi"] - b["demi"]) < 1e-12, (a, b)
        assert a["pas"] == b["pas"], (a, b)


def test_AUCUN_MILLIMETRE_ne_sort_sans_une_TAILLE_CIBLE_posee():
    """L'ASSERTION LA PLUS IMPORTANTE DE LA TÂCHE, et elle est EXÉCUTÉE.

    Un GLB n'a aucune échelle. La page affiche donc des unités glTF, et ne
    passe aux millimètres QUE lorsqu'une taille cible a été posée et qu'une
    échelle a pu en être déduite. Une seule décision porte cela —
    `enMillimetres()` — et tout ce qui écrit une unité ou convertit un nombre
    passe par elle : deux littéraux « mm » sur cette page finiraient par se
    contredire sur une moitié de l'écran.

    LE COMPTE EST RIGIDE, et c'est ce qui mord : `REP.echelle` n'est lu ou
    écrit qu'en TROIS endroits — la décision, la conversion, et le recalcul de
    lireRepere(). Un quatrième site est un site qui pourrait afficher un
    millimètre sans passer par la garde.

    MUTATION VÉRIFIÉE : retirer le `if (!enMillimetres())` de fmtMesure rend
    « 0,00 » là où l'unité annonce des unités glTF, et le contrôle exécuté
    ci-dessous rougit.
    """
    code = _code("etabli/etabli.js")
    assert code.count("REP.echelle") == 3, code.count("REP.echelle")
    decision = _fonction_etabli("enMillimetres")
    assert "return REP.echelle !== null;" in decision
    fmt = _fonction_etabli("fmtMesure")
    assert "if (!enMillimetres()) {" in fmt
    assert fmt.index("if (!enMillimetres()) {") < fmt.index("REP.echelle")
    # L'ÉCHELLE EST DÉDUITE, jamais saisie : elle sort d'echelleMm(), qui rend
    # `null` sans cible > 0 — et elle se REFAIT à chaque lecture, sans quoi un
    # facteur hérité du modèle précédent survivrait au changement de maillage.
    lu = _fonction_etabli("lireRepere")
    assert "REP.echelle = echelleMm(plusGrandeDimension(), REP.cibleMm);" in lu
    grande = _fonction_etabli("plusGrandeDimension")
    assert "Math.max(t.x, t.y, t.z)" in grande
    # …ET ON L'EXÉCUTE. Les trois fonctions sont extraites VERBATIM, `REP` est
    # la seule chose que le harnais fournisse.
    sortie = json.loads(_node(
        "const REP = { echelle: null, cibleMm: null, pas: null };\n"
        + decision + "\n" + _fonction_etabli("uniteCourante") + "\n" + fmt
        + """
      const r = { sansCible: { u: uniteCourante(), v: fmtMesure(1.5) },
                  pasDeNombre: fmtMesure(NaN) };
      REP.echelle = 21;
      r.avecCible = { u: uniteCourante(), v: fmtMesure(1.5) };
      console.log(JSON.stringify(r));
    """))
    assert "mm" not in sortie["sansCible"]["u"], sortie
    assert "mm" not in sortie["sansCible"]["v"], sortie
    assert re.search(r"1[.,]500", sortie["sansCible"]["v"]), sortie
    assert sortie["avecCible"]["u"] == "mm", sortie
    # 1,5 unité × 21 mm/unité = 31,50 mm — la conversion, pas une décoration.
    assert re.search(r"31[.,]50", sortie["avecCible"]["v"]), sortie
    assert sortie["pasDeNombre"] == "—", sortie


def test_les_MILLIMETRES_viennent_de_la_MEME_regle_QUE_print3d():
    """LES DEUX CÔTÉS DE LA CHAÎNE, CONFRONTÉS.

    Le navigateur ne fabrique pas une seconde définition du millimètre : il
    reprend celle que Python appliquera au moment d'écrire le STL, à savoir
    `s = cible_mm / plus_grande` où `plus_grande` est la plus grande des trois
    dimensions de la boîte englobante (print3d.mettre_a_l_echelle). Deux règles
    voisines auraient divergé en silence — l'écran promettant 63 mm et le
    slicer en recevant 47.

    On EXÉCUTE donc les deux : `echelleMm` dans node, `mettre_a_l_echelle` en
    Python sur les mêmes triangles, et on compare le facteur MESURÉ sur le
    maillage mis à l'échelle. La boîte est 3,0 × 1,1 × 0,4 — trois côtés
    distincts, pour qu'une erreur d'axe ne tombe pas sur une égalité.
    """
    from app.services import print3d as P3
    tris = [((0.0, 0.0, 0.0), (3.0, 1.1, 0.4), (3.0, 0.0, 0.0)),
            ((0.0, 0.0, 0.0), (0.0, 1.1, 0.4), (3.0, 1.1, 0.4))]
    dims = [b[1] - b[0] for b in P3.bbox(tris)]
    assert dims == [3.0, 1.1, 0.4], dims
    mis = P3.mettre_a_l_echelle(tris, 63.0)
    dims_mm = [b[1] - b[0] for b in P3.bbox(mis)]
    assert abs(max(dims_mm) - 63.0) < 1e-9, dims_mm
    # le facteur que PYTHON a réellement appliqué, mesuré sur une AUTRE
    # dimension que celle qui porte la cible.
    facteur_python = dims_mm[1] / dims[1]
    sortie = json.loads(_node(
        _fonction_viewer("echelleMm")
        + "console.log(JSON.stringify({ e: echelleMm(3.0, 63.0),"
          " refus: [echelleMm(3, 0), echelleMm(3, -5), echelleMm(3, 'x'),"
          " echelleMm(3, null), echelleMm(3, undefined), echelleMm(0, 63),"
          " echelleMm(-2, 63), echelleMm(NaN, 63)] }));"))
    assert abs(sortie["e"] - facteur_python) < 1e-12, (sortie, facteur_python)
    assert abs(sortie["e"] - 21.0) < 1e-12, sortie
    # LA SÉVÉRITÉ DE LA FORGE 3D DES CARTES, reprise à la lettre : un nombre
    # > 0, sinon rien. `null` et non zéro — un facteur nul écrirait « 0,00 mm »
    # partout, ce qui est un mensonge de plus, pas un refus.
    #
    # CES HUIT-LÀ NE SONT EXÉCUTÉES QUE CÔTÉ JS, et il faut le dire : ce qui
    # est confronté aux deux implémentations est le FACTEUR, une ligne plus
    # haut. Python refuse de son côté (`mettre_a_l_echelle` lève sur une cible
    # ≤ 0), mais c'est son banc à lui qui le tient — pas celui-ci.
    assert sortie["refus"] == [None] * 8, sortie["refus"]
    # …et le refus de Python sur le même cas, pour que la symétrie ne soit pas
    # qu'une affirmation de commentaire.
    with pytest.raises(ValueError):
        P3.mettre_a_l_echelle(tris, 0)
    # …et le même verdict est écrit dans core.js, d'où la règle est reprise.
    core = _lire("cardforge/js/core.js")
    assert "if (!isFinite(mm) || mm <= 0)" in core


def test_la_TAILLE_CIBLE_se_pose_dans_le_rail_et_se_REFUSE_en_le_disant():
    """La cible est la SEULE chose que l'utilisateur pose, et le seul endroit
    d'où des millimètres puissent naître. Elle se refuse comme tout le reste
    de cette page : dans la barre du bas, jamais par une boîte du navigateur
    (test_aucun_refus_ne_passe_par_alert).

    DEUX REFUS, ET LE SECOND N'EST PAS DÉFENSIF : sans modèle mesuré il n'y a
    pas de dénominateur, la cible serait acceptée et ne convertirait rien —
    un champ qui ment sur ce qu'il vient de faire.

    `change` ET NON `input`, qui se déclenche à CHAQUE frappe : « 63 »
    poserait d'abord une échelle à 6, et « 0,5 » traverserait deux refus rouges
    (« 0 », puis « 0, » que Number() rend zéro) avant d'être accepté. Un refus
    qui clignote à la frappe est un refus qu'on cesse de lire.
    """
    poser = _fonction_etabli("poserCible")
    assert "if (!Number.isFinite(cible) || !(cible > 0)) {" in poser
    assert poser.count("direRefus(") == 2
    # vide = « tel quel », le mot même de la route (cible_mm absent)
    assert 'if (texte === "") {' in poser
    assert "REP.cibleMm = null;" in poser
    rendu = _fonction_etabli("rendreRepere")
    # LA NOTE QUI DIT CE QUE LES MILLIMÈTRES NE SONT PAS, et elle n'était
    # épinglée par rien : `mettre_a_l_echelle` recentre en X/Y et pose Z au
    # sol, donc une pièce lue ici à −31,50 n'arrivera pas à −31,50 dans le
    # slicer. Sans cette phrase, le rail laisse croire à des coordonnées de
    # plateau — et une note qu'aucun banc ne tient est une note qui s'en va.
    assert "PAS des coordonnées de plateau" in rendu
    assert "recentre en X/Y et pose Z au sol" in rendu
    assert 'id="rCible"' in rendu and 'type="number"' in rendu
    assert '$("#rCible").addEventListener("change"' in rendu
    assert '$("#rCible").addEventListener("input"' not in _code("etabli/etabli.js")
    assert 'poserCible($("#rCible").value)' in rendu


def test_la_POSITION_lue_est_celle_du_MODELE_et_NON_de_l_ETALEMENT():
    """LE PIÈGE LE PLUS CHER DE CETTE TÂCHE, ET IL EST MUET.

    Sur la plaque, une pièce n'est PAS là où le modèle la met : `etaler()`
    glisse un BERCEAU entre elle et son parent, et sa boîte monde porte donc un
    décalage d'AFFICHAGE. Lu tel quel, il donnerait des coordonnées fausses
    « par rapport à l'origine » — avec l'autorité du chiffre, et sans que rien
    ne grince. C'est ce que poserGizmo() refuse de laisser partir au serveur ;
    on ne l'affiche pas davantage.

    CE CONTRÔLE FAISAIT SA PROPRE MISE EN SCÈNE, et c'était son défaut : il
    fabriquait le berceau à la main (`new THREE.Group(); berceau.add(piece)`),
    donc il mesurait une structure qu'il avait lui-même posée. Le jour où
    l'étalement en aurait glissé une autre, il serait resté vert pendant que
    toutes les coordonnées du rail devenaient fausses DU DÉCALAGE EXACT. On
    fait donc tourner le VRAI `etaler()`, sur le vrai module.

    LE SECOND CHEMIN EST LE DÉPLACEMENT MESURÉ : on relève la position monde de
    chaque pièce AVANT et APRÈS l'étalement, et leur différence doit être ce que
    `decalageEtalement()` annonce. L'une passe par `getWorldPosition` de la
    PIÈCE, l'autre par les colonnes de translation du BERCEAU et de son parent :
    deux lectures indépendantes de la même mise en place.

    L'ENVELOPPE TOURNE ET CHANGE D'ÉCHELLE (0,3 ; −0,7 ; 0,45 rad et 2 ; 0,5 ;
    1,75), avec une translation de (−4 ; 9 ; 3) qui doit s'annuler d'elle-même :
    c'est le cas d'une réparation en Z, où `mesh_edit._ROT["Z"]` n'est plus
    l'identité, et trois asymétries pour qu'aucune erreur d'indice ne tombe sur
    un zéro.
    """
    sortie = json.loads(_node_trois(
        "cadrer",
        _importer_plaque("etaler, ranger, decalageEtalement, estEtalee") + """
      const api = monter(860, 824);
      const racine = new THREE.Group();
      /* L'ENVELOPPE de mesh_edit.reparer : indexee, et elle CONTIENT les
         pieces — donc elle n'en est pas une (voir piecesDe). */
      const enveloppe = new THREE.Group();
      enveloppe.userData.indexGltf = 13;
      enveloppe.rotation.set(0.3, -0.7, 0.45);
      enveloppe.scale.set(2, 0.5, 1.75);
      enveloppe.position.set(-4, 9, 3);
      racine.add(enveloppe);
      const cotes = [[0.9, 0.4, 0.2, 1.3, 0, -0.7],
                     [0.5, 1.1, 0.3, -0.8, 0.6, 0.4],
                     [0.7, 0.7, 0.15, 0.2, -1.2, 1.1]];
      const pieces = cotes.map(([l, h, p, x, y, z], i) => {
        const g = new THREE.Group();
        g.name = "piece_" + i;
        g.userData.indexGltf = i;
        g.position.set(x, y, z);
        g.add(new THREE.Mesh(new THREE.BoxGeometry(l, h, p),
                             new THREE.MeshBasicMaterial()));
        enveloppe.add(g);
        return g;
      });
      api.scene.add(racine); api.racine = racine;
      racine.updateMatrixWorld(true);
      cadrer(api);
      const monde = (o) => o.getWorldPosition(new THREE.Vector3()).toArray();
      const avant = pieces.map(monde);
      /* LE VRAI ETALEMENT, sur le vrai module. */
      const compte = etaler(api).pieces.length;
      racine.updateMatrixWorld(true);
      const apres = pieces.map(monde);
      const lu = (o) => {
        const d = decalageEtalement(api, o);
        return { d: d.decalage.toArray(), etale: d.etale };
      };
      const dits = pieces.map(lu);
      /* un maillage SOUS une piece : il herite de la correction de sa piece */
      const feuille = lu(pieces[0].children[0]);
      /* UN LEURRE : meme `indexGltf` qu'une piece, mais ce n'est PAS elle.
         GLTFLoader clone un noeud reference deux fois, et `associations` rend
         au clone le meme {nodes: i}. Pose APRES l'etalement, il n'est dans
         aucun berceau. */
      const leurre = new THREE.Group();
      leurre.userData.indexGltf = 0;
      leurre.position.set(3, 3, 3);
      enveloppe.add(leurre);
      racine.updateMatrixWorld(true);
      const leurreLu = lu(leurre);
      /* l'enveloppe CONTIENT des pieces : sa lecture se DIT douteuse */
      const enveloppeLue = lu(enveloppe);
      /* le berceau EST bien le parent aujourd'hui — on le CONSTATE plutot que
         de le supposer, et c'est tout ce que ce banc a le droit d'en dire. */
      const berceauEstParent = pieces.every((g) => g.parent !== enveloppe);
      /* le decalage LOCAL que l'etalement a pose : c'est lui que la conversion
         par A_parent transforme, et les deux doivent differer. */
      const locaux = pieces.map((g) => g.parent.position.toArray());
      ranger(api);
      racine.updateMatrixWorld(true);
      const range = { lu: lu(pieces[0]), etalee: estEtalee(api),
                      monde: pieces.map(monde) };
      console.log(JSON.stringify({ compte, avant, apres, dits, feuille,
                                   enveloppeLue, berceauEstParent, locaux,
                                   leurreLu, range }));
    """))
    assert sortie["compte"] == 3, sortie["compte"]
    assert sortie["berceauEstParent"] is True, sortie
    # ── LE SECOND CHEMIN : le déplacement MESURÉ contre le décalage ANNONCÉ ──
    deplacements = [[b - a for a, b in zip(av, ap)]
                    for av, ap in zip(sortie["avant"], sortie["apres"])]
    for i, (dep, dit) in enumerate(zip(deplacements, sortie["dits"])):
        assert dit["etale"] is False, (i, dit)
        for a, b in zip(dit["d"], dep):
            assert abs(a - b) < 1e-9, (i, dit["d"], dep)
    # …ET LES TROIS ONT VRAIMENT BOUGÉ, chacune différemment : sur un étalement
    # nul, « annoncer zéro » serait juste par accident.
    for i, dep in enumerate(deplacements):
        assert math.hypot(*dep) > 0.1, (i, dep)
    assert len({tuple(round(v, 6) for v in d) for d in deplacements}) == 3, \
        deplacements
    # LA CONVERSION FAIT VRAIMENT QUELQUE CHOSE : le décalage MONDE n'est pas
    # le décalage LOCAL que l'étalement a posé dans le berceau. Sous une
    # enveloppe tournée et mise à l'échelle, les deux diffèrent — et un
    # « rendre la position du berceau telle quelle » passerait sinon inaperçu.
    for i, (dep, loc) in enumerate(zip(deplacements, sortie["locaux"])):
        assert math.dist(dep, loc) > 1.0, (i, dep, loc)
    # UN MAILLAGE SOUS UNE PIÈCE hérite de la correction de sa pièce.
    assert sortie["feuille"] == sortie["dits"][0], (sortie["feuille"],
                                                    sortie["dits"][0])
    # UN NŒUD QUI CONTIENT DES PIÈCES se DIT douteux plutôt que de rendre un
    # zéro qu'on prendrait pour une correction faite.
    assert sortie["enveloppeLue"]["etale"] is True, sortie["enveloppeLue"]
    assert sortie["enveloppeLue"]["d"] == [0, 0, 0], sortie["enveloppeLue"]
    # ── L'INDEXATION EST PAR IDENTITÉ D'OBJET, ET C'EST MESURABLE ────────────
    # Un nœud portant le MÊME `indexGltf` qu'une pièce sans être elle — ce que
    # GLTFLoader produit en clonant un nœud référencé deux fois, `associations`
    # rendant au clone le même {nodes: i} — serait ATTRAPÉ par une table à clé,
    # dont le parent, qui n'est pas un berceau, donnerait un décalage bidon
    # avec `etale: false` : une réponse confiante et fausse. Par identité, il ne
    # correspond à rien et se dit douteux. (Le cas n'est pas vérifié sur cette
    # chaîne d'import ; il est bon marché à fermer, on le ferme.)
    assert sortie["leurreLu"]["etale"] is True, sortie["leurreLu"]
    assert sortie["leurreLu"]["d"] == [0, 0, 0], sortie["leurreLu"]
    # RANGÉE, il n'y a plus rien à retrancher — et surtout pas de faux doute.
    assert sortie["range"]["etalee"] is False, sortie["range"]
    assert sortie["range"]["lu"] == {"d": [0, 0, 0], "etale": False}, \
        sortie["range"]["lu"]
    # …et les pièces sont revenues EXACTEMENT où elles étaient.
    for av, ap in zip(sortie["avant"], sortie["range"]["monde"]):
        for a, b in zip(av, ap):
            assert abs(a - b) < 1e-9, (av, ap)
    # ── ET LE CALCUL VIT DANS plaque.js, chez qui pose le berceau ────────────
    # La page ne peut plus le refaire en supposant « le berceau est le parent
    # de la pièce » : cet invariant est INTERNE au module d'étalement.
    js = _code("etabli/etabli.js")
    # Depuis la plaque façon slicer, la page ne retranche plus un DÉCALAGE :
    # elle demande au module la BOÎTE DANS LA POSE ASSEMBLÉE (boiteModele), la
    # seule lecture juste pour une pièce TOURNÉE non symétrique — le banc
    # dédié en fait la preuve sur une pièce en L. decalageEtalement reste
    # l'API mesurée ici ; la page, elle, ne la recompose pas.
    assert "boiteModele(S.vueA, o)" in js
    assert "function boiteModele" not in js
    assert "function decalageEtalement" not in js
    assert "berceau" not in js
    plq = _code("lib3d/plaque.js")
    assert "export function decalageEtalement(api, objet)" in plq
    dec = _fonction_plaque("decalageEtalement")
    # ── ELLE LIT L'ÉTAT, ELLE NE DEVINE RIEN ────────────────────────────────
    # ASSERTION STRUCTURELLE, et elle ne peut pas être autre chose : aujourd'hui
    # le berceau EST le parent de la pièce, donc une version qui le devine rend
    # exactement les mêmes nombres et aucune mesure ne les sépare. Ce qui
    # distingue les deux, c'est d'où vient l'entrée — et c'est précisément ce
    # que le jour d'un second Group ferait diverger, en silence. On épingle
    # donc la ligne qui va CHERCHER l'entrée dans la table.
    assert "etat.berceaux.map((e) => [e.piece, e])" in dec
    assert "const e = n && parPiece.get(n);" in dec
    # …et le calcul du décalage se fait entre le berceau et le parent INSCRITS
    assert "e.berceau.getWorldPosition" in dec
    assert "e.parent.getWorldPosition" in dec
    # ── ET LES DEUX ÉCHECS RENDENT LE MÊME VERDICT ──────────────────────────
    # ASSERTION STRUCTURELLE, et elle ne peut pas être autre chose : l'état
    # « berceau détaché » est INATTEIGNABLE aujourd'hui — oublierPlaque() fait
    # ranger() avant tout changement de modèle, et la vue B n'est jamais
    # étalée. Aucune exécution ne peut donc l'exercer. Il reste que c'était le
    # seul endroit de cette fonction où un état cassé produisait une réponse
    # CONFIANTE (`etale: false`), c'est-à-dire un zéro qu'on aurait pris pour
    # une correction faite. Objet hors pièce ou berceau détaché : dans les deux
    # cas la lecture n'a pas pu être corrigée, et elle se dit douteuse.
    assert "return { decalage: zero, etale: true };" in dec
    assert "etale: !e" not in dec
    # …et le repère 3D ne MARQUE rien sur la plaque : la croix tomberait à
    # l'endroit du MODÈLE, c'est-à-dire à côté de la pièce que l'on voit.
    lu = _fonction_etabli("lireRepere")
    assert "marquerAuRepere(S.vueA, PLQ.active ? [] : m.points)" in lu


def test_la_MARQUE_relie_la_selection_a_l_ORIGINE_et_BORNE_son_compte():
    """« Visualiser sur un repère 3D la position de chaque sélection par
    rapport à l'origine » — la seconde moitié de la demande, et trois nombres
    ne la tiennent pas : il faut que le CHEMIN jusqu'à l'origine se voie.

    Six segments par point, et chacun a sa raison :
      — la DESCENTE jusqu'au plan de la trame, sans quoi un point flottant en
        l'air ne se rapporte à aucune case ;
      — les DEUX JAMBES qui rejoignent l'origine par x puis par z, qui sont la
        lecture graphique de « à quelle distance » ;
      — la CROIX, sans laquelle un point posé sur le plan se confond avec le
        pied de sa propre descente. Elle mesure un quart de PAS, donc elle est
        à l'échelle de la graduation et non d'un modèle que ce module ne
        connaît pas.
    Chaque segment porte la couleur de l'axe qu'il longe — la table est
    extraite de la source, jamais recopiée.

    ET LE COMPTE EST BORNÉ. Un modèle de la Bibliothèque porte près de mille
    nœuds ; « tout cocher » fabriquerait six mille segments à chaque redessin
    du panneau. Au-delà de MARQUES_MAX la lecture n'est de toute façon plus une
    lecture, et les chiffres du rail s'abrègent au même moment.

    LE SECOND CHEMIN : Python reconstruit l'ensemble des six segments attendus
    et le compare comme un ENSEMBLE — l'ordre d'émission n'est pas la règle, et
    l'épingler aurait fait rougir un simple réordonnancement.
    """
    q = [1.7, -0.85, 2.35]           # trois coordonnées distinctes et non nulles
    sortie = json.loads(_node_trois(
        "cadrer, majRepere, marquerAuRepere",
        _table_js("lib3d/viewer.js", "COULEUR_AXE") + "\n"
        + _constantes_viewer("MARQUES_MAX")
        + "const Q = " + json.dumps(q) + ";\n" + """
      const api = monter(860, 824);
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      cadrer(api);
      const trace = majRepere(api);
      const groupe = api.scene.children.find((o) => o.name === "lib3d-repere");
      const pose = [{ x: Q[0], y: Q[1], z: Q[2] }];
      const rendu = marquerAuRepere(api, pose);
      const marque = groupe.children[groupe.children.length - 1];
      const p = Array.from(marque.geometry.attributes.position.array);
      const c = Array.from(marque.geometry.attributes.color.array);
      /* La couleur d'un segment, RETROUVÉE dans la table : on ne recopie pas
         trois entiers dans le banc, on demande au module lequel c'est. */
      const teintes = {};
      for (const axe of ["x", "y", "z"]) {
        const t = new THREE.Color(COULEUR_AXE[axe]);
        teintes[axe] = [t.r, t.g, t.b];
      }
      const segments = [];
      for (let i = 0; i < p.length; i += 6) {
        /* MEME DECALAGE que la position : les deux attributs ont trois
           composantes par sommet, donc six par segment. */
        const j = i;
        let axe = "?";
        for (const nom of ["x", "y", "z"]) {
          if (teintes[nom].every((v, k) => Math.abs(v - c[j + k]) < 1e-6)) {
            axe = nom;
          }
        }
        segments.push({ a: p.slice(i, i + 3), b: p.slice(i + 3, i + 6), axe });
      }
      /* LA BORNE : bien plus de points que MARQUES_MAX, tous distincts. */
      const foule = [];
      for (let i = 0; i < MARQUES_MAX * 3; i++) {
        foule.push({ x: i * 0.11, y: i * -0.07, z: i * 0.03 });
      }
      const bornes = marquerAuRepere(api, foule);
      const apresFoule = groupe.children[groupe.children.length - 1]
        .geometry.attributes.position.count;
      /* ET LE RETRAIT : une sélection vidée ne laisse pas sa croix derrière. */
      const vide = marquerAuRepere(api, []);
      console.log(JSON.stringify({
        pas: trace.pas, rendu, segments, max: MARQUES_MAX, bornes, apresFoule,
        vide, enfantsApresVide: groupe.children.length }));
    """))
    assert sortie["rendu"] == 1, sortie["rendu"]
    assert abs(sortie["pas"] - 0.5) < 1e-12, sortie["pas"]
    croix = sortie["pas"] / 4
    x, y, z = q
    # LE SECOND CHEMIN : l'ensemble attendu, écrit d'après la demande et non
    # d'après le code — la descente, les deux jambes, les trois bras.
    attendu = {
        (("y",) + tuple(sorted([(x, y, z), (x, 0.0, z)]))),
        (("x",) + tuple(sorted([(x, 0.0, z), (0.0, 0.0, z)]))),
        (("z",) + tuple(sorted([(0.0, 0.0, z), (0.0, 0.0, 0.0)]))),
        (("x",) + tuple(sorted([(x - croix, y, z), (x + croix, y, z)]))),
        (("y",) + tuple(sorted([(x, y - croix, z), (x, y + croix, z)]))),
        (("z",) + tuple(sorted([(x, y, z - croix), (x, y, z + croix)]))),
    }
    obtenu = set()
    for s in sortie["segments"]:
        bouts = sorted([tuple(round(v, 5) for v in s["a"]),
                        tuple(round(v, 5) for v in s["b"])])
        obtenu.add((s["axe"],) + tuple(bouts))
    # CINQ DÉCIMALES et non quinze : la géométrie est un Float32BufferAttribute,
    # donc 2,35 y revient 2,349999905. Arrondir plus fin ferait rougir la
    # simple précision, qui n'est pas la règle qu'on mesure.
    attendu = {(a[0],) + tuple(tuple(round(v, 5) for v in p) for p in a[1:])
               for a in attendu}
    assert len(sortie["segments"]) == 6, sortie["segments"]
    assert obtenu == attendu, (sorted(obtenu), sorted(attendu))
    # LA BORNE MORD : trois fois trop de points, et la géométrie s'arrête net.
    assert sortie["bornes"] == sortie["max"], sortie
    assert sortie["apresFoule"] == sortie["max"] * 12, sortie   # 6 segments
    # …et une sélection vidée retire la croix, sans laisser un objet mort.
    assert sortie["vide"] == 0, sortie
    assert sortie["enfantsApresVide"] == 2, sortie   # la trame ET les axes


def test_la_MARQUE_meurt_avec_le_MODELE_qu_elle_decrit():
    """LA TRAME ET LES AXES DÉCRIVENT LE REGARD ; LA MARQUE DÉCRIT LE MODÈLE.

    `vider()` ne retire délibérément qu'`api.racine` — c'est ce qui permet à la
    règle de survivre d'un maillage à l'autre. Mais les croix, elles, sont aux
    coordonnées d'une sélection qui vient de disparaître, et `charger()` fait
    `vider()` PUIS attend le téléchargement : sur un GLB de plusieurs
    mégaoctets, l'écran gardait plusieurs secondes une grille, des axes et les
    croix d'un modèle absent. Un état que ce canevas ne pouvait pas produire
    avant que le repère n'existe.

    ELLE NE PEUT PAS SE RÉPARER SEULE : le module ne retient pas les points
    qu'on lui a passés. L'invariant se tient donc chez celui qui EFFACE, sinon
    le prochain écran qui réutilisera ce canevas partagé héritera des croix
    sans hériter de l'écouteur qui les nettoie.
    """
    sortie = json.loads(_node_trois(
        "cadrer, majRepere, marquerAuRepere, vider",
        """
      const api = monter(860, 824);
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      cadrer(api);
      majRepere(api);
      const groupe = api.scene.children.find((o) => o.name === "lib3d-repere");
      const compte = () => groupe.children.filter((o) => o.isLineSegments).length;
      marquerAuRepere(api, [{ x: 1, y: 2, z: 3 }, { x: -4, y: 0.5, z: 2 }]);
      const avant = compte();
      vider(api);
      const apres = compte();
      /* …et la TRAME et les AXES, eux, SURVIVENT : ils decrivent le regard. */
      const survivants = groupe.children.map((o) => o.type).sort();
      console.log(JSON.stringify({ avant, apres, survivants,
                                   visible: groupe.visible,
                                   racine: api.racine }));
    """))
    assert sortie["avant"] == 3, sortie      # la trame, les axes, la marque
    assert sortie["apres"] == 2, sortie      # …la marque est partie avec lui
    assert sortie["racine"] is None, sortie
    assert sortie["survivants"] == ["GridHelper", "LineSegments"], sortie
    # …ET LA RÈGLE RESTE ALLUMÉE : vider() efface ce qui décrit le MODÈLE, il
    # n'éteint pas ce qui décrit le REGARD. Un `montrerRepere(api, false)` glissé
    # là laisserait le canevas sans graduation jusqu'au prochain chargement.
    assert sortie["visible"] is True, sortie
    # …et c'est bien `vider()` qui en répond, chez celui qui efface.
    vide = _fonction_viewer("vider")
    assert "marquerAuRepere(api, []);" in vide


def test_le_REPERE_est_MASQUE_pour_la_vignette_et_RETABLI_meme_si_elle_leve():
    """LA VIGNETTE MONTRE UN OBJET, PAS UN ATELIER. Grille, axes et croix
    vivent dans `api.scene` — la même scène que la capture photographie :
    laissés visibles, ils poseraient un quadrillage en travers de la carte de
    la Bibliothèque, exactement le défaut que le gizmo a déjà valu.

    L'ÉTAT D'AVANT EST RENDU, jamais supposé : `montrerRepere()` rend la
    visibilité précédente, et une vue dont le repère n'est pas encore construit
    rend `false`. Supposer « visible » le rallumerait de force sur une vue qui
    ne l'avait pas.

    ET LE RÉTABLISSEMENT EST DANS LE `finally`, comme celui du gizmo : une
    capture qui lève laisserait sinon la règle éteinte pour le reste de la
    session, sans qu'aucun message ne l'explique.
    """
    bloc = _capture()
    i_masque = bloc.index("const repereVu = montrerRepere(vue, false);")
    i_rendu = bloc.index("vue.renderer.render(")
    i_finally = bloc.index("} finally {")
    i_retabli = bloc.index("montrerRepere(vue, repereVu);")
    assert i_masque < i_rendu < i_finally < i_retabli
    # l'état est RELU, pas supposé — et il vaut `false` par défaut.
    # CAPTURÉE HORS DU `try`, comme la visibilité du gizmo : à l'intérieur, une
    # instruction levante insérée un jour laisserait la sentinelle à sa valeur
    # par défaut et éteindrait le repère pour toute la session.
    assert "const repereVu = montrerRepere(vue, false);" in bloc
    assert bloc.index("const repereVu") < bloc.index("try {")
    montrer = _fonction_viewer("montrerRepere")
    assert "const avant = e.groupe.visible;" in montrer
    assert "return avant;" in montrer
    # et la capture ne gagne AUCUN filet de plus : ses deux `catch` sont ceux
    # de la fabrication et de l'envoi, et un troisième dirait qu'un échec de
    # repère est un échec d'écriture. (Le compte des `catch` est tenu par
    # test_un_echec_de_vignette_ne_fait_jamais_echouer_l_ecriture ; on épingle
    # ici que le masquage n'a rien ajouté.)
    nu = _code("etabli/etabli.js").split(
        "async function capturerVignette", 1)[1].split(FIN_FONCTION, 1)[0]
    assert nu.count("montrerRepere(") == 2       # masquer, et rétablir
    # LE TÉMOIN : la prose en parle DAVANTAGE que le code — c'est ce qui rend
    # la négative ci-dessus nécessaire, et un compte figé sur la prose aurait
    # rougi à la première phrase ajoutée.
    assert bloc.count("montrerRepere(") > nu.count("montrerRepere(")


def test_le_bloc_du_REPERE_est_HORS_des_onglets_et_se_LIT():
    """« Une graduation VISIBLE » : un cinquième onglet l'aurait cachée neuf
    fois sur dix, au moment même où l'on coche des pièces dans « Parties » pour
    lire où elles sont. Le bloc vit donc SOUS les panneaux, toujours affiché —
    et il n'est PAS dans la table des panneaux, sinon les onglets le
    masqueraient en passant.

    L'ORDRE DE DÉMARRAGE EST PORTEUR, et c'est un appariement : rendreParties()
    finit par lireRepere(), qui écrit dans deux zones que rendreRepere() vient
    de créer. Dans l'autre ordre, la PREMIÈRE ligne du démarrage déréférence
    `null`, l'import lève, et la page entière reste morte — pas de
    chronologie, pas de canevas, pas même un refus lisible.

    Et les RÈGLES CSS comptent autant que le balisage : sans elles le bloc
    EXISTE et ne se lit pas. Les hauteurs sont POSÉES, jamais déduites —
    l'en-tête d'etabli.css raconte ce que coûte l'intrinsèque (998 rangées de
    2 px), et trois colonnes de chiffres sans largeur fixe ne s'alignent pas
    d'une rangée à la suivante.
    """
    html, css = _lire("etabli/index.html"), _lire("etabli/etabli.css")
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    assert '<div class="repere" id="repere"></div>' in html
    # HORS des onglets : ni bouton, ni entrée dans la table des panneaux.
    assert 'data-onglet="repere"' not in html
    panneaux = code.split("const PANNEAUX = {", 1)[1].split("};", 1)[0]
    assert "repere" not in panneaux, panneaux
    assert html.count('class="on"') + html.count('class="on actif"') == 4
    # L'APPARIEMENT DES DEUX LIGNES DE DÉMARRAGE, ancré en colonne 0 :
    # `rendreRepere();` n'est appelé qu'ici, mais `rendreParties();` l'est
    # aussi ailleurs, indenté — une ancre lâche prendrait cet appel-là.
    assert re.search(r"^rendreRepere\(\);$.*?^rendreParties\(\);$",
                     js, re.M | re.S), "rendreRepere doit précéder rendreParties"
    # LES SITES D'APPEL, ET ILS COUVRENT TOUT : la queue de rendreParties
    # (chargement, clic, granularité, plaque) et la case cochée, qui ne
    # redessine PAS le panneau et n'y serait donc jamais atteinte.
    # CINQ appels DIRECTS — la queue de rendreParties, la case cochée, les DEUX
    # issues de poserCible, et celui que programmerLecture() diffère — plus
    # DEUX sites programmés : le glissement du gizmo et l'écoute du pas. Ce
    # dernier a rejoint la coalescence parce que `dispatchEvent` est SYNCHRONE
    # et que majRepere() vit dans la boucle de rendu : lu directement, il
    # exécutait ses 2 ms au milieu de l'image. Les comptes sont rigides pour
    # que tout nouveau site se dise.
    assert code.count("lireRepere();") == 5, code.count("lireRepere();")
    assert code.count("programmerLecture();") == 2, \
        code.count("programmerLecture();")
    poser = _fonction_etabli("poserCible")
    assert poser.count("lireRepere();") == 2
    queue = code.split("$(\"#btnSeparer\").addEventListener", 1)[1]
    assert "lireRepere();" in queue.split(FIN_FONCTION, 1)[0]
    cases = code.split('box.querySelectorAll("input[type=checkbox]")', 1)[1] \
                .split("}));", 1)[0]
    assert "lireRepere();" in cases
    # ── LA NOTE LA PLUS IMPORTANTE DOIT ÊTRE LA PLUS TROUVABLE ──────────────
    # L'avertissement « pas de vue ≠ pas de modèle » vit dans le docbloc de
    # programmerLecture(). Or qui câble un déplacement au clavier demande
    # « d'où vient le pas ? » et atterrit sur la déclaration de REP, mille neuf
    # cents lignes plus haut — qui ne disait que « il vient de l'évènement ».
    # Le renvoi est donc épinglé LÀ, sur la clé elle-même : un commentaire que
    # personne ne trouve est un commentaire qui n'existe pas, et le lot suivant
    # écrit sur le disque.
    decl = js.split("const REP = {", 1)[0].rsplit("/*", 1)[1]
    assert "PAS DE VUE" in decl and "programmerLecture" in decl, decl[-400:]
    prog = _fonction_etabli("programmerLecture")
    assert "POUR LE LOT SUIVANT" in _lire("etabli/etabli.js")
    # LE PAS VIENT DU MODULE PARTAGÉ, par évènement : la page ne le recalcule
    # jamais de son côté — deux sources pour un même nombre divergeraient.
    assert '$("#vueA canvas").addEventListener("lib3d:graduation"' in js
    assert "REP.pas = ev.detail.pas;" in code
    # …et l'écoute PROGRAMME plutôt que de lire : `dispatchEvent` est synchrone
    # et majRepere() vit dans la boucle de rendu.
    ecoute = code.split('addEventListener("lib3d:graduation"', 1)[1] \
                 .split("});", 1)[0]
    assert "programmerLecture();" in ecoute
    assert "pasGradue" not in code
    # les règles qui rendent le bloc LISIBLE
    assert ".repere {" in css
    assert "max-height" in css.split(".repere-lecture {", 1)[1].split("}", 1)[0]
    ligne = css.split(".repere-ligne {", 1)[1].split("}", 1)[0]
    assert "min-height: 20px" in ligne
    colonne = css.split(".repere-ligne span {", 1)[1].split("}", 1)[0]
    assert "width: 10ch" in colonne and "tabular-nums" in colonne
    # …ET L'ELLIPSE : « -1 234,567 » fait dix glyphes, ce qu'un GLB exporté
    # d'un CAD en millimètres produit couramment. Sans elle, un chiffre trop
    # long serait rogné EN SILENCE — le pire des affichages pour une mesure.
    assert "text-overflow: ellipsis" in colonne
    assert ".repere-ligne.etale b" in css


# ── P (suite). LES CÂBLAGES, et non plus les seuls calculs ───────────────────
# CE QUE LA PREMIÈRE ÉCRITURE DE CETTE SECTION A MANQUÉ, et il faut le dire en
# tête parce que c'est un défaut de MÉTHODE, pas une assertion oubliée. Ses dix
# contrôles exerçaient les règles PURES — le pas, les cases, l'échelle, le
# décalage — et rien ne vérifiait qu'elles SERVENT à quelque chose. Une revue a
# posé vingt-six mutations : dix sont revenues vertes, et toutes les dix
# portaient sur un câblage, jamais sur un calcul. `decalageEtalement` était
# exercée mais son USAGE ne l'était pas ; `montrerRepere` était gardée par son
# APPEL mais pas par son EFFET ; le pas ANNONCÉ était mesuré mais la trame
# DESSINÉE pouvait porter le double.
#
# La règle qu'on en tire, et que les contrôles ci-dessous appliquent : une
# fonction pure se mesure sur ses nombres, mais une fonction pure ne prouve rien
# tant que le banc n'a pas lu CE QUI EST DESSINÉ ou CE QUI EST ÉCRIT à l'écran.
# On lit donc ici la géométrie rendue et le balisage produit, jamais l'intention.


def _importer_plaque(quoi: str) -> str:
    """La ligne d'import du VRAI /lib3d/plaque.js pour le harnais node.

    Les déclarations `import` sont hoistées en ESM : posée dans le corps du
    contrôle, celle-ci est résolue avant tout le reste. On charge le module
    LIVRÉ, à l'octet près — la raison même d'être de `_node_trois`.
    """
    chemin = (FRONT / "lib3d" / "plaque.js").resolve().as_uri()
    return f"import {{ {quoi} }} from {json.dumps(chemin)};\n"


def _constantes_etabli(*noms: str) -> str:
    """Les constantes d'etabli.js, VERBATIM, pour le harnais node.

    Jumeau de `_constantes_viewer` et de `_constantes_plaque`. `LIGNES_REPERE`
    recopié à la main aurait fait mesurer une borne que la page n'applique
    plus — et la mutation qui la met à zéro serait repassée au vert.
    """
    js = _lire("etabli/etabli.js")
    bouts = []
    for n in noms:
        m = re.search(r"^const " + n + r" = [^\n]*?;", js, re.M)
        assert m, f"constante {n} introuvable dans etabli.js"
        bouts.append(m.group(0))
    return "\n".join(bouts) + "\n"


# Le faux rail : le contrat MINIMAL que le bloc du repère consomme du DOM.
#
# IL EST STRICT, ET C'EST TOUT SON INTÉRÊT — la première écriture ne l'était
# pas, et cela masquait une PAGE MORTE. Sa doublure fabriquait n'importe quel
# sélecteur à la demande (`zones[s] = zones[s] || {…}`) : renommer `id=
# "repereLecture"` dans le GABARIT en laissant `$("#repereLecture")` intact
# laissait le banc vert, alors qu'en navigateur `$` rend `null`, `lireRepere()`
# lève sur `null.innerHTML`, et comme le démarrage tourne À L'IMPORT, la page
# ENTIÈRE reste morte. Le mode d'échec que le commentaire de démarrage décrit,
# et que le banc ne pouvait pas voir.
#
# DEUX PROPRIÉTÉS LE CORRIGENT, et elles imitent le navigateur :
#   — un sélecteur inconnu LÈVE, comme `null.innerHTML` ;
#   — un id ne devient joignable QU'APRÈS avoir été écrit dans un `innerHTML`,
#     ce que fait un accesseur en écriture. La doublure lit donc le balisage
#     que rendreRepere() produit VRAIMENT, au lieu de le supposer.
#
# ET SA SEULE AMORCE EST L'ID D'index.html, injecté par `_faux_rail()` : c'est
# l'appariement au réel qui manquait. `_MONTAGE` a le sien (les clés d'`api`
# sont épinglées sur la vraie déclaration) ; deux doublures, deux contrats.
_FAUX_RAIL = """
const zones = {};
const nouvelle = () => ({
  addEventListener() {}, _html: "", _val: "",
  /* `.value` COERCE EN CHAINE, comme un vrai champ : y ecrire le nombre 63
     rend la chaine "63", et un banc qui ne le simule pas laisserait passer un
     code qui compare `.value` a un nombre. */
  get value() { return this._val; },
  set value(v) { this._val = String(v); },
  get innerHTML() { return this._html; },
  set innerHTML(v) {
    this._html = String(v);
    /* Un id n'existe qu'une fois ECRIT, comme dans un vrai document. */
    for (const m of this._html.matchAll(/id="([^"]+)"/g)) {
      if (!zones["#" + m[1]]) zones["#" + m[1]] = nouvelle();
    }
  },
});
zones["__ANCRE__"] = nouvelle();      /* le seul id que porte index.html */
const $ = (s) => {
  const z = zones[s];
  /* Ce que le navigateur ferait : `null.innerHTML` leve. */
  if (!z) throw new TypeError("selecteur mort : " + s);
  return z;
};
const esc = (v) => String(v ?? "").replace(/[&<>"']/g, (c) => (
  { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const direRefus = (m) => { zones.refus = String(m); };
const direGeometrie = () => {};
const REP = { cibleMm: null, echelle: null, pas: null };
const SEL = { granularite: "maillage", retenus: new Set() };
const PLQ = { active: false, pieces: [], masquees: new Set(),
              teintes: new Map(), partages: 0, vides: 0, axe: null,
              pas: null, courante: null, repereAvant: null,
              planApplique: false, planFichier: null, enCours: false,
              aEnvoyer: null, sauvegarde: null };
const S = { vueA: null, geoA: null };
const lignesLues = () => {
  const html = $("#repereLecture").innerHTML;
  const nombres = [...html.matchAll(/<span>([^<]*)<\\/span>/g)].map((m) => m[1]);
  return { rangees: (html.match(/repere-ligne/g) || []).length,
           nombres, html: html.replace(/\\s+/g, " ").trim() };
};
"""


def _faux_rail() -> str:
    """Le faux rail, AMORCÉ SUR L'ID QUE PORTE index.html.

    L'id n'est pas écrit dans le banc : il est LU dans le gabarit. Le renommer
    d'un côté seulement fait lever la doublure, exactement comme le navigateur
    lèverait — c'est l'appariement qui manquait, et sans lequel un id renommé
    dans le gabarit laissait le banc vert sur une page morte.
    """
    html = _lire("etabli/index.html")
    m = re.search(r'<div class="repere" id="([^"]+)"></div>', html)
    assert m, "le bloc du repère est introuvable dans index.html"
    return _FAUX_RAIL.replace("__ANCRE__", "#" + m.group(1))


def _bloc_repere(js: str = None) -> str:
    """Le bloc du repère d'etabli.js, des millimètres à la lecture.

    Borné aux DEUX bouts et vérifié : `enMillimetres` l'ouvre, l'écouteur
    `etabli:charge` qui suit lireRepere() le ferme. Une borne qui raterait
    rendrait un extrait vide, sur lequel toute négative serait verte — c'est le
    défaut que `_plaque_bloc` a payé, et sa leçon vaut ici.
    """
    code = js if js is not None else _code("etabli/etabli.js")
    bloc = code.split("function enMillimetres()", 1)[1] \
               .split('document.addEventListener("etabli:charge"', 1)[0]
    for temoin in ("function fmtMesure(", "function mesurerRetenus(",
                   "function lireRepere(", "repere-ligne"):
        assert temoin in bloc, temoin
    return bloc


def test_la_LECTURE_suit_le_GESTE_du_gizmo():
    """LE GIZMO EST L'UN DES DEUX MODES DE MANIPULATION, et le lot s'appelle
    « la manipulation MESURÉE ». Sans cette ligne, on tire une poignée pendant
    que les trois chiffres et la croix du repère restent à la position d'AVANT
    le geste : une règle qui ne bouge pas sous ce qu'elle mesure, avec
    l'autorité du chiffre.

    L'ancrage est DANS l'écouteur `objectChange` et APRÈS `noterAttente(` : la
    file d'écriture d'abord — c'est elle qui porte la conséquence — la lecture
    ensuite.
    """
    code = _code("etabli/etabli.js")
    ecouteur = code.split('GIZMO.addEventListener("objectChange"', 1)[1] \
                   .split("\n    });", 1)[0]
    assert "noterAttente(" in ecouteur
    assert "programmerLecture();" in ecouteur
    assert ecouteur.index("noterAttente(") \
        < ecouteur.index("programmerLecture();")
    # ── ET ELLE EST PROGRAMMÉE, PAS APPELÉE, parce que le prix est MESURÉ ────
    # Sur un modèle de 1 000 nœuds, hors navigateur, lireRepere() coûte
    # 0,363 ms à une sélection et 2,057 ms à douze (2,068 à vingt-quatre — le
    # palier est celui de LIGNES_REPERE, qui borne les rangées écrites), soit
    # 12 % d'une trame à 60 Hz. Et node ne simule RIEN de la remise en page que
    # le navigateur ajoute : `innerHTML` y est une affectation de chaîne.
    # Or `objectChange` est émis à chaque mouvement de souris, donc
    # possiblement plusieurs fois par image : appelée directement, la lecture
    # aurait payé ce prix autant de fois pour un seul rendu, et les lectures
    # intermédiaires ne seraient jamais apparues à l'écran.
    prog = _fonction_etabli("programmerLecture")
    assert "requestAnimationFrame(" in prog
    # PAS DE MINUTERIE : `rAF` cale la lecture sur l'horloge du rendu, si bien
    # que les chiffres et le dessin décrivent la MÊME image. La négative est
    # posée sur la FONCTION — la doctrine n'appartient qu'à elle, et
    # l'interdire au fichier entier légiférerait pour du code sans rapport.
    assert "setTimeout" not in prog
    # …et la coalescence est EXÉCUTÉE, pas lue.
    sortie = json.loads(_node(
        "let lectures = 0;\n"
        "const file = [];\n"
        "const requestAnimationFrame = (f) => file.push(f);\n"
        "const lireRepere = () => { lectures++; };\n"
        "let _lectureProgrammee = 0;\n" + prog + """
      /* cent evenements dans la MEME image : un seul rendez-vous */
      for (let i = 0; i < 100; i++) programmerLecture();
      const programmees = file.length;
      file.splice(0).forEach((f) => f());
      const apresImage = lectures;
      /* …et l'image SUIVANTE reprogramme : la lecture n'est pas perdue */
      for (let i = 0; i < 100; i++) programmerLecture();
      file.splice(0).forEach((f) => f());
      console.log(JSON.stringify({ programmees, apresImage, total: lectures }));
    """))
    assert sortie["programmees"] == 1, sortie   # cent évènements, un rendez-vous
    assert sortie["apresImage"] == 1, sortie
    assert sortie["total"] == 2, sortie         # …et l'image suivante compte
    # ICI on épingle que le gizmo passe par la COALESCENCE et jamais par un
    # appel direct ; l'énumération des sites est tenue par
    # test_le_bloc_du_REPERE_est_HORS_des_onglets_et_se_LIT.
    assert "lireRepere();" not in ecouteur


def test_la_LECTURE_de_CHAQUE_selection_est_EXECUTEE():
    """LE CŒUR DE LA DEMANDE, ENFIN EXÉCUTÉ — « la position de CHAQUE sélection
    par rapport à l'origine ».

    `mesurerRetenus()` n'avait AUCUNE couverture, et quatre mutations la
    traversaient en vert : le centre de la boîte remplacé par `objet.position`
    (la lecture cesse d'être rapportée à l'origine), le décalage d'étalement
    calculé et non retranché, une seule sélection au lieu de toutes, et la
    borne de lignes mise à zéro. On lit donc ici LE BALISAGE PRODUIT, et non le
    code qui prétend le produire.

    LE PIÈGE QUE LES DONNÉES DÉSAMORCENT : `objet.position` est LOCALE, et sur
    un maillage posé à l'origine elle vaut la boîte. Les trois maillages ont
    donc chacun une géométrie DÉCENTRÉE (`geometry.translate`) ET une pose
    propre, si bien que `position` ne coïncide avec le centre monde pour aucun
    des trois — et le troisième vit sous un parent translaté ET mis à l'échelle.

    LE SECOND CHEMIN : Python recompose les centres attendus par une
    arithmétique de translations et d'échelles, là où three.js passe par un
    Box3 sur les sommets transformés.
    """
    sortie = json.loads(_node_trois(
        "echelleMm, marquerAuRepere, majRepere, cadrer, dessinerRegles",
        _importer_plaque("etaler, ranger, boiteModele, plateauDe")
        + _faux_rail() + _constantes_etabli("LIGNES_REPERE")
        + _fonction_etabli("enMillimetres") + "\n"
        + _fonction_etabli("uniteCourante") + "\n"
        + _fonction_etabli("fmtMesure") + "\n"
        + _fonction_etabli("plusGrandeDimension") + "\n"
        + _fonction_etabli("mesurerRetenus") + "\n"
        + _fonction_etabli("rendreRepere") + "\n"
        + _fonction_etabli("rendreCible") + "\n"
        + _fonction_etabli("poserCible") + "\n"
        # lireRepere() gradue aussi le plateau depuis la plaque slicer : la
        # VRAIE graduerPlateau, sur le vrai dessinerRegles.
        + _fonction_etabli("graduerPlateau") + "\n"
        + _fonction_etabli("lireRepere") + "\n" + """
      const api = monter(860, 824);
      const racine = new THREE.Group();
      const cube = (l, h, p, tx, ty, tz) => new THREE.Mesh(
        new THREE.BoxGeometry(l, h, p).translate(tx, ty, tz),
        new THREE.MeshBasicMaterial());
      /* geometrie DECENTREE + pose propre : `position` ne vaut la boite pour
         aucun des trois, et le troisieme vit sous un parent transforme. */
      const m1 = cube(1, 1, 1, 0.7, -0.3, 1.1);
      m1.name = "fond-matiere"; m1.position.set(2, 1, -4);
      const m2 = cube(2, 0.5, 3, -1.25, 2.5, 0.4);
      m2.name = "illustration";
      const parent = new THREE.Group();
      parent.position.set(5, -1, 0); parent.scale.set(2, 2, 2);
      const m3 = cube(1, 1, 1, 0.5, 0.5, 0.5);
      m3.name = "cadre"; m3.position.set(1, 0, 2);
      parent.add(m3); racine.add(m1); racine.add(m2); racine.add(parent);
      api.scene.add(racine); api.racine = racine;
      racine.updateMatrixWorld(true);
      S.vueA = api;
      const boite = new THREE.Box3().setFromObject(racine);
      S.geoA = { taille: boite.getSize(new THREE.Vector3()) };
      cadrer(api);
      /* la boucle de rendu cree le repere : ici on la remplace par un appel. */
      REP.pas = majRepere(api).pas;
      rendreRepere();

      const r = { taille: S.geoA.taille.toArray(),
                  plusGrande: plusGrandeDimension(),
                  lignes: LIGNES_REPERE,
                  /* LES ZONES JOIGNABLES viennent du GABARIT, pas du banc :
                     rendreRepere() les a ecrites, la doublure les a vues. */
                  zones: Object.keys(zones).filter((k) => k[0] === "#").sort() };
      /* LE SECOND REFUS, EXERCE : sans modele mesure il n'y a pas de
         denominateur, et une cible acceptee ne convertirait rien. */
      const memoire = S.geoA;
      S.geoA = null;
      /* le champ porte une SAISIE avant le refus : sans cela, « il est vide
         apres » serait vrai meme si personne ne le reecrivait. */
      $("#rCible").value = "80";
      r.sansModele = { rendu: poserCible("63"), refus: zones.refus,
                       cible: REP.cibleMm, champ: $("#rCible").value };
      S.geoA = memoire;
      zones.refus = undefined;
      lireRepere();
      r.vide = lignesLues();
      /* LES TROIS, dans l'ordre d'insertion du Set. */
      for (const m of [m1, m2, m3]) SEL.retenus.add(m.uuid);
      SEL.retenus.add("uuid-d-un-materiau");
      lireRepere();
      r.trois = lignesLues();
      /* LA MEME LECTURE EN MILLIMETRES : la conversion traverse le balisage. */
      r.pose = poserCible("63");
      /* LE CHAMP REDIT CE QUI EST APPLIQUE, meme apres un refus : sans cela,
         deux sources de verite pour la seule valeur d'ou naissent les mm. */
      const refuses = {};
      for (const essai of ["-5", "abc", "0"]) {
        $("#rCible").value = essai;
        refuses[essai] = { rendu: poserCible(essai), champ: $("#rCible").value,
                           cible: REP.cibleMm };
      }
      r.refuses = refuses;
      r.mm = lignesLues();
      r.echelleTete = zones["#repereEchelle"].innerHTML;
      poserCible("");

      /* LA PLAQUE, POUR DE VRAI : on appelle le module, pas une mise en scene.
         Les trois maillages deviennent des pieces indexees, `etaler()` les
         envoie chacune ailleurs, et le rail doit relire LES MEMES NOMBRES. */
      const monde = (o) => new THREE.Box3().setFromObject(o)
        .getCenter(new THREE.Vector3()).toArray();
      m1.userData.indexGltf = 0;
      m2.userData.indexGltf = 1;
      m3.userData.indexGltf = 2;
      const avantEtalement = [m1, m2, m3].map(monde);
      const etalement = etaler(api);
      racine.updateMatrixWorld(true);
      r.pieces = etalement.pieces.length;
      r.deplacees = [m1, m2, m3].map(monde);
      PLQ.active = true;
      PLQ.pieces = etalement.pieces;
      lireRepere();
      r.etalee = lignesLues();
      r.avantEtalement = avantEtalement;
      const groupe = api.scene.children.find((o) => o.name === "lib3d-repere");
      r.marquesEtalee = groupe.children.filter((o) => o.isLineSegments).length;
      ranger(api);
      racine.updateMatrixWorld(true);
      PLQ.active = false; PLQ.pieces = [];
      lireRepere();
      r.marquesRangee = groupe.children.filter((o) => o.isLineSegments).length;

      /* LES DEUX BORNES : celle des LIGNES du rail (LIGNES_REPERE) et celle
         des CROIX du repere (MARQUES_MAX), toutes deux franchies. Le clic dans
         le canevas AJOUTE sans vider : trente selections est atteignable. */
      SEL.retenus.clear();
      for (let i = 0; i < 30; i++) {
        const m = cube(0.2, 0.2, 0.2, 0, 0, 0);
        m.name = "piece_" + i; m.position.set(i, 0, 0);
        racine.add(m); SEL.retenus.add(m.uuid);
      }
      racine.updateMatrixWorld(true);
      lireRepere();
      r.foule = lignesLues();
      r.marques = groupe.children[groupe.children.length - 1]
        .geometry.attributes.position.count / 12;      /* 6 segments par croix */
      console.log(JSON.stringify(r));
    """))

    def nombre(s):
        return float(s.replace("−", "-").replace(" ", "")
                     .replace(" ", "").replace(",", "."))

    # LE SECOND CHEMIN : les centres monde, recomposés à la main.
    attendus = [(2 + 0.7, 1 - 0.3, -4 + 1.1),            # m1 : pose + géométrie
                (-1.25, 2.5, 0.4),                        # m2 : géométrie seule
                (5 + 2 * (1 + 0.5), -1 + 2 * 0.5, 2 * (2 + 0.5))]   # m3 : parent
    # …et AUCUN d'eux n'est la `position` de son objet : c'est ce qui rend la
    # mutation « centre → position » visible.
    for attendu, pose in zip(attendus, [(2, 1, -4), (0, 0, 0), (1, 0, 2)]):
        assert attendu != pose, attendu

    # LE SECOND REFUS DE poserCible, EXÉCUTÉ et non compté : sans modèle
    # mesuré, la cible est REFUSÉE et ne se pose pas. Un simple compte de
    # `direRefus(` laissait passer la garde neutralisée.
    sans = sortie["sansModele"]
    assert sans["rendu"] is False, sans
    assert sans["cible"] is None, sans
    assert "aucun modèle mesuré" in (sans["refus"] or ""), sans
    # LE CHAMP PORTAIT « 80 » et l'état ne porte rien : c'est l'état qui gagne.
    assert sans["champ"] == "", sans
    # LES ZONES QUE LE GABARIT A VRAIMENT ÉCRITES. La doublure ne fabrique
    # rien : ces quatre-là existent parce que rendreRepere() les a posées dans
    # un `innerHTML`, et le fait que lireRepere() les atteigne sans lever est
    # la preuve que les sélecteurs et le balisage parlent des mêmes ids.
    assert sortie["zones"] == ["#rCible", "#repere", "#repereEchelle",
                              "#repereLecture"], sortie["zones"]
    assert sortie["vide"]["rangees"] == 0, sortie["vide"]
    assert "aucune sélection" in sortie["vide"]["html"], sortie["vide"]

    trois = sortie["trois"]
    assert trois["rangees"] == 3, trois        # CHAQUE sélection, pas la première
    lus = [nombre(v) for v in trois["nombres"]]
    assert len(lus) == 9, trois
    for i, attendu in enumerate(attendus):
        for k in range(3):
            assert abs(lus[3 * i + k] - attendu[k]) < 5e-4, (i, k, lus, attendus)
    # le matériau retenu n'a pas de position, et le rail le DIT
    assert "sans position" in trois["html"], trois["html"]
    # …et les noms viennent du GLB, pas d'un compteur
    for nom in ("fond-matiere", "illustration", "cadre"):
        assert nom in trois["html"], nom

    # LA PLUS GRANDE DIMENSION vient d'un VRAI Box3, pas d'un nombre écrit à la
    # main : la boîte englobe m1, m2 et m3 transformés.
    assert abs(sortie["plusGrande"] - max(sortie["taille"])) < 1e-9, sortie
    assert sortie["plusGrande"] > 8, sortie["taille"]

    # LES MILLIMÈTRES TRAVERSENT LE BALISAGE, et par la seule règle de print3d.
    assert sortie["pose"] is True, sortie
    facteur = 63.0 / sortie["plusGrande"]
    mm = [nombre(v) for v in sortie["mm"]["nombres"]]
    for i, attendu in enumerate(attendus):
        for k in range(3):
            assert abs(mm[3 * i + k] - attendu[k] * facteur) < 5e-3, (i, k, mm)
    assert "mm" in sortie["echelleTete"], sortie["echelleTete"]
    # ── LE CHAMP ET L'ÉTAT NE DIVERGENT JAMAIS ──────────────────────────────
    # `#rCible` était LU et jamais réécrit, et rendreRepere() ne passe qu'à
    # l'import : après « -5 » refusé, l'écran montrait le champ à −5 et le rail
    # à « cible 63 mm ». Deux sources de vérité pour la seule valeur d'où des
    # millimètres peuvent naître, avec le champ qui ment sur ce qui est
    # appliqué. Les trois refus sont EXÉCUTÉS, « abc » compris — il manquait au
    # harnais.
    for essai, r in sortie["refuses"].items():
        assert r["rendu"] is False, (essai, r)
        assert r["cible"] == 63, (essai, r)      # la cible posée tient
        assert r["champ"] == "63", (essai, r)    # …et le champ le redit

    # ── LA PLAQUE : LE RAIL LIT LES MÊMES NOMBRES, ASSEMBLÉ ET ÉTALÉ ────────
    # C'est la formulation la plus forte de la promesse, et elle passe par le
    # VRAI `etaler()` : les trois pièces sont physiquement ailleurs — on le
    # vérifie — et pourtant les neuf chiffres du rail n'ont pas bougé.
    assert sortie["pieces"] == 3, sortie["pieces"]
    for i, (av, ap) in enumerate(zip(sortie["avantEtalement"],
                                     sortie["deplacees"])):
        assert math.dist(av, ap) > 0.1, (i, av, ap)   # elles ONT bougé
    etalee = [nombre(v) for v in sortie["etalee"]["nombres"]]
    assert len(etalee) == 9, sortie["etalee"]
    for i, attendu in enumerate(attendus):
        for k in range(3):
            assert abs(etalee[3 * i + k] - attendu[k]) < 5e-4, \
                (i, k, etalee, attendus)
    assert "la plaque est une VUE" in sortie["etalee"]["html"]
    # …et la croix ne marque RIEN sur la plaque, mais revient au rangement.
    assert sortie["marquesEtalee"] == 2, sortie      # la trame et les axes seuls
    assert sortie["marquesRangee"] == 3, sortie      # …plus la marque

    # LA BORNE DE LIGNES est celle du module, pas un nombre de banc.
    foule = sortie["foule"]
    assert foule["rangees"] == sortie["lignes"], foule
    assert sortie["lignes"] >= 1, sortie
    assert f"et {30 - sortie['lignes']} autre(s)" in foule["html"], foule["html"]
    # ── ET LA TRONCATURE DES CROIX SE DIT AUSSI ─────────────────────────────
    # `marquerAuRepere` borne le nombre de croix et RENDAIT déjà ce compte, que
    # l'appelant jetait : le rail annonçait ses lignes tronquées et taisait ses
    # croix manquantes. C'est la faute que ce même bloc reproche ailleurs —
    # « une mesure qu'on fait et qu'on tait se lit comme une perte ».
    assert sortie["marques"] < 30, sortie["marques"]
    assert f"{30 - sortie['marques']} croix non tracée(s)" in foule["html"], \
        foule["html"]


def test_les_AXES_traversent_l_ORIGINE_et_le_repere_n_est_DECALE_de_rien():
    """« Par rapport à l'ORIGINE » — encore faut-il que l'origine soit là où le
    repère la met. Trois mutations passaient : des axes de longueur NULLE (la
    capacité entièrement absente), des DEMI-DROITES au lieu d'axes (ils ne
    traversent plus l'origine, et « à gauche de zéro » cesse de se lire), et le
    groupe entier POSÉ AILLEURS — trame, axes et croix décalés, chaque chiffre
    du rail démenti par le dessin.

    On lit donc la géométrie rendue : trois segments, chacun de −portée à
    +portée sur SON axe et nul sur les deux autres, et le groupe à l'identité —
    position, quaternion, échelle.
    """
    sortie = json.loads(_node_trois(
        "cadrer, majRepere",
        _table_js("lib3d/viewer.js", "COULEUR_AXE") + "\n" + """
      const api = monter(860, 824);
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      cadrer(api);
      const e = majRepere(api);
      const groupe = api.scene.children.find((o) => o.name === "lib3d-repere");
      groupe.updateMatrixWorld(true);
      const p = Array.from(e.axes.geometry.attributes.position.array);
      const c = Array.from(e.axes.geometry.attributes.color.array);
      const teintes = {};
      for (const a of ["x", "y", "z"]) {
        const t = new THREE.Color(COULEUR_AXE[a]);
        teintes[a] = [t.r, t.g, t.b];
      }
      const segments = [];
      for (let i = 0; i < p.length; i += 6) {
        let axe = "?";
        for (const nom of ["x", "y", "z"]) {
          if (teintes[nom].every((v, k) => Math.abs(v - c[i + k]) < 1e-6)) {
            axe = nom;
          }
        }
        segments.push({ axe, a: p.slice(i, i + 3), b: p.slice(i + 3, i + 6) });
      }
      console.log(JSON.stringify({
        pas: e.pas, cases: e.cases, segments,
        pose: groupe.position.toArray(),
        quat: groupe.quaternion.toArray(),
        echelle: groupe.scale.toArray(),
        monde: Array.from(groupe.matrixWorld.elements),
        /* la trame aussi vit à l'origine : seule sa ROTATION peut bouger */
        poseTrame: e.trame.position.toArray() }));
    """))
    portee = sortie["cases"] * sortie["pas"]
    assert portee > 0, sortie
    assert len(sortie["segments"]) == 3, sortie["segments"]
    rangs = {"x": 0, "y": 1, "z": 2}
    vus = set()
    for s in sortie["segments"]:
        assert s["axe"] in rangs, s
        vus.add(s["axe"])
        k = rangs[s["axe"]]
        # DE −PORTÉE À +PORTÉE : l'axe TRAVERSE l'origine, il n'en part pas.
        assert abs(s["a"][k] + portee) < 1e-3 * portee, (s, portee)
        assert abs(s["b"][k] - portee) < 1e-3 * portee, (s, portee)
        # …et il est NUL sur les deux autres : un axe oblique ne gradue rien.
        for autre in range(3):
            if autre == k:
                continue
            assert abs(s["a"][autre]) < 1e-9 and abs(s["b"][autre]) < 1e-9, s
    assert vus == {"x", "y", "z"}, vus
    # LE GROUPE EST À L'IDENTITÉ : rien n'est décalé, tourné ni mis à l'échelle.
    assert sortie["pose"] == [0, 0, 0], sortie["pose"]
    assert sortie["quat"] == [0, 0, 0, 1], sortie["quat"]
    assert sortie["echelle"] == [1, 1, 1], sortie["echelle"]
    assert sortie["poseTrame"] == [0, 0, 0], sortie["poseTrame"]
    identite = [1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
    assert sortie["monde"] == identite, sortie["monde"]


def test_la_TRAME_DESSINEE_porte_le_PAS_ANNONCE():
    """LA RÈGLE QUI MENT, PRISE EN FLAGRANT DÉLIT — c'est la mutation qui a le
    plus coûté à la première écriture de cette section.

    `new THREE.GridHelper(cote, 2 * cases)` mis à `cases` : la case dessinée
    vaut alors DEUX PAS pendant que le rail annonce un pas. Tout était vert —
    le pas ANNONCÉ était mesuré, l'événement portait le bon nombre, et personne
    n'avait jamais regardé l'écartement des lignes. Une graduation dont la case
    ne vaut pas le pas écrit est précisément la règle que cette tâche existe
    pour interdire.

    On mesure donc l'écartement DANS la géométrie livrée, à trois zooms, et on
    le compare au pas de l'évènement. Le second chemin est arithmétique : les
    lignes sont relevées puis différenciées, là où le module les engendre par
    une multiplication.
    """
    sortie = json.loads(_node_trois(
        "cadrer, majRepere",
        "let dernier = null;\n" + """
      function trameDe(api) {
        const e = majRepere(api);
        const pos = e.trame.geometry.attributes.position;
        /* Les lignes PARALLELES a X : leur coordonnee de rangement est z. */
        const lignes = new Set();
        for (let i = 0; i < pos.count; i += 2) {
          const ax = pos.getX(i), bx = pos.getX(i + 1);
          if (Math.abs(ax - bx) > 1e-6) lignes.add(Math.round(pos.getZ(i) * 1e5));
        }
        const rangees = [...lignes].map((v) => v / 1e5).sort((a, b) => a - b);
        const ecarts = [];
        for (let i = 1; i < rangees.length; i++) {
          ecarts.push(rangees[i] - rangees[i - 1]);
        }
        return { annonce: dernier.pas, cases: dernier.cases,
                 lignes: rangees.length,
                 etendue: rangees[rangees.length - 1] - rangees[0],
                 ecartMin: Math.min(...ecarts), ecartMax: Math.max(...ecarts) };
      }
      const api = monter(860, 824);
      api.renderer.domElement.dispatchEvent = (ev) => { dernier = ev.detail; };
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      cadrer(api);
      const rangs = [];
      for (const z of [1, 2, 8]) {
        api.camera.zoom = z;
        api.camera.updateProjectionMatrix();
        rangs.push({ z, ...trameDe(api) });
      }
      console.log(JSON.stringify(rangs));
    """))
    assert len(sortie) == 3, sortie
    for r in sortie:
        pas = r["annonce"]
        assert pas > 0, r
        # L'ÉCARTEMENT DESSINÉ EST LE PAS ANNONCÉ, à la simple précision près.
        assert abs(r["ecartMin"] - pas) < 1e-4 * pas, r
        assert abs(r["ecartMax"] - pas) < 1e-4 * pas, r
        # …et la trame porte bien DEUX FOIS `cases` cases, donc 2·cases + 1
        # lignes, d'un bord à l'autre de 2·cases·pas.
        assert r["lignes"] == 2 * r["cases"] + 1, r
        assert abs(r["etendue"] - 2 * r["cases"] * pas) < 1e-3 * r["etendue"], r
    # les trois zooms ne mesurent pas trois fois le même pas
    assert len({r["annonce"] for r in sortie}) == 3, sortie


def test_la_TRAME_du_repere_ne_se_CONFOND_pas_avec_le_plateau():
    """DEUX GRILLES DE PAS DIFFÉRENTS, ET UN SEUL PAS ANNONCÉ.

    Le plateau de /lib3d/plaque.js et la trame de ce repère ne portent pas
    le même pas : le plateau se dimensionne sur l'empreinte de l'étalement
    (un pas de PLATEAU, stable, gradué sur ses bords depuis la plaque façon
    slicer), la trame porte le pas de VUE 1-2-5 que le rail annonce en
    chiffres et qui change au zoom. Sous une même palette, l'utilisateur
    lirait deux quadrillages pour un seul nombre — la règle qui ment que
    cette tâche interdit. (Depuis la plaque slicer, la page ÉTEINT le repère
    sur la plaque, ce qui règle le cas à l'écran ; les palettes restent
    distinctes pour le jour où un autre écran les superposerait.)

    La première écriture reprenait les deux gris du plateau en JUSTIFIANT la
    reprise (« une seconde palette se lirait comme une seconde échelle ») :
    l'argument était retourné, et c'est le contraire qui est vrai. On apparie
    donc les deux tables plutôt que de le promettre en prose.

    ET LA LIGNE CENTRALE N'EST PAS PLUS CLAIRE : GridHelper propose d'éclaircir
    les deux lignes du milieu, or ce sont les axes, que le module dessine
    par-dessus en rouge/vert/bleu. Deux marques pour un même centre, dont l'une
    pâle, ne feraient que brouiller l'autre.
    """
    vue = _code("lib3d/viewer.js")
    plq = _code("lib3d/plaque.js")
    # les couleurs du plateau, lues LÀ-BAS et non recopiées ici
    grille = re.search(r"new THREE\.GridHelper\([^)]*?"
                       r"(0x[0-9a-f]{6}), (0x[0-9a-f]{6})\)", plq)
    assert grille, "GridHelper du plateau introuvable"
    plateau = {grille.group(1), grille.group(2)}
    assert len(plateau) == 2, plateau
    trame = {}
    for nom in ("COULEUR_TRAME", "COULEUR_TRAME_CENTRE"):
        m = re.search(r"^const " + nom + r" = ([^\n;]+);", vue, re.M)
        assert m, nom
        trame[nom] = m.group(1).strip()
    assert trame["COULEUR_TRAME"] not in plateau, (trame, plateau)
    assert trame["COULEUR_TRAME"].startswith("0x"), trame
    # la ligne centrale EST la trame : les axes marquent déjà le centre.
    assert trame["COULEUR_TRAME_CENTRE"] == "COULEUR_TRAME", trame
    # ── ET LA COULEUR DESSINÉE, pas seulement la constante ───────────────────
    # C'est MA PROPRE RÈGLE non appliquée à mon propre correctif : écrire les
    # deux gris du plateau EN DUR dans l'appel à GridHelper, en laissant les
    # constantes intactes, passait tous les contrôles. L'attribut `color` de la
    # géométrie est lisible — le contrôle des axes le lit déjà.
    rendu = json.loads(_node_trois(
        "cadrer, majRepere",
        "const PLATEAU = " + json.dumps(sorted(plateau)) + ";\n" + """
      const api = monter(860, 824);
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      cadrer(api);
      const e = majRepere(api);
      const c = e.trame.geometry.attributes.color;
      const vues = new Set();
      for (let i = 0; i < c.count; i++) {
        vues.add([c.getX(i), c.getY(i), c.getZ(i)]
          .map((v) => v.toFixed(6)).join(","));
      }
      /* les deux gris du plateau, passes par la MEME conversion que three.js
         applique a un GridHelper — sinon on comparerait sRGB et lineaire. */
      const interdits = PLATEAU.map((h) => {
        const t = new THREE.Color(Number(h));
        return [t.r, t.g, t.b].map((v) => v.toFixed(6)).join(",");
      });
      console.log(JSON.stringify({ dessinees: [...vues], interdits }));
    """))
    assert len(rendu["interdits"]) == 2, rendu
    for teinte in rendu["dessinees"]:
        assert teinte not in rendu["interdits"], (teinte, rendu)
    # UNE SEULE teinte dessinée : la ligne centrale n'est plus distincte.
    assert len(rendu["dessinees"]) == 1, rendu["dessinees"]


def test_le_PLAN_de_la_TRAME_suit_le_REGARD_et_ne_papillote_pas():
    """« UNE GRADUATION VISIBLE » — et elle ne l'était pas dans deux des cinq
    vues nommées. La trame naissait dans le plan du sol ; vue par la tranche,
    une grille est une LIGNE.

    Ce que ce contrôle mesure est la HAUTEUR ÉCRAN de la trame, ses sommets
    projetés par la vraie caméra, en unités de découpage où le cadre en fait 2 :

        vue      trame FIGÉE dans XZ    trame posée par planDeTrame
        libre        2,110·10²                2,110·10²      (plan y)
        iso          1,548·10¹                1,548·10¹      (plan y)
        dessus       1,896·10¹                1,896·10¹      (plan y)
        face         1,161·10⁻¹⁵              1,896·10¹      (plan z)
        profil       1,161·10⁻¹⁵              1,896·10¹      (plan x)

    Et ce n'est pas un cas de coin : `axeEmpile` rend « z » pour les douze
    pièces du modèle réel (0,0630 × 0,0880 × ~0), donc `VUE_DE_PLAQUE` désigne
    « Face » comme la vue qui regarde l'étalement en face — celle-là même où la
    graduation n'existait pas.

    LE PLANCHER GARDE LA PRIORITÉ, ce qui préserve le point de vue historique :
    |avant·y| vaut 0,3600 en libre et 0,5774 en isométrique, tous deux au-dessus
    du seuil, quand « face » et « profil » valent zéro exactement.

    PAS DE PAPILLOTEMENT, et on le BALAIE plutôt que de le croire : une orbite
    complète en élévation, et le plan ne change qu'aux deux passages du seuil.
    """
    sortie = json.loads(_node_trois(
        "projeter, orienter, cadrer, majRepere, marquerAuRepere, planDeTrame,"
        " axeDeVue",
        _table_js("etabli/etabli.js", "PROJECTION_DE_VUE") + "\n" + """
      /* LES DEUX ETENDUES ECRAN, et pas seulement la hauteur : une trame vue
         par la tranche s'effondre sur l'UNE OU L'AUTRE selon l'axe par lequel
         on la regarde. Ne mesurer que la hauteur laissait passer une rotation
         permutee — le defaut d'origine tourne d'un quart de tour. */
      function etendueEcran(api, objet) {
        objet.updateMatrixWorld(true);
        api.camera.updateMatrixWorld(true);
        api.camera.updateProjectionMatrix();
        const pos = objet.geometry.attributes.position;
        let xa = Infinity, xb = -Infinity, ya = Infinity, yb = -Infinity;
        for (let i = 0; i < pos.count; i++) {
          const v = new THREE.Vector3().fromBufferAttribute(pos, i)
            .applyMatrix4(objet.matrixWorld).project(api.camera);
          xa = Math.min(xa, v.x); xb = Math.max(xb, v.x);
          ya = Math.min(ya, v.y); yb = Math.max(yb, v.y);
        }
        return { largeur: xb - xa, hauteur: yb - ya };
      }
      const hauteurEcran = (api, o) => etendueEcran(api, o).hauteur;
      /* LA NORMALE MONDE de la trame : GridHelper nait normale +Y, on suit sa
         rotation. C'est elle qui doit nommer le meme axe que `e.plan` — sans
         quoi la grille et les croix parlent de deux plans differents. */
      function normaleTrame(trame) {
        return new THREE.Vector3(0, 1, 0)
          .applyQuaternion(trame.quaternion).normalize().toArray();
      }
      const vues = ["libre", "iso", "face", "dessus", "profil"];
      const rangs = vues.map((vue) => {
        const api = monter(860, 824);
          poserModele(api, 3, 1.1, 0.4, 0, 0, 0);
        projeter(api, PROJECTION_DE_VUE[vue]);
        orienter(api, vue);
        api.camera.updateMatrixWorld(true);
        const avant = axeDeVue(api.camera.matrixWorld.elements);
        const e = majRepere(api);
        const posee = etendueEcran(api, e.trame);
        const normale = normaleTrame(e.trame);
        const rot = e.trame.rotation.toArray().slice(0, 3);
        e.trame.rotation.set(0, 0, 0);         /* l'etat d'AVANT : figee en XZ */
        const figee = etendueEcran(api, e.trame);
        return { vue, plan: e.plan, cosY: Math.abs(avant.y), posee, figee, rot,
                 normale };
      });
      /* LE BALAYAGE EN ELEVATION : deux traversees du seuil par tour. */
      let plan = "y";
      const suite = [];
      for (let i = 0; i <= 720; i++) {
        const a = (i / 720) * Math.PI * 2;
        plan = planDeTrame({ x: Math.cos(a), y: Math.sin(a), z: 0 }, plan);
        suite.push(plan);
      }
      const bascules = suite.filter((p, i) => i && p !== suite[i - 1]).length;

      /* LE BALAYAGE EN AZIMUT, A ELEVATION NULLE : c'est LUI qui exerce le
         partage x/z. Le precedent avait z === 0 en permanence, si bien que
         `meilleur` valait toujours « x » et que la branche de marge ne
         s'executait JAMAIS — donnees trop symetriques, pour la troisieme fois
         sur ce chantier. */
      const balayer = (sens) => {
        let p = sens > 0 ? "x" : "z";
        const angles = [];
        const N = 200000;
        for (let i = 0; i <= N; i++) {
          const a = (sens > 0 ? i : N - i) / N * (Math.PI / 2);
          const avant = { x: Math.cos(a), y: 0, z: Math.sin(a) };
          const q = planDeTrame(avant, p);
          if (q !== p) angles.push(a);
          p = q;
        }
        return angles;
      };
      const montant = balayer(1), descendant = balayer(-1);
      /* UN TOUR COMPLET en azimut, pour compter les bascules. */
      let pz = "x";
      const tour = [];
      for (let i = 0; i <= 3600; i++) {
        const a = (i / 3600) * Math.PI * 2;
        pz = planDeTrame({ x: Math.cos(a), y: 0, z: Math.sin(a) }, pz);
        tour.push(pz);
      }
      const basculesAzimut = tour.filter((q, i) => i && q !== tour[i - 1]).length;

      /* ET LE SEUIL DU PLANCHER, oscille des DEUX cotes : une main qui tremble
         a cette elevation-la reconstruisait la trame a chaque image. */
      const oscillation = (amplitude) => {
        let q = "y", bascules2 = 0;
        const base = Math.asin(0.25);
        for (let i = 0; i < 200; i++) {
          const a = base + (i % 2 ? amplitude : -amplitude);
          const r = planDeTrame({ x: Math.cos(a), y: Math.sin(a), z: 0 }, q);
          if (r !== q) bascules2++;
          q = r;
        }
        return bascules2;
      };
      /* LE PLAN CHANGE SUR UNE VUE DEJA GRADUEE : pas et cases ne bougent
         pas d'une vue nommee a l'autre, si bien qu'un memo qui ignore le plan
         renvoie la trame d'avant et la laisse a plat. On orbite donc SUR PLACE
         plutot que de repartir d'un canevas neuf. */
      const suivi = monter(860, 824);
      poserModele(suivi, 3, 1.1, 0.4, 0, 0, 0);
      projeter(suivi, PROJECTION_DE_VUE["libre"]); orienter(suivi, "libre");
      const avantBascule = majRepere(suivi);
      const memo = { plan: avantBascule.plan, pas: avantBascule.pas,
                     cases: avantBascule.cases };
      projeter(suivi, PROJECTION_DE_VUE["face"]); orienter(suivi, "face");
      const apresBascule = majRepere(suivi);
      const bascule = { avant: memo, apres: { plan: apresBascule.plan,
        pas: apresBascule.pas, cases: apresBascule.cases },
        hauteur: hauteurEcran(suivi, apresBascule.trame) };

      /* LA MARQUE SUIT LE PLAN, elle n'est pas figee sur le sol : en « face »
         (plan z) la descente doit rejoindre z = 0, pas y = 0 — figee, elle
         plongerait dans le vide et ne se rapporterait a aucune case. */
      const enFace = monter(860, 824);
      poserModele(enFace, 3, 1.1, 0.4, 0, 0, 0);
      projeter(enFace, PROJECTION_DE_VUE["face"]); orienter(enFace, "face");
      const eF = majRepere(enFace);
      marquerAuRepere(enFace, [{ x: 1.7, y: -0.85, z: 2.35 }]);
      const gF = enFace.scene.children.find((o) => o.name === "lib3d-repere");
      const mF = gF.children[gF.children.length - 1];
      const pF = Array.from(mF.geometry.attributes.position.array);
      const segF = [];
      for (let i = 0; i < pF.length; i += 6) {
        segF.push([pF.slice(i, i + 3), pF.slice(i + 3, i + 6)]);
      }
      /* LA PORTEE COMPTE LES TROIS AXES : une cible haute en Y est aussi loin
         de l'origine qu'une cible lointaine en X des que le plan est XY. */
      const haut = monter(860, 824);
      poserModele(haut, 3, 1.1, 0.4, 0, 40, 0);
      projeter(haut, PROJECTION_DE_VUE["face"]); orienter(haut, "face");
      const eH = majRepere(haut);
      /* L'AXE DE VUE, par un second chemin : getWorldDirection de three.js. */
      const temoin = monter(860, 824);
      poserModele(temoin, 3, 1.1, 0.4, 0, 0, 0);
      projeter(temoin, "orthographique"); orienter(temoin, "iso");
      temoin.camera.updateMatrixWorld(true);
      const d = temoin.camera.getWorldDirection(new THREE.Vector3());
      console.log(JSON.stringify({ rangs, bascules, bascule,
        montant, descendant, basculesAzimut,
        tremblement: oscillation(0.0001), franc: oscillation(0.2),
        planFace: eF.plan, segF, pasFace: eF.pas,
        porteeHaut: eH.cases * eH.pas, cibleHaut: haut.controls.target.y,
        axeLu: axeDeVue(temoin.camera.matrixWorld.elements),
        axeTrois: d.toArray() }));
    """))
    attendu = {"libre": "y", "iso": "y", "dessus": "y",
               "face": "z", "profil": "x"}
    rangs = {"x": 0, "y": 1, "z": 2}
    for r in sortie["rangs"]:
        quoi = r["vue"]
        assert r["plan"] == attendu[quoi], (quoi, r)
        # LA NORMALE DESSINÉE NOMME LE MÊME AXE QUE `e.plan`, et c'est ce qui
        # manquait : une rotation PERMUTÉE (z ↔ x) laissait la hauteur écran
        # intacte — 18,963 — pendant que la LARGEUR tombait à 4,03·10⁻¹⁵. La
        # trame redevenait une ligne, tournée d'un quart de tour, et
        # `marquerAuRepere` traçait ses croix dans un plan que la grille
        # n'occupait plus.
        k = rangs[r["plan"]]
        assert abs(abs(r["normale"][k]) - 1) < 1e-9, (quoi, r["normale"])
        for autre in range(3):
            if autre != k:
                assert abs(r["normale"][autre]) < 1e-9, (quoi, r["normale"])
        # LES DEUX ÉTENDUES : c'est la grandeur qui peut tomber à zéro, et il y
        # en a deux. N'en mesurer qu'une, c'est mesurer la moitié du défaut.
        assert r["posee"]["hauteur"] > 1.0, (quoi, r)
        assert r["posee"]["largeur"] > 1.0, (quoi, r)
        if attendu[quoi] == "y":
            # le plancher est gardé : rien n'a bougé pour ces trois-là
            assert abs(r["posee"]["hauteur"] - r["figee"]["hauteur"]) < 1e-9, r
            assert r["cosY"] >= 0.25, (quoi, r)
            assert r["rot"] == [0, 0, 0], (quoi, r)
        else:
            # …et là où elle était PLATE, elle ne l'est plus. Le rapport est de
            # seize ordres de grandeur : ce n'est pas une amélioration, c'est
            # une capacité qui n'existait pas.
            assert r["figee"]["hauteur"] < 1e-9, (quoi, r)
            assert (r["posee"]["hauteur"]
                    / max(r["figee"]["hauteur"], 1e-300) > 1e12), (quoi, r)
            assert r["cosY"] < 1e-9, (quoi, r)
            assert r["rot"] != [0, 0, 0], (quoi, r)
    # DEUX BASCULES PAR TOUR, et pas une de plus : le plancher est quitté puis
    # repris une fois de chaque côté. Un plan qui papillote reconstruirait la
    # géométrie à chaque image.
    assert sortie["bascules"] == 4, sortie["bascules"]
    # ── LA BANDE MORTE, MESURÉE DANS LES DEUX SENS ──────────────────────────
    # Le balayage précédent avait z ≡ 0, donc `meilleur` valait toujours « x »
    # et la branche de marge ne s'exécutait jamais : la constante faisait
    # quelque chose et aucun banc ne le savait. On balaie donc l'AZIMUT, où x
    # et z se disputent, et on relève l'angle de bascule dans chaque sens :
    # s'ils diffèrent, il y a hystérésis ; s'ils coïncident, il n'y en a pas.
    assert len(sortie["montant"]) == 1, sortie["montant"]
    assert len(sortie["descendant"]) == 1, sortie["descendant"]
    bande = abs(sortie["montant"][0] - sortie["descendant"][0])
    assert bande > 0.02, (sortie["montant"], sortie["descendant"], bande)
    # …et le partage se fait bien de part et d'autre de 45°, où x et z sont à
    # égalité — c'est le lieu où deux plans se relaieraient sans la marge.
    for angle in (sortie["montant"][0], sortie["descendant"][0]):
        assert abs(angle - math.pi / 4) < 0.08, angle
    # QUATRE BASCULES PAR TOUR D'AZIMUT : une par quadrant.
    assert sortie["basculesAzimut"] == 4, sortie["basculesAzimut"]
    # ── LE SEUIL DU PLANCHER A LA SIENNE AUSSI ──────────────────────────────
    # C'est le correctif de ce commit : `MARGE_TRANCHE` n'était branchée que
    # sur le partage x/z, si bien qu'une caméra qui tremble autour de 14,48°
    # d'élévation basculait à CHAQUE image. MESURÉ, 200 appels oscillant de
    # ±0,0057° autour du seuil : sans la bande 200 bascules, avec la bande 0.
    # Chaque bascule reconstruit jusqu'à 513 lignes, émet `lib3d:graduation` et
    # déclenche donc une relecture complète du rail, dans la boucle de rendu.
    assert sortie["tremblement"] == 0, sortie["tremblement"]
    # …et un mouvement FRANC bascule quand même : la bande amortit, elle ne
    # fige pas.
    assert sortie["franc"] > 50, sortie["franc"]
    # LE PLAN BASCULE SUR UNE VUE DÉJÀ GRADUÉE. Le pas et le nombre de cases
    # sont IDENTIQUES avant et après — c'est ce qui rend le piège muet : un mémo
    # qui ne compare que ces deux-là rend la trame d'avant, laissée à plat, et
    # rien ne lève. On vérifie donc que le plan a changé ET que la trame est
    # redevenue visible.
    b = sortie["bascule"]
    assert b["avant"]["plan"] == "y" and b["apres"]["plan"] == "z", b
    assert b["avant"]["pas"] == b["apres"]["pas"], b
    assert b["avant"]["cases"] == b["apres"]["cases"], b
    assert b["hauteur"] > 1.0, b
    # LA MARQUE SUIT LE PLAN : en « face » la descente rejoint z = 0, et le
    # pied de la descente n'est PAS sur y = 0. Figée sur le sol, elle aurait
    # plongé dans le vide sans se rapporter à aucune case.
    assert sortie["planFace"] == "z", sortie["planFace"]
    pieds = [b for a, b in sortie["segF"]
             if abs(a[0] - 1.7) < 1e-4 and abs(a[1] + 0.85) < 1e-4
             and abs(a[2] - 2.35) < 1e-4]
    descente = [b for b in pieds if abs(b[2]) < 1e-4]
    assert descente, sortie["segF"]
    assert abs(descente[0][0] - 1.7) < 1e-4, descente     # x conservé
    assert abs(descente[0][1] + 0.85) < 1e-4, descente    # y conservé, PAS mis à 0
    # LA PORTÉE COMPTE LES TROIS AXES : une cible à 40 en Y est rejointe.
    assert abs(sortie["cibleHaut"] - 40) < 1e-6, sortie["cibleHaut"]
    assert sortie["porteeHaut"] >= 40, sortie["porteeHaut"]
    # L'AXE DE VUE EST CELUI DE three.js, lu par un second chemin.
    for a, b in zip([sortie["axeLu"]["x"], sortie["axeLu"]["y"],
                     sortie["axeLu"]["z"]], sortie["axeTrois"]):
        assert abs(a - b) < 1e-12, (sortie["axeLu"], sortie["axeTrois"])


def test_le_bloc_du_repere_ne_PEUT_PAS_ecrire_un_millimetre_de_plus():
    """LA NÉGATIVE QUI MANQUAIT, et son absence était démontrable : ajouter
    dans la branche « aucune taille cible » un ` · soit ${(REP.pas *
    1000).toFixed(1)} mm` passait tous les contrôles. Des millimètres inventés,
    sans cible, sans toucher `REP.echelle` — donc sous le compte rigide qui
    était le seul verrou. La couche FORMATAGE était tenue ; la couche ÉCRITURE
    ne l'était pas.

    ET LA PORTÉE DE LA LISTE NOIRE EST ELLE-MÊME UNE ASSERTION — c'est le
    second défaut, et il est plus intéressant que le premier. La négative ne
    couvrait que le bloc du repère, borné à l'écouteur `etabli:charge` ; or
    l'écouteur `lib3d:graduation`, qui écrit DANS LA MÊME ZONE, vit cent lignes
    plus bas, donc DEHORS. Un `$("#repereEchelle").innerHTML += ` · soit
    ${(REP.pas * 1000).toFixed(1)} mm`` y passait sans rien faire rougir.

    /lib3d/plaque.js couvre TOUT SON MODULE ; on fait pareil. `etabli.js` n'a
    aucune raison légitime d'écrire l'abréviation ailleurs que dans
    `uniteCourante()` : partout ailleurs il dit « millimètres » en toutes
    lettres. La frontière disparaît donc, et avec elle la question de savoir où
    elle passe.

    Assertions NÉGATIVES, donc posées sur `_code()` : la prose de ce fichier
    explique longuement d'où les millimètres viennent, et un `not in` nu serait
    satisfait par elle. Le témoin le prouve.
    """
    fichier = _code("etabli/etabli.js")
    lu = _fonction_etabli("lireRepere")
    # LA PAGE ENTIÈRE, plus seulement le bloc : un suffixe en dur porte
    # forcément un espace devant son unité.
    assert " mm" not in fichier
    bloc = _bloc_repere()
    assert " mm" not in bloc
    # …et le TOKEN lui-même ne vit qu'en deux endroits nommés : l'unité rendue
    # par uniteCourante, et l'indice du champ de saisie. Un troisième est un
    # site qui pourrait écrire un millimètre sans passer par la garde.
    sites = re.findall(r"(?<![A-Za-z])mm(?![A-Za-z])", bloc)
    assert len(sites) == 2, (len(sites), sites)
    assert bloc.count('placeholder="mm"') == 1
    unite = _fonction_etabli("uniteCourante")
    assert unite.count('"mm"') == 1
    # …ET LE TOKEN NE VIT NULLE PART AILLEURS DANS LE FICHIER : deux sites, les
    # deux du bloc. Un troisième, où qu'il soit, est un site qui pourrait écrire
    # un millimètre sans passer par la garde — l'écouteur `lib3d:graduation`,
    # cent lignes plus bas, en est l'exemple mesuré.
    assert len(re.findall(r"(?<![A-Za-z])mm(?![A-Za-z])", fichier)) == 2
    # ── ET UNE GARDE POSITIVE, parce qu'une liste noire ne ferme qu'une
    # ORTHOGRAPHE ────────────────────────────────────────────────────────────
    # « millimetres », « 0,001 m », une unité inventée demain : aucune n'est
    # dans la liste noire. Et compter le littéral
    # `$("#repereEchelle").innerHTML` ne fermait qu'une ÉCRITURE : un
    # `textContent`, un `insertAdjacentHTML`, un `append`, un `replaceChildren`
    # sur la même zone n'y entrent pas. MESURÉ — un
    # `$("#repereEchelle").textContent = (REP.pas * 1000).toFixed(1) +
    # " millimetres";` inventait des millimètres à partir du SEUL PAS DE LA
    # GRILLE, sans cible posée, sans toucher `REP.echelle`, et passait les
    # dix-huit contrôles du repère. Deux orthographes dont l'intersection reste
    # ouverte ne font pas une garde.
    #
    # CE QUI FERME LA FAMILLE : le multi-ensemble des PAIRES zone × verbe DOM.
    # Tout écrivain neuf apparaît comme une septième paire, quel que soit son
    # verbe et quel que soit le mot d'unité qu'il épelle. Les six sont
    # énumérées parce que chacune se justifie ; une septième DOIT se dire.
    paires = collections.Counter(re.findall(
        r'[$]\("#(repere[A-Za-z]*|rCible)"\)[.](\w+)', fichier))
    assert paires == collections.Counter({
        ("repere", "innerHTML"): 1,         # rendreRepere écrit le bloc
        ("rCible", "addEventListener"): 1,  # …et branche son champ
        ("rCible", "value"): 2,             # la lecture du champ, et rendreCible
        ("repereEchelle", "innerHTML"): 1,  # lireRepere, et elle seule
        ("repereLecture", "innerHTML"): 1,  # idem
    }), sorted(paires.items())
    # …ET LES DEUX ÉCRITURES DU RAIL VIVENT DANS lireRepere(), qui commence par
    # recalculer `REP.echelle` : rien ne s'y affiche sans être passé par la
    # garde des millimètres.
    for zone in ('$("#repereEchelle").innerHTML',
                 '$("#repereLecture").innerHTML'):
        assert zone in lu, zone
    assert lu.index("REP.echelle = echelleMm(") < lu.index(
        '$("#repereEchelle").innerHTML')
    # LE TÉMOIN : la prose, elle, en parle — et le bloc ENTIER la contient.
    assert " mm" in _bloc_repere(_lire("etabli/etabli.js"))
    # …et le reste de la page n'en écrit pas davantage : `direRefus` dit
    # « millimètres » en toutes lettres, jamais l'abréviation.
    assert "millimètres" in _fonction_etabli("poserCible")


def test_montrerRepere_ETEINT_VRAIMENT_le_repere():
    """L'APPEL ÉTAIT GARDÉ, L'EFFET NE L'ÉTAIT PAS. Vider le corps de
    `montrerRepere()` en gardant les deux littéraux que le banc épinglait
    laissait tout au vert — et la vignette de la Bibliothèque serait repartie
    avec un quadrillage en travers du maillage.

    On l'exécute donc : on éteint, on lit `visible`, on rétablit avec ce que la
    fonction a rendu, et on vérifie que la vue est revenue à son état d'avant.
    """
    sortie = json.loads(_node_trois(
        "cadrer, majRepere, montrerRepere",
        """
      const api = monter(860, 824);
      poserModele(api, 3, 1.1, 0.4, 7, -2, 0.5);
      cadrer(api);
      majRepere(api);
      const groupe = api.scene.children.find((o) => o.name === "lib3d-repere");
      const r = { depart: groupe.visible };
      r.rendu = montrerRepere(api, false);
      r.eteint = groupe.visible;
      montrerRepere(api, r.rendu);
      r.retabli = groupe.visible;
      /* …et sur une vue SANS repere construit, elle ne ment pas : `false`. */
      const vierge = monter(430, 824);
      r.vierge = montrerRepere(vierge, false);
      console.log(JSON.stringify(r));
    """))
    assert sortie["depart"] is True, sortie
    assert sortie["rendu"] is True, sortie          # l'état d'AVANT, pas un vœu
    assert sortie["eteint"] is False, sortie        # …et l'effet a bien eu lieu
    assert sortie["retabli"] is True, sortie
    assert sortie["vierge"] is False, sortie


# ── Q. la plaque façon slicer : voir, graduer, déplacer, et le PLAN DE PLAQUE ─
# Retour de l'utilisateur, mot pour mot : « quand je demande "sur la plaque" je
# n'ai pas besoin de voir les repères orthonormés. la plaque devrait être
# graduée sur les côtés pour un repérage des positionnements sur la grille. je
# dois aussi pouvoir déplacer les éléments ou la pièce sur la grille comme le
# propose la plupart des slicers. »
#
# CE QUE CETTE SECTION LIT : de la géométrie DESSINÉE (les traits des règles,
# les cases de la grille, les matrices monde des pièces), des textes ÉCRITS
# (les libellés sur la texture des bandes, par un canevas 2D factice qui les
# enregistre — voir _MONTAGE), du JSON ÉCRIT sur le disque par la route, et le
# balisage du rail. Jamais le code qui prétend produire tout cela — la leçon
# des dix mutations vertes de la section P. Et les données sont ASYMÉTRIQUES :
# trois boîtes de cotes distinctes sous une enveloppe tournée et mise à
# l'échelle, un canevas non carré, des déplacements non ronds.
#
# LA DÉCISION DE STRUCTURE DU LOT : ce qu'on compose sur la plaque est un PLAN
# DE PLAQUE explicite et persisté ({ index, dx, dy, rot } par pièce, en unités
# du modèle), DISTINCT du maillage — `model.vN.glb` ne bouge pas quand on range
# des pièces — écrit par Python dans `plaque.v<N>.json`, relu à l'entrée, et
# que l'extraction consommera. La séparation maillage / disposition du 3MF.


def _scene_enveloppe() -> str:
    """Deux pièces de cotes DISTINCTES sous une enveloppe tournée et mise à
    l'échelle (0,3 ; −0,7 ; 0,45 rad — 2 ; 0,5 ; 1,75), translatée de
    (−4 ; 9 ; 3) : le cas d'une réparation en Z, où rien n'est l'identité et
    où une erreur d'axe ou de signe ne peut pas tomber sur un zéro. Le même
    montage que la lecture du rail (section P), pour que les deux parlent des
    mêmes nombres — sauf la pièce 2, devenue un L dans le plan du plateau et
    posée À PLAT SOUS LA RACINE : la seule pièce dont la boîte tournée change
    de centre, et sous l'enveloppe tournée l'inflation des boîtes noyait cette
    asymétrie (écart naïf 0,4 % contre 23,6 % à l'identité, mesuré).
    """
    return """
      const racine = new THREE.Group();
      const enveloppe = new THREE.Group();
      enveloppe.userData.indexGltf = 13;
      enveloppe.rotation.set(0.3, -0.7, 0.45);
      enveloppe.scale.set(2, 0.5, 1.75);
      enveloppe.position.set(-4, 9, 3);
      racine.add(enveloppe);
      const cotes = [[0.9, 0.4, 0.2, 1.3, 0, -0.7],
                     [0.5, 1.1, 0.3, -0.8, 0.6, 0.4],
                     [0.7, 0.7, 0.15, 0.2, -1.2, 1.1]];
      const pieces = cotes.map(([l, h, p, x, y, z], i) => {
        const g = new THREE.Group();
        g.name = "piece_" + i;
        g.userData.indexGltf = i;
        g.position.set(x, y, z);
        /* LA PIECE 2 EST UN L DANS LE PLAN DU PLATEAU (xz, l'axe est y) : un
           bras le long de x, un bras le long de z, sans symetrie centrale —
           la boite d'un L tourne n'a plus le meme centre. Une scene faite de
           boites seules avait laisse passer une lecture fausse de 20 %.
           ET IL EST A PLAT SOUS LA RACINE, pas sous l'enveloppe : mesure,
           l'inflation des boites sous l'enveloppe tournee noyait l'asymetrie
           (ecart naif 0,4 % sous l'enveloppe, 23,6 % a l'identite). */
        g.add(new THREE.Mesh(new THREE.BoxGeometry(...(i === 2
          ? [0.7, 0.15, 0.15] : [l, h, p])), new THREE.MeshBasicMaterial()));
        if (i === 2) {
          const aile = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.15, 0.7),
                                      new THREE.MeshBasicMaterial());
          aile.name = "aile_2";
          aile.position.set(0.275, 0, 0.275);
          g.add(aile);
          racine.add(g);
        } else {
          enveloppe.add(g);
        }
        return g;
      });
      api.scene.add(racine); api.racine = racine;
      racine.updateMatrixWorld(true);
      cadrer(api);
      api.camera.updateMatrixWorld(true);
      const pose = (o) => [o.position.toArray(), o.quaternion.toArray(),
                           o.scale.toArray()];
      const nomme = (nom) => api.scene.children.find((o) => o.name === nom);
    """


def _fonction_etabli_async(nom: str) -> str:
    """Une fonction `async` d'etabli.js, VERBATIM — `_fonction_etabli` ne
    connaît que l'ancre `\nfunction `."""
    js = _lire("etabli/etabli.js")
    i = js.find("\nasync function " + nom + "(")
    assert i >= 0, f"fonction async {nom} introuvable dans etabli.js"
    return js[i:js.index("\n}\n", i) + 2]


def _rodrigues(n, theta_deg, v):
    """v tourné de theta autour de l'axe unitaire n — le second chemin de la
    rotation, en Python, sans three.js."""
    t = math.radians(theta_deg)
    c, s_ = math.cos(t), math.sin(t)
    nv = sum(a * b for a, b in zip(n, v))
    nxv = [n[1] * v[2] - n[2] * v[1], n[2] * v[0] - n[0] * v[2],
           n[0] * v[1] - n[1] * v[0]]
    return [v[i] * c + nxv[i] * s_ + n[i] * nv * (1 - c) for i in range(3)]


def _nombre_fr(texte: str) -> float:
    return float(str(texte).replace("−", "-").replace("\u202f", "")
                 .replace("\u00a0", "").replace(" ", "").replace(",", "."))


def test_sur_la_plaque_le_REPERE_ORTHONORME_s_eteint_et_revient_a_son_etat_d_AVANT():
    """« je n'ai pas besoin de voir les repères orthonormés » — et ce n'est
    pas qu'un confort : le repère porte un pas de VUE qui change au zoom, le
    plateau porte un pas de PLATEAU stable ; deux quadrillages de pas
    différents sous une même scène font une règle qui ment. Sur la plaque,
    ni axes, ni croix, ni trame du repère ; à la sortie, le repère revient à
    l'état où il était — pas à « visible ».

    EXÉCUTÉ, pas seulement épinglé : la VRAIE oublierPlaque() tourne sur les
    vrais modules (ranger, montrerRepere, effacerRegles, marquerPiece), dans
    les deux états de départ. La leçon de montrerRepere_ETEINT_VRAIMENT :
    l'appel était gardé, l'effet ne l'était pas.

    ET LA LECTURE DU RAIL RESTE : elle est corrigée du décalage d'étalement
    (test_la_POSITION_lue…), le repère éteint n'y change rien.
    """
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    bloc = _plaque_bloc()
    # à l'entrée : APRÈS l'étalement réussi (un refus n'éteint rien), AVANT le
    # cadrage ; l'état d'avant est RENDU par la fonction, jamais supposé
    assert "PLQ.repereAvant = montrerRepere(S.vueA, false);" in bloc
    bp = code.split("function basculerPlaque()", 1)[1].split("\n}\n", 1)[0]
    assert bp.index("etaler(S.vueA, plan)") \
        < bp.index("PLQ.repereAvant = montrerRepere(S.vueA, false);") \
        < bp.index("cadrer(S.vueA);")
    # à la sortie : rétabli TEL QUEL, après le rangement, et les règles du
    # plateau s'effacent avec la plaque
    ob = code.split("function oublierPlaque()", 1)[1].split("\n}\n", 1)[0]
    assert ob.index("ranger(S.vueA);") \
        < ob.index("montrerRepere(S.vueA, PLQ.repereAvant);")
    assert "effacerRegles(S.vueA);" in ob
    assert "marquerPiece(S.vueA, null);" in ob
    # QUATRE sites, et le compte est rigide : les deux de la vignette (masquer,
    # rétablir) et les deux de la plaque (éteindre, rétablir). Un cinquième
    # serait un écran qui décide de la règle sans le dire.
    assert code.count("montrerRepere(") == 4, code.count("montrerRepere(")
    # ── EXÉCUTÉ : la vraie oublierPlaque sur les vrais modules ───────────────
    sortie = json.loads(_node_trois(
        "cadrer, majRepere, montrerRepere, dessinerRegles, effacerRegles",
        _importer_plaque("etaler, ranger, estEtalee, marquerPiece, plateauDe")
        + """
      let envois = 0;
      const envoyerPlan = () => { envois++; };
      const majBoutonPlaque = () => {};
      const majBoutonsVue = () => {};
      const PLQ = { active: false, pieces: [], masquees: new Set(),
                    teintes: new Map(), partages: 0, vides: 0, axe: null,
                    pas: null, courante: null, repereAvant: null,
                    planApplique: false, planFichier: null, enCours: false,
                    aEnvoyer: null, sauvegarde: null };
      const S = { vueA: null };
    """ + _fonction_etabli("oublierPlaque") + """
      function tour(repereAllume) {
        const api = monter(860, 824);
        S.vueA = api;
        """ + _scene_enveloppe() + """
        majRepere(api);
        const repere = nomme("lib3d-repere");
        montrerRepere(api, repereAllume);
        /* LES DEUX LIGNES DE basculerPlaque, sur les vrais modules. */
        const et = etaler(api);
        PLQ.active = true; PLQ.pas = et.plateau.pas; PLQ.courante = 1;
        PLQ.repereAvant = montrerRepere(api, false);
        marquerPiece(api, 1);
        dessinerRegles(api, plateauDe(api), (v) => String(v), "u");
        const pendant = { repere: repere.visible, regles: !!nomme("lib3d-regles"),
                          poignee: !!nomme("plaque-poignee"),
                          plateau: !!nomme("plaque-plateau"), etalee: estEtalee(api) };
        oublierPlaque();
        const apres = { repere: repere.visible, regles: !!nomme("lib3d-regles"),
                        poignee: !!nomme("plaque-poignee"),
                        plateau: !!nomme("plaque-plateau"), etalee: estEtalee(api),
                        active: PLQ.active, pas: PLQ.pas, courante: PLQ.courante,
                        repereAvant: PLQ.repereAvant, envois };
        envois = 0;
        return { pendant, apres };
      }
      console.log(JSON.stringify({ allume: tour(true), eteint: tour(false) }));
    """))
    for etat in ("allume", "eteint"):
        pendant, apres = sortie[etat]["pendant"], sortie[etat]["apres"]
        # PENDANT : le repère est éteint, les règles, la poignée et le plateau
        # sont là
        assert pendant["repere"] is False, (etat, pendant)
        assert pendant["regles"] and pendant["poignee"] and pendant["plateau"], \
            (etat, pendant)
        assert pendant["etalee"] is True, (etat, pendant)
        # APRÈS : tout est rangé, le plan pendant est PARTI (une fois), l'état
        # est remis à zéro…
        assert apres["regles"] is False and apres["poignee"] is False \
            and apres["plateau"] is False, (etat, apres)
        assert apres["etalee"] is False and apres["active"] is False, (etat, apres)
        assert apres["pas"] is None and apres["courante"] is None, (etat, apres)
        assert apres["repereAvant"] is None, (etat, apres)
        assert apres["envois"] == 1, (etat, apres)
    # …ET LE REPÈRE REVIENT À SON ÉTAT D'AVANT, PAS À « VISIBLE » : allumé
    # avant, allumé après ; éteint avant, éteint après.
    assert sortie["allume"]["apres"]["repere"] is True, sortie["allume"]
    assert sortie["eteint"]["apres"]["repere"] is False, sortie["eteint"]


def test_le_PLATEAU_est_un_nombre_entier_de_PAS_et_son_pas_est_un_pas_de_PLATEAU():
    """« la plaque devrait être graduée sur les côtés pour un repérage des
    positionnements sur la grille » — encore faut-il que la GRILLE et la
    GRADUATION soient la même chose. Le côté du plateau est donc arrondi au
    multiple supérieur du pas (geometriePlateau), si bien que les cases de la
    grille dessinée VALENT le pas des règles, trait pour trait — on compare
    les deux ensembles de coordonnées, lus dans les géométries.

    ET C'EST UN PAS DE PLATEAU, PAS UN PAS DE VUE : tiré de l'empreinte de
    l'étalement par la règle 1-2-5 du canevas, il ne bouge ni au zoom (le pas
    du repère, lui, change de 0,5 à 0,05 sur la même scène) ni quand on
    déplace une pièce. Deux visites de la même version voient le même
    plateau.

    Le second chemin de la pure geometriePlateau est en Python : côté brut,
    décade, mantisse, arrondi — recomposés sans le module.
    """
    # ── LA PURE, sur des entrées non rondes ─────────────────────────────────
    pur = json.loads(_node(
        _constantes_viewer("DIVISIONS_VISEES")
        + _fonction_viewer("pasGradue")
        + _harnais_vue() + _fonction_viewer("sensDesRegles")
        + _constantes_plaque("AXES", "DEBORD_PLATEAU", "RECUL_PLATEAU")
        + _fonction_plaque("geometriePlateau") + """
      console.log(JSON.stringify({
        z: geometriePlateau(3.1, 1.7, 0.2, "z"),
        x: geometriePlateau(0.031, 0.0574, 0.007, "x"),
        nul: geometriePlateau(0, 0, 0, "y"),
      }));
    """))
    debord = float(re.search(r"^const DEBORD_PLATEAU = ([0-9.]+);",
                             _lire("lib3d/plaque.js"), re.M).group(1))
    recul = float(re.search(r"^const RECUL_PLATEAU = ([0-9.]+);",
                            _lire("lib3d/plaque.js"), re.M).group(1))
    for nom, (l, p_, m) in (("z", (3.1, 1.7, 0.2)), ("x", (0.031, 0.0574, 0.007))):
        g = pur[nom]
        brut = max(l, p_, m) * debord + m
        decade = 10 ** math.floor(math.log10(brut / 10))
        n = brut / 10 / decade
        pas = (5 if n >= 5 else 2 if n >= 2 else 1) * decade
        cases = math.ceil(brut / pas - 1e-9)
        assert abs(g["pas"] - pas) < 1e-12, (nom, g, pas)
        assert g["cases"] == cases, (nom, g, cases)
        assert abs(g["cote"] - cases * pas) < 1e-12, (nom, g)
        assert g["cote"] >= brut - 1e-12, (nom, g, brut)          # contient l'empreinte
        assert g["cote"] - brut < pas + 1e-12, (nom, g, brut)      # d'au plus un pas
        assert 10 <= cases <= 25, (nom, g)
        assert g["axe"] == nom
        u, v = [a for a in "xyz" if a != nom]
        assert (g["u"], g["v"]) == (u, v), g
        assert abs(g["niveau"] + g["cote"] * recul) < 1e-15, g
        # LE COIN EST L'ORIGINE DES RÈGLES : ±côté/2 selon le sens dans lequel
        # chaque axe croît sur la vue de face — pour l'axe x, v (= z) décroît
        # vers la droite d'écran, l'origine est donc au +z. La table est celle
        # que le contrôle des règles retrouve par la CAMÉRA (second chemin).
        sens = {"z": (1, 1), "y": (1, -1), "x": (1, -1)}[nom]
        assert (g["sens"]["u"], g["sens"]["v"]) == sens, (nom, g["sens"])
        assert g["coin"][u] == -sens[0] * g["cote"] / 2, (nom, g)
        assert g["coin"][v] == -sens[1] * g["cote"] / 2, (nom, g)
        assert g["coin"][nom] == g["niveau"], g
    assert pur["nul"]["pas"] is None and pur["nul"]["cases"] == 1, pur["nul"]
    # ── LE PLATEAU DESSINÉ, sur le vrai etaler ──────────────────────────────
    sortie = json.loads(_node_trois(
        "cadrer, majRepere, dessinerRegles",
        _importer_plaque("etaler, plateauDe, deplacerPiece") + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      const et = etaler(api);
      const g = plateauDe(api);
      const vue1 = majRepere(api).pas;
      api.camera.zoom = 8; api.camera.updateProjectionMatrix();
      const vue8 = majRepere(api).pas;
      const apresZoom = plateauDe(api).pas;
      deplacerPiece(api, 0, 0.37, -0.29);
      const apresDeplacement = plateauDe(api).pas;
      /* LA GRILLE DESSINÉE : GridHelper naît dans XZ ; ses lignes paralleles
         a X ont un z constant, les autres un x constant. */
      const grille = nomme("plaque-plateau").children.find((o) => o.type === "GridHelper");
      const pos = grille.geometry.attributes.position;
      const xs = new Set(), zs = new Set();
      for (let i = 0; i < pos.count; i += 2) {
        if (Math.abs(pos.getX(i) - pos.getX(i + 1)) < 1e-9) xs.add(Math.round(pos.getX(i) * 1e6) / 1e6);
        if (Math.abs(pos.getZ(i) - pos.getZ(i + 1)) < 1e-9) zs.add(Math.round(pos.getZ(i) * 1e6) / 1e6);
      }
      /* LES TRAITS DES RÈGLES : le pied de chaque trait, le long de u. */
      const r = dessinerRegles(api, g, (v) => String(v), "u");
      const tp = r.traits.geometry.attributes.position;
      const pieds = new Set();
      for (let i = 8; i < tp.count; i += 2) {      /* 4 segments de contour d'abord */
        pieds.add(Math.round(tp["get" + g.u.toUpperCase()](i) * 1e6) / 1e6);
      }
      console.log(JSON.stringify({
        g, largeur: et.largeur, profondeur: et.profondeur,
        vue1, vue8, apresZoom, apresDeplacement,
        xs: [...xs].sort((a, b) => a - b), zs: [...zs].sort((a, b) => a - b),
        pieds: [...pieds].sort((a, b) => a - b),
      }));
    """))
    g = sortie["g"]
    assert g["axe"] == "y" and (g["u"], g["v"]) == ("x", "z"), g
    assert abs(g["cote"] - g["cases"] * g["pas"]) < 1e-12, g
    assert 10 <= g["cases"] <= 25, g
    assert g["cote"] >= max(sortie["largeur"], sortie["profondeur"]), sortie
    mant = g["pas"] / 10 ** math.floor(math.log10(g["pas"]))
    assert min(abs(mant - m) for m in (1, 2, 5)) < 1e-9, g["pas"]
    # STABLE : le pas de vue a changé de 16 fois entre les deux zooms, le pas du
    # plateau n'a pas bougé — ni au zoom, ni au déplacement.
    assert sortie["vue1"] != sortie["vue8"], sortie
    assert sortie["apresZoom"] == g["pas"] == sortie["apresDeplacement"], sortie
    # LA GRILLE VAUT LE PAS : cases + 1 lignes dans chaque direction, espacées
    # du pas, d'un bord à l'autre du côté…
    for nom in ("xs", "zs"):
        lignes = sortie[nom]
        assert len(lignes) == g["cases"] + 1, (nom, len(lignes), g)
        ecarts = [b - a for a, b in zip(lignes, lignes[1:])]
        assert all(abs(e - g["pas"]) < 1e-5 for e in ecarts), (nom, ecarts)
        assert abs(lignes[-1] - lignes[0] - g["cote"]) < 1e-5, (nom, lignes)
    # …ET LES TRAITS DES RÈGLES TOMBENT SUR CES LIGNES-LÀ, un pour une.
    assert sortie["pieds"] == sortie["xs"], (sortie["pieds"], sortie["xs"])


def test_les_REGLES_sont_DESSINEES_par_le_canevas_avec_les_LIBELLES_de_la_PAGE():
    """« graduée sur les côtés » — comme un plateau de slicer : origine à un
    coin, deux règles le long des deux bords, traits et libellés, contour.
    On lit ce qui est DESSINÉ (les segments) et ce qui est ÉCRIT (les textes
    sur les bandes, par le canevas 2D factice du montage), jamais le code.

    LA DOCTRINE DES UNITÉS TIENT PAR L'ARCHITECTURE : viewer.js reçoit un
    FORMATEUR et une unité, et écrit exactement ce qu'ils rendent — le
    formateur de ce banc entoure ses nombres de guillemets, et ce sont ces
    guillemets qu'on retrouve sur la texture. Ni plaque.js ni viewer.js ne
    mettent un nombre en forme (test_le_plateau_a_sa_grille…), et la page
    passe fmtMesure, le seul formateur de l'écran.

    L'ORIGINE EST EN BAS À GAUCHE DE LA VUE QUI REGARDE LE PLATEAU EN FACE, et
    le second chemin passe par la CAMÉRA : on pose la vraie vue d'axe (la
    table VUE_DE_PLAQUE de la page), on projette les quatre coins du plateau,
    et l'origine doit être celui de plus petites abscisse et ordonnée écran —
    pour les TROIS axes. Le sens de lecture des bandes en découle, et il se
    lit sur leur matrice.

    MÉMO ET LIBÉRATION : un second appel identique rend le même objet sans
    écrire un texte de plus ; un changement d'unité redessine ET libère les
    textures d'avant (l'évènement dispose de three.js en témoigne).
    """
    sortie = json.loads(_node_trois(
        "cadrer, projeter, orienter, dessinerRegles, effacerRegles",
        _importer_plaque("etaler, plateauDe, geometriePlateau")
        + _table_js("etabli/etabli.js", "VUE_DE_PLAQUE")
        + _constantes_viewer("LIBELLES_SERRES") + _fonction_viewer("graduationsDe")
        + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      etaler(api);
      const g = plateauDe(api);
      const fmt = (v) => "\u00ab" + v.toFixed(4) + "\u00bb";
      const r = dessinerRegles(api, g, fmt, "u. glTF");
      const appels = (b) => b.material.map.image.appels;
      const dirLocal = (b, v) => v.clone().applyQuaternion(b.quaternion).toArray();
      const grad = graduationsDe(g.cote, g.pas);
      const tp = r.traits.geometry.attributes.position;
      const segs = [];
      for (let i = 0; i < tp.count; i += 2) {
        segs.push([[tp.getX(i), tp.getY(i), tp.getZ(i)],
                   [tp.getX(i + 1), tp.getY(i + 1), tp.getZ(i + 1)]]);
      }
      /* memo : meme formateur, meme unite → meme objet, aucun texte de plus */
      const n1 = appels(r.bandes[0]).length;
      const r2 = dessinerRegles(api, g, fmt, "u. glTF");
      const memo = { meme: r2 === r, textes: appels(r.bandes[0]).length === n1 };
      /* changement d'unite → redessin, et les textures d'avant sont LIBEREES */
      let liberees = 0;
      for (const b of r.bandes) b.material.map.addEventListener("dispose", () => { liberees++; });
      const r3 = dessinerRegles(api, g, (v) => (v * 1000).toFixed(1), "mm");
      const groupes = api.scene.children.filter((o) => o.name === "lib3d-regles").length;
      /* L'ORIGINE EN BAS A GAUCHE, PAR LA CAMERA — pour les trois axes. */
      const coinsEcran = {};
      for (const axe of ["x", "y", "z"]) {
        const [u, v] = ["x", "y", "z"].filter((a) => a !== axe);
        /* la geometrie du MODULE, pas une geometrie ecrite a la main : c'est
           elle qui porte le coin et le sens, et c'est elle qu'on mesure. */
        const geo = geometriePlateau(2.3, 1.1, 0.2, axe);
        const rr = dessinerRegles(api, geo, (val) => String(val), "u");
        projeter(api, "orthographique");
        orienter(api, VUE_DE_PLAQUE[axe]);
        api.camera.updateMatrixWorld(true);
        const o = rr.origine.clone();
        const au = new THREE.Vector3(); au[u] = rr.sens.u * geo.cote;
        const av = new THREE.Vector3(); av[v] = rr.sens.v * geo.cote;
        const coins = [o, o.clone().add(au), o.clone().add(av), o.clone().add(au).add(av)]
          .map((c) => { const q = c.clone().project(api.camera); return [q.x, q.y]; });
        const coinsMonde = [o, o.clone().add(au), o.clone().add(av), o.clone().add(au).add(av)]
          .map((c) => c.toArray());
        coinsEcran[axe] = { coins, coinsMonde, cote: geo.cote, sens: rr.sens,
          coinGeo: geo.coin, sensGeo: geo.sens,
          bandeU: dirLocal(rr.bandes[0], new THREE.Vector3(1, 0, 0)),
          bandeV: dirLocal(rr.bandes[1], new THREE.Vector3(1, 0, 0)),
          normaleU: dirLocal(rr.bandes[0], new THREE.Vector3(0, 0, 1)),
          normaleV: dirLocal(rr.bandes[1], new THREE.Vector3(0, 0, 1)),
          hautU: dirLocal(rr.bandes[0], new THREE.Vector3(0, 1, 0)),
          centreU: rr.bandes[0].position.toArray(),
          centreV: rr.bandes[1].position.toArray(), origine: o.toArray() };
      }
      const efface = effacerRegles(api);
      console.log(JSON.stringify({
        g, valeurs: grad.valeurs, saut: grad.saut, textes: r.textes, segs,
        origine: r.origine.toArray(), sens: r.sens,
        bandeU: appels(r.bandes[0]), bandeV: appels(r.bandes[1]),
        largeurCanevas: r.bandes[0].material.map.image.width,
        memo, liberees, textesMm: r3.textes, groupes, coinsEcran, efface,
        reste: api.scene.children.filter((o) => o.name === "lib3d-regles").length,
      }));
    """))
    g, valeurs = sortie["g"], sortie["valeurs"]
    # les graduations : 0, pas, …, cote — cases + 1 valeurs
    assert len(valeurs) == g["cases"] + 1, (len(valeurs), g)
    assert all(abs(v - k * g["pas"]) < 1e-12 for k, v in enumerate(valeurs))
    # LES TEXTES SONT CEUX DU FORMATEUR, guillemets compris — à chaque `saut`
    saut = sortie["saut"]
    assert saut == (2 if len(valeurs) > 13 else 1), (saut, len(valeurs))
    attendus = [f"\u00ab{v:.4f}\u00bb" if k % saut == 0 else None
                for k, v in enumerate(valeurs)]
    assert sortie["textes"] == attendus, (sortie["textes"], attendus)
    # ÉCRITS SUR LES DEUX BANDES, dans l'ordre, l'unité en dernier, à des
    # abscisses croissantes proportionnelles à la valeur (bornées aux marges)
    for nom in ("bandeU", "bandeV"):
        ecrits = sortie[nom]
        assert [e["texte"] for e in ecrits] == \
            [t for t in attendus if t is not None] + ["u. glTF"], (nom, ecrits)
        xs = [e["x"] for e in ecrits]
        assert xs == sorted(xs) and len(set(xs)) == len(xs), (nom, xs)
        longueur = g["cote"] + 1.2 * g["pas"]
        W = sortie["largeurCanevas"]
        # retenu au bord par sa PROPRE demi-largeur — celle que le canevas
        # factice du montage mesure (dix pixels par glyphe) : le « 0 » du coin
        # reste entier et au plus près de son trait
        for e, k in zip(ecrits[:-1], [k for k in range(len(valeurs)) if k % saut == 0]):
            demi = 10 * len(e["texte"]) / 2
            attendu = min(W - demi, max(demi, valeurs[k] / longueur * W))
            assert abs(e["x"] - attendu) < 1e-6, (nom, e, attendu)
        assert ecrits[0]["x"] == 10 * len(ecrits[0]["texte"]) / 2, ecrits[0]
    # LES SEGMENTS : 4 de contour + 2 traits par graduation, le contour fait
    # le tour du carré depuis l'origine, les traits partent des bords VERS
    # L'EXTÉRIEUR et sont plus longs sous un libellé
    segs = sortie["segs"]
    assert len(segs) == 4 + 2 * len(valeurs), len(segs)
    o = sortie["origine"]
    iu, iv = "xyz".index(g["u"]), "xyz".index(g["v"])
    su, sv = sortie["sens"]["u"], sortie["sens"]["v"]
    # (positions lues dans un tampon Float32 : la simple précision borne l'écart)
    proche = lambda a, b: all(abs(x - y) < 1e-6 for x, y in zip(a, b))
    assert proche(segs[0][0], o) and abs(segs[0][1][iu] - (o[iu] + su * g["cote"])) < 1e-6
    assert abs(segs[1][1][iv] - (o[iv] + sv * g["cote"])) < 1e-6
    assert proche(segs[3][1], o)
    for k, val in enumerate(valeurs):
        tu, tv = segs[4 + 2 * k], segs[5 + 2 * k]
        assert abs(tu[0][iu] - (o[iu] + su * val)) < 1e-6, (k, tu)
        assert (tu[1][iv] - tu[0][iv]) * sv < 0, (k, tu)          # vers l'extérieur
        assert abs(tv[0][iv] - (o[iv] + sv * val)) < 1e-6, (k, tv)
        assert (tv[1][iu] - tv[0][iu]) * su < 0, (k, tv)
        longueur_trait = abs(tu[1][iv] - tu[0][iv])
        assert longueur_trait > 0
        if attendus[k] is None:
            assert longueur_trait < abs(segs[4][1][iv] - segs[4][0][iv]), k
    # LE CONTOUR EST LE BORD DU PLATEAU, ET L'ORIGINE EN EST UN COIN — pas un
    # point à −côté/2 d'où l'on partirait dans le sens des règles. MUTATION
    # VERTE du premier tour : une origine qui ignorait `sens` laissait tout
    # au vert, parce que segments, traits et bandes se lisaient cohérents
    # avec eux-mêmes ; seuls les coins du carré du plateau les rattachent au
    # monde. On les lit sur le contour, dans les deux axes du plan.
    bord = {round(g["coin"][g["u"]], 6), round(g["coin"][g["u"]] + su * g["cote"], 6)}
    assert bord == {round(k, 6) for seg in segs[:4] for pt in seg for k in [pt[iu]]}, \
        (bord, segs[:4])
    bord_v = {round(g["coin"][g["v"]], 6), round(g["coin"][g["v"]] + sv * g["cote"], 6)}
    assert bord_v == {round(pt[iv], 6) for seg in segs[:4] for pt in seg}, (bord_v, segs[:4])
    assert round(o[iu], 6) in bord and round(o[iv], 6) in bord_v, (o, bord, bord_v)
    # MÉMO ET LIBÉRATION
    assert sortie["memo"] == {"meme": True, "textes": True}, sortie["memo"]
    assert sortie["liberees"] == 2, sortie["liberees"]
    assert sortie["textesMm"][0] == "0.0" and sortie["textesMm"][2] == "400.0"
    assert sortie["groupes"] == 1, sortie["groupes"]     # jamais deux jeux de règles
    assert sortie["efface"] is True and sortie["reste"] == 0
    # L'ORIGINE EST EN BAS À GAUCHE DE LA VUE DE FACE — pour les trois axes —
    # et chaque bande LIT dans le sens où son axe croît à l'écran (pour l'axe
    # x, c'est v qui est horizontal et u vertical : la table des orientations
    # le décide, pas ce banc) ; leur normale est +axe.
    for axe, c in sortie["coinsEcran"].items():
        coins = c["coins"]
        assert coins[0][0] <= min(k[0] for k in coins) + 1e-9, (axe, coins)
        assert coins[0][1] <= min(k[1] for k in coins) + 1e-9, (axe, coins)
        u, v = [a for a in "xyz" if a != axe]
        iu, iv, ia = "xyz".index(u), "xyz".index(v), "xyz".index(axe)
        assert abs(c["bandeU"][iu] - c["sens"]["u"]) < 1e-9, (axe, c)
        assert abs(c["bandeV"][iv] - c["sens"]["v"]) < 1e-9, (axe, c)
        assert abs(c["normaleU"][ia] - 1) < 1e-9, (axe, c)
        # LES DEUX bandes sont HORS du plateau : U du côté opposé à v, V du
        # côté opposé à u — la famille se ferme sur les deux, pas sur une
        assert (c["centreU"][iv] - c["origine"][iv]) * c["sens"]["v"] < 0, (axe, c)
        assert (c["centreV"][iu] - c["origine"][iu]) * c["sens"]["u"] < 0, (axe, c)
        assert abs(c["normaleV"][ia] - 1) < 1e-9, (axe, c)
        # …ET L'ORIGINE DESSINÉE EST LE `coin` DE LA GÉOMÉTRIE, à la levée
        # près sur l'axe : une seule source (mutation verte du premier tour :
        # viewer.js recalculait ±côté/2 et, pour l'axe y, désignait un autre
        # coin que `coin`)
        assert abs(c["origine"][iu] - c["coinGeo"][u]) < 1e-12, (axe, c)
        assert abs(c["origine"][iv] - c["coinGeo"][v]) < 1e-12, (axe, c)
        assert c["sens"] == c["sensGeo"], (axe, c)
        # …et les quatre coins dessinés SONT ceux du carré du plateau, centré
        # sur l'origine du monde : ±côté/2 sur u et sur v, rien d'autre
        demi = c["cote"] / 2
        for k in c["coinsMonde"]:
            assert round(abs(k[iu]), 6) == round(demi, 6), (axe, k, demi)
            assert round(abs(k[iv]), 6) == round(demi, 6), (axe, k, demi)
        assert len({(round(k[iu], 6), round(k[iv], 6)) for k in c["coinsMonde"]}) == 4
        # (l'un des deux axes du plan est horizontal à l'écran, l'autre vertical)
        du_, dv_ = coins[1], coins[2]
        horizontal_u = abs(du_[0] - coins[0][0]) > 0.1 and abs(dv_[1] - coins[0][1]) > 0.1
        vertical_u = abs(du_[1] - coins[0][1]) > 0.1 and abs(dv_[0] - coins[0][0]) > 0.1
        assert horizontal_u != vertical_u, (axe, coins)
    # ── ET LA PAGE CÂBLE LE TOUT AVEC SON SEUL FORMATEUR ────────────────────
    code = _code("etabli/etabli.js")
    grad = _fonction_etabli("graduerPlateau")
    assert "dessinerRegles(S.vueA, PLQ.active ? plateauDe(S.vueA) : null," in grad
    assert "fmtMesure, uniteCourante());" in grad
    lu = _fonction_etabli("lireRepere")
    assert "graduerPlateau();" in lu
    assert lu.index("REP.echelle = echelleMm(") < lu.index("graduerPlateau();")
    assert code.count("graduerPlateau();") == 1, code.count("graduerPlateau();")


def test_une_piece_se_DEPLACE_par_le_BERCEAU_et_sa_pose_ne_bouge_pas_d_un_BIT():
    """« déplacer les éléments ou la pièce sur la grille » — et le piège le
    plus cher de la plaque tient toujours : le déplacement écrit dans le
    BERCEAU, jamais dans la pièce, si bien que l'`objectChange` du gizmo (qui
    lit `o.position`) ne peut structurellement pas le voir, et que
    decalageEtalement() continue de dire vrai — la lecture du rail reste celle
    du MODÈLE.

    Sous l'enveloppe tournée et mise à l'échelle : le déplacement demandé (du,
    dv) dans les axes du plateau est celui que l'EMPREINTE mesure, à 1e-9, et
    le décalage annoncé par le module est la différence des centres monde.
    """
    sortie = json.loads(_node_trois(
        "cadrer",
        _importer_plaque("etaler, plateauDe, empreinteDe, deplacerPiece, poserCoin, "
                         "decalageEtalement, dispositionDe") + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      const centre = (o) => new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3()).toArray();
      const assemble = pieces.map(centre);
      etaler(api);
      racine.updateMatrixWorld(true);
      const g = plateauDe(api);
      const poses = pieces.map(pose);
      const emp0 = empreinteDe(api, 1);
      const d0 = decalageEtalement(api, pieces[1]).decalage.toArray();
      const ok = deplacerPiece(api, 1, 0.37, -0.29);
      racine.updateMatrixWorld(true);
      const emp1 = empreinteDe(api, 1);
      const d1 = decalageEtalement(api, pieces[1]).decalage.toArray();
      const c1 = centre(pieces[1]);
      /* la lecture du MODELE : centre courant moins decalage */
      const lecture = c1.map((v, i) => v - d1[i]);
      const dispo = dispositionDe(api);
      /* poser le COIN a un point donne */
      const posee = poserCoin(api, 2, g.coin[g.u] + 3 * g.pas, g.coin[g.v] + 5 * g.pas);
      const emp2 = empreinteDe(api, 2);
      const refus = [deplacerPiece(api, 7, 1, 1), deplacerPiece(api, 1, NaN, 0),
                     deplacerPiece(api, 1, 0, Infinity)];
      console.log(JSON.stringify({ g, ok, emp0, emp1, d0, d1, assemble: assemble[1],
        lecture, posesAvant: poses, posesApres: pieces.map(pose), dispo,
        posee, emp2, refus, autres: [0, 2].map((k) => decalageEtalement(api, pieces[k]).decalage.toArray()) }));
    """))
    g = sortie["g"]
    iu, iv, ia = "xyz".index(g["u"]), "xyz".index(g["v"]), "xyz".index(g["axe"])
    assert sortie["ok"] is True
    # L'EMPREINTE A BOUGÉ D'EXACTEMENT (du, dv), et pas d'un cheveu sur l'axe
    e0, e1 = sortie["emp0"], sortie["emp1"]
    assert abs((e1["u"] - e0["u"]) - 0.37) < 1e-9, (e0, e1)
    assert abs((e1["v"] - e0["v"]) - (-0.29)) < 1e-9, (e0, e1)
    assert abs(e1["bas"]) < 1e-9 and abs(e0["bas"]) < 1e-9, (e0, e1)     # au contact
    assert abs(e1["l"] - e0["l"]) < 1e-12 and abs(e1["p"] - e0["p"]) < 1e-12
    # LE DÉCALAGE ANNONCÉ A SUIVI, sur les deux axes du plan seulement
    d0, d1 = sortie["d0"], sortie["d1"]
    assert abs((d1[iu] - d0[iu]) - 0.37) < 1e-9, (d0, d1)
    assert abs((d1[iv] - d0[iv]) - (-0.29)) < 1e-9, (d0, d1)
    assert abs(d1[ia] - d0[ia]) < 1e-12, (d0, d1)
    # …ET LA LECTURE DU MODÈLE N'A PAS BOUGÉ : le centre assemblé, à 1e-9
    for a, b in zip(sortie["lecture"], sortie["assemble"]):
        assert abs(a - b) < 1e-9, (sortie["lecture"], sortie["assemble"])
    # LA POSE DES TROIS PIÈCES, AU BIT PRÈS — celle qu'on déplace comme les autres
    assert sortie["posesApres"] == sortie["posesAvant"], sortie["posesApres"]
    # le plan de plaque porte le déplacement, en unités du modèle
    dispo = sortie["dispo"]
    assert dispo["axe"] == g["axe"] and dispo["pas"] == g["pas"], dispo
    p1 = next(q for q in dispo["pieces"] if q["index"] == 1)
    assert abs(p1["dx"] - d1[iu]) < 1e-12 and abs(p1["dy"] - d1[iv]) < 1e-12, (p1, d1)
    assert p1["rot"] == 0
    # poserCoin met le COIN là où on le demande — à 3 et 5 pas du coin du
    # plateau, sur des traits de la grille
    assert sortie["posee"] is True
    e2 = sortie["emp2"]
    assert abs(e2["u"] - (g["coin"][g["u"]] + 3 * g["pas"])) < 1e-9, (e2, g)
    assert abs(e2["v"] - (g["coin"][g["v"]] + 5 * g["pas"])) < 1e-9, (e2, g)
    # une clé inconnue, un NaN, un infini : refusés, sans lever
    assert sortie["refus"] == [False, False, False], sortie["refus"]
    # les deux autres pièces n'ont pas bougé de leur place d'étalement… sauf
    # la 2, qu'on vient de poser
    assert len(sortie["autres"]) == 2


def test_la_ROTATION_tourne_autour_du_CENTRE_dans_le_PLAN_et_se_LIT_par_Rodrigues():
    """La rotation autour de la normale au plateau, comme les slicers : autour
    du CENTRE de la pièce (elle ne s'envole pas), dans le plan (son assise ne
    change pas), et par un PIVOT distinct du berceau — sans quoi le décalage
    que le rail retranche deviendrait faux de (R − I)(t − c), plausible et
    muet (voir poserPivot).

    Sous l'enveloppe tournée et mise à l'échelle, la matrice du pivot n'est
    PAS une rotation décomposable : c'est le cas qui distingue une matrice
    écrite à la main d'un quaternion. Le second chemin est Rodrigues, en
    Python, sur la direction monde de la pièce.

    ET LE PLAN FAIT LE TOUR : rangé puis ré-étalé AVEC le plan composé, le
    plateau retrouve les mêmes empreintes, tournées comprises.
    """
    sortie = json.loads(_node_trois(
        "cadrer",
        _importer_plaque("etaler, ranger, plateauDe, empreinteDe, poserAngle, "
                         "rotationDe, deplacerPiece, decalageEtalement, dispositionDe") + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      etaler(api);
      racine.updateMatrixWorld(true);
      const g = plateauDe(api);
      const dirMonde = (o) => new THREE.Vector3(1, 0, 0)
        .applyMatrix4(new THREE.Matrix4().extractRotation(
          new THREE.Matrix4().copy(o.matrixWorld))).toArray();
      const lin = (o) => { const e = o.matrixWorld.elements; return [e[0], e[1], e[2]]; };
      const poses = pieces.map(pose);
      const emp0 = empreinteDe(api, 1);
      const d0 = decalageEtalement(api, pieces[1]).decalage.toArray();
      const lin0 = lin(pieces[1]);
      const ok90 = poserAngle(api, 1, 90);
      racine.updateMatrixWorld(true);
      const emp90 = empreinteDe(api, 1);
      const ok37 = poserAngle(api, 1, 37);
      racine.updateMatrixWorld(true);
      const emp37 = empreinteDe(api, 1);
      const d37 = decalageEtalement(api, pieces[1]).decalage.toArray();
      const lin37 = lin(pieces[1]);
      const rot37 = rotationDe(api, 1);
      poserAngle(api, 1, 370); const rot370 = rotationDe(api, 1);
      poserAngle(api, 1, -190); const rotMoins = rotationDe(api, 1);
      const refus = poserAngle(api, 1, "abc");
      const rotApresRefus = rotationDe(api, 1);
      poserAngle(api, 1, 37);
      deplacerPiece(api, 0, 0.61, 0.13);
      poserAngle(api, 2, -120);
      racine.updateMatrixWorld(true);
      const avant = [0, 1, 2].map((k) => empreinteDe(api, k));
      const plan = dispositionDe(api);
      /* LE TOUR : ranger, re-etaler AVEC le plan → memes empreintes */
      ranger(api);
      racine.updateMatrixWorld(true);
      const rangees = pieces.map(pose);
      const et2 = etaler(api, plan);
      racine.updateMatrixWorld(true);
      const apres = [0, 1, 2].map((k) => empreinteDe(api, k));
      const rots = [0, 1, 2].map((k) => rotationDe(api, k));
      console.log(JSON.stringify({ g, ok90, ok37, emp0, emp90, emp37, d0, d37,
        lin0, lin37, rot37, rot370, rotMoins, refus, rotApresRefus,
        posesAvant: poses, posesApres: pieces.map(pose), rangees,
        plan, planApplique: et2.planApplique, avant, apres, rots }));
    """))
    g = sortie["g"]
    e0, e90, e37 = sortie["emp0"], sortie["emp90"], sortie["emp37"]
    assert sortie["ok90"] is True and sortie["ok37"] is True
    # À 90° : les côtés de l'empreinte S'ÉCHANGENT, le centre et l'assise ne
    # bougent pas
    assert abs(e90["l"] - e0["p"]) < 1e-9 and abs(e90["p"] - e0["l"]) < 1e-9, (e0, e90)
    assert abs(e0["l"] - e0["p"]) > 0.05, e0            # non carrée : l'échange se voit
    for k in ("cu", "cv", "bas", "haut"):
        assert abs(e90[k] - e0[k]) < 1e-9, (k, e0, e90)
        assert abs(e37[k] - e0[k]) < 1e-9, (k, e0, e37)
    # LE DÉCALAGE QUE LE RAIL RETRANCHE N'A PAS BOUGÉ : c'est le pivot qui
    # tourne, pas le berceau
    for a, b in zip(sortie["d0"], sortie["d37"]):
        assert abs(a - b) < 1e-12, (sortie["d0"], sortie["d37"])
    # RODRIGUES : la première colonne de la matrice monde de la pièce (son +X
    # dans le monde) a tourné de 37° autour de +axe
    n = [0.0, 0.0, 0.0]
    n["xyz".index(g["axe"])] = 1.0
    attendu = _rodrigues(n, 37, sortie["lin0"])
    for a, b in zip(sortie["lin37"], attendu):
        assert abs(a - b) < 1e-9, (sortie["lin37"], attendu)
    # …et ce n'est pas un cas où la rotation serait triviale : la colonne a un
    # module non unitaire (l'enveloppe est mise à l'échelle) et trois
    # composantes non nulles
    assert abs(math.hypot(*sortie["lin0"]) - 1) > 0.1, sortie["lin0"]
    assert all(abs(c) > 1e-3 for c in sortie["lin0"]), sortie["lin0"]
    # l'angle est ABSOLU et ramené dans ]−180, 180]
    assert sortie["rot37"] == 37 and sortie["rot370"] == 10 and sortie["rotMoins"] == 170
    assert sortie["refus"] is False and sortie["rotApresRefus"] == 170
    # la pose des pièces, au bit près, tournées ou non
    assert sortie["posesApres"] == sortie["posesAvant"]
    assert sortie["rangees"] == sortie["posesAvant"]      # et après rangement
    # LE TOUR PAR LE PLAN : mêmes empreintes, mêmes rotations
    plan = sortie["plan"]
    assert sorted(q["index"] for q in plan["pieces"]) == [0, 1, 2]
    assert {q["index"]: q["rot"] for q in plan["pieces"]} == {0: 0, 1: 37, 2: -120}
    assert sortie["planApplique"] is True
    assert sortie["rots"] == [0, 37, -120]
    for k, (a, b) in enumerate(zip(sortie["avant"], sortie["apres"])):
        for champ in ("u", "v", "l", "p", "cu", "cv", "bas", "haut"):
            assert abs(a[champ] - b[champ]) < 1e-9, (k, champ, a, b)


def test_l_ETALEMENT_applique_le_PLAN_s_il_existe_sinon_dispose_et_le_PLATEAU_ne_bouge_pas():
    """À l'entrée de la plaque : si un plan existe, etaler() APPLIQUE cette
    disposition au lieu de disposer() — pour les pièces qu'il nomme ; les
    autres gardent leur place d'étalement. Un plan d'un AUTRE axe est ignoré
    et dit : ses dx/dy parlent d'axes qui ne sont pas ceux du plateau.

    ET LE PLATEAU NE DÉPEND QUE DU MAILLAGE : même côté, même pas, même coin
    avec ou sans plan, quoi qu'on ait déplacé. Deux visites de la même version
    voient le même plateau — c'est ce qui rend les règles comparables d'une
    fois sur l'autre.
    """
    sortie = json.loads(_node_trois(
        "cadrer",
        _importer_plaque("etaler, ranger, plateauDe, empreinteDe, rotationDe, "
                         "decalageEtalement") + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      const lire = () => ({
        g: plateauDe(api),
        d: pieces.map((o) => decalageEtalement(api, o).decalage.toArray()),
        emp: [0, 1, 2].map((k) => empreinteDe(api, k)),
        rot: [0, 1, 2].map((k) => rotationDe(api, k)),
      });
      const et0 = etaler(api); racine.updateMatrixWorld(true);
      const sans = lire();
      ranger(api); racine.updateMatrixWorld(true);
      const g = sans.g;
      const plan = { axe: g.axe, pas: g.pas, pieces: [
        { index: 0, dx: 1.234, dy: -0.567, rot: 15 },
        { index: 2, dx: -0.321, dy: 0.876, rot: -60 },
        { index: 9, dx: 5, dy: 5, rot: 5 } ] };
      const et1 = etaler(api, plan); racine.updateMatrixWorld(true);
      const avec = lire();
      ranger(api); racine.updateMatrixWorld(true);
      const autreAxe = etaler(api, { ...plan, axe: g.axe === "x" ? "z" : "x" });
      racine.updateMatrixWorld(true);
      const ignore = lire();
      ranger(api);
      console.log(JSON.stringify({ sans, avec, ignore,
        appliques: [et0.planApplique, et1.planApplique, autreAxe.planApplique] }));
    """))
    sans, avec, ignore = sortie["sans"], sortie["avec"], sortie["ignore"]
    g = sans["g"]
    iu, iv, ia = "xyz".index(g["u"]), "xyz".index(g["v"]), "xyz".index(g["axe"])
    assert sortie["appliques"] == [False, True, False], sortie["appliques"]
    # LES PIÈCES NOMMÉES prennent (dx, dy, rot) du plan…
    assert abs(avec["d"][0][iu] - 1.234) < 1e-12 and abs(avec["d"][0][iv] + 0.567) < 1e-12
    assert abs(avec["d"][2][iu] + 0.321) < 1e-12 and abs(avec["d"][2][iv] - 0.876) < 1e-12
    assert avec["rot"] == [15, 0, -60], avec["rot"]
    # …la composante d'AXE reste le posé au contact : la même que sans plan
    for k in range(3):
        assert abs(avec["d"][k][ia] - sans["d"][k][ia]) < 1e-12, (k, avec["d"], sans["d"])
        assert abs(avec["emp"][k]["bas"]) < 1e-9, avec["emp"][k]
    # …LA PIÈCE NON NOMMÉE garde sa place d'étalement, et l'index inconnu (9)
    # n'a rien cassé
    assert avec["d"][1] == sans["d"][1], (avec["d"][1], sans["d"][1])
    assert avec["emp"][1] == sans["emp"][1]
    # …et les déplacements du plan ne sont PAS ceux de disposer (le banc
    # mesurerait sinon une coïncidence)
    assert abs(avec["d"][0][iu] - sans["d"][0][iu]) > 0.01
    # UN PLAN D'UN AUTRE AXE EST IGNORÉ : tout comme sans plan
    assert ignore["d"] == sans["d"] and ignore["rot"] == [0, 0, 0], ignore
    # LE PLATEAU NE BOUGE PAS : même géométrie dans les trois cas
    assert avec["g"] == g and ignore["g"] == g, (avec["g"], ignore["g"], g)


def _harnais_glisser() -> str:
    """La scène, le faux canevas à écouteurs, les doublures de la page et la
    VRAIE glisserSurPlaque, branchée — commun au glisser et à l'anneau, pour
    que les deux mesurent le même geste sur la même scène."""
    sel = (FRONT / "lib3d" / "selection.js").resolve().as_uri()
    return (_importer_plaque("etaler, estEtalee, plateauDe, empreinteDe, sousLePointeur, "
                             "pointSurPlateau, rotationDe, angleSurPlateau, poserAngle, "
                             "aimanter, poserCoin, marquerPiece, montrerPiece")
            + f"import {{ TOLERANCE_CLIC }} from {json.dumps(sel)};\n"
            + _constantes_etabli("PAS_ROTATION") + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      etaler(api); racine.updateMatrixWorld(true);
      const g = plateauDe(api);
      const PLQ = { courante: null };
      const courantes = [];
      let notes = 0;
      const pieceCourante = (cle) => { PLQ.courante = cle; marquerPiece(api, cle); courantes.push(cle); };
      const noterPlan = () => { notes++; };
      const rendreRotation = () => {};
      let _gestePlaque = null;
      const canvas = {
        listeners: {},
        addEventListener(t, f) { (this.listeners[t] = this.listeners[t] || []).push(f); },
        getBoundingClientRect() { return { left: 0, top: 0, width: 860, height: 824 }; },
        captures: 0, setPointerCapture() { this.captures++; },
      };
      const fire = (t, ev) => { for (const f of canvas.listeners[t] || []) f(ev); };
      const px = (p) => { const q = p.clone().project(api.camera);
        return { clientX: ((q.x + 1) / 2) * 860, clientY: ((1 - q.y) / 2) * 824 }; };
      const pointMonde = (u, v) => { const w = new THREE.Vector3(); w[g.u] = u; w[g.v] = v; return w; };
    """ + _fonction_etabli("glisserSurPlaque") + """
      glisserSurPlaque(api, canvas);
    """)


def test_l_AIMANTATION_aligne_le_COIN_sur_le_pas_du_plateau_et_Maj_la_libere():
    """LE GESTE DES SLICERS, EXÉCUTÉ SUR LA VRAIE glisserSurPlaque : un
    poser sur une pièce coupe l'orbite (`controls.enabled`), un mouvement
    sous TOLERANCE_CLIC ne bouge rien (le clic reste un clic), au-delà la
    pièce suit la différence des points du PLAN DU PLATEAU sous le pointeur,
    son COIN aimanté au pas depuis le coin du plateau — Maj la libère — et le
    relever rend l'orbite. Le poser sur le vide ne coupe rien. Le poser sur
    l'ANNEAU tourne la pièce de la différence d'angle, Maj arrondit à
    PAS_ROTATION.

    Les pixels viennent de la VRAIE projection de la caméra (canevas 860 ×
    824, non carré) ; les cibles sont des points du plateau construits en
    monde puis projetés, et le second chemin de l'aimantation est le `round`
    de Python sur les nombres relevés. La rotation cible est construite avec
    `applyAxisAngle` de three.js — pas avec la formule d'angle du module.
    """
    sortie = json.loads(_node_trois(
        "cadrer",
        _harnais_glisser() + """
      const r = { types: Object.keys(canvas.listeners).sort(), g,
                  tolerance: TOLERANCE_CLIC, pasRotation: PAS_ROTATION };
      /* LE POSER SUR UNE PIECE : au centre de la piece 1, sur sa face haute */
      const emp0 = empreinteDe(api, 1);
      const c = pointMonde(emp0.cu, emp0.cv); c[g.axe] = emp0.haut;
      const p0 = px(c);
      const ndc0 = { x: (p0.clientX / 860) * 2 - 1, y: -((p0.clientY / 824) * 2 - 1) };
      const P0 = pointSurPlateau(api, ndc0);
      fire("pointerdown", { button: 0, pointerId: 1, ...p0, shiftKey: false });
      r.poser = { enabled: api.controls.enabled, courantes: [...courantes], captures: canvas.captures };
      /* SOUS LA TOLERANCE : rien ne bouge */
      fire("pointermove", { pointerId: 1, clientX: p0.clientX + 2, clientY: p0.clientY + 2, shiftKey: false });
      r.sousTolerance = empreinteDe(api, 1);
      /* AU-DELA : la cible est un point du PLATEAU, construit en monde, et
         posee a 0,37 pas et 0,62 pas d'un trait de la grille — quelle que
         soit la place que disposer() a donnee au coin — pour que l'aimantation
         ait quelque chose a faire des deux cotes. */
      const fu = (emp0.u - g.coin[g.u]) / g.pas, fv = (emp0.v - g.coin[g.v]) / g.pas;
      const du = (Math.floor(fu) + 1.37 - fu) * g.pas;
      const dv = (Math.floor(fv) - 1 + 0.62 - fv) * g.pas;
      const P1 = pointMonde(P0.u + du, P0.v + dv);
      fire("pointermove", { pointerId: 1, ...px(P1), shiftKey: false });
      r.aimante = empreinteDe(api, 1);
      r.coin0 = { u: emp0.u, v: emp0.v };
      r.delta1 = { du, dv };
      /* MAJ : libre, exactement la difference des points */
      const du2 = 0.83 * g.pas, dv2 = 0.41 * g.pas;
      const P2 = pointMonde(P0.u + du2, P0.v + dv2);
      fire("pointermove", { pointerId: 1, ...px(P2), shiftKey: true });
      r.libre = empreinteDe(api, 1);
      r.delta2 = { du: du2, dv: dv2 };
      r.pendant = { enabled: api.controls.enabled, notes };
      fire("pointerup", { pointerId: 1, button: 0, ...px(P2) });
      r.releve = { enabled: api.controls.enabled };
      /* un mouvement APRES le relever ne fait plus rien */
      fire("pointermove", { pointerId: 1, ...px(P0 ? pointMonde(P0.u + 3, P0.v) : c), shiftKey: false });
      r.apres = empreinteDe(api, 1);
      /* LE VIDE : un point DU PLATEAU, dans son coin, loin des pieces — et
         non un coin d'ecran dont le rayon rate le plan : la, `pointSurPlateau`
         rend null et la garde suivante masquerait l'absence de la garde sur
         la cible (mutation verte du second tour). Le temoin : ce pixel
         touche bien le plateau et ne touche aucune piece. */
      const coinVide = pointMonde(g.coin[g.u] + g.sens.u * 0.03 * g.cote,
                                  g.coin[g.v] + g.sens.v * 0.03 * g.cote);
      const pv = px(coinVide);
      const ndcVide = { x: (pv.clientX / 860) * 2 - 1, y: -((pv.clientY / 824) * 2 - 1) };
      r.videTemoin = { plateau: pointSurPlateau(api, ndcVide) !== null,
                       piece: sousLePointeur(api, ndcVide) };
      fire("pointerdown", { button: 0, pointerId: 2, ...pv, shiftKey: false });
      r.vide = { enabled: api.controls.enabled, sous: sousLePointeur(api, ndcVide) };
      fire("pointerup", { pointerId: 2, button: 0, ...pv });
      /* UN CLIC (poser + relever au meme endroit) : rien ne bouge */
      const emp1 = empreinteDe(api, 1);
      const c1 = pointMonde(emp1.cu, emp1.cv); c1[g.axe] = emp1.haut;
      fire("pointerdown", { button: 0, pointerId: 3, ...px(c1), shiftKey: false });
      fire("pointerup", { pointerId: 3, button: 0, ...px(c1) });
      r.clic = { emp: empreinteDe(api, 1), enabled: api.controls.enabled };
      r.notes = notes;
      r.courantes = courantes;
      console.log(JSON.stringify(r));
    """))
    g = sortie["g"]
    assert sortie["types"] == ["pointercancel", "pointerdown", "pointermove", "pointerup"]
    # LE POSER coupe l'orbite, désigne la pièce, capture le pointeur
    assert sortie["poser"] == {"enabled": False, "courantes": [1], "captures": 1}
    # SOUS LA TOLÉRANCE, rien n'a bougé
    c0 = sortie["coin0"]
    assert abs(sortie["sousTolerance"]["u"] - c0["u"]) < 1e-12
    assert abs(sortie["sousTolerance"]["v"] - c0["v"]) < 1e-12
    assert sortie["tolerance"] == 4
    # L'AIMANTATION : le coin visé, arrondi au trait le plus proche depuis le
    # coin du plateau — le `round` de Python contre celui du module
    pas, cu, cv = g["pas"], g["coin"][g["u"]], g["coin"][g["v"]]
    vise_u = c0["u"] + sortie["delta1"]["du"]
    vise_v = c0["v"] + sortie["delta1"]["dv"]
    att_u = cu + round((vise_u - cu) / pas) * pas
    att_v = cv + round((vise_v - cv) / pas) * pas
    assert abs(sortie["aimante"]["u"] - att_u) < 1e-6, (sortie["aimante"], att_u)
    assert abs(sortie["aimante"]["v"] - att_v) < 1e-6, (sortie["aimante"], att_v)
    # …et l'aimantation a VRAIMENT déplacé le coin loin du point visé (sinon on
    # mesurerait une coïncidence)
    assert abs(abs(att_u - vise_u) - 0.37 * pas) < 1e-6, (att_u, vise_u, pas)
    assert abs(abs(att_v - vise_v) - 0.38 * pas) < 1e-6, (att_v, vise_v, pas)
    # MAJ : exactement la différence des points du plateau, sans arrondi
    assert abs(sortie["libre"]["u"] - (c0["u"] + sortie["delta2"]["du"])) < 1e-6
    assert abs(sortie["libre"]["v"] - (c0["v"] + sortie["delta2"]["dv"])) < 1e-6
    # pendant le geste l'orbite reste coupée et le plan est noté ; au relever
    # elle revient ; après, plus rien ne bouge
    assert sortie["pendant"] == {"enabled": False, "notes": 2}
    assert sortie["releve"] == {"enabled": True}
    assert sortie["apres"] == sortie["libre"]
    # LE VIDE ne coupe rien — et c'est bien un point du plateau sans pièce
    assert sortie["videTemoin"] == {"plateau": True, "piece": None}, sortie["videTemoin"]
    assert sortie["vide"] == {"enabled": True, "sous": None}
    # UN CLIC ne bouge rien et rend l'orbite
    assert sortie["clic"]["emp"] == sortie["libre"] and sortie["clic"]["enabled"] is True
    assert sortie["notes"] == 2                       # deux glissers, rien d'autre
    assert sortie["courantes"] == [1]                 # désignée une fois, puis déjà courante
    # ── ET LE CÂBLAGE : une fois, sur le canevas de A, hors du bloc ─────────
    code = _code("etabli/etabli.js")
    assert code.count("glisserSurPlaque(") == 2       # la définition et l'appel
    bloc = code.split('addEventListener("etabli:charge"', 1)[1]
    assert bloc.index("if (_clicBranche) return;") < bloc.index("glisserSurPlaque(S.vueA")
    assert "glisserSurPlaque(" not in _plaque_bloc()


def test_l_ANNEAU_tourne_la_piece_COURANTE_et_une_piece_MASQUEE_ne_se_saisit_pas():
    """LE SECOND GESTE DE LA SOURIS, sur la même glisserSurPlaque : le poser
    sur l'ANNEAU tourne la pièce de la différence d'angle autour de son centre
    — la cible est construite avec `applyAxisAngle` de three.js, pas avec la
    formule d'angle du module — et Maj arrondit à PAS_ROTATION. L'anneau garde
    son RAYON quand la pièce tourne (il respirait : 0,928 → 0,749 entre 0° et
    45°, la géométrie refaite à chaque mouvement), et un clic sur lui ne
    relâche pas la pièce courante.

    Et une pièce MASQUÉE par l'œil ne se saisit pas : le raycast de three.js
    ne saute PAS les objets invisibles (mesuré dans le fichier vendorisé :
    seul `layers` est testé), c'est le module qui filtre. L'œil qui masque la
    pièce courante la relâche, sans quoi les flèches pousseraient une pièce
    qu'on ne voit pas.
    """
    sortie = json.loads(_node_trois(
        "cadrer",
        _harnais_glisser() + """
      const r = { g, pasRotation: PAS_ROTATION };
      r.centreAvant = empreinteDe(api, 1);
      pieceCourante(1);
      /* L'ANNEAU : la piece 1 est courante, son anneau est visible */
      const marque = marquerPiece(api, 1);
      const anneau = nomme("plaque-poignee").children[0].geometry.parameters;
      const rayon = (anneau.innerRadius + anneau.outerRadius) / 2;
      const centre = pointMonde(marque.centre.u, marque.centre.v);
      const n = new THREE.Vector3(); n[g.axe] = 1;
      const bras = new THREE.Vector3(); bras[g.u] = rayon;
      const R0 = centre.clone().add(bras);
      const rot0 = rotationDe(api, 1);
      const pr0 = px(R0);
      const ndcR = { x: (pr0.clientX / 860) * 2 - 1, y: -((pr0.clientY / 824) * 2 - 1) };
      r.sousAnneau = sousLePointeur(api, ndcR);
      fire("pointerdown", { button: 0, pointerId: 4, ...pr0, shiftKey: false });
      /* + 37 degres autour de +axe, par three.js */
      const R1 = centre.clone().add(bras.clone().applyAxisAngle(n, 37 * Math.PI / 180));
      fire("pointermove", { pointerId: 4, ...px(R1), shiftKey: false });
      r.tournee = rotationDe(api, 1) - rot0;
      const R2 = centre.clone().add(bras.clone().applyAxisAngle(n, 42 * Math.PI / 180));
      fire("pointermove", { pointerId: 4, ...px(R2), shiftKey: true });
      r.tourneeMaj = rotationDe(api, 1) - rot0;
      r.centreApres = empreinteDe(api, 1);
      fire("pointerup", { pointerId: 4, button: 0, ...px(R2) });
      r.notes = notes;
      /* LE RAYON NE RESPIRE PAS : le meme a 0 deg, a 45 deg et a 90 deg */
      poserAngle(api, 1, 0);
      const r0 = marquerPiece(api, 1).rayon;
      poserAngle(api, 1, 45);
      const r45 = marquerPiece(api, 1).rayon;
      poserAngle(api, 1, 90);
      const r90 = marquerPiece(api, 1).rayon;
      const emp45 = (poserAngle(api, 1, 45), empreinteDe(api, 1));
      r.rayons = { r0, r45, r90, diagonaleCourante45: Math.hypot(emp45.l, emp45.p) / 2 };
      /* UNE PIECE MASQUEE PAR L'OEIL ne se saisit pas : sous le pointeur, au
         centre de la piece 1 masquee, il n'y a plus rien — on ne deplace pas
         ce qu'on ne voit pas. Et le poser ne coupe plus l'orbite. */
      /* Le pixel vise le CENTRE MONDE du maillage — toujours dans la boite —
         et non le haut-centre de son AABB, qui n'est pas sur une boite
         inclinee sous l'enveloppe : a ce pixel-la, le rayon ne touchait rien,
         masquee ou pas, et l'assertion etait vide (mutation verte). Le temoin :
         visible, le meme pixel rend la piece 1. */
      const cible1 = pieces[1].children[0].getWorldPosition(new THREE.Vector3());
      const p2 = px(cible1);
      const ndc2 = { x: (p2.clientX / 860) * 2 - 1, y: -((p2.clientY / 824) * 2 - 1) };
      r.visibleSous = sousLePointeur(api, ndc2);
      montrerPiece(api, 1, false);
      r.masqueeSous = sousLePointeur(api, ndc2);
      marquerPiece(api, null);
      fire("pointerdown", { button: 0, pointerId: 5, ...p2, shiftKey: false });
      r.masqueePoser = { enabled: api.controls.enabled };
      fire("pointerup", { pointerId: 5, button: 0, ...p2 });
      montrerPiece(api, 1, true);
      console.log(JSON.stringify(r));
    """))
    g = sortie["g"]
    # L'ANNEAU : sous le pointeur c'est la poignée, et 37° demandés par
    # three.js font 37° au module — le sens est le bon, sur cet axe-là
    assert sortie["sousAnneau"] == {"quoi": "poignee", "cle": 1}
    assert abs(sortie["tournee"] - 37) < 1e-6, sortie["tournee"]
    assert sortie["tourneeMaj"] == 40, sortie["tourneeMaj"]     # 42 arrondi au pas de 5
    assert sortie["pasRotation"] == 5
    # …et la rotation n'a pas déplacé le centre de la pièce
    assert abs(sortie["centreApres"]["cu"] - sortie["centreAvant"]["cu"]) < 1e-9
    assert abs(sortie["centreApres"]["cv"] - sortie["centreAvant"]["cv"]) < 1e-9
    assert sortie["notes"] == 2                       # deux rotations
    # LE RAYON NE RESPIRE PAS : identique à 0°, 45° et 90°, alors que
    # l'empreinte courante à 45° en diffère de plus de 5 % (mesuré : 0,928 → 0,749 avant correctif)
    r_ = sortie["rayons"]
    assert r_["r0"] == r_["r45"] == r_["r90"], r_
    assert abs(r_["diagonaleCourante45"] - r_["r0"] / 1.15) > 0.05 * r_["r0"] / 1.15, r_
    # UNE PIÈCE MASQUÉE PAR L'ŒIL ne se saisit pas, et le poser sur elle ne
    # coupe pas l'orbite : le raycast de three.js ne saute PAS les objets
    # invisibles (mesuré dans le fichier vendorisé : seul `layers` est testé),
    # c'est le module qui filtre.
    assert sortie["visibleSous"] == {"quoi": "piece", "cle": 1}, sortie["visibleSous"]
    assert sortie["masqueeSous"] is None, sortie["masqueeSous"]
    assert sortie["masqueePoser"] == {"enabled": True}
    # ── UN CLIC SUR L'ANNEAU NE RELÂCHE PAS : le geste en cours est visible du
    # sélecteur, qui ne raycaste qu'`api.racine` et prendrait l'anneau pour
    # le vide ────────────────────────────────────────────────────────────────
    code = _code("etabli/etabli.js")
    clic = code.split("designerAuClic(S.vueA", 1)[1]
    assert clic.index('if (_gestePlaque && _gestePlaque.quoi === "poignee") return;') \
        < clic.index("pieceCourante(null)")
    gl = _fonction_etabli("glisserSurPlaque")
    assert "_gestePlaque = geste;" in gl and "_gestePlaque = null;" in gl
    # ── ET L'ŒIL QUI MASQUE LA PIÈCE COURANTE LA RELÂCHE ────────────────────
    oeil = code.split('querySelectorAll(".plaque-oeil")', 1)[1] \
               .split('querySelectorAll(".plaque-rang")', 1)[0]
    assert "if (!masquee && cle === PLQ.courante) {" in oeil
    assert "PLQ.courante = null;" in oeil and "marquerPiece(S.vueA, null);" in oeil


def test_les_FLECHES_avancent_d_un_pas_de_PLATEAU_suivent_l_ECRAN_et_ne_volent_pas_les_CHAMPS():
    """Flèches = un pas, Alt = pas fin (÷10), Ctrl = ×10 — et le pas est celui
    du PLATEAU, jamais celui de la vue : la scène est zoomée pour que les deux
    diffèrent, et c'est le pas du plateau qu'on retrouve dans le déplacement
    monde. Les flèches suivent l'ÉCRAN : après →, la pièce projetée par la
    vraie caméra a une abscisse écran plus grande ; après ↑, une ordonnée plus
    grande — sous deux points de vue, dont une orbite quelconque que le nom de
    la dernière vue ne décrit pas.

    ET LE CLAVIER N'EST PAS VOLÉ AUX CHAMPS : une flèche dont la cible est un
    input, un textarea, un select ou un contenteditable ne bouge rien et ne
    fait pas de preventDefault — la taille cible et la rotation se tapent
    encore.
    """
    sortie = json.loads(_node_trois(
        "cadrer, majRepere, orienter",
        _importer_plaque("etaler, plateauDe, empreinteDe, axesEcran, deplacerPiece, "
                         "marquerPiece") + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      etaler(api); racine.updateMatrixWorld(true);
      const g = plateauDe(api);
      api.camera.zoom = 16; api.camera.updateProjectionMatrix();
      const pasVue = majRepere(api).pas;
      const PLQ = { active: true, courante: 1 };
      const S = { vueA: api };
      let notes = 0, empeches = 0;
      const noterPlan = () => { notes++; };
    """ + _fonction_etabli("toucheClavierPlaque") + """
      const ev = (key, cible, mods) => ({ key, target: cible, altKey: false, ctrlKey: false,
        ...(mods || {}), preventDefault() { empeches++; } });
      const centre = () => { const e = empreinteDe(api, 1); const w = new THREE.Vector3();
        w[g.u] = e.cu; w[g.v] = e.cv; return w; };
      const ecran = (w) => { const q = w.clone().project(api.camera); return [q.x, q.y]; };
      const essai = (key, cible, mods) => {
        const avant = centre(); const eAvant = ecran(avant);
        const pris = toucheClavierPlaque(ev(key, cible, mods));
        racine.updateMatrixWorld(true);
        const apres = centre();
        return { pris, dist: avant.distanceTo(apres),
                 dAxe: apres[g.axe] - avant[g.axe],
                 dx: ecran(apres)[0] - eAvant[0], dy: ecran(apres)[1] - eAvant[1] };
      };
      const canvas = { tagName: "CANVAS" };
      const r = { g, pasVue };
      r.champs = ["INPUT", "TEXTAREA", "SELECT"].map((t) => essai("ArrowRight", { tagName: t }));
      r.editable = essai("ArrowRight", { tagName: "DIV", isContentEditable: true });
      r.autreTouche = essai("Enter", canvas);
      r.libre = { droite: essai("ArrowRight", canvas), gauche: essai("ArrowLeft", canvas),
                  haut: essai("ArrowUp", canvas), bas: essai("ArrowDown", canvas),
                  fin: essai("ArrowRight", canvas, { altKey: true }),
                  gros: essai("ArrowUp", canvas, { ctrlKey: true }) };
      /* une orbite QUELCONQUE, que le nom de la derniere vue ne decrit pas */
      api.camera.position.set(api.controls.target.x - 5, api.controls.target.y + 2.5,
                              api.controls.target.z - 7);
      api.camera.lookAt(api.controls.target);
      api.camera.updateMatrixWorld(true);
      r.orbite = { droite: essai("ArrowRight", canvas), haut: essai("ArrowUp", canvas) };
      PLQ.active = false;
      r.horsPlaque = essai("ArrowRight", canvas);
      r.notes = notes; r.empeches = empeches;
      console.log(JSON.stringify(r));
    """))
    g, pas = sortie["g"], sortie["g"]["pas"]
    # le pas de vue et le pas de plateau DIFFÈRENT sur cette scène : c'est ce
    # qui rend la mesure discriminante
    assert abs(sortie["pasVue"] - pas) > 1e-9, (sortie["pasVue"], pas)
    # LES CHAMPS gardent leurs flèches
    for r in sortie["champs"] + [sortie["editable"], sortie["autreTouche"],
                                 sortie["horsPlaque"]]:
        assert r["pris"] is False and r["dist"] == 0, r
    # UN PAS DE PLATEAU par flèche, dans le plan, et vers la droite / le haut
    # DE L'ÉCRAN
    for vue in ("libre", "orbite"):
        d = sortie[vue]["droite"]
        assert d["pris"] is True and abs(d["dist"] - pas) < 1e-9, (vue, d)
        assert abs(d["dAxe"]) < 1e-12 and d["dx"] > 1e-4, (vue, d)
        h = sortie[vue]["haut"]
        assert h["pris"] is True and abs(h["dist"] - pas) < 1e-9, (vue, h)
        assert abs(h["dAxe"]) < 1e-12 and h["dy"] > 1e-4, (vue, h)
    gauche, bas = sortie["libre"]["gauche"], sortie["libre"]["bas"]
    assert gauche["dx"] < -1e-4 and abs(gauche["dist"] - pas) < 1e-9, gauche
    assert bas["dy"] < -1e-4 and abs(bas["dist"] - pas) < 1e-9, bas
    # Alt = un dixième, Ctrl = dix fois
    assert abs(sortie["libre"]["fin"]["dist"] - pas / 10) < 1e-9, sortie["libre"]["fin"]
    assert abs(sortie["libre"]["gros"]["dist"] - 10 * pas) < 1e-9, sortie["libre"]["gros"]
    # le plan est noté à chaque geste pris, et le défilement de la page est
    # empêché autant de fois — pas une de plus (les champs, jamais)
    assert sortie["notes"] == 8 and sortie["empeches"] == 8, sortie
    # ── LA PURE axesEcran, sur des matrices écrites à la main ───────────────
    # Colonnes de camera.matrixWorld : la première est la droite d'écran, la
    # deuxième le haut. Une caméra qui regarde le plateau PAR LA TRANCHE (droite
    # et haut projetés sur le même axe du plan) ne peut pas donner deux flèches
    # à la même direction : le haut prend l'autre axe.
    pur = json.loads(_node(
        _constantes_plaque("AXES") + _fonction_plaque("axesEcran") + """
      const M = (droite, haut) => [droite[0], droite[1], droite[2], 0,
                                   haut[0], haut[1], haut[2], 0,
                                   0, 0, 1, 0, 0, 0, 0, 1];
      console.log(JSON.stringify({
        face: axesEcran(M([1, 0, 0], [0, 1, 0]), "z"),
        dessus: axesEcran(M([1, 0, 0], [0, 0, -1]), "y"),
        profil: axesEcran(M([0, 0, -1], [0, 1, 0]), "x"),
        tranche: axesEcran(M([0.6, 0, 0.8], [0.8, 0, -0.6]), "z"),
        oblique: axesEcran(M([0.3, 0, -0.95], [-0.2, 0.95, 0.24]), "y"),
      }));
    """))
    assert pur["face"] == {"droite": {"axe": "x", "signe": 1}, "haut": {"axe": "y", "signe": 1}}
    assert pur["dessus"] == {"droite": {"axe": "x", "signe": 1}, "haut": {"axe": "z", "signe": -1}}
    assert pur["profil"] == {"droite": {"axe": "z", "signe": -1}, "haut": {"axe": "y", "signe": 1}}
    assert pur["tranche"]["droite"]["axe"] == "x" and pur["tranche"]["haut"]["axe"] == "y", pur
    assert pur["oblique"] == {"droite": {"axe": "z", "signe": -1}, "haut": {"axe": "x", "signe": -1}}, pur
    # ── et la page n'y lit JAMAIS le pas de vue ─────────────────────────────
    fn = _fonction_etabli("toucheClavierPlaque")
    assert "REP.pas" not in fn and "REP." not in fn
    assert "plateauDe(S.vueA)" in fn and ".pas" in fn
    assert 'document.addEventListener("keydown", toucheClavierPlaque);' \
        in _code("etabli/etabli.js")


def _poster_plan(c, corps):
    return c.post("/api/etabli/plaque", json=corps)


def _plan_valide(job, version, **extra):
    corps = {"job": job, "version": version, "axe": "z", "pas": 0.02,
             "pieces": [{"index": 0, "dx": 0.0126, "dy": -0.0473, "rot": 90},
                        {"index": 3, "dx": -0.001, "dy": 0.0, "rot": -15.5}]}
    corps.update(extra)
    return corps


def test_le_PLAN_DE_PLAQUE_est_ecrit_par_PYTHON_relu_et_le_MAILLAGE_ne_bouge_pas():
    """LA DÉCISION DE STRUCTURE DU LOT, FRAPPÉE : le navigateur compose, PYTHON
    écrit `plaque.v<N>.json` à côté du .glb, et une route le relit. Le
    maillage NE BOUGE PAS — sha256 de model.glb et de model.v2.glb avant et
    après, registre compris : ranger des pièces n'est pas une version.

    Les gardes, dans l'ordre où elles mordent, chacune frappée : version non
    entière (un 2.0 de JSON est un flottant), nom de job dégénéré (refusé, pas
    aplati — la leçon de la vignette, par la MÊME fonction), version absente
    du disque (un plan sans maillage ne dit rien, et c'est ce qui empêche de
    fabriquer un dossier à volonté), axe hors x|y|z, pas ≤ 0 ou non numérique
    (un booléen est un entier pour Python : refusé quand même), pièces non
    liste, index non entier ou négatif ou en double, dx/dy/rot non finis.
    Rien n'est écrit tant qu'une garde mord. Écriture ATOMIQUE, lue en AST
    comme celle de la vignette.
    """
    import ast
    import hashlib
    import inspect
    from app.api import routes
    from app.config import settings
    from app.services import mesh_edit
    d = _job("plan_plaque")
    mesh_edit.ecrire_version("plan_plaque", _glb_de_banc(),
                             operation="reparer", detail={})
    sha = lambda p_: hashlib.sha256(p_.read_bytes()).hexdigest()
    avant = {n: sha(d / n) for n in ("model.glb", "model.v2.glb", "report.json")}
    c = _client()

    # ── LE CAS NOMINAL : écrit, relu, et le maillage n'a pas bougé ──────────
    r = _poster_plan(c, _plan_valide("plan_plaque", 2))
    assert r.status_code == 200, r.text
    assert r.json() == {"ok": True, "fichier": "plaque.v2.json", "pieces": 2}
    p = d / "plaque.v2.json"
    assert p.is_file()
    doc = json.loads(p.read_text(encoding="utf-8"))
    assert doc == {"format": "plaque/1", "job": "plan_plaque", "version": 2,
                   "axe": "z", "pas": 0.02, "unites": "modele", "repere": "monde",
                   "pieces": [{"index": 0, "dx": 0.0126, "dy": -0.0473, "rot": 90.0},
                              {"index": 3, "dx": -0.001, "dy": 0.0, "rot": -15.5}]}
    assert not (d / "plaque.v2.json.tmp").exists()
    assert {n: sha(d / n) for n in avant} == avant       # LE MAILLAGE N'A PAS BOUGÉ
    assert not (d / "model.v3.glb").exists()               # …et aucune version n'est née
    g = c.get("/api/etabli/plaque", params={"job": "plan_plaque", "version": 2})
    assert g.status_code == 200 and g.json() == doc
    # une version sans plan : 404 franc, le cas ordinaire — et une version
    # qui n'est le numéro de rien : 400, à la lecture comme à l'écriture
    assert c.get("/api/etabli/plaque",
                 params={"job": "plan_plaque", "version": 1}).status_code == 404
    assert c.get("/api/etabli/plaque",
                 params={"job": "plan_plaque", "version": 0}).status_code == 400
    assert c.get("/api/etabli/plaque",
                 params={"job": "plan_plaque", "version": -2}).status_code == 400
    # le plan se RÉÉCRIT (une retouche de plus), en place
    r = _poster_plan(c, _plan_valide("plan_plaque", 2, pieces=[{"index": 5}]))
    assert r.status_code == 200, r.text
    assert json.loads(p.read_text(encoding="utf-8"))["pieces"] == \
        [{"index": 5, "dx": 0.0, "dy": 0.0, "rot": 0.0}]
    # les valeurs absentes valent zéro, un index seul suffit
    # ── LES GARDES, chacune frappée ─────────────────────────────────────────
    refus = [
        ("version 2.0", _plan_valide("plan_plaque", 2.0), 400),
        ("version '2'", _plan_valide("plan_plaque", "2"), 400),
        ("version 0", _plan_valide("plan_plaque", 0), 400),
        ("version True", _plan_valide("plan_plaque", True), 400),
        ("version absente", {k: v for k, v in _plan_valide("plan_plaque", 2).items()
                             if k != "version"}, 400),
        ("version 9 absente du disque", _plan_valide("plan_plaque", 9), 404),
        ("job inconnu", _plan_valide("nexiste_pas_plan", 1), 404),
        ("job absent", {k: v for k, v in _plan_valide("plan_plaque", 2).items()
                        if k != "job"}, 400),
        ("job entier", _plan_valide(123, 2), 400),
        ("job ..", _plan_valide("..", 1), 400),
        ("job a/..", _plan_valide("a/..", 1), 400),
        ("job vide", _plan_valide("", 1), 400),
        ("axe w", _plan_valide("plan_plaque", 2, axe="w"), 400),
        ("axe absent", {k: v for k, v in _plan_valide("plan_plaque", 2).items()
                        if k != "axe"}, 400),
        ("pas 0", _plan_valide("plan_plaque", 2, pas=0), 400),
        ("pas -1", _plan_valide("plan_plaque", 2, pas=-1), 400),
        ("pas '0.02'", _plan_valide("plan_plaque", 2, pas="0.02"), 400),
        ("pas True", _plan_valide("plan_plaque", 2, pas=True), 400),
        ("pieces dict", _plan_valide("plan_plaque", 2, pieces={}), 400),
        ("piece non objet", _plan_valide("plan_plaque", 2, pieces=[3]), 400),
        ("index -1", _plan_valide("plan_plaque", 2, pieces=[{"index": -1}]), 400),
        ("index 1.5", _plan_valide("plan_plaque", 2, pieces=[{"index": 1.5}]), 400),
        ("index '3'", _plan_valide("plan_plaque", 2, pieces=[{"index": "3"}]), 400),
        ("index True", _plan_valide("plan_plaque", 2, pieces=[{"index": True}]), 400),
        ("index absent", _plan_valide("plan_plaque", 2, pieces=[{"dx": 1}]), 400),
        ("index en double", _plan_valide("plan_plaque", 2,
                                         pieces=[{"index": 2}, {"index": 2}]), 400),
        ("dx 'a'", _plan_valide("plan_plaque", 2, pieces=[{"index": 0, "dx": "a"}]), 400),
        ("rot True", _plan_valide("plan_plaque", 2, pieces=[{"index": 0, "rot": True}]), 400),
    ]
    temoin = p.read_text(encoding="utf-8")
    for nom, corps, statut in refus:
        r = _poster_plan(c, corps)
        assert r.status_code == statut, (nom, r.status_code, r.text[:200])
        assert "plan de plaque" in r.text, (nom, r.text[:200])
    for nom in ("..", "a/..", ""):
        r = _poster_plan(c, _plan_valide(nom, 1))
        assert "nom de job" in r.text, (nom, r.text[:200])
    # RIEN N'A ÉTÉ ÉCRIT par un refus : le plan en place est le témoin, et
    # aucun fichier n'est né au-dessus du dossier des jobs
    assert p.read_text(encoding="utf-8") == temoin
    assert not list(settings.outputs_path.glob("plaque*.json"))
    assert not list((settings.outputs_path / "assets3d").glob("plaque*.json"))
    # un job traversant se réduit au NOM, comme pour la vignette
    _job("evade_plan")
    r = _poster_plan(c, _plan_valide("../../evade_plan", 1))
    assert r.status_code == 200, r.text
    assert (settings.outputs_path / "assets3d" / "evade_plan" / "plaque.v1.json").is_file()
    assert not (settings.outputs_path / "plaque.v1.json").exists()
    # la lecture franchit la MÊME porte que l'écriture
    assert c.get("/api/etabli/plaque",
                 params={"job": "..", "version": 1}).status_code == 400
    # ── LES DEUX ROUTES DU RÉSEAU PASSENT PAR LES MÊMES GARDES ──────────────
    for fn in (routes._etabli_vignette_cible, routes._etabli_plaque_cible):
        arbre = ast.parse(inspect.getsource(fn).lstrip())
        appels = {ast.unparse(n.func) for n in ast.walk(arbre) if isinstance(n, ast.Call)}
        assert "_etabli_cible_sous_jobs" in appels, (fn.__name__, appels)
    garde = inspect.getsource(routes._etabli_cible_sous_jobs)
    assert '("", ".", "..")' in garde and ".resolve().parents" in garde
    # ── L'ÉCRITURE EST ATOMIQUE, en AST comme pour la vignette ──────────────
    src = inspect.getsource(routes.etabli_plaque_ecrire)
    arbre = ast.parse(src)
    appels = {ast.unparse(n.func) for n in ast.walk(arbre) if isinstance(n, ast.Call)}
    assert "tmp.write_text" in appels and "tmp.replace" in appels, appels
    assert "p.write_text" not in appels and "p.write_bytes" not in appels, appels
    # …et `tmp` est un AUTRE chemin que `p` : un `tmp = p` garderait les deux
    # noms et perdrait l'atomicité
    affectations = {ast.unparse(n.targets[0]): ast.unparse(n.value)
                    for n in ast.walk(arbre) if isinstance(n, ast.Assign)
                    and len(n.targets) == 1}
    assert affectations.get("tmp") == "d / f\'{p.name}.tmp\'", affectations.get("tmp")


def test_le_plan_part_a_la_PREMIERE_RETOUCHE_jamais_a_l_etalement_et_n_entre_pas_dans_la_FILE():
    """« On n'écrit pas un fichier pour avoir regardé » : le plan part à la
    première RETOUCHE — glisser, flèche, rotation — jamais à l'étalement
    automatique. Il est RELU avant d'étaler (et le modèle capturé avant
    l'attente), envoyé COALESCÉ (une minuterie, pas une requête par pixel), la
    charge capturée AU GESTE — job et version compris — pour qu'un changement
    de modèle pendant l'attente ne fasse pas partir le plan sous un autre nom.
    Le dernier geste part au rangement. Et RIEN n'entre dans `S.enAttente`.

    La coalescence est EXÉCUTÉE sur les vraies noterPlan/envoyerPlan, avec
    une minuterie factice et un jpost qui enregistre.
    """
    js, code = _lire("etabli/etabli.js"), _code("etabli/etabli.js")
    # LES TROIS SITES DE RETOUCHE, et aucun autre : le compte est rigide
    assert code.count("noterPlan();") == 3, code.count("noterPlan();")
    for fn in ("glisserSurPlaque", "toucheClavierPlaque", "poserRotation"):
        assert "noterPlan();" in _fonction_etabli(fn), fn
    assert "noterPlan(" not in _plaque_bloc()
    # RELU AVANT D'ÉTALER, le modèle capturé avant l'attente, la garde après
    bp = code.split("function basculerPlaque()", 1)[1].split("\n}\n", 1)[0]
    assert bp.index("const cible = S.a;") < bp.index("plan = await lirePlan(cible);") \
        < bp.index("if (S.a !== cible || !S.vueA.racine) return;") \
        < bp.index("etaler(S.vueA, plan)")
    lp = _fonction_etabli_async("lirePlan")
    assert "if (r.status === 404) return null;" in lp
    assert "if (!cible || !cible.job || !cible.version) return null;" in lp
    # LE DERNIER GESTE PART AU RANGEMENT, avant que ranger() ne défasse ce
    # qu'il décrit
    ob = code.split("function oublierPlaque()", 1)[1].split("\n}\n", 1)[0]
    assert ob.index("envoyerPlan();") < ob.index("ranger(S.vueA);")
    # RIEN DANS LA FILE : la section entière du plan et du déplacement
    section = code.split("const ROUTE_PLAQUE =", 1)[1] \
                  .split('document.addEventListener("keydown"', 1)[0]
    for interdit in ("S.enAttente", "noterAttente", "ROUTES[", "GLTFExporter"):
        assert interdit not in section, interdit
    assert "jpost(ROUTE_PLAQUE, corps)" in section
    assert "PLQ.aEnvoyer = { job: S.a.job, version: S.a.version, ...plan };" in section
    # ── LA COALESCENCE, EXÉCUTÉE ────────────────────────────────────────────
    sortie = json.loads(_node_trois(
        "cadrer",
        _importer_plaque("etaler, dispositionDe")
        + _constantes_etabli("ROUTE_PLAQUE", "DELAI_PLAN_MS") + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      etaler(api);
      const PLQ = { active: true, aEnvoyer: null, sauvegarde: null };
      const S = { vueA: api, a: { job: "premier", version: 2 } };
      const minuteries = [];
      const setTimeout = (f, ms) => { minuteries.push({ f, ms }); return minuteries.length; };
      const clearTimeout = () => {};
      const envois = [];
      let rejeter = false;
      const jpost = async (route, corps) => {
        envois.push({ route, corps });
        if (globalThis.__jpost) return globalThis.__jpost(route, corps);
        if (rejeter) throw new Error("disque plein");
        return {};
      };
      const refus = [];
      const direRefus = (m) => refus.push(m);
      const rendreEtatPlan = () => {};
      let _envoiPlan = 0;
      let _envoiChaine = Promise.resolve();
      let _envoisEnVol = 0;
    """ + _fonction_etabli("noterPlan") + "\n"
        + _fonction_etabli_async("envoyerPlan") + """
      for (let i = 0; i < 100; i++) noterPlan();
      const programmees = minuteries.length;
      /* le modele change PENDANT l'attente : la charge capturee ne change pas */
      S.a = { job: "second", version: 7 };
      await minuteries[0].f();
      const premier = envois.map((e) => ({ route: e.route, job: e.corps.job,
        version: e.corps.version, axe: e.corps.axe, pas: e.corps.pas,
        pieces: e.corps.pieces.length, cles: Object.keys(e.corps).sort() }));
      const etat1 = { sauvegarde: PLQ.sauvegarde, aEnvoyer: PLQ.aEnvoyer, envoi: _envoiPlan };
      /* un refus du serveur se DIT */
      rejeter = true;
      noterPlan();
      await minuteries[minuteries.length - 1].f();
      const etat2 = { sauvegarde: PLQ.sauvegarde, refus };
      /* une etape sans version : impossible, et rien ne part */
      rejeter = false;
      S.a = { job: null, meshy: "t1", version: null };
      const avant = envois.length;
      noterPlan();
      const etat3 = { sauvegarde: PLQ.sauvegarde, minuteries: minuteries.length, envois: envois.length - avant };
      /* hors plaque : rien */
      PLQ.active = false; S.a = { job: "x", version: 1 };
      noterPlan();
      const apresHorsPlaque = minuteries.length;
      /* LES ENVOIS SE SUIVENT : un premier POST lent, un second immediat — le
         second attend le premier, et le compte en vol redescend a zero. */
      PLQ.active = true; S.a = { job: "chaine", version: 3 };
      const journal = [];
      let lent = true;
      const jpostLent = jpost;
      const jpostJournal = async (route, corps) => {
        journal.push(["debut", corps.version, _envoisEnVol]);
        if (lent) { lent = false; for (let i = 0; i < 50; i++) await Promise.resolve(); }
        journal.push(["fin", corps.version, _envoisEnVol]);
        return {};
      };
      /* jpost est lu par son nom dans envoyerPlan : on le redirige. */
      const jpostOriginal = jpost;
      globalThis.__jpost = jpostJournal;
      noterPlan();
      const t1 = envoyerPlan();
      S.a = { job: "chaine", version: 4 };
      noterPlan();
      const t2 = envoyerPlan();
      await Promise.all([t1, t2]);
      console.log(JSON.stringify({ programmees, delai: minuteries[0].ms, premier, etat1, etat2, etat3,
        apresHorsPlaque, DELAI_PLAN_MS, journal, enVolApres: _envoisEnVol,
        envoisChaine: envois.slice(-2).map((e) => e.corps.version) }));
    """))
    assert sortie["programmees"] == 1, sortie            # cent retouches, une minuterie
    assert sortie["delai"] == sortie["DELAI_PLAN_MS"]
    assert sortie["premier"] == [{"route": "/api/etabli/plaque", "job": "premier",
                                  "version": 2, "axe": "y", "pas": 0.2, "pieces": 3,
                                  "cles": ["axe", "job", "pas", "pieces", "version"]}], \
        sortie["premier"]
    assert sortie["etat1"] == {"sauvegarde": "ok", "aEnvoyer": None, "envoi": 0}
    assert sortie["etat2"]["sauvegarde"] == "refus"
    assert len(sortie["etat2"]["refus"]) == 1 and "disque plein" in sortie["etat2"]["refus"][0]
    assert sortie["etat3"] == {"sauvegarde": "impossible", "minuteries": 2, "envois": 0}
    assert sortie["apresHorsPlaque"] == 2
    # LES ENVOIS SE SUIVENT : le second POST ne commence qu'après la fin du
    # premier (deux POST coalescés qui se croiseraient laisseraient sur le
    # disque l'avant-dernier plan), et le compte en vol redescend à zéro
    assert [j[0] for j in sortie["journal"]] == ["debut", "fin", "debut", "fin"], sortie["journal"]
    assert [j[1] for j in sortie["journal"]] == [3, 3, 4, 4], sortie["journal"]
    assert sortie["journal"][0][2] >= 1 and sortie["enVolApres"] == 0, sortie
    assert sortie["envoisChaine"] == [3, 4]
    # ── LE PLAN NE SE PERD PAS À LA SORTIE DE LA PAGE ───────────────────────
    # Un glisser puis « ← 3D Studio » dans la fenêtre de coalescence : la
    # minuterie mourrait avec la page. Le bouton fait partir la charge et
    # REFUSE le temps qu'elle arrive — la règle de la file, appliquée au plan
    # — AVANT même la garde de la file, et avant la navigation.
    depart = code.split('$("#btnRetour").addEventListener', 1)[1].split("\n});\n", 1)[0]
    assert "if (_envoiPlan || PLQ.aEnvoyer || _envoisEnVol) {" in depart
    garde = depart.split("if (_envoiPlan || PLQ.aEnvoyer || _envoisEnVol) {", 1)[1] \
                  .split("  }", 1)[0]
    assert "envoyerPlan();" in garde and "direRefus(" in garde and "return;" in garde
    assert depart.index("_envoisEnVol") < depart.index("if (S.enAttente.length) {") \
        < depart.index("location.href")
    # …et les déchargements que le bouton ne voit pas (le hub qui remplace
    # l'iframe, un onglet fermé) : la charge pendante part en `keepalive`, la
    # seule requête que le navigateur laisse finir après le déchargement
    cache = code.split('window.addEventListener("pagehide"', 1)[1].split("\n});\n", 1)[0]
    assert "keepalive: true" in cache and "JSON.stringify(corps)" in cache
    assert "ROUTE_PLAQUE" in cache and "jpost(" not in cache
    assert "const corps = PLQ.aEnvoyer;" in cache and "PLQ.aEnvoyer = null;" in cache


def test_sur_la_plaque_le_rail_annonce_le_PAS_DU_PLATEAU_et_les_regles_portent_la_MEME_unite():
    """Le rail dit « pas de la grille » : sur la plaque, la grille visible est
    celle du PLATEAU (le repère est éteint), et c'est donc son pas qu'il
    annonce — le même que les flèches avancent. Et les règles dessinées sur
    les bords portent la même unité que le rail : sans cible, des unités
    glTF ; une cible posée, des millimètres — par fmtMesure, le seul
    formateur, et par uniteCourante, la seule unité. On lit le balisage du
    rail ET les textes écrits sur les bandes.
    """
    sortie = json.loads(_node_trois(
        "echelleMm, marquerAuRepere, majRepere, cadrer, dessinerRegles",
        _importer_plaque("etaler, ranger, boiteModele, plateauDe")
        + _faux_rail() + _constantes_etabli("LIGNES_REPERE")
        + _fonction_etabli("enMillimetres") + "\n"
        + _fonction_etabli("uniteCourante") + "\n"
        + _fonction_etabli("fmtMesure") + "\n"
        + _fonction_etabli("plusGrandeDimension") + "\n"
        + _fonction_etabli("mesurerRetenus") + "\n"
        + _fonction_etabli("rendreRepere") + "\n"
        + _fonction_etabli("rendreCible") + "\n"
        + _fonction_etabli("poserCible") + "\n"
        + _fonction_etabli("graduerPlateau") + "\n"
        + _fonction_etabli("lireRepere") + "\n" + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      S.vueA = api;
      const boite = new THREE.Box3().setFromObject(racine);
      S.geoA = { taille: boite.getSize(new THREE.Vector3()) };
      REP.pas = majRepere(api).pas;
      rendreRepere();
      const echelle = () => zones["#repereEchelle"].innerHTML;
      const textes = () => { const r = api.scene.children.find((o) => o.name === "lib3d-regles");
        return r ? r.children[1].material.map.image.appels.map((a) => a.texte) : null; };
      lireRepere();
      const r = { horsPlaque: echelle(), reglesHors: textes(), pasVue: REP.pas };
      const et = etaler(api);
      PLQ.active = true; PLQ.pieces = et.pieces; PLQ.pas = et.plateau.pas;
      lireRepere();
      r.plateau = plateauDe(api);
      r.surPlaque = echelle();
      r.reglesGltf = textes();
      r.pose = poserCible("63");
      r.echelle = REP.echelle;
      r.surPlaqueMm = echelle();
      r.reglesMm = textes();
      poserCible("");
      ranger(api);
      PLQ.active = false; PLQ.pieces = []; PLQ.pas = null;
      lireRepere();
      r.apres = { echelle: echelle(), regles: textes() };
      console.log(JSON.stringify(r));
    """))
    pas_plateau = sortie["plateau"]["pas"]
    assert abs(sortie["pasVue"] - pas_plateau) > 1e-9, (sortie["pasVue"], pas_plateau)
    # hors plaque : le pas de VUE, « de la grille », et aucune règle
    assert "pas de la grille" in sortie["horsPlaque"]
    assert sortie["reglesHors"] is None
    # sur la plaque : le pas DU PLATEAU, en unités glTF, et les règles aussi
    assert "pas du plateau" in sortie["surPlaque"], sortie["surPlaque"]
    assert "u. glTF" in sortie["surPlaque"]
    assert "aucune taille cible" in sortie["surPlaque"]
    pas_lu = _nombre_fr(re.search(r"<b>([^<]*) u\. glTF</b>", sortie["surPlaque"]).group(1))
    assert abs(pas_lu - pas_plateau) < 5e-4, (pas_lu, pas_plateau)
    regles = sortie["reglesGltf"]
    assert regles[-1] == "u. glTF", regles
    assert abs(_nombre_fr(regles[1]) - 2 * pas_plateau) < 5e-4, regles  # un libellé sur deux
    # une cible posée : le rail ET les règles passent en millimètres, par la
    # même échelle
    assert sortie["pose"] is True
    assert " mm</b>" in sortie["surPlaqueMm"] and "cible 63 mm" in sortie["surPlaqueMm"]
    mm = sortie["reglesMm"]
    assert mm[-1] == "mm", mm
    assert abs(_nombre_fr(mm[1]) - 2 * pas_plateau * sortie["echelle"]) < 5e-3, \
        (mm, pas_plateau, sortie["echelle"])
    assert len(mm) == len(regles)
    # de retour à l'Assemblé : le pas de vue, et plus de règles
    assert "pas de la grille" in sortie["apres"]["echelle"]
    assert sortie["apres"]["regles"] is None


def test_la_LECTURE_du_rail_reste_celle_du_MODELE_pour_une_piece_TOURNEE_et_ASYMETRIQUE():
    """LE CHIFFRE FAUX AVEC ASSURANCE, ET LA QUATRIÈME FOIS QUE DES DONNÉES
    TROP SYMÉTRIQUES LE CACHAIENT. La page lisait « centre de la boîte monde −
    décalage » : juste en translation, faux dès qu'une pièce NON SYMÉTRIQUE
    tourne — la rotation se fait autour du centre de la boîte assemblée, et la
    boîte d'une pièce tournée n'a plus le même centre. Sonde de la revue : une
    pièce en L large de 1,2, écart 0 avant rotation, 0,241 après 37°, et aucun
    †. Sur une boîte : 1e-16 — d'où un banc vert sur une scène de boîtes.

    On lit donc la BOÎTE DANS LA POSE ASSEMBLÉE (boiteModele), recomposée
    maillage par maillage par W⁻¹ ; exacte pour la pièce comme pour l'un de
    ses maillages (la granularité « maillage » du panneau, la plus courante).
    Le second chemin est la boîte mesurée AVANT tout étalement, et le témoin
    est la lecture naïve, qui doit être FAUSSE ici — sinon la scène est encore
    trop symétrique. Puis le RAIL lui-même, sur le vrai lireRepere.
    """
    sortie = json.loads(_node_trois(
        "cadrer",
        _importer_plaque("etaler, ranger, boiteModele, decalageEtalement, poserAngle, "
                         "deplacerPiece") + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      const boite = (o) => new THREE.Box3().setFromObject(o);
      const centre = (o) => boite(o).getCenter(new THREE.Vector3()).toArray();
      const L = pieces[2], aile = L.children[1], boiteSeule = L.children[0];
      const assemble = { L: centre(L), aile: centre(aile), boite: centre(boiteSeule),
                         piece1: centre(pieces[1]) };
      const tailleL = boite(L).getSize(new THREE.Vector3()).toArray();
      etaler(api); racine.updateMatrixWorld(true);
      poserAngle(api, 2, 37);
      deplacerPiece(api, 2, 0.31, -0.17);
      poserAngle(api, 1, 37);
      racine.updateMatrixWorld(true);
      const lu = (o) => { const b = boiteModele(api, o);
        return { c: b.boite.getCenter(new THREE.Vector3()).toArray(), etale: b.etale,
                 vide: b.boite.isEmpty() }; };
      /* la lecture NAIVE d'avant : boite monde moins decalage */
      const naive = (o) => { const d = decalageEtalement(api, o).decalage;
        return boite(o).getCenter(new THREE.Vector3()).sub(d).toArray(); };
      const r = { assemble, tailleL,
        L: lu(L), aile: lu(aile), boite: lu(boiteSeule), piece1: lu(pieces[1]),
        naiveL: naive(L), naivePiece1: naive(pieces[1]),
        enveloppe: lu(enveloppe), horsPlaqueAvant: null };
      ranger(api); racine.updateMatrixWorld(true);
      r.rangee = lu(L);
      console.log(JSON.stringify(r));
    """))
    dist = lambda a, b: math.dist(a, b)
    # LA PIÈCE EN L, TOURNÉE ET DÉPLACÉE : la boîte modèle retrouve le centre
    # assemblé à 1e-9, pour la pièce, pour son aile, pour sa boîte
    for nom in ("L", "aile", "boite", "piece1"):
        assert sortie[nom]["etale"] is False and sortie[nom]["vide"] is False, (nom, sortie[nom])
        assert dist(sortie[nom]["c"], sortie["assemble"][nom]) < 1e-9, \
            (nom, sortie[nom]["c"], sortie["assemble"][nom])
    # LE TÉMOIN : la lecture naïve est FAUSSE sur le L — de plus de 5 % de sa
    # largeur — et juste sur la boîte symétrique (c'est pourquoi le banc était
    # vert). Si cette assertion tombe, la scène est redevenue trop symétrique.
    ecart = dist(sortie["naiveL"], sortie["assemble"]["L"])
    assert ecart > 0.05 * max(sortie["tailleL"]), (ecart, sortie["tailleL"])
    assert dist(sortie["naivePiece1"], sortie["assemble"]["piece1"]) < 1e-9
    # un nœud qui CONTIENT des pièces ne peut pas être recomposé : il le dit
    assert sortie["enveloppe"]["etale"] is True
    # rangée, la boîte modèle est la boîte monde, sans doute
    assert sortie["rangee"]["etale"] is False
    assert dist(sortie["rangee"]["c"], sortie["assemble"]["L"]) < 1e-9
    # ── ET LE RAIL, sur le vrai lireRepere : les chiffres écrits sont ceux du
    # modèle, pièce tournée comprise ───────────────────────────────────────
    rail = json.loads(_node_trois(
        "echelleMm, marquerAuRepere, majRepere, cadrer, dessinerRegles",
        _importer_plaque("etaler, ranger, boiteModele, plateauDe, poserAngle, deplacerPiece")
        + _faux_rail() + _constantes_etabli("LIGNES_REPERE")
        + _fonction_etabli("enMillimetres") + "\n"
        + _fonction_etabli("uniteCourante") + "\n"
        + _fonction_etabli("fmtMesure") + "\n"
        + _fonction_etabli("plusGrandeDimension") + "\n"
        + _fonction_etabli("mesurerRetenus") + "\n"
        + _fonction_etabli("rendreRepere") + "\n"
        + _fonction_etabli("graduerPlateau") + "\n"
        + _fonction_etabli("lireRepere") + "\n" + """
      const api = monter(860, 824);
      """ + _scene_enveloppe() + """
      S.vueA = api;
      const boite = new THREE.Box3().setFromObject(racine);
      S.geoA = { taille: boite.getSize(new THREE.Vector3()) };
      REP.pas = majRepere(api).pas;
      rendreRepere();
      const L = pieces[2], aile = L.children[1];
      const centre = (o) => new THREE.Box3().setFromObject(o).getCenter(new THREE.Vector3()).toArray();
      const assemble = { L: centre(L), aile: centre(aile) };
      SEL.retenus.add(L.uuid); SEL.retenus.add(aile.uuid);
      const et = etaler(api);
      PLQ.active = true; PLQ.pieces = et.pieces; PLQ.pas = et.plateau.pas;
      poserAngle(api, 2, 37); deplacerPiece(api, 2, 0.31, -0.17);
      racine.updateMatrixWorld(true);
      lireRepere();
      console.log(JSON.stringify({ assemble, lu: lignesLues() }));
    """))
    lus = [_nombre_fr(v) for v in rail["lu"]["nombres"]]
    assert rail["lu"]["rangees"] == 2 and len(lus) == 6, rail["lu"]
    for i, nom in enumerate(("L", "aile")):
        for k in range(3):
            assert abs(lus[3 * i + k] - rail["assemble"][nom][k]) < 5e-4, \
                (nom, k, lus, rail["assemble"])
    assert "†" not in rail["lu"]["html"], rail["lu"]["html"]

