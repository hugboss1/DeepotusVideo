# -*- coding: utf-8 -*-
"""t316 (28/10/2026) (lot D2 « skins de capture ») — les SKINS qui habillent la scène de la capture (t315), façon
chaîne YouTube. Plan docs/superpowers/plans/2026-10-28-t316-skins.md, spec 2026-10-25-boite-a-outils-design.md §8.5.

Un skin est un document `DATA_ROOT/skins/<id>.json` (id = 16 hex) rattaché à un espace, avec ses images
`DATA_ROOT/skins/<id>/{logo,fond}.png`. `DATA_ROOT/skins/choix.json` = {espace_id: skin_id | ""} : le skin de chaque
espace ("" = sans habillage) ; rien n'est écrit dans espaces.json. Cinq skins LIVRÉS, en lecture seule
(`app/skins/livres.json`) : un espace qui n'a rien choisi prend `livre-deepotus`, dont le petit « Fait avec
DeepotusVideo » est actif par défaut et désactivable (spec §12, choix 10).

Le serveur est le SEUL juge du format (`normaliser`) : un champ inconnu est ignoré, une valeur hors borne est bornée,
une couleur qui n'est ni un rôle (principale, accent, texte, fond) ni un #rrggbb reprend sa valeur par défaut. Les
couleurs `principale`/`accent` à null suivent le KIT de l'espace (`espaces.kit_de_l_espace`) ; les polices à null
suivent son IDENTITÉ (typographies, t206). Le logo d'un skin est celui DE L'ESPACE (ou une image du skin) ; le logo
de l'application n'est jamais lu ni touché ici (règle du logo figé, 16/10).

Export et import : un .zip à LISTE BLANCHE (`skin.json`, `images/logo.png`, `images/fond.png`), 12 Mo au plus, tout
validé avant la première écriture ; l'import crée toujours un skin NEUF dans l'espace courant.
Aucun réseau, aucune dépense. Les refus portent un message littéral (traduit par L10)."""
from __future__ import annotations

import copy
import io
import json
import re
import secrets
import threading
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from app.config import DATA_ROOT

FORMAT = "deepotus-skin"
VERSION = 1
ID = re.compile(r"^[a-f0-9]{16}$")
ID_LIVRE = re.compile(r"^livre-[a-z]{2,20}$")
DEFAUT_ESPACE = "livre-deepotus"
LIVRES_FICHIER = Path(__file__).resolve().parent.parent / "skins" / "livres.json"
IMAGES = ("logo", "fond")
MAX_IMAGE = 5 * 1024 * 1024
MAX_COTE = 2048
MAX_SKINS = 60
MAX_ZIP = 12 * 1024 * 1024
MAX_ENTREES = 8
ENTREES = {"skin.json": None, "images/logo.png": "logo", "images/fond.png": "fond"}
ROLES = ("principale", "accent", "texte", "fond")
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")
POLICE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \-]{0,39}$")
FORMES = ("cercle", "carre", "vif")
STYLES_BANDEAU = ("bande", "bloc", "souligne")
STYLES_CURSEUR = ("anneau", "point", "aucun")
FONDS = ("uni", "degrade", "image")
COINS = ("bas-droite", "bas-gauche", "haut-droite", "haut-gauche")
MAX_NOM, MAX_TEXTE = 60, 80

