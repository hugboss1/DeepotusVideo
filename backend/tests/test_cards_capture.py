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
LES DEUX RONDES DE MUTATION. Le principe ne bouge pas : on REMET le défaut,
on joue le contrôle qui doit le voir, on restaure. Un contrôle qui reste vert
sur le défaut restauré ne garde rien.

Ronde 1 (livraison) — 5 gardes cassées, 5 vues : `_side_or_400` sans son test
d'appartenance ; `FILE_RE` privée de son ancre finale ; écriture directe au
lieu de tmp + replace ; plafond de trame élargi ; `capture` retiré de
`MODULE_IDS` (4 contrôles d'un coup).

Ronde 2 (corrections) — 19 défauts remis, 18 vus :
  · brouillon PARTAGÉ + replace nu (le 500 en concurrence) ......... ROUGE
  · brouillon partagé seul ......................................... ROUGE
  · `except DecompressionBombError` retiré (413 -> 400) ............ ROUGE
  · `$` + `.match` remis ENSEMBLE (le $-newline) ................... ROUGE
  · service remis à la racine (`GET /{nom}`) ....................... ROUGE
  · mébipixels réétiquetés « millions » ............................ ROUGE
  · LANCZOS -> NEAREST (le témoin de la ronde 1, FERMÉ) ............ ROUGE
  · horodatage en secondes ......................................... ROUGE
  · `HTTPException` à message anglais ajoutée ...................... ROUGE
  · tout 404 traduit en « backend absent » (JS) .................... ROUGE
  · `effacements()` : garde neutralisée, puis INVERSÉE (JS) ........ ROUGE
  · `accept="image/*"` remis (JS) .................................. ROUGE
  · `img.onerror` renommé d'une lettre (JS) ........................ ROUGE
  · plafond réécrit en toutes lettres dans une phrase (JS) ......... ROUGE
  · `capture` retiré du lint ; `<script>` retiré d'index.html ...... ROUGE
  · le test du meta.json abîmé qui ne nettoie plus son épave ....... ROUGE

ET LE TÉMOIN QUI SURVIT, AVOUÉ — c'en est un NOUVEAU : celui de la ronde 1
(LANCZOS) est fermé par `test_la_reduction_FILTRE_vraiment…`. Retirer
`_replace_avec_patience` SEUL, en gardant le brouillon unique, n'est vu
qu'environ une fois sur deux : sans la reprise, la course rend
{200: 33, 409: 7} sur ce poste, mais parfois 37 ou 38 succès — au-dessus du
plancher de 90 % du contrôle. Le seuil qui l'attraperait à coup sûr (exiger
40/40) serait FAUX DANS L'AUTRE SENS : une machine chargée rendrait un 409
légitime et le contrôle rougirait sans faute. Entre un trou connu et une
intermittence rouge, on garde le trou et on l'écrit. Le défaut GRAVE — le
brouillon partagé, celui qui rendait des 500 et ne laissait AUCUN fichier —
est vu, lui, à tous les coups.

Run : .\\scripts\\run-tests.ps1 -Filter cards_capture
"""
import asyncio
import io
import json
import os
import pathlib
import re
import shutil
import struct
import subprocess
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
from PIL import Image, ImageDraw                                 # noqa: E402

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
    b = max(2, min(w, h) // 24)
    # DESSINÉ PAR PRIMITIVE, pas pixel par pixel : la boucle Python coûtait
    # 2,7 millions d'itérations pour une carte de scan réaliste, et le test de
    # concurrence en fabrique quarante.
    ImageDraw.Draw(im).rectangle(
        [b, b, w - b - 1, h - b - 1],
        fill=(teinte, teinte - 4 if teinte > 4 else 0, teinte // 2))
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


def _get(did: str, nom: str):
    """Le service passe sous /file/ — voir `capture.get_file` : à la racine du
    préfixe, le joker avalait toutes les routes GET des tâches suivantes."""
    return _api("GET", f"/api/cards/{did}/capture/file/{nom}")


def _en_parallele(appels):
    """DE LA VRAIE CONCURRENCE, pas une boucle. `asyncio.gather` sur le même
    transport lance les requêtes ensemble, et l'écriture disque de la route
    part en `asyncio.to_thread` — donc dans de VRAIS threads, exactement là où
    la course se joue. Une boucle séquentielle ne l'aurait jamais reproduite."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=600.0) as c:
            return await asyncio.gather(
                *[c.request(m, p, **kw) for (m, p, kw) in appels])
    return asyncio.run(go())


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
    assert "/api/cards/{did}/capture/file/{nom}" in chemins, chemins[-8:]
    # AVANT le filet attrape-tout : Starlette apparie dans l'ordre. Sans cela
    # POST /capture/card répondrait « Route inconnue ».
    filet = [p for p in chemins if p.endswith("/{rest:path}")]
    if filet:
        assert chemins.index("/api/cards/{did}/capture/card") \
            < chemins.index(filet[0])


