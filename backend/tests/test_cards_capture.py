# -*- coding: utf-8 -*-
"""Card Forge — P10 « Import » (id de module `capture`). Les seuils, mesurés.

CE QUE CE FICHIER TIENT : l'ADMISSION d'une image de carte, le SERVICE des
fichiers du dossier `capture/` (T1), et L'ANALYSE LOCALE — bordure, zones,
fond, palette — mesurée sur des CARTES DE SYNTHÈSE À VÉRITÉ CONNUE (T2,
spec §9.1). Le test POSE une bordure de x mm, trois cartouches, un fond ; il
exige que l'analyse les retrouve à une tolérance CHIFFRÉE ET ÉCRITE DANS
L'ASSERTION — une tolérance qui ne se lit nulle part est une tolérance qu'on
élargit en silence le jour où le test rougit.

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
     inconnu, nom inconnu, image pathologique — chacun a son refus nommé ou
     son relevé DÉGRADÉ AVOUÉ.
  6. L'ANALYSE COURT SUR LE RECTO STOCKÉ, GRATUITEMENT. Pas de corps, pas de
     réseau, pas de fournisseur : la source est balayée pour qu'aucun appel
     payant ne s'y glisse à T3. Elle est REJOUABLE, et déposer un verso ne
     l'efface pas (D3 amendé).
  7. CHAQUE CONFIANCE A UN CAS CONNU OÙ ELLE S'EFFONDRE, et il est joué :
     bordure irrégulière -> régularité en berne ; recto flou -> netteté en
     berne ; fond dégradé -> refus motivé portant sa mesure. Un chiffre de
     confiance qui ne peut pas être bas est un chiffre qui ment (clôture T1).

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

Ronde 3 (T2, l'analyse) — 20 défauts remis, 20 vus :
  · seuil de refus du fond mis à zéro .............................. ROUGE
  · `_clamp01` qui rend toujours 1 (la confiance ne bouge plus) .... ROUGE
  · clamp retiré, confiance libre de dépasser 1 .................... ROUGE
  · échelle prise sur la HAUTEUR au lieu de la largeur ............. ROUGE
  · échelle en dur (0,1 mm/px) au lieu du format ................... ROUGE
  · front = la PLUS HAUTE marche au lieu de la PREMIÈRE ............ ROUGE
  · plancher de front abaissé à 1 (tout dégradé devient bordure) ... ROUGE
  · rayon de coin sondé à MI-BANDE (les huit sondes) ............... ROUGE
  · fusion des boîtes désactivée ................................... ROUGE
  · retrait de bordure supprimé (l'anneau redevient une zone) ...... ROUGE
  · plancher d'étendue supprimé (le grain devient du dessin) ....... ROUGE
  · 404 sans recto remplacé par un relevé vide ..................... ROUGE
  · le prix recopié dans la phrase d'option IA ..................... ROUGE
  · les pixels retraversent la frontière (`border.px` revient) ..... ROUGE
  · une clé de mesure disparaît du schéma de l'écran (JS) .......... ROUGE
  · `effacements` oublie une clé de mesure (JS) .................... ROUGE
  · `estNombre` relâché : `Number(null)` redevient zéro (JS) ....... ROUGE
  · `analyser()` relit la réponse à la main (JS) ................... ROUGE
  · le verrou BUSY saute sur `analyser()` (JS) ..................... ROUGE
  · les boîtes placées au jugé, sans l'échelle (JS) ................ ROUGE

Ronde 4 (T2, corrections de revue) — 19 défauts remis, 19 vus :
  · la bande exclue n'est plus nommée dans les notes .............. ROUGE
  · plus aucune boîte n'est marquée `tronquee` .................... ROUGE
  · TOUTES les boîtes sont marquées `tronquee` (le drapeau qui
    ne discrimine plus) ............................................ ROUGE
  · la bande n'est plus publiée en mm ............................. ROUGE
  · le relevé n'initialise plus `zones_bande_mm` (la clé manque
    quand une détection LÈVE) ...................................... ROUGE
  · `epaisseurs_mm` redevient une liste triée par taille .......... ROUGE
  · la note « profil texturé » disparaît .......................... ROUGE
  · `_front` ne distingue plus texture et aplat ................... ROUGE
  · le rayon n'est plus corrigé du biais de rangée ................ ROUGE
  · l'option IA proposée même sans sujet à détourer ............... ROUGE
  · le seuil de silence du ratio revient à zéro ................... ROUGE
  · le 503 de dépendance absente redevient un 500 ................. ROUGE
  · les lignes du fond reprennent l'ordre fixe (JS) ............... ROUGE
  · les bornes de couverture ne sont plus écrites (JS) ............ ROUGE
  · `divergence` ne compare plus rien (JS) ........................ ROUGE
  · `core:geom` MIS EN COMMENTAIRE (JS) ........................... ROUGE
  · `peutIncruster` oublie l'échelle (JS) ......................... ROUGE
  · `panne()` ne voit plus le rejet réseau (JS) ................... ROUGE
  · `effacements` oublie `zones_bande_mm` (JS) .................... ROUGE

DEUX DE CES DIX-NEUF SONT DES TROUS QUE LA RONDE A OUVERTS, PAS FERMÉS, et
c'est ce qui les rend intéressants :
  · `core:geom` entouré de `/* */` laissait le contrôle VERT — il cherchait
    du code par son TEXTE, et un texte en commentaire est encore du texte.
    Les recherches de code passent désormais par `_code_js`, qui dépouille.
  · retirer `zones_bande_mm` de l'initialisation du relevé ne se voyait sur
    aucun chemin heureux : la clé est réécrite juste après. Elle ne manque
    que si la détection LÈVE — un chemin gardé que rien n'exécutait. Il l'est
    maintenant (`test_une_DETECTION_QUI_LEVE…`), en faisant mourir `_grille`.

ET LES TÉMOINS QUI SURVIVENT À LA RONDE 3, AVOUÉS ET MESURÉS. Six réglages
peuvent bouger sans qu'aucun contrôle ne rougisse, et ce n'est pas un oubli
(le septième, `BORD_FRONT_RATIO`, a été RETOURNÉ par la ronde — voir plus
bas) :

  · `ZONE_SOUS` (8 pixels de travail par bloc) de 4 à 24 — les trois boîtes
    restent trouvées et appariées dans tout cet intervalle. C'est le témoin
    de classe LANCZOS de la ronde 1 : un réglage de COÛT et de finesse, dont
    la dégradation est graduelle et n'a pas de seuil honnête à épingler.
  · `ZONE_MIN_BLOCS` (2) et `ZONE_MAX_BOITES` (12) — des réglages de LISIBILITÉ
    du relevé. Les fabriquer en test demanderait une carte à quarante taches
    d'un bloc, qui ne ressemble à aucun import réel.
  · `BORD_MIN_BORDS` (2) abaissé à 1 — le facteur n/4 de la confiance plafonne
    déjà une « bordure » d'un seul bord à 0,25, donc l'écran la donne pour ce
    qu'elle vaut. Le garde-fou est une ceinture, pas la bretelle.
  · `BORD_MARGE` (20 % de chaque extrémité) ramenée à 2 % — mesuré sur des
    coins de 40, 90 et 140 px : l'épaisseur, la confiance et le rayon sont
    IDENTIQUES. La marge protège d'un cas plus dur que tout ce qu'on sait
    fabriquer sans deviner ; elle reste, avouée comme non gardée.
  · `asyncio.to_thread` retiré de la route — l'analyse bloquerait la boucle
    d'événements. Aucun test en-processus ne peut le voir : le transport ASGI
    du banc joue tout dans la même boucle de toute façon.

LE TÉMOIN QUI N'EN ÉTAIT PAS UN — `BORD_FRONT_RATIO`, retourné par la ronde 4.
L'aveu de la ronde 3 disait que ce rapport ne peut pas mordre sur une carte
(un fondu monotone ne cumule que ~5 de marche médiane) et qu'il ne mord que
sur une image minuscule. Re-mesuré, C'EST L'INVERSE : sur un profil OSCILLANT
— des rayures de 2 px — la marche médiane vaut 455 et le plancher passe de 40
à 1824, donc le rapport décide seul ; sur une image de 40 x 56, la marche
médiane vaut ZÉRO et il ne joue aucun rôle. Ce qu'il attrape est une bordure à
filets fins ou un scan tramé, et ce refus-là a maintenant SA note et SON
contrôle (`test_une_bordure_TEXTUREE…`). Leçon : un aveu qui explique pourquoi
un garde-fou ne peut pas servir mérite la même mesure qu'une affirmation de
succès — celui-ci était une hypothèse écrite au présent.

ET LE TÉMOIN DE LA RONDE 2, AVOUÉ — c'en est un NOUVEAU : celui de la ronde 1
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


# ── les cartes de SYNTHÈSE, et la vérité qu'on y pose (spec §9.1) ───────────
#
# Le poste de mesure de toute cette section : un poker_eu (63 x 88 mm) rendu à
# 630 x 880 px, soit EXACTEMENT 0,1 mm par pixel. Ce chiffre rond n'est pas de
# la coquetterie — il rend la vérité posée lisible en millimètres sans
# arrondi intermédiaire : une bordure de 26 px EST une bordure de 2,6 mm.
SYNTH_W, SYNTH_H = 630, 880
SYNTH_MM_PX = 63.0 / SYNTH_W          # 0,1 mm/px
OR = (216, 183, 106)                  # la bande
NOIR = (20, 18, 12)                   # l'intérieur


def _synth(bord_px: int = 26, boites=(), bord=OR, fond=NOIR,
           w: int = SYNTH_W, h: int = SYNTH_H, rayon: int = 0,
           dehors=(255, 255, 255)):
    """Une carte à VÉRITÉ CONNUE : bande de `bord_px`, intérieur uni, et les
    cartouches qu'on veut, posés au pixel."""
    im = Image.new("RGB", (w, h), dehors)
    d = ImageDraw.Draw(im)
    if rayon:
        d.rounded_rectangle([0, 0, w - 1, h - 1], radius=rayon, fill=bord)
    else:
        d.rectangle([0, 0, w - 1, h - 1], fill=bord)
    if bord_px:
        d.rectangle([bord_px, bord_px, w - bord_px - 1, h - bord_px - 1],
                    fill=fond)
    for (x, y, bw, bh, col) in boites:
        d.rectangle([x, y, x + bw - 1, y + bh - 1], fill=col)
    return im