# le skin de référence : chaque livré et chaque skin de l'utilisateur en est une variation
DEFAUT = {
    "couleurs": {"principale": None, "accent": None, "texte": "#ffffff", "fond": "#0b0f14"},
    "polices": {"titre": None, "texte": None},
    "cadre": {"marge": 0.0, "bord": 0.0, "couleur": "principale", "fond": {"type": "degrade", "c1": "fond", "c2": "principale"}},
    "logo": {"actif": True, "source": "espace", "x": 0.03, "y": 0.04, "l": 0.07, "opacite": 0.9},
    "bandeau": {"actif": True, "titre": "", "sous_titre": "", "style": "bande", "x": 0.03, "y": 0.8, "l": 0.45,
                "debut_s": 2.0, "duree_s": 8.0},
    "intro": {"actif": True, "titre": "", "sous_titre": "", "duree_s": 3.0},
    "outro": {"actif": True, "titre": "", "sous_titre": "", "duree_s": 3.0},
    "encart": {"forme": "cercle", "bord": 0.004, "couleur": "principale", "ombre": True, "x": 0.76, "y": 0.62,
               "l": 0.2, "h": 0.32},
    "alertes": {"actif": True, "x": 0.35, "y": 0.05, "l": 0.3, "duree_s": 5.0, "abonne": "", "message": ""},
    "pause": {"titre": "", "sous_titre": ""},
    "fin": {"titre": "", "sous_titre": ""},
    "zoom": {"niveau": 1.5, "duree_ms": 1800},
    "curseur": {"style": "anneau", "couleur": "accent", "taille": 1.0},
    "signature": {"actif": False, "coin": "bas-droite", "opacite": 0.75},
}
# bornes des nombres : (min, max) ; les places x, y, l, h sont normalisées 0..1 et tenues dans le cadre ensuite
BORNES = {
    ("cadre", "marge"): (0.0, 0.12), ("cadre", "bord"): (0.0, 0.02),
    ("logo", "l"): (0.03, 0.3), ("logo", "opacite"): (0.2, 1.0),
    ("bandeau", "l"): (0.2, 0.9), ("bandeau", "debut_s"): (0.0, 600.0), ("bandeau", "duree_s"): (0.0, 600.0),
    ("intro", "duree_s"): (1.0, 8.0), ("outro", "duree_s"): (1.0, 8.0),
    ("encart", "bord"): (0.0, 0.02), ("encart", "l"): (0.08, 0.6), ("encart", "h"): (0.08, 0.6),
    ("alertes", "l"): (0.15, 0.7), ("alertes", "duree_s"): (2.0, 10.0),
    ("zoom", "niveau"): (1.1, 2.5), ("zoom", "duree_ms"): (800, 4000),
    ("curseur", "taille"): (0.5, 2.0), ("signature", "opacite"): (0.3, 1.0),
}
ENTIERS = {("zoom", "duree_ms")}

_VERROU = threading.Lock()


class RefusSkin(ValueError):
    """Une demande refusée : `statut` = le code HTTP (400, 404, 409, 413, 415). Message littéral (L10)."""
    def __init__(self, message: str, statut: int):
        super().__init__(message)
        self.statut = statut


def racine() -> Path:
    return DATA_ROOT / "skins"


def _maintenant() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def est_livre(sid) -> bool:
    return isinstance(sid, str) and bool(ID_LIVRE.match(sid)) and sid in _livres_bruts()


# ── format ──

def _nombre(v, defaut, lo, hi, entier=False):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or v != v:          # NaN refusé
        return defaut
    v = max(lo, min(hi, v))
    return int(round(v)) if entier else round(float(v), 4)


def _texte(v, defaut="", n=MAX_TEXTE) -> str:
    if not isinstance(v, str):
        return defaut
    v = "".join(c for c in v if c >= " " and c != "\x7f")         # caractères de contrôle ôtés
    return re.sub(r"\s+", " ", v).strip()[:n]


def _couleur(v, defaut, nul=False):
    if v is None and nul:
        return None
    if isinstance(v, str) and (v in ROLES or HEX.match(v)):
        return v.lower() if HEX.match(v) else v
    return defaut


def _hex(v, defaut, nul=False):
    if v is None and nul:
        return None
    return v.lower() if isinstance(v, str) and HEX.match(v) else defaut


def _choix(v, permis, defaut):
    return v if v in permis else defaut


def _police(v):
    return v if isinstance(v, str) and POLICE.match(v) else None