def test_le_service_ne_squatte_pas_les_routes_a_venir():
    """LE JOKER `GET /{nom}` À LA RACINE DU PRÉFIXE ÉTAIT UN PIÈGE DE CLASSE :
    Starlette apparie dans l'ordre, donc il aurait avalé `/ai-options` (T3),
    `/rembg` et `/analyse` — et répondu « Fichier inconnu dans le dossier de
    capture » à qui interroge une route qui n'existe pas encore. Le
    diagnostic aurait coûté une demi-tâche à quelqu'un. Sous `/file/`, une
    route absente redevient une route absente."""
    did = _deck()
    for futur in ("ai-options", "rembg", "analyse", "state"):
        r = _api("GET", f"/api/cards/{did}/capture/{futur}")
        assert r.status_code == 404, (futur, r.status_code)
        detail = (r.json() or {}).get("detail", "")
        assert "dossier de capture" not in detail, \
            f"/{futur} est avalé par le service de fichiers : {detail!r}"
        assert "Route inconnue" in detail, (futur, detail)
    CC.delete_deck(did)


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
        assert d["bytes"] > 0
        # L'HORODATAGE EST EN MILLISECONDES : en secondes, deux imports de la
        # même seconde rendaient la même URL d'aperçu et le navigateur
        # resservait l'ancienne image. 1e12 ms = 2001 ; un horodatage en
        # secondes (1,7e9) tomberait ici.
        assert d["stamp"] > 1_000_000_000_000, d["stamp"]
        g = _get(did, nom)
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
    assert _get(did, "source_recto.png").status_code == 200
    assert _get(did, "source_verso.png").status_code == 404
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
    # LE CHIFFRE ANNONCÉ EST JUSTE. `// 1048576` écrivait « 137 millions »
    # pour 144 000 000 pixels — un mébipixel sous le nom d'un million, et un
    # nombre que personne ne pouvait retrouver (le commentaire de la source,
    # vingt lignes plus haut, dit 144). Leçon Mo/Mio de P8, même piège.
    assert "144" in detail, detail
    assert "137" not in detail, detail
    # et rien n'a été écrit
    assert not (CT.deck_dir(did) / "capture" / "source_recto.png").exists()
    CC.delete_deck(did)


def test_une_bombe_QUE_PIL_REFUSE_D_OUVRIR_est_refusee_pour_LA_BONNE_RAISON():
    """AU-DELÀ DE ~179 Mpx (2 x `MAX_IMAGE_PIXELS`), la bibliothèque lève
    `DecompressionBombError` AVANT de rendre la taille — donc avant notre
    contrôle. Écrasé par un `except Exception` générique, ce refus ressortait
    en 400 « Corps illisible : une image PNG/JPEG/WebP est attendue » : le
    message envoie chercher un fichier corrompu là où il n'y a qu'une image
    valide et démesurée. Mesuré sur 20000² (400 Mpx) et 60000² (3,6 Gpx).

    LE MONTAGE EST UN EN-TÊTE, ET C'EST EXACT : `Image.open` tranche sur la
    TAILLE DÉCLARÉE seule, sans lire un octet d'IDAT — la preuve est que le
    même montage à 12000² passe l'ouverture (test voisin) et sort en 413 par
    notre contrôle à nous. Fabriquer 3,6 milliards de pixels réels pour dire
    la même chose coûterait des minutes et des gigaoctets."""
    did = _deck()
    for cote in (20000, 60000):
        bombe = _png_entete_saine_corps_pourri(cote, cote)
        r = _post(did, bombe, "recto")
        assert r.status_code == 413, (cote, r.status_code, r.text[:200])
        detail = r.json()["detail"]
        assert "trop grande" in detail, (cote, detail)
        assert "illisible" not in detail, (cote, detail)
        assert "pixel" in detail.lower(), (cote, detail)
    assert not (CT.deck_dir(did) / "capture" / "source_recto.png").exists()
    CC.delete_deck(did)


