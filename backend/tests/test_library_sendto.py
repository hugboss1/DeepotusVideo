"""Bibliothèque — « Envoyer vers… » (plan
2026-08-28-bibliotheque-provenance-envoyer-vers, chantier B).

Tout vit dans le BUNDLE (patcher libsend, maillon APRÈS libprov) et
réutilise les mécanismes EXISTANTS de l'app (Lh/__dzRenderGraph,
deepotus:navigate, __dzToSpriteLab, __dzPrint3d, createScheduledPost +
deepotus:select-post, PUT /bible/entities/{id}) — ces pins attrapent un
effacement silencieux de la chaîne.

Run: pytest tests/test_library_sendto.py -q
"""
import pathlib

_RACINE = pathlib.Path(__file__).resolve().parent.parent.parent
_BUNDLE = _RACINE / "frontend" / "dist" / "assets" / "index-BEOJX8L5.js"


def test_le_miroir_bundle_envoyer_vers():
    s = _BUNDLE.read_text("utf-8")
    # le menu : définition + l'appel du bouton du modal
    assert s.count("__dzSendTo") == 2
    assert "Envoyer vers…" in s
    # greffe Quick : pose (menu) + lecture/consommation (mount de Quick)
    assert s.count("__dzQuickStart") == 3
    # greffe Montage : pose image + pose clip (menu) + lecture + delete
    assert s.count("__dzMontageAdd") == 4
    # cibles existantes réutilisées : Sprite Lab (def + 2 modal + 2 menu),
    # Impression 3D (def + hub + menu — le pin de test_print3d suit à 3)
    assert s.count("__dzToSpriteLab") == 5
    assert s.count("__dzPrint3d") == 3
    # l'amont ne bouge pas
    assert s.count("__dzLibPicker") == 10
    assert s.count("__dzSrcChips") == 2


def test_les_cibles_portent_les_mecanismes_reels():
    s = _BUNDLE.read_text("utf-8")
    # Studio : le graphe minimal consommé par l'init Lh existante
    assert 'type:"Image",x:300,y:240,props:{filename:nom}' in s
    # Template : l'image câblée au port bg du Spatial compose
    assert 'toPort:"bg"' in s
    # Bible : le PUT existant, inspiration_images fusionnées
    assert '/api/bible/entities/' in s
    # Cardforge : le chemin img: résolu par artSource, via presse-papier
    assert '"img:"+nom' in s
    # Scheduler : brouillon + sélection (patron Épisodes)
    assert s.count("deepotus:select-post") == 6


def test_le_patcher_libsend_est_garde():
    patcher = (_RACINE / "scripts"
               / "patch_bundle_libsend.py").read_text("utf-8")
    assert "guard_downstream" in patcher and "STABLE_PROBES" in patcher
    assert "SPEC_CHAR_DELTA" in patcher and "node --check" in patcher