def normaliser(doc) -> dict:
    """Le skin relu champ par champ (liste blanche). Ne lève que si `doc` n'est pas un objet."""
    if not isinstance(doc, dict):
        raise RefusSkin("Skin illisible : un objet JSON est attendu.", 400)
    d = copy.deepcopy(DEFAUT)
    src = {k: (v if isinstance(v, dict) else {}) for k, v in doc.items() if k in DEFAUT}
    for section, base in d.items():
        s = src.get(section, {})
        for k, defaut in list(base.items()):
            v = s.get(k, defaut)
            borne = BORNES.get((section, k))
            if section == "couleurs":
                base[k] = _hex(v, defaut, nul=k in ("principale", "accent"))
            elif section == "polices":
                base[k] = _police(v)
            elif k == "couleur":
                base[k] = _couleur(v, defaut)
            elif k == "fond" and section == "cadre":
                f = v if isinstance(v, dict) else {}
                base[k] = {"type": _choix(f.get("type"), FONDS, defaut["type"]),
                           "c1": _couleur(f.get("c1"), defaut["c1"]), "c2": _couleur(f.get("c2"), defaut["c2"])}
            elif isinstance(defaut, bool):
                base[k] = v if isinstance(v, bool) else defaut
            elif borne:
                base[k] = _nombre(v, defaut, *borne, entier=(section, k) in ENTIERS)
            elif k in ("x", "y"):
                base[k] = _nombre(v, defaut, 0.0, 1.0)
            elif k == "forme":
                base[k] = _choix(v, FORMES, defaut)
            elif k == "style":
                base[k] = _choix(v, STYLES_BANDEAU if section == "bandeau" else STYLES_CURSEUR, defaut)
            elif k == "source":
                base[k] = _choix(v, ("espace", "image"), defaut)
            elif k == "type":
                base[k] = _choix(v, FONDS, defaut)
            elif k == "coin":
                base[k] = _choix(v, COINS, defaut)
            elif isinstance(defaut, str):
                base[k] = _texte(v, defaut)
    # une place tenue dans le cadre : x + l ≤ 1, y + h ≤ 1 (la hauteur d'un logo, d'un bandeau ou d'une alerte se
    # déduit de sa largeur à l'écran : seule la marge basse de l'encart, qui a sa hauteur, est vérifiée ici)
    for section in ("logo", "bandeau", "alertes", "encart"):
        p = d[section]
        p["x"] = round(min(p["x"], 1 - p["l"]), 4)
        if "h" in p:
            p["y"] = round(min(p["y"], 1 - p["h"]), 4)
    return d


def _livres_bruts() -> dict:
    try:
        return json.loads(LIVRES_FICHIER.read_text("utf-8"))
    except (OSError, ValueError):
        return {}


def _vue(sid: str, doc: dict, livre: bool, espace_id=None, nom="", modifie="", base=None) -> dict:
    v = normaliser(doc)
    v.update({"format": FORMAT, "version": VERSION, "id": sid, "nom": nom or sid, "livre": livre,
              "espace_id": None if livre else espace_id, "base": base, "modifie": modifie})
    v["images"] = [] if livre else [n for n in IMAGES if (racine() / sid / f"{n}.png").is_file()]
    return v


def livres() -> list:
    return [_vue(k, v, True, nom=_texte(v.get("nom"), k, MAX_NOM)) for k, v in _livres_bruts().items() if ID_LIVRE.match(k)]


# ── stockage ──

def _fichier(sid: str) -> Path:
    if not isinstance(sid, str) or not ID.match(sid):
        raise RefusSkin("Identifiant de skin invalide.", 400)
    return racine() / f"{sid}.json"


def _ecrire_json(f: Path, doc) -> None:
    f.parent.mkdir(parents=True, exist_ok=True)
    tmp = f.with_name(f.name + ".tmp")
    tmp.write_text(json.dumps(doc, ensure_ascii=False, indent=1), "utf-8")
    tmp.replace(f)


def _lire_brut(sid: str) -> dict:
    f = _fichier(sid)
    try:
        doc = json.loads(f.read_text("utf-8"))
    except FileNotFoundError:
        raise RefusSkin("Skin introuvable.", 404) from None
    except (OSError, ValueError):
        raise RefusSkin("Skin illisible.", 409) from None
    if not isinstance(doc, dict):
        raise RefusSkin("Skin illisible.", 409)
    return doc


def lire(sid: str) -> dict:
    if est_livre(sid):
        return next(v for v in livres() if v["id"] == sid)
    if isinstance(sid, str) and ID_LIVRE.match(sid):
        raise RefusSkin("Skin introuvable.", 404)
    d = _lire_brut(sid)
    return _vue(sid, d, False, d.get("espace_id"), _texte(d.get("nom"), sid, MAX_NOM), d.get("modifie", ""), d.get("base"))


def _tous() -> list:
    out = []
    if racine().is_dir():
        for f in sorted(racine().glob("*.json")):
            if ID.match(f.stem):
                try:
                    out.append(lire(f.stem))
                except RefusSkin:
                    continue                          # un fichier illisible n'empêche pas la liste
    return out