def _pngs(im) -> bytes:
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


# Trois cartouches POSÉS, aux places d'une vraie carte : un bandeau de titre,
# une boîte de capacité, un badge de camp. Leurs coordonnées en px sont la
# vérité ; leurs millimètres s'en déduisent par SYNTH_MM_PX et rien d'autre.
TROIS_BOITES_PX = ((80, 60, 470, 70), (80, 620, 470, 150), (60, 200, 90, 90))
TROIS_COULEURS = ((230, 210, 150), (200, 190, 170), (240, 230, 120))
TROIS = tuple((x, y, w, h, c) for (x, y, w, h), c
              in zip(TROIS_BOITES_PX, TROIS_COULEURS))


def _analyse(did: str):
    return _api("POST", f"/api/cards/{did}/capture/analyse")


def _pose_et_analyse(im, fmt: str | None = None):
    """Le geste réel, de bout en bout : on dépose, puis on demande la mesure.
    Le relevé est rendu avec le `did` pour que l'appelant range son deck."""
    did = (CC.create_deck("import", {"fmt": fmt})["id"] if fmt else _deck())
    r = _post(did, _pngs(im), "recto")
    assert r.status_code == 200, r.text[:300]
    a = _analyse(did)
    assert a.status_code == 200, (a.status_code, a.text[:400])
    return did, a.json()


def _iou(a, b) -> float:
    """Intersection sur union de deux boîtes [x, y, w, h]."""
    ix = max(0.0, min(a[0] + a[2], b[0] + b[2]) - max(a[0], b[0]))
    iy = max(0.0, min(a[1] + a[3], b[1] + b[3]) - max(a[1], b[1]))
    inter = ix * iy
    if not inter:
        return 0.0
    return inter / (a[2] * a[3] + b[2] * b[3] - inter)


def _scan_js(src: str):
    """(littéraux de chaîne, source SANS ses commentaires).

    Un automate de vingt lignes, et il en faut un pour DEUX raisons :

      · les commentaires de ce chantier sont en français, donc pleins
        d'apostrophes, et toute recherche de `'…'` par expression régulière
        prend un commentaire pour une chaîne ;
      · un contrôle qui cherche du CODE par son texte est satisfait par ce
        même code MIS EN COMMENTAIRE. Mesuré : l'écoute de `core:geom`
        neutralisée en l'entourant de `/* */` laissait le contrôle vert. Un
        garde-fou qu'on peut désactiver sans faire rougir un test n'est pas
        gardé — on cherche donc dans le code dépouillé.
    """
    chaines, code, i, n = [], [], 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and i + 1 < n and src[i + 1] == "*":
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif c == "/" and i + 1 < n and src[i + 1] == "/":
            j = src.find("\n", i)
            i = n if j < 0 else j + 1
        elif c in "\"'`":
            j, buf = i + 1, []
            while j < n and src[j] != c:
                if src[j] == "\\" and j + 1 < n:
                    buf.append(src[j + 1])
                    j += 2
                    continue
                buf.append(src[j])
                j += 1
            chaines.append("".join(buf))
            code.append(src[i:min(j + 1, n)])
            i = j + 1
        else:
            code.append(c)
            i += 1
    return chaines, "".join(code)


def _chaines_js(src: str) -> list:
    return _scan_js(src)[0]


def _code_js(src: str) -> str:
    return _scan_js(src)[1]


def _cles_du_schema() -> set:
    """Les clés du bloc `state:` de mod-capture.js — le SCHÉMA que `patchAs`
    fait respecter. Lues sur le fichier : le JS n'est importable d'aucune
    façon depuis Python, et c'est cette frontière-là qui casse en silence."""
    js = JS.read_text(encoding="utf-8")
    i = js.index("state: {")
    bloc = js[i:js.index("\n    },", i)]
    return set(re.findall(r"^\s{6}([a-z_]+):", bloc, re.M))


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
    vit donc dans une fonction PURE, que ce test extrait de la vraie source
    et fait tourner dans node.

    ET LA LISTE DES CLÉS N'EST PAS RECOPIÉE ICI (renfort T2) : elle se DÉRIVE
    du schéma déclaré par le module. Le contrôle nommait cinq clés en dur, et
    T2 en a ajouté trois (`echelle`, `ecart_ratio`, `notes`) — une mesure
    oubliée dans `effacements` aurait survécu à un nouveau recto, c'est-à-dire
    aurait décrit une image qui n'est plus sur le disque, et le test serait
    resté vert. Toute clé de mesure ajoutée demain tombe désormais ici."""
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
    # `sources` est le SEUL sous-arbre qu'un dépôt ne doit pas effacer (c'est
    # lui qu'il vient d'écrire) ; tout le reste décrit la mesure.
    mesure = _cles_du_schema() - {"sources"}
    manquantes = mesure - set(recto)
    assert not manquantes, \
        (f"un nouveau recto laisserait {sorted(manquantes)} en place : ces "
         f"mesures décriraient une image qui n'est plus sur le disque")
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
    code : du HTML = pas de route, du JSON = le backend parle.

    LA RÈGLE VIT À UN SEUL ENDROIT (renfort T2). Elle était écrite dans
    `upload()` ; `analyser()` est arrivé avec le même besoin, et une règle
    recopiée est une règle qui dérive — le second appel aurait pu perdre la
    nuance sans que rien ne rougisse. Le contrôle exige donc la règle dans
    `lireJson` ET son usage par les DEUX appels."""
    corps = _corps_js("lireJson")
    assert "content-type" in corps.lower(), corps[-700:]
    assert "json" in corps, corps[-700:]
    assert "resp.status === 404" not in corps, \
        "le 404 est encore traduit en aveugle en « route absente »"
    for appel in ("upload", "analyser"):
        c = _corps_js(appel)
        assert "lireJson(" in c, \
            f"{appel}() lit la réponse à la main : la règle va diverger"
    # ... et l'échec de route reste NOMMÉ, pas silencieux.
    assert "missing" in _corps_js("panne")


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


# ═══════════════════════ T2 — l'analyse, à vérité connue ════════════════════

def test_l_analyse_SANS_RECTO_est_un_404_qui_dit_quoi_faire():
    """L'analyse court sur le recto STOCKÉ : sans recto, il n'y a rien à
    mesurer, et le refus doit envoyer déposer — pas annoncer une panne."""
    did = _deck()
    r = _analyse(did)
    assert r.status_code == 404, (r.status_code, r.text[:300])
    detail = r.json()["detail"]
    assert "recto" in detail.lower(), detail
    assert re.search(r"dépos", detail, re.I), detail
    # ... et un verso SEUL ne suffit pas non plus : la mesure est du recto.
    _post(did, _pngs(_synth()), "verso")
    r = _analyse(did)
    assert r.status_code == 404, (r.status_code, r.text[:200])
    CC.delete_deck(did)


