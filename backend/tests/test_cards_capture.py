# -*- coding: utf-8 -*-
"""Card Forge — P10 « Import » (id de module `capture`). Les seuils, mesurés.

CE QUE CE FICHIER TIENT AUJOURD'HUI (tâche T1, la coquille) : l'ADMISSION
d'une image de carte et le SERVICE des fichiers du dossier `capture/`. Rien
d'autre : l'analyse (bordure, zones, fond, palette) est la tâche T2 et ses
seuils à vérité connue arriveront ici, sous ces tests-là.

Ce qui est verrouillé, seuil par seuil :

  1. L'ADMISSION EST CELLE DE `texture.py:post_paper`, à la lettre : corps vide
     -> 400 ; corps > 64 Mo -> 400 ; dimensions lues dans L'EN-TÊTE avant tout
     décodage -> 413 au-delà de 32 Mpx ; `load()` gardé ; RGB ; réduction
     LANCZOS au-delà de 4096 px ; écriture atomique (tmp + replace).
     Le contrôle AVANT décodage est épinglé SUR LA SOURCE : après `img.load()`
     le demi-gigaoctet est déjà alloué, et aucun test dynamique ne distingue
     les deux ordres.
  2. `?side` est une LISTE BLANCHE À DEUX ENTRÉES, refusée en français et
     nommée. Pas un 422 FastAPI en anglais : le paramètre se prend en `str` et
     se valide à la main, sinon l'utilisateur lit « value is not a valid
     enumeration member » pour une faute de frappe.
  3. Le GET du dossier sert par LISTE BLANCHE DE NOMS FINAUX. Ni traversée, ni
     fichier temporaire : `source_recto.png.tmp` existe pendant la fenêtre
     d'écriture, il ne doit être servi à personne — un nom de fichier est un
     identifiant, jamais un chemin.
  4. RÉ-IMPORT = REMPLACEMENT. Une capture est un point de départ, pas une
     pile : le second envoi écrase le premier, et les octets servis sont ceux
     du second.
  5. JAMAIS 500 (spec §8) : corps illisible, JSON à la place d'un PNG, deck
     inconnu, nom inconnu — chacun a son refus nommé.

────────────────────────────────────────────────────────────────────────────
LA RONDE DE MUTATION (T1, 24/08) — cinq gardes cassées une par une, la
batterie relancée à chaque fois, le fautif restauré ensuite :

  · `_side_or_400` sans son test d'appartenance ....... test du ?side, ROUGE
  · `FILE_RE` privée de son SEUL `$` final ............ test du .tmp, ROUGE
  · écriture directe au lieu de tmp + replace ......... test atomique, ROUGE
  · `IMG_MAX_PIXELS * 8` (plafond de trame élargi) .... test bombe, ROUGE
  · `capture` retiré de `MODULE_IDS` .................. 4 tests, ROUGE
    (test_cards_core.py: coquille des dix, parité écran/backend, sous-arbre
     capture ; test_cards_capture.py: dans les dix ids)

ET LE TÉMOIN QUI SURVIT, AVOUÉ. `Image.LANCZOS` remplacé par
`Image.NEAREST` dans la réduction : 19 tests sur 19 restent VERTS. Rien ici
ne mesure la QUALITÉ du rééchantillonnage — les tests lisent les dimensions
et le poids, pas la netteté. Le trou est réel et il est chiffrable (un
plus-proche-voisin sur une carte à filets fins fabrique de l'aliasing que
l'analyse de bordure de T2 prendra pour du signal), mais le seuil qui le
fermerait — « l'énergie haute fréquence de la réduite reste sous x % de
celle de la source » — appartient à T2, qui apporte l'outillage de mesure
(`_micro_contrast`, `stats`). L'écrire ici en aveugle serait un seuil posé
au doigt mouillé. C'est le témoin volontaire de cette tâche.

Run : .\\scripts\\run-tests.ps1 -Filter cards_capture
"""
import asyncio
import io
import os
import pathlib
import re
import struct
import sys
import tempfile
import zlib

_tmp = tempfile.mkdtemp()
os.environ["DATABASE_URL"] = \
    f"sqlite+aiosqlite:///{pathlib.Path(_tmp, 't.db').as_posix()}"
