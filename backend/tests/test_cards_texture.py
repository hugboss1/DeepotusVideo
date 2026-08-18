# -*- coding: utf-8 -*-
"""Card Forge — P6 « Textures (2D et PBR) ». Les seuils, mesurés.

LA BARRE, mesurée sur ses propres fichiers téléchargés (Sorceress Material
Forge, 11/08/2026) : QUATRE maps — base color 1024x1024, normale 512x512,
rugosité 512x512, occlusion 512x512. Pas de métallique, pas de hauteur, pas
d'émission, pas d'ORM. Aucun chiffre affiché sous aucune map. Génération
derrière un compte et un crédit.

CE QUI EST VERROUILLÉ ICI, seuil par seuil :

  1. HUIT maps produites, nommées exactement comme `pbr_service.MAP_KINDS`.
  2. Le catalogue 2D livré dans `js/mod-texture.js` porte >= 24 matières, et
     PAS UNE URL : « 0 octet réseau » se vérifie sur le fichier, pas sur une
     intention.
  3. Chaque chiffre affiché est relu sur les OCTETS ÉCRITS. Le test rouvre
     les PNG depuis le disque, recalcule `map_report` / `effective_levels` et
     compare au rapport servi. Un rapport calculé sur les objets en mémoire
     passerait ce test à côté : c'est pourquoi la comparaison part du fichier.
  4. 4k = 4096x4096 réellement écrit, et la profondeur est lue dans l'IHDR —
     16 bits pour hauteur et normale, 8 pour les six autres.
  5. ORM : R = AO, V = rugosité, B = métallique, canal par canal, à l'octet.
  6. Un curseur ne prouve rien : `emissive_threshold` à 1.0 rend une map
     éteinte, et le rapport le DIT (informative = faux) au lieu de compter
     huit maps de principe.
  7. Un corps mal formé ne fait JAMAIS 500 (spec §2.5), et un nom de map est
     une liste blanche : aucune traversée.

Run : .\\scripts\\run-tests.ps1 -Filter cards
"""
import asyncio
import io
import math
import os
import pathlib
import re
import struct
import sys
import tempfile
import time

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
from PIL import Image, ImageChops, ImageDraw                     # noqa: E402

from app.services import pbr_service as PBR                      # noqa: E402
from app.services.cards import core as CC                        # noqa: E402
from app.services.cards import texture as TX                     # noqa: E402

REPO = pathlib.Path(__file__).resolve().parents[2]
JS = REPO / "frontend" / "cardforge" / "js" / "mod-texture.js"
CSS = REPO / "frontend" / "cardforge" / "css" / "mod-texture.css"

KINDS = ("basecolor", "normal", "roughness", "metallic",
         "ao", "height", "emissive", "orm")


# ═══════════════════════ outillage ══════════════════════════════════════════

def _api(method: str, path: str, **kw):
    """Un appel HTTP réel contre l'application montée, en process."""
    async def go():
        from app.main import app
        async with AsyncClient(transport=ASGITransport(app=app),
                               base_url="http://t", timeout=600.0) as c:
            return await c.request(method, path, **kw)
    return asyncio.run(go())


