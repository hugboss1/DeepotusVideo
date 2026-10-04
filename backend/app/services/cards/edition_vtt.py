# -*- coding: utf-8 -*-
"""Card Forge — P11, sidecar « table virtuelle » (tâche #84, plan-cartes T6, 04/10/2026).

SIDECAR, pas une pièce : aucun `router` ici (règle 8 — les routes vivent dans
edition.py). Ce fichier ne fait que des octets : planches et objet sauvegardé
de Tabletop Simulator.

CE QUE TTS PUBLIE (kb.tabletopsimulator.com, relu le 04/10/2026) :
  * Custom Deck : une PLANCHE d'images, découpée par TTS selon « how many cards
    horizontally and vertically » — sans maximum publié ; 10 x 7 est la
    convention des gabarits. TTS découpe par la GRILLE : la planche a donc
    TOUJOURS 10 x 7 cases, même à moitié vide (une planche rognée aux rangées
    utilisées étirerait les cartes).
  * « Custom Deck (Rectangle) 4096 x (whatever height fits) » ; PNG ou JPG, RVB.
  * La dernière case sert de carte cachée, SAUF avec « Back is Hidden » : on le
    coche, et les 70 cases portent des cartes.
  * L'objet : CustomDeck {FaceURL, BackURL, NumWidth, NumHeight, BackIsHidden,
    UniqueBack}, DeckIDs, CardID. CardID = 100 x clé de deck + index : relevé
    sur des objets sauvegardés, PAS publié par la base de connaissances.
DÉCISION DE L'UTILISATEUR (04/10) : les URL sont des chemins LOCAUX (file:///)
vers les planches écrites sur ce PC — ça marche tout de suite en solo ; pour
jouer en ligne, TTS propose « Upload to Steam Cloud ».
"""
from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
import zipfile
from pathlib import Path

from PIL import Image

from .contract import CardGeom, R

__all__ = ["COLS", "ROWS", "PAR_PLANCHE", "LARGEUR_MAX", "cellule", "coupe", "construire", "slug"]

COLS, ROWS = 10, 7
PAR_PLANCHE = COLS * ROWS            # BackIsHidden : les 70 cases portent des cartes
LARGEUR_MAX = 4096                   # « Custom Deck (Rectangle) 4096 x … »
QUALITE_JPEG = 92
DOS_NEUTRE = (52, 58, 70)

_SLUG_BAD = re.compile(r"[^A-Za-z0-9]+")


def slug(name: str) -> str:
    """RECOPIÉ (règle 8) de `print_gabarits.deck_slug` : un nom de fichier qui
    survit à Windows et à TTS. Jamais vide."""
    s = unicodedata.normalize("NFKD", str(name or "")).encode("ascii", "ignore").decode("ascii")
    s = _SLUG_BAD.sub("-", s).strip("-").lower()
    return s[:48].strip("-") or "jeu"


def cellule(g: CardGeom) -> tuple[int, int]:
    """La case d'une carte, au RATIO DE COUPE (TTS montre la carte finie, sans
    fond perdu), la plus grande qui laisse la planche 10 x 7 sous 4096 px sur
    les DEUX axes : 409 de large en général, la hauteur décide pour un format
    haut (tarot US : 339 x 585)."""
    tw, th = g.trim_px
    cw = LARGEUR_MAX // COLS
    ch = round(cw * th / tw)
    if ch * ROWS > LARGEUR_MAX:
        ch = LARGEUR_MAX // ROWS
        cw = round(ch * tw / th)
    return cw, ch


def coupe(data: bytes, g: CardGeom, i: int, cote: str) -> Image.Image:
    """Ouvre un bitmap de carte, REFUSE toute taille autre que la toile du jeu
    (le verrou « un seul moteur », recopié de P7), et le rend à la COUPE."""
    try:
        im = Image.open(io.BytesIO(data))
        im.load()
    except Exception:
        raise ValueError(f"{cote} {i + 1} : ce n'est pas une image lisible")
    w, h = im.size
    if (w, h) != tuple(g.canvas_px):
        raise ValueError(
            f"{cote} {i + 1} : {w}x{h} px ; la géométrie du jeu impose "
            f"{g.canvas_px[0]}x{g.canvas_px[1]} px ({g.label} à {g.dpi} DPI). "
            "Les cartes doivent venir de CF.renderCard, jamais d'un autre moteur.")
    bx, by = g.bleed_off_px
    x0, y0 = int(R(bx)), int(R(by))
    return im.convert("RGB").crop((x0, y0, x0 + g.trim_px[0], y0 + g.trim_px[1]))


def _jpeg(im: Image.Image) -> bytes:
    b = io.BytesIO()
    im.save(b, "JPEG", quality=QUALITE_JPEG, subsampling=0, optimize=True)
    return b.getvalue()


