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
    """
    vue = _lire("lib3d/viewer.js")
    js = _lire("etabli/etabli.js")
    assert "const recul = aspect < seuil ? seuil / aspect : 1;" in vue
    assert "rayon * marge * recul" in vue
    assert js.count("cadrer(S.vueA)") == 2       # ouverture ET fermeture


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
    du corps des fonctions. Les trois fichiers du canevas sont couverts —
    selection.js l'est aussi par `..._ne_connait_aucune_route`, et le doublon
    est délibéré : si ce banc-ci était un jour le seul survivant, il devrait
    couvrir la chaîne entière à lui seul.
    """
    js = _lire("etabli/etabli.js")
    assert "GLTFExporter" not in js
    viewer = _lire("lib3d/viewer.js")
    assert "GLTFExporter" not in viewer
    assert "GLTFExporter" not in _lire("lib3d/selection.js")


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
    # LES DEUX boutons portent la classe : c'est elle, et rien d'autre, qui les
    # rend identiques. Un seul des deux la portant, le partage serait un mot.
    assert html.count('class="head-btn"') == 2
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


def test_la_vignette_pointe_sur_une_image_qui_EXISTE_ou_sur_rien():
    """La carte du bundle affiche `thumb` telle quelle : une URL morte donne
    une case grise, sans erreur nulle part.

    `/api/assets/3d/{job}/preview` ne sert QUE `preview.png`, que le moteur
    dépose — un job adopté n'en a aucun. Mais chaque fiche écrite par
    l'Établi rend, elle, `sil_v<n>/silhouette_face.png` : c'est la vignette
    honnête d'une production, et la route la PRÉFÈRE. Sans image du tout,
    `thumb` vaut `null` plutôt qu'un lien cassé.

    `prod_vign_deux` est le cas COURANT — un job de moteur, donc avec son
    `preview.png`, corrigé ensuite à l'Établi — et le seul où la préférence
    se mesure : partout ailleurs une seule des deux images existe.
    """
    from PIL import Image
    from app.services import mesh_edit
    _job("prod_vign_sil")
    mesh_edit.ecrire_version("prod_vign_sil", _glb_de_banc(),
                             operation="reparer", detail={})
    d0 = _job("prod_vign_deux")
    Image.new("RGB", (1, 1)).save(d0 / "preview.png")
    mesh_edit.ecrire_version("prod_vign_deux", _glb_de_banc(),
                             operation="reparer", detail={})
    # des octets illisibles : la fiche dégrade proprement, donc PAS de
    # silhouette — c'est ainsi qu'on atteint les deux autres branches
    d2 = _job("prod_vign_prev")
    mesh_edit.ecrire_version("prod_vign_prev", b"ceci n'est pas un GLB",
                             operation="reparer", detail={})
    Image.new("RGB", (1, 1)).save(d2 / "preview.png")
    _job("prod_vign_rien")
    mesh_edit.ecrire_version("prod_vign_rien", b"ceci n'est pas un GLB",
                             operation="reparer", detail={})

    c = _client()
    par_job = {e["job"]: e
               for e in c.get("/api/etabli/productions").json()["items"]}
    assert par_job["prod_vign_sil"]["thumb"] == \
        "/api/assets/3d/prod_vign_sil/silhouette/face?v=2"
    assert par_job["prod_vign_deux"]["thumb"] == \
        "/api/assets/3d/prod_vign_deux/silhouette/face?v=2"
    assert par_job["prod_vign_prev"]["thumb"] == \
        "/api/assets/3d/prod_vign_prev/preview"
    assert par_job["prod_vign_rien"]["thumb"] is None
    # et les trois URL servent VRAIMENT une image
    for j in ("prod_vign_sil", "prod_vign_deux", "prod_vign_prev"):
        assert c.get(par_job[j]["thumb"]).status_code == 200


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
