# -*- coding: utf-8 -*-
"""Card Forge — tâche #87 PR A (plan-cartes T14-T15, 04/10/2026) : l'ART DU DECK EN LOT, devis puis tir gardé.

DÉCISIONS DE L'UTILISATEUR (04/10) : route SERVEUR gardée (confirmation explicite, garde mensuelle « cartes » avant
chaque tir, route recensée payante, lignée cardforge + deck_id + parent + recette) ; MUR DUR par lot (10 $ par défaut).
Écarts au plan corrigés : la façade `image_providers.generate` n'a pas la signature du plan (size obligatoire, rend
{images}) et NE SERT PAS FLUX (défaut du plan) ; aucune garde de dépense prévue ; colonne d'art devinée à son nom au
lieu du mappage ; entités en `nom`/`planche` au lieu de `name`/`ref_image` ; tests du plan contradictoires (409/200).
AUCUN APPEL RÉEL : le tir, la garde, la bible et l'index sont simulés.
Témoin positif : la base (5234b286) n'a pas d'art en lot.
Run : cd backend ; & $PY tests/test_cards_lot_art.py
"""
import asyncio
import os
import pathlib
import subprocess
import sys
import tempfile

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_tmp = tempfile.mkdtemp(prefix="cflot_")
os.environ["DEEPOTUS_DATA_DIR"] = _tmp
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
for _k in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY", "OPENROUTER_API_KEY", "ELEVENLABS_API_KEY",
           "HEYGEN_API_KEY", "FIGMA_TOKEN", "OLLAMA_MODEL", "FAL_KEY"):
    os.environ[_k] = ""
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
_ICI = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(_ICI.parent))

import pytest                                                    # noqa: E402
from fastapi import HTTPException                                # noqa: E402
from httpx import ASGITransport, AsyncClient                     # noqa: E402

RACINE = _ICI.parent.parent
BASE = "5234b286"

COLS = ["nom", "prompt", "illus", "qty", "espece"]
ROWS = [["Colosse", "un golem de pierre sous la pluie", "", "3", "golem"],
        ["Oracle", "une pieuvre", "oracle_v2.png", "2", "pieuvre"],
        ["Rebut", "", "", "5", "golem"],
        ["Écho", "un écho translucide", "", "1", "pieuvre"],
        ["Hors", "écartée", "", "4", "golem"]]
MAP = {"nom": "title", "illus": "art"}
CORPS = {"columns": COLS, "rows": ROWS, "map": MAP, "off": [4], "qty_col": "qty", "model": "nano-banana", "n": 1,
         "gabarit": "{prompt}", "style": "vitrail, plomb épais", "size": "portrait_4_3"}
ENTITES = [{"name": "Colosse", "aliases": ["le géant"], "description": "trois mètres, mousse verte",
            "ref_image": "planche_colosse.png"}]

TIRS, GARDES, NOTES, REFUS, PANNE = [], [], [], [], []


async def _faux_tir(model, prompt, size, n, refs):
    TIRS.append((model, prompt, size, n, list(refs)))
    if len(TIRS) in PANNE:
        raise RuntimeError(r"le fournisseur a répondu 500 (C:\Users\x\secret.png)")
    return [f"lot_{len(TIRS)}_{k}.png" for k in range(n)]


async def _faux_verifier(op, categorie="", ref=None, confirme=None):
    GARDES.append((op, categorie))
    if len(GARDES) in REFUS:
        raise HTTPException(402, detail={"dz_plafond": True, "message": "Plafond mensuel atteint"})
    return {}


async def _faux_noter(files, source, **kw):
    NOTES.append((list(files), source, kw))


def _armer(fal="cle-test", entites=()):
    from app.config import settings
    from app.services import plafonds as PL, library_index as LI
    from app.services.cards import data as D
    settings.FAL_KEY = fal
    settings.OPENAI_API_KEY = ""
    D._tirer_lot = _faux_tir
    PL.verifier = _faux_verifier
    LI.noter = _faux_noter

    async def _bible():
        return [dict(e) for e in entites]
    D._bible_entites = _bible
    for l in (TIRS, GARDES, NOTES, REFUS, PANNE):
        l.clear()


def _req(methode, chemin, corps=None):
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://127.0.0.1") as c:
            r = await c.post("/api/cards/decks", json={"name": "Lot"})
            did = r.json()["deck"]["id"]
            if methode == "GET":
                return did, await c.get(f"/api/cards/{did}/data/{chemin}")
            return did, await c.post(f"/api/cards/{did}/data/{chemin}", json=corps)
    return asyncio.run(go())