def _png_entete_saine_corps_pourri(w: int, h: int) -> bytes:
    """UN PNG QUI MENT À DEUX NIVEAUX : son IHDR déclare w x h honnêtement,
    son IDAT ne se décode pas. C'est le discriminateur DYNAMIQUE de l'ordre
    des gardes — si la taille est contrôlée sur l'en-tête, il sort en 413 ;
    si elle l'est après `load()`, le décodage meurt d'abord et il sort en
    400. Aucun autre montage ne sépare les deux."""
    def chunk(typ: bytes, data: bytes) -> bytes:
        return (struct.pack(">I", len(data)) + typ + data
                + struct.pack(">I", zlib.crc32(typ + data) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 0, 0, 0, 0)
    pourri = b"\x78\x9c" + b"\xff" * 64          # en-tête zlib, suite invalide
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
            + chunk(b"IDAT", pourri) + chunk(b"IEND", b""))


def test_le_controle_de_trame_est_AVANT_le_decodage_ET_CA_SE_MESURE():
    """La preuve était au TEXTE (l'ordre de deux mots dans la source). Elle
    est maintenant au COMPORTEMENT : l'image ci-dessous est indécodable, donc
    un contrôle placé après `load()` répondrait 400 « corps illisible ». Elle
    répond 413 : les dimensions ont été lues et refusées sans qu'un octet de
    trame soit décodé — c'est le seul endroit où ce refus coûte zéro."""
    did = _deck()
    menteur = _png_entete_saine_corps_pourri(12000, 12000)
    assert len(menteur) < 500, "le montage doit rester minuscule"
    from PIL import Image as _I
    with _I.open(io.BytesIO(menteur)) as im:
        assert im.size == (12000, 12000)          # l'en-tête suffit...
        try:
            im.load()
            leve = False
        except Exception:
            leve = True
    assert leve, "le corps devait être indécodable — le montage ne prouve rien"
    r = _post(did, menteur, "recto")
    assert r.status_code == 413, \
        f"413 attendu (en-tête AVANT décodage), reçu {r.status_code} : {r.text[:200]}"
    assert "12000" in r.json()["detail"]
    # ... et le même corps SANS trame démesurée sort bien en 400 : c'est ce
    # qui prouve que le 413 ci-dessus vient de la TAILLE et non du hasard.
    petit = _png_entete_saine_corps_pourri(40, 56)
    r = _post(did, petit, "recto")
    assert r.status_code == 400 and "illisible" in r.json()["detail"], r.text[:200]
    CC.delete_deck(did)


def test_les_HUIT_copies_de_MAX_IMPORT_PX_disent_le_meme_chiffre():
    """La règle 8 interdit à une pièce d'importer le module d'une voisine :
    le plafond d'import est donc RECOPIÉ, et la seule chose qui empêche les
    copies de diverger est ce test. Il en confrontait TROIS sur sept, et son
    commentaire annonçait le contraire — un test qui ment sur sa couverture
    est pire qu'absent. Les huit sont lues SUR LES FICHIERS (les quatre JS ne
    sont importables d'aucune façon depuis Python) ; la ronde en a d'ailleurs
    trouvé une huitième, écrite en prose dans `mod-capture.js`."""
    front = REPO / "frontend" / "cardforge" / "js"
    back = pathlib.Path(CP.__file__).parent
    porteurs = [back / "face.py", back / "frame.py", back / "type.py",
                back / "capture.py", front / "mod-face.js",
                front / "mod-frame.js", front / "mod-type.js",
                front / "mod-capture.js"]
    vus = {}
    for p in porteurs:
        assert p.is_file(), p
        m = re.search(r"MAX_IMPORT_PX\s*=\s*(\d+)",
                      p.read_text(encoding="utf-8"))
        assert m, f"{p.name} ne déclare plus MAX_IMPORT_PX"
        vus[p.name] = int(m.group(1))
    assert len(vus) == 8, vus
    assert set(vus.values()) == {4096}, vus
    assert CP.MAX_IMPORT_PX == 4096
    # ... ET AUCUN 4096 ORPHELIN dans les fichiers de la pièce : un plafond
    # écrit en clair dans une phrase est une copie de plus, que rien ne
    # confronte (c'est exactement ce que la ronde a trouvé).
    for p in (back / "capture.py", front / "mod-capture.js"):
        txt = p.read_text(encoding="utf-8")
        for m in re.finditer(r"4096", txt):
            ligne = txt[txt.rfind("\n", 0, m.start()) + 1:
                        txt.find("\n", m.start())]
            assert "MAX_IMPORT_PX" in ligne, \
                f"{p.name} écrit 4096 hors de sa constante : {ligne.strip()!r}"