def _planche(images: list[Image.Image], cw: int, ch: int) -> Image.Image:
    p = Image.new("RGB", (COLS * cw, ROWS * ch), (255, 255, 255))
    for k, im in enumerate(images):
        p.paste(im.resize((cw, ch), Image.LANCZOS), ((k % COLS) * cw, (k // COLS) * ch))
    return p


def _url(chemin: Path) -> str:
    return "file:///" + chemin.resolve().as_posix()


def _transform(x: float = 0.0) -> dict:
    return {"posX": x, "posY": 1.0, "posZ": 0.0, "rotX": 0.0, "rotY": 180.0, "rotZ": 180.0,
            "scaleX": 1.0, "scaleY": 1.0, "scaleZ": 1.0}


def construire(nom_jeu: str, g: CardGeom, fronts: list[bytes], backs: list[bytes],
               noms: list[str], dossier: Path) -> tuple[bytes, dict]:
    """Écrit les planches et l'objet dans `dossier` (vidé d'abord : TTS met une
    image en CACHE par URL — le nom de chaque planche porte l'empreinte de son
    contenu, et seul le dernier export reste) ; rend (ZIP, résumé)."""
    n = len(fronts)
    cw, ch = cellule(g)
    faces = [coupe(d, g, i, "recto") for i, d in enumerate(fronts)]
    dos = [coupe(d, g, i, "verso") for i, d in enumerate(backs) if d]
    if dos and len(dos) != n:
        raise ValueError(f"{len(dos)} verso(s) pour {n} recto(s) : un verso par carte, ou aucun")
    uniques = bool(dos) and len({hashlib.sha256(d).digest() for d in backs}) > 1
    if not dos:
        note_dos = "aucun verso reçu : dos neutre uni"
    elif uniques:
        note_dos = "versos différents : planches de dos (UniqueBack)"
    else:
        note_dos = "verso commun : une seule image de dos"

    dossier.mkdir(parents=True, exist_ok=True)
    for vieux in dossier.iterdir():
        if vieux.is_file():
            vieux.unlink()
    s = slug(nom_jeu)
    fichiers: list[tuple[str, bytes]] = []

    def poser(nom: str, data: bytes) -> Path:
        chemin = dossier / nom
        chemin.write_bytes(data)
        fichiers.append((nom, data))
        return chemin

    dos_commun = None
    if not uniques:
        img_dos = dos[0].resize((cw, ch), Image.LANCZOS) if dos else Image.new("RGB", (cw, ch), DOS_NEUTRE)
        d = _jpeg(img_dos)
        dos_commun = poser(f"dos_{hashlib.sha256(d).hexdigest()[:10]}.jpg", d)

    custom, ids, cartes = {}, [], []
    for k in range(0, n, PAR_PLANCHE):
        cle = k // PAR_PLANCHE + 1
        d = _jpeg(_planche(faces[k:k + PAR_PLANCHE], cw, ch))
        face = poser(f"faces_{cle}_{hashlib.sha256(d).hexdigest()[:10]}.jpg", d)
        if uniques:
            d2 = _jpeg(_planche(dos[k:k + PAR_PLANCHE], cw, ch))
            arriere = poser(f"dos_{cle}_{hashlib.sha256(d2).hexdigest()[:10]}.jpg", d2)
        else:
            arriere = dos_commun
        custom[str(cle)] = {"FaceURL": _url(face), "BackURL": _url(arriere), "NumWidth": COLS, "NumHeight": ROWS,
                            "BackIsHidden": True, "UniqueBack": uniques, "Type": 0}
        for j in range(min(PAR_PLANCHE, n - k)):
            cid = 100 * cle + j
            nom = str(noms[k + j] if k + j < len(noms) else "").strip() or f"Carte {k + j + 1}"
            ids.append(cid)
            cartes.append({"Name": "Card", "Transform": _transform(), "Nickname": nom[:120], "CardID": cid,
                           "CustomDeck": {str(cle): custom[str(cle)]}})

    if n == 1:
        objet = cartes[0]
    else:
        objet = {"Name": "Deck", "Transform": _transform(), "Nickname": str(nom_jeu or "Jeu")[:120],
                 "Description": "Card Forge (Deepotus)", "HideWhenFaceDown": True, "SidewaysCard": False,
                 "DeckIDs": ids, "CustomDeck": custom, "ContainedObjects": cartes}
    sauve = {"SaveName": "", "GameMode": "", "Date": "", "Table": "", "Sky": "", "Note": "", "Rules": "",
             "XmlUI": "", "LuaScript": "", "LuaScriptState": "", "ObjectStates": [objet], "TabStates": {},
             "VersionNumber": ""}
    js = json.dumps(sauve, ensure_ascii=False, indent=2).encode("utf-8")
    vignette = io.BytesIO()
    faces[0].resize((256, round(256 * ch / cw)), Image.LANCZOS).save(vignette, "PNG")
    poser(f"{s}.json", js)
    poser(f"{s}.png", vignette.getvalue())
    resume = {"jeu": s, "cartes": n, "planches": len(custom), "cellule": [cw, ch],
              "planche_px": [COLS * cw, ROWS * ch], "dos": note_dos, "unique_back": uniques,
              "objet": str(dossier / f"{s}.json"), "vignette": str(dossier / f"{s}.png"),
              "note": "Chemins locaux (file:///) vers les planches de ce PC : prêt en solo. Pour jouer en ligne, "
                      "Tabletop Simulator propose « Upload to Steam Cloud ». CardID = 100 x clé + index "
                      "(convention relevée, non publiée)."}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("tts/manifeste.json", json.dumps(resume, ensure_ascii=False, indent=1))
        for nom, data in fichiers:
            z.writestr(zipfile.ZipInfo(f"tts/{nom}", date_time=(2026, 1, 1, 0, 0, 0)), data,
                       compress_type=zipfile.ZIP_DEFLATED if nom.endswith(".json") else zipfile.ZIP_STORED)
    return buf.getvalue(), resume