os.environ.setdefault("FAL_KEY", "test-key")
os.environ["IMAGES_FOLDER"] = str(pathlib.Path(_tmp, "images"))
os.environ["OUTPUTS_FOLDER"] = str(pathlib.Path(_tmp, "outputs"))
pathlib.Path(_tmp, "images").mkdir(exist_ok=True)
pathlib.Path(_tmp, "outputs").mkdir(exist_ok=True)
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest                                                   # noqa: E402
from httpx import AsyncClient, ASGITransport                     # noqa: E402
from PIL import Image                                            # noqa: E402

from app.services.cards import capture as CP                     # noqa: E402
from app.services.cards import contract as CT                    # noqa: E402
from app.services.cards import core as CC                        # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
JS = REPO / "frontend" / "cardforge" / "js" / "mod-capture.js"
CSS = REPO / "frontend" / "cardforge" / "css" / "mod-capture.css"


# ═══════════════════════ outillage ══════════════════════════════════════════

def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=600.0) as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _deck() -> str:
    return CC.create_deck("import")["id"]


def _carte(w: int = 630, h: int = 880, teinte: int = 40) -> bytes:
    """Une carte plausible : bordure claire, intérieur sombre, un aplat.
    Une image PLATE ne dirait rien des mesures de T2 ; celle-ci porte déjà
    une bordure franche, pour que le fichier d'aujourd'hui serve demain."""
    im = Image.new("RGB", (w, h), (216, 183, 106))
    px = im.load()
    b = max(2, min(w, h) // 24)
    for y in range(b, h - b):
        for x in range(b, w - b):
            px[x, y] = (teinte, teinte - 4 if teinte > 4 else 0, teinte // 2)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _bombe_png(w: int, h: int) -> bytes:
    """Un PNG VALIDE et minuscule qui DÉCLARE `w` x `h`.

    Construit à la main, une ligne à la fois : la charge est faite de zéros,
    donc zlib la réduit à quelques kilo-octets et le tampon de construction ne
    dépasse jamais une ligne. C'est exactement l'asymétrie qu'une bombe de
    pixels exploite — quelques centaines de kilo-octets sur le fil, des
    centaines de mégaoctets chez celui qui décode."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)   # 8 bits, gris
    co = zlib.compressobj(1)
    ligne = b"\x00" * (w + 1)                              # filtre 0 + w octets
    morceaux = [co.compress(ligne) for _ in range(h)]
    morceaux.append(co.flush())
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", b"".join(morceaux)) + chunk(b"IEND", b""))


def _post(did: str, corps: bytes, side: str | None = None):
    q = "" if side is None else f"?side={side}"
    return _api("POST", f"/api/cards/{did}/capture/card{q}",
                content=corps, headers={"Content-Type": "image/png"})


# ═══════════════════════ la pièce existe ════════════════════════════════════

def test_la_piece_existe_et_respecte_la_regle_1():
    """Règle 1 : 1 JS + 1 CSS + 1 py + 1 test. Le test, c'est ce fichier ;
    les trois autres se vérifient sur le disque, pas sur une intention."""
    assert JS.is_file(), JS
    assert CSS.is_file(), CSS
    assert pathlib.Path(CP.__file__).is_file()
    from fastapi import APIRouter
    assert isinstance(CP.router, APIRouter)


def test_capture_est_dans_les_dix_ids_du_contrat():
    """Un sous-arbre que le contrat ignore est un sous-arbre effacé à chaque
    autosave (F2 : `doc.forge3d`, deux phases durant). P10 ne recommence pas."""
    assert "capture" in CT.MODULE_IDS
    assert CT.MODULE_IDS[-1] == "capture", "P10 est la dixième du rail"
    assert len(CT.MODULE_IDS) == 10


def test_la_route_est_montee_sous_capture():
    from app.main import app
    chemins = list(app.openapi().get("paths", {}))
    assert "/api/cards/{did}/capture/card" in chemins, chemins[-8:]
    # AVANT le filet attrape-tout : Starlette apparie dans l'ordre. Sans cela
    # POST /capture/card répondrait « Route inconnue ».
    filet = [p for p in chemins if p.endswith("/{rest:path}")]
    if filet:
        assert chemins.index("/api/cards/{did}/capture/card") \
            < chemins.index(filet[0])


# ═══════════════════════ l'admission ════════════════════════════════════════

def test_admission_aller_retour_recto_et_verso():
    """Le geste complet : on dépose, le serveur RÉPOND ses mesures, et le
    fichier se relit à l'octet par la route de service."""
    did = _deck()
    for side, nom in (("recto", "source_recto.png"),
                      ("verso", "source_verso.png")):
        r = _post(did, _carte(300, 420), side)
        assert r.status_code == 200, (side, r.text[:300])
        d = r.json()
        assert d["side"] == side
        assert (d["w"], d["h"]) == (300, 420), d
        assert d["bytes"] > 0 and d["stamp"] > 0
        g = _api("GET", f"/api/cards/{did}/capture/{nom}")
        assert g.status_code == 200, (nom, g.status_code)
        assert g.headers["content-type"] == "image/png"
        assert len(g.content) == d["bytes"], "les octets servis ne sont pas ceux pesés"
        with Image.open(io.BytesIO(g.content)) as im:
            assert im.size == (300, 420)
    CC.delete_deck(did)


def test_le_recto_est_le_defaut():
    """`?side` absent = recto. Un défaut implicite doit s'écrire quelque part :
    ici, et le verso reste vierge."""
    did = _deck()
    r = _post(did, _carte(120, 168))
    assert r.status_code == 200, r.text
    assert r.json()["side"] == "recto"
    assert _api("GET", f"/api/cards/{did}/capture/source_recto.png") \
        .status_code == 200
    assert _api("GET", f"/api/cards/{did}/capture/source_verso.png") \
        .status_code == 404
    CC.delete_deck(did)


def test_un_side_inconnu_est_refuse_EN_FRANCAIS_et_nomme():
    """Un `Literal["recto","verso"]` de FastAPI aurait rendu un 422 anglais
    (« value is not a valid enumeration member ») sur une faute de frappe. Le
    paramètre se prend en `str` et se valide ici : 400, en français, avec les
    deux valeurs possibles ÉCRITES dans le message."""
    did = _deck()
    for mauvais in ("front", "RECTO_", "dos", "1", " ", "recto,verso"):
        r = _post(did, _carte(60, 84), mauvais)
        assert r.status_code == 400, (mauvais, r.status_code, r.text[:200])
        detail = r.json()["detail"]
        assert "recto" in detail and "verso" in detail, detail
        assert re.search(r"[éèêàç]", detail), \
            f"le refus n'est pas en français : {detail!r}"
    # aucun fichier n'a été écrit au passage
    d = CT.deck_dir(did) / "capture"
    assert not d.exists() or not list(d.iterdir()), list(d.iterdir())
    CC.delete_deck(did)


def test_un_corps_vide_ou_trop_lourd_est_refuse_avant_tout_decodage():
    """Deux garde-fous DISTINCTS et le premier est le poids : `SRC_MAX_BYTES`
    pèse ce qui arrive sur le fil, et il se lit sur `len(raw)` — pas après une
    tentative d'ouverture."""
    did = _deck()
    r = _post(did, b"", "recto")
    assert r.status_code == 400 and "vide" in r.json()["detail"].lower(), r.text
    assert CP.SRC_MAX_BYTES == 64 * 1024 * 1024
    gros = b"\x89PNG\r\n\x1a\n" + b"\x00" * (CP.SRC_MAX_BYTES + 1)
    r = _post(did, gros, "recto")
    assert r.status_code == 400, r.status_code
    assert "64" in r.json()["detail"], r.json()["detail"]
    CC.delete_deck(did)


def test_une_BOMBE_DE_PIXELS_est_refusee_sur_ses_DIMENSIONS():
    """Le poids du corps ne dit RIEN du coût du décodage : un PNG de zéros de
    quelques centaines de kilo-octets déclare 12000 x 12000, soit 144 Mpx et un
    demi-gigaoctet de tampon — par requête, et la bibliothèque se contente
    d'AVERTIR jusqu'à 179 Mpx avant de décoder quand même."""
    did = _deck()
    bombe = _bombe_png(12000, 12000)
    assert len(bombe) < 1_000_000, len(bombe)
    with Image.open(io.BytesIO(bombe)) as im:
        assert im.size == (12000, 12000)      # l'en-tête suffit, sans décoder
    assert CP.IMG_MAX_PIXELS == 32 * 1024 * 1024
    r = _post(did, bombe, "recto")
    assert r.status_code == 413, (r.status_code, r.text[:200])
    detail = r.json()["detail"]
    assert "12000" in detail and "pixel" in detail.lower(), detail
    # et rien n'a été écrit
    assert not (CT.deck_dir(did) / "capture" / "source_recto.png").exists()
    CC.delete_deck(did)


def test_le_controle_de_trame_est_AVANT_le_decodage_dans_la_source():
    """Épinglé sur la SOURCE, parce qu'aucun test dynamique ne distingue les
    deux ordres : les deux rendent 413, mais l'un a déjà alloué le tampon."""
    src = pathlib.Path(CP.__file__).read_text(encoding="utf-8")
    i = src.index("def _store_image(")
    corps = src[i:src.index("\ndef ", i + 1)]
    assert corps.index("IMG_MAX_PIXELS") < corps.index("img.load()"), \
        "les dimensions sont contrôlées APRÈS le décodage"


def test_une_image_trop_grande_est_REDUITE_a_MAX_IMPORT_PX():
    """4096 px de côté long. La 7e copie de la constante est AVOUÉE dans la
    source (règle 8 : une pièce ne partage pas ses constantes) — le test
    vérifie qu'elles disent toutes le même chiffre."""
    from app.services.cards import type as type_mod
    from app.services.cards import face as face_mod
    assert CP.MAX_IMPORT_PX == 4096
    assert CP.MAX_IMPORT_PX == type_mod.MAX_IMPORT_PX == face_mod.MAX_IMPORT_PX
    did = _deck()
    r = _post(did, _carte(5000, 2000), "recto")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert max(d["w"], d["h"]) == CP.MAX_IMPORT_PX, d
    assert d["h"] == round(2000 * 4096 / 5000), d       # le ratio est tenu
    with Image.open(io.BytesIO(
            _api("GET", f"/api/cards/{did}/capture/source_recto.png").content)) as im:
        assert im.size == (d["w"], d["h"]), "le fichier ment sur la réponse"
    CC.delete_deck(did)


def test_le_reimport_REMPLACE_et_ne_laisse_aucun_tmp():
    """Une capture est un point de départ, pas une pile : le second envoi
    écrase le premier. Et l'écriture est ATOMIQUE — le `.tmp` de la fenêtre
    d'écriture ne survit pas à la requête."""
    did = _deck()
    _post(did, _carte(200, 280), "recto")
    r = _post(did, _carte(300, 200), "recto")
    assert r.status_code == 200, r.text
    assert (r.json()["w"], r.json()["h"]) == (300, 200)
    d = CT.deck_dir(did) / "capture"
    restes = [p.name for p in d.iterdir()]
    assert restes == ["source_recto.png"], restes
    with Image.open(d / "source_recto.png") as im:
        assert im.size == (300, 200), "l'ancien fichier a survécu"
    CC.delete_deck(did)


def test_l_ecriture_est_atomique_tmp_puis_replace():
    """Sur la source : un `save()` direct sur le nom final laisse un fichier
    tronqué lisible par le GET si l'écriture s'interrompt. La mesure ne peut
    pas se prendre au vol dans un test — l'ordre s'épingle donc au texte."""
    src = pathlib.Path(CP.__file__).read_text(encoding="utf-8")
    i = src.index("def _store_image(")
    corps = src[i:src.index("\ndef ", i + 1)]
    assert ".tmp" in corps and "replace(" in corps, corps[-400:]
    assert corps.index(".tmp") < corps.index("replace("), corps[-400:]


# ═══════════════════════ le service, par liste blanche ══════════════════════

def test_le_GET_sert_par_LISTE_BLANCHE_et_refuse_la_traversee():
    """Un nom de fichier est un IDENTIFIANT, jamais un chemin. Le double
    garde-fou de `deck_dir` protège le `did` ; le nom, lui, n'a que cette
    liste — et elle est close."""
    did = _deck()
    _post(did, _carte(80, 112), "recto")
    for mauvais in ("../meta.json", "..%2fmeta.json", "source_recto.png.tmp",
                    "source_RECTO.png", "meta.json", "source_dos.png",
                    "source_recto.jpg", "", "source_recto"):
        chemin = f"/api/cards/{did}/capture/{mauvais}"
        r = _api("GET", chemin)
        assert r.status_code in (400, 404), (mauvais, r.status_code)
        assert "json" in r.headers.get("content-type", ""), \
            f"{mauvais} rend {r.headers.get('content-type')} — le catch-all SPA"
        assert not r.text.lstrip().startswith("<")
    CC.delete_deck(did)


def test_un_tmp_de_la_fenetre_d_ecriture_n_est_jamais_servi():
    """LE CAS SE FABRIQUE : on POSE un `.tmp` à la main, comme la fenêtre
    d'écriture en laisse un, et on demande la porte. Sans liste blanche de
    noms FINAUX, un `?nom=source_recto.png.tmp` servirait un fichier en cours
    d'écriture — c'est-à-dire une image tronquée présentée comme la capture."""
    did = _deck()
    d = CT.deck_dir(did, create=True) / "capture"
    d.mkdir(parents=True, exist_ok=True)
    (d / "source_recto.png.tmp").write_bytes(_carte(40, 56)[:200])
    r = _api("GET", f"/api/cards/{did}/capture/source_recto.png.tmp")
    assert r.status_code in (400, 404), r.status_code
    assert (d / "source_recto.png.tmp").is_file(), "le test n'a rien prouvé"
    CC.delete_deck(did)


def test_un_fichier_absent_ou_un_deck_inconnu_sont_NOMMES():
    did = _deck()
    r = _api("GET", f"/api/cards/{did}/capture/source_recto.png")
    assert r.status_code == 404
    assert "capture" in r.json()["detail"].lower(), r.json()["detail"]
    for faux in ("deck_00000000", "pas_un_did"):
        r = _api("GET", f"/api/cards/{faux}/capture/source_recto.png")
        assert r.status_code in (400, 404), (faux, r.status_code)
        assert "json" in r.headers.get("content-type", "")
    r = _post("deck_00000000", _carte(40, 56), "recto")
    assert r.status_code == 404, r.status_code
    CC.delete_deck(did)


# ═══════════════════════ jamais 500 ═════════════════════════════════════════

def test_jamais_500_quoi_qu_on_envoie():
    """Spec §8. Le corps est BRUT : tout ce qui n'est pas une image doit
    ressortir en refus nommé, jamais en trace de pile."""
    did = _deck()
    corps = [b"{\"pas\": \"une image\"}", b"\x00\x01\x02\x03",
             b"GIF89a" + b"\x00" * 40, _carte(20, 28)[:60],
             "des accents é à".encode("utf-8"),
             b"\x89PNG\r\n\x1a\n" + b"\xff" * 300]
    for c in corps:
        for side in (None, "recto", "verso", "milieu"):
            r = _post(did, c, side)
            assert r.status_code != 500, (c[:12], side, r.text[:200])
            assert r.status_code in (400, 413), (c[:12], side, r.status_code)
            assert "json" in r.headers.get("content-type", "")
    CC.delete_deck(did)


def test_les_refus_sont_TOUS_en_francais():
    """La doctrine des refus nommés vaut pour la pièce entière : on balaie les
    `HTTPException` de la source et on exige un message, en français, qui ne
    soit pas un mot-clé technique nu."""
    src = pathlib.Path(CP.__file__).read_text(encoding="utf-8")
    messages = re.findall(r'HTTPException\(\s*\d{3},\s*(?:f?")([^"]{6,})',
                          src)
    assert len(messages) >= 5, messages
    for m in messages:
        # `[^\W\d_]` = « une lettre », accents compris — un `[a-z]` couperait
        # « Côté » en deux et ferait échouer le test sur du français correct.
        assert re.search(r"[^\W\d_]{3,}\s+[^\W\d_]{2,}", m), m
        assert not re.match(r"^[A-Z][a-z]+ [a-z]+ (is|not|must)\b", m), m


# ═══════════════════════ l'écran, ce qu'on peut lire d'ici ══════════════════

def test_l_ecran_n_a_AUCUN_painter_et_ne_sort_pas_de_chez_lui():
    """§9.4 : P10 ne dessine pas la carte. Et son panneau ne s'adresse qu'au
    sous-arbre `capture` — un `M.patch` d'une autre pièce serait une écriture
    hors jeton (le CORE la refuserait, mais elle ne doit pas être écrite)."""
    js = JS.read_text(encoding="utf-8")
    assert js.lstrip().startswith("/*") or js.lstrip().startswith('"use strict"')
    assert 'painters: []' in js.replace('painters:[', 'painters: [')
    assert re.search(r'id:\s*"capture"', js)
    for interdit in ("CF.patch(", "CF.api", "CF.setCards", "CF.setFormat"):
        assert interdit not in js, interdit
    css = CSS.read_text(encoding="utf-8")
    assert ".cf-capture" in css


def test_le_bouton_de_la_galerie_ne_promet_plus_la_phase_4():
    """Le placeholder honnête (`core.js:galImport`) devait mourir le jour où
    la pièce existe : un bouton qui explique qu'il ne fait rien alors que le
    panneau est là serait devenu un mensonge à l'envers."""
    core = (REPO / "frontend" / "cardforge" / "js" / "core.js") \
        .read_text(encoding="utf-8")
    i = core.index("function galImport(")
    corps = core[i:core.index("\n  }", i)]
    assert "phase 4" not in corps, corps
    assert 'show("capture")' in corps, corps


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