def test_une_image_trop_grande_est_REDUITE_a_MAX_IMPORT_PX():
    """4096 px de côté long, mesurés sur le fichier SERVI."""
    did = _deck()
    r = _post(did, _carte(5000, 2000), "recto")
    assert r.status_code == 200, r.text[:300]
    d = r.json()
    assert max(d["w"], d["h"]) == CP.MAX_IMPORT_PX, d
    assert d["h"] == round(2000 * 4096 / 5000), d       # le ratio est tenu
    with Image.open(io.BytesIO(_get(did, "source_recto.png").content)) as im:
        assert im.size == (d["w"], d["h"]), "le fichier ment sur la réponse"
    CC.delete_deck(did)


def _damier(w: int, h: int) -> bytes:
    """Un damier de 1 pixel — le pire cas d'un rééchantillonnage, et le seul
    motif où plus-proche-voisin et filtre séparable donnent des images
    OPPOSÉES au lieu de proches."""
    a = bytes([0, 255] * (w // 2)) + (b"\x00" if w % 2 else b"")
    b = bytes([255, 0] * (w // 2)) + (b"\xff" if w % 2 else b"")
    im = Image.frombytes("L", (w, h),
                         b"".join(a if y % 2 == 0 else b for y in range(h)))
    buf = io.BytesIO()
    im.convert("RGB").save(buf, format="PNG")
    return buf.getvalue()


def test_la_reduction_FILTRE_vraiment_elle_ne_prend_pas_un_pixel_sur_deux():
    """LE TÉMOIN SURVIVANT DE LA PREMIÈRE RONDE, FERMÉ. `Image.LANCZOS`
    remplacé par `Image.NEAREST` ne faisait tomber aucun des 19 contrôles :
    les dimensions et le poids sont identiques, seule la QUALITÉ change — et
    rien ne la mesurait. Il n'a pas fallu l'outillage de T2 pour la mesurer,
    juste le bon sujet : sur un damier de 1 px réduit de 5000 à 4096, un
    filtre séparable MOYENNE (écart-type mesuré 6,0 sur 255) là où le
    plus-proche-voisin REPIQUE le damier (127,5). Le seuil est posé à 40 —
    vingt fois la marge d'un côté, trois fois de l'autre : il attrape la
    substitution sans se briser sur un changement de filtre honnête."""
    did = _deck()
    r = _post(did, _damier(5000, 2000), "recto")
    assert r.status_code == 200, r.text[:200]
    assert r.json()["w"] == CP.MAX_IMPORT_PX, r.json()
    from PIL import ImageStat
    with Image.open(io.BytesIO(_get(did, "source_recto.png").content)) as im:
        ecart = ImageStat.Stat(im.convert("L")).stddev[0]
    assert ecart < 40, \
        (f"écart-type {ecart:.1f} sur le fichier servi : le damier a survécu "
         f"à la réduction, donc aucun filtrage n'a eu lieu")
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


def test_une_ecriture_qui_ECHOUE_ne_laisse_NI_final_NI_brouillon():
    """L'ATOMICITÉ, MESURÉE PLUTÔT QUE LUE. La preuve était au texte (l'ordre
    de `.tmp` et de `replace(` dans la source) : elle ne disait rien de ce qui
    arrive VRAIMENT quand l'écriture meurt. Ici `Image.save` écrit puis lève,
    exactement comme un disque plein ou un verrou : le nom final ne doit pas
    exister (personne ne servira une image tronquée), le brouillon ne doit pas
    rester (il s'accumulerait à chaque incident), et la réponse doit être un
    refus NOMMÉ — pas une trace de pile."""
    from PIL import Image as _I
    did = _deck()
    # LES OCTETS SONT FABRIQUÉS AVANT LE PIÈGE : `_carte` passe elle aussi par
    # `Image.save`, et la poser après le remplacement ferait mourir le test au
    # lieu de la route.
    corps = _carte(60, 84)
    vrai = _I.Image.save

    def _save_qui_meurt(self, fp, *a, **k):
        vrai(self, fp, *a, **k)                  # le brouillon est écrit...
        raise OSError(13, "verrou simule par le test")   # ... puis tout casse

    _I.Image.save = _save_qui_meurt
    try:
        r = _post(did, corps, "recto")
    finally:
        _I.Image.save = vrai
    assert r.status_code != 500, r.text[:300]
    assert r.status_code == 409, (r.status_code, r.text[:300])
    detail = r.json()["detail"]
    assert "verrou simule" in detail, detail
    # LE CHEMIN ABSOLU NE SORT PAS. `str(OSError)` porte le nom du fichier,
    # donc le nom de compte de l'utilisateur — la fuite du gauntlet, à ne pas
    # rejouer dans une réponse HTTP.
    assert "\\" not in detail and "/" not in detail, detail
    assert "olivi" not in detail.lower(), detail
    d = CT.deck_dir(did) / "capture"
    restes = sorted(p.name for p in d.iterdir()) if d.is_dir() else []
    assert restes == [], f"des restes après l'échec : {restes}"
    # et la pièce fonctionne toujours après l'incident
    assert _post(did, _carte(60, 84), "recto").status_code == 200
    CC.delete_deck(did)


def test_VINGT_PAIRES_D_ENVOIS_SIMULTANES_ne_font_AUCUN_500():
    """LE DÉFAUT LE PLUS CHER DE LA PREMIÈRE LIVRAISON, et il ne demandait
    qu'un double-clic : le brouillon s'appelait `source_recto.png.tmp`, LE
    MÊME pour tout le monde. Deux envois simultanés sur le même côté
    écrivaient dans le même fichier et se disputaient le `replace` —
    WinError 32, « le processus ne peut pas accéder au fichier », remonté en
    500. Mesuré avant correction sur 40 requêtes : {200: 36, 500: 4}, soit
    10 %.

    Le test envoie VINGT PAIRES sur le même côté, en vraie concurrence, avec
    des tailles distinctes pour que le gagnant soit identifiable. Ce qui est
    exigé : aucun 500, aucun brouillon abandonné, un fichier final ENTIER —
    celui de l'un des envois, pas un mélange des deux — et la très grande
    majorité des envois SERVIS.

    CE DERNIER POINT EST LE VRAI SEUIL, et il a fallu le mesurer pour
    l'écrire. « Aucun 500 » ne suffisait pas : le brouillon partagé remis en
    place rendait 40 refus 409 sur 40 et NE LAISSAIT AUCUN FICHIER — un
    contrôle qui ne regarde que le code de panne aurait vu là un système
    poli. Mesures sur ce poste, 40 envois simultanés de 1400x1900 :
      · brouillon partagé ............... {409: 40}, dossier VIDE
      · brouillon unique ................ {200: 33, 409: 7}
      · brouillon unique + patience ..... {200: 40} (trois passages)
    Le plancher est posé à 90 % (36/40) : trois fois la marge du pire cas
    mesuré, et infiniment loin du zéro du défaut."""
    did = _deck()
    # DES CARTES DE LA TAILLE D'UN VRAI SCAN. Sur des vignettes de 200 px,
    # l'encodage PNG dure moins d'une milliseconde et la fenêtre de course est
    # trop étroite pour se reproduire : le test restait VERT sur le défaut
    # remis (mesuré). À ~2,6 Mpx, l'écriture dure assez pour que deux threads
    # se croisent — c'est aussi la taille des images que la pièce recevra.
    tailles = [(1400 + 2 * i, 1900 + 2 * i) for i in range(40)]
    appels = [("POST", f"/api/cards/{did}/capture/card?side=recto",
               {"content": _carte(w, h),
                "headers": {"Content-Type": "image/png"}})
              for (w, h) in tailles]
    reps = _en_parallele(appels)
    codes = {}
    for r in reps:
        codes[r.status_code] = codes.get(r.status_code, 0) + 1
    assert 500 not in codes, (codes, [r.text[:160] for r in reps
                                      if r.status_code == 500][:2])
    assert set(codes) <= {200, 409}, codes
    assert codes.get(200, 0) >= 0.9 * len(tailles), \
        f"{codes} : la course mange les envois au lieu de les servir"
    # AUCUN BROUILLON ABANDONNÉ : un `.tmp` par requête, tous consommés.
    d = CT.deck_dir(did) / "capture"
    restes = sorted(p.name for p in d.iterdir())
    assert restes == ["source_recto.png"], restes
    # LE DERNIER GAGNE PROPREMENT : le fichier est une image ENTIÈRE, et sa
    # taille est celle d'un des envois — jamais deux moitiés cousues.
    servi = _get(did, "source_recto.png")
    assert servi.status_code == 200
    with Image.open(io.BytesIO(servi.content)) as im:
        im.load()
        assert im.size in tailles, (im.size, tailles[:3])
    CC.delete_deck(did)


# ═══════════════════════ le service, par liste blanche ══════════════════════

def test_le_GET_sert_par_LISTE_BLANCHE_et_refuse_la_traversee():
    """Un nom de fichier est un IDENTIFIANT, jamais un chemin. Le double
    garde-fou de `deck_dir` protège le `did` ; le nom, lui, n'a que cette
    liste — et elle est close."""
    did = _deck()
    _post(did, _carte(80, 112), "recto")
    for mauvais in ("../meta.json", "..%2fmeta.json", "source_recto.png.tmp",
                    "source_RECTO.png", "meta.json", "source_dos.png",
                    "source_recto.jpg", "", "source_recto",
                    # LE $-NEWLINE, QUATRIÈME OCCURRENCE DE LA LEÇON DU
                    # CHANTIER : en Python, `$` apparie AUSSI juste avant un
                    # saut de ligne final. `source_recto.png%0A` passait donc
                    # la liste blanche d'un motif ancré par `$` + `.match`.
                    # `\\Z` + `fullmatch` ne connaissent que la fin de chaîne.
                    "source_recto.png%0A", "source_recto.png%0D%0A",
                    "source_recto.png%20"):
        chemin = f"/api/cards/{did}/capture/file/{mauvais}"
        r = _api("GET", chemin)
        assert r.status_code in (400, 404), (mauvais, r.status_code)
        assert "json" in r.headers.get("content-type", ""), \
            f"{mauvais} rend {r.headers.get('content-type')} — le catch-all SPA"
        assert not r.text.lstrip().startswith("<")
    CC.delete_deck(did)


def test_la_liste_blanche_REFUSE_le_saut_de_ligne_final():
    """LE $-NEWLINE, QUATRIÈME FOIS SUR CE CHANTIER. En Python, `$` apparie
    aussi JUSTE AVANT un saut de ligne final : `re.match(r"^x\\.png$",
    "x.png\\n")` réussit. Un nom venu d'une URL (`…%0A`) traversait donc la
    liste blanche d'un motif ancré par `$`.

    LE CONTRÔLE EST PRIS SUR LA FONCTION, PAS SUR LA ROUTE, et c'est le point :
    par HTTP le défaut ne se voyait pas — le fichier « source_recto.png\\n »
    n'existe pas sur le disque, donc la route rendait 404 de toute façon et le
    test restait vert sur le motif fautif (mesuré). Le jour où un nom à
    espace-fin ou à point-fin (que Windows, lui, RABOTE en ouvrant le fichier)
    passerait la liste, le 404 deviendrait un 200. La garde se prouve où elle
    est écrite."""
    for mauvais in ("source_recto.png\n", "source_recto.png\r\n",
                    "source_verso.png\n", "source_recto.png ",
                    "source_recto.png.", "source_recto.png\t"):
        assert not CP.FILE_RE.fullmatch(mauvais), repr(mauvais)
        with pytest.raises(Exception) as e:
            CP._name_or_404(mauvais)
        assert getattr(e.value, "status_code", None) == 404, repr(mauvais)
    for bon in ("source_recto.png", "source_verso.png"):
        assert CP._name_or_404(bon) == bon


def test_un_tmp_de_la_fenetre_d_ecriture_n_est_jamais_servi():
    """LE CAS SE FABRIQUE : on POSE un `.tmp` à la main, comme la fenêtre
    d'écriture en laisse un, et on demande la porte. Sans liste blanche de
    noms FINAUX, un `?nom=source_recto.png.tmp` servirait un fichier en cours
    d'écriture — c'est-à-dire une image tronquée présentée comme la capture."""
    did = _deck()
    d = CT.deck_dir(did, create=True) / "capture"
    d.mkdir(parents=True, exist_ok=True)
    (d / "source_recto.png.tmp").write_bytes(_carte(40, 56)[:200])
    # ... et le brouillon RÉEL, qui porte un suffixe unique depuis la ronde.
    (d / f"source_recto.png.{'a' * 32}.tmp").write_bytes(_carte(40, 56)[:200])
    for nom in ("source_recto.png.tmp",
                f"source_recto.png.{'a' * 32}.tmp"):
        r = _api("GET", f"/api/cards/{did}/capture/file/{nom}")
        assert r.status_code in (400, 404), (nom, r.status_code)
    assert (d / "source_recto.png.tmp").is_file(), "le test n'a rien prouvé"
    CC.delete_deck(did)


def test_un_fichier_absent_ou_un_deck_inconnu_sont_NOMMES():
    did = _deck()
    r = _get(did, "source_recto.png")
    assert r.status_code == 404
    assert "capture" in r.json()["detail"].lower(), r.json()["detail"]
    for faux in ("deck_00000000", "pas_un_did"):
        r = _get(faux, "source_recto.png")
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
    soit pas un mot-clé technique nu.

    LE PLANCHER ÉTAIT `>= 5` POUR DOUZE REFUS : un `HTTPException` ajouté
    demain avec un message anglais, ou sans message du tout, ne serait pas
    même compté. Le contrôle est une ÉGALITÉ au nombre de `HTTPException` du
    fichier : tout refus non apparié par la regex fait tomber le test."""
    src = pathlib.Path(CP.__file__).read_text(encoding="utf-8")
    messages = re.findall(r'HTTPException\(\s*\d{3},\s*(?:f?")([^"]{6,})',
                          src)
    combien = len(re.findall(r"\bHTTPException\(", src))
    assert combien >= 8, combien
    assert len(messages) == combien, \
        (f"{combien} refus dans la source, {len(messages)} portent une phrase "
         f"française d'au moins 6 signes")
    # LA MARQUE D'UNE PHRASE ANGLAISE, en liste noire. Le contrôle d'avant
    # exigeait « deux groupes de lettres séparés par une espace » : « Empty
    # body » le satisfaisait sans broncher (mesuré en remettant le défaut).
    # Prouver qu'un texte EST français demanderait un dictionnaire ; refuser
    # les mots qui trahissent l'anglais tient en une ligne et attrape le cas
    # réel — un message écrit à la va-vite dans la langue du framework.
    ANGLAIS = {"the", "is", "are", "not", "must", "empty", "body", "invalid",
               "unknown", "missing", "failed", "error", "request", "required",
               "allowed", "found", "file", "too", "large", "please"}
    for m in messages:
        # `[^\W\d_]` = « une lettre », accents compris — un `[a-z]` couperait
        # « Côté » en deux et ferait échouer le test sur du français correct.
        assert re.search(r"[^\W\d_]{3,}\s+[^\W\d_]{2,}", m), m
        mots = {w.lower() for w in re.findall(r"[A-Za-z]+", m)}
        assert not (mots & ANGLAIS), (sorted(mots & ANGLAIS), m)


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


def _corps_js(nom: str) -> str:
    """Le corps d'une fonction de mod-capture.js, du `function nom(` à
    l'accolade de fin de colonne 2 (l'indentation du module est stable)."""
    js = JS.read_text(encoding="utf-8")
    i = js.index("function " + nom + "(")
    j = js.index("\n  }", i)
    return js[i:j]


def _fonction_js(nom: str) -> str:
    """La fonction ENTIÈRE, accolade fermante comprise — prête à être
    exécutée. `_corps_js` s'arrête juste avant, pour l'inspection."""
    return _corps_js(nom) + "\n  }\n"


def _node(source: str) -> str:
    """Exécute du JS dans node et rend sa sortie. Le harnais QA du lab exige
    déjà node (`qa/test_core_contract.mjs`) ; ici il est OPTIONNEL — sur une
    machine sans node le contrôle se saute plutôt que de rougir pour une
    raison qui n'est pas la sienne."""
    node = shutil.which("node")
    if not node:
        pytest.skip("node absent : la règle ne peut pas être EXÉCUTÉE ici")
    r = subprocess.run([node, "-e", source], capture_output=True, timeout=60)
    assert r.returncode == 0, r.stderr.decode("utf-8", "replace")[:400]
    return r.stdout.decode("utf-8", "replace")


def test_deposer_un_VERSO_n_efface_pas_l_analyse_du_RECTO():
    """DÉCISION DE PLAN (D3 amendé) : l'analyse est une propriété du RECTO.
    Les adoptions (§7.1.5 : illustration, bordure, zones) sont des gestes de
    recto ; le verso est stocké pour l'objet 3D et le dos (§6.2ter). La
    première livraison remettait l'analyse à zéro à CHAQUE dépôt : importer
    son verso effaçait donc les mesures du recto, sans un mot.

    LA RÈGLE EST EXÉCUTÉE, PAS LUE. La première écriture de ce contrôle
    lisait la forme du code (« la garde est là, l'effacement vient après ») :
    un `|| true` glissé dans la garde la laissait verte — mesuré. La décision
    vit donc dans une fonction PURE de trois lignes, que ce test extrait de
    la vraie source et fait tourner dans node."""
    fn = _fonction_js("effacements")
    sortie = _node(fn + """
      const dump = (s) => JSON.stringify(effacements(s));
      console.log(dump("recto") + "|" + dump("verso") + "|" + dump("milieu"));
    """)
    recto, verso, autre = sortie.strip().split("|")
    recto = json.loads(recto)
    assert json.loads(verso) == {}, f"un verso efface : {verso}"
    assert json.loads(autre) == {}, autre
    assert recto.get("analyzed", "absent") is None, recto
    for k in ("border", "boxes", "bg", "palette", "layers"):
        assert k in recto, (k, recto)
    # ... et l'écran le DIT : une asymétrie muette serait une surprise.
    js = JS.read_text(encoding="utf-8")
    assert re.search(r"analyse[^\n]{0,80}recto", js, re.I), \
        "aucune phrase d'écran n'explique que l'analyse porte sur le recto"


def test_l_ecran_distingue_UNE_ROUTE_ABSENTE_d_un_REFUS_NOMME():
    """Le CORE a déjà nommé ce bug et payé son remède (`core.js:jsonNamed`,
    §9bis) : traduire TOUT 404 en « backend absent » fait déclarer le domaine
    éteint parce qu'un JEU a été supprimé. `capture.py` rend précisément un
    404 « Deck introuvable » AVANT de lire le corps — un jeu effacé dans un
    autre onglet aurait donc affiché « backend absent : l'import exige
    /api/cards ». La question se tranche sur le TYPE DE RÉPONSE, pas sur le
    code : du HTML = pas de route, du JSON = le backend parle."""
    corps = _corps_js("upload")
    assert "content-type" in corps.lower(), corps[-700:]
    assert "json" in corps, corps[-700:]
    assert "resp.status === 404" not in corps, \
        "le 404 est encore traduit en aveugle en « route absente »"


def test_l_ecran_ne_promet_que_les_formats_que_PIL_sait_ouvrir():
    """`accept="image/*"` ouvrait le sélecteur sur HEIC, SVG, AVIF, TIFF —
    que la route refuse en 400 « corps illisible ». Un filtre de fichiers est
    une PROMESSE : il ne doit proposer que ce qui passe."""
    js = JS.read_text(encoding="utf-8")
    m = re.search(r'accept="([^"]+)"', js)
    assert m, "le champ de dépôt ne filtre plus rien"
    assert m.group(1) == "image/png,image/jpeg,image/webp", m.group(1)


def test_l_apercu_ne_peut_pas_echouer_en_silence():
    """Gotcha connu du projet (vignettes du dock, 2026-08) : une `<img>` sans
    `onerror` qui perd son fichier laisse la DERNIÈRE image affichée, ou un
    cadre vide, et l'écran continue d'annoncer « capture déposée ». Le PNG
    peut disparaître (dossier nettoyé, jeu dupliqué à moitié) : l'échec doit
    se voir."""
    js = JS.read_text(encoding="utf-8")
    # `"onerror" in js` était vrai d'un `img.onerrorX` — un contrôle qui se
    # contente d'un mot ne voit pas une faute de frappe. L'AFFECTATION est ce
    # qui branche le garde-fou : c'est elle qu'on exige.
    assert re.search(r"\bimg\.onerror\s*=\s*(\(|function)", js), \
        "aucun garde-fou branché sur le chargement de l'aperçu"


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