def _prix(m, n):
    from app.services.cards import face
    return face.prix_usd(m, n)


def test_temoin_la_base_n_a_pas_d_art_en_lot():
    d = subprocess.run(["git", "show", f"{BASE}:backend/app/services/cards/data.py"], capture_output=True,
                       cwd=str(RACINE)).stdout
    assert d and b"/lot/generer" not in d


def test_le_devis_compte_les_LIGNES_et_rien_n_est_appele():
    _armer()
    _did, r = _req("POST", "lot/devis", CORPS)
    assert r.status_code == 200, r.text
    j = r.json()
    # Colosse, Rebut, Écho à illustrer ; Oracle a son art ; « Hors » est écartée ; Rebut n'a pas de texte
    assert j["lignes_a_generer"] == 3 and j["incomplets"] == 1 and j["deja_illustrees"] == 1, j
    assert j["cartes_couvertes"] == 9 and j["lignes_de_ce_lot"] == 2 and j["images"] == 2, j
    assert j["sans_prompt"] == [3] and j["model"] == "nano-banana" and j["mur_usd"] == 10.0 and j["sous_le_mur"]
    assert j["total_usd"] == round(_prix("nano-banana", 2), 4) and j["usd_par_image"] == _prix("nano-banana", 1)
    assert TIRS == [] and GARDES == [] and NOTES == []


def test_le_devis_multiplie_par_les_variantes_et_suit_le_prix_du_modele():
    _armer()
    j1 = _req("POST", "lot/devis", CORPS)[1].json()
    j4 = _req("POST", "lot/devis", dict(CORPS, n=4))[1].json()
    jp = _req("POST", "lot/devis", dict(CORPS, model="nano-banana-pro"))[1].json()
    assert j4["images"] == 8 and round(j4["total_usd"], 4) == round(_prix("nano-banana", 8), 4), j4
    assert jp["total_usd"] == round(_prix("nano-banana-pro", 2), 4) and jp["total_usd"] > j1["total_usd"]
    assert _req("POST", "lot/devis", dict(CORPS, n=9))[1].json()["n_par_ligne"] == 4     # borné


def test_refus_400_flux_modele_inconnu_art_non_mappe_gabarit_hors_colonnes():
    _armer()
    r = _req("POST", "lot/devis", dict(CORPS, model="flux"))[1]
    assert r.status_code == 400 and "FLUX" in r.text, r.text
    assert _req("POST", "lot/devis", dict(CORPS, model="xyz"))[1].status_code == 400
    r = _req("POST", "lot/devis", dict(CORPS, map={"nom": "title"}))[1]
    assert r.status_code == 400 and "illustration" in r.text, r.text
    r = _req("POST", "lot/devis", dict(CORPS, gabarit="{prompt}, {couleur}"))[1]
    assert r.status_code == 400 and "couleur" in r.text, r.text
    # un gabarit est une saisie, pas du code : pas d'accès aux attributs
    assert _req("POST", "lot/devis", dict(CORPS, gabarit="{nom.__class__}"))[1].status_code == 400
    assert _req("POST", "lot/devis", dict(CORPS, col_entite="nope"))[1].status_code == 400
    assert _req("POST", "lot/devis", ["pas", "un", "objet"])[1].status_code == 400
    assert TIRS == []


def test_sans_confirmation_le_lot_rend_le_devis_et_ne_tire_rien():
    _armer()
    r = _req("POST", "lot/generer", CORPS)[1]
    assert r.status_code == 400 and r.json()["detail"]["erreur"] == "confirmation requise", r.text
    assert r.json()["detail"]["devis"]["images"] == 2 and TIRS == [] and GARDES == []