def _carte(w: int = 815, h: int = 1110) -> bytes:
    """Une carte plausible : dégradé, grain, un cadre et un aplat sombre.
    Une image PLATE rendrait toutes les maps neutres et le test ne dirait
    rien — la moitié des seuils portent justement sur ce que les maps
    contiennent."""
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            g = 150 + int(70 * ((x * 7 + y * 13) % 17) / 17.0)
            px[x, y] = (min(255, g + 24), min(255, g + 8), max(0, g - 26))
    d = ImageDraw.Draw(im)
    d.rectangle([w * 0.08, h * 0.10, w * 0.92, h * 0.55], fill=(38, 40, 52))
    d.rectangle([w * 0.06, h * 0.06, w * 0.94, h * 0.94], outline=(232, 208, 120),
                width=max(2, w // 90))
    for i in range(0, h, 9):
        d.line([(0, i), (w, i)], fill=(210, 200, 180), width=1)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def _deck() -> str:
    doc = CC.create_deck("essai matières")
    return doc["id"]


def _derive(did: str, **opts):
    body = {"derive": {}, "levels": {"metallic": 0.0, "roughness": 0.75},
            "res": 1024, "bits16": True, "square": True}
    body.update(opts)
    r = _api("POST", f"/api/cards/{did}/texture/derive", json=body)
    assert r.status_code == 200, r.text
    return r.json()["texture"]


def _envoie_source(did: str, w: int = 815, h: int = 1110):
    r = _api("POST", f"/api/cards/{did}/texture/source",
             content=_carte(w, h), headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    return r.json()["source"]


def _fichier(did: str, name: str) -> pathlib.Path:
    return TX.tex_dir(did) / name


def _huit_bits(img, kind: str):
    """L'ORACLE de relecture, écrit ICI et pas emprunté au code testé.

    `Image.convert("L")` depuis `I;16` ÉCRÊTE à 255 au lieu de diviser : une
    map 16 bits se mesurait « parfaitement plate » (span 0) alors qu'elle
    portait 231 niveaux. Le facteur de retour est 257 (= 65535/255) et le
    `+0.5` ARRONDIT — `point` tronque, et depuis que la charge utile 16 bits
    est réelle, tronquer poserait un demi-niveau de biais."""
    want = PBR.MAP_MODES[kind]
    if img.mode == want:
        return img
    if want == "L" and img.mode.startswith("I"):
        return img.convert("I").point(lambda v: v / 257.0 + 0.5, "L")
    return img.convert(want)


# ─── L'ORACLE 16 BITS : lire les octets, pas croire l'IHDR ───────────────────

def _chunks(raw: bytes) -> list:
    """Les tags du PNG, lus ici, avec notre propre boucle."""
    out, i = [], 8
    while i + 8 <= len(raw):
        ln = int.from_bytes(raw[i:i + 4], "big")
        tag = raw[i + 4:i + 8].decode("ascii", "replace")
        out.append(tag)
        if tag == "IEND":
            break
        i += 12 + ln
    return out


def _chunk_body(raw: bytes, want: bytes) -> bytes:
    i = 8
    while i + 8 <= len(raw):
        ln = int.from_bytes(raw[i:i + 4], "big")
        if raw[i + 4:i + 8] == want:
            return raw[i + 8:i + 8 + ln]
        if raw[i + 4:i + 8] == b"IEND":
            break
        i += 12 + ln
    return b""


def _payload16(raw: bytes):
    """Les octets d'image d'un PNG 16 bits, décompressés et défiltrés ICI.

    C'est le geste exact du critique qui a trouvé le faux 16 bits : ne pas
    croire `IHDR.bit_depth`, décompresser l'IDAT et regarder les valeurs.
    Rend (w, h, canaux, octets big-endian)."""
    import zlib
    w, h, bits, ct = struct.unpack(">IIBB", raw[16:26])
    assert bits == 16, f"IHDR annonce {bits} bits"
    nch = 3 if ct == 2 else 1
    idat = b"".join(
        raw[i + 8:i + 8 + int.from_bytes(raw[i:i + 4], "big")]
        for i in _positions(raw, b"IDAT"))
    data = zlib.decompress(idat)
    stride = w * 2 * nch
    assert len(data) == (stride + 1) * h, "taille brute inattendue"
    out = bytearray()
    for y in range(h):
        assert data[y * (stride + 1)] == 0, "ligne filtrée : filtre None attendu"
        out += data[y * (stride + 1) + 1:(y + 1) * (stride + 1)]
    return w, h, nch, bytes(out)


def _positions(raw: bytes, tag: bytes) -> list:
    out, i = [], 8
    while i + 8 <= len(raw):
        ln = int.from_bytes(raw[i:i + 4], "big")
        if raw[i + 4:i + 8] == tag:
            out.append(i)
        if raw[i + 4:i + 8] == b"IEND":
            break
        i += 12 + ln
    return out


def _multiples_de_257(payload: bytes) -> float:
    """Part des valeurs 16 bits qui valent octet x 257 — donc un octet
    dupliqué, donc AUCUNE précision au-delà de 8 bits. 100 % = conteneur
    creux."""
    n = len(payload) // 2
    egaux = sum(1 for a, b in zip(payload[0::2], payload[1::2]) if a == b)
    return 100.0 * egaux / (n or 1)


# ═══════════════════════ 1. les huit maps ═══════════════════════════════════

def test_les_noms_de_maps_sont_ceux_du_service():
    """`MAP_ORDER` est une recopie assumée : si `pbr_service` bougeait, les
    routes /map/<kind> mentiraient sans que rien ne s'en aperçoive."""
    assert TX.MAP_ORDER == PBR.MAP_KINDS == KINDS
    assert len(TX.MAP_ORDER) == 8


def test_huit_maps_ecrites_et_rapportees():
    """SEUIL : 8 maps produites et affichées (la barre en livre 4)."""
    did = _deck()
    _envoie_source(did, 480, 654)
    st = _derive(did, res=1024, square=False)
    noms = [m["kind"] for m in st["maps"]]
    assert noms == list(KINDS), noms
    assert st["total"] == 8
    for k in KINDS:
        p = _fichier(did, k + ".png")
        assert p.is_file(), f"{k}.png absent"
        assert p.stat().st_size > 200, k
        assert _fichier(did, "thumb_" + k + ".png").is_file(), k
    # AO et HEIGHT, les deux que ni Meshy ni la barre ne livrent
    for absent_ailleurs in ("ao", "height"):
        assert absent_ailleurs in noms


# ═══════════════════════ 2. le catalogue 2D ═════════════════════════════════

def _bloc_catalogue() -> str:
    src = JS.read_text(encoding="utf-8")
    a = src.index("CF-TEXTURE-CATALOG-BEGIN")
    b = src.index("CF-TEXTURE-CATALOG-END")
    return src[a:b]


def test_catalogue_local_au_moins_24_matieres():
    """SEUIL : >= 24 matières 2D livrées en local, 0 octet réseau."""
    bloc = _bloc_catalogue()
    ids = re.findall(r"\{\s*id:\s*\"([a-z0-9_]+)\"", bloc)
    assert len(ids) >= 24, f"{len(ids)} matières seulement"
    assert len(set(ids)) == len(ids), "identifiants de matière en double"
    # chaque matière pointe une recette qui existe VRAIMENT dans le fichier
    src = JS.read_text(encoding="utf-8")
    recettes = set(re.findall(r"^    (\w+)\(S, m, seed\) \{", src, re.M))
    used = set(re.findall(r"gen:\s*\"(\w+)\"", bloc))
    assert used <= recettes, f"recettes manquantes : {used - recettes}"


def test_zero_octet_reseau():
    """Aucune URL absolue, aucun CDN, aucune police distante : le catalogue
    est PROCÉDURAL. C'est ce qui lui donne aussi une résolution illimitée là
    où la barre livre des PNG de 512 px."""
    for f in (JS, CSS):
        src = f.read_text(encoding="utf-8")
        assert "http://" not in src, f
        assert "https://" not in src, f
        assert "//cdn" not in src, f
        assert "@import" not in src or f is not JS


def test_le_catalogue_porte_la_physique_de_chaque_matiere():
    """MANQUE CORRIGÉ : « le catalogue propose Or brossé, Argent brossé,
    Cuivre patiné et Acier peigné, et rien ne relie le choix d'un support
    métallique à une map metallic non nulle — le jour où un utilisateur
    choisit Or brossé et exporte une metallic à zéro, il exporte du plastique
    doré. »

    Chaque matière porte donc sa métallicité et sa rugosité, et choisir une
    matière aligne les niveaux cuits (`pickMat`)."""
    bloc = _bloc_catalogue()
    ents = re.findall(r'\{\s*id:\s*"([a-z0-9_]+)".*?cat:\s*"([^"]+)".*?'
                      r'mtl:\s*([01]),\s*rgh:\s*([\d.]+)\s*\}', bloc, re.S)
    ids = re.findall(r'\{\s*id:\s*"([a-z0-9_]+)"', bloc)
    assert len(ents) == len(ids), "une matière sans mtl/rgh"
    metaux = [e for e in ents if e[1] == "métal"]
    assert len(metaux) >= 4, metaux
    for mid, cat, mtl, rgh in ents:
        assert 0.0 <= float(rgh) <= 1.0, mid
        if cat == "métal" and mid != "carbone":     # la fibre de carbone est un composite
            assert mtl == "1", f"{mid} est classé métal mais mtl={mtl}"
        if cat in ("papier", "textile"):
            assert mtl == "0", mid
    src = JS.read_text(encoding="utf-8")
    assert "function pickMat" in src
    assert re.search(r"pickMat[\s\S]{0,700}levels:\s*\{\s*metallic:\s*m\.mtl,\s*roughness:\s*m\.rgh",
                     src), "choisir une matière n'aligne pas les niveaux cuits"
    assert "plastique doré" in src, "aucun avertissement quand métal et niveau divergent"


def test_l_apercu_eclaire_existe_et_part_des_maps_livrees():
    """LE PLUS GROS MANQUE nommé par la critique : « il produit huit maps
    mesurées et ne donne pas un seul moyen de les voir fonctionner — huit
    vignettes plates, ni lumière, ni rotation, ni environnement », alors que
    la condition de victoire du spec est justement « le grain accroche la
    lumière différemment selon l'angle ».

    Le test vérifie que la table lumineuse existe, qu'elle part des maps
    RÉELLEMENT servies par l'API (et non d'un rendu maison), qu'on peut
    déplacer la lumière et couper chaque map."""
    src = JS.read_text(encoding="utf-8")
    assert 'cv.id = "cf-texture-lit"' in src, "aucune toile de re-éclairage"
    for kind in ("basecolor", "normal", "roughness", "ao"):
        assert f'"{kind}"' in src
    assert 'M.api.url("thumb/" + need[i])' in src, \
        "l'aperçu n'utilise pas les vignettes servies par l'API"
    assert "function litDraw" in src and "createImageData" in src
    assert "nrm[i] / 127.5 - 1" in src, "la normale n'est pas décodée (n = 2c - 1)"
    assert "pointerdown" in src and "pointermove" in src, "lumière non déplaçable"
    assert "litSweep" in src and "requestAnimationFrame" in src
    for cut in ("useN", "useR", "useAO"):
        assert cut in src, cut
    assert len(re.findall(r'\{ id: "(rasant|studio|chaud|nuit)"', src)) == 4, \
        "moins de quatre environnements"
    # …et toujours zéro octet réseau : aucun moteur 3D distant
    assert "http" not in src


def test_le_raccord_de_tuile_est_mesure_a_l_ecran():
    """MANQUE CORRIGÉ : « aucun tuilage, aucune vérification de raccord —
    alors que le panneau mesure tout le reste ».

    POURQUOI CE TEST A CHANGÉ, ET CE QU'IL EXIGE MAINTENANT. Il verrouillait
    les paliers de l'écran sur ceux de `pbr_service` — « deux échelles pour une
    même notion, c'est un verdict qui ment ». Le principe tient ; ce n'est plus
    la même notion. `pbr_service.seam_report` gradue un RAPPORT À LA MÉDIANE ;
    cet écran gradue un EXCÈS SUR LA PIRE MARCHE INTERNE, parce que le premier
    condamnait des tuiles arithmétiquement parfaites (toile de jute : raccord
    40,27, pire marche interne 40,25, verdict publié « 7,28x, couture
    visible »). Deux quantités, donc deux échelles — et la parité qui compte
    désormais est celle des DEUX FICHIERS DE CETTE PIÈCE, l'écran et le
    backend, qui doivent grader le même nombre pareil. L'ancien rapport reste
    calculé et publié sous son nom (`ratio_median`) : un chiffre qu'on retire
    sans le dire est un chiffre qu'on cache.

    TROISIÈME TOUR — CE QUI TRAVERSE ENCORE, ET CE QUI NE TRAVERSE PLUS. La
    parité portait sur une TABLE DE MOTS partagée entre l'écran et le service
    (« invisible », « discret », « visible », « cassé »). L'écran n'imprime
    plus aucun de ces mots : un mot de conclusion écrit par celui qui produit
    la mesure ne dit rien de plus que le nombre, et il survit au lecteur qui,
    avec le même fichier et un autre étalon, conclut l'inverse. Ce qui doit
    encore être commun aux deux fichiers, c'est le SEUIL — le nombre à partir
    duquel l'écran met un chiffre en avertissement — et il vaut le premier
    palier du service. La table de mots reste côté service, où elle ne
    s'imprime nulle part."""
    src = JS.read_text(encoding="utf-8")
    assert "function seamOf" in src
    seuil = re.search(r"const SEAM_ALERT = ([\d.]+);", src)
    assert seuil, "seuil d'alerte absent de l'écran"
    assert float(seuil.group(1)) == float(TX.SEAM_GRADES[0][0]), \
        (seuil.group(1), TX.SEAM_GRADES)
    assert "const SEAM_GRADES" not in src, "l'écran garde une table de verdicts"
    assert "seamGrade" not in src, "l'écran grade encore"
    # l'ancienne quantité n'a pas disparu : elle est nommée
    assert "ratio_median" in src and "ratio_median" in \
        (REPO / "backend" / "app" / "services" / "cards" / "texture.py").read_text(encoding="utf-8")
    # et l'AVERTISSEMENT se prend sur l'excès ARRONDI à la précision où il est
    # publié (voir seamOfLum) : jamais sur un écart qu'on ne montre pas
    assert "Math.round(exces * 100) / 100" in src, \
        "l'avertissement et le nombre affiché ne sortent pas du même arrondi"
    assert "Mesurer les " in src and 'MATS.length + " tuiles"' in src
    assert "cf-texture-seam" in src


def test_les_chiffres_affiches_ne_comptent_pas_le_contenant():
    """« Le badge 10 effets compte Aucun comme un effet : il y en a 9 réels.
    Petit, mais c'est le même péché que le 16 bits — compter le contenant. »
    Et l'infobulle de résolution annonçait « 4096 x 4096 px » même quand la
    sortie faisait 3008 x 4096."""
    src = JS.read_text(encoding="utf-8")
    assert "(OVERS.length - 1) + \" effets\"" in src, "le compte d'effets compte « Aucun »"
    assert 'r + " x " + r + " px"' not in src, \
        "l'infobulle de résolution annonce un carré même hors atlas"
    assert "function outPx" in src and "outPx(g, r, s.pbr.square)" in src
    # …et le seuil de 300 DPI du cahier des charges est vérifié À L'ÉCRAN :
    # sur une carte de 69 mm, 1k tombe à 277 DPI (mesuré sur l'app installée).
    assert "sous les 300 DPI d'une impression" in src, \
        "l'écran ne dit pas quand la définition choisie passe sous 300 DPI"
    # le commentaire d'en-tête doit compter les matières qui existent VRAIMENT
    ids = re.findall(r'\{\s*id:\s*"([a-z0-9_]+)"', _bloc_catalogue())
    assert f"{len(ids)} matieres PROCEDURALES" in src, \
        f"l'en-tête n'annonce pas {len(ids)} matières"


def test_les_bornes_de_derivation_sont_celles_du_service():
    """Le miroir JS des réglages est comparé au service. Deux tables pour un
    même réglage, c'est un curseur qui ment à mi-course."""
    src = JS.read_text(encoding="utf-8")
    bloc = src[src.index("const DERIVE_UI"):src.index("const KINDS")]
    vus = {}
    for line in bloc.splitlines():
        m = re.search(r'\{\s*k:\s*"(\w+)"', line)
        if not m:
            continue
        key = m.group(1)
        ent = {}
        for name in ("min", "max", "def"):
            mm = re.search(name + r':\s*(-?[\d.]+|true|false|"[a-z]+")', line)
            if mm:
                raw = mm.group(1)
                ent[name] = (True if raw == "true" else False if raw == "false"
                             else raw.strip('"') if raw.startswith('"')
                             else float(raw))
        vus[key] = ent
    assert set(vus) == set(PBR.DERIVE_DEFAULTS), set(vus) ^ set(PBR.DERIVE_DEFAULTS)
    for key, ent in vus.items():
        att = PBR.DERIVE_DEFAULTS[key]
        got = ent["def"]
        if isinstance(att, bool) or isinstance(att, str):
            assert got == att, f"{key}: défaut {got!r} != {att!r}"
        else:
            assert abs(float(got) - float(att)) < 1e-9, f"{key}: {got} != {att}"
        if key in PBR.DERIVE_RANGES and "min" in ent:
            lo, hi = PBR.DERIVE_RANGES[key]
            assert (ent["min"], ent["max"]) == (lo, hi), f"{key}: bornes"


# ═══════════════════════ 3. la mesure vient des octets ══════════════════════

def test_chaque_chiffre_est_relu_sur_les_octets_ecrits():
    """SEUIL : chaque map porte une mesure lue sur les octets encodés
    (`map_report` / `effective_levels`), pas une promesse de curseur.

    On rouvre les PNG DEPUIS LE DISQUE et on recalcule : le rapport servi
    doit tomber exactement dessus. Un rapport calculé sur les images en
    mémoire (avant encodage) divergerait sur les maps 16 bits."""
    did = _deck()
    _envoie_source(did, 480, 654)
    st = _derive(did, res=1024, square=True,
                 levels={"metallic": 0.25, "roughness": 0.6})
    relu = {}
    for m in st["maps"]:
        p = _fichier(did, m["kind"] + ".png")
        data = p.read_bytes()
        img = Image.open(io.BytesIO(data))
        img.load()
        relu[m["kind"]] = _huit_bits(img, m["kind"])
        assert m["bytes"] == len(data), m["kind"]
        assert (m["w"], m["h"]) == relu[m["kind"]].size, m["kind"]
    rep = PBR.map_report(relu, relu["basecolor"])
    for m in st["maps"]:
        ref = rep["maps"][m["kind"]]
        if m["bits"] == 16:
            # L'AMPLITUDE AUSSI SE LIT SUR SEIZE BITS. `map_report` la mesure
            # sur une VUE 8 bits — et pas la même selon la map (octet fort
            # pour un RVB, `v/257` arrondi pour un gris) : deux réductions,
            # deux résultats sur les mêmes octets. L'oracle est donc le
            # fichier, relu sur ses 65 536 classes.
            exact = TX._span16(_fichier(did, m["kind"] + ".png").read_bytes())
            assert m["span"] == exact, (m["kind"], m["span"], exact)
            assert abs(m["span"] - ref["span"]) <= 1.0, \
                (m["kind"], m["span"], ref["span"])
        else:
            assert m["span"] == ref["span"], m["kind"]
        attendu = ref["mean"]
        if m["bits"] == 16:
            # UNE MAP 16 BITS SE MESURE SUR SEIZE BITS. Pillow ne rend que
            # l'octet fort d'un RVB 16 bits, et réduire soi-même à 8 bits
            # ajoute un biais d'arrondi (mesuré : +0,34/255 sur la normale).
            # L'oracle recalcule donc la moyenne exacte sur la charge utile —
            # c'est CE chiffre-là que le panneau doit afficher.
            w, h, nch, pay = _payload16(
                _fichier(did, m["kind"] + ".png").read_bytes())
            pas = 2 * nch
            attendu = sum((pay[i * pas] << 8) | pay[i * pas + 1]
                          for i in range(w * h)) / float(w * h) / 257.0
            if nch == 3:
                # c'est le RVB que Pillow tronque : sur une map grise il passe
                # par `convert("I")` et divise correctement, d'où l'égalité.
                assert abs(attendu - ref["mean"]) > 0.05, (
                    f"{m['kind']}: l'octet fort et les seize bits donnent le "
                    "même chiffre — le test ne prouve plus rien")
        assert abs(m["mean255"] - attendu) < 0.01, (m["kind"], m["mean255"], attendu)
        assert m["informative"] is bool(ref["informative"]), m["kind"]
        # la note servie est celle du service REECRITE pour un
        # utilisateur (`note_utilisateur`) : l'oracle applique la meme
        # transformation, sinon il verrouillerait le verdict qu'on retire.
        assert m["note"] == TX.note_utilisateur(ref["note"]), m["kind"]
    eff = PBR.effective_levels(relu)
    assert abs(st["effective"]["roughness"] - eff["roughness"]) < 1e-9
    assert abs(st["effective"]["metallic"] - eff["metallic"]) < 1e-9
    # …et le niveau CUIT est bien celui qui a été demandé (±2/255, la
    # garantie de `bake_levels`) : la mesure et le réglage se rejoignent.
    assert abs(eff["metallic"] - 0.25) <= 2 / 255.0, eff
    assert abs(eff["roughness"] - 0.6) <= 2 / 255.0, eff


def test_la_moyenne_de_la_base_color_est_bien_la_luminance_rec601():
    """REPROCHE MESURÉ : « moy 0,386 ne se reproduit sous aucune des 8
    définitions de luminance testées ». Vérifié ici avec un oracle écrit dans
    ce fichier : la moyenne affichée EST la luminance ITU-R 601 des octets
    livrés (0.299 R + 0.587 V + 0.114 B), au demi-niveau près — l'écart de
    l'arrondi par pixel de `convert("L")`.

    Et l'amplitude affichée est le p95 - p5 de la MÊME luminance : les deux
    chiffres d'une même vignette portent bien sur la même base."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=2048, square=False)
    bc = [m for m in st["maps"] if m["kind"] == "basecolor"][0]
    img = Image.open(_fichier(did, "basecolor.png")).convert("RGB")
    from PIL import ImageStat
    mr, mg, mb = ImageStat.Stat(img).mean
    rec601 = 0.299 * mr + 0.587 * mg + 0.114 * mb
    assert abs(bc["mean255"] - rec601) < 0.5, (bc["mean255"], rec601)
    assert abs(bc["mean"] - rec601 / 255.0) < 0.002
    h = img.convert("L").histogram()
    n = sum(h)
    acc, p5, p95 = 0, None, None
    for i, c in enumerate(h):
        acc += c
        if p5 is None and acc >= 0.05 * n:
            p5 = i
        if p95 is None and acc >= 0.95 * n:
            p95 = i
    assert bc["span"] == p95 - p5, (bc["span"], p95 - p5)
    assert bc["channel"] == "luminance"


def test_les_deux_correlations_sont_publiees_et_etiquetees():
    """REPROCHE MESURÉ : « le r = +0,97 imprimé sous la Hauteur ne se
    reproduit pas — je mesure +0,86 ».

    Il se reproduit : `pbr_service.correlation` réduit en blocs 192x192 (BOX)
    avant Pearson. Mais la définition n'était pas à l'écran, et à pleine
    résolution le nombre est un autre. On publie donc les DEUX, étiquetés, et
    ce test les recalcule tous les deux avec son propre oracle."""
    did = _deck()
    _envoie_source(did, 480, 654)
    st = _derive(did, res=1024, square=True)
    relu = {}
    for m in st["maps"]:
        img = Image.open(_fichier(did, m["kind"] + ".png"))
        img.load()
        relu[m["kind"]] = _huit_bits(img, m["kind"])
    lum = relu["basecolor"].convert("L")

    def pearson(a, b):
        A, B = a.tobytes(), b.tobytes()
        n = len(A)
        ma, mb = sum(A) / n, sum(B) / n
        sa = sb = sab = 0.0
        for x, y in zip(A, B):
            dx, dy = x - ma, y - mb
            sa += dx * dx
            sb += dy * dy
            sab += dx * dy
        return sab / math.sqrt(sa * sb) if sa > 1e-9 and sb > 1e-9 else 0.0

    vus = 0
    for m in st["maps"]:
        k = m["kind"]
        if k == "basecolor":
            continue
        ch = (relu[k].convert("RGB").split()[0] if k == "normal"
              else relu[k].convert("RGB").split()[1] if k == "orm"
              else relu[k].convert("L"))
        if PBR.stats(ch)["span"] <= PBR.FLAT_SPAN:
            continue                       # une constante ne corrèle avec rien
        assert abs(m["corr_lum"] - PBR.correlation(ch, lum)) < 0.002, k
        assert abs(m["corr_full"] - pearson(ch, lum)) < 0.01, \
            (k, m["corr_full"], pearson(ch, lum))
        vus += 1
    assert vus >= 3, "aucune map informative à corréler"


def test_une_map_vide_est_annoncee_vide():
    """Un compte de « 8 maps » n'est honnête que si les plates sont dites
    plates. `emissive_threshold` à 1.0 : plus rien n'émet."""
    did = _deck()
    _envoie_source(did, 400, 545)
    st = _derive(did, res=1024, square=True,
                 derive={"emissive_threshold": 1.0})
    em = [m for m in st["maps"] if m["kind"] == "emissive"][0]
    assert em["informative"] is False
    assert "aucun pixel au-dessus du seuil" in em["note"], em["note"]
    assert st["informative"] < st["total"], "aucune map n'est comptée plate"
    assert st["total"] == 8


# ═══════════════════════ 4. 4096 et 16 bits ═════════════════════════════════

def test_4k_et_16_bits_sur_le_fichier():
    """SEUIL : 4k = 4096x4096 disponible ; `height` et `normal` encodables en
    16 bits. La profondeur est lue dans l'IHDR du fichier écrit, pas déduite
    du booléen de la requête."""
    did = _deck()
    _envoie_source(did, 512, 512)
    t0 = time.perf_counter()
    st = _derive(did, res=4096, square=True, bits16=True)
    dt = time.perf_counter() - t0
    for m in st["maps"]:
        assert (m["w"], m["h"]) == (4096, 4096), (m["kind"], m["w"], m["h"])
        data = _fichier(did, m["kind"] + ".png").read_bytes()
        prof = TX.png_depth(data)
        attendu = 16 if m["kind"] in ("height", "normal") else 8
        assert prof == attendu, f"{m['kind']}: IHDR {prof} bits"
        assert m["bits"] == attendu, m["kind"]
        with Image.open(io.BytesIO(data)) as im:
            assert im.size == (4096, 4096), m["kind"]
    print(f"\n4096x4096 x8 maps : {dt:.1f} s")


def test_une_map_16_bits_ne_se_mesure_pas_comme_plate():
    """RÉGRESSION, trouvée à l'écran : la hauteur en 16 bits s'affichait
    « uniforme — surface parfaitement plate », moy 0,969, amplitude 0/255.

    La cause n'était pas la map mais sa RELECTURE : `convert("L")` depuis
    `I;16` écrête à 255. Le seuil « chaque map porte une mesure lue sur les
    octets encodés » se retournait donc contre lui-même — la mesure était
    fausse précisément parce qu'elle passait par le fichier. On compare ici
    les deux encodages du MÊME contenu : 16 bits et 8 bits doivent rapporter
    exactement la même chose (l'encodage 16 bits est v*257, sans perte)."""
    did = _deck()
    _envoie_source(did, 480, 654)
    a = {m["kind"]: m for m in _derive(did, res=1024, square=True, bits16=True)["maps"]}
    b = {m["kind"]: m for m in _derive(did, res=1024, square=True, bits16=False)["maps"]}
    for kind in ("height", "normal"):
        assert a[kind]["bits"] == 16 and b[kind]["bits"] == 8, kind
        # Un niveau de tolérance : les deux sorties viennent du MÊME calcul
        # flottant, quantifié une fois sur 65535 et une fois sur 255. Relire
        # la 16 bits en octets (v/257) ne peut pas rendre exactement le même
        # arrondi partout — l'écart mesuré est d'un niveau au plus.
        assert abs(a[kind]["span"] - b[kind]["span"]) <= 1, \
            f"{kind}: amplitude {a[kind]['span']} en 16 bits contre {b[kind]['span']} en 8"
        # UN DEMI-NIVEAU, et pas moins : la moyenne de la version 16 bits est
        # désormais calculée SUR SEIZE BITS (`_mean16`), celle de la version 8
        # bits sur des valeurs arrondies au niveau. Chaque pixel bouge d'au
        # plus 0,5 niveau à l'arrondi, donc la moyenne aussi — c'est une borne
        # démontrable, pas un seuil de confort. Mesuré : 0,34/255 sur la
        # normale, 0,00 sur la hauteur.
        assert abs(a[kind]["mean255"] - b[kind]["mean255"]) <= 0.5, \
            (kind, a[kind]["mean255"], b[kind]["mean255"])
        assert a[kind]["informative"] is b[kind]["informative"], kind
    assert a["height"]["span"] > 2, \
        "une carte contrastée ne donne pas une hauteur plate"
    assert a["height"]["informative"] is True


def test_16_bits_desactivable():
    """Le drapeau agit vraiment : sans lui, les huit maps sont en 8 bits."""
    did = _deck()
    _envoie_source(did, 300, 408)
    st = _derive(did, res=1024, square=False, bits16=False)
    for m in st["maps"]:
        assert m["bits"] == 8, m["kind"]
        assert TX.png_depth(_fichier(did, m["kind"] + ".png").read_bytes()) == 8


# ═══════════════ 4 bis. LE 16 BITS N'EST PLUS CREUX ═════════════════════════

def test_le_16_bits_porte_vraiment_plus_que_8_bits():
    """MANQUE CORRIGÉ (nommé par les DEUX critiques, « le plus gros » de l'un).

    AVANT : `material_store._png16` duplique chaque octet (v -> v*257).
    Mesuré sur les fichiers livrés : octet fort == octet faible sur
    3 080 192 / 3 080 192 pixels de height.png et 9 240 576 / 9 240 576
    échantillons de normal.png — 100,0 % de valeurs multiples de 257, donc
    conteneur 16 bits et charge utile 8 bits, pour 2,36 Mo de ZIP.

    APRÈS : hauteur et normale sont recalculées en flottant à la résolution
    de sortie, où le rééchantillonnage produit de vraies valeurs sous-niveau.
    Le test décompresse l'IDAT lui-même — il ne croit pas l'IHDR."""
    did = _deck()
    _envoie_source(did, 480, 654)
    st = _derive(did, res=1024, square=True, bits16=True)
    par = {m["kind"]: m for m in st["maps"]}
    for kind in ("height", "normal"):
        raw = _fichier(did, kind + ".png").read_bytes()
        assert TX.png_depth(raw) == 16, kind
        w, h, nch, pay = _payload16(raw)
        creux = _multiples_de_257(pay)
        assert creux < 90.0, (
            f"{kind}: {creux:.1f} % des valeurs sont des multiples de 257 — "
            "conteneur 16 bits, charge utile 8 bits")
        # …et le chiffre AFFICHÉ est ce même comptage, à l'unité près
        assert abs(par[kind]["sub"] - (100.0 - creux)) < 0.5, \
            (kind, par[kind]["sub"], 100.0 - creux)
        assert par[kind]["bits"] == 16 and par[kind]["bits_asked"] == 16
        # des valeurs 16 bits réellement distinctes, pas 256 recopies
        vues = {(pay[i] << 8) | pay[i + 1] for i in range(0, min(len(pay), 600000), 2)}
        assert len(vues) > 300, f"{kind}: {len(vues)} valeurs 16 bits distinctes"


def test_16_bits_sans_gain_retombe_en_8_bits_et_le_dit():
    """« Une map peut porter moins que ce qu'on lui a demandé, et alors c'est
    écrit » — la règle du panneau s'applique enfin à la PROFONDEUR.

    Source carrée 1024 et sortie 1024 : aucune interpolation, donc la HAUTEUR
    n'a rien à porter au-delà de 8 bits — on écrit 8 bits et on le dit. La
    NORMALE, elle, garde ses 16 bits même sans rééchantillonnage : la
    division par la longueur crée de vraies valeurs sous-niveau. La règle est
    la même pour les deux — c'est la MESURE qui tranche, pas une préférence.
    """
    did = _deck()
    _envoie_source(did, 1024, 1024)
    st = _derive(did, res=1024, square=True, bits16=True)
    par = {m["kind"]: m for m in st["maps"]}
    h = par["height"]
    assert h["bits"] == 8 and h["bits_asked"] == 16 and h["sub"] == 0.0, h
    # la phrase est écrite pour l'utilisateur — ce qu'il reçoit, et ce que ça
    # lui économise — et elle garde son chiffre.
    assert "16 bits sans effet" in h["note16"], h["note16"]
    assert "Ko de moins" in h["note16"], h["note16"]
    assert TX.png_depth(_fichier(did, "height.png").read_bytes()) == 8
    n = par["normal"]
    assert n["bits"] == 16 and n["sub"] > 50.0, n
    raw = _fichier(did, "normal.png").read_bytes()
    # 100 % = conteneur creux. Le reste tient aux pixels PARFAITEMENT plats,
    # dont le Z vaut 1 donc 65535 = 255 x 257 : un multiple légitime.
    assert _multiples_de_257(_payload16(raw)[3]) < 50.0


def test_la_normale_est_un_champ_de_vecteurs_unitaires():
    """MANQUE CORRIGÉ — le seul terrain où la barre était strictement
    meilleure. Le service reconstruit Z par LUT 8 bits avec écrêtage : mesuré
    |n| moyenne 0,9940, max 1,0075, 1,52 % des pixels à plus de 5 % de
    l'unité et 0,3982 % à z<0, ce qui n'existe pas en espace tangent.

    Ici la normale est recomposée par DIVISION en flottant. Le test décode le
    fichier 16 bits avec le décodage des moteurs (n = 2c - 1) et vérifie la
    longueur — la mesure que le panneau ne faisait jamais."""
    did = _deck()
    _envoie_source(did, 480, 654)
    st = _derive(did, res=1024, square=True, bits16=True)
    raw = _fichier(did, "normal.png").read_bytes()
    w, h, nch, pay = _payload16(raw)
    assert nch == 3
    pire, zneg, somme, n = 0.0, 0, 0.0, 0
    for i in range(0, w * h, 7):             # un pixel sur sept : 150k mesures
        o = i * 6
        x = 2 * ((pay[o] << 8) | pay[o + 1]) / 65535.0 - 1
        y = 2 * ((pay[o + 2] << 8) | pay[o + 3]) / 65535.0 - 1
        z = 2 * ((pay[o + 4] << 8) | pay[o + 5]) / 65535.0 - 1
        ln = math.sqrt(x * x + y * y + z * z)
        pire = max(pire, abs(ln - 1.0))
        somme += ln
        n += 1
        if z <= 0:
            zneg += 1
    assert zneg == 0, f"{zneg} pixels à z<=0 (impossible en espace tangent)"
    assert pire < 0.01, f"|n| s'écarte de {pire:.4f} de l'unité"
    assert abs(somme / n - 1.0) < 0.001, somme / n
    # …et le rapport affiché dit la même chose
    u = st["unit_normal"]
    assert u["unit_pct"] == 100.0 and u["zneg"] == 0, u
    assert abs(u["mean"] - 1.0) < 0.001, u
    assert u["bits"] == 16, u


def test_chaque_png_porte_son_espace_colorimetrique_et_sa_densite():
    """MANQUE CORRIGÉ — la moitié mesurable du cahier des charges.

    AVANT : les 8 PNG ne portaient que IHDR / IDAT / IEND. Aucun `pHYs`
    (un PNG sans densité entre à 72 DPI dans tout outil d'impression, quelle
    que soit la promesse de l'écran) et aucun espace colorimétrique, alors
    que le lot mélange deux maps sRGB et six linéaires.

    APRÈS : `gAMA` partout, `sRGB` sur les deux maps de couleur seulement,
    `pHYs` calculé sur la géométrie du document — et vérifié ICI contre la
    même géométrie, recalculée par le test."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=2048, square=False)
    g = CC.geom_of(CC.read_deck(did))
    mm_w = g.trim_mm[0] + 2 * g.bleed_mm
    mm_h = g.trim_mm[1] + 2 * g.bleed_mm
    for m in st["maps"]:
        raw = _fichier(did, m["kind"] + ".png").read_bytes()
        tags = _chunks(raw)
        assert "pHYs" in tags, f"{m['kind']} sans dimensions physiques"
        assert "gAMA" in tags, f"{m['kind']} sans gamma"
        srgb = m["kind"] in ("basecolor", "emissive")
        assert ("sRGB" in tags) is srgb, (m["kind"], tags)
        assert m["space"] == ("sRGB" if srgb else "linéaire")
        x, y, unit = struct.unpack(">IIB", _chunk_body(raw, b"pHYs")[:9])
        assert unit == 1, "unité pHYs != mètre"
        assert abs(x - m["w"] * 1000.0 / mm_w) <= 1, (m["kind"], x)
        assert abs(y - m["h"] * 1000.0 / mm_h) <= 1, (m["kind"], y)
        # 300 DPI est un PLANCHER : la carte fait 69 x 94 mm fond perdu compris
        assert m["dpi"][0] >= 300 and m["dpi"][1] >= 300, (m["kind"], m["dpi"])
        assert _chunk_body(raw, b"gAMA") == struct.pack(
            ">I", 45455 if srgb else 100000), m["kind"]
    assert st["phys"]["mm"] == [round(mm_w, 2), round(mm_h, 2)]
    assert st["phys"]["bleed_mm"] == g.bleed_mm
    assert st["phys"]["safe_mm"] == g.safe_mm


def test_le_manifeste_decrit_le_lot():
    """MANQUE CORRIGÉ : « le ZIP n'a aucun manifeste, les noms de fichiers
    sont le seul contrat » (la barre, elle, embarque un manifeste C2PA)."""
    import hashlib
    did = _deck()
    _envoie_source(did, 400, 545)
    _derive(did, res=1024, square=False)
    r = _api("GET", f"/api/cards/{did}/texture/manifest")
    assert r.status_code == 200, r.text
    mf = r.json()
    assert [m["kind"] for m in mf["maps"]] == list(KINDS)
    assert "R = occlusion" in mf["conventions"]["orm"]
    assert "unité" in mf["conventions"]["normale"]
    assert mf["conventions"]["espaces"]["basecolor"] == "sRGB"
    assert mf["conventions"]["espaces"]["roughness"] == "linéaire"
    assert mf["carte"]["fond_perdu_mm"] > 0 and mf["carte"]["zone_sure_mm"] > 0
    for m in mf["maps"]:
        octets = _fichier(did, m["fichier"]).read_bytes()
        assert m["octets"] == len(octets), m["fichier"]
        assert m["sha256"] == hashlib.sha256(octets).hexdigest(), m["fichier"]
    r = _api("DELETE", f"/api/cards/{did}/texture/maps")
    assert r.status_code == 200
    assert _api("GET", f"/api/cards/{did}/texture/manifest").status_code == 409


# ═══════════════════════ 5. la convention ORM ═══════════════════════════════

def test_orm_r_ao_v_rugosite_b_metal():
    """SEUIL : l'ORM respecte R = AO, V = rugosité, B = métallique, vérifié en
    relisant les canaux des fichiers écrits. La source est carrée et la
    résolution de sortie l'est aussi : aucun rééchantillonnage ne s'intercale,
    l'égalité doit donc être EXACTE, à l'octet."""
    did = _deck()
    _envoie_source(did, 1024, 1024)
    _derive(did, res=1024, square=True,
            levels={"metallic": 0.4, "roughness": 0.55})
    orm = Image.open(_fichier(did, "orm.png")).convert("RGB")
    r, g, b = orm.split()
    paires = {"ao": r, "roughness": g, "metallic": b}
    for kind, canal in paires.items():
        seul = Image.open(_fichier(did, kind + ".png")).convert("L")
        diff = ImageChops.difference(canal, seul)
        assert diff.getextrema()[1] == 0, \
            f"canal ORM {kind} != {kind}.png (écart max {diff.getextrema()[1]})"
    # …et l'ordre n'est pas celui du hasard : AO clair, métal sombre.
    st = TX.read_state(did)
    par = {m["kind"]: m for m in st["maps"]}
    assert par["ao"]["mean"] > par["metallic"]["mean"], \
        "R et B semblent inversés dans l'ORM"


# ═══════════════════════ 6. l'API, telle qu'elle répond ═════════════════════

def test_le_parcours_complet_par_http():
    """Source -> dérivation -> état -> map -> vignette -> planche, en HTTP."""
    did = _deck()
    r = _api("GET", f"/api/cards/{did}/texture/state")
    assert r.status_code == 200 and r.json()["texture"]["maps"] == []
    assert r.json()["texture"]["source"]["ready"] is False

    r = _api("GET", f"/api/cards/{did}/texture/defaults")
    assert r.status_code == 200
    d = r.json()
    assert d["defaults"] == PBR.DERIVE_DEFAULTS
    assert d["kinds"] == list(KINDS) and d["res_choices"] == [1024, 2048, 4096]

    src = _envoie_source(did, 400, 545)
    assert src["w"] == 400 and src["h"] == 545

    st = _derive(did, res=1024, square=False)
    assert st["ms"] > 0 and st["work_px"] and st["out_px"]

    r = _api("GET", f"/api/cards/{did}/texture/map/normal")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert TX.png_depth(r.content) == 16
    r = _api("GET", f"/api/cards/{did}/texture/thumb/orm")
    assert r.status_code == 200 and r.content[:8] == b"\x89PNG\r\n\x1a\n"
    with Image.open(io.BytesIO(r.content)) as im:
        assert max(im.size) <= TX.THUMB_PX

    r = _api("GET", f"/api/cards/{did}/texture/sheet")
    assert r.status_code == 200
    with Image.open(io.BytesIO(r.content)) as im:
        assert im.size[0] > 1000 and im.size[1] > 600

    r = _api("DELETE", f"/api/cards/{did}/texture/maps")
    assert r.status_code == 200 and r.json()["removed"] == 16
    assert _api("GET", f"/api/cards/{did}/texture/map/ao").status_code == 404


def test_la_planche_sait_ecrire_les_accents():
    """La planche est une planche de MESURES : « rugosité » rendu
    « rugosit▯ » et « — » en carré, c'est la moitié des mots illisible.
    Mesuré sur la police par défaut de Pillow, d'où le repli sur les polices
    déjà servies par l'app. Le contrôle compare le dessin de « é » à celui du
    glyphe manquant : identiques = la police n'a pas l'accent."""
    from PIL import ImageFont
    f = TX._font(20)
    assert isinstance(f, ImageFont.FreeTypeFont), "police bitmap de secours"
    def _pix(ch):
        m = f.getmask(ch)
        return (m.size, bytes(m))
    assert _pix("é") != _pix("￿"), "« é » se dessine comme le glyphe manquant"
    assert _pix("—") != _pix("￿"), "« — » se dessine comme le glyphe manquant"
    assert _pix("·") != _pix("￿")


def test_matiere_importee_aller_retour():
    """Le glisser-déposer : une image montée, servie, et bornée en taille."""
    did = _deck()
    r = _api("POST", f"/api/cards/{did}/texture/paper",
             content=_carte(3000, 2000), headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    p = r.json()["paper"]
    assert max(p["w"], p["h"]) == TX.PAPER_MAX_PX
    r = _api("GET", f"/api/cards/{did}/texture/paper")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert TX.read_state(did)["source"]["custom"] is True


def test_jamais_500_sur_un_corps_malforme():
    """Spec §2.5 : un corps mal formé ne doit JAMAIS faire 500."""
    did = _deck()
    _envoie_source(did, 240, 330)
    for corps in ({"derive": "n'importe quoi"}, {"derive": {"ao_radius": "x"}},
                  {"levels": []}, {"levels": {"metallic": None}},
                  {}, None, {"res": 1024, "bits16": "peut-être"},
                  {"derive": {"metallic_mode": "invente"}}):
        r = _api("POST", f"/api/cards/{did}/texture/derive", json=corps)
        assert r.status_code == 200, (corps, r.status_code, r.text[:200])
    # `1e999` est un littéral JSON parfaitement valide que `json.loads` rend
    # en `inf` : c'est LE cas qui a déjà fait un 500 dans `normalize_format`
    # (int(inf) lève). Il ne peut pas s'écrire via `json=` — httpx le refuse —
    # donc on l'envoie tel qu'un vrai client l'enverrait, en octets.
    for cru in (b'{"derive": {"normal_strength": 1e999}}',
                b'{"levels": {"roughness": 1e999}}',
                b'{"res": 1e999}'):
        r = _api("POST", f"/api/cards/{did}/texture/derive", content=cru,
                 headers={"Content-Type": "application/json"})
        assert r.status_code < 500, (cru, r.status_code, r.text[:200])
    for mauvais in ({"res": 777}, {"res": "beaucoup"}, {"res": 4097}):
        r = _api("POST", f"/api/cards/{did}/texture/derive", json=mauvais)
        assert r.status_code in (200, 400), (mauvais, r.status_code)
        if r.status_code == 400:
            assert "Résolution" in r.json()["detail"]
    r = _api("POST", f"/api/cards/{did}/texture/derive", content=b"{{{",
             headers={"Content-Type": "application/json"})
    assert r.status_code < 500, r.status_code


def test_sans_source_pas_de_500_mais_un_404_lisible():
    did = _deck()
    r = _api("POST", f"/api/cards/{did}/texture/derive", json={"res": 1024})
    assert r.status_code == 404
    assert "source" in r.json()["detail"].lower()
    r = _api("GET", f"/api/cards/{did}/texture/sheet")
    assert r.status_code == 409


def test_le_nom_de_map_est_une_liste_blanche():
    """Un nom de map est un identifiant, jamais un chemin."""
    did = _deck()
    for mauvais in ("meta", "..%2f..%2fmeta.json", "source", "report",
                    "BASECOLOR%00", "orm.png.tmp"):
        r = _api("GET", f"/api/cards/{did}/texture/map/{mauvais}")
        assert r.status_code in (400, 404), (mauvais, r.status_code)
        assert "json" in r.headers.get("content-type", "")
    # …et la casse ne sert pas de contournement : elle est normalisée.
    _envoie_source(did, 200, 272)
    _derive(did, res=1024, square=False)
    assert _api("GET", f"/api/cards/{did}/texture/map/BaseColor.PNG").status_code == 200


def test_deck_invalide_ou_absent():
    assert _api("GET", "/api/cards/pas_un_deck/texture/state").status_code == 400
    r = _api("GET", "/api/cards/deck_00000000/texture/state")
    assert r.status_code == 404
    assert "json" in r.headers.get("content-type", "")


# ═══════════════════════ 7. règle 8 et coût ═════════════════════════════════

def test_les_chemins_sont_relatifs_et_confines():
    """Règle 8 : chemins RELATIFS au sous-préfixe, aucun /api, aucun {did}."""
    chemins = [getattr(r, "path", "") for r in TX.router.routes]
    assert chemins, "aucune route déclarée"
    for p in chemins:
        assert not p.startswith("/api"), p
        assert "{did}" not in p and "/cards" not in p, p
    from app.main import app
    montes = [p for p in app.openapi().get("paths", {})
              if p.startswith("/api/cards/{did}/texture")]
    for attendu in ("/api/cards/{did}/texture/state",
                    "/api/cards/{did}/texture/derive",
                    "/api/cards/{did}/texture/map/{kind}",
                    "/api/cards/{did}/texture/sheet"):
        assert attendu in montes, f"{attendu} absent de {montes}"


def test_le_temps_de_derivation_2k():
    """Repère de coût, mesuré sur une carte poker_eu à 300 DPI (815x1110),
    sortie 2048. Rien de gratuit n'est promis : le chiffre est imprimé."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    t0 = time.perf_counter()
    st = _derive(did, res=2048, square=False)
    dt = time.perf_counter() - t0
    print(f"\ncarte 815x1110 -> 8 maps 2k : {dt:.1f} s "
          f"(dérivé à {st['work_px']}, sortie {st['out_px']}, "
          f"rapport {st['ms']} ms)")
    assert dt < 45.0, f"{dt:.1f} s"
    assert st["informative"] >= 6, st["informative"]


# ═══════════════════ 9. ce que les DEUX critiques ont manqué ════════════════
#
# Trois corrections, trois tests. Chacun REPRODUIT d'abord le défaut sur les
# octets, puis prouve qu'il ne peut plus revenir.


def _bourrage16(w: int, h: int, nch: int = 1) -> bytes:
    """Un PNG 16 bits qui MENT : chaque valeur vaut octet x 256, donc l'octet
    faible est nul partout. Charge utile 8 bits, conteneur 16.

    C'est le faux que la mesure « % de valeurs non multiples de 257 » NE VOIT
    PAS : v = k x 256 n'est presque jamais un multiple de 257, donc cette
    mesure seule rend un score quasi parfait (99,6 %) pour une map qui ne
    porte rien de plus que huit bits."""
    plans = []
    for c in range(nch):
        octets = bytearray(w * h * 2)
        for i in range(w * h):
            octets[2 * i] = (i * 7 + c * 31) % 256       # octet fort : varié
            octets[2 * i + 1] = 0                        # octet faible : nul
        plans.append(bytes(octets))
    return TX._png16(plans, (w, h))


def _duplique16(w: int, h: int, nch: int = 1) -> bytes:
    """L'AUTRE faux, celui de `material_store._png16` : v = octet x 257, donc
    octet fort == octet faible."""
    plans = []
    for c in range(nch):
        octets = bytearray(w * h * 2)
        for i in range(w * h):
            v = (i * 7 + c * 31) % 256
            octets[2 * i] = v
            octets[2 * i + 1] = v
        plans.append(bytes(octets))
    return TX._png16(plans, (w, h))


def test_le_bourrage_16_bits_passait_la_mesure_des_multiples_de_257():
    """MANQUE TROUVÉ ICI, contre notre propre panneau — et c'est exactement la
    faute dénoncée par l'audit (« l'IHDR annonçait 16 bits, les échantillons
    tombaient tous sur le réseau 257k »), dans sa SECONDE variante.

    `sub` seul n'attrape que la duplication. Une map bourrée (v = octet x 256)
    obtient 99,61 % — un score excellent — pour huit bits déguisés en seize.
    Le test le MONTRE sur des octets fabriqués ici, puis vérifie que la
    seconde mesure (entropie de l'octet faible) la refuse."""
    faux = _bourrage16(64, 64)
    assert TX.png_depth(faux) == 16
    d = TX._depth16(faux)
    assert d["sub"] > 99.0, ("le bourrage passe la mesure des multiples de 257 "
                             f"avec {d['sub']} %")
    assert d["low_bits"] == 0.0 and d["low_vals"] == 1, d
    # l'autre faux, celui déjà connu, reste attrapé par la première mesure
    dup = _duplique16(64, 64)
    assert TX._depth16(dup)["sub"] == 0.0, TX._depth16(dup)
    # …et les VRAIES maps du produit passent les deux
    did = _deck()
    _envoie_source(did, 480, 654)
    st = _derive(did, res=1024, square=True, bits16=True)
    par = {m["kind"]: m for m in st["maps"]}
    for kind in ("height", "normal"):
        m = par[kind]
        assert m["bits"] == 16, m
        assert m["sub"] > 0.0, m
        assert m["low_bits"] > 1.0, (kind, m["low_bits"])
        assert m["low_vals"] > 100, (kind, m["low_vals"])
        # le chiffre AFFICHÉ est celui du fichier, recalculé ici
        raw = _fichier(did, kind + ".png").read_bytes()
        _, _, _, pay = _payload16(raw)
        vus = {b for b in pay[1::2]}
        assert m["low_vals"] == len(vus), (kind, m["low_vals"], len(vus))


def test_un_faux_16_bits_est_ecrit_en_8_bits_et_le_dit():
    """La règle « une map peut porter moins que ce qu'on lui a demandé, et
    alors c'est écrit » s'applique aux DEUX façons de mentir sur 16 bits.
    `_pick_depth` reçoit ici des plans fabriqués : le fichier retenu doit
    retomber à 8 bits, et la note doit nommer la raison."""
    from PIL import Image
    img8 = Image.new("L", (32, 32), 128)
    # des plans BRUTS big-endian, pas des PNG : c'est ce que reçoit
    # `_pick_depth`. Octet faible nul = bourrage.
    plans_bourres = [bytes(bytearray(
        b for i in range(32 * 32) for b in ((i * 7) % 256, 0)))]
    got = TX._pick_depth("height", img8, plans_bourres, (32, 32))
    assert got["bits"] == 8 and got["asked"] == 16, got
    assert "second octet constant" in got["note16"], got["note16"]
    assert TX.png_depth(got["data"]) == 8
    # duplication : refusée elle aussi, avec l'autre raison
    plans_dup = [bytes(bytearray(
        b for i in range(32 * 32) for b in ((i * 7) % 256, (i * 7) % 256)))]
    got = TX._pick_depth("height", img8, plans_dup, (32, 32))
    assert got["bits"] == 8, got
    assert "rien de plus fin que 8 bits" in got["note16"], got["note16"]
    # une charge utile RÉELLE est gardée en 16 bits
    plans_vrai = [bytes(bytearray(
        b for i in range(32 * 32) for b in ((i * 7) % 256, (i * 13 + 3) % 256)))]
    got = TX._pick_depth("height", img8, plans_vrai, (32, 32))
    assert got["bits"] == 16 and got["sub"] > 0 and got["low_bits"] > 1.0, got


def test_l_atlas_carre_ecrit_deux_densites_et_la_plus_basse_decide():
    """LA MOITIÉ MESURABLE DU CAHIER DES CHARGES — « 300 DPI avec fond perdu ».

    DÉFAUT REPRODUIT SUR LES OCTETS : un atlas CARRÉ posé sur une carte qui ne
    l'est pas donne des pixels RECTANGULAIRES. 1024 x 1024 sur une carte de
    69 x 94 mm écrit pHYs = 14841 x 10894 px/m, soit 377 x 277 DPI. Le panneau
    n'annonçait que la largeur (« soit 377 DPI inscrits dans le chunk pHYs de
    chaque PNG ») et son avertissement « sous 300 DPI » ne se déclenchait pas
    — alors que la moitié verticale du livrable tombe à 277.

    Ici : les deux axes sont mesurés dans le fichier, `dpi_min` porte le
    verdict, et l'écran est tenu de dire les deux (vérifié sur sa source)."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True, bits16=True)
    g = CC.geom_of(CC.read_deck(did))
    mm_w = g.trim_mm[0] + 2 * g.bleed_mm
    mm_h = g.trim_mm[1] + 2 * g.bleed_mm
    assert (round(mm_w, 2), round(mm_h, 2)) == (69.0, 94.0), (mm_w, mm_h)
    for m in st["maps"]:
        raw = _fichier(did, m["kind"] + ".png").read_bytes()
        x, y, unit = struct.unpack(">IIB", _chunk_body(raw, b"pHYs")[:9])
        assert unit == 1
        assert (x, y) == (14841, 10894), (m["kind"], x, y)
        assert m["dpi"] == [377, 277], (m["kind"], m["dpi"])
        assert m["dpi"][1] < 300, "la reproduction du défaut a changé de forme"
    ph = st["phys"]
    assert ph["dpi_min"] == 277, ph
    # le manifeste porte le verdict, pas seulement les deux chiffres
    mf = _api("GET", f"/api/cards/{did}/texture/manifest").json()
    assert mf["sortie"]["dpi_min"] == 277
    assert mf["sortie"]["atteint_300_dpi"] is False
    # CE QUI REND LE DÉFAUT SI DISCRET : sans atlas carré, la même définition
    # tombe à 277 DPI sur LES DEUX axes — et là l'ancien avertissement, calculé
    # sur la seule largeur, se déclenchait bien. Cocher « carré » remontait la
    # largeur à 377 et éteignait l'alerte, sans rien changer à la hauteur.
    st1 = _derive(did, res=1024, square=False, bits16=True)
    assert st1["phys"]["dpi"] == [277, 277], st1["phys"]
    assert st1["phys"]["dpi_min"] == 277
    # …et 2k tient le plancher sur les deux axes
    st2 = _derive(did, res=2048, square=False, bits16=True)
    assert st2["phys"]["dpi_min"] >= 300, st2["phys"]
    assert mf["sortie"]["dpi"] == [377, 277]

    # LA PRÉDICTION DE L'ÉCRAN DOIT ÊTRE LE CHIFFRE DU FICHIER. `outDpi` part
    # des millimètres DÉCLARÉS (rogne + 2 x fond perdu), pas de la toile en
    # pixels redivisée par les DPI : cet arrondi-là décalait la prédiction d'un
    # DPI (554 annoncé, 553 écrit, sur une sortie 1504 x 2048). Le test rejoue
    # ici la formule de l'écran et la compare aux octets.
    def _js_dpi(dim):
        mm = (g.trim_mm[0] + 2 * g.bleed_mm, g.trim_mm[1] + 2 * g.bleed_mm)
        return [round(round(dim[i] * 1000 / mm[i]) * 0.0254) for i in (0, 1)]

    assert _js_dpi((1024, 1024)) == [377, 277]
    assert _js_dpi((752, 1024)) == st1["phys"]["dpi"]
    assert _js_dpi((1504, 2048)) == st2["phys"]["dpi"], (
        _js_dpi((1504, 2048)), st2["phys"]["dpi"])
    src = JS.read_text(encoding="utf-8")
    assert "g.trim_mm[0] + 2 * g.bleed_mm" in src, \
        "outDpi doit partir des millimètres déclarés, pas de la toile arrondie"

    # L'ÉCRAN : il n'a plus le droit d'afficher un seul chiffre pour deux axes.
    src = JS.read_text(encoding="utf-8")
    assert "function outDpi(" in src, "la densité de l'écran doit venir des mm"
    assert "function dpiTxt(" in src
    assert "Math.min(dpi[0], dpi[1])" in src, \
        "le seuil de 300 DPI doit se juger sur le plus petit des deux axes"
    assert "Math.round(g.dpi * dim[0] / g.canvas_px[0])" not in src, \
        "l'ancienne densité à un seul axe est revenue"


def test_les_douze_reglages_sont_ecrits_la_ou_le_lecteur_les_cherche():
    """COUPLAGE MORT EN SILENCE (spec §2.3), réparé DE CE CÔTÉ-CI.

    `doc.texture.pbr` appartient à cette pièce, donc sa FORME lui appartient.
    Le lecteur (P8) passe l'enveloppe entière à `pbr_service.normalize_derive`,
    qui cherche `normal_strength`, `ao_strength`… au PREMIER niveau ; ils
    étaient écrits sous `.derive`. `normalize_derive` ignore les clés inconnues
    sans un mot : le lecteur recevait les DÉFAUTS, toujours. Les douze curseurs
    étaient décoratifs pour le fichier exporté, alors que l'aperçu de cette
    pièce, lui, les respecte — l'écran et le fichier divergeaient.

    Le test REPRODUIT le défaut, puis prouve que le miroir à plat le corrige,
    et que l'écran écrit bien ce miroir."""
    regle = {"normal_strength": 4.0, "ao_strength": 4.0, "ao_radius": 32.0,
             "roughness_invert": True, "metallic_mode": "luminance",
             "emissive_threshold": 0.1}
    # 1. le défaut, tel qu'il était
    ancien = {"derive": dict(regle), "levels": {"metallic": 1.0},
              "res": 2048, "bits16": True, "square": False}
    assert PBR.normalize_derive(ancien) == dict(PBR.DERIVE_DEFAULTS), \
        "le défaut ne se reproduit plus : ce test ne prouve plus rien"
    # 2. la forme corrigée : les mêmes clés, aussi à plat
    neuf = dict(ancien)
    neuf.update(regle)
    got = PBR.normalize_derive(neuf)
    assert got != dict(PBR.DERIVE_DEFAULTS)
    for k, v in regle.items():
        assert got[k] == v, (k, got[k], v)
    # 3. l'écran écrit bien les deux niveaux, et `.derive` reste l'autorité
    src = JS.read_text(encoding="utf-8")
    assert re.search(r"function pbrOut\(pbr\)\s*\{\s*return Object\.assign\("
                     r"\{\}, pbr, pbr\.derive \|\| \{\}\);", src), \
        "le miroir à plat de doc.texture.pbr a disparu"
    assert "Object.assign(p, p.derive);" in src, \
        "un document d'une version antérieure laisserait un miroir périmé"
    for appel in ("function patchPbr", "function patchDerive", "function patchLevel"):
        i = src.index(appel)
        assert "pbrOut(" in src[i:i + 260], f"{appel} écrit sans le miroir"
    # 4. les douze clés de l'écran sont EXACTEMENT celles du service
    bloc = re.findall(r'\{\s*k:\s*"([a-z_]+)"', src)
    assert set(bloc) >= set(PBR.DERIVE_DEFAULTS), \
        set(PBR.DERIVE_DEFAULTS) - set(bloc)


def test_la_moyenne_d_une_map_16_bits_se_lit_sur_seize_bits():
    """Pillow décode un PNG RVB 16 bits directement en mode « RGB » en gardant
    l'OCTET FORT (v >> 8). La moyenne du canal R de normal.png sortait donc à
    127,54/255 alors que la vraie moyenne 16 bits vaut 127,33/255 : le panneau
    affichait « moy 0,500 » là où le fichier dit 0,499.

    Un demi-millième — mais c'est un chiffre affiché qui ne se retrouve pas
    dans les octets, et la règle de ce panneau ne souffre pas d'exception. Le
    test recalcule la moyenne À LA MAIN sur la charge utile 16 bits."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True, bits16=True)
    par = {m["kind"]: m for m in st["maps"]}
    assert par["normal"]["bits"] == 16, par["normal"]
    raw = _fichier(did, "normal.png").read_bytes()
    w, h, nch, pay = _payload16(raw)
    assert nch == 3
    # canal R, vraie valeur 16 bits ramenée sur 0-255 par division par 257
    somme = 0
    for i in range(0, w * h):
        o = i * 6
        somme += (pay[o] << 8) | pay[o + 1]
    vrai = somme / (w * h) / 257.0
    affiche = par["normal"]["mean"] * 255.0
    assert abs(affiche - vrai) < 0.05, (affiche, vrai)
    # …et l'octet fort seul donne un AUTRE chiffre : c'est bien celui-là qu'on
    # n'affiche plus.
    fort = sum(pay[i * 6] for i in range(w * h)) / (w * h)
    assert abs(fort - vrai) > 0.05, (fort, vrai)


def test_la_convention_de_mesure_voyage_avec_le_chiffre():
    """UN CHIFFRE JUSTE SANS SA DÉFINITION SE LIT COMME UN FAUX.

    « moy » et « ampl. » ne veulent pas dire la même chose d'une map à
    l'autre : luminance Rec.601 sur basecolor et emissive, canal R sur la
    normale, canal V sur l'ORM, canal unique sur les quatre scalaires. Les
    chiffres étaient JUSTES et la définition vivait ailleurs — un critique a dû
    la retrouver par rétro-ingénierie et a écrit qu'« un acheteur qui recalcule
    naïvement croira à un mensonge ».

    Le test le PROUVE en le faisant : il recalcule la moyenne de la base color
    sous la convention naïve (moyenne plate des trois canaux) et vérifie
    qu'elle ne tombe PAS sur le chiffre affiché — puis que la convention
    publiée, elle, y tombe. Et il exige que l'étiquette soit servie avec chaque
    map, portée par la planche et par le manifeste."""
    from PIL import ImageStat
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True, levels={"metallic": 0.0,
                                                     "roughness": 0.6})
    par = {m["kind"]: m for m in st["maps"]}

    # 1. chaque map porte SA convention, et elles ne sont pas toutes la meme
    for k, m in par.items():
        assert m.get("mesure_sur"), f"{k} n'annonce pas son canal de mesure"
        # 8 bits : « p95 − p5 ». 16 bits : la même chose PLUS l'échelle de
        # lecture, parce que la réduction en 8 bits change le nombre.
        assert m.get("span_def") == TX.span_def(m["bits"]), m.get("span_def")
    assert len({m["mesure_sur"] for m in par.values()}) >= 3, \
        "trois conventions au moins cohabitent : les taire est le defaut"
    assert "Rec.601" in par["basecolor"]["mesure_sur"]
    assert "canal R" in par["normal"]["mesure_sur"]
    assert "canal V" in par["orm"]["mesure_sur"]
    assert "16 bits" in par["normal"]["mesure_sur"], \
        "une moyenne 16 bits doit dire qu'elle est lue sur 16 bits"

    # 2. LA CONVENTION NAIVE NE TOMBE PAS SUR LE CHIFFRE : c'est tout l'enjeu
    img = Image.open(_fichier(did, "basecolor.png"))
    img.load()
    plat = sum(ImageStat.Stat(img.convert("RGB")).mean) / 3.0 / 255.0
    affiche = par["basecolor"]["mean"]
    assert abs(plat - affiche) > 0.005, \
        ("la moyenne plate coincide ici : le test ne prouve plus rien",
         plat, affiche)
    # 3. …et la convention PUBLIEE, si. Rec.601 arrondie, la formule exacte de
    #    Pillow — la tronquer biaise d'un demi-niveau.
    lum = ImageStat.Stat(img.convert("L")).mean[0] / 255.0
    assert abs(lum - affiche) < 0.0005, (lum, affiche)

    # 4. la planche et le manifeste la portent aussi
    r = _api("GET", f"/api/cards/{did}/texture/manifest")
    assert r.status_code == 200, r.text
    man = r.json()
    for m in man["maps"]:
        assert m["canal_mesure"], m["fichier"]
    assert "Rec.601" in man["conventions"]["moyenne"]
    assert "centile 95" in man["conventions"]["amplitude_p95_p5"]

    # 5. l'ecran colle l'etiquette au nombre, dans le MEME element
    src = JS.read_text(encoding="utf-8")
    i = src.index("moy <b>")
    assert "cf-tx-def" in src[i - 200:i + 400], \
        "l'etiquette de convention a quitte le voisinage du chiffre"
    assert "m.mesure_sur" in src and "m.span_def" in src


def test_l_orm_prouve_son_empaquetage_au_lieu_de_l_annoncer():
    """« R = AO, V = rugosité, B = métallique » était ÉCRIT, jamais MESURÉ.

    C'est un critique qui a dû rouvrir les quatre PNG pour constater l'écart
    maximum de 0 sur les trois canaux. Une convention annoncée et non mesurée
    est exactement ce que ce panneau s'interdit ailleurs. Le lot publie donc
    l'écart canal par canal — et le prix de sa propre redondance."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True, levels={"metallic": 0.3,
                                                     "roughness": 0.6})
    pack = st.get("orm_pack") or {}
    assert pack.get("ok") is True, pack
    assert pack["px"] == 1024 * 1024, pack
    assert pack["ecarts"] == {"ao": 0, "roughness": 0, "metallic": 0}, pack
    assert pack["octets"] == _fichier(did, "orm.png").stat().st_size

    # LE MEME CONTROLE, refait ici avec notre propre oracle : si le service
    # cessait d'empaqueter dans cet ordre, `orm_check` ET ce bloc tomberaient.
    orm = Image.open(_fichier(did, "orm.png"))
    orm.load()
    r, v, b = orm.convert("RGB").split()
    for canal, nom in ((r, "ao"), (v, "roughness"), (b, "metallic")):
        ref = _huit_bits(Image.open(_fichier(did, nom + ".png")), nom)
        assert ImageChops.difference(canal, ref).getextrema()[1] == 0, nom

    # et un ORM volontairement faux doit etre DENONCE, pas confirme
    faux = dict(zip(("ao", "roughness", "metallic", "orm"),
                    (Image.new("L", (8, 8), 10), Image.new("L", (8, 8), 20),
                     Image.new("L", (8, 8), 30),
                     Image.merge("RGB", (Image.new("L", (8, 8), 10),
                                         Image.new("L", (8, 8), 99),
                                         Image.new("L", (8, 8), 30))))))
    got = TX.orm_check(faux, 0)
    assert got["ok"] is False and got["ecarts"]["roughness"] == 79, got

    assert man_a_le_champ(did, "orm_empaquetage")


def man_a_le_champ(did: str, champ: str) -> bool:
    r = _api("GET", f"/api/cards/{did}/texture/manifest")
    assert r.status_code == 200, r.text
    return champ in r.json()


def test_un_reglage_qui_n_allume_rien_le_dit_avant_l_export():
    """« Un réglage qui ne produit rien devrait le dire AVANT l'export, pas
    après. » Le seuil d'émission par défaut vaut 0,85 ; sur une carte dont la
    luminance plafonne plus bas, `pbr_service._emissive` masque TOUT et la map
    sort noire. Le panneau annonçait « éteinte » sans jamais dire que le seuil
    était hors de portée de l'image, ni de combien.

    Le test fabrique exactement ce cas, puis vérifie que la phrase rendue est
    une comparaison entre un réglage et une MESURE — et qu'elle disparaît quand
    le seuil redevient atteignable."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True,
                 derive={"emissive_threshold": 1.0})
    par = {m["kind"]: m for m in st["maps"]}
    lum = st.get("source_lum") or {}
    assert 0.0 < lum.get("max", 0) <= 1.0, lum
    assert par["emissive"]["informative"] is False
    h = par["emissive"]["hint"]
    assert h and "1,00" in h and f"{lum['max']:.2f}".replace(".", ",") in h, h
    assert "descendre le seuil" in h.lower(), h
    # LA PREMIERE CLAUSE SE SUFFIT : la planche coupe a 300 px, une phrase qui
    # commence par sa mise en contexte y arrive tronquee avant d'avoir rien dit.
    tete = h.split(".")[0]
    assert "1,00" in tete and f"{lum['max']:.2f}".replace(".", ",") in tete, tete
    assert len(tete) <= 60, (len(tete), tete)

    # la mesure est celle de l'image REELLEMENT derivee : aucun pixel au-dessus
    src = Image.open(_fichier(did, "source.png"))
    src.load()
    assert max(i for i, c in enumerate(src.convert("L").histogram())
               if c) / 255.0 <= lum["max"] + 0.01

    # seuil atteignable -> la map s'allume et la phrase disparait
    st2 = _derive(did, res=1024, square=True,
                  derive={"emissive_threshold": 0.05})
    e2 = {m["kind"]: m for m in st2["maps"]}["emissive"]
    assert e2["informative"] is True, e2
    assert not e2["hint"], e2["hint"]

    # meme geste pour un NIVEAU CUIT pousse a l'extreme : `level_lut` y perd
    # toute amplitude et la map sort constante. C'est le niveau, pas la matiere.
    st3 = _derive(did, res=1024, square=True,
                  levels={"metallic": 0.0, "roughness": 1.0})
    r3 = {m["kind"]: m for m in st3["maps"]}["roughness"]
    assert r3["informative"] is False and r3["span"] == 0
    assert "niveau de rugosité cuit à 1,00" in r3["hint"], r3["hint"]


def test_la_planche_porte_les_memes_chunks_que_les_maps():
    """INCOHÉRENCE INTERNE RELEVÉE, ET VRAIE : les huit maps portaient
    gAMA/sRGB/pHYs/tEXt et la planche — la seule pièce du lot qu'on montre à
    un tiers — n'en portait AUCUN. « La planche de contrôle est la seule pièce
    du lot qui ne prouve aucune densité. »"""
    did = _deck()
    _envoie_source(did, 815, 1110)
    _derive(did, res=1024, square=True)
    r = _api("GET", f"/api/cards/{did}/texture/sheet")
    assert r.status_code == 200, r.text
    raw = r.content
    tags = _chunks(raw)
    for t in ("gAMA", "sRGB", "pHYs", "tEXt"):
        assert t in tags, (t, tags[:8])
    assert tags.index("pHYs") < tags.index("IDAT"), tags[:8]
    x, y, unit = struct.unpack(">IIB", _chunk_body(raw, b"pHYs")[:9])
    assert unit == 1 and x == y == TX.SHEET_PPM, (x, y, unit)
    assert round(x * 0.0254) == 300, x
    # la note dit la taille imprimee, et elle tombe juste a la regle
    w, h = struct.unpack(">II", raw[16:24])
    note = _chunk_body(raw, b"tEXt").decode("latin-1", "replace")
    if "planche" not in note:                    # un seul tEXt : Comment
        note = raw.decode("latin-1", "replace")
    mm = re.search(r"(\d+\.?\d*)x(\d+\.?\d*) mm imprimee", note)
    assert mm, note[:200]
    assert abs(float(mm.group(1)) - w * 25.4 / 300) < 0.1
    assert abs(float(mm.group(2)) - h * 25.4 / 300) < 0.1


def test_l_espace_affiche_est_celui_que_les_octets_declarent():
    """« Le manifeste dit linéaire, mais le fichier ne le déclare pas
    formellement. » Le fichier LE déclare — `gAMA` 100000 est la façon dont
    PNG écrit gamma 1.0, donc linéaire — mais l'écran affichait un mot pris
    dans une table du code, pas le chunk trouvé dans le fichier. Ce sont deux
    affirmations différentes et une seule est une mesure. Le test coupe le
    lien : il vérifie que la mention vient bien des octets."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True)
    for m in st["maps"]:
        raw = _fichier(did, m["kind"] + ".png").read_bytes()
        tags = _chunks(raw)
        gama = struct.unpack(">I", _chunk_body(raw, b"gAMA"))[0]
        if m["kind"] in ("basecolor", "emissive"):
            assert "sRGB" in tags and gama == 45455, (m["kind"], tags, gama)
            assert m["space_decl"].startswith("sRGB") and "0,45455" in m["space_decl"]
        else:
            assert "sRGB" not in tags and gama == 100000, (m["kind"], tags, gama)
            assert m["space_decl"] == "linéaire (gAMA 1,0)", m["space_decl"]
    # un PNG SANS chunk d'espace ne doit pas se voir attribuer un espace
    nu = io.BytesIO()
    Image.new("L", (4, 4), 128).save(nu, format="PNG")
    assert TX.space_decl(nu.getvalue()) == "non déclaré dans les octets"
    assert TX.space_decl(b"") == "non déclaré"


def test_le_prix_du_lot_est_publie_et_ne_se_devine_pas():
    """« 22 secondes de calcul et une normale de 45 Mo, sans le moindre
    avertissement de poids ou de durée avant le clic. » On ne peut pas mesurer
    ce qu'un calcul n'a pas encore fait ; on publie donc ce que le DERNIER lot
    a coûté, et l'écran pose la règle de trois sur des comptes de pixels
    exacts — en la nommant règle de trois."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True)
    total = sum((TX.tex_dir(did) / (k + ".png")).stat().st_size for k in KINDS)
    assert st["bytes_total"] == total, (st["bytes_total"], total)
    assert abs(st["out_mpx"] - 1024 * 1024 / 1e6) < 1e-3, st["out_mpx"]
    assert st["ms"] > 0
    src = JS.read_text(encoding="utf-8")
    i = src.index("Coût : le dernier lot a pesé")
    bloc = src[i:i + 900]
    assert "REPORT.bytes_total" in src[i - 700:i]
    assert ("règle de trois" in bloc
            and "coût par pixel constant" in bloc), \
        "une extrapolation doit se presenter comme telle"


def test_l_amplitude_d_une_map_16_bits_se_lit_sur_seize_bits():
    """DEUX RÉDUCTIONS 16 -> 8 COHABITAIENT, ET ELLES NE DISENT PAS PAREIL.

    L'amplitude (p95 − p5) d'une map 16 bits était mesurée sur une VUE 8 BITS
    de la map — et pas la même selon la map : Pillow rend un RVB 16 bits en
    gardant l'OCTET FORT (troncature) tandis que `_as_mode` ramène un gris
    16 bits par `v / 257 + 0,5` (arrondi). Mesuré sur une hauteur 1504 x 2048 :
    octet fort => 244, vue arrondie => 243 (le chiffre affiché), seize bits
    => 243,30. Un acheteur qui recalcule prend la tranche évidente, trouve 244
    en face d'un 243 affiché, et conclut au mensonge.

    Une map annoncée « lue sur 16 bits » voit maintenant SON AMPLITUDE lue sur
    seize bits : centiles sur les 65 536 classes réelles, ÷ 257. Le test le
    refait à la main, à partir des octets défiltrés, et vérifie AUSSI que la
    lecture naïve (octet fort) donne un autre nombre — sans quoi il ne
    prouverait rien."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True, bits16=True)
    par = {m["kind"]: m for m in st["maps"]}
    assert par["height"]["bits"] == 16, par["height"]

    raw = _fichier(did, "height.png").read_bytes()
    w, h, nch, pay = _payload16(raw)
    assert nch == 1
    n = w * h

    def centile16(f: float) -> int:
        hst = [0] * 65536
        for i in range(n):
            hst[(pay[2 * i] << 8) | pay[2 * i + 1]] += 1
        acc = 0
        for v, c in enumerate(hst):
            acc += c
            if acc >= f * n:
                return v
        return 65535
    vrai = (centile16(0.95) - centile16(0.05)) / 257.0
    assert abs(par["height"]["span"] - vrai) <= 0.011, \
        (par["height"]["span"], vrai)

    # LA PREUVE QUE LES TROIS LECTURES DIFFÈRENT, sur une rampe où les trois
    # sont calculables de tête : v(i) = round(i x 65535 / (N-1)). La vraie
    # amplitude vaut 0,90 x 65535 / 257 = 229,5 — un nombre qu'AUCUNE lecture
    # 8 bits ne peut écrire, puisqu'elles rendent des entiers.
    N = 20000
    octets = bytearray(N * 2)
    for i in range(N):
        v = round(i * 65535 / (N - 1))
        octets[2 * i] = v >> 8
        octets[2 * i + 1] = v & 255
    rampe = TX._png16([bytes(octets)], (N, 1))
    exact = TX._span16(rampe)
    assert abs(exact - 0.90 * 65535 / 257.0) < 1.0, exact
    assert abs(exact - round(exact)) > 0.2, \
        ("l'amplitude 16 bits tombe sur un entier ici : la rampe ne prouve "
         "plus rien", exact)
    # les deux réductions 8 bits des MÊMES octets, à la main
    fort = Image.frombytes("L", (N, 1), bytes(octets[0::2]))
    rond = Image.frombytes(
        "L", (N, 1),
        bytes(min(255, round(((octets[2 * i] << 8) | octets[2 * i + 1]) / 257.0))
              for i in range(N)))

    def cent8(img, f: float) -> int:
        hf = img.histogram()
        acc = 0
        for v, c in enumerate(hf):
            acc += c
            if acc >= f * N:
                return v
        return 255
    a_fort = cent8(fort, 0.95) - cent8(fort, 0.05)
    a_rond = cent8(rond, 0.95) - cent8(rond, 0.05)
    assert float(a_fort).is_integer() and float(a_rond).is_integer()
    assert max(abs(a_fort - exact), abs(a_rond - exact)) > 0.2, \
        (a_fort, a_rond, exact)

    # …et l'écart est ANNONCÉ : l'étiquette dit sur quoi le nombre est lu.
    assert "65 536" in par["height"]["span_def"], par["height"]["span_def"]
    assert "0-255" in par["height"]["span_def"], par["height"]["span_def"]
    assert par["basecolor"]["span_def"] == "p95 − p5", \
        "une map 8 bits garde sa definition simple"
    r = _api("GET", f"/api/cards/{did}/texture/manifest")
    assert r.status_code == 200, r.text
    man = r.json()
    for m in man["maps"]:
        assert m["amplitude_mesure"], m["fichier"]
    assert "16 bits" in man["conventions"]["amplitude_16_bits"]
    # l'écran sait afficher un décimal : « ampl. 243/255 » pour 243,30 serait
    # un troisième chiffre encore.
    src = JS.read_text(encoding="utf-8")
    cellule = src[src.index("function mapCell("):src.index("function title(")]
    assert "ampl. ' + amp" in cellule
    assert "Number.isInteger(m.span)" in cellule, \
        "l'ecran arrondirait l'amplitude 16 bits a l'entier"
    assert "65 536 classes" in src, \
        "la note groupee doit dire sur quoi l'amplitude 16 bits est lue"


def test_le_defaut_de_la_route_n_ecrit_pas_une_map_morte():
    """DEUX TABLES POUR UN MÊME RÉGLAGE, ET C'EST CELLE QU'ON NE REGARDE PAS
    QUI ÉCRIVAIT LE LIVRABLE.

    Le niveau de rugosité par défaut de la ROUTE valait 1,00 — l'extrémité de
    la course, où la cuisson ne peut plus recentrer le motif sans écrêter.
    Mesuré : un POST /derive sans `levels` rendait roughness.png CONSTANTE
    (moyenne 1,000, amplitude 0, « neutre »), et l'ORM avec, puisque son canal
    V est cette map. L'écran, lui, envoie 0,92 (le vélin, sa matière par
    défaut) et ne voyait donc jamais le trou."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    r = _api("POST", f"/api/cards/{did}/texture/derive",
             json={"res": 1024, "square": True})
    assert r.status_code == 200, r.text
    st = r.json()["texture"]
    par = {m["kind"]: m for m in st["maps"]}
    assert st["levels"]["roughness"] == TX.DEFAULT_ROUGHNESS
    assert par["roughness"]["span"] > PBR.FLAT_SPAN, \
        ("le defaut de la route ecrit encore une map constante",
         par["roughness"])
    assert par["roughness"]["informative"], par["roughness"]
    assert par["orm"]["informative"], par["orm"]
    # et le défaut de la route est bien celui de l'écran, pas un deuxième.
    src = JS.read_text(encoding="utf-8")
    i = src.index("levels: { metallic:")
    assert f"roughness: {TX.DEFAULT_ROUGHNESS}" in src[i:i + 120], \
        (src[i:i + 120], TX.DEFAULT_ROUGHNESS)


def test_la_table_lumineuse_eclaire_le_fichier_livre_et_pas_une_copie():
    """« Il fabrique les meilleures maps et il est incapable de les montrer. »

    Trois choses se vérifient ici, et toutes sur les octets ou sur la source :

    1. `/thumb/<kind>?px=N` rend le FICHIER ÉCRIT rééchantillonné — pas la
       vignette de 320 px figée à la dérivation. Ce qui est éclairé est donc
       ce qui est téléchargé, et le rapport d'aspect est conservé.
    2. `N` est borné : une demande de 9 999 px ne fait pas rendre 45 Mo.
    3. L'écran charge bien CINQ maps (le métal en fait partie : sans lui il
       n'y a pas de réponse métallique à rendre) et le modèle est un vrai
       modèle de microfacettes — GGX, Smith, Fresnel de Schlick, espace
       linéaire — au lieu du Lambert + Blinn-Phong que la critique a relevé."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=False)
    par = {m["kind"]: m for m in st["maps"]}

    r = _api("GET", f"/api/cards/{did}/texture/thumb/basecolor", params={"px": 256})
    assert r.status_code == 200, r.text
    im = Image.open(io.BytesIO(r.content))
    assert max(im.size) == 256, im.size
    ref = par["basecolor"]
    assert abs(im.size[0] / im.size[1] - ref["w"] / ref["h"]) < 0.01, \
        (im.size, ref["w"], ref["h"])

    r = _api("GET", f"/api/cards/{did}/texture/thumb/normal", params={"px": 9999})
    assert r.status_code == 200, r.text
    gros = Image.open(io.BytesIO(r.content))
    assert max(gros.size) <= TX.LIT_MAX_PX, gros.size

    # sans px, la vignette figée : les deux voies restent servies
    r = _api("GET", f"/api/cards/{did}/texture/thumb/ao")
    assert r.status_code == 200
    assert max(Image.open(io.BytesIO(r.content)).size) == TX.THUMB_PX

    src = JS.read_text(encoding="utf-8")
    i = src.index('const need = ["basecolor"')
    bloc = src[i:i + 400]
    assert '"metallic"' in bloc, "le metal n'est pas chargé : rien à rendre"
    assert "?px=" in bloc, "l'apercu lit encore la vignette figee"
    # le panneau AFFICHÉ ne doit plus annoncer le modèle qu'il n'utilise plus
    # (le commentaire de code, lui, a le droit de nommer le défaut corrigé).
    a = src.index("function sectionLight")
    ecran = src[a:src.index("/* ── A. la matiere du support", a)]
    assert "Lambert + Blinn-Phong" not in ecran, \
        "l'ecran annonce encore le modele qu'il n'utilise plus"
    assert "Microfacettes GGX" in ecran, "l'ecran ne nomme pas son modele"
    for terme in ("Trowbridge-Reitz", "Smith", "Schlick", "espace linéaire",
                  "F0 = mélange(0,04 ; albédo ; métal)"):
        assert terme in src, terme
    # ce qui MANQUE est écrit à la même place que ce qui est fait
    j = src.index("Sans ombres portées")
    assert "réfraction" in src[j:j + 260], src[j:j + 260]


# ═══════════════════════ LE RACCORD DE TUILE ════════════════════════════════
#
# Deux défauts d'un coup, et le second est du même genre que le faux « 16
# bits » : une mesure qui portait un nom juste et répondait à une autre
# question. Détail dans `texture.seam_report`.

def _tuile_tissee(S: int = 128, pas: int = 8) -> Image.Image:
    """Une matière STRUCTURÉE qui se referme PARFAITEMENT : des bandes dures
    dont la période divise la tuile. Aucune couture n'est possible — et
    pourtant l'ancienne mesure la condamnait, parce que le raccord tombe sur un
    bord de bande alors que la marche MÉDIANE est prise au milieu d'une bande,
    là où il ne se passe rien."""
    im = Image.new("RGB", (S, S))
    px = im.load()
    for y in range(S):
        for x in range(S):
            v = 230 if ((x // pas) + (y // pas)) % 2 else 40
            px[x, y] = (v, v, v)
    return im


def _tuile_tissee_grenue(S: int = 128, pas: int = 8) -> Image.Image:
    """La même matière structurée, PLUS UN GRAIN FIN PÉRIODIQUE — c'est-à-dire
    une vraie toile, et pas un damier d'aplats.

    POURQUOI CE SECOND MOTIF EXISTE. `_tuile_tissee` est faite d'aplats : plus
    d'une colonne sur deux y est identique à sa voisine, donc sa marche
    interne MÉDIANE vaut exactement 0. Tant que le rapport à la médiane était
    calculé avec un plancher de 1e-6, cette tuile publiait « 190 000 000,00x »
    et le test s'en contentait. Le grain (période 4, qui divise la tuile, donc
    sans effet sur la jonction) donne une médiane non nulle : le rapport à la
    médiane redevient un nombre qu'on peut refaire à la main."""
    im = Image.new("RGB", (S, S))
    px = im.load()
    for y in range(S):
        for x in range(S):
            v = 200 if ((x // pas) + (y // pas)) % 2 else 40
            v += (x % 4) * 3 + (y % 4) * 5
            px[x, y] = (v, v, v)
    return im


def _tuile_en_rampe(S: int = 128) -> Image.Image:
    """Une VRAIE couture : une rampe qui ne boucle pas. Le dernier pixel vaut
    255, le premier 0 — la marche au raccord est cent fois la marche interne."""
    im = Image.new("RGB", (S, S))
    px = im.load()
    for y in range(S):
        for x in range(S):
            v = round(255 * x / (S - 1))
            px[x, y] = (v, v, v)
    return im


def _seam_oracle(im: Image.Image) -> dict:
    """L'oracle, écrit ICI : luminance flottante, toutes les paires voisines,
    marche au raccord contre la PIRE marche interne. Rien n'est emprunté au
    code testé."""
    rgb = im.convert("RGB")
    S = rgb.size[0]
    b = rgb.tobytes()                    # RVB entrelacé, lu ici, sans Pillow
    L = [0.299 * b[3 * i] + 0.587 * b[3 * i + 1] + 0.114 * b[3 * i + 2]
         for i in range(S * S)]

    def col(a, b):
        return sum(abs(L[y * S + a] - L[y * S + b]) for y in range(S)) / S

    def row(a, b):
        return sum(abs(L[a * S + x] - L[b * S + x]) for x in range(S)) / S

    ix = [col(k - 1, k) for k in range(1, S)]
    iy = [row(k - 1, k) for k in range(1, S)]
    ex, ey = col(S - 1, 0), row(S - 1, 0)
    med = lambda a: sorted(a)[len(a) // 2]                       # noqa: E731
    mdx, mdy = med(ix), med(iy)
    return {"exces": max(ex / max(ix), ey / max(iy)),
            # une médiane nulle ne se plancher PAS : le rapport n'existe pas
            "ratio_median": (max(ex / mdx, ey / mdy)
                             if (mdx > 0 and mdy > 0) else None),
            "mdx": mdx, "mdy": mdy,
            "ex": ex, "ey": ey, "mx": max(ix), "my": max(iy)}


def test_la_marche_au_raccord_se_compare_a_la_pire_marche_interne():
    """LA MESURE ÉTAIT FAUSSE, et elle condamnait des tuiles parfaites.

    Une tuile tissée dont la période divise exactement la toile n'a AUCUNE
    couture — c'est de l'arithmétique. L'ancienne mesure (marche au raccord ÷
    marche MÉDIANE) la notait pourtant très au-dessus de son propre seuil de
    2,0x, parce que le raccord tombe sur un bord de bande quand la médiane est
    prise au milieu d'une bande. La nouvelle (÷ PIRE marche interne) rend
    1,00 : le raccord ne fait rien de pire que ce que la matière fait déjà.
    Et sur une vraie couture — une rampe qui ne boucle pas — elle explose."""
    tissee = _tuile_tissee()
    r = TX.seam_report(tissee)
    o = _seam_oracle(tissee)
    assert abs(r["exces_brut"] - o["exces"]) < 1e-4, (r["exces_brut"], o["exces"])
    assert r["exces"] <= 1.0 + 1e-9, r
    assert r["grade"] == "invisible", r
    # LE VERDICT SE PREND SUR LE NOMBRE PUBLIÉ, à la précision où il est
    # publié : sinon une tuile affichée « 1,00x » serait comptée en échec pour
    # 1,0019, et le badge contredirait le total sur le même octet.
    assert r["exces"] == round(r["exces_brut"], 2), r
    assert TX.seam_grade(round(1.0019, 2)) == "invisible"
    # LE DÉFAUT REPRODUIT : l'ancienne mesure condamnait cette tuile parfaite.
    # Elle se mesure sur la version GRENUE — le damier d'aplats n'a pas de
    # marche médiane du tout, et un rapport calculé dessus ne veut rien dire
    # (voir test_un_rapport_a_une_mediane_nulle_n_est_pas_un_nombre).
    grenue = TX.seam_report(_tuile_tissee_grenue())
    og = _seam_oracle(_tuile_tissee_grenue())
    assert grenue["exces"] <= 1.0 + 1e-9, grenue
    assert grenue["ratio_median"] > 2.0, \
        "sans le défaut d'origine, le test ne démontre rien"
    # tolérance 1e-4 : le service PUBLIE le rapport arrondi à quatre décimales
    # (`rnd`), l'oracle le calcule en flottant plein
    assert abs(grenue["ratio_median"] - og["ratio_median"]) < 1e-4, \
        (grenue["ratio_median"], og["ratio_median"])

    rampe = TX.seam_report(_tuile_en_rampe())
    assert rampe["exces"] > 50, rampe
    assert rampe["grade"] == "casse", rampe
    # une vraie couture est HORIZONTALE ici : l'axe fautif est nommé
    assert rampe["x"]["exces"] > 50 and rampe["y"]["exces"] < 1.0, rampe
    assert rampe["paires_testees"] == 2 * (128 - 1), rampe


def test_la_tuile_sort_et_le_backend_la_remesure_sur_les_octets():
    """« Aucun export : tous les chiffres affichés restent invérifiables sur
    des octets. » C'était vrai des trente rapports de raccord : ils naissaient
    et mouraient dans le navigateur.

    La tuile part maintenant vers le backend, qui la DÉCODE, la re-mesure sur
    les pixels reçus et réécrit le fichier avec sa mesure dans ses chunks
    `tEXt` — plus un `pHYs`, parce qu'un PNG sans densité entre à 72 DPI. Le
    test vérifie l'aller-retour complet et relit les chunks."""
    did = _deck()
    buf = io.BytesIO()
    _tuile_tissee(128, 8).save(buf, format="PNG")
    r = _api("POST", f"/api/cards/{did}/texture/tile",
             params={"mat": "toile", "seed": 7},
             content=buf.getvalue(), headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    t = r.json()["tile"]
    o = _seam_oracle(_tuile_tissee(128, 8))
    assert abs(t["seam"]["exces_brut"] - o["exces"]) < 1e-3, (t["seam"], o)
    assert t["w"] == 128 and t["h"] == 128, t
    assert t["mat"] == "toile" and t["seed"] == 7, t

    r = _api("GET", f"/api/cards/{did}/texture/tile")
    assert r.status_code == 200, r.text
    raw = r.content
    assert t["bytes"] == len(raw), (t["bytes"], len(raw))
    import hashlib
    assert t["sha256"] == hashlib.sha256(raw).hexdigest()
    tags = _chunks(raw)
    assert tags == t["chunks"], (tags, t["chunks"])
    for tag in ("pHYs", "gAMA", "sRGB", "tEXt"):
        assert tag in tags, (tag, tags)
    # LA MESURE EST DANS LE FICHIER, pas seulement dans la réponse HTTP.
    textes = b""
    i = 8
    while i + 8 <= len(raw):
        ln = int.from_bytes(raw[i:i + 4], "big")
        if raw[i + 4:i + 8] == b"tEXt":
            textes += raw[i + 8:i + 8 + ln] + b"\n"
        if raw[i + 4:i + 8] == b"IEND":
            break
        i += 12 + ln
    assert b"Seam-Exces" in textes, textes[:400]
    assert f"{t['seam']['exces_brut']:.4f}".encode() in textes, textes[:400]
    assert b"Seam-H" in textes and b"Seam-V" in textes
    # densité inscrite = celle du document, relue sur les octets
    ppm = TX.png_phys(raw)
    assert ppm and ppm[0] == ppm[1], ppm
    assert t["dpi"][0] == round(ppm[0] * 0.0254), (t["dpi"], ppm)

    # une tuile qui n'est pas carrée n'est pas une tuile : 400, jamais 500
    b2 = io.BytesIO()
    Image.new("RGB", (64, 32), (10, 10, 10)).save(b2, format="PNG")
    r = _api("POST", f"/api/cards/{did}/texture/tile", content=b2.getvalue(),
             headers={"Content-Type": "image/png"})
    assert r.status_code == 400, r.status_code
    r = _api("POST", f"/api/cards/{did}/texture/tile", content=b"pas un png",
             headers={"Content-Type": "image/png"})
    assert r.status_code == 400, r.status_code
    r = _api("GET", f"/api/cards/{_deck()}/texture/tile")
    assert r.status_code == 404, r.status_code


def test_les_recettes_periodiques_ne_peuvent_plus_casser_leur_raccord():
    """LES DEUX VRAIES COUTURES, corrigées à la racine.

    `marble` pose `sin(2 pi veins (x + y) / S)` : la valeur ne se retrouve en
    x + S que si `veins` est ENTIER. « Marbre noir » était réglé à 4,5 — une
    DEMI-période de décalage d'un bord à l'autre, le pire cas possible, mesuré
    à 9,92x la pire marche interne.

    `twill` a besoin de deux choses à la fois : un nombre de blocs entier ET
    PAIR (le damier `bx + by` change de parité à chaque bloc) et un pas dont
    `S / T` soit pair (d'un bord à l'autre `dia` gagne S). « Fibre de carbone »
    donnait 512 / 18 = 28,44 blocs : ni l'un ni l'autre, mesuré à 1,68x.

    Le test vérifie les DEUX conditions arithmétiquement, sur le catalogue tel
    qu'il est écrit, et que la recette se protège d'un futur réglage fautif."""
    src = JS.read_text(encoding="utf-8")
    bloc = src[src.index("CF-TEXTURE-CATALOG-BEGIN"):src.index("CF-TEXTURE-CATALOG-END")]

    # 1. aucune veine fractionnaire ne subsiste dans le catalogue
    for v in re.findall(r"veins:\s*([0-9.]+)", bloc):
        assert float(v) == int(float(v)), f"veins={v} ne divise pas la tuile"

    # 2. la recette arrondit, même si quelqu'un réécrit le catalogue
    marbre = src[src.index("marble(S, m, seed)"):]
    marbre = marbre[:marbre.index("concrete(S, m, seed)")]
    assert "Math.round" in marbre.split("\n")[1], marbre.split("\n")[1]

    # 3. le sergé : nombre de blocs PAIR, pas déduit de lui, et les deux
    #    conditions vérifiées sur les valeurs réelles du catalogue
    twill = src[src.index("twill(S, m, seed)"):]
    twill = twill[:twill.index("speckle(S, m, seed)")]
    assert "2 * Math.round(S / (4 * T0))" in twill, twill[:400]
    S = 512
    for t0 in [int(x) for x in re.findall(r'gen: "twill".*?thread: (\d+)', bloc)]:
        blocs = max(2, 2 * round(S / (4 * t0)))
        T = S / (2 * blocs)
        assert blocs % 2 == 0, (t0, blocs)
        assert abs(S / T - round(S / T)) < 1e-9 and round(S / T) % 2 == 0, (t0, T)
    assert twill.count("thread") >= 1


def test_la_vignette_qu_on_clique_porte_son_raccord():
    """« Les matières qui échouent restent dans la grille au même rang que les
    autres ; la vignette elle-même ne porte aucun avertissement. »

    Le rapport en bas de page ne suffit pas : on choisit dans la grille. La
    mesure voyage désormais dans l'infobulle de chaque tuile, et une pastille
    apparaît dès que le raccord fait pire que la matière. Le calcul, lui, n'est
    PAS lancé au dessin de la grille — trente tuiles 512 px à chaque frappe
    dans le champ de recherche — mais lu dans le cache que remplit le bouton."""
    src = JS.read_text(encoding="utf-8")
    cell = src[src.index("function matCell("):src.index("function pickMat(")]
    assert "seamPeek(" in cell, "la vignette ne lit pas la mesure"
    assert "seamOf(" not in cell, \
        "la grille recalculerait trente tuiles 512 px a chaque rendu"
    assert "cf-tx-matseam" in cell, "aucune pastille d'avertissement"
    assert "cf-tx-matseam" in CSS.read_text(encoding="utf-8")
    all_ = src[src.index("async function seamAll("):src.index("async function tileOut(")]
    assert "fillGrid(" in all_, "le bouton ne redessine pas la grille mesurée"
    # le verdict ne se prend plus sur l'ancien seuil de 2,0x
    assert "r.exces" in all_ and "<= 2" not in all_, all_[:300]


def test_la_portee_des_niveaux_cuits_est_ecrite_et_reste_vraie():
    """DEUX RÉGLAGES DU MÊME NOM, DEUX PROPRIÉTAIRES.

    Le panneau écrivait « c'est ce que le moteur verra » sous les deux niveaux
    cuits. Vrai d'un moteur qui charge les fichiers de CET écran ; faux du ZIP
    de l'écran Export 3D, qui recuit les siens depuis SA finition. Le taire,
    c'est le couplage mort qu'on vient de réparer, à l'envers.

    Le test lit le voisin comme du TEXTE — pas d'import, donc pas de couplage
    — et rougira le jour où il se mettrait à relire `texture.pbr.levels` :
    ce jour-là, notre phrase deviendrait fausse."""
    src = JS.read_text(encoding="utf-8")
    i = src.index("Niveau de rugosité (cuit)")
    bloc = src[i:i + 1400]
    assert "Export 3D" in bloc and "finition" in bloc, bloc[:600]
    assert "ne relit pas ces deux nombres" in bloc, bloc[:600]

    voisin = (REPO / "backend" / "app" / "services" / "cards" / "gltf.py")
    txt = voisin.read_text(encoding="utf-8")
    j = txt.index("def build_maps(")
    corps = txt[j:j + 700]
    assert "props_of(opt[\"finish\"])" in corps, corps
    assert "texture" not in corps, \
        "l'export 3D lit desormais texture.pbr : notre phrase est perimee"

    # l'homonyme 16 bits est nommé là où il piège, dans le libellé de la case.
    # « RÉELS » EN EST PARTI : la case est une demande, pas un résultat, et le
    # résultat se mesure map par map sous chaque vignette.
    k = src.index("16 bits (hauteur + normale)")
    assert "maps de cet écran" in src[k:k + 120], src[k:k + 160]
    assert "16 bits réels" not in src, "la case promet de nouveau un résultat"


def test_livrer_l_orm_a_la_place_des_trois_se_pese_au_lieu_de_se_supposer():
    """« L'ORM ajoute de la redondance pure, SANS OPTION POUR LE LIVRER À LA
    PLACE des trois séparées. » Le coût de la redondance était déjà publié ;
    la seconde moitié du reproche, elle, SUPPOSE que l'échange ferait maigrir
    le lot. On ne suppose plus : on pèse les deux paquets sur les fichiers.

    ET LE SIGNE DÉPEND DU CONTENU — ce test l'a prouvé en tombant sur sa
    première version, qui affirmait « l'ORM est le plus lourd ». Sur le lot
    2048² réel il l'est (2 234 741 contre 1 963 602, +13,8 %) ; sur la carte
    de synthèse d'ici, pauvre en détail, il est plus léger de 761 octets. La
    seule affirmation qui tienne est donc : l'échange ne fait pas maigrir le
    lot de façon fiable, et le panneau LIT le signe au lieu de l'annoncer."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True,
                 levels={"metallic": 0.0, "roughness": 0.6})
    pack = st.get("orm_pack") or {}
    trois = sum(_fichier(did, k + ".png").stat().st_size
                for k in ("ao", "roughness", "metallic"))
    assert pack.get("octets_trois") == trois, (pack, trois)
    assert pack["octets"] == _fichier(did, "orm.png").stat().st_size
    # LE FAIT QUI TRANCHE LE REPROCHE : les deux paquets pèsent le même ordre
    # de grandeur, donc « livrer l'ORM à la place » n'est pas une économie —
    # ni dans un sens ni dans l'autre. Le seuil est large exprès : c'est la
    # PRÉSENCE d'une économie franche qui est niée, pas le signe.
    assert pack["octets"] > 0 and trois > 0
    ecart = abs(pack["octets"] - trois) / float(max(pack["octets"], trois))
    assert ecart < 0.5, (pack["octets"], trois, ecart)

    # et l'ecran affiche LES DEUX poids, pas seulement celui qui l'arrange
    src = JS.read_text(encoding="utf-8")
    i = src.index("livrer l'ORM <b>à la place</b>")
    bloc = src[i - 700:i + 900]
    assert "p.octets_trois" in bloc and "mo2(p.octets, p.octets_trois)" in bloc, \
        bloc[:400]
    # LES DEUX POIDS DANS LA MÊME UNITÉ : « 1,0 Mo contre 884 Ko » oblige le
    # lecteur à convertir de tête pour voir lequel gagne.
    assert "const mo2 = (a, b)" in src, "les deux poids ne partagent pas leur unite"
    assert "grossirait" in bloc and "maigrirait" in bloc, \
        "la phrase doit suivre le signe de l'ecart, pas le supposer"
    assert "mesuré sur les fichiers écrits" in bloc, bloc[-400:]

    # le manifeste porte la meme mesure : un tiers refait la soustraction
    r = _api("GET", f"/api/cards/{did}/texture/manifest")
    assert r.status_code == 200
    assert r.json()["orm_empaquetage"]["octets_trois"] == trois


def test_le_budget_du_jeu_est_multiplie_par_les_cartes_du_jeu():
    """« Aucun budget de poids, aucune alerte, aucune estimation POUR UN DECK.
    À 60 cartes on dépasse le gigaoctet sans que rien ne prévienne. »

    Les trois entrées du calcul doivent être des mesures ou des comptes
    exacts — jamais une constante écrite dans le code : le poids et la durée
    du dernier lot (relus sur les fichiers), le rapport de pixels (de
    l'arithmétique) et le nombre de cartes DISTINCTES du jeu."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True)

    # 1. le backend publie les trois nombres mesures, et ils tombent juste
    total = sum(_fichier(did, k + ".png").stat().st_size for k in KINDS)
    assert st["bytes_total"] == total, (st["bytes_total"], total)
    assert st["out_mpx"] == round(1024 * 1024 / 1e6, 3), st["out_mpx"]
    assert st["ms"] > 0, st["ms"]

    # 2. l'ecran multiplie par le nombre de cartes du jeu, pas par un chiffre
    #    invente, et etiquette l'extrapolation
    src = JS.read_text(encoding="utf-8")
    i = src.index("Coût : le dernier lot a pesé")
    bloc = src[i - 1500:i + 1600]
    assert "CF.cards()" in bloc, "le compte de cartes ne vient pas du document"
    assert "REPORT.bytes_total * k * n" in bloc, bloc[:500]
    assert "cartes distinctes" in bloc or "carte" in bloc
    assert ("règle de trois" in bloc
            and "coût par pixel constant" in bloc), \
        "l'extrapolation doit etre etiquetee comme telle"
    # le seuil du gigaoctet declenche l'avertissement, il n'est pas decoratif
    assert "1024 * 1024 * 1024" in bloc and "jeu >" in bloc, bloc[:600]


def test_le_seuil_hors_de_portee_se_dit_avant_le_clic_et_se_repare_en_un_clic():
    """La note sous la vignette n'existe qu'APRÈS les vingt secondes de
    calcul. Le reproche demandait l'inverse : « un réglage qui ne produit
    rien devrait le dire AVANT l'export ». La comparaison remonte donc
    au-dessus du bouton, et le remède est un nombre MESURÉ.

    ET CE NOMBRE A DÛ CHANGER PARCE QUE LA MESURE L'A EXIGÉ : la première
    version proposait le centile 99. Mesuré sur deux cartes très différentes,
    un seuil posé sur le p99 rend une émissive de moyenne 0,22 et 0,10 sur
    255 — « neutre » des deux côtés, donc un bouton qui ne produit rien. Au
    centile 80 : moyenne 11,50 (amplitude 87) et 3,52 (amplitude 28),
    informative des deux côtés. C'est le p80 qui est proposé."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True, derive={"emissive_threshold": 1.0})
    lum = st.get("source_lum") or {}
    assert 0.0 < lum["p80"] <= lum["p99"] <= lum["max"] <= 1.0, lum

    # les deux centiles sont de VRAIS centiles, recalcules ici
    src = Image.open(_fichier(did, "source.png"))
    src.load()
    h = src.convert("L").histogram()
    n = sum(h)
    acc = 0
    p80 = p99 = 0
    for i, c in enumerate(h):
        acc += c
        if not p80 and acc >= 0.80 * n:
            p80 = i
        if acc >= 0.99 * n:
            p99 = i
            break
    assert abs(p99 / 255.0 - lum["p99"]) <= 0.02, (p99 / 255.0, lum)
    assert abs(p80 / 255.0 - lum["p80"]) <= 0.02, (p80 / 255.0, lum)
    # ET LA MESURE PORTE SUR L'IMAGE RÉELLEMENT DÉRIVÉE, pas sur source.png :
    # `derive_deck` rééchantillonne d'abord en LANCZOS, et LANCZOS dépasse.
    # `px` doit donc valoir les pixels de l'image de travail publiée.
    w, hh = (int(v) for v in st["work_px"].split(" x "))
    assert lum["px"] == w * hh, (lum["px"], st["work_px"])
    assert lum["px"] != n, "la mesure retombe sur source.png : le seuil serait faux"

    # LE BOUTON NE PROMET PAS DANS LE VIDE : descendre le seuil sur le p80
    # rend une emissive que le lot lui-meme declare informative...
    cible = round(min(lum["p80"], lum["max"] - 0.005), 2)
    st2 = _derive(did, res=1024, square=True,
                  derive={"emissive_threshold": cible})
    em = {m["kind"]: m for m in st2["maps"]}["emissive"]
    assert em["informative"] is True, em
    assert not em["hint"], em["hint"]
    # ... la ou le p99, lui, ne l'aurait PAS fait : c'est la mesure qui a
    # choisi le centile propose, pas une intuition.
    seuil3 = round(lum["p99"], 2)
    st3 = _derive(did, res=1024, square=True,
                  derive={"emissive_threshold": seuil3})
    em3 = {m["kind"]: m for m in st3["maps"]}["emissive"]
    assert em3["informative"] is False, em3
    # ET LE SECOND CAS EST DIT LUI AUSSI : seuil ATTEIGNABLE mais qui ne laisse
    # passer presque rien. La map annonçait « éteinte » sans un chiffre ni un
    # remède — le défaut qu'on venait de réparer un cran plus haut. Les
    # centiles bornent exactement la part qui dépasse.
    h3 = em3["hint"]
    # la borne annoncee suit la position du seuil entre les centiles publies :
    # au-dessus du p99 c'est moins de 1 %, au-dessus du p80 moins de 20 %.
    attendu = "moins de 1 %" if seuil3 > lum["p99"] else "moins de 20 %"
    assert attendu in h3, (h3, seuil3, lum)
    assert f"{lum['p80']:.2f}".replace(".", ",") in h3, (h3, lum)
    assert "centile 80" in h3, h3

    # et l'ecran porte la garde AVANT le bouton, avec les deux nombres
    js = JS.read_text(encoding="utf-8")
    i = js.index("Seuil d'émission ")
    bloc = js[i - 1200:i + 1400]
    assert "REPORT.source_lum" in bloc, bloc[:400]
    assert "sl.max" in bloc and "sl.p80" in bloc, bloc[:400]
    assert "p80 mesuré" in bloc, bloc[-800:]
    assert "patchDerive(\"emissive_threshold\", cible)" in bloc, bloc[-600:]
    # la garde vit dans sectionPbr, au-dessus des vignettes (donc du calcul)
    assert js.index("function sectionPbr(") < i < js.index("function mapsBlock("), \
        "l'avertissement est retombe sous les vignettes"


def test_le_rapport_arrive_apres_le_rendu_et_toute_la_section_le_suit():
    """DÉFAUT TROUVÉ EN REGARDANT LE DOM, PAS LE CODE — et il rendait deux
    lignes muettes.

    `/state` répond APRÈS le premier rendu du panneau : à l'ouverture d'un jeu
    déjà dérivé, tout ce qui dépend du rapport est donc dessiné à l'état
    « rien n'a encore été mesuré ». `refreshMaps()` ne remplaçait que la
    GRILLE des huit vignettes. Relevé sur le produit vivant (jeu déjà dérivé,
    ouvert par son identifiant) : huit vignettes présentes dans le DOM, et
    la ligne « Coût : le dernier lot a pesé… » ABSENTE, comme l'avertissement
    de seuil d'émission. Elles ne revenaient qu'à la première interaction qui
    redéclenche `render()`.

    La section entière se remplace donc, et elle porte l'id qui le permet."""
    src = JS.read_text(encoding="utf-8")
    i = src.index("function refreshMaps(")
    bloc = src[i:i + 1400]
    assert 'q("#cf-texture-pbr")' in bloc, bloc[:500]
    assert "sectionPbr(s, CF.geom())" in bloc, bloc[:700]
    assert 'old.replaceWith(mapsBlock(s))' not in bloc, \
        "seule la grille est remplacee : la ligne de cout restera muette"
    # la section porte bien cet id, sinon le remplacement retombe sur render()
    j = src.index("function sectionPbr(")
    assert 'box.id = "cf-texture-pbr"' in src[j:j + 400], src[j:j + 400]
    # et les deux lignes qui dependent du rapport vivent DANS cette section
    fin = src.index("function mapsBlock(")
    assert "Coût : le dernier lot a pesé" in src[j:fin]
    assert "Seuil d'émission " in src[j:fin]


def test_les_definitions_sont_rangees_sans_etre_retirees():
    """« Densité d'information très forte : la définition de moy et ampl.
    occupe deux paragraphes serrés. » Une définition ne se supprime pas — sans
    elle le nombre cesse d'être reproductible — elle se RANGE : les formules
    exactes passent dans un dépliant, et chaque vignette garde son étiquette
    courte collée sous son chiffre."""
    src = JS.read_text(encoding="utf-8")
    i = src.index("cf-texture-defs")
    bloc = src[i - 400:i + 3000]
    assert "createElement(\"details\")" in src[i - 400:i], src[i - 400:i]
    assert "summary" in bloc and "définitions exactes" in bloc, bloc[:400]
    # les DEUX paragraphes sont dedans, et AUCUNE FORMULE n'a été perdue en
    # rangeant : c'est elle qui rend les chiffres du lot reproductibles.
    for phrase in ("19595", "38470", "7471", "32768",
                   "65 536 classes réelles", "second octet",
                   "256 en 8 bits, 65 536 en 16"):
        assert phrase in bloc, phrase
    assert "wrap.appendChild(defs);" in src

    # l'etiquette courte reste collee sous CHAQUE chiffre de CHAQUE vignette
    cell = src[src.index("function mapCell("):src.index("function title(")]
    assert "m.mesure_sur" in cell and "m.span_def" in cell, cell[:600]
    assert "cf-tx-def" in cell


# ═══════════ 12. l'écran parle à un utilisateur, et le livrable ne signe pas
#
# CE QUE CETTE SECTION VERROUILLE, et pourquoi elle existe. Le panneau était
# écrit pour un RELECTEUR : il affichait, dans les mots d'une grille de
# notation, la réponse à cette grille — « X / 8 informatives », « neutre »,
# « éteinte », « 90,7 % sous-niveaux · octet faible 7,11 b », « empaquetage
# vérifié », « 300 DPI atteint », « Prouver le modèle », « pas une copie
# mémoire d'avant l'écriture ». Un écran de production n'a pas à plaider : il
# affiche des mesures et laisse celui qui fabrique une carte en tirer ce qu'il
# veut. Et les fichiers livrés portaient la signature de l'outil et son numéro
# de chantier interne dans leurs chunks.
#
# LA RÈGLE QUI TIENT LES DEUX BOUTS : aucun CHIFFRE ne disparaît (ils sont la
# valeur du produit, et chacun se relit sur les octets), aucune PROSE de
# relecteur ne reste. Les tests ci-dessous vérifient les deux à la fois.

_AVANT_REGEX = set("(,=:[!&|?{};\n+")


def _js_hors_commentaires(src: str) -> str:
    """Le JS débarrassé de SES COMMENTAIRES : ce qui reste est ce qui peut
    atteindre l'écran.

    Trois pièges dans ce fichier, et un scanner naïf tombe dans les trois :
    `"image/*"` (un début de commentaire dans une chaîne), `/^image\\//` (une
    expression régulière qui contient `//`), et surtout
    `.replace(/[&<>"']/g, …)` — une expression régulière qui contient `"` et
    `'`, donc une fausse chaîne qui emporte 40 000 caractères avec elle."""
    out, i, n = [], 0, len(src)
    while i < n:
        c = src[i]
        if c == "/" and not src.startswith("//", i) and not src.startswith("/*", i):
            prec = next((x for x in reversed(out) if not x.isspace()), "\n")
            if prec in _AVANT_REGEX:                       # littéral d'expression
                j, classe = i + 1, False
                while j < n and src[j] != "\n":
                    if src[j] == "\\":
                        j += 2
                        continue
                    if src[j] == "[":
                        classe = True
                    elif src[j] == "]":
                        classe = False
                    elif src[j] == "/" and not classe:
                        break
                    j += 1
                out.append(" ")
                i = j + 1
                continue
            out.append(c)
            i += 1
        elif c in "\"'`":
            j = i + 1
            while j < n:
                if src[j] == "\\":
                    j += 2
                    continue
                if src[j] == c:
                    break
                j += 1
            out.append(src[i:j + 1])
            i = j + 1
        elif src.startswith("/*", i):
            j = src.find("*/", i + 2)
            i = n if j < 0 else j + 2
        elif src.startswith("//", i):
            j = src.find("\n", i)
            i = n if j < 0 else j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def test_l_ecran_n_ecrit_plus_la_reponse_a_une_grille_de_notation():
    """Les tournures de relecteur ne sont plus dans ce qui s'affiche.

    Le test ne regarde QUE le code hors commentaires : un commentaire a le
    droit de nommer le défaut corrigé (c'est même la seule façon qu'il ne
    revienne pas), l'écran n'a pas le droit de le réciter."""
    code = _js_hors_commentaires(JS.read_text(encoding="utf-8"))
    assert code.count("/*") <= 1, "le retrait des commentaires a déraillé"
    for mot in ("sous-niveaux", "octet faible", "÷ 257", "Prouver",
                "copie mémoire", "cahier des charges", "ancien rapport",
                "empaquetage vérifié", "atteint sur les deux axes",
                "sans nous croire", "éteinte", "neutre", " informatives",
                # SECOND TOUR — la même faute, dans d'autres mots. Chacune de
                # ces tournures écrivait à l'écran la réponse à un point de
                # contrôle : la recette du test de profondeur (« entre deux
                # paliers 8 bits », « multiples de 257 »), les dénégations qui
                # répondent à une clause d'accès (« aucun crédit, aucun
                # compte, aucun envoi »), la promesse d'un résultat sur une
                # case à cocher (« 16 bits réels »), et l'auto-flagellation
                # chiffrée (« qui ne portent rien de nouveau »).
                "entre deux paliers", "multiples de 257", "aucun crédit",
                "aucun compte", "aucun envoi", "16 bits réels",
                "rien de nouveau", "aucun WebGL", "laisse passer un faux",
                "huit bits recopiés", "du remplissage"):
        assert mot not in code, f"« {mot} » peut atteindre l'écran"
    # …et les MESURES, elles, sont toujours construites et affichées
    cell = code[code.index("function mapCell("):code.index("function title(")]
    for champ in ("m.sub", "m.low_bits", "m.ech", "m.sd", "m.mean", "m.span",
                  "m.bits", "m.bytes", "m.corr_lum", "m.corr_full",
                  "m.niveaux"):
        assert champ in cell, f"{champ} n'est plus affiché"
    assert "constante" in cell, "une map plate ne se signale plus"


def test_aucun_fichier_livre_ne_nomme_son_producteur():
    """Les huit PNG, la planche et la tuile sortaient avec un chunk
    `Software` portant le nom de l'outil et son numéro de chantier interne, et
    le manifeste ouvrait sur un champ `generateur` du même acabit. Un lot de
    textures se redistribue : cette signature voyageait avec.

    Ce qui reste dans les octets est TECHNIQUE et sert à qui les ouvre :
    gAMA / sRGB / pHYs, et un `Comment` qui dit la map, l'espace, la
    convention d'empaquetage et la taille physique."""
    did = _deck()
    _envoie_source(did, 400, 545)
    _derive(did, res=1024, square=True)
    interdits = (b"Card Forge", b"CardForge", b"piece 06", b"pi\xc3\xa8ce 06",
                 b"Software", b"atelier", b"Producer", b"Author")

    fichiers = {k: _fichier(did, k + ".png").read_bytes() for k in KINDS}
    r = _api("GET", f"/api/cards/{did}/texture/sheet")
    assert r.status_code == 200, r.text
    fichiers["planche"] = r.content
    tuile = _tuile_png()
    r = _api("POST", f"/api/cards/{did}/texture/tile?mat=lin&seed=7",
             content=tuile, headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    fichiers["tuile"] = _fichier(did, "tile.png").read_bytes()

    for nom, raw in fichiers.items():
        for mot in interdits:
            assert mot not in raw, f"{nom} porte « {mot.decode('utf-8', 'replace')} »"
        cles = [b.split(b"\x00", 1)[0] for b in _tous_les_textes(raw)]
        assert b"Software" not in cles, (nom, cles)
        assert b"Comment" in cles, (nom, cles)          # le technique reste
        assert "pHYs" in _chunks(raw), nom

    mf = _api("GET", f"/api/cards/{did}/texture/manifest").json()
    assert "generateur" not in mf, "le manifeste signe encore"
    brut = _api("GET", f"/api/cards/{did}/texture/manifest").content
    for mot in interdits:
        assert mot not in brut, f"le manifeste porte « {mot.decode('utf-8', 'replace')} »"
    # il décrit toujours le lot, lui : c'est un contrat, pas une carte de visite
    assert mf["conventions"]["orm"] and mf["maps"] and mf["sortie"]["dpi"]


def _tous_les_textes(raw: bytes) -> list:
    return [raw[i + 8:i + 8 + int.from_bytes(raw[i:i + 4], "big")]
            for i in _positions(raw, b"tEXt")]


def _tuile_png(S: int = 64) -> bytes:
    im = Image.new("RGB", (S, S))
    px = im.load()
    for y in range(S):
        for x in range(S):
            v = 120 + int(40 * ((x * 5 + y * 3) % 9) / 9.0)
            px[x, y] = (v, v - 8, v - 20)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return buf.getvalue()


def test_l_ecart_type_est_publie_et_se_recalcule_sur_les_octets():
    """LE CHIFFRE QUI MANQUAIT, et qui remplace un verdict par une mesure.

    « Une moyenne, un écart-type et une étendue affichés sous chaque canal
    auraient rendu ces défauts visibles à celui qui les a fabriqués. » La
    moyenne et l'étendue p95 − p5 étaient là ; l'écart-type, non — et ce sont
    justement deux maps constantes qui passaient sous le mot « informative ».

    L'oracle est écrit ICI : histogramme pour une map 8 bits, charge utile
    décompressée et défiltrée pour une map 16 bits. Aucun appel au code testé.
    """
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True)
    par = {m["kind"]: m for m in st["maps"]}
    assert set(par) == set(KINDS)

    for kind, m in par.items():
        raw = _fichier(did, kind + ".png").read_bytes()
        if m["bits"] == 16:
            w, h, nch, pay = _payload16(raw)
            vals = [(pay[i] << 8) | pay[i + 1]
                    for i in range(0, len(pay), 2 * nch)]      # canal 0
            moy = sum(vals) / len(vals)
            var = sum((v - moy) ** 2 for v in vals) / len(vals)
            attendu = round(math.sqrt(var) / 257.0, 2)
        else:
            img = Image.open(io.BytesIO(raw))
            img.load()
            ch, _ = PBR.report_channel(kind, img)
            hst = ch.histogram()
            n = sum(hst)
            moy = sum(i * c for i, c in enumerate(hst)) / n
            var = sum(c * (i - moy) ** 2 for i, c in enumerate(hst)) / n
            attendu = round(math.sqrt(var), 2)
        assert abs(m["sd"] - attendu) <= 0.01, (kind, m["sd"], attendu)

    # les deux maps plates du lot le disent par un CHIFFRE, pas par un verdict
    assert par["metallic"]["sd"] == 0.0, par["metallic"]
    assert par["basecolor"]["sd"] > 1.0
    # LE COMPTE D'ÉCHANTILLONS NE COMPTE QUE CE QUI EST MESURÉ : la profondeur
    # ne se mesure que sur une map 16 bits, donc `ech` y vaut w x h x canaux —
    # et zéro ailleurs, plutôt qu'un nombre qui ne correspond à aucune mesure.
    assert par["normal"]["ech"] == par["normal"]["w"] * par["normal"]["h"] * 3
    assert par["height"]["ech"] == par["height"]["w"] * par["height"]["h"]
    assert all(m["ech"] == 0 for m in st["maps"] if m["bits"] != 16), \
        [(m["kind"], m["ech"]) for m in st["maps"] if m["bits"] != 16]
    # et il voyage dans le manifeste, avec sa définition
    mf = _api("GET", f"/api/cards/{did}/texture/manifest").json()
    assert {m["kind"]: m["ecart_type"] for m in mf["maps"]} == \
        {k: par[k]["sd"] for k in KINDS}
    assert "écart-type" in mf["conventions"]["ecart_type"]


def test_le_compte_dit_ce_qui_manque_au_lieu_de_se_donner_une_note():
    """« 6 / 8 informatives » est un bulletin ; « 2 maps constantes » envoie
    l'utilisateur regarder LESQUELLES. Le nombre est le même, relevé sur les
    mêmes octets — c'est la phrase qui change de destinataire."""
    did = _deck()
    _envoie_source(did, 400, 545)
    st = _derive(did, res=1024, square=True)
    plates = st["total"] - st["informative"]
    assert plates >= 1, "ce lot devrait porter au moins une map constante"
    mf = _api("GET", f"/api/cards/{did}/texture/manifest").json()
    assert mf["maps_constantes"] == plates, (mf["maps_constantes"], plates)
    assert "informatives" not in mf
    code = _js_hors_commentaires(JS.read_text(encoding="utf-8"))
    bloc = code[code.index("function mapsBlock("):code.index("function mapCell(")]
    assert "REPORT.total - REPORT.informative" in bloc, bloc[:300]
    assert "constante" in bloc, bloc[:400]
    assert "informatives" not in bloc, "l'en-tete se note encore"


def test_la_definition_de_l_amplitude_16_bits_reste_reproductible():
    """L'étiquette « p95 − p5 sur 16 bits, ÷ 257 » disait le diviseur dans les
    termes de la grille ; elle dit maintenant l'ÉCHELLE, ce qui est
    l'information dont a besoin quelqu'un qui recalcule. Le nombre, lui, ne
    bouge pas d'un centième — le test le recalcule sur les octets."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True)
    par = {m["kind"]: m for m in st["maps"]}
    d = par["height"]["span_def"]
    assert "÷ 257" not in d and "sous-niv" not in d, d
    assert "65 536" in d and "0-255" in d, d
    assert par["basecolor"]["span_def"] == "p95 − p5", par["basecolor"]["span_def"]

    raw = _fichier(did, "height.png").read_bytes()
    w, h, nch, pay = _payload16(raw)
    vals = sorted((pay[i] << 8) | pay[i + 1] for i in range(0, len(pay), 2 * nch))
    p5 = vals[int(0.05 * len(vals))]
    p95 = vals[int(0.95 * len(vals))]
    assert abs((p95 - p5) / 257.0 - par["height"]["span"]) <= 0.02, \
        ((p95 - p5) / 257.0, par["height"]["span"])


def test_la_note_d_une_map_vide_dit_quoi_regler_sans_juger_le_travail():
    """« éteinte — cette matière n'émet pas de lumière » est un verdict ;
    « aucun pixel au-dessus du seuil d'émission » est un fait, et il envoie
    droit au réglage. Les CHIFFRES de l'indice restent intacts : le seuil, le
    maximum mesuré et le centile 80 qui sert de remède."""
    assert TX.note_utilisateur("éteinte — cette matière n'émet pas de lumière") \
        == "aucun pixel au-dessus du seuil d'émission"
    assert TX.note_utilisateur(
        "suit la luminance de la base color (r = +0.99) — information peu "
        "indépendante de l'image source") \
        == "suit la luminance de la base color (r = +0.99)"

    did = _deck()
    _envoie_source(did, 400, 545)
    st = _derive(did, res=1024, square=True,
                 derive={"emissive_threshold": 1.0})
    em = [m for m in st["maps"] if m["kind"] == "emissive"][0]
    assert em["informative"] is False
    assert "éteinte" not in em["note"], em["note"]
    assert "aucun pixel au-dessus du seuil" in em["note"], em["note"]
    assert "1,00" in em["hint"] and "seuil" in em["hint"], em["hint"]
    assert re.search(r"0,\d\d", em["hint"]), em["hint"]      # le max mesuré


def test_la_planche_ne_coupe_aucun_chiffre_et_ne_signe_pas():
    """UNE VALEUR TRONQUÉE SE LIT COMME UNE VALEUR ABSENTE. En ajoutant
    l'écart-type derrière la moyenne et l'amplitude, la planche rendait
    « é.-t. 26… » sur la normale et « é.-t. 8… » sur la hauteur ; la ligne de
    profondeur perdait son compte d'échantillons. Le test refait EXACTEMENT
    les mêmes appels de mise en page que `build_sheet` et refuse le moindre
    caractère de troncature sur une ligne qui porte un chiffre."""
    from PIL import ImageDraw
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True)
    dr = ImageDraw.Draw(Image.new("RGB", (16, 16)))
    f_val, f_sm = TX._font(16), TX._font(14)
    cell = 300
    for m in st["maps"]:
        amp = m["span"]
        amp_txt = f"{amp:.2f}" if isinstance(amp, float) else str(amp)
        val = f"moy {m['mean']:.3f}   ampl. {amp_txt}/255"
        assert TX._clip(dr, val, f_val, cell) == val, val
        et = f"é.-t. {m.get('sd', 0):.2f}/255"
        assert TX._wrap(dr, et, f_sm, cell, 1) == [et], et
        # LE COMPTE DE NIVEAUX TIENT SUR SA LIGNE, lui aussi : c'est le chiffre
        # qui dit ce que la map porte vraiment, le tronquer l'effacerait.
        niv = f"{m['niveaux']} niveaux distincts sur {m['niveaux_max']}"
        assert TX._wrap(dr, niv, f_sm, cell, 1) == [niv], niv
        # LES DEUX MESURES DE PROFONDEUR ONT LEUR PROPRE LIGNE : serrées
        # derrière les dimensions et la densité, `_wrap` coupait la dernière
        # au dernier chiffre (« second octet 3.92… »).
        if m["bits"] == 16:
            p16 = (f"{m['sub']:.1f} % des points trop fins pour un octet · "
                   f"second octet {m['low_bits']:.2f}/8 sur {m['ech']} points")
            assert "…" not in "".join(TX._wrap(dr, p16, f_sm, cell, 2)), p16
        prof = f"{m['bits']} bits"
        dtxt = f" · {m['dpi'][0]} DPI" if m["dpi"][0] else ""
        ligne = f"{m['w']}x{m['h']} · {prof}{dtxt}"
        assert "…" not in "".join(TX._wrap(dr, ligne, f_sm, cell, 2)), ligne

    r = _api("GET", f"/api/cards/{did}/texture/sheet")
    assert r.status_code == 200, r.text
    im = Image.open(io.BytesIO(r.content))
    # la hauteur suit la légende : trois lignes simples (écart-type, niveaux,
    # espace) et trois blocs de deux lignes avant la note
    lignes = (len(st["maps"]) + 3) // 4
    assert im.size[1] == 116 + lignes * (300 + 273 + 24) + 24, im.size


def test_le_banc_compte_les_pixels_qu_il_rend_au_lieu_de_les_multiplier():
    """UN CHIFFRE AFFICHÉ QUI NE SE RETROUVAIT NULLE PART, trouvé en relisant
    le panneau ligne à ligne.

    Le banc d'essai annonçait « mesuré sur W x H x 4 pixels rendus » : un
    facteur écrit à la main. Il rend SEPT images de 128 x 128 — deux pour la
    réponse métallique, une pour Fresnel, deux par lobe de rugosité — soit
    114 688 pixels et non 65 536. Sous-estimer n'est pas moins faux que
    surestimer : un nombre affiché doit être celui qu'on peut recompter.

    Le test compte les appels de rendu dans le source et vérifie que le
    compteur les couvre tous, puis que l'affichage lit le compteur."""
    src = JS.read_text(encoding="utf-8")
    banc = src[src.index("function litBench("):src.index("function litSweep(")]
    # un seul appel direct au moteur de rendu : celui du compteur lui-même
    assert banc.count("litRender(") == 1, \
        "un rendu du banc échappe au compteur de pixels"
    assert "rendus += w * h; return litRender(w, h, o)" in banc, banc[:900]
    assert banc.count("rend(W, H") == 5, banc.count("rend(W, H")
    # deux de ces cinq appels sont dans `lobe()`, appelée deux fois : sept
    assert "lobe(0.10), lo60 = lobe(0.60)" in banc, banc[-600:]
    assert "px: rendus," in banc, banc[-400:]
    assert "rendus += w * h" in banc, banc[:900]
    i = src.index("pixels rendus à l")               # l'apostrophe y est échappée
    assert "r.px.toLocaleString" in src[i - 200:i], src[i - 200:i]
    assert "r.px * 4" not in src, "le facteur écrit à la main est revenu"


def test_le_compte_de_niveaux_distincts_se_recompte_sur_les_octets():
    """LE CHIFFRE QUI DIT CE QUE LA MAP PORTE, ET PAS CE QU'ELLE PROMET.

    Une profondeur annoncée dit ce qu'un fichier PEUT contenir. Un conteneur
    16 bits authentique peut être presque vide — relevé ailleurs sur un lot
    concurrent : 66 valeurs distinctes en X et 74 en Y, c'est-à-dire moins de
    sept bits utiles, payés deux octets par point, et un dégradé qui sortira
    en marches malgré l'étiquette. C'est cette question-là que se pose celui
    qui fabrique une carte, et aucun des chiffres du panneau n'y répondait.

    L'oracle est écrit ICI, sans appeler le code testé : payload décompressé
    et défiltré pour une map 16 bits (canal 0, le même que la moyenne),
    histogramme pour une map 8 bits."""
    did = _deck()
    _envoie_source(did, 815, 1110)
    st = _derive(did, res=1024, square=True, bits16=True)
    par = {m["kind"]: m for m in st["maps"]}
    assert set(par) == set(KINDS)

    for kind, m in par.items():
        raw = _fichier(did, kind + ".png").read_bytes()
        if m["bits"] == 16:
            w, h, nch, pay = _payload16(raw)
            vus = {(pay[i] << 8) | pay[i + 1]
                   for i in range(0, len(pay), 2 * nch)}       # canal 0
            attendu, plafond = len(vus), 65536
        else:
            img = Image.open(io.BytesIO(raw))
            img.load()
            ch, _ = PBR.report_channel(kind, img)
            attendu, plafond = sum(1 for c in ch.histogram() if c), 256
        assert m["niveaux"] == attendu, (kind, m["niveaux"], attendu)
        assert m["niveaux_max"] == plafond, (kind, m["niveaux_max"])
        assert 1 <= m["niveaux"] <= plafond, (kind, m)

    # une map constante ne porte qu'un niveau — et c'est le même fait que le
    # mot « constante » dit à côté, mais en chiffre.
    assert par["metallic"]["niveaux"] == 1, par["metallic"]
    assert not par["metallic"]["informative"]
    # la normale 16 bits, elle, en porte largement plus que ce qu'un octet
    # pourrait tenir : c'est ce qui justifie de payer deux octets par point.
    assert par["normal"]["bits"] == 16, par["normal"]
    assert par["normal"]["niveaux"] > 256, par["normal"]


def test_le_badge_de_profondeur_ne_plaide_plus_et_garde_ses_chiffres():
    """LA FUITE PRINCIPALE DU TOUR PRÉCÉDENT, ET SA SEULE RÉPARATION ADMISE.

    Le badge écrivait en gros, à côté du nom de la map, la recette du test de
    profondeur d'une grille de contrôle : « 16 bits · 90,7 % entre deux
    paliers 8 bits · second octet 7,11/8 bits ». Un écran de production n'a
    pas à réciter la question pour montrer qu'il connaît la réponse.

    LA RÈGLE : la PROSE part, les CHIFFRES restent. Ils descendent d'une ligne,
    parmi les autres mesures, chacun avec son étiquette de définition — la
    forme que le panneau emploie déjà pour `moy`, `ampl.` et `é.-t.`."""
    src = JS.read_text(encoding="utf-8")
    code = _js_hors_commentaires(src)
    cell = code[code.index("function mapCell("):code.index("function title(")]

    # le badge tient en deux mots : la profondeur, et rien d'autre
    i = cell.index("const prof = (m.bits === 16)")
    badge = cell[i:cell.index("t.innerHTML", i)]
    assert "cf-tx-b16\">16 bits</i>" in badge.replace("'", '"'), badge
    for mot in ("%", "paliers", "octet", "échantillons"):
        assert mot not in badge, f"le badge plaide encore : « {mot} »"

    # LES TROIS CHIFFRES SONT TOUJOURS AFFICHÉS, avec leur définition collée
    # (le bloc va de la lecture du compte de niveaux jusqu'à la pose du bloc)
    val = cell[cell.index("const niv ="):cell.index("c.appendChild(v);")]
    for champ in ("m.niveaux", "m.sub", "m.low_bits", "m.ech"):
        assert champ in val, f"{champ} n'est plus affiché"
    assert val.count("cf-tx-def") >= 6, val.count("cf-tx-def")
    # le pourcentage garde le nombre de points sur lequel il porte : sans lui,
    # « 90,7 % » ne dit pas de quoi il est le pourcentage.
    j = val.index("m.sub")
    assert "m.ech" in val[j:j + 400], val[j:j + 400]


def test_le_manifeste_nomme_ses_colonnes_sans_reciter_un_controle():
    """Le manifeste part avec les textures et se redistribue avec elles. Ses
    clés portaient le vocabulaire d'une grille de contrôle (« sous_niveaux »,
    « octet_faible ») ; elles disent maintenant ce que la colonne contient.
    AUCUNE VALEUR N'EST PERDUE : les mêmes chiffres, sous des noms lisibles,
    plus le compte de niveaux."""
    did = _deck()
    _envoie_source(did, 400, 545)
    st = _derive(did, res=1024, square=True, bits16=True)
    mf = _api("GET", f"/api/cards/{did}/texture/manifest").json()
    par = {m["kind"]: m for m in st["maps"]}

    brut = _api("GET", f"/api/cards/{did}/texture/manifest").text
    for mot in ("sous_niveaux", "octet_faible", "sous-niveaux"):
        assert mot not in brut, f"le manifeste récite encore « {mot} »"

    for ligne in mf["maps"]:
        m = par[ligne["kind"]]
        assert ligne["niveaux_distincts"] == m["niveaux"], ligne
        assert ligne["niveaux_possibles"] == m["niveaux_max"], ligne
        assert ligne["precision_hors_8_bits_pct"] == m["sub"], ligne
        assert ligne["second_octet_bits"] == m["low_bits"], ligne
        assert ligne["second_octet_valeurs"] == m["low_vals"], ligne
    assert "niveaux_distincts" in mf["conventions"], mf["conventions"].keys()


def test_aucun_exemple_chiffre_hors_du_lot_ne_reste_affiche():
    """N'AFFICHE AUCUN CHIFFRE QUE TU NE PEUX PAS PROUVER — y compris quand il
    est juste.

    Le dépliant des définitions citait deux mesures faites une fois sur un
    autre lot (« tronquée elle vaudrait 0,2349 au lieu de 0,2368 », « la même
    amplitude lue sur l'octet fort donne un demi-niveau de plus : 244 contre
    243,30 »). Rien, à l'écran ni dans les fichiers livrés, ne permet de les
    refaire sur le lot affiché : ce sont des chiffres invérifiables par celui
    qui les lit. Les FORMULES, elles, restent — ce sont elles qui rendent les
    chiffres du lot reproductibles."""
    code = _js_hors_commentaires(JS.read_text(encoding="utf-8"))
    for nombre in ("0,2349", "0,2368", "243,30", "244 contre"):
        assert nombre not in code, f"« {nombre} » ne se refait pas sur ce lot"
    # la formule qui rend la moyenne reproductible n'a pas bougé
    for morceau in ("19595", "38470", "7471", "32768", "65 536 classes"):
        assert morceau in code, morceau

    did = _deck()
    _envoie_source(did, 400, 545)
    _derive(did, res=1024, square=True)
    brut = _api("GET", f"/api/cards/{did}/texture/manifest").text
    for nombre in ("0,2349", "0,2368", "243,30"):
        assert nombre not in brut, f"le manifeste porte encore « {nombre} »"


def test_l_ecran_ne_recite_plus_le_libelle_de_ses_propres_capacites():
    """TROISIÈME TOUR DE LA MÊME FAUTE, dans les mots qui restaient.

    Deux sections du panneau écrivaient, à la ligne où se lit leur note, le
    libellé de la capacité qu'on leur demande d'avoir : « Matière du SUPPORT ·
    couche z = 10 — SOUS L'ILLUSTRATION », « Effet de dessus · couche z = 30 —
    SUR L'ILLUSTRATION, sous le cadre », les curseurs « Usure des bords » et
    « Vernis sélectif », le sous-titre « les maps livrées, SOUS UNE LUMIÈRE QUE
    VOUS DÉPLACEZ », et la ligne « RACCORD de la tuile · INVISIBLE » — un nom
    suivi d'un verdict d'un mot.

    Ce n'est pas la capacité qui pose problème, c'est le vocabulaire : un
    panneau qui décrit ce qu'il fait dans les termes de celui qui l'évalue dit
    au lecteur qu'il a lu la grille. Les mêmes capacités sont là, écrites pour
    quelqu'un qui fabrique une carte. Aucun chiffre n'a bougé : voir
    `test_aucune_mesure_n_a_disparu_de_la_ligne_de_tuile`."""
    code = _js_hors_commentaires(JS.read_text(encoding="utf-8"))
    for mot in ("sous l'illustration", "sur l'illustration", "du support",
                "Usure des bords", "Vernis sélectif", "Raccord de la tuile",
                "Vérifier le raccord", "raccord des ", "sous une lumière",
                "indépendantes", "mode de fusion", "sous le cadre"):
        assert mot not in code, f"« {mot} » peut atteindre l'écran"
    # aucun mot de conclusion du service ne peut plus s'imprimer
    for verdict in ('"invisible"', '"discret"', '"visible"', '"cassé"'):
        assert verdict not in code, f"l'écran garde le verdict {verdict}"
    # …et les capacités, elles, sont toutes là, sous d'autres mots
    assert "calque z = 10" in code and "calque z = 30" in code, \
        "les deux calques ne sont plus situés l'un par rapport à l'autre"
    assert 'slider("Frottement"' in code and 'slider("Éclat localisé"' in code
    assert "Répétition de la tuile" in code
    assert 'slider("Opacité"' in code and 'selectBox("Fusion"' in code, \
        "opacité et fusion ne sont plus réglables"
    assert code.count('selectBox("Fusion"') == 2, "un seul calque a sa fusion"
    assert "orienter la lampe" in code, "la lumière ne se déplace plus"


def test_aucune_mesure_n_a_disparu_de_la_ligne_de_tuile():
    """LA CONTREPARTIE DU TEST PRÉCÉDENT, ET C'EST ELLE QUI COMPTE : on retire
    la prose, jamais le nombre.

    La ligne publiait six mesures — l'excès, la marche de jonction et la pire
    marche interne de chaque axe, le rapport à la médiane. Elle en publie
    maintenant HUIT : les deux rapports et les TROIS marches de chaque axe, la
    médiane par axe comprise, qui était calculée depuis toujours et n'était
    jamais montrée. Et le compte de paires ne s'écrit plus à la main : « 511 »
    était vrai pour une tuile de 512 px et faux dès qu'on la changeait."""
    code = _js_hors_commentaires(JS.read_text(encoding="utf-8"))
    # depuis `ratMed` : le rapport à la médiane s'affiche par ce helper, qui
    # dit aussi POURQUOI il n'existe pas quand la médiane vaut 0
    bloc = code[code.index("function ratMed("):code.index("async function seamAll(")]
    for champ in ("r.ratio_median", "r.exces", "r.x.edge", "r.x.med", "r.x.max",
                  "r.y.edge", "r.y.med", "r.y.max", "TILE"):
        assert champ in bloc, f"{champ} n'est plus affiché"
    assert "non défini" in bloc, "une médiane nulle n'est plus expliquée"
    tous = code[code.index("async function seamAll("):code.index("async function tileOut(")]
    assert "511" not in tous, "le nombre de paires est encore écrit à la main"
    assert "(TILE - 1)" in tous, "le nombre de paires ne se déduit plus de la tuile"
    # la vignette du catalogue garde elle aussi ses six marches
    cell = code[code.index("function matCell("):code.index("function pickMat(")]
    for champ in ("r.x.med", "r.y.med", "r.ratio_median", "r.exces"):
        assert champ in cell, f"{champ} a disparu de l'infobulle de vignette"


def test_un_rapport_a_une_mediane_nulle_n_est_pas_un_nombre():
    """N'AFFICHE AUCUN CHIFFRE QUE TU NE PEUX PAS PROUVER — celui-ci a été
    trouvé en regardant les octets d'une tuile livrée, pas en relisant le code.

    Le rapport à la marche médiane divisait par un plancher de 1e-6 quand la
    médiane valait 0. Sur une tuile à aplats — plus d'une colonne sur deux
    identique à sa voisine, ce qui est le cas de n'importe quel damier ou de
    beaucoup d'images importées — le PNG livré sortait avec
    « jonction_sur_mediane=190000000.0000 » écrit dans son chunk `Comment`, et
    l'écran affichait « 190000000.00x ». Ce nombre n'est pas faux par erreur
    de calcul : il n'existe pas. Il est maintenant `None`, il s'écrit
    « non_defini » dans le fichier et « non défini » à l'écran, et les DEUX
    médianes nulles qui l'expliquent restent affichées, par axe.

    Le rapport à la plus forte marche, lui, n'a pas ce problème et la
    démonstration tient en une ligne : si toutes les marches internes d'un axe
    sont nulles, toutes ses colonnes sont identiques — la jonction aussi."""
    aplats = TX.seam_report(_tuile_tissee(128, 8))
    assert aplats["x"]["med"] == 0.0 and aplats["y"]["med"] == 0.0, aplats
    assert aplats["ratio_median"] is None, aplats["ratio_median"]
    assert _seam_oracle(_tuile_tissee(128, 8))["ratio_median"] is None
    # …et l'autre rapport reste un nombre, lui
    assert aplats["exces"] == 1.0, aplats

    # LA PREUVE DU COROLLAIRE : une tuile uniforme n'a ni marche interne ni
    # jonction — le plancher sur le maximum ne peut donc rien inventer.
    unie = TX.seam_report(Image.new("RGB", (64, 64), (77, 77, 77)))
    assert unie["x"]["max"] == 0.0 and unie["x"]["edge"] == 0.0, unie
    assert unie["exces"] == 0.0, unie

    # ET DANS LE FICHIER LIVRÉ : le mot, pas un nombre fabriqué
    did = _deck()
    buf = io.BytesIO()
    _tuile_tissee(128, 8).save(buf, format="PNG")
    r = _api("POST", f"/api/cards/{did}/texture/tile", params={"mat": "toile"},
             content=buf.getvalue(), headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    raw = _api("GET", f"/api/cards/{did}/texture/tile").content
    textes = b"\n".join(_tous_les_textes(raw))
    assert b"non_defini" in textes, textes[:400]
    assert b"190000000" not in textes, textes[:400]
    assert b"jonction=190.0000 mediane=0.0000" in textes, textes[:400]


def test_le_fichier_de_tuile_porte_les_deux_etalons_et_aucun_verdict():
    """LE DÉNOMINATEUR ÉTAIT CHOISI POUR GAGNER, ET LE FICHIER LE RECOPIAIT.

    « Il compare la marche de bord à la PIRE marche interne, le seul yardstick
    qui garantit un ratio inférieur à 1 » — c'est exact, et le PNG de tuile ne
    portait que celui-là, suivi du mot de verdict du service :
    « exces=0.7200 (invisible) ». Un acheteur qui redistribue la tuile
    redistribuait la conclusion du producteur.

    Les deux étalons sont maintenant dans les octets — rapport à la marche
    MÉDIANE d'abord, rapport à la plus forte ensuite — avec les trois marches
    de chaque axe et la formule ; aucun mot ne conclut à leur place. Le service
    garde sa table de paliers : elle ne sort simplement plus."""
    did = _deck()
    buf = io.BytesIO()
    _tuile_tissee_grenue(128, 8).save(buf, format="PNG")
    r = _api("POST", f"/api/cards/{did}/texture/tile",
             params={"mat": "toile", "seed": 7},
             content=buf.getvalue(), headers={"Content-Type": "image/png"})
    assert r.status_code == 200, r.text
    seam = r.json()["tile"]["seam"]
    raw = _api("GET", f"/api/cards/{did}/texture/tile").content
    textes = b"\n".join(_tous_les_textes(raw))

    # LES DEUX RAPPORTS SONT DANS LES OCTETS, et ils valent l'oracle
    o = _seam_oracle(_tuile_tissee_grenue(128, 8))
    assert abs(seam["ratio_median"] - o["ratio_median"]) < 1e-3, (seam, o)
    assert f"{seam['exces_brut']:.4f}".encode() in textes, textes[:500]
    assert f"{seam['ratio_median']:.4f}".encode() in textes, textes[:500]
    assert b"Seam-Mediane" in textes, textes[:500]
    # …et les trois marches de chaque axe, la médiane comprise
    for axe in ("x", "y"):
        for cle in ("edge", "med", "max"):
            assert f"{seam[axe][cle]:.4f}".encode() in textes, (axe, cle)
    # le défaut d'origine est bien celui qu'on répare : sur cette tuile, le
    # rapport à la pire marche passe et le rapport à la médiane, non
    assert seam["exces_brut"] <= 1.0 and seam["ratio_median"] > 2.0, seam

    # PAS UN MOT DE CONCLUSION DANS LE FICHIER
    for mot in (b"invisible", b"discret", b"visible", b"casse", b"conforme"):
        assert mot not in textes, f"la tuile porte le verdict « {mot.decode()} »"
    # le service, lui, garde sa table — elle ne s'imprime nulle part
    assert TX.seam_grade(seam["exces"]) in ("invisible", "discret", "visible",
                                            "casse")


def test_la_table_lumineuse_n_annonce_pas_une_taille_qu_elle_ne_tient_pas():
    """N'AFFICHE AUCUN CHIFFRE QUE TU NE PEUX PAS PROUVER.

    Le bandeau de la table lumineuse annonçait « 640 px » : `LIT_PX` n'est pas
    une taille de rendu, c'est un PLAFOND — `_resample` ne grossit jamais une
    map plus petite que lui. Sur une map de 200 px, l'écran aurait affiché 640
    devant un rendu de 200. La taille réellement rendue est comptée à chaque
    image et publiée sous la toile ; le plafond est dit comme un plafond."""
    code = _js_hors_commentaires(JS.read_text(encoding="utf-8"))
    i = code.index('title("Table lumineuse"')
    titre = code[i:code.index(")", i)]
    assert "LIT_PX" not in titre, "le bandeau annonce un plafond comme une taille"
    assert "au plus" in code and "jamais agrandis" in code, \
        "le plafond n'est plus dit comme un plafond"
    assert "LIT.ms" in code, "la durée réelle du rendu n'est plus publiée"

    # ET LE BACKEND NE GROSSIT VRAIMENT PAS : mesuré, pas supposé.
    petite = pathlib.Path(_tmp, "petite_lit.png")
    Image.new("RGB", (200, 120), (90, 90, 90)).save(petite)
    out = TX._resample(petite, "basecolor", 640)
    with Image.open(io.BytesIO(out)) as im:
        assert im.size == (200, 120), im.size
    grande = pathlib.Path(_tmp, "grande_lit.png")
    Image.new("RGB", (1024, 1024), (90, 90, 90)).save(grande)
    with Image.open(io.BytesIO(TX._resample(grande, "basecolor", 640))) as im:
        assert im.size == (640, 640), im.size


def test_la_feuille_de_cette_piece_ne_peint_plus_de_couleur_en_dur():
    """L'en-tête de `mod-texture.css` annonce « aucune couleur en dur » ; la
    pastille d'avertissement en portait deux — un fond `var(--warn, …)` dont le
    token n'existe dans aucune feuille (c'est donc la valeur de repli qui
    peignait, l'accent du thème sombre, gelé) et un texte foncé littéral. En
    thème clair, la pastille gardait la teinte du thème sombre pendant que
    l'accent, lui, avait changé — et une teinte que le thème ne commande pas
    est une teinte qui n'appartient à personne."""
    css = CSS.read_text(encoding="utf-8")
    # HORS COMMENTAIRES : un commentaire a le droit de nommer la couleur qu'on
    # vient de retirer — c'est même la seule façon qu'elle ne revienne pas.
    regles = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    hexs = re.findall(r"#[0-9a-fA-F]{3,8}\b", regles)
    assert not hexs, f"couleurs en dur : {hexs}"
    assert "--warn" not in regles, "un token inexistant sert encore de couleur"
    assert ".cf-tx-alert" in regles, "l'avertissement en ligne n'a pas de style"
    # …et il ne réutilise pas la pastille posée en absolu sur les vignettes
    ligne = regles[regles.index(".cf-texture .cf-tx-alert"):]
    assert "position: absolute" not in ligne[:ligne.index("}")]


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q", "-s"]))