def lister(eid: str) -> list:
    return [v for v in _tous() if v["espace_id"] == eid]


def _nom_libre(nom: str, eid: str) -> str:
    noms = {v["nom"] for v in lister(eid)}
    if nom not in noms:
        return nom
    for i in range(2, 100):
        n = f"{nom[:MAX_NOM - 5]} ({i})"
        if n not in noms:
            return n
    return nom


def _enregistrer_brut(sid: str, doc: dict, eid: str, nom: str, base) -> dict:
    brut = normaliser(doc)
    brut.update({"format": FORMAT, "version": VERSION, "nom": nom, "espace_id": eid, "base": base,
                 "modifie": _maintenant()})
    _ecrire_json(_fichier(sid), brut)
    return lire(sid)


def creer(base: str | None, nom: str | None, eid: str) -> dict:
    """Un skin neuf de l'espace `eid` : copie de `base` (livré ou skin, images comprises) ou du skin de référence."""
    with _VERROU:
        if len(_tous()) >= MAX_SKINS:
            raise RefusSkin("Trop de skins : supprimez-en un d'abord.", 409)
        src = lire(base) if base else None
        n = _texte(nom, "", MAX_NOM) or (src["nom"] if src else "Skin")
        sid = secrets.token_hex(8)
        v = _enregistrer_brut(sid, src or {}, eid, _nom_libre(n, eid), base if src else None)
        if src and not src["livre"]:
            for im in src["images"]:
                (racine() / sid).mkdir(parents=True, exist_ok=True)
                (racine() / sid / f"{im}.png").write_bytes((racine() / src["id"] / f"{im}.png").read_bytes())
            v = lire(sid)
        return v


def enregistrer(sid: str, doc) -> dict:
    """Remplace le contenu d'un skin de l'utilisateur (le nom peut changer ; l'espace, jamais). Livré : 409."""
    if est_livre(sid) or (isinstance(sid, str) and ID_LIVRE.match(sid)):
        raise RefusSkin("Un skin livré ne se modifie pas : dupliquez-le d'abord.", 409)
    if not isinstance(doc, dict):
        raise RefusSkin("Skin illisible : un objet JSON est attendu.", 400)
    with _VERROU:
        d = _lire_brut(sid)
        nom = _texte(doc.get("nom"), "", MAX_NOM) or _texte(d.get("nom"), sid, MAX_NOM)
        return _enregistrer_brut(sid, doc, d.get("espace_id"), nom, d.get("base"))


def supprimer(sid: str) -> None:
    if est_livre(sid) or (isinstance(sid, str) and ID_LIVRE.match(sid)):
        raise RefusSkin("Un skin livré ne se supprime pas.", 409)
    with _VERROU:
        f = _fichier(sid)
        if not f.is_file():
            raise RefusSkin("Skin introuvable.", 404)
        f.unlink()
        dossier = racine() / sid
        if dossier.is_dir():
            for x in dossier.iterdir():
                x.unlink()
            dossier.rmdir()
        ch = _choix_lus()
        if sid in ch.values():
            _ecrire_json(racine() / "choix.json", {k: v for k, v in ch.items() if v != sid})


# ── le skin de chaque espace ──