def test_le_lot_confirme_tire_par_ligne_garde_chaque_tir_et_note_la_lignee():
    _armer(entites=ENTITES)
    did, r = _req("POST", "lot/generer", dict(CORPS, confirmer=True, col_entite="nom"))
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["generees"] == 2 and j["echecs"] == 0 and j["arret"] == "", j
    assert [x["ligne"] for x in j["resultats"]] == [1, 4] and j["resultats"][0]["fichiers"] == ["lot_1_0.png"]
    # LA GARDE AVANT CHAQUE TIR, en image, catégorie « cartes »
    assert [g[1] for g in GARDES] == ["cartes", "cartes"] and GARDES[0][0] == {"kind": "image", "n": 1, "model": "nano-banana"}
    # le prompt : la colonne, la description de l'entité, le style ; la planche en référence
    assert TIRS[0][1] == "un golem de pierre sous la pluie, trois mètres, mousse verte, vitrail, plomb épais", TIRS[0]
    assert TIRS[0][4] == ["planche_colosse.png"] and TIRS[1][4] == [] and TIRS[0][2] == "portrait_4_3"
    assert all("vitrail" in t[1] for t in TIRS)
    # LA LIGNÉE : cardforge, deck_id, mère = la planche (relation « carte »), recette rejouable
    assert len(NOTES) == 2 and all(s == "cardforge" and k["deck_id"] == did for _f, s, k in NOTES)
    assert NOTES[0][2]["parent"] == "planche_colosse.png" and NOTES[0][2]["relation"] == "carte"
    assert NOTES[1][2]["parent"] is None and NOTES[1][2]["relation"] is None
    rec = NOTES[0][2]["recette"]
    assert rec["prompt"] == TIRS[0][1] and rec["model"] == "nano-banana" and rec["size"] == "portrait_4_3" and rec["lot"]["ligne"] == 1


def test_une_entite_se_retrouve_par_son_alias_et_sans_la_casse():
    _armer(entites=ENTITES)
    rows = [["LE GÉANT", "un colosse", "", "1", ""]]
    _req("POST", "lot/generer", dict(CORPS, rows=rows, off=[], confirmer=True, col_entite="nom"))
    assert TIRS and "mousse verte" in TIRS[0][1] and TIRS[0][4] == ["planche_colosse.png"], TIRS


def test_le_mur_du_lot_refuse_avant_tout_tir():
    _armer()
    r = _req("POST", "lot/generer", dict(CORPS, confirmer=True, mur_usd=0.01))[1]
    assert r.status_code == 409 and "mur" in r.text and TIRS == [] and GARDES == [], r.text
    assert _req("POST", "lot/devis", dict(CORPS, mur_usd=500))[1].json()["mur_usd"] == 100.0       # borné
    assert _req("POST", "lot/devis", dict(CORPS, mur_usd="abc"))[1].json()["mur_usd"] == 10.0
    assert _req("POST", "lot/devis", dict(CORPS, mur_usd=0))[1].json()["mur_usd"] == 10.0        # 0 n'est pas « aucun mur »
    assert _req("POST", "lot/devis", dict(CORPS, mur_usd=-5))[1].json()["mur_usd"] == 10.0


def test_un_modele_sans_tarif_lu_ne_part_pas():
    _armer()
    from app.services.cards import face
    ancien = face.prix_usd
    face.prix_usd = lambda m, n=1: None
    try:
        r = _req("POST", "lot/devis", CORPS)[1]
    finally:
        face.prix_usd = ancien
    assert r.status_code == 400 and "tarifs" in r.text, r.text


def test_un_format_inconnu_est_refuse_avant_tout_tir():
    _armer()
    r = _req("POST", "lot/generer", dict(CORPS, confirmer=True, size="8k_panorama"))[1]
    assert r.status_code == 400 and "Format" in r.text and TIRS == [] and GARDES == [], r.text


def test_un_fournisseur_qui_ne_rend_rien_est_un_echec_de_la_ligne():
    _armer()
    from app.services.cards import data as D

    async def vide(model, prompt, size, n, refs):
        TIRS.append(prompt)
        return []
    D._tirer_lot = vide
    j = _req("POST", "lot/generer", dict(CORPS, confirmer=True))[1].json()
    assert j["generees"] == 0 and j["echecs"] == 2 and "aucune image" in j["erreurs"][0]["message"] and NOTES == [], j


def test_sans_cle_503_sans_rien_lancer():
    _armer(fal="")
    r = _req("POST", "lot/generer", dict(CORPS, confirmer=True))[1]
    assert r.status_code == 503 and "Réglages" in r.text and TIRS == [] and GARDES == [], r.text


def test_un_echec_n_arrete_pas_le_lot_et_se_dit_sans_chemin():
    _armer()
    PANNE.append(1)
    r = _req("POST", "lot/generer", dict(CORPS, confirmer=True))[1]
    j = r.json()
    assert r.status_code == 200 and j["generees"] == 1 and j["echecs"] == 1, j
    assert j["erreurs"][0]["ligne"] == 1 and "500" in j["erreurs"][0]["message"]
    assert "secret" not in j["erreurs"][0]["message"] and "<chemin>" in j["erreurs"][0]["message"], j["erreurs"]
    assert [x["ligne"] for x in j["resultats"]] == [4] and len(NOTES) == 1


