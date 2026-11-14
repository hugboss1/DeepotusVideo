# -*- coding: utf-8 -*-
"""SVB (15/11/2026) — les IMAGES du studio virtuel venues de la BIBLIOTHÈQUE de l'application : illustrations, logos,
affiches que l'utilisateur a générés ou importés, posés dans un décor en tableau, en logo mural, en kakémono, sur un
écran du décor ou en enseigne. Conception docs/superpowers/specs/2026-11-14-studio-virtuel-3d-design.md (§ 9).

Une image de la Bibliothèque est RECOPIÉE dans le studio à sa première utilisation (même doctrine que le catalogue de
matières de la Forge) : le décor reste entier si elle est ensuite jetée ou renommée dans la Bibliothèque. La copie est
ramenée à 2 048 px au plus (une texture de décor n'a pas besoin de plus, une carte intégrée la porte), sa
transparence est gardée (un logo détouré reste détouré). La recette ne garde qu'une RÉFÉRENCE `img:<id>`.

- `DATA_ROOT/studiov/images/<id>/{image.png | image.jpg, fiche.json}` (id = 16 hex) ;
- la fiche garde le fichier d'origine, sa licence et son auteur tels que la Bibliothèque les connaît : ils servent
  aux crédits du décor.
Aucun réseau, aucune dépense."""
from __future__ import annotations

import io
import json
import re
import secrets
import shutil
import threading
from pathlib import Path

from app.config import settings
from app.services import studiov as S

ID_IMAGE = re.compile(r"^[a-f0-9]{16}$")
EXTENSIONS = (".png", ".jpg", ".jpeg", ".webp")
MAX_COTE = 2048
MAX_IMAGES = 400
_VERROU = threading.RLock()
_vignettes: dict = {}                      # (fichier, mtime) -> octets JPEG


class RefusImage(ValueError):
    """Une demande refusée : `statut` = le code HTTP. Message littéral (traduit par L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


def racine() -> Path:
    return S.racine() / "images"


def fichier_bibliotheque(filename) -> Path:
    """Un fichier image de la Bibliothèque, désigné par son NOM seul (jamais un chemin)."""
    if not isinstance(filename, str) or not filename or Path(filename).name != filename or filename in (".", ".."):
        raise RefusImage("Nom de fichier invalide.", 400)
    f = settings.images_path / filename
    if f.suffix.lower() not in EXTENSIONS or not f.is_file():
        raise RefusImage("Image introuvable dans la Bibliothèque.", 404)
    return f


def vignette_bibliotheque(filename) -> bytes:
    """La vignette (120 px, JPEG sur fond sombre) d'une image de la Bibliothèque, pour la grille du décorateur."""
    from PIL import Image
    f = fichier_bibliotheque(filename)
    cle = (filename, f.stat().st_mtime_ns)
    with _VERROU:
        if cle in _vignettes:
            return _vignettes[cle]
    try:
        with Image.open(f) as im:
            im.draft("RGB", (240, 240))
            im = im.convert("RGBA")
            im.thumbnail((120, 120), Image.LANCZOS)
            fond = Image.new("RGB", im.size, (27, 32, 40))
            fond.paste(im, mask=im.getchannel("A"))
            buf = io.BytesIO()
            fond.save(buf, "JPEG", quality=80)
    except Exception:                                   # noqa: BLE001 — fichier qui n'est pas une image lisible
        raise RefusImage("Image illisible.", 415) from None
    with _VERROU:
        if len(_vignettes) >= 600:
            _vignettes.clear()
        _vignettes[cle] = buf.getvalue()
    return buf.getvalue()


def _dossier(iid: str) -> Path:
    if not isinstance(iid, str) or not ID_IMAGE.match(iid):
        raise RefusImage("Identifiant d'image invalide.", 400)
    return racine() / iid


def _fiche(iid: str) -> dict:
    dossier = _dossier(iid)
    try:
        d = json.loads((dossier / "fiche.json").read_text("utf-8"))
    except (OSError, ValueError):
        raise RefusImage("Image introuvable.", 404) from None
    if not isinstance(d, dict) or d.get("fichier") not in ("image.png", "image.jpg"):
        raise RefusImage("Image introuvable.", 404)
    return d


def _vue(iid: str, d: dict) -> dict:
    return {"id": iid, "ref": f"img:{iid}", "nom": S.K._texte(d.get("nom"), iid, 60) or iid, "origine": S.K._texte(d.get("origine"), "", 200),
            "l": int(d.get("l") or 1), "h": int(d.get("h") or 1), "alpha": bool(d.get("alpha")),
            "licence": S.K._texte(d.get("licence"), "", 40), "auteur": S.K._texte(d.get("auteur"), "", 80),
            "cree": d.get("cree") or "", "url": f"/api/studiov/images/{iid}/fichier"}