def test_l_analyse_ne_DEPENSE_rien_et_ne_sort_pas_de_la_machine():
    """« GRATUIT, PIL pur, AUCUN appel réseau/fournisseur » (plan T2). Le jour
    où T3 branchera le détourage payant, ce sera SOUS UNE AUTRE ROUTE : celle
    -ci reste l'analyse qu'on peut relancer sans y penser.

    LE BALAYAGE EST SUR L'ARBRE SYNTAXIQUE, PAS SUR LE TEXTE. La première
    écriture cherchait des sous-chaînes et rougissait sur un COMMENTAIRE de
    T1 qui nomme les routes futures — un test qui interdit de parler d'une
    chose n'est pas un test qui interdit de la faire. Ici on lit les IMPORTS
    réels : une dépendance payante ne peut entrer que par là."""
    import ast
    arbre = ast.parse(pathlib.Path(CP.__file__).read_text(encoding="utf-8"))
    modules = set()
    for n in ast.walk(arbre):
        if isinstance(n, ast.Import):
            modules.update(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            modules.add(n.module or "")
            modules.update(f"{n.module or ''}.{a.name}" for a in n.names)
    racines = {m.split(".")[0] for m in modules}
    for interdit in ("httpx", "requests", "urllib", "aiohttp", "fal_client",
                     "openai", "rembg", "replicate", "socket", "http"):
        assert interdit not in racines, \
            (f"« {interdit} » est IMPORTÉ par la pièce : l'analyse doit "
             f"rester gratuite et locale ({sorted(racines)})")
    # Les seules dépendances de calcul, et elles sont locales.
    assert "app.services.pbr_service" in modules, sorted(modules)
    assert "app.services.pixel_ops.chroma_key" in modules, sorted(modules)


def test_les_PRIMITIVES_reutilisees_existent_encore_chez_elles():
    """L'analyse emprunte `_micro_contrast` (PRIVÉE), `stats` et `chroma_key`
    à deux services voisins. Un renommage là-bas ferait tomber la route en
    production avec une trace de pile ; ici il fait rougir un test qui NOMME
    le contrat emprunté."""
    from app.services.pbr_service import _micro_contrast, stats
    from app.services.pixel_ops import chroma_key
    im = Image.new("L", (32, 32), 128)
    assert _micro_contrast(im, 1.5).size == (32, 32)
    s = stats(im)
    assert {"mean", "median", "p5", "p95", "span"} <= set(s)
    out, ok = chroma_key(Image.new("RGB", (40, 40), (10, 20, 30)))
    assert out.mode == "RGBA" and isinstance(ok, bool)


def test_une_BORDURE_POSEE_en_mm_est_RETROUVEE_a_tolerance_chiffree():
    """LE CŒUR DE §9.1 : le test pose x mm de bordure, l'analyse rend x.

    TOLÉRANCE : 1,5 pixel, soit 0,15 mm sur ce poste (630 px pour 63 mm). Ce
    n'est pas un chiffre de confort — c'est la RÉSOLUTION de la mesure : le
    front est localisé à la rangée près, et une rangée d'hésitation (le côté
    d'un bord anticrénelé) est le pire cas physique. Une tolérance plus large
    laisserait passer une erreur d'échelle ; plus étroite, elle rougirait sur
    une image ré-encodée."""
    tol = 1.5 * SYNTH_MM_PX
    for bord_px in (13, 26, 40):
        did, a = _pose_et_analyse(_synth(bord_px))
        b = a["border"]
        attendu = bord_px * SYNTH_MM_PX
        assert b, f"bordure de {bord_px} px non vue : {a['notes']}"
        assert abs(b["mm"] - attendu) <= tol, \
            (f"bordure posée {attendu:.3f} mm, mesurée {b['mm']} mm "
             f"(tolérance {tol:.3f} mm)")
        # ... et la COULEUR de la bande est celle qu'on a peinte, à l'octet.
        assert b["color"] == "#d8b76a", (b["color"], bord_px)
        assert 0.0 <= b["confidence"] <= 1.0, b
        CC.delete_deck(did)


def test_une_bordure_IRREGULIERE_a_une_confiance_PLUS_BASSE():
    """Le chiffre doit BOUGER DANS LE BON SENS. Bandes posées de 1,0 / 2,6 /
    4,0 / 6,0 mm : la régularité tombe à 1 - (6-1)/6 = 0,167, et la confiance
    la suit. Sans cette exigence, une « confiance » constante à 1 passerait
    tous les autres contrôles de ce fichier."""
    did, reg = _pose_et_analyse(_synth(26))
    CC.delete_deck(did)
    irr = Image.new("RGB", (SYNTH_W, SYNTH_H), OR)
    # gauche 10, haut 40, droite 26, bas 60 px
    ImageDraw.Draw(irr).rectangle(
        [10, 40, SYNTH_W - 27, SYNTH_H - 61], fill=NOIR)
    did, a = _pose_et_analyse(irr)
    a, b = a["border"], reg["border"]
    assert a and b
    assert a["confidence"] < b["confidence"], (a["confidence"], b["confidence"])
    assert a["confidence"] < 0.5, a
    # et les quatre épaisseurs mesurées SONT les quatre posées, CHACUNE À SON
    # BORD (gauche 10, haut 40, droite 26, bas 60 px).
    assert a["epaisseurs_mm"] == {"gauche": 1.0, "haut": 4.0,
                                 "droite": 2.6, "bas": 6.0}, a["epaisseurs_mm"]
    CC.delete_deck(did)


def test_un_recto_FLOU_fait_tomber_la_confiance_puis_la_bordure():
    """LA SECONDE PART DE LA CONFIANCE, et son cas connu. Le profil de bord
    est une MOYENNE sur 60 % du bord : elle écrase le grain (un bruit uniforme
    de ±28 par canal laisse la netteté à 0,993 — mesuré). Ce qu'elle n'écrase
    pas, c'est un front ÉTALÉ — la photo floue d'une carte. Mesuré à sigma
    0 / 1 / 3 px : confiance 1,00 -> 0,50 -> 0,167, puis plus de bordure du
    tout à sigma 6 (le front ne domine plus le plancher)."""
    from PIL import ImageFilter
    vues = []
    for sigma in (0, 1, 3):
        im = _synth(26)
        if sigma:
            im = im.filter(ImageFilter.GaussianBlur(sigma))
        did, a = _pose_et_analyse(im)
        assert a["border"], (sigma, a["notes"])
        vues.append(a["border"]["confidence"])
        CC.delete_deck(did)
    assert vues[0] > vues[1] > vues[2], vues
    assert vues[2] < 0.3, vues
    did, a = _pose_et_analyse(_synth(26).filter(ImageFilter.GaussianBlur(6)))
    assert a["border"] is None, a["border"]
    CC.delete_deck(did)


def test_une_carte_SANS_bordure_n_en_publie_AUCUNE_et_le_DIT():
    """« Aucun front trouvé » = bordure ABSENTE du résultat, jamais « 0 mm,
    confiance 1 » (plan D4). Une carte pleine illustration, un dégradé doux :
    la bonne réponse est de se taire et d'expliquer."""
    grad = Image.new("RGB", (SYNTH_W, SYNTH_H))
    d = ImageDraw.Draw(grad)
    for y in range(SYNTH_H):
        d.line([(0, y), (SYNTH_W, y)],
               fill=(int(20 + y * 0.25), 40, int(200 - y * 0.2)))
    did, a = _pose_et_analyse(grad)
    assert a["border"] is None, a["border"]
    assert any("ordure" in n for n in a["notes"]), a["notes"]
    # LE PIÈGE NOMMÉ PAR LE PLAN, épinglé : pas de zéro rassurant.
    assert not isinstance(a["border"], dict), a["border"]
    CC.delete_deck(did)
    # ... et un contraste sous le plancher (L1 = 24 pour un plancher de 40)
    # se tait aussi, alors que L1 = 45 se voit : le plancher est un seuil,
    # pas une opinion.
    for delta, attendu in ((15, True), (8, False)):
        im = Image.new("RGB", (SYNTH_W, SYNTH_H),
                       (120 + delta, 120 + delta, 120 + delta))
        ImageDraw.Draw(im).rectangle(
            [26, 26, SYNTH_W - 27, SYNTH_H - 27], fill=(120, 120, 120))
        did, a = _pose_et_analyse(im)
        assert bool(a["border"]) is attendu, (delta, a["border"], a["notes"])
        CC.delete_deck(did)


def test_les_TROIS_BOITES_POSEES_sont_retrouvees_ET_COMPTEES():
    """La seconde vérité connue de §9.1. Trois cartouches posés au pixel :
    l'analyse doit en rendre TROIS — le compte exact, pas « au moins » — et
    chacun doit recouvrir le sien.

    SEUIL D'APPARIEMENT : IoU >= 0,60. Le plafond n'est pas libre — les
    boîtes sont quantifiées sur une grille de 1,5 mm, donc un cartouche de
    9 x 9 mm mesuré à un bloc près ne PEUT pas dépasser ~0,74 d'IoU. Mesuré
    sur les trois : 0,914 / 0,890 / 0,735. Le seuil est posé sous le pire des
    trois, et loin au-dessus du 0,05 que rendait une grille de 2,5 mm."""
    did, a = _pose_et_analyse(_synth(26, TROIS))
    boites = a["boxes"]
    assert len(boites) == 3, [(b["x"], b["y"], b["w"], b["h"]) for b in boites]
    trouvees = [[b["x"], b["y"], b["w"], b["h"]] for b in boites]
    for (x, y, w, h) in TROIS_BOITES_PX:
        posee = [v * SYNTH_MM_PX for v in (x, y, w, h)]
        meilleur = max(_iou(posee, t) for t in trouvees)
        assert meilleur >= 0.60, \
            (f"cartouche posé {[round(v, 1) for v in posee]} mm : meilleur "
             f"recouvrement {meilleur:.3f} sur {trouvees}")
    for b in boites:
        assert 0.0 < b["densite"] <= 1.0, b
        assert 0.0 < b["nettete"] <= 1.0, b
        assert b["x"] >= 0 and b["y"] >= 0, b
    CC.delete_deck(did)


def test_la_bordure_ne_DEVORE_pas_les_boites():
    """LE DÉFAUT MESURÉ PENDANT L'ÉCRITURE, épinglé pour de bon. La bande de
    bordure est le plus fort contraste de la carte : sans retrait, son anneau
    relie les trois cartouches en UN SEUL composant faisant le tour de
    l'image — mesuré, une boîte de 570 x 825 px au lieu de trois. Une boîte
    qui couvre plus des trois quarts de la carte est cet anneau-là."""
    did, a = _pose_et_analyse(_synth(26, TROIS))
    carte = a["echelle"]["carte_mm"]
    for b in a["boxes"]:
        part = (b["w"] * b["h"]) / float(carte[0] * carte[1])
        assert part < 0.75, (part, b, "l'anneau de bordure est passé en zone")
    CC.delete_deck(did)


def test_deux_boites_EMBOITEES_n_en_font_qu_UNE():
    """LA FUSION, ET LE CAS QU'ELLE EXISTE POUR RÉGLER. Les composants connexes
    sont disjoints par construction — mais leurs RECTANGLES peuvent
    s'emboîter : un cartouche CREUX (un cadre à filet) est un seul composant
    dont la boîte englobe tout ce qui est posé dedans, et un pictogramme au
    centre en est un second, sans contact.

    Deux boîtes pour une seule zone donneraient deux slots superposés à P3.
    Mesuré sur le montage ci-dessous : 2 composants, 1 boîte après fusion —
    et 2 si l'on remonte le seuil de fusion au-dessus de 1."""
    im = _synth(26)
    d = ImageDraw.Draw(im)
    d.rectangle([100, 200, 520, 620], outline=(235, 220, 160), width=6)
    d.rectangle([270, 380, 350, 460], fill=(240, 230, 120))
    did, a = _pose_et_analyse(im)
    assert len(a["boxes"]) == 1, \
        [(b["x"], b["y"], b["w"], b["h"]) for b in a["boxes"]]
    b = a["boxes"][0]
    # ... et la boîte fusionnée est bien celle du cadre POSÉ (10 x 20 mm,
    # 42 x 42 mm), à un bloc près.
    assert _iou([b["x"], b["y"], b["w"], b["h"]], [10.0, 20.0, 42.0, 42.0]) \
        >= 0.85, b
    CC.delete_deck(did)


def test_un_FOND_NON_UNI_est_refuse_AVEC_LA_MESURE_QUI_A_REFUSE():
    """Spec §8 :589 — « fond non uni à l'import -> refus mesuré du détourage
    local + proposition de l'option IA ». Le refus doit porter le CHIFFRE et
    le SEUIL, et proposer la suite sans en donner le prix (le prix vient de
    `pricing.py` par la route d'options, jamais d'une copie)."""
    grad = Image.new("RGB", (SYNTH_W, SYNTH_H))
    d = ImageDraw.Draw(grad)
    for y in range(SYNTH_H):
        d.line([(0, y), (SYNTH_W, y)],
               fill=(int(20 + y * 0.25), 40, int(200 - y * 0.2)))
    did, a = _pose_et_analyse(grad)
    bg = a["bg"]
    assert bg.get("bg_failed") is True, bg
    assert bg["seuil"] == CP.FOND_SEUIL_UNI == 0.60, bg
    assert 0.0 <= bg["uniformite"] < bg["seuil"], \
        f"le refus n'est pas motivé par sa mesure : {bg}"
    assert bg["motif"] == "pourtour non uni", bg
    phrase = bg["option_ia"]
    assert "IA" in phrase and "payante" in phrase, phrase
    # LE PRIX N'EST PAS RECOPIÉ (doctrine D5) : aucun chiffre monétaire ici.
    assert not re.search(r"\d[\d ,.]*\s*(\$|€|USD|EUR)", phrase), phrase
    # LA NOTE PORTE LE MÊME CHIFFRE, ÉCRIT EN FRANÇAIS. Les notes sont de la
    # prose (l'écran les affiche telles quelles) : « 0.246 » au milieu de
    # trois lignes à virgule décimale se voit — mesuré à l'écran, corrigé.
    fr = str(bg["uniformite"]).replace(".", ",")
    assert any("ond" in n and fr in n for n in a["notes"]), (fr, a["notes"])
    assert not any(re.search(r"\d\.\d", n) for n in a["notes"]), \
        [n for n in a["notes"] if re.search(r"\d\.\d", n)]
    CC.delete_deck(did)


def test_un_FOND_UNI_rend_sa_couleur_POSEE_et_sa_confiance():
    """L'autre côté de la porte : pourtour uni, sujet assez grand pour que la
    couverture tienne dans [5 %, 95 %]. La couleur rendue est celle POSÉE.

    TOLÉRANCE : 6 niveaux par canal. La clé est la MÉDIANE des échantillons
    de pourtour — sur un aplat elle est exacte, et les 6 niveaux couvrent un
    ré-encodage qui ne serait pas sans perte. Mesuré ici : écart 0."""
    fond = (30, 60, 120)
    uni = Image.new("RGB", (SYNTH_W, SYNTH_H), fond)
    ImageDraw.Draw(uni).rectangle([120, 180, 500, 700], fill=(230, 200, 90))
    did, a = _pose_et_analyse(uni)
    bg = a["bg"]
    assert not bg.get("bg_failed"), bg
    vu = tuple(int(bg["color"][i:i + 2], 16) for i in (1, 3, 5))
    assert max(abs(v - p) for v, p in zip(vu, fond)) <= 6, (bg["color"], fond)
    assert bg["confidence"] == bg["uniformite"] >= CP.FOND_SEUIL_UNI, bg
    assert CP.FOND_COUV_MIN <= bg["couverture"] <= CP.FOND_COUV_MAX, bg
    CC.delete_deck(did)


def test_la_MESURE_du_fond_et_le_VERDICT_de_chroma_key_ne_divergent_pas():
    """LA MESURE PUBLIÉE VIENT D'ICI, LE VERDICT VIENT DE `pixel_ops`. Deux
    formules pour un seul refus : si elles dérivaient, le message dirait
    « pourtour non uni à 0,82 » sur un refus causé par autre chose — un
    utilisateur chercherait un fond que rien ne condamne. Le contrôle exige
    l'accord sur les deux cas, dans les deux sens."""
    from app.services.pixel_ops import chroma_key
    grad = Image.new("RGB", (300, 420))
    d = ImageDraw.Draw(grad)
    for y in range(420):
        d.line([(0, y), (300, y)], fill=(int(20 + y * 0.5), 40, int(200 - y * 0.4)))
    uni = Image.new("RGB", (300, 420), (30, 60, 120))
    ImageDraw.Draw(uni).rectangle([60, 90, 240, 330], fill=(230, 200, 90))
    for im, attendu in ((grad, False), (uni, True)):
        m = CP._mesure_fond(im)
        _, ok = chroma_key(im, tolerance=CP.FOND_TOLERANCE,
                           feather=CP.FOND_FEATHER)
        assert ok is attendu, (attendu, ok)
        porte = (m["uniformite"] >= CP.FOND_SEUIL_UNI
                 and CP.FOND_COUV_MIN <= m["couverture"] <= CP.FOND_COUV_MAX)
        assert porte is ok, \
            (f"la mesure d'ici dit {porte} là où chroma_key dit {ok} : "
             f"uniformité {m['uniformite']:.3f}, couverture {m['couverture']:.3f}")


def test_la_PALETTE_rend_les_teintes_POSEES():
    """Quantification adaptative sur une carte peinte de cinq aplats connus :
    les deux dominants doivent sortir À L'OCTET (une médiane de coupe sur une
    zone uniforme rend la couleur elle-même), et les parts doivent faire 1."""
    did, a = _pose_et_analyse(_synth(26, TROIS))
    hexs = [c["hex"] for c in a["palette"]]
    assert len(hexs) == CP.PALETTE_N == 6, hexs
    assert "#d8b76a" in hexs, hexs        # la bande
    assert "#14120c" in hexs, hexs        # l'intérieur (20,18,12)
    parts = [c["part"] for c in a["palette"]]
    assert abs(sum(parts) - 1.0) < 0.02, parts
    assert parts == sorted(parts, reverse=True), parts
    CC.delete_deck(did)


def test_L_ECHELLE_VIENT_DU_FORMAT_DU_DECK_et_pas_de_l_image():
    """La MÊME image, trois formats : les millimètres changent, et chacun est
    exactement `trim_mm[0] * px / largeur`. C'est la preuve que l'échelle
    n'est pas un hasard de l'image — elle vient du document."""
    octets = _synth(26)
    for fmt, trim in (("poker_eu", 63.0), ("tarot_eu", 70.0), ("mini", 44.0)):
        did, a = _pose_et_analyse(octets, fmt)
        attendu = trim * 26 / SYNTH_W
        assert a["echelle"]["fmt"] == fmt, a["echelle"]
        assert abs(a["border"]["mm"] - attendu) < 1e-3, \
            (fmt, a["border"]["mm"], attendu)
        assert abs(a["echelle"]["carte_mm"][0] - trim) < 0.01, a["echelle"]
        CC.delete_deck(did)


def test_la_BANDE_EXCLUE_du_retrait_est_NOMMEE_et_les_boites_coupees_AVOUEES():
    """LA TROUVAILLE BLOQUANTE DE LA RONDE. Le retrait qui empêche l'anneau de
    bordure d'avaler les zones (contrôle voisin) blanchit AUSSI une bande de
    plusieurs millimètres le long des quatre bords — 6,00 mm mesurés pour une
    bordure de 2,6 mm. Un cartouche posé dedans ressortait COUPÉ à la
    frontière du masque, avec une densité et une netteté parfaitement
    saines : rien, dans le relevé, ne distinguait la coupe d'une mesure.
    Mesuré, cartouche de 30 x 9 mm : collé au coin -> IoU 0,459 ; à 3 mm du
    bord -> 0,503 — SOUS le seuil d'appariement de 0,60 de cette suite ; et
    `notes` était VIDE dans les cinq cas.

    C'est le cas du Patriarche (bandeau de titre collé au cadre), et T3 fera
    naître des slots de ces millimètres-là. Trois exigences : la bande est
    publiée EN MILLIMÈTRES, la note la nomme avec ses deux termes, et toute
    boîte qui la touche porte `tronquee`."""
    did, a = _pose_et_analyse(_synth(26, [(27, 27, 300, 90, (235, 220, 160))]))
    assert a["zones_bande_mm"] and a["zones_bande_mm"] > 0, a["zones_bande_mm"]
    note = [n for n in a["notes"] if "bande" in n and "exclue" in n]
    assert note, a["notes"]
    assert _fr_py(a["zones_bande_mm"]) in note[0], (a["zones_bande_mm"], note)
    assert a["boxes"], a["notes"]
    assert all(b.get("tronquee") is True for b in a["boxes"]), a["boxes"]
    CC.delete_deck(did)
    # ... et une boîte LOIN du bord ne porte pas le drapeau : sinon il ne
    # dirait rien, il décorerait.
    did, a = _pose_et_analyse(_synth(26, [(200, 200, 300, 90, (235, 220, 160))]))
    assert a["boxes"], a["notes"]
    assert all(b.get("tronquee") is False for b in a["boxes"]), a["boxes"]
    CC.delete_deck(did)


def _fr_py(v, n=2):
    """Le MÊME écrivain de nombres que la source (`capture._fr`) — pas une
    seconde recette. Deux façons d'écrire un nombre dans un test et dans le
    code, c'est un faux-rouge qui attend son zéro final : `str(rnd(0.250,3))`
    donne « 0.25 » quand `_fr` donne « 0,250 »."""
    return CP._fr(v, n)


def test_les_QUATRE_EPAISSEURS_sont_APPARIEES_a_leur_bord():
    """DEUX TRIS, DEUX CLÉS. `bords` sortait de `sorted(vus)` — l'ordre
    ALPHABÉTIQUE des noms — et `epaisseurs_mm` de `sorted(eps)` — l'ordre
    NUMÉRIQUE des épaisseurs. Les apparier par indice était donc faux dès que
    l'ordre des mesures n'était pas l'ordre de l'alphabet. Mesuré sur des
    bandes posées gauche 1,0 / haut 2,0 / droite 3,0 / bas 4,0 mm :
    l'appariement par indice donnait {bas: 1,0, droite: 2,0, gauche: 3,0,
    haut: 4,0} — les QUATRE fausses. `epaisseurs_mm` est un DICTIONNAIRE."""
    im = Image.new("RGB", (SYNTH_W, SYNTH_H), OR)
    # gauche 10 px, haut 20 px, droite 30 px, bas 40 px
    ImageDraw.Draw(im).rectangle(
        [10, 20, SYNTH_W - 31, SYNTH_H - 41], fill=NOIR)
    did, a = _pose_et_analyse(im)
    b = a["border"]
    assert b["epaisseurs_mm"] == {"gauche": 1.0, "haut": 2.0,
                                 "droite": 3.0, "bas": 4.0}, b["epaisseurs_mm"]
    # `bords` et le dictionnaire disent la MÊME chose — une seule vérité.
    assert b["bords"] == sorted(b["epaisseurs_mm"]), b
    CC.delete_deck(did)
    # ... et quand un bord seulement est vu, il n'y en a QU'UN dans le
    # dictionnaire : on ne publie pas trois trous pour faire quatre.
    im = Image.new("RGB", (SYNTH_W, SYNTH_H), OR)
    ImageDraw.Draw(im).rectangle([0, 20, SYNTH_W - 1, SYNTH_H - 1], fill=NOIR)
    did, a = _pose_et_analyse(im)
    if a["border"]:
        assert set(a["border"]["epaisseurs_mm"]) == set(a["border"]["bords"])
        assert len(a["border"]["bords"]) < 4, a["border"]
    CC.delete_deck(did)


def test_une_bordure_TEXTUREE_est_refusee_pour_SA_VRAIE_RAISON():
    """LE TÉMOIN `BORD_FRONT_RATIO`, RETOURNÉ PAR LA RONDE. L'aveu de la
    livraison disait deux choses, toutes deux fausses : que le rapport ne mord
    jamais sur une carte, et qu'il ne mord que sur une image minuscule.

    Mesuré : sur un profil OSCILLANT (rayures de 2 px), la marche médiane vaut
    455 et le plancher passe de 40 à 1824 — le rapport décide, et il décide
    seul. Sur une image de 40 x 56, la marche médiane vaut 0 : le rapport ne
    joue AUCUN rôle. C'est l'inverse exact de ce qui était écrit.

    Conséquence réelle, et c'est elle qu'on garde : un scan tramé ou une
    bordure à filets fins rend `border: null` avec une note qui disait
    « aucun front franc » — un refus qui ne nomme pas sa cause. La note doit
    dire le PROFIL TEXTURÉ et ses deux chiffres."""
    ray = Image.new("RGB", (SYNTH_W, SYNTH_H), NOIR)
    d = ImageDraw.Draw(ray)
    for y in range(0, SYNTH_H, 4):
        d.rectangle([0, y, SYNTH_W - 1, y + 1], fill=OR)
    did, a = _pose_et_analyse(ray)
    assert a["border"] is None, a["border"]
    tex = [n for n in a["notes"] if "textur" in n.lower()]
    assert tex, a["notes"]
    assert "455" in tex[0] and "1824" in tex[0], tex[0]
    # ... et le refus ORDINAIRE (dégradé doux, marche médiane nulle) garde sa
    # note à lui : les deux causes ne se confondent pas.
    grad = Image.new("RGB", (SYNTH_W, SYNTH_H))
    dg = ImageDraw.Draw(grad)
    for y in range(SYNTH_H):
        dg.line([(0, y), (SYNTH_W, y)],
                fill=(int(20 + y * 0.25), 40, int(200 - y * 0.2)))
    CC.delete_deck(did)
    did, a = _pose_et_analyse(grad)
    assert a["border"] is None
    assert not any("textur" in n.lower() for n in a["notes"]), a["notes"]
    assert any("front franc" in n for n in a["notes"]), a["notes"]
    CC.delete_deck(did)


def test_l_option_IA_n_est_PAS_proposee_quand_il_n_y_a_RIEN_a_detourer():
    """Un aplat total refuse par la porte de COUVERTURE : 0,0 % de l'image
    survivrait au détourage, c'est-à-dire qu'il n'y a pas de sujet. Proposer
    là une option PAYANTE, c'est vendre un service sans objet."""
    did, a = _pose_et_analyse(Image.new("RGB", (SYNTH_W, SYNTH_H), (90, 90, 90)))
    bg = a["bg"]
    assert bg["bg_failed"] is True and bg["couverture"] == 0.0, bg
    assert "option_ia" not in bg, bg.get("option_ia")
    assert "rien" in bg["motif"] or "rien" in " ".join(a["notes"]).lower(), \
        (bg["motif"], a["notes"])
    CC.delete_deck(did)


def test_le_RAYON_est_CORRIGE_du_biais_de_la_rangee_exterieure():
    """LE BIAIS ÉTAIT CONNU, ÉCRIT, EXACT — ET ABSORBÉ PAR UNE TOLÉRANCE DIX
    FOIS TROP LARGE. La ronde a eu raison : un biais qu'on sait calculer se
    corrige, il ne se tolère pas.

    D'OÙ IL VIENT : la rangée extérieure d'un coin arrondi a une HAUTEUR. Le
    premier pixel plein de cette rangée n'est pas à `r` du coin mais à
    `r - sqrt(r)` environ — le pixel dont le centre entre le premier dans le
    disque. Ce n'est PAS un artefact de la bibliothèque de dessin du test :
    c'est vrai de tout arc rastérisé, donc du scan d'une vraie carte. La
    correction appartient à la MESURE, pas au montage.

    Mesuré avant correction, rayons posés 10/20/40/60/90 px : 7/16/34/53/81 px
    lus, soit 3 à 9 px de moins — 12 à 30 % du rayon. Après inversion, l'écart
    tombe sous 0,10 mm, et la tolérance passe de 1,00 mm à 0,15 mm : la même
    que l'épaisseur de bande, parce que c'est la même résolution — 1,5 px."""
    tol = 1.5 * SYNTH_MM_PX
    for r_px in (10, 20, 40, 60, 90):
        im = Image.new("RGB", (SYNTH_W, SYNTH_H), (255, 255, 255))
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([0, 0, SYNTH_W - 1, SYNTH_H - 1], radius=r_px,
                            fill=OR)
        d.rectangle([26, 26, SYNTH_W - 27, SYNTH_H - 27], fill=NOIR)
        did, a = _pose_et_analyse(im)
        vu = a["border"]["radius_mm"]
        attendu = r_px * SYNTH_MM_PX
        assert abs(vu - attendu) <= tol, \
            (f"rayon posé {attendu:.2f} mm, mesuré {vu} mm "
             f"(tolérance {tol:.2f} mm)")
        CC.delete_deck(did)
    # ... et un coin CARRÉ rend toujours zéro : la correction ne fabrique pas
    # un rayon là où la course vaut zéro pixel.
    did, a = _pose_et_analyse(_synth(26))
    assert a["border"]["radius_mm"] == 0.0, a["border"]
    CC.delete_deck(did)


def test_le_SEUIL_DE_SILENCE_de_l_ecart_de_ratio_est_NOMME_et_tenu():
    """Le 0,005 nu de la livraison : sous un demi-pour-cent d'écart, l'image
    est au format à l'arrondi d'un pixel près (un poker_eu de 630 px de large
    fait 880 px de haut ; 879 ou 881 donnent déjà ±0,11 %), et une note à
    chaque analyse serait du bruit. Il porte maintenant un nom et sa raison.
    Mesuré aux deux bords : +0,0045 se tait, +0,0057 parle."""
    assert 0.0 < CP.ECART_RATIO_MUET < 0.05, CP.ECART_RATIO_MUET
    for cible, parle in ((0.004, False), (0.006, True)):
        hh = int(round(SYNTH_W * (88.0 / 63.0) * (1 + cible)))
        did, a = _pose_et_analyse(_synth(26).resize((SYNTH_W, hh)))
        assert abs(a["ecart_ratio"]) > 0, a["ecart_ratio"]
        vu = any("ratio" in n for n in a["notes"])
        assert vu is parle, (cible, a["ecart_ratio"], a["notes"])
        CC.delete_deck(did)


def test_une_dependance_ABSENTE_rend_503_avec_l_erreur_LITTERALE():
    """La doctrine §8 était REVENDIQUÉE et jamais jouée. On la joue : la
    bibliothèque d'images est retirée du chargeur le temps d'une requête, et
    le refus doit être un 503 qui PORTE l'erreur, pas un 500.

    (Ce que la prose de la source dit maintenant : PIL n'est pas une
    dépendance optionnelle de ce laboratoire — ce garde-fou couvre une
    installation cassée, pas une option absente. La doctrine 503 vise les
    dépendances vraiment facultatives, et T3 en aura une.)"""
    import types
    did = _deck()
    _post(did, _pngs(_synth(26)), "recto")
    # `PIL.Image` AUSSI, et c'est le piège du montage : `from PIL import Image`
    # ne s'arrête pas à l'attribut manquant, il retombe sur le SOUS-MODULE —
    # qui est encore dans le chargeur. Une première écriture ne retirait que
    # `PIL` et la route répondait 200, la bibliothèque toujours là.
    vrais = {k: v for k, v in sys.modules.items()
             if k == "PIL" or k.startswith("PIL.")}
    for k in vrais:
        del sys.modules[k]
    sys.modules["PIL"] = types.ModuleType("PIL")     # un PIL sans `Image`
    try:
        r = _analyse(did)
    finally:
        sys.modules.pop("PIL", None)
        sys.modules.update(vrais)
    assert r.status_code == 503, (r.status_code, r.text[:300])
    detail = r.json()["detail"]
    assert "Image" in detail or "PIL" in detail, detail
    assert re.search(r"[éèêàç]", detail), detail
    # la pièce remarche une fois la bibliothèque revenue
    assert _analyse(did).status_code == 200
    CC.delete_deck(did)


def test_les_MESURES_franchissent_la_frontiere_en_MILLIMETRES():
    """Plan D3 : « une unité par frontière, convertie au bord de l'API ». Le
    relevé ne parle qu'en millimètres — la seule exception est `echelle`, dont
    le rôle EST de dire dans quel cadre ces millimètres se lisent (la trame de
    l'image en pixels, et le facteur qui l'y ramène).

    LE PIÈGE ÉTAIT ÉCRIT : la bordure publiait son épaisseur en pixels À CÔTÉ
    de ses millimètres, « pour le confort ». Deux unités pour une mesure, et
    la première pièce qui adopte (T3, T4) doit choisir laquelle croire.

    ET LE BALAYAGE SE DÉRIVE DE LA RÉPONSE, il ne récite pas quatre noms. La
    première écriture nommait `border`, `boxes`, `bg`, `palette` EN DUR : la
    ronde a ajouté un `retrait_px` au sommet du relevé, proprement déclaré
    partout, et les 56 contrôles sont restés verts. C'est la leçon des miroirs
    de T1 appliquée à un balayage — ce qu'on énumère à la main, on cesse de
    l'énumérer le jour où l'on ajoute une clé."""
    did, a = _pose_et_analyse(_synth(26, TROIS))

    def balaie(v, chemin):
        if isinstance(v, dict):
            for k, x in v.items():
                assert "px" not in k.split("_") and not k.endswith("_px"), \
                    f"{chemin}.{k} traverse l'API en pixels"
                balaie(x, f"{chemin}.{k}")
        elif isinstance(v, list):
            for i, x in enumerate(v):
                balaie(x, f"{chemin}[{i}]")

    balayees = set(a) - {"echelle"}
    assert len(balayees) >= 6, balayees
    for cle in sorted(balayees):
        assert "px" not in cle.split("_"), f"{cle} traverse l'API en pixels"
        balaie(a[cle], cle)
    # ... et `echelle` porte l'exception, EXPLICITEMENT nommée.
    assert a["echelle"]["image_px"] == [SYNTH_W, SYNTH_H], a["echelle"]
    assert abs(a["echelle"]["mm_par_px"] - SYNTH_MM_PX) < 1e-6, a["echelle"]
    CC.delete_deck(did)


def test_l_ECART_DE_RATIO_est_MESURE_et_publie_au_lieu_d_etre_un_echec():
    """Une image carrée sur un poker_eu : les mm sont calés sur la LARGEUR, et
    l'écart de ratio dit de combien la hauteur les dément. Publier l'écart
    plutôt que refuser, c'est le laisser servir — mais il doit être JUSTE :
    1,0000 / 1,3968 - 1 = -0,2841, au signe près."""
    did, a = _pose_et_analyse(_synth(24, w=600, h=600))
    attendu = 1.0 / (88.0 / 63.0) - 1.0
    assert abs(a["ecart_ratio"] - attendu) < 1e-3, (a["ecart_ratio"], attendu)
    assert a["ecart_ratio"] < 0, "une image plus large que le format"
    assert any("ratio" in n for n in a["notes"]), a["notes"]
    assert not any(re.search(r"\d\.\d", n) for n in a["notes"]), \
        ["une note écrit un nombre à l'anglaise", a["notes"]]
    CC.delete_deck(did)
    # ... et un ratio JUSTE ne fait pas de bruit.
    did, a = _pose_et_analyse(_synth(26))
    assert abs(a["ecart_ratio"]) < 1e-6, a["ecart_ratio"]
    assert not any("ratio" in n for n in a["notes"]), a["notes"]
    CC.delete_deck(did)


def test_une_image_PATHOLOGIQUE_degrade_l_analyse_SANS_500():
    """Spec §8 : jamais 500. Un pixel, trois pixels, un aplat total — chacun
    rend un relevé DÉGRADÉ ET AVOUÉ (les détections absentes, les notes qui
    disent pourquoi), pas une trace de pile."""
    # LA RÉFÉRENCE : les clés d'un relevé SAIN. Un relevé dégradé doit être
    # aussi COMPLET — vide, pas amputé. Une clé qui n'apparaît que sur le
    # chemin heureux force chaque lecteur à un `if` de plus, et l'écran, lui,
    # lèverait sur une valeur `undefined` (c'est la leçon `patchAs` de T1).
    did, sain = _pose_et_analyse(_synth(26, TROIS))
    cles = set(sain)
    CC.delete_deck(did)
    for (w, h) in ((1, 1), (2, 3), (SYNTH_W, SYNTH_H)):
        im = Image.new("RGB", (w, h), (90, 90, 90))
        did, a = _pose_et_analyse(im)
        assert set(a) == cles, (w, h, sorted(cles - set(a)), sorted(set(a) - cles))
        assert a["border"] is None, (w, h, a["border"])
        assert a["boxes"] == [], (w, h, a["boxes"])
        assert a["bg"].get("bg_failed") is True, (w, h, a["bg"])
        assert a["notes"], (w, h, "un relevé vide qui ne dit pas pourquoi")
        assert a["palette"], (w, h, a["palette"])
        assert a["analyzed"] > 1_000_000_000_000, a["analyzed"]
        CC.delete_deck(did)


def test_une_DETECTION_QUI_LEVE_laisse_le_releve_COMPLET_et_l_AVOUE():
    """LE CHEMIN GARDÉ, ENFIN JOUÉ. Chaque détection de `analyse_recto` est
    entourée d'un `try` qui écrit une note et continue — c'est ce qui tient la
    promesse « jamais 500 » sur une image pathologique. Mais rien ne
    l'exécutait : les images dégénérées passent par le chemin NORMAL (elles
    rendent zéro boîte, sans lever).

    Ce que le contrôle exige, et que la ronde a mis en lumière : sur ce
    chemin-là aussi, le relevé reste COMPLET. Une clé qui n'existe que si la
    détection réussit oblige chaque lecteur à un `if` de plus — et côté écran,
    `patchAs` reçoit un `undefined` que `sanitize` refuse (leçon T1)."""
    did = _deck()
    _post(did, _pngs(_synth(26, TROIS)), "recto")
    complet = set(_analyse(did).json())
    vrai = CP._grille

    def _grille_qui_meurt(*a, **k):
        raise RuntimeError("panne simulée par le test")

    CP._grille = _grille_qui_meurt
    try:
        r = _analyse(did)
    finally:
        CP._grille = vrai
    assert r.status_code == 200, (r.status_code, r.text[:300])
    a = r.json()
    assert set(a) == complet, sorted(complet - set(a))
    assert a["boxes"] == [] and a["zones_bande_mm"] is None, a["zones_bande_mm"]
    assert any("panne simulée" in n for n in a["notes"]), a["notes"]
    # ... et les AUTRES détections ont quand même travaillé : une panne de
    # zones n'emporte pas la bordure.
    assert a["border"] and a["border"]["mm"] == 2.6, a["border"]
    CC.delete_deck(did)


def test_un_aplat_GRENU_ne_fabrique_pas_de_zones():
    """LE PLANCHER D'ÉTENDUE, ET SON CAS QUI COMPTE. Un aplat PARFAIT ne prouve
    rien : son énergie est nulle partout, donc le seuil relatif ne découpe
    rien même sans plancher. Le vrai piège est le GRAIN — le scan d'une zone
    vide de la carte. Mesuré sur un aplat gris bruité de ±8 niveaux : sans le
    plancher, 12 « zones » sortent de nulle part ; avec, zéro. À ±4 : une
    contre zéro. Le plancher de 10 est ce qui sépare le grain du dessin (la
    carte de synthèse, elle, mesure une étendue de 89)."""
    import random
    random.seed(3)
    im = Image.new("RGB", (SYNTH_W, SYNTH_H))
    px = im.load()
    for y in range(SYNTH_H):
        for x in range(SYNTH_W):
            n = 120 + random.randint(-8, 8)
            px[x, y] = (n, n, n)
    did, a = _pose_et_analyse(im)
    assert a["boxes"] == [], \
        f"{len(a['boxes'])} zones inventées sur du grain : {a['boxes'][:2]}"
    assert any("tendue" in n for n in a["notes"]), a["notes"]
    CC.delete_deck(did)


def test_l_analyse_est_REJOUABLE_et_ne_touche_a_aucun_fichier():
    """« Relançable sans re-dépôt » (plan D3 précisé T2). Deux analyses de
    suite rendent les mêmes mesures, et le dossier ne bouge pas : la route
    RÉPOND, elle n'écrit rien — c'est la pièce qui publie."""
    did = _deck()
    _post(did, _pngs(_synth(26, TROIS)), "recto")
    a = _analyse(did).json()
    b = _analyse(did).json()
    for k in ("border", "boxes", "bg", "palette", "echelle", "ecart_ratio"):
        assert a[k] == b[k], k
    assert b["analyzed"] >= a["analyzed"]
    d = CT.deck_dir(did) / "capture"
    assert sorted(p.name for p in d.iterdir()) == ["source_recto.png"]
    CC.delete_deck(did)


def test_deposer_un_VERSO_ne_change_RIEN_a_la_mesure_du_recto():
    """L'asymétrie de D3 amendé, vue côté ROUTE cette fois (le contrôle
    voisin la prouve côté écran, dans node)."""
    did = _deck()
    _post(did, _pngs(_synth(26, TROIS)), "recto")
    avant = _analyse(did).json()
    _post(did, _pngs(_synth(13)), "verso")
    apres = _analyse(did).json()
    assert avant["border"] == apres["border"], (avant["border"], apres["border"])
    assert avant["boxes"] == apres["boxes"]
    CC.delete_deck(did)


def test_l_analyse_ne_rend_JAMAIS_500_meme_sur_un_recto_abime():
    """Un PNG tronqué posé À LA MAIN dans le dossier — l'accident réel d'un
    disque plein ou d'un dossier copié à moitié. La route doit le NOMMER."""
    did = _deck()
    d = CT.deck_dir(did, create=True) / "capture"
    d.mkdir(parents=True, exist_ok=True)
    (d / "source_recto.png").write_bytes(_pngs(_synth(26))[:400])
    r = _analyse(did)
    assert r.status_code != 500, r.text[:300]
    assert r.status_code in (400, 409), (r.status_code, r.text[:200])
    assert "json" in r.headers.get("content-type", "")
    assert re.search(r"[éèêàç]", r.json()["detail"]), r.json()["detail"]
    CC.delete_deck(did)


# ═══════════════════════ l'écran, côté mesures ══════════════════════════════

def test_le_SCHEMA_de_l_ecran_couvre_TOUTES_les_cles_du_releve():
    """LA FRONTIÈRE QUI CASSE EN SILENCE. `patchAs` LÈVE sur une clé hors
    schéma : une clé publiée par `analyse_recto` et absente du bloc `state:`
    de mod-capture.js ne « manquerait » pas à l'écran — elle ferait échouer le
    geste « Analyser » en entier, avec pour tout diagnostic « capture ne
    possède pas ecart_ratio » dans un toast. Rien d'autre que ce contrôle ne
    tient les deux bouts : le JS n'est importable d'aucune façon depuis
    Python, et le Python n'est lu par aucun test JS."""
    from app.services.cards.contract import geom
    releve = CP.analyse_recto(_synth(26, TROIS), geom("poker_eu", 300))
    schema = _cles_du_schema()
    hors = set(releve) - schema
    assert not hors, \
        (f"le backend publie {sorted(hors)} — `M.patch` lèvera : ajoutez-les "
         f"au bloc `state:` de mod-capture.js")
    # ... et dans l'autre sens : `releve()` ne doit pas inventer de clés.
    js = _corps_js("releve")
    for cle in sorted(set(releve)):
        assert cle + ":" in js, \
            f"releve() ne recopie pas « {cle} » : la mesure se perdrait"


def test_l_ecran_ecrit_TOUJOURS_un_CHIFFRE_de_confiance():
    """Spec §7.1.2 : « l'écran affiche le chiffre, jamais une certitude ». La
    règle est EXÉCUTÉE : on extrait `conf` et `num` de la vraie source et on
    les fait tourner dans node. Une version qui rendrait « bonne » ou
    « fiable » sur un nombre tomberait ici, et une virgule anglaise aussi."""
    src = (_fonction_js("estNombre") + _fonction_js("num")
           + _fonction_js("conf"))
    sortie = _node(src + """
      console.log([conf(0.84), conf(1), conf(0), conf(null), conf("x"),
                   num(2.6, 2), num(0.1665, 2)].join("|"));
    """)
    vus = sortie.strip().split("|")
    assert vus[0] == "confiance 0,84", vus
    assert vus[1] == "confiance 1,00", vus
    assert vus[2] == "confiance 0,00", "une confiance NULLE s'écrit aussi"
    assert vus[3] == "confiance inconnue" and vus[4] == "confiance inconnue", vus
    assert vus[5] == "2,60" and vus[6] == "0,17", vus
    # AUCUN ADJECTIF DE CERTITUDE dans les phrases d'ÉCRAN.
    #
    # LES COMMENTAIRES NE SONT PAS DES PHRASES D'ÉCRAN, et la première
    # écriture les confondait : un `'` d'apostrophe française dans un
    # commentaire (« qu'on n'a pas ») ferme un faux littéral, et tout le
    # commentaire entrait dans le balayage — le contrôle rougissait sur la
    # DOCTRINE qui interdit le mot. On dépouille donc pour de bon.
    plat = " ".join(_chaines_js(JS.read_text(encoding="utf-8"))).lower()
    assert "confiance " in plat, "le dépouillage a mangé les phrases d'écran"
    assert "deux decimales" not in plat, "un commentaire a survécu au dépouillage"
    for mot in ("fiable", "certaine", "sûre", "excellente", "parfaite",
                "bonne détection", "détection correcte"):
        assert mot not in plat, f"« {mot} » remplace un chiffre à l'écran"
    # ET LA CLASSE DE DÉFAUT EST FERMÉE, pas seulement l'occurrence trouvée.
    # `isFinite(Number(x))` est VRAI pour `null` : partout où l'écran s'en
    # servait pour décider s'il a une mesure, une mesure absente devenait un
    # zéro affiché (le rayon de coin non suivi, l'écart de ratio jamais
    # calculé). Le seul test d'existence autorisé est `estNombre`.
    js = JS.read_text(encoding="utf-8")
    assert "isFinite(Number(" not in js, \
        ("`isFinite(Number(x))` est de retour : il accepte null et le peint "
         "en zéro — utiliser `estNombre`")


def test_l_incrustation_des_boites_n_est_PAS_un_painter():
    """§9.4 : P10 n'a aucun z et ne dessine pas la carte. L'aperçu des boîtes
    est de l'HTML posé PAR-DESSUS l'<img>, en pourcentages de la carte —
    donc dans la même unité que `boxes`, sans mesurer une seule fois la mise
    en page. Un canvas ici serait un painter clandestin."""
    corps = _corps_js("dessineBoites")
    for interdit in ("getContext", "canvas", "CanvasRenderingContext"):
        assert interdit not in corps, interdit
    assert "carte_mm" in corps, "les boîtes ne sont pas placées par l'échelle"
    assert corps.count('+ "%"') >= 4, \
        "les quatre côtés doivent être posés en pourcentages"
    js = JS.read_text(encoding="utf-8")
    assert 'painters: []' in js.replace('painters:[', 'painters: [')


def test_le_refus_du_fond_nomme_a_l_ecran_la_PORTE_QUI_A_REFUSE():
    """Le JSON disait juste (`motif` nomme la porte), l'écran non : il posait
    TOUJOURS la ligne d'uniformité en tête. Sur un refus par COUVERTURE on
    lisait donc « uniformité 1,00 pour un plancher de 0,60 » — un chiffre qui
    PASSE, présenté comme la cause d'un refus — puis la couverture sans ses
    bornes, alors que `couverture_bornes` était publié et lu par personne.

    La règle est EXÉCUTÉE : on extrait `lignesFond` de la vraie source et on
    lui donne les deux refus."""
    src = (_fonction_js("isPlain") + _fonction_js("estNombre")
           + _fonction_js("num") + _fonction_js("lignesFond"))
    sortie = _node(src + """
      const uni = {bg_failed:true, motif:"pourtour non uni", uniformite:0.246,
                   seuil:0.6, couverture:0.15, couverture_bornes:[0.05,0.95],
                   option_ia:"IA"};
      const cou = {bg_failed:true, motif:"couverture hors bornes",
                   uniformite:1, seuil:0.6, couverture:0.0,
                   couverture_bornes:[0.05,0.95]};
      const ok = {color:"#1e3c78", confidence:1, couverture:0.358, seuil:0.6};
      console.log(JSON.stringify([lignesFond(uni), lignesFond(cou),
                                  lignesFond(ok)]));
    """)
    par_uni, par_couv, sain = json.loads(sortie)
    par_uni = " | ".join(x for x in par_uni if x)
    par_couv = " | ".join(x for x in par_couv if x)
    sain = " | ".join(x for x in sain if x)
    # le refus par uniformité mène avec l'uniformité...
    assert "uniformit" in par_uni.split("|")[1], par_uni
    assert "0,25" in par_uni and "0,60" in par_uni, par_uni
    # ... et le refus par COUVERTURE mène avec la couverture ET ses bornes,
    # sans jamais donner l'uniformité pour cause.
    assert "couverture" in par_couv.split("|")[1].lower(), par_couv
    assert "5" in par_couv and "95" in par_couv, \
        f"les bornes ne sont pas écrites : {par_couv}"
    tete = par_couv.split("|")[1].lower()
    assert "uniformit" not in tete, \
        f"la mauvaise porte est nommée en tête : {par_couv}"
    assert "refus" not in sain.lower(), sain


def test_l_ecran_DIT_quand_le_FORMAT_a_bouge_sous_les_mesures():
    """Le piège était nommé dans un commentaire, pas fermé. Le CORE émet
    `core:geom` quand le format change (core.js:424) ; P10 ne l'écoutait pas.
    Après un passage poker -> tarot, l'écran gardait sa pastille verte et
    affichait « 63,0 x 88,0 mm (poker_eu) » sur un jeu tarot : des
    millimètres faux de 11 %, présentés comme mesurés.

    La décision vit dans une fonction PURE, exécutée ici."""
    fn = _fonction_js("isPlain") + _fonction_js("divergence")
    sortie = _node(fn + """
      const d = (e, f) => JSON.stringify(divergence(e, {format: {fmt: f}}));
      console.log([d({fmt:"poker_eu"}, "poker_eu"), d({fmt:"poker_eu"}, "tarot_eu"),
                   d(null, "poker_eu"), d({fmt:"poker_eu"}, null),
                   d({}, "tarot_eu")].join("|"));
    """)
    memes, autres, sans_e, sans_f, vide = sortie.strip().split("|")
    assert json.loads(memes) is None, memes
    assert json.loads(autres) == {"avant": "poker_eu", "apres": "tarot_eu"}, autres
    for muet in (sans_e, sans_f, vide):
        assert json.loads(muet) is None, muet
    # ... et l'écran se REPEINT sur l'événement, sinon la divergence attend
    # un clic pour se voir. LA RECHERCHE PORTE SUR LE CODE DÉPOUILLÉ : la
    # ligne mise en commentaire satisfaisait le contrôle précédent (mesuré en
    # l'entourant de `/* */` — vert), ce qui en faisait un garde-fou qu'on
    # pouvait débrancher sans rien casser.
    code = _code_js(JS.read_text(encoding="utf-8"))
    assert re.search(r'CF\.on\(\s*"core:geom"', code), \
        "P10 n'écoute pas core:geom : le format peut bouger sans qu'elle le sache"
    assert "divergence(" in _code_js(_corps_js("mesures")), \
        "la divergence est calculée mais jamais affichée"


def test_le_bouton_des_ZONES_ne_promet_que_ce_qu_il_peut_faire():
    """Sa visibilité tenait au seul `boxes.length` ; l'incrustation, elle,
    exige AUSSI `echelle.carte_mm` — sans quoi elle n'a pas d'unité où poser
    ses pourcentages. Un document venu d'une version antérieure (des boîtes,
    pas d'échelle) affichait donc un bouton qui ne faisait rien. Les deux
    conditions sont la MÊME : `peutIncruster`."""
    src = (_fonction_js("isPlain") + _fonction_js("estNombre")
           + _fonction_js("peutIncruster"))
    sortie = _node(src + """
      const p = (s) => peutIncruster(s) ? 1 : 0;
      console.log([p({boxes:[{x:1}], echelle:{carte_mm:[63,88]}}),
                   p({boxes:[], echelle:{carte_mm:[63,88]}}),
                   p({boxes:[{x:1}], echelle:null}),
                   p({boxes:[{x:1}], echelle:{carte_mm:[0,88]}}),
                   p({})].join(""));
    """)
    assert sortie.strip() == "10000", sortie
    # ... et c'est ELLE que les deux endroits interrogent.
    for f in ("paint", "dessineBoites"):
        assert "peutIncruster(" in _corps_js(f), f


def test_une_PANNE_DE_RESEAU_ne_se_dit_pas_dans_la_langue_du_navigateur():
    """`panne()` ne traduisait que `e.missing` : un `fetch` rejeté (backend
    éteint, câble débranché) ressortait en « Failed to fetch », en anglais et
    sans dire ce qu'il faut faire. Le CORE a déjà écrit le remède
    (`core.js:1244`, « backend injoignable ») ; on l'applique."""
    src = _fonction_js("panne")
    sortie = _node(src + """
      const e1 = new Error("route absente"); e1.missing = true;
      const e2 = new TypeError("Failed to fetch");
      const e3 = new Error("Côté inconnu : « dos »");
      console.log([panne(e1, "l'analyse"), panne(e2, "l'analyse"),
                   panne(e3, "l'analyse")].join("|"));
    """)
    absente, reseau, nomme = sortie.strip().split("|")
    assert "backend absent" in absente, absente
    # LA PHRASE DU NAVIGATEUR RESTE, EN PARENTHÈSES, ET C'EST VOULU : la
    # doctrine du lab est « l'erreur LITTÉRALE, préfixée » — celui qui
    # diagnostique veut le mot exact, celui qui lit veut la phrase française.
    # Ce qui est interdit, c'est que la phrase anglaise soit TOUT le message.
    assert reseau.startswith("backend injoignable"), reseau
    assert "service local" in reseau, reseau
    assert reseau != "Failed to fetch", reseau
    # ... et un refus NOMMÉ par le backend traverse intact : le remède ne doit
    # pas avaler la phrase que la route a pris la peine d'écrire.
    assert nomme == "Côté inconnu : « dos »", nomme


def test_le_geste_ANALYSER_est_garde_contre_le_double_clic():
    """Patron BUSY de T1, étendu au second geste : le MÊME verrou que
    l'import — mesurer pendant qu'un fichier monte mesurerait l'image d'avant.
    Et le bouton n'existe pas sans recto : l'analyse porte sur lui."""
    corps = _corps_js("analyser")
    assert re.search(r"if\s*\(\s*BUSY\s*\)", corps), corps[:400]
    assert "BUSY = true" in corps and "BUSY = false" in corps, corps[:400]
    assert 'info("recto")' in corps, corps[:400]
    assert "M.patch(" in corps, "la PIÈCE publie (D3) — pas la route"
    peint = _corps_js("paint")
    assert "cf-capture-analyse" in peint, \
        "le bouton n'est pas piloté par l'état de l'écran"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