def test_le_plafond_arrete_le_lot_avant_le_premier_tir_ou_en_cours():
    _armer()
    REFUS.append(1)
    r = _req("POST", "lot/generer", dict(CORPS, confirmer=True))[1]
    assert r.status_code == 402 and TIRS == [], r.text
    _armer()
    REFUS.append(2)
    rows = [[f"c{i}", f"motif {i}", "", "1", ""] for i in range(3)]
    r = _req("POST", "lot/generer", dict(CORPS, rows=rows, off=[], confirmer=True))[1]
    j = r.json()
    # LE PLAFOND ARRÊTE LE LOT : la 3e ligne n'est ni gardée ni tirée
    assert r.status_code == 200 and j["generees"] == 1 and "Plafond" in j["arret"] and len(TIRS) == 1 and len(GARDES) == 2, j


def test_un_nom_d_artiste_est_refuse_avant_tout_tir():
    _armer()
    r = _req("POST", "lot/generer", dict(CORPS, confirmer=True, style="à la manière de Starowieyski"))[1]
    assert r.status_code == 400 and "artiste" in r.text and "Ligne 1" in r.text and GARDES == [] and TIRS == [], r.text


def test_douze_lignes_par_demande_le_reste_attend():
    _armer()
    rows = [[f"c{i}", f"motif {i}", "", "1", ""] for i in range(15)]
    j = _req("POST", "lot/generer", dict(CORPS, rows=rows, off=[], confirmer=True))[1].json()
    assert j["generees"] == 12 and j["restants"] == 3 and len(TIRS) == 12 and len(GARDES) == 12, (j["generees"], j["restants"])
    r = _req("POST", "lot/generer", dict(CORPS, rows=[["x", "", "", "1", ""]], off=[], confirmer=True))[1]
    assert r.status_code == 200 and r.json()["generees"] == 0 and TIRS.__len__() == 12        # rien de complet : rien
    # rien à dépenser : ni confirmation ni clé exigées, et aucune garde
    _armer(fal="")
    r = _req("POST", "lot/generer", dict(CORPS, rows=[["x", "", "", "1", ""]], off=[]))[1]
    assert r.status_code == 200 and r.json()["generees"] == 0 and GARDES == [], r.text


def test_modeles_sans_flux_avec_tarif_et_cle():
    _armer()
    j = _req("GET", "lot/modeles")[1].json()
    ids = {m["id"]: m for m in j["models"]}
    assert "flux" not in ids and ids["nano-banana"]["cle"] is True and ids["gpt-image-2"]["cle"] is False, ids
    assert ids["nano-banana"]["usd_par_image"] == _prix("nano-banana", 1) and j["mur_usd"] == 10.0
    assert j["tailles"][0] == "portrait_4_3" and j["lignes_max"] == 12


def test_le_tir_reel_ne_passe_les_references_qu_a_nano_banana():
    from app.config import settings
    from app.services import image_providers as IP
    import importlib
    from app.services.cards import data as D
    D = importlib.reload(D)            # le vrai `_tirer_lot`, pas le simulé
    vus = []

    async def faux_generate(provider, prompt, size, n=1, **kw):
        vus.append((provider, size, n, kw.get("image_paths")))
        return {"images": ["a.png"], "seed": None}
    ancien = IP.generate
    IP.generate = faux_generate
    try:
        (settings.images_path / "planche.png").write_bytes(b"x")
        assert asyncio.run(D._tirer_lot("nano-banana", "p", "square_hd", 2, ["planche.png", "absente.png"])) == ["a.png"]
        asyncio.run(D._tirer_lot("gpt-image-2", "p", "square_hd", 1, ["planche.png"]))
    finally:
        IP.generate = ancien
    assert vus[0][0] == "nano-banana" and vus[0][1:3] == ("square_hd", 2)
    assert [p.name for p in vus[0][3]] == ["planche.png"] and vus[1][3] is None, vus


def test_la_route_est_recensee_payante_et_gardee():
    sys.path.insert(0, str(_ICI))
    import _recensement_payant as RP
    rec = RP.recenser()
    cle = ("data", "POST", "/lot/generer")
    assert cle in rec and rec[cle]["garde"] is True and "_tirer_lot" in rec[cle]["puits"], rec.get(cle)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-p", "no:cacheprovider"]))