def _choix_lus() -> dict:
    try:
        d = json.loads((racine() / "choix.json").read_text("utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in d.items() if isinstance(k, str) and isinstance(v, str)} if isinstance(d, dict) else {}


def choisi(eid: str) -> str:
    """L'id du skin de l'espace ("" = sans habillage) ; un choix disparu retombe sur le livré par défaut."""
    sid = _choix_lus().get(eid)
    if sid is None:
        return DEFAUT_ESPACE
    if sid == "" or est_livre(sid):
        return sid
    try:
        return sid if lire(sid)["espace_id"] == eid else DEFAUT_ESPACE
    except RefusSkin:
        return DEFAUT_ESPACE


def choisir(eid: str, sid) -> str:
    if sid in (None, ""):
        sid = ""
    elif not est_livre(sid):
        if lire(sid)["espace_id"] != eid:          # 404/400 levés par lire
            raise RefusSkin("Ce skin appartient à un autre espace : dupliquez-le d'abord.", 409)
    with _VERROU:
        ch = _choix_lus()
        ch[eid] = sid
        _ecrire_json(racine() / "choix.json", ch)
    return sid


def actif(eid: str) -> dict | None:
    sid = choisi(eid)
    return lire(sid) if sid else None


def contexte(eid: str) -> dict:
    """Ce que l'écran lit pour résoudre un skin : l'espace, son kit (couleurs, slogans), ses polices, son logo."""
    from app.services import espaces, identite
    try:
        e = espaces.lire()["espaces"].get(eid) or {}
    except Exception:  # noqa: BLE001 — un espace illisible n'empêche pas d'habiller la scène
        e = {}
    try:
        kit = espaces.kit_de_l_espace(eid)
    except Exception:  # noqa: BLE001
        kit = {}
    try:
        typos = [t.get("nom") for t in identite.lire(eid).get("typographies", []) if isinstance(t, dict)]
    except Exception:  # noqa: BLE001
        typos = []
    typos = [t for t in typos if _police(t)]
    return {
        "espace": {"id": eid, "nom": _texte(e.get("nom"), eid, MAX_NOM)},
        "kit": {k: kit.get(k) for k in ("name", "brand_color", "accent_color", "tagline_1", "tagline_2")},
        "polices": {"titre": typos[0] if typos else None, "texte": (typos[1] if len(typos) > 1 else typos[0]) if typos else None},
        "logo_espace": f"/api/espaces/{eid}/logo",
    }


# ── images ──

def _png(octets: bytes) -> bytes:
    """Une image relue par Pillow (qui vérifie que c'en est une), réduite à 2 048 px au plus, réécrite en PNG."""
    if len(octets) > MAX_IMAGE:
        raise RefusSkin("Image trop lourde : 5 Mo au plus.", 413)
    from PIL import Image
    try:
        with Image.open(io.BytesIO(octets)) as im:
            im.verify()
        with Image.open(io.BytesIO(octets)) as im:
            if im.width * im.height > 40_000_000:
                raise RefusSkin("Image trop grande.", 413)
            im = im.convert("RGBA")
            im.thumbnail((MAX_COTE, MAX_COTE))
            sortie = io.BytesIO()
            im.save(sortie, "PNG", optimize=True)
            return sortie.getvalue()
    except RefusSkin:
        raise
    except Exception:  # noqa: BLE001 — Pillow lève des types variés sur un fichier qui n'est pas une image
        raise RefusSkin("Ce fichier n'est pas une image lisible (PNG, JPEG ou WebP).", 415) from None


def _nom_image(nom: str) -> str:
    if nom not in IMAGES:
        raise RefusSkin("Image inconnue : logo ou fond.", 400)
    return nom


def poser_image(sid: str, nom: str, octets: bytes) -> dict:
    nom = _nom_image(nom)
    if est_livre(sid):
        raise RefusSkin("Un skin livré ne se modifie pas : dupliquez-le d'abord.", 409)
    png = _png(octets)
    with _VERROU:
        d = _lire_brut(sid)
        (racine() / sid).mkdir(parents=True, exist_ok=True)
        (racine() / sid / f"{nom}.png").write_bytes(png)
        if nom == "logo":
            d.setdefault("logo", {})["source"] = "image"
        else:
            d.setdefault("cadre", {}).setdefault("fond", {})["type"] = "image"
        return _enregistrer_brut(sid, d, d.get("espace_id"), _texte(d.get("nom"), sid, MAX_NOM), d.get("base"))


def retirer_image(sid: str, nom: str) -> dict:
    nom = _nom_image(nom)
    if est_livre(sid):
        raise RefusSkin("Un skin livré ne se modifie pas : dupliquez-le d'abord.", 409)
    with _VERROU:
        d = _lire_brut(sid)
        (racine() / sid / f"{nom}.png").unlink(missing_ok=True)
        if nom == "logo" and isinstance(d.get("logo"), dict):
            d["logo"]["source"] = "espace"
        elif nom == "fond" and isinstance(d.get("cadre"), dict) and isinstance(d["cadre"].get("fond"), dict):
            d["cadre"]["fond"]["type"] = "degrade"
        return _enregistrer_brut(sid, d, d.get("espace_id"), _texte(d.get("nom"), sid, MAX_NOM), d.get("base"))


def chemin_image(sid: str, nom: str) -> Path:
    nom = _nom_image(nom)
    if est_livre(sid):
        raise RefusSkin("Image introuvable.", 404)
    _fichier(sid)
    p = racine() / sid / f"{nom}.png"
    if not p.is_file():
        raise RefusSkin("Image introuvable.", 404)
    return p


# ── export et import ──

def exporter(sid: str) -> tuple[str, bytes]:
    """(nom de fichier, octets du .zip) : skin.json (sans id ni espace) et ses images."""
    v = lire(sid)
    doc = normaliser(v)
    doc.update({"format": FORMAT, "version": VERSION, "nom": v["nom"]})
    sortie = io.BytesIO()
    with zipfile.ZipFile(sortie, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("skin.json", json.dumps(doc, ensure_ascii=False, indent=1))
        for im in v["images"]:
            z.writestr(f"images/{im}.png", (racine() / sid / f"{im}.png").read_bytes())
    import unicodedata
    ascii_ = unicodedata.normalize("NFKD", v["nom"]).encode("ascii", "ignore").decode("ascii")      # « Néon » -> neon
    slug = re.sub(r"[^A-Za-z0-9]+", "-", ascii_).strip("-").lower()[:40]
    return f"skin-{slug or 'deepotus'}.zip", sortie.getvalue()


def importer(octets: bytes, eid: str) -> dict:
    """Un skin NEUF de l'espace `eid` depuis un .zip ; tout est validé avant la première écriture. Rend la vue du skin
    et `ignores` (les entrées hors liste blanche, jamais extraites)."""
    if len(octets) > MAX_ZIP:
        raise RefusSkin("Paquet trop lourd : 12 Mo au plus.", 413)
    try:
        z = zipfile.ZipFile(io.BytesIO(octets))
        infos = z.infolist()
    except (zipfile.BadZipFile, OSError, ValueError):
        raise RefusSkin("Ce fichier n'est pas un paquet de skin (.zip) lisible.", 400) from None
    if len(infos) > MAX_ENTREES:
        raise RefusSkin("Paquet refusé : trop d'entrées.", 400)
    lus, ignores, total = {}, [], 0
    for i in infos:
        if i.filename not in ENTREES or i.is_dir():
            ignores.append(_texte(i.filename, "?", 80))
            continue
        total += i.file_size
        if i.file_size > MAX_ZIP or total > MAX_ZIP:
            raise RefusSkin("Paquet refusé : contenu décompressé trop lourd.", 413)
        with z.open(i) as f:
            data = f.read(MAX_ZIP + 1)
        if len(data) > MAX_ZIP:
            raise RefusSkin("Paquet refusé : contenu décompressé trop lourd.", 413)
        lus[i.filename] = data
    if "skin.json" not in lus:
        raise RefusSkin("Paquet refusé : skin.json manquant.", 400)
    try:
        doc = json.loads(lus["skin.json"].decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise RefusSkin("Paquet refusé : skin.json illisible.", 400) from None
    if not isinstance(doc, dict) or doc.get("format") != FORMAT or doc.get("version") != VERSION:
        raise RefusSkin("Paquet refusé : ce n'est pas un skin DeepotusVideo de version 1.", 400)
    images = {ENTREES[k]: _png(v) for k, v in lus.items() if ENTREES[k]}
    propre = normaliser(doc)
    if "logo" not in images and propre["logo"]["source"] == "image":
        propre["logo"]["source"] = "espace"
    if "fond" not in images and propre["cadre"]["fond"]["type"] == "image":
        propre["cadre"]["fond"]["type"] = "degrade"
    with _VERROU:
        if len(_tous()) >= MAX_SKINS:
            raise RefusSkin("Trop de skins : supprimez-en un d'abord.", 409)
        sid = secrets.token_hex(8)
        try:
            v = _enregistrer_brut(sid, propre, eid, _nom_libre(_texte(doc.get("nom"), "", MAX_NOM) or "Skin", eid), None)
            for nom, png in images.items():
                (racine() / sid).mkdir(parents=True, exist_ok=True)
                (racine() / sid / f"{nom}.png").write_bytes(png)
            v = lire(sid)
        except Exception:
            _fichier(sid).unlink(missing_ok=True)       # retour arrière : rien de l'import ne reste
            d = racine() / sid
            if d.is_dir():
                for x in d.iterdir():
                    x.unlink()
                d.rmdir()
            raise
    v["ignores"] = ignores
    return v