def lire(iid: str) -> dict:
    return _vue(iid, _fiche(iid))


def chemin(iid: str) -> Path:
    f = _dossier(iid) / _fiche(iid)["fichier"]
    if not f.is_file():
        raise RefusImage("Image introuvable.", 404)
    return f


def lister() -> list:
    out = []
    if racine().is_dir():
        for d in racine().iterdir():
            if d.is_dir() and ID_IMAGE.match(d.name):
                try:
                    out.append(lire(d.name))
                except RefusImage:
                    continue
    return sorted(out, key=lambda v: v["cree"], reverse=True)


def depuis_bibliotheque(filename, connu: dict | None = None) -> dict:
    """Recopie une image de la Bibliothèque dans le studio et rend sa fiche. `connu` = ce que l'index de la
    Bibliothèque sait du fichier (licence, auteur). La même image, inchangée, n'est copiée qu'une fois."""
    from PIL import Image
    f = fichier_bibliotheque(filename)
    st = f.stat()
    cle = f"{filename}|{st.st_size}|{st.st_mtime_ns}"
    with _VERROU:
        if racine().is_dir():
            for d in racine().iterdir():
                try:
                    if json.loads((d / "fiche.json").read_text("utf-8")).get("cle") == cle:
                        return lire(d.name)
                except (OSError, ValueError, AttributeError):
                    continue
        if len(lister()) >= MAX_IMAGES:
            raise RefusImage("Trop d'images dans le studio : retirez-en une d'abord.", 409)
        try:
            with Image.open(f) as im:
                im.load()
                alpha = im.mode in ("RGBA", "LA") or "transparency" in im.info
                im = im.convert("RGBA" if alpha else "RGB")
                if alpha and im.getchannel("A").getextrema()[0] == 255:
                    alpha, im = False, im.convert("RGB")           # une couche alpha toute opaque n'est pas une transparence
                if max(im.size) > MAX_COTE:
                    im.thumbnail((MAX_COTE, MAX_COTE), Image.LANCZOS)
                buf = io.BytesIO()
                if alpha:
                    im.save(buf, "PNG", optimize=True)
                else:
                    im.save(buf, "JPEG", quality=90, optimize=True)
                l, h = im.size
        except RefusImage:
            raise
        except Exception:                               # noqa: BLE001 — fichier qui n'est pas une image lisible
            raise RefusImage("Image illisible.", 415) from None
        iid = secrets.token_hex(8)
        d = _dossier(iid)
        d.mkdir(parents=True, exist_ok=False)
        nom = "image.png" if alpha else "image.jpg"
        try:
            (d / nom).write_bytes(buf.getvalue())
            c = connu if isinstance(connu, dict) else {}
            S.K._ecrire_json(d / "fiche.json", {"nom": S.K._texte(Path(filename).stem, "", 60) or "Image", "origine": filename, "cle": cle,
                                                "fichier": nom, "l": l, "h": h, "alpha": alpha,
                                                "licence": S.K._texte(c.get("licence"), "", 40), "auteur": S.K._texte(c.get("auteur"), "", 80),
                                                "cree": S.K._maintenant()})
        except OSError:
            shutil.rmtree(d, ignore_errors=True)
            raise RefusImage("L'image n'a pas pu être enregistrée.", 500) from None
    return lire(iid)


def emplois(decor: dict) -> set:
    """Les références d'image qu'un décor emploie : objets, écrans, enseigne."""
    refs = {o.get("image") for o in decor.get("objets", [])} | {e.get("image") for e in decor.get("ecrans", [])}
    if (decor.get("enseigne") or {}).get("source") == "image":
        refs.add(decor["enseigne"].get("image"))
    return {r for r in refs if isinstance(r, str) and r}


def supprimer(iid: str) -> None:
    with _VERROU:
        d = _dossier(iid)
        if not d.is_dir():
            raise RefusImage("Image introuvable.", 404)
        ref = f"img:{iid}"
        noms = [v["nom"] for v in S._tous() if ref in emplois(v)]
        if noms:
            raise RefusImage(f"Cette image est posée dans {len(noms)} décor(s) : retirez-la d'abord de « {noms[0]} ».", 409)
        shutil.rmtree(d, ignore_errors=True)
