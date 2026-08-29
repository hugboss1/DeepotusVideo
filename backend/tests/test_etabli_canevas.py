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
