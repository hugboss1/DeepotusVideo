# -*- coding: utf-8 -*-
"""Banc du maillon dzplanifaff et du message du plafond (10/11/2026) : trois défauts d'affichage.

1. Le graphe d'acheminement du Planificateur dit « auto possible » d'après la liste `auto_channels` de /api/health
   (YouTube, Instagram… que le serveur publie seul), pas seulement pour Telegram et X.
2. « Scheduler » et « Analytics » passent par dzT : « Planificateur » et « Statistiques » en français.
3. Le message du plafond mensuel renvoie vers « Réglages → Tarifs et budget » (nom français de la section).

Lancer : depuis backend/, python -m pytest tests/test_planif_affichage.py  (ou python tests/test_planif_affichage.py)
"""
import importlib
import json
import pathlib
import shutil
import subprocess
import sys

R = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(R / "scripts"))
sys.path.insert(0, str(R / "backend" / "tests"))
sys.path.insert(0, str(R / "backend"))

M = importlib.import_module("patch_bundle_dzplanifaff")
RAW = M.BUNDLE.read_bytes()
BUNDLE = RAW.decode("utf-8")


def test_marqueur_unique_et_paires_posees():
    assert BUNDLE.count(M.MARKER) == 1
    for ancre, remplace in M.PAIRES:
        assert BUNDLE.count(remplace) == 1, remplace[:80]
        assert "\n" not in ancre + remplace


def test_aller_retour_exact():
    avant = M.defaire(BUNDLE)
    assert M.MARKER not in avant
    assert M.appliquer(avant) == BUNDLE
    assert not M.partiel(BUNDLE)


def test_graphe_lit_auto_channels_et_garde_les_anciens_canaux():
    z = M.PAIRES[0][1]
    assert 'I==="x"&&!!(o!=null&&o.x_enabled)' in z, "Telegram et X restent comme avant"
    assert "o.auto_channels.indexOf(I)>=0" in z and 'o[I+"_enabled"]' in z, "liste du serveur, à défaut le drapeau"
    assert "Array.isArray(o.auto_channels)" in z and "!!(o&&" in z, "health absent ou ancien serveur : pas d'erreur"
    assert 'I==="whatsapp"||' in BUNDLE[BUNDLE.index(M.MARKER) - 400:BUNDLE.index(M.MARKER)], "dzdiffusion intact"


def test_libelles_passent_par_dzt():
    assert 'children:"Scheduler"})' not in BUNDLE
    assert 'children:"Analytics"})' not in BUNDLE
    assert 'children:dzT("scheduler.calendrier.titre")})' in BUNDLE
    assert 'onClick:function(){__dzSchedAnalytics()},children:dzT("scheduler.calendrier.analytics")})' in BUNDLE


def test_cles_du_dictionnaire():
    d = json.loads((R / "frontend" / "shared" / "i18n" / "planif_news.json").read_text("utf-8"))
    assert d["scheduler.calendrier.titre"] == {"fr": "Planificateur", "en": "Scheduler"}
    assert d["scheduler.calendrier.analytics"] == {"fr": "Statistiques", "en": "Analytics"}
    for f in (R / "frontend" / "shared" / "dz-i18n-dico.js", R / "frontend" / "dist" / "shared" / "dz-i18n-dico.js"):
        c = f.read_text("utf-8")
        assert '"scheduler.calendrier.titre"' in c and '"scheduler.calendrier.analytics"' in c, f


def test_epingles_figees_et_fins_de_ligne():
    assert BUNDLE.count("x.useState(") == 731
    assert BUNDLE.count("v2.8.0") == 4
    assert BUNDLE.count("DzTracks") == 181
    assert BUNDLE.count(M.CONFIRMER) == 30
    assert RAW.count(b"\r\n") > 15000 and RAW.count(b"\n") == RAW.count(b"\r\n")
    assert not M.BAK.exists(), "le .bak du maillon est supprimé après l'écriture"


def test_idempotent_et_voisins():
    py = sys.executable
    for nom in ("patch_bundle_dzplanifaff.py", "patch_bundle_dzigformat.py"):
        r = subprocess.run([py, str(R / "scripts" / nom), "--check"], capture_output=True, cwd=R)
        assert r.returncode == 0, (nom, r.stdout[-300:], r.stderr[-300:])
        assert "appliqu".encode() in r.stdout, (nom, r.stdout)


def test_inverse_inscrit_en_tete():
    AIDE = importlib.import_module("_i18n_l1_aide")
    assert AIDE.avant_dzplanifaff(BUNDLE) == M.defaire(BUNDLE)
    assert AIDE.avant_dzplanifaff(M.defaire(BUNDLE)) == M.defaire(BUNDLE), "sans marqueur : rendu tel quel"
    corps = pathlib.Path(AIDE.__file__).read_text(encoding="utf-8")
    c = corps[corps.index("def avant_dzigformat("):corps.index("def avant_dzmethodes(")]
    assert "bundle = avant_dzplanifaff(bundle)" in c and c.index("avant_dzplanifaff(") < c.index("if _m.MARKER not in bundle")


def test_bundle_syntaxe():
    node = shutil.which("node")
    if not node:
        return
    r = subprocess.run([node, "--check", str(M.BUNDLE)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[-300:]


def test_health_expose_auto_channels():
    src = (R / "backend" / "app" / "api" / "routes.py").read_text("utf-8")
    sante = src[src.index('@router.get("/health")'):]
    sante = sante[:sante.index("@router.", 10)] if "@router." in sante[10:] else sante
    assert '"auto_channels": _canaux_auto(),' in sante
    from app.api import routes
    from app.services import publishers
    sauve = dict(publishers._REGISTRY)
    try:
        publishers._REGISTRY.clear()
        publishers.register("youtube", lambda: True, None)
        publishers.register("instagram", lambda: True, None)
        publishers.register("tiktok", lambda: False, None)
        assert routes._canaux_auto() == ["instagram", "youtube"], "triés, seulement les disponibles"

        def casse():
            raise RuntimeError("clé illisible")
        publishers.register("x", casse, None)
        assert routes._canaux_auto() is None, "une erreur ne casse pas /api/health : le graphe retombe sur <canal>_enabled"
    finally:
        publishers._REGISTRY.clear()
        publishers._REGISTRY.update(sauve)


def test_message_plafond_nomme_tarifs_et_budget():
    from fastapi import HTTPException
    from app.services import plafonds
    src = (R / "backend" / "app" / "services" / "plafonds.py").read_text("utf-8")
    assert "Pricing & budget" not in src and "Réglages → Tarifs et budget." in src
    for f in (R / "frontend" / "shared" / "dz-plafonds.js", R / "frontend" / "dist" / "shared" / "dz-plafonds.js"):
        c = f.read_text("utf-8")
        assert "Pricing & budget" not in c and "Réglages → Tarifs et budget pour voir ou relever les plafonds." in c, f
    assert ((R / "frontend" / "shared" / "dz-plafonds.js").read_bytes()
            == (R / "frontend" / "dist" / "shared" / "dz-plafonds.js").read_bytes()), "copie dist à l'octet"
    e = plafonds._refus("global", "", 0.0, 0.006, 0.001, "cartes")
    assert isinstance(e, HTTPException) and e.status_code == 402
    assert e.detail["dz_plafond"]["message"].endswith("relevez le plafond dans Réglages → Tarifs et budget.")
    e = plafonds._refus("espace", "", 1.0, 0.5, 1.2, "", "Atelier")
    assert e.detail["dz_plafond"]["message"].endswith("le plafond dans Réglages → Espaces."), "le motif espace est inchangé"


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
